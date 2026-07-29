# FeesDefender dual: expediente activo local/Drive — diseño marco

**Fecha:** 2026-07-29.
**Estado:** **rev. 2** (2026-07-29), tras la revisión adversarial de Claude Code
con veredicto **REQUIERE REVISIÓN** (4 bloqueantes B0 + 10 hallazgos A + 5 M).
Los cuatro B0 y los diez A están **aceptados y resueltos en el contrato**; el
detalle y la adjudicación de cada uno viven en el **§20** y en
`2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`.
**Naturaleza:** SPEC marco. No es un plan de implementación ni autoriza una
migración monolítica.
**Antecedentes directos:**

- `2026-07-14-expediente-scratch-design.md` (su Cluster B queda **absorbido**
  por esta arquitectura: `local_scratch`, `--case-dir` y `promover` son piezas
  de aquí, no de allí);
- biblioteca de checkout/checkin (`core.repository_checkout`);
- el diseño de la **enumeración recursiva del atomizador** (`MEJORAS #98`), que al
  redactar esta SPEC vive en la rama `claude/98-enumeracion-recursiva` y **todavía
  no está en esta**. Se cita por número y rama a propósito: escribir aquí su
  nombre de fichero dejaría una cita rota mientras esa rama no se mergee (guard
  `tests/test_docs_gobernanza.py::test_citas_a_specs_y_plans_existen`);
- `docs/ARQUITECTURA.md` y `docs/ARQUITECTURA_RELACIONES.md`;
- `docs/MEJORAS_FUTURAS.md` **#93** (ciclo de vida del lock), **#94** (el
  montaje `G:` no sirve para verificar), **#95** (rendimiento medido del
  checkout/checkin) y **#96** (el guard de escritura se dispara sobre la copia
  prestada y ahí no protege de nada). **#96 es dependencia dura del §6.3**: la
  proyección local de `_caso.md` es exactamente el disparador del bug que #96
  describe.

## 1. Problema

FeesDefender ya puede operar sobre rutas locales o sobre un Drive montado en
algunos flujos, pero no dispone de un contrato único que determine **qué copia
de un expediente es la operativa**.

Hoy conviven, entre otros, estos mecanismos:

- `CASOS_ROOT` y `case_locator` resuelven un caso dentro de una sola raíz
  configurada;
- varios motores aceptan un `Path` y son indiferentes al almacenamiento;
- checkout/checkin bloquea el expediente de Drive y crea una copia local;
- el expediente scratch permite que un caso nazca en local;
- algunos scripts resuelven siempre por `CASOS_ROOT`;
- algunas skills deciden por prosa entre filesystem, `expedientes-xl` y
  conectores de Drive;
- determinados plugins solo ven `G:`/`H:`, mientras que otros motores solo
  pueden ejecutarse en el PC con el repositorio y las credenciales locales.

La consecuencia peligrosa no es que falte soporte para rutas locales. Es que
dos puntos de entrada pueden resolver de forma distinta el mismo caso. Durante
un checkout, un proceso puede escribir en la copia local y otro en Drive,
creando un *split brain* incompatible con la custodia y la idempotencia.

La enumeración recursiva del atomizador de email corrige la visibilidad de los
`.eml` anidados, pero no resuelve este problema arquitectónico.

## 2. Objetivo y definición de «dual»

FeesDefender será dual cuando todos los puntos de entrada migrados:

1. resuelvan el mismo **expediente activo**;
2. apliquen la misma política de bloqueo y capacidades;
3. produzcan el mismo resultado de negocio sobre local o Drive, salvo los
   campos de procedencia, custodia, ruta y tiempo que deban diferir;
4. no cambien de almacenamiento silenciosamente;
5. registren la trazabilidad en la copia operativa y la reconcilien al publicar
   o hacer checkin;
6. declaren con precisión cuándo el runtime no puede acceder a la copia activa.

«Dual» no significa que cualquier entorno pueda acceder físicamente a cualquier
ruta. Cowork en la nube no puede alcanzar una carpeta del Desktop y un conector
acotado a `G:`/`H:` no puede escribir en `C:`. En esos casos el flujo debe
abortar sin tocar la copia de Drive y recomendar el runtime que sí tiene acceso.

Tampoco significa que Gmail, CRM o Google Drive funcionen sin red o sin
credenciales. La paridad afecta a la **ubicación del expediente**, no elimina
las dependencias externas.

## 3. Decisiones cerradas

### 3.1. Canon y copia operativa

- Un expediente publicado tiene su fuente canónica en el Drive del despacho.
- Si está `disponible`, la copia operativa puede ser la de Drive.
- Durante un checkout, Drive conserva el canon y el lock, pero la copia local
  es la **única copia operativa y escribible**.
- Un expediente puede nacer como scratch local. Es válido para trabajar, pero
  no adquiere custodia canónica ni colaboración hasta su promoción.
- Un scratch puede permanecer local mientras el usuario lo decida. El sistema
  debe mostrar siempre que no está publicado.

### 3.2. Escritura exclusiva

No se admite edición simultánea del mismo expediente.

- Solo el titular del checkout puede modificar el caso, desde la copia local
  vinculada al nonce vigente.
- Los demás usuarios pueden leer el estado compartido del lock, pero no
  incorporar documentos ni generar derivados en el expediente.
- Si necesitan aportar un documento, se lo entregan al titular por el canal
  ordinario; el titular lo incorpora y registra desde la copia local.
- No se construye una bandeja nueva de entregas.
- `_pendiente_checkin/` deja de ser el camino ordinario para aportaciones
  durante un checkout. Se conserva inicialmente solo para compatibilidad y
  recuperación de contenido anterior; una sub-SPEC decidirá su retirada.
- Un intento bloqueado no crea un falso evento de incorporación.

**Conmutación atómica del guard (B0-4).** `decidir_escritura` es una función
**pura del estado**: no puede distinguir «mutación nueva» de «contenido ya
existente», así que «denegar lo nuevo y desviar lo legacy» no es implementable
como dos políticas simultáneas. Por tanto:

- la Fase 2 cambia `decidir_escritura` a **denegar** para todo estado distinto
  de `disponible` —`conflicto` incluido— y lo hace **para todos los llamadores a
  la vez** (es un único punto de estrangulamiento: `case_manager.dir_intake` /
  `guard_escritura`, `intake_lotes.reservar_lote`, `intake_manual`,
  `intake_drive`, `email_export.email_dest_dir`);
- el evento `pendiente_checkin` **deja de emitirse** ese mismo día; se conserva
  en `INTAKE_EVENTS` solo para leer logs históricos;
- la única lectura restante de la bandeja es la integración de contenido **ya
  depositado** durante el checkin;
- **criterio de retirada, inequívoco:** cero ficheros bajo `_pendiente_checkin/`
  en todos los casos vivos, verificado por inventario y por API (no por el
  montaje, `MEJORAS #94`), en un PR separado.

Se acepta que esa conmutación **rompe** temporalmente el intake de los
componentes aún no migrados sobre un caso prestado: el remedio es que fallen en
alto con `CASE_LOCKED`, no que sigan escribiendo en el canon.

La comprobación del lock ocurre **antes** de descargar, copiar, transformar o
crear bytes.

### 3.2-bis. Qué significa «cero escritura» (A-3)

La promesa de §14.1 («checkout ajeno → cero bytes») se evalúa en **cuatro
planos**, y un componente no puede declararla cubriendo solo el primero:

1. **Árbol del caso.** Ningún fichero creado, modificado, movido ni borrado.
2. **Almacenamiento canónico.** Tampoco **creación de directorios** ni de
   ficheros de estado de canal. Hoy se incumple en al menos cuatro sitios
   verificados: `intake_log.append_event` hace `mkdir(parents=True)` sobre la
   ruta que devuelve `caso_path`; `email_export._save_export_index` /
   `_save_resolved_links` escriben en `path_for(resolve_ref(case_id))/00_Input`
   **ignorando el destino recibido y sin pasar por el guard**;
   `catalogo_documental.save_catalog` hace `mkdir` + `write_text` sin guard; y
   `scripts.sala_maquina plan`, documentado como «no escribe nada», escribe
   `_segmentacion.md` de cada bundle detectado.
3. **Servicios externos.** Ninguna llamada mutante a CRM, Gmail o Drive E&V. Las
   lecturas permitidas se declaran por operación.
4. **Estado local de aplicación.** Registro privado, cachés y sentinels de
   Streamlit no se marcan «hecho» antes de que el efecto exista (regla ya
   vigente en `CLAUDE.md`).

Corolario de capacidades: `scripts.sala_maquina plan` **necesita `write_case`**,
no `read_case`. Ningún subcomando se cataloga como lectura sin comprobarlo
contra el código.

