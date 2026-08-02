"""Guards de gobernanza de docs: frontmatter estado: valido en docs/*.md."""

import hashlib
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


# ===========================================================================
# G7-G8 — poblacion de REVISIONES ADVERSARIALES.
#
# Contrato: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
# rev. 8, sus §4, §5 y §6.
#
# ⚠️ TERCERA POBLACION de vocabularios. NO comparte set con _ESTADOS_DOCS (docs
# de raiz de docs/) ni con _ESTADOS_HANDOFF (handoffs). El campo se llama
# `estado_remediacion` y NO `estado` precisamente para que la colision sea
# imposible por construccion. Misma disciplina que G4-G6: son poblaciones con
# reglas distintas, no una deriva. NO unificar los sets, NO volver recursivo el
# glob de _docs_con_frontmatter (trampa D3, cabecera de este fichero).
# ===========================================================================

_SP = ROOT / "docs" / "superpowers"

_VEREDICTOS_REV = frozenset({
    "SHIP", "LISTA-CON-CAMBIOS", "REQUIERE-REVISION",
    "NO-SHIP", "NO-EJECUTABLE", "SIN-VEREDICTO",
})
_ESTADOS_REM = frozenset({"remediado", "parcial", "sin-cambios", "pendiente"})

# El disparador NO es el regex: el guard busca todo encabezado que CONTENGA esta
# frase y exige que case. Sin eso, un encabezado mal formado no se detecta y pasa
# en silencio, que es el modo de fallo caro.
_DISPARADOR_ADJ = "Adjudicación de la revisión"

_RE_ADJUDICACION = re.compile(
    r"^#{2,3}\s+(?:\S+\s+)?"                    # ## o ###, numeracion opcional (10., 10-bis.)
    r"Adjudicación de la revisión adversarial"
    r"[^(\n]*"                                  # calificador: "del PLAN", "de rama completa"
    r"\((?P<revisor>[^,)]+),\s*(?P<fecha>\d{4}-\d{2}-\d{2})\)"
    r"\s*—\s*(?P<veredicto>[A-Z-]+),\s*(?P<estado>[a-z-]+)\s*$")

_CAMPOS_FICHA = ("Objeto revisado", "Ronda", "Revisor", "Informe recibido",
                 "Hallazgos", "Remediado en")
_RE_CAMPO = re.compile(r"^- \*\*(?P<campo>[^:*]+):\*\*\s*(?P<valor>.+)$")

# SIN lista de exclusion: el corpus de G7 es TODO `docs/superpowers/**/*.md`
# menos las actas. La `_ADJ_LEGACY` de siete ficheros existio mientras los ocho
# encabezados heredados de julio estaban sin migrar; el retrofit del 2026-08-02
# los dejo conformes y la lista se retiro vacia (spec rev. 9 §7).
#
# La polaridad importaba y se deja dicha por si alguien vuelve a necesitarla: si
# hiciera falta excluir algo, se excluye por NOMBRE en una lista que solo puede
# encoger, nunca se define el corpus por INCLUSION — una lista de inclusion
# ("el corpus son los ficheros que ya cumplen") deja escapar cualquier fichero
# NUEVO con una adjudicacion mal formada, que es el modo de fallo caro.

_CLAVES_ACTA = ("tipo", "objeto", "objeto_rev", "commit", "ronda", "revisor",
                "veredicto", "marcador_nonce", "sha256_informe", "adjudicado_en")
_RE_SECCION = re.compile(r"§(\d+[\w-]*)")


def _sin_cercas(txt: str) -> list[str]:
    """Lineas de `txt` con el contenido de los bloques ``` vaciado.

    Imprescindible: la PLANTILLA del §5 del spec vive dentro de una cerca y
    empieza por `## … Adjudicación de la revisión…`. Sin este filtro el guard se
    autodetecta — defecto OBSERVADO en la ronda 1, no deducido.
    """
    fuera, dentro = [], False
    for ln in txt.splitlines():
        if ln.lstrip().startswith("```"):
            dentro = not dentro
            fuera.append("")
            continue
        fuera.append("" if dentro else ln)
    return fuera


