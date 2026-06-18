# HANDOFF — Unificar las DOS salas de lectura en UNA sola skill que la alimente

> Origen: hilo Claude Code FeesDefender, 2026-06-18. Decisión (tomada en otro hilo):
> juntar las dos "salas de lectura" existentes en una única skill. Este documento es
> autocontenido para arrancar el trabajo en un hilo nuevo en frío.

## 0) Reglas operativas (no romper)

- Fuente única de skills: `.claude/skills/` de este repo. Tras editar: empaquetar con
  `scripts/package_skill.py` y dejar nota para re-importar el `.skill` en el servidor
  (ejecución en Cowork/claude.ai). No tocar `despacho-skills` (deprecado).
- Validar con `scripts/validate_skills.py` (modo aviso) y `scripts/check_skills.py`.
- Concurrencia: working tree compartido en `main`. Commits ACOTADOS (nunca `add -A`);
  `PLAN.md` arrastra cambios ajenos sin commitear → no barrerlos; dejar `PLAN.md`/
  `STATUS.md` al día solo en el `/cierre`, acotando.
- Windows/PowerShell; UTF-8 sin BOM.

## 1) Qué son hoy las dos salas (lo que hay que unificar)

**A) MOTOR LOCAL — `core/sala_lectura.py`** (Python, corre en Claude Code local):
- Lee `00_Input`; clasifica con reglas deterministas por NOMBRE (`_categoria_por_nombre`)
  + residuo a worklist `01_Procesado/_revisar/_clasificar.md` que Claude-en-sesión
  rellena leyendo `01_Procesado/MD/` (excepción RGPD §2). MEJORAS #37 ya añadió
  `clasificar_residuo_llm` / `preparar_residuo` / `rellenar_worklist` +
  `make_llm_cloud_chat_fn` (Scaleway OPT-IN; default = Claude-en-sesión, sin API de pago).
- Copia a `01_Procesado/Sala lectura/<FUENTE>/` (por FUENTE), nombre canónico
  `_nombre_canonico` = `AAAA-MM-DD_tipo_descripcion.ext` (CON slug de tipo, `_TIPO_SLUG`).
- SSOT = `indice_documental.yaml` (`catalogo_documental.py`). Render `INDICE.md`
  (fuente→tipo) + `CRONOLOGIA.md` (fecha asc). Bundles CRM (`conjunto_detector`).
- Idempotente por sha256 + `ruta_sala_lectura`; SÍ borra copia vieja al re-ubicar
  (`old.unlink()`). Depende de Docling/OCR/inventory.

**B) SKILL PROMPT-DRIVEN — `.claude/skills/organizar-sala-lectura/`** (corre en
Cowork/Drive, SIN core/, sin Docling), versión actual **v1.2**:
- Lee `00_Input/01_Drive EV` (solo esa fuente; `04_Manual` y demás fuera de alcance).
- El MODELO clasifica leyendo el CONTENIDO (no por nombre). Taxonomía E&V canónica.
- Copia a `01_Procesado/Sala lectura Drive EV/<TIPO>/` (por TIPO), nombre
  `AAAA-MM-DD_descripcion.ext` (SIN slug: la carpeta ya dice el tipo).
- `_MANIFIESTO.md` con sha256 (calculado de los BYTES, no el md5 del conector) + ruta
  original; `INDICE.md` + `CRONOLOGIA.md`. Cabeceras "GENERADO — no editar".
- Gate humano ÚNICO (Paso 2.5): propuesta visual (artefacto HTML; fallback markdown)
  → espera OK → ejecuta de una pasada.
- Add-only: nunca borra; conserva clasificación previa por sha256; cambio de reglas
  = vaciado manual + recorrido limpio.

## 2) Decisiones de este hilo que la skill unificada DEBE preservar

- **SALIDA FUERA DE `00_Input`.** `inventory.scan` hace `rglob("*")` sobre TODO
  `00_Input` (`core/inventory.py:86`): cualquier cosa bajo `00_Input` se re-ingiere como
  intake (duplicados, re-OCR) y los re-pulls la pisan. La sala va a `01_Procesado/`.
