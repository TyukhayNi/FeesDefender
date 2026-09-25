# `crm_ficha`: el YAML entero y el conjunto verificado — plan de implementación

> **Estado (2026-09-25): rev. 1, con la R2 adjudicada y SIN aplicar.** No se ejecuta tal cual:
> la §9 enumera los defectos confirmados de estas tareas y lo que cambia en cada una. La sesión
> que implemente escribe primero el spec rev. 3 y este plan rev. 2 según la §9, y solo entonces
> empieza la Task 1.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que `crm_ficha` no pierda nada de lo que el `_ficha_crm.yaml` declara y que su «VERIFICADA» certifique de verdad que el expediente tiene exactamente esas partes con esos datos (`MEJORAS #283` + `#288`).

**Architecture:** todo lo que decide vive en `core/crm_ficha.py` como funciones puras —lectura sin pérdida, validación de claves/tipos/identidad, auditoría de vínculos y de datos—; `scripts/crm_ficha.py` solo orquesta las llamadas al CRM y pinta el resultado, y `scripts/crm_colaboradores_firmas.py` pasa a leer con el mismo lector. Se reutilizan las lecturas que ya existen (`get_relaciones`, `get_cliente_contrario`, `get_colaborador`); no hay endpoint nuevo.

**Tech Stack:** Python 3.14, PyYAML (`SafeLoader`), pytest + typer `CliRunner`, `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md` rev. 2 (§ citados abajo). Leerlo entero antes de empezar.

## Global Constraints

- El `_ficha_crm.yaml` es la lista **completa** de partes del expediente (decisión de Nikolai, 2026-09-25): una parte vinculada que no declara es **fallo**.
- `crm_ficha` **nunca desvincula** ni **pisa** un dato existente. La política de completar solo lo vacío (`_COMPLETABLES_*` de `core/sudespacho_relations.py`) **no se toca**.
- Todo `ValueError` de validación sale **antes del primer writer** (`link_ev_mmc`), con **todos** los problemas juntos.
- Los tests no tocan la red: los dobles se declaran como hoy (`monkeypatch.setattr("scripts.crm_ficha.<nombre>", ...)`). Ningún test escribe fuera de `tmp_path`.
- **Ningún aserto existente se relaja.** Los tests del CLI que llegan a la verificación **declaran** la lectura nueva de fichas (Task 5): es preparación, no aserto, y se dice en el commit.
- Aceptación: `python -m scripts.session_close` (dos semillas). Radio de daño: **dos rondas**; la de diseño está hecha, **la R2 va sobre este diff** con `gpt-6-astra` · `medium` (Task 8).

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `core/crm_ficha.py` | lector sin pérdida (`leer_yaml_ficha`), tuplas de claves, validación agregada, `cargar_ficha_yaml`, `auditar_relaciones`, `auditar_datos`, `validar_id_crm` |
| `core/sudespacho_relations.py` | **solo** añade `id_crm: str = ""` a `NuevoClienteContrario` y `NuevoColaborador` (sin cambiar ningún comportamiento) |
| `scripts/crm_ficha.py` | orquesta: carga, plan, escrituras, vía `id_crm`, relecturas y veredicto |
| `scripts/crm_colaboradores_firmas.py` | `apply` lee con `leer_yaml_ficha` |
| `tests/test_crm_ficha_lector.py` (nuevo) | A.1-A.5 |
| `tests/test_crm_ficha_auditoria.py` (nuevo) | B.1-B.2 puros |
| `tests/test_crm_ficha_cli.py` | CLI: sobrantes, `[DATO]`, `id_crm`, parcial; y el ayudante `_declara_fichas` |
| `tests/test_crm_colaboradores_firmas*.py` | `apply` falla sin reescribir |
| `tests/_mutantes_crm_ficha.py` (nuevo) | arnés de mutantes |

---

### Task 1: Lector sin pérdida (spec §3 A.1)

**Files:** Modify `core/crm_ficha.py`; Create `tests/test_crm_ficha_lector.py`.

**Interfaces:** Produces `leer_yaml_ficha(path: Path) -> dict` (lanza `ValueError` con línea ante clave repetida, alias o merge; `FileNotFoundError` si no existe; documento vacío → `{}`).

- [ ] **Step 1: tests que fallan**

```python
# tests/test_crm_ficha_lector.py
import pytest

from core import crm_ficha as cf


def _yaml(tmp_path, texto):
    p = tmp_path / "_ficha_crm.yaml"
    p.write_text(texto, encoding="utf-8")
    return p


@pytest.mark.parametrize("texto, donde", [
    ("contrario: {nombre: UNO}\ncontrario: {nombre: DOS}\n", "contrario"),     # raíz: una parte entera
    ("contrario:\n  nombre: A\n  apellido1: X\n  apellido1: Y\n", "apellido1"),  # dentro de la parte
    ("colaboradores:\n  - {nombre: A, email: a@x.es, email: b@x.es}\n", "email"),
])
def test_R1H01_una_clave_repetida_se_rechaza_con_su_linea(tmp_path, texto, donde):
    with pytest.raises(ValueError, match=f"repetida.*{donde}|{donde}.*repetida"):
        cf.leer_yaml_ficha(_yaml(tmp_path, texto))


def test_alias_y_merge_se_rechazan(tmp_path):
    with pytest.raises(ValueError, match="alias"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "a: &x {nombre: A}\ncontrario: *x\n"))
    # Un merge necesita un alias, así que lo para la comprobación de alias, que va antes;
    # la del merge en el constructor es la segunda red, por si el escaneo cambia.
    with pytest.raises(ValueError, match="alias|merge"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "base: &b {nombre: A}\ncontrario: {<<: *b}\n"))


def test_documento_vacio_es_ficha_vacia(tmp_path):
    assert cf.leer_yaml_ficha(_yaml(tmp_path, "")) == {}


def test_un_yaml_normal_se_lee_igual_que_con_safe_load(tmp_path):     # control positivo
    import yaml
    texto = "contrario:\n  nombre: JUAN\n  nif: '00000000T'\nnotas_html: '<p>x</p>'\n"
    assert cf.leer_yaml_ficha(_yaml(tmp_path, texto)) == yaml.safe_load(texto)
```

- [ ] **Step 2:** `python -m pytest tests/test_crm_ficha_lector.py -p no:randomly --tb=short` → FALLAN (`leer_yaml_ficha` no existe).
- [ ] **Step 3: implementación** en `core/crm_ficha.py`:

