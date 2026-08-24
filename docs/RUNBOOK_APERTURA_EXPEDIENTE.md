---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-22
---

# RUNBOOK — Apertura de expediente (FeesDefender)

> **Fuente única operativa** del flujo de apertura E2E de un expediente de honorarios de
> Engel & Völkers: alta → intake multi-fuente → sala de máquina → etiqueta Gmail →
> sala de lectura → viabilidad → ficha CRM completa → (si procede) archivo → cierre.
>
> Consolida los 3 handoffs de las aperturas del 2026-07-17 (W-02T3XO, W-02TH0W, W-046G2R;
> en `docs/superpowers/handoffs/handoff-2026-07-17-apertura-W-*.md`) + los hallazgos de la
> apertura de W-02VUDR (2026-07-21: `[APER-35]` a `[APER-40]`) + los hallazgos de la
> apertura EN LOCAL de W-02ZIIF (2026-07-22: `[APER-41]` en adelante). Las etiquetas
> `[APER-xx]` remiten al hallazgo original.
>
> **SSOT del detalle CRM (endpoints, campos, enums, tags):** `docs/INTEGRACION_SUDESPACHO.md`
> (§10–§15). Este runbook **no duplica** la API; la orquesta y marca los gotchas.
>
> **Higiene PII (nunca se rompe):** en este documento y en todo lo que produzcas
> (docs, bitácora, commits, **nombres de rama**, campos libres del CRM), el caso se
> referencia solo por `W-XXXXXX`. Nunca nombre/dirección/NIF/teléfono de tercero.

---

## 0. Entorno e higiene (leer antes de tocar nada)

- **`[APER-01]` Ejecuta el PIPELINE desde el repo principal, sandbox OFF.** Un worktree no
  hereda `.venv`, `.env`, `CASOS_ROOT` ni PHPSESSID (gitignored) → el pipeline no corre ahí.
  Prefijo: `Set-Location "C:\Users\tnm33\Dev\FeesDefender"` + `.venv\Scripts\python.exe`.
  `G:` y los tokens de Google/Gmail (en `~`) sí son accesibles desde cualquier sitio.
- **Worktree vs. raíz compartida (regla que nunca se rompe).** Si tu sesión tiene un
  **worktree asignado**, las **ediciones de ficheros del repo** (docs, código, `PLAN.md`,
  `STATUS.md`) van en el worktree, **nunca** por `cd`/ruta absoluta a la raíz compartida:
  otra sesión o el harness pueden hacer checkout/commit en paralelo y **sobrescribir tu
  edición sin conflicto de git** (pasó dos veces con `MEJORAS_FUTURAS.md`). Verifica
  `pwd` / `git branch --show-current` antes de editar. Correr el pipeline desde la raíz
  (que sí tiene entorno) y **editar** en el worktree no es contradictorio: el pipeline
  toca `CASOS` en `G:` (fuera de git), no ficheros versionados. Detalle:
  `docs/DEAD_ENDS.md` (entrada "En un worktree, el `cd` de Bash al repo raíz apunta al
  PRINCIPAL, no al worktree") + memoria `feedback-worktree-vs-raiz-compartida` (recoge el
  facet de sobrescritura silenciosa de ediciones, sin conflicto de git).
- **`[APER-40]` / W-02VUDR — Comandos de shell: PowerShell, no Bash.** Rutas con
  backslash (`.venv\Scripts\python.exe`) ejecutadas por un tool Bash (POSIX sh) pierden
  los backslashes (`exit 127`). Y **nunca** `Glob`/`grep` recursivo sobre `G:\` sin
  acotar para localizar algo de un caso concreto — `G:` es Drive Stream-con-caché
  (filesystem virtual), no disco local, y cuelga/hace timeout. Ir directo a
  `CASOS_ROOT` acotado (`Get-ChildItem` en PowerShell) o, si el dato vive en CRM, a la
  API (`core/sudespacho_relations.py`) en vez del filesystem. Memoria
  `feedback-eficiencia-herramientas-windows-drive`.
- **`[APER-41]` / W-02ZIIF — Modo local (opcional, más rápido para el pipeline mecánico).**
  En vez de `CASOS_ROOT = G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS`, apunta
  `CASOS_ROOT` a una carpeta local temporal (p. ej. `$env:USERPROFILE\Desktop`) **en la
  misma invocación de cada comando** (`core/config.py:31` lee la env var, no persiste entre
  llamadas de herramienta). Corre TODO el pipeline mecánico ahí (alta → intake → sala de
  máquina → sala de lectura) y haz *checkin* a Drive solo al final, antes de la ficha CRM.
  - **Por qué:** medido en W-02ZIIF (2026-07-22) — OCR+split ~18 min, sala de lectura
    (skill completa, Paso 0 → catálogo) ~25 min, alta CRM con 2 vínculos <2 min de
    ejecución real. Evita además los cuelgues de `G:` de `[APER-40]` por completo (no hay
    Drive Stream-con-caché de por medio; escrituras NTFS reales, atómicas de verdad).
  - **Aviso honesto:** esta prueba corrió TODO en serie — no se midió la ventaja de
    paralelizar fases sobre el mismo caso, que era la motivación original de valorar el
    modo local. Y la infraestructura de checkout/checkin (`project-biblioteca-checkout-checkin`)
    asume un caso YA EXISTENTE en Drive para hacer el merge a 3 vías — **no cubre un caso
    que nace en local** sin ese baseline previo. Ese primer *checkin* de un caso nuevo es
    un hueco de infraestructura sin resolver, no algo ya construido — no prometer una vía
    de vuelta a Drive sin verificarla primero. Memoria `project-apertura-local-vs-drive`.

---

## 1. Recon en paralelo (antes de preguntar) `[APER-02]`

Con el hilo de Gmail + la carpeta de Drive del caso, lanza **a la vez**:

- `list_accounts` (Gmail + Drive),
- `get_folder_path` + **`get_file_metadata` de la carpeta** — `get_file_metadata` **ya
  devuelve `driveId`**, que es literalmente el `--team-id` que pide `abrir_caso`; **no hace
  falta `list_shared_drives`** para "encontrarlo" (W-046G2R),
- lectura del hilo.

En 2 tandas salen caso, partes e importe.

**Localización del caso desde el correo (gotchas, W-046G2R):**
- Un enlace `#inbox/<fragment-id>` de Gmail **no** es un `thread_id` válido (`read_thread`
  → `Invalid id value`). Ir a `search_messages` por remitente/asunto, o abrir el enlace en
  el Browser.
