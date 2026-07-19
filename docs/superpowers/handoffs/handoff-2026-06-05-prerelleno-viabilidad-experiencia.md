---
tipo: handoff
estado: historico
creado: 2026-06-05
origen: sesión Cowork — cristalización de conocimiento de dominio para el pre-relleno de viabilidad
destino: chat de construcción de la skill viabilidad-prerelleno
consumido_por: "skill viabilidad-prerelleno (.claude/skills/viabilidad-prerelleno/); PLAN_PRERELLENO_LLM_VIABILIDAD.md"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# Experiencia cristalizada — Skill de pre-relleno documental del informe de viabilidad (FeesDefender)

> **Para qué es este documento.** Paquete de conocimiento para construir, en otro chat, una skill que lea los documentos **no anonimizados** de un expediente, extraiga los datos básicos y **pre-rellene el informe de viabilidad** ANTES de la entrevista con los consultores de E&V. Pega esto entero en el chat de construcción de la skill: contiene el encuadre, las reglas innegociables, la estructura del informe, las reglas de derivación de los 14 hitos, los tipos de caso, la taxonomía documental y el mapa cuestionario→fuente.

---

## 0. Encuadre (qué hace y qué NO hace la skill)

- **Eje:** pre-relleno **documental**, paso **previo** a la entrevista. NO sustituye a la entrevista, la **prepara**. En FeesDefender la prueba primaria es **testifical** (los consultores); el documento **corrobora**. Por eso todo lo que solo puede afirmar un testigo se deja en `pendiente` y se enruta a la hoja de huecos.
- **Entrada (decisión cerrada):** **todo** lo que haya en `00_Input/` del expediente (`01_Drive EV`, `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`). NO se lee `06_Entrevistas` (aún no hay entrevista) ni nunca `90_Notas personales`.
- **Salida (decisión cerrada):** **un único** `Informe viabilidad LLM - <case_id>.xlsx` en `02_Analisis/`. Es un archivo **paralelo**: NUNCA sobrescribe el informe humano. Incorpora dentro la **hoja de huecos** para la entrevista (decisión cerrada: sí se marcan).
- Trabaja sobre documentos **no anonimizados** (necesita nombres, fechas e importes reales). El responsable del tratamiento es el despacho; el rastro fuente+cita que genera la skill vale además como traza RGPD.

---

## 1. Reglas de oro (innegociables)

1. **Nunca inventar.** Cada dato extraído se ancla a su fuente: `[doc: <fichero>]` + **cita literal** + **confianza** (alta/media/baja). Si el dato no consta en ningún documento → `pendiente`/`null`, jamás se rellena por inferencia. (Disciplina de la skill `verificacion-anclada-fuente` y regla de oro del proyecto.)
2. **Las 3 dimensiones de VIABILIDAD (JURÍDICA / FINANZAS / GLOBAL) se dejan SIEMPRE en `pendiente`.** Son criterio jurídico del abogado; jamás se autocalculan ni las propone la skill.
3. **El TOTAL de DATOS OPERACIÓN es métrica auxiliar, no veredicto.** No hay umbrales fijos; lo pondera el abogado.
4. **Política conservadora de scoring:** una firma **sin cotejar** (`no_cotejado`) puntúa **0**, no 1 (en juicio una firma sin cotejar es debilidad probatoria). Los `N/A` no suman ni restan (la fórmula los ignora).
5. **Terminología:** **propietario** (quien ofrece el bien; nunca "vendedor") / **buscador** (quien busca; nunca "comprador" ni "arrendatario").
6. **El NIG no se usa** en ningún campo, payload ni plantilla.
7. **No leer `90_Notas personales/`** (zona reservada del abogado).

---

## 2. Estructura del informe de viabilidad

Bloques, en orden (fuente: `data/_plantillas/informe_viabilidad.yaml`):

