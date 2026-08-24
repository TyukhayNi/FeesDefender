---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md
objeto_rev: "4"
commit: 3f092f8
ronda: "7"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k3wq
sha256_informe: 53ba2b4d0370d1564a336cde7021b942c902807d78f39e053b8d0ed8ab45fbec
adjudicado_en: docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md §12
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R7.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el §12 del objeto, no aquí.
>
> **Por qué esta ronda existe.** El plan de la Fase 1 se escribió el 2026-07-29 y **nunca había
> pasado una revisión adversarial**: la fila #3 de `PLAN.md` lo decía expresamente, y las tres
> pasadas adjudicadas que allí se mencionan fueron sobre la **spec**, no sobre el plan. R7 es la
> primera mirada externa sobre su descomposición en tasks, y se corrió **antes de ejecutarla**:
> ocho tasks cuyo Task 6 toca la superficie de migración más ancha del repo.
>
> **Lo que encontró, en una frase.** El plan no construye la Fase 1 que la spec define: conserva
> hasta la Fase 4 el mismo fallback que su criterio de salida exige eliminar. Quince hallazgos,
> quince confirmados.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k3wq -->
# Informe adversarial R7 — primera revisión del plan de la Fase 1 dual

## Objeto, alcance y cadena de custodia

- Objeto: `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`, exclusivamente Tasks 4–11.
- Commit declarado del árbol externo: `3f092f8`.
- Fuera de alcance: Tasks 1–3, marcadas como supersedidas.
- Árbol leído: `objeto/`, 1.057 ficheros. El hash canónico se obtuvo alimentando SHA-256 con ruta relativa POSIX y bytes de cada fichero, en el orden sin distinción de mayúsculas que reproduce el digest entregado.
- SHA-256 de apertura: `12616082d39bf3d2cc43be50775a76d3ade3a0dd09f4c48f7e44bbcb8b503055` — coincide con el esperado.
- Toda ejecución se hizo sobre `informe/scratch_objeto` o bajo `%TEMP%`. No se escribió en `objeto/`.
- SHA-256 de cierre: `12616082d39bf3d2cc43be50775a76d3ade3a0dd09f4c48f7e44bbcb8b503055` — coincide con apertura y esperado.

## Resumen ejecutivo

La descomposición T4→T11 no tiene una dependencia invertida: Task 4 es la única sin predecesoras y Task 8 está situada antes del primer consumidor mutante migrado. El plan sí enumera casi todas las piezas nominales de la Fase 1.

No obstante, no implementa la Fase 1 que la spec y D1 exigen. Conserva hasta Fase 4 el mismo fallback que afirma cerrar; no migra al creador explícito ni a todos los escritores; deja `log_path(case_id)` vivo; y no proporciona la adopción que la transición exige para los checkouts legacy antes de migrar `sala_maquina`. Además, varias pruebas permiten pasar a implementaciones rotas: el test crucial de split brain es literalmente `...`, el de atomicidad no invoca la escritura del registro y el mutante de los «cuatro planos» solo ataca uno.

D2 no obliga a construir el mutex dentro de esta Fase 1, pero sí vuelve costosa una omisión del Task 5: no hay forma física ni contrato de concurrencia del registro. Un lock por W-code no serializa dos reemplazos de un eventual fichero agregado hechos por procesos que trabajan sobre W-codes distintos.

## Hallazgos

