---
name: cendoj-descarga
description: "Usar siempre que se necesite localizar y/o descargar sentencias o autos del CENDOJ (Centro de Documentación Judicial del CGPJ). Activar cuando el usuario aporte referencias procedentes de Sepin, Lefebvre El Derecho, vLex, Iberley o cualquier base privada, o cuando facilite metadatos parciales (tribunal, sección, fecha, ROJ, ECLI, número de resolución). Produce los PDFs oficiales del CGPJ con nombre normalizado y verificación de coincidencia temática."
version: "1.1"
---

# Descarga de Sentencias desde CENDOJ

## Premisa

Las bases privadas (Sepin, Lefebvre, vLex, Iberley) no permiten descarga sin suscripción. CENDOJ es el repositorio oficial gratuito del CGPJ. Pero CENDOJ no acepta búsquedas vía URL — requiere formulario con sesión. **La automatización solo es viable mediante navegación real con `mcp__Claude_in_Chrome` sobre el navegador del usuario.** El sandbox bash no tiene acceso a `poderjudicial.es`.

---

## URLs clave

| Función | URL |
|---|---|
| Buscador principal | `https://www.poderjudicial.es/search/indexAN.jsp` |
| Visor de documento | `https://www.poderjudicial.es/search/AN/openDocument/{hash}/{fecha_yyyymmdd}` |
| PDF directo | `https://www.poderjudicial.es/search/contenidos.action?action=accessToPDF&publicinterface=true&tab=AN&reference={hash}&encode=true&optimize={fecha_yyyymmdd}&databasematch=AN` |

El `{hash}` es un identificador hexadecimal de 32 caracteres que CENDOJ asigna a cada documento; se obtiene del atributo `href` del enlace en la página de resultados. **Extraer SIEMPRE el `href` completo con `querySelectorAll`; un hash truncado genera un `fetch` con tamaño aparentemente correcto pero documento equivocado.** `{fecha_yyyymmdd}` es la fecha de indexación interna, también extraíble de la URL del resultado.

---

## Flujo de trabajo

### Paso 1 — Recoger todas las referencias

Pedir al usuario, o extraer del texto, todas las referencias que se quieran localizar. Para cada una, anotar:

- Órgano (TS / AN / AP / TSJ + provincia)
- Sección
- Fecha de resolución
- Número de resolución (si se conoce)
- ROJ (si se conoce)
- ECLI (si se conoce)
- Tema / palabra clave que identifica la materia

### Paso 2 — Inicializar el navegador

```
mcp__Claude_in_Chrome__list_connected_browsers
mcp__Claude_in_Chrome__select_browser → deviceId
mcp__Claude_in_Chrome__tabs_context_mcp createIfEmpty=true
mcp__Claude_in_Chrome__navigate → https://www.poderjudicial.es/search/indexAN.jsp
```

Esperar 5-6 s tras la navegación para que cargue el formulario y el modal de aviso legal. Cerrar el modal haciendo click en la X (coord. ≈ 1002, 47) o sobre la cabecera.

### Paso 3 — Estrategia de búsqueda en cascada

**Caso A — Tienes ECLI:** búsqueda directa. Devuelve siempre 1 resultado.

```
find "ECLI input field" → form_input ECLI:ES:XXX:YYYY:NNNN → key Return → wait 5
```

**Caso B — Tienes ROJ:** introducir en campo `Nº ROJ` con el formato exacto que aparece en CENDOJ (ej. `SAP M 8959/2018`). Devuelve 1 resultado.

**Caso C — Solo tienes órgano + sección + fecha:**

1. Localización (dropdown jerárquico):
   - Click sobre el cuadro `Localización` (coord. ≈ 550-890, 357) para abrir el desplegable.
   - Si la provincia está dentro de una comunidad autónoma (p. ej. Granada → Andalucía), click sobre `+ ANDALUCÍA` para expandir, luego sobre la provincia.
   - Si la provincia coincide con la CCAA (Cantabria, Asturias, Madrid…), click directamente sobre el checkbox.
   - Cerrar el desplegable haciendo click fuera (coord. ≈ 1000, 250).

2. Sección: `find "Sección input textbox"` → `form_input "N"` (número de sección sin formato).

3. Fechas: `find "Fecha resolución Desde input"` → `form_input "dd/mm/yyyy"`; ídem `Hasta` con la misma fecha (no rango).

