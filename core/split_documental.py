"""Cerebro del split de bundles multi-documento en la Sala de máquina.

Corte primario por HOJA EN BLANCO (chars≈0 ∧ baja tinta); marcadores como
clasificador (separar.detectar_tipo) y fallback (separar.detectar_segmentos).
NO edita core/anon/: reutiliza separar.py como librería. Ver
docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from core.anon import separar
from core.anon.exceptions import PDFVacioError
from core.utils import file_sha256

_LOG = logging.getLogger("split_documental")
if not _LOG.handlers:
    _LOG.addHandler(logging.NullHandler())


class ManifestValidationError(ValueError):
    """Manifiesto de segmentación inválido: identidad, ledger o destino.

    Hereda de `ValueError` a propósito: `validar_manifiesto` ya lanzaba `ValueError`
    (rangos, solapes) y hay llamadores y tests que lo esperan. Heredar conserva ese
    contrato y a la vez permite un `except` específico en el preflight del CLI.
    """


DOC_ID_INICIAL = "d01"
STAGING = "_staging"          # subcarpeta de publicación por generación (sala_maquina)
# `fullmatch` con clase ASCII explícita, NO `re.match(r"^d\d{2,}$")`: el `$` casa antes de
# un salto final, así que `"d01\n"` pasaba y reventaba como OSError DENTRO de
# `materializar` —rompiendo el «se valida antes de cualquier I/O»—; y `\d` acepta dígitos
# Unicode, con lo que `"d١٢"` pasaba y su `int()` daba 12. Medido en la revisión r1.
_DOC_ID_RE = re.compile(r"d[0-9]{2,}")


def validar_doc_id(doc_id: object, *, contexto: str = "") -> str:
    """Formato canónico del `doc_id`, validado ANTES de cualquier I/O (spec §3.1).

    No es celo: el `doc_id` es un campo del manifiesto que **edita el letrado** y que
    entra directamente en el nombre de un fichero. El slug era seguro por construcción
    mientras venía de `f"{seg:02d}"`; en cuanto lo escribe una persona, aparece el
    traversal.
    """
    sufijo = f" ({contexto})" if contexto else ""
    if not isinstance(doc_id, str) or not _DOC_ID_RE.fullmatch(doc_id):
        raise ManifestValidationError(
            f"doc_id inválido {doc_id!r}{sufijo}: debe ser d + dos o más dígitos ASCII "
            f"(p. ej. d01), sin espacios ni saltos de línea")
    return doc_id


def siguiente_doc_id(doc_id: str) -> str:
    """Acuña el siguiente `doc_id`. Ancho mínimo 2, sin tope: d99 → d100."""
    validar_doc_id(doc_id, contexto="next_doc_id")
    return f"d{int(doc_id[1:]) + 1:02d}"


def _destino_en_bundle(destino: Path, carpeta_bundle: Path) -> Path:
    """El destino final cae DENTRO de la carpeta del bundle (spec §3.1).

    No se reutiliza `sala_maquina.destino_seguro` —el equivalente contra el `case_dir`—
    porque importarlo aquí crearía un ciclo: `sala_maquina` ya importa este módulo.

    Lo que NO hace, medido: con el prefijo `parent_slug__` delante, un `doc_id` como
    `..\\..\\fuera` resuelve DENTRO de la carpeta (el prefijo absorbe el primer `..`), así
    que a esa forma la para el formato canónico, no esta comprobación. Aquí se cazan las
    que de verdad escapan (`d01/../../fuera`).
    """
    destino, carpeta_bundle = Path(destino), Path(carpeta_bundle)
    try:
        destino.resolve().relative_to(carpeta_bundle.resolve())
    except ValueError:
        raise ManifestValidationError(
            f"destino fuera de la carpeta del bundle: {destino} (bundle: {carpeta_bundle})")
    return destino

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
    doc_id: str = ""      # identidad persistente del documento lógico (vacío = suelto)


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
    """Manifiesto propuesto por `plan`, ya con identidad acuñada y ledger abierto."""
    entradas: list[dict] = []
    doc_id = DOC_ID_INICIAL
    for s in segmentos:
        entradas.append({"seg": s.seg, "doc_id": doc_id,
                         "pp": _pp(s.pagina_inicio, s.pagina_fin),
                         "tipo": s.tipo, "role": s.role})
        doc_id = siguiente_doc_id(doc_id)
    return {
        "fuente": bundle_rel_path,
        "bundle_sha256": bundle_sha256,
        "segmentos": entradas,
        "delimitadores": sorted(blancos),
        "next_doc_id": doc_id,     # high-water mark: nunca decrece (spec §3.2)
        "retirados": [],           # tombstones: un doc_id de baja no se reutiliza
    }


def escribir_manifiesto(carpeta_bundle: Path, manifiesto: dict) -> None:
    """Escribe el manifiesto como JSON (editable por el letrado) + espejo Markdown legible."""
    carpeta_bundle = Path(carpeta_bundle)
    carpeta_bundle.mkdir(parents=True, exist_ok=True)
    (carpeta_bundle / _MANIFIESTO_JSON).write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    lineas = [
        "<!-- GENERADO — editable: ajusta pp/tipo/role y re-ejecuta apply -->",
        "<!-- NO toques `doc_id`: es la identidad persistente del documento lógico. "
        "Cambiarlo o intercambiarlo entre filas aborta la corrida. -->",
        f"# Segmentación propuesta — {manifiesto['fuente']}",
        "",
        "| seg | doc_id | páginas | tipo | role |",
        "|---|---|---|---|---|",
    ]
    for e in manifiesto["segmentos"]:
        lineas.append(f"| {e['seg']} | {e.get('doc_id', '')} | {e['pp']} | "
                      f"{e['tipo']} | {e['role']} |")
    lineas += ["", f"Delimitadores (hojas en blanco descartadas): {manifiesto['delimitadores']}", ""]
    (carpeta_bundle / _MANIFIESTO_MD).write_text("\n".join(lineas) + "\n", encoding="utf-8")


def leer_manifiesto(carpeta_bundle: Path) -> dict:
    """Lee de vuelta el manifiesto JSON (tras la edición del letrado, para `apply`)."""
    return json.loads((Path(carpeta_bundle) / _MANIFIESTO_JSON).read_text(encoding="utf-8"))


def manifiesto_existe(carpeta_bundle: Path) -> bool:
    """True si ya hay un manifiesto escrito en `carpeta_bundle` (idempotencia de `plan`)."""
    return (Path(carpeta_bundle) / _MANIFIESTO_JSON).exists()


def _solapa(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _next_doc_id_de(manifiesto: dict) -> str:
    """`next_doc_id` del manifiesto, o el que le correspondería si no lo trae (legacy)."""
    declarado = manifiesto.get("next_doc_id")
    if isinstance(declarado, str) and _DOC_ID_RE.fullmatch(declarado):
        return declarado
    usados = [e["doc_id"] for e in manifiesto.get("segmentos", []) if e.get("doc_id")]
    usados += list(manifiesto.get("retirados") or [])
    if not usados:
        return DOC_ID_INICIAL
    return siguiente_doc_id(max(usados, key=lambda d: int(d[1:])))


def validar_identidad(manifiesto: dict, *, exigir_doc_id: bool = True) -> None:
    """Formato, unicidad, tombstones y high-water mark del ledger (spec §3.1-§3.2).

    `exigir_doc_id=False` para el manifiesto PREVIO en una reconciliación: bajo `--force`
    un esquema viejo no bloquea (sus entradas simplemente no tienen identidad que heredar).
    """
    fuente = manifiesto.get("fuente", "?")
    vistos: set[str] = set()
    retirados = set(manifiesto.get("retirados") or [])
    if not manifiesto.get("segmentos"):
        # Con la lista vacía pasaban las dos validaciones, `materializar` devolvía [], el
        # barrido de la publicación archivaba TODOS los PDF del bundle, no se publicaba
        # nada y la corrida salía 0. Un bundle sin documentos lógicos no es un estado
        # válido (hallazgo H-11 de la revisión r1).
        raise ManifestValidationError(
            f"el manifiesto de {fuente} no declara ni un segmento: un bundle tiene al "
            f"menos un segmento (con la lista vacía se archivaría el bundle entero)")
    for e in manifiesto["segmentos"]:
        if "doc_id" not in e:
            if not exigir_doc_id:
                continue
            raise ManifestValidationError(
                f"manifiesto sin `doc_id` (esquema anterior a la identidad persistente) "
                f"en {fuente}, seg={e.get('seg')}: requiere el retrofit de la pieza B "
                f"(spec 2026-08-01-identidad-segmento-bundle §11). Salidas disponibles "
                f"hoy: `apply --force` sobre el caso, o borrar este `_segmentacion.json` "
                f"y lanzar `apply --solo` sobre el documento. No se acuñan identidades en "
                f"silencio: si un --force histórico renumeró, el segNN del artefacto "
                f"puede no representar el pp actual.")
        did = validar_doc_id(e["doc_id"], contexto=f"{fuente}, seg={e.get('seg')}")
        if did in vistos:
            raise ManifestValidationError(f"doc_id repetido en {fuente}: {did}")
        if did in retirados:
            raise ManifestValidationError(
                f"doc_id {did} está en `retirados` (dado de baja) en {fuente} y no puede "
                f"volver a usarse: el ledger es monotónico.")
        vistos.add(did)
    nxt = _next_doc_id_de(manifiesto)
    validar_doc_id(nxt, contexto=f"next_doc_id de {fuente}")
    tope = max((int(d[1:]) for d in vistos | retirados), default=-1)
    if tope >= int(nxt[1:]):
        raise ManifestValidationError(
            f"next_doc_id ({nxt}) no es un high-water mark en {fuente}: hay doc_id ≥ él")


def validar_edicion(manifiesto: dict, baseline: dict[str, str]) -> None:
    """La correspondencia `doc_id → pp` ya establecida no se reasigna a mano (spec §3.3).

    `baseline`: mapa `doc_id → pp` de la última materialización (filas de cobertura del
    bundle). Sin baseline —primera corrida, o caso legacy sin `_cobertura.json`— no hay
    nada contra qué comparar y la comprobación NO corre: se declara, no se finge.

    Editar el `pp` de un doc_id a un rango nuevo es legítimo (el manifiesto es el gate del
    letrado). Lo que se rechaza es la PERMUTACIÓN: mismo conjunto de rangos, distinta
    correspondencia, que cruza dos identidades semánticas sin que nada lo delate.
    """
    if not baseline:
        return
    actual = {e["doc_id"]: e["pp"] for e in manifiesto.get("segmentos", [])
              if e.get("doc_id")}
    comunes = sorted(set(actual) & set(baseline))
    if not comunes:
        return
    if {_pp_a_rango(actual[d]) for d in comunes} != {_pp_a_rango(baseline[d]) for d in comunes}:
        return          # el conjunto de rangos cambió: re-segmentación, permitida
    cruzados = [d for d in comunes if _pp_a_rango(actual[d]) != _pp_a_rango(baseline[d])]
    if cruzados:
        raise ManifestValidationError(
            f"permutación de identidades en {manifiesto.get('fuente', '?')}: los doc_id "
            f"{cruzados} han intercambiado su rango de páginas sin que cambie el conjunto "
            f"de rangos. Si querías re-segmentar, cambia los `pp`; renombrar no se hace "
            f"a mano.")


def validar_manifiesto(manifiesto: dict, total_pag: int) -> None:
    """Rangos y solapes (como siempre) Y la identidad (spec §3).

    Los rangos van PRIMERO a propósito: sus mensajes son los que ya conocen los llamadores
    y los tests, y un manifiesto con rango imposible es un error más básico que uno con
    identidad mal puesta.
    """
    ultimo_fin = 0
    for e in sorted(manifiesto["segmentos"], key=lambda x: _pp_a_rango(x["pp"])[0]):
        ini, fin = _pp_a_rango(e["pp"])
        if ini < 1 or fin > total_pag or fin < ini:
            raise ValueError(f"Segmento {e['seg']} fuera de rango: {e['pp']} (total {total_pag})")
        if ini <= ultimo_fin:
            raise ValueError(f"Segmento {e['seg']} solapa con el anterior: {e['pp']}")
        ultimo_fin = fin
    validar_identidad(manifiesto)


@dataclass
class Reconciliacion:
    manifiesto: dict
    heredados: list[str]       # doc_id que conservan identidad
    acunados: list[str]        # doc_id nuevos
    retirados: list[dict]      # entradas ANTERIORES dadas de baja (doc_id + tipo, para archivar)
    legacy_sin_identidad: list[str] = field(default_factory=list)  # `pp` previos sin doc_id


def reconciliar_manifiesto(previo: dict | None, propuesto: dict) -> Reconciliacion:
    """`--force` RECONCILIA el manifiesto en vez de sustituirlo (spec §5).

    1. `pp` idéntico → hereda el doc_id (el caso real: re-OCR sin cambiar segmentación).
    2. Sin igualdad y sin solape → acuña del `next_doc_id`.
    3. Sin igualdad pero con solape → se detiene: no hay emparejamiento difuso.
    4. Entrada anterior sin pareja → tombstone + sus artefactos se archivan (el llamador).

    Lo que esto NO promete (hallazgo N-A-3): un split o merge real de límites no conserva
    ninguna identidad, porque ningún rango nuevo iguala al viejo. Es correcto: el
    documento lógico cambió.
    """
    if previo is None:
        return Reconciliacion(dict(propuesto), [],
                              [e["doc_id"] for e in propuesto["segmentos"]], [])

    validar_identidad(previo, exigir_doc_id=False)
    # Indexado por RANGO, no por la cadena `pp`: el manifiesto lo edita una persona, y
    # `01-03` o `1 - 3` son el mismo rango que `1-3`. Con el índice por cadena la herencia
    # fallaba y `--force` abortaba diciendo que un rango «solapa» consigo mismo, sin salida
    # salvo editar el fichero a mano (hallazgo H-06).
    por_pp = {_pp_a_rango(e["pp"]): e for e in previo.get("segmentos", []) if e.get("doc_id")}
    # Las entradas legacy (sin doc_id) no tienen identidad que heredar: sus segmentos
    # acuñarán una nueva. Correcto, pero se DECLARA (H-07) — hacerlo callando contradice
    # el fail-closed que justifica abortar en la corrida normal.
    legacy = [e["pp"] for e in previo.get("segmentos", []) if not e.get("doc_id")]
    next_id = _next_doc_id_de(previo)

    entradas: list[dict] = []
    heredados: list[str] = []
    acunados: list[str] = []
    usados: set[tuple[int, int]] = set()
    for e in propuesto["segmentos"]:
        rango = _pp_a_rango(e["pp"])
        anterior = por_pp.get(rango)
        if anterior is not None:
            did = anterior["doc_id"]
            heredados.append(did)
            usados.add(rango)
        else:
            chocan = sorted(p for p in por_pp if _solapa(rango, p))
            if chocan:
                raise ManifestValidationError(
                    f"reconciliación imposible en {propuesto.get('fuente', '?')}: el "
                    f"segmento {e['pp']} no iguala ninguna entrada anterior y solapa con "
                    f"{[f'{a}-{b}' for a, b in chocan]}. --force se detiene: reconcilia "
                    f"_segmentacion.json a mano (ajusta los pp o retira las entradas "
                    f"viejas) y vuelve a lanzar.")
            did = next_id
            next_id = siguiente_doc_id(next_id)
            acunados.append(did)
        entradas.append({**e, "doc_id": did})

    retirados_entradas = [e for rango, e in sorted(por_pp.items()) if rango not in usados]
    manifiesto = {**propuesto, "segmentos": entradas, "next_doc_id": next_id,
                  "retirados": list(previo.get("retirados") or [])
                  + [e["doc_id"] for e in retirados_entradas]}
    return Reconciliacion(manifiesto, heredados, acunados, retirados_entradas, legacy)


def _norm_tipo(tipo: str) -> str:
    """TIPO en MAYÚSCULAS y path-safe. NO usa slugify (lleva lowercase=True y
    machacaría el case): decisión D5 de la validación 2026-07-15. Colapsa cualquier
    char no [A-Z0-9] a '_'; vacío → 'DOCUMENTO'."""
    return re.sub(r"[^A-Z0-9]+", "_", (tipo or "").upper()).strip("_") or "DOCUMENTO"


def _slug_seg(parent_slug: str, doc_id: str, tipo: str) -> str:
    """Nombre del segmento por IDENTIDAD, no por contenido.

    `parent_slug` ya viene de `output_slug` (path-safe) y `TIPO` de `_norm_tipo`
    (mayúsculas, NO slugify: bajaría el case — decisión D5 de 2026-07-15). El sha del
    segmento sale del nombre: sigue en la cobertura como cadena de custodia.
    """
    validar_doc_id(doc_id, contexto=f"segmento de {parent_slug}")
    return f"{parent_slug}__{doc_id}_{_norm_tipo(tipo)}"


def materializar(pdf_path: Path, manifiesto: dict, carpeta_bundle: Path, *,
                 parent_slug: str, parent_sha256: str, bundle_rel_path: str,
                 carpeta_salida: Path | None = None,
                 log: logging.Logger | None = None) -> list[DocLogico]:
    """Corta el bundle según el manifiesto → PDFs + `DocLogico` por documento lógico.

    Reutiliza separar.separar_pdf (cortador atómico Windows-safe) y separar.generar_indice.
    Renombra cada PDF a {slug}.pdf, con el slug derivado del `doc_id` (identidad estable).

    `carpeta_salida` (default: la propia `carpeta_bundle`) es dónde aterrizan los PDFs y
    el `indice.json`; `sala_maquina` la apunta al *staging* para publicar por generación.
    La contención se valida SIEMPRE contra `carpeta_bundle`, que es la frontera real.
    """
    log = log or _LOG
    pdf_path = Path(pdf_path)
    carpeta_bundle = Path(carpeta_bundle)
    carpeta_salida = Path(carpeta_salida) if carpeta_salida else carpeta_bundle

    # Validación COMPLETA antes de tocar disco (ni mkdir): un doc_id no canónico no puede
    # llegar a formar parte de una ruta que se escriba.
    slugs = []
    for e in manifiesto["segmentos"]:
        slug = _slug_seg(parent_slug, e.get("doc_id"), e["tipo"])
        _destino_en_bundle(carpeta_salida / f"{slug}.pdf", carpeta_bundle)
        slugs.append(slug)

    carpeta_salida.mkdir(parents=True, exist_ok=True)

    segs_sep = []
    for e in manifiesto["segmentos"]:
        ini, fin = _pp_a_rango(e["pp"])
        segs_sep.append({"tipo": e["tipo"], "num_doc": e["seg"],
                         "pagina_inicio": ini, "pagina_fin": fin, "lineas_inicio": []})

    resultados = separar.separar_pdf(pdf_path, segs_sep, carpeta_salida, log)

    docs: list[DocLogico] = []
    for e, r, slug in zip(manifiesto["segmentos"], resultados, slugs):
        emitido = carpeta_salida / r["archivo"]
        destino_pdf = carpeta_salida / f"{slug}.pdf"
        emitido.replace(destino_pdf)          # renombrar a identidad persistente
        seg_sha = file_sha256(destino_pdf)    # custodia: el sha se mide, ya no nombra
        r["archivo"] = f"{slug}.pdf"   # que generar_indice registre el nombre final, no el temporal de separar_pdf
        docs.append(DocLogico(
            slug=slug, seg_sha256=seg_sha, destino="split", tipo=e["tipo"],
            parent_slug=parent_slug, parent_sha256=parent_sha256,
            role_in_bundle=e.get("role", "documento"), paginas=r["paginas"],
            fuentes=[bundle_rel_path], doc_id=e["doc_id"],
        ))
    separar.generar_indice(resultados, pdf_path, carpeta_salida, log)
    return docs
