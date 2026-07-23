# Diseño — Consumo de emails atomizados en la sala de lectura (nivel-fichero)

> ⚠️ **ESTADO: REVISIÓN ADVERSARIAL PENDIENTE DE ADJUDICAR.** Antes de crear el plan
> o implementar, leer
> [`2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md`](2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md).
> Los hallazgos P0 deben resolverse expresamente en esta spec.

> Diseño cerrado por brainstorming dialógico con Nikolai, 2026-07-23. Motivo: limpieza de
> arquitectura (sin caso urgente disparándolo). Contexto previo: exploración
> `docs/superpowers/2026-07-19-sala-lectura-procesado-exploracion.md`, `MEJORAS_FUTURAS.md` #75/#76.
> Implementación: Claude Code.

---

## 1. Frontera y no-solapamiento

Este spec es **nivel-FICHERO**: cambia cómo `organizar-sala-lectura` consume la salida de
`core/email_atomize` cuando esta ya existe para un caso. Es **hermano, no prerrequisito ni parte**,
de:

- **Cronología Unificada** (nivel ACTO, `MEJORAS` diseño completo, no construida) — no se toca.
- **Motor Documental `#48`** (registro único, aparcado) — **dependencia BLANDA**: este spec lee los
  MD dispersos de `01_Procesado/Emails/` directamente, sin esperar a que `#48` se desaparque.
- **Cableado automático de `email_atomize`** (`MEJORAS #68`) — **fuera de alcance**. `email_atomize`
  sigue disparándose manualmente, como hoy. Este spec solo cambia el CONSUMO: si el caso ya tiene
  `email_atomize` corrido, la sala lo aprovecha; si no, cae al comportamiento actual sin cambios.
- **Cola de visión NO-OP para imágenes ≥50KB** (adyacente a `MEJORAS #76`) — fuera de alcance. Se
  trata solo el OCR de adjuntos-documento (PDF nativo/escaneado), no fotos.

**Dependencia blanda, nunca gate:** si `01_Procesado/Emails/corpus.jsonl` no existe para un lote de
correo, ese lote se procesa exactamente como hoy (lectura del `.eml` crudo). Ningún caso deja de
poder montarse por falta de `email_atomize`.

## 2. Por qué (motivación)

Hoy, si un caso ya tiene `email_atomize` corrido (mensajes atomizados, adjuntos deduplicados por
sha256, autoría reconstruida en citas/reenvíos — Capa B), `organizar-sala-lectura` ignora ese
trabajo por completo: vuelve a abrir cada `.eml` crudo como si `email_atomize` nunca hubiera
corrido. Consecuencias concretas que este spec corrige:

- **Trabajo duplicado.** El dedup de adjuntos, la limpieza de MIME/HTML y la reconstrucción de
  autoría enterrada (Capa B) ya están hechos y se tiran.
- **Peor calidad de clasificación.** Leer `.eml` crudo (cabeceras MIME, firmas HTML repetidas,
  cadenas de reenvío sin desenredar) es más propenso a error que leer el resumen ya depurado.
- **Riesgo de inundar la sala.** Sin cambiar la granularidad, un caso grande de correo (p.ej. 277
  mensajes) generaría cientos de filas en el listado plano de la sala — el mismo "ruido
  ingobernable" que `whatsapp_atomize` ya rechazó explícitamente para WhatsApp.

Lo que este spec NO promete: no acelera casos que nunca han corrido `email_atomize` (ahí la sala
sigue igual que hoy). Es una mejora de calidad/consistencia/legibilidad para cuando ambos procesos
ya se han corrido sobre el mismo expediente y hoy no se aprovechan entre sí.

## 3. Arquitectura de consumo

**Decisión (descartadas: revivir `core.sala_lectura` determinista + tool MCP; y dejar el LLM leyendo
directamente el MD sin ayuda mecánica):** un script Python pequeño, **embebido dentro del propio
paquete `.skill`** de `organizar-sala-lectura` (mismo patrón que `scripts/preclasificar.py`,
`scripts/verificar_sala.py`), resuelve la parte mecánica (qué hilos ya están atomizados y dónde),
mientras la skill (Claude, prompt-driven) sigue decidiendo categoría/fecha/parte como hoy — ahora
leyendo un resumen limpio en vez del `.eml` crudo cuando existe.

**Por qué esta opción y no las otras dos:**
- Un servidor MCP aparte (tipo `expedientes-xl`) exigiría Python del sistema instalado en cada
  máquina del equipo (Paola/Ana/Sergio) — instalación nueva a mantener, sin ganancia real sobre
  la opción elegida.
- Dejar que el LLM lea el MD sin ayuda mecánica es más simple pero menos determinista: la
  agrupación por hilo y la detección de qué ya está atomizado quedarían sujetas a interpretación
  del modelo en cada corrida, en vez de a una regla fija y testeable.
