---
tipo: revision-adversarial
objeto: "diff 8d03e13..4206b80 — implementación de «El mutex del caso lo pide quien escribe» rev. 2 (MEJORAS #126, PLAN fila #17, PR #292)"
objeto_rev: "2"
commit: "4206b80"
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k2vd
sha256_informe: 32315bafca7ed129ac444387cdf60621665b6a6e5df696002099ab8112fde4de
adjudicado_en: docs/superpowers/specs/2026-09-05-mutex-en-los-entrypoints-de-intake-design.md §8
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R2 sobre el DIFF.** Segunda y última ronda de la pieza (radio de
> daño: decide quién escribe sobre el árbol del caso). El §1 conserva la voz del revisor sin una
> coma cambiada; el §2 es la evidencia que verifiqué yo. **La adjudicación NO está aquí:** va en
> el §8 del diseño, que pasa a **rev. 3**.
>
> **Objeto:** copias externas de `8d03e13` (base) y `4206b80` (head) con `git archive`, más el
> parche. Codex `gpt-6-astra`; hashes de custodia al abrir y al cerrar coincidentes con los míos.
> **El diff REMEDIADO (`eaf604d`) no se ha vuelto a revisar**, y se dice.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k2vd -->

Higiene conforme: al abrir, `C:\t\rev126_diff\rev` contenía exclusivamente `MANDATO.md`.

# R2 adversarial del diff de MEJORAS #126 — PR #292

## 1. Objeto, higiene y custodia de apertura

Revisión de las copias externas `../base/` y `../head/`, identificadas por el mandato como `8d03e13` y `4206b80`, respectivamente. `../HEAD.txt` contiene `4206b80`. Fecha del sistema comprobada: 2026-09-05. Revisor: Codex. La adjudicación corresponde a Claude contra la fuente.

Inventario recursivo: **1.208 ficheros en base, 1.210 en head y ninguna entrada `.git`**. Los diez ficheros cuyo contenido difiere coinciden exactamente con los enumerados por `diff_base_head.patch`: los cinco scripts de producción, dos ficheros de tests, `PLAN.md` y dos documentos. `core/` no cambia. El diseño rev. 2 es idéntico en ambos árboles. `git apply --check` sobre la copia de base acepta el patch. Esto verifica la coherencia de los materiales entregados; sin objetos Git no autentica que los árboles procedan de esos commits ni el procedimiento `git archive` empleado para producirlos.

SHA-256 leídos antes de abrir el código:

| Fichero de head | SHA-256 de apertura |
|---|---|
| `scripts/_mutex_cli.py` | `e490fff276c11ae58868f4b2ded08065a6af30505da2e4045551eb604d318bfb` |
| `scripts/sync_sudespacho.py` | `ae8e8177f5227cb14fe31b893d6d160bfb8865df2d2059f24fb51cd97e336ddf` |

No ejecuté código desde los originales ni escribí en ellos. Las ejecuciones fueron sobre `./head_run/` y `./base_run/`; los temporales, logs, mutantes y sondas permanecen en este scratchpad. El informe está fuera de ambos árboles revisados. La comparación final del inventario completo también conserva todos los hashes de los originales.

## 2. Resumen en tres líneas

La batería solicitada pasa: head 216/216 y base 201/201; las familias de mutantes exigidas a–g son detectadas.
Hay una evasión reproducida del mutex por resolución del destino, otra discordancia con junctions y una fuga del contador de `sync_all` entre invocaciones.
Las pruebas no cierran toda la frontera prometida: sobreviven sesiones CRM vacías y E13 acepta que el primer hijo falle; recomiendo NO-SHIP, sujeto a adjudicación.

## 3. Hallazgos

### H-01 — ALTO — Un `_caso.md` anidado sin identidad oculta el mutex del caso contenedor

**Fuente:** `head/scripts/_mutex_cli.py:91` y `:92`; consumidor `head/scripts/atomize_emails.py:37`.

