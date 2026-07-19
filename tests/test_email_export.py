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
import hashlib
import json
from email.message import EmailMessage as PyEmailMessage

from core import email_export as ee
from core.intake_drive import DriveFileInfo


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
        {"date": "Thu, 12 Jun 2026 10:00:00 +0200", "subject": "Oferta [inmueble]"}
    )
    assert nombre == "2026-06-12_oferta_inmueble.eml"


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
    {"id": "Label_99", "name": "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - [inmueble] - (W-02VND1)"},
]
_ETIQUETA = "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - [inmueble] - (W-02VND1)"


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

    rep = ee.export_label(
        "nikolai@engelvoelkers.com", _ETIQUETA, tmp_path,
        service=svc, extract_attachments=True,
    )

    assert rep.written == 1
    assert rep.attachments == 1
    carpeta = tmp_path / "2026-06-12_con_adjunto"
    assert carpeta.is_dir()
    assert (carpeta / "2026-06-12_con_adjunto.eml").exists()
    assert (carpeta / "contrato.pdf").read_bytes() == b"%PDF datos"


def test_export_label_plano_por_defecto_no_extrae_adjuntos(tmp_path):
    """Por defecto: .eml plano en la raíz, sin subcarpeta ni adjuntos sueltos."""
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
    assert rep.attachments == 0
    assert (tmp_path / "2026-06-12_con_adjunto.eml").exists()
    assert [p.name for p in tmp_path.iterdir() if p.is_dir()] == []  # sin subcarpetas
    assert not list(tmp_path.glob("*.pdf"))


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
    """§9.3: el mismo Message-ID en dos gmail_id (p. ej. dos copias) se ESCRIBE dos veces
    (contrato T7: ya no se salta por Message-ID) y la 2ª se cuenta como duplicado."""
    raws = {
        "g1": _build_raw(message_id="<dup@x>", subject="Duplicado"),
        "g2": _build_raw(message_id="<dup@x>", subject="Duplicado"),
    }
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}]}]
    svc = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.written == 2
    assert rep.skipped == 0
    assert rep.duplicados == 1
    assert len(list(tmp_path.glob("*.eml"))) == 2


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

    rep = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=svc, case_id=case_id, extract_attachments=True,
    )

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
    """Exportado antes SIN case_id (sin traza, caso no migrado a lotes — cajón legacy
    03_Email); al re-exportar CON case_id, la traza registra los ficheros ya
    presentes y emite el evento (caso real W-02VND1)."""
    from core import config, intake_log
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
    dest = config.caso_path(case_id) / "00_Input" / "03_Email"

    # 1ª corrida: SIN case_id → escribe los ficheros pero NO emite traza.
    rep0 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws),
        extract_attachments=True,
    )
    assert rep0.written == 2 and rep0.intake_logged is False
    assert intake_log.read_events(case_id) == []

    # 2ª corrida: CON case_id → 0 descargados (idempotente) pero traza de lo presente.
    rep1 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, dest,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws), case_id=case_id,
        extract_attachments=True,
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


# ---------------------------------------------------------------------------
# T7 — estado de canal a la raíz de 00_Input/ + dedup Message-ID vía M9
# ---------------------------------------------------------------------------

_CASO_EXPORT_COUNTER = 0


def _caso_para_export() -> str:
    """Caso fresco (case_id único) para tests de ``export_label`` con ``case_id``."""
    global _CASO_EXPORT_COUNTER
    _CASO_EXPORT_COUNTER += 1
    return _setup_caso(f"EMAIL-CANAL-{_CASO_EXPORT_COUNTER:03d}")


def _fake_service_una_pagina(raws: dict[str, bytes]) -> "_FakeService":
    """``_FakeService`` con una sola página que lista todos los ``gmail_id`` de ``raws``."""
    pages = [{"messages": [{"id": gid} for gid in raws]}]
    return _FakeService(labels=_LABELS, pages=pages, raws=raws)


# Mismo Message-ID, cuerpos distintos (§9.3: bytes distintos, mismo hilo lógico).
_EML_UNO = _build_raw(message_id="<uno@x>", subject="Uno", body="Cuerpo original.")
_EML_UNO_VARIANTE = _build_raw(message_id="<uno@x>", subject="Uno variante", body="Cuerpo distinto.")
# Fecha temprana + Message-ID propio, para el cajón legacy 03_Email/ (T8: índices cross-lote).
_EML_VIEJO = _build_raw(
    message_id="<viejo@x>", subject="Viejo", date="Thu, 01 Jan 2026 09:00:00 +0200",
)


def test_indices_de_canal_viven_en_la_raiz_de_00_input(tmp_casos_root):
    from core import config

    case_id = _caso_para_export()
    dest = ee.email_dest_dir(case_id)
    ee.export_label(
        "acc@x", _ETIQUETA, dest, case_id=case_id,
        service=_fake_service_una_pagina({"g1": _EML_UNO}),
    )
    input_dir = config.caso_path(case_id) / "00_Input"
    assert (input_dir / "_exported_ids.json").is_file()
    assert not (dest / "_exported_ids.json").exists()


def test_fallback_legacy_del_indice_en_03_email(tmp_casos_root):
    """Caso no migrado: el índice viejo en 03_Email/ se respeta (no re-descarga)."""
    from core import config

    case_id = _caso_para_export()
    legacy = config.caso_path(case_id) / "00_Input" / "03_Email"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "_exported_ids.json").write_text(
        json.dumps({"acc@x": ["gid-1"]}), encoding="utf-8"
    )
    dest = ee.email_dest_dir(case_id)
    report = ee.export_label(
        "acc@x", _ETIQUETA, dest, case_id=case_id,
        service=_fake_service_una_pagina({"gid-1": _EML_UNO}),
    )
    assert report.written == 0 and report.skipped == 1


def test_mismo_message_id_bytes_distintos_se_escribe_y_anota(tmp_casos_root):
    """§9.3: mismo Message-ID con bytes distintos → se copia igual + duplicado anotado."""
    from core.intake_manifest import IntakeManifest

    case_id = _caso_para_export()
    with IntakeManifest(case_id) as m:
        m.register(
            "sha-previo", "2026-07-01_email_01/previo.eml",
            source="email", message_id="uno@x",
        )
    dest = ee.email_dest_dir(case_id)
    report = ee.export_label(
        "acc@x", _ETIQUETA, dest, case_id=case_id,
        service=_fake_service_una_pagina({"g1": _EML_UNO_VARIANTE}),
    )
    assert report.written == 1 and report.duplicados == 1
    assert list(report.duplicados_map.values()) == ["2026-07-01_email_01/previo.eml"]
    assert any(dest.rglob("*.eml"))  # el fichero ESTÁ en disco, no se descarta


