# Empaquetado del plugin FeesDefender (Plan 3/3) — Implementation Plan

> **For agentic workers:** este plan es de EMPAQUETADO (no TDD red-green). Pasos con checkbox `- [ ]`. Verificación = `claude plugin validate` + install local + suite verde.

**Goal:** Empaquetar el conector `expedientes_xl` + la skill `intake-expediente` como un **plugin instalable `feesdefender`**, ensamblado por un build script desde la SSOT, validado e instalable en local; con guía de distribución a un repo git privado y de configuración en Cowork.

**Architecture:** Metadatos del plugin tracked en `plugin-src/` (manifest + `.mcp.json` + plantilla de marketplace). `scripts/package_plugin.py` ensambla `dist/plugin/` (gitignored) copiando: el esqueleto de `plugin-src/`, el conector `plugins/expedientes_xl/`, y la skill `.claude/skills/intake-expediente/`. La SSOT no se duplica en git; `dist/` es artefacto reproducible (como `package_skill.py`).

**Tech Stack:** Python (build script), `claude plugin` CLI (validate/marketplace/install). Windows + PowerShell.

---

## Estructura de ficheros

Tracked (SSOT de metadatos del plugin):
- Create: `plugin-src/.claude-plugin/plugin.json` — manifest del plugin.
- Create: `plugin-src/.mcp.json` — declara el server `expedientes-xl` con `${CLAUDE_PLUGIN_ROOT}`.
- Create: `plugin-src/marketplace.json` — plantilla de marketplace (lista el plugin).
- Create: `scripts/package_plugin.py` — ensambla `dist/plugin/`.
- Modify: `.gitignore` — asegurar que `dist/` está ignorado (probablemente ya lo está).

Generado (gitignored, por el build):
```
dist/plugin/
├── .claude-plugin/marketplace.json
└── feesdefender/
    ├── .claude-plugin/plugin.json
    ├── .mcp.json
    ├── expedientes_xl/{__init__.py,fsops.py,server.py,requirements.txt,README.md}
    └── skills/intake-expediente/{SKILL.md,CHANGELOG.md,scripts/traza.py}
```

---

## Task 1: Metadatos tracked del plugin (`plugin-src/`)

- [ ] **Step 1: `plugin-src/.claude-plugin/plugin.json`**
```json
{
  "name": "feesdefender",
  "version": "0.1.0",
  "description": "Despacho Tyukhay Legal — depósito de ficheros al expediente (conector expedientes-xl) + skill de intake con trazabilidad.",
  "author": { "name": "Tyukhay Legal", "email": "nikolai.tyukhay@tyukhay.legal" },
  "license": "Proprietary"
}
```

- [ ] **Step 2: `plugin-src/.mcp.json`** (servidor host-side, ruta al binario vía `${CLAUDE_PLUGIN_ROOT}`)
```json
{
  "mcpServers": {
    "expedientes-xl": {
      "command": "python",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/expedientes_xl/server.py",
        "G:\\Unidades compartidas\\EXPEDIENTES - TYUKHAY LEGAL"
      ]
    }
  }
}
```

- [ ] **Step 3: `plugin-src/marketplace.json`** (plantilla; el build la copia a `dist/plugin/.claude-plugin/`)
```json
{
  "name": "despacho-tyukhay",
  "description": "Marketplace de plugins del despacho Tyukhay Legal.",
  "owner": { "name": "Tyukhay Legal" },
  "plugins": [
    {
      "name": "feesdefender",
      "source": "./feesdefender",
      "description": "Conector expedientes-xl + skill intake-expediente."
    }
  ]
}
```

- [ ] **Step 4: Commit**
```bash
git add plugin-src/.claude-plugin/plugin.json plugin-src/.mcp.json plugin-src/marketplace.json
git commit -m "feat(plugin): metadatos tracked del plugin feesdefender (manifest + .mcp.json + marketplace)"
```

---

## Task 2: Build script `scripts/package_plugin.py`

