---
tipo: revision-adversarial
objeto: "diseño «Ficheros de protocolo: por dónde están, no por cómo se llaman» (rev. 1), para cerrar MEJORAS #149"
objeto_rev: "1"
commit: "ff2ecd4"
ronda: "1"
revisor: Claude Code (sesión independiente)
veredicto: REQUIERE-REVISION
marcador_nonce: vzqk
sha256_informe: 9bccee50bcb4ea81fef72c5fa49ae65d8c57435d7c8d809fd35c3dfaed370f47
adjudicado_en: docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md §8
adjudicador: Claude Code
independencia_adjudicacion: "más débil — autor y revisor son el mismo modelo (AGENTS.md §Revisor sustituto)"
---

> **Acta de revisión adversarial R1 sobre un DISEÑO.** El §0 es el mandato literal, el §1
> conserva la voz del revisor sin una coma cambiada, el §2 es la evidencia que verifiqué por mi
> cuenta y el §3 el mapa hallazgo → dónde se remedió.
>
> **Dónde vive la adjudicación:** en la **rev. 2 del propio diseño**
> (`2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md`, §8), como manda `CLAUDE.md`.
>
> **Revisor sustituto, y su independencia es MÁS DÉBIL.** Codex no tiene cupo (2026-09-05). El
> revisor fue un subagente de Claude Code sin el contexto de autoría (`AGENTS.md` §«Revisor
> sustituto»); autor y revisor son el mismo modelo. Lo que compensa: implementó literalmente el
> enunciado del §3.2 y lo ejecutó contra el árbol (`probes/probe_contrato.py`), y reprodujo con una
> carrera simulada la pérdida de H-01 (`probes/probe_carrera_migracion.py`). Se registra como
> `revisor: Claude Code (sesión independiente)`, nunca como «Codex».
>
> **Esta es la primera de las dos rondas** que la pieza compra por radio de daño: decide qué es
> prueba documental y toca el único `unlink()` de un fichero que no es un temporal. La segunda va
> sobre el diff.
>
> **Higiene del workdir:** el directorio se creó vacío para esta ronda; un primer intento de la
> misma ronda murió por límite de uso sin escribir nada, y el relanzamiento encontró solo el
> `MANDATO.md`, como el revisor declara en su primera línea. El digest se recalculó al recibirlo
> (`9bccee50…`) y coincide.

## 0. Mandato, literal

# MANDATO — Revisión adversarial R1 sobre un DISEÑO (FeesDefender, MEJORAS #149)

## Higiene, primero

- **Solo lectura.** No editas, creas ni borras nada dentro del repo. Nada de `git checkout`, `stash`, `commit`, `merge`, `rebase`.
- Tu único fichero de salida es `INFORME.md` en el directorio de trabajo indicado (sondas auxiliares, si las necesitas, en una subcarpeta `probes/` de ese mismo directorio, declaradas). Si al llegar encuentras allí cualquier fichero distinto de `MANDATO.md`, no lo leas y decláralo en la primera línea.
- Fecha del sistema: 2026-09-05. Escribe en castellano.
- No has visto la conversación del autor y no debes buscarla.

## Objeto

- Repo (worktree, solo lectura): `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\mejoras-149-control-por-ubicacion`, HEAD `ff2ecd4` (compruébalo).
- Documento revisado: `docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md` (rev. 1).
- Código que el diseño describe y va a modificar: `core/config.py` (`INTAKE_CONTROL_FILES`, `INTAKE_CONTROL_PREFIXES`, `MERGE_EXCLUSIONS`), `core/inventory.py`, `core/intake_manual.py`, `core/intake_drive.py`, `core/intake_lotes.py`, `core/email_export.py`, `core/sala_maquina.py` (`_es_control`, `inventariar_cacheado`), `scripts/migrar_layout_intake.py`, `core/migrar_layout.py`, `core/crm_ficha_validacion.py`, `core/intake_manifest.py`, `core/apertura_v1_estado.py`, `core/ocurrencias_crm.py`, `core/sync.py`, `core/sync_sudespacho.py`, `core/whatsapp_intake.py`, `plugins/expedientes_xl/tiers.py`, y los tests `tests/test_apertura_v1_control_files.py`, `tests/test_intake_lotes.py`, `tests/test_inventory.py`, `tests/test_migrar_layout.py`. Historia: `docs/MEJORAS_FUTURAS.md` entrada 149 y el acta `docs/superpowers/specs/2026-09-04-apertura-w02jsvz-pipeline-r1-adversarial-review.md` (el CRÍTICO que motivó la reversión `4cd71dd`).

## Qué se te pida

Atacar el diseño. Cada afirmación que cite una función, un fichero o una ubicación la compruebas abriendo el código y anotas `fichero:línea`. Puedes ejecutar Python con `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe` desde el worktree con `CASOS_ROOT` en un directorio temporal fuera del repo; nunca contra `data/CASOS/`, `G:` ni `H:`.

Lentes, en orden de daño:

