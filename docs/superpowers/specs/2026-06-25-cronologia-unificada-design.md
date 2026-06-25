# Cronología Unificada de Prueba — Especificación de diseño

> **Versión:** v1 (2025-06-25)
> **Estado:** Esquema del evento probatorio COMPLETO (Fases 0, 1 y 2 cerradas). Fase 3 (correlación) pendiente; Fases 4–7 pendientes.
> **Banco de pruebas:** expediente W-02VND1 (Tibidabo 8). El diseño es genérico; el caso solo sirvió de validación sobre datos reales.
> **Naturaleza:** documento de diseño (no construcción). El build vive en `core/` de FeesDefender y lo realiza Claude Code en local. El motor de atomización de correo está **congelado** y es el primer adaptador de esta capa; no se toca.
> **Disciplina rectora:** skill `verificacion-anclada-fuente` (sin inferencia en la capa canónica; anclaje con pinpoint; categorías A–E).

---

## 0. Propósito y alcance

Fusionar todas las fuentes de prueba de un expediente (correo, WhatsApp, CRM, entrevistas, documental, registros) en **una sola línea de tiempo**, manteniendo la fidelidad evidencial: lo que consta en la prueba se separa de lo que se infiere de ella. La herramienta es **replicable a cualquier caso** del despacho.

Dos capas de replicabilidad:
- **Capa genérica** — el proceso idéntico en todo caso (este documento). Un caso sin particularidades se queda aquí y está completo.
- **Capa específica del caso** — vistas temáticas por tesis probatoria (titularidad real, administrador de hecho, nexo causal…), que no son código sino consultas sobre el campo `etiquetas`/`hipótesis`; vacías por defecto.

Relación con otras piezas: la cronología vive **por encima** de los atomizadores por fuente (el motor de correo es el primero; siguen WhatsApp, CRM, entrevistas, documental) y **por encima** de `organizar-sala-lectura` (nivel fichero). No los duplica.

---

## 1. Principios rectores (Decisión 1)

### 1.1 El átomo: acto registrado anclado a fuente (Modelo B)

El átomo de la cronología es un **acto datado anclado a un registro de fuente** (un mensaje enviado, una oferta firmada, una inscripción publicada, una actividad registrada en el CRM), **nunca un hecho del mundo inferido** (p. ej. "la venta se consumó", "hubo nexo causal").

Reparto ontológico de tres (respaldo: W3C PROV-O):
- **Acto** (lo que ocurre) = la unidad de la línea de tiempo (PROV *Activity*).
- **Documento** (lo que existe y prueba) = no va en la línea de tiempo; se engancha al acto (PROV *Entity*).
- **Actor** (quién interviene) = resuelto vía el registro de identidades (PROV *Agent*).

### 1.2 Reglas de granularidad

- Un mensaje = un evento. Un `_chat.txt` = N eventos. Una entrevista = **un** evento. Una inscripción/publicación = un evento. Un documento, por sí solo = **cero** eventos.
- Los **actos documentales con fecha propia** (firma de contrato, firma de oferta, pago, emisión de factura) **sí son eventos**; el documento es su prueba.
- Los **hitos externos** (BORME, SHAB suizo, prensa) **sí entran** como eventos.
- **Un suceso, varias ventanas** (SEM): varias pruebas del mismo acto no generan varios actos.
- **Contexto de la prueba electrónica**: cada evento conserva el enlace a su **hilo** y un **nivel de formalización**; un mensaje no se valora aislado.

### 1.3 Las dos capas

- **Capa canónica** — solo actos registrados directamente anclados (estatus A/B), cada uno con pinpoint. **Regla del Modelo B reforzada:** un suceso material entra en la capa canónica únicamente si está directamente atestiguado (p. ej. una inscripción registral); el que exige inferencia se queda en la derivada. El "evento material" no es puerta trasera para colar inferencia.
- **Capa derivada** — los hechos del mundo, el relato y el nexo causal. **No es plana:** admite hechos intermedios, hipótesis y presunciones judiciales (art. 386 LEC). Cada hecho derivado cita los actos que lo sostienen, lleva su clasificación del art. 217 LEC y alimenta `HECHOS_X.md` con el semáforo 🟢/🟡/🔴.

### 1.4 Confianza en tres ejes (no una escala única)

- **Eje 1 — estatus de anclaje:** categorías A–E de la skill (A declarado en materiales, B en fuente online verificada, C apoyado-no-expreso, D no encontrado, E inferencia).
- **Eje 2 — credibilidad/fuerza:** para hechos derivados y enlaces (¿es cierto? / ¿cuánta fuerza?).
- **Eje 3 — fiabilidad de la fuente:** atributo, solo cuando importe.

