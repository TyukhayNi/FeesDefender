---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md
objeto_rev: "3"
commit: 01d9060
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: qk4v
sha256_informe: d9d71ad1a711b43db46a49f17eab512ca3c1f88e018b3db86b012001839b32c3
adjudicado_en: docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md §12
---

# Acta — R1 adversarial sobre el diseño F3 rev. 3 (Codex, 2026-09-07)

Ronda sobre el **diseño**, no sobre el diff: el objeto fue el spec rev. 3 recién escrito, antes
de construir. El revisor corrió en solo lectura sobre una copia congelada del commit `01d9060`
(`git archive` a un directorio fuera del repo), sin red y sin acceso al repositorio real.
Declaró el `sha256` del objeto al abrir y al cerrar, y coinciden.

Esta acta existe porque yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**El bloque literal archiva DOS textos del revisor, y conviene decir por qué** (la explicación
va aquí fuera, para no contaminar el bloque):

- `INFORME.md` — la revisión completa. `sha256` = `2e7999b6235dca5b2f48202c28489941d5c55735ee0cd675ce3121d6766bb187`
- `VEREDICTO.md` — solo la palabra del veredicto. `sha256` = `cceaeaa61c464dd249e1f61395c60d1797348d6363c7b340c857120cf5c60f64`

Hicieron falta dos porque **mi mandato pidió el veredicto con el vocabulario equivocado**: el
set `APTO / APTO CON REPAROS / NO APTO / SIN VERIFICAR`, en vez del set cerrado del contrato
(`SHIP · LISTA-CON-CAMBIOS · REQUIERE-REVISION · NO-SHIP · NO-EJECUTABLE · SIN-VEREDICTO`) que
es el que comprueba el guard **G9**. El error es del mandato, no del revisor. La segunda
llamada le pidió **traducir su propio juicio ya emitido**, con instrucción expresa de no
reatacar el objeto ni tocar `INFORME.md`, y **se comprobó por hash que no lo tocó** (mismo
digest antes y después). Rellenar yo el veredicto habría sido exactamente lo que esta acta
existe para hacer imposible.

## 0. Mandato entregado (literal)

# Mandato — Revisión adversarial R1 sobre un DISEÑO (spec F3 rev. 3)

## Higiene del workdir (léelo primero)

Tu directorio de trabajo (`-C`) debe contener **solo este `MANDATO.md`**. Si encuentras cualquier
otro fichero, **no lo leas** y decláralo en la primera línea de tu informe. Un fichero con marca de
tiempo anterior a este mandato no puede ser respuesta a este mandato.

## Objeto

Copia congelada y de solo lectura del repositorio FeesDefender en:

    C:\t\f3rest-obj-0907-1154

**No la modifiques.** Calcula y declara el `sha256` del fichero objeto principal **al abrir y al
cerrar** tu revisión; esa igualdad es la prueba de no-mutación (no hay `.git`, así que no puedo
pedirte `git status`).

**Objeto principal de la revisión:**

    docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md   (rev. 3)

**Contexto que debes leer para juzgarlo:**

- `docs/INTEGRACION_SUDESPACHO.md` §10.10 (el contrato que el spec dice implementar), §14.5, §14.6
- `docs/DEAD_ENDS.md` — entrada «Módulo de correo (nest-mail / Roundcube)», que este cambio revierte
- `docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md` §7, §15, §18 (el plan que el spec sirve)
- `docs/superpowers/specs/2026-07-19-intake-miniapp-entrega-design.md` (spec hermano, afectado)
- `core/procurador_intake.py`, `core/procurador_review.py`, `core/procurador_runner.py`,
  `core/procurador_search.py`, `core/gmail_source.py` — F1 y F2, ya construidas, que este diseño
  extiende. **Lee el código, no solo el spec.**
- `core/sync_sudespacho.py` (`SudespachoClient`, `SudespachoConfig`) — el transporte propuesto
- `CLAUDE.md` y `docs/GOBERNANZA_FUENTES_VERDAD.md` — las reglas de la casa

## Qué se te pide

Ataca este diseño. **No es un diff: es un spec que todavía no se ha construido**, así que el daño
que puedes evitar es el más barato de evitar.

Contexto de riesgo que debes tener presente al calibrar: la pieza **escribe en el CRM de producción
de un despacho de abogados**. Un correo relacionado con el expediente equivocado, o un documento
subido al expediente de otro cliente, corrompe el archivo profesional y puede tener consecuencias
de responsabilidad. Un fallo silencioso —algo que diga que archivó y no archivara— es peor que uno
ruidoso, porque nadie lo audita.

Presta atención especialmente a:

1. **Lo que el spec afirma como medido vs. lo que de verdad quedaría probado.** El §2 lista siete
   hechos y una prueba de punta a punta; el §8 lista lo no probado. ¿Está la frontera bien puesta?
   ¿Hay alguna afirmación del §2 que sea en realidad una inferencia? ¿Falta algo en el §8?
2. **La §4 (verificar por resultado).** ¿Las tres obligaciones que deriva bastan? ¿Hay algún camino
   por el que el módulo pueda devolver `ok=True` sin que nada se haya escrito, o `ok=False`
   habiendo escrito (que es peor: provocaría un reintento y un duplicado)?
3. **Idempotencia y reanudación.** ¿Qué pasa si el proceso muere entre el relate y el adjuntar? ¿Y
   si dos personas archivan el mismo correo a la vez? El §5 y el §8.2 dicen algo; ¿es suficiente?
4. **La resolución del `account` (§3.2).** ¿Es correcta la afirmación de que se resuelve por lectura?
   ¿Qué pasa si el mismo Message-ID está en varias cuentas (el correo llega a `procesal@` y se
   reenvía a cuatro abogados)? El spec dice que si no aparece va a revisión — ¿y si aparece en
   varias?
