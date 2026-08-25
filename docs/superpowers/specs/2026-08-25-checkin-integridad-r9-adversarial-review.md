---
tipo: revision-adversarial
objeto: "diff de MEJORAS #96 y #93-B/A-2c contra origin/main"
objeto_rev: "1"
commit: 60e5b2d
ronda: "9"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: v4tk
sha256_informe: 8e4f653825dcaf2a553f267363a680015cc9cb01fce39d4d4170b208cd449bd0
adjudicado_en: docs/superpowers/plans/2026-08-25-checkin-integridad-96-93b.md §2
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R9.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el **§2 del plan**, no aquí. El acta existe porque yo soy la parte
> revisada: sin el original archivado nadie puede contrastar **qué dijo el revisor** con
> **qué decidí yo que dijo**.
>
> **Lo que encontró, en una frase.** Dos vías de escritura sobre el canon de un caso
> prestado —que es justo lo que este subsistema existe para impedir—, y **una de las dos la
> había introducido el propio arreglo**.
>
> **Limitación declarada por el revisor, y que no se maquilla:** no pudo ejecutar ni un
> test (`ModuleNotFoundError: dotenv` en la copia externa). Sus ocho hallazgos son análisis
> de fuente, y él los marca como SIN VERIFICAR en ejecución. Las corridas que sostienen la
> remediación son del adjudicador.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:v4tk -->
# R9 — revisión adversarial de #96 y #93-B/A-2c

**Veredicto:** NO-SHIP
**Hallazgos:** 8 (2 críticos, 1 alto, 5 medios, 0 bajos)
**Qué pude ejecutar:** Resolví y comprobé las rutas de `base`, `head` y `CAMBIOS.diff`; inventarié los hunks del diff; recorrí con PowerShell (`Get-Content`, `Get-ChildItem`, `Select-String`) las definiciones y llamadas de `MANIFEST_CHECKOUT.json`, `MERGE_EXCLUSIONS`, `cmd_checkout`, `cmd_checkin`, `_integrar_bandeja`, `_pull_caso_md`, `_push_caso_md`, `guard_escritura`, `plan_merge`, la máquina de estados y los tests afectados. `rg` no está instalado (`The term 'rg' is not recognized`), por lo que usé `Select-String`. Comprobé el arnés disponible: `Python 3.14.7` y `pytest 9.1.1`. Intenté la suite dirigida con bytecode y caché desactivados y `--basetemp` dentro del scratch:

```text
python -m pytest tests/test_guard_copia_prestada.py tests/test_checkin_reentrante.py \
  tests/test_repository_cli_fallos.py::test_estado_ausente_sale_con_4_y_NO_registra_el_evento \
  tests/test_repository_cli_checkin.py::test_camino_verde_libera_el_lock_con_ultimo_checkin \
  -q -p no:cacheprovider --basetemp <scratch>

ERROR collecting tests/test_guard_copia_prestada.py
core/config.py:14: in <module>
    from dotenv import load_dotenv
E   ModuleNotFoundError: No module named 'dotenv'
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!
```

**Qué NO pude verificar, y por qué:** No se ejecutó ningún test: la colección abortó por la dependencia ausente `python-dotenv`; conforme al mandato, no instalé ni simulé el entorno. Tampoco ejecuté rclone ni escribí en un Drive real. Las reproducciones dinámicas propuestas en H9-01 a H9-04 y H9-06 a H9-08 quedan **SIN VERIFICAR en ejecución**; las cadenas de control y de datos descritas sí están comprobadas contra el fuente de `head` y, donde corresponde, contra `base`.

## Hallazgos

### H9-01 — El manifiesto que identifica «copia local» se sube deliberadamente al canon y apaga allí el guard [CRÍTICO]
**Dónde:** `scripts/repository_cli.py:621-631` (`cmd_checkout`); `core/config.py:391-399` (`MERGE_EXCLUSIONS`); `core/case_manager.py:726-744` (`es_copia_prestada`) y `:777-784` (`guard_escritura`); `tests/test_repository_cli_checkout.py:210-221`.

