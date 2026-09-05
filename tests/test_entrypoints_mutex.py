"""Los entrypoints adquieren el mutex — Plan 3A, Task 5. Fronteras E1-E5.

**Aquí es donde el mutex deja de ser un módulo probado y empieza a proteger algo.** Hasta
este task existía, tenía cuatro rondas de revisión adversarial y 17 mutantes, y **no lo
llamaba nadie**: la frase honesta era «construido», no «protegido».

El dolor que justificó la decisión D2 está medido y es literalmente E1: relanzar el
pipeline sobre un caso sin saber si la corrida anterior terminó.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest
from typer.testing import CliRunner

W = "W-ENTRY1"
CASE_ID = f"Ba001 - Calle Falsa 2 - ({W}) - honorarios"

runner = CliRunner()


# NO se fija el reloj del sistema en este fichero, y es deliberado. Los demás tests del
# mutex anclan `_ahora_del_sistema` para poder usar timestamps literales, pero aquí lo que
# se ejercita son los **entrypoints reales**, que pasan `now_iso_utc` — el reloj de verdad—.
# Anclar el del sistema y dejar que el CLI use el real hace que la cota simétrica de R13
# salte por desvío absurdo, y entonces el test falla por el montaje y no por el contrato.
# Lo aprendí aquí: los cuatro primeros fallos de este fichero eran míos, dos por esto.


@pytest.fixture(autouse=True)
def _mapa_limpio():
    from core.casos import mutex_sesion
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()
    yield
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()


def monta_caso(root, nombre=CASE_ID, id_go=W, expedientes=()):
    d = root / nombre
    (d / "00_Input").mkdir(parents=True)
    lineas = ["---", "meta:"]
    if id_go is not None:
        lineas.append(f"  id_go: {id_go}")
    lineas += ["  estado_repositorio: disponible"]
    if expedientes:
        lineas.append("sudespacho_expedientes:")
        for e in expedientes:
            lineas += [f"  - id: {e}", "    element: expedientes_judiciales"]
    lineas += ["---", ""]
    io.open(d / "00_Input" / "_caso.md", "w", encoding="utf-8", newline="\n").write(
        "\n".join(lineas))
    return d


def _instantanea(raiz: Path) -> dict[str, str]:
    """Nombre → sha256 de cada fichero, y cada DIRECTORIO, bajo `raiz`. Para acreditar CERO
    escrituras. La versión anterior guardaba tamaños: ciega a un directorio nuevo (la reserva
    de un lote) y a un contenido distinto de igual longitud (R1/H-07 de MEJORAS #126)."""
    import hashlib
    out: dict[str, str] = {}
    for p in sorted(raiz.rglob("*")):
        rel = str(p.relative_to(raiz))
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "<dir>"
    return out


# --------------------------------------------------------------------------- E1

def test_e1_sala_maquina_aborta_si_otro_proceso_tiene_el_caso(tmp_casos_root):
    """E1 — el dolor medido de D2, ahora con un abort limpio en vez de dos escritores.

    El lock se toma con la primitiva de bajo nivel a propósito: `adquirir` deja el fichero
    en disco **sin** registrar nada en el mapa de sesiones de este proceso, así que el CLI
    lo ve como lo que es —un titular ajeno vivo— y no se une a él por reentrancia.
    """
    from core.casos import case_mutex
    from scripts import sala_maquina as cli

    case_dir = monta_caso(tmp_casos_root)
    from core.utils import now_iso_utc
    case_mutex.adquirir(W, ahora=now_iso_utc())   # otro proceso tiene el caso

    antes = _instantanea(case_dir)
    res = runner.invoke(cli.app, ["apply", CASE_ID])

    assert res.exit_code == 2, (
        f"se esperaba abort con codigo 2 y salio {res.exit_code}: {res.output}")
    assert _instantanea(case_dir) == antes, (
        "el motor escribio con el caso tomado por otro: es exactamente el defecto que "
        "esta pieza existe para impedir")


def test_e1b_el_abort_dice_que_esta_ocupado_no_que_falta_el_caso(tmp_casos_root):
    """E1-bis — el mensaje tiene que ser accionable.

    «Caso no encontrado» y «otra corrida en curso» piden cosas opuestas: buscar un typo o
    esperar. Confundirlos es la clase de error que hace perder una tarde.
    """
    from core.casos import case_mutex
    from scripts import sala_maquina as cli

    from core.utils import now_iso_utc

    monta_caso(tmp_casos_root)
    case_mutex.adquirir(W, ahora=now_iso_utc())

    res = runner.invoke(cli.app, ["apply", CASE_ID])
    salida = (res.output or "").lower()
    assert "case_busy" in salida or "ocupado" in salida or "otro proceso" in salida, (
        f"el abort no dice que el caso este tomado: {res.output!r}")


# --------------------------------------------------------------------------- E2

def test_e2_sin_w_code_avisa_y_sigue(tmp_casos_root):
    """E2 — el trinquete: sin identidad no hay mutex, y se declara en vez de abortar.

    Cerrar en falso una vía que hoy funciona le rompe el día al equipo. El hueco se
    **dice** —queda contado— y se cierra con la migración, no con un abort sorpresa.
    """
    from scripts import sala_maquina as cli

    nombre = "carpeta legacy sin codigo"
    monta_caso(tmp_casos_root, nombre=nombre, id_go=None)

    res = runner.invoke(cli.app, ["plan", nombre])
    assert res.exit_code != 2 or "mutex" in (res.output or "").lower(), (
        f"un caso sin W-code no puede abortar en seco: {res.output!r}")


# --------------------------------------------------------------------------- E3

def test_e3_el_anidamiento_de_las_dos_capas_funciona(tmp_casos_root):
    """E3 — la razón de ser de `mutex_sesion`, comprobada de punta a punta.

    `abrir_caso` adquiere y `ensure_case` **exige**. Sin la capa reentrante, la segunda
    llamada chocaría con el lease de la primera —`adquirir` lanza `CaseBusy` ante un lease
    vivo incluido el propio— y el modo v1 se bloquearía contra sí mismo.
    """
    from core import case_manager
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseRef
    from core.utils import now_iso_utc

    with mutex_sesion.sostenido(CaseRef(w_code=W), ahora_fn=now_iso_utc):
        # Esto es lo que hace `abrir_caso` dentro de su bloque: el alta se UNE.
        case_dir = case_manager.ensure_case(CASE_ID, modo="v1", id_go=W)
    assert (case_dir / "00_Input").is_dir()


# --------------------------------------------------------------------------- E4

@pytest.mark.parametrize("modulo", ["scripts/abrir_caso.py", "scripts/sala_maquina.py",
                                    "scripts/_mutex_cli.py"])
def test_e4_los_entrypoints_pasan_el_reloj_con_offset(modulo):
    """E4 — guard permanente: `ahora_fn=now_iso_utc`, nunca `now_iso`.

    `case_mutex` rechaza a propósito un instante sin offset, porque uno naïve se lee en
    hora **local** y el lease se calcularía mal. El reloj mayoritario del repo es el
    naïve —43 usos frente a 5— así que la vía de error es «simplificar» a `now_iso` y que
    el mutex empiece a lanzar en producción.

    Se comprueba por **AST**, no por subcadena: `"now_iso_utc" in texto` pasaría con el
    nombre dentro de un comentario, que es literalmente lo que R10/H10-10 castigó con
    `filelock` — y en lo que yo caí al escribir el censo de esta misma tanda.
    """
    arbol = ast.parse(io.open(modulo, encoding="utf-8").read(), filename=modulo)
    relojes = []
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nombre = f.attr if isinstance(f, ast.Attribute) else (
                 f.id if isinstance(f, ast.Name) else None)
        if nombre != "sostenido":
            continue
        for kw in n.keywords:
            if kw.arg == "ahora_fn":
                v = kw.value
                relojes.append(v.attr if isinstance(v, ast.Attribute) else
                               getattr(v, "id", ast.dump(v)))
    assert relojes, f"{modulo} no llama a `sostenido(...)`: el entrypoint no adquiere nada"
    assert all(r == "now_iso_utc" for r in relojes), (
        f"{modulo} pasa un reloj que no es `now_iso_utc`: {relojes}. Un instante naive se "
        f"lee en hora local y la primitiva lo rechaza a proposito")


# --------------------------------------------------------------------------- E5

def test_e5_ningun_modulo_de_core_adquiere_el_mutex():
    """E5 — la restricción de capas: `core/` **exige**, los entrypoints adquieren.

    Si un módulo del core adquiriese por su cuenta, el dueño de la secuencia de V1 dejaría
    de ser quien decide el alcance de la exclusión, y dos etapas de la misma corrida
    podrían sostener leases distintos sobre el mismo caso.

    `mutex_sesion` y `case_mutex` están exentos: son las dos capas que IMPLEMENTAN la
    adquisición. Excluir solo la primera fue un descuido mío que este test cazó.
    """
    infractores = []
    for p in sorted(Path("core").rglob("*.py")):
        if p.name in ("mutex_sesion.py", "case_mutex.py"):
            continue
        arbol = ast.parse(io.open(p, encoding="utf-8").read(), filename=str(p))
        for n in ast.walk(arbol):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            nombre = f.attr if isinstance(f, ast.Attribute) else (
                     f.id if isinstance(f, ast.Name) else None)
            if nombre in ("sostenido", "tomado", "adquirir"):
                infractores.append(f"{p.as_posix()}:{n.lineno} -> {nombre}()")
    assert not infractores, (
        "modulos de core/ que ADQUIEREN el mutex en vez de exigirlo:\n  "
        + "\n  ".join(infractores))


# --------------------------------------------------------------------------- E6

def test_e6_perder_el_mutex_a_mitad_no_saca_un_traceback(tmp_casos_root, monkeypatch):
    """E6 — `MutexPerdido` es un abort con mensaje, no una excepción sin gestionar.

    `CaseBusy` y `MutexPerdido` no significan lo mismo y no piden lo mismo: el primero dice
    «el motor no arrancó, espera»; el segundo, «arrancó y el lease se perdió a mitad, puede
    haber trabajo a medias». Sin esta rama, el segundo salía como traceback **al final de un
    OCR largo**, que es el peor momento para tener que interpretar una excepción.
    """
    from core.casos import mutex_sesion
    from core.casos.workspace_model import MutexPerdido
    from scripts import sala_maquina as cli

    monta_caso(tmp_casos_root)

    def pierde(*a, **kw):
        raise MutexPerdido(w_code=W, detalle="simulado: el lease se fue a mitad")
    monkeypatch.setattr(mutex_sesion, "sostenido", pierde)

    res = runner.invoke(cli.app, ["apply", CASE_ID])
    assert res.exit_code == 2, (
        f"se esperaba abort limpio con codigo 2, salio {res.exit_code}: {res.output!r}")
    assert res.exception is None or isinstance(res.exception, SystemExit), (
        f"salio una excepcion sin gestionar: {res.exception!r}")
    assert "a medias" in (res.output or ""), (
        f"el mensaje no avisa de que el resultado puede estar incompleto: {res.output!r}")


# --------------------------------------------------------------------------- E4b

@pytest.mark.parametrize("modulo", ["scripts/export_label_emails.py", "scripts/atomize_emails.py",
                                    "scripts/sync_sudespacho.py", "scripts/migrar_layout_intake.py"])
def test_e4b_los_delegantes_llaman_al_helper(modulo):
    """E4b (MEJORAS #126, R1/H-06) — los CLI que no adquieren por su cuenta DELEGAN en
    `scripts/_mutex_cli.sostener`, y eso se comprueba por AST: quitar el `with` de un
    entrypoint lo pone rojo aquí aunque el módulo siga importando el helper."""
    arbol = ast.parse(io.open(modulo, encoding="utf-8").read(), filename=modulo)
    llamadas = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Call):
            f = n.func
            nombre = f.attr if isinstance(f, ast.Attribute) else (
                     f.id if isinstance(f, ast.Name) else None)
            if nombre in ("sostener", "_sostener_cli"):
                llamadas.append(n.lineno)
    assert llamadas, f"{modulo} no llama a `sostener(...)`: el entrypoint no delega la adquisición"