5. **Coherencia con F1/F2 ya construidas.** ¿El diseño encaja con lo que `procurador_review.py` y
   `procurador_runner.py` hacen hoy? ¿El requisito duro §18.9 del plan (terna propuesta / acción /
   quién-cuándo) queda satisfecho por el §6?
6. **Lo que el spec deja fuera y quizá no debería**, y lo que arrastra sin justificar.
7. **La honestidad del §0.** Describe un error de método propio. ¿Lo describe bien, o se queda
   corto / se excede?

## Cómo trabajar

- **Puedes ejecutar.** El Python de sistema es
  `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe` y trae `pytest`, `httpx`,
  `yaml`, `dotenv`, `typer`, `filelock`, `mcp`. No trae `pytest-randomly`.
- Si corres tests, usa `--basetemp` **relativo dentro de tu workdir** (no `C:\t\...`: tu sandbox no
  puede crear ahí) y **copia lo que necesites a tu workdir**; no mutes el objeto.
- **No tienes red.** Las mediciones contra el CRM que el spec cita no las puedes reproducir: si algo
  depende de ellas, decláralo **SIN VERIFICAR**, no lo des por bueno ni por falso.
- Distingue siempre **lo que has comprobado** de **lo que sospechas**. Una sospecha etiquetada como
  tal es útil; una sospecha con aplomo de hallazgo hace perder el tiempo.

## Entregable

Escribe **`INFORME.md`** en tu directorio de trabajo, con:

1. Primera línea: declaración de higiene del workdir (§ arriba) y el `sha256` del objeto al abrir.
2. Un hallazgo por bloque, cada uno con: **ID** (`H-01`…), **severidad**
   (`CRÍTICO` / `ALTO` / `MEDIO` / `BAJO`), **dónde** (fichero + sección o línea), **qué está mal**,
   **por qué importa** (el fallo concreto que produciría), y **si lo has verificado o solo inferido**.
3. Lo que hayas mirado y esté **bien**: dilo también, en una lista corta. Un informe que solo
   enumera defectos no permite saber qué quedó cubierto.
4. Lo que **no has podido verificar** y por qué.
5. El `sha256` del objeto al cerrar.
6. **Última línea: la palabra del veredicto, sola, de este conjunto cerrado y ninguna otra:**
   `APTO` · `APTO CON REPAROS` · `NO APTO` · `SIN VERIFICAR`

---

### 0.bis Mandato de la segunda llamada (literal)

# Mandato — solo el veredicto, en el vocabulario correcto

Ya emitiste tu informe de revisión R1 sobre el diseño F3 rev. 3. Está en `INFORME.md`, en este
mismo directorio, y **terminaba con la palabra `NO APTO`**.

El error fue mío: el mandato original te pidió el veredicto de un conjunto (`APTO` / `APTO CON
REPAROS` / `NO APTO` / `SIN VERIFICAR`) que **no es el vocabulario del contrato de este repo**.
El contrato exige uno de estos seis, y solo estos:

    SHIP · LISTA-CON-CAMBIOS · REQUIERE-REVISION · NO-SHIP · NO-EJECUTABLE · SIN-VEREDICTO

## Qué te pido, y solo esto

Traduce **tu propio veredicto ya emitido** a ese vocabulario. No cambia tu juicio: cambia la
palabra con que se escribe.

- **NO vuelvas a revisar el objeto.** No leas la copia congelada, no re-analices nada, no
  emitas hallazgos nuevos.
- **NO modifiques `INFORME.md`.** Su hash está registrado; cualquier cambio rompe la cadena de
  custodia del acta. Si lo tocas, el trabajo se invalida.
- Puedes releer tu propio `INFORME.md` para recordar qué concluiste, nada más.

## Entregable

Escribe **`VEREDICTO.md`** en este directorio, con exactamente dos cosas:

1. Una o dos frases diciendo a qué palabra del set cerrado equivale tu `NO APTO`, y por qué esa
   y no otra.
2. **Última línea: la palabra sola**, sin comillas, sin puntuación, sin nada más.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:qk4v -->
Higiene inicial: el workdir NO contenía solo MANDATO.md; también estaba `_stdout.log` (metadato LastWriteTime 2026-09-07 11:55:24, frente a 11:55:09 del mandato), cuyo contenido NO he leído. SHA-256 del objeto principal al abrir: D804E26AB59A354F5D42783FFAF24EEE6C7B0CA137259109A185CF999F98340E.

# Revisión adversarial R1 — diseño F3, rev. 3

Revisión realizada el 2026-09-07. Objeto congelado: `C:\t\f3rest-obj-0907-1154`. Todas las rutas de fuente citadas a continuación son relativas a esa raíz. «Spec F3» identifica `docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md`. Este informe y las sondas se han creado después del mandato, fuera del objeto, en `C:\t\f3rest-r1-0907-1154`.

El diseño necesita cambios antes de construirse como está escrito. El bloqueo principal no es que la API REST quede refutada: es que el flujo permite declarar terminado un archivo incompleto y no fija la identidad de lo que se escribe y verifica. La revisión es de diseño; los efectos futuros descritos no se presentan como incidentes ya ocurridos ni como fallos de una implementación F3 existente. La adjudicación corresponde a Claude contra la fuente.

## Hallazgos

### H-01 — Asignado no equivale a archivado completo en el destino confirmado

