---
name: escritos-judiciales
description: "Usar siempre que se genere un escrito procesal civil español en formato .docx: demandas, contestaciones, recursos, requerimientos, escritos de trámite. Produce documentos Word con el formato estándar del despacho, listo para firma."
version: "1.0"
---

# Escritos Judiciales Civiles — Formato Estándar

## Stack

- **Lenguaje:** Node.js
- **Librería:** `docx` (npm install -g docx, v9+)
- **Salida:** `.docx` → carpeta del expediente (ver «Fase 0» y «Guardado y registro»); copia a `outputs/` para entrega.

---

## Fase 0 — Detección de expediente

Antes de generar nada, decide el modo según la estructura (no según el cliente):

1. Localiza `00_Input/_caso.md` subiendo desde la carpeta de trabajo del asunto.
2. **Existe** → modo **expediente estructurado**: guarda en la subcarpeta del expediente y registra (ver abajo).
3. **No existe** → modo **ad-hoc**: pregunta al letrado la carpeta destino; guarda allí; **sin registro de intake**.

No inventes la ruta del expediente: si no localizas `_caso.md` y el letrado no la indica, trabaja en ad-hoc.

## Guardado y registro

En modo estructurado, la salida primaria va a `<case>/<destino>/` y se deja una copia en `outputs/` (para entrega/`present_files`). El destino depende del tipo de escrito:

| Tipo de escrito | `tipo` | `destino` |
|---|---|---|
| demanda, contestación, reconvención, recurso, escrito de trámite | `demanda` / `contestacion` / `reconvencion` / `recurso` / `escrito_tramite` | `05_Procedimiento` |
| requerimiento extrajudicial | `requerimiento` | `04_Output predemanda` |

Tras guardar, **registra** con el helper bundleado (doble registro: manifiesto `<destino>/_index.md` + Navegación de `_caso.md`):

```bash
python scripts/registrar_outputs.py "<case_dir>" outputs.json
```

`outputs.json` (una entrada por `.docx` generado):

```json
[{"fichero": "DEMANDA_W-XXXXXX.docx", "tipo": "demanda", "perspectiva": "actora",
  "destino": "05_Procedimiento", "fuentes": ["informe_viabilidad", "encargo"],
  "wikilink": "DEMANDA_W-XXXXXX", "estado": "borrador"}]
```

`perspectiva` (`actora` | `defensiva`) la aporta el contexto del asunto; `wikilink` por defecto es el *stem* del fichero. El registro es *best-effort*: si falla, avisa pero **no invalida** el `.docx`. En modo ad-hoc **no se registra**.

**Telemetría (mejora continua).** Tras generar, registra el uso para que la skill mejore con el tiempo:

```bash
python scripts/registrar_uso.py escritos-judiciales "<ref>" generar_escrito \
  --archivos DEMANDA_W-XXXXXX.docx --metricas '{"tipo": "demanda", "hechos": 7}'
```

Es *best-effort* (no rompe la generación) y escribe en el store central; nunca en el `.skill`.

---

## Configuración de página

```javascript
page: {
  size: { width: 11906, height: 16838 }, // A4
  margin: { top: 1418, right: 1418, bottom: 1418, left: 1418 }, // 2,5 cm = 1417,3 DXA
}
```

---

## Tipografía base

| Elemento | Fuente | Tamaño | Estilo |
|---|---|---|---|
| Texto general | Times New Roman | 12pt (SZ=24) | Normal |
| Citas | Times New Roman | 10pt (SZ10=20) | Cursiva |
| Encabezado | Times New Roman | 10pt | Cursiva |

**Párrafo estándar:** justificado, interlineado 1,5 (line: 360), espaciado anterior 6pt (before: 120), posterior 0.

---

## Encabezado y pie

- **Encabezado:** vacío (sin texto, sin línea separadora)
- **Pie:** número de página centrado, TNR 12pt, sin línea separadora

```javascript
headers: { default: new Header({ children: [
  new Paragraph({ children: [new TextRun({ text: "", font: TNR, size: SZ10 })] })
]})}
footers: { default: new Footer({ children: [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { line: 240, before: 60, after: 0 },
    children: [new TextRun({ font: TNR, size: SZ, children: [PageNumber.CURRENT] })],
  })
]})}
```