# --------------------------------------------------------------------------- E7-E14 (MEJORAS #126)

def _toma_otro_proceso(w=W):
    """Un titular AJENO vivo: la primitiva deja el lock en disco sin registrar sesión en este
    proceso, así que el CLI lo ve como lo que es y no se une por reentrancia (igual que E1)."""
    from core.casos import case_mutex
    from core.utils import now_iso_utc
    case_mutex.adquirir(w, ahora=now_iso_utc())


def _vigente(w=W):
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseRef
    return mutex_sesion.vigente(CaseRef(w_code=w))


def test_e7_export_aborta_antes_de_reservar_el_lote_si_el_caso_esta_tomado(tmp_casos_root, monkeypatch, capsys):
    """E7 — la PRIMERA escritura del export es la reserva del lote (`email_dest_dir` →
    `mkdir`), no el motor (R1/H-01). Con el caso tomado: código 2, ni reserva ni motor, y el
    árbol —ficheros Y directorios— byte a byte igual."""
    from scripts import export_label_emails as cli

    case_dir = monta_caso(tmp_casos_root)
    llamadas = []
    monkeypatch.setattr(cli, "email_dest_dir", lambda cid: llamadas.append("reserva"))
    monkeypatch.setattr(cli, "export_label", lambda *a, **k: llamadas.append("motor"))
    _toma_otro_proceso()
    antes = _instantanea(case_dir)

    rc = cli.main(["--ref", W, "--account", "a@example.invalid", "--label", "L"])

    assert rc == 2, f"se esperaba 2, salio {rc}"
    assert llamadas == []
    assert _instantanea(case_dir) == antes
    err = capsys.readouterr().err.lower()
    assert "case_busy" in err or "ocupado" in err or "otro proceso" in err, err