- **Severidad:** CRÍTICO.
- **Dónde:** spec F3 §5.1–5.3, líneas 163–167; §9, líneas 229–231; `docs/INTEGRACION_SUDESPACHO.md` §10.10, líneas 931–935.
- **Qué está mal:** §5.1 excluye del flujo todos los Message-ID devueltos por `findAssigned` y los muestra como archivados. Según el contrato citado, la respuesta solo informa de asignación; no identifica el destino ni certifica adjuntos. La exclusión impide llegar a la «idempotencia fina» del paso 3 y a la reanudación de los adjuntos.
- **Por qué importa:** (a) un correo relacionado con A que se confirma para B se muestra ✅ sin relacionarlo con B; (b) el proceso relaciona correctamente con B, muere antes de adjuntar y, al volver, lo muestra ✅ dejando los documentos sin subir. Ni siquiera hacen falta dos procesos para el segundo fallo. «Ya-relacionado → no-op» en §9 consolida ese error si el no-op incluye el archivo completo.
- **Estado de evidencia:** contradicción **VERIFICADA por lectura** del flujo y de su contrato declarado. Que el CRM devuelva efectivamente ese resultado para cada caso sigue **SIN VERIFICAR**, sin red. El contraejemplo es una deducción del contrato, no un sondeo.
- **Cambio necesario:** usar `findAssigned` solo como indicio para reconciliar. La condición terminal debe probar relación con el destino confirmado y cumplimiento de cada adjunto seleccionado, distinguiendo relación previa de archivo completo. Una relación con otro expediente debe mostrarse explícitamente antes de decidir cómo proceder.

### H-02 — El censo no identifica la escritura que se pretende certificar

- **Severidad:** CRÍTICO.
- **Dónde:** spec F3 §4, líneas 154–159; §5.9; §9, líneas 228–233; `core/sync_sudespacho.py`, líneas 627–743 y 368–377.
- **Qué está mal:** se exige comparar el censo, pero no se define el predicado de éxito: documentos esperados, identidad de origen, nombre final, carpeta, destino exacto y completitud de la lectura. Incluso comparar conjuntos de IDs nuevos no basta sin vincular esos IDs a los adjuntos pedidos. El test obligatorio solo cubre que el censo no cambie. Además, el lector reutilizable convierte un esquema JSON no reconocido en colección vacía mediante `_items`; no es automáticamente una lectura fiable para certificar escrituras.
- **Por qué importa:** la subida pedida no hace nada, pero otra persona añade un documento al mismo expediente entre las lecturas: el censo aumenta y permite un falso éxito. También aumenta si se sube el adjunto equivocado, con nombre incorrecto o a otra carpeta del mismo expediente. Una subida parcial más un documento ajeno puede dar incluso el incremento numérico exacto esperado. La prueba narrada de §2 sí comprueba nombre y carpeta; §4 no convierte esas comprobaciones en obligaciones.
- **Estado de evidencia:** insuficiencia del criterio **VERIFICADA lógicamente**; contraejemplo numérico ejecutado localmente. La aceptación de JSON no reconocido como `[]` se **REPRODUJO con el método original** y una respuesta sintética. No se ha observado una falsa certificación real en el CRM.
- **Cambio necesario:** definir una verificación por adjunto y conservar los IDs gdocu confirmados, destino, nombre y carpeta, con evidencia suficiente de correspondencia con el origen. Exigir lecturas completas, esquema válido y filtro de destino comprobado; ante ambigüedad, resultado indeterminado. Añadir casos de escritura ajena concurrente, resultado parcial, nombre/carpeta incorrectos y fallo de lectura.

### H-03 — Falta un protocolo para escritura incierta y recuperación de los IDs de adjunto

- **Severidad:** ALTO.
- **Dónde:** spec F3 §2.4, líneas 85–88; §5.4, líneas 168–170; §6, líneas 180–188; §8.2 y §9.
- **Qué está mal:** persistir los IDs cuando responde no cubre la muerte entre la escritura remota y la recepción/persistencia local. El esquema `{ok, verificado, error}` y el caso obligatorio `ok=False` no fijan un estado operativo que prohíba reescribir cuando el resultado es desconocido. «Comprueba primero el censo» tampoco determina cómo se distingue un intento ya aplicado de uno ausente. Por otra parte, §2.4 solo fundamenta recuperar `mail_id`; §5.4 lo extiende a «los ids», incluidos los `att_id`, sin dar una ruta de lectura ni su respuesta para recuperarlos.
- **Por qué importa:** un POST puede escribir y luego agotar el timeout, o la relectura fallar/desfasarse. Devolver fallo no demuestra ausencia de efecto. Repetir puede duplicar; no repetir puede dejar una omisión. Si muere tras relacionar y antes de guardar la respuesta, conocer después el `mail_id` no reconstruye por sí solo qué adjuntos había, sus IDs y el plan aprobado. Tras una subida parcial tampoco basta un estado por correo.
- **Estado de evidencia:** lagunas del contrato **VERIFICADAS documentalmente**. Las ventanas de fallo son **inferencias de ejecución distribuida**; no se han medido consistencia, atomicidad ni tiempos del servidor.
- **Cambio necesario:** persistir antes del write la intención identificada y el plan confirmado; registrar por fase y adjunto los intentos, efectos confirmados y resultados indeterminados. Una incertidumbre debe activar reconciliación por lectura, no un nuevo POST hasta resolverla. Documentar y medir la recuperación de `att_id` y las garantías de esas lecturas, o declarar la recuperación manual necesaria. Un booleano puede mantenerse como resumen, pero no sustituir ese protocolo.

### H-04 — Comprobar antes de escribir no excluye dos escritores