1. **Borrado o pérdida que el diseño permitiría.** El §3.4 es el único sitio con `unlink()`: ¿la regla «idénticos por sha256 → borrar; distintos → abortar en tiempo de plan» está bien colocada respecto a las dos fases del script actual? ¿Puede el plan decir «idénticos» y la fase 2 borrar algo distinto (carrera, cambio entre plan y ejecución)? ¿El rollback de la fase 1 sigue siendo completo con la regla nueva?
2. **El censo de ubicaciones (§3.1).** Para cada fichero del registro, comprueba en el código **dónde lo escribe de verdad** su escritor (raíz de `00_Input/`, raíz de una entrega, otra cosa). Busca escritores que el diseño no haya censado: `grep -rn "00_Input" core scripts` y cualquier `write_text`/`write_bytes`/`open(..., "w")` bajo `00_Input/`. ¿Hay algún fichero de protocolo a profundidad 3 o más (p. ej. dentro de `05_CRM/`, de un bundle partido de la sala de máquina, de `_organizado/`)? ¿Qué pasa con `01_Procesado/` —fuera de `00_Input/`— y con `_cobertura.json`?
3. **Los siete consumidores (§3.3).** Para cada uno, ¿la ruta relativa que el diseño supone es la que el código puede calcular en ese punto? Casos: `intake_drive` cuenta ficheros dentro de `01_Drive EV/` (¿tiene a mano `00_Input/`?); `intake_lotes.items_desde_disco` recibe `lote_dir` (¿y si el lote no es de primer nivel, o es un cajón legacy?); `sala_maquina._es_control` tiene llamadores con **nombre** (`tests/test_apertura_v1_control_files.py` lo llama con un basename) — ¿el cambio de firma rompe algo? ¿Qué otros llamadores de `_es_control` hay?
4. **Falsos negativos nuevos.** Con el contrato por ubicación, ¿qué fichero de protocolo que hoy se excluye pasaría a inventariarse? Piensa en `.pulled` escrito por `sync_sudespacho.pull_expediente` (¿a qué profundidad?), `.synced`, un `_manifiesto.yaml` de `split_documental` (la sala de máquina escribe manifiestos de bundles: ¿dónde, y son protocolo o documento?), lotes anidados, y `MANIFEST_CHECKOUT.json`/`AUDITLOG_MERGE_*` si vivieran bajo `00_Input/`.
5. **Falsos positivos nuevos.** ¿Puede un documento del cliente caer en profundidad 2 con uno de los tres nombres de entrega (`_manifiesto.yaml`, `.pulled`, `.synced`)? ¿Cómo llega un fichero de E&V a la raíz de `01_Drive EV/`?
6. **Compatibilidad.** ¿Qué tests hoy verdes cambian de resultado con el contrato nuevo? Enumera los que dependan del basename a cualquier profundidad. ¿`INTAKE_CONTROL_FILES` conservado como unión sigue siendo coherente con `MERGE_EXCLUSIONS` y con el guard `test_carveout_espeja_merge_exclusions`?
7. **Mutantes (§5).** ¿Cada uno mata el defecto y protege contra endurecer de más? ¿Cuáles pasarían hoy sin que el diseño lo declare como positivo? ¿Falta alguno para las lentes 1, 4 y 5?
8. **Enunciados más anchos que la función.** Señala cualquier frase del diseño que prometa más de lo que el código propuesto puede garantizar.

## Formato del informe

`INFORME.md`:
1. Primera línea: higiene del workdir.
2. Hallazgos `H-01`, `H-02`… por severidad (CRÍTICO / ALTO / MEDIO / BAJO): título, severidad, evidencia (`fichero:línea`, salida de la sonda), por qué importa, remedio breve.
3. Lo verificado y correcto, con evidencia.
4. Lo que no pudiste verificar y por qué.
5. Veredicto: `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE`, con una frase.

Al terminar, calcula el `sha256` del informe canonicalizado (UTF-8, `\r\n`→`\n`, sin saltos al borde, un único `\n` final) y devuelve en tu respuesta final SOLO: ruta, sha256, veredicto y recuento por severidad.

## 1. Informe recibido de Claude Code (sesión independiente), sin modificar

<!-- informe-literal:inicio:vzqk -->
Higiene del workdir: al llegar solo había `MANDATO.md`; no leí nada más. Sondas declaradas en `probes/` (`probe_contrato.py`, `probe_carrera_migracion.py`), ejecutadas con el venv del repo y `CASOS_ROOT` en un temporal fuera del repo. Repo en solo lectura; HEAD comprobado `ff2ecd4`, árbol limpio.

# Revisión adversarial R1 — diseño «Ficheros de protocolo: por dónde están, no por cómo se llaman» (rev. 1)

- Documento: `docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md`
- Worktree: `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\mejoras-149-control-por-ubicacion` @ `ff2ecd4`
- Fecha: 2026-09-05. Revisor: sesión independiente de Claude Code (no Codex), sin acceso a la conversación del autor.

Todas las rutas de código son relativas al worktree. «Hoy» = comportamiento en `ff2ecd4`; «nuevo» = lo que el diseño enuncia en §3.1/§3.2, implementado literalmente en `probes/probe_contrato.py`.

## 1. Hallazgos

### H-01 — ALTO — La regla «idénticos → borrar; distintos → abortar en tiempo de plan» no está donde se decide el borrado

**Evidencia.**
- `scripts/migrar_layout_intake.py:72-75`: el plan se calcula con `migrar_layout.plan_migracion(base)` y, si `dry_run`, se devuelve ahí. `core/migrar_layout.py:43-58`: `plan_migracion` no mira la raíz de `00_Input/` para nada; solo enumera cajones.
- `scripts/migrar_layout_intake.py:88-101`: la decisión «mover a la raíz» vs. «duplicado a borrar» se toma **en fase 1**, por `destino.exists()` en el momento del bucle, no en el plan.
- `scripts/migrar_layout_intake.py:122-123`: fase 2 hace `hijo.unlink()` sobre lo que la fase 1 encoló, sin releer nada.
- Sonda `probes/probe_carrera_migracion.py` sobre el código actual: raíz sin `_exported_ids.json` en el plan → un escritor concurrente (simulado en `shutil.move`, como haría `core/email_export.py:1073-1074`, que escribe el estado de canal en la raíz) crea `_exported_ids.json` con contenido distinto durante la fase 1 → salida:
  ```
  raiz            : b'{"cuenta": ["nuevo", "distinto"]}'
  anidado existe  : False
  RESULTADO: el anidado (contenido 'viejo') se BORRO en fase 2 sin compararse con la raiz
  ```