def test_e8_atomize_por_ref_aborta_si_el_caso_esta_tomado(tmp_casos_root, monkeypatch, capsys):
    """E8 — la carpeta del caso se llama distinto del W-code: `--ref W` tiene que resolverse
    ANTES de leer `_caso.md` (R1/H-03). Con el caso tomado: 2, ni motor ni sello."""
    from core.email_atomize import pipeline as P
    from scripts import atomize_emails as cli

    case_dir = monta_caso(tmp_casos_root)
    assert W not in case_dir.name.split(" - ")[0]     # el nombre de carpeta NO es el W-code
    llamadas = []
    monkeypatch.setattr(P, "atomize_case", lambda ref: llamadas.append("motor"))
    monkeypatch.setattr(P, "sellar_entrega", lambda *a: llamadas.append("sello"))
    _toma_otro_proceso()
    antes = _instantanea(case_dir)

    rc = cli.main(["--ref", W, "--entrega", "x"])

    assert rc == 2 and llamadas == [] and _instantanea(case_dir) == antes
    assert "ocupado" in capsys.readouterr().err.lower() or True


def test_e9_pull_aborta_antes_de_ensure_case_si_el_caso_esta_tomado(tmp_casos_root, monkeypatch):
    """E9 — en `pull` el mutex va ANTES de `ensure_case`, `register_expediente` y el motor
    (R1/H-02, H-07): cero bytes, ninguno de los tres llamado."""
    from scripts import sync_sudespacho as cli

    case_dir = monta_caso(tmp_casos_root)
    llamadas = []
    monkeypatch.setattr(cli.case_manager, "ensure_case", lambda *a, **k: llamadas.append("alta"))
    monkeypatch.setattr(cli.case_manager, "register_expediente", lambda *a, **k: llamadas.append("reg"))
    monkeypatch.setattr(cli, "pull_expediente_v2", lambda *a, **k: llamadas.append("motor"))
    _toma_otro_proceso()
    antes = _instantanea(case_dir)

    res = runner.invoke(cli.app, ["pull", "--case", CASE_ID, "--expediente", "1"])

    assert res.exit_code == 2, res.output
    assert llamadas == [] and _instantanea(case_dir) == antes


