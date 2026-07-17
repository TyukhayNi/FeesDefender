# Despliegue del MCP "Drive como disco" (`expedientes-xl` consolidado)

> Checklist ejecutable de la secuencia de despliegue del spec
> `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md` §8. Orden
> **OBLIGATORIO**: cada paso presupone el anterior cerrado. **Nunca** dejar una skill
> ya migrada a los nombres nuevos con el server viejo (`expedientes`) todavía activo, ni
> al revés — el desincronizado Code↔Cowork es justo lo que esta secuencia evita.
>
> Referencia de superficie y límites conocidos: `plugins/expedientes_xl/README.md`.

## Secuencia de despliegue (spec §8 — orden OBLIGATORIO)

1. [ ] Mergear el PR de código; `python -m pytest -q --tb=no` verde en `main`.
2. [ ] Claude Code: verificar que `plugin-src/.mcp.json` apunta al `run_server.bat`
       (no directo a `server.py`) y que las tools nuevas responden (`read_text` sobre
       un fichero de `G:`).
3. [ ] Claude Desktop (Cowork): con la app **CERRADA** (¡reescribe su config al
       cerrar!), actualizar el bloque `expedientes-xl` en `claude_desktop_config.json`
       al wrapper.
4. [ ] Validar en Cowork: `read_text`/`list_dir`/`search_content` sobre `G:` y `H:`.
5. [ ] Re-empaquetar las skills afectadas y re-importarlas en Cowork.
6. [ ] Migrar `organizar-sala-lectura` a los nombres del consolidado
       (`write_file`→`write_text`; `read_media_file`→**YA NO** — los binarios no
       vuelven a pasar por el modelo, se manejan server-side).
7. [ ] **SOLO ENTONCES** retirar la entrada `expedientes` de
       `claude_desktop_config.json`.
8. [ ] Sesión de humo: intake de un fichero de prueba + `tree` de un caso + `grep`
       (`search_content`) — ver checklist de la sesión de humo abajo.

**NUNCA** dejar la skill migrada con el server viejo activo (o viceversa).

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
