# `crm_ficha`: el YAML entero y el conjunto verificado — plan de implementación

> **Estado (2026-09-26): rev. 2, ejecutado.** La rev. 1 es la que revisó la R2 (`0177559`); esta
> la sustituye, y lo que cambió de una a otra, tarea a tarea, está en la §9, que se conserva tal
> cual como adjudicación. La R3, sobre el diff, está adjudicada en la §10 y remediada en el mismo
> PR, sin otra ronda que revise el remedio. Spec: rev. 4.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que `crm_ficha` no pierda nada de lo que el `_ficha_crm.yaml` declara, que no escriba sobre una ficha que el YAML contradice, y que su «VERIFICADA» certifique de verdad que el expediente tiene exactamente esas partes con esos datos (`MEJORAS #283` + `#288`).

**Architecture:** lo que decide vive en `core/crm_ficha.py` como funciones puras —lectura sin pérdida, validación de claves, tipos e identidad, auditoría de vínculos y de datos, y las contradicciones que la fase previa no deja pasar—. `core/sudespacho_relations.py` gana `id_crm` en los dos DTOs y dos resolutores de solo lectura (`resolver_contrario_existente`, `resolver_colaborador_existente`), con la rama por id dentro, que usan los `_resolver_o_crear_*` de siempre. `scripts/crm_ficha.py` orquesta: carga, plan, `--dry-run`, **fase previa de solo lectura**, escrituras por `ensure_*`, relecturas y veredicto. `scripts/crm_colaboradores_firmas.py` lee con el mismo lector. No hay endpoint nuevo.

**Tech Stack:** Python 3.14, PyYAML (`SafeLoader`), pytest + typer `CliRunner`, `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md` **rev. 3** (§ citados abajo). Leerlo entero antes de empezar.

## Global Constraints

- El `_ficha_crm.yaml` es la lista **completa** de partes del expediente (decisión de Nikolai, 2026-09-25): una parte vinculada que no declara es **fallo**.
- `crm_ficha` **nunca desvincula** ni **pisa** un dato existente. La política de completar solo lo vacío (`_COMPLETABLES_*` de `core/sudespacho_relations.py`) **no se toca**.
- Todo `ValueError` de validación sale **antes de cualquier llamada al CRM**, con **todos** los problemas juntos; todo problema de la fase previa sale **antes del primer writer** (`link_ev_mmc`), también todos juntos. `--dry-run` no lee el CRM.
- Los tests no tocan la red: la guarda `_sin_red` (una `BaseException`) sigue en su sitio, y los dobles se declaran por su ruta (`scripts.crm_ficha.<nombre>` en el CLI; `core.sudespacho_relations.<nombre>` en la integración). Una lectura **no declarada** levanta una excepción de arnés que tampoco hereda de `Exception`. Ningún test escribe fuera de `tmp_path`.
- **Ningún aserto pierde su propiedad.** Los literales del contrato nuevo se adaptan por escrito, las fixtures se migran por escrito (identidades sintéticas, `id_crm`), y cada commit los enumera. Nada de `skip`, `xfail` ni aserto relajado.
- Aceptación: `python -m scripts.session_close` (dos semillas). Radio de daño: dos rondas y una tercera autorizada; la R1 (spec), la R2 (plan) y la R3 (diff, §10) están hechas, las tres con `gpt-6-astra` · `medium` · `default`. No hay cuarta sin autorización expresa de Nikolai.
- Intérprete: el venv de la raíz, `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`, ejecutado **desde el worktree** (medido el 2026-09-25: `core`, `scripts` y `tests` se importan del worktree, no de la raíz). En los comandos de abajo, `python` es ese.

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `core/crm_ficha.py` | lector sin pérdida (`leer_yaml_ficha`), `CLAVES_*`, `validar_ficha`, `cargar_ficha_yaml` (DTOs **y** declaraciones), `auditar_relaciones`, `auditar_datos`/`Discrepancia`, `CAMPOS_*_CRM`, `contradicciones_previas` |
| `core/sudespacho_relations.py` | `id_crm: str = ""` en `NuevoClienteContrario` y `NuevoColaborador`; `resolver_contrario_existente` y `resolver_colaborador_existente` (solo lectura, con la rama por `id_crm`), que usan los dos `_resolver_o_crear_*`. Sin `id_crm`, ningún comportamiento cambia |
| `scripts/crm_ficha.py` | orquesta: carga, plan, `--dry-run`, fase previa, escrituras, relecturas y veredicto; `EXITO_VERIFICADA` y `SIN_VERIFICAR` como constantes del módulo |
| `scripts/crm_colaboradores_firmas.py` | `apply` lee con `leer_yaml_ficha` |
| `tests/test_crm_ficha_lector.py` (nuevo) | Tasks 1-3, la declaración de la 6 y el validador de la 7 |
| `tests/test_crm_ficha_auditoria.py` (nuevo) | Task 5 y `contradicciones_previas` (Task 7) |
| `tests/test_crm_ficha_id_crm.py` (nuevo) | la rama por id del core (Task 7) |
| `tests/test_crm_ficha_cli.py` | Tasks 6 y 7: los ayudantes `_declara_fichas` y `_declara_resolucion`, los tests nuevos y las migraciones |
| `tests/test_crm_ficha_integracion.py` (nuevo) | Task 8: `CRMFalso` con estado y espía de writers |
| `tests/test_crm_colaboradores_firmas_cli.py` | Task 4 |
| `tests/_mutantes_crm_ficha.py` (nuevo) | Task 9, sobre una copia del árbol |
| `tests/_mutantes_p6.py` | Task 2: M11 re-apuntado a donde vive ahora su propiedad |
| migraciones | `tests/test_crm_ficha_yaml_none.py`, `test_crm_ficha_n_contrarios.py`, `test_crm_ficha_validacion.py`, `test_crm_ficha_validacion_r1.py`, `test_crm_ficha_cli.py`, `test_crm_colaboradores_firmas_cli.py` (Tasks 2, 3, 6 y 7) |

**Medido antes de escribir este plan (2026-09-25), con una sonda desechable** que antepone las reglas nuevas al loader de `4209582` y corre los catorce ficheros de test que cargan un `_ficha_crm.yaml` (baseline verde): **las claves y los tipos (Task 2) rompen 1 test**, el `OTRO_CLIENTE`; **la identidad (Task 3) rompe 22 más**. La §9 decía «diecisiete»: la R2 midió cinco ficheros y la regla alcanza a seis. Las 23 migraciones van enumeradas en sus tareas, más cuatro de precisión: tests cuyo `raises` seguiría verde, pero ya no solo por su propiedad.

---

### Task 1: Lector sin pérdida (spec §3 A.1)

**Files:** Modify `core/crm_ficha.py`; Create `tests/test_crm_ficha_lector.py`.

**Interfaces:** Produces `leer_yaml_ficha(path: Path) -> Any` — el documento tal cual (`{}` si está vacío; cualquier otra raíz la rechaza `validar_ficha` en la Task 2). Lanza `ValueError` con **todas** las claves repetidas (con su línea y la de la primera), todos los alias y anclas, todos los merge y todas las claves que no son un texto; `ValueError` ante una sintaxis rota (y solo ese); `FileNotFoundError` si no existe. Es **aditiva**: nadie la consume hasta la Task 2 (la R2 lo dio por bueno).

- [ ] **Step 1: tests que fallan**

```python
# tests/test_crm_ficha_lector.py
"""El `_ficha_crm.yaml` se lee entero o no se lee (spec §3, Parte A)."""
import re

import pytest
import yaml

from core import crm_ficha as cf


def _yaml(tmp_path, texto):
    p = tmp_path / "_ficha_crm.yaml"
    p.write_text(texto, encoding="utf-8")
    return p


@pytest.mark.parametrize("texto, clave, linea, primera", [
    ("contrario: {nombre: UNO}\ncontrario: {nombre: DOS}\n", "contrario", 2, 1),   # una parte entera
    ("contrario:\n  nombre: A\n  apellido1: X\n  apellido1: Y\n", "apellido1", 4, 3),
    ("colaboradores:\n  - {nombre: A, email: a@x.es, email: b@x.es}\n", "email", 2, 2),
])
def test_R1H01_una_clave_repetida_se_rechaza_con_su_linea(tmp_path, texto, clave, linea, primera):
    with pytest.raises(ValueError) as e:
        cf.leer_yaml_ficha(_yaml(tmp_path, texto))
    assert (f"línea {linea}: la clave {clave!r} está repetida (ya en la línea {primera})"
            in str(e.value))


def test_R2H04_dos_repetidas_salen_las_dos(tmp_path):
    with pytest.raises(ValueError) as e:
        cf.leer_yaml_ficha(_yaml(tmp_path, "a: 1\na: 2\nb: 1\nb: 2\n"))
    assert "línea 2: la clave 'a'" in str(e.value) and "línea 4: la clave 'b'" in str(e.value)


@pytest.mark.parametrize("texto, forma", [("? [a, b]\n: c\n", "una lista"),
                                          ("? {a: 1}\n: c\n", "un mapping")])
def test_R2H04_una_clave_que_no_es_texto_se_rechaza_con_su_linea(tmp_path, texto, forma):
    with pytest.raises(ValueError, match=f"línea 1: una clave tiene que ser un texto, y aquí es {forma}"):
        cf.leer_yaml_ficha(_yaml(tmp_path, texto))


def test_los_alias_se_rechazan_con_su_linea(tmp_path):
    with pytest.raises(ValueError, match=r"línea 1: los alias"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "a: &x {nombre: A}\ncontrario: *x\n"))


def test_R2_el_merge_SIN_alias_se_rechaza(tmp_path):
    """`{<<: {nombre: A}}` no lleva alias: lo para la comprobación del merge, no la de alias."""
    with pytest.raises(ValueError, match=r"línea 1: el merge"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "contrario: {<<: {nombre: A}}\n"))


def test_el_merge_con_alias_tambien(tmp_path):
    with pytest.raises(ValueError, match="alias"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "base: &b {nombre: A}\ncontrario: {<<: *b}\n"))


def test_R2H04_una_sintaxis_rota_sale_como_ValueError(tmp_path):
    with pytest.raises(ValueError, match="inválido"):
        cf.leer_yaml_ficha(_yaml(tmp_path, 'notas_html: ["*",\n'))


@pytest.mark.parametrize("texto", ["", "# solo un comentario\n"])
def test_documento_vacio_es_ficha_vacia(tmp_path, texto):
    assert cf.leer_yaml_ficha(_yaml(tmp_path, texto)) == {}


def test_un_yaml_normal_se_lee_igual_que_con_safe_load(tmp_path):     # control positivo
    texto = "contrario:\n  nombre: JUAN\n  nif: '00000000T'\nnotas_html: '<p>E&amp;V</p>'\n"
    assert cf.leer_yaml_ficha(_yaml(tmp_path, texto)) == yaml.safe_load(texto)


def test_si_no_existe_FileNotFoundError(tmp_path):
    with pytest.raises(FileNotFoundError):
        cf.leer_yaml_ficha(tmp_path / "no.yaml")
```

- [ ] **Step 2:** `python -m pytest tests/test_crm_ficha_lector.py -p no:randomly --tb=short` → FALLAN (`leer_yaml_ficha` no existe).
- [ ] **Step 3: implementación** en `core/crm_ficha.py` (prototipada el 2026-09-25 contra los 19 casos de arriba y de la R2, fuera del repo):

```python
_ETIQUETA_MERGE = "tag:yaml.org,2002:merge"


class _CargadorFicha(yaml.SafeLoader):
    """`SafeLoader` que no pierde nada en silencio (spec §3 A.1). Una clave repetida, un merge
    o una clave que no es un texto no se resuelven —«gana la última»—: se APUNTAN con su línea,
    y `leer_yaml_ficha` los levanta todos juntos (R2/H-04)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.problemas: list[str] = []


def _mapping_sin_perdida(loader: _CargadorFicha, node: yaml.MappingNode,
                         deep: bool = False) -> dict:
    vistas: dict[object, int] = {}
    resultado: dict = {}
    for clave_node, valor_node in node.value:
        linea = clave_node.start_mark.line + 1
        if clave_node.tag == _ETIQUETA_MERGE:
            loader.problemas.append(f"línea {linea}: el merge (`<<`) no se admite en "
                                    "_ficha_crm.yaml: escribe cada clave")
            continue
        if not isinstance(clave_node, yaml.ScalarNode):
            forma = "una lista" if isinstance(clave_node, yaml.SequenceNode) else "un mapping"
            loader.problemas.append(f"línea {linea}: una clave tiene que ser un texto, y aquí "
                                    f"es {forma}")
            loader.construct_object(valor_node, deep=deep)     # lo de debajo también se mira
            continue
        clave = loader.construct_object(clave_node, deep=deep)
        valor = loader.construct_object(valor_node, deep=deep)
        if clave in vistas:
            loader.problemas.append(f"línea {linea}: la clave {clave!r} está repetida (ya en la "
                                    f"línea {vistas[clave]}); YAML se quedaría solo con la última")
            continue
        vistas[clave] = linea
        resultado[clave] = valor
    return resultado


_CargadorFicha.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                               _mapping_sin_perdida)


def leer_yaml_ficha(path: Path) -> Any:
    """El `_ficha_crm.yaml` sin perder nada (spec §3 A.1). Lo usan `cargar_ficha_yaml` y
    `scripts/crm_colaboradores_firmas.py::apply`: con un solo lector, ninguno de los dos
    consolida una pérdida que el otro ya no podría ver."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe _ficha_crm.yaml: {path}")
    texto = path.read_text(encoding="utf-8")
    try:
        # PyYAML resuelve los alias en el composer, antes de que ningún constructor los vea:
        # donde siguen visibles es en los EVENTOS. Y dentro del `try`, porque el escaneo también
        # analiza y una sintaxis rota lo tumba con `ParserError` (R2/H-04).
        problemas = [f"línea {ev.start_mark.line + 1}: los alias (`&`/`*`) no se admiten en "
                     "_ficha_crm.yaml: escribe cada dato donde va"
                     for ev in yaml.parse(texto, Loader=yaml.SafeLoader)
                     if isinstance(ev, yaml.AliasEvent) or getattr(ev, "anchor", None)]
        cargador = _CargadorFicha(texto)
        try:
            data = cargador.get_single_data()
        finally:
            cargador.dispose()
    except yaml.YAMLError as exc:
        # El límite, declarado (spec §3 A.1): una sintaxis rota para el análisis, y es lo único
        # que se puede decir de ese fichero.
        raise ValueError(f"_ficha_crm.yaml inválido: {exc}") from exc
    problemas += cargador.problemas
    if problemas:
        raise ValueError("_ficha_crm.yaml no se puede leer sin perder datos:\n  - "
                         + "\n  - ".join(problemas))
    return {} if data is None else data
```