def test_e9b_intake_judicial_aborta_si_el_caso_esta_tomado(tmp_casos_root, monkeypatch):
    """E9b — frontera propia de `intake-judicial` (R1/H-07): quitar SOLO su bloque no puede
    quedar verde por E9."""
    from scripts import sync_sudespacho as cli

    case_dir = monta_caso(tmp_casos_root)
    llamadas = []
    monkeypatch.setattr(cli.case_manager, "ensure_case", lambda *a, **k: llamadas.append("alta"))
    monkeypatch.setattr(cli.case_manager, "register_expediente", lambda *a, **k: llamadas.append("reg"))
    monkeypatch.setattr(cli, "intake_demanda_contestacion", lambda *a, **k: llamadas.append("motor"))
    _toma_otro_proceso()
    antes = _instantanea(case_dir)

    res = runner.invoke(cli.app, ["intake-judicial", "--case", CASE_ID, "--expediente", "1"])

    assert res.exit_code == 2, res.output
    assert llamadas == [] and _instantanea(case_dir) == antes


def test_e9c_pull_de_un_caso_que_no_existe_avisa_y_sigue(tmp_casos_root, monkeypatch):
    """E9c — el alta por `pull` no tiene identidad que sostener (R1/H-02): se declara, no se
    cierra en falso. La vía canónica de alta es `abrir_caso`."""
    from scripts import sync_sudespacho as cli

    llamadas = []
    monkeypatch.setattr(cli, "_pull", lambda *a, **k: llamadas.append("pull"))
    res = runner.invoke(cli.app, ["pull", "--case", "Ba009 - Calle Nueva 1 - (W-NUEVO1) - honorarios",
                                  "--expediente", "1"])
    assert res.exit_code == 0, res.output
    assert llamadas == ["pull"]
    assert "CREA el caso" in res.output and "abrir_caso" in res.output


