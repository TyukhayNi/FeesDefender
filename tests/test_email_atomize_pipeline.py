from __future__ import annotations
import json
from email.message import EmailMessage
from pathlib import Path
from core.email_atomize import pipeline as P


def _msg(mid, subject, body="cuerpo", fecha="Thu, 12 Jun 2026 10:00:00 +0200",
         attachments=None):
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = "Jaime <per01c@example.invalid>"
    m["To"] = "b@x"
    m.set_content(body)
    for fn, mime, data in attachments or []:
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
    return m.as_bytes()


def test_e2e_atomiza_a_directorio(tmp_path):
    src = tmp_path / "03_Email"
    out = tmp_path / "Emails"
    src.mkdir()
    # mensaje con adjunto
    (src / "2026-06-12_a.eml").write_bytes(
        _msg("<a@x>", "Oferta", attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")])
    )
    # padre que embebe a <a@x> (duplicado por Message-ID) + su propio mensaje
    padre = EmailMessage()
    padre["Message-ID"] = "<padre@x>"; padre["Subject"] = "RV: Oferta"
    padre["Date"] = "Fri, 13 Jun 2026 09:00:00 +0200"; padre["From"] = "c@x"; padre["To"] = "d@x"
    padre.set_content("Te reenvío.")
    padre.add_attachment(
        _msg("<a@x>", "Oferta", attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")]),
        maintype="message", subtype="rfc822", filename="a.eml")
    (src / "2026-06-13_padre.eml").write_bytes(padre.as_bytes())

    rep = P.atomize_dir(src, out)

    # 2 mensajes únicos: <a@x> (colapsado de suelto+embebido) y <padre@x>
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    # corpus tiene meta + 2 filas
    corpus = (out / "corpus.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(corpus) == 3
    # registro congelado presente
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg["_no_editar"] is True
    assert len(reg["mensajes"]) == 2
    # un adjunto único
    assert (out / "INDICE_ADJUNTOS.md").exists()
    assert (out / "CORREOS_LECTURA.md").exists()
    atts = list((out / "adjuntos").glob("*"))
    assert any(p.suffix == ".pdf" for p in atts)
    assert rep.mensajes == 2


def test_e2e_idempotente_no_renumera(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-12_a.eml").write_bytes(_msg("<a@x>", "Uno"))
    P.atomize_dir(src, out)
    reg1 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    # añadir un segundo .eml y re-correr
    (src / "2026-06-13_b.eml").write_bytes(_msg("<b@x>", "Dos"))
    P.atomize_dir(src, out)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    # <a@x> conserva su MSG-id original
    assert reg1["mensajes"]["a@x"]["id"] == reg2["mensajes"]["a@x"]["id"] == "MSG-00001"
    assert reg2["mensajes"]["b@x"]["id"] == "MSG-00002"


def test_emails_src_dirs_lotes_y_legacy(tmp_casos_root):
    from core import case_manager
    from core.email_atomize.pipeline import emails_src_dirs
    case_manager.ensure_case("EV-EA-001", titulo="ea")
    base = tmp_casos_root / "EV-EA-001" / "00_Input"
    (base / "03_Email").mkdir(parents=True)
    (base / "2026-07-17_email_01").mkdir()
    (base / "2026-07-17_whatsapp_01").mkdir()               # no email: fuera
    dirs = {d.name for d in emails_src_dirs("EV-EA-001")}
    assert dirs == {"2026-07-17_email_01", "03_Email"}


def test_atomize_dir_acepta_varias_fuentes(tmp_path):
    from core.email_atomize.pipeline import atomize_dir
    d1, d2, out = tmp_path / "l1", tmp_path / "l2", tmp_path / "out"
    d1.mkdir(); d2.mkdir()
    (d1 / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (d2 / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    report = P.atomize_dir([d1, d2], out, case_dir=tmp_path)
    assert len(list((out / "mensajes").glob("*.md"))) == 2
    assert report.mensajes == 2


# --- Derivadores de ruta y conteo (cableado, spec §4.1/§4.6) ------------------

def test_contar_eml_distingue_nivel_superior_de_recursivo(tmp_path):
    src = tmp_path / "2026-07-28_email_01"
    (src / "mensaje_con_adjunto").mkdir(parents=True)
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    # El layout que deja `--extraer-adjuntos`: el .eml baja a una subcarpeta y el
    # motor (glob, no rglob) no lo verá — MEJORAS #98.
    (src / "mensaje_con_adjunto" / "c.eml").write_bytes(_msg("<c@x>", "Tres"))

    assert P.contar_eml([src]) == (2, 3)


def test_contar_eml_suma_fuentes_y_tolera_inexistentes(tmp_path):
    lote = tmp_path / "2026-07-28_email_01"
    legacy = tmp_path / "03_Email"
    lote.mkdir()
    legacy.mkdir()
    (lote / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (legacy / "b.eml").write_bytes(_msg("<b@x>", "Dos"))

    assert P.contar_eml([lote, legacy, tmp_path / "no_existe"]) == (2, 2)
    assert P.contar_eml([]) == (0, 0)


def test_emails_src_dirs_de_caso_no_resuelve_el_caso(tmp_path, monkeypatch):
    from core.casos import case_locator

    def _prohibido(*a, **k):
        raise AssertionError("re-localización del caso: debe partir del case_dir dado")

    monkeypatch.setattr(case_locator, "path_for", _prohibido)
    monkeypatch.setattr(case_locator, "resolve_ref", _prohibido)

    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "2026-07-28_email_01").mkdir(parents=True)
    (case_dir / "00_Input" / "2026-07-20_whatsapp_01").mkdir()   # otra fuente: se ignora
    (case_dir / "00_Input" / "03_Email").mkdir()                 # cajón legacy: se incluye

    fuentes = P.emails_src_dirs_de_caso(case_dir)
    assert [f.name for f in fuentes] == ["2026-07-28_email_01", "03_Email"]
    assert P.emails_out_dir_de_caso(case_dir) == case_dir / "01_Procesado" / "Emails"


def test_llave_del_registro_no_colisiona_entre_fuentes(tmp_path):
    # `sub/a.eml` en dos fuentes distintas, mensajes DISTINTOS: el registro debe
    # distinguirlos (hallazgo 4 de la revisión adversarial).
    lote = tmp_path / "2026-07-28_email_01"
    legacy = tmp_path / "03_Email"
    (lote / "sub").mkdir(parents=True)
    (legacy / "sub").mkdir(parents=True)
    (lote / "sub" / "a.eml").write_bytes(_msg("<uno@x>", "Uno"))
    (legacy / "sub" / "a.eml").write_bytes(_msg("<dos@x>", "Dos"))
    out = tmp_path / "Emails"

    rep = P.atomize_dir([lote, legacy], out, case_dir=tmp_path)

    assert rep.mensajes == 2
    procesados = set(json.loads((out / "_registro.json").read_text(encoding="utf-8"))
                     ["eml_procesados"])
    assert procesados == {"2026-07-28_email_01/sub/a.eml", "03_Email/sub/a.eml"}


def test_eml_leidos_cuenta_ficheros_no_atoms(tmp_path):
    # Mata la implementación perezosa `eml_leidos = report.mensajes`: con dedup, dos
    # ficheros pueden dar un solo atom.
    src = tmp_path / "03_Email"
    src.mkdir()
    raw = _msg("<a@x>", "Oferta")
    (src / "copia_1.eml").write_bytes(raw)
    (src / "copia_2.eml").write_bytes(raw)

    rep = P.atomize_dir(src, tmp_path / "Emails", case_dir=tmp_path)

    assert (rep.eml_enumerados, rep.eml_leidos) == (2, 2)
    assert rep.mensajes == 1
    assert rep.publicado is True and rep.poda_omitida is False
