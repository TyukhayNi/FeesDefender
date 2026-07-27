---
titulo: Revisión adversarial Codex — informe completo (vista procesal 05_Procedimiento)
fecha: 2026-07-27
revisor: Codex
spec: docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md
veredicto: NO SHIP
estado: abierto
adjudicacion: pendiente
handoff: docs/superpowers/handoffs/2026-07-27-vista-procesal-codex-review.md
---

> **Andamio efímero** (gobernanza §5). Texto **recibido de Codex por chat, sin modificar**.
> Codex trabajó en solo lectura (HEAD desacoplado) y no tocó el repo ni el expediente.
> El handoff resumido está en el fichero enlazado arriba. La adjudicación de cada hallazgo
> contra la fuente la hace Claude Code y se anota aparte.
>
> **Cautela de lectura registrada por Claude Code:** el informe declara «177 pruebas pasadas,
> 3 omitidas» como regresión del repositorio; la suite real tiene ~2213 funciones de test en 156
> ficheros, de modo que la cifra corresponde a un subconjunto, no a la suite. No invalida los
> hallazgos de lectura de código, pero nada que dependa de haber ejecutado la suite queda
> verificado por este informe.

## Veredicto

**NO SHIP.** La inspección del caso real confirma los números principales, pero también materializa los dos riesgos más graves: el manifiesto pierde identidades `doc_id` y contiene 31 entradas cuya ruta ya no existe. La vista no puede construirse con seguridad tomando ese manifiesto como fuente autoritativa.

Carpeta auditada, exclusivamente en lectura:

`CASO = C:\Users\tnm33\Desktop\BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Bad debt`

El spec se revisó desde la rama local `claude/intake-crm-sudespacho-a7fc5a` (`2955f65`); el código coincide con el `HEAD` auditado.

## Verificación empírica del caso piloto

| Premisa | Resultado | Evidencia |
|---|---:|---|
| Caso vinculado al expediente CRM 487 | **Confirmada** | `CASO\00_Input\_caso.md:9-15,112-116` |
| Documentos lógicos CRM | **70** | 70 `doc_ids` únicos en `_caso.md:14-85`; 70 eventos documentales en `_intake_log.jsonl:4-81` |
| Ficheros físicos en `00_Input/05_CRM` | **69** | Inventario directo y 69 entradas en `MANIFEST_CHECKOUT.json:1069-1341` |
| SHA-256 distintos | **61** | Hash de los 69 ficheros y cruce 69/69 con `_intake_log.jsonl:4-81` |
| Extensiones físicas | **65 PDF / 2 DOC / 2 RTF** | Inventario directo de `00_Input/05_CRM` |
| Duplicados físicos | **7 grupos: seis pares y un triplete** | Ocho copias físicas adicionales: `61 + 8 = 69` |
| Duplicado lógico sin segunda ruta | **Tasa: dos `doc_id`, un SHA y un path** | `doc_id` 39526 y 38060 en `_intake_log.jsonl:29,31`; entrada sin IDs en `_intake_hashes.json:102-105` |
| Reparto procesal 9/5/15/12/29 | **No verificable** | No existe `_mapa_procesal.yaml`; `05_Procedimiento` está vacío |
| Reparto CRM actual | **47 / 15 / 8 lógico; 46 / 15 / 8 físico** | `_caso.md:86-90` y árbol `05_CRM` |
| Último pull | **70 procesados, 0 fallos** | 62 `dedup_skipped`, 8 `cross_source_overlap`, 0 `documents_failed`: `_intake_log.jsonl:82-83` |
| Duración del pull | **Ventana observable de 110 s** | De `_intake_log.jsonl:1` a `:82`; no existe métrica de duración explícita |
| Sala de máquina | **No ejecutada** | `01_Procesado` tiene cero ficheros, tanto en el baseline como actualmente |
| Vista procesal | **No creada** | `05_Procedimiento` tiene cero ficheros |
| PDF sin texto extraíble | **7 de 65** | Barrido de las 438 páginas con `pypdf` |
| PDF con alguna página de menos de 40 caracteres | **19 de 65** | Barrido por página |
| PDF que pasa la heurística global pese a páginas deficitarias | **8 de 65** | Contraste con `core/extractor.py:125-137` |
| Ausencia de D01 | **Confirmada por nombres** | Ordinario en `_intake_log.jsonl:35-49`; monitorio en `:64-79`; cero coincidencias D01 normalizadas |
| Tamaño de los 65 PDF | **40.683.521 bytes / 38,80 MiB** | Inventario físico |
| Total de `05_CRM` | **42.094.319 bytes / 40,14 MiB** | Inventario físico |
| Copias físicas redundantes | **4.997.915 bytes / 4,77 MiB** | Diferencia por grupos SHA |
| Ruta proyectada con descripción de 60 caracteres | **Cabe en el piloto, por poco** | 248 caracteres con `D-99A` y `.docx`; 253 con fecha en la carpeta más larga |
| Fechas CRM `modified_at` | **No disponibles** | Cero apariciones en los controles del caso |

