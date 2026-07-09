import hashlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from core import case_manager, intake_log
from core.casos import case_locator
from scripts import abrir_caso as cli


def test_hash_tree_local(tmp_path: Path):
    root = tmp_path / "01_Drive EV"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_bytes(b"hola")
    (root / "sub" / "b.txt").write_bytes(b"mundo")

    hashes = cli.hash_tree_local(root, prefijo="01_Drive EV")

    assert hashes["01_Drive EV/a.txt"] == hashlib.sha256(b"hola").hexdigest()
    assert hashes["01_Drive EV/sub/b.txt"] == hashlib.sha256(b"mundo").hexdigest()
    assert len(hashes) == 2


@pytest.fixture
def drive_temporal(tmp_path, monkeypatch):
    """Apunta CASOS_ROOT al tmp y mockea el pull rclone y el alta CRM."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    # Mock del pull: deposita 2 ficheros en 00_Input/01_Drive EV y devuelve un stub
    def fake_pull(case_id, folder_id, team_id, *, force=False):
        dest = case_locator.path_for(case_id) / "00_Input" / "01_Drive EV" / "ACTIVACION"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "hoja.pdf").write_bytes(b"contenido-1")
        (dest.parent / "oferta.pdf").write_bytes(b"contenido-2")
        return type("R", (), {"count": 2})()

    monkeypatch.setattr("core.intake_drive.pull_drive_ev", fake_pull)
    monkeypatch.setattr("core.sudespacho_create.create_expediente", lambda dto, **kw: "9999")
    return root


def _args(**over):
    base = [
        "--w-code", "W-02Z2NR", "--ciudad", "Barcelona", "--tipo-caso", "VUELTA",
        "--codigo-caso", "BaRS11", "--sufijo", "Vuelta",
        "--direccion", "Passeig Marítim 30",
        "--folder-id", "FID", "--team-id", "TID", "--yes",
    ]
    for k, v in over.items():
        base += [f"--{k}", v]
    return base


def test_cli_pasada_completa_crea_intake_log_y_crm(drive_temporal):
    result = CliRunner().invoke(cli.app, _args())
    assert result.exit_code == 0, result.output

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    case_dir = case_locator.path_for(case_id)
    assert (case_dir / "00_Input" / "01_Drive EV" / "ACTIVACION" / "hoja.pdf").is_file()

    # evento pull_drive_ev con sha256 por fichero (D4)
    eventos = intake_log.read_events(case_id)
    pulls = [e for e in eventos if e["event"] == "pull_drive_ev"]
    assert pulls and pulls[-1]["details"]["files"]
    assert all(f["sha256"] for f in pulls[-1]["details"]["files"])

    # CRM registrado en _caso.md
    import yaml
    fm = yaml.safe_load((case_dir / "00_Input" / "_caso.md").read_text(encoding="utf-8").split("---")[1])
    ids = [e["id"] for e in fm["meta"]["sudespacho_expedientes"]]
    assert "9999" in ids


def test_cli_idempotente_no_dobla_intake_ni_crm(drive_temporal, monkeypatch):
    llamadas = {"crm": 0}
    def contando(dto, **kw):
        llamadas["crm"] += 1
        return "9999"
    monkeypatch.setattr("core.sudespacho_create.create_expediente", contando)

    CliRunner().invoke(cli.app, _args())
    CliRunner().invoke(cli.app, _args())

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    fm_txt = (case_locator.path_for(case_id) / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    import yaml
    fm = yaml.safe_load(fm_txt.split("---")[1])
    # una sola entrada CRM pese a dos corridas (register_expediente es idempotente)
    assert len(fm["meta"]["sudespacho_expedientes"]) == 1


def test_cli_dry_run_no_escribe_crm(drive_temporal, monkeypatch):
    llamadas = {"crm": 0}
    monkeypatch.setattr("core.sudespacho_create.create_expediente",
                        lambda dto, **kw: llamadas.__setitem__("crm", llamadas["crm"] + 1) or "9999")
    result = CliRunner().invoke(cli.app, _args() + ["--dry-run"])
    assert result.exit_code == 0
    assert llamadas["crm"] == 0
