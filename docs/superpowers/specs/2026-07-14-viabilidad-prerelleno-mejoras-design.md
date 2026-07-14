# Diseño — Mejoras a la skill `viabilidad-prerelleno` (fricción BaRS8)

- **Fecha:** 2026-07-14
- **Rama:** `claude/viabilidad-prerelleno-review-5cb695`
- **Origen:** revisión crítica de `Propuesta_mejoras_viabilidad-prerelleno.md`, anclada al código y a los `SKILL.md` reales.
- **Estado:** diseño aprobado (pendiente de plan de implementación).

## Contexto

Al pre-rellenar el Informe de Viabilidad de BaRS8 (W-02XOR7) con la skill
`viabilidad-prerelleno` surgió una propuesta de mejoras en tres partes: (A) un fix
técnico en `render_informe.py`, (B) seis mejoras de texto a la skill, y (C) una tabla
de aplicabilidad cruzada a otras skills del despacho. La revisión contra el código real
confirmó el bug (A), validó las seis mejoras (B) con ajustes, y **refutó la mayor parte
de la tabla (C)**: ninguna otra skill comparte el patrón `shutil.copy(plantilla, salida)`,
varias ya son conscientes del límite shell/Drive, y `verificacion-anclada-fuente` es
mal hogar para centralizar reglas por su altitud (skill portable AGPL, sin concepto de
layout de expediente).

El brainstitng posterior aplicó dos filtros: **YAGNI** (recortar C a lo demostrado) y
un **principio arquitectónico** — *lógica al código; detalle a `references/` (carga bajo
demanda); el `SKILL.md`, que se carga siempre, solo recibe ediciones tersas con
crecimiento neto ≈ 0*.

## Objetivos

1. Eliminar el `PermissionError` latente del render, de forma robusta y con test.
2. Incorporar las mejoras metodológicas de B en su hogar correcto (código / `SKILL.md`
   / `references/`), sin engordar el prompt base ni contradecir reglas existentes.
3. Propagar a otras skills **solo** lo que tiene necesidad demostrada; el resto al backlog
   bajo la regla de promoción del `CLAUDE.md` ("solo por necesidad demostrada").

## Alcance

### Dentro (PR 1) — `viabilidad-prerelleno`

**Código — `scripts/render_informe.py`:**
- Línea 106: `shutil.copy(args.plantilla, salida)` → `shutil.copyfile(...)`. `copyfile`
  no copia el modo de fichero, así que la salida nace escribible y desaparece la causa
  raíz del bug (el asset read-only ya no contamina la copia). `os` sigue importado
  (línea 24); no hace falta import nuevo.
- Antes del copy: `os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)`
  para cerrar el otro modo de fallo (directorio `02_Analisis` inexistente).
- **B2 en código:** envolver `wb.save(salida)` (línea 205) en `try/except OSError`;
  en el fallo, reescribir en un directorio local de trabajo e imprimir un aviso con la
  ruta del fallback y la instrucción de copiarlo a `02_Analisis`. Hace la entrega
  robusta sin depender de que el LLM lea prosa.

