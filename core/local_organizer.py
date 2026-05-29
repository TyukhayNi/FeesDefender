"""Organizador local del Drive E&V — Sprint 2.

Clasifica los documentos en bruto descargados del Drive de Engel & Völkers
(``00_Input/01_Drive EV/``) y produce una **vista humana navegable** en una
subcarpeta ``_organizado/`` con la taxonomía estándar del cliente: copias
renombradas, subcarpetas por subgrupo cuando procede, un ``_README.md`` por
categoría y un ``_INDICE.md`` maestro.

Garantías de diseño:

- **Cadena de custodia intacta**: nunca mueve, renombra ni borra los
  originales. La vista ``_organizado/`` son copias (``shutil.copy2``) con
  trazabilidad SHA-256 al original en ``_audit.jsonl``.
- **Frontera PII local**: toda llamada al modelo pasa por ``core.llm_local``
  (Ollama local). Ningún original ni nombre de fichero con PII sale a una API
  externa. La clasificación se hace sobre el **cuerpo anonimizado**
  (``06_Anonimizado/``); el nombre de fichero original se usa solo como pista
  contextual, y solo localmente.
- **Idempotencia**: ``ejecutar_plan`` dos veces con los mismos inputs no
  produce cambios (todo ``SKIP_UNCHANGED``).
- **Precondición de anonimización**: ``planificar`` aborta si falta
  ``06_Anonimizado/``. Documentos sin su ``.md`` anonimizado se marcan
  ``OCR_PENDIENTE`` / ``NO_ANONIMIZADO`` y van a ``08. PENDIENTE DE
  CLASIFICAR`` sin invocar al modelo.

Flujo: ``planificar`` (``--plan``) escribe la propuesta editable; el humano
revisa ``_plan_reorganizacion.md``; ``ejecutar_plan`` (``--execute``) detecta
las correcciones (loop de aprendizaje), materializa la vista y registra audit.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from core.case_manager import caso_path
from core.config import (
    ORDEN_POR_CATEGORIA,
    ORGANIZADO_SUBDIR,
    TAXONOMIA_EV,
    UMBRAL_CONFIANZA_AUTOMOVE,
    UMBRAL_VOLUMEN_SUBCARPETAS,
    settings,
)
from core.utils import file_sha256, now_iso, read_md, slugify
from core import llm_local

logger = logging.getLogger("feesdefender.local_organizer")


# ---------------------------------------------------------------------------
# Constantes de carpeta y ficheros
# ---------------------------------------------------------------------------

DRIVE_EV_SUBDIR = "01_Drive EV"
ANONIMIZADO_SUBDIR = "06_Anonimizado"
AI_COWORK_SUBDIR = "07_AI cowork"

PLAN_PROPUESTO = "_plan_propuesto.md"
PLAN_REORGANIZACION = "_plan_reorganizacion.md"
INDICE_FILE = "_INDICE.md"
AUDIT_FILE = "_audit.jsonl"
README_FILE = "_README.md"

CATEGORIA_PENDIENTE = "08. PENDIENTE DE CLASIFICAR"
CATEGORIA_FOTOS = "00. FOTOS"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tiff"}
DOC_EXTS = {".pdf", ".docx"}

# Caracteres prohibidos en nombres de fichero/carpeta en Windows.
_FORBIDDEN = re.compile(r'[\\/:*?"<>|]')

# Heurística de PII residual: 3+ palabras Capitalizadas seguidas, fuera de
# corchetes (las etiquetas de anonimización van como [NOMBRE_1]).
_PII_RESIDUAL = re.compile(
    r"(?<!\[)\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){2,})\b"
)

# Schema mínimo para validar la respuesta del clasificador.
_SCHEMA_CLASIFICADOR = {
    "required": ["categoria", "confianza", "nombre_propuesto"],
}

_FEWSHOT_K = 6
_MAX_BODY_CHARS = 4000


# ---------------------------------------------------------------------------
# Estructura de un documento planificado
# ---------------------------------------------------------------------------

@dataclass
class DocPlan:
    sha256: str
    origen: str                 # nombre de fichero original
    ext: str
    categoria: str
    subgrupo: str | None
    nombre_propuesto: str
    fecha_detectada: str | None
    fecha_fuente: str
    confianza: float
    estado: str                 # OK | OCR_PENDIENTE | NO_ANONIMIZADO | ERROR_PARSEO
    descripcion: str
    src_abs: str = ""           # ruta absoluta del original (no se serializa al .md)
    fragmento: str = ""         # excerpt anonimizado (para loop de aprendizaje)

    def clave(self) -> str:
        return self.sha256


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

def _drive_ev_dir(case_id: str) -> Path:
    return caso_path(case_id) / "00_Input" / DRIVE_EV_SUBDIR


def _organizado_dir(case_id: str) -> Path:
    return _drive_ev_dir(case_id) / ORGANIZADO_SUBDIR


def _aicowork_dir(case_id: str) -> Path:
    return caso_path(case_id) / AI_COWORK_SUBDIR


def _anonimizado_dir(case_id: str) -> Path:
    return caso_path(case_id) / ANONIMIZADO_SUBDIR


def _aprendizaje_dir() -> Path:
    """Carpeta despacho-wide de aprendizaje (correcciones + métricas).

    Función (no constante) para que los tests puedan aislarla via monkeypatch.
    """
    return settings.project_root / "data" / "_aprendizaje"


def _prompt_clasificador_path() -> Path:
    return settings.project_root / "data" / "_prompts" / "clasificador_ev.md"


def _correcciones_path() -> Path:
    return _aprendizaje_dir() / "correcciones.jsonl"


def _revisar_path() -> Path:
    return _aprendizaje_dir() / "_revisar.jsonl"


def _metricas_path() -> Path:
    return _aprendizaje_dir() / "metricas.json"


# ---------------------------------------------------------------------------
# Sanitización y utilidades
# ---------------------------------------------------------------------------

def _sanitize(nombre: str, max_len: int = 60) -> str:
    limpio = _FORBIDDEN.sub(" ", nombre).strip()
    limpio = re.sub(r"\s+", " ", limpio)
    return limpio[:max_len].strip()


def _is_image(ext: str) -> bool:
    return ext.lower() in IMG_EXTS


def _exif_o_mtime(path: Path) -> tuple[str | None, str]:
    """Devuelve (fecha_iso, fuente) para una imagen. Best-effort."""
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as img:
            exif = getattr(img, "_getexif", lambda: None)() or {}
        # 36867 = DateTimeOriginal
        raw = exif.get(36867) or exif.get(306)
        if raw:
            dt = datetime.strptime(str(raw)[:19], "%Y:%m:%d %H:%M:%S")
            return dt.date().isoformat(), "exif"
    except Exception:
        pass
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return mtime.date().isoformat(), "drive_mtime"
    except OSError:
        return None, "desconocida"


# ---------------------------------------------------------------------------
# Índice del material anonimizado (resolución por SHA y por slug)
# ---------------------------------------------------------------------------

def _build_anon_index(case_id: str) -> dict:
    """Indexa ``06_Anonimizado/*.md`` por origen_sha256 y por slug.

    Devuelve ``{"por_sha": {sha: (path, body)}, "por_slug": {slug: (path, body)}}``.
    """
    por_sha: dict[str, tuple[Path, str]] = {}
    por_slug: dict[str, tuple[Path, str]] = {}
    raiz = _anonimizado_dir(case_id)
    if not raiz.is_dir():
        return {"por_sha": por_sha, "por_slug": por_slug}
    for md in raiz.glob("*.md"):
        try:
            meta, body = read_md(md)
        except Exception:
            continue
        sha = meta.get("origen_sha256")
        if sha:
            por_sha[sha] = (md, body)
        por_slug[md.stem] = (md, body)
    return {"por_sha": por_sha, "por_slug": por_slug}


def _resolver_anon(doc: Path, sha: str, index: dict) -> str | None:
    """Devuelve el cuerpo anonimizado del documento, o None si no existe."""
    hit = index["por_sha"].get(sha)
    if hit:
        return hit[1]
    hit = index["por_slug"].get(slugify(doc.stem))
    if hit:
        return hit[1]
    return None


# ---------------------------------------------------------------------------
# Few-shot por similaridad TF-IDF (degradación elegante sin sklearn/datos)
# ---------------------------------------------------------------------------

def _load_corrections() -> list[dict]:
    path = _correcciones_path()
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _few_shot(body: str, k: int = _FEWSHOT_K) -> list[dict]:
    """Recupera hasta ``k`` correcciones relevantes por similaridad TF-IDF.

    Degrada con elegancia: si no hay correcciones o sklearn no está
    instalado, devuelve ``[]`` (el clasificador funciona sin few-shot).
    """
    corr = _load_corrections()
    if not corr:
        return []
    fragmentos = [c.get("fragmento", "") for c in corr]
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.warning("scikit-learn no instalado; few-shot deshabilitado.")
        return corr[:k]
    try:
        vec = TfidfVectorizer()
        matriz = vec.fit_transform(fragmentos + [body])
        sims = cosine_similarity(matriz[-1], matriz[:-1]).ravel()
        orden = sims.argsort()[::-1][:k]
        return [corr[i] for i in orden if sims[i] > 0.0]
    except Exception as exc:
        logger.debug("Fallo TF-IDF, few-shot vacío: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Clasificación
# ---------------------------------------------------------------------------

def _build_prompt(reglas: str, fewshot: list[dict], cuerpo: str, nombre_original: str) -> str:
    partes = [reglas, ""]
    if fewshot:
        partes.append("## Ejemplos de clasificaciones revisadas por un humano\n")
        for ej in fewshot:
            partes.append(
                f"- Documento: «{ej.get('nombre_original', '')}» → "
                f"categoría `{ej.get('decision_categoria') or ej.get('categoria', '')}`"
            )
        partes.append("")
    partes.append("## Documento a clasificar\n")
    partes.append(f"Nombre de fichero original (pista, puede contener PII): {nombre_original}")
    partes.append("\nContenido anonimizado:\n")
    partes.append(cuerpo[:_MAX_BODY_CHARS])
    return "\n".join(partes)


def _clasificar_documento(
    doc: Path,
    sha: str,
    anon_index: dict,
    reglas: str,
) -> DocPlan:
    """Clasifica un único documento. No copia nada (solo decide)."""
    ext = doc.suffix.lower()

    # Imágenes: directas a FOTOS, sin Ollama.
    if _is_image(ext):
        fecha, fuente = _exif_o_mtime(doc)
        return DocPlan(
            sha256=sha, origen=doc.name, ext=ext,
            categoria=CATEGORIA_FOTOS, subgrupo=None,
            nombre_propuesto="Fotografía", fecha_detectada=fecha,
            fecha_fuente=fuente, confianza=1.0, estado="OK",
            descripcion="Fotografía del inmueble", src_abs=str(doc),
        )

    if ext not in DOC_EXTS:
        return DocPlan(
            sha256=sha, origen=doc.name, ext=ext,
            categoria=CATEGORIA_PENDIENTE, subgrupo=None,
            nombre_propuesto=_sanitize(doc.stem) or "Documento",
            fecha_detectada=None, fecha_fuente="desconocida",
            confianza=0.0, estado="NO_PROCESABLE",
            descripcion="Formato no procesable por el organizador", src_abs=str(doc),
        )

    cuerpo = _resolver_anon(doc, sha, anon_index)
    if cuerpo is None:
        return DocPlan(
            sha256=sha, origen=doc.name, ext=ext,
            categoria=CATEGORIA_PENDIENTE, subgrupo=None,
            nombre_propuesto=_sanitize(doc.stem) or "Documento",
            fecha_detectada=None, fecha_fuente="desconocida",
            confianza=0.0, estado="OCR_PENDIENTE",
            descripcion="Sin versión anonimizada (ejecutar anonimización)",
            src_abs=str(doc),
        )

    fewshot = _few_shot(cuerpo)
    prompt = _build_prompt(reglas, fewshot, cuerpo, doc.name)
    fragmento = cuerpo[:500]

    try:
        data = llm_local.complete_json(prompt, schema=_SCHEMA_CLASIFICADOR)
    except llm_local.LLMLocalError as exc:
        logger.warning("Clasificación falló para %s: %s", doc.name, exc)
        return DocPlan(
            sha256=sha, origen=doc.name, ext=ext,
            categoria=CATEGORIA_PENDIENTE, subgrupo=None,
            nombre_propuesto=_sanitize(doc.stem) or "Documento",
            fecha_detectada=None, fecha_fuente="desconocida",
            confianza=0.0, estado="ERROR_PARSEO",
            descripcion="El clasificador no devolvió un resultado válido",
            src_abs=str(doc), fragmento=fragmento,
        )

    categoria = data.get("categoria")
    if categoria not in TAXONOMIA_EV:
        categoria = CATEGORIA_PENDIENTE

    return DocPlan(
        sha256=sha, origen=doc.name, ext=ext,
        categoria=categoria,
        subgrupo=(data.get("subgrupo_sugerido") or None),
        nombre_propuesto=_sanitize(data.get("nombre_propuesto") or doc.stem) or "Documento",
        fecha_detectada=(data.get("fecha_detectada") or None),
        fecha_fuente=(data.get("fecha_fuente") or "desconocida"),
        confianza=float(data.get("confianza") or 0.0),
        estado="OK",
        descripcion=_sanitize(data.get("descripcion_oneline") or "", max_len=120),
        src_abs=str(doc), fragmento=fragmento,
    )


# ---------------------------------------------------------------------------
# Listado de documentos de entrada
# ---------------------------------------------------------------------------

def _listar_documentos(case_id: str) -> list[Path]:
    """Ficheros directos de ``01_Drive EV/`` (no recursivo).

    Excluye nombres que empiezan por ``_`` o ``.`` (incluye ``_organizado/``,
    ``.pulled``, ficheros auxiliares).
    """
    raiz = _drive_ev_dir(case_id)
    if not raiz.is_dir():
        return []
    docs = [
        p for p in raiz.iterdir()
        if p.is_file() and not p.name.startswith(("_", "."))
    ]
    return sorted(docs, key=lambda p: p.name.lower())


# ---------------------------------------------------------------------------
# Subgrupos y orden
# ---------------------------------------------------------------------------

def _activar_subcarpetas(docs: list[DocPlan]) -> None:
    """Decide subcarpetas por categoría según volumen + subgrupos sugeridos.

    Para cada categoría con más de ``UMBRAL_VOLUMEN_SUBCARPETAS`` documentos y
    al menos 2 con ``subgrupo`` no nulo, se mantienen los subgrupos sugeridos;
    en el resto de categorías se anulan (van a la raíz de la categoría).
    """
    por_cat: dict[str, list[DocPlan]] = {}
    for d in docs:
        por_cat.setdefault(d.categoria, []).append(d)

    for cat, grupo in por_cat.items():
        con_subgrupo = [d for d in grupo if d.subgrupo]
        activar = len(grupo) > UMBRAL_VOLUMEN_SUBCARPETAS and len(con_subgrupo) >= 2
        if not activar:
            for d in grupo:
                d.subgrupo = None


def _clave_orden(d: DocPlan, criterio: str):
    sin_fecha = (d.fecha_detectada is None)
    fecha = d.fecha_detectada or ""
    nombre = d.nombre_propuesto.lower()
    if criterio in ("cronologico", "exif_o_alfabetico"):
        return (sin_fecha, fecha, nombre)
    # alfabetico, tipo_documento → por nombre
    return (False, "", nombre)


def _ordenar(docs: list[DocPlan]) -> list[DocPlan]:
    """Ordena por (categoría según TAXONOMIA_EV, subgrupo, criterio interno)."""
    cat_rank = {c: i for i, c in enumerate(TAXONOMIA_EV)}

    def sort_key(d: DocPlan):
        criterio = ORDEN_POR_CATEGORIA.get(d.categoria, "alfabetico")
        return (
            cat_rank.get(d.categoria, len(TAXONOMIA_EV)),
            (d.subgrupo or "").lower(),
            *(_clave_orden(d, criterio),),
        )

    return sorted(docs, key=sort_key)


# ---------------------------------------------------------------------------
# Serialización del plan (tabla markdown round-trip por SHA)
# ---------------------------------------------------------------------------

_COLUMNAS = [
    "SHA", "Origen", "Categoría", "Subgrupo", "Nombre", "Fecha",
    "FuenteFecha", "Confianza", "Estado", "Descripción",
]


def _celda(s: str) -> str:
    return str(s).replace("|", "/").replace("\n", " ").strip()


def _plan_a_md(case_id: str, docs: list[DocPlan], *, editable: bool) -> str:
    docs = _ordenar(docs)
    titulo = "Plan de reorganización (EDITABLE)" if editable else "Plan propuesto (NO EDITAR)"
    nota = (
        "> Edita solo las columnas **Categoría**, **Subgrupo** y **Nombre**. "
        "No toques la columna **SHA** (es la clave de trazabilidad).\n"
        if editable else
        "> Copia intocable de la propuesta original del clasificador. Sirve de "
        "base para detectar tus correcciones al ejecutar.\n"
    )
    lineas = [
        f"# {titulo} — {case_id}",
        "",
        f"Generado: {now_iso()} · Modelo: `{llm_local.configured_model()}`",
        "",
        nota,
        "",
        "| " + " | ".join(_COLUMNAS) + " |",
        "|" + "|".join(["---"] * len(_COLUMNAS)) + "|",
    ]
    for d in docs:
        fila = [
            d.sha256,
            _celda(d.origen),
            _celda(d.categoria),
            _celda(d.subgrupo or "-"),
            _celda(d.nombre_propuesto),
            d.fecha_detectada or "-",
            d.fecha_fuente,
            f"{d.confianza:.2f}",
            d.estado,
            _celda(d.descripcion),
        ]
        lineas.append("| " + " | ".join(fila) + " |")
    lineas.append("")
    return "\n".join(lineas)


def _parse_plan_md(text: str) -> list[dict]:
    """Parsea la tabla del plan. Devuelve un dict por fila (clave: SHA)."""
    filas: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        celdas = [c.strip() for c in line.strip("|").split("|")]
        if len(celdas) != len(_COLUMNAS):
            continue
        if celdas[0] == "SHA" or set(celdas[0]) <= {"-"}:
            continue  # cabecera o separador
        fila = dict(zip(_COLUMNAS, celdas))
        filas.append(fila)
    return filas


# ---------------------------------------------------------------------------
# planificar (--plan)
# ---------------------------------------------------------------------------

class OrganizadorError(RuntimeError):
    pass


def _cargar_reglas() -> str:
    path = _prompt_clasificador_path()
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Clasifica el documento en una categoría de la taxonomía E&V."


def _verificar_precondiciones(case_id: str, *, check_ollama: bool) -> None:
    drive = _drive_ev_dir(case_id)
    if not drive.is_dir() or not _listar_documentos(case_id):
        raise OrganizadorError(
            f"No hay documentos en {drive}. Descarga primero el Drive E&V."
        )
    anon = _anonimizado_dir(case_id)
    if not anon.is_dir() or not list(anon.glob("*.md")):
        raise OrganizadorError(
            f"Falta material anonimizado en {anon}. Ejecuta primero:\n"
            f'  python -m scripts.anonimizar_caso "{case_id}"'
        )
    if check_ollama and not llm_local.health_check():
        raise OrganizadorError(
            "Ollama no está disponible. Arráncalo y descarga el modelo:\n"
            "  ollama serve\n"
            f"  ollama pull {llm_local.configured_model()}"
        )


@dataclass
class Precondiciones:
    """Estado de las precondiciones del organizador para un caso.

    Pensado para que la UI deshabilite el botón y muestre mensajes claros
    *antes* de invocar ``planificar``/``ejecutar_plan`` (que de todos modos
    revalidan y lanzan ``OrganizadorError`` si algo falta).
    """

    drive_ok: bool          # hay documentos en 00_Input/01_Drive EV/
    n_docs: int
    anon_ok: bool           # 06_Anonimizado/ poblado
    ollama_ok: bool         # core.llm_local.health_check()
    plan_existe: bool       # ya hay un _plan_reorganizacion.md editable
    modelo: str

    @property
    def listo_para_planificar(self) -> bool:
        return self.drive_ok and self.anon_ok and self.ollama_ok


def estado_precondiciones(case_id: str) -> Precondiciones:
    """Inspecciona (sin efectos secundarios) si el caso puede organizarse.

    Las tres comprobaciones de fichero son baratas (listados de carpeta). El
    ``health_check`` de Ollama solo se invoca si Drive y anonimizado están
    listos, para no golpear el servicio cuando el caso todavía no es candidato.
    """
    docs = _listar_documentos(case_id)
    drive_ok = bool(docs)

    anon = _anonimizado_dir(case_id)
    anon_ok = anon.is_dir() and bool(list(anon.glob("*.md")))

    ollama_ok = llm_local.health_check() if (drive_ok and anon_ok) else False

    plan_existe = (_aicowork_dir(case_id) / PLAN_REORGANIZACION).exists()

    return Precondiciones(
        drive_ok=drive_ok,
        n_docs=len(docs),
        anon_ok=anon_ok,
        ollama_ok=ollama_ok,
        plan_existe=plan_existe,
        modelo=llm_local.configured_model(),
    )


def _clasificar_todos(case_id: str, docs_paths: list[Path]) -> list[DocPlan]:
    anon_index = _build_anon_index(case_id)
    reglas = _cargar_reglas()
    resultados: list[DocPlan] = []
    for doc in docs_paths:
        sha = file_sha256(doc)
        resultados.append(_clasificar_documento(doc, sha, anon_index, reglas))
    _activar_subcarpetas(resultados)
    return resultados


def planificar(case_id: str, *, log: logging.Logger | None = None) -> dict:
    """``--plan``: clasifica y escribe la propuesta. No toca ``_organizado/``."""
    log = log or logger
    _verificar_precondiciones(case_id, check_ollama=True)
    llm_local.warmup()

    docs_paths = _listar_documentos(case_id)
    docs = _clasificar_todos(case_id, docs_paths)

    aicowork = _aicowork_dir(case_id)
    aicowork.mkdir(parents=True, exist_ok=True)
    (aicowork / PLAN_PROPUESTO).write_text(
        _plan_a_md(case_id, docs, editable=False), encoding="utf-8"
    )
    (aicowork / PLAN_REORGANIZACION).write_text(
        _plan_a_md(case_id, docs, editable=True), encoding="utf-8"
    )

    return _resumen_plan(case_id, docs, aicowork)


def _resumen_plan(case_id: str, docs: list[DocPlan], aicowork: Path) -> dict:
    total = len(docs)
    alta = sum(1 for d in docs if d.confianza >= UMBRAL_CONFIANZA_AUTOMOVE)
    pendientes = sum(1 for d in docs if d.estado != "OK" or d.categoria == CATEGORIA_PENDIENTE)
    conf_media = round(sum(d.confianza for d in docs) / total, 3) if total else 0.0
    return {
        "case_id": case_id,
        "n_documentos": total,
        "n_alta_confianza": alta,
        "n_pendientes": pendientes,
        "confianza_media": conf_media,
        "plan_propuesto": str(aicowork / PLAN_PROPUESTO),
        "plan_reorganizacion": str(aicowork / PLAN_REORGANIZACION),
    }


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def _leer_audit(case_id: str) -> list[dict]:
    path = _organizado_dir(case_id) / AUDIT_FILE
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _estado_por_sha(audit: list[dict]) -> dict[str, str]:
    """Último destino conocido por SHA (acciones que materializan copia)."""
    estado: dict[str, str] = {}
    for e in audit:
        if e.get("action") in ("COPY", "MOVED", "RENUMBER"):
            estado[e["sha256"]] = e["dst_relative"]
    return estado


def _append_audit(case_id: str, entradas: list[dict]) -> Path:
    org = _organizado_dir(case_id)
    org.mkdir(parents=True, exist_ok=True)
    path = org / AUDIT_FILE
    with path.open("a", encoding="utf-8") as fh:
        for e in entradas:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# Loop de aprendizaje (detección de correcciones humanas)
# ---------------------------------------------------------------------------

def _tiene_pii_residual(fragmento: str) -> bool:
    return bool(_PII_RESIDUAL.search(fragmento or ""))


def _detectar_correcciones(
    case_id: str,
    propuesto: list[dict],
    editado: list[dict],
    anon_index: dict,
) -> int:
    """Compara propuesta vs plan editado y registra las correcciones humanas."""
    prop_por_sha = {f["SHA"]: f for f in propuesto}
    registradas = 0
    aprendizaje = _aprendizaje_dir()
    aprendizaje.mkdir(parents=True, exist_ok=True)

    for fila in editado:
        sha = fila["SHA"]
        base = prop_por_sha.get(sha)
        if not base:
            continue
        cambio_cat = fila["Categoría"] != base["Categoría"]
        cambio_sub = fila["Subgrupo"] != base["Subgrupo"]
        cambio_nom = fila["Nombre"] != base["Nombre"]
        if not (cambio_cat or cambio_sub or cambio_nom):
            continue

        hit = anon_index["por_sha"].get(sha)
        fragmento = (hit[1][:500] if hit else "")

        entrada = {
            "timestamp": now_iso(),
            "case_id": case_id,
            "sha256": sha,
            "nombre_original": fila["Origen"],
            "fragmento": fragmento,
            "propuesta": {
                "categoria": base["Categoría"],
                "subgrupo": base["Subgrupo"],
                "nombre": base["Nombre"],
            },
            "decision": {
                "categoria": fila["Categoría"],
                "subgrupo": fila["Subgrupo"],
                "nombre": fila["Nombre"],
            },
            "decision_categoria": fila["Categoría"],
        }

        # RGPD: el fragmento debe venir de 06_Anonimizado. Si parece tener PII
        # residual, no contamina el dataset de aprendizaje — se deriva a revisión.
        if fragmento and _tiene_pii_residual(fragmento):
            logger.warning("Posible PII residual en corrección de %s; derivada a _revisar.jsonl", sha[:12])
            with _revisar_path().open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entrada, ensure_ascii=False) + "\n")
            continue

        with _correcciones_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        registradas += 1

    return registradas


# ---------------------------------------------------------------------------
# ejecutar_plan (--execute / --dry-run)
# ---------------------------------------------------------------------------

def _numerar(filas: list[dict]) -> list[tuple[dict, str, int]]:
    """Asigna prefijo NN dentro de (categoría, subgrupo). Devuelve (fila, dst_rel, nn)."""
    cat_rank = {c: i for i, c in enumerate(TAXONOMIA_EV)}

    def key(f):
        criterio = ORDEN_POR_CATEGORIA.get(f["Categoría"], "alfabetico")
        sin_fecha = f["Fecha"] in ("-", "")
        if criterio in ("cronologico", "exif_o_alfabetico"):
            ord_interno = (sin_fecha, f["Fecha"], f["Nombre"].lower())
        else:
            ord_interno = (False, "", f["Nombre"].lower())
        return (cat_rank.get(f["Categoría"], 99), (f["Subgrupo"] or "-").lower(), ord_interno)

    ordenadas = sorted(filas, key=key)
    contador: dict[tuple[str, str], int] = {}
    salida: list[tuple[dict, str, int]] = []
    for f in ordenadas:
        cat = f["Categoría"]
        sub = f["Subgrupo"] if f["Subgrupo"] not in ("-", "") else None
        clave = (cat, sub or "")
        contador[clave] = contador.get(clave, 0) + 1
        nn = contador[clave]
        ext = Path(f["Origen"]).suffix.lower()
        nombre_final = f"{nn:02d} {_sanitize(f['Nombre'])}{ext}"
        partes = [cat] + ([_sanitize(sub, 80)] if sub else []) + [nombre_final]
        dst_rel = "/".join(partes)
        salida.append((f, dst_rel, nn))
    return salida


def ejecutar_plan(case_id: str, *, dry_run: bool = False) -> dict:
    """``--execute``: materializa la vista organizada desde el plan editado.

    Lee ``_plan_reorganizacion.md``, detecta correcciones humanas (loop de
    aprendizaje), copia los documentos con nombre limpio a ``_organizado/``,
    escribe READMEs e índice, y registra audit. Idempotente.
    """
    aicowork = _aicowork_dir(case_id)
    reorg_path = aicowork / PLAN_REORGANIZACION
    prop_path = aicowork / PLAN_PROPUESTO
    if not reorg_path.exists():
        raise OrganizadorError(
            f"No existe {reorg_path}. Ejecuta primero la fase de planificación (--plan)."
        )

    editado = _parse_plan_md(reorg_path.read_text(encoding="utf-8"))
    propuesto = _parse_plan_md(prop_path.read_text(encoding="utf-8")) if prop_path.exists() else []

    anon_index = _build_anon_index(case_id)
    n_correcciones = 0
    if not dry_run and propuesto:
        n_correcciones = _detectar_correcciones(case_id, propuesto, editado, anon_index)

    # Solo materializan documentos en estado OK (con SHA y origen presentes).
    materializables = [f for f in editado if f["Estado"] == "OK"]

    org = _organizado_dir(case_id)
    drive = _drive_ev_dir(case_id)
    estado_previo = _estado_por_sha(_leer_audit(case_id))

    resultados: list[dict] = []
    audit_nuevo: list[dict] = []
    acciones: dict[str, int] = {}

    for fila, dst_rel, _nn in _numerar(materializables):
        sha = fila["SHA"]
        src = drive / fila["Origen"]
        dst = org / dst_rel
        prev = estado_previo.get(sha)

        if prev == dst_rel and dst.exists():
            action = "SKIP_UNCHANGED"
        elif prev and prev != dst_rel:
            action = "MOVED"
        else:
            action = "COPY"

        if not dry_run and action != "SKIP_UNCHANGED":
            if action == "MOVED":
                old = org / prev
                if old.exists():
                    old.unlink()
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.copy2(src, dst)
            else:
                action = "MISSING_SRC"

        acciones[action] = acciones.get(action, 0) + 1
        entrada = {
            "timestamp": now_iso(),
            "action": action,
            "src_relative": fila["Origen"],
            "dst_relative": dst_rel,
            "sha256": sha,
            "categoria": fila["Categoría"],
            "subgrupo": fila["Subgrupo"] if fila["Subgrupo"] not in ("-", "") else None,
            "confianza": float(fila["Confianza"]) if fila["Confianza"] else 0.0,
            "nombre_propuesto": fila["Nombre"],
            "nombre_final": Path(dst_rel).name,
            "modelo": llm_local.configured_model(),
        }
        resultados.append(entrada)
        # Solo se registran en el audit las acciones que cambian el estado.
        if action in ("COPY", "MOVED"):
            audit_nuevo.append(entrada)

    if not dry_run:
        if audit_nuevo:
            _append_audit(case_id, audit_nuevo)
        _escribir_readmes(case_id, editado)
        _escribir_indice(case_id, editado)
        _actualizar_metricas(case_id, editado, n_correcciones)

    return {
        "case_id": case_id,
        "dry_run": dry_run,
        "organizado_dir": str(org),
        "n_documentos": len(materializables),
        "acciones": acciones,
        "correcciones_registradas": n_correcciones,
        "resultados": resultados,
    }


# ---------------------------------------------------------------------------
# READMEs e índice
# ---------------------------------------------------------------------------

def _filas_por_categoria(filas: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for f in filas:
        if f["Estado"] != "OK":
            continue
        out.setdefault(f["Categoría"], []).append(f)
    return out


def _escribir_readmes(case_id: str, filas: list[dict]) -> None:
    org = _organizado_dir(case_id)
    for cat, grupo in _filas_por_categoria(filas).items():
        carpeta = org / cat
        if not carpeta.exists():
            continue
        lineas = [
            f"# {cat}",
            "",
            f"{len(grupo)} documento(s). Generado: {now_iso()}.",
            "",
            "| Nombre | Fecha | Subgrupo | Confianza | Descripción |",
            "|---|---|---|---|---|",
        ]
        for f in sorted(grupo, key=lambda x: x["Nombre"].lower()):
            lineas.append(
                f"| {_celda(f['Nombre'])} | {f['Fecha']} | "
                f"{_celda(f['Subgrupo'])} | {f['Confianza']} | {_celda(f['Descripción'])} |"
            )
        lineas.append("")
        (carpeta / README_FILE).write_text("\n".join(lineas), encoding="utf-8")


def _escribir_indice(case_id: str, filas: list[dict]) -> None:
    org = _organizado_dir(case_id)
    org.mkdir(parents=True, exist_ok=True)
    ok = [f for f in filas if f["Estado"] == "OK"]

    # Vista cronológica (sin fecha al final).
    def fecha_key(f):
        return (f["Fecha"] in ("-", ""), f["Fecha"], f["Nombre"].lower())

    lineas = [
        f"# Índice del expediente — {case_id}",
        "",
        f"Vista generada por el organizador local. Generado: {now_iso()}.",
        "",
        "## Vista cronológica",
        "",
        "| Fecha | Categoría | Nombre |",
        "|---|---|---|",
    ]
    for f in sorted(ok, key=fecha_key):
        lineas.append(f"| {f['Fecha']} | {_celda(f['Categoría'])} | {_celda(f['Nombre'])} |")

    lineas += ["", "## Resumen por categoría", "", "| Categoría | Documentos |", "|---|---|"]
    por_cat = _filas_por_categoria(filas)
    for cat in TAXONOMIA_EV:
        if cat in por_cat:
            lineas.append(f"| {cat} | {len(por_cat[cat])} |")
    lineas.append("")
    (org / INDICE_FILE).write_text("\n".join(lineas), encoding="utf-8")


def _actualizar_metricas(case_id: str, filas: list[dict], n_correcciones: int) -> None:
    path = _metricas_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (json.JSONDecodeError, OSError):
        data = {}
    ok = [f for f in filas if f["Estado"] == "OK"]
    confs = [float(f["Confianza"]) for f in ok if f["Confianza"]]
    total = len(filas)
    data[case_id] = {
        "timestamp": now_iso(),
        "n_documentos": total,
        "n_ok": len(ok),
        "tasa_aceptacion_directa": round((total - n_correcciones) / total, 3) if total else 0.0,
        "confianza_media": round(sum(confs) / len(confs), 3) if confs else 0.0,
        "correcciones": n_correcciones,
        "modelo": llm_local.configured_model(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# refresh / rebuild / renumerar
# ---------------------------------------------------------------------------

def refrescar(case_id: str) -> dict:
    """``--refresh``: clasifica solo documentos cuyo SHA no esté en el audit.

    Los nuevos se añaden al plan y se materializan (sin revisión humana
    intermedia, salvo baja confianza → van a PENDIENTE).
    """
    _verificar_precondiciones(case_id, check_ollama=True)
    llm_local.warmup()

    ya_vistos = set(_estado_por_sha(_leer_audit(case_id)).keys())
    nuevos_paths = [p for p in _listar_documentos(case_id) if file_sha256(p) not in ya_vistos]
    if not nuevos_paths:
        return {"case_id": case_id, "n_nuevos": 0, "acciones": {}}

    docs = _clasificar_todos(case_id, nuevos_paths)
    for d in docs:
        if d.estado == "OK" and d.confianza < UMBRAL_CONFIANZA_AUTOMOVE:
            d.categoria = CATEGORIA_PENDIENTE

    # Añadir al plan editable existente (o crearlo) y ejecutar.
    aicowork = _aicowork_dir(case_id)
    aicowork.mkdir(parents=True, exist_ok=True)
    reorg = aicowork / PLAN_REORGANIZACION
    existentes = reorg.read_text(encoding="utf-8") if reorg.exists() else ""
    nuevas_filas = _plan_a_md(case_id, docs, editable=True)
    # Reescribimos el plan completo = filas existentes (parseadas) + nuevas.
    filas_prev = _parse_plan_md(existentes)
    todos = filas_prev + _parse_plan_md(nuevas_filas)
    # Deduplicar por SHA conservando lo nuevo.
    vistos: dict[str, dict] = {}
    for f in todos:
        vistos[f["SHA"]] = f
    docs_merge = _filas_a_docplan(vistos.values())
    reorg.write_text(_plan_a_md(case_id, docs_merge, editable=True), encoding="utf-8")
    (aicowork / PLAN_PROPUESTO).write_text(_plan_a_md(case_id, docs_merge, editable=False), encoding="utf-8")

    res = ejecutar_plan(case_id)
    res["n_nuevos"] = len(nuevos_paths)
    return res


def reconstruir(case_id: str) -> dict:
    """``--rebuild``: borra ``_organizado/`` y rehace plan + execute desde cero."""
    org = _organizado_dir(case_id)
    if org.exists():
        shutil.rmtree(org)
    planificar(case_id)
    return ejecutar_plan(case_id)


def renumerar(case_id: str) -> dict:
    """``--renumerar``: reasigna prefijos NN en orden actualizado, in-place."""
    audit = _leer_audit(case_id)
    estado = _estado_por_sha(audit)
    if not estado:
        return {"case_id": case_id, "n_renombrados": 0}

    # Reconstituir filas mínimas desde el último audit por SHA.
    ultimas: dict[str, dict] = {}
    for e in audit:
        if e.get("action") in ("COPY", "MOVED", "RENUMBER"):
            ultimas[e["sha256"]] = e
    filas = [{
        "SHA": sha,
        "Origen": e["src_relative"],
        "Categoría": e["categoria"],
        "Subgrupo": e.get("subgrupo") or "-",
        "Nombre": e["nombre_propuesto"],
        "Fecha": "-",
        "FuenteFecha": "desconocida",
        "Confianza": str(e.get("confianza", 0.0)),
        "Estado": "OK",
        "Descripción": "",
    } for sha, e in ultimas.items()]

    org = _organizado_dir(case_id)
    audit_nuevo: list[dict] = []
    renombrados = 0
    for fila, dst_rel, _nn in _numerar(filas):
        sha = fila["SHA"]
        old_rel = estado.get(sha)
        if old_rel == dst_rel:
            continue
        old = org / old_rel if old_rel else None
        new = org / dst_rel
        new.parent.mkdir(parents=True, exist_ok=True)
        if old and old.exists():
            old.rename(new)
            renombrados += 1
            audit_nuevo.append({
                "timestamp": now_iso(),
                "action": "RENUMBER",
                "src_relative": fila["Origen"],
                "dst_relative": dst_rel,
                "sha256": sha,
                "categoria": fila["Categoría"],
                "subgrupo": fila["Subgrupo"] if fila["Subgrupo"] not in ("-", "") else None,
                "confianza": float(fila["Confianza"]) if fila["Confianza"] else 0.0,
                "nombre_propuesto": fila["Nombre"],
                "nombre_final": Path(dst_rel).name,
                "modelo": llm_local.configured_model(),
            })
    if audit_nuevo:
        _append_audit(case_id, audit_nuevo)
    return {"case_id": case_id, "n_renombrados": renombrados}


def _filas_a_docplan(filas) -> list[DocPlan]:
    docs: list[DocPlan] = []
    for f in filas:
        docs.append(DocPlan(
            sha256=f["SHA"], origen=f["Origen"], ext=Path(f["Origen"]).suffix.lower(),
            categoria=f["Categoría"],
            subgrupo=(f["Subgrupo"] if f["Subgrupo"] not in ("-", "") else None),
            nombre_propuesto=f["Nombre"],
            fecha_detectada=(None if f["Fecha"] in ("-", "") else f["Fecha"]),
            fecha_fuente=f["FuenteFecha"],
            confianza=float(f["Confianza"]) if f["Confianza"] else 0.0,
            estado=f["Estado"], descripcion=f["Descripción"],
        ))
    return docs
