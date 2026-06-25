# Cronología Unificada de Prueba — Especificación de diseño

> **Versión:** v7 (2026-06-25) — **DISEÑO COMPLETO**
> **Estado:** **DISEÑO CERRADO, 8 fases (0–7).** Fases 0–2 (esquema del evento, D1–D6). **Fase 3 (correlación) COMPLETA (F3.D1–D5).** **Fase 4 (tiempo heterogéneo) COMPLETA (F4.D1–D2).** **Fase 5 (arquitectura de ingesta) COMPLETA (F5.D1–D2).** **Fase 6 (vistas y custodia) COMPLETA (F6.D1–D2).** **Fase 7 (alcance del piloto) COMPLETA (F7.D1).** Siguiente paso: **BUILD** en Claude Code, no más diseño.
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
- **`_registro_cronologia.json`** — libro persistente NO derivable: mapa `huella→id` congelado, actores resueltos, enlaces, **decisiones humanas sticky** (estado_revision confirmado/descartado). Si se borra, se rompen las citas.
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

**Opcionales (sobre todo analíticos):** `autor`+`fecha` · `justificacion` (OBLIGATORIA en contradice y en apoyos a presunción) · `estado_revision` (pendiente/confirmado/descartado) · `matiz_contradiccion` (de_contenido/de_credibilidad/de_autenticidad) · **`riesgo_tergiversacion`** (bool; reenvío descontextualizado o cita parcial — añadido en F3.D2) · **log de revisiones lean** {autor·fecha·motivo·estado_anterior→nuevo} (añadido en F3.D3) · **`requiere_precedencia`** (bool, default falso; en enlaces indiciarios cuya validez depende del orden temporal — añadido en F4.D2; ver §8.2).

**Invariantes:** la fuerza vive en el enlace, no en el hecho; "contradice" no resuelve (su superación posterior = enlace/evento nuevo, no campo mutable); enlaces **binarios** (la pluralidad de indicios del 386 y la convergencia se leen del grafo y se agregan en el nodo de presunción); impugnar autenticidad/credibilidad es un **acto procesal** (evento enlazado), no un campo.

### 3.3 Ficha del HECHO DERIVADO (capa derivada; alimenta `HECHOS_X.md`)

El acto dice "consta en la fuente"; el hecho derivado dice "quedó probado". No embebe apoyos (se leen del grafo).

**Núcleo:** `id_hecho` · `hecho_bruto` (descriptivo) + `calificacion_asociada` (opcional, lectura jurídica — separar el hecho de la calificación es control clave anti-contaminación) · `clasificacion_217` (constitutivo/impeditivo/extintivo/excluyente) · `tipo_hecho` (sustantivo/procesal/negativo) · `parte_con_carga` (+ `motivo_inversion` opcional, art. 217.7) · `estado_procesal` (no_valorado/probado/no_probado/parcial/pacífico/irrelevante) · `estatus_soporte` 🟢🟡🔴 **calculado del grafo** (no manual; fórmula en §7.4) · `credibilidad` (eje 2) · `funcion_inferencial` (final/intermedio/contextual).

**Bloques opcionales:**
- **Presunción (general 385/386):** tipo {ninguna/judicial_386/legal_385} · naturaleza {iuris_tantum/iuris_et_de_iure} · admite_prueba_contrario · nexo_logico + calidad "preciso y directo" · estado {aplicada/destruida/no_aplicada}.
- **Dispensa de prueba (art. 281):** ninguna / admitido_expreso / admitido_tácito / notorio / máxima_experiencia.
- `disponibilidad_probatoria` + `parte_mejor_disponibilidad`.
- `medio_prueba_previsto`.
- **Tesis/HipótesisCaso** (entidad ligera: id · descripción · estado {principal/subsidiaria/alternativa/descartada}).
- **Punto controvertido** (agrupa versiones rivales; la rivalidad va por enlace; nodo donde se computa el tope por rival seria — ver §7.5; también acoge el **punto controvertido temporal** de §8.2).
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
- **Transversales CERRADAS:** anclaje A–E · estado_registro · alcance_probatorio · modo_recuperación · nivel_formalización · estado_resolución_identidad · precisión temporal vía EDTF · **relación de orden temporal (antes/después/contiene/contenido_en/indeterminado — §8.2).**

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

## 7. Correlación entre fuentes (Fase 3 — F3.D1 a F3.D5)

La ficha de enlace (§3.2) ya aporta la **estructura** de la correlación; la Fase 3 aporta el **algoritmo y las reglas**. Regla rectora: **dentro de una fuente se DEDUPLICA** (copias idénticas colapsan a un id conservando procedencias); **entre fuentes NO se fusiona, se CORRELACIONA** (un WhatsApp y un correo del mismo hecho son pruebas independientes que se enlazan; un hecho probado por N fuentes vale más).

