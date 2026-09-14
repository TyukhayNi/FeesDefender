---
tipo: plan
estado: vigente
creado: 2026-09-14
spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md §§5, 5.1, 5.2, 21.3
---

# V2 — el lazo del CRM dentro de la secuencia (P1, primera mitad)

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development`
> o `superpowers:executing-plans` para ejecutar este plan tarea a tarea. Los pasos usan casillas
> (`- [ ]`) para el seguimiento.

**Goal:** que `--modo v1` deje de exigir `--crm skip` y pueda cerrar el lazo del CRM —alta, ficha,
actuación y verificación— como cuatro etapas más del secuenciador que ya existe.

**Architecture:** cuatro `Etapa` nuevas en `scripts/abrir_caso.py`, construidas sobre funciones que
**ya están escritas** (`_alta_crm`, `scripts/crm_ficha`, `core.sudespacho_actuaciones.alta_actuacion`,
`core.verificar_apertura`). `core/apertura_v1.py::secuenciar` **no se toca**: recibe las etapas como
invocables y añadir etapas no cambia su contrato. Lo único que se sustituye es la puerta del
`--crm skip`.

**Tech Stack:** Python 3, `typer`, `pytest`. Sin dependencias nuevas.

## Global Constraints

- **NO hay spec nuevo.** El diseño vive en `§5` (alta inicial), `§5.1` (alta mínima y **ficha
  diferida**), `§5.2` (resultado remoto desconocido) y `§21.3` (qué sale de V1) del spec orquestador,
  ya revisado en cinco rondas. Este plan **no rediseña**: cablea.
- **Esto es V2, NO V3.** `email`, `sala_lectura` y `viabilidad` **no entran** (`§21.3`). Y la
  **ejecución de la fase 8.1** —la ficha *completa* del contrario— es **posterior a V3**: mandarla a
  V2 suprimiría dos precondiciones suyas, y el spec ya llamó a eso «derogar, no diferir» tras una
  adjudicación. La etapa `crm_ficha` de este plan lleva al CRM **el YAML que exista**, nada más.
- **En medio la máquina no pregunta: declara `Pendiente`** (P0 del handoff). Ninguna etapa nueva
  puede abortar la secuencia por falta de un dato humano.
- **El `firmante` no se infiere nunca.** El prefijo del asunto **es la tarifa** (`SENIOR` 103 €/h,
  `ABOGADO` 77 €/h) y quien firma no es quien opera. Ausente → `Pendiente`.
- **Vocabulario cerrado:** `EtapaResultado.estado ∈ ("hecha", "saltada", "fallo")`;
  `Pendiente(codigo, detalle)`. `saltada` **no** es `hecha`: significa que la etapa decidió, con
  razón declarada, que no había nada que hacer.
- **Windows + PowerShell**, UTF-8 sin BOM, ningún test escribe en el árbol de producción.
- **La prueba de aceptación es CORRERLA** contra el expediente de prueba **636**, y borrar lo
  creado. Medido el 2026-09-14: 5.612 tests verdes y 39 mutantes muertos no vieron tres defectos
  que una sola ejecución real encontró.

---

### Task 1: `ETAPAS_V2` y la puerta que se sustituye, no se borra

**Files:**
- Modify: `scripts/abrir_caso.py:55` (`ETAPAS_V1`) y `:1287-1292` (la puerta del `--crm skip`)
- Test: `tests/test_abrir_caso_v2_puerta.py` (crear)

**Interfaces:**
- Produces: `ETAPAS_V2: tuple[str, ...]` = `("drive", "crm", "sala_maquina", "crm_alta",
  "crm_ficha", "actuacion", "verificar")`; `ETAPAS_V1` se conserva con sus tres nombres.

**Por qué la puerta no se borra.** Hoy dice «`--modo v1` no escribe en el CRM: exige `--crm skip`».
Esa puerta protege una propiedad real —que nadie escriba en el CRM por accidente— y la propiedad
sigue valiendo. Lo que cambia es cómo se garantiza: en vez de prohibir la escritura, se exige que
**toda escritura esté en el vocabulario de etapas** y que `--hasta` permita parar antes de
cualquiera de ellas.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_abrir_caso_v2_puerta.py`:

