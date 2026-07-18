# Apertura B1–B5 · PR-2 (B2: `--case-id` para intake incremental) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el intake incremental (`--fuente email|whatsapp|manual`) resuelva la identidad del caso desde `_caso.md` con un único `--case-id <ref>` en vez de repetir los 6 flags de identidad idénticos al nombre de carpeta.

**Architecture:** Patrón biblioteca. Una función pura nueva en el cerebro (`descomponer_case_id`, inverso de `componer_case_id`), un lector de frontmatter en `case_locator` (`read_case_meta`), y la CLI (`scripts/abrir_caso.py`) que, con `--case-id`, resuelve el `case_id` canónico vía `resolve_ref`, descompone el nombre y lee `tipo_caso`/`ciudad` del `_caso.md` para construir la `Identidad` sin pedir los flags.

**Tech Stack:** Python 3, Typer, `dataclasses`, `re`, `pytest`, `typer.testing.CliRunner`. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-18-apertura-expediente-b1-b5-design.md` (§6). RUNBOOK §5 documenta el dolor.

## Global Constraints

- **Plataforma:** Windows. Encoding **UTF-8 sin BOM** en todo fichero editado.
- **Worktree:** editar SOLO en este worktree (`…\worktrees\feesdefender-input-layout-spec-2b1e28`). **Nunca** `cd`/ruta absoluta a la raíz compartida (`Dev\FeesDefender`) para editar.
- **Ejecutar pytest** con el intérprete del repo principal contra el worktree, desde la raíz del worktree:
  `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest <ruta>::<test> -v`
  Para el conteo global: `--junit-xml`. Los 5 fallos `test_sudespacho_relations::test_list_colaboradores_rest_*` son **ambientales** (falta `SUDESPACHO_*` env), no regresión.
- **`main` protegida:** rama + PR, check `leak-scan` verde. **Nunca** push directo ni `--no-verify`.
- **No tocar** `core/anon/`. **PII por W-code** en docs/commits/ramas.
- **Rama:** `claude/apertura-pr2-case-id` (ya creada desde `origin/main`). Independiente de PR-1 (no toca `intake_log`/`utils`/DTOs). PR-2 se abre desde ella hacia `main`.
- **Contrato preexistente que NO se rompe:** `componer_case_id(codigo, direccion, w_code, sufijo)` produce `f"{codigo} - {direccion} ({w_code}) - {sufijo}"` (dirección pegada al paréntesis, sin guion previo; `core/abrir_caso.py:26-32`). La dirección **puede contener ` - `** (p. ej. `"Passeig Marítim, 30 - Castelldefels (08860)"`) y paréntesis no-W-code (p. ej. `(08860)`). El W-code se ancla con la regex `_W_CODE_EN_NOMBRE = re.compile(r"\((W-[A-Z0-9]+)\)")` (`core/abrir_caso.py:23`).
- TDD estricto, DRY, YAGNI, commits frecuentes.

---

### Task 1: `descomponer_case_id` — inverso puro de `componer_case_id`

**Files:**
- Modify: `core/abrir_caso.py` (añadir función; reutiliza `_W_CODE_EN_NOMBRE` `:23` y el estilo de `_codigo_de` `:54`)
- Test: `tests/test_abrir_caso.py`

**Interfaces:**
- Consumes: nada.
- Produces: `descomponer_case_id(case_id: str) -> tuple[str, str, str, str]` → `(codigo, direccion, w_code, sufijo)`. Inverso exacto de `componer_case_id`; lanza `ValueError` si no hay `(W-...)`.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_abrir_caso.py`:

```python
import pytest

from core.abrir_caso import componer_case_id, descomponer_case_id


@pytest.mark.parametrize("codigo,direccion,w_code,sufijo", [
    ("BaRS11", "Passeig Marítim, 30 - Castelldefels (08860)", "W-02Z2NR", "Vuelta"),
    ("MaRS2", "Puerto Rico 2, 5º 2", "W-0470GM", "Negativa arras"),
    ("VaRS3", "Calle Mayor 1", "W-02TH0W", "Negativa escritura"),
])
def test_descomponer_case_id_round_trip(codigo, direccion, w_code, sufijo):
    case_id = componer_case_id(codigo=codigo, direccion=direccion, w_code=w_code, sufijo=sufijo)
    assert descomponer_case_id(case_id) == (codigo, direccion, w_code, sufijo)


def test_descomponer_case_id_sin_wcode_lanza():
    with pytest.raises(ValueError):
        descomponer_case_id("BaRS11 - Sin referencia - Vuelta")
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_abrir_caso.py -k descomponer -v`
Expected: FAIL con `ImportError: cannot import name 'descomponer_case_id'`.

