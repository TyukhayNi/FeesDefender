"""Las costuras de V1, contratadas por el extremo que CONSUME.

Remedia la frontera de fondo de la R-B (L6-01..L6-04, L2-02, L3-03): todos los tests de
adaptador inyectaban el colaborador (`intake=`, `pull=`, `correr=`, `etapas=`), y eso los
dejaba ciegos al otro extremo. Medido por dos lentes con sus propios mutantes: se podia
hacer que `apply()` dejara de devolver el status, que la custodia dejara de reenviar
`force`, o que `main` pasara `hasta=None`, **sin un solo test rojo**.

Regla que estos tests encarnan: en una pieza de cableado, al menos un test por costura
recorre el camino por DEFECTO y afirma el efecto donde el valor se consume.
"""
import json

import pytest

from core import apertura_v1 as av1
from core.intake_drive import DriveIntakeResult
from scripts import abrir_caso as cli

#: Salto de linea explicito: escribirlo como escape dentro de estas cadenas es
#: como se rompio este fichero tres veces hoy.
FIN = chr(10)


# --------------------------------------------------------------------------
# Costura 1: `etapa_sala_maquina` -> `sala_maquina.apply` -> el status
# --------------------------------------------------------------------------

@pytest.mark.parametrize("status,estado", [
    ("ok", "hecha"), ("parcial", "hecha"), ("fallo", "fallo"), (None, "hecha"),
])
def test_costura_el_status_de_apply_llega_por_el_camino_POR_DEFECTO(status, estado,
                                                                   monkeypatch):
    """L6-01. Sin `correr=`: si `apply` deja de devolver su status, toda la maquina de
    estados del §24 D4 queda muerta en produccion y ningun test lo notaba."""
    from scripts import sala_maquina

    from scripts.sala_maquina import ResultadoApply
    monkeypatch.setattr(sala_maquina, "apply",
                        lambda case_id=None, **k: ResultadoApply(
                            status_atomizacion=status))

    class _Ident:
        case_id = "C"
        w_code = "W-000000"

    r = cli.etapa_sala_maquina(_Ident())
    assert r.estado == estado
    assert bool(r.pendientes) is (status == "parcial")


def test_costura_apply_recibe_EL_caso_y_no_otro(monkeypatch):
    """L6-10. El doble tenia contador y no espia de valor: apuntar `apply` a otro caso
    sobrevivia."""
    from scripts import sala_maquina

    vistos = []
    from scripts.sala_maquina import ResultadoApply
    monkeypatch.setattr(sala_maquina, "apply",
                        lambda case_id=None, **k: (vistos.append(case_id)
                                                   or ResultadoApply("ok")))

    class _Ident:
        case_id = "BaXX9 - Otro (W-999999) - X"
        w_code = "W-999999"

    cli.etapa_sala_maquina(_Ident())
    assert vistos == ["BaXX9 - Otro (W-999999) - X"]


# --------------------------------------------------------------------------
# Costura 2: `_intake_drive_ev` -> `pull_drive_ev` -> `force`
# --------------------------------------------------------------------------

def test_costura_la_custodia_REENVIA_force_a_quien_lo_consume(tmp_path, monkeypatch):
    """L6-02/L6-03. HA-03 se probaba en el llamador, no donde el parametro se consume:
    `_intake_drive_ev` podia dejar de reenviar `force` sin un solo rojo. Y su `return res`
    podia volverse `None` — que haria fallar SIEMPRE la etapa de Drive — y sobrevivia."""
    vistos = {}

    def _pull(case_id, folder_id, team_id, *, force=False):
        vistos.update(case_id=case_id, folder_id=folder_id, force=force)
        destino = tmp_path / "00_Input" / "01_Drive EV"
        destino.mkdir(parents=True, exist_ok=True)
        return DriveIntakeResult(case_id=case_id, team_id=team_id, folder_id=folder_id,
                                 target_dir=destino, files_after=0, skipped=False)

    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev", _pull)
    monkeypatch.setattr(cli, "_intake_generico", lambda *a, **k: None)

    class _Ident:
        case_id = "C"
        w_code = "W-000000"

    res = cli._intake_drive_ev(_Ident(), tmp_path, "FID", "TID",
                               dry_run=False, force=True)
    assert vistos["force"] is True, "la custodia no reenvia `force` al pull"
    assert res is not None, "la custodia no devuelve el resultado: la etapa fallaria siempre"
    assert res.folder_id == "FID"