4. Submit: el botón `Buscar` falla con `left_click` por colisión con la extensión Adobe Acrobat. Usar siempre:
   ```
   javascript_tool: document.querySelector('button[type="submit"], input[type="submit"]').click(); 'ok'
   ```
   o `key Return` desde el campo `Hasta`.

5. Esperar 5-6 s para los resultados.

**Caso D — Hay varios candidatos con la misma fecha:** añadir búsqueda por texto libre. Combinar siempre con la fecha de resolución (Desde=Hasta=fecha exacta).

Palabras clave útiles según materia, en orden decreciente de precisión:

| Materia | Búsqueda libre |
|---|---|
| Mediación inmobiliaria | `contrato mediación corretaje` |
| Cláusulas abusivas en mediación | `mediación inmobiliaria cláusula` |
| Arrendamiento urbano | `arrendamiento vivienda renta` |
| Compraventa inmobiliaria | `compraventa inmueble entrega cosa` |
| Vicios ocultos | `saneamiento vicios ocultos` |
| Reclamación de cantidad | `incumplimiento contractual cantidad` |

Si no se conoce la materia exacta, partir del título descriptivo que aporta la base privada y reducirlo a tres sustantivos clave.

**Nota sobre referencias privadas como LEADS.** Las referencias de Sepin, Lefebvre, vLex e Iberley son LEADS a verificar y corregir contra CENDOJ. Prevalecen siempre el ROJ, ECLI, fecha y ponente extraídos del PDF oficial del CGPJ. Si la doctrina buscada solo existe como Auto de inadmisión (ECLI con sufijo `A`), ofrecer el ATS si su razonamiento sirve, o declarar NO LOCALIZADA — nunca descargar una «aproximada».

### Paso 4 — Extraer los hashes

Una vez en la página de resultados, extraer todos los `href` de los documentos:

```javascript
Array.from(document.querySelectorAll('a'))
  .filter(a => a.href.includes('openDocument') && a.textContent.includes('NOMBRE_PROVINCIA'))
  .map(a => ({ roj: a.textContent.trim(), href: a.href }))
```

El `href` tiene la forma `…/openDocument/{HASH}/{FECHA}`. Capturar ambos.

### Paso 5 — Discriminar el documento correcto

Cuando hay varios candidatos para una misma fecha:

1. Verificar metadatos en la línea bajo el ROJ: `ECLI`, `Nº Resolución`, `Ponente`, `Nº Recurso`.
2. Si la referencia privada da ponente o nº de recurso, coincidir por ahí.
3. Si solo hay rasgo temático, abrir cada candidato y comprobar texto (caro) **o** usar búsqueda libre con palabra clave y la fecha exacta (barato, recomendado).

Una resolución `AAP` (Auto) tiene ECLI con sufijo `A` (ej. `ECLI:ES:APS:2019:113A`). Si la referencia privada habla de «sentencia», descartar los autos.

### Paso 6 — Descargar los PDFs

Desde una pestaña activa en `poderjudicial.es` (cualquier ruta del dominio), ejecutar este JS por **cada** PDF, **uno a uno**, con clic previo simulado sobre el viewport para activar el "user gesture":

```javascript
(async () => {
  const url = `/search/contenidos.action?action=accessToPDF&publicinterface=true&tab=AN&reference=HASH&encode=true&optimize=FECHA&databasematch=AN`;
  const r = await fetch(url);
  const ct = (r.headers.get('content-type') || '');
  const blob = await r.blob();
  // Si no es PDF (probable HTML de CAPTCHA) o el blob es minúsculo, abortar sin descargar
  if (!(ct.includes('pdf') || blob.size > 20000)) return 'NO-PDF ct=' + ct + ' size=' + blob.size;
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u; a.download = 'NOMBRE_NORMALIZADO.pdf';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  return 'ok ' + blob.size;
})()
```

**Reglas operativas críticas para la descarga:**

- **Una descarga por turno.** Chrome bloquea descargas múltiples desde el mismo origen sin gesto adicional. Disparar la siguiente solo tras confirmar que la anterior está en disco.
- **Click previo en el viewport.** Antes de cada `javascript_tool`, ejecutar `computer.left_click` sobre cualquier área neutra de la página (ej. coord. 780, 400). Esto reinyecta el user-activation flag que Chrome exige para `a.click()` con `download`.
- **Verificación por ruta exacta (no glob).** `ls`/`Glob` sobre `~/Downloads` falla de forma intermitente (montaje VirtioFS del sandbox). Verificar por ruta completa exacta: `test -f "/ruta/exacta/Archivo.pdf"` o `stat "/ruta/exacta/Archivo.pdf"`. Si no aparece tras 5 s, reintentar el ciclo click + JS en una pestaña nueva del mismo origen.
- **Si Chrome muestra el PDF en el visor de Acrobat** en lugar de descargar, el flujo `fetch + blob + download attribute` lo evita siempre. No navegar nunca directamente a la URL del PDF.
- **Validación de contenido.** El JS devuelve `'NO-PDF ct=...'` si recibe HTML (probable CAPTCHA) o un blob pequeño. En ese caso, ver el Paso 6-bis.

