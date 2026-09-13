"""El lector de estado de la sala de lectura: dice en que punto esta, sin tocarla.

Sale de la fila #30 (`[APER-70]`). El boton «📚 Sala de lectura» de Streamlit disparaba
`core.sala_lectura.organizar`, un constructor **declarado muerto en su propia primera
linea**, y lo disparaban Paola y Ana, que no tocan codigo. La decision fue que gobierna la
skill `organizar-sala-lectura`, que **no corre desde Streamlit**: corre en Cowork o en
Claude Code. Asi que la UI no puede montar la sala — y lo que si puede, y no hacia, es
**decir si esta montada y que le falta**.

Todo lo de aqui es de LECTURA. Que eso sea cierto no se deja a la buena fe: hay un test
que sella el arbol entero —ficheros por `sha256` y **directorios por su ruta**— y vuelve a
compararlo despues de llamar, con sus dos controles positivos al lado. La primera version del
sello solo miraba ficheros y daba VERDE ante un `mkdir`; lo midio la R1 adversarial (H-03).
"""
from __future__ import annotations

import hashlib
import os
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
    """Huella del arbol: ruta relativa de cada entrada + `sha256` si es fichero.

    **Los DIRECTORIOS entran en la huella, y esa linea la compro la R1 adversarial.** La
    primera version solo recorria ficheros regulares, asi que un `mkdir` de un directorio
    vacio —justo la escritura mas probable de un lector que «se asegura» de que la carpeta
    existe— no cambiaba el sello y el test daba **VERDE**. El revisor lo demostro
    sustituyendo `sle.estado` por una version que hace `mkdir` y corriendo el cuerpo
    original del test: `control_mkdir: ["VERDE", "VERDE", "VERDE"]` (R1, H-03).

    Sigue sin cubrir —y se dice, porque prometer mas es el defecto que esto remedia—
    metadatos (`mtime`, atributos), escrituras transitorias que restauren los mismos
    bytes, y cualquier efecto fuera de `raiz`.
    """
    out = []
    for p in sorted(raiz.rglob("*")):
        if p.is_dir():
            out.append((str(p.relative_to(raiz)) + "/", "<dir>"))
        elif p.is_file():
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