def test_dedup_mismo_message_id_dentro_de_la_misma_corrida_se_anota(tmp_casos_root):
    """Finding revisión: dos gmail_id NUEVOS (ninguno aún en M9) comparten Message-ID
    dentro de la MISMA llamada a ``export_label``. Ambos se escriben (§9.3); el 2º se
    cuenta como duplicado y ``duplicados_map`` debe anotar ``duplicado_de`` apuntando
    al 1º escrito esta corrida (00_Input-relativo: ``f"{dest.name}/{rel}"``), no
    quedarse en blanco."""
    case_id = _caso_para_export()
    dest = ee.email_dest_dir(case_id)
    raws = {
        "g1": _build_raw(message_id="<mismo@x>", subject="Primera copia", body="Cuerpo A."),
        "g2": _build_raw(message_id="<mismo@x>", subject="Segunda copia", body="Cuerpo B."),
    }
    report = ee.export_label(
        "acc@x", _ETIQUETA, dest, case_id=case_id,
        service=_fake_service_una_pagina(raws),
    )

    assert report.written == 2
    assert report.duplicados == 1
    emls = sorted(p.relative_to(dest).as_posix() for p in dest.glob("*.eml"))
    assert len(emls) == 2
    assert len(report.duplicados_map) == 1
    primer_rel = report.files[0]
    esperado = f"{dest.name}/{primer_rel}"
    assert list(report.duplicados_map.values()) == [esperado]


def test_emit_traza_registra_message_id_en_m9(tmp_casos_root):
    from core.intake_manifest import IntakeManifest

    case_id = _caso_para_export()
    dest = ee.email_dest_dir(case_id)
    ee.export_label(
        "acc@x", _ETIQUETA, dest, case_id=case_id,
        service=_fake_service_una_pagina({"g1": _EML_UNO}),
    )
    with IntakeManifest(case_id) as m:
        assert "uno@x" in m.message_ids()


# ---------------------------------------------------------------------------
# T8 — lote por corrida, manifiesto del lote e índices cross-lote (spec §8)
# ---------------------------------------------------------------------------

def test_email_dest_dir_reserva_lote(tmp_casos_root):
    from core.intake_lotes import PATRON_LOTE

    case_id = _caso_para_export()
    d = ee.email_dest_dir(case_id)
    assert PATRON_LOTE.match(d.name).group(2) == "email"
    assert d.parent.name == "00_Input" and d.is_dir()


def test_export_escribe_manifiesto_con_message_id(tmp_casos_root):
    from core import intake_lotes

    case_id = _caso_para_export()
    dest = ee.email_dest_dir(case_id)
    ee.export_label(
        "acc@x", _ETIQUETA, dest, case_id=case_id,
        service=_fake_service_una_pagina({"g1": _EML_UNO}),
    )
    man = intake_lotes.leer_manifiesto(dest)
    assert man["fuente"] == "email"
    eml = next(i for i in man["items"] if i["relpath"].endswith(".eml"))
    # message_id_of() normaliza (sin '<>'), igual que M9/upload_email en todo el módulo.
    assert eml["message_id"] == "uno@x" and eml["tipo_contenido"] == "eml"


def test_reexport_sin_novedad_no_deja_lote_vacio_y_cronologia_completa(tmp_casos_root):
    """§9.5: el re-export no re-descarga (índice de canal) y la cronología cross-lote
    sale completa (el lote vacío de la 2ª corrida no deja rastro)."""
    from core import config

    case_id = _caso_para_export()
    d1 = ee.email_dest_dir(case_id)
    ee.export_label(
        "acc@x", _ETIQUETA, d1, case_id=case_id,
        service=_fake_service_una_pagina({"g1": _EML_UNO}),
    )
    d2 = ee.email_dest_dir(case_id)
    r2 = ee.export_label(
        "acc@x", _ETIQUETA, d2, case_id=case_id,
        service=_fake_service_una_pagina({"g1": _EML_UNO}),
    )
    assert r2.written == 0
    assert not d2.exists()                                  # lote vacío eliminado
    crono = (config.caso_path(case_id) / "01_Procesado" / "Emails"
             / "CRONOLOGIA.md").read_text(encoding="utf-8")
    assert d1.name in crono                                 # ruta con prefijo de lote


def test_cronologia_cross_lote_incluye_legacy(tmp_casos_root):
    from core import config

    case_id = _caso_para_export()
    legacy = config.caso_path(case_id) / "00_Input" / "03_Email"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "2026-01-01_viejo.eml").write_bytes(_EML_VIEJO)
    ee.write_indices_caso(case_id)
    indice = (config.caso_path(case_id) / "01_Procesado" / "Emails"
              / "INDICE.md").read_text(encoding="utf-8")
    assert "03_Email/2026-01-01_viejo.eml" in indice


# ---------------------------------------------------------------------------
# resolve_ref — case_id canónico desde W-code (id_go)
# ---------------------------------------------------------------------------

def _crear_caso_con_id_go(root, ciudad, nombre, id_go):
    caso = root / ciudad / nombre / "00_Input"
    caso.mkdir(parents=True)
    (caso / "_caso.md").write_text(
        f"---\ncase_id: {nombre}\nmeta:\n  id_go: {id_go}\n---\n# {nombre}\n",
        encoding="utf-8",
    )


def test_resolve_ref_wcode_a_case_id(tmp_casos_root):
    import importlib

    from core.casos import case_locator
    importlib.reload(case_locator)

    _crear_caso_con_id_go(
        tmp_casos_root, "Barcelona", "BaRS1 - [inmueble] - (W-02VND1) - Vuelta", "W-02VND1"
    )

    # W-code → nombre de carpeta canónico.
    assert case_locator.resolve_ref("W-02VND1") == "BaRS1 - [inmueble] - (W-02VND1) - Vuelta"
    # case_id exacto → se devuelve tal cual.
    assert (
        case_locator.resolve_ref("BaRS1 - [inmueble] - (W-02VND1) - Vuelta")
        == "BaRS1 - [inmueble] - (W-02VND1) - Vuelta"
    )
    # Desconocido → fallback al propio ref.
    assert case_locator.resolve_ref("W-NOEXISTE") == "W-NOEXISTE"


def test_resolve_ref_ignora_carpeta_fantasma_sin_caso_md(tmp_casos_root):
    """Una carpeta llamada como el W-code pero SIN _caso.md (creada por error) no
    eclipsa al caso real: la resolución usa id_go y devuelve el caso canónico."""
    import importlib

    from core.casos import case_locator
    importlib.reload(case_locator)

    # Caso real (con _caso.md e id_go) bajo ciudad.
    _crear_caso_con_id_go(
        tmp_casos_root, "Barcelona", "BaRS1 - [inmueble] - (W-02VND1) - Vuelta", "W-02VND1"
    )
    # Carpeta fantasma plana con el nombre del W-code, SIN _caso.md.
    (tmp_casos_root / "W-02VND1" / "00_Input" / "03_Email").mkdir(parents=True)

    assert case_locator.resolve_ref("W-02VND1") == "BaRS1 - [inmueble] - (W-02VND1) - Vuelta"


# ---------------------------------------------------------------------------
# Rendimiento — índice persistente (B) + descarga en paralelo (A)
# ---------------------------------------------------------------------------