### Paso 6-bis — CAPTCHA «Control > Descargas masivas»

CENDOJ activa un CAPTCHA de imagen (`captcha.jsp?prevaction=accessToPDF...`) cuando detecta descargas intensivas, especialmente sin sesión autenticada. Suele aparecer tras varias descargas `fetch + blob` seguidas.

- **Prohibido resolverlo.** Resolver CAPTCHAs está fuera de mandato (política anti-bot). Hay que PARAR y devolver el control al usuario.
- **Handoff al usuario:** abrir o refrescar la pestaña visible del buscador (`navigate` sobre la pestaña del grupo MCP) para que el usuario la localice; pedirle que teclee EL CÓDIGO QUE VE en la imagen (no el pre-rellenado) y pulse «Acceder».
- **Iniciar sesión NO siempre lo desactiva** una vez disparado. Lo que funciona: pestaña nueva + el usuario resuelve el CAPTCHA una vez → permite un puñado de descargas antes de reaparecer.
- **Prevención:** descargas de una en una, volumen moderado por sesión; confirmar cada descarga en disco antes de la siguiente; si reaparece a mitad, nuevo handoff.

### Paso 7 — Guardar SIEMPRE en la carpeta del expediente (regla del despacho)

**Regla fija.** Las sentencias descargadas del CENDOJ deben guardarse **siempre en la carpeta del expediente del caso en curso**, no solo en `~/Downloads` ni únicamente en `outputs/`. El usuario trabaja por expedientes y necesita la documental archivada en la carpeta del caso. No basta con localizar o citar: hay que descargar el PDF oficial y dejarlo en el expediente.

Las descargas caen primero en `~/Downloads`. Desde ahí:

1. **Destino principal — carpeta del expediente.** Copiar los PDF (con nombre normalizado) a la carpeta del caso activo. Es la carpeta conectada del expediente que el usuario tiene montada para el caso (la raíz del expediente o una subcarpeta tipo `_ocr`, `05_Procedimiento`, `Jurisprudencia`…). Si hay varias subcarpetas candidatas y el destino no es obvio, **preguntar al usuario** en qué subcarpeta archivarlas.

   ```bash
   # La carpeta del caso aparece montada en /sessions/<id>/mnt/<carpeta_caso>/
   cp /sessions/<id>/mnt/Downloads/STS_*.pdf "/sessions/<id>/mnt/<carpeta_caso>/"
   ```

2. **Destino secundario — `outputs/`** (para poder enlazar/presentar al usuario con `mcp__cowork__present_files`):

   ```bash
   cp /sessions/<id>/mnt/Downloads/STS_*.pdf /sessions/<id>/mnt/outputs/
   ```

Requiere `mcp__cowork__request_cowork_directory ~/Downloads` previo si Descargas no está montado (y, en su caso, el montaje de la carpeta del expediente). Confirmar al usuario la ruta final dentro del expediente.

**Nota opcional — subida automática a Drive por tamaño.** No sustituye al archivado en el expediente ni al registro del Paso 7-bis; es un atajo para dejar copia en la carpeta de Drive del caso *si el conector de Drive está disponible* en el entorno:

- **PDF <150 KB** → subida automática por el conector (rápida).
- **PDF 150-300 KB** → ofrecer al usuario esperar la subida automática o arrastrar manualmente desde Descargas (suele ser más rápido).
- **PDF >300 KB** → arrastrar manualmente desde Descargas (la subida automática suele agotar el tiempo).

Los `.md` (conversiones del Paso 8-bis y consolidado del Paso 9) son pequeños y pueden subirse siempre de forma automática. Si el conector falla, volver al método manual (arrastrar) y verificar la llegada por ruta exacta (`stat`).

### Paso 7-bis — Registro en el expediente (solo si la jurisprudencia es de un asunto)

Si la descarga se hace **para un expediente concreto** (el letrado indica la carpeta del asunto o existe `00_Input/_caso.md`), además de entregarla:

