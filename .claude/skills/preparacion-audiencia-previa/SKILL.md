---
name: preparacion-audiencia-previa
version: "1.0.1"
description: >-
  Prepara el acto de AUDIENCIA PREVIA de cualquier juicio ordinario civil español (arts. 415-429 LEC),
  en posición actora o demandada. Produce dos entregables con el formato del despacho: la MINUTA de
  audiencia previa (.docx, guion de sala con los cuadros de hechos) y la SOLICITUD DE PRUEBA (.docx,
  escrito procesal de proposición de prueba). Lee demanda, contestación y alegación de nulidad; fija
  los hechos; propone la prueba por chat para visto bueno del letrado; y, si el caso es de
  FeesDefender/Engel & Völkers, guarda en 05_Procedimiento y registra en el intake. Úsala SIEMPRE que
  el usuario diga "preparar la audiencia previa", "minuta de audiencia previa", "solicitud de prueba",
  "proposición de prueba", "cuadro de hechos controvertidos", "la audiencia previa es mañana", o
  mencione un ordinario con demanda y contestación. NO redacta la demanda/contestación
  (escritos-judiciales) ni prepara el juicio (preparacion-juicio-oral).
---

# Preparación de la audiencia previa (civil)

## Posicionamiento

Skill metodológica para la **fase de audiencia previa** de **cualquier juicio ordinario civil**
español (arts. 415→429 LEC). Se sitúa **después** de la demanda y la contestación (ya presentadas) y
**antes** del acto del juicio. Cubre las dos posiciones procesales: **actora** y **demandada**.

**Dos contextos (detéctalo al inicio — ver Fase 0):**

- **Modo FeesDefender / E&V** — el caso es de Engel & Völkers y existe un expediente FeesDefender
  (hay `00_Input/_caso.md`). Activa la terminología propietario/buscador, los patrones de causa de
  pedir E&V (vía `engel-volkers`), guarda en `05_Procedimiento/` y registra en el intake.
- **Modo civil genérico** — cualquier otro ordinario civil. Terminología **neutra** (nombres reales de
  las partes; en su defecto actor/demandado), sin patrones E&V; pregunta **dónde guardar** los `.docx`
  y **omite** el registro de intake. Todo lo demás (8 bloques, cuadros de hechos, gate de prueba,
  source-locked, CENDOJ) es idéntico.

Todas las salidas son **herramientas del letrado para el acto**, no análisis internos. Dos
entregables por defecto:

- `MINUTA_AP_[REF].docx` — guion de sala con las ocho finalidades de la AP (arts. 415→429 LEC) y los
  dos cuadros de hechos (no controvertidos y controvertidos). Lenguaje llano en los bloques que se
  leen en sala; tablas en la fijación de hechos. Formato en [references/formato_minuta.md](references/formato_minuta.md).
- `SOLICITUD_PRUEBA_[REF].docx` — escrito procesal de proposición de prueba, **listo para presentar
  y firmar**. Se genera encadenando con la skill `escritos-judiciales`. Formato y estructura en
  [references/solicitud_prueba.md](references/solicitud_prueba.md).

**Ubicación de los outputs:** en modo FeesDefender, ambos `.docx` van a `05_Procedimiento/` del
expediente (work-product del letrado; la carpeta estaba inerte y esta skill es su primer escritor). En
modo civil genérico, **pregunta la carpeta destino** al letrado.

**Registro en intake (solo modo FeesDefender):** cada output se da de alta en dos sitios — la sección
*Navegación* de `00_Input/_caso.md` (wikilinks) y un manifiesto `05_Procedimiento/_index.md`. Mecánica
exacta en [references/manifiesto_y_registro.md](references/manifiesto_y_registro.md), vía
`scripts/registrar_outputs.py`. En modo civil genérico **no hay registro de intake**.

**Convivencia obligatoria:** `verificacion-anclada-fuente` (source-locked) en la fijación de hechos y
en la validación. **Encadenamiento:** `escritos-judiciales` (solicitud), `cendoj-descarga`
(verificación de jurisprudencia), skill de cliente `engel-volkers` cuando aplique. **Predecesoras:**
`preparacion-litigio-civil`, `viabilidad-prerelleno`. **Sucesora natural:** `preparacion-juicio-oral`
(reutiliza estos cuadros de hechos tras el acto).

**Flujo operativo paso a paso** (Fases 0–7) en [references/flujo.md](references/flujo.md). Léelo al
empezar la preparación, antes de generar nada.

## Qué hace y qué NO hace

Hace:

- Lee la **documental procesal** del expediente: demanda, contestación, reconvención y/o alegación de
  nulidad, autos de admisión, providencia de señalamiento, y la documental de `00_Input/`
  (encargo, exposé, report, chats, correos) y la transcripción de `06_Entrevistas/`.
- **Fija los hechos** no controvertidos y controvertidos contrastando demanda y contestación, anclando
  cada hecho a su fuente.
- Redacta la **minuta** (guion de sala) y la **solicitud de prueba** (escrito procesal).
- Guarda los outputs (en `05_Procedimiento/` y registra en el intake si es modo FeesDefender; en la
  carpeta que indique el letrado si es modo civil genérico).

