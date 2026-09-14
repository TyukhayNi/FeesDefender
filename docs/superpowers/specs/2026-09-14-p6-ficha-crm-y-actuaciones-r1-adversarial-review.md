---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md
objeto_rev: "1"
commit: 0dd1017
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k9r4
sha256_informe: c3486c82431891e8241f7bb35e72a8179e889db3b13692898b4b78e38c8e7918
adjudicado_en: docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md §6
---

# Acta — R1 adversarial sobre el DISEÑO de P6 (ficha CRM y actuaciones)

Objeto: el **diseño rev. 1**, en el commit `0dd1017`. Ronda **1 de 2**: esta sobre el diseño, la
siguiente sobre el diff. El presupuesto lo fija el radio de daño de la pieza 2, que decide la
identidad de una parte y hoy contamina la ficha de otro cliente.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, `model_reasoning_effort=high` |
| Objeto | `C:/t/p6-obj-021040/head` — 1330 ficheros |
| `sha256` del diseño, al abrir y al cerrar | `30583d965d15273c279b6576fa0fe9cd96e0ff2d2afe325629709c857c6036fb`, idénticos |
| `sha256` del informe | `c3486c82431891e8241f7bb35e72a8179e889db3b13692898b4b78e38c8e7918` — **fichero crudo y bloque canonicalizado coinciden**, y coinciden con el que el revisor devolvió por separado |
| Sondas | **28 ejecutadas, 28 pasadas**; el verde reproduce los defectos descritos, no valida el diseño |
| Veredicto | **NO-SHIP** |
| Hallazgos | 8 (5 `ALTO`, 3 `MEDIO`) — **8 confirmados, 0 refutados** |

**Por qué esta ronda valió lo que cuesta: ocho defectos cazados antes de escribir una línea de
código**, y tres de ellos estructurales. El que más enseña es H-03: el remedio que la rev. 1
proponía para dejar de fundir dos personas **creaba el estado que el propio código bloquea
después** —crear B hace que el buzón devuelva dos fichas, y la guarda de ambigüedad se evalúa
antes del cruce con el NIF—, así que la primera corrida habría funcionado y la segunda se habría
bloqueado para siempre. Un defecto que no se ve leyendo la función una vez, sino preguntándose
qué estado deja la solución.

**Y H-06 es un fallo de lectura del autor sobre la fuente que él mismo citó:** el spec prometía
encapsular «los seis pasos» de la receta y su tabla asignaba cinco. El que faltaba es el que
contrasta que el expediente de destino es el que crees — y la receta documenta que el
extrajudicial 464 y el judicial 464 son casos distintos, y que `_link_rest` devuelve 201 sobre un
expediente inexistente.

**Dos hallazgos coinciden con los que el autor encontró por su cuenta mientras la ronda corría**
(el nombre del fichero de estado y la falta de proveedor del rol), y en los dos el revisor llegó
más lejos: que el evento de cierre no lleva las fechas y que la ventana medida no es la actividad
facturable; y que *quien opera no es quien firma*, que es lo que vuelve el dato imposible de
inferir.

## 0. Mandato, literal

<!-- mandato-literal:inicio:k9r4 -->
# Mandato — revisión adversarial R1 del DISEÑO de P6 (ficha CRM y actuaciones)

Eres el revisor adversarial. Tu trabajo es **encontrar defectos en el diseño antes de que se
escriba una línea de código**, no aprobarlo. El autor (Claude) adjudicará cada hallazgo contra
la fuente.

**Esta es la ronda 1 de 2.** La 2 será sobre el diff. El presupuesto es de dos porque una de
las tres piezas decide **la identidad de una parte** y hoy **escribe encima de la ficha de otro
cliente**. Aprovecha que aquí todavía no hay código: un defecto de diseño cazado ahora vale
mucho más que el mismo defecto cazado en el diff.

## 0. Higiene del workdir

Tu directorio de trabajo (`-C`) contiene **solo este `MANDATO.md`** y lo que tú escribas. Si
encuentras cualquier otro fichero, **no lo leas** y decláralo en la primera línea del informe.

## 1. El objeto

Una copia congelada del árbol, en ruta absoluta (NO está dentro de tu workdir):

- `C:/t/p6-obj-021040/head/` — el repo en el commit `0dd1017`.

**El documento a revisar:**
`C:/t/p6-obj-021040/head/docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md`

**SOLO LECTURA sobre esa ruta.** Al abrir y al cerrar, reporta el `sha256` de ese fichero para
acreditar que no lo mutaste. No hay `.git`: no puedes acreditar genealogía, solo contenido.

**El código que el diseño va a cambiar está en la misma copia y DEBES leerlo** — el diseño se
juzga contra el código real, no contra su descripción:

