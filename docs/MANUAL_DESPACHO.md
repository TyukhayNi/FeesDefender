---
estado: vigente
dueño: Nikolai Tyukhay
titulo: "Manual de Gestión Interna del Despacho — Índice Navegable"
fuente: "docs/MANUAL_GESTION_INTERNA_DESPACHO.txt (V.2020-1)"
fuente_lineas: 2022
fecha_lectura: 2026-04-26
proposito: |
  Mapa de navegación al manual completo. El texto fuente vive en
  `docs/MANUAL_GESTION_INTERNA_DESPACHO.txt` (64k tokens, demasiado grande
  para cargarlo entero). Este índice da las líneas exactas para que un
  futuro asistente lea solo la sección que necesite vía
  `Read --offset --limit` o `sed -n '<n>,<m>p'`.
  Las convenciones accionables ya destiladas viven en
  `docs/CONVENCIONES_DESPACHO.md`.
---

# Manual de Gestión Interna del Despacho — índice navegable

El manual completo está en `docs/MANUAL_GESTION_INTERNA_DESPACHO.txt`. Este
índice mapea sus secciones a rangos de línea para lectura selectiva. Los
asuntos accionables (formato, plazos, taxonomía, plantillas) están
destilados en `docs/CONVENCIONES_DESPACHO.md`.

## Tabla de contenidos por línea

| Sección | Líneas | Qué contiene |
|---|---|---|
| Definiciones | 103 – 108 | Roles: Administración, Abogado, Junior, Senior. |
| Imputación horas extrajudicial | 109 – 112 | Reglas para asignar horas a expedientes. |
| Duración actuaciones judiciales | 113 – 114 | Tiempos estándar referencia (monitorio: 4 h). |
| Reclamaciones extrajudiciales (Engel) | 115 – 289 | Flujo completo: requerimiento → MASC/OVC → propuesta demanda → acuerdo transaccional. |
| Bad Debt (Engel) — fases | 290 – 508 | Tabla por antigüedad de deuda, KPI, asignación a procurador, demanda monitorio, modificación bases imponibles IVA. |
| Envío propuesta defensa judicial | 509 – 558 | Reuniones con CFO Engel (Ricardo), DocuSign, archivo. |
| Búsqueda MBox (Thunderbird) | 559 – 574 | Cómo localizar emails relevantes. |
| Archivo de WhatsApp | 575 – 601 | Estructura de carpetas y exportación. |
| Apertura de expediente jud/extrajud | 602 – 693 | Datos a rellenar, etiquetas/tags, taxonomía de asuntos. |
| Forma de los escritos judiciales | 694 – 755 | Sala 1ª TS: 25 pp, Times New Roman 12, márgenes 2,5 cm, interlineado 1,5. |
| Aportación de documentos | 756 – 814 | Formato PDF, rotulado, nomenclatura. |
| Gestión Documental CRM | 815 – 990 | Nomenclatura de archivos, carpetas Gdocu, juzgados (Tribunales de Instancia). |
| Gestión de actuaciones | 991 – 1100 | Predefinidas, facturables, ejemplos. |
| Gestión de la agenda | 1101 – 1110 | Tipos de eventos. |
| Gestión de plazos | 1111 – 1118 | Vencimientos, control. |
| Gestión de señalamientos | 1119 – 1166 | Registro CRM, plantilla "TJ - SEÑALAMIENTO VISTA". |
| Procedimiento ordinario | 1167 – 1226 | Admisión a trámite, contestación. |
| Audiencia previa | 1227 – 1280 | Antes y después de audiencia. |
| Después de un juicio | 1281 – 1295 | Registro actuaciones, control grabación. |
| Después de una sentencia civil | 1296 – 1370 | Recurso apelación, costas, cumplimiento voluntario. |
| Tasación de costas / liquidación intereses / recursos reposición | 1371 – 1500 | Flujo Junior-Abogado-Admin. |
| Ejecución forzosa civil | 1501 – 1700 | Embargos, averiguaciones, despacho. |
| Consignaciones judiciales | 1701 – 1750 | Solicitud entrega, comunicación al cliente. |
| Tesorería / Conciliación bancaria | 1751 – 1840 | Fichero de tesorería, conciliación cobros y pagos. |
| Facturación recibida | 1841 – 1875 | Gastos registradores, refacturación. |
| Satisfacción y comunicación con Engel | 1876 – 1940 | Plantillas e-mail por procedimiento (diligencias prelim, monitorios, declarativos, ejecuciones). |
| Rentabilidad y tiempos por actuación | 1941 – 1985 | Horas estándar Junior/Admin/Senior por tipo. |
| Gastos de viajes | 1986 – 2010 | Suplidos, justificantes, refacturación. |
| Anexo 1 — Distribución de responsabilidades | 2011 – fin | Junior, Administración, Titulares. |
| Anexo — Check list documentos monitorio | 2011 – fin | D01–D17 nomenclatura. |
| Anexo — Programas a instalar | 2011 – fin | OCR local: ocrmypdf, Tesseract, Ghostscript, Presidio, spaCy. |

