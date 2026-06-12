---
name: engel-volkers
description: "Skill de cliente para los asuntos del despacho con Engel & Völkers en España y Andorra (las sociedades EV MMC SPAIN, S.L.U. y ENGEL & VÖLKERS SPAIN, S.L.U.). Aporta identidad y estructura societaria del cliente, mapa de Market Centers y equipos, tipologías oficiales del CRM, criterios de redacción y trato, y reglas operativas del despacho para estos asuntos. Actívala SIEMPRE que el asunto sea de este cliente o se mencione, en cualquier grafía, «Engel & Völkers», «Engel&Völkers», «Engel y Völkers», «Engel Völkers», «engel volkers» (también en minúsculas o sin diéresis), «E&V», «EV MMC», «MMC Spain» o «Engel & Völkers Spain» — aunque el usuario no pida explícitamente el contexto de cliente; inclúyase el caso defensivo en que se demanda A E&V por actos u omisiones de un franquiciado. NO la actives por términos inmobiliarios genéricos sin este cliente («agencia inmobiliaria», «mediación inmobiliaria», otra agencia o promotora), NI cuando el despacho defienda directamente a un FRANQUICIADO de la marca demandado por su propia actuación (E&V no asesora a sus franquiciados, que tienen letrados propios), NI ante falsos amigos ajenos al cliente como «Friedrich Engels» o el «Völkerrecht»/Derecho internacional. No genera escritos ni aporta jurisprudencia: combínala con escritos-judiciales, preparacion-litigio-civil y preparacion-juicio-oral, que consumen el contexto de cliente que esta skill aporta."
version: 1.0
status: vigente
---

# Engel & Völkers — Skill de cliente

Esta skill aporta **exclusivamente el contexto del cliente** Engel & Völkers para el despacho de Nikolai Tyukhay (civil / inmobiliario, Barcelona). No produce escritos, no contiene jurisprudencia ni ejes argumentales, y no fija la mecánica de generación de `.docx`. Esas responsabilidades viven en las skills genéricas del despacho:

- `preparacion-litigio-civil` — fase estratégica previa (estructura del expediente, decisiones, prueba).
- `escritos-judiciales` — generación del `.docx` con formato Sala 1.ª TS.
- `preparacion-juicio-oral` — soporte para el acto de juicio tras la audiencia previa.

Cuando trabajes un asunto de E&V, activa esta skill **en cadena** con la genérica que corresponda: esta da el «quién es el cliente y cómo se le trata»; la genérica da el «cómo se redacta».

## Cuándo se activa

Ante el nombre del cliente o cualquiera de sus variantes de grafía: «E&V», «Engel & Völkers», «Engel&Völkers», «Engel y Völkers», «Engel Völkers», «engel volkers» (también en minúsculas o sin diéresis), «EV MMC», «MMC Spain», «Engel & Völkers Spain». Inclúyase el caso **defensivo** en que se demanda **a E&V** por actos u omisiones de un franquiciado: ahí el cliente es la matriz (→ ID 27) y la skill **sí** aplica.

**No** se activa:

- Por términos inmobiliarios **genéricos** sin este cliente: «agencia inmobiliaria», «mediación inmobiliaria», u otra agencia o promotora — pertenecen a una eventual skill de materia, no a esta skill de cliente.
- Cuando el despacho defiende **directamente a un franquiciado** demandado por su propia actuación: E&V **no asesora** a sus franquiciados, que tienen letrados propios (ver §2). El asunto no es de este cliente, aunque aparezca el nombre de la marca.
- Ante **falsos amigos** ajenos al cliente: «Friedrich Engels» (filosofía/teoría política) o el «Völkerrecht» / Derecho internacional público.

---

## 1. Identidad del cliente

Engel & Völkers es una agencia inmobiliaria internacional de gama alta que opera en España bajo modelo de franquicias y oficinas propias (*Market Centers*). El despacho trabaja para el grupo en **España y Andorra**. Quedan fuera del alcance EV MMC Portugal y EV Finance Spain.

Dos sociedades del grupo están dentro del alcance del despacho:

