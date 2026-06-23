"""Re-fecha los anexos de WhatsApp de una Sala lectura con la fecha de ENVÍO.

Aplica la regla v1.5 de `organizar-sala-lectura`: cada anexo de un bundle de
WhatsApp lleva el `AAAA-MM-DD` del mensaje del `_chat.txt` que lo adjunta (no la
fecha de la carpeta madre). La carpeta y el principal (.txt) conservan la fecha
del chat. Determinista e idempotente. Empareja por el SEQ de 8 dígitos
(`00000NNN-...`) presente en el nombre del export y en la referencia del chat.

Uso:
    python -m scripts.redate_whatsapp_anexos "<ruta Sala lectura>"          # dry-run
    python -m scripts.redate_whatsapp_anexos "<ruta Sala lectura>" --apply  # ejecuta

Tras --apply, regenera el indice_documental.yaml:
    python .claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py \
        "<...>/_MANIFIESTO.md" "<...>/indice_documental.yaml"
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from core.whatsapp_export import parse_chat

_COLS = ["sha256", "ruta_original", "nombre_canonico", "tipo", "fecha", "parte", "parent_id"]
_RE_FECHA_PREFIJO = re.compile(r"^\d{4}-\d{2}-\d{2}")
_RE_SEQ = re.compile(r"^(\d{8})-")
# `<adjunto: ...>` en CUALQUIER posición del mensaje. El core lo ancla a inicio de línea,
# por lo que se pierde en los documentos que WhatsApp exporta con preámbulo
# (`nombre.PDF • 34 páginas <adjunto: 00000017-...>`). Aquí lo buscamos sin anclar.
_RE_ADJ_ANY = re.compile(r"<adjunto:\s*(.+?)>", re.IGNORECASE)


def _seq(basename: str) -> str | None:
    m = _RE_SEQ.match(basename)
    return m.group(1) if m else None


def _parse_filas(texto: str) -> list[list[str]]:
    """Devuelve las filas de datos como listas de celdas (preserva orden y formato)."""
    filas = []
    for line in texto.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            filas.append(None)  # línea no-tabla; marcador para reconstruir
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        filas.append(celdas)
    return filas


def _mapa_envio(chat_txt: Path) -> dict[str, str]:
    """seq8 -> fecha de envío (AAAA-MM-DD) leída del _chat.txt."""
    msgs = parse_chat(chat_txt.read_text(encoding="utf-8", errors="replace"))
    mapa: dict[str, str] = {}
    for m in msgs:
        if m.timestamp is None:
            continue
        fecha = m.timestamp.date().isoformat()
        # iOS sin anclar (cubre documentos con preámbulo) + el adjunto_ref del core (Android).
        refs = list(_RE_ADJ_ANY.findall(m.texto))
        if m.adjunto_ref and m.adjunto_ref not in ("<archivo adjunto>", "<Media omitted>"):
            refs.append(m.adjunto_ref)
        for ref in refs:
            seq = _seq(ref.strip())
            if seq:
                mapa[seq] = fecha
    return mapa


def procesar(sala: Path, apply: bool) -> int:
    manifiesto = sala / "_MANIFIESTO.md"
    texto = manifiesto.read_text(encoding="utf-8")
    lineas = texto.splitlines(keepends=True)

    # Índice de la cabecera de columnas para localizar filas de datos.
    filas_celdas: list[list[str] | None] = []
    for ln in lineas:
        s = ln.strip()
        if s.startswith("|"):
            filas_celdas.append([c.strip() for c in s.strip("|").split("|")])
        else:
            filas_celdas.append(None)

    # Cache de mapas de envío por bundle.
    cache: dict[str, dict[str, str]] = {}
    cambios = 0
    sin_match: list[str] = []
    renombrados: list[tuple[Path, Path]] = []

    for i, celdas in enumerate(filas_celdas):
        if not celdas or len(celdas) != len(_COLS):
            continue
        fila = dict(zip(_COLS, celdas))
        if fila["sha256"] in ("sha256",) or set(fila["sha256"]) <= {"-"}:
            continue
        parent = fila["parent_id"]
        nombre_canonico = fila["nombre_canonico"]
        # Solo anexos de bundles de WhatsApp.
        if not parent or "whatsapp" not in parent.lower() or "_anexo_" not in nombre_canonico:
            continue

        seq = _seq(Path(fila["ruta_original"]).name)
        if not seq:
            continue

        # Mapa de envío del chat de este bundle.
        if parent not in cache:
            chat_txt = sala / parent / f"{parent}.txt"
            if not chat_txt.exists():
                # busca cualquier .txt dentro de la carpeta del bundle
                cand = list((sala / parent).glob("*.txt"))
                chat_txt = cand[0] if cand else chat_txt
            cache[parent] = _mapa_envio(chat_txt) if chat_txt.exists() else {}

        fecha_envio = cache[parent].get(seq)
        if not fecha_envio:
            sin_match.append(f"{parent}/{Path(nombre_canonico).name} (seq {seq})")
            continue

        nombre_actual = Path(nombre_canonico).name
        if nombre_actual[:10] == fecha_envio:
            continue  # idempotente: ya está

        nombre_nuevo = _RE_FECHA_PREFIJO.sub(fecha_envio, nombre_actual, count=1)
        canonico_nuevo = f"{parent}/{nombre_nuevo}"

        ruta_vieja = sala / parent / nombre_actual
        ruta_nueva = sala / parent / nombre_nuevo

        cambios += 1
        print(f"  {nombre_actual[:10]} -> {fecha_envio}  {nombre_nuevo}")

        if apply:
            if ruta_vieja.exists():
                ruta_vieja.rename(ruta_nueva)
                renombrados.append((ruta_vieja, ruta_nueva))
            # Reescribe la celda fecha y nombre_canonico en la línea original.
            celdas[_COLS.index("fecha")] = fecha_envio
            celdas[_COLS.index("nombre_canonico")] = canonico_nuevo
            lineas[i] = "| " + " | ".join(celdas) + " |\n"

    print(f"\nTotal anexos a re-fechar: {cambios}")
    if sin_match:
        print(f"SIN match en el chat ({len(sin_match)}) — se dejan como están:")
        for s in sin_match:
            print(f"  - {s}")

    if apply and cambios:
        manifiesto.write_text("".join(lineas), encoding="utf-8")
        print(f"\n_MANIFIESTO.md actualizado ({len(renombrados)} ficheros renombrados).")
    return 0


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    apply = "--apply" in argv
    if not args:
        print(__doc__)
        return 2
    sala = Path(args[0])
    if not (sala / "_MANIFIESTO.md").exists():
        print(f"No encuentro _MANIFIESTO.md en {sala}")
        return 1
    print(f"{'APLICANDO' if apply else 'DRY-RUN'} sobre: {sala}\n")
    return procesar(sala, apply)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
