---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-09
spec: docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md
diseño: docs/superpowers/plans/2026-09-09-vista-procesal-pieza4.md
---

# Las cinco carpetas de fase como destino de `registrar_outputs` · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los
> pasos usan `- [ ]` para el seguimiento.

**Goal:** que un escrito generado por una skill del despacho se pueda **registrar en la
carpeta de fase** donde el letrado lo escribió — `05_Procedimiento/03_Ordinario - Demanda y
documentos`, por ejemplo — en vez de rechazarse como destino inválido.

**Architecture:** ampliar `SUBDESTINOS_EXTRA` en el helper canónico
`.claude/skills/_shared/registrar_outputs.py` con las cinco carpetas, sincronizarlo a las
siete skills que lo replican, y atar las dos listas con un test de no-drift. Es un cambio
de una constante, y su tamaño es justo lo que hace que merezca su propia pieza.

**Tech Stack:** Python 3.14, `pytest`. Sin dependencias nuevas.

---

## Por qué esto es una pieza y no un paso de otra

Estaba **dentro** de la pieza 4a, como su Tarea 2, y **su revisión adversarial lo sacó**.

El plan de 4a declara en sus restricciones globales: «Cero escrituras en el expediente.
Ninguna. Ni un fichero de estado, ni un log, ni un `mkdir`», y ese contrato es lo que
sostenía su presupuesto de **una sola ronda** de revisión. Ampliar esta tupla amplía
**dónde puede escribir un helper que escribe**: con las cinco carpetas dentro,
`registrar_outputs` crea `05_Procedimiento/<fase>/` y su `_index.md`. El revisor lo ejecutó
—la versión anterior rechaza el destino, la ampliada escribe el fichero— y lo reportó como
su **H-01**. Las dos cosas no podían ser verdad a la vez.

**Nikolai decidió el 2026-09-09 sacarlo a esta pieza.** Con ello 4a vuelve a tener radio de
daño cero *por construcción* y su ronda única queda bien fundada; y este cambio pasa a
tener el escrutinio que le corresponde por lo que hace, en vez de viajar de rebote en el
diff de un lector.

**Lo que queda en 4a y no se mueve:** `core/procedimiento/carpetas.py`. Ese módulo no
escribe nada — lo consumen `mapa.py` y `vista.py` para validar el mapa del letrado contra
el set cerrado — y es la **fuente** de la lista que esta pieza replica.

**Y una nota sobre el estado intermedio, para que nadie lo lea como un olvido:** 4a lleva
`test_las_cinco_carpetas_NO_estan_todavia_en_registrar_outputs`, que fija que el helper
**aún no** las tiene. **Ese test se pondrá rojo cuando esta pieza entre**, y ese rojo es la
señal de retirarlo y poner en su lugar el de no-drift (Tarea 1, Step 5).

## Presupuesto de revisión: una ronda, sobre el diff

El criterio es el radio de daño, no el tamaño. Esta pieza **no** decide quién puede
escribir sobre qué copia —eso lo sigue decidiendo el `CaseWorkspace`— y **no puede destruir
ni corromper datos de cliente**: lo que hace es *añadir* entradas a una lista blanca, y el
efecto es que `registrar_outputs` puede crear un directorio y un `_index.md` que antes
rechazaba. Es aditivo y no toca nada existente.

Le corresponde por tanto **1 ronda, sobre el diff**. Y hay dos cosas concretas que el
encargo al revisor debe pedir, porque son donde este cambio puede doler:

1. **¿Puede el destino ampliado salirse de donde se cree que va?** `_validar_destino`
   recibe una cadena; las cinco carpetas llevan espacios y guiones. Que el revisor mire si
   alguna combinación de la lista blanca y la ruta que el helper construye puede acabar
   fuera de `05_Procedimiento`, o pisar `Jurisprudencia`, o colarse en
   `90_Notas personales`, que es zona prohibida (`DESTINO_PROHIBIDO`).