def _adjudicaciones(txt: str) -> list[tuple[int, str]]:
    """(indice de linea, linea) de cada encabezado disparador fuera de cerca."""
    return [(i, ln) for i, ln in enumerate(_sin_cercas(txt))
            if ln.startswith("#") and _DISPARADOR_ADJ in ln]


def _ficha(lineas: list[str], desde: int) -> dict[str, str]:
    """Campos `- **Campo:** valor` contiguos tras el encabezado (salta blancos)."""
    campos, i = {}, desde + 1
    while i < len(lineas) and not lineas[i].strip():
        i += 1
    while i < len(lineas):
        m = _RE_CAMPO.match(lineas[i])
        if not m:
            break
        campos[m.group("campo").strip()] = m.group("valor").strip()
        i += 1
    return campos


def _fm(txt: str) -> dict[str, str]:
    fm = txt.split("---")[1] if txt.startswith("---") else ""
    return dict(re.findall(r"^([a-z0-9_]+):\s*(.+)$", fm, re.MULTILINE))


def _es_acta(txt: str) -> bool:
    return txt.startswith("---") and "tipo: revision-adversarial" in txt[:600]


def _md_superpowers():
    for p in sorted(_SP.rglob("*.md")):
        yield p, p.read_text(encoding="utf-8")


def _errores_adjudicacion(txt: str) -> list[str]:
    """Incumplimientos del §5 en `txt`. Lista vacia = conforme."""
    lineas, fallos = _sin_cercas(txt), []
    for i, ln in _adjudicaciones(txt):
        m = _RE_ADJUDICACION.match(ln)
        if not m:
            fallos.append("encabezado fuera de formato: " + repr(ln[:90]))
        else:
            if m.group("veredicto") not in _VEREDICTOS_REV:
                fallos.append("veredicto " + repr(m.group("veredicto")) + " fuera del set")
            if m.group("estado") not in _ESTADOS_REM:
                fallos.append("estado_remediacion " + repr(m.group("estado")) + " fuera del set")
        faltan = [c for c in _CAMPOS_FICHA if c not in _ficha(lineas, i)]
        if faltan:
            fallos.append("ficha incompleta, faltan " + repr(faltan))
    return fallos


def test_adjudicaciones_bien_formadas():
    """G7 — encabezado canonico + ficha de 6 campos, con vocabulario cerrado.

    Corpus: todo `docs/superpowers/**/*.md` MENOS las actas — su informe literal
    puede contener cualquier encabezado y no debe reinterpretarse como
    adjudicacion del proyecto. Sin exclusiones desde el retrofit del 2026-08-02.
    """
    malos: dict[str, list[str]] = {}
    for p, txt in _md_superpowers():
        if _es_acta(txt):
            continue
        fallos = _errores_adjudicacion(txt)
        if fallos:
            malos[p.name] = fallos
    assert not malos, (
        "adjudicaciones que incumplen el §5 del contrato: " + repr(malos) + "\n\n"
        "Forma esperada (OJO a la raya larga «—», que NO es un guion, y a las tildes):\n"
        "  ## N. Adjudicación de la revisión adversarial (Revisor, AAAA-MM-DD) — VEREDICTO, estado\n"
        "  veredicto = " + repr(sorted(_VEREDICTOS_REV)) + "\n"
        "  estado    = " + repr(sorted(_ESTADOS_REM)) + "\n"
        "  ficha     = " + repr(list(_CAMPOS_FICHA)))


