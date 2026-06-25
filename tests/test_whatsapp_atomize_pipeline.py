from pathlib import Path

from core.whatsapp_atomize.pipeline import atomize_whatsapp_case, descubrir_chats


CHAT = (
    "[30/10/2024, 10:00:00] Juan: Hola\n"
    "[30/10/2024, 10:01:00] Ana: El 14 may 2024, a las 9:00, Pe <pe@ej.com> escribió:\n"
    "Mira esto\n"
)


def _montar_caso(tmp_path) -> Path:
    chat_dir = tmp_path / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x"
    chat_dir.mkdir(parents=True)
    (chat_dir / "_chat.txt").write_text(CHAT, encoding="utf-8")
    return tmp_path


def test_descubrir_chats(tmp_path):
    caso = _montar_caso(tmp_path)
    chats = descubrir_chats(caso)
    assert len(chats) == 1 and chats[0].name == "chat-x"


def test_atomize_genera_salida_y_no_toca_input(tmp_path, monkeypatch):
    caso = _montar_caso(tmp_path)
    import core.whatsapp_atomize.pipeline as pl
    monkeypatch.setattr(pl, "caso_path", lambda cid: caso)
    input_antes = (caso / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x" / "_chat.txt").read_text(encoding="utf-8")

    resumen = atomize_whatsapp_case("CASO-X")

    out = caso / "01_Procesado" / "Whatsapp"
    assert (out / "chat-x__LECTURA.md").exists()
    assert (out / "corpus.jsonl").exists()
    assert (out / "_registro.json").exists()
    assert resumen["enterrados"] >= 1
    assert any((out / "enterrados").glob("ENT-*.md"))
    assert (caso / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x" / "_chat.txt").read_text(encoding="utf-8") == input_antes


def test_idempotente(tmp_path, monkeypatch):
    caso = _montar_caso(tmp_path)
    import core.whatsapp_atomize.pipeline as pl
    monkeypatch.setattr(pl, "caso_path", lambda cid: caso)
    atomize_whatsapp_case("CASO-X")
    reg1 = (caso / "01_Procesado" / "Whatsapp" / "_registro.json").read_text(encoding="utf-8")
    atomize_whatsapp_case("CASO-X")
    reg2 = (caso / "01_Procesado" / "Whatsapp" / "_registro.json").read_text(encoding="utf-8")
    assert reg1 == reg2
