---
tipo: handoff
estado: historico
consumido_por: "RUNBOOK_APERTURA_EXPEDIENTE.md"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# Handoff — Mejoras de proceso de APERTURA DE EXPEDIENTE
**Fuente:** sesión de apertura E2E del caso **W-02T3XO** (BaRS3 - [dirección] - Vuelta), 2026-07-17.
**Para:** sesión dedicada que consolida los 3 handoffs de las 3 aperturas de hoy.
**Objetivo:** cristalizar la experiencia para que las próximas aperturas vayan más rápido y con menos errores.

> Cada mejora lleva una **etiqueta `[APER-xx]`** para deduplicar/fusionar entre los 3 handoffs.
> Alcance de esta sesión: correos + Drive + sala de máquina + sala de lectura + CRM + pre-relleno de
> viabilidad + envío de email desde el CRM (con descubrimiento de su API por HAR).

---

## 1. RUNBOOK rápido (orden + comandos exactos)

**Entorno**
- `[APER-01]` **Ejecuta todo desde el repo principal, sandbox OFF.** El worktree no tiene `.venv`,
  `.env`, `CASOS_ROOT` ni PHPSESSID → el pipeline no corre ahí. Descubrirlo a mitad cuesta tiempo.
  Prefijo: `Set-Location "C:\Users\tnm33\Dev\FeesDefender"` + `.venv\Scripts\python.exe`. `G:` y los
  tokens de Google/Gmail (en `~`) sí son accesibles.
- `[APER-02]` **Recon en paralelo antes de preguntar:** con el hilo Gmail + carpeta Drive, lanzar a
  la vez `list_accounts` (Gmail+Drive), `get_folder_path`+`get_file_metadata` de la carpeta, y leer
  el hilo. Sale caso, partes e importe en 2 tandas.

**Identidad (auto-derivar, no preguntar)**
- `[APER-03]` **Código de equipo `BaRS<N>` = nombre de la unidad compartida del Drive** (`"Barcelona
  - S3"` -> BaRS3). `list_shared_drives` + `driveId` de la carpeta. NO preguntar.
- `[APER-04]` **Sufijo = tipo_caso CANÓNICO** (`VUELTA` -> `"Vuelta"`), nunca paráfrasis. Ofrecer
  "Venta directa a cliente" obligó a renombrar carpeta G:, `_caso.md`, etiqueta Gmail y referencia
  CRM. (En memoria `feedback-case-sufijo-tipo-canonico`.)
- `[APER-05]` **`--tipo-caso` se deduce del hilo** (vuelta/negativa/bad debt/...). De las 4 preguntas
  de apertura, 3 (equipo, sufijo, tipo) son auto-derivables; la única real es el **alcance**
  (¿uno o varios asuntos en el hilo?).

**Pipeline**
- `[APER-06]` Etiqueta Gmail primero (reversible). En la **cuenta EV** la taxonomía es
  `01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS<N> - <dir> - (W-XXXXX) - <tipo>` (distinta de la de
  `mails.repositorio`: `01. EXTRAJUDICIAL/...`).
- `[APER-07]` Alta + intake:
  `python -m scripts.abrir_caso --w-code W-XXXXXX --ciudad Barcelona --tipo-caso VUELTA
  --codigo-caso BaRS3 --sufijo "Vuelta" --direccion "..." --folder-id <id> --team-id <driveId>
  --fuente drive_ev --crm api --cuantia <n> --yes --force`
  - `--yes` desde el principio (el prompt "el código BaRS3 ya existe" es esperado; sin él se cuelga en background).
  - `--force` si el W-code ya existe (2a pasada de intake).
  - En `drive_ev`, `--dry-run` NO ahorra (igual hace el pull real).
- `[APER-08]` Export de correos (reentrante):
  `... --fuente email --cuenta nikolai.tyukhay@engelvoelkers.com --label "<etiqueta EV>" --force`.
- `[APER-09]` Sala de máquina: `python -m scripts.sala_maquina apply "<case_id>"` (background; OCR).
- `[APER-10]` **Sala de lectura — secuencia COMPLETA:** `catalogo -> clasificar -> [rellenar
  worklist] -> aplicar -> POBLAR -> render`. **`render` solo escribe índices; `poblar` es el que
  copia los documentos.** Mejor: comando `organizar` (todo-en-uno). (Olvidé `poblar` y la sala salió
  vacía.)
- `[APER-11]` Viabilidad: skill `viabilidad-prerelleno` (lee `00_Input`, genera `.xlsx`).

---

## 2. CRM — la ficha COMPLETA es una CHECKLIST, no solo el alta  `[APER-12]`

**`abrir_caso --crm api` hace SOLO el alta mínima** (referencia, cuantía, tags de *tipo*, posición).
Falta —y va aparte, todo **REST con `x-api-key`, sin PHPSESSID**—:

1. **Tags dependientes del caso** (el alta NO los pone): ciudad (`Barcelona` azul `#5b9bd1___296`) +
   equipo (`BaRS3` rojo `#a32929___128`). **PUT de reemplazo completo**
   `PUT /api/element_register/extrajudiciales/{id}`: **preservar `Numero_Expediente`** o se pierde;
   `tags` = cadena `,95,286,296,128,` (concatenar al valor actual, no reemplazar).
2. **Cliente propio EV:** `link_ev_mmc(exp_id)` (id 2).
3. **Contrario (deudor = firmante del encargo):** `ensure_contrario_vinculado(exp_id,
   NuevoClienteContrario(nombre, apellido1, apellido2, nif, movil, direccion, poblacion))` (dedup NIF).
