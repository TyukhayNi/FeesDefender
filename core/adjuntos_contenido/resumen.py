from __future__ import annotations

from pathlib import Path
from typing import Protocol

from . import render
from .estado import cargar_estado, guardar_estado


class Resumidor(Protocol):
    def resumir(self, texto: str) -> str: ...
    def describir_imagen(self, ruta: Path) -> str: ...


class ResumidorNoop:
    """Por defecto: no llama a ningún modelo; deja la cola en 'pendiente'."""

    def resumir(self, texto: str) -> str:
        return ""

    def describir_imagen(self, ruta: Path) -> str:
        return ""


def aplicar_resumenes(case_id: str, resumidor: Resumidor) -> int:
    from core.email_atomize.pipeline import emails_out_dir
    return aplicar_resumenes_dir(emails_out_dir(case_id) / "adjuntos", resumidor)


def aplicar_resumenes_dir(adjuntos_dir: Path, resumidor: Resumidor) -> int:
    estado = cargar_estado(adjuntos_dir)
    aplicados = 0
    for _sha, entry in estado.items():
        pendiente_resumen = entry.get("resumen_estado") == "pendiente"
        pendiente_vision = entry.get("vision_estado") == "pendiente"
        if not pendiente_resumen and not pendiente_vision:
            continue
        destino = adjuntos_dir / f"{entry['base']}.contenido.md"
        if not destino.exists():
            continue
        md = destino.read_text(encoding="utf-8")
        fm, _resumen, texto_body = render.parsear_contenido(md)

        if pendiente_vision:
            binario = adjuntos_dir / f"{entry['base']}{Path(fm.get('nombre_original', '')).suffix}"
            nuevo = resumidor.describir_imagen(binario) if binario.exists() else ""
        else:
            nuevo = resumidor.resumir(texto_body)

        if not nuevo.strip():
            continue  # NO-OP o sin resultado: se mantiene pendiente

        md = render.reemplazar_resumen(md, nuevo)
        md = render.set_frontmatter(md, "resumen_estado", "hecho")
        entry["resumen_estado"] = "hecho"
        if pendiente_vision:
            md = render.set_frontmatter(md, "vision_estado", "hecho")
            entry["vision_estado"] = "hecho"
        destino.write_text(md, encoding="utf-8")
        aplicados += 1

    guardar_estado(adjuntos_dir, estado)
    return aplicados
