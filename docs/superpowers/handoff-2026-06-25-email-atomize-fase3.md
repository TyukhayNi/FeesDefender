# Handoff — Fase 3 del motor de atomización de correo (`core/email_atomize`)

> **Autocontenido para una sesión nueva (sin memoria de la conversación previa).**
> Arranca la **capa de caso** (identidades, vistas temáticas, entregas) sobre el motor de
> atomización de correo, cuyas Fases 1 (Capa A MIME) y 2 (Layer B inline) ya están completas y
> en `origin/main`.

Antes de empezar lee `CLAUDE.md`, `STATUS.md` y `PLAN.md` (raíz del repo). Entorno: **Windows +
PowerShell**, venv en `.venv`, **UTF-8 sin BOM**, la lógica vive en `core/` (UI/CLI solo
orquesta), **NUNCA tocar `00_Input`** (crudo inmutable), pipeline idempotente. Responder en
castellano.

## Qué ya existe (Fases 1 y 2 COMPLETAS, en `origin/main`)

Módulo `core/email_atomize/` que lee `<caso>/00_Input/03_Email/*.eml` y produce en
`<caso>/01_Procesado/Emails/`:
- `mensajes/` — 1 `.md` por **mensaje atómico** (frontmatter YAML + cuerpo = solo lo que escribió
  el autor). Fuente de verdad.
- `adjuntos/` — binarios deduplicados por sha256 + ficha `.md` por adjunto único.
- `corpus.jsonl` — índice de máquina (1 línea/mensaje + meta no-editar).
- `_registro.json` — IDs **CONGELADOS** (`MSG-NNNNN` por Message-ID/fingerprint, `ATT-NNNNN` por
  sha256). **Re-ejecutar NUNCA renumera.**
- `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md` — vistas humanas.
- `_revision/{cola,casi_duplicados,del_burgo}.md` — cola de revisión de Layer B.

CLI: `python -m scripts.atomize_emails --ref W-02VND1` (o `--src <…/03_Email> --out <…/Emails>`).

- **Fase 1** = Capa A (MIME): mensaje principal + `message/rfc822` embebidos (byte-fiel, dedup
  por Message-ID). Reutiliza `core/email_export.py`.
- **Fase 2** = Layer B (reconstrucción de autoría **INLINE**): segmentación HTML (`html.parser`) +
  texto plano, atribución **solo desde cabecera contigua parseable** (ES/CA/EN), confianza
  `alta-reconstruida`/`media`/`baja` con guardas anti-misatribución, fingerprint **día-granular**,
  upgrade de fidelidad **sin tocar Capa A**, poda de huérfanos. **Directriz primaria: CERO
  MISATRIBUCIÓN** (ambigüedad / sin cabecera / sin fecha / identidad no confirmada → revisión,
  nunca alta).

Spec/plan de referencia:
- `docs/superpowers/specs/2026-06-24-email-atomize-design.md` (Fase 1)
- `docs/superpowers/specs/2026-06-25-email-atomize-layerb-design.md` (Fase 2, detallado; sintetizado
  por workflow adversarial)
- planes homónimos en `docs/superpowers/plans/`

**Caso piloto W-02VND1** = `BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta` (Barcelona). Ruta real:
`G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta`.
Estado tras Fase 2: 277 Capa A byte-idénticos + 89 Capa B `alta-reconstruida`; **PersonaUno = 12
directos (Capa A) + 13 inline PROMOVIDOS + 3 en revisión** (ver `_revision/del_burgo.md`). Fin
último del proyecto: recuperar la autoría enterrada de **PersonaUno** para levantar el velo
de Tibidabo 8 S.L.

## Objetivo de la Fase 3 (capa ESPECÍFICA del caso; el motor sigue genérico)