- **Todos los registros del caso llavean por SHA-256, scope `00_Input`**
  (`_intake_hashes.json` M9, `_inventory.json`, `indice_documental.yaml`). El puente
  entre la sala y la traza del caso es el sha256 (el conector da md5 → calcular sha256 de
  los bytes). "Catálogo único" es la dirección ya elegida del proyecto (`PLAN.md`
  acoplamiento #2; `[SIGUIENTE-CATALOGO-DOCUMENTAL]`). **Actualización 2026-06-18
  (sesión concurrente, `45dd5ad`):** `build_catalog` **YA está cableado** en
  `core/pipeline.py` (tras `inventory.scan`, idempotente) + subcomando `catalogo` en
  `scripts/sala_lectura.py`; y #37 (residuo por Claude-en-sesión) validado sobre el
  caso real BaRS1/Tibidabo.
- **NO destructivo:** el crudo de `00_Input` NUNCA se toca ni se borra. Copia server-side.
- **TAXONOMÍA E&V canónica** = `core/config.py` `TAXONOMIA_EV` (8 cats, incl
  `08. PENDIENTE DE CLASIFICAR`). **PBC POR PARTE** (decidido sobre Tibidabo): identidad
  del VENDEDOR (nota mercantil, nota simple/titularidad, titular real, poderes, catastro)
  → `01. ACTIVACIÓN`; EXCEPCIÓN Anexos 1 y 2 del vendedor → `06. PBC` (la carpeta
  sobrevive SOLO para eso); identidad/KYC del COMPRADOR → `03. OFERTAS` (subcarpeta por
  oferta si hay varias). La parte se decide LEYENDO el documento.
- **Clasificación:** Claude-en-sesión por defecto (sin API de pago); Scaleway solo
  OPT-IN (futuro DPA). Lo ambiguo/ilegible → `08. PENDIENTE`; nunca forzar.
- **Gate humano ÚNICO + autonomía:** el diálogo de permiso por-llamada es ajuste del
  CLIENTE Cowork ("Permitir siempre"); la skill no lo suprime por código, pero hace que
  el usuario lo active UNA vez en Paso 0; tras el OK del gate, ejecuta todo sin más
  preguntas.
- **DRY de criterios pendiente:** la taxonomía de la skill debe GENERARSE del canónico
  (`core/config.py` + `core/sala_lectura.py`), como `sync_cuestionario_from_canon.py` en
  `viabilidad-prerelleno`; + gate anti-drift en `check_skills` (`sync_taxonomia_skills.py`).
  Hoy se corrigió a mano un drift real (`08. PENDIENTE` → `08. PENDIENTE DE CLASIFICAR`).

## 3) Cambios pendientes del último handoff Cowork (sobre Tibidabo W-02VND1) — incorporar

1. **ORDEN:** en el visor (Paso 2.5) e `INDICE.md`, por fecha DESCENDENTE; `CRONOLOGIA.md`
   se queda ascendente.
2. **FECHA DEL CUERPO:** jerarquía (a) otorgamiento/firma en el cuerpo → (b) otra fecha
   inequívoca del contenido → (c) nombre del fichero → (d) `0000-00-00`. mtime NO es
   fuente; si se usa como aprox., marcar `(*)` en `CRONOLOGIA` y `_MANIFIESTO`. Regresión
   real (leer cada doc, no por nombre): "PODERES JAIME.pdf"→`2023-01-17` (no 2024-10-04);
   "Poderes PersonaTres Feu" (TIBIDABO 8 S.L.U., notario Yllescas, nº4160)→`2024-11-21`
   (no 2025-02-14).
3. **PERMISO:** Paso 0 bloqueante → "Permitir siempre" en el conector de Drive; CERO
   diálogos durante la ejecución; gate único (2.5).
4. **CONECTOR + URL:** Paso 0 carga el conector de Drive (ToolSearch) y acepta URL de
   carpeta pegada en el chat. Resolver folderId y DETECTAR nivel: raíz del expediente →
   bajar a `00_Input/01_Drive EV`; o si la URL ya es `01_Drive EV` → usarla. Disparador
   "organiza esta carpeta <url>".
5. **DOBLE SALIDA (`01_Plano` + `02_Por categoria`): ANALIZADO en este hilo.** Pros: dos
   modos de lectura. Contras: bytes ×2 (el conector copia, no crea shortcuts); ambigüedad
   de índices; ROMPE la dedup por sha (mismo sha en dos rutas → "ya visto" saltaría la 2ª
   copia; habría que rehacer dedup a `(sha, subcarpeta)`); triaje tendría que fijar de cuál
   lee. **RECOMENDACIÓN DE ESTE HILO = opción A:** UN solo árbol físico (`02_Por categoria`,
   por tipo) + la vista plana como ÍNDICE (`INDICE_PLANO.md` con nombre-bundle
   `NN-categoria__AAAA-MM-DD__descripcion`), NO copias físicas → 0 bytes duplicados, dedup
   intacta. Copia física plana solo si hay necesidad real de export en bloque. **DECISIÓN
   ABIERTA:** A (recomendada) vs B (doble salida física con safeguards). Documentar en spec.

## 4) El trabajo del nuevo hilo: unificar en UNA sola skill

Objetivo: una única skill que alimente la sala de lectura, sirviendo tanto el caso local
(motor, multi-fuente, con Docling/catálogo) como el caso Cowork (Drive, una fuente, sin
core). **Tensiones a resolver (cerrarlas con Nikolai antes de implementar):**

- **T1. POR FUENTE (motor) vs POR TIPO (skill):** elegir una disposición física única, o
  definir cómo coexisten. Hoy NO colisionan por nombre de carpeta
  (`Sala lectura/<fuente>/` vs `Sala lectura Drive EV/<tipo>/`).
- **T2. SSOT:** catálogo `indice_documental.yaml` (motor) vs `_MANIFIESTO.md` (skill). La
  dirección del proyecto es catálogo único llaveado por sha256
  (`[SIGUIENTE-CATALOGO-DOCUMENTAL]`). Decidir si la skill unificada escribe/alimenta el
  catálogo o sigue con manifiesto + puente de reconciliación por sha256.
- **T3. CLASIFICADOR:** reglas-por-nombre+residuo (motor) vs modelo-lee-contenido (skill).
  Unificar el contrato de clasificación y la taxonomía (PBC por parte) en una sola fuente.
- **T4. RUNTIME:** el motor necesita core/Docling (local); la skill corre en Cowork sin
  core. "Una skill que la alimente" implica decidir si la skill orquesta el motor cuando
  hay entorno local, o si es puramente prompt y el motor queda como camino alterno.
- **T5. NAMING:** motor con slug (carpetas por fuente, el slug informa); skill sin slug
  (carpetas por tipo). Bajo disposición única, fijar uno.

Recomendación de partida (de este hilo): vía brainstorming→spec→plan (superpowers);
mantener Claude-en-sesión por defecto; sala fuera de `00_Input`; sha256 como llave;
opción A para la vista plana. NO empezar a codificar sin spec aprobado por Nikolai.

## 5) Estado / referencias

- **Commits 2026-06-18 en `main`:** `6cc20e7` (spec) · `71f5cab` (plan) · `20bc2f2`
  (2 skills v1.0) · `18d7287` (alcance+destino+fix 08) · `5ed9279` (manifiesto sha256) ·
  `ca35e09` (v1.1 PBC/gate/autonomía/enlaces) · `6b64bcc` (solo-añade) · `7c7a5de`
  (v1.2 sin slug).
- **Spec:** `docs/superpowers/specs/2026-06-18-organizacion-sala-lectura-drive-triaje-design.md`
- **Plan:** `docs/superpowers/plans/2026-06-18-organizar-sala-lectura-y-triaje-drive.md`
- **Skill organización:** `.claude/skills/organizar-sala-lectura/` (v1.2; `.skill` en `dist/skills/`).
- **Skill triaje:** `.claude/skills/triaje-viabilidad/` (v1.0) — DESFASADA: su "Entrada"
  aún apunta a `02_Sala lectura/`; debe leer la sala unificada. Output a
  `05_Procedimiento/Triaje viabilidad/` sin cerrar (fallback (a) crear vs (b) raíz). NO
  fusionar triaje con `viabilidad-prerelleno` (son secuencia, no duplicado).
- **Motor:** `core/sala_lectura.py` (con MEJORAS #37), `core/catalogo_documental.py`,
  `core/inventory.py` (rglob), `core/intake_manifest.py` (sha256, scope `00_Input`).
- **Memoria de proyecto:** `project-sala-lectura-prompt-driven.md`,
  `project-sala-lectura-01-procesado.md`.
- **Pendiente operativo:** re-importar `.skill` v1.2 en Cowork; reorganizar Tibidabo
  (vaciando antes la sala v1.0); alinear triaje; gate anti-drift de taxonomía.
