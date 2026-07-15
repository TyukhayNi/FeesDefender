"""Cerebro del split de bundles multi-documento en la Sala de máquina.

Corte primario por HOJA EN BLANCO (chars≈0 ∧ baja tinta); marcadores como
clasificador (separar.detectar_tipo) y fallback (separar.detectar_segmentos).
NO edita core/anon/: reutiliza separar.py como librería. Ver
docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from core.anon import separar
from core.anon.exceptions import PDFVacioError
from core.utils import file_sha256

_LOG = logging.getLogger("split_documental")
if not _LOG.handlers:
    _LOG.addHandler(logging.NullHandler())

# Umbrales del detector de blanco (calibrar contra el bundle real en F0, Task 8b).
UMBRAL_CHARS_BLANCO = 10       # < → candidata a blanco (cribado barato por chars OCR)
UMBRAL_TINTA_BLANCO = 0.008    # fracción de píxeles con tinta; < → blanco confirmado
_RENDER_SCALE = 2              # pypdfium2 → ~144 dpi
_UMBRAL_OSCURO = 200           # nivel de gris (0-255) por debajo del cual el píxel es "tinta"

# Marcadores E&V inyectados (hueco del congelado: separar.TIPOS_DOCUMENTO está
# tuneado a lo judicial). Se pasan como tipos_extra; NO viven en core/anon.
TIPOS_EXTRA_EV: list[dict] = [
    {"tipo": "DOC_PBC", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["PREVENCION DE BLANQUEO", "PREVENCIÓN DE BLANQUEO",
                    "SUJETO OBLIGADO", "IDENTIFICACION DEL TITULAR REAL",
                    "IDENTIFICACIÓN DEL TITULAR REAL"]},
    {"tipo": "DOC_ARRAS", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["CONTRATO DE ARRAS", "ARRAS PENITENCIALES", "SEÑAL Y ARRAS"]},
    {"tipo": "DOC_RESERVA", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["DOCUMENTO DE RESERVA", "HOJA DE RESERVA", "CONTRATO DE RESERVA"]},
    {"tipo": "DOC_ACTIVACION", "prioridad": 7, "exige_inicio": True,
     "marcadores": ["ACTIVACION DEL ENCARGO", "ACTIVACIÓN DEL ENCARGO", "HOJA DE ACTIVACION",
                    "HOJA DE ACTIVACIÓN"]},
    {"tipo": "DOC_OFERTA", "prioridad": 6, "exige_inicio": True,
     "marcadores": ["OFERTA DE COMPRA", "HOJA DE OFERTA", "PROPUESTA DE COMPRA"]},
    {"tipo": "DOC_RECLAMACION", "prioridad": 6, "exige_inicio": True,
     "marcadores": ["RECLAMACION DE CANTIDAD", "RECLAMACIÓN DE CANTIDAD",
                    "REQUERIMIENTO DE PAGO", "BUROFAX"]},
]


@dataclass
class Segmento:
    seg: int
    pagina_inicio: int
    pagina_fin: int
    tipo: str
    role: str = "documento"


@dataclass
class DocLogico:
    slug: str
    seg_sha256: str
    destino: str          # passthrough | split | merge
    tipo: str
    parent_slug: str
    parent_sha256: str
    role_in_bundle: str
    paginas: str | None
    fuentes: list[str] = field(default_factory=list)


def segmentar_por_blancos(total_pag: int, blancos: set[int]) -> list[tuple[int, int]]:
    """Puro: rangos (inicio, fin) 1-based inclusive EXCLUYENDO las páginas en blanco.

    Colapsa blancos consecutivos, iniciales y finales; nunca emite rangos vacíos.
    """
    rangos: list[tuple[int, int]] = []
    inicio: int | None = None
    for p in range(1, total_pag + 1):
        if p in blancos:
            if inicio is not None:
                rangos.append((inicio, p - 1))
                inicio = None
        else:
            if inicio is None:
                inicio = p
    if inicio is not None:
        rangos.append((inicio, total_pag))
    return rangos


def _primeras_lineas(texto_pagina: str, n: int = 5) -> list[str]:
    """Primeras N líneas útiles (>=3 chars) del texto de una página (para clasificar)."""
    out: list[str] = []
    for raw in (texto_pagina or "").splitlines():
        ln = raw.strip()
        if len(ln) >= 3:
            out.append(ln)
        if len(out) >= n:
            break
    return out


def clasificar(textos: list[str], inicio: int, fin: int, *, tipos_extra=None) -> str:
    """Etiqueta un segmento por los marcadores de su primera página (separar.detectar_tipo).

    Reutiliza los marcadores judiciales de separar.py + los E&V inyectados. Sin
    marcador reconocible → 'DOCUMENTO'.
    """
    if tipos_extra is None:
        tipos_extra = TIPOS_EXTRA_EV
    lineas = _primeras_lineas(textos[inicio - 1]) if 0 <= inicio - 1 < len(textos) else []
    tipo, _prio, _num = separar.detectar_tipo(lineas, tipos_extra=tipos_extra)
    return tipo or "DOCUMENTO"


def _texto_por_pagina(pdf_path: Path) -> list[str]:
    """Texto de cada página vía pypdf (cribado barato; el buscable ya tiene capa)."""
    from pypdf import PdfReader
    with PdfReader(str(pdf_path)) as reader:
        return [(p.extract_text() or "") for p in reader.pages]


def cobertura_tinta(pdf_path: Path, num_pag: int, *, scale: int = _RENDER_SCALE) -> float:
    """Fracción de píxeles con tinta (grises < _UMBRAL_OSCURO) de la página `num_pag` (1-based).

    Una hoja en blanco (aunque escaneada, con mota/franjas) queda muy por debajo del
    umbral; una foto/plano escaneado con 0 chars OCR tiene tinta alta → NO es blanco.
    """
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        pil = doc[num_pag - 1].render(scale=scale).to_pil().convert("L")
    finally:
        doc.close()
    hist = pil.histogram()               # 256 buckets para modo 'L'
    oscuros = sum(hist[:_UMBRAL_OSCURO])
    total = pil.width * pil.height
    return oscuros / total if total else 0.0


def paginas_en_blanco(pdf_path: Path, textos: list[str], *,
                      umbral_chars: int = UMBRAL_CHARS_BLANCO,
                      umbral_tinta: float = UMBRAL_TINTA_BLANCO) -> set[int]:
    """Páginas delimitadoras (1-based): pocos chars OCR Y baja cobertura de tinta.

    Cribado barato por chars primero; solo las candidatas se rasterizan (coste
    acotado a las páginas vacías-de-texto, no a las 200).
    """
    blancos: set[int] = set()
    for i, txt in enumerate(textos, 1):
        if len((txt or "").strip()) >= umbral_chars:
            continue  # tiene texto → no es separador
        if cobertura_tinta(pdf_path, i) < umbral_tinta:
            blancos.add(i)
    return blancos


def detectar(pdf_path: Path, *, tipos_extra=None, log: logging.Logger | None = None
             ) -> tuple[list[Segmento], set[int]]:
    """Detecta los documentos lógicos de un PDF ya buscable.

    Primario: hoja en blanco. Fallback (sin blancos): marcadores (separar). Si
    ni una ni otro dan >1 → passthrough (un solo segmento con todo el PDF).
    Devuelve (segmentos, paginas_en_blanco).
    """
    log = log or _LOG
    if tipos_extra is None:
        tipos_extra = TIPOS_EXTRA_EV
    pdf_path = Path(pdf_path)

    textos = _texto_por_pagina(pdf_path)
    total = len(textos)
    if total == 0:
        raise PDFVacioError(f"PDF sin páginas: {pdf_path.name}")

    blancos = paginas_en_blanco(pdf_path, textos)
    rangos = segmentar_por_blancos(total, blancos)

    if len(rangos) > 1:
        segmentos = [
            Segmento(seg=i, pagina_inicio=ini, pagina_fin=fin,
                     tipo=clasificar(textos, ini, fin, tipos_extra=tipos_extra))
            for i, (ini, fin) in enumerate(rangos, 1)
        ]
        return segmentos, blancos

    # Sin blancos útiles → fallback por marcadores
    segs_sep = separar.detectar_segmentos(pdf_path, log, tipos_extra=tipos_extra)
    if len(segs_sep) > 1:
        segmentos = [
            Segmento(seg=i, pagina_inicio=s["pagina_inicio"], pagina_fin=s["pagina_fin"],
                     tipo=s["tipo"])
            for i, s in enumerate(segs_sep, 1)
        ]
        return segmentos, blancos

    # Passthrough
    tipo = clasificar(textos, 1, total, tipos_extra=tipos_extra)
    return [Segmento(seg=1, pagina_inicio=1, pagina_fin=total, tipo=tipo)], blancos


_MANIFIESTO_JSON = "_segmentacion.json"
_MANIFIESTO_MD = "_segmentacion.md"


def _pp(inicio: int, fin: int) -> str:
    """Serializa un rango de páginas 1-based inclusive como 'inicio-fin'."""
    return f"{inicio}-{fin}"


def _pp_a_rango(pp: str) -> tuple[int, int]:
    """Inversa de `_pp`: 'inicio-fin' -> (inicio, fin)."""
    a, b = pp.split("-", 1)
    return int(a), int(b)


def construir_manifiesto(bundle_rel_path: str, bundle_sha256: str,
                         segmentos: list[Segmento], blancos: set[int]) -> dict:
    """Construye el manifiesto (dict serializable) propuesto por `plan` a partir de `detectar`."""
    return {
        "fuente": bundle_rel_path,
        "bundle_sha256": bundle_sha256,
        "segmentos": [{"seg": s.seg, "pp": _pp(s.pagina_inicio, s.pagina_fin),
                       "tipo": s.tipo, "role": s.role} for s in segmentos],
        "delimitadores": sorted(blancos),
    }


def escribir_manifiesto(carpeta_bundle: Path, manifiesto: dict) -> None:
    """Escribe el manifiesto como JSON (editable por el letrado) + espejo Markdown legible."""
    carpeta_bundle = Path(carpeta_bundle)
    carpeta_bundle.mkdir(parents=True, exist_ok=True)
    (carpeta_bundle / _MANIFIESTO_JSON).write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    lineas = [
        "<!-- GENERADO — editable: ajusta pp/tipo/role y re-ejecuta apply -->",
        f"# Segmentación propuesta — {manifiesto['fuente']}",
        "",
        "| seg | páginas | tipo | role |",
        "|---|---|---|---|",
    ]
    for e in manifiesto["segmentos"]:
        lineas.append(f"| {e['seg']} | {e['pp']} | {e['tipo']} | {e['role']} |")
    lineas += ["", f"Delimitadores (hojas en blanco descartadas): {manifiesto['delimitadores']}", ""]
    (carpeta_bundle / _MANIFIESTO_MD).write_text("\n".join(lineas) + "\n", encoding="utf-8")


def leer_manifiesto(carpeta_bundle: Path) -> dict:
    """Lee de vuelta el manifiesto JSON (tras la edición del letrado, para `apply`)."""
    return json.loads((Path(carpeta_bundle) / _MANIFIESTO_JSON).read_text(encoding="utf-8"))


def manifiesto_existe(carpeta_bundle: Path) -> bool:
    """True si ya hay un manifiesto escrito en `carpeta_bundle` (idempotencia de `plan`)."""
    return (Path(carpeta_bundle) / _MANIFIESTO_JSON).exists()


def validar_manifiesto(manifiesto: dict, total_pag: int) -> None:
    """Falla claro si algún rango está fuera de [1, total_pag] o solapa/está desordenado."""
    ultimo_fin = 0
    for e in sorted(manifiesto["segmentos"], key=lambda x: _pp_a_rango(x["pp"])[0]):
        ini, fin = _pp_a_rango(e["pp"])
        if ini < 1 or fin > total_pag or fin < ini:
            raise ValueError(f"Segmento {e['seg']} fuera de rango: {e['pp']} (total {total_pag})")
        if ini <= ultimo_fin:
            raise ValueError(f"Segmento {e['seg']} solapa con el anterior: {e['pp']}")
        ultimo_fin = fin