**Qué está mal:** El discriminante no distingue local de canon. `cmd_checkout` crea `local/MANIFEST_CHECKOUT.json` y acto seguido hace `copyto` al destino remoto `MANIFEST_CHECKOUT.json` en la raíz del caso (`repository_cli.py:628-631`). El propio test de checkout exige que esa clave exista en el `drive` sintético (`test_repository_cli_checkout.py:221`). `es_copia_prestada`, en cambio, solo pregunta si existe un fichero con ese nombre en la raíz resuelta; no valida contenido, procedencia, nonce ni tipo de workspace. Si existe, `guard_escritura` retorna antes de leer `estado_repositorio` y permite la escritura. El checkin no retira el manifiesto remoto: `MERGE_EXCLUSIONS` lo saca del inventario/merge genérico, pero una exclusión no es una eliminación. Por tanto, tras un checkout normal el canon conserva exactamente la marca que el arreglo interpreta como «esto no es el canon». El bypass alcanza tanto `prestado` como `conflicto`.

**Por qué importa:** La guarda cuyo único propósito es impedir escrituras directas sobre el canon durante un préstamo queda desactivada en el camino normal que crea ese préstamo. Intake, pipeline o UI pueden escribir en el árbol canónico en vez de `_pendiente_checkin`, abriendo divergencia y posibles sobrescrituras durante el merge. Es una vía de escritura sobre el canon de un caso prestado.

**Cómo se comprueba:** Montar un caso bajo `CASOS_ROOT` con `00_Input/_caso.md` en `prestado` y un `MANIFEST_CHECKOUT.json` de raíz —estado que produce `cmd_checkout` y que ya fija `test_el_manifest_se_genera_en_local_y_se_sube`—; llamar `guard_escritura(case_id, "00_Input/nuevo.pdf", "intake")`. El contrato exige `desviar=True`; el código de `head` toma `case_manager.py:777-781` y devuelve `desviar=False`. Repetir con estado `conflicto`. Reproducción dinámica: **SIN VERIFICAR** por el fallo de colección indicado arriba.

### H9-02 — El checkin «reentrante» puede subir trabajo nuevo sin lock y luego devolver 0 diciendo «nada que hacer» [CRÍTICO]
**Dónde:** `scripts/repository_cli.py:675-773` (inventario, plan, copia y verificación), `:818-850` (evidencia antes de CP10-bis), `:995-1014` (`_sin_ciclo_que_cerrar`); `core/repository_checkout.py:491-494` (fichero nuevo local → `COPY_LOCAL`); `tests/test_checkin_reentrante.py:66-99`.

**Qué está mal:** La reentrancia no se comprueba al entrar. Antes de leer el estado del Drive, `cmd_checkin` inventaría, planifica, ejecuta `rclone copy`, propaga movimientos, verifica y sube la evidencia de CP9. Solo en `repository_cli.py:838` relee `_caso.md` y descubre que el caso ya estaba `disponible` con `ultimo_checkin_timestamp`; entonces retorna 0. Si, después del primer checkin, queda o se añade en la copia local un fichero que no estaba ni en el baseline ni en Drive, `plan_merge` lo clasifica expresamente como `COPY_LOCAL` (caso 7). El segundo checkin lo sube al canon sin que exista un ciclo prestado, y después devuelve 0 con el mensaje «Nada que hacer». Incluso con local inalterado CP9 puede hacer `copyto` de evidencia antes del retorno.

**Por qué importa:** Convierte una copia ya cerrada en una vía autorizada de hecho para mutar el canon sin lock. El 0 permite que automatización u operador confundan «se detectó antes y no se tocó nada» con «se escribió y luego se decidió llamarlo no-op»; además contradice el propio aviso que manda abrir otro checkout para trabajo nuevo.

**Cómo se comprueba:** Ejecutar un primer checkin verde; sin nuevo checkout, crear en el mismo local `00_Input/post_cierre.pdf`; ejecutar de nuevo. Capturar inventario remoto, comandos y retorno. El comportamiento seguro es cero mutaciones y salida no exitosa o un no-op previo a CP1; el flujo actual planifica `COPY_LOCAL`, ejecuta `copy`/`check`/subida de evidencia, deja `post_cierre.pdf` en Drive y retorna 0 sin un segundo `case_checkin`. El test actual no monta trabajo posterior al cierre y solo busca ausencia del subcomando `check`, no ausencia de escrituras. Reproducción dinámica: **SIN VERIFICAR** por el fallo de colección.

