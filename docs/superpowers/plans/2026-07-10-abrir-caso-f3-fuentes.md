# abrir-caso F3 (A+C) — Fuentes no-Drive + init_caso — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a la CLI `scripts/abrir_caso.py` las fuentes de arranque `manual`, `whatsapp` y `email` (además de `drive_ev`), delegando el depósito a los escritores nativos, con custodia forense uniforme; documentar la relación con `init_caso.py`.

**Architecture:** El cerebro puro `core/abrir_caso.py` NO cambia (ya soporta las fuentes). Todo el trabajo es en el orquestador CLI: se extrae la lógica genérica de F1 a `_intake_generico`, se añade un dispatch por `--fuente`, y cada fuente enruta a su músculo. WhatsApp/email se auto-loguean (escritor nativo); Drive/manual los loguea el orquestador. Una fuente por invocación; reentrante.

**Tech Stack:** Python, Typer, `pytest` + `typer.testing.CliRunner`. Reutiliza `core.intake_drive`, `core.intake_manual`, `core.whatsapp_intake`, `core.email_export`, `core.intake_log`, `core.config`.

**Spec:** `docs/superpowers/specs/2026-07-10-abrir-caso-f3-fuentes-design.md`.

**Comando de tests (venv):** `"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest <ruta> -v`

---

## File Structure

- **Modify** `scripts/abrir_caso.py` — refactor a dispatch por fuente; nuevas opciones `--fuente/--src/--rol/--cuenta/--label`; helpers `_validar_flags`, `_intake_generico`, `_intake_drive_ev`, `_depositar_manual`, `_inventario_local`, `_intake_manual`, `_intake_whatsapp`, `_intake_email`, `_despachar_intake`.
- **Modify** `scripts/init_caso.py` — nota de relación en el docstring (parte C).
- **Modify** `tests/test_abrir_caso_cli.py` — tests nuevos por fuente (patrón F1: fixture + `CliRunner`).
- **Modify** `PLAN.md` — reconciliar estado (F2a mergeada) + registrar decisión init_caso.

Diseño clave de custodia (§3.1 spec): `_intake_generico` recibe un dict `hashes = {relpath_desde_00_Input: sha256}` que cubre **solo los ficheros recién depositados** (no toda la subcarpeta). Así `reconcile` no ve como `extras` ficheros de intakes manuales previos. Para `drive_ev` la subcarpeta se acaba de bajar (fresca) ⇒ hashear todo el árbol es correcto; para `manual` se hashea solo lo depositado en esta pasada.

---

### Task 1: Refactor F1 a dispatch + opción `--fuente` (drive_ev intacto)

**Files:** Modify `scripts/abrir_caso.py`, `tests/test_abrir_caso_cli.py`.

Red de seguridad: los tests F1 existentes (`tests/test_abrir_caso_cli.py`) deben seguir verdes tras el refactor.

- [ ] **Step 1: Ejecutar la suite F1 (baseline verde)**

Run: `... -m pytest tests/test_abrir_caso_cli.py -v`
Expected: PASS (todos los tests F1 actuales).

- [ ] **Step 2: Añadir el test del dispatch explícito drive_ev**

Añadir a `tests/test_abrir_caso_cli.py`:

```python
def test_cli_fuente_drive_ev_explicita_equivale_a_default(drive_temporal):
    """--fuente drive_ev explícito da el mismo resultado que el default."""
    result = CliRunner().invoke(cli.app, _args(fuente="drive_ev"))
    assert result.exit_code == 0, result.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    eventos = intake_log.read_events(case_id)
    assert any(e["event"] == "pull_drive_ev" for e in eventos)
```

- [ ] **Step 3: Run → fail**

Run: `... -m pytest tests/test_abrir_caso_cli.py::test_cli_fuente_drive_ev_explicita_equivale_a_default -v`
Expected: FAIL (Typer: `No such option: --fuente`).

- [ ] **Step 4: Refactor de `scripts/abrir_caso.py`**

Añadir imports arriba (junto a los existentes):

```python
import hashlib
import shutil
import zipfile

from core import config
```

Añadir el conjunto de fuentes válidas de CLI y el helper genérico (tras `hash_tree_local`):