Formaliza el "doble confianza": una cosa es que un hecho esté *expresamente en la prueba* (anclaje) y otra que sea *cierto* (credibilidad).

### 1.5 El enlace de prueba como primitivo único

Un solo mecanismo de enlace, tipado, con fuerza/diagnosticidad, que conecta artefacto↔evento y evento↔evento. Absorbe la Fase 3 (correlación) y el tratamiento de contradicciones (citar ambas partes con pinpoint, no resolver por suposición).

---

## 2. Arquitectura de almacenamiento (Decisión 2)

### 2.1 Modelo híbrido (almacén delgado + contenido en la fuente)

- **Verdad de contenido VERBATIM = en la fuente** (correo `mensajes/*.md`, WhatsApp `_chat.txt`+media, transcripción, ficha CRM, PDF). El evento **no copia** el verbatim: lo apunta.
- **Verdad de relación temporal = almacén de eventos canónico, DELGADO y persistente** (fecha+precisión, fuente, tipo, actores resueltos, estado, pinpoint, contenido **derivado**/paráfrasis — nunca verbatim).

### 2.2 Pinpoint doble

Cada acto apunta a su fuente con: **localizador interno** (id/ruta) + **clave natural de contenido** (Message-ID/sha256 en correo; fecha+autor+hash en WhatsApp; referencia oficial en BORME). Permite re-enganchar si una fuente se reconstruye y es verificable por un tercero (conforme a la skill).

### 2.3 Piezas del nivel cronología

- **Almacén de eventos** (canónico, persistente).
- **`eventos.jsonl`** — índice de máquina regenerable (como el `corpus.jsonl` del correo).
- **`_registro_cronologia.json`** — libro persistente NO derivable: mapa `huella→id` congelado, actores resueltos, enlaces. Si se borra, se rompen las citas.
- **Capa derivada de hechos** — encima; cita `EVT-…`; alimenta `HECHOS_X.md`.

### 2.4 Relación con el motor de correo

La cronología **consume** las salidas del motor de correo (`mensajes/*.md`, `corpus.jsonl`, `_registro.json`); **no lo modifica** (spec congelado). El correo es el primer adaptador; los demás replican el patrón.
**Precondición:** cada fuente debe exponer átomos con ID estable (un `_chat.txt` crudo no los tiene → necesita su atomizador; es la Fase 5).

### 2.5 Identidad de artefacto (por contenido, no por nombre)

- Huella idéntica (sha256) → mismo artefacto, automático, **conservando todas las procedencias**.
- Huella distinta + señales (nombre, nº páginas, texto interno, huella visual, metadatos PDF) → "probablemente el mismo" a **confirmación humana**, nunca fusión automática.
- Unir la identidad del artefacto **nunca borra las apariciones**: cada envío/aparición es su propio evento (valor probatorio).
- Versiones (lo realmente distinto) **no se unen, se enlazan** como familia (subtipo: formato / cadena-con-orden / plantilla / contiene). El **orden** de la cadena se fija por los **eventos**, no por la fecha del fichero. La familia se **acota al mismo asunto**.

### 2.6 Otros

- **Custodia:** el almacén de eventos y `_registro_cronologia.json` son **work-product**, no prueba; la prueba son las fuentes apuntadas. No mezclar al sellar entrega.
- **Frontera regenerable/humano = en `HECHOS_X.md`:** `eventos.jsonl` y las vistas son regenerables (no editar); la capa derivada **propone** hechos que el letrado **cura** en `HECHOS_X.md` (propiedad humana).
- **Build incremental:** correo + WhatsApp primero; índice de artefactos por hash desde el día 1.
- **Ubicación prevista:** `01_Procesado/Cronologia/` (coherente con `01_Procesado/Emails/`).

---

## 3. Las tres fichas (Decisión 3)

### 3.1 Ficha del ACTO

**Núcleo (siempre):**
- `id_ficha` — estable, opaco.
- `procedencia` — fuente {correo|whatsapp|crm|entrevista|documental|registral} · localizador_interno · clave_natural · **ref. hash de intake** (la custodia ya existe en `00_Input/_intake_hashes.json` + `_intake_log.jsonl`).
- `cuando` — **fecha en EDTF (ISO 8601-2)** · `fecha_fin` opcional (actos durativos) · **orden_relativo** (funciona incluso sin fecha; secuencia en la fuente).
- `tipo` — categoría · subtipo (el **canal** no va aquí: está en `procedencia.fuente`).
- `quien` — (actor_resuelto · papel_en_el_acto) [+ `en_representacion_de` cuando aplique → relación de representación, ver §4].
- `que_dice` — `puntero_al_literal` (no se copia) · `parafrasis` (+autor +fecha, marcada como paráfrasis) · `requiere_transcripcion`.
- `alcance_probatorio` — contenido / existencia / metadatos / mixto.
- `anclaje` — A–E.
- `modo_recuperacion` — directa / reconstruida-desde-cita / reenviada.
- `estado_registro` — vigente / editado / borrado / parcial.