| Clave interna | Razón social | NIF | ID CRM | Rol en los asuntos |
|---|---|---|---|---|
| `EV_MMC_SPAIN` | EV MMC SPAIN, S.L.U. | B65824054 | 2 | Sociedad operativa que firma los encargos. **Cliente por defecto** en todos los asuntos de honorarios (actores y defensivos). |
| `ENGEL_VOLKERS_SPAIN` | ENGEL & VÖLKERS SPAIN, S.L.U. | B65708091 | 27 | Sociedad matriz del grupo en España. **Siempre en posición defensiva** (en 15 años no ha sido actora). Mayoría de asuntos: demandas o denuncias derivadas de actos u omisiones de franquiciados. |

Notas de asignación de sociedad:

- Por defecto, todo asunto de honorarios se vincula a **EV MMC SPAIN (ID 2)**.
- **ENGEL & VÖLKERS SPAIN (ID 27)** entra solo en clave defensiva, en asuntos transversales de la matriz. Si se demanda **directamente al franquiciado**, E&V Spain **no asesora** (el franquiciado tiene sus propios letrados).
- El ID 73 es un duplicado de EV MMC SPAIN en el CRM: **no usar nunca**.

Domicilio operativo actual de ambas: **Avenida Diagonal 640, Barcelona**.

Régimen jurídico de la actividad: **agencia inmobiliaria no colegiada** (libertad de ejercicio conforme al RD-Ley 4/2000; STC 330/1994). Relevante para encuadrar la naturaleza del contrato de mediación y la legitimación.

A falta de política específica de E&V sobre proveedor cloud y residencia de datos en el EEE, el material se trata bajo el régimen general de confidencialidad y protección de datos del despacho.

### 1.1 Estructura territorial — Market Centers y equipos

La actividad se organiza por *Market Centers* (oficinas) y, dentro de cada uno, por **equipos** identificados con un código `<plaza><segmento><n>`:

- **Plaza:** `Ba` Barcelona · `Ma` Madrid · `SS` San Sebastián · `Se` Sevilla · `Bi` Bilbao · `Sa` Santander.
- **Segmento:** `RR` Residential Rentals · `RS` Residential Sales · `CR` Commercial Rentals · `CS` Commercial Sales · `DP`/`PD` equipo pendiente de asignar.
- **`n`:** número de equipo.

Catálogo de equipos por plaza (fuente: `core/ciudades.py` de FeesDefender; contexto extrajudicial):

| Plaza | Equipos |
|---|---|
| Barcelona (`Ba`) | RR1, RR2, RR3, RR4, RR10 · RS1–RS12 · CR1, CR2, CR10 · CS1, CS10 · DP1 |
| Madrid (`Ma`) | RR1, RR2, RR3 · RS1–RS15 · PD1 |
| Bilbao (`Bi`) | RS1, RS2 |
| San Sebastián (`SS`) | RR1, RS1 |
| Santander (`Sa`) | RS1 |
| Sevilla (`Se`) | RS1, RS6 |

Cada equipo tiene además su tag CRM (rojo) propio en los dos contextos del gestor documental (extrajudicial y judicial). Identificar el equipo del expediente permite localizar al consultor y al Team Leader intervinientes.

*Nota:* el catálogo canónico del CRM incluye una séptima plaza, **Valencia (`Va`)**, no listada arriba por estar fuera del foco actual del despacho. Incorporarla si entra un asunto de esa plaza.

---

## 2. Relación con el despacho

Cliente corporativo recurrente, con volumen estable. Existe un **contrato marco vigente** entre el despacho y las dos sociedades (anexo en vigor desde el 01/01/2025), del que cuelgan **propuestas de gasto individuales por asunto** («anexos»). *Las tarifas, mínimos, descuentos, honorarios de éxito y comisiones no se documentan en esta skill: son datos confidenciales del acuerdo bilateral y viven en la memoria privada de Nikolai.*

El despacho actúa como **letrado externo de defensa prejudicial y judicial** de E&V. No depende del departamento legal interno: la relación con el Head of Legal Iberia es **horizontal, entre compañeros con funciones delimitadas**, no de encargo ni supervisión.

Reparto de funciones e interlocución (**solo cargos, sin nombres**):

