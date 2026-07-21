# Changelog — organizar-sala-lectura

## 1.10 — 2026-07-21
- **Fix — `verificar_sala.py` reconoce `parent_id` como carpeta de bundle.**
  La v1 de `verificar()` solo aceptaba match exacto contra `nombre_canonico`
  o sha256; la convención real desde v1.1 es que `parent_id` sea el nombre
  pelado de la carpeta del bundle (prefijo de directorio). Con eso, todo
  anexo de todo bundle salía como "huérfano" (21 falsos positivos detectados
  al re-correr sobre W-02VUDR). Ahora también resuelve por prefijo de
  directorio.
- **Fix — `copiar_manifiesto_rclone.py::_rc_activo` usa POST, no GET.** La RC
  API de rclone es POST-only (confirmado con `curl` real contra v1.73.5: GET
  a `/core/pid` → 404, POST → 200). Con GET, `_rc_activo()` SIEMPRE devolvía
  `False` → `levantar_rcd_si_falta` nunca detectaba un rcd ya activo y
  agotaba el timeout de 10s — Task 4 (copia vía `rclone rcd`) nunca había
  funcionado de verdad pese a la verificación de la v1.9. Con el fix: 3
  ficheros (incl. uno de 1,1 GB) se copiaron server-side en 19s.
- **Paso 1-bis.d pasa de sugerencia a obligación + Paso 6.5 verifica fecha
  contra cobertura.** 7 binarios opacos de W-02VUDR quedaron en `0000-00-00`
  con su espejo MD ya disponible y una fecha inequívoca en el texto (p.ej.
  un burofax certificado con "Fecha y hora del envío: 08/04/2025") porque
  `texto_espejo_md()` era una consulta opcional, fácil de saltarse bajo
  presión de tiempo (casos grandes fanned-out en varios subagentes).
  `texto_espejo_md` pasa a ser obligatoria antes de escribir `0000-00-00`
  para cualquier binario opaco, y `verificar()` (Paso 6.5) ahora acepta
  `cobertura_filas` opcional para detectar automáticamente esta discrepancia
  si se repite: fecha `0000-00-00` con texto ya extraído por encima de un
  umbral de caracteres. Rompe el propósito de la sala (timeline claro) si no
  se corrige.

## 1.9 — 2026-07-21
- **Pre-clasificación mecánica (Paso 1-bis, `scripts/preclasificar.py`):**
  `clasificar_por_patron` — 6 patrones estrechos para 00/01/03/04/05/06 y
  **"07. RECLAMACIONES" como DEFAULT** (no una categoría a demostrar leyendo
  contenido; en un expediente ya judicializado concentra la mayoría de
  documentos), "08. PENDIENTE DE CLASIFICAR" solo para bundles conversacionales
  sin parte identificable. `dedup_por_sha` (dedup por sha256 antes de
  clasificar). `agrupar_por_hilo` (agrupa `.eml` del mismo hilo por sufijo
  `_N` del motor de export; clasifica un representante y propaga). `texto_espejo_md`
  (lee el espejo MD de `02_Sala de máquina` para binarios opacos en vez de
  rendirse a `(*)`). `subcategoria_crm` (subcarpeta del Gestor Documental como
  etiqueta secundaria gratis, sub-agrupa "07. RECLAMACIONES" en `INDICE.md`).
  Test anti-drift contra `core.config.TAXONOMIA_EV`.
- **Plan persistido a fichero + gate condicional (Paso 2-bis/3):** la propuesta
  se guarda en `_plan/plan-<fecha>.md` antes del gate; el gate solo espera
  aprobación humana si hay anomalías genuinas (bundle sin parte, W-code ajeno,
  casi-duplicado, binario opaco sin espejo MD) — si la propuesta sale limpia,
  auto-aprueba y ejecuta, dejando constancia de la decisión en el plan.
- **Copia en bloque vía `rclone rcd` (Paso 4, `scripts/copiar_manifiesto_rclone.py`):**
  para casos Drive-residentes (Modo 1/3) con client OAuth propio del despacho
  configurado, evita el reinicio del "pacer" de cuota de invocar `rclone.exe`
  una vez por fichero (medido: 110s/6 reintentos `403 Quota exceeded` con el
  cliente compartido). Sin ese prerrequisito, sigue la copia secuencial de
  siempre. Verificado en vivo (W-02VUDR, `gdrive_tl`): 10/10 ficheros
  server-side, 0 `403`.
- **Fase verify con criterios duros (Paso 6.5, `scripts/verificar_sala.py`):**
  contrasta `_MANIFIESTO.md` contra lo realmente copiado en disco antes de
  reportar éxito — fila sin fichero, fichero sin fila, anexo con `parent_id`
  huérfano. Nunca arregla, solo detecta y obliga a listar problemas.