El ascenso se detiene en el primer ancestro que contiene `00_Input/_caso.md`, aunque `_leer_id_go` devuelva `None`. No comprueba que ese ancestro sea una entrada del catálogo ni sigue hasta el caso exterior que sí tiene W-code. Se puede escribir dentro del árbol de un caso ocupado pasando por `--src/--out`.

**Reproducción ejecutada:** `head_run/tests/test_r2_probes.py::test_repro_nested_identity_shadow`. Crear el caso canónico A con `meta.id_go: W-ENTRY1`; dentro de A crear `01_Procesado/copied_case/00_Input/_caso.md` con texto sin metadatos. Tomar el lock W-ENTRY1 mediante la primitiva, sin registrar sesión reentrante. Ejecutar el CLI real con `--src A/00_Input --out A/01_Procesado/copied_case/01_Procesado/Emails`.

**Esperado:** identificar el caso contenedor A; código 2 y árbol de A intacto.

**Observado:** `w_code_de_ruta` devuelve `None`; aviso «el destino no cae bajo ningún caso del catálogo»; código 0. El motor real crea, entre otros, `_registro.json`, `corpus.jsonl`, `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md` y la carpeta `_revision`. La instantánea por nombres de directorios y SHA-256 cambia mientras W-ENTRY1 está tomado. No se sustituyó el motor en esta reproducción; incluso una fuente sin mensajes produce las escrituras.

La frontera a corregir es la identidad del **caso del catálogo que contiene el destino**. La mera presencia de un documento `_caso.md` más profundo no debe suplantarla ni convertirla en ausencia de identidad.

### H-02 — MEDIO — Un caso materializado mediante junction tiene identidad por referencia, pero queda sin mutex por destino

**Fuente:** `head/scripts/_mutex_cli.py:80`–`:87`.

Resolver físicamente la salida antes de buscar el caso pierde la relación con una entrada del catálogo que sea una junction hacia fuera de `CASOS_ROOT`. El localizador por referencia sí la reconoce. Las dos vías seleccionan políticas incompatibles para el mismo árbol físico.

**Reproducción ejecutada:** `test_repro_catalogue_case_junction_outside`. Crear un caso físico con `_caso.md` y W-ENTRY1 en una carpeta hermana del catálogo. Crear una junction `CASOS_ROOT/<case_id>` hacia ese caso mediante `New-Item -ItemType Junction`. Verificar que `w_code_de(case_id) == W-ENTRY1`. Tomar ese mutex. Ejecutar `atomize_emails --src <junction>/00_Input --out <junction>/01_Procesado/Emails`.

**Esperado:** al menos rechazar esta discordancia antes de escribir, o usar la misma identidad que la vía por referencia.

**Observado:** identidad por ruta `None`, aviso de destino externo, código 0 y escrituras del motor real sobre el caso físico ocupado. La junction inversa —alias externo hacia un caso físico dentro del catálogo— sí se reconoce correctamente; también la probé.

**Acotación:** exige una junction preexistente. `ensure_case` ya tiene una guarda de contención que rechaza este layout en el alta nominal; no afirmo que sea un layout admitido por esa puerta. El problema está en que el localizador y la atomización existente lo aceptan, y la nueva protección de `--out` lo trata como destino libre. No hay evidencia de que los expedientes reales estén montados así. Por esta precondición lo califico MEDIO.

### H-03 — MEDIO — La pérdida de mutex deja documentos en `_NUEVOS` y contamina la siguiente corrida

**Fuente:** `head/scripts/sync_sudespacho.py:397`–`:401`, `:436`–`:438` y `:465`.

El `continue` por `MutexPerdidoEnCli` evita tanto acumular como consumir `_NUEVOS[case_id]`. El diccionario vive en el módulo, no en una corrida. Tampoco se limpia al entrar en `sync_all`.

**Reproducción ejecutada:** `test_repro_sync_counts_leak`. A tiene un expediente y su motor informa 3 documentos después de llamar a `marcar_perdido()` sobre la sesión real; B informa 2 y termina normalmente. Invocar `sync-all` dos veces mediante `CliRunner` en el mismo proceso; en la segunda, ambos motores informan 0.

