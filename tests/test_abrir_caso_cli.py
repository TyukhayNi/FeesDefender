import hashlib
import re
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

    # Mock del pull: deposita 2 ficheros en 00_Input/01_Drive EV (+ el marcador
    # de control .pulled, como haría pull_drive_ev de verdad) y devuelve un stub
    def fake_pull(case_id, folder_id, team_id, *, force=False):
        dest = case_locator.path_for(case_id) / "00_Input" / "01_Drive EV" / "ACTIVACION"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "hoja.pdf").write_bytes(b"contenido-1")
        (dest.parent / "oferta.pdf").write_bytes(b"contenido-2")
        (dest.parent / ".pulled").write_text('{"team_id": "TID"}', encoding="utf-8")
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


def test_cli_fuente_drive_ev_explicita_equivale_a_default(drive_temporal):
    """--fuente drive_ev explícito da el mismo resultado que el default."""
    result = CliRunner().invoke(cli.app, _args(fuente="drive_ev"))
    assert result.exit_code == 0, result.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    eventos = intake_log.read_events(case_id)
    assert any(e["event"] == "pull_drive_ev" for e in eventos)


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


def test_cli_persiste_id_go_para_resolve_ref(drive_temporal):
    """El --w-code debe quedar en meta.id_go de _caso.md.

    Bug real (2026-07-17, caso VaRS3/W-02TH0W): abrir_caso.py nunca pasaba
    id_go a ensure_case(), así que resolve_ref(w_code) no encontraba el caso
    y scripts/export_label_emails.py creaba una carpeta nueva (stray) en vez
    de escribir en el caso real.
    """
    result = CliRunner().invoke(cli.app, _args())
    assert result.exit_code == 0, result.output

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    assert case_locator.resolve_ref("W-02Z2NR") == case_id