4. **Colaboradores (TL + consultores):** `ensure_colaborador_vinculado(...)` (dedup email).
   **Completar ficha entera** (móvil + fijo) buscando la firma en su correo `@engelvoelkers.com`; si
   existe -> GET->merge->PUT para no pisar. (En memoria `feedback-crm-fichas-mayusculas`.)
5. **Nota/hechos inicial:** PUT `Notas` con el narrativo (tipo + partes + cláusula + cuantía).

**Gotchas CRM (etiquetados):**
- `[APER-13]` **NO es PHPSESSID:** alta, vínculos y creación de contrario/colaboradores van por
  **REST x-api-key**. `check-legacy` (PHPSESSID) es otra vía; no mirarla para esto.
- `[APER-14]` **Móvil en 9 dígitos** (`6XXXXXXXX`): la API rechaza `+34`/espacios (`HTTP 400 movil is
  incorrect`). Si un colaborador REST falla, cae al fallback legacy y pide cookie = **falsa pista**
  -> arreglar el móvil.
- `[APER-15]` **La doc puede ir por detrás del código:** verificar contra `core/sudespacho_relations.py`
  (funciones `ensure_*`, PR #53); `INTEGRACION §7` estaba desfasada. Grep del código > doc.
- `[APER-16]` **Estado de PR/merge por `gh`, no por la rama local** (confundir "checkout local en
  rama feat" con "PR sin mergear").

---

## 3. Correo/adjuntos y captura de API (secundario)

- `[APER-17]` Los adjuntos incrustados en un `.eml` (p. ej. capturas WhatsApp) **NO se extraen** en el
  intake (`export_label` con `extract_attachments=False`; `abrir_caso` no expone el flag). Se extraen
  con `python -m scripts.atomize_emails --ref ...` (motor aparte, manual). Si la prueba SOLO viene por
  correo (sin copia en Drive), hay que lanzar atomize. (`MEJORAS #68`.)
- `[APER-18]` Descubrir API por navegador: capturar en **pestaña controlada por Claude-in-Chrome**
  (grupo MCP), no en la del usuario; clics por **`find`/ref** (no coordenadas: screenshot 1568 vs
  página 1920); cuerpos de red enormes -> volcar a fichero y parsear con python filtrando url/método
  y excluyendo `data:`; para **payloads** usar **HAR de DevTools** (el HAR **nunca al repo**: expone
  credenciales SMTP/IMAP en claro vía `GET /api/accounts/{id}`).

---

## 4. A CONSTRUIR (promover a PLAN.md) — mayor ahorro primero  `[APER-BUILD]`

1. **`abrir_caso` end-to-end de CRM:** que el alta orqueste la **ficha completa** (tags ciudad+equipo
   auto desde `--ciudad`/`--codigo-caso`, `link_ev_mmc`, contrario con datos del encargo,
   colaboradores con datos de firmas, `Notas`). Hoy son 5-6 llamadas manuales. **Incluye** un
   `update_expediente` (PUT round-trip que preserva `Numero_Expediente`) que hoy no existe.  <- EL QUE MÁS AHORRA
2. **Auto-derivación de identidad** en `abrir_caso --fuente drive_ev`: deducir `--team-id`,
   `--codigo-caso` (nombre de la unidad compartida) y `--sufijo` (del `tipo_caso`) desde `--folder-id`.
   Elimina 3 flags y 3 preguntas.
3. **Normalizador de teléfono** (9 dígitos) en los escritores de CRM: mata el 400 del móvil de raíz.
4. **Sala de lectura:** arreglar los 3 defectos del CLI deprecado (`MEJORAS #67`: ruta MD, colisión
   de nombres, no-plano) o estandarizar en la skill canónica + usar siempre `organizar`.
5. **Cablear `atomize` + OCR de adjuntos** en el flujo (`MEJORAS #68`).

---

## 5. Artefactos ya producidos en esta sesión (no rehacer)

- **PRs MERGEADOS:** FeesDefender **#60** (docs API envío email `INTEGRACION §10.9` + puntero
  `ARQUITECTURA_CRM §3.9` + spec MCP F3+ + `MEJORAS #67/#68/#69`); ElContable **#5** (referencia común
  agnóstica §7). Descubrimiento del envío de email desde el CRM registrado en las 4 fuentes de verdad
  de FeesDefender + la común de ElContable.
- **Memoria persistente creada/actualizada:** `feedback-case-sufijo-tipo-canonico`,
  `reference-sudespacho-enviar-email-crm` (flujo completo del envío), `feedback-crm-fichas-mayusculas`
  (colaboradores completos), `reference-sudespacho-crm-cableado-expediente` (extrajudicial REST +
  gotcha móvil + PUT update).
- **Caso W-02T3XO:** abierto; ficha CRM (exp 625) completa (tags, EV, contrario (W-02T3XO),
  colaboradores (TL + consultores) con contacto, nota); email enviado a colaboradores desde el CRM.
  Pendiente del caso (no de proceso): **nota simple actual** (viabilidad) + **entrevista** (congelada).

---

## 6. Propuesta de cristalización (decidir en la sesión consolidada)

- **`docs/RUNBOOK_APERTURA_EXPEDIENTE.md`** = fuente única operativa (secciones 1 y 2 de este handoff).
- **Skill Claude Code `abrir-caso`** que ejecute el runbook con los gotchas embebidos.
- Promover `[APER-BUILD]` 1-5 a `PLAN.md` (empezar por el 1: alta CRM completa).
