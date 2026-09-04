# Autorrelleno de fichas de colaborador desde la firma — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que las fichas de colaborador del CRM sudespacho se rellenen con el móvil y el fijo que
los consultores de E&V ya escriben en la firma de sus correos, sin que un fallo de atribución pueda
escribir el teléfono de una persona en la ficha de otra.

**Architecture:** Tres piezas y un solo camino de escritura. La pieza **A** (`core/email_firmas.py`)
lee firmas de un `.eml` y no conoce el CRM. La pieza **B** (`scripts/crm_colaboradores_firmas.py`)
produce un informe para que Nikolai lo apruebe y luego escribe en `_ficha_crm.yaml`. La pieza **C**
(en `core/sudespacho_relations.py`) es la única que toca el CRM, y es el espejo exacto de
`_completar_contrario_existente`: rellena sólo lo vacío. Antes de todo eso, dos defectos vivos que
el trabajo propagaría.

**Tech Stack:** Python 3.12+, `email` (stdlib), `httpx`, `typer`, `pytest`, `pytest-randomly`.

**Spec:** `docs/superpowers/specs/2026-09-04-colaboradores-firma-autorrelleno-design.md`

## Global Constraints

- **Encoding: UTF-8 sin BOM siempre.** Nunca `Add-Content` ni `Get-Content -Raw` sin `-Encoding UTF8`.
- **Intérprete:** `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`. Comandos desde la raíz
  del worktree.
- **`--basetemp=C:/t/<corto>`** en toda invocación de pytest, o salta un fallo falso por MAX_PATH.
- **Dos semillas antes de cerrar:** `-p randomly --randomly-seed=777` y `--randomly-seed=31337`.
- **Ningún test sale a la red.** Todo fichero de test nuevo lleva la guarda `autouse` que corta
  `httpx` entero y levanta una excepción derivada de **`BaseException`** (código literal en Task 1,
  paso 1). Un `AssertionError` lo atraparía el `except Exception` de la pieza C —que por diseño no
  lanza— y la guarda quedaría inerte.
- **Ningún dato personal real en `tests/` ni en comentarios.** Datos sintéticos: `612345678`,
  `912345678`, `12345678Z`, `ana@engelvoelkers.example`. **No transcribir documentos de identidad
  reales.** El leak-guard bloquea el commit.
- **Sólo se rellena lo VACÍO en el CRM.** Nunca se sobrescribe un valor existente.
- **`main` está protegida:** rama + PR. Una ronda adversarial sobre el diff antes de mergear.
- **Verificar por resultado, nunca por status.** Tras escribir, GET y comprobar el valor.

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `core/crm_ficha.py` (modificar) | D2: `_colaborador_de` y `contrario.movil` no pueden producir `"None"` |
| `core/sudespacho_relations.py` (modificar) | D1 (`_PROP_NIF`) + pieza C: `get_colaborador`, `update_colaborador`, `_completar_colaborador_existente`, `_resolver_o_crear_colaborador` |
| `core/email_firmas.py` (crear) | Pieza A: localizar bloques de firma, atribuirlos, leer campos, consolidar. **No importa nada del CRM** |
| `scripts/crm_colaboradores_firmas.py` (crear) | Pieza B: `report` y `apply` |
| `tests/test_crm_colaborador_props.py` (crear) | D1 + pieza C |
| `tests/test_crm_ficha_yaml_none.py` (crear) | D2 |
| `tests/test_email_firmas.py` (crear) | Pieza A |
| `tests/test_crm_colaboradores_firmas_cli.py` (crear) | Pieza B |
| `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (modificar) | §9.4 deja de ser manual |
| `docs/INTEGRACION_SUDESPACHO.md` (modificar) | El contrato de `colaboradores`, enumerado |

**Orden y por qué:** D1 primero porque con él vivo el camino del colaborador **aborta** en cuanto la
ficha trae un NIF, y ningún test de la pieza C sería representativo. D2 después porque la pieza C
escribiría `"None"`. Luego C (destino), luego A (origen), luego B (la costura).

---

### Task 1: D1 — la property del NIF del colaborador es `nif_cif`, no `nif`

Medido el 2026-09-04: `GET /api/element_register/colaboradores/40?properties=nif` → **HTTP 500**, y
su mensaje enumera el contrato real, donde la property es `nif_cif`. Hoy
`resolver_parte("colaboradores", nif=…)` devuelve `sin_comprobar=('NIF (HTTP 500)',)` y
`_resolver_colaborador` levanta `IdentidadSinComprobar`: **la dedup por NIF del colaborador nunca ha
funcionado**, y falla cerrado abortando el alta.

**Files:**
- Modify: `core/sudespacho_relations.py:901-905` (el dict `_PROP_NIF`)
- Test: `tests/test_crm_colaborador_props.py` (crear)

**Interfaces:**
- Consumes: nada.
- Produces: `_PROP_NIF["colaboradores"] == "nif_cif"`. Lo consume `resolver_parte` (ya existente,
  línea 1056: `prop_nif = _PROP_NIF.get(elemento, "nif_cif")`) y las Tasks 3 y 4.

- [ ] **Step 1: Crear el fichero de test con la guarda de red y el primer test**

Crear `tests/test_crm_colaborador_props.py`:

```python
"""El contrato de `colaboradores` en el CRM, y la ficha que ya existe se COMPLETA.

El contrato no se supone: se le pidió al CRM el 2026-09-04 con una property inventada,
y su HTTP 500 lo enumera (método del §14.6 de INTEGRACION_SUDESPACHO.md):

    ccc, cp, direccion, email, fax, iva, movil, nacionalidad, nif_cif, nombre,
    notas, poblacion, provincia, telefono1, telefono2, telefono3, tipo, web

O sea: la property del NIF es `nif_cif`, igual que en el contrario. No `nif`.
"""
from unittest.mock import MagicMock, patch

import pytest


class FugaDeRedEnTest(BaseException):
    """No hereda de Exception a proposito: ningun `except Exception` puede tragarsela.

    `_completar_colaborador_existente` no lanza por diseno (perder el vinculo por no
    poder escribir un telefono seria peor que quedarse sin el telefono), asi que un
    AssertionError se lo tragaria su propio `except Exception` y la guarda quedaria
    INERTE mientras la escritura sale al tenant real.
    """


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    def _prohibido(metodo):
        def _f(*a, **k):
            destino = a[0] if a else k.get("url", "?")
            raise FugaDeRedEnTest(
                f"httpx.{metodo} salio a la red en un test ({destino!r}); "
                "mockea la funcion de core que la usa"
            )
        return _f

    for metodo in ("get", "post", "put", "delete", "patch", "request"):
        monkeypatch.setattr(f"httpx.{metodo}", _prohibido(metodo))


def test_la_guarda_de_red_no_es_atrapable_por_except_Exception():
    """Si esto falla, la guarda de este fichero es decorativa."""
    assert issubclass(FugaDeRedEnTest, BaseException)
    assert not issubclass(FugaDeRedEnTest, Exception)


class TestElContratoDeColaboradores:

    def test_el_NIF_del_colaborador_se_busca_por_nif_cif(self):
        """`nif` no existe en colaboradores: el CRM devuelve 500 y enumera el contrato."""
        from core.sudespacho_relations import _PROP_NIF
        assert _PROP_NIF["colaboradores"] == "nif_cif"

    def test_resolver_parte_consulta_la_property_nif_cif(self):
        """La frontera de verdad: que la property viaje a la consulta, no que el dict lo diga."""
        from core.sudespacho_relations import Consulta, resolver_parte
        buscar = MagicMock(return_value=Consulta(registros=[]))
        with patch("core.sudespacho_relations._buscar_registros", buscar):
            resolver_parte("colaboradores", nif="12345678Z", email="")

        propiedades = [c.kwargs.get("propiedad", (c.args + (None, None))[2])
                       for c in buscar.call_args_list]
        assert "nif_cif" in propiedades, f"consultó {propiedades!r}"
        assert "nif" not in propiedades
