# Handoff W-046G2R — mejoras de proceso en apertura de expedientes (1 de 3)

> **Autocontenido para una sesión nueva de Claude Code (sin memoria de la
> conversación previa).** Nikolai hizo 3 aperturas de expediente el
> 2026-07-17 en sesiones/worktrees distintos y quiere consolidar los 3
> handoffs en una sesión dedicada de mejora de proceso (posible skill
> `abrir-caso`, mejoras de CLI, o solo documentación). Este fichero cubre
> **una** de esas tres sesiones: alta → intake → viabilidad → retipificación
> → archivo de un expediente extrajudicial de Engel & Völkers.

**Higiene PII:** el caso se referencia solo por su ID GO **W-046G2R**. No se
incluyen nombres de calle ni de terceros — quien consolide este handoff debe
mantener la misma disciplina en el documento resultante.

## Qué se hizo (cronología resumida)

1. Triaje de un correo de consulta (Engel & Völkers, MC Barcelona) sobre una
   compraventa frustrada — identificación del caso W-046G2R.
2. Alta completa vía `scripts.abrir_caso`: carpeta Drive + intake
   `drive_ev` (53 ficheros) + alta CRM extrajudicial (expediente 623),
   tipo inicial `DEVOLUCION_RESERVA` (defensiva).
3. Intake incremental: etiqueta Gmail creada y correo exportado
   (`--fuente email`), export de WhatsApp depositado (`--fuente whatsapp`).
4. Sala de máquina (OCR de 86 documentos vía `scripts.sala_maquina`).
5. Lectura de la documental (encargo, contrato de arras, prórroga,
   desistimiento, chat de WhatsApp) → opinión de viabilidad: retener la 1ª
   parte de honorarios ya cobrada es sólido; reclamar la 2ª es defendible
   pero contestado (riesgo de *contra proferentem* sobre una cláusula que
   redactó la propia agencia).
6. Retipificación a `NEGATIVA_ESCRITURA` (actora) — renombrado de carpeta +
   `_caso.md` + ~80 ficheros de la sala de máquina + CRM (referencia, tags,
   posición) + etiqueta Gmail.
7. Alta de la ficha del contrario en el CRM + vinculación al expediente.
8. **Archivo del expediente** (inviable): CRM `historico`, actuación
   facturable, etiqueta Gmail movida y coloreada, carpeta Drive movida a
   scaffolding nuevo de archivo, informe `.md`, evento en `_intake_log.jsonl`.
9. Cierre de sesión con hallazgo operativo grave (ver más abajo) corregido
   antes de comitear.

## Catálogo de fricciones y atajos (para no repetirlas)

**Localización del caso desde el correo**
- Un enlace de Gmail `#inbox/<fragment-id>` **no** es un `thread_id` válido
  para la API (`read_thread` da `Invalid id value`). Ir directo a
  `search_messages` por remitente/asunto, o abrir el enlace en el Browser.
- `search_messages` sin acotar excede el límite de tokens de salida. Acotar
  `max_results` bajo y afinar el `query` antes de buscar amplio.

**Drive**
- `get_file_metadata(folder_id)` **ya devuelve `driveId`** — es literalmente
  el `--team-id` que pide `abrir_caso`. No hace falta `list_shared_drives`
  para "encontrarlo".

**Alta del caso (`scripts.abrir_caso`)**
- Los códigos de equipo (`BaRS3`, `MaRS2`...) **siempre** colisionan con
  casos anteriores del mismo equipo — no es un caso raro, es la norma. Usar
  `--yes` desde la primera llamada, no esperar al fallo (si no, el proceso
  queda colgado en background esperando confirmación interactiva).
- Cada intake incremental posterior obliga a repetir los 6 flags de
  identidad (`--w-code --ciudad --tipo-caso --codigo-caso --sufijo
  --direccion`) idénticos al nombre real de la carpeta, con `--force`.
  Frágil ante cualquier diferencia de espaciado/tilde. **Candidato de
  mejora de CLI:** aceptar `--case-id "<nombre completo>"` para intakes
  incrementales, sin recomponer la identidad cada vez.
- Export de WhatsApp: el nombre del `.zip` suele decir con quién es el chat
  (`"...Cliente Vendedor.zip"` / `"...Cliente Comprador.zip"`) → mapear
  directo a los 4 roles de `config.WHATSAPP_SUBDIRS` (`00_Consultor
  propietario`, `01_Consultor buscador`, `02_Grupo operacion`, `03_Otros`).
