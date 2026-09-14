---
tipo: spec
estado: vigente
creado: 2026-09-14
objeto: core/sudespacho_relations.py, core/crm_ficha.py, core/sudespacho_actuaciones.py
rev: "3"
---

# P6 — La ficha CRM y la actuación, sin YAML a mano y sin fundir a dos personas

Tres piezas del §P6 del handoff de la apertura. **Dos rondas** por el radio de daño: la pieza 2
decide **la identidad de una parte** y hoy escribe encima de la ficha de otro cliente.

**Rev. 3 (2026-09-14), tras la R3 excepcional: 9 hallazgos, 9 confirmados, 0 refutados.** La R3
la autorizó Nikolai expresamente sobre el techo de dos rondas, y su objeto no era la pieza sino
**la remediación de la R2**. Encontró que el remedio cerraba el caso y no la frontera en cinco
sitios, y que un mutante del arnés moría por la razón equivocada. Adjudicación en el §8, con las
**siete fronteras** en que se agrupan los nueve. **Se cierra sin cuarta ronda**, por decisión de
Nikolai: lo que la sustituye es correr la pieza contra el CRM real (§9).

**Rev. 2 (2026-09-14), tras la R1 adversarial: 8 hallazgos, 8 confirmados.** La rev. 1 no se
conserva porque no llegó a código; lo que cambió y por qué está en el §6.

## 0. Lo que este spec NO rehace, porque ya está

El §P6 del handoff pide «corregir el §15.6 (`items`/`hydra:member` está al revés)». **Ya está
corregido** (§15.6, líneas 2125-2134): no era una forma sustituyendo a otra, era la **cabecera
`Accept` eligiendo** — `application/json` exacto da `{"items"}`; `ld+json`, `*/*` o ninguna dan
`hydra:member`.

Y la premisa de que `crm_ficha.py` «tiene dueña» es **falsa a fecha de hoy**: ninguna sesión
viva, ningún PR abierto, ninguna rama con trabajo sobre esto. Verificado con `list_sessions`,
`gh pr list` y `git ls-remote`. *(El revisor no puede comprobar esto desde su copia y lo declaró
SIN VERIFICAR, correctamente: es una afirmación del autor.)*

## 1. El vocabulario de la identidad, que es lo que faltaba

La rev. 1 hablaba de «NIF aportado» y de que «difiere», y las dos expresiones tapaban estados
distintos (R1/H-01, H-02). Antes de cualquier tabla, tres definiciones:

**Un documento puede estar en tres estados, no dos:**

| Estado | Qué es | Cómo se reconoce |
|---|---|---|
| **ausente** | no se aportó | cadena vacía o solo espacios |
| **utilizable** | se aportó y tiene forma canónica | `_canonizar_documento(x)` devuelve algo no vacío |
| **no interpretable** | se aportó *algo* que no sobrevive a la canonicalización | `x` no vacío y `_canonizar_documento(x)` vacío |

El tercero existe y no es teórico: `_canonizar_documento` elimina separadores, así que `" -- . "`
se convierte en `""`. La rev. 1 lo trataba como «ausente» y activaba la política de email en
silencio. **La pérdida de información durante la normalización no puede degradar un documento
aportado a «no se aportó».**

**Comparar dos documentos es comparar sus formas canónicas, en los dos lados.** `12.345.678-z` y
`12345678Z` son el mismo documento; una comparación textual los declara distintos y **duplica
una ficha legítima**. La igualdad es simétrica y solo está definida entre **utilizables**: si
cualquiera de los dos lados es ausente o no interpretable, **no hay comparación**, y eso no
autoriza nada.

**Y `ResolucionParte()` vacía significa «no existe: créala».** No es un valor neutro:
`_exigir_identidad_cierta` la deja pasar sin restricción. Devolverla ante evidencia no comparable
es autorizar una creación con el contrato de fallar cerrado puesto del revés.

## 2. Pieza 2 — `[APER-71]`: el email identifica un buzón, no a una persona

**El defecto** (`core/sudespacho_relations.py::resolver_parte`): con NIF propio que no casa nada
y correo doméstico compartido —lo normal en un matrimonio, que es la norma entre propietarios—,
la función resuelve a la ficha del cónyuge «por email», y `_completar_contrario_existente`
**rellena los huecos de la ficha ajena con los datos del otro**. Medido el 2026-09-10 sobre el
expediente 643. *(Precisión que aportó la R1: rellena huecos, no sustituye campos poblados. Es
contaminación de una ficha ajena y un vínculo erróneo, no un PUT indiscriminado.)*

### 2.1 El orden de decisión, y por qué este orden

**Un criterio fuerte que identifica unívocamente no puede quedar tapado por la multiplicidad de
uno débil.** Esa es la frontera de R1/H-03, y obliga a reordenar la función: hoy la guarda de
ambigüedad del email se evalúa **antes** del cruce con el NIF, así que `ids_nif={B}` con
`ids_mail={A,B}` sale `ambiguo` teniendo una respuesta unívoca delante.

Orden nuevo, y cada paso responde a un hallazgo:

1. **Consulta fallida → `sin_comprobar`.** Se conserva tal cual y con su precedencia actual. La
   R1 lo intentó refutar y no pudo: hoy bloquea con y sin match de NIF. No se toca.
