---
estado: propuesto (R4 adjudicada; REQUIERE-REVISION, pendiente rev. 6)
dueño: Nikolai Tyukhay
fecha: 2026-08-15
revision: "5"
---

# Diseño — Apertura integral sobre componentes existentes

> **Fuente única del diseño de apertura integral.** Esta spec reúne en un solo documento la
> apertura, el descubrimiento de fuentes, el intake, las salas, el prerrelleno y los dos
> CRM. No se crearán specs separadas por adaptador. Las specs anteriores siguen siendo
> antecedentes o contratos internos de cada componente. En el orden E2E, los gates y el
> cierre solo prevalecen las sustituciones expresas adjudicadas en el §16; una omisión no
> deroga una regla anterior.
>
> **Naturaleza:** diseño. No autoriza todavía la implementación. R1 y R2 terminaron
> `NO-SHIP`; sus diecisiete hallazgos están adjudicados y remediados en esta rev. 3
> (§§18-19), que queda **pendiente de R3**. Solo después de adjudicar una R3 favorable
> podrá escribirse el plan único de implementación.

## 1. Problema y decisión

La apertura real de un expediente exige coordinar piezas que ya existen pero hoy se
ejecutan de forma manual y con estados incompatibles: Gmail, Drive E&V, LeadHub, el CRM
Sudespacho, la sala de máquina, la sala de lectura y el informe de viabilidad. En la
apertura usada como banco de pruebas aparecieron omisiones y falsos positivos porque el
runbook no imponía técnicamente el orden ni una verificación material de cada fase.

La primera decisión es **completar y cablear los componentes existentes**, no crear un
orquestador que duplique lógica todavía incompleta. `scripts.abrir_caso` conserva el alta
inicial; `scripts.crm_ficha` conserva la ficha completa; los entrypoints vigentes de
correo, sala de máquina, sala de lectura y viabilidad conservan sus responsabilidades.

Solo después de que cada componente cumpla por separado sus invariantes podrá justificarse
un coordinador fino, reanudable e idempotente. Ese coordinador, si la prueba E2E demuestra
que sigue siendo necesario, se limitará a ordenar llamadas, conservar estado y presentar el
resultado; no incorporará reglas de identidad, CRM, intake ni procesamiento documental.
Una autorización inicial podrá cubrir los efectos ordinarios. El trabajo mecánico se
ejecutará sin supervisión, con staging disjunto y una sección crítica protegida desde la
primera entrega por el mutex interproceso corto y el protocolo durable de §§6-7. Solo se
detendrá ante riesgo de mezclar expedientes, una identidad materialmente dudosa, un estado
de workspace no admitido, una recuperación no reconciliada o una decisión jurídica.

El flujo no decide la viabilidad. Prerrellena datos y evidencia; el veredicto y el
recuadro ejecutivo permanecen reservados al abogado.

## 2. Alcance y fronteras

El diseño coordina cuatro sistemas probatorios externos y un adaptador auxiliar de
enriquecimiento postal, que conservan contratos distintos:

1. **Gmail de Engel & Völkers:** descubrimiento expansivo, etiquetado y exportación fiel.
2. **Drive de Engel & Völkers:** fuente de la carpeta operativa de la propiedad.
3. **LeadHub de Engel & Völkers:** lectura y captura probatoria mediante el proyecto
   autónomo `FeesDefender-crm`.
4. **Sudespacho:** CRM del despacho; alta, ficha completa, relaciones y descarga del
   gestor documental a `00_Input/05_CRM/`.
5. **Fuentes postales oficiales:** consulta mínima y de solo lectura a la lista cerrada
   del §8.1; no son fuente de identidad ni una vía abierta de investigación.

LeadHub y Sudespacho son adaptadores diferentes. Nunca se denomina a Sudespacho «CRM de
Engel» ni se mezclan sus modelos de identidad, credenciales o salida.

Incluye:

- apertura o reutilización del expediente;
- alta y ficha completa de Sudespacho;
- descubrimiento repetido de toda la evidencia relacionada;
- intake trazable desde las cuatro fuentes probatorias;
- sala de máquina, sala de lectura y prerrelleno de viabilidad;
- invalidación, reanudación y cierre verificable.

No incluye:

- el juicio jurídico de viabilidad;
- la redacción de escritos;
- acciones de comunicación, edición o mutación en LeadHub;
- almacenamiento o automatización de contraseñas;
- fuentes postales comerciales abiertas o no contratadas;
- un motor externo de workflows.

## 3. Arquitectura y regla de reutilización

Se mantiene la arquitectura del proyecto:

- **`core/`**: modelos, identidad, reglas de invalidación, invariantes y contratos de
  adaptadores;
- **`scripts/`**: CLI finos existentes que traducen parámetros, autorizan efectos y
  presentan estado;
- **skills/adaptadores**: ejecutan capacidades existentes sin duplicar su lógica.

La primera entrega reutiliza estas interfaces:

```powershell
python -m scripts.abrir_caso ... --yes
python -m scripts.crm_ficha --case-id <W-code> --yes
```

No se crea `scripts.apertura_expediente` en la primera entrega. Añadir un CLI coordinador
exige antes una prueba E2E que muestre qué estado o reanudación no pueden resolver los
entrypoints actuales. `--yes` no autoriza resolver en silencio una ambigüedad de identidad,
una colisión de contenido o una decisión jurídica.

La primera vertical mutante queda deliberadamente limitada a Drive canónico. En un caso
**existente**, el frontmatter debe declarar expresamente `estado_repositorio: disponible`:
ausencia, corrupción o error de lectura no heredan el default retrocompatible de
`leer_estado_repositorio`, sino que bloquean como `workspace_no_soportado` con motivo
`estado_ausente_o_ilegible`. `prestado`, `conflicto`, un checkout local o `local_scratch`
también bloquean con cero efectos.

Un caso **genuinamente nuevo** no puede leer un `_caso.md` inexistente. Tras demostrar que
no hay candidato en Drive, Sudespacho, checkout ni scratch, adquiere el mutex del W-code y
crea atómicamente la estructura canónica mínima y `_caso.md` con
`estado_repositorio: disponible`; ese es el único efecto local permitido antes del gate y
ningún servicio externo se toca hasta releerlo con éxito. Un caso legacy existente sin el
campo no se confunde con uno nuevo: exige migración explícita fuera de esta corrida. Cuando
exista `CaseWorkspace`, esta restricción se sustituirá por su contrato; hasta entonces no
se imita parcialmente la arquitectura dual.

Un expediente ya abierto se reutiliza siempre por `--case-id` —acepta W-code o identidad
canónica resuelta—. Repetir los flags de alta es una colisión, y `--force` nunca convierte
esa colisión en una carpeta nueva. La reanudación por `--case-id` incorpora únicamente
fuentes nuevas o cambiadas y no emite un segundo POST de alta.

La autorización única `--yes` sustituye el gate por cada escritura CRM de la spec de
2026-07-09 y la revisión humana **previa** de `_ficha_crm.yaml` de la spec de 2026-07-18.
Cuando cada valor tiene la procedencia y concordancia exigidas por el §8.1, la creación o
actualización continúa sin otra pregunta y queda `pendiente_revision_humana`. La revisión
se hace **después en Sudespacho** y no puede omitirse: hasta revisión humana registrada y
GET posterior no existe `crm_ficha_completa` ni se habilita preparar un requerimiento o una
demanda. Una discrepancia material, una identidad o rol dudosos o un dato que exige juicio
jurídico bloquean antes de escribir; `--yes` no resuelve contradicciones.

La nueva entrega no puede hacer regresar capacidades ya construidas en B2–B5:

- `--case-id` para intake incremental, excluyente con los flags de alta;
- autodetección de equipo, código y sufijo desde `--folder-id`, con precedencia de los
  valores explícitos;
- tags de equipo y ciudad durante el alta;
- normalización de teléfonos en los DTO que comparten REST y legacy;
- evento forense `archivado` en `INTAKE_EVENTS`.

No se integra `FeesDefender-crm` por importación. Mientras su recolector y su contrato de
solicitud/resultado no existan, la apertura solo registra el handoff piloto y la recepción
del paquete conforme al §6.3; no finge una invocación automática ni una entrega completa.

## 4. Identidad y preflight

Antes de escribir:

1. Verificar entorno canónico, unidades montadas, ejecutables, permisos y disponibilidad
   de los cuatro adaptadores probatorios y, si hace falta, del adaptador postal auxiliar.
2. Cargar secretos mediante un único proveedor de credenciales de Windows, sin imprimir
   valores ni depender de que la variable haya sido heredada por el proceso actual.
3. Leer el correo inicial y su hilo.
4. Derivar W-code, ciudad, equipo, tipo canónico y dirección.
5. Buscar candidatos existentes en Drive y Sudespacho.
6. Resolver una sola identidad canónica y fijarla para toda la ejecución.
7. Clasificar la resolución como `existente`, `nuevo` o `legacy/error`. En `existente`,
   leer el valor explícito y exigir `estado_repositorio: disponible`; en `legacy/error`,
   bloquear sin defaults; en `nuevo`, adquirir el mutex, inicializar atómicamente el caso
   canónico con ese valor y releerlo. Cualquier checkout o scratch bloquea antes de toda
   escritura; la inicialización nueva precede solo a efectos remotos.

Se bloquea la apertura si el mismo W-code presenta varios frentes incompatibles, si hay
más de un expediente candidato no reconciliable o si una referencia de Sudespacho no
coincide. Una vez fijada, ningún resolvedor corto puede cambiar la ruta del caso.

El preflight conserva el contrato operativo del §0 del runbook: el pipeline con efectos se
ejecuta desde el repo canónico que contiene `.env` y `.venv`, mediante PowerShell; las
ediciones versionadas permanecen en el worktree asignado; y nunca se barre recursivamente
una unidad `G:` completa para localizar un caso. El modo local no se presenta como cerrado
mientras no exista un checkin probado para un caso nacido sin baseline en Drive. En esta
primera entrega el modo local no se ejecuta: se bloquea conforme al punto 7.

La clasificación `nuevo` se prueba por ausencia concordante en todos los resolvedores, no
por la falta de `_caso.md` en una ruta elegida. Si existe carpeta, referencia remota,
checkout, scratch o lectura fallida, no se inicializa nada. La creación mínima usa temp +
`os.replace`, el mutex por W-code y readback antes de liberar el lock.

La política de colisión queda fijada así:

- un código de equipo repetido con W-code nuevo es normal y queda cubierto por `--yes`;
- un W-code ya existente no autoriza crear otra carpeta: el intake incremental entra por
  `--case-id`;
- `--force` solo puede reutilizar el mismo caso canónico ya resuelto por `--case-id`; nunca permite crear
  una sombra plana ni saltarse una discrepancia de referencia;
- varios expedientes CRM con el mismo W-code se tratan como posibles frentes distintos y
  exigen decisión del abogado sobre el alcance.

## 5. Alta inicial

El alta es idempotente:

- crear o reutilizar la estructura canónica del expediente en Drive;
- crear o reutilizar la ficha mínima de Sudespacho;
- calcular el nombre candidato de la etiqueta Gmail, sin crearla hasta confirmar la rama
  judicial o extrajudicial;
- persistir los identificadores externos;
- registrar por separado `crm_alta`, `crm_ficha_pendiente`,
  `pendiente_revision_humana`, `crm_ficha_completa` y
  `escritura_resultado_desconocido`.

El dominio monetario canónico es un decimal no negativo de escala máxima 2, transportado
como `Decimal` o cadena decimal canónica; el CLI no lo convierte a `float`. El adaptador
solo envía céntimos si una prueba de contrato demuestra que el campo `Moneda` de
Sudespacho los conserva por POST/PUT y GET. Mientras esa capacidad no esté demostrada, el
subdominio admitido por la integración es el euro entero: un valor fraccionario bloquea la
escritura con error explícito. Nunca se redondea, trunca ni aproxima en silencio. Después de
cada escritura se exige una lectura de verificación y comparación decimal; un `2xx` no
basta.

### 5.1 Alta mínima y ficha diferida

El alta inicial no completa ni da por verificada la ficha del contrario. En este momento
todavía no se han materializado ni leído los documentos de Drive E&V y no existe base
suficiente para decidir quién firmó el encargo, quién es el deudor ni cuál es su domicilio
de requerimiento. Los datos del correo inicial se conservan como candidatos, no como ficha
confirmada.

Sudespacho puede recibir únicamente el expediente mínimo. El flujo registra `crm_alta` y
`crm_ficha_pendiente`; no crea ni actualiza un cliente contrario a partir del aviso inicial.
La ficha completa se difiere al paso 8.1.

Los entrypoints actuales de alta y ficha completa solo cubren de extremo a extremo la rama
extrajudicial. Si el caso nace judicial, el flujo usa `--crm skip`, no crea un extrajudicial
fantasma y registra `adaptador_no_disponible` con motivo `rama_judicial` hasta que exista un camino judicial
equivalente y verificado. El alta manual o parcial no permite declarar `crm_alta` ni
`crm_ficha_completa` sin readback del expediente judicial correspondiente.

### 5.2 Resultado remoto desconocido

Antes de cada POST de alta se persiste una intención durable con `operation_id`, tipo de
efecto, elemento, W-code, referencia canónica, importe exacto, revisión esperada y estado
`en_curso`. Esa intención se escribe antes de la llamada remota y solo pasa a `completada`
después del GET de verificación. Si la petición pudo alcanzar Sudespacho pero no llega
una respuesta verificable —incluido timeout después de commit remoto—, el resultado queda
`escritura_resultado_desconocido`: no se registra `crm_alta`, no se imprime una apertura
completa y no se repite el POST.

Toda reanudación consulta primero Sudespacho por elemento y referencia canónica. Exactamente
un candidato compatible se adopta solo después de GET y se enlaza al caso; más de uno
bloquea por posible duplicado; cero candidatos permite un nuevo POST únicamente después de
una consulta remota concluyente. Si la consulta no está disponible, el estado desconocido
persiste. El mismo contrato se aplica a cualquier escritura no idempotente cuyo resultado
se pierda.

