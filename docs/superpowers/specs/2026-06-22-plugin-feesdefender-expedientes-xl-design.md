# Diseño — Plugin FeesDefender (Fase A): conector `expedientes-xl` + skills

*Fecha: 2026-06-22 · Autor: Nikolai + Claude Code · Estado: borrador para revisión.*

## 1. Problema y objetivo

El despacho necesita **depositar ficheros en el árbol de un expediente del Drive
compartido** (`G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\…`) **dirigido
desde Claude** (Claude Code local y/o Cowork), incluyendo **binarios y volúmenes
grandes** (p. ej. exports de WhatsApp: `.zip` de cientos de MB con fotos, vídeos y
PDFs). Hoy no se puede:

- El conector estándar `expedientes` (`@modelcontextprotocol/server-filesystem`)
  solo escribe **texto** (`write_file` = string UTF-8). No deposita binarios ni
  descomprime archivos.
- El sandbox de Cowork (`mcp__workspace__bash`) está **aislado** del disco real:
  lo que escribe el shell no llega al Drive.

**Objetivo (Fase A):** un **plugin `FeesDefender`** que aporte (a) un **conector MCP
genérico** con operaciones de fichero server-side de cualquier tamaño/tipo
(descomprimir, copiar, hashear), (b) las **skills prompt-driven** ya existentes del
despacho, y (c) una **skill de intake** que, tras depositar, **dispara la trazabilidad**
(dedup por hash + `IntakeManifest` + evento `upload_*`), para **leer/organizar
expedientes y depositar ficheros con traza** desde Claude **sin compartir el código
pesado de FeesDefender** (`core/`).

## 2. Hallazgos verificados (base del diseño)

Este diseño NO se apoya en suposiciones; cada pieza está comprobada en esta línea de
trabajo (2026-06-22):

1. **El MCP filesystem local llega al Drive a velocidad de disco.** Listado recursivo
   de un caso de 928 ficheros ≈1,1 s; lectura real ≈62 ms (vs ~53 min del conector de
   Drive per-fichero).
2. **Cowork alcanza un MCP stdio definido en `claude_desktop_config.json`** (el puente
   de Claude Desktop al VM de Cowork): Cowork listó 273 ficheros de un caso por la
   integración `expedientes`, host-side, sobre `G:`.
3. **Cowork NO hereda los plugins instalados por la CLI de Claude Code.** El plugin de
   prueba se vio en el tab **Code** pero **no** en **Cowork** → son sistemas de plugins
   separados. Cowork tiene su propio mecanismo (fichero `.plugin` nativo), fuera del
   alcance de esta fase.
4. **Un plugin SÍ empaqueta y registra un MCP server stdio + skills en Claude Code**
   (verificado con `claude plugin details`: componentes `MCP servers (1)` +
   `Skills (1)`), con `${CLAUDE_PLUGIN_ROOT}` para apuntar al binario/script incluido.
5. **El server estándar ya tiene `move_file` server-side** (cualquier tamaño/tipo),
   pero **no** copy, ni extract, ni escritura binaria → ésas son las adiciones reales.

## 3. El cuello de botella real: el ORIGEN (no "binario vs texto")

Las operaciones server-side solo actúan sobre ficheros **ya presentes en
`allowedDirectories`** (un disco que el servidor host-side puede leer). De ahí dos
casos:

- **Fichero ya en un disco del PC** (Downloads, staging, el propio Drive) →
  `extract_archive`/`copy_path` lo llevan al caso **sin que los bytes pasen por el
  LLM**. ✅ Caso principal de esta fase.
- **Fichero solo en el sandbox de Cowork** → el servidor host-side **no** lo ve. Único
  puente: `write_file_base64` (bytes por el LLM, con tope duro). ❌ Límite inherente.

**Consecuencia de diseño:** la capacidad que se construye es el **depósito grande
dirigido desde el agente cuando el fichero ya está en un disco del PC**. No rompe el
aislamiento del sandbox (imposible). El intake de WhatsApp por **Streamlit local** ya
resuelve su caso sin MCP (Streamlit tiene los bytes y escribe a disco); esta extensión
es para el camino **agéntico**.

## 4. Arquitectura

```
Plugin "FeesDefender"  (repo = fuente única; NO contiene core/)
├── MCP server "expedientes-xl"   (Python genérico, sin lógica de dominio)
│     extract_archive · copy_path · copy_dir · write_file_base64(cap) · delete_path
├── skills prompt-driven YA existentes (organizar-sala-lectura, triaje-viabilidad,
│     viabilidad-prerelleno, escritos-judiciales, pase-de-estilo, …)
└── manifest (.claude-plugin/plugin.json) + .mcp.json + marketplace (git privado)
```

