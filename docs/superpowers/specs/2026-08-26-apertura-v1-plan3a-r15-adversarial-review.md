---
tipo: revision-adversarial
objeto: "diff del Plan 3A (core/casos/{mutex_sesion,escritura}.py, case_manager, entrypoints, custodia)"
objeto_rev: "rama claude/feesdefender-mutex-wiring-0e3b64, ea61f81..fa552b9"
commit: fa552b9
ronda: "15"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k9vt
sha256_informe: bf0031b15078718ea8ad05fdb70da34c7f618db66fe691628c2cf453ca6e1589
adjudicado_en: docs/superpowers/plans/2026-08-26-apertura-v1-plan3-write-set.md §6
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R15.** El §1 conserva literalmente la voz del revisor; la
> adjudicación vive en el **§6 del plan**. Es la ronda del **diff** de 3A, y la única que le
> tocaba: R14 cubrió el diseño.
>
> Veredicto `NO-SHIP`: **10 hallazgos, 10 confirmados, 0 refutados** — 2 CRÍTICOS, 3 ALTOS,
> 4 MEDIOS, 1 BAJO.
>
> **Esta ronda EJECUTÓ, y ahí está su valor.** Contención real entre dos procesos, préstamo
> real entre dos hilos, una junction, un alias 8.3 de Windows, un proceso hijo matado a
> propósito entre `__enter__` y el registro, y 101 tests del diff. Los dos críticos no se
> deducen leyendo: se midieron.
>
> **Los dos críticos son la misma clase de defecto —falsa garantía de exclusión mutua— y los
> dos son reincidencias mías:**
>
> - **H15-01** es la **tercera** aparición de la propiedad que R14 nombró: R14 la cerró en la
>   costura (frontera C0) y yo remedié *ese sitio* en vez de la propiedad —«todo camino que
>   fije identidad comprueba concordancia»—. El alta es un camino que fija identidad.
> - **H15-02** es la **pérdida silenciosa de R11/H11-02 reaparecida en la capa que construí
>   encima de su arreglo**: cerrarla para el titular no la cierra para quien le pide prestado.
>
> **Dos intentos, y el primero no dio informe.** La corrida inicial ejecutó 196.799 tokens,
> corrió 369 tests y montó cuatro sondas, y el **filtro de contenido de la plataforma la cortó
> al redactar** —igual que R11—. Dos defectos de **mi mandato**, no suyos: le di un
> `--basetemp` que su entorno no puede crear (369 errores de setup) y le pedí «buscar vías de
> **escapar**» de un contenedor de rutas, que se lee como investigación de evasión. Reformulado
> con la misma sustancia, la segunda corrida entregó.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k9vt -->
# R15 — revisión adversarial del diff del Plan 3A (Codex, 2026-08-26)

Veredicto: NO-SHIP

sha256 de `DIFF.patch` al cerrar: `EE348B70D0314DB9BE566945FAC75CA4246FCE684DB0B97B3C99745740CB0168`

Comandos ejecutados:

- `Get-FileHash -Algorithm SHA256 ../r15-objeto/DIFF.patch` (al abrir y al cerrar) y `git apply --stat ../r15-objeto/DIFF.patch`.
- Inspección de fuente con `Get-Content`, `Select-String` y un barrido AST propio de las llamadas `replace`/`copy`/`copy2`/`dump`/`open` en los 11 productores del censo.
- `python.exe -m pytest tests/test_mutex_sesion.py -q -p no:randomly -p no:cacheprovider --basetemp=$env:TEMP/r15mutex` → 13 tests verdes.
- `python.exe -m pytest tests/test_mutex_sesion.py tests/test_escritura_costura.py tests/test_alta_v1.py tests/test_custodia_destino_efectivo.py tests/test_entrypoints_mutex.py tests/test_escritura_censo.py tests/test_abrir_caso_cli.py -q -p no:randomly -p no:cacheprovider --basetemp=$env:TEMP/r15target` → 101 tests verdes.
- `python.exe -m pytest -q -p no:randomly -p no:cacheprovider --basetemp=$env:TEMP/r15full` → colección interrumpida por cinco módulos que requieren `mcp.server.fastmcp`, no instalado.
- La misma suite con `--ignore` solo para esos cinco módulos MCP → llegó al 100%; dos tests adicionales de `test_expedientes_xl_wrapper.py` fallaron por la misma dependencia ausente. El resto no tuvo fallos; hubo skips y seis xfails declarados.
- Sondas ejecutables propias, siempre en este scratchpad y con `PYTHONDONTWRITEBYTECODE=1`: `probe_two_process_threads.py`, `probe_mutex_borrowers.py`, `probe_mutex_closing.py`, `probe_orphan_lease.py`, `probe_paths.py`, `probe_alta_identity.py`, `probe_custody_race.py` y `probe_censo_calls.py`.

