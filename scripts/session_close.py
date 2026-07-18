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


def main() -> None:
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

    result = subprocess.run(
        [PYTHON, "-m", "pytest", "-q", "--tb=short", *pytest_args],
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


if __name__ == "__main__":
    main()