def test_la_sala_del_motor_deprecado_acusa_el_manifiesto_que_le_falta(
    tmp_path: Path,
) -> None:
    """El caso REAL medido en W-030TZY y W-02NHNC (`MEJORAS #221`).

    El motor escribe `INDICE.md`, `CRONOLOGIA.md` **y** el catalogo en `01_Procesado/`
    (`catalogo_documental.save_catalog`): son **tres** de los cuatro que el contrato exige,
    dos de ellos dentro de la sala. El que no escribe es el `_MANIFIESTO.md`. Ese estado
    tiene que verse, porque el mensaje de exito del motor decia «organizada» sobre el.

    **El nombre decia «los dos que le faltan» y el aserto siempre exigio uno** — R1, H-07.
    Mezclaba el inventario de la sala con el del expediente: «dos de los cuatro» es cierto
    *dentro de la sala* y falso *en el expediente*, y la frase no decia cual de los dos.

    Sobre el manifiesto: no hay ningun **generador** en `core/` ni en `scripts/`. Si hay
    quien lo **reescribe** cuando ya existe (`scripts/redate_whatsapp_anexos.py`), que es
    otra cosa (R1, H-08).
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


@pytest.mark.parametrize("kwargs", [
    {"sala": False},
    {},
    {"artefactos": ARTEFACTOS_EN_LA_SALA, "catalogo": True,
     "documentos": ("2025-01-02_encargo.pdf",)},
])
def test_control_positivo_el_sello_ve_un_directorio_nuevo(tmp_path: Path, kwargs) -> None:
    """El instrumento del test de arriba, probado contra la escritura que se le escapaba.

    Sin esto, `test_leer_el_estado_no_toca_un_solo_byte` es una guarda que nadie ha visto
    morder: daba verde ante un `mkdir` y nadie lo sabia hasta que la R1 lo midio (H-03).
    Aqui se crea el directorio a mano —no lo crea `estado()`— y se exige que el sello
    **cambie**. Si algun dia alguien simplifica `_sello` a solo ficheros, esto se pone rojo.
    """
    case_dir = _caso(tmp_path, **kwargs)
    antes = _sello(case_dir)
    (case_dir / "01_Procesado" / "_directorio_nuevo").mkdir(parents=True)
    assert _sello(case_dir) != antes


def test_control_positivo_el_sello_ve_un_fichero_nuevo(tmp_path: Path) -> None:
    case_dir = _caso(tmp_path)
    antes = _sello(case_dir)
    (case_dir / "01_Procesado" / "colado.txt").write_text("x", encoding="utf-8")
    assert _sello(case_dir) != antes


# ---------------------------------------------------------------------------
# El layout de la SKILL, que es el constructor que gobierna (R1, H-01)
# ---------------------------------------------------------------------------


def _caso_de_la_skill(tmp_path: Path) -> Path:
    """Una sala montada como la monta la skill: los CUATRO artefactos dentro.

    Es el layout de `SKILL.md` §estructura, y el que su propio `verificar_sala.py` asume
    al excluir esos cuatro nombres del recuento de documentos.
    """
    case_dir = tmp_path / "BaRS1 - Sintetico - (W-00TEST) - Impago"
    sala = case_dir / "01_Procesado" / "Sala lectura"
    sala.mkdir(parents=True)
    for nombre in (*ARTEFACTOS_EN_LA_SALA, CATALOGO):
        (sala / nombre).write_text(f"# {nombre}\n", encoding="utf-8")
    (sala / "2025-01-02_encargo.pdf").write_text("contenido\n", encoding="utf-8")
    return case_dir


def test_una_sala_montada_por_la_skill_no_sale_incompleta(tmp_path: Path) -> None:
    """El hallazgo ALTO de la R1, y el que decidio el NO-SHIP.

    La skill pone el catalogo **dentro** de la sala; `c4` lo buscaba solo en
    `01_Procesado/`, que es donde lo deja el motor deprecado. Consecuencia: la pantalla
    declaraba incompleta una sala recien construida por el constructor que ella misma
    recomienda, y ofrecia pedir un artefacto que ya estaba. Volver a correr la skill no
    lo arreglaba nunca.
    """
    r = sle.estado(_caso_de_la_skill(tmp_path)).artefactos
    assert r.estado == va.OK, r.detalle
    assert r.evidencia["catalogo_en"] == "sala"


def test_el_catalogo_de_la_skill_no_se_cuenta_como_documento(tmp_path: Path) -> None:
    """Y la otra mitad del mismo hallazgo: el catalogo inflaba el recuento en uno.

    La exclusion razonaba que el catalogo «vive fuera», cierto solo del motor retirado.
    """
    assert sle.estado(_caso_de_la_skill(tmp_path)).n_documentos == 1


def test_el_layout_del_motor_deprecado_sigue_valiendo(tmp_path: Path) -> None:
    """Aceptar el de la skill no puede romper el del motor: los dos conviven hoy.

    La decision de cual es el sitio canonico sigue abierta (`MEJORAS #221`), y un lector
    que solo admitiera el nuevo repetiria el defecto con el signo cambiado.
    """
    case_dir = _caso(tmp_path, artefactos=ARTEFACTOS_EN_LA_SALA, catalogo=True)
    r = sle.estado(case_dir).artefactos
    assert r.estado == va.OK
    assert r.evidencia["catalogo_en"] == "01_Procesado"


# ---------------------------------------------------------------------------
# «No lo se» no es «no hay» (R1, H-02) — y la capitalizacion (R1, H-05)
# ---------------------------------------------------------------------------


def test_si_no_se_puede_enumerar_el_recuento_es_None_y_no_cero(
    tmp_path: Path, monkeypatch
) -> None:
    """Una sala ilegible decia «0 documento(s)», igual que una vacia de verdad.

    `rglob` **suprime** los errores de exploracion. El revisor lo reprodujo inyectando
    `PermissionError` en `os.scandir`: `permiso_listado_denegado: {"n_documentos": 0}`
    sobre una sala que si tenia contenido. Aqui se inyecta en el mismo punto de E/S.
    """
    case_dir = _caso(tmp_path, documentos=("2025-01-02_encargo.pdf",))
    sala = case_dir / "01_Procesado" / "Sala lectura"
    real = os.scandir

    def _revienta(path=".", *a, **k):
        if Path(path) == sala:
            raise PermissionError(13, "denegado")
        return real(path, *a, **k)

    monkeypatch.setattr(os, "scandir", _revienta)
    e = sle.estado(case_dir)
    assert e.montada is True, "la sala existe: eso si se sabe"
    assert e.n_documentos is None, "no se pudo leer, y eso NO es cero"


def test_los_artefactos_en_minusculas_tampoco_cuentan_como_documentos(
    tmp_path: Path,
) -> None:
    """En Windows `INDICE.md` e `indice.md` son el MISMO fichero.

    `c4` los encontraba por una grafia (el filesystem no distingue) y el recuento los
    sumaba como documentos por la otra: los dos numeros de la misma pantalla, discrepando
    sobre los mismos bytes (R1, H-05).
    """
    e = sle.estado(_caso(tmp_path, artefactos=("indice.md", "cronologia.md",
                                               "_manifiesto.md"),
                         catalogo=True, documentos=("2025-01-02_encargo.pdf",)))
    assert e.n_documentos == 1
