---
tipo: revision-adversarial
objeto: "diseño del Plan 3B: los once derivados y las puertas laterales"
objeto_rev: "rama claude/feesdefender-plan3-decision-batches-844080, commit d1b09e2"
commit: d1b09e2
ronda: "18"
revisor: Codex
veredicto: NO-EJECUTABLE
marcador_nonce: v7kt
sha256_informe: 4a5415ba5520738de332a56f501e6f66361c0ffb84cc632686be6a7ebe173fa2
adjudicado_en: docs/superpowers/plans/2026-08-26-apertura-v1-plan3b-derivados.md §6
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R18.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicación** vive en el **§6 del plan**
> (`docs/superpowers/plans/2026-08-26-apertura-v1-plan3b-derivados.md`). Es la ronda de **DISEÑO**: se corrió **antes de escribir
> una línea de código**, que es para lo que existe.
>
> Veredicto `NO-EJECUTABLE`: **15 hallazgos** — 4 CRÍTICOS, 5 ALTOS, 5 MEDIOS, 1 BAJO. Adjudicados: **15 confirmados,
> 0 refutados.**
>
> **Esta ronda EJECUTÓ.** El revisor corrió 222 tests dirigidos (219 pasados, 3 `slow` omitidos), cinco sondas propias y censos de llamadores por AST, y midió el comportamiento en vez de
> deducirlo. Los críticos salieron de las sondas.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:v7kt -->

NO-EJECUTABLE

## Resumen

Se contrastaron el Plan 3B completo, la matriz y la costura de 3A, la adjudicación R15, la tabla canónica del §25 y los productores/consumidores de las once filas.
Se ejecutó todo sobre `objeto_copia/`: 222 pruebas dirigidas (219 pasaron, 3 `slow` omitidas), cinco sondas propias y censos de llamadores; `pytest-randomly` no estaba instalado.
Las tres puertas que el plan enumera sí escriben hoy sobre el canon prestado, y los tres subcomandos de `sala_maquina` sí rechazan con código 2 sin cambiar bytes.
El bloqueante principal es anterior a cualquier detalle de migración: `deposito(ref, …)` relocaliza siempre en el catálogo canónico y no puede conservar `CaseWorkspace.working_root`; la pieza E resuelve una copia y la F la pierde.
Además, #21 nunca activa el nuevo rechazo por ser `protocolo`, #26 es RMW aunque figura P, y las capacidades propuestas se solapan de modo que una capacidad P/L puede escribir una salida A.
La pieza H evita un conflicto descartando `_tiempos.jsonl` del checkin, y la pieza G no define un conteo de población computable ni conserva el contrato actual de lectores de `corpus.jsonl`.
Las diecisiete fronteras no cubren esos fallos y uno de sus mutantes ya mata varias pruebas preexistentes por razones ajenas a la frontera anunciada.

## Hallazgos

### H18-01 — CRÍTICO — La costura pierde la copia que la pieza E acaba de resolver

**Qué afirma el plan.** «Las tres puertas laterales resuelven workspace» y «los cuatro motores […] reciben el `Deposito`» (`plan 3B:196-214`).

**Por qué está mal.** `CaseWorkspace` conserva la raíz efectiva en `working_root` (`core/casos/workspace_model.py:465-505`), pero la firma propuesta mantiene `deposito(ref, …)` (`plan 3B:180-182`). La costura vigente recibe solo ese `CaseRef` y `_identidad()` ejecuta `CaseCatalog().localizar(ref)` (`core/casos/escritura.py:119-132`); el propio catálogo declara que solo localiza el canon y que no decide la copia de trabajo (`core/casos/case_catalog.py:1-15,51-78`). La sonda `test_sonda_deposito_ref_no_conserva_working_root` construyó canon prestado y checkout separado: el depósito escribió `Sonda checkout - (W-R1804)/01_Procesado/marca.txt` bajo `CASOS_ROOT`; el checkout quedó intacto.