- Ni `migrar` ni `email_export` toman `core/casos/case_mutex` (grep sin resultados en los dos ficheros); la única puerta es `CasoPrestadoError` (`:67-71`), que no excluye dos procesos locales sobre un caso disponible.

**Por qué importa.** El §2 promete «nada de lo que esta pieza toca borra un fichero sin haber demostrado antes, por hash, que es idéntico a otro que se conserva» y el §3.4 sitúa la comprobación «en tiempo de plan». Con el código tal como está, una comparación solo en el plan deja tres ventanas: (a) el plan no ve raíz y no compara nada, la fase 1 sí la ve y encola; (b) el plan ve raíz idéntica, la raíz cambia antes del `unlink()` de la fase 2 (el `email_export` añade gmail_ids); (c) `dry_run=True` devuelve el plan sin pasar por ninguna comprobación si esta se pone después de `:74`. El diseño no dice qué hace la fase 1 cuando encuentra en la raíz algo que el plan no vio. Es estado de canal, no documental del cliente —por eso ALTO y no CRÍTICO—, pero es exactamente el único `unlink()` que la pieza dice blindar.

**Remedio.** Dos comprobaciones por hash, no una: (1) en el plan (para el `--dry-run` y para el mensaje al operador) y (2) **en el momento del `unlink()`**, releyendo sha256 de anidado y raíz; si difieren o la raíz ya no existe, **no borrar** y reportar (dejar el fichero en su cajón es seguro y no exige rollback). En fase 1, si `destino.exists()` y el plan no lo había visto → abortar antes de mover (la fase 1 ya es reversible). Añadir los dos mutantes (§H-11). El rollback de la fase 1 sigue siendo completo con la regla nueva: no introduce ninguna mutación nueva en fase 1 (verificado en `:82-118`).

### H-02 — ALTO — El registro deja fuera la ubicación legacy del estado de canal: `03_Email/_exported_ids.json` pasa de excluido a inventariado

**Evidencia.**
- §3.4 reconoce que `_exported_ids.json` y `_resolved_links.json` viven «directamente bajo `03_Email/` (profundidad 2)» en casos no migrados; `core/email_export.py:974-981, 1001, 1006-1007` los sigue leyendo de ahí como fallback vivo.
- §3.1 `INTAKE_CONTROL_ENTREGA = {"_manifiesto.yaml", ".pulled", ".synced"}` no incluye esos dos nombres; §3.2 «Cualquier otra profundidad: documento».
- Sonda: `03_Email/_exported_ids.json  hoy=True  nuevo=False  <-- CAMBIA`.
- La migración que los sacaría de ahí **no tiene ningún llamador automático**: `grep migrar_layout_intake|migrar\(` en `core/`, `scripts/`, `streamlit_app.py` solo devuelve el propio CLI (`scripts/migrar_layout_intake.py:66,159`). El docstring dice «se dispara SOLO cuando el caso recibe un intake nuevo», pero nadie la dispara.

**Por qué importa.** En todo caso no migrado, `core/sala_maquina.inventariar_cacheado` (`:1224-1249`, sin filtro de extensión) pasará a devolver `03_Email/_exported_ids.json` y `03_Email/_resolved_links.json` como documentos → filas `sin_soporte` en `_cobertura`. Es el síntoma exacto de `#149`, reintroducido en los casos viejos, en la red de calidad que la entrada quiere limpiar. `inventory.scan` (`core/inventory.py:97`) los manda a `skipped` por extensión, así que ahí solo es ruido menor.

**Remedio.** Declararlos por ubicación como lo que son: `("03_Email", nombre)` para los dos, o de forma general «`INTAKE_CONTROL_RAIZ` ∩ {estado de canal} también en la raíz del cajón legacy `03_Email/`». Es lo que §3.4 ya hace para la migración; el §3.2 tiene que decir lo mismo. Mutante: caso legacy con `03_Email/_exported_ids.json` → `inventariar` no lo devuelve; `03_Email/hilo/_exported_ids.json` sí.

### H-03 — ALTO — Hay más consumidores que los siete, y uno sigue clasificando por basename a cualquier profundidad sobre la misma carpeta

**Evidencia.**
- `scripts/abrir_caso.py:77-92` `hash_tree_local`: `rglob` sobre `01_Drive EV/` y `if p.name in intake_drive.CONTROL_FILES: continue` (`:88`). Es lo que alimenta `files` del evento forense `pull_drive_ev` (`:188-191, 203-205`).
- `scripts/abrir_caso.py:402-404`: recuento V1 de la etapa `drive`, mismo filtro por basename recursivo.
- `core/intake_drive.py:60-65`: el alias `CONTROL_FILES` existe **precisamente** para `abrir_caso.hash_tree_local` («la consumen otros módulos… para excluirlos del ledger forense»).
- Otros clasificadores propios sobre `00_Input/` que el diseño no menciona: `core/sync.py:73-76` (tupla propia `(".synced", "_inventory.json")`), `core/sync_sudespacho.py:1022-1023` (`p.name != _PULL_MARKER`), `scripts/migrate_05crm_buckets.py:64,137` (frozenset propio), `core/anon/api.py:517-520` (cualquier segmento que empiece por `_`, a cualquier profundidad), `core/local_organizer.py:399-402` (`_`/`.` inicial, no recursivo).
- §3.1: «**ningún** consumidor de `00_Input/` vuelve a clasificar con él». §1: «siete consumidores».

