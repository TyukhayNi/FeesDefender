---
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-05-21
---

# Migración FeesDefender — Cowork → Claude Code

> ⛔ **KIT CONSUMIDO — NO COPIES NADA DE AQUÍ** (marcado el 2026-08-03).
>
> La migración se ejecutó en mayo de 2026 y Claude Code es desde entonces el entorno de
> desarrollo. Este paquete es un **snapshot congelado del 2026-05-21** que se conserva como
> registro de la decisión, no como plantilla.
>
> **Los ficheros vivos son los de la raíz del repo y `.claude/`.** Los de esta carpeta son
> segundos ejemplares y **ya han derivado**: medido el 2026-08-03, los `commands/cierre.md`,
> `commands/status.md` y `commands/tests.md` de aquí difieren de los vigentes, y
> `CLAUDE_snapshot_2026-05-21.md` sigue afirmando «546/546 verdes en s20», cifra retirada del
> fichero vivo el 2026-08-03 por rancia (PR #192).
>
> **Por qué el snapshot ya no se llama `CLAUDE.md`:** Claude Code carga automáticamente
> cualquier fichero con ese nombre en el directorio en que se trabaja. Una copia de mayo con
> ese nombre era una instrucción latente esperando a que alguien abriese una sesión aquí.
> Renombrado el 2026-08-03; el contenido no se tocó.
>
> **No está indexado en `docs/INDICE.md` a propósito:** la población que ese índice cubre —y
> que vigilan sus guards— es `docs/*.md` **no recursivo**. Meter una fila de un fichero
> anidado mezclaría vocabularios (la trampa D3 de `GOBERNANZA_FUENTES_VERDAD.md`). Su estado
> vive aquí, en este frontmatter, que es su hogar.

> Paquete preparado en sesión 23 (2026-05-21).
> Objetivo: dejar el desarrollo del repo en Claude Code (CLI nativo Windows con PowerShell directo) y reservar Cowork solo para trabajo legal (escritos, comunicaciones, investigación CENDOJ).

## TL;DR

1. Instalar Claude Code.
2. Copiar los ficheros de esta carpeta a la raíz del repo y a `.claude/`.
3. Configurar variables de entorno (las que ya usas en `.env`).
4. Abrir el repo con `claude` desde PowerShell y leer `CLAUDE.md`.

Esta carpeta **no toca nada del repo**. Todo lo que hay aquí son plantillas — el paso de "copiar a destino" lo decides tú.

---

## Por qué migrar

Pain point principal documentado en memoria: PowerShell siempre lo ejecuta el usuario. En Claude Code eso desaparece — el agente ejecuta PS nativo en Windows, ve la salida en el mismo hilo y encadena el siguiente paso solo.

Eliminamos además:

- Desfase entre rutas Linux (`/sessions/.../mnt/...`) y Windows (`G:\...`).
- Latencia "Edit/Write puede tardar en aparecer en bash".
- Necesidad de copiar bloques PowerShell al portapapeles cada vez.
- Skills + slash commands quedan versionados con el repo (todo el equipo ve lo mismo).

Lo que **no** ganamos (y por eso Cowork sigue teniendo su sitio):

- MCPs preinstalados (Drive, Gmail, DocuSign, Chrome) — en Claude Code se configuran a mano.
- Botones "Save" / "Present files" con vista previa.
- Artefactos visuales / dashboards interactivos.
- Tareas programadas (`scheduled-tasks`).

Recomendación operativa: **código del repo → Claude Code; escritos, comunicaciones a clientes, investigación jurisprudencial → Cowork.**

---

## Contenido del paquete

```
docs/migracion_claude_code/
├── README.md                    ← este fichero
├── CLAUDE.md                    → copiar a raíz del repo
├── settings/
│   ├── settings.json            → copiar a .claude/settings.json
│   └── settings.local.json      → copiar a .claude/settings.local.json (gitignored)
├── commands/                    → copiar a .claude/commands/
│   ├── tests.md
│   ├── cierre.md
│   ├── renovar-php.md
│   ├── status.md
│   ├── pull-rclone.md
│   ├── health-check.md
│   └── sync-crm.md
├── hooks/
│   └── README.md                ← guía de hooks opcionales
├── skills/
│   ├── README.md                ← qué skills copiar y cómo
│   └── copiar_skills.ps1        → script PowerShell que copia las skills
└── mcp_servers.json             → plantilla (opcional)
```

Resultado final en el repo, tras aplicar el paquete:

```
<repo>/
├── CLAUDE.md                    ← nuevo
├── .claude/
│   ├── settings.json            ← versionado
│   ├── settings.local.json      ← gitignored
│   ├── commands/                ← versionado
│   ├── skills/                  ← versionado (subset relevante de Cowork)
│   └── mcp_servers.json         ← opcional, gitignored si tiene secretos
├── ... (resto del repo intacto)
```

---

## Paso a paso

### 1. Instalar Claude Code

Desde PowerShell (no requiere admin):

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
npm install -g @anthropic-ai/claude-code
claude --version
```

Login con la misma cuenta Anthropic que usas en Cowork:

```powershell
claude login
```

### 2. Copiar `CLAUDE.md` a la raíz

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
Copy-Item ".\docs\migracion_claude_code\CLAUDE.md" ".\CLAUDE.md"
```

`CLAUDE.md` se carga automáticamente cada vez que abres Claude Code en este directorio. Es el equivalente a "Project instructions" de Cowork.

### 3. Crear `.claude/` y copiar settings + commands

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
New-Item -ItemType Directory -Force -Path ".claude\commands" | Out-Null
Copy-Item ".\docs\migracion_claude_code\settings\settings.json"       ".\.claude\settings.json"
Copy-Item ".\docs\migracion_claude_code\settings\settings.local.json" ".\.claude\settings.local.json"
Copy-Item ".\docs\migracion_claude_code\commands\*.md"                ".\.claude\commands\"
```

### 4. Copiar skills (opcional pero recomendado)

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
.\docs\migracion_claude_code\skills\copiar_skills.ps1
```

El script copia desde el repositorio local de skills de Cowork a `.claude/skills/` del repo. Detalle y alternativas en `skills/README.md`.

### 5. Actualizar `.gitignore`

Añadir al `.gitignore` del repo:

```
# Claude Code — local
.claude/settings.local.json
.claude/mcp_servers.json
```

`settings.json` y `commands/` SÍ se versionan (todo el equipo comparte la misma configuración base).

### 6. Configurar MCPs (opcional, solo si los necesitas)

Por ahora ninguno es estrictamente necesario para el desarrollo del core. Si más adelante quieres conectar:

- **sudespacho CRM** (cuando el wrapper esté listo) — ver `mcp_servers.json` plantilla.
- **Google Drive E&V** — solo si quieres operar el Drive desde el chat sin pasar por rclone.
- **Gmail despacho** — solo si quieres redactar/buscar correo desde el chat.

Detalle en `mcp_servers.json` (comentado).

### 7. Primer arranque

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
claude
```

Primer mensaje sugerido en el chat:

```
Lee STATUS.md y dime cuál es el [SIGUIENTE] abierto.
```

A partir de ahí, todo funciona como en Cowork pero con PS nativo.

---

## Equivalencias Cowork ↔ Claude Code

| Cowork | Claude Code |
|---|---|
| "Project instructions" | `CLAUDE.md` en raíz del repo |
| Skills `/skills/...` | `.claude/skills/<slug>/SKILL.md` |
| MCP catálogo Cowork | `.claude/mcp_servers.json` (manual) |
| Plan mode | Plan mode nativo (`/plan`) |
| `mcp__cowork__present_files` | `claude` muestra rutas; el usuario abre con Explorer |
| Subagentes Cowork (Plan, Explore) | Subagentes Claude Code (igual API) |
| Skill `preparacion-litigio-civil` | Sigue funcionando idéntica en `.claude/skills/` |
| Skill `escritos-judiciales` | Igual — pero el `.docx` final lo guardas tú en el caso |
| Skill `cendoj-descarga` | Solo si copias Chrome MCP a Claude Code; alternativa: seguir usando Cowork solo para esto |

---

## Qué dejamos en Cowork

No tiene sentido migrar todo. Estas tareas siguen siendo más cómodas en Cowork:

- Redacción de escritos procesales (`.docx` finales con preview).
- Búsqueda y descarga CENDOJ (Chrome MCP ya conectado).
- Comunicaciones a clientes (Gmail / Drive ya conectados).
- Investigación jurisprudencial general.
- Análisis de viabilidad de casos concretos cuando no implican tocar código.

El repo puede vivir abierto en Claude Code y Cowork a la vez sin conflicto — son procesos independientes que leen los mismos ficheros.

---

## Rollback

Si por algún motivo decides volver a Cowork como única vía:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
Remove-Item -Recurse -Force ".\.claude"
Remove-Item ".\CLAUDE.md"
```

El paquete `docs/migracion_claude_code/` se queda — sirve para volver a aplicar la migración cuando quieras. Nada del repo cambia salvo la adición de `CLAUDE.md` y `.claude/`.

---

## Próximos pasos sugeridos tras migrar

1. Probar el flujo "abrir Claude Code → leer STATUS.md → arrancar [SIGUIENTE]" con un cambio pequeño (corregir un typo o mejorar un docstring).
2. Probar `/tests` y `/cierre` para verificar que los slash commands ejecutan PS sin fricción.
3. Si todo va bien tras 2-3 sesiones, considerar mover también la configuración personal del editor (VSCode + extensión Claude Code) para tener autocompletado y diff inline.

---

## Soporte

Si algo no funciona al aplicar el paquete, los ficheros más probables a revisar son (en este orden):

1. `CLAUDE.md` — reglas que no se entienden o ambiguas.
2. `.claude/settings.json` — permisos demasiado restrictivos.
3. `.claude/commands/<nombre>.md` — el script PS del comando no encuentra venv o entry point.

El paquete está pensado para ser **autocontenido y reversible**.