1. **CABECERA** — `REF` (patrón `<equipo> - <direccion> (<id_go>)`) y `FECHA`.
2. **EQUIPO COMERCIAL** — DIRECTOR CAPTADOR, ASESOR CAPTADOR, DIRECTOR BUSCADOR, ASESOR BUSCADOR.
3. **CONTEXTO** — OBSERVACIONES y MOTIVOS DE IMPAGO (este último solo en BAD_DEBT y NEGATIVA_*; vacío en VUELTA / RESP. PROFESIONAL).
4. **IMPORTES** — ver §4.
5. **VIABILIDAD** — JURÍDICA / FINANZAS / GLOBAL, enum {verde, amarillo, rojo, pendiente}. **Pre-relleno = siempre `pendiente`** (regla de oro 2). Formato condicional: verde C6EFCE/006100, amarillo FFEB9C/9C5700, rojo FFC7CE/9C0006, pendiente D9D9D9/595959.
6. **DATOS OPERACIÓN** — 14 hitos, columnas `[hito, score, fecha, observaciones]` + fila TOTAL. Ver §3.
7. **ACTIVIDADES** — EXPOSÉS PROPIEDAD, VISITAS PROPIEDAD, EXPOSÉS BUSCADOR, VISITAS BUSCADOR (métricas numéricas).

---

## 3. Los 14 hitos — regla de derivación documental

Cada hito puntúa derivándose de respuestas del cuestionario que, en el pre-relleno, se obtienen del **documento** correspondiente. Si el documento no está, el hito queda `pendiente` (no 0) y se anota como hueco.

| # | Hito | Score | Regla (pre-relleno documental) | Fecha desde |
|---|------|-------|--------------------------------|-------------|
| 1 | **CUANTÍA** | categórico 1/2/3 | `≤10.000€`→1; `10.001–20.000€`→2; `>20.000€`→3. Base = TOTAL DEUDA. | — |
| 2 | **ENCARGO** | bool compuesto | score=1 **solo si todas**: encargo firmado (cap_08) + original (cap_13) + completo todas las páginas (cap_08b) + firmas de todos los clientes (cap_08c) + cotejo firmas vs DNI = sí (cap_08d). Si cotejo `no_cotejado` → **0**. | doc encargo |
| 3 | **IDENTIFICACIÓN PROPIETARIO** | bool | 1 si hay copia de DNI de todos los propietarios (cap_17). | — |
| 4 | **TITULARIDAD** | bool | 1 si existe nota simple de captación (cap_18a). Obs. automática si los titulares NO coinciden con los firmantes del encargo (cap_18c=no). | nota simple (cap_18b) |
| 5 | **HOJA DE VISITA** | bool con N/A | N/A si no aplica al caso (vis_00=no); 1 si hoja firmada (vis_05) **y** tenemos original/copia (vis_06∈{original,copia}); si no, 0. | doc hoja de visita |
| 6 | **OFERTA** | bool | 1 si tenemos original firmado de la oferta (ofb_05). | doc oferta |
| 7 | **IDENTIFICACIÓN BUSCADOR** | bool | 1 si hay copia de DNI de todos los buscadores (vis_09). Obs. automática si firmas oferta vs DNI no coinciden (vis_10=no) o pendientes de cotejo. | — |
| 8 | **ARRAS / ARRENDAMIENTO** | bool con N/A | 1 si arras/contrato `firmadas` (arr_00); 0 si `intentadas_no_firmadas`; N/A si `no_aplica`. | arr_00_fecha |
| 9 | **RECONOCIMIENTO HONORARIOS — ARRAS** | bool con N/A | 1 si existe documento de reconocimiento firmado en arras (arr_13); 0 no; N/A no aplica. | arr_13_fecha |
| 10 | **ESCRITURA** | bool con N/A | 1 si se otorgó escritura (esc_01=si); 0 no; N/A no aplica. Obs. automática: si esc_01=si y esc_02=no (sin nota simple post) → "confirmar otorgamiento con nota simple actualizada". | esc_01_fecha |
| 11 | **RECONOCIMIENTO HONORARIOS — ESCRITURA** | bool con N/A | 1 si reconocimiento firmado en escritura (esc_03); 0 no; N/A no aplica. | esc_03_fecha |
| 12 | **RECLAMACIÓN FINANZAS** | bool con N/A | 1 si hubo reclamación previa de Finanzas (rec_01); 0 no; N/A no aplica. | rec_01_fecha |
| 13 | **RECLAMACIÓN JURÍDICO** | bool | 1 si se envió burofax jurídico (rec_02) — interrumpe prescripción. | rec_02_fecha |
| 14 | **RESPUESTA A LA RECLAMACIÓN** | bool con N/A | 1 si hubo respuesta (rec_03=si); 0 no; N/A si `en_plazo`. | rec_03_fecha |
| (+) | **OFERTA VINCULANTE CONFIDENCIAL** | bool con N/A | 1 si hubo oferta de transacción del deudor (rec_04); 0 no; N/A no aplica. | rec_04_fecha |

