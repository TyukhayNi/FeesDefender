---
tipo: spec
estado: vigente
creado: 2026-09-14
objeto: core/sudespacho_relations.py, core/crm_ficha.py, core/sudespacho_actuaciones.py
rev: "1"
---

# P6 — La ficha CRM y la actuación, sin YAML a mano y sin fundir a dos personas

Tres piezas del §P6 del handoff de la apertura. Fila **#33** de `PLAN.md` (pendiente de crear).
**Dos rondas** por el radio de daño: la pieza 2 decide **la identidad de una parte** y hoy
escribe encima de la ficha de otro cliente.

## 0. Lo que este spec NO rehace, porque ya está

El §P6 del handoff pide también «corregir el §15.6 de `INTEGRACION_SUDESPACHO.md`
(`items`/`hydra:member` está al revés)». **Ya está corregido en `main`**: el §15.6 lo tiene
tachado y explicado —no era una forma sustituyendo a otra, era la **cabecera `Accept`
eligiendo**: `application/json` exacto da `{"items"}` y `ld+json`, `*/*` o ninguna dan
`hydra:member`—. El handoff venía rancio en ese punto; se verificó antes de planificar.

Y la premisa de que `crm_ficha.py` «tiene dueña» —una sesión hermana— **es falsa a fecha de
hoy**: no hay ninguna sesión viva, ni PR abierto, ni rama con trabajo sobre esto. La anotación
de `PLAN.md` es del 2026-09-05 y quedó rancia. Verificado con `list_sessions`, `gh pr list` y
`git ls-remote` antes de tocar nada.

## 1. Pieza 1 — `core/sudespacho_actuaciones.py` (`MEJORAS #209`)

**El problema, en las palabras del backlog:** «crear actuaciones en el CRM no tiene helper: la
receta vive en prosa y se reescribe a mano cada vez». Y la frontera que el propio `#209`
enuncia: *el contrato del CRM se documenta y no se encapsula*, así que cada operación nueva se
reescribe contra la prosa.

La receta está medida y verificada de punta a punta (`INTEGRACION_SUDESPACHO.md §15.6`,
2026-09-10, W-02VEKE). Seis pasos, ninguno opcional. Este módulo los encapsula:

| Función | Paso | Lo que encapsula, y por qué no es trivial |
|---|---|---|
| `aprender_id_predefinido(asunto)` | 1 | **Tres resultados, no dos:** un id, «no aplica» (las filas existen y traen el campo vacío — `[APER-72]` lo midió sobre 20 actuaciones reales), y «no pude mirar». Confundir los dos últimos hace inventar un entero |
| `resolver_profesional(username)` | 2 | `profesional_asignado` es el **username** (`Nikolai_Tyukhay`), no el id de `empleados`. El id de Ana es 8 y **no vale aquí** |
| `crear_actuacion(...)` | 4 | POST con `Estado`, `fecha_vencimiento` ISO con offset, `facturar`/`obligacion` booleanos, `duracion` `HH:MM:SS`→segundos, `Prioridad` obligatoria |
| `vincular_actuacion(elemento, exp_id, act_id)` | 5 | `POST relation_element` con `["right.actuaciones.{id}"]`. **Sin esto la actuación queda huérfana y el POST del paso 4 devuelve 201 igual** |
| `verificar_actuacion_vinculada(...)` | 6 | Relee **desde el lado del expediente**. El `GET` por id de la actuación devuelve **404 aunque exista**: no sirve como comprobación |
| `alta_actuacion(...)` | 1→6 | Orquestador. **Devuelve el resultado de la verificación, no el 201 del POST** |

**`asunto_canonico(rol_firmante)` y por qué es la pieza con más filo.** `[APER-72]` midió que
**el prefijo del `Subject` ES la tarifa**: `SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD` factura
a **103,00 €/h** (Nikolai) y `ABOGADO - …` a **77,00** (otra persona del equipo). Copiar el
prefijo equivocado **factura al cliente la tarifa de otro**. El prefijo se elige por **quién
firma**, no por quién teclea, y el catálogo canónico vive en `docs/MANUAL_DESPACHO.md`.

**Decisión de diseño (a atacar):** `asunto_canonico` **exige** el rol del firmante y falla si
no se le da; no tiene defecto. Un defecto aquí sería elegir una tarifa en silencio.

**Y `duracion_desde_estado(estado_json)`:** el evento de `estado.json` tiene `iniciada` y
`terminada` pero **no** `duracion_s`. Se deriva de la diferencia, y **se declara** cuando falta
uno de los dos extremos en vez de suponer cero.

**Lo que este módulo NO hace:** aplicar la tarifa de usuario (es el botón de `§15.4`, solo UI) y
escribir `tipo_actuacion` (va vacío en las 20 reales).

## 2. Pieza 2 — `[APER-71]`: el email no identifica a una persona