```python
_FUENTES_CLI = ("drive_ev", "manual", "whatsapp", "email")


def _inventario_desde_hashes(case_dir: Path, subdir: str, hashes: dict[str, str]) -> list[dict]:
    """Inventario {relpath, sha256, size} a partir de {subdir/rel: sha}."""
    return [
        {"relpath": k[len(subdir) + 1:], "sha256": v,
         "size": (case_dir / "00_Input" / k).stat().st_size}
        for k, v in hashes.items()
    ]


def _intake_generico(
    case_dir: Path, case_id: str, fuente: str, hashes: dict[str, str], *, dry_run: bool
) -> None:
    """Camino de custodia orquestado (drive_ev, manual): plan → (dry-run) →
    reconcile → append_event. `hashes` cubre SOLO lo recién depositado."""
    inventario = _inventario_desde_hashes(case_dir, brain.FUENTE_A_SUBDIR[fuente], hashes)
    plan = brain.plan_intake(inventario, intake_log.read_events(case_id), fuente)
    if dry_run:
        typer.echo(f"[dry-run] {len(plan.depositables)} depositables, "
                   f"{len(plan.items) - len(plan.depositables)} omitidos")
        return
    n_dup = sum(1 for i in plan.items if i.dup)
    n_zero = sum(1 for i in plan.items if i.zero)
    typer.echo(f"Intake: {len(plan.depositables)} depositables, "
               f"{n_dup} duplicados omitidos, {n_zero} de 0 bytes omitidos")
    rec = brain.reconcile(plan, hashes)
    if not rec.ok:
        typer.echo(f"[ERROR] Reconciliación falló: faltan={rec.faltantes} "
                   f"mismatch={rec.mismatches} extra={rec.extras}", err=True)
        raise typer.Exit(code=1)
    if plan.con_sha:
        intake_log.append_event(case_id, brain.FUENTE_A_EVENTO[fuente],
                                details={"count": len(plan.con_sha), "files": plan.con_sha})


def _intake_drive_ev(ident, case_dir: Path, folder_id, team_id, *, dry_run: bool) -> None:
    intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id)
    subdir = brain.FUENTE_A_SUBDIR["drive_ev"]
    hashes = hash_tree_local(case_dir / "00_Input" / subdir, prefijo=subdir)
    _intake_generico(case_dir, ident.case_id, "drive_ev", hashes, dry_run=dry_run)
```

Reescribir el bloque central de `main()` (el que hoy hace pull+hash+plan+dry-run+reconcile+log, líneas ~131-166) por una sola llamada al dispatcher. Sustituir desde `# 5.3 pull + hash local (D4)` hasta antes de `_alta_crm(...)` por:

```python
    # 5.3-5.7 intake por fuente
    _despachar_intake(
        fuente, ident, case_dir,
        folder_id=folder_id, team_id=team_id, src=src, rol=rol,
        cuenta=cuenta, label=label, dry_run=dry_run,
    )
    if dry_run:
        typer.echo(f"[dry-run] esqueleto en {case_dir}; se omiten log de intake y alta CRM")
        raise typer.Exit(code=0)
```

Añadir el dispatcher (por ahora solo drive_ev; las demás ramas llegan en Tasks 3-5):

```python
def _despachar_intake(fuente, ident, case_dir, *, folder_id, team_id, src, rol,
                      cuenta, label, dry_run):
    if fuente == "drive_ev":
        _intake_drive_ev(ident, case_dir, folder_id, team_id, dry_run=dry_run)
    else:
        raise typer.Exit(code=1)  # ramas manual/whatsapp/email: Tasks 3-5
```

Añadir las opciones nuevas a la firma de `main()` (tras `team_id`):

```python
    fuente: str = typer.Option("drive_ev", "--fuente", help="drive_ev|manual|whatsapp|email"),
    src: str | None = typer.Option(None, "--src", help="manual/whatsapp: carpeta o .zip"),
    rol: str | None = typer.Option(None, "--rol", help="whatsapp: rol_subdir"),
    cuenta: str | None = typer.Option(None, "--cuenta", help="email: cuenta gmail"),
    label: str | None = typer.Option(None, "--label", help="email: etiqueta"),
```