## 6. Descubrimiento paralelo

Después de fijar la identidad pueden arrancar en paralelo el descubrimiento y las descargas
de las cuatro ramas, pero cada una escribe solo en un staging propio identificado por
`run_id` y fuente. En la primera entrega ningún proceso paralelo incorpora directamente a
`00_Input` ni escribe `_intake_hashes.json`, `_intake_log.jsonl`, `_caso.md` o
`estado.json`: esos commits atraviesan el mutex interproceso corto por caso del §7. La
exclusión se prueba con dos procesos solapados; una cola en memoria o `os.replace` no
cumplen el contrato.

### 6.1 Gmail E&V

La búsqueda no presume que el correo que anuncia la contingencia sea el único. Busca por:

- W-code y variantes seguras;
- dirección;
- partes e identificadores de contacto;
- importes;
- enlaces o IDs de Drive;
- asuntos relacionados;
- listas institucionales como UT PBC, Legal y sus equivalentes por ciudad.

Los candidatos se agrupan por hilo. Para incluir tráfico recibido por una lista de
distribución se exige además una señal propia de la operación, evitando contaminar el caso
con mensajes masivos de otras ciudades. Un mismo asunto puede abarcar varios `thread_id` y
una etiqueta preexistente se audita por contaminación cruzada antes de exportarla.

Los hilos confirmados quedan identificados durante el recon. La etiqueta canónica se crea,
renombra o aplica solo cuando la rama judicial o extrajudicial está confirmada; si ya se
conoce durante el recon, puede hacerse entonces, y si depende de la lectura documental se
espera. Después de aplicar esa etiqueta se exportan los mensajes como EML fieles con sus
adjuntos. Se conserva la jerarquía, color y mecánica de `rename_label` del §6 del runbook.

### 6.2 Drive E&V

Se descarga la carpeta de la operación con la identidad ya fijada a un staging nuevo. El
adaptador entrega inventario remoto, ocurrencias, hashes y errores; no decide por sí mismo
que el caso está completo. Cada vuelta de estabilización ejecuta una consulta remota real:
la presencia de `.pulled`, una caché o un inventario local nunca cuenta como comprobación
sin novedad. Si Drive no responde, la fuente queda `no_consultada` o `fallida` y esa vuelta
no avanza el punto fijo.

Drive conserva en la primera entrega la semántica única de **espejo versionado**, no la de
lote inmutable. La descarga no escribe `--inplace` sobre el espejo vigente: primero compara
el staging con la generación publicada y, durante el commit serializado, preserva byte a
byte toda versión que vaya a ser reemplazada en el historial content-addressed del espejo,
con su ruta, hash y generación. Una retirada remota produce tombstone y conserva los bytes
anteriores; nunca los borra. Solo después se publica la nueva generación. El manifiesto
distingue versión vigente, versiones históricas y tombstones, de modo que ninguna versión
procesada se pierde y Drive no se describe a la vez como espejo mutable y lote inmutable.

### 6.3 LeadHub E&V

La integración se mantiene como **handoff asíncrono en régimen piloto**. El despacho entrega
la lista cerrada de referencias; la captura de solo lectura ocurre en un perfil dedicado y
el paquete vuelve para recepción y reverificación. No es una rama local automatizada.

Durante el piloto el operador principal es **Nikolai Tyukhay con sus propias credenciales**;
subsidiariamente puede ejecutarla **Marta Reynares con las suyas**. Esta decisión es
provisional y ya está autorizada antes de la medición por la excepción §2.1 del contrato de
`FeesDefender-crm`, versión 3.7, commit `8bc09ea`. La vía Nikolai solo ejecuta el arnés de
medición y no produce ni entrega un paquete probatorio; Marta conserva la captura probatoria
ordinaria. Los resultados servirán para proponer después el contrato definitivo.

En cada vía se registran, sin credenciales: actor presente, cuenta y rol confirmados en
pantalla, tiempo total, tiempo activo del operador, número y clase de intervenciones
manuales, referencias solicitadas, artefactos esperados/obtenidos y cobertura por sección.
Una ejecución con Nikolai no demuestra automatización, y una captura coherente no acredita
completitud del universo de contactos. La misma pasada, cuando el recolector exista, sirve
para uso operativo y para el paquete probatorio e incluye:

- propiedad;
- contactos relevantes;
- leads;
- actividades;
- registro de cambios;
- exposé y demás artefactos fijados por su diseño;
- PDF, transcripción, datos estructurados, diligencia y manifiesto.

La salida identifica cuenta, rol y persona ejecutora. Se mantienen la lista blanca de
operaciones GraphQL de lectura, el bloqueo de mutaciones, la prohibición de coordenadas y
de controles de comunicación o edición, el fallo ruidoso ante cambios de interfaz y la
puerta humana de entrega del repositorio hermano.

El paquete se deposita en un lote canónico nuevo:

```text
00_Input/AAAA-MM-DD_leadhub_NN/
```

Para ello se añade `leadhub` al catálogo de fuentes de intake, con su evento propio,
manifiesto y hashes. No se reutiliza `05_CRM`, que pertenece exclusivamente a Sudespacho.

El perfil dedicado es un directorio de navegador aislado del perfil cotidiano. El operador
presente introduce sus propias credenciales en la ventana, pero el script nunca las recibe;
solo se conserva la sesión resultante mientras siga vigente. Una sesión abierta en el
Chrome habitual no demuestra que el perfil dedicado esté autenticado y no se migran cookies
entre perfiles ni entre operadores.

El adaptador debe negociar capacidades antes de prometer una captura. A fecha de esta spec,
`FeesDefender-crm` contiene el arnés de medición y sus guardas, pero no el recolector ni el
empaquetado probatorio completos. `scripts/medir.py`, además, usa referencias de censo fijas:
no puede presentarse como descargador parametrizable. Hasta que el contrato de resultado
esté implementado y probado, el handoff usa `espera_operador_ev`, `espera_entrega` o
`adaptador_no_disponible`, nunca `completada`. Un paquete entregado pasa primero a
`recibida_pendiente_reverificacion`; solo la comprobación local de manifiesto, hashes,
actor/cuenta y cobertura permite registrarlo como recibido. Las demás ramas continúan y el
caso puede quedar `preparado_con_pendientes`, pero no `completo`.

### 6.4 Sudespacho

Se usa directamente `pull_expediente_v2`; ningún coordinador reproduce su lógica.

Para cada expediente vinculado:

1. Verificar como gate que su W-code coincide con el caso.
2. Invocar el pull con el `element` correcto y `physical_complete=True`.
3. Exigir `documents_failed == 0` y ausencia de errores materiales.
4. Reconciliar documentos listados, materializados y deduplicados.
5. Registrar la fotografía del gestor documental.

Una ficha recién creada sin documentos es un resultado válido. Una ficha preexistente
vacía o consultada con el `element` equivocado exige diagnóstico explícito.

## 7. Intake, deduplicación y procedencia

Gmail, LeadHub y las demás fuentes de entrega producen lotes inmutables. Drive E&V conserva
una sola semántica de espejo versionado. Su proyección vigente sigue en
`00_Input/01_Drive EV/` y el historial vive en:

```text
00_Input/_versiones/drive_ev/objetos/<sha256>
00_Input/_versiones/drive_ev/generaciones/<generation_id>.json
```

El registro central de controles excluye ese historial del corpus vigente, pero no de la
custodia. Cada manifiesto de generación mapea ruta remota a hash, tamaño, estado vigente o
tombstone y generación anterior. Sudespacho conserva la copia física completa de su
fotografía y no se presenta como lote. El flujo:

- verifica nombres de destino únicos antes de copiar;
- calcula SHA-256 después de materializar;
- deduplica entre fuentes por contenido sin perder la procedencia ni las ocurrencias;
- conserva alias cuando el mismo documento aparece en correo, Drive o CRM;
- impide que el truncado de nombres sobrescriba dos EML distintos;
- registra entradas, salidas y errores en el manifiesto o ledger propio del componente,
  sin incluir cuerpos documentales.

Cada staging se valida por separado. La incorporación a `00_Input`, la publicación de una
generación del espejo y toda escritura de manifiesto, log, `_caso.md` o `estado.json` se
hacen en una sección crítica protegida por un mutex interproceso corto por caso desde la
primera entrega. Todos los entrypoints que puedan publicar adquieren la misma primitiva,
con propietario y nonce verificables, espera acotada y recuperación segura del abandono
tras crash; liberar exige demostrar titularidad. El lock de checkout/checkin no se reutiliza
mientras sus defectos caracterizados sigan abiertos. La atomicidad de `os.replace` no se
toma como protección frente a lost updates. Una prueba con dos procesos realmente
solapados debe conservar la unión íntegra.

La exclusión no vuelve atómico un conjunto de ficheros. Cada incorporación o efecto remoto
usa además un protocolo durable mínimo:

1. persistir `operation_id`, conjunto esperado, generación y estado `en_curso` antes de
   publicar bytes o llamar al remoto;
2. marcar inválidas las fases derivadas antes de exponer una generación nueva;
3. publicar bytes o ejecutar el efecto, registrando el mismo `operation_id` en cada
   artefacto afectado;
4. escribir manifests, log, `_caso.md`, YAML y `estado.json` en el orden específico de la
   operación, con el estado global todavía no completado;
5. reconciliar disco y servicio remoto mediante inventario, GET o readback material;
6. marcar la operación `completada` siempre al final.

Al arrancar, toda operación `en_curso` o de resultado desconocido se reconcilia antes de
continuar. Un manifest corrupto o una línea corrupta del log bloquean y se preservan para
diagnóstico: nunca se convierten en manifest vacío ni se saltan. Las pruebas inyectan un
crash después de cada frontera, incluidas Gmail, Drive, Sudespacho, archivo y la proyección
Sudespacho → YAML → `_caso.md`.

La deduplicación en `00_Input` es lógica: cada fuente conserva su copia fiel y su ocurrencia,
aunque el hash coincida. La sala de lectura sí puede materializar una sola copia por hash y
representar el resto como alias. En particular, nunca se incumple la copia física completa
de `00_Input/05_CRM/`.

Se conservan además las invariantes de custodia del diseño de 2026-07-09:

- el archivo crudo de intake no se borra; solo se eliminan temporales regenerables;
- los nombres originales se preservan en `00_Input`;
- todo depósito se hashea después de materializarse y se registra en `_intake_log.jsonl`;
- el lock del caso se respeta con write-then-verify; un caso prestado no recibe escrituras
  directas;
- `90_Notas personales/` no se lee ni se escribe.

### 7.1 Intake incremental y CRM existente

Toda fuente adicional entra por `scripts.abrir_caso --case-id <ref> --crm skip`. El modo
incremental no repite los flags de identidad ni puede dar de alta otro expediente CRM. Si
el expediente ya existía en Sudespacho, se registra primero en `_caso.md` con su `element`
correcto y después se ejecuta `pull_expediente_v2` por cada expediente vinculado. Registrar
el ID no sustituye la descarga. El pull y la atomización de correos terminan antes de la
sala de máquina.

## 8. Procesamiento y orden vinculante

Solo cuando termina la primera ronda de intake se ejecuta esta secuencia:

1. Atomizar correo y adjuntos.
2. Ejecutar y verificar la sala de máquina vigente.
3. Ejecutar y verificar la skill canónica de sala de lectura.
4. Prerrellenar y verificar el informe de viabilidad, o registrar
   `no_aplica_confirmado` si el tipo canónico está fuera de
   `core.config.INFORME_VIABILIDAD_TIPOS`.
5. Crear o actualizar y releer la ficha de Sudespacho: cliente propio, contrario y
   colaboradores; dejarla `pendiente_revision_humana`.
6. Tras la revisión humana en el CRM, ejecutar GET y sincronizar el resultado revisado a
   `_ficha_crm.yaml` y `_caso.md`; solo entonces declarar `crm_ficha_completa`.

Está prohibido encadenar `core.pipeline.run`, `core.sala_lectura` o cualquier motor
documental jubilado. Los entrypoints vigentes forman una lista blanca central. Ninguna
fase se completa por el mero código de salida cero: debe satisfacer sus invariantes
materiales y producir manifiesto.

Antes de lanzar `sala_maquina apply` se comprueba que no exista otra corrida activa y se
lee su salida real; nunca se deduce que terminó por el tiempo transcurrido. Una reconstrucción
forzada parte de una fotografía fresca de `00_Input` y detecta derivados huérfanos que el
motor actual no poda. Antes de volver a verde, la reconciliación compara el manifiesto
derivado con la generación activa: mueve a historial o marca inactivos los derivados cuyo
hash ya no esté vigente y los excluye de índices, cobertura, sala de lectura y consumidores.
No borra crudo ni historia. Si un texto sale roto tras el split, se contrasta primero con la
extracción del PDF de origen antes de atribuir el defecto al pipeline.

Esta regla sustituye parcialmente solo la consecuencia operativa de «solo añade; nunca
borra» de los contratos de sala de máquina y sala de lectura: los bytes previos se siguen
conservando y el crudo continúa intocable, pero una copia obsoleta ya no permanece en la
**generación activa**. La retirada activa se implementa por historial versionado o marca de
inactividad, nunca por borrado irreversible.

Antes de regenerar derivados, la fase detecta ficheros temporales de Office (`~$*`) y prueba
la apertura exclusiva de cada destino que vaya a reemplazar. Un derivado bloqueado conserva
la publicación anterior, registra `pendiente_reintento` y no contamina el inventario. La
ejecución no cierra Word ni mata procesos del usuario.

El prerrelleno cita evidencia localizable, conserva los datos desconocidos como tales y
deja siempre en blanco `VIABILIDAD` y el recuadro ejecutivo.