**El defecto, con su mecánica exacta** (`core/sudespacho_relations.py::resolver_parte`):

```python
if ids_nif:  return ResolucionParte(id=ids_nif.pop(),  por="nif")
if ids_mail: return ResolucionParte(id=ids_mail.pop(), por="email")   # ← aquí
```

Escenario medido el 2026-09-10 sobre el expediente 643: la segunda firmante del encargo, **con
NIF propio y distinto**, comparte el correo doméstico con el primero —lo normal en un
matrimonio, que es la norma entre propietarios—. `_buscar_registros(nif=B)` no devuelve nada,
`_buscar_registros(email=casa@…)` devuelve la ficha de **A**, y la función resuelve a A «por
email». Después, `_completar_contrario_existente` **escribe los datos de B encima de la ficha de
A**, y `ensure_contrario_vinculado` lo informa como «existente».

**La frontera, que no es el caso:** *un email identifica un buzón, no una persona.* Un NIF sí
identifica a una persona. Cuando se aportó un NIF y ese NIF no casa ninguna ficha, resolver por
email **afirma una identidad que el NIF desmiente**.

**El remedio propuesto.** `_buscar_registros` ya acepta `properties=` extra, así que la consulta
por email puede traer también el NIF de la ficha encontrada, sin una llamada más. Con NIF
aportado, `ids_nif` vacío e `ids_mail = {X}`:

| NIF de la ficha X | Lectura | Resultado |
|---|---|---|
| Existe y **difiere** del aportado | Son personas distintas que comparten buzón | `ResolucionParte()` **vacía** → se crea ficha nueva, y se **dice** por qué |
| **Vacío** en el CRM | No se puede distinguir «es la misma sin NIF registrado» de «es otra» | `ambiguo` → **para**. Fallar cerrado es la política de la casa (decisión de Nikolai, 2026-09-04) |
| Coincide con el aportado | No debería ocurrir (entonces `ids_nif` no estaría vacío); si ocurre es una diferencia de canonicalización | `ambiguo` → para, y lo dice |

**Y lo que NO cambia:** sin NIF aportado, resolver por email sigue siendo lo único posible y se
mantiene (`por="email"`). El cambio se activa **solo cuando hay un NIF que contrastar**.

**Decisión de diseño (a atacar):** el segundo caso —ficha sin NIF— para en vez de crear. Fallar
cerrado bloquea un alta legítima y obliga a una intervención manual; fusionar dos personas
corrompe la ficha de un cliente y **se descubre tarde**. Se elige el coste reversible.

## 3. Pieza 3 — `[APER-63]`: la ficha lee **un** contrario

`core/crm_ficha.py` hace `contrario_raw = data.get("contrario")` y construye **uno**. Una
reclamación formulada por dos firmantes —de nuevo, un matrimonio— exige hoy una segunda llamada
a mano.

**Remedio:** aceptar `contrario:` como mapping **o** como lista, y vincular todos. Con la pieza 2
detrás, dos firmantes que comparten correo ya no se funden.

**Compatibilidad:** los `_ficha_crm.yaml` existentes llevan un mapping. La lectura de un mapping
suelto se conserva, no se migra nada.

**Y lo que este spec NO toca**, aunque `[APER-63]` lo menciona en el mismo bloque: que
`cliente_propio` lleve la clave y no el id ya **aborta con un error legible**, que es el
comportamiento correcto; y que el móvil extranjero no se pueda guardar es un límite del CRM
(`[APER-14]`), no un defecto del código.

## 4. Cómo se prueba sin tocar el CRM

**Ningún test de este diff toca el CRM real.** `httpx` se mockea por inyección, que es el patrón
que el repo ya usa desde el PR #282 (los dos tests de colaborador «inyectan el `client` en vez de
construirlo del entorno»). Lo que se puede probar así:

- la **gramática** de cada petición (params, headers, cuerpo);
- las **tres** salidas de `aprender_id_predefinido`, incluida «no pude mirar»;
- que `alta_actuacion` **no declara éxito sin la verificación del paso 6**;
- la tabla entera de la pieza 2, incluidos los bordes;
- que un `contrario:` mapping y uno lista producen el mismo resultado para un solo contrario.

**Lo que NO queda acreditado y se declara:** que los payloads son los que el CRM acepta hoy. Eso
lo acredita una corrida real contra el tenant, y **no se hace en este diff**. El módulo encapsula
una receta ya verificada en vivo el 2026-09-10; si el CRM cambia, lo dirá la primera corrida.

## 5. Presupuesto de rondas

**Dos**, por la regla del 2026-08-26: la pieza 2 decide **quién es quién** y hoy **corrompe la
ficha de un cliente**. Una sobre este diseño y otra sobre el diff.

La pieza 1 sola habría sido una ronda; van juntas porque comparten rama y porque fragmentarlas
era justamente lo que se decidió no hacer.
