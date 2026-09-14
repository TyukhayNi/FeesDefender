---
tipo: plan
estado: vigente
creado: 2026-09-14
rev: "2"
spec: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md §§5, 5.1, 5.2, 21.3
---

# V2 — el lazo del CRM dentro de la secuencia (P1, primera mitad) — rev. 2

> ## ✅ DESBLOQUEADO el 2026-09-14 — se puede implementar
>
> Estuvo **parado unas horas** por `MEJORAS #258` («no hay lectura verificable del CRM»). Resultó
> que sí la hay: el endpoint singular quiere `?properties=<cadena>` y yo pasaba `properties[0]=…`,
> que es la convención del **plural**. Con la forma correcta el instrumento distingue —`200` para
> un id que existe, `500` para uno que no—, y con él se verificó por lectura tanto un alta como su
> borrado. Detalle: `INTEGRACION_SUDESPACHO.md` §18.1.
>
> **Lo que la parada deja, y conviene conservar:** la Task 6 no puede aceptar la pieza con un
> `201`. Cada corrida contra el 636 **relee** con `?properties=…` y comprueba el `200`. Eso es
> ahora posible y es obligatorio.

## Global Constraints

- **NO hay spec nuevo.** El diseño está en `§5`, `§5.1`, `§5.2` y `§21.3` del spec orquestador, ya
  revisado en cinco rondas. Este plan cablea; no rediseña.
- **Ninguna escritura sin autorización explícita.** En el modo secuenciado, omitir `--crm` es un
  error: hay que declarar `api` o `skip`. El default `api` del modo **libre** no se toca — cambiarlo
  sería una regresión para sus llamadores.
- **`email`, `sala_lectura`, `viabilidad`, `crm_ficha` y la §8.1 NO entran.**
- **En medio la máquina no pregunta: declara `Pendiente`** (P0). Con una excepción declarada: un
  dato humano **presente y mal escrito** sí corta, porque alguien lo escribió creyendo que servía.
- **El `firmante` no se infiere nunca.** El prefijo del asunto **es la tarifa** (`SENIOR` 103 €/h,
  `ABOGADO` 77 €/h). Y el valor que viaja al CRM es el **username** (`Nikolai_Tyukhay`), no el
  nombre con espacios: la rev. 1 usaba el segundo y `alta_actuacion` levanta `ValueError`.
- **Vocabulario cerrado:** `EtapaResultado.estado ∈ ("hecha", "saltada", "fallo")`;
  `Pendiente(codigo, detalle)`.
- **Windows + PowerShell**, UTF-8 sin BOM, ningún test escribe en el árbol de producción.
- **La prueba de aceptación es CORRERLA** contra el expediente de prueba **636**, y borrar lo
  creado. Verificar **por resultado, nunca por status**.

---

### Task 0: Verificar las firmas antes de escribir una línea

**Files:** ninguno (sonda desechable en el scratchpad).

**Por qué esta tarea existe:** la rev. 1 tenía tres llamadas que no compilaban y proponía crear una
función que ya existía. No fue mala suerte: fue escribir el plan de memoria. Esta tarea cuesta dos
minutos y es la que impide repetirlo.

- [ ] **Step 1: Imprimir las firmas reales**

```bash
python -c "
import inspect
from scripts import abrir_caso as ac
from core import crm_ficha, sudespacho_actuaciones as sa, verificar_apertura as va, apertura_v1 as av1
for f in (ac._alta_crm, sa.alta_actuacion, va.verificar, av1.secuenciar):
    print(f.__module__ + '.' + f.__name__, inspect.signature(f))
print('ETAPAS_V1 =', ac.ETAPAS_V1)
print('ESTADOS_ETAPA =', av1.ESTADOS_ETAPA)
print('Resultado:', [c for c in dir(va) if c.startswith('c') and c[1].isdigit()])
"
```

**Firmas confirmadas el 2026-09-14** (si alguna difiere, **para y dilo**, no adaptes la llamada a
ciegas):

- `scripts.abrir_caso._alta_crm(ident, *, cuantia, crm_mode, yes, force=False)` → hoy `-> None`.
- `core.sudespacho_actuaciones.alta_actuacion(elemento, exp_id, referencia_esperada, *, asunto,
  firmante, duracion_s=None, vence=None, agenda=True, recordatorios=None, invitados=None,
  descripcion="", seguimientos=None, facturar=True, tipo_facturacion="duracion", unidades=None,
  precio_unidad=None, extra=None, desde=None, client=None) -> Recibo`.
- `core.verificar_apertura.verificar(case_dir, fuentes=None) -> Informe` — **ya existe**; no se
  crea ningún agregador.
- `core.apertura_v1.secuenciar(etapas, *, hasta=None) -> ResultadoV1`.

- [ ] **Step 2: Leer los estados del `Recibo` y del `Resultado`**