- `core/sudespacho_relations.py` — `resolver_parte`, `_buscar_registros`, `Consulta`,
  `ResolucionParte`, `_exigir_identidad_cierta`, `ensure_contrario_vinculado`,
  `_completar_contrario_existente`, `_link_rest`, `get_relaciones`
- `core/crm_ficha.py` — cómo lee `contrario`
- `docs/INTEGRACION_SUDESPACHO.md` §15.2, §15.3, §15.4, §15.6 — la receta de la actuación
- `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` — `[APER-63]`, `[APER-71]`, `[APER-72]`, `[APER-14]`,
  `[APER-24]`, `[APER-26]`

## 2. Puedes ejecutar, y deberías

Python de sistema con `pytest`, `httpx`, `yaml`, `typer`, `filelock`, `dotenv`:

```
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

Copia lo que necesites a tu workdir y ejecútalo allí. **`--basetemp` relativo dentro de tu
workdir** (tu sandbox no puede crear `C:\t\...`). No hay credenciales del CRM y **no debe
haberlas**: no intentes llamar al CRM real. Lo que sí puedes es cargar los módulos, leer AST,
y **construir sondas** que ejerciten `resolver_parte` con `_buscar_registros` sustituido, para
comprobar si la tabla de decisión del diseño cubre lo que dice cubrir.

**Un revisor que no corre no refuta: deja SIN VERIFICAR.**

## 3. Qué propone el diseño, en corto

1. **`core/sudespacho_actuaciones.py` nuevo** que encapsula la receta de seis pasos del §15.6,
   con `asunto_canonico(rol_firmante)` que **exige** el rol (el prefijo del `Subject` ES la
   tarifa: 103 €/h vs 77 €/h) y `duracion_desde_estado` derivada de `iniciada`/`terminada`.
2. **`resolver_parte` deja de resolver por email cuando hay un NIF que lo desmiente.** Tabla de
   tres casos en el §2 del spec.
3. **`crm_ficha` acepta `contrario:` como mapping o como lista.**

## 4. Dónde mirar con más ganas

1. **La tabla de decisión de la pieza 2 (§2 del spec). Es lo más importante de esta ronda.**
   ¿Es **exhaustiva** sobre los estados posibles, o solo disjunta sobre los que enumera? Piensa
   en: NIF aportado pero **no canonizable**; email aportado y NIF vacío; **varias** fichas por
   email; la consulta por email que falla (`ok=False`) mientras la de NIF va bien; una ficha X
   cuyo NIF esté escrito con otra forma (con guion, en minúsculas, con espacios); dos fichas por
   email con NIFs distintos entre sí. **¿Qué estado queda sin caso?**
2. **¿El remedio de la pieza 2 abre un agujero nuevo?** Pasar de «resuelta por email» a «crear
   ficha nueva» significa **crear**. ¿Puede eso duplicar una ficha legítima? ¿En qué escenario?
   Compara con el contrato que `_exigir_identidad_cierta` ya declara (fallar cerrado) y di si el
   diseño lo respeta o lo contradice.
3. **`asunto_canonico` exige el rol y no tiene defecto.** ¿De dónde sale ese rol en el flujo
   real? Busca en el árbol quién llamaría a esto y si ese dato existe ahí. Si no existe, el
   diseño está pidiendo algo que el llamador no puede dar, y eso se descubre ahora o se paga
   construyendo.
4. **El paso 6 (verificar por resultado).** El diseño dice que `alta_actuacion` «devuelve el
   resultado de la verificación, no el 201 del POST». ¿Es suficiente? ¿Qué pasa si el paso 5
   falla pero el 4 ya creó la actuación — queda huérfana y alguien la reintenta? ¿El diseño dice
   algo de la **idempotencia** del reintento? (`_link_rest` ya documenta ser idempotente; el
   POST del paso 4, ¿lo es?)
5. **`duracion_desde_estado`.** Busca `estado.json` en el árbol y comprueba que los campos
   `iniciada`/`terminada` existen y con qué forma. El diseño lo afirma citando el handoff. ¿Es
   cierto contra el código?
6. **La pieza 3 y la compatibilidad.** ¿Aceptar mapping **o** lista introduce alguna ambigüedad?
   ¿Qué pasa con una lista vacía, con `contrario: null`, con una lista de un elemento que no es
   mapping? ¿Y el orden importa para la vinculación?
7. **Lo que el diseño declara que NO prueba** (§4): ¿está bien delimitado, o hay algo que sí se
   podría probar sin el CRM y que se está declarando fuera de alcance con demasiada facilidad?
8. **Las dos premisas que el §0 dice haber verificado.** Puedes comprobar la primera contra el
   árbol (el §15.6 corregido). La segunda (que no hay sesión hermana) **no es verificable desde
   aquí**: dilo como SIN VERIFICAR en vez de aceptarla.

## 5. Formato del informe

Escribe **`INFORME.md`** en tu workdir:

```
# Informe R1 — diseño de P6 (commit 0dd1017)