## Hallazgos

### H1 — La pérdida de identidad por SHA y path ocurre en el caso real

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §2.1, §2.2 y §4.2
- **Evidencia:** `CASO\00_Input\_intake_log.jsonl:29,31`; `CASO\00_Input\_intake_hashes.json:102-105`; `core/intake_manifest.py:291-321`; `core/sync_sudespacho.py:1310-1329`
- **Por qué falla:** los `doc_id` 39526 y 38060 tienen el mismo SHA y la misma ruta `05_CRM/99_Otros/tasa_ordinario.pdf`. La entrada del manifiesto tiene `aliases: []` y no guarda ninguno de los dos IDs. Por tanto, el segundo documento ya se pierde silenciosamente en el caso piloto y `sin_asignar` no puede denunciarlo.
- **Corrección propuesta:** separar objetos físicos por SHA de ocurrencias lógicas keyed por `(source, expediente_id, doc_id)`. Deben poder existir varias ocurrencias sobre el mismo SHA y path.

### H2 — Falta ámbito por expediente y no se persisten fechas CRM

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §2.1 y §2.2
- **Evidencia:** `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:102-110`; `core/sync_sudespacho.py:298-311,719-730,1527-1533`; `core/case_manager.py:76-109,1070-1092`; `CASO\00_Input\_caso.md:9-15`
- **Por qué falla:** el cambio descrito eleva `doc_id`, `source` y `modified_at`, pero omite `expediente_id`, aunque un caso admite varios expedientes. El caller CRM pasa `expediente_id`, pero no `modified_at`. En el caso real no existe ninguna aparición de `modified_at` o `fechamodificacion`, por lo que tampoco pueden verificarse fechas de lote u ordenar escritos por fecha CRM.
- **Corrección propuesta:** persistir por ocurrencia `{source, expediente_id, doc_id, modified_at, path, sha256}` y pasar `info.modified_at` desde el pull.

### H3 — El backfill prometido ya ha demostrado que no funciona

- **Severidad:** ALTA
- **Sección del spec:** §2.1
- **Evidencia:** `CASO\00_Input\_intake_log.jsonl:82-83`; `CASO\00_Input\_intake_hashes.json:1-13,102-105`; `core/intake_manifest.py:300-321`
- **Por qué falla:** el pull del 2026-07-27 procesó los 70 IDs con cero fallos, pero `_intake_hashes.json` sigue sin `doc_id` ni `expediente_id` en ninguna entrada canónica. Solo ocho aliases conservan IDs. El fichero ni siquiera fue reescrito: conserva fecha de modificación del 2026-06-12.
- **Corrección propuesta:** migración versionada y upsert de metadatos antes de los retornos `skip`, tanto para primary como para alias existente. Añadir una comprobación posterior que exija 70 ocurrencias resolubles.

### H4 — El manifiesto real contiene 31 entradas primarias inexistentes

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §2.2, §4.1 y §5
- **Evidencia:** `CASO\00_Input\_intake_hashes.json:22-28,397-400`; `CASO\00_Input\_caso.md:14-90`; `core/intake_manifest.py:166-178,207-243`
- **Por qué falla:** `_intake_hashes.json` contiene 92 SHA, pero solo 61 `primary_path` existen. Las otras 31 rutas están ausentes; varias contienen nombres como `Roser`/`W-030LFT`. `reconcile()` conserva expresamente entradas sin primary ni alias presente. El diseño pretende usar este manifiesto como fuente de “qué documentos existen”, aunque discrepa del pull state de 70 IDs y del disco.
- **Corrección propuesta:** abortar si el manifiesto no concuerda con `pull_state.doc_ids`, total CRM y disco. Separar histórico/superseded de ocurrencias activas; una ruta ausente no puede seguir formando parte del conjunto autoritativo.