### H9-03 — CP11 sobrescribe una instantánea obsoleta de `_caso.md` tras una ventana nueva de varias operaciones remotas [ALTO]
**Dónde:** `scripts/repository_cli.py:838-850` (pull y validación), `:852-882` (evento e integración), `:884-896` (mutación y push del `fm` antiguo); `core/case_manager.py:340-354` y `:1191-1281` (escritores de metadatos canónicos); en `base`, el pull de CP11 ocurría después del evento y de la bandeja (`scripts/repository_cli.py`, símbolo `cmd_checkin`, CP11).

**Qué está mal:** CP10-bis descarga un dict ordinario `fm` y CP11 vuelve a subir ese mismo snapshot sin relectura, compare-and-swap ni comprobación de nonce/versión. Entre ambos puntos se hacen como mínimo el pull/push del log y el `lsjson` de la bandeja, y puede haber varios `moveto` y `rmdirs`. `_append_evento_drive` no modifica `_caso.md`; `_integrar_bandeja` tampoco lo hace en el caso normal porque un `_caso.md` de bandeja colisionaría con el canónico y terminaría como `_reingesta__caso.md`. Eso no impide que otro escritor actualice el canónico durante la ventana: el repo contiene escritores sin versionado como `ensure_case` y `update_pull_state`, y la propia arquitectura admite actividad concurrente sobre el caso prestado. El push final reconstruye el fichero desde el snapshot anterior y borra silenciosamente cualquier metadato o cambio de lock intermedio. Antes del diff, la relectura estaba después del evento y la bandeja; el cambio amplía materialmente la ventana obsoleta.

**Por qué importa:** Puede perder frontmatter canónico —vínculos CRM, pull state, ciudad u otros metadatos— o pisar una transición concurrente de lock, sin conflicto ni rastro. No es solo una carrera ya existente entre pull y push: el diff adelanta el pull por varias operaciones de red potencialmente largas.

**Cómo se comprueba:** En `FakeRclone`, armar un hook posterior al `copyto` que hace el pull de CP10-bis y anterior al `copyto` final del lock; el hook añade `meta.sentinel_concurrente = "conservar"` (o cambia nonce/estado) en `drive["00_Input/_caso.md"]`. Tras `cmd_checkin`, exigir que el sentinel sobreviva o que el cierre aborte por versión cambiada. Con el código actual, `_push_caso_md(fm, ...)` sube el snapshot previo y lo elimina. Reproducción dinámica: **SIN VERIFICAR** por el fallo de colección.

### H9-04 — `_sin_ciclo_que_cerrar` no respeta la tolerancia del parser y también convierte estados desconocidos en éxito [MEDIO]
**Dónde:** `core/repository_checkout.py:139-146` (`estado_de_fm`); `scripts/repository_cli.py:1099-1124` (`_pull_caso_md`); `:995-1022` (`_sin_ciclo_que_cerrar`).

**Qué está mal:** `estado_de_fm` trata deliberadamente un `meta` no-dict como `disponible`, pero el helper nuevo hace `meta = (fm or {}).get("meta") or {}` y después `meta.get(...)`. Con frontmatter como `meta: corrupto` o una lista no vacía, esa segunda llamada lanza `AttributeError`; reaparece el traceback tardío que #93-B pretendía retirar, aunque ya se hayan subido y verificado bytes. Hay una segunda mala clasificación: `validar_transicion` también rechaza cualquier estado desconocido, pero `_sin_ciclo_que_cerrar` decide «reentrancia» solo por la presencia histórica de `ultimo_checkin_timestamp`. Un `_caso.md` con `estado_repositorio: corrupto` y una marca de un checkin anterior sale con 0 y deja el estado corrupto intacto.

**Por qué importa:** Un protocolo malformado no queda diagnosticado como tal: puede producir excepción cruda o falso éxito. La marca histórica no prueba que el estado actual sea `disponible` ni que el ciclo esté cerrado.

**Cómo se comprueba:** Dos casos. (1) `_caso.md` parseable con frontmatter `meta: corrupto`: ejecutar checkin y observar `AttributeError: 'str' object has no attribute 'get'` al entrar en `_sin_ciclo_que_cerrar`. (2) `meta` dict con `estado_repositorio: corrupto` y `ultimo_checkin_timestamp` no vacío: el resultado normativo debe ser error de protocolo; el helper actual retorna 0. Reproducción dinámica: **SIN VERIFICAR** por el fallo de colección.

