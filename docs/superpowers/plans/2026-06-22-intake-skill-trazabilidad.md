# Skill de intake + trazabilidad (Plan 2/3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una skill del despacho que, tras depositar ficheros en `00_Input/<fuente>/` con el conector `expedientes-xl`, **dispare la trazabilidad forense** (evento `upload_*` en `_intake_log.jsonl`) de forma determinista, funcionando en Cowork y en Claude Code.

**Architecture:** Helper Python **puro** `traza.py` (sin IO, sin `import core`) que construye la línea JSONL del evento — espejando el esquema de `core/intake_log.py` — y comprueba duplicados sobre el contenido del log. Es puro → corre incluso en el sandbox de Cowork; el agente lo ejecuta para obtener la línea y la escribe en el Drive con el `append_text` del conector. Un **test de paridad** ancla el esquema a `core/` (gate anti-drift). El `IntakeManifest` pesado (`_intake_hashes.json`) NO se reimplementa: se reconcilia con `core/` en local (fuera de Fase A).

**Tech Stack:** Python 3 (venv del repo), `pytest`. La skill se ejecuta en claude.ai/Cowork (servidor) o Claude Code; consume el conector `expedientes-xl` (Plan 1).

---

## Estructura de ficheros

- Create: `.claude/skills/intake-expediente/scripts/traza.py` — helper PURO (build event + dedup). Sin `import core`.
- Create: `.claude/skills/intake-expediente/SKILL.md` — la skill de intake (orquestación).
- Create: `.claude/skills/intake-expediente/CHANGELOG.md`
- Test: `tests/test_intake_traza.py` — unit + **paridad con `core/intake_log.py`**.

`traza.py` es pura y autocontenida (no importa `core`) para poder correr en el sandbox de Cowork. La paridad con `core` se garantiza por test (no por import), con gate anti-drift.

---

## Task 1: `traza.build_upload_event` (línea JSONL determinista)

**Files:**
- Create: `.claude/skills/intake-expediente/scripts/traza.py`
- Test: `tests/test_intake_traza.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_intake_traza.py
import json
from pathlib import Path

import pytest

# import del helper puro de la skill por ruta (no es un paquete instalable)
import importlib.util

_TRAZA = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "intake-expediente" / "scripts" / "traza.py"
_spec = importlib.util.spec_from_file_location("intake_traza", _TRAZA)
traza = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(traza)


def test_build_upload_event_estructura():
    line = traza.build_upload_event(
        case_id="BaRS1",
        event="upload_whatsapp",
        files=[{"path": "02_Whatsapp/00_Consultor propietario/chat/_chat.txt", "sha256": "abc123"}],
        actor="nikolai",
        ts="2026-06-22T10:00:00",
    )
    entry = json.loads(line)
    assert entry["ts"] == "2026-06-22T10:00:00"
    assert entry["actor"] == "nikolai"
    assert entry["event"] == "upload_whatsapp"
    assert entry["case_id"] == "BaRS1"
    assert entry["details"]["count"] == 1
    assert entry["details"]["files"][0]["sha256"] == "abc123"
    assert line.endswith("\n")


def test_build_upload_event_rechaza_evento_invalido():
    with pytest.raises(ValueError):
        traza.build_upload_event(
            case_id="X", event="evento_inventado", files=[], actor="a", ts="t"
        )
```

- [ ] **Step 2: Ejecutar y verificar que FALLA**

Run: `python -m pytest tests/test_intake_traza.py -v`
Expected: FAIL (ModuleNotFoundError del fichero / AttributeError build_upload_event).

- [ ] **Step 3: Implementación mínima**

```python
# .claude/skills/intake-expediente/scripts/traza.py
"""Helper PURO de trazabilidad de intake (sin IO, sin import core).

Construye la línea JSONL de un evento `upload_*` espejando el esquema de
`core/intake_log.py::append_event` ({ts, actor, event, case_id, details}).
Puro → ejecutable en el sandbox de Cowork; el agente escribe la línea en el
Drive con el `append_text` del conector expedientes-xl. La paridad con core se
verifica en tests/test_intake_traza.py (gate anti-drift).
"""
from __future__ import annotations

import json
from typing import Any

# Subconjunto de core.intake_log.INTAKE_EVENTS relevante para depósito de ficheros.
# El test de paridad exige que sea subconjunto del set real de core.
UPLOAD_EVENTS: frozenset[str] = frozenset({
    "upload_manual",
    "upload_email",
    "upload_whatsapp",
    "upload_entrevista",
    "pull_drive_ev",
})


def build_upload_event(
    *,
    case_id: str,
    event: str,
    files: list[dict[str, Any]],
    actor: str,
    ts: str,
) -> str:
    """Devuelve la línea JSONL (con '\\n') de un evento de depósito.

    `files`: lista de {"path": <relativo a 00_Input, posix>, "sha256": <hex>}.
    `event`: debe estar en UPLOAD_EVENTS. `ts`: ISO-8601 (lo provee el caller).
    """
    if event not in UPLOAD_EVENTS:
        raise ValueError(f"Evento de depósito desconocido: {event!r}")
    entry = {
        "ts": ts,
        "actor": actor,
        "event": event,
        "case_id": case_id,
        "details": {"count": len(files), "files": files},
    }
    return json.dumps(entry, ensure_ascii=False) + "\n"
```