- **Defensa prejudicial y judicial** (litigio, reclamación de honorarios, contestaciones) → el despacho, con dirección técnica propia de los asuntos litigiosos.
- **Head of Legal Iberia** → compliance y gestión del equipo legal interno de E&V. Coordinación horizontal con el despacho **solo en su ámbito**; no encarga ni revisa los litigios.
- **Reporting financiero y aprobación de gasto** → CFO.
- **Comercial implicado en cada expediente** → el *Market Center*: Sales Director, Director de Zona, Team Leader, consultor captador, consultor buscador, Team Assistant.
- **Operativa y franquicias** → COO / Head of Operations & Franchises.
- **Recursos humanos y consultores comerciales** → P&C / Recruiting.

Las propuestas de gasto se aprueban de forma periódica en una **reunión Jurídico-Finanzas**.

Expectativas de servicio: es una **marca premium**. Comunicaciones especialmente cuidadas y de registro corporativo; escritos con formato Sala 1.ª TS.

---

## 3. Tipologías oficiales (CRM FeesDefender)

Taxonomía canónica del CRM (fuente: `core/config.py` de FeesDefender). Para cada tipología: **clave interna · tag CRM · supuesto fáctico (nota oficial) · cuestionario de viabilidad sí/no · vía habitual**.

La fundamentación jurídica por tipología (jurisprudencia, ejes argumentales) **no vive aquí** — la aporta la skill de materia / las skills genéricas en el momento de redactar el escrito.

El **cuestionario de viabilidad** referido es el protocolo de FeesDefender (`data/_plantillas/cuestionario_viabilidad.yaml`), aplicable a siete tipologías (las seis negativas/vuelta/exclusiva actoras y la defensiva de responsabilidad profesional). Estructura el material probatorio del expediente antes de la decisión del jurista.

### 3.1 Actoras (E&V reclama) — 7

| Clave | Tag CRM | Supuesto fáctico | Cuestionario | Vía habitual |
|---|---|---|---|---|
| `BAD_DEBT` | `BAD DEBT` | Impago de factura de honorarios de intermediación. | No | Declarativo (verbal ≤ 15.000 € / ordinario > 15.000 €). Sin monitorio. |
| `NEGATIVA_OFERTA` | `NEGATIVA OFERTA` | El cliente se niega a aceptar la oferta en las condiciones fijadas en el encargo. | Sí | Requerimiento extrajudicial → verbal / ordinario. |
| `NEGATIVA_ARRAS` | `NEGATIVA ARRAS` | El cliente se niega a firmar el contrato privado (arras) tras aceptar la oferta. | Sí | Requerimiento extrajudicial → verbal / ordinario. |
| `NEGATIVA_ESCRITURA` | `NEGATIVA ESCRITURA` | El cliente se niega a firmar la escritura tras firmar el contrato privado. | Sí | Requerimiento extrajudicial → verbal / ordinario. |
| `NEGATIVA_CONTRATO_ARRENDAMIENTO` | `NEGATIVA CONTRATO ARRENDAMIENTO` | El cliente se niega a formalizar el contrato de arrendamiento tras la oferta aceptada. | Sí | Requerimiento → verbal / ordinario. **Nota:** en la práctica no se materializa, porque el arrendatario adelanta los honorarios antes de pasar la oferta al propietario. |
| `VUELTA` | `VUELTA` | El cliente se aprovecha de la gestión de la agencia cerrando la operación sin ella. | Sí | **Diligencias preliminares siempre como paso previo**; luego ordinario (preferido aunque la cuantía sea menor, por la complejidad probatoria). |
| `INCUMPLIMIENTO_EXCLUSIVA` | `INCUMPLIMIENTO EXCLUSIVA` | El cliente vendedor incumple el pacto de exclusividad del encargo. | Sí | Requerimiento extrajudicial → verbal / ordinario. |

### 3.2 Defensivas (E&V es demandada) — 4

En todas: **siempre se opone**.

| Clave | Tag CRM | Supuesto fáctico | Cuestionario | Vía habitual |
|---|---|---|---|---|
| `RESPONSABILIDAD_PROFESIONAL` | `RESPONSABILIDAD PROFESIONAL` | El cliente reclama daños y perjuicios por presunta negligencia de la agencia. | Sí | Contestación / oposición. |
| `DEVOLUCION_RESERVA` | `DEVOLUCION RESERVA` | El comprador o arrendatario reclama la devolución de la reserva o compromiso de seriedad. | No | Contestación / oposición. |
| `LAU_20` | `LAU 20` | El arrendatario reclama la devolución de honorarios al amparo del art. 20.1 LAU. | No | Contestación / oposición. **Nota:** tras la Ley 12/2023, el art. 20.1 LAU es aplicable tanto a arrendadores persona física como persona jurídica. Régimen transitorio, caso a caso. |
| `DEVOLUCION_HONORARIOS` | `DEVOLUCION HONORARIOS` | El cliente (comprador, vendedor o arrendatario fuera del art. 20.1 LAU) reclama la devolución de los honorarios pagados. Cajón general: compraventa, intermediación mercantil y encargos no residenciales. | No | Contestación / oposición. |