### H7-01 — CRÍTICO — La Fase 1 conserva el fallback que su criterio de salida exige eliminar

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:292-293, 298, 458-463`; `core/case_manager.py:266-274`; `core/catalogo_documental.py:87-90`.
- **Cita literal:** «`strict: bool = False`»; «**Default `False` en esta fase**»; «`path_for(strict=False)` sigue comportándose exactamente como hoy»; «No invierte el default [...] (Fase 4)».
- **Fuente contrariada:** la spec dice que en Fase 1 «`caso_path` deja de devolver rutas inexistentes y ningún escritor hace `mkdir` de la raíz» (`...dual-case-workspace-design.md:875-894`) y D1 lo vuelve a cerrar en los mismos términos (`...orquestador-apertura-expediente-design.md:1625-1631`). El invariante de transición prohíbe que cualquier entrypoint existente llame `caso_path` y asuma que el resultado es escribible (`...dual-case-workspace-design.md:467-477`).
- **Por qué es defecto:** con el default conservado, los 44 ficheros que llaman realmente a `caso_path` no reciben modo estricto. `case_manager.ensure_case` aún depende del fallback para crear (`case_manager.py:266-270`), pero el plan tampoco lo migra a una función explícita de creación. A la vez, escritores no migrados como `catalogo_documental.save_catalog` siguen haciendo `mkdir(parents=True)` sobre la ruta resuelta. Invertir sin migrar rompe el alta; no invertir conserva el expediente fantasma. El plan no contiene el tajo que resuelva esa disyuntiva. Tampoco hay Step que llame `caso_path(..., strict=True)` y pruebe que propaga el keyword.
- **Qué lo demostraría:** después de T6, ejecutar un test parametrizado sobre todos los escritores inventariados con un W-code inexistente y exigir `LocalWorkspaceMissing` más hash de `CASOS_ROOT` idéntico; en paralelo, `ensure_case` debe crear únicamente por una API explícita que no pase por el localizador estricto.

### H7-02 — ALTO — Un registro corrupto se convierte en “registro vacío” y abre una vía fail-open

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:267,270`.
- **Cita literal:** «Un registro corrupto [...] se devuelve vacío con aviso» y «JSON corrupto → cuarentena + vacío».
- **Fuente contrariada:** «Fail closed. La ambigüedad o falta de verificación bloquea la mutación» y «Sin fallback silencioso» (`...dual-case-workspace-design.md:182-188`). El resolver consulta primero el registro y puede devolver `drive_active` cuando el canon dice `disponible` (`ibid.:434-450`).
- **Por qué es defecto:** `cargar()` borra semánticamente la diferencia entre “no había workspace local” y “no puedo saber qué workspace había”. Tras devolver `[]`, el resolver ya no puede detectar un scratch/checkout colisionante y puede autorizar Drive. La cuarentena conserva bytes, pero la decisión de autorización ya ha fallado abierta.
- **Qué lo demostraría:** sembrar un registro truncado que contenga el comienzo de una entrada local y un canon `disponible`; `resolver_por_identidad` debe devolver un error estructurado de registro no verificable y cero efectos, nunca `DRIVE_ACTIVE`.

### H7-03 — ALTO — La prueba de atomicidad del Task 5 no ejecuta la operación atómica

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:266,270`.
- **Cita literal:** «`os.replace` deja el fichero íntegro si el proceso muere entre escritura y rename (simulado escribiendo el temporal y no renombrando)».
- **Fuente contrariada:** «La escritura es atómica» (`...dual-case-workspace-design.md:321-323`).
- **Por qué es defecto:** escribir un temporal a mano y omitir el rename no atraviesa `WorkspaceRegistry.alta/baja/revalidar`. Ese test pasa aunque producción escriba el JSON destino in-place y jamás llame `os.replace`.
- **Qué lo demostraría:** sembrar bytes válidos, parchear `os.replace` para lanzar una excepción en la llamada de producción, invocar `alta`, comprobar que la excepción ocurrió, que el destino conserva exactamente los bytes anteriores y que el temporal está en el mismo directorio. Un mutante que sustituya `os.replace` por `write_text(destino)` debe morir.

### H7-04 — MEDIO — Task 5 no fija una forma concurrente compatible con el namespace por W-code de D2

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:263-270`; `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1645-1660`.
- **Cita literal:** Task 5 habla de «fichero temporal [...] + `os.replace`» y de «un registro corrupto»; D2 fija «Namespace [...] W-code» y un lockfile `O_CREAT|O_EXCL` que «vive en el registro local».
- **Fuente contrariada:** D2 separa locks por identidad canónica (`ibid.:1649-1659`) y exige liberación por nonce. La atomicidad de reemplazo no evita actualizaciones perdidas.
- **Por qué es defecto:** si Task 5 materializa un JSON agregado —la lectura natural del singular y de `cargar()`—, dos procesos sobre W-codes distintos pueden cargar el mismo estado y reemplazarlo; el último elimina el alta del primero. Los futuros locks por W-code no se excluyen entre sí. Cambiar después a ficheros por entrada o añadir un lock global altera forma, cuarentena, migración y tests. No hay contradicción entre los campos de `WorkspaceEntry` y D2; la incompatibilidad está en la concurrencia no decidida.
- **Qué lo demostraría:** dos procesos, barrera después de `cargar()`, `alta()` simultánea de W-codes distintos; al terminar deben existir ambas entradas. Además, un test de layout debe demostrar que los lockfiles de D2 no son interpretados como entradas ni cuarentenados por `cargar()`.