---

## Tabla de cabecera del escrito

Siempre al inicio del documento. Dos filas: **Mi ref.** y **Juzgado**.

```javascript
const borde = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
// columnWidths: [1800, 7526], total: 9326 DXA
```

---

## Reglas tipográficas obligatorias

### Nombres propios
- `DON` / `DOÑA` + nombre siempre en **MAYÚSCULAS NEGRITA**: `DON IVÁN PÉREZ MARTÍNEZ`
- Aplica a: letrado, procurador, demandante, demandado — en toda mención

### Comparecencia
- **Incluir del letrado:** despacho, teléfono, correo electrónico
- **Incluir del demandado:** DNI en **MAYÚSCULAS NEGRITA**, móvil, correo electrónico
- **No incluir del actor:** nacionalidad, nº de pasaporte, domicilio

### Palabras clave en negrita
- `DIGO:`
- `DEMANDA DE JUICIO ORDINARIO` (y cualquier tipo de escrito: RECURSO DE APELACIÓN, etc.)
- Cuantías: `TRESCIENTOS MIL EUROS (300.000 €)`
- Referencias documentales: ver sección DOCUMENTO

### Nomens iuris — primera definición
Cuando se define un nomen que se repetirá, la primera vez va entre «» y en **negrita**:

```javascript
function rNomen(nomen) {
  return [r("(en adelante, «"), rB(nomen), r("»)")];
}
// Ejemplo: ...la finca sita en... (en adelante, «el Inmueble»)
```

---

## Patrones lingüísticos obligatorios

**Trimembración a binomio.** Eliminar el tercer adjetivo cuando es sinónimo:

- *libre, voluntario y consciente* → *libre e informado*
- *información completa, veraz y anticipada* → *información previa y veraz*
- *individualizables, documentables y autónomos* → *individualizados*

**Nominalizaciones a verbos en activa.**

- *procede a la desestimación de* → *desestime*
- *en cumplimiento de las obligaciones que asumió* → *cumpliendo lo asumido*

**Hedge phrases prohibidas.** Lista cerrada de eliminación íntegra: *con holgura, sin fisura, con total escrupulosidad, sin margen a interpretación, con rotundidad, con total claridad, conviene subrayar, conviene advertir, a mayor abundamiento, de contrario, esta parte considera, como no podía ser de otro modo, en su esencia, íntegramente* (cuando es repetitivo).

**Muletillas forenses.** Reducir al mínimo. Mantenibles solo en zonas de alto registro (comparecencia, suplico):

- *mi representada* → propagar alias en el cuerpo (introducido en la comparecencia con nomen).
- *respetuosamente comparezco* → *comparezco*.
- *como mejor proceda en Derecho* → eliminar.

**Incisos autorreferenciales suprimibles.** *como ha quedado acreditado*, *como desarrollarán los Fundamentos jurídicos*, *como resulta del Hecho X y de la documental aportada* (sustituir por *«como resulta del Hecho X»* a secas).

**Preámbulos subsidiarios estandarizados.** Fórmula breve obligatoria: *«Subsidiariamente, si el Juzgador rechaza los Hechos anteriores y acoge la interpretación X que postula la actora, …»* (12 palabras, no las 50-70 habituales).

**Listas breves a prosa.** Cuando una lista numerada tiene ítems de una sola frase, condensar en párrafo corrido con punto y coma o con (i)(ii)(iii) inline.

**Citas duplicadas a remisión.** Una sentencia se transcribe literalmente solo en el motivo donde más fuerza tiene. En las demás apariciones, remisión por número de Documento o por *«como se transcribió supra en el Hecho X»*.

---

## Arquitectura: motivos de oposición como Hechos en juicio verbal

**Aplicabilidad.** Arquitectura recomendada por defecto para contestaciones a demanda en juicio verbal. En el juicio ordinario sigue siendo válido el patrón tradicional con motivos sustantivos en Fundamentos.

