---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
objeto_rev: "1"
commit: bedfc45dda942afd5c5df3b8ec95e6ce8a008b33
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: qzvx
sha256_informe: 6266a9702354dd30ec7607acf8193f33b3778f494593bd39293a4a734d9ef8be
adjudicado_en: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md §18
adjudicador: Codex (subagente independiente, sustitución excepcional por indisponibilidad de Claude Code)
independencia_adjudicacion: debilitada-misma-familia
---

> **Acta de revisión adversarial R1.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el §18 del objeto, no aquí.
>
> **Adjudicación excepcional:** adjudica Codex (subagente independiente, sustitución
> excepcional por indisponibilidad de Claude Code), por decisión expresa de Nikolai. Esto
> contradice la regla ordinaria «Claude adjudica siempre». Revisor y adjudicador pertenecen
> al mismo modelo/familia; la independencia es más débil y puede compartir puntos ciegos.
> La ronda conserva NO-SHIP y la rev. 2 queda pendiente de R2.

## 0. Mandato (literal, tal como se entregó)

MANDATO NUMERADO, EN ORDEN DE DAÑO
1. Busca rutas que puedan perder, sobrescribir, duplicar o contaminar datos/expedientes; fugas PII/secretos; ruptura de custodia; escrituras externas que el diseño dé por verificadas sin estarlo.
2. Contrasta punto por punto la adjudicación de los dos diseños anteriores y del runbook: detecta reglas relevantes omitidas, derogaciones ambiguas o contradicciones internas.
3. Comprueba implementabilidad contra el código real: entrypoints existentes, modelos de datos, readback, idempotencia, reanudación, colisiones, rama judicial, Gmail, Drive, Sudespacho y la frontera con FeesDefender-crm/LeadHub. Marca expresamente las promesas que hoy no puedan construirse como están redactadas.
4. Ataca el orden E2E, los gates y el punto fijo: carreras, estados parciales, reintentos ciegos, doble ejecución, etiquetas prematuras, aperturas fantasma y falso estado “completo”.
5. Revisa que cada criterio de aceptación sea observable, verificable y no contradiga otro; detecta criterios ausentes que permitan declarar éxito sin resultado material.
6. Evalúa si la spec está lista para pasar a plan TDD. Distingue defectos del diseño de limitaciones conocidas correctamente bloqueadas. No diseñes una solución más grande que el encargo.

CONTRATO DE REVISIÓN
- Solo lectura sobre repo, Git, datos ignorados y sistemas externos. No edites ningún fichero del repo, no hagas git add/commit/switch/reset, no escribas en Drive/CRM/Gmail/LeadHub.
- No lances subagentes.
- Puedes ejecutar inspecciones y tests solo si todas las escrituras/cache/basetemp van fuera del repo. Compara git status --porcelain --untracked-files=all antes/después.
- Responde al mandato 1–6 punto por punto en una sección propia.
- Hallazgos numerados H-01, H-02… y ordenados por severidad/daño. Para cada uno: severidad, anclaje preciso file:line, hecho observado, impacto, evidencia en fuente/código real y corrección mínima sugerida. No eleves nitpicks.
- Separa fortalezas, hallazgos, preguntas/limitaciones y veredicto (SHIP / NO SHIP para pasar a plan; no es veredicto jurídico).
- Tú no adjudicas: no declares que tu remedio es la decisión final.

## 1. Informe recibido de Codex, sin modificar

Digest declarado y verificado antes de adjudicar contra
C:\Users\tnm33\.codex\visualizations\2026\08\14\01a00102-89b6-7490-9cab-ad0a8c6f33d2\reviews\2026-08-15-apertura-integral-r1-adversarial-review.md:
6266A9702354DD30EC7607ACF8193F33B3778F494593BD39293A4A734D9EF8BE.

<!-- informe-literal:inicio:qzvx -->
# Revisión adversarial R1 — apertura integral de FeesDefender

## Identificación y alcance

