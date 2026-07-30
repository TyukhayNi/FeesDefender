---
tipo: handoff
estado: consumido
creado: 2026-07-27
origen: revisión adversarial de Codex (chat, solo lectura) — 2ª pasada sobre el spec v3.1, commit `972da2d`
destino: sesión Claude Code — adjudicar los 6 hallazgos nuevos (N1-N6) y decidir el reparto del trabajo
consumido_por: "PR #137 (`12c8a91`): los 6 se aceptaron en sustancia. N6 se arregló en el propio PR (`core/repository_checkout.py`); el resto se repartió en las cuatro piezas del bloque `[SIGUIENTE-VISTA-PROCESAL]` de `PLAN.md` — N1 → pieza 2 (PR #140, `86e3abd`), N3 → pieza 3 (aún abierta) — y en el spec v3.1 (el `eco_crm` de N5, en §1.1)."
titulo: Revisión adversarial 2ª pasada — vista procesal 05_Procedimiento v3.1
revisor: Codex
spec: docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md
commit_revisado: 972da2d
veredicto: NO SHIP
pasada_anterior: docs/superpowers/handoffs/2026-07-27-vista-procesal-codex-informe.md
---

> **Andamio efímero** (gobernanza §5). Texto **recibido de Codex por chat, sin modificar**.
> Trabajó en solo lectura y no modificó el repo.
>
> **Nota de Claude Code:** esta pasada **sí ejecutó la suite completa** —2290 passed, 0 failed,
> 76 skipped en 141 s, con el comando a la vista—, a diferencia de la primera, que reportó un 8%
> como si fuera la regresión del repositorio. La verificación de esta pasada es fiable en ese eje.
> Balance de cierre de la pasada anterior: 17 resueltos, 7 a medias, 1 solo mencionado.

## Veredicto

**NO SHIP.** La opción B es coherente, pero el contrato de ocurrencias no puede conservar su propio histórico y quedan agujeros bloqueantes en el intake acotado, la cobertura, `eco_crm` y el checkin del grupo.

La v3.1 revisada corresponde al commit `972da2d`. `core/`, `scripts/`, `tests/`, `.claude/` y `pyproject.toml` son idénticos entre ese commit y el worktree auditado.

## Estado de la suite