1. Copia el PDF a `<case>/05_Procedimiento/Jurisprudencia/` (créala si no existe).
2. Regístralo con el helper bundleado:

   ```bash
   python scripts/registrar_outputs.py "<case_dir>" outputs.json
   ```

   con una entrada por sentencia:

   ```json
   [{"fichero": "SAP_Madrid_281-2018_02-07-2018_ROJ_SAP_M_8959-2018.pdf",
     "tipo": "jurisprudencia", "perspectiva": "",
     "destino": "05_Procedimiento/Jurisprudencia",
     "fuentes": ["ROJ: SAP M 8959/2018"],
     "meta": {"ecli": "ES:APM:2018:8959"},
     "estado": "descargado"}]
   ```

`fuentes` lleva el ROJ y `meta.ecli` el ECLI oficial del PDF (no los de la base privada). El registro es *best-effort*. Si la descarga **no** corresponde a un expediente (consulta suelta), omite este paso y entrega solo por `outputs/`.

### Paso 8 — Verificación

Cada PDF de CENDOJ trae en su primera página un bloque de metadatos. Validar con:

```bash
for f in SAP_*.pdf; do
  echo "=== $f ==="
  pdftotext -layout "$f" - 2>/dev/null | head -20
done
```

Confirmar coincidencia de: Roj, ECLI, Id Cendoj, Órgano, Sede, Sección, Fecha, Nº Recurso, Nº Resolución, Ponente.

**Nota sobre encoding CIDFont.** `pdftotext` puede devolver 0 coincidencias aunque el PDF sea correcto (encoding CIDFont propio de CENDOJ). No declarar el PDF inválido por eso: usar los metadatos de cabecera para la identidad, el resumen oficial de CENDOJ para la materia y, opcionalmente, OCR (`pdftoppm` + Tesseract). Estado a reportar: «identidad verificada; FJ no verificable por encoding».

**Contrastar materia.** ROJ correcto ≠ materia correcta. Comparar el resumen de CENDOJ con la materia esperada; si no coinciden, declararlo. No descargar «la más parecida».

**Verificar holding y vigencia.** No basta con que la resolución exista. Comprobar el régimen temporal aplicable (p. ej. doctrina de la LEC 1881, superada bajo la LEC 2000). Enlazar con `verificacion-anclada-fuente`. Marcar las resoluciones superadas/contrarias y para qué sirven.

**ROJ vs año.** El año del ROJ (publicación) puede diferir del nº/año de resolución (ej.: nº res. 769/2014, ROJ STS 254/2015). Reconciliar por **ECLI**; documentar la divergencia; no «corregir» el dato bueno.

Adicionalmente, verificar que la materia es la esperada:

```bash
for f in SAP_*.pdf; do
  echo "=== $f ==="
  pdftotext "$f" - 2>/dev/null | grep -iE "PALABRA_CLAVE_1|PALABRA_CLAVE_2" | head -3
done
```

### Paso 8-bis — Conversión automática PDF → Markdown (opcional)

Para facilitar la lectura sin visor PDF —y para sortear el encoding CIDFont—, convertir cada documento descargado a Markdown legible con el helper bundleado:

```bash
bash scripts/batch_pdf_to_md.sh <dir_pdfs> <dir_salida>
```

Equivale, documento a documento, a:

```bash
pdftotext -layout "$pdf" "${pdf%.pdf}.txt"
python scripts/parse_pdf_to_md.py "${pdf%.pdf}.txt" "${pdf%.pdf}.md"
```

Para cada `SAP_Madrid_281-2018.pdf` se genera `SAP_Madrid_281-2018.md` con cabecera (ROJ, ECLI, tribunal, fecha, ponente), hechos, ratio decidendi (fundamentos) y fallo. Si el texto sale vacío/ilegible, el `.md` lleva una nota de encoding CIDFont recomendando OCR. La conversión es *best-effort*: ante dudas, prevalece el PDF oficial.

### Paso 9 — Consolidado final: índice único de búsqueda (opcional)

Cuando la búsqueda agrupa varias resoluciones (p. ej. para un expediente), generar un único Markdown que las aglutine y facilite la clasificación:

```bash
python scripts/consolidate_search_results.py \
  --pdf-dir <dir_pdfs> \
  --output-file "00_INDICE_busqueda-CENDOJ_<tema>_<AAAA-MM-DD>.md"
```