```bash
python -c "
from core import sudespacho_actuaciones as sa, verificar_apertura as va
import inspect
print(inspect.getsource(sa.Recibo)[:900])
print('---')
print([n for n in dir(va) if 'ESTADO' in n.upper() or 'VEREDICTO' in n.upper()])
"
```

Anotar los estados exactos del `Recibo` (`no_intentada`, `incierta`, `incompleta`, `verificada`) y
los **cuatro** del verificador (`ok`, `pendiente`, `fallo`, **`sin_implementar`**). La rev. 1
ignoraba el cuarto y lo contaba como comprobación hecha.

---

### Task 1: Autorización explícita de escritura

**Files:**
- Modify: `scripts/abrir_caso.py:55` (`ETAPAS_V1`), la validación del modo (`:1277-1330`) y
  `secuencia_v1` (`:912`)
- Test: `tests/test_abrir_caso_v2_autorizacion.py` (crear)

**Interfaces:**
- Produces: `ETAPAS_V2 = ETAPAS_V1 + ("crm_alta", "actuacion", "verificar")`;
  `_errores_de_modo(*, crm, hasta, fuente, force, dry_run, folder_id, case_id, crm_explicito)
  -> list[str]`; `secuencia_v2(ident, case_dir, *, folder_id, team_id, crm, hasta=None,
  etapas=None) -> av1.ResultadoV1`.

**La propiedad que hay que conservar, dicha entera.** Hoy `--modo v1` exige `--crm skip`, y eso
garantiza que el modo secuenciado **no escribe en el CRM por accidente**. R1/H-01 midió que
nombrar las etapas no acredita nada: el default de `--crm` es `api`, así que omitir el flag
escribiría. La garantía nueva tiene que ser igual de fuerte: **en modo secuenciado, `--crm` es
obligatorio y explícito**, y `skip` deja las etapas escritoras en `saltada` con su `Pendiente`.

**Y la parada es INCLUSIVA:** `--hasta crm_alta` **ejecuta** `crm_alta` y para después. No se
cambia —`secuenciar` ya funciona así y V1 depende de ello— pero se documenta en la ayuda del flag,
porque quien quiera evitar el alta debe pedir `--hasta sala_maquina`.

- [ ] **Step 1: Escribir el test que falla**

```python
"""La autorizacion de escritura del modo secuenciado.

R1/H-01: nombrar las etapas no acredita autorizacion. El default de `--crm` es
`api`, asi que omitir el flag escribiria en el CRM sin que nadie lo pidiera.
"""

import core.apertura_v1 as av1
import scripts.abrir_caso as ac


class _Ident:
    case_id = "W-TEST1"


def test_omitir_crm_en_modo_secuenciado_es_ERROR():
    errores = ac._errores_de_modo(
        crm="api", crm_explicito=False, hasta=None, fuente="drive_ev",
        force=False, dry_run=False, folder_id="X", case_id=None)

    assert [e for e in errores if "--crm" in e], (
        "omitir el flag no puede valer como autorizacion de escritura")


def test_crm_skip_deja_las_escritoras_en_saltada(tmp_path):
    etapas = ac._etapas_v2(_Ident(), tmp_path, folder_id="X", team_id="1", crm="skip")
    por_nombre = {e.nombre: e for e in etapas}

    res = por_nombre["crm_alta"].correr()

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["crm_no_autorizado"]


def test_crm_api_explicito_autoriza():
    errores = ac._errores_de_modo(
        crm="api", crm_explicito=True, hasta=None, fuente="drive_ev",
        force=False, dry_run=False, folder_id="X", case_id=None)

    assert not [e for e in errores if "--crm" in e]


def test_las_etapas_de_v2_amplian_v1_por_la_derecha():
    assert ac.ETAPAS_V2[:3] == ac.ETAPAS_V1
    assert ac.ETAPAS_V2[3:] == ("crm_alta", "actuacion", "verificar")


def test_hasta_sigue_rechazando_lo_que_no_es_etapa():
    errores = ac._errores_de_modo(
        crm="skip", crm_explicito=True, hasta="inventada", fuente="drive_ev",
        force=False, dry_run=False, folder_id="X", case_id=None)

    assert [e for e in errores if "--hasta" in e]
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_autorizacion.py -q --tb=short
```

Esperado: FAIL — `has no attribute '_errores_de_modo'`.

- [ ] **Step 3: Implementación mínima**

```python
ETAPAS_V1 = ("drive", "crm", "sala_maquina")
#: V2 AMPLIA V1 por la derecha: las tres primeras conservan nombre y orden, asi que un
#: `--hasta sala_maquina` de antes sigue parando donde paraba. `crm_ficha` NO esta:
#: llevar el YAML al CRM ejecuta los efectos materiales de la §8.1, que el spec situa
#: despues de la sala de lectura y la viabilidad (R1/H-05).
ETAPAS_V2 = ETAPAS_V1 + ("crm_alta", "actuacion", "verificar")
```

