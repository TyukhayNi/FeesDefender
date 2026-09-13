"""Tests de `core.intake_drive_hash` — la vía (a) de `MEJORAS #225`. Sin red, sin rclone.

Lo que estos tests defienden, por orden de lo que costó descubrirlo:

1. **`no_verificable` no se cuenta como `ok`.** Un documento nativo de Google no tiene bytes
   canónicos; sumarlo a los que cuadran convertiría el informe en una mentira tranquilizadora.
2. **`ejecutada=False` no se lee como cero discrepancias.** «No pude mirar» ≠ «no hay».
3. **El listado local lleva el MISMO `--local-encoding` que la copia.** Sin él, los ficheros
   cuyo nombre empieza por espacio saldrían por `ausente` — falso hallazgo justo en los
   ficheros que motivaron el flag.
4. **Los dos listados apuntan a la MISMA población** (mismo team drive, misma carpeta raíz,
   mismo `--drive-skip-shortcuts`) que el `rclone copy` del pull.
"""

from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core import case_manager
from core.intake_control import es_fichero_de_protocolo
from core.intake_drive_hash import (
    AUSENTE,
    DISCREPA,
    INFORME,
    NO_VERIFICABLE,
    VERIFICADO,
    Verificacion,
    cmd_listar_local,
    cmd_listar_origen,
    comparar,
    escribir_informe,
    lineas_del_grito,
    verificar_pull_por_hash,
)


# ---------------------------------------------------------------------------
# Fixtures (mismo patrón que `test_intake_drive.py`: CASOS_ROOT aislado)
# ---------------------------------------------------------------------------

@pytest.fixture
def caso_ev(tmp_casos_root):
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)
    case_manager.ensure_case("EV-2026-001", titulo="Caso prueba Drive EV",
                             cliente="EV MMC SPAIN, S.L.U.")
    return "EV-2026-001"


# ---------------------------------------------------------------------------
# Ayudas: entradas de `rclone lsjson` sintéticas
# ---------------------------------------------------------------------------

def entrada(path: str, size: int | None = 1024, sha: str | None = "a" * 64) -> dict:
    e: dict = {"Path": path, "Name": path.rsplit("/", 1)[-1], "IsDir": False}
    if size is not None:
        e["Size"] = size
    if sha is not None:
        e["Hashes"] = {"sha256": sha}
    return e


# ---------------------------------------------------------------------------
# comparar — el contraste puro
# ---------------------------------------------------------------------------

def test_mismo_sha_cuadra():
    v = comparar([entrada("encargo.pdf")], [entrada("encargo.pdf")])
    assert v.ejecutada is True
    assert [f.ruta for f in v.verificados] == ["encargo.pdf"]
    assert v.verificados[0].veredicto == VERIFICADO
    assert not v.discrepan and not v.ausentes and not v.no_verificables
    assert v.hay_hallazgos is False


def test_sha_distinto_discrepa_con_su_delta():
    """El caso real de W-02V48N: 8.044.067 en origen, 8.044.544 en destino (+477)."""
    v = comparar(
        [entrada("firmado.pdf", size=8_044_067, sha="b" * 64)],
        [entrada("firmado.pdf", size=8_044_544, sha="c" * 64)],
    )
    assert not v.verificados
    (f,) = v.discrepan
    assert f.veredicto == DISCREPA
    assert f.delta == 477
    assert f.compatible_con_relleno is True   # +477 y 8.044.544 % 512 == 0
    assert v.hay_hallazgos is True


def test_discrepancia_que_no_es_relleno_no_se_etiqueta_como_tal():
    """Control negativo de `compatible_con_relleno`: si no encaja, no lo dice.

    Sin este control, la propiedad podría estar cableada a True y los dos tests pasarían.
    """
    mas_pequeno = comparar(
        [entrada("x.pdf", size=2_000, sha="b" * 64)],
        [entrada("x.pdf", size=1_024, sha="c" * 64)],
    ).discrepan[0]
    assert mas_pequeno.delta == -976
    assert mas_pequeno.compatible_con_relleno is False

    no_alineado = comparar(
        [entrada("y.pdf", size=1_000, sha="b" * 64)],
        [entrada("y.pdf", size=1_500, sha="c" * 64)],
    ).discrepan[0]
    assert no_alineado.delta == 500
    assert no_alineado.compatible_con_relleno is False   # 1500 % 512 != 0


