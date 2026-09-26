#!/usr/bin/env python
"""pre-commit leak-guard — bloquea capturas de depuración y PII en contenido.

Complementa a gitleaks (secretos) y check-added-large-files (tamaño). Cubre lo que
esos no ven, en tres capas:
  1. Rutas de captura vetadas (RUTAS_VETADAS) — defensa sobre el .gitignore.
  2. PII por VALOR (`escanear`): nombres/emails REALES de terceros desde una
     blocklist gitignored. Denylist: solo caza lo enumerado.
  3. PII por FORMA (`escanear_formas`): identificadores estructurados de CUALQUIER
     caso — DNI/NIE/IBAN bloquean, email de tercero avisa; el NIF/CIF societario queda
     FUERA a propósito (dato público de registro). Generaliza a expedientes que nadie
     ha listado aún; reutiliza los patrones canónicos de core/anon.

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
resuelve en DOS raíces: el árbol que se está commiteando y el CHECKOUT PRINCIPAL del mismo
repositorio (el primero de `git worktree list`, que sí conserva los gitignored), y se unen
los términos de ambas. El principal se acepta SOLO verificado por resultado: tiene que ser
un árbol de trabajo cuyo `--git-common-dir` sea el mismo que el nuestro. Un `.git` separado
(`--separate-git-dir`), un bare o un submódulo no pasan esa verificación, y entonces el
principal queda «no determinado» y se dice — nunca se lee la carpeta padre de unos metadatos
como si fuera un checkout (R1/H-02). La consulta a git ignora `GIT_DIR` y compañía del
entorno: el repositorio lo fija el árbol que se revisa, no una variable heredada.

La resolución ocurre UNA vez por invocación (`resolver_blocklist`) y ese mismo objeto sirve
para escanear y para el aviso (R1/H-03). Si la lista sale VACÍA, `main` lo dice en STDERR
con cada ruta buscada y su estado real —no existe / existe sin términos utilizables— y con
si el principal se resolvió o no (R1/H-04): un guard que no puede mirar tiene que declararlo,
sin afirmar causas que no comprobó. Y si la lista NO está vacía pero el principal no se pudo
determinar —git falló al consultarlo, o no es un árbol verificable—, lo dice igual: la lista es
PARCIAL, y los términos que vivan solo en el principal no se han mirado (R1/H-01 de «git que falla
en voz alta», 2026-09-26: hasta entonces solo se declaraba la vacía, y un worktree con un solo
término propio escaneaba con la mitad en silencio). Para que ese aviso llegue a quien commitea, el hook va
con `verbose: true` en `.pre-commit-config.yaml`: pre-commit solo muestra la salida de un
hook que devuelve 0 si el hook es verbose (R1/H-01). Sigue sin fallar cerrado — esa tercera
vía queda para cuando no encontrar la lista sea una anomalía y no el caso normal.

Uso (lo invoca pre-commit con los ficheros staged como argv):
    python scripts/precommit_leak_guard.py <fichero> [<fichero> ...]
Sale 1 si encuentra algo (con detalle), 0 si está limpio.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_DEFECTO = Path(__file__).resolve().parent.parent

# Artefactos gitignored de los que se lee la blocklist, relativos a cada raíz.
_REL_REPLACEMENTS = Path("data") / "_saneado" / "replacements.txt"
_REL_BLOCKLIST = Path("data") / "_config" / "pii_blocklist.txt"

# Variables con las que el entorno puede redirigir a git a OTRO repositorio. Se quitan al
# consultar: el repositorio lo fija `cwd=repo`, que es el árbol que se está revisando.
_ENV_GIT_REDIRIGE = ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")

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

#: Cabeceras de los dos avisos de la blocklist. Constantes, para que los tests no copien la frase
#: (un negativo contra un literal se vacía si el texto cambia).
AVISO_VACIA = "leak-guard AVISO — blocklist VACÍA"
AVISO_PARCIAL = "leak-guard AVISO — blocklist PARCIAL"


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _limpiar_regex_lhs(lhs: str) -> str:
    """De una regla `regex:(?i)(?<![\\w])Nombre\\ Apellido(?![\\w@])` saca 'Nombre Apellido'."""
    lhs = lhs[len("regex:"):]
    lhs = re.sub(r"^\(\?i\)", "", lhs)
    lhs = re.sub(r"\(\?<!\[\\w\]\)", "", lhs)
    lhs = re.sub(r"\(\?!\[\\w@?\]\)$", "", lhs)
    return lhs.replace(r"\ ", " ").strip()


def _git(repo: Path, *args: str) -> str | None:
    """Salida de `git <args>` con `cwd=repo`, o None si git no está, falla o tarda. El
    entorno se limpia de las variables que redirigen a otro repositorio (R1/P1)."""
    env = {k: v for k, v in os.environ.items() if k not in _ENV_GIT_REDIRIGE}
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            env=env,
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
    return out.stdout


def _resolver_principal(repo: Path) -> tuple[Path | None, str, bool]:
    """(checkout principal, motivo, ¿determinado?). El principal es el PRIMER árbol de
    `git worktree list` —así lo documenta git—, aceptado solo si se verifica por resultado: es
    un árbol de trabajo distinto de `repo` y comparte `--git-common-dir` con él. Todo lo que no
    pase esa verificación devuelve None con el motivo, para que el aviso diga lo que pasó y no
    lo que se supone (R1/H-02, H-04).

    «Determinado» dice si se SABE qué otra raíz hay que leer, y cada salida lo declara: lo está
    si se resolvió, si este árbol ya es el principal y si el repositorio es bare (no hay otra).
    Todo lo demás es «no se pudo saber», y con términos locales deja la lista PARCIAL, que `main`
    declara (R1/H-01 de «git que falla en voz alta»).
    """
    comun_propio = _git(repo, "rev-parse", "--git-common-dir")
    if comun_propio is None:
        return None, "no se pudo consultar git desde este árbol (¿sin git, fuera de un repo?)", False
    listado = _git(repo, "worktree", "list", "--porcelain")
    if listado is None:
        return None, "git worktree list falló", False
    lineas = listado.splitlines()
    if not lineas or not lineas[0].startswith("worktree "):
        return None, "git worktree list no devolvió ningún árbol", False
    if len(lineas) > 1 and lineas[1].strip() == "bare":
        return None, "el repositorio es bare: no hay checkout principal", True
    candidato = Path(lineas[0][len("worktree "):].strip())
    try:
        if candidato.resolve() == repo.resolve():
            return None, "este árbol ES el checkout principal", True
    except OSError:
        return None, f"no se pudo resolver la ruta {candidato}", False
    toplevel = _git(candidato, "rev-parse", "--show-toplevel")
    comun_cand = _git(candidato, "rev-parse", "--git-common-dir")
    if toplevel is None or comun_cand is None:
        return None, (f"{candidato} no es un árbol de trabajo consultable (¿.git separado, "
                      "submódulo?)"), False
    try:
        if Path(toplevel.strip()).resolve() != candidato.resolve():
            return None, f"{candidato} no es la raíz de un árbol de trabajo", False
        if (candidato / comun_cand.strip()).resolve() != (repo / comun_propio.strip()).resolve():
            return None, f"{candidato} pertenece a otro repositorio", False
    except OSError:
        return None, f"no se pudo resolver la ruta {candidato}", False
    return candidato, f"resuelto: {candidato}", True


def _leer_terminos(raiz: Path) -> list[tuple[Path, str, set[str]]]:
    """Por cada artefacto de `raiz`: (ruta, estado observado, términos utilizables)."""
    out: list[tuple[Path, str, set[str]]] = []

    repl = raiz / _REL_REPLACEMENTS
    terms: set[str] = set()
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
        out.append((repl, _estado(terms), terms))
    else:
        out.append((repl, "no existe", terms))

    bl = raiz / _REL_BLOCKLIST
    terms = set()
    if bl.exists():
        for line in bl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and len(line) >= _TERM_MIN:
                terms.add(line)
        out.append((bl, _estado(terms), terms))
    else:
        out.append((bl, "no existe", terms))
    return out


def _estado(terms: set[str]) -> str:
    if terms:
        return f"existe, {len(terms)} términos"
    return f"existe, 0 términos utilizables (vacío, comentarios o más cortos de {_TERM_MIN})"


@dataclass(frozen=True)
class Blocklist:
    """Resultado de UNA resolución de la blocklist: lo que se leyó y de dónde. El mismo
    objeto sirve para escanear y para el aviso, así los dos describen la misma carga
    (R1/H-03)."""

    terminos: list[str]                 # más largos primero
    raices: list[Path]                  # árbol dado y, si se resolvió, el principal
    rutas: list[tuple[Path, str]]       # (ruta buscada, estado observado)
    principal: str                      # cómo acabó la resolución del checkout principal
    # ¿Se sabe qué otra raíz había que leer? Por defecto NO: una Blocklist construida sin decirlo
    # no se da por completa (R1/H-01 de «git que falla en voz alta»).
    principal_determinado: bool = False


def resolver_blocklist(repo: Path) -> Blocklist:
    """Términos sensibles desde artefactos gitignored, unión del árbol dado y del checkout
    principal si es un worktree (`MEJORAS #161`). Consulta git una sola vez por invocación."""
    raices = [repo]
    principal, motivo, determinado = _resolver_principal(repo)
    if principal is not None:
        raices.append(principal)
    terms: set[str] = set()
    rutas: list[tuple[Path, str]] = []
    for raiz in raices:
        for ruta, estado, encontrados in _leer_terminos(raiz):
            rutas.append((ruta, estado))
            terms |= encontrados
    # Los más largos primero: match más específico y mensajes más útiles.
    return Blocklist(sorted(terms, key=len, reverse=True), raices, rutas, motivo, determinado)


def cargar_blocklist(repo: Path) -> list[str]:
    """Solo los términos. Vacío si no hay ninguno en ninguna raíz — y entonces `main` lo
    declara en STDERR."""
    return resolver_blocklist(repo).terminos


def raices_blocklist(repo: Path) -> list[Path]:
    """Raíces donde se busca la blocklist: el árbol dado y, si se resolvió, el principal."""
    return resolver_blocklist(repo).raices


def rutas_blocklist(repo: Path) -> list[Path]:
    """Las rutas concretas donde se ha buscado la blocklist (existan o no)."""
    return [ruta for ruta, _ in resolver_blocklist(repo).rutas]


def aviso_blocklist_vacia(bl: Blocklist) -> str:
    """Texto del aviso cuando la lista salió vacía: qué NO se comprobó, dónde se buscó y qué
    se encontró en cada sitio. Solo afirma lo observado (R1/H-04)."""
    lineas = [
        f"{AVISO_VACIA}: la comprobación de PII por VALOR (nombres, "
        "emails, direcciones de la lista) NO se ha ejecutado. Este verde no la acredita.",
        f"  Checkout principal: {bl.principal}",
        "  Rutas buscadas:",
    ]
    for ruta, estado in bl.rutas:
        lineas.append(f"    - {ruta} — {estado}")
    lineas.append(
        "  La lista vive gitignored en el checkout principal. Ver docs/SEGURIDAD_DATOS.md y "
        "MEJORAS #161."
    )
    return "\n".join(lineas)


def aviso_blocklist_parcial(bl: Blocklist) -> str:
    """Texto del aviso cuando HAY términos pero el checkout principal no se pudo determinar: se
    ha escaneado con los de este árbol, y los que vivan solo en el principal —si lo hay— no se
    han mirado (R1/H-01 de «git que falla en voz alta»). Solo afirma lo observado."""
    lineas = [
        f"{AVISO_PARCIAL}: el checkout principal no se pudo determinar, así que se ha "
        f"escaneado solo con lo que hay en este árbol ({len(bl.terminos)} término(s)). Si hay "
        "un principal, los términos que vivan solo allí NO se han comprobado: este verde no "
        "lo acredita.",
        f"  Checkout principal: {bl.principal}",
        "  Rutas buscadas:",
    ]
    for ruta, estado in bl.rutas:
        lineas.append(f"    - {ruta} — {estado}")
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


def escanear(
    paths: list[str], repo: Path = REPO_DEFECTO, blocklist: Blocklist | None = None
) -> list[str]:
    """Rutas vetadas + PII por valor. `blocklist` es la resolución ya hecha por quien llama
    (así el aviso y el escaneo describen la misma carga); si no se pasa, se resuelve aquí."""
    problemas: list[str] = []
    if blocklist is None:
        blocklist = resolver_blocklist(repo)
    patrones = [
        (t, re.compile(r"(?<![\w])" + re.escape(t) + r"(?![\w@])", re.IGNORECASE))
        for t in blocklist.terminos
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
    bl = resolver_blocklist(repo)  # UNA resolución: la misma para el aviso y el escaneo
    if not bl.terminos:
        # MEJORAS #161: el guard sin lista no refuta nada. Lo dice, y sigue (rutas + formas).
        print(aviso_blocklist_vacia(bl), file=sys.stderr)
        print("", file=sys.stderr)
    elif not bl.principal_determinado:
        # R1/H-01 de «git que falla en voz alta»: con media lista tampoco refuta lo que no miró.
        print(aviso_blocklist_parcial(bl), file=sys.stderr)
        print("", file=sys.stderr)
    bloqueos = escanear(paths, repo, bl)
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
        "'leak-guard:allow' en la línea exime SOLO las detecciones por FORMA (DNI/NIE/IBAN); "
        "un término de la blocklist no admite exención por anotación.\n"
        "Si es un falso positivo justificado, --no-verify lo salta (queda a tu criterio).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
