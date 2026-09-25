from pathlib import Path

from core.whatsapp_atomize.propuesta_identidades import preparar_propuesta


CHAT = (
    "[30/10/2024, 10:00:00] +34600111222: Hola soy el propietario\n"
    "[30/10/2024, 10:01:00] Ana E&V: Buenas, soy de Engel\n"
)


def test_preparar_propuesta_reune_autores(tmp_path, monkeypatch):
    chat_dir = tmp_path / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x"
    chat_dir.mkdir(parents=True)
    (chat_dir / "_chat.txt").write_text(CHAT, encoding="utf-8")
    import core.whatsapp_atomize.propuesta_identidades as pr
    monkeypatch.setattr(pr, "caso_path", lambda cid: tmp_path)
    datos = preparar_propuesta("CASO-X")
    autores = {d["autor_export"] for d in datos}
    assert "+34600111222" in autores and "Ana E&V" in autores
    assert all("muestras" in d for d in datos)


def test_preparar_propuesta_lee_el_chat_android_con_nombre_propio(tmp_path, monkeypatch):
    """MEJORAS #285: la propuesta de identidades leía `chat_dir / "_chat.txt"` a pelo."""
    chat_dir = (tmp_path / "00_Input" / "2026-09-23_whatsapp_02" / "03_Otros"
                / "Chat de WhatsApp con Pablo")
    chat_dir.mkdir(parents=True)
    (chat_dir / "Chat de WhatsApp con Pablo.txt").write_text(
        "8/1/24, 10:32 - Pablo: hola\n", encoding="utf-8")
    import core.whatsapp_atomize.propuesta_identidades as pr
    monkeypatch.setattr(pr, "caso_path", lambda cid: tmp_path)
    assert {d["autor_export"] for d in preparar_propuesta("CASO-X")} == {"Pablo"}
