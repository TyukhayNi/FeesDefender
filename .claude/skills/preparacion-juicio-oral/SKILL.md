---
name: preparacion-juicio-oral
version: "1.0"
description: Preparación del acto de juicio civil español tras la audiencia previa. Produce herramientas de soporte interno para el letrado (no escritos procesales): documento único de conclusiones (con hechos no controvertidos y controvertidos en tablas, citas literales de AP con timestamps, conclusiones jurídicas y petitum) e interrogatorios por testigo (versión letrado completa + versión testigo orientativa cuando aplica). Se usa cuando el usuario dice «preparar juicio», «preparar testifical», «cuadro de hechos», «hechos controvertidos», «interrogatorio testigo», «banco de preguntas», «esquema de conclusiones», «el juicio es mañana», o cuando menciona referencias internas (W-XXXXX, REF-XXXX) en un asunto con audiencia previa ya celebrada. No redacta demandas, contestaciones ni escritos de trámite; se encadena con `escritos-judiciales` y con la skill de cliente que corresponda. Predecesora natural: `preparacion-litigio-civil`.
---

# Preparación del acto de juicio oral civil

## Posicionamiento

Skill metodológica para la fase posterior a la audiencia previa. Todas las salidas son **herramientas de soporte interno del letrado**, no escritos procesales que vea el juez ni la otra parte. Excepción: los interrogatorios admiten una versión testigo orientativa que se envía a testigos colaborativos para su preparación.

Outputs por defecto:

- `CONCLUSIONES_[REF].docx` — documento único: hechos no controvertidos (tabla) + hechos controvertidos (tabla) + conclusiones (bullets) + petitum.
- `PREGUNTAS_[Testigo]_letrado.docx` — versión completa con preguntas, RE/RD/Nota y caja de anticipación.
- `PREGUNTAS_[Testigo]_testigo.docx` — versión testigo (cuando aplica): preguntas + disclaimer.
- `ORDEN_VISTA_[REF].docx` — **obligatorio**: guion de intervención en sala con estructura canónica (ver Decisión 13). Se genera siempre, no bajo solicitud.

Bajo solicitud: `CUADRO_HECHOS_[REF].docx`.

En modo expediente estructurado (existe `00_Input/_caso.md`), estos `.docx` se guardan en `05_Procedimiento/` y se registran en el intake con `scripts/registrar_outputs.py` (detalle en [flujo.md](flujo.md), «Guardado y registro»). En modo ad-hoc no hay registro.

Convivencia: `escritos-judiciales`, `preparacion-litigio-civil`, skills de cliente. **`verificacion-anclada-fuente` es convivencia obligatoria** en la fijación de hechos (Fase 1) y en la validación (Fase 6): véase Decisión 14.

**Flujo operativo:** el procedimiento paso a paso (Fases 0–6: reconocimiento del expediente → fijación de hechos → confirmación → conclusiones → interrogatorios → orden de vista → validación) está en [flujo.md](flujo.md). Léelo al iniciar la preparación de un asunto, antes de generar nada.

## Decisiones metodológicas codificadas

1. **Modo soporte letrado por defecto**. Formato Arial 12 pt, interlineado 1,25, márgenes asimétricos A4 (2,5/2/2,5/3,5 cm con margen izquierdo amplio para anotación a mano). Encabezados de bloque sombreados con borde inferior; tablas con cabecera gris 25 % y filas alternas gris 5 %; etiquetas RE/RD/Nota en 10 pt cursiva gris oscuro; citas literales de AP en 9 pt cursiva gris oscuro. Modo formal Sala 1ª TS disponible como subset alternativo cuando el output sí va a presentarse al juzgado.

2. **Fijación literal del juez por encima de la minuta interna**. La transcripción del CGPJ del acto de la AP prevalece sobre cualquier nota de trabajo. Si la minuta y la transcripción difieren, se sigue la transcripción.

3. **Hechos controvertidos: uno o varios**. Dos modos: «juez activo» (recoger fijación literal) y «partes» (formulación argumentativa por la actora cuando el juez no concretó).

4. **Citas literales de AP con timestamps**. Cada hecho admite array opcional `cita_ap[]` con objetos `{timestamp, atribucion, texto}`. Atribuciones tipificadas: `Magistrado` | `Letrado actora` | `Letrado demandada`. Sin nombres personales (no aportan operativamente). Las citas se renderizan en cursiva 9 pt gris oscuro debajo del hecho dentro de la celda.

