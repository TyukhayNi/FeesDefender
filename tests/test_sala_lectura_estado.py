"""El lector de estado de la sala de lectura: dice en que punto esta, sin tocarla.

Sale de la fila #30 (`[APER-70]`). El boton «📚 Sala de lectura» de Streamlit disparaba
`core.sala_lectura.organizar`, un constructor **declarado muerto en su propia primera
linea**, y lo disparaban Paola y Ana, que no tocan codigo. La decision fue que gobierna la
skill `organizar-sala-lectura`, que **no corre desde Streamlit**: corre en Cowork o en
Claude Code. Asi que la UI no puede montar la sala — y lo que si puede, y no hacia, es
**decir si esta montada y que le falta**.

Todo lo de aqui es de LECTURA. Que eso sea cierto no se deja a la buena fe: hay un test
que sella el arbol entero por `sha256` y vuelve a compararlo despues de llamar.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from core import sala_lectura_estado as sle
from core import verificar_apertura as va

ARTEFACTOS_EN_LA_SALA = ("INDICE.md", "CRONOLOGIA.md", "_MANIFIESTO.md")
CATALOGO = "indice_documental.yaml"


def _caso(tmp_path: Path, *, sala: bool = True, artefactos=(), catalogo=False,
          documentos=()) -> Path:
    """Un expediente sintetico en `tmp_path`. Nunca se toca el arbol de produccion."""
    case_dir = tmp_path / "BaRS1 - Sintetico - (W-00TEST) - Impago"
    proc = case_dir / "01_Procesado"
    proc.mkdir(parents=True)
    if catalogo:
        (proc / CATALOGO).write_text("- doc: uno\n", encoding="utf-8")
    if sala:
        d = proc / "Sala lectura"
        d.mkdir()
        for nombre in artefactos:
            (d / nombre).write_text(f"# {nombre}\n", encoding="utf-8")
        for rel in documentos:
            destino = d / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text("contenido\n", encoding="utf-8")
    return case_dir


def _sello(raiz: Path) -> list[tuple[str, str]]:
    """Huella del arbol: ruta relativa + sha256 de cada fichero, ordenada."""
    out = []
    for p in sorted(raiz.rglob("*")):
        if p.is_file():
            out.append((str(p.relative_to(raiz)),
                        hashlib.sha256(p.read_bytes()).hexdigest()))
    return out


# ---------------------------------------------------------------------------
# montada / no montada
# ---------------------------------------------------------------------------


def test_sin_carpeta_de_sala_no_esta_montada(tmp_path: Path) -> None:
    e = sle.estado(_caso(tmp_path, sala=False))
    assert e.montada is False
    assert e.n_documentos == 0


def test_con_carpeta_y_documentos_esta_montada(tmp_path: Path) -> None:
    e = sle.estado(_caso(tmp_path, documentos=("2025-01-02_encargo.pdf",)))
    assert e.montada is True
    assert e.n_documentos == 1


def test_una_sala_vacia_esta_montada_pero_sin_documentos(tmp_path: Path) -> None:
    """Existir y estar poblada son cosas distintas, y confundirlas es el defecto de
    `MEJORAS #221` otra vez: un mensaje que describe el paso y no el expediente."""
    e = sle.estado(_caso(tmp_path))
    assert e.montada is True
    assert e.n_documentos == 0


# ---------------------------------------------------------------------------
# el conteo de documentos
# ---------------------------------------------------------------------------


def test_los_artefactos_no_cuentan_como_documentos(tmp_path: Path) -> None:
    """`INDICE.md` y compania viven en la sala y no son documentos del expediente.

    Contarlos inflaria el numero justo en los casos donde la sala esta vacia: una sala
    recien renderizada diria «3 documentos» teniendo cero.
    """
    e = sle.estado(_caso(tmp_path, artefactos=ARTEFACTOS_EN_LA_SALA,
                         documentos=("2025-01-02_encargo.pdf",)))
    assert e.n_documentos == 1


def test_los_miembros_de_un_documento_compuesto_cuentan(tmp_path: Path) -> None:
    """La subcarpeta del documento compuesto es la unica excepcion a la sala plana.

    Sus miembros son documentos del expediente: un hilo de correo con tres adjuntos son
    cuatro ficheros que alguien tiene que leer.
    """
    e = sle.estado(_caso(tmp_path, documentos=(
        "2025-01-02_requerimiento/2025-01-02_requerimiento.eml",
        "2025-01-02_requerimiento/adjuntos/anexo-1.pdf",
        "2025-01-02_requerimiento/adjuntos/anexo-2.pdf",
    )))
    assert e.n_documentos == 3


def test_un_fichero_con_nombre_de_artefacto_dentro_de_un_compuesto_si_cuenta(
    tmp_path: Path,
) -> None:
    """La exclusion es por POSICION, no por nombre.

    Los artefactos son los de la RAIZ de la sala. Un adjunto que se llame `INDICE.md`
    dentro de un documento compuesto es un documento del expediente, y excluirlo por
    nombre lo haria desaparecer del conteo sin que nadie lo dijera.
    """
    e = sle.estado(_caso(tmp_path, artefactos=("INDICE.md",),
                         documentos=("2025-01-02_hilo/adjuntos/INDICE.md",)))
    assert e.n_documentos == 1


# ---------------------------------------------------------------------------
# los cuatro artefactos: se DELEGA, no se reimplementa
# ---------------------------------------------------------------------------


def test_los_artefactos_los_dictamina_la_comprobacion_canonica(tmp_path: Path) -> None:
    """El veredicto es, literalmente, el de `c4_artefactos_de_la_sala`.

    Reimplementar aqui «cuales son los cuatro» duplicaria el contrato que
    `verificar_apertura._ARTEFACTOS_SALA` ya posee, y las dos copias divergirian — que es
    exactamente como `_MD_SUBDIR` dejo 140 enlaces muertos (`MEJORAS #151`).
    """
    case_dir = _caso(tmp_path, artefactos=ARTEFACTOS_EN_LA_SALA, catalogo=True,
                     documentos=("2025-01-02_encargo.pdf",))
    assert sle.estado(case_dir).artefactos == va.c4_artefactos_de_la_sala(case_dir)


def test_sala_completa_da_ok(tmp_path: Path) -> None:
    case_dir = _caso(tmp_path, artefactos=ARTEFACTOS_EN_LA_SALA, catalogo=True)
    assert sle.estado(case_dir).artefactos.estado == va.OK


def test_la_sala_del_motor_deprecado_acusa_los_dos_que_le_faltan(
    tmp_path: Path,
) -> None:
    """El caso REAL medido en W-030TZY y W-02NHNC (`MEJORAS #221`).

    `core.sala_lectura` escribe `INDICE.md` y `CRONOLOGIA.md`, no escribe el
    `_MANIFIESTO.md` —en todo `core/` y `scripts/` no lo escribe nadie— y deja el
    catalogo en `01_Procesado/`. Ese estado tiene que verse, porque el mensaje de exito
    del motor decia «organizada» sobre el.
    """
    case_dir = _caso(tmp_path, artefactos=("INDICE.md", "CRONOLOGIA.md"), catalogo=True)
    r = sle.estado(case_dir).artefactos
    assert r.estado == va.FALLO
    assert r.evidencia["faltan"] == ["_MANIFIESTO.md"]


# ---------------------------------------------------------------------------
# el texto de la solicitud
# ---------------------------------------------------------------------------


def test_la_solicitud_nombra_el_caso_y_la_skill(tmp_path: Path) -> None:
    """Lo que la UI le da a Paola y Ana en vez de un boton que no puede terminar.

    Tiene que servir para copiar y pegar: quien lo recibe necesita saber **que caso** y
    **que se le pide**, y la skill es hoy el unico constructor que gobierna.
    """
    e = sle.estado(_caso(tmp_path, sala=False))
    assert "W-00TEST" in e.solicitud
    assert "organizar-sala-lectura" in e.solicitud


def test_la_solicitud_de_una_sala_incompleta_dice_que_le_falta(tmp_path: Path) -> None:
    e = sle.estado(_caso(tmp_path, artefactos=("INDICE.md", "CRONOLOGIA.md"),
                         catalogo=True))
    assert "_MANIFIESTO.md" in e.solicitud


def test_la_solicitud_identifica_por_w_code_y_no_por_el_nombre_de_la_carpeta(
    tmp_path: Path,
) -> None:
    """El identificador es el W-code, nunca el `case_id`. Y no es una preferencia.

    Un `case_id` es `BaXXX - <direccion> - (W-XXXXX) - <tipo>`: **lleva la direccion del
    inmueble dentro**, o sea PII de un tercero, y `docs/SEGURIDAD_DATOS.md` §16 prohibe
    que aparezca en un mensaje — lo documenta `case_locator._w_code_de`. Este texto se
    escribe para copiar y pegar en un chat o un correo, asi que sale del entorno. El
    W-code identifica sin exponer.
    """
    case_dir = _caso(tmp_path, sala=False)
    solicitud = sle.estado(case_dir).solicitud
    assert "W-00TEST" in solicitud
    assert "Sintetico" not in solicitud
    assert case_dir.name not in solicitud


def test_sin_w_code_la_solicitud_lo_dice_en_vez_de_filtrar_la_carpeta(
    tmp_path: Path,
) -> None:
    """Una carpeta no canonica no justifica volcar su nombre al texto.

    El camino facil —«si no hay W-code, pon el nombre de la carpeta»— es justo el que
    filtra la direccion. Se dice que falta y el destinatario pregunta; el coste de
    preguntar es una linea, el de filtrar no se deshace.
    """
    case_dir = tmp_path / "BaRS1 - Calle Inventada 7 - Sin codigo"
    (case_dir / "01_Procesado").mkdir(parents=True)
    solicitud = sle.estado(case_dir).solicitud
    assert "Calle Inventada" not in solicitud
    assert case_dir.name not in solicitud
    assert "sin W-code" in solicitud


# ---------------------------------------------------------------------------
# la propiedad que de verdad importa: esto NO escribe
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kwargs", [
    {"sala": False},
    {},
    {"artefactos": ARTEFACTOS_EN_LA_SALA, "catalogo": True,
     "documentos": ("2025-01-02_encargo.pdf", "sub/adjunto.pdf")},
])
def test_leer_el_estado_no_toca_un_solo_byte(tmp_path: Path, kwargs) -> None:
    """La razon de ser de este modulo es sustituir a uno que escribia.

    Si `estado()` creara la carpeta que no encuentra —un `mkdir(exist_ok=True)` de mas es
    todo lo que hace falta— habriamos cambiado un escritor por otro mas discreto. Se
    sella el arbol por `sha256` antes y despues, y se comparan tambien las RUTAS: un
    fichero nuevo no cambia ningun hash, solo aparece.
    """
    case_dir = _caso(tmp_path, **kwargs)
    antes = _sello(case_dir)
    sle.estado(case_dir)
    assert _sello(case_dir) == antes


def test_un_caso_que_no_existe_no_se_crea_al_preguntarle(tmp_path: Path) -> None:
    fantasma = tmp_path / "no-existe"
    e = sle.estado(fantasma)
    assert e.montada is False
    assert not fantasma.exists()