### H7-05 — ALTO — El test que debía impedir el split brain es un test vacío que pasa

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:338-365`.
- **Cita literal:** el cuerpo de `test_append_event_escribe_en_el_arbol_del_workspace_no_en_casos_root` termina en `...`.
- **Fuente contrariada:** Fase 1 exige que `append_event` reciba el workspace/log resuelto porque, sin ello, `--case-dir` «parte la custodia en dos» (`...dual-case-workspace-design.md:883-894`). El propio plan llama a Task 8 «la tarea más importante» (`:338-339`).
- **Por qué es defecto:** `...` es una expresión Python válida. El test pasa sin llamar `append_event`, sin sembrar `CASOS_ROOT` y sin comprobar ningún fichero. Una implementación que reintroduzca `caso_path` queda verde exactamente en la frontera central del plan.
- **Qué lo demostraría:** configurar `CASOS_ROOT` con un sentinel, crear un scratch fuera, invocar `append_event(scratch, ...)`, afirmar que el único log nuevo está bajo scratch y comparar hash/inventario del canon antes/después. El mutante `destino = caso_path(case_id)` debe fallar.

### H7-06 — ALTO — El vocabulario de auditoría está rancio: 28 + 5 no son 32

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:349,368`; `core/intake_log.py:42-88`; `tests/test_intake_log.py:332-388`.
- **Cita literal:** «Altas en `INTAKE_EVENTS` (27 → 32)» y «el set de eventos pasa a 32».
- **Fuente contrariada:** el objeto actual prueba y enumera **28** eventos; `contenido_adjuntos` se añadió el 2026-08-04 (`test_intake_log.py:332-339`). Task 8 ordena conservar `pendiente_checkin`.
- **Por qué es defecto:** añadir los cinco nombres listados produce 33. Para satisfacer el aserto “32”, el implementador tendría que borrar silenciosamente un evento histórico o contrariar el Step. En un log forense, retirar vocabulario rompe lectura/reentrada y no puede normalizarse como actualización de conteo.
- **Qué lo demostraría:** `assert len(INTAKE_EVENTS) == 33` y comparación de conjuntos: los 28 actuales deben ser subconjunto estricto y la diferencia debe ser exactamente los cinco eventos nuevos.

### H7-07 — ALTO — El death test de “cuatro planos” muta solamente uno

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:419-431`.
- **Cita literal:** la interfaz promete «los **cuatro planos**», pero Step 3 solo ordena «introducir a mano **una escritura** en un caso bloqueado».
- **Fuente contrariada:** §3.2-bis dice que un componente no puede declararse cubierto comprobando solo el árbol y enumera árbol, canon incluidas carpetas, servicios externos y estado local (`...dual-case-workspace-design.md:133-152`); §14.2 exige death tests en los cuatro (`ibid.:1104-1106`).
- **Por qué es defecto:** el único mutante descrito prueba el detector de ficheros. `llamadas_externas`, registro y sentinels pueden no participar en ninguna aserción y el arnés seguir pasando. Es el modo de fallo advertido en el mandato: cuatro fronteras nombradas, una sola atacada.
- **Qué lo demostraría:** cuatro mutantes independientes y cuatro rojos obligatorios: crear/modificar fichero del árbol; crear directorio/fichero en canon; ejecutar una llamada mutante del doble externo; modificar registro/caché/sentinel. El Step solo se completa si cada mutante falla por su plano correspondiente.

### H7-08 — ALTO — “Servicio externo falla” existe como fila, no como escenario ejecutable

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:420-424,431-433`.
- **Cita literal:** «`ESCENARIOS`: las 9 filas» y «`matriz_para(invocar: Callable[[CaseWorkspace | Path], int])`».
- **Fuente contrariada:** §14.1 exige «Servicio externo falla → Reintento seguro o aborto idempotente» (`...dual-case-workspace-design.md:1078-1090`) y §14.2 exige dobles de integración y conteo de efectos (`ibid.:1094-1106`).
- **Por qué es defecto:** la firma del arnés solo entrega workspace/ruta; el plan no define doble, instante de fallo, contador, segunda invocación ni aserto de idempotencia. Se puede cumplir `len(ESCENARIOS) == 9` y no inducir jamás el fallo externo.
- **Qué lo demostraría:** para `sala_maquina`, parametrizar un doble que falle después de un efecto observable, ejecutar dos veces y exigir o bien cero publicación o una única publicación estable, además del conteo exacto de llamadas.

