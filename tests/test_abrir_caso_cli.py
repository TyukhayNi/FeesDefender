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


def test_cli_case_id_resuelve_identidad_por_wcode(drive_temporal, tmp_path):
    # 1) Crear el caso con una pasada normal (drive_ev).
    r1 = CliRunner().invoke(cli.app, _args())
    assert r1.exit_code == 0, r1.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"

    # 2) Intake incremental con --case-id (W-code) + fuente manual, sin repetir los 6 flags.
    src = tmp_path / "extra"
    src.mkdir()
    (src / "nota.txt").write_bytes(b"contenido incremental")
    r2 = CliRunner().invoke(cli.app, [
        "--case-id", "W-02Z2NR", "--fuente", "manual", "--src", str(src), "--yes",
    ])
    assert r2.exit_code == 0, r2.output

    # El intake fue al MISMO caso (no una carpeta nueva) y se logeó upload_manual.
    eventos = intake_log.read_events(case_id)
    assert any(e["event"] == "upload_manual" for e in eventos)


def test_cli_case_id_excluyente_con_flags_de_identidad(drive_temporal):
    r = CliRunner().invoke(cli.app, [
        "--case-id", "W-02Z2NR", "--w-code", "W-02Z2NR",
        "--fuente", "manual", "--src", "x", "--yes",
    ])
    assert r.exit_code != 0
    assert "excluyente" in r.output.lower()


def test_cli_sin_case_id_ni_flags_falla(drive_temporal):
    r = CliRunner().invoke(cli.app, ["--fuente", "manual", "--src", "x", "--yes"])
    assert r.exit_code != 0
    assert "identidad" in r.output.lower()


def test_cli_case_id_caso_inexistente_falla(drive_temporal, tmp_path):
    src = tmp_path / "e"
    src.mkdir()
    (src / "a.txt").write_bytes(b"x")
    r = CliRunner().invoke(cli.app, [
        "--case-id", "W-NOEXISTE", "--fuente", "manual", "--src", str(src), "--yes",
    ])
    assert r.exit_code != 0
    assert "no encontrado" in r.output.lower()


def test_cli_case_id_formato_no_canonico_falla_limpio(drive_temporal, tmp_path):
    """[Finding #1b] Un case_id existente (con `_caso.md`) pero cuyo nombre de
    carpeta no sigue la gramática canónica (legacy: doble espacio, sin
    `(W-...)`) debe fallar con [ERROR] limpio, no con un ValueError sin capturar."""
    nombre_legacy = "BaRS11 - Legacy  Address - Vuelta"
    case_manager.ensure_case(
        nombre_legacy, titulo=nombre_legacy, referencia_crm=nombre_legacy,
        tipo_caso="VUELTA", ciudad="Barcelona", direccion="Legacy  Address",
    )
    src = tmp_path / "e"
    src.mkdir()
    (src / "a.txt").write_bytes(b"x")

    r = CliRunner().invoke(cli.app, [
        "--case-id", nombre_legacy, "--fuente", "manual", "--src", str(src), "--yes",
    ])

    assert r.exit_code != 0
    assert r.exception is None or isinstance(r.exception, SystemExit)
    assert "[ERROR]" in r.output


def _args_b5_autoderivar(**over):
    """Args de drive_ev SIN los 3 flags auto-derivables (codigo/sufijo/team)."""
    base = [
        "--w-code", "W-02Z2NR", "--ciudad", "Barcelona", "--tipo-caso", "VUELTA",
        "--direccion", "Passeig Marítim 30", "--folder-id", "FID", "--yes",
    ]
    for k, v in over.items():
        base += [f"--{k}", v]
    return base


def _mock_drive_info(monkeypatch, *, drive_id="DRIVEID", unidad="Barcelona - S3 "):
    from core.intake_drive import DriveFolderInfo
    monkeypatch.setattr(
        "core.intake_drive.get_drive_folder_info",
        lambda fid: DriveFolderInfo(name="carpeta", drive_id=drive_id),
    )
    monkeypatch.setattr(
        "core.intake_drive.get_shared_drive_name",
        lambda did: unidad,
    )