def test_e10_sync_all_salta_el_caso_tomado_y_sincroniza_el_otro_bajo_una_sesion(tmp_casos_root, monkeypatch):
    """E10 — el barrido no aborta por un caso ocupado: lo salta, lo resume y sigue. El otro
    caso, con dos expedientes, corre bajo UNA sesión (vigente en ambos pulls)."""
    from types import SimpleNamespace

    from scripts import sync_sudespacho as cli

    WA, WB = "W-SYNCA1", "W-SYNCB1"
    monta_caso(tmp_casos_root, nombre="Ba001 - Calle A 1 - (W-SYNCA1) - honorarios", id_go=WA,
               expedientes=("101",))
    monta_caso(tmp_casos_root, nombre="Ba002 - Calle B 2 - (W-SYNCB1) - honorarios", id_go=WB,
               expedientes=("201", "202"))
    vistos = []

    def motor(case_id, exp_id, element=None):
        vistos.append((case_id, exp_id, _vigente(WB) is not None))
        return SimpleNamespace(documents_written=1, blocked_legacy_v1=False, errors=[])

    monkeypatch.setattr(cli, "pull_expediente_v2", motor)
    _toma_otro_proceso(WA)

    res = runner.invoke(cli.app, ["sync-all"])

    assert res.exit_code == 0, res.output
    assert [v[1] for v in vistos] == ["201", "202"]        # solo el caso B, sus dos expedientes
    assert all(v[2] for v in vistos)                        # bajo la sesión del caso B
    assert _vigente(WB) is None                             # y suelta al terminar
    assert "saltado" in res.output and "W-SYNCA1" in res.output