- Objeto: `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`.
- Base: `2c3ba24f76be6576c69f40b52fd63115158c79ce`.
- Commit revisado: `bedfc45dda942afd5c5df3b8ec95e6ce8a008b33` (`HEAD` durante la revisión).
- Revisor: Codex, revisión independiente de solo lectura.
- Fuentes leídas completas: `CLAUDE.md`, `AGENTS.md`, los diseños de 2026-07-09 y 2026-07-18, el runbook de apertura y el objeto principal.
- Código contrastado: entrypoints y módulos reales de apertura, ficha CRM, localización de casos, intake, manifest/log, Drive E&V, pull Sudespacho, correo, salas y viabilidad. Para la frontera LeadHub se contrastó además el repositorio hermano `C:\Users\tnm33\Dev\FeesDefender-crm` en el commit `89226262918f4ef1ca79f612b329c9f196c8f938`, sin modificarlo.
- No se consultaron ni mutaron casos reales ni sistemas externos. La única ejecución dinámica fue una reproducción sintética bajo `%TEMP%` de la carrera del manifest.

## Fortalezas

1. La spec distingue correctamente LeadHub de Sudespacho, conserva la prohibición de mutaciones en LeadHub y reconoce que el recolector probatorio todavía no existe.
2. Mantiene bloqueada la rama judicial en vez de hacerla pasar por los entrypoints extrajudiciales, preserva `--crm skip` en intake incremental y no confunde vincular un expediente con descargar su gestor documental.
3. Corrige el orden material de la ficha del contrario: primero evidencia, salas y prerrelleno; después identidad y CRM. También conserva el veredicto jurídico fuera del flujo.
4. La tabla del §16 adjudica expresamente buena parte de B1–B5 y del runbook, y declara que una omisión no deroga una regla anterior.
5. Sustituye el éxito por código de salida por verificaciones materiales y reconoce honestamente los límites de readback de relaciones y del adaptador LeadHub.

## Hallazgos

### H-01 — CRÍTICA — El paralelismo ordenado por la spec pierde entradas del manifest y puede clobberar `_caso.md`

**Anclaje:** objeto `:181-182`, `:270-294`, `:421-423`; `core/intake_manifest.py:158-194`; `core/case_manager.py:1020-1062`; `core/intake_log.py:156-205`.

**Hecho observado.** Tras fijar identidad, la spec arranca en paralelo Gmail, Drive, LeadHub y Sudespacho. Esas ramas no son solo lectura: materializan lotes, registran hashes, actualizan pull state y escriben eventos. `IntakeManifest` hace `load → mutación en memoria → os.replace` sin lock, revisión de versión ni merge contra el estado vigente. `_atomic_write_caso_md` tiene la misma forma read-modify-replace sin exclusión. El append del JSONL tampoco coordina procesos.

La carrera del manifest se reprodujo con dos instancias solapadas sobre un caso sintético en `%TEMP%`: ambas cargaron vacío; la primera guardó el hash `a…`; la segunda guardó `b…`; el fichero final tuvo `COUNT=1` y `LOST_A=True`. No se escribió en el repo.

**Impacto.** Una apertura conforme al diseño puede perder procedencia, aliases y estado de pull aunque todos los procesos terminen con éxito. Dos ramas pueden además perder actualizaciones mutuas de `_caso.md`. Esto rompe custodia, deduplicación, reanudación y la propia prueba de “todas las invariantes verdes”.

**Evidencia en fuente/código real.** La atomicidad de `os.replace` evita un fichero parcial, pero no evita lost updates entre dos ciclos read-modify-write. La spec paraleliza precisamente los writers que comparten esos ficheros.

**Corrección mínima sugerida.** Mantener en paralelo solo el descubrimiento y las descargas a staging disjunto; serializar el commit a `00_Input`, manifest, log y `_caso.md`. Alternativamente, exigir antes del paralelismo un lock interproceso/CAS probado para cada estado compartido. Añadir una aceptación que ejecute dos ramas solapadas y demuestre la unión íntegra de ambos resultados.

### H-02 — CRÍTICA — La rama LeadHub atribuye la sesión al abogado y la integra como rama local, contra el contrato del repositorio autónomo

**Anclaje:** objeto `:211-253`, `:545-555`; `C:\Users\tnm33\Dev\FeesDefender-crm\CLAUDE.md:7-16`; `...\docs\superpowers\specs\2026-07-31-descarga-fichas-crm-leadhub-design.md:20-62`, `:627-638`, `:850-904`; `...\scripts\medir.py:29-36`, `:76-87`.

