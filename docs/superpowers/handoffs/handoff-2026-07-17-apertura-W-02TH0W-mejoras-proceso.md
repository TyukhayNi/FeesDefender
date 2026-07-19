---
tipo: handoff
estado: historico
consumido_por: "RUNBOOK_APERTURA_EXPEDIENTE.md"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# Handoff — Mejoras de proceso de APERTURA DE EXPEDIENTE (2/3)

**Fuente:** sesión de apertura E2E del caso **W-02TH0W** (equipo VaRS3, tipo NEGATIVA_OFERTA), 2026-07-17.
**Para:** sesión dedicada que consolida los 3 handoffs de las 3 aperturas de hoy.
**Objetivo:** cristalizar la experiencia para que las próximas aperturas vayan más rápido y con menos errores.

> Etiquetas `[APER-xx]` continúan la numeración del handoff de **W-02T3XO** (que ocupa `[APER-01]`–`[APER-18]`
> y `[APER-BUILD] 1-5`). Este empieza en `[APER-19]` para no colisionar al fusionar.
> Alcance distintivo de esta sesión (lo que el otro handoff NO cubre): **actuación facturable en CRM**,
> **3 fixes de código ya mergeados**, **reglas nuevas de viabilidad-prerelleno**, **generación de burofax
> desde plantilla (fallida, no dead end)** y **gotchas del cierre de sesión + git**.

---

## 1. RUNBOOK — deltas y confirmaciones sobre el handoff de W-02T3XO

**Confirmo su §1 íntegro** (entorno sandbox OFF, recon en paralelo, identidad auto-derivable, orden del
pipeline). Añado/corrijo:

