---
name: viabilidad-prerelleno
description: >-
  Pre-rellena el Informe de Viabilidad de Engel & Völkers (proyecto FeesDefender) para
  reclamaciones de honorarios de mediación impagados, ANTES de la entrevista con los
  consultores. Lee la documental no anonimizada de 00_Input de un expediente, extrae datos
  anclados a fuente, deriva los 14 hitos, marca lo testifical como pendiente (guion de
  entrevista) y vuelca banderas a AVISOS LLM, generando un .xlsx-bitácora paralelo de 4 hojas.
  Úsala SIEMPRE que se abra o prepare un expediente de reclamación de honorarios de E&V, cuando
  el usuario diga "pre-rellenar", "preparar la viabilidad", "informe de viabilidad", "cargar el
  expediente", "preparar la entrevista" de un caso de honorarios, o cuando mencione 00_Input,
  hitos, semáforo de viabilidad o el cuestionario de evidencia de un caso E&V. NO valora la
  viabilidad ni redacta el recuadro ejecutivo (eso es la Skill B `informe-viabilidad-ev`).
---

# Pre-relleno documental del Informe de Viabilidad (FeesDefender / E&V)

## Qué hace y qué NO hace

Esta skill es la **Skill A** del proyecto FeesDefender. Prepara la entrevista; **no la sustituye**. En estos casos la prueba primaria es **testifical** (los consultores de E&V); el documento **corrobora**. Por eso todo lo que solo puede afirmar un testigo se deja en `pendiente` y se enruta al guion de entrevista.

Hace, en esta fase (**1ª pasada, documental**):

- Lee **toda** la documental no anonimizada de `00_Input/` del expediente.
- Detecta el tipo de caso y rellena la hoja `PREGUNTAS` con lo acreditable por documento, **anclado a fuente**.
- Deriva los **14 hitos** de `DATOS OPERACIÓN` con scoring conservador.
- Marca lo testifical como `¿PENDIENTE ENTREVISTA?=sí` (eso es el guion de entrevista).
- Vuelca sus banderas de trabajo a `AVISOS LLM` y añade la primera entrada a `BITACORA`.
- Produce **un .xlsx paralelo** que NUNCA sobrescribe el informe humano.

**NO hace** (es de la Skill B `informe-viabilidad-ev` o del abogado):

- No valora la **VIABILIDAD** (JURÍDICO/FINANZAS): se dejan SIEMPRE en blanco.
- No escribe el **recuadro ejecutivo** para el CFO (`B48`).
- No rellena las **NOTAS LETRADO**.
- No lee la fuente `entrevista` (lotes ni cajón legacy `06_Entrevistas/`) en esta 1ª pasada (aún no hay entrevista), ni **nunca** `90_Notas personales/`.

> La **2ª pasada** (leer la transcripción de la entrevista y cerrar huecos testificales) está prevista pero **no se construye todavía** en esta versión.

## Reglas de oro (innegociables)

1. **Nunca inventar.** Cada dato se ancla a su fuente: `[doc: <fichero>]` + cita literal + confianza (`alta/media/baja`). Si el dato no consta en ningún documento → `pendiente`/vacío, jamás por inferencia. Encadena con la disciplina de `verificacion-anclada-fuente`.
2. **VIABILIDAD siempre en blanco** en el pre-relleno. La decide el abogado.
3. **TOTAL de hitos = métrica auxiliar, no veredicto.** Sin umbrales fijos.
4. **Scoring conservador**: una firma `no_cotejado` puntúa **0**, no 1. Los `N/A` no suman. Sin documento → `pendiente` (vacío), no `0` — **salvo en los hitos de existencia documental** (ver matiz):
   - **Hitos de existencia documental** — la pregunta ES "¿existe este documento concreto?" (`ENCARGO`, `IDENT_PROPIETARIO`, `TITULARIDAD`, `HOJA_VISITA`, `OFERTA`, `IDENT_BUSCADOR`, `ARRAS/ARRENDAMIENTO` en su vertiente firmadas, `RECON_HON_ARRAS`, `RECON_HON_ESCRITURA`, `ESCRITURA` — marcados en `hitos_derivacion.md`). Si tras revisar **todo** `00_Input` (crudo o MD, regla 8) no aparece ese documento **ni ninguna referencia a su existencia** (email, CRM, WhatsApp) → **`0`**, no pendiente. La ausencia no es una laguna aquí: es la respuesta — el hito pregunta literalmente por algo que, de existir, estaría en el expediente.
   - **El resto** (hitos/preguntas que dependen de un hecho no necesariamente documentado: comunicaciones verbales, gestiones en curso como el envío de un burofax por un canal aún no subido, decisiones internas) — aquí la ausencia de documento no prueba que el hecho no ocurrió → sigue aplicando `pendiente` (vacío).
