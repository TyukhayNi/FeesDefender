---
estado: propuesto (brainstorming aprobado; pendiente de revisión)
dueño: Nikolai Tyukhay
fecha: 2026-08-15
---

# Diseño — Apertura integral sobre componentes existentes

> **Fuente única del diseño de apertura integral.** Esta spec reúne en un solo documento la
> apertura, el descubrimiento de fuentes, el intake, las salas, el prerrelleno y los dos
> CRM. No se crearán specs separadas por adaptador. Las specs anteriores siguen siendo
> antecedentes o contratos internos de cada componente. En el orden E2E, los gates y el
> cierre solo prevalecen las sustituciones expresas adjudicadas en el §16; una omisión no
> deroga una regla anterior.
>
> **Naturaleza:** diseño. No autoriza todavía la implementación. El siguiente artefacto,
> tras revisar esta spec, es un único plan de implementación.

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
ejecutará sin supervisión y solo se detendrá ante riesgo de mezclar expedientes, una
identidad materialmente dudosa o una decisión jurídica.

El flujo no decide la viabilidad. Prerrellena datos y evidencia; el veredicto y el
recuadro ejecutivo permanecen reservados al abogado.

## 2. Alcance y fronteras

El diseño coordina cuatro sistemas externos, que conservan contratos distintos:

1. **Gmail de Engel & Völkers:** descubrimiento expansivo, etiquetado y exportación fiel.
2. **Drive de Engel & Völkers:** fuente de la carpeta operativa de la propiedad.
3. **LeadHub de Engel & Völkers:** lectura y captura probatoria mediante el proyecto
   autónomo `FeesDefender-crm`.
4. **Sudespacho:** CRM del despacho; alta, ficha completa, relaciones y descarga del
   gestor documental a `00_Input/05_CRM/`.

LeadHub y Sudespacho son adaptadores diferentes. Nunca se denomina a Sudespacho «CRM de
Engel» ni se mezclan sus modelos de identidad, credenciales o salida.

Incluye:

- apertura o reutilización del expediente;
- alta y ficha completa de Sudespacho;
- descubrimiento repetido de toda la evidencia relacionada;
- intake trazable desde las cuatro fuentes;
- sala de máquina, sala de lectura y prerrelleno de viabilidad;
- invalidación, reanudación y cierre verificable.

No incluye:

- el juicio jurídico de viabilidad;
- la redacción de escritos;
- acciones de comunicación, edición o mutación en LeadHub;
- almacenamiento o automatización de contraseñas;
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
2026-07-09 y la revisión manual obligatoria de `_ficha_crm.yaml` de la spec de 2026-07-18.
Cuando los datos están anclados, son unívocos y superan las validaciones, las escrituras
ordinarias continúan sin otra pregunta. Una discrepancia material, una identidad dudosa o
un dato que exige juicio jurídico sigue bloqueando; `--yes` no lo convierte en automático.

La nueva entrega no puede hacer regresar capacidades ya construidas en B2–B5:

- `--case-id` para intake incremental, excluyente con los flags de alta;
- autodetección de equipo, código y sufijo desde `--folder-id`, con precedencia de los
  valores explícitos;
- tags de equipo y ciudad durante el alta;
- normalización de teléfonos en los DTO que comparten REST y legacy;
- evento forense `archivado` en `INTAKE_EVENTS`.

No se integra `FeesDefender-crm` por importación. Se invoca como proceso autónomo mediante
un contrato versionado de solicitud/resultado y se recibe su paquete probatorio.

## 4. Identidad y preflight

Antes de escribir:

1. Verificar entorno canónico, unidades montadas, ejecutables, permisos y disponibilidad
   de los cuatro adaptadores.
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
- registrar por separado `crm_alta`, `crm_ficha_pendiente` y `crm_ficha_completa`.

La cuantía se representa como decimal exacto de extremo a extremo. Después de cada
escritura en Sudespacho se exige una lectura de verificación; un `2xx` no basta.

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
fantasma y registra `adaptador_judicial_no_disponible` hasta que exista un camino judicial
equivalente y verificado. El alta manual o parcial no permite declarar `crm_alta` ni
`crm_ficha_completa` sin readback del expediente judicial correspondiente.