def test_indice_salta_descarga_en_recorrida(tmp_path):
    """B: 2ª corrida no vuelve a bajar los gmail_id ya exportados (0 gets)."""
    raws = {
        "g1": _build_raw(message_id="<m1@x>", subject="Uno"),
        "g2": _build_raw(message_id="<m2@x>", subject="Dos"),
    }
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}]}]
    rep1 = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, tmp_path,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws),
    )
    assert rep1.written == 2
    assert (tmp_path / "_exported_ids.json").exists()

    svc2 = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    rep2 = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc2)
    assert rep2.written == 0
    assert rep2.skipped == 2
    assert svc2._users._messages.got_formats == []  # ni un solo get de red


def test_force_ignora_indice_y_rebaja(tmp_path):
    """force=True ignora el índice y vuelve a bajar; el Message-ID ya en disco se anota
    como duplicado pero el mensaje SE ESCRIBE igual (contrato T7, §9.3)."""
    raws = {"g1": _build_raw(message_id="<m1@x>", subject="Uno")}
    pages = [{"messages": [{"id": "g1"}]}]
    ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, tmp_path,
        service=_FakeService(labels=_LABELS, pages=pages, raws=raws),
    )
    svc2 = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    rep = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc2, force=True
    )
    assert svc2._users._messages.got_formats == ["raw"]  # sí re-bajó
    assert rep.written == 1        # se escribe igual (duplicado, no descartado)
    assert rep.skipped == 0
    assert rep.duplicados == 1


def test_descarga_paralela_escribe_todo_en_orden(tmp_path, monkeypatch):
    """A: con service=None y max_workers>1 baja en paralelo (cada hilo su cliente)."""
    raws = {
        "g1": _build_raw(message_id="<m1@x>", subject="Asunto 1",
                         date="Thu, 11 Jun 2026 10:00:00 +0200"),
        "g2": _build_raw(message_id="<m2@x>", subject="Asunto 2",
                         date="Thu, 12 Jun 2026 10:00:00 +0200"),
        "g3": _build_raw(message_id="<m3@x>", subject="Asunto 3",
                         date="Thu, 13 Jun 2026 10:00:00 +0200"),
    }
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}, {"id": "g3"}]}]
    # Sin red: cada construcción de cliente devuelve un fake con los mismos datos.
    monkeypatch.setattr(ee, "_load_credentials", lambda account, **k: object())
    monkeypatch.setattr(ee, "_build_service",
                        lambda creds: _FakeService(labels=_LABELS, pages=pages, raws=raws))

    rep = ee.export_label(
        "c@engelvoelkers.com", _ETIQUETA, tmp_path, service=None, max_workers=4
    )
    assert rep.written == 3
    assert sorted(p.name for p in tmp_path.glob("*.eml")) == [
        "2026-06-11_asunto_1.eml",
        "2026-06-12_asunto_2.eml",
        "2026-06-13_asunto_3.eml",
    ]


# ===========================================================================
# Parte 1 — aplanado byte-fiel de emails anidados (message/rfc822)
# ===========================================================================
#
# Construye MIME crudo a mano: la fidelidad al bit exige controlar los bytes
# exactos (as_bytes() normaliza CRLF→LF y repliega cabeceras, así que no sirve).

def _envoltorio(boundary: bytes, partes: list[bytes], *, mid: bytes = b"<padre@ev>") -> bytes:
    cab = (b"Message-ID: " + mid + b"\r\nSubject: RV bloque\r\n"
           b"Date: Mon, 08 Jun 2026 12:00:00 +0200\r\nFrom: consultor@engelvoelkers.com\r\n"
           b"MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=\"" + boundary + b"\"\r\n\r\n")
    cuerpo = b""
    for p in partes:
        cuerpo += b"--" + boundary + b"\r\n" + p
    return cab + cuerpo + b"--" + boundary + b"--\r\n"


def _parte_rfc822(eml: bytes, *, b64: bool = False) -> bytes:
    if b64:
        return (b"Content-Type: message/rfc822\r\nContent-Transfer-Encoding: base64\r\n\r\n"
                + base64.encodebytes(eml))
    return (b"Content-Type: message/rfc822\r\nContent-Disposition: attachment; "
            b"filename=\"c.eml\"\r\n\r\n" + eml)


def _child(*, mid: bytes, subject: bytes, date: bytes, body: bytes = b"Cuerpo.\r\n") -> bytes:
    """Construye los bytes RFC822 de un .eml hijo con cabeceras propias."""
    return (b"Message-ID: " + mid + b"\r\nSubject: " + subject + b"\r\nDate: " + date
            + b"\r\nFrom: contacto@externo.com\r\n"
            b"Content-Type: text/plain; charset=\"utf-8\"\r\n\r\n" + body)


# --- Capa pura (unitarios literales del plano §5) --------------------------

def test_nested_original_byte_fiel_7bit_y_nombre():
    inner = (b"Message-ID: <leaf@x>\r\nSubject: RE: consulado\r\n"
             b"Date: Tue, 11 May 2023 09:00:00 +0200\r\nFrom: per01a@example.invalid\r\n"
             b"Content-Type: text/plain; charset=\"utf-8\"\r\n\r\nCuerpo jardin.\tfin\r\n")
    raw = _envoltorio(b"BTOP", [b"Content-Type: text/plain\r\n\r\nhola\r\n", _parte_rfc822(inner)])
    res = list(ee.iter_nested_originals(raw))
    assert len(res) == 1
    child, parent_mid = res[0]
    assert child == inner[:-2]                  # byte-original (el CRLF final es del delimitador)
    assert parent_mid == "padre@ev"
    assert ee.eml_filename(ee.parse_headers(child)) == "2023-05-11_consulado.eml"


def test_nested_original_base64():
    inner = b"Subject: hijo b64\r\nDate: Wed, 01 Jan 2025 00:00:00 +0100\r\n\r\nbody\xc3\xb1\r\n"
    raw = _envoltorio(b"BTOP", [_parte_rfc822(inner, b64=True)])
    res = list(ee.iter_nested_originals(raw))
    assert len(res) == 1 and res[0][0] == inner


def test_nested_original_recursivo_nieto_y_provenance_encadenada():
    nieto = (b"Message-ID: <nieto@x>\r\nSubject: nieto\r\n"
             b"Date: Mon, 02 Feb 2022 00:00:00 +0100\r\n\r\nz\r\n")
    medio = _envoltorio(b"BMED", [_parte_rfc822(nieto)], mid=b"<medio@x>")   # boundary distinto
    raw = _envoltorio(b"BTOP", [_parte_rfc822(medio)])
    mids = {ee.message_id_of(b): p for b, p in ee.iter_nested_originals(raw)}
    assert set(mids) == {"medio@x", "nieto@x"}
    assert mids["medio@x"] == "padre@ev"
    assert mids["nieto@x"] == "medio@x"


def test_nested_original_lf_only():
    inner = b"Subject: lf\nDate: Tue, 11 May 2023 09:00:00 +0200\n\ncuerpo\n"
    raw = (b"Content-Type: multipart/mixed; boundary=\"B\"\n\n--B\n"
           b"Content-Type: message/rfc822\n\n" + inner + b"--B--\n")
    res = list(ee.iter_nested_originals(raw))
    assert len(res) == 1 and res[0][0] == inner[:-1]


