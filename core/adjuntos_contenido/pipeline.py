from __future__ import annotations

from pathlib import Path

from . import render, router
from .descubrir import descubrir
from .estado import cargar_estado, guardar_estado
from .model import ContenidoReport


def procesar_caso(case_id: str, *, forzar: bool = False) -> ContenidoReport:
    from core.email_atomize.pipeline import emails_out_dir
    return procesar_dir(emails_out_dir(case_id) / "adjuntos", forzar=forzar)


def _declarar_solapes(por_chat: dict[str, list[tuple[str, Path]]]) -> None:
    """Anota en cada export de WhatsApp qué OTROS adjuntos son el mismo chat.

    `MEJORAS #55.1` avisa de que fundir exports es peor que no tenerlos: cinco copias del
    mismo chat fundidas cuentan cinco veces cada mensaje, y una cronología probatoria así
    engaña. Aquí no se funde — pero callarlo sería el otro extremo, porque un LLM leyendo
    cinco `.contenido.md` creería tener cinco conversaciones. Declararlo es lo que permite
    no fundir sin engañar al lector; la reconciliación sigue sin construirse.
    """
    for huella, entradas in por_chat.items():
        if len(entradas) < 2:
            continue
        for att_id, ruta in entradas:
            otros = [o for o, _ in entradas if o != att_id]
            try:
                md = ruta.read_text(encoding="utf-8")
                ruta.write_text(
                    render.set_frontmatter(
                        md, "chat_solape",
                        f"MISMO CHAT que {', '.join(otros)} — no se han fundido; "
                        f"al construir una cronología, contar UNO solo"),
                    encoding="utf-8")
            except OSError:
                continue        # anotar el solape no puede tumbar la corrida


def procesar_dir(adjuntos_dir: Path, *, forzar: bool = False) -> ContenidoReport:
    report = ContenidoReport()
    if not adjuntos_dir.exists():
        report.errores.append(f"no existe el directorio {adjuntos_dir}")
        return report

    descubiertos = descubrir(adjuntos_dir)
    prev = {} if forzar else cargar_estado(adjuntos_dir)
    nuevo: dict = {}
    esperados: set[str] = set()
    # huella del chat → [(att_id, ruta del .contenido.md)] de los exports de WhatsApp de
    # esta corrida. Sirve para declarar el solape (`MEJORAS #55.1`) SIN fundir nada.
    por_chat: dict[str, list[tuple[str, Path]]] = {}

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
            resumen=None, texto=ext.texto, ocr_aplicado=ext.ocr,
            chat_huella=ext.chat_huella)
        destino.write_text(md, encoding="utf-8")
        if ext.chat_huella:
            por_chat.setdefault(ext.chat_huella, []).append((adj.att_id, destino))

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

    _declarar_solapes(por_chat)

    report.pendientes_resumen = sum(
        1 for e in nuevo.values() if e.get("resumen_estado") == "pendiente")
    report.pendientes_vision = sum(
        1 for e in nuevo.values() if e.get("vision_estado") == "pendiente")
    guardar_estado(adjuntos_dir, nuevo)
    return report