- [ ] **Step 4: Ejecutar y verificar que PASA**

Run: `python -m pytest tests/test_intake_traza.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/intake-expediente/scripts/traza.py tests/test_intake_traza.py
git commit -m "feat(intake-skill): traza.build_upload_event (línea JSONL determinista)"
```

---

## Task 2: `traza.is_duplicate` (dedup sobre el contenido del log)

**Files:**
- Modify (append): `.claude/skills/intake-expediente/scripts/traza.py`
- Test (append): `tests/test_intake_traza.py`

- [ ] **Step 1: Escribir el test que falla**

```python
def test_is_duplicate_detecta_hash_previo():
    log = "".join([
        traza.build_upload_event(case_id="C", event="upload_manual",
                                  files=[{"path": "04_Manual/a.pdf", "sha256": "HASH_A"}],
                                  actor="a", ts="t1"),
        traza.build_upload_event(case_id="C", event="upload_email",
                                  files=[{"path": "03_Email/b.eml", "sha256": "HASH_B"}],
                                  actor="a", ts="t2"),
    ])
    assert traza.is_duplicate(log, "HASH_A") is True
    assert traza.is_duplicate(log, "HASH_NUEVO") is False


def test_is_duplicate_log_vacio_o_corrupto():
    assert traza.is_duplicate("", "X") is False
    assert traza.is_duplicate("no es json\n{tampoco\n", "X") is False
```

- [ ] **Step 2: Ejecutar y verificar que FALLA**

Run: `python -m pytest tests/test_intake_traza.py -k is_duplicate -v`
Expected: FAIL (AttributeError is_duplicate).

- [ ] **Step 3: Implementación mínima** (APPEND a `traza.py`)

```python
def is_duplicate(log_text: str, sha256: str) -> bool:
    """True si `sha256` ya aparece en algún evento de depósito del log JSONL.

    Tolerante a líneas corruptas (las salta), como core.intake_log.read_events.
    """
    if not sha256:
        return False
    for raw in log_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        for f in entry.get("details", {}).get("files", []):
            if isinstance(f, dict) and f.get("sha256") == sha256:
                return True
    return False
```

- [ ] **Step 4: Ejecutar y verificar que PASA**