### H5 — Un manifiesto corrupto puede convertirse silenciosamente en expediente vacío

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §2.2 y §5
- **Evidencia:** `core/intake_manifest.py:166-178`; `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:276-285,335-351`
- **Por qué falla:** JSON inválido, I/O fallido o esquema incorrecto se transforma en `{}`. Con YAML vacío y ledger anterior, `sin_asignar` puede quedar vacío y las entradas CRM del ledger clasificarse como `borrar`.
- **Corrección propuesta:** manifiesto ausente, corrupto o de versión desconocida debe ser una puerta bloqueante, nunca “cero documentos”.

### H6 — El ledger no protege un fichero sustituido manualmente

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §4.1 y §5
- **Evidencia:** `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:280-303,337-351`
- **Por qué falla:** si el ledger registra `P` con SHA `A`, pero el letrado sustituye `P` por un escrito `B`, `apply()` seguiría autorizado a borrar, mover o sobrescribir `P` por figurar en el ledger. También falta una puerta para un fichero ajeno que ya ocupe el nombre canónico.
- **Corrección propuesta:** antes de toda operación destructiva, verificar que el SHA actual coincide con el SHA previo del ledger. Toda divergencia o destino ajeno existente debe abortar.

### H7 — El mapping carece de validación de ruta y unicidad lógica

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §3 y §5
- **Evidencia:** `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:242-269,335-353`
- **Por qué falla:** no se validan `orden`, `descripcion` ni `despacho.fichero`. Traversal, nombres reservados Windows, puntos/espacios finales y colisiones `casefold()` pueden escapar o colisionar. Tampoco hay puerta para repetir `crm:<doc_id>` o `despacho:<fichero>`.
- **Corrección propuesta:** carpetas en whitelist, `fichero` como basename, contención absoluta, rechazo de reparse points y colisión con normalización Windows.

### H8 — `apply()` no tiene semántica transaccional

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §4.1 y §5
- **Evidencia:** `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:276-303,335-353`
- **Por qué falla:** el spec no define recuperación ante disco lleno, ACL, antivirus, ruta larga o fallo al escribir el ledger. Un error tras varias copias/movimientos deja disco y ledger en generaciones distintas.
- **Corrección propuesta:** staging en el mismo volumen, verificación SHA, reemplazos atómicos, borrados al final y ledger atómico como último commit. Diff vacío implica cero escrituras.

### H9 — La sala de máquina no ha corrido en el piloto y el diseño solo avisa

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §2.4 y §5
- **Evidencia:** `CASO\MANIFEST_CHECKOUT.json:2-4`; inventario de `CASO\01_Procesado` con cero ficheros; `scripts/sala_maquina.py:124-159`; `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:206-209`
- **Por qué falla:** el caso real no tiene `02_Sala de máquina`, OCR, MD ni cobertura. Si se construye ahora la vista, todo se copiaría desde crudo: incluidos siete PDF sin texto extraíble y los dos `.doc`. El spec permite continuar con un aviso, pese a que el resultado incumple el objetivo de buscabilidad.
- **Corrección propuesta:** gate por documento y SHA. Bloquear entradas soportadas sin cobertura vigente, salvo override explícito que registre “crudo no buscable”.

### H10 — La existencia de artefactos no es una fuente fiable de estado

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §2.4
- **Evidencia:** `core/sala_maquina.py:455-482`; `scripts/sala_maquina.py:25-35,83-98`; `core/sala_maquina.py:135-153`
- **Por qué falla:** un OCR borrado, una extracción por visión o un estado SHA obsoleto pueden dejar MD sin PDF buscable. La rama 2 interpretaría “no hay OCR” como “el crudo ya tenía texto”.
- **Corrección propuesta:** resolver desde `_cobertura.json`, verificando `rel_path`, SHA de origen, método, artefacto esperado y SHA del artefacto existente.

### H11 — Los bundles no siempre tienen `03_MD/<slug-físico>.md`

- **Severidad:** ALTA
- **Sección del spec:** §2.4
- **Evidencia:** `core/sala_maquina.py:403-436`; `scripts/sala_maquina.py:39-52`; `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:181-186`
- **Por qué falla:** un bundle genera MD por segmento, no necesariamente un MD padre. Si cambia el path conservando SHA, el estado puede saltar el reprocesado mientras el slug derivado cambia.
- **Corrección propuesta:** resolver y agrupar por `parent_sha256`/`rel_path` desde cobertura estructurada; usar la peor calidad de los segmentos.