**Esperado:** el primer resumen contabiliza o separa explícitamente los documentos de A cuyo mutex se perdió; la segunda corrida anuncia cero nuevos y no hereda contadores.

**Observado:** primera salida 2, B sí se ejecuta, ambos casos aparecen en `tocados`, pero el total anuncia solo **2** y queda `_NUEVOS = {A: 3}`. Segunda salida 0: cada expediente imprime «sin cambios», el total anuncia **3 doc(s) nuevos** y no hay «Siguiente paso», porque `tocados` está vacío. Queda demostrada la fuga entre invocaciones, además de la omisión en el primer resumen. Un proceso CLI nuevo elimina la contaminación posterior, pero no corrige el primer resumen.

### H-04 — MEDIO — E12/E4b permiten cerrar la sesión CRM antes de las escrituras

**Fuente:** `head/tests/test_entrypoints_mutex.py:252`–`:271` y `:438`–`:472`; compromiso más amplio en el diseño rev. 2 §4.

E12 consulta `vigente` en el momento de la llamada para reserva/export y atomización/sello, pero no ejercita `ensure_case`, `register_expediente` ni los motores de `pull` e `intake_judicial`. E4b busca cualquier llamada al helper dentro del módulo; no verifica que gobierne un `with` ni su alcance. E9/E9b prueban rechazo al entrar, no duración.

**Reproducción ejecutada:** dos mutaciones independientes, conservando intactos los tests del autor:

```python
with _mutex_o_exit(...):
    pass
_pull(...)  # segunda mutación: _intake_judicial(...)
```

**Esperado:** la batería permanente falla porque las escrituras de un caso disponible ocurren fuera de la sesión.

**Observado:** cada mutante obtiene **22 passed, 1 skipped**, salida 0, en todo `test_entrypoints_mutex.py`; el omitido es E13, que solo usa atomización. Patches y logs: `mutants/empty_pull_session.*` y `mutants/empty_intake_session.*`.

No imputo este comportamiento al código actual: mis sondas adicionales de alta, registro y motor comprueban sesión vigente en ambos CLI de head y liberación tras excepción. El defecto es la cobertura permanente que debía impedir esta regresión.

E14 tiene una limitación relacionada: sustituye `sostenido` por una función que lanza **antes de entrar**, no inyecta `marcar_perdido` durante el motor como dice el diseño. Su primer caso no tiene expedientes y al segundo también le falla la entrada; no demuestra que otro caso sincronice tras una pérdida real. Las sondas de esta revisión sí ejercitan salida del contexto después de trabajo, y por esa vía descubren H-03.

### H-05 — MEDIO — E13 acepta un primer hijo fallido y no prueba el resultado 0/2 del diseño

**Fuente:** `head/tests/_bootstrap_e13.py:28` y `head/tests/test_entrypoints_mutex.py:541`.

El bootstrap devuelve un informe con `publicado=False`; el CLI devuelve 1 por esa rama. E13 solo exige `p1.returncode != 2`, por lo que tanto ese 1 deliberado como un fallo no controlado satisfacen el test. El diseño §4 exige exactamente un 0 y un 2.

**Reproducciones ejecutadas:**

1. Envolver `Popen.communicate` para registrar los códigos de la ejecución original de E13: **segundo = 2, primero = 1**. E13 pasa.
2. Mutar únicamente el bootstrap: tras recibir `SUELTA`, sustituir `return _Informe()` por `raise RuntimeError("R2: forced failure after SUELTA")`. Ejecutar E13 con `--runslow`: **1 passed**, salida 0 del test. El primer hijo ha fallado con traceback y el test lo acepta.

**Esperado:** detectar el fallo del primer hijo y comprobar el estado de terminación concreto que se haya contratado. Si se quiere conservar el informe no publicado, el contrato debería reconocer el 1 esperado y el test distinguirlo de un 1 por excepción; el actual no lo hace.

