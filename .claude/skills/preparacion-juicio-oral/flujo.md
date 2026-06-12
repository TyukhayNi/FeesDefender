# Flujo operativo — `preparacion-juicio-oral`

## Fase 0 — Reconocimiento del expediente

Localiza la carpeta del expediente. Inventaría archivos: demanda, contestación, transcripción AP, minuta AP, proposiciones de prueba, resolución de admisión, anexos numerados, DiOr intermedias. Si falta algún archivo crítico, lo señala al usuario.

**Modo de trabajo (por estructura, no por cliente).** Localiza `00_Input/_caso.md` subiendo desde la carpeta del asunto. Si existe → modo **expediente estructurado**: las salidas se guardan en `05_Procedimiento/` y se registran (ver Fase 6). Si no existe → modo **ad-hoc**: pregunta al usuario la carpeta destino; **sin registro de intake**.

Crea o reutiliza `_extraidos/` y extrae texto de PDFs con `pdftotext -layout`; .doc con `soffice --headless --convert-to txt`; PDFs escaneados con `ocrmypdf -l spa` y luego `pdftotext`.

## Fase 1 — Lectura y fijación de hechos

Lee la transcripción literal de la AP. Identifica:

- Hechos no controvertidos fijados o admitidos en sala. Para cada uno, captura `cita_ap[]` con `{timestamp, atribucion, texto}`. Atribuciones tipificadas: `Magistrado`, `Letrado actora`, `Letrado demandada` (sin nombres).
- Hecho(s) controvertido(s) fijado(s) por el juez (modo `juez_activo`) o, si el juez no concretó, por la actora a partir de la contestación (modo `partes`).
- Impugnaciones documentales, prueba admitida/denegada, sesgos del juez detectables.

Construye internamente el modelo de datos del caso (ver `templates/caso_ejemplo.json`).

> **Ejecución en modo *source-locked* (Decisión 14).** Esta fase se ejecuta en convivencia con `verificacion-anclada-fuente`. Cada hecho, cita de AP, importe y referencia documental se ancla a fuente verificable del expediente; no se infieren parentescos, relaciones ni conocimiento que el documento no sostenga literalmente. La jurisprudencia (propia y de contrario) se verifica en CENDOJ antes del acto: las referencias de bases privadas (EDJ/Lefebvre, vLex, Iberley, Sepin) se contrastan contra el texto oficial del CGPJ (encadénese con `cendoj-descarga`).

## Fase 2 — Confirmación interactiva

Antes de generar nada, el agente presenta al usuario en chat las citas detectadas y le pide confirmación una por una. Evita incluir citas marginales o malinterpretadas.

## Fase 3 — Producción del documento de conclusiones

Genera `CONCLUSIONES_[REF].docx`. Estructura: hechos no controvertidos (tabla con citas literales en celdas), hechos controvertidos (tabla con citas), conclusiones (bullets), petitum.

## Fase 4 — Banco de interrogatorios

Para cada testigo del modelo:

- Selecciona plantilla según `rol`.
- Genera siempre `[Testigo]_letrado.docx` con preguntas + RE + RD + Nota + anticipación.
- Genera `[Testigo]_testigo.docx` cuando aplica (default por rol o flag `generar_version_testigo`). Incluye disclaimer estándar.

## Fase 5 — Orden de vista (obligatoria) y cuadro de hechos (opcional)

`ORDEN_VISTA_[REF].docx` se genera **SIEMPRE** (output por defecto, no bajo solicitud), con la estructura canónica de siete apartados de la Decisión 13: (1) datos del acto; (2) documentos a tener a mano; (3) orden de testigos con rol y tiempo; (4) protestas previsibles; (5) riesgos/flancos con respuesta preparada; (6) conclusiones orales en bullets; (7) recordatorios procesales. Ningún apartado se omite: si alguno no aplica, se deja constancia expresa.

Bajo solicitud: `CUADRO_HECHOS_[REF].docx`.

## Fase 6 — Validación

Comprueba coherencia: testigos = admitidos en AP; referencias documentales coherentes entre archivos; importes y fechas consistentes. Pasa los `.docx` por el validador. Entrega al usuario los archivos con resumen en chat de decisiones estratégicas y alertas operativas para el acto del juicio.

Esta fase se ejecuta también en modo *source-locked* (Decisión 14): la validación no introduce hechos ni citas nuevas, solo verifica el anclaje de lo ya fijado.

### Guardado y registro (modo expediente estructurado)

Cuando existe `00_Input/_caso.md` (Fase 0), los `.docx` se guardan en `<case>/05_Procedimiento/` y se registran con el helper bundleado (manifiesto `05_Procedimiento/_index.md` + Navegación de `_caso.md`):

```bash
python scripts/registrar_outputs.py "<case_dir>" outputs.json
```

`outputs.json` lleva una entrada por documento generado. Mapa de `tipo` (todos a `destino: "05_Procedimiento"`):

| Documento | `tipo` |
|---|---|
| `CONCLUSIONES_[REF].docx` | `conclusiones` |
| `PREGUNTAS_[Testigo]_letrado.docx` / `_testigo.docx` | `interrogatorio` |
| `ORDEN_VISTA_[REF].docx` | `orden_vista` |
| `CUADRO_HECHOS_[REF].docx` | `cuadro_hechos` |

`perspectiva` (`actora` | `defensiva`) la aporta el asunto; `wikilink` por defecto es el *stem* del fichero; `estado: "borrador"`. El registro es *best-effort*: si falla, avisa pero **no invalida** el `.docx`. En modo ad-hoc **no se registra**.

### Rúbrica de cobertura pre-vista

Antes de entregar, el agente ejecuta esta rúbrica de ocho ítems y **resume el resultado en chat**. Los ítems no cubiertos se corrigen antes de entregar (no se entrega con ítems en rojo):

- **(a)** Cada hecho controvertido está cubierto por ≥ 1 pregunta de testifical y ≥ 1 conclusión.
- **(b)** Hay un `.docx` por cada testigo admitido en la AP (ni más ni menos).
- **(c)** Cada flanco/riesgo tiene su respuesta preparada y **localizada** (se sabe en qué documento/cita se apoya).
- **(d)** Coherencia de importes, fechas y referencias documentales entre todos los archivos.
- **(e)** Base jurídica y petitum alineados (lo que se pide se sostiene en lo que se argumenta).
- **(f)** La jurisprudencia de contrario está identificada y distinguida.
- **(g)** No hay nada fuera de lo fijado en la AP (no se introducen hechos ni controversias nuevas).
- **(h)** Todo está anclado a fuente y la jurisprudencia (propia y de contrario) está verificada en CENDOJ.

Si la rúbrica aporta valor de archivo (asuntos complejos, varios testigos, frentes múltiples), se persiste como `VALORACION_PREVISTA_[REF].md`. En asuntos simples basta con el resumen en chat; no se crea el archivo si no añade nada.

## Reglas de interacción

1. Confirmación antes de ejecutar. Asunto crítico — se pide luz verde antes de cualquier generación.
2. Iteración por chat antes del `.docx`. El `.md` pivote se itera con el usuario; el `.docx` se materializa al final.
3. Si el archivo destino está abierto (Word lo bloquea), se guarda con sufijo `_v2` y se avisa.
4. Brevedad operativa cuando hay urgencia.
5. Sin invención de contenido jurídico: jurisprudencia y calificaciones vienen de los inputs o de skills específicas del cliente.