## Cómo leer una sección sin cargar el archivo entero

```bash
# Desde Bash dentro del proyecto (mount Linux):
sed -n '602,693p' "docs/MANUAL_GESTION_INTERNA_DESPACHO.txt"
```

```python
# Desde la herramienta Read del asistente:
Read(path="docs/MANUAL_GESTION_INTERNA_DESPACHO.txt", offset=602, limit=92)
```

## Roles citados en el manual (con referencia interna)

| Rol | Persona en el manual | Función principal |
|---|---|---|
| Abogado Senior / titular | Nikolai Tyukhay | Firma escritos, aprueba propuestas con CFO Engel, control general. |
| Abogado | Paola Barreto | Revisión jurídica, firma incidentales. |
| Abogado Junior | Sergio Piñol | Preparación borradores, minutas, cálculos. |
| Administración (Tyukhay) | Ana Velastegui, Olga Osipova | CRM, archivo, citaciones, facturación, conciliación. |
| Administración Engel Legal | Marta Reynares | Carpetas Drive de operaciones, listados Bad Debt. |
| CFO Engel | Ricardo | Aprueba propuestas y liquidaciones. |

## Referencias de procuradores propios (manual L437-440)

| Partido judicial | Procurador propio |
|---|---|
| Barcelona | Alfredo Martinez Sanchez |
| Valencia | Pilar Ibañez |
| Madrid | Maria Soledad Castañeda |
| Resto de partidos | Lista CRM "PROCURADOR PROPIO" o, si no hay, Consejo General de Procuradores. |

## Plantillas CRM que el manual nombra (no cambiar de título)

Estas plantillas se mencionan literalmente en el manual y se citan desde
los prompts de FeesGuard. Cualquier cambio aquí debe
sincronizarse con `prompts/`.