Qué pude EJECUTAR y qué no:

- Ejecuté contención real entre dos procesos y préstamo real entre dos hilos. En el camino sano, tras salir el hilo adquirente y seguir dentro el prestatario, el segundo proceso recibió `CaseBusy`; al salir el prestatario pudo adquirir.
- Ejecuté pérdida del latido con dos prestatarios, expiración del lease y entrada de un segundo escritor; el primer prestatario terminó sin error. Es H15-02.
- Ejecuté las ventanas `cerrando` y `__exit__` fallido: la unión durante el cierre fue rechazada y el mapa quedó vacío.
- Ejecuté escapes por junction y equivalencia 8.3 en Windows, dos identidades simultáneas en el alta, aborto inyectado tras crear el esqueleto, divergencia de ciudad y carreras hash/stat.
- No ejecuté rclone ni Drive for Desktop reales, OCR/anon con `--runslow`, Ollama ni los servidores MCP. Las ramas que dependen de ellos quedan indicadas al final; no las doy por confirmadas por ejecución real.

## Hallazgos

### H15-01 — El alta V1 puede operar un caso existente bajo otro W-code y mantener dos lockfiles vivos — CRÍTICO

**Qué:** `ensure_case(modo="v1")` valida exclusivamente el `id_go` recibido y el mutex de ese valor antes de localizar el caso. Si el caso ya existe con otro `meta.id_go` —o su nombre presenta otro W-code— no compara identidades. Después, la rama de caso existente reescribe `meta.id_go` con el valor nuevo. Dos procesos pueden sostener simultáneamente los locks viejo y nuevo y operar el mismo directorio.

**Dónde:** `core/case_manager.py:289` y `core/case_manager.py:307` del árbol `head/`.

**Por qué es un defecto:** es exactamente la falsa garantía de exclusión que `IdentidadDiscordante` dice impedir. La afirmación «en v1 exige id_go explícito y mutex sostenido» es insuficiente y materialmente falsa para un caso existente: exige *un* mutex, no necesariamente el mutex canónico del expediente. También permite crear de cero una carpeta cuyo W-code presentado no coincide con el persistido.

**Cómo lo verifiqué:** `python.exe probe_alta_identity.py ../r15-objeto/head probe-alta-out3`. Salida relevante: `BEFORE_ID W-OLD01`, `DURING_ID W-NEW01`, `DIR_SAME True` y `TWO_LOCK_FILES ['W-NEW01.lock', 'W-OLD01.lock']` mientras ambas sesiones seguían dentro.

**Remedio que propondría:** separar una fase previa sin escrituras: localizar primero; si existe, leer y normalizar nombre, `meta.id_go` y argumento, exigir concordancia y comprobar el mutex de esa identidad exacta. La identidad de un caso existente no debe ser un campo actualizable por `ensure_case`. Para un caso nuevo, rechazar también cualquier W-code presentado por `case_id` que discrepe del `id_go` explícito antes de `mkdir`.

