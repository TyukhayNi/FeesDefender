#!/usr/bin/env python3
"""
FeesDefender — Verificacion de tests pre-commit
=================================================
Ejecutar como parte del cierre de sesion desde PowerShell:

    cd "C:\\Users\\tnm33\\Dev\\FeesDefender"
    python -m scripts.session_close && git add <rutas> && git commit -m "<mensaje>"
    # (nunca `git add -A`: grapa solo las rutas del cambio)

Verja de tests por defecto RAPIDA: omite los tests marcados `@pytest.mark.slow`
(motor NLP/OCR real de core/anon/, ~3-4 min). Esos solo se ejecutan cuando:
  - el commit toca `core/anon/` (deteccion automatica via git), o
  - se pasa `--runslow` / la variable de entorno RUN_SLOW=1.

Asi la red de seguridad de anonimizacion (regresion SaRS1, OCR, integracion)
corre siempre que cambia el motor, sin depender de que nadie se acuerde, y el
cierre del dia a dia (cambios fuera de core/anon/) vuela en segundos.

El mensaje de commit lo proporciona Claude en el chat. El resto del protocolo
de cierre (STATUS.md, DEAD_ENDS.md, memoria) lo gestiona Claude directamente.
Ver STATUS.md seccion "Protocolo de cierre de sesion".
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from sys import executable as PYTHON

ROOT = Path(__file__).resolve().parent.parent
_ANON_PREFIX = "core/anon/"

# Un item de PLAN.md que contenga una de estas frases (minusculas) afirma
# trabajo EN CURSO/sin publicar. Los items completados las reescriben en
# pasado ("mergeada", "podados", "✅"), asi que su presencia + una rama que
# git ya no conoce = drift PLAN.md <-> git (lo que paso con [BIBLIOTECA-CHECKOUT]).
_FRASES_PENDIENTE = (
    "sin commitear",
    "sin comitear",
    "pendiente commit",
    "pendiente de commit",
    "rama de trabajo",
    "a la espera de ok",
    "espera ok de",
)
# Tokens con pinta de rama git: prefijo convencional + resto del nombre.
_RE_RAMA = re.compile(
    r"\b(?:feat|fix|docs|chore|refactor|test|hotfix|release)/[A-Za-z0-9._\-/]+"
)


def _git_lines(args: list[str]) -> list[str]:
    """Salida de un comando git, una linea por elemento. [] si git falla."""
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return []
    if r.returncode != 0:
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def _anon_tocado() -> bool:
    """True si core/anon/ tiene cambios sin commitear o en el ultimo commit."""
    # Cambios en working tree + staged (porcelain: 'XY ruta').
    for ln in _git_lines(["status", "--porcelain"]):
        ruta = ln[3:] if len(ln) > 3 else ln
        if _ANON_PREFIX in ruta.replace("\\", "/"):
            return True
    # Ficheros del ultimo commit (por si ya se commiteo antes de la verja).
    for ruta in _git_lines(["show", "--name-only", "--pretty=format:", "HEAD"]):
        if _ANON_PREFIX in ruta.replace("\\", "/"):
            return True
    return False


def _git_count(rango: list[str]) -> int:
    """Nº de commits en un rango tipo 'A..B'. 0 si git falla o el rango es vacío."""
    out = _git_lines(["rev-list", "--count", *rango])
    return int(out[0]) if out and out[0].isdigit() else 0


def _trabajo_sin_publicar() -> list[tuple[str, int, str]]:
    """Ramas locales con commits que NO están en el archivo central (origin).

    Devuelve tuplas (rama, n_commits, tipo) donde tipo es:
      - 'sin_publicar': la rama tiene upstream y va n commits por delante.
      - 'nunca_subida': la rama no tiene upstream y tiene n commits sobre origin/main.
    Solo consultas locales a git; sin red ni credenciales.
    """
    filas: list[tuple[str, int, str]] = []
    fmt = "%(refname:short)\t%(upstream:short)"
    for ln in _git_lines(["for-each-ref", "--format=" + fmt, "refs/heads"]):
        partes = ln.split("\t")
        rama = partes[0]
        upstream = partes[1] if len(partes) > 1 and partes[1] else ""
        if upstream:
            n = _git_count([f"{upstream}..{rama}"])
            if n:
                filas.append((rama, n, "sin_publicar"))
        else:
            n = _git_count([f"origin/main..{rama}"])
            if n:
                filas.append((rama, n, "nunca_subida"))
    return filas


def _avisar_publicacion() -> None:
    """AVISO no bloqueante: trabajo grapado (commits) que no ha llegado a origin.

    No consulta la red ni comprueba si existe el PR (eso exigiría credenciales):
    solo detecta commits locales sin publicar y recuerda la vía rama + PR.
    """
    actual = (_git_lines(["branch", "--show-current"]) or [""])[0]
    filas = _trabajo_sin_publicar()
    print("\n" + "-" * 40)
    print("Trabajo sin publicar")
    if not filas:
        print(f"Rama actual: {actual} - sin commits sin publicar. Nada que llevar al archivo.")
        return
    print("[!] Tienes trabajo que NO esta en el archivo central (origin):")
    for rama, n, tipo in filas:
        marca = " (rama nunca subida)" if tipo == "nunca_subida" else ""
        aqui = "  <- estas aqui" if rama == actual else ""
        plural = "commit" if n == 1 else "commits"
        print(f"  -> {rama}: {n} {plural} sin publicar{marca}{aqui}")
    print("Recuerda: 'main' no admite entradas directas.")
    print("Publica con: rama + PR (debe pasar 'leak-scan' antes de fusionar).")


def _ramas_conocidas() -> set[str]:
    """Nombres de rama que git conoce (locales + remotas, sin prefijo origin/)."""
    ramas: set[str] = set()
    for ln in _git_lines(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"]
    ):
        if ln.startswith("origin/"):
            ln = ln[len("origin/"):]
        if ln and ln != "HEAD":
            ramas.add(ln)
    return ramas


def _plan_items_desfasados(
    texto: str, ramas_conocidas: set[str]
) -> list[tuple[str, list[str]]]:
    """Items de PLAN.md que afirman trabajo pendiente en una rama fantasma.

    Puro y testeable. Trocea PLAN.md por encabezados (`#`); para cada bloque que
    contenga una frase de pendiente (`_FRASES_PENDIENTE`), extrae los tokens con
    pinta de rama y devuelve los que git YA NO conoce. Los items completados no
    usan esas frases, asi que no se marcan aunque citen una rama podada.

    Devuelve [(titulo_del_item, [ramas_fantasma_ordenadas]), ...].
    """
    filas: list[tuple[str, list[str]]] = []
    titulo = ""
    buf: list[str] = []

    def _cerrar(titulo: str, contenido: str) -> None:
        low = contenido.lower()
        if not any(frase in low for frase in _FRASES_PENDIENTE):
            return
        ramas = {m.rstrip("./") for m in _RE_RAMA.findall(contenido)}
        fantasmas = sorted(r for r in ramas if r not in ramas_conocidas)
        if fantasmas:
            filas.append((titulo, fantasmas))

    for ln in texto.splitlines():
        if ln.lstrip().startswith("#"):
            if buf:
                _cerrar(titulo, "\n".join(buf))
            titulo = ln.lstrip("#").strip()
            buf = [ln]
        else:
            buf.append(ln)
    if buf:
        _cerrar(titulo, "\n".join(buf))
    return filas


# --- Higiene de PLAN.md / STATUS.md (presupuesto de tamaño + ledger) ---
_STATUS_MAX_LINEAS = 400
_CERRADOS_MAX = 30
_RE_HEADING_CERRADOS = re.compile(r"^#{2,}\s+.*Cerrados\b", re.IGNORECASE)


def _contar_lineas(texto: str) -> int:
    """Nº de líneas de un texto (0 si vacío)."""
    return len(texto.splitlines())


def _indice_cerrados(lineas: list[str]) -> int | None:
    """Índice de la línea del encabezado '## … Cerrados' (None si no existe)."""
    for i, ln in enumerate(lineas):
        if _RE_HEADING_CERRADOS.match(ln.strip()):
            return i
    return None


def _cerrados_sin_colapsar(plan_texto: str) -> list[str]:
    """Títulos de encabezados de ítems CERRADOS que no se han colapsado al ledger.

    Puro y testeable. Un ítem cerrado se escribe con el encabezado empezando por
    ✅ (`## ✅ [FOO] COMPLETA`). Un ✅ a mitad del encabezado marca una FASE hecha
    de un ítem abierto (`[SIGUIENTE-GOOGLE-MCP] F1 ✅ …`) y NO se marca. Solo se
    miran los encabezados ANTES de la sección '## … Cerrados' (el encabezado de la
    propia sección y las entradas del ledger quedan fuera del corte).
    """
    lineas = plan_texto.splitlines()
    corte = _indice_cerrados(lineas)
    limite = corte if corte is not None else len(lineas)
    titulos: list[str] = []
    for ln in lineas[:limite]:
        s = ln.strip()
        if not s.startswith("#"):
            continue
        texto = s.lstrip("#").strip()
        if texto.startswith("✅"):
            titulos.append(texto.lstrip("✅").strip())
    return titulos


def _contar_cerrados(plan_texto: str) -> int:
    """Nº de entradas del ledger '## … Cerrados' (líneas '- ' hasta el siguiente
    encabezado o el fin del fichero). 0 si no hay sección Cerrados."""
    lineas = plan_texto.splitlines()
    corte = _indice_cerrados(lineas)
    if corte is None:
        return 0
    n = 0
    for ln in lineas[corte + 1:]:
        s = ln.strip()
        if s.startswith("#"):
            break
        if s.startswith("- "):
            n += 1
    return n


def _avisar_plan_desfasado() -> None:
    """AVISO no bloqueante: PLAN.md afirma trabajo pendiente en ramas fantasma.

    Cierra el agujero que dejo [BIBLIOTECA-CHECKOUT] desfasado: PLAN decia
    "sin commitear en feat/repository-checkout" cuando la rama ya estaba
    mergeada y podada. Solo consultas locales a git; sin red.
    """
    plan = ROOT / "PLAN.md"
    print("\n" + "-" * 40)
    print("Coherencia PLAN.md <-> git")
    if not plan.exists():
        print("PLAN.md no encontrado - nada que comprobar.")
        return
    texto = plan.read_text(encoding="utf-8")
    filas = _plan_items_desfasados(texto, _ramas_conocidas())
    if not filas:
        print("PLAN.md: sin items pendientes que citen ramas que git ya no conoce.")
        return
    print("[!] PLAN.md marca trabajo PENDIENTE en ramas que git ya no conoce")
    print("    (probable: mergeadas y podadas -> el item deberia estar cerrado):")
    for titulo, fantasmas in filas:
        print(f"  -> {titulo}: {', '.join(fantasmas)}")
    print("Si ya esta en main: marca el item [x]/✅ con el hash del PR y")
    print("quita la prosa de rama/worktree (git es el hogar de ese hecho).")


def _avisar_higiene_planificacion() -> None:
    """AVISO no bloqueante: higiene de STATUS.md y PLAN.md.

    (1) STATUS.md supera el presupuesto de tamaño -> rotar a docs/bitacora/.
    (2) PLAN.md tiene item(s) ✅ sin colapsar al ledger '## Cerrados'.
    (3) El ledger '## Cerrados' supera el tope -> agrupar por area.
    Solo lee ficheros del repo; sin git ni red. Cablea las reglas que la
    doctrina 2026-07-05 dejo como prosa y por eso se degradaron.
    """
    print("\n" + "-" * 40)
    print("Higiene de planificacion (STATUS.md / PLAN.md)")
    hay_aviso = False

    status = ROOT / "STATUS.md"
    if status.exists():
        n = _contar_lineas(status.read_text(encoding="utf-8"))
        if n > _STATUS_MAX_LINEAS:
            hay_aviso = True
            print(f"[!] STATUS.md: {n} lineas (> {_STATUS_MAX_LINEAS}). "
                  "Rota el historico de cierres a docs/bitacora/2026.md (fase C).")

    plan = ROOT / "PLAN.md"
    if plan.exists():
        texto = plan.read_text(encoding="utf-8")
        sin_colapsar = _cerrados_sin_colapsar(texto)
        if sin_colapsar:
            hay_aviso = True
            print(f"[!] PLAN.md: {len(sin_colapsar)} item(s) ✅ sin colapsar al "
                  "ledger '## Cerrados':")
            for titulo in sin_colapsar:
                print(f"  -> {titulo}")
        n_cerrados = _contar_cerrados(texto)
        if n_cerrados > _CERRADOS_MAX:
            hay_aviso = True
            print(f"[!] PLAN.md: '## Cerrados' tiene {n_cerrados} entradas "
                  f"(> {_CERRADOS_MAX}). Promueve el ledger a agrupacion por area.")

    if not hay_aviso:
        print("STATUS.md y PLAN.md dentro de presupuesto; sin ✅ sin colapsar.")


# --- Trazabilidad de specs/plans recientes en el ledger ---
#
# Cierra el hueco que dejo `crm-atlas`: PR #104 mergeado a `main` con 6.400 lineas
# de atlas y CERO filas en `PLAN.md ## ✅ Cerrados`, cero prosa en la bitacora. Su
# unica huella era el nombre de su rama, citado como escombro a podar.
#
# Dos decisiones de diseño que parecen detalles y no lo son (revision adversarial
# 2026-07-26, §Autocorrecciones):
#
# 1. `docs/superpowers/handoffs/` NO entra en el corpus de trazas. El handoff es
#    un andamio efimero y `GOBERNANZA_FUENTES_VERDAD §5` dice expresamente que no
#    es fuente de verdad. Incluirlo AUTOANULA el aviso: el stem de `crm-atlas`
#    aparece justo dentro del handoff que denuncio el hueco, o sea que el defecto
#    se daria por trazado por haber sido denunciado. Con handoffs dentro: 0 avisos.
# 2. La etiqueta `[XXX]` del bloque NO se usa como señal: sobre-empareja (una
#    etiqueta generica casa con cualquier item vecino y da por trazado lo que no
#    lo esta). Señal = el stem del fichero, o el nº de PR del commit que lo
#    introdujo. `INDICE.md` tampoco entra: es vista derivada, no ledger.
_TRAZA_DIAS = 10
_DIRS_DISENO = ("docs/superpowers/specs/", "docs/superpowers/plans/")
_CORPUS_TRAZAS = ("PLAN.md", "docs/bitacora", "docs/MEJORAS_FUTURAS.md", "docs/DEAD_ENDS.md")
_RE_SHA = re.compile(r"^[0-9a-f]{40}$")
_RE_PR_SUBJECT = re.compile(r"\(#(\d+)\)\s*$")


def _pr_del_commit(sha: str) -> str | None:
    """Nº de PR del subject de un squash ('… (#127)'). None si no lo lleva."""
    subject = _git_lines(["log", "-1", "--pretty=format:%s", sha])
    if not subject:
        return None
    m = _RE_PR_SUBJECT.search(subject[0])
    return m.group(1) if m else None


def _disenos_recientes(dias: int = _TRAZA_DIAS) -> list[tuple[str, str | None]]:
    """[(ruta, nº_de_PR|None)] de specs/plans AÑADIDOS en los ultimos N dias.

    `--diff-filter=A` = solo altas; renombrar o editar un doc viejo no dispara.
    Solo consultas locales a git; sin red.
    """
    vistos: dict[str, str] = {}
    for pat in _DIRS_DISENO:
        sha = ""
        for ln in _git_lines(["log", f"--since={dias}.days.ago", "--diff-filter=A",
                              "--pretty=format:%H", "--name-only", "--", pat]):
            if _RE_SHA.match(ln):
                sha = ln
            elif ln.startswith(pat) and ln.endswith(".md"):
                vistos.setdefault(ln, sha)
    cache: dict[str, str | None] = {}
    filas = []
    for ruta, sha in sorted(vistos.items()):
        if sha not in cache:
            cache[sha] = _pr_del_commit(sha)
        filas.append((ruta, cache[sha]))
    return filas


def _texto_corpus_trazas() -> str:
    """Concatena el corpus donde vive la trazabilidad REAL (ledger + narrativa)."""
    partes: list[str] = []
    for rel in _CORPUS_TRAZAS:
        p = ROOT / rel
        if p.is_dir():
            for f in sorted(p.glob("*.md")):
                partes.append(f.read_text(encoding="utf-8", errors="replace"))
        elif p.exists():
            partes.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(partes)


def _disenos_sin_traza(recientes: list[tuple[str, str | None]], corpus: str) -> list[str]:
    """Rutas de specs/plans recientes sin señal en el corpus. Puro y testeable.

    Trazado = su STEM aparece en el corpus, o el nº de PR que lo introdujo. Basta
    una de las dos: un plan puede estar trazado por la fila de ledger de su PR sin
    que nadie escriba el nombre del fichero, y al reves.
    """
    huerfanos = []
    for ruta, pr in recientes:
        stem = ruta.rsplit("/", 1)[-1][:-3]  # sin .md
        if stem in corpus:
            continue
        # `#1` NO puede casar dentro de `#104`: el nº de PR se compara entero.
        if pr and re.search(rf"#{pr}(?!\d)", corpus):
            continue
        huerfanos.append(ruta)
    return huerfanos


def _avisar_specs_sin_traza() -> None:
    """AVISO no bloqueante: spec/plan reciente sin traza en el ledger ni la bitacora.

    Solo git local + lectura de ficheros del repo; sin red. Un spec sin traza NO
    es necesariamente un defecto —«spec hoy, decision mañana» es un estado
    legitimo—, por eso avisa y no bloquea: la verja de pytest del cierre romperia
    ese estado.
    """
    print("\n" + "-" * 40)
    print(f"Trazabilidad de specs/plans (ultimos {_TRAZA_DIAS} dias)")
    recientes = _disenos_recientes()
    if not recientes:
        print(f"Sin specs/plans nuevos en los ultimos {_TRAZA_DIAS} dias.")
        return
    huerfanos = _disenos_sin_traza(recientes, _texto_corpus_trazas())
    if not huerfanos:
        print(f"{len(recientes)} spec(s)/plan(es) reciente(s); todos con traza.")
        return
    print(f"[!] {len(huerfanos)} de {len(recientes)} spec(s)/plan(es) reciente(s) sin traza")
    print("    en PLAN.md / bitacora / MEJORAS_FUTURAS / DEAD_ENDS:")
    for ruta in huerfanos:
        print(f"  -> {ruta}")
    print("Si el trabajo ya esta en main: fila en 'PLAN.md ## ✅ Cerrados' con el")
    print("nº de PR y enlace al spec. Si sigue abierto: item en la cola.")
    print("(Un handoff que lo mencione NO cuenta: no es fuente de verdad.)")


#: Dependencias de terceros que la suite necesita ya en la fase de COLECCION:
#: `core.config` importa `dotenv`; `core.utils`, `yaml` y `slugify`. Sin ellas
#: pytest no "falla": no llega a ejecutar ninguna asercion.
#: `xdist` va aqui aunque no lo importe la suite: la verja lanza `-n auto`, y sin el
#: plugin pytest muere con «unrecognized arguments: -n» — un rojo que no dice nada
#: sobre el estado del codigo. Mejor el mensaje de venv que el traceback de argparse.
DEPS_DE_COLECCION: tuple[str, ...] = ("pytest", "dotenv", "yaml", "slugify", "xdist")


def deps_que_faltan(deps: tuple[str, ...] = DEPS_DE_COLECCION) -> list[str]:
    """Las de `deps` que ESTE interprete no puede importar.

    No mide "estoy dentro de un venv" —alguien puede tenerlas instaladas
    globalmente y estar perfectamente— sino la propiedad que de verdad decide
    si la medicion vale: si el interprete que va a lanzar pytest puede importar
    lo que la suite necesita.
    """
    import importlib.util
    faltan = []
    for mod in deps:
        try:
            if importlib.util.find_spec(mod) is None:
                faltan.append(mod)
        except (ImportError, ValueError, ModuleNotFoundError):
            # Un paquete padre ausente hace que `find_spec` LANCE en vez de
            # devolver None; cuenta igual como ausente.
            faltan.append(mod)
    return faltan


def venv_sugerido() -> Path | None:
    """El `python.exe` del venv del repo, resolviendo el caso worktree.

    **Por que no vale `ROOT/.venv`.** En un worktree ese venv NO existe -el
    venv vive en el repo principal-, y el worktree es justamente el escenario
    que dispara la verja: sugerir `ROOT/.venv` manda a un interprete
    inexistente. Defecto real del PR #258, cazado al ejecutarlo y no por sus
    tests (uno pedia solo `".venv" in salida`, y una ruta equivocada tambien lo
    cumple).

    **Como se resuelve sin subproceso.** En un worktree, `ROOT/.git` es un
    FICHERO con `gitdir: <repo>/.git/worktrees/<nombre>`; el antecesor llamado
    `.git` da la raiz real. La verja va antes de cualquier subproceso, asi que
    no se le puede preguntar a git.

    Returns:
        La ruta si existe en disco; ``None`` si no hay venv en ninguna de las
        dos raices -mejor callar que inventar una ruta.
    """
    raices = [ROOT]
    dot_git = ROOT / ".git"
    if dot_git.is_file():
        try:
            texto = dot_git.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            texto = ""
        if texto.startswith("gitdir:"):
            gitdir = Path(texto.split(":", 1)[1].strip().replace("\\", "/"))
            for ancestro in gitdir.parents:
                if ancestro.name == ".git":
                    raices.append(ancestro.parent)
                    break
    for raiz in raices:
        for rel in (("Scripts", "python.exe"), ("bin", "python")):
            candidato = raiz.joinpath(".venv", *rel)
            if candidato.exists():
                return candidato
    return None


def main() -> None:
    # Antes de cualquier otra cosa: si este interprete no puede importar las
    # dependencias, la suite no va a "fallar" — no va a correr. Presentar eso
    # como "tests fallando" manda a diagnosticar una rotura inexistente y
    # ensena a ignorar esta verja por creerla averiada. Misma regla que la
    # revision adversarial del despacho: quien no corre no refuta, deja SIN
    # VERIFICAR. De ahi el codigo 2, distinto del 1 de "medi y salio mal".
    faltan = deps_que_faltan()
    if faltan:
        print(f"\n[X] NO SE HA MEDIDO NADA: este interprete no puede importar "
              f"{', '.join(faltan)}.")
        print(f"    Interprete usado: {PYTHON}")
        venv = venv_sugerido()
        if venv is not None:
            print("    Los worktrees no tienen `.venv` propio. Usa el del repo:")
            print(f'      & "{venv}" -m scripts.session_close')
        else:
            # Nunca imprimir una ruta compuesta a ciegas: si no se encuentra el
            # venv, decirlo es mas util que mandar a un fichero inexistente.
            print("    No encuentro el `.venv` del repo (ni aqui ni en la raiz "
                  "principal).")
            print("    Crealo o activalo antes de cerrar: pip install -r "
                  "requirements.txt")
        print("    La suite NO ha corrido: esto no dice nada sobre su estado.")
        sys.exit(2)

    force_slow = "--runslow" in sys.argv or os.getenv("RUN_SLOW") == "1"
    runslow = force_slow or _anon_tocado()

    print("FeesDefender - pytest pre-commit")
    print("-" * 40)
    if runslow:
        motivo = "forzado (--runslow/RUN_SLOW)" if force_slow else "core/anon/ tocado"
        print(f"Modo: COMPLETO (incluye tests lentos) - {motivo}")
        pytest_args = ["--runslow"]
    else:
        print("Modo: RAPIDO (omite tests lentos; core/anon/ sin cambios)")
        pytest_args = []

    # La suite ENTERA en paralelo. Medido el 2026-09-06 sobre 12 CPUs: 371 s -> 94 s,
    # con el conteo IDENTICO (4.656 tests, 88 `skip`, 6 `xfail`) y CERO tests
    # serializados: la suite ya era segura en paralelo, cosa que `pytest-randomly`
    # llevaba meses forzando sin que nadie hubiera cobrado el dividendo.
    #
    # `-n auto` NO va en `addopts` de `pyproject.toml`, y eso tambien esta medido:
    # sobre un fichero suelto arrancar 12 workers cuesta MAS de lo que ahorra
    # (17,0 s contra 11,9 s). Aqui siempre corre la suite completa, asi que aqui si.
    #
    # `--durations` para que el coste sea visible y no una sensacion: 19 tests
    # (el 0,4%) se comen el 29% del tiempo.
    result = subprocess.run(
        [PYTHON, "-m", "pytest", "-q", "--tb=short",
         "-n", "auto", "--durations=15", *pytest_args],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("\n[X] Tests fallando - commit abortado.")
        sys.exit(1)
    print("\n[OK] Tests verdes - puedes continuar con git add / commit.")

    # Chequeo de skills (modo AVISO, no bloquea el cierre): CHANGELOG sin
    # actualizar, .skill caducado, drift de helpers, identidad incompleta.
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_skills", ROOT / "scripts" / "check_skills.py"
        )
        cs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cs)
        print("\n" + "-" * 40)
        cs.report(repackage=False)
    except Exception as e:  # el chequeo nunca debe romper el cierre
        print(f"[aviso] no se pudo correr check_skills: {e}")

    # Aviso de trabajo sin publicar (modo AVISO, no bloquea el cierre).
    try:
        _avisar_publicacion()
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudo comprobar trabajo sin publicar: {e}")

    # Aviso de PLAN.md desfasado respecto a git (modo AVISO, no bloquea).
    try:
        _avisar_plan_desfasado()
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudo comprobar coherencia de PLAN.md: {e}")

    # Aviso de higiene de planificacion (modo AVISO, no bloquea).
    try:
        _avisar_higiene_planificacion()
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudo comprobar higiene de planificacion: {e}")

    # Aviso de specs/plans recientes sin traza en el ledger (modo AVISO, no bloquea).
    try:
        _avisar_specs_sin_traza()
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudo comprobar trazabilidad de specs/plans: {e}")


if __name__ == "__main__":
    # UTF-8 wrap en Windows: sin esto, _avisar_higiene_planificacion() revienta
    # con UnicodeEncodeError (cp1252 no codifica el "✅" de sus propios avisos) y
    # el aviso real de PLAN.md/STATUS.md nunca llega a imprimirse (mismo gotcha
    # documentado en CLAUDE.md para separar.py/anonimizar.py).
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    main()
