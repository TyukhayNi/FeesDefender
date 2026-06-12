# PLAN — Intake automático de correos de procuradores → Sudespacho

> **Para retomar en un hilo nuevo. Documento autocontenido.** Diseño cerrado con
> Nikolai el 2026-06-12 (sesión de diseño larga, sobre maquetas). Implementación
> pendiente (Claude Code). Identificador de backlog: `[SIGUIENTE-INTAKE-PROCURADORES-EMAIL]`.
>
> **RGPD — excepción consciente y ACOTADA a este flujo:** este intake usa una **LLM
> en la nube (Mistral, UE)**, aceptando exponer PII porque da mejor resultado que
> scripts puros. NO deroga la regla general del despacho (nada de LLM cloud con
> datos de caso) para el resto de FeesDefender (pipeline, anonimizador, etc.).

---

## 1. Objetivo

Archivar automáticamente en el CRM **Sudespacho** los correos que llegan al
despacho relacionados con procedimientos: (a) **notificaciones de procuradores**
y (b) **contestaciones a correos que el despacho envía desde un expediente**
(p. ej. testigos). Cada correo queda **relacionado con su expediente** en el
módulo de correo del CRM y, cuando procede, sus **adjuntos** se suben al gestor
documental con un **nombre legible**. Todo pasa por una **red de seguridad** con
confirmación humana antes de escribir en el CRM.

Es el sentido inverso del intake actual (correo→CRM, no CRM→local). Encaja con
`docs/PLAN_INTAKE_CRM_COMPLETO.md`.

## 2. Alcance

**Entra:**
- Notificaciones de procuradores (dominios conocidos: `@procuradores-a.example`,
  `@procuradores-b.example`, `proc-a@example.invalid`,
  `@procuradores-c.example`, `proc-f@colegio-proc.example`, `@procuradores-d.example`,
  `@procuradores-e.example`; ampliable).
- Contestaciones a correos enviados desde el CRM (señal: pertenencia al **hilo**
  del correo saliente ya relacionado, o referencia citada en la plantilla).

**No entra (ruido):** alertas automáticas (Google), publicidad, correos internos
sin relevancia procesal.

## 3. Arquitectura

Un **proceso/robot independiente** (no el servidor MCP `gmail-ro`, que es para
consultas interactivas). Corre en local, periódicamente. Reutiliza:
- La conexión a Sudespacho de FeesDefender (`core/sync_sudespacho.py`,
  `SudespachoConfig.from_env()` → API Key en variable de entorno de usuario
  `SUDESPACHO_API_KEY`, cabecera `x-api-key`). **La API Key nunca pasa por el LLM.**
- El motor de extracción/OCR existente (Docling) para leer el contenido de los
  adjuntos.
- El patrón de aprendizaje del organizador local (`core/local_organizer.py`).

Nuevo módulo sugerido: `core/procurador_intake.py` + UI en `streamlit_app.py`.

## 4. Flujo paso a paso

0. **Disparador:** cada X minutos sobre correos entrantes no procesados.
1. **Filtro:** quedarse con notificaciones de procuradores + contestaciones a
   correos del CRM; descartar ruido.
2. **Anti-duplicado (antes de tocar nada):** comprobar si el correo ya está
   relacionado (`GET /api/mail/element_registries`). Los enviados desde el
   expediente ya constan → no se duplican. El mismo correo en los 4 buzones de los
   abogados (procesal@ reenvía a ana.velastegui@, sergio.pinol@,
   nikolai.tyukhay@, paola.barreto@) se trata **una sola vez**.
3. **Entender (LLM Mistral):** de asunto + cuerpo (+ contenido de adjuntos)
   extrae señales y un veredicto (¿trae actuación/documento a archivar?).
4. **Buscar expediente** (ver §5).
5. **Red de seguridad** (ver §6): nada se escribe sin confirmación humana.
6. **Ejecutar lo confirmado** (ver §7): relacionar correo + adjuntar ficheros.
7. **Marcar y registrar:** correo marcado como procesado + apunte en log de
   auditoría (correo, expediente, carpeta, confianza, **quién confirmó**, cuándo).

## 5. Emparejamiento correo → expediente

- **Llave principal = "Su ref"** que el procurador rotula como *Su ref / S/R / Su
  Rfa / Referencia*. **ES el identificador del expediente en el CRM =
  `num_expediente / serie_expediente`**, donde `serie` = **año de creación** del
  expediente. Ej. `13/2026` → num_expediente=13, serie=2026. Match casi exacto:
  buscar el expediente con ese num+serie. (NO confundir con "Mi ref / M/R" del
  procurador.)
- **Multi-señal de respaldo:** contrario, cliente, `juzgado`, `num_asunto`
  (nº autos), `tipo_procedimiento`. Normalizar la referencia (frágil a
  espacios/acentos — ver `[SIGUIENTE-DEDUP-GUARD-ROBUSTO]` en `PLAN.md`).