```python
class _CargadorFicha(yaml.SafeLoader):
    """`SafeLoader` que no pierde nada en silencio (R1/H-01 del diseño): una clave
    repetida, un alias o un merge son un error con su línea, no «gana la última»."""


def _mapping_sin_perdida(loader: _CargadorFicha, node, deep=False):
    vistas: dict[object, int] = {}
    for clave_node, _valor in node.value:
        if clave_node.tag == "tag:yaml.org,2002:merge":
            raise ValueError(f"línea {clave_node.start_mark.line + 1}: el merge (`<<`) no se "
                             "admite en _ficha_crm.yaml: escribe cada clave")
        clave = loader.construct_object(clave_node, deep=deep)
        linea = clave_node.start_mark.line + 1
        if clave in vistas:
            raise ValueError(f"línea {linea}: la clave {clave!r} está repetida (ya en la "
                             f"línea {vistas[clave]}); YAML se quedaría solo con la última")
        vistas[clave] = linea
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_CargadorFicha.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                               _mapping_sin_perdida)


def leer_yaml_ficha(path: Path) -> dict:
    """El `_ficha_crm.yaml` como mapping, sin perder nada (spec §3 A.1). Lo usan
    `cargar_ficha_yaml` y `scripts/crm_colaboradores_firmas.py::apply`."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe _ficha_crm.yaml: {path}")
    texto = path.read_text(encoding="utf-8")
    if "&" in texto or "*" in texto:
        # PyYAML resuelve los alias en el composer, antes de construir: se detectan en
        # los eventos, que es donde siguen siendo visibles.
        for ev in yaml.parse(texto, Loader=yaml.SafeLoader):
            if isinstance(ev, yaml.AliasEvent) or getattr(ev, "anchor", None):
                raise ValueError(f"línea {ev.start_mark.line + 1}: los alias (`&`/`*`) no "
                                 "se admiten en _ficha_crm.yaml: escribe cada dato donde va")
    try:
        data = yaml.load(texto, Loader=_CargadorFicha)
    except yaml.YAMLError as exc:
        raise ValueError(f"_ficha_crm.yaml inválido: {exc}") from exc
    return {} if data is None else data
```

  (Los alias se detectan en los **eventos** porque PyYAML los resuelve en el *composer*, antes
  de que ningún constructor los vea; el prefiltro `&`/`*` solo evita el escaneo en el caso
  común, y un `&amp;` dentro de `notas_html` lo recorre sin falso positivo.)
- [ ] **Step 4:** los tests del Step 1 → PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): lector sin perdida del _ficha_crm.yaml (R1/H-01 del diseño)`.

---

### Task 2: Claves y tipos, en un solo `ValueError` (spec §3 A.2, A.3, A.5)

**Files:** Modify `core/crm_ficha.py` (`cargar_ficha_yaml` y constructores); Test `tests/test_crm_ficha_lector.py`.

**Interfaces:**
- Produces `CLAVES_RAIZ`, `CLAVES_CONTRARIO`, `CLAVES_COLABORADOR` (tuplas) y `validar_ficha(data: dict) -> list[str]` (lista de problemas con ruta; vacía = válida).
- `cargar_ficha_yaml(path)` = `leer_yaml_ficha` → `validar_ficha` (si hay problemas, un `ValueError` con todos, uno por línea) → construir.
- Consumes `leer_yaml_ficha` (Task 1).

- [ ] **Step 1: tests que fallan**

```python
@pytest.mark.parametrize("texto, ruta, sugerencia", [
    ("contrario: {nombre: A, nif: '1', apellido: X}\n", "contrario.apellido", "apellido1"),
    ("contrario:\n  - {nombre: A, nif: '1', apellido: X}\n", "contrario[0].apellido", "apellido1"),
    ("colaboradores:\n  - {nombre: A, email: a@x.es, mail: b}\n", "colaboradores[0].mail", "email"),
    ("contrarios: {nombre: A, nif: '1'}\n", "contrarios", "contrario"),
])
def test_clave_desconocida_con_ruta_y_sugerencia(tmp_path, texto, ruta, sugerencia):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    assert ruta in str(e.value) and sugerencia in str(e.value)


def test_varios_problemas_salen_todos(tmp_path):
    texto = "contrario: {nombre: A, nif: '1', apellido: X, dni: Y}\nnotas: z\n"
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for trozo in ("contrario.apellido", "contrario.dni", "notas"):
        assert trozo in str(e.value)


@pytest.mark.parametrize("texto, ruta", [
    ("contrario: {nombre: A, nif: '1', apellido1: {x: y}}\n", "contrario.apellido1"),
    ("contrario: {nombre: A, nif: '1', apellido1: [x]}\n", "contrario.apellido1"),
    ("notas_html: {texto: importante}\n", "notas_html"),
    ("contrario: {nombre: '   ', nif: '1'}\n", "contrario.nombre"),
    ("cliente_propio: false\n", "cliente_propio"),
    ("cliente_propio: 0\n", "cliente_propio"),
    ("cliente_propio: []\n", "cliente_propio"),
    ("cliente_propio: NO_EXISTE\n", "cliente_propio"),
    ("colaboradores: {nombre: A, email: a@x.es}\n", "colaboradores"),
    ("colaboradores:\n  - texto suelto\n", "colaboradores[0]"),
])
def test_R1H02_valor_de_otro_tipo_se_rechaza(tmp_path, texto, ruta):
    with pytest.raises(ValueError, match=__import__("re").escape(ruta)):
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))


@pytest.mark.parametrize("texto", ["false\n", "0\n", "[]\n", "texto\n"])
def test_una_raiz_que_no_es_mapping_se_rechaza(tmp_path, texto):
    with pytest.raises(ValueError, match="raíz|mapping"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))


def test_null_y_ausente_son_no_hay_dato(tmp_path):                    # control positivo
    f = cf.cargar_ficha_yaml(_yaml(tmp_path,
        "contrario: {nombre: A, nif: '1', apellido2: null}\ncolaboradores: null\n"))
    assert f.contrarios[0].apellido2 == "" and f.colaboradores == []
    assert f.cliente_propio == cf.CLIENTE_PROPIO_DEFAULT