**Opcionales (los 3 primeros OBLIGATORIOS si la fuente es digital):** `nivel_formalizacion` · `contexto_hilo` · `idioma` · `fecha_documento` · `fiabilidad_fuente` · `adjuntos` (por hash) · `pendiente_revision` · `etiquetas`.

**A nivel de almacén (no casillas):** marca "generada por pipeline + fecha"; ediciones humanas a la paráfrasis en el log; cabecera "generado, no editar".
**Invariante:** ningún acto canónico es un hecho inferido.

### 3.2 Ficha de ENLACE

Distinción vertebral: `modo_origen` = automático / heurístico (a revisar) / analítico (juicio del letrado, work-product).

**Núcleo:** `id_enlace` · `origen` (tipo {acto|artefacto|hecho|hipótesis|presunción} · id · **selector interno** opcional para fragmento) · `destino` (tipo · id · selector interno) · `funcion` (documenta-atestigua | corrobora-directa | indiciaria | contradice | menciona | reconstruye | contexto) · `signo` (apoya/socava/neutro) · `magnitud` (alta/media/baja) · `modo_origen` · `es_simetrico` (bool).

**Opcionales (sobre todo analíticos):** `autor`+`fecha` · `justificacion` (OBLIGATORIA en contradice y en apoyos a presunción) · `estado_revision` (pendiente/confirmado/descartado) · `matiz_contradiccion` (de_contenido/de_credibilidad/de_autenticidad).

**Invariantes:** la fuerza vive en el enlace, no en el hecho; "contradice" no resuelve (su superación posterior = enlace/evento nuevo, no campo mutable); enlaces **binarios** (la pluralidad de indicios del 386 y la convergencia se leen del grafo y se agregan en el nodo de presunción); impugnar autenticidad/credibilidad es un **acto procesal** (evento enlazado), no un campo.

### 3.3 Ficha del HECHO DERIVADO (capa derivada; alimenta `HECHOS_X.md`)

El acto dice "consta en la fuente"; el hecho derivado dice "quedó probado". No embebe apoyos (se leen del grafo).

**Núcleo:** `id_hecho` · `hecho_bruto` (descriptivo) + `calificacion_asociada` (opcional, lectura jurídica — separar el hecho de la calificación es control clave anti-contaminación) · `clasificacion_217` (constitutivo/impeditivo/extintivo/excluyente) · `tipo_hecho` (sustantivo/procesal/negativo) · `parte_con_carga` (+ `motivo_inversion` opcional, art. 217.7) · `estado_procesal` (no_valorado/probado/no_probado/parcial/pacífico/irrelevante) · `estatus_soporte` 🟢🟡🔴 **calculado del grafo** (no manual) · `credibilidad` (eje 2) · `funcion_inferencial` (final/intermedio/contextual).

**Bloques opcionales:**
- **Presunción (general 385/386):** tipo {ninguna/judicial_386/legal_385} · naturaleza {iuris_tantum/iuris_et_de_iure} · admite_prueba_contrario · nexo_logico + calidad "preciso y directo" · estado {aplicada/destruida/no_aplicada}.
- **Dispensa de prueba (art. 281):** ninguna / admitido_expreso / admitido_tácito / notorio / máxima_experiencia.
- `disponibilidad_probatoria` + `parte_mejor_disponibilidad`.
- `medio_prueba_previsto`.
- **Tesis/HipótesisCaso** (entidad ligera: id · descripción · estado {principal/subsidiaria/alternativa/descartada}).
- **Punto controvertido** (agrupa versiones rivales; la rivalidad va por enlace).
- Autoría + **log de revisiones** lean {fecha · fase_procesal · estado · motivo}.

**Invariantes:** no embebe apoyos; la pluralidad de indicios del 386 se lee de las flechas entrantes; un hecho directamente atestiguado no es derivado (es acto).

---

## 4. Modelo del actor (Decisión 5)

Formaliza el `identidades.yaml`. Principio: la **identidad es única**; los **roles** son capas que cuelgan. Tres capas separadas: `papel_en_el_acto` (vive en el evento, por-ocurrencia) · `rol_material` y `rol_procesal` (estables, en el actor).