Y justo tras la validación de ciudad, validar la fuente:

```python
    if fuente not in _FUENTES_CLI:
        typer.echo(f"[ERROR] Fuente desconocida: {fuente}. Válidas: {_FUENTES_CLI}", err=True)
        raise typer.Exit(code=1)
```

- [ ] **Step 5: Run → el nuevo test pasa y F1 sigue verde**

Run: `... -m pytest tests/test_abrir_caso_cli.py -v`
Expected: PASS (F1 + el nuevo test).

- [ ] **Step 6: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "refactor(abrir-caso): dispatch por --fuente; _intake_generico extraído (drive_ev intacto)"
```

---

### Task 2: Validación de flags por fuente

**Files:** Modify `scripts/abrir_caso.py`, `tests/test_abrir_caso_cli.py`.

- [ ] **Step 1: Tests de validación**

Añadir a `tests/test_abrir_caso_cli.py`:

```python
def _args_min(**over):
    """Args base SIN los flags específicos de drive_ev (folder-id/team-id)."""
    base = [
        "--w-code", "W-02Z2NR", "--ciudad", "Barcelona", "--tipo-caso", "VUELTA",
        "--codigo-caso", "BaRS11", "--sufijo", "Vuelta",
        "--direccion", "Passeig Marítim 30", "--yes",
    ]
    for k, v in over.items():
        base += [f"--{k}", v]
    return base


def test_cli_manual_sin_src_exit_1(drive_temporal):
    result = CliRunner().invoke(cli.app, _args_min(fuente="manual"))
    assert result.exit_code == 1
    assert "--src" in result.output


def test_cli_whatsapp_sin_rol_exit_1(drive_temporal, tmp_path):
    z = tmp_path / "x.zip"
    z.write_bytes(b"PK")
    result = CliRunner().invoke(cli.app, _args_min(fuente="whatsapp", src=str(z)))
    assert result.exit_code == 1
    assert "--rol" in result.output


def test_cli_email_flags_ajenos_exit_1(drive_temporal):
    """email con --src (ajeno) debe fallar."""
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="email", cuenta="a@b.com", label="Caso", src="/x"))
    assert result.exit_code == 1
    assert "ajeno" in result.output.lower()


def test_cli_whatsapp_rol_invalido_exit_1(drive_temporal, tmp_path):
    z = tmp_path / "x.zip"
    z.write_bytes(b"PK")
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="whatsapp", src=str(z), rol="99_Inexistente"))
    assert result.exit_code == 1
    assert "rol" in result.output.lower()
```

- [ ] **Step 2: Run → fail**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k "sin_src or sin_rol or ajenos or rol_invalido" -v`
Expected: FAIL (aún no hay validación; p. ej. `manual` cae en el `raise Exit(1)` genérico pero sin el mensaje `--src`, o la rama no valida el rol).

- [ ] **Step 3: Implementar `_validar_flags`** en `scripts/abrir_caso.py` (antes de `_despachar_intake`):

```python
def _validar_flags(fuente, *, folder_id, team_id, src, rol, cuenta, label) -> None:
    """Exige los flags propios de la fuente y rechaza los ajenos (fail-fast)."""
    requeridos = {
        "drive_ev": [],
        "manual": [("--src", src)],
        "whatsapp": [("--src", src), ("--rol", rol)],
        "email": [("--cuenta", cuenta), ("--label", label)],
    }[fuente]
    faltan = [n for n, v in requeridos if not v]
    if faltan:
        typer.echo(f"[ERROR] Fuente {fuente}: faltan flags {faltan}", err=True)
        raise typer.Exit(code=1)

    ajenos = {
        "drive_ev": [("--src", src), ("--rol", rol), ("--cuenta", cuenta), ("--label", label)],
        "manual": [("--rol", rol), ("--cuenta", cuenta), ("--label", label),
                   ("--folder-id", folder_id), ("--team-id", team_id)],
        "whatsapp": [("--cuenta", cuenta), ("--label", label),
                     ("--folder-id", folder_id), ("--team-id", team_id)],
        "email": [("--src", src), ("--rol", rol),
                  ("--folder-id", folder_id), ("--team-id", team_id)],
    }[fuente]
    presentes = [n for n, v in ajenos if v]
    if presentes:
        typer.echo(f"[ERROR] Fuente {fuente}: flags ajenos a la fuente {presentes}", err=True)
        raise typer.Exit(code=1)

    if fuente == "whatsapp" and rol not in config.WHATSAPP_SUBDIRS:
        typer.echo(f"[ERROR] rol inválido: {rol}. Válidos: {config.WHATSAPP_SUBDIRS}", err=True)
        raise typer.Exit(code=1)
```

