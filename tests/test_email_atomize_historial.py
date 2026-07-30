from __future__ import annotations

from core.email_atomize import historial as H
from core.email_atomize import render as R
from core.email_atomize.model import RegistroMensaje


def test_frases_sustanciales_fija_el_umbral_en_ocho_palabras():
    """El umbral es contractual (`MEJORAS #105` midio el 90 % sobre el), asi que se fija por sus
    DOS bordes: 7 palabras fuera y 8 dentro. Con solo ejemplos claramente cortos y claramente
    largos, la mutacion `8 -> 7` sobrevivia (hallazgo de la revision adversarial)."""
    assert H.frases_sustanciales("Una dos tres cuatro cinco seis siete.") == []
    assert H.frases_sustanciales("Una dos tres cuatro cinco seis siete ocho.") == [
        "Una dos tres cuatro cinco seis siete ocho."]


def test_frases_sustanciales_aplana_los_saltos_de_linea():
    texto = ("Corta.\n"
             "Esta frase tiene mas de ocho palabras y por tanto se conserva entera.\n"
             "Tambien corta.")
    assert H.frases_sustanciales(texto) == [
        "Esta frase tiene mas de ocho palabras y por tanto se conserva entera."]


def test_frases_sustanciales_quita_las_marcas_de_cita_ANTES_de_aplanar():
    """El defecto que haria inutil todo el modulo: si se aplana antes de quitar los `>`, quedan
    a mitad de cadena, `normaliza_cuerpo` (que los quita solo al principio de linea) no los
    limpia, y NINGUNA frase del historial casa con su gemela de una ficha.

    La continuacion NO lleva puntuacion terminal antes del salto, y es larga a proposito: asi la
    frase resultante ATRAVIESA el salto y el `>` intermedio queda DENTRO de ella. Con una
    continuacion corta o ya puntuada, el partidor la separaba, el `>` nunca se observaba y el
    test pasaba igual invirtiendo limpieza y aplanado (hallazgo de la revision adversarial)."""
    citada = ("> Esta frase tiene mas de ocho palabras y viene citada con marca\n"
              "> y continua en la linea siguiente sin puntuacion terminal ninguna.")
    limpia = ("Esta frase tiene mas de ocho palabras y viene citada con marca "
              "y continua en la linea siguiente sin puntuacion terminal ninguna.")
    assert H.frases_sustanciales(citada) == H.frases_sustanciales(limpia)
    assert ">" not in H.frases_sustanciales(citada)[0]


def test_frases_sustanciales_retira_las_lineas_de_cabecera_de_cita():
    """El defecto que degradaba el artefacto EN PRODUCCION: las lineas `De:`/`Enviado:`/`Para:`/
    `Asunto:` y las de atribucion no terminan en puntuacion, asi que se pegaban a la primera
    frase citada real; esa frase compuesta no casa con su gemela limpia y salia «EXCLUSIVA»
    siendo falso. En correo real el historial esta lleno de esas lineas."""
    esperado = ["Esta frase citada tiene mas de ocho palabras y es la primera del historial."]
    outlook = ("De: Otro <otro@example.invalid>\n"
               "Enviado: lunes, 27 de julio de 2026 9:00\n"
               "Para: dest@example.invalid\n"
               "Asunto: Re: Asunto\n"
               "Esta frase citada tiene mas de ocho palabras y es la primera del historial.")
    assert H.frases_sustanciales(outlook) == esperado
    # La forma Apple/Gmail, que es la otra que aparece de verdad.
    apple = ("El 27 jul 2026, a las 9:00, Otro <otro@example.invalid> escribio:\n"
             "Esta frase citada tiene mas de ocho palabras y es la primera del historial.")
    assert H.frases_sustanciales(apple) == esperado


def _msg(msg_id: str, cuerpo: str) -> RegistroMensaje:
    return RegistroMensaje(msg_id=msg_id, cuerpo=cuerpo)


def test_indice_frases_agrupa_VARIANTES_bajo_una_sola_clave():
    """Prueba la NORMALIZACION, no solo la agrupacion: las variantes difieren en mayusculas,
    tildes y espaciado, y tienen que compartir una unica clave. Con frases byte-identicas la
    mutacion `k = f` (sin normalizar) sobrevivia (hallazgo de la revision adversarial)."""
    base = "Esta frase tiene mas de ocho palabras y aparece en varias fichas distintas."
    variantes = [
        base,
        base.upper(),
        "Esta frase tiene mas de ocho palabras y aparece en varias fichas distintas.".replace(
            "mas", "m\u00e1s").replace("aparece", "aparec\u00e9"),
        "Esta   frase tiene  mas de ocho palabras y aparece en varias fichas   distintas.",
    ]
    idx = H.indice_frases([_msg(f"MSG-0000{i}", v) for i, v in enumerate(variantes, 1)]
                          + [_msg("MSG-00009", "otra cosa corta")])
    assert len(idx) == 1, f"las variantes deben compartir UNA clave; hay {len(idx)}: {list(idx)}"
    assert list(idx.values()) == [["MSG-00001", "MSG-00002", "MSG-00003", "MSG-00004"]]


