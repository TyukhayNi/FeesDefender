# Diseño — Sala de lectura ÚNICA, plana, alimentada por una sola skill (todo `00_Input`)

> **Origen:** brainstorming Claude Code ↔ Nikolai, 2026-06-18, a partir del HANDOFF
> `docs/superpowers/handoff-2026-06-18-unificar-salas-lectura.md`. **Decisión cerrada y
> aprobada por Nikolai.** Implementación: Claude Code (skills en `.claude/skills/`,
> ejecución en Cowork/claude.ai). **No empezar a implementar sin el plan aprobado**
> (este spec → `writing-plans` → plan → implementación).

## 1. Objetivo

Unificar las **dos** salas de lectura que hoy conviven en `01_Procesado/` de cada
expediente en **UNA sola "Sala lectura"**, alimentada por **una única skill
prompt-driven** que procesa **todo `00_Input`** (no solo `01_Drive EV`). Sustituye:

- **Motor local** `core/sala_lectura.py` (Python, por FUENTE, con Docling/catálogo).
- **Skill Cowork** `organizar-sala-lectura` v1.2 (Drive, solo `01_Drive EV`, por TIPO).

Resuelve `MEJORAS #34` (multiusuario): Paola y cualquiera la ejecutan desde Cowork
sobre el Drive del despacho, sin Python local ni dependencia del PC de Nikolai.

## 2. Decisiones cerradas (tensiones T1–T5 del handoff)

- **T1 — Disposición física: PLANA.** Un único directorio `Sala lectura/`. La
  taxonomía E&V **no** vive en carpetas: vive en `INDICE.md`. Orden cronológico por el
  prefijo de fecha del nombre. (Coste aceptado: el ruido de `08. PENDIENTE` —documentación
  técnica/de obra— se intercala con los documentos jurídicos en el listado físico; la
  vista por categoría está en `INDICE.md`.)
- **T5 — Naming: SIN slug de categoría.** Fichero `AAAA-MM-DD_descripcion.ext`
  (descripción legible con guiones_bajos, sin PII). Documento **compuesto** =
  **subcarpeta** `AAAA-MM-DD_descripcion/` (misma nomenclatura → se intercala
  cronológicamente) que contiene el principal + sus anexos.