- `[APER-19]` **El bug del `id_go` YA ESTÁ ARREGLADO (PR #54, en `main`).** `scripts/abrir_caso.py` ahora
  persiste el W-code en `meta.id_go` → `case_locator.resolve_ref(w_code)` encuentra el caso. Antes, el
  intake de email se desviaba a una carpeta nueva `CASOS\W-XXXXXX` en vez de la real. **Las sesiones
  futuras ya no tropiezan con esto.**
- `[APER-20]` **`ensure_case` corre ANTES del corte de `--dry-run`.** Por eso un dry-run seguido de la
  ejecución real "colisiona contra sí mismo" y exige `--force`. **Es comportamiento esperado, no un
  error** — forzar es seguro cuando es el mismo caso contra su propio esqueleto recién creado.
- `[APER-21]` **Sala de máquina — ficheros de Drive sin extensión usable YA se auto-detectan (PR #55).**
  Antes iban a `sin_soporte` (p. ej. nombre sin punto, o `"... jpg"` con la extensión escrita como
  palabra). Ahora `core/sala_maquina.py` husmea la extensión por **firma de bytes** (magic bytes: PDF,
  JPEG, PNG, GIF, BMP) cuando el nombre no la trae. Si aún ves `sin_soporte`, es que es un formato
  genuinamente desconocido, no un fallo de nombre.
- `[APER-22]` **Sala de lectura — la subcarpeta con fecha es POR DISEÑO, no un bug.** Solo los `.eml`
  con adjuntos MIME (documentos compuestos) generan subcarpeta datada; el resto es plano. No reinvestigar
  (perdí un turno confirmándolo; era confusión con la carpeta de OTRO caso).

---

## 2. CRM — ACTUACIÓN FACTURABLE (área nueva, el otro handoff no la toca)  `[APER-23]`

Todo **REST con `x-api-key`, sin PHPSESSID**. Documentado en `docs/INTEGRACION_SUDESPACHO.md` **§15**
(mergeado, PR #58). Flujo de 3 pasos:

1. **Descubrir esquema de campos** (si hace falta): `GET /api/view/config/actuaciones/fields` → nombre +
   tipo de cada campo. (Atajo genérico sin HAR, sirve para cualquier elemento.)
2. **Crear:** `POST /api/element_register/actuaciones` con body:
   - `Subject` (TextArea — **PII: sin topónimo, ver [APER-31]**), `Description` (TextAreaLong),
     `duracion` (Cronometro; acepta `"HH:MM:SS"` al crear, se guarda como **segundos totales**),
     `Estado` (`"Planificado"|"Hecho"`), `facturar` (bool), `tipo_actuacion` (`"Llamada"|"Tarea"`),
     `tipo_facturacion` (p. ej. `"duracion"`), `profesional_asignado` (**username** tipo
     `"Nikolai_Tyukhay"`, NO id), `Prioridad` (`"Alta"|"Media"|"Baja"` — la UI la exige), `fecha_alta`.
   - Respuesta: `201 {"id": N, "message": "Created!"}`.
3. **Vincular al expediente — PASO SEPARADO Y OBLIGATORIO:**
   `POST /api/relation_element/extrajudiciales/{exp_id}` body `["right.actuaciones.{id}"]` → 201.

**Gotchas de actuaciones (etiquetados):**
- `[APER-24]` **`relatedElement`/`relatedId` en el payload de creación NO vinculan** — se ignoran en
  silencio (devuelve 201 igual, pero la pestaña Historial→Actuaciones sale vacía). Corregía una memoria
  que tenía este dato MAL (`reference-sudespacho-archivo-actuaciones`, ya corregida). Vincular siempre por
  `relation_element` (paso 3).
- `[APER-25]` **Tarifa (`precio_hora` / checkbox "Facturar por duración" / botón "Aplicar tarifa usuario")
  = SOLO por UI, sin API confirmada.** Vive en el panel lateral que se abre con
  `item-to-preview={id}` sobre `Historial?relation-section=Actuaciones`. Al guardar por UI **hay que fijar
  `Prioridad`** o el "Actualizar" falla en silencio (error rojo "introduce un valor" bajo el campo vacío).
- `[APER-26]` **`PUT` es reemplazo completo; `PATCH` → 405.** Para editar un solo campo: `GET` todos los
  valores → reenviar todos por `PUT /api/element_register/actuaciones/{id}` cambiando solo el que toca. (Así
  quité un topónimo del `Subject` sin perder el resto.)
- `[APER-27]` **Catálogo `Predefined`/`PredefinedDetail` (plantillas de actuación tipo "SENIOR -
  EXTRAJUDICIAL") — descubrimiento INCONCLUSO, NO dead end** (por decisión explícita de Nikolai). Intentos
  ya hechos que NO repetir: `GET /api/predefined/{slug}` → 500 (el controlador espera id numérico, no
  slug); `POST /api/list/actuaciones/id_predefinido` → 500 (`Undefined array key "label"`, body exacto sin
  descubrir). Reintentar por otra vía, no por estas dos.

---

## 3. Viabilidad-prerelleno — reglas nuevas YA en la skill (PR #56)  `[APER-28]`

No hay que renegociarlas en cada apertura; ya están en `.claude/skills/viabilidad-prerelleno/`:
- **Regla de oro 8 (vía de lectura):** preferir `01_Procesado/02_Sala de máquina/03_MD/<slug>.md` cuando
  existe y su `_cobertura.md` es `ok`; caer al crudo (`00_Input`) si es `low`/`empty` o no hay MD. Anotar
  en la cita qué capa se usó (`[doc: x, vía MD]` vs `[doc: x, crudo]`) para campos que alimentan hito/importe.
- **Regla de oro 4 ampliada (hitos de existencia `[E]`):** para los 10 hitos cuya pregunta ES "¿existe este
  documento?" (ENCARGO, IDENT_PROPIETARIO, TITULARIDAD, HOJA_VISITA, OFERTA, IDENT_BUSCADOR,
  ARRAS_ARRENDAMIENTO, RECON_HON_ARRAS, RECON_HON_ESCRITURA, ESCRITURA), la **ausencia total** de referencia
  en `00_Input` → puntúa **`0`, no `pendiente`** (la ausencia ES la respuesta). Los otros 4 (CUANTÍA,
  RECLAMACION_JURIDICO, RESPUESTA_RECLAMACION, OFERTA_VINCULANTE_CONFIDENCIAL) siguen en `pendiente` por
  defecto (dependen de hechos que pueden ocurrir sin quedar documentados).

---

## 4. Generación de burofax desde plantilla del Gestor Documental — FALLIDA, NO dead end  `[APER-29]`

- Objetivo: generar el requerimiento (`BUROFAX _ ENGEL _ NEGATIVA ...`) desde plantilla → `.rtf` en el
  gestor documental → PDF → envío a la deudora por correo certificado + burofax + email vía **codicert.es**.
- **No se pudo capturar la llamada** con Claude-in-Chrome (2 intentos). Hipótesis: el flujo abre un popup
  efímero que salta a un handoff `ms-word:` (fuera de cualquier pestaña rastreable) y Word guarda de vuelta
  al CRM por **WebDAV**, no por una petición de pestaña de navegador.
- **NO documentar como dead end** (Nikolai: "es capturable, ya lo descubriremos").
- **Próximo intento — la única vía no probada:** capturar con **proxy a nivel de sistema** (mitmproxy /
  Fiddler), no con MCP de navegador. Si el salto es WebDAV/`ms-word:`, solo un proxy de SO lo ve.

---

## 5. Cierre de sesión + git — gotchas de proceso  `[APER-30]`

- `[APER-30]` **Numeración de "cierre" en `STATUS.md`: grep del último `(Nº cierre` en `origin/main` ANTES
  de numerar.** Colisionó DOS veces este día con la sesión paralela (dos "10º cierre") → tuve que renumerar
  a posteriori a "11º" y resolver conflicto de merge. No fiarse del `STATUS.md` local.
- `[APER-31]` **PII en el nombre de rama git.** La rama de cierre nació como `docs/cierre-sesion-<alias>-<topónimo>`
  → fuga (el contenido estaba limpio, solo el nombre filtraba). **Regla: ramas de cierre SIEMPRE por W-code**
  (`docs/cierre-sesion-w0XXXXX`), nunca alias de proyecto/dirección — aunque ese alias sea normal DENTRO del
  caso (carpeta Drive, `Referencia_Cliente`, `case_id`). Mismo cuidado en campos libres del CRM (`Subject`).
- `[APER-32]` **`git push --force-with-lease` está BLOQUEADO por el sistema de permisos** (aun con aprobación
  en chat). Si una rama de PR ya publicada necesita reincorporar `main`: **merge commit + push fast-forward**,
  no rebase+force. Receta que funcionó:
  1. `git checkout -b tmp-merge <commit-ya-publicado>` (no destructivo).
  2. `git merge origin/main --no-edit` → resolver conflicto → `git commit`.
  3. `git push origin tmp-merge:<rama-remota-del-PR>` (fast-forward, sin `--force`).
  4. `git checkout -B <rama-local> origin/<rama-remota>` para realinear; borrar `tmp-merge`.
- `[APER-33]` **Estado de PR/merge por `gh`, no por la rama local** (confirmo el `[APER-16]` del otro handoff).
  Además: `git reset --hard` y `git branch -D`/force-push también los bloquea el sistema de permisos → usar
  siempre alternativas no destructivas (`checkout -b`/`checkout -B`).

---

## 6. A CONSTRUIR — refuerza y amplía el `[APER-BUILD]` del otro handoff  `[APER-BUILD-VaRS3]`

- **REFUERZO de su `[APER-BUILD] 1` (abrir_caso end-to-end de CRM) — confirmado como el mayor cuello de
  botella también aquí.** Hoy `scripts/abrir_caso.py` **no llama a NINGUNA función de
  `core/sudespacho_relations.py`** (verificado): vincular EV MMC, colaboradores y contrario es 100% manual.
  **AMPLIAR el alcance del build para incluir el contrario EXTRAJUDICIAL:** `ensure_contrario_vinculado(...)`
  (PR #53, ya en código) — el vínculo `clientes_contrarios`↔`extrajudiciales` vía `relation_element`
  genérico quedó **confirmado en vivo esta sesión** (antes solo en judicial).
- **NUEVO: helper `crear_actuacion_facturable(exp_id, subject, description, duracion, ...)`** en
  `core/sudespacho_relations.py` — encadena el `POST element_register/actuaciones` + el `relation_element`
  (paso 3 de §2) en una sola llamada, con los campos ya conocidos. La tarifa se sigue aplicando por UI
  (`[APER-25]`). Hoy la actuación se montó artesanalmente turno a turno.
- **NUEVO: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`** — coincide con la propuesta §6 del otro handoff; unificar
  ambos. Es la única laguna documental real: NO existe hoy ningún runbook/checklist de apertura en `docs/`
  (verificado contra `docs/INDICE.md`).

---

## 7. Artefactos ya producidos en esta sesión (no rehacer)

- **PRs MERGEADOS (todos en `main`):** **#53** (crear+vincular contrario extrajudicial,
  `core/sudespacho_relations.py` + `INTEGRACION §10.6/10.7`), **#54** (fix `id_go`), **#55** (sniff de
  extensión en sala de máquina), **#56** (reglas 4/8 de viabilidad-prerelleno), **#58** (`INTEGRACION §15`
  endpoints de actuaciones), **#62** (cierre s11 en `STATUS.md`).
- **Memoria persistente:** `reference-sudespacho-archivo-actuaciones` (corregida: `relatedElement`/`relatedId`
  NO vincula → `relation_element`; `duracion` HH:MM:SS→segundos; tarifa solo-UI); `feedback-descubrimiento-
  crm-sin-log-forense` (nueva: descubrir API sin log forense; no marcar dead end sin confirmación de Nikolai).
- **Caso W-02TH0W:** abierto E2E; CRM extrajudicial **exp 624** (cliente EV MMC + 3 colaboradores +
  contrario vinculados); email intake + sala de máquina + sala de lectura + informe de viabilidad
  prerellenado (14 hitos, 1 aviso alto: sin confirmar envío del requerimiento → riesgo prescripción);
  **actuación facturable id 20862** creada, vinculada y tarificada (Hecho, 1h45m, tarifa aplicada por UI).
  Pendiente del caso (no de proceso): valorar VIABILIDAD (jurídico/finanzas — Skill B no construida); enviar
  el requerimiento cuando se resuelva `[APER-29]` o generándolo por UI.

---

## 8. Nota para la sesión consolidada

- Los 3 handoffs viven en `docs/superpowers/`, nombrados por W-code para no pisarse
  (`...-W-02T3XO-...`, `...-W-02TH0W-...`, + el 3º). Fusionar por etiqueta `[APER-xx]`: rangos disjuntos
  (01-18 = W-02T3XO; 19-33 = W-02TH0W).
- **⚠️ El handoff de W-02T3XO contiene PII sin higienizar** (apellido real del contrario, nombres de
  colaboradores, direcciones). Estos ficheros están **untracked**; si se van a commitear, **scrubbar antes**
  (referenciar por W-code, no por nombre). Este handoff (W-02TH0W) ya está limpio.
