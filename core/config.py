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
    # Remoto rclone configurado con `rclone config` → gdrive_ev (cuenta engelvoelkers.com)
    # Cada caso almacena en _caso.md: drive_ev_team_id + drive_ev_folder_id
    # intake_drive.py usa: rclone copy "gdrive_ev:" dest/ --drive-team-drive <team_id> --drive-root-folder-id <folder_id>
    drive_ev_remote: str = os.getenv("DRIVE_EV_REMOTE", "gdrive_ev")
    drive_ev_root_folder_id: str = os.getenv("DRIVE_EV_ROOT_FOLDER_ID", "")  # legacy, no usar

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()


# ---------------------------------------------------------------------------
# Taxonomía de casos
# ---------------------------------------------------------------------------

# Posición procesal del cliente (Engel & Völkers)
POSICION_ACTORA = "actora"       # Engel reclama
POSICION_DEFENSIVA = "defensiva"  # Engel es demandado
POSICION_OTROS = "otros"         # Caso genérico (no honorarios, sin posición procesal fija)

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
    "DEVOLUCION_HONORARIOS": (
        "DEVOLUCION HONORARIOS",
        "El cliente (comprador, vendedor o arrendatario fuera del art. 20.1 LAU) reclama "
        "la devolución de los honorarios pagados a la agencia. Cajón general para "
        "compraventa, intermediación mercantil y encargos no residenciales.",
    ),
}

# Tipos de caso — categoría comodín "Otros casos"
#
# Cubre asuntos de E&V no relacionados con defensa/reclamación de honorarios
# (consultas contractuales, requerimientos varios, mediaciones, dudas legales
# sobre operaciones, etc.). Sin posición procesal fija — la decide el caso.
#
# El tag CRM "OTROS" debe darse de alta en sudespacho.net si se desea filtrar
# por él en el frontal; mientras tanto se envía como texto libre.
TIPOS_CASO_OTROS: dict[str, tuple[str, str]] = {
    "OTROS": (
        "OTROS",
        "Caso genérico de E&V no relacionado con defensa o reclamación de honorarios.",
    ),
}

# Unión completa (útil para validación y selectores de UI)
TIPOS_CASO_ALL: dict[str, tuple[str, str]] = {
    **TIPOS_CASO_ACTORA,
    **TIPOS_CASO_DEFENSIVA,
    **TIPOS_CASO_OTROS,
}

# Tags CRM válidos (lista plana, para validación)
TAGS_CRM_VALIDOS: frozenset[str] = frozenset(
    tag for tag, _ in TIPOS_CASO_ALL.values()
)


# ---------------------------------------------------------------------------
# Clientes propios E&V (sudespacho — tabla clientes_propios)
# ---------------------------------------------------------------------------
#
# Mapping clave_interna → (id_sudespacho, razón social).
#
# Por defecto, todos los casos de honorarios (actora + defensiva) se vinculan
# a EV MMC SPAIN, S.L.U. (ID=2) — la sociedad operativa que firma los encargos.
# Para "Otros casos" puede ser necesario vincular a ENGEL & VÖLKERS SPAIN,
# S.L.U. (ID=27) — la sociedad matriz del grupo en España.
#
# IDs confirmados:
#   - EV MMC SPAIN, S.L.U.        → 2  (B65824054)
#   - ENGEL & VÖLKERS SPAIN, S.L.U. → 27  (sociedad matriz; ver
#     https://tnm.sudespacho.net/tnm/ficheros/clientes-propios/27)
#
# ID 73 = duplicado de EV MMC SPAIN — nunca usar.
CLIENTES_PROPIOS_EV: dict[str, tuple[str, str]] = {
    "EV_MMC_SPAIN":      ("2",  "EV MMC SPAIN, S.L.U."),
    "ENGEL_VOLKERS_SPAIN": ("27", "ENGEL & VÖLKERS SPAIN, S.L.U."),
}

