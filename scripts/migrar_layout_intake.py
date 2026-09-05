"""Migración BAJO DEMANDA de un caso al layout de lotes (spec §7, MEJORAS #54).

Se dispara SOLO cuando el caso recibe un intake nuevo — nunca de oficio ni en
barrido. Envuelve los cajones de entrega en lotes sintéticos y remapea los
registros aguas abajo (M9, cobertura OCR, catálogo). Espejos y protocolo
intactos. Correr TRAS el checkin si el caso estaba prestado.

Los movimientos físicos (fase 1) son todo-o-nada: si cualquier ``shutil.move``
o ``mkdir`` falla a mitad de camino (fichero bloqueado, permiso, disco lleno),
se revierte lo ya movido antes de propagar el error. Ningún borrado ocurre en
fase 1: los ficheros de control duplicados (``03_Email``) se dejan en su sitio
y se listan en ``duplicados_a_borrar``; el ``unlink`` real se hace en fase 2,
tras confirmar que la fase 1 completó entera. Así fase 1 es genuinamente
reversible (rollback = solo movimientos, nunca borrados) y M9/cobertura/
catálogo (también fase 2) solo se tocan si la fase 1 completó entera — una
migración a medias nunca deja los registros aguas abajo apuntando a rutas que
ya no existen, ni borra nada.

**Qué es estado de canal y qué es documento (MEJORAS #149, diseño rev. 2 §3.4).** Lo decide
la UBICACIÓN, no el nombre: ``03_Email/_exported_ids.json`` y ``03_Email/_resolved_links.json``
—directamente bajo el cajón— son estado de canal cuyo hogar desde #54 es la raíz de
``00_Input/``; ``03_Email/hilo/_exported_ids.json`` es un adjunto, se mueve al lote con todo lo
demás y entra en el ``mapping`` M9. El 2026-09-04 una versión que decidía por *basename* borró
un adjunto legítimo homónimo y se revirtió entera.

**La migración no borra lo que no acaba de comparar.** El duplicado de estado de canal solo
se borra si es idéntico por ``sha256`` al de la raíz. Tres comprobaciones, dos de ellas por
hash: en el plan (también con ``--dry-run``; distintos → se aborta antes de mover nada,
nombrando los dos), al empezar a mover (comprobación de EXISTENCIA: si la raíz apareció
entre el plan y la ejecución → se aborta y la fase 1 revierte), y **en el momento del**
``unlink()`` (relectura por hash de ambos: si la raíz ya no existe o difiere → NO se borra y
se reporta; dejar el fichero en su cajón es seguro y no exige rollback).

**Lo que la relectura NO garantiza (R2/H-01):** leer, comparar y borrar son tres operaciones;
un escritor que cambie la raíz entre la relectura y el ``unlink()`` deja borrado un legacy que
ya no es idéntico. La ventana es de milisegundos y no se cierra con más lecturas: se cierra
con el **mutex del caso**, que esta migración adquiere — y que desde ``MEJORAS #126`` (PR #292)
también piden ``export_label_emails``, ``atomize_emails`` y ``sync_sudespacho``; la UI de
Streamlit todavía no.

**Un documento del cliente no puede aterrizar en una ubicación de protocolo (R2/H-02).** Si
un fichero del cajón acabaría, dentro del lote, en una ruta que el registro declara protocolo
(``04_Manual/_manifiesto.yaml`` → ``<lote>/_manifiesto.yaml``), ``escribir_manifiesto`` lo
sobrescribiría con el albarán y la prueba desaparecería. El plan lo detecta y **aborta**
(también en ``--dry-run``), nombrando el fichero: renombrarlo es decisión del operador.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
from pathlib import Path

import typer
import yaml

from core import config, intake_log, intake_lotes, migrar_layout
from core.case_manager import leer_estado_repositorio
from core.config import caso_path
from core.intake_control import es_fichero_de_protocolo
from core.intake_manifest import compute_sha256

app = typer.Typer(add_completion=False)


class CasoPrestadoError(RuntimeError):
    """El caso está prestado/conflicto: migrar tras el checkin (§7.6)."""


class ColisionConProtocoloError(RuntimeError):
    """Un fichero del cajón legacy aterrizaría, dentro del lote, en una ruta que el registro
    declara PROTOCOLO (p. ej. ``04_Manual/_manifiesto.yaml`` → ``<lote>/_manifiesto.yaml``):
    ``escribir_manifiesto`` lo sobrescribiría. Se lanza ANTES de mover nada, también en
    ``--dry-run``. Renombrar el documento es decisión del operador."""


# El alias histórico de esta CLI apunta a la excepción única del helper (MEJORAS #126).
from scripts._mutex_cli import CasoOcupado as CasoOcupadoError  # noqa: E402
from scripts._mutex_cli import sostener as _sostener_cli  # noqa: E402
from scripts._mutex_cli import w_code_de as _w_code_de  # noqa: E402


class EstadoDeCanalDivergenteError(RuntimeError):
    """El cajón legacy y la raíz tienen el mismo fichero de estado de canal con contenido
    DISTINTO: son dos estados de momentos distintos y decidir cuál vale es del operador.
    Se lanza ANTES de mover nada, también en ``--dry-run``."""


def _write_atomico(path: Path, text: str) -> None:
    # Temporal con la forma `._<nombre>.<pid>.tmp`: casa con `intake_control.RAIZ_PREFIJOS`
    # para `_intake_hashes.json`, así un huérfano tampoco es documento (rev. 2 §3.4).
    tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _json_atomico(path: Path, data) -> None:
    _write_atomico(
        path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def _yaml_atomico(path: Path, data) -> None:
    _write_atomico(
        path,
        yaml.dump(data, allow_unicode=True, default_flow_style=False,
                  sort_keys=False))


def _mapping_documental(mov: migrar_layout.MovimientoCajon) -> dict[str, str]:
    """Sub-mapping de ``mov`` sin el estado de canal que se desvía a la raíz de
    ``00_Input/`` y nunca llega al lote. Por (directorio, nombre): el homónimo ANIDADO sí
    va al lote y sí está aquí (rev. 2 §3.4 regla 1)."""
    return {k: v for k, v in mov.mapping.items() if not es_fichero_de_protocolo(k)}


def _estado_de_canal_legacy(base: Path,
                            plan: list[migrar_layout.MovimientoCajon]) -> dict[str, dict]:
    """Decisión por cada fichero de estado de canal directamente bajo un cajón del plan.

    Devuelve ``{"<cajon>/<nombre>": {"accion": "mover" | "duplicado", "sha256": ...}}``.
    Lanza :class:`EstadoDeCanalDivergenteError` si la raíz ya tiene el fichero y difiere.
    """
    decisiones: dict[str, dict] = {}
    for mov in plan:
        cajon_dir = base / mov.cajon
        if not cajon_dir.is_dir():
            continue
        for hijo in sorted(cajon_dir.iterdir()):
            if not hijo.is_file():
                continue
            rel = f"{mov.cajon}/{hijo.name}"
            if not es_fichero_de_protocolo(rel):
                continue
            destino = base / hijo.name
            sha = compute_sha256(hijo)
            if destino.is_file():
                sha_raiz = compute_sha256(destino)
                if sha_raiz != sha:
                    raise EstadoDeCanalDivergenteError(
                        f"Estado de canal divergente: `00_Input/{rel}` (sha256 {sha[:12]}…) y "
                        f"`00_Input/{hijo.name}` (sha256 {sha_raiz[:12]}…) son distintos. No se "
                        "mueve nada: decide cuál vale y retira el otro antes de migrar.")
                decisiones[rel] = {"accion": "duplicado", "sha256": sha}
            else:
                decisiones[rel] = {"accion": "mover", "sha256": sha}
    return decisiones


def _colisiones_con_protocolo(plan: list[migrar_layout.MovimientoCajon]) -> list[str]:
    """Rutas del plan cuyo destino en el lote es una ubicación de protocolo (R2/H-02)."""
    return [
        f"{k} -> {v}" for mov in plan for k, v in sorted(mov.mapping.items())
        if not es_fichero_de_protocolo(k) and es_fichero_de_protocolo(v)
    ]


@contextlib.contextmanager
def _bajo_mutex(case_id: str, *, avisos: list[str] | None = None):
    """Sostiene el mutex del caso durante las fases 1 y 2 (R2/H-01 de MEJORAS #149). Delegado
    en `scripts/_mutex_cli.sostener` (MEJORAS #126): un solo sitio adquiere desde los CLI. Sin
    W-code no hay mutex y se DICE (trinquete E2); ocupado → `CasoOcupadoError` antes de mover."""
    def _avisar(msg: str) -> None:
        if avisos is not None:
            avisos.append(msg)
    with _sostener_cli(_w_code_de(case_id), avisar=_avisar, que="la migración de layout") as s:
        yield s


def migrar(case_id: str, *, dry_run: bool,
           informe: dict | None = None) -> list[migrar_layout.MovimientoCajon]:
    """Migra el caso. ``informe`` (opcional, se rellena) recibe ``estado_de_canal``
    (decisiones del plan), ``duplicados_borrados``, ``no_borrados`` (con motivo) y
    ``avisos``. Las fases 1 y 2 corren bajo el mutex del caso (R2/H-01)."""
    estado = leer_estado_repositorio(case_id)
    if estado in (config.ESTADO_REPO_PRESTADO, config.ESTADO_REPO_CONFLICTO):
        raise CasoPrestadoError(
            f"El caso está '{estado}': la migración se corre tras el checkin "
            "(desviar medio árbol a la bandeja no tiene sentido, spec §7.6).")
    base = caso_path(case_id) / "00_Input"
    plan = migrar_layout.plan_migracion(base)
    # Regla 2 (rev. 2 §3.4): la comparación por hash va EN EL PLAN, también en dry-run, y
    # aborta antes de mover nada si los dos estados de canal difieren.
    decisiones = _estado_de_canal_legacy(base, plan)
    colisiones = _colisiones_con_protocolo(plan)
    if colisiones:
        raise ColisionConProtocoloError(
            "Un documento del cajón aterrizaría en una ubicación de PROTOCOLO del lote y el "
            "albarán lo sobrescribiría. No se mueve nada; renómbralo antes de migrar: "
            + "; ".join(colisiones))
    if informe is not None:
        informe["estado_de_canal"] = decisiones
    if dry_run or not plan:
        return plan
    avisos: list[str] = []
    with _bajo_mutex(case_id, avisos=avisos):
        plan = _migrar_bajo_mutex(case_id, base, plan, decisiones, informe)
    if informe is not None:
        informe["avisos"] = avisos
    return plan


def _migrar_bajo_mutex(case_id: str, base: Path, plan: list[migrar_layout.MovimientoCajon],
                       decisiones: dict[str, dict],
                       informe: dict | None) -> list[migrar_layout.MovimientoCajon]:
    # --- Fase 1: movimientos físicos, todo-o-nada -------------------------
    hechos: list[tuple[Path, Path]] = []
    lotes_creados: list[Path] = []
    mapping_total: dict[str, str] = {}
    duplicados_a_borrar: list[tuple[Path, Path, str]] = []   # (anidado, raíz, sha en el plan)
    try:
        for mov in plan:
            cajon_dir, lote_dir = base / mov.cajon, base / mov.lote
            lote_dir.mkdir(parents=True, exist_ok=False)
            lotes_creados.append(lote_dir)
            for hijo in sorted(cajon_dir.iterdir()):
                rel = f"{mov.cajon}/{hijo.name}"
                if hijo.is_file() and rel in decisiones:
                    # estado de canal → raíz de 00_Input (hogar desde #54), no al lote
                    destino = base / hijo.name
                    if decisiones[rel]["accion"] == "mover":
                        if destino.exists():
                            # Regla 3: apareció entre el plan y la ejecución. Abortar aquí es
                            # barato: la fase 1 es reversible y no se ha borrado nada.
                            raise EstadoDeCanalDivergenteError(
                                f"`00_Input/{hijo.name}` apareció después de planificar la "
                                f"migración; `00_Input/{rel}` no se mueve. Vuelve a lanzar.")
                        shutil.move(str(hijo), str(destino))
                        hechos.append((hijo, destino))
                    else:
                        # ya consolidado en la raíz: el duplicado NO se borra aquí — un
                        # borrado en fase 1 no sería reversible por el rollback. Se borra
                        # en fase 2, solo si la fase 1 completa entera Y sigue idéntico.
                        duplicados_a_borrar.append((hijo, destino, decisiones[rel]["sha256"]))
                    continue
                destino = lote_dir / hijo.name
                shutil.move(str(hijo), str(destino))
                hechos.append((hijo, destino))
            mapping_total.update(_mapping_documental(mov))
    except Exception as exc:
        for src, dst in reversed(hechos):
            try:
                shutil.move(str(dst), str(src))
            except Exception:
                pass    # best-effort: seguimos revirtiendo el resto
        for lote_dir in lotes_creados:
            try:
                if lote_dir.is_dir() and not any(lote_dir.iterdir()):
                    lote_dir.rmdir()
            except Exception:
                pass
        raise RuntimeError(f"Migración abortada y revertida: {exc}") from exc

    # --- Fase 2: borrado de duplicados + manifiestos + remaps + evento ----
    # (solo se ejecuta si la fase 1 completó entera)
    borrados: list[str] = []
    no_borrados: list[dict] = []
    for hijo, destino, sha_plan in duplicados_a_borrar:
        # Regla 4: releer AMBOS en el momento de borrar. Solo se borra lo que acaba de
        # demostrarse idéntico; lo demás se deja en su cajón (seguro, sin rollback) y se dice.
        rel = hijo.relative_to(base).as_posix()
        if not destino.is_file():
            no_borrados.append({"fichero": rel, "motivo": "la raíz ya no tiene el fichero"})
            continue
        sha_hijo, sha_raiz = compute_sha256(hijo), compute_sha256(destino)
        if not (sha_hijo == sha_raiz == sha_plan):
            no_borrados.append({"fichero": rel,
                                "motivo": "el contenido cambió desde el plan (raíz o cajón)"})
            continue
        hijo.unlink()
        borrados.append(rel)
    if informe is not None:
        informe["duplicados_borrados"] = borrados
        informe["no_borrados"] = no_borrados
    for mov in plan:
        lote_dir = base / mov.lote
        intake_lotes.escribir_manifiesto(
            lote_dir, fuente=mov.fuente, fecha_intake=mov.lote[:10],
            origen="migracion_layout",
            items=intake_lotes.items_desde_disco(lote_dir),
            fecha_intake_estimada=True)

    remapeados: dict[str, int] = {}
    m9_path = base / "_intake_hashes.json"
    if m9_path.is_file():
        data = json.loads(m9_path.read_text(encoding="utf-8") or "{}")
        data, remapeados["m9"] = migrar_layout.remap_paths(data, mapping_total)
        _json_atomico(m9_path, data)
    cob_path = (caso_path(case_id) / "01_Procesado" / "02_Sala de máquina"
                / "_cobertura.json")
    if cob_path.is_file():
        rows = json.loads(cob_path.read_text(encoding="utf-8") or "[]")
        rows, remapeados["cobertura"] = migrar_layout.remap_cobertura(rows, mapping_total)
        _json_atomico(cob_path, rows)
    cat_path = caso_path(case_id) / "01_Procesado" / "indice_documental.yaml"
    if cat_path.is_file():
        entries = yaml.safe_load(cat_path.read_text(encoding="utf-8")) or []
        entries, remapeados["catalogo"] = migrar_layout.remap_catalogo(
            entries, mapping_total)
        _yaml_atomico(cat_path, entries)

    intake_log.append_event(case_id, "migracion_layout_intake", details={
        "lotes": [m.lote for m in plan], "remapeados": remapeados,
        "duplicados_borrados": borrados, "no_borrados": no_borrados})
    return plan


@app.command()
def main(case_id: str, dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    informe: dict = {}
    try:
        plan = migrar(case_id, dry_run=dry_run, informe=informe)
    except CasoPrestadoError as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)
    except CasoOcupadoError as exc:
        # Código 2 y cero bytes, como el resto de abortos por mutex de este repo.
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=2)
    except Exception as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)
    for aviso in informe.get("avisos", []):
        typer.echo(aviso, err=True)
    if not plan:
        typer.echo("Nada que migrar: sin cajones de entrega con contenido.")
        return
    for mov in plan:
        n_docs = len(_mapping_documental(mov))
        typer.echo(f"{'[dry-run] ' if dry_run else ''}{mov.cajon} → {mov.lote} "
                   f"({n_docs} ficheros)")
    for rel, d in informe.get("estado_de_canal", {}).items():
        typer.echo(f"{'[dry-run] ' if dry_run else ''}estado de canal {rel}: {d['accion']}")
    for rel in informe.get("duplicados_borrados", []):
        typer.echo(f"borrado el duplicado {rel} (idéntico a la raíz, verificado al borrar)")
    for item in informe.get("no_borrados", []):
        typer.echo(f"[AVISO] NO borrado {item['fichero']}: {item['motivo']}", err=True)


if __name__ == "__main__":
    app()