- [ ] **Step 3: Implementar la función**

Añadir a `core/abrir_caso.py`, tras `componer_case_id` (`:32`):

```python
def descomponer_case_id(case_id: str) -> tuple[str, str, str, str]:
    """Inverso de ``componer_case_id``: (codigo, direccion, w_code, sufijo).

    El W-code se localiza por la forma ``(W-...)`` (no cualquier paréntesis),
    así una dirección con ``(08860)`` o con ` - ` interno se reconstruye bien.
    Lanza ``ValueError`` si el nombre no contiene un W-code en esa forma.
    """
    m = _W_CODE_EN_NOMBRE.search(case_id)
    if not m:
        raise ValueError(f"case_id sin (W-...): {case_id!r}")
    w_code = m.group(1)
    codigo = case_id.split(" - ", 1)[0].strip()
    before = case_id[:m.start()].rstrip()          # "codigo - direccion"
    after = case_id[m.end():].lstrip()             # "- sufijo"
    prefijo = f"{codigo} - "
    direccion = before[len(prefijo):].strip() if before.startswith(prefijo) else before.strip()
    sufijo = after[1:].strip() if after.startswith("-") else after.strip()
    return codigo, direccion, w_code, sufijo
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_abrir_caso.py -k descomponer -v`
Expected: PASS (3 round-trips + el de error).

- [ ] **Step 5: Commit**

```bash
git add core/abrir_caso.py tests/test_abrir_caso.py
git commit -m "feat(abrir-caso): descomponer_case_id, inverso de componer (B2)"
```

---

### Task 2: `read_case_meta` — lector del frontmatter de `_caso.md`

**Files:**
- Modify: `core/casos/case_locator.py` (añadir función junto a `_id_go_of` `:46-69`)
- Test: `tests/test_case_locator.py`

**Interfaces:**
- Consumes: nada.
- Produces: `read_case_meta(case_dir: Path) -> dict` → el dict `meta` del frontmatter de `00_Input/_caso.md` (con claves `tipo_caso`, `ciudad`, `direccion`, `id_go`, …), o `{}` si no existe/está corrupto. No lanza.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_case_locator.py`:

```python
def test_read_case_meta_devuelve_meta(tmp_path):
    from core.casos.case_locator import read_case_meta
    case_dir = tmp_path / "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
    (case_dir / "00_Input").mkdir(parents=True)
    (case_dir / "00_Input" / "_caso.md").write_text(
        "---\n"
        "ciudad: Barcelona\n"
        "meta:\n"
        "  tipo_caso: VUELTA\n"
        "  ciudad: Barcelona\n"
        "  direccion: Falsa 1\n"
        "  id_go: W-000AAA\n"
        "---\n\n# Caso\n",
        encoding="utf-8",
    )
    meta = read_case_meta(case_dir)
    assert meta["tipo_caso"] == "VUELTA"
    assert meta["ciudad"] == "Barcelona"
    assert meta["id_go"] == "W-000AAA"


def test_read_case_meta_sin_fichero_devuelve_vacio(tmp_path):
    from core.casos.case_locator import read_case_meta
    assert read_case_meta(tmp_path / "no-existe") == {}
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_case_locator.py -k read_case_meta -v`
Expected: FAIL con `ImportError: cannot import name 'read_case_meta'`.

- [ ] **Step 3: Implementar la función**

Añadir a `core/casos/case_locator.py`, tras `_id_go_of` (`:69`):

```python
def read_case_meta(case_dir: Path) -> dict:
    """Lee el dict ``meta`` del frontmatter de ``00_Input/_caso.md``.

    Devuelve ``{}`` si el fichero no existe, no tiene frontmatter válido, o el
    YAML está corrupto. No lanza (mismo criterio tolerante que ``_id_go_of``).
    """
    import yaml

    caso_md = case_dir / "00_Input" / "_caso.md"
    if not caso_md.is_file():
        return {}
    try:
        text = caso_md.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}
    meta = fm.get("meta") if isinstance(fm, dict) else None
    return meta if isinstance(meta, dict) else {}
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_case_locator.py -k read_case_meta -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add core/casos/case_locator.py tests/test_case_locator.py
git commit -m "feat(case-locator): read_case_meta lee el meta de _caso.md (B2)"
```

---

### Task 3: CLI `--case-id` en `scripts/abrir_caso.py`

**Files:**
- Modify: `scripts/abrir_caso.py` (opciones de `main` `:291-310`; flujo de identidad `:319-338`)
- Test: `tests/test_abrir_caso_cli.py`

**Interfaces:**
- Consumes: `brain.descomponer_case_id` (Task 1), `case_locator.read_case_meta` (Task 2), `case_locator.resolve_ref`/`path_for` (existentes), `brain.resolver_identidad` (existente).
- Produces: la CLI acepta `--case-id <ref>` (case_id canónico **o** W-code) como alternativa **excluyente** a los 6 flags de identidad. Con `--case-id`, resuelve identidad + `tipo_caso`/`ciudad` desde `_caso.md` (el caso debe existir).

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_abrir_caso_cli.py` (el fixture `drive_temporal` y el helper `_args` ya existen):