### 3.3 Otros — 1

| Clave | Tag CRM | Supuesto fáctico | Cuestionario | Vía habitual |
|---|---|---|---|---|
| `OTROS` | `OTROS` | Caso genérico de E&V no relacionado con defensa o reclamación de honorarios (consultas contractuales, requerimientos varios, mediaciones, dudas legales, **propiedad horizontal residual**). | No | Sin posición procesal fija — la decide el caso. La sociedad cliente puede ser EV MMC (ID 2) o, según el asunto, ENGEL & VÖLKERS SPAIN (ID 27). |

---

## 4. Criterios de redacción y trato

- **Lengua.** Castellano en escritos procesales y en comunicaciones formales con la sede. **Ruso** en comunicaciones con clientes finales rusos o de la ex-URSS cuando el despacho actúa frente al cliente final en nombre de E&V (salvo indicación contraria).
- **Formato de escritos.** Criterios formales de la Sala 1.ª TS: Times New Roman 12 pt; notas al pie y citas 10 pt (cursiva, justificadas, sangría izquierda 1 cm); márgenes 2,5 cm; interlineado 1,5; espaciado anterior 6 pt / posterior 0; párrafos numerados; jerarquía 1. → 1.1. → 1.1.1.; máximo 25 páginas. (La mecánica concreta del `.docx` la implementa `escritos-judiciales`.)
- **Registro hacia E&V.** Corporativo, cuidado, acorde a marca premium.
- **Memo interno vs. cuerpo procesal.** Cuando se circule un borrador a E&V, los puntos débiles y riesgos del asunto van **siempre en una sección de memo interno separada** del cuerpo del escrito, nunca dentro del escrito que verá la contraparte o el juzgado.
- **Anti-deanonimización.** En versiones anonimizadas o destinadas a un tercero, no describir la marca ni rasgos que la identifiquen: usar «mi representada». El pipeline de FeesDefender pre-carga variantes OCR de la denominación del cliente para mapearlas a una etiqueta canónica antes de anonimizar.

---

## 5. Decisiones operativas del despacho para asuntos E&V

- **Umbral mínimo para reclamar judicialmente:** 2.500 € (IVA incluido), en todas las tipologías actoras.
- **Sin monitorio.** Siempre declarativo (incluida `BAD_DEBT`).
- **`VUELTA`:** diligencias preliminares siempre como paso previo (no se fija precepto LEC en la skill).
- **Frontera verbal / ordinario:** 15.000 € (regla general LEC).
- **Transacción:** sin umbral. Siempre se transa si la contraparte tiene voluntad. **Un buen acuerdo = pago a la vista del 50 % de lo reclamado.** Antes de escalar a la vía judicial, priorizar siempre los medios alternativos (negociación, mediación, conciliación).
- **Defensivas:** siempre se opone.

---

## 6. Documentación contractual habitual de E&V

Documentos tipo que aparecen recurrentemente en los expedientes (útiles para identificar prueba y encuadrar la operación):

1. **Hoja de encargo de venta** (en su modalidad exclusiva o no exclusiva).
2. **Oferta de Compra de Inmueble** — la cláusula 2 fija el rol de E&V como **mera intermediaria** y excluye el asesoramiento jurídico / fiscal.
3. **Reconocimiento de Gestión y Honorarios de Agencia** — devengo típico 50 % a la firma de arras + 50 % a escritura; devengo del 100 % por causa imputable al comprador.
4. **Dossier publicitario** — incluye la advertencia de acudir a un técnico independiente.
5. **Contrato Privado de Compraventa con Entrega de Arras Penitenciales.**

En operaciones de Madrid aparece además el **compromiso de seriedad de oferta**, documento propio de ese flujo. *(Los flujos documentales por plaza pueden sofisticarse en versiones futuras.)*