**Consecuencia práctica.** La herramienta diaria, que opera en `local_checkout`/`local_scratch`, dejaría de escribir en `ws.working_root`: según clase, escribiría o desviaría contra el canon, o rechazaría mirando el estado del canon. Las piezas E y F no se pueden ejecutar juntas con las interfaces que el plan fija.

### H18-02 — CRÍTICO — `agregado=True` no puede rechazar la fila #21

**Qué afirma el plan.** «Cuando el guard desviaría, la costura lanza `AgregadoNoDesviable`» y así el rechazo «deja de depender de que el entrypoint se acuerde» (`plan 3B:165-186`). La tabla clasifica #21 como A y su depósito como `protocolo` (`plan 3B:158,231`).

**Por qué está mal.** La costura llama `guard_escritura(..., es_protocolo=(clase == "protocolo"))` (`core/casos/escritura.py:208-213`). `decidir_escritura` retorna siempre `desviar=False` para protocolo, aun con estado prestado (`core/repository_checkout.py:541-576`). El contrato C4 ya lo fija y su test lo verifica literalmente: «Exento del desvío: escribe en la ruta viva aunque el caso esté prestado» (`tests/test_escritura_costura.py:197-219`); ese test pasó en la corrida R18.

**Consecuencia práctica.** `_sala_maquina_state.json`, que el propio plan considera RMW no desviable, obtiene un depósito canónico y nunca dispara `AgregadoNoDesviable`. La propiedad continúa dependiendo exclusivamente del entrypoint y C8 queda falsa.

### H18-03 — CRÍTICO — La fila #26 es A, no P

**Qué afirma el plan.** P incluye «#14, #15, #24, #26» y #26 es «función pura de su entrada» desviable (`plan 3B:155-160,235`).

**Por qué está mal.** En la ruta de producción, `core/sala_maquina.py:874-888` carga el manifiesto previo y, con `--force`, llama `reconciliar_manifiesto(previo, propuesto)` antes de reescribirlo. La reconciliación hereda `doc_id`, avanza `next_doc_id` y acumula tombstones desde el manifiesto anterior (`core/split_documental.py:450-507`); ambos espejos se sobrescriben (`:301-320`). La sonda R18 ejecutó dos corridas con la misma foto viva: la primera dejó rangos `1-3,5-9`; la segunda volvió a leer la foto viva y reemplazó la bandeja por `[(d01,1-3),(d02,11-12)]`, perdiendo `5-9` y reutilizando `d02`.

**Consecuencia práctica.** Desviar #26 pierde identidades/tombstones de la primera corrida exactamente por el mecanismo C5. La categoría A no es exhaustiva y ninguna frontera G1-G17 cubre esta fila.

### H18-04 — CRÍTICO — Los doce depósitos no hacen exigible la familia que dicen representar

**Qué afirma el plan.** «Uno por familia, no uno por motor» evita que una escritura herede la exención de otra (`plan 3B:213-240`), con G8 como frontera (`:287`).

**Por qué está mal.** `Deposito` autoriza cualquier relativa contenida bajo `_base`; no conserva una lista de ficheros/familia ni el futuro atributo `agregado` (`core/casos/escritura.py:52-115`). Las bases del propio plan se solapan exactamente: `01_Procesado/Emails` sirve a #16 G y #17 A; `…/Emails/adjuntos` a #15 P y #19 A; `…/02_Sala de máquina` a #21 A, #22 L y #24 P (`plan 3B:224-236`). Por tanto, el motor puede escribir `_registro.json` con el depósito G, `_contenido_estado.json` con el P o `_sala_maquina_state.json` con el L, todos dentro de la contención válida. G8 solo muta «un depósito único de clase protocolo» y no observa el cruce entre capacidades distintas con la misma base.

**Consecuencia práctica.** El rechazo A y el aserto append-only se pueden eludir sin escapar del depósito y sin violar ningún tipo o path. La costura no cierra la propiedad que justifica la pieza F.

### H18-05 — ALTO — Las cuatro respuestas por categoría no son alcanzables en los motores monolíticos