La aplicabilidad se deriva únicamente del catálogo canónico
`INFORME_VIABILIDAD_TIPOS`. Para `BAD_DEBT`, `LAU_20`, `DEVOLUCION_RESERVA` y
`DEVOLUCION_HONORARIOS` el estado normal es `no_aplica_confirmado`: no se fabrica un XLSX
vacío ni se bloquea la ficha CRM. Una excepción solicitada por el abogado puede generar el
informe, pero no cambia la regla automática.

### 8.1 Ficha completa del contrario tras la lectura documental

Esta fase solo empieza cuando los documentos de Drive E&V y las demás fuentes disponibles
se han materializado, la sala de máquina y la sala de lectura están verificadas y la fase
de viabilidad está `completada` o `no_aplica_confirmado`. Cuando existe prerrelleno, debe
permitir localizar la evidencia. El correo que anuncia la incidencia no basta para decidir
la identidad del contrario.

La selección distingue propietario, firmante del encargo y deudor de los honorarios. Se
ancla prioritariamente en el encargo firmado y en los documentos contractuales de la
operación; Gmail y LeadHub sirven para descubrir, contextualizar y contrastar, no para
reemplazar una contradicción documental. Si varias personas pueden ocupar el rol de deudor
o las fuentes discrepan, se fija `pendiente_identidad_contrario` y no se prepara ni envía el
requerimiento.

Cada valor candidato conserva `source_id`, hash del documento o identificador de consulta,
localización dentro de la fuente y valor normalizado. La concordancia automática solo existe
si hay un único valor respaldado o si todos los valores no vacíos normalizan al mismo
resultado. Valores incompatibles de identidad, rol o datos personales bloquean antes del
PUT/POST y exigen decisión; una autorización previa de efectos no elige entre ellos.

La autoridad por campo también es cerrada:

| Campo | Fuentes autorizativas antes de escribir | Sin fuente suficiente |
|---|---|---|
| propietario, firmante y deudor | encargo firmado y documentos contractuales de la operación | `pendiente_identidad_contrario`; Gmail o LeadHub aislados no deciden el rol |
| nombre legal e identificador | encargo/contrato firmado o documento oficial incorporado al expediente | no se crea ni actualiza la persona |
| domicilio | esos mismos documentos; solo para completar CP/provincia, el adaptador postal cerrado | `pendiente_domicilio` |
| email y teléfonos | documento firmado o comunicación directamente atribuida a esa persona | se dejan vacíos; no se infieren |

Una extracción automática debe señalar el fragmento o campo exacto que la sostiene; un
resumen libre o una inferencia del modelo no es ancla. Persiste un riesgo deliberadamente
aceptado: un único valor mal extraído de una fuente autorizativa puede llegar al CRM antes de
que lo vea una persona. La decisión de no reinstaurar aprobación previa no disimula ese
riesgo; lo acota con procedencia, bloqueo de contradicciones y prohibición de uso downstream,
y lo corrige con el gate posterior y la resincronización obligatoria.

Sin que el operador tenga que pedirlo en cada expediente, la ficha candidata incorpora:

- nombre visible completo en `nombre`, aunque el CRM conserve además `1apellido` y
  `2apellido` por separado;
- NIF/CIF/NIE;
- domicilio postal completo;
- código postal;
- población;
- provincia;
- email y teléfonos cuando consten.

La redundancia del nombre es deliberada: las vistas de listado y detalle de Sudespacho solo
renderizan `nombre` y omiten los apellidos separados. Todos los campos de texto libre se
normalizan en mayúsculas; el email, en minúsculas; el NIF/CIF/NIE, en mayúsculas; y los
teléfonos, según el formato admitido por la API. Los campos `Select`, como `provincia`, se
escriben con el literal exacto del enum de Sudespacho y se renderizan en mayúsculas en los
escritos.

Si el código postal o la provincia no constan en la documentación, el adaptador puede
consultarlos a partir del domicilio. La lista cerrada inicial es: (1) documentos del propio
expediente, sin salida externa; (2) localizador oficial de **Correos**; y (3) **Sede
Electrónica del Catastro**. «Fuente pública equivalente» deja de ser autorización. Las
fuentes comerciales abiertas o no contratadas están prohibidas; añadir una fuente exige
modificar la lista, documentar base y condiciones de uso y aprobar su contrato de
tratamiento antes de ejecutarla.

La consulta externa envía solo componentes postales —vía, número, localidad/provincia si
constan—, nunca nombre, identificador, W-code ni naturaleza del asunto. La ficha local del
caso conserva consulta, fuente, resultado y confianza. El log técnico conserva únicamente
fuente, instante, nombres de campos enviados, un `query_id` opaco y no derivable del
domicilio, y la categoría de resultado; no guarda hash de la consulta, URL con parámetros,
respuesta cruda, cookies ni cuerpo de página. La telemetría de terceros queda desactivada.
Perfiles, cachés y respuestas temporales se eliminan al terminar; todo log técnico
transitorio, de éxito o fallo y sin contenido crudo, se elimina en un máximo de 7 días. La
evidencia mínima de auditoría se separa de ese log y permanece con el expediente bajo su
política de conservación. Si hay resultados
incompatibles, varias coincidencias o una dirección insuficiente, se fija
`pendiente_domicilio` y se bloquean requerimiento y demanda.

La identidad normalizada se proyecta siempre a tres destinos:

1. **`_caso.md`:** ficha maestra local. Mantiene `meta.cliente` y `meta.contraparte` como
   resúmenes retrocompatibles y conserva la ficha completa en `meta.partes.contrario`. La
   actualización modifica también `## Partes`, sin perder `## Navegación` ni contenido del
   abogado.
2. **`_ficha_crm.yaml`:** entrada operativa y reanudable del adaptador de Sudespacho.
3. **Sudespacho:** ficha remota vinculada al expediente.

`scripts.crm_ficha` es el único punto de cableado extrajudicial: carga y normaliza la ficha
anclada, completa `_caso.md`, crea o actualiza el contrario aunque ya existiera y verifica
por GET todos los campos. La proyección candidata registra en `estado.json` una
`candidate_revision` y los digests esperados de YAML, `_caso.md` y GET. Tras ese GET el
estado obligatorio es
`pendiente_revision_humana`, no `crm_ficha_completa`. `core.case_manager` expone una
operación pequeña de sincronización que reutiliza su escritura atómica y no absorbe lógica
de CRM.

Los tags de equipo y ciudad permanecen en el alta. La ficha completa vincula el cliente
propio correcto, el contrario, los colaboradores propios de E&V y las notas iniciales. Un
procurador o letrado de la parte contraria nunca se clasifica como colaborador. La actuación
facturable solo se crea cuando proceda y se vincula expresamente; la tarifa sigue reservada
a la UI. Cuando se implemente la rama judicial, Juzgado y autos deberán tratarse mediante su
relación intermedia y sus enums propios; no se inventarán campos planos ni se confundirán
NIG, referencia propia y número de autos. Hasta entonces se aplica el bloqueo del §5.

Un campo vacío de `_caso.md` se completa automáticamente. Dos valores no vacíos de fuentes
independientes e incompatibles no se sobrescriben en silencio: producen
`pendiente_sincronizacion`. Después de la escritura automática, una persona revisa la ficha
dentro de Sudespacho y registra actor, instante, `candidate_revision`, ID remoto y digest o
versión remota exacta que vio —ETag o `updated_at` cuando el API los ofrezca; en su defecto,
hash canónico de todos los campos materiales del GET—. Si no corrige nada, un GET posterior
debe coincidir con esa attestación y campo por campo con YAML y `_caso.md`. Si corrige en el
CRM, el humano confirma la nueva versión y ese GET atestado se resincroniza en dirección
**Sudespacho → `_ficha_crm.yaml` → `_caso.md`**. Cualquier mutación remota posterior o
diferencia no atestada exige nueva revisión; nunca se adopta como «corrección humana» por
mera cronología. Un CAS puede sustituir exclusivamente los valores y digests de la
`candidate_revision` esperada; un cambio local o documental independiente desde esa
revisión bloquea en `pendiente_sincronizacion`. La proyección completa el protocolo durable
del §7 y una nueva lectura verifica la igualdad final. Solo entonces queda
`crm_ficha_completa`.
Mientras exista `pendiente_revision_humana`,
`pendiente_sincronizacion` o discrepancia posterior, ningún entrypoint puede preparar o
enviar requerimiento ni demanda.

Las relaciones tienen un contrato distinto. Mientras no exista readback fiable, una
relación ya intentada no se vuelve a enviar automáticamente al reanudar: el flujo registra
`escritura_sin_readback` y no afirma idempotencia ni `crm_ficha_completa`. Solo una lectura
verificable o una operación de vínculo demostrablemente idempotente permite cerrar ese
subgate. La ausencia de readback no se maquilla con un nuevo POST ciego.

## 9. Bucle de estabilización

Después del primer procesamiento se vuelven a consultar Gmail, Drive, LeadHub y
Sudespacho. Cada vuelta registra una consulta efectiva por fuente. En Drive implica una
consulta remota nueva que ignora `.pulled`; en LeadHub, mientras siga como handoff, implica
comprobar una entrega o estado nuevo del operador, no releer el estado local. Una fuente
saltada, no disponible o servida solo desde caché no cuenta como «sin novedad». Si aparece
evidencia nueva:

- un nuevo fichero de intake invalida sala de máquina, sala de lectura y prerrelleno;
- una nueva extracción invalida sala de lectura y prerrelleno;
- una nueva evidencia citada invalida el prerrelleno;
- un nuevo dato material sobre partes invalida la ficha del paso 8.1 y cualquier
  requerimiento derivado;
- un cambio de identidad invalida toda la ejecución y exige intervención.

En la primera entrega no hay un grafo parcial de dependencias: cualquier cambio de fuente
incrementa la generación global e invalida todas las fases derivadas. Esta regla conservadora
hace observable la reanudación con el estado mínimo; una optimización por vector de snapshots
queda diferida hasta que el E2E demuestre que hace falta. El caso alcanza estado estable tras dos rondas
consecutivas, sobre la misma generación de entrada, en las que todas las fuentes obligatorias
han sido consultadas realmente, no hay novedad y las invariantes están verdes. Una fuente
`no_consultada`, `fallida`, `espera_operador_ev` o `espera_entrega` impide `completo`; puede
dar `preparado_con_pendientes`, pero no incrementa su contador de ausencia de cambios. El
punto fijo y la generación que lo sostiene se persisten conforme al §10.

Cada adaptador define de forma cerrada su fotografía material: Gmail incluye IDs de hilo y
mensaje más hashes de EML/adjuntos; Drive, ruta, ID/versión remota, hash, tamaño y tombstone;
Sudespacho, expediente, documentos, versiones y campos materiales; LeadHub, referencias,
cuenta/rol, cobertura y artefactos recibidos. Sustituir contenido bajo el mismo ID o ruta
cambia la fotografía. Cada attestación lleva `round_id`, generación e instante; el contador
solo avanza cuando una actualización atómica incorpora todas las fuentes obligatorias y
frescas de esa misma ronda. Se conservan las dos attestations completas que acreditan el
punto fijo —o una cadena de digests equivalente que permita reproducirlas—.

### 9.1 Archivo por decisión jurídica

El flujo no decide que un asunto es inviable. Si el abogado ordena archivarlo, se conserva
el contrato del §10 del runbook y no se borra nada:

1. marcar el expediente histórico en Sudespacho con motivo y fecha;
2. registrar y vincular la actuación de cierre cuando proceda;
3. renombrar la etiqueta Gmail hacia la rama de archivo conservando sus hilos;
4. mover la carpeta del caso a la rama de archivo de Drive;
5. actualizar estado, motivo y fecha en los dos niveles de `_caso.md`;
6. registrar el evento forense `archivado`.

Cada efecto se verifica antes de ejecutar el siguiente. Un fallo parcial queda reanudable y
no convierte el expediente en `archivado` completo.

## 10. Estado, ledger y recuperación

Cada fuente o fase, según corresponda, puede estar en:

- `pendiente`;
- `en_curso`;
- `completada`;
- `pendiente_reintento`;
- `espera_login`;
- `espera_operador_ev`;
- `espera_entrega`;
- `adaptador_no_disponible`;
- `recibida_pendiente_reverificacion`;
- `vacio_confirmado`;
- `no_consultada`;
- `pendiente_identidad_contrario`;
- `pendiente_domicilio`;
- `pendiente_revision_humana`;
- `pendiente_sincronizacion`;
- `no_aplica_confirmado`;
- `workspace_no_soportado`;
- `escritura_resultado_desconocido`;
- `escritura_sin_readback`;
- `espera_decision_juridica`;
- `fallida`.

La primera entrega no crea una máquina de workflows, pero sí la fotografía mínima que hace
observables la reanudación, la invalidación y el punto fijo:

```text
01_Procesado/_apertura/estado.json
```

Su esquema mínimo y obligatorio es:

```json
{
  "schema_version": 2,
  "case_id": "<identidad canónica>",
  "revision": 1,
  "input_generation": 1,
  "sources": {
    "<fuente>": {
      "status": "pendiente|en_curso|completada|vacio_confirmado|no_consultada|pendiente_reintento|fallida|espera_login|espera_operador_ev|espera_entrega|adaptador_no_disponible|recibida_pendiente_reverificacion",
      "round_id": "<ronda de consulta común>",
      "checked_at": "<ISO-8601>",
      "query_id": "<id sin PII>",
      "snapshot_sha256": "<digest del inventario>",
      "input_generation": 1,
      "changed": false,
      "attempts": 1
    }
  },
  "phases": {
    "<fase>": {
      "status": "pendiente|en_curso|completada|no_aplica_confirmado|workspace_no_soportado|pendiente_reintento|pendiente_identidad_contrario|pendiente_domicilio|pendiente_revision_humana|pendiente_sincronizacion|escritura_resultado_desconocido|escritura_sin_readback|espera_decision_juridica|fallida",
      "input_generation": 1,
      "artifact_sha256": "<digest del manifiesto o resultado>",
      "verified_at": "<ISO-8601>",
      "attempts": 1
    }
  },
  "operations": {
    "<operation_id>": {
      "kind": "<intake|crm|gmail|drive|archivo|proyeccion>",
      "status": "en_curso|resultado_desconocido|completada|fallida",
      "generation": 1,
      "expected": ["<artefacto o efecto>"],
      "started_at": "<ISO-8601>",
      "verified_at": "<ISO-8601 o null>"
    }
  },
  "fixed_point": {
    "generation": 1,
    "consecutive_unchanged": 0,
    "reached": false,
    "attested_rounds": [
      {"round_id": "<id>", "sources_digest": "<sha256>", "completed_at": "<ISO-8601>"}
    ]
  }
}
```