### H12 — La heurística global falla en ocho PDF reales del piloto

- **Severidad:** ALTA
- **Sección del spec:** §2.4
- **Evidencia:** `core/extractor.py:125-137`; `core/sala_maquina.py:511-521`; barrido de 438 páginas bajo `CASO\00_Input\05_CRM`
- **Por qué falla:** 8 de los 65 PDF superan los 100 caracteres y 40 caracteres/página de media, pero contienen páginas con menos de 40 caracteres. Cinco tienen al menos una página completamente vacía. Dos escrituras de compraventa de 74 páginas pasan la heurística aunque 38 páginas de cada una quedan por debajo del umbral.
- **Corrección propuesta:** detectar texto por página y OCRizar o advertir páginas deficitarias. Si no se implementa, retirar la promesa de buscabilidad completa.

### H13 — La regla propuesta tergiversa en su aplicación el criterio cerrado

- **Severidad:** ALTA
- **Sección del spec:** §2.4
- **Evidencia:** `docs/MEJORAS_FUTURAS.md:2915-2925`; `core/sala_maquina.py:522-539`; `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:161-179`
- **Por qué falla:** un `.eml` acabaría como crudo en vez de MD atomizado más adjuntos; toda imagen pasa hoy por PDF/OCR aunque el criterio exige crudo para fotografía. El ledger tampoco conserva la procedencia doble exigida.
- **Corrección propuesta:** selector explícito por clase documental y ledger con `raw_sha256`, `copied_sha256`, `derived_from` y método. El piloto no contiene imágenes ni EML, pero el fallo permanece en el diseño general.

### H14 — No universalizar `01_OCR` es correcto, pero no por “pérdida de custodia”

- **Severidad:** MEDIA
- **Sección del spec:** §2.4
- **Evidencia:** `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:188-194`; `docs/MEJORAS_FUTURAS.md:2923-2925`
- **Por qué falla:** universalizar alteraría la semántica de `01_OCR`, pero no destruiría la custodia si se conservan original y hashes. El argumento de formatos nativos y riesgo de conversión sí es sólido. En el piloto, duplicar los 65 PDF supone como mínimo otros 40.683.521 bytes; el tamaño OCR real no puede saberse aún.
- **Corrección propuesta:** mantener la decisión, justificándola por semántica, fidelidad y coste; usar cobertura como índice universal.

### H15 — La transición raw→OCR/LibreOffice no define reemplazo ni extensión

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §2.4, §3 y §4.1
- **Evidencia:** `CASO\00_Input\_intake_log.jsonl:35`; `PLAN.md:64-79`; `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:178-215,251-267`
- **Por qué falla:** la demanda ordinaria central está efectivamente solo en `.doc` (`doc_id=36797`). Cuando LibreOffice genere PDF, el spec no decide si conservar `.doc`, crear `.pdf`, retirar el anterior o cómo mantener idempotencia.
- **Corrección propuesta:** acción atómica `reemplazar` por `crm:<doc_id>`, extensión real del artefacto, verificación SHA y retirada segura del destino anterior.

### H16 — Mapa, ledger y ficheros no forman una unidad atómica en checkin

- **Severidad:** BLOQUEANTE
- **Sección del spec:** §8.4
- **Evidencia:** `core/repository_checkout.py:370-389,408-439`; `scripts/repository_cli.py:496-543,584-602`; `CASO\00_Input\_caso.md:118-123`
- **Por qué falla:** el caso está actualmente `prestado`. El merge puede subir un ledger `COPY_LOCAL` aunque el mapa tenga conflicto, o resucitar un derivado borrado en Drive porque `D is None` produce `COPY_LOCAL`.
- **Corrección propuesta:** grupo de dependencia mapa+ledger+ficheros; conflicto de uno bloquea la subida de todos. `Drive ausente + baseline presente` debe ser conflicto.

### H17 — `documents_written: 0` no significa que la corrida no escribiera bytes