Run: `python -m pytest tests/test_intake_traza.py -k is_duplicate -v` (2) then `python -m pytest tests/test_intake_traza.py -v` (4 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/intake-expediente/scripts/traza.py tests/test_intake_traza.py
git commit -m "feat(intake-skill): traza.is_duplicate (dedup sobre el log)"
```

---

## Task 3: Test de PARIDAD con `core/` (gate anti-drift)

**Files:**
- Test (append): `tests/test_intake_traza.py`

- [ ] **Step 1: Escribir el test que falla**

```python
def test_paridad_eventos_subconjunto_de_core():
    from core import intake_log
    assert traza.UPLOAD_EVENTS <= intake_log.INTAKE_EVENTS, (
        "traza.UPLOAD_EVENTS tiene eventos que core.intake_log.INTAKE_EVENTS no reconoce"
    )


def test_paridad_shape_con_core(tmp_path, monkeypatch):
    """La línea de traza tiene las MISMAS claves que core.append_event escribe.

    `caso_path` delega en case_locator; para aislar el test de esa maquinaria,
    parcheamos `intake_log.log_path` para que escriba en tmp_path directamente.
    """
    import json as _json
    from core import intake_log

    logf = tmp_path / "_intake_log.jsonl"
    monkeypatch.setattr(intake_log, "log_path", lambda case_id: logf)

    intake_log.append_event(
        "CASO_PARIDAD", "upload_manual",
        details={"count": 1, "files": [{"path": "04_Manual/a.pdf", "sha256": "H"}]},
        actor="a", ts="t",
    )
    core_entry = _json.loads(logf.read_text(encoding="utf-8").splitlines()[0])

    traza_entry = _json.loads(traza.build_upload_event(
        case_id="CASO_PARIDAD", event="upload_manual",
        files=[{"path": "04_Manual/a.pdf", "sha256": "H"}], actor="a", ts="t",
    ))

    assert set(core_entry.keys()) == set(traza_entry.keys())
    assert set(core_entry["details"].keys()) == set(traza_entry["details"].keys())
    assert core_entry == traza_entry
```

- [ ] **Step 2: Ejecutar y verificar que FALLA o PASA**

Run: `python -m pytest tests/test_intake_traza.py -k paridad -v`
Expected: PASS if `traza.py` matches core's schema. If it FAILS on the assertion, the failure pinpoints a REAL schema divergence in `traza.py` → fix `traza.py` to match `core.intake_log.append_event`'s output exactly. (The harness is already isolated via the `log_path` monkeypatch, so a failure means a genuine mismatch, not test wiring.)

- [ ] **Step 3: Make it pass**

If the assertion reveals a real divergence in `traza.py` (different keys/structure than core), fix `traza.py` to match core's `append_event` output exactly, then re-run.

- [ ] **Step 4: Verde**

Run: `python -m pytest tests/test_intake_traza.py -v` (5 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/test_intake_traza.py
git commit -m "test(intake-skill): paridad de traza con core.intake_log (anti-drift)"
```

---

## Task 4: Autoría de `SKILL.md` (la skill de intake)

> No es TDD: es autoría de skill (sigue las convenciones del despacho). Verbatim abajo.

**Files:**
- Create: `.claude/skills/intake-expediente/SKILL.md`
- Create: `.claude/skills/intake-expediente/CHANGELOG.md`

- [ ] **Step 1: Escribir `SKILL.md`** con este contenido:

```markdown
---
name: intake-expediente
description: >-
  Deposita ficheros (de cualquier tipo y tamaño: PDFs, emails .eml, exports de
  WhatsApp .zip, transcripciones de entrevistas, fotos, vídeos) en la carpeta
  00_Input de un expediente FeesDefender del Drive, DIRIGIDO desde Claude
  (Cowork o Claude Code), y dispara la trazabilidad forense (evento upload_* en
  _intake_log.jsonl con hash SHA-256 por fichero). Usa el conector MCP
  expedientes-xl para todo lo que toca bytes (extraer/copiar/hashear server-side,
  sin que pasen por el modelo). Úsala cuando el usuario diga "sube esto al caso",
  "deposita este zip", "mete estos PDFs en el expediente", "ingesta este export
  de WhatsApp", "añade este email al caso". NO organiza la sala de lectura (eso
  es organizar-sala-lectura) NI valora viabilidad (triaje-viabilidad). NO procesa
  por fuente (MIME del email, OCR del PDF): eso es el pipeline local.
metadata:
  rol: input
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# intake-expediente

Deposita ficheros en `00_Input/<fuente>/` de un expediente del Drive, dirigido desde
Claude, **con trazabilidad**. Todo lo que toca bytes va **server-side** por el conector
`expedientes-xl` (los bytes nunca pasan por el modelo). La trazabilidad (evento `upload_*`)
se construye con el helper puro `scripts/traza.py` y se escribe con `append_text`.

## Requisitos
- Conector MCP **expedientes-xl** disponible (Plan 1), acotado a la raíz del Drive del
  despacho. Si no está, no se puede depositar — avisa.
- El fichero a subir debe estar **ya en un disco que el conector alcanza** (déjalo en
  `…/EXPEDIENTES - TYUKHAY LEGAL/_ingest/`). Ficheros grandes NO viajan por el chat;
  los pequeños (< tope) pueden entrar por `write_file_base64`.

## Fuentes y destino (`00_Input/`)
`01_Drive EV` · `02_Whatsapp/<rol>` · `03_Email` · `04_Manual` · `05_CRM` ·
`06_Entrevistas/<AAAA-MM-DD>_<rol>_<apellido>`. El evento `upload_*` se elige por fuente:
WhatsApp→`upload_whatsapp`, email→`upload_email`, entrevista→`upload_entrevista`, resto
manual→`upload_manual`.

## Procedimiento
1. **Resuelve el caso y la fuente.** Confirma la subcarpeta destino de `00_Input/`.
2. **Deposita (server-side):** `.zip`/`.tar` → `extract_archive(archivo, 00_Input/<fuente>/)`;
   fichero suelto → `copy_path`; binario pequeño solo en el chat → `write_file_base64`.
3. **Hashea** cada fichero depositado con `hash_path` (SHA-256 server-side).
4. **Dedup (aviso, no bloqueo):** lee `00_Input/_intake_log.jsonl` (si existe) y, con
   `traza.is_duplicate(log, sha)`, marca los que ya constaban. No re-deposita el crudo.
5. **Dispara la traza:** ejecuta `traza.build_upload_event(case_id, event, files=[{path,
   sha256}…], actor, ts)` (el `path` relativo a `00_Input/`, posix; `ts` ISO; `actor` =
   quien sube) → te devuelve la línea JSONL → escríbela con `append_text` a
   `00_Input/_intake_log.jsonl`.
6. **Reporta:** ficheros depositados por fuente, hashes, duplicados marcados.

## Qué NO hace (límites de capa)
- **NO** escribe el `_intake_hashes.json` (IntakeManifest): esa dedup pesada (aliases/
  reconcile/atómica) se reconcilia en **local con `core/`** (CLI/Streamlit), no se
  reimplementa aquí (evita drift). El evento de auditoría sí queda registrado.
- **NO** procesa por fuente (MIME del `.eml`, OCR del PDF, adjuntos faltantes de WhatsApp):
  eso es el pipeline local. Lo depositado lo recoge `inventory.scan` en la siguiente corrida.
- **NO** toca `90_Notas personales/` ni organiza la sala de lectura.

## Gotchas
- **El conector hace el trabajo de bytes.** Nunca leas el binario al contexto para
  hashear/copiar: usa `hash_path`/`copy_path`/`extract_archive`.
- **`traza.py` es puro** (sin IO): en Cowork lo ejecutas para OBTENER la línea, y la
  escribe el conector. Si añades un evento nuevo, debe estar en `core.intake_log.INTAKE_EVENTS`
  (lo vigila `tests/test_intake_traza.py::test_paridad_eventos_subconjunto_de_core`).
- **Sin PII en los paths** del evento más allá del nombre de fichero ya existente.
```

- [ ] **Step 2: Escribir `CHANGELOG.md`**

```markdown
# Changelog — intake-expediente

## 1.0 — 2026-06-22
- Versión inicial. Deposita ficheros en `00_Input/<fuente>/` vía el conector
  `expedientes-xl` (server-side) y dispara el evento `upload_*` en `_intake_log.jsonl`
  con SHA-256 por fichero, mediante el helper puro `scripts/traza.py`. Dedup de aviso
  sobre el log. El `IntakeManifest` (`_intake_hashes.json`) NO se reimplementa: se
  reconcilia en local con `core/`. No procesa por fuente (MIME/OCR) — eso es el pipeline.
```

- [ ] **Step 3: Validar la skill**

Run: `python -m scripts.check_skills 2>&1 | Select-String "intake-expediente"`
Expected: sin errores bloqueantes para `intake-expediente` (avisos de identidad/`.skill` aceptables; el `.skill` se empaqueta en el Plan 3).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/intake-expediente/SKILL.md .claude/skills/intake-expediente/CHANGELOG.md
git commit -m "feat(intake-skill): SKILL.md intake-expediente v1.0 + CHANGELOG"
```

---

## Task 5: Verificación end-to-end + cierre

**Files:** (ninguno nuevo)

- [ ] **Step 1: Suite del Plan 2 verde**

Run: `python -m pytest tests/test_intake_traza.py -v`
Expected: 5 passed.

- [ ] **Step 2: Smoke del flujo (manual, opcional, tras reiniciar sesión)**

Con el conector `expedientes-xl` cargado: dejar un `.zip` de prueba en `_ingest/`, pedir a
la skill que lo deposite en un caso de prueba, y verificar que (a) los ficheros aparecen en
`00_Input/<fuente>/` y (b) `_intake_log.jsonl` tiene una línea `upload_*` con los SHA-256.
Limpieza al terminar.

- [ ] **Step 3: Suite global no rota**

Run: `python -m pytest -q --tb=no`
Expected: sin regresiones (los cambios son aditivos: una skill nueva + un test nuevo).

---

## Notas de cierre
- **Plan 3/3 pendiente:** empaquetar el plugin FeesDefender (incluye esta skill + el
  conector + manifest `.claude-plugin/plugin.json` + `.mcp.json` con `${CLAUDE_PLUGIN_ROOT}`
  + marketplace privado + entrada `claude_desktop_config.json` para Cowork).
- **Diferido (no Fase A):** reconcile local del `IntakeManifest` para ficheros depositados
  desde Cowork (CLI que reusa `core.IntakeManifest` + `core.compute_sha256` sobre `00_Input/`).
- **Anti-drift:** `tests/test_intake_traza.py` ancla el esquema del evento a `core/intake_log.py`.
