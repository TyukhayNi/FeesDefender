"""Tests del motor de exportación de etiqueta Gmail → expediente.

- **Capa pura:** nombre canónico (``eml_filename``), partición del ``.eml``
  (``split_eml``), dedup por ``Message-ID``.
- **Glue:** ``export_label`` con un ``service`` falso (boundary de red), cubriendo
  paginación, subcarpeta fechada con adjuntos, idempotencia y etiqueta inexistente.

Solo lectura: el servicio falso no expone modificación; verificamos que nunca se
pide marcar como leído.
"""

from __future__ import annotations

import base64
from email.message import EmailMessage as PyEmailMessage

from core import email_export as ee


# ---------------------------------------------------------------------------
# Helpers — construir mensajes RFC822 crudos
# ---------------------------------------------------------------------------

def _build_raw(
    *,
    message_id: str,
    subject: str = "Asunto de prueba",
    date: str = "Thu, 12 Jun 2026 10:00:00 +0200",
    from_addr: str = "Eva <eva@engelvoelkers.com>",
    body: str = "Cuerpo del correo.",
    attachments: list[tuple[str, str, bytes]] | None = None,
) -> bytes:
    msg = PyEmailMessage()
    msg["Message-ID"] = message_id
    msg["Subject"] = subject
    msg["Date"] = date
    msg["From"] = from_addr
    msg["To"] = "despacho@tyukhay.legal"
    msg.set_content(body)
    for fn, mime, datos in attachments or []:
        maintype, _, subtype = mime.partition("/")
        msg.add_attachment(datos, maintype=maintype, subtype=subtype, filename=fn)
    return msg.as_bytes()


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


# ---------------------------------------------------------------------------
# Capa pura — eml_filename
# ---------------------------------------------------------------------------

def test_eml_filename_fecha_iso_y_descripcion():
    nombre = ee.eml_filename(
        {"date": "Thu, 12 Jun 2026 10:00:00 +0200", "subject": "Oferta Tibidabo 8"}
    )
    assert nombre == "2026-06-12_oferta_tibidabo_8.eml"


def test_eml_filename_quita_prefijos_re_fwd_y_acentos():
    nombre = ee.eml_filename(
        {"date": "Fri, 13 Jun 2026 09:00:00 +0200", "subject": "RE: RV: Comisión pendiente"}
    )
    assert nombre == "2026-06-13_comision_pendiente.eml"


def test_eml_filename_sin_fecha_ni_asunto():
    assert ee.eml_filename({}) == "0000-00-00_sin_asunto.eml"


def test_eml_filename_fecha_invalida_cae_a_sentinela():
    nombre = ee.eml_filename({"date": "no es una fecha", "subject": "x"})
    assert nombre.startswith("0000-00-00_")


# ---------------------------------------------------------------------------
# Capa pura — split_eml
# ---------------------------------------------------------------------------

def test_split_eml_devuelve_raw_fiel_y_sin_adjuntos():
    raw = _build_raw(message_id="<a@x>")
    eml_bytes, adjuntos = ee.split_eml(raw)
    assert eml_bytes == raw  # byte-fiel
    assert adjuntos == []


def test_split_eml_extrae_adjuntos():
    raw = _build_raw(
        message_id="<b@x>",
        attachments=[
            ("contrato.pdf", "application/pdf", b"%PDF-1.4 datos"),
            ("foto.jpg", "image/jpeg", b"\xff\xd8\xff datos"),
        ],
    )
    eml_bytes, adjuntos = ee.split_eml(raw)
    assert eml_bytes == raw
    nombres = {fn for fn, _m, _d in adjuntos}
    assert nombres == {"contrato.pdf", "foto.jpg"}
    por_nombre = {fn: datos for fn, _m, datos in adjuntos}
    assert por_nombre["contrato.pdf"] == b"%PDF-1.4 datos"


def test_message_id_normalizado():
    raw = _build_raw(message_id="<id-con-corchetes@x>")
    assert ee.message_id_of(raw) == "id-con-corchetes@x"


# ---------------------------------------------------------------------------
# Capa pura — dedup / existing_message_ids
# ---------------------------------------------------------------------------

def test_existing_message_ids_escanea_recursivo(tmp_path):
    (tmp_path / "2026-06-12_uno.eml").write_bytes(_build_raw(message_id="<uno@x>"))
    sub = tmp_path / "2026-06-13_dos"
    sub.mkdir()
    (sub / "2026-06-13_dos.eml").write_bytes(_build_raw(message_id="<dos@x>"))
    assert ee.existing_message_ids(tmp_path) == {"uno@x", "dos@x"}


def test_existing_message_ids_dir_inexistente():
    assert ee.existing_message_ids("/no/existe/seguro") == set()