**Hecho observado.** El objeto prescribe una captura “en paralelo” con perfil dedicado y “sesión autenticada por el abogado”; si caduca, la rama queda en `espera_login`. El contrato canónico de `FeesDefender-crm` dice otra cosa: la captura la ejecuta Marta Reynares con su propio acceso; el despacho decide y entrega la lista de referencias; el universo de contactos no es derivable del CRM; la entrega tiene puerta humana, sincronización no atómica y reverificación en el despacho. El código actual solo es un arnés de medición con `SHOP`, `REF` y `CONTACTO` fijos, tal como reconoce el propio objeto.

**Impacto.** El flujo propuesto cambia quién accede, quién ejecuta y quién puede declarar la diligencia; además presenta como una rama local reanudable lo que hoy es un handoff externo con operador corporativo, veredicto técnico/humano y transferencia posterior. Puede producir atribución falsa de cuenta/persona ejecutora y una cadena de custodia incompleta. Tampoco puede determinar automáticamente “contactos relevantes” sin la decisión que el contrato reserva al despacho.

**Evidencia en fuente/código real.** El contrato hermano exige confirmar en pantalla cuenta, rol y operador; declara que el paquete acredita solo lo visible para esa cuenta; y que el manifiesto viaja por Drive y se reverifica al recibirlo. No existe aún el contrato de solicitud/resultado ejecutable que el objeto afirma que se invocará como proceso.

**Corrección mínima sugerida.** Reescribir la rama como handoff asíncrono: `espera_operador_ev`/`espera_entrega`, lista de referencias decidida por el despacho, ejecución por el actor autorizado del contrato hermano, y recepción con reverificación de hashes. No fijar “abogado autenticado” ni `espera_login` local salvo que se adjudique y cambie primero el contrato canónico de `FeesDefender-crm`.

### H-03 — ALTA — El punto fijo no vuelve a consultar Drive: `.pulled` convierte dos comprobaciones en un falso “sin novedad”

**Anclaje:** objeto `:206-210`, `:409-423`, criterios `10` y `14` en `:569-574`; `scripts/abrir_caso.py:108-112`; `core/intake_drive.py:163-230`.

**Hecho observado.** El bucle exige volver a consultar Drive y estabilizarse tras dos pasadas sin novedad. El entrypoint vigente llama `pull_drive_ev(...)` sin `force`; si existe un `.pulled` con return code cero, el adaptador retorna `skipped=True` sin ejecutar rclone. El `--force` del CLI gobierna colisiones de identidad y no se transmite al pull.

**Impacto.** Un fichero añadido o sustituido en Drive después del primer pull no se observa. Dos iteraciones consecutivas pueden declarar estabilidad porque ambas saltaron la fuente, dejando salas, prerrelleno y ficha obsoletos.

**Evidencia en fuente/código real.** `core/intake_drive.py:207-230` retorna antes de construir o ejecutar el comando remoto. No existe hoy un flag del entrypoint de apertura que fuerce el refresh de fuente en el bucle.

**Corrección mínima sugerida.** Separar semánticamente `--force` de identidad y “refrescar fuente”; exigir un snapshot remoto real en cada vuelta de estabilización y registrar qué consulta se hizo. Añadir prueba E2E: crear `.pulled`, añadir un fichero remoto/simulado y comprobar que la siguiente vuelta invalida dependientes.

### H-04 — ALTA — “Cada rama entrega un lote inmutable” contradice el espejo Drive fijo que puede sobrescribir el crudo

**Anclaje:** objeto `:270-294`; diseño 2026-07-09 `:178-195`; `core/config.py:529-537`; `core/intake_drive.py:197-200`, `:257-273`, `:305-319`.

**Hecho observado.** La nueva spec afirma que cada rama entrega un lote inmutable y que el crudo no se borra. El contrato heredado y el código definen Drive E&V como espejo `00_Input/01_Drive EV`, no como lote. `rclone copy` escribe al mismo destino con `--inplace`, `--ignore-size` y `--ignore-checksum`. Una versión nueva bajo el mismo nombre puede reemplazar la copia anterior; una retirada remota tampoco queda representada como snapshot/tombstone.

**Impacto.** Se puede perder la versión de intake originalmente procesada y, con ella, la posibilidad de reproducir qué evidencia alimentó una sala o informe. El hash posterior prueba el estado final, no conserva el anterior sobrescrito.

