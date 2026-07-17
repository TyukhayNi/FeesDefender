# expedientes-xl

Servidor MCP stdio **consolidado** de operaciones de fichero acotadas a un sandbox de
directorios sobre el montaje local de Google Drive (GDFD): `G:` (Drive del despacho,
Tyukhay) y `H:` (Drive del cliente, Engel & Völkers). Sin lógica de FeesDefender
(no `import core`): solo opera sobre bytes, zonas y guardas genéricas.

Desde la consolidación (spec `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md`)
absorbe también la navegación/lectura/búsqueda/escritura de texto que antes cubría el
servidor Node `expedientes` (jubilado — ver §8 del spec y `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md`
para la secuencia de migración).

## Requisitos
- Python 3 + `python -m pip install -r requirements.txt` (instala `mcp`).
- Los directorios permitidos montados en disco (`G:\`, `H:\` — Drive for Desktop / GDFD).

## Registro

### Claude Code
```
claude mcp add expedientes-xl -- python <ruta>/plugins/expedientes_xl/server.py --rw G:\ --ro H:\
```

### Cowork (Claude Desktop, vía claude_desktop_config.json)
El plugin empaquetado (`plugin-src/.mcp.json`) ya apunta al wrapper `run_server.bat`
(poll-until-mount de `G:` y `H:` antes de arrancar el server; ver §8 del spec y el
checklist de despliegue). Registro manual equivalente:
```json
{
  "mcpServers": {
    "expedientes-xl": {
      "command": "cmd",
      "args": ["/c", "<ruta>/plugins/expedientes_xl/run_server.bat"]
    }
  }
}
```

**IMPORTANTE**: editar `claude_desktop_config.json` con Claude Desktop **CERRADO** —
la app reescribe su config al cerrar y un cambio con la app abierta se pierde
(`reference-claude-desktop-config-clobber`).

Zonas por *tier* (spec §2): pasar `--rw DIR` (lectura+escritura, repetible) y/o
`--ro DIR` (solo-lectura en V1, repetible); un `<allowed_dir>` posicional se trata como
`--rw` (compat). Opcional: `--max-b64-bytes N` para el tope de `write_file_base64`
(def. 8 MiB). En V1: `--rw G:\ --ro H:\` — `H:` entera es solo-lectura (§2, §5.1
Tier 2 del spec); ningún flujo real escribe en el Drive de E&V hoy.

## Zonas por tier (spec §2)

La clasificación se resuelve sobre la ruta **canónica** (symlinks/atajos ya resueltos),
por patrón de segmento, en **origen y destino**, y se re-evalúa **por cada nodo**
visitado en operaciones recursivas (`tree`/`copy_dir`/`hash_tree`/`search_content`).

| Tier | Zona | Lectura | Escritura |
|---|---|---|---|
| **0 — Prohibida** | `90_Notas personales` / `90_NOTAS_PERSONALES` | **Nunca** (ni al modelo) | Nunca |
| **1 — Forense-inmutable** | `00_Input` (original forense) y backups (`Otros ordenadores`, `BACKUP`, `BACKUP MADRID`, `TWBCN-Backup2`) | Sí | Crear-nuevo (no-overwrite) sí; sobrescribir/editar solo carve-out de protocolo (`_caso.md`, `MANIFEST_CHECKOUT.json`, `_intake_log.jsonl` y `AUDITLOG_MERGE_*.jsonl` en modo append). Backups: solo-lectura, sin excepciones |
| **2 — Workspace** | El resto de `G:` | Sí | Sí |
| — | `H:` entera (V1) | Sí | **No** — unidad solo-lectura en V1 (independiente del tier del path) |

Nodo Tier 0 encontrado en una travesía → se **poda** el subárbol (nunca aborta el resto).
La poda se refleja en el **contador del valor de retorno** (`podados` / `_podados` de
`tree`/`list_dir`/`search_content`, etc.); el log de auditoría solo registra un evento de
poda en el caso del symlink re-validado de `hash_tree` (`podado_symlink_tier0`) — la poda
de directorios Tier 0 no escribe en `audit.jsonl` (comportamiento intencional en V1).
Destino efectivo Tier 1 fuera del carve-out → **aborta** la operación completa antes de
tocar bytes (pre-scan en dos pasadas para `copy_dir`). `SIN borrado` en ningún tier:
`delete_path` está **retirado** de la superficie (spec §2).

## Superficie de tools (19)

Todas validan zonas (`tiers.py`) y guardas Stream-aware (`guards.py`) antes de delegar
en `fsops.py`/`readops.py`; las mutaciones quedan auditadas (`audit.py`, JSONL
append-only en `XL_AUDIT_PATH`).

### Leer
| Tool | Firma | Notas |
|---|---|---|
| `read_text` | `(path, head=None, tail=None) -> str` | UTF-8 `errors="replace"`, tope `XL_READ_MAX_BYTES`. `tail` lee el final real del fichero (seek). Lectura completa que excede el tope termina con línea `[TRUNCADO: ...]`. |
| `read_multiple` | `(paths: list[str]) -> dict[str, str]` | Un fallo individual no tumba el lote (queda como `"ERROR: ..."` en su entrada). |

### Navegar
| Tool | Firma | Notas |
|---|---|---|
| `list_dir` | `(path, sizes=False) -> list[dict]` | Poda Tier 0; añade `{"_podados": n}` y `{"_truncado": true}` si aplica (tope 500 entradas). |
| `tree` | `(path, max_depth=8) -> dict` | `{entries, podados, truncado, omitidos_profundidad}`. `omitidos_profundidad` cuenta ficheros más allá de `max_depth` (sin silencios). Guarda de árbol frío (§6.2). |
| `get_metadata` | `(path) -> dict` | `{name, size, mtime, is_dir, tier, hydration}`. |
| `resolve_shortcut` | `(path) -> dict` | Resuelve un `.lnk` (vía COM/PowerShell, ruta por variable de entorno — sin inyección) y **re-valida** el destino contra sandbox y tiers. `target=None` si escapa del sandbox, cae en Tier 0, o la resolución falla (fail-closed). |
| `hydration_status` | `(path) -> dict` | `{"status": "HOT"\|"COLD"\|"UNKNOWN"}` — tool del oráculo (§4 del spec). |

### Buscar
| Tool | Firma | Notas |
|---|---|---|
| `search_name` | `(path, patron) -> list[str]` | `fnmatch` case-insensitive, poda Tier 0, tope 200 resultados. |
| `search_content` | `(path, consulta, regex=False) -> dict` | `{matches, omitidos_cold, podados}`. Salta binarios (byte nulo en los primeros 8 KB) y `.g*` (stubs nativos de Google); COLD/UNKNOWN por encima del umbral se omiten y se listan, nunca abortan el resto del árbol. |

### Escribir (texto/dirs — Tier 2 o carve-out Tier 1; atómico §6.1)
| Tool | Firma | Notas |
|---|---|---|
| `create_dir` | `(path) -> str` | Crea con padres. |
| `write_text` | `(path, text) -> str` | Atómico (tmp+nonce mismo directorio + `os.replace`). |
| `edit_text` | `(path, old, new) -> str` | Reemplaza **exactamente 1** aparición exacta; atómico. Error si `old` aparece 0 o ≥2 veces. |
| `append_text` | `(path, text) -> str` | Crea el fichero si falta. Pensado para `.jsonl` de protocolo. |
| `write_file_base64` | `(path, content_b64) -> int` | Tope duro de tamaño (`--max-b64-bytes`, def. 8 MiB); comprobado ANTES de escribir. |

### Copiar
| Tool | Firma | Notas |
|---|---|---|
| `copy_path` | `(src, dst) -> str` | No destructivo; zonas + `check_gdoc` + guarda de hidratación del ORIGEN (una copia lee bytes del origen); destino atómico (write, sin guarda de hidratación — no aplica). |
| `copy_dir` | `(src, dst) -> dict` | **Devuelve dict** `{"copiados": [...]}` (no lista plana). Travesía por nodo: poda Tier 0, **pre-scan** que valida CADA destino antes de copiar nada (aborta si alguno viola zonas), guarda de árbol frío. Los stubs `.gdoc`/`.gsheet`/… del origen se **omiten** (auditado `omitido_gdoc`), nunca abortan el árbol. No recrea directorios vacíos; symlinks-fichero se **deferencian** (contenido copiado, no recreados como enlace). |

### Comprimir
| Tool | Firma | Notas |
|---|---|---|
| `extract_archive` | `(archive_path, dest_dir, strip_top_level=False) -> dict` | **Devuelve dict** `{"extraidos": [...], "omitidos": [...]}` (no lista plana). Zip/tar; presupuesto anti zip-bomb; saneado anti path-traversal por miembro; cada miembro se valida contra zonas antes de volcar bytes (el que cae en Tier 0 o Tier 1-existente se **omite**, listado en `omitidos`, nunca aborta el resto). |

### Integridad
| Tool | Firma | Notas |
|---|---|---|
| `hash_path` | `(path) -> str` | SHA-256 (hex), server-side. |
| `hash_tree` | `(root) -> dict[str, str]` | `{relpath_posix: sha256hex}`. Poda Tier 0 (incluido symlink-fichero suelto que apunte a Tier 0: se re-valida por ruta resuelta). Guarda de árbol frío. |

**Sin borrado**: `delete_path` fue retirado de la superficie (spec §2) — no hay ningún
tool que borre ficheros o directorios.

## Variables de entorno `XL_*`

| Variable | Default | Efecto |
|---|---|---|
| `XL_AUDIT_PATH` | `%LOCALAPPDATA%\FeesDefender\xl_audit.jsonl` | Ruta del log de auditoría JSONL append-only (fuera del volumen Drive). Best-effort: un fallo de escritura no rompe la operación. |
| `XL_ORACLE_TTL` | `5` (segundos) | TTL del snapshot SQLite del oráculo de hidratación (anti-thrashing: un `backup()` por ráfaga, no por operación). |
| `XL_HYDRATION_MAX_FILE_MB` | `10` | Umbral de tamaño de fichero por encima del cual se exige HOT antes de leer/copiar (si no, `ERROR_FILE_NOT_HYDRATED`). |
| `XL_TREE_MAX_MB` | `150` | Umbral de volumen lógico acumulado de un árbol; se aborta si se supera (independiente del conteo COLD). |
| `XL_TREE_MAX_COLD` | `50` | Umbral de nº de ficheros COLD en un árbol; se aborta si se supera (evita ráfagas de hidratación / rate-limit 403). |
| `XL_ORACLE_STRICT` | `0` | Si `"1"`, exige validación cruzada BD↔`content_cache` (decodifica varints del blob `content-entry` y comprueba que el content-id aparece como nombre de fichero en caché) antes de declarar HOT. Más estricto, más caro. |
| `XL_READ_MAX_BYTES` | `5000000` (~5 MB) | Tope de lectura de `read_text`/`read_multiple`. Superarlo en lectura completa (sin `head`/`tail`) trunca con marcador `[TRUNCADO: ...]`. |
| `XL_IO_CAP` | `2` | Tamaño del semáforo global de E/S pesada (`hash_tree`/`copy_dir`/`extract_archive`/`tree`/`search_content`). Evita que 2+ pipelines pesados desmonten `G:`/`H:` simultáneamente. |
| `XL_OP_TIMEOUT` | `120` (segundos) | Timeout de respuesta del canal MCP para operaciones pesadas. **Responde** con error aunque la E/S siga en curso en el hilo daemon (timeout-que-responde, spec §3.2) — la cancelación-que-aborta-E/S real queda V2. |

## Límites conocidos (V1)

- **`H:` 100 % COLD**: la primera lectura de cualquier fichero de `H:` es una
  **descarga** (Stream puro, sin caché local previo — a diferencia de `G:`, ~26 % COLD
  con ~22 GB de caché). Planificar operaciones grandes sobre `H:` en consecuencia.
- **Stubs nativos de Google** (`.gdoc`, `.gsheet`, `.gslides`, `.gdraw`, `.gform`,
  `.gtable`, `.gmap`) son **ilegibles por el sistema de ficheros** (a nivel de kernel
  Windows da `ERROR_INVALID_FUNCTION`). `copy_path` y las lecturas (`read_text`/
  `search_content`) enrutan por `check_gdoc` y **lanzan `GDocBloqueado`** (mensaje
  amigable que desvía a `google-despacho`); `copy_dir` los **omite** (auditado
  `omitido_gdoc`, listado nunca silencioso). **`hash_path` NO pasa por `check_gdoc`**
  (solo `guard_file`): sobre un stub `.g*` también falla, pero con un **`OSError` crudo**
  (`ERROR_INVALID_FUNCTION` del kernel), no el `GDocBloqueado` amigable. En todos los
  casos, usa `google-despacho` (`export_to_drive`/`read_file_content`) para su contenido
  real.
- **Conflict-copies de la nube** son un límite inherente de GDFD: la escritura atómica
  (`tmp` + `os.replace`) protege la integridad **local** únicamente. Si un tercero edita
  la versión web mientras se escribe, Drive puede generar una copia de conflicto — no
  hay forma de evitarlo desde el cliente FS.
- **El oráculo de hidratación es OPCIONAL y fail-closed**: si la BD SQLite interna de
  DriveFS no está disponible o cambió de esquema, el estado es `UNKNOWN` y las guardas
  lo tratan como COLD — lecturas/árboles grandes **abortan** en vez de arriesgar una
  hidratación silenciosa. Ante `ERROR_FILE_NOT_HYDRATED`/`ERROR_TREE_NOT_HYDRATED`: fijar
  la carpeta "Disponible sin conexión" en la UI de Drive, o autorizar la descarga.
  **`attrib +P` NO fuerza hidratación en GDFD** (verificado; no usar como workaround).
- **`copy_dir`/`extract_archive` devuelven dicts estructurados**, no listas planas:
  `copy_dir` → `{"copiados": [...]}`; `extract_archive` → `{"extraidos": [...],
  "omitidos": [...]}`. Cualquier consumidor (skill) que parseaba el `copy_tree`/
  `extract_archive` antiguos como lista debe adaptarse — afecta en particular a
  `intake-expediente`.
- **`copy_dir` no recrea directorios vacíos** y **deferencia symlinks-fichero**
  (copia el contenido en vez de recrear el enlace) — cambio de semántica intencional
  respecto al `copy_tree` anterior.
- **`tree` añade `omitidos_profundidad`** (ficheros más allá de `max_depth`) junto a
  `entries`/`podados`/`truncado` — sin silencios.
- **Cancelación real de operaciones pesadas es V2**: el timeout de `XL_OP_TIMEOUT`
  responde al canal MCP, pero el hilo daemon puede seguir con la E/S en segundo plano.

## Verificación
- `python -m pytest tests/test_expedientes_xl_fsops.py tests/test_expedientes_xl_server.py tests/test_expedientes_xl_tiers.py tests/test_expedientes_xl_guards.py tests/test_expedientes_xl_oracle.py tests/test_expedientes_xl_readops.py tests/test_expedientes_xl_winio.py tests/test_expedientes_xl_audit.py tests/test_expedientes_xl_integracion.py -v`
- `claude mcp add … && claude mcp list` → debe salir `expedientes-xl … √ Connected`.
- Checklist de despliegue completo (Code → Cowork → migración de skills →
  jubilación de `expedientes`): `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md`.