```python
"""La puerta del CRM en el modo secuenciado: se sustituye, no se borra.

`--modo v1` exigia `--crm skip` porque ninguna de sus tres etapas escribia en el
CRM. V2 anade cuatro que si, asi que la puerta pasa de «prohibido escribir» a
«solo se escribe lo que esta en el vocabulario de etapas».
"""

import scripts.abrir_caso as ac


def test_las_etapas_de_v2_incluyen_las_tres_de_v1_en_orden():
    # V2 AMPLIA V1, no lo reordena: un `--hasta sala_maquina` tiene que seguir
    # parando donde paraba.
    assert ac.ETAPAS_V2[:3] == ac.ETAPAS_V1


def test_las_cuatro_etapas_nuevas_estan_y_en_orden():
    assert ac.ETAPAS_V2[3:] == ("crm_alta", "crm_ficha", "actuacion", "verificar")


def test_el_modo_v1_ya_no_exige_crm_skip():
    errores = ac._errores_de_modo_v1(crm="api", hasta=None, fuente="drive_ev",
                                     force=False, dry_run=False, folder_id="X",
                                     case_id=None)
    assert not [e for e in errores if "--crm skip" in e]


def test_hasta_admite_una_etapa_nueva():
    errores = ac._errores_de_modo_v1(crm="api", hasta="crm_ficha", fuente="drive_ev",
                                     force=False, dry_run=False, folder_id="X",
                                     case_id=None)
    assert not [e for e in errores if "--hasta" in e]


def test_hasta_sigue_rechazando_lo_que_no_es_etapa():
    errores = ac._errores_de_modo_v1(crm="api", hasta="inventada", fuente="drive_ev",
                                     force=False, dry_run=False, folder_id="X",
                                     case_id=None)
    assert [e for e in errores if "--hasta" in e], (
        "un --hasta mal escrito no puede convertirse en «no pares»")
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_puerta.py -q --tb=short
```

Esperado: FAIL — `module 'scripts.abrir_caso' has no attribute 'ETAPAS_V2'`.

- [ ] **Step 3: Implementación mínima**

En `scripts/abrir_caso.py`, junto a `ETAPAS_V1`:

```python
ETAPAS_V1 = ("drive", "crm", "sala_maquina")
#: V2 AMPLIA V1 por la derecha: las tres primeras conservan su orden y su nombre, asi
#: que un `--hasta sala_maquina` de antes sigue parando donde paraba. Las cuatro nuevas
#: cierran el lazo del CRM (spec §§5, 5.1, 21.3).
ETAPAS_V2 = ETAPAS_V1 + ("crm_alta", "crm_ficha", "actuacion", "verificar")
```

Extraer la validación del modo a una función testeable (hoy vive inline en el comando) y
**sustituir** el bloque del `--crm skip`:

```python
def _errores_de_modo_v1(*, crm, hasta, fuente, force, dry_run, folder_id, case_id):
    """Las puertas del modo secuenciado. Se valida ANTES de tocar nada.

    La puerta del CRM NO desaparece con V2: cambia de forma. Antes prohibia escribir
    («exige --crm skip») porque ninguna de las tres etapas lo hacia. Ahora la garantia
    es otra y mas fuerte: lo unico que escribe son etapas con nombre, y `--hasta` deja
    parar antes de cualquiera de ellas.
    """
    errores = []
    if hasta is not None and hasta not in ETAPAS_V2:
        errores.append(
            f"--hasta {hasta!r} no es una etapa; validas: {list(ETAPAS_V2)}")
    if crm not in ("api", "skip"):
        errores.append(f"--crm solo admite api|skip (recibido: {crm!r})")
    # ... el resto de puertas (fuente, force, dry_run, folder_id) se mueven aqui TAL CUAL
    return errores
```

