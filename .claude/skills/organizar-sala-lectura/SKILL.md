---
name: organizar-sala-lectura
description: >-
  Organiza el intake de un expediente FeesDefender en una "sala de lectura"
  legible: lee TODO 00_Input (01_Drive EV, 02_Whatsapp, 03_Email, 04_Manual,
  05_CRM, 06_Entrevistas; excluye 90_Notas personales), clasifica cada fichero
  por las categorías canónicas de Engel & Völkers (activación, ofertas, arras,
  facturación, PBC, reclamaciones, fotos, pendiente de clasificar), presenta una
  propuesta para tu visto bueno y, tras aprobarla, los copia con nombre canónico
  AAAA-MM-DD_descripcion a 01_Procesado/Sala lectura, en estructura PLANA (la
  categoría vive en INDICE.md, no en carpetas; los documentos compuestos van en
  subcarpeta fechada), sin tocar el crudo, más INDICE.md, CRONOLOGIA.md,
  _MANIFIESTO.md e indice_documental.yaml. Úsala cuando el usuario diga "organiza
  esta carpeta", "ordena el intake", "monta la sala de lectura", "prepara los
  ficheros para leer" de un caso. NO valora viabilidad (eso es triaje-viabilidad)
  NI genera el informe formal (eso es viabilidad-prerelleno) NI mueve/borra el
  crudo.
metadata:
  rol: output
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.5"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# organizar-sala-lectura

Convierte el intake de un expediente FeesDefender (desordenado, de todas las
fuentes de `00_Input`) en una **sala de lectura ÚNICA y plana**: documentos con
nombre canónico `AAAA-MM-DD_descripcion`, clasificados por las categorías canónicas
de E&V **en `INDICE.md`** (no en carpetas), más índices de navegación y un catálogo
máquina. Es el **único constructor** de la sala (el camino de sala del motor local
quedó deprecado). Corre en claude.ai/Cowork o en Claude Code local, por **dos modos de
acceso** (ver "Modos de acceso"): **local** (MCP de filesystem sobre el Drive montado en
disco — rápido) o **conector** de Drive (nube — fallback), sin instalar nada. **No
destructivo: copia, nunca mueve ni borra el crudo.** Presenta **una propuesta para tu
visto bueno** antes de copiar nada.

## Cuándo se activa

- Disparadores: «organiza esta carpeta», «ordena el intake», «monta la sala de
  lectura», «prepara los ficheros para leer», «esta carpeta de Drive está hecha un lío».

**NO se activa cuando:**

- Hay que **valorar la viabilidad** del caso → `triaje-viabilidad`.
- Hay que producir el **informe formal de viabilidad** → `viabilidad-prerelleno`.

**Modelo:** ejecútese con **Sonnet o Haiku** (clasificación atómica + visto bueno
humano); **no requiere Opus**. El grueso de la velocidad lo da el skip incremental
por `sha256` (la 2ª pasada solo toca lo nuevo).

## Entrada y montaje

- Trabaja sobre el **expediente en el Drive del despacho** (no el de Engel).
- **Lee** de **TODO `00_Input/`** (`01_Drive EV`, `02_Whatsapp`, `03_Email`,
  `04_Manual`, `05_CRM`, `06_Entrevistas`), **excluyendo `90_Notas personales`**
  (zona del abogado: ningún módulo la lee ni la escribe).
- **Escribe** en `01_Procesado/Sala lectura/`. Cowork debe tener montada la **raíz
  del expediente** (la salida vive fuera de `00_Input`).

## Modos de acceso

La skill accede a los ficheros por uno de dos modos, decidido en el **Paso 0**. **Prefiere
SIEMPRE el local si está disponible** (≈velocidad de disco; el conector es per-fichero y
puede tardar decenas de minutos en un expediente grande).