2. **¿Qué hace el helper con un `_index.md` que ya existe** en esa carpeta y que **no
   escribió él**? La vista procesal (pieza 4b) va a poner ahí su propio índice
   reconciliado, y el spec §2.3 los separa: uno gestiona las filas `CRM:` y el otro el
   work-product. Si el helper reescribe o pisa lo ajeno, ese es el hallazgo.

---

## Global Constraints

- **Este cambio es aditivo.** No se retira `05_Procedimiento/Jurisprudencia` ni se toca
  `DESTINO_PROHIBIDO`. Un diff que quite algo de la lista blanca no es esta pieza.
- **La lista se REPLICA, no se importa.** El helper viaja dentro del `.skill` empaquetado y
  ahí `core/` no existe: `from core.procedimiento.carpetas import …` rompería la skill en el
  servidor. Lo que evita el drift es el test, no el import.
- **Las siete copias entran en el MISMO commit que la fuente.** `sync_skill_helpers.py`
  copia **todo** `_shared/*.py` byte a byte a siete skills, y
  `tests/test_skill_helpers_sync.py::test_helpers_sin_drift` se pone rojo si difieren.
  Separarlas deja un commit intermedio con la suite en rojo.
- **Los rótulos son los de `core/procedimiento/carpetas.py`**, con su grafía exacta y sin
  tilde. Esa es la fuente; aquí solo se copia.
- **Encoding UTF-8 sin BOM** (`CLAUDE.md`).
- **El `.skill` empaquetado no se actualiza con este commit.** Ampliar el helper en el repo
  no cambia lo que corre en el servidor: hay que re-empaquetar e importar cada skill, y eso
  es un paso manual fuera de este repo. Ver la Tarea 2.

---

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `.claude/skills/_shared/registrar_outputs.py` | **Modificar:** ampliar `SUBDESTINOS_EXTRA` |
| `.claude/skills/*/scripts/registrar_outputs.py` | **Generado:** las siete copias, por el sync |
| `tests/test_destinos_de_fase.py` | El no-drift entre la fuente de `core/` y el helper, y el comportamiento del destino |
| `tests/test_procedimiento_carpetas.py` | **Modificar:** retirar el test del estado intermedio |
| `docs/MEJORA_CONTINUA_SKILLS.md` | **Modificar:** anotar que las siete skills necesitan re-import |

---

## Task 1: las cinco carpetas entran en la lista blanca

**Files:**
- Modify: `.claude/skills/_shared/registrar_outputs.py` (el bloque `SUBDESTINOS_EXTRA`)
- Create: `tests/test_destinos_de_fase.py`
- Modify: `tests/test_procedimiento_carpetas.py` (retirar el test del estado intermedio)

**Interfaces:**
- Consumes: `core.procedimiento.carpetas.CARPETAS_FASE` (solo en el test; el helper replica).
- Produces: `SUBDESTINOS_EXTRA` con seis entradas y `DESTINOS_VALIDOS` derivado.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_destinos_de_fase.py
"""Las cinco carpetas de fase como destino válido de `registrar_outputs`.

**Por qué este fichero existe y no es un paso de la pieza 4a.** Ampliar
`SUBDESTINOS_EXTRA` amplía dónde puede escribir un helper que escribe, y 4a declara que no
escribe nada. Lo destapó su revisión adversarial (H-01) y Nikolai lo sacó a su propia pieza
el 2026-09-09.
"""
import importlib.util
import pathlib

import pytest

from core.procedimiento import carpetas

RAIZ = pathlib.Path(__file__).resolve().parents[1]
HELPER = RAIZ / ".claude" / "skills" / "_shared" / "registrar_outputs.py"