def test_cli_idempotente_no_dobla_intake_ni_crm(drive_temporal, monkeypatch):
    """§8: una segunda pasada completa (mismo w_code, --force para superar la
    guarda de colisión) no debe volver a dar de alta en el CRM ni duplicar el
    evento de intake. --force es necesario porque, sin él, la segunda pasada
    ni siquiera llega a la fase de CRM (se corta en ColisionCaso); con él,
    ejerce de verdad la guarda de idempotencia del §8 (Fix B)."""
    llamadas = {"crm": 0}
    def contando(dto, **kw):
        llamadas["crm"] += 1
        return "9999"
    monkeypatch.setattr("core.sudespacho_create.create_expediente", contando)

    r1 = CliRunner().invoke(cli.app, _args())
    assert r1.exit_code == 0, r1.output
    r2 = CliRunner().invoke(cli.app, _args() + ["--force"])
    assert r2.exit_code == 0, r2.output

    # create_expediente se llamó exactamente una vez en las dos corridas: la
    # guarda de idempotencia del CLI (Fix B) evitó la re-alta en la 2ª pasada.
    assert llamadas["crm"] == 1

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    case_dir = case_locator.path_for(case_id)
    fm_txt = (case_dir / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    import yaml
    fm = yaml.safe_load(fm_txt.split("---")[1])
    # una sola entrada CRM pese a dos corridas
    assert len(fm["meta"]["sudespacho_expedientes"]) == 1

    # la 2ª pasada no tiene depositables nuevos (todo dup) → no nuevo evento
    eventos = intake_log.read_events(case_id)
    pulls = [e for e in eventos if e["event"] == "pull_drive_ev"]
    assert len(pulls) == 1


def test_cli_dry_run_no_escribe_crm(drive_temporal, monkeypatch):
    llamadas = {"crm": 0}
    monkeypatch.setattr("core.sudespacho_create.create_expediente",
                        lambda dto, **kw: llamadas.__setitem__("crm", llamadas["crm"] + 1) or "9999")
    result = CliRunner().invoke(cli.app, _args() + ["--dry-run"])
    assert result.exit_code == 0
    assert llamadas["crm"] == 0


def test_cli_crm_falla_no_rompe_pipeline(drive_temporal, monkeypatch):
    """§9: si el alta CRM revienta, Drive+intake ya completados no se pierden;
    el CLI termina en exit 0 y avisa de la referencia pendiente."""
    def revienta(dto, **kw):
        raise RuntimeError("CRM 500")
    monkeypatch.setattr("core.sudespacho_create.create_expediente", revienta)

    result = CliRunner().invoke(cli.app, _args())
    assert result.exit_code == 0, result.output
    assert "AVISO" in result.output
    assert "referencia_crm queda pendiente" in result.output


def test_cli_crm_skip(drive_temporal, monkeypatch):
    llamadas = {"crm": 0}
    monkeypatch.setattr("core.sudespacho_create.create_expediente",
                        lambda dto, **kw: llamadas.__setitem__("crm", llamadas["crm"] + 1) or "9999")
    result = CliRunner().invoke(cli.app, _args(crm="skip"))
    assert result.exit_code == 0, result.output
    assert llamadas["crm"] == 0
    assert "CRM omitido" in result.output


def test_cli_colision_sin_force_exit_1(drive_temporal):
    r1 = CliRunner().invoke(cli.app, _args())
    assert r1.exit_code == 0, r1.output

    r2 = CliRunner().invoke(cli.app, _args())
    assert r2.exit_code == 1
    assert "[ERROR]" in r2.output
    assert "ya existe" in r2.output


def test_hash_tree_local_excluye_ficheros_de_control(tmp_path: Path):
    """IMPORTANT 2: .pulled / _inventory.json / .synced no son documento."""
    root = tmp_path / "01_Drive EV"
    root.mkdir(parents=True)
    (root / "a.txt").write_bytes(b"hola")
    (root / ".pulled").write_text('{"team_id": "TID"}', encoding="utf-8")
    (root / "_inventory.json").write_text("{}", encoding="utf-8")
    (root / ".synced").write_text("", encoding="utf-8")

    hashes = cli.hash_tree_local(root, prefijo="01_Drive EV")

    assert list(hashes) == ["01_Drive EV/a.txt"]


def test_cli_excluye_pulled_del_ledger(drive_temporal):
    """IMPORTANT 2: `.pulled` (escrito por pull_drive_ev) no debe colarse en
    el evento pull_drive_ev del log forense ni contar como depositable."""
    result = CliRunner().invoke(cli.app, _args())
    assert result.exit_code == 0, result.output

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    eventos = intake_log.read_events(case_id)
    pulls = [e for e in eventos if e["event"] == "pull_drive_ev"]
    assert pulls
    files = pulls[-1]["details"]["files"]
    assert not any(f["path"].endswith(".pulled") for f in files)
    # solo hoja.pdf + oferta.pdf: el .pulled del fixture queda excluido
    assert len(files) == 2


def test_cli_ciudad_desconocida_exit_1(drive_temporal):
    result = CliRunner().invoke(cli.app, _args(ciudad="Atlantis"))
    assert result.exit_code == 1
    assert "[ERROR]" in result.output
    assert "Ciudad desconocida" in result.output


def test_cli_dry_run_es_honesto_sobre_lo_ejecutado(drive_temporal, monkeypatch):
    """MINOR 2: dry-run SÍ crea el esqueleto y SÍ ejecuta el pull (el plan
    necesita el inventario); solo se omiten el log de intake y el alta CRM."""
    llamadas = {"crm": 0}
    monkeypatch.setattr(
        "core.sudespacho_create.create_expediente",
        lambda dto, **kw: llamadas.__setitem__("crm", llamadas["crm"] + 1) or "9999",
    )
    result = CliRunner().invoke(cli.app, _args() + ["--dry-run"])
    assert result.exit_code == 0, result.output
    assert llamadas["crm"] == 0

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    case_dir = case_locator.path_for(case_id)
    assert case_dir.is_dir()
    assert (case_dir / "00_Input" / "01_Drive EV" / "ACTIVACION" / "hoja.pdf").is_file()

    eventos = intake_log.read_events(case_id)
    pulls = [e for e in eventos if e["event"] == "pull_drive_ev"]
    assert pulls == []


def _args_min(**over):
    """Args base SIN los flags específicos de drive_ev (folder-id/team-id)."""
    base = [
        "--w-code", "W-02Z2NR", "--ciudad", "Barcelona", "--tipo-caso", "VUELTA",
        "--codigo-caso", "BaRS11", "--sufijo", "Vuelta",
        "--direccion", "Passeig Marítim 30", "--yes",
    ]
    for k, v in over.items():
        base += [f"--{k}", v]
    return base


def test_cli_manual_sin_src_exit_1(drive_temporal):
    result = CliRunner().invoke(cli.app, _args_min(fuente="manual"))
    assert result.exit_code == 1
    assert "--src" in result.output


def test_cli_whatsapp_sin_rol_exit_1(drive_temporal, tmp_path):
    z = tmp_path / "x.zip"
    z.write_bytes(b"PK")
    result = CliRunner().invoke(cli.app, _args_min(fuente="whatsapp", src=str(z)))
    assert result.exit_code == 1
    assert "--rol" in result.output


def test_cli_email_flags_ajenos_exit_1(drive_temporal):
    """email con --src (ajeno) debe fallar."""
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="email", cuenta="a@b.com", label="Caso", src="/x"))
    assert result.exit_code == 1
    assert "ajeno" in result.output.lower()


