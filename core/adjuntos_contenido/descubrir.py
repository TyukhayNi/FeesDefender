from __future__ import annotations

from pathlib import Path

from .model import AdjuntoDescubierto

_HEADER = "# GENERADO por core.email_atomize"


def descubrir(adjuntos_dir: Path) -> list[AdjuntoDescubierto]:
    """Empareja cada sidecar de email_atomize con su binario en `adjuntos/`."""
    out: list[AdjuntoDescubierto] = []
    for sidecar in sorted(adjuntos_dir.glob("*.md")):
        if sidecar.name.endswith(".contenido.md"):
            continue
        try:
            texto = sidecar.read_text(encoding="utf-8")
        except Exception:
            continue
        if not texto.lstrip().startswith(_HEADER):
            continue
        meta = _parse_sidecar(texto)
        if not meta.get("att_id") or not meta.get("sha256"):
            continue
        base, binario = _binario_para(sidecar, meta.get("nombre_original", ""))
        out.append(AdjuntoDescubierto(
            att_id=meta["att_id"],
            sha256=meta["sha256"],
            tipo=meta.get("tipo", ""),
            nombre_original=meta.get("nombre_original", ""),
            mensajes=meta.get("mensajes", []),
            base=base,
            ruta_binario=binario,
            ruta_sidecar=sidecar,
        ))
    return out


def _parse_sidecar(texto: str) -> dict:
    meta: dict = {}
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea.startswith("- ") or ": " not in linea:
            continue
        clave, valor = linea[2:].split(": ", 1)
        clave, valor = clave.strip(), valor.strip()
        if clave == "mensajes":
            meta[clave] = [m.strip() for m in valor.split(",") if m.strip()]
        else:
            meta[clave] = valor
    return meta


def _binario_para(sidecar: Path, nombre_original: str) -> tuple[str, Path]:
    nombre = sidecar.name
    if nombre.endswith(".ficha.md"):
        base = nombre[: -len(".ficha.md")]
    else:
        base = nombre[: -len(".md")]
    ext = Path(nombre_original).suffix
    return base, sidecar.with_name(f"{base}{ext}")