- **Severidad:** MEDIA
- **Sección del spec:** §2.1 y §9
- **Evidencia:** `CASO\00_Input\_intake_log.jsonl:3,45,59,66,68,70,72,74,76,82-83`; `CASO\00_Input\_caso.md:118-123`
- **Por qué falla:** durante el checkout, los ocho `cross_source_overlap` se materializaron en `_pendiente_checkin`: ocho PDF y 4.997.915 bytes, aunque la métrica final dice `documents_written: 0`. Todos son byte-idénticos a ficheros ya presentes en `05_CRM`.
- **Corrección propuesta:** registrar separadamente `physical_files_written`, `overlap_copies_written` y `bytes_written`. No usar `documents_written: 0` como prueba de corrida sin efectos.

### H18 — `_index.md` y `registrar()` no soportan reconciliación

- **Severidad:** ALTA
- **Sección del spec:** §2.3
- **Evidencia:** `.claude/skills/_shared/registrar_outputs.py:70-77,116-145,160-173,192-221`; `core/config.py:391-410`
- **Por qué falla:** el helper solo añade filas por filename; mover o borrar deja filas fantasma. El `registrar()` completo también añade wikilinks a `_caso.md`. `_index.md` sería además un multiwriter sometido a merge por hash completo.
- **Corrección propuesta:** reconciliador puro de filas `CRM:<doc_id>`, sin tocar navegación, y bloques de propiedad diferenciados para CRM y despacho.

### H19 — El piloto cabe con descripción de 60, pero no existe garantía general de `MAX_PATH`

- **Severidad:** ALTA
- **Sección del spec:** §3 y §5
- **Evidencia:** `core/abrir_caso.py:27-33`; `core/utils.py:111-135`; inventario de rutas de `CASO`
- **Por qué falla:** bajo la raíz `G:\Unidades compartidas\...\CASOS\Barcelona`, el piloto produciría 248 caracteres con `D-99A_<60>.docx` y 253 con una fecha colocada en la carpeta más larga: cabe, pero deja seis caracteres de margen frente a 259. El spec no fija 60 ni limita `case_id` u `orden`. Además, el expediente ya contiene una ruta local de 301 caracteres, equivalente a 346 bajo la raíz G, por lo que la cadena de herramientas ya depende de soporte de rutas largas.
- **Corrección propuesta:** preflight dinámico de cada ruta absoluta y segmento, con truncado hash estable. No depender de un límite fijo solo para `descripcion`.

### H20 — El impacto en skills sigue incompleto y sobredimensionado

- **Severidad:** MEDIA
- **Sección del spec:** §8
- **Evidencia:** `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:427-479`; `.claude/skills/contestacion-honorarios-art20-lau/SKILL.md:125-132,238-241`; `.claude/skills/oposicion-alegacion-nulidad/SKILL.md:98-112`; `.claude/skills/engel-volkers/SKILL.md:175-186`
- **Por qué falla:** las secciones suman doce skills, no nueve. Dos skills procesales leen demanda/documental sin rutas deterministas y no son meras sincronizaciones de helper. `engel-volkers` solo enumera raíces y no necesita replicar el árbol interno.
- **Corrección propuesta:** matriz por rutas leídas, destino escrito, handoff y helper; reclasificar las dos procesales y no tocar `engel-volkers`.

### H21 — La exclusión de procesales de la sala de lectura no es operativa

- **Severidad:** ALTA
- **Sección del spec:** §7 y §8.1
- **Evidencia:** `.claude/skills/organizar-sala-lectura/SKILL.md:64-72,178-183,494-507`; `.claude/skills/organizar-sala-maquina/SKILL.md:137-142`
- **Por qué falla:** la skill lee todo `00_Input`. El spec no define cómo identificar los documentos procesales ni retirar copias previas sin afectar otros outputs.
- **Corrección propuesta:** excluir por las ocurrencias y SHA crudos del mapa/manifiesto y limpiar solo derivados cuya trazabilidad acredite propiedad.

### H22 — “62 de 70 nuevos hashes” es una lectura errónea de la métrica real

- **Severidad:** MEDIA
- **Sección del spec:** §1.1, §2.1 y §4.2
- **Evidencia:** `CASO\00_Input\_intake_log.jsonl:82`; `CASO\00_Input\_caso.md:14-90`; `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:94-97,305-320`
- **Por qué falla:** están confirmados 70 IDs, 69 paths y 61 hashes. El `62` del pull significa `documents_skipped_dedup`; no “62 hashes nuevos”. Hubo 62 skips normales y 8 overlaps. Las primeras altas posibles por contenido son 61.
- **Corrección propuesta:** cambiar `62 de 70` por `61 SHA distintos` y explicar separadamente `62 dedup_skipped + 8 overlap` en esta corrida idempotente.

