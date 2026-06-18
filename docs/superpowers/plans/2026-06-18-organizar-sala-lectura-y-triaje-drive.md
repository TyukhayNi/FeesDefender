# Sala de lectura por prompt + triaje de viabilidad — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear dos skills de Cowork — `organizar-sala-lectura` (ordena el intake desordenado del Drive del despacho en `02_Sala lectura/` por taxonomía E&V) y `triaje-viabilidad` (check básico de viabilidad sobre la sala ya organizada) — para que cualquier abogado del despacho las use sin instalar nada.

**Architecture:** Skills en prosa (no código `core/`). Corren en claude.ai/Cowork con el conector de Drive; el modelo lee/clasifica el contenido y copia ficheros vía el conector, y escribe el `.docx` del triaje vía la skill `docx`. Sin OCR local, sin scripts Python, sin módulo OPERACIÓN. Se autoran en `.claude/skills/` (fuente única), se validan con `scripts/validate_skills.py` y se empaquetan con `scripts/package_skill.py`.

**Tech Stack:** Markdown (SKILL.md + references), frontmatter YAML de dos ejes (`_plantilla-skill`), conector de Drive (copy/create), skill `docx`. Spec: `docs/superpowers/specs/2026-06-18-organizacion-sala-lectura-drive-triaje-design.md`.

**Nota de verificación:** estas son skills (prompts), no código. No hay pytest. La "prueba" de cada skill es (a) `python scripts/validate_skills.py` en modo aviso (conformidad de frontmatter), y (b) una **eval manual** documentada sobre una carpeta sintética sin PII. Cada tarea de autoría incluye el contenido concreto a escribir, no un placeholder.

**Decisiones cerradas (del spec):** no destructivo (copia); taxonomía y nombres canónicos del motor local; manifiesto por caso; registro global aparcado. **Decisión abierta para resolver en Task 2:** ¿el conector de Drive mueve o solo copia? (afecta a si `01_Raw` se llena moviendo o el crudo se queda donde está). Recomendación transversal: construir `02_Sala lectura` por copia siempre.

---

## File Structure

**Skill 1 — `organizar-sala-lectura` (núcleo + identidad; pura prompt):**
- Create: `.claude/skills/organizar-sala-lectura/SKILL.md` — procedimiento de organización.
- Create: `.claude/skills/organizar-sala-lectura/references/taxonomia_ev.md` — las 8 categorías E&V + keywords de desambiguación + reglas de nombre canónico.
- Create: `.claude/skills/organizar-sala-lectura/CHANGELOG.md`
- Create: `.claude/skills/organizar-sala-lectura/.gitignore`

**Skill 2 — `triaje-viabilidad` (núcleo + identidad; requires verificacion-anclada-fuente):**
- Create: `.claude/skills/triaje-viabilidad/SKILL.md` — procedimiento del triaje + semáforo.
- Create: `.claude/skills/triaje-viabilidad/references/criterios_triaje.md` — factores de viabilidad de honorarios de mediación + reglas del semáforo.
- Create: `.claude/skills/triaje-viabilidad/CHANGELOG.md`
- Create: `.claude/skills/triaje-viabilidad/.gitignore`

**Eval (no se empaqueta):**
- Create: `docs/superpowers/evals/2026-06-18-organizar-sala-lectura-eval.md` — resultado de la eval manual.

Cada `SKILL.md` debe quedar por debajo de 500 líneas; el detalle va a `references/` (progressive disclosure), como en `pase-de-estilo`.

---

## Task 1: Scaffold `organizar-sala-lectura` + frontmatter

**Files:**
- Create: `.claude/skills/organizar-sala-lectura/SKILL.md`
- Create: `.claude/skills/organizar-sala-lectura/CHANGELOG.md`
- Create: `.claude/skills/organizar-sala-lectura/.gitignore`

