---
name: organizar-sala-lectura
description: >-
  Organiza el intake de un expediente FeesDefender en una "sala de lectura"
  legible: lee 00_Input (lotes por fuente + 01_Drive EV/05_CRM; legacy
  02_Whatsapp/03_Email/04_Manual/06_Entrevistas; excluye 90_Notas personales),
  clasifica cada fichero
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
  rol: procesado
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.8"
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
quedó deprecado). Corre en claude.ai/Cowork o en Claude Code local, por **tres modos de
acceso** (ver "Modos de acceso"): **Drive vía `expedientes-xl`** (montado en disco — rápido),
**local-nativo** (caso en ruta local del PC) o **conector** de Drive (nube — fallback), sin
instalar nada. **No destructivo: copia, nunca mueve ni borra el crudo.** El gate humano
es **condicional**: si la propuesta no tiene anomalías, se auto-aprueba y ejecuta sin
esperar OK; si las hay, presenta **una propuesta para tu visto bueno** antes de copiar
nada.

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
- **Lee** de **TODO `00_Input/`**: `00_Input/` tiene dos formas de canal —
  **lotes de entrega** `<AAAA-MM-DD>_<fuente>_<NN>/` (fuentes `whatsapp`, `email`,
  `manual`, `entrevista`; cada lote lleva `_manifiesto.yaml` con `tipo_contenido` por
  ítem) y **cajones espejo** fijos `01_Drive EV/` y `05_CRM/` (sync incremental). Los
  casos antiguos no migrados conservan los cajones `02_Whatsapp/`, `03_Email/`,
  `04_Manual/`, `06_Entrevistas/`: lee AMBAS formas. **Excluyendo `90_Notas
  personales`** (zona del abogado: ningún módulo la lee ni la escribe).
- **Escribe** en `01_Procesado/Sala lectura/`. Cowork debe tener montada la **raíz
  del expediente** (la salida vive fuera de `00_Input`).

## Modos de acceso

La skill accede a los ficheros por uno de **tres** modos, decidido en el **Paso 0** según
**dónde vive el caso**. Todo lo demás (clasificación, taxonomía, gate, índices, catálogo,
bundles) es **idéntico** en los tres. Orden de preferencia: **Modo 1 > Modo 2 > Modo 3**
(los locales evitan la latencia per-fichero del conector nube, que puede tardar decenas de
minutos en un expediente grande).

- **Modo 1 — Drive vía `expedientes-xl` (preferente).** El caso está en el Drive montado en
  disco (`G:/Unidades compartidas/EXPEDIENTES - TYUKHAY LEGAL/CASOS/<ciudad>/<caso>/`,
  subdividido por ciudad: Barcelona, Madrid…). Se accede por el MCP consolidado
  `expedientes-xl` (sandbox `G:` lectura+escritura / `H:` solo-lectura), disponible tanto en
  Claude Code como en Cowork-en-PC (vía la extensión `.dxt`). Lee bytes →
  `expedientes-xl:hash_path` da **sha256 real** server-side. **Copia binarios server-side**
  (`expedientes-xl:copy_path` un fichero / `expedientes-xl:copy_dir` un bundle con su `media/`):
  los bytes NO pasan por el modelo. Se le indica el caso por **nombre de carpeta** (lo resuelve
  bajo `CASOS/`) **o** por **ruta `G:/…` completa** pegada.
- **Modo 2 — Local-nativo.** El caso está en una **ruta local del PC fuera de `G:`/`H:`**
  (p. ej. `Desktop/…` tras un `checkout-caso`, o cualquier carpeta suelta que aporte el
  usuario). `expedientes-xl` **NO llega ahí** (su sandbox es `G:`/`H:`): se usa el filesystem
  que sí alcanza la ruta — en **Claude Code**, las tools nativas (`Read`/`Write`/`Glob`/`Bash`;
  `shutil`/`cp` para binarios); en **Cowork**, el **montaje bash** de la VM (`<mount>/Desktop/…`,
  el mismo que usan `checkout-caso`/`checkin-caso`). sha256 de los bytes leídos localmente;
  copia binarios con `cp`/`shutil`. La sala organizada en local se devuelve al Drive con
  `checkin-caso`.