### 4.1. Canales de entrega por cliente (de los hallazgos §2)

| Cliente | Skills | Conector `expedientes-xl` |
|---|---|---|
| **Claude Code local** | por el **plugin** (install único) | por el **plugin** (`.mcp.json`, host-side) ✅ |
| **Cowork** | por **re-import `.skill`** (flujo actual del despacho) | por **`claude_desktop_config.json`** (puente verificado §2.2) — config **una vez por máquina** |

El plugin es **SSOT + vehículo de Claude Code**. La entrega a Cowork usa los canales
**ya probados**; no depende de que Cowork cargue plugins nativos (no lo hace hoy, §2.3).

### 4.2. Por qué NO expone el código de FeesDefender

- El server `expedientes-xl` es **genérico** (operaciones de fichero), **sin `import
  core`** ni lógica de dominio (regla de 3 capas). El saneado anti path-traversal se
  **re-implementa autocontenido** en el server (patrón de `core/intake_manual.extract_zip`),
  no se importa de `core/`. → el plugin es shippable sin el repo.
- El plugin **no incluye** la maquinaria pesada (OCR/Docling, sync CRM, rclone,
  Streamlit): se queda en la máquina local del repo. Compartir el plugin no expone
  `core/`.
- El conector **nunca** escribe trazabilidad de dominio. La trazabilidad
  (`IntakeManifest` + evento `upload_*`) la dispara la **skill de intake** (§5bis), que
  es **del despacho** (se comparte internamente como las demás skills, no es pública como
  el conector). El **formato** del manifest/log tiene su **fuente de verdad en `core/`**
  (`intake_manifest.py`, `intake_log.py`); la skill lo **espeja** con **gate anti-drift**
  (patrón de `sync_taxonomia_skills.py`). El conector solo aporta primitivos genéricos
  (mover/descomprimir/**hashear**/escribir texto); no conoce el esquema del manifest.

## 5. El MCP server `expedientes-xl` (superficie de herramientas)

Todas las rutas se resuelven y validan **dentro de `allowedDirectories`**; cualquier
ruta que escape se rechaza (sin intentar rescatarla).

| Tool | Contrato | Notas |
|---|---|---|
| `extract_archive(archive_path, dest_dir)` | Descomprime `.zip`/`.tar` de `archive_path` en `dest_dir`. | Saneado anti-traversal **por miembro** (descarta entradas con `..`, absolutas, nulos; doble check `resolve().relative_to`). Server-side, cualquier tamaño. |
| `copy_path(src, dst)` | Copia fichero `src`→`dst` (no destructivo). | Cualquier tamaño/tipo. |
| `copy_dir(src, dst)` | Copia recursiva de árbol `src`→`dst`. | Idem; saneado de cada destino. |
| `write_file_base64(path, content_b64, max_bytes)` | Escribe binario decodificando base64. | **Tope duro configurable** (def. p. ej. 8 MB). Único camino para el caso sandbox-trapped; los bytes pasan por el LLM. Rechaza si supera `max_bytes`. |
| `hash_path(path)` | Devuelve el **SHA-256** del fichero, calculado server-side. | Solo cruza el digest (64 chars), **no los bytes**. Habilita el dedup de ficheros grandes sin pasarlos por el LLM. Genérico. |
| `append_text(path, text)` | Anexa `text` a un fichero (crea si falta). | Para `_intake_log.jsonl` (append-only). Genérico; valida `allowedDirectories`. |
| `delete_path(path)` *(opcional)* | Borra fichero/dir dentro del sandbox. | Restringido a `allowedDirectories`. Diferible si añade riesgo. |

> Todos genéricos (file ops + hashing + texto). Ninguno conoce el esquema del manifest:
> ese conocimiento vive en la skill de intake (§5bis).

**Diferido a fase posterior (no Fase A):** IO por chunks (offset/length) para inspección
de ficheros grandes — la lectura por chunks **igual** enruta bytes por el LLM, así que no
sirve para transferencia masiva; solo para inspección. Se añade si surge necesidad.

## 5bis. Skill de intake + trazabilidad (cierra la brecha)

El conector deposita bytes; la **traza** (dedup + manifest + evento) la dispara una
**skill de intake del despacho** que orquesta llamadas al conector. Flujo:

```
1. hash_path(zip)                  → SHA-256 server-side (sin pasar bytes por el LLM)
2. read_text_file(_intake_hashes.json) → ¿ya importado? → SKIP (dedup de importación)
3. extract_archive(zip → 00_Input/<fuente>/) → depósito server-side
4. hash_path(cada fichero depositado) → SHA-256 server-side (dedup fino)
5. write_file(_intake_hashes.json, manifest actualizado) → IntakeManifest
6. append_text(_intake_log.jsonl, evento upload_*) → traza/auditoría
```