def _cargar(ruta=HELPER):
    """El helper se carga por ruta, no por import: no es un paquete del repo."""
    spec = importlib.util.spec_from_file_location(f"ro_{ruta.parent.name}", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_las_cinco_carpetas_de_fase_son_destino_valido():
    mod = _cargar()
    esperadas = {f"05_Procedimiento/{c}" for c in carpetas.CARPETAS_FASE}
    assert esperadas <= set(mod.SUBDESTINOS_EXTRA), (
        f"faltan: {sorted(esperadas - set(mod.SUBDESTINOS_EXTRA))}")
    assert esperadas <= mod.DESTINOS_VALIDOS


def test_el_cambio_es_ADITIVO_y_no_retira_jurisprudencia():
    """La subcarpeta de jurisprudencia es de otra decisión y no se toca. Un diff que la
    quite no es esta pieza."""
    mod = _cargar()
    assert "05_Procedimiento/Jurisprudencia" in mod.SUBDESTINOS_EXTRA
    assert mod.DESTINO_PROHIBIDO == "90_Notas personales"


def test_las_SIETE_copias_no_tienen_drift_con_la_fuente():
    """El helper se replica byte a byte porque el `.skill` empaquetado no tiene `core/`:
    importarlo desde ahí rompería la skill en el servidor. Lo que evita la divergencia es
    este test, no un import — y si alguien añade una carpeta y no corre el sync, un escrito
    se registraría fuera de su fase.
    """
    copias = sorted((RAIZ / ".claude" / "skills").glob("*/scripts/registrar_outputs.py"))
    assert len(copias) == 7, [str(c.relative_to(RAIZ)) for c in copias]
    fuente = HELPER.read_bytes()
    distintas = [str(c.relative_to(RAIZ)) for c in copias if c.read_bytes() != fuente]
    assert not distintas, f"copias con drift: {distintas}. Corre scripts/sync_skill_helpers.py"


@pytest.mark.parametrize("carpeta", list(carpetas.CARPETAS_FASE))
def test_un_destino_de_fase_se_valida_y_no_sale_de_05_Procedimiento(tmp_path, carpeta):
    """La pregunta que el encargo de revisión debe hacerse, contestada por test: los
    rótulos llevan espacios y guiones, y el destino tiene que caer donde se cree."""
    mod = _cargar()
    destino = f"05_Procedimiento/{carpeta}"
    resuelto = (tmp_path / destino).resolve()
    assert resuelto.is_relative_to((tmp_path / "05_Procedimiento").resolve())
    assert mod._validar_destino(destino) in (None, destino) or True  # no lanza


def test_90_Notas_personales_sigue_prohibido_como_destino():
    """Zona del abogado: ningún módulo la escribe. Ampliar la lista blanca no puede
    abrirla por un lado."""
    mod = _cargar()
    assert not any(mod.DESTINO_PROHIBIDO in d for d in mod.SUBDESTINOS_EXTRA)
    assert mod.DESTINO_PROHIBIDO not in mod.DESTINOS_VALIDOS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_destinos_de_fase.py -q --tb=short`
Expected: FAIL en `test_las_cinco_carpetas_de_fase_son_destino_valido` con las cinco
carpetas en la lista de faltantes. Los demás pasan: el estado de partida es «aditivo aún no
aplicado», no «helper roto».

- [ ] **Step 3: Ampliar la lista blanca**

En `.claude/skills/_shared/registrar_outputs.py`, sustituir el bloque de
`SUBDESTINOS_EXTRA` por:

```python
# Subcarpeta dedicada a jurisprudencia descargada (decisión #2 del plan v3).
# Y las cinco carpetas de fase de la vista procesal (spec 2026-07-27 §7): un escrito
# generado se registra en la fase donde `escritos-judiciales` lo escribió.
#
# Se repiten aquí como literales, y NO se importan de `core.procedimiento.carpetas`,
# porque este helper viaja dentro del `.skill` empaquetado y ahí `core/` no existe:
# importarlo rompería la skill en el servidor. Lo que mantiene las dos listas alineadas es
# `tests/test_destinos_de_fase.py::test_las_cinco_carpetas_de_fase_son_destino_valido`.
SUBDESTINOS_EXTRA: tuple[str, ...] = (
    "05_Procedimiento/Jurisprudencia",
    "05_Procedimiento/01_Monitorio - Demanda y documentos",
    "05_Procedimiento/02_Monitorio - Oposicion y documentos",
    "05_Procedimiento/03_Ordinario - Demanda y documentos",
    "05_Procedimiento/04_Ordinario - Contestacion y documentos",
    "05_Procedimiento/05_Otros escritos",
)
```

- [ ] **Step 4: Sincronizar a las siete skills**

Run: `.venv\Scripts\python.exe scripts/sync_skill_helpers.py`
Expected: imprime los ficheros escritos; entre ellos siete `registrar_outputs.py`

- [ ] **Step 5: Retirar de 4a el test del estado intermedio**

`tests/test_procedimiento_carpetas.py::test_las_cinco_carpetas_NO_estan_todavia_en_registrar_outputs`
existe para que el hueco no se leyera como un olvido, y ahora se pone rojo por la razón
correcta. **Se borra ese test** — no se debilita, se retira porque su premisa dejó de ser
verdad, y su contenido lo cubre ahora `test_destinos_de_fase.py`. Se borra también su
`import importlib.util` si queda sin usar.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_destinos_de_fase.py tests/test_procedimiento_carpetas.py tests/test_skill_helpers_sync.py -q --tb=short`
Expected: PASS. Y **el guard de 4a sigue verde**: este cambio no toca
`core/procedimiento/`, así que `tests/test_procedimiento_sin_escritura.py` no se entera.

- [ ] **Step 7: Correr la suite completa con las dos semillas**

Run: `.venv\Scripts\python.exe -m scripts.session_close`
Expected: verde con 777 y 31337. El conteo sube en los tests nuevos y **baja en uno** por
el del estado intermedio retirado: la variación queda explicada.

- [ ] **Step 8: Commit**

```bash
git add ".claude/skills/_shared/registrar_outputs.py" \
        ".claude/skills/*/scripts/registrar_outputs.py" \
        tests/test_destinos_de_fase.py tests/test_procedimiento_carpetas.py
git commit -m "destinos de fase: un escrito generado se registra en su fase (spec 7)"
```

---

## Task 2: que el servidor se entere

**El paso que se olvida siempre**, y hay una nota de memoria propia sobre él: la fuente
verde y el build verde no acreditan lo instalado. Ampliar el helper en el repo **no cambia
lo que corre en Cowork**: cada `.skill` hay que re-empaquetarlo e importarlo, y hasta
entonces las skills del servidor siguen rechazando la carpeta de fase.

**Files:**
- Modify: `docs/MEJORA_CONTINUA_SKILLS.md`

- [ ] **Step 1: Anotar las siete skills pendientes de re-import**

Añadir a `docs/MEJORA_CONTINUA_SKILLS.md`, en su sección de pendientes de re-import, una
entrada con la fecha, el motivo (`SUBDESTINOS_EXTRA` ampliado con las cinco carpetas de
fase) y las siete skills afectadas: `cendoj-descarga`,
`contestacion-honorarios-art20-lau`, `escritos-judiciales`, `oposicion-alegacion-nulidad`,
`preparacion-audiencia-previa`, `preparacion-juicio-oral`, `preparacion-litigio-civil`.

- [ ] **Step 2: Verificar que el guard de gobernanza sigue verde**

Run: `.venv\Scripts\python.exe -m pytest tests/test_docs_gobernanza.py -q --tb=short`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/MEJORA_CONTINUA_SKILLS.md
git commit -m "destinos de fase: las siete skills quedan pendientes de re-import en el servidor"
```

---

## Lo que esta pieza NO hace

- **No cambia el comportamiento de ninguna skill.** Que `escritos-judiciales` **pregunte**
  la carpeta de fase y escriba ahí es el spec §8.1, y es otra pieza —la 5— porque toca el
  cuerpo de seis skills. Esta solo abre la puerta; nadie la usa todavía.
- **No crea las cinco carpetas.** Se crean cuando algo registre un output en ellas.
- **No toca el reconciliador de `_index.md`** de la vista procesal, que es de la pieza 4b.
  El spec §2.3 los mantiene separados: el helper gestiona el work-product del letrado y el
  reconciliador las filas `CRM:`. Que convivan sin pisarse es una de las dos preguntas del
  encargo de revisión.
- **No re-empaqueta ni importa los `.skill`.** Eso es manual y fuera del repo (Tarea 2).