- **Modo 3 — Conector nube (fallback puro-nube).** No hay filesystem local (Cowork
  móvil/navegador, o PC sin montaje). **Prefiere el conector `google-despacho` (Drive
  multicuenta EV+TL) si está disponible**: ve el Drive del despacho (cuenta TL), escribe
  (scope `drive`) y **copia binarios server-side** (`google-despacho:copy_file` dentro del
  Drive; los bytes no pasan por el modelo). El conector **nativo** de Drive queda como
  **último recurso**: en Cowork es la cuenta **E&V** (`@engelvoelkers.com`), que **NO ve**
  «EXPEDIENTES - TYUKHAY LEGAL» y por tanto no puede escribir la sala. Ambos dan `md5`
  (no sha256): ver Gotchas.

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

## Autonomía y gate condicional

La skill **no inserta preguntas de aclaración** ni pide permiso fichero a fichero.
Tiene **un único gate humano posible**: la propuesta del Paso 2.5, pero es
**condicional** (ver el gate en el Paso 3) — si no hay anomalías, se auto-aprueba y
pasa directo al Paso 4 sin esperar OK, dejando constancia en el plan persistido; solo
cuando hay algo genuinamente ambiguo espera tu confirmación y, tras el OK, ejecuta todo
de una pasada **sin más preguntas**. Por defecto asume autorización para crear y copiar
en `01_Procesado/Sala lectura/` (el crudo de `00_Input` no se toca ni se borra;
siempre **copia**). En **Modo 3 (conector)**, el diálogo de permiso por-llamada se neutraliza
en el **Paso 0** ("Permitir siempre"), no en la skill; en **Modos 1 y 2 (filesystem)** no hay
tal diálogo.

## Procedimiento

0. **Montaje (bloqueante). Determina DÓNDE vive el caso y elige modo (ver "Modos de acceso"):**
   - **¿El usuario dio una ruta local del PC** (`Desktop/…`, `C:/Users/…`, cualquier cosa
     fuera de `G:`/`H:`; típico tras un `checkout-caso`)? → **Modo 2 (local-nativo).** Usa el
     filesystem del entorno (Claude Code: tools nativas `Read`/`Write`/`Glob`/`Bash`; Cowork:
     montaje bash). Baja a `00_Input/`.
   - **¿El caso está en el Drive** (ruta `G:/…` completa, o solo el nombre del caso)? Prueba
     los modos en este orden y usa el **primero disponible** (ToolSearch por sus tools):
     1. **`expedientes-xl`** → **Modo 1.** Resuelve el caso: **ruta `G:/…`** pegada → úsala;
        **solo el nombre** → búscalo bajo `G:/Unidades compartidas/EXPEDIENTES - TYUKHAY
        LEGAL/CASOS/<ciudad>/<caso>/` (lista las ciudades y casa el nombre; no asumas
        profundidad fija). Sin diálogo de permiso.
     2. **`google-despacho`** → **Modo 3 (preferente).** Localiza la carpeta del caso en la
        unidad `EXPEDIENTES - TYUKHAY LEGAL` (cuenta TL) por nombre / `W-XXXXX` / URL.
     3. **conector nativo** de Drive → **Modo 3 (último recurso).** URL de carpeta pegada:
        resuelve `folderId` y DETECTA nivel (raíz → baja a `00_Input/`; subcarpeta de
        `00_Input/` → úsala). En Cowork avisa: la cuenta E&V no ve el Drive del despacho.
   - En cualquier Modo 3, pide activar **"Permitir siempre"** en el conector (CERO diálogos
     durante la ejecución). Baja a `00_Input/`.
   - Disparadores: "organiza esta carpeta <nombre|ruta G:|ruta local|url>".
1. **Lista** **TODO `00_Input/`**: lotes `<AAAA-MM-DD>_<fuente>_<NN>/` + cajones espejo
   (`01_Drive EV`, `05_CRM`) + cajones legacy de casos no migrados (`02_Whatsapp`,
   `03_Email`, `04_Manual`, `06_Entrevistas`), **excluyendo `90_Notas personales`**. Para
   cada fichero, calcula **sha256** de los bytes (**Modo 1**: `expedientes-xl:hash_path`,
   server-side; **Modo 2**: hash de los bytes locales; **Modo 3**: ver Gotchas) y **salta**
   (sin leer ni copiar) lo que ya conste en `_MANIFIESTO.md` (ver "Re-aplicación").
