"""Sala de lectura de 01_Procesado (F4–F6).

Clasificador/fechador híbrido + copiador organizado + render de índices.
El catálogo `indice_documental.yaml` es la única fuente de verdad. El residuo
ambiguo del clasificador se vuelca a `01_Procesado/_revisar/_clasificar.md`
(worklist) que Claude rellena en sesión leyendo los `MD/` en claro.

Excepción RGPD temporal autorizada por Nikolai (spec
2026-06-17-sala-lectura-f4f6-design.md §2).
"""
from __future__ import annotations

import re
from pathlib import Path

from core import catalogo_documental
from core.config import TAXONOMIA_EV, UMBRAL_CONFIANZA_AUTOMOVE, caso_path
from core.local_organizer import _exif_o_mtime, _sanitize

# Categoría → tokens del nombre de fichero (orden de prioridad de la tupla).
# Las primeras que casen ganan; el orden de TAXONOMIA fija desempates.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("07. RECLAMACIONES", ("burofax", "requerimiento", "reclamacion", "reclamación", "ovc", "incumplimiento")),
    ("05. FACTURACIÓN - FINANZAS", ("factura", "honorarios", "abono", "minuta", "justificante de pago")),
    ("06. PBC", ("dni", "nie", "pasaporte", "nota simple", "titularidad", "pbc", "blanqueo")),
    ("04. ARRAS - ARRENDAMIENTOS", ("arras", "reserva", "señal", "arrendamiento", "alquiler")),
    ("03. OFERTAS", ("oferta", "contraoferta")),
    ("01. ACTIVACIÓN", ("encargo", "captacion", "captación", "exclusiva", "expose", "exposé", "hoja de visita")),
]

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tiff", ".tif"}

_FECHA_ISO_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_FECHA_DMY_RE = re.compile(r"(?<!\d)(\d{2})[-/.](\d{2})[-/.](\d{4})(?!\d)")


def _fecha_desde_nombre(nombre: str) -> tuple[str | None, str | None]:
    """Extrae fecha ISO (YYYY-MM-DD) del nombre de fichero.

    Reconoce dos patrones:
    - ISO: ``YYYY-MM-DD`` → devuelve ``(fecha, "contenido")``.
    - DMY: ``DD-MM-YYYY``, ``DD/MM/YYYY`` o ``DD.MM.YYYY`` → normaliza a ISO.

    Devuelve ``(None, None)`` si no hay patrón reconocible.
    """
    m = _FECHA_ISO_RE.search(nombre)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "contenido"
    m = _FECHA_DMY_RE.search(nombre)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}", "contenido"
    return None, None


def _es_imagen(ext: str) -> bool:
    """`ext` es el sufijo con punto (p. ej. `.jpg`), como `Path.suffix`."""
    return ext.lower() in _IMG_EXTS


def _categoria_por_nombre(nombre: str) -> str | None:
    low = nombre.lower().replace("_", " ")
    for categoria, tokens in _KEYWORDS:
        if any(t in low for t in tokens):
            return categoria
    return None


# ---------------------------------------------------------------------------
# Task 5: clasificar_caso — enriquece catálogo + worklist del residuo
# ---------------------------------------------------------------------------

CATEGORIA_FOTOS = "00. FOTOS"
WORKLIST_NAME = "_clasificar.md"
_CONF_DETERMINISTA = 0.9
_CONF_IMAGEN = 1.0

_WL_COLS = ["Hash", "Origen", "Fuente", "Tipo", "Fecha", "Parte", "Descripcion"]


def _revisar_dir(case_id: str) -> Path:
    return caso_path(case_id) / "01_Procesado" / "_revisar"


def _input_path(case_id: str, ruta_relativa: str) -> Path:
    return caso_path(case_id) / "00_Input" / ruta_relativa


def _fecha_de(case_id: str, entry) -> tuple[str | None, str]:
    fecha, fuente = _fecha_desde_nombre(entry.nombre_original)
    if fecha:
        return fecha, fuente
    src = _input_path(case_id, entry.ruta_relativa)
    if _es_imagen(Path(entry.nombre_original).suffix) and src.exists():
        f, fnt = _exif_o_mtime(src)
        return f, ("exif" if fnt == "exif" else "mtime")
    if src.exists():
        from datetime import datetime
        return datetime.fromtimestamp(src.stat().st_mtime).date().isoformat(), "mtime"
    return None, "desconocida"


