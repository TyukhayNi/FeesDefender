import json

from core.whatsapp_atomize.corpus import corpus_jsonl_wa
from core.whatsapp_atomize.model import RegistroMensajeWA


def test_corpus_una_linea_por_mensaje_mas_meta():
    msgs = [
        RegistroMensajeWA(msg_id="MSG-00002", fecha_iso="2024-10-30", hora="1001", texto="b"),
        RegistroMensajeWA(msg_id="MSG-00001", fecha_iso="2024-10-30", hora="1000", texto="a"),
    ]
    out = corpus_jsonl_wa(msgs)
    lineas = out.strip().split("\n")
    meta = json.loads(lineas[0])
    assert meta["_tipo"] == "corpus_whatsapp"
    primero = json.loads(lineas[1])
    assert primero["msg_id"] == "MSG-00001"
    assert len(lineas) == 3