- **Severidad:** ALTO.
- **Dónde:** spec F3 §5 y §8.2; `docs/superpowers/specs/2026-07-19-intake-miniapp-entrega-design.md` §§2 y 4.
- **Qué está mal:** no hay una operación de adquisición exclusiva, clave de idempotencia garantizada por el servidor ni restricción operativa que impida escribir a dos instalaciones. El spec hermano llega a afirmar que comprobar la relación hace que dos personas archiven una sola vez. Son operaciones separadas, y esa conclusión no se sigue.
- **Por qué importa:** A y B consultan antes de que ninguno escriba; ambos ven pendiente; ambos relacionan y adjuntan. Consultar el censo primero no elimina esa ventana. Pueden usar planes distintos para el mismo correo, o generar duplicados si adjuntar no es idempotente. Un fichero por Message-ID sincronizado en Drive y los JSONL locales de F2 tampoco proporcionan exclusión entre equipos.
- **Estado de evidencia:** intercalado **VERIFICADO como contraejemplo del algoritmo descrito**; duplicación concreta del backend **SIN VERIFICAR**. El propio §8.2 reconoce que no se conoce su idempotencia.
- **Cambio necesario:** escoger una garantía concreta de único escritor efectivo entre instalaciones o una idempotencia remota medida y suficiente para todas las operaciones. Definir clave, conflicto entre destinos/planes y recuperación tras muerte del escritor. Si la primera entrega se limita a un único escritor, esa limitación debe ser efectiva y formar parte del contrato; no basta con suponer que las personas no coincidirán.

### H-05 — Leer `cuenta` obtiene candidatos, no decide una cuenta única ni el alcance del write

- **Severidad:** ALTO.
- **Dónde:** spec F3 §3.2, líneas 131–138; §2.5; firmas y cuerpos de §3.1/§2; spec de entrega §2; `core/procurador_runner.py`, líneas 139–146.
- **Qué está mal:** la búsqueda por `uid` se describe en singular sin definir cardinalidad, paginación ni tratamiento de varias coincidencias. El caso de reenvío a varios abogados es parte del propio diseño, no una posibilidad remota. Además, el `account` resuelto se usa para leer, pero no aparece en la firma/cuerpo de `relacionar`: queda sin medir cómo escoge el POST entre varios registros del mismo Message-ID. La decisión previa de archivar desde la cuenta del usuario tampoco queda reconciliada.
- **Por qué importa:** escoger el primer registro puede verificar una cuenta distinta de la afectada por el write, omitir una relación visible en otra, o producir un falso fallo tras haber escrito. Incluso varias filas con la misma cuenta requieren decidir qué `mail_id` se usa. La muestra de un filtro que devuelve una fila no prueba unicidad para los correos reenviados. «No aparece → no está indexado» requiere además descartar permisos insuficientes, lectura fallida o normalización distinta.
- **Estado de evidencia:** ausencia de resolución multicuenta y ausencia de `account` en el write **VERIFICADAS en el spec/SSOT**. Existencia real de varias filas y semántica del POST en ese caso **SIN VERIFICAR**; se plantean como riesgo condicionado, no como comportamiento observado.
- **Cambio necesario:** leer y validar todas las coincidencias; definir qué hacer ante cero/una/varias y preservar `(Message-ID, cuenta, mail_id)`. Ante ambigüedad, revisión sin escribir. Medir con el mismo Message-ID en varias cuentas el alcance de lectura, relate, adjuntar y `findAssigned`. La selección de cuenta necesita una política o demostrar que el write es independiente de ella con identidad inequívoca.

### H-06 — El contrato F2→F3 no conserva un destino confirmado inequívoco

- **Severidad:** CRÍTICO.
- **Dónde:** spec F3 §§1, 3.1, 5.10 y 6; `core/procurador_review.py`, líneas 46–54, 100–112, 268–312 y 346–368; `core/procurador_runner.py`, líneas 146–150; `core/procurador_search.py`, líneas 35–38; `streamlit_app.py`, líneas 2778–2825.
- **Qué está mal:** `archivar(plan)` no define su DTO ni cómo materializa los overrides humanos. F2 guarda la corrección en `intake_audit.jsonl`, pero el snapshot de cola confirmado conserva la propuesta original. `confirmado` es terminal y el runner omite todo Message-ID ya existente: no es un reanudador de writes. Además, `HumanAction` y `RobotProposal` solo guardan el ID numérico, sin tipo de elemento; la UI permite seleccionar judicial o extrajudicial. Añadir un outcome y `archivado_en_crm` no resuelve esas fronteras.
- **Por qué importa:** si F3 se conecta leyendo la propuesta del ítem confirmado, archiva en el expediente propuesto aunque la persona lo haya corregido. Si reconstruye solo el ID confirmado y supone judicial, una selección extrajudicial puede dirigirse a un judicial con el mismo número interno de ID. «Judicial-first» solo evita este último riesgo si se bloquea de forma explícita la selección y ejecución de otros elementos. Tampoco debe tratarse una confirmación histórica de dry-run como permiso tácito para ejecutar hoy.
- **Estado de evidencia:** separación de stores, conservación de propuesta y transición terminal **REPRODUCIDAS localmente** con las definiciones originales; ausencia de namespace en la acción **VERIFICADA y reproducida**. El archivo equivocado es el efecto **inferido si se conecta sin cerrar esa frontera**, no una escritura real observada.
- **Cambio necesario:** definir y persistir el plan efectivo vinculado a una decisión concreta: elemento canónico + ID, cuenta/correo, carpeta y selección de adjuntos. Aplicar explícitamente cada override sin modificar el snapshot del robot. Separar estados de aprobación y ejecución/reconciliación, definir migración de dry-run y restringir judicial-first en el punto de escritura, no solo en la prosa.

### H-07 — La traza F2 existente no basta para las decisiones de adjuntos de F3/F4