**Por qué importa.** Si `abrir_caso` no cambia, el ledger forense y el inventario de la sala de máquina discreparán sobre los mismos ficheros: T9 (`01_Drive EV/OFERTAS/.pulled` = documento) estará en `_cobertura` y no en el evento `pull_drive_ev`; un adjunto homónimo (`_inventory.json`) en una subcarpeta de E&V quedará fuera del hash-ledger. Y la frase «ningún consumidor» pasa a ser una afirmación falsa que un guard no ve, porque T7 mira escritores, no lectores. `core/anon/api.py:519` es otra capa (anonimización) y no hace falta tocarla, pero conviene decir en §3.5 que allí un adjunto `_ficha_crm.yaml` seguirá excluido por su `_` inicial, para que nadie lo dé por cubierto.

**Remedio.** Sumar `scripts/abrir_caso.py:88` y `:404` a la tabla del §3.3 (ambos tienen a mano la raíz: `prefijo`/`res.target_dir.parent`, `abrir_caso.py:200`), decidir el destino de los alias `intake_drive.CONTROL_FILES`, `inventory._CONTROL_FILES`, `intake_manual._CONTROL_FILES` (ver H-07) y listar en §3.5 los clasificadores por regla propia que **no** cambian, con su regla.

### H-04 — MEDIO — `INTAKE_CONTROL_ENTREGA` aplana «nombre en ubicación» a «nombre en cualquier carpeta de primer nivel»: falsos positivos nuevos

**Evidencia.**
- §3.1: la profundidad 2 admite cualquier carpeta de primer nivel («un lote, `01_Drive EV/`, `sudespacho_<id>/` o un cajón legacy»); la función del §3.2 no comprueba el nombre del directorio.
- `tests/test_inventory.py:51-53, 64, 77-78` fija como contrato que una carpeta de primer nivel **no reconocida** (`CarpetaRara/`) contiene documentos de fuente `manual` (`core/intake_lotes.fuente_de`, `:51`).
- Sonda: `CarpetaRara/_manifiesto.yaml  hoy=False  nuevo=True  <-- CAMBIA`; `CarpetaRara/.pulled  hoy=True  nuevo=True`.
- Cómo llega un fichero de E&V a la raíz de `01_Drive EV/`: `core/intake_drive.py:256-272` hace `rclone copy <remote>: <target_dir>` de la carpeta W-XXXXXX entera; cualquier fichero de la raíz de esa carpeta cae en `01_Drive EV/<nombre>`. Un `.synced` o `_manifiesto.yaml` ahí sería de E&V, y nadie escribe esos dos nombres en `01_Drive EV/` (`.synced` lo escribe `core/sync.py:82` en `drive/`; `_manifiesto.yaml` solo en lotes, `core/intake_lotes.py:148,178`).
- T8 declara como positivo `01_Drive EV/.synced`, una ubicación que ningún escritor usa, contradiciendo §3.2 («las dos únicas profundidades son las que los escritores usan de verdad»).

**Por qué importa.** Probabilidad baja, pero es la misma frontera que el diseño dice cerrar: el nombre sin su ubicación real. Además `drive/.synced` (`core/sync.py:36-37,82`) queda cubierto solo por accidente: `drive/` no es lote, espejo ni cajón legacy y el §3.1 no lo nombra.

**Remedio.** Registro por pares `(patrón de directorio, nombre)`: `_manifiesto.yaml` ↔ `PATRON_LOTE`; `.pulled` ↔ `01_Drive EV`, `sudespacho_*`; `.synced` ↔ `drive`. Y añadir `drive/` al censo del §3.1. Mutantes: `CarpetaRara/_manifiesto.yaml` documento; `01_Drive EV/_manifiesto.yaml` documento; `drive/.synced` protocolo.

### H-05 — MEDIO — El censo de escritores del propio repo está incompleto, y los temporales de dos escritores nombrados no están en `INTAKE_CONTROL_RAIZ_PREFIJOS`

**Evidencia** (todos escriben bajo `00_Input/`, ninguno está en el registro del §3.1):
- `core/intake_manifest.py:188`: `._intake_hashes.<pid>.tmp` en la raíz. `core/ocurrencias_crm.py:140`: `._ocurrencias_crm.json.<pid>.tmp` en la raíz. Los dos módulos aparecen en el comentario del §3.1 como escritores censados; sus temporales no. Prefijos declarados: solo `.apertura_v1.` y `._caso.`.
- `scripts/migrar_layout_intake.py:39-47`: `_intake_hashes.json.tmp` en la raíz (`with_suffix(".json.tmp")`), sin `fsync`.
- `scripts/migrate_05crm_buckets.py:272-275, 342-345`: `_caso.md.bak_<ts>`, `_intake_hashes.json.bak_<ts>`, `_migration_05crm_<ts>.json` en la raíz. Al retirar `startswith("_caso")` de `inventory.scan` (§3.3) el `.bak` del `_caso.md` deja de estar excluido por nombre (queda en `skipped` por extensión; en `sala_maquina.inventariar` ya entraba hoy).
- `core/local_organizer.py:126-127, 67-68, 682-689`: `01_Drive EV/_organizado/_audit.jsonl`, `_README.md` y **copias** de documentos (`:12`), a profundidad ≥3. Hoy y mañana entran en `sala_maquina.inventariar` como documentos (duplicados con distinto nombre).
- `core/email_export.py:1098-1099, 1362-1370, 1383-1387`: cuando `dest` no casa `PATRON_LOTE` (cajón legacy `03_Email/` o uso suelto) escribe `INDICE.md` y `CRONOLOGIA.md` **dentro de `dest`**, o sea bajo `00_Input/03_Email/`.
- `core/sync_sudespacho.py:605-607`: `_descarga_bruta.bin` dentro del destino del pull legacy si el zip es inválido.
- Sonda: las siete rutas anteriores dan `nuevo=False`.