Terminología de partes en estas operaciones: **propietario** (quien ofrece el bien) y **buscador** (quien lo busca) — cubre compraventa, arrendamiento y traspaso. No usar «vendedor / comprador».

---

## 7. Estructura interna de carpetas y nomenclatura

Convención estándar del expediente (fuente: `core/config.py`, `CASO_SUBDIRS`):

```
00_Input · 01_Procesado · 02_Analisis · 03_Decision · 04_Output predemanda
05_Procedimiento · 06_Anonimizado · 07_AI cowork · 90_Notas personales
```

`90_Notas personales` es zona reservada del abogado: ningún proceso automatizado la lee ni la escribe.

Dentro de `00_Input`, las fuentes documentales se numeran: `01_Drive EV` (carpeta `W-XXXXXX` del Drive del cliente), `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`, `06_Entrevistas`.

Otras convenciones:

- **Referencia de expediente:** patrón `W-XXXXXX` (Drive E&V).
- **Nomenclatura de documental aportada:** `D XX - nombre.pdf`.
- **Conversión a PDF:** los `.eml` y las exportaciones de WhatsApp se convierten a PDF antes de aportarse. La **multimedia** (audio, vídeo) solo se referencia; no se aporta.
- **Taxonomía documental E&V:** `00. FOTOS`, `01. ACTIVACIÓN`, `03. OFERTAS`, `04. ARRAS - ARRENDAMIENTOS`, `05. FACTURACIÓN - FINANZAS`, `06. PBC`, `07. RECLAMACIONES`, `08. PENDIENTE DE CLASIFICAR`.

---

## 8. Telemetría y feedback (Fase 1 del plan de evolución)

Esta skill registra su propio uso para alimentar el plan de mejora del despacho (ver `EVOLUCION.md`). Es **best-effort y no debe entorpecer el trabajo**: si el registro falla, continúa con el asunto sin bloquear. Como es una skill de **contexto** (no genera documentos), el registro lo hace el propio asistente, no un script.

**Al usar esta skill en un asunto real**, añade una línea a `logs/uso.jsonl` dentro de la carpeta de esta skill. En PowerShell, rellenando los valores del asunto:

```powershell
$dir = "C:\Users\tnm33\despacho-skills\engel-volkers"   # ajusta si la skill está instalada en otra ruta
if (-not (Test-Path "$dir\logs")) { New-Item -ItemType Directory "$dir\logs" -Force | Out-Null }
$rec = @{ ts=[DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"); skill="engel-volkers";
          ref="W-XXXXXX"; sociedad="EV_MMC_SPAIN"; tipologia="BAD_DEBT"; posicion="actora";
          skill_encadenada="escritos-judiciales" } | ConvertTo-Json -Compress
Add-Content "$dir\logs\uso.jsonl" -Value $rec -Encoding UTF8
```

Valores admitidos: `sociedad` ∈ {`EV_MMC_SPAIN`, `ENGEL_VOLKERS_SPAIN`}; `tipologia` = clave del §3 (`BAD_DEBT`, `NEGATIVA_OFERTA`, … `LAU_20`, `OTROS`); `posicion` ∈ {`actora`, `defensiva`}; `skill_encadenada` = la genérica usada (`escritos-judiciales` / `preparacion-litigio-civil` / `preparacion-juicio-oral`) o `null`.

**Al cerrar el trabajo del asunto**, ofrece al letrado el checklist post (`templates/checklist_post.md`) — una sola pregunta — y guarda la respuesta en `logs/<ref>_post.jsonl`. No insistas si declina.

El esquema completo está en `logs/README.md`. Estos datos contienen referencias reales de asuntos y **no se versionan** (la carpeta de la skill está en `.gitignore`).

---

## Lo que esta skill deliberadamente NO contiene

- Tarifas, mínimos, descuentos, honorarios de éxito o porcentajes de comisión (memoria privada).
- Nombres personales de directivos o interlocutores de E&V (solo cargos).
- Jurisprudencia, doctrina o ejes argumentales por tipología (skills genéricas / de materia).
- Mecánica de generación de `.docx` ni formato general de escritos (`escritos-judiciales`).
- Plantillas de demandas, contestaciones, recursos o interrogatorios (skills genéricas).
- Política de costas en defensivas (irrelevante operativamente).
