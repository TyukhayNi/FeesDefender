---
estado: propuesto (R1 adjudicada; pendiente R2)
dueño: Nikolai Tyukhay
fecha: 2026-08-15
revision: "2"
---

# Diseño — Apertura integral sobre componentes existentes

> **Fuente única del diseño de apertura integral.** Esta spec reúne en un solo documento la
> apertura, el descubrimiento de fuentes, el intake, las salas, el prerrelleno y los dos
> CRM. No se crearán specs separadas por adaptador. Las specs anteriores siguen siendo
> antecedentes o contratos internos de cada componente. En el orden E2E, los gates y el
> cierre solo prevalecen las sustituciones expresas adjudicadas en el §16; una omisión no
> deroga una regla anterior.
>
> **Naturaleza:** diseño. No autoriza todavía la implementación. La R1 terminó `NO-SHIP`;
> sus nueve hallazgos están adjudicados y remediados en esta rev. 2 (§18), que queda
> **pendiente de R2**. Solo después de adjudicar R2 podrá escribirse el plan único de
> implementación.

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
ejecutará sin supervisión, con las escrituras compartidas serializadas conforme a §§6-7,
y solo se detendrá ante riesgo de mezclar expedientes, una identidad materialmente dudosa
o una decisión jurídica.

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

Se bloquea la apertura si el mismo W-code presenta varios frentes incompatibles, si hay
más de un expediente candidato no reconciliable o si una referencia de Sudespacho no
coincide. Una vez fijada, ningún resolvedor corto puede cambiar la ruta del caso.

El preflight conserva el contrato operativo del §0 del runbook: el pipeline con efectos se
ejecuta desde el repo canónico que contiene `.env` y `.venv`, mediante PowerShell; las
ediciones versionadas permanecen en el worktree asignado; y nunca se barre recursivamente
una unidad `G:` completa para localizar un caso. El modo local no se presenta como cerrado
mientras no exista un checkin probado para un caso nacido sin baseline en Drive.

La política de colisión queda fijada así:

- un código de equipo repetido con W-code nuevo es normal y queda cubierto por `--yes`;
- un W-code ya existente no autoriza crear otra carpeta: el intake incremental entra por
  `--case-id`;
- `--force` solo puede reutilizar el mismo caso canónico ya resuelto; nunca permite crear
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

Antes de cada POST de alta se persiste atómicamente una intención con elemento, W-code,
referencia canónica e importe exacto. Si la petición pudo alcanzar Sudespacho pero no llega
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
`estado.json`: esos commits se serializan por caso. Solo un lock interproceso o CAS probado
contra dos writers solapados permite relajar esta regla.

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
provisional y contradice de forma expresa el contrato todavía vigente de
`FeesDefender-crm`, que asigna la ejecución a Marta. No se modifica ese repositorio desde
esta entrega: antes se medirán ambas vías y solo después se propondrá allí el contrato
definitivo.

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
hacen en una sección crítica serializada por caso. La atomicidad de `os.replace` no se toma
como protección frente a lost updates. Un modo multiproceso futuro exige lock o CAS con
versión y una prueba que solape dos commits y conserve la unión íntegra.

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
4. Prerrellenar y verificar el informe de viabilidad.
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
motor actual no poda. Si un texto sale roto tras el split, se contrasta primero con la
extracción del PDF de origen antes de atribuir el defecto al pipeline.

Antes de regenerar derivados, la fase detecta ficheros temporales de Office (`~$*`) y prueba
la apertura exclusiva de cada destino que vaya a reemplazar. Un derivado bloqueado conserva
la publicación anterior, registra `pendiente_reintento` y no contamina el inventario. La
ejecución no cierra Word ni mata procesos del usuario.

El prerrelleno cita evidencia localizable, conserva los datos desconocidos como tales y
deja siempre en blanco `VIABILIDAD` y el recuadro ejecutivo.

### 8.1 Ficha completa del contrario tras la lectura documental

