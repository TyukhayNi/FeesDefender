# Bundle por hilo de correo en la sala de lectura (Slice 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la correspondencia de un caso ocupe una entrada por hilo en la sala de lectura en vez de una por mensaje, cambiando la clave de agrupación a la descripción del nombre (ignorando la fecha), añadiendo una función determinista que decide la forma del bundle, y colapsando los bundles en `INDICE.md`.

**Architecture:** Todo vive dentro del paquete `.skill` de `organizar-sala-lectura`, en scripts **stdlib puro y self-contained** (corren en el sandbox de Cowork sin `core/`). Dos funciones deterministas en `scripts/preclasificar.py` (`agrupar_por_hilo` con clave nueva, `layout_bundle_hilo` nueva) + un cambio en `scripts/indices_desde_manifiesto.py` (`construir_indice` colapsa bundles; `construir_cronologia` NO se toca) + prosa en `SKILL.md`. No se toca `core/` en absoluto.

**Tech Stack:** Python 3 stdlib (`re`, `collections.Counter`, `pathlib`), pytest. Windows + PowerShell.

**Spec:** `docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md` (Slice 1, re-tajada y con la premisa de agrupación corregida el 2026-07-26).

## Global Constraints

- **Stdlib puro en los scripts de la skill.** Prohibido importar `core/`, `yaml` o cualquier
  dependencia externa en `preclasificar.py` e `indices_desde_manifiesto.py`: corren en el sandbox de
  Cowork, que no tiene el repo. Patrón declarado en el docstring de ambos ficheros.
- **`core/` NO se toca.** Ni `core/email_atomize`, ni `core/email_export`, ni `core/anon` (congelado
  por `CLAUDE.md`). Este plan solo lee su comportamiento, nunca lo modifica.
- **`CRONOLOGIA.md` no cambia de comportamiento.** Sigue emitiendo una línea por fila del manifiesto.
  Solo `INDICE.md` colapsa.
- **Encoding UTF-8 sin BOM** en todo fichero escrito.
- **Ningún fichero desaparece en silencio.** Doctrina del ítem 12 del backlog: si una fila no encaja
  en el modelo, se emite igual (o se aborta ruidosamente), nunca se omite.
- **Comandos desde la raíz del worktree:** `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\emails-atomizados-sala-lectura-c290ef`.
- **NO editar `.agents/skills/`** — es un espejo untracked ajeno a este trabajo. La fuente única es
  `.claude/skills/`.
- **Versión objetivo de la skill: 1.13** (frontmatter de `SKILL.md` + entrada en `CHANGELOG.md`).

## File Structure

| Fichero | Responsabilidad | Acción |
|---|---|---|
| `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py` | Pre-clasificación mecánica determinista. Gana la clave de hilo por descripción y la función de layout del bundle. | Modificar |
| `.claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py` | Derivar `INDICE.md` y `CRONOLOGIA.md` del manifiesto. Solo el índice colapsa bundles. | Modificar |
| `.claude/skills/organizar-sala-lectura/SKILL.md` | Procedimiento que sigue el LLM. Pasos 1-bis.b y 4 + sección de documentos compuestos + versión 1.13. | Modificar |
| `.claude/skills/organizar-sala-lectura/CHANGELOG.md` | Historial de la skill. | Modificar |
| `tests/test_preclasificar_sala_lectura.py` | Tests de las dos funciones deterministas. | Modificar |
| `tests/test_indices_desde_manifiesto.py` | Tests del colapso del índice. | Modificar |

---