## Higiene y no-mutación
## Qué pude ejecutar y qué no
## Hallazgos
Por cada uno: **ID**, **severidad** (CRÍTICO/ALTO/MEDIO/BAJO), dónde (fichero:línea o §),
qué está mal, cómo se manifiesta con un caso concreto, cómo lo comprobaste, y **de qué
frontera es un ejemplo**.
## Lo que revisé y NO encontré defectuoso
## VEREDICTO
```

**La última línea debe ser el veredicto, exactamente una de estas tres palabras y nada más:**

```
SHIP
SHIP-CON-CAMBIOS
NO-SHIP
```

## 6. Recordatorios

- Es un **diseño**: los defectos que valen son de contrato, de exhaustividad y de frontera, no
  de estilo ni de nombres.
- Ante cada hallazgo, escribe **de qué frontera es un ejemplo**. El autor remedia la frontera.
- No propongas rediseñar el alcance: está decidido (las tres piezas, en una rama, dos rondas).
- Si algo te parece correcto pero no puedes probarlo, **SIN VERIFICAR**. Nunca «refutado».
<!-- mandato-literal:fin:k9r4 -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k9r4 -->
Higiene: al abrir el workdir encontré `_stdout.log` además de `MANDATO.md`; no leí `_stdout.log` ni utilicé su contenido.

# Informe R1 — diseño de P6 (commit 0dd1017)

## Higiene y no-mutación

Objeto leído: `C:/t/p6-obj-021040/head/docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md`. En este informe, **spec** designa ese fichero; las demás rutas de fuente son relativas a `C:/t/p6-obj-021040/head/`.

SHA-256 del diseño al abrir:

`30583d965d15273c279b6576fa0fe9cd96e0ff2d2afe325629709c857c6036fb`

SHA-256 del diseño al cerrar la inspección:

`30583d965d15273c279b6576fa0fe9cd96e0ff2d2afe325629709c857c6036fb`

Coinciden. No escribí en el árbol congelado, no ejecuté código desde él y no usé git. No hay `.git`: **SIN VERIFICAR la genealogía y pertenencia al commit 0dd1017**; el identificador procede del mandato. El hash acredita contenido, no genealogía ni por sí solo la integridad de todo el árbol.

Todo lo producido está en `C:/t/p6-rev-r1-021040/`. Copié cinco ficheros de código a `fuentes/`; `fuentes_sha256.json` registra sus hashes. No busqué ni cargué credenciales. No llamé al CRM, a Drive, a gestores de sesiones ni a servicios externos. No hubo delegación a agentes ni a `agy`.

## Qué pude ejecutar y qué no

**Ejecutado: 28 sondas, 28 pasadas, 0 fallos**, última corrida en 5,45 s. El verde significa que se reprodujeron los resultados descritos, incluidos defectos; no que el diseño esté validado.

Reproducción desde este workdir, usando las copias ya depositadas:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
& 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe' -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_final --junitxml sondas_junit_final.xml test_sondas_r1.py
```

Evidencia: `test_sondas_r1.py`, `resultados_sondas.json`, `sondas_junit_final.xml` y `fuentes_sha256.json`. `preparar_sondas.py` documenta la copia inicial. Los temporales son relativos al workdir. `rg` no está disponible; usé búsquedas de PowerShell.

Ejecuté cuerpos originales extraídos por AST de `resolver_parte`, `Consulta`, `ResolucionParte`, `_buscar_registros`, `_exigir_identidad_cierta`, la cadena `ensure_contrario_vinculado` → `_resolver_o_crear_contrario` → `_completar_contrario_existente`, y el lector YAML. No importé el producto completo ni sus efectos de entorno. Importé íntegramente la copia de `apertura_v1_estado.py` y ejecuté su escritura/lectura en `tmp_path`; extraje y ejecuté `registrar_cierre_v1` con un registrador falso. Las búsquedas y escrituras CRM se sustituyeron por dobles; también bloqueé `socket.connect` y los envíos de clientes httpx. Los datos son sintéticos.

Dos familias están expresamente rotuladas **MODELO**: el reintento de actuaciones y la extensión mínima de la tabla sobre el resolver original para listas con NIF incompleto. Demuestran contraejemplos permitidos por el contrato; **no son el futuro diff ni pruebas del servidor**.