5. **Terminología**: **propietario** (ofrece el bien; nunca "vendedor") / **buscador** (busca; nunca "comprador" ni "arrendatario"). Aplica **también al texto libre que tú redactas** (MOTIVOS DE IMPAGO, AVISOS, resúmenes): si un documento dice "comprador/vendedor/arrendatario", **normalízalo** a buscador/propietario al transcribir la postura. La cita literal en `CITA/FUENTE` (col J) puede conservar el término original entre comillas, pero el campo que redactas no.
6. **No leer** la fuente `entrevista` (lotes ni cajón legacy `06_Entrevistas/`) en esta 1ª pasada, ni nunca `90_Notas personales/`. El **NIG no se usa**.
7. Trabaja sobre documentos **no anonimizados** (necesita nombres, fechas e importes reales). El rastro fuente+cita vale además como traza RGPD.
8. **Vía de lectura por documento (rápida pero rigurosa):**
   1. Si existe `01_Procesado/02_Sala de máquina/03_MD/<slug>.md` para ese fichero **y** su estado en `_cobertura.md` es `ok` → léelo desde ahí. Ya está extraído y su calidad ya fue verificada (densidad de texto, sin gibberish); releer el binario crudo sería releer lo mismo por una vía más lenta.
   2. Si el estado es `low`/`empty`, o no existe MD para ese documento (sala de máquina no se ha corrido, o el documento llegó después) → lee el **crudo** de `00_Input/` directamente. Nunca te fíes de una extracción ya marcada como dudosa.
   3. Para cualquier dato que alimente un **hito** o un **importe** (fechas de encargo/oferta/escritura, precio, cuantías, cotejo de firmas) — los campos de más peso del informe — anota en la cita **de qué vía vino**: `[doc: fichero, vía MD]` frente a `[doc: fichero, crudo]`. Así el rastro queda auditable sin perder velocidad.
   4. Esto **no** exige correr `organizar-sala-maquina` antes — esta skill sigue siendo independiente; solo aprovecha el MD *si ya existe*.

## Flujo de trabajo

### 1. Localiza el expediente y lee `00_Input/`
`00_Input/` tiene dos formas de canal: **lotes de entrega** `<AAAA-MM-DD>_<fuente>_<NN>/`
(fuentes `whatsapp`, `email`, `manual`, `entrevista`; cada lote lleva `_manifiesto.yaml`
con `tipo_contenido` por ítem) y **cajones espejo** fijos `01_Drive EV/` y `05_CRM/` (sync
incremental). Los casos antiguos no migrados conservan los cajones `02_Whatsapp/`,
`03_Email/`, `04_Manual/`: lee AMBAS formas. Whatsapp/Email se subdividen por consultor
(`00_Consultor propietario`, `01_Consultor buscador`, `02_Grupo/Dirección`, `03_Otros`) tanto
dentro de un lote como del cajón legacy. Lee todo lo que haya. No leas la fuente
`entrevista` (lotes `<AAAA-MM-DD>_entrevista_<NN>/` o cajón legacy `06_Entrevistas/`) ni
`90_Notas personales/`. Para la vía de lectura de cada documento (MD vs crudo), aplica la
regla de oro 8.

### 2. Determina el tipo de caso
Del nombre de la carpeta / informe existente / tag CRM. Las claves canónicas son las de `core/config.py` (`TIPOS_CASO_ACTORA` / `TIPOS_CASO_DEFENSIVA`). Actores: `BAD_DEBT`, `NEGATIVA_OFERTA`, `NEGATIVA_ARRAS`, `NEGATIVA_ESCRITURA`, `NEGATIVA_CONTRATO_ARRENDAMIENTO`, `VUELTA`, `INCUMPLIMIENTO_EXCLUSIVA`. Defensivos: `RESPONSABILIDAD_PROFESIONAL`, `DEVOLUCION_RESERVA`, `LAU_20`, `DEVOLUCION_HONORARIOS`. Comodín: `OTROS`.

