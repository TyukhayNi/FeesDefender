#!/usr/bin/env python
"""pre-commit leak-guard — bloquea capturas de depuración y PII en contenido.

Complementa a gitleaks (secretos) y check-added-large-files (tamaño). Cubre lo que
esos no ven, en tres capas:
  1. Rutas de captura vetadas (RUTAS_VETADAS) — defensa sobre el .gitignore.
  2. PII por VALOR (`escanear`): nombres/emails REALES de terceros desde una
     blocklist gitignored. Denylist: solo caza lo enumerado.
  3. PII por FORMA (`escanear_formas`): identificadores estructurados de CUALQUIER
     caso — DNI/NIE/IBAN bloquean, email de tercero avisa. Generaliza a expedientes
     que nadie ha listado aún; reutiliza los patrones canónicos de core/anon.

Doctrina y encaje: docs/SEGURIDAD_DATOS.md (principios 2, 5, 7).

Diseño anti-falsos-positivos: la lista de PII a detectar se lee de artefactos
GITIGNORED que ya existen (`data/_saneado/replacements.txt`, opcional
`data/_config/pii_blocklist.txt`) — así los nombres reales nunca entran en un
fichero versionado, ni siquiera en este hook. El match usa límite de palabra
(un término no salta si va pegado a más letras, para no marcar prefijos). Si no hay lista, la
guarda sigue haciendo el bloqueo de rutas + tamaño (vía los otros hooks).

Dónde se busca la lista (`MEJORAS #161`, 2026-09-05). Por estar gitignored, un worktree
recién creado NO tiene ninguno de los dos ficheros, y el flujo estándar del repo es el
worktree: durante meses el hook pasó en verde sin haber comprobado nada, hasta que una
dirección de inmueble llegó a GitHub con el pre-commit en verde. Desde entonces la lista se
resuelve en DOS raíces: el árbol que se está commiteando y la RAÍZ COMÚN del repositorio
(`git rev-parse --git-common-dir`, el checkout principal que sí conserva los gitignored). Se
unen los términos de ambas. Y si aun así la lista sale VACÍA, `main` lo dice en STDERR con
las rutas que buscó: un guard que no puede mirar tiene que declararlo, no callar. Sigue sin
fallar cerrado — esa tercera vía queda para cuando no encontrar la lista sea una anomalía y
no el caso normal.

Uso (lo invoca pre-commit con los ficheros staged como argv):
    python scripts/precommit_leak_guard.py <fichero> [<fichero> ...]
Sale 1 si encuentra algo (con detalle), 0 si está limpio.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_DEFECTO = Path(__file__).resolve().parent.parent

# Artefactos gitignored de los que se lee la blocklist, relativos a cada raíz.
_REL_REPLACEMENTS = Path("data") / "_saneado" / "replacements.txt"
_REL_BLOCKLIST = Path("data") / "_config" / "pii_blocklist.txt"

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


def _raiz_comun(repo: Path) -> Path | None:
    """Checkout principal del repositorio al que pertenece `repo`, o None.

    En un worktree, `git rev-parse --git-common-dir` devuelve el `.git` COMPARTIDO (el del
    checkout principal), y su padre es la raíz que conserva los ficheros gitignored. En el
    propio checkout principal devuelve `.git` y el padre es `repo`: se responde None para no
    leer la misma raíz dos veces. Sin git, o fuera de un repositorio, None: el guard no
    debe romperse por no poder preguntar — pero tampoco debe fingir que preguntó, y por eso
    `rutas_blocklist` no incluirá ninguna raíz común en ese caso.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(repo),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    git_dir = out.stdout.strip()
    if not git_dir:
        return None
    comun = (repo / git_dir).resolve().parent
    if comun == repo.resolve():
        return None
    return comun


def raices_blocklist(repo: Path) -> list[Path]:
    """Raíces donde se busca la blocklist, en orden: el árbol dado y, si es distinto, el
    checkout principal del repositorio (`MEJORAS #161`)."""
    raices = [repo]
    comun = _raiz_comun(repo)
    if comun is not None:
        raices.append(comun)
    return raices