### H9-05 — El nuevo uso de salida 4 contradice el contrato público del propio frontal [MEDIO]
**Dónde:** `scripts/repository_cli.py:45-49` (tabla de códigos) frente a `:1015-1022` (anomalía conocida → 4); `tests/test_checkin_reentrante.py:112-122`; `tests/test_repository_cli_fallos.py:330-362`.

**Qué está mal:** El contrato publicado define 4 como «no se pudo leer el protocolo o registrar la traza: estado indeterminado, lock conservado, recuperación necesaria». La rama nueva ha leído correctamente `_caso.md`, conoce `estado_actual == "disponible"`, sabe que no hay `ultimo_checkin_timestamp` y, por su propio diagnóstico, no hay lock que conservar. Aun así retorna 4. El mensaje además dice «el merge SÍ está subido y verificado — no lo repitas», mientras la semántica documentada de 4 señala estado indeterminado y recuperación. Los tests fijan el número nuevo, pero no actualizan ni distinguen el contrato que consumen scripts externos.

**Por qué importa:** Un automatismo no puede saber si debe reintentar para liberar un lock conservado, detenerse porque no había ciclo, o tratar el merge como ya aplicado. Esa ambigüedad es especialmente dañina porque los bytes ya pudieron cambiar antes del 4.

**Cómo se comprueba:** Añadir un test contractual que, para cada retorno 4, compruebe las invariantes documentadas (`lectura/traza fallida`, estado indeterminado y lock conservado). El escenario `disponible` sin marca viola las tres. La corrección exige asignar una semántica/código distinto o cambiar explícitamente el contrato y sus consumidores; el estado actual mezcla ambos.

### H9-06 — Los controles canónicos del guard omiten justo el estado que produce el checkout real [MEDIO]
**Dónde:** `tests/test_guard_copia_prestada.py:106-129`; `tests/test_repository_cli_checkout.py:210-221`; `core/case_manager.py:777-784`.

**Qué está mal:** `test_prestado_SIN_manifiesto_sigue_desviando` y el control de `conflicto` construyen el canon sin manifiesto. Ese escenario existe si falla la copia redundante, pero omite el camino normal: el test de checkout separado exige que el manifiesto se suba al Drive. Ningún test combina «canon prestado/conflicto» con «manifiesto remoto presente». El único control con manifiesto usa estado `disponible`; tanto el algoritmo correcto como el bypass defectuoso devuelven `desviar=False`, así que no discrimina. Su nombre promete «con o sin manifiesto», pero el cuerpo solo ejecuta con manifiesto.

**Por qué importa:** La suite puede permanecer verde mientras el arreglo desactiva por completo el guard en producción; H9-01 es exactamente el mutante que estos controles deberían matar.

**Cómo se comprueba:** Parametrizar los controles por `estado in {prestado, conflicto}` y `manifest in {ausente, presente}`, exigiendo desvío en el canon en las cuatro combinaciones. La combinación `manifest=presente` falla con `head`. Mejor aún, encadenar el `drive` resultante de `cmd_checkout` con la resolución canónica usada por `guard_escritura`. Ejecución: **SIN VERIFICAR** por la dependencia ausente.

### H9-07 — El test «no toca el Drive» solo comprueba que no aparece la palabra `check` [MEDIO]
**Dónde:** `tests/test_checkin_reentrante.py:95-101`; `scripts/repository_cli.py:717-773` y `:818-850`.

**Qué está mal:** El docstring exige «ni lock, ni log, ni bandeja», pero el único control sobre comandos es `assert "check" not in _subs(fake2)`. No toma snapshot del Drive, no prohíbe `copy`, `copyto` o `moveto`, ni comprueba la evidencia. El código actual ya puede ejecutar `copyto` de CP9 antes de detectar reentrancia, y el test sigue pasando. Además `_dos_veces` reutiliza un local inalterado; nunca monta el caso peligroso de trabajo añadido después del primer cierre, que activa `COPY_LOCAL` y H9-02.

**Por qué importa:** El aserto certifica una propiedad mucho más débil que la nombrada y deja verde una mutación canónica con salida 0.

