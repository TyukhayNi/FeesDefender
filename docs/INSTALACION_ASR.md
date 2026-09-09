---
estado: vigente
---

# Instalación del reconocimiento de voz (ASR + diarización)

> Deja operativo `scripts/transcribir_audio.py`: notas de voz de WhatsApp, grabaciones de
> juicio y entrevistas de viabilidad → Markdown con timestamps citables y etiqueta de
> hablante. **Todo local**: el audio no sale de la máquina, solo se descargan modelos.
>
> Instalado y medido el **2026-09-09** en el portátil de trabajo (i7-1255U). Este documento
> es la receta reproducible; si hay que montarlo en otra máquina, se sigue de arriba abajo.

Hasta ese día no había ASR en el repo: `core/intake_lotes.py` clasificaba audio y vídeo y
`core/whatsapp_intake.py` contaba los audios de un export, pero `core/sala_maquina.py`
(`clasificar_ruta`) solo conocía `pdf | imagen | nativo | ofimatica`, así que **un `.opus`
caía en `sin_soporte`**. La spec de intake de WhatsApp lo difería expresamente (§5.5 «Audio
diferido»). En W-02USSI eso eran **67 ficheros y 5,21 h de audio que nadie había oído** — el
92 % de todo lo ilegible de ese caso.

---

## 1. Por qué un venv aparte y no `requirements.txt`

`faster-whisper` arrastra `ctranslate2`, `av` y `onnxruntime`: cinco wheels que **no** los
necesita ningún otro módulo del repo. El venv compartido lo usan varias sesiones a la vez y
ya se rompió una vez (2026-09-05, `site-packages` a..p borrados). Un venv dedicado y fuera
del árbol de trabajo no lo puede romper, ningún `git clean` lo toca y todos los worktrees lo
comparten.

Cuando se cablee a la sala de máquina (`MEJORAS #194`), la dependencia entra como **extra
opcional**, nunca en el `requirements.txt` base: el patrón es LibreOffice en
`core/ofimatica_a_pdf.py` — presente se usa, ausente el documento sale `sin_soporte` con la
causa real en la nota.

## 2. Receta

```powershell
# 1. venv dedicado, fuera del repo (Python 3.14 del sistema)
& "C:\Program Files\Python314\python.exe" -m venv "$env:USERPROFILE\.venvs\asr"
$vpy = "$env:USERPROFILE\.venvs\asr\Scripts\python.exe"
& $vpy -m pip install --upgrade pip
& $vpy -m pip install faster-whisper sherpa-onnx
```

Instala 26 paquetes y **cero `torch`**. Los cinco que importan traen wheel para
`cp314`/`abi3` en Windows, así que nada compila: `faster-whisper 1.2.1`,
`ctranslate2 4.8.2`, `onnxruntime 1.29.0`, `av 18.1.0`, `flatbuffers`.

```powershell
# 2. modelos de diarización (~34 MB, sin cuenta ni token de nadie)
$m = "$env:USERPROFILE\.venvs\asr\models"; New-Item -ItemType Directory -Force $m | Out-Null
curl.exe -sSL -o "$m\seg.tar.bz2" "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
& $vpy -c "import tarfile,os; tarfile.open(os.path.expanduser(r'~\.venvs\asr\models\seg.tar.bz2'),'r:bz2').extractall(os.path.expanduser(r'~\.venvs\asr\models'))"
curl.exe -sSL -o "$m\3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx" "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx"
```

El `recongition` de esa URL es un **typo del repo de k2-fsa**, no una errata de este
documento: corregirlo da 404.

```powershell
# 3. modelo de ASR (se descarga solo al primer uso; ~1,6 GB para turbo)
& $vpy -c "from huggingface_hub import snapshot_download; snapshot_download('mobiuslabsgmbh/faster-whisper-large-v3-turbo')"
```

**`ffmpeg` no es necesario** para transcribir: `av` (PyAV) trae sus propias libs y abre el
`.opus` de WhatsApp directo. Sí es útil para `ffprobe` y para fabricar audio de prueba, y
está instalado por scoop (`scoop install ffmpeg`, 9.0.1).