En el comando, capturar si el flag vino puesto:

```python
crm_explicito = ctx.get_parameter_source("crm") is not ParameterSource.DEFAULT
```

Y en la validación, **sustituir** el bloque del `--crm skip`:

```python
    if not crm_explicito:
        errores.append(
            "--modo v1 exige declarar --crm api|skip. Omitirlo no autoriza a escribir: "
            "el default del CLI es `api` y alcanzaria un POST de alta."
        )
    elif crm not in ("api", "skip"):
        errores.append(f"--crm solo admite api|skip (recibido: {crm!r})")
```

`_etapas_v2` recibe `crm` y lo propaga a cada etapa escritora (Tasks 2 y 3 lo consumen).

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_autorizacion.py -q --tb=short
```

Esperado: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_v2_autorizacion.py
git commit -m "V2: la autorizacion de escritura se declara, no se hereda del default"
```

---

### Task 2: `_alta_crm` deja de devolver `None` para cinco cosas distintas

**Files:**
- Modify: `scripts/abrir_caso.py:1012-1142` (`_alta_crm`) y su llamador del modo libre
- Test: `tests/test_alta_crm_resultado.py` (crear)

**Interfaces:**
- Produces: `ResultadoAlta = namedtuple("ResultadoAlta", "estado exp_id detalle")` con
  `estado ∈ ("creado", "ya_vinculado", "declinado", "fallo_post", "fallo_registro")`;
  `_alta_crm(...) -> ResultadoAlta` (mismos parámetros que hoy).

**R1/H-02, literal:** «el helper devuelve `None` si el caso ya estaba vinculado, si se declina el
alta, si el POST lanza una excepción, si falla el registro local y también después de un alta
correcta». La rev. 1 traducía **los cinco** a `saltada` con el detalle «el caso ya tiene expediente
CRM vinculado» — es decir, **un timeout se describía como si la vinculación existiera**.

**El modo libre no cambia de comportamiento:** su llamador ignora el retorno hoy y lo seguirá
ignorando. Añadir un valor de retorno no rompe a nadie.

- [ ] **Step 1: Escribir el test que falla**

```python
"""`_alta_crm` distingue sus cinco desenlaces.

R1/H-02: devolvia `None` para los cinco, y el adaptador de la rev. 1 describia un
timeout como «el caso ya tiene expediente vinculado».
"""

import pytest

import scripts.abrir_caso as ac


def test_alta_correcta_devuelve_creado_con_id(monkeypatch, _ident, _crm_ok):
    res = ac._alta_crm(_ident, cuantia=None, crm_mode="api", yes=True)

    assert (res.estado, res.exp_id) == ("creado", "644")


def test_ya_vinculado_se_distingue_de_creado(monkeypatch, _ident, _crm_ya_vinculado):
    res = ac._alta_crm(_ident, cuantia=None, crm_mode="api", yes=True)

    assert res.estado == "ya_vinculado"


def test_un_timeout_NO_se_describe_como_ya_vinculado(monkeypatch, _ident, _crm_timeout):
    # El defecto exacto que midio R1/H-02.
    res = ac._alta_crm(_ident, cuantia=None, crm_mode="api", yes=True)

    assert res.estado == "fallo_post"
    assert "vinculado" not in res.detalle.lower()


def test_fallo_al_registrar_en_local_no_se_confunde_con_fallo_de_post(
        monkeypatch, _ident, _crm_post_ok_registro_falla):
    # El caso peor del §5.2: el POST hizo commit y el vinculo local no se escribio.
    res = ac._alta_crm(_ident, cuantia=None, crm_mode="api", yes=True)

    assert res.estado == "fallo_registro"
    assert res.exp_id, "el id del expediente creado NO se puede perder"
```

**Nota para quien implemente:** las cuatro fixtures (`_ident`, `_crm_ok`, `_crm_ya_vinculado`,
`_crm_timeout`, `_crm_post_ok_registro_falla`) se escriben en este mismo fichero, sustituyendo
`sudespacho_create.create_expediente` y el registro local con `monkeypatch`. Ninguna toca el CRM.

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_alta_crm_resultado.py -q --tb=short
```

Esperado: FAIL — `AttributeError: 'NoneType' object has no attribute 'estado'`.

- [ ] **Step 3: Implementar el resultado**

Añadir el `namedtuple` y sustituir **cada** `return` mudo de `_alta_crm` por su estado. No se
cambia ninguna decisión del helper: solo se deja de tirar la información de qué pasó.

- [ ] **Step 4: Correr para verificar que pasa, y que el modo libre no se movió**

```bash
python -m pytest tests/test_alta_crm_resultado.py tests/test_abrir_caso_modo_v1.py tests/test_abrir_caso_exit_bajo_mutex.py -q --tb=short
```

Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_alta_crm_resultado.py
git commit -m "V2: _alta_crm dice CUAL de sus cinco desenlaces ocurrio"
```

