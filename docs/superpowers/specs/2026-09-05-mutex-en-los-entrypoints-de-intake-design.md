---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "MEJORAS #126 — tres entrypoints de intake escriben en el expediente sin pedir el mutex del caso"
rev: "2"
---

# El mutex del caso lo pide quien escribe, no quien lo recuerda

> **Rev. 2 (2026-09-05), tras la R1 adversarial de Codex sobre la rev. 1: `REQUIERE-REVISION`,
> nueve hallazgos, los nueve confirmados.** Lo que cambia: el bloque del export empieza **antes de
> reservar el lote** (H-01, la reserva es un `mkdir` y en caso prestado escribe además la traza);
> el alta por `pull`/`intake_judicial` de un caso que aún no existe se **declara sin identidad y
> sin mutex**, con su vía canónica (`abrir_caso`) y su deuda (H-02); el helper **resuelve la
> referencia** (`resolve_ref`) antes de leer `_caso.md` (H-03); `--src/--out` **no significa «sin
> caso»**: si el destino cae bajo un caso del catálogo se sostiene su mutex (H-04); hay política
> explícita para `MutexPerdido`, sin prometer cancelación instantánea (H-05); el guard E4 se
> reparte entre adquirentes reales y delegantes (H-06); las fronteras de test observan la reserva,
> el alta y el sello con instantáneas por hash y directorios (H-07); E13 lleva su *bootstrap* y su
> barrera (H-08); y la tabla del §1 se corrige con los escritores reales (H-09). Adjudicación en
> el **§7**; voz del revisor, literal, en el acta hermana `…-r1-adversarial-review.md`.
>
> **Rev. 1 (2026-09-05).** Fila #17 de `PLAN.md`, promovida de `MEJORAS #126` por disparador real
> (apertura de W-02X1WJ, 2026-09-01). Alcance **recortado a tres** de los cuatro entrypoints que la
> entrada nombra: `scripts/crm_ficha.py` es de la sesión hermana «Completar fichas de
> colaboradores» (reparto de Nikolai del 2026-09-05) y queda fuera con nombre. Radio de daño:
> **decide quién puede escribir sobre el árbol del caso → dos rondas** (`CLAUDE.md` §«Cuántas
> rondas»): esta sobre el diseño, otra sobre el diff.

## 1. El problema, medido

El mutex de sesión existe, tiene cuatro rondas de revisión y 17 mutantes, y lo piden **tres**
entrypoints: `scripts/abrir_caso.py`, `scripts/sala_maquina.py` y, desde el PR #290,
`scripts/migrar_layout_intake.py`. Todo lo demás que escribe en el árbol del caso entra sin
llamar. Tabla **corregida en la rev. 2** con los escritores reales (R1/H-09; fuentes en el acta):

| Entrypoint | Escribe en | Por qué duele |
|---|---|---|
| `scripts/export_label_emails.py` | **antes del motor:** la reserva del lote `00_Input/<AAAA-MM-DD>_email_<NN>/` (`email_dest_dir` → `reservar_lote` → `mkdir`; en caso prestado, además `_intake_log.jsonl` por el desvío a bandeja); **el motor:** los `.eml` y adjuntos del lote, `_manifiesto.yaml` del lote, `_intake_hashes.json`, `_exported_ids.json`, `_resolved_links.json`, `_intake_log.jsonl`, y `01_Procesado/Emails/INDICE.md` y `CRONOLOGIA.md` | escribe en `00_Input` mientras `sala_maquina apply` lo lee durante una hora de OCR: el escenario de `[APER-39]`, ~1h40 de OCR repetido más huérfanos (medido). Y la ventana de H-01 de `#149`: puede cambiar `_exported_ids.json` mientras la migración compara |
| `scripts/atomize_emails.py` | `01_Procesado/Emails/` entero (registro `_registro.json`, mensajes, adjuntos, corpus, revisiones, vistas; **poda** con `unlink`) y, con `--entrega`, `_entregas/<…>/_SELLO.md`. **No** emite `_intake_log.jsonl`: eso lo hace `scripts/sala_maquina.py` cuando encadena la atomización | la atomización corre sobre el mismo `00_Input` que el OCR está inventariando, y `--src/--out` permite hacerlo sobre el árbol de un caso sin nombrarlo |
| `scripts/sync_sudespacho.py pull` / `intake_judicial` | `ensure_case` (modo `libre`: el esqueleto del caso fuera de `00_Input`, y puede copiar/prerrellenar plantillas en `02_Analisis`), `register_expediente` (`_caso.md`), y `pull_expediente_v2`: `00_Input/05_CRM/<rama>/`, `00_Input/_ocurrencias_crm.json` (**antes** de descargar), `_intake_hashes.json`, `_intake_log.jsonl`, con desvío a bandeja si el caso está prestado | `[APER-37]` manda ejecutar `pull` **justo antes** del `apply` |
| `scripts/sync_sudespacho.py sync_all` | lo mismo que `pull`, por cada expediente de **cada caso** del catálogo | barre también el caso que otra sesión tiene tomado |