**Qué afirma el plan.** P se desvía, A rechaza, G se desvía declarando población y L escribe en el árbol vivo (`plan 3B:155-169`); el E2E prueba cada categoría en canon y bandeja (`:365-370`).

**Por qué está mal.** Una sola llamada a `atomize_dir` produce #14-#17 (`core/email_atomize/pipeline.py:86-90,130-272`), mezclando P, G y A. Una sola corrida `apply` produce #21-#24, #26 y #27 (`scripts/sala_maquina.py:742-853` y `core/sala_maquina.py:874-934`), mezclando A, L y P. Si el entrypoint obtiene todos los depósitos antes del motor, el primer A rechaza y P/G/L nunca ejecutan su respuesta. Si se obtienen durante la corrida, el rechazo puede llegar después de escrituras de otras categorías. El plan no fija orden de adquisición, atomicidad ni frontera para ninguno de los dos resultados.

**Consecuencia práctica.** Un E2E por depósito puede quedar verde aunque ninguna invocación real produzca la matriz prometida; en producción habrá rechazo total o publicación parcial según un orden no diseñado.

### H18-06 — ALTO — «Tres puertas» no es el censo de la superficie que el propio plan adopta

**Qué afirma el plan.** «Hay tres puertas más» que llegan «a cinco» filas (`plan 3B:45-60`).

**Por qué está mal.** Las tres enumeradas son reales, pero el plan cuenta como puerta una API pública sin llamador externo (`aplicar_resumenes`) y omite las APIs públicas equivalentes `atomize_case(case_id)` (`core/email_atomize/pipeline.py:441-442`) y `procesar_caso(case_id)` (`core/adjuntos_contenido/pipeline.py:11-13`). También quedan `atomize_dir`, `procesar_dir`, `aplicar_resumenes_dir` y `split_documental.escribir_manifiesto` con `Path` desnudo; el CLI conserva `--src --out` (`scripts/atomize_emails.py:28-30`). Su rama `--entrega` añade después otra escritura, `_entregas`, mediante `sellar_entrega` (`scripts/atomize_emails.py:54-56`; `core/email_atomize/entregas.py:45-69`), fuera de las once filas, depósitos y fronteras. Streamlit no añade una puerta: solo imprime el comando (`streamlit_app.py:1129-1147`).

**Evidencia ejecutada.** Las sondas sobre canon prestado produjeron 14 rutas nuevas con `--ref` y `_contenido_estado.json` tanto desde `__main__` como desde `aplicar_resumenes`, siempre sin `_pendiente_checkin`.

**Consecuencia práctica.** El censo y G17 pueden bajar mientras siguen existiendo contratos públicos que escriben el mismo write-set sin resolución, mutex ni guard. La cifra «tres/cinco» no sirve como criterio de cierre.

### H18-07 — ALTO — La pieza H evita el merge perdiendo `_tiempos.jsonl`

**Qué afirma el plan.** «`_tiempos.jsonl` entra en `MERGE_EXCLUSIONS`» para darle «un solo hogar» (`plan 3B:259-271`).

**Por qué está mal.** `_tiempos.jsonl` se escribe en el `case_dir` efectivo de la corrida (`scripts/sala_maquina.py:131-145,742-746,846`), por tanto también en un checkout local. `MERGE_EXCLUSIONS` alimenta los `--exclude` del checkout/sync (`scripts/repository_cli.py:223-228,594-603`), `plan_merge` omite esas rutas (`core/repository_checkout.py:245-266,292-303`) y el checkin solo sube lo que queda en ese plan (`scripts/repository_cli.py:744-759`). No existe para tiempos el protocolo especial pull→append→push que sí existe para `_intake_log.jsonl` (`:1063-1109`). Además, modificar solo `core/config.py` deja roja `tests/test_expedientes_xl_tiers.py:28-31`, que exige espejar todo basename excluido en `plugins/expedientes_xl/tiers.py:31-32`; ese fichero no figura en File Structure.