---

### Task 3: Etapa `crm_alta`

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_abrir_caso_v2_etapas.py` (crear)

**Interfaces:**
- Consumes: `_alta_crm(...) -> ResultadoAlta` (Task 2).
- Produces: `etapa_crm_alta(ident, case_dir, *, crm, alta=None) -> av1.EtapaResultado`.

- [ ] **Step 1: Escribir el test que falla**

```python
import core.apertura_v1 as av1
import scripts.abrir_caso as ac
from scripts.abrir_caso import ResultadoAlta


class _Ident:
    case_id = "W-TEST1"


def test_sin_autorizacion_no_llama_al_alta(tmp_path):
    llamadas = []
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="skip",
                           alta=lambda: llamadas.append(1))

    assert res.estado == "saltada"
    assert llamadas == [], "con --crm skip no se puede tocar el CRM"


def test_alta_creada_sale_hecha(tmp_path):
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                           alta=lambda: ResultadoAlta("creado", "644", ""))

    assert res.estado == "hecha"
    assert "644" in res.detalle


def test_ya_vinculado_sale_saltada(tmp_path):
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                           alta=lambda: ResultadoAlta("ya_vinculado", "640", ""))

    assert res.estado == "saltada"


def test_fallo_de_post_es_FALLO_y_no_dice_vinculado(tmp_path):
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                           alta=lambda: ResultadoAlta("fallo_post", None, "timeout"))

    assert res.estado == "fallo"
    assert "vinculado" not in res.detalle.lower()


def test_post_ok_sin_registro_local_es_FALLO_que_conserva_el_id(tmp_path):
    # El caso del §5.2: hay un expediente creado que nadie vinculo. Perder su id
    # obligaria a buscarlo a mano.
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                           alta=lambda: ResultadoAlta("fallo_registro", "645", "disco"))

    assert res.estado == "fallo"
    assert "645" in res.detalle
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short
```

Esperado: FAIL — `has no attribute 'etapa_crm_alta'`.

- [ ] **Step 3: Implementación mínima**

```python
_ALTA_A_ETAPA = {
    "creado": "hecha",
    "ya_vinculado": "saltada",
    "declinado": "saltada",
    "fallo_post": "fallo",
    "fallo_registro": "fallo",
}


def etapa_crm_alta(ident, case_dir: Path, *, crm: str, alta=None) -> av1.EtapaResultado:
    """Etapa 4 (V2): alta del expediente en el CRM, si se autorizo y no la hay ya.

    NO reimplementa el alta: invoca `_alta_crm`, que resuelve duplicados con
    `core.alta_crm_politica`, tags, telefono y evento. Lo que esta etapa aporta es
    traducir sus CINCO desenlaces al vocabulario de V1 sin colapsarlos — la rev. 1
    describia un timeout como «ya tiene expediente vinculado» (R1/H-02).
    """
    if crm != "api":
        return av1.EtapaResultado(
            nombre="crm_alta", estado="saltada",
            detalle="escritura al CRM no autorizada (--crm skip)",
            pendientes=(av1.Pendiente(
                codigo="crm_no_autorizado",
                detalle="El alta CRM no se intento: relanza con --crm api."),))
    try:
        r = (alta or (lambda: _alta_crm(ident, cuantia=None, crm_mode=crm, yes=True)))()
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="crm_alta", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    estado = _ALTA_A_ETAPA.get(r.estado, "fallo")
    detalle = {"creado": f"expediente CRM {r.exp_id}",
               "ya_vinculado": f"ya vinculado a {r.exp_id}; no se da de alta otro",
               "declinado": "alta declinada por politica de duplicados",
               "fallo_post": f"el alta no se pudo confirmar: {r.detalle}",
               "fallo_registro": (f"expediente {r.exp_id} CREADO en el CRM pero NO "
                                  f"vinculado en local: {r.detalle}")}[r.estado]
    return av1.EtapaResultado(nombre="crm_alta", estado=estado, detalle=detalle)
```

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short
```

Esperado: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_v2_etapas.py
git commit -m "V2: etapa crm_alta, que no colapsa cinco desenlaces en uno"
```

---

### Task 4: Etapa `actuacion` con recibo DURABLE

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_abrir_caso_v2_etapas.py` (añadir)

**Interfaces:**
- Consumes: `core.sudespacho_actuaciones.alta_actuacion(elemento, exp_id, referencia_esperada, *,
  asunto, firmante, desde=None, ...) -> Recibo`.
- Produces: `etapa_actuacion(ident, case_dir, *, crm, alta=None, firmante=None)
  -> av1.EtapaResultado`; `_recibo_path(case_dir) -> Path`.

**R1/H-03 es el hallazgo que más dinero cuesta si se ignora.** El revisor lo reprodujo: dos
corridas sin `desde` crean **dos actuaciones** (IDs 900 y 901); la tercera, con `desde`, reutiliza
la 901. Además la rev. 1 declaraba `hecha` los cuatro estados del recibo, incluida `incierta`.