def rutas_blocklist(repo: Path) -> list[Path]:
    """Todas las rutas concretas donde se ha buscado la blocklist (existan o no). Es lo que
    el aviso imprime cuando la lista sale vacía, para que quien lo lea sepa qué faltó."""
    rutas: list[Path] = []
    for raiz in raices_blocklist(repo):
        rutas.append(raiz / _REL_REPLACEMENTS)
        rutas.append(raiz / _REL_BLOCKLIST)
    return rutas


def _leer_terminos(raiz: Path, terms: set[str]) -> None:
    repl = raiz / _REL_REPLACEMENTS
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

    bl = raiz / _REL_BLOCKLIST
    if bl.exists():
        for line in bl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and len(line) >= _TERM_MIN:
                terms.add(line)


def cargar_blocklist(repo: Path) -> list[str]:
    """Términos sensibles desde artefactos gitignored, unión de todas las raíces de
    `raices_blocklist` (el árbol dado + el checkout principal si es un worktree). Vacío si
    no hay ninguno en ninguna — y entonces `main` lo declara en STDERR."""
    terms: set[str] = set()
    for raiz in raices_blocklist(repo):
        _leer_terminos(raiz, terms)
    # Los más largos primero: match más específico y mensajes más útiles.
    return sorted(terms, key=len, reverse=True)


def aviso_blocklist_vacia(repo: Path) -> str:
    """Texto del aviso cuando no hay blocklist: dice qué NO se comprobó y dónde se buscó."""
    lineas = [
        "leak-guard AVISO — blocklist VACÍA: la comprobación de PII por VALOR (nombres, "
        "emails, direcciones de la lista) NO se ha ejecutado. Este verde no la acredita.",
        "  Rutas buscadas:",
    ]
    for ruta in rutas_blocklist(repo):
        lineas.append(f"    - {ruta}")
    lineas.append(
        "  Remedio: la lista vive en el checkout principal (gitignored); si esto es un worktree "
        "y aun así falta, el checkout principal tampoco la tiene. Ver docs/SEGURIDAD_DATOS.md "
        "y MEJORAS #161."
    )
    return "\n".join(lineas)


def _es_binario(data: bytes) -> bool:
    return b"\x00" in data[:4096]


# ── Detección por FORMA (no por valor) ───────────────────────────────────────
# La blocklist es una denylist: solo caza PII enumerada. Esto generaliza a
# identificadores estructurados de CUALQUIER caso (DNI/NIE/NIF/IBAN = bloqueo,
# email de tercero = aviso), reutilizando los patrones canónicos de core/anon.

def _patrones_forma():
    """(shapes bloqueantes de UNA línea, patrón de email). Reutiliza core/anon;
    fallback a copias mínimas si el import no está disponible (CI mínimo)."""
    try:
        if str(REPO_DEFECTO) not in sys.path:
            sys.path.insert(0, str(REPO_DEFECTO))
        from core.anon.anonimizar import PATRONES_REGEX_COMPILADOS  # type: ignore

        # NIF/CIF fuera: es dato público de registro mercantil (p. ej. el CIF de
        # la clienta E&V vive legítimamente en core/config). Bloqueamos identificadores
        # de persona física + IBAN.
        shapes = [
            (t, rx)
            for rx, t in PATRONES_REGEX_COMPILADOS
            if t in {"DNI", "NIE", "IBAN"} and "\n" not in rx.pattern
        ]
        email = next((rx for rx, t in PATRONES_REGEX_COMPILADOS if t == "EMAIL"), None)
        if shapes and email is not None:
            return shapes, email
    except Exception:
        pass
    # Fallback inline — mantener en sync con core/anon PATRONES_REGEX.
    shapes = [
        ("IBAN", re.compile(r"\bES\s*\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{2}[\s]?\d{10}\b", re.I)),
        ("DNI", re.compile(r"\b\d{8}[A-ZÁÉÍÓÚÜÑ]\b", re.I)),
        ("NIE", re.compile(r"\b[XYZ]\d{7}[A-ZÁÉÍÓÚÜÑ]\b", re.I)),
    ]
    email = re.compile(r"[\w.+-]+\s*@\s*[\w-]+(?:\s*\.\s*[\w]+)+")
    return shapes, email