> **Tipos que NO reciben Informe de Viabilidad (parar antes de generarlo).** La lista canónica de tipos que SÍ lo reciben es `INFORME_VIABILIDAD_TIPOS` en `core/config.py`: las `NEGATIVA_*`, `VUELTA`, `INCUMPLIMIENTO_EXCLUSIVA` y `RESPONSABILIDAD_PROFESIONAL`. Quedan **fuera** `BAD_DEBT`, `LAU_20`, `DEVOLUCION_RESERVA` y `DEVOLUCION_HONORARIOS`. El caso paradigmático es `BAD_DEBT`: impago de factura limpio, operación cerrada sin incidencias y sin controversia sobre la prestación (el deudor suele reconocer la deuda y alegar tesorería); el derecho al cobro ya está documentado y procede la vía de reclamación de cantidad, no un análisis de viabilidad probatoria. Por eso, si el tipo NO está en `INFORME_VIABILIDAD_TIPOS`, **no fabriques el .xlsx mecánicamente**: avisa al usuario de que el caso no requiere informe de viabilidad y pregunta si aun así quiere generarlo (p. ej. para dejar constancia o porque hay controversia latente). Solo entonces continúa.

El tipo condiciona:
- **MOTIVOS DE IMPAGO** (`H12`): tiene sentido en `BAD_DEBT` y `NEGATIVA_*`. **Regla de relleno (cerrada): vacío por defecto; se rellena SOLO si hay postura del deudor documentada y anclada a fuente** — y esto aplica también a `VUELTA` (reconcilia el handoff con el caso real Tibidabo). Frase telegráfica EN MAYÚSCULAS y con terminología propietario/buscador (normaliza aunque el documento diga "comprador/vendedor"). En defensivos, vacío.
- **VUELTA** activa la sección 8 (ruptura del nexo causal), casi toda testifical → huecos.
- **Arrendamiento** (`NEGATIVA_CONTRATO_ARRENDAMIENTO`/`LAU_20`): el hito 8 es el contrato de arrendamiento; **ajusta la fórmula de honorarios** del encargo (típicamente una mensualidad o % sobre renta anual, no `H13/100*E14*1.21`); los hitos de escritura suelen ser `N/A`.

### 3. Pre-rellena `PREGUNTAS` desde los documentos
Lee `references/cuestionario_viabilidad.yaml` (vista generada desde el canónico del repo: 11 secciones, 88 preguntas — 58 documentales / 30 testificales — con su `clase_fuente`, `hito` y `fuente_probable`). Para cada pregunta:

- Si un documento la responde → escribe `RESPUESTA` (col I), `CITA/FUENTE` (col J, rastro `[doc: fichero] "cita"`), `CONFIANZA` (col K) y `¿PENDIENTE?` (col M) = `no`.
- Si ningún documento la resuelve (o es `clase_fuente: testifical`) → deja respuesta vacía y `¿PENDIENTE?` = `sí`. Esa fila es guion de entrevista.
- `clase_fuente` es solo un **default**: una pregunta "documental" cuyo documento no aparece también pasa a `pendiente`. Nunca rellenes por inferencia.
- **No toques** las columnas fijas (SECCIÓN, ID, PREGUNTA, OBJETIVO, TIPO, FUENTE, HITO) ni NOTAS LETRADO.

### 4. Deriva los 14 hitos
Aplica `references/hitos_derivacion.md` (tabla completa de reglas, celdas e importes). Resumen: cada hito sale de IDs concretos del cuestionario; scoring conservador; sin documento → `pendiente` (vacío). El hito antiguo `RECLAMACIÓN FINANZAS` **ya no existe** (son 14, no 15).

### 5. Importes y actividades
Importes en `references/hitos_derivacion.md` (% honorarios default 5; en arrendamiento, fórmula del encargo). Actividades en valores numéricos.

### 6. Vuelca banderas a `AVISOS LLM`
Cuantía a conciliar, riesgos (despatrimonialización, sociedad pantalla), pruebas débiles (firma sin cotejar, original no localizado), documentos faltantes, y el recuento de preguntas `¿PENDIENTE?=sí`. Estado inicial `abierto`; `¿SUBE AL RECUADRO CFO?` = `no` por defecto (lo decide el abogado); puedes sugerir `sí` solo en banderas de severidad **alta** de cuantía/riesgo.