**Observado:** se comprueba de verdad el 2 por contención del segundo proceso, pero el éxito o fallo del primero no queda verificado. Evidencia: `mutants/e13_crash.patch`, `mutants/e13_crash.log` y `probe_e13_failure.py`.

### H-06 — BAJO — El runbook atribuye a `sync-all` un aborto con código 2 que no tiene

**Fuente:** `head/docs/RUNBOOK_APERTURA_EXPEDIENTE.md:361`–`:364`; también la afirmación agregada de `docs/MEJORAS_FUTURAS.md:5689`–`:5690`.

**Reproducción ejecutada:** E10, caso A tomado y caso B con dos expedientes disponibles.

**Esperado según el runbook:** los cinco subcomandos «abortan con código 2 y cero bytes» si otro proceso tiene el caso.

**Observado:** `sync-all` salta A, ejecuta los dos expedientes de B y devuelve **0**. Esto es correcto según el diseño §3.2 y P3, pero contradice la instrucción operativa agregada. «Cero bytes» vale para el caso ocupado, no para el barrido. La corrección debe distinguir esta política, no cambiar el barrido para ajustarlo a una frase incorrecta.

## 4. Contraste de P1–P5 y respuesta al mandato

| Propiedad | Resultado | Evidencia y alcance |
|---|---|---|
| P1 — ningún escritor fuera del mutex y árbol intacto al estar ocupado | **REFUTADA** como afirmación universal | H-01 produce escrituras reales dentro del caso ocupado; H-02 añade la discordancia por junction. En referencias y destinos ordinarios, E7–E12 y las sondas adicionales confirman las fronteras actuales. `sync-all` no devuelve 2 por ocupación: su excepción está expresamente diseñada. |
| P2 — resolución de identidad y avisos | **REFUTADA** | Se verifica `resolve_ref` antes de `_caso.md`; funcionan referencias ordinarias, W ausente, rutas relativas, `..` y alias hacia dentro. El ascenso anidado y la junction saliente fallan según H-01/H-02. El aviso de destino externo también se usa para un destino dentro de un caso sin identidad. |
| P3 — políticas y estado de `sync_all` | **REFUTADA** en «memoria de la corrida» | H-03. Sí se confirman salto y resumen del ocupado, continuación a B tras pérdida real en A y salida final 2 incluso con `tocados`. Todos los pulls de un caso están dentro de una única llamada a `sostener`. |
| P4 — contención real de E13 y código 2 del segundo | **CONFIRMADA** en su enunciado estricto | E13 se ejecutó con procesos nuevos y el segundo recibió 2 por ocupación. H-05 refuta la garantía adicional del diseño sobre terminación 0 del primero; E13 tampoco compara el árbol del perdedor. |
| P5 — capas, helper, censo, AST y migración | **CONFIRMADA** para el código actual | `core/` idéntico; E5, E4a/E4b, censo 88 y 21 tests de migración pasan. El helper usa `mutex_sesion.sostenido`. H-04 limita lo que E4b puede garantizar frente a regresiones. |

### Respuesta a los ocho puntos concretos

1. **Flujos y escrituras.** Export resuelve y muestra texto antes del bloque; reserva y motor quedan dentro. `_print_report`, `ExportReport.resumen`, la lectura de `report.errors/written` y la salida posterior solo calculan/imprimen; no escriben al expediente. El diseño pide incluir también el informe, pero sacarlo no abre una escritura. Atomización cubre motor y sello; comprobé ambos retornos, publicado y no publicado, con pérdida real al salir: devuelven 2 y no dejan sesión. `pull` e `intake_judicial` envuelven sus trabajadores completos, desde `ensure_case` hasta sus mensajes finales. `verify_expediente_referencia` llama a `fetch_referencia_cliente`, que hace un GET HTTP y compara valores; no escribe ficheros ni modifica CRM. No lo invoqué contra CRM real. `list_cases`, `buscar` y `read_md` son lectores: no encontré escrituras antes del bloque de `sync_all`. `_NUEVOS` sí sobrevive: H-03.

