---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
objeto_rev: "2"
commit: f087edadbe803df8a738397b8697cdfccb1d52c4
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: nqwp
sha256_informe: fa1c5129fa76abfde991406140be4fa415ccb4b3ba905a2e1b7d4dcb3d68df17
adjudicado_en: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md §19
adjudicador: Codex (sustitución excepcional por indisponibilidad de Claude Code)
independencia_adjudicacion: debilitada-misma-familia
---

> **Acta de revisión adversarial R2.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el §19 del objeto, no aquí.
>
> **Adjudicación excepcional:** adjudica Codex por decisión expresa de Nikolai ante la
> indisponibilidad de Claude Code. Revisor y adjudicador pertenecen al mismo modelo/familia;
> la independencia es más débil y puede compartir puntos ciegos. La ronda conserva NO-SHIP
> y la rev. 3 queda pendiente de R3.

## 0. Mandato (literal, tal como se entregó)

MANDATO R2, NUMERADO POR DAÑO
1. Reproduce y ataca uno por uno los remedios de H-01…H-09. Determina si cada remedio es implementable, suficiente, observable y coherente con el código real; busca especialmente remedios que solo cambien el nombre del riesgo.
2. Busca nuevas rutas de pérdida, sobrescritura, duplicación, contaminación, fuga PII/secretos, falsa custodia o efectos externos declarados completos sin readback, incluidas carreras entre staging/commit, recuperación tras crash, revisiones humanas posteriores y actualización CRM→YAML→_caso.md.
3. Ataca el modelo de estado/generaciones/punto fijo: enums, transiciones, invalidación, CAS, candidate_revision, resultados desconocidos, consultas negativas reales y posibilidad de quedar verde sobre entradas obsoletas.
4. Contrasta fronteras y contratos: Gmail, Drive E&V, Sudespacho, LeadHub/FeesDefender-crm, sala de máquina, sala de lectura, viabilidad y rama judicial. Verifica que la spec no prometa capacidades inexistentes ni contradiga contratos anteriores no derogados.
5. Revisa los 50 criterios de aceptación y la estrategia de entrega: cada criterio debe ser demostrable por test o evidencia concreta, no contradecir otro, y el orden no puede exigir infraestructura todavía inexistente ni permitir éxito parcial disfrazado.
6. Decide si la rev.2 está lista para plan TDD (SHIP / NO SHIP). Distingue defectos bloqueantes de riesgos deliberados/limitaciones bien bloqueadas. No diseñes un motor mayor ni amplíes el encargo.

CONTRATO ESTRICTO
- Solo lectura sobre este repo, su Git/index/HEAD/worktree, datos ignorados, repo hermano y sistemas externos. No edites, no hagas git add/commit/switch/reset, no escribas en Drive/Gmail/CRM/LeadHub ni en FeesDefender-crm.
- No lances subagentes. Haz las pasadas necesarias tú mismo.
- Si ejecutas tests/experimentos, toda escritura/cache/basetemp debe ir fuera del repo: PYTHONDONTWRITEBYTECODE=1, pytest -p no:cacheprovider y basetemp en C:\Users\tnm33\AppData\Local\Temp con ruta corta. Nada de efectos externos.
- Captura `git status --porcelain --untracked-files=all` al principio y al final; deben coincidir y estar limpios.
- Contrasta contra código real y fuentes completas, no solo diff.
- Hallazgos H2-01, H2-02… ordenados por severidad/daño. Cada hallazgo: severidad, file:line preciso, hecho, impacto, evidencia/reproducción y corrección mínima. No infles nitpicks.
- Incluye secciones: Identificación y alcance; Fortalezas; Hallazgos; Respuesta al mandato 1–6 punto por punto; Preguntas/limitaciones; Veredicto SHIP/NO SHIP (no jurídico). Tú NO adjudicas.
- Escribe el informe ÚNICAMENTE fuera del repo en: C:\Users\tnm33\.codex\visualizations\2026\08\14\01a00102-89b6-7490-9cab-ad0a8c6f33d2\reviews\2026-08-15-apertura-integral-r2-adversarial-review.md
- Ese fichero no existe: no sobrescribas ningún informe previo. Formato canónico: UTF-8 sin BOM, LF, exactamente un salto final.
- Devuelve por canal final: ruta exacta, SHA256 canónico, conteo por severidad, veredicto, lista breve de hallazgos y evidencia de status limpio antes/después. Sin ruta+digest la revisión no cuenta.

## 1. Informe recibido de Codex, sin modificar

Digest declarado y verificado antes de adjudicar contra
C:\Users\tnm33\.codex\visualizations\2026\08\14\01a00102-89b6-7490-9cab-ad0a8c6f33d2\reviews\2026-08-15-apertura-integral-r2-adversarial-review.md:
FA1C5129FA76ABFDE991406140BE4FA415CCB4B3BA905A2E1B7D4DCB3D68DF17.

<!-- informe-literal:inicio:nqwp -->
# Revisión adversarial R2 — apertura integral de FeesDefender

## Identificación y alcance