En W-02X1WJ la regla la sostuvo a mano quien ejecutaba: retuvo el export y la atomización tres
veces mientras corría el OCR. Cuando retuvo el pull de `--fuente drive_ev`, el mutex lo habría
bloqueado igual con `CaseBusy`: la disciplina manual solo era *load-bearing* en los caminos que no
lo tienen.

**Lo que esta pieza cierra del residuo de la R2 de `#149` (H-01), y lo que no:** cierra el lado
**CLI** (`export_label_emails` y `sync_sudespacho` pasan a sostener el mutex, así que la migración
deja de estar sola). **No** cierra la UI: `streamlit_app.py` reserva el lote y llama a
`export_label` directamente, y llama a `intake_demanda_contestacion`, sin mutex. Se declara en el
§5 y no se atribuye a esta pieza un cierre global.

## 2. La frontera

**Todo entrypoint que escriba bajo el árbol de un caso con W-code sostiene el mutex de ese caso
desde ANTES de la primera escritura hasta la última, y aborta limpio (código 2, cero bytes) si
otro proceso lo tiene.** Sin W-code no hay namespace: se avisa y se sigue (trinquete E2 de
`tests/test_entrypoints_mutex.py`).

**Lo que el mutex NO da, dicho aquí (R1/H-05):** exclusión, no cancelación. `case_mutex` no
preempta código Python a mitad: si el lease se pierde durante una escritura, el motor la termina y
la pérdida se conoce al **salir** del bloque. Sostener el contexto garantiza que no entran dos
escritores con lease válido; no garantiza rollback.

Lo que NO cambia: `core/casos/case_mutex.py` y `core/casos/mutex_sesion.py` no se tocan. `core/`
sigue **exigiendo** y nunca adquiriendo (guard E5). El helper nuevo usa `mutex_sesion.sostenido`,
nunca la primitiva (el guard del censo prohíbe `tomado`/`adquirir` fuera de sus capas).

## 3. Diseño

### 3.1. Un solo sitio para adquirir desde un CLI: `scripts/_mutex_cli.py`

Hoy hay tres copias casi iguales de «sostener el mutex desde un entrypoint». Se extrae a un
módulo de `scripts/` (no de `core/`, por E5); se importa como `from scripts._mutex_cli import …`
(un guion bajo inicial es un nombre válido de módulo; lo que no vale es `import _mutex_cli` como
módulo de nivel superior).