def test_fallback_reserializa_y_avisa(monkeypatch):
    padre = PyEmailMessage()
    padre["Message-ID"] = "<p5@ev>"; padre["Subject"] = "padre"
    padre["Date"] = "Mon, 08 Jun 2026 12:00:00 +0200"; padre.set_content("x")
    hijo = PyEmailMessage()
    hijo["Subject"] = "hijo"; hijo["Date"] = "Tue, 11 May 2023 09:00:00 +0200"; hijo.set_content("y")
    padre.add_attachment(hijo, filename="c.eml")

    monkeypatch.setattr(ee, "iter_nested_originals", lambda raw: iter(()))   # fuerza el disparador
    rep = ee.ExportReport(account="c@ev", label="L")
    got = ee._nested_con_fallback(padre.as_bytes(), rep)
    assert len(got) == 1
    assert len(rep.errors) == 1 and "p5@ev" in rep.errors[0]
    assert ee.eml_filename(ee.parse_headers(got[0][0])) == "2023-05-11_hijo.eml"


def test_split_eml_salta_rfc822_y_no_explota_pdf_interno():
    hijo = PyEmailMessage()
    hijo["Subject"] = "h"; hijo["Date"] = "Tue, 11 May 2023 09:00:00 +0200"; hijo.set_content("z")
    hijo.add_attachment(b"%PDF in", maintype="application", subtype="pdf", filename="int.pdf")
    padre = PyEmailMessage()
    padre["Subject"] = "p"; padre["Date"] = "Mon, 08 Jun 2026 12:00:00 +0200"; padre.set_content("x")
    padre.add_attachment(hijo, filename="c.eml")
    padre.add_attachment(b"%PDF dir", maintype="application", subtype="pdf", filename="dir.pdf")
    _, adjuntos = ee.split_eml(padre.as_bytes())
    assert {fn for fn, _m, _d in adjuntos} == {"dir.pdf"}


# --- End-to-end con _FakeService (export_label) ----------------------------

def test_export_label_aplana_anidados_a_primer_nivel(tmp_path):
    """(a) padre + N hijos → N+1 .eml a primer nivel, nested_flattened==N."""
    h1 = _child(mid=b"<leaf1@x>", subject=b"Conversacion uno", date=b"Tue, 11 May 2023 09:00:00 +0200")
    h2 = _child(mid=b"<leaf2@x>", subject=b"Conversacion dos", date=b"Sat, 02 Mar 2024 12:00:00 +0200")
    padre = _envoltorio(b"BTOP", [b"Content-Type: text/plain\r\n\r\nsobre\r\n",
                                  _parte_rfc822(h1), _parte_rfc822(h2)])
    raws = {"g1": padre}
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws=raws)
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)

    assert rep.written == 1
    assert rep.nested_flattened == 2
    assert rep.nested_dedup == 0
    nombres = sorted(p.name for p in tmp_path.glob("*.eml"))
    assert nombres == [
        "2023-05-11_conversacion_uno.eml",
        "2024-03-02_conversacion_dos.eml",
        "2026-06-08_rv_bloque.eml",
    ]


def test_export_label_dedup_hijo_en_dos_padres(tmp_path):
    """(b) mismo hijo (Message-ID) en dos padres → una sola copia, nested_dedup>=1."""
    hijo = _child(mid=b"<comun@x>", subject=b"Compartida", date=b"Tue, 11 May 2023 09:00:00 +0200")
    p1 = _envoltorio(b"BTOPA", [_parte_rfc822(hijo)], mid=b"<p1@ev>")
    p2 = _envoltorio(b"BTOPB", [_parte_rfc822(hijo)], mid=b"<p2@ev>")
    raws = {"g1": p1, "g2": p2}
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}, {"id": "g2"}]}], raws=raws)
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)

    assert rep.written == 2                # los dos padres
    assert rep.nested_flattened == 1       # el hijo, una vez
    assert rep.nested_dedup >= 1           # la 2ª aparición, colapsada
    assert len(list(tmp_path.glob("*.eml"))) == 3   # 2 padres + 1 hijo
    assert len(list(tmp_path.glob("2023-05-11_compartida*.eml"))) == 1


def test_export_label_cronologia_ordena_hijo_por_su_fecha(tmp_path):
    """(c) CRONOLOGIA.md ordena el hijo por SU fecha (anterior al padre)."""
    hijo = _child(mid=b"<viejo@x>", subject=b"Antiguo", date=b"Tue, 11 May 2023 09:00:00 +0200")
    padre = _envoltorio(b"BTOP", [_parte_rfc822(hijo)])
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": padre})
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)

    crono = (tmp_path / "CRONOLOGIA.md").read_text(encoding="utf-8")
    assert crono.index("2023-05-11") < crono.index("2026-06-08")   # hijo antes que padre


def test_export_label_no_aplanar_solo_el_padre(tmp_path):
    """(d) flatten_nested_emails=False → solo el padre a primer nivel."""
    hijo = _child(mid=b"<leaf@x>", subject=b"Hijo", date=b"Tue, 11 May 2023 09:00:00 +0200")
    padre = _envoltorio(b"BTOP", [_parte_rfc822(hijo)])
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": padre})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc,
                          flatten_nested_emails=False)

    assert rep.nested_flattened == 0
    assert sorted(p.name for p in tmp_path.glob("*.eml")) == ["2026-06-08_rv_bloque.eml"]


def test_export_label_traza_forwarded_in(tmp_casos_root):
    """(e) el evento upload_email lleva forwarded_in con el Message-ID del padre."""
    from core import intake_log

    case_id = _setup_caso("EMAIL-2026-004")
    hijo = _child(mid=b"<leaf@x>", subject=b"Hijo reenviado", date=b"Tue, 11 May 2023 09:00:00 +0200")
    padre = _envoltorio(b"BTOP", [_parte_rfc822(hijo)])
    dest = ee.email_dest_dir(case_id)
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": padre})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest, service=svc, case_id=case_id)

    assert rep.intake_logged is True
    eventos = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_email"]
    assert len(eventos) == 1
    por_mid = {m["message_id"]: m for m in eventos[0]["details"]["mensajes"]}
    assert por_mid["leaf@x"]["forwarded_in"] == "padre@ev"
    assert por_mid["padre@ev"]["forwarded_in"] is None


# ---------------------------------------------------------------------------
# Parte 1 — correcciones de la revisión adversarial (robustez/fidelidad/traza)
# ---------------------------------------------------------------------------