1-bis. **Pre-clasifica mecánicamente antes de leer contenido.** Con la lista de
   `(ruta, sha256, nombre)` del Paso 1:
   a. `dedup_por_sha(ficheros)` → clasifica UNA sola vez cada sha256 único; los
      duplicados se anotan en el `_MANIFIESTO.md` como "duplicado, saltado" sin
      volver a leerlos.
   b. `agrupar_por_hilo(rutas_eml)` sobre los `.eml` únicos → clasifica solo un
      representante por hilo (el nombre sin sufijo `_N`) y propaga su categoría
      al resto del grupo sin volver a leerlos.
   c. `clasificar_por_patron(nombre, es_bundle_conversacional=...)` sobre cada
      único/representante restante → SIEMPRE devuelve una categoría (00-06 por
      patrón estrecho, 07 por defecto, u 08 si es un bundle de WhatsApp sin
      patrón). Pásalo por alto (verifica leyendo) solo cuando el motivo sea
      `default_reclamaciones` y el documento sea inusual o el letrado lo pida
      — no hace falta confirmar 07 sistemáticamente.
   d. Para los binarios opacos (PDF escaneado, imagen) que SÍ necesiten lectura
      real (bundles conversacionales, o para poner fecha real en vez de
      `0000-00-00`): prueba `texto_espejo_md(sm_dir, sha256)` — si
      `01_Procesado/02_Sala de máquina/` ya tiene el texto OCR, úsalo en vez de
      leer el binario o rendirte a `(*)`. Si el binario opaco NO tiene espejo MD
      disponible (`01_Procesado/02_Sala de máquina/` no existe, o su fila en
      `_cobertura.json` no tiene `estado` ok/low), márcalo como señal para el
      gate condicional del Paso 2.5 (ver abajo) — es exactamente la categoría de
      "algo ambiguo" que debe forzar la aparición del gate, en vez de
      clasificarlo a ciegas por nombre y seguir en silencio.
   e. `subcategoria_crm(ruta)` sobre cada documento con categoría "07.
      RECLAMACIONES" → si devuelve subcarpeta (`civil`/`demanda`/`documentos`/
      `preliminares`/`documentacion_rgpd_lopd`), guárdala en el
      `_MANIFIESTO.md` como columna informativa para sub-agrupar el `INDICE.md`
      dentro de "07. RECLAMACIONES" (ver Paso 5 actualizado abajo) — gratis,
      sin coste de clasificación.
   Si `01_Procesado/02_Sala de máquina/` no existe todavía, salta (d) y sigue
   igual — no es bloqueante, solo una ganancia si ya se corrió `organizar-sala-maquina`.
