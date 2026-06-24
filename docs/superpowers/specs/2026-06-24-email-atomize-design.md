# Diseño — Motor de atomización de correo (`core/email_atomize/`)

> Spec de diseño. Aprobado por Nikolai 2026-06-24 (brainstorming).
> Caso piloto: **W-02VND1 (BaRS1 — Tibidabo 8)**. Motor **genérico**, no específico del caso.
> Fin último: recuperar TODA la autoría de PersonaUno —hoy enterrada como reenvíos—
> para levantar el velo de Tibidabo 8 S.L. (titular real + administrador de hecho).

## 1. Contexto y objetivo

Nuevo módulo reutilizable que descompone los correos de un expediente a nivel de
**MENSAJE ATÓMICO**. Lee los `.eml` ya exportados a `00_Input/03_Email/` (producidos por
`core.email_export`) y produce, en `01_Procesado/Emails/`, una fuente de verdad de un
`.md` por mensaje (frontmatter YAML + cuerpo limpio), adjuntos deduplicados por contenido
con su ficha, un índice de máquina (`corpus.jsonl`), un control persistente (`_registro.json`)
y dos vistas humanas (`CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md`).

**Arquitectura 3 capas (CLAUDE.md):** la lógica vive en `core/email_atomize/`; el CLI
`scripts/atomize_emails.py` solo orquesta. **Nunca toca `00_Input`** (crudo inmutable);
re-ejecutar es idempotente.

## 2. Medición sobre datos reales (W-02VND1, solo lectura, 2026-06-24)

Pasada de validación de la huella de dedup y conteos ANTES de fijar el diseño (paso 1 del
orden de trabajo), reutilizando las funciones reales de `core.email_export`:

| Métrica | Valor | Implicación de diseño |
|---|---|---|
| `.eml` a primer nivel | 277, todos con Message-ID, **todos distintos** | `email_export` ya dedupó perfecto a nivel de `.eml` |
| Padres con `message/rfc822` embebido | 9 padres → 266 embebidos | — |
| Embebidos ya presentes como `.eml` suelto | **266 / 266 (100 %)** | Mensajes únicos de Capa A = **exactamente 277**; descender + dedup por Message-ID **converge** con "procesar los 277 ficheros". Los embebidos no aportan nada nuevo en este caso, pero el motor debe descender + dedupar para ser **genérico** (casos sin aplanar previo, o embebido ≠ suelto). |
| Ficheros con marcas de reenvío/cita en línea | **122 / 277** | **Aquí vive la autoría enterrada de PersonaUno.** Los reenvíos como `message/rfc822` ya están atomizados a nivel `.eml`; lo no recuperado es **inline** (Capa B). Capa B es el núcleo del objetivo, no un extra. |
| Partes de adjunto / distintas por sha256 | 293 → **168** (43 % duplicados) | el dedup por sha256 es carga real |
| sha256 ≥ 5× (candidatos decorativos) | 7 hashes / 78 partes | filtro recurrencia+tamaño validado |
| Mojibake en cuerpos decodificados | 3 ficheros, **todos del `text/html`**; el `text/plain` limpio | preferir text/plain lo resuelve; recuperación de charset condicional para HTML-only |

### 2.1 Causa raíz del mojibake ("investigar por qué")

El `.eml` de origen está **correctamente en UTF-8**: el `text/plain` decodifica limpio con
su charset declarado (p. ej. *"Crec que aquest document ja està inclòs en la relació"*). El
mojibake aparecía solo en la parte `text/html` del mismo mensaje multipart (charset mal
declarado). Dos conclusiones, ya verificadas con sonda:

1. **Preferir `text/plain`** elimina el mojibake de los 3 ficheros marcados.
2. Una "reparación" `cp1252→utf-8` **ciega corrompe** texto ya limpio (la sonda de
   doble-decodificación lo empeoró). La recuperación de charset debe ser **condicional**:
   aplicar solo cuando el sniff de mojibake dispara **y** el round-trip **reduce** marcas;
   si no, conservar y marcar para revisión.

## 3. Arquitectura del módulo

Paquete `core/email_atomize/`, cada unidad con una responsabilidad:

- `ids.py` — asignación de IDs congelados (`MSG-NNNNN`/`ATT-NNNNN`), carga/guardado de
  `_registro.json`, mapa `sha256 → ID`.
- `extract.py` — **Capa A**: lee cada `.eml`, desciende en `message/rfc822` embebido
  (reutilizando `email_export.iter_nested_originals`/`message_id_of`/`parse_headers`),
  emite registros de mensaje atómico con bytes verbatim + procedencia.
- `bodies.py` — limpieza de cuerpo: preferencia text/plain, HTML→texto, top/bottom/
  intercalado, recuperación de charset + sniff de mojibake.
- `dedup.py` — dedup por Message-ID primero; huella inline para mensajes sin Message-ID;
  regla de upgrade de fidelidad; cola de casi-duplicados.