- [ ] **Step 4:** los tests del Step 1 → PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): lector sin perdida del _ficha_crm.yaml (R1/H-01; R2/H-04)`.

---

### Task 2: Claves y tipos, en un solo `ValueError` (spec §3 A.2, A.3, A.5)

**Files:** Modify `core/crm_ficha.py` (`validar_ficha`, constructores, `cargar_ficha_yaml`), `tests/_mutantes_p6.py` (M11); Test `tests/test_crm_ficha_lector.py`; migra `tests/test_crm_ficha_yaml_none.py`.

**Interfaces:**
- Produces `CLAVES_RAIZ`, `CLAVES_CONTRARIO`, `CLAVES_COLABORADOR` (tuplas, **sin `id_crm`**: entra en la Task 7 con su consumidor) y `validar_ficha(data: object) -> list[str]` (problemas con su ruta; vacía = válida).
- `cargar_ficha_yaml(path)` = `leer_yaml_ficha` → `validar_ficha` (si hay problemas, un `ValueError` con todos, uno por línea) → construir.
- Consumes `leer_yaml_ficha` (Task 1).

- [ ] **Step 1: tests que fallan**

```python
#: El inventario, fijado aquí y no leído de la tupla que lo implementa: si alguien quita una
#: clave de `CLAVES_*`, lo dice este test y no el silencio (R2, acta §5).
_INVENTARIO_CONTRARIO = ("nombre", "apellido1", "apellido2", "email", "movil", "nif",
                         "direccion", "poblacion", "cp", "provincia", "telefono")
_INVENTARIO_COLABORADOR = ("nombre", "email", "movil", "telefono", "nif")


def test_las_tuplas_son_el_inventario_del_spec():
    assert cf.CLAVES_RAIZ == ("contrario", "colaboradores", "notas_html", "cliente_propio",
                              "firmante")
    assert cf.CLAVES_CONTRARIO == _INVENTARIO_CONTRARIO
    assert cf.CLAVES_COLABORADOR == _INVENTARIO_COLABORADOR


def _parte(rol, clave, valor_yaml):
    """Una parte válida salvo `clave`, que lleva `valor_yaml` (texto YAML en flujo)."""
    base = {"contrario": {"nombre": "A", "nif": "'00000000T'"},
            "colaborador": {"nombre": "A", "email": "a@x.es"}}[rol]
    cuerpo = "{" + ", ".join(f"{k}: {v}" for k, v in {**base, clave: valor_yaml}.items()) + "}"
    return f"contrario: {cuerpo}\n" if rol == "contrario" else f"colaboradores:\n  - {cuerpo}\n"


def _linea(error, ruta):
    return next(l for l in str(error.value).splitlines() if f"{ruta}:" in l)


@pytest.mark.parametrize("texto, ruta, sugerencias", [
    ("contrario: {nombre: A, nif: '1', apellido: X}\n", "contrario.apellido",
     ["apellido1", "apellido2"]),
    ("contrario:\n  - {nombre: A, nif: '1', apellido: X}\n", "contrario[0].apellido",
     ["apellido1", "apellido2"]),
    ("colaboradores:\n  - {nombre: A, email: a@x.es, mail: b}\n", "colaboradores[0].mail",
     ["email"]),
    ("contrarios: {nombre: A, nif: '1'}\n", "contrarios", ["contrario"]),
])
def test_clave_desconocida_con_ruta_y_TODAS_las_sugerencias(tmp_path, texto, ruta, sugerencias):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    linea = _linea(e, ruta)
    assert "clave desconocida" in linea
    for s in sugerencias:
        assert repr(s) in linea


def test_sin_candidata_cercana_no_se_inventa_sugerencia(tmp_path):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A, nif: '1', zzzz: X}\n"))
    assert "¿querías" not in _linea(e, "contrario.zzzz")


def test_varios_problemas_salen_todos(tmp_path):
    texto = "contrario: {nombre: A, nif: '1', apellido: X, dni: Y}\nnotas: z\n"
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for trozo in ("contrario.apellido:", "contrario.dni:", "notas:"):
        assert trozo in str(e.value)


_ESCALARES = ([("contrario", f"contrario.{c}", c) for c in _INVENTARIO_CONTRARIO]
              + [("colaborador", f"colaboradores[0].{c}", c) for c in _INVENTARIO_COLABORADOR])


@pytest.mark.parametrize("rol, ruta, clave", _ESCALARES)
@pytest.mark.parametrize("valor", ["{x: y}", "[x]"])
def test_R1H02_un_mapping_o_una_lista_en_CUALQUIER_escalar_se_rechaza(tmp_path, rol, ruta,
                                                                      clave, valor):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, clave, valor)))
    assert f"{ruta}: tiene que ser un texto o null" in str(e.value)


@pytest.mark.parametrize("clave", ["notas_html", "firmante"])
@pytest.mark.parametrize("valor", ["{texto: importante}", "[x]"])
def test_R1H02_tambien_en_notas_y_firmante(tmp_path, clave, valor):
    with pytest.raises(ValueError, match=re.escape(f"{clave}: tiene que ser un texto o null")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, f"{clave}: {valor}\n"))


@pytest.mark.parametrize("rol, ruta", [("contrario", "contrario"),
                                       ("colaborador", "colaboradores[0]")])
def test_un_nombre_de_solo_espacios_se_rechaza(tmp_path, rol, ruta):
    with pytest.raises(ValueError, match=re.escape(f"{ruta}.nombre: falta o está vacío")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, "nombre", "'   '")))


@pytest.mark.parametrize("valor", ["false", "0", "[]", "{}", "NO_EXISTE"])
def test_cliente_propio_fuera_del_catalogo_se_rechaza(tmp_path, valor):
    with pytest.raises(ValueError, match="cliente_propio desconocido"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, f"cliente_propio: {valor}\n"))


@pytest.mark.parametrize("texto, ruta", [
    ("colaboradores: {nombre: A, email: a@x.es}\n", "colaboradores"),
    ("colaboradores:\n  - texto suelto\n", "colaboradores[0]"),
    ("contrario: [texto suelto]\n", "contrario[0]"),
])
def test_una_coleccion_con_otra_forma_se_rechaza(tmp_path, texto, ruta):
    with pytest.raises(ValueError, match=re.escape(f"{ruta}: tiene que ser")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))


@pytest.mark.parametrize("texto", ["false\n", "0\n", "[]\n", "texto\n"])
def test_una_raiz_que_no_es_mapping_se_rechaza(tmp_path, texto):
    with pytest.raises(ValueError, match="raíz"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))


def test_R2H02_una_provincia_que_no_existe_se_rechaza_al_validar(tmp_path):
    with pytest.raises(ValueError, match=re.escape("contrario.provincia:")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte("contrario", "provincia", "Atlantida")))


def test_una_provincia_con_otra_caja_vale(tmp_path):                  # control positivo
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, _parte("contrario", "provincia", "barcelona")))
    assert f.contrarios[0].provincia == "barcelona"


@pytest.mark.parametrize("rol, ruta", [("contrario", "contrario"),
                                       ("colaborador", "colaboradores[0]")])
@pytest.mark.parametrize("clave, valor", [("movil", "'+34'"), ("telefono", "'0034'")])
def test_R2H02_un_telefono_que_se_queda_vacio_se_rechaza(tmp_path, rol, ruta, clave, valor):
    with pytest.raises(ValueError, match=re.escape(f"{ruta}.{clave}:")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, clave, valor)))


@pytest.mark.parametrize("rol", ["contrario", "colaborador"])
def test_un_telefono_legitimo_vale(tmp_path, rol):                     # control positivo
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, "movil", "'+34 600 111 222'")))
    parte = f.contrarios[0] if rol == "contrario" else f.colaboradores[0]
    assert parte.movil == "600111222"


def test_null_y_ausente_son_no_hay_dato(tmp_path):                    # controles positivos
    f = cf.cargar_ficha_yaml(_yaml(tmp_path,
        "contrario: {nombre: A, nif: '1', apellido2: null}\ncolaboradores: null\n"))
    assert f.contrarios[0].apellido2 == "" and f.colaboradores == []
    assert f.cliente_propio == cf.CLIENTE_PROPIO_DEFAULT
    assert (cf.cargar_ficha_yaml(_yaml(tmp_path, "cliente_propio: null\n")).cliente_propio
            == cf.CLIENTE_PROPIO_DEFAULT)


def test_cargar_ficha_yaml_lee_con_el_lector_sin_perdida(tmp_path):
    """El consumidor 1 del lector (el 2 es `apply`, Task 4)."""
    with pytest.raises(ValueError, match="repetida"):
        cf.cargar_ficha_yaml(_yaml(tmp_path,
            "contrario: {nombre: UNO, nif: '1'}\ncontrario: {nombre: DOS, nif: '2'}\n"))


def test_cada_clave_llega_a_su_atributo(tmp_path):
    """Centinela distinto por campo: mata el cruce de asignaciones, no solo la tupla."""
    valores = {c: f"V_{c}" for c in _INVENTARIO_CONTRARIO}
    valores["provincia"] = "Zaragoza"          # la validación exige una provincia real
    texto = "contrario:\n" + "".join(f"  {c}: '{v}'\n" for c, v in valores.items())
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for c, v in valores.items():
        assert getattr(f.contrarios[0], c) == v, c
    valores_col = {c: f"W_{c}" for c in _INVENTARIO_COLABORADOR}
    texto = ("colaboradores:\n  - " + "\n    ".join(f"{c}: '{v}'" for c, v in valores_col.items())
             + "\n")
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for c, v in valores_col.items():
        assert getattr(f.colaboradores[0], c) == v, c
```

  (Los contrarios de estos tests llevan `nif` y los colaboradores `email` porque la Task 3 exigirá identidad: se ponen ya para que estos tests no cambien después. `V_movil` y `W_telefono` sobreviven a `normalize_es_phone`, que solo quita `[\s.\-/()]` y el prefijo: medido.)
- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación.**

```python
CLAVES_RAIZ = ("contrario", "colaboradores", "notas_html", "cliente_propio", "firmante")
CLAVES_CONTRARIO = ("nombre", "apellido1", "apellido2", "email", "movil", "nif",
                    "direccion", "poblacion", "cp", "provincia", "telefono")
CLAVES_COLABORADOR = ("nombre", "email", "movil", "telefono", "nif")

_TELEFONOS = ("movil", "telefono")


def _forma(valor: object) -> str:
    if isinstance(valor, dict):
        return "un mapping"
    if isinstance(valor, list):
        return "una lista"
    return type(valor).__name__


def _hay(valor: object) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _sugerencia(clave: object, validas: tuple[str, ...]) -> str:
    """TODAS las válidas cercanas, en el orden de la tupla (R2/H-07): `apellido` casa igual con
    `apellido1` que con `apellido2`, y elegir una sería adivinar. No es un alias de entrada."""
    cerca = set(difflib.get_close_matches(str(clave), validas, n=len(validas), cutoff=0.6))
    elegidas = [repr(v) for v in validas if v in cerca]
    return f"; ¿querías {' o '.join(elegidas)}?" if elegidas else ""


def _problemas_escalar(valor: object, ruta: str) -> list[str]:
    if valor is None or isinstance(valor, str):
        return []
    if isinstance(valor, (bool, int, float)):
        return [f"{ruta}: vino del YAML como {type(valor).__name__} ({valor!r}). Un valor con "
                "ceros a la izquierda lo reinterpreta YAML (`01001` es el octal 513) y el dato "
                "original ya no se puede recuperar. Escríbelo entre comillas: `cp: '01001'`"]
    return [f"{ruta}: tiene que ser un texto o null, y es {_forma(valor)}"]


def _problemas_parte(d: dict, ruta: str, validas: tuple[str, ...]) -> list[str]:
    p = [f"{ruta}.{k}: clave desconocida{_sugerencia(k, validas)}" for k in d if k not in validas]
    p += [x for k in validas if k in d for x in _problemas_escalar(d[k], f"{ruta}.{k}")]
    nombre = d.get("nombre")
    if nombre is None or (isinstance(nombre, str) and not nombre.strip()):
        p.append(f"{ruta}.nombre: falta o está vacío")     # ausente, null o solo espacios
    # Lo que no puede llegar NUNCA es de la declaración, no de la ficha (spec §3 A.3, R2/H-02).
    for k in _TELEFONOS:
        v = d.get(k)
        if _hay(v) and not normalize_es_phone(v.strip()):
            p.append(f"{ruta}.{k}: {v!r} se queda vacío al normalizarlo, y la parte se "
                     "escribiría sin él")
    v = d.get("provincia")
    if "provincia" in validas and _hay(v) and provincia_canonica(v) is None:
        p.append(f"{ruta}.provincia: {v!r} no es ninguna provincia del CRM y el Select la "
                 "descartaría: el dato no puede llegar nunca")
    return p