### H15-02 — La pérdida del latido solo se comunica al último prestatario; otro puede terminar «protegido» después de entrar un segundo escritor — CRÍTICO

**Qué:** cada contexto tiene su variable local `fallo`, pero solo el prestatario que lleva la cuenta a cero llama al gestor subyacente. Los prestatarios que salen antes no consultan `sesion.perdido()` ni revalidan; retornan normalmente aunque el hilo de latido haya muerto y el lease haya expirado.

**Dónde:** `core/casos/mutex_sesion.py:159` (especialmente 165-190) y `core/casos/case_mutex.py:600` del árbol `head/`.

**Por qué es un defecto:** un llamador puede completar sin excepción bajo una exclusión que ya no existe. La sonda dejó expirar el lease, adquirió un nonce nuevo mientras los dos prestatarios originales seguían dentro y luego dejó salir al primero: recibió éxito. Es una falsa garantía de exclusión mutua, no solo un mensaje pobre.

**Cómo lo verifiqué:** `python.exe probe_mutex_borrowers.py ../r15-objeto/head probe-mutex-out2`. Salida: `SECOND_WRITER_ENTERED True`, `A_AFTER_LOSS RETURNED_OK`, `B_STILL_INSIDE True`, `SAME_SESSION True`; solo al final `B_AFTER_LOSS MutexPerdido`.

**Remedio que propondría:** desacoplar «quién cierra el gestor» de «qué resultado recibe cada préstamo». Todo prestatario debe comprobar el estado compartido al salir: si su cuerpo iba limpio y la sesión está perdida, lanzar `MutexPerdido`; si ya llevaba una excepción, anotarle la pérdida. Solo el último debe seguir ejecutando `gestor.__exit__`. Añadir un test con dos prestatarios, fallo de `renovar`, expiración y adquisición desde otro proceso.

### H15-03 — La contención léxica de `Deposito` no contiene la escritura real y rechaza aliases legítimos — ALTO

**Qué:** `_resolver` acepta cualquier ruta cuya cadena normalizada quede bajo `_base`. Una junction situada bajo `_base` puede apuntar fuera y las escrituras la atraviesan. En la dirección recíproca, la forma 8.3 de la misma carpeta no normaliza igual: una ruta relativa que vuelve a la misma base mediante su alias corto se rechaza aunque `os.path.samefile` diga que son el mismo directorio.

**Dónde:** `core/casos/escritura.py:70`, `core/casos/escritura.py:90` y `core/casos/escritura.py:205` del árbol `head/`.

**Por qué es un defecto:** son falsas las dos propiedades pedidas: «lo escrito cae bajo la base» y «no se rechazan rutas legítimas». `normcase(abspath(...))` conoce texto, no reparse points, nombres 8.3 ni la identidad final que Windows abre.

**Cómo lo verifiqué:** `python.exe probe_paths.py ../r15-objeto/head probe-paths-out3`. Una junction `base/junction -> outside` fue aceptada y produjo `JUNCTION_OUTSIDE_EXISTS True`. Para la forma corta, la sonda obtuvo `SHORT_SAMEFILE True` y a continuación `SHORT_RESOLVE_ERROR ValueError`.

**Remedio que propondría:** no anunciar contención semántica con una prueba puramente léxica. En Windows, comprobar por handle los ancestros existentes y rechazar reparse points, o abrir/crear mediante handles con política equivalente a no-follow y validar `GetFinalPathNameByHandle`. Para rutas existentes, esa identidad por handle también resuelve aliases 8.3. Un `resolve()` previo aislado no basta por TOCTOU.

### H15-04 — El alta V1 deja un esqueleto parcial si falla después de `mkdir` — ALTO

**Qué:** las dos precondiciones nuevas sí van antes de tocar el caso, pero después se crea la raíz y varias subcarpetas sin rollback. Si `_ensure_crm_tree_dirs` o `_write_case_index` falla, la excepción sube y queda el rastro.