- **Severidad:** ALTO.
- **Dónde:** spec F3 §6, líneas 180–188, y §5.6–5.10; plan §18.9 y §18.2; `core/procurador_review.py`, líneas 91–93, 108–112 y 208–214; `core/procurador_intake.py`, líneas 104–115; `core/procurador_runner.py`, líneas 100–106.
- **Qué está mal:** `from_intake_proposal` proyecta la lista de adjuntos a un diccionario por nombre original. Dos adjuntos homónimos se colapsan, y no se conserva `subir`. La acción humana tampoco modela esa selección. El runner actual entrega `attachments=[]`. El outcome propuesto enumera lo subido, pero no exige el manifiesto completo de lo propuesto, aprobado, descartado y pendiente ni su enlace inequívoco con cada intento y documento remoto. El flujo sitúa F4 después del relate y no fija dónde se congela/confirma su resultado para la traza.
- **Por qué importa:** F6 no puede distinguir «no subido porque se desmarcó» de «omitido por un fallo», ni reconstruir cuál de dos `documento.pdf` aprobó la persona. Una caída antes del paso final de traza puede dejar efectos sin resultado registrado. La terna del expediente sí existe; afirmar que basta extenderla con el outcome deja sin definir la terna de los adjuntos.
- **Estado de evidencia:** colapso de nombres y pérdida de selección **REPRODUCIDOS localmente**. Falta de una obligación de manifiesto/correlación en F3 **VERIFICADA por lectura**. No se afirma que una F4 todavía no construida ya falle.
- **Cambio necesario:** identificar cada adjunto de forma estable y guardar propuesta, decisión efectiva `subir/nombre/carpeta`, actor/fecha e intento/outcome por identidad, incluido lo no subido. Mantener autoría desde F3, aunque la interfaz de auditoría se entregue con F6. El registro durable de la intención debe preceder al efecto remoto.

### H-08 — El join por orden admite una correspondencia de adjuntos no probada

- **Severidad:** ALTO.
- **Dónde:** spec F3 §10, líneas 241–244; §2.7, líneas 96–100; `core/procurador_intake.py`, `AttachmentProposal`; `core/procurador_review.py`, líneas 91–93.
- **Qué está mal:** el guardarraíl acepta «unicidad o coincidencia de orden». No se declara una garantía de orden común entre los adjuntos de origen/F4 y `mailadjunto`. Tener igual conteo o posiciones iguales no identifica el contenido. Si F4 consume exclusivamente el manifiesto devuelto por relate, los `att_id` ya están disponibles y deberían ser obligatorios; si consume el correo por otra vía, falta una correspondencia verificable.
- **Por qué importa:** dos adjuntos con el mismo nombre y orden inverso pueden recibir nombres intercambiados o seleccionarse al revés. El censo posterior puede coincidir perfectamente y no detectar nada. La exclusión de inline u otra transformación del inventario aumenta la fragilidad de un join posicional.
- **Estado de evidencia:** debilidad **VERIFICADA en el criterio permitido**; permutación y sus efectos **inferidos**, sin atribuir al CRM un reordenamiento medido.
- **Cambio necesario:** usar `att_id` estable a lo largo del flujo siempre que F4 parta de relate. Para unir fuentes distintas, exigir una identidad/correspondencia comprobable; si no existe, revisión. Prohibir el orden como sustituto de identidad salvo garantía medida y documentada que cierre ese caso, incluyendo homónimos e inline.

### H-09 — Parte de los «hechos medidos» son generalizaciones o explicaciones causales pendientes

- **Severidad:** MEDIO.
- **Dónde:** spec F3 §2, líneas 75–100; §4, líneas 148–150; §7, líneas 194–197; §8; SSOT §10.10, líneas 952–988.
- **Qué está mal:** 39/40 coincidencias no justifican la identidad universal de `uid`; queda una excepción sin caracterizar. `hasAttachments=true` junto con `mailadjunto` vacío no prueba por sí solo que la causa sean inline ni que el segundo inventario sea completo y «archivable». Un `success` ante vacíos prueba un falso positivo, no que el endpoint responda siempre success o sea incapaz de otro resultado. El plan B de pasar cookies/dataHash capturados al REST también se afirma como camino conocido sin prueba descrita de ese uso.
- **Por qué importa:** tratar un inventario incompleto como selección completa puede ocultar documentos; asumir unicidad o recuperación universal puede conducir a un registro equivocado o impedir recuperar un archivo. Considerar un respaldo de autenticación ya resuelto puede dejar la entrega sin alternativa operativa cuando cambie la API. Se repite en menor escala el salto de observación a propiedad del sistema criticado por §0.
- **Estado de evidencia:** extrapolaciones **VERIFICADAS comparando la evidencia narrada con las conclusiones**. Las propias observaciones de producción están **SIN VERIFICAR** en esta revisión; no se las da por falsas.
- **Cambio necesario:** separar observación, hipótesis explicativa y garantía exigida. Añadir a §8 la excepción `uid`, completitud del inventario y prueba de identidad/contenido, alcance por endpoint de la normalización, semántica multicuenta, recuperación de `att_id`, resultados parciales/lecturas y el respaldo REST con sesión. Cambiar «siempre» por «también responde success sin efecto en la prueba descrita».

### H-10 — La visibilidad queda como duda opcional, sin condición de habilitación

