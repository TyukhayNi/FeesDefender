---
estado: consumido
creado: 2026-07-30
origen: sesión que construyó las Tasks 0-3 del PR-A
destino: sesión de la Task 4
consumido_por: PR-A de la Fase 0 — `tests/test_repository_cli_checkin.py` (Task 4)
---

# Handoff — Fase 0, Task 4: caracterización de `cmd_checkin`

**Andamio efímero, ya consumido.** La Task 4 se escribió en
`tests/test_repository_cli_checkin.py` (PR-A); cuando el PR-B cierre la Fase 0 este
fichero pasa a `estado: historico`. El hogar autoritativo del estado del ítem es `PLAN.md`,
bloque `[SIGUIENTE-DUAL-WORKSPACE]`; el hogar del plan es
`docs/superpowers/plans/2026-07-29-dual-workspace-fase0-banco-pruebas.md` (**rev. 4**).

## Qué hay que hacer, en una frase

Escribir `tests/test_repository_cli_checkin.py` con los **13 escenarios** que la Task 4
del plan enumera, **con el frontal sin tocar**, y cerrar el PR-A.

## Punto de partida exacto

- **Rama:** `claude/fase0-pr-a-red-de-seguridad`, empujada a `origin`, **sin PR abierto**.
- **Commits ya hechos (no rehacerlos):** `2a15d40` Task 0 barrera + Task 1A `Entorno` ·
  `c9725f0` Task 2 doble + fixtures + migración de los 16 · `2e7e8b8` Task 3
  caracterización de `cmd_checkout`.
