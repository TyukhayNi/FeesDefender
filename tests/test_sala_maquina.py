from core import sala_maquina as sm


def test_clasificar_ruta_por_extension():
    assert sm.clasificar_ruta(".pdf") == "pdf"
    assert sm.clasificar_ruta(".PDF") == "pdf"
    assert sm.clasificar_ruta(".jpg") == "imagen"
    assert sm.clasificar_ruta(".heic") == "imagen"
    assert sm.clasificar_ruta(".eml") == "nativo"
    assert sm.clasificar_ruta(".txt") == "nativo"
    assert sm.clasificar_ruta(".docx") == "nativo"
    assert sm.clasificar_ruta(".mp4") == "sin_soporte"