- **T4 — Runtime/propiedad: la SKILL es el único constructor** de la sala y del
  catálogo. Corre en Cowork o en Claude Code local (lee vía conector de Drive o FS;
  el árbol del caso vive en `G:\…` = Drive montado). Se **deprecan** el camino de sala
  del core (`clasificar_caso`/`aplicar_clasificacion`/`render_indices`/
  `poblar_sala_lectura`/`clasificar_residuo_llm` #37) y el paso `build_catalog` del
  pipeline (sin más consumidor). El **pipeline confidencial**
  (`extractor → MD/ → anon → 06_Anonimizado → frontier`; scorer; viability; demanda)
  queda **intacto y separado**.
- **T2 — SSOT: manifiesto (LLM) + catálogo derivado por helper.** El modelo escribe
  `_MANIFIESTO.md` (traza humana). Un **helper determinista** empaquetado en la skill
  deriva `indice_documental.yaml` del manifiesto. El LLM **no** escribe YAML (evita
  mojibake/drift de esquema). El catálogo es la SSOT máquina; el manifiesto es la traza.
  Ambos del mismo origen → sin doble verdad.
- **T3 — Clasificador: canon único + generado a la skill + gate anti-drift.** El motor
  de clasificación es **Claude-en-sesión leyendo el contenido** (no por nombre). El
  criterio vive en una sola fuente y se genera a la skill (ver §6).

## 3. Restricciones heredadas (no romper)

- **RGPD — APROBADO por el responsable del tratamiento (Nikolai, 2026-06-18):** la skill
  lee **todo `00_Input` en claro** (incluidas WhatsApp, email, entrevistas), vía
  Cowork/Claude, ejecutado por Paola y otros. Extiende la excepción de `MEJORAS #34`.
- **Salida FUERA de `00_Input`.** `inventory.scan` hace `rglob("*")` sobre `00_Input`
  (`core/inventory.py:86`): cualquier cosa bajo `00_Input` se re-ingiere. La sala va a
  `01_Procesado/Sala lectura/`.
- **No destructivo.** El crudo de `00_Input` nunca se toca ni se borra. Copia server-side.
- **Llave = sha256 de los bytes, scope `00_Input`.** Es el puente con los registros del
  caso (`_intake_hashes.json` M9, `_inventory.json`, `indice_documental.yaml`). El
  conector da `md5Checksum`; la skill calcula **sha256 de los bytes descargados**.
- **Modelo: Sonnet/Haiku, NO Opus.** Clasificación atómica + visto bueno humano. Nota de
  uso en la skill + prompt ligero. El grueso de la velocidad lo da el skip incremental.
- **Fuente única de skills:** `.claude/skills/` del repo; tras editar, `package_skill.py`
  + nota de re-import del `.skill` en el servidor. No tocar `despacho-skills` (deprecado).
- **Windows/PowerShell; UTF-8 sin BOM.**

## 4. Arquitectura y componentes (unidades con frontera clara)

1. **Skill `organizar-sala-lectura` (ampliada)** — prompt-driven, runtime Cowork/local.
   Flujo:
   - **Paso 0 (bloqueante):** carga el conector de Drive (ToolSearch); acepta URL de
     carpeta pegada en el chat; resuelve `folderId` y DETECTA nivel (raíz del expediente
     → baja a `00_Input`; o si la URL ya es una subcarpeta de `00_Input` → la usa);
     pide activar **"Permitir siempre"** en el conector (cero diálogos durante la
     ejecución).
   - **Recogida:** lista **todo `00_Input`** (todas las fuentes: `01_Drive EV`,
     `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`, `06_Entrevistas`), excluyendo
     `90_Notas personales`. Para cada fichero: `md5Checksum` (metadato) y, si es nuevo,
     contenido.
   - **Skip incremental:** compara `sha256` (de bytes) contra `_MANIFIESTO.md`; hash ya
     presente → SKIP total (no lee contenido, no clasifica, no copia). Respeta ajustes
     manuales.
   - **Clasificación (solo lo nuevo):** Claude lee el contenido → categoría `TAXONOMIA_EV`
     (PBC-por-parte, §6), fecha (jerarquía §7), descripción (sin PII), parte, y pertenencia
     a bundle (§5). Ambiguo/ilegible → `08. PENDIENTE DE CLASIFICAR`, nunca forzar.
   - **Gate humano único (Paso 2.5):** propuesta visual (artefacto HTML; fallback
     markdown), ordenada por fecha **descendente** → espera OK → ejecuta de una pasada.
   - **Escritura:** copia a `01_Procesado/Sala lectura/` (plana, §4.2) + `_MANIFIESTO.md`
     + `INDICE.md` (por categoría, fecha desc) + `CRONOLOGIA.md` (asc). Cabeceras
     "GENERADO — no editar".
2. **Helper `manifiesto_a_catalogo`** (python empaquetado en la skill): deriva
   `indice_documental.yaml` (esquema de `core/catalogo_documental.CatalogEntry`) del
   `_MANIFIESTO.md`. Determinista, idempotente.
3. **Helper `sync_taxonomia_skills.py`** (scripts/): genera la sección de taxonomía/criterios
   de la skill desde el canon (§6). Gate anti-drift en `scripts/check_skills.py`.
4. **Canon de criterios** `data/_prompts/clasificador_ev.md`: PBC-por-parte + jerarquía de
   fecha + regla ambiguo→08. (La lista de categorías sigue en `core/config.py::TAXONOMIA_EV`.)

### 4.1 Scaffolding objetivo

```
<Expediente>/01_Procesado/
└── Sala lectura/
    ├── INDICE.md          (por categoría E&V, enlaces a la ubicación plana, fecha desc)
    ├── CRONOLOGIA.md      (por fecha ascendente)
    ├── _MANIFIESTO.md     (sha256 · original → canónico · categoría · fecha · parte · parent_id)
    ├── 2024-04-26_catastro.pdf
    ├── 2024-05-13_reconocimiento_de_cliente.pdf
    ├── 2024-10-04_contrato_honorarios_intermediacion/        (compuesto)
    │   ├── 2024-10-04_contrato_honorarios_intermediacion.pdf
    │   ├── 2024-10-04_contrato_honorarios_intermediacion_anexo_1_pbc.pdf
    │   └── 2024-10-04_contrato_honorarios_intermediacion_anexo_2_pbc.pdf
    ├── 2025-07-14_contraoferta_vendedor_17m.pdf
    └── 2025-07-22_requerimiento_resolucion.pdf
```

### 4.2 Vista por categoría e `indice_documental.yaml`

`INDICE.md` agrupa por categoría con enlaces a la ubicación plana real. El catálogo
`indice_documental.yaml` (derivado) conserva `fuente`, `tipo_documental`, `parte`,
`parent_id`/`orden_en_bundle`, `hash`, etc.: la **fuente y la categoría se conservan en
el catálogo/índices** aunque las carpetas físicas sean planas.

## 5. Reglas de bundle (determinista por origen)

Carpeta-bundle solo si hay **≥1 anexo**; documento solo → fichero plano.

- **WhatsApp:** chat (`.txt`/`.md`) + multimedia en el mismo export → principal = chat,
  anexos = media. (`MEJORAS #35`.)
- **Email `.eml`:** cuerpo = principal; partes MIME adjuntas = anexos.
- **CRM:** `conjunto_detector` (clúster por `modified_at` ∩ patrón `D NN`). **Mejor
  esfuerzo**: desde Cowork no hay `modified_at` del CRM → puede degradarse a plano.
- **Sueltos `01_Drive EV`/`04_Manual`:** solo se agrupan con **señal explícita**
  (convención `_anexo_N`, PDF troceado, o propuesta confirmada en el gate); si no → planos.
  Nunca inventar bundles.

`parent_id`/`orden_en_bundle` se registran en el manifiesto → catálogo.

## 6. Clasificador y DRY de criterios

- **Motor:** Claude-en-sesión lee el contenido (no por nombre). Sin API de pago
  (Scaleway queda OPT-IN para un futuro DPA). Ambiguo/ilegible → `08. PENDIENTE`.
- **PBC por parte** (decidido sobre Tibidabo): identidad del **VENDEDOR** (nota mercantil,
  nota simple/titularidad, titular real, poderes, catastro) → `01. ACTIVACIÓN`;
  **excepción** anexos 1 y 2 del vendedor → `06. PBC` (la carpeta sobrevive solo para eso);
  identidad/KYC del **COMPRADOR** → `03. OFERTAS` (subcarpeta por oferta si hay varias).
  La parte se decide **leyendo** el documento.
- **DRY:** fuente única = `TAXONOMIA_EV` (`core/config.py`) + `data/_prompts/clasificador_ev.md`
  (PBC-por-parte + jerarquía de fecha + ambiguo→08). `scripts/sync_taxonomia_skills.py`
  genera la sección de clasificación de la skill desde ese canon; `scripts/check_skills.py`
  gate anti-drift (igual que `sync_cuestionario_from_canon.py` en `viabilidad-prerelleno`).

## 7. Fecha (jerarquía)

(a) otorgamiento/firma en el cuerpo → (b) otra fecha inequívoca del contenido → (c) nombre
del fichero → (d) `0000-00-00`. `mtime` **no** es fuente; si se usa como aprox., marcar
`(*)` en `CRONOLOGIA.md` y `_MANIFIESTO.md`. Regresión real (leer cada doc, no por nombre):
`PODERES JAIME.pdf` → `2023-01-17`; `Poderes PersonaTres Feu` → `2024-11-21`. (Resuelve
`MEJORAS #38`: la fecha de contenido prevalece sobre `mtime`.)

## 8. Idempotencia / 2ª pasada

Skip por `sha256` (de bytes) en `_MANIFIESTO.md`. La 2ª pasada solo lee/clasifica/copia
documentos **nuevos**; coste ∝ docs nuevos. Sin novedades → casi instantánea (listar +
comparar hashes + re-render índices). Respeta ajustes manuales (no pisa lo ya colocado).
Add-only; nunca borra. Cambio de reglas de clasificación = vaciado manual + recorrido limpio.

## 9. Colisión de nombres (`MEJORAS #36`)

En estructura plana sube la probabilidad de dos ítems con el mismo `AAAA-MM-DD_descripcion`.
Guarda determinista: sufijo `_2`/`_3` por destino ya usado en la corrida (o fragmento de
hash), respetando idempotencia.

## 10. Lectores de la sala

- **`triaje-viabilidad`:** repuntar su "Entrada" (hoy `02_Sala lectura/`) a **`00_Input`
  directo** (como `viabilidad-prerelleno`), **no** a la sala. Razón: el triaje es un go/no-go
  jurídico y no debe **heredar errores de clasificación** de la sala (un encargo mal
  clasificado a `08. PENDIENTE` se le escaparía si solo mirase categorías); leyendo
  `00_Input` ve todo y busca sus 6 factores (encargo firmado, nexo causal, obligado al
  pago, prueba, importe/base, prescripción) por lectura dirigida — que no duplica la
  clasificación de 8 categorías de `organizar`. Opcional: si la sala existe, usar
  `INDICE.md` como **pista de navegación**, pero la **fuente de verdad es `00_Input`**. NO
  se fusiona con `viabilidad-prerelleno` (son secuencia, no duplicado).
- **`viabilidad-prerelleno`:** **no se toca** (lee `00_Input` directo).
- **Consecuencia:** la sala **no tiene lectores que dependan de ella**; es una capa humana
  de lectura + la base que produce `organizar`. Esto desacopla el triaje del orden de
  ejecución (no exige correr `organizar` antes).

## 11. Deprecación y migración

- **Deprecar** (marcar, no borrar de golpe): `core/sala_lectura.py` (camino de sala, incl.
  `clasificar_residuo_llm` #37) + paso `catalogo.build` en `core/pipeline.py`.
- **Conservar:** `core/catalogo_documental.py` (esquema `CatalogEntry` y `build_catalog`,
  reutilizados por el helper para conocer el esquema), `core/conjunto_detector.py`, y el
  fix **OCR-OOM `2eeec1a`** (sirve a la extracción del pipeline confidencial). El
  **cableado de `build_catalog` en el pipeline (`45dd5ad`)** se deprecna junto al paso
  `catalogo.build` (su único consumidor era la sala del core); la **función** `build_catalog`
  permanece disponible. **Reevaluar `MEJORAS #39`** (OCR local): la skill esquiva el OCR
  local para la sala (usa la extracción del conector de Drive); el OCR local solo lo
  necesita el camino confidencial.
- **Migración BaRS1 (banco de pruebas):** vaciar las salas v1.0 (`Sala lectura/` por fuente
  + `Sala lectura Drive EV/` por categoría) y recorrer limpio con la skill unificada.

## 12. Código y skills afectados

- **Skill** `.claude/skills/organizar-sala-lectura/` (alcance todo `00_Input`; salida plana;
  bundles; fecha-cuerpo; orden índices; Paso 0 conector+URL+permiso; helpers empaquetados).
- **Skill** `.claude/skills/triaje-viabilidad/` (repuntar entrada a la sala unificada).
- **Core:** marcar deprecado `core/sala_lectura.py` + paso `catalogo.build` en `pipeline.py`.
- **Scripts:** `sync_taxonomia_skills.py` (nuevo) + gate en `check_skills.py`;
  `package_skill.py`/`validate_skills.py` (empaquetado/validación).
- **Canon:** `data/_prompts/clasificador_ev.md` (criterios) + `core/config.py::TAXONOMIA_EV`.
- **MEJORAS:** #34 (resuelto por esta vía), #35 (bundle WhatsApp), #36 (colisión), #38
  (fecha cuerpo); #37/#39 → deprecación/reevaluar.

## 13. Tests

- **Helpers deterministas** (pytest): `manifiesto_a_catalogo` (manifiesto→YAML válido,
  esquema `CatalogEntry`, idempotente); `sync_taxonomia_skills` (genera desde canon);
  gate anti-drift de `check_skills` (detecta divergencia taxonomía canon↔skill).
- **Skill (prompt):** `validate_skills`/`check_skills` + prueba real sobre BaRS1 (tras
  vaciar las salas v1.0): verifica salida plana, bundles, fecha-cuerpo, skip en 2ª pasada,
  catálogo derivado coherente.

## 14. Fuera de alcance / diferido

- Fusión de generadores Cowork↔core (no se fusionan; la skill es el único constructor).
- Bundles CRM perfectos desde Cowork (sin `modified_at`): mejor esfuerzo; afinado futuro.
- Copia física plana de export en bloque: solo si surge necesidad real (hoy la vista plana
  ES la física).
- Redesign de `triaje-viabilidad`/`viabilidad-prerelleno` más allá de repuntar la entrada
  de triaje a `00_Input` (ambas leen `00_Input` directo; la sala no es su fuente).

## 15. Referencias

- HANDOFF `docs/superpowers/handoff-2026-06-18-unificar-salas-lectura.md`.
- Specs/planes previos: `docs/superpowers/specs/2026-06-18-organizacion-sala-lectura-drive-triaje-design.md`,
  `docs/superpowers/specs/2026-06-17-sala-lectura-f4f6-design.md`,
  `docs/PLAN_SALA_LECTURA_01_PROCESADO.md`.
- `PLAN.md` → `[SIGUIENTE-SALA-UNICA-PLANA]`. `docs/MEJORAS_FUTURAS.md` #34/#35/#36/#38/#39.
- Código: `core/sala_lectura.py`, `core/catalogo_documental.py`, `core/inventory.py`,
  `core/conjunto_detector.py`, `core/intake_manifest.py`.
- Memoria: `project-sala-lectura-prompt-driven.md`, `project-sala-lectura-01-procesado.md`.