- Disparador: medido en vivo en la apertura de W-02VUDR — 14 min de
  clasificación + 30+ min de copia+índices sobre 172 documentos. Plan:
  `docs/superpowers/plans/2026-07-21-preclasificacion-sala-lectura.md`.
- Taxonomía, bundles, modos de acceso, re-aplicación: sin cambios de fondo
  (salvo la sub-agrupación de "07" en `INDICE.md` arriba).

## 1.8 — 2026-07-19
- **Migración al MCP consolidado `expedientes-xl`** (server viejo `expedientes` /
  `server-filesystem` Node jubilado). El acceso pasa de dos a **tres modos** por ubicación
  del caso: (1) **Drive vía `expedientes-xl`** (`copy_path`/`copy_dir`/`hash_path`/`read_text`/
  `write_text` server-side; copia binarios sin pasar bytes por el modelo → Cowork-en-PC es
  constructor completo, no solo texto); (2) **local-nativo** (caso en ruta local del PC fuera
  de `G:`/`H:`, p. ej. tras `checkout-caso`: filesystem del entorno — nativo en Claude Code,
  montaje bash en Cowork); (3) **conector nube**, prefiriendo `google-despacho` (Drive
  multicuenta, ve el Drive del despacho y copia server-side) sobre el conector nativo (que en
  Cowork es cuenta E&V y no ve el Drive del despacho).
- **`read_media_file` retirado:** los binarios ya no vuelven al modelo (no hay visión
  directa). La clasificación de binarios opacos se apoya en nombre + metadata + espejo MD de
  la sala de máquina; lo dudoso → `08. PENDIENTE DE CLASIFICAR`.
- **Retirada la doctrina "binarios solo por motor local"**: el "único residuo" de volcado
  local desaparece (los tres modos copian binarios server-side/nativo). Cierra `MEJORAS #40`.
- Tools MCP citadas con nombre cualificado `servidor:tool` (checklist de autoría §8).
- Clasificación, taxonomía, gate único, índices, catálogo y bundles: **sin cambios**.

## 1.7 — 2026-07-18
- **Fix de compatibilidad Cowork:** `<fuente>` en la `description` (placeholder con ángulos)
  hacía que claude.ai rechazara la importación («SKILL.md description cannot contain XML
  tags») → reescrito como «lotes por fuente». Solo texto del frontmatter; sin cambios de
  comportamiento.