def test_cli_whatsapp_rol_invalido_exit_1(drive_temporal, tmp_path):
    z = tmp_path / "x.zip"
    z.write_bytes(b"PK")
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="whatsapp", src=str(z), rol="99_Inexistente"))
    assert result.exit_code == 1
    assert "rol" in result.output.lower()


def _crear_carpeta_manual(tmp_path):
    src = tmp_path / "aportado"
    (src / "sub").mkdir(parents=True)
    (src / "escrito.pdf").write_bytes(b"ESCRITO")
    (src / "sub" / "anexo.pdf").write_bytes(b"ANEXO")
    return src


def _lotes_manual(case_dir: Path) -> list[Path]:
    """Subcarpetas de lote manual (`<AAAA-MM-DD>_manual_NN`) bajo 00_Input/."""
    input_dir = case_dir / "00_Input"
    if not input_dir.is_dir():
        return []
    return sorted(p for p in input_dir.iterdir() if p.is_dir() and "_manual_" in p.name)


def test_cli_manual_carpeta_deposita_y_loguea(drive_temporal, tmp_path):
    src = _crear_carpeta_manual(tmp_path)
    result = CliRunner().invoke(cli.app, _args_min(fuente="manual", src=str(src)) + ["--crm", "skip"])
    assert result.exit_code == 0, result.output

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    case_dir = case_locator.path_for(case_id)
    lotes = _lotes_manual(case_dir)
    assert len(lotes) == 1
    assert (lotes[0] / "escrito.pdf").is_file()
    assert (lotes[0] / "sub" / "anexo.pdf").is_file()

    eventos = intake_log.read_events(case_id)
    manuales = [e for e in eventos if e["event"] == "upload_manual"]
    assert manuales and len(manuales[-1]["details"]["files"]) == 2
    assert all(f["sha256"] for f in manuales[-1]["details"]["files"])
    assert all(f["path"].startswith(f"{lotes[0].name}/") for f in manuales[-1]["details"]["files"])


def test_cli_manual_zip_deposita(drive_temporal, tmp_path):
    import zipfile as _zf
    z = tmp_path / "aportado.zip"
    with _zf.ZipFile(z, "w") as zf:
        zf.writestr("carpeta/doc.pdf", b"DOC")
    result = CliRunner().invoke(cli.app, _args_min(fuente="manual", src=str(z)) + ["--crm", "skip"])
    assert result.exit_code == 0, result.output
    case_dir = case_locator.path_for("BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta")
    lotes = _lotes_manual(case_dir)
    assert len(lotes) == 1
    assert (lotes[0] / "carpeta" / "doc.pdf").is_file()


def test_cli_manual_dry_run_no_deposita(drive_temporal, tmp_path):
    src = _crear_carpeta_manual(tmp_path)
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="manual", src=str(src)) + ["--dry-run"])
    assert result.exit_code == 0, result.output
    case_dir = case_locator.path_for("BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta")
    # dry-run no reserva lote (ni siquiera esqueleto 00_Input/ para esta fuente)
    assert _lotes_manual(case_dir) == []


def test_cli_manual_reentrante_dedup(drive_temporal, tmp_path):
    src = _crear_carpeta_manual(tmp_path)
    a = _args_min(fuente="manual", src=str(src)) + ["--crm", "skip"]
    r1 = CliRunner().invoke(cli.app, a)
    assert r1.exit_code == 0, r1.output
    r2 = CliRunner().invoke(cli.app, a + ["--force"])
    assert r2.exit_code == 0, r2.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    manuales = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_manual"]
    # 2ª pasada: todo dup → no nuevo evento
    assert len(manuales) == 1


def test_cli_manual_src_inexistente_exit_1(drive_temporal):
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="manual", src="/no/existe/ruta") + ["--crm", "skip"])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output


def _sin_yes(**over) -> list[str]:
    return [a for a in _args(**over) if a != "--yes"]


def test_cli_codigo_duplicado_declina_confirmacion_exit_1(drive_temporal):
    """MINOR 3: colisión de código (§ requiere_confirmacion) declinada por el
    usuario (input 'n') debe abortar con exit 1."""
    case_manager.ensure_case(
        "BaRS11 - Otra (W-VIEJO1) - Vuelta",
        titulo="x", tipo_caso="VUELTA", ciudad="Barcelona", direccion="Otra",
    )
    result = CliRunner().invoke(cli.app, _sin_yes(), input="n\n")
    assert result.exit_code == 1
    assert "[AVISO]" in result.output
    assert "ya existe" in result.output


