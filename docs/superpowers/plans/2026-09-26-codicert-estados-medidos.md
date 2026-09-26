---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: F2 del envío certificado por Codicert — lo que cambia el barrido de los 117 envíos reales de madrid.bd: el 22 que cierra, el canal sin clasificar y el envío estancado
spec: docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md
---

# Envío certificado por Codicert — F2: los estados, medidos sobre todos los envíos

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que F2 diga **por qué** no cosecha un envío —y que lo diga bien— y que un 22 sin ningún aviso entregado **cierre**, conforme a lo medido en los 117 envíos de `madrid.bd` y a lo decidido por Nikolai el 2026-09-26.

**Architecture:** todo en las piezas que ya existen. `core/expedicion_certificada.py` gana una familia (`AVISO_FALLIDO`, el 22) con su regla de cierre, deja de cosechar lo que viene por un canal que no conoce, y cada envío no cosechable sabe **su motivo** (`EnvioObservado.pendiente_por`), medido contra la hora de la lectura, que `Expedicion` pasa a llevar como campo obligatorio (`leida_en`). Los tres sitios que se lo explican al abogado —los informes `estado` y `cosechar` de `scripts/codicert.py` y el motivo del aportable de F3— leen ese motivo y una sola redacción (`QUE_SIGNIFICA`), en vez de decir de todo «el hecho aún puede mejorar».

**Tech Stack:** Python 3.14, `pytest`, `pytest-xdist`, `pytest-randomly`. Sin dependencias nuevas.

## Global Constraints

- Ningún test escribe en el árbol de producción; `tmp_path` y dobles (`CLAUDE.md` §Tests).
- Nunca se borra ni se debilita un test para poner verde. Los siete sitios que construyen `Expedicion` en los tests **ganan** el argumento `leida_en`; ninguna aserción se toca.
- Un negativo contra un literal se vacía: los «no contiene» se escriben contra las constantes del módulo (`exp.QUE_SIGNIFICA[...]`), nunca contra una frase copiada.
- Aceptar el cambio son **dos semillas** (777 y 31337), con la suite entera en paralelo.
- La fecha se toma del sistema. Terminología: requerido; propietario/buscador.
- Nada de terceros en el repo: los envíos se citan por su código (`006…`), nunca por destinatario.

---

## Mediciones del 2026-09-26 que gobiernan este plan

Barrido **en solo lectura** (`GET /envios` y `GET /envios/{id}/estados`, sin coste) de **todos** los envíos de `madrid.bd` del 2026-06-03 al 2026-09-23 —117: 72 entregas electrónicas por correo, 20 por SMS, 24 burofax y 1 SMS Certificado— y de los 2 del sandbox. Autorizado por Nikolai en la sesión. Los scripts (`sondear_sms.py`, `barrido_estados.py`, `tiempos_estados.py`) quedan en el scratchpad de la sesión, fuera del repo: imprimen códigos, títulos y fechas, y nada de terceros.

**M-17. El SMS no tiene estados propios, y el 22 es un callejón.** Ninguno de los 22 SMS (20 de producción, el SMS Certificado y la prueba del sandbox del 17/09) pasa por 29, 30 ni 39: recorren los del correo. Por SMS: `17 → 20` (5), `17 → 14 → 21 → 40` (6), `42` en segundos (2), en curso (6) y **`3 → 14 → 22` y ahí se queda** (`006bij47xan`: 83 días sin el 40 que cierra a todos los demás). La DPC v2.5 §4.5.10 mapea el 22 a ETSI **D.4 ConsignmentNotificationFailure**. F2 lo tenía sin clasificar, así que ese envío no se cosecharía nunca. En el sandbox, además, el 20 llegó **antes** que el 17: el acuse del operador puede llegar tarde.

**M-18. El SMS Certificado existe en producción y F2 no conoce su canal.** `006bkxe0q63`, tipo `s`: `17 → 20 «Documentación accedida»`. `CANAL_DE_TIPO` solo tiene `b` y `c`, así que el canal es `desconocido:s`, **no se cosecha nunca y no lleva aviso**: sale como pendiente que «aún puede mejorar». Y con un 42 **sí** se cosecharía, porque `cosechable` aceptaba cualquier cierre sin mirar el canal. De paso contradice al spec §1.1, que da por supuesto que este canal acredita solo la entrega (29/30).

**M-19. Un burofax entregado se quedó sin su 19.** `006bgjupt2a`: `3 → 8 → 11 → 12 → 17`, **88 días** sin el 19 que F2 espera. En los otros siete con 17, el 19 llegó a los 1,3 · 1,9 · 3,1 · 3,9 · 4,2 · 20,1 y 29,1 días.

**M-20. Cuánto dura un silencio.** El más largo seguido de un cambio: **29,1 días** (burofax, del 17 al 19); 28,7 en el correo (una relectura, 20 → 20); 29,0 en el SMS (del 21 al 40). El 40 llega **a los 30 días exactos del envío, al segundo**: 24 de 24 en el correo y 6 de 6 en el SMS. Y la `fecha_expiracion` del listado es **el envío más 5 años** en los 119 envíos, de los tres tipos: la custodia, no los 30 días.

**M-21. La frontera: tres sitios dicen lo mismo de todo lo no cosechable.** `render_estado` («PENDIENTES (el hecho aún puede mejorar…)»), `render_cosecha` («NO COSECHADOS (el hecho aún puede mejorar)») y el aportable de F3 («el hecho aún puede mejorar: se prepara cuando culmine»). De los 117, tres se pararon sin que F2 los cierre —M-17, M-18 y M-19—, y de los tres esa frase es falsa. No son tres casos: es una propiedad, **«no cosechable» tiene cuatro motivos y el frontal conocía uno**.

**Lo que el barrido NO encontró, dicho también:** en el correo (72) no hay códigos sin clasificar ni envíos parados; todo termina en 20, 40 o 42, o sigue dentro de sus 30 días. 45 de esos 72 pasan por el 27 (servidor) y no por el 17. En el burofax, 7 culminan en 19, 12 cierran en 42 tras varias incidencias (31) y 4 siguen en curso.

## Decisiones