def test_cli_drive_ev_autoderiva_codigo_team_sufijo(drive_temporal, monkeypatch):
    _mock_drive_info(monkeypatch, drive_id="DRIVEID", unidad="Barcelona - S3 ")
    captura = {}
    def fake_pull(case_id, folder_id, team_id, *, force=False):
        captura["case_id"] = case_id
        captura["team_id"] = team_id
        dest = case_locator.path_for(case_id) / "00_Input" / "01_Drive EV"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "a.pdf").write_bytes(b"x")
        (dest / ".pulled").write_text("{}", encoding="utf-8")
        return type("R", (), {"count": 1})()
    monkeypatch.setattr("core.intake_drive.pull_drive_ev", fake_pull)

    result = CliRunner().invoke(cli.app, _args_b5_autoderivar(crm="skip"))

    assert result.exit_code == 0, result.output
    # código BaRS3 (de "Barcelona - S3") + sufijo "Vuelta" (de VUELTA)
    assert "BaRS3 - Passeig Marítim 30 (W-02Z2NR) - Vuelta" in captura["case_id"]
    assert captura["team_id"] == "DRIVEID"  # team_id = driveId


def test_cli_drive_ev_flags_explicitos_ganan(drive_temporal, monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("no debe llamar a la Drive API con todo explícito")
    monkeypatch.setattr("core.intake_drive.get_drive_folder_info", boom)
    monkeypatch.setattr("core.intake_drive.get_shared_drive_name", boom)
    # _args() trae los 3 flags explícitos (BaRS11 / Vuelta / TID)
    result = CliRunner().invoke(cli.app, _args(crm="skip"))
    assert result.exit_code == 0, result.output
    caso = next(case_locator.path_for(p.name) for p in case_locator.list_cases("Barcelona"))
    assert "BaRS11" in caso.name  # ganó el flag, no un derivado


def test_cli_drive_ev_codigo_no_derivable_error(drive_temporal, monkeypatch):
    # unidad ambigua -> codigo_de_unidad None -> falta --codigo-caso -> exit 1
    _mock_drive_info(monkeypatch, unidad="Sevilla - S1 / S6")
    result = CliRunner().invoke(cli.app, _args_b5_autoderivar(crm="skip"))
    assert result.exit_code == 1
    assert "--codigo-caso" in result.output


def test_cli_drive_ev_folder_info_none_degrada_limpio(drive_temporal, monkeypatch):
    monkeypatch.setattr("core.intake_drive.get_drive_folder_info", lambda fid: None)
    result = CliRunner().invoke(cli.app, _args_b5_autoderivar(crm="skip"))
    assert result.exit_code == 1
    assert "--codigo-caso" in result.output  # error de flags, no traceback


def test_cli_drive_ev_sufijo_autoderivado_sin_api(drive_temporal, monkeypatch):
    # codigo y team explícitos -> no se toca la Drive API; solo se deriva sufijo
    def boom(*a, **kw):
        raise AssertionError("no debe llamar a la Drive API")
    monkeypatch.setattr("core.intake_drive.get_drive_folder_info", boom)
    monkeypatch.setattr("core.intake_drive.get_shared_drive_name", boom)
    result = CliRunner().invoke(
        cli.app,
        _args_b5_autoderivar(**{"codigo-caso": "BaRS11", "team-id": "TID", "crm": "skip"}),
    )
    assert result.exit_code == 0, result.output
    caso = next(case_locator.path_for(p.name) for p in case_locator.list_cases("Barcelona"))
    assert caso.name.endswith("- Vuelta")  # sufijo derivado de VUELTA


def test_cli_case_id_drive_ev_autoderiva_team_id(drive_temporal, monkeypatch):
    """B5: la vía --case-id (re-pull) no pasa por _autoderivar_drive_ev, pero el
    bloque común 5.1.b deriva --team-id del driveId de --folder-id."""
    # 1) Crear el caso con una pasada normal (drive_ev, con --team-id explícito).
    r1 = CliRunner().invoke(cli.app, _args())
    assert r1.exit_code == 0, r1.output

    # 2) Re-pull con --case-id y SIN --team-id: se auto-deriva del driveId.
    from core.intake_drive import DriveFolderInfo
    monkeypatch.setattr(
        "core.intake_drive.get_drive_folder_info",
        lambda fid: DriveFolderInfo(name="x", drive_id="DRIVEID2"),
    )
    captura = {}
    def fake_pull(case_id, folder_id, team_id, *, force=False):
        captura["team_id"] = team_id
        dest = case_locator.path_for(case_id) / "00_Input" / "01_Drive EV"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "nuevo.pdf").write_bytes(b"contenido-nuevo")
        return type("R", (), {"count": 1})()
    monkeypatch.setattr("core.intake_drive.pull_drive_ev", fake_pull)

    r2 = CliRunner().invoke(cli.app, [
        "--case-id", "W-02Z2NR", "--fuente", "drive_ev", "--folder-id", "FID",
        "--crm", "skip", "--yes",
    ])
    assert r2.exit_code == 0, r2.output
    assert captura["team_id"] == "DRIVEID2"  # team_id derivado del driveId