### 3.3. Servicios externos

Cuando la copia activa sea local:

- Gmail, CRM o Drive E&V pueden leerse si el runtime dispone de acceso;
- el titular puede descargar documentos desde esas fuentes directamente al
  expediente local;
- ninguna operación puede caer silenciosamente en la copia canónica de Drive;
- las mutaciones canónicas —alta o actualización de CRM, publicación, cambio
  de custodia— se aplazan a `promover` o `checkin`, salvo una excepción
  protocolaria definida expresamente;
- una operación que no soporte destino local aborta antes de producir efectos.

### 3.4. Enfoque elegido

Se adopta un contexto central de expediente activo, denominado
`CaseWorkspace`. Se descarta por ahora una abstracción completa de
almacenamiento. El fundamento y la vía de evolución se conservan en el §13
para revisión adversarial.

## 4. Invariantes

Estos invariantes gobiernan todas las sub-SPECs:

1. **Un caso, una copia operativa.**
2. **Fail closed.** La ambigüedad o falta de verificación bloquea la mutación.
3. **Sin fallback silencioso.** Un fallo de acceso local nunca redirige a Drive.
4. **Lock compartido, ruta privada.** Drive conoce titular, máquina, tiempo y
   nonce; la ruta local solo vive en la máquina que la usa.
5. **Los entrypoints mutantes resuelven primero.** Ninguna CLI, UI, skill o tool
   de plugin puede escribir antes de obtener un `CaseWorkspace` autorizado.
6. **Motores puros conservados.** OCR, atomizadores, renderizadores y demás
   motores que ya trabajan con rutas no se convierten en clientes de Drive.
7. **Protocolo separado de contenido.** Lock, manifests y reconciliación tienen
   reglas propias; no se mezclan como ficheros ordinarios.
8. **Sin pérdida.** Un conflicto de nonce, metadata o log conserva la copia
   local y no libera el lock automáticamente.
9. **Idempotencia por copia activa.** Una repetición trabaja sobre la misma
   copia y no duplica efectos canónicos.
10. **Paridad declarada, no presunta.** Un componente no se anuncia como dual
    hasta superar su matriz contractual local/Drive/checkout.
11. **El lock coordina; no autentica.** Drive y sus permisos siguen siendo la
    barrera de seguridad. Usuario, máquina y nonce evitan carreras y errores
    operativos, pero no constituyen una credencial criptográfica.

## 5. Modelo conceptual

### 5.1. `CaseRef`

Identidad estable del caso, independiente de su ruta. Contiene como mínimo:

- identificador interno o W-code;
- identificador estable del expediente, cuando exista;
- referencia canónica de Drive, cuando esté publicado.

El nombre de carpeta es una presentación y no basta como identidad.

**Unicidad exigible (A-8).** Hoy `case_locator.resolve_ref` resuelve el W-code
recorriendo `list_cases()` y devolviendo **el primero** cuyo `meta.id_go` casa,
sin comprobar duplicados; y `list_cases` deduplica por *nombre de carpeta*, no
por W-code. Con la proyección local del §6.3 habrá deliberadamente dos ficheros
de identidad con el mismo W-code. Por tanto:

- el `CaseCatalog` **devuelve `AMBIGUOUS_CASE`** cuando dos carpetas del catálogo
  comparten `id_go`; no elige por orden de escaneo;
- la proyección local lleva una marca (`meta.proyeccion_local: true` o
  equivalente) que la **excluye del catálogo**;
- el destino de un checkout **no puede residir bajo `CASOS_ROOT`**; el checkout
  lo rechaza en alto.

### 5.2. `WorkspaceMode`

Los modos normativos son:

| Modo | Canon | Copia operativa | Escritura |
|---|---|---|---|
| `drive_active` | Drive | Drive | Permitida |
| `local_checkout` | Drive | Local | Solo titular |
| `local_scratch` | Ninguno todavía | Local | Permitida |
| `blocked_foreign_checkout` | Drive | Local ajeno | Prohibida |
| `blocked_conflict` | Drive | Indeterminada | Prohibida |

Los modos `blocked_*` son resultados de resolución, no workspaces utilizables
por motores mutantes.

### 5.3. `CaseWorkspace`

Es un valor validado e inmutable durante una operación. Expone:

- `case_ref`;
- `mode`;
- `working_root: Path`, solo cuando el runtime puede acceder;
- referencia canónica, si existe;
- identidad del checkout: titular, máquina, nonce y timestamp;
- capacidades concedidas;
- procedencia y momento de la validación.

No descarga documentos, no hace OCR y no implementa lógica de negocio. Su
responsabilidad es responder: «¿dónde se trabaja y qué está permitido?».

El `CaseWorkspace` no debe almacenarse entre ejecuciones como autorización
permanente. Cada operación mutante vuelve a resolverlo; una operación larga
revalida antes de publicar efectos canónicos.

### 5.4. Capacidades

La primera versión define al menos:

- `read_case`;
- `write_case`;
- `ingest`;
- `generate_derivatives`;
- `mutate_canonical`;
- `checkout`;
- `checkin`;
- `promote`.

Los motores no deducen capacidades a partir de una letra de unidad. Las
reciben del contexto o son invocados por un entrypoint que ya las verificó.

| Modo | Leer | Ingestar/generar | Mutar canon | Cerrar ciclo |
|---|---:|---:|---:|---:|
| `drive_active` | Sí | Sí | Según operación | Checkout |
| `local_checkout` titular | Sí | Sí, en local | No durante trabajo | Checkin |
| `local_scratch` | Sí | Sí, en local | No | Promover |
| bloqueado | Solo diagnóstico autorizado | No | No | Resolver conflicto |

## 6. Fuentes de verdad y metadatos

### 6.1. Estado compartido en Drive

El `_caso.md` canónico conserva:

- `estado_repositorio`;
- `checkout_user`;
- `checkout_maquina`;
- `checkout_timestamp`;
- `checkout_nonce`;
- los metadatos canónicos ya existentes.

Nunca contiene la ruta local completa.

El contrato vigente de `case_checkout` incluye hoy
`details.ruta_local` en `_intake_log.jsonl` de Drive. La migración debe dejar de
emitirla y sustituirla por un identificador opaco de workspace. Los eventos
históricos no se reescriben automáticamente. Esta ruptura deliberada se
documentará en la sub-SPEC de checkout.

### 6.2. Registro privado de workspaces

Cada instalación local mantiene un registro fuera de los expedientes y del
repositorio, bajo un directorio configurable cuyo valor por defecto será el
estado de aplicación del usuario en Windows.

El registro asocia una `CaseRef` con:

- ruta local absoluta;
- referencia canónica, si existe;
- nonce y máquina;
- tipo `checkout` o `scratch`;
- última validación;
- versión de schema.

La escritura es atómica. El registro no contiene documentos ni secretos. Como
la ruta puede incluir datos identificativos, no se sincroniza, no se sube a
Drive y no aparece en mensajes dirigidos a otros usuarios.

Una ruta movida no se sigue por heurística. `--case-dir` permite validarla y
reparar expresamente el registro.

**Identidad de máquina (M-2).** `checkout_maquina` es hoy
`socket.gethostname()`, y se publica en el `_caso.md` que E&V puede ver. El §16
prohíbe la ruta, no el hostname. Decisión de esta rev.: en el canon viaja un
**identificador corto y estable derivado del hostname** (no reversible a ojo), y
el hostname legible vive solo en el registro privado. Los mensajes de bloqueo
muestran titular y fecha; la máquina, solo si el titular es el propio usuario.

### 6.3. Proyección local del protocolo

El checkout debe materializar en local la identidad y metadata necesarias para
que las funciones que dependen de `_caso.md` se comporten igual que en Drive.
No basta con copiar únicamente los documentos.

La sub-SPEC de checkout puede decidir el formato auxiliar del registro, pero
debe respetar este contrato físico de compatibilidad:

- la copia local dispone de la proyección en
  `00_Input/_caso.md`, la misma ruta relativa que esperan los consumidores;
- el fichero queda excluido del merge genérico y se reconcilia por el
  protocolo;
- el nonce y la referencia canónica quedan vinculados al workspace;
- los campos de lock siguen siendo propiedad de Drive;
- los metadatos de negocio modificables durante el checkout se reconcilian de
  forma explícita, no mediante copia ciega;
- un cambio inesperado en Drive desde el baseline produce conflicto.