**Por qué importa.** El §1 dice censar «los ficheros que el propio repo escribe en `00_Input/`» y el §3.2 que «las dos únicas profundidades son las que los escritores usan de verdad»; T10 argumenta que «un huérfano tampoco es documento». Con el registro propuesto, un huérfano de `IntakeManifest.save` o de `RegistroOcurrencias.save` es documento. Ninguno de estos es regresión respecto a hoy (hoy tampoco se excluyen), pero el diseño afirma completitud y T7 debería ponerse rojo con ellos.

**Remedio.** Añadir `._intake_hashes.`, `._ocurrencias_crm.` a los prefijos de raíz (y unificar el `_write_atomico` del script a `mkstemp` con prefijo `.` para no crear `_intake_hashes.json.tmp`). Decidir explícitamente `_organizado/**` (es un producto derivado del repo bajo `00_Input/`: o se declara protocolo por directorio, o se documenta que la sala de máquina lo inventaría a sabiendas) y el `write_indices` sobre cajón legacy. Los `.bak_`/`_migration_05crm_` son de un script puntual: basta anotarlos en §3.5.

### H-06 — MEDIO — T12 («los tests hoy verdes siguen verdes») es falso para al menos dos tests, y el diseño no los declara

**Evidencia** (los siete ficheros de test citados están verdes en `ff2ecd4`: 80 passed en la sonda de pytest).
- `tests/test_intake_lotes.py:104-113`: `2026-07-17_manual_01/_exported_ids.json` **debe quedar fuera** del albarán. Nuevo contrato: `_exported_ids.json` no está en `INTAKE_CONTROL_ENTREGA` → entra. Sonda: `hoy=True nuevo=False <-- CAMBIA`. El test se pone rojo.
- `tests/test_intake_manual.py:142-154`: `04_Manual/_inventory.json` debe quedar fuera de `list_files`. Nuevo: `_inventory.json` solo en la raíz → entra. Sonda: `<-- CAMBIA`. Rojo.
- `tests/test_abrir_caso_cli.py:234-245`: `01_Drive EV/_inventory.json` fuera de `hash_tree_local`. Rojo **si** se aplica H-03; verde-inconsistente si no.
- `tests/test_intake_lotes.py:28-35`: asserta identidad de los tres alias con `config.INTAKE_CONTROL_FILES`. El diseño no dice si los alias sobreviven (ver H-07).
- `tests/test_apertura_v1_control_files.py:32,54`: llama a `sm._es_control` con un **basename**. Con la firma nueva pasa por coincidencia (un basename es una ruta relativa de profundidad 1). No rompe, pero el test deja de comprobar lo que su docstring dice y el diseño lo lista como «ampliación», no como semántica cambiada.

**Por qué importa.** Los dos primeros no son ruido: codifican que hoy `_exported_ids.json`/`_inventory.json` se excluyen en cualquier lote/cajón. El diseño decide que eso estaba mal (ningún escritor los pone ahí) — correcto — pero entonces T12 debe decir «estos N tests cambian de expectativa y por qué», o el revisor del diff no podrá distinguir un rojo esperado de una regresión.

**Remedio.** Enumerar en §5 los tests que cambian, con la expectativa nueva. Comprobar la afirmación ejecutando la suite contra la implementación antes de escribirla en el plan.

### H-07 — MEDIO — `INTAKE_CONTROL_FILES` «conservado como unión» no espeja `MERGE_EXCLUSIONS` ni al plugin, y sin consumidores es una trampa

**Evidencia.**
- §3.1: «se conserva como la unión de nombres —lo espejan `MERGE_EXCLUSIONS`, el carve-out del plugin y `tests/test_apertura_v1_control_files.py`».
- `core/config.py:391-401` `MERGE_EXCLUSIONS` no contiene `_intake_hashes.json`, `_ficha_crm.yaml`, `_ocurrencias_crm.json`, `_inventory.json`, `_exported_ids.json`, `_resolved_links.json`, `.pulled`, `.synced`, `_manifiesto.yaml`. Es deliberado: `00_Input/_ocurrencias_crm.json` está en `GRUPOS_MERGE` (`config.py:436-444`), o sea **se sincroniza** en el checkin; M9 también viaja. El espejo real es solo `_apertura_v1.json`/`.apertura_v1.*.tmp` (`plugins/expedientes_xl/tiers.py:31-39`; guard `tests/test_expedientes_xl_tiers.py:28-31`, que compara `MERGE_EXCLUSIONS` con el plugin, no con `INTAKE_CONTROL_FILES`).
- `tests/test_apertura_v1_control_files.py:21-24` solo itera `est.FICHEROS_CONTROL` (= `_apertura_v1.json`), así que la unión puede crecer sin que ningún guard compruebe coherencia.
- Si «ningún consumidor» lo usa, los únicos lectores serán `scripts/abrir_caso.py:88,404` (vía alias, H-03) y `tests/test_intake_lotes.py:28-35`.

**Por qué importa.** Un lector futuro que crea la frase «lo espejan» puede intentar «arreglar» el espejo añadiendo `_intake_hashes.json` a `MERGE_EXCLUSIONS`: el checkin dejaría de subir M9 y `GRUPOS_MERGE` quedaría roto. Y un registro por basename que sobrevive «para los guards» es el mismo proxy que causó la reversión del 2026-09-04, con otro nombre.