2. **NIF no interpretable → `ambiguo`, con su motivo.** Nunca cae a la política de email
   (R1/H-01).
3. **`ids_nif` con exactamente una ficha → resuelve. El NIF manda**, sin mirar la cardinalidad
   del email. Si el email da varias y una es esa, la intersección lo confirma; si no la incluye,
   es `conflicto`, que ya existe.
4. **`ids_nif` con varias → `ambiguo`.** Sin cambios.
5. **`ids_nif` vacío y NIF utilizable** → la tabla del §2.2.
6. **NIF ausente** → política actual por email (`por="email"`), sin cambios, con una sola
   ficha; con varias, `ambiguo`. Es lo único posible cuando no hay nada que contrastar.

### 2.2 Con NIF utilizable que no casó ninguna ficha

La consulta por email trae también el NIF de cada ficha (`_buscar_registros` ya acepta
`properties=` extra; la R1 lo verificó ejecutándolo con HTTP simulado). Para **cada** ficha que
casa el email:

| NIF de esa ficha | Lectura | Efecto |
|---|---|---|
| **utilizable y distinto** (canónico ≠ canónico) | persona distinta que comparte buzón | esa ficha **se descarta como candidata** |
| **utilizable e igual** | la consulta por NIF debió encontrarla y no lo hizo | `ambiguo` — hay algo que no cuadra y no se adivina |
| **ausente o no interpretable** | no se puede distinguir «la misma sin NIF registrado» de «otra» | `ambiguo` |

Y sobre el conjunto resultante:

- **todas descartadas** → `ResolucionParte()` vacía: no existe, se crea. Es el único camino a la
  creación, y exige que **todas** las fichas del buzón tengan NIF utilizable y distinto.
- **alguna no descartada** → `ambiguo`, y para.

**Por qué `ambiguo` y no crear, en el caso de la ficha sin NIF:** fallar cerrado bloquea un alta
legítima y cuesta una intervención manual; fusionar dos personas corrompe la ficha de un cliente
y **se descubre tarde**. Es la política que `_exigir_identidad_cierta` ya declara (decisión de
Nikolai, 2026-09-04), y la rev. 1 la contradecía sin decirlo.

### 2.3 El estado que crea este remedio, y que la rev. 1 dejaba bloqueado

R1/H-03: crear B para que A y B compartan buzón produce `ids_mail={A,B}` **en la corrida
siguiente**. Con el orden del §2.1 eso ya no bloquea —el paso 3 resuelve por NIF antes de mirar
la cardinalidad del email—, así que **la reejecución converge**: es la propiedad que la rev. 1
rompía y que hay que probar explícitamente, junto con el corte a mitad (B creado, vínculo
fallido) y un tercer firmante del mismo buzón.

## 3. Pieza 3 — `[APER-63]`: la ficha lee **un** contrario

`core/crm_ficha.py:109` hace `data.get("contrario")` y construye uno. Dos firmantes exigen hoy
una llamada a mano.

**Remedio:** aceptar mapping **o** lista. Y con la semántica que la rev. 1 no fijaba (R1/H-08),
porque el lector actual devuelve `contrario=None` por igual para `null`, `[]` y `[no-mapping]`:

| Forma | Significado |
|---|---|
| clave ausente o `null` | no hay contrario — es legítimo |
| mapping | un contrario (compatibilidad; no se migra nada) |
| lista de mappings | N contrarios, **en el orden del fichero** |
| lista **vacía** | no hay contrario, igual que ausente |
| elemento que no es mapping | **error legible con su índice**, y cero escrituras |

**Validar la colección ENTERA antes de escribir nada.** Filtrar los elementos inválidos —el
patrón que usa `colaboradores`— convertiría una lista de un elemento malo en «cero contrarios»
en silencio, y validar al iterar escribiría el primero antes de descubrir que el segundo está
roto. **Un elemento inválido no es una parte ausente.**

## 4. Pieza 1 — `core/sudespacho_actuaciones.py` (`MEJORAS #209`)

Encapsula la receta de seis pasos del §15.6 (medida en vivo el 2026-09-10, W-02VEKE). La frontera
que el propio `#209` enuncia: *el contrato del CRM se documenta y no se encapsula*, así que cada
operación se reescribe contra la prosa.

| Función | Paso | Lo que encapsula |
|---|---|---|
| `aprender_id_predefinido(asunto)` | 1 | **Tres resultados:** un id, «no aplica» (hay filas y traen el campo vacío — `[APER-72]` sobre 20 reales) y «no pude mirar». También **cero filas**, que no es ninguno de los anteriores |
| `resolver_profesional(username)` | 2 | El **username** (`Nikolai_Tyukhay`), no el id de `empleados` |
| **`resolver_destino(case_id, elemento, exp_id)`** | **3** | **Faltaba en la rev. 1 (R1/H-06).** Resuelve el par `(elemento, id)` desde `_caso.md` y lo **contrasta** con el expediente antes de escribir |
| `crear_actuacion(...)` | 4 | POST con `Estado`, `fecha_vencimiento` ISO con offset, booleanos, `duracion` `HH:MM:SS`, `Prioridad` |
| `vincular_actuacion(...)` | 5 | `relation_element`. Sin esto queda huérfana y el paso 4 devuelve 201 igual |
| `verificar_actuacion_vinculada(...)` | 6 | Relee **del lado del expediente**. El `GET` por id devuelve **404 aunque exista** |
| `alta_actuacion(...)` | 1→6 | Orquestador con recibo (§4.2) |