`input_generation` aumenta si cambia la fotografía material de cualquier fuente. Antes de
publicar la nueva generación se persiste su operación `en_curso`; en la misma sección
crítica se invalidan todas las fases derivadas con una generación anterior y se reinicia
`consecutive_unchanged`. Una consulta real sin cambios registra `round_id`, `checked_at`,
`query_id` y digest; una fuente saltada no puede imitarla. Cada actualización usa temp +
`os.replace`, compara `revision` y atraviesa el mutex del §7. Un CAS fallido obliga a releer
y fusionar, nunca a sobrescribir.

Las transiciones son cerradas y separadas por entidad:

- **fuente:** `pendiente → en_curso`; desde `en_curso` solo pasa a `completada`,
  `vacio_confirmado`, `no_consultada`, `pendiente_reintento`, `fallida` o uno de sus estados
  de espera/adaptador/recepción. Un estado no exitoso vuelve a `en_curso` incrementando
  `attempts`; una fuente exitosa vuelve a `pendiente` al abrir una ronda posterior o al
  invalidarse su fotografía. Solo `completada` y `vacio_confirmado`, con consulta real,
  digest y `round_id`, cuentan para punto fijo;
- **fase:** `pendiente → en_curso`; desde `en_curso` solo pasa a `completada`,
  `no_aplica_confirmado`, `fallida` o un estado bloqueante de su enum. Un bloqueo vuelve a
  `en_curso` con nuevo intento; `completada`/`no_aplica_confirmado` vuelven a `pendiente`
  cuando cambia `input_generation`;
- **operación:** `en_curso` termina en `completada`, `fallida` o
  `resultado_desconocido`; este último exige reconciliación y nunca autoriza directamente
  un segundo efecto.

Ninguna transición se infiere por ausencia de fichero o por un control corrupto.

La fase `crm_ficha` añade `candidate_revision`, `candidate_digests` para YAML, `_caso.md` y
primer GET, y `human_review_attestation` con actor, instante, ID remoto y digest/versión
exacta revisada. Son la precondición del CAS posterior; no se sustituyen valores que ya no
correspondan a esa fotografía ni se acepta una versión remota posterior no atestada.

Esta fotografía no sustituye `_caso.md` ni los manifiestos y no ejecuta fases: enlaza
fuente, fase, generación, operaciones durables y verificación material. No se crea un motor
de workflows ni un ledger general adicional: `operations` es el mínimo necesario para
recuperar efectos ya iniciados.

Los fallos transitorios de red, ficheros fríos y respuestas temporales se reintentan con
backoff acotado. La reanudación empieza en la primera fase no válida y no repite efectos ya
confirmados.

## 11. Gates bloqueantes

Se detiene automáticamente ante:

- W-code ajeno o identidad no unívoca;
- más de un frente jurídico incompatible;
- posible contaminación con otro caso;
- colisión de nombres con contenido distinto;
- discrepancia de hashes;
- descarga parcial presentada como completa;
- intento de mutación no autorizada en LeadHub;
- decisión de viabilidad o identidad del deudor no respaldada;
- rama judicial solicitada sin adaptador judicial completo;
- relación CRM sin readback fiable cuando ya consta un intento de escritura;
- escritura CRM con resultado desconocido hasta reconciliación remota;
- ficha `pendiente_revision_humana` o divergente antes de preparar requerimiento o demanda;
- fuente postal fuera de la lista cerrada o consulta que incluya identidad/W-code;
- intento de commit paralelo sobre estado compartido sin lock o CAS probado.

La indisponibilidad del operador o de la entrega LeadHub no detiene las ramas
independientes: genera el pendiente explícito correspondiente y un cierre parcial.

## 12. Fallos observados y controles vinculantes

| Fallo observado | Efecto | Control vinculante |
|---|---|---|
| Runbook no seguido desde el inicio | Fases fuera de orden | Secuencia vinculante de entrypoints y verificación material tras cada uno |
| Ejecución desde worktree sin entorno | Sin venv, secretos o acceso operativo | Preflight del entorno canónico |
| API key no visible en el proceso | CRM falsamente inaccesible | Proveedor único de secretos de Windows, sin imprimirlos |
| Alta mínima confundida con ficha completa | Partes y relaciones ausentes | Estados separados y verificación GET |
| Contrario completado antes de leer Drive E&V | Firmante o deudor inferido desde el aviso | `crm_ficha_pendiente` hasta sala de lectura y prerrelleno verificados |
| Etiqueta Gmail creada antes de clasificar la rama | Reubicación y jerarquía incorrecta | Crear o renombrar solo tras confirmar judicial/extrajudicial |
| Intake incremental usa el default `--crm api` | Expediente extrajudicial fantasma | `--case-id ... --crm skip` obligatorio para fuentes adicionales |
| Cuantía decimal redondeada | Importe erróneo | `Decimal`/cadena canónica; céntimos solo con contrato probado, si no rechazo explícito |
| Resolución por W-code corto desviada | Ruta equivocada | Pin de identidad canónica |
| Uso del motor de sala de lectura deprecado | Layout y derivados incorrectos | Lista blanca de entrypoints vigentes |
| Éxito con sala vacía | Falso positivo | Invariantes materiales de salida |
| Colisión por truncado de dos EML | Sobrescritura silenciosa | Destinos únicos antes de copiar y hash posterior |
| Manifiesto ausente | Imposible verificar sala | Manifiesto obligatorio |
| Verificador CRM sin `PYTHONPATH` | Cobertura final incompleta | Entorno construido por el entrypoint que lo invoca |
| Gmail limitado al aviso inicial | Cadenas UT PBC omitidas | Descubrimiento expansivo obligatorio |
| Evidencia nueva tras el prerrelleno | Salidas obsoletas | Bucle de estabilización |
| Residuo documental sin clasificar | Sala detenida | Clasificación automática; gate solo ante ambigüedad real |
| Split documental incorrecto | Piezas artificiales | Coherencia del split antes de procesar |
| Adjunto de correo repetido en Drive | Duplicación entre fuentes | SHA-256 con procedencia y alias |
| LeadHub fuera del flujo | Datos y prueba omitidos | Handoff piloto obligatorio, con actor/cuenta, entrega y reverificación |
| Pull Sudespacho no cableado | `05_CRM` incompleto | Pull obligatorio previo a las salas |
| Verificación artesanal al final | Defectos tardíos | Verificación local tras cada fase |
| Carpeta exacta pero inválida creada por el resolvedor | Un esqueleto plano oculta el caso canónico por ciudad | Resolución estrictamente de solo lectura; ningún lookup crea carpetas; rechazo de sombras sin identidad válida |
| Pull Sudespacho devuelve `0` documentos, errores y exit `0` | Vacío ambiguo presentado como éxito | Estados distintos `vacio_confirmado`/`fallida`; los errores mandan sobre el recuento |
| Ficheros YAML/JSON de control entran en cobertura | Falsos pendientes y OCR inútil | Registro central y exhaustivo de controles excluidos del inventario probatorio |
| Tesseract escribe error pero el proceso global termina `0` | Extracción incompleta oculta | Resultado material por documento; stderr y cobertura prevalecen sobre el exit global |
| Original legible con OCR vacío | Documento útil tratado como ausente | Revisión visual registrada, sin fingir texto extraído ni alterar el original |
| Sala antigua cuadra con su manifiesto pero viola el layout vigente | Verificación formal de una topología obsoleta | El verificador valida también planitud, taxonomía y ausencia de PII en destinos |
| Mismo adjunto llega por Drive y correo | Doble copia y doble cómputo | Una copia por SHA-256 y todas las ocurrencias/alias en manifiesto |
| Dos EML del mismo hilo comparten basename | Agrupación o colisión incorrecta | Identidad por Message-ID/Thread-ID y ruta relativa, nunca solo por basename |
| DNI y nota simple clasificados por tema en vez de por parte | Sala de lectura jurídicamente confusa | Taxonomía mecánica por parte y función documental antes del bundle |
| `crm_ficha` confirma el principal pero no relee relaciones | Cliente/contrario/colaboradores no verificables | Readback de cada relación o estado explícito `escritura_sin_readback` |
| `_caso.md` conserva cuantía nula tras el alta | Superficies del caso incoherentes | Invariante decimal cruzada entre índice, informe y Sudespacho |
| `crm_ficha` actualiza Sudespacho pero no `_caso.md` | La ficha maestra conserva partes pendientes | Una identidad normalizada se proyecta a los tres destinos y se verifica |
| Contrario preexistente solo se vincula | La ficha antigua permanece incompleta | GET, merge completo, PUT y nuevo GET antes de confirmar el vínculo |
| Reanudación reenvía una relación sin poder leerla | Vínculo duplicado o estado incognoscible | No re-POST; `escritura_sin_readback` hasta disponer de verificación |
| Caso judicial entra por el alta extrajudicial | Expediente fantasma y modelo CRM incorrecto | `--crm skip` y `adaptador_no_disponible` con motivo `rama_judicial` |
| Derivado abierto en Word bloquea la regeneración | Atomización parcial con exit global `0` | Preflight de locks `~$*`, publicación transaccional y reintento dirigido |
| Dos corridas de sala de máquina se solapan | Cobertura fusionada y derivados huérfanos | Gate de proceso activo, salida real y reconciliación de huérfanos |
| Sesión autenticada solo en Chrome cotidiano | LeadHub parece disponible, pero el colector no puede usarla | Perfil dedicado del operador presente; `espera_operador_ev`, `espera_entrega` o `adaptador_no_disponible` |
| Apellidos guardados pero nombre visible incompleto | Listados, ficha y escritos muestran solo el nombre de pila | `nombre` contiene el nombre completo, además de los apellidos separados, y se verifica por GET |
| Contrario sin código postal o provincia | Requerimiento no direccionable con seguridad | Solo Correos/Catastro con minimización; `pendiente_domicilio` bloquea requerimiento y demanda |
| Datos personales con capitalización irregular | Escritos y plantillas inconsistentes | Mayúsculas en texto libre, email en minúsculas y literales exactos para campos `Select` |
| Ramas paralelas escriben estado compartido | Lost update de manifest, log o `_caso.md` | Descargas a staging disjunto y commit serializado; lock/CAS solo si está probado |
| `.pulled` evita volver a Drive | Falso punto fijo | Consulta remota real en cada ronda; caché o skip no cuentan como «sin novedad» |
| Drive reemplaza un fichero del espejo | Se pierde la versión procesada | Historial content-addressed + manifiesto de generación + tombstone antes de publicar |
| Operador LeadHub atribuido al actor equivocado | Diligencia y custodia falsas | Piloto Nikolai/Marta medido por vía; actor, cuenta y rol reales registrados; contrato definitivo pendiente |
| Ficha escrita y tratada como completa sin revisión | Requerimiento o demanda sobre datos no revisados | `pendiente_revision_humana`; revisión en CRM + GET + resincronización antes de completar |
| Timeout después de commit del alta CRM | Duplicado en el reintento | `escritura_resultado_desconocido` y reconciliación por referencia antes de cualquier POST |
| Reanudación sin generación común | Fase verde sobre inputs obsoletos | `estado.json` atómico obligatorio desde la primera entrega |
| Consulta postal abierta o excesiva | Divulgación de PII a terceros | Allowlist cerrada, minimización, sin telemetría, log sin contenido y retención técnica máxima de 7 días |

## 13. Resultado final

El resumen distingue exactamente:

- `completo`: punto fijo acreditado sobre una generación, todas las ramas obligatorias
  verificadas, ninguna escritura remota incierta y ficha CRM revisada por humano + GET;
- `preparado_con_pendientes`: ramas independientes terminadas, con un pendiente explícito
  como `espera_operador_ev`, `espera_entrega` o `pendiente_revision_humana`;
- `bloqueado`: gate material que impide seguir sin riesgo.

Incluye el estado de cada fase, pendientes, número de intentos, inventarios conciliados y
rutas de los manifiestos; no vuelca secretos ni contenido sensible al terminal.

## 14. Criterios de aceptación

> **Alcance vigente (rev. 4).** Estos cincuenta criterios describen la apertura completa.
> La primera vertical exige **veintidós** de ellos; los otros veintiocho quedan
> **diferidos con su vertical**, no exentos. La enumeración y el reparto, en el §21.4.

1. La secuencia documentada de entrypoints existentes completa una apertura normal sin
   pedir datos que puedan obtenerse de las fuentes autorizadas y, en la primera vertical,
   solo después de releer `estado_repositorio: disponible`: explícito en un caso existente
   o escrito atómicamente en la inicialización de un caso nuevo probado.
2. Interrumpir y reanudar en cualquier fase no duplica efectos confirmados ni repite una
   escritura cuyo resultado remoto sea desconocido; cada frontera de crash se reconcilia
   mediante el `operation_id` durable antes de continuar.
3. Ninguna fase se marca completa solo por un código de salida cero.
4. Todo fichero procesado resuelve a una fila de manifiesto y su hash coincide.
5. Ningún destino se repite con hashes distintos.
6. Gmail descubre hilos recibidos por listas institucionales aunque el usuario no participe.
7. El pull de Sudespacho bloquea referencias ajenas y reconcilia el universo listado.
8. LeadHub no ejecuta mutaciones ni acciones de comunicación.
9. Una captura LeadHub incompleta nunca recibe veredicto de entrega completa y el piloto
   registra actor, cuenta, rol, tiempos, intervenciones manuales y cobertura de la vía usada.