# ---------------------------------------------------------------------------
# Service falso — boundary de red de la Gmail API
# ---------------------------------------------------------------------------

class _Exec:
    def __init__(self, result):
        self._r = result

    def execute(self):
        return self._r


class _Labels:
    def __init__(self, labels):
        self._labels = labels

    def list(self, **kw):
        return _Exec({"labels": self._labels})


class _Messages:
    def __init__(self, pages, raws):
        self._pages = pages  # lista de respuestas de list()
        self._raws = raws    # gmail_id -> raw bytes
        self.list_calls = 0
        self.got_formats: list[str] = []

    def list(self, **kw):
        page = self._pages[min(self.list_calls, len(self._pages) - 1)]
        self.list_calls += 1
        return _Exec(page)

    def get(self, *, userId, id, format):
        self.got_formats.append(format)
        return _Exec({"id": id, "raw": _b64url(self._raws[id])})


class _Users:
    def __init__(self, labels, messages):
        self._labels = labels
        self._messages = messages

    def labels(self):
        return self._labels

    def messages(self):
        return self._messages


class _FakeService:
    def __init__(self, *, labels, pages, raws):
        self._users = _Users(_Labels(labels), _Messages(pages, raws))

    def users(self):
        return self._users


_LABELS = [
    {"id": "Label_1", "name": "INBOX"},
    {"id": "Label_99", "name": "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - Tibidabo 8 - (W-02VND1)"},
]
_ETIQUETA = "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - Tibidabo 8 - (W-02VND1)"


def test_export_label_etiqueta_inexistente(tmp_path):
    svc = _FakeService(labels=_LABELS, pages=[{}], raws={})
    rep = ee.export_label("nikolai@engelvoelkers.com", "Etiqueta inexistente", tmp_path, service=svc)
    assert rep.label_id is None
    assert rep.errors and "no encontrada" in rep.errors[0].lower()
    assert rep.written == 0


def test_export_label_escribe_eml_planos_y_paginado(tmp_path):
    raws = {
        "g1": _build_raw(message_id="<m1@x>", subject="Primera", date="Thu, 12 Jun 2026 10:00:00 +0200"),
        "g2": _build_raw(message_id="<m2@x>", subject="Segunda", date="Fri, 13 Jun 2026 10:00:00 +0200"),
        "g3": _build_raw(message_id="<m3@x>", subject="Tercera", date="Sat, 14 Jun 2026 10:00:00 +0200"),
    }
    pages = [
        {"messages": [{"id": "g1"}, {"id": "g2"}], "nextPageToken": "p2"},
        {"messages": [{"id": "g3"}]},
    ]
    svc = _FakeService(labels=_LABELS, pages=pages, raws=raws)

    rep = ee.export_label("nikolai@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)

    assert rep.label_id == "Label_99"
    assert rep.total_in_label == 3
    assert rep.written == 3
    assert rep.skipped == 0
    # format='raw' siempre (eml fiel); nunca se pide modificar
    assert set(svc._users._messages.got_formats) == {"raw"}
    emls = sorted(p.name for p in tmp_path.glob("*.eml"))
    assert emls == ["2026-06-12_primera.eml", "2026-06-13_segunda.eml", "2026-06-14_tercera.eml"]
    assert (tmp_path / "INDICE.md").exists()
    assert (tmp_path / "CRONOLOGIA.md").exists()


def test_export_label_adjuntos_en_subcarpeta_fechada(tmp_path):
    raws = {
        "g1": _build_raw(
            message_id="<conadj@x>",
            subject="Con adjunto",
            attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")],
        ),
    }
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws=raws)

    rep = ee.export_label("nikolai@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)

    assert rep.written == 1
    assert rep.attachments == 1
    carpeta = tmp_path / "2026-06-12_con_adjunto"
    assert carpeta.is_dir()
    assert (carpeta / "2026-06-12_con_adjunto.eml").exists()
    assert (carpeta / "contrato.pdf").read_bytes() == b"%PDF datos"


def test_export_label_idempotente(tmp_path):
    raws = {
        "g1": _build_raw(message_id="<m1@x>", subject="Primera"),
        "g2": _build_raw(message_id="<m2@x>", subject="Segunda"),
    }
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}]}]
    svc1 = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    rep1 = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc1)
    assert rep1.written == 2

    # Segunda corrida: mismos mensajes → todo saltado, nada duplicado.
    svc2 = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    rep2 = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc2)
    assert rep2.written == 0
    assert rep2.skipped == 2
    assert len(list(tmp_path.glob("*.eml"))) == 2