# Cliente por defecto para casos de honorarios (BAD_DEBT, NEGATIVA_*, VUELTA,
# INCUMPLIMIENTO_EXCLUSIVA, RESPONSABILIDAD_PROFESIONAL, DEVOLUCION_RESERVA,
# LAU_20, DEVOLUCION_HONORARIOS). Para "OTROS" la UI deja elegir.
CLIENTE_PROPIO_DEFAULT: str = "EV_MMC_SPAIN"


# ---------------------------------------------------------------------------
# Variantes OCR conocidas del cliente (anonimización — MEJORAS_FUTURAS §14)
# ---------------------------------------------------------------------------
#
# El OCR degrada la denominación del cliente ("Engel & Völkers" → "Engel £
# Vólkers", "ENGEL 8 VÖLKERS"...) y el motor las deja sin anonimizar de forma
# inconsistente. El pipeline pre-carga estas variantes para mapearlas todas a
# una única etiqueta canónica antes de las pasadas del motor. Ampliar según
# aparezcan nuevas degradaciones en casos reales.
VARIANTES_OCR_CLIENTE: dict[str, tuple[str, ...]] = {
    "ENGEL_VOLKERS_SPAIN": (
        "ENGEL & VÖLKERS SPAIN, S.L.U.",
        "ENGEL & VÖLKERS SPAIN, S.L.",
        "Engel & Völkers Spain",
        "Engel & Völkers",
        "Engel & Volkers",
        "Engel Völkers",
        "Engel Volkers",
        "ENGEL & VÖLKERS",
        "ENGEL Y VÖLKERS",
        "ENGEL 8 VÖLKERS SPAIN, S.L.",
        "ENGEL 8 VÖLKERS",
        "ENGEL 8 VOLKERS",
        "Engel £ Vólkers",
        "Engel 4 Volkers",
    ),
    "EV_MMC_SPAIN": (
        "EV MMC SPAIN, S.L.U.",
        "EV MMC SPAIN",
        "EV MMC",
    ),
}


def cliente_propio_id(clave: str) -> str:
    """Devuelve el id_sudespacho de un cliente propio E&V.

    Args:
        clave: clave interna (p.ej. "EV_MMC_SPAIN", "ENGEL_VOLKERS_SPAIN").

    Raises:
        ValueError: si la clave no está mapeada.
    """
    entry = CLIENTES_PROPIOS_EV.get(clave)
    if not entry:
        raise ValueError(f"Cliente propio E&V desconocido: {clave!r}")
    return entry[0]


def cliente_propio_label(clave: str) -> str:
    """Devuelve la razón social legible de un cliente propio E&V."""
    entry = CLIENTES_PROPIOS_EV.get(clave)
    if not entry:
        raise ValueError(f"Cliente propio E&V desconocido: {clave!r}")
    return entry[1]


def posicion_de_tipo(tipo: str) -> str:
    """Devuelve POSICION_ACTORA, POSICION_DEFENSIVA o POSICION_OTROS dado un tipo de caso."""
    if tipo in TIPOS_CASO_ACTORA:
        return POSICION_ACTORA
    if tipo in TIPOS_CASO_DEFENSIVA:
        return POSICION_DEFENSIVA
    if tipo in TIPOS_CASO_OTROS:
        return POSICION_OTROS
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

# El orden importa: refleja el flujo procesal del abogado.
# Anonimizado (06) va antes de AI cowork (07): primero se elimina la PII,
# luego se trabaja con LLMs externos sobre material ya limpio.
#
# Nota sobre el doble "05" (D15, reorg 2026-06-10): existe `05_Procedimiento`
# (aquí, nivel caso) y `00_Input/05_CRM/` (espejo crudo del Gestor Documental).
# Son cosas distintas y la duplicidad del prefijo "05" es cosmética (baja
# prioridad). `05_Procedimiento` es el **work-product del letrado** para el
# litigio en curso (escritos de trámite, notas de vista, providencias
# trabajadas), NO un espejo del CRM. Hoy es funcionalmente inerte: solo lo
# crea este scaffolding y lo barre `linker.py`; ningún módulo escribe en él
# automáticamente. Su creación sigue siendo eager dentro de CASO_SUBDIRS
# (patrón establecido del caso); el criterio *lazy* de D7 se aplicó solo al
# árbol de `05_CRM/`.
CASO_SUBDIRS: tuple[str, ...] = (
    "00_Input",
    "01_Procesado",
    "02_Analisis",
    "03_Decision",
    "04_Output predemanda",
    "05_Procedimiento",
    "06_Anonimizado",
    "07_AI cowork",
    "90_Notas personales",
)

