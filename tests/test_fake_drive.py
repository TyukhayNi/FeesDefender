"""El doble se prueba contra el PARSER REAL y contra fixtures grabadas.

Un doble validado contra el JSON que el propio plan le dicta no prueba nada: es la
circularidad que la 2ª revisión adversarial cazó. Aquí:

- el inventario que emite el doble se parsea con `parse_inventario_lsjson` **de
  producción**, no con una reimplementación;
- las formas de `lsjson` vienen de `tests/_fixtures/rclone_v1735/`, con su procedencia
  declarada en el `README.md` de ese directorio;
- la decisión de exclusión se toma **solo por los flags del comando**, y hay un test
  «con flags / sin flags» que lo demuestra.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._barrera import BINARIO_SINTETICO, REMOTO_SINTETICO, BarreraViolada
from tests._dobles import EjecutorActor, FakeDrive, FakeRclone

FIXTURES = Path(__file__).parent / "_fixtures" / "rclone_v1735"


@pytest.fixture
def cli():
    from scripts import repository_cli
    return repository_cli


def _fake(tmp_path, drive=None, **kw) -> FakeRclone:
    return FakeRclone(drive if drive is not None else {}, raiz_local=tmp_path, **kw)


def _cmd(*resto: str) -> list[str]:
    return [BINARIO_SINTETICO, *resto]


# ---------------------------------------------------------------------------
# El inventario del doble lo valida el PARSER REAL
# ---------------------------------------------------------------------------

def test_el_inventario_del_doble_lo_parsea_produccion(cli, tmp_path):
    fake = _fake(tmp_path, {"00_Input/a.pdf": b"aaa", "01_Procesado/INDICE.md": b"bbb"})
    res = fake(_cmd("lsjson", f"{REMOTO_SINTETICO}", "-R", "--hash", "--fast-list"))

    inv = cli.validar_inventario_texto(res.stdout)      # el de producción, no una copia
    assert set(inv) == {"00_Input/a.pdf", "01_Procesado/INDICE.md"}
    assert inv["00_Input/a.pdf"]["hash"] == fake.drive.md5("00_Input/a.pdf")


@pytest.mark.parametrize("fixture", ["lsjson_local.json", "lsjson_drive.json"])
def test_el_parser_real_digiere_las_fixtures_de_los_dos_backends(cli, fixture):
    """Local y Drive NO son iguales (13 hashes vs 3; `ID` solo en Drive)."""
    inv = cli.parse_inventario_lsjson((FIXTURES / fixture).read_text(encoding="utf-8"))
    assert "00_Input/a.pdf" in inv
    assert inv["00_Input/a.pdf"]["hash"] == "da2859ec2a07a2a1e8d50ae90700141f"
    assert all("IsDir" not in k for k in inv), "los directorios no entran al inventario"


def test_las_tres_variantes_google_native_dan_hash_none(cli):
    """Sin clave `Hashes`, `Hashes: {}` y `Hashes` sin `md5` → las tres `None`.

    La forma que emitiría Drive de verdad está **sin verificar** (`MEJORAS #104`: cero
    Google-native en 3007 ficheros). Lo que sí se fija es que el contrato del parser
    trata igual las tres, que es lo que la Fase 2 va a necesitar.
    """
    texto = (FIXTURES / "lsjson_native.json").read_text(encoding="utf-8")
    inv = cli.parse_inventario_lsjson(texto)
    assert len(inv) == 3
    assert all(v["hash"] is None for v in inv.values())


def test_inventario_vacio_y_truncado_los_rechaza_produccion(cli):
    with pytest.raises(cli.InventarioInvalido):
        cli.validar_inventario_texto((FIXTURES / "lsjson_vacio.json").read_text(encoding="utf-8"))
    with pytest.raises(cli.InventarioInvalido):
        cli.validar_inventario_texto((FIXTURES / "lsjson_truncado.txt").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# La circularidad muerta: el doble decide SOLO por los flags del comando
# ---------------------------------------------------------------------------

def test_copy_con_flags_excluye_y_sin_flags_no(tmp_path):
    """El test que mata la circularidad (A-1 de la 2ª pasada).

    El doble anterior llamaba a `rc.esta_excluido()`, o sea importaba las reglas de
    producción: si alguien quitara `_exclusiones_rclone()` del comando, el doble seguiría
    excluyendo y el test seguiría verde. Ahora **sin flags baja también el protocolo**.
    """
    drive = {"00_Input/_caso.md": b"canon", "00_Input/a.pdf": b"aaa",
             "90_Notas personales/n.md": b"privado"}

    con = tmp_path / "con_flags"
    _fake(tmp_path, dict(drive))(_cmd(
        "copy", REMOTO_SINTETICO, str(con),
        "--exclude", "_caso.md", "--exclude", "90_Notas personales/**"))
    assert (con / "00_Input/a.pdf").exists()
    assert not (con / "00_Input/_caso.md").exists()
    assert not (con / "90_Notas personales/n.md").exists()

    sin = tmp_path / "sin_flags"
    _fake(tmp_path, dict(drive))(_cmd("copy", REMOTO_SINTETICO, str(sin)))
    assert (sin / "00_Input/_caso.md").exists(), (
        "sin --exclude el doble DEBE transferir el protocolo: si excluye por su cuenta, "
        "un cambio de producción que dejara de pasar los flags no rompería ningún test")
    assert (sin / "90_Notas personales/n.md").exists()


def test_el_doble_no_importa_las_reglas_de_produccion():
    """Guard estático: si vuelve un import de `core` aquí, la circularidad ha vuelto.

    Se ancla a **líneas de import**, no a la aparición de la subcadena: el propio
    docstring del doble menciona `from core...` al explicar la prohibición, y buscar la
    subcadena a secas daba un falso positivo. Misma familia que el aserto de #160 que
    pasaba porque `tmp_path` inyectaba la palabra en la salida capturada.
    """
    fuente = Path("tests/_dobles/fake_drive.py").read_text(encoding="utf-8")
    imports = [ln.strip() for ln in fuente.splitlines()
               if ln.strip().startswith(("import ", "from ")) and " import " in ln + " import "]
    ofensores = [ln for ln in imports
                 if ln.startswith(("from core", "import core"))]
    assert not ofensores, (
        f"el doble no puede importar producción para decidir la transferencia: {ofensores}")


# ---------------------------------------------------------------------------
# Contrato de rclone v1.73.5 — códigos de salida y `--log-file`
# ---------------------------------------------------------------------------

def test_files_from_con_filtros_aborta_y_no_crea_log(tmp_path):
    """Medido: `CRITICAL`, rc 1, nada transferido y **el log no se crea**."""
    lista = tmp_path / "lista.txt"
    lista.write_text("a.pdf\n", encoding="utf-8")
    log = tmp_path / "no_deberia_existir.log"
    res = _fake(tmp_path, {"a.pdf": b"x"})(_cmd(
        "copy", str(tmp_path), REMOTO_SINTETICO,
        "--files-from", str(lista), "--exclude", "*.tmp", "--log-file", str(log)))

    assert res.returncode == 1
    assert "should be used alone" in res.stderr
    assert not log.exists(), "la validación de flags ocurre ANTES de inicializar el log"


def test_un_fallo_operativo_si_deja_log(tmp_path):
    """El par del anterior: la frontera es validación-de-flags / ejecución, no fallo/éxito.

    Medido: `copy` de un origen inexistente → rc 3 **con** log de 1408 B.
    """
    log = tmp_path / "si_existe.log"
    res = _fake(tmp_path, {"a.pdf": b"x"}, resultados={("copy", 1): (3, "", "boom")})(
        _cmd("copy", str(tmp_path), REMOTO_SINTETICO, "--log-file", str(log)))

    assert res.returncode == 3
    assert log.exists(), "un fallo de la OPERACIÓN sí deja log; solo el de flags no"


def test_copyto_ausente_da_3_y_moveto_ausente_da_1(tmp_path):
    """En el MISMO test, para que un doble que los unifique no pase.

    El doble heredado devolvía 3 para cualquier fallo de subcomando: aplanaba estos dos
    códigos, que el contrato mide distintos (B0-3 de la 3ª pasada).
    """
    fake = _fake(tmp_path, {})
    r_copyto = fake(_cmd("copyto", f"{REMOTO_SINTETICO}no_existe.md", str(tmp_path / "x")))
    r_moveto = fake(_cmd("moveto", f"{REMOTO_SINTETICO}no_existe.md",
                         f"{REMOTO_SINTETICO}backup/x"))
    assert r_copyto.returncode == 3
    assert r_moveto.returncode == 1


def test_lsjson_de_ruta_ausente_da_3_con_stdout_invalido(cli, tmp_path):
    res = _fake(tmp_path, {"otra/cosa.md": b"x"})(
        _cmd("lsjson", f"{REMOTO_SINTETICO}no_existe"))
    assert res.returncode == 3
    assert res.stdout == "["
    with pytest.raises(cli.InventarioInvalido):
        cli.validar_inventario_texto(res.stdout)


def test_rmdirs_sobre_arbol_no_vacio_da_0_y_no_borra(tmp_path):
    fake = _fake(tmp_path, {"_pendiente_checkin/a.pdf": b"x"})
    antes = fake.drive.snapshot()
    res = fake(_cmd("rmdirs", f"{REMOTO_SINTETICO}_pendiente_checkin"))
    assert res.returncode == 0
    assert fake.drive.snapshot() == antes


def test_check_compara_por_md5_e_ignora_extras_con_one_way(tmp_path):
    """Mismo tamaño y contenido distinto → difiere. Y `--one-way` ignora los extras."""
    local = tmp_path / "caso"
    (local / "sub").mkdir(parents=True)
    (local / "sub" / "a.txt").write_bytes(b"NUEVO")
    fake = _fake(tmp_path, {"sub/a.txt": b"VIEJO", "solo_drive.md": b"extra"})

    r1 = fake(_cmd("check", str(local), REMOTO_SINTETICO, "--one-way"))
    assert r1.returncode == 1, "mismo tamaño, md5 distinto: compara por hash"

    fake.drive.escribir("sub/a.txt", b"NUEVO")
    r2 = fake(_cmd("check", str(local), REMOTO_SINTETICO, "--one-way"))
    assert r2.returncode == 0, "--one-way ignora `solo_drive.md`, extra del destino"

    r3 = fake(_cmd("check", str(local), REMOTO_SINTETICO))
    assert r3.returncode == 1, "sin --one-way el extra del destino SÍ cuenta"


def test_files_from_tolera_entradas_inexistentes(tmp_path):
    """Medido: exit 0, la entrada ausente se omite en silencio."""
    local = tmp_path / "caso"
    local.mkdir()
    (local / "presente.txt").write_bytes(b"aqui")
    lista = tmp_path / "lista.txt"
    lista.write_text("presente.txt\nausente.txt\n", encoding="utf-8")

    fake = _fake(tmp_path, {})
    res = fake(_cmd("copy", str(local), REMOTO_SINTETICO, "--files-from", str(lista)))
    assert res.returncode == 0
    assert fake.drive.rutas() == ["presente.txt"]


def test_backup_dir_recibe_la_version_del_destino(tmp_path):
    local = tmp_path / "caso"
    local.mkdir()
    (local / "f.txt").write_bytes(b"NUEVO")
    fake = _fake(tmp_path, {"f.txt": b"VIEJO"})
    lista = tmp_path / "l.txt"
    lista.write_text("f.txt\n", encoding="utf-8")

    fake(_cmd("copy", str(local), REMOTO_SINTETICO, "--files-from", str(lista),
              "--backup-dir", f"{REMOTO_SINTETICO}_merge_backups/W_TS"))
    assert fake.drive.leer("f.txt") == b"NUEVO"
    assert fake.drive.leer("_merge_backups/W_TS/f.txt") == b"VIEJO"


# ---------------------------------------------------------------------------
# La barrera sigue viva con el doble puesto (B0-1 de la 3ª pasada)
# ---------------------------------------------------------------------------

def test_el_doble_rechaza_una_ruta_local_fuera_de_la_raiz(tmp_path):
    """El agujero que la rev. 3 no vio: doblar `run_rclone` desactiva el proxy.

    `run_rclone` es la ÚNICA superficie de `subprocess` del frontal, así que con el
    doble puesto el proxy no ve nada. Por eso `FakeRclone` invoca el MISMO validador.
    """
    with pytest.raises(BarreraViolada) as exc:
        _fake(tmp_path, {})(_cmd("copyto", str(tmp_path.parent / "fuera.md"),
                                 f"{REMOTO_SINTETICO}x"))
    assert "fuera de la raíz permitida" in str(exc.value)


def test_el_doble_rechaza_el_remote_real(tmp_path):
    from core.config import RCLONE_REMOTE_TL, TEAM_DRIVE_TL
    real = f"{RCLONE_REMOTE_TL},team_drive={TEAM_DRIVE_TL}:CASOS"
    with pytest.raises(BarreraViolada):
        _fake(tmp_path, {})(_cmd("lsjson", real))


def test_subcomando_y_flag_desconocidos_lanzan(tmp_path):
    """Nunca éxito permisivo: un doble que ignora lo que no entiende esconde cambios."""
    with pytest.raises(AssertionError, match="subcomando no soportado"):
        _fake(tmp_path, {})(_cmd("sync", REMOTO_SINTETICO, str(tmp_path)))
    with pytest.raises(AssertionError, match="flag no soportado"):
        _fake(tmp_path, {})(_cmd("lsjson", REMOTO_SINTETICO, "--inventado"))


# ---------------------------------------------------------------------------
# El hook: `armar(n_objetivo)`, one-shot, las fallidas cuentan, y la traza de actores
# ---------------------------------------------------------------------------

def test_el_hook_dispara_en_la_operacion_objetivo_y_no_antes(tmp_path):
    """Sin `n_objetivo` el `xfail` del rollback ajeno es inconstruible.

    Necesita disparar tras la TERCERA operación; un one-shot sin objetivo se habría
    consumido en la primera.
    """
    disparos: list[int] = []
    fake = _fake(tmp_path, {"a.md": b"x"})
    fake.armar(3, lambda n, cmd, drive: disparos.append(n))

    for _ in range(4):
        fake(_cmd("lsjson", REMOTO_SINTETICO))

    assert disparos == [3], "one-shot en la 3ª: ni antes, ni repetido"


def test_las_operaciones_fallidas_tambien_cuentan(tmp_path):
    """Si no contaran, `n_objetivo` se descolocaría al introducir un fallo."""
    disparos: list[int] = []
    fake = _fake(tmp_path, {}, resultados={("lsjson", 1): (3, "[", "boom")})
    fake.armar(2, lambda n, cmd, drive: disparos.append(n))

    fake(_cmd("lsjson", REMOTO_SINTETICO))            # falla, pero cuenta como la 1
    fake(_cmd("lsjson", REMOTO_SINTETICO))
    assert disparos == [2]


def test_el_hook_ve_los_efectos_de_su_operacion_objetivo(tmp_path):
    """Dispara DESPUÉS de los efectos y del resultado, antes de devolver al caller.

    El orden decide si el defecto se reproduce: disparando antes de materializar el CP0,
    el segundo actor escribiría `prestado`, el primero lo leería y abortaría bien — y el
    `xfail(strict=True)` rompería la suite por pasar.
    """
    visto: list[bytes | None] = []
    local = tmp_path / "l"
    local.mkdir()
    (local / "f.md").write_bytes(b"subido")
    fake = _fake(tmp_path, {})
    fake.armar(1, lambda n, cmd, drive: visto.append(drive.leer("f.md")))

    fake(_cmd("copyto", str(local / "f.md"), f"{REMOTO_SINTETICO}f.md"))
    assert visto == [b"subido"]


def test_la_traza_distingue_los_actores(tmp_path):
    """Con una instancia compartida, sin etiquetar no hay forma de asertar causalidad."""
    fake = _fake(tmp_path, {"a.md": b"x"})
    a, b = EjecutorActor(fake, "A"), EjecutorActor(fake, "B")

    a(_cmd("lsjson", REMOTO_SINTETICO))
    b(_cmd("lsjson", REMOTO_SINTETICO))
    a(_cmd("copyto", f"{REMOTO_SINTETICO}a.md", str(tmp_path / "a.md")))

    assert fake.traza_actores == [("A", "lsjson"), ("B", "lsjson"), ("A", "copyto")]


def test_las_operaciones_del_hook_entran_en_la_secuencia(tmp_path):
    """Lo que el hook provoque se numera igual y queda en el `registro` con su actor."""
    fake = _fake(tmp_path, {"a.md": b"x"})
    a, b = EjecutorActor(fake, "A"), EjecutorActor(fake, "B")
    fake.armar(1, lambda n, cmd, drive: b(_cmd("lsjson", REMOTO_SINTETICO)))

    a(_cmd("lsjson", REMOTO_SINTETICO))

    assert fake.n_operaciones == 2
    assert fake.traza_actores == [("A", "lsjson"), ("B", "lsjson")]
    assert len(fake.registro) == 2


# ---------------------------------------------------------------------------
# `cmds` es alias contractual, y `FakeDrive` da los snapshots que la matriz necesita
# ---------------------------------------------------------------------------

def test_cmds_es_el_mismo_objeto_que_registro(tmp_path):
    fake = _fake(tmp_path, {"a.md": b"x"})
    fake(_cmd("lsjson", REMOTO_SINTETICO))
    assert fake.cmds is fake.registro


def test_bytes_snapshot_permite_exigir_supervivencia_identica(tmp_path):
    fake = _fake(tmp_path, {"log.jsonl": b'{"a":1}\n\n{"b":"\xff"}'})
    antes = fake.drive.bytes_snapshot()
    fake(_cmd("lsjson", REMOTO_SINTETICO))
    assert fake.drive.bytes_snapshot() == antes
    assert antes["log.jsonl"].endswith(b'\xff"}'), "los bytes crudos se conservan"