**Evidencia en fuente/código real.** `FUENTES_LOTE` excluye expresamente `drive_ev`; `ESPEJO_SUBDIRS` lo incluye. La tabla del §16 no adjudica esta contradicción entre espejo mutable y lote inmutable.

**Corrección mínima sugerida.** Elegir expresamente una semántica. Si Drive sigue siendo espejo, conservar por versión cualquier contenido reemplazado y emitir ocurrencias/tombstones; si pasa a snapshots, definir lotes Drive inmutables y su reconciliación. No declarar ambas cosas a la vez.

### H-05 — ALTA — Se elimina la revisión humana del YAML sin definir un gate automático de evidencia que pueda sustituirla

**Anclaje:** objeto `:96-100`, `:335-407`, criterios `20-26` y `32` en `:582-607`; diseño 2026-07-18 `:68-78`, `:239-253`; `core/crm_ficha.py:27-80`; `scripts/crm_ficha.py:76-103`.

**Hecho observado.** La spec sustituye la revisión manual obligatoria de `_ficha_crm.yaml` por continuidad automática cuando los datos sean “anclados, unívocos y validados”. No define un esquema de anclas, una fuente autorizada por campo, un algoritmo de conflicto ni un artefacto firmado que pruebe esos predicados. El loader real solo exige `nombre` a contrario/colaboradores; `--yes` pasa directamente a vínculos y PUT.

**Impacto.** Datos extraídos o inferidos incorrectamente pueden crear/actualizar una persona real y vincularla al expediente sin una decisión humana. El criterio 32 repite la intención, pero no proporciona una observación que permita demostrar “unívoco”.

**Evidencia en fuente/código real.** El YAML actual no conserva cita, hash de documento, rol jurídico, confianza ni resolución de contradicciones. `crm_ficha` imprime un plan descriptivo, no verifica la evidencia que originó los valores.

**Corrección mínima sugerida.** Mantener el gate humano heredado hasta que la spec defina y acepte un modelo de procedencia/conflicto verificable por campo. Si se automatiza después, exigir que el adaptador rechace todo valor sin ancla válida y que el test demuestre conflicto, fuente ausente y rol ambiguo.

### H-06 — ALTA — El alta CRM no tiene contrato para el resultado incierto y los criterios permiten duplicados tras timeout

**Anclaje:** objeto `:147-177`, `:475-477`; criterios `2`, `3` y `28` en `:561-562`, `:598-599`; `scripts/abrir_caso.py:265-305`, `:497-499`.

**Hecho observado.** La spec exige alta idempotente y readback tras toda escritura, pero no especifica qué ocurre si el POST se confirma en Sudespacho y la respuesta se pierde. El código actual registra el ID local solo después de recibirlo; captura cualquier excepción, avisa, y el comando termina imprimiendo `OK Caso abierto` con exit cero. Al reintentar, no hay ID local que frene otro POST.

**Impacto.** Un timeout-after-commit puede crear expedientes duplicados/fantasma. El estado local puede decir pendiente aunque el remoto exista, y el siguiente intento agrava la divergencia. “No repetir efectos confirmados” no cubre precisamente el efecto remoto de resultado desconocido.

**Evidencia en fuente/código real.** `_alta_crm` no hace readback ni búsqueda de reconciliación después del error; tampoco persiste `resultado_desconocido`. El gate de relaciones sin readback del §8.1 no se generaliza al alta.

**Corrección mínima sugerida.** Definir un estado `escritura_resultado_desconocido`; antes de cualquier re-POST, buscar por referencia canónica y reconciliar exactamente un candidato por readback. Solo registrar `crm_alta` tras verificar referencia, elemento y cuantía. Añadir aceptación de timeout después de commit remoto.

### H-07 — ALTA — La precisión decimal exacta es imposible con la interfaz de dinero vigente

**Anclaje:** objeto `:158-159`, criterio `11` en `:570`; `scripts/abrir_caso.py:380`; `core/abrir_caso.py:238-266`; `core/sudespacho_create.py:856-875`, `:1215-1248`, `:1410-1442`.

**Hecho observado.** La spec exige decimal exacto de extremo a extremo. El CLI recibe `float`; los DTO usan `float`; y los payloads REST convierten `cuantia`, `costas` e `intereses` con `int(round(...))`. Una cuantía con céntimos se redondea antes del POST.