```python
# scripts/_mutex_cli.py
class CasoOcupado(RuntimeError): ...        # otro proceso tiene el caso: abort ANTES de escribir
class MutexPerdidoEnCli(RuntimeError): ...  # el lease se perdió DURANTE: puede haber trabajo a medias

def w_code_de(ref_o_case_id: str) -> str | None:
    """`meta.id_go` del `_caso.md` del caso al que resuelve `ref_o_case_id`.
    PRIMERO `resolve_ref` (R1/H-03: un W-code pasado como `--ref` no es un nombre de carpeta y
    `caso_path` no lo encuentra), DESPUÉS `_caso.md`. None si el caso no existe o no declara
    `id_go`. Nunca deriva la identidad del nombre de la carpeta."""

def w_code_de_ruta(ruta: Path) -> str | None:
    """Para `--src/--out` (R1/H-04): si `ruta` cae bajo un caso del catálogo (existe
    `<caso>/00_Input/_caso.md` en algún ancestro dentro de `CASOS_ROOT`), su `meta.id_go`;
    si no, None. Un destino dentro de un caso es una escritura en ese caso aunque el CLI no lo
    nombre."""

@contextlib.contextmanager
def sostener(w_code: str | None, *, avisar: Callable[[str], None], que: str):
    """Sostiene el mutex de `w_code` durante el bloque.
    - `w_code is None` → `avisar(texto canónico + qué se está haciendo)` y `yield None`.
    - `CaseBusy` → `CasoOcupado` con el mensaje de la primitiva (quién, desde cuándo).
    - `MutexPerdido` al salir → `MutexPerdidoEnCli` con el aviso de qué artefactos revisar,
      que los pone el llamador en `que` (`«el lote de correo recién escrito»`, `«01_Procesado/
      Emails»`, `«00_Input/05_CRM»`): no se copia el texto de `sala_maquina`, que apunta a
      `_cobertura.md`, un fichero que estos motores no generan (R1/H-05).
    - `ahora_fn=now_iso_utc` SIEMPRE (E4 por AST).
    """
```

`migrar_layout_intake` pasa a usarlo (retira su `_bajo_mutex` y `_w_code_de`). `sala_maquina`
**no cambia**: ya tiene el `CaseWorkspace` resuelto. `abrir_caso` no cambia: tiene la identidad
resuelta antes que nadie y su bloque lleva cuatro rondas.

### 3.2. Los cinco subcomandos, y dónde empieza el bloque

| Subcomando | Identidad | El bloque empieza… | …y termina |
|---|---|---|---|
| `export_label_emails.main` | `w_code_de(args.ref)` tras el parseo | **antes de `email_dest_dir`** (R1/H-01: la reserva es la primera escritura; en caso prestado además la traza del desvío) | tras `export_label` y el informe |
| `atomize_emails --ref` | `w_code_de(args.ref)` | antes de `P.atomize_case` | tras `sellar_entrega` (si `--entrega`); la salida temprana `publicado=False` sigue sin sellar |
| `atomize_emails --src/--out` | `w_code_de_ruta(Path(args.out))` (R1/H-04): si la salida cae bajo un caso, su mutex; si no, aviso «destino fuera de todo caso: no hay mutex que sostener» y sigue | antes de `P.atomize_dir` | tras el sello |
| `sync_sudespacho pull` / `intake_judicial` | `w_code_de(case)` **antes de `ensure_case`**. Si el caso **no existe** → es un alta: `None`, aviso «este pull crea el caso: sin identidad no hay mutex; la vía canónica de alta es `abrir_caso`, que sí lo sostiene» y sigue (R1/H-02, trinquete E2, y se declara como deuda en `MEJORAS #126`). Si existe y declara `id_go` → mutex | antes de `ensure_case` | tras `_siguiente_paso` |
| `sync_sudespacho sync_all` | `w_code_de(case_id)` por caso | antes del **primer** `pull_expediente_v2` del caso (envuelve todos sus expedientes) | al terminar el caso |

**Códigos de salida:** `CasoOcupado` → **2** en los cuatro subcomandos de un caso (cero bytes: el
bloque empieza antes de la primera escritura). `MutexPerdidoEnCli` → **2** con el mensaje de qué
revisar; el trabajo hecho **no se deshace** (§2). En `sync_all`: `CasoOcupado` **salta el caso** y
lo resume (`bloqueados_por_mutex`, en memoria y en la salida, sin escritura nueva de protocolo:
el censo de escrituras se queda en 88); `MutexPerdidoEnCli` **anota el caso, sigue con los demás**
—una pérdida afecta a un caso, no al barrido— y el código de salida final es 2 si hubo alguna.