**SIN VERIFICAR:** aceptación actual de payloads por el tenant, normalización real del almacenamiento CRM, idempotencia del POST de creación, concurrencia real y consistencia temporal del servidor. Tampoco ejecuté la suite completa del producto ni un módulo de actuaciones que aún no existe. La ausencia de sesión hermana, PR o rama del §0 es **SIN VERIFICAR**: esta copia no proporciona esos datos.

## Hallazgos

### H-01 — NIF aportado pero sin forma canónica: estado sin decisión segura

**Severidad: ALTO. Coste: acotado.** Dónde: spec §2, líneas 83–94; `core/sudespacho_relations.py:1056`, `:1184`, `:1189`, `:1217` y `:1520`.

La tabla exige «NIF aportado» y después «NIF que contrastar», sin distinguir presencia del texto de existencia de un identificador canónico. `_canonizar_documento` elimina separadores: `" -- . "` se convierte en `""`. No existe una salida definida para este estado. Tampoco la función valida que toda cadena alfanumérica restante sea un documento utilizable: canonicalización no equivale a validación.

**Caso y comprobación:** con ese NIF y un email que devuelve A, el resolver original omite la consulta NIF y devuelve A por email. La sonda de `ensure_contrario_vinculado` con el NIF `" -- "` vinculó A y completó su CP vacío con el CP de B. No modificó su móvil ya poblado. Si el cambio usa `if nif_canon`, esa ruta peligrosa queda fuera del remedio; si usa `if nif`, podría interpretar el texto no comparable como discrepancia y autorizar una creación. Ninguna elección está fijada por la tabla.

**Frontera:** dato presente → evidencia de identidad suficiente. La pérdida de información durante la normalización no puede degradar un documento aportado a «no se aportó» y activar silenciosamente otro criterio.

**Remedio de contrato:** separar ausente, utilizable y no interpretable, tanto en entrada como en la ficha leída; declarar la salida cerrada del último. La política de email sin NIF puede conservarse para el caso realmente ausente. Probar que el no interpretable no llega a completar, crear ni vincular.

### H-02 — «Difiere» no define la comparación que autoriza crear

**Severidad: ALTO. Coste: acotado.** Dónde: spec §2, líneas 87–91; `core/sudespacho_relations.py:1056`, `:1107`, `:1128`, `:1134` y `:1222`.

La tercera fila reconoce las diferencias de canonicalización, pero no exige normalizar **los dos lados antes de elegir fila** ni define el tratamiento de un NIF CRM no interpretable. La primera fila convierte una discrepancia en `ResolucionParte()` vacía: esa salida tiene el significado fuerte «no existe; crear» y el guard la acepta sin restricciones.

**Caso:** la persona ya tiene ficha X con `nif_cif="12.345.678-z"`; se aporta `12345678Z`; la consulta exacta por NIF no encuentra X y la de email sí. Comparar textos elige «difiere → crear» y duplica X. Comparar sus formas canónicas elige «coincide → parar». El spec admite dos implementaciones con efectos opuestos sobre la misma identidad. Las variantes de caja/espacios también deben compararse igual, aunque la fuente documenta que el CRM suele normalizarlas y por ello no suelen llegar a esta rama.

**Comprobación:** cuatro sondas verificaron desigualdad literal e igualdad con la función canónica original. Otra ejecutó `_exigir_identidad_cierta(ResolucionParte(), ...)` sin excepción. `_buscar_registros` devuelve `values[]` sin canonicalizar y la búsqueda aplica `equal` al valor pedido; no realiza un barrido normalizado de todas las fichas. La existencia en el tenant de una ficha concreta almacenada así queda **SIN VERIFICAR**; el contraejemplo es del dominio de entradas admitido, no una medición en vivo.

**Frontera:** representación distinta ≠ identidad distinta; descartar un candidato exige más que una comparación textual. Autorizar creación con evidencia no comparable contradice el contrato de fallar cerrado, aunque devolver vacío sea compatible con el tipo Python.

**Remedio de contrato:** igualdad canónica simétrica y explícita, con formas vacías/no interpretables cerradas. Solo una discrepancia entre identificadores utilizables puede justificar esa fila; preservar los guards de consulta fallida y multiplicidad. Si «coincide» ya pretendía significar eso, debe quedar escrito como condición de la tabla y prueba de aceptación.

### H-03 — El estado legítimo que crea el remedio queda bloqueado en el siguiente uso; la lista incompleta además depende del orden

**Severidad: ALTO. Coste: estructural.** Dónde: spec §2, líneas 85–98, y §3, líneas 106–110; `core/sudespacho_relations.py:1199`; `scripts/crm_ficha.py:156` y `:168`.