**Impacto.** El sistema puede escribir y luego “verificar” un importe distinto del autorizado. Drive/informe y Sudespacho no pueden cumplir el criterio 11 para valores no enteros.

**Evidencia en fuente/código real.** El truncamiento de precisión es explícito en `_build_rest_payload_extrajudicial` y `_build_rest_payload_judicial`.

**Corrección mínima sugerida.** Adjudicar primero el dominio que admite Sudespacho. Si admite céntimos, usar `Decimal`/string canónica hasta el wire y verificar escala; si solo admite euros enteros, rechazar valores fraccionarios y reescribir el criterio como igualdad exacta dentro de ese dominio. Nunca redondear silenciosamente.

### H-08 — ALTA — La spec difiere el único estado capaz de demostrar reanudación e invalidación, pero ya exige esas propiedades

**Anclaje:** objeto `:409-423`, `:440-477`; criterios `2`, `10`, `13` y `14` en `:561-574`; estrategia `:627-637`.

**Hecho observado.** El caso solo se considera estable tras dos comprobaciones consecutivas sin novedad y debe reanudar desde la primera fase no válida. Sin embargo, la primera entrega prohíbe crear estado/ledger global y solo permite añadirlos después de que una prueba E2E demuestre la carencia. Los artefactos actuales registran estados locales heterogéneos, pero no una generación de inputs, la relación de dependencia, una comprobación negativa por adaptador ni el ordinal de las dos vueltas.

**Impacto.** No hay forma inequívoca de distinguir “fuente consultada sin cambios” de “fuente saltada/no disponible”, ni de probar qué versión de inputs validó cada sala y ficha. La prueba E2E exigida como condición previa al ledger no puede verificar los criterios cuya observabilidad depende de ese ledger: es una dependencia circular.

**Evidencia en fuente/código real.** `_intake_hashes.json`, `_cobertura.json`, catálogos y frontmatter no comparten `run_id`/generación ni registran el punto fijo cross-sistema. El propio incidente de `.pulled` de H-03 ilustra que la ausencia de novedad no es observable globalmente.

**Corrección mínima sugerida.** Exigir desde la primera entrega una fotografía mínima, atómica y regenerable de generación por fuente/fase, sin construir una máquina de workflows completa; o rebajar la primera entrega a runbook manual y retirar criterios de reanudación/punto fijo hasta el coordinador.

### H-09 — ALTA — El enriquecimiento postal introduce un quinto adaptador con PII fuera de la frontera y sin contrato de privacidad

**Anclaje:** objeto `:43-55`, `:66-72`, `:367-374`; criterios `22-23` en `:586-589`; `docs/SEGURIDAD_DATOS.md:32-47`, `:58-66`.

**Hecho observado.** El alcance declara cuatro sistemas externos, pero la ficha envía o consulta un domicilio de tercero en Correos, fuentes municipales/catastrales y eventualmente fuentes comerciales. No se define qué servicio/endpoints se autorizan, qué datos mínimos salen, qué logging/cookies/retención aplica, ni cómo se evita que la consulta quede en terminal o telemetría. El criterio 23 solo impide filtrar PII a Git.

**Impacto.** La automatización puede revelar a terceros una dirección asociada a una investigación o reclamación y generar trazas externas no gobernadas. Además, un plan no puede escribir tests de contrato para “fuente pública equivalente” o “fuente comercial” sin una lista cerrada.

**Evidencia en fuente/código real.** La política vigente protege repo/chat y secretos, pero el objeto amplía el tratamiento externo sin adjudicar esa nueva frontera. No existe hoy adaptador postal en el inventario de componentes.

**Corrección mínima sugerida.** Declarar el enriquecimiento como adaptador de solo lectura separado, con lista cerrada de fuentes, minimización de consulta, política de logs/retención y autorización explícita; o mantenerlo como paso humano bloqueante. Añadir aceptación de no salida de PII fuera de los campos estrictamente necesarios.

## Respuesta al mandato 1–6

### 1. Pérdida, sobrescritura, duplicación, contaminación, PII y custodia