- **Objeto:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, rev. 2.
- **Rama:** `codex/docs/apertura-integral-w02q38c`.
- **Commit revisado:** `f087edadbe803df8a738397b8697cdfccb1d52c4`.
- **SHA-256 del objeto:** `F5F5511DFC5ACBCEDE676282A776F0303EB96B951F13FC5D16B3086BAF1CA382`, coincidente con el mandato.
- **Ronda:** R2.
- **Revisor:** Codex, independiente y en solo lectura. Este informe no adjudica los hallazgos.
- **Estado inicial del repo:** limpio; `git status --porcelain --untracked-files=all` no produjo salida.
- **Fuentes leídas completas:** `AGENTS.md`, `CLAUDE.md`, la spec rev. 2, el acta R1 y `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`. Se leyeron además los diseños de apertura de 2026-07-09 y 2026-07-18, el runbook, la arquitectura dual del expediente activo, los contratos de sala de máquina y sala de lectura, las skills canónicas de sala de lectura, triaje y prerrelleno, el plan de intake/CRM y la política de seguridad.
- **Código contrastado:** apertura, localizador y gestor de casos, manifests/logs/lotes, Drive E&V, export Gmail, pull Sudespacho, ficha CRM, salas y pruebas de checkout/checkin. En la frontera LeadHub se leyó el repo hermano `C:\Users\tnm33\Dev\FeesDefender-crm` en `89226262918f4ef1ca79f612b329c9f196c8f938`, rama `main`, también limpio.
- **Ejecución dinámica:** solo el banco sintético `tests/test_repository_cli_defectos.py`, con `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp C:\Users\tnm33\AppData\Local\Temp\fdr2d678a`. Resultado esperado y reproducido: **7 xfailed, 0 xpassed**, exit 0. No se tocaron casos ni sistemas vivos.
- **Búsqueda de implementación:** no hay ninguna aparición implementada de `CaseWorkspace`, `candidate_revision`, `input_generation`, `consecutive_unchanged` o `escritura_resultado_desconocido` en `core/`, `scripts/` o `tests/`; son trabajo futuro de esta spec o de la arquitectura dual.

## Fortalezas

1. La rev. 2 corrige de forma material H-03: cada ronda exige una consulta remota real y un skip, caché o `.pulled` no acredita ausencia de cambios.
2. H-04 recibe una semántica única y comprensible: Drive E&V es espejo versionado, con historial content-addressed, generaciones y tombstones; ya no se llama simultáneamente lote inmutable.
3. El alta con resultado incierto y el dominio monetario están mucho mejor cerrados. La intención previa, el estado desconocido, la prohibición de segundo POST y el caso de prueba de timeout son concretos; `Decimal` más rechazo de fracciones no soportadas evita el redondeo silencioso.
4. La autoridad y procedencia por campo de la ficha son observables, y el riesgo residual de escribir antes de revisión humana se declara con honestidad y queda bloqueado para requerimientos y demandas.
5. La rama judicial, las relaciones CRM sin readback y LeadHub sin recolector completo no se presentan falsamente como completas. `preparado_con_pendientes` permite continuar ramas independientes sin blanquear la cobertura ausente.
6. `estado.json` pasa a la primera entrega y la invalidación global conservadora es una base más sencilla y verificable que un grafo prematuro.

## Hallazgos

### H2-01 — CRÍTICA — «Commit serializado» sigue siendo una propiedad deseada, no un mecanismo ejecutable

**Anclaje:** objeto `:99-101`, `:214-221`, `:361-365`, criterio 41 `:835-836` y estrategia `:863-864`; `core/intake_manifest.py:166-194`; `core/case_manager.py:1020-1062`; `core/intake_log.py:156-205`; `PLAN.md:21`, `:850-863`; `tests/test_repository_cli_defectos.py:127-225`.

**Hecho.** La spec prohíbe un coordinador en la primera entrega, permite ramas solapadas y exige que sus commits se serialicen. No elige quién adquiere la sección crítica ni qué primitiva la hace exclusiva entre los entrypoints/procesos existentes. A la vez, reserva lock/CAS para «relajar» la regla, aunque el criterio 41 ya exige dos ramas solapadas. En el código real, manifest y `_caso.md` siguen siendo ciclos read-modify-replace sin lock y el JSONL no coordina procesos. El único protocolo de lock existente no sirve como sustituto: el banco sintético conserva siete defectos `xfail`, incluido doble titular y rollback que cancela un lock ajeno.

**Impacto.** Dos procesos pueden entrar a la supuesta sección crítica y perder manifest, frontmatter, log o estado exactamente como en H-01. El remedio cambia «writers paralelos» por «commits serializados», pero no impide que dos writers se crean seriales. Se rompe custodia y el criterio 41 puede pasar solo si el test no solapa de verdad.

**Evidencia/reproducción.** La ejecución de `tests/test_repository_cli_defectos.py -q -rxX` produjo 7 xfails y 0 xpasses. La fuente declara expresamente «Sin lock, sin versionado» en `_atomic_write_caso_md`; `IntakeManifest.save` reemplaza el fichero desde una copia en memoria; `append_event` abre en append sin mutex interproceso.