- El script embebido da determinismo donde importa (qué existe, qué falta) sin instalar nada nuevo:
  viaja dentro del mismo `.skill` que el equipo ya reimporta, y Cowork ya lo ejecuta en su sandbox
  interno exactamente igual que ejecuta `preclasificar.py` hoy.

**Cero-instalación:** ningún servidor MCP nuevo, ningún requisito de Python del sistema en el
puesto de Paola/Ana/Sergio más allá de lo que ya tienen para usar Cowork/las skills.

## 4. Contrato de datos

`core/email_atomize` ya expone lo que hace falta, sin construir nada nuevo en ese lado:

- **`01_Procesado/Emails/corpus.jsonl`** — una línea por mensaje atomizado, con (entre otros)
  el campo **`hilo`** ([`headers.py:100`](../../../core/email_atomize/headers.py:100),
  [`corpus.py:26`](../../../core/email_atomize/corpus.py:26)), calculado de
  `References`/`In-Reply-To` — ya estable, ya probado, no se recalcula ni se duplica su lógica.
- **`01_Procesado/Emails/mensajes/*.md`** — un fichero por mensaje atómico, con `MSG-NNNNN`
  congelado por contenido ([`ids.py:37-46`](../../../core/email_atomize/ids.py:37)): el mismo
  `Message-ID` siempre produce el mismo `MSG-id`, re-ejecutar `email_atomize` **nunca renumera**.
- **`01_Procesado/Emails/adjuntos/`** — adjuntos deduplicados por sha256, con su ficha.
- **`01_Procesado/Emails/adjuntos/<sha>.contenido.md`** — texto extraído del adjunto (ver §6).

## 5. Script nuevo (`scripts/emails_atomizados.py`)

Dos funciones, sin estado propio (todo se deriva de lo que ya escribió `email_atomize`):

- **`hilos_disponibles(caso_dir) -> dict[hilo_id, HiloInfo]`** — lee `corpus.jsonl` (si no existe,
  devuelve `{}` y todo el lote cae al camino actual); agrupa mensajes por `hilo`; por cada hilo
  devuelve la lista de `MSG-id` con su fecha, la fecha del primer mensaje (para datar el bundle) y
  sus adjuntos referenciados.
- **`render_documento_hilo(caso_dir, hilo_id) -> str`** — concatena cronológicamente los
  `mensajes/*.md` de ese hilo en un único documento de lectura markdown, listo para copiar como
  principal del bundle.

## 6. Cambios en el procedimiento de `organizar-sala-lectura`

- **Paso 1-bis.b** (hoy `agrupar_por_hilo(rutas_eml)` solo ahorra lecturas de clasificación): antes
  de tocar los `.eml`, se llama a `hilos_disponibles()`. Los hilos cubiertos por `email_atomize` se
  clasifican leyendo `render_documento_hilo()` (categoría/parte con el mismo criterio de siempre:
  vendedor→`01. ACTIVACIÓN`, comprador→`03. OFERTAS`, etc.); los hilos sin cobertura siguen el
  camino de hoy, sin cambios.
- **Paso 4 (copia) / "Documentos compuestos":** un hilo cubierto se copia como **un bundle fechado
  por su primer mensaje** (`AAAA-MM-DD_descripcion/`) — principal = el documento renderizado,
  anexos = los adjuntos que `email_atomize` YA deduplicó (se reutilizan tal cual, no se re-extraen
  del MIME). **El `.eml` original NO se copia** — criterio ya cerrado por Nikolai 2026-07-19: el
  `.eml` es custodia (queda en `00_Input`, referenciado por su sha256 en `_intake_log.jsonl`), no
  lectura. Un hilo sin cobertura sigue copiándose como hoy (`.eml` + adjuntos MIME).
- **Granularidad (cerrada):** un documento de lectura por **HILO**, no por mensaje individual ni un
  único documento para todo el caso. Un caso con 277 mensajes en ~40 hilos produce ~40 filas en la
  sala, no 277 ni 1 — coherente con la convención existente "fecha DESCENDENTE, una fila por
  documento con SU fecha", y con el precedente de `whatsapp_atomize` (grano-chat, no grano-mensaje).

## 7. Idempotencia — skip por hilo (el punto de robustez real)

El criterio de "ya copiado, saltar" no puede seguir siendo un único `sha256` de fichero origen: un
hilo son varios `.eml`, y puede crecer entre corridas (llega una respuesta nueva). Solución —
**reutiliza la convención YA existente de "anexo con fecha propia dentro de un bundle"** (la misma
que usan hoy los anexos de WhatsApp), sin inventar una invariante nueva:

- La unidad de comparación es el **`MSG-id`** (estable, congelado por contenido), no el hilo
  entero ni un hash agregado.
