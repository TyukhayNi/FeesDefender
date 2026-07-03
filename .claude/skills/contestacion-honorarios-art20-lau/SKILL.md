---
name: contestacion-honorarios-art20-lau
description: >-
  Contestación a la demanda en defensa de la agencia inmobiliaria (típicamente
  EV MMC SPAIN / Engel & Völkers) frente a la reclamación del arrendatario de
  DEVOLUCIÓN DE HONORARIOS ex art. 20.1, último párrafo, LAU (Ley 12/2023),
  habitualmente con recalificación previa a vivienda habitual y subsidiarias
  de nulidad del encargo por vicio del consentimiento y abusividad. Úsala SIEMPRE que, representando a la
  agencia, haya que contestar una demanda de reembolso de honorarios; dispara
  con "art. 20 LAU honorarios", "devolución de comisión de agencia", "20.1 LAU
  arrendatario", "nos reclaman los honorarios de la inmobiliaria", "contestar
  demanda Engel & Völkers honorarios". Aporta los ocho motivos como Hechos, el
  uso quirúrgico de las resoluciones de apoyo, la prueba de oro, el suplico en
  cascada y la plantilla maestra; orquesta cendoj-descarga,
  verificacion-anclada-fuente, escritos-judiciales y pase-de-estilo. NO redacta
  la demanda del arrendatario, NO es la oposición del 408.2 LEC ni genera el .docx.
metadata:
  type: workflow
  jurisdiction: ES
  area: civil
  version: "1.1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# Contestación a la demanda — devolución de honorarios (art. 20.1 LAU)

## Qué resuelve esta skill

El arrendatario demanda a la agencia inmobiliaria (en los asuntos del despacho,
normalmente EV MMC SPAIN, S.L.U., «la Agencia») pidiendo la devolución de los
honorarios que pagó por los servicios de la agencia, con fundamento en el art.
20.1, último párrafo, LAU (redacción de la disposición final primera, apartado
cuatro, de la Ley 12/2023, por el derecho a la vivienda). El patrón típico de la
demanda encadena tres pretensiones: (a) recalificar el contrato —normalmente de
temporada— a arrendamiento de vivienda habitual, por simulación o fraude de ley;
(b) sobre esa base, condenar a la agencia a restituir los honorarios ex art.
20.1 LAU; y (c) subsidiariamente, anular el encargo de prestación de servicios
por vicio del consentimiento y/o por abusividad de la cláusula de honorarios.

Esta skill prepara la contestación completa: fija la estrategia, pregunta al
letrado las decisiones que condicionan el escrito, selecciona y ordena los ocho
motivos de oposición, dirige la prueba documental y produce —encadenando con
`escritos-judiciales`— el `.docx` final con el formato del despacho.

Nació del asunto W-02THLJ (contestación íntegra aprobada por el letrado) y
bundlea esa experiencia: la plantilla maestra placeholderizada
(`assets/plantilla-maestra.txt`), las plantillas de los motivos y el suplico en
cascada, y las advertencias sobre el uso de las resoluciones de apoyo.

## Estrategia maestra

**Desacoplar a la Agencia del debate habitual/temporal.** La pelea sobre si el
arrendamiento era de vivienda habitual o de temporada es, ante todo, un pleito
entre arrendatario y arrendador. La primera línea de defensa de la Agencia no
depende de esa calificación: el art. 20.1 LAU impone la obligación **solo al
arrendador**, y el contrato de encargo con la Agencia es *res inter alios acta*
(art. 1257 CC). Sea el contrato habitual o temporal, la acción de reembolso
contra la Agencia está mal dirigida. Solo subsidiariamente se entra en la
calificación (y entonces la temporalidad juega a favor: motivo 4).

Corolarios prácticos que la experiencia ha fijado:

- **Congruencia (art. 218 LEC).** Si el arrendador es codemandado, la acción de
  reembolso mal dirigida contra la Agencia debe llevar a su absolución: el juez
  no puede condenar al codemandado por una pretensión que no se dirigió contra
  él sin incurrir en incongruencia. Úsalo como argumento de refuerzo del motivo 1.
- **Terminología: «el Inmueble», nunca «la vivienda».** Referirse al objeto como
  «vivienda» en el propio escrito socava el motivo de temporada (motivo 4).
  Revisa el texto final: ninguna mención a «la vivienda» fuera de citas
  literales de preceptos o resoluciones.