**El recibo se persiste** en `<case_dir>/00_Input/_recibo_actuacion.json`. Sin persistencia no hay
reentrada: un `Recibo` en memoria muere con el proceso, que es justo el caso que el §5.2 describe.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_sin_firmante_declara_pendiente(tmp_path):
    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="")

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["actuacion_sin_firmante"]


def test_relanzar_NO_crea_una_segunda_actuacion(tmp_path):
    # R1/H-03, reproducido por el revisor: sin `desde`, dos corridas dan 900 y 901.
    creadas = []

    def _alta(**kw):
        if kw.get("desde") is None:
            creadas.append(len(creadas) + 900)
        return _ReciboFalso("verificada", act_id=creadas[-1])

    ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                       firmante="Nikolai_Tyukhay", alta=_alta)
    ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                       firmante="Nikolai_Tyukhay", alta=_alta)

    assert creadas == [900], "la segunda corrida creo otra actuacion"


def test_un_recibo_incierto_NO_es_hecha(tmp_path):
    # `incierta` significa que no se sabe si el efecto ocurrio. Declararlo `hecha`
    # es exactamente la mentira que el §5.2 existe para impedir.
    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay",
                             alta=lambda **kw: _ReciboFalso("incierta", act_id=None))

    assert res.estado == "fallo"
    assert [p.codigo for p in res.pendientes] == ["actuacion_incierta"]


def test_un_recibo_incompleto_se_reanuda_con_desde(tmp_path):
    vistos = []

    def _alta(**kw):
        vistos.append(kw.get("desde"))
        return _ReciboFalso("incompleta" if len(vistos) == 1 else "verificada", act_id=910)

    ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay", alta=_alta)
    ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay", alta=_alta)

    assert vistos[0] is None and vistos[1] is not None, "la reanudacion no paso `desde`"
```

**Nota:** `_ReciboFalso` es un `dataclass` de tres campos (`estado`, `act_id`, `exp_id`) que se
escribe en el propio fichero de test. **No se usa un `**kw` que trague cualquier cosa**: R1 señaló
que el doble de la rev. 1 ocultaba firma, username y recibo. Este doble **valida** que `firmante`
sea un username sin espacios y que `elemento`, `exp_id`, `referencia_esperada` y `asunto` vengan.

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short -k actuacion
```

Esperado: FAIL — `has no attribute 'etapa_actuacion'`.

- [ ] **Step 3: Implementación mínima**

Traducir los cuatro estados del recibo: `verificada` → `hecha`; `incompleta` → reanudar con
`desde` y, si sigue incompleta, `fallo` + `Pendiente`; `incierta` → `fallo` +
`Pendiente(codigo="actuacion_incierta")`; `no_intentada` → `fallo`. Persistir el recibo tras
**cada** intento, antes de devolver.

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short
```

Esperado: PASS, 9 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_v2_etapas.py
git commit -m "V2: la actuacion conserva su recibo, y relanzar no crea otra"
```

---

### Task 5: Etapa `verificar` — diagnóstico sin bloquear V2

**Files:**
- Modify: `scripts/abrir_caso.py`
- Test: `tests/test_abrir_caso_v2_etapas.py` (añadir)

**Interfaces:**
- Consumes: `core.verificar_apertura.verificar(case_dir, fuentes=None) -> Informe` — **existe ya**.
- Produces: `etapa_verificar(ident, case_dir, *, verificar=None) -> av1.EtapaResultado`;
  `COMPROBACIONES_DE_V2: frozenset[str]`.

**R1/H-07:** un `fallo` de cualquiera de las nueve dejaba V2 en `bloqueado`. Una sala de lectura a
medio montar —fase de **V3**— bloquearía el cierre del lazo del CRM aunque éste terminara bien.

**La regla:** solo las comprobaciones **de V2** deciden el estado de la etapa. Las demás viajan
como `Pendiente`, visibles y sin bloquear. Y los **cuatro** estados se traducen, incluido
`sin_implementar`, que la rev. 1 contaba como comprobación hecha.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_un_fallo_de_V3_no_bloquea_V2(tmp_path):
    # Sala de lectura a medio montar: es V3. Visible como pendiente, nunca como
    # fallo de V2 (R1/H-07).
    informe = _InformeFalso([("c4_artefactos_de_la_sala", "fallo", "faltan 4 de 4"),
                             ("c9_cuantia_crm", "ok", "")])

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=lambda cd: informe)

    assert res.estado == "hecha"
    assert "c4_artefactos_de_la_sala" in [p.codigo.split(":")[1] for p in res.pendientes]


def test_un_fallo_de_V2_si_bloquea(tmp_path):
    informe = _InformeFalso([("c9_cuantia_crm", "fallo", "la cuantia no cuadra")])

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=lambda cd: informe)

    assert res.estado == "fallo"


