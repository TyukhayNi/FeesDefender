from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import pipeline as P


def _eml(mid, de, to, subject, body, fecha="Mon, 03 Feb 2020 18:42:00 +0100"):
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = subject; m["From"] = de; m["To"] = to
    m["Date"] = fecha
    m.set_content(body)
    return m.as_bytes()


def _caso(tmp_path):
    case = tmp_path / "caso"
    src = case / "00_Input" / "03_Email"
    out = case / "01_Procesado" / "Emails"
    src.mkdir(parents=True)
    return case, src, out


def test_genera_vistas_desde_config(tmp_path):
    case, src, out = _caso(tmp_path)
    (case / "identidades.yaml").write_text(
        "personas:\n"
        "  - id: persona_uno\n"
        "    nombre: PersonaUno\n"
        "    vigilada: true\n"
        "    direcciones: [ { email: per01a@example.invalid, estado: confirmada } ]\n",
        encoding="utf-8")
    (case / "vistas.yaml").write_text(
        "vistas:\n"
        "  - id: dossier_persona_vigilada\n"
        "    titulo: Dossier\n"
        "    tipo: persona\n"
        "    persona: persona_uno\n"
        "  - id: nexo_causal\n"
        "    titulo: Nexo\n"
        "    tipo: tematica\n"
        "    palabras_clave: [inmueble]\n",
        encoding="utf-8")
    (src / "a.eml").write_bytes(_eml("<a@x>", "Jaime <per01a@example.invalid>", "x@y.com",
                                     "[inmueble]", "cuerpo sobre arras y inmueble"))
    rep = P.atomize_dir(src, out)   # case_dir derivado = out.parent.parent = case
    assert (out / "vistas" / "dossier_persona_vigilada.md").exists()
    assert (out / "vistas" / "nexo_causal.md").exists()
    assert rep.vistas_generadas == 2
    dossier = (out / "vistas" / "dossier_persona_vigilada.md").read_text(encoding="utf-8")
    assert "per01a@example.invalid" in dossier


def test_sin_config_no_genera_vistas(tmp_path):
    case, src, out = _caso(tmp_path)
    (src / "a.eml").write_bytes(_eml("<a@x>", "x@y.com", "z@y.com", "hola", "cuerpo"))
    rep = P.atomize_dir(src, out)
    assert rep.vistas_generadas == 0
    assert not (out / "vistas").exists()


def test_poda_vista_huerfana(tmp_path):
    case, src, out = _caso(tmp_path)
    (case / "identidades.yaml").write_text(
        "personas:\n  - id: p\n    vigilada: false\n"
        "    direcciones: [ { email: a@x.com, estado: confirmada } ]\n", encoding="utf-8")
    (case / "vistas.yaml").write_text(
        "vistas:\n  - id: v1\n    tipo: persona\n    persona: p\n", encoding="utf-8")
    (src / "a.eml").write_bytes(_eml("<a@x>", "a@x.com", "z@y.com", "hola", "cuerpo"))
    P.atomize_dir(src, out)
    assert (out / "vistas" / "v1.md").exists()
    # quitar la vista del config y re-correr → v1.md debe podarse
    (case / "vistas.yaml").write_text("vistas: []\n", encoding="utf-8")
    P.atomize_dir(src, out)
    assert not (out / "vistas" / "v1.md").exists()


def test_vista_persona_inexistente_puebla_notas(tmp_path):
    case, src, out = _caso(tmp_path)
    (case / "identidades.yaml").write_text(
        "personas:\n  - id: p\n    vigilada: false\n"
        "    direcciones: [ { email: a@x.com, estado: confirmada } ]\n", encoding="utf-8")
    (case / "vistas.yaml").write_text(
        "vistas:\n  - id: rota\n    tipo: persona\n    persona: no_existe\n", encoding="utf-8")
    (src / "a.eml").write_bytes(_eml("<a@x>", "a@x.com", "z@y.com", "hola", "cuerpo"))
    rep = P.atomize_dir(src, out)
    assert rep.vistas_generadas == 0
    assert any("no_existe" in n for n in rep.notas)


def test_vistas_yaml_malformado_no_aborta_la_corrida(tmp_path):
    case, src, out = _caso(tmp_path)
    # palabras_clave: 5 → list(5) revienta dentro de cargar_vistas
    (case / "vistas.yaml").write_text(
        "vistas:\n  - id: v1\n    tipo: tematica\n    palabras_clave: 5\n", encoding="utf-8")
    (src / "a.eml").write_bytes(_eml("<a@x>", "a@x.com", "z@y.com", "hola", "cuerpo"))
    rep = P.atomize_dir(src, out)
    # la atomización completa pese al vistas.yaml corrupto
    assert (out / "mensajes").exists() and list((out / "mensajes").glob("*.md"))
    assert (out / "corpus.jsonl").exists()
    assert (out / "_registro.json").exists()      # reg.save() se alcanzó
    assert any("vistas" in e for e in rep.errores)
    assert rep.vistas_generadas == 0