def test_cada_clave_llega_a_su_atributo(tmp_path):
    """Centinela distinto por campo: mata el cruce de asignaciones, no solo la tupla."""
    campos = [c for c in cf.CLAVES_CONTRARIO if c != "id_crm"]
    texto = "contrario:\n" + "".join(f"  {c}: 'V_{c}'\n" for c in campos)
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for c in campos:
        assert getattr(f.contrarios[0], c) == f"V_{c}", c
    campos_col = [c for c in cf.CLAVES_COLABORADOR if c != "id_crm"]
    texto = "colaboradores:\n  - " + "\n    ".join(f"{c}: 'W_{c}'" for c in campos_col) + "\n"
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for c in campos_col:
        assert getattr(f.colaboradores[0], c) == f"W_{c}", c
```

  (Los contrarios de estos tests llevan `nif` porque la Task 3 exigirá identidad; se ponen ya para que este test no cambie después.)
- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación.**

```python
CLAVES_RAIZ = ("contrario", "colaboradores", "notas_html", "cliente_propio", "firmante")
CLAVES_CONTRARIO = ("nombre", "apellido1", "apellido2", "email", "movil", "nif",
                    "direccion", "poblacion", "cp", "provincia", "telefono", "id_crm")
CLAVES_COLABORADOR = ("nombre", "email", "movil", "telefono", "nif", "id_crm")


def _sugerencia(clave: str, validas) -> str:
    import difflib
    cerca = difflib.get_close_matches(str(clave), validas, n=1, cutoff=0.6)
    return f"; ¿querías {cerca[0]!r}?" if cerca else ""


def _problemas_escalar(valor, ruta: str) -> list[str]:
    if valor is None or isinstance(valor, str):
        return []
    if isinstance(valor, (bool, int, float)):
        return [f"{ruta}: vino como {type(valor).__name__} ({valor!r}); escríbelo entre "
                "comillas (YAML reinterpreta los ceros a la izquierda: `01001` es el octal 513)"]
    return [f"{ruta}: tiene que ser un texto o null, y es {type(valor).__name__}"]


def _problemas_parte(d: dict, ruta: str, validas: tuple[str, ...]) -> list[str]:
    fuera = [f"{ruta}.{k}: clave desconocida{_sugerencia(k, validas)}"
             for k in d if k not in validas]
    tipos = [p for k in validas if k != "id_crm" and k in d
             for p in _problemas_escalar(d[k], f"{ruta}.{k}")]
    nombre = d.get("nombre")
    if isinstance(nombre, str) and nombre.strip():
        vacio = []                        # el caso normal
    elif nombre is not None and not isinstance(nombre, str):
        vacio = []                        # el tipo ya lo ha dicho `_problemas_escalar`
    else:
        vacio = [f"{ruta}.nombre: falta o está vacío"]   # ausente, null o solo espacios
    return fuera + tipos + vacio


def validar_ficha(data) -> list[str]:
    """Todos los problemas de estructura, claves y tipos, con su ruta (spec §3 A.2-A.5)."""
    if not isinstance(data, dict):
        return [f"la raíz del _ficha_crm.yaml tiene que ser un mapping, y es "
                f"{type(data).__name__}"]
    p = [f"{k}: clave desconocida{_sugerencia(k, CLAVES_RAIZ)}" for k in data
         if k not in CLAVES_RAIZ]
    for k in ("notas_html", "firmante"):
        p += _problemas_escalar(data.get(k), k)
    cp = data.get("cliente_propio")
    if cp is not None and (not isinstance(cp, str) or cp.strip() not in _CLIENTES_PROPIOS):
        p.append(f"cliente_propio: {cp!r} no es uno de {sorted(_CLIENTES_PROPIOS)}")
    contr = data.get("contrario")
    if isinstance(contr, dict):
        p += _problemas_parte(contr, "contrario", CLAVES_CONTRARIO)
    elif isinstance(contr, list):
        for i, e in enumerate(contr):
            p += (_problemas_parte(e, f"contrario[{i}]", CLAVES_CONTRARIO) if isinstance(e, dict)
                  else [f"contrario[{i}]: tiene que ser un mapping"])
    elif contr is not None:
        p.append(f"contrario: tiene que ser un mapping o una lista, y es {type(contr).__name__}")
    cols = data.get("colaboradores")
    if isinstance(cols, list):
        for i, e in enumerate(cols):
            p += (_problemas_parte(e, f"colaboradores[{i}]", CLAVES_COLABORADOR)
                  if isinstance(e, dict) else [f"colaboradores[{i}]: tiene que ser un mapping"])
    elif cols is not None:
        p.append(f"colaboradores: tiene que ser una lista, y es {type(cols).__name__}")
    return p
```

  `_CLIENTES_PROPIOS` = las claves de `core.config.CLIENTES_PROPIOS_EV` (importarlo; no copiar la lista). `cargar_ficha_yaml` pasa a: `data = leer_yaml_ficha(path)`; `problemas = validar_ficha(data)`; si hay, `raise ValueError("_ficha_crm.yaml no se puede usar:\n  - " + "\n  - ".join(problemas))`; y construye **leyendo de las tuplas** (`_contrario_de`/`_colaborador_de` recorren `CLAVES_*` en vez de enumerar a mano). `cliente_propio` ausente/`null` → `CLIENTE_PROPIO_DEFAULT` (sin `or`). Los tests existentes de `_escalar` (octal, `None`) **siguen pasando sin tocarlos**.
- [ ] **Step 4:** nuevos + `python -m pytest tests -k crm_ficha -p no:randomly` → PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): claves y tipos por campo, todos los problemas en un error (MEJORAS #283; R1/H-02)`.

---

### Task 3: Identidad estable antes de escribir (spec §3 A.4)

**Files:** Modify `core/sudespacho_relations.py` (solo dos campos por defecto), `core/crm_ficha.py`; Test `tests/test_crm_ficha_lector.py`.

**Interfaces:** Produces `NuevoClienteContrario.id_crm: str = ""` y `NuevoColaborador.id_crm: str = ""`; `validar_ficha` añade «sin NIF, email ni id_crm».

- [ ] **Step 1: tests que fallan**