La tabla cubre exclusivamente `ids_nif=∅`, `ids_mail={X}`. Crear B para que A y B compartan buzón produce inmediatamente `ids_mail={A,B}`. El resolver actual devuelve `ambiguo` **antes** de examinar la intersección con el NIF, incluso si `ids_nif={B}`. El spec no decide cómo tratar este estado creado por su propia solución.

**Caso y comprobación:** la primera corrida puede crear y vincular A y B. La siguiente, con el mismo YAML, se bloquea al resolver cualquiera de ellos. Si B fue creado pero falló su vinculación, reintentar tampoco permite terminarla por la vía normal. Dos sondas originales, con el orden de resultados invertido, devolvieron `ambiguo=(A,B)` teniendo un único match NIF B. Un tercer deudor C del mismo buzón también queda fuera de la tabla y bloqueado. No propongo ignorar la multiplicidad: el comportamiento actual es seguro, pero contradice la expectativa operativa de varios firmantes y reejecución.

La interacción con el caso «sin NIF sigue por email» es más dañina. **Modelo ejecutado**, aplicando solo la tabla propuesta sobre el comportamiento restante: A no tiene NIF; B sí; ambos comparten email y el CRM empieza vacío. Orden `[A,B]`: crea A y bloquea B porque el NIF de A está vacío. Orden `[B,A]`: crea B y resuelve A a B por email. La auditoría de cardinalidad del CLI puede detectar el colapso al final, pero después de los efectos. No previene completar campos de la ficha equivocada.

**Frontera:** seguridad de una resolución aislada → cierre de la operación bajo repetición y composición en una lista. «Vincular todos» necesita un contrato para el conjunto, no solo iterar una función singular.

**Remedio de contrato:** decidir expresamente los conjuntos múltiples, su cruce con los NIF y el estado parcial/reintentable; mantener el cierre ante incertidumbre. Definir validación del lote antes de escribir para los casos de identidad incompleta/compartida. Probar reejecución, corte tras crear B, tercer firmante y permutaciones de entrada. Esto afecta al contrato conjunto de las piezas 2 y 3; no exige separarlas ni ampliar el alcance.

### H-04 — Devolver la verificación no permite recuperar una creación parcial

**Severidad: ALTO. Coste: estructural.** Dónde: spec §1, líneas 42–45, y §4, línea 125; `docs/INTEGRACION_SUDESPACHO.md:2102`; `core/sudespacho_relations.py:1784`.

`alta_actuacion` no define identidad de operación, recibo de creación ni recuperación. Que el resultado final no sea un falso éxito es necesario, pero un fallo después del POST deja un efecto que el siguiente intento debe reconocer. La idempotencia documentada de `relation_element` solo evita repetir **el mismo vínculo**, no crear otra actuación.

**Caso:** paso 4 crea N; paso 5 falla; el llamador recibe «no verificada» y repite el alta completa. El nuevo POST puede crear M, que sí se vincula, mientras N queda huérfana. Si el fallo fue en la lectura del paso 6, N podría estar ya vinculada y el reintento añadir M al mismo expediente. Un timeout del paso 4 deja incluso incierto el ID creado.

**Comprobación:** inspección de la receta, `_link_rest` y el contrato de retorno; el modelo local de pasos 4–6 terminó con dos actuaciones creadas y solo la segunda vinculada sin declarar ningún falso éxito. La no idempotencia concreta del POST en el tenant es **SIN VERIFICAR**; tampoco hay una garantía documental que permita asumirla. El defecto es no definir qué hacer ante esa incertidumbre.

**Frontera:** éxito observable → recuperación de efectos parciales. Una verificación negativa no equivale a ausencia de escritura.

**Remedio de contrato:** conservar/devolver el `act_id` obtenido y el paso alcanzado, permitir reanudar vínculo/verificación sobre ese ID, y declarar estado incierto y política de conciliación cuando el POST no dé recibo. Prohibir reintento ciego de creación en ese estado. Los fallos en cada paso, respuestas perdidas y dos intentos consecutivos son comprobables sin CRM.

### H-05 — El rol obligatorio no tiene proveedor en el flujo diseñado

**Severidad: MEDIO. Coste: estructural.** Dónde: spec §1, líneas 41 y 47–54; `core/crm_ficha.py:20`; `scripts/crm_ficha.py:59`; `scripts/abrir_caso.py:1335`; `core/config.py:759`.

Exigir el rol y no darle valor por defecto es correcto. Falta el contrato del llamador: dónde obtiene **el firmante de esta actuación**, cómo se convierte en rol y cómo se mantiene coherente con `profesional_asignado`.