# Subcarpetas de intake dentro de 00_INPUT/.
#
# Terminología de partes (cubre compraventa, arrendamiento y traspaso):
#   "propietario" = quien ofrece el bien (antes "vendedor")
#   "buscador"    = quien busca el bien (antes "comprador" o "arrendatario")
#
# Nivel 2 — fuentes de documentos (numeradas):
#   01_drive_ev, 02_whatsapp, 03_email, 04_manual
#
# Nivel 3 — conversaciones estándar dentro de 02_whatsapp/ y 03_email/:
#   00_consultor-propietario/
#   01_consultor-buscador/
#   02_grupo-operacion/     (whatsapp) | 02_direccion-ev/ (email)
#   03_otros/
#
# Automatización pendiente: drive_ev (cuenta engelvoelkers.com),
#                           email (nikolai.tyukhay@engelvoelkers.com),
#                           whatsapp (exportación manual por ahora).

INPUT_SUBDIRS: tuple[str, ...] = (
    "01_Drive EV",        # carpeta W-XXXXXX del Drive engelvoelkers.com (intake automatizado)
    "02_Whatsapp",        # conversaciones exportadas manualmente (automatización pendiente)
    "03_Email",           # hilos de correo exportados manualmente (automatización pendiente)
    "04_Manual",          # uploads manuales desde la UI (incluye demanda defensiva tras refactor v2)
    "05_CRM",             # árbol del gestor documental sudespacho (CRM_TREE; ver §13 de docs/INTEGRACION_SUDESPACHO.md)
    "06_Entrevistas",     # <YYYY-MM-DD>_<rol>_<apellido>/ con grabación + transcripción
)

# Subcarpetas de nivel 3 dentro de 02_Whatsapp/
WHATSAPP_SUBDIRS: tuple[str, ...] = (
    "00_Consultor propietario",
    "01_Consultor buscador",
    "02_Grupo operacion",
    "03_Otros",
)

# Subcarpetas de nivel 3 dentro de 03_Email/
EMAIL_SUBDIRS: tuple[str, ...] = (
    "00_Consultor propietario",
    "01_Consultor buscador",
    "02_Direccion EV",
    "03_Otros",
)


def caso_path(case_id: str) -> Path:
    """Devuelve la ruta absoluta a un caso. Tolera layout flat y por ciudades."""
    from core.casos.case_locator import path_for
    return path_for(case_id)


# ---------------------------------------------------------------------------
# Organizador local (core/local_organizer.py — Sprint 2)
# ---------------------------------------------------------------------------
#
# Clasifica los documentos en bruto del Drive E&V (00_Input/01_Drive EV/) y
# produce una vista humana navegable en una subcarpeta `_organizado/` con la
# taxonomía estándar interna del cliente. El prefijo "_" garantiza que el
# motor de anonimización (core/anon/api.py) ignore esa subcarpeta.

# Taxonomía estándar E&V — set cerrado. El clasificador local debe devolver
# exactamente uno de estos valores en el campo `categoria`.
TAXONOMIA_EV: tuple[str, ...] = (
    "00. FOTOS",
    "01. ACTIVACIÓN",
    "03. OFERTAS",
    "04. ARRAS - ARRENDAMIENTOS",
    "05. FACTURACIÓN - FINANZAS",
    "06. PBC",
    "07. RECLAMACIONES",
    "08. PENDIENTE DE CLASIFICAR",
)