**Consecuencia práctica.** La telemetría generada durante el préstamo queda solo en la copia y desaparece del expediente canónico al checkin. El conflicto se evita descartando el artefacto, no dándole un hogar único.

### H18-08 — ALTO — El depósito de #27 no cubre al escritor real

**Qué afirma el plan.** La fila #27 recibe un depósito `00_Input`, clase protocolo L (`plan 3B:236`), y los motores pasan a recibir capacidades (`:211-220`).

**Por qué está mal.** `append_event` no acepta `Deposito`: acepta `CaseWorkspace`, `Path` o `case_id` (`core/intake_log.py:172-220`). El evento `split_documental` de la ruta de producción llama todavía con `case_id` (`core/sala_maquina.py:925-934`), y esa variante vuelve a localizar por catálogo (`core/intake_log.py:194-196`), es decir, el canon. Ni `core/intake_log.py` aparece en File Structure ni G13 comprueba que el evento use el depósito enumerado.

**Consecuencia práctica.** En un checkout, documentos y evento pueden quedar en árboles distintos; la fila #27 permanece fuera de la migración aunque la tabla la cuente entre los doce depósitos.

### H18-09 — ALTO — La población de G no tiene una magnitud computable definida

**Qué afirma el plan.** Cada agregado declara, por ejemplo, «47 mensajes de `00_Input`; 12 en `_pendiente_checkin/`» y G12 verifica «el conteo real» (`plan 3B:242-257,291`).

**Por qué está mal.** El productor actual enumera solo lotes `email` y `03_Email` bajo `00_Input` (`core/email_atomize/pipeline.py:393-410`). `contar_eml` cuenta ficheros `.eml`, no mensajes (`:418-427`); después el motor desciende mensajes embebidos, colapsa duplicados y puede producir varias filas lógicas (`:115-159`). Contar `.eml` en la bandeja no da «mensajes fuera», y procesarlos para conocer el número introduce la deduplicación cruzada que el propio plan deja «SIN VERIFICAR» (`plan 3B:406-407`). G11/G12 no fijan identidad, deduplicación, origen admisible ni qué significa el denominador.

**Consecuencia práctica.** Dos implementaciones incompatibles pueden pasar las fronteras mostrando cifras distintas; el agregado seguirá teniendo apariencia de cobertura completa sin una población reconciliable.

### H18-10 — MEDIO — La nueva línea de `corpus.jsonl` no tiene el lector que el plan afirma

**Qué afirma el plan.** «`corpus.jsonl` […] primera línea de metadatos (`{"_poblacion": {...}}`), y el lector la salta por la clave» (`plan 3B:255-257`).

**Por qué está mal.** El fichero ya tiene una primera línea meta `_README`/`_tipo` (`core/email_atomize/corpus.py:8-13,49-53`). El lector real del repo solo salta `_README` o `_tipo == "corpus"` (`scripts/audit_correos_no_separados.py:83-91`), y `tests/test_email_atomize_pipeline_b.py:262-266` filtra solo líneas que empiezan por `{"_README"`; `tests/test_email_atomize_pipeline.py:46-48` fija exactamente una línea meta. Una línea separada `{"_poblacion":…}` se cuenta como atom; reemplazar la actual tampoco se salta. El plan no enumera esos consumidores ni define que `_poblacion` se añada al objeto meta ya existente.

**Consecuencia práctica.** El auditor aumenta falsamente el número de atoms y los consumidores reciben un registro sin schema de mensaje; la tarea puede romper la suite o, peor, sesgar conteos sin lanzar.

### H18-11 — MEDIO — La pieza E no puede ser a la vez extracción pura y core silencioso

**Qué afirma el plan.** `_resolver_workspace` se extrae a `core/casos/puerta.py` «sin cambiarla» y los tests verdes prueban equivalencia (`plan 3B:196-206,318-325,348-352`), mientras «Core no imprime» (`:309`).