**Caso:** Ana tramita una revisión que firma Nikolai. El actor de la UI identifica a quien opera, no al firmante. `FichaCRMInput` no contiene firmante, rol ni profesional; `scripts.crm_ficha.main` recibe únicamente caso, dry-run y confirmación. El `--rol` de `abrir_caso` es una subcarpeta de WhatsApp, no seniority. El manual contiene personas/roles y `ACTORES_DESPACHO` nombres con comentarios, pero ninguno identifica al firmante de esta operación. Usar al operador elegiría una categoría errónea; no aportar nada bloquearía el helper.

**Comprobación:** lectura de esas interfaces y búsqueda en `core/` y `scripts/` de `rol_firmante`, `asunto_canonico`, `firmante` y `profesional_asignado`. La asignación profesional judicial localizada en `sudespacho_create.py:1443` procede de `abogado_principal`, no de un vínculo declarado con este futuro helper. No se ejecutó una integración inexistente.

**Frontera:** parámetro obligatorio → procedencia del dato que lo satisface. Un catálogo de roles no determina quién firma un trabajo concreto.

**Remedio de contrato:** nombrar el llamador y su entrada explícita/autoridad para firmante y profesional, con validación de coherencia. Puede ser una entrada humana expresa; no hace falta inferirla ni automatizar la tarifa. Probar operador distinto del firmante y ausencia del dato.

### H-06 — El paso 3 de la receta carece de responsable y evidencia de identidad del expediente

**Severidad: ALTO. Coste: estructural.** Dónde: spec §1, líneas 35–45; `docs/INTEGRACION_SUDESPACHO.md:2095`; `core/sudespacho_relations.py:1790`.

El texto promete los seis pasos, pero la tabla asigna funciones a 1, 2, 4, 5 y 6. Falta dónde se ejecuta el paso 3: obtener `(elemento,id)` del caso y contrastarlo con una referencia del expediente **antes de escribir**. Pasar `elemento` y `exp_id` a `vincular_actuacion` no acredita por sí solo a qué caso pertenecen.

**Caso:** se confunde el extrajudicial 464 con el judicial 464. La propia receta documenta que este último existe y es otro caso. Crear, vincular y releer contra ese par equivocado puede verificar con éxito una actuación en el expediente ajeno. La verificación del paso 6 no descubre un origen equivocado si usa la misma dirección que la escritura.

**Comprobación:** contraste literal de la tabla con §15.6 paso 3 y con `_link_rest`, que incluso documenta 201 para un expediente inexistente. No reproduje una escritura real ni doy por ejecutado un guard futuro implícito en «1→6».

**Frontera:** identificador técnicamente válido → identidad de negocio del destino. Verificar llegada no verifica intención.

**Remedio de contrato:** asignar a `alta_actuacion` o a una precondición comprobable del llamador la resolución del par y el contraste con el caso esperado, antes del POST. Probar dos elementos con el mismo número y referencia discrepante; en el segundo caso deben producirse cero escrituras.

### H-07 — La duración se atribuye a un artefacto/evento distinto del que escribe el código

**Severidad: MEDIO. Coste: acotado.** Dónde: spec §1, líneas 56–58; `core/apertura_v1_estado.py:20`, `:32`, `:43`; `scripts/abrir_caso.py:889`, `:1556` y `:1581`.

La afirmación «el evento de `estado.json` tiene `iniciada` y `terminada`» mezcla dos contratos. Las fechas sí existen en `00_Input/_apertura_v1.json`, marcador de una ronda V1. El evento `apertura_v1_terminada` del log no lleva ninguna de ellas, ni `ronda_id` ni `duracion_s`. No hay un fichero literal `estado.json` localizado en la copia ni un escritor con ese nombre para este flujo.

**Caso y comprobación:** ejecuté `abrir` y `cerrar` con 10:00:00Z y 10:01:30Z. El JSON real contiene `ronda_id`, `iniciada`, `terminada`, `estado`, `etapas`; su diferencia es 90 segundos. Ejecuté también el registrador de cierre: sus details son `estado`, `parada`, `pendientes`, `etapas`, sin extremos temporales. Un consumidor del evento no puede derivar la duración prometida.

Además, la ventana medida es la ronda Drive → CRM → sala de máquina; no contiene automáticamente el tiempo posterior de revisión de viabilidad. El marcador se reemplaza al abrir otra ronda. El diseño debe precisar qué ronda/actividad está convirtiendo en duración de la actuación para no atribuirle tiempos de otra ejecución.

**Frontera:** dato temporal existente → fuente, ronda y actividad que ese dato mide. Una resta correcta sobre la ventana equivocada sigue dando una duración equivocada.

