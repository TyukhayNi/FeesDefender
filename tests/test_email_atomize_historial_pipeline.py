from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import pipeline as P

# Cita con marcador Outlook: `cortar_autor` la reconoce y RECORTA el cuerpo, que es la
# precondicion de todo este artefacto (`cuerpo_recortado_cita`).
_HISTORIAL = ("Esta frase citada tiene mas de ocho palabras y es la primera del historial.\n"
              "Esta segunda frase citada tambien pasa de ocho palabras con holgura.")


def _eml(mid: str, subject: str, *, fecha: str, cuerpo: str) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = "autor@example.invalid"
    m["To"] = "dest@example.invalid"
    m.set_content(cuerpo)
    return m.as_bytes()


def _con_historial(texto_autor: str, historial: str = _HISTORIAL) -> str:
    """Cuerpo con cola citada: autor arriba, marcador de cita, historial debajo.

    Marcador sin campos de cabecera (`-----Mensaje original-----`, la alternativa que el propio
    brief de esta tarea preve para el caso en que `cortar_autor` no reconozca el marcador con
    bloque `De:`/`Enviado:`): un bloque `De:`/`Enviado:`/`Para:`/`Asunto:` sintetico aqui dispara
    dos defectos AJENOS a esta tarea, verificados por separado (ver informe): (1) la Capa B
    reconstruye ese bloque como un mensaje propio y atribuido -- comportamiento correcto y
    preexistente, pero que infla el recuento de `.md` sin relacion con el historial; y (2)
    `frases_sustanciales` (modulo de la Tarea 1, `core/email_atomize/historial.py`, con su propio
    umbral congelado "no cambiar sin re-medir") no trata una linea de cabecera sin puntuacion
    terminal como limite de frase, y la pega a la primera frase citada real, dando una
    "exclusiva" espuria. Este marcador ejercita `cortar_autor`/el recorte igual (`cuerpo_recortado_
    cita=True`, ver comprobacion de precondicion) sin arrastrar ninguno de los dos.
    """
    return (f"{texto_autor}\n"
            "-----Mensaje original-----\n\n"
            f"{historial}")


def _historiales(out: Path) -> list[Path]:
    return sorted((out / "mensajes").glob("*.historial.md"))


def test_un_portador_con_cuerpo_recortado_obtiene_su_historial_verbatim(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    P.atomize_dir(src, out)

    hs = _historiales(out)
    assert len(hs) == 1, f"se esperaba un historial; hay {[p.name for p in hs]}"
    txt = hs[0].read_text(encoding="utf-8")
    assert "SIN ATRIBUIR" in txt
    # VERBATIM: el historial aparece tal cual, no reformateado.
    assert _HISTORIAL in txt
    # Y no atribuye: ninguna direccion del portador aparece como remitente del historial.
    assert "- de:" not in txt and "remitente:" not in txt


def test_un_portador_sin_cuerpo_recortado_no_genera_fichero(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Sin historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo="Solo texto del autor, sin ninguna cita debajo."))

    P.atomize_dir(src, out)
    assert _historiales(out) == []


def test_historial_100_por_cien_duplicado_se_escribe_igual_con_cero_exclusivas(tmp_path):
    """Decision 4 de la SPEC: el fichero existe siempre que haya texto recortado. «0 exclusivas»
    es una afirmacion FALSABLE — si no se escribiera, la respuesta a «me estoy perdiendo algo en
    este portador?» no existiria en ningun sitio."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    # El mensaje ANTERIOR del hilo llega como .eml propio: su cuerpo ES el historial.
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Original", fecha="Mon, 27 Jul 2026 09:00:00 +0200",
             cuerpo=_HISTORIAL))
    # Y el portador lo cita entero.
    (src / "b.eml").write_bytes(
        _eml("<b@example.invalid>", "Respuesta", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    P.atomize_dir(src, out)

    hs = _historiales(out)
    assert len(hs) == 1
    txt = hs[0].read_text(encoding="utf-8")
    assert "- **exclusivas de este fichero: 0**" in txt
    assert "duplicada" in txt, "las frases deben marcarse como duplicadas, no desaparecer"


def test_un_historial_que_falla_al_escribirse_se_declara_y_no_degrada_la_corrida(
        tmp_path, monkeypatch):
    """Contrato §7: el historial es una vista DERIVADA. Su fallo va a `notas` nombrando al
    portador, NO a `errores` -- porque `errores` gobierna `poda_omitida` y apagaria la poda del
    arbol entero por un artefacto accesorio. Y la ausencia queda declarada, no silenciosa."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    real = Path.write_text

    def falla_solo_el_historial(self, *a, **k):
        if self.name.endswith(".historial.md"):
            raise OSError("disco lleno de mentira")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "write_text", falla_solo_el_historial)
    rep = P.atomize_dir(src, out)

    assert _historiales(out) == []
    assert rep.errores == [], "un historial fallido NO puede entrar en errores: apagaria la poda"
    assert rep.poda_omitida is False
    assert any("historial de MSG-00001 no escrito" in n for n in rep.notas), \
        f"la ausencia debe declararse nombrando al portador; notas: {rep.notas}"
    # Y la ficha del portador SI se publica: la vista derivada no arrastra al artefacto principal.
    assert len(list((out / "mensajes").glob("*.md"))) == 1