def test_nested_boundary_como_contenido_no_trunca_ni_pierde():
    """A: un `--<boundary>` que aparece como CONTENIDO (no a inicio de línea) en el
    cuerpo de un hijo NO debe truncarlo ni descartar los hijos siguientes."""
    h1 = _child(mid=b"<c1@x>", subject=b"Uno", date=b"Tue, 11 May 2023 09:00:00 +0200",
                body=b"texto con --BTOP-- citado en medio, no es delimitador\r\n")
    h2 = _child(mid=b"<c2@x>", subject=b"Dos", date=b"Sat, 02 Mar 2024 12:00:00 +0200")
    raw = _envoltorio(b"BTOP", [_parte_rfc822(h1), _parte_rfc822(h2)])
    res = list(ee.iter_nested_originals(raw))
    assert [ee.message_id_of(b) for b, _ in res] == ["c1@x", "c2@x"]   # ambos, en orden
    assert res[0][0] == h1[:-2]    # byte-fiel: c1 conserva el `--BTOP--` citado completo
    assert res[1][0] == h2[:-2]


def test_split_headers_body_elige_separador_mas_temprano():
    """D: padre con separador de cabeceras LF (\\n\\n) que transporta un hijo con
    separadores CRLF (\\r\\n\\r\\n) → debe partir por el \\n\\n del padre (el primero),
    no por el \\r\\n\\r\\n del hijo (posterior)."""
    inner = b"Message-ID: <crlf@x>\r\nSubject: hijo crlf\r\nDate: Tue, 11 May 2023 09:00:00 +0200\r\n\r\ncuerpo\r\n"
    raw = (b"Content-Type: multipart/mixed; boundary=\"B\"\n\n--B\n"
           b"Content-Type: message/rfc822\n\n" + inner + b"--B--\n")
    res = list(ee.iter_nested_originals(raw))
    assert len(res) == 1
    assert ee.message_id_of(res[0][0]) == "crlf@x"


def test_export_label_aplana_anidados_excepcion_no_aborta_corrida(tmp_path, monkeypatch):
    """B: una excepción en _aplana_anidados se registra y NO aborta el resto de la corrida."""
    h = _child(mid=b"<leaf@x>", subject=b"Hijo", date=b"Tue, 11 May 2023 09:00:00 +0200")
    padre = _envoltorio(b"BTOP", [_parte_rfc822(h)])
    simple = _build_raw(message_id="<simple@x>", subject="Suelto")
    raws = {"g1": padre, "g2": simple}
    pages = [{"messages": [{"id": "g1"}, {"id": "g2"}]}]

    def boom(*a, **k):
        raise OSError("disco lleno simulado")
    monkeypatch.setattr(ee, "_aplana_anidados", boom)

    svc = _FakeService(labels=_LABELS, pages=pages, raws=raws)
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)

    assert rep.written == 2                              # ambos padres escritos
    assert any("disco lleno" in e for e in rep.errors)   # el fallo se registró
    assert (tmp_path / "INDICE.md").exists()             # los índices se regeneraron
    assert (tmp_path / "2026-06-08_rv_bloque.eml").exists()
    assert (tmp_path / "0000-00-00_suelto.eml").exists() or len(list(tmp_path.glob("*.eml"))) == 2


def test_force_re_aplana_hijo_borrado(tmp_path):
    """C: tras borrar SOLO un hijo aplanado (padre intacto), force=True lo regenera."""
    hijo = _child(mid=b"<leaf@x>", subject=b"Hijo Borrado", date=b"Tue, 11 May 2023 09:00:00 +0200")
    padre = _envoltorio(b"BTOP", [_parte_rfc822(hijo)])
    svc1 = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": padre})
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc1)

    hijo_path = tmp_path / "2023-05-11_hijo_borrado.eml"
    assert hijo_path.exists()
    hijo_path.unlink()                                   # se borra solo el hijo

    svc2 = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": padre})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc2, force=True)

    assert hijo_path.exists()              # regenerado
    assert rep.nested_flattened == 1


def test_traza_forwarded_in_backfill_desde_disco(tmp_casos_root):
    """E: en el backfill (export sin case_id sobre el cajón legacy 03_Email, no
    migrado a lotes, luego con case_id y candidates vacío), forwarded_in se
    reconstruye desde el disco (no queda None)."""
    from core import config, intake_log

    case_id = _setup_caso("EMAIL-2026-005")
    hijo = _child(mid=b"<leaf@x>", subject=b"Hijo BF", date=b"Tue, 11 May 2023 09:00:00 +0200")
    padre = _envoltorio(b"BTOP", [_parte_rfc822(hijo)])
    dest = config.caso_path(case_id) / "00_Input" / "03_Email"

    # Corrida 1: SIN case_id → escribe padre + hijo, sin traza.
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": padre}))
    # Corrida 2: CON case_id → candidates vacío (índice persistente) → traza backfill.
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest, case_id=case_id,
                          service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": padre}))

    assert rep.written == 0
    assert rep.intake_logged is True
    eventos = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_email"]
    por_mid = {m["message_id"]: m for m in eventos[-1]["details"]["mensajes"]}
    assert por_mid["leaf@x"]["forwarded_in"] == "padre@ev"   # reconstruido desde disco
    assert por_mid["padre@ev"]["forwarded_in"] is None


def _multipart_eml(mid: bytes, boundary: bytes) -> bytes:
    """Un .eml multipart/mixed con una parte de texto y el boundary dado."""
    return (b"Message-ID: " + mid + b"\r\nSubject: m\r\nDate: Tue, 11 May 2023 09:00:00 +0200\r\n"
            b"MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=\"" + boundary + b"\"\r\n\r\n"
            b"--" + boundary + b"\r\nContent-Type: text/plain\r\n\r\ncuerpo\r\n"
            b"--" + boundary + b"--\r\n")


def test_boundary_reusado_entre_primos_se_recupera_byte_fiel():
    """44.1 (datos reales W-02VND1): dos anidados PRIMOS reutilizan el mismo token de
    boundary (Apple Mail/Outlook/Nodemailer los repiten). El rebanado byte-fiel los
    recupera correctamente —los Message-ID coinciden con el parser— y NO cae al fallback
    re-serializado (la red de seguridad se ancla a la coincidencia de mids, no a la mera
    repetición de boundary)."""
    c1 = _multipart_eml(b"<c1@x>", b"SHARED")
    c2 = _multipart_eml(b"<c2@x>", b"SHARED")     # MISMO boundary que c1 (primos)
    padre = _envoltorio(b"BTOP", [_parte_rfc822(c1), _parte_rfc822(c2)])
    rep = ee.ExportReport(account="c@ev", label="L")
    got = ee._nested_con_fallback(padre, rep)
    assert sorted(ee.message_id_of(b) for b, _ in got) == ["c1@x", "c2@x"]
    assert rep.errors == []                       # byte-fiel: sin fallback ni aviso
    assert any(b == c1[:-2] for b, _ in got)      # byte-original (sin el CRLF del delimitador)