- `attachments.py` — dedup por sha256, filtro decorativo (recurrencia+tamaño), ficha.
- `inline.py` — **Capa B**: separación heurística de reenvíos/citas en línea con
  confianza + cola de revisión (se construye en fase posterior).
- `render.py` — `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md`, escritor del `.md` por mensaje.
- `corpus.py` — escritores de `corpus.jsonl` + `_registro.json` con los registros meta
  "generado / no editar".
- `identities.py` + `views.py` — **capa específica del caso** (identidades.yaml, vistas
  temáticas) — diseñada ahora, construida la última.
- `pipeline.py` — orquestación; `scripts/atomize_emails.py` es un CLI fino encima.

**Reutilizar, no reimplementar:** `message_id_of`, `parse_headers`, `iter_nested_originals`,
`_iter_partes_hoja`, los helpers de slug de `eml_filename`, `compute_sha256_bytes` vienen de
`email_export`/`intake_manifest`. Se usan en su sitio (ya están probados); no se copian.

**Disparo:** CLI `scripts/atomize_emails.py` (espejo de `core.email_export`). Motor local,
se ejecuta desde PowerShell. Sin botón Streamlit ni skill (decisión 2026-06-24).

## 4. Salida (`<caso>/01_Procesado/Emails/`)

```
mensajes/   AAAA-MM-DD_HHMM_slug_MSG-NNNNN.md     ← fuente de verdad, 1 por mensaje atómico
adjuntos/   AAAA-MM-DD_slug_ATT-NNNNN.ext         ← binarios deduplicados
            AAAA-MM-DD_slug_ATT-NNNNN.md          ← ficha por adjunto único
                                                     (si el original es .md → ...ATT-NNNNN.ficha.md)
corpus.jsonl                                       ← índice de máquina, 1 línea/mensaje + meta
_registro.json                                     ← mapa congelado sha256→ID + lista de .eml procesados
CORREOS_LECTURA.md                                 ← documento humano único
INDICE_ADJUNTOS.md                                 ← catálogo de adjuntos
_revision/  cola.md / casi_duplicados.md           ← colas de revisión Capa B (cuando se construya)
_entregas/                                          ← snapshots sellados (acción manual)
```

Hermano de `Sala lectura/` y `MD/`. Solo lectura sobre `00_Input`. Sin colisión con
convenciones existentes. Lee `.eml` en claro **en local** (sin LLM, sin externo) — misma
postura que el pipeline confidencial; no abre terreno RGPD nuevo.

## 5. IDs y congelación (regla dura)

- `MSG-NNNNN`/`ATT-NNNNN`, 5 dígitos, neutros, **globales por expediente**, **congelados por
  contenido** en `_registro.json` (`sha256 → ID`).
- Clave de identidad MSG = Message-ID cuando consta; si no, la huella inline (texto plano
  normalizado + remitente + fecha redondeada + asunto normalizado + hash de cuerpo). Clave
  ATT = sha256 del fichero.
- Las re-ejecuciones **nunca renumeran**: las entradas `sha256→ID` existentes mandan; el
  contenido nuevo toma el siguiente número libre. Una cita `ATT-00007` apunta siempre a los
  mismos bytes.
- **Upgrade de fidelidad:** un mensaje reconstruido de baja confianza que reaparezca como
  copia MIME limpia **conserva su `MSG-id`** pero mejora cuerpo/confianza.

## 6. Limpieza de cuerpo (el `.md` = solo lo que escribió el autor)

- **text/plain preferido**; HTML→texto solo si el plano está vacío/muñón; si divergen
  materialmente (tablas de importes) → conservar HTML y marcar.
- **Recuperación de charset (condicional):** decodificar con el charset declarado; correr el
  sniff de mojibake (densidad de `Ã`/`Â`/`�`); solo si dispara **y** un round-trip
  `cp1252→utf-8` **reduce** marcas, aplicarlo; si no, conservar + marcar a revisión.
- **Top/bottom-posting:** limpiar la cola citada (queda enlazada como su propio mensaje).
  **Respuesta intercalada:** NO limpiar — conservar el bloque íntegro, marcado "respuesta
  intercalada". **Mensaje que solo existe como cita:** extraer como confianza baja
  "reconstruido desde cita" → cola de revisión.
- **Verbatim recuperable:** cada `.md` guarda el sha256 del `.eml` de origen en frontmatter;
  los bytes siguen en `00_Input`.

## 7. Frontmatter y corpus

Frontmatter por mensaje (campos del encargo):

- identidad/enhebrado: `msg_id`, `rfc_message_id`, `in_reply_to`, `hilo`.
- cabecera: `fecha` (ISO + tz Europe/Madrid), `de`, `de_nombre`, `para[]`, `cc[]`,
  `cco[]` (solo si consta), `asunto`.
- procedencia: `eml_origen`, `profundidad`, `ruta_anidacion`, `procedencia[]`, `capa`,
  `confianza`, `auth{dkim,spf,dmarc}`, `sha256`.