**Dónde:** `core/case_manager.py:312` a `core/case_manager.py:357` del árbol `head/`.

**Por qué es un defecto:** contradice literalmente la afirmación «no deja carpeta si aborta». A1/A2 solo prueban abortos anteriores a `mkdir`; no cubren un fallo de I/O durante la materialización.

**Cómo lo verifiqué:** en `probe_alta_identity.py` sustituí `_write_case_index` por un fallo `OSError` sobre un caso nuevo. Salida: `ABORT_ERROR fallo inyectado...`, `ABORT_DIR_EXISTS True` y quedaron `00_Input/05_CRM`, `01_Procesado` y `90_Notas personales`.

**Remedio que propondría:** para alta nueva, construir en un directorio staging hermano y publicar por rename solo al completar; ante fallo, retirar únicamente el staging creado por esa invocación. No aplicar limpieza recursiva al destino si preexistía. Añadir fallos inyectados después de cada paso materializador.

### H15-05 — Hash, tamaño y evento no describen necesariamente los mismos bytes — ALTO

**Qué:** `hash_tree_local` calcula el hash y cierra el fichero; después `_inventario_desde_hashes` hace un `stat()` independiente y `reconcile` compara el plan contra el mismo diccionario de hashes antiguo. Si el fichero cambia entre ambos pasos, el inventario mezcla hash viejo y tamaño nuevo, la reconciliación sigue dando `ok` y `plan.con_sha` publica el hash obsoleto. Si desaparece, sube un `FileNotFoundError` sin tratamiento.

**Dónde:** `scripts/abrir_caso.py:49`, `scripts/abrir_caso.py:72` y `scripts/abrir_caso.py:112` del árbol `head/`.

**Por qué es un defecto:** la cadena bytes→hash→evento no queda unida por el cambio de raíz efectiva. El destino es correcto, pero el evento puede afirmar el hash de bytes que ya no están allí; es un defecto de custodia real y los tests F1-F5 no mutan el fichero entre hash e inventario.

**Cómo lo verifiqué:** `python.exe probe_custody_race.py ../r15-objeto/head probe-custody-out`. Salida: `RECORDED_HASH_IS_OLD True`, `RECORDED_SIZE_IS_NEW True`, `CURRENT_HASH_MATCHES_RECORDED False`, `RECONCILIATION_OK_WITH_STALE_HASH True`; al borrar el fichero antes del inventario: `DISAPPEARANCE FileNotFoundError`.

**Remedio que propondría:** obtener hash y tamaño de una misma apertura estable (o de un snapshot), volver a hashear el destino para reconciliar en vez de reutilizar `hashes`, y validar que la identidad/metadata del fichero no cambió antes de emitir. Una desaparición o mutación debe producir un evento explícito de custodia fallida o un aborto limpio, nunca éxito con hash viejo.

### H15-06 — Un pull fallido puede dejar bytes parciales sin inventario ni evento — MEDIO

**Qué:** `pull_drive_ev` conserva los bytes parciales, escribe `.pulled` con el error y lanza `DriveIntakeError(result_obj)`. Por tanto `_intake_drive_ev` no recibe `res`, no usa `res.target_dir` y no ejecuta hash ni `_intake_generico`.

**Dónde:** `core/intake_drive.py:274` a `core/intake_drive.py:338` y `scripts/abrir_caso.py:143` a `scripts/abrir_caso.py:150` del árbol `head/`.

**Por qué es un defecto:** un `rclone` no cero puede haber copiado parte del árbol. Esos bytes quedan en el expediente o bandeja sin ningún evento que diga qué llegó y que la operación falló. La rama de error no viola la suposición sobre `target_dir.parent`: no llega a evaluarla; el defecto es que no se custodia nada.

**Cómo lo verifiqué:** contra la fuente: el resultado con `target_dir` se construye en 326-335 y se encapsula en la excepción en 337-338; el único llamador hashea después de un retorno normal. **SIN VERIFICAR con rclone real**: faltaron rclone/Drive y un error parcial reproducible.