# --------------------------------------------------------------------------
# Costura 3: `main` -> `secuencia_v1` -> `hasta`, y el registro durable
# --------------------------------------------------------------------------

@pytest.fixture()
def caso_v1(tmp_path, monkeypatch):
    """Raiz de casos aislada. Mismo montaje que `test_abrir_caso_modo_v1.casos_root`:
    `settings` es un dataclass CONGELADO, asi que se desvia el localizador."""
    from core.casos import case_locator
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    return root


def test_costura_main_PASA_el_hasta_a_la_secuencia(caso_v1, monkeypatch):
    """L6-04. `hasta=hasta` -> `hasta=None` sobrevivia: el flag podia quedar INERTE y el
    informe diria «corrida completa» donde el operador pidio parar."""
    visto = {}

    def _falsa(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None):
        visto["hasta"] = hasta
        return av1.ResultadoV1(
            estado=av1.EstadoV1.PREPARADO_CON_PENDIENTES,
            etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="d"),),
            pendientes=(av1.PENDIENTE_FUENTES_V3,), parada="drive",
            no_ejecutadas=("crm", "sala_maquina"))

    monkeypatch.setattr(cli, "secuencia_v1", _falsa)

    from typer.testing import CliRunner
    CliRunner().invoke(cli.app, [
        "--modo", "v1", "--crm", "skip",
        "--w-code", "W-000000", "--ciudad", "Barcelona",
        "--tipo-caso", "BAD_DEBT", "--codigo-caso", "BaXX8",
        "--sufijo", "Bad debt", "--direccion", "Prueba 1",
        "--folder-id", "FID", "--team-id", "TID", "--hasta", "drive", "--yes",
    ])
    assert visto.get("hasta") == "drive", (
        "`main` no propaga --hasta: el flag queda inerte y nadie se enteraria")


# --------------------------------------------------------------------------
# Costura 4: `main` -> el proceso. Codigo de salida, evento y estado durable.
# --------------------------------------------------------------------------

def _correr_main(monkeypatch, resultado, extra=()):
    """Conduce `main --modo v1` hasta el final con la secuencia doblada."""
    from typer.testing import CliRunner
    monkeypatch.setattr(cli, "secuencia_v1", lambda *a, **k: resultado)
    return CliRunner().invoke(cli.app, [
        "--modo", "v1", "--crm", "skip",
        "--w-code", "W-000000", "--ciudad", "Barcelona",
        "--tipo-caso", "BAD_DEBT", "--codigo-caso", "BaXX7",
        "--sufijo", "Bad debt", "--direccion", "Prueba 2",
        "--folder-id", "FID", "--team-id", "TID", "--yes", *extra,
    ])


def _resultado(estado):
    return av1.ResultadoV1(
        estado=estado,
        etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="d"),),
        pendientes=(av1.PENDIENTE_FUENTES_V3,), parada=None, no_ejecutadas=())


@pytest.mark.parametrize("estado,codigo", [
    (av1.EstadoV1.BLOQUEADO, 1),
    (av1.EstadoV1.PREPARADO_CON_PENDIENTES, 0),
])
def test_costura_el_estado_gobierna_el_CODIGO_DE_SALIDA_DEL_PROCESO(estado, codigo,
                                                                    caso_v1, monkeypatch):
    """L1-03. `codigo_de_salida` se probaba como funcion pura: borrar la salida de `main`
    dejaba todo verde. Un script que invoque la secuencia lee el codigo del PROCESO."""
    res = _correr_main(monkeypatch, _resultado(estado))
    assert res.exit_code == codigo, res.output