- **Contestaciones:** por el **hilo** del correo saliente ya relacionado.
- **Sin match:** a bandeja "sin expediente" (nunca inventar).

Campos del expediente (catálogo real `/api/view/config/expedientes_judiciales/fields`):
`num_expediente`, `serie_expediente`, `referencia_procurador`, `juzgado`,
`num_asunto` (autos), `NIG`, `tipo_procedimiento`, `posicion_procesal`, `cuantia`,
`profesional_asignado`, `tags`. Cliente y contrario son **registros relacionados**,
no campos escalares.

## 6. Red de seguridad (bandeja de revisión)

UI nueva en la app **Streamlit** de FeesDefender ("Bandeja de correos"), con
**login ligero por persona** (alimenta el "quién confirmó" y permite filtrar).
El robot **no escribe en el CRM** hasta que una persona confirma.

Cabecera de triaje: recuentos (alta / dudoso / sin expediente), filtros (por
procurador, buscador), opción de **confirmar en bloque** los de confianza alta
(decidir si se activa de inicio; empezar revisando todo).

**Tres estados de tarjeta:**
- 🟢 **Confianza alta:** match exacto por Su ref. Muestra los datos del expediente
  (nº/serie, contrario, juzgado, nº autos, procedimiento) con **check verde por
  cada dato que coincide con el correo** + recuento ("5 datos coinciden"). El
  expediente se puede **cambiar** (buscador colapsado, enlace "cambiar"). Carpeta
  en desplegable. Adjuntos con casilla "Subir". Cuerpo del correo compacto
  (1 línea + "ver completo"). Botones: Confirmar / Descartar.
- 🟡 **Dudoso:** match por señal débil (p. ej. hilo de una contestación). Buscador
  de expediente **abierto** de inicio, **sin checks verdes**, aviso "verifica".
  Botón "Guardar y confirmar".
- 🔴 **Sin expediente:** no hay match. Bloque "**datos detectados en el correo**"
  (Su ref, contrario, juzgado, autos, tipo) para ayudar a localizarlo. Buscador
  vacío (judicial / extrajudicial / clientes). Carpeta y "Asignar y confirmar"
  **deshabilitados** hasta elegir expediente.

**Buscador-selector (combobox) de expediente:** prerrelleno con el match; al
escribir busca en el CRM por referencia/contrario/cliente/autos y lista
candidatos (nº/serie · contrario · juzgado · autos). Al cambiar de expediente, se
refrescan los datos y las carpetas. Reutiliza/amplía la búsqueda por referencia ya
existente en FeesDefender.

**Enlace "abrir en el CRM":** navegación normal → abre el expediente en la sesión
del CRM de quien pincha (su propio login en el navegador), no comparte sesión.

## 7. Escritura en el CRM (contrato)

El módulo de correo del CRM es **Roundcube**, servido por un microservicio aparte
**`nest-mail-commons-pro.sudespacho.biz`** (OpenAPI en `/api-json`), distinto del
`api-crm-commons-pro`.

- **Relacionar correo ↔ expediente:** modelo `MailRelationInput =
  { element, elementId, mail }` (element=`expedientes_judiciales` /
  extrajudiciales / clientes; elementId=ID expediente; mail=identificador del
  correo). Se setea `mailRelations: [MailRelationInput]` vía **`PUT /api/mail/{id}`**
  (body tipo `MailSend`/`MailUpdate`).
- **Adjuntar al gestor documental:** `attachmentGdocu: [{ identifier }]` en el
  mismo PUT, o subida directa. Subida de fichero por **URL prefirmada**:
  `GET /api/documents/presigned-upload-attachment-url` (nest-mail) o
  `GET /api/documents/presigned_urls/{service}/upload/{n}` (api-crm) → PUT bytes a
  S3 → registrar. Alternativa de bajo nivel: `POST /api/documents` /
  `POST /api/documents/single-document/import` (api-crm).
- **Atribución (APROBADO):** una sola API Key, dada de alta como usuario
  **"Robot intake / Archivo automático"**. El "quién confirmó" vive en nuestro
  log. Si hay campo de nota, escribir "confirmado por X". NO una clave por persona.
- **PENDIENTE confirmar al construir:** ¿`nest-mail` acepta `x-api-key` o exige
  el JWT de sesión web (`api-auth-commons-pro/api/authenticate/refresh`)? Si exige
  JWT, resolver el flujo de auth para ese microservicio.

## 8. Carpetas del gestor documental

