#!/usr/bin/env python
"""pre-commit leak-guard — bloquea capturas de depuración y PII en contenido.

Complementa a gitleaks (secretos) y check-added-large-files (tamaño). Cubre lo que
esos no ven: rutas de captura vetadas y nombres/emails REALES de terceros en el
contenido de ficheros de texto.

Doctrina y encaje: docs/SEGURIDAD_DATOS.md (principios 2, 5, 7).

Diseño anti-falsos-positivos: la lista de PII a detectar se lee de artefactos
GITIGNORED que ya existen (`data/_saneado/replacements.txt`, opcional
`data/_config/pii_blocklist.txt`) — así los nombres reales nunca entran en un
fichero versionado, ni siquiera en este hook. El match usa límite de palabra
(un término no salta si va pegado a más letras, para no marcar prefijos). Si no hay lista, la
guarda sigue haciendo el bloqueo de rutas + tamaño (vía los otros hooks).

Uso (lo invoca pre-commit con los ficheros staged como argv):
    python scripts/precommit_leak_guard.py <fichero> [<fichero> ...]
Sale 1 si encuentra algo (con detalle), 0 si está limpio.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_DEFECTO = Path(__file__).resolve().parent.parent

# Rutas cuyo contenido es tóxico por defecto (capturas, PII, prueba real). Defensa
# sobre el .gitignore: bloquea incluso un `git add -f`.
RUTAS_VETADAS = [
    re.compile(r"(^|/)docs/_descubrimiento/"),
    re.compile(r"(^|/)data/_audit/"),
    re.compile(r"(^|/)data/_saneado/"),
    re.compile(r"(^|/)data/CASOS/"),
    re.compile(r"\.har$", re.IGNORECASE),
]

_TERM_MIN = 4  # términos más cortos generan ruido/falsos positivos


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _limpiar_regex_lhs(lhs: str) -> str:
    """De una regla `regex:(?i)(?<![\\w])Nombre\\ Apellido(?![\\w@])` saca 'Nombre Apellido'."""
    lhs = lhs[len("regex:"):]
    lhs = re.sub(r"^\(\?i\)", "", lhs)
    lhs = re.sub(r"\(\?<!\[\\w\]\)", "", lhs)
    lhs = re.sub(r"\(\?!\[\\w@?\]\)$", "", lhs)
    return lhs.replace(r"\ ", " ").strip()


def cargar_blocklist(repo: Path) -> list[str]:
    """Términos sensibles desde artefactos gitignored. Vacío si no hay ninguno."""
    terms: set[str] = set()

    repl = repo / "data" / "_saneado" / "replacements.txt"
    if repl.exists():
        for line in repl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or "==>" not in line:
                continue
            lhs = line.split("==>", 1)[0].strip()
            if lhs.startswith("regex:"):
                lhs = _limpiar_regex_lhs(lhs)
            if len(lhs) >= _TERM_MIN:
                terms.add(lhs)

    bl = repo / "data" / "_config" / "pii_blocklist.txt"
    if bl.exists():
        for line in bl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and len(line) >= _TERM_MIN:
                terms.add(line)

    # Los más largos primero: match más específico y mensajes más útiles.
    return sorted(terms, key=len, reverse=True)


def _es_binario(data: bytes) -> bool:
    return b"\x00" in data[:4096]


def escanear(paths: list[str], repo: Path = REPO_DEFECTO) -> list[str]:
    problemas: list[str] = []
    blocklist = cargar_blocklist(repo)
    patrones = [
        (t, re.compile(r"(?<![\w])" + re.escape(t) + r"(?![\w@])", re.IGNORECASE))
        for t in blocklist
    ]
    for raw in paths:
        p = _norm(raw)
        if any(rx.search(p) for rx in RUTAS_VETADAS):
            problemas.append(f"RUTA VETADA: {p} (captura/PII/prueba real — no se versiona)")
            continue
        fp = repo / raw
        if not fp.is_file():
            continue
        try:
            data = fp.read_bytes()
        except OSError:
            continue
        if _es_binario(data):
            continue
        texto = data.decode("utf-8", errors="replace")
        for termino, rx in patrones:
            if rx.search(texto):
                problemas.append(f"PII EN CONTENIDO: '{termino}' aparece en {p}")
    return problemas


def main(argv: list[str], repo: Path = REPO_DEFECTO) -> int:
    paths = argv[1:]
    if not paths:
        return 0
    problemas = escanear(paths, repo)
    if not problemas:
        return 0
    print("leak-guard BLOQUEA el commit/push — posible fuga de datos:\n", file=sys.stderr)
    for pr in problemas:
        print(f"  ✗ {pr}", file=sys.stderr)
    print(
        "\nSaca el dato del árbol versionado (guía: docs/SEGURIDAD_DATOS.md).\n"
        "Si es un falso positivo justificado, --no-verify lo salta (queda a tu criterio).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