def validar_ficha(data: object) -> list[str]:
    """Todos los problemas de forma, claves y tipos, con su ruta (spec §3 A.2-A.5)."""
    if not isinstance(data, dict):
        return [f"la raíz del _ficha_crm.yaml tiene que ser un mapping, y es {_forma(data)}"]
    p = [f"{k}: clave desconocida{_sugerencia(k, CLAVES_RAIZ)}" for k in data
         if k not in CLAVES_RAIZ]
    for k in ("notas_html", "firmante"):
        p += _problemas_escalar(data.get(k), k)
    cp = data.get("cliente_propio")
    if cp is not None and not (isinstance(cp, str) and cp.strip() in CLIENTES_PROPIOS_EV):
        p.append(f"cliente_propio desconocido: {cp!r} (tiene que ser uno de "
                 f"{sorted(CLIENTES_PROPIOS_EV)}; ver core.config.CLIENTES_PROPIOS_EV)")
    contr = data.get("contrario")
    if isinstance(contr, dict):
        p += _problemas_parte(contr, "contrario", CLAVES_CONTRARIO)
    elif isinstance(contr, list):
        for i, e in enumerate(contr):
            p += (_problemas_parte(e, f"contrario[{i}]", CLAVES_CONTRARIO) if isinstance(e, dict)
                  else [f"contrario[{i}]: tiene que ser un mapping, y es {_forma(e)}"])
    elif contr is not None:
        p.append("contrario: tiene que ser un mapping o una lista de mappings, y es "
                 f"{_forma(contr)}")
    cols = data.get("colaboradores")
    if isinstance(cols, list):
        for i, e in enumerate(cols):
            p += (_problemas_parte(e, f"colaboradores[{i}]", CLAVES_COLABORADOR)
                  if isinstance(e, dict)
                  else [f"colaboradores[{i}]: tiene que ser un mapping, y es {_forma(e)}"])
    elif cols is not None:
        p.append(f"colaboradores: tiene que ser una lista de mappings, y es {_forma(cols)}")
    return p


def _valor(v: object) -> str:
    """Un escalar YA VALIDADO, como texto. `null` es «no hay dato» (H-09): nunca "None"."""
    return "" if v is None else str(v).strip()


def _contrarios_de(raw) -> list[NuevoClienteContrario]:
    """`contrario:` ya validado: ausente/`null`, mapping o lista, en el orden del fichero."""
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [_contrario_de(raw)]
    return [_contrario_de(e) for e in raw]


def _contrario_de(d: dict) -> NuevoClienteContrario:
    return NuevoClienteContrario(**{c: _valor(d.get(c)) for c in CLAVES_CONTRARIO})


def _colaborador_de(d: dict) -> NuevoColaborador:
    return NuevoColaborador(**{c: _valor(d.get(c)) for c in CLAVES_COLABORADOR})


def cargar_ficha_yaml(path: Path) -> FichaCRMInput:
    data = leer_yaml_ficha(path)
    problemas = validar_ficha(data)
    if problemas:
        raise ValueError("_ficha_crm.yaml no se puede usar:\n  - " + "\n  - ".join(problemas))
    cp = data.get("cliente_propio")
    return FichaCRMInput(
        contrarios=_contrarios_de(data.get("contrario")),
        colaboradores=[_colaborador_de(c) for c in data.get("colaboradores") or []],
        notas_html=_valor(data.get("notas_html")),
        cliente_propio=CLIENTE_PROPIO_DEFAULT if cp is None else _valor(cp),
        firmante=_valor(data.get("firmante")),
    )
```

  Importes nuevos del módulo: `difflib`, `typing.Any`, `core.config.CLIENTES_PROPIOS_EV` (las claves del catálogo, sin copiar la lista), `core.sudespacho_relations.provincia_canonica` y `core.utils.normalize_es_phone`. **Sale `_escalar`**: su rechazo de números vive ahora en `_problemas_escalar`, con el mismo texto de las comillas que exigen `test_un_movil_sin_comillas…` y `test_un_cp_sin_comillas…`. Y sale el filtro que `cargar_ficha_yaml` aplicaba a `colaboradores` (`if isinstance(c, dict)`): un elemento que no es un mapping lo rechaza la validación con su índice, y el filtro era un segundo camino por donde una parte desaparecía en silencio.

  **`tests/_mutantes_p6.py`, M11.** Su ancla —la comprobación de elementos de `_contrarios_de`— desaparece, porque esa propiedad vive ahora en `validar_ficha` y dejarla también en el constructor sería código muerto (con la validación delante nunca se alcanza) y haría **sobrevivir** a todo mutante de cualquiera de las dos. M11 pasa a mutar la rama de `validar_ficha` —`else [f"contrario[{i}]: tiene que ser un mapping, y es {_forma(e)}"])` → `else [])`— contra el mismo test (`test_un_elemento_invalido_aborta_con_su_indice`), y su nombre dice lo que ahora hace: «un elemento inválido deja de abortar con su índice». M12 (`return [_contrario_de(e) for e in raw]`) conserva su ancla.

  **Migración (1 test), en el commit:** `tests/test_crm_ficha_yaml_none.py::TestClientePropioConPorDefecto::test_cliente_propio_con_valor_se_respeta` declaraba `OTRO_CLIENTE`, que ya no es declarable; pasa a `ENGEL_VOLKERS_SPAIN`, la clave real no predeterminada del catálogo. La propiedad —«lo declarado se respeta y no cae al defecto»— es la misma.
- [ ] **Step 4:** nuevos + `python -m pytest tests -k "crm_ficha or colaboradores_firmas" -p no:randomly -q` → PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): claves y tipos por campo, todos los problemas en un error (MEJORAS #283; R1/H-02; R2/H-02, H-07)`, enumerando la migración y el re-apuntado de M11.

---

### Task 3: Identidad por NIF o email, todavía sin `id_crm` (spec §3 A.4)

**Files:** Modify `core/crm_ficha.py`; Test `tests/test_crm_ficha_lector.py`; migra seis ficheros de test (abajo).

**Interfaces:** Produces `SIN_IDENTIDAD = "sin identidad estable"` (constante de módulo que los tests importan: el mensaje puede crecer en la Task 7 sin vaciar un negativo). `validar_ficha` añade `f"{ruta}: {SIN_IDENTIDAD} —falta NIF o email—: …"` a toda parte sin `nif` ni `email` no vacíos.

- [ ] **Step 1: tests que fallan**

```python
@pytest.mark.parametrize("texto, ruta", [
    ("contrario: {nombre: A}\n", "contrario"),
    ("contrario:\n  - {nombre: A, nif: '1'}\n  - {nombre: B}\n", "contrario[1]"),
    ("colaboradores:\n  - {nombre: A}\n", "colaboradores[0]"),
    ("colaboradores:\n  - {nombre: A, nif: '  ', email: ''}\n", "colaboradores[0]"),
])
def test_R1H04_una_parte_sin_identidad_estable_se_rechaza(tmp_path, texto, ruta):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    assert f"{ruta}: {cf.SIN_IDENTIDAD}" in str(e.value)


@pytest.mark.parametrize("identidad", ["nif: '00000000T'", "email: a@x.es"])
def test_basta_el_nif_o_el_email(tmp_path, identidad):                # control positivo
    assert cf.cargar_ficha_yaml(_yaml(tmp_path,
                                      f"contrario: {{nombre: A, {identidad}}}\n")).contrarios


def test_R2H06_id_crm_todavia_NO_es_una_clave(tmp_path):
    """El estado intermedio seguro: hasta la Task 7, que trae su consumidor, `id_crm` es una
    clave desconocida y la parte sigue sin identidad. Aceptarlo antes la mandaría a CREAR."""
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A, id_crm: '1128'}\n"))
    assert "contrario.id_crm: clave desconocida" in str(e.value)
    assert f"contrario: {cf.SIN_IDENTIDAD}" in str(e.value)
```

- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación**, al final de `_problemas_parte`:

```python
SIN_IDENTIDAD = "sin identidad estable"
_IDENTIDAD = ("nif", "email")
...
    if not any(_hay(d.get(k)) for k in _IDENTIDAD):
        p.append(f"{ruta}: {SIN_IDENTIDAD} —falta NIF o email—: cada corrida crearía otra "
                 "ficha y la anterior quedaría como sobrante (spec §3 A.4)")
```

  **Migración, escrita aquí y enumerada en el commit.** Los 22 tests que la sonda midió rotos, más cuatro de precisión (marcados †: su `raises` seguiría verde, pero ya no solo por su propiedad). Toda identidad es sintética (`'00000000T'`, `…@engelvoelkers.example`), y **ningún aserto cambia**:

  | Fichero | Test | Migración |
  |---|---|---|
  | `test_crm_ficha_yaml_none.py` | `TestNingunCampoDelColaboradorPuedeValerNone::test_una_clave_vacia_es_cadena_vacia[email, movil, telefono, nif]` | identidad por la OTRA clave: `nif` si la vacía es `email`; `email` en las demás |
  | 〃 | `…::test_todas_vacias_a_la_vez` | **en dos pasos, y se dice:** aquí, dos casos —identidad por `email` con `movil`, `telefono` y `nif` vacíos; por `nif` con `email`, `movil` y `telefono` vacíos—, de modo que cada campo sale vacío en al menos uno; la Task 7 lo **devuelve** a los cuatro a la vez con `id_crm` |
  | 〃 | `…::test_un_movil_sin_comillas_se_RECHAZA_en_vez_de_corromperse` † | `email` |
  | 〃 | `TestElMovilDelContrarioTampoco::test_movil_vacio_es_cadena_vacia` | `nif` |
  | 〃 | `…::test_las_otras_claves_de_texto_tampoco[email, direccion, poblacion]` | `nif` |
  | 〃 | `…::test_NINGUN_campo_de_texto_del_contrario_puede_valer_None` | **en dos pasos:** aquí, dos casos —identidad por `nif` con las otras nueve vacías, `email` incluido; por `email` con las otras nueve vacías, `nif` incluido—; la Task 7 lo devuelve a las diez a la vez con `id_crm` |
  | 〃 | `TestNotasHtmlSinNoneLiteral::test_notas_html_ausente_es_cadena_vacia` | `nif` |
  | 〃 | `TestClientePropioConPorDefecto::test_cliente_propio_ausente_toma_default` | `nif` |
  | `test_crm_ficha_n_contrarios.py` | `test_un_mapping_suelto_sigue_valiendo` | `nif` |
  | 〃 | `test_el_orden_del_fichero_se_conserva` | un `nif` distinto por parte |
  | 〃 | `test_un_elemento_invalido_aborta_con_su_indice` † | `nif` en el primero |
  | 〃 | `test_se_valida_la_coleccion_ENTERA_antes_de_construir_nada` † | `nif` en el primero **y un espía** sobre `core.crm_ficha.NuevoClienteContrario` que exige cero construcciones: sin él, su `raises` pasaría aunque se ignorase el segundo (§9) |
  | `test_crm_ficha_validacion.py` | `TestQueDatosSeValidan::test_los_campos_vacios_no_se_validan` | `email` (el `nif: ''` es su propiedad) |
  | 〃 | `TestUnDatoDeUnaPalabraNoAcredita::test_los_apellidos_sueltos_SI_se_validan_pero_no_acreditan` | `nif` |
  | `test_crm_ficha_validacion_r1.py` | `TestElYAMLNoPuedeCorromperUnDato::_carga` (el ayudante: arregla `test_el_cp_entre_comillas_sobrevive` y `test_una_clave_vacia_es_AUSENCIA_no_la_cadena_None[cp:, telefono:, provincia:]`, y precisa † `test_un_cp_sin_comillas_se_RECHAZA_en_vez_de_corromperse`) | `nif` |
  | `test_crm_ficha_cli.py` | `test_el_plan_del_cli_enumera_los_dos_contrarios` | un `nif` por parte |
  | `test_crm_colaboradores_firmas_cli.py` | `TestApplyRellenaSoloElHueco::test_el_YAML_resultante_lo_puede_leer_cargar_ficha_yaml` | `nif` en el contrario |

- [ ] **Step 4:** PASAN; `python -m pytest tests -k "crm_ficha or colaboradores_firmas" -p no:randomly -q`.
- [ ] **Step 5:** commit `feat(crm_ficha): toda parte lleva NIF o email (R1/H-04; id_crm llega con su consumidor, R2/H-06)`, con la tabla de migración en el cuerpo.

---

### Task 4: `crm_colaboradores_firmas.apply` lee sin pérdida (spec §3 A.1)

**Files:** Modify `scripts/crm_colaboradores_firmas.py` (el `yaml.safe_load` de `apply` y los comentarios que citan `_escalar`); Test `tests/test_crm_colaboradores_firmas_cli.py`.

- [ ] **Step 1: test que falla**

```python
class TestApplyNoReescribeUnaFichaQuePerderiaDatos:
    """R1/H-01 del diseño de crm_ficha: `apply` leía con `safe_load` y reescribía el fichero
    entero, así que una clave repetida se CONSOLIDABA —la parte perdida desaparecía también
    del disco— y `crm_ficha` ya no podía verla."""

    @pytest.mark.parametrize("texto, linea", [
        ("colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n"
         "    email: otra@engelvoelkers.com\n", 4),
        ("colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n"
         "colaboradores:\n  - nombre: BEA\n    email: bea@engelvoelkers.com\n", 4),
    ])
    def test_una_clave_repetida_falla_sin_tocar_el_fichero(self, caso, texto, linea):
        _ficha(caso).write_text(texto, encoding="utf-8")
        antes = hashlib.sha256(_ficha(caso).read_bytes()).hexdigest()
        r = _aplica(["--confirmar"])
        assert r.exit_code == 1, r.output
        assert f"línea {linea}" in r.output
        assert hashlib.sha256(_ficha(caso).read_bytes()).hexdigest() == antes
```

- [ ] **Step 2:** FALLA (hoy `safe_load` colapsa y reescribe).
- [ ] **Step 3:** en `apply`, `datos = yaml.safe_load(...) or {}` pasa a