## 6. Descubrimiento paralelo

Después de fijar la identidad del expediente arrancan en paralelo cuatro ramas:

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

Se descarga la carpeta de la operación con la identidad ya fijada. El adaptador entrega
inventario, ocurrencias, hashes y errores; no decide por sí mismo que el caso está completo.

### 6.3 LeadHub E&V

Se solicita al proyecto `FeesDefender-crm` una captura integral, de solo lectura, usando el
perfil de navegador dedicado y la sesión autenticada por el abogado. La misma pasada sirve
para uso operativo y para el paquete probatorio e incluye, conforme al contrato de dicho
proyecto:

- propiedad;
- contactos relevantes;
- leads;
- actividades;
- registro de cambios;
- exposé y demás artefactos fijados por su diseño;
- PDF, transcripción, datos estructurados, diligencia y manifiesto.

La salida identifica cuenta, rol y persona ejecutora. Se mantienen la lista blanca de
operaciones GraphQL de lectura, el bloqueo de mutaciones, la prohibición de coordenadas y
de controles de comunicación o edición, y el fallo ruidoso ante cambios de interfaz.

El paquete se deposita en un lote canónico nuevo:

```text
00_Input/AAAA-MM-DD_leadhub_NN/
```

Para ello se añade `leadhub` al catálogo de fuentes de intake, con su evento propio,
manifiesto y hashes. No se reutiliza `05_CRM`, que pertenece exclusivamente a Sudespacho.

El perfil dedicado es un directorio de navegador aislado del perfil cotidiano. El abogado
introduce sus credenciales en la ventana del perfil, pero el script nunca las recibe; solo
se conserva la sesión resultante mientras siga vigente. Una sesión abierta en el Chrome
habitual no demuestra que el perfil dedicado esté autenticado y no se migran cookies entre
perfiles.

El adaptador debe negociar capacidades antes de prometer una captura. A fecha de esta spec,
`FeesDefender-crm` contiene el arnés de medición y sus guardas, pero no el recolector ni el
empaquetado probatorio completos. `scripts/medir.py`, además, usa referencias de censo fijas:
no puede presentarse como descargador parametrizable. Hasta que el contrato de resultado
esté implementado y probado, la rama termina en `adaptador_no_disponible`, nunca en
`completada`.

Si la sesión ha caducado, la rama queda en `espera_login`; las demás continúan. El caso
puede quedar `preparado_con_pendientes`, pero no `completo`, mientras falte esta captura.

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

Cada rama entrega un lote inmutable con manifiesto. El flujo:

- verifica nombres de destino únicos antes de copiar;
- calcula SHA-256 después de materializar;
- deduplica entre fuentes por contenido sin perder la procedencia ni las ocurrencias;
- conserva alias cuando el mismo documento aparece en correo, Drive o CRM;
- impide que el truncado de nombres sobrescriba dos EML distintos;
- registra entradas, salidas y errores en el manifiesto o ledger propio del componente,
  sin incluir cuerpos documentales.

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
5. Completar y verificar la ficha de Sudespacho: cliente propio, contrario y
   colaboradores.

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

Sin que el operador tenga que pedirlo en cada expediente, la ficha confirmada incorpora:

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

Si el código postal o la provincia no constan en la documentación, el adaptador los busca
automáticamente a partir del domicilio. Aplica este orden: documento del propio expediente
que identifique inequívocamente a la persona y la dirección; localizador oficial de Correos;
fuente municipal, catastral u otra fuente pública equivalente. Una fuente comercial aislada
solo sirve como indicio y exige una segunda fuente independiente coincidente. Registra en
la ficha maestra local dirección consultada, fuentes, resultado y nivel de confianza. Si
hay resultados incompatibles, varias coincidencias o una dirección insuficiente, fija
`pendiente_domicilio` y bloquea la preparación y el envío del requerimiento.

La identidad normalizada se proyecta siempre a tres destinos:

1. **`_caso.md`:** ficha maestra local. Mantiene `meta.cliente` y `meta.contraparte` como
   resúmenes retrocompatibles y conserva la ficha completa en `meta.partes.contrario`. La
   actualización modifica también `## Partes`, sin perder `## Navegación` ni contenido del
   abogado.
2. **`_ficha_crm.yaml`:** entrada operativa y reanudable del adaptador de Sudespacho.
3. **Sudespacho:** ficha remota vinculada al expediente.

`scripts.crm_ficha` es el único punto de cableado extrajudicial: carga y normaliza la ficha
ya anclada, completa `_caso.md`, crea o actualiza el contrario aunque ya existiera y
verifica por GET todos los campos. `core.case_manager` expone una operación pequeña de
sincronización que reutiliza su escritura atómica y no absorbe lógica de CRM.

Los tags de equipo y ciudad permanecen en el alta. La ficha completa vincula el cliente
propio correcto, el contrario, los colaboradores propios de E&V y las notas iniciales. Un
procurador o letrado de la parte contraria nunca se clasifica como colaborador. La actuación
facturable solo se crea cuando proceda y se vincula expresamente; la tarifa sigue reservada
a la UI. Cuando se implemente la rama judicial, Juzgado y autos deberán tratarse mediante su
relación intermedia y sus enums propios; no se inventarán campos planos ni se confundirán
NIG, referencia propia y número de autos. Hasta entonces se aplica el bloqueo del §5.

Un campo vacío de `_caso.md` se completa automáticamente. Dos valores no vacíos
incompatibles no se sobrescriben en silencio: producen `pendiente_sincronizacion`. La ficha
de la entidad solo queda completa cuando `_caso.md`, `_ficha_crm.yaml` y el GET de
Sudespacho coinciden campo por campo.

Las relaciones tienen un contrato distinto. Mientras no exista readback fiable, una
relación ya intentada no se vuelve a enviar automáticamente al reanudar: el flujo registra
`escritura_sin_readback` y no afirma idempotencia ni `crm_ficha_completa`. Solo una lectura
verificable o una operación de vínculo demostrablemente idempotente permite cerrar ese
subgate. La ausencia de readback no se maquilla con un nuevo POST ciego.

## 9. Bucle de estabilización

Después del primer procesamiento se vuelven a consultar Gmail, Drive, LeadHub y
Sudespacho. Si aparece evidencia nueva:

- un nuevo fichero de intake invalida sala de máquina, sala de lectura y prerrelleno;
- una nueva extracción invalida sala de lectura y prerrelleno;
- una nueva evidencia citada invalida el prerrelleno;
- un nuevo dato material sobre partes invalida la ficha del paso 8.1 y cualquier
  requerimiento derivado;
- un cambio de identidad invalida toda la ejecución y exige intervención.

Solo se recalculan las fases dependientes. El caso alcanza estado estable tras dos
comprobaciones consecutivas sin novedad y con todas las invariantes verdes. Este punto fijo
evita que un correo descubierto tarde deje obsoletas las salas o el informe.

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

Cada fase puede estar en:

- `pendiente`;
- `en_curso`;
- `completada`;
- `pendiente_reintento`;
- `espera_login`;
- `espera_decision_juridica`;
- `fallida`.

En la primera entrega no se crea una máquina de estados paralela. Cada componente conserva
su estado en los artefactos que ya gobierna: `_caso.md`, manifiestos, marcadores de intake y
resultados de verificación. `_caso.md` refleja el estado de alto nivel y los estados
materiales como `pendiente_domicilio` o `pendiente_sincronizacion`.

Solo si la prueba E2E demuestra que esos artefactos no permiten una reanudación inequívoca,
el coordinador fino podrá añadir una fotografía atómica en:

```text
01_Procesado/_apertura/estado.json
```

En ese mismo supuesto, cada ejecución tendrá un ledger append-only:

```text
01_Procesado/_apertura/ejecuciones/<run_id>.jsonl
```