**Justificación procesal.** Los arts. 399 y 405 LEC permiten que los Hechos incluyan el soporte normativo y jurisprudencial mínimo de los hechos impeditivos o extintivos. Razón forense: el juez lee con detenimiento los Hechos —donde busca la matriz probatoria— y survola los Fundamentos por aplicación de *iura novit curia*. Llevar los motivos a Hechos asegura que el argumento llegue.

**Estructura.** Dos planos:

- **Hechos comunes:** sustrato fáctico común a todos los motivos. Sin número máximo —tres es lo habitual y suficiente para la mayoría de los casos—. Bloques recurrentes: (a) operación o relación contractual base; (b) suscripción y ejecución del contrato controvertido; (c) hechos omitidos o tergiversados por la actora. En supuestos más complejos pueden añadirse Hechos adicionales —cronología previa, eventos posteriores al contrato, antecedentes contractuales entre las partes, comunicaciones extraprocesales relevantes—. Regla operativa: cada bloque fáctico que sirva a más de un motivo merece su propio Hecho común; los bloques que sirvan a uno solo van dentro del soporte fáctico de ese motivo.

- **Hechos-motivo:** los siguientes al último Hecho común. Un Hecho por cada motivo de oposición. La numeración global de Hechos no se interrumpe entre los dos bloques —si hay cinco Hechos comunes, los Hechos-motivo arrancan en el Sexto—.

**Patrón fijo del Hecho-motivo.** Tres apartados internos constantes:

1. **Tesis del motivo** — conclusión y fundamento principal en una frase.
2. **Soporte fáctico** — remisión a Hechos comunes o despliegue específico cuando el hecho impeditivo es propio del motivo.
3. **Soporte normativo, jurisprudencial y efecto procesal pretendido** — norma aplicable, doctrina TS/TJUE, aplicación al caso, fallo concreto solicitado. Subapartados *X.3.1, X.3.2…* cuando hay varios pilares interpretativos.

**Previo con roadmap efecto-causa.** El Previo enuncia los motivos en una lectura, con la consecuencia procesal primero y el fundamento después: *(1) la falta de legitimación pasiva ad causam de la representada, por imponer el precepto la obligación exclusivamente a X; (2) la no aplicación del art. Y al contrato Z, por tener los servicios prestados naturaleza distinta a…*. Numeración con paréntesis *(1) (2) (3)…*.

**Fundamentos exclusivamente procesales.** En esta arquitectura, los Fundamentos contienen únicamente competencia y procedimiento, postulación, *iura novit curia* y costas. La legitimación se menciona aquí por reenvío al Hecho-motivo correspondiente. Numeración romana (I a V), sin numeración global de párrafos.

---

## Sección HECHOS

### Título de cada hecho
```
PRIMERO.- DE LAS PARTES.-   ← negrita, justificado
```

### Subapartados — lista decimal continua
- **Referencia única** `hechos-cont` para todo el apartado de Hechos
- La numeración **no reinicia** entre distintos Hechos
- **Sangría francesa:** `left: 0, hanging: 425` (DXA) — 0,75 cm
- El número cuelga 0,75 cm a la izquierda del texto

```javascript
// NUMBERING_CONFIG — referencia "hechos-cont"
{
  reference: "hechos-cont",
  levels: [{
    level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT,
    style: {
      run: { font: TNR, size: SZ },
      paragraph: {
        alignment: AlignmentType.JUSTIFIED,
        spacing: { line: 360, before: 120, after: 0 },
        indent: { left: 425, hanging: 425 }, // se sobreescribe en el Paragraph
      },
    },
  }],
}

// Helper sub() — siempre con indent explícito
function sub(content) {
  const children = typeof content === "string" ? [r(content)] : content;
  return new Paragraph({
    numbering: { reference: "hechos-cont", level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 360, before: 120, after: 0 },
    indent: { left: 0, hanging: 425 }, // left=0, hanging=425 DXA
    children,
  });
}
```