Esta fase solo empieza cuando los documentos de Drive E&V y las demás fuentes disponibles
se han materializado, la sala de máquina y la sala de lectura están verificadas y el
prerrelleno permite localizar la evidencia. El correo que anuncia la incidencia no basta
para decidir la identidad del contrario.

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
dentro de Sudespacho y registra actor, instante y resultado. Si no corrige nada, un GET
posterior debe coincidir campo por campo con YAML y `_caso.md`. Si corrige en el CRM, ese
GET es la fuente de la versión revisada y se resincroniza en dirección **Sudespacho →
`_ficha_crm.yaml` → `_caso.md`**. Un CAS puede sustituir exclusivamente los valores y
digests de la `candidate_revision` esperada; un cambio local o documental independiente
desde esa revisión bloquea en `pendiente_sincronizacion`. Los commits son atómicos y una
nueva lectura verifica la igualdad final. Solo entonces queda `crm_ficha_completa`.
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
  "schema_version": 1,
  "case_id": "<identidad canónica>",
  "revision": 1,
  "input_generation": 1,
  "sources": {
    "<fuente>": {
      "status": "completada|vacio_confirmado|no_consultada|fallida|espera_login|espera_operador_ev|espera_entrega|adaptador_no_disponible|recibida_pendiente_reverificacion",
      "checked_at": "<ISO-8601>",
      "query_id": "<id sin PII>",
      "snapshot_sha256": "<digest del inventario>",
      "input_generation": 1,
      "changed": false
    }
  },
  "phases": {
    "<fase>": {
      "status": "pendiente|en_curso|completada|pendiente_reintento|pendiente_identidad_contrario|pendiente_domicilio|pendiente_revision_humana|pendiente_sincronizacion|escritura_resultado_desconocido|escritura_sin_readback|espera_decision_juridica|fallida",
      "input_generation": 1,
      "artifact_sha256": "<digest del manifiesto o resultado>",
      "verified_at": "<ISO-8601>"
    }
  },
  "fixed_point": {
    "round_id": "<id>",
    "generation": 1,
    "consecutive_unchanged": 0,
    "reached": false
  }
}
```

`input_generation` aumenta si cambia el inventario de cualquier fuente. En la misma
actualización se invalidan todas las fases derivadas con una generación anterior y se
reinicia `consecutive_unchanged`. Una consulta real sin cambios registra `checked_at`,
`query_id` y digest; una fuente saltada no puede imitarla. Cada actualización usa temp +
`os.replace` y compara `revision`, dentro de la sección crítica serializada del §7; si se
habilitan varios writers, un CAS fallido obliga a releer y fusionar, nunca a sobrescribir.

La fase `crm_ficha` añade `candidate_revision` y `candidate_digests` para YAML,
`_caso.md` y el primer GET. Son la precondición exacta del CAS posterior a la revisión
humana; no se sustituyen valores que ya no correspondan a esa fotografía.

Esta fotografía no sustituye `_caso.md` ni los manifiestos y no ejecuta fases: solo enlaza
fuente, fase, generación y verificación material. Un ledger append-only por ejecución queda
fuera de la primera entrega y solo se añadirá si una prueba E2E demuestra que la fotografía
no basta.

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

1. La secuencia documentada de entrypoints existentes completa una apertura normal sin
   pedir datos que puedan obtenerse de las fuentes autorizadas.
2. Interrumpir y reanudar en cualquier fase no duplica efectos confirmados ni repite una
   escritura cuyo resultado remoto sea desconocido.
3. Ninguna fase se marca completa solo por un código de salida cero.
4. Todo fichero procesado resuelve a una fila de manifiesto y su hash coincide.
5. Ningún destino se repite con hashes distintos.
6. Gmail descubre hilos recibidos por listas institucionales aunque el usuario no participe.
7. El pull de Sudespacho bloquea referencias ajenas y reconcilia el universo listado.
8. LeadHub no ejecuta mutaciones ni acciones de comunicación.
9. Una captura LeadHub incompleta nunca recibe veredicto de entrega completa y el piloto
   registra actor, cuenta, rol, tiempos, intervenciones manuales y cobertura de la vía usada.
10. Cada vuelta consulta realmente Gmail, Drive, LeadHub y Sudespacho; un nuevo correo o
    documento invalida y regenera las salidas dependientes, y `.pulled` no omite Drive.
11. La cuantía usa decimal exacto de escala máxima 2 en Drive, informe y Sudespacho. Si el
    CRM no demuestra soporte de céntimos, rechaza el valor fraccionario; nunca lo redondea.
12. `VIABILIDAD` y el recuadro ejecutivo quedan en blanco durante el prerrelleno.
13. El resumen final usa uno de los tres estados definidos en §13.
14. La suite E2E reproduce, sin PII, colisiones, intake tardío, ruta desviada, descarga
    parcial, operador/entrega LeadHub pendiente, reanudación tras interrupción y punto fijo.
15. Un resolvedor no crea estructura alguna y rechaza una carpeta sombra que solo coincide
    por nombre.
16. Los controles internos y temporales `~$*` no cuentan como documentos materiales.
17. La sala de lectura no pasa si su manifiesto cuadra pero el layout, la taxonomía o los
    nombres de destino infringen el contrato vigente.
18. Sudespacho distingue un gestor documental vacío confirmado de una respuesta con errores.
19. LeadHub no se marca disponible mientras solo exista el arnés de medición.
20. Toda ficha de contrario releída por API contiene nombre visible completo, apellidos
    separados, identificador y domicilio con código postal, población y provincia, pero
    permanece `pendiente_revision_humana` hasta revisión registrada y segundo GET.
21. Los campos de texto libre del contrario quedan en mayúsculas y el email en minúsculas;
    los `Select` conservan el literal exacto del CRM.
22. Una dirección postal incompleta o ambigua impide preparar o enviar requerimiento o
    demanda y produce `pendiente_domicilio`, no un dato inferido silenciosamente.
23. Un código postal resuelto automáticamente usa solo expediente, Correos o Catastro;
    conserva fuente, consulta y confianza en la ficha local, minimiza los datos enviados y
    cumple el contrato de logs/retención del §8.1 sin filtrar PII a Git.
24. `scripts.crm_ficha` sincroniza la identidad candidata en los tres destinos y, tras una
    corrección humana en CRM, la resincroniza Sudespacho → YAML → `_caso.md` y verifica.
25. Un contrario ya existente se actualiza mediante GET, merge, PUT y GET; vincularlo o
    releerlo antes de la revisión humana no se considera ficha completa.
26. La actualización de `_caso.md` modifica frontmatter y `## Partes` de forma atómica,
    conserva `## Navegación` y no sobrescribe valores no vacíos incompatibles.
