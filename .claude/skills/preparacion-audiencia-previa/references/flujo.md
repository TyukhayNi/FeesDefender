# Flujo operativo — preparación de la audiencia previa

Source-locked en todo momento (convivencia con `verificacion-anclada-fuente`). No inventar; anclar
cada hecho, cita e importe a su fuente del expediente.

## Fase 0 — Reconocimiento y contexto

Primero determina el **modo**, porque condiciona terminología, ubicación de outputs y registro:

- **Modo FeesDefender / E&V**: existe `00_Input/_caso.md` (caso de Engel & Völkers). Lee de él
  `tipo_caso`, partes, `referencia_crm`, `organo`, `cuantia`, `estado` (campos a `null` → complétalos
  desde la documental). Estructura: `00_Input`, …, `05_Procedimiento`, …, `90_Notas personales`.
  Terminología propietario/buscador; patrones E&V vía `engel-volkers`.
- **Modo civil genérico**: cualquier otro ordinario civil, sin estructura FeesDefender. **Pregunta al
  letrado** dónde están la demanda y la contestación, los datos de cabecera (órgano, autos, cuantía,
  partes) y **dónde guardar** los `.docx`. Terminología **neutra** (nombres reales / actor-demandado),
  sin patrones E&V.

En ambos modos, determina la **perspectiva** (actora/demandada) — ver `actora_defensiva.md`.

## Fase 1 — Lectura procesal y fijación de hechos

Lee y contrasta:

- **Demanda** y **contestación** (y reconvención / alegación de nulidad si las hay).
- Autos de admisión, **providencia de señalamiento** (de Sudespacho sincronizado en `00_Input/`).
- `00_Input/`: encargo, exposé, report, nota simple, escritura, chats (`02_Whatsapp`), correos
  (`03_Email`), CRM (`05_CRM`).
- `06_Entrevistas/`: transcripción de la call de viabilidad/entrevista a consultores — de aquí salen
  los **testigos** y los hechos a acreditar. **No** la trates como prueba: es trabajo interno; su valor
  es identificar la testifical y la documental, y detectar admisiones internas peligrosas.
- **Nunca** `90_Notas personales/`.

Construye los dos cuadros (ver `formato_minuta.md`, "Regla de fijación de hechos"):

- **No controvertidos**: lo admitido o no negado por ambas partes, anclado a documento.
- **Controvertidos**: un hecho por fila, tesis de cada parte y prueba de EV.

## Fase 2 — Confirmación de hechos con el letrado

Antes de generar nada, presenta los dos cuadros y la **causa de pedir**, y señala:

- **Flancos / admisiones internas peligrosas** (p. ej. en la entrevista se reconoció algo que
  perjudica): no se vierten al proceso, pero el letrado debe conocerlos.
- **Lagunas documentales** (p. ej. base de cálculo sin soporte escrito).
- **Coherencia con escritos propios** (regla de oro 5). Patrón típico: si en nuestra contestación
  admitimos que una cláusula "no fue negociada individualmente", **no** lo neguemos ahora; usa la
  prueba de que el cliente negoció *otras* cláusulas concretas por la **vía de la transparencia**
  (conocimiento real), no negando la predisposición.

Espera la confirmación o ajustes del letrado sobre los hechos antes de pasar a la prueba.

## Fase 3 — Propuesta de prueba (por chat; espera visto bueno)

La proposición de prueba no se vuelca al escrito sin aprobación: cada testigo tiene coste y estrategia,
y el letrado decide a quién cita. **Presenta por chat una tabla con la prueba propuesta y espera su
confirmación o ajustes** antes de generar la minuta y la solicitud:

| Medio | Qué acredita (hecho controvertido) | Fuente de los datos de citación | Riesgo / observación |
|---|---|---|---|

- Cubre **documental**, **más documental** (con la alegación complementaria que la hace pertinente),
  **testifical** (con quién, y por qué), **interrogatorio** de la parte contraria y **oficios**.
- Marca riesgos (p. ej. un testigo de memoria débil o doble filo) y lagunas en los datos de citación
  (`[pendiente: dato de citación]`).
- La generación de la minuta (bloque 7) y de la solicitud de prueba **queda condicionada** a este
  visto bueno. Solo tras la confirmación se componen los JSON y se generan los `.docx`.

## Fase 4 — Señalamiento

Toma fecha y sala de la AP de la **providencia/DIOR de señalamiento** del expediente Sudespacho
sincronizado en `00_Input/`. Si no consta, **pregunta** al letrado; no lo inventes.

## Fase 5 — Generar la minuta

1. Compón el JSON de datos según `formato_minuta.md` (la prueba del bloque 7 = la aprobada en Fase 3).
2. `python scripts/gen_minuta.py datos.json "05_Procedimiento/MINUTA_AP_<REF>.docx"`.
3. Registra el uso (`scripts/registrar_uso.py`).

## Fase 6 — Generar la solicitud de prueba

Escrito procesal generado con `scripts/gen_solicitud.py` (formato exacto del despacho; ver
`solicitud_prueba.md`), con la prueba aprobada en Fase 3:

`python scripts/gen_solicitud.py datos.json "05_Procedimiento/SOLICITUD_PRUEBA_<REF>.docx"`

## Fase 7 — Guardar, registrar y validar

- **Modo FeesDefender**: guarda en `05_Procedimiento/` y registra ambos outputs:
  `python scripts/registrar_outputs.py <case_dir> outputs.json` (manifiesto `05_Procedimiento/_index.md`
  + wikilinks en `00_Input/_caso.md`). Ver `manifiesto_y_registro.md`.
- **Modo civil genérico**: guarda los `.docx` en la carpeta indicada por el letrado. **No hay registro
  de intake** (no existe `_caso.md`).
- **Validación source-locked**: cada hecho, cita, importe y referencia documental tiene fuente;
  jurisprudencia verificada en CENDOJ (`cendoj-descarga`); terminología propietario/buscador; NIG no
  usado; no se ha contradicho ningún escrito propio.
- Si el `.docx` destino está abierto (Word lo bloquea), guarda con sufijo `_v2` y avisa.

## Tras el acto (mejora continua)

Rellena `templates/checklist_post_ap.md` con lo que fijó realmente el juez, la prueba admitida/
inadmitida y lo no previsto → `logs/<ref>_post.jsonl`. La **transcripción del CGPJ del acto prevalece**
sobre la minuta interna si difieren.