### 4.1 El paso 3, que promete la receta y la rev. 1 no asignaba

**Cada elemento numera aparte.** En W-02VEKE, `464` es de `extrajudiciales` y `540` de
`expedientes_judiciales`, y `GET expedientes_judiciales/464` devuelve **un expediente de otro
caso, con 200 y todo**. Pasar `elemento` y `exp_id` no acredita a qué caso pertenecen, y
`_link_rest` documenta devolver **201 para un expediente inexistente**.

**Y la verificación del paso 6 no lo caza**, porque usa la misma dirección que la escritura:
verificar la llegada no verifica la intención. Así que el contraste va **antes del POST**, contra
algo del propio expediente (la referencia, el conteo de documentos), y sin él no se escribe.

### 4.2 El recibo, porque una verificación negativa no es ausencia de escritura

R1/H-04: si el paso 4 crea la actuación N y el paso 5 falla, el llamador recibe «no verificada» y
repite el alta entera; el nuevo POST crea M, M se vincula y **N queda huérfana**. La idempotencia
documentada de `relation_element` evita repetir *el mismo vínculo*, no crear otra actuación — y
la del POST de creación **no está acreditada**.

`alta_actuacion` devuelve un **recibo** con el `act_id` obtenido y **el último paso alcanzado**,
y admite reanudar desde ahí sobre ese id. Tres estados terminales, no dos:

- **verificada** — los seis pasos.
- **incompleta con id conocido** — hay efecto en el CRM y se puede reanudar. **Reintentar el alta
  completa está prohibido en este estado.**
- **incierta** — el POST no dio recibo (un timeout deja hasta el id en duda). Se declara y se
  concilia a mano; no se reintenta a ciegas.

### 4.3 `asunto_canonico` y de dónde sale el rol

El prefijo del `Subject` **es la tarifa**: `SENIOR - EXTRAJUDICIAL - …` factura a **103,00 €/h**
y `ABOGADO - …` a **77,00** (`[APER-72]`, 20 actuaciones reales). Copiar el prefijo equivocado
**factura al cliente la tarifa de otro**, así que la función **exige** el rol y no tiene defecto.

**Pero exigir un dato no lo crea** (R1/H-05, y coincide con lo que el autor encontró por su
cuenta antes del informe). Hoy no hay proveedor: `FichaCRMInput` no tiene firmante ni profesional,
`scripts.crm_ficha.main` recibe solo caso y confirmación, el `--rol` de `abrir_caso` es una
subcarpeta de WhatsApp, y el único origen es `sudespacho_create.py:894`, con
`responsable: str = "Nikolai_Tyukhay"` **hardcodeado**. Endurecer la firma sin abrir el origen
traslada el defecto un nivel arriba y añade la ilusión de haberlo cerrado.

**Y el dato que lo vuelve imposible de inferir**, que la R1 aporta: *quien opera no es quien
firma*. Ana puede tramitar una revisión que firma Nikolai. Tomar el actor de la UI elegiría la
tarifa equivocada con total naturalidad.

**Decisión:** el firmante es una **entrada humana explícita** —campo nuevo `firmante:` en el
`_ficha_crm.yaml`, sin defecto— y `asunto_canonico` valida su coherencia con
`profesional_asignado`. No se infiere, no se automatiza el acto fiscal. Sin el campo, el helper
**para y lo dice**; es un dato que alguien tiene que decidir.

### 4.4 La duración: qué fichero, qué ventana

R1/H-07, que amplía lo que el autor ya había visto:

- **El fichero no es `estado.json`.** Es `00_Input/_apertura_v1.json` (`_FICHERO` en
  `core/apertura_v1_estado.py:20`). El nombre venía del handoff, sin verificar.
- **El evento `apertura_v1_terminada` NO lleva las fechas** — sus `details` son `estado`,
  `parada`, `pendientes`, `etapas`. Un consumidor del log no puede derivar la duración.
- **Y la ventana medida es la ronda Drive → CRM → sala de máquina**, que **no** es la actividad
  que se factura: no incluye la revisión de viabilidad posterior. Una resta correcta sobre la
  ventana equivocada sigue dando una duración equivocada.

**Decisión:** `duracion_desde_ronda(case_dir)` lee `RondaV1`, acepta las fechas UTC con `Z`,
devuelve **`None` declarado** cuando falta `terminada` (la ronda no se cerró), y **rechaza**
extremos invertidos o sin zona. Y **se documenta que mide la ronda V1, no la actuación**: quien
la use para facturar tiene que saber qué está facturando. El marcador se reemplaza al abrir otra
ronda, así que tampoco es un histórico.

## 5. Cómo se prueba sin tocar el CRM

Ningún test de este diff toca el CRM real; `httpx` se sustituye por inyección, el patrón del
PR #282. Además de la gramática de cada petición:

- las **cuatro** salidas de `aprender_id_predefinido`, incluidas «cero filas» y «no pude mirar»;
- la tabla del §2.2 **entera**, con sus bordes: NIF no interpretable, NIF CRM no interpretable,
  igualdad canónica con `12.345.678-z` vs `12345678Z`, varias fichas por email;