## 1.6 — 2026-07-18
- **Reclasificación de `rol`: `output` → `procesado`.** La skill organiza el intake en la sala
  de lectura (artefacto interno), no produce un entregable jurídico. Se estrena el rol
  `procesado` del eje de pipeline de datos del expediente. Taxonomía a revalidar con el grafo de
  ecosistema (`docs/MEJORAS_FUTURAS.md` #50). Sin cambios de comportamiento.

## 1.5 — 2026-06-22
- **Anexos de WhatsApp con fecha de ENVÍO, no de la carpeta madre**: cada adjunto del
  chat se fecha por el `[DD/MM/AAAA, HH:MM]` del mensaje del `_chat.txt` que lo referencia
  (`‎<adjunto: …>` iOS / `… (archivo adjunto)` Android), regla que prevalece sobre la
  jerarquía general (a)–(c) para anexos de WhatsApp. Antes todos los anexos heredaban la
  fecha del chat (la del principal). Aviso explícito: la fecha de **envío** (chat.txt) ≠ la
  **incrustada en el nombre** (`PHOTO-2024-10-30…` = fecha de **captura**); el nombre solo es
  fallback marcado `(*)` cuando el adjunto no aparece referenciado en el `_chat.txt`.
- **Nombrado de bundles**: el prefijo `AAAA-MM-DD` de cada anexo es su propia fecha (distintos
  anexos del mismo bundle pueden llevar fechas distintas); la pertenencia al bundle la
  preserva la subcarpeta + `parent_id`/`orden`, no el prefijo de fecha. Carpeta y principal
  siguen fechándose por el inicio del documento (en WhatsApp, la fecha del chat).

## 1.4 — 2026-06-22
- **Dos modos de acceso a ficheros** (nueva sección "Modos de acceso"), elegidos en el
  Paso 0: **local** (MCP de filesystem `expedientes` sobre el Drive montado en disco,
  `G:/…/CASOS/<caso>/`) **preferente**, y **conector** de Drive como **fallback** (Cowork
  puro-nube / PC sin montaje). Motivo: el conector es per-fichero (una corrida real tardó
  ~53 min); el modo local lee a velocidad de disco. Verificado que Cowork (Claude Desktop
  en el PC con el montaje) alcanza el MCP local.
- **Paso 0**: intenta primero el MCP local (ToolSearch por sus tools); identifica el caso
  por **nombre de carpeta** (resuelto bajo `CASOS/`) **o** por **ruta `G:/…` completa**. Si
  el MCP no está, cae al conector (URL + "Permitir siempre", como antes).
- **sha256 real en modo local**: lee los bytes directamente (cierra el gotcha del `md5` del
  conector). En modo conector se mantiene la salvedad: calcular sha256 de los bytes, no usar
  el md5.
- **Copia** según modo (tools del MCP en local; server-side en conector) y **enlaces** de la
  propuesta según modo (`viewUrl` en conector; ruta relativa en local).
- Clasificación, taxonomía, gate único, índices, catálogo y bundles: **sin cambios**.

## 1.3 — 2026-06-18
- **Alcance ampliado a TODO `00_Input`**: lee las seis fuentes (`01_Drive EV`,
  `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`, `06_Entrevistas`); antes
  solo `01_Drive EV`.
- **Salida PLANA**: `01_Procesado/Sala lectura/` (antes `Sala lectura Drive EV/`
  con subcarpetas por categoría). La categoría vive en `INDICE.md`, no en
  carpetas.
- **Paso 0 (bloqueante)**: carga el conector de Drive vía ToolSearch, acepta URL
  del expediente o de subcarpeta de `00_Input`, y solicita "Permitir siempre"
  para cero diálogos durante la ejecución.
- **Documentos compuestos (bundles)**: WhatsApp, `.eml` y lotes CRM agrupados en
  subcarpeta fechada (`AAAA-MM-DD_descripcion/`); sueltos solo si hay convención
  `_anexo_N` o PDF troceado.
- **Fecha por jerarquía del cuerpo**: (a) otorgamiento/firma → (b) fecha del
  contenido → (c) nombre del fichero → (d) `0000-00-00`; `mtime` solo como
  aproximación marcada `(*)`.
- **Índices**: `INDICE.md` (por categoría, fecha DESC) + `CRONOLOGIA.md` (ASC;
  sin-fecha al final) + `_MANIFIESTO.md` (tabla sha256 + metadatos por fila;
  cabecera GENERADO).
- **Catálogo `indice_documental.yaml`** derivado por el helper
  `scripts/manifiesto_a_catalogo.py` (el LLM NO escribe YAML). SSOT máquina.
- **Taxonomía DRY desde el canon**: `references/taxonomia_ev.md` generado por
  `scripts/sync_taxonomia_skills.py` desde `core/config.py::TAXONOMIA_EV` +
  `data/_prompts/criterio_clasificacion_ev.md`; gate anti-drift en
  `check_skills.py`.
- **Nota de modelo**: ejecútese con Sonnet o Haiku; no requiere Opus.

## 1.2 — 2026-06-18
- Nombre canónico **sin slug de tipo**: `AAAA-MM-DD_descripcion.ext` (el tipo ya lo
  indica la carpeta canónica → el slug era redundante en la disposición por tipo).
  Solo afecta a esta skill; el motor local (`core/`, disposición por fuente) conserva
  el slug a propósito (allí sí informa). Verificado: el slug era decorativo, sin
  acoplamientos funcionales.

## 1.1 — 2026-06-18
- Enrutado de identidad/PBC **por parte**: vendedor → `01. ACTIVACIÓN`; comprador →
  `03. OFERTAS` (subcarpeta por oferta si hay varias). `06. PBC` sobrevive **solo**
  para los Anexos 1 y 2 del vendedor (ya no es el cajón genérico de identidad).
- **Gate humano único (Paso 2.5):** propuesta visual (tarjeta/HTML) antes de copiar,
  con panel "requiere tu visto bueno" y enlace al original por fila; ejecuta solo tras OK.
- **Autonomía:** sin preguntas de permiso por-fichero; el diálogo por-llamada es ajuste
  del cliente Cowork. Un solo gate (la propuesta).
- **Enlaces:** la propuesta enlaza al original; los índices, a la copia canónica.
- **Re-aplicación solo-añade:** al re-correr (goteo de intake), compara por sha256,
  salta lo ya copiado y conserva la clasificación previa de lo conocido; **nunca
  borra**. Cambio de reglas de clasificación = vaciado manual + recorrido limpio.
- (Slug de tipo en el nombre canónico: verificado que es decorativo; decisión de
  quitarlo pendiente de OK, no aplicada.)

## 1.0 — 2026-06-18
- Versión inicial. Lee `00_Input/01_Drive EV/` y copia (no destructivo) a
  `01_Procesado/Sala lectura Drive EV/` con taxonomía E&V, nombres canónicos e
  INDICE/CRONOLOGIA/manifiesto. Salida fuera de `00_Input` (no se re-ingiere ni la
  pisan los re-pulls). Alcance: solo `01_Drive EV`. Taxonomía alineada al canónico
  `TAXONOMIA_EV` (incluye `08. PENDIENTE DE CLASIFICAR`). El `_MANIFIESTO.md` guarda
  **sha256** (de los bytes, no el md5 del conector) + ruta original por documento,
  para dejar abierto el puente de reconciliación con el catálogo único.
