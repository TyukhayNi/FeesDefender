# Diseño — Vista procesal del expediente en `05_Procedimiento`

_Brainstorming Claude Code · FeesDefender · 2026-07-27_
_Origen: petición de Nikolai sobre el expediente judicial CRM **487** (caso `W-02MA0R`) —
«que en Procedimiento acabe la demanda de monitorio con documentos en una carpeta, en otra la
contestación al monitorio, en otra la demanda de juicio ordinario con documentos, en otro
contestación y en otra el resto de los escritos»._
_Precedentes: `docs/INTEGRACION_SUDESPACHO.md` §13 (árbol `05_CRM`), `PLAN.md`
`[SIGUIENTE-REORG-05CRM]` (buckets planos D5/D6), `core/intake_manifest.py` (dedup M9)._

## 0. Estado de las decisiones (cerradas con Nikolai, 2026-07-27)

| Decisión | Resuelto |
|---|---|
| **Alcance** | Herramienta **reutilizable** en `core/` + CLI `plan`/`apply` + tests. No script puntual, no skill |
| **Dónde se construye la vista** | Solo en `05_Procedimiento`. **`00_Input/05_CRM` no se toca**: sigue siendo espejo fiel de cómo está archivado el expediente en el CRM |
| **Nomenclatura** | Orden procesal: escrito rector `00_`, documentos con su numeración del pleito (`D-02_`), escritos sueltos por fecha de lote (`AAAA-MM-DD_`) |
| **Ubicación del mapping** | `05_Procedimiento/_mapa_procesal.yaml` — dentro del árbol que **sí** sincroniza al Drive en el checkin |
| **Deriva (doc_id nuevos)** | Van a `sin_asignar:`; **`apply` aborta** mientras ese bloque no esté vacío. Nunca se adivina la carpeta |
| **Idempotencia** | `apply` solo toca lo que figura en su propio `_MANIFIESTO_PROCESAL.json`. Escritos generados y `Jurisprudencia/` son inalcanzables por construcción |
| **Resolución `doc_id` → fichero** | Opción **B**: persistir el `doc_id` en la entrada canónica del manifiesto de intake (hoy solo vive en los alias) |

## 1. Problema

El expediente 487 tiene **dos procedimientos** (monitorio y, tras la oposición, ordinario) y
**70 documentos** en el gestor documental del CRM. El CRM no los archiva por fase procesal:

| `id_carpeta` | Label CRM | Docs | Bucket que le asigna hoy `resolve_bucket` |
|---|---|---|---|
| 306 | CIVIL | 38 | `99_Otros` |
| 307 | DEMANDA | 15 | `01_Demanda` |
| 304 | DEMANDA | 8 | *(sin mapear)* → `99_Sin categoria/487` |
| 1 | General | 5 | `99_Otros` |
| 312 | DOCUMENTOS | 2 | `99_Otros` |
| 303 | MONITORIO | 1 | `99_Otros` |
| 63 | Documentacion RGPD LOPD | 1 | `99_Otros` |

El grueso (38) está volcado en un cajón genérico «CIVIL». **Ningún mapeo de `id_carpeta` puede
desenredar eso**: la información de a qué fase pertenece cada documento no está en la carpeta
del CRM. Está, en cambio, en el **lote de presentación** (`modified_at`), que agrupa con
nitidez los escritos con sus documentos.

Dos herramientas existentes se descartaron por razones verificadas:

- **`bucket_override` (D11)** solo se consulta en el momento de escribir un documento nuevo.
  Sobre 69 ficheros ya en disco no hace nada.
- **`scripts/migrate_05crm_buckets.py`** trata `99_Otros` como bucket terminal
  (`KNOWN_BUCKETS`): un fichero ya depositado ahí es no-op. Sí sirve, y se usará, para el
  fallback `99_Sin categoria/487`.

## 2. Arquitectura

Tres piezas con una responsabilidad cada una:

### 2.1 `core/intake_manifest.py` — persistir el `doc_id` en la entrada canónica

`register(sha256, relative_path, *, source, **alias_details)` recibe hoy el `doc_id` dentro de
`alias_details`, pero **solo lo persiste si se crea un alias** — es decir, solo cuando el
documento es un duplicado de otro ya presente. Cuando el hash es nuevo (el caso normal: 62 de
los 70) el `doc_id` se descarta.

