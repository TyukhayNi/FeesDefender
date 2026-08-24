"""Guard permanente del localizador: la escotilla legacy no puede crecer (Task 6, paso 5).

## Por que este guard y no el fichero de clasificacion

`scripts/clasificacion_localizador.py` fue la **lista de trabajo** de la migracion, y
esta indexado por `fichero:linea`. Eso caduca por construccion: las propias ediciones
de la migracion movieron las lineas, y a mitad del trabajo la firma ya apuntaba a
sitios equivocados. Un guard que caduca solo se desactiva o se reajusta a mano, que es
peor que no tenerlo.

Este guard no depende de lineas. Dice una cosa que sigue siendo cierta mientras el
diseno lo sea:

    **`strict=False` es una escotilla declarada, y su censo no crece.**

## Que se cuenta y por que un numero y no cero

El objetivo del diseno es cero llamadas con la escotilla. No se pone `== 0` hoy porque
el paso 5 no retira los llamadores legacy —eso es la Fase 4—, y un guard que exige algo
que el plan aplaza a otra fase es un guard que alguien desactiva la primera semana. Se
fija el censo **actual** como techo: bajar esta bien y no rompe; subir es rojo y hay
que justificarlo moviendo el numero a proposito.

Es la misma polaridad que el §7 del contrato de gobernanza pide para las exenciones:
una lista que **solo puede encoger**.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Techo del censo de `strict=False` en produccion. **Solo puede bajar.**
#: Si un cambio legitimo necesita subirlo, se sube A PROPOSITO y con motivo en el
#: commit — que es justo la conversacion que el guard existe para forzar.
TECHO_ESCOTILLA = 0

RAICES = ("core", "scripts")
SUELTOS = ("streamlit_app.py",)


def _ficheros_produccion():
    for d in RAICES:
        for p in sorted((ROOT / d).rglob("*.py")):
            if "__pycache__" not in p.parts:
                yield p
    for f in SUELTOS:
        if (ROOT / f).is_file():
            yield ROOT / f


def _llamadas_con_escotilla() -> list[str]:
    """Sitios que pasan `strict=False` a `path_for`/`caso_path`, por AST."""
    hallados: list[str] = []
    for ruta in _ficheros_produccion():
        texto = io.open(ruta, encoding="utf-8", errors="replace").read()
        if "strict" not in texto:
            continue
        try:
            arbol = ast.parse(texto)
        except SyntaxError:
            continue
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            f = nodo.func
            nombre = f.id if isinstance(f, ast.Name) else (
                f.attr if isinstance(f, ast.Attribute) else None)
            if nombre not in ("path_for", "caso_path"):
                continue
            for kw in nodo.keywords:
                if kw.arg == "strict" and isinstance(kw.value, ast.Constant) \
                        and kw.value.value is False:
                    hallados.append(f"{ruta.relative_to(ROOT).as_posix()}:{nodo.lineno}")
    return sorted(hallados)


def test_la_escotilla_legacy_no_crece():
    """El censo de `strict=False` en produccion no supera su techo."""
    hallados = _llamadas_con_escotilla()
    assert len(hallados) <= TECHO_ESCOTILLA, (
        f"la escotilla `strict=False` crecio a {len(hallados)} (techo "
        f"{TECHO_ESCOTILLA}): {hallados}\n"
        "Si el uso es legitimo, sube TECHO_ESCOTILLA a proposito y explica por que "
        "en el commit. Si no lo es, usa `localizar()`, `buscar()` o "
        "`destino_de_alta()` segun lo que de verdad quieras preguntar.")


def test_el_guard_no_pasa_en_verde_por_no_mirar_nada():
    """Hermano de los guards de cobertura de G7/G8/G9.

    Un contador que no encuentra el simbolo pasaria siempre. Se comprueba que el
    mecanismo VE las llamadas al localizador, aunque no lleven la escotilla.
    """
    vistas = 0
    for ruta in _ficheros_produccion():
        texto = io.open(ruta, encoding="utf-8", errors="replace").read()
        if "caso_path" in texto or "path_for" in texto:
            vistas += 1
    assert vistas >= 10, (
        f"el guard solo ve {vistas} ficheros que mencionen el localizador; "
        "algo va mal en el recorrido y estaria pasando en verde por vacio")


def test_el_contador_detecta_una_escotilla_sintetica(tmp_path, monkeypatch):
    """Prueba de mutacion del propio guard: si no cuenta, no vale.

    Se inyecta un fichero con `strict=False` en el arbol que el guard recorre y se
    exige que aparezca. Sin esto, `test_la_escotilla_legacy_no_crece` podria estar
    pasando porque el AST nunca casa, no porque no haya escotillas.
    """
    fake = ROOT / "core" / "_zz_guard_probe_tmp.py"
    fake.write_text("from core.config import caso_path\n"
                    "d = caso_path('W-X', strict=False)\n",
                    encoding="utf-8")
    try:
        hallados = _llamadas_con_escotilla()
        assert any("_zz_guard_probe_tmp.py" in h for h in hallados), hallados
    finally:
        fake.unlink(missing_ok=True)


@pytest.mark.parametrize("fuente,esperado", [
    ("d = caso_path('W-X', strict=False)", 1),
    ("d = caso_path('W-X', strict=True)", 0),
    ("d = caso_path('W-X')", 0),
    ("d = path_for('W-X', strict=False)", 1),
    ("d = config.caso_path('W-X', strict=False)", 1),
    ("d = otra_cosa('W-X', strict=False)", 0),
])
def test_el_contador_distingue_los_casos(tmp_path, fuente, esperado):
    """El contador no puede ser un `grep` disfrazado: `strict=True` no cuenta, y
    `strict=False` sobre otra funcion tampoco."""
    fake = ROOT / "core" / "_zz_guard_probe_param.py"
    fake.write_text(fuente + "\n", encoding="utf-8")
    try:
        n = len([h for h in _llamadas_con_escotilla()
                 if "_zz_guard_probe_param.py" in h])
        assert n == esperado, fuente
    finally:
        fake.unlink(missing_ok=True)