2. **Identidad y entradas límite.** W-code inexistente → `resolve_ref` conserva referencia → `buscar` devuelve `None` → helper devuelve `None`: comprobado. `case_id` con `/` no lo valida el helper: puede resolver rutas existentes; el `pull` con `<caso>/child` acaba en `ValueError` de `ensure_case`, antes de escribir, comprobado por instantánea. Ruta relativa y `..` se normalizan; el propio `CASOS_ROOT` devuelve `None`; raíz no ancestro devuelve `None` antes de ascender, sin bucle infinito. Junctions en ambos sentidos: H-02. Sin `meta`, `id_go` vacío o cero numérico → `None`; entero 123 → cadena `"123"`, después `sostener` lanza `ValueError` porque no es W-code. Es un rechazo previo a escritura, no el aviso de ausencia. El helper no valida el formato del W-code ni transforma todos los metadatos inválidos en ausencia. `read_md` puede lanzar errores YAML que no son `ValueError`; no ejecuté una matriz de YAML corrupto. La identificación anidada falla según H-01. Para un caso existente sin identidad pasado por `--out`, se imprime `AVISO_FUERA_DE_CASO`, aunque exista el caso: el retorno `None` no conserva la causa. `AVISO_ALTA` sí se selecciona antes de crear un caso ausente en los comandos CRM.

3. **`sostener`.** Las clases importadas de `workspace_model` son las usadas realmente por `case_mutex` y `mutex_sesion`, no clases homónimas distintas. `mutex_sesion.sostenido` cierra su gestor en `finally` y elimina la sesión; `tomado` señala pérdida al salir si no hay excepción del cuerpo. Una pérdida puede sustituir el retorno ya calculado y alcanza el `except` externo: comprobado con `marcar_perdido`, para retorno 0 y retorno 1 de atomización. Una excepción `RuntimeError` del motor se propaga y se suelta el mutex; E12 y las sondas CRM lo ejecutan. Si coinciden excepción del cuerpo y pérdida, el core prioriza la primera y añade una nota; no prometo conversión universal a 2 en esa combinación, que no ejecuté.

4. **`sync_all`.** A ocupado/B disponible: el ocupado no entra al trabajador ni añade `tocados`; B hace sus dos pulls y se libera al final, según E10. Desde un estado limpio, el código suma sus retornos al total. El `continue` por ocupación no omite el resumen de ocupados, que se emite después del bucle. El de pérdida sí omite consumir `_NUEVOS`; no hay un `pop` posterior a esa pérdida: H-03. `tocados` del caso perdido permanece, B continúa y el `raise typer.Exit(2)` final se ejecuta incluso después de imprimir los siguientes pasos, reproducido. E10 observa vigencia en cada pull, pero no compara identidad/nonce de las sesiones; la única sesión por caso se confirma además por el flujo de código.

5. **Migración e imports.** `CasoOcupadoError` es un alias de la misma clase `CasoOcupado`, por lo que el `except` histórico sigue capturándola; los 21 tests de migración pasan en ambos árboles. Los imports intermedios no introducen un ciclo: `_mutex_cli` solo importa librería estándar al cargar y difiere imports de core a sus funciones. Su `noqa` afecta al lint, no a Python. La migración mantiene `_bajo_mutex` como envoltorio delegado. Una pérdida entra en su `except Exception` general y devuelve 1; el mandato no incluye migración entre los cinco subcomandos con contrato nuevo de salida 2 por pérdida. Su docstring inicial sigue diciendo que export y sync aún no piden mutex: texto preexistente que este diff deja desactualizado.