5. **Documento único de conclusiones**. Cuatro secciones: I. Hechos no controvertidos (tabla); II. Hechos controvertidos (tabla); III. Conclusiones (bullets en mayúsculas negrita + 2-3 líneas con sangría); IV. Petitum (líneas cortas).

6. **Un archivo .docx por testigo**. Cada testigo lleva su propio archivo. En sala el letrado coge el del testigo en turno.

7. **Plantilla por rol procesal**: `directo` (RE+Nota), `cruzado` (RE+RD+Nota), `neutro` (mixto), `problematico` (con bloques de contención).

8. **Doble versión por testigo**. Siempre se genera `[Testigo]_letrado.docx`. La versión `_testigo.docx` se genera por defecto en `directo` y `neutro`; no se genera en `cruzado` ni `problematico` (con sobrescritura mediante flag `generar_version_testigo`). La versión testigo incluye disclaimer estándar y solo preguntas.

9. **Disclaimer estándar para versión testigo**: «Las preguntas que figuran a continuación son orientativas y se le facilitan únicamente para que pueda prepararse con tranquilidad al acto del juicio. No tiene obligación de contestarlas en los términos en que aquí se anticipan: usted declarará libre y exclusivamente conforme a su conocimiento personal de los hechos, con la obligación de decir verdad que le impone el artículo 365 LEC. Si alguna pregunta no la entiende, no recuerda la respuesta exacta o no le consta, así lo manifestará al tribunal. El presente documento es confidencial. Se le ruega no difundirlo ni compartirlo con terceros.»

10. **Mezcla abierta/cerrada en testifical**. La forma «Diga si es cierto que» se reserva para anclajes documentales y bloques nucleares. Para reconstrucción cronológica, preguntas abiertas. Algunos jueces se irritan con interrogatorios íntegramente cerrados.

11. **Checkbox antes del nº de pregunta** (`☐ N. ...`) para que el letrado tache en sala lo cubierto.

12. **Anticipación a repreguntas como sección obligatoria** del interrogatorio del letrado. En caja con borde y sombreado tenue. Solo se lee si el adversario abre el frente.

13. **Orden de vista obligatoria, con estructura canónica**. `ORDEN_VISTA_[REF].docx` se genera siempre (output por defecto, no bajo solicitud). Su estructura canónica tiene siete apartados, ninguno de los cuales se omite; si un apartado no aplica a este asunto, no se borra: se deja constancia expresa («No aplica» o «Sin elementos identificados») para que el letrado vea en sala que la cuestión se consideró y se descartó, no que se olvidó. Apartados: (1) **datos del acto** — procedimiento, órgano, fecha y sala; (2) **documentos a tener a mano** — referencias documentales listas para exhibición rápida; (3) **orden de testigos** — con rol procesal y tiempo estimado por testigo; (4) **protestas previsibles** — para formularlas en el momento y dejarlas a efectos de recurso; (5) **riesgos / flancos** — cada uno con su respuesta preparada y localizada; (6) **conclusiones orales en bullets** — guion de la exposición final; (7) **recordatorios procesales** — p. ej. solicitar conclusiones por escrito, diligencias finales. La razón del orden de testigos se documenta junto al apartado (3).

14. **Anclaje a fuente obligatorio (modo *source-locked*)**. La fijación de hechos (Fase 1) y la validación (Fase 6) se ejecutan en convivencia con `verificacion-anclada-fuente`: cada hecho, cada cita de la AP, cada importe y cada referencia documental queda anclado a fuente verificable del expediente, **sin inferencias** — está prohibido afirmar parentescos, relaciones, intenciones o conocimiento que el documento no sostenga literalmente. Si la fuente no lo dice, no se afirma. La **jurisprudencia**, tanto la propia como la de contrario, se **verifica en CENDOJ antes del acto**: las referencias que lleguen de bases privadas (EDJ/Lefebvre El Derecho, vLex, Iberley, Sepin) se contrastan contra el texto oficial del CGPJ en CENDOJ antes de usarlas o de distinguirlas en sala (encadénese con la skill `cendoj-descarga`). Esta decisión no introduce contenido jurídico nuevo: refuerza la regla de no invención ya presente en el flujo.

## Triggers

«Preparar juicio», «preparar testifical», «preparar el juicio», «el juicio es mañana», «cuadro de hechos», «mapa de hechos», «hechos controvertidos», «hechos no controvertidos», «interrogatorio testigo», «interrogatorio cruzado», «interrogatorio directo», «banco de preguntas», «preguntas al testigo», «esquema de conclusiones», «conclusiones del juicio», «vista oral», «acto del juicio», referencia interna W-XXXXX o REF-XXXX en asunto con AP ya celebrada.