def test_render_marca_duplicadas_y_exclusivas_y_los_recuentos_cuadran():
    dup = "Esta frase tiene mas de ocho palabras y ya existe en otra ficha distinta."
    exc = "Esta otra frase tiene mas de ocho palabras y no existe en ningun otro sitio."
    idx = H.indice_frases([_msg("MSG-00007", dup)])
    md = H.render_historial(portador_msg_id="MSG-00002",
                            nombre_ficha="2026-07-28_1000_asunto_MSG-00002.md",
                            resto_citado=f"> {dup}\n> {exc}", indice=idx)
    assert "- frases sustanciales (>=8 palabras): 2" in md
    assert "- ya presentes en otra ficha: 1" in md
    assert "- **exclusivas de este fichero: 1**" in md
    assert "| 1 | duplicada | MSG-00007 |" in md
    assert "| 2 | **EXCLUSIVA** | — |" in md
    assert "SIN ATRIBUIR" in md and "2026-07-28_1000_asunto_MSG-00002.md" in md
    # El texto va VERBATIM: con sus marcas de cita, sin tocar.
    assert f"> {dup}\n> {exc}" in md


def test_render_no_cuenta_como_duplicada_una_frase_que_solo_esta_en_su_propia_ficha():
    """Contrato §8.7: el indice se excluye a si mismo. Sin esto, el historial de un portador
    cuyo propio cuerpo repita una frase saldria «duplicada» y se leeria como «esto ya esta en
    otro sitio», que es falso."""
    f = "Esta frase tiene mas de ocho palabras y solo vive en el propio portador."
    idx = H.indice_frases([_msg("MSG-00002", f)])
    md = H.render_historial(portador_msg_id="MSG-00002", nombre_ficha="x.md",
                            resto_citado=f, indice=idx)
    assert "- ya presentes en otra ficha: 0" in md
    assert "- **exclusivas de este fichero: 1**" in md


def test_nombre_historial_es_el_de_la_ficha_con_el_sufijo():
    m = RegistroMensaje(msg_id="MSG-00002", fecha_iso="2026-07-28", hora="1000", asunto="Asunto")
    assert R.nombre_historial(m) == R.nombre_md(m).removesuffix(".md") + ".historial.md"


def test_una_frase_que_normaliza_a_vacio_es_NO_COMPARABLE_y_no_exclusiva():
    """`normaliza_cuerpo` TRUNCA en el marcador de firma, asi que una frase que empiece por ahi
    normaliza a cadena vacia. Declararla «EXCLUSIVA» seria una afirmacion FALSA: no se ha podido
    comparar con nada. Categoria y contador propios (hallazgo de la revision adversarial)."""
    from core.email_atomize.inline import normaliza_cuerpo
    f = "Enviado desde mi iPhone y aqui sigue bastante texto que se pierde al normalizar."
    assert normaliza_cuerpo(f) == "", "precondicion: si no normaliza a vacio, el test es vacuo"

    md = H.render_historial(portador_msg_id="MSG-00002", nombre_ficha="x.md",
                            resto_citado=f, indice={})
    assert "| 1 | NO COMPARABLE | — |" in md
    assert "- no comparables (normalizan a vacio): 1" in md
    assert "- **exclusivas de este fichero: 0**" in md
    assert "EXCLUSIVA" not in md


def test_el_indice_no_trunca_la_frase():
    """La spec dice que el indice «repite la frase»: truncar a 120 caracteres en silencio hacia
    que dos proposiciones que difieran mas alla de ese punto se vieran identicas en la tabla."""
    larga = ("Esta frase es deliberadamente muy larga para superar cualquier limite de celda que "
             "se hubiera puesto en el renderizador del indice de frases del historial citado y "
             "acaba con una marca inequivoca: FINAL-DE-LA-FRASE-LARGA.")
    md = H.render_historial(portador_msg_id="MSG-00002", nombre_ficha="x.md",
                            resto_citado=larga, indice={})
    indice_solo = md.split("## Texto retirado")[0]
    assert "FINAL-DE-LA-FRASE-LARGA" in indice_solo, "la frase del INDICE esta truncada"
