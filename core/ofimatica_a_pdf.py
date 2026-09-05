"""Documentos ofimáticos (`.doc`, `.odt`, `.ppt`, …) → PDF con capa de texto, vía LibreOffice.

Hasta el 2026-09-05 un `.doc` binario caía en `sin_soporte` en la sala de máquina: ni PDF
buscable, ni MD, ni fila que dijera por qué. En W-02MA0R la **demanda del juicio ordinario**
existía solo como `ordinario_vuelta_comprador.doc` (`MEJORAS #61`, acción 10 del informe de
Codex sobre el alta) y ningún LLM podía leerla.

Este módulo hace UNA cosa: convertir un fichero ofimático a PDF con `soffice --headless`.
El PDF resultante entra después por el camino PDF normal de `core.sala_maquina.ejecutar`
(pypdf si trae texto suficiente, escalera de OCR si no), así que la calidad y la custodia
las gobierna el mismo código que gobierna un PDF llegado por Drive.

Dos decisiones que no son detalle:

- **Verificar por resultado, nunca por código de salida.** `soffice` devuelve 0 en más de
  un caso en que no ha escrito nada (perfil bloqueado por una instancia abierta, filtro
  ausente). El PDF existe en `--outdir` con bytes, o la conversión falló.
- **Perfil de usuario propio y efímero** (`-env:UserInstallation`). Sin él, si el letrado
  tiene LibreOffice abierto, la instancia headless se pega a la GUI y la orden termina sin
  convertir. Con un perfil temporal la conversión es independiente de lo que haya en pantalla.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

#: Extensiones que LibreOffice abre como Writer/Impress y que hoy no tenían camino propio.
#: `.docx` y `.rtf` NO están: siguen en la ruta `nativo` (extracción determinista de texto).
EXTS_OFIMATICA: frozenset[str] = frozenset({
    ".doc", ".dot", ".odt", ".ott", ".ppt", ".pps", ".pptx", ".odp",
})

#: Variable de entorno para fijar el binario (una instalación portable, otra ruta).
ENV_SOFFICE = "FEESDEFENDER_SOFFICE"

_RUTAS_WINDOWS = (
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
)

#: Tope por documento. Un `.doc` normal convierte en segundos; el primer arranque de
#: LibreOffice ronda los 6 s. Un cuelgue no debe parar el lote entero.
TIMEOUT_S = 180


class ConversorNoDisponible(RuntimeError):
    """No hay `soffice` alcanzable: ni por `FEESDEFENDER_SOFFICE`, ni en PATH, ni instalado."""


class ConversionFallida(RuntimeError):
    """`soffice` terminó y el PDF no está (o está vacío)."""


def localizar_soffice() -> Path | None:
    """Ruta al binario de LibreOffice, o `None` si no hay ninguno.

    Orden: la variable `FEESDEFENDER_SOFFICE` (si apunta a un fichero existente), `soffice`
    en el PATH, y las dos rutas de instalación habituales en Windows. `None` es la respuesta
    honesta, y quien la reciba tiene que DECIRLO en la cobertura: un converso ausente que
    saliera como «sin soporte para esta extensión» sería el mismo silencio de antes.
    """
    fijado = os.environ.get(ENV_SOFFICE, "").strip()
    if fijado:
        p = Path(fijado)
        return p if p.is_file() else None
    en_path = shutil.which("soffice") or shutil.which("soffice.exe")
    if en_path:
        return Path(en_path)
    for candidata in _RUTAS_WINDOWS:
        if candidata.is_file():
            return candidata
    return None


def convertir(src: Path, dst_pdf: Path, *, soffice: Path | None = None,
              timeout_s: int = TIMEOUT_S) -> Path:
    """Convierte `src` a PDF y lo deja en `dst_pdf`. Devuelve `dst_pdf`.

    Lanza `ConversorNoDisponible` si no hay binario y `ConversionFallida` si `soffice`
    terminó sin dejar un PDF con bytes (sea cual sea su código de salida) o agotó el tiempo.
    Nunca devuelve «bien» sin haber comprobado el fichero.
    """
    src = Path(src)
    dst_pdf = Path(dst_pdf)
    binario = soffice or localizar_soffice()
    if binario is None:
        raise ConversorNoDisponible(
            f"LibreOffice (soffice) no encontrado: instálalo o fija {ENV_SOFFICE}")
    with tempfile.TemporaryDirectory(prefix="fd_soffice_") as tmp:
        tmp_dir = Path(tmp)
        perfil = tmp_dir / "perfil"
        salida = tmp_dir / "out"
        salida.mkdir()
        cmd = [
            str(binario), "--headless", "--norestore", "--nologo",
            f"-env:UserInstallation={perfil.as_uri()}",
            "--convert-to", "pdf", "--outdir", str(salida), str(src),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace",
                               timeout=timeout_s)
        except subprocess.TimeoutExpired as exc:
            raise ConversionFallida(
                f"soffice agotó {timeout_s}s convirtiendo {src.name}") from exc
        # soffice nombra la salida por el stem de la entrada. Se busca por resultado.
        producido = salida / f"{src.stem}.pdf"
        if not producido.is_file() or producido.stat().st_size == 0:
            detalle = (r.stderr or r.stdout or "").strip().replace("\n", " ")[:300]
            raise ConversionFallida(
                f"soffice terminó (rc={r.returncode}) sin producir PDF para {src.name}"
                + (f": {detalle}" if detalle else ""))
        dst_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(producido), str(dst_pdf))
    return dst_pdf
