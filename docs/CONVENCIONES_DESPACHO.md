---
estado: vigente
dueño: Nikolai Tyukhay
titulo: "Convenciones del Despacho — destilado operativo"
fuente: "docs/MANUAL_GESTION_INTERNA_DESPACHO.txt (V.2020-1)"
indice_completo: "docs/MANUAL_DESPACHO.md"
fecha: 2026-04-26
proposito: |
  Reglas operativas accionables extraídas del manual del despacho. Es
  el documento que se inyecta como contexto en los prompts forenses
  para que el LLM aplique los criterios reales del despacho. Cuando
  cambien las convenciones, actualizar aquí (y, si procede, también
  en el manual fuente).
---

# Convenciones del Despacho

Reglas con las que opera el despacho día a día, destiladas del manual.
Las que afectan a redacción de escritos, formato y registros se cargan
como contexto a `prompts/demanda.md`, `prompts/requerimiento.md`,
`prompts/viabilidad.md` y futuros prompts EV-específicos.

## 1. Roles y matriz de responsabilidades

**Abogado Senior / titular** (Nikolai Tyukhay). Único que firma los
escritos, único que presta consentimiento sobre acuerdos transaccionales
en nombre del cliente, conduce la reunión semanal con el CFO de Engel
(Ricardo) para aprobación de propuestas. Dedicación-tipo: 10 min por
monitorio, 2 h por demanda ordinaria, 9 h por juicio.

**Abogado** (Paola Barreto). Revisión jurídica y de cálculo de borradores
preparados por Junior, firma de escritos incidentales (tasaciones,
liquidaciones, recursos de reposición), control de viabilidad.

**Abogado Junior** (Sergio Piñol). Preparación de borradores de demanda,
minutas y cuadros de cálculo, escritos iniciales y de trámite. Dedicación
tipo: 4 h monitorio, 15 h demanda ordinaria, 3 h audiencia previa.

**Administración Tyukhay** (Ana Velastegui, Olga Osipova). CRM y archivo,
fichas de Clientes/Contrarios/Colaboradores, citaciones a testigos,
facturación, conciliación bancaria, reporte mensual de horas, control de
plazos vía agenda. Dedicación tipo: 1 h monitorio, 1 h demanda ordinaria,
30 min audiencia previa.

**Administración Engel Legal** (Marta Reynares). Comparte carpetas Drive
de operaciones, mantiene listados Bad Debt.

**CFO Engel** (Ricardo). Aprobación de presupuestos de defensa judicial,
firma de propuestas vía DocuSign tras reunión con el Senior.

## 2. Comunicación con el cliente Engel

### Emails centrales

| Dirección | Para qué |
|---|---|
| `procesal@tyukhay.legal` | Lista de distribución (Nikolai, Paola, Ana, Sergio) — todas las notificaciones de procuradores entran aquí. |
| `contabilidad@tyukhay.legal` | Facturas de proveedores y suplidos de procuradores. Separa de procesal. |
| `nikolai.tyukhay@engelvoelkers.com` | Copia obligatoria en hitos procesales y comunicaciones a Engel. |

### Reglas de comunicación con Engel

- Comunicación escrita siempre, no oral, para los hitos procesales. Genera
  registro y refuerza la valoración del trabajo.
- Plantillas obligatorias del CRM (ver `MANUAL_DESPACHO.md` sección
  *Plantillas CRM*). No improvisar.
- Personalización mínima: adaptar saludo y datos pero conservar la
  estructura de la plantilla.
- Sin jerga legal innecesaria — los destinatarios son operativa y
  finanzas, no abogados.
- **Confidencialidad estricta sobre la negociación de acuerdos**: la
  correspondencia de negociación NO se traslada al cliente bajo ninguna
  circunstancia. Su revelación generaría responsabilidad disciplinaria.

### Hitos a notificar por procedimiento

**Diligencias preliminares.** Presentación → número de autos → señalamiento
→ resultado → informe.

**Monitorios.** Presentada demanda → número de autos → admisión + requerimiento
→ resultado.

**Declarativos.** Número de autos / admisión → citación testigos → celebrado
juicio → sentencia.

**Ejecuciones.** Demanda ejecutiva → auto despachando ejecución → archivo por
falta de activos (si procede).