27. No se crea `scripts.apertura_expediente` mientras los entrypoints existentes no cumplan
    sus contratos y una prueba E2E no demuestre una carencia concreta de coordinación.
28. El alta mínima no crea ni actualiza un contrario a partir del correo inicial y conserva
    `crm_ficha_pendiente` hasta completar las fuentes documentales.
29. La fase 8.1 no comienza antes de materializar Drive E&V y verificar sala de máquina,
    sala de lectura y prerrelleno.
30. Firmante del encargo, propietario y deudor se distinguen; una discrepancia documental
    produce `pendiente_identidad_contrario` y bloquea el requerimiento.
31. La etiqueta Gmail no se crea ni se mueve antes de confirmar la rama judicial o
    extrajudicial y conserva jerarquía, color e hilos.
32. La autorización única sustituye los antiguos gates previos para valores con procedencia
    concordante; una contradicción material bloquea y toda escritura queda
    `pendiente_revision_humana` hasta el gate posterior.
33. Un código de equipo repetido no crea conflicto, un W-code existente entra por
    `--case-id` y `--force` nunca crea una carpeta sombra.
34. Todo intake incremental usa `--crm skip`; un expediente CRM preexistente se registra y
    descarga antes de ejecutar la sala de máquina.
35. B2–B5 conservan `--case-id`, autodetección desde `folder-id`, tags de alta,
    normalización telefónica y evento `archivado`.
36. El intake conserva crudo, nombres originales, hashes y locks, y nunca toca
    `90_Notas personales/`.
37. Dos corridas de sala de máquina no se solapan y una reconstrucción detecta derivados
    huérfanos antes de validarse.
38. Un caso judicial no pasa por los entrypoints extrajudiciales ni puede terminar
    `crm_ficha_completa` mientras falte el adaptador judicial verificado.