## Inputs esperados

Demanda y contestación, transcripción de la AP (texto del CGPJ con timestamps `[hh:mm:ss:ms]`), minuta interna de la AP si existe, proposiciones de prueba, resolución de admisión, anexos documentales, resoluciones intermedias.

## Gotchas (errores a evitar)

Avisos no obvios que, sin esta nota, el agente pasaría por alto. Léelos antes de generar:

- **La transcripción del CGPJ prevalece sobre la minuta interna.** Si la nota de trabajo y la transcripción difieren en lo que fijó el juez, manda la transcripción (Decisión 2).
- **No inferir (source-locked).** Prohibido afirmar parentescos, relaciones, intenciones o conocimiento que el documento no sostenga literalmente. Si la fuente no lo dice, no se afirma (Decisión 14).
- **Jurisprudencia siempre verificada en CENDOJ antes del acto.** Las referencias de bases privadas (EDJ/Lefebvre, vLex, Iberley, Sepin) se contrastan contra el texto oficial del CGPJ; no se citan ni se distinguen en sala sin ese contraste (Decisión 14; encadenar con `cendoj-descarga`).
- **Orden de vista: ningún apartado se omite.** Si un apartado de los siete no aplica, se deja constancia expresa («No aplica»), no se borra (Decisión 13).
- **Fichero abierto = Word lo bloquea.** Si el `.docx` destino está abierto, se guarda con sufijo `_v2` y se avisa al usuario (no se falla en silencio).
- **Interrogatorios íntegramente cerrados irritan a algunos jueces.** La forma «Diga si es cierto que» se reserva para anclajes documentales y bloques nucleares; el resto, preguntas abiertas (Decisión 10).
- **La caja de anticipación a repreguntas solo se lee si el adversario abre el frente.** Es contención, no guion de exposición (Decisión 12).
- **Sin invención de contenido jurídico.** Jurisprudencia y calificaciones vienen de los inputs o de skills de cliente, nunca del modelo.

## Validación

Se considera madura cuando se haya aplicado a un asunto piloto (W-EJEMPLO) y a un asunto civil ajeno (arrendaticio o responsabilidad contractual) para verificar transversalidad.

## Telemetría y feedback (Fase 1 — auto-instrumentación)

La skill se auto-instrumenta conforme a la **Fase 1** de `EVOLUCION.md`. Esta sección documenta el mecanismo; no altera ninguna de las 12 decisiones metodológicas anteriores, solo registra su ejecución.

- **`scripts/log_uso.js`** — módulo helper. Expone `log(entry)` (escribe en `logs/uso.jsonl`) y `logTo(file, entry)` (para `logs/<ref>_pre.jsonl` y `logs/<ref>_post.jsonl`). Inyecta `ts` (ISO 8601 UTC) y `skill` automáticamente, crea `logs/` si no existe y es *best-effort*: si el log falla, avisa por stderr pero **nunca** rompe la generación del `.docx`.

- **Generadores instrumentados.** Los cuatro `gen_*.js` (`gen_conclusiones`, `gen_interrogatorio`, `gen_cuadro_hechos`, `gen_orden_vista`) llaman a `log_uso.log({...})` justo después de escribir cada `.docx`, registrando `ref`, `accion`, `archivos` producidos y métricas relevantes (hechos no controvertidos/controvertidos, testigos, preguntas, etc.).

- **Checklists.** `templates/checklist_pre_juicio.md` (objetivo táctico, frentes prioritarios, riesgos, testigos clave con rol) se rellena al iniciar la preparación → `logs/<ref>_pre.jsonl`. `templates/checklist_post_juicio.md` (entregables usados en sala, pregunta no prevista, retirada fallida, bloque largo/corto, valoración del acto) se rellena tras el juicio → `logs/<ref>_post.jsonl`.

- **Revisión programada.** `scripts/schedule_post_juicio.js` calcula `fecha_juicio + 7 días` y emite el descriptor de tarea (`taskId`, `fireAt`, `description`, `prompt`) en el formato de la skill `schedule`, lo deja en `logs/<ref>_schedule.json` e imprime la instrucción para activarlo. Si la integración automática con `schedule` no está disponible, el letrado lo invoca manualmente.

- **Esquema.** Todos los formatos de `logs/` están documentados en `logs/README.md`. Los datos de `logs/` (referencias reales) no se versionan ni se empaquetan en el `.skill`; solo viaja el `README.md`.

**Criterio de activación de la Fase 2:** 5+ ejecuciones reales en `uso.jsonl` con su `<ref>_post.jsonl` correspondiente.