- **Numeración de párrafos corrida y común a todo el escrito** (criterio Sala
  1.ª del despacho), no reiniciada por hechos.

## Encadenamiento con otras skills

Esta skill es la orquestadora del asunto. Apóyate en:

- **`verificacion-anclada-fuente`** — transversal desde el primer minuto.
  Ninguna cita, cifra o fecha entra «de memoria»: todo anclado a fuente (BOE,
  CENDOJ; subsidiariamente vLex/Lefebvre). Las citas de las resoluciones de
  apoyo se cotejan contra el PDF que obre en el expediente.
- **`cendoj-descarga`** — para localizar/descargar resoluciones. **Aviso**: las
  tres resoluciones de apoyo del playbook son de Primera Instancia y **rara vez
  están en CENDOJ**; no pierdas tiempo buscándolas allí: pídelas al expediente o
  al letrado (ver `references/resoluciones-apoyo.md`).
- **`escritos-judiciales`** — léela antes de generar el `.docx`: formato Sala
  1.ª (TNR 12, márgenes 2,5 cm, interlineado 1,5, citas 10 pt en cursiva con
  sangría, numeración corrida), guardado en `05_Procedimiento` y registro.
- **`pase-de-estilo`** — pase final: retira marcas de IA (em dash, tríadas,
  muletillas) sin tocar fondo ni citas.
- **`preparacion-litigio-civil`** — si el expediente no está montado, pásala
  primero.

## Decisiones previas del letrado (no redactes sin ellas)

Pregunta por chat, en un solo turno, y espera respuesta. Cada una cambia la
estructura del escrito:

1. **Territorio del pleito.** ¿Cataluña o fuera? Dentro: se incluye el motivo 3
   (doble retribución lícita ex art. 55.6.i Ley 18/2007). Fuera: se omite y se
   **renumeran** los motivos siguientes.
2. **Posición procesal.** ¿Solo la Agencia demandada, o codemandada con la
   propiedad? Si hay codemanda, incorporar el argumento de congruencia (art. 218
   LEC) al motivo 1 y coordinar con la defensa del arrendador.
3. **¿Consta factura de la Agencia al propietario?** Si consta: prueba directa
   de la doble retribución pactada. Si no consta: usa la **variante «coste
   absorbido»** (los honorarios de la propiedad se pactaron en el encargo de
   comercialización aunque no se facturaran separadamente); no afirmes nunca una
   facturación que no esté en el expediente.
4. **Enfoque frente a la recalificación.** ¿Desacople puro (no entrar en el
   debate habitual/temporal, motivos 1-3) o además impugnar la simulación de
   frente (motivo 4 con toda su carga fáctica)? Depende de la solidez de la
   prueba de temporalidad (ver «Punto flaco»).
5. **Disponibilidad de las resoluciones de apoyo.** ¿Obran en el expediente los
   PDF de las SJPI de Valencia, Madrid y Barcelona? Sin el PDF no se cita ni se
   aporta (ver `references/resoluciones-apoyo.md`).

## Flujo de trabajo

Trabaja por fases y confirma cada hito con el letrado antes de avanzar.

### Fase 1 — Lectura del expediente

1. Lee la **demanda y todos sus documentos**: la propia documental del actor
   suele contener el material del desacople (solicitud del portal inmobiliario
   con horizonte temporal declarado, resolución de mutuo acuerdo, contrato
   posterior…). Inventaría qué documento del actor sostiene qué motivo propio.
2. Lee el expediente de la Agencia: encargo con la propiedad, exposé, registro
   CRM, comunicaciones consultora-actor, encargo de servicios firmado, oferta,
   contrato, factura, certificados de solvencia.
3. **Línea roja:** el hilo interno de la consultora con el departamento legal
   **no se aporta nunca** — contiene admisiones perjudiciales. Si el letrado
   pide algo de ese hilo, extrae el dato, jamás el documento.
4. Cronología con marcas horarias del CRM (nexo causal: el lead entra por otro
   inmueble y la Agencia le propone el arrendado). Es la espina dorsal de los
   Hechos Primero y Segundo.

### Fase 2 — Decisiones del letrado

Formula las cinco preguntas del apartado anterior. Registra las respuestas: de
ellas depende qué motivos entran y con qué numeración.

### Fase 3 — Esqueleto: los motivos como Hechos