- **Modo local (preferente):** MCP de filesystem `expedientes` sobre el Drive del despacho
  montado en disco, acotado a `G:/Unidades compartidas/EXPEDIENTES - TYUKHAY LEGAL/`. Los
  casos cuelgan de `CASOS/<ciudad>/<caso>/` (subdivididos por ciudad: Barcelona, Madrid…).
  Disponible cuando ese MCP está conectado (Claude Code local, o Cowork en un PC con el
  montaje y el server en `claude_desktop_config.json`). Lee bytes → **sha256 real**. Se le
  indica el caso por **nombre de carpeta** (lo resuelve buscando bajo `CASOS/`) **o** por
  **ruta `G:/…` completa** pegada. **Copia — límite por entorno (ver Gotchas):** en Claude
  Code local copia binarios con el filesystem real (`shutil`); en Cowork el MCP `expedientes`
  (`server-filesystem`) **solo escribe TEXTO** (índices, `.md`/`.txt`/`.yaml`) — `write_file`
  no es binario y no hay `copy_file`, `move_file` es destructivo. Desde Cowork, por tanto,
  **la copia de binarios (PDF, fotos, vídeos, `.xlsx`) la hace el motor local**; Cowork solo
  amplía la sala en texto.
- **Modo conector (fallback):** conector de Drive (nube). Único camino en Cowork puro-nube
  (móvil/navegador) o en PC sin el montaje. Trabaja con `folderId`/URL; el conector da
  `md5` (no sha256 — ver Gotchas) y copia server-side. **Aviso:** el `copy_file` server-side
  solo escribe binarios si el conector apunta a la **Drive del despacho**; el conector de E&V
  (`@engelvoelkers.com`) NO la ve y no puede escribir en la sala (ver Gotchas).

Todo lo demás (clasificación, taxonomía, gate, índices, catálogo, bundles) es **idéntico**
en ambos modos.

## Por qué fuera de 00_Input

`00_Input/` es zona de intake: el pipeline confidencial la escanea entera
(`inventory.scan` hace `rglob` sobre `00_Input`) y los re-pulls del Drive de Engel
la sobrescriben. Si la sala viviera ahí, las copias se re-ingerirían como intake
nuevo (duplicados, re-OCR) y un re-pull las pisaría. Por eso la salida va a
`01_Procesado/`.

## Qué produce

```
<Expediente (Drive del despacho)>/
├── 00_Input/                       ← crudo (todas las fuentes), NO se toca
└── 01_Procesado/
    └── Sala lectura/
        ├── INDICE.md · CRONOLOGIA.md · _MANIFIESTO.md · indice_documental.yaml
        ├── AAAA-MM-DD_descripcion.ext                 (documento suelto)
        └── AAAA-MM-DD_descripcion/                    (documento compuesto)
            ├── AAAA-MM-DD_descripcion.ext             (principal)
            └── AAAA-MM-DD_descripcion_anexo_N_x.ext   (anexos)
```

Estructura **PLANA**: la categoría E&V vive en `INDICE.md`, no en carpetas (ver
`references/taxonomia_ev.md` para el set cerrado y los criterios).

## Autonomía y gate único

La skill **no inserta preguntas de aclaración** ni pide permiso fichero a fichero.
Tiene **un solo gate humano**: la propuesta del Paso 2.5. Tras tu OK, ejecuta todo de
una pasada **sin más preguntas**. Por defecto asume autorización para crear y copiar
en `01_Procesado/Sala lectura/` (el crudo de `00_Input` no se toca ni se borra;
siempre **copia**). En **modo conector**, el diálogo de permiso por-llamada se neutraliza
en el **Paso 0** ("Permitir siempre"), no en la skill; en **modo local** no hay tal
diálogo.

## Procedimiento