**Remedio que propondría:** capturar `DriveIntakeError`, inventariar `exc.result.target_dir`, emitir un evento de pull fallido con hashes de parciales, retorno y condición de incompletitud, y volver a lanzar/terminar con error. No presentar ese inventario como intake exitoso.

### H15-07 — `ciudad` puede cambiar en metadatos sin mover el caso existente — MEDIO

**Qué:** si el caso ya existe, su ruta gana y `path_for_ciudad` no se consulta; sin embargo un kwarg `ciudad` distinto activa `_atomic_write_caso_md` y cambia el frontmatter. V1 devuelve la carpeta antigua con una ciudad nueva declarada.

**Dónde:** `core/case_manager.py:307` a `core/case_manager.py:311` y `core/case_manager.py:373` a `core/case_manager.py:394` del árbol `head/`.

**Por qué es un defecto:** el repositorio ya tiene `move_to_city` precisamente para mantener movimiento y metadato como una operación. La nueva ruta V1 hereda el cuerpo compartido y puede dejar esos dos planos en desacuerdo.

**Cómo lo verifiqué:** `probe_alta_identity.py` creó el caso en Barcelona y volvió a llamar a V1 con Madrid. Salida: `CITY_PHYSICAL_PARENT Barcelona` y `CITY_METADATA Madrid`.

**Remedio que propondría:** en `ensure_case`, tratar `ciudad` de un caso existente como comprobación, no como migración; rechazar la discrepancia con instrucción de usar `move_to_city`, o delegar explícitamente en esa operación con sus requisitos y rollback.

### H15-08 — `sala_maquina` no presenta `MutexPerdido` como error operativo — MEDIO

**Qué:** `_bajo_mutex` traduce únicamente `CaseBusy` a mensaje y salida 2. `MutexPerdido`, que aparece al salir tras un OCR largo, atraviesa el context manager sin captura. El usuario obtiene una excepción/traceback y salida genérica después de que el motor ya pudo escribir bytes parciales.

**Dónde:** `scripts/sala_maquina.py:485` a `scripts/sala_maquina.py:493` del árbol `head/`.

**Por qué es un defecto:** `MutexPerdido` es un `WorkspaceError` estructurado y esperado, no un error de programación. La interfaz no informa de manera accionable que la exclusión se perdió y que el resultado puede ser parcial.

**Cómo lo verifiqué:** trazado contra la fuente: el `except` es nominalmente `CaseBusy`; `case_mutex.tomado` lanza `MutexPerdido` al salir si la sesión está marcada como perdida (`core/casos/case_mutex.py:655`). La sonda de H15-02 confirma esa excepción en el último prestatario.

**Remedio que propondría:** capturar `MutexPerdido` por separado, emitir un mensaje sin rutas que declare resultado potencialmente parcial y salir con un código documentado. Además, los puntos de publicación irreversible deben revalidar antes de publicar; la captura de CLI por sí sola no restaura exclusión.

### H15-09 — La fixture global elimina de toda la suite la rama de fallback real del registro — MEDIO

**Qué:** el `autouse` fija `FEESDEFENDER_WORKSPACE_REGISTRY` en todos los tests. Los tests del registro inyectan raíz y los mundos contractuales vuelven a sobrescribir la variable, pero no hay ningún test que la elimine y pruebe el fallback `%LOCALAPPDATA%/FeesDefender/workspaces` dentro de un `LOCALAPPDATA` aislado.

**Dónde:** `tests/conftest.py:164` a `tests/conftest.py:180` del árbol `head/`.

**Por qué es un defecto:** la fixture no rompe un test que legítimamente deba usar el perfil real —ningún test debería hacerlo—, pero sí hace que una regresión de la rama «sin override» quede invisible. Eso importa porque el mutex usa `raiz_por_defecto()` cuando no se pasa raíz.