- **Severidad:** ALTO.
- **Dónde:** spec F3 §8.4, líneas 218–219; §3.1; plan §7, líneas 192–195, y §18.8; spec de entrega §§2–4.
- **Qué está mal:** el diseño reconoce que la ruta REST no recibe los permisos del plugin, pero deja pendiente «si eso importa». No exige comprobar quién puede leer el correo relacionado y los documentos creados. La prueba bajo una API key no establece visibilidad para las personas que deben consultar/revisar, ni ausencia de visibilidad para quienes no deben acceder. Tampoco concreta la identidad efectiva del usuario API aprobado para la escritura frente a reutilizar una clave existente de lectura.
- **Por qué importa:** puede quedar un archivo visible para el robot pero invisible para quien tramita el asunto, o una ampliación de acceso no pretendida. El censo del robot no distingue ninguno de esos resultados. El riesgo no queda cubierto por la medida judicial pendiente: son condiciones distintas.
- **Estado de evidencia:** ausencia de criterio de aceptación **VERIFICADA en el diseño**. Una fuga o restricción real de permisos **NO está comprobada**; debe quedar **SIN VERIFICAR** hasta medirla.
- **Cambio necesario:** exigir antes de habilitar writes una comprobación de permisos efectivos sobre relación y documentos, con el usuario API previsto y usuarios humanos representativos. Fijar el resultado esperado y el bloqueo ante visibilidad no demostrada. La autoría humana debe seguir en la traza propia, compatible con la atribución CRM al robot que aprueba el plan.

### H-11 — La revisión documental pendiente afecta a decisiones operativas, no solo al webview

- **Severidad:** MEDIO.
- **Dónde:** spec F3 §7, líneas 201–204; plan §§7 y 15; spec de entrega §§1–5 y 8; `docs/GOBERNANZA_FUENTES_VERDAD.md`, principio rector y tabla de hogares canónicos.
- **Qué está mal:** se limita la afectación del hermano a §5/auth, pero también cambian o chocan la cuenta de archivado personal (§2), el significado de archivado y la garantía contra concurrencia (§4), y la autoría aplazada a F6 (§8). El plan sigue descartando REST en §7 y mandando resolver auth de nest-mail en §15. Quitar la necesidad técnica de webview tampoco revoca la decisión de una app instalable, bajo demanda y centrada solo en bandeja.
- **Por qué importa:** un implementador puede cumplir un documento y romper otro: desplegar cuentas con distinta semántica, mostrar archivo completo con solo relación, aplazar la traza o entregar la app general cuando se había decidido otra forma de uso. Son contratos todavía presentados como vigentes.
- **Estado de evidencia:** contradicciones **VERIFICADAS por lectura**. No se atribuye a esta revisión autorización para cambiar las decisiones del usuario.
- **Cambio necesario:** identificar todos los apartados afectados y reconciliarlos antes de habilitar la entrega. Mantener el contrato de transporte en §10.10 y enlazarlo desde el plan. Separar la eliminación del requisito de webview de cualquier decisión de empaquetado/producto.

## Frontera de evidencia del §2 y evaluación del §0

En esta revisión, **ninguna medición de producción del 2026-09-07 se ha reproducido**. La tabla juzga lo que alcanzaría a probar la evidencia narrada si se confirma; la reiteración de la misma narración en spec, SSOT y DEAD_ENDS no constituye tres mediciones independientes.

| Afirmación | Alcance que sí tendría la prueba narrada | Frontera pendiente |
|---|---|---|
| §2.1, cookies/dataHash vacíos | Ese relate escribió con claves presentes y vacías, bajo la credencial y condiciones de la prueba. | No garantiza otros usuarios/cuentas ni comportamiento futuro. «Opcionales» no describe claves cuya presencia es obligatoria. |
| §2.2, elemento sin sufijo | La forma sin sufijo funcionó y la forma con sufijo produjo el error narrado. | No valida por sí sola todos los elementos; judicial sigue bloqueado correctamente en §8.3. |
| §2.3, JSON con IDs | La respuesta observada de relate permite encadenar esa operación. | No acredita recuperación posterior de `att_id`, respuesta de correo sin adjuntos, pluralidad de `mail_id` ni igualdad entre inventarios de origen y CRM. |
| §2.4, `uid` | Correspondencia en 39 casos y selectividad del filtro de un Message-ID. | Excepción número 40, unicidad entre cuentas, normalización en esa lectura y recuperación de los adjuntos. |
| §2.5, `account` | La cuenta altera la lectura de relaciones en el ejemplo narrado. | Cardinalidad multicuenta, alcance del write sin account y permisos. La referencia de El Contable no forma parte de la evidencia examinada. |
| §2.6, con/sin `<>` | Compatibilidad de las variantes en las operaciones efectivamente sondeadas; el pelado de Gmail sí se comprobó en código y sonda. | No se enumeran las operaciones medidas, especialmente el filtro `uid` y los IDs devueltos por `findAssigned`. Gmail tiene fallback a ID interno cuando no hay cabecera, comprobado localmente; no debe pasar como Message-ID RFC. |
| §2.7, inline | Los dos endpoints pueden dar resultados diferentes; un `false` observado refuta que el booleano sea siempre true. | La causa inline y que `mailadjunto` represente todos los adjuntos que deben archivarse son hipótesis, no consecuencias necesarias. |
| Prueba punta a punta | Relación y un documento con nombre/carpeta solicitados en un extrajudicial inicialmente vacío; selección 1 de 3 en ese caso. | No prueba contenido binario correcto, exclusividad de efectos, judicial, permisos, parciales, reintentos, concurrencia ni reanudación. |

**§0 acierta en el error central:** un HAR de la UI no demuestra inexistencia de otra ruta API. La entrada conservada de DEAD_ENDS, líneas 676–677, documenta que `MailRoundcube` ya era candidato y pasó a «descartado» a partir del HAR. El atlas congelado, líneas 776–780, contiene las cinco operaciones. Eso sostiene el diagnóstico documental: se cerró indebidamente una posibilidad que estaba identificada.