# Criterio de ordenación de documentos dentro de cada categoría.
ORDEN_POR_CATEGORIA: dict[str, str] = {
    "00. FOTOS": "exif_o_alfabetico",
    "01. ACTIVACIÓN": "cronologico",
    "03. OFERTAS": "cronologico",
    "04. ARRAS - ARRENDAMIENTOS": "cronologico",
    "05. FACTURACIÓN - FINANZAS": "cronologico",
    "06. PBC": "tipo_documento",
    "07. RECLAMACIONES": "cronologico",
    "08. PENDIENTE DE CLASIFICAR": "alfabetico",
}

# Subcarpeta de la vista organizada, bajo 00_Input/01_Drive EV/.
ORGANIZADO_SUBDIR: str = "_organizado"

# Confianza mínima para mover un documento automáticamente en --refresh.
# Por debajo, va a "08. PENDIENTE DE CLASIFICAR" para revisión humana.
UMBRAL_CONFIANZA_AUTOMOVE: float = 0.80

# Nº de documentos en una categoría a partir del cual se evalúa subdividir
# en subcarpetas (si además hay subgrupos sugeridos por el clasificador).
UMBRAL_VOLUMEN_SUBCARPETAS: int = 5


# ---------------------------------------------------------------------------
# Refactor intake v2 — árbol del gestor documental + entrevistas + viabilidad
# ---------------------------------------------------------------------------
#
# Decisiones D1–D12 + M1–M10 cerradas (memoria persistente:
# project_intake_estructura_v2.md). Documentación de la estrategia híbrida y
# de los mappings empíricos: docs/INTEGRACION_SUDESPACHO.md sección 13.
#
# Convenciones:
#   - Capitalización tipo oración (D3) — siglas se mantienen (M7).
#   - Separador de paths internos: "/" (forward slash). Coincide con filesystem
#     y con la salida canónica de crm_branch_path() (D11).

# Subcarpeta CRM dentro de 00_Input/ (constante para evitar literales sueltos).
CRM_SUBDIR: str = "05_CRM"

# Nombre de la carpeta de fallback dentro de 05_CRM/ cuando crm_branch_path()
# no resuelve a una rama del árbol (M5-Q2). Prefijo "99_" deliberado: el filtro
# de core/anon/api.py:330 excluye carpetas con prefijo "_", así que "_Sin
# categoria/" eliminaría los huérfanos del pipeline de anonimización. "99_"
# mantiene el orden visual al final del árbol sin chocar con ese filtro.
CRM_FALLBACK_PATH: str = "99_Sin categoria"

# Buckets procesales planos de 05_CRM (D5 — reorg 2026-06-10). La estructura
# de 05_CRM es solo navegación humana del input; el pipeline aplana a un output
# por documento con slug stem-only (extractor.py), independiente de la
# subcarpeta de origen. Cada bucket mapea 1:1 a una hoja real de CRM_TREE; el
# andamiaje intermedio (Civil/1ª Instancia/Declarativo/…) se aplana. La
# resolución rama-canónica → bucket vive en case_manager._bucket_for (D6).
# Motivo: límite de ruta de Windows (260 car.) + desorden de carpetas vacías.
CRM_BUCKET_DEMANDA: str = "01_Demanda"                     # ← Declarativo/Demanda
CRM_BUCKET_CONTESTACION: str = "02_Contestacion"           # ← Declarativo/Oposicion (un solo bucket — D5b)
CRM_BUCKET_MONITORIO_DEMANDA: str = "03_Monitorio_Demanda" # ← Monitorio/Demanda
CRM_BUCKET_MONITORIO_OPOSICION: str = "04_Monitorio_Oposicion"  # ← Monitorio/Oposicion
CRM_BUCKET_PRELIMINARES: str = "05_Diligencias_Preliminares"    # ← Preliminares/* (NUNCA 01_Demanda — D6)
CRM_BUCKET_OTROS: str = "99_Otros"                         # ← resto, plano por fecha

# Subcarpeta de entrevistas dentro de 00_Input/.
ENTREVISTAS_SUBDIR: str = "06_Entrevistas"

