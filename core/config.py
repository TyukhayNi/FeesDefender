"""Configuración global cargada desde .env.

Centraliza rutas, parámetros del LLM y opciones del scoring. Cualquier módulo
del core debe importar `settings` desde aquí en lugar de leer el entorno.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto si existe
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Rutas
    project_root: Path = _PROJECT_ROOT
    casos_root: Path = Path(os.getenv("CASOS_ROOT", _PROJECT_ROOT / "data" / "CASOS")).resolve()
    prompts_dir: Path = (_PROJECT_ROOT / "prompts").resolve()
    plantilla_dir: Path = (_PROJECT_ROOT / "data" / "CASOS" / "_PLANTILLA").resolve()

    # LLM
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")
    ollama_timeout_s: int = int(os.getenv("OLLAMA_TIMEOUT_S", "180"))
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

    # rclone
    rclone_binary: str = os.getenv("RCLONE_BINARY", "rclone")
    rclone_remote: str = os.getenv("RCLONE_REMOTE", "gdrive")

    # Scoring
    scoring_mode: str = os.getenv("SCORING_MODE", "hybrid")
    scoring_top_k: int = int(os.getenv("SCORING_TOP_K", "15"))

    # Drive (integración Google Drive — tyukhay.legal)
    drive_output_folder_id: str = os.getenv("DRIVE_OUTPUT_FOLDER_ID", "")
    # Drive (integración Google Drive — engelvoelkers.com, para intake E&V)
    drive_ev_root_folder_id: str = os.getenv("DRIVE_EV_ROOT_FOLDER_ID", "")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()


# ---------------------------------------------------------------------------
# Taxonomía de casos
# ---------------------------------------------------------------------------

# Posición procesal del cliente (Engel & Völkers)
POSICION_ACTORA = "actora"       # Engel reclama
POSICION_DEFENSIVA = "defensiva"  # Engel es demandado

# Tipos de caso — posición actora (Engel reclama honorarios / daños)
# Formato: clave_interna → (tag_crm, descripción)
TIPOS_CASO_ACTORA: dict[str, tuple[str, str]] = {
    "BAD_DEBT": (
        "BAD DEBT",
        "Impago de factura de honorarios de intermediación.",
    ),
    "NEGATIVA_OFERTA": (
        "NEGATIVA OFERTA",
        "El cliente se niega a aceptar la oferta en condiciones fijadas en el encargo.",
    ),
    "NEGATIVA_ARRAS": (
        "NEGATIVA ARRAS",
        "El cliente se niega a firmar el contrato privado (arras) tras aceptar la oferta.",
    ),
    "NEGATIVA_ESCRITURA": (
        "NEGATIVA ESCRITURA",
        "El cliente se niega a firmar la escritura tras firmar el contrato privado.",
    ),
    "NEGATIVA_CONTRATO_ARRENDAMIENTO": (
        "NEGATIVA CONTRATO ARRENDAMIENTO",
        "El cliente se niega a formalizar el contrato de arrendamiento tras la oferta aceptada.",
    ),
    "VUELTA": (
        "VUELTA",
        "El cliente se aprovecha de la gestión de la agencia cerrando la operación sin ella.",
    ),
    "INCUMPLIMIENTO_EXCLUSIVA": (
        "INCUMPLIMIENTO EXCLUSIVA",
        "El cliente vendedor incumple el pacto de exclusividad del encargo.",
    ),
}

# Tipos de caso — posición defensiva (Engel es demandado)
TIPOS_CASO_DEFENSIVA: dict[str, tuple[str, str]] = {
    "RESPONSABILIDAD_PROFESIONAL": (
        "RESPONSABILIDAD PROFESIONAL",
        "El cliente reclama daños y perjuicios por presunta negligencia de la agencia.",
    ),
    "DEVOLUCION_RESERVA": (
        "DEVOLUCION RESERVA",
        "El comprador o arrendatario reclama la devolución de la reserva o compromiso de seriedad.",
    ),
    "LAU_20": (
        "LAU 20",
        "El arrendatario reclama la devolución de honorarios pagados, al amparo del art. 20.1 LAU.",
    ),
}

# Unión completa (útil para validación y selectores de UI)
TIPOS_CASO_ALL: dict[str, tuple[str, str]] = {
    **TIPOS_CASO_ACTORA,
    **TIPOS_CASO_DEFENSIVA,
}

# Tags CRM válidos (lista plana, para validación)
TAGS_CRM_VALIDOS: frozenset[str] = frozenset(
    tag for tag, _ in TIPOS_CASO_ALL.values()
)


def posicion_de_tipo(tipo: str) -> str:
    """Devuelve POSICION_ACTORA o POSICION_DEFENSIVA dado un tipo de caso."""
    if tipo in TIPOS_CASO_ACTORA:
        return POSICION_ACTORA
    if tipo in TIPOS_CASO_DEFENSIVA:
        return POSICION_DEFENSIVA
    raise ValueError(f"Tipo de caso desconocido: {tipo!r}")


def tag_crm(tipo: str) -> str:
    """Devuelve el tag CRM para un tipo de caso."""
    entry = TIPOS_CASO_ALL.get(tipo)
    if not entry:
        raise ValueError(f"Tipo de caso desconocido: {tipo!r}")
    return entry[0]


# ---------------------------------------------------------------------------
# Estructura de carpetas de un caso
# ---------------------------------------------------------------------------

# El orden importa: refleja el flujo procesal.
# 07_ANONIMIZADO: Markdown anonimizado listo para LLMs online (sin PII).
CASO_SUBDIRS: tuple[str, ...] = (
    "00_INPUT",
    "01_PROCESADO",
    "02_ANALISIS",
    "03_DECISION",
    "04_OUTPUT_PREDEMANDA",
    "05_PROCEDIMIENTO",
    "06_AI_COWORK",
    "07_ANONIMIZADO",
    "90_NOTAS_PERSONALES",
)


def caso_path(case_id: str) -> Path:
    """Devuelve la ruta absoluta a un caso. No lo crea."""
    return settings.casos_root / case_id