**Cómo lo verifiqué:** barrido de todos los usos de `FEESDEFENDER_WORKSPACE_REGISTRY`, `raiz_por_defecto`, `LOCALAPPDATA` y `workspaces` en `tests/*.py`; no hay `delenv("FEESDEFENDER_WORKSPACE_REGISTRY")` ni un aserto del fallback aislado. La suite ampliada ejecutó siempre con el autouse.

**Remedio que propondría:** conservar el aislamiento global y añadir un test que, dentro del propio `tmp_path`, haga `monkeypatch.delenv("FEESDEFENDER_WORKSPACE_REGISTRY")`, redirija `LOCALAPPDATA` a `tmp_path` y compruebe la ruta fallback exacta y las barreras de ubicación.

### H15-10 — Morir entre `__enter__` y el registro deja un lease vivo huérfano — BAJO

**Qué:** el lock nativo `.guard` se libera al morir el proceso, pero el JSON de lease ya publicado sigue vivo hasta caducar. La ventana concreta existe: `tomado().__enter__()` adquiere y arranca el latido antes de que `_Entrada` se construya y `_SESIONES[clave]` se asigne.

**Dónde:** `core/casos/mutex_sesion.py:153` a `core/casos/mutex_sesion.py:157` y `core/casos/case_mutex.py:429` a `core/casos/case_mutex.py:440` del árbol `head/`.

**Por qué es un defecto:** no rompe exclusión, pero contradice la lectura natural de la cabecera de `case_mutex.py:7-10` («un lock nativo se suelta solo cuando el proceso muere»): el caso sigue dando `CaseBusy` durante hasta 300 s por defecto aunque no quede titular. Es defecto de disponibilidad/documentación, no CRÍTICO.

**Cómo lo verifiqué:** `python.exe probe_orphan_lease.py parent ../r15-objeto/head probe-orphan-out probe-orphan.signal`. Maté el hijo después de entrar y antes de registrar. Salida: `LEASE_FILE_AFTER_DEATH True`, `IMMEDIATE_ACQUIRE CaseBusy`, `AFTER_EXPIRY_ACQUIRE True` con lease de 2 s.

**Remedio que propondría:** documentar expresamente el periodo de falsa ocupación tras crash. Si se exige recuperación inmediata, mantener además un lock nativo de titularidad durante toda la sesión y usar su liberación por muerte para distinguir un lease huérfano, sin decidir por PID.

## Comprobaciones que no produjeron hallazgo

- La reentrancia sana sí conserva el lock hasta el último prestatario: la sonda de dos hilos + segundo proceso dio `EXTERNAL_DURING_B CaseBusy`, `CHILD_EXIT 0`, `EXTERNAL_AFTER_B ACQUIRED`.
- La transición a `cerrando=True` ocurre bajo `_CANDADO`; durante el `__exit__` fuera del candado una unión recibe `MutexPerdido`. Si `__exit__` lanza, el `finally` anidado elimina la entrada. La sonda dio `JOIN_WHILE_CLOSING MutexPerdido` y `MAP_EMPTY_AFTER_EXIT_FAILURE True`.
- M7, M8 y M8b sincronizan correctamente el camino que dicen medir: B está dentro antes de que A salga, y M8 comprueba el lock antes de dejar salir B. No pueden pasar si se vuelve a cerrar con el adquirente. Su hueco es distinto: no cubren la pérdida compartida de H15-02.
- El `raise typer.Exit(0)` del `dry_run` está dentro del `with`; el protocolo de context manager ejecuta el `finally` y libera. No encontré una rama que lo evite.
- Dentro de `deposito()`, todas las ramas que llegan a `guard_escritura` han resuelto antes el estado del mutex; las ramas inválidas abortan antes del guard. El defecto de H15-03 es de contención efectiva, no del orden mutex→guard.
- `SUBDIRS_ALTA_V1` sí es subconjunto por construcción (`tuple(s for s in CASO_SUBDIRS if ...)`) y la rama V1 no crea la subestructura ni plantillas diferidas en el camino feliz.
- En producción, tanto el retorno normal como `skipped=True` de `pull_drive_ev` conservan el `target_dir` calculado como `.../00_Input/01_Drive EV`; por tanto `target_dir.parent` es correcto en esas dos ramas. La rama de error no retorna y queda en H15-06.
- Detector corregido del trinquete: el AST archivado cuenta 93; clasifiqué las 18 llamadas `replace` de los 11 productores. Once son falsas (`str.replace`, `datetime.replace`, `dataclasses.replace`) y siete son escrituras (`os.replace` o `Path.replace`), dando 82. La regla «receptor `os`/`shutil`; para `Path.replace`, un posicional y cero keywords» no tiene contraejemplos en esos productores. No prueba tipos en Python en general —un objeto propio podría tener `replace(x)`—, pero aquí cada llamada de un argumento se deriva como `Path` y cada `str.replace` tiene dos argumentos. Tampoco encontré aliases de `os`/`shutil` que la regla pierda.

