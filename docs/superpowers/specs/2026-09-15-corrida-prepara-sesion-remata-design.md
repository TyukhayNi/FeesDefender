# La corrida prepara y una sesión remata: el correo entra y el JSON de viabilidad deja de ser efímero

> **Estado:** rev. 1 (2026-09-15). Diseño aprobado en conversación, sin construir todavía.
> **Origen:** las tres decisiones de Nikolai del 2026-09-14, que son el disparador declarado de
> `MEJORAS #264` («que Nikolai elija cuál de las tres salidas quiere»):
> **(1)** la salida elegida es la **3** —la corrida prepara, una sesión remata en un paso—;
> **(2)** el correo **entra** en la corrida; **(3)** el clasificador por LLM queda **cerrado**,
> no se prueba prompt ni modelo (`MEJORAS #263`, refutado por medición: 13 % y convencido).
> **Radio de daño y rondas:** ninguna de las dos piezas decide quién puede escribir sobre qué
> copia, y ninguna puede destruir ni corromper datos de cliente —la etapa de viabilidad **crea**
> un fichero nuevo y nunca sobrescribe—, así que **no** entran en la categoría de dos rondas.
> Tampoco son docs puro: las dos tocan la secuencia de apertura. → **una ronda adversarial sobre
> el diff, por PR** (`CLAUDE.md`, §«Cuántas rondas»). El presupuesto se relee del diff cuando
> exista; esta línea no lo congela.

## 1. Qué problema resuelve