```python
    try:
        datos = leer_yaml_ficha(ficha_path)
    except ValueError as exc:
        typer.echo(f"[ERROR] {exc}\nNo se toca el fichero: reescribirlo consolidaría lo que "
                   "se ha perdido.", err=True)
        raise typer.Exit(code=1)
```

  con `from core.crm_ficha import leer_yaml_ficha`; el `if not isinstance(datos, dict)` de debajo se queda (una raíz lista sigue siendo error). Los comentarios del volcado que decían que `core.crm_ficha._escalar` rechaza el octal pasan a nombrar `validar_ficha`, que es quien lo hace ahora; y la docstring de `test_los_telefonos_se_escriben_ENTRE_COMILLAS`, igual.
- [ ] **Step 4:** PASA, y los tests existentes del script siguen verdes.
- [ ] **Step 5:** commit `fix(crm_colaboradores_firmas): apply lee con el lector sin perdida y no reescribe una ficha que perderia datos`.

---

### Task 5: Vínculos por igualdad y datos declarados, puros (spec §4 B.1, B.2)

**Files:** Modify `core/crm_ficha.py`; Create `tests/test_crm_ficha_auditoria.py`.

**Interfaces:**
- `auditar_relaciones(esperado: Mapping[str, Sequence[str]], leido: Mapping[str, Sequence[Mapping]]) -> AuditoriaRelaciones`, con `ok`, `faltan` y `sobran` (listas de `str`: `"colaboradores id=624"`; `faltan` lleva `"(la corrida escribió N, la lectura ve M)"`; `ok`, `"(xN)"` si N > 1). Solo `BLOQUES_AUDITADOS = ("clientes_propios", "clientes_contrarios", "colaboradores")`, en ese orden y con los ids ordenados.
- `auditar_datos(elemento: str, id_: str, declarado: Mapping, ficha_crm: Mapping) -> list[Discrepancia]`. `declarado` es **la declaración** (el mapping validado de la parte), no el DTO. `Discrepancia(elemento, id, campo, propiedad, tipo, crm, yaml)`, con `tipo` `"vacio"` o `"distinto"` para que la fase previa (Task 7) filtre, y `str()` = `"clientes_contrarios id=1128 1apellido: vacío en el CRM"` o `"… distinto (CRM 'X', YAML 'Y')"`.
- `CAMPOS_CONTRARIO_CRM` / `CAMPOS_COLABORADOR_CRM`: tuplas `(campo_yaml, propiedad_crm, clase)`.

- [ ] **Step 1: tests que fallan**

```python
# tests/test_crm_ficha_auditoria.py
"""La verificación compara vínculos y datos por IGUALDAD (spec §4, Parte B)."""
import pytest

from core import crm_ficha as cf


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
    assert a.sobran == ["clientes_propios id=27", "clientes_contrarios id=9",
                        "colaboradores id=8"]


def test_multiplicidad_en_los_dos_sentidos_y_id_int_frente_a_str():
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": ["5", "5"],
                               "colaboradores": ["7"]},
                              {"clientes_propios": [{"id": 2}], "clientes_contrarios": [{"id": 5}],
                               "colaboradores": [{"id": "7"}, {"id": "7"}]})
    assert a.faltan == ["clientes_contrarios id=5 (la corrida escribió 2, la lectura ve 1)"]
    assert a.sobran == ["colaboradores id=7"]


def test_faltan_y_sobran_a_la_vez():
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": ["5"],
                               "colaboradores": []},
                              _rel(clientes_propios=["2"], clientes_contrarios=["6"]))
    assert a.faltan == ["clientes_contrarios id=5 (la corrida escribió 1, la lectura ve 0)"]
    assert a.sobran == ["clientes_contrarios id=6"]


def test_exacto_es_todo_ok_y_los_bloques_ajenos_no_se_miran():     # control positivo
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": ["5", "5"],
                               "colaboradores": []},
                              _rel(clientes_propios=["2"], clientes_contrarios=["5", "5"],
                                   actuaciones=["21496"]))
    assert a.ok == ["clientes_propios id=2", "clientes_contrarios id=5 (x2)"]
    assert a.faltan == [] and a.sobran == []


def test_R1H03_la_ficha_de_w030a13_con_el_apellido_vacio_no_pasa():
    decl = {"nombre": "ANA", "apellido1": "GARCIA", "nif": "00000000T"}
    [d] = cf.auditar_datos("clientes_contrarios", "1128", decl,
                           {"nombre": "ANA", "1apellido": "", "nif_cif": "00000000T"})
    assert (d.propiedad, d.tipo) == ("1apellido", "vacio")
    assert str(d) == "clientes_contrarios id=1128 1apellido: vacío en el CRM"


def test_mayusculas_espacios_y_formato_no_son_diferencia_y_lo_distinto_se_dice():
    decl = {"nombre": "Ana", "apellido1": "García", "nif": "00.000.000-t", "email": "Ana@X.es",
            "movil": "+34 600 111 222", "direccion": "CALLE  MAYOR 1"}
    ficha = {"nombre": "ANA ", "1apellido": "GARCÍA", "nif_cif": "00000000T",
             "email": "ana@x.es", "movil": "600111222", "direccion": "calle mayor 1"}
    assert cf.auditar_datos("clientes_contrarios", "1", decl, ficha) == []
    ficha["1apellido"] = "PEREZ"
    [d] = cf.auditar_datos("clientes_contrarios", "1", decl, ficha)
    assert str(d) == "clientes_contrarios id=1 1apellido: distinto (CRM 'PEREZ', YAML 'García')"


#: (campo del YAML, propiedad del CRM, un valor, otro valor) — fijado aquí, fuera de la tupla
#: que lo implementa, para que un cruce en `CAMPOS_*_CRM` no se pruebe contra sí mismo.
_MAPA_CONTRARIO = [
    ("nombre", "nombre", "ANA", "LUISA"), ("apellido1", "1apellido", "GARCIA", "PEREZ"),
    ("apellido2", "2apellido", "RUIZ", "SOLER"), ("email", "email", "a@x.es", "b@x.es"),
    ("movil", "movil", "600111222", "699999999"), ("nif", "nif_cif", "00000000T", "11111111H"),
    ("direccion", "direccion", "CALLE UNO 1", "CALLE DOS 2"),
    ("poblacion", "poblacion", "BADALONA", "GIRONA"), ("cp", "cp", "08019", "08028"),
    ("provincia", "provincia", "Barcelona", "Madrid"),
    ("telefono", "telefono1", "931112233", "932223344"),
]
_MAPA_COLABORADOR = [
    ("nombre", "nombre", "ANA CONSULTORA", "BEA ASESORA"), ("email", "email", "a@x.es", "b@x.es"),
    ("movil", "movil", "600111222", "699999999"), ("telefono", "telefono1", "931112233", "932223344"),
    ("nif", "nif_cif", "00000000T", "11111111H"),
]
_MATRIZ = ([("clientes_contrarios", *f) for f in _MAPA_CONTRARIO]
           + [("colaboradores", *f) for f in _MAPA_COLABORADOR])


def test_cada_campo_va_a_su_propiedad_del_CRM():
    assert [(c, p) for c, p, _ in cf.CAMPOS_CONTRARIO_CRM] == [(c, p) for c, p, *_ in _MAPA_CONTRARIO]
    assert ([(c, p) for c, p, _ in cf.CAMPOS_COLABORADOR_CRM]
            == [(c, p) for c, p, *_ in _MAPA_COLABORADOR])


@pytest.mark.parametrize("elemento, campo, prop, valor, otro", _MATRIZ)
def test_la_matriz_campo_por_rol(elemento, campo, prop, valor, otro):
    decl = {campo: valor}
    assert cf.auditar_datos(elemento, "9", decl, {prop: valor}) == []          # igual
    [v] = cf.auditar_datos(elemento, "9", decl, {prop: ""})                     # vacío
    [a] = cf.auditar_datos(elemento, "9", decl, {})                             # ausente = vacío
    [d] = cf.auditar_datos(elemento, "9", decl, {prop: otro})                   # distinto
    assert (v.tipo, a.tipo, d.tipo) == ("vacio", "vacio", "distinto")
    assert v.propiedad == a.propiedad == d.propiedad == prop


def test_lo_que_el_yaml_no_declara_no_se_compara():                     # control positivo
    assert cf.auditar_datos("colaboradores", "7", {"nombre": "ANA", "email": "ana@x.es",
                                                   "movil": None},
                            {"nombre": "ANA", "email": "ana@x.es", "movil": "699"}) == []


@pytest.mark.parametrize("en_el_crm, esperado", [
    ("Barcelona", []), ("", ["vacio"]), ("1", ["vacio"]), ("Sin Asignar", ["vacio"]),
    ("Madrid", ["distinto"]),
])
def test_R2H03_la_provincia_se_compara_igual_en_los_dos_lados(en_el_crm, esperado):
    """`provincia_canonica('barcelona')` es `'Barcelona'`; normalizar solo un lado no casaba
    NUNCA. Y el `1` del enum es «Sin Asignar» (atlas): el vacío del Select, no una provincia."""
    got = cf.auditar_datos("clientes_contrarios", "1", {"provincia": "barcelona"},
                           {"provincia": en_el_crm})
    assert [d.tipo for d in got] == esperado
```

- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación.**

```python
@dataclass(frozen=True)
class AuditoriaRelaciones:
    ok: list[str]
    faltan: list[str]
    sobran: list[str]


BLOQUES_AUDITADOS = ("clientes_propios", "clientes_contrarios", "colaboradores")


def _orden_id(id_: str) -> tuple:
    return (0, int(id_)) if id_.isdigit() else (1, id_)


def auditar_relaciones(esperado: Mapping[str, Sequence[str]],
                       leido: Mapping[str, Sequence[Mapping]]) -> AuditoriaRelaciones:
    """Lo escrito contra lo leído, por IGUALDAD y con multiplicidad (spec §4 B.1).

    Por `Counter` y no por conjuntos: dos declaraciones que colapsan a un id con un solo
    vínculo son una `falta`, y un conjunto las daría por buenas (R1/H-02 del PR #275)."""
    ok: list[str] = []
    faltan: list[str] = []
    sobran: list[str] = []
    for bloque in BLOQUES_AUDITADOS:
        pedidos = Counter(str(i) for i in esperado.get(bloque, ()))
        vistos = Counter(str(v.get("id")) for v in leido.get(bloque, ()) or ())
        for id_ in sorted(set(pedidos) | set(vistos), key=_orden_id):
            p, v = pedidos[id_], vistos[id_]
            if p and v >= p:
                ok.append(f"{bloque} id={id_}" + (f" (x{p})" if p > 1 else ""))
            elif p:
                faltan.append(f"{bloque} id={id_} (la corrida escribió {p}, la lectura ve {v})")
            sobran += [f"{bloque} id={id_}"] * max(0, v - p)
    return AuditoriaRelaciones(ok=ok, faltan=faltan, sobran=sobran)


@dataclass(frozen=True)
class Discrepancia:
    elemento: str
    id: str
    campo: str          # la clave del YAML
    propiedad: str      # la del CRM
    tipo: str           # "vacio" | "distinto"
    crm: str
    yaml: str

    def __str__(self) -> str:
        base = f"{self.elemento} id={self.id} {self.propiedad}"
        if self.tipo == "vacio":
            return f"{base}: vacío en el CRM"
        return f"{base}: distinto (CRM {self.crm!r}, YAML {self.yaml!r})"


def _n_texto(v: object) -> str:
    return "" if v is None else " ".join(str(v).split()).casefold()


def _n_nif(v: object) -> str:
    return _canonizar_documento("" if v is None else str(v))


def _n_email(v: object) -> str:
    return "" if v is None else str(v).strip().lower()


def _n_tel(v: object) -> str:
    return normalize_es_phone("" if v is None else str(v).strip())


def _n_cp(v: object) -> str:
    return "" if v is None else str(v).strip()


#: El «Sin Asignar» del Select (atlas, enum `provincia`: `1=Sin Asignar`) es el VACÍO del
#: campo, no una provincia: tratarlo como un valor daría «distinto» ante una ficha sin dato.
_PROVINCIA_SIN_ASIGNAR = frozenset({"1", "sin asignar"})


def _n_provincia_crm(v: object) -> str:
    t = _n_texto(v)
    return "" if t in _PROVINCIA_SIN_ASIGNAR else t


def _n_provincia_yaml(v: object) -> str:
    # La MISMA normalización de texto en los dos lados, después de canonizar el del YAML
    # (R2/H-03). La que no se reconoce ya la ha rechazado `validar_ficha`.
    return _n_texto(provincia_canonica(str(v)) or v)


_NORMALIZA = {"texto": (_n_texto, _n_texto), "nif": (_n_nif, _n_nif),
              "email": (_n_email, _n_email), "tel": (_n_tel, _n_tel), "cp": (_n_cp, _n_cp),
              "provincia": (_n_provincia_yaml, _n_provincia_crm)}

#: (campo del YAML, propiedad del CRM, clase). Anclado a la fuente, no supuesto: el payload
#: de `_rest_post_cliente_contrario` / `_rest_post_colaborador`, los GET de
#: `get_cliente_contrario` / `get_colaborador` (`_PROPS_COLABORADOR`), el atlas
#: (`### clientes_contrarios`) e INTEGRACION §10.6.
CAMPOS_CONTRARIO_CRM = (
    ("nombre", "nombre", "texto"), ("apellido1", "1apellido", "texto"),
    ("apellido2", "2apellido", "texto"), ("email", "email", "email"),
    ("movil", "movil", "tel"), ("nif", "nif_cif", "nif"),
    ("direccion", "direccion", "texto"), ("poblacion", "poblacion", "texto"),
    ("cp", "cp", "cp"), ("provincia", "provincia", "provincia"),
    ("telefono", "telefono1", "tel"),
)
CAMPOS_COLABORADOR_CRM = (
    ("nombre", "nombre", "texto"), ("email", "email", "email"),
    ("movil", "movil", "tel"), ("telefono", "telefono1", "tel"), ("nif", "nif_cif", "nif"),
)
_CAMPOS_DE = {"clientes_contrarios": CAMPOS_CONTRARIO_CRM,
              "colaboradores": CAMPOS_COLABORADOR_CRM}


