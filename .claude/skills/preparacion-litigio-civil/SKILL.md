---
name: preparacion-litigio-civil
description: Fase estratégica previa a la redacción de escritos procesales civiles españoles. Úsala siempre que el usuario abra un asunto nuevo, inicie la preparación de una demanda, contestación, recurso, requerimiento extrajudicial o escrito de trámite, o mencione referencias internas de expediente (W-XXXXX, REF-XXXX). También cuando hable de «preparar», «iniciar», «empezar», «abrir expediente» o «redactar» cualquier escrito procesal civil, incluso si no lo dice explícitamente. Esta skill monta la estructura de carpetas del expediente, inicializa los documentos maestros (PREPARACION_X.md y HECHOS_X.md), pre-carga las decisiones cerradas estándar del despacho, y guía la toma de decisiones estratégicas antes de pasar a la redacción formal. NO redacta el .docx final — para eso encadena con la skill `escritos-judiciales`.
version: "1.0"
---

# Preparación de escritos procesales civiles

Esta skill gobierna la fase estratégica del trabajo procesal civil: la que va desde que se abre el asunto hasta que el escrito está listo para redactarse en .docx. Su propósito es que ninguna decisión estructural, probatoria, deontológica o de estilo se tome dos veces, y que la fase de redacción formal arranque con un mapa completo del asunto.

La skill NO produce el escrito final. Cuando llegue el momento de generar el .docx, invoca `escritos-judiciales`.

## Cuándo se activa

Detecta los siguientes contextos:

- Apertura de un asunto nuevo o mención de una referencia interna (W-XXXXX, REF-XXXX, [letra+número]).
- Frases como «vamos a preparar la demanda», «empezamos contestación», «redactar el recurso», «requerimiento previo», «escrito de trámite para [...]».
- Cualquier consulta que implique decidir estructura, pretensión, prueba o estrategia procesal en sede civil antes de redactar.

Si dudas, actívala. Es preferible que opere y se descarte que dejarla pasar.

## Flujo operativo

Sigue estos pasos en orden. No saltes ninguno salvo que el usuario lo indique expresamente.

### 1. Identificar tipo de escrito y posición procesal

Pregunta o extrae del contexto:

- **Tipo de escrito**: demanda, contestación, recurso, requerimiento extrajudicial, escrito de trámite.
- **Posición procesal**: actor, demandado, recurrente, recurrido, remitente.
- **Procedimiento**: ordinario, verbal, monitorio, ejecución, jurisdicción voluntaria.
- **Referencia interna** del despacho (formato libre del usuario).

Si falta cualquiera de estos datos, pídelo antes de seguir.

### 2. Verificar o crear la estructura de carpetas

Comprueba si el expediente ya existe en el sistema de archivos.

- **Si existe** (hay `00_Input/_caso.md`): confirma la ruta y navega a ella; **no recrees** la estructura. Ubica/actualiza los maestros en `02_Analisis/`.
- **Si no existe**: usa `scripts/scaffold_expediente.py` para crear el expediente. Ejemplo:

```bash
python scripts/scaffold_expediente.py \
  --base-dir "<ruta destino>" \
  --tipo-escrito demanda \
  --referencia "REF-2026-001" \
  --parte-representada "JUAN PÉREZ" \
  --posicion actor \
  --contraparte "PEDRO GÓMEZ"
```

El script monta el **mismo árbol que un expediente E&V** (`CASO_SUBDIRS`), un `_caso.md` mínimo (`tipo_expediente: particular`, sin campos E&V, Navegación vacía) y los maestros en `02_Analisis/`:

```
<ruta destino>/
├── 00_Input/
│   └── _caso.md            ← maestro del expediente (tipo_expediente: particular)
├── 01_Procesado/
├── 02_Analisis/
│   ├── PREPARACION_[TIPO].md
│   └── HECHOS_[TIPO].md
├── 03_Decision/
├── 04_Output predemanda/
├── 05_Procedimiento/        ← escritos generados (se registran en _caso.md)
├── 06_Anonimizado/
├── 07_AI cowork/
└── 90_Notas personales/
```

El árbol y el formato de `_caso.md` los produce el scaffolder canónico compartido `scaffold_caso.py`, común con el core E&V (garantía de no divergencia). `00_Input` no lleva subcarpetas E&V: solo intake manual. Consulta `reference/estructura_carpetas.md` para la convención completa.

### 3. Cargar las decisiones cerradas estándar

Lee `reference/decisiones_cerradas_estandar.md` y vuelca su contenido en la sección «Decisiones estratégicas cerradas» del `PREPARACION_X.md` recién generado. Estas son las convenciones permanentes del despacho (formato TS Sala 1.ª, DON/DOÑA mayúsculas negrita, listas a/b/c, deontología, etc.) y no se renegocian en cada asunto.

### 4. Cargar la guía específica del tipo de escrito

Lee el reference correspondiente al tipo identificado en el paso 1:

- `reference/demanda.md` — estructura, pretensión, prueba, riesgos típicos.
- `reference/contestacion.md` — allegaciones contrarias, oposición, hechos impeditivos/extintivos.
- `reference/recurso.md` — motivos de impugnación, fundamentos de revocación.
- `reference/requerimiento_extrajudicial.md` — hechos, pretensión, plazo, advertencia.
- `reference/escrito_tramite.md` — estructura mínima de escritos de trámite frecuentes.

No leas más de un reference por sesión salvo que el asunto requiera coordinación entre escritos.

### 5. Inventario de decisiones pendientes específicas del asunto

Para el tipo de escrito identificado, recorre con el usuario las decisiones estratégicas que sí requieren toma de postura asunto por asunto. Las preguntas mínimas son:

- **Pretensión**: ¿cuál es el petitum principal? ¿hay petición subsidiaria?
- **Cuantía**: determinada / indeterminada / por relación.
- **Intereses**: tipo y fecha de origen con fundamento documental.
- **Prueba**: ¿pericial? Si la hay, anuncio doble vía ex art. 337.1 LEC + designación subsidiaria ex art. 339 LEC. Perito propuesto identificado con nombre completo.
- **Testifical e interrogatorio**: quiénes.
- **Documental**: índice provisional con origen y fecha.

Cada respuesta se consigna en `PREPARACION_X.md` con marca `[CERRADO]` o `[PENDIENTE]`.

### 6. Cronología y personas clave

Construye la tabla cronológica de hechos con respaldo documental (`DOC_NN`) y la tabla de personas clave (nombre en formato DON/DOÑA mayúsculas negrita, rol, datos). Ambas viven en `PREPARACION_X.md`.

### 7. Redacción de Hechos (versión literal aprobada)

Cada Hecho se redacta como módulo cerrado en `HECHOS_X.md`, con título y texto literal. Esta es la fuente de verdad para el escrito final. La redacción de Hechos no es responsabilidad de esta skill; es responsabilidad del flujo conjunto entre letrado y cliente. Esta skill solo garantiza que exista el documento, que esté estructurado y que cada Hecho tenga su entrada.

### 8. Revisión deontológica del índice documental

Antes de cerrar la fase de preparación, revisa el índice documental para verificar que no se aporta correspondencia entre letrados sin consentimiento expreso (art. 21 EGAE, art. 5 CDCGAE). Marca esta revisión como ejecutada en `PREPARACION_X.md`.

### 9. Transición a la redacción formal

Cuando el `PREPARACION_X.md` no tenga decisiones marcadas como `[PENDIENTE]` y los Hechos estén consolidados en `HECHOS_X.md`:

- Anuncia al usuario que la fase de preparación está completa.
- Invoca la skill `escritos-judiciales` para generar el .docx aplicando los criterios formales TS Sala 1.ª.
- Una vez generado el borrador, recorre el `CHECKLIST_DECISIONES.md` (template en `templates/`) como verificación previa a firma.

## Principios transversales

- **El maestro es la única fuente de verdad.** Cualquier decisión que se tome en conversación debe quedar reflejada en `PREPARACION_X.md`. Si no está ahí, no existe.
- **Decisiones cerradas no se reabren.** Salvo cambio expreso, las decisiones marcadas `[CERRADO]` se respetan sin pedir confirmación de nuevo.
- **Listas y subdivisiones**: aplicar formato a), b), c) en segundo nivel y numeración 1., 1.1., 1.1.1. en jerárquica.
- **Personas**: DON/DOÑA + nombre completo en MAYÚSCULAS NEGRITA en toda mención.
- **Nomen iuris**: paréntesis único `(en adelante, «el X»)`.
- **Sin trimembraciones gratuitas.** En civil siempre «desestimar».
- **Idioma de comunicaciones con cliente**: ruso para clientes ex-URSS salvo indicación contraria; español para resto.

## Archivos bundled

| Ruta | Cuándo leerla |
|------|----------------|
| `templates/PREPARACION_template.md` | Solo si el script de scaffolding no está disponible y hay que crear el maestro a mano. |
| `templates/HECHOS_template.md` | Igual que el anterior. |
| `templates/CHECKLIST_DECISIONES.md` | En el paso 9, antes de firma. |
| `reference/decisiones_cerradas_estandar.md` | Siempre en el paso 3. |
| `reference/estructura_carpetas.md` | Si hay duda sobre el árbol de carpetas o variantes. |
| `reference/demanda.md` y demás | Solo el que corresponda al tipo de escrito identificado. |
| `scripts/scaffold_expediente.py` | En el paso 2 cuando el expediente es nuevo. |

## Relación con `escritos-judiciales`

Esta skill termina donde empieza `escritos-judiciales`. La frontera es la generación del .docx. Antes: aquí. Después: allí. Si el usuario pide directamente «redacta la demanda en Word», no saltes la preparación: verifica si `PREPARACION_X.md` está completo y, si no, recorre los pasos 1-8 antes de delegar en `escritos-judiciales`.

## Changelog

- **1.0** — Scaffolding alineado a `CASO_SUBDIRS` + `_caso.md` mínimo
  (`tipo_expediente: particular`) vía el scaffolder canónico compartido
  `scaffold_caso.py` (común con el core E&V); maestros en `02_Analisis/`.