### Remisiones documentales — DOCUMENTO Nº XX
- Siempre en **párrafo numerado aparte** dentro de la lista `hechos-cont`
- Misma sangría francesa que el resto de subapartados
- Formato: `"Nº"` — **sin punto** después de la N (nunca `N.º`)
- **Primera mención** de cada documento: negrita + subrayado
- **Menciones posteriores:** solo negrita

```javascript
function rDoc(n, primera = false) {
  const text = `DOCUMENTO Nº ${n}`;
  return primera
    ? r(text, { bold: true, underline: { type: UnderlineType.SINGLE } })
    : r(text, { bold: true });
}

function pDoc(n, descripcion, primera = false) {
  return new Paragraph({
    numbering: { reference: "hechos-cont", level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 360, before: 120, after: 0 },
    indent: { left: 0, hanging: 425 },
    children: [
      r("Se acompaña como "),
      rDoc(n, primera),
      r(" " + descripcion),
    ],
  });
}
```

### Citas literales
10pt cursiva, sangría izquierda 567 DXA (≈1 cm):

```javascript
function pCita(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 360, before: 120, after: 0 },
    indent: { left: 567 },
    children: [new TextRun({ text, font: TNR, size: SZ10, italics: true })],
  });
}
```

---

### Citas de jurisprudencia a pie de página (OBLIGATORIO)

**Regla del despacho.** Toda cita de una resolución judicial (STS, SAP, STSJ, SAN, ATS…) se hace en **dos planos**:

1. **En el cuerpo del escrito:** identificación abreviada con el ECLI inline, p. ej. *«(STS, Sala 1.ª, núm. 791/2011, de 11 de noviembre)»*, seguida de una **llamada de nota al pie** (`FootnoteReferenceRun`).
2. **A pie de página:** nota completa con identificación oficial **y enlace clicable al CENDOJ para descarga directa**, siguiendo EXACTAMENTE este patrón:

```
{TIPO} (Sala/Sección) núm. {NºRes}/{año}, de {fecha literal}. ROJ: {ROJ}. ECLI:{ECLI}. Texto íntegro y descarga directa en CENDOJ (CGPJ): {URL_openDocument}
```

Ejemplos reales (formato de referencia):

```
STS (Sala 1.ª) núm. 791/2011, de 11 de noviembre. ROJ: STS 9282/2011. ECLI:ES:TS:2011:9282. Texto íntegro y descarga directa en CENDOJ (CGPJ): https://www.poderjudicial.es/search/AN/openDocument/6d2ff30b2fa96ee0/20120220
STS (Sala 1.ª) núm. 824/2011, de 15 de noviembre. ROJ: STS 7365/2011. ECLI:ES:TS:2011:7365. Texto íntegro y descarga directa en CENDOJ (CGPJ): https://www.poderjudicial.es/search/AN/openDocument/b885cd88e4055bc1/20111128
STS (Sala 1.ª) núm. 305/2011, de 27 de junio. ROJ: STS 5089/2011. ECLI:ES:TS:2011:5089. Texto íntegro y descarga directa en CENDOJ (CGPJ): https://www.poderjudicial.es/search/AN/openDocument/b55c27b773cd7856/20110805
```

**Reglas.** Una nota por resolución, numeración correlativa. La URL es la del visor `openDocument/{hash}/{fecha}` del CENDOJ (obtenida con la skill `cendoj-descarga`) y debe insertarse como **hipervínculo clicable** (`ExternalHyperlink`). El ECLI y el ROJ se toman del PDF oficial del CGPJ, no de bases privadas. La nota al pie va en TNR 8pt (SZ8=16).

```javascript
// Document({ footnotes: { 1: fnJuris("STS (Sala 1.ª) núm. 791/2011, de 11 de noviembre. ROJ: STS 9282/2011. ECLI:ES:TS:2011:9282.", URL1), 2: ... } })
function fnJuris(meta, url) {
  return { children: [ new Paragraph({ spacing: { line: 240 }, children: [
    new TextRun({ text: meta + " Texto íntegro y descarga directa en CENDOJ (CGPJ): ", font: TNR, size: 16 }),
    new ExternalHyperlink({ link: url, children: [ new TextRun({ text: url, font: TNR, size: 16, style: "Hyperlink" }) ] }),
  ] }) ] };
}
// En el cuerpo: ...núm. 791/2011, de 11 de noviembre"), new FootnoteReferenceRun(1), r(").")
```