**Por qué está mal.** La función actual contiene presentación Typer: `typer.echo`, `typer.Exit` y códigos 1/2 (`scripts/sala_maquina.py:363-452`). Depende además de `_arg_o_none`, `_identidad_actor`, `_registro_de_workspaces`, `_drive_accesible`, `_workspace_legacy`, `_wcode_o_none`, del binding `case_locator` y de la precedencia catálogo→registro→legacy (`:274-452`). Moverla sin cambio introduce impresión/CLI en core; separar presentación, helpers o precedencias deja de ser la extracción pura que Task 3 ordena. Los tests de un solo frontal no prueban que los otros tres mantengan códigos, stdout/stderr y fallbacks.

**Consecuencia práctica.** Las restricciones del propio plan son simultáneamente incompatibles y la equivalencia reclamada no tiene frontera observable para tres de las cuatro puertas.

### H18-12 — MEDIO — G16 contradice el contrato que dice conservar

**Qué afirma el plan.** «`--case-dir` sigue siendo vía legítima y no bypass del mutex» (`plan 3B:295`), conservando su contrato actual (`:208-209`).

**Por qué está mal.** `_workspace_legacy` admite `LOCAL_SCRATCH` con W-code nulo (`scripts/sala_maquina.py:328-349`). `_bajo_mutex` detecta ese caso, imprime aviso y hace `yield` sin adquirir nada (`:455-484`). Su docstring declara que es deliberado en modo `libre`, la herramienta diaria (`:464-469`). Por tanto, «conservar» y «no bypass» no describen el mismo comportamiento.

**Consecuencia práctica.** G16 no puede fijar simultáneamente la compatibilidad legacy y la garantía de mutex; una prueba verde tendrá que escoger una y dejar falsa la otra.

### H18-13 — MEDIO — El rechazo de D ocurre después de una escritura del guard

**Qué afirma el plan.** La escritura misma rechaza cuando el guard desviaría, conservando mutex antes de guard (`plan 3B:175-194`).

**Por qué está mal.** La única información `decision.desviar` aparece después de llamar `guard_escritura` (`core/casos/escritura.py:208-213`). Ese guard, cuando desvía, ejecuta `append_event` antes de retornar (`core/case_manager.py:888-893`). El plan no cambia `emitir_evento`, no diseña rollback y G1 solo comprueba que lance. En modo `libre`, C1 además permite llegar al guard sin mutex (`core/casos/escritura.py:186-211`; `tests/test_escritura_costura.py:123-139`).

**Consecuencia práctica.** Una API que dependa de la supuesta garantía de la costura recibe una excepción después de que `_intake_log.jsonl` ya cambió; «rechazo» no equivale a cero efectos y puede dejar el evento fuera de mutex en el modo diario.

### H18-14 — MEDIO — Las diecisiete fronteras no corresponden uno-a-uno a sus mutantes

**Qué afirma el plan.** «Diecisiete fronteras, diecisiete mutantes» y si un mutante mata más pruebas «está mal apuntado» (`plan 3B:276-300`).

**Por qué está mal.** No hay frontera para conservar `working_root` (H18-01), para #21 protocolo+A (H18-02), para #26 RMW (H18-03), para capacidades solapadas (H18-04), para la atomicidad entre categorías (H18-05), para supervivencia de tiempos al checkin (H18-07), para el escritor real de #27 (H18-08), ni para el schema/semántica de población (H18-09/10). A la vez, el mutante G10 «devolver `[]` desde `_cobertura_previa`» afecta directamente pruebas existentes en `test_sala_maquina_acotar.py`, `test_sala_maquina_cobertura_legacy.py` y `test_sala_maquina_ejecutar.py`, no solo su nueva frontera. G14, al tocar `MERGE_EXCLUSIONS`, también interactúa con el espejo exigido por `test_expedientes_xl_tiers.py:28-31`.

**Consecuencia práctica.** El arnés puede declarar una propiedad cerrada sin tocar sus defectos reales y puede rechazar mutantes por tests que ejercen contratos distintos; el criterio 6 de salida no es ejecutable como está redactado.

### H18-15 — BAJO — Hay afirmaciones literales y cifras de superficie inexactas

