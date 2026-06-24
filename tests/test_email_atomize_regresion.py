from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import bodies as B


def test_plain_limpio_gana_a_html_mal_declarado():
    """Reproduce el patrón real W-02VND1: text/plain UTF-8 correcto + text/html con
    bytes mal declarados. El motor debe quedarse con el plano limpio (sin mojibake)."""
    m = EmailMessage()
    m["Message-ID"] = "<cat@x>"; m["Subject"] = "Relat"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("Crec que aquest document ja está inclòs en la relació.")
    # html "equivalente" pero con caracteres que en mal-declarado se verían como mojibake
    m.add_alternative("<p>Crec que aquest document ja está inclòs en la relació.</p>",
                      subtype="html")
    cuerpo = B.extraer_cuerpo(m.as_bytes())
    assert "está inclòs en la relació" in cuerpo.texto
    assert "Ã" not in cuerpo.texto and "Â" not in cuerpo.texto
    assert cuerpo.formato_original == "plain"
    assert cuerpo.mojibake_marcado is False