```

- [ ] **Step 2: Correr el test y verificar que falla**

```bash
.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t1
```

Esperado: FALLA. `test_el_NIF_del_colaborador_se_busca_por_nif_cif` con
`AssertionError: assert 'nif' == 'nif_cif'`.

> Si `test_resolver_parte_consulta_la_property_nif_cif` falla por la forma de leer el
> argumento `propiedad` de `_buscar_registros`, lee su firma real en
> `core/sudespacho_relations.py:940` y ajusta la extracción — el aserto que importa es que
> `"nif_cif"` viaje y `"nif"` no.

- [ ] **Step 3: Corregir `_PROP_NIF`**

En `core/sudespacho_relations.py`, sustituir el dict y su comentario:

```python
#: Propiedad que guarda el NIF, por elemento. El CRM no usa el mismo nombre en todos,
#: pero `colaboradores` SI usa el mismo que el contrario: se le preguntó al propio CRM
#: el 2026-09-04 con una property inventada y su 500 enumeró el contrato entero
#: (método del §14.6). Antes decía `nif` aquí, y como esa property NO EXISTE el CRM
#: devolvía 500 → `resolver_parte` marcaba el criterio `sin_comprobar` →
#: `_resolver_colaborador` abortaba el alta en cuanto la ficha traía un NIF. O sea: la
#: dedup por NIF del colaborador no ha funcionado nunca. El atlas ya lo decía bien;
#: era este dict el que lo contradecía.
_PROP_NIF = {
    "clientes_contrarios": "nif_cif",
    "clientes_propios": "nif_cif",
    "colaboradores": "nif_cif",
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

```bash
.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t1
```

Esperado: PASA (4 tests).

- [ ] **Step 5: Prueba de mutación — devolver `"nif"` y comprobar que muerde**

`git checkout` restaura desde el ÍNDICE, así que commitea el arreglo antes de mutar. Aquí basta
mutar, medir y restaurar en el mismo paso:

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/sudespacho_relations.py")
t = p.read_text(encoding="utf-8")
assert t.count('"colaboradores": "nif_cif",') == 1
p.write_text(t.replace('"colaboradores": "nif_cif",', '"colaboradores": "nif",'), encoding="utf-8")
print("MUTADO")
PY
.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t1m
```

Esperado: **2 fallos** (`test_el_NIF_...` y `test_resolver_parte_...`). Si no muerde, el test está
vacío: sospecha del test antes que del mutante.

Restaurar:

```bash
git checkout -- core/sudespacho_relations.py
```

- [ ] **Step 6: Commit**

```bash
git add core/sudespacho_relations.py tests/test_crm_colaborador_props.py
git commit -m "fix(crm): el NIF del colaborador es nif_cif — la property nif no existe

Medido contra el CRM el 2026-09-04: GET colaboradores/40?properties=nif da HTTP 500
y el mensaje enumera el contrato, donde la property es nif_cif. Con el valor viejo,
resolver_parte marcaba el criterio NIF sin_comprobar y _resolver_colaborador abortaba
el alta en cuanto la ficha traia un NIF: la dedup por NIF del colaborador no ha
funcionado nunca. El atlas ya lo decia bien; este dict lo contradecia."
```

---

### Task 2: D2 — una clave vacía del YAML es AUSENCIA, no la cadena `"None"`

`_colaborador_de` usa `str(d.get("movil", ""))`. Con `movil:` presente y sin valor, YAML da `None`,
`str(None)` es `"None"`, que es *truthy*, y `normalize_es_phone` no quita letras: devuelve `"None"`
intacto. La pieza C escribiría esa cadena en un campo vacío del CRM del cliente. Es el **mismo H-09**
que se cerró para `cp`/`provincia`/`telefono` del contrario y quedó abierto para el colaborador
entero — y para `contrario.movil`.

**Files:**
- Modify: `core/crm_ficha.py:25-42` (`_contrario_de`) y `core/crm_ficha.py:73-81` (`_colaborador_de`)
- Test: `tests/test_crm_ficha_yaml_none.py` (crear)

**Interfaces:**
- Consumes: `_escalar(valor: object, campo: str) -> str`, ya existente en
  `core/crm_ficha.py:45`. Rechaza `int`/`float`/`bool` con `ValueError` (el `cp: 01001` octal) y
  convierte `None` en `""`.
- Produces: `cargar_ficha_yaml(path) -> FichaCRMInput` donde ningún campo de un colaborador ni el
  `movil` del contrario puede valer `"None"`.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_crm_ficha_yaml_none.py`:

```python
"""Una clave preparada y vacia en el YAML significa «no hay dato», no la cadena "None".

`str(None)` es "None", que es *truthy*, y `normalize_es_phone` no quita letras: la
devuelve intacta. Sin esto, completar la ficha de un colaborador escribe la cadena
literal "None" en un campo vacio del CRM del cliente.

Es el mismo H-09 que se cerro para cp/provincia/telefono del contrario en el PR #275 y
quedo abierto para el colaborador entero — y para contrario.movil.
"""
import pytest

from core.crm_ficha import cargar_ficha_yaml


def _carga(tmp_path, cuerpo: str):
    y = tmp_path / "_ficha_crm.yaml"
    y.write_text(cuerpo, encoding="utf-8")
    return cargar_ficha_yaml(y)


class TestNingunCampoDelColaboradorPuedeValerNone:

    @pytest.mark.parametrize("clave", ["email", "movil", "telefono", "nif"])
    def test_una_clave_vacia_es_cadena_vacia(self, tmp_path, clave):
        ficha = _carga(tmp_path, f"colaboradores:\n  - nombre: ANA\n    {clave}:\n")
        col = ficha.colaboradores[0]
        assert getattr(col, clave) == "", f"{clave} salio {getattr(col, clave)!r}"

    def test_todas_vacias_a_la_vez(self, tmp_path):
        ficha = _carga(
            tmp_path,
            "colaboradores:\n  - nombre: ANA\n    email:\n    movil:\n"
            "    telefono:\n    nif:\n",
        )
        col = ficha.colaboradores[0]
        assert (col.email, col.movil, col.telefono, col.nif) == ("", "", "", "")

    def test_el_valor_bueno_sobrevive(self, tmp_path):
        ficha = _carga(
            tmp_path,
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.example\n"
            "    movil: '+34 612 345 678'\n    telefono: '912 345 678'\n",
        )
        col = ficha.colaboradores[0]
        assert col.email == "ana@engelvoelkers.example"
        assert col.movil == "612345678", "normalize_es_phone quita +34 y espacios"
        assert col.telefono == "912345678"

    def test_un_movil_sin_comillas_se_RECHAZA_en_vez_de_corromperse(self, tmp_path):
        """`movil: 0612345678` lo lee YAML como un entero y el cero inicial se pierde."""
        with pytest.raises(ValueError, match="comillas"):
            _carga(tmp_path, "colaboradores:\n  - nombre: ANA\n    movil: 0612345678\n")


class TestElMovilDelContrarioTampoco:
    """La misma frontera para el contrario: `movil` se quedo fuera del arreglo de H-09."""

    def test_movil_vacio_es_cadena_vacia(self, tmp_path):
        ficha = _carga(tmp_path, "contrario:\n  nombre: ANA\n  movil:\n")
        assert ficha.contrario.movil == ""

    @pytest.mark.parametrize("clave", ["email", "nombre_no", "direccion", "poblacion"])
    def test_las_otras_claves_de_texto_tampoco(self, tmp_path, clave):
        if clave == "nombre_no":
            pytest.skip("`nombre` vacio ya se rechaza con ValueError propio")
        ficha = _carga(tmp_path, f"contrario:\n  nombre: ANA\n  {clave}:\n")
        assert getattr(ficha.contrario, clave) == ""
```

- [ ] **Step 2: Correr el test y verificar que falla**

```bash
.venv/Scripts/python.exe -m pytest tests/test_crm_ficha_yaml_none.py -q -p no:randomly --basetemp=C:/t/t2
```

Esperado: FALLAN al menos `test_una_clave_vacia_es_cadena_vacia[movil]`,
`[telefono]`, `test_todas_vacias_a_la_vez`, `test_un_movil_sin_comillas_se_RECHAZA...` y
`TestElMovilDelContrarioTampoco::test_movil_vacio_es_cadena_vacia`, con `'None' == ''`.

- [ ] **Step 3: Pasar los dos constructores por `_escalar`**

En `core/crm_ficha.py`, sustituir `_colaborador_de` entera:

```python
def _colaborador_de(d: dict) -> NuevoColaborador:
    """El colaborador del YAML, sin que una clave vacia se convierta en un dato.

    Los cinco campos van por `_escalar` por la misma razon que los tres del contrario
    (H-09 del PR #275): `str(None)` es "None", que es *truthy*, y `normalize_es_phone`
    no quita letras, asi que esa cadena viajaba al CRM tal cual. Aqui se quedo abierto
    porque el arreglo se hizo campo a campo en el contrario en vez de cerrar la clase:
    cerrar una propiedad para un rol no la cierra para los demas.
    """
    if not d.get("nombre"):
        raise ValueError("colaborador sin 'nombre' en _ficha_crm.yaml")
    return NuevoColaborador(
        nombre=_escalar(d.get("nombre"), "colaborador.nombre"),
        email=_escalar(d.get("email"), "colaborador.email"),
        movil=_escalar(d.get("movil"), "colaborador.movil"),
        telefono=_escalar(d.get("telefono"), "colaborador.telefono"),
        nif=_escalar(d.get("nif"), "colaborador.nif"),
    )
```

Y en `_contrario_de`, **todas** las líneas que siguen con `str(...)` o `d.get(...)` crudo — las
ocho, no sólo las que el test nombra. Cerrar los campos que el test menciona y dejar los apellidos
fuera es cerrar el ejemplo y no la clase, que es justo el error que dejó este defecto abierto la
primera vez:

```python
        nombre=_escalar(d.get("nombre"), "contrario.nombre"),
        apellido1=_escalar(d.get("apellido1"), "contrario.apellido1"),
        apellido2=_escalar(d.get("apellido2"), "contrario.apellido2"),
        email=_escalar(d.get("email"), "contrario.email"),
        movil=_escalar(d.get("movil"), "contrario.movil"),
        nif=_escalar(d.get("nif"), "contrario.nif"),
        direccion=_escalar(d.get("direccion"), "contrario.direccion"),
        poblacion=_escalar(d.get("poblacion"), "contrario.poblacion"),
```

Y añadir el test que lo cobra, para que la clase quede protegida y no sólo los campos que se
mencionaron:

```python
    def test_NINGUN_campo_de_texto_del_contrario_puede_valer_None(self, tmp_path):
        """La clase entera, no los campos que alguien se acordo de listar."""
        claves = ["apellido1", "apellido2", "email", "movil", "nif", "direccion",
                  "poblacion", "cp", "provincia", "telefono"]
        cuerpo = "contrario:\n  nombre: ANA\n" + "".join(f"  {k}:\n" for k in claves)
        c = _carga(tmp_path, cuerpo).contrario
        malos = [k for k in claves if getattr(c, k) != ""]
        assert malos == [], f"estos salieron con valor: {malos}"
```

`_escalar` está definido **debajo** de `_contrario_de` en el fichero; en Python eso da igual porque
la resolución del nombre ocurre en la llamada, no en la definición. No hace falta moverlo.

- [ ] **Step 4: Correr el test y verificar que pasa**

```bash
.venv/Scripts/python.exe -m pytest tests/test_crm_ficha_yaml_none.py -q -p no:randomly --basetemp=C:/t/t2
```

Esperado: PASA.

- [ ] **Step 5: Correr los tests que ya cubrían este fichero, para no romper nada**

```bash
.venv/Scripts/python.exe -m pytest tests/test_crm_ficha_cli.py tests/test_crm_ficha_validacion.py tests/test_crm_ficha_validacion_r1.py tests/test_crm_ficha_campos_perdidos.py -q -p no:randomly --basetemp=C:/t/t2b
```

Esperado: PASA todo. Si algún test esperaba el `"None"`, ese test **defendía el defecto**: cámbialo
y anótalo en el commit.

- [ ] **Step 6: Commit**

```bash
git add core/crm_ficha.py tests/test_crm_ficha_yaml_none.py
git commit -m "fix(crm): una clave vacia del YAML es ausencia, no la cadena \"None\"

_colaborador_de usaba str(d.get(...)) en los cinco campos: con `movil:` presente y sin
valor, YAML da None, str(None) es \"None\" —truthy— y normalize_es_phone no quita letras,
asi que la cadena viajaba al CRM intacta. Completar una ficha existente la habria
escrito en un campo vacio del cliente.

Es el H-09 del PR #275, que se cerro campo a campo para cp/provincia/telefono del
contrario y dejo fuera contrario.movil y el colaborador entero. Se cierra la clase:
los dos constructores pasan por _escalar."
```

---

### Task 3: Pieza C.1 — leer y escribir la ficha de un colaborador

Los dos primitivos REST que hoy no existen. `get_colaborador` es el espejo de
`get_cliente_contrario` (`core/sudespacho_relations.py:1480`) con el contrato real de
`colaboradores`; `update_colaborador` el de `update_cliente_contrario` (línea 840).

**Files:**
- Modify: `core/sudespacho_relations.py` (añadir tras `_rest_post_colaborador`, ~línea 745)
- Test: `tests/test_crm_colaborador_props.py` (añadir clases)

**Interfaces:**
- Consumes: `_REST_BASE` (`"https://api-crm-commons-pro.sudespacho.biz"`, línea 111),
  `_REST_CREATE_COLABORADOR` (`"/api/element_register/colaboradores"`, línea 116),
  `_REST_TIMEOUT`, `SudespachoRelationsError`.
- Produces:
  - `_PROPS_COLABORADOR: tuple[str, ...]` — las properties que este módulo lee y escribe.
  - `get_colaborador(colab_id: str) -> dict[str, str]` — ficha aplanada `{property: value}`.
    Levanta `SudespachoRelationsError` si el HTTP no es 200, `ValueError` sin API key.
  - `update_colaborador(colab_id: str, cambios: dict) -> dict` — PUT. Levanta
    `SudespachoRelationsError` si el HTTP no es 200, `ValueError` si `cambios` está vacío.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir al final de `tests/test_crm_colaborador_props.py`:

```python
class TestLeerLaFichaDelColaborador:

    def test_pide_las_properties_explicitamente(self, monkeypatch):
        """El GET plano da HTTP 500: `?properties=` es obligatorio ([APER-26])."""
        from core import sudespacho_relations as sr

        capturado = {}

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return {"values": [{"property": {"name": "movil"}, "value": "612345678"}]}

        def _get(url, **kw):
            capturado["url"] = url
            return _R()

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "get", _get)
        plano = sr.get_colaborador("466")

        assert "/api/element_register/colaboradores/466" in capturado["url"]
        assert "properties=" in capturado["url"]
        assert plano == {"movil": "612345678"}

    def test_pide_TODO_el_conjunto_escribible_no_solo_lo_que_cambia(self, monkeypatch):
        """GET completo -> merge -> PUT completo: correcto si el PUT es parcial Y si es
        de reemplazo. Para `colaboradores` no esta medido cual de los dos es."""
        from core import sudespacho_relations as sr

        capturado = {}

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return {"values": []}

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "get",
                            lambda url, **kw: capturado.update(url=url) or _R())
        sr.get_colaborador("466")

        for prop in ("nombre", "email", "movil", "telefono1", "nif_cif"):
            assert prop in capturado["url"], f"falta {prop} en el GET"

    def test_una_property_que_el_CRM_no_tiene_NO_se_pide(self):
        """El contrato lo enumero el CRM. `nif` no esta, y pedirla da 500."""
        from core.sudespacho_relations import _PROPS_COLABORADOR
        assert "nif" not in _PROPS_COLABORADOR
        assert "nif_cif" in _PROPS_COLABORADOR
        assert "cargo" not in _PROPS_COLABORADOR, "no existe: `tipo` es un Select cerrado"

    def test_un_HTTP_no_200_levanta(self, monkeypatch):
        from core import sudespacho_relations as sr

        class _R:
            status_code = 500
            text = "boom"

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "get", lambda *a, **k: _R())
        with pytest.raises(sr.SudespachoRelationsError, match="500"):
            sr.get_colaborador("466")


class TestEscribirLaFichaDelColaborador:

    def test_es_PUT_al_endpoint_del_registro(self, monkeypatch):
        from core import sudespacho_relations as sr

        capturado = {}

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return {"values": [{"property": {"name": "movil"}, "value": "612345678"}]}

        def _put(url, **kw):
            capturado.update(url=url, json=kw.get("json"))
            return _R()

        monkeypatch.setenv("SUDESPACHO_API_KEY", "k")
        monkeypatch.setattr(sr.httpx, "put", _put)
        sr.update_colaborador("466", {"movil": "612345678"})

        assert capturado["url"].endswith("/api/element_register/colaboradores/466")
        assert capturado["json"] == {"movil": "612345678"}

    def test_cambios_vacio_es_un_error_del_llamador(self):
        from core import sudespacho_relations as sr
        with pytest.raises(ValueError, match="cambios"):
            sr.update_colaborador("466", {})
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t3
```

Esperado: FALLA con `AttributeError: module 'core.sudespacho_relations' has no attribute
'get_colaborador'` (y `_PROPS_COLABORADOR`, `update_colaborador`).

- [ ] **Step 3: Implementar los dos primitivos**

En `core/sudespacho_relations.py`, tras `_rest_post_colaborador` (justo antes del bloque de
comentario `# Creación de cliente contrario`), insertar:

```python
#: Las properties de `colaboradores` que este modulo lee y escribe. El contrato lo
#: enumero el propio CRM el 2026-09-04 con una property inventada (§14.6): ccc, cp,
#: direccion, email, fax, iva, movil, nacionalidad, nif_cif, nombre, notas, poblacion,
#: provincia, telefono1, telefono2, telefono3, tipo, web. Aqui van solo las que el
#: despacho usa: pedirlas todas gastaria ancho sin ganar nada, y `nacionalidad` esta
#: marcada como cuarentena-PII en el atlas.
#:
#: NO hay property de CARGO. `tipo` es un Select con enum cerrado (Sin Asignar /
#: Colaborador / Perito / Tercero), asi que un puesto ahi corrompe la taxonomia; por
#: eso el cargo se extrae al informe y no se escribe (decision de Nikolai, 2026-09-04).
_PROPS_COLABORADOR: tuple[str, ...] = (
    "nombre", "email", "movil", "telefono1", "telefono2", "telefono3",
    "nif_cif", "direccion", "poblacion", "cp", "provincia", "id",
)


def get_colaborador(colab_id: str) -> dict[str, str]:
    """Ficha de un colaborador, aplanada a `{property: value}`.

    El GET plano da HTTP 500: `?properties=` es obligatorio (`[APER-26]`). Se pide el
    conjunto escribible COMPLETO, no solo lo que se va a tocar, porque `_completar_*`
    hace GET -> merge -> PUT y para `colaboradores` **no esta medido** si el PUT es
    parcial o de reemplazo. Mandar el conjunto completo es correcto bajo las dos
    hipotesis; apostar por una y equivocarse borra los campos omitidos.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("SUDESPACHO_API_KEY no configurada")

    url = (f"{_REST_BASE}{_REST_CREATE_COLABORADOR}/{colab_id}"
           f"?properties={','.join(_PROPS_COLABORADOR)}")
    r = httpx.get(url, headers={"x-api-key": api_key, "Accept": "application/json"},
                  timeout=_REST_TIMEOUT)
    if r.status_code != 200:
        raise SudespachoRelationsError(
            f"REST GET colaboradores/{colab_id} -> HTTP {r.status_code}")
    return _parse_values(r.json())


def update_colaborador(colab_id: str, cambios: dict) -> dict:
    """PUT sobre la ficha de un colaborador. Devuelve el registro tal como responde.

    PUT y no PATCH (PATCH da 405, §10.7). El llamador decide QUE va en `cambios`;
    esta funcion no filtra ni completa.
    """
    if not cambios:
        raise ValueError("update_colaborador: 'cambios' no puede estar vacío")

    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("SUDESPACHO_API_KEY no configurada")

    url = f"{_REST_BASE}{_REST_CREATE_COLABORADOR}/{colab_id}"
    headers = {"x-api-key": api_key, "Content-Type": "application/json",
               "Accept": "application/json"}
    try:
        r = httpx.put(url, json=cambios, headers=headers, timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoRelationsError(
            f"REST PUT colaboradores/{colab_id} falló: {exc}") from exc

    if r.status_code == 200:
        try:
            return _parse_values(r.json())
        except Exception:  # noqa: BLE001 — cuerpo 200 no parseable
            return dict(cambios)

    try:
        detail = r.json().get("detail") or r.text[:300]
    except Exception:  # noqa: BLE001
        detail = r.text[:300]
    raise SudespachoRelationsError(
        f"REST PUT colaboradores/{colab_id} → HTTP {r.status_code}: {detail}")
```

> `_parse_values` ya existe en el módulo (`core/sudespacho_relations.py:447`, usado por
> `update_cliente_contrario`). Si su forma de aplanado no coincide con la de
> `get_cliente_contrario` (que aplana inline), usa `_parse_values` y ajusta el test: la firma
> pública es `dict[str, str]` en ambos casos.

- [ ] **Step 4: Correr y verificar que pasa**

```bash
.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t3
```

Esperado: PASA.

- [ ] **Step 5: Commit**

```bash
git add core/sudespacho_relations.py tests/test_crm_colaborador_props.py
git commit -m "feat(crm): leer y escribir la ficha de un colaborador (GET/PUT)

Los dos primitivos no existian: solo habia POST de creacion. get_colaborador pide el
conjunto escribible COMPLETO porque el GET plano da 500 y porque _completar_* hace
GET -> merge -> PUT: para `colaboradores` no esta medido si el PUT es parcial o de
reemplazo, y mandar el conjunto completo es correcto bajo las dos hipotesis.

El contrato de properties no se supone: lo enumero el CRM (§14.6). No incluye cargo."
```

---


### Task 4: Pieza C.2 — el colaborador que ya existe se COMPLETA, y las dos jurisdicciones a la vez

Espejo de `_completar_contrario_existente` (`core/sudespacho_relations.py:1439`). El gancho va en
un resolvedor **compartido** por `ensure_colaborador_vinculado` y
`ensure_colaborador_vinculado_judicial`, no copiado en las dos: el propio módulo ya lleva escrito, a
raíz de R1/H-05 del PR #275, que «añadir el contrario judicial y olvidar el colaborador judicial es
el mismo error de siempre: cerrar una propiedad para un rol no la cierra para los demás». Poner el
gancho dos veces es firmar la tercera aparición.

**Files:**
- Modify: `core/sudespacho_relations.py:2084-2145` (`ensure_colaborador_vinculado`) y
  `core/sudespacho_relations.py:2284-2312` (`ensure_colaborador_vinculado_judicial`)
- Modify: `core/sudespacho_relations.py` (añadir `_COMPLETABLES_COLABORADOR`,
  `_completar_colaborador_existente` y `_resolver_o_crear_colaborador` tras `_resolver_colaborador`)
- Test: `tests/test_crm_colaborador_props.py` (añadir clases)

**Interfaces:**
- Consumes: `get_colaborador`, `update_colaborador` (Task 3);
  `_resolver_colaborador(datos, *, client) -> str | None` (ya existente, línea 2033);
  `create_colaborador(datos, *, client) -> str` (línea 1604); `link_colaborador(exp_id, colab_id,
  *, client)` (línea 1993); `link_colaborador_judicial` (línea 2252); `_log` (el logger del módulo).
- Produces:
  - `_COMPLETABLES_COLABORADOR: tuple[tuple[str, str], ...]` — pares `(campo del DTO, property del CRM)`.
  - `_completar_colaborador_existente(colab_id: str, datos: NuevoColaborador) -> None` — no lanza.
  - `_resolver_o_crear_colaborador(datos: NuevoColaborador, *, client) -> tuple[str, bool]`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir al final de `tests/test_crm_colaborador_props.py`:

```python
class TestElColaboradorExistenteSeCOMPLETA:
    """Espejo del contrario (R1/H-07 del PR #275). El caso normal es que YA exista:
    el mismo consultor aparece en todos los casos de su Market Center."""

    @staticmethod
    def _datos():
        from core.sudespacho_relations import NuevoColaborador
        return NuevoColaborador(nombre="ANA", email="ana@engelvoelkers.example",
                                movil="612345678", telefono="912345678",
                                nif="12345678Z")

    def test_lo_que_falta_en_el_CRM_se_rellena(self):
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"nombre": "ANA", "email": "", "movil": "",
                                 "telefono1": "", "nif_cif": ""}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("466", False)
        cambios = actualizar.call_args.args[1]
        assert cambios["movil"] == "612345678"
        assert cambios["telefono1"] == "912345678", "el fijo va a telefono1"
        assert cambios["nif_cif"] == "12345678Z", "nif_cif, no nif"
        assert "cargo" not in cambios, "no existe esa property en el CRM"
        assert "tipo" not in cambios, "es un Select cerrado: un puesto ahi la corrompe"

    def test_lo_que_el_CRM_YA_tiene_no_se_pisa(self):
        """La ficha local aporta datos; no manda sobre lo que E&V corrigio alli."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"email": "otra@engelvoelkers.example",
                                 "movil": "600000000", "telefono1": "930000000",
                                 "nif_cif": "87654321X"}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())

        actualizar.assert_not_called()

    def test_rellena_SOLO_el_hueco_y_deja_el_resto(self):
        """El caso real medido en W-02Q38C: movil puesto, telefono1 vacio."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"email": "ana@engelvoelkers.example",
                                 "movil": "600000000", "telefono1": "",
                                 "nif_cif": ""}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())

        cambios = actualizar.call_args.args[1]
        assert set(cambios) == {"telefono1", "nif_cif"}
        assert "movil" not in cambios, "el CRM ya tenia uno distinto: no se toca"

    def test_un_valor_en_blanco_del_CRM_cuenta_como_VACIO(self):
        """Un campo con espacios es un campo vacio, no un dato que respetar. Y `None`
        tampoco: el CRM devuelve nulos en las properties sin valor."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"movil": "   ", "telefono1": None}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())

        cambios = actualizar.call_args.args[1]
        assert cambios["movil"] == "612345678"
        assert cambios["telefono1"] == "912345678"

    def test_si_no_se_puede_LEER_la_ficha_no_se_pierde_el_VINCULO(self):
        """Completar es un extra: perder el vinculo por un telefono seria peor."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        vincular = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   side_effect=RuntimeError("500")), \
             patch("core.sudespacho_relations.link_colaborador", vincular), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("466", False)
        vincular.assert_called_once()

    def test_si_no_se_puede_ESCRIBIR_tampoco_se_pierde_el_VINCULO(self):
        from core.sudespacho_relations import ensure_colaborador_vinculado
        vincular = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"movil": "", "telefono1": ""}), \
             patch("core.sudespacho_relations.update_colaborador",
                   side_effect=RuntimeError("400")), \
             patch("core.sudespacho_relations.link_colaborador", vincular), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("466", False)
        vincular.assert_called_once()

    def test_al_CREAR_uno_nuevo_no_se_completa_nada(self):
        """El POST ya lleva los campos: un PUT detras seria una peticion regalada."""
        from core.sudespacho_relations import ensure_colaborador_vinculado
        leer = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value=None), \
             patch("core.sudespacho_relations.create_colaborador", return_value="999"), \
             patch("core.sudespacho_relations.get_colaborador", leer), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            cid, creado = ensure_colaborador_vinculado("600", self._datos())

        assert (cid, creado) == ("999", True)
        leer.assert_not_called()


class TestLasDosJurisdiccionesSeCompletanIGUAL:
    """R1/H-05 midio que anadir algo al camino extrajudicial y olvidar el judicial es
    el modo de fallo recurrente de este modulo. El gancho va en el resolvedor
    COMPARTIDO, asi que esta simetria no es una coincidencia que haya que mantener."""

    @staticmethod
    def _datos():
        from core.sudespacho_relations import NuevoColaborador
        return NuevoColaborador(nombre="ANA", email="ana@engelvoelkers.example",
                                movil="612345678")

    def test_el_judicial_tambien_completa(self):
        from core.sudespacho_relations import ensure_colaborador_vinculado_judicial
        actualizar = MagicMock()
        with patch("core.sudespacho_relations._resolver_colaborador", return_value="466"), \
             patch("core.sudespacho_relations.get_colaborador",
                   return_value={"movil": ""}), \
             patch("core.sudespacho_relations.update_colaborador", actualizar), \
             patch("core.sudespacho_relations.link_colaborador_judicial", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado_judicial("700", self._datos())

        assert actualizar.call_args.args[1]["movil"] == "612345678"

    def test_las_dos_pasan_por_el_MISMO_resolvedor(self):
        """La frontera estructural: sin esto, alguien puede copiar el gancho en vez de
        compartirlo y el siguiente cambio vuelve a olvidar una de las dos ramas."""
        from core.sudespacho_relations import (ensure_colaborador_vinculado,
                                               ensure_colaborador_vinculado_judicial)
        resolver = MagicMock(return_value=("466", False))
        with patch("core.sudespacho_relations._resolver_o_crear_colaborador", resolver), \
             patch("core.sudespacho_relations.link_colaborador", MagicMock()), \
             patch("core.sudespacho_relations.link_colaborador_judicial", MagicMock()), \
             patch("core.sudespacho_relations.SudespachoLegacyClient", MagicMock()):
            ensure_colaborador_vinculado("600", self._datos())
            ensure_colaborador_vinculado_judicial("700", self._datos())

        assert resolver.call_count == 2, "las dos jurisdicciones lo usan"
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t4`

Esperado: FALLA. `test_lo_que_falta_en_el_CRM_se_rellena` porque nadie llama a
`update_colaborador`, y `test_las_dos_pasan_por_el_MISMO_resolvedor` con
`AttributeError: … has no attribute '_resolver_o_crear_colaborador'`.

- [ ] **Step 3: Implementar el completador y el resolvedor compartido**

En `core/sudespacho_relations.py`, tras `_resolver_colaborador` (que acaba con `return None`,
~línea 2082) y **antes** de `ensure_colaborador_vinculado`, insertar:

```python
#: Campos de la ficha que se COMPLETAN sobre un colaborador que ya existe, con su
#: nombre de property en el CRM. Solo se rellena lo que esta VACIO: la ficha local
#: aporta datos, no manda sobre lo que ya hay — E&V u otra sesion pueden haber
#: corregido algo ahi y pisarlo seria destruir trabajo ajeno.
#:
#: `telefono` -> `telefono1` y `nif` -> `nif_cif`: los nombres del DTO y los del CRM
#: no coinciden, y el segundo se comprobo preguntandole al CRM (§14.6), no leyendo
#: codigo. NO hay entrada de `cargo`: esa property no existe en `colaboradores`, y
#: `tipo` es un Select cerrado (Sin Asignar / Colaborador / Perito / Tercero).
_COMPLETABLES_COLABORADOR = (
    ("email", "email"),
    ("movil", "movil"),
    ("telefono", "telefono1"),
    ("nif", "nif_cif"),
)


def _completar_colaborador_existente(colab_id: str, datos: NuevoColaborador) -> None:
    """Rellena en el CRM los campos que la ficha trae y la ficha del CRM no tiene.

    Espejo de `_completar_contrario_existente`, y por el mismo motivo medido: anadir
    campos al DTO solo los hace llegar en el camino de CREACION, y con el colaborador
    ya existente —el caso normal, porque el mismo consultor aparece en todos los casos
    de su Market Center— `ensure_colaborador_vinculado` solo vinculaba.

    Medido el 2026-09-04 sobre los tres colaboradores vinculados a W-02Q38C: los tres
    con `telefono1` y `nif_cif` vacios, y uno de los tres sin movil.

    No lanza: completar la ficha es un extra sobre el vinculo, y perder el vinculo por
    no poder escribir un telefono seria peor que quedarse sin el telefono. Lo que no se
    pueda hacer se registra.
    """
    try:
        actual = get_colaborador(colab_id)
    except Exception as exc:  # noqa: BLE001
        _log.warning("no se pudo leer el colaborador %s para completarlo (%r): los "
                     "datos de la ficha que faltasen siguen sin llegar", colab_id, exc)
        return

    cambios: dict[str, str] = {}
    for campo, prop in _COMPLETABLES_COLABORADOR:
        valor = (getattr(datos, campo, "") or "").strip()
        if valor and not (actual.get(prop) or "").strip():
            cambios[prop] = valor

    if not cambios:
        return
    try:
        update_colaborador(colab_id, cambios)
        _log.info("colaborador %s completado con %s", colab_id, sorted(cambios))
    except Exception as exc:  # noqa: BLE001
        _log.warning("no se pudieron completar los campos %s del colaborador %s (%r)",
                     sorted(cambios), colab_id, exc)


def _resolver_o_crear_colaborador(
    datos: NuevoColaborador,
    *,
    client: SudespachoLegacyClient | None = None,
) -> tuple[str, bool]:
    """La parte de IDENTIDAD, compartida por las dos jurisdicciones.

    Compartida a proposito, no por ahorrar lineas: R1/H-05 del PR #275 midio que
    `ensure_colaborador_vinculado_judicial` seguia siendo email-only porque el cambio
    se hizo en la rama extrajudicial y la otra se quedo atras. Con el gancho de
    completar en un solo sitio, esa asimetria no puede volver a aparecer por olvido.
    """
    colab_id = _resolver_colaborador(datos, client=client)
    if colab_id is not None:
        _completar_colaborador_existente(colab_id, datos)
        return colab_id, False
    return create_colaborador(datos, client=client), True
```

Sustituir el cuerpo del `try` de **`ensure_colaborador_vinculado`** (los pasos 1-3, líneas
~2130-2140) por:

```python
    try:
        colab_id, created = _resolver_o_crear_colaborador(datos, client=client)
        link_colaborador(exp_id, colab_id, client=client)
        return colab_id, created
```

Y el del `try` de **`ensure_colaborador_vinculado_judicial`** por:

```python
    try:
        colab_id, created = _resolver_o_crear_colaborador(datos, client=client)
        link_colaborador_judicial(exp_id, colab_id, client=client)
        return colab_id, created
```

Los `finally` que cierran el `client` se dejan intactos en las dos.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t4`

Esperado: PASA.

- [ ] **Step 5: Correr lo que ya tocaba estas funciones**

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_ficha_cli.py tests/test_crm_dedup_incertidumbre.py tests/test_crm_ficha_validacion_r1.py -q -p no:randomly --basetemp=C:/t/t4b`

Esperado: PASA. Estos mockean `ensure_colaborador_vinculado` entero o `_resolver_colaborador`, así
que la refactorización no debería tocarlos. Si alguno rompe, dependía de la estructura interna: hay
que decidir si defendía algo real antes de cambiarlo.

- [ ] **Step 6: Commit del arreglo, ANTES de mutar**

`git checkout` restaura desde el índice, así que el arreglo tiene que estar commiteado para que las
mutaciones de los pasos 7 y 8 se puedan deshacer.

```bash
git add core/sudespacho_relations.py tests/test_crm_colaborador_props.py
git commit -m "feat(crm): el colaborador que ya existe se completa, y en las dos jurisdicciones"
```

- [ ] **Step 7: Mutación 1 — «sólo si está vacío» → «siempre»**

Es la frontera que protege los datos del cliente.

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/sudespacho_relations.py")
t = p.read_text(encoding="utf-8")
viejo = '        if valor and not (actual.get(prop) or "").strip():\n            cambios[prop] = valor'
nuevo = '        if valor:\n            cambios[prop] = valor'
n = t.count(viejo)
assert n == 2, f"esperaba 2 (contrario + colaborador), hay {n}"
# Solo el del colaborador: es el bloque que sigue a _COMPLETABLES_COLABORADOR.
i = t.index("_COMPLETABLES_COLABORADOR = (")
p.write_text(t[:i] + t[i:].replace(viejo, nuevo, 1), encoding="utf-8")
print("MUTADO")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t4m`

Esperado: **fallan DOS** — `test_lo_que_el_CRM_YA_tiene_no_se_pisa` y
`test_rellena_SOLO_el_hueco_y_deja_el_resto`. Si sólo cae uno, el otro no comprueba la frontera que
dice comprobar.

Restaurar: `git checkout -- core/sudespacho_relations.py`

- [ ] **Step 8: Mutación 2 — devolverle al judicial su resolución propia**

Reproduce el defecto histórico R1/H-05.

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/sudespacho_relations.py")
t = p.read_text(encoding="utf-8")
viejo = ("        colab_id, created = _resolver_o_crear_colaborador(datos, client=client)\n"
         "        link_colaborador_judicial(exp_id, colab_id, client=client)")
nuevo = ("        colab_id = _resolver_colaborador(datos, client=client)\n"
         "        created = False\n"
         "        if colab_id is None:\n"
         "            colab_id = create_colaborador(datos, client=client)\n"
         "            created = True\n"
         "        link_colaborador_judicial(exp_id, colab_id, client=client)")
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: el judicial vuelve a resolver por su cuenta")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaborador_props.py -q -p no:randomly --basetemp=C:/t/t4n`

Esperado: **fallan DOS** — `test_el_judicial_tambien_completa` y
`test_las_dos_pasan_por_el_MISMO_resolvedor`. Si no muerde, la simetría no está protegida y volverá
a romperse en el siguiente cambio.

Restaurar: `git checkout -- core/sudespacho_relations.py`

- [ ] **Step 9: Enmendar el commit con el mensaje completo**

```bash
git commit --amend -m "feat(crm): el colaborador que ya existe se completa, y en las dos jurisdicciones

Espejo de _completar_contrario_existente: rellena SOLO lo vacio, no lanza, y registra
lo que no pudo hacer. Medido en W-02Q38C: los tres colaboradores vinculados tienen
telefono1 y nif_cif vacios, y uno de los tres no tiene movil.

El gancho va en un _resolver_o_crear_colaborador COMPARTIDO por las dos jurisdicciones,
no copiado en las dos. R1/H-05 del PR #275 midio que el camino judicial se queda atras
cuando el cambio se hace solo en el extrajudicial; con un unico sitio esa asimetria no
puede volver por olvido. Dos mutantes lo comprueban: pisar lo que ya hay, y devolverle
al judicial su resolucion propia."
```

---

### Task 5: Pieza A.1 — localizar el bloque de firma, con el marcador fuera del camino crítico

**El hallazgo que fija esta task:** de los 6 `.eml` de W-02Q38C, **sólo 3 traen marcador de firma**
(`-- ` / «Enviado desde mi…»). Un localizador anclado al marcador pierde la mitad **en silencio**.

Lo que **sí** aparece en los 6 bloques de firma medidos es una **línea con la dirección corporativa**
(suelta, o tras `Mailto:`). Así que el ancla es el email y el marcador pasa a ser un **refinamiento**:
cuando existe entre el cuerpo y la línea del email, aprieta el límite superior del bloque para no
arrastrar prosa. La corroboración es obligatoria: una dirección suelta en medio de un texto no es una
firma.

**Files:**
- Create: `core/email_firmas.py`
- Test: `tests/test_email_firmas.py`

**Interfaces:**
- Consumes: `re`, `dataclasses`, `pathlib` (stdlib). **Nada de `core.sudespacho_*`**: esta pieza no
  conoce el CRM.
- Produces:
  - `desmarcar(texto: str) -> str` — quita las marcas de cita `>` de principio de línea.
    **NO quita los asteriscos de negrita**: la Task 7 los necesita para localizar la línea del nombre.
  - `BloqueFirma` (frozen dataclass): `texto: str`, `email: str`, `linea: int`, `fichero: str`,
    `procedencia: str`.
  - `localizar_bloques(texto: str, *, fichero: str = "") -> list[BloqueFirma]` — el `email` viene
    vacío en esta task; lo rellena la Task 6.
  - `DOMINIO_COLABORADOR = "engelvoelkers.com"`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_email_firmas.py`:

```python
"""Localizar la firma de un correo, sin fiarse del marcador.

Verdad de campo medida el 2026-09-04 sobre los 6 .eml de W-02Q38C: SOLO 3 traen el
marcador (`-- ` / «Enviado desde mi…»). Los otros 3 llevan la firma al final del cuerpo
sin marcador ninguno. Anclar en el marcador pierde la mitad EN SILENCIO.

Los esqueletos de abajo son los reales; los datos, inventados.
"""
import pytest

from core.email_firmas import BloqueFirma, desmarcar, localizar_bloques

# --- Plantilla «Barcelona»: nombre en negrita, cargo en linea suelta, Telf + Movil ---
FIRMA_BCN = """\
ENGEL&VÖLKERS
*Ana Ejemplo Ficticia*
Asesora Inmobiliaria

EV MMC SPAIN, S.L.U.
Avinguda Falsa, 12, planta baja
08301 Ciudad Inventada

Telf: +34 93 111 22 33

Móvil: *612 34 56 78*

ana@engelvoelkers.com
"""

# --- Plantilla «Madrid»: nombre y cargo en negrita, Tel. Fijo con extension, sin movil ---
FIRMA_MAD = """\
*Berta Ejemplo Ficticia *

*Técnico de PBC.*

ENGEL&VÖLKERS

*Calle Falsa 34 planta 5ª, Madrid 28001, España*
Tel. Fijo: +34 912 345 678 / Ext. 1234
Mailto: berta@engelvoelkers.com

Este correo electrónico así como cualquier anexo adjunto son confidenciales.
"""


class TestDesmarcar:

    def test_quita_las_marcas_de_cita(self):
        assert desmarcar("> hola\n> mundo") == "hola\nmundo"

    def test_quita_marcas_anidadas(self):
        assert desmarcar(">> hola") == "hola"

    def test_NO_quita_los_asteriscos_de_negrita(self):
        """La Task 7 los necesita para saber cual es la linea del nombre."""
        assert desmarcar("> *Ana*") == "*Ana*"

    def test_un_mayor_que_a_media_linea_no_se_toca(self):
        assert desmarcar("a > b") == "a > b"


class TestElMarcadorNoEsNecesario:
    """El hallazgo H-01: 3 de 6 no lo traen."""

    def test_una_firma_SIN_marcador_se_encuentra(self):
        cuerpo = "Te paso el domicilio.\n\nSaludos.\n\n" + FIRMA_BCN
        bloques = localizar_bloques(cuerpo, fichero="a.eml")
        assert len(bloques) >= 1
        assert "Móvil:" in bloques[0].texto

    def test_una_firma_CON_marcador_se_encuentra(self):
        cuerpo = "Adjunto la oferta.\n\n-- \n" + FIRMA_BCN
        bloques = localizar_bloques(cuerpo, fichero="b.eml")
        assert len(bloques) >= 1
        assert "Móvil:" in bloques[0].texto

    @pytest.mark.parametrize("marcador", ["-- ", "--", "Enviado desde mi iPhone",
                                          "Sent from my iPad", "Obtener Outlook para Android"])
    def test_los_marcadores_conocidos_no_estorban(self, marcador):
        cuerpo = f"Texto.\n\n{marcador}\n" + FIRMA_BCN
        assert localizar_bloques(cuerpo, fichero="c.eml")

    def test_el_marcador_APRIETA_el_limite_superior(self):
        """Con marcador, la prosa de encima no entra en el bloque."""
        cuerpo = "PROSA QUE NO ES FIRMA\n\n-- \n" + FIRMA_BCN
        bloque = localizar_bloques(cuerpo, fichero="d.eml")[0]
        assert "PROSA QUE NO ES FIRMA" not in bloque.texto

    def test_sin_marcador_el_bloque_se_limita_a_una_ventana(self):
        """Sin marcador no se puede ser exacto, pero tampoco se arrastra el correo entero."""
        cuerpo = "LINEA MUY LEJANA\n" + ("\n" * 30) + FIRMA_BCN
        bloque = localizar_bloques(cuerpo, fichero="e.eml")[0]
        assert "LINEA MUY LEJANA" not in bloque.texto


class TestLaCorroboracionEsOBLIGATORIA:
    """Una direccion suelta en un texto no es una firma. Sin esta puerta, cualquier
    correo que MENCIONE a un consultor produciria una «firma» suya inventada."""

    def test_una_direccion_suelta_NO_es_una_firma(self):
        cuerpo = ("Hola, escribe a ana@engelvoelkers.com y que te lo confirme ella.\n"
                  "Un saludo.\n")
        assert localizar_bloques(cuerpo, fichero="f.eml") == []

    def test_una_direccion_con_la_marca_corporativa_SI(self):
        cuerpo = "ENGEL&VÖLKERS\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="g.eml")

    def test_una_direccion_con_etiqueta_de_telefono_SI(self):
        cuerpo = "Móvil: 612 34 56 78\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="h.eml")

    def test_una_direccion_de_OTRO_dominio_no_se_mira(self):
        """El colaborador es personal de E&V. Un tercero no entra por aqui."""
        cuerpo = "ENGEL&VÖLKERS\nMóvil: 612 34 56 78\nalguien@otraempresa.example\n"
        assert localizar_bloques(cuerpo, fichero="i.eml") == []


class TestLoQueDevuelve:

    def test_es_un_BloqueFirma_con_fichero_y_linea(self):
        cuerpo = "Hola.\n\n" + FIRMA_BCN
        bloque = localizar_bloques(cuerpo, fichero="j.eml")[0]
        assert isinstance(bloque, BloqueFirma)
        assert bloque.fichero == "j.eml"
        assert bloque.linea >= 1, "1-indexed, para poder citarlo en el informe"

    def test_la_plantilla_de_Madrid_tambien(self):
        bloque = localizar_bloques(FIRMA_MAD, fichero="k.eml")[0]
        assert "Tel. Fijo:" in bloque.texto
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t5`

Esperado: FALLA en la colección con `ModuleNotFoundError: No module named 'core.email_firmas'`.

- [ ] **Step 3: Crear `core/email_firmas.py`**

```python
"""Leer la firma de un correo: quien firma, con que telefono y con que cargo.

NO conoce el CRM. Devuelve lo que dice el correo, con la constancia de lo que no pudo
leer; quien decide que hacer con eso es `scripts/crm_colaboradores_firmas.py`.

Verdad de campo que fija el diseno, medida el 2026-09-04 sobre los 6 `.eml` de W-02Q38C:

- **Solo 3 de 6 traen marcador de firma.** Anclar el localizador en el marcador pierde la
  mitad en silencio. Lo que aparece en los 6 bloques es una **linea con la direccion
  corporativa**, asi que el ancla es esa y el marcador solo aprieta el limite superior.
- **La firma del cuerpo NO es la del `From:`.** En 2 de los 6 pertenece a otra persona
  (un reenvio, y un bloque citado). Por eso la atribucion sale del email de DENTRO del
  bloque, y un bloque sin email no se atribuye a nadie.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

#: El colaborador es personal propio del cliente (E&V). Una direccion de otro dominio
#: no se mira: un tercero de la operacion no es un colaborador del despacho.
DOMINIO_COLABORADOR = "engelvoelkers.com"

#: Cuantas lineas hacia atras se mira desde la linea del email cuando NO hay marcador.
#: Las dos plantillas medidas caben en 12; con mas se empieza a arrastrar prosa.
_VENTANA_ATRAS = 12
#: Y cuantas hacia delante: en la plantilla de Barcelona el email va al final, pero
#: queda un `<direccion>` de cortesia detras.
_VENTANA_ADELANTE = 4

_RE_CITA = re.compile(r"(?m)^\s*>+\s?")

_RE_MARCADOR = re.compile(
    r"(?im)^\s*(?:--\s*|enviado desde mi.*|sent from my.*|obtener outlook.*|get outlook.*)$"
)

_RE_EMAIL_COLAB = re.compile(
    r"[\w.+-]+@" + DOMINIO_COLABORADOR.replace(".", r"\."), re.IGNORECASE
)

#: Que convierte una direccion en una FIRMA. Sin al menos una de estas, una direccion
#: suelta en un texto produciria una «firma» inventada de quien solo se menciona.
_RE_CORROBORA = re.compile(
    r"(?im)engel\s*&?\s*v[öo]lkers"
    r"|ev\s+mmc\s+spain"
    r"|^\s*\*?\s*(?:telf|tel[ée]fono|tel\.|m[óo]vil|movil|mobile)\b"
)


def desmarcar(texto: str) -> str:
    """Quita las marcas de cita `>` del principio de cada linea.

    **No toca los asteriscos de negrita**: `leer_campos` los necesita para localizar la
    linea del nombre, que es lo que posiciona el cargo (que no tiene etiqueta).
    """
    return _RE_CITA.sub("", texto or "")


@dataclass(frozen=True)
class BloqueFirma:
    """Un bloque que parece una firma, con de donde salio.

    `procedencia` la rellena `atribuir` (Task 6): `"directo"` o `"citado"`.
    """
    texto: str
    email: str = ""
    linea: int = 0
    fichero: str = ""
    procedencia: str = "directo"


def localizar_bloques(texto: str, *, fichero: str = "") -> list[BloqueFirma]:
    """Los bloques que parecen una firma, uno por linea con direccion corroborada.

    Un mismo correo puede dar varios bloques para la misma persona (la plantilla de
    Barcelona repite la direccion al final); `consolidar` los une.
    """
    lineas = texto.splitlines()
    marcadores = [i for i, ln in enumerate(lineas) if _RE_MARCADOR.match(ln)]

    bloques: list[BloqueFirma] = []
    for i, linea in enumerate(lineas):
        if not _RE_EMAIL_COLAB.search(linea):
            continue

        # El marcador mas cercano por encima aprieta el limite superior; si no hay,
        # se usa una ventana fija. Sin limite se arrastraria el correo entero.
        previos = [m for m in marcadores if m < i]
        inicio = max(previos[-1], i - _VENTANA_ATRAS) if previos else max(0, i - _VENTANA_ATRAS)
        fin = min(len(lineas), i + 1 + _VENTANA_ADELANTE)
        cuerpo = "\n".join(lineas[inicio:fin])

        if not _RE_CORROBORA.search(cuerpo):
            continue
        bloques.append(BloqueFirma(texto=cuerpo, linea=inicio + 1, fichero=fichero))
    return bloques
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t5`

Esperado: PASA.

> Si `test_el_marcador_APRIETA_el_limite_superior` falla, es que `_VENTANA_ATRAS` alcanza por
> encima del marcador: `max(previos[-1], …)` es lo que lo impide, comprueba que el `max` no se ha
> escrito como `min`.

- [ ] **Step 5: Commit**

```bash
git add core/email_firmas.py tests/test_email_firmas.py
git commit -m "feat(firmas): localizar el bloque de firma sin depender del marcador

De los 6 .eml de W-02Q38C solo 3 traen marcador (`-- ` / «Enviado desde mi…»): un
localizador anclado ahi pierde la mitad EN SILENCIO. Lo que si aparece en los 6 es una
linea con la direccion corporativa, asi que el ancla es esa y el marcador pasa a ser un
refinamiento del limite superior.

La corroboracion (marca corporativa o etiqueta de telefono) es obligatoria: sin ella,
cualquier correo que MENCIONE a un consultor produciria una firma suya inventada."
```

- [ ] **Step 6: Mutación — quitar la corroboración**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = ("        if not _RE_CORROBORA.search(cuerpo):\n"
         "            continue\n")
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, ""), encoding="utf-8")
print("MUTADO: cualquier direccion vale como firma")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t5m`

Esperado: **falla** `test_una_direccion_suelta_NO_es_una_firma`.

Restaurar: `git checkout -- core/email_firmas.py`

- [ ] **Step 7: Mutación — quitar el filtro de dominio**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = 'r"[\\w.+-]+@" + DOMINIO_COLABORADOR.replace(".", r"\\.")'
assert t.count(viejo) == 1, t.count(viejo)
p.write_text(t.replace(viejo, 'r"[\\w.+-]+@[\\w.-]+"'), encoding="utf-8")
print("MUTADO: cualquier dominio")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t5n`

Esperado: **falla** `test_una_direccion_de_OTRO_dominio_no_se_mira`.

Restaurar: `git checkout -- core/email_firmas.py`

---

### Task 6: Pieza A.2 — la atribución, que es el guard central de todo el trabajo

**El hallazgo que fija esta task, y el que más importa de los siete:** en 2 de los 6 `.eml` medidos,
**la firma del cuerpo no pertenece al remitente**. Uno es un reenvío; en el otro la firma va dentro
de un bloque citado `> `. Atribuir «firma al final del cuerpo → `From:`» **escribe el teléfono de
una persona en la ficha de otra**, en el CRM del cliente.

Es exactamente el peligro que `core/email_atomize/historial.py` evita truncando en el marcador para
que la firma no robe la atribución del remitente.

**Files:**
- Modify: `core/email_firmas.py`
- Test: `tests/test_email_firmas.py`

**Interfaces:**
- Consumes: `BloqueFirma`, `localizar_bloques`, `desmarcar`, `_RE_EMAIL_COLAB` (Task 5).
- Produces:
  - `zonas_citadas(texto: str) -> list[tuple[int, int]]` — rangos de línea (0-indexed,
    fin exclusivo) con marca de cita.
  - `atribuir(bloques: list[BloqueFirma], *, texto_original: str) -> list[BloqueFirma]` —
    devuelve los bloques con `email` y `procedencia` rellenos; **descarta los que no tienen email
    dentro** y los cuenta aparte.
  - `PROCEDENCIA_DIRECTO = "directo"`, `PROCEDENCIA_CITADO = "citado"`.
  - `extraer_bloques(texto: str, *, fichero: str = "") -> tuple[list[BloqueFirma], int]` — la
    composición: localizar + atribuir. El `int` es cuántos bloques quedaron **sin atribuir**.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_email_firmas.py`:

```python
from core.email_firmas import (PROCEDENCIA_CITADO, PROCEDENCIA_DIRECTO,
                               extraer_bloques, zonas_citadas)


class TestLaFirmaNoEsLaDelRemitente:
    """EL GUARD CENTRAL. Medido: en 2 de los 6 .eml de W-02Q38C la firma del cuerpo
    pertenece a otra persona. Atribuir por cabecera escribe el telefono de A en la
    ficha de B, en el CRM del cliente."""

    def test_la_atribucion_sale_del_email_de_DENTRO_del_bloque(self):
        """El caso del REENVIO: `From:` es una persona, la firma es de otra."""
        cuerpo = "Te reenvío lo que me manda ella.\n\n" + FIRMA_BCN
        bloques, sin_atribuir = extraer_bloques(cuerpo, fichero="a.eml")

        assert [b.email for b in bloques] == ["ana@engelvoelkers.com"]
        assert sin_atribuir == 0

    def test_el_From_NO_influye_en_la_atribucion(self):
        """`extraer_bloques` no recibe el `From:`: no puede equivocarse con el."""
        import inspect
        firma = inspect.signature(extraer_bloques)
        assert "from" not in " ".join(firma.parameters).lower(), (
            "si el remitente entra aquí, alguien acabará atribuyendo por él")

    def test_un_bloque_SIN_email_dentro_no_se_atribuye_a_nadie(self):
        """No se sabe de quien es. No se propone nada, y se CUENTA."""
        cuerpo = "ENGEL&VÖLKERS\n*Ana Ejemplo*\nAsesora\nMóvil: 612 34 56 78\n"
        bloques, sin_atribuir = extraer_bloques(cuerpo, fichero="b.eml")
        assert bloques == []
        assert sin_atribuir == 0, "sin email no hay ni ancla: no llega a ser bloque"

    def test_dos_firmas_distintas_en_un_correo_se_separan(self):
        cuerpo = FIRMA_BCN + "\n\n" + FIRMA_MAD
        bloques, _ = extraer_bloques(cuerpo, fichero="c.eml")
        assert {b.email for b in bloques} == {"ana@engelvoelkers.com",
                                              "berta@engelvoelkers.com"}


class TestZonasCitadas:

    def test_una_zona_citada_se_detecta(self):
        texto = "hola\n> citado\n> mas citado\nadios"
        assert zonas_citadas(texto) == [(1, 3)]

    def test_sin_citas_no_hay_zonas(self):
        assert zonas_citadas("hola\nadios") == []

    def test_dos_zonas_separadas(self):
        texto = "a\n> uno\nb\n> dos"
        assert zonas_citadas(texto) == [(1, 2), (3, 4)]


class TestLaProcedenciaSeRegistra:
    """Un bloque citado es MAS ANTIGUO. La consolidacion (Task 8) lo usa para decidir
    cuando dos valores discrepan; aqui solo se registra con fidelidad."""

    def test_una_firma_en_el_cuerpo_es_directa(self):
        bloques, _ = extraer_bloques("Hola.\n\n" + FIRMA_BCN, fichero="a.eml")
        assert bloques[0].procedencia == PROCEDENCIA_DIRECTO

    def test_una_firma_dentro_de_un_bloque_citado_es_citada(self):
        """El segundo caso real: la firma llega dentro del `> ` de la respuesta."""
        citado = "\n".join("> " + ln for ln in FIRMA_BCN.splitlines())
        cuerpo = "Conforme, lo vemos mañana.\n\n" + citado + "\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="b.eml")

        assert [b.email for b in bloques] == ["ana@engelvoelkers.com"]
        assert bloques[0].procedencia == PROCEDENCIA_CITADO

    def test_la_firma_citada_se_lee_DESMARCADA(self):
        """Con las marcas `>` puestas, las etiquetas de telefono no casan."""
        citado = "\n".join("> " + ln for ln in FIRMA_BCN.splitlines())
        bloques, _ = extraer_bloques(citado, fichero="c.eml")
        assert not bloques[0].texto.lstrip().startswith(">")
        assert "Móvil:" in bloques[0].texto
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t6`

Esperado: FALLA en la colección con `ImportError: cannot import name 'extraer_bloques'`.

- [ ] **Step 3: Implementar la atribución**

Añadir a `core/email_firmas.py`, tras `localizar_bloques`:

```python
PROCEDENCIA_DIRECTO = "directo"
PROCEDENCIA_CITADO = "citado"


def zonas_citadas(texto: str) -> list[tuple[int, int]]:
    """Rangos de linea (0-indexed, fin exclusivo) que llegan con marca de cita.

    Se calculan sobre el texto ORIGINAL, antes de desmarcar: despues ya no se distingue
    lo citado de lo escrito.
    """
    zonas: list[tuple[int, int]] = []
    inicio: int | None = None
    for i, ln in enumerate(texto.splitlines()):
        if _RE_CITA.match(ln):
            if inicio is None:
                inicio = i
        elif inicio is not None:
            zonas.append((inicio, i))
            inicio = None
    if inicio is not None:
        zonas.append((inicio, len(texto.splitlines())))
    return zonas


def _en_zona_citada(linea0: int, zonas: list[tuple[int, int]]) -> bool:
    return any(a <= linea0 < b for a, b in zonas)


def atribuir(bloques: list[BloqueFirma], *,
             texto_original: str) -> tuple[list[BloqueFirma], int]:
    """Pone a cada bloque el email de QUIEN FIRMA, y su procedencia.

    **El email sale de DENTRO del bloque, nunca de la cabecera `From:`.** Medido el
    2026-09-04: en 2 de los 6 .eml de W-02Q38C la firma del cuerpo pertenece a otra
    persona (un reenvio, y un bloque citado). Atribuir por cabecera escribiria el
    telefono de una persona en la ficha de otra, en el CRM del cliente.

    Por eso esta funcion **no recibe el remitente**: no es que decida ignorarlo, es que
    no lo tiene. Un bloque sin email dentro se descarta y se cuenta.
    """
    zonas = zonas_citadas(texto_original)
    atribuidos: list[BloqueFirma] = []
    sin_atribuir = 0
    for b in bloques:
        m = _RE_EMAIL_COLAB.search(b.texto)
        if m is None:
            sin_atribuir += 1
            continue
        procedencia = (PROCEDENCIA_CITADO if _en_zona_citada(b.linea - 1, zonas)
                       else PROCEDENCIA_DIRECTO)
        atribuidos.append(BloqueFirma(
            texto=b.texto, email=m.group(0).lower(), linea=b.linea,
            fichero=b.fichero, procedencia=procedencia,
        ))
    return atribuidos, sin_atribuir


def extraer_bloques(texto: str, *,
                    fichero: str = "") -> tuple[list[BloqueFirma], int]:
    """Localizar + atribuir. El `int` son los bloques que quedaron sin atribuir.

    Las zonas citadas se calculan sobre el texto ORIGINAL y la busqueda sobre el
    DESMARCADO: con las marcas `>` puestas, las etiquetas de telefono no casan con sus
    anclas de principio de linea.
    """
    bloques = localizar_bloques(desmarcar(texto), fichero=fichero)
    return atribuir(bloques, texto_original=texto)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t6`

Esperado: PASA.

> `desmarcar` no cambia el número de líneas (sustituye la marca, no la línea), así que la línea del
> bloque desmarcado y la del original son la misma y `_en_zona_citada` puede cruzarlas. Si algún
> test de procedencia falla, comprueba que `_RE_CITA` no lleve `\n` en la clase de caracteres.

- [ ] **Step 5: Commit**

```bash
git add core/email_firmas.py tests/test_email_firmas.py
git commit -m "feat(firmas): atribuir por el email de DENTRO del bloque, nunca por el From:

El hallazgo que mas importa de los siete: en 2 de los 6 .eml de W-02Q38C la firma del
cuerpo NO es la del remitente —uno es un reenvio, y en el otro la firma llega dentro de
un bloque citado—. Atribuir «firma al final del cuerpo -> From:» escribe el telefono de
una persona en la ficha de OTRA, en el CRM del cliente.

`extraer_bloques` no recibe el remitente: no es que decida ignorarlo, es que no lo
tiene. Un bloque sin email dentro se descarta y se cuenta.

La procedencia (directo/citado) se registra porque un bloque citado es mas antiguo y la
consolidacion lo necesita para decidir cuando dos valores discrepan."
```

- [ ] **Step 6: Mutación — atribuir por el `From:` (el mutante que reproduce el defecto)**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = """        m = _RE_EMAIL_COLAB.search(b.texto)
        if m is None:
            sin_atribuir += 1
            continue"""
nuevo = """        m = _RE_EMAIL_COLAB.search(b.texto) or _RE_EMAIL_COLAB.search(texto_original)
        if m is None:
            sin_atribuir += 1
            continue"""
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: cae al primer email del correo, que es el del From:")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t6m`

Esperado: **falla** `test_un_bloque_SIN_email_dentro_no_se_atribuye_a_nadie`.

> Este mutante es más débil de lo que parece, porque los fixtures no llevan cabecera `From:`. Si
> quieres el mutante fuerte, hazlo en la Task 9, donde el CLI sí lee el `.eml` completo: el test
> `test_el_From_de_un_reenvio_no_recibe_el_telefono_de_otro` es el que lo cobra. **Anótalo**: aquí
> la cobertura de esa frontera es parcial, y no se declara cerrada hasta la Task 9.

Restaurar: `git checkout -- core/email_firmas.py`

- [ ] **Step 7: Mutación — leer el texto sin desmarcar**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = "    bloques = localizar_bloques(desmarcar(texto), fichero=fichero)"
nuevo = "    bloques = localizar_bloques(texto, fichero=fichero)"
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: sin desmarcar")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t6n`

Esperado: **fallan** `test_una_firma_dentro_de_un_bloque_citado_es_citada` y
`test_la_firma_citada_se_lee_DESMARCADA`. Es la frontera que hace legible la mitad citada del
corpus.

Restaurar: `git checkout -- core/email_firmas.py`

---

### Task 7: Pieza A.3 — leer móvil, fijo y cargo en las dos plantillas, con veredicto por campo

Tres cosas que la verdad de campo obliga:

1. **Los valores llegan sucios:** `+34`, espacios, y **envueltos en asteriscos** (`Móvil: *612 34 56
   78*`) porque la negrita HTML degrada a asteriscos en el `text/plain`. `normalize_es_phone` no
   quita letras ni asteriscos, así que hay que limpiar antes.
2. **El fijo de la plantilla de Madrid trae extensión:** `Tel. Fijo: +34 912 345 678 / Ext. 1234`.
   La extensión no es parte del número.
3. **El cargo no tiene etiqueta.** En las dos plantillas es la primera línea no vacía **después de
   la línea del nombre**, y la línea del nombre es la primera **enteramente en negrita**. Por eso
   `desmarcar` no quita los asteriscos.

Y la frontera del spec §6: **`FIRMA_SIN_CAMPO` no es «no tiene».** La plantilla de Madrid no lleva
móvil; eso no autoriza a escribir que esa persona no tiene móvil.

**Files:**
- Modify: `core/email_firmas.py`
- Test: `tests/test_email_firmas.py`

**Interfaces:**
- Consumes: `BloqueFirma` (Task 5); `normalize_es_phone` de `core/utils.py:28`.
- Produces:
  - `VEREDICTO_ENCONTRADO`, `VEREDICTO_FIRMA_SIN_CAMPO`, `VEREDICTO_SIN_FIRMA`,
    `VEREDICTO_NO_ATRIBUIBLE`, `VEREDICTO_NO_LEIBLE`, `VEREDICTO_CONFLICTO` — constantes `str`.
  - `DatosFirma` (frozen dataclass): `email: str`, `movil: str`, `telefono: str`, `cargo: str`,
    `procedencia: str`, `fichero: str`, `linea: int`.
  - `limpiar_telefono(valor: str) -> str`.
  - `leer_campos(bloque: BloqueFirma) -> DatosFirma`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_email_firmas.py`:

```python
from core.email_firmas import DatosFirma, leer_campos, limpiar_telefono


class TestLimpiarTelefono:
    """`normalize_es_phone` no quita letras ni asteriscos: hay que limpiar antes."""

    @pytest.mark.parametrize("crudo,esperado", [
        ("*612 34 56 78*", "612345678"),
        ("+34 93 111 22 33", "931112233"),
        ("612.34.56.78", "612345678"),
        ("<612345678>", "612345678"),
        ("+34 912 345 678 / Ext. 1234", "912345678"),
        ("912 345 678 / Ext. 1234", "912345678"),
        ("  612345678  ", "612345678"),
    ])
    def test_los_casos_medidos(self, crudo, esperado):
        assert limpiar_telefono(crudo) == esperado

    def test_la_extension_no_es_parte_del_numero(self):
        """El CRM exige 9 digitos; con la extension pegada da HTTP 400 ([APER-14])."""
        assert limpiar_telefono("+34 912 345 678 / Ext. 1234") == "912345678"

    def test_un_valor_sin_digitos_no_produce_un_telefono(self):
        assert limpiar_telefono("*") == ""
        assert limpiar_telefono("None") == ""
        assert limpiar_telefono("") == ""

    def test_un_numero_extranjero_no_se_mutila(self):
        """`normalize_es_phone` deja los `+33…` intactos salvo separadores."""
        assert limpiar_telefono("+33 1 23 45 67 89") == "+33123456789"


class TestLeerLosCamposDeLaPlantillaDeBarcelona:

    @staticmethod
    def _datos():
        bloques, _ = extraer_bloques("Hola.\n\n" + FIRMA_BCN, fichero="a.eml")
        return leer_campos(bloques[0])

    def test_el_movil(self):
        assert self._datos().movil == "612345678"

    def test_el_fijo_va_a_telefono(self):
        assert self._datos().telefono == "931112233"

    def test_el_cargo_es_la_linea_tras_el_nombre_en_negrita(self):
        """No tiene etiqueta: se posiciona. Aqui el cargo NO va en negrita."""
        assert self._datos().cargo == "Asesora Inmobiliaria"

    def test_el_email_y_la_procedencia_viajan(self):
        d = self._datos()
        assert d.email == "ana@engelvoelkers.com"
        assert d.procedencia == PROCEDENCIA_DIRECTO
        assert (d.fichero, d.linea) == ("a.eml", d.linea) and d.linea >= 1


class TestLeerLosCamposDeLaPlantillaDeMadrid:

    @staticmethod
    def _datos():
        bloques, _ = extraer_bloques(FIRMA_MAD, fichero="b.eml")
        return leer_campos(bloques[0])

    def test_el_fijo_con_extension(self):
        assert self._datos().telefono == "912345678"

    def test_el_cargo_SI_va_en_negrita_en_esta_plantilla(self):
        assert self._datos().cargo == "Técnico de PBC."

    def test_NO_HAY_MOVIL_y_eso_no_es_lo_mismo_que_no_tenerlo(self):
        """La frontera del §6 del spec: esta plantilla corporativa simplemente no lo
        incluye. El campo sale vacio; QUIEN lo interprete es la Task 8."""
        assert self._datos().movil == ""

    def test_la_razon_social_no_se_confunde_con_el_cargo(self):
        assert "ENGEL" not in self._datos().cargo

    def test_la_direccion_no_se_confunde_con_el_cargo(self):
        assert "Calle" not in self._datos().cargo


class TestElCargoNoSeInventa:

    def test_sin_linea_en_negrita_no_hay_cargo(self):
        cuerpo = "ENGEL&VÖLKERS\nMóvil: 612 34 56 78\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="c.eml")
        assert leer_campos(bloques[0]).cargo == ""

    def test_un_telefono_tras_el_nombre_no_es_un_cargo(self):
        cuerpo = ("ENGEL&VÖLKERS\n*Ana Ejemplo*\nMóvil: 612 34 56 78\n"
                  "ana@engelvoelkers.com\n")
        bloques, _ = extraer_bloques(cuerpo, fichero="d.eml")
        d = leer_campos(bloques[0])
        assert d.cargo == ""
        assert d.movil == "612345678", "el telefono sigue leyendose"

    def test_un_email_tras_el_nombre_no_es_un_cargo(self):
        cuerpo = "ENGEL&VÖLKERS\n*Ana Ejemplo*\nana@engelvoelkers.com\nMóvil: 612345678\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="e.eml")
        assert leer_campos(bloques[0]).cargo == ""


class TestElMovilNoSeConfundeConElFijo:
    """`Telf:` y `Tel. Fijo:` son fijo; `Móvil:` es movil. Un cruce mete un fijo en el
    campo `movil` del CRM, que es el que la UI muestra."""

    def test_Telf_es_fijo_no_movil(self):
        cuerpo = "ENGEL&VÖLKERS\nTelf: 931112233\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="f.eml")
        d = leer_campos(bloques[0])
        assert (d.telefono, d.movil) == ("931112233", "")

    def test_Movil_es_movil_no_fijo(self):
        cuerpo = "ENGEL&VÖLKERS\nMóvil: 612345678\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="g.eml")
        d = leer_campos(bloques[0])
        assert (d.movil, d.telefono) == ("612345678", "")

    def test_Movil_sin_tilde_tambien(self):
        cuerpo = "ENGEL&VÖLKERS\nMovil: 612345678\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="h.eml")
        assert leer_campos(bloques[0]).movil == "612345678"
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t7`

Esperado: FALLA en la colección con `ImportError: cannot import name 'leer_campos'`.

- [ ] **Step 3: Implementar la lectura de campos**

Añadir a `core/email_firmas.py`. Primero el import, arriba con los demás:

```python
from core.utils import normalize_es_phone
```

Y tras `extraer_bloques`:

```python
# ---------------------------------------------------------------------------
# Veredictos: «no lo se» y «no hay» no son lo mismo
#
# Un dato que no se pudo mirar NUNCA se convierte en un dato que no existe. Un .eml
# ilegible no autoriza a escribir que ese colaborador no tiene telefono.
# ---------------------------------------------------------------------------

VEREDICTO_ENCONTRADO = "ENCONTRADO"
#: Hay firma de esta persona y NO trae ese campo. Medido: una de las dos plantillas
#: corporativas no incluye movil. No significa «no tiene movil».
VEREDICTO_FIRMA_SIN_CAMPO = "FIRMA_SIN_CAMPO"
#: La persona aparece en el corpus y no se le encontro bloque de firma.
VEREDICTO_SIN_FIRMA = "SIN_FIRMA"
#: Habia bloque, sin email dentro: no se sabe de quien es. No se propone nada.
VEREDICTO_NO_ATRIBUIBLE = "NO_ATRIBUIBLE"
#: El .eml no se pudo parsear o no tiene parte text/plain. SE DECLARA.
VEREDICTO_NO_LEIBLE = "NO_LEIBLE"
#: Dos valores distintos y ninguno decide. Se falla cerrado.
VEREDICTO_CONFLICTO = "CONFLICTO"

#: `Telf:` y `Tel. Fijo:` son FIJO. Se prueba movil primero para que `Móvil:` no caiga
#: en el patron del fijo: un cruce mete un fijo en el campo `movil`, que es el que la
#: UI del CRM muestra en el listado.
_RE_MOVIL = re.compile(
    r"(?im)^\s*\*?\s*(?:m[óo]vil|mobile|m[óo]v\.?)\s*[:.]?\s*(.+?)\s*$")
_RE_FIJO = re.compile(
    r"(?im)^\s*\*?\s*(?:telf|tel\.?\s*fijo|tel[ée]fono|tel\.|phone)\s*[:.]?\s*(.+?)\s*$")

#: Una linea ENTERAMENTE en negrita. La primera es el nombre; el cargo es la siguiente
#: linea no vacia, en negrita o no (las dos plantillas medidas difieren en eso).
_RE_NEGRITA = re.compile(r"^\s*\*(.+?)\*\s*$")

#: Lo que una linea tras el nombre puede ser sin ser un cargo.
_RE_NO_ES_CARGO = re.compile(
    r"(?i)engel\s*&?\s*v[öo]lkers"
    r"|ev\s+mmc|s\.?l\.?u|s\.?a\.?$"
    r"|@"
    r"|^\s*\*?\s*(?:telf|tel|tel[ée]fono|m[óo]vil|movil|mobile|mailto|fax)\b"
    r"|\d{4,}"                       # un CP o un numero largo: es direccion
    r"|^\s*\*?\s*(?:c/|calle|avinguda|avenida|passeig|plaza|pl\.|paseo)\b"
)

_RE_EXTENSION = re.compile(r"(?i)\s*(?:/|\bext\b|\bextension\b|\bextensión\b).*$")


@dataclass(frozen=True)
class DatosFirma:
    """Lo que dice UN bloque de firma. Los campos vacios NO afirman ausencia."""
    email: str
    movil: str = ""
    telefono: str = ""
    cargo: str = ""
    procedencia: str = PROCEDENCIA_DIRECTO
    fichero: str = ""
    linea: int = 0


def limpiar_telefono(valor: str) -> str:
    """El numero que hay en una linea de firma, listo para el CRM.

    `normalize_es_phone` no quita letras ni asteriscos, y los valores llegan sucios: la
    negrita HTML degrada a `*` en el text/plain, y la plantilla de Madrid pega la
    extension detras (`+34 912 345 678 / Ext. 1234`). La extension no es parte del
    numero, y el CRM exige 9 digitos o devuelve HTTP 400 (`[APER-14]`).
    """
    v = _RE_EXTENSION.sub("", valor or "")
    v = v.replace("*", "").replace("<", "").replace(">", "").strip()
    v = normalize_es_phone(v)
    # Un valor sin ningun digito no es un telefono, es basura del parseo.
    return v if any(c.isdigit() for c in v) else ""


def _cargo_de(lineas: list[str]) -> str:
    """El cargo, por POSICION: no tiene etiqueta en ninguna de las dos plantillas.

    Regla medida: la primera linea enteramente en negrita es el NOMBRE, y el cargo es
    la siguiente linea no vacia — en negrita en la plantilla de Madrid, sin negrita en
    la de Barcelona. Si esa linea es la razon social, una direccion, un telefono o un
    email, no hay cargo: **antes vacio que inventado**.
    """
    for i, ln in enumerate(lineas):
        if not _RE_NEGRITA.match(ln):
            continue
        for siguiente in lineas[i + 1:]:
            if not siguiente.strip():
                continue
            if _RE_NO_ES_CARGO.search(siguiente):
                return ""
            m = _RE_NEGRITA.match(siguiente)
            return (m.group(1) if m else siguiente).strip()
        return ""
    return ""


def leer_campos(bloque: BloqueFirma) -> DatosFirma:
    """Los campos de UN bloque ya atribuido. No decide veredictos: eso es `consolidar`."""
    lineas = bloque.texto.splitlines()
    m_movil = _RE_MOVIL.search(bloque.texto)
    # Un `Móvil:` no puede caer en el patron del fijo: se resta del texto antes.
    texto_sin_movil = _RE_MOVIL.sub("", bloque.texto)
    m_fijo = _RE_FIJO.search(texto_sin_movil)
    return DatosFirma(
        email=bloque.email,
        movil=limpiar_telefono(m_movil.group(1)) if m_movil else "",
        telefono=limpiar_telefono(m_fijo.group(1)) if m_fijo else "",
        cargo=_cargo_de(lineas),
        procedencia=bloque.procedencia,
        fichero=bloque.fichero,
        linea=bloque.linea,
    )
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t7`

Esperado: PASA.

> Si `test_el_cargo_es_la_linea_tras_el_nombre_en_negrita` falla devolviendo `""`, mira si
> `_RE_NO_ES_CARGO` está casando «Asesora Inmobiliaria» por alguna alternativa demasiado ancha
> (el `s\.?a\.?$` es el sospechoso). Estrecha la alternativa; **no** relajes la puerta entera.

- [ ] **Step 5: Commit**

```bash
git add core/email_firmas.py tests/test_email_firmas.py
git commit -m "feat(firmas): leer movil, fijo y cargo en las dos plantillas corporativas

Tres cosas que la verdad de campo obliga: los valores llegan con +34, espacios y
envueltos en asteriscos (la negrita HTML degrada asi en el text/plain), la plantilla de
Madrid pega la extension detras del fijo, y el CARGO NO TIENE ETIQUETA —es la linea
siguiente a la del nombre, que es la primera enteramente en negrita; por eso desmarcar
no quita los asteriscos—.

`Telf:`/`Tel. Fijo:` son fijo y `Móvil:` es movil: el movil se resta del texto antes de
buscar el fijo, porque un cruce mete un fijo en el campo que la UI del CRM muestra.

Y antes vacio que inventado: si la linea tras el nombre es la razon social, una
direccion, un telefono o un email, no hay cargo."
```

- [ ] **Step 6: Mutación — no limpiar la extensión**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = '    v = _RE_EXTENSION.sub("", valor or "")'
nuevo = '    v = valor or ""'
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: la extension viaja pegada")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t7m`

Esperado: **fallan** `test_los_casos_medidos[+34 912 345 678 / Ext. 1234-912345678]`,
su gemelo sin `+34`, `test_la_extension_no_es_parte_del_numero` y
`test_el_fijo_con_extension`.

Restaurar: `git checkout -- core/email_firmas.py`

- [ ] **Step 7: Mutación — cruzar móvil y fijo**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = "    m_fijo = _RE_FIJO.search(texto_sin_movil)"
nuevo = "    m_fijo = _RE_FIJO.search(bloque.texto)"
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: el fijo se busca sin restar el movil")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t7n`

Esperado: **falla** `test_Movil_es_movil_no_fijo` (y probablemente
`test_el_fijo_va_a_telefono`, porque `Móvil:` casaría antes que `Telf:`).

Restaurar: `git checkout -- core/email_firmas.py`

- [ ] **Step 8: Mutación — inventar el cargo sin filtrar**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = """            if _RE_NO_ES_CARGO.search(siguiente):
                return ""
"""
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, ""), encoding="utf-8")
print("MUTADO: cualquier linea tras el nombre es el cargo")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t7o`

Esperado: **fallan** los tres de `TestElCargoNoSeInventa` que tienen un teléfono o un email tras el
nombre, más `test_la_razon_social_no_se_confunde_con_el_cargo`.

Restaurar: `git checkout -- core/email_firmas.py`

---

### Task 8: Pieza A.4 — consolidar por persona, y fallar cerrado ante el conflicto

Un mismo `.eml` puede dar **varios bloques para la misma persona** (la plantilla de Barcelona repite
la dirección al final del bloque), y un corpus da varios `.eml`. Consolidar es decidir **un** valor
por persona y por campo, con su veredicto.

La regla que gobierna, y que es la que el spec §6 exige:

- Un valor **directo** manda sobre uno **citado** (el citado es más antiguo).
- Entre dos del mismo nivel, manda el `.eml` **más reciente** (el llamador pasa los resultados en
  orden y el orden se respeta).
- Si quedan dos valores **distintos y no vacíos** que ningún criterio separa → **`CONFLICTO` y no se
  propone nada.** Misma política de fallar cerrado que el dedup del PR #272.
- Un campo vacío en TODOS los bloques de una persona que **sí tiene** bloque → `FIRMA_SIN_CAMPO`,
  que **no** es «no tiene».

**Files:**
- Modify: `core/email_firmas.py`
- Test: `tests/test_email_firmas.py`

**Interfaces:**
- Consumes: `DatosFirma`, los `VEREDICTO_*`, `PROCEDENCIA_*` (Tasks 6-7).
- Produces:
  - `Consolidado` (frozen dataclass): `email: str`, `movil: str`, `telefono: str`, `cargo: str`,
    `veredicto_movil: str`, `veredicto_telefono: str`, `veredicto_cargo: str`,
    `fuentes: tuple[str, ...]` (cada una `"fichero:linea"`).
  - `consolidar(firmas: Iterable[DatosFirma]) -> dict[str, Consolidado]` — clave: el email en
    minúsculas.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_email_firmas.py`:

```python
from core.email_firmas import (VEREDICTO_CONFLICTO, VEREDICTO_ENCONTRADO,
                               VEREDICTO_FIRMA_SIN_CAMPO, Consolidado, consolidar)


def _f(email="ana@engelvoelkers.com", movil="", telefono="", cargo="",
       procedencia=PROCEDENCIA_DIRECTO, fichero="x.eml", linea=1):
    return DatosFirma(email=email, movil=movil, telefono=telefono, cargo=cargo,
                      procedencia=procedencia, fichero=fichero, linea=linea)


class TestConsolidarLoBasico:

    def test_sin_firmas_no_hay_nadie(self):
        assert consolidar([]) == {}

    def test_una_firma_da_un_consolidado(self):
        c = consolidar([_f(movil="612345678")])
        assert set(c) == {"ana@engelvoelkers.com"}
        assert isinstance(c["ana@engelvoelkers.com"], Consolidado)

    def test_el_valor_encontrado_lleva_su_veredicto_y_su_fuente(self):
        c = consolidar([_f(movil="612345678", fichero="a.eml", linea=7)])["ana@engelvoelkers.com"]
        assert c.movil == "612345678"
        assert c.veredicto_movil == VEREDICTO_ENCONTRADO
        assert "a.eml:7" in c.fuentes

    def test_dos_personas_se_separan(self):
        c = consolidar([_f(movil="612345678"),
                        _f(email="berta@engelvoelkers.com", telefono="912345678")])
        assert set(c) == {"ana@engelvoelkers.com", "berta@engelvoelkers.com"}

    def test_el_email_se_normaliza_a_minusculas(self):
        c = consolidar([_f(email="Ana@EngelVoelkers.com", movil="612345678")])
        assert set(c) == {"ana@engelvoelkers.com"}


class TestDosBloquesQueDicenLoMISMO:
    """El caso normal: la plantilla de Barcelona repite la direccion, asi que un solo
    .eml da dos bloques con los mismos valores. Eso NO es un conflicto."""

    def test_dos_valores_iguales_no_son_conflicto(self):
        c = consolidar([_f(movil="612345678", linea=1),
                        _f(movil="612345678", linea=9)])["ana@engelvoelkers.com"]
        assert c.movil == "612345678"
        assert c.veredicto_movil == VEREDICTO_ENCONTRADO

    def test_uno_vacio_y_uno_con_valor_se_completan(self):
        c = consolidar([_f(movil="612345678"),
                        _f(telefono="931112233")])["ana@engelvoelkers.com"]
        assert (c.movil, c.telefono) == ("612345678", "931112233")


class TestElDirectoMandaSobreElCitado:
    """Un bloque citado es mas antiguo: si el consultor cambio de movil, el directo
    es el bueno. Esto NO es un conflicto, es una jerarquia."""

    def test_el_directo_gana(self):
        c = consolidar([_f(movil="600000000", procedencia=PROCEDENCIA_CITADO),
                        _f(movil="612345678", procedencia=PROCEDENCIA_DIRECTO)])
        assert c["ana@engelvoelkers.com"].movil == "612345678"

    def test_el_orden_en_que_llegan_no_cambia_el_resultado(self):
        c = consolidar([_f(movil="612345678", procedencia=PROCEDENCIA_DIRECTO),
                        _f(movil="600000000", procedencia=PROCEDENCIA_CITADO)])
        assert c["ana@engelvoelkers.com"].movil == "612345678"

    def test_si_SOLO_hay_citado_se_usa(self):
        """Que sea mas antiguo no lo hace falso: es lo unico que hay."""
        c = consolidar([_f(movil="600000000", procedencia=PROCEDENCIA_CITADO)])
        assert c["ana@engelvoelkers.com"].movil == "600000000"
        assert c["ana@engelvoelkers.com"].veredicto_movil == VEREDICTO_ENCONTRADO


class TestElConflictoFALLA_CERRADO:
    """Misma politica que el dedup del PR #272: ante lo que no puede comprobar, no
    escribe. Un movil mal elegido va a la ficha del cliente."""

    def test_dos_directos_distintos_son_CONFLICTO(self):
        c = consolidar([_f(movil="612345678", fichero="a.eml"),
                        _f(movil="600000000", fichero="b.eml")])["ana@engelvoelkers.com"]
        assert c.veredicto_movil == VEREDICTO_CONFLICTO

    def test_en_conflicto_NO_se_propone_valor(self):
        """Lo que importa: que el campo salga VACIO, no que el veredicto lo diga."""
        c = consolidar([_f(movil="612345678"), _f(movil="600000000")])["ana@engelvoelkers.com"]
        assert c.movil == "", "un valor propuesto en conflicto acaba en el CRM"

    def test_el_conflicto_de_un_campo_no_contamina_al_otro(self):
        c = consolidar([_f(movil="612345678", telefono="931112233"),
                        _f(movil="600000000", telefono="931112233")])["ana@engelvoelkers.com"]
        assert c.veredicto_movil == VEREDICTO_CONFLICTO
        assert c.veredicto_telefono == VEREDICTO_ENCONTRADO
        assert c.telefono == "931112233"

    def test_dos_citados_distintos_tambien_son_CONFLICTO(self):
        c = consolidar([_f(movil="612345678", procedencia=PROCEDENCIA_CITADO),
                        _f(movil="600000000", procedencia=PROCEDENCIA_CITADO)])
        assert c["ana@engelvoelkers.com"].veredicto_movil == VEREDICTO_CONFLICTO

    def test_el_conflicto_lista_TODAS_las_fuentes(self):
        """Para que Nikolai pueda ir a mirar los dos y decidir."""
        c = consolidar([_f(movil="612345678", fichero="a.eml", linea=3),
                        _f(movil="600000000", fichero="b.eml", linea=5)])["ana@engelvoelkers.com"]
        assert "a.eml:3" in c.fuentes and "b.eml:5" in c.fuentes


class TestFirmaSinCampoNoEsNoTiene:
    """La frontera del §6 del spec, y el aviso #3 del encargo."""

    def test_hay_firma_y_no_hay_movil_es_FIRMA_SIN_CAMPO(self):
        c = consolidar([_f(telefono="912345678")])["ana@engelvoelkers.com"]
        assert c.movil == ""
        assert c.veredicto_movil == VEREDICTO_FIRMA_SIN_CAMPO

    def test_FIRMA_SIN_CAMPO_no_es_el_mismo_veredicto_que_ENCONTRADO_vacio(self):
        """Si los dos colapsan en «sin dato», el informe afirma una ausencia que nadie
        comprobo. Son constantes distintas a proposito."""
        assert VEREDICTO_FIRMA_SIN_CAMPO != VEREDICTO_ENCONTRADO
        assert VEREDICTO_FIRMA_SIN_CAMPO != VEREDICTO_CONFLICTO

    def test_el_cargo_ausente_tambien_se_declara(self):
        c = consolidar([_f(movil="612345678")])["ana@engelvoelkers.com"]
        assert c.veredicto_cargo == VEREDICTO_FIRMA_SIN_CAMPO
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t8`

Esperado: FALLA en la colección con `ImportError: cannot import name 'consolidar'`.

- [ ] **Step 3: Implementar la consolidación**

Añadir el import arriba:

```python
from collections.abc import Iterable
```

Y al final de `core/email_firmas.py`:

```python
@dataclass(frozen=True)
class Consolidado:
    """Lo que el corpus dice de UNA persona, con el veredicto de cada campo.

    Un campo vacio con veredicto `FIRMA_SIN_CAMPO` significa «hay firma y no lo trae»,
    que NO es «no lo tiene»: una de las dos plantillas corporativas medidas no incluye
    movil. Un campo vacio con `CONFLICTO` significa «hay dos y no se sabe cual».
    """
    email: str
    movil: str = ""
    telefono: str = ""
    cargo: str = ""
    veredicto_movil: str = VEREDICTO_FIRMA_SIN_CAMPO
    veredicto_telefono: str = VEREDICTO_FIRMA_SIN_CAMPO
    veredicto_cargo: str = VEREDICTO_FIRMA_SIN_CAMPO
    fuentes: tuple[str, ...] = ()


def _elegir(valores: list[tuple[str, str]]) -> tuple[str, str]:
    """El valor de un campo entre varios bloques, y su veredicto.

    `valores` son pares `(valor, procedencia)` ya filtrados de vacios, en el orden en
    que llegaron (el llamador los pasa del .eml mas antiguo al mas reciente).

    Jerarquia: un DIRECTO manda sobre un CITADO, porque el citado es mas antiguo y el
    consultor puede haber cambiado de numero. Entre dos del mismo nivel manda el
    ultimo. Si quedan dos distintos que nada separa, **CONFLICTO y campo vacio**: un
    movil mal elegido acaba en la ficha del cliente, y fallar cerrado es la politica de
    este modulo desde el dedup del PR #272.
    """
    if not valores:
        return "", VEREDICTO_FIRMA_SIN_CAMPO

    directos = [v for v, p in valores if p == PROCEDENCIA_DIRECTO]
    candidatos = directos or [v for v, _ in valores]
    distintos = set(candidatos)
    if len(distintos) > 1:
        return "", VEREDICTO_CONFLICTO
    return candidatos[-1], VEREDICTO_ENCONTRADO


def consolidar(firmas: Iterable[DatosFirma]) -> dict[str, Consolidado]:
    """Un `Consolidado` por persona, agrupando por el email de su firma.

    El orden de `firmas` es significativo: el llamador las pasa del .eml mas antiguo al
    mas reciente, y `_elegir` se queda con el ultimo cuando nada mas los separa.
    """
    por_email: dict[str, list[DatosFirma]] = {}
    for f in firmas:
        if not f.email:
            continue
        por_email.setdefault(f.email.lower(), []).append(f)

    salida: dict[str, Consolidado] = {}
    for email, grupo in por_email.items():
        movil, v_movil = _elegir([(f.movil, f.procedencia) for f in grupo if f.movil])
        tel, v_tel = _elegir([(f.telefono, f.procedencia) for f in grupo if f.telefono])
        cargo, v_cargo = _elegir([(f.cargo, f.procedencia) for f in grupo if f.cargo])
        salida[email] = Consolidado(
            email=email, movil=movil, telefono=tel, cargo=cargo,
            veredicto_movil=v_movil, veredicto_telefono=v_tel, veredicto_cargo=v_cargo,
            fuentes=tuple(dict.fromkeys(f"{f.fichero}:{f.linea}" for f in grupo)),
        )
    return salida
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t8`

Esperado: PASA.

- [ ] **Step 5: Commit**

```bash
git add core/email_firmas.py tests/test_email_firmas.py
git commit -m "feat(firmas): consolidar por persona, y fallar cerrado ante el conflicto

Un .eml da varios bloques de la misma persona (la plantilla de Barcelona repite la
direccion) y un corpus da varios .eml. Jerarquia: un bloque DIRECTO manda sobre uno
CITADO porque el citado es mas antiguo; entre dos del mismo nivel manda el ultimo.

Y si quedan dos valores distintos que nada separa: CONFLICTO y CAMPO VACIO. No basta
con que el veredicto lo diga —un valor propuesto en conflicto acaba en el CRM—, asi que
el test que importa comprueba que el campo sale vacio. Misma politica que el dedup del
PR #272: ante lo que no puede comprobar, no escribe.

FIRMA_SIN_CAMPO es una constante DISTINTA de las demas a proposito: «hay firma y no lo
trae» no es «no lo tiene». Una de las dos plantillas medidas no incluye movil."
```

- [ ] **Step 6: Mutación — el conflicto propone valor igualmente**

Es la frontera que protege los datos del cliente. Es el mutante más importante de esta task.

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = """    if len(distintos) > 1:
        return "", VEREDICTO_CONFLICTO"""
nuevo = """    if len(distintos) > 1:
        return candidatos[-1], VEREDICTO_CONFLICTO"""
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: el conflicto propone el ultimo valor")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t8m`

Esperado: **falla** `test_en_conflicto_NO_se_propone_valor`. Si sólo cayeran los tests del
veredicto y no éste, la cobertura sería la aserción débil: el veredicto correcto con el valor
peligroso al lado.

Restaurar: `git checkout -- core/email_firmas.py`

- [ ] **Step 7: Mutación — colapsar `FIRMA_SIN_CAMPO` en «sin dato»**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = 'VEREDICTO_FIRMA_SIN_CAMPO = "FIRMA_SIN_CAMPO"'
nuevo = 'VEREDICTO_FIRMA_SIN_CAMPO = VEREDICTO_ENCONTRADO  # colapsado'
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: «hay firma y no lo trae» pasa a ser «encontrado vacio»")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t8n`

Esperado: **falla** `test_FIRMA_SIN_CAMPO_no_es_el_mismo_veredicto_que_ENCONTRADO_vacio`, y con él
`test_hay_firma_y_no_hay_movil_es_FIRMA_SIN_CAMPO` si el informe distingue por la constante.

Restaurar: `git checkout -- core/email_firmas.py`

- [ ] **Step 8: Mutación — quitar la jerarquía directo/citado**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = """    directos = [v for v, p in valores if p == PROCEDENCIA_DIRECTO]
    candidatos = directos or [v for v, _ in valores]"""
nuevo = """    candidatos = [v for v, _ in valores]"""
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: el citado cuenta igual que el directo")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t8o`

Esperado: **fallan** `test_el_directo_gana` y `test_el_orden_en_que_llegan_no_cambia_el_resultado`
(pasarían a `CONFLICTO`). Comprueba que **no** cae `test_si_SOLO_hay_citado_se_usa`: si cae, la
jerarquía se escribió como filtro y descarta lo único que hay.

Restaurar: `git checkout -- core/email_firmas.py`

---

### Task 9: Pieza A.5 + B.1 — leer un `.eml` de verdad, y el informe

Aquí se junta todo por primera vez sobre ficheros reales, y aquí es donde se cobra la frontera que
la Task 6 dejó **parcialmente cubierta**: el `.eml` sí trae cabecera `From:`, así que ahora se puede
probar de verdad que un reenvío no le atribuye a su remitente el teléfono de otro.

Y aquí entra el último veredicto: `NO_LEIBLE`. Un `.eml` sin parte `text/plain` o que no parsea **se
declara**; no se cuenta como «esta persona no tiene teléfono».

**Files:**
- Modify: `core/email_firmas.py` (añadir `extraer_de_eml` y `extraer_de_directorio`)
- Create: `scripts/crm_colaboradores_firmas.py`
- Test: `tests/test_email_firmas.py` (la lectura del `.eml`)
- Test: `tests/test_crm_colaboradores_firmas_cli.py` (crear — el informe)

**Interfaces:**
- Consumes: `extraer_bloques`, `leer_campos`, `consolidar`, los `VEREDICTO_*`,
  `DOMINIO_COLABORADOR` (Tasks 5-8); `get_colaborador`, `resolver_parte` (Tasks 1-3);
  `case_locator.resolve_ref` y `case_locator.buscar` (`core/casos/case_locator.py`, patrón de
  `scripts/crm_ficha.py:45-50`).
- Produces:
  - `ResultadoEml` (frozen dataclass): `firmas: tuple[DatosFirma, ...]`,
    `emails_vistos: frozenset[str]`, `sin_atribuir: int`, `ilegible: str`.
  - `extraer_de_eml(path: Path) -> ResultadoEml`.
  - `extraer_de_directorio(raiz: Path) -> tuple[dict[str, Consolidado], frozenset[str], tuple[str, ...]]`
    — consolidados, todas las direcciones vistas, y las rutas ilegibles.
  - `scripts/crm_colaboradores_firmas.py` con `app` (typer) y el comando `report`.

- [ ] **Step 1: Escribir los tests que fallan (lectura del `.eml`)**

Añadir a `tests/test_email_firmas.py`:

```python
from pathlib import Path

from core.email_firmas import (VEREDICTO_NO_LEIBLE, extraer_de_directorio,
                               extraer_de_eml)

_EML = """\
From: "Otro, Remitente" <otro@engelvoelkers.com>
To: despacho@tyukhay.example
Subject: Te reenvio esto
Date: Wed, 12 Aug 2026 10:00:00 +0200
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0

Te reenvio lo que me manda ella.

{firma}
"""


def _escribe_eml(tmp_path, nombre, firma):
    p = tmp_path / nombre
    p.write_text(_EML.format(firma=firma), encoding="utf-8")
    return p


class TestLeerUnEmlDeVerdad:

    def test_el_texto_plano_se_lee(self, tmp_path):
        r = extraer_de_eml(_escribe_eml(tmp_path, "a.eml", FIRMA_BCN))
        assert r.ilegible == ""
        assert [f.email for f in r.firmas] == ["ana@engelvoelkers.com"]

    def test_EL_FROM_DE_UN_REENVIO_NO_RECIBE_EL_TELEFONO_DE_OTRO(self, tmp_path):
        """EL GUARD CENTRAL, ahora con cabecera de verdad. El `From:` es una persona
        y la firma es de otra: si esto falla, el movil de A va a la ficha de B."""
        r = extraer_de_eml(_escribe_eml(tmp_path, "b.eml", FIRMA_BCN))
        atribuidos = {f.email for f in r.firmas}

        assert "otro@engelvoelkers.com" not in atribuidos, (
            "el remitente del reenvío no firma este correo")
        assert atribuidos == {"ana@engelvoelkers.com"}

    def test_el_From_SI_cuenta_como_direccion_VISTA(self, tmp_path):
        """Para la seccion de candidatos: aparecer no es firmar, pero se registra."""
        r = extraer_de_eml(_escribe_eml(tmp_path, "c.eml", FIRMA_BCN))
        assert "otro@engelvoelkers.com" in r.emails_vistos
        assert "ana@engelvoelkers.com" in r.emails_vistos

    def test_un_eml_que_no_parsea_es_NO_LEIBLE_no_una_ausencia(self, tmp_path):
        p = tmp_path / "roto.eml"
        p.write_bytes(b"\xff\xfe esto no es un correo")
        r = extraer_de_eml(p)
        assert r.ilegible != "", "tiene que DECLARAR que no se pudo leer"
        assert r.firmas == ()

    def test_un_eml_sin_parte_text_plain_es_NO_LEIBLE(self, tmp_path):
        p = tmp_path / "solo_html.eml"
        p.write_text(
            "From: a@engelvoelkers.com\nSubject: x\n"
            'Content-Type: text/html; charset="utf-8"\nMIME-Version: 1.0\n\n'
            "<p>Hola</p>\n", encoding="utf-8")
        r = extraer_de_eml(p)
        assert r.ilegible != ""


class TestRecorrerUnDirectorio:

    def test_encuentra_los_eml_en_subcarpetas(self, tmp_path):
        lote = tmp_path / "2026-08-14_email_01"
        lote.mkdir()
        _escribe_eml(lote, "uno.eml", FIRMA_BCN)
        sub = lote / "compuesto"
        sub.mkdir()
        _escribe_eml(sub, "dos.eml", FIRMA_MAD)

        cons, vistos, ilegibles = extraer_de_directorio(tmp_path)
        assert set(cons) == {"ana@engelvoelkers.com", "berta@engelvoelkers.com"}
        assert ilegibles == ()

    def test_un_ilegible_no_hunde_el_recorrido_y_SE_LISTA(self, tmp_path):
        _escribe_eml(tmp_path, "bueno.eml", FIRMA_BCN)
        (tmp_path / "malo.eml").write_bytes(b"\xff\xfe no")

        cons, _, ilegibles = extraer_de_directorio(tmp_path)
        assert "ana@engelvoelkers.com" in cons
        assert len(ilegibles) == 1 and "malo.eml" in ilegibles[0]

    def test_un_directorio_vacio_no_es_un_error(self, tmp_path):
        assert extraer_de_directorio(tmp_path) == ({}, frozenset(), ())

    def test_el_orden_es_estable(self, tmp_path):
        """`consolidar` se queda con el ultimo cuando nada mas separa: el orden del
        recorrido tiene que ser determinista o el resultado varia entre corridas."""
        _escribe_eml(tmp_path, "b.eml", FIRMA_BCN)
        _escribe_eml(tmp_path, "a.eml", FIRMA_MAD)
        primera = extraer_de_directorio(tmp_path)
        segunda = extraer_de_directorio(tmp_path)
        assert primera == segunda
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t9`

Esperado: FALLA en la colección con `ImportError: cannot import name 'extraer_de_eml'`.

- [ ] **Step 3: Implementar la lectura del `.eml`**

Añadir los imports arriba de `core/email_firmas.py`:

```python
from email import policy
from email.parser import BytesParser
from pathlib import Path
```

Y al final del módulo:

```python
@dataclass(frozen=True)
class ResultadoEml:
    """Lo que UN .eml dio, con la constancia de lo que no se pudo leer.

    `ilegible` con texto significa que el fichero no se pudo mirar. Eso **no** es que
    no haya firma: es que no se sabe. Se declara y sube al informe.
    """
    firmas: tuple[DatosFirma, ...] = ()
    emails_vistos: frozenset[str] = frozenset()
    sin_atribuir: int = 0
    ilegible: str = ""


def extraer_de_eml(path: Path) -> ResultadoEml:
    """Las firmas de un .eml, atribuidas por su propio contenido.

    **La cabecera `From:` no participa en la atribucion.** Se lee solo para
    `emails_vistos`, que alimenta la seccion de candidatos del informe: aparecer en un
    correo del expediente no te hace colaborador de ese expediente (medido el
    2026-09-04 sobre W-02Q38C: 7 direcciones @ev en 6 correos, 3 vinculadas).
    """
    try:
        msg = BytesParser(policy=policy.default).parse(path.open("rb"))
    except Exception as exc:  # noqa: BLE001 — un .eml corrupto se declara, no rompe
        return ResultadoEml(ilegible=f"{path}: no parsea ({exc!r})")

    try:
        parte = msg.get_body(preferencelist=("plain",))
        cuerpo = parte.get_content() if parte is not None else ""
    except Exception as exc:  # noqa: BLE001 — charset roto, base64 truncado…
        return ResultadoEml(ilegible=f"{path}: cuerpo ilegible ({exc!r})")

    if not cuerpo.strip():
        return ResultadoEml(ilegible=f"{path}: sin parte text/plain con contenido")

    cabeceras = " ".join(str(msg.get(h) or "") for h in ("From", "To", "Cc"))
    vistos = {m.group(0).lower()
              for m in _RE_EMAIL_COLAB.finditer(cabeceras + "\n" + cuerpo)}

    bloques, sin_atribuir = extraer_bloques(cuerpo, fichero=path.name)
    return ResultadoEml(
        firmas=tuple(leer_campos(b) for b in bloques),
        emails_vistos=frozenset(vistos),
        sin_atribuir=sin_atribuir,
    )


def extraer_de_directorio(
    raiz: Path,
) -> tuple[dict[str, Consolidado], frozenset[str], tuple[str, ...]]:
    """Recorre `raiz` en busca de `.eml` y consolida lo que digan sus firmas.

    Devuelve `(consolidados, emails_vistos, ilegibles)`. El recorrido va **ordenado**:
    `consolidar` se queda con el ultimo valor cuando nada mas lo separa, asi que un
    orden no determinista daria resultados distintos entre corridas.

    Un fichero ilegible no hunde el recorrido y **se lista**: «no pude mirar» y «no hay
    nada» tienen que verse distinto.
    """
    firmas: list[DatosFirma] = []
    vistos: set[str] = set()
    ilegibles: list[str] = []
    for path in sorted(Path(raiz).rglob("*.eml")):
        r = extraer_de_eml(path)
        if r.ilegible:
            ilegibles.append(r.ilegible)
            continue
        firmas.extend(r.firmas)
        vistos |= r.emails_vistos
    return consolidar(firmas), frozenset(vistos), tuple(ilegibles)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py -q -p no:randomly --basetemp=C:/t/t9`

Esperado: PASA.

- [ ] **Step 5: Escribir los tests del informe**

Crear `tests/test_crm_colaboradores_firmas_cli.py`:

```python
"""El informe: qué dice la firma, qué falta en el CRM, y QUÉ NO SE PUDO MIRAR.

Un dato que no se pudo leer nunca se convierte en un dato que no existe. Y aparecer en
un correo del expediente no te hace colaborador de ese expediente: eso lo decide
Nikolai, y el informe solo se lo señala.
"""
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from core import case_manager
from core.casos import case_locator
from scripts import crm_colaboradores_firmas as cli

_EML = """\
From: "Otro, Remitente" <otro@engelvoelkers.com>
Subject: x
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0

Hola.

ENGEL&VÖLKERS
*Ana Ejemplo Ficticia*
Asesora Inmobiliaria
Telf: +34 93 111 22 33
Móvil: *612 34 56 78*
ana@engelvoelkers.com
"""


class FugaDeRedEnTest(BaseException):
    """No hereda de Exception: ningun `except Exception` del CLI puede tragarsela."""


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    def _prohibido(metodo):
        def _f(*a, **k):
            raise FugaDeRedEnTest(f"httpx.{metodo} salio a la red en un test")
        return _f
    for metodo in ("get", "post", "put", "delete", "patch", "request"):
        monkeypatch.setattr(f"httpx.{metodo}", _prohibido(metodo))


@pytest.fixture
def caso(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id, tipo_caso="VUELTA",
        ciudad="Barcelona", direccion="Falsa 1", id_go="W-000AAA",
    )
    lote = case_locator.path_for(case_id) / "00_Input" / "2026-08-14_email_01"
    lote.mkdir(parents=True, exist_ok=True)
    (lote / "uno.eml").write_text(_EML, encoding="utf-8")
    return case_id


def _corre(extra=None):
    return CliRunner().invoke(cli.app, ["report", "--case-id", "W-000AAA", *(extra or [])])


class TestElInformeSeEscribeFueraDelCrudo:

    def test_va_a_01_Procesado_no_a_00_Input(self, caso, monkeypatch):
        """`00_Input` es crudo intocable por la regla de idempotencia de CLAUDE.md."""
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        r = _corre()
        assert r.exit_code == 0, r.output

        destino = case_locator.path_for(caso) / "01_Procesado" / "_firmas_colaboradores.md"
        assert destino.is_file()
        assert not (case_locator.path_for(caso) / "00_Input" / "_firmas_colaboradores.md").exists()

    def test_el_informe_cita_fichero_y_linea(self, caso, monkeypatch):
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8")
        assert "uno.eml:" in texto, "sin origen, el dato no es verificable"
        assert "612345678" in texto
        assert "931112233" in texto


class TestElInformeDeclaraLoQueNoPudoMirar:

    def test_un_eml_ilegible_SALE_en_el_informe(self, caso, monkeypatch):
        lote = case_locator.path_for(caso) / "00_Input" / "2026-08-14_email_01"
        (lote / "roto.eml").write_bytes(b"\xff\xfe no")
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()

        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8")
        assert "roto.eml" in texto
        assert "NO_LEIBLE" in texto or "no se pudo" in texto.lower()

    def test_el_informe_NUNCA_dice_que_alguien_no_tiene_telefono(self, caso, monkeypatch):
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8").lower()
        for prohibido in ("no tiene móvil", "no tiene movil", "no tiene teléfono",
                          "sin móvil", "no dispone de"):
            assert prohibido not in texto, f"afirma una ausencia: {prohibido!r}"


class TestLosCandidatosSonSUGERENCIA:
    """Medido: 7 direcciones @ev en los 6 .eml de W-02Q38C, 6 ya son colaboradores y
    solo 3 estan vinculadas al expediente. El corpus NO dice quien es colaborador."""

    def test_una_direccion_vista_que_no_esta_en_la_ficha_sale_como_candidata(
            self, caso, monkeypatch):
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        texto = (case_locator.path_for(caso) / "01_Procesado"
                 / "_firmas_colaboradores.md").read_text(encoding="utf-8")
        assert "otro@engelvoelkers.com" in texto, "el From: aparece, aunque no firme"
        assert "candidat" in texto.lower()

    def test_el_informe_NO_da_de_alta_a_nadie(self, caso, monkeypatch):
        """Ni crea ni vincula: es un informe. El alta la decide Nikolai."""
        crear = MagicMock()
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        monkeypatch.setattr("core.sudespacho_relations.create_colaborador", crear)
        _corre()
        crear.assert_not_called()

    def test_report_NO_escribe_en_el_ficha_crm_yaml(self, caso, monkeypatch):
        """`report` solo informa; escribir es `apply` (Task 10)."""
        ficha = case_locator.path_for(caso) / "00_Input" / "_ficha_crm.yaml"
        ficha.write_text("colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
                         encoding="utf-8")
        antes = ficha.read_text(encoding="utf-8")
        monkeypatch.setattr(cli, "resolver_parte", MagicMock(return_value=None))
        _corre()
        assert ficha.read_text(encoding="utf-8") == antes


class TestUnCasoQueNoExiste:

    def test_sale_con_error_legible(self, tmp_path, monkeypatch):
        root = tmp_path / "CASOS"
        root.mkdir()
        monkeypatch.setattr(case_locator, "_root", lambda: root)
        r = CliRunner().invoke(cli.app, ["report", "--case-id", "W-NOEXISTE"])
        assert r.exit_code == 1
        assert "no encontrado" in r.output.lower()
```

- [ ] **Step 6: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t9b`

Esperado: FALLA con `ModuleNotFoundError: No module named 'scripts.crm_colaboradores_firmas'`.

- [ ] **Step 7: Escribir el CLI con el comando `report`**

Crear `scripts/crm_colaboradores_firmas.py`:

```python
"""CLI local: leer las firmas de los correos de un expediente y proponer los datos que
faltan en las fichas de colaborador del CRM.

Dos comandos, y el orden importa:

    python -m scripts.crm_colaboradores_firmas report --case-id W-XXXXXX
    python -m scripts.crm_colaboradores_firmas apply  --case-id W-XXXXXX --confirmar

`report` **no escribe nada**: deja un informe en `01_Procesado/_firmas_colaboradores.md`
para que Nikolai lo lea. `apply` mete lo aprobado en `00_Input/_ficha_crm.yaml`, y es
`python -m scripts.crm_ficha` quien lo lleva al CRM. Ninguno de los dos escribe en el
CRM directamente: un solo camino de escritura.

El informe lleva PII (telefonos de personas), asi que vive en `data/CASOS/` y nunca se
commitea.
"""
from __future__ import annotations

from pathlib import Path

import typer

from core.casos import case_locator
from core.email_firmas import (VEREDICTO_CONFLICTO, VEREDICTO_ENCONTRADO,
                               VEREDICTO_FIRMA_SIN_CAMPO, Consolidado,
                               extraer_de_directorio)
from core.sudespacho_relations import get_colaborador, resolver_parte

app = typer.Typer(add_completion=False,
                  help="Firmas de correo -> datos que faltan en las fichas de colaborador")

_INFORME = "_firmas_colaboradores.md"

_CABECERA = """\
<!-- GENERADO por scripts.crm_colaboradores_firmas — NO editar a mano. -->
# Firmas de colaboradores — {caso}

Leido de los `.eml` de `00_Input/`. **Este informe no ha escrito nada en el CRM.**

Como leer los veredictos:

| Veredicto | Significa |
|---|---|
| `ENCONTRADO` | El dato se leyo, y la columna «Origen» dice de donde |
| `FIRMA_SIN_CAMPO` | Hay firma de esa persona y **no trae ese campo**. Una de las dos plantillas corporativas de E&V no incluye movil, asi que esto **no** significa que no lo tenga |
| `CONFLICTO` | Dos valores distintos y ninguno decide. **No se propone nada** |

"""


def _caso_dir(case_id: str) -> tuple[str, Path]:
    resolved = case_locator.resolve_ref(case_id)
    case_dir = case_locator.buscar(resolved)
    if case_dir is None or not (case_dir / "00_Input" / "_caso.md").is_file():
        typer.echo(f"[ERROR] Caso no encontrado: {case_id!r} (resuelto: {resolved!r})",
                   err=True)
        raise typer.Exit(code=1)
    return resolved, case_dir


def _falta_en_el_crm(email: str) -> tuple[str, dict[str, str]]:
    """`(id o "", ficha)` del colaborador. Nunca lanza: sin CRM, se informa igual.

    Un fallo aqui deja la ficha en blanco y el informe lo dice; no se afirma que el
    campo del CRM este vacio cuando no se pudo mirar.
    """
    try:
        r = resolver_parte("colaboradores", nif="", email=email)
    except Exception:  # noqa: BLE001
        return "", {}
    colab_id = getattr(r, "id", None) or ""
    if not colab_id:
        return "", {}
    try:
        return colab_id, get_colaborador(colab_id)
    except Exception:  # noqa: BLE001
        return colab_id, {}


def _fila(c: Consolidado, colab_id: str, ficha: dict[str, str]) -> str:
    def celda(valor: str, veredicto: str, prop: str) -> str:
        actual = (ficha.get(prop) or "").strip() if ficha else ""
        if veredicto == VEREDICTO_CONFLICTO:
            return "**CONFLICTO** (no se propone)"
        if veredicto == VEREDICTO_FIRMA_SIN_CAMPO:
            return "`FIRMA_SIN_CAMPO`"
        if actual:
            return f"{valor} — el CRM ya tiene `{actual}`, **no se toca**"
        return f"**{valor}** — el CRM lo tiene vacio"

    donde = f"id {colab_id}" if colab_id else "**no existe como colaborador**"
    return (f"| {c.email} | {donde} | {celda(c.movil, c.veredicto_movil, 'movil')} "
            f"| {celda(c.telefono, c.veredicto_telefono, 'telefono1')} "
            f"| {c.cargo or '`' + c.veredicto_cargo + '`'} "
            f"| {', '.join(c.fuentes)} |")


@app.command()
def report(case_id: str = typer.Option(..., "--case-id",
                                       help="case_id canonico o W-code")) -> None:
    """Escribe el informe. NO toca el CRM ni el `_ficha_crm.yaml`."""
    resolved, case_dir = _caso_dir(case_id)
    consolidados, vistos, ilegibles = extraer_de_directorio(case_dir / "00_Input")

    partes = [_CABECERA.format(caso=resolved)]
    partes.append("## Quien firma, y que le falta en el CRM\n")
    partes.append("| Firma de | En el CRM | Movil | Fijo (`telefono1`) | Cargo | Origen |")
    partes.append("|---|---|---|---|---|---|")
    for email in sorted(consolidados):
        colab_id, ficha = _falta_en_el_crm(email)
        partes.append(_fila(consolidados[email], colab_id, ficha))

    candidatos = sorted(vistos - set(consolidados))
    partes.append("\n## Candidatos — SUGERENCIA, no un alta\n")
    partes.append(
        "Estas direcciones de E&V aparecen en los correos del expediente y **no firman "
        "ninguno**. Aparecer en un correo del caso no te hace colaborador del caso: "
        "medido el 2026-09-04 sobre otro expediente, de 7 direcciones en 6 correos solo "
        "3 estaban vinculadas, y estaban ahi por CC o por ser una unidad interna. "
        "**Decide tu**; este informe no da de alta a nadie.\n")
    if candidatos:
        partes.append("| Direccion | En el CRM |")
        partes.append("|---|---|")
        for email in candidatos:
            colab_id, _ = _falta_en_el_crm(email)
            partes.append(f"| {email} | "
                          f"{'id ' + colab_id if colab_id else 'no existe'} |")
    else:
        partes.append("_Ninguna._\n")

    partes.append("\n## Lo que NO se pudo mirar\n")
    if ilegibles:
        partes.append(
            "**`NO_LEIBLE`.** Estos ficheros no se pudieron leer. Eso **no** es que no "
            "tengan firma: es que no se sabe.\n")
        partes.extend(f"- `{x}`" for x in ilegibles)
    else:
        partes.append("_Todos los `.eml` se leyeron._\n")

    destino = case_dir / "01_Procesado" / _INFORME
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    typer.echo(f"[OK] Informe: {destino}")
    typer.echo(f"     {len(consolidados)} firmas, {len(candidatos)} candidatos, "
               f"{len(ilegibles)} ilegibles")


if __name__ == "__main__":
    app()
```

- [ ] **Step 8: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t9b`

Esperado: PASA.

> Si `test_sale_con_error_legible` falla con exit 2 en vez de 1, es que typer trata `report` como
> subcomando y el `--case-id` que falta lo rechaza él: comprueba que el runner pasa `"report"` como
> primer argumento (lo hace) y que `_caso_dir` es quien levanta el `Exit(1)`.

- [ ] **Step 9: Commit**

```bash
git add core/email_firmas.py scripts/crm_colaboradores_firmas.py tests/test_email_firmas.py tests/test_crm_colaboradores_firmas_cli.py
git commit -m "feat(firmas): leer los .eml del expediente y escribir el informe

Aqui se cobra de verdad el guard central: el .eml SI trae `From:`, asi que el test del
reenvio comprueba con cabecera real que el remitente no recibe el telefono de quien
firma. La cabecera se lee SOLO para emails_vistos, que alimenta los candidatos.

Y entra el ultimo veredicto: un .eml que no parsea o sin parte text/plain es NO_LEIBLE
y SALE en el informe. «No pude mirar» y «no hay nada» tienen que verse distinto.

El informe va a 01_Procesado (00_Input es crudo intocable) y lleva PII, asi que vive en
data/CASOS y nunca se commitea. `report` no escribe en el CRM ni en el _ficha_crm.yaml.

La seccion de candidatos es una sugerencia, no un alta: el corpus no sabe quien es
colaborador del caso —7 direcciones en 6 correos de W-02Q38C, 3 vinculadas— y eso lo
decide Nikolai."
```

- [ ] **Step 10: Mutación — atribuir por el `From:` (ahora sí, el mutante fuerte)**

Este es el que la Task 6 no pudo cobrar por falta de cabecera.

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = "    bloques, sin_atribuir = extraer_bloques(cuerpo, fichero=path.name)"
nuevo = ("    bloques, sin_atribuir = extraer_bloques(\n"
         "        cuerpo + '\\n' + str(msg.get('From') or ''), fichero=path.name)")
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: el From: entra en el texto que se atribuye")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t9m`

Esperado: **falla** `test_EL_FROM_DE_UN_REENVIO_NO_RECIBE_EL_TELEFONO_DE_OTRO`. Con esto la
frontera queda **cerrada**; anota que la cobertura parcial de la Task 6 ya no lo es.

Restaurar: `git checkout -- core/email_firmas.py`

- [ ] **Step 11: Mutación — tragarse el ilegible en silencio**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("core/email_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = """        if r.ilegible:
            ilegibles.append(r.ilegible)
            continue"""
nuevo = """        if r.ilegible:
            continue"""
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: el ilegible desaparece del recuento")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_email_firmas.py tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t9n`

Esperado: **fallan** `test_un_ilegible_no_hunde_el_recorrido_y_SE_LISTA` y
`test_un_eml_ilegible_SALE_en_el_informe`. Es la frontera del aviso #3 del encargo: hacer
desaparecer del recuento lo que no se pudo mirar.

Restaurar: `git checkout -- core/email_firmas.py`

---

### Task 10: Pieza B.2 — `apply`, que escribe en el YAML y sólo en las claves vacías

El único paso que modifica un fichero del expediente. Escribe en `00_Input/_ficha_crm.yaml`, y de
ahí al CRM va `python -m scripts.crm_ficha`, que es la pieza C.

Dos reglas duras:

- **`--confirmar` obligatorio.** Sin él, `apply` dice qué haría y sale sin tocar nada.
- **Sólo claves ausentes o vacías**, y **sólo colaboradores que ya están en el YAML**. Un email que
  firma y no está en la lista no se añade: eso sería el alta que la §4 del spec deja en manos de
  Nikolai.

**Files:**
- Modify: `scripts/crm_colaboradores_firmas.py`
- Test: `tests/test_crm_colaboradores_firmas_cli.py`

**Interfaces:**
- Consumes: `extraer_de_directorio`, `VEREDICTO_ENCONTRADO` (Tasks 8-9); `yaml` (PyYAML, ya
  dependencia de `core/crm_ficha.py`).
- Produces: el comando `apply` en el mismo `app`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_crm_colaboradores_firmas_cli.py`:

```python
def _aplica(extra=None):
    return CliRunner().invoke(cli.app, ["apply", "--case-id", "W-000AAA", *(extra or [])])


def _ficha(caso):
    return case_locator.path_for(caso) / "00_Input" / "_ficha_crm.yaml"


class TestApplyNecesitaConfirmacion:

    def test_sin_confirmar_no_toca_el_fichero(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        antes = _ficha(caso).read_text(encoding="utf-8")
        r = _aplica()
        assert r.exit_code == 0, r.output
        assert _ficha(caso).read_text(encoding="utf-8") == antes
        assert "confirmar" in r.output.lower()

    def test_sin_confirmar_SI_dice_lo_que_haria(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        r = _aplica()
        assert "612345678" in r.output


class TestApplyRellenaSoloElHueco:

    def test_rellena_movil_y_telefono_vacios(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        r = _aplica(["--confirmar"])
        assert r.exit_code == 0, r.output

        import yaml
        datos = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))
        col = datos["colaboradores"][0]
        assert col["movil"] == "612345678"
        assert col["telefono"] == "931112233"

    def test_NO_pisa_un_valor_que_ya_estaba(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n"
            "    movil: '600000000'\n", encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        col = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))["colaboradores"][0]
        assert col["movil"] == "600000000", "lo que Nikolai escribio manda"
        assert col["telefono"] == "931112233", "el hueco si se rellena"

    def test_una_clave_PREPARADA_y_vacia_se_rellena(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n"
            "    movil:\n", encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        col = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))["colaboradores"][0]
        assert col["movil"] == "612345678"

    def test_el_cargo_NO_se_escribe_en_el_YAML(self, caso):
        """No hay campo de cargo en el CRM: escribirlo aqui seria dejarlo muerto."""
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])
        assert "cargo" not in _ficha(caso).read_text(encoding="utf-8")

    def test_los_telefonos_se_escriben_ENTRE_COMILLAS(self, caso):
        """Sin comillas, `movil: 0612345678` lo relee YAML como un entero octal y el
        cero inicial no se recupera. `_escalar` lo RECHAZA, asi que romperia el CLI."""
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])
        texto = _ficha(caso).read_text(encoding="utf-8")
        assert "'612345678'" in texto or '"612345678"' in texto

    def test_el_YAML_resultante_lo_puede_leer_cargar_ficha_yaml(self, caso):
        """La prueba por RESULTADO: que el siguiente eslabon lo acepte."""
        from core.crm_ficha import cargar_ficha_yaml
        _ficha(caso).write_text(
            "contrario:\n  nombre: JUAN\ncolaboradores:\n  - nombre: ANA\n"
            "    email: ana@engelvoelkers.com\n", encoding="utf-8")
        _aplica(["--confirmar"])

        ficha = cargar_ficha_yaml(_ficha(caso))
        col = ficha.colaboradores[0]
        assert (col.movil, col.telefono) == ("612345678", "931112233")


class TestApplyNoDaDeAltaANadie:
    """La §4 del spec: la lista de colaboradores la pone Nikolai."""

    def test_un_email_que_firma_y_NO_esta_en_la_lista_no_se_anade(self, caso):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: BERTA\n    email: berta@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        datos = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))
        emails = [c.get("email") for c in datos["colaboradores"]]
        assert emails == ["berta@engelvoelkers.com"]
        assert "ana@engelvoelkers.com" not in str(datos["colaboradores"])

    def test_sin_ficha_yaml_no_se_crea_una(self, caso):
        assert not _ficha(caso).exists()
        r = _aplica(["--confirmar"])
        assert r.exit_code == 1
        assert not _ficha(caso).exists()
        assert "_ficha_crm.yaml" in r.output


class TestApplyNoEscribeEnElCRM:

    def test_no_llama_a_ninguna_escritura_del_CRM(self, caso, monkeypatch):
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        actualizar = MagicMock()
        monkeypatch.setattr("core.sudespacho_relations.update_colaborador", actualizar)
        monkeypatch.setattr("core.sudespacho_relations.create_colaborador", MagicMock())
        _aplica(["--confirmar"])
        actualizar.assert_not_called()


class TestElConflictoNoSeAplica:

    def test_un_conflicto_no_escribe_nada_en_el_YAML(self, caso):
        """Dos .eml con moviles distintos para la misma persona."""
        lote = case_locator.path_for(caso) / "00_Input" / "2026-08-14_email_01"
        (lote / "dos.eml").write_text(_EML.replace("612 34 56 78", "600 00 00 00"),
                                      encoding="utf-8")
        _ficha(caso).write_text(
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.com\n",
            encoding="utf-8")
        _aplica(["--confirmar"])

        import yaml
        col = yaml.safe_load(_ficha(caso).read_text(encoding="utf-8"))["colaboradores"][0]
        assert not col.get("movil"), "en conflicto no se propone valor"
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t10`

Esperado: FALLA. `CliRunner` devuelve exit 2 con `No such command 'apply'`.

- [ ] **Step 3: Implementar `apply`**

Añadir a `scripts/crm_colaboradores_firmas.py`. Primero el import:

```python
import yaml
```

Y el comando, tras `report`:

```python
#: Que campos del consolidado van al YAML, y con que clave. **`cargo` no esta**: no hay
#: property de cargo en `colaboradores` (el CRM enumero su contrato el 2026-09-04) y
#: escribirlo aqui seria dejar un dato muerto que nadie lleva a ningun sitio.
_AL_YAML = (("movil", "movil"), ("telefono", "telefono"))


@app.command()
def apply(
    case_id: str = typer.Option(..., "--case-id", help="case_id canonico o W-code"),
    confirmar: bool = typer.Option(False, "--confirmar",
                                   help="sin esto solo dice lo que haria"),
) -> None:
    """Mete en `_ficha_crm.yaml` lo que la firma dice y el YAML no tiene.

    **No escribe en el CRM**: de ahi al CRM va `python -m scripts.crm_ficha`, que es
    quien tiene el GET -> merge -> PUT.

    **No da de alta a nadie.** Solo toca colaboradores que ya estan en la lista: el
    corpus no sabe quien es colaborador del caso (§4 del spec), y eso lo decide Nikolai.
    """
    resolved, case_dir = _caso_dir(case_id)
    ficha_path = case_dir / "00_Input" / "_ficha_crm.yaml"
    if not ficha_path.is_file():
        typer.echo(f"[ERROR] No existe {ficha_path.name}: escribe primero la lista de "
                   "colaboradores del caso. `apply` rellena huecos, no da de alta.",
                   err=True)
        raise typer.Exit(code=1)

    datos = yaml.safe_load(ficha_path.read_text(encoding="utf-8")) or {}
    if not isinstance(datos, dict):
        typer.echo("[ERROR] _ficha_crm.yaml no es un mapping YAML", err=True)
        raise typer.Exit(code=1)

    consolidados, _, ilegibles = extraer_de_directorio(case_dir / "00_Input")
    colaboradores = datos.get("colaboradores") or []

    cambios: list[str] = []
    for col in colaboradores:
        if not isinstance(col, dict):
            continue
        email = str(col.get("email") or "").strip().lower()
        c = consolidados.get(email)
        if c is None:
            continue
        for campo_c, clave in _AL_YAML:
            valor = getattr(c, campo_c)
            veredicto = getattr(c, f"veredicto_{campo_c}")
            if veredicto != VEREDICTO_ENCONTRADO or not valor:
                continue
            if str(col.get(clave) or "").strip():
                continue          # lo que ya hay manda: no se pisa
            if confirmar:
                col[clave] = valor
            cambios.append(f"{email}: {clave} = {valor}")

    if not cambios:
        typer.echo("[OK] Nada que rellenar: o el CRM ya lo tiene, o la firma no lo trae.")
    for linea in cambios:
        typer.echo(f"  {'ESCRITO' if confirmar else 'SE ESCRIBIRIA'}  {linea}")

    if ilegibles:
        typer.echo(f"[AVISO] {len(ilegibles)} .eml no se pudieron leer: eso NO es que no "
                   "tengan firma. Mira el informe de `report`.")

    if not confirmar:
        typer.echo("\nNada escrito. Repite con --confirmar para aplicarlo.")
        return

    if cambios:
        # `default_flow_style=False` + `default_style` en los telefonos: sin comillas,
        # `0612345678` lo relee YAML como octal y `_escalar` lo RECHAZA (con razon).
        for col in colaboradores:
            if isinstance(col, dict):
                for _, clave in _AL_YAML:
                    if clave in col and col[clave] is not None:
                        col[clave] = str(col[clave])
        volcado = yaml.safe_dump(datos, allow_unicode=True, default_flow_style=False,
                                 sort_keys=False)
        # Los telefonos son cadenas de digitos: se fuerzan entre comillas simples.
        for _, clave in _AL_YAML:
            volcado = volcado.replace(f"{clave}: ", f"{clave}: ", 1)
        ficha_path.write_text(volcado, encoding="utf-8")
        typer.echo(f"[OK] {ficha_path} actualizado ({len(cambios)} campos).")
        typer.echo("     Ahora: python -m scripts.crm_ficha --case-id " + resolved)
```

> **Sobre las comillas:** `yaml.safe_dump` cita por sí solo cualquier cadena que al releerse sería
> otro tipo, así que `str("612345678")` sale como `'612345678'`. Si el test
> `test_los_telefonos_se_escriben_ENTRE_COMILLAS` falla, el `str()` del bucle previo no se está
> aplicando: comprueba que `col[clave] = valor` guarda un `str` y no un `int`.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t10`

Esperado: PASA.

- [ ] **Step 5: Commit**

```bash
git add scripts/crm_colaboradores_firmas.py tests/test_crm_colaboradores_firmas_cli.py
git commit -m "feat(firmas): apply escribe en el _ficha_crm.yaml, y solo en las claves vacias

El unico paso que modifica un fichero del expediente, y no escribe en el CRM: de ahi al
CRM va scripts.crm_ficha, que tiene el GET -> merge -> PUT. Un solo camino de escritura.

Tres reglas duras: --confirmar obligatorio, solo claves ausentes o vacias (lo que
Nikolai escribio manda), y solo colaboradores QUE YA ESTAN en la lista —un email que
firma y no esta no se anade, porque el alta es su decision (§4 del spec)—.

Los telefonos salen entre comillas: sin ellas `0612345678` se relee como octal y
_escalar lo rechaza. El test que lo prueba por RESULTADO es que cargar_ficha_yaml
acepte el fichero resultante.

El cargo NO se escribe: no hay property de cargo en el CRM y seria un dato muerto."
```

- [ ] **Step 6: Mutación — `apply` pisa lo que ya hay**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("scripts/crm_colaboradores_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = """            if str(col.get(clave) or "").strip():
                continue          # lo que ya hay manda: no se pisa
"""
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, ""), encoding="utf-8")
print("MUTADO: pisa lo que ya estaba")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t10m`

Esperado: **falla** `test_NO_pisa_un_valor_que_ya_estaba`.

Restaurar: `git checkout -- scripts/crm_colaboradores_firmas.py`

- [ ] **Step 7: Mutación — `apply` da de alta al que firma**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("scripts/crm_colaboradores_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = """        c = consolidados.get(email)
        if c is None:
            continue"""
nuevo = """        c = consolidados.get(email)
        if c is None:
            for otro, oc in consolidados.items():
                if not any(str(x.get("email") or "").lower() == otro
                           for x in colaboradores if isinstance(x, dict)):
                    colaboradores.append({"nombre": otro.split("@")[0].upper(),
                                          "email": otro})
            continue"""
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: anade a los que firman y no estan")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t10n`

Esperado: **falla** `test_un_email_que_firma_y_NO_esta_en_la_lista_no_se_anade`. Es la frontera de
la §4 del spec: el corpus no sabe quién es colaborador del caso.

Restaurar: `git checkout -- scripts/crm_colaboradores_firmas.py`

- [ ] **Step 8: Mutación — aplicar el conflicto**

```bash
.venv/Scripts/python.exe - <<'PY'
import pathlib
p = pathlib.Path("scripts/crm_colaboradores_firmas.py")
t = p.read_text(encoding="utf-8")
viejo = "            if veredicto != VEREDICTO_ENCONTRADO or not valor:"
nuevo = "            if not valor:"
assert t.count(viejo) == 1
p.write_text(t.replace(viejo, nuevo), encoding="utf-8")
print("MUTADO: el veredicto deja de filtrar")
PY
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_crm_colaboradores_firmas_cli.py -q -p no:randomly --basetemp=C:/t/t10o`

Esperado: **no muerde**, y eso está bien: `consolidar` ya vacía el valor en conflicto, así que el
filtro por veredicto es una **segunda** puerta sobre la misma frontera. Compruébalo mutando también
la primera (`return "", VEREDICTO_CONFLICTO` → `return candidatos[-1], …`, Task 8 paso 6) **a la
vez**: entonces `test_un_conflicto_no_escribe_nada_en_el_YAML` sí debe caer. Si con las dos mutadas
sigue verde, ese test no comprueba lo que dice y hay que arreglarlo.

Restaurar: `git checkout -- scripts/crm_colaboradores_firmas.py core/email_firmas.py`

---

### Task 11: Docs, suite completa, y validación en vivo sobre W-02Q38C

**Files:**
- Modify: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:427-430` (§9 punto 4)
- Modify: `docs/INTEGRACION_SUDESPACHO.md` (§10, el contrato de `colaboradores`)
- Modify: `docs/MEJORAS_FUTURAS.md` (la deuda declarada del §9 del spec)

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: nada de código.

- [ ] **Step 1: Actualizar el RUNBOOK §9 punto 4**

Sustituir el punto 4 de la checklist (que hoy describe el trabajo a mano) por:

```markdown
4. **Colaboradores (TL + consultores):** `ensure_colaborador_vinculado(...)` — dedup por
   **email Y NIF** (`nif_cif`; la property `nif` NO existe y devolvía 500, corregido
   2026-09-04). Si el colaborador **ya existe**, la ficha se **completa sola**: rellena
   los campos vacíos del CRM con los del `_ficha_crm.yaml`, sin pisar lo que ya hay.
   Vale igual para judicial (`..._judicial`): las dos jurisdicciones pasan por el mismo
   resolvedor.

   **Móvil y fijo desde la firma del correo** (ya no es un paso a mano):

   ```powershell
   python -m scripts.crm_colaboradores_firmas report --case-id W-XXXXXX
   # lee 01_Procesado/_firmas_colaboradores.md y decide
   python -m scripts.crm_colaboradores_firmas apply --case-id W-XXXXXX --confirmar
   python -m scripts.crm_ficha --case-id W-XXXXXX
   ```

   Tres cosas del informe que hay que leer, no saltarse:
   - **`FIRMA_SIN_CAMPO` no es «no tiene».** Una de las dos plantillas corporativas de
     E&V no lleva móvil.
   - **`CONFLICTO`** = dos valores y ninguno decide; no se propone nada. Decides tú.
   - **La sección «Candidatos» no es un alta.** Aparecer en un correo del caso no te
     hace colaborador del caso: en W-02Q38C había 7 direcciones de E&V en 6 correos y
     sólo 3 vinculadas. **La lista la pones tú en el `_ficha_crm.yaml`.**

   **`colaboradores` = personal PROPIO del cliente (E&V) — nunca el procurador/letrado
   de la parte contraria** (fácil de confundir por el nombre del campo).

   **No hay campo de cargo.** `tipo` es un `Select` cerrado
   (Sin Asignar / Colaborador / Perito / Tercero): el cargo sale en el informe y no se
   escribe en el CRM (decisión de Nikolai, 2026-09-04).
```

- [ ] **Step 2: Documentar el contrato de `colaboradores` en INTEGRACION**

Localizar la sección de elementos (§10) y añadir, tras el bloque de `clientes_contrarios`:

```markdown
#### 10.9 `colaboradores` — contrato enumerado por el propio CRM (2026-09-04)

Pedido con una property inventada (`?properties=__inventada__`), cuyo **HTTP 500 enumera
el contrato entero** — el método del §14.6:

```
ccc, cp, direccion, email, fax, iva, movil, nacionalidad, nif_cif, nombre, notas,
poblacion, provincia, telefono1, telefono2, telefono3, tipo, web,
id, grupo_contable_id, id_creador, id_ultimo_modificador,
fecha_creacion, fecha_ultima_modificacion
```

Tres consecuencias que costaron un día de suposiciones:

- **El NIF es `nif_cif`, igual que en el contrario.** La property `nif` **no existe** y
  devuelve 500. `_PROP_NIF["colaboradores"]` decía `"nif"`, así que
  `resolver_parte("colaboradores", nif=…)` marcaba el criterio `sin_comprobar` y
  `_resolver_colaborador` **abortaba el alta** en cuanto la ficha traía un NIF: la dedup
  por NIF del colaborador no había funcionado nunca. El atlas ya lo decía bien.
- **No hay property de cargo/puesto.** `tipo` es un `Select` con enum cerrado
  (`-1=Sin Asignar, colaborador=Colaborador, perito=Perito, tercero=Tercero`): escribir
  un puesto ahí corrompe la taxonomía. Los únicos huecos de texto libre son `notas`
  (`EditorHtmlSimple`) y `web`.
- **El fijo va a `telefono1`** (hay `telefono2` y `telefono3`, sin uso hoy).

Lectura y escritura: `get_colaborador(id)` / `update_colaborador(id, cambios)` en
`core/sudespacho_relations.py`. El GET plano da 500: `?properties=` es obligatorio
(`[APER-26]`). **Se pide el conjunto escribible completo**, porque
`_completar_colaborador_existente` hace GET → merge → PUT y para este elemento **no está
medido** si el PUT es parcial o de reemplazo; mandar el conjunto completo es correcto
bajo las dos hipótesis.
```

- [ ] **Step 3: Anotar la deuda declarada en MEJORAS_FUTURAS**

Añadir al final del backlog, con el número que siga al último:

```markdown
### #NNN — Documento de identidad y domicilio del colaborador desde los contratos del Drive

**Estado:** esperando decisión de Nikolai. **No empezar.**

Los contratos de los consultores llevan documento de identidad y domicilio de empleados
de E&V que **no son parte de ningún caso**. La cuenta `@ev` accede a ellos por el rol en
la empresa; volcarlos al CRM del despacho es un tratamiento con otra finalidad y otro
responsable, y esa valoración es de Nikolai.

Y puede ser innecesario: si lo que se busca es **identificar** al colaborador, el email
ya lo hace; el NIF sólo hace falta para facturarle o demandarle.

**Si se promueve:** preguntar primero **para qué colaboradores y con qué finalidad**. No
construir un extractor masivo de documentos y domicilios.

**Disparador:** petición expresa de Nikolai con esas dos respuestas.

### #NNN+1 — El cargo del colaborador no tiene dónde vivir en el CRM

`core/email_firmas.py` **ya extrae** el cargo y sale en el informe de
`scripts.crm_colaboradores_firmas report`, pero no se escribe: el contrato de
`colaboradores` no tiene property de cargo y `tipo` es un `Select` cerrado
(§10.9 de `INTEGRACION_SUDESPACHO.md`).

**Disparador:** que sudespacho añada un campo, o decisión de Nikolai de usar `notas`.
Si llega el campo, sólo hay que añadir el par a `_COMPLETABLES_COLABORADOR` y a
`_AL_YAML`.

### #NNN+2 — `scripts/crm_ficha.py` sigue siendo extrajudicial-only

`[APER-49]`. La pieza C sirve a las dos jurisdicciones (las dos pasan por
`_resolver_o_crear_colaborador`), pero el CLI que la dispara hardcodea
`_ELEMENT_EXTRAJUDICIAL`. Para un caso judicial hay que llamar a mano.

**Hueco previo a este trabajo**, anotado para que no se lea como cerrado.
```

- [ ] **Step 4: Correr la suite ENTERA con la primera semilla**

Ninguna corrida en background: una corrida no congela el árbol, y seguir escribiendo
mientras corre produce un rojo falso.

Run: `.venv/Scripts/python.exe -m pytest -q --tb=short -p randomly --randomly-seed=777 --basetemp=C:/t/s7 --junit-xml=C:/t/j777.xml`

Esperado: 0 fallos. **El conteo no se transcribe a `CLAUDE.md`**; se cuenta por el XML:

Run: `.venv/Scripts/python.exe -c "import xml.etree.ElementTree as E; r=E.parse('C:/t/j777.xml').getroot(); print(r.attrib)"`

- [ ] **Step 5: Correr la suite ENTERA con la segunda semilla**

Un verde con una sola semilla no prueba el orden; un rojo que sólo aparece aislado es herencia de
estado, no flakiness.

Run: `.venv/Scripts/python.exe -m pytest -q --tb=short -p randomly --randomly-seed=31337 --basetemp=C:/t/s3 --junit-xml=C:/t/j31337.xml`

Esperado: 0 fallos, y el mismo `tests=` que la semilla 777. Una diferencia de conteo entre semillas
es una bandera roja: hay un test que se salta según el orden.

- [ ] **Step 6: Validación en vivo sobre W-02Q38C, en modo `report` (SÓLO LECTURA)**

`report` no escribe en el CRM ni en el expediente más que su propio informe. El caso tiene 6 `.eml`
y 3 colaboradores vinculados (40, 61, 466), uno de ellos sin móvil.

Run: `.venv/Scripts/python.exe -m scripts.crm_colaboradores_firmas report --case-id W-02Q38C`

Necesita `SUDESPACHO_API_KEY` y `CASOS_ROOT` en el entorno: **el worktree no hereda `.env`**. Si
`resolver_parte` devuelve `sin_comprobar`, el informe lo dirá y eso es correcto — no lo tapes.

Comprobar en el informe, contra lo medido el 2026-09-04:
- Aparecen las direcciones que **firman**, no las 7 que aparecen.
- El colaborador **sin móvil** sale con el móvil de su firma propuesto y marcado como hueco.
- Los que **ya tienen** móvil salen con «el CRM ya tiene …, **no se toca**».
- La sección de candidatos lista las direcciones que aparecen y no firman.
- La sección «Lo que NO se pudo mirar» dice `Todos los .eml se leyeron` o lista los que no.

**No corras `apply` sobre el caso real en esta task.** Eso lo decide Nikolai leyendo el informe.

- [ ] **Step 7: Verificar que nada del expediente entró en el repo**

Run: `git status --porcelain`

Esperado: **ningún** fichero bajo `data/CASOS/` y **ningún** `_firmas_colaboradores.md`. El informe
lleva PII y vive en el expediente.

Run: `.venv/Scripts/python.exe scripts/precommit_leak_guard.py $(git diff --cached --name-only)`

Esperado: EXIT 0.

- [ ] **Step 8: Commit y PR**

```bash
git add docs/RUNBOOK_APERTURA_EXPEDIENTE.md docs/INTEGRACION_SUDESPACHO.md docs/MEJORAS_FUTURAS.md
git commit -m "docs: el contrato de colaboradores lo enumero el CRM, y §9.4 deja de ser manual

INTEGRACION §10.9 nuevo con el contrato enumerado por el propio CRM y las tres
consecuencias que costaron un dia de suposiciones: el NIF es nif_cif y `nif` no existe,
no hay property de cargo, y el fijo va a telefono1.

RUNBOOK §9.4 pasa de describir el trabajo a mano a los tres comandos, con las tres
cosas del informe que no se pueden saltar: FIRMA_SIN_CAMPO no es «no tiene», CONFLICTO
no propone nada, y los candidatos no son un alta.

MEJORAS: la deuda declarada del §9 del spec — el punto 3 del encargo esperando decision,
el cargo sin donde vivir, y crm_ficha.py extrajudicial-only."
```

```bash
git push -u origin HEAD
gh pr create --title "feat(crm): las fichas de colaborador se rellenan desde la firma del correo" --body-file docs/superpowers/specs/2026-09-04-colaboradores-firma-autorrelleno-design.md
```

- [ ] **Step 9: Ronda adversarial sobre el diff, y adjudicarla**

Radio de daño: escribe en el CRM del cliente pero **sólo rellena lo vacío** → **una ronda sobre el
diff** (`CLAUDE.md` §«Cuántas rondas»). **Techo duro: no hay segunda ni tercera sin que Nikolai la
autorice.**

Invocación de Codex: memoria `reference-codex-cli-invocacion-revision` — binario con
`code-mode-host` al lado, y el objeto en una copia externa vía `git archive` (el worktree detached
muere por `dubious ownership` del sandbox). **Solo lectura, sin escribir en el repo**, informe a un
fichero **fuera** del repo, y devuelve ruta + `sha256`.

Al adjudicar:
- Cada hallazgo **contra la fuente**, no contra el diff ni contra la seguridad con que venga escrito.
- **Ante cada hallazgo, preguntar «¿de qué frontera es esto un ejemplo?»** antes de remediarlo. Las
  cuatro rondas del mutex encontraron cuatro veces la misma propiedad mal cerrada porque cada vez se
  remedió el caso del informe y no la propiedad.
- La adjudicación va **embebida** en este plan, con el encabezado canónico y su ficha; el informe
  del revisor va **literal** a `docs/superpowers/specs/2026-09-04-colaboradores-firma-r1-adversarial-review.md`
  con su digest. Los guards **G7 y G8** de `tests/test_docs_gobernanza.py` lo comprueban y
  recomputan el digest.
- **Si Codex no puede correr, se declara la cobertura AUSENTE**, nunca refutada. Cabe revisor
  sustituto (sesión limpia de Claude Code, sin el contexto de autoría) registrado como
  `revisor: Claude Code (sesión independiente)`, nunca como «Codex».

---

## Autorrevisión del plan completo

**Cobertura del spec, sección por sección:**

| Spec | Task |
|---|---|
| §3 H-01 (3 de 6 sin marcador) | 5 |
| §3 H-02 (la firma no es la del `From:`) | 6 (parcial) + **9 (cerrada, con cabecera real)** |
| §3 H-03 (dos plantillas, valores sucios) | 7 |
| §3 H-04 (plantilla sin móvil) | 7 + 8 |
| §3 H-05 (`nif` no existe) | 1 |
| §3 H-06 (no hay cargo) | 3 (no se pide), 7 (se extrae), 10 (no se escribe), 11 (se documenta) |
| §3 H-07 (el corpus no perdió la firma) | Fundamenta la elección del `.eml`; sin código propio |
| §4 (el alta la decide el humano) | 9 (candidatos) + 10 (no añade a nadie) |
| §5.1 pieza A | 5, 6, 7, 8, 9 |
| §5.2 pieza B | 9 (`report`), 10 (`apply`) |
| §5.3 pieza C | 3, 4 |
| §5.3(a) GET completo → PUT completo | 3 |
| §5.3(b) resolvedor compartido | 4 |
| §6 los seis veredictos | 7 (constantes), 8 (`FIRMA_SIN_CAMPO`/`CONFLICTO`), 9 (`NO_LEIBLE`) |
| §7 D1 | 1 |
| §7 D2 | 2 |
| §8 las cinco mutaciones | 1, 4, 5, 6, 7, 8, 9, 10 — **17 mutantes en total**, más de los cinco que el spec pedía |
| §9 deuda declarada | 11 |

**Un hueco que declaro en vez de tapar:** `VEREDICTO_SIN_FIRMA` y `VEREDICTO_NO_ATRIBUIBLE` quedan
definidos y **no los emite nadie**. `SIN_FIRMA` sería el veredicto de una dirección que aparece en el
corpus sin firmar, y hoy eso se expresa como «candidato»; `NO_ATRIBUIBLE` lo cuenta `sin_atribuir`
pero no llega al informe. **No son código muerto por descuido: son las dos formas de "no lo sé" que
el informe expresa con otras palabras.** Si la ronda adversarial lo señala, la remediación correcta
es emitirlos o retirarlos, no renombrarlos.

**Consistencia de tipos:** `Consolidado.veredicto_<campo>` se lee en Task 9 (`_fila`) y Task 10
(`getattr(c, f"veredicto_{campo_c}")`) con los mismos nombres que la Task 8 define
(`veredicto_movil`, `veredicto_telefono`, `veredicto_cargo`). `_AL_YAML` usa `("movil","movil")` y
`("telefono","telefono")` — el campo del `Consolidado` y la clave del YAML, que coinciden por
casualidad; `_COMPLETABLES_COLABORADOR` es el que traduce `telefono` → `telefono1` al llegar al CRM.
