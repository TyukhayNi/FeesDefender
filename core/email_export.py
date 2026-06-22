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
import re
import unicodedata
from dataclasses import dataclass, field
from email import policy
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

from .gmail_source import _build_service, _load_credentials

# ---------------------------------------------------------------------------
# Capa pura — base64url, cabeceras, nombre canónico, partición del .eml
# ---------------------------------------------------------------------------

_RE_PREFIJO_ASUNTO = re.compile(r"^\s*(re|rv|fwd?|fw|aw|wg)\s*:\s*", re.IGNORECASE)
_RE_NO_SLUG = re.compile(r"[^a-zA-Z0-9]+")
# Caracteres no admitidos en nombres de fichero de Windows (+ control).
_RE_FS_INVALIDO = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

_SIN_FECHA = "0000-00-00"
_MAXLEN_DESCRIPCION = 60


def decode_b64url_bytes(data: str) -> bytes:
    """Decodifica base64url de Gmail a bytes, con padding tolerante."""
    if not data:
        return b""
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


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
    limpio = _RE_FS_INVALIDO.sub("_", nombre or "").strip().strip(".").strip()
    return limpio or fallback


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
) -> ExportReport:
    """Exporta TODOS los mensajes de una etiqueta a ``dest_dir`` como ``.eml`` fieles.

    Idempotente (salta ``Message-ID`` ya presentes). Los mensajes con adjuntos van
    a una subcarpeta fechada con el ``.eml`` y los adjuntos extraídos. Regenera
    ``INDICE.md``/``CRONOLOGIA.md`` al final. ``service`` se inyecta en tests; en
    producción se construye desde el token OAuth de la cuenta.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    if service is None:
        service = _build_service(_load_credentials(account))

    report = ExportReport(account=account, label=label)
    report.label_id = resolve_label_id(service, label)
    if report.label_id is None:
        report.errors.append(
            f"Etiqueta no encontrada en la cuenta {account!r}: {label!r}. "
            "¿Cuenta correcta? Las etiquetas E&V viven en @engelvoelkers."
        )
        return report

    vistos = existing_message_ids(dest)
    msg_ids = list_label_message_ids(service, report.label_id)
    report.total_in_label = len(msg_ids)
    msgs = service.users().messages()

    for gmail_id in msg_ids:
        try:
            raw_msg = msgs.get(userId="me", id=gmail_id, format="raw").execute()
            raw_bytes = decode_b64url_bytes(raw_msg.get("raw", ""))
            mid = message_id_of(raw_bytes)
            if mid and mid in vistos:
                report.skipped += 1
                continue
            if mid:
                vistos.add(mid)

            headers = parse_headers(raw_bytes)
            eml_bytes, adjuntos = split_eml(raw_bytes)
            nombre_eml = eml_filename(headers)

            if adjuntos:
                carpeta = _dir_unico(dest, Path(nombre_eml).stem)
                carpeta.mkdir(parents=True, exist_ok=True)
                (carpeta / nombre_eml).write_bytes(eml_bytes)
                for idx, (fn, _mime, datos) in enumerate(adjuntos, start=1):
                    seguro = _sanea_nombre_fichero(fn, fallback=f"adjunto_{idx}")
                    destino_adj = _ruta_unica(carpeta, seguro)
                    destino_adj.write_bytes(datos)
                    report.attachments += 1
                report.files.append(str((carpeta / nombre_eml).relative_to(dest)))
            else:
                destino = _ruta_unica(dest, nombre_eml)
                destino.write_bytes(eml_bytes)
                report.files.append(str(destino.relative_to(dest)))

            report.written += 1
        except Exception as exc:  # noqa: BLE001 — un fallo no aborta la corrida
            report.errors.append(f"{gmail_id}: {exc}")

    write_indices(dest)
    return report


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
    """Carpeta de destino canónica de los correos de un caso: ``00_Input/03_Email``."""
    from .casos.case_locator import path_for

    return path_for(case_id) / "00_Input" / "03_Email"