**Remedio.** Reescribir la frase: el único espejo exigido por guard es `est.FICHEROS_CONTROL` ⊂ `MERGE_EXCLUSIONS` ∩ plugin. O bien retirar `INTAKE_CONTROL_FILES` y sus tres alias (cambiando `test_intake_lotes.py:28-35` y `test_apertura_v1_control_files.py:24` para que pregunten a `es_fichero_de_protocolo`), o bien dejarlo con un comentario que diga literalmente «no clasifica nada; solo lo lee el guard X» y hacer que un test lo compruebe (`git grep` de sus lectores).

### H-08 — MEDIO — `crm_ficha_validacion.es_fichero_de_control` no es «redundante pero inofensiva»: con §3.3 pasa a ser donde desaparece el adjunto homónimo

**Evidencia.**
- `core/crm_ficha_validacion.py:318-325`: clasifica por basename a cualquier profundidad (`rsplit("/", 1)[-1]`), lista `:44-49` con `_ficha_crm.yaml`, `_manifiesto.yaml`, etc. `tests/test_crm_ficha_validacion_r1.py:127` fija `sub/_caso.md` y `sub\_ficha_crm.yaml` como control.
- `:301-302`: una fila de `_cobertura` clasificada control se salta: ni `legibles` ni `ilegibles`.
- Tras §3.3, `<lote>/adjuntos/_ficha_crm.yaml` (T1) **sí** estará en `_cobertura` como documento. El validador lo saltará.

**Por qué importa.** Un documento real que el OCR no leyó y que no cuenta como ilegible convierte un `SIN_COMPROBAR` en `NO_ENCONTRADO` — la familia «no lo sé no es no hay» que la propia validación dice remediar (`:307-311`). El §3.5 la deja «como está» por estar en obra en otra sesión; puede dejarse, pero no calificarla de inofensiva ni omitirlo del §6 «No cubre».

**Remedio.** Anotar en §3.5 el efecto real y proponer que, cuando esa sesión toque el fichero, `es_fichero_de_control` delegue en `es_fichero_de_protocolo(rel)` (las filas de `_cobertura` traen `rel_path` relativo a `00_Input/`, `core/sala_maquina.py:1230,1249`), conservando por nombre solo los que no viven en `00_Input/` (`_cobertura.*`, `_sala_maquina_state.json`, `_registro.json`, `_tiempos.jsonl`).

### H-09 — BAJO — Afirmaciones del §3.3 que no casan con el código

- «`intake_manual` (`_listar`, `list_files`)»: no existe `_listar` en `core/intake_manual.py` (grep sin resultados). Los dos consumidores son `list_files` (`:308-338`) y `list_crm_branch_files` (`:286-305`). En este último la ruta es `05_CRM/<rama…>/<fichero>` con profundidad ≥3, así que con el contrato nuevo el filtro es un no-op — correcto, pero hay que decirlo.
- «`intake_drive.pull_drive_ev` … `01_Drive EV/OFERTAS/.algo` **no**»: `_count_files` (`core/intake_drive.py:861-867`) es **no recursivo**; nunca ve profundidad 3. El ejemplo es cierto para `inventory`/`sala_maquina`/`abrir_caso`, no para `intake_drive`.
- «`inventariar_cacheado` ya la calcula»: sí (`core/sala_maquina.py:1230`), pero **después** del `_es_control(p.name)` de `:1228`; hay que reordenar. Trivial, pero el plan del diff debe verlo.
- Otros llamadores de `_es_control`: solo `core/sala_maquina.py:1228` y `tests/test_apertura_v1_control_files.py:32,54` (grep). El cambio de firma no rompe nada más.

### H-10 — BAJO — Radio de daño del §4: la pieza no toca «el único `unlink()` del intake», toca el único `unlink()` de un fichero que no es temporal

`core/case_manager.py:1348-1350`, `core/intake_manifest.py:196-198`, `core/ocurrencias_crm.py:153-155`, `core/apertura_v1_estado.py:92-94` hacen `unlink` de temporales propios; `core/email_export.py:1108-1113` hace `rmdir`. La frase del §4 es más ancha que el código; la conclusión (dos rondas) sigue siendo correcta.

### H-11 — BAJO — Mutantes: T3 es circular, T7 no tiene mecanismo, faltan los de H-01/H-02/H-04/H-05