**Nota para quien implemente:** las demás puertas (`--fuente`, `--force`, `--dry-run`,
`--folder-id`) se trasladan **sin cambiar ni una palabra de su mensaje**. Este plan solo sustituye
la del CRM.

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_puerta.py -q --tb=short
```

Esperado: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_v2_puerta.py
git commit -m "V2: la puerta del CRM se sustituye, no se borra"
```

---

### Task 2: Etapa `crm_alta`

**Files:**
- Modify: `scripts/abrir_caso.py` (función nueva junto a `etapa_sala_maquina`, ~:824)
- Test: `tests/test_abrir_caso_v2_etapas.py` (crear)

**Interfaces:**
- Consumes: `_alta_crm(...)` (ya existe, `:1012`), con su política de duplicados
  (`core.alta_crm_politica.decidir`) y su mutex.
- Produces: `etapa_crm_alta(ident, case_dir, *, alta=None) -> av1.EtapaResultado`.

**Lo que esta etapa NO hace:** reimplementar el alta. `_alta_crm` ya resuelve duplicados, tags,
normalización telefónica y el evento; la etapa solo la invoca y traduce su resultado al vocabulario
de V1. Duplicarla sería exactamente lo que costó las 838 líneas de la fila #29.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_abrir_caso_v2_etapas.py`:

```python
"""Las cuatro etapas de V2, con sus dependencias INYECTADAS.

Ninguna toca el CRM real: cada etapa recibe su efecto por parametro, que es el
mismo patron de `etapa_sala_maquina(ident, *, correr=None)`.
"""

import types

import pytest

import core.apertura_v1 as av1
import scripts.abrir_caso as ac


class _Ident:
    case_id = "W-TEST1"


def test_crm_alta_que_crea_el_expediente_sale_hecha(tmp_path):
    res = ac.etapa_crm_alta(_Ident(), tmp_path, alta=lambda: "642")

    assert res.nombre == "crm_alta"
    assert res.estado == "hecha"
    assert "642" in res.detalle


def test_crm_alta_no_duplica_si_ya_hay_expediente(tmp_path):
    # `saltada` NO es `hecha`: la etapa decidio, con razon declarada, que no
    # habia nada que hacer.
    res = ac.etapa_crm_alta(_Ident(), tmp_path, alta=lambda: None)

    assert res.estado == "saltada"


def test_crm_alta_traduce_un_fallo_sin_reventar(tmp_path):
    def _explota():
        raise RuntimeError("el CRM dijo 500")

    res = ac.etapa_crm_alta(_Ident(), tmp_path, alta=_explota)

    assert res.estado == "fallo"
    assert "500" in res.detalle
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short
```

Esperado: FAIL — `has no attribute 'etapa_crm_alta'`.

- [ ] **Step 3: Implementación mínima**

```python
def etapa_crm_alta(ident, case_dir: Path, *, alta=None) -> av1.EtapaResultado:
    """Etapa 4 (V2): alta del expediente en el CRM, si no lo hay ya.

    NO reimplementa el alta: invoca `_alta_crm`, que ya resuelve duplicados con
    `core.alta_crm_politica`, tags, telefono y evento, y corre bajo el mutex.

    `alta` se inyecta para poder probarla sin tocar el CRM, igual que `correr` en
    `etapa_sala_maquina`.
    """
    def _alta():
        return _alta_crm(ident, case_dir)

    try:
        exp_id = (alta or _alta)()
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="crm_alta", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    if not exp_id:
        return av1.EtapaResultado(
            nombre="crm_alta", estado="saltada",
            detalle="el caso ya tiene expediente CRM vinculado; no se da de alta otro")
    return av1.EtapaResultado(nombre="crm_alta", estado="hecha",
                              detalle=f"expediente CRM {exp_id}")
```

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short
```

Esperado: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_v2_etapas.py
git commit -m "V2: etapa crm_alta, que invoca el alta existente en vez de duplicarla"
```

---