0. **Montaje (bloqueante). Elige modo (ver "Modos de acceso"):**
   - **Intenta primero el modo local:** comprueba si el MCP `expedientes` está disponible
     (ToolSearch por sus tools de filesystem). Si lo está, **úsalo**. Resuelve el
     expediente desde lo que dé el usuario: **ruta `G:/…` completa** pegada → úsala; **solo
     el nombre del caso** → búscalo bajo `G:/Unidades compartidas/EXPEDIENTES - TYUKHAY
     LEGAL/CASOS/` (subdividido por ciudad: `CASOS/<ciudad>/<caso>/` — lista las ciudades y
     casa el nombre; no asumas profundidad fija). Baja a `00_Input/`. En local **no hay
     diálogo de permiso del conector**.
   - **Si el MCP local NO está:** cae al **modo conector**. Carga el conector de Drive
     (ToolSearch). Acepta una URL de carpeta pegada: resuelve `folderId` y DETECTA nivel —
     raíz del expediente → baja a `00_Input/`; subcarpeta de `00_Input` → úsala. Pide
     activar **"Permitir siempre"** en el conector (CERO diálogos durante la ejecución).
   - Disparadores: "organiza esta carpeta <nombre|ruta G:|url>".
1. **Lista** **TODO `00_Input/`** (`01_Drive EV`, `02_Whatsapp`, `03_Email`,
   `04_Manual`, `05_CRM`, `06_Entrevistas`), **excluyendo `90_Notas personales`**. Para
   cada fichero, calcula **sha256** de los bytes (modo local: lee los bytes; modo conector:
   ver Gotchas) y **salta** (sin leer ni copiar) lo que ya conste en `_MANIFIESTO.md` (ver
   "Re-aplicación").
2. **Clasifica cada fichero NUEVO** leyendo su contenido:
   - **Categoría** — una de las 8 de `references/taxonomia_ev.md`. La **identidad/PBC se
     enruta POR PARTE**: vendedor → `01. ACTIVACIÓN` (con los Anexos 1 y 2 del vendedor a
     `06. PBC`); comprador → `03. OFERTAS`. Lo ambiguo o ilegible →
     `08. PENDIENTE DE CLASIFICAR`, **nunca se fuerza**.
   - **Fecha por la jerarquía del canon:** (a) otorgamiento/firma en el cuerpo → (b) otra
     fecha inequívoca del contenido → (c) fecha del nombre del fichero → (d) `0000-00-00`.
     `mtime` **no** es fuente; si se usa como aproximación, márcala `(*)` en
     `CRONOLOGIA.md` y `_MANIFIESTO.md`.
   - **Anexo de WhatsApp — fecha de ENVÍO (no de la carpeta madre):** cada adjunto del
     chat lleva la fecha del **mensaje del `_chat.txt` que lo referencia** — la línea
     `‎<adjunto: <fichero>>` (iOS) o `<fichero> (archivo adjunto)` (Android), cuyo
     `[DD/MM/AAAA, HH:MM]` es la fecha de envío. Esta regla **prevalece** sobre (a)–(c)
     para los anexos de WhatsApp: NUNCA heredan la fecha del chat ni la del principal.
     ⚠️ No confundir con la fecha **incrustada en el nombre** del adjunto (`PHOTO-2024-10-30…`,
     `VIDEO-2024-11-29…`): esa es la de **captura** del medio, no la de envío. Fallback
     solo si el adjunto **no** aparece referenciado en el `_chat.txt`: (i) fecha incrustada
     en el nombre, marcada `(*)`; (ii) fecha del chat, marcada `(*)`.
   - **Descripción** ≤50 car., minúsculas, **guiones_bajos**, **sin PII**.
   - **Bundle:** detecta si el fichero es parte de un documento compuesto (ver
     "Documentos compuestos").
   No copies nada todavía.
3. **(Paso 2.5 — GATE) Presenta la propuesta y ESPERA.** Renderiza la propuesta
   visual (ver abajo) y **espera confirmación**. Si piden ajustes, reclasifica y vuelve
   a presentar. **Solo con OK explícito** pasas al paso 4.
