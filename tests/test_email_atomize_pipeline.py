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


# --- Foto incompleta: fail-closed transitorio / sin poda permanente (MEJORAS #98 T4) --

def test_fallo_de_lectura_no_publica_nada(tmp_path, monkeypatch):
    # Rama TRANSITORIA (Drive sin hidratar): la última publicación completa queda intacta.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)          # corrida completa previa
    antes = {p.relative_to(out).as_posix(): p.read_bytes()
             for p in out.rglob("*") if p.is_file()}
    assert len(list((out / "mensajes").glob("*.md"))) == 2

    real = Path.read_bytes

    def flaky(self):
        if self.name == "b.eml":
            raise OSError("no hidratado")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", flaky)
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.publicado is False
    assert rep.fallos_lectura and "b.eml" in rep.fallos_lectura[0]
    assert any("NO PUBLICADA" in n for n in rep.notas)
    # nada se ha tocado: ni fichas, ni agregados, ni registro. La clave del snapshot es la
    # ruta RELATIVA, no `p.name`: con subcarpetas dos ficheros homónimos ocultarían un
    # cambio (hallazgo de la revisión adversarial).
    assert {p.relative_to(out).as_posix(): p.read_bytes()
            for p in out.rglob("*") if p.is_file()} == antes


def test_fallo_de_construccion_publica_pero_no_poda(tmp_path, monkeypatch):
    # Rama PERMANENTE (.eml corrupto): se publica lo bueno y NO se borra la ficha del
    # que falló, para que un solo correo roto no bloquee el caso para siempre.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)
    fichas_antes = sorted(p.name for p in (out / "mensajes").glob("*.md"))
    assert len(fichas_antes) == 2

    real_construir = P._construir_mensaje

    def rompe_b(col, *a, **k):
        # `col.message_id` está normalizado sin `<>` (`core.email_export.message_id_of`).
        if col.message_id == "b@x":
            raise ValueError("cabecera imposible")
        return real_construir(col, *a, **k)

    # El mensaje bueno CAMBIA antes de la 2ª corrida: sin esto, una implementación que no
    # publicara absolutamente nada pasaría el test igual, porque el input bueno no varía
    # (hallazgo de la revisión adversarial).
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno", body="cuerpo NUEVO"))
    monkeypatch.setattr(P, "_construir_mensaje", rompe_b)
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.publicado is True and rep.poda_omitida is True
    assert rep.errores and "cabecera imposible" in rep.errores[0]
    assert any("poda de mensajes/ OMITIDA" in n for n in rep.notas)
    # la ficha del que falló SOBREVIVE
    assert sorted(p.name for p in (out / "mensajes").glob("*.md")) == fichas_antes
    # y lo bueno SÍ se publicó: la ficha de <a@x> trae el cuerpo nuevo
    fichas = {p.name: p.read_text(encoding="utf-8")
              for p in (out / "mensajes").glob("*.md")}
    assert any("cuerpo NUEVO" in md for md in fichas.values())