- H-01 demuestra pérdida reproducible de manifest/procedencia por paralelismo.
- H-04 identifica sobrescritura potencial del crudo Drive y ausencia de versiones/tombstones.
- H-06 cubre duplicación y aperturas fantasma por resultado remoto desconocido.
- H-02 cubre atribución/entrega probatoria incorrecta en LeadHub.
- H-05 y H-09 cubren mutación de fichas personales sin gate probatorio y divulgación a nuevas fuentes externas.
- La spec sí conserva correctamente el bloqueo por referencia ajena en Sudespacho, pero hoy no está en el core del pull: `scripts/sync_sudespacho.py:172-203` solo avisa y continúa, mientras `pull_expediente_v2` no recibe una referencia esperada. Es una limitación conocida que el plan deberá cerrar antes de reutilizar el pull como gate.

### 2. Adjudicación de diseños anteriores y runbook

La tabla del §16 conserva correctamente B2–B5, el orden de ficha tras viabilidad, `--crm skip`, el bloqueo judicial, la etiqueta tardía y el archivo secuencial. Las divergencias materiales son:

- la revisión humana del YAML se sustituye sin un control equivalente (H-05);
- el espejo Drive heredado se describe simultáneamente como lote inmutable (H-04);
- el contrato externo de LeadHub no queda adjudicado y se contradice (H-02);
- la regla de verificación por resultado no cubre el resultado desconocido del alta (H-06).

No considero defecto que la rama judicial o el recolector LeadHub sigan bloqueados: son limitaciones reconocidas correctamente. Sí lo es describir su actor/flujo de manera incompatible con la fuente canónica.

### 3. Implementabilidad contra el código real

- B2–B5, el bloqueo judicial, el pull físico completo del core y buena parte de los verificadores son reutilizables.
- No son construibles tal como están redactados: el paralelismo de writers (H-01), LeadHub como proceso local del abogado (H-02), el punto fijo Drive con el entrypoint vigente (H-03), la inmutabilidad sobre el espejo actual (H-04), el gate automático del YAML sin modelo de evidencia (H-05), la idempotencia ante outcome incierto (H-06), el decimal exacto con `float → int(round)` (H-07) y el punto fijo/reanudación sin estado mínimo (H-08).
- `scripts.crm_ficha` es extrajudicial-only, no actualiza `_caso.md`, no completa un contrario preexistente y no hace readback de relaciones. La spec lo reconoce y lo bloquea: son trabajos de implementación, no hallazgos nuevos por sí solos.
- La sala de lectura canónica de skill tiene verificadores más fuertes que `scripts.sala_lectura`, cuyo `organizar` acaba en `core.sala_lectura.organizar` y solo imprime acciones (`scripts/sala_lectura.py:116-125`; `core/sala_lectura.py:663-673`). El plan debe nombrar una única interfaz ejecutable; no puede tratar ambos caminos como equivalentes.

### 4. Orden E2E, gates y punto fijo

El orden documental es mejor que el runbook manual, pero H-01 hace inseguro el paralelismo de materialización; H-03 permite un falso punto fijo; H-06 no cubre el estado “escritura quizá aplicada”; y H-08 impide demostrar reanudación/invalidation cross-fase. El gate de etiqueta tardía y el bloqueo judicial están bien definidos.

### 5. Criterios de aceptación

Los criterios son numerosos, pero varios no son verificables aún:

- criterio 2 no cubre efectos remotos de resultado desconocido (H-06);
- criterios 10 y 14 no exigen que la segunda consulta de Drive sea real (H-03);
- criterio 11 contradice el wire format vigente (H-07);
- criterio 32 no define cómo observar “anclado/unívoco” (H-05);
- no existe criterio de concurrencia que proteja manifest y frontmatter (H-01);
- no existe criterio que compruebe el actor/handoff/recepción exigidos por el contrato LeadHub (H-02);
- criterios 2, 10, 13 y 14 presuponen estado global que la entrega difiere (H-08).

Faltan, como mínimo, pruebas de dos writers solapados, refresh Drive tras `.pulled`, timeout-after-commit CRM, reconciliación de versión reemplazada y recepción LeadHub con actor y referencias autorizadas.

### 6. Preparación para plan TDD