_SHAPES, _EMAIL_RX = _patrones_forma()
_ALLOW = "leak-guard:allow"  # anotación de exención por línea (valor sintético legítimo)


def _email_inerte(e: str) -> bool:
    """Placeholders inertes (docs/tests): example.* / *.invalid — no son PII."""
    e = re.sub(r"\s+", "", e).lower()
    return (
        e.endswith(".example")
        or e.endswith(".invalid")
        or e.endswith("@example.com")
        or e.endswith("@example.org")
        or e.endswith("@example.net")
    )


def escanear_formas(paths: list[str], repo: Path = REPO_DEFECTO) -> tuple[list[str], list[str]]:
    """PII por forma. Devuelve (bloqueos, avisos).

    - bloqueos: DNI/NIE/NIF/IBAN — identificadores estructurados de cualquier caso.
    - avisos:   emails de tercero (no inertes) — surfacea, no bloquea.

    Se saltan las zonas curadas con ejemplos sintéticos (`tests/`, `docs/`,
    `.claude/`, ficheros `*.example`) y cualquier línea con la anotación
    `leak-guard:allow`. El bloqueo muerde donde caen los dumps reales (raíz,
    `scripts/`, `core/`, `data/` no ignorado, app).
    """
    bloqueos: list[str] = []
    avisos: list[str] = []
    for raw in paths:
        p = _norm(raw)
        # Excepción a la exención de docs/: el atlas del CRM es GENERADO desde datos
        # del tenant → SÍ se escanea (un enum puede traer email del personal; el
        # gate del generador es la barrera dura, esto es la red del hook).
        _es_atlas_crm = "docs/crm_atlas/" in p or p.endswith("docs/CRM_SUDESPACHO_ATLAS.md")
        if not _es_atlas_crm and (
            re.search(r"(^|/)(tests|docs|\.claude)/", p) or p.endswith(".example")
        ):
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
        for linea in data.decode("utf-8", errors="replace").splitlines():
            if _ALLOW in linea:
                continue
            for tipo, rx in _SHAPES:
                m = rx.search(linea)
                if m:
                    bloqueos.append(f"PII POR FORMA ({tipo}): '{m.group().strip()}' en {p}")
            for m in _EMAIL_RX.finditer(linea):
                if not _email_inerte(m.group()):
                    avisos.append(f"EMAIL DE TERCERO (aviso): '{m.group().strip()}' en {p}")
    return bloqueos, avisos


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
    if not cargar_blocklist(repo):
        # MEJORAS #161: el guard sin lista no refuta nada. Lo dice, y sigue (rutas + formas).
        print(aviso_blocklist_vacia(repo), file=sys.stderr)
        print("", file=sys.stderr)
    bloqueos = escanear(paths, repo)
    bloqueos_forma, avisos = escanear_formas(paths, repo)
    bloqueos += bloqueos_forma

    if avisos:
        print("leak-guard AVISO — posible PII (no bloquea, revísalo):", file=sys.stderr)
        for a in avisos:
            print(f"  ⚠ {a}", file=sys.stderr)
        print("", file=sys.stderr)

    if not bloqueos:
        return 0
    print("leak-guard BLOQUEA el commit/push — posible fuga de datos:\n", file=sys.stderr)
    for pr in bloqueos:
        print(f"  ✗ {pr}", file=sys.stderr)
    print(
        "\nSaca el dato del árbol versionado (guía: docs/SEGURIDAD_DATOS.md).\n"
        "Si es un valor sintético legítimo, anota la línea con 'leak-guard:allow'.\n"
        "Si es un falso positivo justificado, --no-verify lo salta (queda a tu criterio).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