## 3. Taxonomía de casos (etiquetas/tags en CRM)

Cada expediente lleva como mínimo tres tags por orden: **(i) Equipo, (ii)
Asunto, (iii) Valoración de riesgo**.

Asuntos canónicos:

- `BAD DEBT` — impago de factura.
- `NEGATIVA OFERTA` — vendedor/comprador rechaza aceptar oferta.
- `NEGATIVA ARRAS` — rechazo a firmar arras tras aceptar oferta.
- `NEGATIVA ESCRITURA` — rechazo a escriturar tras firmar arras.
- `VUELTA` — el cliente se aprovecha de la gestión de la agencia.
- `INCUMPLIMIENTO EXCLUSIVA` — ruptura del pacto de exclusiva.
- `DEVOLUCIÓN RESERVA` — comprador/arrendatario reclama devolución.
- `LAU 20` — arrendatario reclama devolución honorarios (art. 20.4 LAU).
- `DEVOLUCION HONORARIOS` — cliente reclama devolución de honorarios pagados.
- `RESPONSABILIDAD PROFESIONAL` — daños y perjuicios por falta de diligencia.
- `FRANQUICIA` — asunto con empresa franquiciada.
- `CONSULTORES` — reclamaciones de consultores frente a la agencia.

## 4. Valoración de riesgo y posibilidad de éxito

### Riesgo (cuando Engel es demandado)

- `RIESGO REMOTO` (>15 % de probabilidad) — hay transacción cerrada o
  >2 años desde la última actuación.
- `RIESGO POSIBLE` (15-50 %) — defecto.
- `RIESGO PROBABLE` (<50 %) — *"si yo fuera el abogado del reclamante,
  recomendaría reclamar"*.

### Posibilidad de éxito (cuando Engel es actor)

- `50 %` por defecto en asuntos nuevos.
- `<15 % – >50 %` en procedimientos ejecutivos < 1 año de antigüedad.
- `<15 %` en ejecutivos > 1 año de antigüedad.

## 5. Bad Debt — fases por antigüedad de la deuda

| Días | Fase | Acción | Provisión |
|---|---|---|---|
| 0–25 | Administrativa | Requerimiento de pago (burofax). Finanzas prepara, Legal envía. | 0 % |
| 25–55 | Administrativa | OVC (MASC) + preparación expediente extrajudicial. | 0 % |
| 40–70 | Contenciosa | Evaluación de éxito y aprobación presupuestos (Legal/Finanzas/Dirección). | 0 % |
| 90–120 | Contenciosa | Comienzo proceso judicial. | 50 % |
| 120–180 | Contenciosa | — | 75 % |
| >180 | Contenciosa | — | 100 % |

**OVC** se envía 15 días después del requerimiento si no hay respuesta.
3 canales: SMS certificado, email certificado, burofax. SMS literal:
*"EV MMC SPAIN, S.L.U. le remite Oferta Vinculante Confidencial (OVC) y
propuesta de negociación extrajudicial. Consulte el documento adjunto."*

**Plazos clave**:

- Recurso de apelación: **20 días**.
- Cumplimiento voluntario tras sentencia firme: **20 días hábiles**.
- Reclamación de prueba al equipo Engel: si en **30 días** no llega, se
  archiva el expediente.

## 6. Formato de los escritos judiciales (Sala 1ª TS)

Estos requisitos son los que ya tenemos cableados en los prompts forenses
del proyecto. Confirmados desde el manual:

- **Extensión** máxima 25 páginas (demandas y recursos).
- **Fuente** Times New Roman.
  - Texto: 12 pt.
  - Notas a pie: 10 pt.
  - Citas: 10 pt, cursiva, alineación justificada, sangría izquierda 1 cm.
- **Márgenes** 2,5 cm (los cuatro lados).
- **Párrafo** alineación justificada, interlineado 1,5, espaciado anterior
  6 pt, posterior 0 pt, espacio entre párrafos del mismo estilo.
- **Numeración de párrafos** obligatoria, con jerarquía 1 / 1.1 / 1.1.1.
- **Citas de documentos**: cuando el formato lo permita, copiar el
  fragmento citado directamente en la demanda (favorece inmediatez
  probatoria).
