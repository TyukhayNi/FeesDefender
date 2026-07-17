"""Tests M9 — ``message_id`` opcional + ``duplicado_de_para`` (Task 4, MEJORAS #54).

Extiende el manifest de dedup cross-source (``core/intake_manifest.py``) con
un ``message_id`` por entry, lookup por Message-ID y el helper de anotación
``duplicado_de_para`` usado por los writers de lote (whatsapp/manual/email)
para poblar ``duplicado_de`` en el manifiesto de lote (spec §6). Un duplicado
detectado se COPIA igual: esto solo anota.
"""
from __future__ import annotations


class TestMessageIdM9:
    def test_register_persiste_message_id(self, tmp_casos_root):
        from core import case_manager
        from core.intake_manifest import IntakeManifest
        case_manager.ensure_case("EV-M9-001", titulo="m9")
        with IntakeManifest("EV-M9-001") as m:
            m.register("sha-1", "2026-07-17_email_01/a.eml",
                       source="email", message_id="<uno@x>")
        with IntakeManifest("EV-M9-001") as m:   # round-trip por disco
            assert m.lookup("sha-1")["message_id"] == "<uno@x>"
            assert m.message_ids() == {"<uno@x>"}
            sha, entry = m.lookup_message_id("<uno@x>")
            assert sha == "sha-1"
            assert entry["primary_path"] == "2026-07-17_email_01/a.eml"

    def test_duplicado_de_para_sha_y_message_id(self, tmp_casos_root):
        from core import case_manager
        from core.intake_manifest import IntakeManifest
        case_manager.ensure_case("EV-M9-002", titulo="m9")
        with IntakeManifest("EV-M9-002") as m:
            m.register("sha-1", "2026-07-17_email_01/a.eml",
                       source="email", message_id="<uno@x>")
            # sha idéntico → duplicado por sha
            assert m.duplicado_de_para("sha-1", 10) == "2026-07-17_email_01/a.eml"
            # mismo correo, bytes distintos (sha nuevo) → duplicado por Message-ID (§6)
            assert m.duplicado_de_para("sha-2", 10, message_id="<uno@x>") \
                == "2026-07-17_email_01/a.eml"
            # sha y mid desconocidos → no es duplicado
            assert m.duplicado_de_para("sha-3", 10, message_id="<otro@x>") is None

    def test_tamano_cero_nunca_marca_duplicado(self, tmp_casos_root):
        from core import case_manager
        from core.intake_manifest import IntakeManifest
        case_manager.ensure_case("EV-M9-003", titulo="m9")
        with IntakeManifest("EV-M9-003") as m:
            m.register("sha-vacio", "2026-07-17_manual_01/vacio.txt", source="manual")
            assert m.duplicado_de_para("sha-vacio", 0) is None