`ensure_case` en modo `libre` (el de `pull`) **no exige ni se une** al mutex; con el CLI
sosteniéndolo antes, simplemente corre dentro. En modo `v1` exige identidad explícita y mutex
vigente (E3); ese modo lo usa `abrir_caso`, no estos CLI.

### 3.3. Lo que no se toca, con nombre

- `scripts/crm_ficha.py`: de la sesión hermana. Queda en `MEJORAS #126` como cuarto entrypoint
  pendiente: «se cierra cuando la hermana cierre la acción 8».
- `core/`: exige, no adquiere (E5). Ningún cambio en motores.
- `streamlit_app.py`: reserva y exporta correo, y lanza el intake judicial, **sin mutex**. Fuera de
  esta pieza y **declarado** en `MEJORAS #126` como segunda deuda con nombre; hasta entonces la
  exclusión respecto de la UI sigue siendo la disciplina del operador.
- El alta de un caso por `pull`/`intake_judicial` (§3.2): sin identidad, sin mutex, declarado.

## 4. Mutantes y tests (`tests/test_entrypoints_mutex.py`, fronteras E7-E14)

**Instrumentos** (R1/H-07): `_instantanea` pasa a registrar **nombres de fichero y directorio y
hash de contenido**, no solo tamaños; y los espías del motor comprueban
`mutex_sesion.vigente(CaseRef(w_code=W)) is not None` **en cada punto de escritura** de la fila
(reserva, alta/registro, motor, sello), no solo en el motor.

| # | Test | Qué debe pasar |
|---|---|---|
| E7 | caso tomado por otro proceso; `export_label_emails.main([...])` con `reservar_lote` **y** `export_label` espiados | código 2, **ninguno** de los dos llamado, instantánea (con directorios) igual |
| E8 | ídem `atomize_emails.main(["--ref", W])` con `atomize_case` y `sellar_entrega` espiados; la carpeta del caso se llama **distinto** del W-code (R1/H-03) | código 2, ninguno llamado |
| E9 | ídem `pull --case <cid> --expediente 1` (Typer: `pull`) con `ensure_case`, `register_expediente` y `pull_expediente_v2` espiados, sobre un caso **existente** con `id_go` | código 2, ninguno llamado, instantánea igual |
| E9b | ídem `intake-judicial` | ídem (R1/H-07: frontera propia, no cubierta por E9) |
| E9c | `pull --case <nuevo>` sobre un caso que **no existe** | aviso «este pull crea el caso… sin mutex», exit 0, el caso se crea (la excepción declarada) |
| E10 | `sync-all` con dos casos de dos expedientes cada uno, uno de los casos tomado | el tomado se salta y se resume; el otro sincroniza sus dos expedientes bajo **una** sesión; exit 0 |
| E11 | `atomize_emails --src <caso>/00_Input/03_Email --out <caso>/01_Procesado/Emails` con el caso tomado | código 2 y nada escrito (R1/H-04); con `--out` fuera de todo caso → aviso y sigue |
| E12 | cada subcomando sostiene el mutex **durante** cada escritura: los espías comprueban la sesión vigente en la reserva, en el alta/registro, en el motor y en el sello; y `None` al terminar (éxito, ocupado y excepción del motor) | frontera «durante toda la escritura», no «antes» |
| E4 (repartido, R1/H-06) | E4a: `ahora_fn=now_iso_utc` por AST en los **adquirentes reales** (`abrir_caso`, `sala_maquina`, `_mutex_cli`); E4b: los **delegantes** (`export_label_emails`, `atomize_emails`, `sync_sudespacho`, `migrar_layout_intake`) llaman a `sostener` por AST | un mutante `now_iso` en el helper muere en E4a; quitar el `with` de un delegante muere en E4b |
| E13 | **dos procesos reales** (`subprocess`, `sys.executable`, argumentos como lista, UTF-8) lanzan `atomize_emails --ref W` sobre el mismo caso. Cada hijo arranca por un *bootstrap* de test (`tests/_bootstrap_e13.py`) que fija `CASOS_ROOT` y la raíz de locks **antes** de importar `core`, parchea el motor por uno que escribe `READY` y **espera un fichero `SUELTA`** (barrera, sin dormir), y llama a `main`. El padre espera `READY` del primero, lanza el segundo, espera su salida (debe ser 2 con «ocupado»), escribe `SUELTA`, espera al primero (0). Timeouts y limpieza en `finally` (R1/H-08) | exactamente uno termina 0 y el otro 2; el perdedor no escribe un byte |
| E14 | `MutexPerdidoEnCli`: se inyecta `marcar_perdido` en la sesión durante el motor | exit 2, mensaje que nombra los artefactos del motor y no `_cobertura.md`; en `sync_all`, el caso se anota y el barrido sigue |