NO hace:

- No redacta la **demanda** ni la **contestación** (eso es `escritos-judiciales`).
- No prepara el **acto del juicio** ni los interrogatorios de testigos (eso es
  `preparacion-juicio-oral`; esta skill solo propone la testifical en la solicitud de prueba).
- No **valora la viabilidad** del caso (eso es la fase de viabilidad).
- No lee nunca `90_Notas personales/`.

## Reglas de oro (innegociables)

1. **Source-locked.** Cada hecho, cita literal, importe, fecha y referencia documental se ancla a su
   fuente verificable del expediente. Sin inferencias: si la fuente no lo dice, no se afirma. Está
   prohibido afirmar parentescos, relaciones, intenciones o conocimiento que el documento no sostenga.
   Encadena con `verificacion-anclada-fuente`.
2. **Jurisprudencia verificada en CENDOJ antes de citarla.** Las referencias de bases privadas
   (Lefebvre El Derecho, vLex, Iberley, Sepin) se contrastan contra el texto oficial del CGPJ antes de
   usarlas o distinguirlas en sala (encadena con `cendoj-descarga`). Nunca se inventa jurisprudencia.
3. **No confundir hecho con cuestión jurídica.** La fijación del art. 428 recoge *hechos*. Las
   cuestiones de calificación (validez de cláusula, devengo objetivo, base de cálculo de derecho) se
   marcan como *cuestión jurídica, no fáctica* y no se enrutan a prueba.
4. **Terminología según el contexto.** Por defecto (civil genérico), **neutra**: usa los nombres
   reales de las partes o, en su defecto, actor/demandado. **Solo en modo E&V inmobiliario** aplica
   **propietario** (ofrece el bien; nunca "vendedor") / **buscador** (busca; nunca "comprador" ni
   "arrendatario"). La cita literal conserva el término original entre comillas. El **NIG no se usa**.
5. **Coherencia con lo ya presentado.** Antes de alegar algo en la AP, comprobar que no contradice una
   admisión de nuestra propia demanda/contestación. Si la hay, reformular para no chocar (ver el patrón
   "predisposición vs. negociación de cláusulas concretas" en [references/flujo.md](references/flujo.md)).
6. **Perspectiva primero.** Determina si somos **actora** o **demandada** antes de redactar: invierte
   la carga argumental, el orden de los cuadros y el sentido de la prueba. Ver
   [references/actora_defensiva.md](references/actora_defensiva.md).

## Flujo resumido

0. **Reconocimiento y contexto.** Determina el **modo**: si hay `00_Input/_caso.md` (caso E&V de
   FeesDefender) → modo FeesDefender; si no → modo civil genérico (pregunta dónde están los escritos y
   dónde guardar). Lee partes, perspectiva, órgano y cuantía.
1. **Lectura procesal y fijación de hechos** (source-locked). Demanda + contestación → tabla de no
   controvertidos y tabla de controvertidos con posición de cada parte y prueba. Lee la entrevista de
   `06_Entrevistas/` para identificar la prueba testifical y los hechos a acreditar.
2. **Confirmación de hechos con el letrado.** Presenta los dos cuadros y la causa de pedir. Señala
   flancos (admisiones internas peligrosas, lagunas documentales). Espera su visto bueno.
3. **Propuesta de prueba (por chat).** Presenta la prueba propuesta (documental, más documental,
   testifical, interrogatorio, oficios) en una tabla —medio · qué acredita · fuente de citación ·
   riesgo— y **espera la confirmación o ajustes del letrado**. La generación de la minuta y la
   solicitud queda condicionada a este visto bueno.
4. **Señalamiento.** Fecha y sala de la AP: en modo FeesDefender, de la providencia/DIOR del
   **expediente Sudespacho** sincronizado en `00_Input/`; en modo genérico, de la providencia que
   aporte el letrado. Si no consta, pregunta; no lo inventes.
5. **Genera la minuta** con `scripts/gen_minuta.py` (ver formato).
6. **Genera la solicitud de prueba** con `scripts/gen_solicitud.py` (escrito procesal).
7. **Guarda y (solo modo FeesDefender) registra** con `scripts/registrar_outputs.py`; en modo genérico,
   guarda en la carpeta indicada por el letrado. **Valida** (source-locked, cierre).

El detalle de cada fase, con el patrón de fijación y los gotchas, está en
[references/flujo.md](references/flujo.md).

## Generación de la minuta

Usa `scripts/gen_minuta.py`, que recibe un JSON de datos y produce el `.docx` con el formato exacto de
la plantilla del despacho (Arial 12, interlineado 1,25, márgenes A4 2,5/2,5/3,5/2 con margen izquierdo
amplio para anotar a mano, cabeceras de bloque sombreadas con borde inferior, `[ PARA LEER EN SALA ]`
en 9 pt, subpuntos numerados jerárquicos, y las dos tablas de hechos con cabecera gris y filas
alternas). La estructura de bloques (415→429) y el esquema del JSON están en
[references/formato_minuta.md](references/formato_minuta.md). Ejemplos: `assets/ejemplo_minuta.json`
(modo E&V) y `assets/ejemplo_minuta_generico.json` (modo civil genérico, terminología neutra).