```python
def test_cli_case_id_resuelve_identidad_por_wcode(drive_temporal, tmp_path):
    # 1) Crear el caso con una pasada normal (drive_ev).
    r1 = CliRunner().invoke(cli.app, _args())
    assert r1.exit_code == 0, r1.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"

    # 2) Intake incremental con --case-id (W-code) + fuente manual, sin repetir los 6 flags.
    src = tmp_path / "extra"
    src.mkdir()
    (src / "nota.txt").write_bytes(b"contenido incremental")
    r2 = CliRunner().invoke(cli.app, [
        "--case-id", "W-02Z2NR", "--fuente", "manual", "--src", str(src), "--yes",
    ])
    assert r2.exit_code == 0, r2.output

    # El intake fue al MISMO caso (no una carpeta nueva) y se logeó upload_manual.
    eventos = intake_log.read_events(case_id)
    assert any(e["event"] == "upload_manual" for e in eventos)


def test_cli_case_id_excluyente_con_flags_de_identidad(drive_temporal):
    r = CliRunner().invoke(cli.app, [
        "--case-id", "W-02Z2NR", "--w-code", "W-02Z2NR",
        "--fuente", "manual", "--src", "x", "--yes",
    ])
    assert r.exit_code != 0
    assert "excluyente" in r.output.lower()


def test_cli_sin_case_id_ni_flags_falla(drive_temporal):
    r = CliRunner().invoke(cli.app, ["--fuente", "manual", "--src", "x", "--yes"])
    assert r.exit_code != 0
    assert "identidad" in r.output.lower()


def test_cli_case_id_caso_inexistente_falla(drive_temporal, tmp_path):
    src = tmp_path / "e"
    src.mkdir()
    (src / "a.txt").write_bytes(b"x")
    r = CliRunner().invoke(cli.app, [
        "--case-id", "W-NOEXISTE", "--fuente", "manual", "--src", str(src), "--yes",
    ])
    assert r.exit_code != 0
    assert "no encontrado" in r.output.lower()
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_abrir_caso_cli.py -k case_id -v`
Expected: FAIL (no existe la opción `--case-id`; Typer la rechaza → exit code de "No such option", y los asserts de contenido fallan).

- [ ] **Step 3: Hacer opcionales los 6 flags de identidad y añadir `--case-id`**

En `scripts/abrir_caso.py`, en la firma de `main` (`:291-297`), cambiar los 6 flags de `typer.Option(..., ...)` a opcionales y añadir `--case-id`:

```python
    w_code: str | None = typer.Option(None, "--w-code"),
    ciudad: str | None = typer.Option(None, "--ciudad"),
    tipo_caso: str | None = typer.Option(None, "--tipo-caso"),
    codigo_caso: str | None = typer.Option(None, "--codigo-caso"),
    sufijo: str | None = typer.Option(None, "--sufijo"),
    direccion: str | None = typer.Option(None, "--direccion"),
    case_id: str | None = typer.Option(
        None, "--case-id",
        help="Intake incremental: resuelve identidad desde _caso.md (case_id o W-code). "
             "Excluyente con los 6 flags de identidad.",
    ),
    folder_id: str | None = typer.Option(None, "--folder-id"),
```

(El resto de opciones, `:298-309`, se mantienen igual.)

- [ ] **Step 4: Reescribir el bloque de resolución de identidad**