Todo lo que toca bytes (1, 3, 4) es **server-side** vía el conector; solo los JSON
pequeños (5, 6) cruzan el agente. Funciona en Claude Code **y** Cowork.

**Fuente de verdad del formato:** `core/intake_manifest.py` + `core/intake_log.py`. La
skill **espeja** el esquema (entradas del manifest, campos del evento, fuentes
`WHATSAPP_SUBDIRS`/`source=`), mantenido por un **sync + gate anti-drift** análogo a
`sync_taxonomia_skills.py`. Sin esto, habría dos definiciones del manifest divergiendo.

**Detalle abierto (para el plan):** cómo escribir los JSON de forma **determinista en
Cowork**, donde la Python adjunta de la skill **no corre** (sandbox aislado). Opciones a
evaluar: (a) el agente ensambla el JSON guiado estrictamente por la skill y lo escribe
vía conector; (b) un primitivo genérico de mayor nivel en el conector. En Claude Code un
helper Python adjunto sí puede hacerlo determinista. **No se resuelve en esta spec.**

## 5ter. Fuentes soportadas: depósito vs procesamiento

El conector es **agnóstico al tipo** (opera sobre bytes). La skill de intake enruta cada
fichero a su subcarpeta de `00_Input/` (la convención por fuente es dominio → vive en la
skill, no en el conector).

| Fuente | Destino `00_Input/` | Cómo se deposita |
|---|---|---|
| Drive E&V (PDFs, contratos, notas, planos) | `01_Drive EV/` | `copy_path` o `extract_archive` |
| WhatsApp (zip export) | `02_Whatsapp/<rol>/` | `extract_archive` |
| Email (`.eml`/`.msg`) | `03_Email/` | `copy_path` (o extraído de zip) |
| Manual (burofaxes, escritos sueltos) | `04_Manual/` | `copy_path` |
| CRM (descargas del gestor) | `05_CRM/<bucket>/` | `copy_path` (bucket = dominio en la skill) |
| Entrevistas (transcripción Meet) | `06_Entrevistas/<AAAA-MM-DD>_<rol>_<apellido>/` | `copy_path` |
| Fotos, vídeos, audios, vCards | la que toque | `copy_path`/`extract_archive` (sin filtro de tipo) |

**Límite de tamaño/origen (igual que §3):** grandes → al disco (`_ingest/`) primero, no
por el chat; pequeños (< `max_bytes`, def. ~8 MB) → `write_file_base64` si solo están en
el sandbox de Cowork.

**Depósito ≠ procesamiento por-fuente.** El conector + la skill **depositan con traza**;
el procesamiento fino por fuente **NO** es del conector y se queda en `core/` (local):
explotar un `.eml` en cuerpo + adjuntos MIME, OCR/markdown de un PDF escaneado, detección
de adjuntos que WhatsApp omitió en el export. Lo depositado **sí** lo recoge el pipeline
local (`inventory.scan` recorre `00_Input/`) en la siguiente corrida sobre el caso. Las
fuentes con parser propio en `core/` (email, WhatsApp) conservan su camino Streamlit
local para ese procesamiento fino.

## 6. Staging — `_ingest/` en la raíz del Drive

