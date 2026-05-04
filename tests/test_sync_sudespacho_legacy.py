"""Tests del módulo sync_sudespacho_legacy — solo lógica pura, sin red."""

from __future__ import annotations

import pytest

from core.sync_sudespacho_legacy import (
    ENDPOINTS,
    SudespachoLegacyClient,
    SudespachoLegacyConfig,
    SudespachoLegacyError,
    _CSRF_RE,
    _EXP_ROW_RE,
    _LAST_PAGE_RE,
    _ROW_ID_RE,
    _extract_filename,
    _is_eplan_landing,
    _jwt_expires_in_secs,
    _update_env_field,
)


# ---- Configuración --------------------------------------------------------

def test_legacy_config_from_env(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_LEGACY_HOST", "tnm.sudespacho.net")
    monkeypatch.setenv("SUDESPACHO_LEGACY_PHPSESSID", "abc123def456")
    monkeypatch.delenv("SUDESPACHO_LEGACY_TIMEOUT_S", raising=False)

    cfg = SudespachoLegacyConfig.from_env()
    assert cfg.host == "tnm.sudespacho.net"
    assert cfg.phpsessid == "abc123def456"
    assert cfg.timeout_s == 120
    assert cfg.base_url == "https://tnm.sudespacho.net"


def test_legacy_config_strip_scheme(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_LEGACY_HOST", "https://tnm.sudespacho.net/")
    monkeypatch.setenv("SUDESPACHO_LEGACY_PHPSESSID", "x")
    cfg = SudespachoLegacyConfig.from_env()
    assert cfg.host == "tnm.sudespacho.net"
    assert cfg.base_url == "https://tnm.sudespacho.net"


def test_legacy_config_falla_sin_envvars(monkeypatch):
    monkeypatch.delenv("SUDESPACHO_LEGACY_HOST", raising=False)
    monkeypatch.delenv("SUDESPACHO_LEGACY_PHPSESSID", raising=False)
    with pytest.raises(SudespachoLegacyError):
        SudespachoLegacyConfig.from_env()


# ---- Endpoints estables ---------------------------------------------------

def test_endpoints_canonicos():
    assert ENDPOINTS["gdocu_list"] == (
        "/gdocu/list/elemento/gdocu/elemento_relacionado/{element}/"
        "miembro_relacionado/{id}/direccion_relacionado/der"
    )
    assert ENDPOINTS["predownload"] == (
        "/gestordocumental/predownloadfile/elemento_relacionado/{element}/"
        "miembro_relacionado/{id}/direccion_relacionado/der"
    )
    assert ENDPOINTS["download_s3"] == (
        "/gestordocumental/descargaficheros3/id_docu/{doc_id}/"
        "elemento_relacionado/{element}/miembro_relacionado/{id}/"
        "direccion_relacionado/der"
    )


# ---- Regex parsing --------------------------------------------------------

def test_row_id_regex_extrae_doc_ids():
    html = """
    <tr id="fila_gdocu_40020" class="impar">...</tr>
    <tr id="fila_gdocu_40021">...</tr>
    <tr id="fila_actuaciones_19342">no es gdocu</tr>
    <tr id="fila_gdocu_40022" data-something>...</tr>
    """
    ids = _ROW_ID_RE.findall(html)
    assert ids == ["40020", "40021", "40022"]


def test_csrf_regex_extrae_token():
    html = """
        var advance = 1;
        var version_edicion_online = 3;
        var csrf_token = 'dbc58b961fe47bd5d96884b0b577408b';
        var apiAuthEndpoint = 'https://api-auth-commons-pro.sudespacho.biz/api/';
    """
    m = _CSRF_RE.search(html)
    assert m is not None
    assert m.group(1) == "dbc58b961fe47bd5d96884b0b577408b"
    assert len(m.group(1)) == 32


def test_csrf_regex_no_falsos_positivos():
    # Token no hexadecimal o longitud incorrecta
    assert _CSRF_RE.search("var csrf_token = 'NO_VALIDO';") is None
    assert _CSRF_RE.search("var csrf_token = 'abc';") is None


# ---- Content-Disposition filename -----------------------------------------

def test_extract_filename_simple():
    cd = 'attachment; filename="Demanda 2026.pdf"'
    assert _extract_filename(cd) == "Demanda 2026.pdf"


def test_extract_filename_sin_comillas():
    cd = "attachment; filename=informe.pdf"
    assert _extract_filename(cd) == "informe.pdf"


def test_extract_filename_rfc5987():
    cd = "attachment; filename*=UTF-8''Sentencia%20n%C2%BA%2042.pdf"
    out = _extract_filename(cd)
    assert "Sentencia" in out and "42.pdf" in out


def test_extract_filename_caracteres_especiales():
    # Como en el caso real: "CEDULA DE EMPLAZAMIENTO - Sección Civil del IT de BCN. Plaza nº. 39.pdf"
    cd = (
        'attachment; filename="CEDULA DE EMPLAZAMIENTO - '
        'Sección Civil del IT de BCN. Plaza nº. 39.pdf"'
    )
    out = _extract_filename(cd)
    assert "CEDULA" in out
    assert ".pdf" in out


def test_extract_filename_vacio():
    assert _extract_filename("") is None
    assert _extract_filename("inline") is None


# ---- Listado de expedientes (parsing del HTML server-rendered) ----------

_LIST_HTML_FIXTURE = """
<table>
  <tr id="fila_expedientes_judiciales_649" class="impar">
    <td><i class="ico"></i></td>
    <td><input type="checkbox" value="649"></td>
    <td>14-04-2026</td>
    <td>Demandado</td>
    <td>29</td>
    <td>2026</td>
    <td>BaRR3 - Roser 39, 2&ordm; (W-030LFT) - Art 20 LAU</td>
    <td>EV MMC SPAIN, S.L.U.</td>
    <td>ZAIRA GASANOVA</td>
  </tr>
  <tr id="fila_expedientes_judiciales_648">
    <td><i></i></td>
    <td><input type="checkbox" value="648"></td>
    <td>13-04-2026</td>
    <td>Actor</td>
    <td>28</td>
    <td>2026</td>
    <td>BaRR1 - Collserola 53 Bis (W-02VREL) - BD</td>
    <td>EV MMC SPAIN, S.L.U.</td>
    <td>RICARD ESPINOSA DE LOS MONTEROS</td>
  </tr>
  <tr id="fila_actuaciones_19342">
    <td>no es expediente</td>
  </tr>
</table>
<a href="javascript:pagina(1, 'list_expedientes_judiciales');">Primero</a>
<a href="javascript:pagina(2, 'list_expedientes_judiciales');">Siguiente</a>
<a href="javascript:pagina(31, 'list_expedientes_judiciales');">Último</a>
"""


def test_exp_row_regex_extrae_filas():
    rows = list(_EXP_ROW_RE.finditer(_LIST_HTML_FIXTURE))
    # Tres filas tr en total, pero solo dos son de expedientes_judiciales
    elements = [m.group("element") for m in rows]
    assert "expedientes_judiciales" in elements
    assert "actuaciones" in elements

    # IDs de las filas de expedientes_judiciales
    judiciales_ids = [m.group("id") for m in rows if m.group("element") == "expedientes_judiciales"]
    assert judiciales_ids == ["649", "648"]


def test_last_page_regex():
    pages = [int(m.group(1)) for m in _LAST_PAGE_RE.finditer(_LIST_HTML_FIXTURE)]
    assert max(pages) == 31


def test_parse_row_extrae_cliente_y_metadatos():
    # Tomar el body de la primera fila
    m = next(_EXP_ROW_RE.finditer(_LIST_HTML_FIXTURE))
    entry = SudespachoLegacyClient._parse_row(
        "expedientes_judiciales", "649", m.group("body"),
    )
    assert entry.expediente_id == "649"
    assert entry.element == "expedientes_judiciales"
    assert entry.fecha_alta == "14-04-2026"
    assert entry.posicion_procesal == "Demandado"
    assert entry.num_expediente == "29"
    assert entry.serie_expediente == "2026"
    assert "EV MMC SPAIN, S.L.U." in (entry.cliente or "")
    # Contraparte persona física (mayúsculas): la nueva heurística la captura
    assert entry.contraparte == "ZAIRA GASANOVA"


def test_parse_row_contraparte_sociedad():
    """Contraparte que es sociedad (con S.L./S.A./etc.) también se captura."""
    body = """
        <td><i></i></td>
        <td>05-03-2026</td>
        <td>Actor</td>
        <td>15</td>
        <td>2026</td>
        <td>BaRR1 - Algun Ref (W-XYZ) - BD</td>
        <td>EV MMC SPAIN, S.L.U.</td>
        <td>COFRELEC GRANOLLERS, S.L.U.</td>
    """
    entry = SudespachoLegacyClient._parse_row("expedientes_judiciales", "999", body)
    assert entry.cliente == "EV MMC SPAIN, S.L.U."
    assert entry.contraparte == "COFRELEC GRANOLLERS, S.L.U."


def test_parse_row_actor_position():
    matches = list(_EXP_ROW_RE.finditer(_LIST_HTML_FIXTURE))
    # Segunda fila: posición Actor
    m = matches[1]
    entry = SudespachoLegacyClient._parse_row(
        "expedientes_judiciales", "648", m.group("body"),
    )
    assert entry.posicion_procesal == "Actor"
    assert entry.cliente == "EV MMC SPAIN, S.L.U."


def test_strip_html_helper():
    out = SudespachoLegacyClient._strip_html(
        "<td><b>Hola</b>&nbsp;mundo &amp; cía</td>"
    )
    assert out == "Hola mundo & cía"


# ---- _is_eplan_landing ----------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


def test_is_eplan_landing_true():
    r = _FakeResponse(200, "<title>E-plan - sudespacho.net</title>")
    assert _is_eplan_landing(r) is True


def test_is_eplan_landing_false_crm_page():
    r = _FakeResponse(200, "<title>Colaboradores · TNM</title><script>var csrf_token='abc'</script>")
    assert _is_eplan_landing(r) is False


def test_is_eplan_landing_false_non_200():
    r = _FakeResponse(404, "E-plan - sudespacho.net")
    assert _is_eplan_landing(r) is False


def test_is_eplan_landing_checks_only_start():
    # El marcador aparece después de los primeros 2000 chars — NO debe detectarse
    r = _FakeResponse(200, "x" * 2100 + "E-plan - sudespacho.net")
    assert _is_eplan_landing(r) is False


# ---- _jwt_expires_in_secs -------------------------------------------------

def _make_jwt(offset_secs: int) -> str:
    """Construye un JWT mínimo con exp = now + offset_secs."""
    import base64, json, time
    payload = {"exp": int(time.time()) + offset_secs, "iat": int(time.time())}
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{p}.sig"


def test_jwt_expires_in_secs_future():
    secs = _jwt_expires_in_secs(_make_jwt(3600))
    assert secs is not None and 3580 <= secs <= 3600


def test_jwt_expires_in_secs_expired():
    secs = _jwt_expires_in_secs(_make_jwt(-100))
    assert secs is not None and secs < 0


def test_jwt_expires_in_secs_invalid_string():
    assert _jwt_expires_in_secs("no_es_un_jwt") is None


def test_jwt_expires_in_secs_without_exp():
    import base64, json
    payload = {"iat": 1000}  # sin campo exp
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert _jwt_expires_in_secs(f"h.{p}.s") is None


# ---- _update_env_field ----------------------------------------------------

def test_update_env_field_updates_os_environ_and_file(tmp_path, monkeypatch):
    import os
    env_file = tmp_path / ".env"
    env_file.write_text("SUDESPACHO_LEGACY_JWT=old_value\n", encoding="utf-8")

    # Parchear Path para que apunte al fichero temporal
    import core.sync_sudespacho_legacy as _mod
    from pathlib import Path
    original_resolve = Path.resolve
    monkeypatch.setattr(
        Path, "resolve",
        lambda self: env_file if str(self).endswith(".env") else original_resolve(self),
    )
    monkeypatch.delenv("SUDESPACHO_LEGACY_JWT", raising=False)

    _update_env_field("SUDESPACHO_LEGACY_JWT", "new_value")

    assert os.environ.get("SUDESPACHO_LEGACY_JWT") == "new_value"
    assert "SUDESPACHO_LEGACY_JWT=new_value" in env_file.read_text(encoding="utf-8")


def test_update_env_field_adds_missing_key(tmp_path, monkeypatch):
    import os
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER_KEY=value\n", encoding="utf-8")

    import core.sync_sudespacho_legacy as _mod
    from pathlib import Path
    original_resolve = Path.resolve
    monkeypatch.setattr(
        Path, "resolve",
        lambda self: env_file if str(self).endswith(".env") else original_resolve(self),
    )
    monkeypatch.delenv("NEW_FIELD", raising=False)

    _update_env_field("NEW_FIELD", "new_val")

    assert "NEW_FIELD=new_val" in env_file.read_text(encoding="utf-8")
    assert os.environ.get("NEW_FIELD") == "new_val"