Suite completa ejecutada. Para no escribir `.pytest_cache` y dirigir los temporales fuera del repo se añadieron dos opciones neutras:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe -m pytest -q --tb=no -p no:cacheprovider --basetemp <tmp>
```

Resultado: `exit code 0`, suite completa. Como `pyproject.toml:11` ya añade `-q`, esa invocación efectiva queda en `-qq` y pytest suprime el total numérico.

Corrida completa equivalente para obtener el recuento explícito (`-o "addopts=-ra"`):

```text
2290 passed, 0 failed, 76 skipped in 141.21s (0:02:21)
```

No fue necesario repetir con `-p no:randomly`: no hubo fallos. `git status --short` quedó vacío después de las pruebas.

### Tests que tocaría el diseño

- `tests/test_pull_expediente_v2.py`: debe comprobar la escritura de `_ocurrencias_crm.json` en altas, dedup, overlap, re-pull, error parcial y cambio de contenido.
- `tests/test_judicial_intake.py`: el caso acotado de `:240-258` debe distinguir documentos listados en CRM de documentos materializados.
- Nuevo `tests/test_ocurrencias_crm.py`: identidad, expedientes múltiples, revisiones, corrupción, escritura atómica e histórico.
- Nuevo `tests/test_procedimiento.py`: mapa, `eco_crm`, cobertura, gates, diff, apply, ledger e índice.
- `tests/test_sala_maquina.py` y `tests/test_sala_maquina_ejecutar.py`: esquema versionado de cobertura, hash del artefacto y todos los métodos/estados alcanzables.
- `tests/test_repository_checkout.py` y `tests/test_repository_cli.py`: grupo indivisible, veto previo a copiar y borrado remoto de derivados.
- `tests/test_skill_registrar_outputs.py`: cinco destinos procesales válidos.
- `tests/test_skill_helpers_sync.py`: no necesita cambiar su lógica, pero debe seguir fallando hasta que la copia canónica y las siete bundleadas estén sincronizadas.

## Cierre de los 25 hallazgos anteriores

`S` = el spec en `972da2d`. Balance: **17 resueltos, 7 a medias y 1 solo mencionado**.

| ID | Estado | Evidencia |
|---|---|---|
| H1 | Resuelto | `S:135-193` separa identidad lógica por expediente y `doc_id`, permitiendo SHA y rutas compartidos. |
| H2 | Resuelto | `S:151-180,192-193` incorpora `expediente_id`, `modified_at`, ruta, SHA e `id_carpeta`; esos datos existen en el punto del pull. |
| H3 | Resuelto | `S:135-149,180-193` elimina el backfill del manifiesto mediante la opción B. |
| H4 | Resuelto | `S:185-193` saca el manifiesto de la ruta de confianza de la vista. |
| H5 | Resuelto | `S:441-442` bloquea registro ausente, corrupto o de versión desconocida. |
| H6 | Resuelto | `S:399-409,463-471` exige el SHA previo del destino y protege ficheros ajenos o modificados manualmente. |
| H7 | Resuelto | `S:342-357` cubre whitelist, basename, traversal, reservados, `casefold`, reparse points y longitud. |
| H8 | A medias | `S:391-397` define staging, verificación, atómicos, borrados al final y ledger último. Pero tras un fallo parcial el ledger viejo hace que las puertas 10–13 **bloqueen** la supuesta reconciliación por reejecución de `plan`. El journal está aceptadamente fuera de v1; falta un procedimiento determinista real. |
| H9 | Resuelto | `S:297-300,447-448,692-695` bloquea cobertura ausente y registra el override. |
| H10 | A medias | `S:237-260` usa correctamente `_cobertura.json`, pero solo comprueba que el OCR **exista**: no dispone del SHA esperado del artefacto. |
| H11 | Resuelto | `S:263-265` resuelve bundles por `parent_sha256` y aplica la peor calidad. |
| H12 | Resuelto | `S:267-272,615-617` limita honestamente la promesa a suficiencia global y separa la detección por página. |
| H13 | A medias | `S:245-256` introduce selector por clase, pero no cubre todos los métodos, extensiones y estados alcanzables; ver N4. |
| H14 | Resuelto | `S:277-282` mantiene el OCR no universal con justificación semántica, de fidelidad y coste. |
| H15 | Resuelto | `S:290-295,381-409` define `reemplazar`, extensión real y procedencia doble. |
| H16 | A medias | `S:584-595` declara el grupo, pero no diseña cómo representarlo ni impedir que el CLI suba sus miembros antes de evaluar conflictos; ver N6. |
| H17 | Solo mencionado | `S:618-621` lo remite a mejoras futuras; el contrato de métricas del pull no se corrige en v1. |
| H18 | Resuelto | `S:203-223` diseña un reconciliador propio de filas CRM que preserva el bloque manual. |
| H19 | A medias | `S:342-368` exige preflight dinámico y truncado estable, pero no define de dónde sale el límite efectivo aplicable a Windows, Drive y consumidores. |
| H20 | A medias | `S:548-582` corrige las dos reclasificaciones y excluye correctamente `engel-volkers`, pero afirma «doce skills»: la unión del propio listado contiene **nueve** skills únicas. |
| H21 | Resuelto | `S:543-546,554-566` convierte la exclusión en operativa por ocurrencia/SHA y exige trazabilidad antes de retirar derivados. |
| H22 | Resuelto | `S:118-121` corrige documentos lógicos, rutas físicas, SHA y significado de las métricas. |
| H23 | A medias | `S:506-507,687-691` retira la falsa afirmación de reproducibilidad, pero el fixture sigue sin existir. |
| H24 | Resuelto | El artefacto que originaba el hallazgo fue retirado del alcance de esta revisión. |
| H25 | Resuelto | `S:529-534` acota la carencia al flujo documental de escritura, no a toda autenticación ni a todo `core`. |

## Hallazgos nuevos

### N1 — El esquema de ocurrencias no puede conservar el histórico que exige

- **Severidad:** BLOQUEANTE · **Sección:** §2.1
- **Evidencia:** `spec:151-181`; `core/sync_sudespacho.py:689-731`
- **Escenario:** `ocurrencias` es un objeto cuya única clave permitida es `crm:<expediente_id>:<doc_id>`. Cuando cambia el contenido del documento, esa misma clave no puede contener simultáneamente la revisión `active` y la anterior `superseded`. Sobrescribirla pierde el histórico. Además, el listado CRM devuelve un único snapshot por documento: reconstruir el registro desde cero **no puede regenerar revisiones antiguas**.
- **Corrección:** definir por clave lógica `{active_revision, revisions: [...]}`, o una colección de revisiones con identificador propio. Aclarar que el snapshot vigente es regenerable pero el histórico no, salvo que exista un endpoint CRM de revisiones. La actualización debe preservar las revisiones locales y escribirse atómicamente.

### N2 — El intake acotado deja documentos fuera del universo de integridad

- **Severidad:** BLOQUEANTE · **Sección:** §1.1(b), §2.1, §4.1 y §5
- **Evidencia:** `spec:84-86,173-185,373-375,441-448`; `core/sync_sudespacho.py:1433-1454,1508-1518,1578-1596`; `tests/test_judicial_intake.py:240-258`; `tests/test_pull_expediente_v2.py:604-625`
- **Escenario:** el pull lista tres documentos, filtra a dos mediante `only_doc_ids` y solo añade al `pull_state` los descargados con éxito. Si las ocurrencias se escriben en ese mismo bucle, registro y `pull_state.doc_ids` **concuerdan perfectamente aunque el tercer documento sea invisible**. Tampoco puede declararse `eco_crm` para un documento propio que deliberadamente no se descargó. Un fallo de descarga produce el mismo agujero: `documents_total_crm=2`, `doc_ids=1`, y ninguna puerta aborta por el error o la cardinalidad.
- **Corrección:** separar `listed_doc_ids` del snapshot CRM y `materialized_doc_ids`. Crear una ocurrencia de estado `listed` para todo documento enumerado, **antes del filtro**, y completar ruta/SHA al materializar. La integridad debe exigir `documents_total_crm == len(unique(listed_doc_ids))`, cero errores pendientes y una decisión explícita para cada listado: materializado, eco versionado o exclusión admitida. Si se quiere garantizar solo el subconjunto materializado, hay que **retirar o acotar expresamente la garantía de completitud**.

### N3 — `_cobertura.json` no autentica el artefacto OCR que se va a copiar

- **Severidad:** BLOQUEANTE · **Sección:** §2.4 y puerta 5
- **Evidencia:** `spec:237-260`; `core/sala_maquina.py:118-132,455-462`; `scripts/sala_maquina.py:47-52`
- **Escenario:** `DocCobertura` persiste el SHA del **origen**, pero no `artifact_path`, `artifact_sha256` ni tamaño del OCR. Si el PDF de `01_OCR` se sustituye o corrompe, el origen y su cobertura siguen cuadrando y la verificación `exists()` acepta el artefacto equivocado. El ledger calcularía y **legitimaría** el SHA del fichero ya sustituido, porque carece de un hash esperado producido por la sala de máquina.
- **Corrección:** versionar el envelope de cobertura y persistir `artifact_path`, `artifact_sha256`, tamaño y estado de materialización. Verificar hash, contención, fichero regular y ausencia de reparse point antes de copiar. Escribir `_cobertura.json` mediante temporal y `os.replace`, no con `write_text` directo.

### N4 — El selector documental no es total ni determinista

- **Severidad:** ALTA · **Sección:** §2.4
- **Evidencia:** `spec:240-256`; `core/sala_maquina.py:27-40,458-473,522-543`; `tests/test_sala_maquina_ejecutar.py:638-690`
- **Escenario:** el código produce `metodo: vision`, que el spec ni incluye entre los métodos persistidos. También alcanza `metodo: error`, sin fila. La clase nativa incluye `.md`, `.ics`, `.csv`, `.xlsx`, `.xls`, `.html` y `.htm`, ausentes del selector. Y una imagen con `metodo: ocr, estado: empty` **casa simultáneamente** las filas «OCR → artefacto» e «imagen sin texto → crudo».
- **Corrección:** sustituir la tabla por una matriz ordenada y exhaustiva sobre `(ruta/clase, extensión, metodo, estado, artifact_verified)`. Incluir `vision`, `error` y todas las extensiones de `_EXTS_NATIVO`; definir prioridad entre filas y hacer que cualquier combinación desconocida bloquee.

### N5 — `eco_crm` no es único ni queda ligado a una versión del documento

- **Severidad:** BLOQUEANTE · **Sección:** §1.1(a), §3, §3.1 y puerta 7-bis
- **Evidencia:** `spec:76-82,317-357,441-456`
- **Escenario:** dos entradas `despacho` tienen claves lógicas distintas y pueden declarar el **mismo** `eco_crm`; ninguna validación lo prohíbe. Si el contenido del `doc_id` cambia en CRM, la nueva ocurrencia activa sigue quedando suprimida como eco aunque ya no sea la copia del fichero propio declarado. Tampoco se fijan tipos estrictos: un YAML con `sin_cobertura_ok: "false"` no está expresamente prohibido.
- **Corrección:** exigir unicidad de `eco_crm` dentro del expediente y ligarlo a una revisión concreta (`eco_modified_at` o `eco_revision`), obligando a reconfirmar si cambia. Validar que `eco_crm` sea un `doc_id` escalar del expediente y que `sin_cobertura_ok` sea literalmente el booleano `true`.
- **Lo que sí está bien:** otro expediente queda bloqueado por la puerta 7-bis; un eco puede y debe seguir figurando en `pull_state`; y asignarlo simultáneamente como entrada CRM ya está prohibido.

### N6 — La biblioteca sube miembros del grupo antes de evaluar el conflicto

- **Severidad:** BLOQUEANTE · **Sección:** §8.5
- **Evidencia:** `spec:584-595`; `core/config.py:391-410`; `core/repository_checkout.py:275-283,350-397,370-389`; `scripts/repository_cli.py:516-544,584-602`
- **Escenario:** el mapa diverge entre local y Drive y recibe `CONFLICT`; ledger y PDF nuevos reciben `COPY_LOCAL`. `cmd_checkin` ejecuta la copia en `scripts/repository_cli.py:529-544` y **solo después**, en `:584-602`, evalúa los conflictos. El Drive termina con mapa antiguo y derivados nuevos. También se resucita un derivado borrado remotamente: la rama `D is None` devuelve `COPY_LOCAL` sin comprobar que existía en el baseline. Un cambio solo en el mapa de Drive es peor: recibe `PRESERVE_DRIVE`, no conflicto, y los derivados locales antiguos pueden subirse.
- **Corrección:** representar explícitamente el grupo y postprocesar el plan **antes de cualquier `rclone copy`**. Cualquier mapa no idéntico al usado para generar los outputs debe vetar todo el grupo. Corregir la rama derivada `D=None, B!=None` a conflicto. El ledger debe fijar al menos `map_sha256`, `coverage_sha256` y `occurrences_sha256`. `_ocurrencias_crm.json` está bien clasificado como derivado, pero es un **input upstream** de la vista: debe quedar versionado y enlazado, no tratarse como otro output publicable.

## Premisas que NO he podido verificar

- `core/ocurrencias_crm.py` y `core/procedimiento.py` todavía no existen: solo puede verificarse la implementabilidad del contrato.
- No se llamó al CRM en vivo. Se comprobó que el DTO y el punto del pull **disponen** de los campos, no que todos lleguen siempre con valor no nulo.
- No se reabrió el expediente del piloto ni se revalidaron sus cifras en esta pasada.
- El fixture anonimizado de los 70 documentos no existe.
- El spec no identifica una fuente única del límite efectivo de ruta aplicable a toda la cadena Windows–Drive–consumidores.

## Lo que he comprobado y está bien

1. En el punto de escritura propuesto del pull están disponibles todos los datos requeridos: `doc_id`, `filename`, `id_carpeta` y `modified_at` (`core/sync_sudespacho.py:283-311,663-731`); `expediente_id` (argumento, `:1341-1350`); SHA y ruta relativa final (`:1520-1533`). **`modified_at` e `id_carpeta` son nullable** según el DTO; el nuevo contrato debe conservar esa posibilidad.
2. **No hay ningún consumidor vigente que necesite resolver `doc_id → ruta` desde `_intake_hashes.json`.** Los actuales usan SHA, paths, aliases o `message_id`: `core/email_export.py:997-999`, `core/whatsapp_intake.py:78-80,164-170`, `scripts/migrate_05crm_buckets.py:212-218`. La opción B no deja un consumidor atrás.
3. `_cobertura.json` sí persiste vía `asdict` los campos enumerados, y `cobertura_desde_dicts` ignora claves desconocidas: `core/sala_maquina.py:118-132,226-239`.
4. Se escribe en `01_Procesado/02_Sala de máquina/_cobertura.json` (`core/sala_maquina.py:261-262`, `scripts/sala_maquina.py:39-52`), después de ejecutar y fusionar (`scripts/sala_maquina.py:165-180`); no se escribe si falla antes el preflight, el plan o una excepción global.
5. La derivación nominal del OCR es correcta: `output_slug` (`core/utils.py:57-69`) → `01_Procesado/02_Sala de máquina/01_OCR/<slug>.pdf` (`core/sala_maquina.py:446-457`).
6. Está confirmado que **`metodo: ocr` sin artefacto es alcanzable** cuando OCRmyPDF falla: `core/sala_maquina.py:458-462`, `tests/test_sala_maquina_ejecutar.py:668-690`.
7. La clasificación conceptual de merge es correcta en lo básico (mapa maestro; ledger y ocurrencias derivados; ninguno en `MERGE_EXCLUSIONS`). El defecto está en la ejecución por fichero y en la ausencia de dependencias, no en las etiquetas.
8. `escritos-judiciales` tiene un lugar natural para la pregunta (Fase 0 y «Guardado y registro»), pero hoy solo pregunta destino en modo ad-hoc y sigue enviando los procesales a la raíz: `.claude/skills/escritos-judiciales/SKILL.md:17-36`. El cambio descrito por el spec es necesario.
9. Ampliar `DESTINOS_VALIDOS` con las cinco rutas exactas basta para que `_validar_destino` las acepte y cree su `_index.md`: `.claude/skills/_shared/registrar_outputs.py:43-63,99-145`. No hace que la skill pregunte ni mueve el `.docx`.
10. El repositorio no fue modificado durante la revisión.