### Task 3: Etapa `crm_ficha` — la que declara pendientes en vez de preguntar

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_abrir_caso_v2_etapas.py` (añadir)

**Interfaces:**
- Consumes: `core.crm_ficha.cargar_ficha_yaml(path) -> FichaCRMInput` (ya existe, `:144`).
- Produces: `etapa_crm_ficha(ident, case_dir, *, llevar=None) -> av1.EtapaResultado`.

**Esta es la etapa donde el P0 del handoff se gana o se pierde.** El `_ficha_crm.yaml` lo escribe
un humano (con ayuda de `scripts.crm_colaboradores_firmas apply`, que rellena los colaboradores
desde las firmas de los correos). Si no está, la etapa **no pregunta y no aborta**: declara un
`Pendiente` y la secuencia continúa hasta el final.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_abrir_caso_v2_etapas.py`:

```python
def test_crm_ficha_sin_yaml_declara_pendiente_y_NO_aborta(tmp_path):
    # El YAML lo teclea un humano. Su ausencia es un pendiente, no un fallo: si
    # fuera fallo, `secuenciar` cortaria y las etapas siguientes no correrian.
    (tmp_path / "00_Input").mkdir(parents=True)

    res = ac.etapa_crm_ficha(_Ident(), tmp_path)

    assert res.estado == "saltada", "sin YAML la secuencia SIGUE"
    assert [p.codigo for p in res.pendientes] == ["ficha_crm_sin_yaml"]


def test_crm_ficha_con_yaml_lo_lleva_al_crm(tmp_path):
    (tmp_path / "00_Input").mkdir(parents=True)
    (tmp_path / "00_Input" / "_ficha_crm.yaml").write_text(
        "contrario:\n  nombre: FULANO DE TAL\n", encoding="utf-8")
    llevadas = []

    res = ac.etapa_crm_ficha(_Ident(), tmp_path, llevar=lambda f: llevadas.append(f))

    assert res.estado == "hecha"
    assert len(llevadas) == 1


def test_crm_ficha_con_yaml_invalido_es_FALLO_no_pendiente(tmp_path):
    # Un YAML que EXISTE y esta mal es distinto de uno que no esta: alguien lo
    # escribio creyendo que servia. Tragarlo como «pendiente» lo haria invisible.
    (tmp_path / "00_Input").mkdir(parents=True)
    (tmp_path / "00_Input" / "_ficha_crm.yaml").write_text(
        "contrario:\n  sin_nombre: x\n", encoding="utf-8")

    res = ac.etapa_crm_ficha(_Ident(), tmp_path)

    assert res.estado == "fallo"
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short -k crm_ficha
```

Esperado: FAIL — `has no attribute 'etapa_crm_ficha'`.

- [ ] **Step 3: Implementación mínima**

```python
def etapa_crm_ficha(ident, case_dir: Path, *, llevar=None) -> av1.EtapaResultado:
    """Etapa 5 (V2): lleva `_ficha_crm.yaml` al CRM, si lo hay.

    **Ausencia y error NO son lo mismo, y esa distincion es el contenido de esta
    etapa.** Que el YAML no exista es el estado normal de un caso cuyo humano aun
    no lo ha escrito: `Pendiente`, y la secuencia sigue hasta el final (P0). Que
    exista y no se pueda interpretar es otra cosa: alguien lo escribio creyendo
    que servia, y tragarlo como pendiente lo haria invisible.

    Esta etapa lleva **el YAML que haya**. La ficha COMPLETA del contrario (§8.1)
    es posterior a V3: depende de la sala de lectura y de la viabilidad.
    """
    from core import crm_ficha as cf

    ruta = Path(case_dir) / "00_Input" / "_ficha_crm.yaml"
    if not ruta.exists():
        return av1.EtapaResultado(
            nombre="crm_ficha", estado="saltada",
            detalle="no hay _ficha_crm.yaml: la ficha del CRM queda sin completar",
            pendientes=(av1.Pendiente(
                codigo="ficha_crm_sin_yaml",
                detalle=f"Escribe {ruta} y relanza con --hasta crm_ficha. "
                        "`python -m scripts.crm_colaboradores_firmas apply` rellena "
                        "los colaboradores desde las firmas de los correos."),))
    try:
        ficha = cf.cargar_ficha_yaml(ruta)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(
            nombre="crm_ficha", estado="fallo",
            detalle=f"_ficha_crm.yaml existe pero no se pudo interpretar: {exc}")

    def _llevar(f):
        from scripts import crm_ficha as orquestador
        return orquestador.main(case_id=ident.case_id)

    try:
        (llevar or _llevar)(ficha)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="crm_ficha", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    return av1.EtapaResultado(nombre="crm_ficha", estado="hecha",
                              detalle=f"{len(ficha.contrarios)} contrario(s), "
                                      f"{len(ficha.colaboradores)} colaborador(es)")
```

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short
```

Esperado: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_v2_etapas.py
git commit -m "V2: etapa crm_ficha — ausencia es pendiente, error es fallo"
```