```python
def test_R1H04_una_parte_sin_nif_email_ni_id_crm_se_rechaza(tmp_path):
    with pytest.raises(ValueError, match="contrario.*NIF, email ni id_crm"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A}\n"))
    with pytest.raises(ValueError, match=r"colaboradores\[0\].*NIF, email ni id_crm"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, "colaboradores:\n  - {nombre: A}\n"))


@pytest.mark.parametrize("linea", ["id_crm: '1128'", "id_crm: 1128"])
def test_id_crm_admite_entero_o_digitos(tmp_path, linea):
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, f"contrario:\n  nombre: A\n  {linea}\n"))
    assert f.contrarios[0].id_crm == "1128"


@pytest.mark.parametrize("valor", ["'12a'", "true", "[1]", "''"])
def test_id_crm_que_no_son_digitos_se_rechaza(tmp_path, valor):
    with pytest.raises(ValueError, match="id_crm"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, f"contrario: {{nombre: A, id_crm: {valor}}}\n"))
```

- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación.** En `core/sudespacho_relations.py`, a los dos dataclasses: `id_crm: str = ""` **al final** (default: nadie más lo ve; `create_*` y los payloads no lo leen — comprobarlo con `git grep -n "id_crm"` tras el cambio). En `_problemas_parte`: `id_crm` válido si es `int` no booleano, o `str` de solo dígitos no vacía; y si no hay `nif` ni `email` no vacíos ni `id_crm`, el problema «`<ruta>`: sin NIF, email ni id_crm: cada corrida crearía otra ficha (A.4)». En los constructores, `id_crm=str(d["id_crm"]) if d.get("id_crm") is not None else ""`.
- [ ] **Step 4:** PASAN; `python -m pytest tests -k "crm_ficha or sudespacho_relations" -p no:randomly`.
- [ ] **Step 5:** commit `feat(crm_ficha): toda parte lleva NIF, email o id_crm (R1/H-04)`.

---

### Task 4: `crm_colaboradores_firmas.apply` lee sin pérdida (spec §3 A.1)

**Files:** Modify `scripts/crm_colaboradores_firmas.py:216-219`; Test el fichero de tests de ese script (`tests/test_crm_colaboradores_firmas*.py`: localizarlo con `git ls-files tests | Select-String colaboradores_firmas`).

- [ ] **Step 1: test que falla** — un `_ficha_crm.yaml` con `colaboradores` repetida (o una clave repetida dentro de un colaborador) y `apply --confirmar`: código de salida ≠ 0, el mensaje nombra la línea, y el fichero **conserva sus bytes** (`sha256` antes y después).
- [ ] **Step 2:** FALLA (hoy `safe_load` colapsa y reescribe).
- [ ] **Step 3:** sustituir `yaml.safe_load(...) or {}` por `leer_yaml_ficha(ficha_path)` dentro de `try/except ValueError` → `typer.echo("[ERROR] ...", err=True)` y `raise typer.Exit(code=1)` **antes** de cualquier cambio.
- [ ] **Step 4:** PASA, y los tests existentes del script siguen verdes.
- [ ] **Step 5:** commit `fix(crm_colaboradores_firmas): apply lee con el lector sin perdida y no reescribe una ficha que perderia datos`.

---

### Task 5: Vínculos por igualdad y datos declarados, puros (spec §4 B.1, B.2)

**Files:** Modify `core/crm_ficha.py`; Create `tests/test_crm_ficha_auditoria.py`.

**Interfaces:**
- `auditar_relaciones(esperado: Mapping[str, Sequence[str]], leido: Mapping[str, Sequence[Mapping]]) -> AuditoriaRelaciones` con `ok`, `faltan`, `sobran` (listas de `str` como `"colaboradores id=624"`).
- `auditar_datos(elemento: str, id_: str, declarado, ficha_crm: Mapping) -> list[str]` (vacía = todo igual; cada entrada `"clientes_contrarios id=1128 1apellido: vacío en el CRM"` o `"... distinto (CRM 'X', YAML 'Y')"`, o `"... provincia 'X' no reconocida: no puede llegar"`).
- `CAMPOS_CONTRARIO_CRM` / `CAMPOS_COLABORADOR_CRM`: tuplas `(campo_yaml, propiedad_crm, normalizador)`.

- [ ] **Step 1: tests que fallan**

```python
# tests/test_crm_ficha_auditoria.py
from core import crm_ficha as cf
from core.sudespacho_relations import NuevoClienteContrario, NuevoColaborador


def _rel(**bloques):
    return {k: [{"id": i} for i in v] for k, v in bloques.items()}


def test_R288_el_653_dos_colaboradores_de_mas_son_sobrantes():
    esperado = {"clientes_propios": ["2"], "clientes_contrarios": ["1128"],
                "colaboradores": ["256", "805", "102", "552"]}
    leido = _rel(clientes_propios=["2"], clientes_contrarios=["1128"],
                 colaboradores=["256", "805", "102", "552", "624", "677"])
    a = cf.auditar_relaciones(esperado, leido)
    assert a.faltan == [] and a.sobran == ["colaboradores id=624", "colaboradores id=677"]


def test_sobrantes_en_los_tres_bloques_incluso_con_cero_esperados():
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": [],
                               "colaboradores": []},
                              _rel(clientes_propios=["2", "27"], clientes_contrarios=["9"],
                                   colaboradores=["8"]))
    assert set(a.sobran) == {"clientes_propios id=27", "clientes_contrarios id=9",
                             "colaboradores id=8"}


def test_multiplicidad_en_los_dos_sentidos_y_id_int_frente_a_str():
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": ["5", "5"],
                               "colaboradores": ["7"]},
                              {"clientes_propios": [{"id": 2}], "clientes_contrarios": [{"id": 5}],
                               "colaboradores": [{"id": "7"}, {"id": "7"}]})
    assert "clientes_contrarios id=5" in a.faltan[0]
    assert a.sobran == ["colaboradores id=7"]


def test_bloques_que_no_gestiona_no_se_miran():                        # control positivo
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": [],
                               "colaboradores": []},
                              _rel(clientes_propios=["2"], actuaciones=["21496"]))
    assert a.faltan == [] and a.sobran == []


def test_R1H03_la_ficha_de_w030a13_con_el_apellido_vacio_no_pasa():
    decl = NuevoClienteContrario(nombre="ANA", apellido1="GARCIA", nif="00000000T")
    ficha = {"nombre": "ANA", "1apellido": "", "nif_cif": "00000000T"}
    assert cf.auditar_datos("clientes_contrarios", "1128", decl, ficha) == [
        "clientes_contrarios id=1128 1apellido: vacío en el CRM"]


def test_dato_distinto_se_dice_y_mayusculas_y_espacios_no_son_diferencia():
    decl = NuevoClienteContrario(nombre="Ana", apellido1="García", nif="00000000t",
                                 email="Ana@X.es", movil="+34 600 111 222")
    ficha = {"nombre": "ANA ", "1apellido": "GARCÍA", "nif_cif": "00000000T",
             "email": "ana@x.es", "movil": "600111222"}
    assert cf.auditar_datos("clientes_contrarios", "1", decl, ficha) == []
    ficha["1apellido"] = "PEREZ"
    assert cf.auditar_datos("clientes_contrarios", "1", decl, ficha) == [
        "clientes_contrarios id=1 1apellido: distinto (CRM 'PEREZ', YAML 'García')"]


def test_lo_que_el_yaml_no_declara_no_se_compara():
    decl = NuevoColaborador(nombre="ANA", email="ana@x.es")
    assert cf.auditar_datos("colaboradores", "7", decl,
                            {"nombre": "ANA", "email": "ana@x.es", "movil": "699"}) == []


def test_provincia_no_reconocida_no_puede_llegar():
    decl = NuevoClienteContrario(nombre="A", nif="1", provincia="Atlantida")
    assert "no reconocida" in cf.auditar_datos("clientes_contrarios", "1", decl,
                                               {"nombre": "A", "nif_cif": "1"})[0]
```

  (El `movil` normalizado que guarda el CRM se toma de `core.utils.normalize_es_phone`: si ese `600111222` no es su salida para `+34 600 111 222`, se ajusta el dato del test **a la salida real de la función**, no la función.)
- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación** — `auditar_relaciones` compara por `collections.Counter` de `str(id)` en `clientes_propios`, `clientes_contrarios` y `colaboradores`, en ese orden y con los ids ordenados para que la salida sea estable; `faltan` cuando `leido[id] < esperado[id]` (con «la corrida escribió N, la lectura ve M»), `sobran` una entrada por copia de más. `auditar_datos` recorre `CAMPOS_*_CRM`, salta los campos del YAML vacíos, normaliza los dos lados (`_texto`: `str(v or "").strip().casefold()`; `_nif`: sin espacios, puntos ni guiones, `upper`; `_email`: `strip().lower()`; `_tel`: `normalize_es_phone`; `provincia`: `provincia_canonica` sobre el YAML y `_texto` sobre el CRM) y devuelve los problemas. Mapas:

```python
CAMPOS_CONTRARIO_CRM = (
    ("nombre", "nombre", "texto"), ("apellido1", "1apellido", "texto"),
    ("apellido2", "2apellido", "texto"), ("email", "email", "email"),
    ("movil", "movil", "tel"), ("nif", "nif_cif", "nif"),
    ("direccion", "direccion", "texto"), ("poblacion", "poblacion", "texto"),
    ("cp", "cp", "texto"), ("provincia", "provincia", "provincia"),
    ("telefono", "telefono1", "tel"),
)
CAMPOS_COLABORADOR_CRM = (
    ("nombre", "nombre", "texto"), ("email", "email", "email"),
    ("movil", "movil", "tel"), ("telefono", "telefono1", "tel"), ("nif", "nif_cif", "nif"),
)
```

  **Antes de dar por buenos `1apellido`, `2apellido` y `nif_cif` para `clientes_contrarios`**, contrastarlos con el payload de `create_cliente_contrario` (`core/sudespacho_relations.py:874-882`) y con `docs/CRM_SUDESPACHO_ATLAS.md`; si alguno no cuadra, se corrige el mapa y se anota de dónde salió.
