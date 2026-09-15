"""La etapa `viabilidad`: la corrida prepara, una sesión remata.

Spec: docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md §5.
"""
import json

from core import viabilidad_json as vj
from scripts import abrir_caso as cli


class _Ident:
    case_id = "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    w_code = "W-TEST01"
    tipo_caso = "Vuelta"


def test_escribe_el_json_y_sale_hecha(tmp_path):
    (tmp_path / "00_Input").mkdir()

    r = cli.etapa_viabilidad(_Ident(), tmp_path, hoy="2026-09-15")

    assert r.estado == "hecha"
    assert vj.ruta(tmp_path).exists()
    assert json.loads(vj.ruta(tmp_path).read_text(encoding="utf-8"))["ref"] == "W-TEST01"


def test_deja_pendiente_lo_que_no_pudo_derivar(tmp_path):
    """El «residuo marcado» de la salida 3 es la mitad del valor de esta etapa: sin él,
    la corrida deja un fichero casi vacío sin decir qué falta."""
    (tmp_path / "00_Input").mkdir()

    r = cli.etapa_viabilidad(_Ident(), tmp_path, hoy="2026-09-15")

    assert r.pendientes
    assert r.pendientes[0].codigo == "viabilidad_sin_rematar"
    assert "equipo" in r.pendientes[0].detalle


def test_si_ya_existe_sale_saltada_y_NO_lo_pisa(tmp_path):
    """Lo único caro del fichero es lo que puso la sesión. Relanzar la corrida no
    puede destruirlo."""
    (tmp_path / "00_Input").mkdir()
    antes = '{"ref": "LO QUE PUSO LA SESION"}'
    vj.ruta(tmp_path).write_text(antes, encoding="utf-8")

    r = cli.etapa_viabilidad(_Ident(), tmp_path, hoy="2026-09-15")

    assert r.estado == "saltada"
    assert vj.ruta(tmp_path).read_text(encoding="utf-8") == antes


def test_case_dir_inexistente_no_tumba_la_corrida(tmp_path):
    """Antes `test_un_fallo_al_escribir_no_tumba_la_corrida`, del pliego: aceptaba
    `hecha` O `fallo` porque quien escribió el plan no sabía cuál de las dos saldría
    con un `case_dir` que ni siquiera existe. Corrido y comprobado, no asumido: el
    resultado real es SIEMPRE `hecha`, nunca `fallo` — `vj.escribir()` crea el árbol
    que falte con `mkdir(parents=True, exist_ok=True)` antes de escribir, así que un
    `case_dir` inexistente no le impide completar la escritura. Se renombra porque
    "un fallo... no tumba la corrida" da por hecho un fallo que aquí no ocurre; lo que
    de verdad protege este test es que la etapa no necesita que `case_dir` exista de
    antemano. Un test que acepta dos resultados opuestos no protege ninguno de los dos.
    """
    r = cli.etapa_viabilidad(_Ident(), tmp_path / "no-existe", hoy="2026-09-15")

    assert r.estado == "hecha"
    assert vj.ruta(tmp_path / "no-existe").exists()


def test_viabilidad_corre_despues_de_todo_y_antes_de_verificar():
    nombres = list(cli.ETAPAS_V2)
    assert nombres.index("viabilidad") < nombres.index("verificar")
    assert nombres.index("sala_maquina") < nombres.index("viabilidad")
    assert nombres[-1] == "verificar", "verificar cierra la corrida"