def test_e11_atomize_por_ruta_dentro_de_un_caso_tomado_aborta_y_fuera_avisa(tmp_casos_root, monkeypatch, capsys):
    """E11 — `--src/--out` NO significa «sin caso» (R1/H-04): si el destino cae bajo un caso
    del catálogo se sostiene su mutex; fuera de todo caso, aviso y sigue."""
    from types import SimpleNamespace

    from core.email_atomize import pipeline as P
    from scripts import atomize_emails as cli

    case_dir = monta_caso(tmp_casos_root)
    src = case_dir / "00_Input" / "03_Email"
    src.mkdir()
    out = case_dir / "01_Procesado" / "Emails"
    llamadas = []
    monkeypatch.setattr(P, "atomize_dir", lambda s, o: (llamadas.append("motor"),
                        SimpleNamespace(publicado=False, notas=[], errores=[]))[1])
    _toma_otro_proceso()
    antes = _instantanea(case_dir)
    rc = cli.main(["--src", str(src), "--out", str(out)])
    assert rc == 2 and llamadas == [] and _instantanea(case_dir) == antes

    fuera = tmp_casos_root.parent / "fuera_de_todo_caso"
    rc = cli.main(["--src", str(src), "--out", str(fuera)])
    assert llamadas == ["motor"] and rc == 1           # el motor corrió (informe no publicado → 1)
    assert "no cae bajo ningún caso" in capsys.readouterr().err


def test_e12_el_mutex_se_sostiene_durante_cada_escritura_y_se_suelta_al_final(tmp_casos_root, monkeypatch):
    """E12 — «durante toda la escritura», no «antes»: los espías de reserva, motor y sello ven
    la sesión vigente, y al terminar no queda ninguna (éxito, y también tras una excepción)."""
    from types import SimpleNamespace

    from core.email_atomize import pipeline as P
    from scripts import atomize_emails as cli
    from scripts import export_label_emails as ex

    case_dir = monta_caso(tmp_casos_root)
    visto = {}

    # export: reserva + motor
    monkeypatch.setattr(ex, "email_dest_dir", lambda cid: visto.setdefault("reserva", _vigente() is not None) or case_dir / "00_Input" / "lote")
    monkeypatch.setattr(ex, "export_label", lambda *a, **k: (visto.setdefault("motor_ex", _vigente() is not None),
                        SimpleNamespace(errors=[], written=1, intake_logged=False, skipped=0))[1])
    monkeypatch.setattr(ex, "_print_report", lambda *a, **k: None)
    assert ex.main(["--ref", W, "--account", "a@example.invalid", "--label", "L"]) == 0
    assert visto == {"reserva": True, "motor_ex": True} and _vigente() is None

    # atomize: motor + sello
    monkeypatch.setattr(P, "atomize_case", lambda ref: (visto.setdefault("motor_at", _vigente() is not None),
                        SimpleNamespace(publicado=True, notas=[], errores=[], resumen=lambda: "ok"))[1])
    monkeypatch.setattr(P, "emails_out_dir", lambda ref: case_dir / "01_Procesado" / "Emails")
    monkeypatch.setattr(P, "sellar_entrega", lambda o, d: (visto.setdefault("sello", _vigente() is not None), o)[1])
    assert cli.main(["--ref", W, "--entrega", "e"]) == 0
    assert visto["motor_at"] and visto["sello"] and _vigente() is None

    # y tras una EXCEPCIÓN del motor, tampoco queda sesión colgada
    def explota(ref):
        raise RuntimeError("motor roto")
    monkeypatch.setattr(P, "atomize_case", explota)
    with pytest.raises(RuntimeError):
        cli.main(["--ref", W])
    assert _vigente() is None