El consolidado incluye: cabecera de la búsqueda (tema, órgano/sección, período, criterios), tabla resumen (tribunal, fecha, ROJ, ECLI, ponente, tamaño), clasificación por uso (✅ favorable / 📚 doctrinal / ⚠️ adversa / ❌ descartar), tabla de verificación (metadatos, encoding, materia, vigencia) y enlaces a PDFs y MDs. La clasificación por uso la completa el letrado: el script deja los documentos bajo «Sin clasificar» con las celdas listas.

---

## Convención de nombrado

Patrón obligatorio para todos los PDFs descargados:

```
{TIPO}_{Provincia}_{Nº-Res-Año}_{dd-mm-yyyy}_ROJ_{ROJ_completo}.pdf
```

Donde:

- `{TIPO}` ∈ `SAP` (Sentencia AP), `AAP` (Auto AP), `STS` (Sentencia TS), `STSJ` (Sentencia TSJ), `SAN` (Sentencia AN).
- `{Provincia}` en castellano y mayúscula inicial: `Madrid`, `Asturias`, `Cantabria`, `Granada`, `Barcelona`, etc.
- `{Nº-Res-Año}` con guion: `281-2018`.
- `{dd-mm-yyyy}` fecha de resolución con guiones: `02-07-2018`.
- `{ROJ_completo}` reemplazando espacios y barras por guion bajo: `SAP M 8959/2018` → `SAP_M_8959-2018`.

Ejemplos válidos:

```
SAP_Madrid_281-2018_02-07-2018_ROJ_SAP_M_8959-2018.pdf
SAP_Asturias_189-2018_19-04-2018_ROJ_SAP_O_1147-2018.pdf
SAP_Cantabria_242-2019_02-05-2019_ROJ_SAP_S_267-2019.pdf
SAP_Granada_68-2018_02-03-2018_ROJ_SAP_GR_329-2018.pdf
```

---

## Códigos ROJ por provincia (referencia rápida)

CENDOJ usa códigos de matrícula provincial para el ROJ de AP. Los más frecuentes:

| Provincia | Código ROJ | ECLI APx |
|---|---|---|
| Madrid | M | APM |
| Barcelona | B | APB |
| Valencia | V | APV |
| Sevilla | SE | APSE |
| Granada | GR | APGR |
| Málaga | MA | APMA |
| Asturias (Oviedo/Gijón) | O | APO |
| Cantabria (Santander) | S | APS |
| Vizcaya (Bilbao) | BI | APBI |
| Guipúzcoa (San Sebastián) | SS | APSS |
| Álava | VI | APVI |
| Navarra | NA | APNA |
| La Coruña | C | APC |
| Pontevedra | PO | APPO |
| Alicante | A | APA |
| Murcia | MU | APMU |
| Zaragoza | Z | APZ |

Para el TS: `STS XXXX/YYYY` con ECLI `ES:TS:YYYY:NNNN`. Sala 1.ª civil = ECLI `ES:TS:YYYY:NNNN` con `Tipo de órgano = Tribunal Supremo. Sala de lo Civil`.

---

## Errores frecuentes y su solución

| Síntoma | Causa | Solución |
|---|---|---|
| `Cannot access a chrome-extension:// URL of different extension` | Adobe Acrobat extension interceptando | Cerrar la pestaña y crear una nueva con `tabs_create_mcp` |
| `left_click ref_XXX` falla repetidamente sobre botones | Mismo problema de extensión | Sustituir por `javascript_tool: document.querySelector(SELECTOR).click()` |
| Descarga no aparece en `~/Downloads` | Chrome bloqueó por falta de user-activation | Click previo en viewport antes del JS, una descarga por turno |
| `WebFetch URL not in provenance set` | URL no vino de `WebSearch` previo | No usar `WebFetch` para CENDOJ — solo navegador real |
| `bash: curl: exit code 56` sobre poderjudicial.es | Proxy del sandbox bloquea el dominio | No intentar bash + curl; usar el navegador del usuario |
| Free text search sin resultados | Texto demasiado específico o tildes | Probar sinónimos: `mediación / corretaje / intermediación`. Sin comillas. Sin tildes si no funciona |
| Resultado de la búsqueda incluye Autos no deseados | Filtro insuficiente | `Tipo res. = Sentencia` en el formulario, o filtrar manualmente por sufijo `A` en ECLI |
| CAPTCHA «Control > Descargas masivas» (`captcha.jsp`) | Descargas intensivas o sin sesión | NO resolverlo (política anti-bot). Parar, abrir/refrescar la pestaña visible y pedir al usuario que lo resuelva. Espaciar las descargas (ver Paso 6-bis) |
| `cp` no aparece en la carpeta real del usuario | Montaje del sandbox aislado | Descargar a Descargas y que el usuario arrastre a Drive; verificar por ruta exacta |
| `ls`/`find` del montaje muestra la carpeta vacía | El listado del montaje no refleja el FS real | Acceder por ruta completa exacta; `pdftotext`/`stat` sí funcionan |
| Un resultado parece on-point pero no lo es | Fiarse del snippet/resumen del buscador | Abrir el PDF y leer hechos + ratio antes de clasificar |