`MEJORAS #264` describe un hueco que se lee tres veces como tres problemas (#36, #262, #263) y es
uno: **qué hace la corrida de apertura cuando necesita que alguien *lea* el expediente.** Las dos
etapas que faltan para cerrarla —sala de lectura y viabilidad— no están bloqueadas por el cableado,
sino por que hoy el único lector fiable es una sesión de Claude, y una sesión no se invoca desde un
`subprocess`.

Nikolai eligió la salida 3, que es la única de las tres que nadie había medido. Este diseño la
construye para **la viabilidad**, y de paso mete en la secuencia la pieza que ya estaba construida
y solo frenada por una puerta: **el correo**.

## 2. Los dos hallazgos que cambiaron el diseño, medidos el 2026-09-15

Ninguno de los dos estaba en el encargo. Los dos se midieron **corriendo**, no leyendo, y los dos
mueven lo que este trabajo puede prometer. Van aquí arriba porque el resto del spec depende de ellos.

### H1. El contrato del JSON que publica `MEJORAS #262` tiene cuatro campos mal

`#262` dejó escrito el contrato del JSON de viabilidad «derivado POR EJECUCIÓN el 2026-09-14 —no
leyéndolo, porque leerlo no bastó». La ejecución fue real y el contrato salió **incorrecto en cuatro
campos**. Contrastado contra el consumidor real,
`.claude/skills/viabilidad-prerelleno/scripts/render_informe.py`:

| Campo | `#262` declara | El consumidor lee | Qué ocurre, medido |
|---|---|---|---|
| `importes` | `{principal, costas, intereses}` | `{precio, pct_honorarios, pagos_parciales, propuesta_pago}` | **Los tres se ignoran en silencio.** Con `principal: 12000`, la celda `H13` queda `None`, `E14`/`H15` salen con sus defaults (5 y 0) y el script imprime `OK` |
| `motivos_impago` | lista (`[]`) | **cadena** (`.strip()`, `.upper()`) | con una lista no vacía: `AttributeError: 'list' object has no attribute 'strip'` |
| `actividades` | lista (`[]`) | **objeto** de 4 claves (`.get()`) | con una lista no vacía: `AttributeError: 'list' object has no attribute 'get'` |
| `bitacora_inicial` | texto (`"..."`) | **booleano**: `if d.get("bitacora_inicial", True)` | el texto enviado se descarta y se escribe uno fijo |
| `equipo` | objeto de 4 claves | objeto de 4 claves | ✅ **fila de control**: acertó — acredita que la medición no era ciega |

**Por qué su ejecución no pudo verlo, que es la parte que enseña.** `#262` pasó `[]` en los dos
campos de lista y claves desconocidas en `importes`. Una lista vacía es *falsy*, así que
`d.get("motivos_impago") or ""` y `d.get("actividades") or {}` la sustituyen y **nunca revientan**;
y `.get()` sobre una clave que no existe devuelve el default **sin avisar**. El instrumento **no
podía dar el otro valor**: esa corrida no era capaz de distinguir «campo correcto» de «campo
ignorado», y salió `OK` en los dos casos.

Esto importa porque este diseño consiste precisamente en **escribir ese JSON**. Construirlo sobre el
contrato publicado produciría, sin nadie delante, informes con los importes vacíos y un `OK` en
pantalla.

### H2. El `equipo` no es derivable de `_ficha_crm.yaml`

El encargo daba por supuesto que la corrida podría derivar el equipo comercial «desde
`_ficha_crm.yaml`». **Es falso, medido sobre 10 fichas reales del Drive del despacho y sus 25
colaboradores**: las únicas claves presentes son `nombre`, `email`, `movil`, `telefono` y `nif`.
**Cero** claves de rol, cargo, lado o puesto. Coincide con el modelo: `NuevoColaborador`
(`core/sudespacho_relations.py:213`) no tiene campo de cargo, y `_colaborador_de`
(`core/crm_ficha.py:124`) lee esos cinco y nada más.

Y aunque lo tuviera no bastaría: el informe pide cuatro roles **con lado** —director y asesor,
captador y buscador— y el cargo de una firma (`core/email_firmas.py` sí lo extrae) dice la función,
no el lado. Un «Asesor inmobiliario» puede ser captador o buscador según la operación.

**Consecuencia, que es lo que hay que decir sin adornos:** de los once campos del JSON, la corrida
puede rellenar **cuatro** sin leer el expediente. Los 14 hitos, las 88 preguntas y los avisos siguen
necesitando la sesión.

### 2.1. Por qué la etapa vale la pena aun rellenando 4 de 11

El valor no son los cuatro campos. Es que **el JSON exista como fichero, en su sitio, con la forma
correcta y validada**. Hoy no existe ninguno: `#262` midió cero JSON en cuatro expedientes y tres
informes ya generados, o sea que el flujo se usa y su entrada se pierde. La sesión que remata abre
un molde correcto en vez de inventarse la forma — y ya sabemos qué produce inventarse la forma:
un contrato con cuatro campos mal, publicado como medido.

## 3. Alcance

**Dentro:**

- Promoción de `MEJORAS #264` a `PLAN.md` por decisión expresa de Nikolai (el procedimiento que
  `CLAUDE.md` §«Regla de promoción backlog → cola» prescribe).
- Una etapa `email` en la secuencia de apertura, y el levantamiento de la puerta `_FUENTES_V1`.
- Una etapa `viabilidad` que deja el JSON escrito con lo derivable y el residuo marcado.
- La corrección del contrato publicado en `MEJORAS #262`.
- La regla de aviso en `render_informe.py` sobre las claves que no reconoce.

**Fuera, y por qué:**

- **El clasificador por LLM** (`MEJORAS #263`): cerrado por decisión de Nikolai, no por falta de
  capacidad. `scripts/medir_clasificador_llm.py` se queda quieto. No se prueba prompt ni modelo.
- **La etapa `sala_lectura`**: es la otra mitad de `#264` y depende del mismo lector. Cablearla hoy
  produciría una etapa que siempre sale `saltada`, que es el hueco de hoy con más código encima.
- **P8 (c)**, el lote en serie: aparcado por decisión expresa.
- **El rol en `_ficha_crm.yaml`**: decidido por Nikolai — el equipo va como residuo marcado. Añadir
  un campo de rol toca el contrato de la ficha y sus validaciones; es una tanda aparte, no un añadido.
- **`MEJORAS #254-#257`**: fuera del encargo.
- **Una décima comprobación en `verificar_apertura`** por el JSON: cabe natural con el orden que
  este diseño deja, pero no entra aquí.

## 4. PR 1 — el correo entra en la corrida

### 4.1. Qué está construido y qué lo frena

`--fuente email` **ya existe**: `_validar_flags` exige sus dos flags (`--cuenta`, `--label`) y el
intake llama a `email_export.export_label`, que reserva un lote y deposita en
`00_Input/<AAAA-MM-DD>_email_<NN>/`. Lo único que lo frena en la corrida es una puerta declarada:
`_FUENTES_V1 = ("drive_ev",)` (`scripts/abrir_caso.py:285`).

**Dato medido, contra el dimensionado errado que la propia `#264` corrige:** `core/email_export.py`
**solo lee** de Gmail. Toda su superficie de API son `users().messages().get`,
`users().messages().list` y `users().labels().list`. Cero `modify`, `send`, `insert`, `delete`,
`trash` o `create`. Escribe en el caso, no en Gmail.

### 4.2. El diseño

**El correo es una etapa más, no una fuente que sustituye al Drive.** «Entra en la corrida» significa
que forma parte de la secuencia, no que desplace a `etapa_drive`. La corrida sigue materializando
Drive E&V y, además, trae el correo si se le dice cuál.

**Orden: entre `drive` y `crm`, y en todo caso antes de `sala_maquina`.** Esto no es estético. La
sala de máquina hace el OCR y la atomización leyendo `00_Input`; un adjunto que llegue solo por
correo y se deposite después **no se OCR-ea y no aparece en la sala de lectura** (`MEJORAS #68.a`).
Poniéndola antes, el gotcha del runbook —atomizar y pull antes del OCR— se cumple **por
construcción y no por memoria del operador**, que es la razón por la que la atomización ya vive
dentro de la tercera etapa.

La secuencia queda:

```
drive → email → crm → sala_maquina → crm_alta → actuacion → viabilidad → verificar
                                                            └── PR 2 ──┘
```

**La etapa sale `saltada` con su pendiente cuando no se pide correo.** Sin `--cuenta` y `--label`
no hay etiqueta que traer, y eso es una decisión declarada, no un fallo — exactamente el patrón de
`etapa_crm_alta` con `--crm skip`. `saltada` no es `hecha`: significa que la etapa decidió, con
razón declarada, que no había nada que hacer.

**La puerta se levanta, no se borra.** `_FUENTES_V1` pasa a admitir `email`; el resto de fuentes
(`manual`, `whatsapp`) siguen fuera y siguen diciendo por qué. Levantar la puerta entera sería el
salto silencioso que el patrón de V2 existe para evitar.

**`PENDIENTE_FUENTES_V3` se precisa, no se retira.** Su texto dice hoy «V1 no descubre correo en
Gmail ni consulta LeadHub». Con `--cuenta` y `--label` la corrida **no descubre** correo: se le dice
exactamente qué etiqueta traer, así que la frase sigue siendo literalmente cierta — pero se lee como
«el correo nunca entra», y a partir de este PR eso induce a error. Se ajusta el `detalle` para
distinguir *descubrir* de *exportar una etiqueta dada*, dejando intactos el `codigo` y la referencia:
los cuatro ficheros de test que lo fijan comparan la referencia y `.codigo`, no el texto.

### 4.3. Tests

- La etapa sale `saltada` con su pendiente sin `--cuenta`/`--label`.
- La etapa sale `hecha` con ellos, con el exportador inyectado (nunca Gmail real).
- La etapa sale `fallo` con su detalle si el exportador revienta, sin tumbar la corrida.
- `--modo v1 --fuente email` sin `--cuenta` o sin `--label` falla **antes** de cualquier efecto.
- `--modo v1 --fuente manual` sigue rechazado, con su mensaje.
- `email` precede a `sala_maquina` en la secuencia — la propiedad, no el índice.
- `--hasta email` es vocabulario válido.

## 5. PR 2 — el JSON de viabilidad deja de ser efímero

### 5.1. La frontera que remedia H1

El remedio **no** es corregir cuatro nombres de clave. `render_informe.py` ya avisa de lo que no
reconoce —`hito desconocido '1' — se ignora`, `pregunta 'x' no está en la plantilla — se ignora`—
pero solo en los dos diccionarios que recorre **por clave**. Los campos de primer nivel y el interior
de `importes` y `actividades` los lee con `.get()`, y ahí **calla**. Esa asimetría es el defecto: los
12.000 € se perdieron por el lado que no avisa, y cualquier clave futura mal escrita se perderá
igual.

**La regla, una y la misma para todo el fichero: toda clave que el consumidor no reconoce se dice en
voz alta.** Se aplica a los campos de primer nivel, a los de `importes` y a los de `actividades`, con
el `warn()` que el módulo ya tiene. No se aborta: avisar y seguir es lo que el propio fichero decidió
para las preguntas de tipo inesperado, y por la razón escrita allí — «tragárselo en silencio sería
peor que el crash».

### 5.2. Dónde vive la validación, y por qué a los dos lados

`render_informe.py` se ejecuta **en el servidor** (Cowork/claude.ai) tras empaquetar el `.skill`; no
puede importar del core del repo. Y el defecto medido ocurre **en el consumidor**. De modo que:

- **En el productor** (`core/viabilidad_json.py`, en el PC): valida antes de escribir. Impide que la
  corrida deje un JSON mal formado.
- **En el consumidor** (`render_informe.py`, en el servidor): la regla de §5.1. Impide que una sesión
  que rellene el JSON a mano en Cowork pierda campos en silencio.

Validar solo el productor dejaría vivo justo el camino por el que se midió el defecto. No es
duplicación: son dos fronteras distintas, y cada una muerde donde la otra no llega.

### 5.3. `core/viabilidad_json.py`

Un módulo con tres responsabilidades y ninguna más:

- **El contrato como dato**, no como prosa: los nombres de campo reales, sus tipos, y qué claves
  admite cada objeto anidado. Es la fuente que el productor y los tests comparten.
- **`preparar(...)`**: compone el JSON con lo derivable y el esqueleto completo del resto.
- **`validar(...)`**: comprueba un JSON contra el contrato y devuelve lo que no cuadra.

**Lo que la corrida deriva (4 campos), y de dónde:**

| Campo | Fuente |
|---|---|
| `case_id` | `ident.case_id` |
| `ref` | `ident.w_code` |
| `fecha` | reloj del sistema |
| `observaciones` | `ident.tipo_caso` |

Los cuatro salen de `Identidad` (`core/abrir_caso.py:82`) y del reloj. **`tipo_caso` es un campo
propio de `Identidad`, no hay que parsear el sufijo del `case_id`**: derivarlo de la cadena
funcionaría hasta el primer caso cuyo nombre no siga el patrón.

**El residuo, marcado y vacío:** `equipo` (sus cuatro claves), `importes`, `hitos`, `preguntas`,
`avisos`, `actividades`, `motivos_impago`.

**La marca es un campo propio del JSON, no un comentario ni una convención de valor.** Lleva la lista
de campos que la corrida no pudo derivar y la razón por la que no pudo — para `equipo`, que el dato
no existe en la apertura (H2); para los demás, que exigen leer el expediente. Va como campo y no
como «lo vacío significa pendiente» porque un valor vacío es **ambiguo**: no distingue «nadie lo ha
puesto» de «se miró y no había». Esa ambigüedad es la misma que dejó pasar los cuatro campos de H1, y
aquí cerraría el círculo justo donde la sesión que remata necesita saber qué le toca.

**Ese campo entra en la lista de claves conocidas de `render_informe.py`, que lo ignora en silencio.**
Es parte del contrato del JSON aunque el consumidor no lo use, así que no es una clave desconocida y
no debe avisar: un aviso que sale en **todas** las corridas deja de leerse, y entonces el que sí
importa —una clave de verdad mal escrita— se pierde entre el ruido. La regla de §5.1 distingue «no
reconozco esto» de «reconozco esto y no me toca a mí».

**Dónde vive el fichero, y por qué me aparto de lo que sugiere `#262`.** La ficha propone dejarlo
«junto al informe, dentro del expediente». Va en **`00_Input/`**, no junto al informe, por tres
razones: hay **precedente exacto** —`_recibo_actuacion.json` vive ahí y por el mismo motivo—,
`core/intake_control.py` ya mantiene la lista de ficheros de protocolo de `00_Input/`
(`_ficha_crm.yaml`, `_ocurrencias_crm.json`) que no se inventarían como documento del cliente, y
porque este JSON es la **entrada** del informe, no una versión suya: ponerlo junto al `.xlsx`
invitaría a leerlo como entregable. La frontera que `#262` señala —protocolo, no documento de
cliente— se respeta; lo que cambia es dónde ya existe el mecanismo que la implementa.

**Nunca sobrescribe.** Si el JSON ya existe, la etapa sale `saltada` y lo dice. Es la misma
protección que `render_informe.py` aplica al `.xlsx` —y por la misma razón: un reintento que pisa el
trabajo de la sesión anterior destruye lo único que costaba caro. Que un fallo a mitad deje residuo
que hay que retirar a mano es un coste aceptado y declarado, igual que allí.

### 5.4. La etapa `viabilidad`

Va **al final de la secuencia y antes de `verificar`**: `verificar` cierra la corrida, que es su
papel, y así una futura comprobación del JSON cae en el sitio natural sin reordenar nada.

Sale `hecha` cuando escribe el JSON; `saltada` cuando ya existía, con su detalle; `fallo` con su
detalle si no pudo escribir. En los tres casos deja un **pendiente** que nombra lo que la corrida no
pudo derivar y quién lo remata — el «residuo marcado» de la salida 3, que es la mitad del valor de
esta etapa.

### 5.5. La ficha `MEJORAS #262`, corregida

Se reescribe el bloque del contrato con los cinco campos correctos y se añade **por qué su ejecución
no pudo verlos** (§2, H1). Lo segundo importa más que lo primero: la ficha se publicó como «derivado
por ejecución», que es el sello de calidad de la casa, y salió mal. Sin la explicación, el próximo
que derive un contrato por ejecución con valores vacíos cometerá el mismo error creyendo que lo ha
medido.

### 5.6. Tests

- El contrato: cada campo declarado tiene el tipo que el consumidor lee.
- `preparar` rellena los cuatro derivables y deja marcado el resto.
- `preparar` compone un JSON que `validar` acepta — y el `equipo` sale vacío, nunca inventado.
- `validar` **rechaza** los cuatro defectos de H1, uno por uno: `importes` con las claves de `#262`,
  `motivos_impago` como lista, `actividades` como lista, `bitacora_inicial` como texto.
- La etapa sale `saltada` sin sobrescribir cuando el JSON ya existe, y el fichero anterior queda byte
  a byte igual.
- El JSON producido por `preparar` **corre de verdad** por `render_informe.py` y genera el `.xlsx`
  —el control que `#262` no tuvo: verificar por resultado, nunca por status—, y el test **lee las
  celdas**, no el código de salida: el defecto de H1 salía con `OK` en pantalla. Salida y JSON van a
  `tmp_path`, nunca al árbol de producción, y el test se salta solo si falta `openpyxl`.
- `render_informe.py` avisa de una clave desconocida de primer nivel, de una de `importes` y de una
  de `actividades`, y **no** avisa de las conocidas: el instrumento tiene que poder dar los dos
  valores.

## 6. Lo que este diseño NO promete

- **No cierra `MEJORAS #264`.** Cierra la mitad de viabilidad; la sala de lectura sigue abierta y
  dependiendo del mismo lector.
- **La corrida no genera el informe.** Deja el JSON preparado. El `.xlsx` lo produce
  `render_informe.py` cuando la sesión ha rellenado los hitos y las preguntas.
- **La corrida no lee el expediente.** Cuatro campos de once. Los 14 hitos y las 88 preguntas siguen
  siendo trabajo de una sesión, y este diseño no finge lo contrario.
- **No se toca el clasificador por LLM.** Cerrado por decisión.

## 7. Deuda que este diseño declara viva

- La etapa `sala_lectura` sigue sin cablear (`MEJORAS #264`, la otra mitad).
- El rol del equipo comercial no existe como dato en ninguna parte de la apertura (H2). Mientras no
  exista, la corrida no podrá rellenarlo.
- No hay comprobación del JSON en `verificar_apertura`. El orden de §5.4 la deja fácil; no entra aquí.
- `render_informe.py` no valida **contra la plantilla** los identificadores de `importes` y
  `actividades` como sí hace con hitos y preguntas: este diseño añade el aviso, no la derivación
  automática desde el `.xlsx`.