**Dependencia dura con `MEJORAS #96` — se arregla ANTES de materializar.**
`case_manager.guard_escritura` decide leyendo `estado_repositorio` del `_caso.md`
**local** (vía `caso_path`). Hoy el checkout **no** baja ese fichero
(`MERGE_EXCLUSIONS`), el campo falta, `estado_de_fm` devuelve `disponible` por
defecto y el guard queda inerte: es la única razón por la que el pipeline
funciona sobre una copia prestada. En el momento en que esta SPEC materialice la
proyección con los campos de lock, el guard se activará sobre la copia local y
desviará el intake a `_pendiente_checkin/`, **fuera de `00_Input`**, que es lo
único que `sala_maquina.inventariar()` recorre: se depositarían documentos que
ni la sala de máquina ni la de lectura verían, con la corrida reportada como
correcta. Es exactamente el bug descrito en `MEJORAS #96`, y esta SPEC es su
disparador. Por tanto **la Fase 2 no materializa `_caso.md` hasta que el guard
distinga *dónde* escribe**: sobre el canon, desviar/denegar; sobre una copia de
trabajo identificada (presencia de `MANIFEST_CHECKOUT.json` o del propio
`CaseWorkspace` en modo `local_checkout`), **no** desviar.

**Propiedad y merge de los campos de `_caso.md` (exigido por la revisión).** La
sub-SPEC de checkout **debe** publicar una tabla campo → propietario → regla de
merge que cubra, como mínimo: `estado_repositorio`, `checkout_*` y
`ultimo_checkin_*` (**propiedad de Drive**, el local no los altera nunca);
`id_go`, `case_id` y la referencia canónica (**inmutables durante el préstamo**);
`ciudad` (**Drive gana**: hay un mutador propio, `case_locator.move_to_city`, que
mueve la carpeta y reescribe el frontmatter); `tipo_caso`, `cliente`, `partes`,
`juzgado` y `sudespacho_expedientes` (**editables en local**, con regla explícita
si ambos lados cambiaron). Sin esa tabla, «se reconcilian de forma explícita» no
es un contrato: es una intención.

**Auditoría local y su baseline (B0-2).** El checkout materializa también
`00_Input/_intake_log.jsonl` después de registrar `case_checkout`. Tres cosas que
la rev. 1 daba por hechas y **no lo estaban**:

1. **No existe baseline del log.** `MANIFEST_CHECKOUT.json` se construye desde
   `inventario_local`, que descarta todo lo que casa `MERGE_EXCLUSIONS` — y
   `_intake_log.jsonl` es una de ellas. Por tanto la Fase 2 **crea un artefacto
   de protocolo propio** con el hash y el número de líneas del log en el instante
   del checkout (campo separado del inventario, o `MANIFEST_LOG.json`). Sin él no
   hay «prefijo del baseline» contra el que comparar nada.
2. **La comparación es por eventos con identidad estable**, no por bytes: el
   canon **no** es append-only en la práctica —`_append_evento_drive` hace
   pull → `splitlines()` → filtrar vacías → `join` → push, con
   `errors="replace"`—, así que una comparación byte a byte divergiría en cada
   checkin y `errors="replace"` corrompe evidencia de forma permanente. Identidad
   mínima del evento: `(ts, actor, event, hash(details))`. La Fase 2 sustituye
   esa reescritura por un append real.
3. **Una cola no parseable BLOQUEA.** `intake_log.read_events` descarta en
   silencio las líneas corruptas; para reconciliar eso es inaceptable. Una línea
   parcial por crash conserva el local, bloquea el cierre y se declara al
   usuario; nunca se descarta.

El checkin solo integra el sufijo local tras verificar el prefijo contra ese
baseline. Después registra `case_checkin` en el canon **con clave de
idempotencia** (un reintento no añade un segundo `case_checkin`). Una divergencia
no explicada bloquea el cierre y conserva la copia local.

## 7. Resolución del expediente activo

Existe un único servicio de resolución utilizado por CLI, UI y adaptadores.

### 7.1. Entrada por ruta explícita

`--case-dir <ruta>` tiene prioridad sobre la búsqueda, pero no sobre la
seguridad:

1. normaliza y comprueba que la ruta existe;
2. lee su identidad local;
3. distingue scratch, checkout y Drive;
4. si es checkout y Drive está accesible, verifica estado y nonce;
5. si Drive no está accesible, permite trabajo local con el último checkout
   verificado, pero marca `mutate_canonical = false`;
6. si la ruta apunta a Drive bloqueado por otro checkout, aborta;
7. si identidad, manifest y registro se contradicen, aborta.

Trabajar offline no expira ni libera un checkout. El checkin debe revalidar el
nonce contra Drive. Si alguien canceló o sustituyó el lock, se declara conflicto
y se conserva el local.

### 7.2. Entrada por identificador

Para `W-XXXXX` o `case_id`:

1. normaliza la referencia y consulta candidatos del registro privado;
2. intenta localizar el caso canónico mediante el catálogo configurado;
3. si Drive está accesible, lee el estado compartido;
4. si está `disponible`, devuelve `drive_active`;
5. si está `prestado`, exige una entrada local con el mismo caso, titular,
   máquina y nonce;
6. si coincide y la ruta existe, devuelve `local_checkout`;
7. si pertenece a otra máquina, falta la ruta o no coincide el nonce, devuelve
   bloqueo;
8. si está `conflicto`, bloquea toda mutación;
9. si Drive no está accesible y hay exactamente un checkout local previamente
   verificado, permite trabajo local con `mutate_canonical = false`;
10. si tampoco hay un candidato local inequívoco, aborta.

Un scratch conocido por el registro local también puede resolverse por su
identidad. Si colisiona con un caso publicado o hay dos rutas locales posibles,
se exige `--case-dir`.

### 7.3. Precedencia y compatibilidad

- `--case-dir` es la selección explícita.
- `CaseWorkspaceResolver` es la vía ordinaria.
- `CASOS_ROOT` continúa como raíz del catálogo canónico y como configuración de
  compatibilidad; deja de ser un selector implícito de la copia operativa **para
  los componentes ya migrados**. Los componentes etiquetados
  `legacy_unresolved` lo conservan como selector hasta que reciben `--case-dir`:
  de lo contrario el modo `local_scratch` queda sin ninguna vía de trabajo entre
  la Fase 1 y la Fase 3 (**A-7**: `--case-dir` no existe hoy en ningún script, y
  `--casos-root` solo en `scripts/migrar_nombres_informe.py`; el Cluster B del
  diseño de scratch nunca se construyó, así que el override de entorno es hoy la
  **única** vía).
- `--casos-root` puede mantenerse para entornos de prueba o catálogos
  alternativos, pero no sustituye la validación del workspace.
- **`caso_path`/`path_for` dejan de devolver rutas inexistentes (A-5).** Su
  fallback actual —devolver la ruta *flat* cuando el caso no aparece— **es** el
  fallback silencioso a Drive que el invariante 3 prohíbe: combinado con el
  `mkdir` de cualquier escritor, materializa un expediente fantasma con nombre de
  W-code en la unidad compartida (bug ya ocurrido con W-02ZIIF). La Fase 1
  introduce modo estricto: resolver un caso ausente **lanza**; crear un caso
  nuevo pasa por una función explícita de creación. Ningún escritor hace `mkdir`
  de la raíz del caso.
- Ningún entrypoint —nuevo **ni existente**— debe llamar directamente a
  `caso_path` y asumir que el resultado es escribible. La prohibición limitada a
  «los nuevos» no cierra nada: los peligrosos son los que ya existen.

## 8. Flujos normativos

### 8.1. Caso disponible en Drive

1. El usuario solicita una operación por identidad.
2. El resolver comprueba `_caso.md`.
3. Devuelve `drive_active`.
4. El entrypoint verifica la capacidad necesaria.
5. El motor trabaja en `working_root`.
6. La auditoría se escribe en el caso canónico.

### 8.2. Checkout

1. Se adquiere y verifica el lock con nonce.
2. Se comprueba que el destino local **no está bajo `CASOS_ROOT`** (§5.1).
3. Se materializan contenido y baseline, excluyendo el protocolo del merge
   genérico.
4. **Se re-verifica el nonce contra Drive** (paso nuevo, A-1) antes de publicar
   nada más. Si ya no es el propio, el checkout **aborta**: no emite
   `case_checkout`, no escribe registro, y la copia parcial pasa a cuarentena
   (§16).
5. Se registra `case_checkout` en Drive sin ruta local (identificador opaco de
   workspace en su lugar).
6. Se materializan la proyección de metadata y el log ya actualizado.
7. Se escribe el registro local de forma atómica.
8. Desde ese momento Drive no admite nuevas mutaciones de contenido.
9. Los comandos por identidad de la misma máquina resuelven al local.
10. Los comandos de otras máquinas abortan e indican titular y timestamp.

