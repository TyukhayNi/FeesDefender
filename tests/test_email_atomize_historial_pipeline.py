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

    Marcador SIN campos de cabecera (`-----Mensaje original-----`) por una sola razon, que sigue
    viva: un bloque `De:`/`Enviado:`/`Para:`/`Asunto:` hace que la Capa B reconstruya ese mensaje
    como ficha propia y atribuida --comportamiento correcto y preexistente-- lo que cambia el
    recuento de fichas y estorba a los tests que cuentan. La forma realista con cabecera se cubre
    aparte, en `test_un_historial_con_cabeceras_de_cita_no_inventa_exclusivas`.

    (Una version anterior de este comentario alegaba un segundo motivo: que las lineas de
    cabecera se pegaban a la primera frase citada y producian una «exclusiva» espuria. Era cierto
    y era un DEFECTO, no una razon para cambiar el fixture; lo destapo la revision adversarial y
    esta arreglado -- `frases_sustanciales` retira ahora esas lineas.)
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


def test_la_poda_conserva_los_historiales_pero_se_lleva_los_huerfanos(tmp_path):
    """El arreglo del §5.3 tiene DOS direcciones y las dos importan: el historial legitimo
    sobrevive a la corrida siguiente, y uno huerfano --portador desaparecido, o portador que ya
    no tiene texto recortado-- se poda. Si solo se vigilara la primera, `esperados` podria
    crecer sin limite y la poda dejaria de converger, que es lo que esa poda existe para
    garantizar."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    P.atomize_dir(src, out)
    primera = [p.name for p in _historiales(out)]
    assert len(primera) == 1

    huerfano = out / "mensajes" / "2020-01-01_0000_fantasma_MSG-09999.historial.md"
    huerfano.write_text("<!-- viejo -->\n", encoding="utf-8")

    P.atomize_dir(src, out)

    assert [p.name for p in _historiales(out)] == primera, \
        "la segunda corrida se ha llevado el historial legitimo"
    assert not huerfano.exists(), "un historial huerfano debe podarse: la poda tiene que converger"


def test_el_historial_es_byte_identico_entre_corridas(tmp_path):
    """Idempotencia del CONTENIDO, no solo de la existencia: re-atomizar no debe reescribir el
    fichero con bytes distintos, o el arbol churnearia en cada corrida y ensuciaria el Drive y la
    comparacion con los `_entregas/` sellados. Sobrevivir a la poda (test anterior) no implica
    ser estable.

    QUE CAZA Y QUE NO, medido por mutacion y escrito aqui para que nadie le atribuya mas:
    - **Caza** el no-determinismo real (iterar un `set`, `random`, orden que cambie entre
      llamadas): con un `shuffle` del recorrido del indice, este test muere.
    - **NO caza** un orden distinto pero FIJO — p. ej. recorrer `mensajes` al reves. Las dos
      corridas comparten el build, luego comparten el orden, y los bytes coinciden. Eso no es un
      defecto que este test deba pillar: el fichero tendria otro contenido fijo, no inestable.

    El fixture tampoco es cualquiera: para que el orden pueda influir, la frase citada tiene que
    existir en DOS fichas ajenas, de modo que la columna «donde vive» liste dos `MSG-id`. Con un
    fixture donde todo saliera EXCLUSIVA esa columna seria siempre `—` y el test no vigilaria
    nada -- que es como estaba escrito primero, y lo destapo el mutation testing."""
    import hashlib

    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    compartida = "Esta frase compartida tiene mas de ocho palabras y vive en dos fichas ajenas."
    # Dos portadores cuyo CUERPO (no su cita) contiene la frase -> dos fichas la contienen.
    for i, mid in enumerate(("a", "b")):
        (src / f"{mid}.eml").write_bytes(
            _eml(f"<{mid}@example.invalid>", f"Asunto {mid}",
                 fecha=f"Mon, 27 Jul 2026 0{i + 8}:00:00 +0200", cuerpo=compartida))
    # Y un tercero que la cita: su historial la marcara «duplicada» con DOS MSG-id.
    (src / "c.eml").write_bytes(
        _eml("<c@example.invalid>", "Asunto c", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Respuesta c.", historial=compartida)))

    def huellas() -> dict[str, str]:
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in _historiales(out)}

    P.atomize_dir(src, out)
    primera = huellas()
    assert len(primera) == 1
    # Precondicion del test: si esto falla, el fixture no ejercita el orden y el test es vacuo.
    txt = _historiales(out)[0].read_text(encoding="utf-8")
    assert "- ya presentes en otra ficha: 1" in txt, txt
    assert "MSG-00001, MSG-00002" in txt or "MSG-00002, MSG-00001" in txt, \
        "la frase debe listar DOS MSG-id, o el orden no se puede notar"

    P.atomize_dir(src, out)
    assert huellas() == primera, "el historial cambia entre corridas: el orden no es determinista"


def test_un_fallo_al_reescribir_NO_borra_el_historial_de_la_corrida_anterior(tmp_path,
                                                                            monkeypatch):
    """Hallazgo B0 de la revision adversarial, y es perdida de datos por un error TRANSITORIO.

    `historiales_esperados` lleva el fichero de todo portador con texto recortado, ESCRIBA O NO.
    Si solo llevara los escritos con exito, un fallo pasajero (disco, permiso, Drive sin hidratar)
    haria que la poda borrase la copia buena de la corrida anterior, con la nota diciendo apenas
    «no escrito». Un historial rancio es muchisimo mejor que ninguno."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    P.atomize_dir(src, out)
    hs = _historiales(out)
    assert len(hs) == 1
    contenido_bueno = hs[0].read_bytes()

    # 2a corrida: la escritura del historial falla, la de las fichas no.
    real = Path.write_text

    def falla_solo_el_historial(self, *a, **k):
        if self.name.endswith(".historial.md"):
            raise OSError("disco lleno de mentira")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "write_text", falla_solo_el_historial)
    rep = P.atomize_dir(src, out)

    supervivientes = _historiales(out)
    assert len(supervivientes) == 1, "LA PODA SE HA COMIDO EL HISTORIAL BUENO tras un fallo"
    assert supervivientes[0].read_bytes() == contenido_bueno, "se conserva la copia anterior"
    assert rep.errores == [], "un historial fallido no puede entrar en errores"
    assert any("puede estar rancio" in n for n in rep.notas), \
        f"la nota debe avisar de que lo que queda es de una corrida anterior; notas: {rep.notas}"


