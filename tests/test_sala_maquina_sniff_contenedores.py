"""El sniff que entiende CONTENEDORES (`MEJORAS #215`, `PLAN.md` fila #27, pieza B).

**Por qué existe el fichero.** `_sniff_ext_por_contenido` tenía seis firmas, todas planas,
y ninguna para `PK\\x03\\x04`. Un `.docx` sin extensión salía `sin_soporte` y nadie lo leía:
los tres `sin_soporte` de la apertura de W-048U77 (2026-09-10) eran `.docx` con contenido, y
uno era un contrato de arras de 78 párrafos —de los documentos que deciden el nexo causal en
una reclamación de honorarios—.

**El listón que fija el plan, y que es lo que hace que estos tests prueben algo.** La cabecera
`PK` la comparten `.docx`, `.xlsx`, `.pptx`, todo ODF y un `.zip` cualquiera. Hacen falta las
**tres** ramas: el `.docx` con extensión (que no debe cambiar de ruta), el mismo sin extensión
(que debe dejar de ser `sin_soporte`) y un `.zip` de verdad (que debe **seguir** siéndolo). Sin
la tercera, un `PK → .docx` ciego aprobaría el examen entero.

**Corrección al texto del plan y de `MEJORAS #215`, medida contra la fuente:** los dos dicen
que un `.docx` debe llegar a la ruta `ofimatica`. No es así y no debe serlo — `clasificar_ruta`
manda `.docx` y `.xlsx` a `nativo`, que tiene extractor determinista propio (`_try_docx`), y su
propio docstring explica que cambiarles la ruta cambiaría el MD de casos ya hechos. Lo que
cierra `#215` es sacarlos de `sin_soporte`, no llevarlos a `ofimatica`.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from core import sala_maquina as sm

_MIME_ODT = "application/vnd.oasis.opendocument.text"
_MIME_ODS = "application/vnd.oasis.opendocument.spreadsheet"
_MIME_ODP = "application/vnd.oasis.opendocument.presentation"


def _zip(ruta: Path, entradas: list[tuple[str, bytes]]) -> Path:
    """Un zip con entradas reales: sin ninguna, el fichero empieza por `PK\\x05\\x06`
    (fin de directorio central) y no llega siquiera a la rama de contenedor."""
    with zipfile.ZipFile(ruta, "w") as zf:
        for nombre, data in entradas:
            zf.writestr(nombre, data)
    return ruta


def _ooxml(ruta: Path, pieza: str) -> Path:
    return _zip(ruta, [("[Content_Types].xml", b"<Types/>"), (pieza, b"<xml/>")])


def _odf(ruta: Path, mimetype: str, relleno: bytes = b"") -> Path:
    return _zip(ruta, [("mimetype", mimetype.encode("ascii") + relleno),
                       ("content.xml", b"<xml/>")])


# ---------------------------------------------------------------------------
# Las tres ramas que el plan exige
# ---------------------------------------------------------------------------

def test_docx_SIN_extension_deja_de_ser_sin_soporte(tmp_path: Path):
    """La rama que cierra `#215`: el contrato de arras de W-048U77."""
    ruta = _ooxml(tmp_path / "Contrato de arras", "word/document.xml")

    assert sm.clasificar_ruta(ruta.suffix.lower()) == "sin_soporte", (
        "premisa del test: sin extensión, el nombre no basta")
    assert sm._sniff_ext_por_contenido(ruta) == ".docx"
    assert sm.clasificar_ruta(".docx") == "nativo"


def test_docx_CON_extension_no_cambia_de_ruta(tmp_path: Path):
    """El sniff no se consulta cuando el nombre ya resuelve, y la ruta sigue siendo
    `nativo`. Si esta rama cambiara, cambiaría el MD de todos los casos ya hechos."""
    ruta = _ooxml(tmp_path / "Contrato de arras.docx", "word/document.xml")

    assert sm.clasificar_ruta(ruta.suffix.lower()) == "nativo"


def test_zip_DE_VERDAD_sigue_siendo_sin_soporte(tmp_path: Path):
    """La rama sin la cual todo lo demás aprobaría un `PK → .docx` ciego."""
    ruta = _zip(tmp_path / "fotos del inmueble", [("IMG_0001.jpg", b"\xff\xd8\xff")])

    assert sm._sniff_ext_por_contenido(ruta) == ".zip"
    assert sm.clasificar_ruta(".zip") == "sin_soporte"


# ---------------------------------------------------------------------------
# El resto del vocabulario de contenedores
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pieza,esperada,ruta_esperada", [
    ("word/document.xml", ".docx", "nativo"),
    ("xl/workbook.xml", ".xlsx", "nativo"),
    ("ppt/presentation.xml", ".pptx", "ofimatica"),
])
def test_cada_ooxml_se_reconoce_por_SU_pieza_del_indice(
        tmp_path: Path, pieza: str, esperada: str, ruta_esperada: str):
    ruta = _ooxml(tmp_path / "documento", pieza)

    assert sm._sniff_ext_por_contenido(ruta) == esperada
    assert sm.clasificar_ruta(esperada) == ruta_esperada


@pytest.mark.parametrize("mimetype,esperada,ruta_esperada", [
    (_MIME_ODT, ".odt", "ofimatica"),
    (_MIME_ODP, ".odp", "ofimatica"),
    # `.ods` se reconoce y AUN ASI no tiene lector: el sniff nombra, `clasificar_ruta`
    # decide. Que salga `sin_soporte` con su nombre real es mejor que con un hueco.
    (_MIME_ODS, ".ods", "sin_soporte"),
])
def test_odf_se_reconoce_por_su_mimetype(
        tmp_path: Path, mimetype: str, esperada: str, ruta_esperada: str):
    ruta = _odf(tmp_path / "documento", mimetype)

    assert sm._sniff_ext_por_contenido(ruta) == esperada
    assert sm.clasificar_ruta(esperada) == ruta_esperada


def test_mimetype_desconocido_es_un_zip_y_no_se_adivina(tmp_path: Path):
    ruta = _odf(tmp_path / "documento", "application/vnd.inventado.del.futuro")

    assert sm._sniff_ext_por_contenido(ruta) == ".zip"


def test_el_mimetype_se_lee_ACOTADO_y_no_entero(tmp_path: Path):
    """El `mimetype` lo escribe un fichero de fuera: leerlo entero sería dejar que él
    dimensione la memoria.

    **El relleno está elegido para que el test MUERA si el tope desaparece**, que es lo
    único que lo convierte en prueba: el tipo correcto se rellena con espacios hasta
    ocupar exactamente los 128 bytes del tope y detrás va basura. Leyendo acotado, lo
    leído es el tipo y sale `.odt`; leyendo entero entra la basura, el `strip` ya no
    limpia nada y sale `.zip`. Un relleno de solo espacios habría dado `.odt` en los dos
    casos: habría documentado el tope sin poder desmentirlo.
    """
    relleno = b" " * (sm._MAX_BYTES_MIMETYPE - len(_MIME_ODT)) + b"BASURA"
    ruta = _odf(tmp_path / "documento", _MIME_ODT, relleno=relleno)

    assert sm._sniff_ext_por_contenido(ruta) == ".odt"


# ---------------------------------------------------------------------------
# Control positivo: los dos mutantes que estas ramas tienen que matar
# ---------------------------------------------------------------------------

def test_MUTANTE_pk_a_docx_ciego_lo_mata_la_rama_del_zip(tmp_path: Path, monkeypatch):
    """El defecto que el plan nombra: resolver la cabecera `PK` como `.docx` sin abrir
    el índice. Si esta rama no estuviera, ese mutante pasaría todo lo demás."""
    monkeypatch.setattr(sm, "_sniff_contenedor_zip", lambda ruta: ".docx")

    zip_real = _zip(tmp_path / "fotos", [("IMG_0001.jpg", b"\xff\xd8\xff")])
    odt = _odf(tmp_path / "escrito", _MIME_ODT)

    assert sm._sniff_ext_por_contenido(zip_real) == ".docx", "premisa: el mutante está puesto"
    assert sm._sniff_ext_por_contenido(odt) == ".docx", "premisa: el mutante está puesto"
    # …y esas dos igualdades son exactamente las que los tests de arriba niegan.


def test_MUTANTE_sin_soporte_de_contenedores_lo_mata_el_docx_sin_extension(
        tmp_path: Path, monkeypatch):
    """El código PRE-remediación: seis firmas planas y ninguna rama de contenedor."""
    monkeypatch.setattr(sm, "_sniff_contenedor_zip", lambda ruta: None)

    ruta = _ooxml(tmp_path / "Contrato de arras", "word/document.xml")

    assert sm._sniff_ext_por_contenido(ruta) is None
    # Que es el `sin_soporte` de W-048U77: el contrato de arras entra y no lo lee nadie.


def test_cabecera_de_contenedor_ILEGIBLE_no_afirma_nada(tmp_path: Path):
    """Truncado o cifrado: `None` no es `.zip`. No poder abrirlo no es haber visto
    que no es un contenedor conocido — es no haber podido mirar."""
    ruta = tmp_path / "documento"
    ruta.write_bytes(b"PK\x03\x04" + b"\x00" * 40)

    assert sm._sniff_ext_por_contenido(ruta) is None


def test_un_zip_vacio_no_llega_a_la_rama_de_contenedor(tmp_path: Path):
    """Documenta la frontera real del formato: sin entradas el fichero empieza por la
    marca de fin de directorio central, así que ni siquiera es `PK\\x03\\x04`."""
    ruta = _zip(tmp_path / "vacio", [])

    assert ruta.read_bytes().startswith(b"PK\x05\x06")
    assert sm._sniff_ext_por_contenido(ruta) is None


# ---------------------------------------------------------------------------
# El inventario, que es quien lo consume
# ---------------------------------------------------------------------------

def test_inventariar_saca_del_sin_soporte_al_docx_sin_extension(tmp_path: Path):
    """De punta a punta por el consumidor real: el fichero llega al inventario con su
    extensión verdadera, que es lo que después elige la ruta de proceso."""
    origen = tmp_path / "caso" / "00_Input" / "01_Drive EV"
    origen.mkdir(parents=True)
    _ooxml(origen / "Contrato de arras", "word/document.xml")
    _zip(origen / "fotos", [("IMG_0001.jpg", b"\xff\xd8\xff")])
    _ooxml(origen / "Encargo.docx", "word/document.xml")

    inv = {d["rel_path"]: d["ext"] for d in sm.inventariar(tmp_path / "caso")}

    assert inv["01_Drive EV/Contrato de arras"] == ".docx"
    assert inv["01_Drive EV/Encargo.docx"] == ".docx"
    assert inv["01_Drive EV/fotos"] == ".zip"
    assert sm.clasificar_ruta(inv["01_Drive EV/fotos"]) == "sin_soporte"