### 7.1 Desenlaces y regla de deslinde (F3.D1)

Dos **planos ortogonales**:
- **Plano de ACTOS:** Colapso (intra-fuente, mismo registro → un evento, suma de procedencias) · Correlación (inter-fuente, acto distinto, mismo hecho → enlace, nunca fusión) · Reconstrucción (acto sin registro directo, solo referido → evento reconstruido baja confianza; **provisional y subsidiario: cede ante el acto directo cuando aparece** — ver §8.1) · Sin relación.
- **Plano de ARTEFACTOS** (§2.5): Identidad por hash · Familia de versiones · Distintos.

Independientes: dos actos correlacionados pueden portar, cada uno, el mismo artefacto. **Orden de resolución (actos):** ¿mismo registro de misma fuente? → Colapso; ¿uno es mera prueba del acto del otro? → enlace `documenta` (no es par de actos); ¿actos distintos sobre el mismo hecho? → Correlación; ¿acto solo referido sin registro? → Reconstrucción; resto → Sin relación.

**Sin nodo `EventoMaterial`** (sería puerta trasera de inferencia, contra §1.3): el destino de convergencia ya existe — acto canónico atestiguado (los demás lo corroboran vía enlace evento↔evento) o hecho derivado (§3.3).

**Registro de tercero datado** (log CRM, acta): proof-link (`documenta`) por defecto; **acto propio solo si el registrar tiene efecto jurídico/normativo directo** (asiento registral, notificación por sede electrónica).

**Dos corroboraciones distintas:** de **CONTENIDO** (por orígenes independientes) y de **CIRCULACIÓN** (por canales). No se suman igual (ver §7.4 y §7.6).

### 7.2 Señales de emparejamiento (F3.D2)

Lo que produce es una **confianza de emparejamiento explicable** ("¿mismo suceso?"), **≠ fuerza probatoria** ("¿cuánto prueba?"). Peso por **rareza/diagnosticidad**. Cada señal declara plano/desenlace y si corrobora contenido o circulación. Anclaje, no impresión.

- **S0 — Referencia explícita:** **S0a (formal**: In-Reply-To/Message-ID, cita íntegra, ref. registral → puede autoenlazar la relación, no la interpretación) **/ S0b (informal**: "como te dije ayer" → requiere apoyo o cola). Flag `riesgo_tergiversacion` → siempre a cola + vista comparativa.
- **S1 — Artefacto compartido** (hash idéntico o casi-idéntico confirmado): por defecto **circulación**. **S1b** (orígenes independientes → contenido: conocimiento/autenticidad) = elevación **siempre por juicio del letrado**.
- **S2 — Ancla dura de contenido** (importe, fecha-clave, ref. oficial, ID, nombre propio raro): contenido, ponderada por rareza. Modo **"estructura"** (multi-campo, sin ancla puntual; para entrevistas) → solo candidatos a revisión. **S2a** (identificador de contexto: nº expediente, ref. finca) = circulación. **Plantillas/cláusulas estándar** (cláusula 3% honorarios, burofaxes genéricos) = lista **no-diagnóstica** (config del expediente).
- **S3 — Actores resueltos coincidentes:** rareza = frecuencia + **lista a priori de actores omnipresentes** (peso bajo fijo) + **co-ocurrencia rara**. La diagnosticidad condicional a hipótesis → §7.4.
- **S4 — Proximidad temporal en ventana:** nunca empareja sola; sobre todo descarta. Opera sobre la **distancia entre intervalos** de §8.2 (intervalos solapados → distancia 0).
- **S5 — Solapamiento temático/asunto:** débil, dependiente de fuente.

**Bloqueo en dos niveles:** duro (≥1 ancla compartida) + **blando** (ventana+tipo+patrón / similitud semántica) **solo para candidatear a revisión**; *embeddings* = red de pesca, no ancla citable. Emparejamiento **binario**; la convergencia emerge del grafo.

**★ Invariante de no-fuga:** la fuerza probatoria nunca depende del score de matching; el cómputo del semáforo (§7.4) usa solo enlaces `confirmado`.

### 7.3 Enrutamiento: automático / cola / no-propuesto (F3.D3)

Tres destinos con el **medio generoso** (falso negativo > falso positivo en corroboración; el filtro humano + el marcado de `modo_origen` neutralizan el falso positivo); **autoenlace conservador**.

