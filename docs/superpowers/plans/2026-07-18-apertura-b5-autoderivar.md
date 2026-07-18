# B5 — Auto-derivar identidad desde `--folder-id` (apertura de expediente) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** En `abrir_caso --fuente drive_ev`, cuando se omitan, auto-derivar `--team-id` (driveId), `--codigo-caso` (nombre de la unidad compartida) y `--sufijo` (del `tipo_caso` canónico) desde `--folder-id`; los flags explícitos siempre ganan.

**Architecture:** Patrón biblioteca (spec §4). Lógica **pura** en `core/config.py` (`sufijo_de_tipo_caso`, `codigo_de_unidad`); **I/O Drive** en `core/intake_drive.py` (`get_shared_drive_name`, `drives.get`); orquestación fina en `scripts/abrir_caso.py` (rellena flags omitidos antes del chequeo de identidad). Es la única unidad pendiente del bloque B1–B5 (spec §8).

**Tech Stack:** Python 3.14, Typer (CLI), httpx (Drive REST), pytest. Windows/PowerShell.

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-07-18-apertura-expediente-b1-b5-design.md §8`. No reabrir sus decisiones.
- **Flags explícitos SIEMPRE ganan** sobre lo auto-derivado (solo se rellena lo que viene `None`).
- **Degradación limpia:** lo que no se pueda derivar queda `None` y lo caza el chequeo de flags de identidad con un error claro (nunca un traceback ni un código equivocado).
- **`codigo_de_unidad` es LOSSY** y devuelve `None` ante duda: **un `None` (pide flag explícito) es preferible a un código equivocado** (obligaría a renombrar carpeta Drive + `_caso.md` + etiqueta Gmail + referencia CRM cross-sistema — memoria `feedback-case-sufijo-tipo-canonico`).
- **Sufijo = `tipo_caso` canónico**, nunca paráfrasis libre (misma memoria).
- **TDD** en todo `core/`. Suite verde (baseline ~2037; los 5 fallos de `test_sudespacho_relations::test_list_colaboradores_rest_*` son ambientales — worktree sin `.env` — e idénticos a `main`). Conteo por `--junit-xml` (la línea de resumen no se captura por tubería en este Windows).
- **UTF-8 sin BOM.** PII por `W-XXXXXX` en docs/commits.
- **`main` protegida:** rama + PR, `leak-scan` verde. Nunca push directo ni `--no-verify`.
- **Comandos shell:** desde la raíz del worktree; usar el intérprete del repo (`python -m pytest`).

## Nombres reales de unidades compartidas (base de `codigo_de_unidad`)

Volcados con `google-despacho::list_shared_drives` (cuenta EV, 2026-07-18). Formato operativo derivable: `"<Ciudad> - <S|R|PD><N>"`.

| Nombre de unidad (real) | Código derivado |
|---|---|
| `Barcelona - S3 ` (con espacio final) | `BaRS3` |
| `Barcelona - S1`..`S12` | `BaRS1`..`BaRS12` |
| `Barcelona - PD1` | `BaPD1` |
| `Barcelona Rentals - R1`..`R10` | `BaRR1`..`BaRR10` |
| `Bilbao - S1`,`S2` | `BiRS1`,`BiRS2` |
| `Madrid - S1`..`S15` | `MaRS1`..`MaRS15` |
| `Madrid - R1`..`R4` | `MaRR1`..`MaRR4` |
| `Madrid - PD1`,`PD2` | `MaPD1`,`MaPD2` |
| `San Sebastian - S1` / `- R1` | `SSRS1` / `SSRR1` |
| `Santander - S1` / `- R1` | `SaRS1` / `SaRR1` |
| `Valencia - S1`..`S5` | `VaRS1`..`VaRS5` |
| `Valencia - R1`,`R3`,`R5` | `VaRR1`,`VaRR3`,`VaRR5` |
| `Valencia - PD1` | `VaPD1` |

Regla: **ciudad2** (primera parte antes de ` - `) + **op2** (letra inicial del sufijo: `S`→`RS`, `R`→`RR`, `PD`→`PD`) + **número**.

**Devuelven `None` a propósito** (no derivables → pedir `--codigo-caso`): `Sevilla - S1 / S6` (ambigua), `BCN - PD10` / `BCN Comm - Agencia` (abreviatura BCN fuera del mapa; comercial no numerada), `Valencia - Commercial ` (comercial), `Madrid - R1 Inactivas` / `Madrid - R1_1` (sufijo no operativo), `Lisboa - S1` (Portugal, fuera del mapa), `BACKUP MADRID` / `NIKOLAI` / `_Team_Example_S0` (sin ` - ` o sin ciudad).

---

### Task 1: `sufijo_de_tipo_caso` (puro, `core/config.py`)

**Files:**
- Modify: `core/config.py` (añadir tras `TAGS_CRM_VALIDOS`, ~línea 153)
- Test: `tests/test_config_apertura_b5.py` (crear)

**Interfaces:**
- Produces: `config.sufijo_de_tipo_caso(tipo: str) -> str` — descriptor del case_id (carpeta Drive + ref CRM + etiqueta Gmail) derivado del `tipo_caso` canónico. Mapa de casos especiales (acrónimos) + fallback title-case.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_config_apertura_b5.py`:

```python
"""B5 — auto-derivación de identidad desde --folder-id (funciones puras)."""
from core import config


class TestSufijoDeTipoCaso:
    def test_vuelta(self):
        assert config.sufijo_de_tipo_caso("VUELTA") == "Vuelta"

    def test_negativa_escritura(self):
        assert config.sufijo_de_tipo_caso("NEGATIVA_ESCRITURA") == "Negativa escritura"

    def test_lau_20_preserva_acronimo(self):
        # El fallback title-case degradaría a "Lau 20"; el mapa especial lo evita.
        assert config.sufijo_de_tipo_caso("LAU_20") == "LAU 20"

    def test_bad_debt_fallback(self):
        assert config.sufijo_de_tipo_caso("BAD_DEBT") == "Bad debt"

    def test_todos_los_tipos_dan_sufijo_valido(self):
        for tipo in config.TIPOS_CASO_ALL:
            suf = config.sufijo_de_tipo_caso(tipo)
            assert suf and "_" not in suf and suf[0].isupper()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config_apertura_b5.py::TestSufijoDeTipoCaso -q`
Expected: FAIL — `AttributeError: module 'core.config' has no attribute 'sufijo_de_tipo_caso'`.

- [ ] **Step 3: Write minimal implementation**

En `core/config.py`, tras el bloque `TAGS_CRM_VALIDOS` (~línea 153):

```python
# ---------------------------------------------------------------------------
# Sufijo del case_id derivado del tipo_caso canónico (B5)
# ---------------------------------------------------------------------------
#
# El descriptor del case_id (carpeta Drive + referencia CRM + etiqueta Gmail)
# se deriva SIEMPRE del tipo_caso, nunca de una paráfrasis libre — si no, hay
# que renombrar cross-sistema (memoria feedback-case-sufijo-tipo-canonico).
# Solo LAU_20 necesita entrada explícita: el fallback title-case degradaría el
# acrónimo ("Lau 20"). El resto sale del fallback (VUELTA -> "Vuelta", etc.).
_SUFIJO_TIPO_CASO_ESPECIAL: dict[str, str] = {
    "LAU_20": "LAU 20",
}


def sufijo_de_tipo_caso(tipo: str) -> str:
    """Descriptor humano del case_id derivado del tipo_caso canónico.

    Ejemplos: ``VUELTA -> "Vuelta"``, ``NEGATIVA_ESCRITURA -> "Negativa
    escritura"``, ``LAU_20 -> "LAU 20"``. Casos especiales (acrónimos) por mapa;
    el resto por fallback title-case ``tipo.replace("_", " ").capitalize()``.
    """
    if tipo in _SUFIJO_TIPO_CASO_ESPECIAL:
        return _SUFIJO_TIPO_CASO_ESPECIAL[tipo]
    return tipo.replace("_", " ").capitalize()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config_apertura_b5.py::TestSufijoDeTipoCaso -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add core/config.py tests/test_config_apertura_b5.py
git commit -m "feat(apertura B5): sufijo_de_tipo_caso puro (config)"
```

---

### Task 2: `codigo_de_unidad` (puro, `core/config.py`)