En `scripts/abrir_caso.py`, sustituir **todo el bloque desde la línea `if ciudad not in CIUDADES:` (`:311`) hasta la línea `case_dir = case_locator.path_for(ident.case_id)` (`:339`) ambas incluidas** — es decir, el chequeo de ciudad original, el chequeo de fuente, la resolución de identidad + colisión, el `ensure_case` y el `case_dir =` — por el bloque siguiente (que reintroduce el chequeo de fuente, ambas vías de identidad, un único chequeo de ciudad, el `ensure_case` y el `case_dir =`). La línea siguiente del fichero (`# 5.3-5.7 intake por fuente` + `_despachar_intake(...)`) NO se toca:

```python
    if fuente not in _FUENTES_CLI:
        typer.echo(f"[ERROR] Fuente desconocida: {fuente}. Válidas: {_FUENTES_CLI}", err=True)
        raise typer.Exit(code=1)

    # 5.1 identidad — dos vías excluyentes: --case-id (intake incremental) o los 6 flags.
    flags_ident = [
        ("--w-code", w_code), ("--ciudad", ciudad), ("--tipo-caso", tipo_caso),
        ("--codigo-caso", codigo_caso), ("--sufijo", sufijo), ("--direccion", direccion),
    ]
    if case_id is not None:
        dados = [n for n, v in flags_ident if v is not None]
        if dados:
            typer.echo(f"[ERROR] --case-id es excluyente con los flags de identidad: {dados}", err=True)
            raise typer.Exit(code=1)
        resolved = case_locator.resolve_ref(case_id)
        case_dir = case_locator.path_for(resolved)
        if not (case_dir / "00_Input" / "_caso.md").is_file():
            typer.echo(f"[ERROR] Caso no encontrado para --case-id {case_id!r} "
                       f"(resuelto: {resolved!r})", err=True)
            raise typer.Exit(code=1)
        meta = case_locator.read_case_meta(case_dir)
        tipo_caso_eff, ciudad = meta.get("tipo_caso"), meta.get("ciudad")
        if not tipo_caso_eff or not ciudad:
            typer.echo("[ERROR] _caso.md sin tipo_caso/ciudad; usa los flags de identidad", err=True)
            raise typer.Exit(code=1)
        codigo_p, direccion_p, w_code_p, sufijo_p = brain.descomponer_case_id(resolved)
        ident = brain.resolver_identidad(
            codigo=codigo_p, direccion=direccion_p, w_code=w_code_p, sufijo=sufijo_p,
            tipo_caso=tipo_caso_eff, nombres_existentes=[], force=True,
        )
    else:
        faltan = [n for n, v in flags_ident if v is None]
        if faltan:
            typer.echo(f"[ERROR] faltan flags de identidad {faltan} (o usa --case-id)", err=True)
            raise typer.Exit(code=1)
        if ciudad not in CIUDADES:
            typer.echo(f"[ERROR] Ciudad desconocida: {ciudad}", err=True)
            raise typer.Exit(code=1)
        nombres = [p.name for p in case_locator.list_cases(ciudad)]
        try:
            ident = brain.resolver_identidad(
                codigo=codigo_caso, direccion=direccion, w_code=w_code, sufijo=sufijo,
                tipo_caso=tipo_caso, nombres_existentes=nombres, force=force,
            )
        except brain.ColisionCaso as exc:
            typer.echo(f"[ERROR] {exc}", err=True)
            raise typer.Exit(code=1)
        if ident.requiere_confirmacion and not force:
            typer.echo(f"[AVISO] El código {ident.codigo} ya existe: {ident.colisiones}")
            if not (yes or typer.confirm("¿Crear igualmente con este código?")):
                raise typer.Exit(code=1)

    if ciudad not in CIUDADES:
        typer.echo(f"[ERROR] Ciudad desconocida: {ciudad}", err=True)
        raise typer.Exit(code=1)

    # 5.2 esqueleto (idempotente; con --case-id el caso ya existe)
    case_manager.ensure_case(
        ident.case_id, titulo=ident.case_id, referencia_crm=ident.case_id,
        tipo_caso=ident.tipo_caso, ciudad=ciudad, direccion=ident.direccion, id_go=ident.w_code,
    )
    case_dir = case_locator.path_for(ident.case_id)
```

