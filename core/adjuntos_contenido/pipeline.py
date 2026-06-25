from __future__ import annotations

from pathlib import Path

from . import render, router
from .descubrir import descubrir
from .estado import cargar_estado, guardar_estado
from .model import ContenidoReport


def procesar_caso(case_id: str, *, forzar: bool = False) -> ContenidoReport:
    from core.email_atomize.pipeline import emails_out_dir
    return procesar_dir(emails_out_dir(case_id) / "adjuntos", forzar=forzar)


def procesar_dir(adjuntos_dir: Path, *, forzar: bool = False) -> ContenidoReport:
    report = ContenidoReport()
    if not adjuntos_dir.exists():
        report.errores.append(f"no existe el directorio {adjuntos_dir}")
        return report

    descubiertos = descubrir(adjuntos_dir)
    prev = {} if forzar else cargar_estado(adjuntos_dir)
    nuevo: dict = {}
    esperados: set[str] = set()

    for adj in descubiertos:
        destino = adjuntos_dir / f"{adj.base}.contenido.md"
        esperados.add(destino.name)

        cached = prev.get(adj.sha256)
        if not forzar and cached and cached.get("ok") and destino.exists():
            nuevo[adj.sha256] = cached
            report.saltados += 1
            continue

        if not adj.ruta_binario.exists():
            report.errores.append(f"{adj.att_id}: binario no encontrado ({adj.ruta_binario.name})")
            continue

        try:
            ext = router.extraer(adj.ruta_binario, adj.tipo)
        except Exception as exc:  # noqa: BLE001 — un adjunto no aborta la corrida
            report.errores.append(f"{adj.att_id}: {exc}")
            continue

        hay_resumen = ext.ok and (bool(ext.texto.strip()) or ext.vision_estado == "pendiente")
        resumen_estado = "pendiente" if hay_resumen else "n/a"

        md = render.render_contenido(
            att_id=adj.att_id, nombre_original=adj.nombre_original, tipo=adj.tipo,
            sha256=adj.sha256, metodo=ext.metodo, caracteres=len(ext.texto),
            confianza=ext.confianza, resumen_estado=resumen_estado,
            vision_estado=ext.vision_estado, mensajes=adj.mensajes,
            resumen=None, texto=ext.texto)
        destino.write_text(md, encoding="utf-8")

        entry = {"metodo": ext.metodo, "chars": len(ext.texto), "ok": ext.ok,
                 "resumen_estado": resumen_estado, "vision_estado": ext.vision_estado,
                 "base": adj.base}
        nuevo[adj.sha256] = entry

        if ext.metodo == "omitido":
            report.omitidos += 1
        elif ext.metodo == "sin_texto" or not ext.ok:
            report.sin_texto += 1
        elif ext.metodo == "vision":
            pass  # imagen sin texto; se contabiliza en pendientes_vision al final
        else:
            report.extraidos += 1

        guardar_estado(adjuntos_dir, nuevo)  # incremental → reanudable

    # poda de huérfanos: solo *.contenido.md sin sidecar actual
    for p in adjuntos_dir.glob("*.contenido.md"):
        if p.name not in esperados:
            p.unlink()
            report.podados += 1

    report.pendientes_resumen = sum(
        1 for e in nuevo.values() if e.get("resumen_estado") == "pendiente")
    report.pendientes_vision = sum(
        1 for e in nuevo.values() if e.get("vision_estado") == "pendiente")
    guardar_estado(adjuntos_dir, nuevo)
    return report