- [ ] **Step 1: Copiar la plantilla**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender"
cp -r .claude/skills/_shared/_plantilla-skill .claude/skills/organizar-sala-lectura
rm .claude/skills/organizar-sala-lectura/_LEEME.md
```

- [ ] **Step 2: Escribir el frontmatter de `SKILL.md`**

Reemplaza el bloque frontmatter por exactamente esto:

```yaml
---
name: organizar-sala-lectura
description: >-
  Organiza una carpeta de intake desordenada del Drive del despacho en una "sala
  de lectura" legible: clasifica cada fichero en las carpetas canónicas de Engel &
  Völkers (activación, ofertas, arras, facturación, PBC, reclamaciones, fotos),
  los copia con nombre canónico fecha_tipo_descripcion a 02_Sala lectura/ dejando
  el crudo intacto en 01_Raw/, y genera INDICE.md, CRONOLOGIA.md y un manifiesto.
  Úsala cuando el usuario diga "organiza esta carpeta", "ordena el intake", "monta
  la sala de lectura", "prepara los ficheros para leer" sobre una carpeta de Drive
  de un caso. NO valora viabilidad (eso es triaje-viabilidad) NI genera el informe
  formal (eso es viabilidad-prerelleno) NI mueve/borra el crudo.
metadata:
  rol: output
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---
```

- [ ] **Step 3: Vaciar el `CHANGELOG.md` a la entrada inicial**

```markdown
# Changelog — organizar-sala-lectura

## 1.0 — 2026-06-18
- Versión inicial. Organización por copia de intake de Drive a 02_Sala lectura/
  con taxonomía E&V, nombres canónicos, INDICE/CRONOLOGIA/manifiesto. No destructivo.
```

- [ ] **Step 4: Confirmar `.gitignore`**

El `.gitignore` heredado de la plantilla excluye telemetría; déjalo tal cual.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/organizar-sala-lectura
git commit -m "feat(skill): scaffold organizar-sala-lectura (frontmatter + changelog)"
```

---

## Task 2: Cuerpo de `SKILL.md` de `organizar-sala-lectura`

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md`

- [ ] **Step 1: Escribir el cuerpo** (debajo del frontmatter), con estas secciones y este contenido exacto de reglas:

**`## Cuándo se activa`**
- Disparadores: «organiza esta carpeta», «ordena el intake», «monta la sala de lectura», «prepara los ficheros para leer», «esta carpeta de Drive está hecha un lío».
- NO se activa: para valorar viabilidad (`triaje-viabilidad`), para el informe formal (`viabilidad-prerelleno`), ni para tocar el expediente local de FeesDefender (eso es el motor `core/`, Claude Code).

**`## Entrada`**
- El usuario indica la **carpeta del caso en el Drive del despacho**. Confirmar que es del Drive del despacho (no el de Engel) antes de tocar nada.

**`## Qué produce`** (estructura exacta):
```
<Carpeta del caso>/
├── 01_Raw/                      ← crudo, nombres originales, NO se toca
└── 02_Sala lectura/
    ├── INDICE.md · CRONOLOGIA.md · _MANIFIESTO.md
    └── <carpetas canónicas E&V>/  (ver references/taxonomia_ev.md)
```

**`## Procedimiento`** (pasos, defaults claros):
1. Listar el contenido de la carpeta con el conector de Drive. Si el crudo está suelto en la raíz, tratarlo como `01_Raw` (ver Gotcha "mover vs copiar").
2. Para cada fichero: leer el contenido (vía conector), decidir **tipo** (una de las 8 categorías de `references/taxonomia_ev.md`; lo ambiguo → `08. PENDIENTE`, nunca forzar) y **fecha** (del contenido; subsidiariamente del nombre; si nada, `0000-00-00`).
3. **Copiar** (no mover) cada fichero a `02_Sala lectura/<tipo>/` con nombre canónico `AAAA-MM-DD_tipo_descripcion.ext` (reglas en `references/taxonomia_ev.md`). La `descripcion` es un slug ≤50 car. **sin PII** (ni nombres, ni DNI, ni direcciones).
4. Escribir `INDICE.md` (agrupado por tipo, cada entrada: enlace + nombre original ↔ canónico), `CRONOLOGIA.md` (por fecha ascendente, s/f al final) y `_MANIFIESTO.md` (tabla: original · canónico · tipo · fecha · checksum-si-disponible). Los tres con cabecera `<!-- GENERADO — NO EDITAR A MANO -->`.
5. Reportar al usuario: nº por categoría, nº a `08. PENDIENTE`, duplicados detectados.

**`## Idempotencia`**
- Si `02_Sala lectura/` ya existe, no re-duplicar: comparar por nombre canónico (y checksum si el conector lo expone) y saltar lo ya copiado; reportar qué se saltó.

