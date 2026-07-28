"""Cerebro puro del renombrado de informes de viabilidad (2026-07-28).

Los informes se bautizaban con el ``case_id`` completo dentro de una carpeta
que ya se llama ``case_id``, así que la ruta se pasaba de los 260 caracteres
que tolera Office y **Excel se negaba a abrirlos** (el sistema de ficheros sí
los admite: ``LongPathsEnabled=1`` y ``openpyxl`` los abre). Este módulo
calcula el renombrado al nombre corto que decide
``core.case_manager._compose_informe_filename`` y lo aplica con garantías:

- **Nunca sobrescribe**: si el destino ya existe, se marca ``colision`` y no
  se toca nada.
- **Nunca decide por el letrado**: si una carpeta ``02_Analisis`` tiene más de
  un informe humano (hay un caso real con uno del pipeline y otro puesto a
  mano en mayúsculas), se marca ``ambiguo`` y se deja intacto.
- **Idempotente**: lo que ya tiene el nombre correcto se marca ``ya_correcto``.

Solo renombra; jamás abre ni modifica el contenido de un ``.xlsx``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .case_manager import (
    RUTA_OFFICE_MAX,
    _compose_informe_filename,
    _parse_id_go_from_case_id,
)
from .utils import read_md

logger = logging.getLogger(__name__)

# Estados posibles de una entrada del plan.
RENOMBRAR = "renombrar"
YA_CORRECTO = "ya_correcto"
COLISION = "colision"
AMBIGUO = "ambiguo"


@dataclass(frozen=True)
class Entrada:
    """Una decisión del plan sobre un informe concreto (o sobre un grupo
    ambiguo, en cuyo caso ``destino`` es ``None``)."""

    case_id: str
    origen: Path
    destino: Path | None
    estado: str
    detalle: str = ""

    @property
    def largo_origen(self) -> int:
        return len(str(self.origen))

    @property
    def largo_destino(self) -> int | None:
        return len(str(self.destino)) if self.destino is not None else None


def _es_informe(nombre_sin_ext: str) -> bool:
    """¿El stem corresponde a un informe de viabilidad (humano o LLM)?

    Compara en minúsculas y con ``_`` como espacio para pillar las tres
    convenciones que conviven en el Drive: ``Informe viabilidad - …``,
    ``_informe_viabilidad`` y el ``INFORME VIABILIDAD …`` puesto a mano.
    """
    return nombre_sin_ext.lower().replace("_", " ").strip().startswith(
        "informe viabilidad"
    )


def _es_llm(nombre_sin_ext: str) -> bool:
    return "llm" in nombre_sin_ext.lower()


def _id_go_efectivo(case_dir: Path, case_id: str) -> str | None:
    """ID GO del frontmatter de ``_caso.md``; si no se puede leer, el del case_id.

    Mismo orden de preferencia que ``ensure_case``, para que la migración
    produzca el nombre que el código generaría hoy.
    """
    index = case_dir / "00_Input" / "_caso.md"
    if index.is_file():
        try:
            frontmatter, _ = read_md(index)
            meta = (frontmatter.get("meta") or {}) if isinstance(frontmatter, dict) else {}
            persistido = meta.get("id_go")
            if persistido:
                return str(persistido).strip()
        except Exception:  # noqa: BLE001 — un _caso.md ilegible no aborta la migración
            logger.debug("No se pudo leer el frontmatter de %s", index, exc_info=True)
    return _parse_id_go_from_case_id(case_id)


def _destino_para(analisis_dir: Path, case_id: str, id_go: str | None, *, llm: bool) -> Path | None:
    """Nombre destino del informe. ``None`` si no hay uno mejor que el actual."""
    if not llm:
        return analisis_dir / _compose_informe_filename(case_id, id_go)
    # El informe LLM no tiene fallback: sin ID GO se queda como está, porque
    # `_informe_viabilidad.xlsx` es el nombre del informe humano.
    if not id_go:
        return None
    return analisis_dir / f"Informe viabilidad LLM - {id_go}.xlsx"


def _plan_para_grupo(
    grupo: list[Path],
    analisis_dir: Path,
    case_id: str,
    id_go: str | None,
    *,
    llm: bool,
) -> list[Entrada]:
    etiqueta = "LLM" if llm else "humano"
    if len(grupo) > 1:
        nombres = ", ".join(sorted(p.name for p in grupo))
        return [
            Entrada(
                case_id, p, None, AMBIGUO,
                f"{len(grupo)} informes {etiqueta} en la misma carpeta ({nombres}): "
                "decide cuál es el vigente antes de renombrar",
            )
            for p in sorted(grupo)
        ]

    origen = grupo[0]
    destino = _destino_para(analisis_dir, case_id, id_go, llm=llm)
    if destino is None:
        return [Entrada(case_id, origen, None, YA_CORRECTO,
                        f"informe {etiqueta} sin ID GO: se deja como está")]
    if destino.name == origen.name:
        return [Entrada(case_id, origen, destino, YA_CORRECTO)]
    if destino.exists():
        return [Entrada(case_id, origen, destino, COLISION,
                        f"'{destino.name}' ya existe: no se sobrescribe")]
    return [Entrada(case_id, origen, destino, RENOMBRAR)]


def _es_raiz_de_caso(case_dir: Path) -> bool:
    """¿``case_dir`` es la raíz de un expediente y no una carpeta interior?

    La firma de una raíz de caso es tener ``00_Input`` (lo crea ``ensure_case``).
    El chequeo evita dos falsos positivos del recorrido recursivo: un
    ``02_Analisis`` que viniera dentro de un espejo (``00_Input/01_Drive EV/…``,
    donde el crudo de E&V replica su propia estructura) y cualquier
    ``02_Analisis`` suelto en la biblioteca.
    """
    return (case_dir / "00_Input").is_dir()


def plan_renombrado(casos_root: Path) -> list[Entrada]:
    """Recorre las carpetas ``02_Analisis`` de todos los casos y decide.

    El recorrido es **recursivo y agnóstico de profundidad** a propósito: los
    casos vivos cuelgan de ``<ciudad>/<case_id>/`` pero los archivados cuelgan
    de ``_ARCHIVO/<carpeta>/<año>/<case_id>/``, y un glob de profundidad fija
    se los dejaba fuera.

    Devuelve el plan completo, incluidas las entradas que no se van a tocar
    (``ya_correcto``, ``colision``, ``ambiguo``), para que el informe del CLI
    dé cuenta de todo lo que hay.
    """
    plan: list[Entrada] = []
    for analisis_dir in sorted(casos_root.rglob("02_Analisis")):
        if not analisis_dir.is_dir():
            continue
        case_dir = analisis_dir.parent
        if not _es_raiz_de_caso(case_dir):
            logger.debug("Se omite %s: el padre no parece raíz de caso", analisis_dir)
            continue
        case_id = case_dir.name
        id_go = _id_go_efectivo(case_dir, case_id)

        humanos: list[Path] = []
        llms: list[Path] = []
        for path in sorted(analisis_dir.iterdir()):
            if path.suffix.lower() != ".xlsx" or not path.is_file():
                continue
            if not _es_informe(path.stem):
                continue
            (llms if _es_llm(path.stem) else humanos).append(path)

        for grupo, llm in ((humanos, False), (llms, True)):
            if grupo:
                plan.extend(
                    _plan_para_grupo(grupo, analisis_dir, case_id, id_go, llm=llm)
                )
    return plan


def aplicar(plan: list[Entrada]) -> list[Entrada]:
    """Ejecuta las entradas en estado ``renombrar``. Devuelve las aplicadas.

    Re-comprueba la existencia del destino justo antes de mover: entre el plan
    y la aplicación el Drive puede haber sincronizado algo.
    """
    aplicadas: list[Entrada] = []
    for entrada in plan:
        if entrada.estado != RENOMBRAR or entrada.destino is None:
            continue
        if entrada.destino.exists():
            logger.warning(
                "'%s' apareció entre el plan y la aplicación: no se renombra %s",
                entrada.destino.name, entrada.origen.name,
            )
            continue
        entrada.origen.rename(entrada.destino)
        logger.info("Renombrado: %s → %s", entrada.origen.name, entrada.destino.name)
        aplicadas.append(entrada)
    return aplicadas


def resumen(plan: list[Entrada]) -> dict[str, int]:
    """Conteo por estado, más cuántas rutas siguen fuera del presupuesto."""
    conteo = {estado: 0 for estado in (RENOMBRAR, YA_CORRECTO, COLISION, AMBIGUO)}
    for entrada in plan:
        conteo[entrada.estado] = conteo.get(entrada.estado, 0) + 1
    conteo["fuera_de_presupuesto"] = sum(
        1 for e in plan
        if (e.largo_destino or e.largo_origen) > RUTA_OFFICE_MAX
    )
    return conteo