## 3. Uso

```powershell
$vpy = "$env:USERPROFILE\.venvs\asr\Scripts\python.exe"
cd "C:\Users\tnm33\Dev\FeesDefender"

# notas de voz: SIN diarizar (ver §5)
& $vpy scripts\transcribir_audio.py "<carpeta>" -s "<salida>" -m large-v3-turbo

# juicio o entrevista: con hablantes, y dile cuántos si lo sabes
& $vpy scripts\transcribir_audio.py "<grabacion.mp4>" --diarizar --hablantes 4

# triaje de un corpus grande (más rápido, menos fino)
& $vpy scripts\transcribir_audio.py "<carpeta>" -m small
```

Escribe un `<nombre>.transcripcion.md` por fichero, con cabecera de trazabilidad
(`origen_sha256`, bytes, duración, modelo, idioma + probabilidad, segmentos, tiempo, xRT) y
una línea por turno: ``- `[mm:ss–mm:ss]` **HABLANTE_02** · texto``. Es **idempotente por
sha256**: re-ejecutar no reprocesa lo ya hecho salvo `--forzar`.

Si los modelos de diarización están en otra ruta, fíjala en `FEESDEFENDER_ASR_MODELOS`.
Con `--diarizar` y sin modelos, **aborta antes de procesar nada** en vez de dejar 67
transcripciones sin hablante.

## 4. Qué modelo, con las cifras delante

El techo es el hardware: **`MaxClockSpeed = 1700 MHz`**, 15 W, sin GPU aprovechable.
Control sintético de 12 turnos y 3 hablantes es-ES, sobre `.opus` a 16 kbps (el códec de
WhatsApp), con verdad-terreno conocida:

| modelo | velocidad | WER | 10 datos duros |
|---|---|---|---|
| `small` | ×1,71 | 2,0 % | 10/10 |
| **`large-v3-turbo`** | ×0,64 | **1,3 %** | 10/10 |
| `large-v3` | ×0,40 | 1,3 % | 10/10 |

**`large-v3` no compra nada sobre `turbo` y cuesta un 60 % más.** Los «datos duros» son
importes, porcentajes, fechas y negaciones — lo que se cita en un escrito; los tres modelos
los conservaron (37.500 €, 21 %, 6 de marzo, 14 de octubre, «No es cierto que…»).

**Dos gradas, no un modelo único.** `small` para **triaje** (decidir si una nota habla del
inmueble del caso; sirve incluso en catalán aunque cambie un tiempo verbal) y `turbo` para
**evidencia**, lo que se va a citar. Así las 5,21 h de W-02USSI son ≈4 h de CPU en vez de
las 8-10 h que costaría pasar `turbo` por todo.

**El rendimiento sostenido no es el de la ráfaga.** Esta CPU se throttlea: medido en corpus
real, `small` cayó de ×2,02 (10 ficheros) a **×1,05** (29 ficheros, 47,2 min de audio), y
`turbo` de ×0,64 a ~×0,50 tras media hora de carga. **Al dar un coste hay que decir en qué
grada, y que son horas de la máquina de trabajo al 100 %.**

**El corpus es bilingüe y el idioma no se fija nunca.** En W-02USSI, de una muestra de 10:
5 castellano y **4 catalán** (Sant Cugat), todos los catalanes en el chat de una
colaboradora. Forzar `language="es"` produce basura silenciosa — un instrumento que no puede
dar el otro valor. El script autodetecta por fichero y registra `language_probability`.

## 5. Diarización: cuándo sí y cuándo no

**NO para notas de voz de WhatsApp.** Cada nota es de un solo hablante y su autor consta en
el cuerpo del chat: en W-02USSI se mapearon los 67 ficheros a su línea `<adjunto: …>` con
cierre en los dos sentidos y hora al segundo. Esa atribución le gana a cualquier diarizador
y no cuesta nada; diarizar solo podría empeorarla.

**SÍ para grabaciones de juicio y entrevistas de viabilidad**, donde hablan más de dos.

Lo medido, y el orden importa porque la primera lectura era falsa:

- Por **trama** de 10 ms: **67-78 %** según el audio. Tres controles distintos (dos voces
  del mismo TTS, tres timbres, con y sin pausas) dieron el mismo rango, así que no era un
  test mal hecho.
- Por **turno**: **12 de 12 correctamente atribuidos.**

No se contradicen: el 67-78 % penaliza **fronteras** (el corte va 0,3-0,5 s desplazado), no
identidad. Lo que hacía inútil la etiqueta era un defecto de diseño propio: **la unidad de
salida era el segmento del ASR**, y Whisper devuelve bloques de hasta 30 s — uno de 27 s
cubría **seis** intervenciones de tres personas, y el bloque entero se etiquetaba con el
hablante mayoritario. Con la unidad correcta (racha de palabras del mismo hablante, más
suavizado de fronteras) la atribución es utilizable.

Consecuencia práctica: **`pyannote` no hace falta**, y con ello se cae lo único que exigía
crear cuenta en HuggingFace y aceptar los términos de un tercero — que para material de
cliente no es un detalle menor. Se dejó medido que `pyannote.audio 4.0.7` **sí** resuelve en
este venv (43 wheels, `exit=0`, ninguno pisa lo instalado) por si algún día se quiere
comparar; `WhisperX` está **descartado**: todas sus versiones declaran `requires_python
<3.14`.

De los tres extractores de voz probados, `campplus` fue el mejor; `CAM++ voxceleb`
colapsaba a 1-2 hablantes incluso fijando `num_clusters=3`, y `titanet-large` quedaba en
medio costando el triple.

## 6. El límite, que viaja escrito en cada transcripción

**Una transcripción ASR es ayuda de lectura, no peritaje.** Los nombres propios y los
términos de oficio salen mal (medido: «GuruFax» por «burofax»). Un pasaje que se vuelva
decisivo se rehace con modelo grande y, si va a sala, lo transcribe una persona. Las
etiquetas de hablante son **provisionales** y se revisan antes de citar.

Por eso cada `.md` lleva en cabecera con qué instrumento se leyó, y el `estado` distingue
tres cosas que no son lo mismo — y **ninguna hereda `ocr_quality`**, cuyos umbrales de
caracteres por página no significan nada sobre minutos de audio:

| `estado` | Qué significa |
|---|---|
| `ok` | hubo habla y hay segmentos |
| `sin_habla` | se decodificó audio y el VAD no encontró voz. **Es un hecho sobre el audio, no un fallo** |
| `sin_audio` | el fichero no tiene pista de audio. No rompe el lote; sale en la lista de REVISAR |

Esa distinción salió de un defecto real: dos vídeos de W-02USSI daban `segmentos: 0` con
cuerpo vacío, indistinguibles de un fallo.

## 7. Checklist

- [ ] `& "$env:USERPROFILE\.venvs\asr\Scripts\python.exe" -c "import faster_whisper, sherpa_onnx; print('ok')"`
- [ ] `Test-Path "$env:USERPROFILE\.venvs\asr\models\sherpa-onnx-pyannote-segmentation-3-0\model.onnx"`
- [ ] `Test-Path "$env:USERPROFILE\.venvs\asr\models\3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx"`
- [ ] `python -m pytest -q tests/test_transcribir_audio.py` (44 tests; corren con el venv **del repo**, sin las dependencias de ASR)
- [ ] una corrida real sobre un fichero, y leer el `.md`: `estado: ok` e idioma detectado

## 8. Cabos sueltos

- **Cableado a la sala de máquina**: `MEJORAS #194`. Hoy la herramienta se llama a mano;
  mientras no se cablee, un `.opus` sigue cayendo en `sin_soporte` en el censo.
- **Copia transitoria**: durante la instalación quedó una copia del script en
  `~\.venvs\asr\transcribir.py`, en uso por una sesión hermana. **El canónico es
  `scripts/transcribir_audio.py`**; la copia se borra cuando esa sesión termine.
- **Sin explicar**: había 2,9 GB de `models--openai--whisper-large-v3` en la caché de
  HuggingFace **desde el 2026-07-30** y nada en el repo ni en la bitácora lo menciona.