- **El sufijo del `case_id`** (el descriptor final, p. ej. "... - Negativa
  escritura") **se deriva del `tipo_caso` canónico**
  (`NEGATIVA_ESCRITURA`→"Negativa escritura"), nunca de una paráfrasis
  libre — si no coincide, hay que renombrar todo cross-sistema (carpeta
  Drive + referencia CRM + etiqueta Gmail), como pasó en otra de las 3
  sesiones de hoy. Fijar el sufijo canónico antes de la alta evita ese
  renombrado.

**Sala de máquina**
- `plan` (preview) es instantáneo; `apply` con OCR real puede tardar varios
  minutos incluso con pocas decenas de documentos — lanzarlo siempre en
  background si son más de ~15 documentos.

**Extracción de datos para fichas CRM (la fase más lenta de hoy)**
- Identificar contrario/importes/fechas se hizo a mano (`grep` sobre los
  `.md` de la sala de máquina + `Read` selectivo de cabeceras). Esto es
  exactamente lo que ya hace la skill **`viabilidad-prerelleno`**
  (extracción anclada a fuente). **Candidato de mejora de proceso:**
  correrla nada más terminar la sala de máquina cuando hay que dar de alta
  un contrario, en vez de journaling manual.

**CRM sudespacho — endpoints/campos confirmados hoy (evita tantear)**
- Alta expediente extrajudicial: `POST /api/element_register/extrajudiciales`
  (REST-first, `x-api-key`, sin PHPSESSID) vía
  `core.sudespacho_create.create_expediente`.
- Archivar (sin borrar): `PUT /api/element_register/extrajudiciales/{id}`
  con `historico` (CheckBox), `referencia_historico` (TextCorto — motivo
  breve, MAYÚSCULAS_GUION_BAJO), `fecha_alta_hist` (Date).
- Actuaciones: elemento `actuaciones`. Campos clave: `Subject` (TextArea,
  patrón `"<PREDEFINIDA> - <breve personalización>"`, p. ej. `"SENIOR -
  EXTRAJUDICIAL - <resumen>"`), `Description` (TextAreaLong), `Estado`
  (Select: Planificado|Hecho), `facturar` (CheckBox), `tipo_facturacion`,
  `duracion`, `precio_hora`, `profesional_asignado`, `id_predefinido`,
  `tags`. **Proceso correcto** (corregido a mitad de sesión): el letrado fija
  horas/tarifa/predefinida sobre una propuesta aprobada; el asistente crea
  la actuación y completa `Description` tras esa aprobación — no antes ni
  sin ella.
- Crear cliente contrario: `POST /api/element_register/clientes_contrarios`
  con `{nombre,1apellido,2apellido,nif_cif,direccion,cp,poblacion,
  provincia,nacionalidad,tipo_doc_identidad,ccc,email,notas}`, todo en
  **MAYÚSCULAS excepto el email**. `provincia`/`nacionalidad`/
  `tipo_doc_identidad` son `Select` — usar el valor literal del enum
  (`GET /api/view/enums/clientes_contrarios/{prop}`), no inventarlo: p. ej.
  `nacionalidad="España"` (no `"ESPAÑA"`), `tipo_doc_identidad="2"`
  (NIF/CIF/NIE).
- Vincular partes: `POST /api/relation_element/extrajudiciales/{id}` con
  body `["right.clientes_contrarios.{id}", "right.clientes_propios.2"]`
  (`2` = EV MMC SPAIN). **Ojo (confirmado por otra de las 3 sesiones de
  hoy):** el `relatedElement`/`relatedId` que acepta el `POST` de creación
  de la actuación **NO vincula de forma fiable** — vincular siempre aparte
  con `relation_element`, igual que con los contrarios.
- Actuación — `duracion` se rellena en formato **`HH:MM:SS`**, el CRM lo
  convierte a segundos internamente (no enviar segundos crudos). Tarifa por
  hora: **confidencial, se lee/fija solo por la UI** (config personal del
  usuario), nunca hardcodear ni pedirla por API.
- Tags del extrajudicial: formato `"#{color}___{tag_id}"`, orden canónico
  equipo(rojo)→asunto(verde)→valoración(lila)→ciudad(azul); constantes en
  `core/sudespacho_create.py` (`TAG_ROJO_*`, `TAG_VERDE_*`, `TAG_LILA_*`,
  `TAG_AZUL_*`).
- Descubrir campos de cualquier elemento: `GET /api/view/config/{elem}/fields`.
  Descubrir enums de un campo Select: `GET /api/view/enums/{elem}/{prop}`.
- **Regla de verificación:** tras cualquier `PUT`/`POST`, hacer un `GET` de
  verificación inmediato. La columna "Contrario" del listado de
  `clientes_contrarios` en la UI **no refleja** cambios de apellidos (solo
  muestra `nombre`) — solo la API es fuente fiable.

**Etiquetas Gmail — convención confirmada midiendo 226 etiquetas reales**
- Color de etiqueta de **caso** (leaf, activa o archivada):
  `{backgroundColor:"#4986e7", textColor:"#ffffff"}` — mayoritario en ambos
  árboles. Las carpetas de **ciudad** (nivel padre) son verdes (`#16a765`)
  — no confundir nivel.
- Nombre de la etiqueta leaf = `Referencia_Cliente` del CRM = nombre de la
  carpeta del caso en Drive (mismo string exacto en las tres superficies).
- "Mover" una etiqueta = `labels().patch(id, {name: "<nuevo path>"})` — NO
  re-etiqueta los hilos, los conserva con el nuevo path. Aplicar color =
  `labels().patch(id, {color: {...}})`.
- Estructura: `01. CONTING/01. EXTRAJUD/<ciudad>/<caso>` (activo) vs
  `03. ARCHIVO/01. ARCHIVO - EXTRAJUDICIALES/<año>/<caso>` (archivo
  extrajudicial) / `02. ARCHIVO - JUDICIALES/<año>/<caso>` (archivo
  judicial). Se van a mover MUCHAS etiquetas en archivos masivos y
  transiciones extrajudicial↔judicial — candidato claro a automatizar.
- `list_labels` sobre miles de etiquetas excede tokens — volcar a fichero y
  `grep`/filtrar ahí, nunca re-listar ni leer entero.

**Drive — archivo**
- Scaffolding `CASOS/_ARCHIVO/01. EXTRAJUDICIALES/<año>/` y
  `CASOS/_ARCHIVO/02. JUDICIALES/` **no existía** antes de hoy — se creó
  ad-hoc. Ya existe para la próxima vez.
- Al archivar, actualizar `_caso.md` en **dos niveles** del frontmatter
  (raíz y `meta`): `estado: archivado` + motivo + fecha.
- El evento `archivado` **no está** en la constante cerrada
  `INTAKE_EVENTS` de `core/intake_log.py` — hoy se escribió la línea a mano
  en `_intake_log.jsonl` sin pasar por `intake_log.append_event` (que lo
  habría rechazado por validación). Pendiente de formalizar.

**Tests / entorno**
- 5 fallos en `test_sudespacho_relations.py::test_list_colaboradores_rest_*`
  son **ambientales**: los worktrees de git no heredan `.env` (gitignored)
  de la raíz del repo. No es una regresión de código si no se tocó
  `core/sudespacho_*`.

## Incidente grave del cierre (ya corregido, léase antes de repetir el patrón)

Gran parte de esta sesión ejecutó comandos de shell y ediciones de fichero
con `cd`/rutas absolutas a la **raíz compartida del repo**
(`C:\Users\tnm33\Dev\FeesDefender`) en vez del **worktree asignado**
(`.claude\worktrees\<nombre>`). La raíz compartida es un checkout activo
donde otras sesiones o el harness pueden hacer checkout/commit en paralelo
— el reflog mostró un checkout a una rama `wip/mejora-archivar-caso` con un
commit de mensaje `"@"`, y vuelta a `main` ya con otro PR mergeado, todo
mientras esta sesión trabajaba. Una edición a `docs/MEJORAS_FUTURAS.md` se
perdió **dos veces** por sobrescritura silenciosa (sin conflicto de git,
porque nunca llegó a comitearse).

**Ya corregido y documentado** — no hace falta re-descubrirlo:
- `docs/DEAD_ENDS.md` → entrada "Worktree asignado vs. raíz compartida del
  repo".
- Memoria `feedback-worktree-vs-raiz-compartida`.
- Regla a aplicar en las próximas 2 sesiones que se consoliden: verificar
  `pwd`/`git branch --show-current` antes de tocar ficheros del repo, y si
  el cwd es la raíz y hay worktree asignado, corregir de inmediato.

## Ya registrado, no duplicar en la consolidación

- `docs/MEJORAS_FUTURAS.md` **#66** — workflow completo de archivo de caso
  (candidato a `core/archivar_caso.py`), con el checklist de los 5 pasos.
- Memorias actualizadas esta sesión: `feedback-crm-fichas-mayusculas`,
  `reference-sudespacho-archivo-actuaciones`,
  `reference-gmail-etiquetas-organizacion`,
  `reference-sudespacho-crm-cableado-expediente`,
  `feedback-worktree-vs-raiz-compartida`.

## Preguntas abiertas para la sesión de consolidación

1. ¿Construir una skill `abrir-caso` (hoy solo hay el script CLI
   `scripts/abrir_caso.py`, sin skill que oriente el flujo completo) que
   incorpore este checklist fase por fase?
2. ¿Mejorar la CLI para intake incremental por `--case-id` en vez de
   repetir los 6 flags de identidad?
3. ¿Enganchar `viabilidad-prerelleno` automáticamente tras la sala de
   máquina cuando el caso necesita alta de contrario (evita el grep manual
   que fue la fase más lenta de hoy)?
4. ¿Priorizar la construcción del MCP `sudespacho` F1 (ya diseñado,
   docs-only, `project-mcp-sudespacho-crm`)? Tantear campos/enums de la API
   a mano cuesta ~8-10 llamadas cada vez que no está fresco en memoria.
5. ¿Consolidar la chuleta de campos/enums/tags del CRM en
   `docs/INTEGRACION_SUDESPACHO.md` (fuente compartida del despacho, no
   solo memoria personal de esta sesión — para que sobreviva también en
   Cowork y otras sesiones)?
6. ¿Formalizar `archivar_caso`: añadir `archivado` a `INTAKE_EVENTS`,
   decidir el enum cerrado de motivos de archivo (visto en `MEJORAS #66`)?