- **T3** «ninguna fila cuyo `rel_path` sea de protocolo»: si el oráculo es `es_fichero_de_protocolo`, el test aprueba cualquier registro, porque `inventariar` y el oráculo comparten la función bajo prueba (un registro vacío hace que ninguna fila «sea de protocolo» y T3 pasa con las dos filas de `#149` dentro). Fijar el conjunto **literal** esperado de `rel_path`.
- **T7** «cada literal que un módulo del repo escribe en `00_Input/`»: no hay forma de enumerar literales de escritura por reflexión; será una lista a mano, o sea el mismo registro comparado consigo mismo. Alternativa ejecutable: en un caso temporal, **ejecutar** cada escritor (`IntakeManifest.save`, `RegistroOcurrencias.save`, `apertura_v1_estado.abrir`, `intake_lotes.escribir_manifiesto`, `email_export._save_export_index`/`_save_resolved_links`, `intake_drive` marcador, `sync` marcador, `inventory.scan`, `case_manager._write_case_index`) y exigir `inventariar(case_dir) == []`; e inyectar un fallo entre `mkstemp` y `os.replace` para que el huérfano también dé `[]` (`tests/test_dedup_manifest.py:380` ya sabe buscar `._intake_hashes.*.tmp`).
- **Faltan:** (H-01) raíz ausente en el plan y distinta al llegar la fase 1 → aborta sin mover; idénticos en el plan y distinta justo antes del `unlink()` → no borra; `--dry-run` con distintos → mensaje, sin tocar disco. (H-02) caso legacy con `03_Email/_exported_ids.json` → fuera de `inventariar`. (H-04) `CarpetaRara/_manifiesto.yaml` → documento. (H-05) huérfano `._intake_hashes.4242.tmp` → protocolo. (Lente 5) documento en la **raíz** con `_` inicial, p. ej. `00_Input/_nota_suelta.pdf` (fuente `manual`, `core/intake_lotes.py:43-44`) → documento; mata al mutante «todo lo que empiece por `_` en la raíz es protocolo». (§3.2) ruta con `\` → misma respuesta que con `/`.
- **Pasan hoy sin declararse positivos:** T8 entero, T9 segundo caso, T11 (`_es_control` hoy no recibe rutas), T10 primera mitad. T9 primer caso (`01_Drive EV/OFERTAS/.pulled`) **cambia** hoy→nuevo y es la discrepancia con `abrir_caso` de H-03.

## 2. Lo verificado y correcto

- Tabla del §1, fila a fila, contra el código: `core/inventory.py:93-96` (`_CONTROL_FILES` + `startswith("_caso")` sobre `rglob`); `core/intake_manual.py:336-337`; `core/intake_drive.py:866`; `core/intake_lotes.py:197`; `core/email_export.py:1081-1083`; `core/sala_maquina.py:1178-1188` (`_IGNORAR` = registro ∪ `_intake_log.jsonl`, prefijos); `scripts/migrar_layout_intake.py:88-100, 122-123`. Exacto.
- Los cuatro no declarados y dónde los escribe el repo: `_intake_hashes.json` raíz (`core/intake_manifest.py:7,56`); `_manifiesto.yaml` raíz del lote (`core/intake_lotes.py:148,178`, vía `email_export.py:1094`, `whatsapp_intake.py:214`, `migrar_layout_intake.py:126`); `_ficha_crm.yaml` raíz (`scripts/crm_colaboradores_firmas.py:209` además de a mano); `_ocurrencias_crm.json` raíz (`core/ocurrencias_crm.py:44-45`). Exacto.
- Resto del registro de raíz: `_caso.md` (`core/case_manager.py:110`), `._caso.<pid>.tmp` (`:1343`), `_intake_log.jsonl` (`core/intake_log.py:172`), `_inventory.json` (`core/inventory.py:115`), `_exported_ids.json`/`_resolved_links.json` con caso (`core/email_export.py:1146-1156, 1171-1174`), `_apertura_v1.json` y `.apertura_v1.*.tmp` (`core/apertura_v1_estado.py:20,44,84`). Todos a profundidad 1.
- Entrega a profundidad 2: `01_Drive EV/.pulled` (`core/intake_drive.py:196-199,305`), `sudespacho_<id>/.pulled` (`core/sync_sudespacho.py:955,1015-1018`), `drive/.synced` (`core/sync.py:36-37,82`), `<lote>/_manifiesto.yaml`. El pull v2 no escribe marcador bajo `05_CRM/` (estado en `_caso.md`, `sync_sudespacho.py:1403`); el `05_CRM/.pulled` de `tests/test_inventory.py:44` es un fixture, no un escritor.
- Lente 4, sala de máquina: `_ZONAS_VETADAS = ("00_Input", …)` (`core/sala_maquina.py:421`); los manifiestos de bundle son `_segmentacion.json/.md` (`core/split_documental.py:266-267,301-320`) y van a la carpeta del bundle bajo `01_Procesado/`. No hay `_manifiesto.yaml` de `split_documental` bajo `00_Input/`. `_cobertura.json` vive en `01_Procesado/02_Sala de máquina/` (`scripts/migrar_layout_intake.py:138-139`), fuera del alcance de `inventariar`. `MANIFEST_CHECKOUT.json`/`AUDITLOG_MERGE_*` no están hoy en `INTAKE_CONTROL_FILES` (`config.py:566-574`): si vivieran bajo `00_Input/` el contrato nuevo no cambia nada respecto a hoy.
- §3.3 rutas calculables: `inventory.scan` tiene `input_dir` (`:83`); `intake_lotes.items_desde_disco` tiene `lote_dir.name` y es agnóstico de bandeja (el lote desviado a `_pendiente_checkin/<origen>/00_Input/<lote>/` conserva el nombre, `core/intake_lotes.py:96`, `case_manager.py:1001-1021`); `email_export` idem con `dest.name` (`:1010-1013`); `intake_drive` puede componer `f"{_DRIVE_EV_INPUT_SUBDIR}/{p.name}"` porque es no recursivo. `_mapping_documental` (`:57-63`) trabaja sobre claves `03_Email/<rel>` y puede aplicar la regla de ubicación como dice §3.4.
- §3.4 reglas 1-2: `plan_migracion` mete el homónimo anidado en `mapping` (`core/migrar_layout.py:52-56`) y hoy `_mapping_documental` lo saca por basename (`:63`); con la regla por ubicación T6 queda cubierto. El rollback de la fase 1 (`:106-118`) no incluye borrados y la regla nueva no añade mutaciones en fase 1 → sigue completo.
- `test_carveout_espeja_merge_exclusions` (`tests/test_expedientes_xl_tiers.py:28-31`) compara `MERGE_EXCLUSIONS` con el plugin; el diseño no toca ninguno de los dos → no cambia.
- `test_inventory.py` entero, `test_migrar_layout.py` entero y `test_apertura_v1_control_files.py` siguen verdes con el contrato del §3.2 (sonda: `05_CRM/.pulled`, `01_Drive EV/.synced`, `_caso.md`, `.apertura_v1.*.tmp` conservan el resultado).
- Presupuesto de rondas (§4): coherente con la regla del 2026-08-26 y con la corrección de la entrada `#149` de `MEJORAS_FUTURAS.md:6634-6635`.

## 3. Lo que no pude verificar y por qué