**Corrección mínima.** Exigir desde la primera entrega un mutex interproceso corto por caso —o CAS equivalente— compartido por **todos** los puntos de commit. El lock de checkout no debe reutilizarse sin cerrar antes sus defectos. Definir adquisición, liberación tras crash, alcance de ficheros y orden de publicación, y probar dos procesos realmente solapados. Esto no requiere crear el coordinador prohibido.

### H2-02 — CRÍTICA — La apertura no se subordina a `CaseWorkspace` y puede escribir en la copia o servicio equivocados

**Anclaje:** objeto `:128-147`, `:163-170`, `:361-379`, `:859-874` y tabla `:880-920`; diseño dual `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md:83-100`, `:133-169`, `:178-198`; `PLAN.md:21`, `:850-863`; `scripts/abrir_caso.py:479-499`; `core/casos/case_locator.py:26-43`, `:100-121`; `core/sync_sudespacho.py:1467-1504`, `:1633-1667`.

**Hecho.** El contrato dual vigente dispone que durante checkout la copia local es la única operativa, que todo entrypoint mutante resuelve primero un `CaseWorkspace` y que las mutaciones canónicas de CRM/publicación/custodia se aplazan a checkin o promoción salvo excepción expresa. La rev. 2 solo dice que se respetará el lock y que el modo local no se dará por cerrado; no adjudica el contrato dual, no lo incluye en §16 y no lo coloca como predecesor de la entrega. Sus pasos sí crean/actualizan CRM, etiquetas Gmail, Drive y custodia.

La dependencia no existe aún en código: `PLAN.md` mantiene pendientes las fases 1-6; no existe `CaseWorkspace`; `abrir_caso` llama `ensure_case` antes de resolver una autorización de workspace y `path_for` todavía devuelve una ruta flat inexistente como fallback. En el pull CRM, el registro de ocurrencias se guarda antes del guard de bytes y después se actualizan `_caso.md` y el log canónicos aunque los documentos se hayan desviado.

**Impacto.** Una apertura sobre un caso prestado puede dividir bytes, manifests y estado entre Drive, local y `_pendiente_checkin`, o mutar CRM/Gmail mientras el contrato exige aplazar esas mutaciones. Una ruta local nacida sin baseline puede quedar presentada como operativa sin custodia. Es una vía de contaminación, split-brain y falsa trazabilidad.

**Evidencia/reproducción.** El diseño dual fija cuatro planos de «cero escritura» y `PLAN.md:850-863` confirma que el núcleo, checkout/scratch y primera vertical siguen pendientes. Un `rg` sobre `core/`, `scripts/` y `tests/` no encontró clase o servicio `CaseWorkspace`.

**Corrección mínima.** Añadir el diseño dual a §16 y elegir una de dos puertas: (a) hacer sus fases 1-3 predecesor duro de cualquier apertura mutante, o (b) limitar esta primera entrega a casos Drive `disponible` y bloquear checkout/scratch. Todo entrypoint debe resolver workspace antes de crear directorios, descargar o mutar servicios; cualquier excepción protocolaria externa debe enumerarse. Añadir matriz Drive disponible/checkout propio/checkout ajeno/scratch.

### H2-03 — CRÍTICA — No hay protocolo de recuperación que haga atómico el conjunto bytes–manifest–log–estado–remoto

**Anclaje:** objeto `:255-262`, `:361-365`, `:523-532`, `:569-582`, `:650-668`; criterios 2, 40-42, 45 y 48 `:765-766`, `:833-852`; `core/intake_manifest.py:166-194`; `core/intake_log.py:210-235`; `core/intake_lotes.py:141-153`; `core/sync_sudespacho.py:1467-1479`, `:1503-1505`, `:1571-1584`, `:1633-1667`; `core/email_export.py:1073-1102`, `:1171-1174`, `:1250-1315`.

**Hecho.** `temp + os.replace` protege un fichero, no una transacción que abarca bytes, historial Drive, manifests, log, `_caso.md`, YAML, `estado.json` y efectos remotos. La spec no fija un orden fail-closed ni un intent/commit durable por incorporación. Por ejemplo, un crash después de publicar bytes Drive o CRM y antes de incrementar `input_generation` deja fases verdes sobre una entrada nueva; invalidar primero evitaría ese falso verde, pero ese orden tampoco está exigido. Un crash en Sudespacho → YAML → `_caso.md` puede dejar dos de las tres proyecciones en revisiones distintas. El archivo secuencial se declara reanudable sin estado por efecto ni identificadores/readbacks persistidos.

El código real muestra el mismo corte en múltiples sitios: guarda ocurrencias, materializa bytes, guarda manifest, modifica `_caso.md` y añade log en operaciones separadas. El export Gmail guarda el índice de IDs antes del manifiesto/traza; un corte puede dejar un lote con bytes pero sin custodia o un índice que hace saltar su relectura. Peor aún, un manifest JSON corrupto se convierte silenciosamente en `{}` y una línea corrupta del log se descarta, en contradicción con el contrato dual que exige bloquear ante una cola no parseable.