El ledger no sustituye los manifiestos de los componentes. Registra fase, entradas,
salidas, hashes, duración, intentos, errores y decisión de invalidación, sin credenciales ni
cuerpos documentales. Su necesidad y su esquema deben derivarse de un fallo E2E reproducido,
no de anticipación arquitectónica.

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
- relación CRM sin readback fiable cuando ya consta un intento de escritura.

La ausencia de login en LeadHub no detiene las ramas independientes: genera
`espera_login` y un cierre parcial explícito.

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
| Cuantía decimal redondeada | Importe erróneo | Decimal exacto y lectura posterior por API |
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
| LeadHub fuera del flujo | Datos y prueba omitidos | Captura paralela obligatoria |
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
| Caso judicial entra por el alta extrajudicial | Expediente fantasma y modelo CRM incorrecto | `--crm skip` y `adaptador_judicial_no_disponible` |
| Derivado abierto en Word bloquea la regeneración | Atomización parcial con exit global `0` | Preflight de locks `~$*`, publicación transaccional y reintento dirigido |
| Dos corridas de sala de máquina se solapan | Cobertura fusionada y derivados huérfanos | Gate de proceso activo, salida real y reconciliación de huérfanos |
| Sesión autenticada solo en Chrome cotidiano | LeadHub parece disponible, pero el colector no puede usarla | Preflight del perfil dedicado y estado `espera_login` o `adaptador_no_disponible` |
| Apellidos guardados pero nombre visible incompleto | Listados, ficha y escritos muestran solo el nombre de pila | `nombre` contiene el nombre completo, además de los apellidos separados, y se verifica por GET |
| Contrario sin código postal o provincia | Requerimiento no direccionable con seguridad | Enriquecimiento postal automático; `pendiente_domicilio` bloquea preparación y envío si hay ambigüedad |
| Datos personales con capitalización irregular | Escritos y plantillas inconsistentes | Mayúsculas en texto libre, email en minúsculas y literales exactos para campos `Select` |

## 13. Resultado final

El resumen distingue exactamente:

- `completo`: estado estable y todas las ramas obligatorias verificadas;
- `preparado_con_pendientes`: ramas independientes terminadas, con un pendiente explícito
  como `espera_login`;
- `bloqueado`: gate material que impide seguir sin riesgo.

Incluye el estado de cada fase, pendientes, número de intentos, inventarios conciliados y
rutas de los manifiestos; no vuelca secretos ni contenido sensible al terminal.

## 14. Criterios de aceptación

1. La secuencia documentada de entrypoints existentes completa una apertura normal sin
   pedir datos que puedan obtenerse de las fuentes autorizadas.
2. Interrumpir y reanudar en cualquier fase no duplica efectos confirmados.
3. Ninguna fase se marca completa solo por un código de salida cero.
4. Todo fichero procesado resuelve a una fila de manifiesto y su hash coincide.
5. Ningún destino se repite con hashes distintos.
6. Gmail descubre hilos recibidos por listas institucionales aunque el usuario no participe.
7. El pull de Sudespacho bloquea referencias ajenas y reconcilia el universo listado.
8. LeadHub no ejecuta mutaciones ni acciones de comunicación.
9. Una captura LeadHub incompleta nunca recibe veredicto de entrega completa.
10. Un nuevo correo o documento invalida y regenera las salidas dependientes.
11. La cuantía conserva precisión decimal exacta en Drive, informe y Sudespacho.
12. `VIABILIDAD` y el recuadro ejecutivo quedan en blanco durante el prerrelleno.
13. El resumen final usa uno de los tres estados definidos en §13.
14. La suite E2E reproduce, sin PII, colisiones, intake tardío, ruta desviada, descarga
    parcial, login caducado y reanudación tras interrupción.
15. Un resolvedor no crea estructura alguna y rechaza una carpeta sombra que solo coincide
    por nombre.
16. Los controles internos y temporales `~$*` no cuentan como documentos materiales.
17. La sala de lectura no pasa si su manifiesto cuadra pero el layout, la taxonomía o los
    nombres de destino infringen el contrato vigente.