- Cuántos casos reales están en layout legacy (`03_Email/` sin migrar): exige leer `data/CASOS/` o `G:`, fuera de mandato. H-02 se sostiene en que el fallback legacy sigue vivo en el código y en que la migración no tiene disparador automático, no en un recuento.
- Que la R1 del 2026-09-04 (`…-r1-adversarial-review.md:170-181,222-249`) reprodujera el CRÍTICO tal como el acta lo describe: leí el acta, no re-ejecuté aquel diff (está revertido en `4cd71dd`).
- La implementación futura de `es_fichero_de_protocolo`: la sonda implementa el **enunciado** del §3.2 literalmente; un diff puede diferir (p. ej. tratar `03_Email/` aparte, lo que resolvería H-02). Los hallazgos son sobre el texto del diseño.
- La ruta exacta en disco de `MANIFEST_CHECKOUT.json`/`AUDITLOG_MERGE_*` (`repository_checkout.py:27` solo la nombra); irrelevante para el veredicto porque no cambian de trato.

## 4. Veredicto

**REQUIERE-REVISION.** La frontera es la correcta y el censo de raíz es exacto, pero el diseño sitúa la única comparación por hash en un momento (el plan) en que el código no decide el borrado (H-01, con sonda que reproduce la pérdida), deja fuera del registro la ubicación legacy del estado de canal reintroduciendo el síntoma de `#149` en los casos no migrados (H-02), afirma «ningún consumidor» mientras `scripts/abrir_caso.py` sigue clasificando por basename recursivo (H-03) y declara verdes tests que se pondrán rojos (H-06). Ninguno exige rehacer el diseño; todos exigen que la rev. 2 diga lo que el código hará.

**Recuento:** CRÍTICO 0 · ALTO 3 (H-01, H-02, H-03) · MEDIO 5 (H-04, H-05, H-06, H-07, H-08) · BAJO 3 (H-09, H-10, H-11).
<!-- informe-literal:fin:vzqk -->

## 2. Evidencia verificada por mí al adjudicar

Abrí la fuente en `ff2ecd4` para los seis hallazgos que cambian el diseño; los cinco restantes
los acepto sobre la evidencia del informe, que cita línea y, en dos casos, sonda.

| Hallazgo | Qué comprobé | Dónde |
|---|---|---|
| H-01 | el plan (`plan_migracion`) enumera cajones sin mirar la raíz; la fase 1 decide «mover» o «duplicado a borrar» por `destino.exists()`; la fase 2 hace `hijo.unlink()` sobre lo encolado, sin releer | `scripts/migrar_layout_intake.py`, bucle de la fase 1 y bloque «Fase 2» |
| H-02 | `email_export` calcula `legacy_cajon = estado_dir / "03_Email"` y fusiona desde ahí el índice de exportación y los enlaces resueltos cuando el caso no está migrado | `core/email_export.py`, bloque «Fallback legacy» de `export_label` |
| H-03 | `hash_tree_local` hace `rglob` y `if p.name in intake_drive.CONTROL_FILES: continue`; el recuento de la etapa `drive` repite el filtro | `scripts/abrir_caso.py` |
| H-04 | `test_inventory` crea `CarpetaRara/x.pdf` y exige que cuente como fuente `manual`; `core/sync._SOURCE_DIR = "drive"` es donde vive `.synced` | `tests/test_inventory.py`, `core/sync.py` |
| H-05 | `IntakeManifest.save` escribe `._intake_hashes.<pid>.tmp` y `RegistroOcurrencias.save` escribe `._ocurrencias_crm.json.<pid>.tmp`, ambos en la raíz | `core/intake_manifest.py`, `core/ocurrencias_crm.py` |
| H-06 | `test_manifiesto_round_trip_y_exclusiones` exige `<lote>/_exported_ids.json` y `<lote>/.pulled` fuera del albarán; `test_excluye_archivos_de_control` exige `04_Manual/.pulled`, `_inventory.json`, `.synced` fuera de `list_files` | `tests/test_intake_lotes.py`, `tests/test_intake_manual.py` |

Digest del informe recalculado al recibirlo: `9bccee50bcb4ea81fef72c5fa49ae65d8c57435d7c8d809fd35c3dfaed370f47`
(UTF-8, `LF`, un único salto final), igual al declarado por el revisor.

## 3. Mapa hallazgo → remedio (la adjudicación completa está en el §8 del diseño)

| # | Sev. | Veredicto | Dónde se remedia en la rev. 2 |
|---|---|---|---|
| H-01 | ALTO | confirmado | §2, §3.4 reglas 2-4; mutantes T5, T5b, T5c |
| H-02 | ALTO | confirmado | §3.1 pares `("03_Email", _exported_ids.json / _resolved_links.json)`; T8 |
| H-03 | ALTO | confirmado | §1 y §3.3 (nueve consumidores; alias retirados); T1, T9 |
| H-04 | MEDIO | confirmado | §3.1 pares (directorio, nombre); T9 |
| H-05 | MEDIO | confirmado | §3.1 `RAIZ_PREFIJOS`, `DIRECTORIOS`; §3.4; §3.5; T10, T12 |
| H-06 | MEDIO | confirmado | §5 «tests que cambian de expectativa» |
| H-07 | MEDIO | confirmado | §3.1 registro derivado que no clasifica; T14 |
| H-08 | MEDIO | confirmado | §3.3 última fila; T13 |
| H-09 | BAJO | confirmado | §1, §3.3 |
| H-10 | BAJO | confirmado | §4 |
| H-11 | BAJO | confirmado | §5 |

Recuento: 11 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar. Lo que el
revisor declaró **no verificado** (§3 de su informe) sigue sin verificar y está en el §7 del diseño.
