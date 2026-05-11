"""Tests del módulo intake_drive — sin red, sin rclone real.

Cubre:
- parse_drive_url: formatos de URL Google Drive + IDs directos + errores.
- pull_drive_ev: idempotencia (.pulled), force=True, fallo rclone, timeout.
- register_drive_ev (vía pull_drive_ev): persistencia en _caso.md.
- DriveIntakeError: se lanza con result adjunto en fallo de rclone.
- get_drive_folder_info: token OK, sin token, error API.
"""

from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core import case_manager
from core.intake_drive import (
    DriveIntakeError,
    DriveFolderInfo,
    DriveIntakeResult,
    _DRIVE_EV_INPUT_SUBDIR,
    _PULL_MARKER,
    get_drive_folder_info,
    parse_drive_url,
    parse_ev_folder_name,
    pull_drive_ev,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reload_config(tmp_casos_root, monkeypatch):
    """Aísla el CASOS_ROOT y recarga config + case_manager en cada test."""
    import importlib
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)


@pytest.fixture
def caso_ev(tmp_casos_root):
    """Crea un caso de prueba con estructura completa."""
    importlib.reload(case_manager)
    case_manager.ensure_case(
        "EV-2026-001",
        titulo="Caso prueba Drive EV",
        cliente="EV MMC SPAIN, S.L.U.",
    )
    return "EV-2026-001"


def _mock_rclone_ok(monkeypatch):
    """Mock de subprocess.run que simula rclone exitoso."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.returncode = 0
    mock.stdout = ""
    mock.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
    return mock


def _mock_rclone_fail(monkeypatch, returncode: int = 1, stderr: str = "error de red"):
    """Mock de subprocess.run que simula fallo de rclone."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.returncode = returncode
    mock.stdout = ""
    mock.stderr = stderr
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
    return mock


# ---------------------------------------------------------------------------
# parse_drive_url
# ---------------------------------------------------------------------------

class TestParseDriveUrl:
    def test_url_simple(self):
        url = "https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        assert parse_drive_url(url) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"

    def test_url_con_cuenta(self):
        url = "https://drive.google.com/drive/u/0/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        assert parse_drive_url(url) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"

    def test_url_con_cuenta_alta(self):
        url = "https://drive.google.com/drive/u/1/folders/ABCDEFabcdef1234567890"
        assert parse_drive_url(url) == "ABCDEFabcdef1234567890"

    def test_url_con_parametros_usp(self):
        url = (
            "https://drive.google.com/drive/u/0/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
            "?usp=sharing"
        )
        assert parse_drive_url(url) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"

    def test_url_con_resourcekey(self):
        url = (
            "https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
            "?usp=sharing&resourcekey=0-abc123"
        )
        assert parse_drive_url(url) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"

    def test_id_directo(self):
        """Un ID puro (sin prefijo de URL) se acepta directamente."""
        folder_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        assert parse_drive_url(folder_id) == folder_id

    def test_id_directo_con_guiones(self):
        folder_id = "0AHf-bCdEfGhIjKlMnOpQ"
        assert parse_drive_url(folder_id) == folder_id

    def test_url_invalida_lanza_error(self):
        with pytest.raises(ValueError, match="folder_id"):
            parse_drive_url("https://docs.google.com/document/d/abc123")

    def test_url_vacia_lanza_error(self):
        with pytest.raises(ValueError):
            parse_drive_url("")

    def test_id_demasiado_corto_lanza_error(self):
        """Un string corto no es ni URL ni ID válido."""
        with pytest.raises(ValueError):
            parse_drive_url("abc")

    def test_strip_espacios(self):
        url = "  https://drive.google.com/drive/folders/ABCDEF1234567890  "
        assert parse_drive_url(url) == "ABCDEF1234567890"


# ---------------------------------------------------------------------------
# pull_drive_ev — caso no existe
# ---------------------------------------------------------------------------

def test_pull_falla_si_caso_no_existe(tmp_casos_root, monkeypatch):
    _mock_rclone_ok(monkeypatch)
    with pytest.raises(FileNotFoundError, match="EV-9999-XXX"):
        pull_drive_ev("EV-9999-XXX", folder_id="folderABC", team_id="teamXYZ")


# ---------------------------------------------------------------------------
# pull_drive_ev — idempotencia
# ---------------------------------------------------------------------------