- **D-1 (Nikolai, 2026-09-26).** El 22 cierra sin entrega **solo si ningún aviso llegó**: si el primero llegó, el requerido aún puede leer y hay que esperar al 40. Lo que aprobó —mi recomendación— nombraba el 17, el 20 y el 21; **la concreción que sigue es mía**, en la dirección segura (más indicios = menos cierres), y se le dice: los indicios de que un aviso llegó son **17, 19, 20, 21 y 27**. El 27 (entregado en el servidor) entra por la misma razón que el 17: el aviso está donde el requerido puede verlo. Y cuentan **en cualquier punto del histórico**, no solo antes del 22, porque el acuse puede llegar tarde (M-17, sandbox).
- **Riesgo aceptado con D-1, declarado:** si un 22 cierra, el certificado se cosecha como definitivo; si después llegara un indicio, la cosecha siguiente lo saltaría (`ya_estaba`) y el hecho posterior no entraría solo en el expediente. Medido: 83 días sin cambios tras el 22.
- **D-2.** Un canal sin clasificar **no se cosecha nunca**, ni con su culminación ni con un cierre, y se declara con ⚠️ como un código sin clasificar.
- **D-2 bis (encontrado al ejecutar, no estaba en el plan).** Tampoco **pone fechas al requerido**: `Requerido.recibido_en` y `accedido_en` ignoran sus envíos. Salió al pintar un informe con los tres recorridos reales: la línea «accedido … (art. 10.2)» del requerido la ponía el SMS Certificado, cuyo adjunto no tiene por qué ser el requerimiento. Contarla podía adelantar un plazo con un hecho que nadie ha clasificado; no contarla lo retrasa, que es el lado seguro. El envío sigue en la lista del requerido y el aviso de canales lo dice. Es la misma frontera de D-2 —un canal desconocido tratado como conocido—, remediada en su segundo sitio. Commit `c8ae1ad`.
- **D-3.** **Estancado** = no cosechable, con el canal y los códigos clasificados, y **más de 40 días** sin eventos (el silencio más largo medido es 29,1; M-20). **Es un aviso, no una clasificación**: no hace cosechable nada; deja de prometer que el hecho mejorará y señala la salida que ya existe, `cosechar --incluir-pendientes` (baja el certificado con su estado en el nombre, sin ocupar el sitio del definitivo).
- **D-4.** `Expedicion.leida_en` es **obligatorio** y con zona horaria. Un valor por defecto `None` callaría lo estancado por falta de hora, que es el silencio que M-21 corrige.
- **Límite declarado:** F3 prepara el aportable solo sobre el certificado **definitivo**. Un envío estancado puede bajarse como provisional, pero no tendrá aportable. Se ficha en `MEJORAS_FUTURAS.md` con su disparador (el primer estancado que haya que aportar) y no se construye aquí.

## Lo que NO cambia

`pendientes` sigue siendo **todo** lo no cosechable (un estancado no culminó, y `completa` tiene que seguir diciéndolo); `cosechar` sigue decidiendo solo por `cosechable`; `_CULMINACION`, `CANAL_DE_TIPO` y los `recibido_en`/`accedido_en` de **cada envío** no se tocan (los del **requerido** sí, por D-2 bis); la regla del 17/21 (rev. 16) tampoco. F1 no se toca.

## Archivos

- Modificar: `core/expedicion_certificada.py` — familias y `_FAMILIA_DE` (~l. 968-1000), `EnvioObservado` (~l. 1075-1148), `Expedicion` (~l. 1150-1182), `refrescar` (~l. 1346), el motivo del aportable en `_preparar_bajo_candado` (~l. 2877).
- Modificar: `scripts/codicert.py` — `render_estado` (~l. 131-191), `render_cosecha` (~l. 194-212), la ayuda de `--incluir-pendientes` (~l. 268-272) y la llamada a `render_cosecha` (~l. 310).
- Crear: `tests/test_expedicion_pendientes.py`.
- Modificar (añadir casos): `tests/test_expedicion_estados.py`, `tests/test_expedicion_observada.py`, `tests/test_expedicion_refrescar.py`, `tests/test_codicert_cli_f2.py`, `tests/test_expedicion_aportable.py`.
- Documentación: el spec (rev. 17), `docs/MEJORAS_FUTURAS.md`, `PLAN.md`.

---

### Task 1: el 22 — familia propia y su regla de cierre

**Files:**
- Modify: `core/expedicion_certificada.py` (familias ~l. 968; `_FAMILIA_DE` ~l. 979-1000; tras `_CULMINACION` ~l. 1071; `cerrado_en` y `cosechable` ~l. 1118-1148)
- Test: `tests/test_expedicion_estados.py`, `tests/test_expedicion_observada.py`

**Interfaces:**
- Produces: `exp.AVISO_FALLIDO == "aviso_fallido"`; `exp.clasificar(22) == exp.AVISO_FALLIDO`; `EnvioObservado.cerrado_en` incluye el 22 cuando no hay indicio de entrega; `EnvioObservado.cosechable` es `True` cuando `cerrado_en` no es `None`.

- [x] **Step 1: Write the failing tests**

En `tests/test_expedicion_estados.py`, al final:

```python
def test_el_22_es_un_aviso_fallido_no_un_desconocido():
    """M-17: medido en producción, y la DPC v2.5 §4.5.10 lo mapea a ETSI D.4."""
    assert exp.clasificar(22) == exp.AVISO_FALLIDO
    assert exp.AVISO_FALLIDO not in (exp.EN_CURSO, exp.RECEPCION, exp.ACCESO,
                                     exp.SIN_ENTREGA, exp.DESCONOCIDO)
```

En `tests/test_expedicion_observada.py`, añadir `import pytest` debajo de `from datetime import datetime` y, al final:

```python
def test_el_22_sin_ningun_aviso_entregado_cierra_sin_entrega():
    """M-17, `006bij47xan`: el SMS no llegó nunca y el recordatorio falló.

    Decisión de Nikolai (2026-09-26): se cierra sin entrega y se cosecha como prueba del
    intento. Sin la regla no se cosecharía nunca: la plataforma no caduca lo que no entregó.
    """
    e = _envio(historico=_historico((3, "2026-07-01T12:05:33+02:00"),
                                    (14, "2026-07-02T13:00:45+02:00"),
                                    (22, "2026-07-04T13:00:50+02:00")))
    assert e.cerrado_en == datetime.fromisoformat("2026-07-04T13:00:50+02:00")
    assert e.cosechable
    assert e.recibido_en is None and e.accedido_en is None
    assert e.desconocidos == ()


@pytest.mark.parametrize("indicio", [17, 19, 20, 21, 27])
def test_el_22_NO_cierra_si_algun_aviso_llego(indicio):
    """Si el primer aviso llegó —al buzón, al contenido o al servidor—, el requerido aún
    puede leer: el 22 del recordatorio no cierra nada y se espera al 40 (D-1)."""
    e = _envio(historico=_historico((5, "2026-09-01T10:00:00+02:00"),
                                    (indicio, "2026-09-01T10:00:05+02:00"),
                                    (14, "2026-09-02T11:00:00+02:00"),
                                    (22, "2026-09-02T11:00:05+02:00")))
    assert e.cerrado_en is None
    assert e.cosechable is (indicio == 20)   # el 20 culmina por sí mismo


def test_un_indicio_que_llega_DESPUES_del_22_tambien_lo_anula():
    """El acuse puede llegar tarde (M-17: en el sandbox el 17 llegó después del 20). La
    regla mira el histórico entero, no solo lo anterior al 22."""
    e = _envio(historico=_historico((3, "2026-07-01T12:05:33+02:00"),
                                    (14, "2026-07-02T13:00:45+02:00"),
                                    (22, "2026-07-04T13:00:50+02:00"),
                                    (17, "2026-07-05T09:00:00+02:00")))
    assert e.cerrado_en is None and not e.cosechable


def test_el_40_cierra_aunque_hubiera_un_22_antes():
    e = _envio(historico=_historico((17, "2026-06-17T16:30:04+02:00"),
                                    (14, "2026-06-18T17:00:33+02:00"),
                                    (22, "2026-06-18T17:00:43+02:00"),
                                    (40, "2026-07-17T16:29:58+02:00")))
    assert e.cerrado_en == datetime.fromisoformat("2026-07-17T16:29:58+02:00")
    assert e.cosechable
```