2. **Clasifica cada fichero NUEVO** leyendo su contenido. **Cómo leer según tipo:** los de
   **texto** (`.txt`/`.md`/`.eml`/`_chat.txt`/`.rtf`/`.csv`) se leen directo (**Modo 1**
   `expedientes-xl:read_text`; **Modo 2** `Read`; **Modo 3** `google-despacho:read_file_content`).
   Los **binarios opacos** (PDF escaneado, imágenes, `.xlsx`, vídeo) **NO vuelven al modelo**
   (no hay lectura de su contenido visual): clasifícalos por **nombre + metadata + fecha** y,
   si existe, por el **espejo MD** de `01_Procesado/02_Sala de máquina/03_MD/`; si hay muchos
   escaneados sin MD, sugiere correr `organizar-sala-maquina` antes. Lo que no puedas
   determinar con seguridad → `08. PENDIENTE DE CLASIFICAR`.
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
2-bis. **Persiste la propuesta a fichero** en
   `01_Procesado/Sala lectura/_plan/plan-<AAAA-MM-DD-HHmm>.md` — la misma
   tabla que vas a mostrar en el Paso 2.5 (`sha256 | ruta_original |
   nombre_canonico | tipo | fecha | parte | parent_id` + categoría +
   `subcategoria_crm`), con cabecera `estado: propuesto`. Fuera de
   `Sala lectura/` propiamente dicha para que un re-pull o una re-corrida no
   lo pise ni lo reingiera (mismo motivo que "por qué la sala vive fuera de
   `00_Input`"). NO se borra tras ejecutar — pasa a `estado: ejecutado`
   (mismo razonamiento no-destructivo del resto de la skill).
3. **(Paso 2.5 — GATE, ahora condicional, no siempre).** Si la propuesta NO
   tiene ninguna fila con motivo `requiere_identificar_parte` (bundle
   conversacional sin parte), ningún documento con W-code ajeno al caso,
   ningún casi-duplicado de hash distinto con mismo nombre, y ningún binario
   opaco SIN espejo MD disponible (ver Paso 1-bis.d más arriba) — **procede
   directo al Paso 4 sin esperar aprobación**, deja constancia en el plan
   persistido (`estado: auto-aprobado, sin anomalías`) para que quede trazado
   qué se decidió sin humano.
   Si SÍ hay alguna de esas señales, presenta la propuesta (tarjeta visual,
   como hasta ahora) y **espera confirmación**. Si piden ajustes, reclasifica y
   vuelve a presentar. **Solo con OK explícito** pasas al paso 4 — el gate
   sigue existiendo, pero solo cuando hay algo genuinamente ambiguo que
   decidir, no como trámite fijo.
4. **(tras OK, y SOLO si `rclone` tiene un client OAuth propio configurado —
   ver prerrequisito del Task 4 del plan de la skill; si no, copia
   secuencial como hasta ahora con `copy_path`/`cp`, más lenta pero sin
   prerrequisito) Copia+renombra en bloque vía `rclone rcd`:** aplica **solo a
   casos Drive-residentes (Modo 1 o Modo 3)** — en **Modo 2 (local-nativo)** los
   ficheros están en disco local, no en ningún remote rclone, así que ahí se
   copia con `cp`/`shutil` como ya indica "Modos de acceso". `remote` (p. ej.
   `gdrive_tl:`) y las rutas relativas de `pares` se derivan de la ubicación del
   caso ya resuelta en el **Paso 0**. `levantar_rcd_si_falta()` una vez, luego
   `copiar_manifiesto(remote, pares)` con TODAS las filas del **plan persistido
   en el Paso 2-bis** (`_plan/plan-<AAAA-MM-DD-HHmm>.md`; el `_MANIFIESTO.md`
   todavía no existe — se escribe en el Paso 5) de una vez (no una
   llamada de shell por fichero) — el pacer de cuota se mantiene estable
   dentro del mismo proceso. Los documentos compuestos (bundles) copian
   primero su principal, luego sus anexos, todo dentro de la misma corrida.
   Los `fallidos` que devuelva se reintentan una vez (red inestable) y si
   siguen fallando se anotan en `_MANIFIESTO.md` como pendientes, igual que
   hoy con `ERROR_FILE_NOT_HYDRATED` — nunca se fuerza ni se fabrica un éxito.
5. **Escribe los índices** en `01_Procesado/Sala lectura/` (con la tool de texto del modo:
   `expedientes-xl:write_text` / `Write` / `google-despacho:create_file`):
   - `_MANIFIESTO.md` — tabla por documento, una fila por fichero, columnas:
     `sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id`. El
     `sha256` se calcula de los bytes (el `md5` de Drive NO sirve: la traza del caso
     llavea por sha256). `parent_id` agrupa los anexos de un bundle bajo su principal.
   - `INDICE.md` — agrupado **por categoría** (la categoría vive aquí, no en carpetas),
     orden **fecha DESCENDENTE**. **Dentro de "07. RECLAMACIONES"**, si la mayoría de sus
     documentos tienen `subcategoria_crm` (Paso 1-bis.e), sub-agrupa por esa subcarpeta
     (`civil`/`demanda`/`documentos`/`preliminares`/`documentacion_rgpd_lopd`,
     y "correspondencia" para los `.eml` sin subcategoría CRM) antes de ordenar
     por fecha dentro de cada subgrupo — es la única categoría que lo necesita
     (concentra la mayoría de los documentos en expedientes judicializados).
     Cada entrada enlaza a la copia plana + nombre original.
   - `CRONOLOGIA.md` — por fecha **ASCENDENTE**; `0000-00-00` y fechas `(*)` al final.
   Los tres con cabecera `<!-- GENERADO — NO EDITAR A MANO -->`.
6.5. **Verify — falla ruidosamente, no resumas bonito.** `verificar(filas,
   ficheros_en_disco)` sobre el `_MANIFIESTO.md` recién escrito. Si devuelve
   ALGÚN problema, NO sigas al Paso 7 con un reporte de éxito — lista los
   problemas primero, en el mismo nivel de visibilidad que el resto del
   reporte, y decide con el letrado si reintentar o dejarlos anotados
   explícitamente. Nunca "cuenta bien" un total que no cuadra con lo real.
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

a. **Cabecera:** caso + fuentes leídas (todos los lotes de `00_Input` + los cajones
   espejo/legacy presentes) + aviso «nada copiado aún».
b. **Contadores** por categoría con su nº.
c. **Panel "Requiere tu visto bueno":** SOLO decisiones a revisar — reclasificaciones
   no obvias, identidad/PBC enrutada por parte (y Anexos 1/2 → `06. PBC`), bundles
   propuestos, duplicados sha256, ficheros sin fecha (`0000-00-00`/`(*)`), docs a
   `08. PENDIENTE` con motivo, doc(s) destacado(s). 1 línea/icono.
d. **Listado por fecha DESCENDENTE:** una línea por documento
   `fecha · nombre-canónico · [categoría]` (la categoría es etiqueta, no carpeta).
   **Cada fila identifica el ORIGINAL** para revisar antes de aprobar: **Modo 3 (conector)** →
   enlace `viewUrl` de `00_Input/…`; **Modos 1 y 2 (filesystem)** → **ruta relativa** del
   original bajo el caso (no hay `viewUrl`).
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
- **sha256, no md5:** el `_MANIFIESTO.md` guarda el sha256 de los bytes. En **Modos 1 y 2
  (filesystem)** se leen los bytes → sha256 real (`expedientes-xl:hash_path` server-side, o
  hash local). En **Modo 3 (conector)**, la API da `md5` (que NO casa con la traza del caso):
  calcula sha256 descargando los bytes, no uses el md5.
- **Sin PII en nombres:** revisa la `descripcion` antes de copiar.
- **Estructura plana:** la categoría vive en `INDICE.md`, **no** en carpetas. La sala es
  un único directorio; solo los documentos compuestos abren subcarpeta fechada.
- **Carpeta enorme:** avisa y procesa por lotes; deja constancia de lo cubierto.
- **Los binarios se copian server-side (ya no hay "residuo local"):** el consolidado
  `expedientes-xl` copia binarios en el Drive con `expedientes-xl:copy_path`/`copy_dir`
  (server-side, sin pasar bytes por el modelo), y `google-despacho:copy_file` hace lo mismo
  vía API. Así **Cowork-en-PC (Modo 1) es constructor completo** (texto **y** binarios), no
  solo texto. El viejo límite del `server-filesystem` Node (solo texto, sin `copy_file`) ya
  no aplica: ese server queda jubilado.
- **`expedientes-xl` NO ve el disco local (fuera de `G:`/`H:`):** si el caso está en
  `Desktop/…` u otra ruta local (Modo 2), usa el filesystem del entorno (`cp`/`shutil` en
  Claude Code; montaje bash en Cowork), no `expedientes-xl`.
- **El conector nativo de Cowork es la cuenta E&V:** no ve «EXPEDIENTES - TYUKHAY LEGAL» →
  no puede escribir la sala. En Modo 3 prefiere `google-despacho` (cuenta TL); el nativo es
  último recurso.
- **Stubs `.gdoc`/`.gsheet` (Docs nativos)** son ilegibles por filesystem (`expedientes-xl`
  los omite/bloquea): para su contenido, exporta con `google-despacho`
  (`export_to_drive`/`read_file_content`).
- **Casos grandes (>80 ficheros): reparte la clasificación por fuente en
  subagentes paralelos** (uno por `01_Drive EV`, uno por el lote de email, uno
  por cada expediente CRM) en vez de un único agente secuencial — el dedup por
  sha256 cruzado entre fuentes (Task 1) es la ÚNICA parte que necesita ver todo
  junto; hazla en un paso de fusión aparte, después de que cada subagente
  devuelva su clasificación local.
- **Caso en Drive con muchos ficheros fríos (no hidratados): considera
  `checkout-caso` a disco local antes de montar la sala.** `hash_tree`/
  `read_text` sobre `G:` paga latencia de red por fichero no cacheado; en local
  esa latencia desaparece. La copia server-side (`copy_path`/`cp`) es igual de
  eficiente en ambos sitios — la ganancia está en la LECTURA, no en la copia.