---

### Task 4: Etapa `actuacion`

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_abrir_caso_v2_etapas.py` (añadir)

**Interfaces:**
- Consumes: `core.sudespacho_actuaciones.alta_actuacion(elemento, exp_id, referencia_esperada, *,
  asunto, firmante, duracion_s=None, ...) -> Recibo` (ya existe, `:1077`).
- Produces: `etapa_actuacion(ident, case_dir, *, alta=None, firmante=None) -> av1.EtapaResultado`.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_actuacion_sin_firmante_declara_pendiente(tmp_path):
    # El prefijo del asunto ES la tarifa (SENIOR 103 €/h, ABOGADO 77 €/h) y quien
    # firma no es quien opera. No se infiere JAMAS del actor de la UI.
    res = ac.etapa_actuacion(_Ident(), tmp_path, firmante="")

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["actuacion_sin_firmante"]


def test_actuacion_con_firmante_la_da_de_alta(tmp_path):
    llamadas = []

    res = ac.etapa_actuacion(_Ident(), tmp_path, firmante="NIKOLAI TYUKHAY",
                             alta=lambda **kw: llamadas.append(kw) or "recibo")

    assert res.estado == "hecha"
    assert llamadas[0]["firmante"] == "NIKOLAI TYUKHAY"
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short -k actuacion
```

Esperado: FAIL — `has no attribute 'etapa_actuacion'`.

- [ ] **Step 3: Implementación mínima**

```python
def etapa_actuacion(ident, case_dir: Path, *, alta=None, firmante=None
                    ) -> av1.EtapaResultado:
    """Etapa 6 (V2): la actuacion de apertura, con la receta de seis pasos.

    **El `firmante` no se infiere nunca.** El prefijo del asunto ES la tarifa
    —`SENIOR` factura 103,00 €/h y `ABOGADO` 77,00— y quien firma no es quien
    opera: Ana puede tramitar lo que firma Nikolai. Sin ese dato, `Pendiente`.
    """
    quien = firmante if firmante is not None else _firmante_de(case_dir)
    if not quien:
        return av1.EtapaResultado(
            nombre="actuacion", estado="saltada",
            detalle="sin firmante declarado: la actuacion decide la tarifa",
            pendientes=(av1.Pendiente(
                codigo="actuacion_sin_firmante",
                detalle="Declara `firmante:` en _ficha_crm.yaml. El prefijo del asunto "
                        "es la tarifa, asi que este dato no se infiere del operador."),))

    def _alta(**kw):
        from core import sudespacho_actuaciones as sa
        return sa.alta_actuacion(**kw)

    try:
        (alta or _alta)(firmante=quien, case_id=ident.case_id)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="actuacion", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    return av1.EtapaResultado(nombre="actuacion", estado="hecha",
                              detalle=f"actuacion de apertura, firma {quien}")
```

**Nota:** `_firmante_de(case_dir)` lee `firmante:` de `_ficha_crm.yaml` con
`cf.cargar_ficha_yaml` y devuelve `""` si el fichero no existe. Se escribe en esta misma tarea.

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short
```

Esperado: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_v2_etapas.py
git commit -m "V2: etapa actuacion — el firmante no se infiere, se declara"
```