**Límite de esta comprobación:** no hay aquí historial de llamadas ni las revisiones 1/2 para probar «sin haberlo llamado nunca», la disponibilidad exacta del catálogo en julio o el coste temporal completo. No deben convertirse en acusaciones fácticas nuevas por repetir la autocrítica. La regla de método citada se documenta como cristalizada en agosto; sirve como lección actual, pero no he probado su vigencia en julio. La referencia correcta de §14.6 es INTEGRACION_SUDESPACHO, a la que CLAUDE enlaza. El §0 también dice «cuatro» operaciones mientras la tabla define cinco; es una imprecisión editorial menor.

**Dónde se queda corto:** localizar la alternativa REST elimina una restricción técnica observada, pero no cierra todavía el contrato seguro de escritura. El mismo rigor de §0 debe aplicarse a los inventarios, IDs, cuentas y condiciones de éxito de la nueva vía (H-02, H-05, H-09). No hay base para cuestionar intenciones ni para refutar REST por esos defectos.

## Lo revisado que está bien

- La separación de transporte REST y decisión humana conserva una arquitectura razonable UI→core. `SudespachoConfig.headers()` y la construcción de `SudespachoClient` sí permiten enviar `x-api-key` al host configurado; no existe un obstáculo de transporte en ese código que obligue al webview. No se ha validado autenticación real.
- Prohibir que un 200/`success` sea prueba suficiente del write es correcto. Las relecturas de relación y gdocu son piezas necesarias; H-02/H-03 precisan lo que todavía les falta.
- El bloqueo explícito de judicial hasta medirlo (§8.3) es correcto para un alcance judicial-first. No se da por probado por simetría con extrajudicial.
- `record_decision` ya persiste propuesta, acción, actor y fecha mediante JSONL con flush/fsync; el snapshot del robot se conserva. Es una base real para §18.9, aunque falta el contrato ampliado descrito en H-06/H-07.
- F1 trata un match múltiple como dudoso; F2 mantiene la confirmación humana y el runner deduplica la ingesta por identidad de correo. Son propiedades útiles, distintas de la idempotencia del write.
- Es razonable dejar fuera de F3 el algoritmo LLM de nombres, grabaciones y la interfaz de F6. Eso no permite posponer la identidad de adjuntos, su selección aprobada o la evidencia durable que F3 deberá entregarles.
- Se declara la idempotencia de adjuntar como no probada, se propone un test de falso success y se documentan residuos del sondeo sin ordenar borrarlos. No he borrado ni alterado esos residuos ni accedido al CRM.

## Cobertura ejecutada y límites

Se leyeron el spec principal completo; INTEGRACION_SUDESPACHO §§10.10, 14.5 y 14.6; la entrada indicada de DEAD_ENDS; el plan §§7, 15 y 18; el spec de entrega; CLAUDE y GOBERNANZA_FUENTES_VERDAD. Se leyeron completos `procurador_intake.py`, `procurador_review.py`, `procurador_runner.py`, `procurador_search.py` y `gmail_source.py`. De `sync_sudespacho.py` se revisaron configuración, construcción del cliente, helpers HTTP/colecciones y lectores de carpetas y gdocu. Se contrastaron adicionalmente la confirmación de bandeja en `streamlit_app.py` y el catálogo Mail/MailRoundcube del atlas local.

**Ejecución offline:** se copiaron cinco módulos a `scratch/source/`; sus SHA-256 coinciden con los del objeto. `scratch/test_review_probes.py` selecciona mediante AST las definiciones originales necesarias, sin editarlas, e inyecta dependencias sintéticas de actor, reloj, extractor y respuesta HTTP. No importa módulos desde el objeto ni usa credenciales. Esto prueba esos fragmentos y DTOs; no sustituye la importación integral ni la suite de F1/F2.

