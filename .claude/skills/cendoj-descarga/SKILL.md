---
name: cendoj-descarga
description: "Usar siempre que se necesite localizar y/o descargar sentencias o autos del CENDOJ (Centro de Documentación Judicial del CGPJ). Activar cuando el usuario aporte referencias procedentes de Sepin, Lefebvre El Derecho, vLex, Iberley o cualquier base privada, o cuando facilite metadatos parciales (tribunal, sección, fecha, ROJ, ECLI, número de resolución). Produce los PDFs oficiales del CGPJ con nombre normalizado y verificación de coincidencia temática."
version: "1.0"
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

El `{hash}` es un identificador hexadecimal de 16 caracteres que CENDOJ asigna a cada documento; se obtiene del atributo `href` del enlace en la página de resultados. `{fecha_yyyymmdd}` es la fecha de indexación interna, también extraíble de la URL del resultado.

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
  const blob = await r.blob();
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u;
  a.download = 'NOMBRE_NORMALIZADO.pdf';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  return 'ok ' + blob.size;
})()
```

**Reglas operativas críticas para la descarga:**

- **Una descarga por turno.** Chrome bloquea descargas múltiples desde el mismo origen sin gesto adicional. Disparar la siguiente solo tras confirmar que la anterior está en disco (`Glob C:\Users\<usuario>\Downloads\PATRÓN`).
- **Click previo en el viewport.** Antes de cada `javascript_tool`, ejecutar `computer.left_click` sobre cualquier área neutra de la página (ej. coord. 780, 400). Esto reinyecta el user-activation flag que Chrome exige para `a.click()` con `download`.
- **Verificación tras 5 s.** Usar `Glob` sobre `~/Downloads/PATRÓN*.pdf` para confirmar. Si no aparece, reintentar el ciclo click + JS en una pestaña nueva del mismo origen.
- **Si Chrome muestra el PDF en el visor de Acrobat** en lugar de descargar, el flujo `fetch + blob + download attribute` lo evita siempre. No navegar nunca directamente a la URL del PDF.

### Paso 7 — Copiar a la carpeta de salida

Las descargas caen siempre en `~/Downloads`. Para entregárselas al usuario por enlace `computer://`, copiar a la carpeta `outputs/` del sandbox:

```bash
cd /sessions/<id>/mnt/outputs/
cp /sessions/<id>/mnt/Downloads/SAP_*.pdf .
```

Requiere `mcp__cowork__request_cowork_directory ~/Downloads` previo si no se ha montado.

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

Adicionalmente, verificar que la materia es la esperada:

```bash
for f in SAP_*.pdf; do
  echo "=== $f ==="
  pdftotext "$f" - 2>/dev/null | grep -iE "PALABRA_CLAVE_1|PALABRA_CLAVE_2" | head -3
done
```

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

---

## Plantilla de informe final

Al terminar, reportar al usuario una tabla con los datos oficiales extraídos del PDF (no de la base privada), seguida de los enlaces `computer://` a los archivos en `outputs/`:

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

- **1.0** — Paso 7-bis (registro de jurisprudencia en `05_Procedimiento/Jurisprudencia`)
  y telemetría de uso con `registrar_uso.py`.