---

### Task 5: Etapa `verificar` y cableado de la secuencia

**Files:**
- Modify: `scripts/abrir_caso.py` (`etapa_verificar` + `secuencia_v1` → `secuencia_v2`)
- Test: `tests/test_abrir_caso_v2_etapas.py` (añadir)

**Interfaces:**
- Consumes: `core.verificar_apertura` (las nueve comprobaciones ya construidas, P2).
- Produces: `etapa_verificar(ident, case_dir, *, verificar=None) -> av1.EtapaResultado` y
  `secuencia_v2(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None) -> ResultadoV1`.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_verificar_traduce_cada_comprobacion_a_pendientes(tmp_path):
    # `verificar_apertura` da ok|pendiente|fallo por comprobacion. La etapa NO
    # colapsa eso en un booleano: cada `pendiente` viaja como Pendiente propio.
    def _falso(_case_dir):
        return [("c3_cobertura", "ok", ""),
                ("c5_viabilidad", "pendiente", "faltan 37 filas")]

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=_falso)

    assert res.estado == "hecha"
    assert [p.codigo for p in res.pendientes] == ["verificacion:c5_viabilidad"]


def test_la_secuencia_v2_tiene_las_siete_etapas_en_orden(tmp_path):
    etapas = ac._etapas_v2(_Ident(), tmp_path, folder_id="X", team_id="1")

    assert tuple(e.nombre for e in etapas) == ac.ETAPAS_V2
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short -k "verificar or secuencia_v2"
```

Esperado: FAIL — `has no attribute 'etapa_verificar'`.

- [ ] **Step 3: Implementación mínima**

```python
def etapa_verificar(ident, case_dir: Path, *, verificar=None) -> av1.EtapaResultado:
    """Etapa 7 (V2): el «OK» del EXPEDIENTE, no el del paso.

    Cada comprobacion viaja con su propio `Pendiente`: colapsar nueve resultados en
    un booleano es exactamente lo que `verificar_apertura` existe para evitar.
    """
    def _verificar(cd):
        from core import verificar_apertura as va
        return va.todas(cd)

    try:
        filas = (verificar or _verificar)(case_dir)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="verificar", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    pendientes = tuple(
        av1.Pendiente(codigo=f"verificacion:{nombre}", detalle=detalle or nombre)
        for nombre, veredicto, detalle in filas if veredicto == "pendiente")
    fallos = [n for n, v, _ in filas if v == "fallo"]
    if fallos:
        return av1.EtapaResultado(nombre="verificar", estado="fallo",
                                  detalle="comprobaciones en fallo: " + ", ".join(fallos),
                                  pendientes=pendientes)
    return av1.EtapaResultado(nombre="verificar", estado="hecha",
                              detalle=f"{len(filas)} comprobaciones",
                              pendientes=pendientes)


def _etapas_v2(ident, case_dir, *, folder_id, team_id):
    """Las siete etapas de V2, en el orden de `ETAPAS_V2`."""
    return [
        av1.Etapa("drive", lambda: etapa_drive(
            ident, case_dir, folder_id=folder_id, team_id=team_id)),
        av1.Etapa("crm", lambda: etapa_crm(ident, case_dir)),
        av1.Etapa("sala_maquina", lambda: etapa_sala_maquina(ident)),
        av1.Etapa("crm_alta", lambda: etapa_crm_alta(ident, case_dir)),
        av1.Etapa("crm_ficha", lambda: etapa_crm_ficha(ident, case_dir)),
        av1.Etapa("actuacion", lambda: etapa_actuacion(ident, case_dir)),
        av1.Etapa("verificar", lambda: etapa_verificar(ident, case_dir)),
    ]


def secuencia_v2(ident, case_dir, *, folder_id, team_id, hasta=None, etapas=None):
    """El orden completo de V2: V1 + el lazo del CRM.

    `etapas` es el punto de inyeccion de los tests. En produccion se construyen aqui.
    """
    if etapas is None:
        etapas = _etapas_v2(ident, case_dir, folder_id=folder_id, team_id=team_id)
    return av1.secuenciar(etapas, hasta=hasta)