**Decisión:** convención `…\EXPEDIENTES - TYUKHAY LEGAL\_ingest\` como zona de aterrizaje.

- **Cero cambios de config** (ya está dentro del `allowedDirectories` actual = la raíz).
- **No amplía la superficie** a carpetas fuera del Drive (importante con ficheros
  confidenciales). Se descarta añadir Downloads/`C:\…` como segundo `allowedDirectory`
  por seguridad; revisable si la ergonomía lo exige.

**Flujo:** dejas el fichero en `_ingest\` (arrastrándolo en el Explorador o guardando
ahí el adjunto del email) → desde Claude: *"extrae `_ingest\export.zip` al caso BaRS1,
02_Whatsapp"* → `extract_archive` lo descomprime server-side al caso.

## 7. Seguridad

- **`allowedDirectories`** validado en **todas** las tools nuevas (igual que el server
  estándar): el destino resuelto debe quedar dentro del sandbox.
- **Anti path-traversal** en cada ruta y en **cada miembro** de un archivo (`..`,
  rutas absolutas, nulos → descartar la entrada entera; doble check con
  `resolve().relative_to`).
- **Topes de tamaño** en `write_file_base64` (`max_bytes`, configurable; default duro).
- **Rechazo fuera de sandbox**: error explícito, nunca operación parcial.
- **Tests pytest por tool**, incluidos **casos de traversal** (entradas maliciosas) y de
  **límite** (base64 sobre el tope). Suite verde tras cada paso.

## 8. Dependencias y configuración

- **Runtime:** server en Python con el SDK oficial `mcp`. Prerrequisito en la máquina:
  `pip install mcp` (Python ya presente en el entorno del despacho). Documentar en la
  guía de instalación.
- **Plugin (Claude Code):** `.mcp.json` declara el server como
  `command: "python"`, `args: ["${CLAUDE_PLUGIN_ROOT}/server/expedientes_xl.py",
  "G:\\Unidades compartidas\\EXPEDIENTES - TYUKHAY LEGAL"]`. La ruta del montaje se
  asume **consistente entre máquinas** (Drive for Desktop monta igual); si varía, se
  parametriza.
- **Cowork:** el mismo server se registra en `claude_desktop_config.json` (entrada
  análoga a la del `expedientes` actual), una vez por máquina.
- **Distribución del plugin:** marketplace en **repo git privado** del despacho (la UI
  de Desktop exige owner/repo o URL git; no admite ruta local). Repo candidato:
  `TyukhayNi/despacho-plugins` (separado de FeesDefender para no acoplar privacidad).

## 9. Tests

- **Por tool** (`extract_archive`, `copy_path`, `copy_dir`, `write_file_base64`,
  `hash_path`, `append_text`, `delete_path`): caso feliz + traversal (`..`, absoluta,
  symlink/escape) + límite (`write_file_base64` sobre `max_bytes`) + fuera de
  `allowedDirectories`.
- **`hash_path`**: SHA-256 correcto y estable (mismo digest que `hashlib.sha256` sobre los
  bytes); no devuelve los bytes.
- **Saneado** equivalente al de `extract_zip` (regresión sobre miembros maliciosos).
- **Trazabilidad (skill de intake)**: el manifest/evento que escribe **coincide con el
  formato de `core/intake_manifest.py` + `core/intake_log.py`** (test de paridad de
  esquema); dedup de importación por hash de zip; dedup fino por hash de fichero;
  idempotencia (re-correr no duplica entradas). Gate anti-drift del esquema espejado.
- Sin red, con `tmp_path` como `allowedDirectory`. Suite verde tras cada paso.

## 10. Decisiones cerradas

- **Forma:** server **Python complementario** (`expedientes-xl`), no fork TS ni reemplazo
  total del estándar. Convive con `expedientes`.
- **Alcance:** **(A)** leer/organizar + depositar. La maquinaria pesada (intake CRM,
  OCR, viabilidad completa) **fuera** del plugin — se queda local.
- **Sin exponer FeesDefender:** conector genérico + skills (prompts); cero `core/`.
- **Trazabilidad SÍ en Fase A:** la dispara una **skill de intake** del despacho (no el
  conector), vía primitivos genéricos (`hash_path` server-side + `append_text`). El
  **formato** es de `core/` (SoT); la skill lo espeja con gate anti-drift.
- **Staging:** `_ingest/` en la raíz del Drive (sin ampliar sandbox).
- **Entrega a Cowork:** canales probados (`.skill` re-import + `claude_desktop_config.json`),
  no plugin nativo de Cowork.

## 11. Fuera de alcance / diferido

- **`.plugin` nativo de Cowork** (instalación única en Cowork) — opción (A) "exhaustiva"
  descartada por ahora; solo ahorraría una edición de config por máquina y no evita el
  montaje del Drive (requisito irreductible). Reabrir si el despacho crece.
- **IO por chunks** para ficheros grandes (solo inspección; no transferencia).
- **Caso sandbox-trapped** más allá de `write_file_base64` con tope (límite inherente).
- **Exponer `core/`** (intake/CRM/OCR) — sería la "Opción B", decisión aparte
  (¿código dentro del plugin vs servidor central cliente-fino?).
- **Montaje del Drive** en las máquinas del equipo (prerrequisito humano, no de software).

## 12. Enlaces

- Intake WhatsApp (caso canónico de binario grande): `docs/superpowers/specs/2026-06-15-intake-whatsapp-design.md`
  (su `deposit_export` resuelve el camino Streamlit local; `extract_archive` cubre el agéntico).
- Pivote local de la sala de lectura: `PLAN.md` `[SIGUIENTE-SALA-UNICA-PLANA]` + `docs/DEAD_ENDS.md`
  (rendimiento conector vs local).
- Conector `expedientes` y su montaje: memoria `reference-expedientes-filesystem-mcp`.