def auditar_datos(elemento: str, id_: str, declarado: Mapping,
                  ficha_crm: Mapping) -> list[Discrepancia]:
    """Cada campo que el YAML declara no vacío, contra el de la ficha del CRM (spec §4 B.2).

    Recibe la DECLARACIÓN, no el DTO: el DTO normaliza al construirse (`'+34'` se queda vacío)
    y la auditoría no vería lo que se perdió por el camino (R2/H-02)."""
    fuera: list[Discrepancia] = []
    for campo, propiedad, clase in _CAMPOS_DE[elemento]:
        bruto = declarado.get(campo)
        if bruto is None or not str(bruto).strip():
            continue                                   # lo que el YAML no declara no se compara
        del_yaml, del_crm = _NORMALIZA[clase]
        visto = del_crm(ficha_crm.get(propiedad))
        if del_yaml(bruto) == visto:
            continue
        fuera.append(Discrepancia(
            elemento=elemento, id=str(id_), campo=campo, propiedad=propiedad,
            tipo="vacio" if not visto else "distinto",
            crm=str(ficha_crm.get(propiedad) or "").strip(), yaml=str(bruto).strip()))
    return fuera
```

  Importes: `collections.Counter`, `typing.Mapping`/`Sequence`, `core.sudespacho_relations._canonizar_documento` (la forma canónica de un documento es una sola, la de la resolución de identidad).

  **Lo que se verifica en vivo y no aquí** (Task 10, antes de usarla en un caso real): la forma en que el GET devuelve `cp` y `provincia`. Todo el código del repo los trata como texto (`_completar_contrario_existente` les hace `.strip()`); si el CRM devolviera un número, la comparación fallaría **cerrada** (un «distinto»), no abierta.
- [ ] **Step 4:** PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): auditar vinculos por igualdad y datos declarados, puros (MEJORAS #288; R1/H-03; R2/H-02, H-03)`.

---

### Task 6: El CLI usa las auditorías (spec §4 B.2-B.4), todavía sin `id_crm` ni fase previa

**Files:** Modify `core/crm_ficha.py` (la declaración en `FichaCRMInput`), `scripts/crm_ficha.py`; Test `tests/test_crm_ficha_lector.py`, `tests/test_crm_ficha_cli.py`.

**Interfaces:**
- `FichaCRMInput.declarados_contrarios` / `.declarados_colaboradores`: `list[dict[str, str]]`, una por parte y en el mismo orden que los DTOs, con las claves **presentes** en el YAML y su valor validado sin normalizar (`_valor`).
- `scripts.crm_ficha.EXITO_VERIFICADA = "VERIFICADA: vínculos y datos de la ficha"` y `SIN_VERIFICAR = "SIN VERIFICAR"`: constantes que importan los tests.
- Importa en el CLI `get_cliente_contrario` y `get_colaborador`, para que los tests puedan doblarlos por su ruta.

- [ ] **Step 1: tests que fallan**

  En `tests/test_crm_ficha_lector.py`:

```python
def test_la_declaracion_se_conserva_sin_normalizar(tmp_path):
    """La auditoría compara la DECLARACIÓN (R2/H-02): el DTO normaliza, la declaración no."""
    f = cf.cargar_ficha_yaml(_yaml(tmp_path,
        "contrario: {nombre: ' A ', nif: '1', movil: '+34 600 111 222'}\n"
        "colaboradores:\n  - {nombre: B, email: b@x.es, telefono: '93 111 22 33'}\n"))
    assert f.contrarios[0].movil == "600111222"
    assert f.declarados_contrarios == [{"nombre": "A", "nif": "1", "movil": "+34 600 111 222"}]
    assert f.declarados_colaboradores == [{"nombre": "B", "email": "b@x.es",
                                           "telefono": "93 111 22 33"}]
```

  En `tests/test_crm_ficha_cli.py`, al principio, los ayudantes (el `import cli` de arriba ya da las constantes):

```python
class LecturaNoDeclarada(BaseException):
    """Un GET por id que el test no declaró. Fuera de `Exception` a propósito, como
    `FugaDeRedEnTest`: el CLI trata una lectura caída como «SIN VERIFICAR» con salida 0, y un
    `KeyError` del doble se colaría por ahí con el test en verde (R2/H-05)."""


def _declara_fichas(monkeypatch, contrarios=None, colaboradores=None):
    """Qué devuelve el CRM al LEER cada parte por id: la lectura final (spec §4 B.2) y, desde la
    Task 7, la fase previa. Es preparación del doble, no un aserto: cada test que llega a esas
    lecturas dice qué ficha hay detrás de cada id, y un id no declarado MATA el test."""
    for nombre, tabla in (("get_cliente_contrario", dict(contrarios or {})),
                          ("get_colaborador", dict(colaboradores or {}))):
        def _get(i, _t=tabla, _n=nombre):
            if str(i) not in _t:
                raise LecturaNoDeclarada(f"{_n}({i!r}) no está declarado en este test")
            return dict(_t[str(i)])
        monkeypatch.setattr(f"scripts.crm_ficha.{nombre}", _get)


#: Las fichas del CRM coherentes con la fixture `caso_con_ficha` (el móvil incluido: sin él, la
#: lectura añadiría una discrepancia que el test no pretende, R2 §3 de su acta).
_JUAN_1099 = {"nombre": "JUAN", "1apellido": "PEREZ", "nif_cif": "00000000T", "movil": "600111222"}
_ANA_776 = {"nombre": "ANA", "email": "ana@engelvoelkers.example"}
```

  Tests nuevos (sobre `caso_con_ficha`, con `link_ev_mmc`, `ensure_*`, `update_expediente` y `get_expediente` doblados como en `TestVerificacionPorLectura._escrituras_en_verde`):
  - **el 653:** `get_relaciones` devuelve un colaborador `624` de más → código 1, `[SOBRA] colaboradores id=624`, el `[ERROR]` de sobrantes («el _ficha_crm.yaml no declara», «crm_ficha no desvincula») y `cli.EXITO_VERIFICADA not in r.output`;
  - **FALTA y SOBRA a la vez:** el `776` no está y está el `624` → las dos líneas y código 1;
  - **W-030A13 relanzado:** `ensure_c` devuelve `("1128", False)` y la ficha 1128 trae `1apellido` vacío (y el móvil de la fixture) → `[DATO] clientes_contrarios id=1128 1apellido: vacío en el CRM`, el `[ERROR]` de datos («crm_ficha no pisa datos») y código 1;
  - **un colaborador con un dato que no llegó:** la ficha 776 vuelve con otro email → `[DATO] colaboradores id=776 email: distinto …` y código 1 (el rol colaborador también se audita);
  - **lectura de ficha fallida:** `get_cliente_contrario` lanza `RuntimeError` → salida 0, `f"{cli.SIN_VERIFICAR}: datos de clientes_contrarios id=1099"` y `cli.EXITO_VERIFICADA not in r.output`;
  - **un fallo conocido gana a un SIN VERIFICAR:** `[SOBRA]` y `get_colaborador` caído a la vez → código 1;
  - **parcial:** `ensure_col` lanza y `get_relaciones` devuelve un colaborador `999` desconocido → código 1, `"sobrantes: sin comprobar"` en la salida y **ningún** `[SOBRA]`;
  - **la guarda de fichas muerde:** `LecturaNoDeclarada` no hereda de `Exception`, y una corrida con una ficha sin declarar la levanta hasta el test (`pytest.raises(LecturaNoDeclarada)`, como `test_una_salida_no_declarada_MATA_el_test`).
- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación.**

  En `core/crm_ficha.py`:

```python
@dataclass
class FichaCRMInput:
    ...                                                    # los campos de siempre
    #: Lo que el YAML declara de cada parte, validado y SIN normalizar, en el orden de
    #: `contrarios` / `colaboradores`. Es lo que audita la lectura (spec §4 B.2): el DTO
    #: normaliza al construirse, y comparar el DTO no vería lo perdido por el camino (R2/H-02).
    declarados_contrarios: list[dict[str, str]] = field(default_factory=list)
    declarados_colaboradores: list[dict[str, str]] = field(default_factory=list)


def _declaracion(d: dict, claves: tuple[str, ...]) -> dict[str, str]:
    return {k: _valor(d[k]) for k in claves if k in d}
```

  y en `cargar_ficha_yaml`, con `raw = data.get("contrario")`, `lista = [] if raw is None else [raw] if isinstance(raw, dict) else raw` y `cols = data.get("colaboradores") or []`: `declarados_contrarios=[_declaracion(d, CLAVES_CONTRARIO) for d in lista]`, `declarados_colaboradores=[_declaracion(d, CLAVES_COLABORADOR) for d in cols]`.

  En `scripts/crm_ficha.py`:

```python
#: El literal de éxito, UNA vez: los tests lo importan —los positivos y los negativos—, así
#: que cambiar el texto no puede vaciar un negativo en silencio (R2, §9, frontera 3).
EXITO_VERIFICADA = "VERIFICADA: vínculos y datos de la ficha"
SIN_VERIFICAR = "SIN VERIFICAR"
```

  - Sustituir el cierre `_auditar` por un `_vinculos(rel, *, parcial=False) -> tuple[list[str], list[str]]` que imprime `[ok]`, `[FALTA]` y —si no es parcial— `[SOBRA]` desde `auditar_relaciones(esperado, rel)`, y devuelve `(faltan, sobran)`. En la **parcial** imprime, en lugar de los sobrantes, `"  sobrantes: sin comprobar — las partes que no llegaron a resolverse no tienen id, y sus vínculos de otra corrida saldrían como sobrantes sin serlo"` y devuelve `sobran == []`.
  - En el bucle de escrituras, cada parte resuelta se apunta en `resueltas: list[tuple[str, str, dict, bool]]` = `(elemento, id, declaración, creado)`: `for contrario, decl in zip(ficha.contrarios, ficha.declarados_contrarios, strict=True)` (y lo mismo para colaboradores). La línea `for contrario in …` conserva su forma para el M13 de P6.
  - Tras la relectura de vínculos, la **lectura de datos**: para cada entrada de `resueltas`, `get_cliente_contrario` o `get_colaborador` según el elemento; un fallo va a `sin_verificar` como `f"datos de {elemento} id={id}"` con su `[AVISO]`; lo leído, a `auditar_datos(elemento, id, decl, ficha_crm)`, y cada discrepancia se imprime `  [DATO] {d}` y se junta.
  - **Veredicto:** `faltan` (vínculos y Notas), `sobran` o `[DATO]` → un `[ERROR]` por tipo, con lo que hay que hacer sin hacerlo (spec §4 B.3): el de `faltan` conserva «La lectura DESMIENTE la escritura»; el de sobrantes dice que el YAML es la lista completa y que una parte legítima se añade al YAML y se relanza, y si no, se desvincula a mano, porque `crm_ficha` no desvincula; el de datos, que se revise y corrija en la ficha del CRM, porque `crm_ficha` no pisa. Si además hay `sin_verificar`, se dice. **Código 1** — un fallo conocido gana a un «SIN VERIFICAR». Ningún mensaje de fallo contiene la palabra «VERIFICADA».
  - Sin fallos y con `sin_verificar` → `f"OK ficha CRM completada: {resolved} — {SIN_VERIFICAR}: …"`, salida 0. Todo limpio → `f"OK ficha CRM completada y {EXITO_VERIFICADA}: {resolved}"`.

  **Migración de los tests del CLI que llegan a la verificación, escrita aquí y enumerada en el commit.** Se les declara la lectura de fichas con `_declara_fichas` y la ficha coherente con su YAML; los literales del contrato nuevo se adaptan a las constantes; y los positivos que la R2 señaló (H-05) exigen, **además**, la certificación completa y la ausencia de «SIN VERIFICAR». Ninguna propiedad se pierde:

  | Test | Fichas declaradas | Literales |
  |---|---|---|
  | `test_crm_ficha_orquesta_todo` | `1099` y `776` | + `cli.EXITO_VERIFICADA in` y `cli.SIN_VERIFICAR not in` |
  | `test_crm_ficha_cliente_propio_engel_volkers_vincula_id_27` | ninguna (no hay partes): `_declara_fichas(monkeypatch)`, para que un GET inesperado muera | — |
  | `TestVerificacionPorLectura._escrituras_en_verde` (sus cuatro tests) | `1099` y `776` | `test_todo_vinculado_dice_VERIFICADA`: `"VERIFICADA por lectura" in` → `cli.EXITO_VERIFICADA in`, + `cli.SIN_VERIFICAR not in`; `test_lectura_caida_es_SIN_VERIFICAR_no_fallo`: el negativo `"VERIFICADA por lectura" not in` → `cli.EXITO_VERIFICADA not in` |
  | `TestVerificarTODOLoQueLaCorridaEscribe._base` (sus cuatro tests) | `1099` y `776` | `test_notas_no_leibles_…`: el negativo, a la constante. `test_dos_partes_que_colapsan_…`: el `776` se declara como la ficha de **ANA** —no hay una ficha coherente con las dos, y el doble dice cuál devolvió el CRM, no fabrica dos (R2 §3)—; su aserto «la corrida escribió 2, la lectura ve 1» sigue, y el `[DATO]` de BEA que se suma no lo sustituye |
  | `TestElCRMDesescapaLasEntidadesHTML._con_notas` (sus dos tests) | `1099` (sin móvil: ese YAML no lo trae) | `test_una_entidad_desescapada_…`: + `cli.EXITO_VERIFICADA in` y `cli.SIN_VERIFICAR not in` |
  | `test_el_cli_vincula_TODOS_los_contrarios_no_solo_el_primero` | `1099` (JUAN) y `1100` (MARIA LOPEZ `11111111H`) | + `cli.EXITO_VERIFICADA in` y `cli.SIN_VERIFICAR not in` |

  No llegan a la verificación, y no cambian: `test_crm_ficha_dry_run_no_escribe`, `test_crm_ficha_sin_yaml_falla`, `test_crm_ficha_sin_expediente_falla`, `test_crm_ficha_falla_limpio_si_writer_revienta_mid_run` (parcial), `test_crm_ficha_cliente_propio_desconocido_falla_sin_escribir`, `test_el_plan_del_cli_enumera_los_dos_contrarios` (dry-run) y los de `TestLaGuardaDeRedMuerde`. `test_un_fallo_a_mitad_AUDITA_lo_ya_escrito` es parcial y no lee fichas.