def test_fallo_de_layer_b_tampoco_poda_el_b_superado(tmp_path, monkeypatch):
    # El escenario que la poda existe para cubrir: una ficha B legítima que, esta misma
    # corrida, dejaría de ser esperada si la poda corriera — aquí porque el ÚNICO portador
    # que la origina falla al reconstruirse, así que sin `poda_omitida` no aportaría
    # candidatos y la ficha se consideraría huérfana. Reutilizamos el portador de texto
    # plano de `test_email_atomize_pipeline_b._carrier_outlook_plano` (import directo:
    # es el mismo fixture ya probado ahí para acuñar un B real, y duplicarlo aquí solo
    # divergiría con el tiempo) para que el fixture acuñe un B DE VERDAD, no vacío.
    from core.email_atomize import inline as INL
    from tests.test_email_atomize_pipeline_b import _carrier_outlook_plano
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))                    # Capa A llana, sin cita
    (src / "b.eml").write_bytes(_carrier_outlook_plano(
        "<b@x>", "alguien@x.com", "1 de mayo de 2020", "[inmueble]",
        "contenido citado suficientemente largo para superar el floor de 24 chars"))
    out = tmp_path / "Emails"

    rep1 = P.atomize_dir(src, out, case_dir=tmp_path)
    # Prueba de que el fixture NO es vacío: se acuña un B real (Capa A de b@x + su B).
    assert rep1.reconstruidos_b == 1
    fichas_antes = sorted(p.name for p in (out / "mensajes").glob("*.md"))
    assert len(fichas_antes) == 3   # a, b (Capa A) + la ficha B reconstruida
    b_antes = [p.name for p in (out / "mensajes").glob("*.md")
               if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(b_antes) == 1
    nombre_b = b_antes[0]

    real = INL.reconstruir

    def rompe_uno(m_a, raw, identidades):
        # `rfc_message_id` está normalizado sin `<>` (`headers._norm_mid`): comparar
        # contra "b@x", no "<b@x>". Es el mismo portador que en la 1ª corrida acuñó la
        # ficha B: sin `poda_omitida`, esta 2ª corrida no volvería a producirla y la
        # poda la retiraría.
        if m_a.rfc_message_id == "b@x":
            raise ValueError("portador ilegible")
        return real(m_a, raw, identidades)

    monkeypatch.setattr(INL, "reconstruir", rompe_uno)
    rep2 = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep2.publicado is True and rep2.poda_omitida is True
    assert any("portador ilegible" in e for e in rep2.errores)
    # la ficha B rancia SOBREVIVE porque la poda está apagada esta corrida
    fichas_despues = sorted(p.name for p in (out / "mensajes").glob("*.md"))
    assert nombre_b in fichas_despues
    assert fichas_despues == fichas_antes


def test_poda_retira_b_superado_cuando_no_hay_errores(tmp_path):
    # Contrapartida de la prueba anterior: con la foto COMPLETA (sin errores), una ficha B
    # que deja de ser esperada SÍ se poda. La transición real más simple: en la 1ª corrida
    # solo existe el portador (se acuña la ficha B); en la 2ª aparece la copia LIMPIA del
    # correo citado y el puente de fidelidad la asciende a upgrade — la ficha B deja de
    # producirse y, sin errores, la poda la retira.
    from tests.test_email_atomize_pipeline_b import _carrier_outlook_plano, _eml_limpio
    cuerpo = "contenido citado suficientemente largo para superar el floor de 24 chars"
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "2026-06-01_carrier_plano.eml").write_bytes(_carrier_outlook_plano(
        "<carrier-plano@x>", "alguien@x.com", "1 de mayo de 2020", "[inmueble]", cuerpo))
    out = tmp_path / "Emails"

    rep1 = P.atomize_dir(src, out, case_dir=tmp_path)
    assert rep1.reconstruidos_b == 1
    b_antes = [p for p in (out / "mensajes").glob("*.md")
               if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(b_antes) == 1
    nombre_b = b_antes[0].name

    (src / "2020-05-01_limpio.eml").write_bytes(_eml_limpio(
        "<limpio@x>", "alguien@x.com", "Fri, 01 May 2020 09:00:00 +0200", "[inmueble]", cuerpo))
    rep2 = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep2.errores == [] and rep2.poda_omitida is False
    assert rep2.upgrades >= 1
    assert not (out / "mensajes" / nombre_b).exists()


def test_sin_fallos_si_poda(tmp_path):
    # Contrapartida imprescindible: la poda legítima sigue funcionando.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)
    assert len(list((out / "mensajes").glob("*.md"))) == 2

    (src / "b.eml").unlink()
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.poda_omitida is False and rep.publicado is True
    assert len(list((out / "mensajes").glob("*.md"))) == 1


def test_no_siembra_carpetas_si_no_publica(tmp_path, monkeypatch):
    # Sin árbol previo y con fallo de lectura: no se crean `mensajes/`/`adjuntos/`.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    out = tmp_path / "Emails"

    real = Path.read_bytes

    def falla_los_eml(self):
        # Acotado a `.eml`: parchear `read_bytes` a secas rompería cualquier otra
        # lectura binaria de la corrida y el test fallaría por la razón equivocada.
        if self.suffix == ".eml":
            raise OSError("no hidratado")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", falla_los_eml)
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.publicado is False
    # NI la raíz: `load_registro` hacía `mkdir` de `out` y la decisión se toma antes.
    # Sin este assert, el test pasaba dejando creado `01_Procesado/Emails/` y la corrida
    # siguiente sin correo ya no haría el no-op estricto (vería «árbol previo»).
    assert not out.exists()