---

## Variantes territoriales y condicionales

**Principio.** Las variantes —territoriales (Cataluña, otros), condicionales (factura/no factura), alternativas (modelo de contrato según oficina)— se incluyen en el escrito **activadas por defecto**, con marcadores visuales que permiten al letrado **eliminar** el bloque cuando no aplique. Asimetría deliberada: borrar es seguro, insertar requiere reinjertar coherencia.

**Marcador visual.** Doble línea horizontal de signos `═` (55 caracteres) antes y después del bloque, con cabecera y pie identificativos. Adicionalmente, **resaltado amarillo** sobre la cabecera y el pie con el texto entre corchetes —obligatorio—; opcionalmente sobre el contenido variable entero. La línea `═` delimita la estructura; el resaltado amarillo es la alarma visual que advierte al letrado de que el bloque exige decisión: eliminarlo o adaptarlo.

```
═══════════════════════════════════════════════
[HECHO SEXTO — TERRITORIO: CATALUÑA. ELIMINAR
EN PROCEDIMIENTOS SUSTANCIADOS FUERA Y RENUMERAR
LOS SIGUIENTES: SÉPTIMO → SEXTO; OCTAVO → SÉPTIMO…]
═══════════════════════════════════════════════
```

**Implementación técnica del resaltado.** En Node.js docx: `highlight: "yellow"` en cada `TextRun` de la cabecera y pie. En python-docx: `r.font.highlight_color = WD_COLOR_INDEX.YELLOW`. En OOXML directo: `<w:rPr><w:highlight w:val="yellow"/></w:rPr>` en los runs correspondientes.

**Nota al letrado.** En cada bloque variable, una nota entre corchetes describe la condición de activación o eliminación con precisión y enumera los párrafos y documentos que también deben suprimirse.

---

## Sección FUNDAMENTOS DE DERECHO

> **Nota.** Cuando se aplica la arquitectura *motivos como Hechos* (ver sección «Arquitectura: motivos de oposición como Hechos en juicio verbal»), el bloque **DEL CARÁCTER SUSTANTIVO desaparece** y los Fundamentos se limitan a procesal: competencia, postulación, *iura novit curia* y costas, con numeración romana I a V y sin numeración global de párrafos.

- Dos subsecciones (arquitectura tradicional): **DEL CARÁCTER PROCESAL** y **DEL CARÁCTER SUSTANTIVO**
- Cada subsección tiene su propia referencia de numeración romana — **reinician entre sí**
- El número va en negrita

```javascript
// Referencias: "fund-procesal" y "fund-sustantivo"
{
  reference: "fund-procesal", // o "fund-sustantivo"
  levels: [{
    level: 0, format: LevelFormat.UPPER_ROMAN, text: "%1.",
    alignment: AlignmentType.LEFT,
    style: {
      run: { font: TNR, size: SZ, bold: true },
      paragraph: {
        alignment: AlignmentType.JUSTIFIED,
        spacing: { line: 360, before: 240, after: 60 },
        indent: { left: 567, hanging: 567 },
      },
    },
  }],
}
```

---

## Numeración automática (OOXML) — extensión

**Aplicación.** Todo párrafo del bloque HECHOS, sin distinción entre Previo y Hechos-motivo. Excluidos: los párrafos de transcripción literal de citas (sangría 1 cm, sin numerar), los títulos de Hecho y los subtítulos *X.1, X.2…* (con número embebido en el texto).

**Stack alternativo Python.** Si la generación se hace con `python-docx` en lugar del stack Node.js de referencia, la definición se inyecta vía manipulación XML directa de `numbering.xml` con `lxml`:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def setup_numbering(doc, num_id="99"):
    numbering = doc.part.numbering_part.element
    abstract = OxmlElement('w:abstractNum')
    abstract.set(qn('w:abstractNumId'), num_id)
    # ... lvl con format decimal, text "%1.", indent left=425 hanging=425 ...
    numbering.append(abstract)
    num = OxmlElement('w:num')
    num.set(qn('w:numId'), num_id)
    # ...
    numbering.append(num)