- **AUTOENLACE** (`modo_origen=automático`): solo **S0a-formal** + **identidad por hash idéntico**. Guardas: hash de plantilla no-diagnóstica unifica el artefacto pero no crea correlación de contenido; chequeo de frecuencia de cabecera (corrupta/reciclada → no autoenlaza); `riesgo_tergiversacion` → cola.
- **COLA/CANDIDATO** (`heurístico`, `pendiente`): recall-bias.
- **NO-PROPUESTO** (non-link): determinista.

**Rank de cola = ordinal interno INTERMEDIO** (el número **nunca se muestra**; la UI muestra "Tier X · posición N"). Amurallado: no decide ruta, no es magnitud, no entra en §7.4.

**Asimetría por tipo:** corroboración recall-bias; **contradicción conservadora (NUNCA se autoenlaza)**, pero salta la compuerta para revisión.

**Compuerta de relevancia + vías de escape (anti sesgo de confirmación):** candidatos solo-blandos emergen si tocan tesis/etiqueta viva o nodo fuerte; PERO toda **contradicción potencial salta la compuerta** (señal de contradicción textual con bypass); **cupo de exploración fuera de tesis**; etiqueta "fuera de tesis"; Tier 1 incluye lo que **destruye una presunción del 386**.

**Priorización:** contradicciones (máx.) → Tier 1 (mueve 🟡→🟢 / hipótesis / destruye 386) → Tier 2 (señal fuerte) → Tier 3 (blandos, por lote).

**Gobernanza:** decisión humana **sticky y persistida**; reapertura solo con flag `reabierto_por_nueva_prueba` + traza; **log de revisiones lean** en el enlace; **cola de reaperturas** priorizada y agrupada por origen de prueba; métricas de backlog y reaperturas; estatus explícito **"archivado, no revisado"** para Tier 3.

**★ Invariante:** ningún enlace `modo_origen=automático` sostiene un hecho en `HECHOS_X.md` sin estar `confirmado`.

### 7.4 Fórmula de agregación del 🟢🟡🔴 (F3.D4)

Regla **estructural categórica** (no suma ponderada; el matiz de frontera vive en la **explicación autogenerada**, no en un campo). Lee la forma del soporte en el grafo.

1. **Solo enlaces `confirmado`** (autoenlaces no cuentan hasta confirmarse).
2. **Independencia en 3 grados** por aportación: `independiente` / `probable_dependencia` / `fuente_común`; solo `independiente` da **pluralidad fuerte** (386 real); los demás colapsan conservadoramente a uno o van a revisión. Default conservador; elevar a `independiente` = juicio del letrado.
3. **Base por tipo:** prueba directa robusta → 🟢; ≥2 indicios independientes diagnósticos convergentes (con rival usable debilitada) → 🟢; **indicio único de gran fuerza** → 🟢 solo con checklist estricto + motivación expresa del letrado (el sistema sugiere "candidato a gran fuerza", no cierra automático); 1 ordinario / dependientes / no-diagnósticos → 🟡; ninguno → 🔴.
4. **Diagnosticidad condicional (ACH):** sin rival **usable** (no declarada o vaga → `diagnosticidad_no_evaluable`), la vía indiciaria no sube a 🟢 (cautela 🟡), pero la rival vaga no añade tope. Las rivales deben ser concretas/excluyentes/operativas.
5. **Cadenas:** `min` **por ruta** + **convergencia entre rutas independientes** (dos rutas indep. ≥🟡 fuerte → pueden sostener 🟢 aunque una tenga eslabón amarillo); no `min` global.
6. **Topes (degradan):** rival **seriamente sostenida** → 🟡 (ver §7.5); socava cualificado (§7.5); presunción 386 ≤ hecho base + nexo preciso y directo; credibilidad/fiabilidad bajas. **Indeterminación temporal (§8.2):** una inferencia indiciaria con `requiere_precedencia=true` cuyo par está `orden_indeterminado` **no cuenta** (bloqueo); si no requiere precedencia, **degrada**.
7. **Circulación aparte** (no eleva el contenido; alimenta su propio hecho "ambas partes lo conocían"); **cómputo neutral a la carga** (el 217 se cruza en una **vista de riesgo** de `HECHOS_X.md`, que muestra siempre el bloque conjunto `estatus_soporte + clasificacion_217 + parte_con_carga + dispensa_281`).
8. **Hechos negativos** (`tipo_hecho=negativo`): vía propia (ausencia esperable de rastro + deber de documentar + facilidad probatoria 217.7 + ausencia de indicios positivos contrarios); no aplicar 386 mecánicamente.
9. **Salida:** estatus **propuesto** + explicación citando ENL; el letrado cura y sobrescribe con motivo.

> Material build-ready: pseudocódigo `calcular_estatus_soporte` + tabla "estructura del soporte → rango de estatus" (en `handoff_F3D4_stresstest_claude.md`).