**TOTAL** = `SUM(scores no-N/A)`. SUM ignora celdas de texto (N/A), así que N/A no infla ni reduce. Interpretación: nº de checks documentales superados; métrica auxiliar.

---

## 4. Importes y fórmulas

- `PRECIO` — desde encargo / oferta / escritura (el de la operación efectiva).
- `% HONORARIOS` — **default 5** si no consta otro en el encargo.
- `TOTAL HONORARIOS (IVA 21%)` = `PRECIO/100 * %HONORARIOS * 1,21` (**compraventa**). En **arrendamiento**, ajustar a la fórmula del encargo (típicamente una mensualidad o % sobre renta anual).
- `PAGOS PARCIALES` — default 0.
- `TOTAL DEUDA` = `TOTAL HONORARIOS − PAGOS PARCIALES`.
- `PROPUESTA DE PAGO` — si consta.
- `DIFERENCIA` = `TOTAL DEUDA − PROPUESTA DE PAGO`.

---

## 5. Tipos de caso (condicionan el informe)

**Posición actora (E&V reclama)** — usan el cuestionario completo:
`NEGATIVA_OFERTA`, `NEGATIVA_ARRAS`, `NEGATIVA_ESCRITURA`, `NEGATIVA_CONTRATO_ARRENDAMIENTO`, `VUELTA`, `INCUMPLIMIENTO_EXCLUSIVA`, `BAD_DEBT` (impago de factura).

**Posición defensiva (E&V demandada):** `RESPONSABILIDAD_PROFESIONAL`, `DEVOLUCION_RESERVA`, `LAU_20` (art. 20.1 LAU), `DEVOLUCION_HONORARIOS` (cajón general no-LAU).

**Comodín:** `OTROS` (asuntos E&V no de honorarios, sin posición fija).

Implicaciones para el pre-relleno:
- **MOTIVOS DE IMPAGO** solo en BAD_DEBT y NEGATIVA_*; vacío en VUELTA y defensivos.
- **VUELTA** activa la sección 8 (ruptura del nexo causal) — casi toda testifical → huecos.
- **Arrendamiento** (NEGATIVA_CONTRATO_ARRENDAMIENTO / LAU_20): hito 8 = contrato de arrendamiento; ajustar fórmula de honorarios; hitos de escritura suelen ser N/A.
- El tipo se lee del nombre de la carpeta del caso / informe existente / tag CRM. La sección del cuestionario solo se rellena si `aplica_a_tipos` incluye el tipo del caso.

---

## 6. Taxonomía documental y dónde vive (00_Input)

Estructura de `00_Input/`: `01_Drive EV`, `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`.
- `02_Whatsapp/` y `03_Email/` se subdividen: `00_Consultor propietario`, `01_Consultor buscador`, `02_Grupo operacion`/`02_Direccion EV`, `03_Otros`.