```

Resultado idéntico al stack Node.js.

---

## Sección SUPLICO

- **Párrafo único corrido**, sin lista numerada
- Pronunciamientos separados por punto y coma o numeración romana entre paréntesis: `(i)... (ii)... (iii)...`
- Nombre del demandado en **MAYÚSCULAS NEGRITA**
- Cuantías en **negrita**

---

## Firmas

- `EL LETRADO` y `EL PROCURADOR` en negrita
- Nombres en **MAYÚSCULAS NEGRITA** con DON/DOÑA
- **Sin** números de colegiado

```
DON IVÁN PÉREZ MARTÍNEZ          DON ALEKSANDR VOLKOV PETROV
```

---

## Índice documental

- Separado del cuerpo por un **salto de página explícito**
- Lista decimal con referencia `idx-docs`, sangría francesa left=425 hanging=425
- `DOCUMENTO Nº XX` siempre en **negrita + subrayado**, seguido de descripción en texto normal

```javascript
function rDocIdx(n) {
  return r(`DOCUMENTO Nº ${n}`, { bold: true, underline: { type: UnderlineType.SINGLE } });
}

// Cada entrada:
new Paragraph({
  numbering: { reference: "idx-docs", level: 0 },
  children: [rDocIdx(n), r(": " + descripcion)],
})
```

---

## Secciones centradas

Títulos de sección (HECHOS, FUNDAMENTOS DE DERECHO, AL JUZGADO SUPLICO, ÍNDICE DOCUMENTAL):

```javascript
function seccion(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { line: 360, before: 360, after: 120 },
    children: [rB(text)],
  });
}
```

---

## Reglas operativas

**Aplicabilidad.** Estas reglas son universales — aplicables a cualquier escrito procesal civil del despacho: demandas, contestaciones, recursos, requerimientos, escritos de trámite. No se condicionan al tipo de escrito ni a la arquitectura empleada.

**1. Esqueleto antes de redacción.** Para cualquier escrito de más de tres páginas, levantar primero un esqueleto en una página: encabezamiento, comparecencia, listado de Hechos con rúbricas, listado de Fundamentos con rúbricas, Suplico esquemático, Otrosíes, firmas. Validar la estructura completa antes de redactar línea del cuerpo.

**2. Nomens y alias en la primera vuelta.** Definir desde el inicio: alias de la representada, nomens *iuris* (el Inmueble, el Encargo, etc.), siglas y abreviaturas que se usarán. No introducir nomens nuevos a mitad del documento.

**3. Verificación de citas jurisprudenciales.** Toda cita TS/TC/TJUE/JPI se verifica contra CENDOJ, BOE o repositorio oficial antes de incluirla. Cada cita lleva ECLI o número de asunto. Las SJPI se invocan como *«criterio judicial coincidente»*, nunca como *«jurisprudencia»* (art. 1.6 CC).

**4. Numeración automática para todo párrafo editable.** Cualquier .docx sometido a edición posterior se genera con numeración automática vía `abstractNum + num` en `numbering.xml`. Nunca con números *hardcoded*. Los párrafos se renumeran solos al insertar o eliminar contenido.

---

## Correcciones doctrinales que el escrito evita

**1. Absolución vs. desestimación.** En jurisdicción civil se *desestima* la demanda, no se *absuelve*. La absolución es figura penal. El Suplico civil termina con *«desestime íntegramente la demanda con imposición de costas»*.

**2. Jurisprudencia vs. criterio judicial.** Art. 1.6 CC: la jurisprudencia es doctrina reiterada de la Sala 1.ª del TS. Las SJPI no la constituyen. Se invocan como *«criterio judicial coincidente»* o *«resolución en caso sustancialmente idéntico»*.

**3. Cuestión de inconstitucionalidad: planteamiento *in praesenti*.** No se reserva para más tarde ni se anuncia condicionalmente: se interesa desde el escrito, con solicitud de la audiencia común e improrrogable de diez días *ex* art. 35.2 LOTC. Fórmula correcta: *«esta parte interesa que el Juzgador, antes de dictar sentencia y al amparo del art. 35.2 LOTC, acuerde la audiencia común e improrrogable…»*. Fórmula incorrecta: *«esta parte se reserva el planteamiento»*.

**4. Remisiones cruzadas por nombre, no por número.** Las referencias internas se hacen por nombre del Hecho o del apartado, no por número de párrafo. La numeración cambia con la edición y las remisiones por número se rompen.

---

## Checklist antes de entregar

- [ ] DON/DOÑA + nombre en MAYÚSCULAS NEGRITA en todas las menciones
- [ ] DNI del demandado en MAYÚSCULAS NEGRITA
- [ ] Datos del letrado (despacho, tfno, email) en la comparecencia
- [ ] DIGO: / DEMANDA / cuantías en negrita
- [ ] Nomens primera vez en negrita «»
- [ ] Numeración de Hechos continua (no reinicia)
- [ ] pDoc() usa referencia hechos-cont y sangría left=0 hanging=425
- [ ] Primera mención de cada DOCUMENTO Nº XX: negrita+subrayado
- [ ] Fundamentos en romano, dos listas independientes (arquitectura tradicional) o una única procesal (arquitectura motivos como Hechos)
- [ ] Suplico en párrafo único
- [ ] Firmas sin nº colegiado
- [ ] Índice documental tras salto de página
- [ ] Sin líneas separadoras en encabezado ni pie
- [ ] "Nº" sin punto (nunca "N.º")
- [ ] Alias de la representada propagado en el cuerpo, sin residuos de "mi representada" fuera de la comparecencia
- [ ] Sin trimembraciones gratuitas (binomio o adjetivo único)
- [ ] Sin hedge phrases prohibidas (consultar lista cerrada en sección «Patrones lingüísticos»)
- [ ] Toda cita TS/TC/TJUE con ECLI o número de asunto verificado contra fuente
- [ ] SJPI invocadas como "criterio judicial coincidente", nunca como jurisprudencia
- [ ] Cuestión de inconstitucionalidad interesada in praesenti con audiencia ex art. 35.2 LOTC (no reservada)
- [ ] Numeración automática activa en HECHOS (numId presente en numbering.xml)
- [ ] Remisiones cruzadas por nombre del Hecho/apartado, no por número de párrafo
- [ ] Variantes territoriales/condicionales con marcadores visuales íntegros y resaltado amarillo
- [ ] Suplico en cascada coherente con los Hechos-motivo (en juicio verbal con esa arquitectura)
- [ ] Cita literal única por sentencia + remisión en repeticiones
- [ ] En civil: "desestimar", nunca "absolver"

---

## Mejora continua

La skill aprende de su uso real (mismo patrón que `preparacion-audiencia-previa` y `preparacion-juicio-oral`):

- **Checklist previo** (`templates/checklist_pre.md`): objetivo, tipo, frentes, riesgos, prueba clave → `<ref>_pre.jsonl` al iniciar.
- **Telemetría** (`scripts/registrar_uso.py`): cada generación deja una línea en `uso.jsonl` (store central).
- **Revisión programada** (`scripts/programar_revision.py`): al generar un escrito, programa la revisión a **presentación + 15 días** (o al detectar la versión `_FIRMADO`):

  ```bash
  python scripts/programar_revision.py escritos-judiciales "<ref>" --tipo-acto escrito \
    --fecha <YYYY-MM-DD presentación> --borrador "<case>/05_Procedimiento/DEMANDA_....docx"
  ```

  La tarea (vía skill `schedule`) pedirá rellenar el **checklist post** (`templates/checklist_post.md`) y correr `scripts/capturar_delta.py` sobre el borrador y su `_FIRMADO`.
- **Cierre del bucle.** Con 5+ usos reales con su `post`, el `motor_mejora.py` agrega uso+deltas+post y propone cambios a este `SKILL.md` (handoff a Claude Code).

## Changelog

Ver [`CHANGELOG.md`](CHANGELOG.md). Cada mejora promovida desde el motor de mejora cita ahí su evidencia (log/delta).
