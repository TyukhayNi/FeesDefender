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

import email
import json
import re
import unicodedata
from dataclasses import dataclass, field
from email import policy
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

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


def split_eml(raw: bytes) -> tuple[bytes, list[tuple[str, str, bytes]]]:
    """Parte el mensaje crudo en ``(eml_fiel, [(filename, mime, bytes)])``.

    El primer elemento son los bytes RFC822 **tal cual** (el ``.eml`` fiel). El
    segundo, los adjuntos decodificados (partes con disposición ``attachment`` o
    con nombre de fichero).
    """
    msg = _parse_message(raw)
    adjuntos: list[tuple[str, str, bytes]] = []
    for parte in msg.walk():
        if parte.get_content_maintype() == "multipart":
            continue
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
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    intake_logged: bool = False

    def resumen(self) -> str:
        return (
            f"etiqueta {self.label!r} ({self.account}): {self.total_in_label} mensajes; "
            f"{self.written} escritos, {self.skipped} ya presentes, "
            f"{self.attachments} adjuntos extraídos, {len(self.errors)} errores"
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

    if candidates:
        # Dedup por Message-ID (correctness): solo si hay algo que bajar (evita el
        # escaneo de disco en re-corridas que no descargan nada).
        vistos = existing_message_ids(dest)
        nuevos_gids: list[str] = []
        for gid, raw_bytes in _iter_raws(
            candidates, service=service, creds=creds, max_workers=max_workers, report=report
        ):
            mid = message_id_of(raw_bytes)
            if mid and mid in vistos:
                report.skipped += 1
                nuevos_gids.append(gid)  # bajado y resuelto (duplicado): no re-bajar
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

        index[account] = sorted(ya_gids | set(nuevos_gids))
        _save_export_index(dest, index)

    write_indices(dest)

    if case_id:
        _emit_traza(case_id, dest, account, label, report)

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
) -> None:
    """Traza forense derivada del disco: registra hashes + evento ``upload_email``.

    Recorre los ficheros presentes en ``dest`` (``.eml`` + adjuntos, excluyendo los
    índices generados) y registra en el ``IntakeManifest`` los que aún no constan
    (por ruta relativa). Emite UN evento ``upload_email`` con el mapeo
    Message-ID → sha → ruta de los ``.eml`` recién registrados; si no hay nada nuevo
    no emite (idempotente). ``dest`` está bajo ``00_Input/``, así que su padre es el
    root de rutas relativas del manifest.
    """
    input_root = dest.parent  # 00_Input/
    nuevos_eml: list[dict[str, Any]] = []
    nuevos_adjuntos = 0

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