# Árbol del gestor documental — anidado, recorrido recursivo trivial (M4-Q2).
# Cada nodo terminal es un dict vacío {}. ensure_case() recorre este árbol en
# eager y crea todas las ramas de todos los casos nuevos (D1).
#
# Cualquier cambio aquí debe reflejarse en docs/INTEGRACION_SUDESPACHO.md §13.6.
CRM_TREE: dict[str, dict] = {
    "General": {},
    "Civil": {
        "1ª Instancia": {
            "Declarativo": {
                "Demanda": {},
                "Oposicion": {},
            },
            "Monitorio": {
                "Demanda": {},
                "Oposicion": {},
            },
            "Documentacion RGPD LOPD": {},
            "Documentos": {},
        },
        "Preliminares": {
            "Demanda": {},
        },
        "Apelacion": {},
        "Ejecucion": {},
    },
    "Penal": {
        "1ª Instancia": {
            "Fase oral": {},
            "Instruccion": {
                "Denuncia": {},
            },
        },
        "Apelacion": {},
        "Ejecucion": {},
    },
}

# Mapping empírico id_carpeta (string numérico devuelto por
# /api/element_registries/gdocu) → ruta canónica dentro de 05_CRM/.
#
# El id_carpeta es una taxonomía GLOBAL del tenant (no es por-expediente): el
# mismo ID aparece en expedientes distintos (p. ej. 307 se observó en 657 y en
# 444). Por eso un mapping estático es válido. La etiqueta-hoja (DEMANDA,
# OPOSICION…) es ambigua entre ramas, así que el ID es la única clave fiable.
#
# Mappings cerrados con la regla de doble verificación (usuario en CRM UI +
# Claude vía REST):
#   - 2026-05-08: 1, 307 (expediente 657).
#   - 2026-06-10: 308, 380 (descubiertos vía evento `category_unknown`;
#     confirmados en UI). El endpoint de árbol `/api/folders/gdocu/{parent}`
#     NO devuelve la jerarquía (dead end, §13.3), por lo que la rama de una
#     hoja ambigua solo se cierra por verificación en UI.
# Nuevos IDs se descubren progresivamente vía evento `category_unknown` en
# _intake_log.jsonl (M10) + verificación UI.
CARPETA_ID_TO_PATH: dict[str, str] = {
    "1": "General",
    "307": "Civil/1ª Instancia/Declarativo/Demanda",
    "308": "Civil/1ª Instancia/Declarativo/Oposicion",
    "380": "Civil/Preliminares/Demanda",
}

# Roles válidos para la subcarpeta 06_Entrevistas/<YYYY-MM-DD>_<rol>_<apellido>/
# (M2 / P6, set cerrado). Reevaluar si surge un rol no contemplado (perito,
# tercero, etc.).
ENTREVISTA_ROLES: frozenset[str] = frozenset({
    "consultor",
    "director",
    "team_leader",
    "propietario",
    "buscador",
})

# Actores del despacho válidos para el selector M10 del sidebar Streamlit.
# Orden = rol/seniority (display order). Conjunto cerrado para que el log
# forense quede limpio de typos; la UI ofrece además "Otros…" como escape.
# Cada upload / pull / link emite un evento en `_intake_log.jsonl` con el
# actor activo (`intake_log.set_actor` sincroniza desde la UI cada render).
ACTORES_DESPACHO: tuple[str, ...] = (
    "Nikolai Tyukhay",          # Abogado Senior (Tyukhay Legal)
    "Karen Paola Barreto",      # Abogada (Tyukhay Legal)
    "Sergio Piñol",             # Abogado junior (Tyukhay Legal)
    "Ana Solange Velastegui",   # Administrativa (Tyukhay Legal)
    "Marta Reynares",           # Administrativa (Engel & Völkers)
)