- [x] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q --tb=short tests/test_expedicion_estados.py tests/test_expedicion_observada.py`
Expected: FAIL — `AttributeError: module 'core.expedicion_certificada' has no attribute 'AVISO_FALLIDO'`; `test_el_22_sin_ningun_aviso_entregado_cierra_sin_entrega` con `cerrado_en is None`; y el paramétrico del **20** y el del **40**, porque hoy el 22 es desconocido y bloquea la cosecha de cualquier envío que lo lleve. Los paramétricos de 17/19/21/27 y el del indicio tardío pasan ya (nada cierra): no prueban nada hasta el Step 4, que es cuando el 22 empieza a poder cerrar.

- [x] **Step 3: Implement**

En `core/expedicion_certificada.py`, el comentario «Las cinco familias» pasa a «Las seis familias», y debajo de `DESCONOCIDO = …`:

```python
AVISO_FALLIDO = "aviso_fallido"  #: el aviso no llegó (22): cierra SOLO si ninguno llegó (M-17)
```

En `_FAMILIA_DE`, tras el bloque de cierres sin entrega:

```python
    # el aviso no llegó — familia propia porque NO siempre cierra (M-17, decisión de
    # Nikolai del 2026-09-26): `3 → 14 → 22` es un aviso que nunca llegó y ahí se queda;
    # `17 → 14 → 22` es un primer aviso entregado y un recordatorio fallido, que no
    # cierra nada. La regla vive en `EnvioObservado.cerrado_en`.
    22: AVISO_FALLIDO,  # Recordatorio lectura fallido — ETSI D.4 (DPC v2.5 §4.5.10)
```

Tras `_CULMINACION`:

```python
#: Los códigos que prueban que ALGÚN aviso llegó a alguna parte: al destinatario (17,
#: 19, 21), a su contenido (20) o a su servidor (27). Con uno de ellos en el histórico
#: —antes o después del 22: el acuse puede llegar tarde—, un 22 no cierra: el requerido
#: tiene el aviso y aún puede leer, y la plataforma cerrará sola con el 40 (M-20).
_INDICIOS_DE_ENTREGA = frozenset({17, 19, 20, 21, 27})
```

`cerrado_en` pasa a:

```python
    @property
    def cerrado_en(self) -> datetime | None:
        """Cierre sin entrega. El 28 es un hecho con valor afirmativo, no un error.

        El 22 cierra también, pero solo si ningún aviso llegó (M-17, D-1): medido, un SMS
        que no se entregó nunca hace `3 → 14 → 22` y ahí se queda —83 días sin el 40 que
        cierra a los demás—, porque la plataforma no caduca lo que no entregó. Con un
        indicio de entrega en cualquier punto del histórico, el 22 no cierra: lo hará el 40.
        """
        fechas = [self._primera(SIN_ENTREGA)]
        if not {e.codigo for e in self.historico} & _INDICIOS_DE_ENTREGA:
            fechas.append(self._primera(AVISO_FALLIDO))
        fechas = [f for f in fechas if f is not None]
        return min(fechas) if fechas else None
```

Y la última línea de `cosechable`, `return any(clasificar(c) == SIN_ENTREGA for c in codigos)`, pasa a:

```python
        return self.cerrado_en is not None
```

- [x] **Step 4: Run them to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_expedicion_estados.py tests/test_expedicion_observada.py`
Expected: PASS, todo.

- [x] **Step 5: Commit**

```bash
git add core/expedicion_certificada.py tests/test_expedicion_estados.py tests/test_expedicion_observada.py
git commit -m "F2: el 22 sin ningun aviso entregado cierra sin entrega (M-17, decision de Nikolai)"
```

### Task 2: un canal sin clasificar no se cosecha

**Files:**
- Modify: `core/expedicion_certificada.py` (`EnvioObservado`, ~l. 1094-1148)
- Test: `tests/test_expedicion_observada.py`

**Interfaces:**
- Produces: `EnvioObservado.canal_clasificado -> bool` (`self.tipo in CANAL_DE_TIPO`); `cosechable` es `False` si no lo está.

- [x] **Step 1: Write the failing test**

Al final de `tests/test_expedicion_observada.py`:

```python
def test_un_canal_sin_clasificar_no_se_cosecha_ni_con_su_culminacion():
    """M-18, `006bkxe0q63`: el SMS Certificado (tipo `s`) existe en producción e hizo
    17 → 20. F2 no sabe en qué culmina ese canal: ni su 20 ni su 42 lo hacen definitivo."""
    leido = _envio(tipo="s", historico=_historico((17, "2026-07-07T12:59:54+02:00"),
                                                   (20, "2026-07-07T12:59:56+02:00")))
    fallido = _envio(tipo="s", historico=_historico((42, "2026-07-07T13:00:00+02:00")))
    assert leido.canal == "desconocido:s" and not leido.canal_clasificado
    assert not leido.cosechable and not fallido.cosechable
    # el canal no borra lo que el histórico acredita
    assert leido.accedido_en == datetime.fromisoformat("2026-07-07T12:59:56+02:00")
```

- [x] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q --tb=short tests/test_expedicion_observada.py`
Expected: FAIL — `AttributeError: 'EnvioObservado' object has no attribute 'canal_clasificado'`.

- [x] **Step 3: Implement**

En `EnvioObservado`, tras `canal`:

```python
    @property
    def canal_clasificado(self) -> bool:
        """¿Sabemos en qué culmina el canal? M-18: el tipo `s` (SMS Certificado), no."""
        return self.tipo in CANAL_DE_TIPO