Consecuencia: el manifiesto sabe el `doc_id` de una copia duplicada pero no el de la copia
buena. `doc_id → ruta` es incontestable para la mayoría del expediente.

**Cambio:** al crear la entrada, persistir `doc_id`, `source` y `modified_at` en el propio
entry, junto a `primary_path`. Retrocompatible: las entradas antiguas sin esos campos siguen
siendo válidas y los adquieren en la siguiente pasada del pull (idempotente y barata —
verificado hoy: 70 documentos reconciliados en segundos, `documents_written: 0`).

**Resolución completa `doc_id` → ruta.** Una entrada canónica solo puede llevar **un** `doc_id`;
los demás documentos con el mismo contenido cuelgan como alias. El resolutor debe por tanto
buscar en **ambos sitios**: el `doc_id` del entry y los `doc_id` de sus `aliases`. Ambos
devuelven el `primary_path` cuando el alias no tiene copia física propia.

Es legítimo que **dos `doc_id` distintos resuelvan al mismo fichero de origen** — es el caso del
`TASA ORDINARIO` presentado dos veces (38060 y 39526, byte-idénticos). Si el letrado los asigna
a la misma carpeta, producen dos copias con nombre distinto (fechas de lote distintas), lo que
refleja fielmente que hubo dos presentaciones. Solo si el nombre final coincidiera se dispara la
puerta 3.

### 2.2 `core/procedimiento.py` (nuevo) — el cerebro

Puro sobre el árbol del caso, **sin red**. La fuente de qué documentos existen es el manifiesto
local, no el CRM: el intake trae, esto organiza. Así el módulo se testea sin mockear HTTP.

- `plan(case_id, expediente_id) -> PlanProcesal` — lee manifiesto + YAML y devuelve el diff.
- `apply(plan) -> ResultadoProcesal` — ejecuta y escribe el manifiesto procesal.

### 2.3 `scripts/procedimiento.py` — CLI

Subcomandos `plan` y `apply`, patrón ya establecido en el repo (`sala_maquina`,
`migrate_05crm_buckets`). `plan` no escribe nada salvo, si se le pide, el YAML inicial.

## 3. Contrato del mapping

`05_Procedimiento/_mapa_procesal.yaml`:

```yaml
version: 1
expediente_crm: '487'
carpetas:
  "01_Monitorio - Demanda y documentos":
    - {doc_id: '33428', orden: '00',   descripcion: demanda_monitorio}
    - {doc_id: '33435', orden: 'D-02', descripcion: contrato_mediacion}
  "05_Otros escritos":
    - {doc_id: '35653', orden: '2025-10-16', descripcion: decreto_admite_a_tramite_emplaza_ddo}
sin_asignar:
  - {doc_id: '41219', fichero: justif_presentacion_escr_pide_compa_telemat.pdf, lote: '2026-05-29T12:07'}
```

El nombre final del fichero copiado es **`<orden>_<descripcion>.<ext>`**. Cada carpeta queda
internamente coherente: las de documentos ordenadas por número de documento del pleito, la de
escritos por fecha.

`plan` **propone** `orden` y `descripcion`:

- `orden` ← número de documento si el nombre del CRM lo lleva (`D 02` → `D-02`,
  `D 02-A` → `D-02A`, `002_DOC 1` → `D-01`).
- Si no lo lleva y la carpeta es una de las cuatro procesales (`01`–`04`), el documento es el
  **escrito rector** de esa carpeta y `orden` ← `00`. Si en una misma carpeta hubiera más de un
  candidato a escrito rector, ambos reciben `00` y la **puerta 3** (colisión de nombre final) se
  dispara para que el letrado desambigüe. No se elige por antigüedad ni por ninguna otra regla
  implícita.
- Si no lo lleva y la carpeta es `05_Otros escritos` —que no tiene escrito rector— `orden` ←
  fecha del lote (`AAAA-MM-DD`).
- `descripcion` ← slug del nombre del CRM, minúsculas, sin acentos ni signos.

`plan` **nunca propone la carpeta**. Esa es la decisión del letrado y va a `sin_asignar` hasta
que la tome.

## 4. Flujo

**`plan`** emite el diff completo:

| Categoría | Significado |
|---|---|
| `copiar` | En el YAML, sin fichero en destino |
| `mover` | En el YAML con carpeta u `orden` distintos a los del manifiesto procesal |
| `borrar` | En el manifiesto procesal, ya no en el YAML |
| `sin_asignar` | En el manifiesto de intake para ese expediente, ausente del YAML |
| `ajenos` | Dentro de las cinco carpetas pero no en el manifiesto procesal — se reportan, **no se tocan** |

**`apply`** ejecuta y escribe `05_Procedimiento/_MANIFIESTO_PROCESAL.json`:

```json
{"generado": "<ISO>", "version": 1, "expediente_crm": "487",
 "ficheros": {"01_Monitorio - Demanda y documentos/00_demanda_monitorio.pdf":
              {"doc_id": "33428", "sha256": "...", "origen_rel": "05_CRM/99_Sin categoria/487/demanda_monitorio_comprador.pdf"}}}
```

Ese manifiesto es la frontera de lo que `apply` puede destruir. Todo lo demás en
`05_Procedimiento` — escritos generados, `Jurisprudencia/`, notas — queda fuera de su alcance
por construcción, no por convención.

## 5. Puertas de fallo

`apply` aborta, con la lista concreta de casos, si:

1. **`sin_asignar` no está vacío.** Decisión pendiente del letrado.
2. **Un `doc_id` del YAML no existe en el manifiesto de intake.** Mapping obsoleto respecto al
   crudo.
3. **Dos entradas producen el mismo nombre final.** Resuelve dos situaciones reales del 487: el
   `TASA ORDINARIO` duplicado (doc_id 38060 y 39526, byte-idénticos, un solo fichero en disco) y
   la segunda copia de la oposición al monitorio (39885, cinco meses posterior). No se
   desambiguan solas: se ponen delante del letrado.
4. **Falta en disco un fichero de origen.** El crudo está incompleto; hay que re-ejecutar el
   intake antes.

Ninguna puerta escribe fuera de las cinco carpetas.

## 6. Tests

**Sobre `plan`** (manifiesto sintético, sin red): asignación completa sin diff; `sin_asignar` no
vacío bloquea; colisión de nombre final; `doc_id` fantasma; huérfano a borrar; re-ejecución
no-op; fichero ajeno reportado y no tocado.

**Sobre el arreglo del manifiesto:** `doc_id` persistido en la entrada canónica; entrada
antigua sin `doc_id` sigue resolviendo y lo adquiere al re-registrar.

**Regresión con datos reales del 487:** el mapping completo produce 9 / 5 / 15 / 12 / 29 y cubre
los 70 documentos exactamente una vez.

## 7. Fuera de alcance en v1

- Que `plan` proponga la carpeta (adivinar la fase procesal).
- Ampliar `DESTINOS_VALIDOS` de `registrar_outputs.py` para que un escrito generado aterrice
  directamente en una carpeta procesal.
- Cualquier modificación de `00_Input/05_CRM`.

## 8. Hallazgos colaterales (no son de este diseño)

Registrados aquí porque salieron al construirlo y no deben perderse:

1. **El intake durante un checkout pierde el pull state.** `00_Input/_caso.md` está en
   `MERGE_EXCLUSIONS`: ni baja en el checkout ni sube en el checkin. Cualquier `intake-judicial`
   ejecutado sobre una copia prestada escribe `sudespacho_expedientes`, `doc_ids` y `by_carpeta`
   en un fichero que el checkin descarta. Afecta también al checkout abierto de `W-02VND1`.
   → `docs/MEJORAS_FUTURAS.md`.
2. **`id_carpeta` 304 sin mapear.** Los 8 documentos del fallback son la demanda de monitorio y
   sus documentos. Añadir `"304": "Civil/1ª Instancia/Monitorio/Demanda"` a `CARPETA_ID_TO_PATH`
   beneficia a todo expediente con monitorio. **Pendiente de la doble verificación en la UI del
   CRM** antes de mapearlo.
3. **Sustantivo, para el letrado:** el `D 07 - FACTURA DEBIDA` del monitorio es byte-idéntico al
   `D 12 - FACTURA ERRADA 23.595 EUROS` del ordinario. En el ordinario la factura correcta es la
   D 13 (25.410 €), que es la cuantía del expediente.
4. **Sustantivo, para el letrado:** falta el documento «D 01» en ambos bloques — el monitorio va
   de D 02 a D 08, el ordinario de D 02 a D 14. O no se subió al CRM, o hay un hueco frente a lo
   presentado en el juzgado.
