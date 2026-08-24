"""El inventario AST de llamadores del localizador (Fase 1, Task 6, Step 0).

Es la lista de trabajo de la migración y el insumo del guard, así que su propio
recuento tiene que estar contratado: un inventario que se equivoca al contar no
puede ser la base de nada.

Lo que se prueba aquí es el **mecanismo** sobre fuentes sintéticas, no la cifra del
repo. Fijar «95 llamadas» en un test lo convertiría en un cepo que hay que reajustar
en cada commit — el mismo modo de fallo que el conteo de la suite que estuvo rancio
dos meses y medio en `CLAUDE.md`. Lo que sí se fija es que el mecanismo distinga
llamada de mención, que es el defecto que R7 encontró (H7-14).
"""
from __future__ import annotations

import io

import pytest

from scripts import inventario_localizador as inv


def _repo(tmp_path, **ficheros):
    """Un árbol sintético con la forma que el inventario espera."""
    for rel, cuerpo in ficheros.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        io.open(p, "w", encoding="utf-8", newline="\n").write(cuerpo)
    for d in ("core", "scripts", "tests"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


# ------------------------------------------------ llamada frente a mención

def test_una_mencion_en_un_comentario_no_es_una_llamada(tmp_path):
    """H7-14 en una línea: el «80 ficheros» del plan contaba menciones."""
    raiz = _repo(tmp_path, **{"core/m.py": "# ojo con caso_path aqui\nx = 1\n"})
    assert inv.inventariar(raiz) == []


def test_una_mencion_en_un_import_no_es_una_llamada(tmp_path):
    raiz = _repo(tmp_path, **{"core/m.py": "from core.config import caso_path\n"})
    assert inv.inventariar(raiz) == []


def test_una_mencion_en_un_docstring_no_es_una_llamada(tmp_path):
    raiz = _repo(tmp_path, **{"core/m.py": '"""Usa caso_path para resolver."""\n'})
    assert inv.inventariar(raiz) == []


def test_una_llamada_si_se_cuenta(tmp_path):
    raiz = _repo(tmp_path, **{"core/m.py": "d = caso_path('W-1')\nd.mkdir()\n"})
    sitios = inv.inventariar(raiz)
    assert len(sitios) == 1
    assert sitios[0].simbolo == "caso_path"
    assert sitios[0].linea == 1


def test_una_llamada_por_atributo_tambien_cuenta(tmp_path):
    """`config.caso_path(...)` es una llamada igual que `caso_path(...)`."""
    raiz = _repo(tmp_path, **{"core/m.py": "d = config.caso_path('W-1')\nd.mkdir()\n"})
    assert len(inv.inventariar(raiz)) == 1


def test_la_definicion_no_se_cuenta_como_llamador(tmp_path):
    raiz = _repo(tmp_path, **{"core/m.py": "def caso_path(x):\n    return x\n"})
    assert inv.inventariar(raiz) == []


def test_un_fichero_no_parseable_no_tumba_el_inventario(tmp_path):
    """Un `.py` roto a medio editar no puede reventar la lista de trabajo."""
    raiz = _repo(tmp_path, **{
        "core/roto.py": "def (((\n",
        "core/bueno.py": "d = caso_path('W-1')\nd.mkdir()\n",
    })
    assert len(inv.inventariar(raiz)) == 1


# ------------------------------------------------------ ámbito y propuesta

def test_distingue_produccion_de_test(tmp_path):
    raiz = _repo(tmp_path, **{
        "core/m.py": "d = caso_path('W-1')\nd.mkdir()\n",
        "tests/test_m.py": "d = caso_path('W-1')\nd.mkdir()\n",
    })
    ambitos = {s.fichero: s.ambito for s in inv.inventariar(raiz)}
    assert ambitos == {"core/m.py": "produccion", "tests/test_m.py": "test"}


def test_streamlit_app_en_la_raiz_cuenta_como_produccion(tmp_path):
    raiz = _repo(tmp_path, **{"streamlit_app.py": "d = caso_path('W-1')\nd.mkdir()\n"})
    sitios = inv.inventariar(raiz)
    assert [s.ambito for s in sitios] == ["produccion"]


def test_el_detector_de_ausencia_se_propone_como_buscar(tmp_path):
    """Los 27 detectores: comprueban la ausencia y siguen con una rama elegante."""
    raiz = _repo(tmp_path, **{"core/m.py":
                              "p = caso_path('W-1') / '_caso.md'\n"
                              "if not p.exists():\n"
                              "    return []\n"})
    assert inv.inventariar(raiz)[0].propuesta == inv.BUSCAR


def test_el_escritor_se_propone_como_localizar(tmp_path):
    raiz = _repo(tmp_path, **{"core/m.py":
                              "d = caso_path('W-1') / 'sub'\n"
                              "d.mkdir(parents=True, exist_ok=True)\n"})
    assert inv.inventariar(raiz)[0].propuesta == inv.LOCALIZAR


def test_la_puerta_de_alta_se_propone_como_destino(tmp_path):
    raiz = _repo(tmp_path, **{"core/m.py":
                              "def ensure_case(cid):\n"
                              "    d = caso_path(cid)\n"
                              "    d.mkdir()\n"})
    assert inv.inventariar(raiz)[0].propuesta == inv.DESTINO


@pytest.mark.parametrize("cuerpo,motivo", [
    ("d = caso_path('W-1')\nif d.exists():\n    d.mkdir()\n", "no es inequivoca"),
    ("d = caso_path('W-1')\nreturn d\n", "hay que leerlo"),
])
def test_lo_dudoso_va_a_REVISAR_y_no_a_un_cubo_comodo(tmp_path, cuerpo, motivo):
    """La heurística no reparte por comodidad: lo ambiguo lo firma una persona.

    Es lo contrario del modo de fallo que R7 castigó — clasificar de más para que la
    lista parezca cerrada. Un cubo REVISAR grande es información honesta.
    """
    raiz = _repo(tmp_path, **{"core/m.py": cuerpo})
    s = inv.inventariar(raiz)[0]
    assert s.propuesta == inv.REVISAR
    assert motivo in s.motivo


# ------------------------------------------------------------------ resumen

def test_el_resumen_cuadra_con_los_sitios(tmp_path):
    raiz = _repo(tmp_path, **{
        "core/a.py": "d = caso_path('W-1')\nd.mkdir()\n",
        "scripts/b.py": "d = path_for('W-2')\nd.mkdir()\n",
        "tests/test_c.py": "d = caso_path('W-3')\nd.mkdir()\n",
    })
    sitios = inv.inventariar(raiz)
    r = inv.resumen(sitios)
    assert r["llamadas_total"] == 3
    assert r["llamadas_produccion"] == 2
    assert r["ficheros_produccion"] == 2
    assert sum(r["por_propuesta"].values()) == r["llamadas_produccion"]


def test_el_resumen_reparte_cada_sitio_de_produccion_en_exactamente_un_cubo(tmp_path):
    """Sin solapes ni huecos: si la suma no cuadra, la lista de trabajo miente."""
    raiz = _repo(tmp_path, **{
        "core/a.py": "d = caso_path('W-1')\nd.mkdir()\n",
        "core/b.py": "p = caso_path('W-2')\nif not p.exists():\n    return []\n",
        "core/c.py": "d = caso_path('W-3')\nreturn d\n",
    })
    r = inv.resumen(inv.inventariar(raiz))
    assert sum(r["por_propuesta"].values()) == 3


def test_el_inventario_del_repo_real_corre_y_encuentra_produccion():
    """Humo sobre el repo de verdad: que el mecanismo no depende de fixtures.

    No se fija la cifra a propósito — un número clavado aquí queda rancio en cuanto
    alguien añade una llamada, y entonces el test deja de medir para estorbar.
    """
    from pathlib import Path
    raiz = Path(inv.__file__).resolve().parents[1]
    r = inv.resumen(inv.inventariar(raiz))
    assert r["llamadas_produccion"] > 0
    assert r["ficheros_produccion"] > 0
    assert r["llamadas_total"] >= r["llamadas_produccion"]
