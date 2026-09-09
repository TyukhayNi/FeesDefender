"""Transcribe audio y vídeo a Markdown con trazabilidad forense. Ejecución 100 % local.

    <python-del-venv-asr> scripts/transcribir_audio.py <fichero-o-carpeta> \
        [-s SALIDA] [-m MODELO] [--diarizar] [--hablantes N]

**Este script NO corre con el venv del repo.** Necesita `faster-whisper` (+ `sherpa-onnx`
para diarizar), que viven en un venv aparte a propósito — receta e intérprete exacto en
`docs/INSTALACION_ASR.md`. Los `import` pesados están dentro de las funciones para que el
módulo se pueda importar (y testear) sin ellos.

Decisiones que no son detalle, todas medidas el 2026-09-09:

- **El idioma se AUTODETECTA por fichero y se registra con su probabilidad.** No se fija:
  el corpus del despacho es bilingüe castellano/catalán (sobre W-02USSI: 5 `es` y 4 `ca`
  en una muestra de 10, todos los catalanes en el chat de una colaboradora). Forzar
  `language="es"` produce basura silenciosa en los catalanes — un instrumento que no puede
  dar el otro valor.
- **La unidad de salida es el TURNO del hablante, no el segmento del ASR.** Whisper
  devuelve bloques de hasta 30 s: uno de 27 s cubría **seis** intervenciones de tres
  personas. Etiquetar el bloque con el hablante mayoritario atribuye a uno lo que dijeron
  tres, y además hace que la métrica por trama (67-78 %) parezca medir identidad cuando
  mide fronteras. Agrupando por racha de palabras: **12 turnos de 12 bien atribuidos**.
- **`estado` no hereda `ocr_quality` ni umbrales de caracteres por página**, que no
  significan nada sobre minutos de audio. Tres valores, y el de en medio es un hecho sobre
  el audio y no un fallo: `ok` | `sin_habla` (se decodificó y el VAD no halló voz) |
  `sin_audio` (el fichero no tiene pista; **no rompe el lote**).
- **Verificar por resultado, nunca por código de salida.** El `.md` existe con segmentos, o
  la cabecera dice por qué no.
- **Idempotente por sha256.** Re-ejecutar no reprocesa salvo `--forzar`; si el origen
  cambió, el sha256 no cuadra y se rehace.
- **Una transcripción ASR es ayuda de lectura, no peritaje.** Los nombres propios y los
  términos de oficio salen mal («GuruFax» por «burofax», medido). La cabecera dice con qué
  instrumento se leyó para que nadie confunda una cosa con la otra.

El cableado a la sala de máquina (que un `.opus` deje de caer en `sin_soporte`) es
`MEJORAS #182`, y su patrón es `core/ofimatica_a_pdf.py`: dependencia externa opcional.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

EXTS_AUDIO = frozenset({".opus", ".ogg", ".oga", ".m4a", ".aac", ".mp3", ".wav",
                        ".flac", ".amr", ".wma"})
EXTS_VIDEO = frozenset({".mp4", ".mov", ".avi", ".webm", ".mkv", ".3gp", ".m4v"})
EXTS = EXTS_AUDIO | EXTS_VIDEO

#: Variable de entorno para fijar la carpeta de modelos de diarización (misma idea que
#: `FEESDEFENDER_SOFFICE` en `core/ofimatica_a_pdf.py`: una instalación en otra ruta).
ENV_MODELOS = "FEESDEFENDER_ASR_MODELOS"
_MODELOS_DEFECTO = Path.home() / ".venvs" / "asr" / "models"

_SEG_REL = Path("sherpa-onnx-pyannote-segmentation-3-0") / "model.onnx"
#: `campplus` fue el mejor de los tres extractores medidos; `CAM++ voxceleb` colapsaba a
#: 1-2 hablantes incluso fijando `num_clusters=3`, y `titanet` quedaba en medio.
_EMB_REL = Path("3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx")

HEADER_SHA = re.compile(r"origen_sha256`?:?\s*`?([0-9a-f]{64})")

#: Fiabilidad medida de la diarización, para que vaya escrita en cada `.md` y nadie cite
#: una etiqueta creyéndola firme. Por trama es 67-78 %; por turno, 12/12 en el control.
NOTA_DIARIZACION = (
    "**Etiquetas PROVISIONALES.** Medido el 2026-09-09 sobre control sintético de 3 "
    "hablantes: la atribución por turno fue correcta en 12 de 12, pero por trama se queda "
    "en 67-78 % (el error está en las fronteras). Revisar antes de citar."
)

LIMITE = (
    "> Transcripción automática: **ayuda de lectura, no peritaje**. Los nombres propios y\n"
    "> los términos de oficio salen mal. Un pasaje decisivo se rehace con modelo grande y,\n"
    "> si va a sala, lo transcribe una persona."
)


def localizar_modelos() -> Path | None:
    """Carpeta de modelos de diarización, o `None` si no hay ninguna utilizable.

    Orden: `FEESDEFENDER_ASR_MODELOS` (si contiene los dos ficheros), luego la ruta por
    defecto. Devuelve `None` en vez de lanzar para que quien llame pueda avisar ANTES de
    procesar nada, como hace `_avisar_si_falta_soffice` en `scripts/sala_maquina.py`.
    """
    candidatas = []
    if (env := os.environ.get(ENV_MODELOS)):
        candidatas.append(Path(env))
    candidatas.append(_MODELOS_DEFECTO)
    for d in candidatas:
        if (d / _SEG_REL).is_file() and (d / _EMB_REL).is_file():
            return d
    return None


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mmss(s: float) -> str:
    """Segundos → `mm:ss`, que es como se cita un pasaje de audio en un escrito."""
    s = max(0.0, s)
    return f"{int(s) // 60:02d}:{int(s) % 60:02d}"


def decodificar(p: Path, sr: int = 16000):
    """Fichero → `np.float32` mono a `sr` Hz, vía PyAV (que trae sus propias libs de
    ffmpeg, así que el `.opus` de WhatsApp entra sin binario externo ni conversión)."""
    import av
    import numpy as np

    with av.open(str(p)) as cont:
        if not cont.streams.audio:
            raise ValueError("el fichero no tiene pista de audio")
        remuestreo = av.AudioResampler(format="s16", layout="mono", rate=sr)
        trozos = []
        for frame in cont.decode(cont.streams.audio[0]):
            for out in remuestreo.resample(frame):
                trozos.append(out.to_ndarray().reshape(-1))
        for out in remuestreo.resample(None):  # vaciar el buffer del remuestreador
            trozos.append(out.to_ndarray().reshape(-1))
    if not trozos:
        raise ValueError("no se decodificó ninguna muestra")
    return np.concatenate(trozos).astype(np.float32) / 32768.0, sr


def diarizar(x, sr: int, hablantes: int | None, modelos: Path | None = None):
    """`[(inicio, fin, 'HABLANTE_NN'), …]`. Dar `hablantes` mejora mucho el resultado."""
    import sherpa_onnx

    d = modelos or localizar_modelos()
    if d is None:
        raise FileNotFoundError(
            f"faltan los modelos de diarización: ni {ENV_MODELOS} ni {_MODELOS_DEFECTO} "
            f"contienen {_SEG_REL} y {_EMB_REL} (ver docs/INSTALACION_ASR.md)")
    cl = (sherpa_onnx.FastClusteringConfig(num_clusters=hablantes) if hablantes
          else sherpa_onnx.FastClusteringConfig(threshold=0.5))
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(d / _SEG_REL)),
            num_threads=12),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(d / _EMB_REL), num_threads=12),
        clustering=cl, min_duration_on=0.3, min_duration_off=0.5)
    sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
    if sd.sample_rate != sr:
        raise ValueError(f"el modelo quiere {sd.sample_rate} Hz y el audio va a {sr}")
    return [(s.start, s.end, f"HABLANTE_{s.speaker + 1:02d}")
            for s in sd.process(x).sort_by_start_time()]


def hablante_de(turnos, t: float) -> str | None:
    """Hablante cuyo turno cubre el instante `t`, o `None` si cae en un hueco."""
    for ini, fin, spk in turnos:
        if ini <= t <= fin:
            return spk
    return None


def suavizar(palabras: list[tuple]) -> list[tuple]:
    """Cose las palabras huérfanas de las fronteras de turno.

    El diarizador coloca el corte 0,3-0,5 s desplazado, así que la PRIMERA palabra de cada
    intervención cae en la cola del turno anterior y sale sin hablante o con el equivocado.
    Medido el 2026-09-09: los 12 turnos se atribuían bien y aun así salían seis líneas de
    una sola palabra («Sí,», «Y», «Nada», «Se», «No»).

    Dos reglas, y las dos miran **hacia adelante** porque el defecto es de INICIO de turno:
    (1) una palabra sin hablante hereda del siguiente que lo tenga, y solo si no hay
    ninguno, del anterior; (2) una palabra aislada entre dos hablantes distintos pertenece
    al que viene después.

    Cada palabra es `(inicio, fin, texto, hablante)`; devuelve la lista con el hablante
    corregido y todo lo demás intacto.
    """
    out = [list(p) for p in palabras]
    n = len(out)
    for i in range(n):  # (1) huérfanas
        if out[i][3] is None:
            sig = next((out[j][3] for j in range(i + 1, n) if out[j][3]), None)
            ant = next((out[j][3] for j in range(i - 1, -1, -1) if out[j][3]), None)
            out[i][3] = sig or ant
    for i in range(1, n - 1):  # (2) islas de una palabra
        if (out[i][3] != out[i - 1][3] and out[i][3] != out[i + 1][3]
                and out[i - 1][3] != out[i + 1][3]):
            out[i][3] = out[i + 1][3]
    return [tuple(p) for p in out]


def linea_racha(racha: list[tuple]) -> str:
    """Una línea por turno: ``- `[mm:ss–mm:ss]` **HABLANTE_NN** · texto``."""
    ini, fin = racha[0][0], racha[-1][1]
    spk = racha[0][3] or "HABLANTE_?"
    return f"- `[{mmss(ini)}–{mmss(fin)}]` **{spk}** · " + "".join(w[2] for w in racha).strip()


def agrupar_por_turno(palabras: list[tuple]) -> list[str]:
    """Palabras con hablante → una línea de Markdown por racha del mismo hablante."""
    lineas: list[str] = []
    racha: list[tuple] = []
    for pal in suavizar(palabras):
        if racha and pal[3] != racha[-1][3]:
            lineas.append(linea_racha(racha))
            racha = []
        racha.append(pal)
    if racha:
        lineas.append(linea_racha(racha))
    return lineas


def transcribir(p: Path, modelo, args) -> str:
    """Cuerpo Markdown de un fichero. **No lanza**: el fallo se declara en la cabecera."""
    from faster_whisper import BatchedInferencePipeline

    tam = p.stat().st_size
    cab = [f"# {p.name}", "",
           f"- `origen`: `{p.name}`",
           f"- `origen_sha256`: `{sha256(p)}`",
           f"- `bytes`: {tam:,}".replace(",", "."),
           f"- `modelo`: faster-whisper `{args.modelo}` (int8, CPU)"]
    t_ini = time.perf_counter()
    try:
        x, sr = decodificar(p)
    except Exception as e:  # un fichero sin pista de audio no es un error del lote
        return "\n".join(cab + [f"- `estado`: **sin_audio** — {type(e).__name__}: {e}", ""])

    dur = len(x) / sr
    cab.append(f"- `duracion`: {mmss(dur)} ({dur:.1f} s)")

    turnos: list[tuple] = []
    if args.diarizar:
        t0 = time.perf_counter()
        try:
            turnos = diarizar(x, sr, args.hablantes)
            cab.append(f"- `diarizacion`: sherpa-onnx · "
                       f"{len({s for _, _, s in turnos})} hablante(s) · "
                       f"{len(turnos)} turnos · {time.perf_counter() - t0:.1f} s")
            cab.append(f"- `diarizacion_fiabilidad`: {NOTA_DIARIZACION}")
        except Exception as e:
            cab.append(f"- `diarizacion`: **fallo** — {type(e).__name__}: {e}")

    pipe = BatchedInferencePipeline(model=modelo)
    t0 = time.perf_counter()
    segs, info = pipe.transcribe(str(p), beam_size=args.beam, word_timestamps=bool(turnos),
                                 vad_filter=True, batch_size=args.batch)
    lineas, n_seg, palabras = [], 0, []
    for s in segs:
        n_seg += 1
        if turnos:
            for w in (s.words or []):
                palabras.append((w.start, w.end, w.word,
                                 hablante_de(turnos, (w.start + w.end) / 2)))
        else:
            lineas.append(f"- `[{mmss(s.start)}–{mmss(s.end)}]` {s.text.strip()}")
    if turnos:
        lineas = agrupar_por_turno(palabras)
    tardo = time.perf_counter() - t0

    estado = ("**ok**" if n_seg else
              "**sin_habla** — se decodificó audio y el VAD no encontró voz")
    cab += [f"- `idioma_detectado`: **{info.language}** (p={info.language_probability:.2f})",
            f"- `segmentos`: {n_seg}",
            f"- `tiempo_asr`: {tardo:.1f} s (x{dur / tardo:.2f} tiempo real)",
            f"- `tiempo_total`: {time.perf_counter() - t_ini:.1f} s",
            f"- `estado`: {estado}",
            "", LIMITE, "", "---", ""]
    return "\n".join(cab + (lineas or ["*(sin habla detectada)*"])) + "\n"


def _construir_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Transcribe audio/vídeo a Markdown, en local.")
    ap.add_argument("entrada", type=Path, help="fichero o carpeta (recursivo)")
    ap.add_argument("-s", "--salida", type=Path,
                    help="carpeta de salida (por defecto, junto al origen)")
    ap.add_argument("-m", "--modelo", default="large-v3-turbo",
                    help="small (triaje) | large-v3-turbo (defecto, evidencia) | large-v3")
    ap.add_argument("--diarizar", action="store_true",
                    help="etiquetar hablantes; para juicios y entrevistas, NO para notas de voz")
    ap.add_argument("--hablantes", type=int, help="número de hablantes si lo sabes (mejora mucho)")
    ap.add_argument("--beam", type=int, default=1, help="1 = rápido (defecto), 5 = algo mejor")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--hilos", type=int, default=12)
    ap.add_argument("--forzar", action="store_true", help="reprocesar aunque el .md ya cuadre")
    return ap


def ficheros_de(entrada: Path) -> list[Path]:
    """Un fichero, o los audios/vídeos de una carpeta en orden estable."""
    if entrada.is_file():
        return [entrada]
    return sorted(p for p in entrada.rglob("*") if p.suffix.lower() in EXTS)


def main(argv: list[str] | None = None) -> int:
    args = _construir_parser().parse_args(argv)

    if not args.entrada.exists():
        print(f"no existe: {args.entrada}", file=sys.stderr)
        return 2
    ficheros = ficheros_de(args.entrada)
    if not ficheros:
        print(f"ningún audio/vídeo en {args.entrada}", file=sys.stderr)
        return 2
    if args.diarizar and localizar_modelos() is None:
        print(f"ERROR: --diarizar y no hay modelos: ni {ENV_MODELOS} ni "
              f"{_MODELOS_DEFECTO}. Ver docs/INSTALACION_ASR.md, o corre sin --diarizar.",
              file=sys.stderr)
        return 2

    print(f"{len(ficheros)} fichero(s) · modelo {args.modelo} · "
          f"diarización {'SÍ' if args.diarizar else 'no'}")
    from faster_whisper import WhisperModel
    t0 = time.perf_counter()
    modelo = WhisperModel(args.modelo, device="cpu", compute_type="int8",
                          cpu_threads=args.hilos)
    print(f"modelo cargado en {time.perf_counter() - t0:.1f} s\n")

    resumen, t_lote = [], time.perf_counter()
    for i, p in enumerate(ficheros, 1):
        destino = (args.salida or p.parent) / (p.stem + ".transcripcion.md")
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists() and not args.forzar:
            m = HEADER_SHA.search(destino.read_text(encoding="utf-8", errors="replace"))
            if m and m.group(1) == sha256(p):
                print(f"[{i}/{len(ficheros)}] {p.name} → ya hecho, sha cuadra")
                resumen.append({"fichero": p.name, "estado": "cacheado"})
                continue
        print(f"[{i}/{len(ficheros)}] {p.name} ...", end=" ", flush=True)
        cuerpo = transcribir(p, modelo, args)
        destino.write_text(cuerpo, encoding="utf-8")
        est = re.search(r"`estado`: \*\*(\w+)\*\*", cuerpo)
        idi = re.search(r"`idioma_detectado`: \*\*(\w+)\*\*", cuerpo)
        print(f"{est.group(1) if est else '?'}"
              + (f" · {idi.group(1)}" if idi else "") + f" → {destino.name}")
        resumen.append({"fichero": p.name, "estado": est.group(1) if est else "?",
                        "idioma": idi.group(1) if idi else None, "md": str(destino)})

    print(f"\n{len(ficheros)} fichero(s) en {(time.perf_counter() - t_lote) / 60:.1f} min")
    idiomas: dict[str, int] = {}
    for r in resumen:
        if r.get("idioma"):
            idiomas[r["idioma"]] = idiomas.get(r["idioma"], 0) + 1
    if idiomas:
        print("idiomas: " + ", ".join(f"{k}={v}" for k, v in sorted(idiomas.items())))
    # `sin_habla` y `sin_audio` no son fallos, pero sí cosas que alguien tiene que mirar.
    malos = [r for r in resumen if r["estado"] not in ("ok", "cacheado")]
    if malos:
        print(f"REVISAR ({len(malos)}): "
              + ", ".join(f"{r['fichero']} [{r['estado']}]" for r in malos))
    if args.salida:
        (args.salida / "_transcripciones.json").write_text(
            json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