**`## Gotchas`**
- **Mover vs copiar:** el conector de Drive puede no soportar mover (reparent). Default seguro: **construir `02_Sala lectura` por copia** y dejar el crudo donde está (o en `01_Raw` si se puede mover sin duplicar). Nunca borrar el crudo.
- **Sin PII en nombres:** el delator más fácil; revisar la `descripcion` antes de copiar.
- **No es el motor local:** esta skill no toca `00_Input` ni `01_Procesado` del expediente FeesDefender; opera solo sobre la carpeta de Drive indicada.

- [ ] **Step 2: Verificar longitud**

Run: `wc -l .claude/skills/organizar-sala-lectura/SKILL.md`
Expected: < 500 líneas.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/SKILL.md
git commit -m "feat(skill): cuerpo de organizar-sala-lectura (procedimiento + gotchas)"
```

---

## Task 3: `references/taxonomia_ev.md` de `organizar-sala-lectura`

**Files:**
- Create: `.claude/skills/organizar-sala-lectura/references/taxonomia_ev.md`

- [ ] **Step 1: Escribir el fichero** con este contenido exacto:

```markdown
# Taxonomía E&V + reglas de nombre canónico

## Las 8 categorías (carpetas de 02_Sala lectura/)

Set cerrado (igual que `TAXONOMIA_EV` del motor local). El clasificador debe
devolver EXACTAMENTE una:

- `00. FOTOS` — imágenes (.jpg .jpeg .png .heic .webp .gif .bmp .tiff).
- `01. ACTIVACIÓN` — encargo, captación, exclusiva, exposé, hoja de visita.
- `03. OFERTAS` — oferta, contraoferta.
- `04. ARRAS - ARRENDAMIENTOS` — arras, reserva, señal, arrendamiento, alquiler.
- `05. FACTURACIÓN - FINANZAS` — factura, honorarios, abono, minuta, justificante de pago.
- `06. PBC` — DNI, NIE, pasaporte, nota simple, titularidad, prevención de blanqueo.
- `07. RECLAMACIONES` — burofax, requerimiento, reclamación, incumplimiento.
- `08. PENDIENTE` — todo lo ambiguo o ilegible. NUNCA forzar a otra categoría.

(No existe `02`; se respeta la numeración de E&V.)

## Cómo clasificar

1. Si es imagen por extensión → `00. FOTOS`.
2. Si el contenido o el nombre casan claramente con los keywords de arriba → esa categoría.
3. En duda → `08. PENDIENTE`. Es preferible un pendiente honesto a un misrouting.

## Nombre canónico

`AAAA-MM-DD_tipo_descripcion.ext`

- `tipo` (slug): foto · activacion · oferta · arras · factura · pbc · reclamacion · pendiente.
- `descripcion`: slug ≤50 car., minúsculas, guiones, **SIN PII** (sin nombres de
  personas, DNI/NIE, direcciones). Describe el documento, no a las partes
  (p. ej. `hoja-encargo`, `burofax`, `factura-honorarios`).
- `AAAA-MM-DD`: fecha del documento; si no consta, `0000-00-00`.

Ejemplos: `2024-03-12_activacion_hoja-encargo.pdf`, `2024-05-02_reclamacion_burofax.pdf`.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/references/taxonomia_ev.md
git commit -m "feat(skill): taxonomia_ev de organizar-sala-lectura"
```

---

## Task 4: Validar y empaquetar `organizar-sala-lectura`

**Files:** (ninguno nuevo)

- [ ] **Step 1: Validar conformidad de frontmatter**

Run: `python scripts/validate_skills.py`
Expected: sin no-conformidades para `organizar-sala-lectura` (o solo avisos esperados; el script es modo aviso, no bloquea).

- [ ] **Step 2: Empaquetar el `.skill`**

Run: `python scripts/package_skill.py .claude/skills/organizar-sala-lectura`
Expected: genera el `.skill` en `dist/skills/` (gitignored).

- [ ] **Step 3: Commit** (solo si validate cambió algo; el `.skill` está gitignored)

```bash
git add -u .claude/skills/organizar-sala-lectura
git commit -m "chore(skill): organizar-sala-lectura conforme a validate_skills" || echo "nada que commitear"
```

---

## Task 5: Scaffold `triaje-viabilidad` + frontmatter

**Files:**
- Create: `.claude/skills/triaje-viabilidad/SKILL.md`
- Create: `.claude/skills/triaje-viabilidad/CHANGELOG.md`
- Create: `.claude/skills/triaje-viabilidad/.gitignore`

- [ ] **Step 1: Copiar la plantilla**

```bash
cd "C:\Users\tnm33\Dev\FeesDefender"
cp -r .claude/skills/_shared/_plantilla-skill .claude/skills/triaje-viabilidad
rm .claude/skills/triaje-viabilidad/_LEEME.md
```

- [ ] **Step 2: Escribir el frontmatter**

```yaml
---
name: triaje-viabilidad
description: >-
  Check BÁSICO de viabilidad de una reclamación de honorarios de mediación
  inmobiliaria (cliente Engel & Völkers), antes del análisis formal. Lee la sala
  de lectura ya organizada de un caso y devuelve un semáforo verde/amarillo/rojo
  con los factores nucleares (hoja de encargo firmada, nexo causal con la operación
  cerrada, obligado al pago, prueba de la intermediación, importe y base de cálculo,
  prescripción), anclando cada conclusión a documento y marcando lo que falta.
  Úsala cuando el usuario diga "haz un triaje de viabilidad", "¿este caso se
  aguanta?", "check rápido de viabilidad", "¿cogemos este caso?". NO sustituye el
  informe formal de viabilidad (viabilidad-prerelleno) NI organiza ficheros
  (organizar-sala-lectura).