6. **Tests y mutantes.** E7/E9/E9b espían los primeros escritores y comparan nombres/hash; E8 cubre motor/sello, aunque su aserción de stderr termina en `or True` y nunca puede fallar. E9c sustituye `_pull`: verifica aviso y delegación, no creación efectiva. E11 comprueba el ejemplo ordinario dentro/fuera, no toda la selección de identidad. E12 sí mira `vigente` durante sus llamadas, con las ausencias de H-04. E14 no simula la pérdida a mitad: H-04. E13 usa una barrera real, comprueba muerte antes de READY mediante `poll`, y tiene límites de 60 s en espera y subprocesos. Si Python tarda más de 60 s, falla; no garantiza determinismo para cualquier carga de Windows. El motor del primer hijo también espera solo 60 s, por lo que una segunda inicialización cercana a ese límite puede agotar la barrera. En timeout de `subprocess.run`, Python mata y espera al segundo hijo; `p2` del test nunca se asigna. El `finally` mata al primero vivo pero no llama a `wait` ni drena sus pipes en esa rama. No inyecté fallos de arranque/timeout. Los ficheros READY/SUELTA y registros quedan en `tmp_path`, retenido bajo `--basetemp`, no en el caso real. Colección explícita de `_bootstrap_e13.py`: **no tests collected**; el fichero no aporta tests. Matriz de mutación ejecutada en §5.

7. **Regresiones.** Los cinco módulos exigidos suman 193 tests y pasan tanto en base como en head. Sus contenidos son idénticos. `test_entrypoints_mutex.py` pasa de 8 casos parametrizados a 23; ésa es la diferencia 201 → 216. No hay cambio de expectativa en esos cinco módulos. La instantánea existente se refuerza, pero las nuevas comprobaciones débiles de E8/E13 se describen arriba.

8. **Docs.** H-06 responde a la promesa literal para los cinco: es falsa para `sync-all` por diseño. H-04/H-05 identifican promesas de pruebas más amplias que las ejecutadas. La exclusión sigue siendo por máquina; alta sin identidad y UI se declaran fuera. La frase «un solo sitio» del helper no elimina las adquisiciones propias de `abrir_caso` y `sala_maquina`, que deliberadamente no cambian. `PLAN.md` remite la R2 a §8 del diseño, pero el archivo entregado termina en §7; no he supuesto una adjudicación aún inexistente.

## 5. Ejecuciones y mutantes

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`. Se usaron `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `-p no:randomly` y `-p no:cacheprovider`. Sin instalaciones ni consultas externas. Los fixtures aíslan catálogo, registro y llamadas externas. Las sondas con motor real usan únicamente casos sintéticos.

Comando efectivo, desde cada copia, con `--basetemp` **relativo y fuera del árbol de la copia**:

```text
python -m pytest -o addopts= -q -p no:randomly -p no:cacheprovider --runslow --basetemp=../tmp_<corrida> tests/test_entrypoints_mutex.py tests/test_sync_sudespacho.py tests/test_email_export.py tests/test_migrar_layout.py tests/test_abrir_caso_cli.py tests/test_escritura_censo.py
```

| Módulo | Base | Head |
|---|---:|---:|
| `test_entrypoints_mutex.py` | 8 | 23 |
| `test_sync_sudespacho.py` | 42 | 42 |
| `test_email_export.py` | 76 | 76 |
| `test_migrar_layout.py` | 21 | 21 |
| `test_abrir_caso_cli.py` | 45 | 45 |
| `test_escritura_censo.py` | 9 | 9 |
| **Total, todos pasan** | **201** | **216** |

Base: 21,07 s; head inicial correcto: 23,54 s. Tras restaurar mutantes, repetición final de head: **216 passed in 18.13s**, con JUnit en `final_suite.xml`. Logs: `base_run_verified.log`, `head_run_verified.log`, `head_final.log`. El censo exige simultáneamente `total <= 88` y `total == 88`: confirma **88**, no solo ausencia de crecimiento.

**Intentos de entorno fallidos, no contabilizados como cobertura:** primera ejecución con directorio de trabajo de herramienta cambiado y `./tmp`: 216/201 errores de preparación `PermissionError` al crear basetemp. La creación aislada de directorios después sí funcionó, por lo que no atribuyo causa definitiva al primer fallo. Una ejecución desde el scratchpad con `Set-Location` y temporales dentro de head llegó a E1, pero la guarda del mutex rechazó el registro por vivir dentro del proyecto (`WorkspaceUnderCatalogRoot`). El comando efectivo cambia a `../tmp_<corrida>` y deja intactas esas guardas; no se parcheó pytest ni core para lograr el verde.