**Remedio de contrato:** señalar la fuente real y su forma, vincularla a la ronda/actividad pertinente, aceptar las fechas UTC con `Z` y mantener la ausencia como no disponible. Definir también rechazo de fechas inválidas, mezclas sin zona y extremos invertidos. No hace falta instrumentar toda la acción 12 para fijar esta entrada.

### H-08 — La compatibilidad YAML no define lista vacía ni elementos inválidos

**Severidad: MEDIO. Coste: acotado.** Dónde: spec §3, líneas 106–110, y §4, línea 127; `core/crm_ficha.py:27`, `:109`; `scripts/crm_ficha.py:79`, `:97`, `:156`.

Mapping y secuencia son formas distinguibles de YAML: admitir ambas no es ambiguo en sí. Falta la semántica de ausencia y error, y cómo cruza la colección el DTO y el orquestador singular. Probar solo mapping frente a lista unitaria válida no cubre esa compatibilidad.

**Caso y comprobación:** el lector actual devolvió `contrario=None` tanto para `null` como para `[]` y `[no-es-mapping]`; un mapping válido produjo DTO y `{}` lanzó `ValueError`. Copiar el patrón de `colaboradores` —filtrar elementos que no sean dict— haría que una lista de un elemento inválido se convirtiera silenciosamente en cero contrarios. Podría completarse el resto de la ficha y verificarse lo que se intentó escribir, omitiendo esa parte. Validar conforme se itera permitiría escribir la primera parte antes de descubrir un segundo elemento inválido.

**Frontera:** compatibilidad de forma → conservación de intención y validación completa antes de efectos. Un elemento inválido no debe convertirse en ausencia de parte.

**Remedio de contrato:** fijar explícitamente ausente/null/lista vacía; rechazar elementos no mapping con índice y error legible; validar toda la colección antes de escribir. Nombrar la representación del DTO y sus consumidores (plan, ejecución y auditoría por cardinalidad). El orden de identidad se trata en H-03; no basta con conservar el orden de lectura del YAML.

## Respuesta punto por punto al mandato §4

| Punto | Resultado |
|---|---|
| 1. Exhaustividad | No es una partición del dominio completo. Faltan decisiones para NIF no interpretable y conjuntos múltiples; comparación insuficientemente definida. H-01 a H-03. Consulta email fallida: el código actual sí la bloquea, con o sin match NIF, comprobado. |
| 2. Agujero de creación | Una comparación literal puede duplicar la ficha legítima X de H-02. La salida vacía atraviesa el guard; el cierre debe decidirse antes de construirla. No todo NIF distinto demuestra una ausencia si no es comparable. |
| 3. Rol | Helper estricto correcto; proveedor por operación y relación con el profesional ausentes del diseño. H-05. |
| 4. Verificación/reintento | Evitar un falso éxito no recupera la escritura parcial ni da idempotencia a crear. H-04. El destino correcto requiere además H-06. |
| 5. Duración | Extremos reales en `_apertura_v1.json`, UTC con `Z`; no en el evento. Derivación de 90 s ejecutada; contrato de fuente/actividad por precisar. H-07. |
| 6. Mapping/lista | Tipos distinguibles; faltan semántica de vacío/error y consumidores plurales. Sondas de bordes y de orden en H-08/H-03. |
| 7. Pruebas sin CRM | La exclusión explícita del §4 se limita a la aceptación actual por el tenant y es razonable. No declara fuera de alcance las sondas locales; su lista de aceptación es insuficiente para estos contratos. Debe incluir fallos por paso, reintentos, órdenes, errores YAML, destino y procedencia temporal/rol. También cero filas, IDs de predefinida discrepantes y campo ausente frente a vacío, sin inventar un ID. |
| 8. Premisas | La corrección de `Accept` sí está en §15.6, líneas 2125–2134. Su publicación en `main` y la situación de sesiones/PRs/ramas: **SIN VERIFICAR** desde esta copia. |

## Lo que revisé y NO encontré defectuoso

### Lo que intenté refutar y NO pude

