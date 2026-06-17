# Diseño — Sala de lectura `01_Procesado`: F4 (copiador+bundles) + F5 (índices) + F6 (clasificador híbrido)

> **Origen:** brainstorming Claude Code ↔ Nikolai, 2026-06-17. Continúa el plan
> fino `docs/PLAN_SALA_LECTURA_01_PROCESADO.md` (Fases 0–3 ya en `main`, commit
> `f253a84`). **Implementación:** Claude Code. **Frontera:** este spec cubre las
> Fases 4–6 del plan; Streamlit se adelanta parcialmente (botón disparador).

---

## 1. Objetivo

Completar la sala de lectura de `01_Procesado`: una capa humana donde el abogado
consulta el caso **en claro y en orden** (documentos con nombre limpio, agrupados
por fuente y en bundles cabecera+anexos), más índices navegables (`INDICE.md` por
fuente, `CRONOLOGIA.md` por fecha). Todo derivado del catálogo
`indice_documental.yaml`, que es la **única fuente de verdad documental**.

Las tres piezas están acopladas y se construyen juntas porque comparten el
catálogo:

- **F6 (clasificador/fechador híbrido)** — rellena `tipo_documental`, `fecha_doc`,
  `descripcion`, `parte` en el catálogo. Desbloqueado en esta sesión (ver §2).
- **F4 (copiador + bundles)** — copia `00_Input → Sala lectura/<fuente>/` con
  nombre canónico `<AAAA-MM-DD>_<tipo>_<descripción>.<ext>` y bundles.
- **F5 (render de índices)** — `INDICE.md` / `CRONOLOGIA.md` desde el catálogo,
  solo lectura.

## 2. Excepción RGPD (decisión de Nikolai, 2026-06-17)

El plan original difería F6 hasta el DPA con Scaleway (LLM soberano UE). **Decisión
de Nikolai:** aflojar **temporalmente** la regla de LLM local/Scaleway y dejar que
**Claude (esta sesión, frontier, Anthropic/EEUU) resuelva el residuo** ambiguo de
la clasificación leyendo el documento en claro. Motivo: no pagar Scaleway por lo
que Claude ya puede hacer en sesión.

- **Autorización expresa** de Nikolai como responsable del tratamiento. Excepción
  **temporal y acotada** a este flujo; **no deroga** la regla general del repo
  (el LLM solo lee de `06_Anonimizado`). Mismo patrón que la excepción del intake
  de procuradores.
- **Traza:** el residuo se materializa en `01_Procesado/_revisar/_clasificar.md`
  (worklist), de modo que queda registro de qué se leyó en claro y cuándo.
- **Reversión:** cuando entre el DPA, el residuo lo resolverá un conector
  (Scaleway o Claude API) en vez de Claude-en-sesión, sin tocar el resto del
  diseño (solo cambia quién rellena el worklist).

## 3. Arquitectura elegida (Opción A)

Módulo nuevo `core/sala_lectura.py`, **centrado en el catálogo**, que **reutiliza
los helpers probados** de `core/local_organizer.py` (el organizador Ollama
descartado) **sin** resucitar Ollama ni sus artefactos paralelos
(`_organizado/`, `_audit.jsonl`, `_plan_reorganizacion.md`).

Reúso desde `local_organizer`:
- `_sanitize` (saneo de nombres Windows, ≤60 car.),
- `_exif_o_mtime` (fecha por EXIF de imagen → mtime),
- el patrón de **plan markdown round-trip por hash** (tabla editable + parseo),
- la lógica de **copia idempotente** (COPY / SKIP_UNCHANGED / MOVED),
- la taxonomía `TAXONOMIA_EV` y `ORDEN_POR_CATEGORIA` (ya en `core/config.py`).

**Descartado** (Opción B): generalizar `local_organizer` in situ — reintroduce el
"tercer artefacto" que el §0 del plan quería evitar y arrastra un módulo
formalmente descartado. **Descartado** (Opción C): solo catálogo + render sin
copiador — incumple Tareas 3/4 del handoff.

## 4. Modelo de datos — catálogo único

`indice_documental.yaml` sigue siendo la SSOT (resuelve el Acoplamiento #2 del
plan: **no** se crea `_manifiesto.jsonl`; el dedup por SHA-256 sigue en
`00_Input/_intake_hashes.json` / `IntakeManifest`).

`CatalogEntry` (en `core/catalogo_documental.py`) se extiende con campos
**opcionales y retrocompatibles** (los catálogos viejos cargan por defecto; los
nuevos escriben todo):

| Campo nuevo | Tipo | Significado |
|---|---|---|
| `descripcion` | `str` | Descripción funcional neutra (≤60 car., sin PII) |
| `fecha_fuente` | `str` | `contenido` \| `crm_mtime` \| `exif` \| `mtime` \| `desconocida` |
| `confianza` | `float` | 0–1; `< UMBRAL` → `_revisar/` |
| `nombre_canonico` | `str \| None` | `<AAAA-MM-DD>_<tipo>_<descripción>.<ext>` |
| `ruta_sala_lectura` | `str \| None` | destino de la copia (idempotencia sin audit aparte) |

