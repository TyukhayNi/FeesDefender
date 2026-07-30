from __future__ import annotations

from core.email_atomize import historial as H
from core.email_atomize import render as R
from core.email_atomize.model import RegistroMensaje


def test_frases_sustanciales_aplica_el_umbral_y_aplana():
    texto = ("Corta.\n"
             "Esta frase tiene mas de ocho palabras y por tanto se conserva entera.\n"
             "Tambien corta.")
    assert H.frases_sustanciales(texto) == [
        "Esta frase tiene mas de ocho palabras y por tanto se conserva entera."]


def test_frases_sustanciales_quita_las_marcas_de_cita_ANTES_de_aplanar():
    """El defecto que haria inutil todo el modulo: si se aplana antes de quitar los `>`, quedan
    a mitad de cadena, `normaliza_cuerpo` (que los quita solo al principio de linea) no los
    limpia, y NINGUNA frase del historial casa con su gemela de una ficha."""
    citada = "> Esta frase tiene mas de ocho palabras y viene citada con marca.\n> Y sigue aqui."
    limpia = "Esta frase tiene mas de ocho palabras y viene citada con marca. Y sigue aqui."
    assert H.frases_sustanciales(citada) == H.frases_sustanciales(limpia)
    assert ">" not in H.frases_sustanciales(citada)[0]


def _msg(msg_id: str, cuerpo: str) -> RegistroMensaje:
    return RegistroMensaje(msg_id=msg_id, cuerpo=cuerpo)


def test_indice_frases_agrupa_por_frase_normalizada():
    f = "Esta frase tiene mas de ocho palabras y aparece en dos fichas distintas."
    idx = H.indice_frases([_msg("MSG-00001", f), _msg("MSG-00002", f),
                           _msg("MSG-00003", "otra cosa corta")])
    assert list(idx.values()) == [["MSG-00001", "MSG-00002"]]


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