4. **(tras OK) Ejecuta de una pasada (PLANO):** **copia** cada fichero a
   `01_Procesado/Sala lectura/` (raíz) con **nombre canónico**
   `AAAA-MM-DD_descripcion.ext`; los documentos compuestos a su **subcarpeta fechada**
   `AAAA-MM-DD_descripcion/`. Copia según el modo: **local** con las tools de escritura del
   MCP `expedientes`; **conector** con la copia server-side de Drive. **Guarda de colisión:**
   si el nombre destino ya se usó en la corrida, añade sufijo `_2`/`_3`. Sin más preguntas.
5. **Escribe los índices** en `01_Procesado/Sala lectura/`:
   - `_MANIFIESTO.md` — tabla por documento, una fila por fichero, columnas:
     `sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id`. El
     `sha256` se calcula de los bytes (el `md5` de Drive NO sirve: la traza del caso
     llavea por sha256). `parent_id` agrupa los anexos de un bundle bajo su principal.
   - `INDICE.md` — agrupado **por categoría** (la categoría vive aquí, no en carpetas),
     orden **fecha DESCENDENTE**; cada entrada enlaza a la copia plana + nombre original.
   - `CRONOLOGIA.md` — por fecha **ASCENDENTE**; `0000-00-00` y fechas `(*)` al final.
   Los tres con cabecera `<!-- GENERADO — NO EDITAR A MANO -->`.
6. **Deriva el catálogo:** ejecuta
   `scripts/manifiesto_a_catalogo.py _MANIFIESTO.md indice_documental.yaml` (el LLM **NO**
   escribe el YAML). Es la SSOT máquina.
7. **Reporta:** nº por categoría, nº a `08. PENDIENTE DE CLASIFICAR`, bundles formados,
   duplicados saltados.

## Documentos compuestos (bundles)

Un documento con anexos = una SUBCARPETA fechada con el principal + sus anexos. Se
agrupan SOLO con señal determinista:

- **WhatsApp:** chat + su `media/` (estructura del export).
- **Email `.eml`:** cuerpo (principal) + adjuntos MIME.
- **CRM:** clúster por subida en lote (mejor esfuerzo; desde Cowork puede degradarse a
  plano si no hay `modified_at`).
- **Sueltos (Drive/Manual):** solo si hay convención `_anexo_N` o un PDF troceado; si no
  → plano. Nunca inventar bundles.

Nombre: carpeta `AAAA-MM-DD_descripcion/`; principal `AAAA-MM-DD_descripcion.ext`; anexos
`AAAA-MM-DD_descripcion_anexo_N_x.ext`. `parent_id`/`orden` van al `_MANIFIESTO.md`.
La carpeta y el principal se fechan por el inicio del documento (en WhatsApp, la fecha
del chat); **el `AAAA-MM-DD` de cada anexo es su PROPIA fecha** (en WhatsApp, la de envío
del mensaje que lo adjunta — ver la jerarquía de fecha arriba), por lo que distintos
anexos del mismo bundle pueden llevar fechas distintas. La pertenencia al bundle la
preserva la subcarpeta + el `parent_id`/`orden` del `_MANIFIESTO.md`, no el prefijo de fecha.

## Propuesta visual (Paso 2.5)

Tarjeta visual (artefacto HTML; *fallback* markdown compacto), **no un muro de texto**:

a. **Cabecera:** caso + fuentes leídas (todas las de `00_Input`) + aviso «nada copiado
   aún».
b. **Contadores** por categoría con su nº.
c. **Panel "Requiere tu visto bueno":** SOLO decisiones a revisar — reclasificaciones
   no obvias, identidad/PBC enrutada por parte (y Anexos 1/2 → `06. PBC`), bundles
   propuestos, duplicados sha256, ficheros sin fecha (`0000-00-00`/`(*)`), docs a
   `08. PENDIENTE` con motivo, doc(s) destacado(s). 1 línea/icono.
