# Robustez y velocidad de `organizar-sala-lectura` — backlog priorizado

> **Origen:** auditoría con Fable 5 (Workflow, 3 fases: auditoría de errores → revisión
> holística de la skill v1.10 → síntesis) sobre los errores reales de las dos pasadas de
> `organizar-sala-lectura` en el caso W-02VUDR (montaje v1.8 original + re-corrida v1.9 de
> comparación A/B), más una lectura fresca de todo `SKILL.md` actual buscando huecos
> adicionales. 2026-07-21.
>
> **Este documento NO es un plan TDD todavía** (no tiene el formato de
> `superpowers:writing-plans` con Tareas/Ficheros/Interfaces/Pasos numerados). Es el
> backlog priorizado que la sesión de construcción dedicada debe convertir en Tasks
> concretas, empezando por los ítems de prioridad alta. Ver
> `docs/superpowers/plans/2026-07-21-preclasificacion-sala-lectura.md` como referencia de
> formato (es el plan hermano que ya se construyó, Tasks 1-5, mergeado PR #112/#113).

## Ya cerrado — no forma parte de este backlog

Durante la misma sesión de auditoría, 4 fixes puntuales + 1 incidente de datos ya se
corrigieron y mergearon (PR #114, `main` en `117b7c1`):

1. `verificar_sala.verificar()` reconoce `parent_id` como nombre de carpeta de bundle
   (no solo match exacto contra `nombre_canonico`/sha256) — 21 falsos positivos.
2. `copiar_manifiesto_rclone._rc_activo()` usa POST, no GET, contra la RC API de rclone
   (era GET, la API es POST-only, `_rc_activo()` siempre devolvía `False`).
3. `verificar()` detecta automáticamente fecha `0000-00-00` con texto ya extraído
   disponible en sala de máquina (`cobertura_filas` opcional).
4. Hueco cerrado en el propio fix 3: el cruce clavaba solo por `sha256`, pero los PDFs
   escaneados multi-documento (spliteados) llevan el hash de origen en `parent_sha256`.
5. **Incidente de datos, no de código:** un fichero de OTRO caso (W-02X270) se había
   copiado por error a la sala real de W-02VUDR — borrado y documentado en su
   `_MANIFIESTO.md` § Excluido de la sala, con evento en `_intake_log.jsonl`.

Los ítems de este backlog atacan los **patrones** detrás de los bugs de arriba, no los
bugs puntuales en sí — por eso siguen pendientes pese a que el PR ya está mergeado.

## Diagnóstico de fondo (4 patrones, no bugs sueltos)

1. **El workflow delega en el juicio de un agente cosas que caben en un chequeo
   determinista de 1 segundo**: frescura del checkout git, config de rclone, señales
   del gate condicional (incluido el W-code ajeno que ya falló en producción).
2. **Los fallos conocidos y recurrentes (`ERROR_FILE_NOT_HYDRATED`) no tienen ruta de
   resolución automática cableada** — dependen de que alguien recuerde el bypass.
3. **El proceso permite que un agente "arregle" un verify fallido editando datos
   generados de producción** en vez de sospechar del propio check (el `_MANIFIESTO.md`
   lleva cabecera "NO EDITAR A MANO" y aun así se editó — 21 filas, sesión anterior).
4. **La telemetría de la corrida no se persiste por fases** — la mejora de velocidad
   real de v1.9 (Tasks 1-3) sigue sin medirse limpia; la única A/B intentada quedó
   dominada por overhead de los patrones 1-3.

## Backlog priorizado (16 ítems)

### Prioridad alta

**1. Señales del gate condicional (Paso 2.5) por código, no por impresión — incluido
W-code ajeno.**
Fichero: `scripts/preclasificar.py` (nueva `senales_gate`) + `SKILL.md` Paso 2.5 + tests.
Cambio: función determinista `senales_gate(filas, wcode_caso, cobertura_filas=None)` —
(a) regex `W-[0-9A-Z]{5,6}` sobre nombre+ruta, señal si aparece W-code ≠ caso (remedio
por defecto: excluir, nunca copiar); (b) mismo nombre de origen con sha256 distinto
(casi-duplicado); (c) binarios opacos sin espejo MD (cruzando por `parent_sha256 or
sha256`); (d) pass-through de `requiere_identificar_parte`. Lista vacía → auto-aprueba;
no vacía → presenta y espera. Por qué: 3 de las 4 señales del gate son hoy
comprobaciones mentales del agente, y ya falló en producción (W-02X270).

**2. Check de frescura del checkout + versión 1.10 en frontmatter + prohibir
auto-reparación sobre la raíz git compartida.**
Fichero: `SKILL.md` (frontmatter + Paso 0) + guard en `scripts/check_skills.py` o test +
prompt-plantilla de subagentes. Cambio: (1) subir `version` a "1.10" en el frontmatter
(hoy divergente del CHANGELOG) + guard/test que compare frontmatter vs. primera entrada
del CHANGELOG; (2) Paso 0 bloqueante para checkouts git: `git fetch origin main --quiet
&& git diff --quiet origin/main HEAD -- .claude/skills/organizar-sala-lectura/` — si
difiere, ABORTAR y reportar, nunca auto-reparar con checkout parcial sobre la raíz
compartida; (3) en el prompt-plantilla de subagentes: "verifica frescura ANTES de leer
SKILL.md; si estás desactualizado, para y avisa". Por qué: en la pasada 2 el subagente
corrió parcialmente v1.8 creyéndose v1.9 (A/B invalidado) y se auto-reparó con
`git checkout origin/main --` sobre la raíz compartida, arriesgando el trabajo de otra
sesión concurrente.

**3. Detectar colisiones de `nombre_canonico` antes de copiar y en el verify.**
Fichero: `scripts/verificar_sala.py` + `scripts/copiar_manifiesto_rclone.py`
(`validar_pares`) + `SKILL.md` Paso 2. Cambio: (1) `verificar()` detecta
`nombre_canonico` repetido entre filas (hoy el `set` colapsa duplicados y el verify pasa
verde); (2) `validar_pares(pares)` en la copia aborta ANTES de tocar Drive si hay
`dst_relpath` duplicados; (3) regla explícita en Paso 2 de desambiguar con `_2`/`_3`
antes de persistir el plan. Por qué: único modo de fallo detectado que puede hacer
DESAPARECER un documento sin rastro en ningún check — en honorarios, perder un
requerimiento de pago es perder prueba.

**4. Prohibir editar artefactos generados para hacer pasar el verify + aviso de fallos
homogéneos.**
Fichero: `SKILL.md` Paso 6.5 + `scripts/verificar_sala.py`. Cambio: (1) si `verificar()`
devuelve ≥5 problemas del MISMO tipo, la hipótesis por defecto es bug del check —
contrastar 2-3 filas a mano y PARAR reportando al letrado; PROHIBIDO editar
`_MANIFIESTO`/índices/yaml a mano (cabecera "GENERADO — NO EDITAR" es vinculante; toda
corrección real se regenera desde el plan persistido); (2) `verificar()` agrupa
problemas por tipo y antepone "ATENCIÓN: N problemas homogéneos del tipo X — sospecha
del check, no de los datos" si supera el umbral. Por qué: modo de fallo más caro
observado — 21 filas de producción parcheadas a mano por un falso positivo.

**5. `ERROR_FILE_NOT_HYDRATED`: fallback a `rclone rcd` cableado automáticamente.**
Fichero: `SKILL.md` Paso 4 + tarea aparte en el plugin `expedientes-xl`. Cambio: (1) si
`copy_path` falla con `ERROR_FILE_NOT_HYDRATED`, NO anotar pendiente — reintentar ESE
fichero vía `copiar_renombrar()` (server-side, inmune al caché de hidratación local);
solo si también falla, pendiente; (2) si el precheck de rclone (ítem 6) da verde, `rcd`
pasa a ruta de copia PRIMARIA en Modo 1; (3) tarea aparte para el fix raíz del plugin
(re-stat en frío antes de devolver el error). Por qué: único fallo repetido idéntico en
AMBAS pasadas; la ruta rcd ya probada copió los 3 ficheros atascados en 19s (incl. 1,1
GB) — la resolución existe, depende de memoria humana, no del procedimiento.

**6. `precheck_rclone.py` determinista — el prerrequisito OAuth se verifica con exit
code, nunca leyendo documentación.**
Fichero: `.claude/skills/organizar-sala-lectura/scripts/precheck_rclone.py` (nuevo) +
`SKILL.md` Paso 4 + tests. Cambio: script stdlib que ejecuta `rclone config show
<remote>`, extrae SOLO la línea `client_id` por regex (NUNCA la config completa —
token/client_secret en claro), exit 0 si hay client propio (project ≠ `202264815644`),
exit != 0 si no o si `rclone` no existe. `SKILL.md`: "solo vale el exit code — NO
deduzcas este prerrequisito leyendo documentación". Por qué: en la pasada 2 el agente
concluyó desde un doc archivado pre-julio que el client propio no existía (falso; un
comando de 1s lo confirmaba) — la mejora de velocidad estrella de v1.9 nunca se probó.

**7. CLI para `verificar_sala.py`: verify determinista de extremo a extremo.**
Fichero: `scripts/verificar_sala.py` (`main` nuevo) + `SKILL.md` Paso 6.5 + tests de
integración. Cambio: `python verificar_sala.py <sala_dir> [--cobertura <ruta>]` — parsea
él mismo el `_MANIFIESTO.md` (parser compartido con `manifiesto_a_catalogo`), lista el
directorio recursivamente con exclusiones cableadas, exit 1 si hay problemas.
Extensión opcional: `--hash {no|muestra|completo}` que contraste sha origen↔copia al
menos para ficheros reintentados + muestreo 10%. Por qué: hoy sus ENTRADAS (parseo,
listado) las ensambla cada agente por juicio — el mismo agente que se equivocó decide
qué ve el check que debe cazarlo. Y verify comprueba existencia, no integridad.

**8. Columna `categoria` en el `_MANIFIESTO` + índices generados por script.**
Fichero: `SKILL.md` Paso 5 + `scripts/manifiesto_a_catalogo.py` (`_COLS`,
`CAMPOS_EMITIDOS`) + `scripts/indices_desde_manifiesto.py` (nuevo) + tests. Cambio:
añadir columnas `categoria` y `subcategoria_crm` al `_MANIFIESTO.md` (y al YAML); nuevo
script que derive `INDICE.md`/`CRONOLOGIA.md` deterministamente. `SKILL.md` Paso 5:
"escribe el `_MANIFIESTO.md` y ejecuta el script" — el LLM deja de transcribir ~350
líneas de markdown por corrida. Por qué: la promesa de re-aplicación ("conserva la
clasificación previa") es hoy incumplible porque el manifiesto no persiste la
clasificación; los índices a mano son parte medible de la fase lenta (30+ min); el YAML
(SSOT máquina) omite el dato por el que se construyó la sala.

### Prioridad media

**9. Corrida interrumpida: progreso durable por fila + protocolo de reanudación.**
Fichero: `scripts/copiar_manifiesto_rclone.py` (`copiar_manifiesto`) + `SKILL.md` §
Re-aplicación. Cambio: `progreso_path` opcional (línea JSON append por fila
completada/fallida a `_plan/copia-<fecha>.jsonl`); nuevo párrafo "Corrida interrumpida"
en `SKILL.md` — reconstruir desde el plan persistido + jsonl + disco, reanudar solo lo
pendiente. Por qué: el `_MANIFIESTO` (única llave del skip incremental) se escribe
DESPUÉS de copiar todo; una sesión que muere a mitad del Paso 4 deja N ficheros
copiados y CERO registro.

**10. Leer siempre el representante de hilo de los `.eml` que caen al default 07.**
Fichero: `SKILL.md` Paso 1-bis.c. Cambio: mantener los 6 patrones estrechos, pero para
`.eml` el representante de cada hilo con motivo `default_reclamaciones` SÍ se lee
siempre (una lectura por hilo, no por mensaje) y su categoría se propaga. Por qué:
trade-off mal calibrado — ~12 correos de correspondencia con el vendedor (prueba
nuclear de activación) degradados de 01.ACTIVACIÓN a 07 en W-02VUDR; ~30 lecturas
baratas recuperan la calidad conservando casi toda la ganancia de velocidad.

**11. Dos bugs deterministas de `preclasificar.py`: exports WhatsApp crudos y
`agrupar_por_hilo` con cifras.**
Fichero: `scripts/preclasificar.py` (`dedup_por_sha`, `_SUFIJO_HILO_RE`) + tests con
nombres reales anonimizados de W-02VUDR. Cambio: (1) `emparejar_exports_whatsapp()` —
detectar el export crudo (zip/blob) con versión extraída del mismo chat y marcarlo
duplicado, sin fila propia; (2) `agrupar_por_hilo` — tratar `_N` como sufijo de hilo
SOLO si el nombre base sin sufijo existe en el conjunto (evita fusionar por un precio
tipo `..._1_990_000`). Por qué: (1) fabricó 5 filas basura `0000-00-00` en el
manifiesto real de W-02VUDR — el verify nunca las cazará (los crudos no tienen espejo).

**12. `_parse_filas` estricto: ninguna fila del manifiesto desaparece del catálogo en
silencio.**
Fichero: `scripts/manifiesto_a_catalogo.py` (`_parse_filas`) + tests. Cambio: contar
líneas candidatas y, si el nº parseado difiere, imprimir las rechazadas y exit != 0;
validar sha256 con `fullmatch [0-9a-f]{64}`. Por qué: hoy una fila malformada hace
`continue` sin aviso — el documento existe en la sala pero no en la SSOT máquina.

**13. Definir el Modo 3 degradado: md5 prefijado para binarios grandes.**
Fichero: `SKILL.md` (gotcha sha256 + Paso 4) + `scripts/manifiesto_a_catalogo.py`.
Cambio: en Modo 3, ficheros grandes admiten `md5:<hash>` en la columna sha256; la
primera sesión con filesystem completa los sha256 pendientes. Por qué: la instrucción
actual ("calcula sha256 descargando los bytes") es incumplible para un vídeo de 1,1 GB
en nube pura.

**14. Endurecer `copiar_manifiesto_rclone`: timeout/async en copias grandes + ciclo de
vida del `rcd`.**
Fichero: `scripts/copiar_manifiesto_rclone.py` (`copiar_renombrar`, `_rc_activo`) +
`SKILL.md` Paso 4 + tests. Cambio: `_async` + polling o timeout parametrizable (hoy 60s
síncrono cuenta una copia grande legítima como fallida); `proc.terminate()` al acabar
si `levantar_rcd_si_falta()` devolvió `Popen` (hoy queda un rcd huérfano en :15572).
Por qué: la primera copia server-side >60s reintroduce el síntoma de "fichero
pendiente" que motivó todo este backlog.

### Prioridad baja

**15. Fecha aproximada `(*)`: sacar el marcador del valor.**
Fichero: `scripts/manifiesto_a_catalogo.py` + `scripts/verificar_sala.py`. Cambio:
detectar sufijo `(*)`, emitir `fecha_doc` limpia + `fecha_aproximada: true` en el YAML.
Por qué: el YAML lleva hoy fechas no parseables (`"2024-06-06(*)"` real).

**16. Telemetría de fases en el plan persistido.**
Fichero: `SKILL.md` Paso 2-bis y Paso 7. Cambio: el plan de `_plan/` gana líneas de
cronometraje por fase (ISO-8601) que el ejecutor rellena y el Paso 7 reporta — sin
código nuevo, solo prosa. Por qué: la mejora de velocidad de v1.9 sigue sin medirse
limpia; con timestamps por fase, la 3ª corrida da por fin el A/B real.