| ID plantilla | Uso |
|---|---|
| `ENGEL - ACUERDO TRANSACCIONAL - PAGO CANTIDAD` | Borrador de acuerdo transaccional. |
| `ACUERDO TRANSACCIONAL - ENGEL ACREEDOR` | Plantilla DocuSign. |
| `ENGEL - SINIESTRO - COMUNICADO - EXTRAJUDICIAL` | Comunicación a corredor (AON / HISCOX). |
| `ADMINISTRACION - NUMERO AUTOS ADMISION - ORDINARIO VERBAL` | Notificación admisión a trámite. |
| `FG - PROCURADOR - ENVIO DEMANDA` | Envío de demanda a procurador. |
| `FG - PROCURADOR - CONTROL NOTIFICACION CONTRARIO` | Control. |
| `FG - PROCURADOR - CONTROL ADMISION DEMANDA - DICTADO SENTENCIA` | Control. |
| `FG - CONTRARIO - ADMISION` | Comunicación a contraria de admisión. |
| `ADMINISTRACION - TESTIGO CITACION - JUDICIAL` | Cédulas de citación. |
| `ENGEL - CLIENTE - JUDICIAL - COBRO` | Cobros derivados de consignaciones. |
| `ABOGADO PRINCIPAL - PRESENTADA DEMANDA MONITORIO - JUDICAL` | Hito 1 monitorio. |
| `ENGEL - ADMINISTRACION - NUMERO AUTOS - JUDICIAL` | Hito 2 monitorio. |
| `ADMINISTRACION - ADMISIÓN DEMANDA MONITORIO + REQUERMIENTO - JUDICAL` | Hito 3 monitorio. |
| `ABOGADO PRINCIPAL - RESULTADO DEMANDA` | Hito 4 monitorio. |
| `ENGEL - ABOGADO - JUDICIAL - SEÑALADA AUDIENCIA PREVIA` | Comunicación señalamiento. |
| `ENGEL - ABOGADO - JUDICIAL - CELEBRADA AUDIENCIA PREVIA` | Tras audiencia previa. |
| `ENGEL - ABOGADO PRINCIPAL- CONTESTACION DEMANDA` | Análisis contestación. |
| `ENGEL - JUDICIAL - CELEBRADO JUICIO` | Tras juicio. |
| `ENGEL - RESPONSABLE - SENTENCIA` | Notificación sentencia. |
| `ENGEL - ABOGADO PRINCIPAL - DEMANDA EJECUTIVA - JUDICAL` | Demanda ejecución. |
| `ENGEL - ADMINISTRACION - AUTO DESPACHANDO EJECUCION - JUDICAL` | Auto ejecución. |
| `ENGEL - ABOGADO PRINCIPAL - ARCHIVO FALTA ACTIVOS` | Archivo por insolvencia. |
| `ESCR VISTA TELEMÁTICA` | Solicitud asistencia telemática del letrado. |

## Actuaciones predefinidas más comunes (manual L1014-1080)

```
TJ - PREPARAR DEMANDA JUICIO MONITORIO
TJ - PREPARAR DEMANDA JUICIO ORDINARIO
TJ - PREPARAR DEMANDA JUICIO VERBAL
TJ - PREPARAR DILIGENCIAS PRELIMINARES
TJ - PREPARAR RECURSO APELACION
TJ - PREPARAR MINUTA AUDIENCIA PREVIA
TJ - PREPARAR INFORME VIABILIDAD RECURSO APELACION
TJ - PREPARAR TASACION COSTAS
TJ - PREPARAR LIQUIDACION INTERESES
TJ - REVISAR Y FIRMAR TASACION COSTAS
TJ - REVISAR Y FIRMAR LIQUIDACION INTERESES
TJ - SEÑALAMIENTO VISTA - CIUDAD - WEBEX/PRESENCIAL - SALA Nº XXX
TJ - REVISAR Y APROBAR ACUERDO TRANSACCIONAL
TJ - PREPARAR BUROFAX + COMPLETAR INFORME VIABILIDAD
TA - SUBIR DOCUMENTO - XXXXXX
TA - ENVIAR DEMANDA + FACTURAR
TA - CONTROL PRESENTACIÓN
TA - CONTROL ADMISIÓN
TA - CONTROL NOTIFICACION DEMANDA CONTRARIO
TA - IMPULSO - CONTROL
TA - IMPULSO - CONTROL CUMPLIMIENTO VOLUNTARIO
TA - SOLICITUD EMBARGOS PERIODICA
TA - FACTURAR AUDIENCIA PREVIA + SOLICITAR GRABACIÓN
TA - RECLAMAR GRABACION AUDIENCIA PREVIA
TA - CONTROL GRABACION VISTA
TA - CONTROL DICTADO SENTENCIA
ADM - EXTRAJUDICIAL - ENVIAR ACUERDO TRANSACCIONAL
ADM - EXTRAJUDICIAL - PREPARAR PROPUESTA + DUPLICAR/COMPLETAR EXPEDIENTE + CREAR ACTUACION
ABOGADO - EXTRAJUDICIAL - REVISION VIABILIDAD
```

Regla del manual: **no se crean actuaciones predefinidas nuevas**; si no
hay exacta, se usa la que más se asemeje.