39. Una relación CRM sin readback no se reenvía ni se declara idempotente; queda
    `escritura_sin_readback`.
40. El archivo ordenado por el abogado verifica CRM, actuación, Gmail, Drive, `_caso.md` y
    evento forense antes de declararse completo.
41. Dos ramas solapadas descargan a staging disjunto y sus commits serializados conservan la
    unión de entradas en manifest, log, `_caso.md` y `estado.json`; no hay lost updates.
42. Sustituir o retirar un fichero Drive conserva los bytes anteriores, la generación y el
    tombstone, y el inventario vigente no procesa el historial como si fuera evidencia nueva.
43. El piloto LeadHub ejecuta y mide por separado la vía Nikolai y la vía Marta antes de
    proponer el cambio del contrato definitivo en `FeesDefender-crm`.
44. Una ficha con `pendiente_revision_humana` no habilita ningún requerimiento ni demanda;
    revisión + GET son necesarios incluso cuando el primer GET coincidió.
45. Una corrección humana en Sudespacho se refleja por GET en YAML y `_caso.md`; el CAS
    sustituye la `candidate_revision` esperada, bloquea cualquier cambio independiente y
    termina con igualdad verificada.
46. Un test de timeout después del commit remoto deja `escritura_resultado_desconocido`,
    encuentra y adopta exactamente un expediente por referencia y demuestra que no hubo
    segundo POST.
47. `estado.json` existe desde la primera entrega y vincula cada fuente y fase a una
    `input_generation`; una fuente saltada no incrementa `consecutive_unchanged`.
48. Cambiar el inventario de una fuente incrementa la generación, invalida atómicamente
    todas las fases derivadas y reinicia el punto fijo.
49. Los perfiles y respuestas temporales del enriquecimiento postal se eliminan al terminar;
    todo log técnico transitorio, de éxito o fallo, desaparece en un máximo de 7 días y no
    conserva hash ni otro derivado determinista del domicilio.
50. La primera entrega no crea `scripts.apertura_expediente`: el estado mínimo y la sección
    crítica se cablean detrás de los entrypoints existentes.

## 15. Estrategia de entrega

La implementación se detallará en un único plan y en este orden:

1. Construir la sección crítica por caso y `estado.json` mínimo; staging disjunto, commit
   serializado, generaciones e invalidación, sin crear un CLI coordinador.
2. Cerrar el alta de resultado incierto y el dominio monetario; completar `crm_ficha` con
   procedencia, modelo postal, actualización de registros preexistentes, revisión humana
   posterior, sincronización de `_caso.md` y readback campo a campo, sin romper B2–B5.
3. Cerrar por separado los contratos pendientes de Drive, Gmail, Sudespacho, sala de
   máquina, sala de lectura, viabilidad y el piloto LeadHub.
4. Cablear el orden vigente mediante los entrypoints existentes, aplicar la adjudicación
   expresa del §16 y actualizar el runbook sin borrar sus gotchas todavía válidos.
5. Ejecutar una prueba E2E con fixtures sin PII y una apertura real controlada.
6. Medir las omisiones de coordinación que permanezcan.
7. Solo si esa evidencia lo exige, diseñar el coordinador fino o un ledger adicional.

Cada bloque se construirá con TDD. Las integraciones vivas tendrán pruebas de contrato
separadas de la suite rápida y nunca usarán datos reales en fixtures versionados.
Este orden no es autorización para planificar todavía: la rev. 2 permanece pendiente de R2.

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
| Contrato LeadHub de 2026-07-31: Marta ejecuta | Excepción piloto, no sustitución definitiva | Nikolai principal y Marta subsidiaria; se miden ambas vías con actor/cuenta reales y solo después se modificará el contrato en `FeesDefender-crm` |
| Runbook §§0–5: entorno, intake y sala de máquina | Conservados | Rigen salvo los cambios expresos de esta tabla y los nuevos verificadores materiales |
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
- contrato de descarga de fichas LeadHub del repositorio hermano `FeesDefender-crm`
  (31 de julio de 2026).

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
no convierte la spec en lista: la rev. 2 queda pendiente de R2.

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