```

En `cosechable`, al docstring se añade el párrafo:

```
        Un canal sin clasificar tampoco (M-18, D-2): sin saber en qué culmina, ni su 20 ni
        su 42 dicen que el certificado sea el definitivo.
```

y la primera comprobación del cuerpo pasa a ser:

```python
        if not self.canal_clasificado or self.desconocidos:
            return False
```

(en lugar de `if self.desconocidos: return False`).

- [x] **Step 4: Run it to verify it passes**

Run: `python -m pytest -q --tb=short tests/test_expedicion_observada.py tests/test_expedicion_estados.py`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add core/expedicion_certificada.py tests/test_expedicion_observada.py
git commit -m "F2: un canal sin clasificar no se cosecha, ni con su culminacion (M-18)"
```

### Task 3: por qué no se cosecha — `pendiente_por`, `leida_en` y `pendientes_por`

**Files:**
- Modify: `core/expedicion_certificada.py` (constantes nuevas tras `_INDICIOS_DE_ENTREGA`; métodos de `EnvioObservado`; `Expedicion`; `refrescar` ~l. 1346)
- Create: `tests/test_expedicion_pendientes.py`
- Modify (añadir el argumento `leida_en`, sin tocar aserciones): `tests/test_expedicion_observada.py` (2 construcciones), `tests/test_codicert_cli_f2.py` (5 construcciones)
- Test: `tests/test_expedicion_refrescar.py`

**Interfaces:**
- Consumes: `EnvioObservado.cosechable`, `canal_clasificado`, `desconocidos` (Tasks 1-2).
- Produces:
  - constantes `exp.CANAL_SIN_CLASIFICAR`, `exp.CODIGO_SIN_CLASIFICAR`, `exp.ESTANCADO`, `exp.PUEDE_MEJORAR`; `exp.MOTIVOS_PENDIENTE` (tupla en ese orden); `exp.DIAS_ESTANCADO = 40`; `exp.ETIQUETA` y `exp.QUE_SIGNIFICA`, los dos `dict[str, str]` por motivo.
  - `EnvioObservado.ultimo_evento() -> datetime`; `EnvioObservado.dias_quieto(ahora: datetime) -> int`; `EnvioObservado.pendiente_por(ahora: datetime) -> str | None`.
  - `Expedicion.leida_en: datetime` (obligatorio, solo por nombre, con zona); `Expedicion.pendientes_por() -> dict[str, tuple[EnvioObservado, ...]]`.

- [x] **Step 1: Write the failing tests**

`tests/test_expedicion_pendientes.py`:

```python
"""Por qué un envío no se cosecha: cuatro motivos y no uno (M-21)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core import expedicion_certificada as exp

#: La hora del barrido real del 2026-09-26.
LEIDA = datetime(2026, 9, 26, 6, 26, 56, tzinfo=timezone.utc)


def _envio(id_envio="006x", tipo="c", *pares):
    historico = tuple(exp.estado_de({"codigo": c, "titulo": "", "fecha": f, "detalle": None})
                      for c, f in pares)
    return exp.EnvioObservado(
        id_envio=id_envio, tipo=tipo, asunto="W-04AKM2 - OVC", destinatario="x@y.es",
        id_personalizado="W-04AKM2 - OVC",
        fecha_envio=datetime.fromisoformat("2026-06-01T10:00:00+02:00"),
        historico=historico)


def _hace(dias, segundos=0):
    return (LEIDA - timedelta(days=dias, seconds=segundos)).isoformat()


def test_lo_cosechable_no_tiene_motivo():
    assert _envio("006a", "c", (20, _hace(3))).pendiente_por(LEIDA) is None


def test_en_curso_y_reciente_puede_mejorar():
    e = _envio("006a", "c", (17, _hace(12)), (14, _hace(11)), (21, _hace(11)))
    assert e.pendiente_por(LEIDA) == exp.PUEDE_MEJORAR


def test_el_burofax_que_se_quedo_en_17_esta_estancado():
    """M-19, `006bgjupt2a`: entregado (17) y 88 días sin el 19. En los otros siete el 19
    llegó entre 1,3 y 29,1 días después."""
    e = _envio("006bgjupt2a", "b", (3, _hace(91)), (8, _hace(91)), (11, _hace(90)),
               (12, _hace(89)), (17, _hace(88)))
    assert e.pendiente_por(LEIDA) == exp.ESTANCADO
    assert e.dias_quieto(LEIDA) == 88


def test_la_frontera_de_los_40_dias():
    """Exactamente 40 días quieto todavía puede mejorar; un segundo más, no (D-3)."""
    justo = _envio("006a", "b", (17, _hace(40)))
    pasado = _envio("006b", "b", (17, _hace(40, segundos=1)))
    assert justo.pendiente_por(LEIDA) == exp.PUEDE_MEJORAR
    assert pasado.pendiente_por(LEIDA) == exp.ESTANCADO


def test_sin_historico_lo_quieto_se_cuenta_desde_el_envio():
    e = _envio("006a", "c")
    assert e.ultimo_evento() == e.fecha_envio
    assert e.pendiente_por(LEIDA) == exp.ESTANCADO


def test_lo_quieto_se_cuenta_desde_el_ULTIMO_evento_no_desde_el_primero():
    e = _envio("006a", "b", (3, _hace(80)), (31, _hace(60)), (12, _hace(10)))
    assert e.dias_quieto(LEIDA) == 10
    assert e.pendiente_por(LEIDA) == exp.PUEDE_MEJORAR


def test_el_codigo_sin_clasificar_se_dice_antes_que_lo_quieto():
    """Un 999 de hace cien días no es «estancado»: es algo que nadie ha clasificado, y eso
    se arregla en el código, no esperando."""
    e = _envio("006a", "c", (999, _hace(100)))
    assert e.pendiente_por(LEIDA) == exp.CODIGO_SIN_CLASIFICAR


def test_el_canal_sin_clasificar_se_dice_primero():
    """M-18, `006bkxe0q63`: 17 → 20 hace 80 días, en un canal que F2 no conoce."""
    e = _envio("006bkxe0q63", "s", (17, _hace(80)), (20, _hace(80)))
    assert e.pendiente_por(LEIDA) == exp.CANAL_SIN_CLASIFICAR


def test_pendientes_por_agrupa_en_el_orden_de_lo_que_hay_que_hacer():
    envios = (
        _envio("006m", "c", (17, _hace(5))),                    # puede mejorar
        _envio("006e", "b", (17, _hace(88))),                   # estancado
        _envio("006k", "c", (20, _hace(2))),                    # cosechable: fuera
        _envio("006d", "c", (999, _hace(1))),                   # código sin clasificar
        _envio("006s", "s", (17, _hace(80)), (20, _hace(80))),  # canal sin clasificar
    )
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=envios, leida_en=LEIDA)
    grupos = e.pendientes_por()
    assert list(grupos) == list(exp.MOTIVOS_PENDIENTE)
    assert {m: [x.id_envio for x in v] for m, v in grupos.items()} == {
        exp.CANAL_SIN_CLASIFICAR: ["006s"], exp.CODIGO_SIN_CLASIFICAR: ["006d"],
        exp.ESTANCADO: ["006e"], exp.PUEDE_MEJORAR: ["006m"]}
    # un estancado NO culminó: la expedición no está completa
    assert e.completa is False and len(e.pendientes) == 4


def test_pendientes_por_solo_trae_los_motivos_que_tienen_envios():
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(_envio("006m", "c", (17, _hace(5))),), leida_en=LEIDA)
    assert list(e.pendientes_por()) == [exp.PUEDE_MEJORAR]


def test_la_expedicion_exige_saber_cuando_se_leyo():
    """D-4: sin la hora de la lectura no se sabe qué está quieto; no hay valor por defecto."""
    with pytest.raises(TypeError):
        exp.Expedicion(id_personalizado="W-1 - OVC", entorno="produccion")
    with pytest.raises(exp.ExpedicionError, match="zona"):
        exp.Expedicion(id_personalizado="W-1 - OVC", entorno="produccion",
                       leida_en=datetime(2026, 9, 26))


def test_cada_motivo_tiene_su_nombre_y_su_explicacion():
    assert set(exp.QUE_SIGNIFICA) == set(exp.ETIQUETA) == set(exp.MOTIVOS_PENDIENTE)
    assert len(exp.MOTIVOS_PENDIENTE) == len(set(exp.MOTIVOS_PENDIENTE)) == 4
```

