---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-18
---

# RUNBOOK — Apertura de expediente (FeesDefender)

> **Fuente única operativa** del flujo de apertura E2E de un expediente de honorarios de
> Engel & Völkers: alta → intake multi-fuente → sala de máquina → sala de lectura →
> viabilidad → ficha CRM completa → (si procede) archivo → cierre.
>
> Consolida los 3 handoffs de las aperturas del 2026-07-17 (W-02T3XO, W-02TH0W, W-046G2R;
> en `docs/superpowers/handoff-2026-07-17-apertura-W-*.md`). Las etiquetas `[APER-xx]`
> remiten al hallazgo original.
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

---

## 3. Etiqueta Gmail (primero — es reversible) `[APER-06]`

Nombre de la etiqueta *leaf* = `Referencia_Cliente` del CRM = nombre de la carpeta del caso
en Drive (**mismo string exacto** en las 3 superficies).

Taxonomía por cuenta (distinta):
- **Cuenta EV** (`nikolai.tyukhay@engelvoelkers.com`):
  `01. CONTING/01. EXTRAJUD/<ciudad>/BaRS<N> - <dir> - (W-XXXXX) - <tipo>`.
- **`mails.repositorio`**: `01. EXTRAJUDICIAL/...`.

**Colores y mecánica (W-046G2R, medido sobre 226 etiquetas reales):**
- *leaf* de caso (activa o archivada): `{backgroundColor:"#4986e7", textColor:"#ffffff"}`.
  Carpeta de **ciudad** (nivel padre): verde `#16a765`. **No confundir nivel.**
- "Mover" una etiqueta = `labels().patch(id, {name:"<nuevo path>"})` — **conserva los
  hilos**, no re-etiqueta. Aplicar color = `labels().patch(id, {color:{...}})`.
- `list_labels` sobre miles de etiquetas excede tokens → volcar a fichero y `grep`.

Memoria `reference-gmail-etiquetas-organizacion`.

---

## 4. Alta + intake inicial `[APER-07]`

```powershell
python -m scripts.abrir_caso --w-code W-XXXXXX --ciudad Barcelona --tipo-caso VUELTA `
  --direccion "..." --folder-id <id> `
  --fuente drive_ev --crm api --cuantia <n> --yes --force
```

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

---

## 5. Intake incremental (fuentes adicionales)

Cada intake posterior resuelve la identidad desde `_caso.md` con **`--case-id <W-code o
case_id>`** (B2, PR-2) — no repitas los 6 flags de identidad:

```powershell
python -m scripts.abrir_caso --case-id W-XXXXXX --fuente manual --src <carpeta|.zip> --yes
python -m scripts.abrir_caso --case-id W-XXXXXX --fuente email --cuenta <gmail> --label <etiqueta> --yes
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

---

## 6. Sala de máquina `[APER-09]`

```powershell
python -m scripts.sala_maquina apply "<case_id>"   # background
```

- `plan` (preview) es instantáneo; **`apply` (OCR real) tarda minutos** aunque haya pocas
  decenas de documentos → siempre en **background** si son más de ~15 (W-046G2R).
- **`[APER-21]`** Ficheros de Drive sin extensión usable (nombre sin punto, o `"… jpg"`) ya
  se **auto-detectan por firma de bytes** (magic bytes, PR #55). Si aún ves `sin_soporte`,
  es un formato genuinamente desconocido, no un fallo de nombre.

---

## 7. Sala de lectura `[APER-10]` `[APER-22]`

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

**Checklist de la ficha:**
1. **Tags equipo (rojo) + ciudad (azul):** los pone **el alta** (`crm_payload` los deriva del
   `codigo` vía `tag_rojo_equipo` + `tag_azul_de_codigo`). Ya **no** hace falta un PUT posterior
   de tags. (Si alguna vez editas `tags`/`Notas` a mano, usa `update_expediente`, que preserva
   `Numero_Expediente`, §10.7.)
2. **Cliente propio EV:** `link_ev_mmc(exp_id, cliente_propio_id=…)` — id del `cliente_propio`
   del `_ficha_crm.yaml` (default EV MMC SPAIN `2`; ENGEL & VÖLKERS SPAIN `27`). `crm_ficha`
   aborta si el valor es desconocido (no linkea la entidad equivocada en silencio).
3. **Contrario:** `ensure_contrario_vinculado(...)` (dedup por NIF). El **deudor de
   honorarios es quien firmó el encargo**, no todo co-titular (W-046G2R, memoria
   `feedback-crm-fichas-mayusculas`).
4. **Colaboradores (TL + consultores):** `ensure_colaborador_vinculado(...)` (dedup email).
   **Ficha completa** (móvil + fijo) buscando la firma en su correo `@engelvoelkers.com`;
   si ya existe → `GET → merge → PUT` para no pisar.
5. **Nota/hechos inicial:** `update_expediente(exp_id, {"Notas": …})` con el narrativo (tipo +
   partes + cláusula + cuantía). `notas_html` en el `_ficha_crm.yaml`.
6. **(Si procede) Actuación facturable:** `POST element_register/actuaciones` **+ vincular
   aparte** con `relation_element` (§15.2/15.3). `duracion` en `HH:MM:SS` → segundos;
   `Prioridad` obligatoria; **tarifa solo por UI** (§15.4).

**Gotchas CRM (deduplicados):**
- **`[APER-13]` No es PHPSESSID:** alta, vínculos, contrario/colaboradores y actuaciones van
  por **REST `x-api-key`**. `check-legacy` (PHPSESSID) es otra vía; no mirarla para esto.
- **`[APER-14]` Móvil en 9 dígitos** (`6XXXXXXXX`): la API rechaza `+34`/espacios
  (`HTTP 400 movil is incorrect`). Si un escritor REST falla, cae al fallback legacy y pide
  cookie = **falsa pista** → arreglar el móvil (§8 gotcha).
- **`[APER-24]` `relatedElement`/`relatedId` en el POST de creación NO vinculan** — se
  ignoran en silencio (201 igual, pero la pestaña queda vacía). Vincular **siempre** por
  `relation_element` (§15.2).
- **`[APER-26]` PUT (no PATCH → 405) y es PARCIAL: preserva los campos omitidos**
  (verificado en vivo 2026-07-18, §10.7). Para editar un campo, `update_expediente(exp_id,
  {campo: valor})` envía **solo** ese campo — NO hace falta reenviar todo ni preservar
  `Numero_Expediente` a mano. El GET-detalle sí exige `?properties=` (el GET plano da HTTP 500).
- **MAYÚSCULAS** en las fichas (excepto email). Los `Select` (provincia, nacionalidad,
  tipo_doc) usan el **valor literal del enum** (`GET /api/view/enums/{elem}/{prop}`), no
  inventado (W-046G2R).
- **GET de verificación tras cada PUT/POST.** La columna "Contrario" del listado de la UI no
  refleja cambios de apellidos (solo `nombre`) — solo la API es fuente fiable (W-046G2R).
- **`[APER-15]` La doc puede ir por detrás del código** → verificar contra
  `core/sudespacho_relations.py` (`ensure_*`, `link_*`); **grep del código > doc**.
- **`[APER-16]` / `[APER-33]` Estado de PR/merge por `gh`, no por la rama local.**

---

## 10. Archivo del expediente (si es inviable) — W-046G2R

Todo REST `x-api-key`. No se borra nada.

1. **CRM:** `update_expediente(exp_id, {"historico": True, "referencia_historico":
   "<MOTIVO_MAYUSCULAS_GUION_BAJO>", "fecha_alta_hist": "<AAAA-MM-DD>"})` — PUT parcial que
   preserva el resto. Nombres REST `historico`/`referencia_historico` verificados en vivo
   2026-07-18 (mismo patrón para `fecha_alta_hist`); ya no hacen falta los `campo_855/868/852`
   legacy. *(Enum cerrado de motivos: pendiente — `MEJORAS #70.c`.)*
2. **Actuación facturable** de cierre (§15).
3. **Gmail:** mover la etiqueta a `03. ARCHIVO/01. ARCHIVO - EXTRAJUDICIALES/<año>/<caso>`
   (o `02. ... JUDICIALES/` si es judicial) + color; `labels.patch` conserva los hilos.
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
  (judicial + archivo), §15 (actuaciones), §11 (tags/colores), §14.4 (enums).
- **Callejones sin salida:** `docs/DEAD_ENDS.md` (worktree vs. raíz; lectura de relaciones REST).
- **Handoffs fuente:** `docs/superpowers/handoff-2026-07-17-apertura-W-{02T3XO,02TH0W,046G2R}-mejoras-proceso.md`.
- **Builds de este flujo (`PLAN.md [SIGUIENTE-APERTURA-EXPEDIENTE]`):** B1 ficha CRM
  end-to-end (`scripts/crm_ficha.py` + `_ficha_crm.yaml`), B2 `--case-id`, B3 normalización de
  móvil, B4 evento `archivado`, B5 auto-derivación de `--team-id`/`--codigo-caso`/`--sufijo`
  desde `--folder-id` (`[APER-34]`, §4) — **todos en `main`**. El bloque B1–B5 está completo.
- **Memorias:** `feedback-case-sufijo-tipo-canonico`, `feedback-crm-fichas-mayusculas`,
  `reference-sudespacho-crm-cableado-expediente`, `reference-sudespacho-archivo-actuaciones`,
  `reference-gmail-etiquetas-organizacion`, `feedback-worktree-vs-raiz-compartida`.