- [ ] **Step 4:** PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): auditar vinculos por igualdad y datos declarados, puros (MEJORAS #288; R1/H-03)`.

---

### Task 6: El CLI usa las auditorías y la vía `id_crm` (spec §4 B.3, B.4; §3 A.4)

**Files:** Modify `scripts/crm_ficha.py`; Test `tests/test_crm_ficha_cli.py`.

**Interfaces:** Consumes `auditar_relaciones`, `auditar_datos` (Task 5), `NuevoClienteContrario.id_crm` / `NuevoColaborador.id_crm` (Task 3). Importa en el módulo del CLI `get_cliente_contrario`, `get_colaborador`, `link_contrario`, `link_colaborador` para que los tests puedan doblarlos por su ruta (`scripts.crm_ficha.<nombre>`).

- [ ] **Step 1: el ayudante y los tests que fallan**

```python
# tests/test_crm_ficha_cli.py — ayudante nuevo, al principio
def _declara_fichas(monkeypatch, contrarios=None, colaboradores=None):
    """La verificación de datos RELEE cada parte (spec §4 B.2). Declarar esas lecturas
    es preparación del doble, no un aserto: cada test que llega a la verificación
    dice qué ficha devuelve el CRM para cada id."""
    c, k = dict(contrarios or {}), dict(colaboradores or {})
    monkeypatch.setattr("scripts.crm_ficha.get_cliente_contrario", lambda i: c[str(i)])
    monkeypatch.setattr("scripts.crm_ficha.get_colaborador", lambda i: k[str(i)])
```

  Tests nuevos (sobre la fixture `caso_con_ficha`, que declara JUAN PEREZ `00000000T` y ANA):
  - **el 653:** `get_relaciones` devuelve un colaborador `624` de más → código 1, `[SOBRA] colaboradores id=624` en la salida y **sin** «VERIFICADA»;
  - **W-030A13 relanzado:** `ensure_c` devuelve `("1128", False)` y la ficha leída de 1128 trae `1apellido` vacío → `[DATO] clientes_contrarios id=1128 1apellido: vacío en el CRM`, código 1, **cero** llamadas de actualización nuevas desde el CLI;
  - **`id_crm`:** YAML con `contrario: {nombre: JUAN, id_crm: '1128'}` → **no** se llama `ensure_contrario_vinculado`, sí `get_cliente_contrario('1128')` y `link_contrario('606', '1128')`; si la ficha leída tiene otro `nombre` → código 1 **antes** de vincular;
  - **parcial:** `ensure_col` lanza → código 1, la salida dice «sobrantes: sin comprobar» y no hay `[SOBRA]` aunque `get_relaciones` devuelva un colaborador desconocido;
  - **lectura de ficha fallida:** `get_cliente_contrario` lanza → «SIN VERIFICAR: datos de clientes_contrarios id=…», nunca «VERIFICADA».
- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación.**
  - Sustituir el cierre `_auditar` por `auditar_relaciones`; en la **parcial**, imprimir solo `faltan` más la línea «sobrantes: sin comprobar…».
  - Tras las escrituras y la relectura de vínculos, para cada parte resuelta leer su ficha (`get_cliente_contrario` / `get_colaborador`) y juntar `auditar_datos(...)`; un fallo de lectura va a `sin_verificar` con el id.
  - Vía `id_crm` (antes de `ensure_*`): leer la ficha por id, exigir `nombre` igual (normalizado con `_texto`); si no, error y `Exit(1)` **antes** del primer writer — por eso las partes con `id_crm` se comprueban **todas** justo después de cargar el YAML, antes de `link_ev_mmc`. Si cuadra, `link_contrario` / `link_colaborador` y su id a `esperado`.
  - Veredicto: `faltan` o `sobran` o `[DATO]` → los mensajes del spec §4 B.3 y código 1; `sin_verificar` → «OK ficha CRM completada — SIN VERIFICAR: …»; nada → «OK ficha CRM completada y VERIFICADA: vínculos y datos de la ficha».
  - **Tests existentes que llegan a la verificación** (los 15 que declaran `get_relaciones`): se les añade `_declara_fichas(...)` con la ficha coherente con su YAML. **Ningún aserto se toca**; el commit lo enumera.
- [ ] **Step 4:** `python -m pytest tests -k crm_ficha -p no:randomly` → PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): el CLI falla con sobrantes y con datos que no llegaron; via id_crm (MEJORAS #288; R1/H-03, H-04)`.

---

### Task 7: Arnés de mutantes (spec §6)

**Files:** Create `tests/_mutantes_crm_ficha.py` (mismo patrón que `tests/_mutantes_mejoras_214.py`: cada mutante sobre una **copia**, y exige que muera **por su test**, nombrado).

| Mutante | Tiene que morir por |
|---|---|
| el lector acepta claves repetidas (quitar la comprobación en `_mapping_sin_perdida`) | `test_R1H01_una_clave_repetida_se_rechaza_con_su_linea` |
| `_problemas_escalar` acepta mappings | `test_R1H02_valor_de_otro_tipo_se_rechaza` |
| se quita el cálculo de `sobran` | `test_R288_el_653_...` |
| `Counter` sustituido por `set` | `test_multiplicidad_en_los_dos_sentidos_...` |
| `auditar_datos` devuelve siempre `[]` | `test_R1H03_la_ficha_de_w030a13_...` |
| dos asignaciones del constructor cruzadas | `test_cada_clave_llega_a_su_atributo` |
| la parcial calcula sobrantes | el test «parcial» de la Task 6 |
| se quita la exigencia de identidad | `test_R1H04_una_parte_sin_...` |

- [ ] Correr `python -m tests._mutantes_crm_ficha`: todos muertos, cada uno por el suyo. Commit.

---

### Task 8: Documentación, cierre y la R2

- [ ] `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`, donde se prepara el `_ficha_crm.yaml`: el contrato nuevo en cinco líneas (claves de cada nivel, tipos, NIF/email/`id_crm`, el YAML es la lista completa, qué hacer con un `[SOBRA]` y con un `[DATO]`).
- [ ] `docs/MEJORAS_FUTURAS.md`: `#283` y `#288` `[CERRADA …]` con el PR; y una entrada nueva, si no existe ya, para **completar apellidos vacíos** de una ficha existente (spec §5), con su radio de daño.
- [ ] `PLAN.md` fila #40 al día; bitácora; `python -m scripts.session_close` (dos semillas).
- [ ] **R2 de Codex sobre el diff**, `gpt-6-astra` · `medium` · `default`, lanzador con los tres flags, vigía de fin **y** muerte, mandato numerado y anclado a commits, con los dos ejes. Adjudicación embebida en el spec (§9) y acta hermana `…-r2-adversarial-review.md`. **Techo:** una tercera ronda solo con autorización expresa de Nikolai.
- [ ] Antes de usarlo en un caso real: correr `crm_ficha --dry-run` y después sobre un expediente de prueba, **verificando por lectura** en el CRM.

## Self-review

- **Cobertura del spec:** A.1 → T1 + T4; A.2/A.3/A.5 → T2; A.4 → T3 + T6; B.1 → T5 + T6; B.2 → T5 + T6; B.3/B.4 → T6; §5 (fuera) → T8 abre la entrada de completar apellidos; §6 → tests de T1-T6 y T7; §7 → T8.
- **Nombres consistentes:** `leer_yaml_ficha`, `validar_ficha`, `CLAVES_*`, `auditar_relaciones`/`AuditoriaRelaciones`, `auditar_datos`, `CAMPOS_*_CRM`, `id_crm`, `_declara_fichas` — los mismos en todas las tareas.
- **Comprobado con un prototipo desechable el 2026-09-25**, fuera del repo, antes de dar el plan
  por bueno: el constructor detecta la clave repetida en raíz y dentro de una parte, con su
  línea; un YAML normal carga igual que con `safe_load`; los alias se ven en los eventos y un
  `&amp;` de `notas_html` no da falso positivo; el merge lo para el constructor aunque no haya
  alias; y `normalize_es_phone("+34 600 111 222")` devuelve `600111222`, que es el dato de T5.
- **Lo que queda por fijar al implementar, dicho donde toca:** las propiedades del CRM de
  `clientes_contrarios` (T5, contra el payload y el atlas).

## 9. Adjudicación de la revisión adversarial del plan (Codex, 2026-09-25) — REQUIERE-REVISION, pendiente

- **Objeto revisado:** este plan rev. 1 y, como segundo encargo, si el spec rev. 2 remedia de verdad la R1; los dos en `0177559`
- **Ronda:** R2 de la pieza (la R1 fue sobre el spec rev. 1; la R3, sobre el diff, la autorizó expresamente Nikolai el 2026-09-25)
- **Revisor:** Codex CLI `0.155.0-alpha.16.3`, `gpt-6-astra` · `medium` · `default` (modelo y esfuerzo releídos del rollout)
- **Informe recibido:** `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto-r2-adversarial-review.md`
- **Hallazgos:** 9 — 2 `alta`, 7 `media`; 9 confirmados contra la fuente, 0 refutados
- **Remediado en:** pendiente — el spec rev. 3 y el plan rev. 2 se escriben al abrir la sesión que implemente, **antes de su Task 1**; esta sección es la lista cerrada de lo que cambia

**Los nueve se reprodujeron contra el código y contra el texto de este plan, no contra el
informe** (acta §2): el bloque literal de la Task 1 ejecutado tal cual, el DTO y
`provincia_canonica` reales, `difflib` con la tupla del plan, y la lectura de
`core/sudespacho_relations.py:1669-1736` y de `scripts/crm_ficha.py:79-163`. **No son nueve
defectos sueltos: son tres fronteras**, y el remedio es el de la frontera.

**Frontera 1 — ninguna escritura sobre una ficha que el YAML contradice (H-01, H-06, H-08).** El
plan vinculaba por `id_crm` tras comparar **solo** el nombre y dejaba toda comparación de datos
para después de escribir; la resolución por NIF completa lo vacío de una ficha cuyo apellido el
YAML contradice (el revisor lo midió con el completado real: sale un PUT del email); la Task 3
aceptaba `id_crm` tres commits antes de que nadie lo consumiera, y en ese intervalo esa parte
seguía el camino de **creación**; y el preflight iba antes del corte de `--dry-run`. Decisión de
diseño, que entra en el spec rev. 3 (A.4, B.2 y §6):

1. **Una fase previa de solo lectura**, después del `--dry-run` y de la cancelación y antes de
   `link_ev_mmc`. Para cada parte, la ficha que **ya existe** —por `id_crm` (GET) o por NIF/email
   (la resolución de hoy, que ya es de solo lectura y ya levanta ante conflicto o ambigüedad)— se
   compara con lo declarado. Un campo **distinto** —el CRM tiene valor y es otro— es error:
   **todos juntos y cero writers**. La corrida nunca pisa, así que ese `[DATO]` no lo puede
   arreglar ella; escribir antes solo dejaría un vínculo y unos completados sobre una ficha que el
   propio YAML desmiente, y `crm_ficha` no desvincula. Una ficha que no se puede leer, o un
   `id_crm` que no existe, también es error: no se escribe sobre lo que no se ha podido comparar.
   Lo **vacío** no es contradicción: si es completable se completa como hoy, y si no, lo dice la
   lectura final (el caso de W-030A13). **La fase previa es la parte de B.2 que ya está decidida
   antes de escribir**: lo no vacío del CRM no cambia al completar, así que no puede fallar donde
   la lectura final no fallaría.
2. **`id_crm` vive en el core**, en los dos `_resolver_o_crear_*`
   (`core/sudespacho_relations.py:1669` y `:2436`): con `id_crm`, ni busca ni crea; lee esa
   ficha, completa lo vacío igual que con una ficha hallada por NIF y devuelve `(id, False)`. El
   CLI sigue llamando a `ensure_*` para toda parte: **no hay un segundo camino de escritura en la
   orquestación**, y el vínculo por id hereda el completado sin reescribirlo. El campo del DTO,
   la aceptación en el validador y esa rama van en **la misma tarea y el mismo commit** (H-06);
   hasta ese commit, la Task 3 exige NIF o email y rechaza la parte que solo trae `id_crm`, que es
   el estado intermedio seguro.
3. **Lo que no puede llegar nunca es propiedad de la declaración, no de la ficha**, y lo rechaza
   la validación para toda parte, creada o existente: una provincia que `provincia_canonica` no
   reconoce y un teléfono no vacío que `normalize_es_phone` deja vacío (H-02). Y `auditar_datos`
   recibe **la declaración** —el mapping validado de la parte—, no el DTO: el DTO normaliza al
   construirse, y cualquier transformación entre el YAML y la auditoría es un sitio por donde lo
   declarado se pierde sin que la auditoría lo vea.
4. **La lectura final (B.2) sigue**, para creadas y completadas, y el spec lo dice sin prometer de
   más: detectar un dato que no llegó al crear o al completar exige leer después, y esa lectura
   **no deshace** la creación ni el vínculo. El §6 cambia «dato distinto → `[DATO]` sin PUT» por
   «dato distinto **preexistente** → error antes del primer writer y **cero** llamadas a writers,
   con la resolución y el completado reales y el transporte doblado».

**Frontera 2 — lo declarado llega intacto a la auditoría (H-02, H-03, H-04).** El DTO borra
`'+34'`; la provincia se normalizaba distinto a cada lado (`provincia_canonica` devuelve
`'Barcelona'` y `_texto` lo pasa a minúsculas: nunca iguales); y el lector dejaba escapar
`TypeError` y `ParserError` donde prometía `ValueError`, y de varias repetidas solo decía la
primera. Remedios: el punto 3 de arriba; `_texto(provincia_canonica(yaml))` contra `_texto(crm)`,
con su control positivo (`barcelona` frente a `Barcelona`); y en la Task 1, el escaneo de eventos
**dentro** del `try` que traduce `yaml.YAMLError`, una clave no escalar rechazada con su línea, y
las repetidas **acumuladas** en todo el documento. Límite que se declara en vez de prometerlo: un
error de sintaxis para el análisis, y solo se puede decir ese.

**Frontera 3 — un test prueba la propiedad que nombra, por el camino que nombra (H-05, H-07,
H-09).** El doble `_declara_fichas` convertía un id no declarado en `KeyError`, que el CLI tomaría
por lectura caída —«SIN VERIFICAR» y salida 0—, y tres tests que solo miran la salida 0 seguirían
verdes; los «PASAN» de las Tasks 2, 3 y 6 eran incompatibles con diecisiete tests existentes y con
dos literales; y las filas «Convergencia», «GET o PUT de completar fallidos» y «fallar cada
writer» del spec §6 no tenían tarea. **Y uno que el revisor no citó:**
`tests/test_crm_ficha_cli.py:283` y `:403` afirman `"VERIFICADA por lectura" not in r.output`;
con el literal de éxito nuevo pasarían **siempre**, que es un negativo vaciado en silencio y no un
aserto relajado a la vista.

**Lo que cambia en cada tarea (plan rev. 2):**

- **Task 1.** Lo de la frontera 2, con sus tests: la línea **afirmada** (`línea 2`), no solo la
  palabra «repetida»; el merge **sin** alias en su propio test —el comentario «un merge necesita
  un alias» es falso: `{<<: {nombre: A}}` no lo lleva—; la clave lista; la sintaxis rota →
  `ValueError`; y dos repetidas → las dos.
- **Task 2.** `id_crm` fuera de las tuplas hasta su tarea. `_sugerencia` da **todas** las cercanas
  (`apellido` → `apellido1` y `apellido2`), sin convertirlas en alias de entrada, y un control sin
  sugerencia. El mensaje de cliente desconocido conserva el literal `cliente_propio desconocido`
  que exige `tests/test_crm_ficha_cli.py:164`. `test_cliente_propio_con_valor_se_respeta` pasa a
  una clave **real** no predeterminada del catálogo —la propiedad es «lo declarado se respeta», y
  `OTRO_CLIENTE` ya no es declarable—, dicho en el commit. La matriz de tipos en **cada** escalar
  de los dos roles y `firmante`, y `cliente_propio: {}`. Y la validación de provincia y teléfonos
  del punto 3.
- **Task 3.** Identidad obligatoria **por NIF o email**, sin `id_crm` todavía. La migración de los
  diecisiete tests se escribe en la tarea —identidades sintéticas—, y
  `test_se_valida_la_coleccion_ENTERA_antes_de_construir_nada` recibe identidad en su primer
  elemento y espía la construcción, o su `raises` pasaría aunque se ignorase el segundo.
- **Task 4.** Sin cambios de fondo; su mutante entra en la Task 9.
- **Task 5.** `auditar_datos(elemento, id_, declarado: Mapping, ficha_crm)`, con resultado
  estructurado (campo, tipo `vacio`/`distinto`, CRM, YAML) para que la fase previa filtre
  `distinto`; la provincia simétrica; la matriz campo × rol × creada/existente, con negativos de
  colaborador; y los mapas `CAMPOS_*_CRM` anclados a la fuente que el revisor ya encontró (payload
  en `core/sudespacho_relations.py:872-882`, GET en `:1751-1754`, atlas
  `docs/CRM_SUDESPACHO_ATLAS.md:1892-1926`, `docs/INTEGRACION_SUDESPACHO.md:746` y `:769-774`).
  El «por fijar» del Self-review se retira, con la regla de medir antes de codificar si al
  implementar algo no cuadra.
- **Task 6 (el CLI, sin la vía `id_crm`).** `_declara_fichas` levanta una excepción de arnés
  **fuera de `Exception`** ante un id no declarado, como la guarda de red
  (`tests/test_crm_ficha_cli.py:303-336`). Los controles positivos exigen la certificación
  completa y la **ausencia** de «SIN VERIFICAR». El literal de éxito es una **constante del
  módulo** que importan los tests, positivos y negativos, así que un cambio de texto no puede
  vaciar un negativo. La lectura sintética del test de W-030A13 conserva el móvil de la fixture.
  Un caso con `[FALTA]` y `[SOBRA]` a la vez, y un fallo conocido que gana a un «SIN VERIFICAR»
  simultáneo. «Ningún aserto se toca» se sustituye por «los literales del contrato nuevo se
  adaptan por escrito, enumerados en el commit, y ninguno pierde su propiedad».
- **Task 7 (nueva): la fase previa y `id_crm`, juntas.** El campo del DTO, la aceptación de
  `id_crm` en el validador, la rama del core y la fase previa del punto 1, en un commit. Tests: la
  parte por id que contradice su NIF declarado → error y cero writers; una parte por NIF cuya
  ficha trae otro apellido → error y cero writers; un id inexistente o un GET caído → error antes
  de escribir; la **segunda** parte inválida → cero writers también para la primera; un
  colaborador por id; y `--dry-run` con `id_crm` cuyos GET **revientan el test** si se llaman.
- **Task 8 (nueva): integración.** `ensure_*`, resolutores y completado **reales**, con el
  transporte doblado en `core.sudespacho_relations.<nombre>` y un espía de **todos** los writers:
  un doble **con estado** y dos corridas (la segunda ni crea ni declara sobrante la primera); GET y
  PUT de completar fallidos → al veredicto; cada writer fallando → código 1, sin «VERIFICADA», sin
  sobrantes inventados; y cero writers ante cada entrada inválida de las Tasks 1-3 y 7.
- **Task 9 (la antigua 7, mutantes).** Sobre **copias**: no el patrón de
  `tests/_mutantes_mejoras_214.py`, que escribe en el árbol real y restaura, justo lo que prohíbe
  `tests/test_guard_aislamiento_paralelo.py`. Base verde, cada mutante aplicado **una** vez y el
  test objetivo **ejecutado** y rojo por su aserto —no por colección ni por el arnés—, con el
  detalle guardado. Mutantes nuevos: desconectar el lector en uno de los dos consumidores; quitar
  el rechazo del merge sin alias; saltarse un rol o las partes creadas en la auditoría; quitar la
  fase previa o moverla detrás de un writer; leer el CRM en `--dry-run`. «La parcial calcula
  sobrantes» pasa a «la parcial **emite** sobrantes», que es lo observable.
- **Task 10 (la antigua 8).** La ronda del diff es la **R3**, autorizada; su adjudicación va en
  este plan (§10) y su acta es `…-r3-adversarial-review.md`.
- **Cabecera.** La línea de Global Constraints que dice «la R2 va sobre este diff» y la fila de
  File Structure que dice que `core/sudespacho_relations.py` «solo añade `id_crm`», al día: con el
  punto 2 añade también la rama por id de los dos resolutores, y sin `id_crm` ningún
  comportamiento cambia.

**Los remedios de la rev. 2 a la R1: el dictamen del revisor se acepta.** H-01 y H-02, **reales**;
H-03 y H-04, **incompletos**, y lo que les faltaba es exactamente esta R2 (H-01, H-02, H-06 y
H-09). Ninguno cosmético.

**Lo que el revisor intentó y no pudo, y se conserva:** la igualdad por multiplicidad detecta
sobrantes y colapsos; la lista completa no necesita revisarse; el lector detecta las repetidas
**antes** de la pérdida y el `&amp;` de `notas_html` no es un alias; las firmas y propiedades del
CRM existen; el mutante de mappings muere por su aserto; la parcial que solo informa faltantes no
abre un falso «VERIFICADA»; y nada obliga a desvincular, a ampliar el completado a los apellidos
ni a construir C6.

**Lo que NO cambia:** el YAML es la lista completa; `crm_ficha` nunca desvincula ni pisa;
`_COMPLETABLES_*` no se toca.
