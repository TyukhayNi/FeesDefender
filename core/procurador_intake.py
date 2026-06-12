"""F1 — Matcher de correos de procuradores → expediente Sudespacho (solo lectura).

Dado un correo (asunto + cuerpo + adjuntos), extrae señales, resuelve el
expediente en el CRM, y propone carpeta + nombres de adjuntos con nivel de
confianza. NO escribe nada en el CRM.

Módulos reutilizados:
    core.llm_cloud      — conector LLM intercambiable (Scaleway/Mistral)
    core.sync_sudespacho — conexión API REST a Sudespacho (x-api-key)

RGPD: excepción acotada SOLO a este flujo (LLM cloud con PII de correos
procesales). Ver docs/PLAN_INTAKE_PROCURADORES_EMAIL.md §preamble.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from .llm_cloud import LLMCloudConfig, LLMCloudError, chat_json
from .sync_sudespacho import SudespachoClient, SudespachoConfig, SudespachoError

logger = logging.getLogger("feesdefender.procurador_intake")


# ---------------------------------------------------------------------------
# Dominios / emails de procuradores conocidos (ampliable)
# ---------------------------------------------------------------------------

PROCURADOR_DOMAINS: set[str] = {
    "procuradores-a.example",
    "procuradores-b.example",
    "procuradores-c.example",
    "procuradores-d.example",
    "procuradores-e.example",
}

PROCURADOR_EMAILS: set[str] = {
    "proc-a@example.invalid",
    "proc-f@colegio-proc.example",
}


def is_procurador_email(from_addr: str) -> bool:
    """Comprueba si el remitente es un procurador conocido."""
    addr = from_addr.strip().lower()
    # Extraer email de "Nombre <email@dom>"
    m = re.search(r"<([^>]+)>", addr)
    if m:
        addr = m.group(1).strip()
    if addr in PROCURADOR_EMAILS:
        return True
    domain = addr.rsplit("@", 1)[-1] if "@" in addr else ""
    return domain in PROCURADOR_DOMAINS


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass
class IntakeSignals:
    """Señales extraídas de un correo por el LLM."""
    su_ref: str | None = None          # "13/2026" → num_expediente/serie
    num_expediente: int | None = None  # extraído de su_ref
    serie_expediente: str | None = None  # año, con sufijo de subserie si lo hay ("2023-n")
    contrario: str | None = None
    cliente: str | None = None
    juzgado: str | None = None
    num_asunto: str | None = None      # nº autos
    tipo_procedimiento: str | None = None
    tipo_actuacion: str | None = None  # Auto, Sentencia, DiOr, etc.
    fecha_actuacion: str | None = None # ISO date
    es_ruido: bool = False
    raw_llm: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttachmentProposal:
    """Propuesta de nombre para un adjunto."""
    original_filename: str
    proposed_name: str
    tipo: str              # abreviatura (Auto, Sent, DiOr, etc.)
    fecha: str | None      # ISO date
    descripcion: str
    confianza: float       # 0.0–1.0
    es_probatorio: bool = False
    num_doc: int | None = None
    subir: bool = True     # desmarcado para logotipos


@dataclass
class MatchResult:
    """Resultado del emparejamiento correo → expediente."""
    expediente_id: int | None = None
    confianza: str = "ninguna"  # "alta", "dudosa", "ninguna"
    datos_expediente: dict[str, Any] = field(default_factory=dict)
    senales_usadas: list[str] = field(default_factory=list)
    candidatos: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class IntakeProposal:
    """Propuesta completa para un correo."""
    signals: IntakeSignals
    match: MatchResult
    attachments: list[AttachmentProposal] = field(default_factory=list)
    carpeta_sugerida: str | None = None
    carpeta_id: int | None = None


# ---------------------------------------------------------------------------
# Normalización de texto (§9 del plan)
# ---------------------------------------------------------------------------

_STOPWORDS_ES = frozenset(
    "a al ante bajo con contra de del desde durante e el ella ellos"
    " en entre es esta este esto fue ha hacia hasta la las le les"
    " lo los me mi ni no nos o para pero por que se si sin sobre"
    " su sus te tu tus u un una uno unas unos y ya".split()
)

_ACCENT_MAP = str.maketrans(
    "áéíóúàèìòùäëïöü",
    "aeiouaeiouaeiou",
)


def normalize_descripcion(text: str, max_chars: int = 40) -> str:
    """Normaliza descripción para nombre de fichero (§9 del plan).

    1. Quitar stopwords.
    2. Quitar tildes de vocales, conservar ñ.
    3. Conservar nombres propios, números, referencias.
    4. Acotar a ~max_chars.
    """
    text = text.strip().lower()
    text = text.translate(_ACCENT_MAP)
    words = text.split()
    words = [w for w in words if w not in _STOPWORDS_ES]
    result = " ".join(words)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit(" ", 1)[0]
    return result.strip()


_FORBIDDEN_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_filename(name: str) -> str:
    """Elimina caracteres prohibidos en Windows."""
    return _FORBIDDEN_CHARS.sub("_", name).strip()


# ---------------------------------------------------------------------------
# Vocabulario de tipos procesales (§9)
# ---------------------------------------------------------------------------

TIPO_ABREV: dict[str, str] = {
    "auto": "Auto",
    "sentencia": "Sent",
    "decreto": "Decr",
    "diligencia de ordenación": "DiOr",
    "diligencia de ordenacion": "DiOr",
    "providencia": "Prov",
    "cédula": "Ced",
    "cedula": "Ced",
    "oficio": "Ofi",
    "mandamiento": "Mand",
    "escrito": "Escr",
    "escrito contraria": "Escr-Crio",
    "escrito parte contraria": "Escr-Crio",
    "justificante de presentación": "Just Escr",
    "justificante de presentacion": "Just Escr",
    "justificante presentacion": "Just Escr",
    "recurso": "Rec",
    "acta": "Acta",
    "tasación de costas": "Tasac",
    "tasacion de costas": "Tasac",
    "tasacion costas": "Tasac",
    "testimonio": "Test",
    "notificación": "Notif",
    "notificacion": "Notif",
    "grabación": "Grab",
    "grabacion": "Grab",
    "otros": "Otros",
}


def abreviar_tipo(tipo_raw: str) -> str:
    """Convierte un tipo procesal a su abreviatura estándar."""
    key = tipo_raw.strip().lower()
    return TIPO_ABREV.get(key, tipo_raw.strip())


# ---------------------------------------------------------------------------
# Extracción de señales (LLM)
# ---------------------------------------------------------------------------

_SYSTEM_EXTRACT = """\
Eres un asistente jurídico. Dado un correo electrónico de un procurador español,
extrae las siguientes señales en JSON. Si un campo no aparece, devuelve null.
NO inventes datos que no estén en el correo.

Campos:
- su_ref: la referencia del despacho destinatario (rotulada "Su ref", "S/R",
  "Su Rfa", "Referencia"). Formato típico: "13/2026", "19/25". NO confundir
  con "Mi ref" o "M/R" (que es la del procurador).
- contrario: nombre de la parte contraria mencionada.
- cliente: nombre del cliente del despacho mencionado.
- juzgado: nombre o número del juzgado.
- num_asunto: número de autos / procedimiento (ej. "123/2025").
- tipo_procedimiento: tipo de procedimiento (ordinario, verbal, monitorio, etc.).
- tipo_actuacion: tipo de resolución o documento (auto, sentencia, decreto,
  diligencia de ordenación, providencia, cédula, oficio, mandamiento, escrito,
  recurso, acta, tasación de costas, testimonio, notificación, grabación, otros).
- fecha_actuacion: fecha de la actuación/resolución en formato ISO (YYYY-MM-DD).
- es_ruido: true SOLO si el correo no tiene contenido procesal en absoluto
  (publicidad, newsletters, alertas automáticas de Google/sistemas, cortesía sin
  trámite). Cualquier comunicación que reporte un trámite, resolución o documento
  (auto, sentencia, decreto, diligencia, providencia, traslado, acuse, escrito,
  justificante, notificación, requerimiento) NO es ruido, AUNQUE el trámite sea
  negativo o meramente informativo (p. ej. "traslado del acuse negativo", "se
  remite al nuevo domicilio", "resguardo de presentación").

Responde SOLO con JSON, sin texto adicional."""


def _parse_su_ref(su_ref: str | None) -> tuple[int | None, str | None]:
    """Extrae num_expediente y serie_expediente de una Su ref como '13/2026'.

    La serie puede llevar sufijo de subserie ('-N', '-P', '-E'). El CRM lo
    almacena DENTRO de serie_expediente, en minúscula (p. ej. '2023-n'), así que
    se conserva: si se descartara, el match por num+serie devolvería 0 (la
    búsqueda exacta no encontraría '2023' cuando el valor real es '2023-n').
    Devuelve la serie como string en el formato del CRM.
    """
    if not su_ref:
        return None, None
    m = re.match(r"(\d+)\s*/\s*(\d{2,4})\s*(-\s*[A-Za-z])?", su_ref.strip())
    if not m:
        return None, None
    num = int(m.group(1))
    year = int(m.group(2))
    if year < 100:
        year += 2000
    serie = str(year)
    if m.group(3):
        serie += m.group(3).replace(" ", "").lower()
    return num, serie


def extract_signals(
    subject: str,
    body: str,
    *,
    attachment_texts: list[str] | None = None,
    llm_config: LLMCloudConfig | None = None,
) -> IntakeSignals:
    """Extrae señales de un correo usando el LLM cloud."""
    content_parts = [f"Asunto: {subject}", f"Cuerpo:\n{body}"]
    if attachment_texts:
        for i, text in enumerate(attachment_texts, 1):
            excerpt = text[:3000]
            content_parts.append(f"Adjunto {i} (extracto):\n{excerpt}")

    messages = [
        {"role": "system", "content": _SYSTEM_EXTRACT},
        {"role": "user", "content": "\n\n".join(content_parts)},
    ]

    raw = chat_json(messages, config=llm_config, temperature=0.0)

    su_ref = raw.get("su_ref")
    num, serie = _parse_su_ref(su_ref)

    return IntakeSignals(
        su_ref=su_ref,
        num_expediente=num,
        serie_expediente=serie,
        contrario=raw.get("contrario"),
        cliente=raw.get("cliente"),
        juzgado=raw.get("juzgado"),
        num_asunto=raw.get("num_asunto"),
        tipo_procedimiento=raw.get("tipo_procedimiento"),
        tipo_actuacion=raw.get("tipo_actuacion"),
        fecha_actuacion=raw.get("fecha_actuacion"),
        es_ruido=bool(raw.get("es_ruido", False)),
        raw_llm=raw,
    )


# ---------------------------------------------------------------------------
# Búsqueda de expediente por num + serie (API REST)
# ---------------------------------------------------------------------------

_MATCH_PROPERTIES = (
    "num_expediente",
    "serie_expediente",
    "juzgado",
    "num_asunto",
    "tipo_procedimiento",
    "referencia_procurador",
)


def _search_by_num_serie(
    num: int,
    serie: int,
    *,
    client: SudespachoClient,
    element: str = "expedientes_judiciales",
) -> list[dict[str, Any]]:
    """Busca expedientes por num_expediente + serie_expediente vía element_registries."""
    path = f"/api/element_registries/{element}"
    params: list[tuple[str, str]] = [
        ("properties[0]", "num_expediente"),
        ("properties[1]", "serie_expediente"),
        ("properties[2]", "juzgado"),
        ("properties[3]", "num_asunto"),
        ("properties[4]", "tipo_procedimiento"),
        ("properties[5]", "referencia_procurador"),
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]", str(num)),
        ("filterGroup[filterGroups][0][filters][0][property]", "num_expediente"),
        ("filterGroup[filterGroups][0][filters][1][operator]", "equal"),
        ("filterGroup[filterGroups][0][filters][1][value]", str(serie)),
        ("filterGroup[filterGroups][0][filters][1][property]", "serie_expediente"),
        ("itemsPerPage", "10"),
        ("return_totals", "true"),
    ]

    r = client._client.get(path, params=params)
    if r.status_code != 200:
        logger.warning("Búsqueda num/serie %d/%d → HTTP %d", num, serie, r.status_code)
        return []

    data = r.json()
    items = data.get("hydra:member", data.get("items", []))

    results = []
    for item in items:
        exp_id = item.get("id")
        vals: dict[str, Any] = {"id": exp_id}
        for val_obj in item.get("values", []):
            prop_name = (val_obj.get("property") or {}).get("name", "")
            if prop_name in _MATCH_PROPERTIES:
                vals[prop_name] = val_obj.get("value")
        results.append(vals)
    return results


def _check_signal_matches(
    signals: IntakeSignals,
    exp_data: dict[str, Any],
) -> list[str]:
    """Compara señales del correo con datos del expediente. Devuelve lista de coincidencias."""
    matches = []
    if signals.num_expediente and str(signals.num_expediente) == str(exp_data.get("num_expediente", "")):
        matches.append("num_expediente")
    if signals.serie_expediente and str(signals.serie_expediente).lower() == str(exp_data.get("serie_expediente", "")).lower():
        matches.append("serie_expediente")
    if signals.juzgado and exp_data.get("juzgado"):
        if _juzgado_match(signals.juzgado, str(exp_data["juzgado"])):
            matches.append("juzgado")
    if signals.num_asunto and exp_data.get("num_asunto"):
        if _norm_ref(signals.num_asunto) == _norm_ref(str(exp_data["num_asunto"])):
            matches.append("num_asunto")
    if signals.tipo_procedimiento and exp_data.get("tipo_procedimiento"):
        if _norm(signals.tipo_procedimiento) in _norm(str(exp_data["tipo_procedimiento"])):
            matches.append("tipo_procedimiento")
    return matches


def _norm(s: str) -> str:
    """Normaliza para comparación: minúscula, sin acentos, sin espacios extra."""
    s = s.strip().lower()
    nfkd = unicodedata.normalize("NFKD", s)
    return re.sub(r"\s+", " ", "".join(c for c in nfkd if unicodedata.category(c) != "Mn"))


_JUZGADO_STOPWORDS = frozenset({"de", "del", "la", "el", "los", "las", "nº", "no", "num"})


def _juzgado_match(a: str, b: str) -> bool:
    """Compara juzgados por tokens significativos (ignora stopwords, acentos, case)."""
    def tokens(s: str) -> set[str]:
        normed = _norm(s)
        return {t for t in normed.split() if t not in _JUZGADO_STOPWORDS and len(t) > 1}
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    overlap = ta & tb
    return len(overlap) >= min(len(ta), len(tb)) * 0.7


def _norm_ref(s: str) -> str:
    """Normaliza referencia numérica: quitar espacios alrededor de /."""
    return re.sub(r"\s*/\s*", "/", s.strip())


def match_expediente(
    signals: IntakeSignals,
    *,
    sudo_client: SudespachoClient | None = None,
) -> MatchResult:
    """Busca el expediente que corresponde a las señales extraídas.

    Estrategia:
    1. Si hay su_ref → buscar por num+serie. Match único = alta.
    2. Si no hay su_ref → 'ninguna' (es_ruido si el LLM lo marcó, si no sin_su_ref).

    `es_ruido` es ADVISORY, no un bloqueo: si hay una su_ref que resuelve a un
    expediente, el correo pertenece a él (basta relacionarlo) y la red de
    seguridad lo confirma a mano. Solo suprime cuando NO hay su_ref utilizable
    (recordatorios sin documento, publicidad). Así un falso positivo de ruido no
    descarta silenciosamente un correo con su_ref válida.
    """
    owns_client = sudo_client is None
    if owns_client:
        sudo_client = SudespachoClient()

    try:
        if signals.num_expediente and signals.serie_expediente:
            results = _search_by_num_serie(
                signals.num_expediente,
                signals.serie_expediente,
                client=sudo_client,
            )
            if len(results) == 1:
                exp = results[0]
                matches = _check_signal_matches(signals, exp)
                senales = ["su_ref"] + matches
                if signals.es_ruido:
                    senales.append("es_ruido_advisory")
                return MatchResult(
                    expediente_id=exp["id"],
                    confianza="alta",
                    datos_expediente=exp,
                    senales_usadas=senales,
                )
            elif len(results) > 1:
                return MatchResult(
                    confianza="dudosa",
                    senales_usadas=["su_ref_multiple"],
                    candidatos=results,
                )
            else:
                return MatchResult(
                    confianza="ninguna",
                    senales_usadas=["su_ref_sin_match"],
                )

        # Sin su_ref utilizable
        if signals.es_ruido:
            return MatchResult(confianza="ninguna", senales_usadas=["es_ruido"])
        return MatchResult(confianza="ninguna", senales_usadas=["sin_su_ref"])
    finally:
        if owns_client:
            sudo_client.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Propuesta de nombres de adjuntos (LLM)
# ---------------------------------------------------------------------------

_SYSTEM_RENAME = """\
Eres un asistente jurídico. Dado el CONTENIDO de un adjunto de un correo
de un procurador, propón un nombre descriptivo para el archivo.

Devuelve JSON con:
- fecha: fecha de la actuación/documento en formato YYYY-MM-DD. Si no aparece, null.
- tipo: tipo de actuación (auto, sentencia, decreto, diligencia de ordenación,
  providencia, cédula, oficio, mandamiento, escrito, escrito contraria,
  justificante de presentación, recurso, acta, tasación de costas, testimonio,
  notificación, grabación, otros).
- descripcion: descripción breve del contenido (~5 palabras, sin artículos ni
  preposiciones, en minúscula).
- confianza: 0.0 a 1.0 (qué tan seguro estás de la clasificación).
- es_probatorio: true si es un documento de prueba numerado (D01, D02...).
- num_doc: número del documento de prueba si es_probatorio, null si no.

Responde SOLO con JSON."""


def propose_attachment_name(
    attachment_text: str,
    email_body: str,
    original_filename: str,
    *,
    fecha_recepcion: str | None = None,
    llm_config: LLMCloudConfig | None = None,
) -> AttachmentProposal:
    """Propone un nombre para un adjunto basándose en su contenido."""
    user_content = (
        f"Contenido del adjunto:\n{attachment_text[:4000]}\n\n"
        f"Contexto (cuerpo del correo):\n{email_body[:1000]}\n\n"
        f"Nombre original del fichero: {original_filename}"
    )
    messages = [
        {"role": "system", "content": _SYSTEM_RENAME},
        {"role": "user", "content": user_content},
    ]

    raw = chat_json(messages, config=llm_config, temperature=0.0)

    tipo_raw = raw.get("tipo", "otros")
    tipo = abreviar_tipo(tipo_raw)
    fecha = raw.get("fecha") or fecha_recepcion
    desc = normalize_descripcion(raw.get("descripcion", original_filename))
    confianza = float(raw.get("confianza", 0.5))
    es_probatorio = bool(raw.get("es_probatorio", False))
    num_doc = raw.get("num_doc")

    ext = _extract_extension(original_filename)

    if es_probatorio and num_doc is not None:
        name = f"D {int(num_doc):02d} - {fecha or 'sin-fecha'} - {desc}{ext}"
    else:
        name = f"{fecha or 'sin-fecha'} - {tipo} - {desc}{ext}"

    name = sanitize_filename(name)

    is_logo = _looks_like_logo(original_filename)

    return AttachmentProposal(
        original_filename=original_filename,
        proposed_name=name,
        tipo=tipo,
        fecha=fecha,
        descripcion=desc,
        confianza=confianza,
        es_probatorio=es_probatorio,
        num_doc=int(num_doc) if num_doc is not None else None,
        subir=not is_logo,
    )


def _extract_extension(filename: str) -> str:
    """Extrae la extensión del nombre original."""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if re.match(r"^\.[a-z0-9]{1,8}$", ext):
            return ext
    return ".pdf"


_LOGO_PATTERNS = re.compile(
    r"(logo|firma|signature|banner|cabecera|header|image\d{3})",
    re.IGNORECASE,
)


def _looks_like_logo(filename: str) -> bool:
    """Heurística: ¿el adjunto parece un logotipo/firma del procurador?"""
    name = filename.lower()
    if _LOGO_PATTERNS.search(name):
        return True
    if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")) and len(name) < 20:
        return True
    return False