**Impacto.** Tras crash o corte de red, la reanudación puede saltar evidencia no registrada, repetir efectos, perder procedencia o declarar `completo` sobre la generación anterior. El criterio 48 promete invalidación «atómica» que no puede obtenerse mediante reemplazos independientes.

**Evidencia/reproducción.** No existe en el esquema un intent de commit de intake/Drive/archivo ni un marcador de publicación común. `IntakeManifest.load` captura `JSONDecodeError` y empieza vacío; `read_events` hace `continue` sobre una línea inválida. No fue posible inyectar crashes en una implementación inexistente; la secuencia real de escrituras demuestra los puntos de corte.

**Corrección mínima.** Definir un protocolo pequeño, no un motor: estado `en_curso`/intent durable antes de publicar, identificador de commit y conjunto esperado, publicación de artefactos, verificación/readback y marcador `completada` siempre último. Al arrancar, reconciliar intent, disco, manifests y remoto; cualquier control corrupto bloquea y se conserva. Añadir crash-injection después de cada frontera, incluidas Drive, Gmail, archivo y las tres proyecciones CRM.

### H2-04 — ALTA — El estado mínimo no puede demostrar transiciones ni dos rondas completas de la misma generación

**Anclaje:** objeto `:543-567`, enum `:584-606`, esquema `:615-647`, reglas `:650-668` y resumen `:748-759`; criterios 10, 47 y 48 `:775-776`, `:849-852`.

**Hecho.** El enum general incluye `pendiente`, `en_curso` y `pendiente_reintento`, pero el enum de `sources.status` del JSON no los admite. No hay tabla de transiciones legales. Cada fuente conserva solo su última consulta y `fixed_point` conserva un único `round_id`; no hay vínculo `source → round_id`, conjunto atómico de attestations de ronda ni rastro de las dos rondas que justifican el contador. Consultas de momentos distintos pueden combinarse como si pertenecieran a una misma vuelta. El resumen promete número de intentos, pero el esquema no tiene contador. `candidate_revision` se menciona en prosa sin forma estructural completa.

Además, `snapshot_sha256` es «digest del inventario» sin definir por adaptador qué entra en él: IDs, rutas, tamaños, versiones, hashes, tombstones, campos remotos materiales o cobertura LeadHub. Una sustitución bajo el mismo ID/ruta puede parecer estable si cada adaptador elige una fotografía distinta.

**Impacto.** El contador puede llegar a dos con una fuente omitida, una consulta vieja o un cambio de contenido que no altere el inventario superficial. Una fase puede permanecer verde sobre inputs obsoletos y la evidencia no permite reconstruir por qué se alcanzó el punto fijo.

**Evidencia/reproducción.** El bloque JSON solo guarda una observación por fuente y una ronda global. No hay reglas que impidan `fallida → completada` ni que exijan que todas las fuentes obligatorias compartan `round_id`, generación y ventana de consulta.

**Corrección mínima.** Completar enums y transiciones; definir la fotografía canónica por adaptador; guardar `round_id` en cada attestación y conservar las dos rondas completas —o una cadena/digest equivalente—. Incrementar el contador solo en una actualización atómica que incluya todas las fuentes obligatorias frescas de esa ronda y generación. Probar consultas intercaladas, fuente fallida, reemplazo mismo ID/ruta y resultado desconocido.

### H2-05 — ALTA — La revisión humana no queda ligada a la versión remota que la persona vio

**Anclaje:** objeto `:506-513`, `:523-535`; criterios 20, 24, 44 y 45 `:790-803`, `:841-845`.

**Hecho.** La spec registra actor, instante y resultado de la revisión, pero no exige que ese registro contenga `candidate_revision`, expediente remoto y digest/versión exacta observada. Tras la revisión, cualquier diferencia del segundo GET se trata como corrección humana y se sincroniza CRM → YAML → `_caso.md`. El CAS descrito protege contra cambios locales o documentales, no distingue una edición humana revisada de una mutación remota concurrente posterior a la revisión.

**Impacto.** Una ficha A puede ser revisada por la persona; después otro usuario o proceso escribe B; el GET lee B, la resincronización lo adopta y el sistema declara `crm_ficha_completa` aunque nadie revisó B. El gate posterior de H-05 queda formalmente registrado, pero no prueba su objeto.

**Evidencia/reproducción.** `candidate_digests` cubre YAML, `_caso.md` y primer GET. El registro de revisión solo enumera actor/instante/resultado; no hay `reviewed_remote_digest`, ETag, `updated_at` ni precondición remota equivalente para el segundo GET.

**Corrección mínima.** Atar la attestación humana a `candidate_revision`, ID remoto y digest/versión de la ficha efectivamente revisada. El GET posterior solo puede cerrar si coincide con esa attestación; cualquier cambio posterior exige una nueva revisión o una confirmación explícita de los campos cambiados. Añadir una prueba de edición remota entre revisión y GET.

### H2-06 — ALTA — El piloto LeadHub exige infringir el contrato hermano antes de poder cambiarlo