def _celda(s) -> str:
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ").strip()


def _write_worklist(case_id: str, residuo: list) -> Path:
    out = _revisar_dir(case_id)
    out.mkdir(parents=True, exist_ok=True)
    path = out / WORKLIST_NAME
    lineas = [
        f"# Worklist de clasificación — {case_id}",
        "",
        "> Rellena **Tipo**, **Fecha** (YYYY-MM-DD), **Parte** "
        "(propietario/buscador/tercero) y **Descripcion** (≤60 car., sin PII) "
        "leyendo `01_Procesado/MD/<slug>.md`. No toques la columna **Hash**.",
        "> Tipos válidos: " + " · ".join(TAXONOMIA_EV),
        "",
        "| " + " | ".join(_WL_COLS) + " |",
        "|" + "|".join(["---"] * len(_WL_COLS)) + "|",
    ]
    for e in residuo:
        fecha, _ = _fecha_de(case_id, e)
        fila = [e.hash, _celda(e.nombre_original), _celda(e.fuente),
                "", fecha or "", "", ""]
        lineas.append("| " + " | ".join(fila) + " |")
    lineas.append("")
    path.write_text("\n".join(lineas), encoding="utf-8")
    return path


def clasificar_caso(case_id: str) -> dict:
    entries = catalogo_documental.load_catalog(case_id)
    residuo = []
    n_det = 0
    for e in entries:
        if e.tipo_documental and (e.confianza or 0) >= UMBRAL_CONFIANZA_AUTOMOVE:
            continue  # ya resuelto en una corrida previa
        ext = Path(e.nombre_original).suffix
        if _es_imagen(ext):
            fecha, fuente = _fecha_de(case_id, e)
            e.tipo_documental = CATEGORIA_FOTOS
            e.fecha_doc, e.fecha_fuente = fecha, fuente
            e.confianza = _CONF_IMAGEN
            e.descripcion = e.descripcion or "Fotografía"
            n_det += 1
            continue
        categoria = _categoria_por_nombre(e.nombre_original)
        if categoria:
            fecha, fuente = _fecha_de(case_id, e)
            e.tipo_documental = categoria
            e.fecha_doc, e.fecha_fuente = fecha, fuente
            e.confianza = _CONF_DETERMINISTA
            n_det += 1
            continue
        residuo.append(e)

    catalogo_documental.save_catalog(case_id, entries)
    _write_worklist(case_id, residuo)
    return {"case_id": case_id, "n_total": len(entries),
            "n_deterministas": n_det, "n_residuo": len(residuo)}


# ---------------------------------------------------------------------------
# Task 6: aplicar_clasificacion — vuelca la worklist rellena al catálogo
# ---------------------------------------------------------------------------


def _parse_worklist(text: str) -> list[dict]:
    filas = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        celdas = [c.strip() for c in line.strip("|").split("|")]
        if len(celdas) != len(_WL_COLS):
            continue
        if celdas[0] == "Hash" or set(celdas[0]) <= {"-"}:
            continue
        filas.append(dict(zip(_WL_COLS, celdas)))
    return filas


def aplicar_clasificacion(case_id: str) -> dict:
    path = _revisar_dir(case_id) / WORKLIST_NAME
    if not path.exists():
        return {"case_id": case_id, "n_aplicadas": 0}
    filas = {f["Hash"]: f for f in _parse_worklist(path.read_text(encoding="utf-8"))}
    entries = catalogo_documental.load_catalog(case_id)
    aplicadas = 0
    for e in entries:
        fila = filas.get(e.hash)
        if not fila:
            continue
        tipo = fila["Tipo"].strip()
        if tipo not in TAXONOMIA_EV:
            continue  # sin tipo válido → sigue pendiente
        e.tipo_documental = tipo
        e.fecha_doc = fila["Fecha"].strip() or e.fecha_doc
        e.fecha_fuente = e.fecha_fuente or "contenido"
        e.parte = fila["Parte"].strip() or None
        e.descripcion = fila["Descripcion"].strip() or None
        e.confianza = 1.0
        aplicadas += 1
    catalogo_documental.save_catalog(case_id, entries)
    return {"case_id": case_id, "n_aplicadas": aplicadas}