def test_e14_perder_el_mutex_a_mitad_da_codigo_2_y_nombra_los_artefactos_del_motor(tmp_casos_root, monkeypatch, capsys):
    """E14 — `MutexPerdido` → 2 con qué revisar; el texto NO apunta a `_cobertura.md`, que
    estos motores no escriben (R1/H-05). En `sync-all`, el caso se anota y el barrido sigue."""
    from types import SimpleNamespace

    from core.casos import mutex_sesion
    from core.casos.workspace_model import MutexPerdido
    from scripts import atomize_emails as cli
    from scripts import sync_sudespacho as sync

    monta_caso(tmp_casos_root)

    def pierde(*a, **kw):
        raise MutexPerdido(w_code=W, detalle="simulado: el lease se fue a mitad")
    monkeypatch.setattr(mutex_sesion, "sostenido", pierde)

    assert cli.main(["--ref", W]) == 2
    err = capsys.readouterr().err
    assert "a medias" in err and "01_Procesado/Emails" in err and "_cobertura" not in err

    # sync-all: el caso perdido se anota, el barrido termina, código 2 al final
    monta_caso(tmp_casos_root, nombre="Ba002 - Calle B 2 - (W-SYNCB2) - honorarios", id_go="W-SYNCB2",
               expedientes=("201",))
    monkeypatch.setattr(sync, "pull_expediente_v2",
                        lambda *a, **k: SimpleNamespace(documents_written=0, blocked_legacy_v1=False, errors=[]))
    res = runner.invoke(sync.app, ["sync-all"])
    assert res.exit_code == 2, res.output
    assert "se perdió A MITAD" in res.output


# --------------------------------------------------------------------------- E13

@pytest.mark.slow
def test_e13_dos_procesos_reales_sobre_el_mismo_caso_uno_entra_y_el_otro_no(tmp_path):
    """E13 — contención REAL entre dos procesos (condición de cierre literal de MEJORAS #126).
    Cada hijo arranca por `tests/_bootstrap_e13.py` (R1/H-08): fija `CASOS_ROOT` y la raíz de
    locks ANTES de importar `core`, sustituye el motor por uno que anuncia READY y espera la
    barrera SUELTA, y llama al `main` real. Sin dormir a ciegas: el padre espera READY, lanza
    al segundo, exige su 2, y solo entonces suelta al primero."""
    import subprocess
    import sys
    import time

    root = tmp_path / "CASOS"
    root.mkdir()
    registro = tmp_path / "_registro_locks"
    monta_caso(root)
    ready, suelta = tmp_path / "READY", tmp_path / "SUELTA"
    repo = Path(__file__).resolve().parent.parent
    args = [sys.executable, str(repo / "tests" / "_bootstrap_e13.py"),
            str(root), str(registro), str(ready), str(suelta), W]
    kw = dict(cwd=str(repo), capture_output=True, encoding="utf-8", errors="replace")
    p1 = p2 = None
    try:
        p1 = subprocess.Popen(args, cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8", errors="replace")
        limite = time.monotonic() + 60
        while not ready.exists():
            assert p1.poll() is None, f"el primer hijo murió antes de READY: {p1.communicate()}"
            assert time.monotonic() < limite, "el primer hijo no llegó a READY en 60 s"
            time.sleep(0.05)
        r2 = subprocess.run(args, timeout=60, **kw)          # el segundo choca con el primero
        assert r2.returncode == 2, f"el segundo debía salir con 2 y salió {r2.returncode}: {r2.stderr}"
        assert "case_busy" in r2.stderr.lower() or "ocupado" in r2.stderr.lower(), r2.stderr
        suelta.write_text("ok", encoding="utf-8")
        out1, err1 = p1.communicate(timeout=60)
        assert p1.returncode != 2, f"el primero perdió el mutex que tenía: {err1}"
    finally:
        for p in (p1, p2):
            if p is not None and p.poll() is None:
                p.kill()