- `search_messages` sin acotar excede el límite de tokens → `max_results` bajo y `query`
  afinado antes de buscar amplio.

---

## 2. Identidad: auto-derivar, no preguntar

De las 4 preguntas clásicas de apertura, **3 son auto-derivables**; la única real es el
**alcance** (¿uno o varios asuntos en el hilo?).

- **`[APER-03]` Equipo `BaRS<N>` = nombre de la unidad compartida del Drive**
  (`"Barcelona - S3"` → `BaRS3`). Del `driveId` de la carpeta. NO preguntar. La CLI lo
  auto-deriva (B5).
- **`[APER-04]` / W-046G2R — Sufijo = `tipo_caso` CANÓNICO**, nunca paráfrasis libre
  (`VUELTA` → `"Vuelta"`; `NEGATIVA_ESCRITURA` → `"Negativa escritura"`). Ofrecer una
  paráfrasis obliga a renombrar carpeta Drive + `_caso.md` + etiqueta Gmail + referencia
  CRM cross-sistema (pasó en W-02T3XO). Fijar el sufijo canónico **antes** del alta.
  Memoria `feedback-case-sufijo-tipo-canonico`.
- **`[APER-05]` `--tipo-caso` se deduce del hilo** (vuelta / negativa / bad debt / …).
- **`[APER-35]` / W-02VUDR — Si al buscar candidatos CRM por W-code aparece MÁS DE UN
  expediente, es un caso con varios frentes (p. ej. demanda solo contra el propietario +
  extrajudicial previo + un judicial "de cortesía" contra el comprador que no se
  demanda), no un error de búsqueda.** `list_expedientes_judiciales_candidatos`/
  `_rest_search_expedientes` (`core/sudespacho_relations.py`) devuelven TODOS los que
  contienen el W-code. **Parar y confirmar con el letrado el alcance** (¿local = un solo
  caso o uno por frente?) antes de fijar `--tipo-caso`/`--direccion` — no asumir 1:1
  caso↔expediente. Ver memoria `feedback-case-sufijo-tipo-canonico`.

---

## 3. Alta + intake inicial `[APER-07]`

```powershell
python -m scripts.abrir_caso --w-code W-XXXXXX --ciudad Barcelona --tipo-caso VUELTA `
  --direccion "..." --folder-id <id> `
  --fuente drive_ev --crm api --cuantia <n> --yes --force
```

> **Modo V1 (`--modo v1`) — hoy es una PUERTA, todavía no la secuencia.** Lo escribo así porque
> la primera versión de este bloque decía «la primera vertical **se ejecuta con**…», y eso era
> falso: el Plan 1 acota el modo, no lo cablea. Lo declaró R6/H6-09.
>
> **Lo que el modo ya hace.** `--modo v1` es el **discriminante**: rechaza, antes de resolver
> identidad, de `ensure_case`, de todo intake y de toda lectura remota, las cinco invocaciones que
> V1 prohíbe — `--crm` distinto de `skip` (el default es `api` y alcanza un POST de alta),
> `--fuente email|manual|whatsapp` (`email` ejecuta `email_export.export_label`, o sea Gmail),
> `--force` sin `--case-id` (crearía una carpeta sombra: criterio 33), `--dry-run` (en `drive_ev`
> el pull es real igual y la corrida sale sin terminar en ninguno de los tres estados) y la falta
> de `--folder-id`. Los errores se acumulan: se ven todos en una pasada.
>
> **Ojo con el comando de arriba:** lleva `--crm api` y `--force`. Copiarlo y añadirle `--modo v1`
> aborta, y debe abortar. La forma V1 es `--modo v1 --crm skip --fuente drive_ev --folder-id <id>`.
>
> **Lo que el modo NO hace todavía.** No encadena el pull de Sudespacho, ni la atomización local
> del correo ya depositado, ni la sala de máquina, que son parte de V1 (§21). Eso llega con el
> Plan 5. Hasta entonces, una corrida en `--modo v1` es una apertura acotada y reconocible, **no**
> la secuencia V1 completa, y no puede declararse `completo`.
>
> **Sin `--modo`**, el comportamiento es el de siempre (`libre`) — el que usan V2, V3 y el uso ad
> hoc. La única diferencia observable es que `--help` ahora lista una opción más.
>
> Contrato: spec de apertura integral §24 D3 y §21; adjudicación de R6 en el §6 del plan
> `docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md`.

