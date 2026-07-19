---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-18
---

# Despliegue del MCP "Drive como disco" (`expedientes-xl` consolidado)

> Checklist ejecutable de la secuencia de despliegue del spec
> `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md` §8. Orden
> **OBLIGATORIO**: cada paso presupone el anterior cerrado. **Nunca** dejar una skill
> ya migrada a los nombres nuevos con el server viejo (`expedientes`) todavía activo, ni
> al revés — el desincronizado Code↔Cowork es justo lo que esta secuencia evita.
>
> Referencia de superficie y límites conocidos: `plugins/expedientes_xl/README.md`.

## ⚠️ CORRECCIÓN 2026-07-19 (aprendido al desplegar en vivo)

**Este checklist partía de una premisa equivocada:** que editar `claude_desktop_config.json`
(pasos 3-4) haría disponible `expedientes-xl` **en Cowork**. **NO es así.** Las entradas de
`claude_desktop_config.json` (mcpServers) alimentan el **chat directo de Claude Desktop** y
**Claude Code**, pero **NO llegan a la VM de Cowork**. **Cowork solo consume extensiones `.dxt`**
(por eso tenía gmail/google-despacho —importados como `.dxt`— y no expedientes-xl).

**Vía real a Cowork** = empaquetar un `.dxt` e importarlo en **Ajustes → Extensiones** (patrón de
`gmail_mcp`/`google_despacho_mcp`). Hecho 2026-07-19: `plugins/expedientes_xl/dxt-build/`
(`manifest.json` + `expedientes-xl.dxt` + README, PR #83). El manifest arranca
`python -m expedientes_xl.server --rw G:\ --ro H:\` con **ruta absoluta a `python.exe`**
(el `python` a secas cae en el **stub de la Microsoft Store** en el PATH de Claude Desktop) y
`env.PYTHONPATH` → `plugins/`. Detalle: `plugins/expedientes_xl/dxt-build/README.md`.

**Gotchas duros del proceso (dolor real de esta sesión):**
- El `.bat` del wrapper corría `python server.py` (script suelto) → `ImportError` de imports relativos.
  Fix: `python -m expedientes_xl.server` (contexto de paquete). PR #80.
- `python` a secas = stub de WindowsApps en el PATH persistente que ve Claude Desktop (no el del
  terminal). Fix: resolver un Python real, eludir WindowsApps. PR #82.
- Editar `claude_desktop_config.json` con la app viva **no recarga** (Electron reengancha a procesos
  de fondo) y el fichero se vacía/reescribe solo. Vía fiable: **`taskkill /F /IM claude.exe /T` + relanzar**.
- Dos `expedientes-xl` a la vez (config.json + `.dxt`) → conflicto que parpadea `failed` y tira otro
  server. Dejar **solo la `.dxt`**.
- Badge `failed` en Desarrollador con las tools funcionando = **cosmético** (health-check vs arranque del
  oracle). Ver `MEJORAS #74`.

Los pasos 3-4 de abajo **solo aplican al chat de Desktop / Claude Code**, no a Cowork.

## Secuencia de despliegue (spec §8 — orden OBLIGATORIO)

1. [ ] Mergear el PR de código; `python -m pytest -q --tb=no` verde en `main`.
2. [ ] Claude Code: verificar que `plugin-src/.mcp.json` apunta al `run_server.bat`
       (no directo a `server.py`) y que las tools nuevas responden (`read_text` sobre
       un fichero de `G:`).
3. [ ] Claude Desktop (Cowork): con la app **CERRADA** (¡reescribe su config al
       cerrar!), actualizar el bloque `expedientes-xl` en `claude_desktop_config.json`
       al wrapper.
4. [ ] Validar en Cowork: `read_text`/`list_dir`/`search_content` sobre `G:` y `H:`.
5. [~] Re-empaquetar las skills afectadas (**✅ repo, 2026-07-19 fase 2**:
       `organizar-sala-lectura` 1.8, `intake-expediente` 1.2, `checkout-caso`/`checkin-caso`
       con frontmatter canónico + CHANGELOG; 4 `.skill` en `dist/skills/`) y
       **re-importarlas en Cowork** (⏳ acción manual de Nikolai).
6. [x] **✅ repo, 2026-07-19 fase 2** — `organizar-sala-lectura` migrada al consolidado:
       `write_file`→`write_text`; `read_media_file` retirado (binarios server-side, no
       vuelven al modelo). Tres modos de acceso por ubicación del caso: (1) Drive vía
       `expedientes-xl`, (2) local-nativo (filesystem del entorno), (3) conector nube
       prefiriendo `google-despacho` sobre el nativo E&V. Tools citadas como `servidor:tool`.
7. [ ] **SOLO ENTONCES** retirar la entrada `expedientes` de
       `claude_desktop_config.json` **y** del scope proyecto de Claude Code
       (`claude mcp remove expedientes -s project`).
8. [ ] Sesión de humo: intake de un fichero de prueba + `tree` de un caso + `grep`
       (`search_content`) — ver checklist de la sesión de humo abajo.

**NUNCA** dejar la skill migrada con el server viejo activo (o viceversa).

## Bundle Claude Code (coherencia del lado Code — 2026-07-19 fase 2)

El lado Claude Code corría tools viejas. Estado de partida (verificado 2026-07-19):
`plugin:feesdefender:expedientes-xl` = **7 tools viejas** (incl. `delete_path`);
`expedientes-xl` standalone (scope proyecto) = **Failed** (arranca `server.py` directo con
`python` pelado → los 2 bugs ya corregidos en el `.dxt`/`run_server.bat`); `expedientes`
(Node FS) = activo. `dist/plugin` YA está reconstruido con las 19 tools + `.bat` corregido.

- [ ] **B1.** Quitar el standalone del scope proyecto: `claude mcp remove expedientes-xl -s project`
      (desde la RAÍZ del repo, no desde un worktree). No corta la sesión.
- [ ] **B2.** Refrescar el plugin: `/plugin marketplace update despacho-tyukhay` + reinstalar
      `feesdefender`.
- [ ] **B3.** **Reiniciar Claude Code** (necesario para cargar las 19 tools; **corta la sesión
      activa**). Verificar: `read_text`/`list_dir` sobre un fichero de `G:` responden y el
      plugin expone 19 tools (ya sin `delete_path`).

## Sesión de humo — puntos a vigilar

Estos son los cuatro puntos donde el despliegue puede fallar de forma no obvia,
detectados durante la construcción (Tasks 1-17). Revisar explícitamente en el paso 8:

1. **`run_server.bat` está terminado en LF, no CRLF.** Verificado en disco
   (`plugins/expedientes_xl/run_server.bat`: 0 CRLF, 42 LF). Normalmente `cmd.exe`
   tolera LF en `.bat`, pero si el wrapper se comporta de forma errática en la sesión
   de humo en vivo (falla al arrancar, cuelgue del poll-loop, etc.), **normalizar a
   CRLF** como primer diagnóstico antes de investigar más a fondo.
2. **`PROBE_H` solo comprueba `H:\Unidades compartidas`** — más superficial que
   `PROBE_G` (que apunta a `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS`,
   una hoja más poblada y específica). Si `H:` da un **falso-montado** (la carpeta
   `Unidades compartidas` existe pero el contenido real de E&V aún no sincronizó),
   **profundizar la sonda** de `PROBE_H` a una ruta más específica dentro de `H:`.
3. **`python` debe resolver en el PATH que ve Claude Desktop.** El wrapper invoca
   `python "%SRV%"` sin ruta absoluta al intérprete. Si Claude Desktop arranca con un
   PATH distinto al de la sesión interactiva (p. ej. servicio/entorno restringido), el
   fallo es **silencioso hacia el pipe MCP** — solo se ve en
   `%APPDATA%\Claude\logs\mcp-server-expedientes-xl-wrapper.log`. Revisar ese log si
   Cowork no conecta.
4. **Cancelación real de operaciones pesadas es V2.** `XL_OP_TIMEOUT` hace que el canal
   MCP **responda** aunque la E/S siga en curso en un hilo daemon en segundo plano — no
   hay forma de abortar esa E/S desde fuera. Si la sesión de humo dispara una operación
   muy pesada (árbol grande, extracción grande) y expira el timeout, el proceso puede
   seguir consumiendo E/S un rato tras la respuesta de error. Esperado, no un fallo del
   despliegue.

## Rollback

Si el paso 4 (validación en Cowork) falla: revertir el bloque `expedientes-xl` de
`claude_desktop_config.json` al `server.py` directo (sin wrapper) o, si el fallo es del
propio servidor consolidado, restaurar temporalmente la entrada `expedientes` (Node,
jubilado) — **nunca** dejar Cowork sin ningún servidor FS operativo mientras se
diagnostica. No avanzar a los pasos 5-7 (re-empaquetado de skills, migración,
jubilación) hasta que el paso 4 esté verde.