Campos ya existentes que F6 rellena: `tipo_documental` (= categoría de
`TAXONOMIA_EV`), `fecha_doc` (ISO `YYYY-MM-DD`), `parte`
(`propietario`/`buscador`/`tercero`), `estado`. `parent_id`/`orden_en_bundle` ya
existen y los puebla F4 (bundles).

`load_catalog` se hace **tolerante a claves desconocidas** (filtra al construir
`CatalogEntry`) para no romper ante catálogos de versiones distintas.

Se excluye siempre `90_Notas personales` del catálogo y de la sala.

## 5. Componente `core/sala_lectura.py` — API pública

Cuatro funciones, idempotentes, "copia, no mueve", `00_Input` intacto:

- `clasificar_caso(case_id) -> dict` — aplica reglas deterministas a cada entrada
  del catálogo; lo confiable lo escribe ya al catálogo; el residuo (sin regla o
  `confianza < UMBRAL_CONFIANZA_AUTOMOVE`) lo vuelca a la worklist
  `01_Procesado/_revisar/_clasificar.md`. Devuelve resumen (n total, n
  deterministas, n residuo).
- `aplicar_clasificacion(case_id) -> dict` — lee la worklist (ya rellena) y vuelca
  `tipo/fecha/descripcion/parte/confianza` al catálogo, por hash. Lo que siga sin
  resolver permanece en `_revisar/` (cuarentena).
- `render_indices(case_id) -> list[Path]` — genera `Sala lectura/INDICE.md` (por
  fuente → tipo) y `Sala lectura/CRONOLOGIA.md` (por `fecha_doc` ascendente, sin
  fecha al final). Cabecera "no editar a mano". Un documento = una entrada. Enlace
  al original en `00_Input` + "ver texto" al `MD/` cuando es binario.
- `poblar_sala_lectura(case_id) -> dict` — copia desde el catálogo a
  `Sala lectura/<fuente>/<nombre_canonico>`; aplica bundles (§7). Idempotente vía
  `ruta_sala_lectura` + SHA. Si el nombre canónico cambió, mueve el viejo→nuevo.

## 6. Reglas deterministas del clasificador (F6, sin LLM)

Orden de prioridad por entrada del catálogo:

1. **Imágenes** (`.jpg/.png/...`) → `00. FOTOS`; fecha EXIF → mtime
   (`_exif_o_mtime`). Confianza alta.
2. **Keywords del nombre de fichero** → categoría:
   - `factura`, `honorarios`, `abono` → `05. FACTURACIÓN - FINANZAS`
   - `burofax`, `requerimiento`, `reclamacion`, `OVC` → `07. RECLAMACIONES`
   - `encargo`, `captacion`, `captación`, `exclusiva`, `expose`, `visita` → `01. ACTIVACIÓN`
   - `oferta`, `contraoferta` → `03. OFERTAS`
   - `arras`, `reserva`, `señal`, `arrendamiento`, `contrato` → `04. ARRAS - ARRENDAMIENTOS`
   - `dni`, `nie`, `pasaporte`, `nota simple`, `titularidad`, `pbc` → `06. PBC`
3. **`id_carpeta_label` del CRM** (fuente CRM) como pista secundaria de categoría.
4. **Fecha:** patrón ISO `YYYY-MM-DD` / `DD-MM-YYYY` en el nombre → `fecha_fuente=contenido`;
   si no, `modified_at` del CRM (`crm_mtime`) o `mtime` del fichero.
5. **Residuo:** sin categoría confiable o sin fecha → a la worklist.

La worklist `_clasificar.md` es una tabla markdown con una fila por documento
residual (clave = hash), columnas: `Hash | Origen | Fuente | Tipo | Fecha |
Parte | Descripción`. Tipo/Fecha/Parte/Descripción vienen vacías o pre-rellenas
con la mejor pista; Claude (en sesión) o un humano las completa leyendo
`01_Procesado/MD/{slug}.md`.

## 7. Bundles (F4)

`poblar_sala_lectura` consume `core/conjunto_detector.detect_bundles` como
**proveedor de propuestas** (no se reescribe):

- **CRM:** cabecera (conserva su nombre descriptivo) en
  `Sala lectura/CRM/<bundle>/` + prueba en subcarpeta `adjuntos/`. El detector
  necesita `GdocuDocInfo` con `modified_at` (metadato del CRM).