def test_sin_implementar_no_pasa_por_comprobacion_hecha(tmp_path):
    # Cuarto estado, que la rev. 1 ignoraba. Ruta real: falta `openpyxl`.
    informe = _InformeFalso([("c5_viabilidad_completa", "sin_implementar", "sin openpyxl")])

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=lambda cd: informe)

    assert [p.codigo for p in res.pendientes] == ["verificacion:c5_viabilidad_completa"]
```

- [ ] **Step 2: Correr para verificar que falla**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py -q --tb=short -k verificar
```

Esperado: FAIL — `has no attribute 'etapa_verificar'`.

- [ ] **Step 3: Implementación mínima**

```python
#: Las comprobaciones cuyo fallo SI es un fallo de V2. El resto diagnostica fases
#: ajenas (sala de lectura y viabilidad son V3) y viaja como pendiente: avanzar a
#: medias en una fase fuera de alcance no puede bloquear el cierre del lazo del CRM.
COMPROBACIONES_DE_V2 = frozenset({"c6_ficha_crm", "c7_actuacion", "c9_cuantia_crm"})
```

**Nota:** los nombres exactos salen de la Task 0. Si alguno no existe con ese nombre, **para y
dilo**: inventarlo dejaría el conjunto vacío y ningún fallo bloquearía nunca.

Y reconciliar con `_informar_v1_y_verificar`, que ya corre el diagnóstico **fuera del mutex** sin
cambiar el código de salida (R1/H-07): con esta etapa dentro de la secuencia habría **dos**
verificaciones con efectos distintos. Se conserva **una sola**: la de la etapa.

- [ ] **Step 4: Correr para verificar que pasa**

```bash
python -m pytest tests/test_abrir_caso_v2_etapas.py tests/test_abrir_caso_v2_autorizacion.py -q --tb=short
```