**Qué afirma el plan.** `emails_out_dir(case_id) → caso_path` (`plan 3B:50-52`), «las filas #21-#24, #26 y #27 llegan solo» por `sala_maquina` (`:40-43`) y el §3 se titula «tres categorías» (`:150`).

**Por qué está mal.** `emails_out_dir` usa `path_for(resolve_ref(case_id))`, no `caso_path` (`core/email_atomize/pipeline.py:430-442`). #24 tiene la API pública `core.sala_maquina.ejecutar(case_dir, …)` (`core/sala_maquina.py:1086-1110`), #26 expone `escribir_manifiesto`/`materializar` (`core/split_documental.py:301-320,528`), y #27 expone `append_event`; que no tengan otro llamador de producción dentro del archive no los convierte en una única puerta según el criterio aplicado a `aplicar_resumenes`. Finalmente la tabla tiene cuatro categorías P/A/G/L y el propio texto lo corrige doce líneas después (`plan 3B:155-163`).

**Consecuencia práctica.** Los censos y mutantes parten de nombres distintos para «puerta» y «categoría»; una bajada numérica no demuestra cierre de la propiedad.

## Lo que verifiqué y resultó CORRECTO

- El objeto conserva las once filas de 3A: #14, #15, #16, #17, #19, #21, #22, #23, #24, #26 y #27; el reparto del §25 es 7 derivado + 4 protocolo (`spec §25:1775-1788`; `3A:113-120`).
- El recuento formal de §4-F es doce depósitos para once filas: #23 necesita las bases de `_cobertura.json` y `_revisar/_cobertura.md`. Las bases y clases enumeradas coinciden con las ubicaciones y clases del §25; el defecto es su solape/capacidad, no la suma.
- #17, #19, #21 y #23 sí leen estado anterior: registro (`email_atomize/pipeline.py:130,272`), caché de adjuntos (`adjuntos_contenido/pipeline.py:48-50,104,118`), estado/intentos/hashes (`scripts/sala_maquina.py:71-101,817-831`) y cobertura previa (`:775-804,880-917`).
- La cita «169 filas → 2» existe en el docstring de `_cobertura_previa` (`scripts/sala_maquina.py:148-156`).
- `_tiempos.jsonl` es append-only (`scripts/sala_maquina.py:131-145`), no está hoy en `MERGE_EXCLUSIONS` (`core/config.py:391-399`) y CP10 mueve/renombra colisiones sin concatenar (`scripts/repository_cli.py:951-992`).
- Las tres rutas laterales enumeradas carecen hoy de resolución de workspace, mutex y guard. Las tres sondas escribieron en el canon prestado.
- Los tres comandos `plan`, `apply` y `reforzar` llaman `_resolver_workspace`, sostienen `_bajo_mutex` cuando hay W-code y exigen capacidades antes del motor (`scripts/sala_maquina.py:651-667,722-750,862-879`). `tests/test_sala_maquina_workspace.py` pasó completo: código 2 y huella byte-idéntica sobre préstamo ajeno.
- El orden vigente de la costura es mutex antes de guard (`core/casos/escritura.py:184-213`), coherente con 3A/R14; H18-13 no refuta ese orden, refuta que el rechazo posterior sea libre de efectos.
- Streamlit no añade un llamador oculto de estos motores: presenta instrucciones/comandos, no los importa ni lanza (`streamlit_app.py:1129-1147`).
- Ejecución: subconjunto de 222 tests, 219 PASS y 3 SKIP marcados `slow`; la sonda adicional de #26 pasó. La primera tentativa con `-p randomly` no recogió tests por ausencia del módulo `randomly`.

## Lo que NO pude verificar