- Al copiar un hilo por primera vez, el `_MANIFIESTO.md` guarda, bajo el `parent_id` del bundle, la
  lista de `MSG-id` que lo componen. **Cambio de esquema concreto:** se añade una columna nueva
  `msg_ids` (lista `MSG-id` separada por `;`) a las ya existentes del `_MANIFIESTO.md`
  (`sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria |
  subcategoria_crm`); para un bundle de hilo, `ruta_original` referencia el hilo (`hilo_id` +
  ruta de `01_Procesado/Emails/`), no un único `.eml`.
- En cada re-corrida: se compara el conjunto de `MSG-id` que tiene ESE hilo hoy en `corpus.jsonl`
  contra el conjunto ya registrado.
  - **Mismo conjunto → skip total.** Cero lectura, cero escritura.
  - **Hay `MSG-id` nuevos** → solo esos mensajes se copian, como **anexo(s) nuevo(s)** dentro de la
    MISMA carpeta del bundle, fechados por su propia fecha de envío. El documento principal ya
    copiado **no se toca, no se regenera, su sha256 no cambia**.
  - **Hilo sin fila previa** → se crea el bundle completo, igual que un hilo nuevo hoy.

Esto respeta la doctrina "solo añade, nunca borra ni sobrescribe" del resto de la skill: nunca se
reescribe un documento ya copiado, solo se añaden ficheros cuando hay contenido genuinamente nuevo.

**Casos de test que esto exige (ver §9):** sin cambios / mensaje nuevo añadido / hilo enteramente
nuevo.

## 8. OCR de adjuntos — motor unificado

- **Quién orquesta:** `core/adjuntos_contenido` sigue siendo el dueño (ya tiene el adjunto
  deduplicado y sabe a qué correo/hilo pertenece) — no se traslada a la sala de máquina (evita
  partir el bundle-email y el riesgo de doble-OCR si el mismo adjunto también está suelto en
  Drive).
- **Qué cambia:** el motor interno pasa de Docling (`router.py:36`, tope 30 páginas) a
  `core/anon/ocr.py::ocr_pdf` — la MISMA función y el mismo criterio nativo-vs-escaneado que ya usa
  `core/sala_maquina.py`. Un solo motor de OCR en todo el despacho: mismo documento, mismo
  resultado, entre por donde entre (suelto en Drive o pegado a un correo).
- **Dónde aterriza el texto:** sigue en `Emails/adjuntos/<sha>.contenido.md`, junto al adjunto — no
  se espeja a `03_MD/` (evita partir el bundle en dos árboles).
- **Fuera de alcance:** la cola de visión NO-OP para imágenes ≥50KB no se toca (problema distinto:
  fotos vs. documentos escaneados).

## 9. Plan de testing

1. **Unitarios `emails_atomizados.py`:** `hilos_disponibles()` agrupa correctamente desde un
   `corpus.jsonl` fixture; `render_documento_hilo()` concatena en orden cronológico; devuelve vacío
   si el fichero no existe (fallback al camino actual).
2. **Unitarios del skip por hilo** (los 3 casos de §7):
   - re-correr sobre un hilo sin cambios → 0 escrituras, sha256 del principal idéntico;
   - un hilo ya bundleado recibe 1 mensaje nuevo → 1 fichero nuevo en la carpeta, fechado por su
     propio envío, principal intacto;
   - hilo completamente nuevo → se crea el bundle entero.
3. **Integración end-to-end:** caso sintético (`corpus.jsonl` + `mensajes/*.md` + adjuntos de
   fixture) → clasificar+copiar completo, verificando: N hilos producen N filas (no N mensajes);
   los adjuntos se reutilizan sin re-extraer del MIME; el `.eml` original no se copia.
4. **`adjuntos_contenido` con motor unificado:** fixture de PDF escaneado pequeño, verificar que
   pasa por `ocr_pdf` y no por Docling.
5. **Regresión:** suite existente `test_email_atomize_*`/tests de `adjuntos_contenido` sigue verde.
6. **Validación opcional, no bloqueante:** correr sobre un caso real ya atomizado (candidato:
   W-02VND1, que ya tiene los tres substratos corridos en vivo) como smoke test final — puede ir
   como último paso del plan de implementación, no como requisito del spec.

## 10. Fuera de alcance (explícito)

- Cableado automático de cuándo se dispara `email_atomize` (`MEJORAS #68`) — sigue manual.
- Motor Documental `#48` (registro único) — no se construye ni se desaparca.
- Cronología Unificada (nivel ACTO) — no se toca.
- Cola de visión NO-OP para imágenes (`MEJORAS #76`-adyacente) — problema distinto, no se resuelve.
- `whatsapp_atomize` → consumo por la sala: mismo patrón sería aplicable, pero no está pedido aquí;
  si se quiere, es un spec hermano posterior, no parte de este.