**Files:**
- Modify: `core/config.py` (añadir `import re` al bloque de imports; función tras `sufijo_de_tipo_caso`)
- Test: `tests/test_config_apertura_b5.py` (ampliar)

**Interfaces:**
- Produces: `config.codigo_de_unidad(nombre_unidad: str) -> str | None` — deriva el código de caso (`"BaRS3"`) del nombre de una unidad compartida; `None` si no se puede derivar con certeza.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_config_apertura_b5.py`:

```python
import pytest


class TestCodigoDeUnidad:
    @pytest.mark.parametrize("nombre,esperado", [
        ("Barcelona - S3 ", "BaRS3"),          # espacio final real
        ("Barcelona - S3", "BaRS3"),
        ("Barcelona - S1", "BaRS1"),
        ("Barcelona - S12", "BaRS12"),
        ("Barcelona - PD1", "BaPD1"),
        ("Barcelona Rentals - R1", "BaRR1"),
        ("Barcelona Rentals - R10", "BaRR10"),
        ("Bilbao - S2", "BiRS2"),
        ("Madrid - S15", "MaRS15"),
        ("Madrid - R1", "MaRR1"),
        ("Madrid - PD2", "MaPD2"),
        ("San Sebastian - S1", "SSRS1"),
        ("San Sebastian - R1", "SSRR1"),
        ("Santander - S1", "SaRS1"),
        ("Valencia - S5", "VaRS5"),
        ("Valencia - R3", "VaRR3"),
        ("Valencia - PD1", "VaPD1"),
    ])
    def test_derivables(self, nombre, esperado):
        assert config.codigo_de_unidad(nombre) == esperado

    @pytest.mark.parametrize("nombre", [
        "Sevilla - S1 / S6",        # ambigua
        "BCN - PD10",               # abreviatura fuera del mapa
        "BCN Comm - Agencia",       # comercial no numerada
        "Valencia - Commercial ",   # comercial (sufijo no operativo)
        "Madrid - R1 Inactivas",    # sufijo no operativo
        "Madrid - R1_1",            # sufijo no operativo
        "Lisboa - S1",              # Portugal, fuera del mapa
        "BACKUP MADRID",            # sin " - "
        "NIKOLAI",                  # sin " - " ni ciudad
        "_Team_Example_S0",         # sin " - "
        "MMC Barcelona Juridico",   # sin " - "
        "Barcelona - ",             # sufijo vacío
        "Barcelona -",              # sin " - " (falta espacio)
        "- S3",                     # sin ciudad
        "",                         # vacío
    ])
    def test_no_derivables_devuelven_none(self, nombre):
        assert config.codigo_de_unidad(nombre) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config_apertura_b5.py::TestCodigoDeUnidad -q`
Expected: FAIL — `AttributeError: module 'core.config' has no attribute 'codigo_de_unidad'`.

- [ ] **Step 3: Write minimal implementation**

En `core/config.py`: añadir `import re` en el bloque de imports (tras `import os`, línea ~9). Luego, tras `sufijo_de_tipo_caso`:

```python
# ---------------------------------------------------------------------------
# Código de caso derivado del nombre de la unidad compartida del Drive (B5)
# ---------------------------------------------------------------------------
#
# Regla LOSSY fijada contra los NOMBRES REALES de las unidades compartidas del
# Drive E&V (cuenta EV, drives.list 2026-07-18). Formato operativo:
# "<Ciudad> - <S|R|PD><N>" -> "<Ciudad2><Op2><N>" (p.ej. "Barcelona - S3" ->
# "BaRS3", "Barcelona Rentals - R1" -> "BaRR1", "Valencia - PD1" -> "VaPD1").
# Lisboa (Portugal) y las unidades comerciales/administrativas quedan fuera a
# propósito. Un None (pedir --codigo-caso explícito) es preferible a un código
# equivocado, que obligaría a renombrar cross-sistema.
_CIUDAD_DE_UNIDAD: dict[str, str] = {
    "Barcelona": "Ba",
    "Bilbao": "Bi",
    "Madrid": "Ma",
    "Santander": "Sa",
    "San Sebastian": "SS",
    "San Sebastián": "SS",
    "Sevilla": "Se",
    "Valencia": "Va",
}