def test_origen_sin_sha256_es_no_verificable_y_NO_cuenta_como_cuadrado():
    """Un nativo de Google (Size -1, sin Hashes) no tiene bytes canónicos.

    Este es el test que impide la mentira tranquilizadora: si el módulo tratara la ausencia
    de checksum en origen como «cuadra», el informe diría que todo está bien.
    """
    v = comparar(
        [entrada("hoja.xlsx", size=-1, sha=None)],
        [entrada("hoja.xlsx", size=29_696, sha="d" * 64)],
    )
    assert len(v.verificados) == 0
    assert len(v.discrepan) == 0
    (f,) = v.no_verificables
    assert f.veredicto == NO_VERIFICABLE
    assert "no declara sha256" in f.motivo
    assert f.delta is None          # restar contra -1 no significaría nada
    assert v.hay_hallazgos is False  # no es un hallazgo: es una imposibilidad declarada


def test_local_sin_hash_es_no_verificable_con_otro_motivo():
    """Distinguir «el origen no publica checksum» de «no pude hashear la copia»."""
    v = comparar([entrada("a.pdf")], [entrada("a.pdf", sha=None)])
    (f,) = v.no_verificables
    assert "hashear la copia local" in f.motivo
    assert not v.verificados and not v.discrepan


def test_fichero_del_origen_que_falta_en_destino_sale_ausente():
    v = comparar([entrada("a.pdf"), entrada("b.pdf")], [entrada("a.pdf")])
    assert [f.ruta for f in v.verificados] == ["a.pdf"]
    (f,) = v.ausentes
    assert f.ruta == "b.pdf" and f.veredicto == AUSENTE
    assert v.hay_hallazgos is True


def test_fichero_del_destino_que_el_origen_no_lista_sale_sobrante():
    v = comparar([entrada("a.pdf")], [entrada("a.pdf"), entrada("viejo.pdf")])
    assert v.sobrantes == ("viejo.pdf",)
    assert v.hay_hallazgos is False   # es procedencia por mirar, no un fallo del pull


def test_sha_se_compara_sin_distinguir_caja():
    v = comparar([entrada("a.pdf", sha="AB" * 32)], [entrada("a.pdf", sha="ab" * 32)])
    assert len(v.verificados) == 1


def test_subcarpetas_y_separadores_se_normalizan():
    v = comparar([entrada("Planos/plano.pdf")], [entrada("Planos\\plano.pdf")])
    assert len(v.verificados) == 1


def test_los_directorios_del_listado_no_se_cuentan():
    v = comparar([{"Path": "Planos", "IsDir": True}, entrada("a.pdf")], [entrada("a.pdf")])
    assert v.total_origen == 1


def test_total_origen_es_la_suma_de_las_cuatro_cestas():
    v = comparar(
        [entrada("ok.pdf"), entrada("mal.pdf", sha="b" * 64),
         entrada("falta.pdf"), entrada("nativo.xlsx", size=-1, sha=None)],
        [entrada("ok.pdf"), entrada("mal.pdf", sha="c" * 64),
         entrada("nativo.xlsx", size=1, sha="d" * 64)],
    )
    assert (len(v.verificados), len(v.discrepan), len(v.ausentes),
            len(v.no_verificables)) == (1, 1, 1, 1)
    assert v.total_origen == 4


# ---------------------------------------------------------------------------
# «No pude mirar» ≠ «no hay»
# ---------------------------------------------------------------------------

def test_no_ejecutada_no_se_lee_como_cero_discrepancias():
    v = Verificacion(ejecutada=False, motivo="rclone no encontrado")
    assert v.total_origen == 0
    assert v.hay_hallazgos is False           # no hay hallazgos porque no se miró
    assert "NO EJECUTADA" in v.resumen()      # y el resumen lo dice, no da un cero
    assert v.a_dict()["ejecutada"] is False
    assert "NO EJECUTADA" in "\n".join(lineas_del_grito(v))