def test_g7_cubre_las_adjudicaciones_del_corpus():
    """Que G7 no quede VACIO en silencio, hermano del guard equivalente de G8.

    Sin esto, renombrar los encabezados —p. ej. al plural, que es una vía medida
    y declarada en el §6— deja 0 adjudicaciones observadas y G7 VERDE: el guard
    certificaria un corpus que ya no mira. Reproducido el 2026-08-02 mutando los
    15 encabezados reales: 0 vistos, 0 errores, modulo entero verde.

    El umbral es un SUELO deliberadamente por debajo del recuento real (15), no
    una cifra exacta: un total exacto obliga a tocar el test cada vez que entra
    una adjudicacion legitima, y esa friccion acaba en que alguien lo relaje.
    """
    vistos = sum(len(_adjudicaciones(txt)) for _, txt in _md_superpowers()
                 if not _es_acta(txt))
    assert vistos >= 10, (
        "G7 observa " + str(vistos) + " adjudicaciones en docs/superpowers/; se "
        "esperaban >=10. O han desaparecido del corpus, o el disparador dejo de "
        "verlas (§6 del contrato: la deteccion es por la cadena literal "
        + repr(_DISPARADOR_ADJ) + "). Un G7 sin nada que mirar pasa en verde y no "
        "certifica nada.")


def test_g7_no_se_autodetecta_en_la_plantilla_del_spec():
    """G7-bis — la plantilla cercada del §5 NO cuenta como adjudicacion.

    Regresion del defecto de la ronda 1: un grep de encabezados sobre
    docs/superpowers/ devolvia la linea de la plantilla del propio spec.
    """
    spec = _SP / "specs" / "2026-08-01-gobernanza-revisiones-adversariales-design.md"
    txt = spec.read_text(encoding="utf-8")
    crudos = [ln for ln in txt.splitlines()
              if ln.startswith("#") and _DISPARADOR_ADJ in ln]
    fuera = [ln for _, ln in _adjudicaciones(txt)]
    assert len(crudos) > len(fuera), (
        "el spec deberia llevar al menos una plantilla cercada que el filtro descarte")
    assert _errores_adjudicacion(txt) == [], (
        "las adjudicaciones reales del spec deben ser el ejemplo de referencia")


# --- G7, fixtures negativas ---------------------------------------------------

_ADJ_OK = """## 3. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Objeto revisado:** `docs/x.md` rev. 1, commit `abc1234`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `x-adversarial-review.md`
- **Hallazgos:** 1 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #1 (`abc1234`)
"""


def test_g7_acepta_la_forma_canonica():
    assert _errores_adjudicacion(_ADJ_OK) == []


def test_g7_rechaza_estado_fuera_del_set():
    # `resuelto` es el token real de email-enumeracion §11, uno de los legacy.
    roto = _ADJ_OK.replace("NO-SHIP, remediado", "NO-SHIP, resuelto")
    assert any("estado_remediacion" in f for f in _errores_adjudicacion(roto))


def test_g7_rechaza_veredicto_con_espacios():
    # `NO EJECUTABLE` es el token real de historial §10-bis y de sandwich plan.
    roto = _ADJ_OK.replace("NO-SHIP, remediado", "NO EJECUTABLE, remediado")
    assert any("encabezado" in f for f in _errores_adjudicacion(roto))


def test_g7_rechaza_ficha_incompleta():
    roto = _ADJ_OK.replace("- **Ronda:** 1\n", "")
    assert any("ficha incompleta" in f for f in _errores_adjudicacion(roto))


def test_g7_rechaza_encabezado_sin_revisor_ni_fecha():
    # Forma real de vista procesal §10 y de dual workspace §20.
    roto = _ADJ_OK.replace(
        "## 3. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado",
        "## 10. Adjudicación de la revisión adversarial")
    assert any("encabezado" in f for f in _errores_adjudicacion(roto))


def test_g7_admite_numeracion_bis_y_calificador():
    encabezados = (
        "## 10-bis. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado",
        "## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-08-01) — NO-SHIP, remediado",
        "## Adjudicación de la revisión adversarial de rama completa (Opus, 2026-08-01) — SHIP, sin-cambios",
    )
    for enc in encabezados:
        txt = _ADJ_OK.replace(_ADJ_OK.splitlines()[0], enc)
        assert _errores_adjudicacion(txt) == [], "deberia aceptar: " + enc


