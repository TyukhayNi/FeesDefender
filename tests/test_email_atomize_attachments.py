from __future__ import annotations
from core.email_atomize import attachments as A


def test_clasifica_decorativo_por_recurrencia_y_tamano():
    logo = b"\x89PNG" + b"x" * 100          # pequeño
    # hash del logo aparece en 6 mensajes -> decorativo
    apariciones = {A._sha(logo): 6}
    assert A.es_decorativo(logo, "image/png", apariciones) is True
    # una captura grande, única -> no decorativo
    captura = b"\xff\xd8\xff" + b"y" * 80000
    assert A.es_decorativo(captura, "image/jpeg", {A._sha(captura): 1}) is False
    # un PDF (no imagen) nunca es decorativo
    pdf = b"%PDF" + b"z" * 50
    assert A.es_decorativo(pdf, "application/pdf", {A._sha(pdf): 99}) is False


def test_contar_apariciones_y_recolectar():
    from email.message import EmailMessage

    def _con_adj(mid, fn, data, mime="application/pdf"):
        m = EmailMessage()
        m["Message-ID"] = mid
        m["Subject"] = "x"; m["From"] = "a@x"; m["To"] = "b@x"
        m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
        m.set_content("c")
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
        return m.as_bytes()

    raws = [
        _con_adj("<a@x>", "contrato.pdf", b"%PDF mismo"),
        _con_adj("<b@x>", "renombrado.pdf", b"%PDF mismo"),   # mismo contenido, otro nombre
        _con_adj("<c@x>", "otro.pdf", b"%PDF distinto"),
    ]
    cont = A.contar_apariciones(raws)
    assert cont[A._sha(b"%PDF mismo")] == 2
    assert cont[A._sha(b"%PDF distinto")] == 1