- **La política de no elegir una tarifa por defecto.** Exigir el rol es correcto; H-05 ataca su procedencia, no pide relajar el requisito. La tarifa efectiva no queda acreditada por un Subject ni por estas sondas; el spec excluye el botón de UI y no he automatizado actos fiscales.
- **El guard de consulta fallida.** Las sondas originales conservaron `sin_comprobar` cuando falló el email, tanto con NIF resuelto como sin coincidencia NIF. No afirmo que este agujero esté abierto en el código; debe preservarse su precedencia al introducir la tabla.
- **La invariancia ante permutar resultados múltiples.** El resolver actual bloqueó los dos órdenes. No selecciona la primera ficha: el problema de H-03 es la falta de decisión sobre el conjunto legítimo que P6 crea.
- **Fallar cerrado para una ficha sin NIF o un mismo NIF no encontrado por la primera consulta.** Es una decisión prudente de la tabla, una vez definido qué significa vacío/coincidente. No la refuté como política; su implementación futura queda SIN VERIFICAR.
- **Traer una property adicional sin otra petición.** Ejecuté `_buscar_registros` con HTTP simulado: incluyó `properties[1]=nif_cif`, mantuvo `Accept: application/json` y devolvió los valores anidados. La posibilidad técnica existe en la fuente actual.
- **Separar creación, vínculo y lectura desde el expediente.** Concuerda con §§15.2, 15.3 y 15.6, y con APER-24. Es una base necesaria; H-04 trata recuperación y H-06 identidad del destino.
- **No hacer de APER-14 ni del ID de cliente propio una ampliación del alcance.** APER-63 dice que `cliente_propio` debe ser la clave: el ID `"2"` aborta, como implementa el CLI. El spec invierte verbalmente clave/id en la línea 113; es una errata descriptiva, no una propuesta de cambio defectuoso. No la elevo a hallazgo de diseño.
- **Precisión del daño actual.** `_completar_contrario_existente` rellena huecos: no sustituye NIF, nombre, apellidos ni campos ya poblados. La sonda escribió el CP de B en A y conservó el móvil de A. Es contaminación de una ficha ajena y vínculo erróneo, pero no un PUT indiscriminado sobre toda la ficha. APER-26 es coherente con la escritura parcial documentada; no lo volví a medir en el CRM.
- **La corrección documental `items`/`hydra:member`.** Está presente; no corresponde rehacerla. Esto acredita la primera premisa contra el árbol, no una corrida nueva de las doce celdas del tenant.

## VEREDICTO

El diseño necesita decisiones previas a implementación en identidad, composición de las partes y recuperación de actuaciones. Los contraejemplos no se resuelven solo añadiendo tests al diff: falta definir qué resultado sería correcto. Mantengo las tres piezas, una rama y dos rondas. Claude debe adjudicar cada hallazgo contra las fuentes y las sondas; esta revisión no adjudica por él.

NO-SHIP
<!-- informe-literal:fin:k9r4 -->

## 2. Evidencia verificada por mí

- **Cadena de custodia.** `sha256` del fichero crudo: `c3486c82431891e8241f7bb35e72a8179e889db3b13692898b4b78e38c8e7918`; del bloque canonicalizado:
  `c3486c82431891e8241f7bb35e72a8179e889db3b13692898b4b78e38c8e7918`. Coinciden entre sí y con el que el revisor devolvió en su
  último mensaje. Comprobé que el proceso había terminado por la aparición de
  `_ultimo_mensaje.txt`, no por la existencia de `INFORME.md`.

- **Los ocho hallazgos, adjudicados contra la fuente.** Cada uno trae su caso concreto y su
  sonda; los verifiqué leyendo `resolver_parte`, `_buscar_registros`, `_canonizar_documento`,
  `_exigir_identidad_cierta`, `core/crm_ficha.py` y `core/apertura_v1_estado.py`. Ninguno es
  refutable. La adjudicación completa, hallazgo por hallazgo, está en el §6 del diseño rev. 2.

- **Lo que el revisor declaró SIN VERIFICAR y es correcto que lo declarara:** la genealogía del
  commit (no hay `.git` en la copia), la aceptación actual de los payloads por el tenant, la
  idempotencia del POST de creación, y la premisa del §0 sobre la ausencia de sesión hermana —que
  no es comprobable desde su copia—. Esa última la verifiqué yo con `list_sessions`,
  `gh pr list` y `git ls-remote`, y es lo que permitió hacer P6 entero en vez de fragmentado.

- **Su precisión sobre el daño actual, que corrige a la baja mi propia descripción:**
  `_completar_contrario_existente` **rellena huecos**, no sustituye campos ya poblados. Su sonda
  escribió el CP de B en la ficha de A y conservó el móvil de A. Sigue siendo contaminación de
  una ficha ajena y un vínculo erróneo, pero no un PUT indiscriminado, y el spec rev. 2 lo dice
  así.

## 3. Lo que NO cubre esta ronda

- **El diff, que no existe todavía.** Esta ronda es sobre el diseño; la R2 irá sobre el código.
- **Cualquier cosa contra el CRM real.** Ni el revisor ni el autor llamaron al tenant, y el
  diseño declara expresamente que este diff no lo hará.
- **La suite del producto.** El revisor corrió 28 sondas propias sobre cuerpos extraídos por AST,
  no la suite; eso es del autor y de `session_close`.