- adjuntos: `adjuntos[]` (`att_id`|`msg_id_anidado`, `nombre`, `tipo`, `sha256`).
- contenido: `idioma`, `formato_original`, `emisor_dispositivo` (si consta), `etiquetas[]`
  (vacío por defecto).
- fuente: `"email"` (agnóstico, para futura cronología unificada).

Comentario inicial `# GENERADO … NO editar`.

**ID de hilo (`hilo`) estable:** derivado del Message-ID raíz de la cadena References/
In-Reply-To; fallback a hash de asunto-normalizado + conjunto del participante más temprano.
Estable entre ejecuciones por ser derivado de contenido, no del orden de asignación.

`corpus.jsonl`: primera línea `{"_README":…,"_tipo":"corpus","_no_editar":true}`; el lector
salta líneas con `_README`/`_tipo`. `_registro.json`: `_README`+`_no_editar:true` primero,
luego datos de control. Vistas humanas: cabecera visible arriba.

## 8. Adjuntos

Dedup por sha256 (contenido, no nombre — mismo nombre + bytes distintos = dos ATT). Filtro
decorativo = hash recurrente (los 7 hashes ≥5×) **y** tamaño pequeño → queda embebido en el
`.eml`, no se indexa. Único + sustancial (capturas, fotos, pantallazos) → ATT + ficha.
Dudosos → revisión. Ficha: `att_id`, `nombre_original`, `tipo`, `sha256`, `primera_aparicion`,
`mensajes[]`, `etiquetas[]`; cuerpo para descripción y, en fase 2, texto OCR. **OCR = fase 2
posterior.**

## 9. CORREOS_LECTURA.md (documento humano único)

Markdown autocontenido, orden cronológico, índice navegable con anclas. Por entrada SOLO:
fecha · hora — asunto; De; Para; CC; CCO (si consta); Adjuntos; cuerpo. Añadidos no técnicos:
`Ref. MSG-NNNNN` discreta al pie; nota de reenvío en lenguaje llano cuando aplique ("Reenvía
el correo de X del [fecha]"); "Enviado desde iPhone" si consta. SIN fontanería forense (vive
en las fichas). Si supera ~1000 msgs, opción de partir por años.

## 10. Forense e idempotencia

SHA-256 por mensaje y adjunto; nunca toca `00_Input`; re-ejecutar es idempotente (IDs
congelados, skip por sha). El **acto de reenviar** se registra como evento ligero de primera
clase (quién reenvió qué, a quién, cuándo) — derivado de la `procedencia`/`forwarded_in` que
`email_export` ya deja en `_intake_log.jsonl` más el mapa Message-ID padre↔hijo. Decodificado
robusto (quoted-printable, base64, `=?UTF-8?Q?`, charsets) + chequeo anti-mojibake que avisa.

## 11. Replicabilidad (2 capas)

- **Genérica (motor, idéntica en todo caso):** todo lo anterior. Salida por defecto:
  `CORREOS_LECTURA.md` + `INDICE_ADJUNTOS.md` + `corpus.jsonl` + `_registro.json`.
- **Específica del caso (opcional, vía `etiquetas` + config `identidades.yaml`):** vistas
  temáticas (`dossier_del_burgo`, `vista_nexo_causal`) y mapa de identidades. Para W-02VND1:
  PersonaUno = {`per01c@example.invalid`, `per01a@example.invalid`, cuenta Outlook *(confirmar)*}. Snapshots
  de entrega en `_entregas/` (acción manual: copia sellada + hash).

## 12. Fases de construcción (cada una con su plan, tests y revisión)

1. **Fase 1 — IDs + Capa A + salidas** (`ids`, `extract`, `bodies` mínimo, `attachments`,
   `corpus`, `render`, `pipeline`, CLI). Entrega 277 `.md` + adjuntos + corpus +
   `_registro.json` + `CORREOS_LECTURA.md` + `INDICE_ADJUNTOS.md`. Incluye la medición como
   paso codificado y probado.
2. **Fase 2 — Capa B** (separación inline, confianza, cola de revisión, upgrade de fidelidad,
   cola de casi-duplicados). El payoff de PersonaUno.
3. **Fase 3 — capa de caso** (identidades.yaml, vistas temáticas, `_entregas`).

OCR de adjuntos queda fuera (posterior).

## 13. Puntos abiertos (señalados, no bloqueantes)

- Conjunto de identidades de PersonaUno (`identidades.yaml`): `per01c@example.invalid`, `per01a@example.invalid`,
  cuenta Outlook *(confirmar)* — Fase 3, lo confirma Nikolai entonces.
- Los 3 `.eml` con HTML mojibake: cubiertos por preferir-plain; se añade un test de regresión
  desde uno.

## 14. Tests

`pytest`, patrón de `tests/test_email_export.py` (capa pura sin red + glue con fixtures de
`.eml` crudos construidos en el test). Cada fase añade su bloque. Suite verde como criterio
de cierre de fase.