### H7-09 — ALTO — Se migra `sala_maquina` antes de construir la adopción exigida para checkouts legacy

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:325,381-398`; `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md:1130-1138`.
- **Cita literal:** Task 7 prueba que un checkout propio «sin entrada de registro → `LocalWorkspaceMissing` (no se adopta solo)»; Task 9 sustituye el resolver existente por `_resolver_workspace`.
- **Fuente contrariada:** §15 ordena que «Los checkouts anteriores sin registro [...] requieren `--case-dir` y una operación explícita de adopción/verificación» (`ibid.:1132-1134`).
- **Por qué es defecto:** ningún Task 4–11 crea esa operación. Task 8 solo añade el nombre de evento `checkout_adoptado`; no existe API, CLI ni Step de adopción. Tras T9, un checkout legacy que antes podía procesarse mediante el override local queda bloqueado, y la transición no ofrece la vía normativa para desbloquearlo.
- **Qué lo demostraría:** sembrar un checkout legacy válido (manifest, proyección/identidad y lock propio en Drive), sin `WorkspaceEntry`, invocar `sala_maquina --case-dir`; debe existir un flujo explícito de verificación/adopción que registre y luego resuelva. En el plan actual solo existe el error.

### H7-10 — MEDIO — La tabla de ocho capacidades puede estar incompleta y los tests seguir verdes

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:238-244`.
- **Cita literal:** «`Capability(StrEnum)`: las 8 del §5.4» y Step 1 solo niega `WRITE_CASE`, `INGEST` y `MUTATE_CANONICAL` en algunos modos.
- **Fuente contrariada:** §5.4 enumera `read_case`, `write_case`, `ingest`, `generate_derivatives`, `mutate_canonical`, `checkout`, `checkin`, `promote` y su disponibilidad por modo (`...dual-case-workspace-design.md:262-283`).
- **Por qué es defecto:** no hay positivos de `READ_CASE`, `CHECKOUT`, `CHECKIN` o `PROMOTE`, ni una igualdad completa por modo. Una tabla casi vacía pasa los negativos y difiere el descubrimiento hasta fases posteriores.
- **Qué lo demostraría:** parametrizar la igualdad completa `CAPACIDADES_POR_MODO == esperado` para cada modo y un mutante que elimine o intercambie individualmente cada una de las ocho capacidades.

### H7-11 — MEDIO — Pureza, reloj e identidad inyectados están nombrados, no contratados

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:319,325`.
- **Cita literal:** «el reloj y la identidad **se inyectan**: la pieza es pura y determinista».
- **Fuente contrariada:** el resolver es el único servicio de resolución (`...dual-case-workspace-design.md:408-410`) y `CaseWorkspace` debe expresar procedencia y momento de validación (`ibid.:243-260`).
- **Por qué es defecto:** Step 1 comprueba resultados de escenarios, pero no prohíbe `datetime.now()`, `getpass.getuser()` o `socket.gethostname()` dentro del resolver, ni repite la misma entrada para exigir el mismo valor. El constructor puede aceptar los tres argumentos y después ignorarlos.
- **Qué lo demostraría:** parchear reloj/usuario/hostname globales para que lancen, resolver dos veces con entradas idénticas y exigir igualdad completa; variar solo cada inyección y exigir que únicamente cambien los campos dependientes.

### H7-12 — MEDIO — El test de `str(error)` no detecta rutas UNC/POSIX, PII ni dos reglas de §10

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:241-244`.
- **Cita literal:** «`str(error)` **nunca** incluye rutas locales», pero el Step solo exige que no contenga «el separador de unidad de Windows».
- **Fuente contrariada:** §16 prohíbe publicar rutas locales y exige logs sin nombres, emails o direcciones (`...dual-case-workspace-design.md:1142-1153`); §10 exige que el mensaje diga que no hubo efecto cuando proceda y no sugiera reintentar contra Drive (`ibid.:719-740`).
- **Por qué es defecto:** `C:/...`, `\\servidor\...`, `/home/...` o una ruta relativa pasan un detector de `:\`; las otras dos reglas ni aparecen en los Steps. Solo se prueba el código de `CapabilityDenied`, no la correspondencia de las doce subclases.
- **Qué lo demostraría:** parametrizar las doce clases con canarios de ruta Windows con ambas barras, UNC, POSIX, nombre, email y dirección; exigir ausencia de todos, código exacto, mensaje de cero efectos en bloqueos y ausencia de cualquier consejo de fallback a Drive.

### H7-13 — MEDIO — El cero-escritura de Task 9 excluye uno de los tres subcomandos prometidos

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:392-398`.
- **Cita literal:** «los tres subcomandos abortan [...] y cero bytes», pero Step 1 pide el death test solo para «`plan` y `apply`».
- **Fuente contrariada:** todo entrypoint mutante debe resolver antes de escribir (`...dual-case-workspace-design.md:182-198`) y la matriz es por entrypoint mutante (`ibid.:1078-1090`).
- **Por qué es defecto:** `reforzar` escribe cobertura, estado y evento en el código actual. Puede omitir el guard y la suite específica de T9 seguir verde. La frase genérica “aplicación a `sala_maquina`” de T10 no enumera los tres callables.
- **Qué lo demostraría:** aplicar la misma matriz/death test a tres invocadores separados (`plan`, `apply`, `reforzar`) y mutar exclusivamente el preflight de `reforzar`.