@pytest.mark.parametrize(
    "fallo, esperado",
    [
        ({"side_effect": FileNotFoundError()}, "no encontrado"),
        ({"side_effect": subprocess.TimeoutExpired(cmd="rclone", timeout=1)}, "timeout"),
        ({"returncode": 3, "stdout": "", "stderr": "boom"}, "exit 3"),
        ({"returncode": 0, "stdout": "no soy json", "stderr": ""}, "no es JSON"),
        ({"returncode": 0, "stdout": '{"Path": "a"}', "stderr": ""}, "no es una lista"),
    ],
)
def test_todos_los_fallos_del_listado_vuelven_como_no_ejecutada(monkeypatch, tmp_path, fallo, esperado):
    """Incluye el `returncode 0` con salida ilegible: se verifica por RESULTADO, no por status."""
    if "side_effect" in fallo:
        def _run(*a, **kw):
            raise fallo["side_effect"]
    else:
        def _run(*a, **kw):
            m = MagicMock(spec=subprocess.CompletedProcess)
            m.returncode = fallo["returncode"]
            m.stdout = fallo["stdout"]
            m.stderr = fallo["stderr"]
            return m
    monkeypatch.setattr("core.intake_drive_hash.subprocess.run", _run)

    v = verificar_pull_por_hash(tmp_path, "folder", "team",
                                remote="gdrive_ev", local_encoding="Slash")
    assert v.ejecutada is False
    assert esperado in v.motivo


def test_fallo_solo_del_listado_local_tambien_es_no_ejecutada(monkeypatch, tmp_path):
    """Control: el origen lista bien y el destino no. No debe salir «todo ausente»."""
    llamadas = {"n": 0}

    def _run(cmd, *a, **kw):
        llamadas["n"] += 1
        m = MagicMock(spec=subprocess.CompletedProcess)
        m.stderr = ""
        if llamadas["n"] == 1:
            m.returncode, m.stdout = 0, json.dumps([entrada("a.pdf")])
        else:
            m.returncode, m.stdout = 1, ""
        return m

    monkeypatch.setattr("core.intake_drive_hash.subprocess.run", _run)
    v = verificar_pull_por_hash(tmp_path, "folder", "team",
                                remote="gdrive_ev", local_encoding="Slash")
    assert v.ejecutada is False
    assert "destino" in v.motivo
    assert not v.ausentes


# ---------------------------------------------------------------------------
# Los comandos: misma población, mismo namespace de nombres
# ---------------------------------------------------------------------------

def test_listado_local_lleva_el_mismo_local_encoding_que_el_pull():
    """Regresión del punto ciego U+2420 (`_LOCAL_ENCODING`, DEAD_ENDS).

    El pull escribe ` NIE Pasaporte.jpg` como `␠NIE Pasaporte.jpg`. Si el listado del destino
    no decodifica con el mismo set, ese fichero no casa con la `Path` del origen y saldría
    como `ausente`: un hallazgo falso, y precisamente en los ficheros más frágiles.
    """
    from core.intake_drive import _LOCAL_ENCODING

    cmd = cmd_listar_local(Path("/x/01_Drive EV"), _LOCAL_ENCODING)
    assert "--local-encoding" in cmd
    assert cmd[cmd.index("--local-encoding") + 1] == _LOCAL_ENCODING
    assert "LeftSpace" in _LOCAL_ENCODING and "LeftPeriod" in _LOCAL_ENCODING
    assert "--hash-type" in cmd and cmd[cmd.index("--hash-type") + 1] == "sha256"


def test_listado_del_origen_direcciona_la_misma_poblacion_que_la_copia(
    caso_ev, tmp_casos_root, monkeypatch
):
    """El `lsjson` del origen y el `copy` del pull comparten los tres args de dirección.

    Es el invariante que hace que el número signifique algo: si el listado apuntara a otra
    carpeta, o no saltara los shortcuts, mediría una población distinta de la que se copió y
    la diferencia sería un artefacto del instrumento.
    """
    from core import intake_drive

    comandos: list[list[str]] = []

    def _run(cmd, *a, **kw):
        comandos.append(list(cmd))
        m = MagicMock(spec=subprocess.CompletedProcess)
        m.returncode, m.stdout, m.stderr = 0, "[]", ""
        return m

    monkeypatch.setattr("subprocess.run", _run)
    monkeypatch.setattr("core.intake_drive_hash.subprocess.run", _run)
    intake_drive.pull_drive_ev(caso_ev, folder_id="F123", team_id="T456")

    copia = next(c for c in comandos if "copy" in c)
    listados = [c for c in comandos if "lsjson" in c]
    assert listados, "el pull no encadenó ningún listado de verificación"
    origen = next(c for c in listados if "--drive-root-folder-id" in c)

    for arg in ("--drive-team-drive", "--drive-root-folder-id"):
        assert copia[copia.index(arg) + 1] == origen[origen.index(arg) + 1]
    assert "--drive-skip-shortcuts" in copia and "--drive-skip-shortcuts" in origen