def test_pull_skip_si_pulled_existe(caso_ev, tmp_casos_root, monkeypatch):
    """Si .pulled existe y force=False, debe devolver skipped=True sin llamar rclone."""
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    # Crear .pulled manualmente
    target = tmp_casos_root / caso_ev / "00_Input" / _DRIVE_EV_INPUT_SUBDIR
    target.mkdir(parents=True, exist_ok=True)
    (target / _PULL_MARKER).write_text("{}", encoding="utf-8")

    result = pull_drive_ev(caso_ev, folder_id="folder123", team_id="team456")

    assert result.skipped is True
    assert result.rclone_returncode == 0
    mock_run.assert_not_called()


def test_pull_force_reejecutra_rclone(caso_ev, tmp_casos_root, monkeypatch):
    """force=True debe llamar rclone aunque .pulled exista."""
    _mock_rclone_ok(monkeypatch)

    target = tmp_casos_root / caso_ev / "00_Input" / _DRIVE_EV_INPUT_SUBDIR
    target.mkdir(parents=True, exist_ok=True)
    (target / _PULL_MARKER).write_text("{}", encoding="utf-8")

    result = pull_drive_ev(caso_ev, folder_id="folder123", team_id="team456", force=True)

    assert result.skipped is False
    assert result.rclone_returncode == 0


# ---------------------------------------------------------------------------
# pull_drive_ev — pull exitoso
# ---------------------------------------------------------------------------

def test_pull_exitoso_escribe_marker(caso_ev, tmp_casos_root, monkeypatch):
    _mock_rclone_ok(monkeypatch)

    result = pull_drive_ev(caso_ev, folder_id="folderW030", team_id="teamBarcelona")

    assert result.skipped is False
    assert result.rclone_returncode == 0
    assert not result.errors

    marker = tmp_casos_root / caso_ev / "00_Input" / _DRIVE_EV_INPUT_SUBDIR / _PULL_MARKER
    assert marker.exists()

    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["folder_id"] == "folderW030"
    assert data["team_id"] == "teamBarcelona"
    assert data["rclone_returncode"] == 0
    assert "last_sync" in data


def test_pull_exitoso_actualiza_caso_md(caso_ev, tmp_casos_root, monkeypatch):
    _mock_rclone_ok(monkeypatch)

    pull_drive_ev(caso_ev, folder_id="folderW030", team_id="teamBarcelona")

    import yaml
    index = tmp_casos_root / caso_ev / "00_Input" / "_caso.md"
    text = index.read_text(encoding="utf-8")
    _, fm_raw, _ = text.split("---", 2)
    fm = yaml.safe_load(fm_raw)

    meta = fm.get("meta", {})
    assert meta.get("drive_ev_team_id") == "teamBarcelona"
    assert meta.get("drive_ev_folder_id") == "folderW030"


def test_pull_exitoso_devuelve_files_after(caso_ev, tmp_casos_root, monkeypatch):
    """files_after debe contar archivos reales, excluir .pulled."""
    _mock_rclone_ok(monkeypatch)

    target = tmp_casos_root / caso_ev / "00_Input" / _DRIVE_EV_INPUT_SUBDIR
    target.mkdir(parents=True, exist_ok=True)
    # Simular 3 archivos descargados por rclone antes del pull
    (target / "contrato.pdf").write_bytes(b"%PDF")
    (target / "oferta.docx").write_bytes(b"DOCX")
    (target / "encargo.pdf").write_bytes(b"%PDF")

    result = pull_drive_ev(caso_ev, folder_id="folderW030", team_id="teamBarcelona")

    assert result.files_after == 3  # .pulled no se cuenta


# ---------------------------------------------------------------------------
# pull_drive_ev — fallos de rclone
# ---------------------------------------------------------------------------

def test_pull_falla_rclone_lanza_error(caso_ev, tmp_casos_root, monkeypatch):
    _mock_rclone_fail(monkeypatch, returncode=1, stderr="remote not found")

    with pytest.raises(DriveIntakeError) as exc_info:
        pull_drive_ev(caso_ev, folder_id="folderX", team_id="teamX")

    err = exc_info.value
    assert err.result.rclone_returncode == 1
    assert err.result.errors
    assert "remote not found" in err.result.errors[0]