### 7. Genera el .xlsx con el script
Reúne lo extraído en un JSON (ver `references/modelo_xlsx.md` para el mapa exacto de celdas) y ejecuta:

```bash
python scripts/render_informe.py datos_<case_id>.json --salida "<expediente>/02_Analisis/Informe viabilidad LLM - <case_id>.xlsx"
```

El script **parte de `assets/plantilla_informe_viabilidad.xlsx`** (formato, fórmulas, semáforo, validaciones y protección ya incorporados), solo escribe valores, deja VIABILIDAD y el recuadro en blanco, y **se niega a sobrescribir** un fichero existente. Construir el formato a mano rompería el semáforo y la protección; por eso siempre se parte de la plantilla.

## Estructura del JSON de datos

```json
{
  "case_id": "W-0RURIT",
  "fecha": "05/06/2026",
  "ref": "BaXX - Avenida del Parque 7 (W-0RURIT) - Vuelta",
  "equipo": {"director_captador": "Soler, Marta", "asesor_captador": "Rovira, Eva",
             "director_buscador": "Soler, Marta", "asesor_buscador": "Prat, Luis"},
  "tipo_caso": "VUELTA",
  "observaciones": "VUELTA",
  "motivos_impago": "",
  "importes": {"precio": 9000000, "pct_honorarios": 3, "pagos_parciales": 0, "propuesta_pago": 0},
  "hitos": {
    "CUANTIA": {"score": 3, "fecha": null},
    "ENCARGO": {"score": 1, "fecha": "12/03/2024"},
    "IDENT_PROPIETARIO": {"score": 0},
    "HOJA_VISITA": {"score": "N/A"},
    "ESCRITURA": {"score": 1, "fecha": "02/06/2026"}
  },
  "actividades": {"exposes_propiedad": null, "visitas_propiedad": 2,
                  "exposes_buscador": 25, "visitas_buscador": 4},
  "preguntas": {
    "cap_08": {"respuesta": "Sí", "cita": "[doc: 01_encargo] \"firmado por DocuSign\"", "confianza": "alta", "pendiente": "no"},
    "vue_01": {"pendiente": "sí"}
  },
  "avisos": [
    {"tipo": "Prueba débil", "aviso": "Firma del encargo sin cotejar con DNI (cap_08d).",
     "impacto": "Hito ENCARGO", "fuente": "PREGUNTAS cap_08d", "severidad": "media",
     "accion": "Recabar DNI para cotejar.", "sube": "no", "estado": "abierto"}
  ]
}
```

Claves de hito admitidas: `CUANTIA, ENCARGO, IDENT_PROPIETARIO, TITULARIDAD, HOJA_VISITA, OFERTA, IDENT_BUSCADOR, ARRAS_ARRENDAMIENTO, RECON_HON_ARRAS, ESCRITURA, RECON_HON_ESCRITURA, RECLAMACION_JURIDICO, RESPUESTA_RECLAMACION, OFERTA_VINCULANTE_CONFIDENCIAL` (el script también acepta los rótulos de pantalla). Un hito sin score, o con `"pendiente"`, queda **vacío** (no `0`).

## Ficheros de la skill
- `assets/plantilla_informe_viabilidad.xlsx` — plantilla limpia de 4 hojas (formato/fórmulas/semáforo/protección). Punto de partida obligatorio del render.
- `references/cuestionario_viabilidad.yaml` — vista del cuestionario (88 preguntas) **GENERADA** desde `data/_plantillas/cuestionario_viabilidad.yaml`; regenerar con `scripts/sync_cuestionario_from_canon.py`, no editar a mano.
- `references/hitos_derivacion.md` — reglas de derivación de los 14 hitos e importes.
- `references/modelo_xlsx.md` — mapa de celdas de las 4 hojas y reglas técnicas del .xlsx.
- `scripts/render_informe.py` — render del .xlsx desde el JSON (salida paralela, no sobrescribe).
- `scripts/sync_cuestionario_from_canon.py` — regenera la vista del cuestionario desde el canónico del repo (fuente única).

## Encadenamiento
`A (documentos)` → entrevista → `A (transcripción, 2ª pasada — futura)` → `B (informe-viabilidad-ev: valora, recuadro y bitácora)`.