# Tipos de caso para los que ensure_case() copia la plantilla
# data/_plantillas/informe_viabilidad.xlsx a 02_Analisis/_informe_viabilidad.xlsx
# (M1, copiado condicional). BAD_DEBT, LAU_20, DEVOLUCION_RESERVA y
# DEVOLUCION_HONORARIOS quedan fuera por decisión de producto.
INFORME_VIABILIDAD_TIPOS: frozenset[str] = frozenset({
    "NEGATIVA_OFERTA",
    "NEGATIVA_ARRAS",
    "NEGATIVA_ESCRITURA",
    "NEGATIVA_CONTRATO_ARRENDAMIENTO",
    "VUELTA",
    "INCUMPLIMIENTO_EXCLUSIVA",
    "RESPONSABILIDAD_PROFESIONAL",
})


# ---------------------------------------------------------------------------
# Shared Drive IDs del Drive engelvoelkers.com (remote gdrive_ev)
#
# Mapping equipo_code → Shared Drive ID.
# Obtenido con: rclone backend drives gdrive_ev:  (2026-04-29)
# None = Shared Drive no identificado — requiere introducción manual en UI.
# ---------------------------------------------------------------------------

DRIVE_EV_TEAM_IDS: dict[str, str | None] = {
    # ── Barcelona Residential Rentals ───────────────────────────────────────
    "BaRR1":  "0AD32Qb2sgwRPUk9PVA",   # Barcelona Rentals - R1
    "BaRR2":  "0AKR2FOV4YCODUk9PVA",   # Barcelona Rentals - R2
    "BaRR3":  "0AE-9XG_p0ERaUk9PVA",   # Barcelona Rentals - R3
    "BaRR4":  "0AF1OhJWdJxguUk9PVA",   # Barcelona Rentals - R4
    "BaRR10": "0APuQs9qUZ25tUk9PVA",   # Barcelona Rentals - R10
    # ── Barcelona Residential Sales ─────────────────────────────────────────
    "BaRS1":  "0ADrldKiH6lk5Uk9PVA",   # Barcelona - S1
    "BaRS2":  "0AEw_yWPTwm2pUk9PVA",   # Barcelona - S2
    "BaRS3":  "0AAPGi435EiuRUk9PVA",   # Barcelona - S3
    "BaRS4":  "0AF1OhJWdJxguUk9PVA",   # Barcelona Rentals - R4
    "BaRS5":  "0ABSsikBsoCoUUk9PVA",   # Barcelona - S5
    "BaRS6":  "0AFcFz9dooXbyUk9PVA",   # Barcelona - S6
    "BaRS7":  "0AGbBxb76Fl14Uk9PVA",   # Barcelona - S7
    "BaRS8":  "0AJGVcVJqtIgpUk9PVA",   # Barcelona - S8
    "BaRS9":  "0AFudh8LJ7y1kUk9PVA",   # Barcelona - S9
    "BaRS10": "0ANCaHYw47N_aUk9PVA",   # Barcelona - S10
    "BaRS11": "0AG2Z-PWFo9PHUk9PVA",   # Barcelona - S11
    "BaRS12": "0AGciVQvwEO3ZUk9PVA",   # Barcelona - S12
    # ── Barcelona Commercial ─────────────────────────────────────────────────
    "BaCR1":  "0AO2kC2doh2bpUk9PVA",   # BCN Comm - Propiedades
    "BaCR10": "0APxcQvRXJ8w_Uk9PVA",   # BCN Comm - MC2
    "BaCS1":  "0AO2kC2doh2bpUk9PVA",   # BCN Comm - Propiedades
    "BaCS10": "0APxcQvRXJ8w_Uk9PVA",   # BCN Comm - MC2
    # ── Barcelona Pendiente ──────────────────────────────────────────────────
    "BaDP1":  "0ADwt6QSqkvYXUk9PVA",   # Barcelona - PD1
    # ── Bilbao ───────────────────────────────────────────────────────────────
    "BiRS1":  "0APU1_XB6UB2WUk9PVA",   # Bilbao - S1
    "BiRS2":  "0AI7ThNrdHBBFUk9PVA",   # Bilbao - S2
    # ── Madrid Residential Rentals ───────────────────────────────────────────
    "MaRR1":  "0AA5B1lBGVwHzUk9PVA",   # Madrid - R1
    "MaRR2":  "0AMPTnhKWXMC_Uk9PVA",   # Madrid - R2
    "MaRR3":  "0AHmE27AuXAeeUk9PVA",   # Madrid - R3
    # ── Madrid Residential Sales ─────────────────────────────────────────────
    "MaRS1":  "0ALZysk_iHdzKUk9PVA",   # Madrid - S1
    "MaRS2":  "0AACVnfVQelcbUk9PVA",   # Madrid - S2
    "MaRS3":  "0AINsdi_58ooZUk9PVA",   # Madrid - S3
    "MaRS4":  "0AAfoBM86F2IBUk9PVA",   # Madrid - S4
    "MaRS5":  "0AHGeJ5ExBVAOUk9PVA",   # Madrid - S5
    "MaRS6":  "0AEuUTqdS_SlSUk9PVA",   # Madrid - S6
    "MaRS7":  "0AObhZ4KtWlKIUk9PVA",   # Madrid - S7
    "MaRS8":  "0AOXSD3P3OC1OUk9PVA",   # Madrid - S8
    "MaRS9":  "0ADvMel_HuihoUk9PVA",   # Madrid - S9
    "MaRS10": "0ABEaSgRKczw1Uk9PVA",   # Madrid - S10
    "MaRS11": "0AKTVQk7Rxw6pUk9PVA",   # Madrid - S11
    "MaRS12": "0AMKhFJmGDw-lUk9PVA",   # Madrid - S12
    "MaRS13": "0ALgE1v7V402eUk9PVA",   # Madrid - S13
    "MaRS14": "0ACrd4VNKpz43Uk9PVA",   # Madrid - S14
    "MaRS15": "0AJbQHw3Fn24RUk9PVA",   # Madrid - S15
    # ── Madrid Pendiente ─────────────────────────────────────────────────────
    "MaPD1":  "0ANRMr1sAL6DiUk9PVA",   # Madrid - PD1
    # ── San Sebastián ────────────────────────────────────────────────────────
    "SSRR1":  "0AGtY4pu8itx0Uk9PVA",   # San Sebastian - R1
    "SSRS1":  "0AEYW3gPNMOhrUk9PVA",   # San Sebastian - S1
    # ── Santander ────────────────────────────────────────────────────────────
    "SaRS1":  "0AEUJHKlwbQGUUk9PVA",   # Santander - S1
    # ── Sevilla (S1 y S6 comparten Shared Drive) ─────────────────────────────
    "SeRS1":  "0ABSFVWC_PfdBUk9PVA",   # Sevilla - S1 / S6
    "SeRS6":  "0ABSFVWC_PfdBUk9PVA",   # Sevilla - S1 / S6
    # ── Valencia ─────────────────────────────────────────────────────────────
    "VaCR1":  "0AKHkaZNM-iYtUk9PVA",   # Valencia - Commercial
    "VaCR2":  "0AKHkaZNM-iYtUk9PVA",   # Valencia - Commercial (mismo drive)
    "VaCS1":  "0AKHkaZNM-iYtUk9PVA",   # Valencia - Commercial (mismo drive)
    "VaPD1":  "0AKY5CXRI9bzNUk9PVA",   # Valencia - PD1
    "VaRR1":  "0AF3-W0dpQNIFUk9PVA",   # Valencia - R1
    "VaRR3":  "0AEHjRLJkpmlHUk9PVA",   # Valencia - R3
    "VaRS1":  "0AJMNkvj7zrzYUk9PVA",   # Valencia - S1
    "VaRS2":  "0AIJDXpIMN3ySUk9PVA",   # Valencia - S2
    "VaRS3":  "0AI05EoJNE-gdUk9PVA",   # Valencia - S3
    "VaRS4":  "0AEHRwRoH0ROdUk9PVA",   # Valencia - S4
    "VaRS5":  "0AJhYfh30xs85Uk9PVA",   # Valencia - S5
}