10. Cada vuelta consulta realmente Gmail, Drive, LeadHub y Sudespacho; un nuevo correo o
    documento invalida y regenera las salidas dependientes, retira del corpus activo los
    derivados obsoletos y `.pulled` no omite Drive.
11. La cuantía usa decimal exacto de escala máxima 2 en Drive, informe y Sudespacho. Si el
    CRM no demuestra soporte de céntimos, rechaza el valor fraccionario; nunca lo redondea.
12. `VIABILIDAD` y el recuadro ejecutivo quedan en blanco durante el prerrelleno; un tipo
    fuera de `INFORME_VIABILIDAD_TIPOS` registra `no_aplica_confirmado` sin crear XLSX.
13. El resumen final usa uno de los tres estados definidos en §13.
14. La suite E2E reproduce, sin PII, colisiones, intake tardío, ruta desviada, descarga
    parcial, operador/entrega LeadHub pendiente, la matriz Drive disponible/checkout/
    conflicto/scratch, crash después de cada frontera y punto fijo.
15. Un resolvedor no crea estructura alguna y rechaza una carpeta sombra que solo coincide
    por nombre.
16. Los controles internos y temporales `~$*` no cuentan como documentos materiales.
17. La sala de lectura no pasa si su manifiesto cuadra pero el layout, la taxonomía, los
    nombres de destino o la generación activa infringen el contrato vigente.
18. Sudespacho distingue un gestor documental vacío confirmado de una respuesta con errores.
19. LeadHub no se marca disponible mientras solo exista el arnés de medición.
20. Toda ficha de contrario releída por API contiene nombre visible completo, apellidos
    separados, identificador y domicilio con código postal, población y provincia, pero
    permanece `pendiente_revision_humana` hasta revisión atestada contra la versión remota
    exacta y segundo GET coincidente.
21. Los campos de texto libre del contrario quedan en mayúsculas y el email en minúsculas;
    los `Select` conservan el literal exacto del CRM.
22. Una dirección postal incompleta o ambigua impide preparar o enviar requerimiento o
    demanda y produce `pendiente_domicilio`, no un dato inferido silenciosamente.
23. Un código postal resuelto automáticamente usa solo expediente, Correos o Catastro;
    conserva fuente, consulta y confianza en la ficha local, minimiza los datos enviados y
    cumple el contrato de logs/retención del §8.1 sin filtrar PII a Git.
24. `scripts.crm_ficha` sincroniza la identidad candidata en los tres destinos mediante el
    protocolo durable y, tras una corrección humana atestada en CRM, la resincroniza
    Sudespacho → YAML → `_caso.md` y verifica.
25. Un contrario ya existente se actualiza mediante GET, merge, PUT y GET; vincularlo o
    releerlo antes de la revisión humana no se considera ficha completa.
26. La actualización de `_caso.md` modifica frontmatter y `## Partes` de forma atómica,
    conserva `## Navegación` y no sobrescribe valores no vacíos incompatibles.
27. No se crea `scripts.apertura_expediente` mientras los entrypoints existentes no cumplan
    sus contratos y una prueba E2E no demuestre una carencia concreta de coordinación.
28. El alta mínima no crea ni actualiza un contrario a partir del correo inicial y conserva
    `crm_ficha_pendiente` hasta completar las fuentes documentales.
29. La fase 8.1 no comienza antes de materializar Drive E&V y verificar sala de máquina y
    sala de lectura; la viabilidad debe estar `completada` o `no_aplica_confirmado`.
30. Firmante del encargo, propietario y deudor se distinguen; una discrepancia documental
    produce `pendiente_identidad_contrario` y bloquea el requerimiento.
31. La etiqueta Gmail no se crea ni se mueve antes de confirmar la rama judicial o
    extrajudicial y conserva jerarquía, color e hilos.
32. La autorización única sustituye los antiguos gates previos para valores con procedencia
    concordante; una contradicción material bloquea y toda escritura queda
    `pendiente_revision_humana` hasta el gate posterior.
33. Un código de equipo repetido no crea conflicto; un W-code existente entra por
    `--case-id`, no repite el alta CRM ni los hashes ya ingeridos, y `--force` nunca crea
    una carpeta sombra.
34. Todo intake incremental usa `--crm skip`; un expediente CRM preexistente se registra y
    descarga antes de ejecutar la sala de máquina.
35. B2–B5 conservan `--case-id`, autodetección desde `folder-id`, tags de alta,
    normalización telefónica y evento `archivado`.
36. El intake conserva crudo, nombres originales, hashes y locks, nunca toca
    `90_Notas personales/`; un workspace existente no explícitamente `disponible` bloquea
    sin efectos, y el caso nuevo probado solo admite la inicialización local atómica antes
    de cualquier efecto remoto.
37. Dos corridas de sala de máquina no se solapan y una reconstrucción retira del corpus
    activo los derivados huérfanos antes de validarse, conservándolos en historial.
38. Un caso judicial no pasa por los entrypoints extrajudiciales ni puede terminar
    `crm_ficha_completa` mientras falte el adaptador judicial verificado.
39. Una relación CRM sin readback no se reenvía ni se declara idempotente; queda
    `escritura_sin_readback`.
40. El archivo ordenado por el abogado registra intención y readback por cada efecto y
    verifica CRM, actuación, Gmail, Drive, `_caso.md` y evento forense antes de declararse
    completo; cada corte intermedio se reanuda sin repetir lo confirmado.
41. Dos procesos solapados descargan a staging disjunto y atraviesan el mismo mutex por
    caso; sus commits conservan la unión de entradas en manifest, log, `_caso.md` y
    `estado.json`, y un proceso no puede liberar el lock del otro.
42. Sustituir o retirar un fichero Drive conserva los bytes anteriores, la generación y el
    tombstone; solo la generación activa alimenta índices y lectores.
43. La excepción §2.1 de `FeesDefender-crm` está vigente antes de ejecutar la vía Nikolai;
    el piloto mide por separado Nikolai y Marta y no presenta la medición como captura
    probatoria antes de proponer el contrato definitivo.
44. Una ficha con `pendiente_revision_humana` no habilita ningún requerimiento ni demanda;
    revisión atestada contra la versión remota exacta + GET coincidente son necesarios
    incluso cuando el primer GET coincidió.
45. Una corrección humana en Sudespacho se refleja por GET en YAML y `_caso.md`; el CAS
    sustituye la `candidate_revision` y versión remota atestadas, bloquea cualquier cambio
    local, documental o remoto independiente y termina con igualdad verificada.
46. Un test de timeout después del commit remoto deja `escritura_resultado_desconocido`,
    encuentra y adopta exactamente un expediente por referencia y demuestra que no hubo
    segundo POST.
47. `estado.json` existe desde la primera entrega y vincula cada fuente y fase a una
    `input_generation` y `round_id`; conserva las dos rondas atestadas y una fuente saltada
    no incrementa `consecutive_unchanged`.
48. Cambiar la fotografía material de una fuente registra primero una operación durable,
    incrementa la generación, invalida todas las fases derivadas antes de publicar y
    reinicia el punto fijo; un crash nunca deja una fase verde sobre la generación anterior.
49. Los perfiles y respuestas temporales del enriquecimiento postal se eliminan al terminar;
    todo log técnico transitorio, de éxito o fallo, desaparece en un máximo de 7 días y no
    conserva hash ni otro derivado determinista del domicilio.
50. La primera entrega no crea `scripts.apertura_expediente`: el mutex, el gate de workspace,
    `operations` y el estado mínimo se cablean detrás de los entrypoints existentes.

## 15. Estrategia de entrega

> **Sustituido para V1 (rev. 4).** El orden de siete bloques de esta sección presupone la
> vertical ancha. Mientras V1 esté en curso rige el §21.5; esta sección vuelve a aplicarse
> cuando entren V2 y V3.

La implementación se detallará en un único plan y en este orden:

1. Construir el mutex interproceso corto, el gate `estado_repositorio: disponible`, el
   protocolo durable por `operation_id` y `estado.json`; staging disjunto, generaciones,
   rondas atestadas e invalidación, sin crear un CLI coordinador.
2. Cerrar el alta de resultado incierto y el dominio monetario; completar `crm_ficha` con
   procedencia, modelo postal, actualización de registros preexistentes, revisión humana
   posterior, sincronización de `_caso.md` y readback campo a campo, sin romper B2–B5.
3. Cerrar por separado los contratos pendientes de Drive, Gmail, Sudespacho, reconciliación
   de derivados por generación, viabilidad `no_aplica_confirmado` y el piloto LeadHub.
4. Cablear el orden vigente mediante los entrypoints existentes, aplicar la adjudicación
   expresa del §16 y actualizar el runbook sin borrar sus gotchas todavía válidos.
5. Ejecutar una prueba E2E con fixtures sin PII y una apertura real controlada.
6. Medir las omisiones de coordinación que permanezcan.
7. Solo si esa evidencia lo exige, diseñar el coordinador fino o un ledger adicional.

Cada bloque se construirá con TDD. Las integraciones vivas tendrán pruebas de contrato
separadas de la suite rápida y nunca usarán datos reales en fixtures versionados.
Este orden no es autorización para planificar todavía: la rev. 3 permanece pendiente de R3.

## 16. Relación con documentación anterior

Esta spec gobierna el orden E2E y los gates nuevos, pero no deroga en bloque los dos
diseños anteriores ni el runbook. Sus contratos de componente y sus gotchas operativos
siguen vigentes salvo sustitución expresa en esta tabla:

| Fuente y decisión | Estado | Contrato vigente |
|---|---|---|
| 2026-07-09 D1: core compartido y frentes local/Cowork | Conservada | Lógica en `core`; CLIs y skills finos con músculos de I/O distintos |
| 2026-07-09 D2: colisiones `ask`/`--force` | Sustituida parcialmente | Código de equipo repetido queda cubierto por `--yes`; W-code y referencia siguen siendo gates estrictos conforme a §4 |
| 2026-07-09 D3: confirmar cada alta CRM | Sustituida | `--yes` cubre valores con procedencia concordante; las contradicciones bloquean y la ficha queda pendiente de revisión humana posterior |
| 2026-07-09 D4: hash tras materializar | Conservada | SHA-256 y log por fichero en todo intake |
| 2026-07-09 D5: `scripts.abrir_caso` | Conservada | Se completa el entrypoint existente; no nace otro coordinador en la primera entrega |
| 2026-07-18 B1: `crm_ficha` separado después de viabilidad | Conservada y ampliada | Se ejecuta tras la lectura documental, escribe/relee, queda `pendiente_revision_humana` y sincroniza CRM→YAML→`_caso.md` tras la revisión |
| 2026-07-18: revisión humana obligatoria del YAML | Sustituida | No hay aprobación previa: el humano revisa después en CRM; revisión + GET son condición de `crm_ficha_completa` y de cualquier requerimiento/demanda |
| 2026-07-18 B2–B5 | Conservadas | Rige la cláusula de no regresión de §3 y el criterio 35 |
| 2026-07-09 / código vigente: Drive E&V como espejo | Conservada y ampliada | Es un espejo versionado, nunca lote: staging, historial content-addressed, generaciones y tombstones sin pérdida |
| Arquitectura dual de 2026-07-29 | Conservada con restricción temporal explícita | Un caso existente exige Drive explícitamente `disponible`; legacy/error, checkout, conflicto y scratch bloquean. Un caso nuevo probado se inicializa atómicamente en Drive antes de efectos remotos. `CaseWorkspace` sustituirá este gate cuando exista |
| Contrato LeadHub de 2026-07-31 v3.7, commit `8bc09ea` | Excepción piloto autorizada, no sustitución definitiva | Nikolai puede ejecutar solo el arnés de medición sin entrega probatoria; Marta conserva la captura ordinaria. Se miden ambas vías antes del contrato definitivo |
| Sala de máquina 2026-07-09 §8: nunca borra productos previos | Conservada y ampliada | Nunca borra crudo ni bytes históricos; la reconciliación por generación retira productos obsoletos solo del corpus activo mediante historial o marca inactiva |
| Sala de lectura canónica: re-aplicación solo añade y nunca borra | Sustituida parcialmente | Se conserva el crudo y toda copia histórica; se sustituye únicamente que una copia obsoleta siga activa: queda versionada/inactiva y fuera de manifiesto, índices y lectores vigentes |
| Runbook §§0–5: entorno, intake y sala de máquina | Conservados y ampliados | Rigen con la reconciliación por generación declarada en las dos filas anteriores y los nuevos verificadores materiales |
| Runbook §6: momento y mecánica de etiqueta Gmail | Conservado | La etiqueta espera a la clasificación judicial/extrajudicial |
| Runbook §§7–8: sala de lectura y viabilidad | Conservados por referencia | Sus skills canónicas siguen siendo el contrato interno |
| Runbook §9: CRM extrajudicial y gotchas | Conservado | La rama judicial continúa no disponible y las relaciones sin readback no se dan por idempotentes |
| Runbook §10: archivo | Conservado | Se incorpora como §9.1 y criterio 40 |

Por tanto, “prevalece esta spec” significa únicamente: prevalecen su orden E2E y las
sustituciones identificadas en la tabla. Una omisión no deroga una regla anterior. Antes de
retirar o modificar un contrato antiguo, el plan debe señalar la fila que lo adjudica.

Tampoco se duplican los contratos internos de los motores que se componen. Siguen siendo
fuentes técnicas de implementación:

- `docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md`;
- la skill canónica `.claude/skills/organizar-sala-lectura/`;
- la skill canónica `.claude/skills/viabilidad-prerelleno/`;
- `docs/superpowers/plans/PLAN_INTAKE_CRM_COMPLETO.md` hasta que sus requisitos se absorban
  en el plan único;
- `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md`, con la
  restricción temporal expresa de esta spec;
- contrato de descarga de fichas LeadHub del repositorio hermano `FeesDefender-crm`
  (versión 3.7, commit `8bc09ea`).