- **`[APER-34]` Auto-derivación (B5):** en `--fuente drive_ev`, si se omiten,
  `--team-id` (driveId), `--codigo-caso` (nombre de la unidad compartida vía Drive API) y
  `--sufijo` (del `tipo_caso` canónico) se **auto-derivan** desde `--folder-id`. Los flags
  explícitos SIEMPRE ganan. Si `codigo_de_unidad` no puede derivar (unidad comercial,
  ambigua como `"Sevilla - S1 / S6"`, o ciudad fuera del mapa), la CLI pide `--codigo-caso`
  explícito con un error claro (nunca un código equivocado).
- **`--yes` desde la primera llamada.** La colisión del código `BaRS<N>` con casos previos
  del mismo equipo **es la norma, no la excepción** (W-046G2R). Sin `--yes`, el prompt
  "el código BaRS3 ya existe" cuelga el proceso en background esperando confirmación.
- **`--force` si el W-code ya existe** (2ª pasada de intake). **`[APER-20]`**: `ensure_case`
  corre **antes** del corte de `--dry-run`, así que un dry-run seguido de la ejecución real
  "colisiona contra sí mismo" y exige `--force`. **Es comportamiento esperado, no un error**
  — forzar es seguro cuando es el mismo caso contra su propio esqueleto recién creado.