- **reejecución y composición** (§2.3): dos corridas seguidas, corte con B creado y vínculo
  fallido, tercer firmante, y **las dos permutaciones** del orden de resultados;
- los **tres estados terminales** del recibo, con fallo inyectado en cada paso y dos intentos
  consecutivos;
- que `resolver_destino` con referencia discrepante produce **cero escrituras**;
- la semántica YAML del §3 completa, incluido el elemento inválido con su índice;
- que `asunto_canonico` sin firmante para, y que un operador distinto del firmante no cambia el
  prefijo.

**Lo que NO queda acreditado, y se declara:** que los payloads son los que el tenant acepta hoy,
la normalización real del almacenamiento del CRM, **la idempotencia del POST de creación** y la
concurrencia. Eso lo acredita una corrida real, y **no se hace en este diff**.

## 6. Adjudicación de la revisión adversarial (Codex, 2026-09-14) — NO-SHIP, remediado

- **Objeto revisado:** el diseño rev. 1, commit `0dd1017` (copia `git archive`, sin `.git`)
- **Ronda:** 1 de 2 — sobre el diseño; la 2 irá sobre el diff
- **Revisor:** Codex CLI `0.153.4`, `model_reasoning_effort=high`
- **Informe recibido:** `docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-r1-adversarial-review.md` §1
- **Hallazgos:** 8 (5 `ALTO`, 3 `MEDIO`) — **8 confirmados, 0 refutados**
- **Remediado en:** esta rev. 2

| | Hallazgo | Adjudicación |
|---|---|---|
| **H-01** | `ALTO` — NIF presente pero no canonizable cae a la política de email en silencio | **CONFIRMADO**, con sonda: `" -- "` vinculó A y le escribió el CP de B. §1 define los **tres** estados |
| **H-02** | `ALTO` — «difiere» no define la comparación; comparar textos duplica una ficha legítima | **CONFIRMADO.** La igualdad es canónica, simétrica y solo entre utilizables (§1) |
| **H-03** | `ALTO` — el remedio **crea** el estado que el código bloquea después; y con el orden invertido, distinto resultado | **CONFIRMADO, y es el más grave.** La frontera: un criterio fuerte unívoco no puede quedar tapado por la multiplicidad de uno débil. Obliga a **reordenar** la función (§2.1) |
| **H-04** | `ALTO` — devolver la verificación no recupera una creación parcial: N huérfana, M creada | **CONFIRMADO.** Recibo con id y paso alcanzado, tres estados terminales, reintento ciego prohibido (§4.2) |
| **H-05** | `MEDIO` — el rol obligatorio no tiene proveedor | **CONFIRMADO**, y coincide con lo que encontré antes del informe. Él aporta lo que yo no vi: **quien opera no es quien firma**. Campo `firmante:` explícito (§4.3) |
| **H-06** | `ALTO` — **falta el paso 3**: prometí seis y la tabla tenía cinco | **CONFIRMADO, y es un fallo de lectura mío** sobre la receta que yo mismo cité. `resolver_destino` y el contraste antes del POST (§4.1) |
| **H-07** | `MEDIO` — la duración se atribuye a un artefacto y una ventana que no son | **CONFIRMADO.** Yo había visto el nombre del fichero; él añade que **el evento no lleva las fechas** y que la ventana no es la actividad facturable (§4.4) |
| **H-08** | `MEDIO` — la compatibilidad YAML no define vacío ni elementos inválidos | **CONFIRMADO**, con sondas: `null`, `[]` y `[no-dict]` dan todos `None` hoy. Tabla del §3 |

**Lo que el revisor intentó refutar y no pudo** —y por tanto se conserva sin cambios—: la política
de no elegir tarifa por defecto, el guard de consulta fallida y su precedencia, la invariancia
ante permutar resultados múltiples, y fallar cerrado ante una ficha sin NIF.

**Y una errata que detectó sin elevarla a hallazgo:** la rev. 1 invertía verbalmente clave/id al
describir `cliente_propio`. Corregida: `[APER-63]` dice que lleva **la clave** (`EV_MMC_SPAIN`),
y el id `"2"` aborta — que es el comportamiento correcto.

## 7. Adjudicación de la R2 (Codex + revisor de skill, 2026-09-14) — NO-SHIP los dos, remediado

- **Objeto revisado:** el diff `530d033..8aed442`
- **Ronda:** 2 de 2 del presupuesto autorizado. **Nikolai autorizó una R3 tras leer esto.**
- **Revisores:** **dos, en paralelo e independientes** — Codex CLI `0.153.4` (acta
  `…-r2-adversarial-review.md`, **11 hallazgos**, 8 `ALTO`, uno preexistente) y un subagente
  despachado con `superpowers:requesting-code-review` (**13 hallazgos**, 1 crítico).
- **Coinciden en cinco**, y cada uno vio lo que el otro no. **Ninguno refutado.**
- **Remediado en:** `tests/test_sudespacho_actuaciones_r2.py` (18 casos) y el diff que los pasa.

**La frontera, y es una sola para los dos informes:** *cada helper distingue estados que su
único llamador colapsa.* Los helpers se escribieron con cuidado —cuatro salidas en el paso 1,
firmante frente a operador, validación frente a fallo de red, un payload validado— y
`alta_actuacion` los aplanaba. Remediar caso a caso habría dejado el siguiente; por eso el
remedio reescribe el orquestador y no los parches.