El desplegable es **espejo de las carpetas de ESE expediente**. Se rellena en
vivo con las carpetas **en uso** (`GET /api/element_registries/gdocu?...associated`)
+ el árbol estándar (`CRM_TREE` en `config.py`). Al cambiar de expediente, se
recarga. **Limitación conocida:** la API no expone carpetas **vacías**
(`/api/folders/gdocu/{parent}` = dead end). Mapa de IDs globales en
`CARPETA_ID_TO_PATH` (1=General, 306=Civil, 307=Demanda, 308=Oposición,
380=Preliminares/Demanda; ampliable). Por defecto **General** si nada claro.

## 9. Renombrado de adjuntos

Aplica a los **adjuntos que van al gestor documental** (el correo en sí se
*relaciona* en Roundcube, no se renombra como fichero).

**Convenciones** (separador `" - "`; extensión REAL y BLOQUEADA — el usuario solo
edita el nombre):
- **Actuaciones procesales:** `<fecha ISO> - <tipo> - <contenido>.<ext>`
  - `2026-06-12 - Auto - nombramiento administrador.pdf`
  - `2026-06-10 - Just Escr - contestacion demanda.pdf`
- **Documentos de prueba (demanda/contestación), numerados:**
  `D <NN> - <fecha ISO> - <contenido>.<ext>` (el número manda para ordenar)
  - `D 01 - 2026-01-02 - contrato arrendamiento.pdf`
  - `D 02 - 2026-02-15 - burofax reclamacion.pdf`

**Vocabulario de tipos + abreviaturas (visor con poco espacio):**

| Tipo | Abrev. | Tipo | Abrev. |
|---|---|---|---|
| Auto | `Auto` | Recurso | `Rec` |
| Sentencia | `Sent` | Acta | `Acta` |
| Decreto | `Decr` | Tasación de costas | `Tasac` |
| Diligencia de ordenación | `DiOr` | Testimonio | `Test` |
| Providencia | `Prov` | Notificación | `Notif` |
| Cédula | `Ced` | Grabación | `Grab` |
| Oficio | `Ofi` | Otros | `Otros` |
| Mandamiento | `Mand` | Escrito (nuestro) | `Escr` |
| Justificante de presentación | `Just Escr` | Escrito parte contraria | `Escr-Crio` |

**Qué lee Mistral para nombrar:** PRIMERO el **contenido del adjunto** (texto
extraído; OCR Docling si está escaneado) → el nombre describe lo de dentro y no
hace falta abrir el fichero; SEGUNDO el cuerpo del correo como contexto; el
filename original solo como pista débil. Devuelve `{ fecha, tipo, descripcion,
confianza }` (+ nº de documento si es probatorio). **El código ensambla el
nombre** (determinista).

**Normalización de la descripción:**
1. Quitar artículos, preposiciones y conjunciones (a, de, del, la, el, los, las,
   un, una, en, con, por, para, y, e, o, u, que, al…).
2. **Quitar tildes de vocales, conservar la ñ** (no convertir "año"→"ano").
3. Conservar nombres propios, números y referencias.
4. Acotar ~40 car. Saneado Windows-safe (reusa `_sanitize`).

Ej.: "contestación a la demanda" → `contestacion demanda`; "nombramiento de
administrador" → `nombramiento administrador`.

**Reglas:** sin fecha → fecha de recepción + revisión; sin tipo → `Otros` +
revisión; colisión en misma carpeta → sufijo `__2`; logotipo del procurador →
casilla "Subir" **desmarcada** por defecto; el CRM conserva `nombreoriginal` y el
nuevo va en `documentName`/`nombrefinal` (cadena de custodia).

## 10. Aprendizaje y memoria del renombrado (FeesDefender conserva la experiencia)

**Requisito de Nikolai:** FeesDefender debe **quedarse con la experiencia de
renombrado** y mejorarla con el uso.

- Cada **corrección humana** en la bandeja (cambiar nombre, tipo, carpeta o
  expediente) se persiste como **señal de aprendizaje** en un store local de
  FeesDefender, extendiendo el patrón del organizador
  (`data/_aprendizaje/correcciones.jsonl`). Sugerido: `correcciones_intake.jsonl`
  (o reusar el mismo store con un campo `fuente: "procurador_intake"`).
- Cada señal guarda: remitente/procurador, tipo de actuación detectado, texto
  base, propuesta del robot y **corrección del humano** (nombre/tipo/carpeta).
- En la siguiente ejecución, esas correcciones alimentan el prompt de Mistral
  como **few-shot** (ejemplos cercanos), de forma que el robot **acierta cada vez
  más** en patrones recurrentes (un procurador concreto, un tipo de resolución,
  una carpeta habitual). No memoriza correos sueltos: aprende **patrones**.
- El store es **local** (señales/metadatos): coherente con el control de datos.
- Métricas de calidad (aciertos vs correcciones) en `data/_aprendizaje/`, como ya
  hace el organizador, para medir mejora y decidir cuándo auto-aprobar confianza
  alta.