**Anclaje:** objeto `:264-320`, criterio 43 `:839-840` y tabla `:897`; `C:\Users\tnm33\Dev\FeesDefender-crm\CLAUDE.md:7-16`; diseño hermano `docs/superpowers/specs/2026-07-31-descarga-fichas-crm-leadhub-design.md:20-62`, `:627-638`, `:848-904`; `scripts/medir.py:29-36`.

**Hecho.** La rev. 2 reconoce la contradicción, pero decide medir primero una vía principal con Nikolai y solo después modificar el contrato hermano. Ese contrato sigue ordenando que la captura la ejecute Marta con su propio acceso y que no la ejecute el despacho. El criterio 43 obliga a ejecutar ambas vías antes del cambio. Por tanto, la evidencia necesaria para autorizar el cambio solo se obtiene violando la regla aún vigente del repo donde debe correr el arnés.

**Impacto.** El criterio no es implementable de forma conforme. O se omite la vía Nikolai y no se cumple, o se ejecuta contra el contrato y la cadena de autoridad queda discutible. Registrar actor/cuenta evita atribución falsa, pero no cura la falta de autorización del flujo.

**Evidencia/reproducción.** El repo hermano estaba limpio en `8922626…`; su `CLAUDE.md:15-16` es categórico. Su código sigue siendo un arnés con `SHOP`, `REF` y `CONTACTO` fijos, no un recolector parametrizable.

**Corrección mínima.** Aprobar **antes** de la medición una enmienda acotada en el contrato hermano que autorice la vía experimental Nikolai, con alcance, cuenta, entorno, métricas y no-entrega; o retirar esa vía y conservar solo Marta. La modificación definitiva puede seguir esperando a los resultados.

### H2-07 — ALTA — La invalidación global no retira derivados obsoletos de los componentes canónicos

**Anclaje:** objeto `:390-417`, `:543-560`; criterios 10, 17, 37 y 42 `:775-787`, `:827-838`; `.claude/skills/organizar-sala-lectura/SKILL.md:464-469`, `:492-514`, `:397-405`; diseño `docs/superpowers/specs/2026-06-18-sala-lectura-unica-design.md:161-166`; diseño de sala de máquina `docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md:220-228`; runbook `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:228-238`.

**Hecho.** La spec afirma que cualquier cambio de fuente invalida y regenera salidas, y que una reconstrucción detecta huérfanos. Los contratos que §16 mantiene como canónicos son add-only: la sala de lectura salta hashes conocidos, conserva clasificaciones y nunca borra; para remontar exige vaciado manual. Su verificador comprueba fila ↔ fichero dentro de la propia sala, no que cada fila pertenezca al inventario vigente. La sala de máquina tampoco poda huérfanos globales; incluso con `--force` el runbook exige borrado manual.

**Impacto.** Si Drive sustituye o retira un documento, la nueva generación invalida la fase pero reejecutar el componente puede dejar la versión retirada visible, catalogada y verificable junto a la nueva. La sala humana queda contaminada y el estado puede volver a verde sobre un corpus que no representa la generación vigente. Si el nuevo verificador decide bloquear, el flujo queda sin remedio automatizado pese a prometer regeneración.

**Evidencia/reproducción.** La skill dice literalmente «solo añade; nunca borra» y reserva el vaciado a una acción manual. El runbook documenta que `--force` no toca `.md`/`.pdf`/`.txt` huérfanos. La rev. 2 no adjudica una sustitución de estos contratos.

**Corrección mínima.** Ampliar expresamente ambos contratos para reconciliar el manifiesto derivado con la **generación activa**: retirar a historial o marcar inactivos los derivados cuyo hash ya no esté vigente y excluirlos de índices/verificación. No es necesario borrar crudo ni historia. Probar retirada y reemplazo Drive hasta que solo la generación activa alimente índices y lectores.

### H2-08 — ALTA — El prerrelleno obligatorio deja sin salida a tipos para los que la skill canónica ordena no generar informe

**Anclaje:** objeto `:390-401`, `:422-426`, criterio 29 `:810-811` y §16 `:900-915`; `.claude/skills/viabilidad-prerelleno/SKILL.md:71-80`; `core/config.py:725-738`.

**Hecho.** La secuencia y el criterio 29 exigen prerrelleno verificado antes de la ficha completa. La skill canónica —que §16 conserva— ordena parar y no fabricar informe para `BAD_DEBT`, `LAU_20`, `DEVOLUCION_RESERVA` y `DEVOLUCION_HONORARIOS`; `INFORME_VIABILIDAD_TIPOS` los excluye por decisión de producto. La spec no contiene `no_aplica` ni excepción por tipo.

**Impacto.** Una apertura normal de uno de esos tipos no puede comenzar la fase 8.1 ni completar CRM sin contradecir la skill y crear un informe que el producto decidió no usar. Es un bloqueo permanente, no un pendiente de capacidad externa.

**Evidencia/reproducción.** No hay aparición de `INFORME_VIABILIDAD_TIPOS`, `BAD_DEBT` o un estado `no_aplica` en el objeto.