- En `drive_ev`, **`--dry-run` NO ahorra** (hace el pull real igual).
- **`[APER-19]`** El bug del `id_go` ya está arreglado (PR #54, en `main`): el W-code se
  persiste en `meta.id_go` de `_caso.md` → `case_locator.resolve_ref(w_code)` encuentra el
  caso. Ya no se desvía el intake a una carpeta nueva `CASOS\W-XXXXXX`.
- **`[APER-36]` / W-02VUDR — `--crm skip` (caso ya dado de alta en CRM ANTES de abrirse en
  Drive/local) NO vincula los expedientes ya existentes.** Deja "referencia pendiente +
  TODO" en `_caso.md`; hay que vincularlos a mano, uno por cada expediente que
  corresponda al caso (extrajudicial y/o judicial):
  ```python
  from core import case_manager
  case_manager.register_expediente(case_id, expediente_id, "extrajudiciales")
  case_manager.register_expediente(case_id, expediente_id_judicial, "expedientes_judiciales")
  ```
  Sin esto, `scripts.crm_ficha`/el archivo posterior no saben a qué expediente(s) del
  CRM corresponde el caso.
- **`[APER-42]` / W-02ZIIF — `--crm api` (arriba) da de alta SOLO la ficha
  EXTRAJUDICIAL.** No hay camino documentado en este runbook para un caso que nace
  judicial desde el principio (p. ej. llega ya con una demanda admitida) — es una
  **decisión de diseño pendiente**, no un bug a arreglar ya (ver §9, aviso de
  `crm_ficha.py`). Si el caso ya es judicial desde el día 1, usa `--crm skip` aquí y da de
  alta el expediente judicial aparte, a mano, siguiendo §9.

---

## 4. Intake incremental (fuentes adicionales)

Cada intake posterior resuelve la identidad desde `_caso.md` con **`--case-id <W-code o
case_id>`** (B2, PR-2) — no repitas los 6 flags de identidad. **`[APER-43]` / W-02ZIIF —
pasa `--crm skip` en TODAS estas llamadas, no solo en la primera del §3**: el default de
`abrir_caso` es `--crm api`, y olvidarlo en una llamada posterior crea una ficha
extrajudicial fantasma que hay que borrar a mano en el CRM (pasó en W-02ZIIF).

```powershell
python -m scripts.abrir_caso --case-id W-XXXXXX --fuente manual --src <carpeta|.zip> --crm skip --yes
python -m scripts.abrir_caso --case-id W-XXXXXX --fuente email --cuenta <gmail> --label <etiqueta> --crm skip --yes
```

`--case-id` es **excluyente** con los 6 flags de identidad (`--w-code --ciudad --tipo-caso
--codigo-caso --sufijo --direccion`); el caso debe existir ya. Para `--fuente drive_ev`
(re-pull) basta `--folder-id`: `--team-id` se auto-deriva del `driveId` (la identidad sale de
`_caso.md`; `--codigo-caso`/`--sufijo` no se pasan con `--case-id`).

- **Export de WhatsApp:** el nombre del `.zip` suele decir el chat
  (`"...Cliente Vendedor.zip"`) → mapear directo a los 4 roles de
  `config.WHATSAPP_SUBDIRS` (`00_Consultor propietario`, `01_Consultor buscador`,
  `02_Grupo operacion`, `03_Otros`) (W-046G2R).
- **Correo — adjuntos embebidos `[APER-17]`:** los adjuntos dentro de un `.eml` (p. ej.
  capturas de WhatsApp) **NO se extraen** en el intake (`export_label` con
  `extract_attachments=False`; `abrir_caso` no expone el flag). Se extraen con
  `python -m scripts.atomize_emails --ref ...` (motor aparte, manual). Solo es crítico si
  la prueba llega **únicamente por correo** sin copia en Drive (`MEJORAS #68`).
- **`[APER-44]` / W-02ZIIF — Verifica por sha256/nombre ANTES de depositar nada a mano en
  `00_Input`.** El intake **copia el duplicado igual y solo lo anota** (`duplicado_de`) —
  "N duplicados omitidos" en la salida del CLI **NO significa "no se copió"**. Si ya viste
  el mismo fichero por otra vía (p. ej. un enlace de Drive ya resuelto automáticamente
  durante la atomización de email), no lo vuelvas a depositar manualmente sin comprobar
  antes por hash o nombre — genera una copia redundante que luego hay que localizar y
  limpiar. Memoria `feedback-verificar-antes-de-depositar-intake`.
- **`[APER-37]` / W-02VUDR — Checklist obligatoria ANTES de `sala_maquina apply`, no
  después:** (1) si hubo intake de email, `scripts.atomize_emails --ref <case_id>`
  (`[APER-17]` es el motivo, esto es el paso que cierra el motivo); (2) si el caso ya
  estaba dado de alta en CRM (`--crm skip`, `[APER-36]`), `scripts.sync_sudespacho pull
  --case <case_id> --expediente <id> --element <extrajudiciales|expedientes_judiciales>
  --referencia "<referencia_cliente_exacta_del_CRM>"` por cada expediente vinculado —
  vincular el expediente (`[APER-36]`) NO descarga sus documentos, es solo bookkeeping.
  Saltarse esto deja `00_Input` incompleto y la sala de máquina hay que reprocesarla.
  Memoria `feedback-orden-intake-antes-sala-maquina`.
  **Dos cosas del pull, actualizadas el 2026-08-04 (`MEJORAS #113`):** deposita en
  `00_Input/05_CRM/<rama>/` y es **idempotente por hash**, así que repetirlo es seguro y
  no hay `--force` ni `--incremental`; y **no procesa nada** — el flag `--run-pipeline`
  llamaba al motor jubilado y se retiró, por eso este paso va *antes* de la sala de
  máquina y no dentro de ella. Si el caso arrastra una carpeta `00_Input/sudespacho_*/`
  (layout v1, congelado), el pull se bloquea y explica la migración: no lo fuerces sin
  mirar qué hay dentro.

---

## 5. Sala de máquina `[APER-09]`

```powershell
python -m scripts.sala_maquina apply "<case_id>"   # background
```

- `plan` (preview) es instantáneo; **`apply` (OCR real) tarda minutos** aunque haya pocas
  decenas de documentos → siempre en **background** si son más de ~15 (W-046G2R).
- **`[APER-21]`** Ficheros de Drive sin extensión usable (nombre sin punto, o `"… jpg"`) ya
  se **auto-detectan por firma de bytes** (magic bytes, PR #55). Si aún ves `sin_soporte`,
  es un formato genuinamente desconocido, no un fallo de nombre.
- **`[APER-39]` / W-02VUDR — NUNCA relanzar `apply` sobre el mismo caso sin comprobar que
  la corrida anterior en background terminó de verdad** (leer su `.output`, no asumir por
  el tiempo transcurrido). `core/sala_maquina.py` **no poda huérfanos**: sin `--force`,
  cada corrida FUSIONA sobre `_cobertura.json` persistido — si se detectó y corrigió un
  problema de intake (p. ej. `[APER-38]`) MIENTRAS una corrida seguía activa, esa corrida
  procesó el estado sucio y una 2ª corrida sin `--force` no lo arregla, solo añade
  trabajo redundante. Hace falta un **`--force`** (foto fresca desde el `00_Input`
  actual) para limpiar — y aun así **hay que borrar a mano** los `.md`/`.pdf`/`.txt`
  huérfanos en `02_Sala de máquina/{01_OCR,03_MD,raw_text}` de documentos que ya no
  están en `00_Input`, porque `--force` no los toca. Coste real medido: ~1h40 de OCR
  repetido evitable. Memoria `feedback-concurrencia-pipelines-y-tiempos-apertura`.
- **`[APER-45]` / W-02ZIIF — Un documento con texto roto/desordenado tras el split
  (letras sueltas, orden alterado) puede ser un defecto del PDF DE ORIGEN, no del
  pipeline** — visto en documentos generados por LexNET / Junta de Andalucía. Verifica
  comparando `extract_text()` del crudo original contra el derivado ANTES de sospechar
  del código. Memoria `reference-lexnet-pdf-layout-roto`.

---

## 6. Etiqueta Gmail (ya con judicial/extrajudicial decidido) `[APER-06]`

Se crea aquí, no antes de intake: para este punto normalmente ya sabes si el caso es
judicial o extrajudicial (a veces se sabe desde el recon del §1, a veces no hasta la sala
de lectura del §7) — crearla ya con el destino correcto evita tener que "moverla" después.
En W-02ZIIF (2026-07-22) se creó como extrajudicial antes de ver que ya había una demanda
admitida, y hubo que reubicarla — este orden lo evita en la mayoría de los casos.

Nombre de la etiqueta *leaf* = `Referencia_Cliente` del CRM = nombre de la carpeta del caso
en Drive (**mismo string exacto** en las 3 superficies).

**Jerarquía en la cuenta EV** (`nikolai.tyukhay@engelvoelkers.com`) — **`01. CONTING` es el
padre único** de ambas ramas; `02. JUDICIALES` NO es de primer nivel (confirmado 2026-07-22
sobre el listado real de etiquetas, W-02ZIIF):
- Activos extrajudiciales: `01. CONTING/01. EXTRAJUD/<ciudad>/BaRS<N> - <dir> - (W-XXXXX) - <tipo>`.
- Activos judiciales: `01. CONTING/02. JUDICIALES/<ciudad>/<caso>` (mismo patrón de
  numeración de ciudad que EXTRAJUD).
- **`mails.repositorio`**: `01. EXTRAJUDICIAL/...`.

**Colores y mecánica (W-046G2R, medido sobre 226 etiquetas reales):**
- *leaf* de caso (activa o archivada): `{backgroundColor:"#4986e7", textColor:"#ffffff"}`.
  Carpeta de **ciudad** (nivel padre): verde `#16a765`. **No confundir nivel.**
- **"Mover" una etiqueta = tool `rename_label(account, label, new_name)`** del MCP
  `gmail-multiaccount` (`plugins/gmail_mcp/server.py`, construida 2026-07-22) — usa
  `labels().patch(id, {name:"<nuevo path>"})` internamente, conserva los hilos, no
  re-etiqueta. El conector **no tiene `delete_label`** (decisión de diseño deliberada del
  módulo, no un hueco) — tras "mover", la ruta antigua queda vacía y hay que borrarla a
  mano desde Gmail si molesta. Aplicar color sigue siendo `labels().patch(id, {color:{...}})`.
- `list_labels` sobre miles de etiquetas excede tokens → volcar a fichero y `grep`.
- **`[APER-46]` / W-02ZIIF — Etiquetas de listas de distribución pueden parecer "la
  etiqueta del caso" sin serlo.** Una etiqueta como
  `02. LISTAS DISTRIBUCION LEGAL/01. LEGAL/sevilla.legal` se auto-aplica a casi todos los
  correos de una oficina cuando una bandeja compartida va en copia — verifica siempre el
  `name` real de la etiqueta (`list_labels`) antes de tratar cualquier label recurrente
  como la etiqueta específica de un caso.
- **`[APER-47]` / W-02ZIIF — Un mismo asunto puede partirse en varios `thread_id`** si la
  línea de asunto cambia a mitad de conversación (Gmail rompe el hilo). Al agrupar
  correspondencia de un caso, busca por remitente/persona/asunto amplio y revisa CADA
  `thread_id` distinto que aparezca — no asumas que todo cuelga de un único hilo.
- **`[APER-38]` / W-02VUDR — Verificar contaminación cruzada tras exportar la etiqueta,
  SIEMPRE que la etiqueta ya existiera de antes (no la acabas de crear tú).** Una
  etiqueta curada en otra sesión puede traer ruido: (a) administración interna del
  despacho — facturación mensual a `Proveedores.ES@engelvoelkers.com`, actas CFO+Legal,
  circularización de auditoría, cartas de auditores, reenvíos a
  `mails.repositorio@gmail.com` con `S/R:`/`M/R:`/`Contrario:` vacíos (memoria
  `feedback-intake-email-exclusiones`); (b) documentos de OTROS casos — grep el lote
  exportado buscando un W-code DISTINTO al del caso en nombre de fichero/asunto. Si
  aparece, **borrar directamente** tras exportar (no mover a una carpeta de cuarentena:
  sigue siendo visible para quien tenga acceso Drive al caso) — comprobar antes por
  `sha256` que ningún adjunto esté también en uso por un mensaje legítimo del caso.
  Regenerar índices: `core.email_export.write_indices_caso(case_id)` +
  `scripts.atomize_emails --ref <case_id>` (poda solo, y solo, los `.md` de mensaje
  huérfanos — los adjuntos hay que borrarlos a mano).

Memoria `reference-gmail-etiquetas-organizacion`.

---

## 7. Sala de lectura `[APER-10]` `[APER-22]`

**`[APER-48]` / W-02ZIIF — No mezcles análisis del fondo del expediente (fechas límite,
argumentos, estrategia) con la mecánica de intake.** Para llegar aquí ya deberías tener
cerrado TODO el intake + atomización + sala de máquina (§3-§5) — este es el punto natural
donde empieza la lectura real; no intercalar análisis a mitad de la mecánica de arriba.

**Usa la skill canónica `organizar-sala-lectura` (v1.3, estructura PLANA)** o el comando
todo-en-uno del CLI:

```powershell
python -m scripts.sala_lectura organizar "<case_id>"
```

- Si vas por pasos granulares, la secuencia COMPLETA es
  `catalogo → clasificar → [rellenar worklist] → aplicar → poblar → render`.
  **`poblar` copia los documentos; `render` solo escribe los índices.** (En W-02T3XO se
  olvidó `poblar` y la sala salió vacía.)
- La **subcarpeta con fecha es por diseño** `[APER-22]`: solo los `.eml` con adjuntos MIME
  (documentos compuestos) la generan; el resto es plano. No reinvestigar.
- **No uses el CLI deprecado `core/sala_lectura.py`** directamente: tiene 3 defectos
  latentes (ruta MD, colisión de nombres en `poblar`, subcarpetas por fuente) — `MEJORAS #67`.

---

## 8. Viabilidad-prerelleno `[APER-11]` `[APER-28]`

Skill `viabilidad-prerelleno`: lee `00_Input`, extrae datos anclados a fuente y genera el
`.xlsx`-bitácora. Reglas ya embebidas en la skill (PR #56), no renegociar:
- **Regla de oro 8 (vía de lectura):** preferir
  `01_Procesado/02_Sala de máquina/03_MD/<slug>.md` cuando su `_cobertura.md` es `ok`; caer
  al crudo de `00_Input` si es `low`/`empty` o no hay MD. Anotar la capa en la cita.
- **Regla 4 ampliada (hitos de existencia `[E]`):** para los 10 hitos cuya pregunta ES
  "¿existe este documento?", la **ausencia total** de referencia en `00_Input` puntúa
  **`0`, no `pendiente`**.

**Úsala como fuente de datos anclada para las fichas del CRM** (contrario, importes,
fechas) en vez del `grep` manual sobre los `.md` — fue la fase más lenta de las aperturas
de hoy (W-046G2R).

---

## 9. CRM — la ficha COMPLETA es una CHECKLIST `[APER-12]`

`abrir_caso --crm api` hace **solo el alta mínima** (referencia, cuantía, tags de *tipo*,
posición). El resto va **aparte**, todo **REST con `x-api-key`, sin PHPSESSID** `[APER-13]`.

> **Detalle de endpoints, campos y enums: SSOT en `INTEGRACION_SUDESPACHO.md` §10–§15.**
> Los tags equipo+ciudad ya van en el **alta** (`crm_payload`). Los pasos 2–5 los orquesta
> `python -m scripts.crm_ficha --case-id <W-code o case_id>` desde `00_Input/_ficha_crm.yaml`
> (B1, PR-3; el YAML lleva PII → solo en `data/CASOS/`). Hace GET de verificación tras escribir.
>
> **`[APER-49]` / W-02ZIIF — `crm_ficha.py` es EXTRAJUDICIAL-ONLY** (verificado en el
> código 2026-07-22: hardcodea `_ELEMENT_EXTRAJUDICIAL`, usa `link_ev_mmc` /
> `ensure_contrario_vinculado` / `get_expediente` / `update_expediente` — ninguno tiene
> equivalente `_judicial` cableado en este CLI). **Para un caso judicial hoy no hay
> orquestador**: hay que llamar `create_expediente_judicial` + `link_ev_mmc_judicial` +
> `link_contrario_judicial` + `ensure_colaborador_vinculado_judicial` a mano — no existen
> todavía `ensure_contrario_vinculado_judicial`, `get_expediente_judicial` ni
> `update_expediente_judicial`. Documentado como hueco pendiente, no como resuelto.

**Checklist de la ficha (extrajudicial — ver aviso de arriba para judicial):**
1. **Tags equipo (rojo) + ciudad (azul):** los pone **el alta** (`crm_payload` los deriva del
   `codigo` vía `tag_rojo_equipo` + `tag_azul_de_codigo`). Ya **no** hace falta un PUT posterior
   de tags. (Si alguna vez editas `tags`/`Notas` a mano, usa `update_expediente`, que preserva
   `Numero_Expediente`, §10.7.)
2. **Cliente propio EV:** `link_ev_mmc(exp_id, cliente_propio_id=…)` — id del `cliente_propio`
   del `_ficha_crm.yaml` (default EV MMC SPAIN `2`; ENGEL & VÖLKERS SPAIN `27`). `crm_ficha`
   aborta si el valor es desconocido (no linkea la entidad equivocada en silencio).
3. **Contrario:** `ensure_contrario_vinculado(...)` (dedup por NIF). El **deudor de
   honorarios es quien firmó el encargo**, no todo co-titular (W-046G2R, memoria
   `feedback-crm-fichas-mayusculas`). Para completar datos DESPUÉS del alta (email, móvil
   hallados más tarde) usa `update_cliente_contrario(contrario_id, cambios)`
   (`core/sudespacho_relations.py`, construido 2026-07-22) — reenvía TODOS los campos ya
   conocidos, no confirmado si el PUT de este elemento es parcial o de reemplazo completo.
4. **Colaboradores (TL + consultores):** `ensure_colaborador_vinculado(...)` (dedup email).
   **Ficha completa** (móvil + fijo) buscando la firma en su correo `@engelvoelkers.com`;
   si ya existe → `GET → merge → PUT` para no pisar. **`colaboradores` = personal PROPIO
   del cliente (E&V) — nunca el procurador/letrado de la parte contraria** (fácil de
   confundir por el nombre del campo).
5. **Nota/hechos inicial:** `update_expediente(exp_id, {"Notas": …})` con el narrativo (tipo +
   partes + cláusula + cuantía). `notas_html` en el `_ficha_crm.yaml`.
6. **(Si procede) Actuación facturable:** `POST element_register/actuaciones` **+ vincular
   aparte** con `relation_element` (§15.2/15.3). `duracion` en `HH:MM:SS` → segundos;
   `Prioridad` obligatoria; **tarifa solo por UI** (§15.4).
7. **`[APER-50]` / W-02ZIIF — Juzgado (solo judicial):** NO es una relación M2M simple ni
   una propiedad plana del expediente — es una relación con atributos propios vía el
   elemento intermedio `autos` (secuencia de 4 llamadas REST confirmada; detalle completo
   en `INTEGRACION_SUDESPACHO.md §12.5`). ⚠️ `fase_procedimiento` es un enum PROPIO de
   `autos`, distinto del `tipo_procedimiento` del expediente aunque la UI se parezca —
   resolver siempre vía `GET /api/view/enums/autos/fase_procedimiento`, nunca adivinar el
   valor interno. No cableado en código: `link_juzgado_judicial()` no existe todavía.

**Gotchas CRM (deduplicados):**
- **`[APER-13]` No es PHPSESSID:** alta, vínculos, contrario/colaboradores y actuaciones van
  por **REST `x-api-key`**. `check-legacy` (PHPSESSID) es otra vía; no mirarla para esto.
- **`[APER-14]` Móvil en 9 dígitos** (`6XXXXXXXX`): la API rechaza `+34`/espacios
  (`HTTP 400 movil is incorrect`). Si un escritor REST falla, cae al fallback legacy y pide
  cookie = **falsa pista** → arreglar el móvil (§8 gotcha).
- **`[APER-24]` `relatedElement`/`relatedId` en el POST de creación NO vinculan** — se
  ignoran en silencio (201 igual, pero la pestaña queda vacía). Vincular **siempre** por
  `relation_element` (§15.2/§15.3, §10.6).
- **`[APER-26]` PUT (no PATCH → 405) y es PARCIAL: preserva los campos omitidos**
  (verificado en vivo 2026-07-18, §10.7). Para editar un campo, `update_expediente(exp_id,
  {campo: valor})` envía **solo** ese campo — NO hace falta reenviar todo ni preservar
  `Numero_Expediente` a mano. El GET-detalle sí exige `?properties=` (el GET plano da HTTP 500).
- **MAYÚSCULAS** en las fichas (excepto email). Los `Select` (provincia, nacionalidad,
  tipo_doc) usan el **valor literal del enum** (`GET /api/view/enums/{elem}/{prop}`), no
  inventado (W-046G2R).
- **GET de verificación tras cada PUT/POST.** La columna "Contrario" del listado de la UI no
  refleja cambios de apellidos (solo `nombre`) — solo la API es fuente fiable (W-046G2R).
  Mitigación práctica: mete el nombre completo en el propio campo `nombre`, redundante con
  los apellidos separados pero es el único campo que el listado renderiza.
- **`[APER-15]` La doc puede ir por detrás del código** → verificar contra
  `core/sudespacho_relations.py` (`ensure_*`, `link_*`); **grep del código > doc**.
- **`[APER-16]` / `[APER-33]` Estado de PR/merge por `gh`, no por la rama local.**
- **`[APER-51]` / W-02ZIIF — `referencia_propia`/`NIG` NO son el número de autos.**
  `referencia_propia` = referencia interna del despacho; `NIG` = identificador del
  juicio asignado por el juzgado; el número de autos/procedimiento (p. ej. "550/2026")
  va en el flujo de Juzgado del punto 7 de arriba (campo `Auto` de `autos`) — no lo
  metas en notas ni en ninguno de esos dos campos por defecto.
- **`[APER-52]` / W-02ZIIF — Ojo con homónimos entre roles.** Si el mismo nombre aparece
  como tercero en un documento operativo (p. ej. comprador en una oferta) y también como
  remitente/CC en correspondencia interna de E&V, NO asumas que es la misma persona ni que
  son distintas — confirma antes de dar de alta nada a ese nombre como contrario o
  colaborador.
- **`[APER-53]` / W-02ZIIF — Existe (sin confirmar en vivo) `POST /api/expedient/convert/{id}`**
  para convertir un expediente extrajudicial existente en judicial (§6.2 de
  `INTEGRACION_SUDESPACHO.md`). Relevante cuando un caso escala de reclamación a demanda y
  YA tiene ficha extrajudicial viva — evitaría crear un judicial desconectado del
  histórico. **No usar sin probarlo primero contra un expediente desechable**: payload y
  respuesta sin confirmar todavía.

---

## 10. Archivo del expediente (si es inviable) — W-046G2R

Todo REST `x-api-key`. No se borra nada.

1. **CRM:** `update_expediente(exp_id, {"historico": True, "referencia_historico":
   "<MOTIVO_MAYUSCULAS_GUION_BAJO>", "fecha_alta_hist": "<AAAA-MM-DD>"})` — PUT parcial que
   preserva el resto. Nombres REST `historico`/`referencia_historico` verificados en vivo
   2026-07-18 (mismo patrón para `fecha_alta_hist`); ya no hacen falta los `campo_855/868/852`
   legacy. *(Enum cerrado de motivos: pendiente — `MEJORAS #70.c`.)*
2. **Actuación facturable** de cierre (§15).
3. **Gmail:** mover la etiqueta con `rename_label` a
   `03. ARCHIVO/01. ARCHIVO - EXTRAJUDICIALES/<año>/<caso>` (o `02. ... JUDICIALES/` si es
   judicial) + color; conserva los hilos, no re-etiqueta.
4. **Drive:** mover la carpeta a `CASOS/_ARCHIVO/01. EXTRAJUDICIALES/<año>/` (scaffolding
   ya existe).
5. **`_caso.md`:** `estado: archivado` + motivo + fecha en **dos niveles** del frontmatter
   (raíz y `meta`).
6. **Evento forense:** registrar el archivo con
   `intake_log.append_event(case_id, "archivado", details={"motivo": ..., "fecha": ...})`.
   El evento `archivado` **ya está** en `INTAKE_EVENTS` de `core/intake_log.py` (B4, PR-1 de
   `[SIGUIENTE-APERTURA-EXPEDIENTE]`; `MEJORAS #70.a`) → ya no se escribe la línea a mano.

---

## 11. Cierre de sesión + git

- **`[APER-30]` Numeración del "cierre" en `STATUS.md`:** `grep` del último `(Nº cierre` en
  **`origin/main`** ANTES de numerar (colisionó dos veces con la sesión paralela). No fiarse
  del `STATUS.md` local.
- **`[APER-31]` Rama de cierre SIEMPRE por W-code** (`docs/cierre-sesion-w0XXXXX`), nunca
  alias de proyecto/dirección — aunque ese alias sea normal *dentro* del caso.
- **`[APER-32]` `git push --force-with-lease`, `git reset --hard`, `git branch -D` están
  BLOQUEADOS** por el sistema de permisos. Para reincorporar `main` a una rama de PR ya
  publicada: **merge commit + push fast-forward** (no rebase+force):
  1. `git checkout -b tmp-merge <commit-ya-publicado>`
  2. `git merge origin/main --no-edit` → resolver conflicto → `git commit`
  3. `git push origin tmp-merge:<rama-remota-del-PR>` (fast-forward)
  4. `git checkout -B <rama-local> origin/<rama-remota>`; borrar `tmp-merge`.
- Cierre estándar: `python -m scripts.session_close` (slash `/cierre`).

---

## Referencias

- **Detalle API CRM (SSOT):** `docs/INTEGRACION_SUDESPACHO.md` §10 (relaciones), §12
  (judicial + archivo + Juzgado/§12.5), §15 (actuaciones), §11 (tags/colores), §14.4 (enums).
- **Callejones sin salida:** `docs/DEAD_ENDS.md` (worktree vs. raíz; lectura de relaciones REST).
- **Handoffs fuente:** `docs/superpowers/handoffs/handoff-2026-07-17-apertura-W-{02T3XO,02TH0W,046G2R}-mejoras-proceso.md`.
- **Builds de este flujo (`PLAN.md [SIGUIENTE-APERTURA-EXPEDIENTE]`):** B1 ficha CRM
  end-to-end (`scripts/crm_ficha.py` + `_ficha_crm.yaml`), B2 `--case-id`, B3 normalización de
  móvil, B4 evento `archivado`, B5 auto-derivación de `--team-id`/`--codigo-caso`/`--sufijo`
  desde `--folder-id` (`[APER-34]`, §3) — **todos en `main`**. El bloque B1–B5 está completo.
- **Memorias (aperturas W-02T3XO/W-02TH0W/W-046G2R/W-02VUDR):**
  `feedback-case-sufijo-tipo-canonico`, `feedback-crm-fichas-mayusculas`,
  `reference-sudespacho-crm-cableado-expediente`, `reference-sudespacho-archivo-actuaciones`,
  `reference-gmail-etiquetas-organizacion`, `feedback-worktree-vs-raiz-compartida`,
  `feedback-orden-intake-antes-sala-maquina`, `feedback-intake-email-exclusiones`,
  `feedback-concurrencia-pipelines-y-tiempos-apertura`,
  `feedback-eficiencia-herramientas-windows-drive`.
- **Memorias (apertura EN LOCAL de W-02ZIIF, 2026-07-22):**
  `feedback-mecanica-antes-analisis`, `feedback-crm-alta-al-final-no-durante-intake`,
  `reference-lexnet-pdf-layout-roto`, `feedback-verificar-antes-de-depositar-intake`,
  `feedback-taxonomia-roi-casos-pequenos`, `project-apertura-local-vs-drive`.