def test_costura_main_EMITE_el_evento_y_cierra_la_ronda(caso_v1, monkeypatch):
    """L1-05/L1-06. F13 contrataba la pertenencia del nombre al set cerrado, no la
    EMISION: `registrar_cierre_v1(...) -> pass` no mataba nada. Y nada exigia que `main`
    usara el estado durable, asi que `_apertura_v1.json` podia no existir nunca."""
    res = _correr_main(monkeypatch, _resultado(av1.EstadoV1.PREPARADO_CON_PENDIENTES))
    assert res.exit_code == 0, res.output

    casos = [d for d in caso_v1.rglob("00_Input") if d.is_dir()]
    assert casos, "el esqueleto del caso no se creo"
    entrada = casos[0]

    log = entrada / "_intake_log.jsonl"
    assert log.is_file(), "no se emitio ningun evento"
    eventos = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l]
    cierres = [e for e in eventos if e["event"] == "apertura_v1_terminada"]
    assert cierres, "la corrida no dejo el evento de cierre en el log forense"
    assert cierres[-1]["details"]["estado"] == "preparado_con_pendientes"

    durable = entrada / "_apertura_v1.json"
    assert durable.is_file(), "no se escribio el estado durable por ronda"
    ronda = json.loads(durable.read_text(encoding="utf-8"))
    assert ronda["terminada"], "la ronda quedo abierta tras una corrida con exito"
    assert ronda["estado"] == "preparado_con_pendientes"
    assert ronda["etapas"] == {"drive": "hecha"}


# --------------------------------------------------------------------------
# Costura 5: revalidar -> publicar -> liberar -> salir. Indivisible.
# --------------------------------------------------------------------------

def test_hc02_la_publicacion_ocurre_DENTRO_del_bloque_de_mutex():
    """HC-01/HC-02 de R-C. La rev. anterior publicaba FUERA «para no afirmar un exito que
    la perdida del lease desmiente», y con eso escribia sin exclusion ninguna: la
    intercalacion `R1 abre / R1 libera / R2 abre / R1 cierra` dejaba el fichero con la
    ronda R1 y borraba la evidencia de que R2 seguia en curso.

    Se comprueba estructuralmente porque la propiedad es de ORDEN, no de valor: las dos
    publicaciones tienen que estar dentro del `with`, y el `typer.Exit` fuera.
    """
    import ast
    import inspect
    import textwrap

    arbol = ast.parse(textwrap.dedent(inspect.getsource(cli.main)))
    withs = [n for n in ast.walk(arbol) if isinstance(n, ast.With)]
    assert withs, "el cuerpo de main ya no tiene el bloque de mutex"

    def _llamadas(nodo):
        return {n.func.id for n in ast.walk(nodo)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}

    dentro = set()
    for w in withs:
        for hijo in w.body:
            dentro |= _llamadas(hijo)
    assert "registrar_cierre_v1" in dentro, (
        "el evento forense se emite FUERA del bloque de mutex: eso es escribir sin "
        "exclusion, que es la violacion que el mutex existe para impedir")

    # Y el `Exit` sigue fuera (HA-07): dentro convertiria una perdida del lease en una
    # nota sobre una salida limpia.
    ramas_v1 = [n for w in withs for n in ast.walk(w)
                if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                and isinstance(n.test.left, ast.Name) and n.test.left.id == "modo"]
    raises = [n for r in ramas_v1 for hijo in r.body for n in ast.walk(hijo)
              if isinstance(n, ast.Raise) and "Exit" in ast.dump(n)]
    assert raises == [], "volvio a haber un typer.Exit dentro del bloque de mutex"


def test_hc02_se_revalida_la_titularidad_ANTES_de_publicar(caso_v1, monkeypatch):
    """HC-01. `sostenido()` cede la sesion y la version anterior usaba `with` sin `as`:
    una perdida a mitad de una etapa larga pasaba inadvertida hasta la salida, con dos
    escritores sobre el mismo expediente. Si la titularidad ya no es nuestra, NO se
    publica nada y la ronda queda abierta para que la corrida siguiente avise."""
    import contextlib

    from core.casos import mutex_sesion

    class _SesionPerdida:
        w_code = "W-000000"

        def revalidar(self):
            return False

    @contextlib.contextmanager
    def _sostenido(*a, **k):
        yield _SesionPerdida()

    monkeypatch.setattr(mutex_sesion, "sostenido", _sostenido)
    monkeypatch.setattr(cli, "registrar_cierre_v1",
                        lambda *a, **k: pytest.fail("publico sin ser titular"))

    res = _correr_main(monkeypatch, _resultado(av1.EstadoV1.PREPARADO_CON_PENDIENTES))

    # La propiedad es «no se publica y no se sale 0», no el texto del mensaje: con este
    # doble salta ANTES la propia costura de escritura (`EscrituraSinMutex`), porque una
    # sesion que no esta en el registro de `mutex_sesion` no sostiene nada. Es defensa en
    # profundidad y se deja dicho en vez de forzar el mensaje: afirmar el texto de UNA de
    # las dos guardas ataria el test a cual de ellas salta primero.
    assert res.exit_code != 0, res.output
    # El motivo puede llegar por la salida o como excepcion (la costura la LANZA), asi que
    # se mira en los dos sitios: lo que importa es que el fallo NOMBRE la exclusion y no
    # sea un error cualquiera que pase por bueno.
    motivo = (res.output + " " + str(res.exception or "")).lower()
    assert "mutex" in motivo or "exclusion" in motivo, motivo


