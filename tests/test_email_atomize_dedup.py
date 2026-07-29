from __future__ import annotations
from email.message import EmailMessage

from core.email_atomize.extract import Avistamiento
from core.email_atomize import dedup as D
from core.email_atomize.dedup import colapsar


def _eml(mid: str, subj: str, *, cuerpo: str = "cuerpo") -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content(cuerpo)
    return m.as_bytes()


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


def test_a_bytes_iguales_gana_la_ruta_menos_enterrada():
    # El mismo Message-ID visto arriba y en subcarpeta, bytes idénticos: el canónico NO
    # puede depender del orden de enumeración (spec §4.2).
    raw = _eml("<a@x>", "Oferta")
    sub = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="arras/a.eml",
                       profundidad=0, fuente="lote")
    top = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="a.eml",
                       profundidad=0, fuente="lote")

    # en los dos órdenes de llegada gana el de nivel superior
    assert colapsar([sub, top])[0].eml_origen == "a.eml"
    assert colapsar([top, sub])[0].eml_origen == "a.eml"


def test_a_misma_profundidad_no_desplaza_nadie():
    # LA prueba que protege todo caso actual: con las profundidades empatadas el canónico
    # es el primero que llegó, exactamente como hoy. Se comprueba en los dos órdenes, con
    # nombres que en Windows ordenan distinto como Path que como str (`a` vs `Z`), y con
    # dos FUENTES distintas — las tres vías por las que la regla lexicográfica de la rev. 1
    # del plan habría movido un canónico existente.
    raw = _eml("<a@x>", "Oferta")
    za = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="Z.eml", profundidad=0,
                      fuente="03_Email")
    av = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="a.eml", profundidad=0,
                      fuente="2026-07-28_email_01")

    assert colapsar([za, av])[0].eml_origen == "Z.eml"    # gana el primero, no el menor
    assert colapsar([av, za])[0].eml_origen == "a.eml"


def test_sin_message_id_dos_copias_identicas_tampoco_se_desplazan():
    # Sin Message-ID la clave de identidad es el sha256 del raw, así que dos copias
    # byte-idénticas colapsan igual. La regla debe comportarse igual que arriba.
    m = EmailMessage()
    m["Subject"] = "Sin id"
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content("cuerpo")
    raw = m.as_bytes()
    primero = Avistamiento(raw=raw, message_id="", eml_origen="Z.eml", profundidad=0,
                           fuente="03_Email")
    segundo = Avistamiento(raw=raw, message_id="", eml_origen="a.eml", profundidad=0,
                           fuente="lote")

    cols = colapsar([primero, segundo])

    assert len(cols) == 1 and cols[0].eml_origen == "Z.eml"


def test_la_fuente_viaja_con_el_canonico():
    # `fuente` alimenta la llave del registro (Task 3): si no se desplaza con el canónico,
    # la llave quedaría apuntando a la fuente equivocada.
    pequena = _eml("<a@x>", "Oferta")
    grande = _eml("<a@x>", "Oferta", cuerpo="cuerpo largo " * 20)
    av_p = Avistamiento(raw=pequena, message_id="<a@x>", eml_origen="a.eml",
                        profundidad=0, fuente="03_Email")
    av_g = Avistamiento(raw=grande, message_id="<a@x>", eml_origen="sub/a.eml",
                        profundidad=1, fuente="2026-07-28_email_01")

    col = colapsar([av_p, av_g])[0]

    assert col.eml_origen == "sub/a.eml" and col.fuente == "2026-07-28_email_01"


def test_una_copia_de_menor_fidelidad_no_desplaza_al_canonico():
    grande = _eml("<a@x>", "Oferta", cuerpo="cuerpo largo " * 20)
    pequena = _eml("<a@x>", "Oferta")
    assert len(pequena) < len(grande)
    av_grande = Avistamiento(raw=grande, message_id="<a@x>", eml_origen="sub/a.eml",
                             profundidad=0, fuente="lote")
    av_pequena = Avistamiento(raw=pequena, message_id="<a@x>", eml_origen="a.eml",
                              profundidad=0, fuente="lote")

    # la de MÁS bytes gana aunque esté más enterrada: la fidelidad manda sobre la ruta
    assert colapsar([av_pequena, av_grande])[0].eml_origen == "sub/a.eml"
    assert colapsar([av_grande, av_pequena])[0].eml_origen == "sub/a.eml"


def test_las_dos_procedencias_se_conservan():
    raw = _eml("<a@x>", "Oferta")
    a = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="a.eml", profundidad=0,
                     fuente="lote")
    b = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="arras/a.eml",
                     profundidad=0, fuente="lote")

    col = colapsar([a, b])[0]

    assert [p["eml_origen"] for p in col.procedencia] == ["a.eml", "arras/a.eml"]
    # los dicts de procedencia NO llevan `fuente`: se renderizan en el frontmatter y
    # añadir una clave cambiaría el .md de todos los atoms existentes
    assert set(col.procedencia[0]) == {"eml_origen", "profundidad", "ruta_anidacion"}
