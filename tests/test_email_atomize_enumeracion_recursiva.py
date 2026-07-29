"""Death tests de la enumeración recursiva (`MEJORAS #98`, spec §6 tests 12-13).

Cruzan enumeración + dedup + publicación: cada tarea puede estar bien por separado y
estas invariantes seguir rotas. Los seis escenarios los pidió la revisión adversarial
del diseño.
"""
from __future__ import annotations

import json
from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import pipeline as P


def _msg(mid: str, subj: str, cuerpo: str = "cuerpo") -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content(cuerpo)
    return m.as_bytes()


def _fichas(out: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in (out / "mensajes").glob("*.md")}


def test_todos_los_eml_en_subcarpetas_se_atomizan(tmp_path):
    # Recupera la cobertura que se pierde al retirar los tres tests de la guarda: el
    # caso típico de `--extraer-adjuntos` es que TODOS los mensajes traigan adjunto.
    src = tmp_path / "2026-07-28_email_01"
    for i, mid in enumerate(("<a@x>", "<b@x>", "<c@x>"), start=1):
        d = src / f"msg_{i}"
        d.mkdir(parents=True)
        (d / f"msg_{i}.eml").write_bytes(_msg(mid, f"Asunto {i}"))
    out = tmp_path / "Emails"

    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.mensajes == 3 and rep.eml_leidos == 3
    assert len(_fichas(out)) == 3


def test_transicion_top_only_a_mixta_con_copia_igual_no_cambia_el_canonico(tmp_path):
    # Death test del hallazgo 1 de la revisión: aparece una copia en subcarpeta con
    # bytes IDÉNTICOS → el canónico NO se mueve; la ficha solo gana la procedencia nueva.
    src = tmp_path / "03_Email"
    src.mkdir()
    raw = _msg("<a@x>", "Oferta")
    (src / "oferta.eml").write_bytes(raw)
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)
    antes = _fichas(out)
    assert len(antes) == 1

    (src / "copia").mkdir()
    (src / "copia" / "oferta.eml").write_bytes(raw)
    P.atomize_dir(src, out, case_dir=tmp_path)

    despues = _fichas(out)
    assert list(despues) == list(antes)                    # mismo nombre de ficha
    md = next(iter(despues.values()))
    assert 'eml_origen: "oferta.eml"' in md                # canónico intacto
    assert "copia/oferta.eml" in md                        # procedencia nueva registrada


def test_transicion_a_copia_mayor_cambia_el_canonico_declaradamente(tmp_path):
    # La otra mitad: con MÁS bytes la copia sí gana. Se fija como comportamiento
    # declarado (la fidelidad manda), no accidental.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "oferta.eml").write_bytes(_msg("<a@x>", "Oferta"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)

    (src / "copia").mkdir()
    (src / "copia" / "oferta.eml").write_bytes(_msg("<a@x>", "Oferta", cuerpo="c " * 200))
    P.atomize_dir(src, out, case_dir=tmp_path)

    md = next(iter(_fichas(out).values()))
    assert 'eml_origen: "copia/oferta.eml"' in md


def test_idempotente_con_subcarpetas(tmp_path):
    src = tmp_path / "03_Email"
    (src / "arras").mkdir(parents=True)
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "arras" / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"

    P.atomize_dir(src, out, case_dir=tmp_path)
    primera = _fichas(out)
    reg1 = (out / "_registro.json").read_text(encoding="utf-8")
    P.atomize_dir(src, out, case_dir=tmp_path)

    assert _fichas(out) == primera                          # byte-idéntico
    assert (out / "_registro.json").read_text(encoding="utf-8") == reg1   # 0 renumeraciones


def test_capa_a_byte_identica_sin_subcarpetas(tmp_path):
    # La invariante que protege todo caso actual: mismo input top-only ⇒ misma salida.
    # Es la versión sintética del paso 3 de la verificación en vivo (spec §7).
    src = tmp_path / "03_Email"
    src.mkdir()
    for i, mid in enumerate(("<a@x>", "<b@x>", "<c@x>"), start=1):
        (src / f"m{i}.eml").write_bytes(_msg(mid, f"Asunto {i}"))
    out = tmp_path / "Emails"

    P.atomize_dir(src, out, case_dir=tmp_path)
    fichas = _fichas(out)
    ids = json.loads((out / "_registro.json").read_text(encoding="utf-8"))["mensajes"]

    assert len(fichas) == 3
    assert all('eml_origen: "m' in md for md in fichas.values())   # nombre pelado
    # El MAPA exacto Message-ID → MSG-id, no el multiconjunto de ids: con el conjunto,
    # una permutación de qué mensaje recibe qué número pasaría el test (hallazgo de la
    # revisión adversarial). Los ids se acuñan en el orden de enumeración: m1, m2, m3.
    # Las claves del registro están normalizadas sin `<>` (`ids.py::_norm_mid`, el mismo
    # `.strip("<>")` que `message_id_of`): comparar contra "<a@x>" nunca casaría.
    assert {mid: e["id"] for mid, e in ids.items()} == {
        "a@x": "MSG-00001", "b@x": "MSG-00002", "c@x": "MSG-00003"}


def test_error_de_enumeracion_no_publica(tmp_path, monkeypatch):
    # End-to-end del sexto bloqueante: un directorio que no se puede recorrer cuenta como
    # fallo transitorio y por tanto NO publica. `rglob` lo habría silenciado.
    import os as _os
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    out = tmp_path / "Emails"
    real_walk = _os.walk

    def walk_con_error(top, onerror=None, **kw):
        yield from real_walk(top, onerror=onerror, **kw)
        if onerror is not None:
            exc = OSError("permiso denegado")
            exc.filename = str(src / "prohibida")
            onerror(exc)

    monkeypatch.setattr(_os, "walk", walk_con_error)
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.publicado is False and rep.fallos_lectura
    assert not out.exists()