def test_un_fallo_del_RENDER_tampoco_aborta_la_atomizacion(tmp_path, monkeypatch):
    """Hallazgo A de la revision adversarial: solo se capturaba `OSError`, asi que un
    `ValueError` del renderizador propagaba y abortaba `atomize_dir` DESPUES de haber escrito las
    fichas. Una vista derivada no puede tumbar la corrida."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    from core.email_atomize import historial as HIST

    def revienta(**k):
        raise ValueError("renderizador roto de mentira")

    monkeypatch.setattr(HIST, "render_historial", revienta)
    rep = P.atomize_dir(src, out)

    assert _historiales(out) == []
    assert rep.errores == []
    assert rep.poda_omitida is False
    assert any("renderizador roto de mentira" in n for n in rep.notas), rep.notas
    # Y la ficha SI se publica: el artefacto principal no se arrastra.
    assert len([p for p in (out / "mensajes").glob("*.md")
                if not p.name.endswith(".historial.md")]) == 1


def test_un_historial_con_cabeceras_de_cita_no_inventa_exclusivas(tmp_path):
    """La forma DOMINANTE del correo real: el historial citado llega con su bloque
    `De:`/`Enviado:`/`Para:`/`Asunto:`. Esas lineas no terminan en puntuacion, asi que antes se
    pegaban a la primera frase citada y esa frase compuesta no casaba con su gemela de la ficha
    limpia -> «exclusiva» espuria. Con el historial 100 % duplicado el recuento tiene que ser 0
    exclusivas: si sale 1, el defecto ha vuelto."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    # El mensaje anterior del hilo, como .eml propio: su cuerpo ES el historial.
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Original", fecha="Mon, 27 Jul 2026 09:00:00 +0200",
             cuerpo=_HISTORIAL))
    # Y el portador lo cita CON cabecera, como llega de verdad.
    con_cabecera = ("Mi respuesta breve.\n"
                    "De: Otro <otro@example.invalid>\n"
                    "Enviado: lunes, 27 de julio de 2026 9:00\n"
                    "Para: dest@example.invalid\n"
                    "Asunto: Re: Original\n"
                    + _HISTORIAL)
    (src / "b.eml").write_bytes(
        _eml("<b@example.invalid>", "Respuesta", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=con_cabecera))

    P.atomize_dir(src, out)

    hs = _historiales(out)
    assert len(hs) == 1, f"se esperaba un historial; hay {[p.name for p in hs]}"
    txt = hs[0].read_text(encoding="utf-8")
    assert "- **exclusivas de este fichero: 0**" in txt, (
        "las cabeceras de cita se estan pegando a la frase y fabricando una exclusiva:\n" + txt)
    # El bloque de texto sigue siendo VERBATIM: las cabeceras estan ahi, solo salen del INDICE.
    assert "De: Otro <otro@example.invalid>" in txt
