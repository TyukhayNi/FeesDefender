# FeesDefender dual: expediente activo local/Drive — diseño marco

**Fecha:** 2026-07-29.
**Estado:** arquitectura aprobada en brainstorming; pendiente de revisión
adversarial y de descomposición en sub-SPECs ejecutables.
**Naturaleza:** SPEC marco. No es un plan de implementación ni autoriza una
migración monolítica.
**Antecedentes directos:**

- `2026-07-14-expediente-scratch-design.md`;
- biblioteca de checkout/checkin (`core.repository_checkout`);
- `2026-07-28-email-atomize-enumeracion-recursiva-design.md` (en la rama
  `claude/98-enumeracion-recursiva` al redactar esta SPEC);
- `docs/ARQUITECTURA.md` y `docs/ARQUITECTURA_RELACIONES.md`.

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

La comprobación del lock ocurre **antes** de descargar, copiar, transformar o
crear bytes.

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

El checkout materializa también `00_Input/_intake_log.jsonl` después de
registrar `case_checkout`. El trabajo local añade eventos a esa copia. El
checkin solo integra el sufijo local tras verificar que el prefijo coincide con
el baseline protocolario. Después registra `case_checkin` en el canon. Una
divergencia no explicada bloquea el cierre y conserva la copia local.

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
  compatibilidad; deja de ser un selector implícito de la copia operativa.
- `--casos-root` puede mantenerse para entornos de prueba o catálogos
  alternativos, pero no sustituye la validación del workspace.
- Ningún entrypoint nuevo debe llamar directamente a `caso_path` y asumir que
  el resultado es escribible.

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
2. Se materializan contenido y baseline, excluyendo el protocolo del merge
   genérico.
3. Se registra `case_checkout` en Drive sin ruta local.
4. Se materializan la proyección de metadata y el log ya actualizado.
5. Se escribe el registro local de forma atómica.
6. Desde ese momento Drive no admite nuevas mutaciones de contenido.
7. Los comandos por identidad de la misma máquina resuelven al local.
8. Los comandos de otras máquinas abortan e indican titular y timestamp.

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
5. Verifica el resultado por inventario/hash.
6. Registra `case_checkin`.
7. Libera el lock únicamente tras verificación completa.
8. Retira o invalida el registro local según la política de cortesía vigente.

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
  y depositar allí;
- un plugin que solo pueda escribir en Drive aborta si el caso activo está en
  local.

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

## 12. Migración por fases

Esta SPEC fija contratos. Cada fase requiere una sub-SPEC, plan, revisión
adversarial y PR propios.

### Fase 1 — núcleo de workspace

- `CaseRef`, modos, capacidades y errores;
- registro local atómico;
- resolver por identidad y `--case-dir`;
- adaptador inicial al `case_locator` actual;
- tests contractuales del resolver.

**Criterio de salida:** una matriz pura demuestra una única resolución para
Drive disponible, checkout propio, checkout ajeno, scratch, conflicto, ruta
ausente y nonce divergente.

### Fase 2 — checkout, scratch y checkin

- materialización de metadata/log local;
- alta y retirada del registro;
- resolución offline;
- reconciliación de metadata y auditoría;
- promoción de scratch;
- política de compatibilidad de `_pendiente_checkin/`.

**Criterio de salida:** ningún camino libera el lock o pierde el local después
de una verificación fallida.

### Fase 3 — primera vertical operativa

- `scripts/sala_maquina`;
- atomización de email y exportación Gmail;
- `organizar-sala-maquina`;
- entradas equivalentes de Streamlit.

**Criterio de salida:** la misma fixture produce resultados funcionalmente
equivalentes en Drive simulado, scratch local y checkout local; un checkout
ajeno no modifica ningún árbol.

### Fase 4 — resto de scripts y UI

- inventario de entrypoints mutantes;
- migración por familias;
- retirada de resoluciones directas peligrosas;
- telemetría local de incompatibilidades sin PII.

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
- integración con árboles temporales y dobles de Drive/CRM/Gmail;
- death tests que comparen inventario y hashes antes/después de un bloqueo;
- pruebas de reentrada en checkout, checkin y promoción;
- pruebas de compatibilidad con casos sin campos nuevos;
- tests anti-drift de skills y plugin.

No se requieren expedientes reales ni una unidad `G:` para la suite.

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

## 19. Mandato para la revisión adversarial

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