Llamar a `_validar_flags` dentro de `_despachar_intake`, como primera línea:

```python
def _despachar_intake(fuente, ident, case_dir, *, folder_id, team_id, src, rol,
                      cuenta, label, dry_run):
    _validar_flags(fuente, folder_id=folder_id, team_id=team_id, src=src, rol=rol,
                   cuenta=cuenta, label=label)
    if fuente == "drive_ev":
        _intake_drive_ev(ident, case_dir, folder_id, team_id, dry_run=dry_run)
    else:
        raise typer.Exit(code=1)  # manual/whatsapp/email: Tasks 3-5
```

- [ ] **Step 4: Run → pass**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k "sin_src or sin_rol or ajenos or rol_invalido" -v`
Expected: PASS. Y la suite completa del fichero sigue verde: `... -m pytest tests/test_abrir_caso_cli.py -v`.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(abrir-caso): validación de flags por fuente (requeridos + ajenos + rol)"
```

---

### Task 3: Fuente `manual` (zip + carpeta) con evento forense

**Files:** Modify `scripts/abrir_caso.py`, `tests/test_abrir_caso_cli.py`.

- [ ] **Step 1: Tests de manual**

Añadir a `tests/test_abrir_caso_cli.py`:

```python
def _crear_carpeta_manual(tmp_path):
    src = tmp_path / "aportado"
    (src / "sub").mkdir(parents=True)
    (src / "escrito.pdf").write_bytes(b"ESCRITO")
    (src / "sub" / "anexo.pdf").write_bytes(b"ANEXO")
    return src


def test_cli_manual_carpeta_deposita_y_loguea(drive_temporal, tmp_path):
    src = _crear_carpeta_manual(tmp_path)
    result = CliRunner().invoke(cli.app, _args_min(fuente="manual", src=str(src)) + ["--crm", "skip"])
    assert result.exit_code == 0, result.output

    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    case_dir = case_locator.path_for(case_id)
    assert (case_dir / "00_Input" / "04_Manual" / "escrito.pdf").is_file()
    assert (case_dir / "00_Input" / "04_Manual" / "sub" / "anexo.pdf").is_file()

    eventos = intake_log.read_events(case_id)
    manuales = [e for e in eventos if e["event"] == "upload_manual"]
    assert manuales and len(manuales[-1]["details"]["files"]) == 2
    assert all(f["sha256"] for f in manuales[-1]["details"]["files"])


def test_cli_manual_zip_deposita(drive_temporal, tmp_path):
    import zipfile as _zf
    z = tmp_path / "aportado.zip"
    with _zf.ZipFile(z, "w") as zf:
        zf.writestr("carpeta/doc.pdf", b"DOC")
    result = CliRunner().invoke(cli.app, _args_min(fuente="manual", src=str(z)) + ["--crm", "skip"])
    assert result.exit_code == 0, result.output
    case_dir = case_locator.path_for("BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta")
    assert (case_dir / "00_Input" / "04_Manual" / "carpeta" / "doc.pdf").is_file()


def test_cli_manual_dry_run_no_deposita(drive_temporal, tmp_path):
    src = _crear_carpeta_manual(tmp_path)
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="manual", src=str(src)) + ["--dry-run"])
    assert result.exit_code == 0, result.output
    case_dir = case_locator.path_for("BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta")
    assert not (case_dir / "00_Input" / "04_Manual" / "escrito.pdf").exists()


def test_cli_manual_reentrante_dedup(drive_temporal, tmp_path):
    src = _crear_carpeta_manual(tmp_path)
    a = _args_min(fuente="manual", src=str(src)) + ["--crm", "skip"]
    r1 = CliRunner().invoke(cli.app, a)
    assert r1.exit_code == 0, r1.output
    r2 = CliRunner().invoke(cli.app, a + ["--force"])
    assert r2.exit_code == 0, r2.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    manuales = [e for e in intake_log.read_events(case_id) if e["event"] == "upload_manual"]
    # 2ª pasada: todo dup → no nuevo evento
    assert len(manuales) == 1


def test_cli_manual_src_inexistente_exit_1(drive_temporal):
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="manual", src="/no/existe/ruta") + ["--crm", "skip"])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output
```