> **Cuántos hallazgos son, dicho con precisión** (corregido tras la R3, que lo reclamó). Los dos
> revisores devolvieron **11 y 13**, con **cinco coincidentes**: **19 hallazgos distintos**, que
> se agrupan en las **13 categorías** de la tabla de abajo. La rev. 2 de este documento decía
> «quince» en prosa sobre una tabla de trece y sin mapeo que permitiera reconstruir el número —
> o sea, una cifra que ningún lector podía comprobar. El agrupamiento es la unidad útil aquí
> porque el remedio es por frontera; el recuento por informe vive en cada acta.

| | Hallazgo | Adjudicación |
|---|---|---|
| **Parseo** | `CRÍTICO` — `_items` hacía `resp.json()` fuera del `try`: un `200` ilegible atravesaba `alta_actuacion` y el llamador recibía una excepción **en vez del recibo con el `act_id`**, tras escribir en el CRM | **CONFIRMADO, y es el mismo defecto que el módulo hermano documenta como ya pagado.** `_items` levanta `CuerpoIlegible`, y los tres consumidores lo tratan |
| **Paginación** | `ALTO` — «todas descartadas» se concluía sobre `itemsPerPage=5`: con seis fichas en el buzón, la decisión de **crear** depende del tamaño de página | **CONFIRMADO.** Ver §7.1 |
| **Validador** | `ALTO` — se escriben N contrarios y `crm_ficha_validacion` sigue anclando **el primero** | **CONFIRMADO.** Es «antes de cambiar un campo, enumera quién lo LEE»: enumeré el CLI y no el validador |
| **Recibo incierto** | `ALTO` — reanudarlo creaba otra actuación: su `act_id` es `None` por definición | **CONFIRMADO**, y lo había encontrado yo antes del informe. La prohibición vivía en el docstring y no en el código |
| **Recibo sin destino** | `ALTO` — el recibo no acreditaba a qué expediente pertenece su actuación | **CONFIRMADO.** `Recibo` lleva `elemento`/`exp_id` y reanudar contra otro destino levanta |
| **Paso 1 con otro asunto** | `ALTO` — se aprendía del asunto **crudo** y se escribía el **canónico**: con `like`, se aprende la plantilla de la otra tarifa | **CONFIRMADO.** El docstring del paso 1 lo advertía y su único llamador lo incumplía |
| **Cuatro salidas** | `ALTO` — `alta_actuacion` leía `pre.valor` y nunca `pre.estado`: «no pude mirar» era indistinguible de «no aplica» | **CONFIRMADO.** La pieza construida que nadie encadena |
| **Validación disfrazada** | `ALTO` — un firmante vacío salía como «puede haberse creado una actuación: concilia a mano» **sin tocar el CRM** | **CONFIRMADO.** La validación va fuera del `try` del POST |
| **Destino** | `ALTO` — se leía `filas[0]` sin comprobar su id, y la regex de W-code **truncaba** (`W-ABCDEF1` = `W-ABCDEF2`) | **CONFIRMADO.** Se exige la fila pedida y se usa `wcode_match` del módulo hermano — que el plan ya mandaba usar |
| **`extra`** | `ALTO` — sobrescribía `Subject`, `profesional_asignado` e `id_predefinido` **después** de validarlos | **CONFIRMADO.** La validación se aplica al objeto final que cruza la frontera de escritura |
| **Zona horaria** | `MEDIO` — dos fechas sin zona restaban y devolvían un número | **CONFIRMADO.** El §4.4 ya lo exigía |
| **Prefijo con espacios** | `MEDIO` — `ABOGADO  -  X` no se detectaba y producía un asunto **doble** | **CONFIRMADO.** La detección tolera caja y espacios, y normaliza a mayúsculas |
| **Test que llama al CRM** | `MEDIO`, **preexistente** — `test_ensure_contrario_vinculado_existente` intenta leer del tenant y pasa porque `_completar_contrario_existente` absorbe la excepción | **CONFIRMADO y NO remediado aquí**: es anterior al diff y tocarlo mezclaría dos cosas. Ver §7.2 |

### 7.1 La paginación, que es el que más enseña de los quince

`_resolver_por_buzon_compartido` concluye «todas las fichas descartadas → se crea», y decidía
sobre las **cinco primeras** (`itemsPerPage` por defecto de `_buscar_registros`). Con seis fichas
en un buzón familiar, **la misma entrada crea o para según cuántas filas devuelva el servidor**.

Antes del diff esto era inocuo —con dos o más fichas se paraba igual por ambigüedad—; el remedio
de `[APER-71]` lo volvió peligroso, porque ahora esa rama **autoriza una creación**. Es la misma
lección que la R1: *un remedio cambia qué estados son alcanzables, y hay que volver a mirar los
que antes no importaban*.

**Remedio:** la consulta por email pide explícitamente más filas de las que un buzón real puede
tener y **detecta el truncamiento**; si la lista puede estar incompleta, se para. No se puede
concluir «todas» sobre una página.

### 7.2 Lo que NO se remedia aquí, y por qué