## 11. Grabaciones (enlaces de descarga)

Las grabaciones de vistas llegan como **enlace** en el cuerpo
(`we.tl` / `wetransfer.com`; prever también Drive/Dropbox/Swisstransfer).
- Detectar el enlace → **descargar cuanto antes** (los WeTransfer **caducan**
  ~7 días → prioridad).
- Subir al gestor documental vía presigned URL como `… - Grab - …`. Si el vídeo
  excede el límite del CRM, guardar en carpeta Drive + enlazar.
- **Fallback:** si la descarga falla/caduca/host desconocido → la tarjeta lo marca
  como "descarga manual" con el enlace. (WeTransfer puede cambiar/bloquear la
  descarga automática; construir defensivo.)

## 12. Motor LLM

- **Mistral AI (Francia):** datos en UE, opción **retención cero**; modelos
  pequeños (Ministral 8B / Mistral Small) baratos y sobrados para extraer
  señales + clasificar + nombrar. Coste esperado: céntimos-pocos €/mes.
- **Conector LLM intercambiable** (capa fina): cambiar modelo/proveedor = 1 línea.
- Alternativa de soberanía UE: **OVHcloud AI Endpoints** (modelos abiertos en
  infra francesa).
- Al construir: confirmar precio/nombre de modelo vigente y **activar retención
  cero**.

## 13. Credenciales / conexión

- Sudespacho: `SUDESPACHO_BASE_URL=https://api-crm-commons-pro.sudespacho.biz`,
  `SUDESPACHO_API_KEY` (variable de entorno de **usuario** de Windows, NO en
  `.env`), cabecera **`x-api-key`** (NO `Authorization`, reservado a JWT web).
  La lee `core/sync_sudespacho.py` en runtime; **nunca pasa por el LLM/chat**.
- Gmail: tokens en `C:\Users\tnm33\.gmail-mcp\` (los del servidor `gmail-ro`).
- Mistral / nest-mail: secretos en entorno, nunca en repo.

## 14. Pegas técnicas detectadas (a resolver al construir)

- `get_expediente(444)` con `EXPEDIENTE_DEFAULT_PROPERTIES` → **HTTP 500 "Array to
  string conversion"**: alguna propiedad array rompe; elegir properties con
  cuidado / excluir la ofensora.
- `list_gdocu_folders(444)` devolvió **vacío**: revisar params (element/member)
  para listar las carpetas en uso de un expediente.
- **Auth de `nest-mail`** (relate/adjuntar): confirmar si `x-api-key` basta o
  exige JWT de sesión.
- **WeTransfer:** descarga automática frágil (caducidad + posibles cambios).

## 15. Fases de construcción (incremental)

- **F1 — Matcher (read-only):** dado un correo, Mistral + búsqueda por referencia
  → expediente + confianza + carpeta sugerida + nombres propuestos. Sin escribir
  nada. Validar contra correos reales (vía `gmail-ro` para el set de prueba).
- **F2 — Bandeja (Streamlit):** las 3 tarjetas + login + log de auditoría.
  Confirmaciones simuladas (dry-run).
- **F3 — Escritura en el CRM:** resolver auth de nest-mail; relate + adjuntar en
  un expediente de prueba; verificar marcado en Roundcube. Activar tras validar.
- **F4 — Renombrado + OCR + aprendizaje:** contenido del adjunto → nombre;
  store de correcciones + few-shot.
- **F5 — Grabaciones:** descarga de enlaces + fallback manual.

## 16. Decisiones cerradas (2026-06-12)

1. Alcance: notificaciones de procuradores **+** contestaciones a correos del CRM.
2. Llave = Su ref (= num/serie, serie=año); multi-señal de respaldo.
3. Red de seguridad con confirmación humana **antes** de escribir; 3 tarjetas.
4. Login por persona en Streamlit; atribución CRM = usuario API "Robot intake".
5. Carpeta = espejo del expediente (desplegable editable, recarga al cambiar).
6. Renombrado: convenciones, abreviaturas, normalización (sin stopwords, sin
   tildes salvo ñ); Mistral lee el **contenido**; extensión bloqueada.
7. Documentos de prueba: `D <NN> - fecha - contenido` (número delante).
8. FeesDefender conserva la experiencia de renombrado (aprendizaje persistente).
9. Motor LLM = Mistral (UE), conector intercambiable.
10. RGPD: excepción acotada SOLO a este flujo.

## 17. Pendientes / a decidir

- ¿Confirmar en bloque los de confianza alta de inicio, o revisar todo al principio?
- ¿Auth de nest-mail (x-api-key vs JWT)?
- Límite de tamaño del CRM para grabaciones (¿Drive + enlace?).
- Catálogo de carpetas: ir cerrando `CARPETA_ID_TO_PATH` con descubrimiento.