def test_export_label_dedup_dentro_de_la_corrida(tmp_path):
    """El mismo Message-ID en dos gmail_id (p. ej. dos copias) se escribe una vez."""
    raws = {
        "g1": _build_raw(message_id="<dup@x>", subject="Duplicado"),
        "g2": _build_raw(message_id="<dup@x>", subject="Duplicado"),
    }
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}]}]
    svc = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.written == 1
    assert rep.skipped == 1


# ---------------------------------------------------------------------------
# Traza forense — manifest (SHA-256) + evento upload_email (con case_id)
# ---------------------------------------------------------------------------

def _setup_caso(case_id: str):
    import importlib

    from core import case_manager, config as cfg

    importlib.reload(cfg)
    importlib.reload(case_manager)
    case_manager.ensure_case(case_id, titulo="Caso email export test")
    return case_id


def test_export_label_emite_traza_forense(tmp_casos_root):
    from core import intake_log
    from core.intake_manifest import IntakeManifest

    case_id = _setup_caso("EMAIL-2026-001")
    raws = {
        "g1": _build_raw(
            message_id="<conadj@x>",
            subject="Con adjunto",
            attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")],
        ),
        "g2": _build_raw(message_id="<plano@x>", subject="Plano"),
    }
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}]}]
    svc = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    dest = ee.email_dest_dir(case_id)

    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest, service=svc, case_id=case_id)

    assert rep.written == 2
    assert rep.intake_logged is True

    # Evento upload_email único, con el mapeo Message-ID → sha → ruta.
    eventos = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_email"]
    assert len(eventos) == 1
    det = eventos[0]["details"]
    assert det["registrados_eml"] == 2
    assert det["registrados_adjuntos"] == 1
    assert det["label"] == _ETIQUETA
    mids = {m["message_id"] for m in det["mensajes"]}
    assert mids == {"conadj@x", "plano@x"}
    assert all(m["sha256"] for m in det["mensajes"])

    # Manifest: SHA-256 de los 3 ficheros físicos (2 .eml + 1 adjunto).
    man = IntakeManifest(case_id)
    man.load()
    rutas = man.all_paths()
    assert any(p.endswith("contrato.pdf") for p in rutas)
    assert sum(1 for p in rutas if p.endswith(".eml")) == 2


def test_export_label_traza_idempotente(tmp_casos_root):
    """2ª corrida sin correos nuevos: ni evento ni cambios; intake_logged False."""
    from core import intake_log

    case_id = _setup_caso("EMAIL-2026-002")
    raws = {"g1": _build_raw(message_id="<m1@x>", subject="Uno")}
    pages = [{"messages": [{"id": "g1"}]}]
    dest = ee.email_dest_dir(case_id)

    rep1 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws), case_id=case_id,
    )
    assert rep1.written == 1 and rep1.intake_logged is True

    rep2 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws), case_id=case_id,
    )
    assert rep2.written == 0
    assert rep2.skipped == 1
    assert rep2.intake_logged is False

    eventos = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_email"]
    assert len(eventos) == 1  # solo el de la 1ª corrida


def test_export_label_traza_backfill_de_corrida_previa(tmp_casos_root):
    """Exportado antes SIN case_id (sin traza); al re-exportar CON case_id, la traza
    registra los ficheros ya presentes y emite el evento (caso real W-02VND1)."""
    from core import intake_log
    from core.intake_manifest import IntakeManifest

    case_id = _setup_caso("EMAIL-2026-003")
    raws = {
        "g1": _build_raw(
            message_id="<a@x>", subject="Con adjunto",
            attachments=[("doc.pdf", "application/pdf", b"%PDF x")],
        ),
        "g2": _build_raw(message_id="<b@x>", subject="Plano"),
    }
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}]}]
    dest = ee.email_dest_dir(case_id)

    # 1ª corrida: SIN case_id → escribe los ficheros pero NO emite traza.
    rep0 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws),
    )
    assert rep0.written == 2 and rep0.intake_logged is False
    assert intake_log.read_events(case_id) == []

    # 2ª corrida: CON case_id → 0 descargados (idempotente) pero traza de lo presente.
    rep1 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws), case_id=case_id,
    )
    assert rep1.written == 0           # nada nuevo que descargar
    assert rep1.intake_logged is True  # pero sí se trazó lo ya depositado

    eventos = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_email"]
    assert len(eventos) == 1
    det = eventos[0]["details"]
    assert det["descargados_esta_corrida"] == 0
    assert det["registrados_eml"] == 2
    assert det["registrados_adjuntos"] == 1

    man = IntakeManifest(case_id)
    man.load()
    assert any(p.endswith("doc.pdf") for p in man.all_paths())

    # 3ª corrida: ya todo registrado → no re-emite.
    rep2 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws), case_id=case_id,
    )
    assert rep2.intake_logged is False
    assert len([e for e in intake_log.read_events(case_id) if e["event"] == "upload_email"]) == 1