- [ ] **Step 4:** `python -m pytest tests -k "crm_ficha or colaboradores_firmas" -p no:randomly -q` → PASAN.
- [ ] **Step 5:** commit `feat(crm_ficha): el CLI falla con sobrantes y con datos que no llegaron (MEJORAS #288; R1/H-03; R2/H-05)`, con la tabla de migración.

---

### Task 7: La fase previa y `id_crm`, juntas (spec §3 A.4; R2/H-01, H-06, H-08)

**Files:** Modify `core/sudespacho_relations.py`, `core/crm_ficha.py`, `scripts/crm_ficha.py`; Create `tests/test_crm_ficha_id_crm.py`; Test `tests/test_crm_ficha_lector.py`, `tests/test_crm_ficha_auditoria.py`, `tests/test_crm_ficha_cli.py`; migra `tests/test_crm_ficha_yaml_none.py`.

**Un solo commit**: el campo del DTO, la aceptación en el validador, la rama del core y la fase previa. Separarlos reabre H-06 (un `id_crm` aceptado que nadie consume va por el camino de **creación**).

**Interfaces:**
- `NuevoClienteContrario.id_crm: str = ""` y `NuevoColaborador.id_crm: str = ""`, **al final** de cada dataclass (nadie construye los DTOs por posición: medido con `git grep`, solo `core/crm_ficha.py` y la UI por kwargs).
- `resolver_contrario_existente(datos) -> str | None` y `resolver_colaborador_existente(datos, *, client=None) -> str | None` en `core/sudespacho_relations.py`: la ficha que **ya existe**, o `None` si hay que crearla. **No escriben.** Con `id_crm` devuelven ese id sin buscar; sin él, la resolución de siempre, que levanta ante conflicto, ambigüedad o consulta caída.
- `CLAVES_CONTRARIO` y `CLAVES_COLABORADOR` terminan en `"id_crm"`; la identidad acepta `nif`, `email` **o** `id_crm`; el DTO recibe `id_crm` canónico (`"01128"` → `"1128"`); la declaración **no** lo lleva (no es un dato que se compare).
- `contradicciones_previas(elemento, id_, declarado, ficha_crm, *, por_id: bool) -> list[str]` en `core/crm_ficha.py`.

- [ ] **Step 1: tests que fallan**

  `tests/test_crm_ficha_id_crm.py` (la rama del core):

```python
"""`id_crm` vive en el core: con él no se busca ni se crea (spec §3 A.4)."""
from unittest.mock import MagicMock

import pytest

from core import sudespacho_relations as sr


class NoDebiaLlamarse(BaseException):
    """Fuera de `Exception`: ningún `except Exception` del código bajo prueba se la traga."""


@pytest.fixture
def sin_busqueda_ni_alta(monkeypatch):
    def _prohibido(nombre):
        def _f(*a, **k):
            raise NoDebiaLlamarse(f"{nombre} no debía llamarse con id_crm")
        return _f
    for n in ("resolver_parte", "_resolver_colaborador", "create_cliente_contrario",
              "create_colaborador"):
        monkeypatch.setattr(f"core.sudespacho_relations.{n}", _prohibido(n))


def test_con_id_crm_el_contrario_no_se_busca_ni_se_crea_y_se_completa(sin_busqueda_ni_alta,
                                                                       monkeypatch):
    completar = MagicMock()
    monkeypatch.setattr("core.sudespacho_relations._completar_contrario_existente", completar)
    datos = sr.NuevoClienteContrario(nombre="ANA", id_crm="1128")
    assert sr.resolver_contrario_existente(datos) == "1128"
    assert sr._resolver_o_crear_contrario(datos) == ("1128", False)
    completar.assert_called_once_with("1128", datos)


def test_con_id_crm_el_colaborador_tampoco(sin_busqueda_ni_alta, monkeypatch):
    completar = MagicMock()
    monkeypatch.setattr("core.sudespacho_relations._completar_colaborador_existente", completar)
    datos = sr.NuevoColaborador(nombre="ANA", id_crm="776")
    assert sr.resolver_colaborador_existente(datos) == "776"
    assert sr._resolver_o_crear_colaborador(datos) == ("776", False)
    completar.assert_called_once_with("776", datos)


def test_sin_id_crm_se_resuelve_como_siempre(monkeypatch):            # control positivo
    resolver = MagicMock(return_value=sr.ResolucionParte(id="1099", por="nif"))
    monkeypatch.setattr("core.sudespacho_relations.resolver_parte", resolver)
    assert sr.resolver_contrario_existente(
        sr.NuevoClienteContrario(nombre="JUAN", nif="00000000T")) == "1099"
    resolver.assert_called_once_with("clientes_contrarios", nif="00000000T", email="")
```

  En `tests/test_crm_ficha_lector.py`: `id_crm` admitido como `'1128'`, `1128` y `' 01128 '` → `"1128"`, en los dos roles; rechazado como `'12a'`, `true`, `[1]`, `''`, `0`, `-3` y `1.5`; **basta como identidad** (sustituye a `test_R2H06_id_crm_todavia_NO_es_una_clave`, que fijaba el estado intermedio y deja de ser verdad en este commit: se dice en él); y no entra en la declaración. `test_las_tuplas_son_el_inventario_del_spec` pasa a esperar `id_crm` al final de las dos tuplas (literal del contrato nuevo, declarado).

  En `tests/test_crm_ficha_auditoria.py`:

```python
def test_la_fase_previa_solo_para_lo_DISTINTO():
    decl = {"nombre": "ANA", "apellido1": "GARCIA", "nif": "00000000T", "email": "ana@x.es"}
    vacia = {"nombre": "ANA", "1apellido": "", "nif_cif": "00000000T", "email": ""}
    assert cf.contradicciones_previas("clientes_contrarios", "1128", decl, vacia,
                                      por_id=False) == []
    otra = {**vacia, "1apellido": "PEREZ"}
    assert cf.contradicciones_previas("clientes_contrarios", "1128", decl, otra, por_id=False) == [
        "clientes_contrarios id=1128 1apellido: distinto (CRM 'PEREZ', YAML 'GARCIA')"]


def test_por_id_una_ficha_sin_nombre_es_que_no_existe():
    decl = {"nombre": "ANA", "email": "a@x.es"}
    assert cf.contradicciones_previas("colaboradores", "9", decl, {}, por_id=True) == [
        "colaboradores id=9: la ficha no existe o no tiene nombre; revisa el id_crm"]
    assert cf.contradicciones_previas("colaboradores", "9", decl, {}, por_id=False) == []
```

  En `tests/test_crm_ficha_cli.py`, el segundo ayudante y los tests de la fase previa:

```python
def _declara_resolucion(monkeypatch, contrarios=None, colaboradores=None):
    """Qué ficha EXISTE ya para cada parte (la fase previa, spec §3 A.4): `{clave: id | None}`,
    con la clave `id_crm`, `nif` o `email` de la parte, por ese orden. `None` = no existe, se
    creará. Una parte no declarada MATA el test, como `_declara_fichas`."""
    for nombre, tabla in (("resolver_contrario_existente", dict(contrarios or {})),
                          ("resolver_colaborador_existente", dict(colaboradores or {}))):
        def _res(dto, *a, _t=tabla, _n=nombre, **k):
            clave = dto.id_crm or dto.nif or dto.email
            if clave not in _t:
                raise LecturaNoDeclarada(f"{_n}({clave!r}) no está declarado en este test")
            return _t[clave]
        monkeypatch.setattr(f"scripts.crm_ficha.{nombre}", _res)
```

  - **R2/H-01, por NIF:** `_declara_resolucion(contrarios={"00000000T": "1099"}, colaboradores={…: None})` y la ficha 1099 con `1apellido: LOPEZ` → código 1, la línea `clientes_contrarios id=1099 1apellido: distinto (CRM 'LOPEZ', YAML 'PEREZ')`, y `link_ev_mmc`, `ensure_*` y `update_expediente` **sin llamar**;
  - **por `id_crm` contradicho por su NIF:** YAML `contrario: {nombre: JUAN, apellido1: PEREZ, nif: '11111111H', id_crm: '1128'}` y la ficha 1128 `{nombre: JUAN, 1apellido: LOPEZ, nif_cif: '22222222J'}` → código 1 con las dos discrepancias, y cero writers;
  - **la segunda parte inválida:** dos contrarios, el primero nuevo (`None`) y el segundo contradicho → cero writers, **tampoco** para el primero;
  - **`id_crm` inexistente o GET caído** (`get_cliente_contrario` lanza `SudespachoRelationsError("HTTP 404")`, o `RuntimeError`) → código 1 («no se pudo leer la ficha … no se escribe sobre lo que no se ha podido comparar») y cero writers; **ficha sin nombre** por `id_crm` → «no existe o no tiene nombre»;
  - **un conflicto de identidad** (`resolver_contrario_existente` levanta `ConflictoDeIdentidad`) → código 1 antes de escribir, con el texto del conflicto;
  - **un colaborador por id:** `colaboradores: [{nombre: ANA, id_crm: '776'}]` → la fase previa lee el 776, `ensure_colaborador_vinculado` recibe un DTO con `id_crm == "776"` y la corrida verifica;
  - **R2/H-08, `--dry-run` con `id_crm`:** los dos resolutores y los dos GET doblados para levantar `LecturaNoDeclarada` si se llaman → salida 0.
- [ ] **Step 2:** FALLAN.
- [ ] **Step 3: implementación.**

  En `core/sudespacho_relations.py`, al final de los dos dataclasses:

```python
    #: La ficha EXACTA del CRM, cuando el `_ficha_crm.yaml` la declara (spec §3 A.4 de
    #: `crm_ficha`): con ella no se busca ni se crea. Vacío = identificar por NIF o email.
    id_crm: str = ""
```

  y los resolutores:

```python
def resolver_contrario_existente(datos: NuevoClienteContrario) -> str | None:
    """La ficha que YA existe para esta parte, o `None` si hay que crearla. **No escribe.**

    Con `id_crm` no se busca: se devuelve ese id y quien llama lo lee (spec §3 A.4 de
    `crm_ficha`). Sin él, la resolución de siempre por NIF o email, que levanta ante conflicto,
    ambigüedad o una consulta caída. La usan la fase previa de `crm_ficha` y
    `_resolver_o_crear_contrario`, y así las dos identifican igual.
    """
    if datos.id_crm:
        return datos.id_crm
    r = resolver_parte("clientes_contrarios", nif=datos.nif, email=datos.email)
    _exigir_identidad_cierta(r, elemento="clientes_contrarios", nif=datos.nif, email=datos.email)
    return r.id


def _resolver_o_crear_contrario(datos: NuevoClienteContrario) -> tuple[str, bool]:
    existente = resolver_contrario_existente(datos)
    if existente:
        _completar_contrario_existente(existente, datos)
        return existente, False
    return create_cliente_contrario(datos), True


def resolver_colaborador_existente(datos: NuevoColaborador, *,
                                   client: SudespachoLegacyClient | None = None) -> str | None:
    """Espejo de `resolver_contrario_existente` para colaboradores. **No escribe.**"""
    if datos.id_crm:
        return datos.id_crm
    return _resolver_colaborador(datos, client=client)
```

  y `_resolver_o_crear_colaborador` llama a `resolver_colaborador_existente(datos, client=client)` en vez de a `_resolver_colaborador`. Las docstrings de los dos `_resolver_o_crear_*` se conservan.

  En `core/crm_ficha.py`: `"id_crm"` al final de `CLAVES_CONTRARIO` y `CLAVES_COLABORADOR`;

```python
_IDENTIDAD = ("nif", "email", "id_crm")


def _id_crm(v: object) -> str | None:
    """El `id_crm` canónico, o `None` si no es el número de una ficha: entero positivo o
    dígitos ASCII. Un booleano no vale, aunque Python lo cuente como entero."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return str(v) if v > 0 else None
    if isinstance(v, str) and v.strip().isascii() and v.strip().isdigit() and int(v) > 0:
        return str(int(v))
    return None
```

  en `_problemas_parte`, `id_crm` fuera del bucle de escalares (`for k in validas if k != "id_crm"`), su propio problema si viene y no es un id (`f"{ruta}.id_crm: {v!r} no es el número de una ficha del CRM"`; `null` es «no hay dato», como en los demás), y la identidad con `_hay(nif) or _hay(email) or _id_crm(d.get("id_crm"))`, con el mensaje `—falta NIF, email o id_crm—`; los constructores pasan `id_crm=_id_crm(d.get("id_crm")) or ""` y el resto de claves por `_valor`; `_declaracion` salta `id_crm`. Y:

```python
def contradicciones_previas(elemento: str, id_: str, declarado: Mapping, ficha_crm: Mapping,
                            *, por_id: bool) -> list[str]:
    """Lo que la fase previa no deja pasar (spec §3 A.4): un dato DISTINTO en una ficha que ya
    existe y, si se llegó por `id_crm`, una ficha sin nombre, que es como vuelve un id que no
    existe. Lo VACÍO no es contradicción: lo completa la corrida o lo dice la lectura final."""
    fuera = [str(d) for d in auditar_datos(elemento, id_, declarado, ficha_crm)
             if d.tipo == "distinto"]
    if por_id and not _n_texto(ficha_crm.get("nombre")):
        fuera.insert(0, f"{elemento} id={id_}: la ficha no existe o no tiene nombre; revisa el "
                        "id_crm")
    return fuera
```

  En `scripts/crm_ficha.py`: importar `resolver_contrario_existente` y `resolver_colaborador_existente`, y `contradicciones_previas`; el plan dice `(id_crm N)` en vez de `(dedup NIF/email)` cuando la parte lo lleva; el mensaje de sobrantes añade «con `id_crm` si no tiene NIF ni email»; y la fase previa, **después** del `if dry_run` y de la confirmación y **antes** de `link_ev_mmc`:

```python
def _fase_previa(ficha) -> list[str]:
    """SOLO LECTURA (spec §3 A.4): cada parte que ya existe, contra lo que el YAML declara.
    Devuelve TODOS los problemas; si hay alguno, no se escribe nada."""
    problemas: list[str] = []
    for elemento, partes, declarados, resolver, leer in (
        ("clientes_contrarios", ficha.contrarios, ficha.declarados_contrarios,
         resolver_contrario_existente, get_cliente_contrario),
        ("colaboradores", ficha.colaboradores, ficha.declarados_colaboradores,
         resolver_colaborador_existente, get_colaborador),
    ):
        for dto, decl in zip(partes, declarados, strict=True):
            try:
                existente = resolver(dto)
            except Exception as exc:  # noqa: BLE001 — conflicto, ambigüedad o consulta caída
                problemas.append(f"{elemento} {dto.nombre!r}: {exc}")
                continue
            if not existente:
                continue                    # se creará: la audita la lectura final
            try:
                actual = leer(existente)
            except Exception as exc:  # noqa: BLE001
                problemas.append(f"{elemento} id={existente}: no se pudo leer la ficha "
                                 f"({exc!r}); no se escribe sobre lo que no se ha podido comparar")
                continue
            problemas += contradicciones_previas(elemento, existente, decl, actual,
                                                 por_id=bool(dto.id_crm))
    return problemas
```

  y en `main`, tras la confirmación:

```python
    previas = _fase_previa(ficha)
    if previas:
        typer.echo("[ERROR] El CRM contradice el _ficha_crm.yaml, o no se ha podido comparar, "
                   "así que no se escribe NADA:\n  - " + "\n  - ".join(previas) + "\n"
                   "crm_ficha no pisa datos: corrige el YAML o la ficha del CRM y relanza.",
                   err=True)
        raise typer.Exit(code=1)
```

  **Migración, escrita aquí y enumerada en el commit.**
  - Los dos tests de `test_crm_ficha_yaml_none.py` que la Task 3 partió en dos casos **vuelven a su forma**, todos los campos vacíos a la vez, con `id_crm: '776'` (colaborador) e `id_crm: '1128'` (contrario) como identidad.
  - Los tests del CLI que pasan de la confirmación declaran la resolución con `_declara_resolucion`, coherente con lo que ya dicen sus `ensure_*` (una parte que el doble da por **creada** no existía: `None`; una **existente**, su id): `test_crm_ficha_orquesta_todo` (JUAN `None`, ANA `776`), `test_crm_ficha_falla_limpio_si_writer_revienta_mid_run` (las dos `None`), `TestVerificacionPorLectura._escrituras_en_verde`, `TestVerificarTODOLoQueLaCorridaEscribe._base` (JUAN `1099`, ANA y BEA `776`), `TestElCRMDesescapaLasEntidadesHTML._con_notas` (JUAN `1099`), `test_el_cli_vincula_TODOS_los_contrarios_no_solo_el_primero` (las dos `None`) y los tests nuevos de la Task 6. `test_crm_ficha_cliente_propio_engel_volkers_vincula_id_27` no tiene partes. `TestLaGuardaDeRedMuerde::test_una_salida_no_declarada_MATA_el_test` sigue sin declarar nada, a propósito: ahora muere antes, en la fase previa, y sigue muriendo.
- [ ] **Step 4:** `python -m pytest tests -k "crm_ficha or colaboradores_firmas or sudespacho_relations" -p no:randomly -q` → PASAN; y `git grep -n "id_crm" -- core scripts` enseña que `create_*` y los payloads no lo leen.
- [ ] **Step 5:** commit `feat(crm_ficha): fase previa de solo lectura e id_crm en los resolutores del core (R2/H-01, H-06, H-08)`, con la migración.

---

### Task 8: Integración con `ensure_*`, resolutores y completado reales (spec §6)

**Files:** Create `tests/test_crm_ficha_integracion.py`.

Un `CRMFalso` **con estado** sustituye el transporte de `core.sudespacho_relations` —las funciones que hablan HTTP— y deja correr de verdad `ensure_*`, `resolver_*_existente`, `resolver_parte`, `_exigir_identidad_cierta` y `_completar_*_existente`. Se instala sobre `_buscar_registros`, `find_colaborador_by_email`, `get_cliente_contrario`, `get_colaborador`, `update_cliente_contrario`, `update_colaborador`, `create_cliente_contrario`, `create_colaborador`, `_link_rest`, `get_relaciones` y `SudespachoLegacyClient` (un cliente inerte con `__exit__`) en `core.sudespacho_relations`, y sobre los nombres que el CLI importó (`get_cliente_contrario`, `get_colaborador`, `get_relaciones`, `get_expediente`, `update_expediente`) en `scripts.crm_ficha`. La guarda `_sin_red` del fichero sigue: si algo se escapa del doble, el test muere.

```python
class CRMFalso:
    """El CRM entero, en memoria: fichas por elemento, los vínculos del expediente, las Notas
    y un registro de cada ESCRITURA (`escrituras`) y de cada búsqueda (`busquedas`)."""

    def __init__(self, fichas=None, vinculos=None):
        self.fichas = {"clientes_contrarios": {}, "colaboradores": {}, **(fichas or {})}
        self.vinculos = {"clientes_propios": [], "clientes_contrarios": [], "colaboradores": [],
                         **(vinculos or {})}
        self.notas = ""
        self.escrituras: list[tuple] = []
        self.busquedas: list[tuple] = []
        self.lecturas: list[tuple] = []
        #: {(operación, id): {número de llamada, …}} que fallan: la 2.ª lectura de una ficha
        #: existente es la del completado (1.ª, fase previa; 3.ª, lectura final).
        self.fallos: dict[tuple, set[int]] = {}
        #: Propiedades que el CRM «pierde» al crear (un POST que no guardó un dato).
        self.pierde_al_crear: set[str] = set()
        self._cuenta = Counter()
        self._siguiente = 5000
```

  con un método por función doblada que respeta **la forma** de lo que devuelve la real: `Consulta(registros=[{"id": …, "values": [{"property": {"name": p}, "value": v}, …]}])` en `_buscar_registros` (igualdad por `_canonizar_documento` si la propiedad es `nif_cif`, por minúsculas si es `email`); un `dict` aplanado en los GET, `SudespachoRelationsError("… HTTP 404")` si el id no existe; el `update_*` aplica el cambio y devuelve la ficha (para que `_completar_colaborador_existente` pueda confirmarlo); `create_*` asigna un id nuevo con el mapeo del payload real (`1apellido`, `nif_cif`, `telefono1`, `provincia` canónica); `_link_rest` parsea `right.<bloque>.<id>` y **no duplica** (es idempotente, `_link_rest`: «relaciones ya existentes devuelven 201 sin crear duplicados»); y `get_relaciones` devuelve `{bloque: [{"id": …}]}` con los bloques no vacíos.

  Tests:
  - **Convergencia:** contrario nuevo por NIF y colaborador existente (776, móvil vacío en el CRM); dos corridas → las dos `EXITO_VERIFICADA`; una sola creación en total; los vínculos, los mismos tras la segunda.
  - **R2/H-01 con el completado real:** la ficha 1128 tiene `1apellido: OTRO` y email vacío; el YAML declara `PEREZ` y un email → código 1 y `crm.escrituras == []` — **ni el PUT del email** que el revisor midió.
  - **Por id contradicho:** código 1, `escrituras == []` y `busquedas == []`.
  - **La segunda parte inválida:** `escrituras == []`.
  - **Colaborador por id:** `id_crm: '776'` → ninguna búsqueda de colaboradores; un PUT del móvil vacío y el vínculo; `EXITO_VERIFICADA`.
  - **GET del completado fallido** (la 2.ª lectura de 1128) y **PUT del completado fallido** → el campo sigue vacío y sale `[DATO] … vacío en el CRM`, código 1.
  - **Una parte CREADA a la que el CRM no guardó un dato** (`pierde_al_crear = {"2apellido"}`) → `[DATO] clientes_contrarios id=5000 2apellido: vacío en el CRM`, código 1.
  - **Cada writer que falla** (parametrizado: vincular el cliente propio, crear el contrario, vincularlo, vincular el colaborador, las Notas), con un colaborador **ajeno** ya vinculado de otra corrida → código 1, sin `EXITO_VERIFICADA` y sin `[SOBRA]`.
  - **Cero writers, y cero llamadas al CRM, ante cada entrada inválida** (parametrizado): clave repetida, alias, merge, clave desconocida, mapping en un escalar, parte sin identidad, `id_crm` que no es un número, provincia desconocida, teléfono `'+34'`, `cliente_propio` desconocido, raíz lista → código 1 y `escrituras == busquedas == lecturas == []`.

- [ ] **Step 1:** escribir el doble y los tests. **Step 2:** correrlos: los que prueban propiedades ya construidas pasan a la primera, y eso **no** acredita nada todavía — lo acreditan los mutantes de la Task 9, que tienen que ponerlos en rojo. **Step 3:** si alguno falla, el defecto es de las Tasks 1-7 y se corrige allí con su test, no aquí. **Step 4:** commit `test(crm_ficha): integracion con ensure_*, resolutores y completado reales (spec §6; R2/H-09)`.

---

### Task 9: Arnés de mutantes, sobre una copia (spec §6)

**Files:** Create `tests/_mutantes_crm_ficha.py`.

**Sobre una copia del árbol, no sobre el vivo.** La §9 lo justifica diciendo que el patrón de `tests/_mutantes_mejoras_214.py` es «justo lo que prohíbe» `tests/test_guard_aislamiento_paralelo.py`, y eso **no es exacto**: el guard exime a los arneses porque pytest no los colecciona (`test_guard_aislamiento_paralelo.py`, docstring de `ficheros_de_test_coleccionados`). La razón es otra, y basta: un arnés que se cae a mitad deja el árbol vivo **mutado** (lo midió P4, y por eso `_mutantes_p6.py` arma la restauración antes de mutar), y con una copia esa posibilidad no existe por construcción.

- La copia: `core/`, `scripts/`, `tests/` y los ficheros de configuración de pytest de la raíz, en un directorio temporal **fuera** del repo; se comprueba al cerrar que los `sha256` de los ficheros mutados en el árbol vivo no han cambiado.
- Por mutante: base **verde** del test objetivo en la copia; mutación aplicada **una** vez (el ancla tiene que aparecer exactamente una vez) y **compilable**; el test objetivo se corre con `--junitxml`, y la muerte solo cuenta si el test **se ejecutó** y falló por su **aserto** (`<failure>` de tipo `AssertionError` o `Failed`, el de `pytest.raises`), no por colección, setup ni una excepción de programa roto (`<error>`, `NameError`, `ImportError`, `AttributeError`…). Se restaura la copia y se sigue.
- El detalle de cada mutante —base, rc, tipo del fallo— se guarda en un JSON junto a la copia, y la salida dice su ruta.

| Mutante | Tiene que morir por |
|---|---|
| el lector acepta claves repetidas | `test_R1H01_una_clave_repetida_se_rechaza_con_su_linea` |
| el lector acepta el merge | `test_R2_el_merge_SIN_alias_se_rechaza` |
| `cargar_ficha_yaml` vuelve a `yaml.safe_load` | `test_cargar_ficha_yaml_lee_con_el_lector_sin_perdida` |
| `apply` vuelve a `yaml.safe_load` | `test_una_clave_repetida_falla_sin_tocar_el_fichero` |
| `_problemas_escalar` acepta mappings | `test_R1H02_un_mapping_o_una_lista_en_CUALQUIER_escalar_se_rechaza` |
| se quita la exigencia de identidad | `test_R1H04_una_parte_sin_identidad_estable_se_rechaza` |
| dos asignaciones del constructor cruzadas | `test_cada_clave_llega_a_su_atributo` |
| se quita el cálculo de `sobran` | `test_R288_el_653_dos_colaboradores_de_mas_son_sobrantes` |
| `Counter` sobre un `set` (ejecutable: pierde la multiplicidad, no el tipo) | `test_multiplicidad_en_los_dos_sentidos_y_id_int_frente_a_str` |
| `auditar_datos` devuelve siempre `[]` | `test_R1H03_la_ficha_de_w030a13_con_el_apellido_vacio_no_pasa` |
| la provincia se normaliza solo de un lado | `test_R2H03_la_provincia_se_compara_igual_en_los_dos_lados` |
| la lectura final se salta los colaboradores | el test del colaborador con un dato que no llegó (Task 6) |
| la lectura final se salta las partes creadas | el de la parte creada a la que el CRM no guardó un dato (Task 8) |
| el core ignora `id_crm` | `test_con_id_crm_el_contrario_no_se_busca_ni_se_crea_y_se_completa` |
| se quita la fase previa | el de R2/H-01 por NIF (Task 7) |
| la fase previa va detrás de `link_ev_mmc` | el mismo: `link_ev_mmc` tiene que seguir sin llamarse |
| la fase previa corre antes del corte de `--dry-run` | el de R2/H-08 (Task 7) |
| la parcial **emite** sobrantes | el de la parcial (Task 6) |
| un «SIN VERIFICAR» tapa un fallo conocido | el de «un fallo conocido gana» (Task 6) |

