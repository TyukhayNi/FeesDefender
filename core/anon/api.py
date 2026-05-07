"""Fachada pública del módulo ``core/anon/``.

El resto del core debe importar desde aquí, no desde los módulos internos.

Esta fachada implementa la API de alto nivel:

- ``anonimizar_documento(case_id, ruta_pdf, ...)``: procesa un único documento.
- ``anonimizar_caso(case_id, ...)``: pipeline completo del anonimizador
  sobre todos los documentos de ``00_Input/`` → ``06_Anonimizado/``.

Garantías:
- **Mapa compartido por caso** (``06_Anonimizado/_mapa_caso.json``): el
  documento N hereda los nombres ya etiquetados del documento N-1, con
  contadores intactos. Sin colisiones de etiquetas.
- **Idempotencia**: el SHA-256 del PDF origen se persiste en el frontmatter
  del .md anonimizado. Si la política es ``SALTAR`` y el hash coincide, no
  se reprocesa. Política ``REPROCESAR`` ignora el skip.
- **Logging unificado**: todas las operaciones de un caso emiten líneas a
  ``07_AI cowork/_anonimizador_log.md`` siguiendo el patrón del pipeline.
- **Sin acoplamiento UI**: la API recibe ``on_progress`` opcional. La UI
  (Streamlit) lo conecta a sus propios mecanismos de progreso.

Notas de alcance MVP (Fase 3):
- No aplica OCR automáticamente. Si el PDF carece de capa de texto,
  ``anonimizar_documento`` devuelve ``ok=False`` con la alerta
  ``"OCR_REQUERIDO"`` y el documento se contabiliza como pendiente.
- No separa PDFs en sub-documentos. Cada PDF de ``00_Input/`` se procesa
  como un único documento. La separación queda como step independiente
  invocable desde ``core.anon.separar.separar_pdf_pipeline``.
- No procesa imágenes (.jpg/.png/.heic). La conversión a PDF queda en
  ``core.anon.imagen_a_pdf.convertir`` para invocación previa.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Iterable

from core.case_manager import caso_path
from core.utils import (
    build_frontmatter,
    file_sha256,
    now_iso,
    read_md,
    slugify,
    validate_case_id,
)

from core.anon.anonimizar import (
    MapaEntidades,
    anonimizar_texto,
    extraer_texto,
    texto_a_markdown,
)
from core.anon.exceptions import (
    AnonError,
    DocxVacioError,
    FormatoNoSoportadoError,
    PDFSinTextoError,
)
from core.anon.mapa_caso import (
    cargar_mapa_caso,
    guardar_mapa_caso,
)


# ---------------------------------------------------------------------------
# Constantes de carpeta — sigue la nomenclatura real del código (config.py).
# ---------------------------------------------------------------------------

SUBDIR_INPUT       = "00_Input"
SUBDIR_ANONIMIZADO = "06_Anonimizado"
SUBDIR_AI_COWORK   = "07_AI cowork"

LOG_FILENAME = "_anonimizador_log.md"

# Extensiones que la fachada procesa directamente. Las imágenes y los PDFs
# escaneados sin OCR requieren paso previo (no en MVP de Fase 3).
EXTS_PROCESABLES = {".pdf", ".docx"}


ProgressCallback = Callable[[str, int, int], None]
"""Firma del callback de progreso: ``(etapa, hecho, total)``."""


# ---------------------------------------------------------------------------
# Construcción del .md anonimizado en formato FeesDefender
# ---------------------------------------------------------------------------

def _quitar_cabecera_legacy(md: str) -> str:
    """Elimina la cabecera del estilo Anonimizador original.

    El original genera:

        # <nombre_archivo>
        <vacía>
        > **Documento anonimizado** | Tipo: ...
        > Generado: ...
        <vacía>
        <cuerpo>

    En FeesDefender la cabecera la pone el frontmatter YAML — no queremos
    duplicarla. Esta función recorta esas primeras líneas y devuelve el
    cuerpo a partir de la primera línea que no es ni título ``#`` ni cita
    ``>``.
    """
    lineas = md.split("\n")
    idx = 0
    # Saltar título inicial '# ...'
    if idx < len(lineas) and lineas[idx].startswith("# "):
        idx += 1
    # Saltar líneas vacías y citas '> ...' que siguen al título
    while idx < len(lineas) and (
        lineas[idx].strip() == "" or lineas[idx].startswith(">")
    ):
        idx += 1
    return "\n".join(lineas[idx:])


def _build_md_anonimizado(
    *,
    case_id: str,
    slug: str,
    tipo_proc: str,
    texto_anonimizado: str,
    origen: Path,
    origen_sha256: str,
    n_entidades: int,
    alertas: list[str],
) -> str:
    """Genera el .md anonimizado con frontmatter YAML estilo FeesDefender."""
    cuerpo_md = texto_a_markdown(texto_anonimizado, slug, tipo_proc)
    cuerpo_limpio = _quitar_cabecera_legacy(cuerpo_md)

    fm = build_frontmatter({
        "case_id":            case_id,
        "tipo":               "documento_anonimizado",
        "fase":               SUBDIR_ANONIMIZADO,
        "slug":               slug,
        "fecha":              now_iso(),
        "tipo_procedimiento": tipo_proc,
        "origen":             origen.name,
        "origen_sha256":      origen_sha256,
        "n_entidades":        n_entidades,
        "alertas":            alertas,
    })

    return f"{fm}\n# {slug.replace('_', ' ').title()}\n\n{cuerpo_limpio}".rstrip() + "\n"


# ---------------------------------------------------------------------------
# Idempotencia
# ---------------------------------------------------------------------------

def _md_ya_actualizado(ruta_md: Path, origen_sha256: str) -> bool:
    """``True`` si el .md ya existe y su frontmatter declara el mismo hash."""
    if not ruta_md.exists():
        return False
    try:
        meta, _ = read_md(ruta_md)
    except Exception:
        return False
    return meta.get("origen_sha256") == origen_sha256


# ---------------------------------------------------------------------------
# anonimizar_documento — procesa un solo documento
# ---------------------------------------------------------------------------

def anonimizar_documento(
    case_id: str,
    ruta_origen: Path,
    *,
    tipo_proc: str = "Juicio Ordinario",
    mapa_caso: MapaEntidades | None = None,
    log: logging.Logger | None = None,
    politica: str = "SALTAR",
) -> dict:
    """Anonimiza un único documento (PDF o DOCX) ya extractable.

    Args:
        case_id: ID del caso (validado vía ``validate_case_id``).
        ruta_origen: Documento a anonimizar.
        tipo_proc: Tipo de procedimiento (metadato del frontmatter, no
            condiciona la anonimización).
        mapa_caso: ``MapaEntidades`` compartido del caso. Si ``None``, se
            crea uno nuevo desde cero (anonimización aislada — usar solo
            cuando se procesa un único documento puntual).
        log: Logger; si ``None`` se usa uno silencioso.
        politica: ``"SALTAR"`` (default) o ``"REPROCESAR"``.

    Returns:
        Dict con:
            - ``ok`` (bool): True si la operación finalizó sin error.
            - ``ruta_md`` (Path | None): Path del .md generado (o existente
              en caso de skip), None si no se llegó a generar.
            - ``skipped`` (bool): True si se saltó por idempotencia.
            - ``n_entidades`` (int): entidades nuevas registradas.
            - ``alertas`` (list[str]): mensajes para el usuario.
            - ``error`` (str | None): mensaje si ``ok=False``.
    """
    case_id = validate_case_id(case_id)
    ruta_origen = Path(ruta_origen)

    if log is None:
        log = logging.getLogger("anon.api.silencioso")
        if not log.handlers:
            log.addHandler(logging.NullHandler())

    if not ruta_origen.exists():
        return {
            "ok": False,
            "ruta_md": None,
            "skipped": False,
            "n_entidades": 0,
            "alertas": [],
            "error": f"No existe el documento: {ruta_origen}",
        }

    if ruta_origen.suffix.lower() not in EXTS_PROCESABLES:
        return {
            "ok": False,
            "ruta_md": None,
            "skipped": False,
            "n_entidades": 0,
            "alertas": [],
            "error": (
                f"Extensión no procesable directamente: {ruta_origen.suffix!r}. "
                f"Usa {sorted(EXTS_PROCESABLES)}."
            ),
        }

    slug = slugify(ruta_origen.stem)
    dir_anon = caso_path(case_id) / SUBDIR_ANONIMIZADO
    dir_anon.mkdir(parents=True, exist_ok=True)
    ruta_md = dir_anon / f"{slug}.md"

    origen_sha = file_sha256(ruta_origen)

    # Idempotencia: si SALTAR y ya está procesado con el mismo hash, skip.
    if politica == "SALTAR" and _md_ya_actualizado(ruta_md, origen_sha):
        log.info(f"[skip] {ruta_origen.name} — ya anonimizado")
        return {
            "ok": True,
            "ruta_md": ruta_md,
            "skipped": True,
            "n_entidades": 0,
            "alertas": [],
            "error": None,
        }

    # Mapa compartido (o aislado si no se proporcionó)
    if mapa_caso is None:
        mapa_caso = MapaEntidades()
    n_entidades_antes = len(mapa_caso.mapa)

    # Extracción de texto. Si falla por falta de OCR, devolvemos alerta
    # estructurada en lugar de propagar la excepción — la UI debe poder
    # mostrar al usuario qué documentos requieren OCR previo.
    try:
        texto_original = extraer_texto(ruta_origen, log)
    except PDFSinTextoError as e:
        log.warning(f"[OCR_REQUERIDO] {ruta_origen.name}: {e}")
        return {
            "ok": False,
            "ruta_md": None,
            "skipped": False,
            "n_entidades": 0,
            "alertas": ["OCR_REQUERIDO"],
            "error": str(e),
        }
    except (DocxVacioError, FormatoNoSoportadoError, AnonError) as e:
        log.error(f"[error] {ruta_origen.name}: {e}")
        return {
            "ok": False,
            "ruta_md": None,
            "skipped": False,
            "n_entidades": 0,
            "alertas": [],
            "error": str(e),
        }

    # Anonimización (4 fases) sobre el mapa compartido
    texto_anon, _ = anonimizar_texto(texto_original, mapa=mapa_caso, log=log)

    n_entidades_nuevas = len(mapa_caso.mapa) - n_entidades_antes

    # Generar .md con frontmatter YAML FeesDefender
    md_final = _build_md_anonimizado(
        case_id=case_id,
        slug=slug,
        tipo_proc=tipo_proc,
        texto_anonimizado=texto_anon,
        origen=ruta_origen,
        origen_sha256=origen_sha,
        n_entidades=n_entidades_nuevas,
        alertas=[],
    )

    ruta_md.write_text(md_final, encoding="utf-8")
    log.info(f"[ok] {ruta_origen.name} → {ruta_md.name} ({n_entidades_nuevas} entidades)")

    return {
        "ok": True,
        "ruta_md": ruta_md,
        "skipped": False,
        "n_entidades": n_entidades_nuevas,
        "alertas": [],
        "error": None,
    }


# ---------------------------------------------------------------------------
# anonimizar_caso — pipeline completo del caso
# ---------------------------------------------------------------------------

def _listar_documentos(case_id: str) -> list[Path]:
    """Recorre ``00_Input/`` recursivamente y devuelve los .pdf/.docx.

    Ignora ficheros y carpetas que empiezan por ``_`` (auxiliares como
    ``_caso.md``, ``_inventory.json``, ``_pulled``, etc.).
    """
    raiz = caso_path(case_id) / SUBDIR_INPUT
    if not raiz.is_dir():
        return []
    docs: list[Path] = []
    for p in raiz.rglob("*"):
        # Saltar si alguna parte del path empieza por '_'
        if any(part.startswith("_") for part in p.relative_to(raiz).parts):
            continue
        if p.is_file() and p.suffix.lower() in EXTS_PROCESABLES:
            docs.append(p)
    return sorted(docs)


def _append_log(case_id: str, lineas: Iterable[str]) -> Path:
    """Append líneas al ``07_AI cowork/_anonimizador_log.md``.

    Crea el fichero con cabecera si no existe. Sigue el patrón de
    ``core.pipeline._write_log``: timestamp + nivel + mensaje.
    """
    log_dir = caso_path(case_id) / SUBDIR_AI_COWORK
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILENAME

    if not log_path.exists():
        cabecera = (
            f"# Log del anonimizador — {case_id}\n\n"
            f"Generado por `core.anon.api.anonimizar_caso`. Una entrada por\n"
            f"ejecución; no se rota automáticamente.\n\n---\n\n"
        )
        log_path.write_text(cabecera, encoding="utf-8")

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"## Ejecución {now_iso()}\n\n")
        for linea in lineas:
            fh.write(f"- {linea}\n")
        fh.write("\n")
    return log_path


def anonimizar_caso(
    case_id: str,
    *,
    tipo_proc: str = "Juicio Ordinario",
    politica: str = "SALTAR",
    on_progress: ProgressCallback | None = None,
    log: logging.Logger | None = None,
) -> dict:
    """Pipeline completo del anonimizador sobre un caso.

    Recorre ``00_Input/``, anonimiza cada documento procesable, mantiene
    un único ``MapaEntidades`` compartido a nivel de caso y escribe los
    ``.md`` resultantes en ``06_Anonimizado/`` con frontmatter YAML.

    Args:
        case_id: ID del caso.
        tipo_proc: Tipo de procedimiento (metadato).
        politica: ``"SALTAR"`` (default, idempotente) o ``"REPROCESAR"``.
        on_progress: Callback opcional ``(etapa, hecho, total)`` para UI.
        log: Logger; si ``None`` se crea uno silencioso.

    Returns:
        Dict con:
            - ``case_id`` (str)
            - ``n_documentos`` (int): documentos encontrados.
            - ``n_procesados`` (int): documentos anonimizados con éxito
              en esta ejecución (no incluye los saltados por idempotencia).
            - ``n_skipped`` (int)
            - ``n_errores`` (int)
            - ``mapa_caso_path`` (Path)
            - ``log_path`` (Path)
            - ``errores`` (list[dict]): ``{"documento", "alertas", "error"}``.
    """
    case_id = validate_case_id(case_id)
    if log is None:
        log = logging.getLogger("anon.api.caso")
        if not log.handlers:
            log.addHandler(logging.NullHandler())

    documentos = _listar_documentos(case_id)
    total = len(documentos)
    log.info(f"Caso {case_id}: {total} documento(s) procesables en 00_Input/")

    if on_progress:
        on_progress("listar", 0, total)

    mapa = cargar_mapa_caso(case_id)

    n_proc = 0
    n_skip = 0
    errores: list[dict] = []
    log_lineas: list[str] = [
        f"Documentos detectados: **{total}**",
        f"Política: `{politica}` · Tipo procedimiento: `{tipo_proc}`",
        "",
    ]

    for i, doc in enumerate(documentos, 1):
        if on_progress:
            on_progress("anonimizar", i, total)
        res = anonimizar_documento(
            case_id,
            doc,
            tipo_proc=tipo_proc,
            mapa_caso=mapa,
            log=log,
            politica=politica,
        )
        rel = doc.relative_to(caso_path(case_id))
        if res["skipped"]:
            n_skip += 1
            log_lineas.append(f"⏭ `{rel}` — sin cambios desde último run")
        elif res["ok"]:
            n_proc += 1
            log_lineas.append(
                f"✅ `{rel}` → `{res['ruta_md'].name}` "
                f"({res['n_entidades']} entidades nuevas)"
            )
        else:
            errores.append({
                "documento": str(rel),
                "alertas":   res["alertas"],
                "error":     res["error"],
            })
            tag = ", ".join(res["alertas"]) or "ERROR"
            log_lineas.append(f"❌ `{rel}` — [{tag}] {res['error']}")

    # Persistir el mapa compartido al final (una sola escritura)
    mapa_path = guardar_mapa_caso(case_id, mapa)
    log_lineas.append("")
    log_lineas.append(f"Mapa de caso guardado en `{mapa_path.name}`")
    log_lineas.append(
        f"Resumen: procesados={n_proc}, saltados={n_skip}, errores={len(errores)}"
    )

    log_path = _append_log(case_id, log_lineas)

    return {
        "case_id":         case_id,
        "n_documentos":    total,
        "n_procesados":    n_proc,
        "n_skipped":       n_skip,
        "n_errores":       len(errores),
        "mapa_caso_path":  mapa_path,
        "log_path":        log_path,
        "errores":         errores,
    }