**Toda mutación del lock es compare-and-swap (A-1).** El write-then-verify
actual solo protege la *adquisición*, y `_push_caso_md` es un `copyto` ciego que
sobrescribe el frontmatter que el proceso pulló al principio. Con el sync lag del
Drive, dos procesos que leen `disponible` antes de que ninguno haya escrito
**pueden creerse ambos titulares**: A escribe `nonce_A` y verifica antes de que B
escriba; B, que pulló el estado anterior, escribe `nonce_B` encima y verifica
después. Los dos siguen adelante. Por tanto:

- **ninguna** escritura del lock (adquirir, revertir, marcar `conflicto`,
  liberar) se publica sin releer y confirmar que el nonce vigente es el propio;
- un push cuya lectura previa diga `prestado` con otro nonce es imposible por
  contrato, no por convención;
- el rollback de un checkout fallido **no** puede limpiar el lock sin demostrar
  propiedad del nonce (hoy lo hace: `repository_cli.py` revierte con el
  frontmatter en memoria).

Si falla la materialización después de adquirir el lock, el checkout no queda
fingidamente completo: revierte el lock si puede demostrar que conserva el
nonce. Si ya emitió `case_checkout`, añade `checkout_cancelado`; si no puede
revertir de forma verificada, conserva el lock e informa de recuperación
necesaria.

### 8.3. Trabajo local del titular

1. El resolver valida registro, identidad y nonce disponible.
2. Gmail, CRM o Drive E&V pueden actuar como fuentes.
3. Todo contenido nuevo se deposita en el local.
4. Los derivados y eventos se generan en el local.
5. No se actualiza el caso canónico ni el CRM como efecto lateral oculto.

### 8.4. Intento de otro usuario

El flujo aborta antes de tocar bytes y devuelve, como mínimo:

- caso;
- estado `prestado`;
- titular;
- máquina, si es apropiado mostrarla;
- fecha;
- instrucción de enviar el documento al titular o esperar al checkin.

No muestra la ruta local y no escribe una aportación pendiente.

### 8.5. Checkin

1. Revalida lock, titular y nonce.
2. Calcula el merge contra el baseline.
3. Reconcilia contenido, metadata de negocio y log conforme a sus contratos.
4. Ante conflicto, conserva local, deja estado `conflicto` y no libera.
5. **Integra el contenido legacy de `_pendiente_checkin/`** (si queda alguno).
6. **Recalcula el inventario y verifica por hash TODO lo mutado**, no solo lo que
   subió el plan.
7. Registra `case_checkin` con clave de idempotencia.
8. Libera el lock únicamente tras verificación completa.
9. Retira o invalida el registro local según la política de cortesía vigente.

**Por qué este orden y no el vigente (A-2).** Hoy `repository_cli.cmd_checkin`
hace lo contrario en los tres pasos finales: verifica por hash **solo**
`files_from` (lo que el plan subió), **luego** registra `case_checkin` en verde,
**luego** integra la bandeja —cuyos fallos solo imprimen un aviso— y **después**
libera el lock, pase lo que pase. Resultado: contenido canónico movido a su ruta
definitiva **después** de la única verificación de integridad y **después** del
evento de cierre, con el lock liberado igualmente si la integración falló a
medias. Eso contradice el paso 7 de la rev. 1 («libera solo tras verificación
completa») y el invariante 8. Además, sin clave de idempotencia, un reintento
tras un fallo intermedio deja **dos** `case_checkin` verdes en el log forense.

**Un checkin que ya movió los bytes no puede terminar en traceback**
(`MEJORAS #93`, fallo B): la transición `disponible → disponible` en el paso de
liberación se trata como no-op idempotente que escribe la traza de auditoría,
no como excepción.

### 8.6. Scratch y promoción

1. `crear-scratch` genera identidad, `_caso.md` mínimo, estructura y log local.
2. El registro lo marca `local_scratch`.
3. Todos los motores migrados usan el mismo `CaseWorkspace`.
4. `promover` crea el canon en Drive y, si corresponde, el expediente CRM.
5. La publicación valida que no exista otro caso con la misma identidad.
6. Solo tras verificar bytes, metadata y auditoría cambia a publicado.
7. Un fallo parcial deja el scratch intacto y un estado reentrante; nunca dos
   expedientes fingidamente canónicos.

La sub-SPEC de promoción fijará el orden de sus efectos y la compensación de
altas parciales.

### 8.7. Cancelación y conflicto

- Cancelar un checkout exige identificar el nonce vigente y confirmar que el
  trabajo local se descarta.
- La cancelación registra `checkout_cancelado`, libera el lock y elimina o
  invalida la entrada privada; no simula un checkin.
- Si se perdió la ruta local, la cancelación sigue siendo una decisión humana
  explícita.
- Resolver un estado `conflicto` requiere una operación propia que preserve
  evidencia de la decisión. No basta con editar a mano el campo
  `estado_repositorio`.

**Cancelación con el titular offline (A-10).** La rev. 1 afirmaba que el trabajo
offline no permite continuar tras una cancelación legítima. Es falso: nada lo
impide, y el único freno es un conflicto en el checkin cuyo baseline ya está
obsoleto. Escenario: el titular pierde red y sigue trabajando (§7.1.5); otro
usuario —o el propio titular desde Cowork, siguiendo la prosa de la skill
`checkout-caso`— cancela el lock; el caso vuelve a `disponible` y terceros
escriben en Drive durante días; al volver, el titular obtiene `LOCK_MISMATCH` y
un merge de tres vías contra un `MANIFEST_CHECKOUT.json` viejo, es decir un
conflicto masivo sin criterio de resolución. Por tanto:

- una cancelación **sin confirmación del titular** deja marca en Drive
  (`checkout_cancelado` con el nonce cancelado y el motivo «unilateral»);
- el checkin posterior detecta esa marca y **no ofrece merge**: ofrece una vía de
  rescate acotada —volcar el delta local a un lote de intake nuevo, con evento
  propio— en lugar de reconciliar contra un baseline caducado;
- el trabajo offline productivo se limita a lo que el rescate puede recuperar sin
  ambigüedad; en particular no se prometen reconciliables las mutaciones de
  ficheros de control (`GRUPOS_MERGE`).

## 9. Scripts, UI, plugins y skills

### 9.1. Regla para código Python

- Los motores internos que transforman un árbol ya resuelto pueden continuar
  recibiendo `Path`.
- Las fachadas públicas mutantes reciben un `CaseWorkspace` o pasan por un
  servicio que lo exige.
- CLI y Streamlit no duplican reglas de resolución.
- Un helper que solo recibe una ruta no se considera barrera de autorización.

### 9.2. Plugins y conectores

Los plugins declaran capacidades de acceso, no una equivalencia ficticia:

- `expedientes-xl` puede trabajar sobre sus raíces permitidas, pero no alcanza
  una ruta local arbitraria;
- un conector local futuro puede acceder al workspace local;
- `email-export`, ejecutado en el PC con OAuth, debe aceptar el destino resuelto
  y depositar allí. **Aceptar el destino no basta (A-3):** `_dir_estado_canal`
  ignora el `dest` recibido y resuelve *siempre*
  `path_for(resolve_ref(case_id))/00_Input` para `_exported_ids.json` y
  `_resolved_links.json`, que además no pasan por el guard ni están en
  `MERGE_EXCLUSIONS`. Con la copia activa en local eso escribe en el canon, deja
  el índice de idempotencia en el lado equivocado (la corrida siguiente
  re-descarga la etiqueta entera) y al checkin aparece como «nuevo en Drive». El
  **estado de canal es parte del workspace**, no del catálogo;
- un plugin que solo pueda escribir en Drive aborta si el caso activo está en
  local.

**El plugin necesita conocer el lock (A-4).** `plugins/expedientes_xl/tiers.py`
clasifica por zona y **no consulta `estado_repositorio` en ningún punto**: su
carve-out `PROTOCOL_EDIT` autoriza **sobrescribir `_caso.md`** bajo `00_Input`, y
Tier 2 (`01_Procesado`, `05_Procedimiento`…) es escritura libre. Es decir, el
runtime que por diseño *no puede ver* la copia local es el que puede borrar el
lock del canon con un `write_text`, sin pasar por una sola línea de Python del
repo. La frontera de entrypoints no alcanza aquí, así que:

- la política de zonas incorpora el estado del lock: leer el `_caso.md` de destino
  y denegar toda escritura salvo protocolo cuando no sea `disponible`;
- `PROTOCOL_EDIT` sobre `_caso.md` queda reservado a una tool de protocolo
  identificada, no al `write_text` genérico;
- esto entra en la Fase 5 **o antes** si el checkout por skill sigue vivo (§9.3);
- el test anti-drift que ya sincroniza `tiers.py` con `core.config` se extiende a
  esta regla.

