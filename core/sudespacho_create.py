"""Creación de expedientes extrajudiciales en sudespacho.net desde FeesDefender.

Endpoint confirmado por captura DevTools el 2026-04-28:

    POST https://tnm.sudespacho.net/extrajudiciales/saveadd/elemento/extrajudiciales
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    Auth: cookie PHPSESSID + campo csrf_token en el body

La creación va por el FRONTAL HEREDADO (tnm.sudespacho.net), no por la API REST nueva.
Usa el mismo mecanismo de auth que sync_sudespacho_legacy.py.

Mapping de campos (confirmado con datos reales el 2026-04-28)
-------------------------------------------------------------
Los campos del formulario tienen IDs numéricos dinámicos (campo_XXXX__extrajudiciales).

    campo_1740  →  referencia_cliente
                   Identificador cruzado entre sudespacho, Drive y FeesDefender.
                   Formato taxonomía FeesDefender: "MaRS2 - Puerto Rico 2, 5º 2 - (W-0470GM) - Negativa arras"
                   Coincide con el case_id. Es el campo clave para trazar el expediente.

    campo_1731  →  fecha_apertura (formato DD-MM-YYYY)
    campo_1730  →  cuantia (entero sin separadores, ej: "12500")
                   Importe principal de la reclamación. Lo que sudespacho llama "Cuantía".
    campo_1729  →  costas (formato ES "0,00" por defecto; se actualiza al cierre)
    campo_1734  →  intereses (formato ES "0,00" por defecto)
    campo_1750  →  total_display = cuantia + costas + intereses (formato ES "12.500,00")
                   Lo que sudespacho llama "Total".
    campo_1748  →  materia ("Civil", "Penal", etc.)
    campo_1749  →  subtipo ("reclamacion extrajudicial", etc.)
    campo_1747  →  año (YYYY, para la numeración del expediente)
    campo_1737  →  nº expediente extrajudicial — auto-asignado por el servidor
                   El frontal envía el siguiente libre en el momento del submit;
                   el servidor asigna el definitivo. Enviar 0 es seguro.
    campo_2487  →  responsable (username del CRM, ej: "Nikolai_Tyukhay")
    campo_2488[]→  tags (formato "#{color_hex}___{tag_id}", último = "__void__")
    campo_1735  →  descripcion (HTML aceptado)
    campo_2586  →  posicion_procesal (01=Actor, 02=Demandado, 03=Querellante, ...)
                   Confirmado 2026-04-28. Ver constantes POSICION_*.
    campo_2587  →  0 (valor fijo; pendiente identificar)
    campo_1732  →  vacío (campo pendiente identificar)
    campo_1741  →  vacío (campo pendiente identificar)
    campo_1742  →  vacío (campo pendiente identificar)

Campos técnicos del formulario (fijos):
    ajax            → "true"
    csrf_token      → token extraído del HTML de la sesión (enviado 3 veces)
    momento_log     → hex único de timestamp (generado en cada submit)
    permisos_grupos[]   → [2]
    permisos_usuarios[] → [2]
    validar_formatos_nacionales → "false"
    cc-num          → "HubspotCollectedFormsWorkaround" (workaround antidetección)

Tags en sudespacho
------------------
Formato: "#{color_hex}___{tag_id}"   ej: "#528800___214"
Se pueden pasar múltiples tags como lista; el último elemento debe ser "__void__".

Ejemplo:
    campo_2488__extrajudiciales[] = #528800___214
    campo_2488__extrajudiciales[] = #a32929___135
    campo_2488__extrajudiciales[] = __void__

Pendiente confirmar
-------------------
- Shape exacto de la respuesta (Response tab en DevTools): ¿devuelve el ID?
- IDs de los tags CRM de FeesDefender (BAD DEBT, NEGATIVA OFERTA, etc.).
- Significado de campo_2586 (02) y campo_2587 (0).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .sync_sudespacho_legacy import (
    SudespachoLegacyClient,
    SudespachoLegacyError,
)


# ---------------------------------------------------------------------------
# Constantes del endpoint
# ---------------------------------------------------------------------------

_LEGACY_HOST = "tnm.sudespacho.net"   # leer de .env en producción
_ENDPOINT_CREATE = (
    "/extrajudiciales/saveadd/elemento/extrajudiciales"
)

# Nº expediente: auto-asignado por el servidor; enviar 0.
_CAMPO_FIJO_1737 = "0"
# campo_2587: valor fijo observado en todas las capturas, pendiente identificar.
_CAMPO_FIJO_2587 = "0"

# ---------------------------------------------------------------------------
# Posición procesal (campo_2586) — confirmado 2026-04-28
# ---------------------------------------------------------------------------

POSICION_ACTOR                   = "01"  # E&V reclama honorarios
POSICION_DEMANDADO               = "02"  # E&V es demandada
POSICION_QUERELLANTE             = "03"
POSICION_QUERELLADO              = "04"
POSICION_DENUNCIANTE             = "05"
POSICION_DENUNCIADO              = "06"
POSICION_RESPONSABLE_CIVIL_DIR   = "07"
POSICION_RESPONSABLE_CIVIL_SUB   = "08"

# Default según tipo de caso: actora → Actor, defensiva → Demandado.
# Ver también config.posicion_de_tipo().

# ---------------------------------------------------------------------------
# Materia (campo_1748) y tipo procedimiento (campo_1749) — confirmados
# ---------------------------------------------------------------------------

# Materia (campo_1748)
MATERIA_CIVIL           = "Civil"
MATERIA_PENAL           = "Penal"
MATERIA_ADMINISTRATIVO  = "Administrativo"
MATERIA_LABORAL         = "Laboral"
MATERIA_FAMILIA         = "4"          # El valor es el ID numérico, no el texto
MATERIA_FISCAL          = "fiscal"
MATERIA_BANCARIO        = "bancario"
MATERIA_HERENCIA        = "herencia"

# Tipo procedimiento (campo_1749) — valores relevantes para E&V
SUBTIPO_EXTRAJUDICIAL   = "reclamacion extrajudicial"   # Default E&V
SUBTIPO_JUICIO_ORDINARIO = "procedimiento juicio ordinario"
SUBTIPO_JUICIO_VERBAL   = "procedimiento juicio verbal"
SUBTIPO_MONITORIO       = "procedimiento monitorio"
SUBTIPO_DESAHUCIO       = "procedimiento desahucio"
SUBTIPO_APELACION       = "procedimiento recurso apelacion"

# Formato de importes: sudespacho espera número entero para el campo
# de base y "N.NNN,NN" (con punto de miles y coma decimal) para el campo
# de display. Locales ES.
_LOCALE_THOUSANDS = "."
_LOCALE_DECIMAL = ","


# ---------------------------------------------------------------------------
# Grupos y usuarios — IDs confirmados en el tenant tnm
# ---------------------------------------------------------------------------

# Grupos (permisos_grupos[])
GRUPO_OFICINA_1           = 2
GRUPO_DIRECCION_CONTAB    = 7

# Usuarios (permisos_usuarios[])
USUARIO_NIKOLAI_TYUKHAY   = 2
USUARIO_PAOLA_BARRETO     = 17

# Defaults para nuevos expedientes E&V
GRUPOS_DEFAULT   = [GRUPO_OFICINA_1]
USUARIOS_DEFAULT = [USUARIO_NIKOLAI_TYUKHAY]


# ---------------------------------------------------------------------------
# Tags — lista completa confirmada contra tenant tnm (Engel & Völkers)
# ---------------------------------------------------------------------------
#
# Fuente: selectize options del formulario de alta extrajudicial en tnm.sudespacho.net
# Capturado el 2026-04-28. Total: 80 tags activos.
#
# Formato: "#{color_hex}___{tag_id}"
# El último elemento de cualquier lista de tags DEBE ser TAG_SENTINEL ("__void__").
# Orden canónico por expediente (Manual Gestión Interna):
#   (i) Equipo/rojo  →  (ii) Asunto/verde  →  (iii) Valoración/azul o lila

TAG_SENTINEL = "__void__"   # Siempre el último elemento de la lista de tags

# -- Verde (#528800): Tipo de asunto (caso de E&V) — 9 de los 18 verdes son FeesDefender
TAG_VERDE_BAD_DEBT                  = "#528800___110"   # BAD DEBT
TAG_VERDE_NEGATIVA_OFERTA           = "#528800___129"   # NEGATIVA OFERTA
TAG_VERDE_NEGATIVA_ARRAS            = "#528800___127"   # NEGATIVA ARRAS
TAG_VERDE_NEGATIVA_ESCRITURA        = "#528800___161"   # NEGATIVA ESCRITURA
TAG_VERDE_VUELTA                    = "#528800___95"    # VUELTA
TAG_VERDE_INCUMPLIMIENTO_EXCLUSIVA  = "#528800___170"   # INCUMPLIMIENTO EXCLUSIVA
TAG_VERDE_RESPONSABILIDAD_PROF      = "#528800___123"   # RESPONSABILIDAD PROFESIONAL
TAG_VERDE_DEVOLUCION_RESERVA        = "#528800___125"   # DEVOLUCIÓN RESERVA
TAG_VERDE_LAU_20                    = "#528800___214"   # LAU 20
TAG_VERDE_DEVOLUCION_HONORARIOS     = "#528800___126"   # DEVOLUCION HONORARIOS
TAG_VERDE_CONSULTORES               = "#528800___194"   # CONSULTORES
TAG_VERDE_NEGATIVA_CONTRATO_ARR     = "#528800___155"   # NEGATIVA CONTRATO ARRENDAMIENTO (color cambiado rojo→verde 2026-04-28)
TAG_VERDE_FRANQUICIA                = "#528800___295"   # FRANQUICIA (creado 2026-04-28)

# -- Lila (#5229a3): Valoración de riesgo — SOLO para casos DEFENSIVOS (3 tags) --
#
# DEFENSIVA — E&V es demandada. Reglas del Manual Gestión Interna:
#   RIESGO REMOTO   <15%:  acuerdo extrajudicial OR >2 años sin actividad procesal.
#   RIESGO POSIBLE  15-50%: TODOS LOS DEMÁS CASOS. ← DEFAULT.
#   RIESGO PROBABLE >50%:  "si fuera el abogado del demandante, recomendaría reclamar".
#
# ⚠️ No hay tags lila para casos ACTORES. La valoración de éxito actora usa azul.
TAG_LILA_RIESGO_REMOTO      = "#5229a3___216"   # Defensiva: <15% (acuerdo extraj. o +2 años)
TAG_LILA_RIESGO_POSIBLE     = "#5229a3___217"   # Defensiva: 15-50% — DEFAULT
TAG_LILA_RIESGO_PROBABLE    = "#5229a3___218"   # Defensiva: >50% (recomendaríamos reclamar)
TAG_LILA_POSIBILIDAD_50     = "#5229a3___286"   # Actora: DEFAULT todos los nuevos (=50%) — color cambiado azul→lila 2026-04-28

# -- Azul (#5b9bd1): Ciudad + probabilidad de éxito actora (10 tags) ----------
#
# Ciudades (plazas E&V):
TAG_AZUL_MADRID          = "#5b9bd1___258"   # Madrid
TAG_AZUL_VALENCIA        = "#5b9bd1___257"   # Valencia
TAG_AZUL_SEVILLA         = "#5b9bd1___291"   # Sevilla (creado 2026-04-28)
TAG_AZUL_BILBAO          = "#5b9bd1___292"   # Bilbao (creado 2026-04-28)
TAG_AZUL_SAN_SEBASTIAN   = "#5b9bd1___293"   # San Sebastián (creado 2026-04-28)
TAG_AZUL_SANTANDER       = "#5b9bd1___294"   # Santander (creado 2026-04-28)
TAG_AZUL_BARCELONA       = "#5b9bd1___296"   # Barcelona (creado 2026-04-28)

# Los tags <15%→50% y <15% NO existen aún en el CRM (2026-04-28).

# -- Rojo (#a32929): Equipos comerciales + tipo especial (49 tags) ------------
#
# Nomenclatura: {ciudad(2)}{tipo_op(2)}{nº}
#   Ba = Barcelona | Ma = Madrid | Bi = Bilbao | Sa = Santander | Se = Sevilla | Va = Valencia
#   RR = Residential Rentals | RS = Residential Sales | CR = Commercial Rentals
#   CS = Commercial Sales | PD = (pendiente confirmar)
#
# Barcelona Residential Rentals
TAG_ROJO_BaRR1  = "#a32929___135"
TAG_ROJO_BaRR3  = "#a32929___113"
TAG_ROJO_BaRR4  = "#a32929___175"
# Barcelona Residential Sales
TAG_ROJO_BaRS1  = "#a32929___156"
TAG_ROJO_BaRS2  = "#a32929___140"
TAG_ROJO_BaRS3  = "#a32929___128"
TAG_ROJO_BaRS4  = "#a32929___163"
TAG_ROJO_BaRS5  = "#a32929___112"   # BaRS5 (ID 122 eliminado del CRM 2026-04-28)
TAG_ROJO_BaRS6  = "#a32929___97"
TAG_ROJO_BaRS7  = "#a32929___134"
TAG_ROJO_BaRS8  = "#a32929___138"
TAG_ROJO_BaRS9  = "#a32929___137"
TAG_ROJO_BaRS10 = "#a32929___131"
TAG_ROJO_BaRS11 = "#a32929___94"
TAG_ROJO_BaRS12 = "#a32929___162"
# Barcelona Commercial Rentals
TAG_ROJO_BaCR1  = "#a32929___172"
TAG_ROJO_BaCR10 = "#a32929___287"
# Barcelona Commercial Sales
TAG_ROJO_BaCS1  = "#a32929___136"
TAG_ROJO_BaCS10 = "#a32929___139"
# Bilbao Residential Sales
TAG_ROJO_BiRS1  = "#a32929___273"
TAG_ROJO_BiRS2  = "#a32929___268"
# Madrid Residential Rentals
TAG_ROJO_MaRR1  = "#a32929___119"
TAG_ROJO_MaRR2  = "#a32929___118"
TAG_ROJO_MaRR3  = "#a32929___225"
# Madrid Residential Sales
TAG_ROJO_MaRS1  = "#a32929___96"
TAG_ROJO_MaRS2  = "#a32929___117"
TAG_ROJO_MaRS3  = "#a32929___115"
TAG_ROJO_MaRS4  = "#a32929___116"
TAG_ROJO_MaRS5  = "#a32929___133"
TAG_ROJO_MaRS6  = "#a32929___130"
TAG_ROJO_MaRS7  = "#a32929___141"
TAG_ROJO_MaRS8  = "#a32929___236"
TAG_ROJO_MaRS9  = "#a32929___120"
TAG_ROJO_MaRS10 = "#a32929___106"
TAG_ROJO_MaRS13 = "#a32929___190"
TAG_ROJO_MaRS14 = "#a32929___189"
# Santander Residential Sales
TAG_ROJO_SaRS1  = "#a32929___276"
# San Sebastián Residential Rentals / Sales (creados 2026-04-28)
TAG_ROJO_SSRR1  = "#a32929___289"
TAG_ROJO_SSRS1  = "#a32929___290"
# Sevilla Residential Sales
TAG_ROJO_SeRS1  = "#a32929___230"
TAG_ROJO_SeRS6  = "#a32929___285"
# Valencia Commercial Rentals
TAG_ROJO_VaCR1  = "#a32929___132"
# Valencia (PD — tipo pendiente confirmar)
TAG_ROJO_VaPD1  = "#a32929___178"
# Valencia Residential Rentals
TAG_ROJO_VaRR1  = "#a32929___104"
# Valencia Residential Sales
TAG_ROJO_VaRS1  = "#a32929___99"
TAG_ROJO_VaRS2  = "#a32929___102"
TAG_ROJO_VaRS3  = "#a32929___103"
TAG_ROJO_VaRS4  = "#a32929___114"
TAG_ROJO_VaRS5  = "#a32929___271"


# ---------------------------------------------------------------------------
# Tags judiciales — grupo 2  (IDs DISTINTOS del grupo extrajudicial)
# ---------------------------------------------------------------------------
# Fuente: select campo_2486 del formulario de alta judicial, capturado 2026-04-30
# Total: 78 tags activos. Completamente distintos al grupo extrajudicial (grupo 1).
#
# ⚠️ CIUDAD: el grupo judicial NO tiene tags de ciudad (Madrid, Barcelona...).
#    Hay que crearlos vía POST /tagsinput/saveadd/... (pendiente 2026-04-30).
# ⚠️ EQUIPOS faltantes respecto al grupo extrajudicial:
#    BiRS1, BiRS2, SaRS1, SeRS6, SSRR1, SSRS1, VaRS5, MaRS11, MaRS12, MaRS13
#    (MaRS15 SÍ existe en judicial con ID 63, aunque no existe en extrajudicial)

# -- Verde (#528800): Tipo de asunto (14 tags) --------------------------------
J_TAG_VERDE_BAD_DEBT                  = "#528800___12"
J_TAG_VERDE_DEVOLUCION_RESERVA        = "#528800___24"
J_TAG_VERDE_DEVOLUCION_HONORARIOS     = "#528800___55"
J_TAG_VERDE_INCUMPLIMIENTO_EXCLUSIVA  = "#528800___62"
J_TAG_VERDE_VUELTA                    = "#528800___1"
J_TAG_VERDE_LAU_20                    = "#528800___227"
J_TAG_VERDE_CONSULTORES               = "#528800___210"
J_TAG_VERDE_NEGATIVA_ARRAS            = "#528800___180"
J_TAG_VERDE_NEGATIVA_ESCRITURA        = "#528800___184"
J_TAG_VERDE_NEGATIVA_OFERTA           = "#528800___197"
J_TAG_VERDE_RESPONSABILIDAD_PROF      = "#528800___19"
J_TAG_VERDE_PARTICULAR                = "#528800___10"
J_TAG_VERDE_LABORAL                   = "#528800___196"
J_TAG_VERDE_INSPECCION_LABORAL_VA     = "#528800___238"

# NEGATIVA CONTRATO ARRENDAMIENTO es AZUL en judicial (distinto de extrajudicial donde es rojo)
J_TAG_AZUL_NEGATIVA_CONTRATO_ARR      = "#5b9bd1___283"

# FRANQUICIA es rojo en grupo judicial (igual que en extrajudicial)
J_TAG_ROJO_J_FRANQUICIA               = "#a32929___7"

# -- Lila (#5229a3): Valoración de riesgo / probabilidad de éxito (6 tags) ---
#
# Defensiva (E&V demandada):
J_TAG_LILA_RIESGO_REMOTO              = "#5229a3___219"   # <15%
J_TAG_LILA_RIESGO_POSIBLE             = "#5229a3___220"   # <15%-50% — DEFAULT defensiva
J_TAG_LILA_RIESGO_PROBABLE            = "#5229a3___221"   # >50%
# Actora (E&V reclama):
J_TAG_LILA_POSIBILIDAD_50             = "#5229a3___259"   # =50% — DEFAULT actora
J_TAG_LILA_POSIBILIDAD_15_50          = "#5229a3___260"   # <15%-50%
J_TAG_LILA_POSIBILIDAD_LT_15          = "#5229a3___261"   # <15%

# -- Rojo (#a32929): Equipos comerciales (44 tags) ----------------------------
# Barcelona
J_TAG_ROJO_BaCR1  = "#a32929___32"
J_TAG_ROJO_BaCR10 = "#a32929___195"
J_TAG_ROJO_BaCS1  = "#a32929___101"
J_TAG_ROJO_BaDP1  = "#a32929___56"     # tipo op. pendiente confirmar
J_TAG_ROJO_BaRR1  = "#a32929___33"
J_TAG_ROJO_BaRR2  = "#a32929___34"     # existe en judicial, NO en extrajudicial
J_TAG_ROJO_BaRR3  = "#a32929___39"
J_TAG_ROJO_BaRR4  = "#a32929___82"     # existe en judicial, NO en extrajudicial
J_TAG_ROJO_BaRS1  = "#a32929___46"
J_TAG_ROJO_BaRS2  = "#a32929___30"
J_TAG_ROJO_BaRS3  = "#a32929___37"
J_TAG_ROJO_BaRS5  = "#a32929___45"
J_TAG_ROJO_BaRS6  = "#a32929___25"
J_TAG_ROJO_BaRS7  = "#a32929___29"
J_TAG_ROJO_BaRS8  = "#a32929___185"
J_TAG_ROJO_BaRS9  = "#a32929___35"
J_TAG_ROJO_BaRS10 = "#a32929___57"
J_TAG_ROJO_BaRS11 = "#a32929___121"
J_TAG_ROJO_BaRS12 = "#a32929___192"
# Madrid
J_TAG_ROJO_MaPD1  = "#a32929___75"
J_TAG_ROJO_MaRR1  = "#a32929___41"
J_TAG_ROJO_MaRR3  = "#a32929___191"
J_TAG_ROJO_MaRS1  = "#a32929___52"
J_TAG_ROJO_MaRS2  = "#a32929___60"
J_TAG_ROJO_MaRS3  = "#a32929___72"     # ⚠️ ID 26 también es MaRS3 en el CRM (duplicado)
J_TAG_ROJO_MaRS4  = "#a32929___73"
J_TAG_ROJO_MaRS5  = "#a32929___71"
J_TAG_ROJO_MaRS6  = "#a32929___54"
J_TAG_ROJO_MaRS7  = "#a32929___51"
J_TAG_ROJO_MaRS8  = "#a32929___53"
J_TAG_ROJO_MaRS9  = "#a32929___58"
J_TAG_ROJO_MaRS10 = "#a32929___61"
J_TAG_ROJO_MaRS14 = "#a32929___74"
J_TAG_ROJO_MaRS15 = "#a32929___63"    # existe en judicial, NO en extrajudicial
# Bilbao Residential Sales (creados 2026-05-04)
J_TAG_ROJO_BiRS1  = "#a32929___304"
J_TAG_ROJO_BiRS2  = "#a32929___305"
# Santander Residential Sales (creado 2026-05-04)
J_TAG_ROJO_SaRS1  = "#a32929___306"
# Sevilla
J_TAG_ROJO_SeRS1  = "#a32929___239"
J_TAG_ROJO_SeRS6  = "#a32929___307"   # creado 2026-05-04
# San Sebastián (creados 2026-05-04)
J_TAG_ROJO_SSRR1  = "#a32929___308"
J_TAG_ROJO_SSRS1  = "#a32929___309"
# Madrid Residential Sales adicionales (creados 2026-05-04)
J_TAG_ROJO_MaRS11 = "#a32929___311"
J_TAG_ROJO_MaRS12 = "#a32929___312"
J_TAG_ROJO_MaRS13 = "#a32929___313"
# Valencia
J_TAG_ROJO_VaCR1  = "#a32929___78"
J_TAG_ROJO_VaCR2  = "#a32929___47"
J_TAG_ROJO_VaPD1  = "#a32929___182"
J_TAG_ROJO_VaRR1  = "#a32929___42"
J_TAG_ROJO_VaRR3  = "#a32929___43"
J_TAG_ROJO_VaRS1  = "#a32929___36"
J_TAG_ROJO_VaRS2  = "#a32929___31"
J_TAG_ROJO_VaRS3  = "#a32929___44"
J_TAG_ROJO_VaRS4  = "#a32929___59"
J_TAG_ROJO_VaRS5  = "#a32929___310"   # creado 2026-05-04

# -- Azul (#5b9bd1): Equipos con color azul en grupo judicial --------
# (Algunos equipos que son ROJOS en extrajudicial son AZULES en judicial)
J_TAG_AZUL_BaRR10 = "#5b9bd1___265"
J_TAG_AZUL_BaCS2  = "#5b9bd1___279"
J_TAG_AZUL_BaRS4  = "#5b9bd1___275"   # BaRS4: ROJO en extrajudicial, AZUL en judicial
J_TAG_AZUL_MaRR2  = "#5b9bd1___266"   # MaRR2: ROJO en extrajudicial, AZUL en judicial
J_TAG_AZUL_VaCS1  = "#5b9bd1___278"

# -- Azul (#5b9bd1): Tags de CIUDAD en grupo judicial (creados 2026-05-04) ----
J_TAG_AZUL_CIUDAD_MADRID        = "#5b9bd1___297"
J_TAG_AZUL_CIUDAD_VALENCIA      = "#5b9bd1___298"
J_TAG_AZUL_CIUDAD_BARCELONA     = "#5b9bd1___299"
J_TAG_AZUL_CIUDAD_SAN_SEBASTIAN = "#5b9bd1___300"
J_TAG_AZUL_CIUDAD_BILBAO        = "#5b9bd1___301"
J_TAG_AZUL_CIUDAD_SANTANDER     = "#5b9bd1___302"
J_TAG_AZUL_CIUDAD_SEVILLA       = "#5b9bd1___303"

# Mapa tipo_caso → tag verde para expedientes judiciales.
# Parallel a _TIPO_A_TAG_VERDE del grupo extrajudicial.
_TIPO_A_TAG_VERDE_J: dict[str, str | None] = {
    "BAD_DEBT":                         J_TAG_VERDE_BAD_DEBT,
    "NEGATIVA_OFERTA":                  J_TAG_VERDE_NEGATIVA_OFERTA,
    "NEGATIVA_ARRAS":                   J_TAG_VERDE_NEGATIVA_ARRAS,
    "NEGATIVA_ESCRITURA":               J_TAG_VERDE_NEGATIVA_ESCRITURA,
    "NEGATIVA_CONTRATO_ARRENDAMIENTO":  J_TAG_AZUL_NEGATIVA_CONTRATO_ARR,
    "VUELTA":                           J_TAG_VERDE_VUELTA,
    "INCUMPLIMIENTO_EXCLUSIVA":         J_TAG_VERDE_INCUMPLIMIENTO_EXCLUSIVA,
    "RESPONSABILIDAD_PROFESIONAL":      J_TAG_VERDE_RESPONSABILIDAD_PROF,
    "DEVOLUCION_RESERVA":               J_TAG_VERDE_DEVOLUCION_RESERVA,
    "LAU_20":                           J_TAG_VERDE_LAU_20,
    "DEVOLUCION_HONORARIOS":            J_TAG_VERDE_DEVOLUCION_HONORARIOS,
    "CONSULTORES":                      J_TAG_VERDE_CONSULTORES,
    "FRANQUICIA":                       J_TAG_ROJO_J_FRANQUICIA,
}


def tag_defaults_for_tipo_caso_judicial(tipo_caso: str) -> list[str]:
    """Equivalente judicial de `tag_defaults_for_tipo_caso()`.

    Usa los IDs del grupo 2 (tags judiciales), completamente distintos
    del grupo 1 (extrajudicial).

    Args:
        tipo_caso: Clave de config.TIPOS_CASO_ALL (ej. "DEVOLUCION_RESERVA").

    Returns:
        Lista [tag_asunto, tag_valoracion] (sin sentinel).
    """
    from . import config

    posicion_cfg = config.posicion_de_tipo(tipo_caso)

    asunto_tag = _TIPO_A_TAG_VERDE_J.get(tipo_caso)

    if posicion_cfg == config.POSICION_ACTORA:
        valoracion_tag = J_TAG_LILA_POSIBILIDAD_50
    else:
        valoracion_tag = J_TAG_LILA_RIESGO_POSIBLE

    tags: list[str] = []
    if asunto_tag is not None:
        tags.append(asunto_tag)
    tags.append(valoracion_tag)
    return tags


# ---------------------------------------------------------------------------
# Tipos de procedimiento judicial (campo_878)
# ---------------------------------------------------------------------------

TIPO_PROC_DILIGENCIAS_PREVIAS          = "Diligencias Previas"
TIPO_PROC_JUICIO_VERBAL                = "procedimiento juicio verbal"    # E&V más frecuente
TIPO_PROC_JUICIO_ORDINARIO             = "procedimiento juicio ordinario"
TIPO_PROC_MONITORIO                    = "procedimiento monitorio"
TIPO_PROC_DESAHUCIO                    = "procedimiento desahucio"
TIPO_PROC_APELACION                    = "procedimiento recurso apelacion"
TIPO_PROC_CONCILIACION                 = "procedimiento conciliacion"
TIPO_PROC_EJECUCION                    = "procedimiento ejecucion titulos judiciales"
TIPO_PROC_RECLAMACION_EXTRAJUDICIAL    = "reclamacion extrajudicial"

# Tipo de procedimiento recomendado para DEVOLUCION_RESERVA (Juicio Verbal <6000€)
TIPO_PROC_DEFAULT_EV                   = TIPO_PROC_JUICIO_VERBAL

# ---------------------------------------------------------------------------
# Endpoint de creación judicial
# ---------------------------------------------------------------------------

_ENDPOINT_CREATE_JUDICIAL = (
    "/expedientesjudiciales/saveadd/elemento/expedientes_judiciales"
)


# ---------------------------------------------------------------------------
# DTO expediente judicial
# ---------------------------------------------------------------------------

@dataclass
class NuevoExpedienteJudicial:
    """Datos necesarios para crear un expediente judicial en sudespacho.

    El campo clave es `referencia_cliente` (campo_867): debe coincidir con
    el case_id de FeesDefender. Para E&V, formato taxonomía:
        "MaRS2 - Puerto Rico 2, 5º 2 - (W-0470GM) - Devolucion reserva"

    Diferencias respecto al extrajudicial:
    - Tiene NIG, referencia_propia, numero_anterior, tipo_procedimiento.
    - El responsable se llama "abogado_principal" (campo_866, select de usuarios).
    - Las tags usan campo_2486 con IDs del grupo judicial (J_TAG_*).
    - No tiene campo_1749 (subtipo); en su lugar, campo_878 (tipo_procedimiento).
    """
    referencia_cliente: str               # → campo_867
    fecha_apertura: date = field(default_factory=date.today)

    # Tags CRM del grupo judicial (J_TAG_*). NO usar TAG_* del grupo extrajudicial.
    tags: list[str] = field(default_factory=list)

    # Tipo de procedimiento (select campo_878)
    tipo_procedimiento: str = TIPO_PROC_JUICIO_VERBAL

    # Tipo de asunto (select campo_876)
    tipo_asunto: str = MATERIA_CIVIL

    # Posición procesal (select campo_2485)
    posicion: str = POSICION_DEMANDADO    # E&V suele ser demandada en judiciales

    # Campos específicos judiciales
    NIG: str = ""                          # → campo_860 (Número de Identificación del Juicio)
    referencia_propia: str = ""            # → campo_870
    referencia_procurador: str = ""        # → campo_869

    # Importes
    cuantia: float = 0.0                   # → campo_849
    costas: float = 0.0                    # → campo_848
    intereses: float = 0.0                 # → campo_856

    # Abogado principal (username del CRM, campo_866)
    abogado_principal: str = "Nikolai_Tyukhay"

    # Notas (HTML)
    notas_html: str = ""                   # → campo_861

    # Permisos (mismos defaults que extrajudicial)
    grupos: list[int] = field(default_factory=lambda: list(GRUPOS_DEFAULT))
    usuarios: list[int] = field(default_factory=lambda: list(USUARIOS_DEFAULT))


# ---------------------------------------------------------------------------
# Builder de form-data judicial
# ---------------------------------------------------------------------------

def build_form_data_judicial(
    datos: NuevoExpedienteJudicial,
    csrf_token: str,
) -> list[tuple[str, str]]:
    """Construye el body form-urlencoded para crear un expediente judicial.

    Campos confirmados el 2026-04-30 por fetch del formulario de alta.
    Endpoint: POST /expedientesjudiciales/saveadd/elemento/expedientes_judiciales

    Args:
        datos: Datos del expediente judicial.
        csrf_token: Token CSRF extraído de la sesión PHP activa.

    Returns:
        Lista de tuplas (campo, valor) para pasar a httpx/requests.
    """
    fecha_str = datos.fecha_apertura.strftime("%d-%m-%Y")
    año_str = str(datos.fecha_apertura.year)
    momento = hex(int(time.time()))[2:]

    total = datos.cuantia + datos.costas + datos.intereses

    tags = list(datos.tags)
    tags_con_sentinel = tags + [TAG_SENTINEL]

    form: list[tuple[str, str]] = [
        # Datos básicos
        ("campo_851__expedientes_judiciales",  fecha_str),
        ("campo_864__expedientes_judiciales",  "0"),        # num_expediente: auto-asignado
        ("campo_875__expedientes_judiciales",  año_str),    # serie expediente
        ("campo_860__expedientes_judiciales",  datos.NIG),
        # campos ocultos del formulario (valores por defecto observados)
        ("campo_855__expedientes_judiciales",  "No"),       # Historico: No por defecto
        ("campo_852__expedientes_judiciales",  ""),         # fecha_alta_hist: vacío
        ("campo_868__expedientes_judiciales",  ""),         # referencia_historico: vacío
        # Datos del expediente
        ("valor_select",                       "1"),
        ("etiqueta_select",                    ""),
        ("campo_876__expedientes_judiciales",  datos.tipo_asunto),
        ("campo_867__expedientes_judiciales",  datos.referencia_cliente),
        ("campo_869__expedientes_judiciales",  datos.referencia_procurador),
        # campo_847 (Siniestro) oculto — No por defecto
        ("campo_847__expedientes_judiciales",  "No"),
        ("valor_select",                       "1"),
        ("etiqueta_select",                    ""),
        ("campo_878__expedientes_judiciales",  datos.tipo_procedimiento),
        ("campo_870__expedientes_judiciales",  datos.referencia_propia),
        ("campo_862__expedientes_judiciales",  ""),         # numero_anterior: vacío
        ("campo_2485__expedientes_judiciales", datos.posicion),
        ("campo_866__expedientes_judiciales",  datos.abogado_principal),
        # Cuantías
        ("campo_849__expedientes_judiciales",  _fmt_importe_entero(datos.cuantia)),
        ("campo_848__expedientes_judiciales",  _fmt_importe_entero(datos.costas)),
        ("campo_856__expedientes_judiciales",  _fmt_importe_entero(datos.intereses)),
        ("campo_879__expedientes_judiciales",  _fmt_importe_display(total)),
    ]

    # Tags (clave repetida, termina en __void__)
    for tag in tags_con_sentinel:
        form.append(("campo_2486__expedientes_judiciales[]", tag))

    form += [
        # Notas
        ("campo_861__expedientes_judiciales",  datos.notas_html),
    ]

    # Permisos
    for gid in datos.grupos:
        form.append(("permisos_grupos[]", str(gid)))
    for uid in datos.usuarios:
        form.append(("permisos_usuarios[]", str(uid)))

    form += [
        ("csrf_token",                    csrf_token),
        ("cc-num",                        "HubspotCollectedFormsWorkaround"),
        ("momento_log",                   momento),
        ("",                              ""),
        ("",                              ""),
        ("ajax",                          "true"),
        ("csrf_token",                    csrf_token),
        ("validar_formatos_nacionales",   "false"),
        ("csrf_token",                    csrf_token),
    ]

    return form


# ---------------------------------------------------------------------------
# Función principal: crear expediente judicial
# ---------------------------------------------------------------------------

def create_expediente_judicial(
    datos: NuevoExpedienteJudicial,
    *,
    legacy_client: SudespachoLegacyClient | None = None,
    legacy_host: str | None = None,
) -> str:
    """Crea un expediente judicial en sudespacho.net.

    Usa el frontal heredado (mismo mecanismo que create_expediente).
    El CSRF token se extrae automáticamente de la sesión PHP activa.

    Args:
        datos: Datos del nuevo expediente judicial.
        legacy_client: Cliente legacy reutilizable (opcional).
        legacy_host: Host del tenant (opcional).

    Returns:
        ID numérico del expediente creado (str).

    Raises:
        SudespachoCreateError: si la creación falla o la respuesta no contiene el ID.
        SudespachoLegacyError: si la sesión PHP ha expirado.

    Example::

        from core.sudespacho_create import (
            create_expediente_judicial, NuevoExpedienteJudicial,
            tag_defaults_for_tipo_caso_judicial, J_TAG_ROJO_MaRS6,
            TIPO_PROC_JUICIO_VERBAL, POSICION_DEMANDADO,
        )

        tags = [J_TAG_ROJO_MaRS6] + tag_defaults_for_tipo_caso_judicial("DEVOLUCION_RESERVA")
        eid = create_expediente_judicial(NuevoExpedienteJudicial(
            referencia_cliente="MaRS6 - Calle Mayor 10 - (W-031ABC) - Devolucion reserva",
            tipo_procedimiento=TIPO_PROC_JUICIO_VERBAL,
            posicion=POSICION_DEMANDADO,
            cuantia=3500.00,
            tags=tags,
        ))
        # eid → "700"
    """
    owns_client = legacy_client is None
    try:
        client = legacy_client or SudespachoLegacyClient()
    except SudespachoLegacyError as exc:
        raise SudespachoCreateError(
            f"No se pudo inicializar el cliente legacy: {exc}. "
            "Revisa SUDESPACHO_LEGACY_PHPSESSID en .env."
        ) from exc

    try:
        try:
            csrf_token = client.get_csrf_token()
        except SudespachoLegacyError as exc:
            raise SudespachoCreateError(
                f"No se pudo obtener el CSRF token: {exc}"
            ) from exc

        form_data = build_form_data_judicial(datos, csrf_token)

        url = f"https://{legacy_host or client.host}{_ENDPOINT_CREATE_JUDICIAL}"
        try:
            response = client.post_form(url, form_data)
        except SudespachoLegacyError as exc:
            raise SudespachoCreateError(
                f"POST {_ENDPOINT_CREATE_JUDICIAL} falló: {exc}"
            ) from exc

        expediente_id = extract_id_from_response(response)
        if not expediente_id:
            raise SudespachoCreateError(
                f"Expediente judicial creado pero no se pudo extraer su ID. "
                f"Respuesta: {str(response)[:400]}."
            )

        return expediente_id

    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def format_tag(color_hex: str, tag_id: str | int) -> str:
    """Construye el token de tag esperado por sudespacho.

    Args:
        color_hex: ej. "#528800" (con #)
        tag_id: ID numérico del tag en el CRM

    Returns:
        Cadena con formato "#{color_hex}___{tag_id}"
    """
    return f"{color_hex}___{tag_id}"


# ---------------------------------------------------------------------------
# Formateadores de importe
# ---------------------------------------------------------------------------

def _fmt_importe_entero(importe: float) -> str:
    """Devuelve el importe como entero (sin decimales).
    Sudespacho usa este formato en campo_1730.
    """
    return str(int(round(importe)))


def _fmt_importe_display(importe: float) -> str:
    """Devuelve el importe en formato español: "2.000,00".
    Sudespacho usa este formato en campo_1750.
    """
    # Separar parte entera y decimal
    cents = round(importe * 100)
    euros = cents // 100
    dec = cents % 100
    # Formatear con punto de miles
    entero_str = f"{euros:,}".replace(",", _LOCALE_THOUSANDS)
    return f"{entero_str}{_LOCALE_DECIMAL}{dec:02d}"


# ---------------------------------------------------------------------------
# DTO de entrada
# ---------------------------------------------------------------------------

@dataclass
class NuevoExpedienteExtrajudicial:
    """Datos necesarios para crear un expediente extrajudicial en sudespacho.

    El campo clave es `referencia_cliente`: debe coincidir con el case_id de
    FeesDefender y seguir la taxonomía:
        "MaRS2 - Puerto Rico 2, 5º 2 - (W-0470GM) - Negativa arras"

    Este campo es el identificador cruzado entre sudespacho, Drive E&V y FeesDefender.
    """
    referencia_cliente: str              # case_id en taxonomía FeesDefender → campo_1740
    cuantia: float = 0.0                 # Importe principal reclamado (€) → campo_1730 (entero)
    fecha_apertura: date = field(default_factory=date.today)

    # Tags CRM (lista de tokens "#{color}___{id}"). Usar constantes TAG_* o format_tag().
    tags: list[str] = field(default_factory=list)

    # Importes secundarios (enteros; campo_1750 Total = cuantia + costas + intereses)
    costas: float = 0.0                  # → campo_1729 (entero)
    intereses: float = 0.0               # → campo_1734 (entero)

    # Permisos de acceso al expediente en el CRM
    # IDs confirmados en el tenant tnm:
    #   Grupos:   2 = OFICINA_1   |   7 = DIRECCION+CONTABILIDAD
    #   Usuarios: 2 = Nikolai_Tyukhay   |   17 = Paola_Barreto
    grupos: list[int] = field(default_factory=lambda: list(GRUPOS_DEFAULT))    # permisos_grupos[]
    usuarios: list[int] = field(default_factory=lambda: list(USUARIOS_DEFAULT)) # permisos_usuarios[]

    # Posición procesal → campo_2586 (confirmada 2026-04-28)
    # Usar constantes POSICION_*. Default: POSICION_ACTOR para asuntos actora.
    # Para asuntos defensiva usar POSICION_DEMANDADO.
    # Ver también config.posicion_de_tipo() para derivarlo del tipo de caso.
    posicion: str = POSICION_ACTOR       # → campo_2586

    # Datos opcionales
    descripcion_html: str = ""           # HTML del campo de hechos → campo_1735
    materia: str = MATERIA_CIVIL         # → campo_1748
    subtipo: str = SUBTIPO_EXTRAJUDICIAL # → campo_1749
    responsable: str = "Nikolai_Tyukhay" # Username en el CRM → campo_2487


# ---------------------------------------------------------------------------
# Notas estándar por tipo de caso (Manual Gestión Interna Despacho)
# ---------------------------------------------------------------------------
# Plantillas para el campo descripcion_html del expediente.
# El campo entre (...) = nombre del comprador/arrendatario; [XXX] = referencia MLS.

NOTA_BAD_DEBT = (
    "Impago de factura (Bad Debt)."
)
NOTA_NEGATIVA_OFERTA = (
    "Reclamamos los honorarios al cliente (especificar vendedor, comprador, "
    "arrendador, arrendatario) por negarse éste a aceptar la oferta en condiciones "
    "fijadas en el encargo."
)
NOTA_NEGATIVA_ARRAS = (
    "Reclamamos los honorarios al cliente (especificar vendedor, comprador, "
    "arrendador, arrendatario) por negarse éste a firmar el contrato privado (arras) "
    "tras aceptar la oferta."
)
NOTA_NEGATIVA_ESCRITURA = (
    "Reclamamos los honorarios al cliente (especificar vendedor, comprador, "
    "arrendador, arrendatario) por negarse éste a firmar la escritura tras firmar el "
    "contrato privado (arras)."
)
NOTA_VUELTA = (
    "Reclamamos los honorarios al cliente (especificar vendedor, comprador, "
    "arrendador, arrendatario) por aprovecharse éste de la gestión de la agencia."
)
NOTA_INCUMPLIMIENTO_EXCLUSIVA = (
    "Reclamamos los honorarios al cliente vendedor por incumplir éste el pacto de "
    "exclusividad."
)
NOTA_RESPONSABILIDAD_PROF = (
    "El cliente (especificar comprador, arrendatario) le reclama a la agencia los "
    "daños y perjuicios causados por la presunta falta de diligencia de la agencia."
)
NOTA_DEVOLUCION_RESERVA = (
    "El cliente (especificar comprador, arrendatario) le reclama a la agencia la "
    "devolución de la reserva entregada."
)
NOTA_LAU_20 = (
    "El arrendatario le reclama a la agencia la devolución de los honorarios "
    "amparándose en el art. 20.1 LAU."
)
NOTA_DEVOLUCION_HONORARIOS = (
    "El cliente (especificar comprador, arrendatario) le reclama a la agencia la "
    "devolución de los honorarios pagados."
)
NOTA_NEGATIVA_CONTRATO_ARR = (
    "El arrendatario, aceptada la oferta de arrendamiento, se ha negado a firmar el "
    "contrato de arrendamiento."
)
NOTA_FRANQUICIA = (
    "Un asunto relacionado con una empresa franquiciada de Engel & Völkers."
)
NOTA_CONSULTORES = (
    "Reclamaciones de los consultores frente a la agencia."
)

# Mapa tipo_caso → tag verde para uso en tag_defaults_for_tipo_caso().
# Los tipos de caso de config.py que tienen tag verde en el CRM están mapeados aquí.
# Notas:
#   - NEGATIVA_CONTRATO_ARRENDAMIENTO: su tag CRM es ROJO (#a32929___155), no verde.
#     Se incluye con su valor real para que tag_defaults_for_tipo_caso() lo trate bien.
#   - FRANQUICIA: no existe todavía como tag en el CRM (2026-04-28) → None.
_TIPO_A_TAG_VERDE: dict[str, str | None] = {
    "BAD_DEBT":                         TAG_VERDE_BAD_DEBT,
    "NEGATIVA_OFERTA":                  TAG_VERDE_NEGATIVA_OFERTA,
    "NEGATIVA_ARRAS":                   TAG_VERDE_NEGATIVA_ARRAS,
    "NEGATIVA_ESCRITURA":               TAG_VERDE_NEGATIVA_ESCRITURA,
    "NEGATIVA_CONTRATO_ARRENDAMIENTO":  TAG_VERDE_NEGATIVA_CONTRATO_ARR,
    "VUELTA":                           TAG_VERDE_VUELTA,
    "INCUMPLIMIENTO_EXCLUSIVA":         TAG_VERDE_INCUMPLIMIENTO_EXCLUSIVA,
    "RESPONSABILIDAD_PROFESIONAL":      TAG_VERDE_RESPONSABILIDAD_PROF,
    "DEVOLUCION_RESERVA":               TAG_VERDE_DEVOLUCION_RESERVA,
    "LAU_20":                           TAG_VERDE_LAU_20,
    "DEVOLUCION_HONORARIOS":            TAG_VERDE_DEVOLUCION_HONORARIOS,
    "CONSULTORES":                      TAG_VERDE_CONSULTORES,
    "FRANQUICIA":                       TAG_VERDE_FRANQUICIA,
}


def tag_defaults_for_tipo_caso(tipo_caso: str) -> list[str]:
    """Devuelve la lista de tags lila y verde para un tipo de caso.

    Sigue las reglas del Manual de Gestión Interna:
        - Actora:   [verde_asunto, TAG_LILA_POSIBILIDAD_50]
        - Defensiva:[verde_asunto, TAG_LILA_RIESGO_POSIBLE]

    El tag rojo de equipo y el azul de ciudad NO se incluyen aquí:
    deben ser añadidos por el caller según el equipo comercial y la plaza.
    El TAG_SENTINEL ("__void__") se añade automáticamente en build_form_data().

    Args:
        tipo_caso: Clave de config.TIPOS_CASO_ALL (ej. "BAD_DEBT", "LAU_20").

    Returns:
        Lista de tags (sin sentinel). Orden: [verde, lila].

    Raises:
        ValueError: si tipo_caso no se reconoce.

    Example::

        tags = tag_defaults_for_tipo_caso("BAD_DEBT")
        # → ["#528800___110", "#5229a3___286"]   (verde + lila probabilidad 50%)

        tags = tag_defaults_for_tipo_caso("LAU_20")
        # → ["#528800___214", "#5229a3___217"]   (verde + lila riesgo posible)

        tags = tag_defaults_for_tipo_caso("NEGATIVA_CONTRATO_ARRENDAMIENTO")
        # → ["#a32929___155", "#5b9bd1___286"]   (rojo especial + azul probabilidad 50%)
    """
    from . import config  # import local para evitar ciclo

    # Determinar posición (actora/defensiva)
    posicion_cfg = config.posicion_de_tipo(tipo_caso)  # lanza ValueError si desconocido

    # Tag de asunto (verde para la mayoría; rojo para NEGATIVA_CONTRATO_ARRENDAMIENTO)
    asunto_tag = _TIPO_A_TAG_VERDE.get(tipo_caso)
    if tipo_caso not in _TIPO_A_TAG_VERDE and tipo_caso in config.TIPOS_CASO_ALL:
        asunto_tag = None  # tipo conocido pero sin tag CRM aún

    # Tag de valoración según posición:
    #   Actora → azul POSIBILIDAD EXITO=50% (tag #5b9bd1___286, capturado 2026-04-28)
    #   Defensiva → lila RIESGO_POSIBLE (DEFAULT según Manual escrito)
    #
    # Nota: en sesión anterior se indicó verbalmente que el default defensiva sería
    # RIESGO_REMOTO; el Manual escrito establece RIESGO_POSIBLE. Se sigue el Manual.
    # Confirmar con el despacho si la instrucción verbal prevalece.
    if posicion_cfg == config.POSICION_ACTORA:
        valoracion_tag = TAG_LILA_POSIBILIDAD_50
    else:
        valoracion_tag = TAG_LILA_RIESGO_POSIBLE

    tags: list[str] = []
    if asunto_tag is not None:
        tags.append(asunto_tag)
    tags.append(valoracion_tag)
    return tags


# ---------------------------------------------------------------------------
# Builder de form-data
# ---------------------------------------------------------------------------

def build_form_data(
    datos: NuevoExpedienteExtrajudicial,
    csrf_token: str,
) -> list[tuple[str, str]]:
    """Construye el body form-urlencoded de la request de creación.

    Devuelve lista de tuplas (nombre, valor) para preservar el orden y
    permitir claves repetidas (tags, csrf_token múltiple).

    Args:
        datos: Datos del expediente.
        csrf_token: Token CSRF extraído de la sesión PHP actual.

    Returns:
        Lista de tuplas (campo, valor) lista para pasar a httpx/requests.
    """
    fecha_str = datos.fecha_apertura.strftime("%d-%m-%Y")
    año_str = str(datos.fecha_apertura.year)
    momento = hex(int(time.time()))[2:]  # hex timestamp sin "0x"

    # Tags: lista + sentinel
    tags = list(datos.tags)
    if not tags:
        tags = []
    # El formulario siempre termina con __void__
    tags_con_sentinel = tags + [TAG_SENTINEL]

    form: list[tuple[str, str]] = [
        # Campos del expediente
        ("campo_1737__extrajudiciales",  _CAMPO_FIJO_1737),
        ("campo_1731__extrajudiciales",  fecha_str),
        ("campo_2587__extrajudiciales",  _CAMPO_FIJO_2587),
        ("campo_1733__extrajudiciales",  "0"),
        ("campo_1732__extrajudiciales",  ""),
        ("campo_1741__extrajudiciales",  ""),   # campo pendiente identificar
        ("campo_1747__extrajudiciales",  año_str),
        ("valor_select",                 "1"),
        ("etiqueta_select",              ""),
        ("campo_1748__extrajudiciales",  datos.materia),
        ("valor_select",                 "1"),
        ("etiqueta_select",              ""),
        ("campo_1740__extrajudiciales",  datos.referencia_cliente),
        ("campo_1749__extrajudiciales",  datos.subtipo),
        ("valor_select",                 "1"),
        ("etiqueta_select",              ""),
        ("campo_1742__extrajudiciales",  ""),
        ("campo_2487__extrajudiciales",  datos.responsable),
        ("campo_2586__extrajudiciales",  datos.posicion),
    ]

    # Tags (clave repetida)
    for tag in tags_con_sentinel:
        form.append(("campo_2488__extrajudiciales[]", tag))

    total = datos.cuantia + datos.costas + datos.intereses

    form += [
        # Importes (campo_1730/1729/1734 → enteros; campo_1750 → Total formateado)
        ("campo_1730__extrajudiciales",  _fmt_importe_entero(datos.cuantia)),
        ("campo_1729__extrajudiciales",  _fmt_importe_entero(datos.costas)),
        ("campo_1734__extrajudiciales",  _fmt_importe_entero(datos.intereses)),
        ("campo_1750__extrajudiciales",  _fmt_importe_display(total)),
        # Descripción
        ("campo_1735__extrajudiciales",  datos.descripcion_html),
        # Permisos — listas dinámicas de IDs
    ]
    for gid in datos.grupos:
        form.append(("permisos_grupos[]", str(gid)))
    for uid in datos.usuarios:
        form.append(("permisos_usuarios[]", str(uid)))
    form += [
        # Técnicos del formulario
        ("csrf_token",                   csrf_token),
        ("cc-num",                       "HubspotCollectedFormsWorkaround"),
        ("momento_log",                  momento),
        ("",                             ""),  # campos vacíos finales observados en captura
        ("",                             ""),
        ("ajax",                         "true"),
        ("csrf_token",                   csrf_token),   # se envía 3 veces
        ("validar_formatos_nacionales",  "false"),
        ("csrf_token",                   csrf_token),
    ]

    return form


# ---------------------------------------------------------------------------
# Extracción del ID de la respuesta
# ---------------------------------------------------------------------------

def extract_id_from_response(response: Any) -> str | None:
    """Extrae el ID del expediente creado de la respuesta del servidor.

    Shape confirmado el 2026-04-28 contra el tenant tnm (saveedit/saveadd):

        {
            "resultado": true,
            "dato": "600",           ← ID del expediente
            "wfcontroller": "extrajudiciales",
            "updated": true,
            ...
        }

    Args:
        response: dict parseado del JSON de respuesta.

    Returns:
        ID numérico como string, o None si no se puede extraer.
    """
    if not isinstance(response, dict):
        return None

    # Campo principal confirmado: "dato"
    dato = response.get("dato")
    if dato is not None and str(dato).isdigit():
        return str(dato)

    # Fallbacks por si el saveadd usa una clave diferente al saveedit
    for key in ("id", "miembro", "expediente_id"):
        val = response.get(key)
        if val is not None and str(val).isdigit():
            return str(val)

    return None


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

class SudespachoCreateError(RuntimeError):
    pass


def create_expediente(
    datos: NuevoExpedienteExtrajudicial,
    *,
    legacy_client: SudespachoLegacyClient | None = None,
    legacy_host: str | None = None,
) -> str:
    """Crea un expediente extrajudicial en sudespacho.net.

    Usa el frontal heredado (mismo mecanismo que sync_sudespacho_legacy).
    El CSRF token se extrae automáticamente de la sesión PHP activa.

    Args:
        datos: Datos del nuevo expediente.
        legacy_client: Cliente legacy reutilizable (opcional).
        legacy_host: Host del tenant (opcional; por defecto lee SUDESPACHO_LEGACY_HOST del .env).

    Returns:
        ID numérico del expediente creado (str).

    Raises:
        SudespachoCreateError: si la creación falla o la respuesta no contiene el ID.
        SudespachoLegacyError: si la sesión PHP ha expirado.

    Example::

        from core.sudespacho_create import create_expediente, NuevoExpedienteExtrajudicial

        from core.sudespacho_create import (
            create_expediente, NuevoExpedienteExtrajudicial,
            tag_defaults_for_tipo_caso, TAG_ROJO_BaRR1, TAG_SENTINEL,
        )

        tags = [TAG_ROJO_BaRR1] + tag_defaults_for_tipo_caso("NEGATIVA_ARRAS")
        eid = create_expediente(NuevoExpedienteExtrajudicial(
            referencia_cliente="MaRS2 - Calle Major 10, 3º 1ª (W-031ABC) - Negativa arras",
            cuantia=12500.00,
            tags=tags,
        ))
        # eid → "653"
    """
    owns_client = legacy_client is None
    try:
        client = legacy_client or SudespachoLegacyClient()
    except SudespachoLegacyError as exc:
        raise SudespachoCreateError(
            f"No se pudo inicializar el cliente legacy: {exc}. "
            "Revisa SUDESPACHO_LEGACY_PHPSESSID en .env."
        ) from exc

    try:
        # 1. Obtener CSRF token activo de la sesión
        try:
            csrf_token = client.get_csrf_token()
        except SudespachoLegacyError as exc:
            raise SudespachoCreateError(
                f"No se pudo obtener el CSRF token: {exc}"
            ) from exc

        # 2. Construir el body
        form_data = build_form_data(datos, csrf_token)

        # 3. Enviar el POST
        url = f"https://{legacy_host or client.host}{_ENDPOINT_CREATE}"
        try:
            response = client.post_form(url, form_data)
        except SudespachoLegacyError as exc:
            raise SudespachoCreateError(
                f"POST {_ENDPOINT_CREATE} falló: {exc}"
            ) from exc

        # 4. Extraer el ID del expediente creado
        expediente_id = extract_id_from_response(response)
        if not expediente_id:
            raise SudespachoCreateError(
                f"Expediente creado pero no se pudo extraer su ID. "
                f"Respuesta: {str(response)[:400]}. "
                "Revisa extract_id_from_response() con el shape real de la respuesta."
            )

        return expediente_id

    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass
