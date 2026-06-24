"""Motor de exportación de una etiqueta Gmail → expediente como ``.eml`` fieles.

Tres capas, alineadas con la arquitectura UI → Core → Datos (la lógica vive aquí;
la UI/CLI solo orquestan):

- **Pura (testeable, sin red):**
  - ``eml_filename(headers)`` → ``"AAAA-MM-DD_descripcion.eml"`` con la nomenclatura
    del despacho (fecha ISO de la cabecera ``Date`` + asunto saneado).
  - ``split_eml(raw)`` → ``(eml_bytes, [(filename, mime, bytes)])``: el ``.eml`` fiel
    (los bytes RFC822 tal cual) + sus adjuntos decodificados.
  - ``parse_headers(raw)`` → dict de cabeceras en minúscula.
  - dedup por ``Message-ID`` (``existing_message_ids``).

- **Glue (red):** ``export_label(account, label, dest_dir, *, service=None)`` resuelve
  el ``labelId`` con ``labels().list`` (NO ``q="label:…"``), pagina
  ``messages().list(labelIds=[id])``, baja cada mensaje con ``messages().get(
  format='raw')`` → ``.eml`` byte-fiel, extrae adjuntos a subcarpeta fechada,
  es idempotente (salta los ``Message-ID`` ya presentes) y devuelve un informe.

- **Índices:** ``write_indices(dest_dir)`` regenera ``INDICE.md`` y ``CRONOLOGIA.md``
  desde todos los ``.eml`` presentes (idempotente).

Reutiliza el OAuth de :mod:`core.gmail_source` (tokens ``~/.gmail-mcp/tokens/``, sin
alta nueva). **Solo lectura:** no marca mensajes como leídos ni escribe en Gmail.
"""

from __future__ import annotations

import base64
import email
import json
import quopri
import re
import unicodedata
from dataclasses import dataclass, field
from email import policy
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from . import intake_log
from .gmail_source import _build_service, _load_credentials
from .intake_manifest import IntakeManifest, compute_sha256_bytes
from .intake_utils import decode_base64url, sanitize_filename

# ---------------------------------------------------------------------------
# Capa pura — base64url, cabeceras, nombre canónico, partición del .eml
# ---------------------------------------------------------------------------

_RE_PREFIJO_ASUNTO = re.compile(r"^\s*(re|rv|fwd?|fw|aw|wg)\s*:\s*", re.IGNORECASE)
_RE_NO_SLUG = re.compile(r"[^a-zA-Z0-9]+")

_SIN_FECHA = "0000-00-00"
_MAXLEN_DESCRIPCION = 60


def decode_b64url_bytes(data: str) -> bytes:
    """Decodifica base64url de Gmail a bytes, con padding tolerante.

    .. deprecated:: Usar :func:`core.intake_utils.decode_base64url` con ``as_bytes=True``.
    """
    return decode_base64url(data, as_bytes=True)


def _parse_message(raw: bytes) -> Message:
    return email.message_from_bytes(raw, policy=policy.default)


def parse_headers(raw: bytes) -> dict[str, str]:
    """Cabeceras del mensaje RFC822 como dict en minúscula (desplegadas)."""
    msg = _parse_message(raw)
    out: dict[str, str] = {}
    for name in ("date", "subject", "from", "to", "message-id"):
        val = msg.get(name)
        if val is not None:
            out[name] = str(val).strip()
    return out


def message_id_of(raw: bytes) -> str:
    """Message-ID normalizado (sin ``<>`` ni espacios), o ``""`` si no hay."""
    return (parse_headers(raw).get("message-id") or "").strip().strip("<>").strip()


def _slug_descripcion(asunto: str) -> str:
    """Asunto → descripción en guiones bajos, sin acentos, sin prefijos Re/Fwd."""
    texto = asunto or ""
    # Quitar prefijos de respuesta/reenvío encadenados (Re: RV: Fwd: …).
    prev = None
    while prev != texto:
        prev = texto
        texto = _RE_PREFIJO_ASUNTO.sub("", texto, count=1)
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = _RE_NO_SLUG.sub("_", texto).strip("_").lower()
    if len(texto) > _MAXLEN_DESCRIPCION:
        texto = texto[:_MAXLEN_DESCRIPCION].rstrip("_")
    return texto or "sin_asunto"


def _fecha_iso(header_date: str | None) -> str:
    """Cabecera ``Date`` → ``AAAA-MM-DD``; ``0000-00-00`` si falta o no parsea."""
    if not header_date:
        return _SIN_FECHA
    try:
        dt = parsedate_to_datetime(header_date)
    except (TypeError, ValueError, IndexError):
        return _SIN_FECHA
    if dt is None:
        return _SIN_FECHA
    return dt.strftime("%Y-%m-%d")


def eml_filename(headers: dict[str, str]) -> str:
    """Construye ``AAAA-MM-DD_descripcion.eml`` desde las cabeceras del mensaje.

    ``headers`` es un mapping con claves en minúscula (p. ej. el de
    :func:`parse_headers`). Usa ``date`` para la fecha y ``subject`` para la
    descripción.
    """
    lower = {str(k).lower(): v for k, v in headers.items()}
    fecha = _fecha_iso(lower.get("date"))
    descripcion = _slug_descripcion(lower.get("subject", ""))
    return f"{fecha}_{descripcion}.eml"


def _sanea_nombre_fichero(nombre: str, *, fallback: str) -> str:
    """Nombre de fichero seguro en Windows (sin caracteres prohibidos ni control)."""
    return sanitize_filename(nombre or "", mode="file", fallback=fallback)


def _payload_message(parte: Message) -> Message | None:
    """El ``Message`` anidado de una parte ``message/rfc822``, o ``None``."""
    payload = parte.get_payload()
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    return payload if isinstance(payload, Message) else None


def _iter_partes_hoja(msg: Message) -> Iterator[Message]:
    """Itera partes hoja tratando ``message/rfc822`` como hoja (NO desciende en ella).

    Lo usa :func:`split_eml` para extraer adjuntos binarios sin explotar los PDF
    que viajan DENTRO de un email anidado (esos se quedan embebidos en su ``.eml``).
    """
    if msg.get_content_type() == "message/rfc822":
        yield msg
        return
    if msg.get_content_maintype() == "multipart":
        for sub in msg.iter_parts():
            yield from _iter_partes_hoja(sub)
        return
    yield msg


def split_eml(raw: bytes) -> tuple[bytes, list[tuple[str, str, bytes]]]:
    """Parte el mensaje crudo en ``(eml_fiel, [(filename, mime, bytes)])``.

    El primer elemento son los bytes RFC822 **tal cual** (el ``.eml`` fiel). El
    segundo, los adjuntos decodificados (partes con disposición ``attachment`` o
    con nombre de fichero). Las partes ``message/rfc822`` (emails anidados) NO se
    devuelven como adjuntos: las gestiona el aplanado (:func:`_aplana_anidados`).

    .. note:: Cambio frente a la versión basada en ``msg.walk()``: ``message/rfc822``
       se trata como hoja, así que los adjuntos que viajan DENTRO de un email anidado
       ya no se extraen sueltos por aquí (se obtienen aplanando el ``.eml`` hijo, que
       los lleva embebidos). Ver ``docs/MEJORAS_FUTURAS.md`` §44.5.
    """
    msg = _parse_message(raw)
    adjuntos: list[tuple[str, str, bytes]] = []
    for parte in _iter_partes_hoja(msg):
        if parte.get_content_type() == "message/rfc822":
            continue  # los emails anidados los gestiona el aplanado, no split_eml
        filename = parte.get_filename()
        disposicion = parte.get_content_disposition()
        if disposicion != "attachment" and not filename:
            continue
        payload = parte.get_payload(decode=True)
        if payload is None:
            continue
        nombre = _sanea_nombre_fichero(filename or "", fallback="adjunto")
        adjuntos.append((nombre, parte.get_content_type(), payload))
    return raw, adjuntos


# ---------------------------------------------------------------------------
# Capa pura — aplanado byte-fiel de emails anidados (message/rfc822)
# ---------------------------------------------------------------------------

def _split_headers_body(block: bytes) -> tuple[bytes, bytes]:
    """Parte un bloque MIME en (cabeceras, cuerpo) por el separador en blanco.

    Elige el separador por la POSICIÓN más temprana, no por el orden de la lista: un
    bloque con line-endings mezclados (un padre con ``\\n\\n`` que transporta un hijo
    con ``\\r\\n\\r\\n``) debe partir por el separador REAL (el primero del bloque), no
    por el primer patrón que se pruebe. En empate (imposible entre estos dos) prima
    ``\\r\\n\\r\\n``.
    """
    candidatos = [
        (i, sep)
        for i, sep in ((block.find(b"\r\n\r\n"), b"\r\n\r\n"), (block.find(b"\n\n"), b"\n\n"))
        if i != -1
    ]
    if not candidatos:
        return block, b""
    i, sep = min(candidatos, key=lambda t: (t[0], 0 if t[1] == b"\r\n\r\n" else 1))
    return block[:i], block[i + len(sep):]


def _split_mime_parts(body: bytes, boundary: bytes) -> list[bytes]:
    """Trozos del cuerpo entre delimitadores ``--boundary`` ANCLADOS a inicio de línea.

    RFC 2046: el delimitador es una línea completa (al inicio del cuerpo o precedido de
    CRLF/LF). Anclar a inicio de línea evita partir por un ``--boundary`` que aparezca
    como CONTENIDO citado dentro del cuerpo de una parte (p. ej. el MIME crudo de otro
    mensaje en una cadena de reenvío), que con un ``split`` ingenuo truncaba el ``.eml``
    y podía descartar las partes siguientes sin avisar. Cada trozo conserva, como en un
    ``split`` ingenuo, el CRLF inicial del delimitador y el CRLF final que precede al
    delimitador siguiente (el caller los recorta). Preámbulo y epílogo se descartan.
    """
    delim = b"--" + boundary
    chunks: list[bytes] = []
    start: int | None = None
    i = body.find(delim)
    while i != -1:
        if i == 0 or body[i - 1:i] in (b"\n", b"\r"):       # delimitador a inicio de línea
            if start is not None:
                chunks.append(body[start:i])
            start = i + len(delim)
        i = body.find(delim, i + len(delim))
    return chunks


def _iter_raw_rfc822(block: bytes) -> Iterator[tuple[bytes, str]]:
    """``(cuerpo_verbatim, transfer_encoding)`` por cada parte ``message/rfc822``.

    Trata ``rfc822`` como hoja (no desciende). El cuerpo es el byte MIME tal cual,
    rebanado del crudo (sin pasar por el parser, que normaliza CRLF).
    """
    headers, body = _split_headers_body(block)
    m = _parse_message(headers + b"\r\n\r\n")
    if m.get_content_type() == "message/rfc822":
        yield body, (m.get("content-transfer-encoding") or "").strip().lower()
        return
    if m.get_content_maintype() == "multipart":
        boundary = m.get_boundary()
        if not boundary:
            return
        for ch in _split_mime_parts(body, boundary.encode()):
            ch = ch[2:] if ch.startswith(b"\r\n") else ch[1:] if ch[:1] in (b"\n", b"\r") else ch
            if ch.endswith(b"\r\n"):                        # el CRLF final es del delimitador
                ch = ch[:-2]
            elif ch[-1:] in (b"\n", b"\r"):
                ch = ch[:-1]
            yield from _iter_raw_rfc822(ch)


def _decode_cte(body: bytes, cte: str) -> bytes:
    if cte == "base64":
        return base64.b64decode(body)
    if cte == "quoted-printable":
        return quopri.decodestring(body)
    return body                                            # 7bit/8bit/binary → verbatim


def iter_nested_originals(raw: bytes) -> Iterator[tuple[bytes, str]]:
    """``(eml_original_bytes, parent_message_id)`` por cada email anidado, recursivo.

    Byte-fiel: rebana el crudo y decodifica el transfer-encoding → el ``.eml`` hijo
    EXACTO como viajó. Desciende a las hojas (email dentro de email dentro de email).
    """
    parent_mid = message_id_of(raw)
    for body, cte in _iter_raw_rfc822(raw):
        try:
            child = _decode_cte(body, cte)
        except Exception:  # noqa: BLE001 — un transfer-encoding corrupto no aborta el resto
            continue
        if not child.strip():
            continue
        yield child, parent_mid
        yield from iter_nested_originals(child)             # nietos, también byte-originales


def _nested_con_fallback(raw: bytes, report: "ExportReport") -> list[tuple[bytes, str]]:
    """Emails anidados byte-originales, con red de seguridad.

    Camino feliz (boundaries únicos por nivel): devuelve el rebanado byte-fiel. Cae al
    fallback re-serializado del parser (``as_bytes()``) + aviso en ``report.errors`` en
    dos casos: (a) el rebanado no halla nada pero el parser sí ve ``message/rfc822``;
    (b) un ``boundary`` se **reutiliza entre niveles** de anidamiento — ahí el rebanado
    por bytes puede truncar el ``.eml`` sin avisar (mismo conteo, contenido cortado),
    mientras que el parser lo resuelve con su pila de boundaries. Nunca trunca en
    silencio: en el peor caso, copia re-serializada marcada para revisión.
    """
    found = list(iter_nested_originals(raw))
    # Pre-filtro barato: sin partes message/rfc822 no hay anidados ni coste de parse.
    if b"message/rfc822" not in raw:
        return found
    msg = _parse_message(raw)
    boundaries = [
        b for b in (p.get_boundary() for p in msg.walk() if p.get_content_maintype() == "multipart")
        if b
    ]
    boundary_reuse = len(boundaries) != len(set(boundaries))
    if found and not boundary_reuse:
        return found  # byte-fiel y sin colisión de boundary entre niveles
    pmid = message_id_of(raw)
    fb: list[tuple[bytes, str]] = []
    for parte in msg.walk():
        if parte.get_content_type() == "message/rfc822":
            inner = _payload_message(parte)
            if inner is not None:
                fb.append((inner.as_bytes(), pmid))
    if fb and boundary_reuse:
        report.errors.append(
            f"boundary reutilizado entre niveles en {pmid or '(sin id)'}; "
            f"{len(fb)} email(s) re-serializados (no byte-fieles, revisar)."
        )
    elif fb:
        report.errors.append(
            f"aplanado byte-fiel falló para {pmid or '(sin id)'}; "
            f"{len(fb)} email(s) guardados re-serializados (revisar)."
        )
    return fb if fb else found


def _aplana_anidados(
    dest: Path,
    raw_bytes: bytes,
    vistos: set[str],
    procedencia: dict[str, str],
    report: "ExportReport",
) -> None:
    """Extrae a primer nivel cada email anidado (byte-original), dedup por Message-ID.

    Dedup por ``Message-ID``; cuando falta (raro: ``.eml`` viejos o clientes que lo
    omiten), respaldo por SHA-256 del contenido byte-original, de modo que el mismo
    bloque reenviado por dos vías en una corrida no se multiplique. La clave (mid o
    ``sha256:…``) se guarda en ``vistos``, que solo se reconstruye intra-corrida desde
    los ``Message-ID`` del disco; la idempotencia cross-corrida para hijos sin
    Message-ID no está garantizada (ver ``docs/MEJORAS_FUTURAS.md`` §44.3)."""
    for inner_bytes, parent_mid in _nested_con_fallback(raw_bytes, report):
        mid = message_id_of(inner_bytes)
        clave = mid or "sha256:" + compute_sha256_bytes(inner_bytes)
        if clave in vistos:
            report.nested_dedup += 1
            continue
        vistos.add(clave)
        if mid and parent_mid:
            procedencia[mid] = parent_mid
        nombre = eml_filename(parse_headers(inner_bytes))
        ruta = _ruta_unica(dest, nombre)
        ruta.write_bytes(inner_bytes)
        report.files.append(str(ruta.relative_to(dest)))
        report.nested_flattened += 1


# ---------------------------------------------------------------------------
# Idempotencia — Message-ID ya presentes en destino
# ---------------------------------------------------------------------------

def existing_message_ids(dest_dir: Path | str) -> set[str]:
    """Conjunto de ``Message-ID`` ya exportados bajo ``dest_dir`` (recursivo)."""
    dest = Path(dest_dir)
    if not dest.is_dir():
        return set()
    ids: set[str] = set()
    for eml in dest.rglob("*.eml"):
        try:
            mid = message_id_of(eml.read_bytes())
        except OSError:
            continue
        if mid:
            ids.add(mid)
    return ids


def _ruta_unica(base_dir: Path, nombre: str) -> Path:
    """Ruta de fichero no usada: añade ``_2``, ``_3``… si colisiona."""
    candidato = base_dir / nombre
    if not candidato.exists():
        return candidato
    stem, sufijo = Path(nombre).stem, Path(nombre).suffix
    n = 2
    while True:
        candidato = base_dir / f"{stem}_{n}{sufijo}"
        if not candidato.exists():
            return candidato
        n += 1


def _dir_unico(base_dir: Path, nombre: str) -> Path:
    candidato = base_dir / nombre
    if not candidato.exists():
        return candidato
    n = 2
    while True:
        candidato = base_dir / f"{nombre}_{n}"
        if not candidato.exists():
            return candidato
        n += 1


# ---------------------------------------------------------------------------
# Glue — Gmail API: resolver etiqueta, paginar, bajar raw
# ---------------------------------------------------------------------------

def resolve_label_id(service: Any, label: str) -> str | None:
    """Resuelve el ``labelId`` por nombre EXACTO vía ``labels().list``.

    NO usa ``q="label:…"`` (el parser de Gmail transforma rutas anidadas con
    espacios/acentos y suele devolver vacío). Devuelve ``None`` si no existe.
    """
    resp = service.users().labels().list(userId="me").execute()
    objetivo = (label or "").strip()
    for lab in resp.get("labels", []) or []:
        if (lab.get("name") or "").strip() == objetivo:
            return lab.get("id")
    return None


def list_label_message_ids(service: Any, label_id: str, *, page_size: int = 500) -> list[str]:
    """IDs de todos los mensajes de una etiqueta, paginando ``messages().list``."""
    ids: list[str] = []
    page_token: str | None = None
    msgs = service.users().messages()
    while True:
        resp = msgs.list(
            userId="me",
            labelIds=[label_id],
            maxResults=page_size,
            pageToken=page_token,
        ).execute()
        for ref in resp.get("messages", []) or []:
            mid = ref.get("id")
            if mid:
                ids.append(mid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            return ids


@dataclass
class ExportReport:
    """Informe de una corrida de :func:`export_label`."""

    account: str
    label: str
    label_id: str | None = None
    total_in_label: int = 0
    written: int = 0
    skipped: int = 0
    attachments: int = 0
    nested_flattened: int = 0   # emails anidados extraídos a primer nivel
    nested_dedup: int = 0       # emails anidados saltados por Message-ID duplicado
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    intake_logged: bool = False

    def resumen(self) -> str:
        return (
            f"etiqueta {self.label!r} ({self.account}): {self.total_in_label} mensajes; "
            f"{self.written} escritos, {self.skipped} ya presentes, "
            f"{self.attachments} adjuntos extraídos, "
            f"{self.nested_flattened} emails anidados aplanados ({self.nested_dedup} dup), "
            f"{len(self.errors)} errores"
        )


def export_label(
    account: str,
    label: str,
    dest_dir: Path | str,
    *,
    service: Any = None,
    case_id: str | None = None,
    extract_attachments: bool = False,
    max_workers: int = 8,
    force: bool = False,
    flatten_nested_emails: bool = True,
) -> ExportReport:
    """Exporta TODOS los mensajes de una etiqueta a ``dest_dir`` como ``.eml`` fieles.

    Idempotente (salta ``Message-ID`` ya presentes). **Estructura plana por defecto:**
    un ``.eml`` por mensaje en la raíz de ``dest_dir`` (el ``.eml`` ya contiene sus
    adjuntos embebidos). Con ``extract_attachments=True``, los mensajes con adjuntos
    van a una subcarpeta fechada con el ``.eml`` + los adjuntos extraídos como
    ficheros. Regenera ``INDICE.md``/``CRONOLOGIA.md`` al final. ``service`` se
    inyecta en tests; en producción se construye desde el token OAuth de la cuenta.

    **Rendimiento:**

    - ``max_workers`` (>1, solo en producción): baja los mensajes en paralelo con un
      pool de hilos (cada hilo su propio cliente Gmail). Acelera la 1ª corrida.
    - **Índice persistente** ``_exported_ids.json`` (por cuenta): las re-corridas
      **saltan la descarga** de los ``gmail_id`` ya exportados → casi instantáneas.
      ``force=True`` lo ignora y vuelve a bajar todo (útil si se borraron ficheros).

    **Emails anidados** (``flatten_nested_emails=True`` por defecto): los ``.eml`` que
    viajan como adjunto ``message/rfc822`` dentro de un correo padre se extraen
    byte-fieles a primer nivel de ``dest_dir``, nombrados por SU propia fecha (se
    integran en la cronología real), con dedup por ``Message-ID`` y procedencia
    (``forwarded_in``) en la traza. Recursivo hasta las hojas. ``False`` lo desactiva.

    Si se pasa ``case_id``, emite **traza forense** (mismo estándar que el intake de
    WhatsApp/manual): registra el SHA-256 de cada ``.eml``/adjunto presente en el
    ``IntakeManifest`` (``source="email"``, dedup cross-source) y emite un evento
    ``upload_email`` en ``_intake_log.jsonl`` con el mapeo Message-ID → sha → ruta.
    La traza se deriva del disco (no solo de lo recién descargado), así que **cubre
    también** ficheros depositados en corridas previas sin traza; es idempotente
    (sin nada nuevo que registrar no emite evento). ``dest_dir`` debe estar bajo el
    ``00_Input/`` de ese caso.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    creds = None
    if service is None:
        creds = _load_credentials(account)
        service = _build_service(creds)

    report = ExportReport(account=account, label=label)
    report.label_id = resolve_label_id(service, label)
    if report.label_id is None:
        report.errors.append(
            f"Etiqueta no encontrada en la cuenta {account!r}: {label!r}. "
            "¿Cuenta correcta? Las etiquetas E&V viven en @engelvoelkers."
        )
        return report

    msg_ids = list_label_message_ids(service, report.label_id)
    report.total_in_label = len(msg_ids)

    # B — índice persistente: saltar la descarga de los gmail_id ya exportados.
    index = _load_export_index(dest)
    ya_gids: set[str] = set() if force else set(index.get(account, []))
    candidates = [g for g in msg_ids if g not in ya_gids]
    report.skipped += len(msg_ids) - len(candidates)

    procedencia: dict[str, str] = {}
    if candidates:
        # Dedup por Message-ID (correctness): solo si hay algo que bajar (evita el
        # escaneo de disco en re-corridas que no descargan nada).
        vistos = existing_message_ids(dest)
        nuevos_gids: list[str] = []

        def _flatten_safe(gid: str, raw: bytes) -> None:
            """Aplana los anidados sin que un fallo aborte la corrida (un email
            problemático entre 125 no debe tumbar el resto)."""
            if not flatten_nested_emails:
                return
            try:
                _aplana_anidados(dest, raw, vistos, procedencia, report)
            except Exception as exc:  # noqa: BLE001 — un fallo de aplanado no aborta la corrida
                report.errors.append(f"{gid}: aplanado de anidados falló: {exc}")

        for gid, raw_bytes in _iter_raws(
            candidates, service=service, creds=creds, max_workers=max_workers, report=report
        ):
            mid = message_id_of(raw_bytes)
            if mid and mid in vistos:
                report.skipped += 1
                nuevos_gids.append(gid)  # bajado y resuelto (duplicado): no re-bajar
                # El padre ya está en disco, pero sus hijos anidados pueden faltar
                # (p. ej. tras borrar un hijo y re-exportar con force): reconciliarlos.
                # _aplana_anidados es idempotente (dedup por Message-ID + _ruta_unica).
                _flatten_safe(gid, raw_bytes)
                continue
            if mid:
                vistos.add(mid)
            try:
                eml_path = _escribe_mensaje(dest, raw_bytes, extract_attachments, report)
            except Exception as exc:  # noqa: BLE001 — un fallo no aborta la corrida
                report.errors.append(f"{gid}: {exc}")
                continue
            report.files.append(str(eml_path.relative_to(dest)))
            report.written += 1
            nuevos_gids.append(gid)
            _flatten_safe(gid, raw_bytes)

        index[account] = sorted(ya_gids | set(nuevos_gids))
        _save_export_index(dest, index)

    write_indices(dest)

    if case_id:
        _emit_traza(case_id, dest, account, label, report, procedencia)

    return report


def _escribe_mensaje(
    dest: Path, raw_bytes: bytes, extract_attachments: bool, report: ExportReport
) -> Path:
    """Escribe un mensaje en ``dest`` y devuelve la ruta del ``.eml``."""
    headers = parse_headers(raw_bytes)
    eml_bytes, adjuntos = split_eml(raw_bytes)
    nombre_eml = eml_filename(headers)
    if adjuntos and extract_attachments:
        carpeta = _dir_unico(dest, Path(nombre_eml).stem)
        carpeta.mkdir(parents=True, exist_ok=True)
        eml_path = carpeta / nombre_eml
        eml_path.write_bytes(eml_bytes)
        for idx, (fn, _mime, datos) in enumerate(adjuntos, start=1):
            seguro = _sanea_nombre_fichero(fn, fallback=f"adjunto_{idx}")
            _ruta_unica(carpeta, seguro).write_bytes(datos)
            report.attachments += 1
        return eml_path
    # Estructura plana: solo el .eml (con sus adjuntos embebidos).
    eml_path = _ruta_unica(dest, nombre_eml)
    eml_path.write_bytes(eml_bytes)
    return eml_path


# ---------------------------------------------------------------------------
# Descarga — secuencial o en paralelo (A) + índice de exportados (B)
# ---------------------------------------------------------------------------

_EXPORT_INDEX_NAME = "_exported_ids.json"


def _load_export_index(dest: Path) -> dict[str, list[str]]:
    """Carga el índice ``_exported_ids.json`` (``{cuenta: [gmail_id, …]}``)."""
    p = dest / _EXPORT_INDEX_NAME
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_export_index(dest: Path, index: dict[str, list[str]]) -> None:
    (dest / _EXPORT_INDEX_NAME).write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def _fetch_raw(service: Any, gmail_id: str) -> bytes:
    """Baja un mensaje ``format='raw'`` y lo decodifica a bytes RFC822."""
    msg = service.users().messages().get(userId="me", id=gmail_id, format="raw").execute()
    return decode_b64url_bytes(msg.get("raw", ""))


def _iter_raws(
    candidates: list[str],
    *,
    service: Any,
    creds: Any,
    max_workers: int,
    report: ExportReport,
):
    """Itera ``(gmail_id, raw_bytes)`` en el orden de ``candidates``.

    Secuencial cuando ``service`` está inyectado (tests) o ``max_workers<=1``; en
    producción (``creds`` disponible) baja en paralelo con un pool de hilos —cada
    hilo construye su propio cliente Gmail (httplib2 no es thread-safe)—, preservando
    el orden y tolerando errores por mensaje (se registran en ``report.errors``).
    """
    if creds is None or max_workers <= 1 or len(candidates) <= 1:
        for gid in candidates:
            try:
                yield gid, _fetch_raw(service, gid)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"{gid}: {exc}")
        return

    import threading
    from concurrent.futures import ThreadPoolExecutor

    local = threading.local()

    def worker(gid: str) -> bytes:
        svc = getattr(local, "svc", None)
        if svc is None:
            svc = _build_service(creds)
            local.svc = svc
        return _fetch_raw(svc, gid)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(worker, gid) for gid in candidates]
        for gid, fut in zip(candidates, futures):
            try:
                yield gid, fut.result()
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"{gid}: {exc}")


def _emit_traza(
    case_id: str,
    dest: Path,
    account: str,
    label: str,
    report: ExportReport,
    procedencia: dict[str, str] | None = None,
) -> None:
    """Traza forense derivada del disco: registra hashes + evento ``upload_email``.

    Recorre los ficheros presentes en ``dest`` (``.eml`` + adjuntos, excluyendo los
    índices generados) y registra en el ``IntakeManifest`` los que aún no constan
    (por ruta relativa). Emite UN evento ``upload_email`` con el mapeo
    Message-ID → sha → ruta de los ``.eml`` recién registrados; si no hay nada nuevo
    no emite (idempotente). ``dest`` está bajo ``00_Input/``, así que su padre es el
    root de rutas relativas del manifest.
    """
    procedencia = dict(procedencia or {})
    input_root = dest.parent  # 00_Input/
    nuevos_eml: list[dict[str, Any]] = []
    nuevos_adjuntos = 0
    disk_proc: dict[str, str] = {}     # hijo_mid → padre_mid reconstruido del disco

    with IntakeManifest(case_id) as manifest:
        ya_registrados = manifest.all_paths()
        for fichero in sorted(dest.rglob("*")):
            if not fichero.is_file():
                continue
            es_eml = fichero.suffix.lower() == ".eml"
            en_subcarpeta = fichero.parent != dest
            # Solo .eml o ficheros dentro de subcarpetas (adjuntos extraídos). Los
            # ficheros sueltos en la raíz (índices, _exported_ids.json) NO se trazan.
            if not es_eml and not en_subcarpeta:
                continue
            try:
                rel = fichero.relative_to(input_root).as_posix()
            except ValueError:
                rel = fichero.name
            if rel in ya_registrados:
                continue
            try:
                data = fichero.read_bytes()
            except OSError as exc:
                report.errors.append(f"traza {rel}: {exc}")
                continue
            # Procedencia desde disco: si este .eml transporta anidados, mapear cada
            # hijo → su padre. Es determinista (no depende del orden en que Gmail listó
            # padre vs. correo suelto) y cubre el backfill (re-export con case_id sin
            # descarga, donde ``procedencia`` de la corrida está vacío). Rebanado crudo,
            # sin parse completo; el pre-filtro evita escanear los .eml hoja.
            if es_eml and b"message/rfc822" in data:
                for child_bytes, parent_mid in iter_nested_originals(data):
                    cmid = message_id_of(child_bytes)
                    if cmid and parent_mid:
                        disk_proc.setdefault(cmid, parent_mid)
            sha = compute_sha256_bytes(data)
            if es_eml:
                mid = message_id_of(data)
                manifest.register(sha, rel, source="email", message_id=mid, kind="email")
                nuevos_eml.append({"message_id": mid, "sha256": sha, "path": rel})
            else:
                manifest.register(
                    sha, rel, source="email", kind="attachment", filename=fichero.name
                )
                nuevos_adjuntos += 1

    # forwarded_in: la procedencia de la corrida tiene prioridad; el resto se completa
    # desde el escaneo de disco (parents con anidados presentes).
    fuente_proc = {**disk_proc, **procedencia}
    for m in nuevos_eml:
        m["forwarded_in"] = fuente_proc.get(m["message_id"])

    if not nuevos_eml and not nuevos_adjuntos:
        return  # nada nuevo que trazar

    intake_log.append_event(
        case_id,
        "upload_email",
        details={
            "account": account,
            "label": label,
            "total_in_label": report.total_in_label,
            "descargados_esta_corrida": report.written,
            "registrados_eml": len(nuevos_eml),
            "registrados_adjuntos": nuevos_adjuntos,
            "mensajes": nuevos_eml,
        },
    )
    report.intake_logged = True


# ---------------------------------------------------------------------------
# Índices — INDICE.md (tabla) + CRONOLOGIA.md (ascendente)
# ---------------------------------------------------------------------------

@dataclass
class _Entrada:
    fecha: str
    asunto: str
    de: str
    ruta: str


def _recolecta_entradas(dest: Path) -> list[_Entrada]:
    entradas: list[_Entrada] = []
    for eml in dest.rglob("*.eml"):
        try:
            h = parse_headers(eml.read_bytes())
        except OSError:
            continue
        entradas.append(
            _Entrada(
                fecha=_fecha_iso(h.get("date")),
                asunto=(h.get("subject") or "(sin asunto)").replace("|", "/").strip(),
                de=(h.get("from") or "").replace("|", "/").strip(),
                ruta=str(eml.relative_to(dest)).replace("\\", "/"),
            )
        )
    entradas.sort(key=lambda e: (e.fecha, e.ruta))
    return entradas


def _escribe_utf8(path: Path, texto: str) -> None:
    path.write_text(texto, encoding="utf-8")


def write_indices(dest_dir: Path | str) -> None:
    """Regenera ``INDICE.md`` y ``CRONOLOGIA.md`` desde los ``.eml`` de ``dest_dir``."""
    dest = Path(dest_dir)
    entradas = _recolecta_entradas(dest)

    cab = (
        "<!-- Generado por core.email_export — NO editar a mano. -->\n"
        f"# Correos exportados — {len(entradas)} mensajes\n\n"
    )
    filas = ["| Fecha | Asunto | De | Fichero |", "| --- | --- | --- | --- |"]
    for e in entradas:
        filas.append(f"| {e.fecha} | {e.asunto} | {e.de} | `{e.ruta}` |")
    _escribe_utf8(dest / "INDICE.md", cab + "\n".join(filas) + "\n")

    crono = [
        "<!-- Generado por core.email_export — NO editar a mano. -->",
        "# Cronología de correos (ascendente)",
        "",
    ]
    for e in entradas:
        asunto = e.asunto or "(sin asunto)"
        crono.append(f"- **{e.fecha}** — {asunto} — {e.de} (`{e.ruta}`)")
    _escribe_utf8(dest / "CRONOLOGIA.md", "\n".join(crono) + "\n")


def email_dest_dir(case_id: str) -> Path:
    """Carpeta de destino canónica de los correos de un caso: ``00_Input/03_Email``.

    Resuelve ``case_id`` (acepta case_id canónico o W-code ``id_go``) al nombre de
    carpeta real antes de construir la ruta.
    """
    from .casos.case_locator import path_for, resolve_ref

    return path_for(resolve_ref(case_id)) / "00_Input" / "03_Email"