metadata:
  rol: fase
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, mercantil, consumo]
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: [verificacion-anclada-fuente]
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---
```

- [ ] **Step 3: `CHANGELOG.md`**

```markdown
# Changelog — triaje-viabilidad

## 1.0 — 2026-06-18
- Versión inicial. Triaje semáforo de viabilidad de honorarios de mediación E&V
  sobre la sala de lectura organizada; source-locked; salida .docx interna.
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/triaje-viabilidad
git commit -m "feat(skill): scaffold triaje-viabilidad (frontmatter + changelog)"
```

---

## Task 6: Cuerpo de `SKILL.md` de `triaje-viabilidad`

**Files:**
- Modify: `.claude/skills/triaje-viabilidad/SKILL.md`

- [ ] **Step 1: Escribir el cuerpo** con estas secciones y reglas exactas:

**`## Cuándo se activa`** — «triaje de viabilidad», «¿se aguanta este caso?», «check rápido», «¿cogemos el caso?». NO: informe formal (`viabilidad-prerelleno`), organizar ficheros (`organizar-sala-lectura`).

**`## Entrada`** — la carpeta `02_Sala lectura/` ya organizada de un caso (si no existe, sugerir correr antes `organizar-sala-lectura`). Lee `INDICE.md`/`CRONOLOGIA.md` para orientarse y luego los documentos relevantes.

**`## Reglas de oro`** (innegociables, heredadas de `verificacion-anclada-fuente` y de la terminología del despacho):
1. **No inventar.** Cada conclusión se ancla a `[doc: <fichero>]` + cita. Lo no acreditado → "falta", no se infiere.
2. **Terminología:** propietario / buscador (nunca vendedor/comprador), aun cuando el documento diga otra cosa.
3. **Es un triaje, no el informe.** No puntúa hitos, no rellena el .xlsx, no decide por el letrado: orienta.

**`## Factores`** — remite a `references/criterios_triaje.md` (los 8 factores + nucleares vs accesorios).

**`## Procedimiento`**:
1. Detectar el tipo de caso (BAD_DEBT, NEGATIVA_*, VUELTA, etc. — ver `criterios_triaje.md`).
2. Para cada factor: buscar en la sala el documento que lo acredita; marcar **acreditado** (con cita), **débil** (existe pero con problema: firma sin cotejar, copia, ilegible) o **falta**.
3. Calcular el **semáforo** según las reglas de `criterios_triaje.md`.
4. Redactar el veredicto corto + **qué documentación pedir** para cerrar huecos.

**`## Qué produce`** — `_TRIAJE_VIABILIDAD.docx` (vía skill `docx`) guardado en la carpeta del caso del **Drive del despacho** (es work product interno; OK ahí porque E&V no accede al Drive del despacho). Contenido: semáforo, tabla factor·estado·cita/falta, veredicto, documentación a recabar.

**`## Gotchas`** — semáforo conservador: si falta un factor **nuclear**, es 🔴 aunque el resto esté. No rellenar el veredicto si la sala está casi vacía: decir que falta documentación para triar.