### 7.5 Contradicción inter-fuente en el cómputo (F3.D5)

El sistema **no resuelve**; representa el conflicto, cita ambas versiones con pinpoint, topa y marca controvertido; la resolución (humana/judicial) = **evento nuevo**, nunca mutando la contradicción.

- **Tres dianas según `matiz_contradiccion`** (proyección múltiple: diana principal + efectos secundarios):
  - **De contenido** → **versiones rivales (N, paramétricas, no solo ¬X**: 21,3M vs 19M vs 20M) bajo un **punto controvertido**; cada versión computa su estatus por §7.4; se reduce al mecanismo de rival ACH. En hecho **compuesto**, el tope afecta solo al **componente discutido**.
  - **De credibilidad** → pega en el **eje 2** de los actos de apoyo del hecho (no en el contenido); se propaga como tope por credibilidad baja.
  - **De autenticidad** → impugnación = **acto procesal propio** (evento enlazado, art. 326); afecta anclaje/alcance solo con **soporte mínimo**; infundada → impugnación táctica + socava credibilidad del impugnante (no saca el documento de la capa canónica por sí sola).
- **Peso simétrico** (soporte propio × diagnosticidad): un socava 🔴 apenas mella un 🟢; un socava 🟢 crea punto controvertido real. **Sin flag de "impacto cualitativo"** (la diagnosticidad ya lo capta). **Multi-rol** permitido (un acto `contradice(X)` débil + `indiciaria(Y)` fuerte).
- **Degradación una sola vez en el NODO** punto controvertido (compara soportes, computa el tope "rival seria"); el enlace `contradice` solo expresa la rivalidad → evita doble contabilidad.
- **Rebatibilidad** solo por evento/enlace nuevo; **vista de historial de conflicto** en el punto controvertido; el cómputo lee **soporte actual** de cada versión, no la profundidad de recursión.
- **Etiqueta analítica `version_mejor_soportada`** (compara `estatus_soporte` entre rivales; preferencia analítica/work-product, **no verdad judicial**).
- **Identidad (Fase 2) ANTES que contradicción** (si no, se fabrican controversias que desaparecen al resolver actores/artefactos).
- **Acoge el punto controvertido TEMPORAL** (§8.2): cuando dos fuentes imponen órdenes incompatibles (A<B vs B<A), la rivalidad es sobre el *cuándo* y se trata por esta misma maquinaria (no se auto-resuelve).

> Material build-ready: mini-pseudocódigo `procesar_contradiccion` (en `handoff_F3D5_stresstest_claude.md`).

---

## 8. Tiempo heterogéneo (Fase 4 — F4.D1 a F4.D2)

El esquema (§3.1) ya fija el **contenedor** temporal (EDTF/ISO 8601-2, `fecha_fin`, `orden_relativo`, `fecha_documento`, `modo_recuperacion`); la Fase 4 fija la **semántica**: qué tiempo se coloca en la línea y cómo se comparan tiempos de precisión desigual.

### 8.1 Los tres tiempos del evento (F4.D1)

Un solo tiempo **ancla la línea = el tiempo del HECHO** del acto (`cuando.fecha`, EDTF). Cinco reglas de deslinde:

1. **Acto no declarativo** (correo, firma, pago, inscripción): hecho = enunciación; una sola fecha, sin añadir nada.
2. **Acto declarativo NARRATIVO** (entrevista, "como te dije ayer"): el acto entra en la línea como **enunciación**; el hecho pasado narrado va por **enlace de testimonio** o por **evento reconstruido provisional** (`modo_recuperacion=reconstruida`, baja confianza, unido por `reconstruye`). El reconstruido es **subsidiario y cede ante el acto directo** cuando aparece (su enunciación sobrevive como testimonio; el nodo del hecho pasa al acto preciso) — gobernado por el orden de resolución de §7.1; evita el doble cómputo que vigila la independencia-3-grados de §7.4.
3. **Acto declarativo PERFORMATIVO** (efecto constitutivo: reconocimiento de deuda, renuncia, acuerdo verbal): acto único, hecho = enunciación, **sin** evento reconstruido hijo; el efecto jurídico va a `calificacion_asociada` (capa derivada, §3.3). Criterio reusado de §7.1 ("acto propio solo si efecto jurídico directo"). No mete inferencia en la capa canónica (respeta §1.3).
4. **Tiempo de REGISTRO = procedencia, NUNCA posición** en la línea (timestamp de log, fecha de extracción, fecha del soporte). Vive en `procedencia` + `fecha_documento`; solo autenticidad y detección `fecha_documento ≠ fecha_hecho`. Cuando es el **único acotador** de un hecho difuso, funciona como **techo** del intervalo (§8.2), no como posición del hecho.
5. La **enunciación no se pierde nunca** (es la fecha del propio acto, o se recupera por `reconstruye`) → "qué se dijo/supo cuándo" (decision time) es una **VISTA**, no un campo.