- [ ] **Step 1: Escribir el script**
```python
"""Ensambla el plugin `feesdefender` en dist/plugin/ desde la SSOT.

Copia: plugin-src/ (metadatos) + plugins/expedientes_xl/ (conector) +
.claude/skills/intake-expediente/ (skill). Salida gitignored y reproducible.
Uso: python -m scripts.package_plugin
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "plugin-src"
CONECTOR = ROOT / "plugins" / "expedientes_xl"
SKILL = ROOT / ".claude" / "skills" / "intake-expediente"
OUT = ROOT / "dist" / "plugin"
PLUGIN = OUT / "feesdefender"

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def _copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_IGNORE)


def build() -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    (PLUGIN / ".claude-plugin").mkdir(parents=True)
    # marketplace.json -> dist/plugin/.claude-plugin/
    shutil.copy2(SRC / "marketplace.json", OUT / ".claude-plugin" / "marketplace.json")
    # plugin.json -> dist/plugin/feesdefender/.claude-plugin/
    shutil.copy2(SRC / ".claude-plugin" / "plugin.json", PLUGIN / ".claude-plugin" / "plugin.json")
    # .mcp.json -> dist/plugin/feesdefender/
    shutil.copy2(SRC / ".mcp.json", PLUGIN / ".mcp.json")
    # conector -> dist/plugin/feesdefender/expedientes_xl/
    _copytree(CONECTOR, PLUGIN / "expedientes_xl")
    # skill -> dist/plugin/feesdefender/skills/intake-expediente/
    _copytree(SKILL, PLUGIN / "skills" / "intake-expediente")
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"[package_plugin] plugin ensamblado -> {out}")
```

- [ ] **Step 2: Ejecutar el build**
Run: `python -m scripts.package_plugin`
Expected: imprime la ruta; `dist/plugin/feesdefender/` contiene manifest, `.mcp.json`, `expedientes_xl/` y `skills/intake-expediente/`.

- [ ] **Step 3: Verificar el árbol generado**
Run (PowerShell): `Get-ChildItem -Recurse dist/plugin | Select-Object FullName`
Expected: la estructura de la sección "Estructura de ficheros".

- [ ] **Step 4: Commit**
```bash
git add scripts/package_plugin.py
git commit -m "feat(plugin): scripts/package_plugin.py ensambla el plugin desde la SSOT"
```

---

## Task 3: Validar e instalar en local (Claude Code)

- [ ] **Step 1: Validar plugin y marketplace**
Run:
```powershell
claude plugin validate "dist/plugin/feesdefender"
claude plugin validate "dist/plugin"
```
Expected: `√ Validation passed` (avisos cosméticos ok). Si falla, corregir `plugin-src/` y re-ejecutar el build.

- [ ] **Step 2: Añadir marketplace local + instalar**
Run:
```powershell
claude plugin marketplace add "C:\Users\tnm33\Dev\FeesDefender\dist\plugin"
claude plugin install "feesdefender@despacho-tyukhay"
claude plugin details feesdefender
```
Expected: instala; `details` muestra `Skills (1) intake-expediente` y `MCP servers (1) expedientes-xl`.

- [ ] **Step 3: Nota** — las tools del MCP del plugin cargan al reiniciar la sesión (host-side). Smoke real de la tubería ya verificado en Plan 1 (`smoke_expedientes_xl.py`). La verificación de "carga en Cowork como plugin" quedó descartada (Cowork no carga plugins de Code — `DEAD_ENDS`/spec); para Cowork la entrega es `claude_desktop_config.json` + re-import `.skill`.

---

## Task 4: Documentación de distribución

- [ ] **Step 1: Crear `plugin-src/README.md`** con:
  - Build: `python -m scripts.package_plugin`.
  - Prerrequisitos por máquina: Python + `pip install mcp`; Drive montado en `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL`.
  - Instalación local (Claude Code): `claude plugin marketplace add <dist/plugin>` + `claude plugin install feesdefender@despacho-tyukhay`.
  - Distribución al despacho: subir el contenido de `dist/plugin/` (o un `plugin-src/` equivalente) a un **repo git privado** `despacho-plugins`; añadir el marketplace en Claude Desktop por `owner/repo`.
  - Cowork: el plugin NO carga nativo; usar `claude_desktop_config.json` para el conector + re-import `.skill` para las skills (canales verificados).

- [ ] **Step 2: Commit**
```bash
git add plugin-src/README.md
git commit -m "docs(plugin): guía de build, instalación local y distribución privada"
```

---

## Notas de cierre
- **Push manual:** crear el repo privado `despacho-plugins` en GitHub (web; no hay `gh`) y empujar el marketplace; entonces el despacho instala por `owner/repo`.
- **Incremental:** añadir más skills al plugin = copiarlas en `package_plugin.py` (lista de skills) + rebuild. Empezar mínimo (intake + conector), crecer luego.
- **Dependencia `mcp`:** documentada como prerrequisito; no se bundlea (evita arrastrar el venv).