- [ ] **Step 2: Verificar longitud** — `wc -l` < 500.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/triaje-viabilidad/SKILL.md
git commit -m "feat(skill): cuerpo de triaje-viabilidad (procedimiento + reglas de oro)"
```

---

## Task 7: `references/criterios_triaje.md` de `triaje-viabilidad`

**Files:**
- Create: `.claude/skills/triaje-viabilidad/references/criterios_triaje.md`

- [ ] **Step 1: Escribir el fichero** con este contenido exacto:

```markdown
# Criterios de triaje — honorarios de mediación inmobiliaria (E&V)

Condensado del cuestionario de viabilidad (`viabilidad-prerelleno`) para un check
RÁPIDO. No sustituye el informe formal.

## Tipos de caso (orienta qué factores pesan)
Actores: BAD_DEBT, NEGATIVA_OFERTA, NEGATIVA_ARRAS, NEGATIVA_ESCRITURA,
NEGATIVA_CONTRATO_ARRENDAMIENTO, VUELTA, INCUMPLIMIENTO_EXCLUSIVA.
Defensivos: RESPONSABILIDAD_PROFESIONAL, DEVOLUCION_RESERVA, LAU_20, DEVOLUCION_HONORARIOS.

## Factores

NUCLEARES (si falta uno → 🔴):
1. **Encargo firmado** — hoja/nota de encargo con firma. En B2C, legibilidad y
   cláusulas conforme TRLGDCU (control de transparencia de la cláusula de honorarios).
2. **Nexo causal** — que la operación se cerró Y que se cerró por la intermediación
   (no por vía ajena que rompa el nexo; clave en VUELTA).
3. **Obligado al pago** — quién debe los honorarios según el encargo
   (propietario / buscador / tercero), identificado.

ACCESORIOS (refuerzan; su ausencia → 🟡, no 🔴):
4. **Prueba de la intermediación** — exposé, visitas, oferta, comunicaciones.
5. **Importe y base de cálculo** — % sobre precio o fórmula del encargo
   (arrendamiento: mensualidad o % sobre renta anual).
6. **Operación consumada** — escritura / arras firmadas, o frustración imputable
   al obligado.
7. **Prescripción** — acción de reclamación de cantidad: 5 años (art. 1964 CC).
   Marcar 🟡/🔴 si el plazo está vencido o al límite.
8. **Reclamación previa** — burofax/requerimiento ya enviado (útil, no esencial).

## Semáforo
- 🟢 **VIABLE (a triaje):** los 3 nucleares acreditados + sin banderas graves en accesorios.
- 🟡 **VIABLE CON RESERVAS:** nucleares acreditados pero con factor débil
  (firma sin cotejar, copia, accesorio ausente) o hueco subsanable pidiendo doc.
- 🔴 **DUDOSO / NO TRIABLE:** falta un nuclear, o prescripción vencida, o la sala
  no tiene material suficiente para opinar.

El semáforo es orientativo: la decisión de coger el caso es del letrado.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/triaje-viabilidad/references/criterios_triaje.md
git commit -m "feat(skill): criterios_triaje de triaje-viabilidad"
```

---

## Task 8: Validar y empaquetar `triaje-viabilidad`

- [ ] **Step 1: Validar** — `python scripts/validate_skills.py` (sin no-conformidades nuevas).
- [ ] **Step 2: Empaquetar** — `python scripts/package_skill.py .claude/skills/triaje-viabilidad`.
- [ ] **Step 3: Commit** (si validate ajustó algo) — `git add -u .claude/skills/triaje-viabilidad && git commit -m "chore(skill): triaje-viabilidad conforme a validate_skills" || echo "nada"`.

---

## Task 9: Eval manual sobre carpeta sintética

**Files:**
- Create: `docs/superpowers/evals/2026-06-18-organizar-sala-lectura-eval.md`

- [ ] **Step 1: Preparar una carpeta sintética** (en Drive de pruebas o local), sin PII real: ~8-10 ficheros mezclados (un "encargo", una "factura", un "burofax", una "oferta", 2 fotos, un par ambiguos, un ilegible).

- [ ] **Step 2: Correr `organizar-sala-lectura`** sobre esa carpeta y comprobar:
  - Cada fichero cae en la categoría correcta (los ambiguos → `08. PENDIENTE`).
  - Nombres canónicos `AAAA-MM-DD_tipo_descripcion`, **sin PII**.
  - `INDICE.md` / `CRONOLOGIA.md` / `_MANIFIESTO.md` generados con cabecera "no editar".
  - El crudo intacto (no movido/borrado).
  - **Idempotencia:** segunda corrida no re-duplica.

- [ ] **Step 3: Correr `triaje-viabilidad`** sobre la `02_Sala lectura` resultante y comprobar:
  - Semáforo coherente con lo que hay (con material escaso → 🔴 "no triable", no inventa).
  - Cada factor anclado a documento o marcado "falta".
  - `_TRIAJE_VIABILIDAD.docx` generado.

- [ ] **Step 4: Documentar el resultado** en el fichero de eval (qué pasó, qué falló, ajustes hechos a las skills). Si algo falló, volver a la tarea de la skill correspondiente, corregir y re-evaluar.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/evals/2026-06-18-organizar-sala-lectura-eval.md
git commit -m "test(skill): eval manual de organizar-sala-lectura + triaje-viabilidad"
```

