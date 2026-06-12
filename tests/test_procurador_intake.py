"""Tests para core.procurador_intake — F1 Matcher (solo lectura)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.procurador_intake import (
    AttachmentProposal,
    IntakeSignals,
    MatchResult,
    _check_signal_matches,
    _extract_extension,
    _looks_like_logo,
    _parse_su_ref,
    abreviar_tipo,
    extract_signals,
    is_procurador_email,
    match_expediente,
    normalize_descripcion,
    propose_attachment_name,
    sanitize_filename,
)
from core.sync_sudespacho import SudespachoClient


# ---------------------------------------------------------------------------
# is_procurador_email
# ---------------------------------------------------------------------------

class TestIsProcuradorEmail:
    def test_known_domain(self):
        assert is_procurador_email("ana@procuradores-a.example")

    def test_known_domain_uppercase(self):
        assert is_procurador_email("ANA@AMSPROCURADOR.COM")

    def test_known_email(self):
        assert is_procurador_email("proc-a@example.invalid")

    def test_angle_brackets(self):
        assert is_procurador_email("ProcuradoraA <proc-a@example.invalid>")

    def test_unknown(self):
        assert not is_procurador_email("random@gmail.com")

    def test_castaneda(self):
        assert is_procurador_email("info@procuradores-b.example")

    def test_pilar(self):
        assert is_procurador_email("proc-f@colegio-proc.example")

    def test_viudez(self):
        assert is_procurador_email("eva@procuradores-d.example")

    def test_varon(self):
        assert is_procurador_email("oficina@procuradores-e.example")

    def test_campuzano(self):
        assert is_procurador_email("despacho@procuradores-c.example")


# ---------------------------------------------------------------------------
# _parse_su_ref
# ---------------------------------------------------------------------------

class TestParseSuRef:
    def test_standard(self):
        assert _parse_su_ref("13/2026") == (13, "2026")

    def test_short_year(self):
        assert _parse_su_ref("19/25") == (19, "2025")

    def test_spaces(self):
        assert _parse_su_ref("  13 / 2026  ") == (13, "2026")

    def test_suffix(self):
        # El sufijo de subserie va DENTRO de serie, en minúscula (formato CRM)
        assert _parse_su_ref("152/2021-P") == (152, "2021-p")

    def test_suffix_short_year(self):
        assert _parse_su_ref("34/23-N") == (34, "2023-n")

    def test_suffix_with_spaces(self):
        assert _parse_su_ref("23 / 2023 - N") == (23, "2023-n")

    def test_suffix_space_separated(self):
        # AMS escribe el sufijo separado por espacio, sin guion
        assert _parse_su_ref("1/2022 N") == (1, "2022-n")

    def test_no_false_suffix(self):
        # texto tras la referencia no debe capturarse como sufijo
        assert _parse_su_ref("33/2024 NEXOLUB") == (33, "2024")

    def test_none(self):
        assert _parse_su_ref(None) == (None, None)

    def test_garbage(self):
        assert _parse_su_ref("sin referencia") == (None, None)

    def test_three_digit_year(self):
        # Caso improbable pero no rompe
        assert _parse_su_ref("5/026") == (5, "2026")


# ---------------------------------------------------------------------------
# normalize_descripcion
# ---------------------------------------------------------------------------

class TestNormalizeDescripcion:
    def test_basic(self):
        assert normalize_descripcion("contestación a la demanda") == "contestacion demanda"

    def test_nombramiento(self):
        assert normalize_descripcion("nombramiento de administrador") == "nombramiento administrador"

    def test_preserves_ñ(self):
        result = normalize_descripcion("daño al año")
        assert "ñ" in result
        assert "ano" not in result.split()

    def test_max_chars(self):
        long_text = "palabra " * 20
        result = normalize_descripcion(long_text, max_chars=40)
        assert len(result) <= 40

    def test_removes_stopwords(self):
        result = normalize_descripcion("el auto de la providencia en el juzgado")
        assert "el" not in result.split()
        assert "de" not in result.split()
        assert "la" not in result.split()
        assert "auto" in result
        assert "providencia" in result
        assert "juzgado" in result


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_removes_forbidden(self):
        assert sanitize_filename('test:file*name?.pdf') == "test_file_name_.pdf"

    def test_clean_passthrough(self):
        assert sanitize_filename("2026-06-12 - Auto - nombramiento.pdf") == "2026-06-12 - Auto - nombramiento.pdf"


# ---------------------------------------------------------------------------
# abreviar_tipo
# ---------------------------------------------------------------------------

class TestAbreviarTipo:
    @pytest.mark.parametrize("input_tipo,expected", [
        ("auto", "Auto"),
        ("Auto", "Auto"),
        ("sentencia", "Sent"),
        ("decreto", "Decr"),
        ("diligencia de ordenación", "DiOr"),
        ("diligencia de ordenacion", "DiOr"),
        ("providencia", "Prov"),
        ("cédula", "Ced"),
        ("oficio", "Ofi"),
        ("mandamiento", "Mand"),
        ("escrito", "Escr"),
        ("escrito contraria", "Escr-Crio"),
        ("escrito parte contraria", "Escr-Crio"),
        ("justificante de presentación", "Just Escr"),
        ("recurso", "Rec"),
        ("acta", "Acta"),
        ("tasación de costas", "Tasac"),
        ("testimonio", "Test"),
        ("notificación", "Notif"),
        ("grabación", "Grab"),
        ("otros", "Otros"),
    ])
    def test_abreviaturas(self, input_tipo, expected):
        assert abreviar_tipo(input_tipo) == expected

    def test_unknown_passthrough(self):
        assert abreviar_tipo("cosa rara") == "cosa rara"


# ---------------------------------------------------------------------------
# _extract_extension
# ---------------------------------------------------------------------------

class TestExtractExtension:
    def test_pdf(self):
        assert _extract_extension("documento.pdf") == ".pdf"

    def test_uppercase(self):
        assert _extract_extension("ESCRITO.PDF") == ".pdf"

    def test_no_extension(self):
        assert _extract_extension("ESCRITO SIN EXT") == ".pdf"

    def test_docx(self):
        assert _extract_extension("escrito.docx") == ".docx"


# ---------------------------------------------------------------------------
# _looks_like_logo
# ---------------------------------------------------------------------------

class TestLooksLikeLogo:
    def test_logo_in_name(self):
        assert _looks_like_logo("logo_ams.png")

    def test_firma(self):
        assert _looks_like_logo("firma.jpg")

    def test_image_numbered(self):
        assert _looks_like_logo("image001.png")

    def test_real_document(self):
        assert not _looks_like_logo("cedula_emplazamiento_2026.pdf")

    def test_short_image(self):
        assert _looks_like_logo("pic.jpg")

    def test_long_image_name(self):
        assert not _looks_like_logo("escaneado_notificacion_juzgado_primera_instancia.png")


# ---------------------------------------------------------------------------
# _check_signal_matches
# ---------------------------------------------------------------------------

class TestCheckSignalMatches:
    def test_full_match(self):
        signals = IntakeSignals(
            num_expediente=13, serie_expediente="2026",
            juzgado="Juzgado 1ª Instancia nº 3 Barcelona",
            num_asunto="456/2025",
            tipo_procedimiento="ordinario",
        )
        exp_data = {
            "num_expediente": "13",
            "serie_expediente": "2026",
            "juzgado": "Juzgado de 1ª Instancia nº 3 de Barcelona",
            "num_asunto": "456/2025",
            "tipo_procedimiento": "Procedimiento Ordinario",
        }
        matches = _check_signal_matches(signals, exp_data)
        assert "num_expediente" in matches
        assert "serie_expediente" in matches
        assert "juzgado" in matches
        assert "num_asunto" in matches
        assert "tipo_procedimiento" in matches

    def test_partial_match(self):
        signals = IntakeSignals(num_expediente=13, serie_expediente="2026")
        exp_data = {"num_expediente": "13", "serie_expediente": "2026"}
        matches = _check_signal_matches(signals, exp_data)
        assert "num_expediente" in matches
        assert "serie_expediente" in matches
        assert "juzgado" not in matches

    def test_serie_con_sufijo(self):
        # serie con subserie debe casar contra el valor del CRM ('2023-n')
        signals = IntakeSignals(num_expediente=34, serie_expediente="2023-n")
        exp_data = {"num_expediente": "34", "serie_expediente": "2023-n"}
        matches = _check_signal_matches(signals, exp_data)
        assert "serie_expediente" in matches


# ---------------------------------------------------------------------------
# extract_signals (con mock del LLM)
# ---------------------------------------------------------------------------

class TestExtractSignals:
    @patch("core.procurador_intake.chat_json")
    def test_basic_extraction(self, mock_chat):
        mock_chat.return_value = {
            "su_ref": "13/2026",
            "contrario": "PEREZ GARCIA",
            "cliente": "EV MMC SPAIN",
            "juzgado": "Juzgado 1ª Instancia nº 3 Barcelona",
            "num_asunto": "456/2025",
            "tipo_procedimiento": "ordinario",
            "tipo_actuacion": "diligencia de ordenación",
            "fecha_actuacion": "2026-06-10",
            "es_ruido": False,
        }
        signals = extract_signals("Notificación exp 13/2026", "Cuerpo del correo")
        assert signals.su_ref == "13/2026"
        assert signals.num_expediente == 13
        assert signals.serie_expediente == "2026"
        assert signals.contrario == "PEREZ GARCIA"
        assert not signals.es_ruido

    @patch("core.procurador_intake.chat_json")
    def test_ruido(self, mock_chat):
        mock_chat.return_value = {"es_ruido": True}
        signals = extract_signals("Re: Felices fiestas", "Gracias igualmente")
        assert signals.es_ruido

    @patch("core.procurador_intake.chat_json")
    def test_no_ref(self, mock_chat):
        mock_chat.return_value = {
            "su_ref": None,
            "contrario": "LOPEZ",
            "es_ruido": False,
        }
        signals = extract_signals("Asunto sin ref", "Cuerpo")
        assert signals.su_ref is None
        assert signals.num_expediente is None


# ---------------------------------------------------------------------------
# match_expediente (con mock del cliente Sudespacho)
# ---------------------------------------------------------------------------

class TestMatchExpediente:
    def test_alta_confianza(self):
        signals = IntakeSignals(
            su_ref="13/2026", num_expediente=13, serie_expediente="2026",
        )
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{
                "id": 444,
                "values": [
                    {"property": {"name": "num_expediente"}, "value": "13"},
                    {"property": {"name": "serie_expediente"}, "value": "2026"},
                ],
            }],
        }
        mock_client._client.get.return_value = mock_response

        result = match_expediente(signals, sudo_client=mock_client)
        assert result.confianza == "alta"
        assert result.expediente_id == 444

    def test_sin_match(self):
        signals = IntakeSignals(
            su_ref="99/2099", num_expediente=99, serie_expediente="2099",
        )
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_client._client.get.return_value = mock_response

        result = match_expediente(signals, sudo_client=mock_client)
        assert result.confianza == "ninguna"
        assert result.expediente_id is None

    def test_ruido_sin_su_ref(self):
        # es_ruido SIN su_ref utilizable → ninguna (no se busca en CRM)
        signals = IntakeSignals(es_ruido=True)
        result = match_expediente(signals, sudo_client=MagicMock())
        assert result.confianza == "ninguna"
        assert result.senales_usadas == ["es_ruido"]

    def test_ruido_advisory_con_su_ref(self):
        # es_ruido es ADVISORY: si hay su_ref que resuelve, igual da ALTA
        signals = IntakeSignals(
            su_ref="13/2026", num_expediente=13, serie_expediente="2026",
            es_ruido=True,
        )
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{
                "id": 444,
                "values": [
                    {"property": {"name": "num_expediente"}, "value": "13"},
                    {"property": {"name": "serie_expediente"}, "value": "2026"},
                ],
            }],
        }
        mock_client._client.get.return_value = mock_response
        result = match_expediente(signals, sudo_client=mock_client)
        assert result.confianza == "alta"
        assert result.expediente_id == 444
        assert "es_ruido_advisory" in result.senales_usadas

    def test_suffix_serie_match(self):
        # su_ref con sufijo: busca por serie '2023-n' y casa el expediente real
        signals = IntakeSignals(
            su_ref="34/2023-N", num_expediente=34, serie_expediente="2023-n",
        )
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{
                "id": 376,
                "values": [
                    {"property": {"name": "num_expediente"}, "value": "34"},
                    {"property": {"name": "serie_expediente"}, "value": "2023-n"},
                ],
            }],
        }
        mock_client._client.get.return_value = mock_response
        result = match_expediente(signals, sudo_client=mock_client)
        assert result.confianza == "alta"
        assert result.expediente_id == 376
        assert "serie_expediente" in result.senales_usadas

    def test_serie_crm_con_espacios(self):
        # CRM guarda '2022 - n' (con espacios); su_ref '1/2022 N' → serie '2022-n'.
        # El filtro de serie en cliente debe casar pese al formato inconsistente.
        signals = IntakeSignals(
            su_ref="1/2022 N", num_expediente=1, serie_expediente="2022-n",
        )
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{
                "id": 356,
                "values": [
                    {"property": {"name": "num_expediente"}, "value": "1"},
                    {"property": {"name": "serie_expediente"}, "value": "2022 - n"},
                ],
            }],
        }
        mock_client._client.get.return_value = mock_response
        result = match_expediente(signals, sudo_client=mock_client)
        assert result.confianza == "alta"
        assert result.expediente_id == 356
        assert "serie_expediente" in result.senales_usadas

    def test_num_distinto_serie_descartado(self):
        # Búsqueda por num devuelve varios años; solo casa la serie correcta.
        signals = IntakeSignals(
            su_ref="1/2026", num_expediente=1, serie_expediente="2026",
        )
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"id": 356, "values": [
                    {"property": {"name": "num_expediente"}, "value": "1"},
                    {"property": {"name": "serie_expediente"}, "value": "2022 - n"},
                ]},
                {"id": 700, "values": [
                    {"property": {"name": "num_expediente"}, "value": "1"},
                    {"property": {"name": "serie_expediente"}, "value": "2026"},
                ]},
            ],
        }
        mock_client._client.get.return_value = mock_response
        result = match_expediente(signals, sudo_client=mock_client)
        assert result.confianza == "alta"
        assert result.expediente_id == 700

    def test_sin_su_ref(self):
        signals = IntakeSignals()
        result = match_expediente(signals, sudo_client=MagicMock())
        assert result.confianza == "ninguna"
        assert "sin_su_ref" in result.senales_usadas


# ---------------------------------------------------------------------------
# propose_attachment_name (con mock del LLM)
# ---------------------------------------------------------------------------

class TestProposeAttachmentName:
    @patch("core.procurador_intake.chat_json")
    def test_actuacion_procesal(self, mock_chat):
        mock_chat.return_value = {
            "fecha": "2026-06-10",
            "tipo": "diligencia de ordenación",
            "descripcion": "admisión de la demanda",
            "confianza": 0.9,
            "es_probatorio": False,
            "num_doc": None,
        }
        result = propose_attachment_name(
            "Texto del auto...", "Cuerpo correo", "DOC001.pdf",
        )
        assert result.tipo == "DiOr"
        assert "2026-06-10" in result.proposed_name
        assert "DiOr" in result.proposed_name
        assert result.proposed_name.endswith(".pdf")
        assert result.subir is True

    @patch("core.procurador_intake.chat_json")
    def test_documento_probatorio(self, mock_chat):
        mock_chat.return_value = {
            "fecha": "2026-01-02",
            "tipo": "otros",
            "descripcion": "contrato arrendamiento",
            "confianza": 0.85,
            "es_probatorio": True,
            "num_doc": 1,
        }
        result = propose_attachment_name(
            "Contrato...", "Cuerpo", "scan001.pdf",
        )
        assert result.proposed_name.startswith("D 01")
        assert "contrato arrendamiento" in result.proposed_name
        assert result.es_probatorio

    @patch("core.procurador_intake.chat_json")
    def test_logo_desmarcado(self, mock_chat):
        mock_chat.return_value = {
            "fecha": None,
            "tipo": "otros",
            "descripcion": "logotipo",
            "confianza": 0.3,
            "es_probatorio": False,
            "num_doc": None,
        }
        result = propose_attachment_name(
            "", "Cuerpo", "logo_ams.png",
        )
        assert result.subir is False

    @patch("core.procurador_intake.chat_json")
    def test_sin_fecha_usa_recepcion(self, mock_chat):
        mock_chat.return_value = {
            "fecha": None,
            "tipo": "auto",
            "descripcion": "apertura procedimiento",
            "confianza": 0.7,
            "es_probatorio": False,
            "num_doc": None,
        }
        result = propose_attachment_name(
            "Texto", "Cuerpo", "doc.pdf",
            fecha_recepcion="2026-06-12",
        )
        assert "2026-06-12" in result.proposed_name
        assert "Auto" in result.proposed_name