d. **Listado por fecha DESCENDENTE:** una línea por documento
   `fecha · nombre-canónico · [categoría]` (la categoría es etiqueta, no carpeta).
   **Cada fila identifica el ORIGINAL** para revisar antes de aprobar: modo conector →
   enlace `viewUrl` de `00_Input/…`; modo local → **ruta relativa** del original bajo el
   caso (no hay `viewUrl`).
e. **Botones:** «Aprobar y ejecutar» / «Quiero ajustar algo».

Regla de enlaces: en la **propuesta** se apunta al **original** (enlace o ruta según modo);
en los **índices** (tras ejecutar) se enlaza a la **copia canónica**.

## Re-aplicación (solo añade; nunca borra)

La skill se re-corre cada vez que entran documentos nuevos a `00_Input` (p. ej. antes
de preparar la demanda). En cada re-corrida:

- **Solo añade.** Compara por **sha256**: lo ya copiado se salta; solo se clasifican y
  copian los documentos **nuevos**. Reporta qué saltó.
- **Conserva la clasificación previa** de los documentos ya conocidos (por sha256,
  según el `_MANIFIESTO.md`): NO los re-clasifica, para que la sala no "baile" entre
  corridas por la varianza del modelo.
- **Nunca borra.** No elimina copias antiguas ni nada de la sala (riesgo en Drive
  compartido + el conector puede no soportar borrado). El crudo de `00_Input` jamás se
  toca.
- **Cambio de reglas de clasificación** (p. ej. nueva taxonomía): es el ÚNICO caso que
  deja copias obsoletas. **No se automatiza** — vacía a mano
  `01_Procesado/Sala lectura/` (el crudo está intacto) y re-corre desde cero.

## Gotchas

- **Identidad/PBC por parte:** no mandes la identidad a `06. PBC` por defecto;
  vendedor → `01. ACTIVACIÓN`, comprador → `03. OFERTAS`. `06. PBC` sobrevive **solo**
  para los Anexos 1 y 2 del vendedor. La parte se decide **leyendo** el documento.
- **sha256, no md5:** el `_MANIFIESTO.md` guarda el sha256 de los bytes. En **modo local**
  se leen los bytes directamente → sha256 real. En **modo conector**, el conector da `md5`
  (que NO casa con la traza del caso); calcula sha256 descargando los bytes, no uses el md5.
- **Sin PII en nombres:** revisa la `descripcion` antes de copiar.
- **Estructura plana:** la categoría vive en `INDICE.md`, **no** en carpetas. La sala es
  un único directorio; solo los documentos compuestos abren subcarpeta fechada.
- **Carpeta enorme:** avisa y procesa por lotes; deja constancia de lo cubierto.
- **Copia de binarios desde Cowork = NO (usa el motor local):** el MCP local `expedientes`
  (`@modelcontextprotocol/server-filesystem`) **no copia binarios** — `write_file` es solo
  texto (UTF-8), no hay `copy_file` y `move_file` es destructivo; volcar `read_media_file`
  (base64) con `write_file` corrompe. El conector de Drive en la nube de Cowork es la cuenta
  **E&V** (`@engelvoelkers.com`), que NO ve la Drive del despacho «EXPEDIENTES - TYUKHAY
  LEGAL», así que su `copy_file` tampoco escribe en la sala. **Conclusión:** desde Cowork la
  sala solo crece en TEXTO (índices, `.md`/`.txt`/`.rtf`, transcripciones); los **binarios**
  (PDF, fotos, vídeos, `.xlsx`) los copia el **motor local** (Claude Code/Python sobre `G:`).
  Para volver Cowork constructor completo: dar copia binaria al MCP `expedientes` (backlog en
  `docs/MEJORAS_FUTURAS.md`). Confirmado en BaRS1/Tibidabo, 2026-06-22.