## Generación de la solicitud de prueba

Es un **escrito procesal**. Para que calque el modelo del despacho, **usa el generador bundleado**
`scripts/gen_solicitud.py` (recibe un JSON y produce el `.docx` con el formato exacto de la plantilla:
Times New Roman 12, márgenes 2,5, tabla de referencia en cabecera, comparecencia del procurador con
`DIGO`, lista numerada con `DOCUMENTAL` / `MÁS DOCUMENTAL` / `DECLARACIÓN en calidad de TESTIGO` con
DNI en negrita y petición de `CITACIÓN JUDICIAL`, `SUPLICO`, "Es justicia…" y firma
letrado/procurador, con número de página centrado). NO improvises el escrito ni lo reconstruyas a mano:
rellena el JSON y ejecuta el script. El formato sigue las convenciones de `escritos-judiciales`
(consúltala solo si necesitas una variante no cubierta). Esquema del JSON, ejemplo y estructura en
[references/solicitud_prueba.md](references/solicitud_prueba.md); ejemplo completo en
`assets/ejemplo_solicitud.json`.

## Mejora continua

Esta skill se auto-instrumenta para mejorar con el uso (mismo patrón que `preparacion-juicio-oral`):

- **Checklist previo** (`templates/checklist_pre_ap.md`): objetivo del acto, perspectiva, frentes
  prioritarios, flancos, prueba clave. Se rellena al iniciar y se vuelca a `logs/<ref>_pre.jsonl`.
- **Registro de uso** (helper canónico `scripts/registrar_uso.py`): cada generación de `.docx`
  registra `ref`, acción, archivos, nº de
  hechos no controvertidos/controvertidos y testigos. Escribe en el **store central**
  `data/_skill_logs/preparacion-audiencia-previa/uso.jsonl` (no en el bundle). Es *best-effort*: si
  el log falla, avisa por stderr pero **nunca** rompe la generación del documento.
- **Revisión post-AP** (`templates/checklist_post_ap.md`): qué fijó realmente el juez (frente a
  nuestra minuta), qué prueba admitió/inadmitió, qué pregunta/objeción no estaba prevista, valoración
  del acto → `logs/<ref>_post.jsonl`. Programar a `fecha_AP + 3 días`.
- **Cierre del bucle.** Cuando haya 5+ ejecuciones reales con su `post`, revisar `logs/` para detectar
  patrones (alegaciones que el juez rechaza siempre, prueba que se inadmite, flancos recurrentes) y
  promover los ajustes al cuerpo de la skill. La fijación literal del juez (transcripción CGPJ del acto)
  **prevalece** sobre la minuta interna: si difieren, manda la transcripción y se anota la divergencia.

## Encadenamiento con otras skills

- **`verificacion-anclada-fuente`** — convivencia obligatoria en la fijación de hechos y la validación.
- **`escritos-judiciales`** — genera la solicitud de prueba como escrito procesal.
- **`cendoj-descarga`** — verifica/descarga la jurisprudencia citada antes del acto.
- **`engel-volkers`** (skill de cliente) — registro y matices E&V cuando aplique.
- **`preparacion-litigio-civil`** / **`viabilidad-prerelleno`** — predecesoras (abren el expediente y
  preparan la viabilidad/demanda).
- **`preparacion-juicio-oral`** — sucesora (tras la AP, reutiliza estos cuadros para el juicio).

## Gotchas (leer antes de generar)

- **El señalamiento de la AP vive en el CRM Sudespacho**, sincronizado en `00_Input/`. No lo inventes:
  extráelo de la providencia/DIOR; si no consta, pregunta.
- **Causalidad en casos de "vuelta": cuestión jurídica, no fáctica.** Si la cláusula configura un
  devengo objetivo, no enrutes la causalidad a prueba; basta acreditar visita o información a través de
  E&V (hecho), y la relación causa-efecto se resuelve por interpretación literal del contrato.
- **No contradigas admisiones propias.** Revisa la contestación/escritos ya presentados antes de alegar
  en sentido contrario (regla de oro 5).
- **`05_Procedimiento` y el manifiesto son convención nueva.** FeesDefender (core) aún no la lee; ver
  el aviso en [references/manifiesto_y_registro.md](references/manifiesto_y_registro.md).
- **Fichero `.docx` abierto = Word lo bloquea.** Si el destino está abierto, guarda con sufijo `_v2` y
  avisa (no falles en silencio).
- **No leas `90_Notas personales/`** nunca; no leas `06_Entrevistas/` si la entrevista aún no se ha
  celebrado.

## Changelog

- **1.0** — Registro de outputs migrado al helper canónico
  `scripts/registrar_outputs.py` (campo `destino`); telemetría migrada al helper
  común `scripts/registrar_uso.py` (store central `data/_skill_logs/`).