1. **`identidades.yaml` por caso.** Sacar de `core/email_atomize/inline.py` los sets hoy
   sembrados en código:
   - `IDENTIDADES_VIGILADAS = {per01a@example.invalid, per01c@example.invalid}` (confirmadas de PersonaUno).
   - `IDENTIDADES_CANDIDATAS = {per01b@example.invalid}` (candidata → **tope `media`**, no se
     auto-promociona; decisión de Nikolai 2026-06-25).
   El motor lee el YAML del caso; **sin YAML = genérico** (sets vacíos, comportamiento actual).
   Incluir **UNIFICACIÓN de identidad** (vista de persona que agrupa `per01c@example.invalid` ↔
   `per01a@example.invalid` como un único "PersonaUno"). `ignacio@despacho-ab.example` =
   **parte relacionada (su despacho), PERSONA DISTINTA**: nunca fundir con PersonaUno.

2. **Vistas temáticas.** `dossier_del_burgo` (todo lo de autoría/relacionado con PersonaUno, orden
   cronológico, con `Ref. MSG-NNNNN` y portador) y `vista_nexo_causal`. Dirigidas por `etiquetas`
   (campo ya presente en el frontmatter/corpus) + `identidades.yaml`.

3. **`_entregas/`.** Snapshot sellado de entrega (copia + hash; acción manual documentada en la
   skill/CLI).

4. **(Opcional)** subir recall: extracción de niveles profundos / más formatos de fecha.

5. **(Posterior)** OCR de adjuntos.

## Reglas duras que NO se rompen (verificar tras cada cambio)

- Los **277 `.md` de Capa A** deben quedar **BYTE-IDÉNTICOS** (comparar hashes antes/después).
- **IDs congelados** en `_registro.json`: nunca renumerar.
- **Cero misatribución**: un remitente se afirma solo desde cabecera verificada.
- El **motor es genérico**; lo del caso entra SOLO por config (`identidades.yaml`), no hardcodeado.

## Cómo trabajar (igual que Fases 1-2)

brainstorming → spec (`docs/superpowers/specs/`) → plan (`docs/superpowers/plans/`) → **TDD**
(test→fail→impl→pass→commit por tarea) → **verificación EN VIVO** sobre W-02VND1 + **REVISIÓN
ADVERSARIAL de código** (workflow). **Lección dura de la Fase 2:** un bug solo visible sobre los
datos reales (parser de fechas que se quedaba en el día de la semana) enmascaró el payoff (14
alta/0 PersonaUno → 89/13 tras el fix). **Verifica SIEMPRE sobre los 277 reales y con revisión
adversarial, no solo con fixtures sintéticos.**

## Gotchas de entorno

- **Suite:** `python -m pytest -q --tb=no --ignore=tests/test_email_export_mcp_server.py
  --ignore=tests/test_expedientes_xl_server.py` (faltan deps `mcp` en `.venv` → esos 2 ficheros
  fallan colección; son pre-existentes ajenos). En PowerShell pytest **no expande globs**: pasa
  rutas explícitas o usa `-k`.
- **Sandbox/guard sobre `G:`:** un guard da **falso positivo** (`"Remove-Item on system path"`) en
  comandos que mezclen `G:\` con `Remove-Item` o con here-strings largos → **separa comandos**; usa
  `dangerouslyDisableSandbox` solo para operaciones de **solo lectura** sobre `G:`
  (`Get-FileHash`/`Get-Content`); para commits con cuerpo largo usa `git commit -F fichero`.
- **Working tree COMPARTIDO** con otras sesiones: commits **acotados a ficheros propios** (sin
  `git add -A`); `PLAN.md`/`CLAUDE.md` traen cambios ajenos sin commitear (**no los commitees**).
  Hay un **post-commit hook que auto-pushea `main`**.

## Primer paso sugerido

Leer el spec de Fase 2 y `core/email_atomize/inline.py` (los sets `IDENTIDADES_VIGILADAS` /
`IDENTIDADES_CANDIDATAS` y dónde se consultan: `reconstruir` y `render.render_revision`), luego
**brainstorming** para cerrar el diseño de `identidades.yaml` (esquema, ubicación: ¿en la raíz del
caso?, carga, unificación de persona) y de las vistas temáticas **antes de codificar**.