La implementación actualizará el runbook para reflejar las sustituciones expresas, sin
borrar los gotchas operativos que sigan vigentes ni mantener un segundo diseño divergente.

## 17. Evidencia del piloto W-02Q38C

La apertura del 15 de agosto de 2026 se usó como prueba operativa de esta spec. El registro
versionado conserva solo el W-code; nombres, direcciones, importes identificativos y cuerpos
documentales permanecen fuera de Git.

Resultados que fijan requisitos:

- Gmail pasó de la cadena de incidencia a tres hilos y seis EML al buscar también tráfico
  institucional de PBC. Dos adjuntos ya existían en Drive y se resolvieron como ocurrencias
  del mismo contenido.
- Sudespacho quedó con cliente propio, contrario, tres colaboradores y notas; su gestor
  documental estaba vacío porque el expediente acababa de crearse. La cuantía se verificó
  por lectura y se sincronizó con `_caso.md` y el informe. El API actual no ofrece readback
  suficiente de las relaciones, por lo que ese subgate no puede darse por cubierto.
- El resolvedor corto llegó a crear un esqueleto plano que después sombreaba el caso bajo
  `Barcelona/`. Se retiró el esqueleto regenerable y se reanudó con la identidad canónica
  completa. Este incidente convierte la resolución sin escrituras en un gate de seguridad.
- La sala de máquina publicó 54 entradas y señaló 12: siete eran controles internos; los
  documentos materiales con OCR vacío o bajo resultaron visualmente legibles. Un exit `0`
  coexistió con error de Tesseract, confirmando que la cobertura por documento es la fuente
  de verdad.
- La sala de lectura heredada verificaba manifiesto contra disco, pero contenía subcarpetas,
  nombres con datos personales y categorías incompatibles con el contrato vigente. Se
  reconstruyó sin buckets por fuente, con 41 documentos únicos, tres carpetas de bundle de
  correo y tres grupos de alias; la verificación SHA-256 completa pasó después del
  intercambio.
- El prerrelleno se actualizó con la cadena de PBC y el contraste de LeadHub, manteniendo en
  blanco el veredicto y el recuadro ejecutivo. La versión anterior se archivó sin
  sobrescribirla.
- LeadHub pudo confirmarse visualmente en el Chrome cotidiano, pero `FeesDefender-crm` no
  dispone aún del recolector completo y su perfil dedicado no estaba autenticado. La rama
  queda pendiente por capacidad, no por ausencia de la operación.
- Una segunda atomización encontró abierto en Word un MD derivado (`~$*` presente): el
  escritor recibió `PermissionError`, aunque el corpus publicado seguía íntegro. El
  flujo debe detectar el lock antes de tocar la publicación y no convertir un fallo blando
  del OCR en éxito global.
- La primera ficha del contrario guardó nombre y apellidos por separado, pero la interfaz
  solo mostró el nombre de pila. Se corrigió el campo visible con el nombre completo y se
  completaron código postal, población y provincia. Sin embargo, `_caso.md` conservó
  cliente y contraparte pendientes porque `scripts.crm_ficha` nunca lo actualiza. El
  incidente fija la proyección automática a los tres destinos de §8.1 y demuestra que el
  defecto está en el cableado existente, no en la ausencia de otro orquestador.

El piloto termina `preparado_con_pendientes`: las fuentes disponibles, las dos salas,
Sudespacho y el prerrelleno están materializados; quedan fuera del cierre `completo` la
captura probatoria integral de LeadHub, el readback de relaciones del CRM y el registro por
el camino común de la revisión humana + GET + resincronización de la ficha. Esta evidencia
no convierte la spec en lista: la rev. 3 queda pendiente de R3.

## 18. Adjudicación de la revisión adversarial (Codex, 2026-08-15) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md` rev. 1, commit `bedfc45dda942afd5c5df3b8ec95e6ce8a008b33`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-08-15-apertura-integral-r1-adversarial-review.md`
- **Hallazgos:** 9 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento; pendiente R2

**Adjudicador excepcional:** Codex (subagente independiente, sustitución excepcional por
indisponibilidad de Claude Code). Esta sustitución, ordenada expresamente por Nikolai,
contradice la regla ordinaria «Claude adjudica siempre». Revisor y adjudicador pertenecen al
mismo modelo/familia, por lo que la independencia es **más débil** y puede haber puntos
ciegos compartidos. Esta adjudicación no es autoaprobación: conserva el `NO-SHIP` de R1 y la
rev. 2 no pasa a plan ni a `SHIP` sin R2 y su adjudicación.

| ID | Sev. | Adjudicación contra la fuente | Decisión y remedio mínimo |
|---|---|---|---|
| H-01 | CRÍTICA | **CONFIRMADO.** `IntakeManifest.save` y `_atomic_write_caso_md` son read-modify-replace sin lock/CAS (`core/intake_manifest.py:181-194`; `core/case_manager.py:1020-1062`), y el JSONL abre en append sin coordinación (`core/intake_log.py:156-205`). `os.replace` evita parcialidad, no lost updates | §§1, 6 y 7: solo descubrimiento/descarga paralelos a staging disjunto; incorporación y estado serializados. Lock/CAS solo tras prueba de dos writers; criterio 41 |
| H-02 | CRÍTICA | **CONFIRMADO.** La rev. 1 atribuía al abogado una rama local completa, mientras el contrato hermano vigente asigna la ejecución a Marta, exige lista de referencias del despacho, puerta humana y reverificación; el código solo tiene referencias fijas | **Remedio distinto al sugerido, por decisión de Nikolai:** §6.3 crea un piloto explícito, Nikolai principal y Marta subsidiaria, mide ambas vías y registra actor/cuenta sin fingir automatización o completitud. El contrato hermano no se edita aquí y queda pendiente de la medición; §16 y criterio 43 |
| H-03 | ALTA | **CONFIRMADO.** `pull_drive_ev` retorna `skipped=True` ante `.pulled` correcto sin ejecutar rclone (`core/intake_drive.py:202-230`), así que dos skips podían aparentar estabilidad | §§6.2 y 9: consulta remota real en cada ronda; un skip/caché no cuenta. Criterios 10 y 47 |
| H-04 | ALTA | **CONFIRMADO.** `drive_ev` está excluido de `FUENTES_LOTE` y dentro de `ESPEJO_SUBDIRS` (`core/config.py:529-537`); el pull escribe al destino fijo con `--inplace` (`core/intake_drive.py:257-273`) | Se elige una sola semántica: **espejo versionado**, no lote. Staging, objetos content-addressed, generaciones y tombstones preservan cada versión; §§6.2 y 7, criterio 42 |
| H-05 | ALTA | **CONFIRMADO.** El loader actual exige poco más que `nombre` y `--yes` pasa a escritura (`core/crm_ficha.py:27-80`; `scripts/crm_ficha.py:76-103`); la rev. 1 no hacía observable «anclado y unívoco» | No se reinstaura aprobación previa. §8.1 fija procedencia y autoridad por campo, bloquea contradicciones, escribe y deja `pendiente_revision_humana`; solo revisión en CRM + GET + resincronización permite completar o preparar requerimiento/demanda. Se declara el riesgo residual asumido de write-before-review; criterios 20, 24, 32 y 44-45 |
| H-06 | ALTA | **CONFIRMADO.** `_alta_crm` registra el ID solo después de la respuesta y absorbe cualquier excepción; luego el CLI imprime `OK Caso abierto` (`scripts/abrir_caso.py:265-305,497-499`) | §5.2: intención previa, `escritura_resultado_desconocido`, búsqueda/reconciliación por referencia antes de repetir POST y caso de timeout-after-commit; criterio 46 |
| H-07 | ALTA | **CONFIRMADO.** CLI y DTO usan `float`, y los payloads convierten con `int(round(...))` (`scripts/abrir_caso.py:380`; `core/sudespacho_create.py:1245-1248,1439-1442`) | §5 adjudica decimal de escala máxima 2. Céntimos solo si el contrato remoto prueba ida/vuelta exacta; si no, se rechazan. Nunca redondeo silencioso; criterio 11 |
| H-08 | ALTA | **CONFIRMADO.** Los artefactos vigentes no comparten generación ni prueba de consulta negativa y la rev. 1 difería `estado.json` hasta después del E2E que lo necesitaba | §10 exige desde la primera entrega una fotografía atómica mínima de fuentes, fases, generación y punto fijo, sin crear un motor de workflows ni otro CLI; criterios 47-48 y 50 |
| H-09 | ALTA | **CONFIRMADO.** La rev. 1 ampliaba el tratamiento de domicilios a servicios externos sin allowlist, minimización ni retención; no existe adaptador postal en `core/` o `scripts/` | §§2, 8.1 y 11: lista cerrada expediente/Correos/Catastro, minimización, telemetría desactivada, logs sin contenido, temporales eliminados y retención técnica máxima de 7 días; fuentes comerciales abiertas/no contratadas prohibidas; criterios 23 y 49 |

Los nueve hechos se sostienen. En H-02 y H-05 se confirma el defecto, pero el remedio del
revisor no sustituye la decisión del dueño: H-02 adopta un piloto con actor principal
distinto antes de modificar el contrato hermano, y H-05 desplaza la revisión humana al
momento posterior a la escritura. Esas divergencias y sus riesgos quedan declarados, no
contados como refutaciones.

## 19. Adjudicación de la revisión adversarial (Codex, 2026-08-15) — NO-SHIP, remediado

- **Objeto revisado:** esta spec rev. 2, commit `f087edadbe803df8a738397b8697cdfccb1d52c4`
- **Ronda:** 2
- **Revisor:** Codex (subagente independiente, solo lectura)
- **Informe recibido:** `2026-08-15-apertura-integral-r2-adversarial-review.md`
- **SHA-256:** `FA1C5129FA76ABFDE991406140BE4FA415CCB4B3BA905A2E1B7D4DCB3D68DF17`
- **Hallazgos:** 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento; pendiente R3

**Adjudicador excepcional:** Codex, por decisión expresa de Nikolai ante la indisponibilidad
de Claude Code. Revisor y adjudicador pertenecen al mismo modelo/familia; la independencia
es más débil y puede compartir puntos ciegos. La adjudicación se hizo contra el código y los
contratos citados, no contra el informe, y no convierte la rev. 3 en `SHIP`.

| ID | Sev. | Adjudicación contra la fuente | Decisión y remedio mínimo |
|---|---|---|---|
| H2-01 | CRÍTICA | **CONFIRMADO.** Manifest y `_caso.md` siguen siendo read-modify-replace sin exclusión interproceso; el lock de checkout conserva siete defectos caracterizados | §§1, 6, 7 y 10: mutex interproceso corto por caso desde la primera entrega, titularidad/nonce, abandono seguro y prueba de dos procesos solapados. No se reutiliza el lock de checkout |
| H2-02 | CRÍTICA | **CONFIRMADO.** `CaseWorkspace` todavía no existe y la spec omitía el contrato dual antes de efectos locales y remotos | **Remedio mínimo elegido:** §§3-4 y 16 distinguen existente/nuevo/legacy: el existente exige Drive explícitamente `disponible`, el nuevo probado se inicializa atómicamente y legacy/error, checkout, conflicto o scratch bloquean hasta que `CaseWorkspace` sustituya el gate |
| H2-03 | CRÍTICA | **CONFIRMADO.** `os.replace` por fichero no hace atómico bytes–manifest–log–estado–remoto; loaders actuales pueden degradar controles corruptos | §§5.2, 7 y 10: `operation_id` durable, invalidez antes de publicar, readback y `completada` al final; reconciliación al arrancar y crash-injection en cada frontera; control corrupto bloquea |
| H2-04 | ALTA | **CONFIRMADO.** El esquema rev. 2 no ligaba fuentes a ronda, sobrescribía la única observación y no definía fotografía ni transiciones | §§9-10: fotografía cerrada por adaptador, `round_id` por fuente, dos rondas atestadas, enums/transiciones cerrados y contador de intentos |
| H2-05 | ALTA | **CONFIRMADO.** Actor e instante no prueban qué versión remota vio el humano; una edición posterior podía adoptarse como corrección revisada | §§8.1 y 10: attestación con `candidate_revision`, ID y digest/versión remota exacta; cualquier cambio posterior exige nueva revisión |
| H2-06 | ALTA | **CONFIRMADO.** Medir primero con Nikolai infringía el contrato hermano que reservaba la ejecución a Marta | **Remediado también fuera de este repo:** `FeesDefender-crm` v3.7, commit `8bc09ea`, autoriza antes de medir una excepción temporal sin entrega probatoria; §§6.3 y 16 |
| H2-07 | ALTA | **CONFIRMADO.** Sala de máquina y sala de lectura son add-only y podían volver a verde conservando derivados retirados | §§8-9: reconciliación contra generación activa; derivados obsoletos se archivan o inactivan y quedan fuera de índices/lectores, sin borrar crudo ni historia |
| H2-08 | ALTA | **CONFIRMADO.** La secuencia exigía XLSX a tipos excluidos por `INFORME_VIABILIDAD_TIPOS` | §§8 y 10: `no_aplica_confirmado` permite continuar sin fabricar informe; criterios 12 y 29 |

Los ocho defectos se sostienen. No se adopta la alternativa más grande de H2-02 —terminar
primero toda la arquitectura dual— porque la restricción a Drive `disponible` elimina el
riesgo en la primera vertical y evita bloquear aperturas normales. La rev. 3 debe superar y
adjudicar R3 antes de pasar a plan TDD.

## 20. Adjudicación de la revisión adversarial (Codex, 2026-08-24) — NO-SHIP, pendiente