Notas: (1) `ident.tipo_caso`/`ident.direccion`/`ident.w_code` existen en `Identidad` — unifican ambas vías. (2) La validación `ciudad not in CIUDADES` corre en ambas vías (redundante en la de flags, barata; imprescindible en la de `--case-id`). (3) Con `--case-id` + `--fuente drive_ev` seguirían haciendo falta `--folder-id`/`--team-id` (el re-pull de Drive los necesita; B5 los auto-derivará). El caso de uso de B2 es el intake incremental por `email`/`whatsapp`/`manual` (RUNBOOK §5).

- [ ] **Step 5: Ejecutar los tests de `--case-id`**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_abrir_caso_cli.py -k case_id -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Regresión del fichero CLI completo (el camino de los 6 flags no rompe)**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_abrir_caso_cli.py -v`
Expected: PASS (todos, incluidos los preexistentes `test_cli_pasada_completa_*`, `test_cli_idempotente_*`, `test_cli_persiste_id_go_*`).

- [ ] **Step 7: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(abrir-caso): --case-id resuelve identidad desde _caso.md (B2)"
```

---

### Task 4: Verificación de PR-2 + apertura de PR

**Files:** ninguno (verificación + git + docs).

- [ ] **Step 1: Actualizar RUNBOOK §5 (doc de la spec §10)**

En `docs/RUNBOOK_APERTURA_EXPEDIENTE.md §5`, sustituir el bloque que dice que el intake incremental "hoy obliga a repetir los 6 flags" + "→ *Build en cola:* `--case-id`" por una nota de que **ya está disponible**: `python -m scripts.abrir_caso --case-id "<W-code o case_id>" --fuente email|whatsapp|manual …` resuelve la identidad desde `_caso.md`. Commit:

```bash
git add docs/RUNBOOK_APERTURA_EXPEDIENTE.md
git commit -m "docs(runbook): §5 --case-id disponible para intake incremental (B2)"
```

- [ ] **Step 2: Suite completa a JUnit XML (conteo fiable)**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q -p no:randomly --junit-xml=.pr2_report.xml`
Expected: 0 fallos nuevos respecto al baseline; los 5 fallos de `test_sudespacho_relations::test_list_colaboradores_rest_*` son ambientales. Verificar en el XML que los nuevos tests de Task 1-3 están en `passed`.

- [ ] **Step 3: Limpiar el artefacto**

```bash
rm -f .pr2_report.xml
```

(Verificar que no queda en `git status`.)

- [ ] **Step 4: Push + PR**

```bash
git push -u origin claude/apertura-pr2-case-id
```

Abrir PR con `gh` hacia `main` (título: `PR-2 apertura: --case-id para intake incremental (B2)`; cuerpo enlazando la spec §6 y este plan; nota de que es independiente de PR-1 y puede mergear en cualquier orden). Confirmar `leak-scan` **verde**.

- [ ] **Step 5: Revisión adversarial antes de mergear**

Revisión de rama completa (workflow/`requesting-code-review`) sobre el diff. Resolver Critical/Important antes del merge.

---

## Self-Review (hecho al escribir el plan)

- **Cobertura de spec §6:** `descomponer_case_id` (Task 1) ✓; `--case-id` XOR los 6 flags + resolución desde `_caso.md` vía `resolve_ref` (Task 3) ✓. Añadido `read_case_meta` (Task 2) porque no existía lector público de `tipo_caso`/`ciudad` (`get_case_status` solo da `local_exists`/`expedientes`) — es el mínimo necesario, sin sobre-construir.
- **Placeholders:** ninguno; todo el código y comandos son literales.
- **Consistencia de tipos/nombres:** `descomponer_case_id(str)->tuple[str,str,str,str]` idéntico en Task 1 (def) y Task 3 (uso). `read_case_meta(Path)->dict` idéntico en Task 2 (def) y Task 3 (uso). `Identidad` expone `tipo_caso`/`direccion`/`w_code`/`case_id` (verificado `core/abrir_caso.py:39-52`), usados en el `ensure_case`.
- **Contrato de `componer`/`descomponer`:** los round-trips de Task 1 incluyen una dirección con ` - ` interno y con `(08860)` — casos reales que romperían un split ingenuo; la regex `_W_CODE_EN_NOMBRE` los desambigua.
- **No regresión del camino de flags:** Task 3 Step 6 corre toda la suite del CLI; el bloque reescrito preserva la guarda de colisión y la confirmación del camino de los 6 flags.