def test_pull_falla_rclone_escribe_marker_con_error(caso_ev, tmp_casos_root, monkeypatch):
    """Aunque rclone falle, .pulled debe escribirse para registrar el intento."""
    _mock_rclone_fail(monkeypatch, returncode=5)

    with pytest.raises(DriveIntakeError):
        pull_drive_ev(caso_ev, folder_id="folderX", team_id="teamX")

    marker = tmp_casos_root / caso_ev / "00_Input" / _DRIVE_EV_INPUT_SUBDIR / _PULL_MARKER
    assert marker.exists()
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["rclone_returncode"] == 5


def test_pull_timeout_lanza_error(caso_ev, tmp_casos_root, monkeypatch):
    def _timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd=["rclone"], timeout=300)

    monkeypatch.setattr("subprocess.run", _timeout)

    with pytest.raises(DriveIntakeError) as exc_info:
        pull_drive_ev(caso_ev, folder_id="folderX", team_id="teamX")

    assert exc_info.value.result.rclone_returncode == -1
    assert any("timeout" in e for e in exc_info.value.result.errors)


def test_pull_rclone_no_encontrado_lanza_error(caso_ev, tmp_casos_root, monkeypatch):
    def _not_found(*a, **kw):
        raise FileNotFoundError("rclone not found")

    monkeypatch.setattr("subprocess.run", _not_found)

    with pytest.raises(DriveIntakeError) as exc_info:
        pull_drive_ev(caso_ev, folder_id="folderX", team_id="teamX")

    assert exc_info.value.result.rclone_returncode == -2
    assert any("rclone" in e.lower() for e in exc_info.value.result.errors)


# ---------------------------------------------------------------------------
# register_drive_ev — standalone
# ---------------------------------------------------------------------------

def test_register_drive_ev_idempotente(caso_ev, tmp_casos_root):
    """Llamar register_drive_ev dos veces con los mismos IDs no debe reescribir."""
    from core.case_manager import register_drive_ev
    import yaml

    register_drive_ev(caso_ev, team_id="teamA", folder_id="folderB")
    index = tmp_casos_root / caso_ev / "00_Input" / "_caso.md"
    mtime_1 = index.stat().st_mtime

    register_drive_ev(caso_ev, team_id="teamA", folder_id="folderB")
    mtime_2 = index.stat().st_mtime

    assert mtime_1 == mtime_2, "El fichero no debería reescribirse si los IDs no cambian"


def test_register_drive_ev_actualiza_si_cambian_ids(caso_ev, tmp_casos_root):
    """Si cambia el folder_id, el índice debe actualizarse."""
    from core.case_manager import register_drive_ev
    import yaml

    register_drive_ev(caso_ev, team_id="teamA", folder_id="folder_viejo")
    register_drive_ev(caso_ev, team_id="teamA", folder_id="folder_nuevo")

    index = tmp_casos_root / caso_ev / "00_Input" / "_caso.md"
    text = index.read_text(encoding="utf-8")
    _, fm_raw, _ = text.split("---", 2)
    fm = yaml.safe_load(fm_raw)

    assert fm["meta"]["drive_ev_folder_id"] == "folder_nuevo"


def test_register_drive_ev_no_falla_si_caso_no_existe(tmp_casos_root):
    """No debe lanzar error si el caso no existe todavía."""
    from core.case_manager import register_drive_ev
    # No debe lanzar, simplemente hace nada
    register_drive_ev("EV-INEXISTENTE-999", team_id="teamA", folder_id="folderB")


# ---------------------------------------------------------------------------
# parse_ev_folder_name
# ---------------------------------------------------------------------------

def test_parse_folder_guion_simple():
    d, m = parse_ev_folder_name("Pedro Lain Entralgo 4 Chalet 4- W-02W4PJ")
    assert d == "Pedro Lain Entralgo 4 Chalet 4"
    assert m == "W-02W4PJ"


def test_parse_folder_guion_con_espacios():
    d, m = parse_ev_folder_name("Gran Via 40, 3º 1ª - W-030LFT")
    assert d == "Gran Via 40, 3º 1ª"
    assert m == "W-030LFT"


def test_parse_folder_guion_largo():
    d, m = parse_ev_folder_name("Serrano 45, 2º Izq – W-04ABCD")
    assert d == "Serrano 45, 2º Izq"
    assert m == "W-04ABCD"


def test_parse_folder_mls_en_minusculas():
    """El ID GO debe normalizarse a mayúsculas."""
    d, m = parse_ev_folder_name("Calle Mayor 1 - w-030lft")
    assert m == "W-030LFT"