- [ ] **Step 2: Run → fail**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k manual -v`
Expected: FAIL (la rama manual aún hace `raise Exit(1)`).

- [ ] **Step 3: Implementar la rama manual** en `scripts/abrir_caso.py`.

Añadir helpers (tras `_intake_drive_ev`):

```python
def _inventario_local(src: Path) -> list[dict]:
    """Inventario {relpath, sha256, size} de un origen local (carpeta o .zip),
    SIN copiar. Usado por el dry-run de manual."""
    items: list[dict] = []
    if src.is_dir():
        for p in sorted(src.rglob("*")):
            if p.is_file():
                data = p.read_bytes()
                items.append({"relpath": p.relative_to(src).as_posix(),
                              "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    elif zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as zf:
            for m in zf.infolist():
                if m.is_dir():
                    continue
                data = zf.read(m)
                items.append({"relpath": m.filename,
                              "sha256": hashlib.sha256(data).hexdigest(), "size": m.file_size})
    else:
        raise FileNotFoundError(f"--src no es carpeta ni .zip: {src}")
    return items


def _depositar_manual(case_id: str, src: Path) -> list[str]:
    """Deposita el origen en 04_Manual y devuelve los relpath (posix) depositados
    en ESTA pasada (no toda la carpeta)."""
    manual_dir = case_locator.path_for(case_id) / "00_Input" / "04_Manual"
    manual_dir.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(src):
        paths = intake_manual.extract_zip(case_id, src.read_bytes())
        return [p.relative_to(manual_dir).as_posix() for p in paths]
    if src.is_dir():
        depositados: list[str] = []
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(src)
            dest = manual_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read_bytes())
            depositados.append(rel.as_posix())
        return depositados
    raise FileNotFoundError(f"--src no es carpeta ni .zip: {src}")


def _intake_manual(ident, case_dir: Path, src_str: str, *, dry_run: bool) -> None:
    src = Path(src_str)
    subdir = brain.FUENTE_A_SUBDIR["manual"]
    if dry_run:
        try:
            inv = _inventario_local(src)
        except FileNotFoundError as exc:
            typer.echo(f"[ERROR] {exc}", err=True)
            raise typer.Exit(code=1)
        plan = brain.plan_intake(inv, intake_log.read_events(ident.case_id), "manual")
        typer.echo(f"[dry-run] manual: {len(plan.depositables)} depositables (sin depositar)")
        return
    try:
        rels = _depositar_manual(ident.case_id, src)
    except FileNotFoundError as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=1)
    hashes = {
        f"{subdir}/{rel}": file_sha256(case_dir / "00_Input" / subdir / rel)
        for rel in rels
    }
    _intake_generico(case_dir, ident.case_id, "manual", hashes, dry_run=False)
```

Importar `intake_manual` en el bloque de imports de `core` (línea ~18): añadir `intake_manual` a la lista `from core import ...`.

Enrutar en `_despachar_intake`:

```python
    elif fuente == "manual":
        _intake_manual(ident, case_dir, src, dry_run=dry_run)
```

- [ ] **Step 4: Run → pass**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k manual -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(abrir-caso): fuente manual (zip+carpeta) con evento forense upload_manual"
```

---

### Task 4: Fuente `whatsapp` (delegación a deposit_export)

**Files:** Modify `scripts/abrir_caso.py`, `tests/test_abrir_caso_cli.py`.

