# EXPLORACIÓN PRE-BRAINSTORMING — Reorganización de la capa «procesado → sala de lectura» + pipeline de email

> Documento de exploración (NO decisiones). Autor: agente de arquitectura. Fecha: 2026-07-19.
> Repo: worktree `el-contable-handoff-eccc1b`, rama `claude/mcp-drive-disco-fase-2-efc0bc`.
> Destino: brainstorming dialógico posterior con Nikolai. Todo anclado a `fichero:línea` o §spec.

---

## 1. Resumen ejecutivo

**Hallazgo principal (H1.1): NO hace falta una arquitectura nueva. La "sala de lectura consumidora
de la capa procesado" es la MATERIALIZACIÓN a nivel-fichero de una frontera que ya está diseñada
(Cronología Unificada §9 / Motor Documental #48) y de unas fuentes fiables que YA ESTÁN CONSTRUIDAS.**
Los dos atomizadores por fuente existen y están mergeados (`core/email_atomize/` con Capa A + Capa B
inline; `core/whatsapp_atomize/`), y la sala de máquina (`core/sala_maquina.py`) ya emite el MD con la
señal de fiabilidad (`ocr_quality`) en el frontmatter. Lo que falta no es diseño de arquitectura sino
**(a)** el contrato de consumo a nivel-fichero (la Cronología diseñó el de nivel-ACTO, que es otra capa);
**(b)** el cableado (hoy nadie encadena atomize→sala; #68) y **(c)** cuatro decisiones-frontera acotadas.

**Recomendación global de enfoque:**
1. **Un solo spec acotado** de "capa procesado → sala de lectura (nivel FICHERO)", explícitamente
   **desacoplado** de la Cronología Unificada (nivel ACTO) y con **dependencia BLANDA** del registro
   único #48 (que está APARCADO): leer los MD donde existan, caer a crudo si no. No arrastrar el build
   de la sala a la Cronología (riesgo real de acoplar dos proyectos y no entregar ninguno).
2. **La sala de lectura consume la VISTA HUMANA de cada atomizador** (`CORREOS_LECTURA.md`,
   `<chat>__LECTURA.md`) + el `03_MD` de la sala de máquina — **no** un `.md` por mensaje atómico
   (eso reventaría el listado plano; el propio atomizador de WhatsApp ya rechazó el grano-mensaje).
3. **Un solo motor de OCR para los adjuntos**, no un cuarto camino: el dueño de la *orquestación* del
   texto de adjuntos es `email_atomize`/`adjuntos_contenido` (ya tiene el adjunto deduplicado y sabe el
   bundle), pero el *motor* debe ser el compartido (OCRmyPDF de la sala de máquina), no el Docling que
   usa hoy `adjuntos_contenido`.

**Las 3-5 preguntas más importantes para Nikolai** (detalle en §7):
- **P1 (la gorda):** ¿Skill prompt-driven que consume MD (#75) **o** revivir `core.sala_lectura`
  determinista + tool MCP (#56)? Son dos visiones vivas y algo enfrentadas; condicionan todo lo demás.
- **P2:** Granularidad del email en la sala (H1.3): ¿unidad = hilo/`.eml` legible, o mensaje atómico?
- **P3:** ¿El build de la sala de lectura depende del registro único #48 (hoy APARCADO) o lee los MD
  dispersos directamente (dependencia blanda)?
- **P4:** OCR de adjuntos de correo (H1.4): ¿se construye la "fase 2" de `email_atomize`/reusa
  `adjuntos_contenido`, y con qué motor (unificar en OCRmyPDF)?
- **P5:** ¿`read_media_file`/#76 entra o no en el piloto? (Recomendación: NO; es otro caso de uso.)

**Ruta del documento:** este fichero.

---

## 2. Contexto consolidado (Fase 0) — qué produce cada pieza, dónde, con qué contrato

### 2.1 Estado REAL del código (ojo: los specs van por detrás del código)

Aviso de rigor: varias afirmaciones del handoff §2 están escritas como aspiracionales cuando en realidad
**ya están construidas**. Anclas:

| Pieza | Estado real | Salida / contrato | Ancla |
|---|---|---|---|
| **`core/email_atomize/`** Capa A | CONSTRUIDA, mergeada, corrida en vivo (277 msgs W-02VND1) | `01_Procesado/Emails/mensajes/*.md` (1 por mensaje atómico, `MSG-NNNNN`), `adjuntos/` dedup sha256 + ficha, `corpus.jsonl`, `_registro.json`, `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md` | `pipeline.py:62-164`; PLAN.md:270-273 |
| **`core/email_atomize/` Capa B (inline)** | CONSTRUIDA (contra lo que dice el spec base "fase 2 a construir") | `inline.py`, `_segmenter.py`; autoría enterrada, `capa: B`, cola `_revision/`; +89 Capa B alta en vivo | `pipeline.py:167-212`; PLAN.md:274-283 |
| **`core/email_atomize/` Fase 3 (caso)** | CÓDIGO COMPLETO en `origin/main` | `identidades.py`, `vistas.py` (dossiers temáticos), `entregas.py` (sellado) | `pipeline.py:24,141,299-303`; PLAN.md:284-288 |
| **`core/whatsapp_atomize/`** | CONSTRUIDA, mergeada, en vivo (4 chats, 2087 msgs BaRS1) | `01_Procesado/Whatsapp/`: `<chat>__LECTURA.md` numerado (`MSG-NNNNN`), `enterrados/MSG-*.md`, adjuntos dedup, `corpus.jsonl`, `_registro.json`, `CRONOLOGIA.md` cross-chat | `git 578e555`; spec `2026-06-25-whatsapp-atomize-design.md:17-33` |
| **`core/sala_maquina.py`** | CONSTRUIDA | `01_Procesado/02_Sala de máquina/{01_OCR,03_MD,raw_text}` + `_revisar/_cobertura.md`; MD con frontmatter `ocr`,`ocr_quality`,`chars`,`text_sha256` | `sala_maquina.py:357-369` (`_escribir_md`), `86-100` (`ocr_quality`) |
| **`core/adjuntos_contenido/`** | CONSTRUIDA (LLM=NO-OP) | lee `emails_out_dir/adjuntos`, escribe `<base>.contenido.md` con caché sha256; texto por `extractor._extract_one` (Docling), imágenes ≥50KB → cola visión "pendiente" | `pipeline.py:11-13`, `router.py:16-45` |
| **`organizar-sala-lectura` (skill v1.8)** | CONSTRUIDA; re-procesa el crudo (MD solo apoyo condicional) | `01_Procesado/Sala lectura/` plana + `INDICE.md`/`CRONOLOGIA.md`/`_MANIFIESTO.md`/`indice_documental.yaml` | `SKILL.md:169-176` |
| **Cronología Unificada** | **DISEÑO COMPLETO (8 fases), NO construida** | prevista `01_Procesado/Cronologia/`; nivel ACTO | spec v7 completo; PLAN.md:333-341 |
| **Motor Documental #48 (registro único)** | **APARCADO 2026-07-04**, diseño de referencia | previsto `_indice_documental.yaml` ámbito-caso + `01_Sala de lectura`/`02_Sala de máquina` | `PLAN_MOTOR_DOCUMENTAL.md:13-17` (aparcado), §H |

**Consecuencia:** las "fuentes fiables por tipo" que #75 da por decididas **ya producen artefactos hoy**.
El brainstorming NO tiene que diseñar fuentes; tiene que diseñar el **consumo**.

### 2.2 El mapa de capas (para no confundir niveles)

Hay **tres niveles** que el proyecto ya separa conceptualmente y que NO deben fundirse:

1. **Nivel FICHERO** — la sala de lectura. "Documentos con nombre que habla, ordenados por fecha, que el
   abogado lee." Contrato: 1 fila por fichero/bundle, categoría E&V, fecha, `_MANIFIESTO`. (spec
   `2026-06-18-sala-lectura-unica`; #56 dice explícito "el esqueleto es cronológico, no por categoría",
   MEJORAS #56:2243-2245).
2. **Nivel MENSAJE/ÁTOMO** — los atomizadores (email, whatsapp). Contrato: `MSG-NNNNN` congelado por
   contenido, dedup intra-fuente, vista humana + `corpus.jsonl` de máquina.
3. **Nivel ACTO** — la Cronología Unificada. Contrato: `EVT-NNNNN`, correlación inter-fuente (no fusión),
   grafo de enlaces, capa derivada de hechos. Spec §1.1-1.2, §9.

La Cronología es **explícita** en que vive "por encima de `organizar-sala-lectura` (nivel fichero)…; no
los duplica" (spec §0 / §9 F5.D2: `CRONOLOGIA_FICHEROS` vs `CRONOLOGIA_ACTOS`, spec línea 346). Es decir:
**la sala de lectura y la Cronología son consumidores HERMANOS de los mismos atomizadores, a niveles
distintos.** La sala NO es "el primer consumidor de la Cronología"; es el consumidor a nivel-fichero.

### 2.3 El cableado que falta (por qué esto no es "solo reordenar")

- La sala de máquina **solo lee `00_Input/`** (`sala_maquina.py:485`, `inventariar`) y trata el `.eml`
  como nativo grueso → **1 MD por `.eml`** (`_NATIVO_EXTRACTORES = {".eml": _try_email, ...}`,
  `sala_maquina.py:254`). No recorre adjuntos MIME (MEJORAS #55:2212-2214).
- `email_atomize` escribe en `01_Procesado/Emails/`, que la sala de máquina **no lee** (#55:2215-2217).
- Nadie encadena `atomize` en el flujo: ni `abrir_caso` ni `organizar-sala-maquina` lo invocan; el intake
  exporta con `extract_attachments=False` (#68.a:2616-2621).
- `adjuntos_contenido` sí lee la salida de `email_atomize`, pero con **otro motor** (`_extract_one`
  Docling, `router.py:36`) distinto del OCRmyPDF de la sala de máquina → reaparece el "tres motores
  desacoplados" de #48 B.1.

---

## 3. Decisiones-frontera (Fase 1) — H1.1 a H1.4

### H1.1 — ¿Pieza NUEVA o materialización de lo ya diseñado? **[EMPEZAR AQUÍ]**

**Conclusión: MATERIALIZACIÓN, no arquitectura nueva.** Desglose del solapamiento:

**Qué YA define la Cronología Unificada (spec v7) que la sala reutiliza — pero a otro nivel:**
- La **frontera de 3 capas** ATOMIZADOR / ADAPTADOR / NÚCLEO AGNÓSTICO (§9.1, F5.D1). El atomizador es
  "dueño de los bytes y de las rarezas del formato… convierte el crudo en átomos con clave natural
  estable" (spec:325). Esto ya está construido (email + whatsapp).
- El principio "**anclar al crudo; sala de lectura solo como PISTA**" (§9.2, spec:341): la Cronología
  ancla al crudo de `00_Input`+hash y usa `indice_documental.yaml` de la sala de lectura como "pista
  débil". Es el ESPEJO de lo que quiere #75 (la sala usa el MD como pista/fuente). Misma doctrina de
  dependencia blanda, en direcciones opuestas.
- La distinción `CRONOLOGIA_FICHEROS` (nivel sala de lectura) vs `CRONOLOGIA_ACTOS` (nivel Cronología),
  "separadas por propósito" (spec:346). **La Cronología ya reservó el terreno de la sala de lectura como
  capa distinta y coexistente.**

**Qué define el Motor Documental #48 que ES exactamente este consumo (pero está APARCADO):**
- "**`01_Sala de lectura` = vista DERIVADA del registro**" (`PLAN_MOTOR_DOCUMENTAL.md:162,220,313-315`).
  El #48 ya modeló la sala de lectura como consumidora de un **registro único de caso** (`_indice_documental.yaml`
  ámbito-caso, §H) que consolida OCR-quality, espejos MD, id dual. Ese registro único es precisamente el
  "substrato compartido" del que la sala DEBERÍA leer. **Pero #48 está aparcado (2026-07-04).**

**Qué queda genuinamente SIN diseñar (el trabajo real del spec):**
1. El **contrato de consumo a nivel-FICHERO**: la Cronología diseñó el contrato acto-level (ficha del
   acto §3.1); la sala necesita un contrato fichero-level (qué campos lee del frontmatter del MD, cómo
   mapea MD→fila del `_MANIFIESTO`). No existe.
2. La **fuente del substrato**: ¿la sala lee los MD **dispersos** (`01_Procesado/Emails/`,
   `.../Whatsapp/`, `.../02_Sala de máquina/03_MD/`) directamente, o lee un **registro único** (#48, sin
   construir)? Sin #48, la sala tiene que saber recorrer 3 árboles distintos con 3 convenciones.
3. El **criterio de copia + `_MANIFIESTO` de procedencia doble** (#75:2788-2798) — detalle nuevo, menor.
4. La **granularidad del email** y el **dueño del OCR de adjuntos** (H1.3, H1.4) — no resueltos en ningún
   spec.

**Opciones:**
- **Opción A — Spec fichero-level autónomo, dependencia blanda de todo lo demás.** Escribir un spec corto
  que reusa los artefactos existentes; NO construir #48 ni la Cronología. *(Recomendada.)*
- **Opción B — Construir primero el registro único #48 y hacer la sala su primer consumidor.** Más limpio
  a largo plazo (un substrato, no 3 árboles) pero **desaparca un proyecto grande** y bloquea la sala.
- **Opción C — Fundir sala de lectura y Cronología en un solo build.** Sobre-ingeniería: mezcla nivel
  fichero y nivel acto, contra la propia doctrina del spec de Cronología. **YAGNI — descartar.**

**Recomendación:** **Opción A**. El hallazgo valioso es literal: *"no hace falta spec nuevo de
arquitectura; hay que construir el consumo fichero-level sobre lo que ya existe, con dependencia blanda"*.
Dejar #48 y la Cronología como norte, no como prerrequisito.

**Pregunta a Nikolai:** ¿Aceptas construir la sala consumidora **leyendo los MD dispersos** (blanda, sin
#48), asumiendo que cuando se desaparque #48 la sala migrará a leer el registro único? ¿O prefieres
desaparcar #48 como cimiento antes (Opción B)?

---

### H1.2 — Orden de pipeline y dependencia lectura↔máquina

**Estado:** la dependencia ya se decidió **BLANDA** en #75 (2762-2767): MD fiable → OCR-soporte → crudo;
si no hay MD, cae a crudo (para no sacar la sala de Cowork puro-nube). Falta **formalizarlo** y resolver
el hueco de cableado (#55).

**Orden ideal (MEJORAS #55:2205-2207):** `intake → atomize/explosión → sala de máquina → sala de lectura
→ viabilidad`. Hoy roto porque atomize (`01_Procesado/Emails`) y máquina (`00_Input`) viven en árboles
distintos y no se alimentan (#55:2208, 2215-2217).

**El nudo real:** la sala de lectura consumidora tendrá que leer de **≥3 orígenes** con convenciones
distintas: `01_Procesado/Emails/CORREOS_LECTURA.md` (+adjuntos), `01_Procesado/Whatsapp/<chat>__LECTURA.md`,
`01_Procesado/02_Sala de máquina/03_MD/{slug}.md`. Eso es lo que un registro único (#48) resolvería.

**Opciones:**
- **Opción A — La sala orquesta y lee 3 árboles (dependencia blanda por tipo).** Por cada fuente en
  `00_Input`, la sala sabe dónde vive su MD fiable: email→Emails/, whatsapp→Whatsapp/, doc→03_MD/. Si no
  existe (no se corrió el atomizador/máquina) → cae a crudo (nombre+metadata, o visión si se admite).
  *Coherente con #75; no exige orden estricto.*
- **Opción B — Un "colector" determinista previo** (podría ser el `core.sala_lectura` de #56) que
  consolida los 3 árboles en un índice intermedio y la skill/tool lee de ahí. Acerca a #48 sin
  construirlo entero.
- **Opción C — Dependencia dura (exigir atomize+máquina antes).** Descartada por #75: rompe Cowork nube.

**Recomendación:** **Opción A** para el piloto (menor superficie, respeta la blandura ya decidida), con
la **Opción B como evolución** natural hacia #48. Formalizar en el spec la tabla "fuente → dónde vive su
MD fiable → fallback a crudo".

**Pregunta a Nikolai:** ¿El orden es una **recomendación** (la sala avisa "corre la sala de máquina para
mejor clasificación" pero funciona sin ella) o quieres un **gate** que lo empuje? (#75 implica lo primero.)

---

### H1.3 — Granularidad del email en el sistema

**Cómo modela HOY la unidad cada capa (dato duro):**
- **`email_atomize`**: átomo = **mensaje** (1 `.md` por mensaje atómico, `MSG-NNNNN`; spec
  `2026-06-24-email-atomize-design.md:82`, "fuente de verdad, 1 por mensaje atómico"). PERO también emite
  **una vista humana única** `CORREOS_LECTURA.md` (orden cronológico, 1 entrada/mensaje, §9 del spec).
- **`whatsapp_atomize`**: átomo = **el chat numerado**, NO el mensaje (decisión explícita: "un `.md` por
  mensaje sería ruido ingobernable → el grano del átomo es el chat numerado"; spec whatsapp §2/§5,
  líneas 42-46). Enterrados promovidos sí tienen `.md` propio.
- **`organizar-sala-lectura` (hoy)**: unidad = **el fichero `.eml`** (cuerpo=principal, adjuntos MIME=
  anexos como bundle; spec `2026-06-18` §5, líneas 130). Grano-fichero.

**El desajuste:** `email_atomize` produce grano-mensaje; la sala asume grano-`.eml`. Si la sala copiara
"1 `.md` por mensaje" a la sala de lectura plana, un caso con 277 mensajes generaría 277 ficheros en el
listado plano — justo el "ruido ingobernable" que WhatsApp ya rechazó.

**Opciones:**
- **Opción A — Unidad de sala = la VISTA HUMANA del atomizador** (`CORREOS_LECTURA.md` como el documento
  de lectura del correo; `<chat>__LECTURA.md` para WhatsApp) + enlaces a adjuntos deduplicados. La sala
  NO explota a mensaje. *Consistente con el grano-chat de WhatsApp y con "la sala es para leer por
  fechas", #56.*
- **Opción B — Unidad de sala = mensaje atómico** (espeja `mensajes/*.md`). Máxima granularidad y
  citabilidad, pero rompe el listado plano y duplica lo que ya es la vista humana.
- **Opción C — Híbrido: hilo como bundle.** Un `.md`/subcarpeta por **hilo** (References/In-Reply-To ya
  da `hilo` estable, spec email §7), con los mensajes como entradas dentro. Intermedio; más trabajo.

**Recomendación:** **Opción A**. La sala de lectura consume el **artefacto de lectura** del atomizador,
no sus átomos. Los átomos (grano-mensaje) son el substrato para la **Cronología** (nivel acto), que sí
los necesita. Esto respeta la separación de niveles de §2.2 y evita explotar la sala. Los adjuntos
relevantes sí pueden aparecer como ítems propios (tienen valor probatorio individual).

**Pregunta a Nikolai:** ¿Te vale que en la sala el correo sea "un documento de lectura cronológico +
adjuntos como ítems", reservando el grano-mensaje para la Cronología? ¿O quieres poder citar el mensaje
individual desde la propia sala (Opción B/C)?

---

### H1.4 — Dueño del OCR de adjuntos

**Estado (dato duro):**
- `email_atomize` deja las fichas de adjunto con `Descripción: (pendiente; OCR en fase 2)`
  (`pipeline.py:269`); la "fase 2 de OCR" **no está construida** (#68.b:2622-2626).
- `adjuntos_contenido` **ya extrae texto** de los adjuntos de `email_atomize` a `<base>.contenido.md`
  con caché sha256 (`pipeline.py:11-13,28`), pero: (1) usa `extractor._extract_one` = **Docling** con
  tope 30pp (`router.py:36`), un motor **distinto** del OCRmyPDF de la sala de máquina; (2) imágenes
  ≥50KB van a "cola de visión" que es **NO-OP** (`vision_estado="pendiente"`, `router.py:32`).
- La sala de máquina OCR-iza con OCRmyPDF (sin tope) pero **solo lee `00_Input`**, no
  `01_Procesado/Emails/adjuntos/` (#68.b:2624).

**El riesgo doble a evitar (lo dice el handoff §4):** (1) **partir el bundle-email** (si la sala de
máquina se lleva los adjuntos a otro árbol, se separan de su correo); (2) **doble OCR** (un adjunto que
está suelto en Drive *y* embebido en el `.eml` se OCR-iza dos veces, con dos motores distintos → "cada
camino lee distinto", #48 B.1).

**Opciones:**
- **Opción A — `email_atomize`/`adjuntos_contenido` es el dueño de la orquestación, con el MOTOR
  unificado.** El adjunto ya está deduplicado por sha256 en `Emails/adjuntos/`; `adjuntos_contenido`
  orquesta su texto — pero **cambiando su motor** de Docling a la función OCR compartida
  (`core/anon/ocr.py::ocr_pdf`, la misma que usa la sala de máquina). Un solo motor, el bundle no se
  parte, dedup una sola vez. *(Recomendada.)*
- **Opción B — La sala de máquina también procesa `01_Procesado/Emails/adjuntos/`.** Un único motor
  (OCRmyPDF) para todo, pero rompe la invariante "máquina lee `00_Input`" y arriesga partir el bundle /
  doble-contar con el adjunto suelto en Drive.
- **Opción C — Dejarlo como está (texto por Docling en `adjuntos_contenido`).** Perpetúa el multi-motor y
  la cola de visión NO-OP. YAGNI negativa: deuda.

**Recomendación:** **Opción A** — separar *quién orquesta* (email_atomize/adjuntos_contenido, que tiene
el bundle y el dedup) de *qué motor* (el compartido OCRmyPDF). Alinea con #48 (fachada de un solo motor)
sin construir #48 entero. Marcar como pregunta si el `.contenido.md` debe vivir junto al adjunto
(`Emails/adjuntos/`) o espejarse a `03_MD/` para que la sala lo lea con la misma convención que los docs.

**Pregunta a Nikolai:** ¿OK a unificar el motor de OCR de adjuntos en OCRmyPDF (retirando el Docling de
`adjuntos_contenido`), y dónde debe aterrizar el texto del adjunto para que la sala lo lea homogéneo?

---

## 4. Exploración Eje B1 — email en la SALA DE MÁQUINA

**Problema:** la sala de máquina trata el `.eml` como nativo grueso → **1 MD por `.eml`** (cabeceras +
cuerpo, sin adjuntos; `sala_maquina.py:254`, `_try_email`). El `.eml` es un **contenedor compuesto**, no
un documento. #55 lo llama "atomize/explosión antes de la máquina".

**Tensión de fondo:** ya existe `email_atomize`, que ES el atomizador de correo (y la Cronología lo
consagra como "primer adaptador congelado", spec §2.4/§9.1). Duplicar esa explosión dentro de la sala de
máquina sería reinventarlo.

**Opciones:**
- **Opción A — Delegar: la sala de máquina NO explota el `.eml`; `email_atomize` es el dueño.** La sala
  de máquina **omite los `.eml`** (o los trata como custodia) y el flujo cablea `atomize` como paso
  hermano. El MD legible del correo sale de `email_atomize` (`CORREOS_LECTURA.md` / `mensajes/*.md`), no
  de la sala de máquina. Los **adjuntos** se OCR-izan por la vía de H1.4. *(Recomendada — no duplica el
  atomizador, respeta que es "congelado".)*
- **Opción B — La sala de máquina explota el `.eml` con su propio código.** Reinventa `email_atomize`
  dentro de la máquina. Contra la doctrina "primer adaptador congelado". Descartar.
- **Opción C — Mantener el MD grueso Y correr atomize aparte (status quo).** Dos representaciones del
  correo (1 MD grueso en `03_MD` + los átomos en `Emails/`) → la sala de lectura tendría que saber cuál
  ignorar. Confuso; el MD grueso no aporta sobre `CORREOS_LECTURA.md`.

**Recomendación:** **Opción A** + cerrar el cableado de #68.a (encadenar `intake → atomize`) y #68.b
(OCR de adjuntos por H1.4). La sala de máquina se queda como dueña de **PDF/imagen/office**; el correo lo
posee `email_atomize`; WhatsApp lo posee `whatsapp_atomize`. Cada fuente, un dueño (§9.1 de Cronología:
"añadir fuente = atomizador + adaptador sin tocar el núcleo").

**Cableado automático (#68):** hoy `atomize_emails` es manual y el intake no extrae adjuntos
(`extract_attachments=False`, #68.a). Opciones de disparo: (i) `abrir_caso` lo encadena; (ii)
`organizar-sala-maquina` lo invoca antes de su OCR; (iii) una fachada `procesar_expediente()` (#48 M4) lo
orquesta. **Pregunta a Nikolai:** ¿dónde vive el disparo del atomize en el flujo (abrir_caso vs sala de
máquina vs fachada)? Es la decisión de cableado de #68 sin resolver.

---

## 5. Exploración Eje A + B2 — la sala de lectura CONSUMIDORA

### 5.1 Jerarquía por tipo (confirmar/afinar #75)

La tabla de #75 (2769-2774) es sólida y está anclada al código. Afinados que sugiere esta exploración:
- **Email → NO la sala de máquina** (que da 1 MD grueso), sino `email_atomize` (#75 ya lo dice). Confirmar
  que el artefacto de lectura es `CORREOS_LECTURA.md` (H1.3-A), no `mensajes/*.md`.
- **WhatsApp → `whatsapp_atomize`** (`<chat>__LECTURA.md`). El handoff/#75 cita `core/whatsapp_atomize`;
  confirmado que existe con esa salida.
- **Documentos → `03_MD/{slug}.md`**, leyendo `ocr_quality` del frontmatter para decidir fiable vs soporte
  (`sala_maquina.py:363-368`). La señal **viaja en el MD** → la sala no consulta `_cobertura.json`
  (#75:2783). Correcto y barato.
- **Fotos/visual → crudo/nombre** (nunca MD). Correcto.

**Frontera de fiabilidad (ya montada, #75:2776-2786):** *fiable* = `ocr_quality=="ok"`; *soporte* =
`low`/`empty`. Dos grados de "ok": `ocr:false` (nativo) = máxima confianza; `ocr:true` (OCR) = fiable.
**Limitación a recordar en el spec:** `ocr_quality` mide densidad+ruido, **no corrección semántica**
(#75:2784-2786) → basta para CATEGORÍA, no para datos exactos (importes/fechas) → esos van a la fuente
(eso es viabilidad, no la sala). Buen guardarraíl anti-sobreconfianza.

### 5.2 Criterio de copia + `_MANIFIESTO` procedencia doble (#75:2788-2798)

Criterio cerrado por Nikolai (qué fichero queda en la sala con nombre canónico):
- PDF nativo/`.docx`/`.txt`/foto → **crudo**.
- Escaneado → **OCR** (`01_OCR/*.pdf` = original + capa de texto, buscable).
- Email → **MD legible** de `email_atomize` + adjuntos originales (el `.eml` es custodia, no lectura).
- **El MD suelto NUNCA sustituye un documento visual** (firmas/sellos/fotos/tablas).

`_MANIFIESTO` con **procedencia doble**: `sha256` del original en `00_Input` + `sha256` del artefacto
copiado + de qué se derivó (hoy guarda un solo sha256, `SKILL.md:211-214`). Custodia intacta: el original
en `_intake_log.jsonl`; la sala es vista derivada, no prueba.

**Observación de rigor (no reabrir, señalar):** esto **rompe la idempotencia por sha256 tal como está
hoy**. La skill hoy saltea por `sha256` del original (`SKILL.md:168,266-278`). Con copia de un artefacto
DERIVADO (OCR, MD), el sha del fichero copiado ≠ sha del original. El `_MANIFIESTO` de doble procedencia
lo resuelve (guardar ambos), pero el **algoritmo de skip** debe cambiar para llavear por sha del origen y
recordar de qué artefacto derivó. Es trabajo real del spec, no gratis. **Pregunta implícita para el
spec**, no para Nikolai.

### 5.3 Email en la lectura (granularidad, enlace, bundles)

Ver H1.3. Recomendado: la sala enlaza al `CORREOS_LECTURA.md` como "documento de correo del caso" +
adjuntos deduplicados como ítems con su `.contenido.md`/OCR. La regla de bundle actual (`.eml` = cuerpo +
adjuntos MIME, spec 2026-06-18 §5) se **reinterpreta**: ya no se explota el `.eml` en la sala (lo hizo el
atomizador); el "bundle" es la vista de correo + sus adjuntos ya deduplicados.

### 5.4 Posición de #76 (`read_media_file` / visión directa)

**Recomendación: FUERA del piloto.** #76 (2814-2858) distingue dos casos de uso: (1) montar la sala
—donde la visión NO aporta velocidad ni fiabilidad frente al MD/OCR determinista (#76:2821-2823); (2)
hojeo ad-hoc del expediente sin OCR previo —donde sí hay hueco en Cowork nube. La sala de lectura es el
caso (1) → la jerarquía #75 (MD→OCR→crudo) ya lo cubre; la visión es peor herramienta aquí. Dejar #76
como cuestión abierta separada (hojeo ad-hoc), no atarla a este spec. Si acaso, el fallback "casos no
claros → visión" de #75 punto 3 es donde #76 tocaría — pero eso es la excepción, no el diseño.

### 5.5 La tensión de fondo #56 vs #75 (LA pregunta grande)

**Dos visiones vivas y parcialmente enfrentadas del MISMO consumo:**
- **#75 (skill prompt-driven que consume MD):** mantiene `organizar-sala-lectura` como "único
  constructor" (spec 2026-06-18 §2 T4), pero eleva el MD a fuente primaria. Ventaja: corre en **Cowork
  puro-nube** (multiusuario, la razón de #34). Coste: el LLM sigue clasificando (más lento; #56 midió ~10
  min re-leyendo 169 ficheros pese a existir los MD, #56:2237).
- **#56 (revivir `core.sala_lectura` determinista + tool MCP):** un core testeado que consume
  `raw_text/`+`_cobertura.md`+sha256 de la sala de máquina, expuesto como tool MCP invocable desde Cowork
  por el `.dxt`; la skill pasa a **orquestador fino** (#56:2250-2259). Ventaja: segundos, no minutos;
  determinista; dedup por sha reutilizado. Coste: exige que la sala de máquina haya corrido (local) →
  **dependencia más dura**, roza el problema de Cowork nube.

Estas dos no son idénticas y el brainstorming **debe reconciliarlas antes de escribir el spec**, porque
condicionan H1.1-H1.4 (si gana #56, "consumir MD" es un core determinista, no un prompt; el registro
único #48 se vuelve casi obligatorio). El spec 2026-06-18 dice "la skill es el único constructor" (§2 T4);
#56 lo contradice parcialmente. **No están formalmente en conflicto cerrado** — #56 está en backlog sin
promover; #75 tampoco tiene spec aún. Es la decisión-madre.

---

## 6. Propuesta de spec(s) + piloto (Fase 4)

### 6.1 Estructura de spec recomendada

**UN solo spec**, no varios: *"Arquitectura capa procesado → sala de lectura (nivel fichero)"*. Motivos:
los cuatro frentes (orden, jerarquía, granularidad email, OCR adjuntos) están acoplados y son pequeños;
partirlos multiplicaría los "specs dormidos" (riesgo real del proyecto, ver §6.3). Contenido:

1. **Frontera y no-solapamiento** (H1.1): declara explícito que este spec es nivel-fichero, hermano —no
   parte— de la Cronología (nivel acto), y con dependencia **blanda** de #48 (registro único). Enuncia
   qué se reusa tal cual (atomizadores + sala de máquina, ya construidos).
2. **Orden y dependencia** (H1.2): tabla "fuente → dónde vive su MD fiable → fallback a crudo"; blanda.
3. **Decisión #56 vs #75** (§5.5): **prerrequisito** — el spec no arranca sin esto resuelto.
4. **Granularidad email** (H1.3) y **OCR de adjuntos** (H1.4): con motor unificado.
5. **Criterio de copia + `_MANIFIESTO` doble** (§5.2) + el **cambio del algoritmo de skip** que implica.
6. **Cableado del atomize** (#68) en el flujo.
7. Fuera de alcance explícito: Cronología, #48 completo, #76.

Si la decisión #56 gana con fuerza, podría partirse en (a) spec del `core.sala_lectura` determinista +
tool MCP y (b) spec del contrato de consumo — pero solo si crece; por defecto, uno.

### 6.2 Piloto mínimo (gate de build, anti-spec-dormido)

**Caso: W-02VND1 (BaRS1).** Es el banco de pruebas ideal porque **ya tiene los tres
substratos construidos y corridos en vivo**:
- Correo: 277 mensajes atomizados + Capa B (89 alta) + adjuntos deduplicados (`email_atomize` en vivo).
- WhatsApp: 4 chats, 2087 mensajes atomizados (`whatsapp_atomize` en vivo).
- Documentos escaneados: candidatos para `03_MD` de la sala de máquina.

**Criterios de éxito del piloto** (verificables, ejercitan lo difícil):
1. La sala se monta **consumiendo los MD existentes** (Emails/, Whatsapp/, 03_MD/) **sin re-procesar el
   crudo** — medir tiempo vs la corrida actual (#56 midió ~10 min; objetivo: segundos/minuto).
2. El **correo NO se explota** en 277 ficheros en la sala plana (valida H1.3-A): aparece como documento
   de lectura + adjuntos como ítems.
3. Un **adjunto escaneado** que llega solo por correo se OCR-iza con el motor unificado y su texto entra
   en la sala (valida H1.4 + #68.b), sin partir el bundle ni doble-OCR.
4. El **`_MANIFIESTO` de doble procedencia** distingue origen vs artefacto copiado, y el **skip
   incremental** funciona en 2ª pasada (valida §5.2).
5. Un documento con MD `low`/`empty` cae correctamente a **soporte/crudo** (valida la blandura de #75).

### 6.3 Riesgo explícito a comunicar

El proyecto tiene **specs completos que no se construyen** (Cronología v7 "DISEÑO COMPLETO, siguiente paso
BUILD" desde 2026-06-25, sin build; #48 aparcado; Motor Documental). El mayor riesgo de este brainstorming
es **producir otro spec dormido**. Mitigación: spec corto + piloto W-02VND1 como gate de build **en la
misma sesión de decisión**, y NO acoplar a la Cronología ni a #48.

---

## 7. Preguntas abiertas para el brainstorming dialógico (priorizadas)

1. **[MADRE] #56 vs #75 — ¿skill prompt-driven que consume MD, o `core.sala_lectura` determinista + tool
   MCP?** Condiciona todo. (§5.5) Sub-preguntas: ¿el peso de "Cowork puro-nube multiusuario" (#34/#75)
   sigue siendo dominante, o el dolor de velocidad (#56, ~10 min) ya lo supera? ¿La sala de máquina
   corriendo antes es aceptable como dependencia (empuja a #56)?

2. **Dependencia de #48 (registro único), hoy APARCADO.** ¿Construir la sala leyendo los MD dispersos
   (blanda, Opción A de H1.1) o desaparcar #48 como cimiento primero (Opción B)? (§3-H1.1)

3. **Granularidad del email en la sala (H1.3).** ¿Documento de lectura cronológico + adjuntos como ítems
   (reservando el grano-mensaje para la Cronología), o poder citar el mensaje individual desde la sala?

4. **OCR de adjuntos de correo (H1.4).** ¿Se unifica el motor en OCRmyPDF (retirando el Docling de
   `adjuntos_contenido`)? ¿Dónde aterriza el `.contenido.md`/OCR del adjunto para que la sala lo lea
   homogéneo (junto al adjunto en Emails/, o espejado a 03_MD/)?

5. **Cableado del atomize en el flujo (#68).** ¿Disparo desde `abrir_caso`, desde `organizar-sala-maquina`,
   o desde una fachada `procesar_expediente()` (#48 M4)? ¿Y el intake pasa a `extract_attachments=True`?

6. **Orden: recomendación o gate (H1.2).** ¿La sala avisa "corre la sala de máquina para mejor
   clasificación" pero funciona sin ella, o hay un gate que lo empuje?

7. **`_MANIFIESTO` doble procedencia y skip incremental (§5.2).** Confirmar que se acepta reescribir el
   algoritmo de skip (llavear por sha del origen + recordar el artefacto derivado), no solo añadir una
   columna.

8. **#76 (`read_media_file`/visión).** Confirmar que queda FUERA de este piloto (caso de uso "hojeo
   ad-hoc", no "montar la sala"). (§5.4)

9. **Terminología/consistencia menor:** ¿la sala de lectura sigue en `01_Procesado/Sala lectura/` o se
   renombra a `01_Sala de lectura/` como prevé #48 §G.1? (Afecta a ~18 skills que citan la ruta; botón K
   de #48.) No bloqueante, pero decide si el spec ya adopta el naming futuro.