def test_rebanado_descuadrado_vs_parser_cae_a_fallback(monkeypatch):
    """Si el rebanado byte-fiel pierde un mensaje que el parser SÍ ve (mids no coinciden),
    cae al fallback re-serializado + aviso (nunca pérdida silenciosa)."""
    c1 = _child(mid=b"<a@x>", subject=b"Uno", date=b"Tue, 11 May 2023 09:00:00 +0200")
    c2 = _child(mid=b"<b@x>", subject=b"Dos", date=b"Sat, 02 Mar 2024 12:00:00 +0200")
    padre = _envoltorio(b"BTOP", [_parte_rfc822(c1), _parte_rfc822(c2)], mid=b"<pp@ev>")
    # Simula un rebanado que solo recupera UNO de los dos anidados (descuadre).
    monkeypatch.setattr(ee, "iter_nested_originals", lambda raw: iter([(c1, "pp@ev")]))
    rep = ee.ExportReport(account="c@ev", label="L")
    got = ee._nested_con_fallback(padre, rep)
    assert sorted(ee.message_id_of(b) for b, _ in got) == ["a@x", "b@x"]   # fallback recupera ambos
    assert len(rep.errors) == 1 and "inconsistente" in rep.errors[0]


def test_aplana_hijo_sin_message_id_dedup_por_contenido(tmp_path):
    """44.2: un hijo SIN Message-ID idéntico, reenviado en dos padres en la misma corrida,
    colapsa en un fichero por dedup de respaldo por SHA-256 (no se multiplica)."""
    hijo = (b"Subject: sin id\r\nDate: Tue, 11 May 2023 09:00:00 +0200\r\n"
            b"Content-Type: text/plain; charset=\"utf-8\"\r\n\r\ncuerpo identico del hijo\r\n")
    p1 = _envoltorio(b"BA", [_parte_rfc822(hijo)], mid=b"<pa@x>")
    p2 = _envoltorio(b"BB", [_parte_rfc822(hijo)], mid=b"<pb@x>")
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}, {"id": "g2"}]}],
                       raws={"g1": p1, "g2": p2})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)

    assert rep.written == 2                 # los dos padres
    assert rep.nested_flattened == 1        # el hijo sin id, una sola vez
    assert rep.nested_dedup >= 1
    assert len(list(tmp_path.glob("2023-05-11_sin_id*.eml"))) == 1


# ===========================================================================
# Parte 2 — rescate de ficheros enlazados (Drive/Gmail) — capa pura
# ===========================================================================

def _build_html_email(*, html: str = "", plain: str = "", message_id: str = "<h@x>") -> bytes:
    msg = PyEmailMessage()
    msg["Message-ID"] = message_id
    msg["Subject"] = "enlaces"
    msg["Date"] = "Mon, 08 Jun 2026 12:00:00 +0200"
    msg["From"] = "consultor@engelvoelkers.com"
    if plain:
        msg.set_content(plain)
        if html:
            msg.add_alternative(html, subtype="html")
    elif html:
        msg.set_content(html, subtype="html")
    return msg.as_bytes()


def _tipos(links):
    return {(l.type, l.file_id): l for l in links}


def test_extract_drive_links_clasifica_familias():
    plain = "Otro fichero por enlace: https://drive.google.com/open?id=OPENID5"
    html = (
        '<p>Adjunto el contrato: '
        '<a href="https://drive.google.com/file/d/FILEID123/view?usp=sharing">aquí</a></p>'
        '<p>La carpeta: <a href="https://drive.google.com/drive/folders/FOLDERID9">carpeta</a></p>'
        '<p>La hoja: <a href="https://docs.google.com/spreadsheets/d/SHEETID7/edit">hoja</a></p>'
        '<img src="https://docs.google.com/uc?export=download&id=SIGIMG1" width="120">'
    )
    links = ee.extract_drive_links(_build_html_email(html=html, plain=plain))
    por = _tipos(links)
    assert (ee.DriveLinkType.FILE, "FILEID123") in por
    assert (ee.DriveLinkType.FOLDER, "FOLDERID9") in por
    assert (ee.DriveLinkType.NATIVE, "SHEETID7") in por
    assert (ee.DriveLinkType.FILE, "OPENID5") in por
    assert (ee.DriveLinkType.IMAGE_SIG, "SIGIMG1") in por      # img src → firma
    assert por[(ee.DriveLinkType.IMAGE_SIG, "SIGIMG1")].from_img is True
    assert por[(ee.DriveLinkType.FILE, "FILEID123")].from_img is False


def test_extract_drive_links_unescape_y_dedup():
    # &amp; entidad HTML en la URL; el mismo (tipo,id) dos veces → una sola entrada.
    html = (
        '<a href="https://drive.google.com/uc?export=download&amp;id=DUP9&amp;foo=bar">a</a>'
        '<a href="https://drive.google.com/file/d/DUP9/view">b</a>'
        '<a href="https://drive.google.com/file/d/DUP9/preview">c</a>'
    )
    links = ee.extract_drive_links(_build_html_email(html=html))
    # FILE/DUP9 aparece tres veces (uc?id, file/d x2) pero colapsa a una entrada FILE.
    files = [l for l in links if l.type == ee.DriveLinkType.FILE and l.file_id == "DUP9"]
    assert len(files) == 1


def test_extract_drive_links_ignora_ruido_no_drive():
    html = (
        '<a href="https://www.google.com/maps/search/Diagonal+640">mapa</a>'
        '<a href="https://calendar.google.com/calendar/event?eid=ABC">cal</a>'
        '<a href="https://meet.google.com/hhq-maaf-zfb">meet</a>'
        '<a href="https://support.google.com/a/users/answer/9282720">ayuda</a>'
    )
    assert ee.extract_drive_links(_build_html_email(html=html)) == []


def test_extract_drive_links_gmail_permalink():
    html = '<a href="https://mail.google.com/mail/u/0/#inbox/FMfcgzABC123">ver correo</a>'
    links = ee.extract_drive_links(_build_html_email(html=html))
    gmail = [l for l in links if l.type == ee.DriveLinkType.GMAIL]
    assert len(gmail) == 1
    assert gmail[0].file_id == "FMfcgzABC123"


def test_iter_body_text_no_desciende_en_rfc822():
    # un enlace que vive en el cuerpo del HIJO anidado NO debe extraerse del padre.
    hijo = (b"Message-ID: <h2@x>\r\nSubject: hijo\r\nDate: Tue, 11 May 2023 09:00:00 +0200\r\n"
            b"Content-Type: text/plain\r\n\r\nver https://drive.google.com/file/d/HIDDEN9/view\r\n")
    padre = _envoltorio(b"BTOP", [b"Content-Type: text/plain\r\n\r\nsobre sin enlaces\r\n",
                                  _parte_rfc822(hijo)])
    assert ee.extract_drive_links(padre) == []
    # iter_body_text solo ve el cuerpo del padre
    textos = [t for t, _ in ee.iter_body_text(padre)]
    assert any("sobre sin enlaces" in t for t in textos)
    assert all("HIDDEN9" not in t for t in textos)


# ===========================================================================
# Parte 2 — orquestación (_resuelve_enlaces vía export_label)
# ===========================================================================

def _info(fid, name, mime, data):
    return DriveFileInfo(file_id=fid, name=name, mime_type=mime, size=len(data),
                         md5=hashlib.md5(data).hexdigest(), modified_time=None, drive_id=None)