### Matriz de mutación

`run_mutants.py` compila cada transformación, ejecuta el fichero permanente `test_entrypoints_mutex.py` en un intérprete nuevo y restaura los bytes del script en `finally`. Patches, logs íntegros y resultados están en `mutants/`. No se ejecutó E13 en los 16 mutantes de producción: queda explícitamente omitido por `slow`; cada resultado pasa/falla por la batería restante. E13 se ejecutó aparte, sin mutación y con su mutante específico.

| Mutante ejecutado | Resultado | Fallos de tests |
|---|---|---:|
| a — quitar `with` de export | Muerto | 3 |
| a — quitar `with` de atomización | Muerto | 5 |
| a — quitar `with` de pull | Muerto | 2 |
| a — quitar `with` de intake judicial | Muerto | 1 |
| a — quitar `with` de sync-all | Muerto | 2 |
| b — adquirir después de `email_dest_dir` | Muerto | 2 |
| c — adquirir después de `ensure_case`, pull | Muerto | 2 |
| c — adquirir después de `ensure_case`, intake judicial | Muerto | 1 |
| d — eliminar `resolve_ref` del helper | Muerto | 3 |
| e — identidad por ruta siempre `None` | Muerto | 1 |
| f — abortar `sync-all` ante ocupado | Muerto | 1 |
| g — mensaje de pérdida con `_cobertura.md` | Muerto | 1 |
| Reloj naïve importado como `now_iso_utc` | Muerto | 7 |
| Sesión vacía y `_pull` fuera | **Sobrevive** | 0; 22 pasan |
| Sesión vacía e `_intake_judicial` fuera | **Sobrevive** | 0; 22 pasan |
| Abortar inmediatamente `sync-all` ante pérdida | Muerto | 1, por faltar el texto del resumen |
| Bootstrap E13 falla después de SUELTA | **Sobrevive** | E13 pasa con `--runslow` |

Total de variantes propias ejecutadas: **17; 14 mueren y 3 sobreviven**. Las siete familias del mandato a–g están cubiertas. Esto no identifica los «14 mutantes» del autor con mis 14 muertos: no se entregó su lista exacta de transformaciones/ejecuciones. Sí reproduce las familias concretas exigidas y demuestra supervivientes adicionales relevantes.

Hubo un fallo del generador antes de ejecutar f: el reemplazo multilínea no coincidía por CRLF y la aserción de «cambio efectivo» detuvo el arnés. Se normalizó el texto de entrada del generador y se reanudaron únicamente las variantes pendientes. No se contabilizó ese fallo como mutante muerto.

**Sondas adicionales:** `head_run/tests/test_r2_probes.py`, ejecutado con `-q -s`, basetemp `../tmp_probes_final`: **11 passed in 3.89s**. Estas pruebas afirman el comportamiento observado, incluidos los defectos; no son una batería de aceptación de un arreglo. Cubren contaminación entre corridas, pérdida real sobre retornos 0/1, rutas/identidad límite, dos direcciones de junction, metadato anidado, vigencia durante escritores CRM, códigos efectivos de E13 y rechazo de `case_id` con barra. Log íntegro: `probes_final.log`. `probe_e13_failure.py` reproduce H-05. Ninguna de estas sondas se añadió a los originales.

## 6. Sin verificar y límites