# Tipo de operación del código, leído de la letra inicial del sufijo de la
# unidad: "S<N>" (venta residencial) -> "RS", "R<N>" (alquiler) -> "RR",
# "PD<N>" (patrimonio) -> "PD".
_OP_DE_SUFIJO_UNIDAD: dict[str, str] = {"S": "RS", "R": "RR", "PD": "PD"}
_SUFIJO_UNIDAD_RE = re.compile(r"^(PD|S|R)(\d+)$")


def codigo_de_unidad(nombre_unidad: str) -> str | None:
    """Deriva el código de caso ("BaRS3") del nombre de una unidad compartida.

    Devuelve ``None`` cuando no puede derivar con certeza (ciudad desconocida,
    sufijo no operativo, unidad comercial o ambigua): pedir ``--codigo-caso``
    explícito. Regla fijada contra los nombres reales (drives.list, cuenta EV).
    """
    if not nombre_unidad or " - " not in nombre_unidad:
        return None
    zona, sufijo = nombre_unidad.split(" - ", 1)
    zona = zona.strip()

    ciudad = None
    for nombre_ciudad, cod in _CIUDAD_DE_UNIDAD.items():
        if zona == nombre_ciudad or zona.startswith(nombre_ciudad + " "):
            ciudad = cod
            break
    if ciudad is None:
        return None

    m = _SUFIJO_UNIDAD_RE.match(sufijo.strip().upper())
    if not m:
        return None
    return f"{ciudad}{_OP_DE_SUFIJO_UNIDAD[m.group(1)]}{m.group(2)}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config_apertura_b5.py -q`
Expected: PASS (todos, incl. TestSufijoDeTipoCaso).

- [ ] **Step 5: Commit**

```bash
git add core/config.py tests/test_config_apertura_b5.py
git commit -m "feat(apertura B5): codigo_de_unidad puro contra nombres reales (config)"
```

---

### Task 3: `get_shared_drive_name` (I/O Drive, `core/intake_drive.py`)

**Files:**
- Modify: `core/intake_drive.py` (añadir tras `get_drive_folder_info`, ~línea 641)
- Test: `tests/test_intake_drive.py` (ampliar; reutiliza `_mock_rclone_token`, `MagicMock`, `patch`)