### Task 1: Clave de hilo por descripción en `agrupar_por_hilo`

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:133-155`
- Test: `tests/test_preclasificar_sala_lectura.py:57-95`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `agrupar_por_hilo(rutas_eml: list[str]) -> dict[str, list[str]]` — las **claves pasan a ser
  la descripción sin prefijo de fecha** (antes eran el stem completo con fecha). Añade además dos
  nombres a nivel de módulo que **la Task 2 consume**: `fecha_de_nombre(nombre: str) -> str` (público)
  y la constante `_SIN_FECHA = "0000-00-00"`. `_descripcion_hilo(nombre: str) -> str` es interno de
  esta tarea; ninguna otra lo usa.

**Contexto que el implementador necesita.** `core.email_export.eml_filename` nombra cada `.eml`
`AAAA-MM-DD_descripcion.eml` con la fecha **de ese mensaje**, y `_slug_descripcion` ya elimina los
prefijos `Re:`/`RV:`/`Fwd:`, así que todos los mensajes de un hilo comparten la misma `descripcion` y
difieren solo en la fecha. Agrupar por descripción = agrupar el hilo. La protección vigente (un `_N`
final solo es sufijo de hilo si la base sin él existe de verdad en el conjunto) **debe conservarse**,
aplicada ahora sobre descripciones: si no, `oferta_vivienda_1_990_000` se fusionaría con un
`oferta_vivienda_1_990` inexistente (bug real del ítem 11 del backlog).

- [ ] **Step 1: Escribir los tests que fallan**

Sustituye los cuatro tests existentes de `agrupar_por_hilo` (líneas 57-95 de
`tests/test_preclasificar_sala_lectura.py`) por estos seis:

```python
def test_agrupar_por_hilo_junta_el_mismo_asunto_en_fechas_distintas():
    # Comportamiento NUEVO (v1.13): la clave es la descripción, no el stem con fecha.
    nombres = [
        "2025-03-20_oferta_calle_x.eml",
        "2025-03-21_oferta_calle_x.eml",
        "2025-04-02_oferta_calle_x.eml",
        "2025-04-22_ubicacion_propietario.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert set(grupos) == {"oferta_calle_x", "ubicacion_propietario"}
    assert len(grupos["oferta_calle_x"]) == 3


def test_agrupar_por_hilo_junta_variantes_del_mismo_dia_y_asunto():
    nombres = [
        "2025-03-20_consulta_procedimiento.eml",
        "2025-03-20_consulta_procedimiento_2.eml",
        "2025-03-20_consulta_procedimiento_3.eml",
        "2025-04-22_ubicacion_propietario.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert len(grupos) == 2
    assert len(grupos["consulta_procedimiento"]) == 3


def test_agrupar_por_hilo_no_fusiona_por_cifra_en_el_asunto():
    # Regresión del ítem 11: "_000" NO es sufijo de hilo (no existe "oferta_vivienda_1_990").
    nombres = [
        "2025-05-10_oferta_vivienda_1_990_000.eml",
        "2025-06-01_otra_cosa.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert set(grupos) == {"oferta_vivienda_1_990_000", "otra_cosa"}


def test_agrupar_por_hilo_sin_base_no_fusiona():
    # _2 y _3 SIN la base -> no se puede afirmar que sean el mismo hilo.
    nombres = ["2025-03-20_consulta_2.eml", "2025-03-20_consulta_3.eml"]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert set(grupos) == {"consulta_2", "consulta_3"}


def test_agrupar_por_hilo_nombre_sin_prefijo_de_fecha():
    # Fichero legacy/manual sin fecha delante: la descripción es el nombre pelado.
    grupos = preclasificar.agrupar_por_hilo(["oferta_suelta.eml"])
    assert set(grupos) == {"oferta_suelta"}


def test_fecha_de_nombre():
    assert preclasificar.fecha_de_nombre("2025-03-20_consulta.eml") == "2025-03-20"
    assert preclasificar.fecha_de_nombre("0000-00-00_sin_fecha.eml") == "0000-00-00"
    assert preclasificar.fecha_de_nombre("oferta_suelta.eml") == "0000-00-00"
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
python -m pytest tests/test_preclasificar_sala_lectura.py -k "agrupar_por_hilo or fecha_de_nombre" -v
```

Esperado: FALLAN. Los de agrupación con `AssertionError` (las claves reales aún llevan el prefijo de
fecha, p. ej. `2025-03-20_oferta_calle_x`), y `test_fecha_de_nombre` con
`AttributeError: module 'preclasificar' has no attribute 'fecha_de_nombre'`.

- [ ] **Step 3: Implementar el cambio mínimo**

En `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py`, junto a `_SUFIJO_HILO_RE`
(línea 87), añade el regex de prefijo de fecha:

```python
_PREFIJO_FECHA_RE = _re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")
_SIN_FECHA = "0000-00-00"
```

Y reemplaza `agrupar_por_hilo` (líneas 133-155) por:

```python
def fecha_de_nombre(nombre: str) -> str:
    """Prefijo `AAAA-MM-DD` del nombre canónico de `email_export`, o `0000-00-00`
    si el nombre no lo lleva. NO valida que la fecha exista en el calendario:
    `0000-00-00` es un valor legítimo que emite `_fecha_iso` cuando la cabecera
    `Date` falta o no parsea."""
    base = nombre[:-4] if nombre.lower().endswith(".eml") else nombre
    m = _PREFIJO_FECHA_RE.match(base)
    return m.group(1) if m else _SIN_FECHA


def _descripcion_hilo(nombre: str) -> str:
    """Descripción del nombre, SIN el prefijo de fecha y sin la extensión.
    `2025-03-20_oferta_calle_x.eml` -> `oferta_calle_x`."""
    base = nombre[:-4] if nombre.lower().endswith(".eml") else nombre
    m = _PREFIJO_FECHA_RE.match(base)
    return m.group(2) if m else base


def agrupar_por_hilo(rutas_eml: list[str]) -> dict[str, list[str]]:
    """Agrupa nombres de `.eml` por HILO. La clave es la **descripción** del
    nombre, IGNORANDO el prefijo de fecha: `core.email_export._slug_descripcion`
    ya elimina los prefijos `Re:`/`RV:`/`Fwd:` del asunto, así que todos los
    mensajes de un hilo comparten descripción y solo difieren en la fecha
    (`eml_filename` usa la fecha del propio mensaje). Agrupar por descripción es,
    por tanto, agrupar el hilo sin leer una sola cabecera RFC — gratis en los tres
    modos de acceso de la skill.

    Se conserva la protección del ítem 11 del backlog, ahora sobre descripciones:
    un `_N` final solo se recorta si la descripción sin ese sufijo existe DE VERDAD
    en el conjunto, así que una cifra del propio asunto
    (`oferta_vivienda_1_990_000`) no fabrica un hilo inexistente.

    Devuelve `{descripcion_hilo: [nombres_del_grupo]}`. Se clasifica un
    representante y su categoría se propaga al resto sin releerlos.

    LIMITACIONES (deliberadas, ver spec 2026-07-23 §5): un hilo cuyo ASUNTO cambió
    a mitad de conversación no se agrupa, y dos conversaciones distintas con el
    mismo asunto SÍ comparten grupo (sin guarda por salto temporal — decisión de
    Nikolai 2026-07-26). El threading riguroso por `References`/`In-Reply-To` es
    `MEJORAS #86`, no un prerrequisito."""
    descripciones = {_descripcion_hilo(n) for n in rutas_eml}
    grupos: dict[str, list[str]] = {}
    for nombre in rutas_eml:
        desc = _descripcion_hilo(nombre)
        m = _SUFIJO_HILO_RE.match(desc)
        clave = m.group(1) if (m and m.group(1) in descripciones) else desc
        grupos.setdefault(clave, []).append(nombre)
    return grupos
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

```bash
python -m pytest tests/test_preclasificar_sala_lectura.py -v
```

Esperado: PASS, todos (los 6 nuevos + los preexistentes de `clasificar_por_patron`, `dedup_por_sha`,
etc., que este cambio no toca).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/scripts/preclasificar.py tests/test_preclasificar_sala_lectura.py && git commit -m "feat(sala-lectura): agrupar_por_hilo usa la descripcion como clave, ignorando la fecha"
```

---

### Task 2: `layout_bundle_hilo` — forma de copia determinista del bundle

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py` (añadir función al final, junto a `subcategoria_crm`)
- Test: `tests/test_preclasificar_sala_lectura.py` (añadir al final)

**Interfaces:**
- Consumes de la Task 1: `fecha_de_nombre(nombre) -> str`, `_SIN_FECHA`.
- Produces:
  ```python
  layout_bundle_hilo(
      grupo: list[str],
      descripcion: str,
      *,
      con_adjuntos: frozenset[str] = frozenset(),
      carpeta_existente: str | None = None,
  ) -> list[dict]
  ```
  Una fila-dict por `.eml` del grupo, en orden de copia, con las claves:
  `nombre_origen` (str), `fecha` (str `AAAA-MM-DD`), `rol` (`"principal"` | `"anexo"`),
  `nombre_canonico` (str, ruta relativa dentro de la sala), `parent_id` (str, `""` para el principal),
  `orden` (int, `0` para el principal y `1..N` para los anexos).

**Contexto que el implementador necesita.** Las convenciones vigentes de documento compuesto en
`SKILL.md` son de obligado cumplimiento: la carpeta es `AAAA-MM-DD_descripcion/`, el principal
`AAAA-MM-DD_descripcion.ext`, los anexos `AAAA-MM-DD_descripcion_anexo_N_x.ext`, el `AAAA-MM-DD` de
**cada anexo es su propia fecha** (no la del bundle), y el `parent_id` de un anexo es **el nombre
pelado de la carpeta** (sin `/` ni extensión). `descripcion` llega ya aprobada por el LLM (≤50
caracteres, minúsculas, guiones bajos, **sin PII**): esta función no la deriva ni la valida.

`carpeta_existente` es lo que hace cumplir mecánicamente la regla §2.3 del spec ("el nombre del bundle
se fija en la primera corrida y no se renombra nunca"): si se pasa, se usa **verbatim** y no se
recalcula, de modo que un mensaje que llegue con fecha anterior al principal no provoque un renombrado
que pisaría documentos ya copiados.

- [ ] **Step 1: Escribir los tests que fallan**

Añade al final de `tests/test_preclasificar_sala_lectura.py`:

```python
def test_layout_bundle_de_tres_mensajes():
    grupo = [
        "2025-04-02_oferta_calle_x.eml",
        "2025-03-20_oferta_calle_x.eml",
        "2025-03-21_oferta_calle_x.eml",
    ]
    filas = preclasificar.layout_bundle_hilo(grupo, "oferta_calle_x")
    assert [f["rol"] for f in filas] == ["principal", "anexo", "anexo"]
    principal = filas[0]
    assert principal["nombre_origen"] == "2025-03-20_oferta_calle_x.eml"
    assert principal["nombre_canonico"] == "2025-03-20_oferta_calle_x/2025-03-20_oferta_calle_x.eml"
    assert principal["parent_id"] == ""
    assert principal["orden"] == 0
    # Cada anexo lleva SU PROPIA fecha y el parent_id pelado de la carpeta.
    assert filas[1]["fecha"] == "2025-03-21"
    assert filas[1]["parent_id"] == "2025-03-20_oferta_calle_x"
    assert filas[1]["nombre_canonico"] == (
        "2025-03-20_oferta_calle_x/2025-03-21_oferta_calle_x_anexo_1_mensaje.eml")
    assert filas[2]["fecha"] == "2025-04-02"
    assert filas[2]["orden"] == 2


def test_layout_mensaje_unico_sin_adjuntos_queda_plano():
    filas = preclasificar.layout_bundle_hilo(["2025-03-20_consulta.eml"], "consulta")
    assert len(filas) == 1
    assert filas[0]["rol"] == "principal"
    assert filas[0]["nombre_canonico"] == "2025-03-20_consulta.eml"
    assert filas[0]["parent_id"] == ""


def test_layout_mensaje_unico_con_adjuntos_abre_bundle():
    filas = preclasificar.layout_bundle_hilo(
        ["2025-03-20_consulta.eml"], "consulta",
        con_adjuntos=frozenset({"2025-03-20_consulta.eml"}))
    assert filas[0]["nombre_canonico"] == "2025-03-20_consulta/2025-03-20_consulta.eml"


def test_layout_fecha_incierta_no_es_principal():
    grupo = ["0000-00-00_oferta_calle_x.eml", "2025-03-20_oferta_calle_x.eml"]
    filas = preclasificar.layout_bundle_hilo(grupo, "oferta_calle_x")
    assert filas[0]["nombre_origen"] == "2025-03-20_oferta_calle_x.eml"
    assert filas[1]["fecha"] == "0000-00-00"


def test_layout_carpeta_existente_no_se_renombra_con_mensaje_anterior():
    # §2.3: el nombre del bundle se fija en la 1ª corrida. Llega un mensaje MÁS
    # ANTIGUO que el principal -> entra como anexo, la carpeta NO cambia.
    grupo = [
        "2025-03-20_oferta_calle_x.eml",
        "2025-03-21_oferta_calle_x.eml",
        "2025-01-05_oferta_calle_x.eml",
    ]
    filas = preclasificar.layout_bundle_hilo(
        grupo, "oferta_calle_x", carpeta_existente="2025-03-20_oferta_calle_x")
    assert all(f["nombre_canonico"].startswith("2025-03-20_oferta_calle_x/") for f in filas)
    nuevo = [f for f in filas if f["nombre_origen"] == "2025-01-05_oferta_calle_x.eml"][0]
    assert nuevo["rol"] == "anexo"
    assert nuevo["fecha"] == "2025-01-05"
    assert nuevo["parent_id"] == "2025-03-20_oferta_calle_x"


def test_layout_es_determinista():
    grupo = ["2025-03-21_x.eml", "2025-03-20_x.eml"]
    assert preclasificar.layout_bundle_hilo(grupo, "x") == preclasificar.layout_bundle_hilo(
        list(reversed(grupo)), "x")
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
python -m pytest tests/test_preclasificar_sala_lectura.py -k layout -v
```

Esperado: FALLAN todos con
`AttributeError: module 'preclasificar' has no attribute 'layout_bundle_hilo'`.

- [ ] **Step 3: Implementar el cambio mínimo**

Añade al final de `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py`:

```python
def layout_bundle_hilo(
    grupo: list[str],
    descripcion: str,
    *,
    con_adjuntos: frozenset[str] = frozenset(),
    carpeta_existente: str | None = None,
) -> list[dict]:
    """Decide la FORMA DE COPIA de un grupo de hilo devuelto por
    :func:`agrupar_por_hilo`. Determinista y sin E/S: solo nombres y fechas.

    Reglas (spec 2026-07-23 §2.1/§2.3):
    - Bundle (subcarpeta fechada) si el grupo tiene ≥2 mensajes O alguno lleva
      adjuntos MIME; si es un mensaje solo y sin adjuntos, queda PLANO (evita
      cientos de carpetas de un fichero).
    - El principal es el mensaje de fecha CIERTA más antigua; los `0000-00-00`
      nunca son principal (misma convención que el índice: lo incierto va al
      final). Empate -> orden alfabético del nombre, para ser determinista.
    - Cada anexo lleva SU PROPIA fecha, no la del bundle.
    - `parent_id` de un anexo = nombre PELADO de la carpeta.
    - `carpeta_existente`, si se pasa, se usa VERBATIM: el nombre del bundle se
      fija en la primera corrida y no se renombra nunca (si llegara un mensaje
      anterior al principal, entra como anexo; renombrar pisaría lo ya copiado).

    `descripcion` llega ya aprobada (≤50 car., minúsculas, guiones bajos, sin
    PII): esta función no la deriva ni la sanea.
    """
    def _clave(nombre: str):
        f = fecha_de_nombre(nombre)
        return (1 if f == _SIN_FECHA else 0, f, nombre)

    ordenados = sorted(grupo, key=_clave)
    if not ordenados:
        return []

    es_bundle = len(ordenados) >= 2 or any(n in con_adjuntos for n in ordenados)
    # Con `carpeta_existente`, el principal NO es simplemente el más antiguo: es el
    # mensaje que dio nombre a la carpeta en la primera corrida (el de la fecha del
    # prefijo). Si no, un mensaje que llegue con fecha ANTERIOR le robaría el rol al
    # principal ya copiado y el bundle quedaría incoherente con su nombre.
    if carpeta_existente:
        fecha_carpeta = fecha_de_nombre(carpeta_existente)
        candidatos = [n for n in ordenados if fecha_de_nombre(n) == fecha_carpeta]
        principal = candidatos[0] if candidatos else ordenados[0]
    else:
        principal = ordenados[0]
    if not es_bundle:
        return [{
            "nombre_origen": principal,
            "fecha": fecha_de_nombre(principal),
            "rol": "principal",
            "nombre_canonico": f"{fecha_de_nombre(principal)}_{descripcion}.eml",
            "parent_id": "",
            "orden": 0,
        }]

    carpeta = carpeta_existente or f"{fecha_de_nombre(principal)}_{descripcion}"
    filas = [{
        "nombre_origen": principal,
        "fecha": fecha_de_nombre(principal),
        "rol": "principal",
        "nombre_canonico": f"{carpeta}/{carpeta}.eml",
        "parent_id": "",
        "orden": 0,
    }]
    for i, nombre in enumerate([n for n in ordenados if n != principal], 1):
        fecha = fecha_de_nombre(nombre)
        filas.append({
            "nombre_origen": nombre,
            "fecha": fecha,
            "rol": "anexo",
            "nombre_canonico": f"{carpeta}/{fecha}_{descripcion}_anexo_{i}_mensaje.eml",
            "parent_id": carpeta,
            "orden": i,
        })
    return filas
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

```bash
python -m pytest tests/test_preclasificar_sala_lectura.py -v
```

Esperado: PASS, todos.

> **Nota para el implementador sobre el test del principal.** `f"{carpeta}/{carpeta}.eml"` produce
> `2025-03-20_oferta_calle_x/2025-03-20_oferta_calle_x.eml` cuando la carpeta se deriva del principal,
> que es lo que el test espera. Con `carpeta_existente` el principal hereda ese nombre aunque su fecha
> propia difiera — es deliberado: el principal ES el documento que da nombre al bundle.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/scripts/preclasificar.py tests/test_preclasificar_sala_lectura.py && git commit -m "feat(sala-lectura): layout_bundle_hilo decide la forma de copia del bundle de hilo"
```

---

### Task 3: `INDICE.md` colapsa bundles a una línea

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py:32-66`
- Test: `tests/test_indices_desde_manifiesto.py`

**Interfaces:**
- Consumes: nada de las Tasks 1-2 (opera sobre el `_MANIFIESTO.md` ya escrito).
- Produces: `construir_indice(filas: list[dict]) -> str` con bundles colapsados.
  `construir_cronologia(filas) -> str` **sin cambios de comportamiento**.

**Contexto que el implementador necesita.** Hoy `construir_indice` recorre TODAS las filas y emite
`_linea(f)` por cada una, sin mirar `parent_id` — así que los anexos de un bundle (los medios de un
chat de WhatsApp, los adjuntos de un correo) ocupan línea propia e inflan el índice. Este cambio hace
que el índice liste solo **documentos principales** con el recuento de sus anexos.

El `parent_id` de un anexo es el nombre **pelado** de la carpeta del bundle, mientras el
`nombre_canonico` del principal incluye la subcarpeta y la extensión
(`2025-03-20_x/2025-03-20_x.eml`). Para casar uno con otro hay que derivar el stem del principal
cortando en el primer `/`.

**Invariante que no se puede romper:** un anexo cuyo `parent_id` no case con ningún bundle presente
(huérfano) **debe seguir apareciendo** en el índice con su propia línea. Desaparecer en silencio es
exactamente el fallo que el ítem 12 del backlog vino a cerrar; `verificar_sala.py` ya detecta el
huérfano, pero el índice no debe ocultarlo entretanto.

- [ ] **Step 1: Escribir los tests que fallan**

Añade al final de `tests/test_indices_desde_manifiesto.py`:

```python
_MANIF_BUNDLE = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| a | 03_Email/m1.eml | 2025-03-20_oferta/2025-03-20_oferta.eml | eml | 2025-03-20 | buscador |  | 03. OFERTAS |  |
| b | 03_Email/m2.eml | 2025-03-20_oferta/2025-03-21_oferta_anexo_1_mensaje.eml | eml | 2025-03-21 | buscador | 2025-03-20_oferta | 03. OFERTAS |  |
| c | 03_Email/m3.eml | 2025-03-20_oferta/2025-04-02_oferta_anexo_2_mensaje.eml | eml | 2025-04-02 | buscador | 2025-03-20_oferta | 03. OFERTAS |  |
| d | 03_Email/adj.pdf | 2025-03-20_oferta/2025-03-21_oferta_anexo_3_hoja.pdf | pdf | 2025-03-21 | buscador | 2025-03-20_oferta | 03. OFERTAS |  |
| e | 01_Drive EV/encargo.pdf | 2024-01-01_encargo.pdf | pdf | 2024-01-01 | propietario |  | 01. ACTIVACIÓN |  |
"""


def _filas_bundle():
    import manifiesto_parser
    return manifiesto_parser.parse_manifiesto(_MANIF_BUNDLE)


def test_indice_colapsa_el_bundle_a_una_linea():
    salida = idx.construir_indice(_filas_bundle())
    lineas = [l for l in salida.splitlines() if l.startswith("- ")]
    assert len(lineas) == 2  # el bundle (1) + el encargo suelto (1)
    bundle = [l for l in lineas if "2025-03-20_oferta" in l][0]
    assert "(+3 anexos)" in bundle
    assert "anexo_1_mensaje" not in salida


def test_cronologia_no_colapsa_el_bundle():
    salida = idx.construir_cronologia(_filas_bundle())
    lineas = [l for l in salida.splitlines() if l.startswith("- ")]
    assert len(lineas) == 5  # todas las filas, es una línea de tiempo
    assert "anexo_1_mensaje" in salida


_MANIF_HUERFANO = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| b | 03_Email/m2.eml | 2025-03-20_oferta/2025-03-21_oferta_anexo_1_mensaje.eml | eml | 2025-03-21 | buscador | carpeta_que_no_existe | 03. OFERTAS |  |
| e | 01_Drive EV/encargo.pdf | 2024-01-01_encargo.pdf | pdf | 2024-01-01 | propietario |  | 01. ACTIVACIÓN |  |
"""


def test_indice_un_anexo_huerfano_no_desaparece():
    # `parent_id` que no case con ningún bundle presente -> línea propia, nunca
    # se omite en silencio (doctrina del ítem 12 del backlog).
    import manifiesto_parser
    filas = manifiesto_parser.parse_manifiesto(_MANIF_HUERFANO)
    salida = idx.construir_indice(filas)
    assert "anexo_1_mensaje" in salida
    lineas = [l for l in salida.splitlines() if l.startswith("- ")]
    assert len(lineas) == 2
    assert "anexos)" not in salida  # el huérfano no reclama anexos propios


def test_indice_sin_bundles_no_cambia_el_recuento():
    salida = idx.construir_indice(_filas())
    lineas = [l for l in salida.splitlines() if l.startswith("- ")]
    assert len(lineas) == 5
    assert "anexos)" not in salida
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
python -m pytest tests/test_indices_desde_manifiesto.py -v
```

Esperado: `test_indice_colapsa_el_bundle_a_una_linea` FALLA con `assert 5 == 2` (hoy emite una línea
por fila). `test_cronologia_no_colapsa_el_bundle` y `test_indice_sin_bundles_no_cambia_el_recuento`
PASAN ya (documentan lo que NO debe cambiar). `test_indice_un_anexo_huerfano_no_desaparece` PASA ya
(hoy todo se emite) y debe seguir pasando después.

- [ ] **Step 3: Implementar el cambio mínimo**

En `.claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py`, añade el import y
sustituye `_linea` y `construir_indice`:

```python
from collections import Counter
```

```python
def _linea(f: dict, n_anexos: int = 0) -> str:
    nombre = f.get("nombre_canonico") or ""
    orig = (f.get("ruta_original") or "").replace("\\", "/").rsplit("/", 1)[-1]
    fecha = f.get("fecha") or _SIN_FECHA
    sufijo = f" (+{n_anexos} anexos)" if n_anexos else ""
    return f"- {fecha} · [{nombre}]({nombre}) — original: {orig}{sufijo}"


def _stem_bundle(f: dict) -> str:
    """Nombre PELADO de la carpeta de un bundle, derivado del `nombre_canonico`
    del principal (`2025-03-20_x/2025-03-20_x.eml` -> `2025-03-20_x`). Cadena
    vacía si la fila no vive en subcarpeta (documento plano)."""
    n = (f.get("nombre_canonico") or "").replace("\\", "/")
    return n.split("/", 1)[0] if "/" in n else ""


def construir_indice(filas: list[dict]) -> str:
    """`INDICE.md`: por categoría, fecha DESC, con los bundles COLAPSADOS a una
    línea por documento principal (`(+N anexos)`). La información de los anexos
    no se pierde: sigue en el `_MANIFIESTO.md`, en `CRONOLOGIA.md` y en disco.
    Un anexo HUÉRFANO (cuyo `parent_id` no case con ningún bundle presente) emite
    su propia línea — nunca desaparece en silencio (doctrina del ítem 12)."""
    def clave_desc(f: dict):
        return (0 if _es_fecha_incierta(f.get("fecha", "")) else 1, _fecha_limpia(f.get("fecha", "")))

    def _parent(f: dict) -> str:
        return (f.get("parent_id") or "").strip()

    bundles = {_stem_bundle(f) for f in filas if not _parent(f) and _stem_bundle(f)}
    n_anexos = Counter(_parent(f) for f in filas if _parent(f))
    # Principales + anexos huérfanos (su bundle no existe entre las filas).
    visibles = [f for f in filas if not _parent(f) or _parent(f) not in bundles]

    por_cat: dict[str, list[dict]] = {}
    for f in visibles:
        por_cat.setdefault((f.get("categoria") or _SIN_CATEGORIA).strip(), []).append(f)

    def _l(f: dict) -> str:
        return _linea(f, n_anexos.get(_stem_bundle(f), 0) if not _parent(f) else 0)

    out = [_GEN, "", "# Índice documental", ""]
    for cat in sorted(por_cat):
        out += [f"## {cat}", ""]
        grupo = por_cat[cat]
        if cat == _RECLAMACIONES and any((f.get("subcategoria_crm") or "").strip() for f in grupo):
            por_sub: dict[str, list[dict]] = {}
            for f in grupo:
                por_sub.setdefault(_subcat(f), []).append(f)
            for sub in sorted(por_sub):
                out += [f"### {sub}", ""]
                out += [_l(f) for f in sorted(por_sub[sub], key=clave_desc, reverse=True)]
                out += [""]
        else:
            out += [_l(f) for f in sorted(grupo, key=clave_desc, reverse=True)]
            out += [""]
    return "\n".join(out).rstrip() + "\n"
```

`construir_cronologia` **no se toca**: sigue llamando a `_linea(f)` con un solo argumento, que ahora
tiene `n_anexos=0` por defecto, así que su salida es byte-idéntica a la de v1.12.

- [ ] **Step 4: Correr los tests para verificar que pasan**

```bash
python -m pytest tests/test_indices_desde_manifiesto.py -v
```

Esperado: PASS, todos.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py tests/test_indices_desde_manifiesto.py && git commit -m "feat(sala-lectura): INDICE.md colapsa bundles a una linea con (+N anexos)"
```

---

### Task 4: Procedimiento de la skill (`SKILL.md`) + v1.13

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md` (frontmatter `version`, Paso 1-bis.b, Paso 4, sección "Documentos compuestos (bundles)")
- Modify: `.claude/skills/organizar-sala-lectura/CHANGELOG.md`

**Interfaces:**
- Consumes: `agrupar_por_hilo` (clave = descripción) y `layout_bundle_hilo(...)` de las Tasks 1-2;
  el colapso de `INDICE.md` de la Task 3.
- Produces: nada que consuma código; es el procedimiento que sigue el LLM.

- [ ] **Step 1: Actualizar el Paso 1-bis.b**

En `SKILL.md`, el Paso 1-bis.b dice hoy que `agrupar_por_hilo` agrupa "el nombre sin sufijo `_N`".
Sustituye ese párrafo por:

```markdown
   b. `agrupar_por_hilo(rutas_eml)` sobre los `.eml` únicos → la clave es la
      **descripción del nombre ignorando el prefijo de fecha** (`email_export` ya
      quita `Re:`/`RV:`/`Fwd:` del asunto, así que todo el hilo comparte
      descripción y solo cambia la fecha). Clasifica solo un representante por
      hilo y propaga su categoría al resto sin releerlos. Un hilo cuyo ASUNTO
      cambió a mitad no se agrupa, y dos conversaciones con el mismo asunto SÍ
      comparten grupo: limitaciones aceptadas a propósito (spec 2026-07-23 §5).
```

- [ ] **Step 2: Añadir la forma de copia al Paso 4**

En el Paso 4, después del párrafo que empieza "Los documentos compuestos (bundles) copian primero su
principal…", añade:

```markdown
   - **Correo: un bundle por hilo.** Para cada grupo de `agrupar_por_hilo`, llama a
     `layout_bundle_hilo(grupo, descripcion, con_adjuntos=..., carpeta_existente=...)`
     (`scripts/preclasificar.py`) y usa sus filas tal cual: te da el principal (el
     mensaje de fecha cierta más antigua), los anexos con **su propia fecha**, el
     `parent_id` y el `orden`. Pasa `carpeta_existente` con el nombre que ya conste
     en el `_MANIFIESTO.md` si el bundle existe de una corrida anterior: **el nombre
     del bundle se fija en la primera corrida y NUNCA se renombra**, ni siquiera si
     llega un mensaje anterior al principal (renombrar pisaría lo ya copiado). Un
     grupo de un solo mensaje sin adjuntos queda PLANO, sin subcarpeta. El `.eml`
     original se copia igual que hasta ahora — el criterio "email → MD legible" NO
     está en vigor todavía (`MEJORAS #84`).
```

- [ ] **Step 3: Documentar el colapso del índice y la convivencia**

En la sección "Documentos compuestos (bundles)", añade al final:

```markdown
**El `INDICE.md` colapsa los bundles** (una línea por documento principal, con
`(+N anexos)`); `CRONOLOGIA.md` no colapsa: sigue listando cada fila, porque un
anexo con fecha propia es un evento datado. Los anexos siguen en el
`_MANIFIESTO.md`, en la cronología y en disco — no se pierde información.

**Convivencia con salas montadas antes de la v1.13.** No hay migración: los `.eml`
ya copiados constan por su `sha256` y se saltan; solo los documentos NUEVOS adoptan
la forma de bundle por hilo. La sala queda mixta (documentos planos antiguos +
bundles nuevos), sin duplicados y sin borrar nada. Es el comportamiento esperado.
Para re-montar una sala entera con la forma nueva, vacía a mano
`01_Procesado/Sala lectura/` y re-corre (el crudo de `00_Input` está intacto).
```

- [ ] **Step 4: Subir la versión y escribir el CHANGELOG**

En el frontmatter de `SKILL.md`, cambia `version: "1.12"` por `version: "1.13"`.

En `CHANGELOG.md`, inserta justo debajo de `# Changelog — organizar-sala-lectura`:

```markdown
## 1.13 — 2026-07-26
- **Un bundle por hilo de correo, no un documento por mensaje.** `agrupar_por_hilo`
  cambia de clave: ahora agrupa por la **descripción** del nombre ignorando el
  prefijo de fecha. Motivo: `email_export` fecha cada mensaje con SU fecha y solo
  numera `_2`/`_3` las colisiones del mismo día, así que la clave anterior no
  agrupaba hilos que cruzan días (277 correos colapsaban a ~240, no a ~40). Como
  `_slug_descripcion` ya elimina `Re:`/`RV:`/`Fwd:`, todo el hilo comparte
  descripción — agrupar por ella es agrupar el hilo sin leer cabeceras RFC. Se
  conserva la protección del ítem 11 (un `_N` solo se recorta si la base existe).
- **`layout_bundle_hilo` decide la forma de copia.** Principal = mensaje de fecha
  cierta más antigua (los `0000-00-00` nunca son principal); anexos con su propia
  fecha y `parent_id` pelado de la carpeta; grupo de uno sin adjuntos queda plano.
  `carpeta_existente` hace cumplir que el nombre del bundle se fije en la primera
  corrida y no se renombre nunca.
- **`INDICE.md` colapsa bundles** a una línea por principal con `(+N anexos)`;
  `CRONOLOGIA.md` sigue intacta (es una línea de tiempo). Un anexo huérfano emite
  su propia línea: nunca desaparece en silencio. Efecto colateral buscado: los
  bundles de WhatsApp y CRM también dejan de inflar el índice.
- **Limitaciones aceptadas** (spec `2026-07-23-emails-atomizados-sala-lectura-design.md`
  §5): un hilo con cambio de asunto no se agrupa, y dos conversaciones con el mismo
  asunto comparten bundle (sin guarda por salto temporal, decisión de Nikolai).
  Threading riguroso por `References`/`In-Reply-To` = `MEJORAS #86`.
```

- [ ] **Step 5: Verificar los guards de la skill y la suite completa**

```bash
python -m pytest -q --tb=short tests/test_check_skills.py tests/test_docs_gobernanza.py tests/test_preclasificar_sala_lectura.py tests/test_indices_desde_manifiesto.py
```

Esperado: PASS, todos. Ojo con qué valida realmente cada guard: `check_skills.py` comprueba
**frescura del CHANGELOG** (`changelog_stale`: si cambia `SKILL.md` y no `CHANGELOG.md`, la skill queda
marcada como stale) — **no** valida que el número de `version:` case con el encabezado del changelog.
Esa coherencia es responsabilidad tuya: el Step 4 sube ambos a la vez, no dejes uno sin el otro.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/SKILL.md .claude/skills/organizar-sala-lectura/CHANGELOG.md && git commit -m "docs(sala-lectura): procedimiento del bundle por hilo + v1.13"
```

---

### Task 5: Verificación final y empaquetado

**Files:**
- Sin cambios de código. Solo verificación y el artefacto `dist/` (gitignored).

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `.skill` empaquetado listo para re-importar en Cowork.

- [ ] **Step 1: Suite completa**

```bash
python -m pytest -q --tb=short
```

Esperado: 0 fallos. El recuento debe ser el de la última medición conocida **más los tests nuevos**
(6 de la Task 1 + 6 de la Task 2 + 4 de la Task 3 = 16, menos los 4 tests de `agrupar_por_hilo` que
la Task 1 sustituyó). Si algo falla, **NO** empaquetes: arréglalo o para y repórtalo.

- [ ] **Step 2: Empaquetar la skill**

```bash
python scripts/package_skill.py --out dist/skills .claude/skills/organizar-sala-lectura
```

Esperado: escribe `dist/skills/organizar-sala-lectura.skill`. Nota: el flag va **antes** de la ruta
(`--out dist/skills <dir>`), no es posicional.

- [ ] **Step 3: Commit final si quedó algo suelto**

```bash
git status --short
```

Esperado: limpio salvo `dist/` (gitignored) y los `?? .agents/ .codex/ AGENTS.md` preexistentes, que
**no** son de este trabajo y no se commitean.

- [ ] **Step 4: Abrir el PR**

```bash
git push -u origin HEAD && gh pr create --fill
```

`main` está protegida: nunca commit directo. El check `leak-scan` debe pasar para poder mergear.

- [ ] **Step 5: Registrar el pendiente operativo**

Tras el merge queda **una acción manual de Nikolai** que ningún test cubre: **re-importar el `.skill`
v1.13 en Cowork** (Ajustes → Skills), o Paola/Ana/Sergio seguirán con la v1.12 y no verán los bundles
por hilo. Anótalo en el bloque de cierre de la bitácora.

---

## Notas de alcance (para no ampliar por accidente)

Fuera de este plan, por decisión explícita del re-tajo del spec:

- **No** se consume `01_Procesado/Emails/` (`corpus.jsonl`, `MSG-id`, Capa B, adjuntos deduplicados) →
  `MEJORAS #84`.
- **No** se toca el motor de extracción/OCR de adjuntos → `MEJORAS #85`.
- **No** se implementa threading por cabeceras `References`/`In-Reply-To` → `MEJORAS #86`.
- **No** se toca `core/` ni se cambia el criterio de qué fichero se copia (sigue el `.eml`).
