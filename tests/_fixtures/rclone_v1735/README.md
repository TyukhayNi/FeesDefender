# Fixtures de rclone — v1.73.5, Windows amd64

Salidas de rclone **fijadas a una versión concreta**. Si rclone se actualiza, se
re-miden y se regeneran: el doble (`tests/_dobles/fake_drive.py`) promete fidelidad a
esta versión, no a rclone en general.

> **Trampa de medición, anotada en `CLAUDE.md`:** nunca leer el código de salida detrás
> de un `Select-Object -First N` en PowerShell — la terminación temprana del pipe lo
> deja en `0`. Ya falseó una medición de este mismo contrato (`copyto` de un origen
> inexistente parecía devolver 0 y devuelve **3**). Patrón correcto:
> `$out = & cmd args 2>&1` y leer `$LASTEXITCODE` acto seguido; en bash, `$?`.

## Procedencia por fichero

| Fichero | Cómo se obtuvo | Estado |
|---|---|---|
| `lsjson_local.json` | `rclone lsjson <dir> -R --hash --fast-list` sobre un árbol sintético de 2 ficheros y 2 directorios, creado en un temporal | **REAL, medido 2026-07-29** |
| `files_from_con_filtros.txt` | `stderr` de `rclone copy SRC DST --files-from lista.txt --exclude '*.tmp'` | **REAL, medido 2026-07-29** (`rc=1`, el destino ni se crea) |
| `lsjson_vacio.json` | `[]` a mano — es lo que devuelve un listado sin entradas | trivial |
| `lsjson_truncado.txt` | `[` a mano — es exactamente el `stdout` de un `lsjson` de ruta inexistente (`rc=3`) | forma **REAL**, medida |
| `lsjson_drive.json` | **Forma** de la medición de la rev. 2 del plan (2026-07-29) sobre el backend Drive; **valores sintéticos** | ⚠ **FUENTE ÚNICA, no re-medida** — re-medirla exige el Drive real, fuera del alcance de la Fase 0 |
| `lsjson_native.json` | **SINTÉTICA y declarada como tal** | ⚠ **la forma real está SIN VERIFICAR** (ver abajo) |

## Lo que se midió, y las tres cosas que sorprendieron

- **Local tiene 13 algoritmos de hash y NO tiene `ID`**; Drive tiene 3 (`md5`, `sha1`,
  `sha256`) y sí tiene `ID`. Las claves van **en minúscula en los dos backends**
  (`.get("md5")` es correcto; la tesis `Hashes.MD5` quedó refutada dos veces).
- **Los directorios no traen la clave `Hashes` en absoluto**, no la traen vacía.
- **`ModTime` tiene dos formatos**: local `"…T23:44:26.6114031+02:00"` (offset y 7
  decimales), Drive `"2026-05-29T07:41:12.000Z"`.
- **No hay backslashes en `Path`** en ningún backend: la fixture «Windows con
  backslashes» que pedía la primera revisión no existe.
- **Códigos de salida, y no son uniformes:** `copyto` de origen ausente → **3**;
  `moveto` de origen ausente → **1**; `lsjson` de ruta ausente → **3** con `stdout` `[`;
  `rmdirs` sobre árbol no vacío → **0** y no borra nada; `check` con cualquier
  diferencia → 1. Un doble que los unifique miente.
- **La frontera del `--log-file` no es «fallo/éxito» sino «validación de flags /
  ejecución»:** flags ilegales → `rc=1` y **no crea el log**; `copy` de un origen
  inexistente → `rc=3` y **sí crea el log** (1408 B medidos). De ahí el orden de
  procesamiento del doble.
- **`check --one-way`** cuenta lo que difiere y lo que falta en destino e **ignora los
  extras del destino** (2 diferencias frente a 3 sin el flag), y **compara por md5
  aunque no se pase `--checksum`** — luego `verificacion_limpia` es de fiar.

## Google-native: por qué su fixture es sintética

**Cero** entradas `application/vnd.google-apps*` en 3007 ficheros hasta profundidad 6 de
la unidad canónica (`MEJORAS #104`): la rama `hash is None` → `PRESERVE_DRIVE` de
`plan_merge` y el veto de grupo que depende de ella **nunca las ha ejercitado un dato
real**. No se muta el Drive para averiguar la forma.

No hace falta para lo que el doble tiene que garantizar: el contrato del parser
(`(item.get("Hashes") or {}).get("md5") or None`) trata igual las **tres** variantes
—sin clave `Hashes`, `Hashes: {}`, y `Hashes` sin `md5`—, así que la fixture emite las
tres y el test exige `hash is None` en todas. **La forma que emitiría Drive de verdad
queda declaradamente sin verificar.**