def test_g7_ignora_lo_que_esta_en_cerca():
    assert _adjudicaciones("```\n" + _ADJ_OK + "```\n") == []


# --- G8: acta bien formada y cadena integra ----------------------------------

def _marcadores(nonce: str) -> tuple[str, str]:
    return ("<!-- informe-literal:inicio:" + nonce + " -->",
            "<!-- informe-literal:fin:" + nonce + " -->")


def _errores_cadena(txt: str) -> list[str]:
    """Marcadores + digest del bloque literal. Sin tocar disco."""
    fm, fallos = _fm(txt), []
    nonce = fm.get("marcador_nonce", "")
    ini, fin = _marcadores(nonce)
    n_ini, n_fin = txt.count(ini), txt.count(fin)
    if (n_ini, n_fin) != (1, 1):
        return ["se esperaba exactamente un par de marcadores con nonce "
                + repr(nonce) + "; hay " + str(n_ini) + " inicio / " + str(n_fin) + " fin"]
    if txt.index(ini) > txt.index(fin):
        return ["el marcador de fin precede al de inicio"]
    cuerpo = txt.split(ini, 1)[1].split(fin, 1)[0]
    # Canonicalizacion explicita del §4: UTF-8, LF, un unico salto final. La
    # misma forma al recibir el informe y aqui.
    canon = (cuerpo.replace("\r\n", "\n").strip("\n") + "\n").encode("utf-8")
    real = hashlib.sha256(canon).hexdigest()
    if real != fm.get("sha256_informe"):
        fallos.append("CADENA ROTA: sha256_informe declarado "
                      + repr(fm.get("sha256_informe")) + " != recomputado " + repr(real))
    if nonce and nonce in cuerpo:
        fallos.append("el nonce " + repr(nonce) + " aparece DENTRO del informe: "
                      "la delimitacion deja de ser inequivoca")
    return fallos


def _actas_con_nonce():
    """Actas que declaran `marcador_nonce`: la adhesion al contrato es el campo.

    Frontera declarada (spec §6): las tres primeras actas delimitan con `---` y
    quedan fuera. No se retrofitan y no hay lista que mantener. El precio, dicho
    en el spec: omitir el campo seria una via para escapar del digest.
    """
    for p, txt in _md_superpowers():
        if _es_acta(txt) and _fm(txt).get("marcador_nonce"):
            yield p, txt


def test_actas_bien_formadas():
    """G8 — frontmatter del §4, `adjudicado_en` a fichero Y seccion, §1 y §2."""
    malos: dict[str, list[str]] = {}
    for p, txt in _actas_con_nonce():
        fm, fallos = _fm(txt), []
        fallos += ["falta " + k for k in _CLAVES_ACTA if not fm.get(k)]
        if fm.get("veredicto") and fm["veredicto"] not in _VEREDICTOS_REV:
            fallos.append("veredicto " + repr(fm["veredicto"]) + " fuera del set")
        # Por NUMERO y prefijo, no por la frase completa: el §4 titula «Informe
        # recibido, sin modificar» y las actas reales insertan el nombre del
        # revisor («Informe recibido DE CODEX, sin modificar»). Lo estable del
        # contrato es que §1 sea el informe y §2 la evidencia; el resto del
        # titular es libre.
        for num, prefijo in ((1, "Informe recibido"), (2, "Evidencia verificada")):
            if not re.search(r"^##\s+" + str(num) + r"\.\s+" + prefijo,
                             txt, re.MULTILINE):
                fallos.append("falta la seccion §" + str(num) + " «" + prefijo + "…»")
        destino = fm.get("adjudicado_en", "")
        ruta = destino.split("§")[0].strip()
        if ruta:
            f = ROOT / ruta
            if not f.exists():
                fallos.append("adjudicado_en apunta a un fichero inexistente: " + ruta)
            else:
                m = _RE_SECCION.search(destino)
                if not m:
                    fallos.append("adjudicado_en sin §seccion")
                elif not re.search(r"^#{1,3}\s+" + re.escape(m.group(1)) + r"\.\s",
                                   f.read_text(encoding="utf-8"), re.MULTILINE):
                    fallos.append("adjudicado_en apunta a §" + m.group(1)
                                  + ", que no existe en " + ruta)
        if fallos:
            malos[p.name] = fallos
    assert not malos, "actas que incumplen el §4 del contrato: " + repr(malos)