- [ ] Correr `python -m tests._mutantes_crm_ficha`: todos muertos, cada uno por el suyo. Y `python -m tests._mutantes_p6`, que la Task 2 re-apuntó, con el árbol limpio: sus 39. Commit.

---

### Task 10: Documentación, cierre y la R3

- [ ] `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`, donde se prepara el `_ficha_crm.yaml`: el contrato nuevo en cinco líneas —claves de cada nivel, tipos, NIF/email/`id_crm`, el YAML es la lista completa, y qué hacer con un `[SOBRA]`, con un `[DATO]` y con un error de la fase previa—.
- [ ] `docs/MEJORAS_FUTURAS.md`: `#283` y `#288` `[CERRADA …]` con el PR; una entrada para **completar apellidos vacíos** de una ficha existente (spec §5), con su radio de daño, si no existe ya; y los dos límites declarados del spec §5 (el NIF ajeno con `id_crm`, la ventana entre la fase previa y la escritura), si cumplen la regla de promoción del backlog.
- [ ] `PLAN.md`: fila #40 al día; la fila #39 con su hash `4209582`. Bitácora. `python -m scripts.session_close` (dos semillas).
- [ ] **R3 de Codex sobre el diff** (`4209582..HEAD`), `gpt-6-astra` · `medium` · `default`: los tres flags en la invocación; objeto por `git archive` de los dos extremos, fuera del repo; vigía de fin **y** de muerte armado antes de lanzar; mandato numerado, anclado a los commits y sin coacción; los dos ejes en cada hallazgo (severidad y coste del remedio: `trivial` · `acotado` · `estructural`); veredicto del set cerrado. Adjudicación en la §10 de este plan; acta hermana `…-crm-ficha-claves-y-conjunto-r3-adversarial-review.md`. **Es la última**: no hay cuarta sin autorización expresa de Nikolai.
- [ ] Antes de usarla en un caso real: `crm_ficha --dry-run` y después sobre un expediente de prueba, **verificando por lectura** en el CRM — la forma de `cp` y `provincia` en el GET (Task 5) incluida.

## Self-review

- **Cobertura del spec rev. 3:** A.1 → T1 + T4; A.2/A.3/A.5 → T2; A.4 → T3 (identidad) + T7 (`id_crm`, fase previa) + T8; B.1 → T5 + T6; B.2 → T5 + T6 + T8; B.3/B.4 → T6; §5 → T10 (backlog) y los límites declarados; §6 → los tests de T1-T8 y los mutantes de T9; §7 → T10.
- **Nombres consistentes:** `leer_yaml_ficha`, `validar_ficha`, `CLAVES_*`, `SIN_IDENTIDAD`, `auditar_relaciones`/`AuditoriaRelaciones`/`BLOQUES_AUDITADOS`, `auditar_datos`/`Discrepancia`, `CAMPOS_*_CRM`, `declarados_*`, `contradicciones_previas`, `resolver_*_existente`, `id_crm`, `EXITO_VERIFICADA`, `SIN_VERIFICAR`, `_declara_fichas`, `_declara_resolucion`, `LecturaNoDeclarada`, `CRMFalso` — los mismos en todas las tareas.
- **Comprobado antes de escribir, fuera del repo, el 2026-09-25:** el lector de la Task 1 contra los 19 casos de arriba y de la R2 (repetidas acumuladas con su línea, clave lista y mapping, alias, merge con y sin alias, sintaxis rota, `&amp;`, documento vacío, raíz lista, igual que `safe_load` en lo normal); las sugerencias de `difflib` (`apellido` → `apellido1` y `apellido2`; `zzzz` → ninguna); que `normalize_es_phone` deja `V_movil` intacto y `'+34'`, `'0034'` y `'-'` vacíos; y la sonda de migración de la cabecera. Donde algo de esto no cuadre al implementar, se corrige aquí, se dice y se mide antes de codificar.

## 9. Adjudicación de la revisión adversarial del plan (Codex, 2026-09-25) — REQUIERE-REVISION, remediado

- **Objeto revisado:** este plan rev. 1 y, como segundo encargo, si el spec rev. 2 remedia de verdad la R1; los dos en `0177559`
- **Ronda:** R2 de la pieza (la R1 fue sobre el spec rev. 1; la R3, sobre el diff, la autorizó expresamente Nikolai el 2026-09-25)
- **Revisor:** Codex CLI `0.155.0-alpha.16.3`, `gpt-6-astra` · `medium` · `default` (modelo y esfuerzo releídos del rollout)
- **Informe recibido:** `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto-r2-adversarial-review.md`
- **Hallazgos:** 9 — 2 `alta`, 7 `media`; 9 confirmados contra la fuente, 0 refutados
- **Remediado en:** spec rev. 3 (A.1, A.3, A.4, B.2, B.3, §5 y §6) y este plan rev. 2 (cabecera y Tasks 1-10), antes de escribir una línea de código; esta sección era la lista cerrada de lo que cambiaba

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

## 10. Adjudicación de la revisión adversarial del diff (Codex, 2026-09-26) — REQUIERE-REVISION, remediado

- **Objeto revisado:** el diff `4209582..93c1907`, que construye esta pieza según el spec rev. 3 y este plan rev. 2, más el dictamen sobre los nueve remedios de la R2
- **Ronda:** R3 de la pieza y la última: Nikolai la autorizó expresamente el 2026-09-25 sobre el techo de dos (spec §7), y no hay cuarta sin su autorización
- **Revisor:** Codex CLI `0.155.0-alpha.16.4`, `gpt-6-astra` · `medium` · `default` (modelo y esfuerzo releídos del rollout; la velocidad, afirmada desde el lanzador conservado)
- **Informe recibido:** `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto-r3-adversarial-review.md`
- **Hallazgos:** 4 — 1 `alta`, 1 `media`, 2 `baja`; 4 confirmados contra la fuente, 0 refutados; y una observación que el revisor no eleva a hallazgo, confirmada también
- **Remediado en:** este mismo PR, sobre `93c1907`: `core/crm_ficha.py` y `scripts/crm_ficha.py` con sus tests (`cc5a241`), los dos arneses, el spec rev. 4 y `MEJORAS #306`/`#307`. **Ninguna ronda revisa el remedio**: esta era la última autorizada

**Los cuatro se reprodujeron contra la fuente, no contra el informe** (acta §2). Los tests de las
reglas nuevas se vieron en rojo antes de su código; los de integración del H-01, escritos con el
core ya corregido, acreditan su sensibilidad por sus mutantes (M21, M22); y la creación fallida de
colaborador cubre un comportamiento que ya existía, así que pasó a la primera. Antes de remediar,
la pregunta de siempre: **¿de qué frontera es esto un ejemplo?** No son cuatro defectos sueltos,
son dos fronteras y una ventana.

**Frontera 1 — lo que se compara tiene que ser lo que se escribe, y lo que se busca (H-01, H-02).**

- **H-01 (`alta` · `acotado`).** Los DTO llevaban el NIF tal como venía y el CRM lo guardaba así;
  la búsqueda manda la forma canónica, y el CRM —medido en la docstring de `_canonizar_documento`—
  normaliza caja y espacios pero **no** separadores. Con `00.000.000-T` la segunda corrida no
  encontraba la ficha de la primera y creaba otra; y en el colaborador por `id_crm` con un NIF
  ajeno, el completado escribía un NIF que la búsqueda no ve, así que la resolución siguiente
  devolvía la otra ficha **sin** ambigüedad: la frase del spec §5 («falla cerrado») era falsa. Y mi
  doble, `CRMFalso`, canonizaba los dos lados: más permisivo que el servidor, certificaba una
  convergencia que no existe. **Remedio:** el NIF viaja en la forma con la que se busca (`_nif`, en
  la construcción de los DTO de esta pieza; los demás llamadores no cambian) y la declaración
  conserva el escrito, que es lo que se audita. El doble filtra como el CRM medido. Dos
  regresiones: la convergencia con separadores en los dos roles, y el colaborador por id con un NIF
  ajeno, cuya resolución siguiente por NIF ahora **para** (`ConflictoDeIdentidad`). La frase del §5
  se corrige con lo medido: vale para el colaborador; en el contrario el NIF no es completable, no
  se escribe, y la lectura final lo da por vacío. **Declarado, no remediado:** una ficha histórica
  con el NIF guardado con separadores sigue sin encontrarla ninguna búsqueda canónica; buscarla es
  la ampliación que el propio revisor dejó fuera del remedio.
- **H-02 (`media` · `acotado`).** Un NIF declarado que se queda en nada sin sus separadores
  (`'-- .'`) contaba como identidad y se comparaba igual a una ficha sin NIF: «VERIFICADA».
  **Remedio:** se rechaza al validar, en los dos roles y aunque haya email o `id_crm`, y la identidad
  cuenta el NIF por su forma canónica. Es la propiedad que la R2 cerró en el DTO —un dato declarado
  no puede desaparecer por el camino— reapareciendo en el comparador, y su cierre es el mismo que ya
  tenía el teléfono que se vacía. **No se toca, y se ficha:** `_resolver_colaborador` ignora
  `r.motivo`, anterior a este diff. Por `crm_ficha` ya no llega el NIF no interpretable; el buzón
  compartido con una ficha sin documento, sí, y cambiarlo cambia a todos los llamadores →
  `MEJORAS #307`, con su propia regresión.

**Frontera 2 — el lector y el arnés tienen que decir lo que prometen (H-03, H-04).**

- **H-03 (`baja` · `acotado`).** El merge se rechazaba sin mirar su valor, así que una repetida
  debajo no salía; y una clave escalar que YAML convierte (`1`, `null`) pasaba el lector porque se
  miraba el nodo y no la clave construida. **Remedio:** se construye el valor del merge rechazado y
  se rechaza toda clave que no sea un texto, con su línea.
- **H-04 (`baja` · `acotado`).** El M11 re-apuntado de P6 dejaba el elemento inválido vivo hasta
  `_contrario_de`, donde el programa moría con un `AttributeError` que el arnés de P6 no cuenta como
  roto, a propósito. **Remedio:** la mutación ejecutable —filtrar el elemento en silencio, que es
  la pérdida que el test existe para detectar—, que muere por `DID NOT RAISE`. La acredita el arnés
  estricto de esta pieza, cuyo M34 es la misma sustitución.

**La ventana — la abre la propia corrida, no solo otra sesión (la observación).** Cada parte se
compara con el CRM de **antes** de la corrida, así que dos declaraciones que acaban en la misma ficha
pasaban las dos y la primera completaba lo que la segunda contradice. **Remedio:** lo que se decide
sin el CRM, al validar —el mismo `id_crm` o el mismo NIF canónico en dos partes de un rol, y un email
compartido sin el NIF de las dos o el `id_crm` de las dos, porque el buzón solo se descarta por
documento—; y lo que solo se ve resolviendo, en la fase previa: dos partes que resuelven a la misma
ficha existente, con cero writers. **Queda abierto, declarado en el §5 del spec, y falla cerrado:**
lo que la corrida completa puede hacer que la resolución de una parte posterior **pare** a mitad
—un contrario por id cuya ficha no tiene NIF recibe el email que otra parte comparte—, con código 1
y escritura parcial. Cerrarlo del todo sería escribir por el id resuelto en la fase previa en vez
de volver a resolver: un cambio estructural que ninguna ronda revisaría, y no se hace.

**Lo que la R3 echó en falta en el arnés (§5 del informe) entra en él:** el NIF canónico por rol
(M21, M22), el NIF que se vacía y el que cuenta como identidad (M23, M24), el merge y la clave no
textual (M25, M26), las identidades repetidas, el email compartido y las dos partes en una ficha
(M27-M29), las cuatro reglas que tenían test y ningún mutante —clave desconocida, `id_crm` no
numérico, teléfono, provincia— (M30-M33) y el elemento filtrado en silencio (M34). **34 de 34
muertos por su aserto**, con el árbol vivo intacto; P6, **39 de 39**, con su M11 nuevo. El censo de
solo lectura de los catorce `_ficha_crm.yaml` reales no cambia: trece pasan y W-030A13 se rechaza
por su `apellido`, así que las reglas nuevas no rechazan ninguna ficha real.

**El dictamen sobre la R2 se acepta:** H-02, H-04 y H-09, **incompletos**, y lo que les faltaba es
exactamente H-02, H-03 y H-01 de esta ronda, más la creación fallida de colaborador que la matriz de
writers no tenía y que entra en ella. Los otros seis, **reales**. Y la salvedad del revisor sobre el
M19 original —muere primero por el diagnóstico, no por el aserto de cero writers— es cierta y la
cubre su variante discriminante, que él mismo corrió: la propiedad tiene defensa.

**La incidencia del revisor, localizada:** su primer intento del arnés, interrumpido, dejó un
directorio en `%TEMP%` de esta máquina, fuera de su directorio (acta §2), que esta sesión **no puede
leer**: lo creó su proceso aislado. Nikolai pidió el 2026-09-26 borrar los temporales revisándolos
antes. Las seis copias del arnés propio fueron a la Papelera tras comprobar, fichero a fichero, que
todo su contenido está en git o es una versión superada —saltos de línea, borradores del arnés—; los
dos informes de hoy (34 de 34, y M27-M28) se conservan junto al lanzador de la R3. El directorio del
revisor queda para Nikolai: sin poder leerlo no se puede revisar antes de borrar.

**Lo que NO cambia:** el YAML es la lista completa; `crm_ficha` nunca desvincula ni pisa;
`_COMPLETABLES_*` no se toca; y no se buscan duplicados históricos escritos con separadores.