def test_cli_crm_gate_declinado_exit_0(drive_temporal, monkeypatch):
    """MINOR 3: gate CRM declinado (input 'n') no llama a create_expediente y
    termina en exit 0 (Drive + intake ya completados)."""
    llamadas = {"crm": 0}
    monkeypatch.setattr(
        "core.sudespacho_create.create_expediente",
        lambda dto, **kw: llamadas.__setitem__("crm", llamadas["crm"] + 1) or "9999",
    )
    result = CliRunner().invoke(cli.app, _sin_yes(), input="n\n")
    assert result.exit_code == 0, result.output
    assert llamadas["crm"] == 0
    assert "declinado" in result.output


def test_cli_whatsapp_delega_en_deposit_export(drive_temporal, tmp_path, monkeypatch):
    z = tmp_path / "chat.zip"
    z.write_bytes(b"PK\x03\x04fake")
    llamadas = {}

    def spy(case_id, rol_subdir, content, *, zip_name, **kw):
        llamadas.update(case_id=case_id, rol=rol_subdir, n=len(content), zip_name=zip_name)
        return type("R", (), {"skipped_dedup": False, "chat_dir": tmp_path})()

    monkeypatch.setattr("core.whatsapp_intake.deposit_export", spy)
    result = CliRunner().invoke(
        cli.app,
        _args_min(fuente="whatsapp", src=str(z), rol="00_Consultor propietario") + ["--crm", "skip"],
    )
    assert result.exit_code == 0, result.output
    assert llamadas["rol"] == "00_Consultor propietario"
    assert llamadas["case_id"] == "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    assert llamadas["n"] > 0
    # el orquestador NO emite un segundo evento (lo hace deposit_export, aquí mockeado)
    eventos = intake_log.read_events(llamadas["case_id"])
    assert [e for e in eventos if e["event"] == "upload_whatsapp"] == []


def test_cli_whatsapp_dry_run_no_llama(drive_temporal, tmp_path, monkeypatch):
    z = tmp_path / "chat.zip"
    z.write_bytes(b"PK")
    llamado = {"v": False}
    monkeypatch.setattr("core.whatsapp_intake.deposit_export",
                        lambda *a, **k: llamado.__setitem__("v", True))
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="whatsapp", src=str(z), rol="03_Otros") + ["--dry-run"])
    assert result.exit_code == 0, result.output
    assert llamado["v"] is False


def test_cli_email_delega_en_export_label(drive_temporal, monkeypatch):
    llamadas = {}

    def spy(account, label, dest_dir, *, case_id=None, **kw):
        llamadas.update(account=account, label=label, dest=str(dest_dir), case_id=case_id)
        return type("R", (), {})()

    monkeypatch.setattr("core.email_export.export_label", spy)
    result = CliRunner().invoke(
        cli.app,
        _args_min(fuente="email", cuenta="mails@x.example", label="Caso W") + ["--crm", "skip"],
    )
    assert result.exit_code == 0, result.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    assert llamadas["account"] == "mails@x.example"
    assert llamadas["label"] == "Caso W"
    assert llamadas["case_id"] == case_id
    dest_posix = llamadas["dest"].replace("\\", "/")
    assert re.search(r"/00_Input/\d{4}-\d{2}-\d{2}_email_\d{2}$", dest_posix), dest_posix
    # el orquestador NO emite un segundo evento (lo hace export_label, aquí mockeado)
    eventos = intake_log.read_events(case_id)
    assert [e for e in eventos if e["event"] == "upload_email"] == []


def test_cli_email_dry_run_no_llama(drive_temporal, monkeypatch):
    llamado = {"v": False}
    monkeypatch.setattr("core.email_export.export_label",
                        lambda *a, **k: llamado.__setitem__("v", True))
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="email", cuenta="a@x.example", label="L") + ["--dry-run"])
    assert result.exit_code == 0, result.output
    assert llamado["v"] is False


def test_cli_whatsapp_dedup_reporta(drive_temporal, tmp_path, monkeypatch):
    z = tmp_path / "chat.zip"
    z.write_bytes(b"PKdup")
    monkeypatch.setattr(
        "core.whatsapp_intake.deposit_export",
        lambda *a, **k: type("R", (), {"skipped_dedup": True, "chat_dir": tmp_path})())
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="whatsapp", src=str(z), rol="03_Otros") + ["--crm", "skip"])
    assert result.exit_code == 0, result.output
    assert "dedup" in result.output.lower() or "ya importado" in result.output.lower()
