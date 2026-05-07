# Instalación del módulo de anonimización

> Este documento describe los pasos para dejar operativo `core/anon/` en
> una máquina nueva. Tras seguirlo, `python -m scripts.health_check` debe
> dar todo verde.

El módulo `core/anon/` (absorbido de Expedientes Seguros el 2026-05-07) usa
una pila completa de NLP + OCR. Tres tipos de dependencia:

1. **Python** (instalable con pip — ya en `requirements.txt`).
2. **Modelos spaCy** (descargas de ~1.5 GB).
3. **Binarios del sistema** (Tesseract OCR, Ghostscript).

Al final del documento hay un checklist resumido.

---

## 1. Dependencias Python

Desde la raíz del proyecto:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
pip install -r requirements.txt
```

Esto instala `pdfminer.six`, `spacy`, `presidio-analyzer`, `presidio-anonymizer`,
`ocrmypdf`, `Pillow` y `pillow-heif` (entre las dependencias previas del
proyecto).

---

## 2. Modelos spaCy

Tres modelos, descargas separadas:

```powershell
python -m spacy download es_core_news_lg
python -m spacy download ca_core_news_sm
python -m spacy download en_core_web_lg
```

Tamaños aproximados: `es_core_news_lg` ≈ 560 MB, `en_core_web_lg` ≈ 780 MB,
`ca_core_news_sm` ≈ 30 MB. Las primeras dos descargas tardan algunos
minutos según conexión.

> Si solo se trabaja con documentos en español, los otros dos no son
> imprescindibles, pero `core/anon/nlp_engine.py` los espera. Para
> reducir, editar el `configuration` allí — pero ten en cuenta que perderás
> detección NER en cédulas catalanas y documentos en inglés (frecuentes
> en Engel & Völkers por la base internacional de clientes).

---

## 3. Tesseract OCR

OCR de PDFs escaneados. Imprescindible para el step `core/anon/ocr.py`.

### Instalación en Windows

1. Descargar el instalador oficial: <https://github.com/UB-Mannheim/tesseract/wiki>
2. **Marcar las casillas de los paquetes de idioma `Spanish`, `Catalan` y
   `Russian`** durante la instalación.
3. Añadir `C:\Program Files\Tesseract-OCR` al `PATH` del sistema.
4. Reiniciar PowerShell.

### Verificación

```powershell
tesseract --version
tesseract --list-langs
```

La segunda llamada debe incluir, como mínimo, `spa`, `cat` y `rus`. Si
faltan, descargar el `.traineddata` correspondiente de
<https://github.com/tesseract-ocr/tessdata> y copiarlo a
`C:\Program Files\Tesseract-OCR\tessdata\`.

---

## 4. Ghostscript

Requerido por `ocrmypdf --optimize 1` (que es el modo por defecto del
wrapper `core/anon/ocr.py`). Sin Ghostscript, ocrmypdf falla
silenciosamente al optimizar.

### Instalación en Windows

1. Descargar de <https://ghostscript.com/releases/gsdnld.html> (versión
   GPL, 64 bits).
2. **Marcar la casilla "Add to PATH"** durante la instalación.
3. Reiniciar PowerShell.

### Verificación

```powershell
gswin64c --version
```

Debe imprimir el número de versión sin error.

---

## 5. Health check global

Una vez completados los pasos 1-4:

```powershell
python -m scripts.health_check
```

Salida esperada (resumida):

```
[1] Dependencias Python
  ✓ pdfminer.six (vYYYYMMDD)
  ✓ spacy (vX.Y.Z)
  ✓ presidio-analyzer (vX.Y.Z)
  ...
[2] Modelos spaCy
  ✓ es_core_news_lg cargable
  ✓ ca_core_news_sm cargable
  ✓ en_core_web_lg cargable
[3] Binarios del sistema
  ✓ tesseract → tesseract 5.x.x
  ✓ ocrmypdf → ocrmypdf 16.x.x
  ✓ gswin64c → GPL Ghostscript 10.x.x
[4] Paquetes de idioma de Tesseract
  ✓ spa disponible
  ✓ cat disponible
  ✓ rus disponible
[5] Smoke test del singleton Presidio
  · Cargando modelos (puede tardar 20-40 s la primera vez)...
  ✓ AnalyzerEngine operativo — N entidad(es) en texto de prueba

✅ Entorno OK. Todo listo para anonimizar.
```

Si algún paso devuelve ✗, el mensaje indica el comando exacto para
solucionarlo.

---

## 6. Primera ejecución

Tras el health check verde, ejecutar la anonimización sobre un caso
existente:

```powershell
python -m scripts.anonimizar_caso "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
```

La primera llamada carga el singleton de Presidio (~30 s en la máquina
del despacho con i7-1255U). Las siguientes son instantáneas mientras
Streamlit / la sesión de Python siga viva.

---

## Checklist resumido

- [ ] `pip install -r requirements.txt`
- [ ] `python -m spacy download es_core_news_lg`
- [ ] `python -m spacy download ca_core_news_sm`
- [ ] `python -m spacy download en_core_web_lg`
- [ ] Tesseract 5.x con paquetes spa+cat+rus en PATH
- [ ] Ghostscript 10.x en PATH
- [ ] `python -m scripts.health_check` → todo verde

---

## Requisitos de hardware

- **RAM**: ~1.5-2 GB para los modelos spaCy + Presidio en memoria, +200 MB
  pico por documento procesado. En la máquina del despacho (16 GB) sin
  problema. Para deploy en VM compartida, mínimo 4 GB asignados.
- **CPU**: i7-1255U sin GPU discreta procesa un documento medio
  (~50 KB de texto) en 2-5 segundos.
- **Disco**: ~2 GB libres para los modelos spaCy en `~/.virtualenvs/.../Lib/site-packages/`.