def test_cmd_listar_origen_pide_sha256_y_solo_ficheros():
    cmd = cmd_listar_origen("gdrive_ev", "F", "T")
    assert cmd[:3] == ["rclone", "lsjson", "gdrive_ev:"]
    assert "--files-only" in cmd and "--recursive" in cmd
    assert cmd[cmd.index("--hash-type") + 1] == "sha256"


# ---------------------------------------------------------------------------
# El protocolo del propio repo no es un documento sobrante
# ---------------------------------------------------------------------------

def test_el_protocolo_del_directorio_no_sale_como_sobrante(monkeypatch, tmp_path):
    destino = tmp_path / "01_Drive EV"
    destino.mkdir()
    locales = [entrada("a.pdf"), entrada(".pulled"), entrada(INFORME)]

    def _run(cmd, *a, **kw):
        m = MagicMock(spec=subprocess.CompletedProcess)
        m.returncode, m.stderr = 0, ""
        m.stdout = json.dumps(locales if "lsjson" in cmd and str(destino) in cmd
                              else [entrada("a.pdf")])
        return m

    monkeypatch.setattr("core.intake_drive_hash.subprocess.run", _run)
    v = verificar_pull_por_hash(destino, "F", "T",
                                remote="gdrive_ev", local_encoding="Slash")
    assert v.ejecutada is True
    assert v.sobrantes == ()
    assert len(v.verificados) == 1


def test_el_informe_esta_declarado_como_fichero_de_protocolo():
    """Si no lo estuviera, el inventario probatorio lo tomaría por documento del cliente."""
    assert es_fichero_de_protocolo(f"01_Drive EV/{INFORME}") is True
    assert es_fichero_de_protocolo(f"01_drive ev/{INFORME}") is True   # Windows
    # …y solo en su ubicación: un homónimo en otra carpeta es documento (MEJORAS #149).
    assert es_fichero_de_protocolo(f"2026-09-10_manual_01/{INFORME}") is False
    assert es_fichero_de_protocolo(INFORME) is False


# ---------------------------------------------------------------------------
# Informe y grito
# ---------------------------------------------------------------------------

def test_escribir_informe_deja_json_legible(tmp_path):
    v = comparar([entrada("a.pdf", size=1_000, sha="b" * 64)],
                 [entrada("a.pdf", size=1_024, sha="c" * 64)])
    ruta = escribir_informe(tmp_path, v)
    assert ruta == tmp_path / INFORME
    d = json.loads(ruta.read_text(encoding="utf-8"))
    assert d["ejecutada"] is True and d["cuadran"] == 0
    assert d["discrepan"][0]["ruta"] == "a.pdf"
    assert d["discrepan"][0]["delta_bytes"] == 24
    assert d["discrepan"][0]["compatible_con_relleno_512"] is True


def test_el_grito_nombra_cada_fichero_que_discrepa():
    """El encargo era «gritar por fichero que no cuadre», no dar un total."""
    v = comparar(
        [entrada("uno.pdf", size=1_000, sha="b" * 64), entrada("dos.pdf"),
         entrada("tres.pdf")],
        [entrada("uno.pdf", size=1_024, sha="c" * 64), entrada("dos.pdf")],
    )
    texto = "\n".join(lineas_del_grito(v))
    assert "DISCREPA" in texto and "uno.pdf" in texto
    assert "AUSENTE" in texto and "tres.pdf" in texto
    assert "compatible con el relleno de #225" in texto
    assert INFORME in texto


def test_el_grito_recorta_pero_dice_cuantos_quedan():
    v = comparar([entrada(f"f{i}.pdf", sha="b" * 64) for i in range(30)],
                 [entrada(f"f{i}.pdf", sha="c" * 64) for i in range(30)])
    lineas = lineas_del_grito(v, maximo=5)
    # Las filas por fichero van sangradas; la cabecera también dice «DISCREPAN» y no cuenta.
    assert sum(1 for ln in lineas if ln.startswith("  DISCREPA")) == 5
    assert any("y 25 más" in ln for ln in lineas)


def test_el_grito_de_un_pull_limpio_no_alarma():
    v = comparar([entrada("a.pdf"), entrada("nativo.xlsx", size=-1, sha=None)],
                 [entrada("a.pdf"), entrada("nativo.xlsx", size=9, sha="d" * 64)])
    texto = "\n".join(lineas_del_grito(v))
    assert texto.startswith("[OK]")
    assert "no cuadran ni descuadran" in texto     # el nativo se declara, no se esconde