**Corrección mínima.** Añadir `viabilidad_prerrelleno: no_aplica_confirmado` derivado exclusivamente del canon `INFORME_VIABILIDAD_TIPOS`; permitir la ficha tras `verificada | no_aplica_confirmado` y adaptar los criterios 12 y 29. No cambia qué casos reciben informe.

## Respuesta al mandato 1–6

### 1. Reproducción y ataque de los remedios H-01…H-09

| R1 | Implementable | Suficiente / observable en R2 | Resultado de la pasada |
|---|---|---|---|
| H-01 | **No como está escrito.** Falta el dueño/primitiva de la sección crítica | El criterio 41 observa la unión final, pero no garantiza exclusión real | Sigue abierto como H2-01; crash-consistency adicional en H2-03 |
| H-02 | Las métricas y la recepción son observables; la vía Nikolai no es conforme al contrato hermano | Explicitar actor y estado pendiente mejora custodia, pero «medir antes de cambiar» es circular | Parcial; H2-06 |
| H-03 | Sí | Consulta real por ronda, `query_id` y prohibición de contar caché son adecuados | Remedio sustancialmente suficiente; la prueba de ronda común depende de H2-04 |
| H-04 | Sí como arquitectura de espejo versionado | Generación/tombstone son observables; falta orden recuperable de publicación y retiro de derivados | Parcial; H2-03 y H2-07 |
| H-05 | Sí | Procedencia/autoridad/conflicto hacen observable el write-before-review y el riesgo residual está bien declarado | Parcial: la revisión no acredita qué versión vio, H2-05 |
| H-06 | Sí para el POST de alta | Intención previa, estado desconocido, reconciliación exacta y criterio 46 forman un contrato fuerte | Suficiente para el alta; no generaliza por sí solo la recuperación de todos los efectos, H2-03 |
| H-07 | Sí | Dominio `Decimal`, escala, rechazo de fracciones no probadas y readback decimal son concretos | Suficiente a nivel de diseño |
| H-08 | Sí en tiempo de entrega | `estado.json` ya no se difiere, pero su esquema no demuestra rondas/transiciones ni el commit cross-artefacto | Parcial; H2-03 y H2-04 |
| H-09 | Sí, condicionado al adaptador | Allowlist, minimización, logs y retención son testables localmente; la telemetría debe concretarse por adaptador | Suficiente para pasar a plan **solo en esta frontera**; el plan debe aportar contrato y evidencia de borrado |

### 2. Nuevas rutas de pérdida, sobrescritura, duplicación, contaminación, PII y falsa custodia

- **Pérdida/lost update:** H2-01 conserva la carrera de H-01 porque no hay exclusión ejecutable.
- **Crash y falsa custodia:** H2-03 identifica cortes entre bytes, manifests, log, estado y remoto; los loaders actuales pueden resetear un manifest corrupto o saltarse una línea del log.
- **Copia equivocada/contaminación:** H2-02 permite escribir entre canon Drive, checkout local y bandeja, además de mutaciones externas incompatibles con el workspace activo.
- **Corpus obsoleto:** H2-07 deja derivados de versiones retiradas en salas que pueden volver a verificarse.
- **Duplicación externa:** el alta CRM está bien cubierta por H-06, pero archivo, creación/renombrado Gmail, actuación y movimientos Drive carecen de intent/readback por efecto en el estado de §10; quedan absorbidos por H2-03 y el criterio 40 debe incluir cortes tras cada efecto.
- **CRM → YAML → `_caso.md`:** H2-03 cubre el corte entre ficheros y H2-05 la aceptación de una edición remota que el humano no vio.
- **PII/secretos:** no encontré una nueva fuga directa en la prosa de rev. 2. H-09 mejora de forma material. Sigue siendo necesario que el plan demuestre, no solo afirme, bloqueo de telemetría y purga de temporales/logs en éxito y fallo.

### 3. Modelo de estado, generaciones y punto fijo

H2-03 y H2-04 son bloqueantes. El estado por fichero puede ser atómico, pero la generación no lo es respecto de los inputs que representa. Tampoco se pueden reconstruir dos rondas completas de la misma generación con una única fotografía sobrescrita. Faltan enums coherentes, transiciones legales, vínculo de consulta a ronda, definición canónica de snapshot, intentos y tratamiento fail-closed de controles corruptos. `candidate_revision` protege cambios locales esperados, pero no la versión remota revisada (H2-05).

La decisión de invalidación global es razonable y no hace falta ampliar a un grafo. El remedio mínimo es hacer durable y auditable esa regla conservadora.

### 4. Fronteras y contratos