**Cómo se comprueba:** Capturar `antes = deepcopy(drive)` justo antes del segundo checkin y exigir igualdad byte a byte después; exigir además que la traza del segundo intento contenga solo las lecturas mínimas permitidas, sin `copy`, `check`, `copyto`, `moveto` ni `rmdirs`. Repetir tras añadir un fichero local post-cierre. El código actual viola al menos la ausencia de escrituras de evidencia y, con fichero nuevo, la igualdad del Drive. Ejecución: **SIN VERIFICAR** por la dependencia ausente.

### H9-08 — El test reescrito dejó sin fijar que CP10-bis ocurra después de verificación y evidencia [MEDIO]
**Dónde:** `tests/test_repository_cli_fallos.py:330-362` en `head` frente al símbolo anterior `test_estado_ausente_revienta_en_cp11_DESPUES_de_mover_los_bytes` en `base`; `scripts/repository_cli.py:763-850`; `tests/test_checkin_reentrante.py:112-122`.

**Qué está mal:** La reescritura conserva que los bytes se copian y cambia correctamente la expectativa del evento, pero no observa que CP8 (`rclone check`) y CP9 (evidencia) hayan terminado antes del diagnóstico. Una implementación que adelantara CP10-bis hasta después de `copy` pero antes de `check`/evidencia seguiría satisfaciendo `rc == 4`, `doc.pdf == LOCAL`, un solo renglón de log y el mensaje. El test nuevo de `disponible` sin marca es aún más débil: solo exige 4 y cero `case_checkin`, por lo que pasaría incluso si la guarda se moviera antes de copiar. La cobertura mudada de A-2c observa el recuento de eventos en dos pasadas, pero no cubre este contrato temporal perdido.

**Por qué importa:** El cambio se justifica como «validar después de subir y verificar, pero antes del evento y la bandeja». Los tests solo fijan la mitad final. Pueden permitir que una refactorización cambie un checkin ya aplicado y verificado por un upload no verificado que sale 4.

**Cómo se comprueba:** En el escenario sin `estado_repositorio`, asertar la secuencia de subcomandos y los artefactos: `copy` antes de `check`, ambos logs de CP9 subidos, luego pull de `_caso.md`, y ausencia posterior de pull/push del log, integración y push del lock. Un mutante que mueva el pull/validación antes de CP8 o CP9 debe morir. Ejecución: **SIN VERIFICAR** por la dependencia ausente.

<!-- informe-literal:fin:v4tk -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-25)

**No-mutación del objeto.** Las dos copias externas se rehicieron desde `git archive` de
los mismos commits y coinciden por SHA-256 de árbol con las que recibió el revisor.

**Reproducciones propias, contra el árbol real.**

| Hallazgo | Cómo lo comprobé | Resultado |
|---|---|---|
| H9-01 | `grep MANIFEST_CHECKOUT scripts/repository_cli.py` → `:630` sube el manifiesto al remote | **CONFIRMADO**, y encontrado por mi cuenta en paralelo |
| H9-02 | test nuevo: fichero local creado tras cerrar, segundo checkin | **CONFIRMADO**: subía al canon sin lock |
| H9-03 | lectura del orden de CP10-bis → evento → bandeja → push | **CONFIRMADO**: ventana ensanchada por mi arreglo |
| H9-04 | `meta: corrupto` en el frontmatter | **CONFIRMADO**: `AttributeError` |
| H9-05 | tabla de códigos del módulo, `:45-49` | **CONFIRMADO**: `2` ya significaba «abortado sin efectos» |
| H9-06 | mis propios controles montaban el canon **sin** manifiesto | **CONFIRMADO** |
| H9-07 | el aserto era `"check" not in _subs(fake)` | **CONFIRMADO**: propiedad mucho más débil que la nombrada |
| H9-08 | el test no observaba `copy`/`check` antes del diagnóstico | **CONFIRMADO** |

**Lo que aporta el adjudicador.** El remedio de H9-05 no es una decisión nueva: el código
correcto (`2`) ya estaba definido en la tabla del propio módulo, diez líneas más arriba de
donde el primer arreglo escribió `4`.

**Y una corrección de mi propia remediación.** Comprobar al *entrar* —primera línea de
`cmd_checkin`— era igual de correcto y ponía **diez** tests de la red de caracterización de
la Fase 0 en rojo, por una operación que en los caminos que abortan antes no aporta nada. La
comprobación se colocó donde de verdad hace falta: justo antes de la primera escritura. De
diez rojos a cuatro, y los cuatro son cambios legítimos de secuencia.