Enfoque: el orquestador **delega** en `whatsapp_intake.deposit_export`, que ya deposita+loguea+deduplica. El test verifica la llamada correcta y la ausencia de doble log (se mockea `deposit_export`; su comportamiento propio ya está testeado en `tests/test_whatsapp_intake*`).

- [ ] **Step 1: Tests de whatsapp**

Añadir a `tests/test_abrir_caso_cli.py`:

```python
def test_cli_whatsapp_delega_en_deposit_export(drive_temporal, tmp_path, monkeypatch):
    z = tmp_path / "chat.zip"
    z.write_bytes(b"PK\x03\x04fake")
    llamadas = {}

    def spy(case_id, rol_subdir, content, *, zip_name, **kw):
        llamadas.update(case_id=case_id, rol=rol_subdir, n=len(content), zip_name=zip_name)
        return type("R", (), {"skipped_dedup": False, "chat_dir": tmp_path})()

    monkeypatch.setattr("core.whatsapp_intake.deposit_export", spy)
    result = CliRunner().invoke(
        cli.app,
        _args_min(fuente="whatsapp", src=str(z), rol="00_Consultor propietario") + ["--crm", "skip"],
    )
    assert result.exit_code == 0, result.output
    assert llamadas["rol"] == "00_Consultor propietario"
    assert llamadas["case_id"] == "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    assert llamadas["n"] > 0
    # el orquestador NO emite un segundo evento (lo hace deposit_export, aquí mockeado)
    eventos = intake_log.read_events(llamadas["case_id"])
    assert [e for e in eventos if e["event"] == "upload_whatsapp"] == []


def test_cli_whatsapp_dry_run_no_llama(drive_temporal, tmp_path, monkeypatch):
    z = tmp_path / "chat.zip"
    z.write_bytes(b"PK")
    llamado = {"v": False}
    monkeypatch.setattr("core.whatsapp_intake.deposit_export",
                        lambda *a, **k: llamado.__setitem__("v", True))
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="whatsapp", src=str(z), rol="03_Otros") + ["--dry-run"])
    assert result.exit_code == 0, result.output
    assert llamado["v"] is False


def test_cli_whatsapp_dedup_reporta(drive_temporal, tmp_path, monkeypatch):
    z = tmp_path / "chat.zip"
    z.write_bytes(b"PKdup")
    monkeypatch.setattr(
        "core.whatsapp_intake.deposit_export",
        lambda *a, **k: type("R", (), {"skipped_dedup": True, "chat_dir": tmp_path})())
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="whatsapp", src=str(z), rol="03_Otros") + ["--crm", "skip"])
    assert result.exit_code == 0, result.output
    assert "dedup" in result.output.lower() or "ya importado" in result.output.lower()
```

- [ ] **Step 2: Run → fail**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k whatsapp -v`
Expected: FAIL (rama whatsapp aún `raise Exit(1)`; los tests de validación de Task 2 siguen verdes).

- [ ] **Step 3: Implementar la rama whatsapp**

Añadir `whatsapp_intake` al import `from core import ...`. Añadir helper (tras `_intake_manual`):

```python
def _intake_whatsapp(ident, src_str: str, rol: str, *, dry_run: bool) -> None:
    src = Path(src_str)
    if not src.is_file():
        typer.echo(f"[ERROR] --src no existe: {src}", err=True)
        raise typer.Exit(code=1)
    if dry_run:
        typer.echo(f"[dry-run] whatsapp: se depositaría {src.name} en rol {rol} (sin ejecutar)")
        return
    res = whatsapp_intake.deposit_export(
        ident.case_id, rol, src.read_bytes(), zip_name=src.name)
    if getattr(res, "skipped_dedup", False):
        typer.echo("WhatsApp: export ya importado (dedup), nada nuevo")
    else:
        typer.echo(f"WhatsApp depositado en {getattr(res, 'chat_dir', '?')}")
```

Enrutar en `_despachar_intake`:

```python
    elif fuente == "whatsapp":
        _intake_whatsapp(ident, src, rol, dry_run=dry_run)
```

- [ ] **Step 4: Run → pass**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k whatsapp -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(abrir-caso): fuente whatsapp (delegación a deposit_export, sin doble log)"
```

---

### Task 5: Fuente `email` (delegación a export_label)