18. Sudespacho distingue un gestor documental vacío confirmado de una respuesta con errores.
19. LeadHub no se marca disponible mientras solo exista el arnés de medición.
20. Toda ficha de contrario releída por API contiene nombre visible completo, apellidos
    separados, identificador y domicilio con código postal, población y provincia.
21. Los campos de texto libre del contrario quedan en mayúsculas y el email en minúsculas;
    los `Select` conservan el literal exacto del CRM.
22. Una dirección postal incompleta o ambigua impide preparar o enviar el requerimiento y
    produce `pendiente_domicilio`, no un dato inferido silenciosamente.
23. Un código postal resuelto automáticamente conserva fuente, consulta y confianza en la
    ficha maestra local sin filtrar datos personales a Git.
24. `scripts.crm_ficha` sincroniza siempre la identidad normalizada en `_caso.md`,
    `_ficha_crm.yaml` y Sudespacho, sin exigir una instrucción adicional del operador.
25. Un contrario ya existente se completa mediante GET, merge, PUT y GET; vincularlo no se
    considera ficha completa.
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
32. La autorización única sustituye los antiguos gates por escritura solo para datos
    unívocos; una ambigüedad material continúa bloqueando.
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

## 15. Estrategia de entrega

La implementación se detallará en un único plan y en este orden:

1. Completar `crm_ficha`: modelo postal, actualización de registros preexistentes,
   sincronización de `_caso.md` y readback campo a campo, sin romper B2–B5.
2. Cerrar por separado los contratos pendientes de Drive, Gmail, Sudespacho, sala de
   máquina, sala de lectura, viabilidad y LeadHub.
3. Cablear el orden vigente mediante los entrypoints existentes, aplicar la adjudicación
   expresa del §16 y actualizar el runbook sin borrar sus gotchas todavía válidos.
4. Ejecutar una prueba E2E con fixtures sin PII y una apertura real controlada.
5. Medir las omisiones de coordinación que permanezcan.
6. Solo si esa evidencia lo exige, diseñar el coordinador fino y el mínimo estado adicional.

Cada bloque se construirá con TDD. Las integraciones vivas tendrán pruebas de contrato
separadas de la suite rápida y nunca usarán datos reales en fixtures versionados.

## 16. Relación con documentación anterior

Esta spec gobierna el orden E2E y los gates nuevos, pero no deroga en bloque los dos
diseños anteriores ni el runbook. Sus contratos de componente y sus gotchas operativos
siguen vigentes salvo sustitución expresa en esta tabla:

| Fuente y decisión | Estado | Contrato vigente |
|---|---|---|
| 2026-07-09 D1: core compartido y frentes local/Cowork | Conservada | Lógica en `core`; CLIs y skills finos con músculos de I/O distintos |
| 2026-07-09 D2: colisiones `ask`/`--force` | Sustituida parcialmente | Código de equipo repetido queda cubierto por `--yes`; W-code y referencia siguen siendo gates estrictos conforme a §4 |
| 2026-07-09 D3: confirmar cada alta CRM | Sustituida | Una autorización `--yes` cubre efectos ordinarios unívocos; las ambigüedades siguen bloqueando |
| 2026-07-09 D4: hash tras materializar | Conservada | SHA-256 y log por fichero en todo intake |
| 2026-07-09 D5: `scripts.abrir_caso` | Conservada | Se completa el entrypoint existente; no nace otro coordinador en la primera entrega |
| 2026-07-18 B1: `crm_ficha` separado después de viabilidad | Conservada y ampliada | Se ejecuta tras la lectura documental y sincroniza `_caso.md`, YAML y CRM |
| 2026-07-18: revisión humana obligatoria del YAML | Sustituida | La ficha unívoca continúa automáticamente; discrepancia o juicio jurídico bloquean |
| 2026-07-18 B2–B5 | Conservadas | Rige la cláusula de no regresión de §3 y el criterio 35 |
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
- `FeesDefender-crm/docs/superpowers/specs/2026-07-31-descarga-fichas-crm-leadhub-design.md`.

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
Sudespacho y el prerrelleno están materializados; queda fuera del cierre `completo` la
captura probatoria integral de LeadHub y el readback de relaciones del CRM.