El test preexistente que intenta alcanzar el CRM (`tests/test_sudespacho_relations.py`) es
anterior a este diff y su remedio toca el aislamiento de la suite, no P6. Se **declara** aquí
—la suite no está tan aislada como decimos— y se ficha aparte. Mezclarlo con esta pieza haría
irrevisable el diff, que es justo lo que el techo de rondas intenta evitar.

## 8. Adjudicación de la R3 (Codex, 2026-09-14) — NO-SHIP, remediado

- **Objeto revisado:** el diff remediado `8aed442..53cc575`, commit `53cc575`
- **Ronda:** 3
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-09-14-p6-ficha-crm-y-actuaciones-r3-adversarial-review.md`
- **Hallazgos:** 9 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento y el diff que la acompaña

**Ronda excepcional, autorizada expresamente por Nikolai** tras leer la R2, y pedida por una
razón concreta: los remedios de hallazgos ALTO son donde aparece el defecto siguiente. Acertó.
El objeto de la ronda no era la pieza sino **la remediación**, y su pregunta central era si
cada remedio cerraba la frontera o solo el caso que el informe describía.

**Nueve de nueve confirmados, cero refutados.** El revisor declaró además que **no pide una
cuarta ronda**, y Nikolai decidió cerrar sin ella: el criterio «hasta que una ronda vuelva
limpia» no converge —lo midieron las cuatro del mutex— y el coste de la ronda es cierto
mientras el del defecto no lo es.

| Hallazgo | Sev. | Coste | Adjudicación |
|---|---|---|---|
| **H-01** el parseo pierde el recibo tras escribir | `CRÍTICO` | acotado | **CONFIRMADO**, reproducido: `{"items": 1}` → `TypeError` fuera del `try`; `values:[null]` → `AttributeError` |
| **H-02** la identidad del recibo es opcional | `ALTO` | acotado | **CONFIRMADO**, reproducido: con `elemento=""` **escribe** el vínculo de una actuación ajena |
| **H-03** `sin_filas` y `no_aplica` se consumen igual | `ALTO` | acotado | **CONFIRMADO**: el orquestador solo distinguía `sin_comprobar`, y el motivo de `no_aplica` afirmaba lo no visto |
| **H-04** se aprende la plantilla de una variante | `ALTO` | acotado | **CONFIRMADO**: filtro `like` y ninguna comprobación del `Subject` de la fila; el orden decidía el id |
| **H-05** la exhaustividad se descarta | `ALTO` | estructural | **CONFIRMADO**: `_buscar_registros` tiraba `totalItems` y `Consulta` no tenía dónde guardarlo |
| **H-06** una `incompleta` que nadie puede reanudar | `MEDIO` | acotado | **CONFIRMADO**, reproducido: cero escrituras y «concilia a mano» |
| **H-07** validar se clasifica como escribir | `MEDIO` | acotado | **CONFIRMADO**, reproducido: cero POST y «puede haberse creado una actuación» |
| **H-08** M29 muere por `NameError` | `MEDIO` | acotado | **CONFIRMADO**: `_RE_WCODE` no existe ni se importa |
| **H-09** el test preexistente llama al tenant | `MEDIO` | acotado | **CONFIRMADO**. Declarado en la rev. 2 como no remediado; **se remedia aquí** por decisión de Nikolai |

### 8.1 Los nueve son ejemplos de SIETE fronteras, y así se remedian

Remediar nueve sitios habría dejado el décimo — es literalmente lo que pasó entre la R2 y esta
ronda. El remedio va por frontera:

| Frontera | Cierra | Dónde |
|---|---|---|
| **A.** Decodificar no es interpretar; y **tras escribir, siempre hay recibo** | H-01 | `_items`, `_values`, y el paso 6 envuelto en `alta_actuacion` |
| **B.** Un contexto ausente no desactiva la comprobación que ese contexto permite | H-02 | `_act_id_reanudable`, con el contrato del recibo entero en un sitio |
| **C.** Estados de conocimiento distintos no se colapsan, y un motivo no afirma lo no visto | H-03 | quinta salida `no_interpretable`; el recibo final conserva cuál fue |
| **D.** La evidencia recibida debe ser de la operación que se ejecuta | H-04 | solo se aprende de la fila cuyo `Subject` es el pedido |
| **E.** Pedido, recibido y total no son la misma información | H-05 | `Consulta.total_declarado` + `truncada`, consumido al decidir |
| **F.** «No lo intenté» es un estado, no una variante de «lo intenté y no sé» | H-06 | estado `no_intentada`, reanudable porque nada se escribió |
| **G.** Validar y transmitir son fases distintas | H-07, H-09 | `_validar_extra` delante del `try`; el test recupera su doble |
| **H.** El arnés distingue morir por la propiedad de morir por estar roto | H-08 | `_ROTO` en `_mutantes_p6`, con control positivo |

### 8.2 Los tres patrones que esta ronda destapó en mí, no en el código

**Escribí comentarios que afirman lo que el código no hace.** El docstring de `_items` decía
«El parseo entero va cubierto, y esto ya se pagó una vez en el módulo hermano» mientras el
`try` seguía envolviendo solo `resp.json()`. El del paso 1 exigía el asunto **literal** «porque
una aproximación devolvería el de otra plantilla», y filtraba con `like` sin comprobar la fila.
Dos veces en el mismo diff, y las dos en el sitio donde un comentario cierra la discusión. Los
dos docstrings quedan corregidos **diciendo que fueron falsos**, no reescritos en silencio.

**Remedié el ejemplo y no la frontera, otra vez.** La R2 sacó la validación del firmante fuera
del `try` y dejó dentro la de `extra`: misma frontera, caso siguiente. Y la guarda de identidad
del recibo existía pero la desactivaba el valor por defecto del campo que la condicionaba.

**Y por tercera vez en esta pieza, el remedio creó el estado que el código bloquea después**
(H-06). El mandato de la ronda lo señalaba por nombre —«¿algún remedio abre un estado nuevo? es
el modo de fallo de esta pieza, ya observado dos veces»—, lo busqué, y lo había introducido.

### 8.3 Lo que el 37/37 valía de verdad

El arnés declaraba **37 mutantes, 37 muertos**. Eran **36 muertes semánticas y una coartada**:
M29 sustituía `wcode_match` por una llamada a `_RE_WCODE`, regex que la R2 había retirado del
módulo, así que moría con `NameError` — el programa mutado no funcionaba, y eso no acredita que
el test detecte nada. Sobre esa muerte falsa se había retirado M16 «porque M29 lo absorbe»: una
afirmación de cobertura apoyada en un mutante que no cubría.

Lo que el revisor comprobó y **rebaja el daño**: el test **sí** caza la mutación de M16 cuando
se le da ejecutable. Lo roto era el mutante, no la cobertura. Aun así el número que di era
falso, y se dio por medido.

Remedio: M29 reapuntado con una sustitución ejecutable, **M16 restaurado**, y el arnés aprende a
distinguir las dos muertes (`_ROTO`). El detector tiene **control positivo**: con un mutante
roto a propósito grita `[ARNES ROTO] … murió por NameError`. Sin esa comprobación sería una
guarda inerte, que es el defecto que viene a cerrar.

### 8.4 Dos huecos de contabilidad que el revisor reclamó, y tenía razón en los dos

**El acta del segundo revisor de la R2 no existía.** El §7 la citaba —`…-r2b-adversarial-review.md`—
y el revisor de la R3 se negó, correctamente, a atribuir a ese revisor hallazgos que no podía
leer. Ya está escrita. Su informe volvió con el `outputFile` **vacío** y se recuperó de la
notificación de la tarea en el transcript; el acta lo dice, porque la procedencia de un original
archivado es parte de lo que el acta acredita.

**Y el número de hallazgos de la R2 no era reconstruible.** La prosa decía «quince» sobre una
tabla de trece filas y sin mapeo. Corregido arriba con el reparto real: **11 + 13 con cinco
coincidentes = 19 distintos en 13 categorías**. Una cifra que ningún lector puede comprobar es,
a efectos de este archivo, una cifra inventada.

### 8.5 Lo que esta ronda NO cubre, dicho por el revisor

Suite completa y sus dos semillas, aceptación real de los payloads por el tenant, límites
efectivos de paginación del servidor, idempotencia del POST y del vínculo, concurrencia, y
constructores externos al árbol. **Los dobles acreditan las decisiones ante las respuestas
descritas, no la frecuencia de esas respuestas en producción.**

De ahí sale lo que sustituye a la cuarta ronda, y es mejor evidencia que otra lectura: **correr
la pieza entera contra el CRM real** sobre `extrajudiciales/636`, leer por API cómo quedó, y
medir si se puede deshacer. Queda en §9.

## 9. La corrida EN VIVO, que es lo que sustituye a la cuarta ronda

**Decidida por Nikolai el 2026-09-14**, y es mejor evidencia que otra lectura. El revisor de la
R3 declaró SIN VERIFICAR, entre otras cosas, «la aceptación actual de los payloads por el
tenant». Eso no lo cubre nadie leyendo: **un doble acepta cualquier cosa que se le mande**, así
que acredita qué decide el código ante una respuesta y nunca que el payload sea aceptable.

Objeto: expediente **`extrajudiciales/636`**, que el despacho tiene como desechable (su
`Referencia_Cliente` era literalmente `PRUEBA - BORRAR`).

**Preparación, y qué se tocó.** El paso 3 acredita el destino con `wcode_match`, que devuelve
`False` si a cualquiera de los dos lados le falta el W-code; el 636 no tenía. Se le puso uno
**sintético** por API conservando la etiqueta original —`PRUEBA - BORRAR (W-TEST636)`— y se
verificó por lectura, no por status. Queda dicho para poder deshacerlo.

### 9.1 Tres defectos en una sola ejecución, ninguno visible para un doble

**Con 5.612 tests verdes, tres rondas adversariales y 39 mutantes muertos**, la primera corrida
real murió en el paso 4:

```
HTTP 404 — The value: <Normal> sent for the property: Prioridad is incorrect.
```

| Defecto | Qué pasaba | Por qué ningún doble lo veía |
|---|---|---|
| `Prioridad: "Normal"` | valor **inexistente**: el enum es `Alta · Media · Baja` | el doble acepta el payload que se le dé |
| `fecha_alta` vacía | las 40 actuaciones reales muestreadas la traen | el doble no valida campos obligatorios de negocio |
| `precio_hora = 0,00` | el asunto decía `SENIOR - …`, que **ES** la tarifa de 103 €/h | dos datos sobre lo mismo, y solo uno se factura |

Los tres estaban **contradiciendo documentación propia**: el enum consta en
`INTEGRACION_SUDESPACHO.md` §15.6 y la tarifa en `[APER-72]`, medida sobre 20 instancias reales
y citada en un comentario del propio módulo. **El conocimiento estaba escrito y el código no lo
aplicaba** — el mismo patrón que la R3 encontró dos veces en los docstrings.

El más caro es el tercero, y conviene nombrarlo: una actuación con `SENIOR` en el asunto y
`0,00` en el precio **parece completa en el listado y factura cero**. El remedio es estructural,
no un valor: prefijo y precio salen ahora de la **misma fila** (`_FIRMANTES`), así que no pueden
volver a decir cosas distintas.

Y el `Prioridad` inválido produjo además un recibo `incierta` —«puede haberse creado una
actuación, concilia a mano»— por algo que el servidor había rechazado. Es la **frontera G otra
vez**, un caso más allá: los enums se validan ahora antes del POST, como `extra`.

### 9.2 Lo que la corrida acreditó, ya remediada

```
1. GET  element_registries/extrajudiciales      200   paso 3, destino acreditado
2. GET  element_registries/actuaciones          200   paso 1, id_predefinido
3. POST element_register/actuaciones            201   paso 4  → actuación 21395
4. POST relation_element/extrajudiciales/636    201   paso 5
5. GET  element_registries/actuaciones          200   paso 6, verificada del lado del expediente
6. POST element_register/calendario             201   paso 7  → evento 20235
7. POST relation_element/actuaciones/21395      201   paso 7, evento colgado de la actuación
```

Recibo: **`verificada`, paso 7**, con `fecha_alta 2026-09-14`, `precio_hora 103.00`,
`Prioridad Alta`, `fecha_vencimiento 2026-10-01 09:00:00` y el evento agendado. **El recibo
conserva el estado de conocimiento del paso 1** —el remedio de H-03— y se lee en vivo:
`id_predefinido [sin_filas]: ninguna de las 0 fila(s) … tiene el asunto exacto`.

**Y el paso 1 se probó contra los datos reales, que es donde H-04 se juega.** Pidiendo
`SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD`, el filtro `like` devolvió **10 filas de las que
solo 3 eran el asunto exacto** —el resto, variantes como `… - DESCARTADO` o `… - INICIAL
W-02JSVZ`—. Antes del remedio se aprendía el id de la primera fila con valor; ahora solo de las
exactas, y el motivo lo dice.

### 9.3 El paso 7: una fecha límite que no avisa no es una fecha límite

Añadido en esta corrida a petición de Nikolai. `fecha_vencimiento` es un campo del elemento que
**nadie mira**; lo que avisa es el evento del calendario. `calendario` resultó ser un elemento
normal cuyo *parent* puede ser `actuaciones` (`CRM_SUDESPACHO_ATLAS.md`), con enum `Tipo` que
incluye `Vencimiento`: se crea y se cuelga con la misma receta que todo lo demás, **sin tocar el
host `api-calendar-commons-pro`**, que sirve notificaciones y salas y no el alta del evento.

El fallo al agendar **no se lleva el recibo**: la actuación ya existe, está vinculada y
verificada, y repetir el alta por un evento que no se pudo poner crearía una segunda. Es la
invariante del paso 6 aplicada al 7.

### 9.4 Lo que la corrida midió y conviene no olvidar

- **`totalItems` existe y llega como FLOAT** (`20834.0`). La guarda de H-05 puede dispararse:
  no es decorado. Una comprobación por `isinstance(x, int)` la habría dejado inerte.
- **El truncamiento de H-05 es real y trivial de reproducir**: pidiendo `itemsPerPage=1` el
  servidor devuelve 1 fila y declara 20.834.
- **`duracion` no hace viaje de ida y vuelta**: se manda `"00:01:00"` y se lee `'60'`. El CRM
  guarda segundos.
- **Filtrar `actuaciones` por `id` con `equal` devuelve vacío** (no error). Para leer una
  instancia, `like` sobre `Subject`, como ya avisaba el §15.6.
- **`fecha_alta` y `precio_hora` se escriben por API**, verificado con un `PUT` sobre la 21393.
  El `§15.4` decía «la tarifa es solo por UI» y es verdad **a medias**: lo que no se resuelve
  por API es la *tarifa confidencial del usuario*, no el campo.

### 9.5 Lo que queda abierto

- **Reversibilidad de `actuaciones`**: el §17.5 documenta `DELETE` sobre `relation_element` y
  `element_register`, medido en `gdocu` y `colaboradores`, **nunca en `actuaciones`**. Las de
  prueba creadas aquí (21393, 21395) y el evento 20235 siguen vivos, igual que el W-code
  sintético del 636.
- **Las dos casillas de la UI** —«Crear documento a través de plantilla» y «Enviar por email»—
  **no son campos del elemento**: los 37 de `actuaciones` solo tienen cinco `CheckBox` y ninguna
  es esa. Son los flujos de §10.11 (familia `rtf`) y §10.9 (`nest-mail`), documentados y
  confirmados, pero **piezas aparte**. Y la segunda haría que el código **envíe correo en nombre
  del despacho**: no se cablea sin decidir antes cuándo y a quién.