La arquitectura del escrito es «motivos como Hechos» (arts. 399/405 LEC): los
motivos de oposición no van en los fundamentos de derecho sino que se
desarrollan como Hechos autónomos, cada uno con su triple estructura interna
(X.1 tesis · X.2 soporte fáctico · X.3 soporte normativo y jurisprudencial).
Los fundamentos de derecho quedan reducidos a los procesales (competencia,
legitimación —con remisión al Hecho correspondiente—, postulación, iura novit
curia, costas).

Estructura completa (caso de ocho motivos, Cataluña, con temporada):

| Hecho | Contenido |
|---|---|
| PREVIO | Objeto de la oposición y estructura; nomens («el Inmueble», «el Encargo») |
| PRIMERO | Comercialización del Inmueble por la Agencia (las cuatro fases; inversión y riesgo) |
| SEGUNDO | Información previa al actor, suscripción del Encargo y ejecución hasta el buen fin |
| TERCERO | Hechos omitidos o tergiversados por la actora |
| CUARTO a UNDÉCIMO | Motivos 1 a 8 (ver `references/motivos.md`) |

Los ocho motivos, con su condición de inclusión:

1. **Falta de legitimación pasiva ad causam** acotada a la acción de reembolso
   (art. 20.1 LAU obliga solo al arrendador; art. 1257 CC). Siempre.
2. **Naturaleza distinta**: mediación/corretaje ≠ gestión inmobiliaria /
   formalización (canon literal, jurisprudencial y sistemático —Título IV Ley
   12/2023—). Siempre.
3. **[Solo Cataluña]** Doble retribución lícita ex art. 55.6.i Ley 18/2007 *a
   sensu contrario*, con acuerdo expreso doblemente documentado (cláusula del
   encargo con la propiedad + encargo del arrendatario).
4. **[Si el contrato es de temporada]** Subsidiario y en todo caso: art. 20.1
   (Título II) inaplicable por el art. 4 LAU; refuerzo con actos propios (art.
   7.1 CC). Plantilla íntegra en `assets/motivo-temporada.txt`.
5. **Subsidiario**: vulneración de la libertad de empresa (art. 38 CE) y
   cuestión de inconstitucionalidad **in praesenti** (audiencia del art. 35.2
   LOTC pedida ya en el suplico, no anunciada para más adelante). Siempre.
6. **Subsidiario**: exceso del perímetro objetivo del art. 20.1 (destinatario,
   objeto y causa distintos). Siempre.
7. **Improcedencia de la nulidad por vicio del consentimiento** (arts.
   1265/1266 CC; STS 683/2012: esencialidad + excusabilidad + nexo causal;
   triple soporte informativo). Si la demanda la pide.
8. **Improcedencia de la nulidad parcial por abusividad** (la cláusula de
   honorarios define el objeto principal, art. 4.2 Dir. 93/13; solo cabe
   control de transparencia, que se supera; STS Pleno 241/2013). Si la demanda
   la pide.

Si un motivo no entra, **renumera** los siguientes y ajusta las remisiones
internas y el suplico. Propón el índice al letrado y espera aprobación.

### Fase 4 — Resoluciones de apoyo

Lee `references/resoluciones-apoyo.md` **antes** de citar ninguna. Regla de
oro: son **criterio judicial coincidente** (resoluciones de instancia), nunca
«jurisprudencia» (art. 1.6 CC exige doctrina reiterada del TS). Cada resolución
sirve para lo que sirve — usarla fuera de su perímetro regala munición a la
contraria.

### Fase 5 — Redacción motivo a motivo

1. Redacta **un Hecho por turno** y propónlo por chat; no avances sin
   aprobación. La plantilla maestra (`assets/plantilla-maestra.txt`) aporta el
   texto base de cada apartado; adapta hechos, fechas y documentos al caso.
2. Citas de documentos **insertadas en el cuerpo** (inmediatez probatoria);
   citas literales en cursiva, 10 pt, sangría 1 cm.
3. Los pantallazos del CRM se insertan **como imagen** en el escrito (no
   transcritos), con su traducción si están en lengua extranjera. Recuerda: las
   imágenes pegadas en el chat **no son ficheros** — pide al letrado que las
   suba como archivos o localízalas en el expediente.
4. Estilo de la casa: aplica el contrato de estilo del despacho; nada de
   «vivienda» fuera de citas literales.

### Fase 6 — Índice documental