- **Objeto revisado:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md` rev. 3, commit `eb1b81a`
- **Ronda:** 3
- **Revisor:** Codex (solo lectura por construcción: copia externa del árbol vía `git archive`, sin `.git` y sin red)
- **Informe recibido:** `2026-08-24-apertura-integral-r3-adversarial-review.md`
- **Hallazgos:** 7 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** pendiente — la rev. 4 requiere tres decisiones de Nikolai, enumeradas al final

**Independencia restablecida.** R1 y R2 las adjudicó Codex por indisponibilidad de Claude Code,
declarando `independencia_adjudicacion: debilitada-misma-familia`. Esta ronda vuelve a la regla
ordinaria de `CLAUDE.md`: revisa Codex, adjudica Claude Code contra la fuente. El mandato ordenó
atacar ese punto ciego antes que la rev. 3, y el resultado justifica la ronda: los diecisiete
hallazgos de R1 y R2 se habían adjudicado **17 de 17 confirmados, 0 refutados**, y siete de esos
remedios no cierran el daño que decían cerrar.

| ID | Sev. | Adjudicación contra la fuente | Decisión y remedio mínimo |
|---|---|---|---|
| H3-01 | CRÍTICA | **CONFIRMADO en su núcleo, con una premisa refutada.** No existe `CaseWorkspace` (0 apariciones en `core/`, `scripts/`, `tests/`), `path_for` termina en `return flat` (`core/casos/case_locator.py:26-43`), `resolve_ref` devuelve la referencia sin resolver (`:99-121`) y el guard vigente **desvía** escrituras en vez de resolver la copia activa (`core/case_manager.py:692-727`). **Premisa refutada:** el informe atribuye a la rev. 3 la degradación de estado ausente/corrupto a `disponible`; la spec la bloquea expresamente como `workspace_no_soportado` (`:105-110`). Esa degradación es del **código** (`core/case_manager.py:94`, `core/config.py:368`), no del diseño. El defecto que sí queda: la spec exige «demostrar que no hay candidato en checkout ni scratch» sin mecanismo para demostrarlo —no hay registro local— y el único indicio disponible es el lock del Drive, cuyos siete defectos siguen vivos (7 xfailed, 0 xpassed) | Retirar la afirmación de que el gate temporal **elimina** el riesgo: acota la ventana, no la cierra. Decisión de Nikolai en (1) |
| H3-02 | CRÍTICA | **CONFIRMADO y reforzado por la prueba dinámica.** La spec exige mutex con propietario, nonce, espera acotada y recuperación de abandono (`:397-405`) sin fijar primitiva, ubicación ni ámbito; el árbol no contiene ninguna (`filelock`/`portalocker`/`fasteners`/`LockFileEx`/`fcntl` ausentes; el único `msvcrt` es `getwch`), y `_atomic_write_caso_md` declara «Sin lock, sin versionado» (`core/case_manager.py:1020-1028`). El refuerzo: propietario y nonce **ya existen** en el lock de checkout y no bastan — `test_defecto_doble_titular` y `test_defecto_rollback_cancela_un_lock_ajeno` reproducen los dos daños que el hallazgo predice | Especificar primitiva y namespace por identidad canónica, independientes de que exista la carpeta, con adquisición/liberación atómicas y prueba de titularidad. Decisión de Nikolai en (2) |
| H3-03 | CRÍTICA | **CONFIRMADO.** El esquema de `operations` (`:702-745`) conserva `kind`, `status`, `generation`, `expected` y dos instantes: sin identidad del destino remoto, digest de petición, clave de reconciliación, paso alcanzado ni resultado del readback, el paso 5 del protocolo no es ejecutable en general y el paso 4 remite a «el orden específico de la operación», que no está definido para ninguna frontera | Definir, por clase de operación no idempotente, registro durable cerrado, orden de publicación, evidencia de readback y algoritmo de recuperación. Es precondición del plan TDD, no un detalle de implementación |
| H3-04 | ALTA | **CONFIRMADO sin matices.** `scripts/abrir_caso.py:479-499` termina en `_alta_crm(...)` + `OK Caso abierto`, y el fichero **no menciona** `pull_expediente_v2`, `sala_lectura`, `sala_maquina`, `viabilidad` ni `crm_ficha`. Es la tercera recurrencia del mismo defecto de familia: el motor existe y nadie lo encadena | Nombrar el dueño ejecutable de la secuencia, o retirar la promesa de trabajo mecánico sin supervisión. Decisión de Nikolai en (3) |
| H3-05 | ALTA | **CONFIRMADO.** `sources` ya guarda `snapshot_sha256` y `round_id` (`:713-725`), así que el dato existe; lo que no existe es la regla que lo use: ni `:249-257` ni `:397-418` rechazan publicar una observación anterior después de una posterior. `input_generation` se incrementa por cambio, no por frescura | Persistir el cursor de origen en cada staging y comparar dentro del lock contra la última atestación comprometida de esa fuente. Añadir el interleaving A(V1)–B(V2)–A(commit) a los criterios 41, 42 y 48 |
| H3-06 | ALTA | **CONFIRMADO.** `attested_rounds` conserva `round_id`, `sources_digest` y `completed_at` (`:748-753`) sobre un `sources` de una sola observación mutable por fuente: sobrescrita la ronda 1, su digest ya no es recomputable. El punto fijo acredita dos rondas con dos hashes opacos | Conservar cada ronda como snapshot inmutable, o una referencia content-addressed verificable con canonicalización y encadenamiento definidos |
| H3-07 | MEDIA | **CONFIRMADO.** El plazo está fijado (`:566-568`, criterio 49) y no hay actor: `:420` reconcilia **operaciones** al arrancar, no residuos, y la estrategia de entrega no construye recolector. «Al terminar» no cubre kill ni corte | Cleanup en `finally` para la ruta normal y un janitor nombrado al arranque o un almacén con TTL para el residuo, con prueba de reloj inyectado |

**El veredicto se acepta: `NO-SHIP`.** La rev. 3 no pasa a plan TDD único. La razón no es el
número de hallazgos, es su naturaleza: tres de los siete son precondiciones de arquitectura que
un plan tendría que **decidir** en vez de ejecutar, y H3-04 dice que el flujo prometido no lo
ejecuta nadie hoy.

**Divergencias con el revisor, declaradas.** Una sola, y es de hecho, no de severidad: el «Hecho»
de H3-01 imputa al diseño una degradación que el diseño bloquea. Se corrige aquí y el hallazgo se
mantiene CRÍTICO por su núcleo. En sentido contrario, dos apartados del informe se quedaron cortos
por el acotamiento del mandato, y esta adjudicación los cierra: la autorización del repo hermano
(`FeesDefender-crm`, `8bc09ea`, ancestro de `main`, y la v3.7 en
`C:\Users\tnm33\Dev\FeesDefender-crm\docs\superpowers\specs\2026-07-31-descarga-fichas-crm-leadhub-design.md:38-41,56-59`) es **cierta**
con el alcance que la spec le atribuye, y la prueba dinámica de los siete defectos de checkout
**se ejecutó** (7 xfailed, 0 xpassed). De lo que el informe declaró `SIN VERIFICAR` solo sobrevive
una cosa, y se declara: las condiciones reales de uso del localizador de Correos y de la Sede
Electrónica del Catastro no las ha mirado nadie, en ninguna ronda.

**Una observación derivada, que no era hallazgo del informe.** Al verificar la evidencia de H3-03
se comprueba que `core/sync_sudespacho.py:1467-1479` persiste el registro de ocurrencias **antes**
de `guard_escritura` (`:1486`). El orden es deliberado y está razonado (N2: el universo enumerado
debe sobrevivir a un fallo de descarga), pero su efecto es que una escritura de protocolo alcanza
la ruta canónica de un caso **prestado** sin pasar el guard y sin declararse `es_protocolo=True`.
Como evidencia de H3-03 es débil; como defecto propio es real y va a `docs/MEJORAS_FUTURAS.md`,
no aquí.

**Las tres decisiones que bloquean la rev. 4** —son de Nikolai, no de esta adjudicación—:

1. **H3-01.** ¿El núcleo contractual mínimo de `CaseWorkspace` (identidad inequívoca, registro
   local, resolver estricto) pasa a ser **predecesor** de esta vertical, o la apertura mutante
   queda bloqueada hasta que exista? La tercera vía —seguir con el gate de `estado_repositorio`—
   exige aceptar por escrito que una copia local no registrada puede coexistir con la apertura.
2. **H3-02.** Qué primitiva de exclusión y qué namespace. El lock de checkout **no se puede
   reutilizar**: sus siete defectos siguen reproducidos en `xfail` y dos de ellos son exactamente
   los que este hallazgo predice.
3. **H3-04.** Quién ejecuta la secuencia. O se amplía un entrypoint existente hasta ser dueño real
   del orden y la reanudación, o se retira de la spec la promesa de trabajo mecánico sin
   supervisión y el criterio E2E prueba que el operador sigue siendo el driver.

## 21. Alcance de la primera vertical (rev. 5) — Drive y Sudespacho → intake → sala de máquina

*Decisión de Nikolai del 2026-08-24, tras adjudicar R3. **Cambio de la rev. 5 frente a la
rev. 4:** el pull de Sudespacho entra en V1 —en la rev. 4 salía diferido—, por decisión expresa
de Nikolai; el resto del reparto no cambia. Esta sección es una **sustitución expresa** en el
sentido del §16: lo que sale de la primera vertical **no queda derogado, queda
diferido**, y su contrato sigue vigente para la vertical donde entre. Una omisión no deroga
nada; solo lo hace esta enumeración.*

### 21.1. Por qué se estrecha

R3 devolvió `NO-SHIP` con siete hallazgos y ninguno refutado (§20). Tres de los siete no eran
defectos de la mecánica sino **el precio de la anchura**: la rev. 3 pedía definir el orden de
publicación durable, la prueba de rondas y la retención de residuos **a la vez** para Gmail,
Drive, LeadHub, Sudespacho, salas, viabilidad, enriquecimiento postal y rama judicial. Estrechar
no contesta esos hallazgos: hace que dos desaparezcan del alcance y dos se vuelvan acotados, y
deja en pie exactamente los tres que hay que resolver de todos modos.

El segundo motivo es de proceso y se declara sin adornos: este ítem lleva **tres rondas de
revisión, veinticuatro hallazgos y cero líneas de código de producción**. Es el síntoma que
`PLAN.md` fila #13 tiene aparcado desde el 2026-08-03.

### 21.2. Qué es la primera vertical

**V1 = resolución de identidad → esqueleto → materialización de Drive E&V y pull de Sudespacho
→ intake con custodia → sala de máquina.** Nada más.

En concreto, V1 comprende:

- resolver la identidad del caso y, en un caso nuevo probado, inicializar atómicamente la
  estructura canónica mínima y `_caso.md`;
- el pull de Drive E&V con la semántica de **espejo versionado** del §6.2 (staging disjunto,
  historia content-addressed, generaciones, tombstones);
- el **pull de Sudespacho** (`pull_expediente_v2`): registro del universo listado por el CRM,
  descarga a `05_CRM/`, bloqueo de referencias ajenas y distinción entre gestor documental vacío
  confirmado y respuesta con errores;
- el intake con su custodia forense: crudo intacto, nombres originales, hashes SHA-256, eventos
  en `_intake_log.jsonl`, `90_Notas personales/` nunca tocada;
- la sala de máquina: OCR y espejos Markdown bajo `01_Procesado/02_Sala de máquina/`, con
  reconciliación por generación activa y retirada de derivados huérfanos del corpus activo;
- el mutex interproceso, el gate de workspace, `operations` y `estado.json` que gobiernan lo
  anterior.

**V1 no escribe en ningún servicio externo, y esa es la invariante que hay que preservar.** El
pull de Sudespacho entra porque es una **lectura**: autentica, enumera y descarga, y todo lo que
escribe es local (`05_CRM/`, manifiesto, registro de ocurrencias, log). El **alta** CRM y toda
`crm_ficha` quedan fuera: toda invocación de V1 usa `--crm skip`, que además es la práctica ya
establecida del despacho. Esa es la propiedad que hace tratable H3-03: en V1 no existe ningún
efecto remoto no idempotente que reconciliar.

**Y una deuda conocida entra en alcance con el pull.** `MEJORAS #120` deja de ser backlog remoto:
`core/sync_sudespacho.py` persiste el registro de ocurrencias **antes** de `guard_escritura`, así
que hoy una escritura de protocolo alcanza la ruta canónica de un caso prestado sin pasar el
guard. Con el pull dentro de V1 y el gate de workspace de H3-01 como criterio, V1 tiene que
cerrarla: llamar al guard con `es_protocolo=True` y fijar la exención por escrito en vez de por
omisión.

### 21.3. Qué sale de V1, y a dónde va

Sale **diferido, no derogado**. Cada bloque conserva su contrato en la sección que lo define.

| Sale de V1 | Contrato que sigue vigente | Entra en |
|---|---|---|
| Alta CRM y dominio monetario | §5 · criterios 11, 35, 46 | V2 |
| `crm_ficha` completa: procedencia, identidad del contrario, revisión humana atestada, las tres superficies | §§5.2, 8.1 · criterios 20-22, 24-26, 28, 30, 32, 44, 45 | V2 |
| Enriquecimiento postal (Correos, Catastro) y su retención | §§8.1, 11 · criterios 23, 49 | V3 |
| Descubrimiento y etiquetado de Gmail | §§6, 8 · criterios 6, 31 | V3 |
| LeadHub y el piloto de medición | §§6.3, 16 · criterios 8, 9, 19, 43 | V3 |
| Sala de **lectura** y su taxonomía | §§8-9 · criterio 17 | V3 |
| Viabilidad y `no_aplica_confirmado` | §8 · criterio 12 | V3 |
| Archivo multiefecto ordenado por el abogado | §12 · criterio 40 | V3 |
| Rama judicial | §5 · criterio 38 | sigue **bloqueada** hasta que exista adaptador judicial verificado (sin cambio) |
| Relaciones CRM sin readback | §5.2 · criterio 39 | V2 |
| Orden de la fase 8.1 | §8.1 · criterio 29 | V2, y su precondición pasa a ser el cierre de V1 |