La selección de backend no se codifica en cada tool. Un adaptador traduce el
`CaseWorkspace` a las operaciones disponibles en ese runtime.

### 9.3. Skills

Las skills son orquestadores, no una segunda implementación del resolver.

- Las skills locales invocan la CLI o el helper canónico.
- Las skills empaquetadas consultan el estado y las capacidades mediante una
  tool compartida.
- Si la copia activa es local pero el runtime no puede verla, la skill aborta y
  dirige al usuario al PC titular.
- Ninguna instrucción en lenguaje natural autoriza saltarse el lock.
- La SSOT permanece en `.claude/skills/`; las copias del plugin se regeneran por
  el build existente.

Cada skill migrada declara en su frontmatter o contrato:

- modos soportados;
- runtime requerido;
- capacidades que solicita;
- comportamiento ante checkout ajeno.

### 9.3-bis. `checkout-caso` / `checkin-caso`: decisión previa a la Fase 2 (B0-3)

La afirmación «las skills ya comparten el cerebro» es falsa para estas dos.
`.claude/skills/checkout-caso/SKILL.md` **ejecuta el protocolo completo en
prosa**: genera nonce, escribe `estado_repositorio: prestado` en el `_caso.md` del
Drive, espera el sync lag, relee, y registra `case_checkout` «vía conector
`expedientes-xl` `append_text`» **incluyendo `ruta_local`** — el campo que el
§6.1 manda retirar. Y no conoce el registro privado del §6.2, que solo escribe la
CLI Python.

Consecuencia si no se decide antes de la Fase 2: todo checkout hecho desde Cowork
nace **sin entrada en el registro**, con lo que el §7.2 paso 7 devuelve *bloqueo*
al propio titular en su propio checkout, y el §15 lo cataloga como «checkout
anterior» que exige `--case-dir` y adopción manual. La vía normal de trabajo de
Cowork se convierte en una fábrica de checkouts inadoptables durante tres fases.

**Se elige la opción (a):** la skill **deja de adquirir el lock**. Pasa a ser un
envoltorio que invoca la CLI canónica cuando es alcanzable y **aborta declarando
`RUNTIME_CANNOT_ACCESS_WORKSPACE`** cuando no lo es (nube pura), dirigiendo al PC
titular. Se descarta la opción (b) —dar a la skill un formato de registro que
pueda escribir— porque duplicaría el escritor del registro en dos runtimes con
semánticas de atomicidad distintas, que es la misma clase de problema que esta
SPEC viene a cerrar. Esta decisión se ejecuta **en la Fase 2, no en la 5**: es la
condición para que la Fase 2 pueda apoyarse en el registro.

## 10. Errores y mensajes

El core devuelve errores estructurados; cada interfaz los presenta sin cambiar
su significado. Como mínimo:

| Código | Significado |
|---|---|
| `CASE_LOCKED` | Prestado por otro titular o máquina |
| `LOCAL_WORKSPACE_MISSING` | El registro apunta a una ruta ausente |
| `LOCK_MISMATCH` | El nonce local no coincide con Drive |
| `CASE_CONFLICT` | El repositorio está en conflicto |
| `AMBIGUOUS_CASE` | Hay más de una resolución posible |
| `RUNTIME_CANNOT_ACCESS_WORKSPACE` | El entorno no puede alcanzar la copia activa |
| `CAPABILITY_DENIED` | El modo no permite la operación |
| `CANONICAL_MUTATION_DEFERRED` | La operación debe esperar a checkin/promoción |
| `LOCK_NOT_MINE` | Se intentó mutar un lock cuyo nonce vigente es de otro (§8.2) |
| `CHECKOUT_CANCELLED_ELSEWHERE` | El lock se canceló mientras el titular trabajaba offline (§8.7) |
| `WORKSPACE_UNDER_CATALOG_ROOT` | El destino local cae bajo `CASOS_ROOT` (§5.1) |
| `AUDIT_BASELINE_MISSING` | Falta el baseline del log para reconciliar (§6.3) |

Los mensajes deben indicar que no se produjo ningún efecto cuando así sea. No
pueden sugerir que el usuario reintente contra Drive como atajo.

## 11. Brechas concretas respecto de la arquitectura vigente

La primera revisión de código identifica estos cambios de contrato; ninguna
sub-SPEC puede ignorarlos:

1. `core.repository_checkout.decidir_escritura` desvía hoy las escrituras de un
   caso `prestado` o `conflicto` a `_pendiente_checkin/`. La política dual lo
   cambia a **denegar** las nuevas mutaciones ordinarias. La integración legacy
   permanece solo para contenido ya existente.
2. `MERGE_EXCLUSIONS` impide copiar `_caso.md` y `_intake_log.jsonl` al local.
   La Fase 2 debe materializarlos como proyecciones protocolarias fuera del
   merge genérico.
3. `case_checkout` publica hoy `ruta_local` en el log de Drive. El nuevo contrato
   la mantiene exclusivamente en el registro privado.
4. `core.intake_log.append_event` resuelve la ruta mediante `caso_path` y
   `CASOS_ROOT`. Debe poder escribir en el workspace ya resuelto sin volver a
   localizar el caso.
5. `scripts.sala_maquina` resuelve directamente con `caso_path`; no conoce el
   lock ni el checkout local.
6. `case_locator.resolve_ref` depende de que exista `_caso.md` en la raíz que
   examina. La proyección local y el registro deben cerrar ese hueco sin
   fabricar una segunda identidad canónica.
7. CLI y skill de checkout/checkin comparten el cerebro, pero mantienen
   orquestación y prosa que pueden divergir. La migración debe conservar una
   sola política ejecutable.

Brechas **añadidas en la rev. 2**, todas verificadas contra el código en el
commit `8d9c96c`. Ninguna es teórica y ninguna estaba en la lista de la rev. 1:

8. `intake_log.append_event` no solo resuelve por `caso_path`: hace
   `path.parent.mkdir(parents=True, exist_ok=True)`, de modo que **crea**
   `CASOS_ROOT/<case_id>/00_Input/` cuando el caso no existe ahí. Combinado con
   el fallback de `path_for` (brecha 12), cualquier evento sobre una identidad
   desconocida fabrica un expediente fantasma en la unidad compartida.
9. `email_export._dir_estado_canal` → `_save_export_index` /
   `_save_resolved_links` escriben el estado de canal en
   `path_for(resolve_ref(case_id))/00_Input` **ignorando el destino recibido y
   sin pasar por el guard**. Los `.eml` sí se desvían (`reservar_lote` →
   `dir_intake`); estos dos JSON, no.
10. `catalogo_documental.save_catalog` hace `mkdir` + `write_text` sobre
    `caso_path` sin guard. Misma familia que la 9.
11. `scripts.sala_maquina plan`, documentado como «no escribe nada», escribe el
    `_segmentacion.md` de cada bundle multi-documento detectado. Necesita
    `write_case`.
12. `case_locator.path_for` **devuelve la ruta flat inexistente** cuando no
    encuentra el caso, y `resolve_ref` devuelve la referencia tal cual. Es el
    fallback silencioso del invariante 3, con precedente real (W-02ZIIF).
13. `INTAKE_EVENTS` es un `frozenset` cerrado y `append_event` **lanza
    `ValueError`** ante un evento desconocido. La Fase 2 necesita eventos nuevos
    (scratch, promoción, adopción, conflicto resuelto, cancelación unilateral) y
    debe retirar la emisión de `pendiente_checkin` sin romper la lectura
    histórica.
14. No existe doble contractual de Drive/rclone. `tests/test_repository_cli.py`
    tiene 27 tests **de los helpers puros** del frontal (constructores de comando,
    semáforo, inventario, plan de bandeja, DELTA) y **ninguno de
    `cmd_checkout`/`cmd_checkin`**. **Actualización del 2026-07-29:** los PRs #156
    y #160 dejaron **16 tests de orquestación** de los dos `cmd_*`
    (`tests/test_repository_cli_guard_pull.py`) con un doble de rclone embrionario,
    así que la afirmación original —«la orquestación no tiene test»— ya es falsa.
    Lo que sigue faltando es el **banco completo**: doble fijado a una versión de
    rclone con fixtures grabadas, caracterización de los caminos felices y de los
    fallos, y los defectos reproducidos. El encabezado de `repository_cli` está al
    día en este punto.
15. `case_manager.guard_escritura` lee el estado del `_caso.md` **local**
    (`MEJORAS #96`). Es dependencia dura de la proyección del §6.3.

## 12. Migración por fases

Esta SPEC fija contratos. Cada fase requiere una sub-SPEC, plan, revisión
adversarial y PR propios.

### Fase 0 — banco de pruebas del frontal (nueva en la rev. 2, A-9)