- **Suite:** 2616 / 0 failures / 0 errors / 77 skipped. **La base de la rama es 2562**,
  no los 2555 que cita el plan: `aaf7dc1` (PR #164) añadió 7 tests desde `fec3444`. Al
  cuadrar el delta, medir la base con un censo, no fiarse del número citado.
- **La rama va por detrás de `origin/main`** (que se mueve con las otras sesiones):
  **rebase antes del PR**, y volver a correr la suite después del rebase.
- **Venv:** `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe` (el worktree no
  tiene `.venv` ni hereda `.env`).

## Por qué esta tarea se dejó aparte y no es un olvido

`cmd_checkin` es el **doble de largo** que `cmd_checkout` (≈229 líneas frente a 130) y es
el camino que decide **pérdida de datos**: propaga borrados con `moveto` al `--backup-dir`,
veta grupos indivisibles, integra la bandeja y clasifica el semáforo. En la sesión que
construyó las Tasks 0-3, **las cuatro veces que predije comportamiento en vez de medirlo
me equivoqué**. Escribir 13 tests sobre este camino sin margen para verificar cada aserto
produce precisamente los asertos vacuos que ya hubo que corregir dos veces.

**Regla de oro de esta tarea: leer `cmd_checkin` entero ANTES de escribir el primer
aserto.** Está en `scripts/repository_cli.py`, desde `def cmd_checkin` hasta
`def _tmp_dir`.

## Lo que ya está construido y hay que reutilizar, no reinventar

| Pieza | Dónde | Para qué sirve aquí |
|---|---|---|
| `FakeDrive` / `FakeRclone` | `tests/_dobles/fake_drive.py` | Drive en memoria + doble de rclone fijado a v1.73.5 |
| **`resultados={(sub, n): (rc, out, err)}`** | ídem | Guionizar un fallo concreto **sin mutar el Drive**. Es el canal que hace falta para el `check` en amarillo y el `moveto` fallido; los `fallos_sub` heredados aplanan todo a `rc=3` |
| `armar(n_objetivo, callback)` | ídem | Hook one-shot; dispara **después** de los efectos y del resultado de la operación `n` |
| `EjecutorActor(fake, "A")` | ídem | Etiquetar actores para asertar la secuencia causal en `traza_actores` |
| `drive.bytes_snapshot()` | ídem | Exigir que unos bytes sobrevivan **idénticos** (el log crudo) |
| `drive.snapshot()` | ídem | Death snapshot: probar que una operación NO tocó el Drive |
| `assert_operandos_sinteticos` | `tests/_barrera.py` | Ya lo invoca el doble; no hay que llamarlo a mano |
| `REMOTO_SINTETICO` | `tests/_barrera.py` | **Fuente única** del remote. No redefinir `REMOTO` |
| Helpers de montaje | `tests/test_repository_cli_checkout.py` | `caso_md`, `meta_de`, la fixture `cli`, `args_checkout`. Copiar el patrón (el plan pide **helpers locales**, no un módulo compartido) |
| `montar_checkin(tmp_path, drive)` | `tests/test_repository_cli_guard_pull.py` | Ya monta un árbol local de checkin con su `MANIFEST_CHECKOUT.json`. Mirarlo antes de escribir otro |

## Los 13 escenarios, literal del plan (Task 4)

1. ruta local inexistente → **2 con cero comandos**;
2. inventario inválido → 1;
3. `--dry-run` escribe el DELTA en el `work_dir` **inyectado** y no toca nada;
4. borrados sin `--yes` → **3**;
5. el `copy` y el `check` usan la **misma** lista `--files-from`;
6. `PRESERVE_DRIVE` no se sube;
7. conflicto escribe estado y **no libera**;
8. veto de grupo **no libera**;
9. `copy` fallido **no propaga borrados**;
10. camino verde libera con `ultimo_checkin_*`;
11. la bandeja se integra y se vacía;
12. colisión → `_reingesta_*` (anotar que `MEJORAS #101` dice que nadie lo reconcilia);
13. **el listado ilegible de la bandeja no libera el lock** — era el 8º defecto y lo cerró
    el PR #160, así que aquí es **caracterización verde**, no `xfail`.

Más un **smoke test** con `build_parser().parse_args([...])`, para que el entrypoint
público no quede fuera.

## Cinco reglas que no son negociables en esta tarea

1. **El frontal no se toca.** La inyección es por `monkeypatch` de `run_rclone`,
   `_tmp_dir`, `_SYNC_LAG_S`, `_nonce` y `_usuario_por_defecto`, como en la Task 3 y como
   hacen los 16 de #156/#160. Enhebrar el `Entorno` es la **Task 1B**, que es de PR-B.
2. **El orden del camino verde se fija DENTRO del test del camino verde**, como tramo de
   su traza marcado `# contrato temporal (A-2)`. No como test suelto: así la Fase 2 tiene
   un único sitio que actualizar cuando cambie el orden.
3. **Es caracterización, no especificación.** Si un escenario falla, **es un bug vivo que
   no conocíamos: para y repórtalo.** No se arregla nada en la Fase 0.
4. **Nunca asertar sobre una subcadena que el nombre del test pueda inyectar en la salida
   capturada.** `tmp_path` lleva el nombre del test y el frontal imprime rutas: en #160 un
   `assert "evidencia" in salida` pasó en verde sin que el mensaje existiera. Frases con
   espacios.
5. **Ningún aserto vacuo.** Un `assert x is y or callable(x)` pasa siempre por la última
   rama. Ya cayeron dos así en la Task 1A. Si un aserto no puede fallar, no es un aserto.

## Trampas medidas que te ahorran tiempo

- **El camino feliz del checkout hace OCHO operaciones rclone, no siete.** En el primer
  checkout de un caso el `_intake_log.jsonl` no existe → el pull del log da rc 3 →
  `_append_evento_drive` sonda con un `lsjson` (`_remoto_existe`) para distinguir
  «ausente» de «ilegible». Espera lo mismo en el checkin: **cuenta las operaciones
  midiendo, no prediciendo.**
- **`moveto` de origen ausente da rc 1; `copyto` da 3.** El doble los distingue; los
  `fallos_sub` heredados no. Para el escenario 9 usa `resultados`.
- **`rmdirs` sobre árbol no vacío da 0 y no borra nada**, y su retorno es uno de los dos
  que el frontal no examina.
- **`FakeDrive` no modela directorios.** No se puede asertar «quedan directorios vacíos»;
  se asierta retorno descartado + comando emitido + lock liberado.
- **`FakeDrive` guarda la REFERENCIA al `dict` del test**, no una copia — es requisito de
  paridad con los 16. Puedes asertar sobre tu variable `drive` directamente.
- **Los nombres de los campos del lock se leen en `core/repository_checkout.py`**, no se
  adivinan: es `checkout_timestamp`, no `checkout_ts` (ya me costó un fallo).
- **El conteo de la suite no se lee del resumen de pytest** (las tuberías lo comen en
  Windows): `--junit-xml` y leer el XML.
- **No usar el árbol de trabajo como banco de pruebas.** Nada de `git stash` con trabajo
  sin commitear: en la sesión anterior se llevó dos tareas enteras. Commit del incremento
  verificado primero.

## Criterio de cierre del PR-A

1. los **dos** `cmd_*` caracterizados con el frontal sin tocar;
2. la barrera es comprobable **también con `run_rclone` doblado**;
3. suite completa verde, con el delta cuadrado contra la base medida de la rama;
4. rebase sobre `origin/main` y `leak-scan` verde;
5. `PLAN.md` **no** se marca todavía: la Fase 0 se cierra cuando entre **PR-B** (Tasks 1B,
   5, 6, 7).