### H23 — El reparto 9/5/15/12/29 sigue sin fuente reproducible

- **Severidad:** MEDIA
- **Sección del spec:** §1.1 y §4.2
- **Evidencia:** `CASO\00_Input\_caso.md:86-90`; inventario vacío de `CASO\05_Procedimiento`
- **Por qué falla:** el árbol solo acredita el reparto CRM 47/15/8. No existe mapa procesal ni otro control que permita reproducir 9/5/15/12/29.
- **Corrección propuesta:** incorporar el YAML completo o un fixture anonimizado con los 70 IDs antes de aceptar el reparto como verificado.

### H24 — La promoción `.doc` es correcta, pero queda un puntero roído

- **Severidad:** BAJA
- **Sección del spec:** §2.4 y §9
- **Evidencia:** `CLAUDE.md:50-55`; `docs/MEJORAS_FUTURAS.md:2458-2468`; `PLAN.md:27,59-82,181-183`
- **Por qué falla:** marca, cola y disparador están bien, y el caso confirma el disparador `.doc`. Sin embargo, `PLAN.md` sigue incluyendo `.doc/soffice` dentro de “Backlog (no promovidos)” para todo #61.
- **Corrección propuesta:** “resto no promovido de #61” y referirse al “punto `.doc` de #61”.

### H25 — “El core solo lee” y “falta auth de escritura” son demasiado amplios

- **Severidad:** BAJA
- **Sección del spec:** §7 y §9
- **Evidencia:** `docs/CRM_SUDESPACHO_ATLAS.md:507-532,965`; `core/sync_sudespacho.py:626-684,815-847`; `core/sudespacho_create.py:1462-1489,1620-1645`; `core/sudespacho_relations.py:648-690`
- **Por qué falla:** el cliente documental solo lee, pero otros módulos de `core` ya escriben con `x-api-key`. Lo ausente es el flujo documental concreto, no la autenticación REST general.
- **Corrección propuesta:** reformular y verificar en entorno controlado payload, presigned upload, importación, carpeta, permisos e idempotencia.

## Premisas del spec que NO he podido verificar

- El reparto procesal 9/5/15/12/29: no existe aún `_mapa_procesal.yaml`.
- Las fechas CRM de modificación/presentación y los lotes: no se persisten en los controles locales.
- La duración contractual exacta del pull: solo hay una ventana observable de eventos de 110 segundos.
- La existencia de bundles según el detector de sala de máquina: no hay manifiestos de segmentación ni sala procesada.
- El tamaño de los futuros PDF OCR: solo puede calcularse el mínimo basado en los 38,80 MiB de PDF crudos.
- La operatividad viva de los endpoints de subida documental y sus permisos: no se realizaron escrituras externas.
- La futura conversión LibreOffice y el comportamiento del aún inexistente `core/procedimiento.py`.

## Lo que he comprobado y está bien

- El caso está correctamente vinculado al expediente judicial CRM 487.
- Están confirmados **70 documentos lógicos, 69 ficheros físicos y 61 SHA distintos**.
- Están confirmadas las extensiones **65 PDF, 2 DOC y 2 RTF**.
- Los siete grupos físicamente repetidos y el duplicado lógico de la tasa están identificados.
- Está confirmada por nombres la ausencia de D01 en monitorio y ordinario, sin poder concluir la causa.
- El último pull terminó con cero errores y cero documentos fallidos.
- `inventariar()` recorre todo `00_Input`; `output_slug` y la ruta ordinaria de OCR están descritos correctamente en el spec.
- `.doc` cae actualmente en `sin_soporte`; el caso contiene los dos `.doc` indicados, incluida la demanda ordinaria.
- La decisión de no universalizar `01_OCR` sigue siendo correcta, con la justificación corregida.
- Los tres endpoints están inventariados en el atlas.
- La promoción del punto `.doc` cumple la regla formal.
- Las siete copias de `registrar_outputs.py` siguen byte-idénticas.
- La regresión del repositorio ya verificada dio **177 pruebas pasadas y 3 omitidas por marca `lento`**.
- La auditoría del caso no alteró datos: los **337 ficheros del baseline** siguen presentes con MD5 idéntico, cero ausentes y cero divergencias.
- No existe ninguna escritura posterior al pull preexistente de las 09:28:23.
- El repositorio permanece limpio: `git status` muestra únicamente `## HEAD (no branch)`.