### H7-14 — MEDIO — “80 ficheros” no es el número de llamadores de `path_for`/`caso_path`

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:283-284`; `PLAN.md:816-820`.
- **Cita literal:** «`path_for` y `caso_path` los llaman 80 ficheros».
- **Fuente contrariada:** `PLAN.md` atribuye el viejo 80 a **cuatro** expresiones: `caso_path`/`settings.casos_root`/`resolve_ref`/`path_for`, no a las dos funciones.
- **Por qué es defecto:** conteo AST del objeto: `path_for` 39 llamadas en 13 ficheros; `caso_path` 112 en 44; unión, 151 llamadas en **55** ficheros (43 de producción y 12 tests). Para las cuatro expresiones tampoco se reproduce el histórico: 192 usos AST en 59 ficheros; conteo textual Python, 399 en 86. El plan usa una medición distinta para justificar la regresión y no entrega inventario de callers.
- **Qué lo demostraría:** script AST versionado que emita fichero, línea, símbolo y clasificación producción/test; su salida debe formar la lista de migración y el guard de `legacy_unresolved`.

### H7-15 — MEDIO — Los comandos no son autoejecutables en el entorno Windows declarado

- **Fichero:línea:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md:249-251,303-306,374-377,448-450`; `CLAUDE.md:129-140`.
- **Cita literal:** `python -m pytest ...` y `--junit-xml=%TEMP%\fd_junit.xml`; el repo declara «Windows + PowerShell» y `.venv/` (`CLAUDE.md:129-134`).
- **Fuente contrariada:** en PowerShell `%TEMP%` no se expande; el argumento observado fue literalmente `--junit-xml=%TEMP%\fd_junit.xml`. El mandato exige basetemp corto por MAX_PATH.
- **Por qué es defecto:** el `python` global de este entorno recogió los tests pero produjo siete errores por `ModuleNotFoundError: dotenv`; la `.venv\Scripts\python.exe` sí ejecutó. Con basetemp bajo el workdir largo, la suite falló en `test_resumen_cuenta_por_estado` (`fuera_de_presupuesto == 1`); el mismo test pasó con `--basetemp=$env:TEMP\fd7_r7_repro_short`, y la suite completa pasó con ruta corta. Además, `%TEMP%` mezcla sintaxis de `cmd.exe` con el shell normativo.
- **Qué lo demostraría:** ejecutar cada bloque literalmente en una PowerShell limpia. Debe usar activación o `.\.venv\Scripts\python.exe`, `--basetemp="$env:TEMP\..."` y `--junit-xml="$env:TEMP\fd_junit.xml"`. La protección de `main` sí está respetada por Task 11 (`:452`) y los cambios de `core/` sí llevan tests; la suite completa incluye los guards documentales.

## Respuestas a las nueve preguntas del mandato

### 1. Cobertura Fase 1 ↔ Tasks 4–11

La correspondencia nominal existe: T4 modelo/capacidades/errores; T5 registro; T6 catálogo y adaptador; T7 resolver; T8 auditoría; T9 primer consumidor; T10 matriz; T11 gobernanza. Lo exigido y no construido de forma ejecutable es: eliminación efectiva del fallback y de todo `mkdir` de raíz (H7-01), retirada de `log_path(case_id)` —el plan lo conserva con `strict=False` hasta Fase 4—, adopción/verificación de checkouts anteriores (H7-09) y el escenario real de fallo externo (H7-08). Los cinco eventos adelantados pertenecen a flujos de Fase 2, pero declarar vocabulario por anticipado no es por sí solo un defecto; sí lo es imponer el total falso 32 (H7-06).