---

## Task 10: Cierre — gate de skills + re-import en servidor

- [ ] **Step 1: Pasar el gate de frescura/conformidad**

Run: `python scripts/check_skills.py`
Expected: sin avisos para las dos skills nuevas (CHANGELOG al día, `.skill` no caducado, identidad completa). Corregir lo que marque.

- [ ] **Step 2: Re-importar en el servidor** (manual, Cowork/claude.ai): subir los dos `.skill` de `dist/skills/`. La ejecución vive en el servidor; el repo es la fuente de autoría.

- [ ] **Step 3: Verificación de activación** (en claude.ai): comprobar que «organiza esta carpeta…» dispara `organizar-sala-lectura` y «¿este caso se aguanta?» dispara `triaje-viabilidad`, y que un falso amigo («redacta la demanda») NO las dispara.

- [ ] **Step 4: Commit de cierre** (acotado a las skills + eval; dejar intactos los cambios ajenos sin commitear del working tree)

```bash
git add .claude/skills/organizar-sala-lectura .claude/skills/triaje-viabilidad docs/superpowers
git commit -m "feat(skill): organizar-sala-lectura + triaje-viabilidad listas (v1.0, experimental)"
```

---

## Self-review (cubierto del spec)

- Spec §3 (estructura `01_Raw`/`02_Sala lectura` + carpetas canónicas) → Task 2 + Task 3.
- Spec §4 (skill organización, nomenclatura, índices, manifiesto, idempotencia) → Tasks 2-3.
- Spec §5 (skill triaje, factores, semáforo, .docx, source-locked) → Tasks 6-7.
- Spec §6 (mover vs copiar / dedup) → Task 2 Gotchas (decisión a fijar en eval, Task 9).
- Spec §7 (manifiesto por caso; global fuera) → Task 2 step 4 (manifiesto); global no se construye.
- Spec §8 (paridad con motor: taxonomía + nombres) → Task 3 (taxonomía idéntica al motor).
- Spec §9 (errores: ilegible, sin fecha, idempotencia, carpeta enorme) → Task 2 + Task 9.
- Spec §10 (pruebas = eval manual) → Task 9.
- Spec §11 (empaquetado/distribución) → Tasks 4, 8, 10.

---

## Seguimiento (post-v1.0, acordado 2026-06-18)

**Decisión: NO fusionar `triaje-viabilidad` con `viabilidad-prerelleno`.** Comparten
dominio pero son momentos distintos (pre-screen go/no-go vs prefill del informe
formal), con output y peso distintos. Es una secuencia, no un duplicado:
`triaje-viabilidad` → abrir expediente + organizar → `viabilidad-prerelleno` →
`informe-viabilidad-ev`. Fusionarlas rompería la atomicidad y metería la maquinaria
pesada (xlsx, 88 preguntas, scripts) en el pre-screen ligero de Cowork.

**Pero sí hay que resolver la duplicación de criterios** (fuente única, sin drift):
- [ ] Anclar `triaje-viabilidad/references/criterios_triaje.md` al cuestionario
  canónico `data/_plantillas/cuestionario_viabilidad.yaml` (vista **condensada
  generada**, no escrita a mano), igual que `viabilidad-prerelleno` genera su vista
  con `sync_cuestionario_from_canon.py`. Así los criterios no divergen entre skills.
- [ ] Dejar escrito el **encadenamiento triaje → prerelleno** en ambos `SKILL.md`
  (qué va antes, que no se solapan), para que el modelo no confunda cuándo usar cada una.

(05_Procedimiento — pendiente de la conversación previa: que el output del triaje
vaya a `05_Procedimiento/Triaje viabilidad/` con fallback a la raíz del caso si no
hay expediente. Sin cerrar el fallback (a) crear vs (b) raíz.)
```