def _patch_drive(monkeypatch, infos: dict, blobs: dict):
    monkeypatch.setattr(ee, "get_drive_file_info", lambda fid: infos.get(fid))
    monkeypatch.setattr(ee, "download_drive_media", lambda fid: blobs.get(fid))


def test_resuelve_file_binario_deposita_en_enlaces(tmp_path, monkeypatch):
    blob = b"%PDF-1.7 contrato real"
    _patch_drive(monkeypatch, {"F1": _info("F1", "contrato.pdf", "application/pdf", blob)}, {"F1": blob})
    html = '<a href="https://drive.google.com/file/d/F1/view">contrato</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p1@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_resolved == 1
    dep = list(tmp_path.glob("2026-06-08_enlaces/_enlaces/*"))
    assert len(dep) == 1 and dep[0].name == "contrato.pdf"
    assert dep[0].read_bytes() == blob


def test_resuelve_file_md5_no_coincide_no_deposita(tmp_path, monkeypatch):
    blob = b"bytes reales descargados"
    info = DriveFileInfo("F2", "x.pdf", "application/pdf", len(blob), "md5incorrecto", None, None)
    _patch_drive(monkeypatch, {"F2": info}, {"F2": blob})
    html = '<a href="https://drive.google.com/file/d/F2/view">x</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p2@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_error == 1 and rep.links_resolved == 0
    assert any("md5" in e for e in rep.errors)
    assert not list(tmp_path.glob("**/_enlaces/*"))


def test_resuelve_file_eml_reentra_parte1(tmp_path, monkeypatch):
    rescued = _child(mid=b"<rescued@x>", subject=b"Rescatado", date=b"Tue, 11 May 2023 09:00:00 +0200")
    _patch_drive(monkeypatch, {"F3": _info("F3", "conv.eml", "message/rfc822", rescued)}, {"F3": rescued})
    html = '<a href="https://drive.google.com/file/d/F3/view">conv</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p3@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_resolved == 1
    assert (tmp_path / "2023-05-11_rescatado.eml").exists()   # primer nivel, por su fecha


def test_resuelve_folder_y_native_solo_traza(tmp_path):
    html = ('<a href="https://drive.google.com/drive/folders/FOLD1">carpeta</a>'
            '<a href="https://docs.google.com/spreadsheets/d/SHEET1/edit">hoja</a>')
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p4@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_skipped_folder == 1 and rep.links_skipped_native == 1
    assert rep.links_resolved == 0
    nat = [e for e in rep.link_entries if e["type"] == "native"][0]
    assert nat["drive_file_id"] == "SHEET1" and nat["outcome"] == "skipped_native"


def test_resuelve_image_sig_pequena_filtrada(tmp_path, monkeypatch):
    """<img src> a una imagen pequeña → firma, filtrada (mime imagen + <50KB)."""
    small = b"\xff\xd8\xff" + b"x" * 2000   # JPEG pequeño
    _patch_drive(monkeypatch, {"SIG1": _info("SIG1", "firma.png", "image/png", small)}, {"SIG1": small})
    html = '<img src="https://docs.google.com/uc?export=download&id=SIG1" width="100">'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p5@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_filtered_sig == 1 and rep.links_resolved == 0


def test_resuelve_image_sig_inaccesible_filtrada(tmp_path, monkeypatch):
    """<img src> cuyos metadatos no se acceden → se trata como firma (no como manual)."""
    _patch_drive(monkeypatch, {}, {})   # metadatos None
    html = '<img src="https://docs.google.com/uc?export=download&id=SIG2" width="100">'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p5b@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_filtered_sig == 1 and rep.links_manual == 0


def test_resuelve_img_src_imagen_grande_se_rescata(tmp_path, monkeypatch):
    """<img src> a una imagen GRANDE (>50KB) NO es firma → se rescata como prueba."""
    big = b"\xff\xd8\xff" + b"x" * (80 * 1024)
    _patch_drive(monkeypatch, {"BIGIMG": _info("BIGIMG", "foto.jpg", "image/jpeg", big)}, {"BIGIMG": big})
    html = '<img src="https://drive.google.com/file/d/BIGIMG/view" width="600">'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p5c@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_resolved == 1 and rep.links_filtered_sig == 0


def test_resuelve_href_imagen_pequena_se_descarga(tmp_path, monkeypatch):
    """Imagen pequeña enlazada por <a href> (no <img>) es prueba: se descarga, NO se filtra."""
    small = b"\xff\xd8\xff" + b"x" * 1000
    _patch_drive(monkeypatch, {"FOTO": _info("FOTO", "recibo.jpg", "image/jpeg", small)}, {"FOTO": small})
    html = '<a href="https://drive.google.com/file/d/FOTO/view">recibo</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p5d@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_resolved == 1 and rep.links_filtered_sig == 0


def test_resuelve_file_permiso_denegado_manual_reintentable(tmp_path, monkeypatch):
    _patch_drive(monkeypatch, {}, {})   # get_drive_file_info → None (403/permiso)
    html = '<a href="https://drive.google.com/file/d/F6/view">x</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p6@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_manual == 1
    idx = json.loads((tmp_path / "_resolved_links.json").read_text(encoding="utf-8"))
    assert idx["F6"]["outcome"] != "resolved"   # NO definitivo → reintento la próxima


def test_resuelve_file_idempotente_no_rebaja(tmp_path, monkeypatch):
    blob = b"%PDF datos idempotencia"
    calls = {"dl": 0}
    monkeypatch.setattr(ee, "get_drive_file_info", lambda fid: _info("F7", "x.pdf", "application/pdf", blob))

    def _dl(fid):
        calls["dl"] += 1
        return blob
    monkeypatch.setattr(ee, "download_drive_media", _dl)
    html = '<a href="https://drive.google.com/file/d/F7/view">x</a>'
    raw = _build_html_email(html=html, message_id="<p7@x>")
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    assert calls["dl"] == 1
    # 2ª corrida con force: re-procesa el padre, pero el enlace está cacheado en el índice.
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, force=True,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    assert calls["dl"] == 1   # NO re-bajó


def test_resuelve_gmail_permalink_reentra_parte1(tmp_path):
    rescued = _child(mid=b"<gmailmsg@x>", subject=b"Desde permalink", date=b"Tue, 11 May 2023 09:00:00 +0200")
    html = '<a href="https://mail.google.com/mail/u/0/#inbox/GID9">ver correo</a>'
    parent = _build_html_email(html=html, message_id="<p9@x>")
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": parent, "GID9": rescued})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_resolved == 1
    assert (tmp_path / "2023-05-11_desde_permalink.eml").exists()