def test_cli_drive_ev_team_id_no_derivable_error_limpio(drive_temporal, monkeypatch):
    """B5 invariante: si --team-id se omite y no se puede derivar (token/red),
    error LIMPIO (exit 1 + menciona --team-id), NUNCA un TypeError de rclone."""
    monkeypatch.setattr("core.intake_drive.get_drive_folder_info", lambda fid: None)
    def boom(*a, **kw):
        raise AssertionError("no debe llegar al pull con team_id=None")
    monkeypatch.setattr("core.intake_drive.pull_drive_ev", boom)

    # 6 flags con --codigo-caso explícito (faltan pasa), pero --team-id omitido
    # y get_drive_folder_info=None -> no se deriva -> error limpio en 5.1.b.
    result = CliRunner().invoke(
        cli.app, _args_b5_autoderivar(**{"codigo-caso": "BaRS11", "crm": "skip"}))
    assert result.exit_code == 1
    assert "--team-id" in result.output
    assert not isinstance(result.exception, TypeError)


# --- Intake de correo: el flag de extracción de adjuntos llega al motor (MEJORAS #68.a) ---

@pytest.fixture
def export_label_espia(tmp_path, monkeypatch):
    """Captura los kwargs con que `_intake_email` llama a `export_label` (sin red)."""
    capturado: dict = {}

    def fake_export(cuenta, label, dest, **kw):
        capturado.update(kw)
        return type("R", (), {"messages": 0, "attachments": 0})()

    monkeypatch.setattr(cli.email_export, "email_dest_dir", lambda case_id: tmp_path / "lote")
    monkeypatch.setattr(cli.email_export, "export_label", fake_export)
    return capturado


def _ident_email():
    return type("I", (), {"case_id": "BaRS9 - Calle Falsa 1 (W-02VUDR) - Art 20 LAU"})()


def test_intake_email_propaga_extraer_adjuntos_al_motor(tmp_path, export_label_espia):
    cli._intake_email(_ident_email(), tmp_path, "c@x", "01. CONTING/X",
                      dry_run=False, extraer_adjuntos=True)

    assert export_label_espia["extract_attachments"] is True


def test_intake_email_no_extrae_adjuntos_por_defecto(tmp_path, export_label_espia):
    """El default NO cambia: activarlo mueve la superficie de dedup de todo intake
    futuro, así que es decisión explícita de quien abre el caso."""
    cli._intake_email(_ident_email(), tmp_path, "c@x", "01. CONTING/X", dry_run=False)

    assert export_label_espia["extract_attachments"] is False


def test_cli_extraer_adjuntos_llega_al_intake_de_email(drive_temporal, monkeypatch):
    """Cablear el flag en el CLI: sin esto, exponerlo en `_intake_email` no sirve."""
    capturado: dict = {}

    def espia(ident, case_dir, cuenta, label, *, dry_run, extraer_adjuntos=False):
        capturado["extraer"] = extraer_adjuntos

    monkeypatch.setattr(cli, "_intake_email", espia)

    result = CliRunner().invoke(cli.app, _args_min(
        fuente="email", cuenta="c@x", label="01. CONTING/X", crm="skip"
    ) + ["--extraer-adjuntos"])

    assert result.exit_code == 0, result.output
    assert capturado["extraer"] is True