**Interfaces:**
- Consumes: `_get_drive_access_token()`, `_is_rate_limit_response()`, `_RATE_LIMIT_BACKOFF_SECONDS` (ya en el módulo).
- Produces: `intake_drive.get_shared_drive_name(drive_id: str) -> str | None` — nombre de la unidad compartida vía `drives.get`; `None` ante cualquier fallo.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_intake_drive.py` (junto a `TestGetDriveFolderInfo`; el import de `get_shared_drive_name` va en la clase para no romper el import de módulo si aún no existe — o añadir al import existente en Step 3):

```python
class TestGetSharedDriveName:
    def test_ok_devuelve_nombre(self, monkeypatch):
        from core.intake_drive import get_shared_drive_name
        _mock_rclone_token(monkeypatch)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "Barcelona - S3 "}
        with patch("httpx.get", return_value=mock_resp):
            assert get_shared_drive_name("0AAPGi435EiuRUk9PVA") == "Barcelona - S3 "

    def test_sin_token_devuelve_none(self, monkeypatch):
        from core.intake_drive import get_shared_drive_name
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "[gdrive_ev]\nscope = drive\n"  # sin línea token
        mock.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
        with patch("httpx.get") as mock_get:
            assert get_shared_drive_name("DID") is None
        mock_get.assert_not_called()

    def test_drive_id_vacio_devuelve_none(self, monkeypatch):
        from core.intake_drive import get_shared_drive_name
        with patch("httpx.get") as mock_get:
            assert get_shared_drive_name("") is None
        mock_get.assert_not_called()

    def test_api_404_devuelve_none(self, monkeypatch):
        from core.intake_drive import get_shared_drive_name
        _mock_rclone_token(monkeypatch)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.get", return_value=mock_resp):
            assert get_shared_drive_name("DID") is None

    def test_nombre_vacio_devuelve_none(self, monkeypatch):
        from core.intake_drive import get_shared_drive_name
        _mock_rclone_token(monkeypatch)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": ""}
        with patch("httpx.get", return_value=mock_resp):
            assert get_shared_drive_name("DID") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_intake_drive.py::TestGetSharedDriveName -q`
Expected: FAIL — `ImportError: cannot import name 'get_shared_drive_name'`.

- [ ] **Step 3: Write minimal implementation**

En `core/intake_drive.py`, tras `get_drive_folder_info` (antes de `get_drive_folder_info_cached`, ~línea 642):

```python
def get_shared_drive_name(drive_id: str) -> str | None:
    """Nombre de una unidad compartida (Shared Drive) del Drive E&V.

    Usa la Drive API v3 ``drives.get`` con el access_token de ``gdrive_ev``
    (rclone). Mismo patrón de degradación limpia y retry de rate-limit que
    :func:`get_drive_folder_info`: devuelve ``None`` ante drive_id vacío, token
    ausente, ``httpx`` no disponible, red caída o respuesta no-200 no
    recuperable (401/403/404/5xx). B5: alimenta ``config.codigo_de_unidad``
    para auto-derivar ``--codigo-caso`` en ``abrir_caso --fuente drive_ev``.
    """
    if not drive_id:
        return None
    access_token = _get_drive_access_token()
    if not access_token:
        return None
    try:
        import httpx
    except ImportError:
        return None

    for delay in (0.0,) + _RATE_LIMIT_BACKOFF_SECONDS:
        if delay > 0:
            time.sleep(delay)
        try:
            r = httpx.get(
                f"https://www.googleapis.com/drive/v3/drives/{drive_id}",
                params={"fields": "name"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
        except Exception:
            return None
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                return None
            name = data.get("name", "")
            return name or None
        if not _is_rate_limit_response(r):
            return None
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_intake_drive.py::TestGetSharedDriveName -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add core/intake_drive.py tests/test_intake_drive.py
git commit -m "feat(apertura B5): get_shared_drive_name (drives.get) en intake_drive"
```

---

### Task 4: Auto-derivación en la CLI `abrir_caso` (drive_ev)

**Files:**
- Modify: `scripts/abrir_caso.py` (nuevo helper `_autoderivar_drive_ev`; enganche en la rama de los 6 flags, ~línea 364-368)
- Test: `tests/test_abrir_caso_cli.py` (ampliar)

**Interfaces:**
- Consumes: `config.sufijo_de_tipo_caso`, `config.codigo_de_unidad` (Task 1/2), `intake_drive.get_drive_folder_info`, `intake_drive.get_shared_drive_name` (Task 3), `intake_drive.DriveFolderInfo`.
- Produces: helper `_autoderivar_drive_ev(*, folder_id, tipo_caso, team_id, codigo_caso, sufijo) -> tuple[str | None, str | None, str | None]` (devuelve `team_id, codigo_caso, sufijo` con los omitidos rellenados donde se pudo).

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_abrir_caso_cli.py`. Nota: `_args` incluye `--codigo-caso/--sufijo/--team-id`; para B5 se construyen args SIN ellos. Añadir helper local y mocks de las 2 funciones IO:

```python
from core import config as _config  # ya arriba? si no, añadir


def _args_b5_autoderivar(**over):
    """Args de drive_ev SIN los 3 flags auto-derivables (codigo/sufijo/team)."""
    base = [
        "--w-code", "W-02Z2NR", "--ciudad", "Barcelona", "--tipo-caso", "VUELTA",
        "--direccion", "Passeig Marítim 30", "--folder-id", "FID", "--yes",
    ]
    for k, v in over.items():
        base += [f"--{k}", v]
    return base


def _mock_drive_info(monkeypatch, *, drive_id="DRIVEID", unidad="Barcelona - S3 "):
    from core.intake_drive import DriveFolderInfo
    monkeypatch.setattr(
        "core.intake_drive.get_drive_folder_info",
        lambda fid: DriveFolderInfo(name="carpeta", drive_id=drive_id),
    )
    monkeypatch.setattr(
        "core.intake_drive.get_shared_drive_name",
        lambda did: unidad,
    )


def test_cli_drive_ev_autoderiva_codigo_team_sufijo(drive_temporal, monkeypatch):
    _mock_drive_info(monkeypatch, drive_id="DRIVEID", unidad="Barcelona - S3 ")
    captura = {}
    def fake_pull(case_id, folder_id, team_id, *, force=False):
        captura["case_id"] = case_id
        captura["team_id"] = team_id
        dest = case_locator.path_for(case_id) / "00_Input" / "01_Drive EV"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "a.pdf").write_bytes(b"x")
        (dest / ".pulled").write_text("{}", encoding="utf-8")
        return type("R", (), {"count": 1})()
    monkeypatch.setattr("core.intake_drive.pull_drive_ev", fake_pull)

    result = CliRunner().invoke(cli.app, _args_b5_autoderivar(crm="skip"))

    assert result.exit_code == 0, result.output
    # código BaRS3 (de "Barcelona - S3") + sufijo "Vuelta" (de VUELTA)
    assert "BaRS3 - Passeig Marítim 30 (W-02Z2NR) - Vuelta" in captura["case_id"]
    assert captura["team_id"] == "DRIVEID"  # team_id = driveId


def test_cli_drive_ev_flags_explicitos_ganan(drive_temporal, monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("no debe llamar a la Drive API con todo explícito")
    monkeypatch.setattr("core.intake_drive.get_drive_folder_info", boom)
    monkeypatch.setattr("core.intake_drive.get_shared_drive_name", boom)
    # _args() trae los 3 flags explícitos (BaRS11 / Vuelta / TID)
    result = CliRunner().invoke(cli.app, _args(crm="skip"))
    assert result.exit_code == 0, result.output
    caso = next(case_locator.path_for(p.name) for p in case_locator.list_cases("Barcelona"))
    assert "BaRS11" in caso.name  # ganó el flag, no un derivado


def test_cli_drive_ev_codigo_no_derivable_error(drive_temporal, monkeypatch):
    # unidad ambigua -> codigo_de_unidad None -> falta --codigo-caso -> exit 1
    _mock_drive_info(monkeypatch, unidad="Sevilla - S1 / S6")
    result = CliRunner().invoke(cli.app, _args_b5_autoderivar(crm="skip"))
    assert result.exit_code == 1
    assert "--codigo-caso" in result.output


def test_cli_drive_ev_folder_info_none_degrada_limpio(drive_temporal, monkeypatch):
    monkeypatch.setattr("core.intake_drive.get_drive_folder_info", lambda fid: None)
    result = CliRunner().invoke(cli.app, _args_b5_autoderivar(crm="skip"))
    assert result.exit_code == 1
    assert "--codigo-caso" in result.output  # error de flags, no traceback


def test_cli_drive_ev_sufijo_autoderivado_sin_api(drive_temporal, monkeypatch):
    # codigo y team explícitos -> no se toca la Drive API; solo se deriva sufijo
    def boom(*a, **kw):
        raise AssertionError("no debe llamar a la Drive API")
    monkeypatch.setattr("core.intake_drive.get_drive_folder_info", boom)
    monkeypatch.setattr("core.intake_drive.get_shared_drive_name", boom)
    result = CliRunner().invoke(
        cli.app,
        _args_b5_autoderivar(**{"codigo-caso": "BaRS11", "team-id": "TID", "crm": "skip"}),
    )
    assert result.exit_code == 0, result.output
    caso = next(case_locator.path_for(p.name) for p in case_locator.list_cases("Barcelona"))
    assert caso.name.endswith("- Vuelta")  # sufijo derivado de VUELTA
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_abrir_caso_cli.py -q -k b5 -k "autoderiva or explicitos or no_derivable or folder_info or sufijo_autoderivado"`
(o simplemente `python -m pytest tests/test_abrir_caso_cli.py -q`)
Expected: FAIL — los nuevos tests fallan (auto-derivación no existe: con args sin `--codigo-caso`, hoy sale "faltan flags de identidad").

- [ ] **Step 3: Write minimal implementation**

En `scripts/abrir_caso.py`, añadir el helper (tras `_alta_crm`, antes de `@app.command()`, ~línea 293):

```python
def _autoderivar_drive_ev(
    *, folder_id, tipo_caso, team_id, codigo_caso, sufijo,
):
    """B5: en --fuente drive_ev, deriva team_id/codigo_caso/sufijo omitidos.

    - sufijo: puro, del tipo_caso (no necesita la Drive API).
    - team_id: driveId de la carpeta (--folder-id).
    - codigo_caso: nombre de la unidad compartida -> config.codigo_de_unidad.

    Los flags explícitos SIEMPRE ganan (solo se rellena lo que viene None).
    Degrada limpio: lo que no se pueda derivar queda None y lo caza el chequeo
    de flags de identidad con un error claro.
    """
    if sufijo is None and tipo_caso:
        sufijo = config.sufijo_de_tipo_caso(tipo_caso)
        typer.echo(f"[auto] --sufijo del tipo_caso: {sufijo!r}")

    if folder_id and (team_id is None or codigo_caso is None):
        info = intake_drive.get_drive_folder_info(folder_id)
        if info is None:
            typer.echo("[auto] No se pudo leer la carpeta de Drive (token/red); "
                       "pasa los flags que falten explícitos.")
            return team_id, codigo_caso, sufijo
        if team_id is None and info.drive_id:
            team_id = info.drive_id
            typer.echo(f"[auto] --team-id del driveId: {team_id}")
        if codigo_caso is None:
            drive_id_eff = team_id or info.drive_id
            unidad = intake_drive.get_shared_drive_name(drive_id_eff) if drive_id_eff else None
            derivado = config.codigo_de_unidad(unidad) if unidad else None
            if derivado:
                codigo_caso = derivado
                typer.echo(f"[auto] --codigo-caso de la unidad {unidad!r}: {codigo_caso}")
            else:
                typer.echo(f"[auto] No pude derivar --codigo-caso de la unidad {unidad!r}; "
                           "pásalo explícito.")
    return team_id, codigo_caso, sufijo
```

Luego, en la rama `else` de identidad (los 6 flags), justo al entrar y **antes** del cálculo de `faltan` (línea ~364-368), sustituir:

```python
    else:
        faltan = [n for n, v in flags_ident if v is None]
        if faltan:
            typer.echo(f"[ERROR] faltan flags de identidad {faltan} (o usa --case-id)", err=True)
            raise typer.Exit(code=1)
```

por:

```python
    else:
        if fuente == "drive_ev":
            team_id, codigo_caso, sufijo = _autoderivar_drive_ev(
                folder_id=folder_id, tipo_caso=tipo_caso,
                team_id=team_id, codigo_caso=codigo_caso, sufijo=sufijo,
            )
        flags_ident_eff = [
            ("--w-code", w_code), ("--ciudad", ciudad), ("--tipo-caso", tipo_caso),
            ("--codigo-caso", codigo_caso), ("--sufijo", sufijo), ("--direccion", direccion),
        ]
        faltan = [n for n, v in flags_ident_eff if v is None]
        if faltan:
            typer.echo(f"[ERROR] faltan flags de identidad {faltan} (o usa --case-id)", err=True)
            raise typer.Exit(code=1)
```

(El resto de la rama `else` —`if ciudad not in CIUDADES`, `nombres`, `resolver_identidad`, confirmación de colisión— queda intacto y ya usa las variables `codigo_caso`/`sufijo` locales, ahora rellenadas.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_abrir_caso_cli.py -q`
Expected: PASS (los nuevos + los existentes; `_args()` con flags explícitos sigue verde).

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_abrir_caso_cli.py
git commit -m "feat(apertura B5): auto-derivar team/codigo/sufijo desde --folder-id en la CLI"
```

---

### Task 5: Documentación (RUNBOOK) + verificación de suite completa

**Files:**
- Modify: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (§2 `[APER-03]`, §4 comando/nota, §5 nota final)

**Interfaces:** ninguna (docs). Cierra el bloque §10 de la spec para B5.

- [ ] **Step 1: Actualizar RUNBOOK §4 — comando y nota de auto-derivación**

En `docs/RUNBOOK_APERTURA_EXPEDIENTE.md §4`, reemplazar el bloque de comando (líneas ~106-110) por la versión que omite los flags auto-derivables y añadir una viñeta:

```markdown
```powershell
python -m scripts.abrir_caso --w-code W-XXXXXX --ciudad Barcelona --tipo-caso VUELTA `
  --direccion "..." --folder-id <id> `
  --fuente drive_ev --crm api --cuantia <n> --yes --force
```

- **`[APER-21]` Auto-derivación (B5, `main`):** en `--fuente drive_ev`, si se omiten,
  `--team-id` (driveId), `--codigo-caso` (nombre de la unidad compartida vía Drive API) y
  `--sufijo` (del `tipo_caso` canónico) se **auto-derivan** desde `--folder-id`. Los flags
  explícitos SIEMPRE ganan. Si `codigo_de_unidad` no puede derivar (unidad comercial,
  ambigua como `"Sevilla - S1 / S6"`, o ciudad fuera del mapa), la CLI pide `--codigo-caso`
  explícito con un error claro (nunca un código equivocado).
```

(Mantener las viñetas `--yes` / `--force` / dry-run / `[APER-19]` existentes debajo.)

- [ ] **Step 2: Actualizar RUNBOOK §2 y §5 — quitar "B5 lo auto-derivará" (ya hecho)**

- §2 `[APER-03]` (línea ~72-73): confirmar que el texto "Del `driveId` de la carpeta. NO preguntar." sigue vigente; añadir al final: `La CLI lo auto-deriva (B5).`
- §5 (línea ~137-138): cambiar `(re-pull) aún hacen falta `--folder-id`/`--team-id` (B5 los auto-derivará).` por `(re-pull) basta `--folder-id`: `--team-id`/`--codigo-caso`/`--sufijo` se auto-derivan (B5).`

- [ ] **Step 3: Verificar la suite completa por JUnit XML**

Run:
```powershell
python -m pytest -q --junit-xml=.reports/b5.xml
```
Comprobar el XML: `testsuite` con `errors="0"` y `failures="0"` salvo los 5 ambientales conocidos (`test_sudespacho_relations::test_list_colaboradores_rest_*`). Cualquier otro fallo se investiga antes de cerrar.

- [ ] **Step 4: Commit**

```bash
git add docs/RUNBOOK_APERTURA_EXPEDIENTE.md
git commit -m "docs(apertura B5): RUNBOOK — auto-derivación desde --folder-id [APER-21]"
```

---

## Verificación final (fuera de tareas, antes del PR)

- Revisión adversarial de la rama completa (workflow / subagente).
- `pre-commit` + `leak-scan` verdes.
- **Verificación en vivo opcional (spec §9 R4):** `get_shared_drive_name` contra un `driveId` real (p.ej. `0AAPGi435EiuRUk9PVA` = "Barcelona - S3") si el token `gdrive_ev` está vivo — confirma que `drives.get` responde y que `codigo_de_unidad` sobre el nombre real da `BaRS3`. No bloquea (la lógica pura ya está cubierta por unit tests con nombres reales).
- PR desde la rama; marcar B5 `[x]` en `PLAN.md [SIGUIENTE-APERTURA-EXPEDIENTE]` con el hash al cerrar.

## Self-Review (writing-plans)

**Spec §8 coverage:**
- `--team-id` = driveId → Task 4 (usa `get_drive_folder_info.drive_id`, ya existente). ✓
- `--sufijo` = `sufijo_de_tipo_caso` (mapa + fallback, LAU_20 especial) → Task 1. ✓
- `--codigo-caso` = `codigo_de_unidad(nombre_unidad)` + IO nueva `get_shared_drive_name` (`drives.get`) → Tasks 2 + 3. ✓
- Flags explícitos ganan → Task 4 (solo rellena `None`) + test `flags_explicitos_ganan`. ✓
- Regla lossy fijada con nombres reales (no tabla hardcodeada; parser sobre el nombre de la API) → Task 2 + tabla de nombres reales. ✓
- Docs (spec §10: RUNBOOK §4 auto-derivación) → Task 5. ✓

**Placeholder scan:** sin TBD/TODO; todo el código de cada step es completo.

**Type consistency:** `sufijo_de_tipo_caso(str)->str`, `codigo_de_unidad(str)->str|None`, `get_shared_drive_name(str)->str|None`, `_autoderivar_drive_ev(...)->tuple` — nombres y firmas consistentes entre tareas y con el enganche de la CLI.