| Frontera | Contraste R2 |
|---|---|
| Gmail | Descubrimiento expansivo y etiqueta tardía están bien. Falta recuperación por efecto tras timeout/crash, incluida la rama de archivo (H2-03). |
| Drive E&V | La semántica de espejo versionado es coherente. Faltan publicación recuperable y reconciliación de derivados retirados (H2-03/H2-07). |
| Sudespacho | La spec exige correctamente gate de referencia, `physical_complete`, `documents_failed == 0` y reconciliación. El CLI real aún solo avisa y continúa ante referencia distinta (`scripts/sync_sudespacho.py:172-203`), y el pull escribe estado canónico alrededor del guard; son dependencias de implementación que H2-02 obliga a ordenar. |
| LeadHub / `FeesDefender-crm` | No se promete recolector existente y la recepción se reverifica, pero el piloto contradice su fuente canónica antes de modificarla (H2-06). |
| Sala de máquina | Se elige el motor vigente y se rechaza exit 0 como prueba. Su contrato add-only no cierra retirada/reemplazo (H2-07). |
| Sala de lectura | Se nombra correctamente la skill canónica, no el core jubilado. La skill puede verificar una sala internamente coherente pero obsoleta (H2-07). |
| Viabilidad | Se conserva el veredicto humano y el prerrelleno en blanco. Falta el camino `no_aplica` ya exigido por la skill (H2-08). |
| Rama judicial | Limitación correctamente bloqueada con `--crm skip` y `adaptador_no_disponible`; no es hallazgo. |
| Workspace local/Drive | Contrato anterior vigente omitido y no implementado; es el bloqueo H2-02. |

### 5. Auditoría de los 50 criterios de aceptación

Leyenda: **D** = demostrable como contrato tras implementar; **P** = parcialmente demostrable, necesita precisión; **B** = bloqueado o contradictorio en la rev. 2. «D» no significa que el código actual ya lo cumpla.

| # | Estado | Evidencia exigible / defecto |
|---:|:---:|---|
| 1 | B | La secuencia mutante no resuelve `CaseWorkspace` ni exclusión real (H2-01/H2-02). |
| 2 | B | «Cualquier fase» exige crash protocol e intents por efecto que no existen (H2-03). |
| 3 | D | Dobles con exit 0 y resultado material inválido. |
| 4 | D | Inventario de disco ↔ fila ↔ SHA-256 completo. |
| 5 | D | Dos contenidos distintos con mismo destino deben bloquear antes de copiar. |
| 6 | D | Fixture de hilo institucional sin usuario en destinatarios. |
| 7 | D | Mock de referencia ajena y universo listado/materializado; el CLI actual debe pasar de aviso a gate. |
| 8 | D | Lista blanca y doble que falle ante toda mutación/comunicación. |
| 9 | D | Paquete incompleto + manifest de actor/cuenta/rol/tiempos/cobertura. |
| 10 | B | Consulta real es demostrable; invalidar y **regenerar** no lo es con componentes add-only y ronda no ligada (H2-04/H2-07). |
| 11 | D | Casos entero, fraccionario rechazado y round-trip exacto si el contrato lo admite. |
| 12 | D | Inspección de celdas protegidas/en blanco; debe combinarse con `no_aplica` de H2-08. |
| 13 | P | Las tres etiquetas son observables, pero `completo` hereda la prueba incompleta de estado. |
| 14 | P | Los escenarios listados son reproducibles; faltan cortes en cada commit/efecto y matriz dual. |
| 15 | D | Resolver puro sin `mkdir` y ambigüedad/sombra; depende de la fase dual 1. |
| 16 | D | Inventario excluye controles y `~$*`. |
| 17 | B | El verificador vigente no contrasta filas antiguas con la generación activa (H2-07). |
| 18 | D | Respuesta vacía sin errores frente a respuesta/error material. |
| 19 | D | Capability negotiation sobre arnés sin recolector. |
| 20 | P | Campos/readback son comprobables; la revisión no queda ligada a la versión remota (H2-05). |
| 21 | D | Comparación exacta de normalización y literals `Select`. |
| 22 | D | Dirección ambigua produce estado bloqueante y ninguna preparación/envío. |
| 23 | P | Egress y allowlist se pueden mockear; telemetría y retención necesitan contrato/evidencia por adaptador. |
| 24 | B | Tres destinos no tienen commit recuperable y la versión revisada no está atestada (H2-03/H2-05). |
| 25 | D | GET–merge–PUT–GET sobre contrario existente y estado humano pendiente. |
| 26 | D | Prueba byte a byte de body/secciones y conflicto de valores dentro de `_caso.md`. |
| 27 | D | Guard de arquitectura/ausencia del módulo coordinador hasta evidencia E2E. |
| 28 | D | Alta mínima sin llamadas de persona y estado pendiente. |
| 29 | B | Contradice los tipos `no aplica` de la skill canónica (H2-08). |
| 30 | D | Fixtures de propietario/firmante/deudor discordantes y bloqueo downstream. |
| 31 | D | Mock Gmail que verifica momento, jerarquía, color y conservación de hilos. |
| 32 | P | Procedencia/conflicto son observables; la attestación humana sigue incompleta (H2-05). |
| 33 | D | Código repetido, W-code existente y `--force` con resolver estricto. |
| 34 | D | Espía de llamadas demuestra `--crm skip`, registro y pull antes de salas. |
| 35 | D | Suite de regresión B2–B5. |
| 36 | B | «Conserva locks» no basta mientras el workspace y los siete xfails siguen pendientes (H2-02). |
| 37 | B | No hay mutex de corridas y la detección de huérfanos no los retira ni invalida el corpus (H2-01/H2-07). |
| 38 | D | Rama judicial bloqueada y ausencia de llamadas extrajudiciales. |
| 39 | D | Intento sin readback queda bloqueado y no hay segundo POST. |
| 40 | B | No hay estado/intento/readback por los seis efectos de archivo ni crash test entre ellos (H2-03). |
| 41 | B | Exige la exclusión que la spec no implementa (H2-01). |
| 42 | B | Historial/tombstone son comprobables, pero no publicación tras crash ni retiro de derivados (H2-03/H2-07). |
| 43 | B | Ejecutar la vía Nikolai antes de cambiar el contrato hermano es circular (H2-06). |
| 44 | B | Actor/instante no prueban la versión revisada (H2-05). |
| 45 | B | El CAS no protege mutación remota post-revisión ni el corte entre tres destinos (H2-03/H2-05). |
| 46 | D | Es el mejor criterio nuevo: timeout-after-commit, un candidato, adopción y contador de POST = 1. |
| 47 | B | La fuente no se liga a ronda y los enums/attestations son incompletos (H2-04). |
| 48 | B | No existe atomicidad entre inventario materializado y `estado.json` (H2-03). |
| 49 | P | La purga local es testable con reloj simulado; «telemetría desactivada» necesita definición y evidencia. |
| 50 | B | Cablear detrás de entrypoints no crea por sí solo exclusión ni resolución de workspace (H2-01/H2-02). |

