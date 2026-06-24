from __future__ import annotations
from core.email_atomize.extract import Avistamiento
from core.email_atomize import dedup as D


def test_colapsa_por_message_id_y_fusiona_procedencia():
    a1 = Avistamiento(raw=b"corto", message_id="m@x", eml_origen="suelto.eml", profundidad=0)
    a2 = Avistamiento(raw=b"copia mas larga byte-fiel", message_id="m@x",
                      eml_origen="padre.eml", profundidad=1, ruta_anidacion=["p@x"])
    msgs = D.colapsar([a1, a2])
    assert len(msgs) == 1
    m = msgs[0]
    assert m.message_id == "m@x"
    # mayor fidelidad = más bytes
    assert m.raw == b"copia mas larga byte-fiel"
    # el avistamiento canónico fija profundidad/ruta; procedencia recoge AMBOS
    assert len(m.procedencia) == 2
    orig = {p["eml_origen"] for p in m.procedencia}
    assert orig == {"suelto.eml", "padre.eml"}


def test_sin_message_id_no_se_colapsa_en_fase1():
    a1 = Avistamiento(raw=b"uno", message_id="", eml_origen="x.eml", profundidad=0)
    a2 = Avistamiento(raw=b"dos", message_id="", eml_origen="y.eml", profundidad=0)
    msgs = D.colapsar([a1, a2])
    assert len(msgs) == 2  # cada uno keyed por sha256 de su raw
