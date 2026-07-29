from __future__ import annotations
from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import extract as E


def _msg(mid: str, subject: str, body: str = "cuerpo") -> EmailMessage:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content(body)
    return m


def _eml(mid: str, subj: str) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content("cuerpo")
    return m.as_bytes()


def test_avistamiento_top_level(tmp_path):
    raw = _msg("<a@x>", "Solo").as_bytes()
    p = tmp_path / "2026-06-12_solo.eml"
    p.write_bytes(raw)
    avist = list(E.iter_avistamientos(tmp_path))
    assert len(avist) == 1
    a = avist[0]
    assert a.message_id == "a@x"
    assert a.profundidad == 0
    assert a.eml_origen == "2026-06-12_solo.eml"
    assert a.raw == raw


def test_desciende_en_rfc822_embebido(tmp_path):
    hijo = _msg("<hijo@x>", "Hijo")
    padre = _msg("<padre@x>", "Padre")
    padre.add_attachment(
        hijo.as_bytes(), maintype="message", subtype="rfc822", filename="adj.eml"
    )
    p = tmp_path / "2026-06-12_padre.eml"
    p.write_bytes(padre.as_bytes())
    avist = list(E.iter_avistamientos(tmp_path))
    mids = sorted(a.message_id for a in avist)
    assert mids == ["hijo@x", "padre@x"]
    hijo_av = next(a for a in avist if a.message_id == "hijo@x")
    assert hijo_av.profundidad == 1
    assert hijo_av.ruta_anidacion == ["padre@x"]


def test_enumera_subcarpetas_con_origen_relativo(tmp_path):
    # El layout que deja `--extraer-adjuntos`: el .eml del mensaje CON adjunto baja a
    # su propia subcarpeta (MEJORAS #98).
    base = tmp_path / "2026-07-28_email_01"
    (base / "arras").mkdir(parents=True)
    (base / "suelto.eml").write_bytes(_eml("<a@x>", "Suelto"))
    (base / "arras" / "arras.eml").write_bytes(_eml("<b@x>", "Con adjunto"))

    stats = E.EnumStats()
    avs = list(E.iter_avistamientos(base, stats=stats))

    assert [a.eml_origen for a in avs] == ["arras/arras.eml", "suelto.eml"]
    assert {a.fuente for a in avs} == {"2026-07-28_email_01"}
    assert (stats.enumerados, stats.leidos, stats.fallos) == (2, 2, [])


def test_origen_de_nivel_superior_es_el_nombre_pelado(tmp_path):
    # Prueba de la byte-identidad: en un caso sin subcarpetas, `eml_origen` debe seguir
    # siendo exactamente lo que era antes del cambio (el nombre), o el frontmatter de
    # todos los atoms existentes cambiaría.
    base = tmp_path / "03_Email"
    base.mkdir()
    (base / "2026-06-12_a.eml").write_bytes(_eml("<a@x>", "Uno"))

    avs = list(E.iter_avistamientos(base))

    assert avs[0].eml_origen == "2026-06-12_a.eml"


def test_fallo_de_lectura_se_declara_y_no_aborta(tmp_path, monkeypatch):
    base = tmp_path / "03_Email"
    base.mkdir()
    (base / "bueno.eml").write_bytes(_eml("<a@x>", "Bueno"))
    (base / "malo.eml").write_bytes(_eml("<b@x>", "Malo"))

    real = Path.read_bytes

    def flaky(self):
        if self.name == "malo.eml":
            raise OSError("no hidratado en Drive")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", flaky)
    stats = E.EnumStats()
    avs = list(E.iter_avistamientos(base, stats=stats))

    assert [a.eml_origen for a in avs] == ["bueno.eml"]     # el bueno sigue saliendo
    assert (stats.enumerados, stats.leidos) == (2, 1)
    assert len(stats.fallos) == 1 and "malo.eml" in stats.fallos[0]


def test_fallo_al_enumerar_un_directorio_se_declara(tmp_path, monkeypatch):
    # `Path.rglob` silencia los errores de directorio; por eso la enumeración usa
    # `os.walk(onerror=...)`, que es el único punto donde se pueden ver.
    import os as _os
    base = tmp_path / "03_Email"
    (base / "prohibida").mkdir(parents=True)
    (base / "visible.eml").write_bytes(_eml("<a@x>", "Visible"))

    real_walk = _os.walk

    def walk_con_error(top, onerror=None, **kw):
        for tupla in real_walk(top, onerror=onerror, **kw):
            yield tupla
        if onerror is not None:
            exc = OSError("permiso denegado")
            exc.filename = str(base / "prohibida")
            onerror(exc)

    monkeypatch.setattr(_os, "walk", walk_con_error)
    stats = E.EnumStats()
    avs = list(E.iter_avistamientos(base, stats=stats))

    assert any("prohibida" in f for f in stats.fallos)
    # El error de un directorio no debe abortar la enumeración del resto: sin este
    # assert, una implementación que interrumpiera `os.walk` al primer `onerror` pasaría
    # el test igual (el error se declararía, pero `visible.eml` desaparecería en
    # silencio — el mismo defecto que la enumeración recursiva vino a corregir).
    assert [a.eml_origen for a in avs] == ["visible.eml"]