Comando ejecutado desde el workdir:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest scratch/test_review_probes.py --basetemp scratch/pytest-tmp -p no:cacheprovider -q
```

Resultado: **7 passed in 5.84s**, exit code **0**. Las sondas afirman y reproducen el comportamiento descrito, incluidas las limitaciones; verde no significa diseño aprobado. Cubren: override en audit frente a propuesta conservada en cola; ausencia de namespace destino; colapso de homónimos/pérdida de selección; dedup del runner sin reanudar; pelado y fallback Gmail; JSON gdocu no reconocido convertido en vacío; y contraejemplo matemático de verificación por conteo. El último es un modelo lógico, no ejecución de F3.

**SIN VERIFICAR:** las siete mediciones y el punta a punta en CRM, sus respuestas literales y binarios; permisos efectivos; cuenta múltiple y política interna del POST; idempotencia/atomicidad/consistencia del servidor; recuperación real de IDs; caso judicial; autenticación de respaldo; existencia y estado actual de los residuos en 636. No hay red por mandato, ni se ha intentado acceder. No se leyeron HAR con PII ni la referencia externa de El Contable. No se ejecutó la suite general, la UI ni una implementación F3: el objeto de esta revisión es un diseño. No se inventaron fixtures como evidencia de respuestas reales.

No se ha escrito en la copia congelada. Las únicas escrituras propias se han realizado en el workdir: informe y scratch de sondas. El archivo `_stdout.log` encontrado al inicio no se ha usado como fuente. La igualdad de hashes acredita que el fichero principal conserva los mismos bytes al abrir y al cerrar; no es un hash de todo el árbol.

## Cierre

SHA-256 del objeto principal al cerrar: **D804E26AB59A354F5D42783FFAF24EEE6C7B0CA137259109A185CF999F98340E**. Coincide con el de apertura.

El veredicto se funda en contradicciones y lagunas comprobables del diseño, no en declarar falsa una API que no se pudo sondear. Deben cerrarse antes de habilitar escrituras la definición de archivo completo, la identidad de destino/adjuntos, el tratamiento de efectos inciertos y concurrentes, la traza de decisiones y las condiciones de permisos. La validación judicial ya exigida por el spec sigue pendiente.

NO APTO

--- VEREDICTO.md (segunda llamada del revisor, solo la palabra) ---

Mi veredicto «NO APTO» equivale a NO-SHIP porque el informe identifica bloqueos que deben cerrarse antes de habilitar escrituras. Expresa un juicio negativo ya emitido sobre el diseño, no una aprobación condicionada ni la imposibilidad de revisar o emitir veredicto.

NO-SHIP
<!-- informe-literal:fin:qk4v -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-09-07)

Cada hallazgo se contrastó **contra la fuente** —el código del objeto y, donde era posible, el
CRM por lectura—, nunca contra el diff ni contra el aplomo del informe. Tres se midieron en
vivo, cosa que el revisor no podía hacer (mandato sin red).

**H-05 — REFUTADO en su premisa fáctica, confirmado como hueco documental.** El revisor temía
que el auto-forward a cuatro abogados produjera un registro `mail` por buzón y que
`resolver_cuenta` eligiera a ciegas. Medido contra el CRM sobre doce Message-ID de la página
más reciente de `element_registries/mail`: **0 de 12 tienen más de un registro**
(`totalItems=1` en los doce). El CRM indexa **una** copia por correo, no una por buzón. El
hueco que sí existía —tratar la cardinalidad en singular sin declararla— se remedia con un
guardarraíl: con más de una cuenta válida, `resolver_cuenta` devuelve `None` y va a revisión.

**H-06 — CONFIRMADO, y es el más grave de los once.** Verificado leyendo la fuente:
`core/procurador_review.py` declaraba `RobotProposal.expediente_id: int | None` y
`HumanAction.expediente_id: int | None` **sin ningún campo de tipo de elemento**, mientras
`streamlit_app.py` ofrece un `st.selectbox("Buscar en", _ps.ELEMENTOS_BUSCABLES)` con judicial
y extrajudicial, usa esa elección para buscar y para leer los datos, y **la descarta** al
construir la acción confirmada. Un id confirmado no identificaba un expediente: el
extrajudicial 636 y un hipotético judicial 636 son expedientes de clientes distintos.
Remediado: `element` en la terna y `destino_efectivo()` como única fuente del destino.

**H-07 — CONFIRMADO.** `from_intake_proposal` construye
`attachment_names={a.original_filename: a.proposed_name ...}`: un diccionario por nombre
original, así que **dos adjuntos homónimos se colapsan en silencio** y `subir` no se conserva.
El efecto sobre F3 es menor de lo que el informe sugiere —`_emparejar` detecta los homónimos y
manda a revisión en vez de adivinar, verificado por el mutante «join ambiguo: coge el primero»,
que muere—, pero la pérdida en la traza es real y queda declarada.

**H-10 — rebajado por medición posterior.** Medido con `GET /api/mail/permissions/{id}` sobre
los tres correos del sondeo: **el CRM deriva los permisos solo**, sin que la vía REST los pida
— grupo «Oficina del Despacho Principal» (el id 2 que el plugin mandaba a mano) y usuario = el
**titular del buzón desde el que se archiva** (cuenta 20 → `ana.velastegui`, cuenta 15 →
`Nikolai_Tyukhay`). Eso convierte la incógnita en una propiedad del diseño: **la visibilidad se
hereda del buzón**. Lo que el informe pide y sigue faltando es el criterio de aceptación.

**H-01, H-02, H-03, H-04, H-08, H-09, H-11 — CONFIRMADOS por lectura.** H-01 y H-02 se
remediaron en el código, cada uno con su test y su mutante muerto; H-08 ya estaba resuelto en
el cliente, que exige unicidad y no acepta el orden que el spec permitía.

**H-01 se cobró su valor el mismo día, en la primera prueba de campo.** Un correo constaba
relacionado con el expediente y su documento **no estaba subido**. Con el código anterior a la
remediación, el módulo habría contestado «ya estaba, no hago nada» y el documento no habría
subido nunca, en silencio. La ronda se pagó sola.

**H-09 — confirmado, y con razón de más de la que el revisor podía acreditar.** Dijo que la
rev. 3 saltaba de la observación a la propiedad del sistema, «repitiendo en menor escala el
salto criticado por su propio §0». No tenía red para demostrarlo. Cuatro horas después la
prueba de campo lo demostró: `cookies`/`dataHash` vacíos valían **sobre correos ya indexados**
y se había escrito como si valieran siempre. Sobre un correo entrante nuevo, el relate REST
devuelve 200 y **no escribe**. Ese hallazgo está en el origen de la rev. 4.

**Divergencia declarada.** Se acepta el veredicto: el diseño rev. 3 no era apto para
construirse tal cual. No se acepta el encuadre de que la vía REST quede en entredicho — el
propio informe lo dice: «no hay base para cuestionar intenciones ni para refutar REST por esos
defectos». Lo que estaba mal era el contrato de seguridad alrededor de la escritura, y el
alcance que se le atribuyó.

**Imprecisiones del informe, anotadas sin rebajar el hallazgo:** el §0 del objeto decía
«cuatro operaciones» donde la tabla define cinco (corregido en la rev. 4); y el revisor no pudo
acreditar «sin haberlo llamado nunca» por falta de historial, cosa que declaró correctamente —
esa afirmación la sostengo yo, que soy quien no lo llamó.