Tipos de documento que alimentan el pre-relleno (etiqueta → qué extraer):
- **encargo** → existencia, integridad (páginas/cláusulas), firmantes, % honorarios, precio, modo de firma, fecha, original sí/no.
- **nota_simple** → titularidad, titulares, fecha; nota post-operación confirma escritura.
- **dni** → identificación de propietarios y buscadores; base de cotejo de firmas.
- **hoja_visita** → vinculación buscador-agencia, firma, original/copia, fecha, nº visitas.
- **oferta** → existencia/firma del buscador, precio, reserva/señal, original sí/no, fecha.
- **arras** (o contrato de arrendamiento) → estado (firmadas/intentadas/no aplica), fecha, reconocimiento de honorarios.
- **escritura** → otorgamiento sí/no, fecha, reconocimiento de honorarios.
- **email / whatsapp** → traslado de ofertas, aceptaciones, negativas, modificaciones, coordinación interna (mayormente corroboran; muchas respuestas siguen siendo testificales).
- **crm** → fechas y existencia de reclamaciones (Finanzas/jurídica), respuestas, oferta vinculante.

---

## 7. Mapa cuestionario → fuente (qué se pre-rellena de documento vs qué es testifical)

El cuestionario tiene **90 preguntas en 11 secciones**. De ellas, **50 no incluyen `entrevista`** en su `fuente_probable` → candidatas a pre-relleno documental. El resto (o las que el documento no aclare) → **hoja de huecos**.

**Pre-rellenables de documento (núcleo, las que mueven los 14 hitos):**
`cap_08, cap_08b, cap_08c, cap_08d, cap_10, cap_11, cap_13` (encargo) · `cap_17, vis_09, vis_10` (DNI/cotejo) · `cap_18a, cap_18b, cap_18c` (nota simple) · `vis_05, vis_06` (hoja de visita) · `ofb_05, ofb_02, ofb_06` (oferta) · `arr_00, arr_00_fecha, arr_13, arr_13_fecha` (arras) · `esc_01, esc_01_fecha, esc_02, esc_03, esc_03_fecha` (escritura) · `rec_01..rec_04` + fechas (CRM/email).

**Testificales puros (van SIEMPRE a huecos — el documento no los acredita):**
`cap_01, cap_03, cap_04, cap_05, cap_06, cap_12, cap_14, cap_15, cap_16` (captación: cómo, con quién, circunstancias) · `vis_00, vis_01, vis_03, vis_07, vis_08` (visitas: relevancia, origen del lead, presentes) · toda la sección **8 (vueltas)** `vue_01..vue_05` · sección **9 (team leader)** `tl_01` · y los matices de negativa/aceptación verbal en arras (`arr_11, arr_12`) y comunicación (`cap_p_03`, etc.).

Cada pregunta tiene un `objetivo_probatorio` (por qué importa). En la hoja de huecos, **conserva el objetivo_probatorio** junto a la pregunta para que el letrado sepa qué prueba persigue.

---

## 8. Hoja de huecos para la entrevista (dentro del .xlsx)

Genera una pestaña con las preguntas no resueltas por documento, agrupadas por sección del cuestionario, con: `ID`, `pregunta`, `objetivo_probatorio`, `hito que respalda` (si lo hay) y `por qué falta` (no hay documento / documento no concluyente). Esto es el guion mínimo que el abogado lleva a la entrevista. Solo se incluyen las secciones cuyo `aplica_a_tipos` cubre el tipo del caso.

---

## 9. Pistas de implementación (opcionales)

- Conviene un **script** que renderice el `.xlsx` a partir de un JSON de datos extraídos (cabecera, equipo, importes, 14 hitos con score+fecha+observaciones, actividades, huecos), aplicando fórmulas Excel y el formato condicional de viabilidad. Así cada ejecución no reinventa el render.
- Las observaciones de cada hito son el lugar natural para el rastro `[doc: fichero] "cita" (confianza)`.
- Encadena conceptualmente con `verificacion-anclada-fuente` (disciplina anti-alucinación) y deja el resultado listo para que la fase de entrevista lo complete.

**Fuentes en el repo (Claude Code):** `data/_plantillas/informe_viabilidad.yaml`, `data/_plantillas/cuestionario_viabilidad.yaml`, `core/config.py` (TIPOS_CASO, CASO_SUBDIRS, INPUT_SUBDIRS, terminología). `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md` (re-encuadre 2026-05-30).