Esperado: PASS, 17 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/
git commit -m "V2: el diagnostico de V3 se ve, pero no bloquea V2"
```

---

### Task 6: La verja, y la corrida real

- [ ] **Step 1: Suite completa con las dos semillas**

```bash
python -m scripts.session_close
```

**Cuadrar el conteo al test.** Este plan añade **22** tests: 5 (Task 1) + 4 (Task 2) + 5 (Task 3) +
4 (Task 4) + 3 (Task 5) + 1 de reconciliación en Task 5. Partiendo de **5.713**, lo esperado es
**5.735**. *(La rev. 1 anunciaba 13 y eran 15; el revisor lo corrigió. Esta cuenta está sumada
tarea a tarea.)*

- [ ] **Step 2: CORRERLA contra el expediente de prueba 636**

Los dobles acreditan qué decide el código ante una respuesta; **nunca** que el payload sea
aceptable. Medido el 2026-09-14: 5.612 tests verdes y 39 mutantes muertos no vieron tres defectos
que una ejecución real encontró.

Tres corridas, no una:

1. `--crm skip` → las tres etapas nuevas salen `saltada`, **cero escrituras** (verificar releyendo).
2. `--crm api` → alta + actuación; **releer el expediente 636** y comprobar por resultado.
3. **`--crm api` otra vez** → `crm_alta` sale `ya_vinculado` y `actuacion` **no crea una segunda**.
   Ésta es la corrida que prueba H-03, y es la que ningún doble acredita.

**Borrar después lo creado.**

- [ ] **Step 3: Declarar lo que la corrida enseñe**

## 7. Deuda declarada, no fingida (R1/H-08)

El §5.2 exige una **intención durable antes del POST** y conciliación antes de repetir. **Esta
entrega no la construye**, y decirlo es parte del trabajo:

- **El alta hereda la deuda que ya existe hoy en producción.** `create_expediente` captura
  cualquier excepción del alta REST y reintenta por el frontal legacy **sin volver a consultar
  duplicados**; si REST hizo commit y se perdió la respuesta, hay dos creaciones. V2 **no empeora**
  esto: lo hace alcanzable desde la secuencia. Lo que sí aporta es que el estado `fallo_registro`
  conserve el `exp_id`, para que un expediente creado y no vinculado se pueda encontrar.
- **La actuación queda cubierta SOLO a partir del recibo, y eso NO es «cubierta»** (R2/H-03,
  confirmado). El recibo se guarda **después** del efecto remoto: un corte entre el POST y
  el guardado deja la actuación creada sin recibo, y la corrida siguiente crea otra. Lo que
  sí está cubierto es la reentrada **normal** —proceso vivo, recibo escrito— y el corte
  posterior al guardado. La ventana entre el efecto y su recibo **sigue abierta**, y decir
  lo contrario era la clase de afirmación de cobertura que esta casa persigue.
- **Lo que queda abierto:** un corte entre el commit remoto del alta y la escritura del vínculo
  local. Se detecta —`fallo_registro` con su `exp_id`— pero se concilia **a mano**.

Construir la intención durable del §5.2 es una pieza propia, y es la que debería ir antes de V3.

## Self-review del plan (hecho)

**Cobertura de los 8 hallazgos de R1:** H-01 → Task 1. H-02 → Task 2. H-03 → Task 4. H-04 →
**desaparece**: `crm_ficha` sale del alcance. H-05 → **desaparece** por lo mismo. H-06 → Task 5
(se reutiliza `verificar`, no se crea agregador) y Task 0 (los cuatro estados). H-07 → Task 5
(`COMPROBACIONES_DE_V2` + una sola verificación). H-08 → §7, declarado y parcialmente cubierto.

**Placeholders:** ninguno. Las tres «Notas» (fixtures de Task 2, `_ReciboFalso` de Task 4, nombres
de comprobación de Task 5) dicen qué hacer, y dos de ellas mandan **parar** si la realidad difiere.

**Consistencia de tipos:** `ResultadoAlta(estado, exp_id, detalle)` se define en Task 2 y lo
consumen Task 3 y sus tests. `etapa_*` devuelven `av1.EtapaResultado`. `_etapas_v2` recibe `crm` en
Task 1 y lo propagan Tasks 3 y 4.

**Lo que este plan NO hace, y es deliberado:** no toca `secuenciar`, no cambia el default del modo
libre, no construye la intención durable del §5.2, y no ejecuta la §8.1.

## 8. Adjudicación de la revisión adversarial (Codex, 2026-09-14) — NO-SHIP, remediado

- **Objeto revisado:** el PLAN rev. 1 (`3d72cd8`), antes de la primera línea de código, con el árbol disponible para verificar contra la fuente.
- **Ronda:** 1 de 2 — la segunda irá sobre el diff, por radio de daño (escribe en el CRM).
- **Revisor:** Codex CLI `0.153.4`, modelo `gpt-6-astra`, `model_reasoning_effort=high`.
- **Informe recibido:** [`…-r1-adversarial-review.md`](2026-09-14-apertura-v2-lazo-crm-r1-adversarial-review.md), `sha256` `2cc864cd29c1fa265e97994010b61c69895eacf4c9a398f7636e238df3b131e9`, recomputado por mí y coincidente con el que devolvió el revisor.
- **Hallazgos:** 8 (6 `ALTO`, 2 `MEDIO`) — **8 confirmados, 0 refutados**.
- **Remediado en:** esta rev. 2 del plan; H-04 y H-05 desaparecen al salir `crm_ficha` del alcance.

**Verifiqué contra la fuente los cuatro decisivos**, no contra el informe: `_alta_crm(ident, *,
cuantia, crm_mode, yes, force=False)` frente a la llamada `(ident, case_dir)` del plan;
`verificar(case_dir, fuentes=None)` **ya existía** en `core/verificar_apertura.py:1134` cuando el
plan proponía crearlo; `Exit -> RuntimeError -> Exception`, luego `except Exception` **sí** captura
`typer.Exit` —mi nota afirmaba lo contrario—; y el fallback legacy de `create_expediente`.

**Las tres fronteras, y la más incómoda es la primera.** (A) Escribí el plan contra firmas que no
verifiqué una por una: **transcribí la firma correcta de `alta_actuacion` en el bloque «Interfaces»
y dos párrafos después escribí `case_id=`, que no existe**. Es el mismo patrón que la R1 de P8
—escribir la verdad en un sitio del documento y no aplicarla en otro del mismo documento—, dos
veces el mismo día. De ahí sale la **Task 0**: verificar firmas con `inspect.signature` antes de
escribir nada. (B) Confundí exclusión nominal con material: decir que la §8.1 no entra no impide
que el comando invocado cree contrarios. (C) Capturar una excepción no conserva autorización ni
implementa recuperación.

**Lo que el revisor no pudo refutar, y queda registrado:** `secuenciar` acepta las estructuras del
plan sin modificarse; el YAML ausente sí produce `saltada`+`Pendiente` sin preguntar; `_alta_crm`
sí protege la reentrada de un expediente ya vinculado, con cero POST medidos; y las comprobaciones
de sala y viabilidad son de lectura, no construyen esas fases.

**Y corrigió mi aritmética:** anuncié 13 tests y eran 15. La cuenta de la rev. 2 está sumada tarea
a tarea.

**Decisión de alcance de Nikolai (2026-09-14), tomada al ver estos hallazgos:** V2 se recorta a
`crm_alta` + `actuacion` + `verificar`. `crm_ficha` se difiere, que es lo que elimina H-05 de raíz.

## 9. Adjudicación de la revisión adversarial (Codex, 2026-09-14) — NO-SHIP, remediado

- **Objeto revisado:** el diff `c8c4c48..318a081` — 8 ficheros, la implementación completa de V2.
- **Ronda:** 2 de 2, por radio de daño. La R1 fue sobre el plan; ésta sobre el código.
- **Revisor:** Codex CLI `0.153.4`, modelo `gpt-6-astra`, `model_reasoning_effort=high`.
- **Informe recibido:** [`…-r2-adversarial-review.md`](2026-09-14-apertura-v2-lazo-crm-r2-adversarial-review.md), `sha256` `7c15f415909d53233f98be3da00e5df99a677bd2ab6a0a7d95053cc44d60718e`, recomputado por mí y coincidente con el que devolvió el revisor.
- **Hallazgos:** 7 (3 `ALTO`, 4 `MEDIO`) — **7 confirmados, 0 refutados**.
- **Remediado en:** este commit; H-03 y la política de copias de H-05 **se declaran como deuda** por decisión de Nikolai.

**Lo que la ronda NO encontró, y era el mayor riesgo de esta pieza.** Se le pidió expresamente que
atacara los **nueve tests reexpresados** buscando relajaciones, comparando aserto por aserto contra
la base. Concluye: *«No encuentro una relajación injustificada de los asertos antiguos bajo el
nuevo contrato autorizado»*. Esa validación vale porque venía de alguien sin nada invertido.

### Los tres ALTO, y por qué ninguno lo veía la suite verde

| | Qué pasaba | Remedio |
|---|---|---|
| **H-01** | `etapa_verificar` llamaba `va.verificar(cd)` **sin fuentes** → `SinRed`, y entonces «las cinco comprobaciones de red salen en `fallo`». Como dos de las tres decisorias son de red, **con `--crm api` la etapa habría dado `fallo` siempre** y la secuencia habría acabado `bloqueado` en toda corrida real | se cablea `DeLaRed` cuando la corrida autorizó el CRM; con `skip` no se sale a la red, que no habría nada que consultar |
| **H-02** | `_leer_recibo` devolvía `None` tanto para «no hay» como para «no se pudo interpretar», y lo segundo **daba permiso para crear una segunda actuación** | `ReciboIlegible`: un recibo corrupto es `fallo` con su pendiente, no vía libre |
| **H-03** | el §7 declaraba cubierta la actuación, y **era falso** | se corrige el §7 y se declara la deuda (abajo) |

**H-02 es la tercera vez en el día que incumplo la misma frontera.** P8 la cerró por la mañana
—«no pude interpretarlo» no es «no hay nada»—, su R1 la encontró en tres vías, y aquí reaparece en
el recibo y otra vez en la ficha (**H-06**). No es descuido puntual: es que la frontera hay que
comprobarla **en cada lectura que se escribe**, no recordarla.

### Los cuatro MEDIO

- **H-04:** el atajo de `verificada` no miraba a qué expediente pertenecía el recibo. Ahora se
  comprueba **con el destino delante**, y un recibo de otro expediente es anomalía declarada.
- **H-06:** ficha presente e ilegible se presentaba como ausente. Misma frontera que H-02.
- **H-07:** el guard usaba `<=`, así que el conjunto decisorio podía quedarse con una de tres y
  seguir verde. Ahora exige igualdad.
- **H-05:** el recibo no estaba declarado como protocolo y la sala de máquina lo habría
  inventariado **como un documento del expediente del cliente**. Se añade a `intake_control.RAIZ`.

### Y una crítica que se acepta entera

El test `test_verificar_por_el_camino_REAL_llama_al_verificador`, escrito precisamente para cerrar
el patrón del *doble que tapa*, **seguía tapando**: probaba que se llama e impedía ver que se
llamaba sin fuentes — que es H-01. Ahora comprueba también las fuentes.

**Tres tests propios se retiraron por afirmar la propiedad equivocada**, con su nota en el
fichero: los de recibo corrupto y YAML ilegible daban por buena justamente la confusión que la
ronda señaló. No es debilitar para poner verde: es que lo que afirmaban era incorrecto, lo dijo un
revisor independiente y se comprobó contra la fuente.

### Deuda declarada, por decisión de Nikolai (2026-09-14)

1. **La ventana entre el efecto remoto y su recibo sigue abierta** (H-03). Cerrarla exige la
   intención durable del §5.2, que este plan declara fuera de alcance desde la rev. 2. Lo que
   cambia es que **ya no se dice que está cubierta**.
2. **La vida del recibo entre copias no está definida** (H-05). Excluirlo del inventario es
   acotado y se hizo; **no** se copia a ciegas la exclusión de merge de `_apertura_v1.json`,
   porque el revisor advierte con razón que aquello es estado de la copia mientras que perder
   este recibo al cambiar de copia **puede recrear la actuación**. Hace falta una política
   explícita, con su registro y sus pruebas. Se ficha.

**No hay R3.** El presupuesto de dos rondas está agotado y el techo duro exige autorización
expresa para una tercera. **La remediación de esta R2 no ha pasado por ninguna ronda**, y eso se
dice aquí y en el PR en lugar de dejarlo implícito.