**Texto — `SKILL.md` (ediciones tersas):**
- **B1:** nota en "Ficheros de la skill" (líneas 127-133): el render fuerza permiso de
  escritura sobre la copia porque el asset puede venir read-only en el entorno
  empaquetado. Redactada según el fix `copyfile` (sin afirmar "intencionalmente
  read-only", que no es hecho del repo — Git no versiona ese atributo).
- **B2 prosa:** una línea en el paso 7 (líneas 82-89) apuntando al conector
  `expedientes-xl` (`write_file_base64`/`copy_path`, para binarios) cuando esté
  disponible. Nota: es `expedientes-xl`, no el MCP `expedientes` de solo-texto.
- **B3:** reescribir el paso 1 (líneas 52-53) y la mención de la línea 24 como
  **aceleración de lectura, no de cita**: si existe `01_Procesado/02_Sala de máquina/`,
  usar los espejos MD para leer/localizar rápido, pero **anclar la CITA al documento
  original** (el MD conserva el nombre del fichero fuente); bajar al OCR/crudo para
  verbatim delicado, firmas o autenticidad. Con guarda explícita "si no existe la sala
  de máquina, leer `00_Input` directo". Preserva la Regla de oro #1 (traza a fuente).
- **B4:** corregir la cláusula de §3 (línea 69, "*o es `clase_fuente: testifical` → deja
  vacía*"), que hoy se lee como absoluta. Nueva redacción: `clase_fuente` es un DEFAULT,
  no una prohibición; si un documento resuelve una pregunta marcada testifical con cita
  literal, se rellena igual que una documental. **No** se toca el yaml generado
  (`references/cuestionario_viabilidad.yaml`, GENERADO — se regenera desde el canónico);
  la regla de razonamiento vive en `SKILL.md`.
- **B6:** sub-paso terso de conciliación dentro del paso 1 (no "paso 0"): antes de
  derivar hitos, buscar si ya existe un informe/documento de viabilidad previo; si
  existe, comparar y volcar discrepancias (cifras, fechas, puntuaciones) a `AVISOS LLM`,
  sin sobrescribir en silencio. Enlaza con la línea 56 (que ya reconoce que puede existir
  un informe previo). Fue el origen del aviso de mayor severidad en BaRS8.

**Texto — `references/hitos_derivacion.md` (carga bajo demanda):**
- **B5 (invertido):** párrafo junto a las "Reglas de oro del scoring" que clarifica la
  precedencia en la dirección **correcta**: el `0` de cierre de un hito solo aplica
  cuando consta que la acción se intentó o el documento existe; a falta de todo rastro,
  sigue rigiendo `pendiente` (Regla de oro #4, conservador). Se ancla al ejemplo HOJA DE
  VISITA. NO se adopta la redacción original de la propuesta ("manda la regla específica
  del hito"), que invertía el salvaguarda y generaba ceros espurios.

**Testing — `tests/`** (hoy no existe test para el script):
- Caso 1: plantilla marcada read-only → el render no revienta y produce el `.xlsx`.
- Caso 2: directorio de salida no escribible → cae al fallback local e imprime la ruta.
- Suite completa (`python -m pytest -q --tb=no`) verde antes de empaquetar.

**Cierre PR 1:** `python scripts/package_skill.py viabilidad-prerelleno` → re-importar el
`.skill` en Cowork. Actualizar `PLAN.md` y `docs/MEJORAS_FUTURAS.md`.

### Dentro (PR 2) — cross-skill mínimo

- **C6 (conciliación) en `triaje-viabilidad` únicamente** — la de gancho más claro (ya
  usa `INDICE.md` como pista de navegación, líneas 52-53). Sub-paso terso "revisa si ya
  hay triaje/informe previo antes de emitir el veredicto". Empaquetar + PR.

### Fuera (backlog — `MEJORAS_FUTURAS.md`)

Con etiqueta "propagar cuando un caso real lo dispare" (regla de promoción del `CLAUDE.md`):
- **C2** (entrega sin-shell) en `triaje-viabilidad`, `preparacion-audiencia-previa` y demás.
- **C6** en `escritos-judiciales` y `organizar-sala-lectura`.
- **C3** cascada MD→OCR en otras skills que leen `00_Input`; **C4** precedencia
  documental/testifical fuera de viabilidad.
- **Centralización en `verificacion-anclada-fuente` (C3/C4): descartada** — mala altitud,
  tensiona con la Regla 9 (verbatim), sin herencia automática entre skills.
- **Instancia latente del bug de permisos** en la skill bundled `docx`
  (`scripts/comment.py:236,254,273,282`: `shutil.copy(TEMPLATE_DIR/*.xml, dest)` + escritura
  posterior). Skill de terceros, fuera del mantenimiento del despacho; fix defensivo
  (`copyfile`/`chmod`) solo si se vendoriza.

## Decisiones de diseño (y por qué)

- **`copyfile` sobre `chmod`:** ataca la raíz (no copiar el modo) en vez de compensarla;
  cambio de una palabra, sin línea extra.
- **B2 en código + una línea de prosa:** el script detecta el fallo de escritura de forma
  fiable; la prosa solo orienta hacia el conector cuando aplica. Robustez + mínimo bloat.
- **B3 separa lectura de cita:** conserva la ganancia de velocidad en casos grandes sin
  romper la traza source-locked (no citar un derivado OCR).
- **B5 invertido:** la redacción original de la propuesta era incorrecta (invertía el
  principio conservador); se adopta el sentido correcto, ya coherente con
  `hitos_derivacion.md:8`.
- **C recortado a C6-en-triaje:** aplica la regla de promoción del `CLAUDE.md` — no
  propagar por completitud de diseño, solo por necesidad demostrada.

## Criterios de éxito

- El render produce el `.xlsx` aunque el asset sea read-only o el directorio de salida no
  exista, con test que lo demuestra.
- Ninguna edición de `SKILL.md` contradice una regla preexistente; crecimiento neto del
  prompt base ≈ 0.
- El yaml generado no se edita a mano.
- Suite pytest verde; skill re-empaquetada; `PLAN.md`/`MEJORAS_FUTURAS.md` al día.

## Riesgos y mitigaciones

- **No puedo confirmar el read-only del asset desde el repo** (Git no versiona el
  atributo). Mitigación: el fix es defensivo y correcto exista o no el permiso; el test
  fuerza el read-only para reproducir.
- **B3 presupone la sala de máquina:** mitigado por la guarda "si existe … si no,
  `00_Input` directo".
- **Bloat cross-skill:** mitigado recortando C a una sola skill y empujando detalle a
  `references/`.