- **SIN VERIFICAR:** suite completa y repetición con semillas 777/31337; `pytest-randomly` no está instalado en el intérprete indicado. No se interpreta como cobertura refutada.
- **SIN VERIFICAR:** los tres tests `slow` de `test_split_sala_maquina_e2e.py`; fueron omitidos por la configuración del repo.
- **SIN VERIFICAR:** ejecución contra un Drive/registro de workspaces real y coste temporal del escaneo de catálogo; la revisión usó montajes aislados bajo `objeto_copia/`.
- **SIN VERIFICAR:** un arnés de mutación binaria G1-G17, porque el objeto es un plan y esos mutantes/tests todavía no existen. Se verificó estáticamente su radio contra tests actuales.
- **SIN VERIFICAR:** consumidores externos al archive de `corpus.jsonl`; los consumidores internos bastan para refutar «el lector la salta», pero no censan integraciones fuera del repo.
- **SIN VERIFICAR:** reacción a un salto NTP real y las seis remediaciones transitivas de R13; no afectan los bloqueantes anteriores.

## SHA-256 del documento revisado

- Al abrir: `16EEAC4436A36E5DDC3826E71C8A4536166B56C1B409B501D2B5C07C1B36E8A5`
- Al cerrar: `16EEAC4436A36E5DDC3826E71C8A4536166B56C1B409B501D2B5C07C1B36E8A5`

<!-- informe-literal:fin:v7kt -->

## 2. Evidencia verificada por el adjudicador

**Contra la fuente, no contra el informe.** Lo que el adjudicador comprobó por su cuenta antes de
aceptar los críticos:

1. **H18-01** — `deposito(ref, …)` no puede transportar `CaseWorkspace.working_root`: la sonda construyó canon prestado + checkout separado y el depósito escribió bajo `CASOS_ROOT`, dejando el checkout intacto. Las piezas E y F son **incompatibles entre sí**.
2. **H18-02** — `agregado=True` no puede rechazar la fila #21: `decidir_escritura` devuelve `desviar=False` **siempre** para `protocolo`. **Verificado en la fuente** por el adjudicador (`core/repository_checkout.py:541-576`).
3. **H18-03** — la fila #26 es read-modify-write, no función pura: `core/sala_maquina.py:883` llama a `reconciliar_manifiesto(previo, propuesto)`. Dos corridas sobre la misma foto viva perdieron los rangos `5-9` y reutilizaron `d02`.
4. **H18-04** — las bases de los doce depósitos se solapan entre categorías, así que un motor puede escribir el artefacto de una con el depósito de otra sin salir de la contención.

**Lo que el revisor verificó y resultó CORRECTO**, y que coincide con lo que el plan ya había
medido:

- las tres puertas laterales **sí** escriben hoy sobre el canon de un caso prestado — coincide con la medición del §1.1 del plan;
- los tres subcomandos de `sala_maquina` **sí** rechazan con código 2 sin cambiar bytes;
- desviar un agregado read-modify-write **sí** lo rompe, demostrado sobre una fila que el plan había clasificado mal.

**Lo que el revisor NO pudo verificar, y se declara como tal** (no como refutado): su intérprete no
tiene `pytest-randomly`, así que **la suite con las dos semillas (777 y 31337) queda SIN VERIFICAR
por su parte**; cinco módulos MCP no coleccionan por una dependencia ausente de su entorno; y sin
`.git` no puede acreditar la genealogía del archive, solo su contenido y su hash.

## 3. Cadena del acta

- `marcador_nonce: v7kt`, un par de marcadores en orden, el nonce no aparece fuera de ellos
  salvo en el frontmatter y en esta línea.
- `sha256_informe` recomputado al archivar sobre el bloque literal canonicalizado:
  `4a5415ba5520738de332a56f501e6f66361c0ffb84cc632686be6a7ebe173fa2`.
- **Objeto no mutado:** el revisor operó sobre un `git archive` sin `.git` y reportó el `sha256` del
  documento revisado **al abrir y al cerrar**, coincidentes. Ésa es la prueba de no-mutación que
  sustituye al `git status` limpio.
- **Aviso de método, de esta sesión:** al calcular el digest de la R20 obtuve un valor y dos minutos
  después otro — el revisor **seguía escribiendo**. La presencia de `INFORME.md` no es la señal de
  fin; lo es la salida del proceso. Un digest solo significa algo sobre un fichero terminado.