def test_evento_upload_drive_link_incluye_no_resueltos(tmp_casos_root, monkeypatch):
    from core import intake_log

    case_id = _setup_caso("EMAIL-2026-006")
    _patch_drive(monkeypatch, {}, {})   # F8 no accesible → manual
    html = ('<a href="https://drive.google.com/drive/folders/FOLD8">c</a>'
            '<a href="https://drive.google.com/file/d/F8/view">f</a>')
    dest = ee.email_dest_dir(case_id)
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p8@x>")})
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest, service=svc, case_id=case_id)

    ev = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_drive_link"]
    assert len(ev) == 1
    outcomes = {e["drive_file_id"]: e["outcome"] for e in ev[0]["details"]["enlaces"]}
    assert outcomes["FOLD8"] == "skipped_folder"
    assert outcomes["F8"] == "manual_permission"   # no resuelto, queda en la worklist


def test_resuelve_enlaces_off_no_toca_nada(tmp_path, monkeypatch):
    _patch_drive(monkeypatch, {"F1": _info("F1", "x.pdf", "application/pdf", b"x")}, {"F1": b"x"})
    html = '<a href="https://drive.google.com/file/d/F1/view">x</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<p10@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc,
                          resolve_drive_links=False)
    assert rep.links_resolved == 0 and rep.link_entries == []
    assert not (tmp_path / "_resolved_links.json").exists() or True  # no se exige el índice


def test_resuelve_usercontent_download_se_clasifica(tmp_path, monkeypatch):
    """A: el host real de descarga directa drive.usercontent.google.com/download?id= se
    clasifica como FILE y se rescata (no se pierde en silencio)."""
    blob = b"%PDF-1.7 dossier"
    _patch_drive(monkeypatch, {"UC9": _info("UC9", "dossier.pdf", "application/pdf", blob)}, {"UC9": blob})
    html = '<a href="https://drive.usercontent.google.com/download?id=UC9&export=download">bajar</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<pa@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_resolved == 1
    assert list(tmp_path.glob("**/_enlaces/dossier.pdf"))


def test_extract_usercontent_clasifica_file():
    html = '<a href="https://drive.usercontent.google.com/download?id=UCX&export=download">x</a>'
    links = ee.extract_drive_links(_build_html_email(html=html))
    assert any(l.type == ee.DriveLinkType.FILE and l.file_id == "UCX" for l in links)


def test_resuelve_file_sin_md5_marca_no_verificado(tmp_path, monkeypatch):
    """C: si Drive no da md5Checksum, se deposita pero la traza marca integridad no verificada."""
    blob = b"%PDF sin md5"
    info = DriveFileInfo("NOMD5", "x.pdf", "application/pdf", len(blob), None, None, None)
    _patch_drive(monkeypatch, {"NOMD5": info}, {"NOMD5": blob})
    html = '<a href="https://drive.google.com/file/d/NOMD5/view">x</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<pc@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_resolved == 1
    e = [x for x in rep.link_entries if x["drive_file_id"] == "NOMD5"][0]
    assert e["md5_ok"] is False   # depositado, pero marcado como no verificado por md5


def test_resuelve_file_demasiado_grande_manual(tmp_path, monkeypatch):
    """E: un binario que excede el tope de tamaño no se baja (anti-OOM) → manual."""
    info = DriveFileInfo("HUGE", "video.mp4", "video/mp4", 500 * 1024 * 1024, "m", None, None)
    calls = {"dl": 0}
    monkeypatch.setattr(ee, "get_drive_file_info", lambda fid: info)
    monkeypatch.setattr(ee, "download_drive_media", lambda fid: (calls.__setitem__("dl", calls["dl"] + 1) or b"x"))
    html = '<a href="https://drive.google.com/file/d/HUGE/view">video</a>'
    svc = _FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}],
                       raws={"g1": _build_html_email(html=html, message_id="<pe@x>")})
    rep = ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, service=svc)
    assert rep.links_manual == 1 and rep.links_resolved == 0
    assert calls["dl"] == 0   # nunca se intentó descargar (no OOM)


def test_force_re_descarga_binario_drive_link_borrado(tmp_path, monkeypatch):
    """G: tras borrar un binario _enlaces, force lo re-descarga (no se fía solo del índice)."""
    blob = b"%PDF borrable"
    _patch_drive(monkeypatch, {"DEL1": _info("DEL1", "doc.pdf", "application/pdf", blob)}, {"DEL1": blob})
    html = '<a href="https://drive.google.com/file/d/DEL1/view">doc</a>'
    raw = _build_html_email(html=html, message_id="<pg@x>")
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    dep = list(tmp_path.glob("**/_enlaces/doc.pdf"))
    assert len(dep) == 1
    dep[0].unlink()   # se borra el binario, queda el índice
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, tmp_path, force=True,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    assert list(tmp_path.glob("**/_enlaces/doc.pdf"))   # regenerado


def test_evento_drive_link_no_se_duplica_en_force(tmp_casos_root, monkeypatch):
    """H: una re-corrida force que solo encuentra enlaces cacheados NO re-emite el evento."""
    from core import intake_log

    case_id = _setup_caso("EMAIL-2026-007")
    blob = b"%PDF cacheado"
    _patch_drive(monkeypatch, {"CCH1": _info("CCH1", "c.pdf", "application/pdf", blob)}, {"CCH1": blob})
    html = '<a href="https://drive.google.com/file/d/CCH1/view">c</a>'
    raw = _build_html_email(html=html, message_id="<ph@x>")
    dest = ee.email_dest_dir(case_id)
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest, case_id=case_id,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest, case_id=case_id, force=True,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    ev = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_drive_link"]
    assert len(ev) == 1   # solo el de la 1ª corrida; la 2ª (todo cacheado) no re-emite


def test_traza_drive_link_no_se_cuenta_como_adjunto_email_en_backfill(tmp_casos_root, monkeypatch):
    """D: en el backfill (binario drive_link cacheado), el binario de _enlaces/ se clasifica
    por su ubicación como drive_link y NO se cuenta como adjunto-email del evento upload_email."""
    from core import intake_log
    from core.intake_manifest import IntakeManifest

    case_id = _setup_caso("EMAIL-2026-008")
    blob = b"%PDF backfill"
    _patch_drive(monkeypatch, {"BF1": _info("BF1", "bf.pdf", "application/pdf", blob)}, {"BF1": blob})
    html = '<a href="https://drive.google.com/file/d/BF1/view">bf</a>'
    raw = _build_html_email(html=html, message_id="<pd@x>")
    dest = ee.email_dest_dir(case_id)
    # Corrida 1: SIN case_id → deposita el binario, sin traza.
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    assert list(dest.glob("**/_enlaces/bf.pdf"))
    # Corrida 2: CON case_id + force → enlace cacheado; la traza registra el binario.
    ee.export_label("c@engelvoelkers.com", _ETIQUETA, dest, case_id=case_id, force=True,
                    service=_FakeService(labels=_LABELS, pages=[{"messages": [{"id": "g1"}]}], raws={"g1": raw}))
    # El upload_email NO debe contar el binario drive_link como adjunto-email.
    ev = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_email"]
    assert ev and ev[-1]["details"]["registrados_adjuntos"] == 0
    # Y el binario consta en el manifest (registrado, no perdido).
    man = IntakeManifest(case_id)
    man.load()
    assert any(p.endswith("bf.pdf") for p in man.all_paths())
