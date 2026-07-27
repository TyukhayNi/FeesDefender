"""Detector de contaminación cruzada: W-codes de OTROS casos en el intake de correo.

Disparador real: W-02VUDR (2026-07-21) — la etiqueta Gmail del caso arrastró adjuntos
de al menos 8 expedientes ajenos. Ver `PLAN.md` `[SIGUIENTE-INTAKE-EMAIL-FILTRO]`.
"""
from __future__ import annotations

from email.message import EmailMessage

from core.email_atomize import contaminacion as CT
from core.email_atomize import pipeline as P
from core.email_atomize.model import AdjuntoRef, RegistroMensaje


def _m(msg_id="MSG-00001", asunto="", adjuntos=None):
    return RegistroMensaje(msg_id=msg_id, asunto=asunto, adjuntos=adjuntos or [])


def test_detecta_w_code_ajeno_en_nombre_de_adjunto():
    m = _m(adjuntos=[AdjuntoRef(nombre="W-028QTL_demanda.pdf")])

    hallazgos = CT.detectar_cruce([m], w_code_propio="W-02VUDR")

    assert len(hallazgos) == 1
    assert hallazgos[0].w_code == "W-028QTL"
    assert hallazgos[0].msg_id == "MSG-00001"
    assert hallazgos[0].donde == "adjunto"


def test_detecta_w_code_ajeno_en_el_asunto():
    m = _m(asunto="RV: Circularización auditoría W-02KJHT y otros")

    hallazgos = CT.detectar_cruce([m], w_code_propio="W-02VUDR")

    assert [(h.w_code, h.donde) for h in hallazgos] == [("W-02KJHT", "asunto")]


def test_el_w_code_propio_no_es_hallazgo():
    m = _m(asunto="Honorarios W-02VUDR", adjuntos=[AdjuntoRef(nombre="W-02VUDR_encargo.pdf")])

    assert CT.detectar_cruce([m], w_code_propio="W-02VUDR") == []


def test_sin_w_code_propio_no_avisa_de_nada():
    """Un caso `(SIN REFERENCIA)` (o un layout del que no se deriva el W-code) no
    permite saber qué es ajeno: callar es correcto, marcarlo todo sería ruido."""
    m = _m(asunto="W-028QTL", adjuntos=[AdjuntoRef(nombre="W-02KJHT.pdf")])

    assert CT.detectar_cruce([m], w_code_propio="") == []


def test_ignora_w_pegado_a_texto():
    m = _m(adjuntos=[AdjuntoRef(nombre="Renew-02ABCD.pdf")])

    assert CT.detectar_cruce([m], w_code_propio="W-02VUDR") == []


def test_caza_w_code_en_minusculas():
    m = _m(adjuntos=[AdjuntoRef(nombre="w-028qtl_demanda.pdf")])

    hallazgos = CT.detectar_cruce([m], w_code_propio="W-02VUDR")

    assert [h.w_code for h in hallazgos] == ["W-028QTL"]


def _h(w_code, msg_id, donde="adjunto"):
    return CT.Hallazgo(w_code=w_code, msg_id=msg_id, donde=donde, detalle="x.pdf")


def test_resumen_agrupa_por_w_code_ajeno_y_cuenta_los_mensajes():
    hallazgos = [_h("W-028QTL", "MSG-00001", "asunto"), _h("W-028QTL", "MSG-00002"),
                 _h("W-02KJHT", "MSG-00003")]

    assert CT.resumir(hallazgos) == [
        "posible contaminación cruzada: W-028QTL en 2 mensajes (MSG-00001, MSG-00002)",
        "posible contaminación cruzada: W-02KJHT en 1 mensaje (MSG-00003)",
    ]


def test_resumen_vacio_cuando_no_hay_hallazgos():
    assert CT.resumir([]) == []


def test_resumen_no_repite_el_mismo_mensaje():
    """Un W-code ajeno en el asunto Y en dos adjuntos del mismo correo es UN mensaje
    contaminado, no tres: la cuenta que importa es cuántos correos hay que mirar."""
    hallazgos = [_h("W-028QTL", "MSG-00001", "asunto"), _h("W-028QTL", "MSG-00001"),
                 _h("W-028QTL", "MSG-00002")]

    assert CT.resumir(hallazgos) == [
        "posible contaminación cruzada: W-028QTL en 2 mensajes (MSG-00001, MSG-00002)",
    ]


def test_resumen_recorta_la_lista_de_mensajes_a_cinco():
    hallazgos = [_h("W-028QTL", f"MSG-{n:05d}") for n in range(1, 8)]

    assert CT.resumir(hallazgos) == [
        "posible contaminación cruzada: W-028QTL en 7 mensajes "
        "(MSG-00001, MSG-00002, MSG-00003, MSG-00004, MSG-00005 +2 más)",
    ]


# --- Integración: el aviso llega al AtomizeReport en el layout real del caso ---

def _eml(mid, subject, attachments=None):
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "Jaime <per01c@example.invalid>"
    m["To"] = "b@x"
    m.set_content("cuerpo")
    for fn, mime, data in attachments or []:
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
    return m.as_bytes()


def _caso(tmp_path, nombre="BaRS9 - Calle Falsa 1 (W-02VUDR) - Art 20 LAU"):
    """Layout estándar: <caso>/00_Input/03_Email y <caso>/01_Procesado/Emails, de
    forma que `atomize_dir` derive el case_dir por defecto (out.parent.parent)."""
    caso = tmp_path / nombre
    src = caso / "00_Input" / "03_Email"
    src.mkdir(parents=True)
    return caso, src, caso / "01_Procesado" / "Emails"


def test_atomize_dir_avisa_de_w_code_ajeno_en_un_adjunto(tmp_path):
    caso, src, out = _caso(tmp_path)
    (src / "2026-06-12_a.eml").write_bytes(_eml(
        "<a@x>", "Facturación mensual",
        attachments=[("W-028QTL_demanda.pdf", "application/pdf", b"%PDF x")]))

    rep = P.atomize_dir(src, out)

    assert [n for n in rep.notas if "W-028QTL" in n] == [
        "posible contaminación cruzada: W-028QTL en 1 mensaje (MSG-00001)"]


def test_atomize_dir_no_avisa_cuando_el_intake_esta_limpio(tmp_path):
    caso, src, out = _caso(tmp_path)
    (src / "2026-06-12_a.eml").write_bytes(_eml(
        "<a@x>", "Hoja de encargo W-02VUDR",
        attachments=[("encargo.pdf", "application/pdf", b"%PDF x")]))

    rep = P.atomize_dir(src, out)

    assert [n for n in rep.notas if "contaminación" in n] == []


# --- Derivación del W-code propio desde el nombre de la carpeta del caso ---

def test_w_code_de_carpeta_lo_saca_del_case_id_canonico():
    assert CT.w_code_de_carpeta(
        "BaRS9 - Calle Falsa 1 (W-02VUDR) - Art 20 LAU") == "W-02VUDR"


def test_w_code_de_carpeta_ignora_un_parentesis_con_pinta_numerica():
    """Una dirección con código postal entre paréntesis no es una referencia."""
    assert CT.w_code_de_carpeta(
        "BaRS9 - Calle Falsa 1 (08860) (W-02VUDR) - Art 20 LAU") == "W-02VUDR"


def test_w_code_de_carpeta_vacio_para_sin_referencia():
    assert CT.w_code_de_carpeta("BaOT1 - Consulta suelta (SIN REFERENCIA) - Otros") == ""