**Files:** Modify `scripts/abrir_caso.py`, `tests/test_abrir_caso_cli.py`.

Enfoque: delegar en `email_export.export_label(cuenta, label, dest, case_id=case_id)`, que exporta la etiqueta Gmail a `03_Email` y auto-emite `upload_email`. Se mockea `export_label` (evita OAuth/Gmail); su comportamiento propio ya está en `tests/test_email_export*`.

- [ ] **Step 1: Tests de email**

Añadir a `tests/test_abrir_caso_cli.py`:

```python
def test_cli_email_delega_en_export_label(drive_temporal, monkeypatch):
    llamadas = {}

    def spy(account, label, dest_dir, *, case_id=None, **kw):
        llamadas.update(account=account, label=label, dest=str(dest_dir), case_id=case_id)
        return type("R", (), {})()

    monkeypatch.setattr("core.email_export.export_label", spy)
    result = CliRunner().invoke(
        cli.app,
        _args_min(fuente="email", cuenta="mails@x.example", label="Caso W") + ["--crm", "skip"],
    )
    assert result.exit_code == 0, result.output
    case_id = "BaRS11 - Passeig Marítim 30 (W-02Z2NR) - Vuelta"
    assert llamadas["account"] == "mails@x.example"
    assert llamadas["label"] == "Caso W"
    assert llamadas["case_id"] == case_id
    assert llamadas["dest"].replace("\\", "/").endswith("00_Input/03_Email")
    # el orquestador NO emite un segundo evento (lo hace export_label, aquí mockeado)
    eventos = intake_log.read_events(case_id)
    assert [e for e in eventos if e["event"] == "upload_email"] == []


def test_cli_email_dry_run_no_llama(drive_temporal, monkeypatch):
    llamado = {"v": False}
    monkeypatch.setattr("core.email_export.export_label",
                        lambda *a, **k: llamado.__setitem__("v", True))
    result = CliRunner().invoke(
        cli.app, _args_min(fuente="email", cuenta="a@x.example", label="L") + ["--dry-run"])
    assert result.exit_code == 0, result.output
    assert llamado["v"] is False
```

- [ ] **Step 2: Run → fail**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k email -v`
Expected: FAIL (rama email aún `raise Exit(1)`).

- [ ] **Step 3: Implementar la rama email**

Añadir `email_export` al import `from core import ...`. Añadir helper (tras `_intake_whatsapp`):

```python
def _intake_email(ident, case_dir: Path, cuenta: str, label: str, *, dry_run: bool) -> None:
    dest = case_dir / "00_Input" / brain.FUENTE_A_SUBDIR["email"]
    if dry_run:
        typer.echo(f"[dry-run] email: se exportaría la etiqueta {label!r} de {cuenta} "
                   f"a {dest} (sin ejecutar)")
        return
    dest.mkdir(parents=True, exist_ok=True)
    email_export.export_label(cuenta, label, dest, case_id=ident.case_id)
    typer.echo(f"Email: etiqueta {label!r} exportada a {dest}")
```

Enrutar en `_despachar_intake`:

```python
    elif fuente == "email":
        _intake_email(ident, case_dir, cuenta, label, dry_run=dry_run)
```

- [ ] **Step 4: Run → pass**

Run: `... -m pytest tests/test_abrir_caso_cli.py -k email -v`
Expected: PASS. Fichero completo verde: `... -m pytest tests/test_abrir_caso_cli.py -v`.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(abrir-caso): fuente email (delegación a export_label, sin doble log)"
```

---

### Task 6: Parte C — documentar `init_caso` ↔ `abrir_caso`

**Files:** Modify `scripts/init_caso.py`, `scripts/abrir_caso.py`.

- [ ] **Step 1: Nota de relación en `scripts/init_caso.py`**

Añadir al final del docstring de módulo (antes del cierre `"""`):

```
Relación con `abrir_caso`: `init_caso` es el atajo LIGERO — solo monta el
esqueleto (validate_case_id + ensure_case), sin intake ni alta CRM.
`scripts/abrir_caso.py` es el flujo COMPLETO (esqueleto + intake por fuente +
CRM) en una pasada. Usa `init_caso` cuando solo quieras la carpeta; `abrir_caso`
cuando quieras abrir el caso de verdad.
```

