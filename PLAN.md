# PLAN — FeesDefender

Bitácora de planificación compartida entre Nikolai y Cowork (PC). Edición de
código: solo Claude Code. Aquí van prioridades, decisiones e ideas.

Estado del proyecto y bitácora de cierre de sesión: ver `STATUS.md` (repo).
Backlog técnico (ideas, bugs latentes, mejoras diferidas): ver
`docs/MEJORAS_FUTURAS.md`. Las entradas se promueven aquí cuando tienen
disparador concreto (caso real, bug bloqueante o decisión de Nikolai),
con referencia al número original (`MEJORAS #NN`).
Historial de commits: `git log`. Acceso móvil: app de GitHub (lectura).

---

## 🎯 Cola priorizada  (orden = prioridad; fila #1 = lo que toca ahora)

| # | Ítem | Estado | Gate / disparador | Esf. |
|---|------|--------|-------------------|------|
| 1 | [OCR ciego bajo el sello (`MEJORAS #90`)](#siguiente-ocr-ciego-texto-perdido-bajo-el-sello-de-firma-mejoras-90) | **(e) CERRADA sin rendimiento; (f) pieza A ✅ CONSTRUIDA (PR #193, `88339aa`), pieza B ⛔ bloqueada** | (a)+(b) construidos y verdes. **(e) cerrada 2026-08-01**: lo medido da +0/−6/+288 chars y membrete de fabricante → los 11 restantes **no se corren**. **(f) pieza A sin dependencias; pieza B bloqueada por el lock roto → gate en la Fase 2 de la fila #3.** `MEJORAS #111` **REFUTADA al medirla (2026-08-02)**: el reproceso no destruye prueba → la pieza A ya no tiene ese gate; le queda una decisión de diseño (qué versión conserva el saneamiento) | **A: medio · B: alto** (era «bajo»: mal estimado) |
| 2 | [Infra C — art. 156 LEC](#siguiente-infra-post-valero-roadmap-de-infraestructura-tras-la-sesión-valero-2026-07-14) | pendiente | desbloqueado (quick win) | bajo |
| 3 | [Arquitectura dual del expediente activo](#siguiente-dual-workspace-arquitectura-dual-del-expediente-activo-localdrive) — **su Fase 1 es ahora predecesora de la fila #15** (decisión D1, §24 de la spec de apertura) | spec **rev. 2** + plan **rev. 5**; **Fase 0 ✅ CERRADA** (#170 PR-A + #174 PR-B) y los **dos guards** adelantados (#156 lectura, #160 escritura) | Gate de revisión de la **spec** consumido (3 pasadas). **El plan de la Fase 1 ya pasó la suya: R7, la primera en un mes de vida, corrida ANTES de ejecutarlo — `NO-SHIP`, 15 hallazgos, 15 confirmados, 0 refutados, todos remediados.** El CRÍTICO: el plan no construía la Fase 1 que la spec define, porque conservaba hasta la Fase 4 el mismo fallback que su criterio de salida (2) exige eliminar — y se contradecía a sí mismo, no solo con la spec. El remedio de fondo: el booleano `strict` metía **tres** intenciones en dos valores, y se separa en `localizar()` / `buscar()` / `destino_de_alta()`; la segunda existe por los **27 detectores de ausencia** que midió el adjudicador. **Task 8b nueva** (adopción de checkouts legacy, que el §15 exigía y ningún task construía). Acta: `docs/superpowers/specs/2026-08-24-dual-workspace-fase1-r7-adversarial-review.md`; adjudicación en el §12 del plan. **Tasks 4 y 5 ✅ CERRADOS** (PR #230, `291436d`): el modelo puro —matriz de capacidades por igualdad completa, 8 canarios × 15 clases de error— y el registro privado, `<w_code>.json` con una lista dentro, atómico y **fallando cerrado** (`RegistryUnreadable` en vez de `[]`), con **11 mutantes que mueren cada uno por su propia frontera**. El §10 pasa de 12 a 15 códigos. **Task 6 a MITAD** (PR #231, abierto): inventario AST versionado (el «80 ficheros» del plan contaba menciones, no llamadas: son **43 de producción**), las tres APIs de forma aditiva con 7 mutantes, el alta por la puerta explícita, y **19 detectores + 6 ya-estrictos migrados** — llamadas de producción **95 → 69**, cubo `buscar` **33 → 8**. **El paso 3 se revirtió**: migrar los constructores era redundante —heredan la estrictez al invertir el default, y por el seam correcto— y hacerlo rompía 18 tests que parchean `caso_path` a nivel de módulo para montar el caso fuera de `CASOS_ROOT`. **Cinco fugas del §16 cerradas sin buscarlas**, aparecidas al leer sitio por sitio: cuatro mensajes interpolaban `settings.casos_root` y uno publicaba el `case_id` entero, con la dirección del inmueble dentro. **Task 6: la mitad del LOCALIZADOR ✅ CERRADA, el `CaseCatalog` ❌ NO.** Cerrados los 3 sitios con *seam* y el **paso 5**: el default invertido —radio medido **dos veces**, 377 rotos antes de migrar y **18** después— con el **censo de `strict=False` en producción a CERO**, mejor de lo que el plan pedía. El **guard permanente** no depende de números de línea, porque la lista de trabajo indexada por línea caducó a mitad de la propia migración, y lleva prueba de mutación propia. **Seis fugas del §16 cerradas** por el camino, ninguna buscada. Y el **`CaseCatalog` ✅**, que cierra el **A-8**: medido antes de construirlo, con dos carpetas declarando `id_go: W-DUPLI` el `resolve_ref` devolvía una **sin aviso**, elegida por orden de escaneo — pedías un expediente y el sistema trabajaba sobre otro. Ahora lanza `AmbiguousCase`, cerrando **las dos** puertas. La marca `proyeccion_local` va con la regla porque el §6.3 fabrica dos identidades iguales a propósito. **Task 6 COMPLETO**. **Task 7 ✅ COMPLETO** — `CaseWorkspaceResolver`, la matriz del §7 en una pieza, 23 tests y **18 mutantes, cada uno muerto por su frontera**. La mutación encontró un **defecto real**: la resta de capacidad para el trabajo offline era **inerte** —quitaba `MUTATE_CANONICAL` de un modo que nunca la tuvo—, así que **un checkout offline seguía anunciando `CHECKIN`** y el sistema habría dejado intentar publicar sin Drive. Y dos tests pasaban **por el camino equivocado**: la guarda que decían probar no se ejercitaba. Cinco de dieciocho fronteras no estaban contratadas, en la pieza que decide quién puede escribir sobre qué copia. **Task 8 ✅ COMPLETO** — `intake_log` escribe donde están los bytes (cierra **B0-1**). 7 mutantes por su frontera, incluido el que el plan declaraba **obligatorio**. **7 de 14 llamadores migrados** (contado por AST); el resto queda `legacy_unresolved` y ya no es peligroso, porque `caso_path` es estricto desde el Task 6. **Un test defendía el defecto**: `test_append_event_crea_subcarpeta_00_input_si_falta` exigía que auditar creara `00_Input` —«útil en migraciones»—, que es literalmente la fábrica de expedientes fantasma del bug de W-02ZIIF; la suite llevaba tiempo **verde protegiendo el B0-1**, y ninguna cobertura adicional lo habría encontrado. Y la migración estaba **a medias sin verse**: se escribía junto a los bytes pero `read_events` seguía exigiendo el catálogo, así que con `--case-dir` lo recién escrito era **ilegible** — de ahí `read_events_de`. **Task 8b ✅ COMPLETO** — la adopción explícita del §15, que R7 detectó que faltaba. 12 mutantes por su frontera. **Desviación de fondo respecto del plan:** pedía comprobar que «la identidad del árbol concuerda con `ref`» y **el árbol local no tiene identidad** — `MERGE_EXCLUSIONS` excluye `_caso.md` y el nonce vive solo en el Drive. Eso **es la razón de ser** de la pieza: la máquina no puede probar que esa carpeta sea la del lock vigente, así que `verificar_adopcion` **declara lo que no pudo verificar** y el subcomando lo imprime antes del resultado — sin eso la firma humana sería un trámite. **Task 9 ✅ COMPLETO** — `sala_maquina` resuelve por workspace y acepta `--case-dir` (cierra **A-7**: `local_scratch` tenía diseño y ninguna vía de trabajo). Sobre un caso prestado a otra máquina el motor arrancaba igual y escribía; ahora los **tres** subcomandos abortan con código 2 y **cero bytes**, verificado por hash. 8 mutantes por su frontera, incluido el que el plan exigía —`reforzar` en solitario, R7/H7-13—. **El problema no era técnico sino de SITIO:** ~28 tests parchean `cli.caso_path` para montar casos fuera del catálogo, y la forma que lo respeta es **preguntar primero al catálogo** — si el canon no conoce el caso no hay lock que respetar. Los 190 tests de sala de máquina siguen verdes. Y `plan` dejó de anunciarse como preview inocuo: **escribe**. **Y el cierre del Task 9 destapó lo que tres merges no vieron:** la suite es verde o roja **según la semilla**. Con la 31337, cero fallos; con la **777, ocho** —todos en `test_sala_maquina_ejecutar.py`, todos `CASE_LOCKED` con un timestamp de fixture—. La causa raíz no era del Task 9 sino de debajo: **`tmp_casos_root` hacía `importlib.reload(core.config)` al entrar y nunca al salir**, así que el módulo se quedaba apuntando al `tmp_path` de ese test para todo lo que corriera después; `test_repository_checkout` dejaba ahí un `EV-2026-001` **prestado** y los tests de sala de máquina —mismo case_id genérico— se encontraban el caso ajeno con lock. Una mina latente que el Task 9 pisó **por ser el primero en preguntar al catálogo**, lo que la convierte en gate de los Tasks 10-11 y de la Fase 3: toda pieza nueva que consulte el catálogo pisaría la misma clase. Arreglada la fixture (restaura al salir) y hermetizado además `test_sala_lectura_md_path_usa_sufijo_sha`, que pasaba solo cuando el orden lo colocaba después de quien creaba su caso. **Verde con tres semillas** (777, 31337, 555): 3.331 tests, 0 fallos. **La lección operativa: un verde de una sola corrida no dice nada sobre orden — dos semillas antes de cerrar.** Riesgo anotado y NO arreglado: los ~28 tests que parchean `cli.caso_path` como override explícito quedan **por debajo** del estado ambiental del catálogo, porque `_resolver_workspace` pregunta primero al canon; hoy no colisiona porque los ids reales son `BaXXX - … - (W-XXXXX) - tipo`, pero es precedencia por azar de nombres y el **Task 10 debería contratarla**. **Tasks 10 y 11 ✅ COMPLETOS — la Fase 1 CIERRA.** La matriz del §14.1 vive **una vez como datos** en `tests/_matriz_contractual.py` y `sala_maquina` corre **las nueve filas, ninguna declarada no aplicable**; los **cuatro planos** del §3.2-bis tienen cada uno su mutante, y cada mutante muere **por su plano** — el aserto comprueba que el mensaje nombra el suyo y **no** el de los otros tres (R7/H7-07). Para que eso sea posible el plano 2 se define como «el canon **alrededor** de la copia de trabajo»: con `CASOS_ROOT` entero, en modo `drive_active` el árbol vive dentro del canon y un mutante del plano 1 mataría también al 2 — el mutante que no prueba lo suyo. **Tres desviaciones del Task 10 tal como estaba escrito, todas del mismo tipo que R7 castigó siete veces —una firma que no puede expresar lo que su prosa promete—:** `invocar` recibe `CaseRef | Path` y no `CaseWorkspace | Path`, porque **tres filas** (registro ausente, nonce divergente, runtime sin acceso) se resuelven con excepciones que el resolver lanza sin rama de `diagnostico`, así que **no existe workspace que las represente**; `assert_sin_efectos` conserva su firma literal pero `antes`/`despues` pasan a ser instantáneas de tres planos, porque como hashes de árbol solo podía comprobar dos de los cuatro que promete; y el plano 3 exige `contador_externo` **o** un motivo por escrito, porque `sala_maquina` no llama a ningún servicio externo mutante y sin esa exigencia el `== 0` habría pasado por vacío en todos los consumidores. **Dos hallazgos que el Task 10 destapó por mirar al entrypoint y no a la pieza:** (a) `_resolver_workspace` pasaba **`drive_accesible=True` literal**, o sea que toda la rama offline del §7.2.9-10 —diseñada, con tests unitarios en el resolver— era **código muerto en producción** y la fila 8 solo era inducible mintiendo; cerrado con `_drive_accesible()` (`FEESDEFENDER_OFFLINE=1`). **Y la segunda condición que le añadí duró una corrida:** mirar también `settings.casos_root` divergía de la fuente que usa el catálogo y daba offline en cualquier clon sin `data/CASOS` — la mataron tres tests en la primera suite completa. (b) **223 tests en 17 módulos** seguían dejando `core.config` apuntando a su `tmp_path`: arreglar `tmp_casos_root` en el 65º había tapado **un pozo de diecisiete**. Cerrado con un guard `autouse` en `conftest`, y la restauración repone además `CASOS_ROOT` porque el orden de desmontaje **no** era el que supuse —lo desmintió el primer test—. **El riesgo que el 65º dejó anotado queda contratado:** la precedencia catálogo > `caso_path` parcheado tiene ahora test en las dos direcciones, con mutante que la invierte y muere. Cabo suelto del 65º cerrado: `scripts/abrir_caso.py` pasa a `localizar`. **Verde con dos semillas** (777 y 31337): 3.358 tests, 0 fallos, 0 errores, 7 `xfailed`, 0 `xpassed` — los +27 sobre el 65º son exactamente los tests nuevos, contados. **R8 corrida sobre el DIFF y adjudicada** (`NO-SHIP`, 9 hallazgos, **9 confirmados, 0 refutados**; acta `…-tasks10-11-r8-adversarial-review.md`, adjudicación en el §14 del plan). Los dos ALTOS son el mismo defecto que el Task 10 venía a impedir, cometido **dentro** del Task 10: las filas bloqueadas admitían **cualquier** salida != 0 —un `typer.Exit(99)` de otra guarda dejaba verde la fila que dice aislar el `LOCK_MISMATCH`— y la fila del fallo externo no miraba canon, estado local, baseline ni códigos de salida, así que un entrypoint que **se tragara el fallo y devolviera éxito** quedaba rotulado «aborto idempotente». Los dos los demostró el revisor **ejecutando mutantes**, no leyendo. Remediados con `codigo_error` por fila + captura de `stderr`, baseline de planos en la fila 9, y seis mutantes nuevos. R8 destapó además que la capacidad offline **no funcionaba por su vía principal** (H8-04, verificado en vivo: con el checkout delante, «Caso no encontrado») — y arreglarlo **reabría** el defecto que la mutación del Task 7 había cerrado, porque `_solo_local` no recibía `drive_accesible` y un checkout sin Drive volvía a anunciar `CHECKIN`; cerrado en el mismo commit. **Siguiente = Fase 2** (los 7 defectos del frontal), que además es el gate de la pieza B de la fila #1 y de los Planes 2-5 de la fila #15. Los **7 defectos del frontal siguen vivos**: reproducidos en `xfail`, se arreglan en la Fase 2. **Absorbe Infra B (scratch)**: `local_scratch`, `--case-dir` y `promover` son piezas de aquí. **Nota cruzada (2026-08-01): su Fase 2 es ahora el gate de la pieza B de la fila #1** — el saneamiento de los segmentos duplicados no puede correr mientras `test_defecto_doble_titular` siga en `xfail`, porque una copia local stale resucita los slugs retirados | alto (5 fases restantes; la Fase 0 ya hecha) |
| 4 | [MCP sudespacho F1](#siguiente-mcp-sudespacho-mcp-sudespacho-crm-del-despacho--f1-lectura-spec-hecho-plan-pendiente) | spec lista | gates de despliegue | alto |
| 5 | [Drive-disco: pasos 5-7 + Claude Code](#siguiente-mcp-drive-disco-pasos-5-7-diferidos) | ✅ desplegado | resto pasivo: check Modo 1 en caso real | medio |
| 6 | [abrir-caso F3-judicial](#abrir-caso--f1--f2a--f3-ac-mergeadas-f2b-aparcada-f3-judicial-pendiente) | disparador confirmado 2026-07-22 | plan concreto listo (4 piezas, ver bloque) | medio |
| 7 | [Google MCP F4 (Calendar)](#siguiente-google-mcp-f1-lectura--mergeada--f2-escriturapermisosnavegación--mergeada--f3f4-pendientes) | diferida | disparador | medio |
| 8 | [Intake email — filtro de exclusión de ruido](#siguiente-intake-email-filtro-exclusión-de-ruido-administrativo-y-cruzado) | parcial (2/4) | disparador: W-02VUDR (fuga cruzada de 7 casos ajenos + cartera de litigios) | medio |
| 9 | [Vista procesal en `05_Procedimiento`](#siguiente-vista-procesal-vista-procesal-del-expediente-en-05_procedimiento) | piezas 1-2 ✅ (#137, #140); spec v3.1 con 2 revisiones consumidas | pieza 3 **bloqueada** por la fila #1 (OCR ciego); plan de la pieza 4 por reescribir | medio |
| 10 | [`.doc` → LibreOffice headless](#siguiente-doc-libreoffice-doc-binario-sin-md-ni-ocr-conversión-libreoffice-headless) | pendiente | disparador: W-02MA0R, la demanda del ordinario solo existe en `.doc` sin gemelo PDF. **Sin gate, y el único ítem de la cola donde un documento es hoy ILEGIBLE del todo** (`.doc` → `sin_soporte`: ni MD ni OCR) — ver «Por qué es el siguiente paso que mejora la LECTURA» en su bloque | bajo |
| 11 | [Cableado del pipeline de correo (`MEJORAS #68`)](#siguiente-cableado-correo-cableado-del-pipeline-de-correo-encadenar-la-atomización-resto-de-mejoras-68) | casillas 1-2 ✅; casilla 3 **decidible, sin gates** (#98 cerrado, PR #155) | solo queda la decisión de Nikolai: `--extraer-adjuntos` a default `True` mueve la superficie de dedup de todo intake futuro | bajo |

| 12 | [La firma no es intercalada: falso positivo que bloquea la Capa B](#siguiente-sandwich-firma-la-firma-no-es-una-respuesta-intercalada) | ✅ **CERRADO** — PR #164 (`aaf7dc1`) | queda su cola: `MEJORAS #109` (el síntoma original sigue sin explicar) y borrar el corpus de prueba | bajo |
| 13 | [Presupuesto explícito de proceso](#siguiente-presupuesto-proceso-cuánta-gobernanza-se-compra) | ✅ **DECIDIDO el 2026-08-26** (PR #249, `26ac6a7`) | **Opción B: el número de rondas lo fija el RADIO DE DAÑO.** Dos si la pieza decide quién escribe o puede destruir datos de cliente (una sobre el diseño, una sobre el diff); una en todo lo demás. **Techo duro: nunca una tercera sobre la misma pieza sin autorización expresa de Nikolai.** Escrito en `CLAUDE.md` §«Cuántas rondas». El dato que lo decidió: el mutex de V1 recibió **cuatro** rondas —660 líneas de producción contra 1.562 de test y 2.376 de plan y actas, seis a uno—, las cuatro devolvieron defectos reales y **ninguna volvió limpia**, así que «hasta que una ronda vuelva sin críticos» **no converge**. Lo que sí se midió: los defectos que habrían entrado parando antes no tenían consecuencia práctica para tres abogados que no trabajan en paralelo. **El coste de la ronda es cierto; el del defecto, no.** | bajo |
| 14 | [Desplegar en Cowork las skills ya construidas](#siguiente-reimport-skills-lo-construido-que-no-ha-llegado-al-equipo) | pendiente — **acción manual de Nikolai**; ningún test la cubre | sin gates. Disparador: `organizar-sala-lectura` va por **v1.14 en el repo** y Paola/Ana/Sergio ejecutan la **v1.12** | bajo (una tarde) |
| 15 | [Apertura integral + piloto W-02Q38C](#siguiente-apertura-integral-apertura-completa-sobre-componentes-existentes) | spec única **rev. 8**; **cinco rondas adversariales corridas y adjudicadas** (R3 §20, R4 §22, R5 §23) y **las cuatro decisiones tomadas + write-set enumerado** (§§24-25). **R5: `REQUIERE-REVISION`, 5 confirmados + 1 añadido por el adjudicador.** El §23 **detiene el bucle de revisión del diseño**: tres de los cinco no son remediables en prosa —el discriminante de V1 ES el dueño de secuencia, la regla de estado cuelga del mutex, y el write-set es un barrido de código—; la rev. 7 corrige solo los errores; **R3 adjudicada el 2026-08-24 por Claude Code: `NO-SHIP`, 7 confirmados, 0 refutados** (§20). La **rev. 5 fija la primera vertical en Drive + pull de Sudespacho → intake → sala de máquina** (§21, decisión de Nikolai): H3-07 sale de alcance, H3-03 y H3-06 quedan acotados, los tres críticos de mecánica siguen íntegros y **`MEJORAS #120` entra en V1**. Piloto abierto, no cerrado | **decisiones TOMADAS** el 2026-08-24 por delegación de Nikolai (§24): D1 la Fase 1 de la fila #3 **precede a V1**; D2 mutex = lockfile local `O_EXCL` con namespace por W-code en el registro de D1, lease renovado, ámbito una máquina; D3 discriminante y dueño de secuencia = **`--modo v1`** del entrypoint existente (no subcomando: 103 referencias en el repo); D4 `fallo` bloquea, `parcial` → `preparado_con_pendientes`, y la poda archiva en vez de borrar. **Write-set enumerado** (§25): 27 clases, 6 productores, **solo 2 consultan el guard**. **Plan TDD troceado en 5** (V1 no es un subsistema y dos contratos no existen aún, §25.5): [Plan 1 — modo `v1` y puertas negativas](docs/superpowers/plans/2026-08-24-apertura-v1-plan1-modo-v1.md) **✅ EJECUTADO** (PR #229, `93810a0`) con su **R6 sobre código adjudicada**: `NO-SHIP`, 9 confirmados / 0 refutados, todos remediados — el CRÍTICO era `--force` creando una carpeta sombra contra el criterio 33. Era el único que no dependía de la Fase 1. [Plan 2 — la primitiva de mutex de D2](docs/superpowers/plans/2026-08-25-apertura-v1-plan2-mutex.md) **✅ EJECUTADO Y MERGEADO** (PR #247, `ff700f3`), con **cuatro rondas adjudicadas**: R10 sobre el plan ANTES de escribir código, y R11-R13 sobre el diff. R10: `NO-EJECUTABLE`, **11 confirmados / 0 refutados**, 4 críticos. El que justifica la ronda: el test que el plan presentaba como su prueba rigurosa —dos procesos reales— **pasaba en verde con la exclusión entera eliminada**, y el revisor lo ejecutó para demostrarlo; el padre terminaba de adquirir **antes** de lanzar al hijo, así que no había carrera. **Tres afirmaciones mías eran falsas**: que `filelock`/`psutil` «se usaban sin declarar» (cero imports), que el mutex «hereda» la barrera de ubicación del registro (nunca construye uno) y que el reloj de producción es `now_iso()`, que devuelve **naïve** — 65 usos frente a 6 de `now_iso_utc`, así que quien cablee la primitiva debe **pasar el reloj con offset explícitamente**. **Dos decisiones que la ronda obligó a tomar:** la primitiva **no es `O_CREAT|O_EXCL`** sino bloqueo nativo (en Windows `filelock` usa `msvcrt.locking`), y se declara en vez de adjudicarla por el nombre de la librería; y `psutil` **desaparece**, porque el propietario resultó ser **diagnóstico** —la titularidad la decide el nonce— y no hacía falta un `boot_id` estable. **Y lo que solo apareció al ejecutar:** la carrera de 12 rondas encontró un defecto real en mi comprobación de contención — `Path.resolve()` consulta el disco y devuelve distinto según el directorio exista o no, así que con dos procesos creando la raíz a la vez rechazaba una ruta legítima (reventó en la ronda 8); ahora es léxica. El **mutante del Task 7 estaba mal apuntado** y mataba tres tests por un `RuntimeError` de montaje, no por contrato. El §10 pasa de **15 a 18 códigos**. **3.577 tests, 0 fallos con dos semillas (777 y 31337); 17 mutantes muertos, cada uno por su frontera.** **Lo que R11-R13 enseñaron no es un defecto sino un patrón mío:** las cuatro rondas encontraron **cuatro veces la misma propiedad mal cerrada** —«el error de reloj no puede agotar el lease que protege», que es una *relación entre dos magnitudes*— porque cada vez remedié el caso que el informe describía y no la propiedad de la que era ejemplo. De ahí la pregunta que ataja, ya en `CLAUDE.md`: **«¿de qué frontera es esto un ejemplo?»**. **Nadie llama todavía a la primitiva: el mutex existe, está probado y NO protege nada en producción.** [Plan 3 — la costura de escritura](docs/superpowers/plans/2026-08-26-apertura-v1-plan3-write-set.md) **troceado en 3A/3B/3C** el 2026-08-26 (~85 primitivas de escritura son demasiado diff para una sola ronda), con **una ronda de diseño sobre el documento común y una de diff por tanda: cuatro, sin tercera sobre ninguna pieza**. Diseño: una **costura única** que exige el mutex ANTES de consultar el guard —porque el guard escribe su propio evento al desviar— y devuelve **un** destino; debajo, **reentrancia revalidada** para que un `tomado()` anidado no sea `CaseBusy` contra uno mismo; los entrypoints adquieren y `core/` exige. **No se toca `case_mutex.py`**: cuatro rondas y 17 mutantes, editarlo es reabrirlas. **14 fronteras enumeradas, una por mutante.** Dos correcciones nacidas de medir: la poda **NO** pierde datos de cliente (poda derivados regenerables, `00_Input` intacto), así que 3C no se adelanta; y la costura **no rechaza en modo `libre`**, porque hacerlo convertiría cualquier camino sin cablear en un fallo duro de las vías de intake de `streamlit_app.py` —la herramienta diaria del equipo—: el hueco se **cuenta** con un censo cuyo tope solo baja, y el rechazo entra cuando llega a cero. **R14 sobre el diseño corrida y adjudicada ANTES de escribir código: `NO-EJECUTABLE`, 9 hallazgos, 9 confirmados, 0 refutados** (3 críticos), todos remediados en la rev. 2; acta `…-plan3-r14-adversarial-review.md`, adjudicación en el §0 del plan. **Siete de los nueve son ejemplos de UNA propiedad —«el nombre de una cosa no es la cosa»—:** el W-code del nombre de carpeta por la identidad canónica de `meta.id_go`, la ruta canónica por el destino efectivo al hashear, el W-code solo por la clave `(raíz, W-code)` del lock, un `Path` devuelto por la escritura efectuada, y el primer adquirente por el último usuario que sale. Las cuatro primeras en el espacio, la quinta en el tiempo. **El CRÍTICO:** el mutex se indexaba por el nombre de carpeta cuando el catálogo considera canónico `meta.id_go` y el docstring de `CaseRef` dice que el nombre «es una presentación y no basta como identidad» — dos lockfiles para un expediente, los dos procesos creyéndose protegidos. **Y el que más dice de cómo fallo:** la rev. 1 se autoconcedía «cuatro rondas en vez de seis» contando R14 como ronda de diseño de tres tandas cuando solo diseña 3A; retitulado a **Plan 3A**, y 3B/3C tendrán la suya cuando exista su diseño. **Dos de los nueve eran defectos que yo mismo había introducido horas antes al autorrevisar** — entre ellos un evento imposible de emitir (`INTAKE_EVENTS` es cerrado) que además recurría por la costura. Corregidas dos cifras que no eran reproducibles: **43 `now_iso(` frente a 5** `now_iso_utc(` (mi «7» contaba imports) y **80 primitivas sobre los 11 ficheros** que la tabla nombra (mi «~85» salió de 8). **Los 7 tasks EJECUTADOS** (el 6 parcial) y **R15 sobre el diff corrida y adjudicada**: `NO-SHIP`, **10 hallazgos, 10 confirmados, 0 refutados** (2 críticos), **5 remediados y 5 declarados**; acta `…-plan3a-r15-adversarial-review.md`, adjudicación en el §6 del plan. **Esta ronda EJECUTÓ** —dos procesos, dos hilos, junction, alias 8.3, un hijo matado— y de ahí salieron los dos críticos: no se deducen leyendo. **Los dos son reincidencias mías.** H15-01 es la **tercera** aparición de la propiedad que R14 nombró: el alta admitía dos identidades para un caso, reescribía `meta.id_go` y devolvía el mismo directorio — R14 la cerró en la costura y yo remedié *ese sitio* en vez de la propiedad «todo camino que fije identidad comprueba concordancia». H15-02 es la **pérdida silenciosa de R11 reaparecida en la capa que construí encima de su arreglo**: cerrarla para el titular no la cierra para quien le pide prestado, y ninguno de mis diez mutantes la tocaba porque todos medían la vida del *lock* y no la *noticia* de cada préstamo. **No se pide tercera ronda:** el techo duro la prohíbe sin tu autorización y lo que queda son promesas estrechadas y deuda nombrada, no garantías falsas. **Suite 3.672, 0 fallos con dos semillas.** **Estado real de 3A:** el mutex protege lo que pasa por `abrir_caso` y `sala_maquina`, y la custodia sigue el destino efectivo; **las 83 escrituras del censo siguen fuera de la costura** (el +1 sobre 82 es deuda declarada de la fila #13, que el propio trinquete cazó). **La fila #5 DECIDIDA y las tandas 3B/3C DISEÑADAS Y REVISADAS, ninguna construida (2026-08-26).** **D5, decidida y autorizada por Nikolai: la ficha acompaña a los bytes** — si el guard desvía el pull a la bandeja, el sello de los ids de Drive **no** se estampa en la ficha canónica; queda aplazado **con aviso en pantalla** (lo eligió él sobre la alternativa silenciosa). Las otras dos salidas se cayeron por medición: estampar igual es mutar el canon durante un checkout, y abortar el pull contradice al guard de 3A, que para esos mismos bytes ya decidió desviar. **Lo medido antes de decidir, y peor que la recomendación del 71º:** `register_drive_ev` no muta el `_caso.md`, lo **reconstruye** con `_write_case_index` (el constructor del alta), así que **borra el cuerpo y toda clave ajena a `CaseMeta` en cada corrida, sin necesidad de carrera**; y con carrera, pisa el lock de otra máquina. Y **no es un sitio, son tres** (`register_expediente`, `register_drive_ev`, `cache_drive_folder_info`), propagados por un comentario mío que afirma lo contrario y **nombra a uno como modelo**. **Tres planes escritos y tres rondas de DISEÑO corridas y adjudicadas, antes de una línea de código:** [3A-bis — la fila #5](docs/superpowers/plans/2026-08-26-apertura-v1-plan3a-bis-fila5.md) (**R16 `NO-EJECUTABLE`, 13/13 confirmados, 4 críticos**), [3B — los derivados](docs/superpowers/plans/2026-08-26-apertura-v1-plan3b-derivados.md) (**R18 `NO-EJECUTABLE`, 15/15, 4 críticos**) y [3C — la poda y el archivado](docs/superpowers/plans/2026-08-26-apertura-v1-plan3c-poda-archivado.md) (**R20 `REQUIERE-REVISION`, 13/13, 3 críticos**). **41 hallazgos, 41 confirmados, 0 refutados**, las tres rondas EJECUTANDO sondas y suite. Actas en `docs/superpowers/specs/*-r1{6,8}-*` y `*-r20-*`; adjudicaciones en los §7, §6 y §5 de sus planes. **NO se escribió código, y ése es el resultado correcto de una ronda de diseño**: los tres diseños necesitan rev. 2. **El patrón de las tres, que es el hallazgo de fondo: el diagnóstico medido aguanta —el revisor reprodujo las mediciones— y las piezas que prometían cerrarlo, no.** Entre otras cosas las tres rondas encontraron **tres guardas INERTES**, escritas el mismo día por la misma mano: `es_copia_prestada` (H16-01), `agregado=True` sobre `protocolo` (H18-02) y `clase="derivado"` como rechazo (H20-03) — tres condiciones que **no pueden ser falsas/verdaderas nunca**. De ahí la regla nueva: **al enunciar una condición de guarda, comprobar que puede tener el otro valor**; es una sonda de tres líneas y hoy habría ahorrado tres críticos. **H16-01 no es de estos planes y es el hallazgo más grande:** `es_copia_prestada` devuelve `False` **siempre** en producción —`buscar()` solo mira bajo `CASOS_ROOT` y el registro solo contiene rutas fuera de él—, y **nueve tests verdes lo defienden** porque su fixture registra **el canon** como `local_path`, esquivando al resolver que lo prohibe. Reproducido por mí. Va a `docs/MEJORAS_FUTURAS.md` **#124** con su medición y su condición de cierre. **Y H18-01 limita lo que 3A puede reclamar:** `deposito(ref, …)` no transporta `CaseWorkspace.working_root`, así que la costura mergeada en #251 **solo sirve para el canon**. **Cifra rancia corregida:** el plan de 3A decía «las 93 escrituras del censo» en dos sitios; el `TECHO_CENSO` vivo es **83**. **Siguiente:** rev. 2 de los tres diseños, en el orden 3A-bis → 3B → 3C, con los puntos enumerados en cada adjudicación; y **`MEJORAS #124` decide antes quién contesta «¿cuál es la copia de trabajo?»**, porque 3A-bis y 3B cuelgan de esa respuesta. **ORDEN INVERTIDO el 2026-09-03 por decisión de Nikolai: se cablea PRIMERO (Plan 5) y 3B/3C quedan aplazados con cuatro deudas declaradas.** El plan del cableado está escrito y pendiente de R-A; el Plan 4 (orden durable, frescura, rondas) sigue sin contrato escrito, y solo su parte de re-ejecutabilidad tras un corte entra en el cableado, apoyada en la idempotencia que cada etapa ya tiene | medio-alto |
| 16 | [El marketplace del plugin no está publicado en git](#siguiente-marketplace-plugin-el-marketplace-despacho-tyukhay-no-está-publicado-en-git) | **E.6.1 ✅ DECIDIDO el 2026-08-25: repo dedicado, privado, remoto SSH.** De los 3 pasos previos quedan **uno**: regenerar el bundle **pegado al push**. El de `__pycache__` era **premisa falsa** (ya se excluía desde `60fee81`) y el **control de secretos ✅ ejecutado**, que es el que encontró los dos defectos de portabilidad reales —el intérprete absoluto del `run_server.bat` y `dxt-build/` viajando— **ya arreglados con contrato y tres mutantes** (PR #245, `583b705`). Después, E.6.2 y E.6.3, mecánicos. **Todo lo que queda es de Nikolai:** crear el repo privado y empujar. Ningún test cubre la publicación y ningún guard la detecta | sin gates técnicos. **Disparador: es el único punto vivo de la migración al perfil `procesal@` —decisión D4, firmada el 2026-08-13 y nunca ejecutada— y hoy la vía de mantenimiento del plugin NO EXISTE.** El propio runbook manda actualizar el plugin en el perfil 2 con `/plugin update` «sin puente», y eso es imposible mientras el marketplace sea de tipo `directory` a un `dist\plugin` gitignorado: cualquier cambio del plugin obliga a rehacer el puente entero (Bloques 0, A.1-A.6, A.8 y D.1). Verificado el 2026-08-25 que la entrada rota está **también** en `tnm33`, no solo en el perfil procesal | bajo |
| 17 | Cuatro entrypoints escriben en el expediente sin pedir el mutex (`MEJORAS #126`) | pendiente | **disparador real: apertura de W-02X1WJ el 2026-09-01.** El mutex SÍ está en `abrir_caso.py:649` y `sala_maquina.py:486`; NO está en `export_label_emails.py`, `atomize_emails.py`, `sync_sudespacho.py` ni `crm_ficha.py` (0 referencias cada uno). Los dos primeros escriben en `00_Input` mientras `apply` lo lee — el escenario de `[APER-39]`, con coste medido de ~1h40 de OCR repetido —, y `pull` es el paso que `[APER-37]` manda ejecutar JUSTO antes del `apply`. En esta apertura la regla la sostuve yo a mano tres veces. **Radio de daño: decide quién escribe → dos rondas** | bajo |
| 18 | `fecha_de_nombre` devuelve un centinela *truthy* y desactiva en silencio el paso de los espejos (`MEJORAS #131`) | pendiente | **disparador real: sala de lectura de W-02X1WJ, 2026-09-01.** `preclasificar.fecha_de_nombre` devuelve la cadena `"0000-00-00"`; el filtro `if not f["fecha"]` dio **0 candidatos** y dejó sin ejecutar el Paso 1-bis.d, que la skill marca como NO opcional porque saltárselo dejó 7 binarios sin fechar en W-02VUDR. Corregido el filtro: **47 candidatos, 27 fechas recuperadas**. Falla hacia el lado que parece que funciona —sin excepción y con un informe que dice «0 sin fecha»—, y degrada el timeline, que es el producto entero de la sala de lectura | bajo |
| 19 | Adoptar el CANON como copia local está permitido, y desactiva el desvío del guard (`MEJORAS #136`) | ✅ **RESUELTO** (2026-09-02) | **disparador: R21, 2026-09-02.** `repository_cli adoptar <ruta del canon>` era **ACEPTADO**, y desde ahí el intake escribía sobre el expediente **sin desviar** con el caso `prestado`; el resolver daba `LOCAL_CHECKOUT` con `working_root` = canon. La invariante «el registro no contiene rutas del catálogo» la aplicaba **un lector** y ningún escritor. **Dos rondas sobre el diff, las dos `NO-SHIP`, 16 hallazgos y 16 confirmados** — R22 (9) y R23 (7, autorizada por Nikolai). **Los dos hallazgos que más enseñan son míos:** R22/H22-04 fue una **pérdida de datos que introduje al arreglar** (filtrar al leer con un booleano que falla cerrado, y reescribir desde la vista filtrada), y R23/H23-01 fue la **misma frontera mal cerrada por cuarta vez** — contraté «*junction* → raíz» y la frontera era «cualquier alias cuyo destino físico caiga dentro del catálogo». El remedio de fondo no fue parchear sino **retirar** mi ascenso por ancestros y dejar la resolución física a `os.path.realpath`. Documento con las dos adjudicaciones: [`…-mejoras-136-el-canon-no-es-una-copia.md`](docs/superpowers/plans/2026-09-02-mejoras-136-el-canon-no-es-una-copia.md). **14 mutantes, 14 muertos, reproducible** (`python -m tests._mutantes_mejoras_136`). Quedan fuera, **preexistentes y con su medición**, `MEJORAS #137` y `#138`. **Cobertura de revisión de lo remediado tras R23: ausente** | bajo-medio |

> **Filas 13 y 14 añadidas el 2026-08-03 al final de la cola a propósito: no reordeno prioridades
> ajenas.** Las dos son baratas y una degrada a terceros hoy — dónde encajan de verdad lo decide
> Nikolai. Origen: `docs/superpowers/handoffs/handoff-2026-08-03-formacion-git-nikolai.md`.

> **Fila 15 añadida el 2026-08-15 por disparador real y decisión expresa de Nikolai.** Se conserva
> al final para no reordenar la cola sin una decisión específica de prioridad.

> **Fila 16 añadida el 2026-08-25, también al final y por el mismo criterio: no reordeno la cola
> sin decisión de prioridad.** Es la promoción del §2.2 de
> `docs/superpowers/handoffs/handoff-2026-08-14-migracion-procesal-continuacion-tnm33.md` — el
> último punto abierto de la migración al perfil `procesal@`. Los otros dos que el handoff dejaba
> pendientes (F.4.1 y E.1) se cerraron al medirlos ese mismo día, así que no se promueven.


> **Filas 17 y 18 añadidas el 2026-09-01, al final y sin reordenar la cola,** por el mismo criterio que las anteriores. Las dos salen de la apertura de W-02X1WJ y las dos comparten un rasgo que justifica promoverlas y no dejarlas en backlog: **fallan en silencio**. La 17 no levanta error porque nadie pide el lock; la 18 informa «0 sin fecha», que es exactamente lo que uno querría leer. Las otras ocho de esa tanda (`MEJORAS #127-#130`, `#132-#135`) se quedan en backlog: o tienen su gate en un plan ya en cola (la #127 en el Plan 5 de la fila #15, la #135 en la casilla 3 de la fila #11) o esperan disparador.
> Detalle de cada ítem en su bloque `[SIGUIENTE-*]` más abajo. Backlog sin
> promover: `docs/MEJORAS_FUTURAS.md`. Ledger de cerrados: `## Cerrados` (final).

---

## [SIGUIENTE-APERTURA-INTEGRAL] Apertura completa sobre componentes existentes

*Fila #15. Disparador: apertura real de W-02Q38C y decisión expresa de convertir sus fallos
operativos en el contrato único de apertura.*

La spec canónica es
[`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`](docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md).
Absorbe y adjudica lo vigente de los diseños de 2026-07-09 y 2026-07-18 y del runbook, sin
crear specs separadas por CRM. La decisión de arquitectura es completar y cablear primero
`scripts.abrir_caso`, `scripts.crm_ficha` y los motores existentes; solo una prueba E2E que
demuestre huecos residuales puede justificar un coordinador nuevo.

R1 y R2 devolvieron **NO-SHIP** con diecisiete hallazgos, todos confirmados contra las
fuentes. Las adjudicaciones excepcionales las firma Codex por indisponibilidad de Claude
Code. La independencia es más débil porque revisor y adjudicador pertenecen al mismo
modelo/familia. La rev. 3 incorpora los remedios, pero **no se autoaprueba y sigue pendiente
de R3**. El contrato hermano `FeesDefender-crm` v3.7, commit `8bc09ea`, autoriza antes de la
medición la excepción temporal de Nikolai sin entrega probatoria.

Actas custodiadas y todavía vinculadas a este ítem abierto:
`docs/superpowers/specs/2026-08-15-apertura-integral-r1-adversarial-review.md` y
`docs/superpowers/specs/2026-08-15-apertura-integral-r2-adversarial-review.md`.

**Estado del piloto:** el expediente extrajudicial y sus relaciones básicas existen en
Sudespacho; la ficha del contrario se corrigió con nombre completo, apellidos separados,
domicilio postal completo y textos normalizados. Los datos personales y los documentos del
caso permanecen fuera de Git. No se declara la apertura cerrada: `_caso.md` todavía no se
sincroniza por el camino común y el paquete probatorio completo de LeadHub sigue limitado por
la capacidad actual del repositorio hermano `FeesDefender-crm`.

**R3 corrida y adjudicada (2026-08-24).** Revisor Codex por CLI sobre una copia externa del
árbol (`git archive`, solo lectura por construcción); adjudica Claude Code contra la fuente, con
lo que la independencia debilitada de R1/R2 queda restablecida. Veredicto `NO-SHIP`: **7
hallazgos confirmados, 0 refutados** —3 CRÍTICOS (gate de workspace incompatible con el contrato
dual, mutex sin primitiva, protocolo durable no recuperable), 3 ALTOS (nadie encadena el flujo,
regresión de frescura, punto fijo no auditable) y 1 MEDIO (retención postal sin ejecutor). Acta:
`docs/superpowers/specs/2026-08-24-apertura-integral-r3-adversarial-review.md`. Adjudicación: §20
de la spec. La ronda cerró además dos `SIN VERIFICAR` heredados —la autorización v3.7 del repo
hermano es **cierta** (`8bc09ea`, ancestro de `main`)— y ejecutó la caracterización del lock
(7 xfailed, 0 xpassed): los siete defectos siguen vivos.

**Alcance estrechado (rev. 4→5, 2026-08-24, decisión de Nikolai).** La primera vertical es
**V1 = identidad → esqueleto → Drive E&V + pull de Sudespacho + atomización local del correo ya
depositado → intake con custodia → sala de máquina**, con `--crm skip` como **requisito ejecutable**
(no convención: hoy el default es `api`) e invariante sin absolutos —cero mutaciones de datos, de
comunicación y de efectos remotos no idempotentes del caso; el refresh de token de `rclone` queda
declarado—. Salen
diferidos —no derogados— el alta CRM, `crm_ficha` completa, el enriquecimiento postal, Gmail,
LeadHub, la sala de **lectura**, la viabilidad y el archivo multiefecto; el reparto por vertical y
los 24 criterios de aceptación que quedan en V1, en el §21 de la spec. Con las tres fuentes
documentales dentro, V1 **respeta entero** el gotcha del runbook (atomizar y pull antes del OCR).
Lo que sigue faltando: V1 no **descubre** correo, así que un caso cuyo material siga en Gmail sin
depositar queda `preparado_con_pendientes` hasta V3, nunca `completo` — **corregido tras R4**:
`fuentes_pendientes` no existía en ningún vocabulario, me lo inventé al estrechar (§22, H4-03).

**R4, R5 y R6 corridas y adjudicadas.** Actas:
`docs/superpowers/specs/2026-08-24-apertura-integral-r4-adversarial-review.md` y
`docs/superpowers/specs/2026-08-24-apertura-integral-r5-adversarial-review.md`.
R4 y R5 (`REQUIERE-REVISION`, 5 hallazgos cada una) cerraron
el diseño en la rev. 8 y el §23 **detuvo a propósito** el bucle de revisión sobre la spec: un cuarto
párrafo habría producido un cuarto hallazgo idéntico. Las cuatro decisiones quedaron tomadas en el
§24 y el write-set barrido en el §25.

**R6 es la primera ronda de este diseño que revisa CÓDIGO y no prosa** — el diff del Plan 1.
Veredicto `NO-SHIP`: **9 hallazgos, 9 confirmados, 0 refutados** (1 CRÍTICO, 5 ALTOS, 2 MEDIOS,
1 BAJO), **todos remediados**. Acta:
`docs/superpowers/specs/2026-08-24-apertura-v1-plan1-r6-adversarial-review.md`; adjudicación en el
**§6 del plan**. El dato que justifica haber gastado la ronda aquí: el CRÍTICO —`--force` en modo
`v1` creaba una carpeta sombra con W-code duplicado, contra el criterio 33, que el §21.4 mete en
los 24 de V1— no lo vio ningún guard, ningún test ni mis dos lecturas. **Y cinco de los nueve eran
defectos míos del mismo día**, entre ellos una prueba de mutación real pero mal dirigida, que me
había hecho declarar contratada una propiedad más ancha de lo que probaba.

- [x] **Plan 1 — `--modo v1` y sus puertas negativas.** Cinco tasks TDD + la remediación de R6.
      La puerta rechaza, antes de las cuatro fronteras del §24 D3, cinco invocaciones: `--crm` ≠
      `skip`, `--fuente` ≠ `drive_ev`, `--force` sin `--case-id`, `--dry-run`, y la falta de
      `--folder-id`. 22 tests, cuatro de ellos verificados por mutación.

**Siguiente:** (1) ~~la **Fase 1 de la arquitectura dual**~~ ✅ **CERRADA** (PR #236); (2) ~~**Plan
2** — la primitiva de mutex de D2~~ ✅ **MERGEADO** (PR #247, cuatro rondas); (3) **Plan 3**
— el write-set: llevar al guard las 25 clases que hoy no pasan, **y cablear el mutex**, que hasta
entonces no protege nada. Lo tachado se conserva para que se lea el orden real en que cayó.

*(Texto original del punto 2, que ya no aplica: la primitiva de mutex de D2 (lockfile `O_EXCL`,
namespace por W-code, lease) — **`O_EXCL` resultó no ser la primitiva real**, ver arriba.)*; (4) el
write-set, llevar al guard las 25 clases que hoy no pasan; (4) **Plan 4**, cuyo contrato hay que **escribir antes** en la spec (§25.5); (5) **Plan
5** — el cableado del orden completo y el E2E, que es lo que hace que `--modo v1` deje de ser solo
una puerta; (6) W-02Q38C se cierra por ese wiring, sin parche manual del caso.

**Lección que los Planes 2-5 heredan, del §6.3 del plan:** una prueba de mutación vale lo que vale
su **elección de mutante**. Si el contrato enumera cuatro fronteras, hacen falta cuatro mutantes,
uno por frontera. Un solo mutante rojo prueba que el test no está vacío; no prueba el contrato.

**`MEJORAS #124` — alcance RECORTADO y construido (2026-09-02).** Plan
[`2026-09-02-mejoras-124-copia-de-trabajo.md`](docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md).

**Cuatro rondas sobre esta pieza, las cuatro con hallazgos confirmados y ninguna limpia.** R21
(diseño rev. 1, `NO-EJECUTABLE`, 8) y R24 (diseño rev. 2, `NO-EJECUTABLE`, 12) tumbaron **los dos
diseños**, y las dos coincidieron en que el problema era el **alcance**, no el detalle. **Decisión de
Nikolai: recortar en vez de escribir una rev. 3** — que es justo el movimiento que la fila #13
existe para frenar.

**Lo construido (§10 del plan):** `deposito()` acepta un `CaseWorkspace` **ya resuelto por el
llamador**; quien resuelve es el entrypoint, que tiene el contexto. Cierra **H18-01** — la costura de
3A solo servía para el canon. **Primer cliente de producción:** `sala_maquina` (`apply`/`reforzar`),
que cierra la frontera **F7** medida en la rev. 2: `deposito()` tenía **cero llamadores**. No mueve
bytes de sitio, y eso se dice.

**R25 y R26 sobre el diff, las dos `NO-SHIP`, 14 hallazgos, 14 confirmados** (§§11-12 del plan;
actas `…-r25-` y `…-r26-`). **Los graves son todos míos y de la misma familia:** R25 midió que mi vía
nueva **aceptaba una identidad que la histórica rechazaba** —una regresión, nacida de escribir en un
docstring «el resolver ya validó contra el canon» sin comprobarlo— y R26 midió que al remediarla
cerré **el ejemplo y no la frontera**: un workspace local del caso A apuntando al canon de B escribía
en B sin desviar. **Quinta aparición del patrón en la sesión.**

**Y el hallazgo que más enseña, R26/H26-04:** mi fixture comprobaba `if "id_go" not in txt` y
`ensure_case` ya escribe `id_go: null`, así que el valor real **nunca entraba**: los 26 tests pasaban
por el nombre de la carpeta, no por el metadato. Arreglar la fixture **no bastó** —el nombre suplía—;
hizo falta un caso con nombre neutro para que el mutante del metadato muriera.

**Se mergea sin tercera ronda, con la cobertura de la última remediación declarada AUSENTE**
(decisión de Nikolai, §12.3). El dato que la sostiene: nada en producción escribe por esta vía salvo
`sala_maquina`, que ya escribía donde escribe. La alternativa anotada y no tomada: **partir la pieza
en dos** —invariante modo/raíz e identidad son independientes, y cada arreglo de una rompió la otra—.

**PARTIDA EN DOS (2026-09-02), que era la alternativa anotada y no tomada.** `ubicacion.py`
—local FUERA del catálogo, `drive_active` DENTRO, sin identidad ninguna— y la regla de identidad,
que conserva lo suyo. **Lo que aparece al partirlas explica las cuatro rondas:** la ubicación **no
necesita saber qué caso es**, y la versión acoplada preguntaba «¿es *el* canon de *este* caso?».
Condición de cierre ejecutable: `python -m tests._mutantes_particion_124` — seis mutantes, y cada uno
mata **solo** tests de su propiedad. El arnés destapó que el **código** estaba partido y los **tests**
no, y que el arreglo de R26/H26-02 había entrado **sin test**.

**Destapó tres defectos vivos que no eran del plan:** `MEJORAS #136` (cerrado, PR #255), `#141`
(`buscar()` no valida el `case_id`) y las entradas `#137`/`#138`.

**Plan 5 — EL CABLEADO, y el orden invertido a propósito (decisión de Nikolai, 2026-09-03).** Plan
[`2026-09-03-apertura-v1-plan5-cableado.md`](docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md).

La spec proponía 3A-bis → 3B → 3C → 4 → 5. **Se invierte: se cablea primero y se aplazan 3B y 3C.**
El razonamiento, con lo medido delante: hay un mutex con cuatro rondas y diecisiete mutantes que
**no protege nada**, y una costura con **un** llamador de producción. Añadir una tercera pieza sin
encadenar, antes de que un E2E mida qué duele, es repetir el modo de fallo que este repo ya tiene
documentado. Lo que decide el orden no es lo interesante que sea cada pieza, sino que la secuencia
existe para que las piezas construidas corran.

**Lo que el plan construye:** un secuenciador puro en `core/apertura_v1.py` —orden, punto de parada,
máquina de estados de D4, informe— y los adaptadores de las tres etapas en `scripts/abrir_caso.py`,
dentro del bloque de mutex que ya existe. Once tasks, **catorce fronteras con un mutante cada una**.

**La decisión técnica que cierra el diseño, y está medida:** el cableado va **en proceso, nunca por
subproceso**. `mutex_sesion._SESIONES` es estado de módulo, o sea del proceso (`:57-60`), así que un
hijo chocaría contra el lease de su propio padre y devolvería `CaseBusy`. Las dos salidas serían no
sostener el mutex —perder justo la protección que el ítem existe para añadir— o pasar el lease entre
procesos, que es reabrir las cuatro rondas del Plan 2.

**Los tres huecos que llena, verificados contra el código y no contra la prosa:** nadie encadena
—`abrir_caso` no importa `sala_maquina` y `_despachar_intake` atiende una sola fuente por
invocación—; `preparado_con_pendientes` tenía **cero apariciones** en `core`, `scripts` y `tests`;
y el `element` del pull CRM lleva default **judicial** (`core/sync_sudespacho.py:1356`), que es
exactamente el cruce contra el que avisa el criterio 38 en su dirección peligrosa.

**Las cuatro deudas, aprobadas expresamente y no ocultadas:** (1) 3B aplazado → los derivados siguen
fuera de la costura, `TECHO_CENSO` sigue en 83; (2) 3C aplazado → **la poda sigue borrando** con
`unlink()` contra lo que D4 ordenó, y lo que la salva es que borra derivados regenerables con
`00_Input` intacto; (3) el bloque 3 de la spec —espejo versionado, monotonía de observación,
snapshot por ronda— tampoco se construye, y lo que lo salva es el marcador `.pulled`, que impide
re-descargar; (4) 3A-bis aplazado → D5 sigue vigente y el sello de ids queda aplazado con aviso.

**Presupuesto: dos rondas** (la secuencia sostiene el mutex mientras corre, así que decide quién
puede escribir sobre esa copia): R-A sobre el plan antes de escribir código, R-B sobre el diff.
**Validación real sobre W-02Q38C**, elegida por Nikolai: es el caso que disparó el ítem y se cierra
**por el cableado, no por parche manual**.

**R-A corrida y adjudicada ANTES de una línea de código: `NO-EJECUTABLE`, 12 hallazgos, 11
confirmados y 1 parcialmente refutado** (4 críticos + 1 elevado por el adjudicador). Acta
[`…-plan5-rA-adversarial-review.md`](docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rA-adversarial-review.md);
adjudicación en el §5 del plan. **La ronda EJECUTÓ** —midió que mi adaptador de Drive no llamaba a
la custodia (`custodia_calls= []`), puso el trinquete del censo en 84/83, dejó VIVO el mutante F12,
pasó mi fixture del E2E por el lector real de metadatos y obtuvo `{}`, y reprodujo la pérdida de
mutex bajo un `typer.Exit(0)`— y los cuatro críticos salieron de ahí, no de leer.

**El hallazgo de fondo es sobre la premisa, y la premisa se la había dado yo a Nikolai.** Dos de las
cuatro deudas que el §0 declaraba «aceptadas» no eran deudas: eran **contradicciones literales de
la tabla de riesgos de la spec**, que ya nombraba los dos mecanismos con su mitigación obligatoria
—«`.pulled` evita volver a Drive → **falso punto fijo** → consulta remota real en cada ronda» y
«`estado.json` atómico **obligatorio desde la primera entrega**»—. Yo construí sobre esos dos el
argumento de que la reanudación «no cuesta diseño nuevo» y **se lo presenté como razón para
preferir la ejecución desatendida**. Consecuencia práctica: con ese diseño, un documento que E&V
añadiese a la carpeta del caso después de la primera apertura **no se vería nunca**.

**Por qué no lo vi:** leí el §21 y el §24 de la spec —el alcance y las decisiones— y no su tabla de
**riesgos**, que es donde vivía la respuesta a la pregunta que me estaba haciendo. Misma clase que
ya tengo medida: el dato se busca en el registro del nivel de su alcance, y «qué mecanismo es un
falso punto fijo» es un riesgo, no un criterio.

**Y tres de los críticos son la misma forma: mis adaptadores RODEABAN costuras que ya existían.**
`etapa_drive` se saltaba la custodia que R14/H14-02 y R15/H15-06 pusieron en `_intake_drive_ev`;
`etapa_crm` leía la ausencia de excepción como éxito, contra la regla que `CLAUDE.md` tiene escrita
—«verificar por resultado, nunca por status»—; y la salida con `typer.Exit(0)` **dentro** del bloque
de mutex convertía en una nota la pérdida ruidosa que R12/H12-04 había construido. **Escribir un
adaptador nuevo encima de una costura vieja es la manera silenciosa de derogarla.**

**Una corrección contra mí, no contra el revisor: HA-08 quedó PARCIALMENTE REFUTADO.** Lo confirmé
y encima le añadí un escenario más grave —«una corrida parcial poda contra un `esperados`
incompleto»— **sin comprobar la guarda**. La guarda existe: el `unlink` de `mensajes/` vive dentro
del `else` de `if report.errores:` (`core/email_atomize/pipeline.py:204-220`). Sobrevive solo en
`vistas/` y `*.contenido.md`, derivados regenerables. **Un adjudicador que no comprueba la guarda no
confirma: infla.**

**Rev. 2 escrita y commiteada**, con los doce remediados y **dos cambios de fondo decididos con
Nikolai**: la etapa de Drive **consulta en cada ronda** (`force=True`) y entra el **`estado.json`
por ronda** (Task 8b). El plan pasa de 11 a 13 tasks y de 14 a **28 fronteras**, con un mutante por
frontera y un arnés que ahora **sí puede medir su propia regla** —ejecuta el conjunto contractual
completo y compara el conjunto exacto de rojos, en vez de leer un booleano de un solo `nodeid`—.
**El censo sube a 84 con su declaración**, que es lo que su propia regla exige. **R-B adjudicada `NO-SHIP` el 2026-09-03, con REVISOR SUSTITUTO y la independencia declarada más
débil.** Codex agotó su cupo a mitad de la ronda (vuelve el 2026-09-07), así que la corrió una
sesión de Claude Code —el mismo modelo que escribió el código— con la compensación que `AGENTS.md`
exige: **seis lentes en paralelo**, copia congelada, sin la adjudicación de R-A. Acta
[`…-plan5-rB-adversarial-review.md`](docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rB-adversarial-review.md);
adjudicación en el §6 del plan. **73 hallazgos, 10 críticos.**

**El defecto vivo que decidió el veredicto:** las dos ramas de `traducir_pull_crm` que producción
alcanzaría eran **inalcanzables**, porque el productor mete en `errors` el aviso de un gestor
documental **vacío** e incrementa `documents_failed` en el mismo bloque que su `errors.append`. Un
expediente CRM sin documentos —lo normal en uno recién creado— **abortaba la apertura entera** sin
que el OCR arrancase. Leí los campos del dataclass y no su productor.

**Y el hallazgo transversal, que invalida mi propia medición:** el «28/28 mutantes muertos» era una
**autoatestación cerrada**. Tres lentes con mutantes propios midieron **17 de 21 vivos** y **11 de
12**, y cuatro de mis 28 muertes caían sobre fronteras que no existen en producción; mi arnés
**excluía justo los ficheros del cableado**. La lección, ya en memoria: un mutante muerto prueba que
el test no está vacío, **no que la frontera exista**.

**Cuatro fronteras cerradas** (no sus ejemplos): el productor clasifica y el adaptador pregunta; un
fichero de control se declara en **los cuatro** registros de `00_Input` —hay uno canónico y lo
declaré en ninguno—; si se perdió la exclusión **no se escribe nada**; y una costura tiene dos
extremos, así que hay diez tests nuevos que recorren el camino **por defecto**. **3.880 tests, 0
fallos con dos semillas; 31/31 mutantes, ya con el cableado dentro del arnés.**

**Diez bloques quedan ABIERTOS y declarados** en el §6 del plan; ninguno bloquea una apertura ni
pierde datos de cliente. **El primero cambia una decisión que tomamos:** `MEJORAS #142` —el `Exit`
dentro del bloque de mutex— vive **casi solo en el modo `libre`**, con 9 salidas, y la rama `v1` que
remedié apenas podía manifestarlo. Lo aplazamos sobre una descripción mía que resultó engañosa.

**DECIDIDO por Nikolai el 2026-09-03: se PARA aquí y se espera a Codex.** No se gasta tercera
ronda, no se remedia más, y **no se mergea**. Cuando Codex vuelva a correr ve el diff; con sus
hallazgos más los diez declarados en el §6 se hace **una sola** remediación informada.

**El disparador es un EVENTO, no una fecha, y la primera versión de esta línea decía «el
2026-09-07»: mal.** Esa fecha salía del mensaje de error de Codex —«purchase more credits **or** try
again at Sep 7th»—, o sea el reset gratuito **con una alternativa al lado**, y yo la convertí en
«Codex vuelve el 7». Peor: al sondearlo horas después el fallo **ya era otro**, un **404** de
`backend-api/codex/responses` con sesión iniciada y el mismo binario que había corrido R-A. Eso no
es cupo y un reset no lo cura. Antes de dar la vía por recuperada hay que **sondearla**, no mirar el
calendario. **Y se recuperó el mismo día:** el sondeo dio verde unas horas después, así que
la espera de cuatro días nunca existió.

**R-C corrida y adjudicada el 2026-09-03: TERCERA ronda, autorizada expresamente por Nikolai, con
Codex y la independencia RESTABLECIDA. `NO-SHIP`, 7 hallazgos, 7 confirmados, 0 refutados.** Acta
[`…-plan5-rC-adversarial-review.md`](docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rC-adversarial-review.md);
adjudicación en el §7 del plan.

**El hallazgo que justifica la ronda: HC-02 es un defecto que introduje AL REMEDIAR R-B.** Saqué la
publicación del registro durable fuera del bloque de mutex «para no afirmar un éxito que la pérdida
del lease desmiente», y con eso escribí **sin exclusión ninguna**. Codex mutó y ejecutó la
intercalación `R1 abre → R1 libera → R2 abre → R1 cierra`: el fichero queda con la ronda R1 y
**borra la evidencia de que R2 sigue en curso**, y ese mutante sobrevivió a los 105 tests
contractuales. Cuatro líneas encima yo había escrito «escribir sin mutex es la violación que el
mutex existe para impedir». Enuncié la propiedad y escribí lo contrario, en el acto de remediar.

**La frontera, que cerró tres hallazgos con un cambio: `revalidar → publicar → liberar → salir`,
indivisible.** La publicación vuelve **dentro** del bloque como último acto, previa
`sesion.revalidar()` —el gestor cede la sesión y yo usaba `with` sin `as`, así que una pérdida a
mitad de una etapa larga pasaba inadvertida—, con el evento forense **antes** del `estado.json`
porque el `.jsonl` es append-only y autoritativo. Fuera del bloque queda solo informar y salir, así
que la propiedad de HA-07 se conserva **y ya no hay escrituras a ese lado**, que es lo que antes la
contradecía. **3.883 tests, 0 fallos en dos semillas; 31/31 mutantes.**

**Cuatro bloques quedan abiertos y confirmados** (§7): **HC-04**, la contaminación cruzada devuelve
`ok` y el OCR sigue —el que más pesa, porque los documentos de otros casos colados van por su
tercera aparición en este repo—; **HC-05**, cuatro consumidores más de `PullResultV2` con el mismo
defecto, uno imprimiendo «Sync completado» con errores dentro; **HC-06**, cambié el §3 de mi propio
plan sin adjudicarlo y el «31/31» es cierto sobre mi lista pero no sobre el §3 (faltan F19, F20 y
F26); y **HC-07**, el punto fijo material del E2E es vacuo.

**Siguiente:** decisión de Nikolai sobre **HC-04** (toca prueba documental) y **HC-06** (una fuente
que modifiqué sin permiso de nadie), más `MEJORAS #142` y los diez bloques del §6. **Task 11 sigue
sin ejecutarse.** No se pide cuarta ronda.

**El razonamiento, que es el de la propia sesión:** hoy remedié HA-07 en la rama que no podía
manifestarlo y dejé el defecto donde vivía. Arreglar diez bloques más antes de que un revisor con
puntos ciegos distintos mire la base es repetir ese movimiento a mayor escala. `MEJORAS #142` queda
abierta con su medición corregida y espera esa misma pasada.

**Estado de la rama al parar:** 28 commits, **3.880 tests con 0 fallos en dos semillas**, **31/31
mutantes** muertos por su frontera con el cableado ya dentro del arnés, las dos actas archivadas con
digest y los guards de gobernanza en verde. **Sin mergear y sin pushear. Task 11 sin ejecutar.**

---

## [SIGUIENTE-PRESUPUESTO-PROCESO] Cuánta gobernanza se compra

*Fila #13. **✅ DECIDIDO el 2026-08-26.** El bloque se conserva porque el razonamiento que
llevó a la decisión sigue siendo la mejor explicación de por qué existe.*

> **La decisión, en `CLAUDE.md` §«Cuántas rondas»:** el número de rondas lo fija el **radio
> de daño** de la pieza. **Dos** si decide quién puede escribir o puede destruir datos de
> cliente —una sobre el diseño, una sobre el diff—; **una** en todo lo demás. Y un **techo
> duro**: nunca una tercera sobre la misma pieza sin autorización expresa de Nikolai.
>
> **El dato que la decidió**, medido sobre el mutex de V1 el 2026-08-26: cuatro rondas, 660
> líneas de producción contra 3.938 de test y documento —seis a uno—, las cuatro con
> defectos reales y **ninguna limpia**. O sea que el criterio implícito que yo venía usando
> —«hasta que una ronda vuelva sin críticos»— **no converge**: siempre hay una ronda más que
> encuentra algo, y «la anterior encontró algo» es un argumento que no se agota.
>
> **Y el corolario que de verdad ahorra rondas:** ante cada hallazgo, preguntar **«¿de qué
> frontera es esto un ejemplo?»** antes de remediarlo. Las cuatro rondas del mutex
> encontraron **cuatro veces la misma propiedad mal cerrada** porque cada vez remedié el caso
> que el informe describía y no la propiedad de la que era ejemplo.

**El disparador, medido el 2026-08-03** sobre el 2026-07-05 → 2026-08-02: **228 commits, de los
que 57 (25 %) tocan `core/`/`scripts/`/`streamlit_app.py`** y 150 (66 %) son solo docs/config.
Líneas añadidas: **`docs/` +63.667 frente a `core/` +6.741 — 9,4 a 1**. Los cuatro últimos
cierres (52º-55º) no produjeron código de producción; el PR #189, uno solo, mete 2.303 líneas de
las que 1.661 son tres informes de revisión adversarial **sobre el contrato de las revisiones
adversariales**.

**Lo que NO dice este ítem:** que la gobernanza sea desperdicio. El mismo mes, las revisiones
compraron defectos vivos y caros — la invariante que habría autorizado modificar un expediente
real de cliente bajo `data/CASOS/`, y tres rutas de pérdida de datos (#156, #160, #175). El
problema no es el control, es que **no hay techo declarado**, y sin techo el mecanismo se
autoalimenta: en el 55º cierre cada remediación cerraba su defecto y abría otro en la costura de
al lado, seis rondas seguidas.

**La decisión, dos números en `CLAUDE.md`:** (a) cuántas rondas de revisión come un documento
antes de que la conclusión razonable sea recortar alcance en vez de revisar otra vez; (b) qué
proporción de sesiones puede cerrar sin código de producción. Cualquier número explícito bate al
actual, que es ninguno.

**Por qué lo tiene que fijar Nikolai y no Claude:** el 55º cierre ya demostró el sesgo — cuando mi
propia regla de parada me obligaba a parar, redefiní el disparador, y un revisor sin nada
invertido lo llamó racionalización *ex post*. Escribir doctrina se siente productivo; el freno
tiene que venir de fuera.

---

## [SIGUIENTE-REIMPORT-SKILLS] Lo construido que no ha llegado al equipo

*Fila #14. Acción manual de Nikolai en Cowork; ningún test la cubre y ningún guard la detecta.*

**El disparador:** `organizar-sala-lectura` está en **v1.14 en `.claude/skills/`** y el equipo
—Paola, Ana, Sergio— sigue ejecutando la **v1.12**. Construido ≠ desplegado, y el único tramo que
falta es manual.

**Censo de re-imports pendientes en este mismo fichero** (2026-08-03), por bloque y no por
número de línea, que aquí se desplaza solo: `[SIGUIENTE-SALA-HILOS]` (v1.14),
`[SIGUIENTE-PRECLASIFICACION-SALA-LECTURA]` (v1.11), `[SIGUIENTE-SALA-UNICA-PLANA]` (v1.3/v1.1),
`[SIGUIENTE-INPUT-LOTES]` (Tarea 15) y `[SIGUIENTE-MCP-DRIVE-DISCO-PASOS-5-7]` (paso 5, cuatro
`.skill` re-empaquetados). Localizables con `grep -i "re-import" PLAN.md`.

**Procedimiento:** `docs/MEJORA_CONTINUA_SKILLS.md` → `scripts/package_skill.py` → importar el
`.skill` en Cowork.

**Trampa ya documentada, que es la que lo ha hecho fallar antes:** empaquetar **desde la raíz**,
nunca desde un worktree que luego se poda (el `.skill` acaba en un `dist/` que desaparece), y
**verificar la versión dentro del zip**, no la del repo.

**Al cerrar:** marcar `[x]` las seis entradas en sus bloques y anotar aquí la versión que quedó
efectivamente en Cowork — que es el dato que hoy no consta en ninguna parte.

---

## [SIGUIENTE-MARKETPLACE-PLUGIN] El marketplace despacho-tyukhay no está publicado en git

*Fila #16. Una decisión de Nikolai (E.6.1) y dos pasos mecánicos detrás. Origen: §2.2 de
`docs/superpowers/handoffs/handoff-2026-08-14-migracion-procesal-continuacion-tnm33.md` — es la
decisión **D4** de la migración al perfil `procesal@`, firmada el 2026-08-13 y nunca ejecutada.
Mismo género que la fila #14: construido ≠ desplegado.*

**El estado medido (2026-08-25).** En `tnm33`, `~\.claude\plugins\known_marketplaces.json` y el
`extraKnownMarketplaces` de `~\.claude\settings.json` mantienen la entrada `despacho-tyukhay` de
tipo `directory` apuntando a `C:\Users\tnm33\Dev\FeesDefender\dist\plugin` (`lastUpdated:
2026-07-20`). El handoff declara la misma entrada en el perfil procesal, donde además **el
directorio no existe** porque `dist/` está gitignorado (`.gitignore:23`) y el clon del perfil 2
viene del remoto. Que el plugin funcione allí es un accidente: la caché de
`~\.claude\plugins\cache\despacho-tyukhay\feesdefender\0.4.0\` viajó entera por el puente de
migración, que después se destruyó (`C:\Users\Public\migracion` ya no existe, comprobado).

**Por qué es disparador y no completitud de diseño.** No es que la vía diseñada esté a medias: es
que **la vía de mantenimiento no existe**. El propio runbook v5, en «Operación diaria», ordena que
al cambiar el plugin se publique la versión nueva y el perfil 2 haga `/plugin update` **sin
puente** — y eso hoy es imposible. La alternativa real es rehacer el puente completo (Bloques 0,
A.1-A.6, A.8 y D.1) por cada cambio del plugin, con su copia de `~\.claude` y su reescritura de
rutas. Es decir: el coste de mantener el perfil procesal está hoy en su punto más alto justo en el
tramo que D4 existía para abaratar.

**E.6.1 ✅ DECIDIDO el 2026-08-25 por Nikolai: repo dedicado, privado, con remoto SSH.**

*La opción descartada estaba mal descrita en la rev. anterior de este bloque, y la corrección
importa porque cambia su coste.* Se dijo «rama de distribución con `dist/` desexcluido»; la doc
exige que el manifiesto viva en la **raíz del repositorio** —«*The `.claude-plugin/marketplace.json`
file must be located at the repository root*»—, así que no basta desexcluir: haría falta una **rama
huérfana** cuya raíz sea el contenido de `dist/plugin`, es decir **un segundo layout de raíz
incompatible dentro del mismo repo**. (También se creyó, por inferencia del
`known_marketplaces.json` local, que no se podía fijar rama. **Falso:** `/plugin marketplace add
owner/repo@main` sí admite ref. La rama no estaba bloqueada; simplemente cuesta más de lo que
parecía.)

Motivos de la decisión, en orden:

1. **Encaje sin reestructurar nada.** `dist/plugin` ya *es* una raíz de marketplace válida
   (`.claude-plugin/marketplace.json` arriba, `./feesdefender` al lado). El repo dedicado es su
   contenido con un `.git`, y `scripts/package_plugin.py` sigue produciendo lo mismo.
2. **No mete artefactos derivados en el repo fuente.** `.gitignore:23` existe por eso.
3. **No abre una vía de publicación más débil.** `main` está protegida y todo entra por PR; una
   rama `dist` sería no protegida y su forma natural de actualizarse es un push directo de salida
   de build.
4. **Todo lo de este repo asume una sola forma de raíz** — `pre-commit`, el `leak-scan` de CI, los
   guards de docs, `session_close`. En una rama huérfana ninguno aplica, y los workflows se leen de
   la rama.
5. **Privado desde el día uno:** el bundle lleva los dos servidores MCP y dos skills con método del
   despacho; y si algún día se distribuye por *Organization settings > Plugins*, la doc **exige**
   que el repo del marketplace sea privado o interno.

**Remoto SSH, no HTTPS — este es el detalle operativo que muerde.** Las actualizaciones automáticas
en segundo plano **no autentican por HTTPS** (los credential helpers están deshabilitados en esos
pulls). Con HTTPS quedaría `/plugin update` manual funcionando y el auto-update **roto en silencio**.
Con la clave en `ssh-agent`, funciona.

**Tres pasos previos al primer push, medidos el 2026-08-25:**

1. **Regenerar el bundle, y copiarlo acto seguido.** El actual es del **20 de julio 13:13**, y
   `intake-expediente` y `exportar-correos-etiqueta` están entre los `.skill` que `session_close`
   marca como caducados: publicarlo tal cual publica las skills de julio. Que la copia vaya *pegada*
   al build no es manía: mientras el marketplace sea de tipo `directory`, los servidores **ejecutan
   desde `dist/plugin`** y le van dejando residuo dentro (ver el punto 2). Un build fresco hace
   `rmtree` de la salida, así que sale limpio; lo que contamina es publicar un árbol que ya se ha
   usado. **Con el marketplace en git esto se extingue solo:** los servidores pasarán a ejecutar
   desde `~\.claude\plugins\cache\`.
2. ~~**Excluir `__pycache__` en `scripts/package_plugin.py`.**~~ **PREMISA FALSA, corregida el
   2026-08-25 al ir a arreglarla.** El empaquetador **ya** los excluye, y desde el commit que lo
   creó (`60fee81`, 2026-06-22). Los 9 `.pyc` del árbol son **residuo de ejecución**, no de
   empaquetado: están fechados **12 horas después** del build. Esta entrada afirmaba un defecto que
   no verifiqué en el código — el backlog describe, no mide, y aquí describió mal. **Lo que sí
   había, y lo encontró el control del punto 3:** el bundle ataba el plugin a un perfil por **dos**
   vías distintas (`run_server.bat` con el intérprete absoluto, la «bomba A.6-ter» que se parcheó en
   el perfil destino y no en la fuente; y `dxt-build/` viajando dentro con su `manifest.json`).
   **Arreglado, con contrato y tres mutantes** (`tests/test_package_plugin.py`).
3. **El control de secretos** de abajo, que ya estaba — **y es el que encontró el defecto real**.
   Ejecutado el 2026-08-25: 0 secretos, **4 rastros de `C:\Users\<perfil>`**. El término `tnm33` de
   la lista no era paranoia de secretos: era la prueba de portabilidad, y es la que mordió.

**Y una cifra del handoff que era de otra cosa:** decía «920 ficheros, 8,2 MB» — eso es el árbol
`~\.claude\plugins` completo. `dist/plugin` son **35 ficheros y 310 KB**. El tamaño no era argumento
para ninguna de las dos opciones.

**Control bloqueante antes de publicar.** Barrido del bundle buscando
`sk-ant-`, `client_secret`, `refresh_token`, `AIza`, `ghp_`, `password` **y `tnm33`**. Debe salir
vacío. Ojo al último término, que no es un secreto sino una prueba de portabilidad: si el bundle
lleva rutas de este perfil, publicarlo no arregla nada. Precedente concreto en el handoff v5
(A.6-ter): `email_export_mcp\run_server.bat` llevaba el intérprete Python absoluto de `tnm33`.

**Los dos pasos mecánicos después.** E.6.2: en el perfil procesal, `/plugin marketplace add` +
`/plugin install feesdefender@despacho-tyukhay`, y comprobar que `expedientes-xl` y `email-export`
siguen cargando. E.6.3: retirar la entrada `directory` huérfana con `/plugin marketplace remove`
—**no** editando el JSON a mano— hasta dejar un solo `despacho-tyukhay` y un solo `feesdefender`.
Y en `tnm33` lo mismo: la entrada rota está en los dos perfiles.

**Al cerrar:** marcar aquí dónde quedó publicado el marketplace y con qué versión, y pasar a
`consumido` el handoff de la migración si no le queda nada más vivo. Hoy la fuente de verdad de
esta pieza es un andamio efímero y dos ficheros en `C:\Users\Public\Documents`.

---

## [SIGUIENTE-OCR-CIEGO] Texto perdido bajo el sello de firma (`MEJORAS #90`)

*Disparador confirmado 2026-07-27 al ejecutar el paso 0 (detector) sobre los 5 casos con Sala de
máquina: **402 documentos `ok`, 24 candidatos, 6 pérdidas reales medidas**. Promovido de
`docs/MEJORAS_FUTURAS.md` #90, que conserva el diagnóstico completo, la tabla de mediciones y el
razonamiento. No reabrir aquí lo que ya está decidido allí.*

**El problema en una frase:** un PDF escaneado que trae capa de texto —aunque sea solo el pie de firma
de LexNET— engaña a los tres guardarraíles en cadena (`_texto_suficiente` → `--skip-text` →
`ocr_quality`), sale **`ok`** en `_cobertura.md`, y por tanto queda fuera de la worklist de revisión
**y** del filtro de `reforzar`. Nadie lo ve.

**Lo que ya está medido (no hay que volver a medirlo):**

| documento | texto hoy | tras re-OCR | faltaba |
|---|---|---|---|
| Cuentas anuales 2024 — W-02VND1, `MEDIDAS CAUTELARES` | 10.979 | 65.076 | **83 %** |
| Cuentas anuales 2023 — W-02VND1 | 10.082 | 53.857 | **81 %** |
| Cuentas anuales 2022 — W-02VND1 | 10.381 | 55.011 | **81 %** |
| Tasación TECNITASA — W-02VND1 | 46.142 | 62.711 | 26 % |
| Exposé de propiedad — W-02XOR7 | 9.854 | 13.732 | 28 % |
| Exposé — W-02VUDR | 12.490 | 13.889 | 10 % |

**Restricción dura que condiciona el diseño:** los cuatro documentos de W-02VND1 son **AcroForm** y
ocrmypdf **rechaza `--redo-ocr`** sobre ellos (`InputFileError: This PDF has a user fillable form`).
Solo `--force-ocr` recuperó su texto — el modo destructivo abandonado tras VALERO. El arreglo no puede
ser cambiar una bandera.

- [x] **(a) Escalera de OCR con degradación explícita** — `core.anon.ocr.ocr_pdf_escalera`
      (`7ed5c1f`). Peldaño 1 `--redo-ocr` sobre el documento entero → peldaño 2, si falla, aislar
      cada página ciega con `pypdf` (**eso quita el AcroForm**, que era el bloqueo) y OCR-izarla
      aparte, recomponiendo el documento sin reescribir las demás páginas → peldaño 3
      `degradado=True`, que `_ocr_y_extraer` traduce a `low`, **nunca `ok`**, con la nota en
      `_cobertura.md`. **`--force-ocr` no aparece en ningún punto.** Verificado en integración
      contra ocrmypdf y Tesseract reales sobre un AcroForm: peldaño 1 rechazado, peldaño 2 recupera
      el cuerpo y deja intacta la página digital.
- [x] **(b) `ocr_quality` por página** — `sala_maquina.calidad_por_pagina` (`7ed5c1f`). Marca `low`
      cuando hay páginas con ráster a página completa y sin texto recuperado, aunque el promedio
      pase (≥2 páginas, o ≥la mitad del documento). El ráster es el discriminante que evita marcar
      los reversos en blanco de un dúplex, y el mínimo de 2 páginas evita marcar la foto suelta del
      camino `imagen` — los falsos positivos que ya hubo que descartar al medir el cribado.
- [x] **(a-bis) El gate de entrada, sin el cual (a) seguiría siendo inalcanzable.** Era el eslabón
      1 de la cadena y no estaba en esta lista: un escaneo con pie de LexNET (~228 char/pág frente
      a un umbral de 40) pasa `_texto_suficiente`, se clasifica «digital» y **nunca llegaba a
      OCRmyPDF** — con la escalera puesta y nada más, los cuatro documentos de W-02VND1 habrían
      vuelto a salir `ok`. Ahora, un PDF que pasa ese gate pero esconde páginas ciegas baja
      igualmente a la escalera en **modo conservador** (empieza en el peldaño 2, que no reescribe
      el texto de las páginas digitales — el matiz medido en (c2)). `_texto_suficiente` no se toca:
      la decisión se toma con el discriminante de página ciega, ya validado en 402 documentos.
- [x] **(a-ter) Dos bugs de fondo, encontrados al ejecutarlo en vivo y no por lectura.**
      (1) ocrmypdf **rechaza `--redo-ocr` junto a `--deskew`**, que es el default de `ocr_pdf`: el
      modo redo era inalcanzable *dos* veces —ningún llamador lo pasaba y, si lo hubiera pasado,
      habría reventado en la validación de opciones antes de OCR-izar nada—. (2) Como el modo redo
      obliga a renunciar al deskew, se reserva a los documentos que **traen capa de texto**: el
      escaneo limpio sigue por `--skip-text` y conserva el enderezado. Sin esto, arreglar #90 le
      habría costado calidad de OCR al caso mayoritario.
- Infraestructura: `core/pdf_paginas.py` es el **SSOT del discriminante de página ciega**, consumido
  por el motor, por la calidad por página y por `scripts/detectar_ocr_ciego` (refactorizado para
  consumirlo, sin cambio de comportamiento). Si cribado y motor divergieran, el detector dejaría de
  describir lo que el motor hace.
- [x] **(c1) Cuentas anuales de W-02VND1 RECUPERADAS** (2026-07-27), primero en la copia local del
      checkout y **ya en Drive** tras el `case_checkin` (ver abajo):

      | ejercicio | páginas recuperadas | texto antes | ahora |
      |---|---|---|---|
      | 2024 | 23 de 25 | 10.979 | **65.159** |
      | 2023 | 20 de 22 | 10.082 | **53.849** |
      | 2022 | 21 de 23 | 10.381 | **55.123** |

      Método: extraer cada página saltada con `pypdf` (**quita el AcroForm**, que era el bloqueo) y
      OCR-izarla con **`--redo-ocr`** — no destructivo: las 64 páginas se recuperaron sin recurrir a
      `--force-ocr`, así que las cifras de las páginas digitales quedan intactas (verificado: texto
      idéntico en las páginas digitales densas). Calidad: gibberish 2,0-2,6 %, y presentes BALANCE /
      PATRIMONIO NETO / PÉRDIDAS Y GANANCIAS / ACTIVO / PASIVO / MEMORIA. Versión anterior en
      `99_Versiones anteriores/recuperacion_ocr_2026-07-27/`; evento `procesado_sala_maquina`
      (`modo: recuperacion_ocr_sello`) en el log; `00_Input/` intacto.
      ✅ **Subido a Drive** con el `case_checkin` del 2026-07-27T17:56:49 (evento en
      `_intake_log.jsonl`), verificado por contenido en el repositorio canónico: los tres MD
      recuperados y el respaldo `99_Versiones anteriores/recuperacion_ocr_2026-07-27/` están en
      `G:`. El checkout abierto el 2026-07-23 queda así cerrado.
- [x] **(c2) Tasación y exposés RECUPERADOS** (2026-07-27):

      | documento | caso | destino | texto antes | ahora | peldaño |
      |---|---|---|---|---|---|
      | Tasación TECNITASA (2 copias de custodia, bytes idénticos) | W-02VND1 | local → **Drive** (checkin 2026-07-27) | 46.142 | **62.828** | por página, 12 de 34 |
      | Exposé de propiedad | W-02XOR7 | Drive (sin checkout) | 9.854 | **13.800** | doc. entero |
      | Exposé | W-02VUDR | Drive (sin checkout) | 12.490 | **13.977** | doc. entero |

      La escalera se comportó como se diseñó: peldaño 1 (`--redo-ocr` de documento entero) bastó en los
      dos exposés; la tasación, AcroForm como las cuentas anuales, exigió el peldaño 2 (extraer página →
      quita el AcroForm → `--redo-ocr`). **En ningún documento hizo falta `--force-ocr`.**

      Matiz verificado, útil para diseñar (a): los dos peldaños no son igual de conservadores. El
      peldaño 2 deja las páginas digitales **byte-idénticas** (19 de 34 en la tasación). El peldaño 1
      **sí reescribe** el texto de algunas páginas digitales (XOR7: 2,3,4,34,35 · VUDR: 2,3,4,45), pero
      de forma **aditiva**: el 100 % de las palabras del original sobrevive en todas ellas y ninguna
      pierde texto — lo que gana es el texto incrustado en imágenes pequeñas dentro de esas páginas. Aun
      así, para documentos donde las cifras sean críticas conviene forzar el peldaño 2.

      > ⚠️ **ERRATA (2026-08-01): la frase «el 100 % de las palabras del original sobrevive» es
      > FALSA como afirmación general, y se midió sobre estos dos exposés, no sobre el motor.** En
      > los tres segmentos de W-02VND1 reprocesados el 2026-07-30, seg03 pierde **77 palabras únicas
      > de 6.405** (1,2 %) y seg02 pierde 2 — cifras, fechas y horas (`340482060416`, `26/12/2085`,
      > `18:39`). Alta con la medición y con lo que falta por medir: **`MEJORAS #111`**. La cautela
      > final del párrafo («para documentos donde las cifras sean críticas, forzar el peldaño 2»)
      > pasa de consejo a **hipótesis por verificar**: que el peldaño 2 sea inmune es justo el
      > punto 3 de `#111`.
      >
      > ✅ **CONTRA-ERRATA (2026-08-02): medido, y la errata de arriba se pasó de frenada. La frase
      > original se sostiene para el corpus que describe.** Los dos exposés conservan el **100 %** de
      > sus palabras (0 de 583 y 0 de 579 ausentes), y con ellos los otros cinco documentos de
      > (c1)/(c2): **7 de 7 limpios, en los dos peldaños**. Y las «77 palabras» de seg03 **no son
      > pérdida**: son otra transcripción del mismo trozo ilegible —un sello de registro de salida y
      > un teléfono de membrete, ambos leídos de dos formas distintas y ninguna fiable—, y donde hay
      > pasaje comparable el nuevo es **más completo**: un DNI que el viejo partía en dos fragmentos
      > el nuevo lo trae entero. Los 2 de seg02 eran artefacto del tokenizador: el sello de firma
      > electrónica sobrevive entero, con recuentos idénticos en sus seis marcas.
      >
      > Por tanto: **la cautela final del párrafo se retira**, no como consejo desmentido sino como
      > hipótesis medida y sin soporte — ninguno de los dos peldaños perdió nada. Detalle,
      > control positivo del arnés y alcance de lo medido: **`MEJORAS #111`**, reescrita.

      Calidad: gibberish 2,6 % (tasación) / 4,0-4,6 % (exposés); tasación con 6/6 términos de tasación
      presentes; páginas conservadas 34/35/45. `00_Input/` intacto en los tres casos; respaldos en
      `99_Versiones anteriores/recuperacion_ocr_2026-07-27/`; `_cobertura.json` actualizado donde
      existía; evento `procesado_sala_maquina` (`modo: recuperacion_ocr_sello`) en los tres logs.

- Quedan **17 candidatos** del cribado sin medir (brochures, dossiers, planos y similares de W-02VND1,
  más `753_informeSaintGobain` de W-02XOR7). Son material de marketing y planos, no prueba nuclear: se
  recuperan cuando hagan falta, o de oficio al construir (a). El script de recuperación usado en (c1) y
  (c2) fue puntual (scratchpad, no versionado): el método está descrito arriba con el detalle suficiente
  para rehacerlo, y **su validación en 7 documentos, 3 casos y 2 destinos distintos es lo que
  des-arriesga la tarea (a)**.
- [x] **(d) Alcance de la re-corrida — DECIDIDO por Nikolai el 2026-07-27: `D1`, acotada a los
      candidatos.** Se re-procesan solo los 17 documentos que el cribado marcó y nadie midió; no se
      lanza `--force` sobre los 5 casos. Queda como trabajo siguiente, ver **(e)**.
      El razonamiento y las opciones descartadas se conservan abajo.

      El motor
      nuevo solo actúa sobre lo que procesa: los **5 casos ya procesados** conservan las coberturas
      que escribió el motor viejo, y en ellas siguen marcados `ok` los **17 candidatos del cribado
      sin medir** (brochures, dossiers y planos de W-02VND1, más `753_informeSaintGobain` de
      W-02XOR7). `apply` sin `--force` no los revisará: sus sha ya están en
      `_sala_maquina_state.json` y se saltan. Tres alcances, de menos a más:

      | opción | qué hace | coste | qué deja sin cubrir |
      |---|---|---|---|
      | **D0 — nada** | solo los casos nuevos usan el motor nuevo | 0 | los 17 candidatos siguen `ok`; nadie los verá hasta que alguien eche en falta el documento leyendo el fondo |
      | **D1 — acotada a los candidatos** | re-procesar solo esos 17 documentos | ~1 h de código (`apply` no sabe hoy acotar por documento; `reforzar` filtra por `low`/`empty` y estos están `ok`) + minutos de OCR. Variante sin código: retirar a mano sus sha del `_sala_maquina_state.json` y lanzar `apply` | los documentos que el cribado NO marcó; el detector sobre-marca pero también puede callar |
      | **D2 — `apply --force` en los 5 casos** | foto fresca y coherente: cobertura, estado y MD reescritos por el motor nuevo | horas: la corrida completa de W-02VND1 (~672 ficheros) fue de ~1 h 40 **con el motor viejo**, y el nuevo añade el OCR de las páginas ciegas que antes se saltaban | nada, pero reescribe MD de documentos que hoy están bien y hay que coordinarlo con checkouts/Drive abiertos |

      **Elegida D1** (recomendación seguida): es donde está la pérdida medida —los 6 reales salieron
      de esos 24 candidatos— y no reescribe nada que hoy funcione. D2 solo habría compensado si se
      quisiera además una cobertura homogénea de cara a la vista procesal.

- [x] **(e) Ejecutar D1 — CERRADA 2026-08-01 por falta de rendimiento (decisión de Nikolai).**
      Herramienta construida y ejecutada sobre los tres casos; el veredicto de la medición es que
      **D1 no recupera nada**: +0, −6 y +288 chars en los tres segmentos de W-02VND1, membrete del
      fabricante en W-02XOR7, ruido en W-02VUDR. Los 11 candidatos restantes de W-02VND1 se declaran
      **no se corren**. Lo que queda vivo de este bloque es (f) —limpiar lo que D1 ensució—. El otro
      hallazgo, que **el reproceso podía perder texto** (`MEJORAS #111`), **quedó REFUTADO al medirlo
      el 2026-08-02**: el reproceso releé lo ilegible, no destruye prueba; las 7 recuperaciones de
      (c1)/(c2) conservan el 100 % de sus palabras. Lo que sí queda de `#111` es (i) que el reproceso
      **no es idempotente a nivel de token y no puede serlo** —así que ningún guard debe assertar
      identidad byte o token— y (ii) una decisión de diseño para la pieza A: el saneamiento conserva
      «la versión que cita el registro», que en seg03 es **la peor de las dos**.
      1. [x] Detector re-corrido: **la lista viva coincide en número (17) pero NO en composición**
         con la del 2026-07-27. Los cuatro AcroForm de W-02VND1 (cuentas anuales, tasación) que
         motivaron la restricción dura **ya no aparecen**, y ningún candidato vivo es AcroForm.
         Reparto: W-02VND1 **14** (11 ficheros físicos, del lote judicial `2026-07-23_manual_01`),
         W-02XOR7 **2**, W-02VUDR **1**.
      2. [x] `apply --solo <rel_path>` (repetible) — «force acotado»: procesa esos documentos aunque
         su sha esté hecho y marca skip todo lo demás, conservando la semántica incremental de
         cobertura y estado. Excluyente con `--force`. Una ruta que no case aborta con salida 2
         antes de OCR-izar. `core.sala_maquina.acotar_plan` + 12 tests.
      3. [ ] Medición: **W-02VUDR = falso positivo** (13.977 → 13.870, −1 % de ruido; su MD ya era
         `extractor=ocr`, o sea que la pérdida estaba recuperada de antes). **W-02XOR7 = falso
         positivo también, y CERRADO sin escribir en `G:` (2026-08-01)**, medido en seco sobre copia
         al scratchpad: de sus 2 candidatos, el **Exposé** ya venía recuperado en (c2) (`extractor:
         ocr`, `2026-07-27T16:42Z`, `nota_recuperacion` en el frontmatter) y
         **`753_informeSaintGobainMedidasMejora`** —el único con pérdida técnica real
         (`extractor: pypdf`, `ocr: false`, 2026-07-13, páginas ciegas 4 y 6)— **recupera 8.959 →
         9.291 (+332, +3,7 %) y lo recuperado es la banda de membrete del fabricante** (logos
         rasterizados, domicilio social, CIF), con ruido de OCR (`С/` cirílico, `G о BAI N`). Cero
         contenido probatorio: **no se reprocesa**. La escalera se comportó bien (peldaño 2,
         `degradado=False`, `split.detectar` = 1 segmento → passthrough, luego el defecto (f) no le
         aplicaba). **W-02VND1 = TAMBIÉN falso positivo, y la cifra que este punto declaraba estaba
         mal medida.** Decía que el primer segmento subió «160.685 → 166.324 (**+5.639**)»: 160.685
         son **chars** del frontmatter y 166.324 son los **bytes del fichero MD nuevo**, que incluyen
         frontmatter y multibyte UTF-8. Comparadas las mismas unidades, los tres segmentos que sí se
         reprocesaron el 2026-07-30 dan:

         | segmento | chars antes (`pypdf`) | chars después (`ocr`) | delta | palabras del viejo ausentes en el nuevo |
         |---|---|---|---|---|
         | seg01 | 9.204 | 9.204 | **+0** | 0 de 502 |
         | seg02 | 44.639 | 44.633 | **−6** | 2 de 2.623 |
         | seg03 | 160.685 | 160.973 | **+288 (+0,18 %)** | **77 de 6.405 (1,2 %)** |

         **Los 11 restantes de W-02VND1 NO se corren.** Son del mismo lote y de la misma naturaleza,
         y la muestra medida no da nada.

         **Dos cautelas medidas al cerrar XOR7, aplicables a cualquier `apply --solo` futuro:**
         (1) `apply` **atomiza el correo incondicionalmente** antes del OCR (cableado de PR #151, sin
         flag para saltarlo): en XOR7 eso habría creado por primera vez el árbol de atomización de
         **47 `.eml`** en el Drive, efecto colateral mucho mayor que la corrida pedida. (2) XOR7 no
         tiene `_cobertura.json`, así que la reconstrucción parcial de (f) habría **encogido la vista
         `_cobertura.md` de 169 filas a ~114** (los `sin_soporte` no son reconstruibles). Medir en
         seco antes de correr en vivo evita ambas.

      **Lo que el cribado es, medido:** marca por estructura (páginas que `--skip-text` saltaría +
      firma repetida), no por «le falta texto», así que sigue marcando documentos YA recuperados.
      La medición es el único veredicto — confirmado con el falso positivo de W-02VUDR.

      Cautelas: no lanzar sobre un caso con checkout abierto sin cerrarlo antes (verificado en
      W-02VND1: `estado_repositorio: disponible`, campos `checkout_*` en null, último checkin
      2026-07-27T17:56:49Z; el `_caso.md` vive en `00_Input/`, no en la raíz del caso), y no
      relanzar sin comprobar que la corrida anterior terminó.

- [ ] **(f) Dos defectos destapados al ejecutar (e)** — ninguno lo introduce `--solo`; los activa.
      El primero está arreglado en esta misma rama, el segundo NO:
      - [x] **Cobertura de caso legacy sin `_cobertura.json`.** W-02XOR7 solo tiene la vista
        `_cobertura.md` (169 filas) y `_sala_maquina_state.json`. `_cobertura_previa` devolvía `[]`,
        la fusión se quedaba con el delta y `_escribir_cobertura_md` reescribía la vista: 169 filas
        de custodia → 2, sin error. Le pasaba igual a `apply` normal. Arreglado con
        `reconstruir_cobertura_desde_md` (lee solo la cabecera del MD). **Parcial y declarado:**
        recupera 113 de 169 — los `sin_soporte` no dejan MD y no son reconstruibles; emite aviso.
      - [ ] **El slug de un segmento de bundle depende de su contenido, así que el reproceso no
        sustituye: añade.** `fusionar_cobertura` indexa por `(rel_path, slug)` y nada poda, de modo
        que cada reproceso deja los artefactos anteriores en disco. Afecta a todo reproceso de
        bundles, no solo a D1. **SPEC rev. 3, con DOS revisiones adversariales consumidas (ambas NO
        SHIP)** — `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md`. La
        decisión sobrevivió en dirección pero no en mecanismo: la identidad es un **`doc_id`
        persistente** con ledger monotónico, **no** el ordinal `seg` (que se rompe con `--force`,
        hallazgo B0-2 de la 1ª pasada). **Partida en dos piezas** (decisión de Nikolai, 2026-08-01):

        ⚠️ **Cruce con el motor documental (`MEJORAS #48`), anotado 2026-08-02.** Este `doc_id` es de
        ámbito **bundle**; el `doc-NNN` del id dual de **F1** es de ámbito **caso**, y hasta hoy los
        dos documentos no se citaban. Se parecen y no son lo mismo: F1 tendrá que envolver este
        ledger o migrarlo, nunca abrir un segundo espacio de nombres en paralelo. Ficha del cruce en
        el **§0.1** del spec y en el aviso de **§G.3** de `PLAN_MOTOR_DOCUMENTAL.md`.

        - **Pieza A — motor y esquema. ✅ CONSTRUIDA** (2026-08-02, rama
          `claude/plan-next-step-a429e7`, pendiente de PR). `doc_id` con formato canónico validado
          antes de tocar disco, `next_doc_id` + tombstones, reconciliación del manifiesto en
          `--force`, preflight de todos los manifiestos antes de escribir nada, publicación por
          generación y guard **bidireccional** que aborta con salida 3. No toca ningún caso real.
          Spec **rev. 4** + plan **rev. 2** tras la **ronda 1 de revisión adversarial** (NO-SHIP,
          2 B0 + 13 A + 9 M; 23 confirmados, 1 rebajado), hecha por un **revisor sustituto** —sesión
          limpia de Claude Code, mismo modelo que el autor, con Codex sin cupo—: acta
          `2026-08-02-identidad-segmento-bundle-pieza-a-r1-claude-adversarial-review.md`,
          adjudicación en el §14 del spec. El `B0` que destapó era de diseño: la rama **passthrough**
          no archivaba, así que un bundle que dejaba de detectarse como tal dejaba el caso sin salida
          con `--force` y reintroducía el defecto en silencio sin él. Límites declarados en
          `MEJORAS #117`. **Ronda 2 DECIDIDA (Nikolai, 2026-08-03): la hace Codex el 2026-08-08**, sobre el
          código mergeado (`88339aa`); mandato ya escrito y anclado en
          `docs/superpowers/handoffs/handoff-2026-08-03-identidad-pieza-a-r2-codex-encargo.md`, con su
          adjudicación prevista como §15 del spec. Hasta entonces, el cambio de diseño de la rev. 4 (§6.1 y §7.1)
          **no lo ha mirado ningún revisor de otro modelo**.
        - **Pieza B — retrofit y saneamiento de los 5 grupos. ⛔ BLOQUEADA.** Depende de un lock de
          exclusión que **hoy está roto**: `test_defecto_doble_titular` sigue vivo como `xfail`
          («el write-then-verify no impide dos titulares») y `cmd_checkin` no verifica nonce al
          empezar, de modo que una copia local stale puede **resucitar** un slug retirado vía
          `COPY_LOCAL`. **Gate: la Fase 2 de la fila #3** (arquitectura dual), que es quien arregla
          esos defectos. Ver la nota cruzada en esa fila.

        ⚠️ **La estimación de esfuerzo «bajo» de la cabecera de esta fila ya no describe la pieza.**
        El contrato pasó de «una función y un script» a identidad, ledger, reconciliación, preflight,
        custodia, guard, journal, retrofit y exclusión. Corregido en la tabla de la cola.

        **Censo del daño (2026-08-01, read-only sobre los 5 casos):** 5 segmentos duplicados y 12
        ficheros huérfanos, en 2 casos — W-02VND1 (3 segmentos × 2 versiones) y W-02VUDR (2 × **3**).
        **El defecto es anterior a D1:** los de W-02VUDR están fechados el 2026-07-21. Y W-02VND1
        quedó **internamente incoherente**: su `_cobertura.json` cita los segmentos del 23/07
        mientras el `indice.json` del bundle, regenerado el 30/07, cita los del 30/07.

        La clave que este punto proponía —`parent_sha256`+`role`+`paginas`— **no sirve**: `role` vale
        `"documento"` en los 35 segmentos censados y `paginas` cambia si el letrado edita el
        manifiesto. La clave correcta es `seg`.

**Herramienta ya disponible:** `python -m scripts.detectar_ocr_ciego todos --salida <fuera-del-repo>.md`
(read-only). Es un **cribado**, no un veredicto: de 24 candidatos, 6 eran reales; medir la pérdida
exige re-OCR-izar y comparar. Ver #90 para los falsos positivos ya identificados.

---

## [SIGUIENTE-VISTA-PROCESAL] Vista procesal del expediente en `05_Procedimiento`
*Abierto 2026-07-27 (Nikolai), sobre el expediente CRM 487 / caso `W-02MA0R`. Spec:
`docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md`.*

**Objetivo.** Cinco carpetas procesales en `05_Procedimiento` (monitorio demanda+documentos,
monitorio oposición, ordinario demanda+documentos, ordinario contestación, otros escritos)
construidas desde un mapping explícito `doc_id → carpeta` que decide el letrado, dejando
`00_Input/05_CRM` intacto como espejo del CRM. Objetivo de uso: **leer un procedimiento entero
sin salir de su carpeta**, con el PDF buscable.

**Estado.** Spec **v3.1** al día, con **dos revisiones adversariales de Codex** consumidas (ambas
NO SHIP; 25 + 6 hallazgos, aceptados en sustancia). El plan viejo
(`2026-07-27-vista-procesal-05-procedimiento.md`) está marcado **OBSOLETO**: sus Tareas 1-2 eran el
cambio de esquema de `intake_manifest`, que se cayó al elegir la **opción B** (registro de
ocurrencias nuevo y regenerable). Handoffs en `docs/superpowers/handoffs/handoff-2026-07-27-vista-procesal-codex-*`.

**Partido en cuatro piezas** (decisión de Nikolai, 2026-07-27), porque el diseño acumuló tres
dependencias aguas arriba que no son suyas:

- [x] **1. Veto de grupo en el checkin** — `GRUPOS_MERGE` + acción `VETO_GRUPO`; y el derivado con
      `D=None, B≠None` pasa a conflicto en vez de resucitar. Era **bug vivo**, independiente de esta
      vista. ✅ **PR #137** (`12c8a91`).
- [x] **2. Ocurrencias con estado `listada`/`materializada`** (`core/ocurrencias_crm.py`): sin ellas
      la puerta de integridad era **vacua** con intake acotado, que es el modo de régimen — registro y
      `pull_state` salen de la misma fuente y cuadran siempre. `registrar_listada` corre antes del
      filtro. Resuelve además N1 (revisiones) y H1 (la `TASA ORDINARIO`: dos `doc_id`, mismo SHA,
      misma ruta). ✅ **PR #140** (`86e3abd`).
- [ ] **3. `artifact_sha256` + escritura atómica de la cobertura** (N3). **Ampliada por el hallazgo
      de la sesión concurrente** (`MEJORAS #90`, fila #1 de esta cola): `estado: ok` puede ser
      mentira justo para los documentos con sello de firma, que son la mayoría de lo procesal. Va
      **después** de esa fila, no en paralelo.
- [ ] **4. La vista procesal** encima, ya sin dependencias. Su plan se reescribe desde cero.

**Bidireccional (contexto del 2026-07-27).** Lo que genera el despacho sube al CRM (para el
procurador y para centralizar); lo que llega del juzgado y del contrario baja del CRM. De ahí
`origen: crm | despacho` + `eco_crm` en el mapa. **La subida carpeta → CRM no está construida**: los
endpoints están inventariados en el atlas pero el cliente documental de `core/` solo lee (§7 del
spec) → `MEJORAS_FUTURAS.md`. Y **falta dueño** para la preparación de la documental numerada
(nadie produce hoy el `D-04_chat_whatsapp.pdf`).

**Dependencias con otras filas:** la fila **#1 (OCR ciego)** bloquea la pieza 3 y acota lo que esta
vista puede prometer sobre buscabilidad. La fila **#10 (`.doc`)** no la bloquea —copia el crudo y
avisa— pero la audiencia previa de W-02MA0R la necesita.

---

## [SIGUIENTE-DOC-LIBREOFFICE] `.doc` binario sin MD ni OCR — conversión LibreOffice headless
*Promovido 2026-07-27 desde `MEJORAS #61` (Cluster D) por disparador real. Decisión de Nikolai:
LibreOffice, descartada la conversión vía CRM (`POST /api/documents/convert/doc-to-pdf`) por
complejidad.*

**Problema.** `core/sala_maquina.clasificar_ruta` enruta por extensión a `pdf` | `imagen` |
`nativo` | `sin_soporte`. `_EXTS_NATIVO` incluye `.docx` y `.rtf` pero **no `.doc`** (Word binario
antiguo), que cae a `sin_soporte`: **ni espejo Markdown ni OCR**. Solo queda el crudo, que ningún
LLM puede leer.

**Disparador (lo que lo saca del backlog).** En W-02MA0R la **demanda del juicio ordinario** existe
en el gestor documental del CRM *solo* como `ordinario_vuelta_comprador.doc`, **sin gemelo PDF**.
Cuando se anotó `MEJORAS #61` todos los `.doc` de VALERO tenían gemelo y no había pérdida; ahora sí
la hay, y afecta al documento central para preparar la audiencia previa. En el expediente son 2 de
69 ficheros (el otro es un burofax).

**Qué hacer.** Conversión LibreOffice headless (`soffice --convert-to pdf`) **aguas arriba** de
`clasificar_ruta`, de modo que un `.doc` entre por la vía `pdf` normal y obtenga MD y, si es
escaneado, OCR. Puntos a cerrar en el plan: dónde vive el PDF derivado (no en `00_Input`, que es
crudo), cómo se registra su procedencia, qué pasa si `soffice` no está instalado (degradar a
`sin_soporte` con nota, nunca fallar el lote), y el arranque en frío de LibreOffice en Windows.

**No entra:** los otros dos puntos de `MEJORAS #61` (localizador de página en escaneado, extractor
de entidades con visión) siguen en backlog, sin disparador.

### Por qué es el siguiente paso que mejora la LECTURA (anotado 2026-08-03)

Escrito al cerrar la pieza A de la fila #1, porque el razonamiento vivía solo en un chat y esta cola
es su hogar. **La pregunta que lo motiva fue de Nikolai:** ¿cuál es el paso que mejora la lectura de
los expedientes?

**El contraste que hay que tener delante.** La fila #1 nació como problema de calidad de OCR y lo
resolvió de verdad: (a)+(b) recuperaron **~200.000 caracteres** de prueba en 7 documentos (cuentas
anuales, tasación, exposés). Pero de lo que quedaba, **las dos cosas que habrían mejorado la calidad
se cayeron al medirlas**: **D1** cerró *sin rendimiento* (+0/−6/+288 chars) y **`MEJORAS #111`** quedó
**refutada** (el reproceso relee, no pierde). Lo construido después —la identidad del segmento, PR
#193— es **fontanería**: hace seguro reprocesar, que es la *precondición* de cualquier mejora de
lectura, no la mejora.

**Esta fila es el único sitio de la cola donde un documento es hoy ILEGIBLE del todo.** Verificado en
`core/sala_maquina.py`: `_EXTS_NATIVO` no incluye `.doc`, así que cae a `sin_soporte` — ni espejo
Markdown ni OCR, solo el crudo, que ningún LLM abre. Y el disparador tiene nombre: la **demanda del
ordinario de W-02MA0R**, documento central para su audiencia previa. Esfuerzo bajo y **sin gate**.

**La otra sin gate es `MEJORAS #114`** («no hay contrato de *dame el mejor texto de este documento*, y
`01_OCR/` no lo lee nadie»): calidad **ya pagada** que se queda en el suelo, porque el OCR produce
buscables que ningún consumidor aguas abajo lee. No se promueve aquí —le falta disparador en el
sentido de `CLAUDE.md`— pero es la segunda candidata si el criterio es legibilidad.

**Y un gate que puede estar rancio, que conviene medir antes de creerlo:** la **pieza 3 de la fila #9**
(vista procesal) se declaró bloqueada «por la fila #1». Lo que la bloqueaba era que `estado: ok`
pudiera ser mentira en documentos con sello de firma, y eso lo cerraron (a)+(b) en julio. **No se
afirma que esté desbloqueada** —el texto de esa fila sigue diciendo lo contrario— pero es lo primero
que hay que comprobar si se busca lectura: detrás está *leer un procedimiento entero sin salir de su
carpeta*, con el PDF buscable.

---

## [SIGUIENTE-INPUT-LOTES] Layout de `00_Input` por lotes de entrega (`MEJORAS #54`)

> ✅ **CERRADO (triaje 2026-07-19)** → ledger `## ✅ Cerrados`. Build mergeado (PR #57 `8142d97`). Tail
> operativo (re-import Cowork + migración `migrar_layout_intake` bajo demanda) NO bloquea. Bloque conservado
> como histórico.

*Disparador: decisión de Nikolai 2026-07-17 (4 decisiones fijadas: espejos fuera del modelo
de lotes; M9 índice único de dedup; los duplicados se copian igualmente; la migración remapea
los registros aguas abajo) + spec rev 2 aprobada y MERGEADA (PR #49, squash `32fa663`).
Promovido de `docs/MEJORAS_FUTURAS.md` #54 al arrancar la construcción (regla de promoción).*

Canales de ENTREGA (`whatsapp`, `email`, `manual`, `entrevista`) pasan a lotes append-only
`00_Input/<AAAA-MM-DD>_<fuente>_<NN>/` con `_manifiesto.yaml` (albarán forense, NO fuente de
dedup); canales ESPEJO (`01_Drive EV`, `05_CRM`) conservan cajón fijo + sync incremental
INTACTO (`.pulled`/`reconcile`). Dedup cross-lote vía M9 (`_intake_hashes.json`) + Message-ID
en correos; el duplicado detectado SE COPIA y se anota (`duplicado_de`). Migración de casos
existentes solo bajo demanda, con remapeo de M9/cobertura OCR/catálogo por rel_path.

- Spec (única fuente de verdad del diseño; no reabrir sus decisiones):
  `docs/superpowers/specs/2026-07-17-layout-00-input-lotes-design.md`.
- Plan TDD: `docs/superpowers/plans/2026-07-17-layout-00-input-lotes.md` (16 tareas).
- [x] Revisión del plan por Nikolai (aprobado 2026-07-17).
- [x] Construcción (subagent-driven, Tareas 1→16) ✅ **PR #57 mergeado, squash `8142d97`**.
      Revisión final de rama completa: 0 Critical / 0 Important. Suite 2037 tests, 0 errors
      (5 fallos ambientales sudespacho, ajenos). PR #51 (plan) cerrado como superseded.
- [ ] Operativo tras merge: re-importar en Cowork las skills re-empaquetadas (Tarea 15).
- [ ] Migración de casos existentes SOLO bajo demanda (`python -m scripts.migrar_layout_intake
      <caso>`) cuando reciban intake nuevo; nunca de oficio ni en barrido.
- Fuera de alcance (specs de seguimiento que consumen esta decisión): reenganche fino de
  `email_atomize`/`sala_maquina`/motor de sala de lectura (**#55/#56**), escritor de la
  fuente `entrevista` (**#53**), limpieza de cajones vacíos post-migración.

## [SIGUIENTE-CABLEADO-CORREO] Cableado del pipeline de correo: encadenar la atomización (resto de `MEJORAS #68`)

*Promovido 2026-07-27 por **decisión explícita de Nikolai**, tras verificar el estado real del
pipeline de correo. El disparador que el ítem esperaba (un adjunto relevante que llegue solo por
correo, sin copia en Drive) **no** se ha materializado; se promueve por decisión, no por incidente.
Origen: `MEJORAS #68`. Naturaleza: **cableado**, no motor.*

**El problema en una frase.** Las cinco piezas del pipeline de correo están construidas y ninguna
llama a la siguiente: si alguien no se acuerda de lanzar la atomización a mano, todo lo demás se
comporta como si no existiera.

**Estado verificado (2026-07-27, contra el código, no contra la memoria):**
- **Nadie encadena `atomize_emails`.** Solo lo invocan el CLI manual `scripts/atomize_emails.py` y
  `scripts/audit_correos_no_separados.py` (que importa un helper para auditar). `core/sala_maquina.py`
  **no lo menciona en absoluto**; ni `abrir_caso` tampoco.
- **El contenido de los adjuntos atomizados no llega a la sala.** `sala_maquina` lee `00_Input` por
  invariante declarada (`_ZONAS_VETADAS`, docstring del módulo), así que lo que la atomización deja en
  `01_Procesado/Emails/adjuntos/` queda fuera; sus fichas siguen con
  `Descripción: (pendiente; OCR en fase 2)`.
- **YA RESUELTO, no repetir:** el flag `--extraer-adjuntos` se expone en `scripts/abrir_caso.py`
  (commit `07b0377`), con default `False` **a propósito** — activarlo mueve la superficie de dedup de
  todo intake futuro, y eso es decisión aparte.

**Decisión CERRADA 2026-07-27: opción (ii), dentro de `scripts/sala_maquina.py::apply`**, antes de
construir el plan de OCR. Descartadas (i) `abrir_caso` (la apertura corre una vez; deja sin cubrir
todo caso reprocesado) y (iii) fachada `procesar_expediente()` (mueve el problema: no dice quién la
llama). Tampoco en el SKILL.md: la prosa es justo el mecanismo que falla hoy. Spec:
`docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md` (rev. 2) · revisión
adversarial adjudicada: `…-adversarial-review.md`.

**Corrección del supuesto que justificaba el orden.** Este bloque decía «atomizar antes de la sala
de máquina, o el OCR queda incompleto». **Es falso para el atomizador** y está verificado contra
código: `inventariar` solo recorre `00_Input` (`sala_maquina.py:551`) y ninguna escritura de
`email_atomize` sale de `01_Procesado/Emails`. La frase valía para `--extraer-adjuntos`, que sí
deposita binarios en `00_Input`. Lo que el cableado compra de verdad: orden garantizado por código,
estado de la atomización declarado en el log, y el detector de contaminación cruzada corriendo solo
(hoy solo se dispara a mano, y el patrón ya ha mordido tres veces).

**Frontera con otros ítems — no construir dos veces:**
- El **motor** de extracción/OCR de adjuntos (unificar Docling → OCRmyPDF, cola de visión NO-OP) es
  **`MEJORAS #87`**, no este bloque. Aquí solo se cablea quién llama a quién.
- El **consumo** de las fuentes atomizadas por la sala de lectura es **`MEJORAS #86`**.
- El filtro de ruido del intake de correo es el bloque `[SIGUIENTE-INTAKE-EMAIL-FILTRO]`, distinto.

- [x] **Cerrar la decisión del punto de disparo** — (ii) `scripts/sala_maquina.py::apply`, antes del
  plan de OCR. Cerrada 2026-07-27 en la spec rev. 2; sobrevivió a dos revisiones adversariales.
- [x] Encadenar la atomización en ese punto, con tests que fijen el orden. ✅ **PR #151**
      (`c845a01`): `_atomizar_correo` en `scripts/sala_maquina.py::apply` antes de
      `_construir_plan`; `contar_eml` + derivadores desde `case_dir` en
      `core/email_atomize/pipeline.py`; evento `atomizado_email` (INTAKE_EVENTS 26→27) con
      `status` `ok`/`parcial`/`fallo`/`noop`; fallo blando para el OCR y banner + evento para
      el registro; aviso de `.eml` invisibles (`MEJORAS #98`), `plan` informa y no atomiza, y
      el evento `status: "noop"` cuando el no-op coincide con la discrepancia; `reforzar`
      tampoco atomiza; el motor solo reconcilia un árbol existente si ve TODO el correo (no
      solo si ve cero). +19 tests (16 con doble del motor, 3 contra el motor real).
- [ ] **DECIDIBLE, y sus dos gates ya están pasados** (`MEJORAS #98` **cerrado** en PR #155,
  `03a6f8f`, verificación en vivo del §7 incluida) — queda **la decisión** de si
  `--extraer-adjuntos` pasa a default `True`. El motor ya ve los `.eml` de las subcarpetas, así
  que activarlo no genera ceguera. Gate 1, la corrida de control del §7 (export real de una
  etiqueta pequeña a scratch): **hecha** — 18 `.eml` arriba + 11 en subcarpeta, el motor los ve
  todos. Gate 2, el que añadió la revisión final de rama (¿algún adjunto extraído es a su vez un
  `.eml`, que con la enumeración recursiva pasaría a ser un avistamiento de primer nivel
  indistinguible de un correo del caso?): **medido y negativo** — las 11 subcarpetas traen
  exactamente 1 `.eml` cada una. Es un corpus, no una garantía: volver a medirlo al generalizar el
  flag. Lo que sigue pesando en la decisión es lo de siempre: activarlo mueve la superficie de
  dedup de todo intake futuro.

**Deuda destapada por la revisión adversarial (no bloquea este bloque):** `MEJORAS #98`
(enumeración no recursiva del motor — **cerrada**, PR #155 `03a6f8f`) y
`MEJORAS #99` (el motor no converge bajo
borrados —no poda `adjuntos/`— y publica sin atomicidad, con riesgo de renumerar IDs congelados,
sigue abierta). Por eso este bloque **no promete** un árbol atomizado fresco: declara su estado en
el evento `atomizado_email` y el consumidor debe comprobarlo.

---

## [SIGUIENTE-SANDWICH-FIRMA] La firma no es una respuesta intercalada

*Hallado 2026-07-29 midiendo la verificación en vivo de `MEJORAS #98`, sobre correo real de un caso
de Valencia con hilos de Gmail. Spec **rev. 2**:
`docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md` (su §9 adjudica la
revisión adversarial de Codex, que devolvió NO-SHIP sobre la rev. 1 y obligó a cambiar la decisión).*

**El problema en una frase.** La firma de E&V va en HTML con cada línea en su propio elemento y, en
los hilos de Gmail, queda **entre** dos bloques de cita; `_sandwich` la cuenta como «el autor escribió
entre las citas», declara respuesta intercalada y devuelve **cero ancestros** — con lo que **toda la
Capa B deja de ejecutarse** (body-scan, forma c′ y desanidado del interior no se consultan) y los
mensajes citados no reciben ficha. El cuerpo, en cambio, sí se recorta, porque eso lo decide otro
detector que ahí acierta. Resultado: esos mensajes no están ni como ficha ni en el cuerpo del
portador.

**Medido:** el DOM ve intercalada en 7 de 29 portadores del caso de Gmail y en **1 de 277** de
W-02VND1. De los 7, en **5** todos los trozos disparadores están bajo `class="gmail_signature"` → los
arregla la exclusión estructural; en 2 hay texto de autor real → el veto se mantiene. En W-02VND1 la
regla **no cambia nada**, y su único caso es un contraejemplo legítimo que debe seguir vetado.

> **Corregido al construir (ver las dos erratas de la spec):** el «5» es falso — los portadores que
> cambian de veredicto son **3** y los que conservan el veto **4**; y de esos 3 salen **0 fichas
> nuevas**, porque sus `blockquote` están vacíos. Lo demás de este párrafo se sostiene.

**Decisión (rev. 2):** los trozos bajo un contenedor de firma no cuentan como texto de autor a
efectos del veto. Es estructural, no lexical, y **no puede levantar un veto correcto**: solo resta
firma del recuento.

- [x] Spec + revisión adversarial adjudicada (rev. 2).
- [x] Plan TDD (`docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md`), con **su
      propia revisión adversarial de Codex adjudicada** (veredicto NO EJECUTABLE, 8 de 9 hallazgos
      aceptados) y **construido**. 6 tests nuevos, suite 2561/0/0. Los dos bloqueantes de fondo se
      reprodujeron ejecutando: (1) el fixture generaba frontera MIME aleatoria y el golden habría
      fallado en falso; (2) **una firma sin cerrar levantaba un veto correcto** —la única dirección
      en la que la spec dice que la regla no puede fallar—, resuelto con un guard fail-closed que no
      cuesta ningún portador. Los 6 tests pasaron *mutation testing*: retirar el guard mata
      exactamente su test, y su mensaje de fallo enseña el defecto en vivo.
- [x] Verificación en vivo (§8) ejecutada sobre la copia local, sin tocar `G:`. **El reparto real no
      es el que la spec preveía**, y son dos erratas escritas en ella: los portadores desbloqueados
      son **3, no 5**, y las fichas nuevas son **0, no 4**. Del árbol entero solo cambió
      `_revision/cola.md`: 0 renumeraciones, 3 trazas, 6 punteros `sin_cabecera`, 0 upgrades, y los 4
      portadores cuyo veto es correcto siguen declarados. En `W-02VND1` la regla no cambia nada (247
      con HTML, 1 vetado antes y después).
- [x] **Y el resultado incómodo, que solo salió al medirlo:** el arreglo **no recupera contenido** en
      este corpus. Los `blockquote` de esos 3 portadores están **vacíos** (2 cada uno, 0 palabras;
      `autor == tokens_total`; 0 marcas de cita; 0 `gmail_quote`): no escondían historial citado. Los
      6 punteros salen con extracto vacío. El arreglo es correcto —un correo cuyo único texto entre
      citas es su firma no es una intercalada— pero **el síntoma que abrió la spec (un hilo de 4-5
      mensajes con una sola ficha) no lo explican estos portadores**, y los otros 4 son intercaladas
      auténticas. Dónde están esos mensajes queda abierto en **`MEJORAS #109`**, con `#107` como
      candidato principal. Cerrarlo exige el hilo concreto, así que hay que hacerlo **antes** de
      borrar el corpus de prueba.
- [x] **Revisión de rama completa** consumida (veredicto LISTA CON CAMBIOS, 3 Important + 8 Minor;
      adjudicación en el §correspondiente del plan). Los tres Important eran ciertos y se
      reprodujeron ejecutando: (1) el ámbito de la firma se **fugaba fuera de su elemento** y
      levantaba un veto correcto por una vía que el guard no veía —arreglado, con test que mata el
      mutante—; (2) mi cifra de «20 de 271 correos con la firma abierta» era **falsa** (medida con
      marcadores más anchos que los implementados): son **1 de 271**, corregida en las cuatro copias;
      (3) mi propia Errata 2 prometía de más igual que el párrafo que corregía.
- [x] ✅ **MERGEADO — PR #164, squash `aaf7dc1`.** Suite final 2562/0/0.
- [ ] **PENDIENTE, y con orden:** primero medir el hilo de `MEJORAS #109` sobre el corpus de prueba
      (es la única copia de ese hilo), y solo después borrar del Escritorio `_PRUEBA_98_VaRS3` y
      `_PRUEBA_98_VaRS3_atomizado` — correo real de cliente, con autorización expresa de Nikolai.
- Recordatorio de la spec §5.1 que es fácil de olvidar: **los sellos anteriores son inmutables**. Si
  se revisan las fichas nuevas de un caso con entrega ya sellada, hay que **sellar una entrega
  nueva** (`--entrega`), no dar por actualizada la anterior.
- Contexto de por qué importa: `MEJORAS #108` (que el árbol sea contexto suficiente para un LLM),
  con `#105` y `#106` como las otras dos piezas que faltan.

## [SIGUIENTE-INTAKE-EMAIL-FILTRO] Intake email — filtro de exclusión de ruido administrativo y cruzado

*Disparador: apertura de W-02VUDR (Cr Denia-Javea 14, 2026-07-21). La etiqueta Gmail del
caso, curada antes de esta sesión, traía 14 correos de administración/gobernanza interna
del despacho (facturación mensual a EV MMC, actas CFO+Legal, circularización de auditoría,
cartas de auditores) — y sus adjuntos arrastraban documentos de **al menos 8 casos de
otros expedientes** (W-028QTL, W-02KJHT, BCN-OS-007074, W-02IXUI, W-02HLLB, W-02G6OE,
W-02BDN7, W-02MFGZ, W-02M50U) más los anexos completos de la cartera de litigios del
despacho. Es la **tercera recurrencia** de este patrón (ver memoria
`feedback-intake-email-exclusiones`, 1ª en W-02XOR7 2026-07-13). Remediado en W-02VUDR por
**borrado directo** (no cuarentena — una carpeta de cuarentena sigue siendo visible para
quien tenga acceso Drive al caso; el original vive en Gmail, así que no se pierde nada;
el evento queda en `_intake_log.jsonl`). Root cause sin resolver: la regla de exclusión
solo existe como memoria/prosa, nunca como filtro de código.*

- [ ] **Filtro de código en `core/email_export.py::export_label`** (o paso de triaje previo
  al depósito): excluir por remitente/destinatario `Proveedores.ES@engelvoelkers.com`;
  por patrón de asunto `S/R:.*M/R:.*Cliente: EV MMC.*Contrario:` con referencias vacías;
  por asuntos "circularización auditoría"/"carta de auditores"/"acta reunión CFO"; por
  reenvíos a `mails.repositorio@gmail.com` que casen esos mismos patrones.
- [ ] **Norma de curado de etiqueta**: la etiqueta Gmail de un caso se puebla SIEMPRE
  buscando por la referencia específica del caso (W-code/dirección), nunca por nombre de
  cliente en genérico ("EV MMC SPAIN") — así se evita arrastrar ruido de otros casos.
- [x] **Chequeo post-atomización**: avisar si aparece un W-code DISTINTO al del caso
  actual en el nombre de un adjunto/asunto — señal fuerte de contaminación cruzada (habría
  bastado para detectar los 7 casos ajenos automáticamente en W-02VUDR).
  ✅ `core/email_atomize/contaminacion.py` (capa pura) + gancho en `atomize_dir` → nota en
  `AtomizeReport.notas`. **AVISA, no excluye** (la decisión de borrar es del letrado, coherente
  con el remedio de W-02VUDR); calla si del nombre de la carpeta no se deriva W-code
  (`(SIN REFERENCIA)`); no mira el cuerpo (el letrado referencia otros casos con normalidad).
  +15 tests. Commit `20465ef`.
- [x] **Adjuntos que llegan solo por correo** (`MEJORAS #68.a`, promovido por decisión de
  Nikolai 2026-07-27): `scripts/abrir_caso.py::_intake_email` llamaba a `export_label` con el
  default `extract_attachments=False` **sin exponer el flag** → un adjunto sin copia en Drive
  no llegaba nunca a la sala de máquina. Nuevo `--extraer-adjuntos` (default intacto: activarlo
  mueve la superficie de dedup). +3 tests. Commit `07b0377`. Queda abierto `#68.b` (OCR de los
  adjuntos ya atomizados, que se solapa con `#87`).
- [ ] Backlog relacionado no promovido: auditar si alguno de los 7 casos ajenos tiene a su
  vez documentación de W-02VUDR colada por el mismo motivo (acción de seguimiento aparte,
  no acoplada al cierre de este caso).

---

## [SIGUIENTE-DUAL-WORKSPACE] Arquitectura dual del expediente activo (local/Drive)

*Abierto 2026-07-29 por **decisión de Nikolai**. Spec:
`docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` (**rev. 2**).
Revisión adversarial adjudicada: `…-adversarial-review.md` (veredicto REQUIERE REVISIÓN;
4 B0 + 10 A aceptados y resueltos en la rev. 2, §20). Plan de las dos primeras fases:
`docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`. **Absorbe el Cluster B
(expediente scratch)** del roadmap post-VALERO.*

**El problema en una frase.** No existe un contrato único que determine **qué copia de un
expediente es la operativa**, así que dos puntos de entrada pueden resolver distinto el mismo
caso: durante un checkout, un proceso escribe en el local y otro en Drive.

**Lo que la revisión adversarial midió (contra código, no contra la memoria):**

- **432 apariciones** de `caso_path`/`settings.casos_root`/`resolve_ref`/`path_for` en **80
  ficheros**, y la resolución **no está en las CLIs**: vive dentro de servicios de `core/` que
  reciben `case_id` (`case_manager` 23, `intake_manual` 10, `anon/api` 9, `sala_lectura` 7,
  `email_export` 6…, más `streamlit_app.py` 9). Lo que esta migración reescribe es **la capa de
  servicios de core**, no «los entrypoints».
- **Cuatro escrituras al canon que ya se saltan el guard hoy**: el `mkdir` de
  `intake_log.append_event`; el estado de canal de `email_export`
  (`_save_export_index`/`_save_resolved_links`, que ignoran el destino recibido);
  `catalogo_documental.save_catalog`; y el `_segmentacion.md` que escribe
  `sala_maquina plan`, documentado como «no escribe nada».
- **El doble checkout sigue siendo posible**: `_push_caso_md` es un `copyto` ciego y el
  write-then-verify solo cubre la adquisición.
- **`expedientes-xl` puede sobrescribir el `_caso.md` del canon** (`PROTOCOL_EDIT` en
  `tiers.py`) sin pasar por una línea de Python: la frontera de entrypoints no lo alcanza.
- **`checkout-caso` reimplementa el protocolo en prosa** y no conoce el registro privado.
- **La orquestación del checkout/checkin no tenía un solo test** (los 27 de
  `test_repository_cli.py` son de helpers puros) → por eso hay una **Fase 0**.
  *(Al día 2026-07-29: los PRs #156 y #160 dejaron **16 tests de orquestación** en
  `test_repository_cli_guard_pull.py`. Lo que sigue faltando es el banco completo.)*

**Fases** (cada una: sub-SPEC + plan + revisión adversarial + PR propios):

- [x] **Adelantado (1/2) — guard de LECTURA del protocolo.** ✅ **PR #156** (`5f4c81a`). Dos rutas de
      destrucción de datos que no podían esperar a una fase: un pull fallido del `_caso.md`
      degradaba el fichero canónico a un stub sin `id_go` (y `resolve_ref` dejaba de encontrar el
      caso por W-code); un pull fallido del log **reemplazaba todo el `_intake_log.jsonl` por una
      línea**. Ahora falla cerrado (`ProtocoloIOError`, salida 4, lock conservado). De paso dejó los
      **primeros 8 tests de orquestación** de `cmd_checkout`/`cmd_checkin` que tiene el repo.
- [x] **Adelantado (2/2) — guard de ESCRITURA del protocolo.** ✅ **PR #160** (`fec3444`). Cara B del
      anterior: seis retornos de `copyto` ignorados. El peor imprimía «✓ VERDE … lock liberado» y
      devolvía **0** con el caso todavía `prestado` en el Drive. Frontera escrita como invariante 9
      del módulo: un fallo al escribir **estado de protocolo** (lock, log) es fatal → salida 4 sin
      liberar; uno al escribir **corroboración** (evidencia, redundancia del `MANIFEST`) es aviso
      ruidoso que no bloquea. Incluyó el **8º defecto**: `_integrar_bandeja` devolvía `(0,0)` con un
      `lsjson` ilegible y el checkin liberaba el lock creyendo la bandeja vacía. 16 tests de
      orquestación en total.
- [x] **Fase 0 — banco de pruebas del frontal.** ✅ **PR #170** (`4dba135`, PR-A: barrera + `Entorno`
      + doble + caracterización) y **PR #174** (PR-B: costura, matriz de fallos, los 7 `xfail` y
      gobernanza). Barrera anti-rclone-real + `Entorno` que inyecta las **ocho** fuentes de
      no-determinismo (rclone, reloj, hostname, directorio de trabajo, espera, nonce, usuario y
      binario — eran cinco en la rev. 2 del plan y se contaron mal) + doble de Drive fijado a
      **rclone v1.73.5** con fixtures grabadas y **hook de mutación** para interleaving determinista
      + caracterización de `cmd_checkout`/`cmd_checkin` + matriz de fallos por call-site + los 7
      defectos reproducidos en `xfail(strict=True, raises=AssertionError)`. Sin esto los criterios de
      salida de las Fases 2-3 eran indemostrables.
      **Lo que la fase dejó medido y no hay que volver a medir:** el camino verde del checkin son
      **diez** operaciones rclone y el del checkout **ocho, no siete** (la octava es la sonda
      `_remoto_existe` cuando el `_intake_log.jsonl` aún no existe); el **AMARILLO sale con `0`**, no
      con 1, así que todo aserto de código de salida va emparejado con el estado del lock; y el
      **ROJO de orquestación es inalcanzable** (se retorna antes de clasificar el semáforo).
      **Los siete defectos siguen vivos**: están reproducidos, no arreglados, y su arreglo no es de
      esta fase.
      **Plan ejecutable rev. 4 — EJECUTABLE, sin más gate (8 tareas en DOS PRs):**
      `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-banco-pruebas.md`. Sustituye a las
      Tareas 1-3 del plan combinado, supersedidas. **PR-A** = barrera + `Entorno` + doble +
      caracterización, con el frontal sin tocar; **PR-B** = enhebrar el `Entorno`, matriz de fallos,
      los siete `xfail` y gobernanza. Ni la rev. 1 ni la rev. 2 se mergearon como ejecutables: las
      dos recibieron **NO EJECUTABLE** (3 B0 cada una, de motivos distintos y todos confirmados
      contra el fuente). Los defectos a reproducir son **siete**: se encontraron ocho y el octavo lo
      cerró el PR #160.

      > ✅ **GATE CONSUMIDO — 2ª revisión adversarial hecha y adjudicada (2026-07-29).** Veredicto
      > **NO EJECUTABLE** otra vez, 3 B0 + 4 A + 1 M, **todo confirmado contra el fuente y nada
      > refutado**: la rev. 2 prometía cinco veces una **Task 1B que no existía** (el tajo que la
      > ronda 1 impuso quedó a medias), su barrera **no era implementable** tal como estaba escrita
      > (parchear `subprocess.run` en el frontal es global; `Settings` es `frozen`; `shutil` no se
      > importa), y su matriz mezclaba caracterización con expectativas normativas. Corregido en la
      > **rev. 3**, que además parte la fase en **dos PRs**. La pasada produjo de rebote el PR #160.
      >
      > ✅ **GATE CONSUMIDO — 3ª revisión adversarial hecha y adjudicada (2026-07-29).** Veredicto
      > **REQUIERE REVISIÓN** (de-escalada desde los dos NO EJECUTABLE anteriores): 3 B0 + 2 A.
      > Adjudicado contra el fuente y contra el binario: **5 confirmados, 1 refutado, 1 sin
      > verificar**. Corregido en la **rev. 4**, sin tocar arquitectura, orden de fases ni el
      > reparto en dos PRs.
      >
      > **El bloqueante de PR-A lo creó la propia rev. 3:** al sustituir el helper opt-in de la
      > barrera por un proxy de `subprocess`, no vio que sus Tasks 3-4 **mandan doblar
      > `run_rclone`**, que es la **única superficie de `subprocess` del módulo** (`:391`/`:399`) —
      > doblada, la barrera valida cero comandos justo en los tests que más I/O hacen. Corregido
      > con un validador de operandos compartido entre barrera y doble, más `raiz_local` explícita
      > (`CASOS_ROOT` **no** gobierna `args.local`). Los otros dos B0 —protocolo del hook sin
      > instante de disparo, sin `n_objetivo` ni actor; y `fallos_sub` incapaz de producir `rc≠0`
      > con JSON parseable, además de aplanar `moveto`(1) y `copyto`(3) a un mismo 3— afectan a
      > **PR-B** y se cierran con el canal `resultados` y el `armar(n_objetivo, callback)`.
      >
      > ⛔ **NO HAY 4ª RONDA, y el motivo está medido:** las rondas 1 y 2 rindieron **dos PRs de
      > producción** (#156, #160, dos rutas de pérdida de datos); la 3ª rindió **cero hallazgos de
      > código** y cinco correcciones de redacción. Una cuarta mediría el plan contra sí mismo.
      > **Siguiente paso: construir PR-A.**
- [x] **Fase 1 — núcleo de workspace.** ✅ **PRs #230** (`291436d`, R7 + modelo + registro),
      **#231** (`0d14ab4`, localizador + catálogo), **#232** (`7f29365`, resolver), **#233**
      (`9ad1149`, `intake_log`), **#234** (`17c46a8`, adopción del §15), **#235** (`533be06`,
      sala de máquina por workspace) y **#236** (`86c5414`, Tasks 10-11: matriz contractual + gobernanza, con **R8** adjudicada).
      `CaseRef`/modos/capacidades/errores, registro privado atómico, `CaseCatalog` con
      `AMBIGUOUS_CASE`, resolver, **las tres intenciones del localizador** en vez del booleano
      `strict` (mata el fallback que fabrica expedientes fantasma; censo de la escotilla a
      **cero**), **`core.intake_log` migrado** y `--case-dir` en `scripts/sala_maquina`.

      **Los tres criterios de salida, con su alcance REAL y no con el que me gustaría:**
      (1) la matriz del §14.1 corre sobre los **tres** comandos mutantes de `sala_maquina`
      (`plan`, `apply`, `reforzar`); `apply` la corre entera y los otros dos corren las **cinco
      filas bloqueadas**, con las de escritura declaradas no aplicables y motivo por escrito.
      (2) **acotado tras R8/H8-08:** el plano 2 demuestra que ninguna de esas ejecuciones crea un
      directorio bajo `CASOS_ROOT` para una identidad desconocida, y `test_guard_localizador`
      mantiene a cero el censo de la escotilla. Lo que **no** existe es un barrido que cace a un
      escritor nuevo que componga la ruta a mano y al que la matriz no llame: el criterio se
      cumple **para los caminos ejercitados**, no universalmente, y afirmarlo entero era inflarlo.
      Barrido pendiente anotado en `MEJORAS #121`. (3) con `--case-dir`, el evento de auditoría
      cae en el mismo árbol que los bytes.

      **Lo que la fase encontró y no venía en el plan.** El A-8: `resolve_ref` elegía en silencio
      entre W-codes duplicados, por orden de escaneo. El B0-1, **con un test que lo defendía**: la
      suite exigía que auditar creara `00_Input`, que es la fábrica de carpetas fantasma. Una
      resta de capacidad **inerte** que dejaba a un checkout offline anunciando `CHECKIN`. Once
      fugas del §16 (rutas locales y PII en mensajes), ninguna buscada. Y en el Task 10, dos más:
      `sala_maquina` pasaba `drive_accesible=True` **literal**, así que toda la rama offline del
      §7.2.9-10 era código muerto en producción; y **223 tests en 17 módulos** dejaban
      `core.config` secuestrado en su `tmp_path` —la mina que con la semilla 777 costó ocho
      fallos en el 65º—, ahora cerrada por un guard `autouse` en `conftest`.

      **Lo que NO cierra, dicho para que nadie lo dé por hecho:** los **7 defectos del frontal**
      siguen vivos en `xfail(strict=True)` —verificado: 7 `xfailed`, 0 `xpassed`— y son la lista
      de trabajo de la Fase 2; `MEJORAS #93` no se cierra y sus consecuencias **empeoran** (ver la
      nota de 2026-08-25 en esa entrada: el silencio de `estado_de_fm` ante el campo ausente ahora
      lo consume también el resolver); y quedan `legacy_unresolved` inventariados para la Fase 4.
- [~] **Fase 2 — checkout, scratch y checkin. APARCADA con disparador escrito (2026-08-25,
      decisión de Nikolai), tras extraerle los dos arreglos que sí mordían.**

      **El dato que la aparcó, medido y no opinado:** `scripts/abrir_caso.py` y
      `core/abrir_caso.py` tienen **cero** referencias a `repository_cli`,
      `repository_checkout` o `MANIFEST_CHECKOUT`. **Abrir un expediente nunca presta nada**:
      son dos subsistemas que no se tocan. Lo que la decisión D1 puso como predecesora de la
      apertura integral **no es el préstamo, es la Fase 1** — y la Fase 1 está cerrada. La
      **fila #15 está desbloqueada desde hoy** y no espera a esta fila.

      Y contra la realidad del despacho —tres abogados que prácticamente nunca trabajan un
      expediente en paralelo— **tres de los cinco defectos que quedaban existen para proteger
      de una concurrencia que no se produce**: A-2a (la bandeja se integra sin verificar) y
      B0-2b (el baseline del log) solo muerden si alguien escribe en un caso prestado, y los
      dos A-1 son literalmente el candado.

      **Lo que sí se extrajo y se cerró** (PR de esta sesión): `MEJORAS #96` y `MEJORAS #93-B`
      + el defecto **A-2c**, que son los dos únicos que habían mordido en la vida real —el
      pipeline roto en silencio sobre una copia prestada, y el checkin de W-02VND1 que salió
      verde (431 ficheros, 0 diferencias) y aun así devolvió un traceback que hubo que cerrar
      a mano. Los `xfail` del frontal pasan de **7 a 6**.

      **Disparador para retomarla:** uso concurrente real entre máquinas — que Paola, Ana o
      Sergio empiecen a usar el préstamo, o dos sesiones sobre el mismo caso. Entonces se
      retoma partida en **2a** (integridad del checkin: A-2a, A-2b, B0-2a, B0-2b) y **2b**
      (concurrencia: los dos A-1, `MEJORAS #93-A`, y que `checkout-caso` deje de adquirir el
      lock). El diseño de 2a está razonado en el bloque de cierre de esta
      sesión; **no hay spec escrita y no se escribe hasta que el disparador exista.**

      Siguen fuera, como estaban: la conmutación **atómica** del guard a denegar y la retirada
      de `_pendiente_checkin`, que son de la Fase 3 y exigen inventario sobre casos reales.
- [ ] **Fase 3 — primera vertical**: sala de máquina + correo (con el estado de canal dentro del
      workspace) + `catalogo_documental`.
- [ ] **Fase 4 — resto de scripts y UI** (Streamlit entera; el `CaseWorkspace` no se cachea en
      `session_state`).
- [ ] **Fase 5 — plugins y skills** (el lock entra en la política de zonas de `expedientes-xl`).
- [ ] **Fase 6 — enforcement** (guardas contra nuevos entrypoints mutantes sin workspace).

**Decisiones cerradas que no se reabren** (spec §3 y §20): Drive es canónico una vez publicado;
durante el checkout la copia local es la única escribible; no hay edición simultánea; solo el
titular incorpora documentos; no habrá bandeja nueva de aportaciones; `_pendiente_checkin/` solo
compatibilidad, con retirada por criterio de inventario; prohibido caer silenciosamente en Drive;
se adopta `CaseWorkspace`, **no** una abstracción virtual de almacenamiento (§13, con la puerta
hacia ella conservada en `WorkspaceMaterializer`).

**Deuda anotada, no promovida:** `MEJORAS #101` (residuos `_reingesta_*` de la bandeja),
`#102` (`errors="replace"` corrompe el log canónico), `#103` (el `CaseWorkspace` no se cachea en
`st.session_state`).

---

## [SIGUIENTE-INFRA-POST-VALERO] Roadmap de infraestructura tras la sesión VALERO (2026-07-14)

*Disparador: sesión E2E VALERO (W-02XOR7 / BaRS8) del 2026-07-14 — OCR → sala de máquina → refuerzo por
visión → audiencia previa. La sesión destapó bugs vivos y fricción de fondo. Brainstorming del roadmap y
decisión de arquitectura del Cluster B: `docs/superpowers/specs/2026-07-14-expediente-scratch-design.md`.
Backlog completo (6 clusters) en `docs/MEJORAS_FUTURAS.md` #58-#63. Orden acordado: **A (+C en paralelo) →
B**; D/E/F quedan en backlog. **Actualización: el Cluster A lo completó la sesión paralela (PR #42, `24e69db`); siguiente = C (quick win) o B.***

- [x] **Split de bundles multi-documento — F1 (cerebro) ✅ MERGEADO 2026-07-15 (PR #45, squash `6dba396`).**
  `core/split_documental.py` nuevo (corte por hoja en blanco + fallback marcadores + manifiesto editable +
  `materializar`), `separar.py` tocado solo con el parámetro aditivo `tipos_extra` (congelado, byte-idéntico),
  evento `split_documental`. Construido subagent-driven (11 tareas TDD); revisión final Opus "ready to merge".
  Plan `docs/superpowers/plans/2026-07-14-split-sala-maquina.md` (spec+plan del PR #43). **F2 (integración en
  `core/sala_maquina.py`, Tareas 12-15 + 13B) ✅ CONSTRUIDA** (suite 2222 verde): split enganchado entre OCR y
  MD, cobertura y estado idempotente por documento lógico, `--force` regenera el manifiesto y passthrough
  robusto si la detección falla. Follow-ons en `MEJORAS #78/#79`. ✅ **MERGEADA** (PR #109, `cc13355`) → ledger `## Cerrados`.
  Deferidos F0 (calibración umbrales + fixture página-imagen) y F2 (contratos M-A/M-C) en `MEJORAS_FUTURAS #64`.

- [x] **A — Fiabilidad de la sala de máquina (`MEJORAS #58`) — ✅ HECHA (PR #42, `24e69db`, sesión paralela).** (1) Bug: `apply` incremental
  machaca `_cobertura.md` (`scripts/sala_maquina.py::apply` debe **fusionar** el estado previo, no volcar
  solo `cob`) — pérdida silenciosa de "qué queda por revisar". (2) `--vision` cableado a un transcriptor
  real (preferente la sesión Claude) o que **avise** en vez de no-op (`core/sala_maquina._transcribir_vision`).
  (3) Comando `reforzar` persistente (render→visión→MD+estado+cobertura). *En VALERO la cobertura de 35 filas
  se perdió y el refuerzo de visión hubo que persistirlo a mano.*
- [~] **B — Expediente scratch (caso de trabajo local) (`MEJORAS #59`) — ABSORBIDO 2026-07-29 por
  `[SIGUIENTE-DUAL-WORKSPACE]`.** Nunca se construyó (verificado contra código: `--case-dir` **no existe
  en ningún script** y `--casos-root` solo en `scripts/migrar_nombres_informe.py`, así que el override de
  `CASOS_ROOT` por entorno —lo que este cluster venía a eliminar— sigue siendo hoy la única vía). Sus tres
  piezas pasan a ser piezas de la arquitectura dual: el modo `local_scratch` (§5.2), el flag `--case-dir`
  (§7.1, Fase 1) y el comando `promover` (§8.6, Fase 2). No se planifica por separado: se cerraría dos
  veces lo mismo. El diseño `2026-07-14-expediente-scratch-design.md` se conserva como antecedente.
- [ ] **C — Campos de `gen_solicitud` (`MEJORAS #60`; fichero real `.claude/skills/preparacion-audiencia-previa/scripts/gen_solicitud.py`, no `scripts/` de la raíz) — quick win, en paralelo a A.** Petición subsidiaria de
  averiguación de domicilio (art. 156 LEC) como campo + DNI pendiente que renderice limpio. Disparador:
  la testigo compradora (petición de averiguación de domicilio, art. 156 LEC) y la testigo directora de zona (DNI pendiente) en la AP de VALERO.
- Backlog (no promovidos): **resto de #61** — localizador de página en escaneado y extractor de
  entidades con visión (su **punto `.doc`/soffice sí está promovido**: ver
  `[SIGUIENTE-DOC-LIBREOFFICE]` en la cola) —, **#62** entorno Windows (`setup_windows_deps`) +
  unificar el `.bat` de OCR, **#63** sincronización de la providencia/DIOR de señalamiento a
  `00_Input`.

## [abrir-caso] ✅ F1 + F2a + F3-(A+C) mergeadas; F2b APARCADA; F3-judicial pendiente

*Disparador: encargo de Nikolai (spec v0.1 `SPEC_ABRIR_CASO.md`, fuera del repo). Abrir un expediente
E&V en una pasada (alta + intake + CRM), uniendo piezas ya existentes. Patrón «biblioteca»: cerebro
puro + orquestadores finos. Spec: `docs/superpowers/specs/2026-07-09-abrir-caso-design.md`. Plan F1:
`docs/superpowers/plans/2026-07-09-abrir-caso-f1.md`. Memoria `project-abrir-caso-f1`.*

- [x] **F1 (cerebro puro + CLI local, fuente `drive_ev`) — MERGEADA** (PR #13, squash `9fb0757`).
  `core/abrir_caso.py` (`componer_case_id`/`resolver_identidad`/`plan_intake`/`reconcile`/`crm_payload`)
  + CLI Typer `scripts/abrir_caso.py` (gate CRM, hash SHA-256 local, `--dry-run/--force/--yes/--crm skip`).
  Promovió `intake_drive.CONTROL_FILES`. +29 tests; suite 1599 verde. Decisiones: ambos frentes,
  colisión `ask`, CRM con gate, hash tras el pull, CLI en módulo nuevo.
- [x] **F2a — primitivas del conector — MERGEADA** (PR #16, squash `a66bc3b`). `hash_tree` +
  `strip_top_level` en `plugins/expedientes_xl/` (`fsops.py`+`server.py`+tests). Plan
  `docs/superpowers/plans/2026-07-09-abrir-caso-f2a-conector.md`.
- [x] **F3-(A+C) — fuentes no-Drive + init_caso — MERGEADA** (PR #22, squash `e68f59e`).
  CLI `--fuente manual|whatsapp|email` por delegación a los escritores nativos (`intake_manual`,
  `whatsapp_intake.deposit_export`, `email_export.export_label`), custodia forense uniforme (evento
  `upload_manual` cierra el hueco de que el intake manual no hasheaba). Regla: whatsapp/email auto-logean;
  drive_ev/manual los logea el orquestador (`_intake_generico`). Una fuente por invocación, reentrante.
  **`init_caso.py` se CONSERVA** (atajo ligero solo-esqueleto; sin disparador de deprecación, decisión
  Nikolai). Spec `docs/superpowers/specs/2026-07-10-abrir-caso-f3-fuentes-design.md` · plan
  `docs/superpowers/plans/2026-07-10-abrir-caso-f3-fuentes.md`. +12 tests, leak-scan verde.
- [~] **F2b — skill Cowork `abrir-caso` — APARCADA** 2026-07-10 (decisión Nikolai tras red-team
  adversarial). Bajo ROI (CRM no corre en Cowork, la CLI local ya hace todo, el intake duplicaría
  `intake-expediente`) + huecos de viabilidad (Cowork sin listado/lectura-de-log; handoff exigiría
  tocar `core/`). Hallazgos reutilizables (esp. **`_caso.md` es de dos niveles con el lock en `meta`**)
  en `docs/superpowers/specs/2026-07-10-abrir-caso-f2b-skill-cowork-design.md` (estado: aparcado).
  Reabrir solo con necesidad real de abrir un caso desde Cowork/móvil.
- [ ] **F3-judicial (parte B) — disparador CONFIRMADO 2026-07-22 (W-02ZIIF, caso real que
  escaló a judicial durante su propia apertura).** Expediente **judicial** en el CRM
  (`NuevoExpedienteJudicial`/`create_expediente_judicial`/element `expedientes_judiciales`).
  **Corrige la nota anterior de este mismo ítem:** "juzgado propiedad no-relación → 404"
  estaba incompleto — el mecanismo real es una relación CON ATRIBUTOS PROPIOS vía el
  elemento intermedio `autos` (secuencia REST de 4 llamadas confirmada en vivo, detalle en
  `docs/INTEGRACION_SUDESPACHO.md §12.5`). Piezas concretas a construir (esfuerzo bajo,
  mirroring mecánico desde plantillas ya existentes — construcción directa o subagentes, **no
  rediseño**; la nota anterior lo daba como «candidato a delegar a Gemini/agy», vía retirada el
  2026-08-01, ver `docs/DEAD_ENDS.md`):
  1. `get_expediente_judicial()`/`update_expediente_judicial()` en `sudespacho_create.py`
     (mirror de `get_expediente`/`update_expediente`).
  2. `ensure_contrario_vinculado_judicial()` en `sudespacho_relations.py` (mirror de
     `ensure_contrario_vinculado`, usando `link_contrario_judicial`).
  3. `link_juzgado_judicial(exp_id, juzgado_id, num_autos, fase_procedimiento)` — nuevo,
     implementa la secuencia de §12.5 resolviendo `fase_procedimiento` vía
     `GET /api/view/enums/autos/fase_procedimiento` (nunca hardcodeado).
  4. Ramificar `scripts/crm_ficha.py` (hoy hardcodea `_ELEMENT_EXTRAJUDICIAL`) para que
     use las piezas judiciales cuando el expediente registrado en `_caso.md` sea judicial.
  Aparte, sin confirmar: `POST /api/expedient/convert/{id}` (extrajudicial→judicial) —
  ver `docs/MEJORAS_FUTURAS.md` **#81**.
- Relacionado: `docs/MEJORAS_FUTURAS.md` **#50** (sección "Relación con el ecosistema" en todas las skills).

## [SIGUIENTE-SALA-HILOS] Bundle por hilo de correo en la sala de lectura (Slice 1)

> ✅ **CERRADO (2026-07-27)** → ledger `## ✅ Cerrados`. Construido, revisado y mergeado en **PR #131**
> (`d27172b`), skill **v1.14**, suite 2366/0/0. Bloque conservado como histórico. **Tail operativo que
> NO bloquea: re-importar el `.skill` v1.14 en Cowork** (si no, Paola/Ana/Sergio siguen en la v1.12).

*Spec: `docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md` (re-tajada
2026-07-27). Revisión adversarial adjudicada: `…-adversarial-review.md`. Origen: `MEJORAS #75`
(promovido parcialmente). Plan TDD: `docs/superpowers/plans/2026-07-26-sala-lectura-bundle-por-hilo.md`.
Implementación: Claude Code.*

**Objetivo.** Que la correspondencia ocupe **una entrada por hilo** en la sala, no una por mensaje: un
caso de ~277 correos deja de producir ~277 ficheros sueltos y ~277 líneas de índice.

**Tres cambios, todos dentro del `.skill`** (scripts stdlib puro, sin instalación nueva para el
equipo): (1) forma de copia = un bundle fechado por grupo de hilo, con el `.eml` de fecha cierta más
antigua como principal y el resto + adjuntos MIME como anexos con su fecha propia (grupo de 1 sin
adjuntos → plano); (2) `INDICE.md` colapsa bundles a una línea con `(+N anexos)` —`construir_indice`
emitía una línea por fila sin mirar `parent_id`, así que agrupar en carpetas por sí solo no habría
reducido nada— mientras `CRONOLOGIA.md` se deja intacta; (3) el nombre del bundle se fija en la primera
corrida y nunca se renombra.

**Dos correcciones que el build impuso al diseño** (ver bitácora del 38º cierre): la clave de
`agrupar_por_hilo` **tuvo que cambiar** (agrupaba colisiones del mismo día y asunto, no hilos), y la
afirmación «idempotencia sin algoritmo nuevo» del §3 del spec **era falsa para bundles** — el nombre de
carpeta y de anexo eran estado derivado del grupo, con tres caminos de pérdida/sobrescritura que
encontró la revisión final. Remedio: **nombres como función pura del fichero de origen**.

**Lo que este ítem NO hace** (salió del alcance en el re-tajo): no consume `01_Procesado/Emails/`
(→ `MEJORAS #86`), no toca el motor OCR de adjuntos (→ `MEJORAS #87`), no introduce threading por
cabeceras RFC (→ `MEJORAS #88`), no toca `email_atomize` ni `core/anon`.

- [x] Plan TDD (`superpowers:writing-plans`) + implementación de los 3 cambios.
- [x] Tests del §6 del spec, +10 tras la revisión final (estabilidad del nombre de anexo entre
      corridas, `carpeta_existente` sin candidato, `plano_existente`, basenames repetidos).
- [x] Skill → **v1.14** (`main` había tomado la 1.13) + CHANGELOG; `.skill` re-empaquetado.
- [ ] **Re-importar el `.skill` v1.14 en Cowork** (acción manual de Nikolai; ningún test lo cubre).

---

## [SIGUIENTE-PRECLASIFICACION-SALA-LECTURA] `preclasificar` mecánico + copia `rclone rcd` + verify

> ✅ **CERRADO (2026-07-23)** → ledger `## ✅ Cerrados`. 16/16 ítems del backlog construidos y
> revisados (v1.12, PR #116 + PR #121 mergeado). Bloque conservado como histórico.

*Disparador: medido en vivo en la apertura de W-02VUDR (2026-07-21) — la clasificación de
`organizar-sala-lectura` tardó 14 min y la fase de copia+índices más de 30 min sobre 172
documentos. Plan TDD completo ya escrito: `docs/superpowers/plans/2026-07-21-preclasificacion-sala-lectura.md`
(5 Tasks, formato `superpowers:writing-plans`, con historial de revisión de 7 puntos y auto-revisión).
Deferida explícitamente a "otra sesión dedicada" (decisión de Nikolai, misma sesión) para poder medir
el antes/después sin mezclar la construcción con el caso real.*

- [x] **Task 1-2** — `preclasificar.py` (patrón con "07. RECLAMACIONES" como DEFAULT, hilo de
  email por sufijo `_N`, dedup sha256, subcategoría CRM, lookup del espejo MD de sala de máquina).
  Self-contained, sin `import core`; test anti-drift contra `core.config.TAXONOMIA_EV`. PR #112.
- [x] **Task 3** — enganchar los helpers en `SKILL.md` (Paso 1-bis), plan persistido a fichero
  ANTES del gate, gate condicional (solo si hay anomalías genuinas), sub-agrupación de
  "07. RECLAMACIONES" por subcategoría CRM en el `INDICE.md`. PR #112.
- [x] **Task 4 (v2)** — `copiar_manifiesto_rclone.py` (copia+renombrado en bloque vía `rclone rcd`,
  evita el reinicio del "pacer" de cuota). Nikolai configuró el client OAuth propio del despacho
  en la misma sesión (proyecto `rclone-despacho-drive-2026`) para `gdrive_ev`/`gdrive_tl`. Paso 7
  (verificación en vivo) ejecutado sobre W-02VUDR vía `gdrive_tl`: 10/10 ficheros copiados
  server-side en 57.5s, 0 `403 Quota exceeded` en logs `-vv`, carpeta de prueba purgada tras la
  verificación. **Hallazgo aparte:** `gdrive_ev` da "Shared drive not found" con el client nuevo
  (reauth probablemente con cuenta de Google sin acceso a ese shared drive, o falta test user) —
  pendiente de revisar, no bloqueaba esta Task porque `gdrive_tl` sirvió para verificar. PR #112.
- [x] **Task 5** — `verificar_sala.py` (fase verify con criterios duros: manifiesto vs. disco,
  anexos huérfanos) enganchada como Paso 6.5, antes de reportar éxito. PR #112.
- [x] **Seguimiento — re-corrida A/B sobre W-02VUDR (2026-07-21).** Reveló 7 errores reales de
  proceso (checkout obsoleto, diagnóstico erróneo de OAuth de rclone, falso positivo de verify
  parcheado a mano, `ERROR_FILE_NOT_HYDRATED` recurrente, 2 regresiones de calidad/dedup, tiempo
  total peor que la línea base por el overhead de los anteriores) — la comparación limpia de
  velocidad de Tasks 1-3 sigue sin lograrse (queda en el nuevo backlog, ítem 16).
- [x] **Fixes puntuales de la re-corrida (PR #114, `main` `117b7c1`):** `verificar_sala` reconoce
  `parent_id` como carpeta de bundle; `_rc_activo` usa POST no GET; `verificar()` detecta fecha
  `0000-00-00` con texto ya extraído (incl. el hueco de `parent_sha256` en bundles spliteados,
  cerrado antes de mergear). Incidente de datos aparte: fichero de otro caso (W-02X270) copiado
  por error a la sala real, borrado y documentado en su `_MANIFIESTO.md`.
- [x] **Auditoría con Fable 5 (Workflow, 2026-07-21):** análisis de los errores de ambas pasadas +
  revisión holística de `SKILL.md` v1.10 → backlog priorizado de 16 ítems (9 alta / 5 media / 2
  baja), 4 patrones de fondo identificados (juicio de agente donde cabe un check determinista;
  fallos recurrentes sin ruta de resolución automática; edición a mano de artefactos generados
  para pasar el verify; telemetría de fases ausente). Backlog completo, con fichero/cambio/por
  qué por ítem:
  `docs/superpowers/plans/2026-07-21-robustez-velocidad-sala-lectura.md`.
- [x] **Ejecución del backlog — 8 ítems de PRIORIDAD ALTA (PR #116).** Backlog convertido a plan TDD
  `docs/superpowers/plans/2026-07-21-robustez-velocidad-sala-lectura-tdd.md` (11 Tasks) y ejecutado
  con `superpowers:subagent-driven-development`. HECHOS los 8 de alta: **(1)** `senales_gate` por
  código (W-code ajeno/casi-duplicado/binario-sin-espejo/parte); **(2)** versión 1.11 + guard
  frontmatter↔CHANGELOG (`tests/test_sala_lectura_version_changelog.py`) + Paso 0 frescura del
  checkout (aborta, nunca auto-repara sobre la raíz compartida) + gotcha de subagentes; **(3)**
  colisión de `nombre_canonico` en `verificar()` + `validar_pares` aborta la copia antes de tocar
  Drive; **(4)** prohibición de editar artefactos generados + aviso de fallos homogéneos (≥5 mismo
  tipo → sospecha del check); **(5)** fallback `ERROR_FILE_NOT_HYDRATED` → `copiar_renombrar` (rcd)
  cableado en Paso 4; **(6)** `precheck_rclone.py` (prerrequisito OAuth por exit code, sin volcar
  secretos); **(7)** CLI de `verificar_sala.py` (parser compartido `manifiesto_parser.py` + listado
  + `--cobertura`/`--hash`); **(8)** columnas `categoria`/`subcategoria_crm` en `_MANIFIESTO`+YAML
  (`CatalogEntry`) + `indices_desde_manifiesto.py` (INDICE/CRONOLOGIA por script). Suite 2281/0/0
  (+70 skip). Skill v1.11 re-empaquetada; **re-import del `.skill` en Cowork PENDIENTE**.
- [x] **CONSTRUIDO Y REVISADO (3ª sesión) — 8 ítems de PRIORIDAD MEDIA/BAJA (9-16)** del backlog,
  vía `superpowers:subagent-driven-development` (9 Tasks). Plan TDD:
  `docs/superpowers/plans/2026-07-22-robustez-velocidad-sala-lectura-tdd-9-16.md`. Skill **v1.12**
  (frontmatter + CHANGELOG). Hecho: progreso JSONL durable por fila + reanudación de corrida
  interrumpida en `copiar_manifiesto` (9); lectura del representante de cada hilo `.eml` que cae
  al `07` por defecto (10); dos bugs deterministas de `preclasificar` — `agrupar_por_hilo` ya no
  fusiona por una cifra suelta del asunto y `emparejar_exports_whatsapp` excluye el zip crudo
  `_export_original.zip` (11); `parse_manifiesto` con `estricto=` — aborta filas con nº de columnas
  incorrecto (12); `sha_valido` admite `md5:` para el Modo 3 degradado en binarios grandes (13);
  timeout parametrizable + modo `async` + `copiar_manifiesto_rclone` gestiona el ciclo de vida de
  su propio `rcd` (14); `fecha_aproximada` separa el marcador `(*)` del valor de fecha en el
  catálogo YAML (15); telemetría de fases en el plan persistido (16). Suite completa verde (2307
  tests, 0 failures, 0 errors, 70 skipped). PR #121 — el merge es el paso de cierre posterior
  a esta sesión.
- [ ] **Seguimiento operativo (no bloquea):** 3ª corrida real A/B de velocidad sobre un caso real,
  ahora con la telemetría del ítem 16, para por fin medir limpio el antes/después — las dos pasadas
  anteriores quedaron invalidadas por los errores que este backlog corrige.
- [x] **RESUELTO (2026-07-22, apertura de prueba W-02ZIIF):** `gdrive_ev` estaba autenticado con
  la cuenta/proyecto equivocados — `rclone backend drives gdrive_ev:` devolvía las Shared Drives
  del DESPACHO (ADMINISTRACION, EXPEDIENTES - TYUKHAY LEGAL, JURIDICO...), ninguna de Engel &
  Völkers. Causa: el proyecto OAuth `rclone-despacho-drive-2026` está en modo Testing y la cuenta
  `nikolai.tyukhay@engelvoelkers.com` no estaba en la lista de test users (solo la cuenta TL, de
  ahí el desvío). Arreglado añadiendo esa cuenta como test user en Google Cloud Console + `rclone
  config reconnect gdrive_ev:`. Confirma que **no** era un problema introducido por la prueba de
  apertura en local ([[project-apertura-local-vs-drive]]) — bloqueaba `--fuente drive_ev` de
  cualquier caso E&V nuevo, en local o en Drive.
- Deferida sin construir en esta sesión: Task 6 (agrupar `doc_NN_*` de una demanda+anexos del CRM en
  subcarpeta) — bajo ROI para un solo expediente; ver `docs/MEJORAS_FUTURAS.md` **#80** (verificar
  dedup de `sync_sudespacho pull` contra "05. Procedimiento" antes de reabrir esto).

## [SIGUIENTE-MCP-DRIVE-DISCO-PASOS-5-7] Drive-disco: pasos 5-7 + bundle Claude Code

*V1 construido (PR #52) y DESPLEGADO 2026-07-19 (fase 1) en Cowork/Desktop vía `.dxt` (PR #83).
**Fase 2 (2026-07-19):** lado-repo cerrado (migración de skills + docs). Quedan las acciones de
máquina (re-import en Cowork, bundle Code con reinicio, paso 7). Checklist operativo:
`docs/DESPLIEGUE_MCP_DRIVE_DISCO.md`.*

**➡️ PUNTO DE RETOME (despliegue pasos 5-7, 2026-07-19).** Paso 7 **COMPLETO** (server viejo `expedientes`
jubilado en Code **y** Desktop). Bundle Code verificado en vivo. **Único resto pasivo:** verificación funcional
de `organizar-sala-lectura` Modo 1 el próximo caso real (por diseño, no gastar una corrida solo para probar).
1. **Bundle Code (B1-B3) ✅ HECHO+VERIFICADO.** `claude mcp list` (raíz) = `plugin:feesdefender:expedientes-xl`
   Connected, **19 tools sin `delete_path`**; `list_dir`/`get_metadata`/`read_text` sobre `G:` OK; poda Tier 0
   OK. Corrección de scope: el standalone y el server viejo estaban en **`-s local`**, no `project`.
2. **Paso 5 gate — decidido por Nikolai:** «jubilar ya el server viejo» (no esperar a caso real).
3. **Paso 7 · Parte B (Code) ✅ HECHA+VERIFICADA:** `claude mcp remove "expedientes" -s local` (desde la
   raíz); `claude mcp list` confirma `expedientes` fuera, queda `expedientes-xl` (Code no se quedó sin FS).
4. **Paso 7 · Parte A (Desktop/Cowork) ✅ HECHA+VERIFICADA:** se retiró `expedientes` desde el **panel de la app**
   (Ajustes → Desarrollador → Servidores MCP locales → papelera) + relaunch — **la vía limpia**, sin `taskkill`.
   Confirmado autoritativo: `claude_desktop_config.json` solo tiene `email-export`; `expedientes` fuera del panel.
   *Aprendizaje:* la papelera del panel es una acción propia de la app que actualiza su estado en memoria y
   reescribe el config → evita el auto-kill del `taskkill /IM claude.exe /T` desde un terminal hijo de Claude
   (que fue lo que hizo fallar el intento por script; ver `docs/DEAD_ENDS.md`). El script
   `Desktop\jubilar_expedientes_node.ps1` v2 (guarda de ancestría) queda como plan B documentado, no usado.

- [x] **Paso 6 (migración de skill) — ✅ repo fase 2.** `organizar-sala-lectura` v1.8 migrada al
  consolidado: `write_file`→`write_text`, `read_media_file` retirado (binarios server-side); tres
  modos por ubicación del caso (Drive `expedientes-xl` / local-nativo / conector nube prefiriendo
  `google-despacho`). Además `intake-expediente` v1.2 (gotcha dict `extract_archive`/`copy_dir`) y
  `checkout`/`checkin` con frontmatter canónico + CHANGELOG. `CLAUDE.md` y `MEJORAS #40` alineados.
  Tests de skills 66/66; `validate_skills`/`check_skills` limpios para las 4.
- [~] **Paso 5 (re-empaquetar + re-import Cowork).** ✅ re-empaquetadas (4 `.skill` en
  `dist/skills/`); ⏳ **re-import en Cowork** = acción manual de Nikolai.
- [x] **Bundle Claude Code — ✅ HECHO+VERIFICADO 2026-07-19.** B1 (retirar standalone, scope real `local`)
  + B2 (`plugin marketplace update despacho-tyukhay` + `plugin update feesdefender@despacho-tyukhay`
  v0.1.0→0.3.0) + B3 (reiniciar Code). `claude mcp list` = `plugin:feesdefender:expedientes-xl` Connected,
  **19 tools sin `delete_path`**; `list_dir`/`get_metadata`/`read_text` de `G:` OK.
- [x] **Paso 7 (jubilar `expedientes` Node) — ✅ COMPLETO 2026-07-19.** Parte B (Code):
  `claude mcp remove "expedientes" -s local` (scope real **`local`**, no `project`; desde la raíz). Parte A
  (Desktop): retirado desde el panel de la app (Ajustes → Desarrollador → papelera) + relaunch — vía limpia sin
  `taskkill`. Confirmado: `claude_desktop_config.json` solo con `email-export`; `expedientes` fuera de Code y
  Desktop; `expedientes-xl` (FS) operativo. Gotcha del auto-kill del `taskkill` en `docs/DEAD_ENDS.md`.
- [x] **`MEJORAS #74`** (oracle perezoso) — ✅ **RESUELTO 2026-07-20 (PR #101 `c2f6240`; extensión `.dxt` 1.1.0 #105 + bundle Code 0.4.0 #102).** Causa CONFIRMADA:
  `server.main` escaneaba las BD DriveFS (`descubrir_cuentas`) antes de `.run()` → `initialize` MCP tardaba
  8-11 s (medido) → Claude Desktop marcaba `failed` (intermitente: frío→failed, caliente→conecta). Fix:
  `oracle.LazyOracle` difiere el escaneo al primer uso; TDD (5 tests). Despliegue: merge + `git pull` en la
  raíz + reiniciar Desktop (la `.dxt` corre el código vivo del repo; no hace falta reempaquetar).
- V2/CUT motivados en el spec §5 y en `docs/MEJORAS_FUTURAS.md` #66. Promoción solo por disparador.

## [SIGUIENTE-GOOGLE-MCP] F1 (lectura) ✅ MERGEADA · F2 (escritura+permisos+navegación) ✅ MERGEADA · F3/F4 pendientes

*Disparador: encargo de Nikolai (`ENCARGO_MCP_Google_despacho.md`, fuera del repo). MCP propio
`google-despacho` (Drive + Calendar, multicuenta EV+TL) que suple la mono-cuenta del Drive nativo.*

- Spec APROBADO + revisado: `docs/superpowers/specs/2026-07-08-google-despacho-mcp-design.md`.
  Plan de F1: `docs/superpowers/plans/2026-07-09-google-despacho-mcp-f1.md`. Rama `feat/google-despacho-mcp`.
- Decisiones cerradas: **un MCP por fases F1(lectura)→F2(escritura+permisos)→F3(lote+intake)→F4(Calendar)**;
  entrega **stdio local + `.dxt` + puente de escritorio**; **`expedientes` se queda** (solo candidato a
  retirar el Drive nativo); OAuth reutiliza el proyecto Cloud de Gmail; ubicación `plugins/google_despacho_mcp/`.
- [x] **R2 CERRADA (2026-07-09):** app ya `En producción` (no `Testing`) → caduca-7-días **no aplica**.
  Decisión: **un solo cliente OAuth, External + Producción, SIN split, NO marcar Internal**. §11 R2 del spec.
- [x] **F1 CÓDIGO COMPLETO (2026-07-09, subagent-driven + revisión adversarial):** `plugins/google_despacho_mcp/`
  (`google_auth` scope `drive.readonly`, `drive_ops` puro, `server` FastMCP con 9 tools de lectura + DL-root,
  `google_cli`, `run_server.bat`, README). **29 tests; suite completa 1570 verde.** La revisión adversarial
  cazó y cerró: bypass de DL-root vía symlink (`_resolve_dest` ahora usa `realpath`), mis-atribución de
  procedencia en el fan-out (`{**f, "account": acc}`), hueco de `max_bytes` post-fetch, import-safety en `.venv`.
- [x] **F1 VALIDADA EN VIVO (2026-07-09):** ambas cuentas conectadas (`~/.google-despacho/tokens/`); humo real =
  105 unidades compartidas EV / 10 TL (incl. «EXPEDIENTES - TYUKHAY LEGAL»), recientes, `about.get`, descarga
  (`get_media`→bytes+sha256) y confinamiento DL-root. Cableado en `claude_desktop_config.json`.
- [x] **F1 MERGEADA (2026-07-09):** PR #12 (`4056d6b`), rama+worktree podados; cableada en `claude_desktop_config.json` y **confirmada end-to-end desde Cowork** por el puente (`list_shared_drives` = 10 unidades TL + 5 EV cross-drive). Entrega vía `.dxt` (una entrada cruda en el config NO se expone al motor de tools de la nube).
- [x] **F2 COMPLETA + MERGEADA (2026-07-10):** PR #23 (squash `52a5845`), rama `feat/google-despacho-mcp-f2` podada. Plan `docs/superpowers/plans/2026-07-10-google-despacho-mcp-f2.md`; spec §13. **19 tools** (13 escritura + 3 permisos con guardarraíl `allow_external` + 3 navegación); scope OAuth `drive.readonly`→`drive`; UPLOAD-root simétrico al DL-root; `sha256` sobre bytes enviados. Subagent-driven; **la revisión adversarial del guardarraíl cazó 3 huecos fail-open** (perm_type/role sin normalizar + escalada de permiso externo en `update`) → fail-closed + tests de regresión. **Suite 1685 verde.**
  - [ ] **Operativo tras merge:** reautorizar TL + EV una vez (`python plugins/google_despacho_mcp/google_cli.py add`; scope subió a `drive`) + check de integración manual (§13.6) contra carpeta desechable de Drive.
  - [~] **INSTALACIÓN EN APP/COWORK — vía script `.ps1` DESCARTADA (2026-07-20).** El objetivo (sesión 2026-07-15, rama `claude/multi-drive-connector-install-9d4964`) era instalar `google-despacho` a mano —vía `instalar_extension.ps1`— saltándose la pantalla Ajustes→Extensiones colgada de la build `1.21459.0.0`. **Descartado (decisión Nikolai 2026-07-20):** el `.ps1` nunca se commiteó (vivía en la rama `wip/mejora-archivar-caso`, podada 2026-07-20) y el import `.dxt` desde el panel ya está probado operativo (cf. despliegue de `expedientes-xl`, cierres 19º-22º). Si se retoma la instalación de `google-despacho` en App/Cowork —y la baja de `gmail-ro`, superada por `gmail-multiaccount`—, va por esa vía normal (panel `.dxt`), no por el script. Histórico: bitácora 2026-07-15.
- **F3 (`import_drive_folder` intake EV→TL de una orden) APARCADA 2026-07-10** — sobreingeniería por ahora (decisión de Nikolai). Brainstorming + mapeo del ecosistema HECHOS y spec escrito (§14 del design doc, `dfad021`), pero **NO se construye**. Motivo: la vía existente **ZIP de Drive → `intake-expediente` (EXPEDIENTES-XL `extract_archive`)** cubre la necesidad hoy sin un orquestador cross-cuenta. **Corrección registrada para si se reabre:** los expedientes de origen se buscan en las **unidades compartidas de ENGEL** (cuenta EV), no en el Drive del despacho (el W-code resuelve la carpeta DESTINO en TL). **Disparadores de reapertura:** (a) volumen recurrente que haga tedioso el ZIP manual, (b) necesidad real de hacer el intake desde Cowork **sin PC**, (c) un caso que pinche la vía ZIP. Lote (`copy_tree`/`move_batch`/`delete_batch`) sigue diferido. Detalle en spec §14 (poner banner APARCADO).
- **Fleco de F2 (no de F3):** `download_file_content` (`drive_ops.py:209`) devuelve el mime de ORIGEN tras exportar un Doc nativo (no el de export) y no ajusta la extensión del destino — bug latente menor (sin consumidor tras aparcar F3). En backlog.
- Siguiente en cola: **F4** (Calendar) cuando haya disparador. Retomar por `writing-plans`.

## [SIGUIENTE-MCP-SUDESPACHO] MCP `sudespacho` (CRM del despacho) — F1 lectura: spec HECHO, plan pendiente

*Disparador: `docs/superpowers/handoffs/handoff-2026-07-13-mcp-sudespacho.md` (brainstorming Cowork) + decisión Nikolai de dar producto rápido y escalable a los compañeros. Primer producto que escala a Ana/Sergio/Paola porque la API REST del CRM ya es nube. Aplica el principio transversal de dos capas (motor determinista + interfaz distribuible).*

- Spec APROBADO en brainstorming: `docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md`.
- **Decisiones cerradas:** **standalone** (sin `import core`, anti-drift por paridad) · entrega **`.dxt` a Cowork por el puente** · orden **F1 lectura → F2 escritura → F3+** · **Modelo B de credenciales: cuenta personal de cada usuario (Bearer JWT + refresh), NO la `x-api-key`** (hallazgo 2026-07-13: la key es GLOBAL/admin, no ligada a usuario, permisos no modificables, ~100% acceso → inútil para rol/atribución; el JWT personal SÍ respeta la matriz de rol —oculta contabilidad server-side— Y atribuye eventos al usuario; **Modelo A retirado, Modelo C descartado**) · **lista blanca deny-by-default** con TODO el árbol financiero/contable VETADO (2ª barrera) · **BORRADO NUNCA** (triple garantía: sin tool, cliente sin `DELETE`, rol con `Delete` OFF) · tools **genéricas** (`element` como parámetro) · **descubrimiento** por `describe_element` + playbook + catálogo (lectura casi automática, escritura mantiene HAR) · descarga vía `downloadUri` a DL-root (bytes nunca por el modelo; `presigned_download_url` NO es bloqueo, ya resuelto) · ubicación `plugins/sudespacho_mcp/`.
- **Descubrimientos reusados de El Contable** (`../ElContable/docs/`): matriz de permisos por rol (valida Modelo A) · slugs financieros confirmados (conceptos_*, facturas, facturas_proforma) · workaround del bug 500 de detalle (forma `?properties=a,b,c` coma vs `properties[]` array) · host de calendario `api-calendar-commons-pro.sudespacho.biz` · gramática `filterGroup` + enums + colisión `E1`.
- [x] **Gate de auth — mecanismo VERIFICADO EN VIVO (2026-07-13, usuario admin):** REST `element_registries/clientes_propios` → 200; JWT en localStorage con claims `username`+`roles` (atribución + rol); vida 60 min + `refresh_token`; **sin PHPSESSID** (REST = Bearer JWT puro). Modelo B viable.
- [x] **Sesión de verificación en vivo (2026-07-13) — 3 gates cerrados:** (1) **Bug 500** resuelto — forma **coma** `?properties=a,b,c`→200, array→500 (INTEGRACION §8.3 corregido, workaround propagado); (2) **Login** resuelto — no hay endpoint usuario/contraseña (todos 404) → alta por **`refresh_token` pegado**, el plugin no maneja contraseña; (3) **Slugs** resueltos — `abogados_propios`/`abogados_contrarios` (no `abogados`), `extrajudiciales` (no `expedientes_extrajudiciales`), `juzgados` válido; `properties[]` obligatorio también en el listado. Spec+plan actualizados.
- [ ] **PENDIENTES del gate:** (a) prueba de **atribución en escritura** (`created_by`, F2); (b) prueba de **rol que oculta la contabilidad** con un usuario de rol abogado (Nikolai es admin, lo ve todo).
- [ ] **🚩 RIESGO tope de licencia (4 concurrentes) — Nikolai lo CONSULTA con sudespacho (en curso):** confirmar si una sesión JWT del MCP consume licencia (Nikolai+3 compañeros=4, sin margen; entrar expulsó al usuario de soporte). Posible bloqueante del escalado simultáneo (NO de código para F1). Mitigaciones a estudiar: reusar token de sesión web, ampliar licencias, o limitar concurrencia. Puerta de DESPLIEGUE, no de build.
- [ ] **F1 (lectura)** — desglosar por `writing-plans` y construir. Entregables: cliente REST puro + lista blanca/catálogo + `describe_element` + tools de consulta genérica + expedientes/documentos + descarga a DL-root + `.dxt`. Playbook de descubrimiento en `docs/INTEGRACION_SUDESPACHO.md`. **Consulta previa OBLIGATORIA: `docs/CRM_SUDESPACHO_ATLAS.md`** — SSOT de la superficie (548 ops de Fase A + campos/relaciones/enums de 87/89 elementos, PR #104), ya pagada. La lista blanca, el catálogo y `describe_element` se derivan de ahí; redescubrir endpoints a mano está prohibido por `CLAUDE.md:212`.
- [ ] **F2 (escritura)** y **F3+** (agenda CRM en escritura, legacy, lote): spec/plan aparte, por disparador.
- [x] **Revisión adversarial del spec (2026-07-13, 4 lentes):** núcleo resiste; correcciones aplicadas a spec+plan (confidencialidad por CAMPO no solo slug + filtro de propiedades; `describe_element` solo-esquema; documentos vía `download_document` a DL-root + `gdocu` en lista blanca + validar elemento-origen; retirada la afirmación "coma esquiva 500" → fallback legacy; `.dxt` autocontenido sin ruta/repo personal; token store atómico+lock+carga tolerante; refresco reactivo a 401 + `_extract` tolerante; descarga con timeout/redirects; no-pérdida-de-datos en F2). **Gates EN VIVO (prerrequisitos de despliegue):** rol abogado oculta contabilidad a nivel slug+campo, endpoint de login, coma-vs-500, escritura con JWT (F2), licencia, vida del refresh_token, verificar slugs. Detalle en spec §13.

---

## 🧭 PRINCIPIO TRANSVERSAL — dos capas: motor determinista + interfaz distribuible (plugin)
*Fijado 2026-07-13 (brainstorming Claude Code, Nikolai). Decisión de rumbo sobre cómo escalar el producto a los compañeros (Ana, Sergio, Paola) sin dejar de trabajar el código de FeesDefender. Disparador: el diseño del MCP de CRM sudespacho (`docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md`) obligó a decidir plugin standalone vs wrap-core.*

**El producto es UNA cosa en DOS capas, no dos tracks que compiten:**
- **Motor determinista (`core/`)** = la capa de confianza y auditoría. Todo lo forense, exacto e irreversible: custodia SHA-256, anonimización (`core/anon` — cero pérdida de lógica), altas en CRM (autoincremento sin duplicar), fidelidad byte de correos. Se mantiene y se sigue trabajando; es el cimiento, no legado a jubilar.
- **Plugins/skills = la interfaz distribuible** que tocan los compañeros. Se reparte por la superficie de Claude (Cowork/Desktop/móvil): se instala y funciona, **sin repo, sin `.venv`, sin `G:`**. El Streamlit local NO escala a terceros porque es un entorno de desarrollador.

**Regla de oro (evita el error caro):** lo irreversible/forense vive en el motor; el plugin lo **dispara**, no lo **reimplementa** "rápido". Si un plugin debe replicar una operación del motor, se blinda con **tests de paridad** contra `core` (patrón §14.6 de `2026-07-08-google-despacho-mcp-design.md`). Corolario de empaquetado: para que un plugin escale a un compañero debe ser **standalone** (`.dxt` autocontenido que él instala con sus credenciales); un plugin acoplado al repo (wrap-core) solo corre en la máquina que tiene el repo.

**Qué escala a los compañeros y qué no (a fecha de hoy):**
- **Escala YA, sin construir nada:** skills puro-LLM + conectores de lectura (Drive/Gmail) — `triaje-viabilidad`, `escritos-judiciales`, `verificacion-anclada-fuente`.
- **Escala con build acotado:** MCP de CRM sudespacho **en lectura** (standalone; la API REST `x-api-key` ya es nube) → candidato a "primer producto rápido" para los compañeros, bajo riesgo.
- **NO escala todavía (se queda en el track local determinista):** OCR, anonimización, atomización de correo y todo lo que hoy exige el pipeline local. Plugin-izarlo para terceros exigiría **hostear el motor** — proyecto aparte, sin disparador hoy.

---

## 🧭 PRINCIPIO TRANSVERSAL — copia al Drive por lote (hidratar→procesar→devolver)
*Fijado 2026-07-07 sobre benchmark medido (Cowork). Fuente: `HANDOFF_benchmark_vias_drive_2026-07-07.md` (integrado y borrable). Números y tabla en `docs/DEAD_ENDS.md` §"Benchmark de vías de copia al Drive". Confirma —no reabre— las decisiones del diseño V2 (merge + biblioteca, doc en Cowork/Drive, no trackeado aquí).*

**Hallazgo rector:** el cuello de botella de trabajar contra el Drive es el **número de operaciones MCP** (~10-15 s fijos cada una), **no los bytes** (202 MB tarda lo mismo que 24 KB). Los ~53 min de la sala fueron 120+ round-trips per-fichero, no volumen.

Tres reglas que gobiernan TODO pipeline de procesado (aplican a `[SIGUIENTE-MOTOR-DOCUMENTAL]`, `[SIGUIENTE-SKILL-EXPEDIENTE-A-MD]`, `[SIGUIENTE-EMAIL-ATOMIZE]`, `[SIGUIENTE-CRONOLOGIA-UNIFICADA]`, `[SIGUIENTE-SALA-UNICA-PLANA]`):

- **(b) REQUISITO de diseño — hidratar→procesar→devolver.** Todo procesado masivo (OCR/MD/anonimizador, atomizadores) se diseña: **copia masiva previa a disco local en un viaje** (`rclone copy` / `copy_dir`, no bucle) → pipeline **contra disco local** → **subida de resultados en un solo lote**. **Nunca** lanzar OCR/lectura contra `G:` en streaming (cada `open()` descarga bajo demanda, con relecturas), ni bucles fichero-a-fichero vía MCP. `create_file` con bytes por el modelo queda descartado para >1 MB.
- **(a) CONTRAINDICACIÓN — el checkout de biblioteca NO acelera sesiones de Cowork.** El overhead por llamada de Cowork se paga igual esté el caso donde esté; el checkout de la biblioteca (diseño V2) aporta a **humanos, pipeline local y trabajo offline**, no a la latencia de Cowork. No justificar el checkout por "acelerar Cowork". *(Offline refuerza el V2: la vuelta de un periodo sin conexión es el caso central del merge 3-vías con baseline; el pin "disponible sin conexión" de Drive for Desktop sincroniza sin lock ni baseline → resuelve por última-escritura o duplicación silenciosa, inaceptable con trazabilidad forense.)*
- **(c) PARCHE PROVISIONAL (hasta que exista el piloto de biblioteca).** Para procesar un caso HOY: `rclone copy` manual del caso a local antes del pipeline y de vuelta al terminar (válido solo si **un único usuario** toca el caso), o **pin offline** de la carpeta antes de procesar.

---

## [SIGUIENTE-MOTOR-DOCUMENTAL] Motor documental unificado (split/OCR/MD) + empaquetado como conector (`MEJORAS #48`)
*Decisión Nikolai 2026-07-03. Disparador concreto: Nikolai quiere empaquetar el motor OCR→split→MD como un conector/plugin reutilizable por los compañeros. Un motor fragmentado y que falla en silencio no se puede empaquetar bien → sanear + fachada + registro de cobertura es la preparación del plugin.*

> **⏸️ APARCADO (2026-07-04).** Nikolai pausa el motor/refactor completo. **Foco actual: skills con código**
> (vía lean — skill que orquesta y llama a motores existentes, p. ej. `ocr-a-md`, sobre el scaffold actual).
> El diseño queda de referencia para retomarlo. Estudio de mercado 2026 + opciones de motor (OSS local
> Docling(MIT)>MinerU(AGPL) / **Mistral OCR cloud+ZDR+DPA como opción de fase de construcción** / Azure
> contenedor para manuscrito, post-anonimización) en §F del doc.

> **Plano completo y memoria de diagnóstico: [`docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`](docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md).**
> Consolida `MEJORAS #21/#24/#39/#42/#43/#41`. **Solo diseño escrito; sin código todavía.**

**Diagnóstico (resumen).** Tres motores de OCR desacoplados (Docling interno · RapidOCR por página vía
script manual · OCRmyPDF en anon), hueco de escaneados >30pp que salen vacíos, banda muerta de umbrales
(100 vs 50 chars), imágenes con tres tratos incompatibles (las `.heic` se caen en el inventario), y
`separar.py` desenganchado del pipeline. Detalle con `file:line` en el doc.

**Decisiones de organización (fijadas 2026-07-03, informadas por Vassal Litigator — ver §G/§H/§I del doc):**
`01_Procesado/01_Sala de lectura/` (humano) + `01_Procesado/02_Sala de máquina/` (máquina, productos numerados `01_OCR/02_Documentos/03_MD`) · id **dual** (`sha8` interno + `doc-NNN` legible) · **registro ÚNICO de caso** estilo Vassal `index.yaml` (vistas humanas derivadas) · **reocr condicional** por `ocr_quality`.

**Decisiones estratégicas (fijadas 2026-07-04 — §L del doc):** (1) **plugin primero, Streamlit parqueado** — distribución vía plugin; (2) **Ollama/LLM local descartado** → motor OCR **FIJADO: OCRmyPDF + `ocr_per_page` torch como reocr** (visión local/cloud fuera); (3) **regla PII relajada temporalmente** — anonimización = **último eslabón**, con **gate de reinstauración del muro `06`** (condiciones: pipeline→MD ✔, sala de máquina ✔, sala de lectura ✔, intake ✔). Resultados tangibles primero.

**Principios rectores (M1–M9 — §M del doc):** M1 golden fixture antes de tocar código · M2 registro primero · M3 walking skeleton · M4 fachada `procesar_expediente()` desde el día uno · M5 `00_Input` intocable (guard/test) · M6 medir el "antes" (documentos ciegos) · M7 Preview→Apply obligatorio · M8 preflight por capacidades (centralizado en `health_check`) · M9 doctor/manifiesto de dependencias.

**Orden de ejecución (fases, resecuenciado §L+§M).**
- [ ] **F(-1) — fundaciones sin riesgo:** golden fixture de W-02VND1 (M1) + auditoría "antes" de documentos ciegos (M6).
- [ ] **F1 — registro ÚNICO de caso** (elevar+extender `indice_documental.yaml` a ámbito caso, esquema estilo Vassal `index.yaml`) + **id dual** (`sha8`+`doc-NNN`) + **fachada fina** `procesar_expediente()` (M4) + vistas humanas derivadas. Piedra angular. ⚠️ **Antes de empezar, leer el §0.1 de `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` y el aviso de §G.3 del doc**: la pieza A de `MEJORAS #90` (fila #1) ya construyó un `doc_id` de ámbito **bundle** (`d01`, con ledger y tombstones) que F1 tiene que envolver o migrar — no duplicar.
- [ ] **F0 — layout + botón reorganizar:** renombrar `Sala lectura` → `01_Sala de lectura`, crear `02_Sala de máquina/`; **botón `reorganizar_caso`** (`plan`/`apply`, `--todos`, journal reversible estilo `migrate_05crm_buckets`); sello **`layout_version`**; **cablear `--force`**; alinear umbrales, docstring/etiqueta, extensiones + HEIC. Ver §J.
- [ ] **F3 — motor OCR + reocr + espejos:** **OCRmyPDF** → PDF buscable (fijado). **Extractor→MD = decisión aplazada tras la junta; bake-off MinerU vs Docling** sobre fixture + casos duros (escritura/catalán/ruso/tabla/manuscrito), gate hardware(CPU/OOM)/catalán/licencia — MinerU favorito (local, CPU, determinista, tablas+manuscrito, sin PII; si cumple, elimina Claude visión). Persistir en `02_Sala de máquina/{01_OCR,02_Documentos,03_MD}` con espejo de `00_Input/`; dejar de borrar el PDF del OCR en anon. **Validado antes con walking skeleton (M3).** Ver §F/§G.
- [ ] **F4 — conector MCP + empaquetado + botón reformar plugin** (aislamiento por subproceso, versión/modelos pinneados, sin fuga de datos, preservar `core/anon`) + **preflight (M8)** + **doctor/manifiesto (M9)**. **Botón `rebuild_plugin`** mecánico + señalización semántica (handoff `motor_mejora`) + hook de drift (`session-start-hook`). Ver §K.
- [ ] **F-final — anonimización + reinstauración del muro `06`** (gate PII §L) — último eslabón; + faltas restantes (D.2–D.9) según disparador.
- **Transversales:** Preview→Apply (M7) y guard `00_Input` (M5) en todas las fases.

---

## [SIGUIENTE-EMAIL-ATOMIZE] Motor de atomización de correo (`core/email_atomize/`)
*Diseño aprobado por Nikolai 2026-06-24/25. Spec: `docs/superpowers/specs/2026-06-24-email-atomize-design.md`. Plan Fase 1: `docs/superpowers/plans/2026-06-24-email-atomize-fase1.md`. Implementación: Claude Code.*

Descompone `00_Input/03_Email/*.eml` a nivel de **mensaje atómico** → `01_Procesado/Emails/`
(`.md` por mensaje + frontmatter, adjuntos dedup sha256 + ficha, `corpus.jsonl`, `_registro.json`
con IDs congelados, `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md`). Fin: recuperar la autoría
enterrada de PersonaUno (levantar el velo de [inmueble] S.L.). Reutiliza `core.email_export`.

- [x] **Fase 1 — IDs + Capa A (MIME) + salidas.** Paquete `core/email_atomize/` (ids/headers/
  extract/dedup/bodies/attachments/render/corpus/pipeline) + CLI `scripts/atomize_emails.py`.
  +24 tests. **Corrida real W-02VND1: 277 mensajes, 162 adjuntos únicos (72 decorativos), 0
  errores, 0 mojibake, idempotente.** Commits `f468a55`→`04901ba` (spec `e9681c1`, plan `88439a2`).
- [x] **Fase 2 — Capa B (reenvíos/citas INLINE).** Diseño sintetizado por workflow adversarial +
  **revisión adversarial de código** (14 hallazgos confirmados, 8 HIGH, TODOS corregidos). `inline.py`
  + `_segmenter.py` (autoridad única autor/cita); segmentación HTML+plano, atribución SOLO desde
  cabecera contigua parseable (ES+CA+EN), confianza alta-reconstruida/media/baja con guardas
  anti-misatribución (ambigüedad, fecha-coherente, candidata→media, conservación de tokens),
  fingerprint día-granular, upgrade de fidelidad sin tocar Capa A, poda de huérfanos, cola `_revision/`.
  +53 tests. **Corrida real W-02VND1: 277 Capa A BYTE-IDÉNTICOS, +89 Capa B alta (0 misatribuciones
  auditadas), 84 a revisión, 6 upgrades, idempotente; PersonaUno 12 directos + 13 inline PROMOVIDOS
  (autoría enterrada recuperada).** Un bug de fecha enmascaraba el payoff (antes 14/0 → 89/13).
  [spec](docs/superpowers/specs/2026-06-25-email-atomize-layerb-design.md) ·
  [plan](docs/superpowers/plans/2026-06-25-email-atomize-fase2.md).
- [x] **Fase 3 — capa de caso.** _CÓDIGO COMPLETO en `origin/main` (`14d8743`→`5b566ea`), vía subagent-driven + revisión adversarial=SHIP; suite 1255 verde. PENDIENTES (no parte de F3 / siguiente sesión): **Task 7** verificación EN VIVO sobre W-02VND1 en `G:` (nada escrito aún; necesita keywords del `nexo_causal` + autorización) y, en spec/plan SEPARADO, el **recall MSG-00018** + OCR de adjuntos._ `identidades.yaml` (mover `IDENTIDADES_VIGILADAS`; set de PersonaUno
  `per01a@example.invalid`/`per01c@example.invalid` confirmados, `per01b@example.invalid` candidato→tope media,
  `ignacio@despacho-ab.example` parte DISTINTA), mejor parser de fechas ES/CA + niveles
  profundos (subir recall PersonaUno), vistas temáticas (`dossier_persona_vigilada`, `vista_nexo_causal`),
  `_entregas/` selladas. OCR de adjuntos = posterior.

---

## [SIGUIENTE-CRONOLOGIA-UNIFICADA] Cronología Unificada de Prueba (capa por encima de los atomizadores)

> 🗄️ **APARCADO (triaje 2026-07-19).** DISEÑO COMPLETO (8 fases) pero **sin una línea de código**
> (`core/cronologia*` no existe). Se conserva como **NORTE de arquitectura**, no como cola activa. La
> materialización cercana es la sala de lectura a nivel-fichero (hermana, NO prerrequisito; ver
> `docs/superpowers/2026-07-19-sala-lectura-procesado-exploracion.md`). **Desarchivar** solo con un caso
> real que exija una cronología unificada de prueba.
*Diseño aportado por Nikolai 2026-06-25 (hilo Cowork). Spec **v7 — DISEÑO COMPLETO (8 fases, 0–7)**: `docs/superpowers/specs/2026-06-25-cronologia-unificada-design.md`. Banco de pruebas de diseño: W-02VND1 ([inmueble]). **Naturaleza: documento de DISEÑO, NO construcción.** Disciplina rectora: skill `verificacion-anclada-fuente`. Implementación: Claude Code en `core/` — **siguiente paso = BUILD, no más diseño.***

**Objetivo.** Fusionar todas las fuentes de prueba de un expediente (correo, WhatsApp,
CRM, entrevistas, documental, registros) en **UNA sola línea de tiempo**, separando lo
que **consta** en la prueba (capa canónica, anclada con pinpoint, estatus A/B) de lo que
se **infiere** de ella (capa derivada: hechos, relato, nexo causal, presunciones 385/386).
Vive **por encima** de los atomizadores por fuente (el motor `core/email_atomize/`,
**congelado**, es el primer adaptador) y **por encima** de `organizar-sala-lectura`
(nivel fichero); no los duplica ni los modifica.

**Decisiones de diseño cerradas (D1–D6 en el spec):**
- **D1 — átomo:** acto datado anclado a fuente (Modelo B, PROV-O Activity/Entity/Agent);
  nunca un hecho del mundo inferido. Confianza en 3 ejes (anclaje A–E · credibilidad ·
  fiabilidad de fuente).
- **D2 — almacén:** híbrido delgado (verbatim **en la fuente**, relación temporal en el
  almacén canónico) + pinpoint doble + `eventos.jsonl` regenerable + `_registro_cronologia.json`
  no-derivable. Salida prevista: `01_Procesado/Cronologia/`.
- **D3 — tres fichas:** Acto · Enlace (primitivo único, absorbe la correlación y las
  contradicciones) · Hecho derivado (alimenta `HECHOS_X.md` con semáforo 🟢🟡🔴 calculado del grafo).
- **D4 — IDs:** dos regímenes — congelados por contenido (`EVT-`/`ATT-`) y asignados/persistidos
  (`ENL-`/`HD-`/`ACT-`/`HIP-`); idempotentes, opacos, 5 dígitos.
- **D5 — actor:** formaliza `identidades.yaml` (identidad única + roles que cuelgan;
  calificaciones del velo = hechos derivados, no flags).
- **D6 — tipología:** categorías de alto nivel CERRADAS; hojas SEMILLA extensibles con gobernanza.

**Decisiones de Fase 3 cerradas (correlación entre fuentes — F3.D1–D5; §7 del spec).** Regla rectora: **intra-fuente DEDUP, inter-fuente CORRELACIÓN (nunca fusión).**
- **F3.D1 — desenlaces:** dos planos ortogonales (actos: Colapso/Correlación/Reconstrucción/Sin relación · artefactos §2.5); **sin nodo `EventoMaterial`** (sería puerta trasera de inferencia); corroboración de CONTENIDO vs CIRCULACIÓN se computan distinto.
- **F3.D2 — señales (S0–S5):** confianza de emparejamiento explicable ≠ fuerza probatoria; peso por rareza/diagnosticidad; bloqueo duro (ancla compartida) + blando (solo candidatea a revisión); flag `riesgo_tergiversacion`. **★ no-fuga:** el semáforo solo usa enlaces `confirmado`.
- **F3.D3 — enrutamiento:** AUTOENLACE (solo S0a-formal + hash idéntico) / COLA (recall-bias, tiers) / NO-PROPUESTO; la contradicción NUNCA se autoenlaza pero salta la compuerta; decisión humana **sticky y persistida** (en `_registro_cronologia.json`).
- **F3.D4 — fórmula del 🟢🟡🔴:** regla **estructural categórica** (no suma ponderada); independencia en 3 grados; diagnosticidad condicional (ACH); cadenas `min` por ruta + convergencia; topes por rival seria/credibilidad/386; salida **propuesta** que el letrado cura.
- **F3.D5 — contradicción:** el sistema **no resuelve**, representa el conflicto (versiones rivales bajo punto controvertido); tres dianas según `matiz_contradiccion` (contenido/credibilidad/autenticidad); degradación una sola vez en el nodo; resolución = evento nuevo.

**Decisiones de Fases 4–7 cerradas (v7 — DISEÑO COMPLETO; §8–§11 del spec).**
- **F4 — tiempo heterogéneo (§8):** la línea ancla el **tiempo del HECHO** (3 tiempos deslindados: no declarativo / narrativo→reconstruido subsidiario / performativo; el tiempo de REGISTRO = procedencia, nunca posición). Cronología = **ORDEN PARCIAL**: proyección a intervalo `[suelo, techo]` EDTF, 5 relaciones derivadas (antes/después/contiene/contenido_en/indeterminado), propagación TCN segura sobre constraints anclados (nunca muta `cuando.fecha`); consumo en prescripción (rango argumental, nunca fecha única), 386 (`requiere_precedencia` bloquea/degrada) y S4. Campos nuevos: solo `requiere_precedencia` + diagnóstico `inconsistencia_temporal_de_fuente`.
- **F5 — arquitectura de ingesta (§9):** **3 capas con frontera tajante** — ATOMIZADOR (por fuente, dueño de bytes; el motor de correo congelado ES el de "correo") · ADAPTADOR/PROYECTOR (delgado, mapea átomo→ficha de acto, emite tokens de actor sin elegir ganador, defaults deterministas nunca inferencia) · NÚCLEO AGNÓSTICO (asigna EVT-id, resuelve identidad, dedup/correla/tiempo/enlaces/vistas). El adaptador **nunca** asigna ids ni correlaciona. Anclaje **al crudo de `00_Input`+hash** (sala de lectura = pista débil); staging multi-fuente; llegadas tardías idempotentes; `90_Notas personales` = prohibición absoluta (ni listar).
- **F6 — vistas y custodia (§10):** entregable humano = `CRONOLOGIA_ACTOS` regenerable **"índice de lectura — NO prueba"** (una entrada/acto, extracto con ventana de contexto, cita = fuente+pinpoint, etiquetas separadas corroboración-de-contenido vs circulación, dossiers temáticos con bloque anti-sesgo); sellado de entrega a `_entregas/<fecha>/` en 3 bloques (prueba aportable con SHA-256 · apoyos demostrativos · manifiesto de custodia transversal), inmutable e incremental; work-product ≠ prueba, nunca mezclados.
- **F7 — alcance del piloto (§11):** primer build = **correo + WhatsApp y nada más** (atomizador+adaptador de WhatsApp para `02_Whatsapp`); objetivo = validar el núcleo agnóstico end-to-end; éxito = 3 hechos-test (correlación-no-fusión por dos canales · identidad atada por teléfono · punto controvertido de contenido y de fecha sin resolver). Ejecución: Claude Code local.

**Material build-ready (handoffs de stress-test) — COMPLETO en el repo 2026-06-25:** `docs/superpowers/specs/cronologia-handoffs/` contiene los **7** handoffs que cita el spec (F3.D4, F3.D5, F4.D1, F4.D2, F5.D1, F5.D2, F6.D1) verbatim + README (son los PROMPTS de revisión adversarial que validaron el diseño; las decisiones sintetizadas viven en el spec §7–§11). **F3.D4 y F3.D5** traen además el **pseudocódigo operativo** (`calcular_estatus_soporte` del 🟢🟡🔴 y `procesar_contradiccion`) — directamente build-ready.

**Estado (DISEÑO).**
- [x] Fase 0 — inventario de fuentes.
- [x] Fase 1 — esquema del evento (D1, D2, D3, D4, D6).
- [x] Fase 2 — identidades (D5).
- [x] **Fase 3 — correlación entre fuentes (F3.D1–D5).** Algoritmo y reglas cerrados (§7 del spec); ver bloque de decisiones arriba.
- [x] **Fase 4 — tiempo heterogéneo (F4.D1–D2).** Tres tiempos del evento + orden parcial / intervalos EDTF (§8 del spec).
- [x] **Fase 5 — arquitectura de ingesta (F5.D1–D2).** Atomizador / adaptador / núcleo agnóstico; anclaje al crudo (§9 del spec).
- [x] **Fase 6 — vistas, entregable humano + custodia (F6.D1–D2).** `CRONOLOGIA_ACTOS` + sellado de entrega (§10 del spec).
- [x] **Fase 7 — alcance del piloto (F7.D1).** Correo + WhatsApp; 3 hechos-test (§11 del spec).

**Siguiente paso = BUILD (diseño COMPLETO).** Cerradas las 8 fases de diseño (0–7), el
siguiente paso ya no es diseñar sino **construir** en `core/` de FeesDefender (Claude Code,
local), incremental (correo + WhatsApp primero), con el motor de correo congelado como
primer adaptador. **Dependencia operativa:** conviene tener el motor de correo terminado
(hoy `[SIGUIENTE-EMAIL-ATOMIZE]` está en Fase 3) antes de arrancar el piloto. La cronología
**consume** sus salidas (`mensajes/*.md`, `corpus.jsonl`, `_registro.json`) y **no lo toca**
(spec congelado).

**Prompt de arranque del BUILD** (registrado 2026-06-25): `docs/superpowers/plans/2026-06-25-cronologia-build-arranque.md`.
**Orden de build** (incremental, con tests en cada paso): (1) motor de correo = primer
atomizador en `core/`, con pasada de medición previa sobre datos reales; (2) esqueleto del
núcleo agnóstico (ficha del acto §3.1, `_registro_cronologia.json`, IDs `EVT-/ATT-/ENL-/HD-/ACT-/HIP-`,
resolución de identidad contra `identidades.yaml`, contrato de staging); (3) adaptador-lector
de correo (solo lectura sobre el motor congelado); (4) atomizador + adaptador de WhatsApp
(`00_Input/02_Whatsapp`, formato iOS); (5) piloto end-to-end correo + WhatsApp → `CRONOLOGIA_ACTOS`
+ dossier del velo, validando los 3 hechos-test (F7.D1). *El arranque cita el spec como
`PLAN_CRONOLOGIA_UNIFICADA.md`; en el repo es `docs/superpowers/specs/2026-06-25-cronologia-unificada-design.md`.*

---

## [SIGUIENTE-SALA-UNICA-PLANA] Sala de lectura única, plana y prompt-driven (todo `00_Input`)
*Decisión cerrada con Nikolai 2026-06-18 (este hilo). RGPD aprobado por el responsable del tratamiento. Spec + plan de implementación DIFERIDOS (Nikolai aportará más contexto desde otro hilo). Enlaces: `MEJORAS #34` (vehículo: skill-Cowork multiusuario), `#35` (bundle WhatsApp chat+media), `#36` (guarda de colisión), `#38` (fecha de contenido vs mtime), `#37`/`#39` (deprecación).*

> **[IMPLEMENTADO y MERGEADO 2026-06-18 — pero con PIVOTE PENDIENTE]** Spec
> `docs/superpowers/specs/2026-06-18-sala-lectura-unica-design.md` + plan
> `docs/superpowers/plans/2026-06-18-sala-lectura-unica.md`. Feature mergeada a `main`
> por FF (13 commits `a53ca42`→`51b6653`, sin push): skill `organizar-sala-lectura`
> v1.3 (plana, todo `00_Input`) + `triaje-viabilidad` v1.1 + canon/sync/gate + helper
> de catálogo + core de sala deprecado. Revisor final APPROVED; suite verde.
> **⚠️ La corrida real en Cowork (BaRS1) tardó ~53 min** — el conector de Drive es
> per-fichero (ver `DEAD_ENDS.md`). **DECISIÓN ABIERTA (manda sobre el resto):** pivotar
> a **motor local plano primario** sobre el montaje `G:` (Drive for Desktop) —filesystem,
> disparo por CLI/Streamlit/skill en Claude Code local—, dejando la skill de Cowork como
> **fallback puro-nube**. **Bloqueado por:** ¿el equipo (Paola incl.) trabaja con el
> montaje `G:`? Si sí → des-deprecar el motor y portar `poblar_sala_lectura` a la
> estructura plana. **Pendiente operativo:** re-import `.skill` v1.3/v1.1 en Cowork.
>
> **✅ Vía rápida lado Claude Code lista (2026-06-22):** MCP filesystem local
> **`expedientes`** sobre `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL`
> (`@modelcontextprotocol/server-filesystem`, global + `cmd /c`, modo Mirror = todo en
> disco). Lectura a velocidad de disco (~1,1 s un caso de 928 ficheros, vs ~53 min por
> el conector). **Permite ya** correr la skill `organizar-sala-lectura` **prompt-driven
> en Claude Code local** sobre el Drive sin el conector per-fichero — desbloquea el lado
> Code del pivote SIN portar todavía el motor Python. NO escribe nada que no se le pida,
> pero el server-filesystem **sí puede escribir/borrar** en `G:` (incluida `90_Notas
> personales` + riesgo de duplicados por el sync de Drive): se asume, no se limitó a
> solo-lectura (decisión de Nikolai 2026-06-22). Montaje
> documentado en `DEAD_ENDS.md` y memoria `reference-expedientes-filesystem-mcp`.
>
> **⚠️ CORRECCIÓN 2026-06-22 — Cowork TAMBIÉN puede usar el MCP local (se creía que no):**
> añadido el mismo server al `mcpServers` de `%APPDATA%\Claude\claude_desktop_config.json`,
> **Cowork cargó la integración `expedientes` y listó 273 ficheros de BaRS1 en segundos.**
> El supuesto "Cowork solo ve Google Drive" era FALSO: **Claude Desktop (app local) hace de
> puente** y lanza los stdio MCP locales en el PC. Los ~53 min fueron por usar el **conector
> remoto** de Drive, no por falta de acceso al disco. **Implicación para este pivote:** la
> sala puede correr rápido en Cowork **en el PC de Nikolai** apuntando la skill al MCP local
> `expedientes` en vez del conector — sin portar el motor Python ni montar servidor remoto.
> **Límite que persiste:** solo donde Claude Desktop corre en el PC con el montaje `G:`;
> Cowork móvil/navegador o las PC de Paola/Ana sin montaje+`mcpServers` seguirían necesitando
> un MCP **remoto** en servidor (ahí sí queda la fase aparte).

**Decisión.** Unificar las **dos** salas de lectura hoy convivientes en `01_Procesado/`
(la `Sala lectura Drive EV` de la skill Cowork —solo Drive EV, por categoría— y la
`Sala lectura` del motor —todo `00_Input`, por fuente—) en **UNA sola `Sala lectura`**,
poseída por la **skill (Cowork, prompt-driven) aplicada a TODO `00_Input`**. El motor
deja de poblar la sala (es un artefacto-hoja: **nada del core la lee**; el pipeline
confidencial extractor→`MD/`→anon→`06`→frontier es independiente y se mantiene).
Resuelve `MEJORAS #34`: Paola y cualquiera la ejecutan desde Cowork sobre el Drive,
sin Python local ni dependencia del PC de Nikolai.

**Estructura canónica (fijada).** Plana, sin slug de categoría, cronológica:
- Fichero: `<AAAA-MM-DD>_<descripcion_guiones_bajos>.ext` (fecha ISO + descripción
  legible, sin PII, sin prefijo de categoría).
- **Documento compuesto** (con anexos) = **subcarpeta** con el mismo nombre del
  principal (`<AAAA-MM-DD>_<descripcion>/`, fecha ISO en la carpeta → se intercala
  cronológicamente), conteniendo el principal + sus anexos (`<principal>_anexo_<N>_…`).
  Documentos sueltos → ficheros planos en la raíz.
- La **taxonomía E&V deja de vivir en las carpetas** y pasa a `INDICE.md` (vista por
  categoría) + `CRONOLOGIA.md` (ascendente) + `_MANIFIESTO.md` (sha256 · original ·
  canónico · categoría · fecha). La **fuente** se conserva en el manifiesto/catálogo
  e índices (no se pierde al quitar las carpetas por fuente).

**Decisiones cerradas (Nikolai, este hilo):**
- **RGPD:** APROBADO que la skill lea **todo `00_Input` en claro** (incl. WhatsApp,
  email, entrevistas), vía Cowork/Claude, ejecutado por Paola y otros. Extiende la
  excepción de `MEJORAS #34` (más fuentes y usuarios); autorizado por el responsable.
- **Catálogo:** se **conserva** `indice_documental.yaml` como SSOT, escrito por un
  helper de la skill (evita la doble verdad con `_MANIFIESTO.md`; deja la puerta a El
  Auditor y a la persistencia de bundles `parent_id`).
- **Bundles:** estructurales en la skill (WhatsApp chat+`media/` `#35`; email
  cuerpo+adjuntos por MIME); los **CRM** quedan "mejor esfuerzo" (Cowork no ve el
  `modified_at` del CRM que usa `conjunto_detector`).
- **Modelo:** la skill se ejecuta con **Sonnet/Haiku, NO Opus** (clasificación atómica;
  hay visto bueno humano y lo ambiguo→`08. PENDIENTE`). Nota de uso en la skill +
  prompt ligero. El grueso de la velocidad lo da el skip incremental (abajo).
- **2ª pasada idempotente (sin duplicar trabajo):** skip por **`md5Checksum`** en
  `_MANIFIESTO.md` (hash de contenido, no nombre). Coste ∝ documentos **nuevos**; si
  no hay nada nuevo → casi instantánea (listar + comparar hashes + re-render índices).
  Respeta ajustes manuales (no pisa lo ya colocado). Incluir el fix de `#38` (la fecha
  de contenido de actos fechados —escrituras, poderes, contratos, burofax— prevalece
  sobre `mtime`, que queda como último recurso marcado).
- **Deprecación:** el camino de sala en el core —`clasificar_caso`/`aplicar_clasificacion`/
  `render_indices`/`poblar_sala_lectura` y **`clasificar_residuo_llm` (`#37`)**— queda
  **superado por la skill** (marcar deprecado, no borrar de golpe). Se conservan los
  fixes de esta sesión (`build_catalog` `45dd5ad`, OCR-OOM `2eeec1a`) porque sirven al
  pipeline confidencial. Reevaluar `#39` (OCR local) ya que la skill esquiva el OCR
  local para la sala (usa la extracción del conector de Drive).

**Lectores de la sala:** `triaje-viabilidad` (la lee; corregir su referencia interna
`02_Sala lectura/` → sala única). `viabilidad-prerelleno` **no se toca** (lee `00_Input`
directo). 

**Reemplaza** el enfoque core de `[SIGUIENTE-SALA-LECTURA-01]` y `[SIGUIENTE-RESIDUO-LLM]`
para la población de la sala (esos quedan como histórico del prototipo que validó el
enfoque y destapó los dos bugs corregidos).

- [ ] **Pendiente:** spec de diseño (`docs/superpowers/specs/`) + plan de implementación
  de la skill. **En espera del contexto adicional de Nikolai (otro hilo).** No empezar hasta entonces.

---

## [SIGUIENTE-RESIDUO-LLM] Clasificador LLM del residuo de intake (`MEJORAS #37`)

> ✅ **CERRADO (triaje 2026-07-19)** → ledger `## ✅ Cerrados`. Implementación + tests en `742e35a`. Bloque
> conservado como histórico.
*Promovido 2026-06-18 por petición de Nikolai (Cowork). `MEJORAS #37`. Implementación: Claude Code.*

**Objetivo.** Cerrar el único paso humano que queda en la sala de lectura: rellenar
la worklist del residuo `01_Procesado/_revisar/_clasificar.md`. Paso **opcional**
`clasificar_residuo_llm(case_id)` que, SOLO sobre las entradas en residuo (las que
`clasificar_caso` no resolvió por nombre/imagen), lee el `.md` del texto extraído de
cada documento y autorrellena las columnas de la worklist (tipo documental, fecha,
parte, descripción). El letrado valida antes de `aplicar_clasificacion`, que sigue
siendo el **único** camino al catálogo canónico `indice_documental.yaml`.

**Restricciones (heredadas de la arquitectura).** La lógica vive en el core; el LLM
ocupa exactamente el slot humano de la worklist (no inventa estructura). Clasifica
solo lo que ve (regla de la casa: no inventar); lo de baja confianza se deja sin
rellenar (marcado para revisión), no se adivina. No toca la clasificación
determinista ni el esquema de la worklist. Idempotente; no pisa lo ya clasificado
por humano. Reutiliza `core/llm_cloud.py`.

**RGPD (cruza con #34/#27).** Extiende la excepción de lectura en claro por LLM. La
posición concreta (proveedor + qué texto lee + exposición en Streamlit) la fija
Nikolai al abrir el hilo de implementación (decisión abierta, ver hilo de Claude
Code).

**Decisión de Nikolai (2026-06-18):** resolver el residuo **desde Claude-en-sesión**
(ya pagado), **sin API externa de pago** (ni Scaleway ni Claude API) y **sin botón
Streamlit**. Encaja con la excepción RGPD §2 ya autorizada (Claude lee `MD/` en
claro); no abre terreno RGPD nuevo. El conector de pago (`make_llm_cloud_chat_fn`
sobre `core/llm_cloud.py`) queda OPT-IN para el futuro DPA.

- [x] Implementación (`preparar_residuo` + `rellenar_worklist` +
  `clasificar_residuo_llm` con `chat_fn` inyectable obligatorio + adaptador
  `make_llm_cloud_chat_fn` opt-in) + disparo headless (`preparar-residuo` /
  `clasificar-residuo [--connector]` en `scripts/sala_lectura.py`). `742e35a`.
  (No se cabló en `run_pipeline.py` ni Streamlit: forzaría el camino de API,
  contrario a la decisión.)
- [x] Tests (+9, LLM mockeado): residuo rellenado, baja confianza sin rellenar,
  idempotencia, no se pisa celda humana, Tipo/Parte inválidos, doc sin MD omitido,
  chat_fn obligatorio, adaptador llm_cloud. Suite 1008 passed / 58 skipped. `742e35a`.

---

## [SIGUIENTE-SALA-LECTURA-01] Sala de lectura y organización de `01_Procesado`

> 🗄️ **HISTÓRICO (triaje 2026-07-19).** El camino core de sala de lectura quedó superado por la skill
> `organizar-sala-lectura` (sala única). Bloque conservado como histórico; el futuro de la sala se decide en
> la decisión-madre `#56 vs #75` (ver `MEJORAS #75`/`#76`).
*Diseño cerrado con Nikolai 2026-06-12 (sesión Cowork, HANDOFF). Plan fino autocontenido: `docs/superpowers/plans/PLAN_SALA_LECTURA_01_PROCESADO.md` (incluye §0 con notas de Claude Code sobre el estado del repo). Implementación: Claude Code.*

**Objetivo.** Capa humana sobre `01_Procesado`: una **sala de lectura** (documentos
en claro y en orden, por fuente y narrativa) + una **capa de texto** (`MD/`) para
búsqueda. Índices `INDICE.md`/`CRONOLOGIA.md` de solo lectura. Clasificador/fechador
**híbrido** (reglas deterministas → LLM Scaleway solo para el residuo). `00_Input`
intacto; ningún camino de IA accede a `01`. Primera fase = ficheros en
`01_Procesado`; Streamlit y artifact Cowork **diferidos**.

**Acoplamientos detectados al leer el repo (doc §0, fijan la secuencia — no bloquean):**
- **#1 (cimiento):** la sala de lectura **es** `[SIGUIENTE-CATALOGO-DOCUMENTAL]`.
  `INDICE.md`/`CRONOLOGIA.md` se renderizan desde `indice_documental.yaml`, que
  **no existe** (Nikolai: "no construirlo a medias"). Construir la sala obliga a
  construir el catálogo. Falta añadirle `parent_id`/`orden_en_bundle` (D9 / MEJORAS #29).
- **#2:** el `_manifiesto.jsonl` del handoff solapa con `00_Input/_intake_hashes.json`
  (`IntakeManifest`) ya existente. Decisión: ¿catálogo único o tres artefactos?
  Inclinación: **catálogo único**.
- **#3:** el clasificador (Tarea 7) lee documento en claro → **misma excepción RGPD
  acotada** que el intake de procuradores (Scaleway UE). Maximizar reglas
  deterministas (filename, `id_carpeta_label`, `modified_at` ya en el DTO por D10).
  **Bloqueante solo de Tarea 7:** DPA Scaleway.
- **Menor:** apoyarse en `[IDEA-SKIP-INCREMENTAL-EXTRACCION]` #1 (doble `extract_all`)
  para cumplir el criterio de idempotencia; el grifo de MD (Tarea 2) toca el mismo flujo.

**Secuencia propuesta (doc §0.F):**
> - [x] **(0) cerrar doble `extract_all`** — ya cerrado s32; verificado s48.
> - [x] **(1) catálogo `indice_documental.yaml`** — `core/catalogo_documental.py` (`f253a84`).
>   Artefacto independiente; reconciliación con `_intake_hashes.json` **diferida**.
> - [x] **(2) scaffolding `Sala lectura/`+`MD/`+`_revisar/`** — en `ensure_case` (`f253a84`).
> - [x] **(3) grifo de MD en claro a `01_Procesado/MD/`** — `markdown_generator.build` +
>   consumidores `scorer.py`/`viability.py` (`f253a84`).
> - [ ] (4) copiador organizado + bundles (consumiendo `conjunto_detector`)
> - [ ] (5) render de índices
> - [ ] (6) clasificador híbrido (tras DPA)
>
> Cada fase con tests y suite verde.

**Decisiones abiertas (doc §0.G):** catálogo
único vs manifiesto aparte (diferida) · taxonomía documental (la redacta Cowork;
bloquea afinar el clasificador, no el cimiento) · DPA Scaleway (bloquea solo
Tarea 7) · correspondencia suelta.

---

## [SIGUIENTE-INTAKE-PROCURADORES-EMAIL] Intake automático de correos de procuradores → Sudespacho
*Diseño cerrado con Nikolai 2026-06-12. Plan fino autocontenido: `docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md`. Implementación: Claude Code.*

**Objetivo.** Sentido inverso del intake actual: archivar en el CRM los correos de
procuradores (y contestaciones a correos del despacho), relacionarlos con su
expediente y subir adjuntos con nombre legible, con red de seguridad humana antes
de escribir. Llave de emparejamiento = *Su ref* (= `num_expediente/serie`,
serie=año). **RGPD — excepción acotada SOLO a este flujo:** usa LLM cloud UE
(Scaleway/Mistral Small 3.2); no deroga la regla general del resto del repo.

**Estado por fases (detalle en el doc §15):**
- **F1 — Matcher (read-only).** ✅ HECHA (s39, 2026-06-12). `core/llm_cloud.py`
  (conector LLM cloud intercambiable) + `core/procurador_intake.py` (señales LLM +
  match por num/serie vía REST + propuesta de nombres). Validado e2e contra correos
  reales (ProcuradoraF 21/25→exp #532, Castañeda 33/2024→exp #455, ambos confianza
  ALTA). API `element_registries` usa `hydra:member`. Volumen ~7 correos/día,
  ~€0.10/mes. Tests +77; suite **853 passed, 58 skipped**. **Commits `f904d72`,
  `6a811ef`** (F1 base + fix match por su_ref con sufijo de subserie y `es_ruido`
  advisory).
- **F2 — Bandeja (Streamlit).** ✅ BACKEND ✅ / UI ✅. **Backend (s40, dry-run, TDD):**
  `core/procurador_review.py` (terna §18.9 + divergencia + log auditoría + máquina de
  estados de cola + store de cola), `core/procurador_runner.py` (process_email +
  run_intake, enrutado §6, dedup §4), `core/gmail_source.py` (adaptador Gmail
  verificado live read-only). Commits `a80afeb`/`00ee3b8`/`7b03759`/`3bedb22`/`95082f1`.
  El **requisito duro §18.9** quedó cumplido: la terna se captura en `record_decision`.
  **UI + CLI completados** (branch `feat/intake-procuradores-f2-ui`, plan/spec en
  `docs/superpowers/`): contexto de tarjeta persistido en la cola (`9490eca`),
  `fetch_expediente_datos`/`recompute_coincidencias` (`945030b`/`15df2f2`), CLI thin
  `scripts/intake_procuradores.py` sobre `fetch_and_run` (`1f336dc`), pestaña Streamlit
  «Bandeja de correos» (3 tarjetas 🟢/🟡/🔴 + login `set_actor` + acciones→
  `transicionar`/`record_decision`/`upsert_queue_item` + combobox de reasignación +
  vista Descartados) (`cbfafba`/`3b24f45`). **`search_expedientes` migrado a REST**
  (`feat/search-expedientes-rest`, fusionado): el probe contra el CRM real demostró que
  el autocomplete legacy devuelve body vacío (`DEAD_ENDS.md`); búsqueda por
  `referencia_cliente`+`referencia_procurador`+nº/serie, sin `clientes`; búsqueda por
  contrario/autos fuera de alcance (`MEJORAS_FUTURAS.md` §31). Suite **935 passed**.
- **F3 — Escritura en el CRM.** 🎨 **DISEÑO CERRADO (2026-07-19); pendiente construir.** El relate+adjuntar
  va por un **plugin propio de Roundcube** (`plugin.sudespacho_asignaa_*`), NO nest-mail/`MailRoundcube`/AppSync
  (refutados por HAR `judicial_648`). Llave = **Message-ID RFC** (conservado en el auto-forward de `procesal@`,
  verificado con cabeceras). **Spike de auth HECHO** (2 pruebas en vivo + HAR `handshake_webmail`): el plugin es
  llamable con la sesión del webmail (`fetch`+`X-Roundcube-Request=rcmail.env.request_token` → 200+JSON); el acceso
  es **SSO por `init.php?dataHash`** (blob cifrado client-side) → **transporte = webview**; headless-puro descartado
  (regenerar el `dataHash` + credenciales IMAP = frágil/inseguro). **A' viable** (archiva solo). Specs:
  `docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md` (v2, tras panel adversarial) +
  `…-intake-miniapp-entrega-design.md` (miniapp bajo demanda por persona, bandeja=visor compartido, índice-caché
  del emparejamiento en Drive, cada quien su cuenta, judicial-first, autoría→F6). SSOT del CRM:
  `INTEGRACION_SUDESPACHO §10.10/§14.5`; dead-end en `DEAD_ENDS`. **[SIGUIENTE]:** `writing-plans` → construir
  cliente `core/procurador_relate.py` (adaptador de transporte webview, TDD) + miniapp/bandeja mínima + índice-caché;
  validar relate/adjuntar reales en expediente de prueba. ✅ Limpieza de pruebas del CRM hecha (Nikolai, 2026-07-19).
- **F4 — Renombrado + OCR + aprendizaje.** ⬜ Contenido del adjunto → nombre; store
  de correcciones few-shot (§10).
- **F5 — Grabaciones.** ⬜ Descarga de enlaces (WeTransfer caduca) + fallback manual.
- **F6 — Control de calidad del archivo (check 2).** ⬜ Capa de auditoría por
  excepción (auto-chequeo determinista + cola de Paola + resumen semanal a Nikolai).
  **Diseño cerrado 2026-06-12, doc §18.** Depende de F2/F3 (consume la terna de traza).

**Pendientes de decisión (doc §17 + §18.11):** ¿confirmar en bloque las de alta de
inicio? · **auth del plugin Roundcube (sesión legacy PHPSESSID vs login propio) → decide A-vs-C** ·
plazos de escalado de la cola por tipo · tamaño de muestra (default 10%) · lista de "tipos con plazo".

---

## [SIGUIENTE-INTAKE-JUDICIAL-AUTO] Intake automático de demanda y contestación desde el CRM

> ✅ **CERRADO (triaje 2026-07-19)** → ledger `## ✅ Cerrados`. 5 fases ✅, validado e2e real. Bloque
> conservado como histórico.
*Añadido 2026-06-10 (sesión Cowork). Implementación: Claude Code. Engloba y resuelve `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` como su Fase 0.*

**Objetivo:** intake end-to-end de los dos documentos judiciales clave de un
expediente —demanda y contestación— desde el Gestor Documental del CRM hasta el
árbol del caso, sin el workaround manual (descarga SPA + expander Streamlit).
Flujo: localizar expediente judicial → identificar demanda y contestación →
descargar → depositar en cajón CRM → encadenar pipeline (anon → MD → frontier)
con dedup (M9) y log (M10, `_intake_log.jsonl`).

**Contexto verificado (sesión Cowork 2026-06-10, lectura de `core/sync_sudespacho.py`):**
- Listado OK: `list_gdocu_docs_rest` (`GET /api/element_registries/gdocu`) →
  `GdocuDocInfo(doc_id, filename, id_carpeta, id_carpeta_label, mime, size, raw)`;
  `id_carpeta_label` trae etiquetas tipo `"CIVIL"`.
- Descarga ROTA: `get_presigned_download_url` usa `ENDPOINTS["presigned_download_url"]`
  = `/api/files/presigned_download_url/{doc_id}` → HTTP 400. Es el bug crítico.
- PISTA: existe declarado pero **sin usar** `ENDPOINTS["presigned_download"]` =
  `/api/documents/presigned_urls/{service}/download/{documentId}` (`service="s3"`),
  mencionado en el docstring de cabecera → primer candidato a probar.
- Demanda/contestación viven en namespace `expedientes_judiciales` (ids no
  comparables con `expedientes_extrajudiciales`). Banco de pruebas: expediente 649 (BaRR3, 26 docs).

**Fases:**
- **Fase 0 (bloqueante) — desbloquear descarga.** ✅ HECHA (2026-06-10). La ruta
  alternativa del plan (`presigned_urls/s3/download`) **también estaba rota** (500);
  el endpoint vivo es `GET /api/documents/{id}/downloadUri` → `presignedDownloadUrl`.
  `get_presigned_download_url` reescrito, `docs/DEAD_ENDS.md` actualizado.
  Cierre cumplido: **31/31** docs del expediente 649 (creció desde 26) ✓.
- **Fase 1 — identificación.** ✅ HECHA. `core/judicial_classifier.py`:
  heurística regex source-locked **solo por `filename`** (la `id_carpeta_label`
  resultó demasiado gruesa — las carpetas DEMANDA/OPOSICION del CRM contienen
  toda la prueba; descubierto en el e2e del 649). Colapso de duplicados
  .pdf/.docx. Casos 0/múltiples → `[PENDIENTE revisión letrado]`, nunca adivina.
  Hook `llm_fn` inyectable pero **sin LLM por defecto** (decisión de Nikolai;
  RGPD: ningún nombre con PII sale del entorno).
- **Fase 2 — routing + pipeline.** ✅ HECHA. `core/judicial_intake.py`
  reutiliza `pull_expediente_v2` (nuevo param `only_doc_ids`) → dedup M9, log
  M10, routing `crm_branch_path`, estado D8. Solo baja demanda+contestación;
  `documents_total_crm` sigue siendo el total real. Pipeline encadenado por el
  caller (`--run-pipeline` / checkbox).
- **Fase 3 — disparo.** ✅ HECHA. CLI `intake-judicial --case --expediente
  [--run-pipeline]` + **botón** en el tab Casos de Streamlit
  («⚖️ Intake judicial automático»).
- **Fase 4 — tests y cierre.** ✅ HECHA. Tests del clasificador (con etiquetas
  reales del 649 como regresión) + orquestador. E2E real: demanda 40022
  auto-depositada, contestación marcada pendiente (2 candidatos). Suite verde.

**Decisiones cerradas (2026-06-10, con Nikolai):**
- Clasificación: heurística por `filename` (la etiqueta de carpeta NO dispara).
  **Sin LLM** — la ambigüedad va a revisión del letrado (RGPD-local).
- Disparo: **CLI + botón Streamlit**.

**Siguiente acordado — `[SIGUIENTE-INTAKE-CRM-COMPLETO]` (sesión 2026-06-10):**
bajar TODO el expediente del CRM a `05_CRM` físicamente completo (sin que el
dedup M9 lo deje incompleto) + OCR/markdown/anonimización con el pipeline actual
+ contador de solapamientos byte-idénticos (para decidir con datos si el "dedup
en extracción" merece construirse, que queda APLAZADO). Plan fino autocontenido
para hilo nuevo: **`docs/superpowers/plans/PLAN_INTAKE_CRM_COMPLETO.md`**.
- **Paso 1 (bajar todo + `physical_complete` + contador `documents_overlap`) HECHO
  en código** (`pull_expediente_v2`, `intake_demanda_contestacion(full=…)`,
  `intake-judicial --full`); falta cierre formal (`✅` + hash del PR).
- **Paso 2 (procesado) SUPERSEDIDO** por las salas nuevas (no `pipeline.run`); la
  reconsideración formal del motor/ejes queda **aparcada** en
  `[APARCADO-INTAKE-CRM-A-LLM]` (abajo).

**Siguiente acordado — `[SIGUIENTE-DEDUP-GUARD-ROBUSTO]` (apuntado 2026-06-10):**
guarda para **no duplicar expedientes ni en el CRM ni en el Drive** al crear un
caso. Hoy es frágil a variaciones tipográficas de la referencia/nombre.

- **Problema detectado (2026-06-10):** el botón «Crear caso + enviar a sudespacho»
  NO bloquea el expediente 444 porque su `referencia_cliente` en el CRM tiene un
  **doble espacio** (`(W-02NV4W)  - Vuelta`) y el case_id estándar lleva uno solo
  → la búsqueda exacta `find_expediente_judicial_by_referencia` devuelve `None` →
  **crearía un expediente duplicado**.
- **Qué hacer:**
  1. **Guarda CRM** (`core/sudespacho_relations.py`,
     `find_expediente_*_by_referencia` / `verify_expediente_referencia`):
     comparar referencias **normalizadas** (espacios repetidos colapsados, sin
     acentos, sin distinción de mayúsculas; reutilizar `_normalize_label`).
  2. **Guarda Drive** (`core/intake_drive.py`): aplicar la misma normalización al
     emparejar caso ↔ carpeta E&V por nombre/referencia, para no crear/pullar a
     una carpeta duplicada (revisar dónde se hace el match).
  3. **UI** (`streamlit_app.py` ~L1675): el aviso «no se creará un expediente
     duplicado» es **engañoso** — mira el `_caso.md` local y NO impide la
     creación; la única protección real es la búsqueda en el CRM. Corregir el
     texto y/o hacer que la guarda CRM realmente bloquee.
- **Riesgo si no se hace:** expedientes/carpetas duplicados, caros de deshacer.

---

## [APARCADO-INTAKE-CRM-A-LLM] Cadena CRM Gdocu → salas → registros → LLM
*Abierto 2026-07-10 (Nikolai); **APARCADO 2026-07-10** tras re-brainstorming con superpowers.
Doc: `docs/superpowers/specs/2026-07-10-intake-crm-a-llm-design.md` (banner APARCADO, mergeado
PR #19). Detalle del re-brainstorming en el comentario del PR #19.*

**Estado: APARCADA la construcción de los ejes** (decisión de Nikolai). Motivo: el proceso
(intake CRM → sala de máquina → sala de lectura → registros) **no está rodado** para decidir
sobre datos reales; el ROI en €/tiempo del doc (§5.3/§8) es estimación **sin medir**. No se
promueve a plan de implementación.

**Qué conserva valor (mergeado, no se retoca):** el runbook end-to-end y el mapa de estado
verificado del flujo (§1–3 del doc). El §4–8 queda archivado como brainstorming.

**Hallazgos (si se reabre, no re-derivar):** "eficiencia de tokens" no es objetivo (Claude-en-
sesión: solo muerde por caber en contexto); `scorer`→`viability` es **código muerto** sobre el
MD viejo (el flujo vivo es la skill leyendo crudo `00_Input/`); dolor único confirmado =
babysitting de casos grandes, **0 decisiones malas observadas**; de los ejes, **E2 (leer MD) es
el portante**, E3 marginal + gate extra, E4 no toca el babysitting (reutilización aguas abajo),
E5 descartado; anti-correlación sospechada (grandes = testificales, document-dependent =
pequeños y ya caben).

**Si se reabre:** probar **E2-sola, opt-in, disparada por tamaño** — NO el trío E2+E3+E4.
**Disparadores:** (a) un go/no-go real poco fiable por desbordar; (b) volumen suficiente para
medir la distribución de tamaños de caso; (c) haber cronometrado UNA corrida local (intake +
`sala_maquina apply` + lectura).

**Higiene independiente (sigue pendiente, NO aparcada):** cerrar formalmente el Paso 1 de
`[SIGUIENTE-INTAKE-CRM-COMPLETO]` (hecho en código, falta `✅` + hash).

---

## [SIGUIENTE-INTAKE-ENTREVISTAS] Intake dedicado de entrevistas (transcripción Meet) en `06_Entrevistas/`
*Promovido 2026-06-10 (sesión Cowork) por decisión de Nikolai. `MEJORAS #26`. Implementación: Claude Code.*

**Objetivo.** Cablear la subida de la entrevista de viabilidad (grabada en Google
Meet, transcripción automática) al árbol del caso, hoy sin conectar.

**Estado verificado (repo, 2026-06-10).** El andamiaje existe pero está muerto:
`ensure_case` crea `00_Input/06_Entrevistas/`; `ENTREVISTA_ROLES`
(`core/config.py`) y la convención `<AAAA-MM-DD>_<rol>_<apellido>/` están
definidas pero **ningún código las consume ni valida**; el evento
`upload_entrevista` (`core/intake_log.py`) y el source `"entrevista"`
(`core/intake_manifest.py`) están declarados pero **nunca se emiten**. No existe
`core/intake_entrevista*.py` ni uploader en Streamlit. El paso 7 del refactor v2
solo cableó el expander de subida a `05_CRM`. Hoy la entrevista solo entra si el
letrado deja manualmente la transcripción en la carpeta, sin dedup ni traza.

**Solución (ya recogida en `docs/MEJORAS_FUTURAS.md` §26).** No requiere
transcripción local (Whisper): Meet ya entrega texto. Dos piezas:

1. **Función de ingesta** (`core/intake_entrevista.py` nuevo o ampliación de
   `core/intake_manual.py`): dado rol ∈ `ENTREVISTA_ROLES`, apellido, fecha y el
   Doc de Meet, crea `06_Entrevistas/<AAAA-MM-DD>_<rol>_<apellido>/`, coloca la
   transcripción exportada a `.docx`/`.txt`, la registra en el manifest con
   `source="entrevista"` y emite el evento `upload_entrevista`. Validar rol contra
   `ENTREVISTA_ROLES` y sanear el path como en `save_file_crm_branch`.
2. **Disparo en la UI** (expander/botón en el tab Casos de Streamlit), análogo al
   de `05_CRM`.

Una vez el `.docx`/`.txt` está en `00_Input/06_Entrevistas/`, el pipeline genérico
(inventory → extractor → markdown → anon) ya lo procesa. La 2ª pasada de
`viabilidad-prerelleno` (leer la transcripción para cerrar huecos testificales)
queda fuera de alcance de este bloque.

---

## [SIGUIENTE-INTAKE-EXPEDIENTE-AGIL] `intake-expediente` más ágil y con menos diálogos de permiso
*Promovido 2026-06-23 (sesión Cowork) por decisión de Nikolai. `MEJORAS #43`. Implementación: Claude Code (edición de la skill en `.claude/skills/intake-expediente/` + re-empaquetado del `.skill`).*

**Objetivo.** Que el intake desde Cowork (vía `expedientes-xl`) sea más rápido y dispare
menos diálogos de permiso por-llamada. Disparador: intake real del zip W-01VG51 → W-02VND1
(2026-06-23), donde el flujo hizo ~10 llamadas evitables y un round-trip muerto.

**Dos palancas (una es código, la otra es ajuste del cliente):**

1. **Skill (código) — menos llamadas al Drive:**
   - **Una sola pasada**: extraer a staging solo para listar/`hash_path`; tras el OK, copiar
     con **`copy_dir`** cuando todo va a una misma `<fuente>` (en vez de N `copy_path`).
   - **Gate sin OCR**: para escaneados, proponer `sin-fecha_...` por defecto y **no** ofrecer
     extraer fechas en Cowork (rama fuera de capa e inviable; la datación es del pipeline
     local hasta que exista `MEJORAS #42`).
   - **Regla dura**: nunca copiar binarios al mount para leerlos con bash (mount aislado del
     Drive; ver `DEAD_ENDS.md`).
   - Efecto colateral: menos operaciones sobre el Drive ⇒ menos diálogos de permiso si el
     usuario no ha activado "Permitir siempre".

2. **Cliente (NO código) — eliminar los diálogos de raíz:** activar **"Permitir siempre"**
   para el conector `expedientes-xl` en Claude Desktop/Cowork **una vez** → cero diálogos
   durante la ejecución. Es el arreglo definitivo del permiso; ningún cambio de skill lo
   sustituye (la propia skill ya lo documenta como ajuste del cliente). **Acción de Nikolai**,
   no de Claude Code.

- [ ] (1) Editar la skill `intake-expediente` (procedimiento + gotchas) e re-empaquetar `.skill`.
- [ ] (2) Activar "Permitir siempre" para `expedientes-xl` (acción manual de Nikolai).

---

## [SIGUIENTE-GOBERNANZA-FUENTES-VERDAD] Unificar fuentes de verdad (estructura/taxonomía/arquitectura)

Propuesta completa en `docs/GOBERNANZA_FUENTES_VERDAD.md` (disparador: revisión de
scaffolding, s. 2026-07-05). Extiende, sin contradecir,
`[CRITICO-FUENTES-VERDAD-PLANIFICACION]` (2026-05-29) e `[IDEA-GOBERNANZA-DOCS]`
(2026-06-10): la planificación ya está unificada; falta el drift de hechos que la
prosa copia del código.

- [x] **Fase 1** (riesgo cero) — **HECHA 2026-07-05**: README reescrito para orientar
  (FeesGuard→FeesDefender + banner a las fuentes canónicas; sin transcribir estructura/pipeline);
  cola de prioridad de `STATUS.md` archivada en `docs/bitacora/STATUS_cola_historica_pre_2026-07.md`
  (`estado: histórico`) + puntero a `PLAN.md` (STATUS 1117→442 líneas); `_skills_drafts/`→`_skills_ARCHIVO/`
  (`git mv`) + `scripts/package_skill.py` deja de empaquetar ese root. **`core/__init__.py`
  (`__product__`/`__product_long__`/docstring) FeesGuard→FeesDefender — HECHO 2026-07-06** (no lo
  importa ni testea nadie; verificado). Las apariciones `FeesGuard/0.1` en
  `sync_sudespacho_legacy.py`/`DEAD_ENDS.md` son User-Agent HTTP real, **NO tocar** (se dejan).
- [x] **Fase 2** — **HECHA 2026-07-05**: en `STATUS.md`, tabla de taxonomía y estructura
  de carpetas del caso reemplazadas por punteros a `core/config.py` (`TIPOS_CASO_*`,
  `CASO_SUBDIRS`); regla añadida al mapa de dependencias de `docs/ARQUITECTURA.md` (marca
  `[FUENTE ÚNICA]` + lista de espejos documentales legítimos). **Test guard**:
  `tests/test_gobernanza_taxonomia.py` (8 tests, verdes) — **ancla el código como fuente de
  verdad** (fija ACTORA=7, DEFENSIVA=4, OTROS=1, `CASO_SUBDIRS`, mapeo de posición); habría
  cazado el drift real que tenía STATUS ("3 tipos defensivos" cuando el código ya tenía 4).
  HALLAZGO que cambió el diseño: la taxonomía vive legítimamente en ~9 `.md` (skills LLM que
  corren en servidor + referencia CRM + bitácora en prosa), así que un escáner de `.md` daría
  falsos positivos → se descartó a favor del anclaje en código (nombre `test_docs_no_duplican_taxonomia.py`
  del plan original abandonado por eso). Suite NO ejecutada aquí (entorno remoto sin venv; lógica
  del guard validada importando `config`).
- [x] **Fase 3** — **HECHA 2026-07-05**. (a) Specs: decisión de Nikolai = **etiquetar, no mover**
  → frontmatter `estado:` en los 11 `PLAN_*.md`, `docs/INDICE.md` como índice único de ciclo de
  vida, regla fijada (specs nuevos nacen en `docs/superpowers/`). (b) Vendorizar la referencia
  sudespacho: **DESCARTADO** — el SSOT (`docs/ARQUITECTURA_RELACIONES.md`, creado en paralelo) la
  define como fuente externa compartida con El Contable/El Auditor; se mantiene fuera. (c)
  `GOBERNANZA_FUENTES_VERDAD.md` reconciliado con el SSOT (se complementan, no se duplican).
- [ ] **Gobernanza ligera** (recomendaciones, pendientes de arrancar): rotación de `STATUS.md` a
  `docs/bitacora/YYYY.md` (parcial: cola histórica ya archivada en Fase 1); invariantes en
  `session_close`; frontmatter `estado:`/`dueño:` + `docs/INDICE.md` (✅ índice creado en Fase 3).
- [ ] **Higiene de PII en la bitácora** (recomendación nº4, propuesta 2026-07-06 en
  `GOBERNANZA_FUENTES_VERDAD.md §4`). Regla: la bitácora referencia por código `W-xxxxx`, sin correos
  ni nombres de terceros ni direcciones (el dato sensible vive en `data/CASOS/`, fuera del repo).
  Huella medida en tracked docs: correos de terceros de casos reales (PersonaUno, PersonaTres, PersonaCuatro,
  PersonaCinco…) mezclados con sintéticos de test, y también en **tests/core** (`email_atomize`/`whatsapp_atomize`),
  no solo en la bitácora. **Piezas:** (1) regla going-forward + check opcional en `session_close`;
  (2) **saneamiento retroactivo del historial** (`git filter-repo`).
  - **2026-07-06: repo puesto en PRIVADO** (corta exposición en curso — era público).
  - **Runbook + mapa de redacción entregados a Nikolai** (fuera del repo: contienen la PII a purgar).
    Ejecuta él en su PC (backup → clon fresco → filter-repo → grep+pytest verde → force-push →
    ticket a GitHub Support para cachés/commits colgados + revisar forks).
  - [ ] **TIER 1 (PRIMERO): purgar lo más sensible** — correos, nombres de personas, teléfonos reales.
    Mapa activo. Pendiente de que Nikolai lo ejecute.
  - [ ] **TIER 2 (SEGUNDO PASE, pendiente): direcciones de inmuebles** — incrustadas en case_ids y
    nombres de fichero de fixtures → mayor riesgo de romper tests. Se hace tras validar Tier 1.
  - [ ] **Fixtures sintéticas** para `email_atomize`/`whatsapp_atomize` (nacieron de un caso real) —
    tarea aparte, para que la PII no vuelva a entrar de raíz.

## Aparcado mientras el bloque crítico no se cierre

- `[SIGUIENTE-ORGANIZADOR-UI]` — **DESCARTADO 2026-06-07** (Ollama demasiado
  lento e impreciso). Sustituido por `[SIGUIENTE-CATALOGO-DOCUMENTAL]`;
  ver "Notas de la sesión Cowork 2026-06-07" abajo.
- `[SIGUIENTE-SUBDIVISION-CIUDADES]` — refactor `CASOS_ROOT` por ciudades
  (Fase 1).
- `[SIGUIENTE-SaRS1-PIPELINE]` H6 — subida manual gdocu expediente 659 +
  entrega a Claude frontier (depende del pull, lógicamente atado al
  bloque crítico).

---

## Resuelto

### [CRITICO-FUENTES-VERDAD-PLANIFICACION] — RESUELTO 2026-05-29

**Resolución (sesión Cowork 2026-05-29):** auditadas las fuentes de verdad de
planificación y consolidadas. La bitácora (`PLAN.md`, `STATUS.md`, historial de
commits) deja de vivir en Drive y pasa al **repo como única fuente de verdad**.

Decisiones cerradas:
- `PLAN.md` (raíz del repo) — cola priorizada compartida; la editan Cowork (PC)
  y Claude Code. Cowork móvil queda fuera del lazo hasta que exista un conector
  MCP de GitHub (hoy **no existe en el registry**; la vía OAuth/GitHub App no la
  soporta el flujo de conector personalizado y Docker+PAT es solo escritorio).
- `STATUS.md` (raíz del repo) — estado fáctico + bitácora de cierre, escrito por
  Claude Code.
- Historial: `git log`. Se **deprecan** `ESTADO.md` y `commits.log` como
  artefactos separados en Drive (duplicación + lag PC→nube generaba divergencia;
  el conector Drive de Cowork solo soporta create, no update → duplicados).
- Acceso móvil: app de GitHub (lectura); edición ocasional vía GitHub web.
- Drive queda solo para expedientes jurídicos (`CASOS_ROOT`) y entregables.

Regla documentada en `CLAUDE.md` §"Planificación y estado". La carpeta Drive
`Proyectos/FeesDefender/` la archiva Nikolai manualmente.

<details>
<summary>Problema original (apuntado 2026-05-28) — para trazabilidad</summary>

Convivían varias fuentes donde se registraban prioridades, decisiones, estado y
planes; el solapamiento generaba riesgo de drift, duplicación de la verdad y de
arrancar por una prioridad obsoleta. Fuentes detectadas: `PLAN.md` (Drive),
`STATUS.md` (repo) / `ESTADO.md` (Drive), `CLAUDE.md`, `README.md`,
`docs/PLAN_*.md`, `docs/MEJORAS_FUTURAS.md`, `docs/DEAD_ENDS.md`,
`bitacora/commits.log` (Drive), memoria de Cowork, project instructions de Cowork,
`docs/INTEGRACION_SUDESPACHO.md`. Riesgo ya materializado: el
`[CRITICO-PRESIGNED-DOWNLOAD-BUG]` vivía en `STATUS.md` pero no en la cola de
máxima prioridad, y hubo que rescatarlo a mano el 2026-05-28.

</details>

---

## Notas de la sesión Cowork 2026-05-28

- Verificado el pipeline de intake CRM: pull v2 implementado, CLIs en
  `scripts/sync_sudespacho.py` (`pull`, `sync_all`), `scripts/bulk_pull_expedientes.py`,
  `scripts/scheduled_sync.py`. NO hay botón en la UI Streamlit para lanzar
  el pull — solo CLI.
- Confirmado el workaround manual vigente para meter requerimientos y
  respuestas a requerimientos descargados manualmente del CRM: usar
  expander "📂 Subir al árbol CRM" (con rama canónica) o, como atajo,
  "📄 Demanda / documentos judiciales" (cajón `04_Manual/`). Ambos
  entran al ciclo anon → MD → frontier por igual; el primero deja además
  rastro en `_intake_log.jsonl`.
- Subido `[CRITICO-PRESIGNED-DOWNLOAD-BUG]` a máxima prioridad — antes
  estaba documentado en `STATUS.md` pero no en cabeza de cola.
- Apuntado `[CRITICO-FUENTES-VERDAD-PLANIFICACION]` — auditoría meta del
  proceso de desarrollo, motivada por la observación de Nikolai de que
  conviven demasiadas fuentes de verdad. **Resuelto el 2026-05-29** (ver arriba).

## Notas de la sesión Cowork 2026-06-07

### Decisión — Organización documental por caso

**1. Organizador local con Ollama → DESCARTADO** (`[SIGUIENTE-ORGANIZADOR-UI]`).
Ollama (Qwen 2.5 14B) demasiado lento e impreciso para esta tarea. La ventaja
de "local" (privacidad/coste) no compensa aquí: ya se anonimiza antes y ya hay
LLM cloud en el pipeline; nombres y estructura no son el payload sensible.
Coste de mantenimiento alto para usuarias no técnicas (fallos silenciosos) y la
vista `_organizado/` duplica almacenamiento.

**2. Sustituto → `[SIGUIENTE-CATALOGO-DOCUMENTAL]`: catálogo YAML canónico +
`INDICE.md` derivado.**

- `indice_documental.yaml` en la raíz del caso = fuente de verdad canónica,
  propiedad del código. Lo consumen pipeline, sync CRM, bitácora y (futuro)
  El Auditor.
- `INDICE.md` auto-renderizado desde ese YAML, de **solo lectura** (cabecera
  "no editar a mano"), para humanos (Paola, Ana, Marta E&V).
- Las ediciones entran por UI/pipeline, **nunca tocando el YAML a mano** (evita
  mojibake/encoding y conflictos de escritura concurrente).
- **Excluir siempre `90_NOTAS_PERSONALES/`** del indexado. El YAML convive con
  la nomenclatura de carpetas, no la sustituye.
- Esquema mínimo por entrada: `id_doc`, `ruta_relativa`, `nombre_original`,
  `tipo_documental`, `fecha_doc`, `parte` (propietario/buscador/tercero),
  `fuente` (E&V/cliente/juzgado), `estado` (original/anonimizado/borrador),
  `hash`, `fecha_indexado`.
- El desorden de carpetas heredado, si es masivo, se trata con un **script de
  migración puntual**, no con una feature permanente.

Patrón YAML→render coherente con el renderer YAML→XLSX de plantillas de
viabilidad. Implementación: Claude Code.

### Idea técnica — `[IDEA-SKIP-INCREMENTAL-EXTRACCION]`

**Origen**: consulta de Nikolai (sesión Cowork 2026-06-07) sobre qué pasa al
relanzar el pipeline con intake ya parcialmente OCRizado/markdowneado/anonimizado.

**Hallazgos al leer el código**:
- `extractor.extract_all` y `markdown_generator.build` **no son idempotentes**:
  reprocesan y sobrescriben todo `01_Procesado/` en cada corrida, exista o no.
  Solo `core/anon` salta por hash (`origen_sha256` en frontmatter, política
  `SALTAR`/`REPROCESAR`).
- **Bug de eficiencia**: `core/pipeline.py` llama a `extract_all` **dos veces**
  por corrida — paso `extractor.extract_all` y de nuevo dentro de
  `_markdown_step`. El OCR (Docling, el único paso caro) se ejecuta el doble de
  lo necesario, se toquen o no los documentos.

**TODO para Claude Code** (por orden de valor/riesgo, de mayor a menor):

- [ ] **1. Arreglar la doble llamada a `extract_all`** en `core/pipeline.py`
  (gana 50 % de OCR, riesgo cero). Cachear el resultado y pasárselo a
  `markdown_generator.build` en vez de reextraer. **Hacerlo aunque se descarte
  el resto.**
- [ ] **2. Skip incremental en extracción** por `sha256` del origen + versión de
  extractor (invalidar si cambia el backend Docling), reutilizando el patrón de
  `core/anon`, con `--force`.
- [ ] **3. Markdown que siga a la extracción**: regenerar solo el `.md` de los
  archivos realmente reextraídos. Trivial una vez la extracción devuelve cuáles
  saltó.

**Matiz de coherencia**: la regla de `CLAUDE.md` "Pipeline idempotente:
re-ejecutar nunca toca `00_Input/`" significa "no muta inputs", no "salta lo ya
hecho". El skip refuerza esa idempotencia, no la rompe. Implementación: Claude Code.

## TODO — Refactor de `hechos_atomicos`: extractor source-locked
*Sesión Cowork 2026-05-29*

**Decisión**: sustituir el prompt LLM único actual (`core/viability.py::analyze` → `02_Analisis/hechos_atomicos.md`) por un extractor en tres capas (E + B + C) que deposita un `08_Para frontier/_hechos.md` 100 % citado.

**Motivación**: el prompt actual es no determinista, no obliga a anclar cada hecho a un span literal del documento fuente y contradice la regla source-locked del despacho (skill `verificacion-anclada-fuente`). El frontier hoy recibe un `.md` que ningún verificador puede auditar.

**Arquitectura objetivo**

- **Capa C — extractor estructurado por `tipo_caso`**: esquema fijo de hechos esperados (hoja encargo, oferta, aceptación/rechazo, incumplimiento, reclamación previa, etc.) por cada `tipo_caso` de `TIPOS_CASO_ALL`. Function calling / JSON schema sobre `06_Anonimizado/`. Huecos como `[PENDIENTE]`. Reaprovecha la ontología del cuestionario de viabilidad (82 preguntas) y las plantillas YAML de `data/_plantillas/`.
- **Capa E — extracción por documento**: para cada `.md` en `06_Anonimizado/` se generan claims residuales fuera del esquema. Contexto pequeño = menos alucinación; ningún claim cruza documentos.
- **Capa B — verificador de spans**: cada claim emerge como `(paráfrasis, span_literal, doc, página, párrafo)`. Si el `span_literal` no aparece en el documento citado (con tolerancia OCR razonable), el claim se descarta automáticamente. Cero hechos sin anclaje verificable.

**Output**: `08_Para frontier/_hechos.md` con (i) ficha estructurada del `tipo_caso` y (ii) hechos adicionales por documento. Frontmatter neutralizado sin `case_id` literal (coherente con H5b SaRS1).

**Pasos sugeridos**

1. Definir esquemas de hechos por `tipo_caso` en `data/_plantillas/hechos/`, reaprovechando campos del cuestionario.
2. Implementar capa C (function calling / structured output; Sonnet para campos relacionales, Haiku para campos atómicos).
3. Implementar capa E (extracción doc-a-doc con cita obligatoria).
4. Implementar capa B (verificador de spans con normalización: lowercase + colapso espacios + remoción puntuación; match exacto sobre cadena normalizada, sin Levenshtein, para no aceptar paráfrasis disfrazadas).
5. Integrar como paso del `core/pipeline.py` después de anonimización, antes de `08_Para frontier/`.
6. Tests E2E sobre BaRS1 + SaRS1: cobertura sobre hechos clave + 0 falsos positivos sin anclaje.
7. Decidir: deprecar `hechos_atomicos.md`/`contradicciones.md`/`prueba_indexada.md` legacy en bloque, o mantenerlos como vista interna durante transición. Inclinación Cowork: deprecar — la duplicación crea divergencia.

**Decisiones pendientes (cerrar antes de implementar)**

- Modo del verificador en CI sobre casos en producción: ¿informativo o bloqueante? Inclinación: informativo en primera fase, bloqueante una vez estabilizado.
- Granularidad del span: ¿párrafo entero, oración, o N caracteres alrededor del hecho? Inclinación: oración completa por defecto, ampliable a párrafo si el hecho es relacional.

**Dependencia con la migración Drive → repo**: ninguna. Pueden ejecutarse en paralelo.

---

## [SIGUIENTE-REORG-05CRM] Aplanado de `05_CRM` por buckets procesales + detector de conjunto
*Añadido 2026-06-10 (sesión Cowork). 15 decisiones aprobadas por Nikolai. Implementación: Claude Code. Capa de nombrado/bundles (D1-D3) documentada en `docs/MEJORAS_FUTURAS.md` #28-#29.*

> **✅ PRIMERA TANDA COMPLETADA 2026-06-10 (Claude Code).**
> - [x] **Paso 0 / D8** — `CARPETA_ID_TO_PATH` poblado: `308`→Declarativo/Oposicion,
>   `380`→Preliminares/Demanda. Descubiertos vía `category_unknown`, doble
>   verificación UI (Nikolai) + REST. Solo había 2 IDs no mapeados en toda la
>   data real. El endpoint de árbol es dead end (§13.3); rama ambigua se cierra en UI.
> - [x] **D6** — `_bucket_for(rama_canonica)` (pura) + exclusión Preliminares,
>   aplicada en `crm_branch_path` (`core/case_manager.py`). Routing por rama
>   completa, no por etiqueta-hoja.
> - [x] **D7** — andamiaje *lazy*: `_ensure_crm_tree_dirs` crea solo `05_CRM/`;
>   los buckets se materializan al escribir. **D15** documentado (05_Procedimiento).
> - [x] **D12-D13** — `scripts/migrate_05crm_buckets.py` (in situ, sin re-bajar
>   ni re-OCR; re-llave manifest + extract_state; colisión de stem; by_carpeta;
>   journal + .bak). **Expediente 444 migrado**: 96 docs → {01_Demanda:23,
>   05_Diligencias_Preliminares:31, 99_Otros:42}, 0 colisiones, 0 re-OCR.
> - [x] **D14** — `test_crm_branch_path.py` reescrito (buckets + anti-sobrecaptura
>   + unit de `_bucket_for`), `test_pull_expediente_v2.py` y `test_smoke_paso7.py`
>   actualizados, `test_migrate_05crm_buckets.py` nuevo. `test_dedup_manifest.py`
>   y `test_judicial_intake.py` revisados (agnósticos a ruta, sin cambios).
>   Suite verde; gold SaRS1 intacto.
>
> **✅ SEGUNDA TANDA COMPLETADA 2026-06-10 (Claude Code, sesión 35).**
> - [x] **D10** — `fechamodificacion` traída al listado REST
>   (`properties[12]`) + campo `modified_at` en el DTO `GdocuDocInfo`.
>   Nombre/formato confirmados **en vivo** contra el 444
>   (`scripts/probe_gdocu_fecha.py`; 97/97 docs con fecha). ISO-8601 con offset.
> - [x] **D9** — detector de conjunto (`core/conjunto_detector.py`): clúster por
>   `modified_at` idéntico ∩ patrón `\bD\s*\d+…-`; cabecera = odd-one-out sin
>   patrón (en el 444 es `ORDINARIO…VALLDAURA.doc`, **no** "DEMANDA" → keyword
>   solo como desempate); bucket por cabecera o consenso; baja confianza →
>   `pendiente_revision`. **Solo emite propuestas** (eventos `conjunto_detectado`
>   / `pendiente_revision`); **persistencia de `parent_id` DIFERIDA** a
>   `[SIGUIENTE-CATALOGO-DOCUMENTAL]` (catálogo `indice_documental.yaml` **no
>   existe** — decisión de Nikolai: no construirlo a medias). Validado contra el
>   444 real (3 lotes, 0 misrouting). CLI on-demand
>   `scripts/detectar_conjuntos.py`. Nuevo evento `conjunto_detectado` (INTAKE_EVENTS 16→17).
> - [x] **D11** — override local `doc_id→bucket` en `bucket_override` del
>   frontmatter de `_caso.md`, respetado por `crm_branch_path` por encima de la
>   carpeta del CRM (`kind == "override"`), sin tocar el CRM remoto. Cableado en
>   el pull (lectura única por corrida). Refactor: `resolve_bucket` como fuente
>   única de la resolución carpeta→bucket (compartida con el detector).
> - **Pregunta abierta resuelta:** confirmado contra el 444 que **solo la prueba
>   de la actora usa `D NN`**; cabecera y contestación NO → la cabecera se
>   detecta como el doc sin patrón.
> - **Tests:** +3 D10, +~13 D9 (`test_conjunto_detector` nuevo), +7 D11,
>   `test_intake_log` (17 eventos). **Suite: 652 passed, 58 skipped** (verja
>   rápida, EXCLUYENDO `test_sudespacho_relations.py` — ver ⚠️). Gold SaRS1 intacto.
> - **⚠️ Ajeno a esta tanda:** `core/sudespacho_relations.py` + su test están
>   modificados en el working tree por trabajo concurrente (no por esta sesión;
>   al inicio NO estaban modificados) y rompen la colección de pytest por import
>   circular. No se tocaron ni commitearon — revisar aparte.
>
> **Pendiente (TERCERA TANDA / futuro):** persistencia `parent_id` de D9 cuando
> exista `[SIGUIENTE-CATALOGO-DOCUMENTAL]`. Follow-up del intake manual (abajo)
> sigue sin abordar (requiere OK de Nikolai por ripple a UI).
>
> **Follow-up detectado (fuera de las 15 decisiones, decisión de Nikolai):** el
> intake **manual** (`intake_manual.save_file_crm_branch` + `list_crm_branch_files`
> + selector `CRM_TREE` en `streamlit_app.py:630`) sigue escribiendo a la rama
> profunda elegida en la UI; convendría bucketizarlo también (vía `_bucket_for`)
> para no recrear el árbol profundo que la migración elimina. No se tocó por
> estar fuera del alcance de la primera tanda (ripple a UI + ~6 tests de
> `test_smoke_paso7.py` no listados en D14).

**Objetivo.** Sustituir el árbol profundo del CRM en `00_Input/05_CRM/` (hasta 4
niveles + ~20 carpetas vacías de andamiaje) por una estructura plana de un nivel
con buckets procesales. Motivos: límite de ruta de Windows (260 car.) sobre un
Drive ya largo, y desorden de carpetas vacías. La estructura de `05_CRM` es
**solo navegación humana del input**: el pipeline (`extractor` →
`markdown_generator` → `anon`) aplana a un output por documento con slug
stem-only (`extractor.py:214`), independiente de la subcarpeta de origen.

**Árbol confirmado (D5).**

```
05_CRM/
├── 01_Demanda/                  ← Declarativo/Demanda (demanda + su prueba documental)
├── 02_Contestacion/             ← Declarativo/Oposicion (un solo bucket aunque haya varios demandados — D5b)
├── 03_Monitorio_Demanda/        ← Monitorio/Demanda (petición inicial + docs)
├── 04_Monitorio_Oposicion/      ← Monitorio/Oposicion (+ docs)
├── 05_Diligencias_Preliminares/ ← Preliminares/Demanda (solicitud de DP + docs)
├── 99_Otros/                    ← resto PLANO por fecha (procesales, resoluciones, Apelación, Ejecución, General, Documentos, RGPD/LOPD, Penal…)
└── 99_Sin categoria/<exp>/      ← fallback cuando id_carpeta no resuelve (ya existe hoy)
```

**Decisiones aprobadas (registro).**

- **D5 — Aplanar a 1 nivel** con el árbol de arriba. Cada bucket mapea 1:1 a una
  hoja real de `CRM_TREE`; se aplana el andamiaje intermedio
  (`Civil/1ª Instancia/Declarativo/…`), no las hojas con significado.
- **D6 — Routing por rama canónica completa, no por etiqueta-hoja.** Función pura
  `_bucket_for(rama_canónica)` aplicada en `crm_branch_path` (`case_manager.py:524`,
  único punto de routing, invocado en `sync_sudespacho.py:1444`). `Preliminares`
  en **lista de exclusión explícita**: su "demanda" (solicitud de DP) **nunca**
  cae en `01_Demanda` → va a `05_Diligencias_Preliminares`. Etiqueta-hoja pura
  sobre-captura (`"Demanda"` casa 3 ramas, `"Oposicion"` 2 → hoy ambas caen a
  fallback, confirmado por `test_crm_branch_path.py`).
- **D7 — Cambiar también el andamiaje** (`_scaffold_crm_tree`,
  `case_manager.py:841`): crear solo los buckets en uso o ir *lazy*
  (crear-al-escribir). Tocar solo el routing dejaría las carpetas vacías.
- **D8 — Requisito previo (paso 0): poblar `CARPETA_ID_TO_PATH`** con los
  `id_carpeta` reales del tenant para las ramas procesales (hoy solo 2 IDs
  mapeados; las etiquetas son ambiguas → casi todo cae a `99_Sin categoria`).
  Descubrimiento progresivo vía evento `category_unknown` ya existente. **Sin
  esto, aplanar es cosmética.** Doble verificación UI + API.
- **D9 — Detector de conjunto** para reagrupar cabecera + prueba **mal archivadas**:
  clúster por *timestamp de modificación del CRM idéntico* (subida en lote) ∩
  *patrón de nomenclatura* `D\s*\d+\s*-` (numeración de prueba del despacho; admite
  sub-índice `22-C`/`22-D`). Se ancla cada lote a su cabecera (`DEMANDA…`/
  `CONTESTACION…`) por cercanía temporal y se asigna al bucket de la cabecera.
  Clústeres de baja confianza → `pendiente_revision`, sin adivinar. La relación
  se persiste como `parent_id` en `indice_documental.yaml` (MEJORAS #29) →
  sobrevive aunque los ficheros queden físicamente dispersos.
- **D10 — Requisito previo de D9: traer la fecha de modificación del CRM.** Hoy
  NO se pide: la query REST solo trae `nombrefinal`/`mime`/`tamano`/`id_carpeta`
  (`sync_sudespacho.py:649-653`) y `GdocuDocInfo` no tiene campo de fecha
  (`:297-303`). Descubrir el índice de esa propiedad y añadir el campo al DTO.
- **D11 — Override local `doc_id → bucket`** editable por el letrado (en
  `_caso.md` o YAML del caso), respetado por encima de la carpeta del CRM, **sin
  tocar el CRM remoto**. Parche inmediato para el mal archivo.
- **D12 — Migrar in situ, NO re-bajar.** El re-pull no migra limpiamente: el
  dedup es por hash (`IntakeManifest.register`), así que un re-pull sin resetear
  manifest devuelve el `primary_path` viejo → con `physical_complete=True`
  duplica (copia vieja + nueva), con `False` no mueve. Migración: mover ficheros
  + reescribir `00_Input/_intake_hashes.json` (rel viejo→nuevo, o borrarlo y dejar
  que `reconcile()` reconstruya desde disco) + re-llavear
  `01_Procesado/raw_text/_extract_state.json` (clave = `rel_path`,
  `extractor.py:218`; los `.txt` NO se mueven, slug = stem) + `inventory.scan`.
  Así `extract_all` hace skip y **no re-OCRiza** los 96 docs del 444. Script
  puntual, no feature.
- **D13 — Pre-migración:** detectar **colisiones de stem** entre ramas que
  confluyan al mismo bucket (forzarían `__1` vía `_resolve_name_collision` →
  cambio de slug → re-OCR; o renombrar también el `.txt`). Refrescar `by_carpeta`
  en el frontmatter de `_caso.md` (queda rancio tras migrar).
- **D14 — Tests.** Asumir cambio de semántica de conteos (`documents_overlap`
  baja, `documents_skipped_dedup` sube — no es bug). Reescribir
  `test_crm_branch_path.py` (expectativas profundas → buckets + tests
  anti-sobrecaptura: `Preliminares/Demanda`→`05_…`, `Declarativo/Oposicion`→
  `02_…`, `Monitorio/Demanda`→`03_…`); actualizar `test_pull_expediente_v2.py` y
  `test_dedup_manifest.py` (claves `by_carpeta` + conteos); revisar
  `test_judicial_intake.py` (mayormente agnóstico a ruta). Añadir unit de
  `_bucket_for()` y test del script de migración (idempotencia + preservación de
  cache OCR + colisión de stem). El gold fixture **SaRS1 no se toca** (es upstream
  del anon; confirmar ejecutando la suite).
- **D15 — `05_Procedimiento`** (carpeta funcional de fase, hoy inerte: nadie
  escribe en ella; solo la crea el scaffolding y la barre `linker.py:19`).
  Mantener su rol semántico de **work-product del letrado para el litigio en
  curso**, diferenciado del espejo crudo del CRM (`00_Input/05_CRM/`). Documentar
  su propósito (hoy no consta). Aplicarle el criterio *lazy* de D7. Anotar la
  duplicidad del "05" (`00_Input/05_CRM` vs `05_Procedimiento`) como cosmética de
  baja prioridad.

**Capa de nombrado/bundles (D1-D3) → `docs/MEJORAS_FUTURAS.md`:** D1 (prefijo ISO
`AAAA-MM-DD`) y D2 (alcance solo `06_Anonimizado`/`INDICE.md`, identidad =
`id_doc`/hash) amplían #28; D3 (bundles cabecera-anexo por `parent_id` en el
catálogo, no subcarpeta física) es #29. D4: fuente única de verdad documental;
no se parchea el motor de anonimización (D8 histórico / `feedback_anon_logica_intacta`).

**Lo que NO se toca (F):** motor de anonimización, `separar.py`, `linker.py`,
independencia de `01_Procesado`/`06_Anonimizado` respecto a `05_CRM`, y la
decisión ya cerrada de descartar el organizador Ollama / vista `_organizado/`.

**Orden de ejecución recomendado.** Paso 0 (D8 descubrir IDs del tenant) →
routing `_bucket_for` + exclusión Preliminares (D6) + andamiaje lazy (D7) →
migración in situ del 444 preservando OCR (D12-D13) → tests (D14). El detector de
conjunto (D9) y su requisito (D10) y el override (D11) pueden ir en una segunda
tanda. Medir antes la ruta más larga real del 444: aplanar `05_CRM` solo ahorra
~30 car.; si no basta para cruzar 260, combinar con rutas largas `\\?\` o acortar
el ensamblado de nombre.

**Pregunta abierta (no bloquea):** confirmar contra una carpeta de contestación
real si el **demandado usa el mismo prefijo `D NN`** u otro, para afinar D9.

## [SIGUIENTE-HOMOGENIZACION-SKILLS] Charter + enforcement + retrofit de skills

> Handoff Cowork→Claude Code (2026-06-16). Diseño aprobado por el letrado. **Lo
> ejecuta Claude Code** (Cowork solo planifica). Objetivo: que todas las skills
> —actuales y futuras— compartan lo mejor del estándar y que las mejoras futuras
> se propaguen solas. **NO duplica `docs/MEJORA_CONTINUA_SKILLS.md`: lo
> referencia.** Estado verificado en disco el 2026-06-16.
>
> **ALCANCE REDUCIDO 2026-06-16 (tras crítica de ROI, aprobado por el letrado):**
> no hay escala que justifique la superestructura de gobernanza. Solo se ejecuta
> **corrección + mínimo reutilizable**; el resto se difiere. Ver «Alcance
> revisado» más abajo — manda esa sección sobre el «Plan por fases» original.

### Decisiones del letrado (cerradas)

1. **CHANGELOG.md separado** por skill (no sección `## Changelog` dentro del
   `SKILL.md`). Actualizar el paso 4 de `MEJORA_CONTINUA_SKILLS.md` para que
   apunte a `CHANGELOG.md`.
2. **Biblioteca de jurisprudencia compartida** en `_shared/jurisprudencia/`,
   referida por ECLI (no per-skill: evita N copias del mismo fallo). Migrar la de
   `oposicion`. Tradeoff asumido: menor autonomía de empaquetado.
   **(Ejecución DIFERIDA — ver Alcance: se queda en `oposicion` hasta que una 2.ª
   skill la necesite.)**
3. **Cosecha: se mantiene el modelo actual** (un fichero por sesión, push por
   conector al Drive del despacho; lo ven solo los abogados, no E&V).
   **SALVAGUARDA pendiente:** verificar **una vez** que el ACL de
   `Biblioteca_Skills/` excluye de hecho a los miembros de E&V (p. ej. Marta
   Reynares); en un Shared Drive los miembros heredan acceso a todo. Si los
   incluye, mover a carpeta restringida o a un drive separado.
4. **AGPL — `verificacion-anclada-fuente` se mantiene PURAMENTE INTERNA.**
   (a) conservar licencia + atribución actuales y añadir un `LICENSE` con el texto
   íntegro de la AGPL-3.0 + nota de "modificado por Tyukhay Legal";
   (b) **nunca co-empaquetarla** con skills propietarias (cada skill, su `.skill`);
   (c) **no exponerla por red** en el despliegue E&V (la cláusula §13 obligaría a
   publicar la versión adaptada). Si en el futuro se necesita exponerla, reabrir
   decisión: publicar la adaptada o reescribir una skill propia.
5. **Taxonomía `type` en dos ejes** (hoy mezclados): `rol`
   (transversal | fase | cliente | output) y `naturaleza`
   (atomica | orquestadora).
6. **Gobernanza: bus factor 1** (Nikolai, único aprobador de versiones, tags y
   promoción de jurisprudencia). El gate de calidad es el validador automático,
   no un segundo humano.

### Anatomía canónica (modular: núcleo + módulos por rol)

- **Núcleo (toda skill propia):** `SKILL.md` con frontmatter estándar,
  `CHANGELOG.md`, `LICENSE`, `.gitignore` (excluye telemetría).
- **Módulo OPERACIÓN** (skills que producen outputs en expediente: las 5
  procesales + `viabilidad-prerelleno`): helpers canónicos
  (`registrar_outputs.py`, `registrar_uso.py`, `programar_revision.py`,
  `scaffold_caso.py`) + bucle de `MEJORA_CONTINUA_SKILLS.md`.
- **Módulo EVOLUCIÓN:** `EVOLUCION.md` de 5 fases (plantilla en el charter).
- **Módulo JURISPRUDENCIA + COSECHA** (`oposicion`; candidatas `escritos`,
  `preparacion-*`): índice ECLI como SSOT en `_shared/jurisprudencia/` +
  consolidador + `drive_config.json`.
- **No aplican módulos** a `verificacion-anclada-fuente` (comportamiento
  transversal) ni `engel-volkers` (contexto de cliente): solo núcleo + identidad.

### Frontmatter estándar (esquema)

`name` (==carpeta), `description` (disparadores + "NO usar cuando…"), y bloque
`metadata`: `rol`, `naturaleza`, `jurisdiction`, `area` (lista), `version`
(semver entre comillas), `author`, `organization`, `contact`, `status`
(vigente | deprecada | experimental), `charter_version`, `orchestrates` (lista),
`requires` (lista), `evolucion_fase`. Más `license` de primer nivel. Para
**adaptadas de tercero**: añadir `author_original`, `adapted_by`,
`base_skill_url` y la licencia de origen (no relicenciar nunca a la baja).
`orchestrates`/`requires` hacen el **mapa de relaciones derivable y validable**
(no prosa que se pudre).

### Alcance REVISADO 2026-06-16 (manda sobre el «Plan por fases» original)

Tras crítica de ROI: 9 skills, un autor, uso bajo (ni 5 usos reales aún). No se
construye la superestructura de gobernanza. Solo **corrección** + **mínimo
reutilizable**. Lo demás, diferido a `docs/MEJORAS_FUTURAS.md` hasta que lo pidan
los datos.

**AHORA — valor inmediato:**

- **Ola 1 (correcciones), verifica el estado real en disco:**
  - Reconciliar `oposicion-alegacion-nulidad` a los helpers canónicos: su
    `scripts/log_uso.py` → `registrar_uso.py` (vías dentro de `metricas`);
    sincronizar helpers.
  - Retirar la **doble telemetría**: `preparacion-audiencia-previa/scripts/log_uso.py`
    y `preparacion-juicio-oral/scripts/log_uso.js`.
  - **Corregir el drift de vías** (3 vías viejas → 4 actuales: A nulidad absoluta ·
    B vicio del consentimiento · C incorporación · D contenido/abusividad) en el
    logger, en `EVOLUCION.md` (Fase 1) y en `logs/README.md` de `oposicion`.
  - **AGPL `verificacion-anclada-fuente`:** añadir `LICENSE` con el texto íntegro
    de AGPL-3.0 + nota de modificación (conservar atribución; no co-empaquetar con
    propietarias). Higiene legal barata.
- **Mínimo reutilizable:**
  - `_shared/_plantilla-skill/` — plantilla para que las skills **nuevas** nazcan
    iguales (frontmatter ligero con los dos ejes `rol`/`naturaleza` + módulos).
    Ahorra tiempo real en cada alta.
  - `scripts/validate_skills.py` en **modo AVISO** — se corre a mano, informa de
    no conformidades, **no bloquea** commits. Sin hook, sin CI.

**DIFERIDO a `docs/MEJORAS_FUTURAS.md`** (no construir hasta que los datos lo pidan):

- Charter `_shared/ARQUITECTURA_SKILLS.md`.
- `scripts/new_skill.py` (scaffolder).
- `inventario_skills.json` + `INVENTARIO.md` (termómetro de conformidad).
- `validate_skills.py` en modo **bloqueante** (pre-commit + CI) y la regla blanda
  en `CLAUDE.md`.
- **Retrofit masivo de identidad** (`metadata`+`license`) de las 7 skills (antiguas
  Olas 2-3): se alinean **al tocar cada una**, no en barrido.
- **Generalizar jurisprudencia+cosecha a `_shared/`**: se queda en `oposicion`
  hasta que una 2.ª skill lo necesite.

**Disparador para reabrir lo diferido:** más skills, más manos, o una
inconsistencia que cueste algo real.

**Cierre:** `python scripts/sync_skill_helpers.py` + `python scripts/package_skill.py <skill_dir>`
+ `git commit`/`tag` + re-import en el servidor. Corre la suite (incl.
`test_skill_helpers_sync.py`).

Encaja con el **retrofit diferido** ya decidido (alinear al tocar cada skill),
salvo la **Ola 1**, que conviene ejecutar ya.

### Matriz de conformidad (verificada 2026-06-16)

| Skill | metadata | license | helpers canónicos | bespoke a retirar |
|---|---|---|---|---|
| oposicion-alegacion-nulidad | sí | sí | **NO** | `log_uso.py` → canónico |
| verificacion-anclada-fuente | sí (AGPL) | sí | n/a | — |
| cendoj-descarga | falta | falta | sí | — |
| escritos-judiciales | falta | falta | sí | — |
| preparacion-litigio-civil | falta | falta | sí | — |
| preparacion-audiencia-previa | falta | falta | sí | `log_uso.py` (doble) |
| preparacion-juicio-oral | falta | falta | sí | `log_uso.js` (doble) |
| engel-volkers | falta (`status` suelto, `version` sin comillas) | falta | n/a | — |
| viabilidad-prerelleno | falta (sin `version`) | falta | **NO** | — |

### Reconciliación documental (evitar el tercer doc solapado)

**(Aplica cuando se construya el charter, hoy diferido.)** El charter
**referencia** `MEJORA_CONTINUA_SKILLS.md` (dueño del bucle) y
`EVOLUCION.md` (instancia del módulo). Marcar `despacho-skills/SKILL_AUTHORING.md`
como **superado** por el charter (idealmente, sacar ese repo obsoleto del árbol de
trabajo para que no contamine).

---

## ✅ Cerrados

> Ciclo de vida cerrado. Narrativa completa: `git log` + el spec/plan enlazado.
> Lista plana, reciente primero. Promover a agrupación por área cuando supere ~30
> entradas (lo avisa `session_close`).

- ✅ **[GOBERNANZA-REVISIONES]** Archivo verificable de las revisiones adversariales — el informe del revisor se archiva **literal** entre marcadores con nonce y con su digest canónico verificado al recibirlo; la adjudicación va embebida en el documento revisado con encabezado canónico y ficha; y **G7/G8** lo comprueban recomputando el digest (desigualdad = rojo). Nació de la pregunta «¿hace falta documentar el diálogo Code ↔ Codex?» y pasó por **seis rondas de revisión adversarial sobre sí mismo: 38 hallazgos, 38 confirmados, cero refutados**, que pararon (a) una invariante que habría autorizado modificar un expediente real bajo `data/CASOS/`, (b) una cláusula que promovía doctrina sin revisar y (c) mi propia redefinición de la regla de parada. **Alcance recortado por Nikolai** sobre ese último hallazgo: fuera el predicado de población, los ejes de clasificación, el *fail-closed*, el censo de 28 y el retrofit de los ocho encabezados heredados; el plan de migración queda **archivado sin ejecutar** conservando su censo. **El retrofit dejó de estar fuera el 2026-08-02** (encargo de Nikolai): los 8 heredados y un noveno que nadie había contado pasan al formato, `_ADJ_LEGACY` se retira vacía, el censo se congela e indexa, y el contrato va a **rev. 9** con la frontera acta/handoff dirimida — ver la entrada `[AUDIT-LOG-REVISIONES]`. El censo sigue fuera como artefacto normativo. Spec: `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` (rev. 9) + cinco actas. Doctrina en `CLAUDE.md` y `AGENTS.md`, con el **revisor sustituto** mientras Codex esté sin cupo. Suite 2696 → 2714. **PR #188**.

- ✅ **[MAXPATH-INFORME]** El informe de viabilidad que Excel no abría — el nombre repetía el `case_id` completo dentro de la carpeta que ya se llama `case_id` (269 car. de ruta en `W-02XOR7`), y **el límite no era el sistema de ficheros sino Office** (`LongPathsEnabled=1`, `openpyxl` lo abría). Política nueva: **solo el ID GO** (`Informe viabilidad - <id_go>.xlsx`) + guardarraíl `RUTA_OFFICE_MAX = 240` + `_find_informe_existente` (sin ella `ensure_case` dejaba una plantilla en blanco junto al informe ya trabajado). Mismo fix en el informe **LLM** de `viabilidad-prerelleno` (298 car. en `W-02TH0W`). Migración `core/migrar_nombres_informe.py` + CLI: **14 renombrados en el Drive**, idempotente. Residuo (crudo de E&V intocable a 287, `01_Procesado` hasta 377) en `MEJORAS #100`; el corolario de diagnóstico en `docs/DEAD_ENDS.md`. Suite 2493/0/0. **Tail:** re-empaquetar/re-importar el `.skill` desde la raíz (2026-07-28)
- ✅ **[SIGUIENTE-SALA-HILOS]** Bundle por hilo de correo en la sala de lectura (Slice 1 del re-tajo del spec de emails atomizados) — la correspondencia ocupa **una entrada por hilo**, no una por mensaje, y `INDICE.md` colapsa los bundles a una línea `(+N anexos)` (`CRONOLOGIA.md` intacta). Clave de `agrupar_por_hilo` cambiada a la **descripción** del nombre (la anterior solo unía colisiones del mismo día y asunto) y `layout_bundle_hilo` con **nombres como función pura del fichero de origen**, tras una revisión final que encontró tres caminos de pérdida/sobrescritura de documentos ya copiados. Skill **v1.14**, suite 2366/0/0. **PR #131** (`d27172b`). Spec `2026-07-23-emails-atomizados-sala-lectura-design.md` + plan `2026-07-26-sala-lectura-bundle-por-hilo.md`. Slices 2 y 3 sin promover: `MEJORAS #86`/`#87`; threading RFC en `#88`. **Tail:** re-importar el `.skill` en Cowork.
- ✅ **[GOBERNANZA-DOCUMENTAL]** Revisión adversarial del diagnóstico de INDICE/PLAN/specs + remediación — 4 de los 5 hallazgos REFUTADOS (el test de `INDICE.md` DESCARTADO: asertaba un contrato que nunca existió); el hueco real estaba en el **ledger**, no en el índice. Ejecutado en tres PR: **#127** (`7c20442`, D1/D2/D6b — el atlas ya no ordena el comando que lo mutila, guarda anti-clobber, tres estados de Fase B, frontmatter generado), **#128** (`4f4bc39`, ledger `[CRM-ATLAS]` + `[PLUGIN-FEESDEFENDER]`, higiene de punteros H2/H4/D3/D4/D5/D6a y guards G1-G3) y **#129** (aviso `_avisar_specs_sin_traza` en `session_close`). Informe: **PR #126** (`4bc8dc2`) · [informe](docs/superpowers/specs/2026-07-26-gobernanza-indice-adversarial-review.md) (2026-07-26)
- ✅ **[SIGUIENTE-PRECLASIFICACION-SALA-LECTURA]** Robustez/velocidad de `organizar-sala-lectura` — 16/16 ítems del backlog fable-5: `preclasificar.py` (gate determinista), `copiar_manifiesto_rclone.py` (rcd + reanudación), `verificar_sala.py`+`manifiesto_parser.py`, columnas `categoria`/`subcategoria_crm`; v1.12 — PR #116 (8 ALTA) + PR #121 (8 MEDIA/BAJA) · [plan](docs/superpowers/plans/2026-07-21-preclasificacion-sala-lectura.md) (2026-07-23)
- ✅ **[SPLIT-SALA-MAQUINA]** Split de bundles multi-documento en la Sala de máquina — F1 (cerebro `core/split_documental.py`, PR #45 `6dba396`) + F2 (integración en `sala_maquina`/CLI, Tareas 12-15 + 13B, PR #109 `cc13355`): split entre OCR y MD, cobertura y estado por documento lógico, manifiesto editable + `--force`, passthrough robusto; skill `organizar-sala-maquina` v1.3; follow-ons `MEJORAS #78/#79` · [plan](docs/superpowers/plans/2026-07-14-split-sala-maquina.md) (2026-07-21)
- ✅ **[CRM-ATLAS]** Atlas del CRM sudespacho (SSOT de la superficie) — Fase A (inventario de endpoints del OpenAPI) + Fase B (esquema por elemento: campos, relaciones, enums) + Grupo 3.2, con gate anti-PII y digest de deriva; `core/crm_atlas.py` + `scripts/crm_atlas.py` + `docs/CRM_SUDESPACHO_ATLAS.md`. Regenerar SIEMPRE con `--phase all`. **PR #104 (`b2d624c`)**; el `87ff113` que cita el spec es un commit colgante pre-squash, no está en `main`. Remediación posterior de D1/D2/D6b en PR #127 (`7c20442`) · [spec](docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md) (2026-07-20)
- ✅ **[SIGUIENTE-RESIDUO-LLM]** Clasificador LLM del residuo de intake (`MEJORAS #37`) — `preparar_residuo`/`rellenar_worklist`/`clasificar_residuo_llm` (chat_fn inyectable) + CLI `scripts/sala_lectura.py`; +9 tests; commit `742e35a` (triaje 2026-07-19)
- ✅ **[SIGUIENTE-INTAKE-JUDICIAL-AUTO]** Intake automático de demanda/contestación desde el CRM — 5 fases ✅, validado e2e real (incluye el Paso 1 del intake CRM-completo) (triaje 2026-07-19)
- ✅ **[SIGUIENTE-INPUT-LOTES]** Layout de `00_Input` por lotes de entrega (`MEJORAS #54`) — build MERGEADO PR #57 (`8142d97`); la cola operativa (re-import Cowork + migración `migrar_layout_intake` bajo demanda) queda como tail no-bloqueante · [spec](docs/superpowers/specs/2026-07-17-layout-00-input-lotes-design.md) (triaje 2026-07-19)
- ✅ **[SIGUIENTE-MCP-DRIVE-DISCO]** MCP "Drive como disco" (`expedientes-xl` G:+H:) V1 — construido PR #52, **DESPLEGADO 2026-07-19** vía extensión `.dxt` (PR #83); funciona en vivo en Cowork/Desktop (G: rw, H: ro, poda Tier 0, 19 tools). Hallazgo: `claude_desktop_config.json` NO llega a Cowork (solo `.dxt`). 3 bugs de arranque bajo Claude Desktop: imports `python -m` (PR #80), stub Python WindowsApps (PR #82), duplicado config.json↔.dxt. Pasos 5-7 + bundle Code diferidos (ver `[SIGUIENTE-MCP-DRIVE-DISCO-PASOS-5-7]`) · [spec](docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md)
- ✅ **[SIGUIENTE-APERTURA-EXPEDIENTE]** Builds de apertura B1-B5 (ficha CRM end-to-end, `--case-id` incremental, normalizador de teléfono, evento `archivado`, auto-derivar `--folder-id`) — PR #69/#71/#72/#74 · [spec](docs/superpowers/specs/2026-07-18-apertura-expediente-b1-b5-design.md)
- ✅ **[SIGUIENTE-SKILL-EXPEDIENTE-A-MD]** Skill `organizar-sala-maquina` (ex `expediente-a-md`) — rama `feat/organizar-sala-maquina` (sin hash de squash registrado) · [spec](docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md)
- ✅ **[SIGUIENTE-CONTROLES-ANTIFUGA]** Controles de `SEGURIDAD_DATOS.md` implementados — commits `51ecf24`/`48c790f`/`e1ff182`/`a79ba90` · doctrina `docs/SEGURIDAD_DATOS.md`
- ✅ **[BIBLIOTECA-CHECKOUT]** Biblioteca de casos (checkout/checkin Desktop↔Drive) — PR #4 (`061d99e`) + PR #5 (`b67f46d`) + PR #6 (`8dd138c`) + PR #7 (`16cbb54`)
- ✅ **[SANEADO-PII-FASE-2]** Historial git reescrito + repo GitHub recreado (scrub total) — nuevo `main` `a40b27f`
- ✅ **[SKILL-CONTESTACION-ART20-LAU]** Skill `contestacion-honorarios-art20-lau` integrada en el repo — 2026-07-03, sin PR/hash registrado en el bloque
- ✅ **[SIGUIENTE-EMAIL-APLANADO-ANIDADOS]** Aplanado byte-fiel de emails anidados en el export de etiquetas — commits `c492b70`+`911bf39`+`5cbb6eb` · [plan](docs/superpowers/plans/PLAN_email_aplanado_anidados.md)
- ✅ **[SIGUIENTE-EXPORT-ETIQUETA-EMAIL]** Exportar etiqueta Gmail → expediente (motor + Streamlit + CLI + skill) — commits `5088e27`+`b58497f`
- ✅ **[PLUGIN-FEESDEFENDER]** Plugin FeesDefender / conector `expedientes-xl` — tres planes del 2026-06-22 ejecutados como una sola pieza: conector de expedientes, trazabilidad de la skill de intake y empaquetado del plugin. **Sin nº de PR: es trabajo anterior a la protección de rama (2026-07-07)**; narrado en `docs/bitacora/2026.md:175` y vivo en `docs/ARQUITECTURA_RELACIONES.md:19,52-65` (SSOT de build) · planes [expedientes-xl-conector](docs/superpowers/plans/2026-06-22-expedientes-xl-conector.md) · [intake-skill-trazabilidad](docs/superpowers/plans/2026-06-22-intake-skill-trazabilidad.md) · [empaquetado-plugin-feesdefender](docs/superpowers/plans/2026-06-22-empaquetado-plugin-feesdefender.md) (2026-06-22)
- ✅ **[INTAKE-WHATSAPP-FASE-A]** Intake de chats de WhatsApp — Fase A (UI Streamlit) — commits `3734dcb`→`cf26b2a` · [spec](docs/superpowers/specs/2026-06-15-intake-whatsapp-design.md)
- ✅ **[ESTILO-DE-LA-CASA]** Infraestructura de escritura del despacho (claridad + persuasión + no-IA) — 2026-06-17, sin hash registrado · plano `PLANO_Code_skill_estilo_casa.md`
- ✅ **[CRITICO-PRESIGNED-DOWNLOAD-BUG]** Descarga del Gestor Documental (bug presigned URL) — RESUELTO 2026-06-10, sin hash registrado · detalle `docs/DEAD_ENDS.md`
- ✅ **[IDEA-GOBERNANZA-DOCS]** Malla de referencias cruzadas + regla de promoción backlog→`PLAN.md` — RESUELTO 2026-06-10, sin hash registrado