---

## Plantilla de informe final

Al terminar, reportar al usuario:

1. **Consolidado único** (si se generó, Paso 9): `00_INDICE_busqueda-CENDOJ_...md` con tabla resumen, clasificación (favorable/doctrinal/adversa/descartar), estado de verificación y enlaces a PDFs y MDs.
2. **PDFs descargados**: datos oficiales extraídos del PDF (no de la base privada), tamaño y confirmación de archivado en el expediente.
3. **MDs** (si se generaron, Paso 8-bis): listado de documentos convertidos.

Tabla mínima de metadatos oficiales, seguida de los enlaces `computer://` a los archivos en `outputs/`:

```markdown
| Tribunal | Fecha | Nº Res | ROJ | ECLI | Ponente |
|---|---|---|---|---|---|
| SAP Madrid, Sec. 13.ª | 02/07/2018 | 281/2018 | SAP M 8959/2018 | ES:APM:2018:8959 | Carlos Cezón González |
...

[SAP Madrid 281/2018 (2-7-2018)](computer://.../outputs/SAP_Madrid_281-2018_...)
...
```

---

## Notas operativas

- **Fuente preferente.** Para citar en escritos procesales, usar siempre los datos del PDF oficial de CENDOJ, no los de la base privada. Las bases privadas a veces simplifican o reformulan; el dato bueno es ECLI + ROJ del CGPJ.
- **Caducidad de los hashes.** Los hashes `openDocument/{hash}` son estables a largo plazo, pero la fecha de indexación cambia si CENDOJ reindexa. Para almacenamiento a largo plazo, guardar siempre el ROJ y el ECLI; el hash es solo de tránsito.
- **Verificación cruzada con bases privadas.** Si la referencia procede de Sepin/Lefebvre/vLex y aporta ponente o número de recurso, contrastar con el PDF oficial. Si no coincide, la base privada se equivocó (sucede): prevalecen los metadatos del CENDOJ.
- **Resoluciones no publicadas en CENDOJ.** No todas las resoluciones llegan a CENDOJ (algunas SJPI, alguna AP menor). Si tras agotar todas las estrategias no aparece, comunicarlo al usuario sin insistir; ofrecer la cita por los datos parciales y proponer redactar el escrito sin el PDF.
- **Verificación sobre el PDF, no sobre el extracto.** Los resúmenes del buscador (y de agentes auxiliares) inducen a error: una candidata puede parecer análoga por el snippet y resultar fuera de caso (p. ej. una «hija» que es compradora, no representante) o incluso ADVERSA. Abrir el PDF, leer el supuesto de hecho y la ratio decidendi, y solo entonces clasificar (favorable / doctrinal / adversa / descartar).

---

## Checklist antes de entregar

- [ ] PDF abierto y leído al menos la primera página de cada uno
- [ ] Metadatos del PDF coinciden con la referencia de la base privada (o se ha justificado la divergencia)
- [ ] Coincidencia temática verificada con `grep` de palabras clave
- [ ] Nombrado siguiendo el patrón `TIPO_Provincia_NºRes_fecha_ROJ.pdf`
- [ ] Archivos copiados a `outputs/` y enlazados con `computer://`
- [ ] Tabla resumen con los 6 metadatos oficiales (Tribunal/Sección, Fecha, Nº Res, ROJ, ECLI, Ponente)
- [ ] Si es de un expediente: PDF en `05_Procedimiento/Jurisprudencia/` y registrado (Paso 7-bis)
- [ ] Si alguno no se ha localizado: aviso explícito al usuario con la causa

---

## Telemetría (mejora continua)

Al terminar una descarga, registra el uso (*best-effort*, store central, nunca en el `.skill`):

```bash
python scripts/registrar_uso.py cendoj-descarga "<ref>" descarga \
  --archivos SAP_Madrid_281-2018_...pdf --metricas '{"encontradas": 3, "no_localizadas": 0}'
```

## Changelog

Ver [`CHANGELOG.md`](CHANGELOG.md).