**El orden del runbook se respeta, y por eso entra el pull.** El gotcha vigente es «atomizar
correo y pull CRM **antes** de `sala_maquina apply`, o el OCR queda incompleto». Con Drive y
Sudespacho dentro de V1, la sala de máquina se valida sobre las dos fuentes documentales que
alimentan el OCR y no hace falta una segunda pasada por el CRM.

**Lo que sigue faltando, dicho igual.** El correo no está en V1: un caso cuyo material llegue por
Gmail tendrá corpus incompleto hasta V3, y la atomización del correo es precisamente la otra mitad
de ese gotcha. Quien cierre V1 sobre un caso real así no puede declarar su corpus completo: el
estado del caso lo dice, `fuentes_pendientes`, nunca `completo`.

### 21.4. Criterios de aceptación de V1

De los cincuenta del §14, V1 exige **veintidós**: 1, 2, 3, 4, 5, 7, 10 (Drive y Sudespacho,
incluido que `.pulled` no omita Drive; no Gmail ni LeadHub), 13, 14 (solo colisiones, intake
tardío, ruta desviada, descarga parcial, la matriz de workspace, crash tras cada frontera **local**
y punto fijo), 15, 16, 18, 27, 33, 34 (íntegro: `--crm skip` y el expediente CRM preexistente
registrado y descargado antes de la sala de máquina), 36, 37, 41, 42, 47, 48 y 50.

Los criterios **27 y 50** son restricciones globales, no fases: rigen en V1 y siguen rigiendo
después. Los veintiocho restantes quedan **diferidos con su vertical**, según la tabla del §21.3. Un
criterio diferido no se declara cumplido ni exento: no se evalúa todavía.

### 21.5. Estrategia de entrega de V1 (sustituye al §15 mientras V1 esté en curso)

El orden de siete bloques del §15 presupone la vertical ancha y **no se aplica a V1**. En su lugar:

1. **Núcleo de workspace** — la Fase 1 de la arquitectura dual (`PLAN.md` fila #3): `CaseRef` con
   unicidad de W-code y `AMBIGUOUS_CASE`, registro local atómico, resolver por identidad, modo
   estricto donde `caso_path` deja de devolver rutas inexistentes, `core.intake_log` migrado, y la
   matriz pura de resolución de siete casos como criterio de salida. **Predecesor de todo lo
   demás**: pendiente de la decisión (1) del §20.
2. **Mutex y protocolo durable local** — primitiva y namespace pendientes de la decisión (2) del
   §20; `operations` y `estado.json` limitados a las fronteras locales de V1.
3. **Espejo versionado de Drive y pull de Sudespacho** con monotonía de observación por fuente
   (H3-05) y snapshot inmutable por ronda atestada (H3-06) sobre **dos** fuentes, más el cierre de
   `MEJORAS #120` en el camino del pull.
4. **Cableado** de Drive y Sudespacho → intake → sala de máquina detrás de `scripts.abrir_caso`,
   respetando el orden del runbook (pull antes de la sala de máquina), pendiente de
   la decisión (3) del §20, con un test que afirme que una corrida completa toca todas las fases
   de V1.
5. **E2E de V1** con fixtures sin PII, y una apertura real controlada con `--crm skip`.

Cada bloque con TDD. Este orden tampoco es autorización para planificar: la rev. 4 estrecha el
alcance y **no remedia** los hallazgos de R3, que siguen abiertos.

### 21.6. Efecto sobre los siete hallazgos de R3

| Hallazgo | Efecto del estrechamiento |
|---|---|
| H3-01 gate de workspace | **Íntegro.** V1 muta el expediente canónico: escribe bytes en `00_Input` y derivados en `01_Procesado`. Sigue exigiendo la decisión (1) |
| H3-02 mutex sin primitiva | **Íntegro.** Sigue exigiendo la decisión (2) |
| H3-03 protocolo durable | **Acotado.** Sin efectos remotos no idempotentes en V1, queda **una** clase de operación cuyo orden hay que definir: publicación local de bytes + manifiesto + log + `_caso.md` + `estado.json`. Sigue siendo precondición del plan, ya no de cinco fronteras |
| H3-04 nadie encadena el flujo | **Íntegro pero menor.** Se reduce a que `scripts.abrir_caso` llame a la sala de máquina tras el intake. Sigue exigiendo la decisión (3) |
| H3-05 regresión de frescura | **Íntegro, y ahora sobre dos fuentes.** Drive y el pull del CRM son el núcleo de V1: es aquí donde este hallazgo importa más, no menos |
| H3-06 punto fijo no auditable | **Acotado.** Dos fuentes en vez de cuatro: el snapshot inmutable por ronda atestada sigue siendo directo, y afirmaciones como «una fuente saltada no incrementa `consecutive_unchanged`» (criterio 47) ya son observables con dos |
| H3-07 retención postal | **Fuera de alcance.** No hay adaptador postal en V1. Vuelve con V3, con su contrato intacto |

Quedan, por tanto, **tres decisiones de Nikolai** (§20) y **cuatro hallazgos** que la rev. 4 debe
cerrar en el texto —H3-03 acotado, H3-05, H3-06 acotado y, cuando vuelva, H3-07—. Nada de esto
autoriza un plan hasta que R4 se corra y se adjudique.

## 22. Adjudicación de la revisión adversarial del estrechamiento (Codex, 2026-08-24) — REQUIERE-REVISION, pendiente

- **Objeto revisado:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md` rev. 5, commit `806079c`
- **Ronda:** 4
- **Revisor:** Codex (solo lectura por construcción: copia externa del árbol vía `git archive`, sin `.git` y sin red)
- **Informe recibido:** `2026-08-24-apertura-integral-r4-adversarial-review.md`
- **Hallazgos:** 5 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** pendiente — dos correcciones son mecánicas, tres exigen decisión

**Objeto de la ronda.** R4 no revisó la spec entera: revisó el **estrechamiento** del §21. El
mandato le prohibió redescubrir H3-03, H3-05, H3-06 y las tres decisiones del §20, y le pidió
decir si el estrechamiento les cambia la forma o describe falsamente su efecto. Ahí acertó de
lleno: **dos de los cinco hallazgos son errores del texto que escribí yo el mismo día**, y uno de
ellos es una palabra que me inventé.

| ID | Sev. | Adjudicación contra la fuente | Decisión y remedio mínimo |
|---|---|---|---|
| H4-01 | CRÍTICA | **CONFIRMADO.** `scripts/abrir_caso.py:381` declara `crm: str = typer.Option("api", ...)`: el default es `api`, no `skip`. `:497` llama a `_alta_crm` incondicionalmente, `:275-276` solo corta `if crm_mode != "api"` y `:298` alcanza `create_expediente`. Mi §21.2 afirma que «toda invocación de V1 usa `--crm skip`»: eso es una **convención del llamador**, no una invariante ejecutable. **Matiz que añado y que no salva:** hay puerta humana antes del POST (`:293`, `yes or typer.confirm`), así que hoy hace falta el default `api` **más** un sí o `--yes`. Baja la probabilidad, no la alcanzabilidad — y el §21.5 disuelve la puerta al pedir que este mismo entrypoint sea el driver de trabajo mecánico sin supervisión, porque un driver no interactivo pasa `--yes` por construcción | El §21 debe definir cómo se reconoce una ejecución V1 y hacer que ese camino **rechace técnicamente** cualquier modo distinto de `skip`, en caso nuevo y en incremental. Más un criterio negativo: omitir el flag aborta antes de cualquier efecto y un spy acredita cero llamadas remotas de alta/ficha/relaciones |
| H4-02 | ALTA | **CONFIRMADO.** `scripts/sala_maquina.py:491-492` llama `_atomizar_correo(...)` y `_procesar_adjuntos(...)` **incondicionalmente**, con el comentario «atomizar ANTES del OCR (spec §4)». La sala de máquina que el §21 mete en V1 procesa correo, y el §21 declara el correo fuera. La contradicción es real y es mía | **Requiere decisión de alcance**, y es binaria: (a) V1 invoca una modalidad de sala de máquina que **no** atomiza y registra la fuente como pendiente, o (b) V1 incluye la **atomización local de correo ya depositado** —no el descubrimiento Gmail— y suma sus artefactos, generación, puntos de crash y poda a los criterios 10, 14, 41 y 48. Ninguna de las dos amplía V1 hasta Gmail remoto |
| H4-03 | ALTA | **CONFIRMADO en sus tres puntos.** (1) El criterio 1 promete «completa una apertura normal» y el §21.3 ordena que V1 nunca sea `completo`: literalmente indemostrable dentro de V1. (2) **`fuentes_pendientes` no existe**: `grep` en todo el árbol da **dos** apariciones, `:1342` y `PLAN.md:98`, ambas escritas por mí hoy. No está en los tres estados del §13 —`completo`, `preparado_con_pendientes`, `bloqueado`— ni en los enums del §10. Cité como garantía un token que no tiene esquema. (3) El criterio 35 se difiere entero a V2 aunque V1 modifica el mismo `scripts.abrir_caso` y ejerce `--case-id` y la autodetección desde `--folder-id` | Mecánico y sin decisión: sustituir `fuentes_pendientes` por **`preparado_con_pendientes`**, que ya existe y significa exactamente lo que quise decir; redactar la versión V1 del criterio 1 como «completa la secuencia V1 y termina `preparado_con_pendientes`»; y partir el 35 conservando en V1 `--case-id` y la autodetección |
| H4-04 | ALTA | **CONFIRMADO.** El criterio 29 (`:950-951`) exige que la fase 8.1 espere Drive, sala de máquina, **sala de lectura** y viabilidad. Mi tabla del §21.3 manda sala de lectura y viabilidad a V3 pero el criterio 29 a V2, diciendo «su precondición pasa a ser el cierre de V1». Eso no difiere: **suprime dos precondiciones**, que es justo lo que la regla «diferido no derogado» prohíbe. Error de lógica mío, no del código | Mecánico: el cierre de V1 es necesario y **no** suficiente. La ejecución de la fase 8.1 y su criterio 29 pertenecen a una integración posterior a V3, o V3 precede al gate final de V2. No se amplía V1 |
| H4-05 | ALTA | **CONFIRMADO, y la lista es más larga que la mía.** Verificado uno a uno: `core/case_manager.py:277-278` crea `01_Procesado/Sala lectura` y `:347-376` copia las plantillas de viabilidad, así que llamar a `ensure_case` «esqueleto canónico mínimo» es **falso** —ejecuta andamiaje de dos verticales diferidas—; `core/intake_drive.py:321-323` llama `register_drive_ev` con `returncode == 0` sin consultar la decisión del guard, y reescribe el `_caso.md` canónico; `scripts/abrir_caso.py:110-111` hashea el cajón **canónico** y no el destino efectivo, así que un desvío puede quedar sin hashes de los bytes realmente depositados. Y la insuficiencia de las pruebas es comprobable: `tests/test_guard_intake_wiring.py:132-138` solo afirma sobre `*.pdf` y el evento, no sobre los controles canónicos — los 21 tests de ese fichero y del cableado de atomización **pasan** en verde con todo lo anterior en pie | El §21 debe **enumerar el write-set de V1** y decidir por artefacto: bloqueado, publicado bajo el mutex, o exento como protocolo por contrato explícito (`es_protocolo=True`, nunca por omisión). El E2E de workspace no disponible debe comparar el árbol byte a byte y acreditar cero cambios; la custodia debe seguir el **destino efectivo**. Y el inicializador de V1 tiene que ser mínimo de verdad |

**El veredicto se acepta: `REQUIERE-REVISION`.** Y la distinción que hace el revisor es la útil: lo
que bloquea el **alcance** son estos cinco, locales al §21; lo que bloquea el **plan**, además, son
las tres decisiones del §20 y los contratos abiertos de H3-03 acotado, H3-05 y H3-06.

**Una corrección de honestidad que acepto entera.** La frase absoluta «V1 no escribe en ningún
servicio externo» es demasiado fuerte incluso con H4-01 cerrado: el preflight de Drive puede
ejecutar `rclone about gdrive_ev:`, usar el refresh token, emitir un access token nuevo y
reescribir `rclone.conf` (`core/intake_drive.py:457-466,513-540`). Es un efecto del servicio de
autenticación, no una mutación de datos del expediente, pero la invariante hay que formularla como
el revisor propone: **cero mutaciones de datos y de acciones de comunicación, y cero efectos
remotos no idempotentes del caso**, declarando el refresh. Un absoluto que se rompe con un caso
conocido no es una invariante: es una frase.

**Y un aviso del revisor que va más allá del §21, anotado aquí para que no se pierda:** tanto
`core/sync_sudespacho.py:1356` como `scripts/sync_sudespacho.py:167` tienen **default judicial**
(`expedientes_judiciales`). La parte negativa del criterio 38 —una apertura extrajudicial no entra
por la vía judicial— no debería descansar en que nadie use el default; conviene hacerla global,
como el 27 y el 50.

**Lo que no hago aquí.** No remedio en esta adjudicación. Dos de los cinco son correcciones
mecánicas de mi propio texto (H4-03 y H4-04) y podrían aplicarse ya; los otros tres exigen
decisión: la forma del enforcement de `skip` (H4-01), la frontera binaria de la atomización de
correo (H4-02) y el alcance del write-set enumerado (H4-05). Aplicar solo las mecánicas fabricaría
una revisión intermedia que nadie ha revisado, y la lección de la rev. 4→5 es que multiplicar
revisiones sin objeto es churn. Se remedia todo junto, en la rev. 6, cuando las decisiones estén
tomadas.

**Autocrítica que corresponde registrar.** De los cinco hallazgos, tres —H4-02, H4-03 y H4-04— son
defectos que introduje al estrechar, no defectos heredados. Escribí un token de estado inexistente
y lo cité como garantía; moví un criterio a una vertical suprimiendo dos de sus precondiciones; y
llamé mínimo a un inicializador que ejecuta andamiaje de las verticales que acababa de diferir.
Ninguno lo habría detectado un guard: los tres son coherencia de contenido, y por eso existe la
ronda con revisor independiente.