En `tests/test_expedicion_refrescar.py`, al final:

```python
def test_la_expedicion_anota_cuando_se_leyo(tmp_path):
    """La hora de la lectura sale del reloj del ENTORNO, no del sistema: es lo que hace
    reproducible saber qué está estancado (D-4)."""
    t = FakeTransporte([_ev("006a", "c", "x@y.es")],
                       {"006a": _h((21, "2026-09-11T19:00:23+02:00"))})
    e = exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t))
    assert e.leida_en == datetime(2026, 9, 21, tzinfo=timezone.utc)
```

- [x] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q --tb=short tests/test_expedicion_pendientes.py tests/test_expedicion_refrescar.py`
Expected: FAIL — `AttributeError` por `PUEDE_MEJORAR`, `pendiente_por`, y `TypeError: Expedicion.__init__() got an unexpected keyword argument 'leida_en'`.

- [x] **Step 3: Implement**

Tras `_INDICIOS_DE_ENTREGA`:

```python
#: Por qué un envío no es cosechable. Cuatro motivos y no uno (M-21): los tres sitios que
#: se lo explican al abogado decían de todos lo mismo —«el hecho aún puede mejorar»—, y
#: medido sobre 117 envíos reales, de tres no es verdad.
CANAL_SIN_CLASIFICAR = "canal_sin_clasificar"    #: no se sabe en qué culmina su canal
CODIGO_SIN_CLASIFICAR = "codigo_sin_clasificar"  #: tiene un código que nadie ha medido
ESTANCADO = "estancado"                          #: en curso, quieto más de DIAS_ESTANCADO
PUEDE_MEJORAR = "puede_mejorar"                  #: en curso: le falta su culminación

#: El orden en que se enseñan, que es el de lo que hay que hacer: lo que nadie clasificó
#: se arregla en el código; lo estancado lo decide el abogado; lo que puede mejorar
#: solo pide esperar.
MOTIVOS_PENDIENTE = (CANAL_SIN_CLASIFICAR, CODIGO_SIN_CLASIFICAR, ESTANCADO, PUEDE_MEJORAR)

#: Días sin eventos a partir de los cuales un envío en curso se da por estancado (M-20,
#: D-3): el silencio más largo medido antes de un cambio es de 29,1 días —un burofax del
#: 17 al 19— y la entrega electrónica caduca a los 30 exactos (30 de 30). **Es un aviso,
#: no una clasificación**: no hace cosechable nada; solo deja de prometer que mejorará.
DIAS_ESTANCADO = 40

#: Cómo se llama cada motivo y qué significa, en una línea. Lo leen los dos informes de
#: `scripts/codicert.py` y el aportable de F3: una sola redacción para los tres, que es
#: justo lo que faltaba (M-21).
ETIQUETA: dict[str, str] = {
    CANAL_SIN_CLASIFICAR: "CANAL SIN CLASIFICAR",
    CODIGO_SIN_CLASIFICAR: "CÓDIGO SIN CLASIFICAR",
    ESTANCADO: "ESTANCADO",
    PUEDE_MEJORAR: "EN CURSO",
}
QUE_SIGNIFICA: dict[str, str] = {
    CANAL_SIN_CLASIFICAR: "su canal no está clasificado; no se sabe en qué culmina",
    CODIGO_SIN_CLASIFICAR: "tiene un código de estado sin clasificar; no se sabe si culmina",
    ESTANCADO: f"lleva más de {DIAS_ESTANCADO} días sin moverse y no se cerrará solo",
    PUEDE_MEJORAR: "el hecho aún puede mejorar; se cosecha cuando culmine",
}
```

En `EnvioObservado`, tras `cosechable`:

```python
    def ultimo_evento(self) -> datetime:
        """La fecha del último evento del histórico; sin histórico, la del envío."""
        return max((e.fecha for e in self.historico), default=self.fecha_envio)

    def dias_quieto(self, ahora: datetime) -> int:
        """Días enteros desde el último evento hasta `ahora`."""
        return (ahora - self.ultimo_evento()).days

    def pendiente_por(self, ahora: datetime) -> str | None:
        """Por qué no es cosechable —uno de `MOTIVOS_PENDIENTE`—, o `None` si lo es.

        Las preguntas van en el orden de `MOTIVOS_PENDIENTE`: con el canal o un código
        sin clasificar no se puede razonar nada más, y lo quieto se dice antes de
        prometer que mejorará.
        """
        if self.cosechable:
            return None
        if not self.canal_clasificado:
            return CANAL_SIN_CLASIFICAR
        if self.desconocidos:
            return CODIGO_SIN_CLASIFICAR
        if ahora - self.ultimo_evento() > timedelta(days=DIAS_ESTANCADO):
            return ESTANCADO
        return PUEDE_MEJORAR