def test_parse_folder_sin_codigo_w():
    """Sin código W-XXXXXX devuelve cadenas vacías."""
    d, m = parse_ev_folder_name("Carpeta sin referencia")
    assert d == ""
    assert m == ""


def test_parse_folder_solo_codigo():
    """Solo código sin dirección: dirección vacía."""
    d, m = parse_ev_folder_name("- W-030LFT")
    assert m == "W-030LFT"


def test_parse_folder_espacios_extra():
    """Espacios extra al principio/final no deben afectar."""
    d, m = parse_ev_folder_name("  Av. Diagonal 500  -  W-XYZABC  ")
    assert d == "Av. Diagonal 500"
    assert m == "W-XYZABC"


def test_parse_folder_sufijo_consultor_captador():
    """Carpeta con sufijo `- <nombre consultor captador>` después del ID GO.

    Caso real Sevilla SeRS6 (W-02RRO3): E&V añade el nombre del consultor
    que captó la propiedad al final del nombre de la carpeta, tras el
    W-XXXXXX. NO es el cliente — es un empleado de E&V. El sufijo se
    descarta para el auto-fill; la dirección debe extraerse igualmente.
    """
    d, m = parse_ev_folder_name(
        "393. Hacienda Vadillo - W-02RRO3 - Natalia Trujillano"
    )
    assert d == "393. Hacienda Vadillo"
    assert m == "W-02RRO3"


def test_parse_folder_sufijo_con_guion_largo():
    """Variante con guion largo (–) tanto antes como después del ID GO."""
    d, m = parse_ev_folder_name(
        "Serrano 45, 2º Izq – W-04ABCD – Juan Pérez"
    )
    assert d == "Serrano 45, 2º Izq"
    assert m == "W-04ABCD"


# ---------------------------------------------------------------------------
# get_drive_folder_info
# ---------------------------------------------------------------------------

def _mock_rclone_token(monkeypatch, token: str | None = "fake_access_token"):
    """Mock de subprocess.run que simula `rclone config show gdrive_ev` con token."""
    token_json = f'{{"access_token": "{token}"}}' if token else "{}"
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = f"[gdrive_ev]\ntoken = {token_json}\n"
    mock.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)


class TestGetDriveFolderInfo:
    def test_ok_devuelve_name_y_drive_id(self, monkeypatch):
        """Cuando rclone y la API responden correctamente, devuelve DriveFolderInfo."""
        _mock_rclone_token(monkeypatch)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "name": "Gran Via 40, 3º 1ª - W-030LFT",
            "driveId": "0AJbQHw3Fn24RUk9PVA",
        }

        with patch("httpx.get", return_value=mock_resp):
            info = get_drive_folder_info("folderXYZ123456")

        assert isinstance(info, DriveFolderInfo)
        assert info.name == "Gran Via 40, 3º 1ª - W-030LFT"
        assert info.drive_id == "0AJbQHw3Fn24RUk9PVA"

    def test_sin_token_devuelve_none(self, monkeypatch):
        """Si rclone no devuelve token, la función devuelve None sin llamar a httpx."""
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "[gdrive_ev]\nscope = drive\n"  # sin línea token
        mock.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)

        with patch("httpx.get") as mock_get:
            result = get_drive_folder_info("folderXYZ123456")

        assert result is None
        mock_get.assert_not_called()

    def test_api_error_401_devuelve_none(self, monkeypatch):
        """Si la Drive API devuelve 401, la función devuelve None."""
        _mock_rclone_token(monkeypatch)

        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("httpx.get", return_value=mock_resp):
            result = get_drive_folder_info("folderXYZ123456")

        assert result is None

    def test_rclone_falla_devuelve_none(self, monkeypatch):
        """Si subprocess.run lanza excepción, devuelve None sin propagar."""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: (_ for _ in ()).throw(OSError("rclone not found")))

        result = get_drive_folder_info("folderXYZ123456")
        assert result is None

    def test_nombre_vacio_devuelve_none(self, monkeypatch):
        """Si la API devuelve name vacío, devuelve None (carpeta sin nombre no es útil)."""
        _mock_rclone_token(monkeypatch)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "", "driveId": "0AJbQHw3Fn24RUk9PVA"}

        with patch("httpx.get", return_value=mock_resp):
            result = get_drive_folder_info("folderXYZ123456")

        assert result is None