**Núcleo:** `id_actor` · `nombre_canonico` · `tipo` (persona_física/jurídica/órgano/sistema) · `identificadores` (lista; cada uno: tipo · valor · fuente · **desde/hasta** · **estado** {confirmado/probable/erróneo/compartido} · confianza · **origen_dato** · evidencia + autor/fecha) · `alias_grafias` · `estado_resolucion` global · **[persona jurídica] ciclo de vida** (denominación actual · denominaciones previas con fechas · forma jurídica · estado {activa/disuelta/liquidada/absorbida} · entidad_previa) · `ambito` (caso/recurrente) + **gobernanza RGPD** (finalidad · base jurídica, a nivel de registro).

**Roles:** `rol_material` (solo OBJETIVOS; "titular real declarado" sí) · `rol_procesal` **por procedimiento** {procedimiento · rol}.

**Relaciones (grafo, registros propios, con fechas):** representación (apoderado_de/representa_a) con tipo_poder · alcance · fuente · fechas (el evento apunta a esta relación) · administrador_de · socio_de/participa_en (**con %**) · control_efectivo_de · empleado_de · familiar_de · abogado_de.

**Invariantes:** identidad **reutilizable** entre casos, pero **roles y calificaciones case-scoped**; las calificaciones del velo (administrador de hecho, titular real efectivo, confusión patrimonial) NO son roles ni flags → son hechos derivados; la resolución de identidad es work-product revisable, no dogma.

---

## 5. Tipología cerrada (Decisión 6)

Principio: categorías de alto nivel **cerradas**; hojas con variedad = lista **semilla** extensible con gobernanza (valor nuevo se cuelga de su categoría, no texto libre).

- **Acto:** categoría CERRADA (comunicación · actuación · acto documental · hito externo); subtipo SEMILLA (mensaje, llamada, nota de voz, reunión/visita, declaración; encargo, emisión de oferta, negociación, pago, requerimiento/burofax; firma de contrato/oferta, otorgamiento de poder, emisión de factura/certificado; inscripción registral, publicación oficial, nota simple/mercantil, resolución, prensa).
- **Enlace (CERRADO):** función (7) · signo (apoya/socava/neutro) · modo_origen (automático/heurístico/analítico) · matiz_contradicción (contenido/credibilidad/autenticidad).
- **Hecho derivado (CERRADO):** 217 (4) · tipo_hecho (sustantivo/procesal/negativo) · función_inferencial (final/intermedio/contextual) · estado_procesal (6) · dispensa (5) · presunción (tipo/naturaleza/estado).
- **Actor:** tipo CERRADA · rol_procesal CERRADA (actora·demandado·reconviniente·tercero·testigo·perito·órgano) · rol_material SEMILLA · relaciones CERRADA-con-extensión.
- **Transversales CERRADAS:** anclaje A–E · estado_registro · alcance_probatorio · modo_recuperación · nivel_formalización · estado_resolución_identidad · precisión temporal vía EDTF.

---

## 6. IDs (Decisión 4)

**Dos regímenes:**
1. **Congelados por contenido** (ACTO, ARTEFACTO): id derivado de la huella del contenido (clave natural / sha256); libro `huella→id` → idempotente, re-ejecutar no renumera, upgrade conserva id.
2. **Asignados y persistidos** (ACTOR, ENLACE, HECHO DERIVADO, HIPÓTESIS): se asignan al crear y se guardan (no son hasheables); igual de estables.

Ambos en `_registro_cronologia.json`.

**Formato:** opaco, secuencial, prefijo por tipo, 5 dígitos, global por expediente, NO parlante: `EVT-` (acto) · `ATT-` (artefacto) · `ENL-` (enlace) · `HD-` (hecho derivado) · `ACT-` (actor) · `HIP-` (hipótesis).

**Cita:** el id es ancla interna; en la demanda se cita por nº de documento + pinpoint, con el id como respaldo estable por debajo.

**Invariantes:** idempotencia; regla de upgrade (conserva id); dedup colapsa a un id sumando procedencias; `EVT-id` ≠ `MSG-id` del correo (se enlazan por pinpoint).

---

## 7. Estado y siguientes pasos

- **Hecho (diseño):** Fase 0 (inventario de fuentes), Fase 1 (esquema del evento — D1, D2, D3, D4, D6), Fase 2 (identidades — D5).
- **Pendiente (diseño):** Fase 3 (correlación vs dedup entre fuentes — algoritmo y reglas; el enlace ya absorbe buena parte), Fase 4 (tiempo heterogéneo), Fase 5 (arquitectura de ingesta: un atomizador por fuente), Fase 6 (vistas y entregable humano + custodia), Fase 7 (alcance piloto: correo + WhatsApp).
- **Build:** en `core/` de FeesDefender, por Claude Code, incremental (correo + WhatsApp primero), tras cerrar al menos la Fase 3 y con el motor de correo terminado.

---

*Documento vivo. Se actualiza al cerrar cada fase de diseño.*