Monta la documental siguiendo `references/indice-documental.md` (la «prueba de
oro»). Documentos en lengua extranjera: acompaña traducción (art. 144 LEC);
la traducción del exposé puede delegarse a un subagente mientras se redacta.

### Fase 7 — Verificación y generación del .docx

1. Pase de `verificacion-anclada-fuente` sobre el borrador completo: citas,
   cifras, fechas, remisiones internas, coherencia del suplico con los motivos
   efectivamente incluidos.
2. Genera el `.docx` con `escritos-judiciales` (formato Sala 1.ª). Notas
   operativas aprendidas (evitan los tropiezos de la primera vez):
   - Escribe el script generador **vía heredoc a `/tmp`** (evita truncados por
     desajuste con el mount).
   - Numeración de párrafos corrida vía inyección en `numbering.xml`.
   - Render de control `docx→PDF` con `libreoffice --headless --convert-to pdf`
     y revisión visual (sangrías, imágenes, cursivas).
3. Pase final de `pase-de-estilo` (sin tocar fondo ni citas).
4. Recorre `assets/checklist-entrega.md`.

### Fase 8 — Guardado y registro

1. Guarda en `05_Procedimiento` del expediente (modo estructurado de
   `escritos-judiciales`, que también registra en el intake).
2. Telemetría de la skill (mejora continua):

   ```bash
   python scripts/registrar_uso.py contestacion-honorarios-art20-lau <REF> contestacion_art20 \
       --archivos CONTESTACION_DEMANDA_<REF>.docx \
       --metricas '{"territorio": "cataluna", "codemanda_propiedad": false, "n_motivos": 8, "motivo_temporada": true, "variante_coste_absorbido": false, "cuestion_inconstitucionalidad": true}'
   ```

## Punto flaco y línea roja

- **Punto flaco: la temporalidad no documentada.** El motivo 4 solo es fuerte si
  la temporalidad está anclada en documentos (calificación expresa en el
  contrato, horizonte temporal declarado por el propio actor en su solicitud,
  domicilio permanente distinto, abandono anticipado). Si la prueba es débil,
  recomienda al letrado el desacople puro (decisión 4) y no des a la contraria
  un flanco fáctico.
- **Línea roja: el hilo interno consultora-departamento legal no se aporta
  jamás.** Contiene admisiones perjudiciales. Sin excepciones.

## Variantes

- **Territorio**: Cataluña (motivo 3 incluido) / fuera (omitido, renumerando).
  La plantilla maestra marca los bloques con `[VARIANTE]…[FIN VARIANTE]`.
- **Factura al propietario**: si no consta, variante «coste absorbido» (motivo
  3 y Hecho Primero).
- **Contestación corta**: si el letrado decide jugarlo todo a la legitimación
  pasiva (p. ej. cuantía baja, juicio verbal, estrategia de coste), existe el
  formato reducido de dos Hechos (falta de legitimación + su consecuencia
  procesal: resolución en audiencia previa y sentencia desestimatoria). Precedente
  del despacho: contestación EV Santander, PO 318/2026. Confírmalo expresamente
  antes de usarlo: renuncia a los motivos de fondo.

## Recursos bundleados

| Fichero | Cuándo leerlo |
|---|---|
| `references/motivos.md` | Fase 3 y Fase 5: desarrollo de cada motivo, citas núcleo, errores a evitar |
| `references/resoluciones-apoyo.md` | Antes de citar cualquier resolución de apoyo |
| `references/jurisprudencia/` | PDF anonimizados de las SJPI de Valencia y Madrid + `INDICE.md` con pasajes verificados |
| `references/indice-documental.md` | Fase 6: prueba de oro, función de cada documento |
| `assets/plantilla-maestra.txt` | Fase 5: texto base íntegro (variante Cataluña, 7 motivos, placeholders) |
| `assets/FORMULARIO_CONTESTACION.docx` | Formulario tipo en Word (mismo texto que la plantilla maestra) para trabajar a mano sin asistencia |
| `assets/motivo-temporada.txt` | Fase 5: plantilla del motivo 4 (no está en la maestra) |
| `assets/suplico-cascada.txt` | Fase 5: suplico en cascada completo (versión 8 motivos) |
| `assets/checklist-previo.md` | Antes de la Fase 3 |
| `assets/checklist-entrega.md` | Fase 7, antes de dar por listo el escrito |