**Mutantes, uno por subcomando y uno por frontera:** retirar el `with` en cada uno de los cinco
(E7-E11 en rojo, y E4b); adquirir DESPUÉS de `email_dest_dir` (E7 en rojo por la reserva);
adquirir después de `ensure_case` en `pull` (E9 en rojo por bytes escritos); `w_code_de` sin
`resolve_ref` (E8 en rojo); `w_code_de_ruta` siempre `None` (E11 en rojo); tratar `CasoOcupado` en
`sync_all` como abort del barrido (E10 en rojo); `now_iso` en el helper (E4a en rojo); mensaje de
pérdida con `_cobertura.md` (E14 en rojo).

## 5. Alcance explícito

- **Toca:** `scripts/_mutex_cli.py` (nuevo), `scripts/export_label_emails.py`,
  `scripts/atomize_emails.py`, `scripts/sync_sudespacho.py`, `scripts/migrar_layout_intake.py`
  (usa el helper), `tests/test_entrypoints_mutex.py` (+ `tests/_bootstrap_e13.py`),
  `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (`[APER-37]`/`[APER-39]`), `MEJORAS #126`, `PLAN.md`
  fila #17.
- **No toca:** `core/casos/*`, `core/` en general (E5), `scripts/crm_ficha.py` (hermana),
  `scripts/sala_maquina.py`, `scripts/abrir_caso.py`, `streamlit_app.py`.
- **No cubre, declarado:** la UI (§3.3); el alta por `pull`/`intake_judicial` de un caso nuevo
  (§3.2); la exclusión entre máquinas (el mutex es por máquina; el canon vive en Drive y su lock
  es el del checkout); cancelación o rollback ante pérdida del lease (§2).

## 6. Lo que esta rev. no sabe

Cuántas veces un `sync_all` o un export desde la UI se han cruzado con un `apply`: no está medido.
Y si el *bootstrap* de E13 aguanta en la máquina de CI (no hay CI de pytest hoy: corre en el PC).

## 7. Adjudicación de la revisión adversarial (Codex, 2026-09-05) — REQUIERE-REVISION, remediado