- [ ] **Step 2: Nota simétrica en `scripts/abrir_caso.py`**

Añadir al docstring de módulo una línea:

```
Para montar solo el esqueleto (sin intake ni CRM), usa `scripts/init_caso.py`.
```

- [ ] **Step 3: Sanity de import (sin test nuevo; docs)**

Run: `... -m pytest tests/test_abrir_caso_cli.py -q`
Expected: PASS (cambios docstring no rompen nada).

- [ ] **Step 4: Commit**

```bash
git add scripts/init_caso.py scripts/abrir_caso.py
git commit -m "docs(abrir-caso): relación init_caso (ligero) vs abrir_caso (completo)"
```

---

### Task 7: Suite completa, PLAN.md y PR

**Files:** Modify `PLAN.md`.

- [ ] **Step 1: Suite completa**

Run: `"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q --tb=short`
Expected: verde salvo los 5 fallos ambientales pre-existentes de `test_sudespacho_relations` (faltan `SUDESPACHO_BASE_URL`/`SUDESPACHO_API_KEY`), idénticos a `main`. Cualquier otro fallo = regresión a corregir.

- [ ] **Step 2: Actualizar `PLAN.md`**

En la sección `## [abrir-caso]`: marcar F2a como mergeada (`a66bc3b`, #16); marcar la parte de fuentes de F3 con el estado real; anotar la decisión de conservar `init_caso.py` (sin disparador de deprecación); dejar la parte judicial (B) como `F3-judicial` pendiente. Reconciliar el desfase detectado (F2a y sala-maquina ya en main).

- [ ] **Step 3: Commit del PLAN**

```bash
git add PLAN.md
git commit -m "docs(plan): abrir-caso F3 fuentes + reconciliar F2a mergeada + decisión init_caso"
```

- [ ] **Step 4: Push + PR**

```bash
git push -u origin feat/abrir-caso-f3-fuentes
gh pr create --fill --base main
```

Verificar que el check `leak-scan` pasa. NO mergear sin visto bueno de Nikolai.

---

## Self-Review

- **Cobertura del spec:**
  - §1/§3.1 fuentes manual/whatsapp/email → Tasks 3/4/5 ✓; drive_ev intacto → Task 1 ✓.
  - §2 D1 delegar → whatsapp/email delegan (Tasks 4/5) ✓; D2 email=label export → Task 5 ✓; D3 quién loguea → manual/drive_ev orquestador (`_intake_generico`), whatsapp/email nativo (Tasks 3-5, tests de "no doble log") ✓; D4 una fuente/invocación → dispatch por `--fuente` ✓; D6 init_caso conservar+documentar → Task 6 ✓.
  - §0/§6 hueco de custodia manual → evento `upload_manual` con sha256 (Task 3) ✓.
  - §4 contrato CLI + validación de flags → Tasks 1/2 ✓.
  - §5 errores/idempotencia: manual src inexistente/dry-run/reentrante (Task 3), whatsapp dedup/dry-run (Task 4), email dry-run (Task 5) ✓.
  - §8 tests: todos los casos enumerados tienen su test ✓.
- **Placeholders:** ninguno; todo el código está escrito.
- **Consistencia de tipos/nombres:** `_intake_generico(case_dir, case_id, fuente, hashes, *, dry_run)` — misma firma en Task 1 (definición) y Tasks 3 (uso manual). `_despachar_intake(...)` con los mismos kwargs en Tasks 1/2/3/4/5. `brain.FUENTE_A_SUBDIR`/`FUENTE_A_EVENTO` ya existen en `core/abrir_caso.py`. `hash_tree_local`/`file_sha256` ya importados en F1.
- **Riesgo de reconcile con 04_Manual pre-existente:** resuelto — `_intake_generico` recibe `hashes` de SOLO lo recién depositado (Task 3 construye `hashes` de `rels`), no del árbol completo.
- **No-regresión:** Task 1 mantiene el comportamiento drive_ev de F1 (misma secuencia pull→hash→plan→reconcile→log); los tests F1 son la red.