```

**Nota:** si `core.verificar_apertura` no expone un agregador `todas(case_dir)`, esta tarea lo
añade: una función que llama a las nueve `cN_*` existentes y devuelve
`list[tuple[str, str, str]]` — `(nombre, veredicto, detalle)` con `veredicto ∈ ("ok",
"pendiente", "fallo")`. No se reescribe ninguna comprobación.

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py tests/test_abrir_caso_v2_puerta.py -q --tb=short
```

Esperado: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py core/verificar_apertura.py tests/
git commit -m "V2: etapa verificar y la secuencia de siete etapas"
```

---

### Task 6: La verja, y la prueba que de verdad acredita

- [ ] **Step 1: Suite completa con las dos semillas**

```bash
python -m scripts.session_close
```

Esperado: verde con 777 y 31337. **Cuadrar el conteo al test:** este plan añade **13** tests
(5 + 3 + 3 + 2 de las tareas 1-5, más los 2 de la 5). Partiendo de 5.713, lo esperado es **5.726**.
Cualquier otra cifra se explica, no se normaliza.

- [ ] **Step 2: CORRERLA contra el expediente de prueba 636**

Los dobles acreditan qué decide el código ante una respuesta; **nunca** que el payload sea
aceptable. Medido el 2026-09-14: con 5.612 tests verdes y 39 mutantes muertos, tres rondas no
vieron tres defectos que una sola ejecución real encontró (`Prioridad: "Normal"` inexistente →
HTTP 404, `fecha_alta` vacía, y `precio_hora` a 0,00 facturando cero con aspecto de completa).

```bash
python -m scripts.abrir_caso --modo v1 --case-id W-TEST-636 --crm api --hasta verificar --folder-id <id>
```

Verificar **por resultado, nunca por status**: releer el expediente 636 en el CRM y comprobar la
ficha, las relaciones y la actuación. **Borrar después lo que se haya creado.**

- [ ] **Step 3: Declarar lo que la corrida enseñe**

Todo defecto que aparezca aquí y no lo viera la suite se anota en el plan con su remedio: es el
dato más caro de esta pieza.

## Self-review del plan (hecho)

**Cobertura del diseño:** §5 (alta) → Task 2. §5.1 (**ficha diferida**) → Task 3, que es
exactamente «alta mínima ahora, ficha cuando haya datos». §5.2 (resultado remoto desconocido) →
Tasks 2 y 3, que traducen excepción a `fallo` sin inventar estado. §21.3 (qué sale de V1) → la
constraint global: `email`, `sala_lectura` y `viabilidad` **no aparecen en ninguna tarea**, y la
§8.1 tampoco.

**Placeholders:** ninguno. Las dos «Notas» (el traslado de las puertas en Task 1, y el agregador
`todas()` en Task 5) dicen exactamente qué hacer y con qué tipos.

**Consistencia de tipos:** las cuatro etapas devuelven `av1.EtapaResultado` con `estado ∈ ("hecha",
"saltada", "fallo")` y `pendientes: tuple[av1.Pendiente, ...]`. `_etapas_v2` produce
`list[av1.Etapa]` que `secuenciar` consume. `ETAPAS_V2` se define en Task 1 y lo leen Tasks 1 y 5.

**Riesgo que declaro:** `scripts/crm_ficha.main()` es un comando `typer`; invocarlo desde la etapa
puede lanzar `typer.Exit` en vez de devolver. La Task 3 lo envuelve en `try/except Exception`, que
**no** captura `typer.Exit` (hereda de `click.exceptions.Exit`, que deriva de `RuntimeError` en
algunas versiones y de `Exception` en otras). Quien implemente la Task 3 debe **comprobarlo** y, si
hace falta, capturar `typer.Exit` explícitamente como ya hace `etapa_sala_maquina:840`.