- **WhatsApp:** chat (`.txt`/`.md`) + multimedia en subcarpeta `media/`.
- **`parent_id`/`orden_en_bundle`** se persisten en el catálogo al materializar el
  bundle (cierra la persistencia diferida de D9 / MEJORAS #29).

**Degradación elegante:** si el metadato del CRM (`modified_at`) no está
disponible localmente para alimentar el detector, se hace **copia plana sin
bundle** — no bloquea. Por eso los bundles van en la última etapa (la más frágil).

## 8. Disparo (opción 1 + opción 3)

**CLI `scripts/sala_lectura.py`** (typer), subcomandos:
`clasificar` · `aplicar` · `render` · `poblar` · `organizar` (orquestador:
`clasificar → render → poblar`; si `clasificar` deja residuo, se **detiene** tras
escribir la worklist y avisa; sin residuo, corre de punta a punta).

**Disparo habitual (opción 1):** Nikolai pide en sesión de Claude Code "organiza
la sala de lectura del caso X"; Claude corre `clasificar`, rellena la worklist
leyendo los `MD/`, y encadena `aplicar → render → poblar`.

**Botón Streamlit (opción 3):** botón "📚 Organizar sala de lectura" en el tab
Casos. Lanza la parte determinista y el render/poblado; el **residuo sigue
necesitando una sesión de Claude** hasta el DPA (el botón avisa de cuántos
documentos quedan en `_revisar/`). No da autonomía plena a Paola/Ana todavía
(ver §11).

## 9. Idempotencia, fronteras y criterios de aceptación

- `00_Input` no se modifica en ninguna ejecución.
- Re-ejecutar no duplica ni re-renombra: la copia se guía por `ruta_sala_lectura`
  + SHA en el catálogo; cambio de nombre canónico ⇒ move viejo→nuevo.
- Ningún camino de IA lee de `01_Procesado` **salvo** la excepción autorizada del
  §2 (Claude sobre `MD/` en claro, para clasificar el residuo).
- Cada documento: una entrada en los índices + su rendición en `MD/` (si binario),
  o es MD nativo (WhatsApp/Entrevistas).
- `90_Notas personales` queda fuera.

## 10. Etapas de implementación (TDD, cada una con suite verde)

1. **Catálogo extendido + clasificador determinista + worklist.** Extender
   `CatalogEntry` (§4), `clasificar_caso` (§6), `aplicar_clasificacion`, round-trip
   de la worklist. Tests: reglas por keyword/imagen/fecha, round-trip worklist,
   tolerancia de `load_catalog` a campos nuevos/desconocidos.
2. **Render de índices** (`render_indices`). Valor inmediato, riesgo bajo. Tests:
   agrupación por fuente/tipo, orden cronológico (sin fecha al final), una entrada
   por doc, cabecera read-only, enlaces relativos.
3. **Copiador plano idempotente** (`poblar_sala_lectura` sin bundles). Nombres
   desde catálogo. Tests: copia, idempotencia (SKIP), renombrado (MOVE), dedup
   SHA, `00_Input` intacto.
4. **Bundles** (`detect_bundles` + degradación) + persistencia
   `parent_id`/`orden_en_bundle`. Tests: bundle CRM cabecera+adjuntos, WhatsApp
   media, degradación a copia plana sin `modified_at`.

CLI y botón Streamlit se cablean al cierre (etapa 3/4, cuando hay algo que
disparar de punta a punta).

## 11. Fuera de alcance / futuro

- **Redesign como skill-Cowork multiusuario** (anotado en
  `docs/MEJORAS_FUTURAS.md`): para que Paola/Ana disparen la opción 1 de forma
  autónoma haría falta mover la organización a una **skill que corre en Cowork**
  con los datos en **Drive**, no el `core/` Python local (que solo corre en el PC
  de Nikolai). Implica reescribir/duplicar lógica, llevar los ficheros vía Drive,
  y extender la excepción RGPD a más usuarios y volumen. Proyecto aparte; se
  reabre cuando el DPA y la multi-usuario lo justifiquen.
- **Clasificador por conector** (Scaleway o Claude API) que sustituya a
  Claude-en-sesión para el residuo: llega con el DPA; entonces el botón Streamlit
  cierra el trabajo solo.
- **Taxonomía documental afinada** (lista cerrada definitiva, §9.1 del plan): hoy
  se usa `TAXONOMIA_EV` existente; afinar no bloquea.

## 12. Referencias del repo

- `core/catalogo_documental.py` — catálogo (extender `CatalogEntry`).
- `core/local_organizer.py` — helpers a reutilizar (no resucitar Ollama).
- `core/conjunto_detector.py::detect_bundles` — proveedor de bundles (CRM).
- `core/markdown_generator.py` — `MD/` en claro (ya re-enrutado, F3).
- `core/inventory.py` — `FileEntry` (source, sha256, mtime).
- `core/config.py` — `TAXONOMIA_EV`, `ORDEN_POR_CATEGORIA`, `UMBRAL_CONFIANZA_AUTOMOVE`.
- `core/case_manager.py:266` — scaffolding `Sala lectura/`, `MD/`, `_revisar/` (F2).
- `data/_prompts/clasificador_ev.md` — taxonomía + esquema (referencia, no se
  llama a LLM en las reglas deterministas).
- `docs/PLAN_SALA_LECTURA_01_PROCESADO.md` — plan fino y §0 (acoplamientos).
