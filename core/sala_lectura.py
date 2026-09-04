"""[DEPRECADO 2026-06-18] El camino de sala de lectura del motor (clasificar_caso/
aplicar_clasificacion/render_indices/poblar_sala_lectura/clasificar_residuo_llm) queda
SUPERSEDIDO por la skill `organizar-sala-lectura` (sala única plana sobre todo 00_Input;
ver docs/superpowers/specs/2026-06-18-sala-lectura-unica-design.md). No ampliar; se
conserva temporalmente. El pipeline confidencial (extractor/MD/anon) NO depende de esto.

---

Sala de lectura de 01_Procesado (F4–F6).

Clasificador/fechador híbrido + copiador organizado + render de índices.
El catálogo `indice_documental.yaml` es la única fuente de verdad. El residuo
ambiguo del clasificador se vuelca a `01_Procesado/_revisar/_clasificar.md`
(worklist) que Claude rellena en sesión leyendo los `MD/` en claro.

Excepción RGPD temporal autorizada por Nikolai (spec
2026-06-17-sala-lectura-f4f6-design.md §2).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable

from core import catalogo_documental
from core.config import TAXONOMIA_EV, UMBRAL_CONFIANZA_AUTOMOVE, caso_path
from core.conjunto_detector import detect_bundles
from core.local_organizer import _exif_o_mtime, _sanitize
from core.utils import now_iso, output_slug, slugify

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
        "leyendo `01_Procesado/02_Sala de máquina/03_MD/<slug>.md`. No toques **Hash**.",
        "> Tipos válidos: " + " · ".join(TAXONOMIA_EV),
        "",
        "| " + " | ".join(_WL_COLS) + " |",
        "|" + "|".join(["---"] * len(_WL_COLS)) + "|",
    ]
    # **Fusiona, no reconstruye** (`MEJORAS #151`). Hasta el 2026-09-04 esto escribia las
    # columnas en blanco, asi que el ciclo que el propio CLI recomienda —«rellena la
    # worklist y vuelve a correr organizar»— DESTRUIA lo rellenado: medido, 99 filas
    # clasificadas a mano perdidas en la corrida siguiente, y el `aplicar` posterior
    # devolvio «Aplicadas: 0». Se preserva toda celda no vacia, sea del letrado o de una
    # corrida previa del clasificador LLM, que es la misma politica que `rellenar_worklist`.
    previas = {f["Hash"]: f for f in _filas_worklist(case_id)}
    for e in residuo:
        fecha, _ = _fecha_de(case_id, e)
        prev = previas.get(e.hash, {})
        fila = [e.hash, _celda(e.nombre_original), _celda(e.fuente),
                prev.get("Tipo", ""),
                prev.get("Fecha") or (fecha or ""),
                prev.get("Parte", ""),
                prev.get("Descripcion", "")]
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


# ---------------------------------------------------------------------------
# MEJORAS #37: clasificar_residuo_llm — autorrelleno LLM de la worklist del residuo
#
# Opera SOLO sobre el residuo (filas de `_clasificar.md` SIN Tipo). Lee el texto
# extraído en claro de `01_Procesado/02_Sala de máquina/03_MD/` y autorrellena las columnas
# vacías (Tipo, Fecha, Parte, Descripcion). NO pisa celdas ya rellenas (por humano
# o por una corrida previa) → idempotente y respeta lo ya clasificado. Lo de baja
# confianza se deja sin rellenar (sigue en residuo), no se adivina.
# `aplicar_clasificacion` sigue siendo el ÚNICO camino al catálogo canónico.
#
# Modo de operación por defecto (decisión de Nikolai, 2026-06-18): Claude-en-sesión
# resuelve el residuo bajo la excepción RGPD §2 (spec 2026-06-17-sala-lectura-f4f6),
# SIN coste de API externa: `preparar_residuo` reúne el material, Claude lo clasifica
# y escribe con `rellenar_worklist`. El parámetro `chat_fn` de `clasificar_residuo_llm`
# es el camino de conector programático (p. ej. `make_llm_cloud_chat_fn` sobre
# `core/llm_cloud.py`), OPT-IN y reservado al futuro DPA: no hay default que llame a
# un API de pago.
# ---------------------------------------------------------------------------

# Columnas de la worklist que el LLM puede autorrellenar.
_COLS_LLM = ("Tipo", "Fecha", "Parte", "Descripcion")
_PARTES_VALIDAS = {"propietario", "buscador", "tercero"}


#: Subruta del directorio donde la **sala de máquina** escribe los espejos MD. Hasta el
#: 2026-09-04 esto decía `01_Procesado/MD/`, que es la salida del motor documental
#: JUBILADO, y por eso `preparar_residuo` respondía «nada que preparar» con 99 documentos
#: en residuo y 176 espejos en disco, y los 140 enlaces «ver texto» del `INDICE.md` salían
#: muertos (`MEJORAS #151`). Se declara una vez: los dos sitios que construían la ruta
#: —absoluta para leer, relativa para el enlace— la duplicaban sin saberlo.
_MD_SUBDIR = ("01_Procesado", "02_Sala de máquina", "03_MD")


def _md_dir(case_id: str) -> Path:
    return caso_path(case_id).joinpath(*_MD_SUBDIR)


def _md_path(case_id: str, entry) -> Path:
    """Ruta CANÓNICA del espejo MD de un documento, según la sala de máquina."""
    return _md_dir(case_id) / f"{output_slug(entry.ruta_relativa, entry.hash)}.md"


def _md_paths(case_id: str, entry) -> list[Path]:
    """Los espejos MD del documento: el canónico, o los de sus segmentos si se partió.

    Cuando el split de la sala de máquina parte un PDF compuesto, **el padre no tiene
    espejo propio**: su texto vive en `<slug>__d01_TIPO.md`, `<slug>__d02_TIPO.md`… Medido
    el 2026-09-04 sobre los 99 documentos de residuo de W-02JSVZ: **88 casaban** por el
    nombre canónico y **11 no**, y los 11 eran bundles partidos. Apuntar solo el
    directorio nuevo dejaba fuera a esos once, así que el arreglo tiene dos piezas.
    """
    canon = _md_path(case_id, entry)
    if canon.is_file():
        return [canon]
    slug = output_slug(entry.ruta_relativa, entry.hash)
    return sorted(_md_dir(case_id).glob(f"{slug}__d*.md"))


def _filas_worklist(case_id: str) -> list[dict]:
    try:
        path = _revisar_dir(case_id) / WORKLIST_NAME
    except FileNotFoundError:
        return []                      # el caso no existe
    if not path.exists():
        return []                      # el caso existe, la worklist no
    return _parse_worklist(path.read_text(encoding="utf-8"))


def _hashes_residuo(case_id: str) -> list[str]:
    """Hashes de las filas del worklist SIN Tipo (residuo aún sin resolver)."""
    return [f["Hash"] for f in _filas_worklist(case_id) if not f["Tipo"].strip()]


def preparar_residuo(case_id: str) -> list[dict]:
    """Reúne el material del residuo para clasificarlo (Claude-en-sesión o conector).

    Devuelve, por cada doc del residuo CON texto legible, un dict:
    ``{hash, nombre_original, fuente, fecha_pista, md_text, md_path}``. Omite los
    que no tienen `.md` extraído (no se clasifica lo que no se ve). Este es el
    material que Claude-en-sesión lee para rellenar la worklist sin API de pago.
    """
    residuo = set(_hashes_residuo(case_id))
    if not residuo:
        return []
    by_hash = {e.hash: e for e in catalogo_documental.load_catalog(case_id)}
    pistas = {f["Hash"]: f["Fecha"].strip() for f in _filas_worklist(case_id)}
    out: list[dict] = []
    for h in residuo:
        e = by_hash.get(h)
        if not e:
            continue
        mds = _md_paths(case_id, e)
        if not mds:
            continue
        out.append({
            "hash": h,
            "nombre_original": e.nombre_original,
            "fuente": e.fuente,
            "fecha_pista": pistas.get(h, ""),
            # Un bundle partido aporta VARIOS segmentos: se concatenan con su nombre
            # delante, porque clasificar un documento compuesto por un solo segmento es
            # justo el error que el split existe para evitar.
            "md_text": "\n\n".join(
                f"<!-- {p.name} -->\n{p.read_text(encoding='utf-8', errors='replace')}"
                for p in mds),
            "md_path": str(mds[0]),
            "md_paths": [str(p) for p in mds],
        })
    return out


def _es_fila_datos(celdas: list[str]) -> bool:
    return (len(celdas) == len(_WL_COLS)
            and celdas[0] != "Hash"
            and not set(celdas[0]) <= {"-"})


def rellenar_worklist(
    case_id: str,
    clasificaciones: dict[str, dict],
    *,
    umbral: float = UMBRAL_CONFIANZA_AUTOMOVE,
) -> dict:
    """Vuelca clasificaciones a las celdas VACÍAS de la worklist, por hash.

    `clasificaciones`: ``{hash: {Tipo, Fecha, Parte, Descripcion, confianza}}``.
    No pisa celdas ya rellenas (humano o corrida previa) → idempotente. Una fila
    con ``confianza < umbral`` se deja intacta (sigue en residuo). Por celda valida:
    Tipo ∈ ``TAXONOMIA_EV`` y Parte ∈ {propietario, buscador, tercero}; lo que no
    valide se deja en blanco (revisión humana), nunca se adivina.
    Devuelve ``{n_filas_tocadas, n_celdas, n_baja_confianza}``.
    """
    path = _revisar_dir(case_id) / WORKLIST_NAME
    if not path.exists():
        return {"n_filas_tocadas": 0, "n_celdas": 0, "n_baja_confianza": 0}
    lineas = path.read_text(encoding="utf-8").splitlines()
    col_idx = {c: i for i, c in enumerate(_WL_COLS)}
    n_filas = n_celdas = n_baja = 0
    for li, line in enumerate(lineas):
        s = line.strip()
        if not s.startswith("|"):
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        if not _es_fila_datos(celdas):
            continue
        cl = clasificaciones.get(celdas[col_idx["Hash"]])
        if not cl:
            continue
        try:
            conf = float(cl.get("confianza", 0) or 0)
        except (TypeError, ValueError):
            conf = 0.0
        if conf < umbral:
            n_baja += 1
            continue
        tocada = False
        for col in _COLS_LLM:
            val = _celda(cl.get(col))
            if not val:
                continue
            if col == "Tipo" and val not in TAXONOMIA_EV:
                continue
            if col == "Parte" and val.lower() not in _PARTES_VALIDAS:
                continue
            idx = col_idx[col]
            if celdas[idx]:  # ya rellena → no pisar
                continue
            celdas[idx] = val
            n_celdas += 1
            tocada = True
        if tocada:
            n_filas += 1
            lineas[li] = "| " + " | ".join(celdas) + " |"
    texto = "\n".join(lineas)
    if not texto.endswith("\n"):
        texto += "\n"
    path.write_text(texto, encoding="utf-8")
    return {"n_filas_tocadas": n_filas, "n_celdas": n_celdas,
            "n_baja_confianza": n_baja}


def clasificar_residuo_llm(
    case_id: str,
    *,
    chat_fn: "Callable[[dict], dict] | None" = None,
    umbral: float = UMBRAL_CONFIANZA_AUTOMOVE,
) -> dict:
    """Autorrellena la worklist del residuo con un clasificador LLM inyectado.

    ``chat_fn(doc) -> dict`` recibe ``{hash, nombre_original, fuente, fecha_pista,
    md_text, md_path}`` y devuelve ``{tipo, fecha, parte, descripcion, confianza}``.
    Es OBLIGATORIO: no hay default que llame a un API de pago (decisión de Nikolai,
    2026-06-18). El modo por defecto del despacho es Claude-en-sesión vía
    ``preparar_residuo`` + ``rellenar_worklist`` (sin coste). Para el conector
    programático (futuro DPA) usar ``make_llm_cloud_chat_fn()``.

    Solo rellena celdas vacías de las filas del residuo; no pisa lo ya clasificado;
    baja confianza se deja sin rellenar. No toca la clasificación determinista ni el
    esquema de la worklist; `aplicar_clasificacion` sigue siendo el único camino al
    catálogo.
    """
    if chat_fn is None:
        raise ValueError(
            "clasificar_residuo_llm requiere chat_fn (callable). El modo por "
            "defecto es Claude-en-sesión vía preparar_residuo + rellenar_worklist, "
            "sin API de pago. Para el conector programático usa make_llm_cloud_chat_fn()."
        )
    docs = preparar_residuo(case_id)
    n_residuo = len(_hashes_residuo(case_id))
    clasif: dict[str, dict] = {}
    for doc in docs:
        raw = chat_fn(doc) or {}
        clasif[doc["hash"]] = {
            "Tipo": raw.get("tipo") or "",
            "Fecha": raw.get("fecha") or "",
            "Parte": raw.get("parte") or "",
            "Descripcion": raw.get("descripcion") or "",
            "confianza": raw.get("confianza", 0),
        }
    res = rellenar_worklist(case_id, clasif, umbral=umbral)
    res.update({"case_id": case_id, "n_docs": len(docs),
                "n_sin_texto": max(0, n_residuo - len(docs))})
    return res


# Esquema y prompt del conector programático (OPT-IN; futuro DPA, no es el default).
_SCHEMA_RESIDUO: dict = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": list(TAXONOMIA_EV)},
        "fecha": {"type": "string"},
        "parte": {"type": "string", "enum": ["propietario", "buscador", "tercero", ""]},
        "descripcion": {"type": "string"},
        "confianza": {"type": "number"},
    },
    "required": ["tipo", "confianza"],
}


def _sistema_clasifica_residuo() -> str:
    return (
        "Eres un clasificador documental de un despacho de abogados. Clasificas un "
        "documento de un expediente inmobiliario LEYENDO SOLO el texto que se te da. "
        "NO inventes: si el texto no permite decidir con seguridad, baja la confianza.\n\n"
        "Devuelve SOLO JSON con estas claves:\n"
        "- tipo: exactamente uno de la taxonomía: " + " · ".join(TAXONOMIA_EV) + "\n"
        "- fecha: fecha del documento en formato YYYY-MM-DD si aparece en el texto; "
        "si no, cadena vacía.\n"
        "- parte: 'propietario', 'buscador' o 'tercero' según a quién se refiera el "
        "documento; cadena vacía si no se deduce.\n"
        "- descripcion: descripción funcional neutra, máx. 60 caracteres, sin datos "
        "personales.\n"
        "- confianza: número 0–1. Usa < 0.8 cuando no estés seguro (se dejará sin "
        "clasificar para revisión humana).\n\n"
        "Responde SOLO con el JSON, sin texto adicional."
    )


def make_llm_cloud_chat_fn(*, llm_config=None, max_chars: int = 6000):
    """Adaptador OPT-IN sobre ``core/llm_cloud.py`` (conector programático).

    Devuelve un ``chat_fn`` para `clasificar_residuo_llm` que clasifica vía la API
    cloud (Scaleway/Mistral por defecto). Reservado al futuro DPA: implica enviar el
    texto en claro a un proveedor externo y, por tanto, coste y tratamiento sujeto a
    contrato. El modo por defecto del despacho NO usa esto (Claude-en-sesión).
    """
    from core.llm_cloud import chat_json  # import perezoso: no forzar httpx en el flujo Claude-en-sesión

    def _chat_fn(doc: dict) -> dict:
        texto = (doc.get("md_text") or "")[:max_chars]
        user = (
            f"Nombre de fichero: {doc.get('nombre_original')}\n"
            f"Fuente: {doc.get('fuente')}\n"
            f"Pista de fecha (del nombre/metadato): {doc.get('fecha_pista') or '(ninguna)'}\n\n"
            f"Texto extraído del documento:\n{texto}"
        )
        messages = [
            {"role": "system", "content": _sistema_clasifica_residuo()},
            {"role": "user", "content": user},
        ]
        return chat_json(messages, config=llm_config, temperature=0.0,
                         json_schema=_SCHEMA_RESIDUO)

    return _chat_fn


# ---------------------------------------------------------------------------
# Task 7: render_indices — INDICE.md por fuente→tipo + CRONOLOGIA.md por fecha
# ---------------------------------------------------------------------------

_SALA = "Sala lectura"
FUENTE_LABEL = {
    "drive_ev": "Drive E&V", "crm": "CRM", "whatsapp": "WhatsApp",
    "entrevista": "Entrevistas", "email": "Email", "manual": "Manual",
}
_CABECERA_RO = (
    "<!-- GENERADO AUTOMÁTICAMENTE — NO EDITAR A MANO. "
    "Se regenera desde indice_documental.yaml. -->"
)


def _sala_dir(case_id: str) -> Path:
    return caso_path(case_id) / "01_Procesado" / _SALA


def _link_original(e) -> str:
    # Enlace relativo desde Sala lectura/ al original en 00_Input/.
    return f"../../00_Input/{e.ruta_relativa}"


def _link_md(e) -> str | None:
    """Enlace «ver texto» del índice, relativo a `01_Procesado/Sala lectura/INDICE.md`.

    Apuntaba a `../MD/` —el motor jubilado—, así que los enlaces salían muertos: 140 de
    140 en W-02JSVZ (`MEJORAS #151`). Comparte el directorio con `_md_dir` vía
    `_MD_SUBDIR` para que no vuelvan a divergir; se salta el primer segmento
    (`01_Procesado`), que es el padre del propio índice.
    """
    if Path(e.nombre_original).suffix.lower() == ".md":
        return None
    subdir = "/".join(_MD_SUBDIR[1:])
    return f"../{subdir}/{output_slug(e.ruta_relativa, e.hash)}.md"


def render_indices(case_id: str) -> list[Path]:
    entries = catalogo_documental.load_catalog(case_id)
    out = _sala_dir(case_id)
    out.mkdir(parents=True, exist_ok=True)

    # --- INDICE.md: por fuente -> tipo ---
    por_fuente: dict[str, list] = {}
    for e in entries:
        por_fuente.setdefault(e.fuente, []).append(e)
    li = [_CABECERA_RO, "", f"# Índice del expediente — {case_id}", "",
          f"Generado: {now_iso()}.", ""]
    for fuente in sorted(por_fuente):
        li.append(f"## {FUENTE_LABEL.get(fuente, fuente)}")
        li.append("")
        por_tipo: dict[str, list] = {}
        for e in por_fuente[fuente]:
            por_tipo.setdefault(e.tipo_documental or "Sin clasificar", []).append(e)
        for tipo in sorted(por_tipo):
            li.append(f"### {tipo}")
            for e in sorted(por_tipo[tipo], key=lambda x: (x.fecha_doc or "", x.nombre_original)):
                md = _link_md(e)
                ver_texto = f" · [ver texto]({md})" if md else ""
                fecha = e.fecha_doc or "s/f"
                li.append(f"- {fecha} — [{e.nombre_original}]({_link_original(e)}){ver_texto}")
            li.append("")
    indice = out / "INDICE.md"
    indice.write_text("\n".join(li), encoding="utf-8")

    # --- CRONOLOGIA.md: por fecha ascendente, sin fecha al final ---
    lc = [_CABECERA_RO, "", f"# Cronología — {case_id}", "",
          f"Generado: {now_iso()}.", "",
          "| Fecha | Fuente | Tipo | Documento |", "|---|---|---|---|"]

    def _key(e):
        return (e.fecha_doc is None, e.fecha_doc or "", e.nombre_original)

    for e in sorted(entries, key=_key):
        lc.append(
            f"| {e.fecha_doc or 's/f'} | {FUENTE_LABEL.get(e.fuente, e.fuente)} "
            f"| {e.tipo_documental or 'Sin clasificar'} "
            f"| [{e.nombre_original}]({_link_original(e)}) |"
        )
    lc.append("")
    crono = out / "CRONOLOGIA.md"
    crono.write_text("\n".join(lc), encoding="utf-8")
    return [indice, crono]


# ---------------------------------------------------------------------------
# Task 8: _nombre_canonico — nombre normalizado fecha_tipo_descripcion
# ---------------------------------------------------------------------------

_TIPO_SLUG = {
    "00. FOTOS": "foto",
    "01. ACTIVACIÓN": "activacion",
    "03. OFERTAS": "oferta",
    "04. ARRAS - ARRENDAMIENTOS": "arras",
    "05. FACTURACIÓN - FINANZAS": "factura",
    "06. PBC": "pbc",
    "07. RECLAMACIONES": "reclamacion",
    "08. PENDIENTE DE CLASIFICAR": "pendiente",
}


def _nombre_canonico(entry) -> str:
    ext = Path(entry.nombre_original).suffix.lower()
    fecha = entry.fecha_doc or "0000-00-00"
    tipo = _TIPO_SLUG.get(entry.tipo_documental or "", "doc")
    desc_src = entry.descripcion or Path(entry.nombre_original).stem
    desc = slugify(_sanitize(desc_src), max_length=50)
    return f"{fecha}_{tipo}_{desc}{ext}"


# ---------------------------------------------------------------------------
# Task 9+10: _bundle_map + poblar_sala_lectura — copia idempotente + dedup
#            + renombrado + bundles CRM con degradación a plano
# ---------------------------------------------------------------------------


def _bundle_map(entries: list, crm_docs) -> dict:
    """Devuelve {hash: (bundle_slug, rol, header_hash, orden)} para los miembros de
    bundles CRM de alta confianza. rol in {'cabecera', 'adjunto'}. Une
    CRM<->catálogo solo contra entradas de fuente CRM. orden es el índice del
    doc_id dentro de prop.member_doc_ids (estable entre corridas)."""
    if not crm_docs:
        return {}
    by_filename = {e.nombre_original: e for e in entries if e.fuente == "crm"}
    id_to_filename = {d.doc_id: d.filename for d in crm_docs}
    out: dict = {}
    for prop in detect_bundles(crm_docs):
        if prop.confidence != "alta":
            continue
        header_id = prop.header_doc_id
        header_e = by_filename.get(id_to_filename.get(header_id, "")) if header_id else None
        slug_src = header_e.nombre_original if header_e else f"bundle-{prop.timestamp}"
        bundle_slug = slugify(_sanitize(Path(slug_src).stem), max_length=50)
        for idx, doc_id in enumerate(prop.member_doc_ids):
            e = by_filename.get(id_to_filename.get(doc_id, ""))
            if not e:
                continue
            rol = "cabecera" if doc_id == header_id else "adjunto"
            out[e.hash] = (bundle_slug, rol, header_e.hash if header_e else None, idx)
    return out


def poblar_sala_lectura(case_id: str, *, crm_docs=None) -> dict:
    entries = catalogo_documental.load_catalog(case_id)
    bundles = _bundle_map(entries, crm_docs)
    acciones: dict[str, int] = {}
    vistos_hash: set[str] = set()

    for e in entries:
        if e.hash and e.hash in vistos_hash:
            acciones["SKIP_DEDUP"] = acciones.get("SKIP_DEDUP", 0) + 1
            continue
        src = _input_path(case_id, e.ruta_relativa)
        if not src.exists():
            acciones["MISSING_SRC"] = acciones.get("MISSING_SRC", 0) + 1
            continue
        fuente_dir = FUENTE_LABEL.get(e.fuente, e.fuente)
        nombre = _nombre_canonico(e)
        e.nombre_canonico = nombre

        b = bundles.get(e.hash)
        if b:
            bundle_slug, rol, header_hash, orden = b
            if rol == "cabecera":
                dst_rel = f"{_SALA}/{fuente_dir}/{bundle_slug}/{nombre}"
                e.parent_id = None
            else:
                dst_rel = f"{_SALA}/{fuente_dir}/{bundle_slug}/adjuntos/{nombre}"
                e.parent_id = header_hash
                e.orden_en_bundle = orden
        else:
            dst_rel = f"{_SALA}/{fuente_dir}/{nombre}"

        dst = caso_path(case_id) / "01_Procesado" / dst_rel
        prev = e.ruta_sala_lectura
        if prev == dst_rel and dst.exists():
            acciones["SKIP_UNCHANGED"] = acciones.get("SKIP_UNCHANGED", 0) + 1
        else:
            if prev and prev != dst_rel:
                old = caso_path(case_id) / "01_Procesado" / prev
                if old.exists():
                    old.unlink()
                acciones["MOVED"] = acciones.get("MOVED", 0) + 1
            else:
                acciones["COPY"] = acciones.get("COPY", 0) + 1
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            e.ruta_sala_lectura = dst_rel
        if e.hash:
            vistos_hash.add(e.hash)

    catalogo_documental.save_catalog(case_id, entries)
    return {"case_id": case_id, "acciones": acciones,
            "n_bundles": len({v[0] for v in bundles.values()})}


# ---------------------------------------------------------------------------
# Task 11: organizar — orquestador F4–F6
# ---------------------------------------------------------------------------


def organizar(case_id: str, *, crm_docs=None) -> dict:
    """Orquestador: catálogo -> aplicar -> clasificar -> (parar si residuo) -> render -> poblar.

    **Le faltaban el primero y el segundo** (`MEJORAS #151`), y por eso no convergía:

    - Sin `catalogo`, sobre un caso recién abierto clasificaba un
      `indice_documental.yaml` que no existía, encontraba 0 documentos y remataba con
      «Sala de lectura organizada. Acciones: {}» — éxito sobre una sala vacía. Un
      inventario vacío que no activa nada es indistinguible de «no había nada que hacer».
      La guarda existía… en el subcomando `clasificar` del CLI, y `organizar` la rodeaba
      llamando aquí directamente.
    - Sin `aplicar`, la worklist rellenada por el letrado no llegaba nunca al catálogo,
      así que el residuo no bajaba y `organizar` volvía a pedir lo mismo para siempre.

    `aplicar` va ANTES de `clasificar` a propósito: vuelca lo rellenado con
    `confianza = 1.0`, y así `clasificar_caso` ya no lo cuenta como residuo.
    """
    if not catalogo_documental.load_catalog(case_id):
        from core import inventory
        inventory.scan(case_id)
        catalogo_documental.build_catalog(case_id)
    aplicar_clasificacion(case_id)
    clasif = clasificar_caso(case_id)
    if clasif["n_residuo"] > 0:
        return {"case_id": case_id, "detenido_por_residuo": True,
                "n_residuo": clasif["n_residuo"],
                "worklist": str(_revisar_dir(case_id) / WORKLIST_NAME)}
    render_indices(case_id)
    pob = poblar_sala_lectura(case_id, crm_docs=crm_docs)
    return {"case_id": case_id, "detenido_por_residuo": False,
            "n_residuo": 0, "acciones": pob["acciones"]}