Sin esto, los criterios de salida de las Fases 2 y 3 son indemostrables: la
**orquestación** del frontal que mueve los bytes no tenía ni un test (los 27 de
`tests/test_repository_cli.py` cubren solo helpers puros) y la matriz del §14.1
exige un Drive simulado que no existe.

- barrera de test que impida ejecutar rclone real o alcanzar el Drive real
  (`tmp_casos_root` **no** es `autouse` y los defaults del frontal son el remote y
  el `team_drive` reales). **La barrera debe seguir validando con `run_rclone`
  doblado**: es la única superficie de `subprocess` del módulo, así que un doble la
  desactiva por completo, y los tests de caracterización doblan precisamente esa
  función. El validador de operandos es por tanto compartido entre la barrera y el
  doble (3ª revisión adversarial del plan, su B0-1);
- puerto inyectable en `scripts/repository_cli.py`, sin cambio de comportamiento,
  para las **cinco** fuentes de no-determinismo —rclone, reloj, hostname,
  directorio de trabajo y espera— más nonce, usuario y binario;
- doble en memoria fijado a una **versión concreta de rclone**, con fixtures
  grabadas: Google-native sin MD5, `moveto` que falla, `lsjson` malformado,
  `--files-from` con filtros, `--backup-dir`, y un **hook de mutación por
  operación** que permita interleaving determinista sin hilos;
- tests que fijen el comportamiento **actual** del checkout/checkin como red de
  seguridad antes de tocarlo.

**Criterio de salida (corregido en la errata del 2026-07-29):**

1. la **brecha 14** del §11 queda cerrada: existe doble contractual y hay
   caracterización de `cmd_checkout`/`cmd_checkin`;
2. los **siete** defectos del frontal están reproducidos en
   `xfail(strict=True, raises=AssertionError)`. **Se encontraron ocho**; el octavo
   —`_integrar_bandeja` devolvía `(0,0)` con un `lsjson` ilegible y el checkin
   liberaba el lock creyendo la bandeja vacía— lo cerró el **PR #160**, así que
   pasa de `xfail` a caracterización verde;
3. una matriz de fallos cubre los retornos que sigan sin examinarse. Tras #160 son
   **dos**: el `lsjson` de CP1 (que juzga por contenido, no por retorno) y el
   `rmdirs` de la bandeja;
4. el arnés de la matriz del §14.1 queda **preparado para consumirse en la Fase
   1**, no ejecutado íntegramente aquí;
5. ningún test puede tocar rclone real, el Drive real ni `CASOS_ROOT`.