### 2. Orden y dependencias

No hay consumo antes de producción:

| Task | Consume | Produce |
|---|---|---|
| 4 | spec | modelo, capacidades, errores |
| 5 | T4 `CaseRef`/errores | registro |
| 6 | T4 `CaseRef`/errores | catálogo y strict |
| 7 | T4+T5+T6 | resolver |
| 8 | T4 | API de log por workspace/ruta |
| 9 | T4+T7+T8 | consumidor `sala_maquina` |
| 10 | T4+T9 | arnés y aplicación |
| 11 | T4–T10 | documentación/cierre |

Task 4 es realmente la única sin dependencias. T5 y T6 podrían ejecutarse en paralelo después de T4. Task 8 está bien colocada: T4–T7 no escriben en el árbol del caso; T5 solo escribe estado privado. El defecto es de cobertura global, no de posición (H7-01).

### 3. Efecto de D1 y D2 posteriores

D1 deja rancio el plan al repetir explícitamente que Fase 1 elimina rutas inexistentes y `mkdir` de escritores, mientras el plan conserva el default falso. D2 no exige añadir el mutex a T5 ni contradice los campos de `WorkspaceEntry`; el hogar fuera de repo/Drive es compatible. Quedan **SIN VERIFICAR** la forma exacta y el coste de migración porque el plan no decide nombre/layout del fichero. La prueba de riesgo verificable es H7-04: atomic replace no resuelve lost updates y locks por W-code no serializan W-codes distintos sobre un registro agregado.

### 4. Task 6, conteo y compatibilidad

El “80” no se reproduce para las dos funciones (H7-14). `strict=False` mantiene rutas dañinas en `catalogo_documental`, `intake_manual`, `case_manager` y otros escritores. Invertir sin preparación rompe al menos `ensure_case`, que usa `caso_path` como cálculo de destino de alta. El plan necesita separar localización estricta de creación explícita, no elegir entre daño y compatibilidad.

### 5. Posición de Task 8

Está antes del primer consumidor mutante migrado y ninguna Task 4–7 escribe por la ruta de caso equivocada. No hay inversión de orden. Sí quedan escritores existentes fuera de T8/T9; por eso su posición correcta no satisface el criterio global.

### 6. Propiedades nombradas sin prueba mortal

- T4: tabla positiva completa de ocho capacidades; código de cada subclase; rutas UNC/POSIX/relativas, PII y semántica de mensajes.
- T5: atomicidad a través de la API; no escritura in-place; concurrencia; `schema` no soportado; uso del `ts` inyectado sin reloj implícito.
- T6: propagación real de `caso_path(strict=True)`; `estado_compartido` y estrictitud de `CaseCatalog.localizar` de forma directa.
- T7: pureza/determinismo; prohibición de reloj/identidad globales. Además, la excepción «`diagnostico=True`» de `:322` no aparece en las firmas de `:320-321`.
- T8: ubicación junto a bytes (test `...`); retirada efectiva del camino por identidad; cardinalidad correcta del vocabulario.
- T9: cero efectos de `reforzar`; texto real de ayuda/docstring que declara escritura.
- T10: mutantes independientes de cuatro planos; fallo externo e idempotencia.
- T11: la suite completa sí ejecuta gobernanza y el PR sí respeta `main`; no se imputa una ausencia en estos dos extremos.

### 7. Tests que pueden pasar con implementación rota

Confirmados por inspección: H7-03 (atomicidad), H7-05 (`...`), H7-07 (un mutante para cuatro planos), H7-08 (fila sin fallo inducido), H7-10 (tabla parcial), H7-11 (inyecciones ignorables), H7-12 (detector de ruta insuficiente) y H7-13 (`reforzar` omitido).

### 8. Ejecutabilidad en Windows/PowerShell

H7-15 reproduce las tres carencias: intérprete, ruta temporal y sintaxis `%TEMP%`. La suite no está rota: con `.venv` y basetemp corto llegó a 100 % con siete `xfail` y cero `XPASS`. Con basetemp largo dio un falso fallo MAX_PATH. El plan ya acompaña cada cambio de `core/` con tests, Task 11 pide suite completa y leak-scan, y respeta rama+PR; no falta un guard de gobernanza por selección, porque la suite completa los incluye.