**NO SHIP para pasar a plan.** La arquitectura general es aprovechable, pero H-01 y H-02 cambian el modelo de ejecución y custodia; H-03–H-08 afectan invariantes que el plan necesitaría dar por cerradas; H-09 amplía la frontera de tratamiento de PII sin contrato. No recomiendo diseñar un motor mayor: bastan adjudicaciones y correcciones mínimas en esta spec antes del plan.

## Preguntas y limitaciones

1. No se sondearon sistemas vivos ni se usaron datos reales; por contrato de revisión, las afirmaciones sobre efectos externos se contrastaron contra fuentes y código.
2. Git del repositorio hermano rechazó inicialmente el ownership del sandbox. Se obtuvo su commit con `git -c safe.directory=...` de alcance exclusivo al comando, sin modificar configuración; su worktree estaba limpio.
3. La reproducción de H-01 demuestra el lost update del manifest. No se provocó una carrera real sobre `_caso.md`, porque la misma forma read-modify-replace basta para identificar el riesgo y no era necesario tocar datos.
4. Queda para adjudicación decidir si Drive debe ser espejo versionado o lotes; el hallazgo no impone una arquitectura concreta, solo exige una semántica no contradictoria y sin pérdida.

## Veredicto

**NO SHIP** para pasar a plan TDD.

Resumen: **9 hallazgos — 2 críticos, 7 altos, 0 medios, 0 bajos.**
<!-- informe-literal:fin:qzvx -->

## 2. Evidencia verificada al adjudicar

La adjudicación se hizo contra la fuente y el código real, no contra el aplomo del informe.

| ID | Evidencia comprobada |
|---|---|
| H-01 | core/intake_manifest.py:181-194 guarda el estado en memoria con temp + os.replace sin lock/CAS; core/case_manager.py:1020-1062 declara expresamente «Sin lock, sin versionado»; core/intake_log.py:156-205 abre el JSONL en append sin coordinación interproceso. |
| H-02 | El repositorio hermano estaba en 89226262918f4ef1ca79f612b329c9f196c8f938. Su CLAUDE.md:13-16 y su diseño de 2026-07-31 §1-§3 asignan la captura a Marta, reservan al despacho la lista de referencias y niegan que el universo sea derivable; §§6.4, 10.2 y 11 exigen actor/cuenta, puerta humana y reverificación. scripts/medir.py:29-32,84-87,132-135 usa referencias fijas. |
| H-03 | core/intake_drive.py:202-230 retorna skipped=True ante .pulled correcto antes de construir o ejecutar rclone. |
| H-04 | core/config.py:529-537 excluye drive_ev de lotes y lo incluye en espejos; core/intake_drive.py:257-273 usa destino fijo y --inplace. |
| H-05 | El diseño de 2026-07-18 §3.2 y §7.4 imponía revisión previa; core/crm_ficha.py:27-80 solo exige nombre para contrario/colaboradores y scripts/crm_ficha.py:76-103 pasa de --yes a escrituras sin esquema de anclas. |
| H-06 | scripts/abrir_caso.py:265-305 registra el ID solo después de recibir respuesta, absorbe cualquier excepción y no reconcilia; :497-499 imprime después OK Caso abierto. |
| H-07 | scripts/abrir_caso.py:380 recibe float; core/abrir_caso.py:238-266 lo conserva y core/sudespacho_create.py:1245-1248,1439-1442 aplica int(round(...)). El atlas tipa los campos como Moneda, pero no prueba ida/vuelta de céntimos. |
| H-08 | Los artefactos existentes encontrados —manifest de intake, cobertura, catálogos y frontmatter— no comparten input_generation, prueba de consulta negativa ni ordinal de punto fijo. La rev. 1 condicionaba estado.json a un E2E posterior. |
| H-09 | docs/SEGURIDAD_DATOS.md:32-47 gobierna dato real, capturas y secretos, pero no una consulta postal externa. Un barrido de core/, scripts/ y tests/ no encontró adaptador postal; las apariciones eran documentación, anonimización o taxonomía. |

También se verificaron la rama codex/docs/apertura-integral-w02q38c, el commit
bedfc45dda942afd5c5df3b8ec95e6ce8a008b33 y el SHA-256 canónico del informe. El
repositorio hermano se consultó en solo lectura y no se mutó. No se consultaron ni
mutaron casos reales, Drive, Gmail, LeadHub o Sudespacho.