- **Objeto revisado:** este documento, rev. 1, commit `7e3a0f4`
- **Ronda:** 1 (diseño) — la primera de dos, por radio de daño
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-05-mutex-en-los-entrypoints-de-intake-r1-adversarial-review.md`
- **Hallazgos:** 9 — 3 ALTOS, 6 MEDIOS; **9 confirmados, 0 refutados**
- **Remediado en:** rev. 2 de este documento

**Independencia: plena** — revisor Codex (`gpt-6-astra`), adjudicador Claude Code. Cada hallazgo
se contrastó contra la fuente (líneas en el §2 del acta); dos de ellos (H-01 y H-02) los había
medido yo antes de recibir el informe, leyendo `email_dest_dir` y `ensure_case`.

| # | Sev. | Hallazgo (frontera, no ejemplo) | Veredicto | Dónde se remedia |
|---|---|---|---|---|
| H-01 | ALTO | `email_dest_dir` reserva el lote (`mkdir`, y traza si desvía) **antes** de `export_label`: el bloque «alrededor de `export_label`» llegaba tarde | ✅ confirmado (`core/intake_lotes.py:96`, `case_manager.py:1234`) | §3.2: el bloque empieza antes de la reserva; E7 espía la reserva; instantánea con directorios |
| H-02 | MEDIO | `pull --case` puede **crear** el caso: no hay `_caso.md` del que leer el W-code; `ensure_case` en modo `libre` ni exige ni se une; el nombre no es identidad | ✅ confirmado (`case_manager.py:479,528-545`) | §3.2: alta sin identidad → aviso y sigue, **declarado** como deuda con su vía canónica (`abrir_caso`); E9c |
| H-03 | ALTO | El helper heredado busca por `caso_path(case_id)`; un `--ref W-…` no es nombre de carpeta y devolvía `None` → «avisa y sigue» y el motor escribe | ✅ confirmado (`migrar_layout_intake.py:161`, `case_locator.py:43`) | §3.1: `w_code_de` hace `resolve_ref` primero; E8 con carpeta ≠ W |
| H-04 | ALTO | `--src/--out` NO es «sin caso»: el destino documentado es `<caso>/01_Procesado/Emails` y el motor asume el layout del caso; reproducido: escribe y sella con el caso ocupado | ✅ confirmado (`pipeline.py:110,130,165,220,272`; `entregas.py:46`) | §3.1 `w_code_de_ruta`; §3.2 fila `--src/--out`; E11 |
| H-05 | MEDIO | `MutexPerdidoEnCli` sin política de ejecución ni de barrido; el texto copiado de `sala_maquina` apunta a `_cobertura.md`; el mutex no cancela a mitad | ✅ confirmado (`case_mutex.py:505,610,655`) | §2 «exclusión, no cancelación»; §3.1 `que=`; §3.2 códigos de salida y política de `sync_all`; E14 |
| H-06 | MEDIO | Ampliar el `parametrize` de E4 hace rojo a los delegantes correctos: E4 solo mira llamadas a `sostenido` | ✅ confirmado (`test_entrypoints_mutex.py:168-176`) | §4: E4a adquirentes reales, E4b delegantes por AST |
| H-07 | MEDIO | Los espías propuestos no cubrían reserva, alta/registro ni sello; `_instantanea` solo mide tamaños; falta `intake_judicial` ocupado | ✅ confirmado (`test_entrypoints_mutex.py:55`) | §4: instrumentos con hash y directorios; E9b; E12 en cada punto de escritura |
| H-08 | MEDIO | E13 con «variable de entorno» y «dos segundos» no inyecta nada en un intérprete nuevo de Windows y es flaky | ✅ confirmado | §4 E13: *bootstrap* por fichero, barrera `READY`/`SUELTA`, timeouts, `finally` |
| H-09 | MEDIO | La tabla del §1 omitía escritores (`_resolved_links.json`, manifiesto del lote, índices de `01_Procesado/Emails`, `_ocurrencias_crm.json`, el esqueleto de `ensure_case`) y atribuía a `atomize_emails` una traza que emite `sala_maquina` | ✅ confirmado (`email_export.py:1075-1099,1372-1418`; `sync_sudespacho.py:1505`; `sala_maquina.py:43`) | §1 reescrito; §1 último párrafo acota el cierre respecto a la UI |

**Lo que el revisor verificó y resultó correcto:** los 17 tests de E1-E6 y del censo pasan y el
censo mide 88; `resolve_ref` solo lee; un mutex externo protege `ensure_case` en modo `libre` sin
autobloqueo; `list_cases`/`caso_path` sirven para el barrido; `CaseBusy` no deja entrada en el
mapa de sesiones; `scripts/_mutex_cli.py` no rompe E5; el `--help` de Typer expone `pull`,
`intake-judicial`, `sync-all`; la contención real entre dos procesos es viable en Windows con un
arnés externo. **Lo que no pudo verificar:** nada del helper, que no existe aún; la R2 sobre el
diff es donde se verifica.