**Adelantado y ya mergeado, con lo que la Fase 0 arranca desde más arriba:** el
guard de **lectura** del protocolo (#156) y el de **escritura** (#160), que entre
los dos cerraron ocho retornos ignorados y dos rutas de destrucción de datos. Los
dos salieron de adjudicar revisiones adversariales de este plan, no de revisar
código: es el argumento más fuerte a favor de haber revisado el plan antes de
ejecutarlo.

> **Errata.** La rev. 2 de esta SPEC exigía aquí que «las brechas 8-15 del §11
> tengan un test». Es incorrecto y lo señaló la revisión adversarial del plan
> (B0-3): las brechas **8-13 y 15 pertenecen a las Fases 1-3** —`intake_log`,
> estado de canal de correo, catálogo, `sala_maquina plan`, fallback de
> `path_for`, `INTAKE_EVENTS` y el guard que lee el lock local— y ninguna es
> alcanzable desde el frontal. Solo la **14** es de esta fase. Mantener el texto
> anterior habría permitido declarar cumplido un criterio objetivamente falso.

Plan ejecutable: `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-banco-pruebas.md`
(**rev. 4, EJECUTABLE**). Pasó por **tres** revisiones adversariales: las rev. 1 y 2
recibieron NO EJECUTABLE (3 B0 cada una) y la rev. 3 recibió REQUIERE REVISIÓN (3 B0 + 2
A), corregida en la rev. 4 sin tocar arquitectura ni el reparto en dos PRs. **No hay más
gate de revisión**: la 3ª pasada rindió cero hallazgos de código, frente a los dos PRs de
producción que rindieron las dos primeras.

### Fase 1 — núcleo de workspace

- `CaseRef` (con unicidad de W-code y `AMBIGUOUS_CASE` desde el catálogo), modos,
  capacidades y errores;
- registro local atómico;
- resolver por identidad y `--case-dir`;
- adaptador inicial al `case_locator` actual, **con modo estricto**: `caso_path`
  deja de devolver rutas inexistentes y ningún escritor hace `mkdir` de la raíz;
- **`core.intake_log` migrado en esta fase** (B0-1): `append_event` recibe el
  workspace o el log ya resuelto; `log_path(case_id)` se retira. Sin esto,
  publicar `--case-dir` parte la custodia en dos y fabrica carpetas fantasma;
- `--case-dir` en el primer consumidor real (`scripts/sala_maquina`), porque es
  el único que hace utilizable el modo `local_scratch` (A-7);
- tests contractuales del resolver.

**Criterio de salida:** una matriz pura demuestra una única resolución para
Drive disponible, checkout propio, checkout ajeno, scratch, conflicto, ruta
ausente y nonce divergente. **Y**: ninguna ruta del código crea un directorio
bajo `CASOS_ROOT` para una identidad que el catálogo no conoce; con `--case-dir`,
el evento de auditoría cae en el mismo árbol que los bytes.

### Fase 2 — checkout, scratch y checkin

- **arreglo previo de `MEJORAS #96`**: el guard distingue *dónde* escribe antes de
  que se materialice ningún `_caso.md` local (§6.3);
- **conmutación atómica del guard a denegar** para todos los llamadores (§3.2);
- baseline de auditoría (hash + nº de líneas del log) como artefacto de
  protocolo, y append real en lugar de reescritura del log canónico;
- tabla campo → propietario → merge de `_caso.md` (§6.3);
- materialización de metadata/log local;
- compare-and-swap en todas las mutaciones del lock + re-verificación del nonce
  tras materializar (§8.2);
- reordenación del checkin: integrar bandeja → verificar todo → evento
  idempotente → liberar (§8.5);
- `checkout-caso`/`checkin-caso` dejan de adquirir el lock (§9.3-bis);
- eventos nuevos en `INTAKE_EVENTS` y retirada de la emisión de
  `pendiente_checkin`;
- alta y retirada del registro; resolución offline y rescate tras cancelación
  unilateral (§8.7);
- promoción de scratch.

**Criterio de salida:** ningún camino libera el lock o pierde el local después
de una verificación fallida; **ningún camino permite dos titulares simultáneos**;
un checkin reentrante no duplica eventos; y no queda ningún llamador que desvíe
escrituras a la bandeja.

### Fase 3 — primera vertical operativa

- `scripts/sala_maquina` (incluido `plan`, que escribe);
- atomización de email y exportación Gmail, **con el estado de canal dentro del
  workspace** (brecha 9);
- `catalogo_documental` (brecha 10), que la vertical arrastra;
- `organizar-sala-maquina`.

Streamlit **no** entra aquí: pasa entera a la Fase 4, para no partir la UI entre
dos fases (la rev. 1 la listaba en ambas).

**Criterio de salida:** la misma fixture produce resultados funcionalmente
equivalentes en Drive simulado, scratch local y checkout local; un checkout
ajeno no modifica ningún árbol **en los cuatro planos del §3.2-bis**.

### Fase 4 — resto de scripts y UI

- inventario de entrypoints mutantes;
- **Streamlit completa**, con la regla de que el `CaseWorkspace` no se cachea en
  `st.session_state` y se revalida por request (mismo patrón que `set_actor`);
- migración por familias;
- retirada de resoluciones directas peligrosas;
- telemetría local de incompatibilidades sin PII.

**Dimensión real de esta fase, medida y no estimada.** El recuento de
`caso_path` / `settings.casos_root` / `resolve_ref` / `path_for` da **432
apariciones en 80 ficheros**, y la resolución **no está en las CLIs**: está dentro
de servicios de `core/` que reciben `case_id` — `case_manager` (23),
`intake_manual` (10), `anon/api` (9), `sala_lectura` (7), `email_export` (6),
`viability` (4), `crm_atlas` (3), `intake_drive` (3), `demanda_generator` (3),
`catalogo_documental` (2), `intake_log` (2)…, más `streamlit_app.py` (9). Lo que
esta migración reescribe es **la capa de servicios de core**, no «los
entrypoints». Decirlo así evita que la Fase 4 se subestime.

### Fase 5 — plugins y skills

- contrato de capacidades de runtime;
- tool común de resolución/diagnóstico;
- actualización de las skills por la SSOT;
- rebuild y tests anti-drift del plugin;
- matriz Cowork-PC, Claude Code, CLI y conectores.

### Fase 6 — enforcement

- guardas que impidan nuevos entrypoints mutantes sin workspace;
- deprecación de overrides ambiguos;
- retirada, mediante decisión separada, del andamio legacy ya sin consumidores;
- documentación operativa y recuperación.

Hasta completar una fase, los componentes no migrados se etiquetan como
`drive_only`, `local_only` o `legacy_unresolved`. No se declara paridad global
antes de completar el inventario.

## 13. Debate arquitectónico: contexto central frente a almacenamiento virtual

Esta sección es parte normativa del documento y debe revisarse
adversarialmente, no tratarse como mero historial.

### 13.1. Opción elegida: `CaseWorkspace`

Ventajas:

- centraliza la decisión peligrosa sin reescribir motores estables;
- permite implantación vertical y progresiva;
- conserva el rendimiento del filesystem local;
- reduce el riesgo de regresión en OCR, PDF, email y herramientas externas;
- hace explícitas las capacidades y el runtime;
- encaja con la arquitectura UI → Core → Datos.

Riesgos:

- un call-site puede intentar seguir usando una ruta directa;
- la autorización queda en la frontera, no en cada `open`;
- durante la migración coexistirán componentes duales y legacy;
- `working_root: Path` no resuelve por sí mismo un futuro backend remoto.

Mitigaciones:

- inventario de entrypoints mutantes;
- death tests de «cero escritura»;
- guardas y deprecaciones en fases;
- `CaseWorkspace` inmutable por operación;
- separación entre resolver, registro y materialización.

### 13.2. Opción descartada ahora: almacenamiento virtual

La alternativa era obligar a que toda lectura y escritura pasase por un backend
intercambiable: filesystem, Drive montado, API de Drive o rclone.

Ventajas teóricas:

- política uniforme en cada operación;
- mejor instrumentación central;
- posibilidad de backends remotos sin montaje;
- mayor cercanía a un SaaS multi-tenant.

Costes y riesgos actuales:

- refactoring transversal de todos los usos de `Path`, `open`, `rglob`,
  `shutil`, hashes y temporales;
- librerías de OCR/PDF y binarios externos exigen rutas materializadas;
- las diferencias de consistencia, renombrado y atomicidad entre NTFS, Drive
  montado, Drive API y rclone no desaparecen por crear una interfaz;
- la fase híbrida tendría dos caminos de I/O y sería especialmente frágil;
- mayor inversión antes de obtener seguridad operativa;
- riesgo de convertir la arquitectura de almacenamiento en el centro de
  motores que hoy son lógica pura.

### 13.3. Puerta limpia hacia la opción 3

La opción 2 no debe bloquear una evolución posterior. La frontera preparada es:

```text
CaseWorkspaceResolver
├── CaseCatalog          # localiza canon y estado compartido
├── WorkspaceRegistry    # resuelve rutas privadas de esta máquina
└── WorkspaceMaterializer
    └── working_root     # Path accesible para los motores actuales
```

En la primera versión solo se implementan las variantes de filesystem y los
adaptadores imprescindibles. No se crea una API virtual de ficheros anticipada.

Si en el futuro un backend remoto no puede ofrecer una ruta, la evolución
natural es que `WorkspaceMaterializer` cree una vista local controlada o que
una sub-SPEC introduzca un `StorageHandle`. La selección del caso, las
capacidades, el lock y los errores permanecerían estables.

La puerta es «limpia» porque concentra el cambio futuro en la materialización y
en los motores que realmente necesiten I/O remoto; no promete que la migración
sea gratuita.

### 13.4. Condiciones que reabrirían la opción 3

Solo se reevalúa una abstracción completa si aparece al menos uno de estos
disparadores:

- FeesDefender pasa a SaaS sin filesystem montado;
- se necesitan dos o más proveedores remotos como almacenamiento operativo;
- la mayoría de los motores dejan de requerir rutas locales;
- los adaptadores por runtime empiezan a duplicar lógica material;
- una auditoría demuestra que la frontera de entrypoint no puede impedir
  escrituras fuera de política.

**Nota de la rev. 2:** el último disparador **ya se ha cumplido parcialmente**
(§9.2, A-4): `expedientes-xl` puede sobrescribir el `_caso.md` del canon sin pasar
por Python. No obliga a reabrir la opción 3 —el plugin es un punto único,
auditable y con test anti-drift— pero sí obliga a un cambio de contrato, y deja de
ser cierto que la frontera de entrypoints Python cubra *todos* los escritores.
Si en el futuro hubiera que replicar la política del lock en un tercer runtime,
ese sería el momento de reabrir el debate: la política dejaría de tener un hogar.

## 14. Estrategia de pruebas

No se prueba «local» sustituyendo una cadena de ruta. Se prueba el contrato de
estado y efectos.

### 14.1. Matriz mínima por entrypoint mutante

| Escenario | Resultado esperado |
|---|---|
| Drive disponible | Escribe solo en Drive |
| Checkout propio | Escribe solo en local |
| Checkout ajeno | Cero bytes nuevos o modificados |
| Scratch local | Escribe solo en scratch |
| Conflicto | Cero mutación |
| Registro local ausente | Error, sin fallback |
| Nonce divergente | Error, local conservado |
| Runtime sin acceso | Error, Drive intacto |
| Servicio externo falla | Reintento seguro o aborto idempotente |

### 14.2. Tipos de prueba

- unitarias del resolver, estados, capacidades y mensajes;
- contractuales reutilizables por CLI, UI, plugins y skills;
- integración con árboles temporales y dobles de Drive/CRM/Gmail. **El doble de
  Drive/rclone no existe y es la Fase 0**: `repository_cli` llama a `run_rclone`
  directamente, sin puerto inyectable, y los 27 tests de
  `tests/test_repository_cli.py` cubren solo sus helpers puros. Mientras no
  exista, las filas «Drive disponible» y «Checkout ajeno» del §14.1 no son
  ejecutables para el ciclo checkout/checkin;
- death tests que comparen inventario y hashes antes/después de un bloqueo, **en
  los cuatro planos del §3.2-bis** (árbol, canon incluidas carpetas, servicios
  externos, estado local);
- pruebas de reentrada en checkout, checkin y promoción, incluida la de que un
  reintento **no** duplica `case_checkin`;
- una prueba de carrera de lock: dos adquisiciones que leen `disponible` antes de
  que ninguna escriba deben producir exactamente un titular;
- pruebas de compatibilidad con casos sin campos nuevos;
- tests anti-drift de skills y plugin.

No se requieren expedientes reales ni una unidad `G:` para la suite. Y ninguna
verificación de integridad se hace leyendo el montaje: siempre por API
(`MEJORAS #94`).

### 14.3. Afirmaciones que no se permiten

- «Byte-idéntico» sin acotar campos de procedencia y auditoría.
- «Dual» porque una función acepta `Path`.
- «Sin efectos» sin comparar árboles, logs y llamadas externas.
- «Mismo caso» basándose solo en el nombre de carpeta.
- «Lock válido» basándose solo en usuario o máquina sin nonce.

## 15. Compatibilidad y transición

- Un `_caso.md` sin `estado_repositorio` sigue leyéndose como `disponible`.
- Los checkouts anteriores sin registro no se adoptan automáticamente. Requieren
  `--case-dir` y una operación explícita de adopción/verificación.
- `CASOS_ROOT` no se elimina en las primeras fases.
- Los motores puros no cambian de firma salvo necesidad demostrada.
- Las skills no migradas conservan su comportamiento declarado, pero deben
  bloquearse ante un checkout que no puedan resolver con seguridad.
- Los contenidos legacy de `_pendiente_checkin/` se integran o recuperan antes
  de retirar el mecanismo; no se borran por migración.

## 16. Seguridad y custodia

- Ninguna ruta local con posibles datos personales se publica en `_caso.md`,
  commits o mensajes a terceros.
- El registro local queda fuera de Git y Drive.
- Los casos reales continúan fuera del repositorio.
- `90_Notas personales/` conserva su tratamiento reservado y queda fuera del
  checkout conforme al contrato vigente.
- La promoción es el punto en que un scratch adquiere custodia canónica.
- Un fallo de checkin no convierte el local en prescindible.
- Los logs de diagnóstico usan W-code y códigos de error, no nombres, emails o
  direcciones.
- **Copia parcial huérfana (M-1).** Un checkout que falla a mitad de la copia
  deja hoy un árbol con documentos reales y **sin `_caso.md`** (está en
  `MERGE_EXCLUSIONS`), es decir PII en el Desktop que ni `--case-dir` ni el
  registro pueden identificar. La Fase 2 la marca (fichero de cuarentena con
  `CaseRef`, nonce y timestamp) y la declara al usuario para que decida; nunca se
  borra sola ni se deja sin rastro.
- El identificador de máquina que viaja al canon es derivado, no el hostname
  legible (§6.2).

## 17. Fuera de alcance

- edición concurrente o multiwriter;
- CRDT, sincronización continua o resolución automática de conflictos;
- una bandeja de aportaciones durante checkout;
- disponibilidad offline de Gmail, CRM o Drive;
- abstracción virtual completa de filesystem;
- acceso de Cowork en la nube al Desktop;
- sustitución de checkout/checkin por sync bidireccional;
- publicación atómica general de todos los pipelines;
- cambios funcionales a OCR, atomización, anonimización o razonamiento
  jurídico;
- migración de todos los componentes en un solo PR.

## 18. Criterios de aceptación de la arquitectura marco

La implantación completa podrá declararse «FeesDefender dual» solo cuando:

1. exista un inventario cerrado de entrypoints mutantes;
2. todos ellos resuelvan o deleguen en el `CaseWorkspace` común;
3. los tres modos operativos superen la matriz contractual;
4. un checkout ajeno produzca cero mutaciones de contenido;
5. no exista fallback silencioso a Drive;
6. los logs locales se reconcilien sin pérdida;
7. plugins y skills declaren sus capacidades y limitaciones de runtime;
8. la documentación operativa explique checkout, scratch, promoción,
   recuperación y conflicto;
9. una revisión adversarial independiente no encuentre rutas de escritura que
   eludan la política.

## 19. Mandato para la revisión adversarial — **CONSUMIDO**

> **Estado:** ejecutado el 2026-07-29 por Claude Code contra el código del commit
> `8d9c96c`. Veredicto **REQUIERE REVISIÓN**. Informe completo:
> `2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`.
> Adjudicación punto por punto: **§20**. Este mandato se conserva como registro
> de lo que se pidió refutar; no vuelve a ejecutarse tal cual.

Claude Code debe revisar tanto la SPEC como el debate del §13. En particular,
debe intentar refutar:

1. que controlar los entrypoints basta para impedir escrituras directas;
2. que el registro local y el nonce identifican inequívocamente la copia
   operativa;
3. que `_caso.md` y `_intake_log.jsonl` pueden materializarse y reconciliarse
   sin abrir una segunda fuente de verdad;
4. que el trabajo offline no permite continuar tras una cancelación legítima;
5. que «cero bytes» es comprobable también en plugins y servicios externos;
6. que `_pendiente_checkin/` puede quedar solo como compatibilidad sin mantener
   dos políticas activas;
7. que las skills empaquetadas pueden compartir el resolver sin duplicarlo;
8. que la frontera `WorkspaceMaterializer` es una puerta real hacia la opción 3
   y no una etiqueta sin capacidad de evolución;
9. que la inversión de la opción 2 no se aproxima a la opción 3 al completar la
   migración;
10. que los modos y capacidades cubren todos los estados actuales de
    checkout/checkin y promoción.

Un hallazgo contra cualquiera de estos puntos debe corregir el contrato antes
de escribir el plan de la Fase 1. No se responde añadiendo excepciones locales
en scripts o skills.

## 20. Adjudicación de la revisión adversarial (rev. 2)

Informe: `2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`.
Veredicto **REQUIERE REVISIÓN** — la arquitectura y la elección de la opción 2
sobreviven; lo que no estaba listo era el contrato. **Todos los B0 y los A se
aceptan.** Ninguno se responde con una excepción local.

### 20.1. Los diez puntos del §19, resueltos

| # del §19 | Resultado | Dónde se corrige |
|---|---|---|
| 1. Los entrypoints bastan | **REFUTADO** — `expedientes-xl` sobrescribe `_caso.md` del canon sin pasar por Python | §9.2, §13.4 |
| 2. Registro + nonce identifican la copia | **REFUTADO** — W-code no único, `resolve_ref` elige por orden de escaneo | §5.1, §7.2 |
| 3. Proyectar y reconciliar sin 2ª fuente de verdad | **REFUTADO en la mecánica** — no había baseline del log y la proyección dispara `MEJORAS #96` | §6.3 |
| 4. Offline no continúa tras cancelación legítima | **REFUTADO** — nada lo impide; el conflicto resultante no tiene baseline útil | §8.7 |
| 5. «Cero bytes» comprobable | **REFUTADO** — indefinido, y ya incumplido en 4 sitios | §3.2-bis, §11.8-11 |
| 6. La bandeja como mera compatibilidad | **REFUTADO** — `decidir_escritura` es pura del estado: no admite dos políticas | §3.2 |
| 7. Skills comparten resolver sin duplicarlo | **REFUTADO** — `checkout-caso` reimplementa el protocolo en prosa | §9.3-bis |
| 8. `WorkspaceMaterializer` es puerta real | **SOBREVIVE** para filesystem y vista local; no para un backend sin ruta, que ya estaba admitido | §13.3 sin cambios |
| 9. La opción 2 no se acerca a la 3 | **SOBREVIVE, con la retórica corregida** — se reescribe la capa de servicios de core, no «los entrypoints» | §12 Fase 4 |
| 10. Modos y capacidades cubren los estados | **PARCIAL** — faltaban `LOCK_NOT_MINE`, cancelación unilateral, destino bajo `CASOS_ROOT` y baseline de auditoría | §10 |

### 20.2. Bloqueantes (B0) y su remedio

| B0 | Qué era | Remedio en esta rev. |
|---|---|---|
| **B0-1** | `--case-dir` en Fase 1 sin migrar `intake_log`: los bytes al local y la custodia al canon, más carpeta fantasma por el `mkdir` | `core.intake_log` se migra **en la Fase 1**; `log_path(case_id)` se retira (§12) |
| **B0-2** | «El prefijo coincide con el baseline protocolario»: no había baseline (el manifest excluye el log), el canon se reescribe con `errors="replace"` y `read_events` descarta líneas corruptas | Artefacto de baseline propio, comparación por identidad de evento, append real, cola no parseable bloqueante (§6.3) |
| **B0-3** | Las skills de checkout/checkin reimplementan el protocolo y no pueden escribir el registro → checkouts inadoptables durante 3 fases | La skill **deja de adquirir el lock** y aborta si la CLI no es alcanzable; se ejecuta en la Fase 2 (§9.3-bis) |
| **B0-4** | «Denegar lo nuevo, desviar lo legacy» no es implementable en una función pura del estado → dos políticas vivas en las Fases 3-6 | Conmutación **atómica** a denegar en la Fase 2 + criterio de retirada por inventario (§3.2) |

### 20.3. Hallazgos A

`A-1` carrera de lock y pushes ciegos → §8.2 (compare-and-swap + re-verificación
tras materializar). `A-2` orden del checkin y evento duplicado → §8.5. `A-3`
«cero escritura» indefinida y ya incumplida → §3.2-bis y §11.8-11. `A-4` el
plugin puede borrar el lock → §9.2 y §13.4. `A-5` fallback creador de `path_for`
→ §7.3 y §11.12. `A-6` `INTAKE_EVENTS` cerrado → §11.13 y Fase 2. `A-7`
`--case-dir` no existe y el scratch se queda sin vía → §7.3 y Fase 1. `A-8`
identidad no única → §5.1. `A-9` no hay doble de Drive → **Fase 0** nueva.
`A-10` cancelación con el titular offline → §8.7.

### 20.4. Hallazgos M — no entran en el contrato, van al backlog

`M-1` (copia parcial huérfana) sí se recoge en §16 porque es custodia. `M-2`
(hostname en el canon) se decide en §6.2. Los tres restantes se anotan en
`docs/MEJORAS_FUTURAS.md` para no perderlos: residuos `_reingesta_*` de la
bandeja sin plan ni verificación, `errors="replace"` en la lectura del log
canónico (que corrompe evidencia con o sin esta migración), y la regla de que el
`CaseWorkspace` no se cachee en `st.session_state`.

### 20.5. Lo que sobrevivió intacto al ataque

- **La elección de la opción 2**, y el §13.2 como descripción correcta del coste
  de la alternativa.
- **El invariante 6** (motores puros conservados): verificado — OCR, split y
  atomización ya reciben `Path`/`case_dir` resueltos y no localizan nada.
- **El invariante 7** (protocolo separado de contenido): ya implementado, con los
  artefactos del protocolo escritos en directorio temporal para no contaminar el
  inventario.
- **El §14.3** (afirmaciones prohibidas): aplicado al propio código es lo que
  produjo la mitad de los hallazgos.
- **La decisión de no construir bandeja de aportaciones** y de que solo el titular
  incorpore documentos: no se encontró forma de impugnarla.