- No corrí la suite completa del repositorio; sí los seis módulos indicados y las sondas descritas. No usé pytest-randomly ni probé órdenes aleatorios.
- Los motores de export/CRM están sustituidos o aislados en las pruebas. No hubo descargas contra Gmail, sudespacho, Drive ni datos de cliente. Los contraejemplos de rutas sí ejecutan el motor real de atomización con fuente sintética vacía.
- La contención externa de E7–E12 y de las sondas de ruta usa la primitiva sin sesión reentrante en el proceso de test. La exclusión entre dos procesos nuevos se ejecutó específicamente en E13; no se repitió ese escenario para cada CLI.
- No inyecté muerte antes de READY, arranque de Windows de más de 60 s, agotamiento de disco, cierres abruptos del sistema ni carrera de sustitución de una junction durante el trabajo. Esos análisis de E13 son lectura de control de flujo, no simulaciones ejecutadas.
- El intento de inventariar procesos globales mediante `Get-CimInstance Win32_Process` recibió «Acceso denegado». No afirmo haber comprobado globalmente ausencia de procesos residuales. En las ejecuciones normales instrumentadas de E13, ambos hijos completaron `communicate`; en el mutante de H-05 el primer hijo también termina por excepción. Permanecen los artefactos de prueba bajo los basetemp del scratchpad.
- El escenario de junction saliente es un layout preexistente no admitido por la guarda del alta nominal; se declara expresamente en H-02. No hay medición de su frecuencia real.
- No hice una tercera ronda ni revisé arreglos posteriores. La conclusión se limita a `4206b80` según los materiales entregados. No se han implementado remedios.

## 7. Custodia de cierre

Se volvieron a leer los originales después de las ejecuciones. Ambos hashes coinciden con los de apertura:

| Fichero de head | SHA-256 de cierre |
|---|---|
| `scripts/_mutex_cli.py` | `e490fff276c11ae58868f4b2ded08065a6af30505da2e4045551eb604d318bfb` |
| `scripts/sync_sudespacho.py` | `ae8e8177f5227cb14fe31b893d6d160bfb8865df2d2059f24fb51cd97e336ddf` |

El inventario completo final de base y head coincide con `archive_inventory.json`. Los cuatro scripts mutados y el bootstrap de la copia de ejecución han sido restaurados byte a byte frente a head. El informe se entrega en UTF-8 sin BOM, con LF y un único salto final; su digest se comunica fuera del fichero.

NO-SHIP

<!-- informe-literal:fin:k2vd -->

## 2. Evidencia verificada por mí al adjudicar

- **H-01.** Leí `_mutex_cli.w_code_de_ruta` en `4206b80`: `for cand in (p, *p.parents)` con
  `return` en el primer `_caso.md` — el anidado gana. Remedio: `caso_de_ruta` devuelve
  `casos[-1]`, el más externo; E11b lo exige con un `_caso.md` sin `meta` dentro de A y comprueba
  que `main(--out …)` aborta con 2 y el motor no corre. Mutante `casos[0]`: muere.
- **H-02.** `Path(ruta).resolve()` era la única forma; una junction del catálogo hacia fuera
  resuelve fuera de `CASOS_ROOT` → `None`. Remedio: forma léxica primero (la misma razón que
  `case_mutex.raiz_de_locks` documenta). E11c crea la junction con `mklink /J` y exige `W` por
  ruta y por referencia; se salta si no puede crearla. Mutante «solo resuelta»: muere.
- **H-03.** `_NUEVOS` era de módulo y el `except MutexPerdidoEnCli` hacía `continue` antes del
  `pop`. Remedio: dict local consumido en `finally`. E14 exige «5 doc(s) nuevos» (3 del caso
  perdido + 2) y «0» en la segunda corrida del mismo proceso. Dos mutantes (no contar el perdido;
  contar solo en el camino feliz): mueren.
- **H-04.** Reproduje los dos mutantes del revisor (`with` vacío + trabajador fuera en `pull` e
  `intake_judicial`): 22/22 verdes. E12b comprueba `mutex_sesion.vigente(...)` dentro de
  `ensure_case`, `register_expediente` y el motor, y `None` al salir: los dos mueren. E14 usa
  `SesionMutex.marcar_perdido()` (`case_mutex.py:533`) sobre la sesión real durante el motor.
- **H-05.** El bootstrap devolvía `publicado=False` → 1, y E13 aceptaba `!= 2`. Remedio: informe
  publicado (0) y `== 0`; mutante «el bootstrap muere tras SUELTA» ahora mata E13.
- **H-06.** Texto del runbook corregido: `sync-all` salta y resume, código 0.

**Cobertura de la remediación: sin tercera ronda** (regla de rondas de `CLAUDE.md`).