```

`Expedicion`: al docstring se añade el párrafo

```
    `leida_en` es **cuándo se leyó** de la plataforma, y es obligatoria (D-4): sin ella no
    se sabe qué lleva semanas quieto, y un «estancado» que se callara por falta de hora
    sería el mismo silencio que M-21 corrige. La pone `refrescar` con el reloj del
    entorno, y exige zona horaria por lo mismo que `estado_de`.
```

y los campos y `__post_init__` pasan a:

```python
    id_personalizado: str
    entorno: str
    envios: tuple[EnvioObservado, ...] = ()
    leida_en: datetime = field(kw_only=True)

    def __post_init__(self) -> None:
        object.__setattr__(self, "envios", tuple(self.envios))
        if self.leida_en.tzinfo is None:
            raise ExpedicionError(
                f"{self.id_personalizado}: la hora de la lectura {self.leida_en!r} no trae "
                "zona horaria. No se asume UTC: con ella se mide qué está estancado.")
```

y, tras `completa`:

```python
    def pendientes_por(self) -> dict[str, tuple[EnvioObservado, ...]]:
        """Lo no cosechable, agrupado por su motivo en el orden de `MOTIVOS_PENDIENTE`.

        Solo salen los motivos con algún envío. `pendientes` sigue siendo la lista entera:
        un estancado NO culminó, y `completa` tiene que seguir diciéndolo.
        """
        grupos: dict[str, list[EnvioObservado]] = {m: [] for m in MOTIVOS_PENDIENTE}
        for envio in self.pendientes:
            grupos[envio.pendiente_por(self.leida_en)].append(envio)
        return {m: tuple(v) for m, v in grupos.items() if v}
```

`refrescar`, el `return` pasa a:

```python
    return Expedicion(id_personalizado=id_personalizado, entorno=entorno_exp.entorno,
                      envios=tuple(envios), leida_en=ahora)
```

Los siete `exp.Expedicion(...)` de los tests ganan `leida_en=LEIDA`, con una constante al principio de cada fichero:

- `tests/test_expedicion_observada.py`: `LEIDA = datetime.fromisoformat("2026-09-13T10:00:00+02:00")`, en las líneas ~91 y ~100.
- `tests/test_codicert_cli_f2.py`: la misma constante, en las líneas ~24, ~37, ~46, ~54 y ~114.

- [x] **Step 4: Run them to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_expedicion_pendientes.py tests/test_expedicion_refrescar.py tests/test_expedicion_observada.py tests/test_codicert_cli_f2.py`
Expected: PASS, todo.

- [x] **Step 5: Commit**

```bash
git add core/expedicion_certificada.py tests/test_expedicion_pendientes.py tests/test_expedicion_refrescar.py tests/test_expedicion_observada.py tests/test_codicert_cli_f2.py
git commit -m "F2: cada envio no cosechable sabe su motivo, medido contra la hora de la lectura (M-21)"
```

### Task 4: los tres textos — `estado`, `cosechar` y el aportable

**Files:**
- Modify: `scripts/codicert.py` (`render_estado` ~l. 131-191, `render_cosecha` ~l. 194-212, ayuda de `--incluir-pendientes` ~l. 268-272, llamada ~l. 310)
- Modify: `core/expedicion_certificada.py` (`_preparar_bajo_candado`, ~l. 2877-2881)
- Test: `tests/test_codicert_cli_f2.py`, `tests/test_expedicion_aportable.py`

**Interfaces:**
- Consumes: `Expedicion.pendientes_por()`, `Expedicion.leida_en`, `EnvioObservado.dias_quieto`, `pendiente_por`, `canal_clasificado`, `exp.QUE_SIGNIFICA`, `exp.MOTIVOS_PENDIENTE` (Task 3).
- Produces: `render_cosecha(cosechados, expedicion: exp.Expedicion) -> str` (antes recibía `pendientes`); helper privado `_no_cosechables(expedicion, titulo) -> list[str]`.

- [x] **Step 1: Write the failing tests**

En `tests/test_codicert_cli_f2.py`, al final:

```python
def test_render_estado_separa_lo_estancado_de_lo_que_puede_mejorar():
    """M-19/M-21: un burofax 88 días en 17 no «puede mejorar»; se dice, con la salida."""
    estancado = _envio("006e", tipo="b", historico=(exp.EstadoCertificado(
        codigo=17, titulo="Entregado",
        fecha=datetime.fromisoformat("2026-06-17T10:00:00+02:00")),))
    reciente = _envio("006m", historico=(exp.EstadoCertificado(
        codigo=21, titulo="Recordatorio lectura entregado",
        fecha=datetime.fromisoformat("2026-09-11T19:00:23+02:00")),))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(estancado, reciente), leida_en=LEIDA)
    texto = cli.render_estado(e, [])
    bloque_estancado = texto.index(exp.QUE_SIGNIFICA[exp.ESTANCADO])
    bloque_mejora = texto.index(exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR])
    assert bloque_estancado < texto.index("· 006e") < bloque_mejora < texto.index("· 006m")
    assert "88 días sin moverse" in texto and "--incluir-pendientes" in texto


def test_render_estado_declara_los_canales_sin_clasificar():
    """M-18: el tipo `s` sale con su aviso, como un código sin clasificar."""
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(_envio("006s", tipo="s"),), leida_en=LEIDA)
    texto = cli.render_estado(e, [])
    assert "CANALES SIN CLASIFICAR: tipo s" in texto
    assert exp.QUE_SIGNIFICA[exp.CANAL_SIN_CLASIFICAR] in texto


def test_render_cosecha_dice_por_que_no_cosecho():
    estancado = _envio("006e", tipo="b", historico=(exp.EstadoCertificado(
        codigo=17, titulo="Entregado",
        fecha=datetime.fromisoformat("2026-06-17T10:00:00+02:00")),))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(estancado,), leida_en=LEIDA)
    texto = cli.render_cosecha([], e)
    assert exp.QUE_SIGNIFICA[exp.ESTANCADO] in texto and "· 006e" in texto
    assert exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR] not in texto
```

y en `test_render_cosecha_distingue_lo_nuevo_de_lo_que_ya_estaba` la llamada `cli.render_cosecha([c], ())` pasa a `cli.render_cosecha([c], exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion", leida_en=LEIDA))` (sus aserciones no cambian).

En `tests/test_expedicion_aportable.py`, tras `test_lo_que_aun_puede_mejorar_se_declara_pendiente`:

```python
def test_lo_estancado_se_declara_pendiente_con_SU_motivo(tmp_path):
    """M-21: el aportable decía de todo lo no cosechable que «puede mejorar». Un burofax en
    17 desde hace 55 días no mejorará: se dice lo que es."""
    entorno, _, _ = _escenario(tmp_path, historicos={"006b": [
        {"codigo": 17, "titulo": "", "fecha": "2026-08-01T10:00:00+02:00", "detalle": None}]})
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PENDIENTE
    assert exp.QUE_SIGNIFICA[exp.ESTANCADO] in r["006b"].motivo
    assert exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR] not in r["006b"].motivo


def test_lo_que_aun_puede_mejorar_lo_dice_en_su_motivo(tmp_path):
    entorno, _, _ = _escenario(tmp_path, historicos={"006b": [
        {"codigo": 17, "titulo": "", "fecha": "2026-09-11T10:00:00+02:00", "detalle": None}]})
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR] in r["006b"].motivo
```

- [x] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q --tb=short tests/test_codicert_cli_f2.py tests/test_expedicion_aportable.py`
Expected: FAIL — `ValueError: substring not found` en los `index`, `"CANALES SIN CLASIFICAR"` ausente, `render_cosecha` que itera la `Expedicion` como si fuera la lista de pendientes, y los dos motivos del aportable.

- [x] **Step 3: Implement**

En `scripts/codicert.py`, antes de `render_estado`:

```python
def _dias(n: int) -> str:
    return f"{n} día" if n == 1 else f"{n} días"


def _no_cosechables(expedicion: exp.Expedicion, titulo: str) -> list[str]:
    """Lo no cosechable, con su motivo: es lo que el abogado necesita para saber qué
    hacer (M-21). Antes salía todo bajo «el hecho aún puede mejorar», y de un envío que
    lleva ochenta días quieto eso es falso."""
    grupos = expedicion.pendientes_por()
    if not grupos:
        return []
    lineas = ["", f"  {titulo}"]
    for motivo, envios in grupos.items():
        alerta = "" if motivo == exp.PUEDE_MEJORAR else "⚠️ "
        lineas.append(f"    {alerta}{exp.ETIQUETA[motivo]} — {exp.QUE_SIGNIFICA[motivo]}")
        lineas += [f"      · {e.id_envio} ({e.canal}), "
                   f"{_dias(e.dias_quieto(expedicion.leida_en))} sin moverse" for e in envios]
        if motivo == exp.ESTANCADO:
            lineas += ["      Si el certificado de hoy te sirve, `cosechar --incluir-pendientes`",
                       "      lo baja con su estado en el nombre, sin ocupar el sitio del",
                       "      definitivo. El aportable, solo sobre el definitivo."]
    return lineas
```

En `render_estado`, la columna COSECHABLE dice `'sí' if e.cosechable else 'no'` (antes `'aún no'`, que promete lo que un estancado no cumplirá), y el bloque

```python
    if expedicion.pendientes:
        lineas += ["", "  PENDIENTES (el hecho aún puede mejorar; no se cosechan):"]
        lineas += [f"    · {e.id_envio} ({e.canal})" for e in expedicion.pendientes]
```

pasa a

```python
    lineas += _no_cosechables(expedicion, "PENDIENTES, y por qué no se cosechan:")
```

y, tras el aviso de códigos desconocidos:

```python
    canales = sorted({e.tipo for e in expedicion.envios if not e.canal_clasificado})
    if canales:
        lineas += [
            "", "  ⚠️ CANALES SIN CLASIFICAR: tipo " + ", ".join(canales),
            "     No se cosechan: no se sabe en qué culminan. Añádelos a",
            "     `CANAL_DE_TIPO` y `_CULMINACION` en core/expedicion_certificada.py.",
        ]
```

`render_cosecha` cambia de firma y de bloque:

```python
def render_cosecha(cosechados, expedicion: exp.Expedicion) -> str:
    """Qué se archivó y qué no —con su motivo—, con el emisor verificado a la vista."""
```

con

```python
    if pendientes:
        lineas += ["", "  NO COSECHADOS (el hecho aún puede mejorar):"]
        lineas += [f"    · {e.id_envio} ({e.canal})" for e in pendientes]
```

sustituido por

```python
    lineas += _no_cosechables(expedicion, "NO COSECHADOS, y por qué:")
```

La llamada del `main` pasa a `print(render_cosecha(cosechados, expedicion))`, y la ayuda de `--incluir-pendientes` a:

```python
                           help="baja también el certificado de lo no cosechable (en "
                                "curso, estancado o sin clasificar); su nombre lleva el "
                                "estado, así que no ocupa el sitio del definitivo")
```

En `core/expedicion_certificada.py`, `_preparar_bajo_candado`:

```python
        if not envio.cosechable:
            motivo = envio.pendiente_por(expedicion.leida_en)
            resultados.append(AportablePreparado(
                envio.id_envio, envio.canal, PENDIENTE,
                motivo=f"no es cosechable — {QUE_SIGNIFICA[motivo]}. El aportable se "
                       "prepara sobre el certificado definitivo."))
            continue
```

- [x] **Step 4: Run them to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_codicert_cli_f2.py tests/test_expedicion_aportable.py tests/test_expedicion_cosechar.py`
Expected: PASS (los dos lentos de OCR real de `test_expedicion_aportable.py` quedan en `skip` sin `--runslow`).

- [x] **Step 5: Commit**

```bash
git add scripts/codicert.py core/expedicion_certificada.py tests/test_codicert_cli_f2.py tests/test_expedicion_aportable.py
git commit -m "F2/F3: estado, cosechar y el aportable dicen el motivo de lo no cosechable (M-21)"
```

### Task 5: verificación — suite, mutantes y el barrido real otra vez

**Files:** ninguno del repo; los scripts van al scratchpad de la sesión.

- [x] **Step 1: Las dos semillas, suite entera**

Run: `python -m pytest -q --tb=short -n auto --randomly-seed=777` y luego `--randomly-seed=31337`
Expected: verde las dos; el conteo sube exactamente en los tests nuevos de este plan (y los paramétricos) respecto del último cierre, sin `skip` ni `xfail` nuevos.

- [x] **Step 2: Los lentos de lo tocado**

Run: `python -m pytest -q --tb=short --runslow tests/test_expedicion_aportable.py`
Expected: PASS, incluidos los dos de OCR real.

- [x] **Step 3: Mutantes**

Un arnés en el scratchpad que aplique cada mutante sobre una copia en memoria del módulo y corra `tests/test_expedicion_estados.py tests/test_expedicion_observada.py tests/test_expedicion_pendientes.py tests/test_expedicion_refrescar.py tests/test_codicert_cli_f2.py tests/test_expedicion_aportable.py`. Cada uno tiene que **morir**:

1. `_INDICIOS_DE_ENTREGA` sin el 27.
2. `_INDICIOS_DE_ENTREGA` sin el 17.
3. `cerrado_en` sin la rama del 22.
4. `cerrado_en` que mira el 22 aunque haya indicios.
5. `cosechable` sin la comprobación del canal.
6. `pendiente_por` con `>=` en vez de `>`.
7. `DIAS_ESTANCADO = 30`.
8. `pendiente_por` que pregunta por lo quieto antes que por el código sin clasificar.
9. `ultimo_evento` con `min` en vez de `max`.
10. `refrescar` con `leida_en=datetime.now(timezone.utc)` en vez del reloj del entorno.
11. `_no_cosechables` sin la línea de `--incluir-pendientes`.
12. `_preparar_bajo_candado` con el motivo fijo de antes.

Expected: 12 de 12 muertos. Uno que sobreviva es un test que falta, y se escribe antes de seguir.

- [x] **Step 4: El barrido real, con el código nuevo (M-22)**

Volver a correr `barrido_estados.py` (solo lectura) y comparar, envío a envío, el veredicto de F2 antes y después.
Expected: **un solo cambio de `cosechable`** —`006bij47xan`, de no a sí—, y los motivos: `006bkxe0q63` → `CANAL_SIN_CLASIFICAR`, `006bgjupt2a` → `ESTANCADO`, y el resto de los no cosechables → `PUEDE_MEJORAR`. Cualquier otra diferencia se explica antes de seguir.

### Task 6: el spec, el backlog y el PLAN

**Files:**
- Modify: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`
- Modify: `docs/MEJORAS_FUTURAS.md`, `PLAN.md`

- [x] **Step 1: Spec rev. 17**

Nota de cabecera «Rev. 17 (2026-09-26)» y, en el cuerpo:
- §1.1: el SMS Certificado **sí** registró un 20 «Documentación accedida» (una muestra, M-18); la razón para descartarlo que daba el §1.1/§5 regla 7 no se sostiene tal cual, y la elección de la entrega electrónica sigue en pie por otra: el SMS Certificado admite **un** fichero, y las condiciones van en adjunto aparte (§7).
- §1.3: el SMS usa los estados del correo, 29/30/39 no aparecen en 22 SMS (M-17); el 22 y D-1; el 40 a los 30 días exactos, 30 de 30; `fecha_expiracion` = envío + 5 años (M-20).
- §6.3: el 22 como causa de cierre, con su condición y el riesgo aceptado.
- §7.1: los cuatro motivos de lo no cosechable y el aviso de estancado (D-3); el límite de F3 con el provisional.

- [x] **Step 2: MEJORAS**

Entrada nueva con el siguiente número libre **leído de `origin/main` al escribirla** (hoy el más alto es el #304 de esta rama): «El aportable de un certificado provisional», disparador: el primer envío estancado cuyo certificado haya que aportar.

- [x] **Step 3: PLAN.md**

La fila del envío certificado (#37) gana una línea: estados medidos sobre 117 envíos y este plan.

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md docs/MEJORAS_FUTURAS.md PLAN.md
git commit -m "docs: spec rev. 17 de Codicert: los estados medidos en 117 envios reales y el 22 que cierra"
```

### Task 7: revisión adversarial — R1 sobre el diff

- [ ] **Step 1: Encargo y lanzamiento**

**Una ronda, sobre el diff** de las Tasks 1-4 (tabla de rondas de `CLAUDE.md`: la pieza no decide quién escribe sobre qué copia ni destruye datos). **Modelo `gpt-6-astra` · `medium`, fila «escritura sobre datos de cliente»**, y la frontera se nombra en el PR: si la regla del 22 cierra de más, `cosechar` archiva como definitivo un certificado «sin entrega», la cosecha siguiente lo salta (`ya_estaba`) y un acceso posterior del requerido no entraría nunca solo en el expediente. Mandato numerado y anclado a commit, con los dos ejes (severidad y coste del remedio), sin nada que haga sospechoso volver limpio; `SHIP` es un resultado legítimo. Vigía armado **antes** de lanzar, que cubra la muerte y no solo el fin. Esta ronda es la **R1 de esta pieza**: no es una R4 de F3 ni cubre la remediación de la R3 de F3, y el mandato lo dice.

- [ ] **Step 2: Adjudicación**

Cada hallazgo, contra la fuente. La adjudicación va **embebida en este plan** (§ al final, encabezado canónico y ficha); la voz del revisor, literal, en el acta hermana `…-estados-medidos-r1-adversarial-review.md`, con nonce y digest (nace con la ronda; hasta entonces no se cita por su ruta, porque el guard G2 exige que toda cita resuelva en disco). Los guards G7/G8/G9 de `tests/test_docs_gobernanza.py`, verdes. Si el revisor no corre, la cobertura se declara **AUSENTE**, no parcial.

---

## Ejecución (2026-09-26)

- **Commits:** `979d41a` (Task 1), `aad3765` (Task 2), `4e24233` (Task 3), `c8ae1ad` (Task 4, con
  D-2 bis), `98f6530` (el plan: D-2 bis y la cita del acta) y el de la documentación de la Task 6.
- **TDD:** cada test nuevo se vio fallar por la razón prevista antes de implementar —en la Task 2,
  además, se comprobó a mano que un `s` con 42 **se cosechaba** con el código de antes—.
- **Suite, dos semillas:** **6.465 casos, 0 fallos, 0 errores, 96 omitidos**, idénticos con la 777 y
  la 31337, por JUnit. **+29 sobre los 6.436 del último cierre tras mezclar `main`, y cuadran al
  test:** 9 de la Task 1 (el paramétrico cuenta cinco), 1 de la Task 2, 13 de la Task 3 y 6 de la
  Task 4. Los 96 omitidos, los mismos. La primera corrida dio **un rojo en las dos semillas**, el
  guard G2 de `tests/test_docs_gobernanza.py`: este plan citaba por su ruta el acta de la R1, que
  aún no existe. El guard tenía razón; corregido en `98f6530` y vuelta a correr entera.
- **Lentos de lo tocado:** `tests/test_expedicion_aportable.py --runslow`, 50 de 50, los dos de OCR
  real dentro.
- **Mutantes:** **18 de 18 muertos**, cada uno por el test que declaraba (los 12 del plan y seis
  más: los dos de D-2 bis, el aviso de canales, la zona de `leida_en`, los grupos vacíos y el
  motivo en `cosechar`). Árbol restaurado byte a byte.
- **M-22, el barrido real con el código nuevo** (solo lectura): **119 envíos, un solo cambio de
  `cosechable`** —`006bij47xan`, de no a sí—; `006bkxe0q63` → canal sin clasificar;
  `006bgjupt2a` → estancado (88 días); el resto de lo no cosechable, en curso (4 burofax, 11
  correos, 6 SMS). Es exactamente lo que la Task 5 esperaba.