**Sin campos nuevos.** No tocado por el stress-test pero fijado: reloj de dispositivo manipulable = "fecha afirmada por la fuente" + eje 3 de fiabilidad, sin tocar el anclaje temporal; husos horarios = ver §8.2.

### 8.2 Orden parcial y comparación de intervalos (F4.D2)

La cronología es un **ORDEN PARCIAL**, no total.

- **Proyección a intervalo:** cada acto se proyecta a `[suelo, techo]` derivado de EDTF (instante preciso = intervalo degenerado; "~marzo 2024" = `[2024-03-01, 2024-03-31]`; cotas abiertas `[−∞, F]` / `[F, +∞]`). Los **actos durativos** usan `fecha_fin`: span `[suelo(inicio), techo(fin)]`. `suelo`/`techo` son **derivados calculados**, no casillas manuales.
- **Cinco relaciones operativas, todas derivadas:** `antes` · `después` · `contiene` · `contenido_en` · `orden_indeterminado`. Contención: `contiene(A,B)` ⟺ suelo(A)≤suelo(B) y techo(B)≤techo(A) (relación CONOCIDA y útil — "durante la negociación" —, distinta de orden desconocido). Se descarta `contiguo_a`/*meets* (frágil con precisión heterogénea).
- **Propagación segura ANTES de declarar `orden_indeterminado`** (Temporal Constraint Networks): cierre transitivo de `antes/después` (A<B<C ⟹ A<C aunque aparenten solapar) + estrechamiento por cota anclada. **Dos guardas (Modelo B):** (a) vive en una capa derivada de **"intervalo efectivo"** y **NUNCA muta el `cuando.fecha` canónico** (lo inferido se marca inferido); (b) solo propagan constraints **anclados (A/B, confirmados)**, jamás reconstruidos/baja confianza. No Allen borroso completo.
- **`orden_relativo` (intra-fuente):** si las fechas absolutas intra-fuente solo **solapan** (mensajes consecutivos, precisión gruesa), `orden_relativo` **refina y manda**; si las **contradicen estrictamente** (una dice A<B, la otra B<A), no se prioriza ninguno: se marca `inconsistencia_temporal_de_fuente` (diagnóstico derivado; degrada el eje 3 de esa fuente en ese tramo) y va a revisión. **Entre fuentes**, `orden_relativo` no cruza; si los intervalos imponen órdenes incompatibles → **punto controvertido temporal** por la maquinaria de §7.5 (no se auto-resuelve).
- **Consumo — prescripción:** el motor expone suelo y techo, obliga a **seleccionar explícitamente el criterio jurídico** del cómputo (el *dies a quo* depende del tipo de acción y de la *actio nata*, art. 1969 CC, no de una regla neutra de extremos) y devuelve un **rango argumental con explicación, nunca una fecha única** (anti-autolesión).
- **Consumo — presunciones (386 LEC):** una inferencia indiciaria con `requiere_precedencia=true` (flag analítico del enlace, §3.2) cuyo par está `orden_indeterminado` queda **bloqueada** (no cuenta en §7.4); si solo requiere co-ocurrencia/pertenencia a periodo/proximidad (`requiere_precedencia=false`), **degrada**, no bloquea.
- **Consumo — señal S4** (§7.2): distancia = separación entre intervalos (solapados → 0); nunca empareja sola.
- **EDTF — alcance:** F4.D2 opera sobre EDTF que resuelve a **intervalo único**; conjuntos `{..}`/alternativas y lenguaje relativo no resoluble ("la primavera siguiente a X") → `orden_indeterminado` pendiente de **anclaje contextual** (Fase 5 + curación humana). El "relativo a otro evento" es una **restricción del grafo** (encaja en la propagación), no EDTF libre.
- **Render:** las cotas abiertas se muestran **≤F / ≥F**, nunca ∞ literal; los pares `orden_indeterminado` se muestran como un **haz** simultáneo, no como secuencia.
- **Timecode SMPTE + husos:** la entrevista es **un** acto canónico; el timecode SMPTE es **pinpoint** y soporte de `orden_relativo` interno de la sesión (no se absolutizan los fragmentos). Para fuentes con instante real, la comparación opera siempre sobre **instante normalizado a UTC conservando el offset original** (render y trazabilidad).

**Campos nuevos:** solo `requiere_precedencia` (enlace indiciario, §3.2) y el diagnóstico derivado `inconsistencia_temporal_de_fuente`. El resto son relaciones derivadas y reglas de consumo.

> Material de stress-test: `handoff_F4D1_stresstest_claude.md` y `handoff_F4D2_stresstest_claude.md`.

---

## 9. Arquitectura de ingesta (Fase 5 — F5.D1 a F5.D2)

Cómo cada fuente cruda se convierte en actos del esquema común, **sin duplicar** el motor de correo (congelado) ni `organizar-sala-lectura` (nivel fichero). La cronología vive **por encima** de ambos.

### 9.1 Contrato del adaptador y frontera de tres capas (F5.D1)

**Tres capas estrictas, con frontera tajante:**

1. **ATOMIZADOR** (específico de fuente): dueño de los bytes y de las rarezas del formato; convierte el crudo en **átomos con clave natural estable congelada por contenido**. El **motor de correo congelado ES el atomizador de "correo"** (no se toca). Mensajería, CRM y entrevistas necesitan el suyo. El **documental** usa un **ingestor de artefactos** (registra por hash; los actos de otras fuentes lo enlazan), **no** un atomizador que cree actos — salvo los **actos documentales con fecha propia** (firma, inscripción, factura; §1.2), que sí acuñan acto y, si el documento es su única fuente, nacen ahí.
2. **ADAPTADOR/PROYECTOR** (específico de fuente, delgado, librería compartida): mapea cada átomo a una **ficha del acto** (§3.1); normaliza la fecha a EDTF, rellena `procedencia` (incl. ref. hash de intake), fija `alcance_probatorio`/`anclaje`/`modo_recuperacion`, apunta al literal (no copia). Emite **todos los tokens de actor crudos en campos diferenciados** (`actor_rotulo`/`actor_email`/`actor_telefono`/`actor_nif`) **sin elegir ganador**, con **normalización sintáctica aditiva** (minúsculas/E.164/limpieza de NIF) que **conserva la grafía original** (valor probatorio/alias). Para "correo" es **lector de solo lectura** sobre la salida del motor congelado; los campos que la fuente no expone se rellenan por **default determinista** (`alcance_probatorio=contenido`, `nivel_formalizacion=suelto`) o "no determinado", **nunca por inferencia** (no rompe Modelo B) y **sin reabrir** el motor.
3. **NÚCLEO AGNÓSTICO** (idéntico en toda fuente): asigna **EVT-id** por par `(fuente, clave_natural)` → id congelado (`EVT-id ≠` id del átomo de la fuente; se enlazan por pinpoint); **resuelve la identidad** contra el registro de entidades (transversal); deduplica intra-fuente; correlaciona inter-fuente (§7); proyecta el tiempo y ordena (§8); construye enlaces y capa derivada; mantiene `_registro_cronologia.json` y genera las vistas.

**Invariante rector de la frontera:** el adaptador **nunca** asigna EVT-ids, crea enlaces, correlaciona ni resuelve identidad. Ventajas: añadir fuente = atomizador + adaptador sin tocar el núcleo; el criterio sensible (identidad) concentrado; re-ejecutar no renumera.

**Granularidad declarativa:** "un acto vs N" es regla declarativa **por fuente** (extensión de §1.2: entrada de log CRM = 1 acto; la ficha-cabecera del CRM = 0); el atomizador la **ejecuta**, no la decide.

**Identidad de artefacto** (§2.5) entre fuentes: el adaptador emite el artefacto con su hash de intake; el núcleo **colapsa soporte por hash pero nunca fusiona actos** entre fuentes.

**Colisión de claves naturales:** el libro mapea por par `(fuente, clave_natural)`; el espacio está **aislado por fuente**, así que dos fuentes no funden un acto por azar.

**Idempotencia y upgrade:** libro `huella→EVT-id`; re-ejecutar no renumera; un átomo de baja calidad que reaparece mejor conserva su id (regla de upgrade del motor de correo, generalizada). Si un upgrade **parte un átomo ya citado**, el original conserva el id, el hermano toma el siguiente libre y el split **salta a revisión humana** (no migración silenciosa).

### 9.2 Encaje con las capas de fichero, staging y orden de construcción (F5.D2)

- **Anclaje al crudo; sala de lectura solo como PISTA.** El atomizador ancla custodia y pinpoint **siempre al crudo de `00_Input` + su hash de intake** (inmutable), nunca a las copias renombradas de `01_Procesado/Sala lectura`. Puede consumir el `indice_documental.yaml` de la sala de lectura como **pista débil**, marcada `origen_dato=pista_sala_lectura`; si el crudo la contradice, **prevalece el crudo** y la discrepancia se registra como incidencia de calidad de la sala de lectura. Niveles distintos: sala de lectura = fichero; cronología = acto; coexisten.
- **Staging = zona lógica única multi-fuente.** Ficheros `01_Procesado/Cronologia/_staging/<fuente>.jsonl` (por fuente, regenerables, cabecera "no editar"), pero el núcleo **siempre opera sobre la UNIÓN** para correlación, orden global e índice de artefactos. El almacén enriquecido + `eventos.jsonl` + `_registro_cronologia.json` viven en la raíz de `Cronologia/`. Zonas raw (`00_Input`) → staging → curada (almacén) → vistas (regenerables).
- **Re-subida = nueva evidencia, nunca sobrescritura.** Un fichero re-subido con hash distinto entra como crudo nuevo (disciplina del **intake**); no se borra el anterior. La relación entre versiones se modela con la **familia de versiones de artefacto** (§2.5, subtipo cadena-con-orden), no con una función de enlace nueva.
- **Llegadas tardías idempotentes.** Datos tardíos (con actos anteriores a lo ya cargado) se **intercalan** en el orden parcial; el recálculo es idempotente y las decisiones humanas sticky se reaplican; lo que cae en tramo ya curado **salta a revisión** vía la gobernanza de reapertura de §7.3 (`reabierto_por_nueva_prueba`), nunca pisa.
- **Independencia de la sala de lectura.** La cronología se construye solo desde `00_Input` + el motor de correo congelado; si la sala existe, aporta pistas; si no, no falta nada esencial. Sin acoplamiento oculto.
- **Anti-confusión:** `CRONOLOGIA_FICHEROS` (sala de lectura, nivel fichero) vs `CRONOLOGIA_ACTOS` (probatoria, nivel acto), separadas por propósito.
- **`90_Notas personales` — PROHIBICIÓN ABSOLUTA:** ningún módulo lee, escribe, indexa **ni lista** esa carpeta. Se descarta cualquier "válvula de aviso" (listar nombres ya relajaría la regla). Riesgo residual asumido: prueba dejada ahí por error no se señala.
- **Orden de construcción incremental:** correo (congelado) + **WhatsApp primero** (espina temporal del caso), con índice de artefactos por hash desde el día 1; luego CRM, entrevistas, documental/registral. Cada fuente nueva regenera su staging y añade candidatos a la cola sin recalcular ni pisar lo curado.

---

## 10. Vistas, entregable humano y custodia (Fase 6 — F6.D1 a F6.D2)

Reúsa lo cerrado en el motor de correo (vistas regenerables "no editar", formato de lectura, dossiers por `etiquetas`, sellado a `_entregas/` con SHA-256, custodia = almacén work-product / prueba = fuentes) y lo generaliza a **multi-fuente**.

### 10.1 El entregable humano unificado (F6.D1)

Cronología única de actos, regenerable, **declarada "índice de lectura — NO prueba"**.

- **Una entrada por acto:** esqueleto común agnóstico (fecha EDTF en humano · tipo · fuente · actores con papel) + bloque mínimo específico de fuente (correo De/Para/CC/asunto; chat emisor; entrevista hablante+timecode; CRM tipo de actividad; registral ref. oficial).
- **Cuerpo = "extracto de lectura"**, no "literal limpio a secas": si el sentido depende del contexto, se añade ventana mínima (mensaje citado / pregunta previa / cola) o marca de recorte `[…]`; siempre con acceso al original íntegro. Generaliza la regla de respuesta intercalada del motor de correo.
- **Cita al pie = la fuente aportable + pinpoint** (lo citable en el escrito); el `EVT-id` es solo ancla interna (coherente con §6). Cabecera dura "índice de lectura regenerado; no sustituye la fuente"; al exportar a juzgado, acompaña al original, no lo desplaza (la cronología es work-product/demostrativo, subordinado a la prueba documental, arts. 318/326 LEC).
- **Dos etiquetas visuales separadas:** "corroborado por fuente independiente" (refuerza contenido) vs "también circuló por" (solo difusión, **prohibido el lenguaje de refuerzo**) — render de la distinción contenido/circulación de §7.1/§7.4.
- **Agrupada por tramos** (año/mes/fase procesal); los actos difusos se muestran como **rango dentro de su tramo, no clavados a un día**; `orden_indeterminado` como subhaz (render de §8.2).
- **Punto controvertido** marcado en neutro, enlazando los actos rivales, **sin semáforo ni conclusión** en la cronología (render de §7.5; la valoración vive en la capa de hechos).
- **Dos vistas enlazadas, no fundidas:** cronología de actos (canónica) ↔ `HECHOS_X.md` (derivada: 🟢🟡🔴 + 217 + carga, curada a mano). La línea de actos alimenta la de hechos por citas `EVT-`.
- **Dossiers temáticos** = la misma vista filtrada por tesis, multi-fuente, bajo demanda; llevan por defecto un **bloque de "actos que tensionan o contradicen la tesis"** (disciplina anti-sesgo de §7.3); si se desactiva, marca explícita "vista parcial de trabajo, no entregable equilibrado".

Todo regenerable, cabecera "no editar"; `HECHOS_X.md` es la única pieza curada a mano. **Cero campos nuevos: es render de §7.1/§7.4/§7.5, §8.2 y la disciplina anti-sesgo de §7.3.**

### 10.2 Custodia transversal y sellado de entrega (F6.D2)

Sellar una entrega = **instantánea congelada y fechada** en `01_Procesado/Cronologia/_entregas/<fecha>/`, con tres bloques separados:

1. **Prueba aportable** = el subconjunto **seleccionado** de documentos de fuente relevantes, copiados con su SHA-256. No se sella el almacén entero: la prueba son los documentos, no la cronología.
2. **Apoyos demostrativos** = `CRONOLOGIA_ACTOS`/dossier marcados "índice de lectura — no prueba" (§10.1), que acompañan a los originales, no los sustituyen.
3. **Manifiesto de custodia transversal** = por documento entregado: fuente · ruta en `00_Input` · hash de intake · los `EVT-` que lo citan. Reproducible y verificable por un tercero.

- **Frontera work-product/prueba reafirmada, nunca mezclada al sellar:** el almacén, `_registro_cronologia.json` y las vistas son work-product, jamás sellados *como* prueba (a lo sumo etiquetados apoyo demostrativo); la prueba son las fuentes apuntadas.
- **Custodia transversal reúsa el intake, no lo rehace:** el manifiesto se apoya en `_intake_hashes.json`/`_intake_log.jsonl` existentes; el sellado consolida en un informe único la cadena de las N fuentes de esa entrega.
- **Inmutable e incremental:** la instantánea sellada no se regenera; la cronología viva sigue aparte; re-sellar = nueva entrega fechada, nunca sobrescribe (coherente con §9.2, "re-subida = nuevo").

---

## 11. Alcance del piloto (Fase 7 — F7.D1)

Scoping del primer build; reúsa la decisión de construcción incremental (correo + WhatsApp primero).

- **Fuentes del piloto: correo + WhatsApp, nada más.** El correo ya está (motor congelado). El piloto añade **atomizador + adaptador de WhatsApp** para las 4 conversaciones de `02_Whatsapp`, priorizando la **espina temporal** (la conversación más larga) y la **ruptura** clave. CRM, entrevistas y documental/registral **quedan fuera** (entran después, incrementalmente, sin tocar el núcleo). OCR de adjuntos = enriquecimiento posterior.
- **Objetivo: validar el núcleo agnóstico end-to-end con dos fuentes reales**, no completar el caso. Que el ciclo **atomizador → adaptador → staging → núcleo** (EVT-id, identidad, dedup, correlación, tiempo, enlaces, vistas) funcione cruzando correo + WhatsApp y produzca la `CRONOLOGIA_ACTOS` unificada + un dossier temático.
- **Criterio de éxito = hechos-test verificables** que ejercitan las piezas difíciles: (1) **correlación, no fusión**, del documento que viaja por dos canales (debe salir como corroboración/circulación bien etiquetadas, §10.1); (2) **resolución de identidad** con su trampa (ficha rotulada con un nombre pero operada por el teléfono de otro → se ata por teléfono, §9.1); (3) **punto controvertido** de contenido y de fecha marcados **sin resolver** (§7.5, §10.1).
- **Hogar de ejecución:** Claude Code local (acceso directo a los ficheros del expediente); el sandbox en nube no monta el almacenamiento.

---

## 12. Estado y siguientes pasos

- **★ DISEÑO COMPLETO (8 fases, 0–7):** Fase 0 (inventario), Fases 1–2 (esquema del evento — D1–D6), **Fase 3 (correlación — F3.D1 a F3.D5)**, **Fase 4 (tiempo heterogéneo — F4.D1 a F4.D2)**, **Fase 5 (arquitectura de ingesta — F5.D1 a F5.D2)**, **Fase 6 (vistas y custodia — F6.D1 a F6.D2)**, **Fase 7 (alcance del piloto — F7.D1).**
- **Siguiente paso = BUILD, no más diseño.** En `core/` de FeesDefender, por Claude Code, incremental (correo + WhatsApp primero), con el motor de correo congelado como primer adaptador. Materiales build-ready disponibles: pseudocódigo de F3.D3/D4/D5 y las tablas/reglas de decisión de los handoffs de stress-test (F4.D1/D2, F5.D1/D2, F6.D1).

---

*Documento vivo. Se actualiza al cerrar cada fase de diseño.*
