"""Orquestación de la Capa A end-to-end.

Lee ``03_Email`` → avistamientos → colapsa por Message-ID → construye RegistroMensaje
(cabeceras + cuerpo + adjuntos + IDs congelados) → escribe mensajes/, adjuntos/ (+fichas),
corpus.jsonl, _registro.json, CORREOS_LECTURA.md, INDICE_ADJUNTOS.md. Idempotente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.email_export import split_eml
from core.intake_manifest import compute_sha256_bytes

from . import attachments as A
from . import bodies as B
from . import corpus as C
from . import dedup as D
from . import extract as E
from . import headers as H
from . import ids as IDS
from . import identidades as ID
from . import inline as INL
from . import render as R
from . import vistas as V
from .model import AdjuntoRef, AdjuntoUnico, RegistroMensaje, SegmentoEnterrado


@dataclass
class AtomizeReport:
    mensajes: int = 0
    adjuntos_unicos: int = 0
    adjuntos_decorativos: int = 0
    reconstruidos_b: int = 0          # mensajes capa B promovidos (alta + media reconstruida)
    reconstruidos_media: int = 0      # de los anteriores, los media-reconstruida (no estructural)
    citas_a_revision: int = 0         # punteros media/baja a _revision/cola.md
    upgrades: int = 0                 # citas resueltas a una copia limpia de Capa A
    vistas_generadas: int = 0
    notas: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        return (f"{self.mensajes} mensajes atómicos ({self.reconstruidos_b} reconstruidos B), "
                f"{self.citas_a_revision} citas a revisión, {self.upgrades} upgrades; "
                f"{self.adjuntos_unicos} adjuntos únicos "
                f"({self.adjuntos_decorativos} decorativos filtrados), "
                f"{self.vistas_generadas} vistas, "
                f"{len(self.errores)} errores")


def _idioma(texto: str) -> str:
    """Heurística mínima es/ca/en por stopwords (suficiente para Fase 1)."""
    t = " " + texto.lower() + " "
    ca = sum(t.count(w) for w in (" amb ", " aquest ", " però ", " seva ", " molt "))
    en = sum(t.count(w) for w in (" the ", " and ", " you ", " with ", " regards "))
    es = sum(t.count(w) for w in (" que ", " con ", " usted ", " saludos ", " los "))
    return max((("ca", ca), ("en", en), ("es", es)), key=lambda x: x[1])[0]


def atomize_dir(src_dir: Path | str, out_dir: Path | str, *, case_dir: Path | str | None = None) -> AtomizeReport:
    """Atomiza todos los .eml de *src_dir* y escribe los artefactos en *out_dir*.

    Args:
        src_dir: directorio con los .eml de entrada.
        out_dir: directorio de salida (se crea si no existe).
        case_dir: raíz del caso donde se busca ``identidades.yaml``/``vistas.yaml``.
            Por defecto ``out.parent.parent`` (layout estándar
            ``<caso>/01_Procesado/Emails``). En tests u otros layouts donde *out*
            no cuelgue de ``01_Procesado/Emails``, pasar *case_dir* explícitamente;
            si no se encuentra el YAML, el comportamiento es genérico (sets vacíos).
    """
    src = Path(src_dir)
    out = Path(out_dir)
    if case_dir is None:
        case_dir = out.parent.parent          # <caso>/01_Procesado/Emails → <caso>
    ident = ID.cargar_identidades(case_dir)
    (out / "mensajes").mkdir(parents=True, exist_ok=True)
    (out / "adjuntos").mkdir(parents=True, exist_ok=True)
    report = AtomizeReport()

    reg = IDS.load_registro(out)
    avistamientos = list(E.iter_avistamientos(src))
    colapsados = D.colapsar(avistamientos)

    # adjuntos: contar apariciones (para filtro decorativo) sobre los raws canónicos
    raws = [m.raw for m in colapsados]
    apariciones = A.contar_apariciones(raws)

    unicos: dict[str, AdjuntoUnico] = {}      # sha -> AdjuntoUnico
    mensajes: list[RegistroMensaje] = []
    carriers: list[tuple[RegistroMensaje, bytes]] = []
    for col in colapsados:
        try:
            m = _construir_mensaje(col, reg, apariciones, unicos, report)
        except Exception as exc:  # noqa: BLE001 — un mensaje no aborta la corrida
            report.errores.append(f"{col.message_id or '(sin id)'}: {exc}")
            continue
        mensajes.append(m)
        carriers.append((m, col.raw))
        reg.marcar_procesado(col.eml_origen)

    # --- Pase Layer B (tras congelar TODOS los IDs de Capa A) ---
    mensajes_b, punteros, upgrades = _pase_layer_b(reg, mensajes, carriers, report, ident)
    mensajes.extend(mensajes_b)

    for m in mensajes:
        (out / "mensajes" / R.nombre_md(m)).write_text(R.render_md(m), encoding="utf-8")
    # Idempotencia: eliminar .md huérfanos (p. ej. un mensaje B superado por un upgrade en una
    # re-corrida) que ya no están en el conjunto esperado. Solo toca *.md de mensajes/.
    esperados = {R.nombre_md(m) for m in mensajes}
    for p in (out / "mensajes").glob("*.md"):
        if p.name not in esperados:
            p.unlink()
    report.mensajes = len(mensajes)
    report.reconstruidos_b = len(mensajes_b)
    report.reconstruidos_media = sum(1 for m in mensajes_b if m.confianza == "media-reconstruida")
    report.citas_a_revision = len(punteros)

    for att in unicos.values():
        _escribe_adjunto(out, att)
    report.adjuntos_unicos = len(unicos)

    (out / "corpus.jsonl").write_text(C.corpus_jsonl(mensajes), encoding="utf-8")
    (out / "CORREOS_LECTURA.md").write_text(
        R.render_correos_lectura(mensajes), encoding="utf-8")
    (out / "INDICE_ADJUNTOS.md").write_text(
        R.render_indice_adjuntos(list(unicos.values())), encoding="utf-8")

    revision = out / "_revision"
    revision.mkdir(exist_ok=True)
    for nombre, contenido in R.render_revision(mensajes_b, punteros, watched=ident.vigiladas, upgrades=upgrades).items():
        (revision / nombre).write_text(contenido, encoding="utf-8")

    # --- Vistas temáticas (capa de caso; contenida: un vistas.yaml inválido NO aborta la
    # corrida ni descarta reg.save(); el fallo se reporta en errores) ---
    try:
        defs = V.cargar_vistas(case_dir)
        salidas, notas = V.render_vistas(mensajes, ident, defs)
        report.notas.extend(notas)
        vistas_dir = out / "vistas"
        if salidas:
            vistas_dir.mkdir(exist_ok=True)
            for nombre, contenido in salidas.items():
                (vistas_dir / nombre).write_text(contenido, encoding="utf-8")
        if vistas_dir.exists():           # poda huérfanos (idempotencia)
            for p in vistas_dir.glob("*.md"):
                if p.name not in salidas:
                    p.unlink()
        report.vistas_generadas = len(salidas)
    except Exception as exc:  # noqa: BLE001 — config de vistas inválida no aborta la atomización
        report.errores.append(f"vistas: {exc}")

    reg.save()
    return report


def _pase_layer_b(reg, mensajes, carriers, report, identidades):
    """Reconstruye autoría inline: segmenta cada portador, atribuye/clasifica, resuelve
    duplicados contra Capa A (upgrade) y acuña IDs fp en orden determinista. Devuelve
    ``(mensajes_b, punteros)``. Idempotente: re-ejecutar no renumera (fp congelados)."""
    idx = INL.indice_layer_a(mensajes)
    por_id = {m.msg_id: m for m in mensajes}
    candidatos = []
    punteros = []
    for m_a, raw in carriers:
        try:
            res = INL.reconstruir(m_a, raw, identidades)
        except Exception as exc:  # noqa: BLE001 — un portador no aborta la corrida
            report.errores.append(f"{m_a.msg_id}: reconstruir inline falló: {exc}")
            continue
        # NUNCA se muta el .md del portador (Capa A byte-idéntica). La intercalada HTML —donde
        # conservadoramente NO segmentamos— se anota en la cola de revisión, no en el portador.
        if res.intercalada:
            punteros.append(SegmentoEnterrado(
                portador_msg_id=m_a.msg_id, estilo="intercalada", confianza="info",
                motivo="intercalada_no_segmentada", extracto=""))
        candidatos.extend(res.candidatos)
        punteros.extend(res.punteros)

    mensajes_b: list[RegistroMensaje] = []
    b_por_fp: dict[str, RegistroMensaje] = {}
    upgrades: list[dict] = []
    for seg in sorted(candidatos, key=lambda s: s.fingerprint):  # orden determinista
        destino = idx.resolver(seg)
        if destino:
            # La cita es copia de menor fidelidad de un mensaje limpio de Capa A. NO se muta
            # ese .md: el cruce se registra en casi_duplicados.md + alias (DD §6).
            upgrades.append({"msg_a": destino, "citado_en": seg.portador_msg_id,
                             "profundidad": seg.profundidad, "fingerprint": seg.fingerprint})
            report.upgrades += 1
            continue
        existente = b_por_fp.get(seg.fingerprint)
        if existente is not None:
            # misma cita reconstruida en otro portador → un solo mensaje B, varias procedencias
            existente.procedencia.append(
                {"citado_en": seg.portador_msg_id, "profundidad": seg.profundidad})
            continue
        seg_msg_id = reg.msg_id_for_fp(seg.fingerprint, cuerpo_sha=seg.cuerpo_sha)
        mb = INL.construir_b(seg, seg_msg_id, por_id[seg.portador_msg_id])
        b_por_fp[seg.fingerprint] = mb
        mensajes_b.append(mb)
    return mensajes_b, punteros, upgrades


def _construir_mensaje(col, reg, apariciones, unicos, report) -> RegistroMensaje:
    sha = compute_sha256_bytes(col.raw)
    msg_id = reg.msg_id_for(col.message_id, sha=sha)
    cab = H.parse_cabeceras(col.raw)
    cuerpo = B.extraer_cuerpo(col.raw)

    _eml, adjuntos = split_eml(col.raw)
    refs: list[AdjuntoRef] = []
    for fn, mime, data in adjuntos:
        att_sha = compute_sha256_bytes(data)
        if A.es_decorativo(data, mime, apariciones):
            report.adjuntos_decorativos += 1
            continue
        att_id = reg.att_id_for(att_sha)
        refs.append(AdjuntoRef(att_id=att_id, msg_id_anidado=None, nombre=fn,
                               tipo=mime, sha256=att_sha))
        u = unicos.get(att_sha)
        if u is None:
            unicos[att_sha] = AdjuntoUnico(
                att_id=att_id, sha256=att_sha, nombre_original=fn, tipo=mime, data=data,
                primera_aparicion=cab.fecha_iso, mensajes=[msg_id], etiquetas=[])
        elif msg_id not in u.mensajes:
            u.mensajes.append(msg_id)

    return RegistroMensaje(
        msg_id=msg_id, rfc_message_id=cab.rfc_message_id, in_reply_to=cab.in_reply_to,
        hilo=cab.hilo, fecha_iso=cab.fecha_iso, hora=cab.hora, fecha_tz=cab.fecha_tz,
        de=cab.de, de_nombre=cab.de_nombre, para=cab.para, cc=cab.cc, cco=[],
        asunto=cab.asunto, eml_origen=col.eml_origen, profundidad=col.profundidad,
        ruta_anidacion=col.ruta_anidacion, procedencia=col.procedencia, capa="A",
        confianza="alta", auth=cab.auth, sha256=sha, adjuntos=refs,
        idioma=_idioma(cuerpo.texto), formato_original=cuerpo.formato_original,
        emisor_dispositivo=cab.emisor_dispositivo, etiquetas=[], fuente="email",
        cuerpo=cuerpo.texto, cuerpo_recortado_cita=cuerpo.cuerpo_recortado_cita,
        respuesta_intercalada=cuerpo.respuesta_intercalada,
        charset_recuperado=cuerpo.charset_recuperado, mojibake_marcado=cuerpo.mojibake_marcado,
        raw=col.raw,
    )


def _escribe_adjunto(out: Path, att: AdjuntoUnico) -> None:
    from core.email_export import _sanea_nombre_fichero
    stem_src = Path(att.nombre_original)
    ext = stem_src.suffix or ""
    slug = _sanea_nombre_fichero(stem_src.stem, fallback="adjunto")
    base = f"{att.primera_aparicion}_{slug}_{att.att_id}"
    (out / "adjuntos" / f"{base}{ext}").write_bytes(att.data)
    ficha_suffix = ".ficha.md" if ext.lower() == ".md" else ".md"
    ficha = (
        f"# GENERADO por core.email_atomize — NO editar.\n\n"
        f"- att_id: {att.att_id}\n- nombre_original: {att.nombre_original}\n"
        f"- tipo: {att.tipo}\n- sha256: {att.sha256}\n"
        f"- primera_aparicion: {att.primera_aparicion}\n"
        f"- mensajes: {', '.join(att.mensajes)}\n- etiquetas: []\n\n"
        f"## Descripción\n\n(pendiente; OCR en fase 2)\n"
    )
    (out / "adjuntos" / f"{base}{ficha_suffix}").write_text(ficha, encoding="utf-8")


def emails_src_dir(case_id: str) -> Path:
    from core.casos.case_locator import path_for, resolve_ref
    return path_for(resolve_ref(case_id)) / "00_Input" / "03_Email"


def emails_out_dir(case_id: str) -> Path:
    from core.casos.case_locator import path_for, resolve_ref
    return path_for(resolve_ref(case_id)) / "01_Procesado" / "Emails"


def atomize_case(case_id: str) -> AtomizeReport:
    return atomize_dir(emails_src_dir(case_id), emails_out_dir(case_id))


def sellar_entrega(out_dir: Path | str, descr: str) -> Path:
    """Sella una entrega del set entregable en <out_dir>/_entregas/. Acción manual."""
    from . import entregas as ENT
    return ENT.sellar(out_dir, descr)