### 9. Lo que falta y las siete `xfail`

Faltan una operación/tarea de adopción legacy (H7-09), el tajo de creación explícita + migración de escritores (H7-01), y pruebas ejecutables para servicio externo, reentrada/idempotencia y runtime sin acceso con Drive físicamente intacto (H7-08). La matriz del §14.1 está nominalmente en T7/T10, pero «servicio externo falla» carece de mecanismo.

Corrida protegida de `tests/test_repository_cli_defectos.py`: **7 xfailed, 0 xpassed**. Las siete afectan `scripts/repository_cli.py` —doble titular, rollback sobre lock ajeno, orden del checkin, `moveto` fallido, checkin reentrante, reescritura del log y baseline ignorado— y ningún Task 4–11 modifica ese fichero. No se verificó empeoramiento directo de sus funciones: siguen vivos, no refutados. El riesgo nuevo se concentra en construir autorización sobre un registro fail-open (H7-02) y fijar ahora una forma no concurrente que D2 deba deshacer (H7-04).

## Ejecuciones y cobertura

1. Hash canónico de apertura: coincide.
2. Conteo AST de callers: 151 llamadas de `path_for`/`caso_path`, 55 ficheros únicos.
3. `python` global + siete xfail: **SIN VERIFICAR por ese intérprete**, siete errores de setup por ausencia de `python-dotenv`.
4. `.venv\Scripts\python.exe -m pytest tests/test_repository_cli_defectos.py ...`: 7 xfailed, 0 xpassed.
5. Suite completa sobre scratch con basetemp largo: un fallo reproducible de longitud de ruta.
6. Test aislado con basetemp corto: pasa.
7. Suite completa con `.venv`, `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` y basetemp corto bajo `$env:TEMP`: 100 %, siete xfailed, cero xpassed; los skips declarados dependen de fixtures/servicios no presentes.
8. Las implementaciones y tests nuevos de Tasks 4–11 no existen todavía: su comportamiento dinámico es **SIN VERIFICAR**; los hallazgos sobre ellos atacan la suficiencia del plan y sus tests propuestos.

## Veredicto final

**NO-SHIP**

Recuento: **1 CRÍTICO · 7 ALTOS · 7 MEDIOS · 0 BAJOS**.
<!-- informe-literal:fin:k3wq -->

## 2. Evidencia verificada de no mutación e independencia

- **Objeto:** copia externa de solo lectura en `objeto/`, generada con `git archive HEAD` del commit
  `3f092f8` — sin `.git` y sin red, por construcción incapaz de escribir en el repo.
- **SHA-256 canónico del árbol** (ruta relativa POSIX + bytes, ordenado), 1.057 ficheros:
  `12616082d39bf3d2cc43be50775a76d3ade3a0dd09f4c48f7e44bbcb8b503055`.
- El revisor lo declaró idéntico en apertura y cierre. **El adjudicador lo recomputó por su cuenta**
  al recibir el informe y coincide byte a byte. No es una declaración del revisor sobre sí mismo:
  es una comprobación independiente.
- El revisor trabajó sobre su propia copia (`informe/scratch_objeto/`), no sobre `objeto/`, que es
  lo que el mandato le exigía para poder correr comandos sin tocar el objeto.
- **Independencia:** revisor Codex, adjudicador Claude Code. Restablecida en el sentido del §20 de
  la spec de apertura — no es la situación degradada de R1/R2, donde ambos papeles cayeron en la
  misma familia de modelo.
- **Lo que el revisor sí ejecutó**, y por tanto no es opinión: conteo AST de llamadores, la suite
  completa con `.venv` y `--basetemp` corto, la corrida protegida de `test_repository_cli_defectos.py`
  (7 `xfailed`, 0 `xpassed`) y la reproducción del falso fallo por MAX_PATH con basetemp largo.
- **Lo que quedó SIN VERIFICAR, y así se declara:** el comportamiento dinámico de los Tasks 4-11,
  porque su código no existe todavía. Los hallazgos sobre ellos atacan la **suficiencia del plan y
  de los tests que propone**, no una implementación observada. Y el empeoramiento directo de las
  siete `xfail` de la Fase 0: siguen vivas, no refutadas, y ningún Task 4-11 toca su fichero.