def test_actas_cadena_de_custodia():
    """G8 — el digest del bloque literal DEBE coincidir con `sha256_informe`.

    Presencia no es comparacion: una transcripcion alterada con un hash
    meramente presente pasaba el guard de una version anterior. Una desigualdad
    es ROJA, nunca aviso: un aviso convierte una cadena de custodia rota en
    suite verde.
    """
    malos = {}
    for p, txt in _actas_con_nonce():
        fallos = _errores_cadena(txt)
        if fallos:
            malos[p.name] = fallos
    assert not malos, "actas con la cadena de custodia rota: " + repr(malos)


def test_g8_cubre_las_actas_que_declaran_nonce():
    """Que el guard no quede vacio en silencio: si nadie declara el campo, no hay
    nada comprobado, y eso debe verse."""
    cubiertas = [p.name for p, _ in _actas_con_nonce()]
    assert len(cubiertas) >= 2, (
        "G8 deberia cubrir al menos las dos actas con nonce; cubre " + repr(cubiertas))


# --- G8, fixtures negativas --------------------------------------------------

def _acta_sintetica(cuerpo="informe\n", nonce="zx7q", digest=None):
    ini, fin = _marcadores(nonce)
    canon = (cuerpo.replace("\r\n", "\n").strip("\n") + "\n").encode("utf-8")
    d = digest if digest is not None else hashlib.sha256(canon).hexdigest()
    return ("---\nmarcador_nonce: " + nonce + "\nsha256_informe: " + d + "\n---\n\n"
            + ini + "\n" + cuerpo + fin + "\n")


def test_g8_acepta_una_cadena_coherente():
    assert _errores_cadena(_acta_sintetica()) == []


def test_g8_rechaza_el_bloque_alterado():
    alterada = _acta_sintetica().replace("informe\n", "informe manipulado\n", 1)
    fallos = _errores_cadena(alterada)
    assert any("CADENA ROTA" in f for f in fallos), fallos


def test_g8_rechaza_digest_que_no_cuadra():
    fallos = _errores_cadena(_acta_sintetica(digest="0" * 64))
    assert any("CADENA ROTA" in f for f in fallos), fallos


def test_g8_rechaza_dos_pares_de_marcadores():
    ini, fin = _marcadores("zx7q")
    acta = _acta_sintetica() + "\n" + ini + "\notro\n" + fin + "\n"
    fallos = _errores_cadena(acta)
    assert any("exactamente un par" in f for f in fallos), fallos


def test_g8_rechaza_marcadores_en_orden_invertido():
    ini, fin = _marcadores("zx7q")
    acta = ("---\nmarcador_nonce: zx7q\nsha256_informe: " + "0" * 64 + "\n---\n\n"
            + fin + "\ninforme\n" + ini + "\n")
    fallos = _errores_cadena(acta)
    assert any("precede" in f for f in fallos), fallos


def test_g8_rechaza_nonce_presente_en_el_informe():
    """El §4 exige elegir el nonce de modo que no aparezca en el informe. Si
    aparece, la delimitacion deja de ser inequivoca — es el caso real del informe
    de la ronda 4, que contenia el token de fin plano."""
    fallos = _errores_cadena(_acta_sintetica(cuerpo="cita del nonce zx7q\n"))
    assert any("aparece DENTRO" in f for f in fallos), fallos