**Resultado de la matriz:** 27 D · 6 P · 17 B = 50 criterios revisados.

### 6. Preparación para plan TDD

**NO SHIP.** H2-01, H2-02 y H2-03 son bloqueantes: el plan no puede escribir pruebas honestas de exclusión, copia activa o recuperación porque la spec no ha elegido los contratos necesarios. H2-04 y H2-05 permiten falso verde sobre ronda o revisión obsoleta. H2-06, H2-07 y H2-08 hacen incumplibles criterios concretos aun sin carrera.

No hace falta diseñar un motor mayor. El mínimo es: mutex/CAS corto; subordinación a la arquitectura dual; orden de commit con intent y recuperación; attestations de ronda; revisión ligada a versión remota; enmienda previa del piloto; reconciliación de derivados por generación; y `no_aplica` de viabilidad.

Son limitaciones bien bloqueadas —y no defectos— la ausencia actual de rama judicial, el recolector LeadHub incompleto, la falta de readback fiable de relaciones y la reserva del juicio jurídico al abogado.

## Preguntas y limitaciones

1. No se consultaron casos reales ni Gmail, Drive, Sudespacho, LeadHub, Correos o Catastro. Los efectos externos se contrastaron contra contratos y código, no contra una sesión viva.
2. No se inyectaron crashes en componentes aún inexistentes. Los puntos de corte se derivan de las secuencias de escritura reales y de la ausencia de un protocolo común en la spec.
3. La prueba dinámica de siete xfails caracteriza el lock de checkout/checkin, no sustituye una prueba futura del mutex corto de commit que exige H2-01.
4. No se lanzaron subagentes ni se escribió en el repo, su índice, datos ignorados, repo hermano o servicios externos.
5. Este informe propone correcciones mínimas para adjudicación; no decide su forma final ni autoriza implementación.

## Veredicto

**NO SHIP** para pasar a plan TDD.

**Resumen:** 8 hallazgos — **3 críticos, 5 altos, 0 medios, 0 bajos**.

<!-- informe-literal:fin:nqwp -->

## 2. Evidencia verificada al adjudicar

La adjudicación se hizo contra la fuente y el código real, no contra el aplomo del informe.

| ID | Evidencia comprobada |
|---|---|
| H2-01 | Manifest y `_caso.md` son read-modify-replace sin exclusión interproceso; el banco sintético del lock conserva siete defectos `xfail`. |
| H2-02 | `CaseWorkspace` no existe en `core/`, `scripts/` o tests; el diseño dual y PLAN mantienen pendientes las fases de checkout/scratch y enforcement. |
| H2-03 | Las escrituras de bytes, manifests, log, estado y remoto ocurren en fronteras separadas; los loaders actuales pueden degradar controles corruptos. |
| H2-04 | El esquema rev. 2 guardaba una sola observación por fuente, sin `round_id`, fotografía cerrada ni tabla de transiciones. |
| H2-05 | La revisión humana registraba actor e instante, pero no la versión remota exacta observada. |
| H2-06 | El contrato hermano asignaba toda captura a Marta; se enmendó antes de medir en `FeesDefender-crm` v3.7, commit `8bc09ea`. |
| H2-07 | Los contratos canónicos de sala de máquina y lectura son add-only y no retiraban del corpus activo derivados de generaciones obsoletas. |
| H2-08 | `INFORME_VIABILIDAD_TIPOS` excluye `BAD_DEBT`, `LAU_20`, `DEVOLUCION_RESERVA` y `DEVOLUCION_HONORARIOS`. |

Se verificaron la rama, el commit, el SHA-256 canónico del informe y los repositorios principal
y hermano. No se consultaron ni mutaron casos reales, Drive, Gmail, LeadHub o Sudespacho.
