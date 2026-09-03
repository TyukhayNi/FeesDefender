"""El cableado de la secuencia detras de `--modo v1`.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §3.
"""
import json

import pytest

from core import apertura_v1 as av1
from core import intake_log
from scripts import abrir_caso as cli


class _Ident:
    case_id = "C"
    w_code = "W-000000"


def test_f13_el_evento_de_cierre_esta_en_el_set_cerrado():
    """F13. `INTAKE_EVENTS` es cerrado: un nombre fuera del set es un evento imposible de
    emitir, y el fallo no aparece hasta que alguien intenta emitirlo."""
    assert "apertura_v1_terminada" in intake_log.INTAKE_EVENTS


def test_el_evento_de_cierre_lleva_el_estado_y_los_pendientes(tmp_path):
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    resultado = av1.ResultadoV1(
        estado=av1.EstadoV1.PREPARADO_CON_PENDIENTES,
        etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="3 ficheros"),),
        pendientes=(av1.PENDIENTE_FUENTES_V3,),
        parada=None,
    )

    cli.registrar_cierre_v1(case_dir, _Ident(), resultado)

    log = case_dir / "00_Input" / "_intake_log.jsonl"
    lineas = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l]
    ev = [l for l in lineas if l["event"] == "apertura_v1_terminada"][-1]
    assert ev["details"]["estado"] == "preparado_con_pendientes"
    assert ev["details"]["pendientes"] == ["fuentes_v3_sin_consultar"]
    assert ev["details"]["etapas"] == [{"nombre": "drive", "estado": "hecha"}]


def _fake(nombre, visto):
    return av1.Etapa(nombre=nombre,
                     correr=lambda: (visto.append(nombre) or
                                     av1.EtapaResultado(nombre=nombre, estado="hecha",
                                                        detalle="ok")))


def test_una_corrida_completa_toca_TODAS_las_fases_de_v1():
    """El criterio que el bloque 4 del §21.5 de la spec pide literalmente."""
    visto = []
    r = cli.secuencia_v1(None, None, folder_id="F", team_id="T",
                         etapas=[_fake(n, visto) for n in cli.ETAPAS_V1])
    assert visto == list(cli.ETAPAS_V1)
    assert r.no_ejecutadas == ()
    assert r.estado == av1.EstadoV1.PREPARADO_CON_PENDIENTES


def test_f24_una_parada_pedida_enumera_las_etapas_que_no_corrieron():
    """F24. Un evento que dice «terminada» sobre una corrida parada a mitad, sin decir que
    faltan dos fases, es un registro falso."""
    visto = []
    r = cli.secuencia_v1(None, None, folder_id="F", team_id="T", hasta="drive",
                         etapas=[_fake(n, visto) for n in cli.ETAPAS_V1])
    assert visto == ["drive"]
    assert r.no_ejecutadas == ("crm", "sala_maquina")
    assert "crm" in " ".join(p.codigo for p in r.pendientes)


def test_f23_el_vocabulario_de_hasta_se_valida_antes_de_todo_efecto():
    """F23. En la rev. 1 un typo pasaba la puerta y reventaba DESPUES del esqueleto."""
    errores = cli.validar_modo("v1", crm="skip", fuente="drive_ev", folder_id="F",
                               hasta="drve")
    assert errores and "drve" in errores[0]
    assert cli.validar_modo("v1", crm="skip", fuente="drive_ev", folder_id="F",
                            hasta="drive") == []


def test_hasta_no_existe_en_modo_libre():
    errores = cli.validar_modo("libre", crm="api", fuente="manual", hasta="drive")
    assert errores and "--hasta" in errores[0]


def test_f14_un_resultado_bloqueado_sale_con_codigo_no_cero():
    assert cli.codigo_de_salida(av1.EstadoV1.BLOQUEADO) != 0
    assert cli.codigo_de_salida(av1.EstadoV1.PREPARADO_CON_PENDIENTES) == 0
    assert cli.codigo_de_salida(av1.EstadoV1.COMPLETO) == 0


def test_f25_la_rama_v1_no_sale_del_proceso_dentro_del_bloque_de_mutex():
    """F25. Con una excepcion en vuelo, `case_mutex.tomado` solo ANOTA la perdida del
    lease en vez de lanzarla (`core/casos/case_mutex.py:640-659`). Un `typer.Exit` dentro
    del `with` convierte una perdida de exclusion en una salida 0 con una nota.

    Se acota a la rama `v1`: el `--dry-run` del modo `libre` tiene el mismo defecto y
    queda deliberadamente fuera de alcance (`MEJORAS #142`).
    """
    import ast
    import inspect
    import textwrap

    arbol = ast.parse(textwrap.dedent(inspect.getsource(cli.main)))
    withs = [n for n in ast.walk(arbol) if isinstance(n, ast.With)]
    assert withs, "el cuerpo de main ya no tiene el bloque de mutex"

    def _es_rama_v1(n):
        # Se compara la ESTRUCTURA y no el texto de `ast.dump`: `dump` renderiza las
        # cadenas con comillas simples, asi que buscar '"v1"' no encuentra nada nunca —
        # una busqueda mutilada que se lee como «no hay rama», que es el error contrario.
        if not isinstance(n, ast.If) or not isinstance(n.test, ast.Compare):
            return False
        izq = n.test.left
        der = n.test.comparators[0] if n.test.comparators else None
        return (isinstance(izq, ast.Name) and izq.id == "modo"
                and isinstance(der, ast.Constant) and der.value == "v1")

    ramas_v1 = [n for w in withs for n in ast.walk(w) if _es_rama_v1(n)]
    assert ramas_v1, "no se encuentra la rama `modo == \"v1\"` dentro del bloque de mutex"
    # Solo el CUERPO de la rama: `ast.walk` sobre el `If` entero recorreria tambien su
    # `else`, donde vive el `Exit` del `--dry-run` del modo `libre` (MEJORAS #142).
    #
    # Y solo los `raise` de `typer.Exit`, no cualquier `raise`. **Acotado el 2026-09-03
    # tras R-C**, y conviene decir por que no es debilitarlo: la propiedad de HA-07 es «no
    # TERMINAR EL PROCESO aqui dentro», porque un `Exit` en vuelo hace que
    # `case_mutex.tomado` se limite a ANOTAR una perdida del lease en vez de lanzarla. Un
    # `raise MutexPerdido` deliberado es justo lo contrario del defecto: es la perdida
    # denunciada en voz alta, y la remediacion de HC-01 lo necesita para no publicar sin
    # ser titular. Prohibirlo bloqueaba el arreglo correcto.
    raises = [n for rama in ramas_v1 for hijo in rama.body for n in ast.walk(hijo)
              if isinstance(n, ast.Raise) and "Exit" in ast.dump(n)]
    assert raises == [], (
        "la rama v1 sale del proceso DENTRO del bloque de mutex: la perdida del lease "
        "quedaria como una nota sobre una salida limpia")