def test_hc03_el_evento_forense_se_emite_ANTES_de_cerrar_el_estado(caso_v1, monkeypatch):
    """HC-03. El orden inverso dejaba el JSON diciendo «ronda terminada» sin rastro en el
    log si el append fallaba. El `.jsonl` es append-only y autoritativo; el `estado.json`
    es el marcador derivado."""
    orden = []
    real_ev = cli.registrar_cierre_v1
    real_cerrar = cli.estado_v1.cerrar
    monkeypatch.setattr(cli, "registrar_cierre_v1",
                        lambda *a, **k: (orden.append("evento"), real_ev(*a, **k))[1])
    monkeypatch.setattr(cli.estado_v1, "cerrar",
                        lambda *a, **k: (orden.append("estado"), real_cerrar(*a, **k))[1])

    _correr_main(monkeypatch, _resultado(av1.EstadoV1.PREPARADO_CON_PENDIENTES))
    assert orden == ["evento", "estado"], orden


def test_costura_los_agotados_viajan_desde_el_apply_REAL(tmp_path, monkeypatch):
    """`MEJORAS #144`, el otro extremo de la costura — y la primera versión de este test
    **no valía**: se llamaba «por el camino por defecto» y doblaba `apply`, que es justo
    la función cuyo dato quiere contratar. La mutación vive DENTRO de `apply`, así que el
    doble la hacía invisible: el mutante F38 sobrevivía.

    Aquí corre el `apply` de verdad, sin OCR, porque un documento con los intentos
    agotados **se salta** — así que basta fabricar ese estado en disco.
    """
    from core.utils import file_sha256
    from scripts import sala_maquina

    # Bajo una raiz aislada y resuelto por IDENTIDAD: `--case-dir` exige que el caso este
    # en el catalogo local, y saltarse el resolver seria probar otra cosa.
    from core.casos import case_locator
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    caso = root / "BaXX5 - Prueba (W-000005) - BAD_DEBT"
    entrada = caso / "00_Input"
    entrada.mkdir(parents=True)
    (entrada / "_caso.md").write_text(
        "---" + FIN + "meta:" + FIN
        + "  case_id: BaXX5 - Prueba (W-000005) - BAD_DEBT" + FIN
        + "  id_go: W-000005" + FIN
        + "  tipo_caso: BAD_DEBT" + FIN
        + "  ciudad: Barcelona" + FIN
        + "---" + FIN,
        encoding="utf-8")
    doc = entrada / "imposible.pdf"
    doc.write_bytes(b"%PDF-1.4 roto")
    sha = file_sha256(doc)

    sm_dir = caso / "01_Procesado" / "02_Sala de máquina"
    sm_dir.mkdir(parents=True)
    (sm_dir / sala_maquina._STATE).write_text(
        json.dumps({"procesados": [], "intentos": {sha: 3}, "hashes": {}}),
        encoding="utf-8")

    res = sala_maquina.apply("BaXX5 - Prueba (W-000005) - BAD_DEBT")

    assert res is not None, "apply dejo de devolver su resultado"
    assert res.documentos_agotados == 1, (
        f"el contador de agotados no viaja: {res}. El pendiente del adaptador puede estar "
        "perfecto y no servir de nada si el dato no sale de `apply`.")
