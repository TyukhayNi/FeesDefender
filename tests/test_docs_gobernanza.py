"""Guards de gobernanza de docs: frontmatter estado: valido en docs/*.md."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ⚠️ TRAMPA (D3, revision adversarial 2026-07-26): este vocabulario es SOLO el de
# los docs de raiz de docs/ y los PLAN_*.md legacy. Los HANDOFFS usan otro
# (`activo | consumido | historico`, GOBERNANZA_FUENTES_VERDAD §5) y hoy quedan
# fuera de alcance porque el glob de _docs_con_frontmatter NO es recursivo.
# Ampliar ese glob a docs/**/*.md sin reconciliar antes los dos vocabularios
# rompe el test al instante (radio medido: 11 ficheros — 7 `consumido`, 1
# `historico` con tilde, 2 `aprobado`, 1 placeholder). Son dos poblaciones con
# reglas distintas, no una deriva: NO unificar los sets, separarlos por poblacion.
_ESTADOS_DOCS = {"vigente", "historico", "aparcado", "revisar"}
_RE_ESTADO = re.compile(r"^estado:\s*(\S+)\s*$", re.MULTILINE)


def _docs_con_frontmatter():
    """docs/*.md de nivel superior que llevan frontmatter (--- al inicio)."""
    for p in sorted((ROOT / "docs").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        if txt.startswith("---"):
            yield p, txt


def test_estado_frontmatter_valido():
    malos = []
    for p, txt in _docs_con_frontmatter():
        m = _RE_ESTADO.search(txt)
        if not m or m.group(1) not in _ESTADOS_DOCS:
            malos.append(p.name)
    assert not malos, f"docs con estado: ausente o invalido: {malos}"


def test_sin_refs_a_docs_plan_legacy():
    """Tras la reubicacion, ningun fichero trackeado debe citar docs/PLAN_*.md
    en la raiz de docs/ (ahora viven en docs/superpowers/plans/)."""
    r = subprocess.run(
        ["git", "grep", "-l", "-E", r"docs/PLAN_[A-Za-z]"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    # git grep devuelve 1 (sin match) => vacio => OK.
    ofensores = [
        ln for ln in r.stdout.splitlines()
        if ln and "test_docs_gobernanza.py" not in ln
        and "docs/superpowers/plans/2026-07-18-gobernanza-planificacion.md" not in ln
        # Excepcion documentada (D5, 2026-07-18): esta linea cita
        # ../ElContable/docs/PLAN_DESCUBRIMIENTO_API_FacturacionEV.md, un plan
        # de OTRO repo (El Contable), no uno de los 11 docs/PLAN_*.md movidos
        # aqui. Coincide con el patron por casualidad (mismo prefijo
        # "docs/PLAN_"); no existe en este repo y no se reubica.
        and "docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md" not in ln
    ]
    assert not ofensores, f"referencias a docs/PLAN_* sin actualizar: {ofensores}"


# ===========================================================================
# G1-G3 — los tres invariantes que SI habrian cazado defectos reales.
# Revision adversarial 2026-07-26:
# docs/superpowers/specs/2026-07-26-gobernanza-indice-adversarial-review.md
# ===========================================================================

def test_mejoras_futuras_numeracion_unica():
    """G1 — cada `## NN.` de MEJORAS_FUTURAS.md es unico (habria cazado D4).

    La regla de promocion backlog->cola (`CLAUDE.md`) referencia las entradas por
    `MEJORAS #NN`. Con dos `## 48.` esa llave dejaba de ser univoca justo en el
    numero que `CLAUDE.md:220` y `PLAN.md` resuelven al motor documental: un
    `Ctrl+F "## 48"` en un fichero de 3.100 lineas caia en la entrada equivocada.
    """
    txt = (ROOT / "docs" / "MEJORAS_FUTURAS.md").read_text(encoding="utf-8")
    nums = re.findall(r"^## (\d+)\.", txt, re.MULTILINE)
    dups = sorted({n for n in nums if nums.count(n) > 1}, key=int)
    assert not dups, (
        f"numeros duplicados en MEJORAS_FUTURAS.md (rompen la llave `MEJORAS #NN`): {dups}")


# --- G2: toda cita a un spec/plan debe resolver en disco ---------------------

# Un nombre = cadena de caracteres corrientes o grupos de llaves COMPLETOS. La coma
# solo se admite dentro de `{...}`: sin eso, `…-{design,fase2}.md` se parte por la
# coma y el token deja de terminar en `.md`, o sea que la cita rota de D5 pasaba
# desapercibida — el propio defecto que este guard existe para cazar.
_NOMBRE = r"(?:[^\s`\"'()\[\]<>,;{}]|\{[^{}]*\})+\.md"
_RE_RUTA_SP = re.compile(rf"docs/superpowers/(?:specs|plans)/{_NOMBRE}")
# Stem DESNUDO (sin directorio): asi estaba escrita la cita rota de D5, y por eso
# un guard que solo mirase rutas completas no la habria cazado.
_RE_STEM_FECHADO = re.compile(rf"(?<![\w/.-])(\d{{4}}-\d{{2}}-\d{{2}}-{_NOMBRE})")

# Descarte por PATRON, no por lista de excepciones (el guard de refs legacy ya
# acumulo 2 excepciones hardcodeadas en 48 lineas; ese es el modo de erosion).
_RE_PLACEHOLDER = re.compile(
    r"[*?]"                          # glob
    r"|\.\.\.|…"                     # elipsis
    r"|\bAAAA\b|\bMM\b|\bDD\b|\bNN\b|X{3,}"   # metavariables de plantilla
    r"|(?<=[_-])[A-Z](?=[._-])"      # metavariable de una letra: PLAN_X.md
)


def _expandir_llaves(token: str) -> list[str]:
    """`a-{x,y}.md` -> ['a-x.md', 'a-y.md']. Recursivo para varios grupos."""
    m = re.search(r"\{([^{}]*)\}", token)
    if not m:
        return [token]
    return [x for alt in m.group(1).split(",")
            for x in _expandir_llaves(token[:m.start()] + alt.strip() + token[m.end():])]


def _md_trackeados() -> list[Path]:
    r = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ROOT / ln for ln in r.stdout.splitlines() if ln]


def test_citas_a_specs_y_plans_existen():
    """G2 — toda cita a un spec/plan en un .md trackeado resuelve en disco.

    Habria cazado D5: `PLAN.md` citaba `2026-06-25-email-atomize-layerb-{design,
    fase2}.md`; el `-design` existe en specs/ pero NO hay ningun plan `*layerb*`
    (se llama `2026-06-25-email-atomize-fase2.md`). El guard de refs legacy solo
    comprueba que no se cite la UBICACION vieja; nunca que la ruta exista.
    """
    nombres = {p.name for p in (ROOT / "docs" / "superpowers").rglob("*.md")}
    rotas: dict[str, list[str]] = {}
    for f in _md_trackeados():
        txt = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(ROOT).as_posix()
        candidatos = [(t, True) for t in _RE_RUTA_SP.findall(txt)]
        candidatos += [(t, False) for t in _RE_STEM_FECHADO.findall(txt)]
        for token, es_ruta in candidatos:
            if _RE_PLACEHOLDER.search(token):
                continue
            for cand in _expandir_llaves(token):
                existe = (ROOT / cand).exists() if es_ruta else Path(cand).name in nombres
                if not existe:
                    rotas.setdefault(rel, []).append(cand)
    assert not rotas, f"citas a specs/plans que no existen en disco: {rotas}"


def test_todo_doc_de_raiz_esta_en_el_indice():
    """G3 — todo `docs/*.md` esta citado en `INDICE.md` (habria cazado D6).

    Sustituye al G3 original («todo doc de raiz DEBE tener frontmatter»), que no
    era barato: 11 de 20 docs lo incumplen hoy y uno de ellos es generado. Este
    caza el mismo defecto — `CRM_SUDESPACHO_ATLAS.md`, declarado SSOT en
    `CLAUDE.md:210`, estaba fuera del indice que promete cubrir la raiz de
    `docs/` — y nace verde con una sola fila.
    """
    indice = ROOT / "docs" / "INDICE.md"
    txt = indice.read_text(encoding="utf-8")
    ausentes = [p.name for p in sorted((ROOT / "docs").glob("*.md"))
                if p != indice and p.name not in txt]
    assert not ausentes, f"docs de raiz sin fila en INDICE.md: {ausentes}"


# ===========================================================================
# G4-G6 — poblacion de HANDOFFS (docs/superpowers/handoffs/).
#
# ⚠️ Estos guards son DELIBERADAMENTE independientes de los de arriba. Los
# handoffs tienen vocabulario y reglas propios (GOBERNANZA_FUENTES_VERDAD §5);
# los docs de raiz de docs/, otros (_ESTADOS_DOCS). Son dos poblaciones, no una
# deriva: aqui NO se toca _ESTADOS_DOCS ni se vuelve recursivo el glob de
# _docs_con_frontmatter — eso es exactamente la trampa D3 que documenta la
# cabecera de este fichero, y unificar los sets rompe 11 ficheros al instante.
# Cada poblacion se guarda por separado.
#
# Nacen de los cuatro incumplimientos de los tres `…-vista-procesal-codex-*`
# detectados el 2026-07-30: frontmatter de vocabulario ajeno, `estado: abierto`
# (fuera del set), nombre sin el prefijo `handoff-` y ausencia de la tabla del
# INDICE que promete cubrir la carpeta. Ninguno lo cazaba ningun test.
# ===========================================================================

_HANDOFFS = ROOT / "docs" / "superpowers" / "handoffs"
_ESTADOS_HANDOFF = {"activo", "consumido", "historico"}
# Excepcion de nombre heredada. Su HOGAR es GOBERNANZA §5; esta lista es la
# copia ejecutable, y el §5 avisa de que anadir una obliga a tocar las dos.
_HANDOFFS_NOMBRE_EXENTO = {"prompt_handoff_expedientes_seguros.md"}
# El §5 fija prefijo + fecha; el <tema-kebab> queda permisivo a proposito,
# porque hay refs de caso en mayusculas (`…-apertura-W-02T3XO-mejoras-proceso`).
_RE_NOMBRE_HANDOFF = re.compile(r"^handoff-\d{4}-\d{2}-\d{2}-[A-Za-z0-9-]+\.md$")
_RE_NOMBRE_MD = re.compile(_NOMBRE)


def _handoffs():
    """(path, dict del frontmatter) de cada `docs/superpowers/handoffs/*.md`."""
    for p in sorted(_HANDOFFS.glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        fm = txt.split("---")[1] if txt.startswith("---") else ""
        yield p, dict(re.findall(r"^([a-z_]+):\s*(.+)$", fm, re.MULTILINE))


def test_handoffs_frontmatter_valido():
    """G4 — `estado:` del set del §5 + los campos que el §5 exige.

    Caza dos de los cuatro incumplimientos de los `codex-*`: el `estado:
    abierto` (palabra fuera del ciclo de vida) y el frontmatter de vocabulario
    ajeno, que no traia `creado`/`origen`/`destino`/`consumido_por`.

    Campos ANADIDOS son libres (`revisor`, `veredicto`, `spec`…): el §5 fija un
    minimo obligatorio, no un vocabulario cerrado. Por eso esto comprueba
    presencia, nunca ausencia.
    """
    malos: dict[str, list[str]] = {}
    for p, fm in _handoffs():
        fallos = []
        estado = fm.get("estado")
        if estado not in _ESTADOS_HANDOFF:
            fallos.append(f"estado={estado!r} (set del §5: {sorted(_ESTADOS_HANDOFF)})")
        fallos += [f"falta {k}" for k in ("creado", "origen", "destino") if not fm.get(k)]
        # Ciclo de vida del §5: `consumido_por` se rellena AL pasar a consumido.
        # Un `activo` legitimamente aun no lo tiene.
        if estado in {"consumido", "historico"} and not fm.get("consumido_por"):
            fallos.append("falta consumido_por")
        if fallos:
            malos[p.name] = fallos
    assert not malos, f"handoffs que incumplen GOBERNANZA §5: {malos}"


def test_handoffs_nombre_canonico():
    """G5 — `handoff-AAAA-MM-DD-<tema>.md`, salvo la exencion declarada.

    Caza el tercer incumplimiento: los tres `codex-*` entraron el 2026-07-27
    sin el prefijo, ocho dias despues de aprobarse la regla.
    """
    malos = [p.name for p in sorted(_HANDOFFS.glob("*.md"))
             if p.name not in _HANDOFFS_NOMBRE_EXENTO
             and not _RE_NOMBRE_HANDOFF.match(p.name)]
    assert not malos, (
        f"handoffs con nombre fuera del §5 (esperado handoff-AAAA-MM-DD-<tema>.md): {malos}")


def test_todo_handoff_esta_en_el_indice():
    """G6 — todo handoff tiene fila en `INDICE.md §Handoffs`.

    Caza el cuarto: los tres `codex-*` faltaban de la tabla que el propio
    INDICE promete que cubre la carpeta. Hermano de G3, para la otra poblacion.
    Expande las llaves porque el INDICE agrupa filas (`…-W-{02T3XO,02TH0W,…}-…`).
    """
    txt = (ROOT / "docs" / "INDICE.md").read_text(encoding="utf-8")
    citados = {Path(n).name
               for tok in _RE_NOMBRE_MD.findall(txt)
               for n in _expandir_llaves(tok)}
    ausentes = [p.name for p in sorted(_HANDOFFS.glob("*.md")) if p.name not in citados]
    assert not ausentes, f"handoffs sin fila en INDICE.md §Handoffs: {ausentes}"