- **Números de página** Times New Roman 12, alineación centrada.
- **Índices de demanda** solo en demandas complejas (vueltas, negativas;
  no Bad Debt). Para esos se usa GPT específico para indexar documentos.

## 7. Aportación de documentos

- Formato **PDF**. Si pesa más de 1 MB, comprimir (ilovepdf u otro).
- Solo se aporta el email **relevante** de la cadena, no el reenvío del
  cliente.
- Emails en orden cronológico, los más antiguos primero.
- Grabaciones: **mp3 + transcripción**. Servicio de transcripción:
  sonix.ai.
- Rotulado: en la esquina superior derecha, *"DOCUMENTO Nº XX"* en
  Helvética 20, color rojo, MAYÚSCULAS. PDF firmados con firma electrónica
  cualificada deben convertirse antes a imagen ("Imprimir → Imprimir en
  PDF") para poder rotularse.
- **Nomenclatura de archivos**:
  - Sin símbolos especiales (Lexnet rechaza `,.\`!"`).
  - Patrón `D 01 - PODER.pdf`. El número siempre con cero delante para
    01-09 (necesario para que Sudespacho ordene correctamente).
  - Sin artículos.

### Check list de documentos para monitorio Bad Debt

```
D 01 - ESCRITURA PODER (HABITUALMENTE APUD ACTA)
D 02 - CONTRATO MEDIACION INMOBILIARIA (FIRMADO POR DEUDOR)
D 03 - DNI DEUDOR
D 04 - NOTA INFORMATIVA SOCIEDAD DEUDORA (si jurídica)
D 05 - OFERTA COMPRA/ARRENDAMIENTO/TRASPASO (firmada)
D 06 - CONTRATO PRIVADO COMPRAVENTA / ARRAS (firmado)
D 07 - NOTA SIMPLE INFORMATIVA COMPRADOR/ARRENDATARIO (si jurídicas)
D 08 - RECONOCIMIENTO HONORARIOS (a veces no existe)
D 09 - 1ª FACTURA
D 10 - JUSTIFICANTES DE PAGOS PARCIALES
D 11 - FACTURA 2ª PARTE (impagada)
D 13/D 14 - CERTIFICADOS REQUERIMIENTOS FINALES
D 15/D 16/D 17 - CERTIFICADOS OVCs (sin la página del contenido económico)
```

## 8. Datos personales en CRM (fichas Cliente, Contrario, Abogado contrario, Colaborador)

- Nombre y apellidos: **MAYÚSCULAS, SIN ACENTOS**.
- Email: **minúsculas**.
- Móvil, teléfono fijo: ficha completa.
- Contrario: NIF/DNI/NIE + dirección postal completa **EN MAYÚSCULAS**.
- Abogado propio: NIF, dirección postal MAYÚSCULAS, nº colegiado
  formato `33.146`, nombre del colegio en minúsculas.
- Nº de autos: `1234/2020` (sin punto de miles).

## 9. Nomenclatura de juzgados (tras reforma Tribunales de Instancia)

Formato:

El encabezamiento nombra la **Sección** del Tribunal de Instancia que
corresponda a la materia:

```
SECCION CIVIL DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE INSTRUCCION DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION CIVIL Y DE INSTRUCCION DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE FAMILIA, INFANCIA Y CAPACIDAD DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE LO PENAL DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE VIOLENCIA SOBRE LA MUJER DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE LO SOCIAL DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE LO CONTENCIOSO-ADMINISTRATIVO DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE LO MERCANTIL DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE MENORES DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
SECCION DE VIGILANCIA PENITENCIARIA DEL TRIBUNAL DE INSTANCIA DE [CIUDAD]. PLAZA Nº [N]
AUDIENCIA PROVINCIAL [CIUDAD], SECCION CIVIL Nº [N]
```

En los escritos de honorarios del despacho se usa por defecto la **Sección
Civil** (o **Civil y de Instrucción** en partidos pequeños que la tengan
combinada).

Antes (no usar): `JUZGADO DE PRIMERA INSTANCIA Nº 1 DE BARCELONA`.
Ahora: `SECCION CIVIL DEL TRIBUNAL DE INSTANCIA DE BARCELONA. PLAZA Nº 1`.

## 10. Procuradores propios

| Partido judicial | Procurador propio |
|---|---|
| Barcelona | Alfredo Martinez Sanchez |
| Valencia | Pilar Ibañez |
| Madrid | Maria Soledad Castañeda |
| Resto | Ficha "PROCURADOR PROPIO" del CRM, o si no, Consejo General de Procuradores. Antes de asignar, contactar al procurador para verificar incompatibilidad. |

## 11. Tiempos estándar (para rentabilidad y planificación)

| Actuación | Junior | Senior | Admin |
|---|---|---|---|
| Demanda monitorio | 4 h | 10 min | 1 h |
| Demanda ordinaria | 15 h | 2 h | 1 h |
| Audiencia previa | 3 h | 2 h | 30 min |
| Juicio | 2 h | 9 h | 2 h |
| Diligencias preliminares | 4 h | 3 h | 2 h |

Señalamientos para reservar agenda: audiencia previa 1 h, juicio 2 h.

## 12. Imputación de horas

- Si la actuación corresponde a expediente concreto → ese expediente.
- Si es genérica (reunión semanal de equipo, agenda CFO, formación)
  → expediente extrajudicial **23/2023-N**.
- Actuaciones extrajudiciales relacionadas con expedientes EV o ENGEL
  & VÖLKERS SPAIN, S.L.U. son **facturables** por defecto.
- Mensualmente, la Admin prepara el reporte de horas para la reunión
  con el CFO (`REPORTE MENSUAL HORAS .xlsx`).

## 13. Carpetas Drive Engel (rutas conocidas)

```
JURÍDICO/ENGEL/CONTINGENCIAS/
├── 01.EXTRAJUDICIALES/
├── 04.JUDICIALES/
│   └── <CIUDAD>/
└── 07.BAD_DEBT/
```

En cada propiedad se crea una subcarpeta `_DEMANDA` con el informe de
viabilidad y las pruebas.

Para modificación de bases imponibles del IVA:
`MODIFICACIÓN BASES IMPONIBLES/TRIMESTRE XX/<refer_propiedad>/`.

## 14. CRM Gestor Documental — taxonomía de carpetas

Cada expediente del CRM tiene árbol predefinido. Criterios de archivo:

- **Tipo de asunto**: CIVIL, PENAL, DOCUMENTOS (cajón de sastre).
- **Fase**: 1ª INSTANCIA, APELACIÓN, EJECUCIÓN.
- **Trámite procesal**: DECLARATIVO (demanda y sus documentos),
  OPOSICIÓN (escritos contrarios), EJECUCIÓN, etc.

## 15. Reglas para nombrar archivos del CRM Gestor Documental

```
[TIPO]   [CONTENIDO]
SENT - 1ª INST - EST TOTAL
AUTO - INC EXEJC
DECR - DESP EJEC
DIOR - REQ APOR TASA
PROV - POR PRECUL PLAZO
DILIG - NOTIFICACION NEGATIVA DEMANDA
JUST ESCR - ACL CUANTÍA          (escrito propio)
ESCR CRIO - ALEG COMPET           (escrito contrario)
ESCR CODEM                        (codemandado/codemandante)
FRA PROC - FASE PROCEDIMIENTO     (factura procurador)
```

Resoluciones del Letrado de la Administración de Justicia:
DECR (decreto), DIOR (diligencia de ordenación), PROV (providencia),
DILIG (diligencia).

## 16. Acuerdo transaccional (MASC)

- Plantilla CRM `ENGEL - ACUERDO TRANSACCIONAL - PAGO CANTIDAD`.
- Borrador con palabra `DEFINITIVO` en el nombre del archivo.
- DocuSign con plantilla `ACUERDO TRANSACCIONAL - ENGEL ACREEDOR`.
- **Firma electrónica avanzada obligatoria** para los contrarios.
- Copia automática al firmar a: Team Leader del equipo, consultores
  implicados, departamento de finanzas Engel, abogados intervinientes.
- El Abogado Titular es el **único** que aprueba el contenido en nombre
  del cliente.

## 17. Tras pago derivado de acuerdo transaccional

1. Admin guarda cadena de correos de la negociación + justificante de
   pago en el Gestor Documental del expediente.
2. Admin envía justificante + certificado del acuerdo firmado al
   Departamento de Finanzas competente (Barcelona / Valencia / Madrid /
   etc.) con copia a `nikolai.tyukhay@engelvoelkers.com` y a Colaboradores.
3. Solicita facturas de abono y nuevas facturas (si Bad Debt) — para envío
   posterior al cliente.
4. **Confidencialidad**: NO enviar al cliente la correspondencia de
   negociación. Comunicación de pago va en correo independiente.
5. **Liquidación de gastos extrajudicial**: solo en negativas y vueltas
   (no Bad Debt). Se envía al Dpto. Finanzas con copia a Nikolai —
   **sin** copia a Colaboradores (evita debates sobre deducción).

## 18. Programas locales requeridos en el equipo del despacho

OCR local:

```
ocrmypdf
python
Tesseract (paquetes de ruso, castellano, catalán e inglés)
Ghostscript 10.07.0 for Windows (64 bit)
```

Anonimización (si se reactiva):

```
Presidio
spaCy (paquetes de ruso, castellano, catalán e inglés)
```

## 19. Informe de Viabilidad (negativas, vueltas, incumplimiento exclusiva)

**Plantilla canónica.** `docs/PLANTILLA_INFORME_VIABILIDAD.xlsx`. Es el
documento que se presenta al CFO de Engel (Ricardo) en la reunión semanal
de aprobación. Tras la reunión, sea cual sea la decisión (aprobar acción
judicial / descartar), se firma con DocuSign. Si se aprueba, el siguiente
paso operativo es **convertir el extrajudicial a judicial en el CRM**
(opción "Duplicar") y empezar la preparación de la demanda.

**Cuándo se usa.** Casos de NEGATIVA OFERTA / NEGATIVA ARRAS / NEGATIVA
ESCRITURA / VUELTA / INCUMPLIMIENTO EXCLUSIVA. **NO** se usa en BAD DEBT
(que tiene su propio flujo basado en el fichero de morosidad).

**Estructura del fichero (dos pestañas operativas).**

`INFORMACION` — datos del expediente y diagnóstico:

| Bloque | Campos clave |
|---|---|
| Cabecera | FECHA, REF (referencia BaCS1/MaRR1/etc), DIRECTOR/ASESOR CAPTADOR, DIRECTOR/ASESOR BUSCADOR |
| Observaciones | OBSERVACIONES, MOTIVOS DE IMPAGO |
| Importes | PRECIO, TOTAL HONORARIOS (% × PRECIO × 1,21), PAGOS PARCIALES, TOTAL DEUDA, PROPUESTA PAGO, DIFERENCIA |
| Viabilidad | JURÍDICO, FINANZAS (cualitativa) |
| Datos operación (chequeo doc) | CUANTIA, ENCARGO, IDENTIFICACIÓN PROPIETARIO, TITULARIDAD, HOJA VISITA, OFERTA, IDENTIFICACIÓN BUSCADOR, ARRAS/ARRENDAMIENTO, RECONOCIMIENTO HONORARIOS-ARRAS, ESCRITURA, RECONOCIMIENTO HONORARIOS-ESCRITURA, RECLAMACIÓN JURIDICO, RESPUESTA RECLAMACIÓN, OFERTA VINCULANTE CONFIDENCIAL — 14 hitos, cada uno con valor 1/0/N/A y fecha |
| Actividades | EXPOSES PROPIEDAD, VISITAS PROPIEDAD, EXPOSES BUSCADOR, VISITAS BUSCADOR (numérico) |

`PREGUNTAS` — subset operativo del Protocolo (≈ 50 preguntas) para
documentar la entrevista con consultores. Coincide con el protocolo de
63 preguntas pero condensado: bloques CAPTACION, COMERCIALIZACION,
VISITA, OFERTA / COMUNICACIÓN BUSCADOR-AGENCIA, COMUNICACIÓN INTERNA,
COMUNICACIÓN AGENCIA-PROPIETARIO, ARRAS, TEAM LEADER. (La pestaña
DOCUMENTOS de versiones antiguas está obsoleta y no se usa.)

**Flujo del Informe de Viabilidad — antes de la reunión con CFO.**

Antes de presentarlo a Ricardo, deben estar procesados todos estos
inputs:

1. Drive de la propiedad de Engel (carpeta `_DEMANDA`).
2. E-mails relevantes entre consultores y clientes (vendedor, comprador,
   notaría) — archivados en `mails.repositorio@gmail.com`.
3. Conversaciones de WhatsApp entre consultores y clientes (exportadas).
4. Resultados de la entrevista de viabilidad con los consultores
   implicados (grabada con Google Meet, transcripción en `_DEMANDA`).
5. Datos del CRM (encargo, oferta, hoja de visita, comunicaciones
   certificadas, certificados de OVC).

Con todo ello, Ana pre-rellena el INFORME (fechas clave, datos de check
de documentos, importes), y el Abogado completa la pestaña PREGUNTAS y
las observaciones cualitativas (viabilidad jurídica, motivos de impago,
puntos fuertes/débiles).

**Mapeo intake YAML → Informe de Viabilidad** (futuro generador automático
del wizard `kickoff_extrajudicial`):

| Sección protocolo (`prompts/intake_consulta.yaml`) | Pestaña destino | Campos |
|---|---|---|
| `captacion_encargo` (q01–q16) | INFORMACION (chequeo doc) + PREGUNTAS (CAPTACION) | ENCARGO, IDENTIFICACIÓN PROPIETARIO, TITULARIDAD; preguntas CAPTACION |
| `comercializacion` (q17–q18) | INFORMACION (Actividades) | EXPOSES PROPIEDAD, VISITAS PROPIEDAD |
| `visitas` (q19–q26) | INFORMACION (chequeo) + PREGUNTAS (VISITA) | HOJA VISITA, IDENTIFICACIÓN BUSCADOR; preguntas VISITA |
| `oferta_comprador` (q27–q35) | INFORMACION (chequeo) + PREGUNTAS (OFERTA) | OFERTA; preguntas COMUNICACIÓN COMPRADOR-AGENCIA |
| `comunicacion_interna` (q36–q38) | PREGUNTAS (COMUNICACIÓN INTERNA) | — |
| `comunicacion_agencia_vendedor` (q39–q45) | PREGUNTAS (COMUNICACIÓN AGENCIA-VENDEDOR) | — |
| `arras` (q46–q57) | INFORMACION (chequeo) + PREGUNTAS (ARRAS) | ARRAS/ARRENDAMIENTO, RECONOCIMIENTO HONORARIOS-ARRAS; preguntas ARRAS |
| `vueltas` (q58–q62) | OBSERVACIONES (cualitativo) | MOTIVOS DE IMPAGO |
| `team_leader` (q63) | PREGUNTAS (TEAM LEADER) | — |

**Implementación prevista.** El wizard `kickoff_extrajudicial`
recoge las respuestas vía YAML, genera dos artefactos en
`04_OUTPUT_PREDEMANDA/`:

```
04_OUTPUT_PREDEMANDA/
├── informe_viabilidad.md       Markdown con todas las respuestas
├── informe_viabilidad.xlsx     Réplica de la plantilla, pre-rellenada
                                con los datos del intake (fechas, checks,
                                importes calculados). Listo para
                                completar las observaciones cualitativas
                                y enviar a DocuSign.
```

El Abogado revisa, completa observaciones y viabilidad cualitativa, y
adjunta el `.xlsx` al envío DocuSign para la reunión con el CFO.

**Convención de nombre del fichero.** El fichero original sigue el patrón
`<REF> <DIRECCION> (<ID-GO>).xlsx`, p. ej. `BaCS1 Roger Lluria 38
BCN-OS-012905.xlsx`. El generador respetará ese patrón.

## 20. Particularidades de expedientes de responsabilidad civil de Engel

- Marcar como **SINIESTRO** en Datos Básicos.
- En Clientes, además de EV MMC SPAIN, S.L.U., añadir
  `AON IBERIA CORREDURÍA DE SEGUROS Y REASEGUROS S.A.U.`
- Crear dos siniestros: primero **HISCOX** (póliza HDIP62088689),
  segundo **AON**.
- Plantilla de comunicación al corredor:
  `ENGEL - SINIESTRO - COMUNICADO - EXTRAJUDICIAL`,
  destino `catalunya@aoncss.es`, copia a `procesal@tyukhay.legal`.