## Lo que NO pude verificar

- No reproduje H15-06 con rclone/Drive reales; la falta de custodia de la rama de excepción está verificada contra el flujo de fuente, y la existencia de parciales depende del fallo concreto de rclone.
- No ejecuté los cinco módulos MCP ni los dos wrappers que dependen de `mcp.server.fastmcp`, porque ese submódulo no está instalado en el intérprete indicado.
- No ejecuté los tests `--runslow`, el fixture SaRS1 con PII, Ollama ni los tests que requieren la blocklist privada. Los skips reales quedaron visibles en la salida de suite.
- No validé la política de contención sobre todos los tipos de reparse point de Windows (symlink, mount point y dispositivos); ejecuté una junction y un alias 8.3, suficientes para refutar las dos propiedades generales.
<!-- informe-literal:fin:k9vt -->

## 2. Evidencia verificada por el adjudicador

- **Cadena del acta:** `marcador_nonce: k9vt`, un par de marcadores en orden, el nonce no
  aparece dentro del informe, y `sha256_informe` recomputado **coincide**.
- **No-mutación del objeto:** `sha256` de `DIFF.patch` antes y después,
  `ee348b70d0314db9be566945fac75ca4246fce684db0b97b3c99745740cb0168` en los dos casos, y el
  revisor reporta el mismo valor.
- **H15-01, verificado por mí antes de aceptarlo**, con un caso cuyo `meta.id_go` era
  `W-OLD01`: el alta en `v1` aceptó `id_go=W-NEW01`, **reescribió el metadato a W-NEW01** y
  devolvió el mismo directorio. Confirmado sin margen.
- **H15-02, verificado por lectura y por mutación:** un prestatario que no es el último no
  consultaba `sesion.perdido()` al salir. El mutante que restaura ese comportamiento mata
  `test_m11` y `test_m11b`, y ninguno más.
- **H15-08 estaba ya arreglado** antes de leer el informe: lo encontré contestando yo mismo
  las preguntas del mandato (commit `e19bf5b`). Coincidimos, y lo digo para que no cuente como
  hallazgo que yo no habría visto.
- **Lo que ya sabía del punto 6 y le dije en el mandato:** el censo de 93 estaba inflado. Lo
  encontré mirando el **desglose por primitiva** en vez del total —el detector contaba
  `str.replace` y `dataclasses.replace`— y el real era 82. El revisor **reprodujo la
  clasificación** (once falsas, siete escrituras) y confirmó que la regla corregida no tiene
  contraejemplos en esos productores. Esa parte del informe valida un arreglo mío, no lo
  descubre.
- **Lo que NO acepté como remediable en esta ronda, y por qué**, en el §6.3 del plan: H15-04,
  H15-05, H15-07 y H15-10 quedan **declarados** (dos de ellos preexistentes al diff), y de
  H15-03 se cierra la mitad realista y se declara el TOCTOU.
