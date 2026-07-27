---
titulo: Revisión adversarial Codex — vista procesal 05_Procedimiento
fecha: 2026-07-27
revisor: Codex
spec: docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md
veredicto: NO SHIP
estado: abierto
adjudicacion: pendiente
---

> **Andamio efímero** (gobernanza §5). Texto **recibido de Codex por chat, sin modificar**:
> Codex trabajó en modo solo lectura y no tocó el repo. La adjudicación de cada hallazgo
> contra la fuente la hace Claude Code y se anota en este mismo fichero cuando se cierre.
>
> Existe además un **informe completo** en poder de Nikolai, no incorporado aquí todavía.

# Handoff para Claude Code — revisión del diseño `05_Procedimiento`

## Objetivo

Revisar y corregir el diseño:
`docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md`

El diseño ha recibido veredicto NO SHIP tras contrastarlo con el código y con el expediente real.
Corrige primero el spec; no implementes `core/procedimiento.py` hasta cerrar los bloqueantes.

No uses como autoridad el plan desactualizado:
`docs/superpowers/plans/2026-07-27-vista-procesal-05-procedimiento.md`

## Expediente verificado

Solo lectura:
`C:\Users\tnm33\Desktop\BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Bad debt`

Datos confirmados:

* Expediente CRM: `487`.
* 70 `doc_id` lógicos.
* 69 ficheros físicos.
* 61 SHA-256 distintos.
* 65 PDF, 2 DOC y 2 RTF.
* Siete grupos físicamente repetidos: seis pares y un triplete.
* Los `doc_id` `39526` y `38060` comparten SHA y ruta:
  `05_CRM/99_Otros/tasa_ordinario.pdf`.
* No existe `_mapa_procesal.yaml`.
* `05_Procedimiento` y `01_Procesado` están vacíos.
* El reparto procesal 9/5/15/12/29 no está respaldado por ningún artefacto local.
* `_intake_hashes.json` contiene 92 entradas, pero solo 61 rutas primarias existen; 31 están
  obsoletas.
* Ninguna entrada canónica del manifiesto conserva `doc_id` o `expediente_id`.
* El último pull registró 62 `dedup_skipped`, 8 `cross_source_overlap`, 0 fallos y
  `documents_written: 0`.
* Pese a esa métrica, escribió ocho PDF —4.997.915 bytes— en `_pendiente_checkin`.
* Los 65 PDF suman 40.683.521 bytes.
* Auditoría por página: 7 PDF sin texto, 19 con páginas deficitarias y 8 que pasan la heurística
  global pese a contener páginas con menos de 40 caracteres.
* No aparece D01 en los bloques monitorio ni ordinario.
* No se persiste `modified_at`; las fechas CRM no pueden reconstruirse desde la carpeta.

## Bloqueantes que debe corregir el spec

### 1. Sustituir el modelo `SHA → entry + aliases`

El modelo actual pierde identidades reales. La tasa lo demuestra: dos `doc_id` con igual SHA y path
no producen alias y ninguno queda persistido.

Diseñar dos capas:

```
physical_objects:
  sha256 -> rutas físicas y artefactos

occurrences:
  (source, expediente_id, doc_id) ->
    sha256
    path
    filename
    modified_at
    estado: active | superseded
```

Requisitos:

* Varias ocurrencias pueden compartir SHA y path.
* Un `doc_id` solo puede tener una ocurrencia activa.
* Si cambia el contenido de un `doc_id`, la anterior queda `superseded`.
* `plan(case_id, expediente_id)` filtra por expediente.
* Nunca resolver por “primer match”.

### 2. Eliminar la promesa falsa de backfill automático

Un pull idempotente no actualiza metadatos de primaries o aliases existentes.
El spec debe exigir:

* Migración versionada.
* Upsert de metadatos antes de cualquier retorno `skip`.
* Paso de `info.modified_at`.
* Verificación posterior: todos los `pull_state.doc_ids` deben tener una ocurrencia resoluble.
* No interpretar `documents_written: 0` como “cero efectos físicos”.

### 3. Añadir una puerta de integridad y completitud

Antes del diff, cruzar:

* `pull_state.documents_total_crm`;
* `pull_state.doc_ids`;
* ocurrencias activas del manifiesto;
* rutas existentes;
* SHA actuales;
* errores del último pull.

Abortar si:

* el manifiesto falta, es corrupto o tiene versión desconocida;
* faltan ocurrencias;
* hay ocurrencias activas fuera de `pull_state`;
* un `doc_id` aparece activo bajo varios SHA;
* una ruta de origen falta;
* el manifiesto contiene datos históricos sin marcar `superseded`.

Nunca convertir un error de carga en `{}`.

### 4. Reforzar la frontera de propiedad del ledger

“Está en el ledger” no basta para borrar o sobrescribir.
Antes de `mover`, `borrar` o `reemplazar`:

* el destino debe seguir existiendo;
* debe ser fichero regular, no symlink/reparse point;
* su SHA actual debe coincidir con el SHA previo del ledger;
* un destino existente no registrado se considera ajeno;
* cualquier divergencia aborta.

Un fichero `despacho` nunca puede entrar en una operación destructiva.

### 5. Hacer `apply()` transaccional

Definir expresamente:

1. Preflight completo.
2. Copia a temporales del mismo volumen.
3. Verificación de tamaño y SHA.
4. Reemplazos/movimientos atómicos.
5. Borrados al final.
6. Ledger escrito atómicamente como último commit.
7. Journal o recuperación determinista tras fallo parcial.
8. Diff vacío = cero escrituras, incluido el campo `generado`.

### 6. Sustituir las tres ramas basadas en existencia

No inferir estado mediante:

```
existe 01_OCR
no existe 01_OCR pero existe MD
no existe ninguno
```

Resolver desde `_cobertura.json`, por SHA y ocurrencia, con:

```
raw_sha256:
method: pypdf | ocr | vision | native | unsupported | converted
artifact_path:
artifact_sha256:
searchability: complete | partial | none
quality:
parent_sha256:
segments:
```

Reglas mínimas:

* `pypdf`/nativo permite copiar crudo.
* `ocr` exige que el artefacto OCR exista y coincida por SHA.
* `vision` no convierte el PDF visual en buscable.
* Artefacto declarado pero ausente = bloqueo.
* Cobertura ausente para un documento soportado = bloqueo, salvo override explícito.
* Bundles se resuelven por `parent_sha256`, no buscando un MD padre inexistente.

### 7. Detectar PDF híbridos por página

La heurística global actual deja páginas ciegas en ocho PDF reales del piloto.
El spec debe optar entre:

* detección y OCR por página; o
* declarar que solo garantiza “texto global suficiente” y mostrar cobertura parcial.

No prometer buscabilidad íntegra con la heurística actual.

### 8. Definir transiciones de artefacto

Añadir una acción `reemplazar` por identidad lógica para:

* raw `.doc` → PDF LibreOffice;
* imagen cruda → PDF OCR;
* raw PDF → OCR;
* OCR → raw;
* regeneración OCR con SHA diferente.

El ledger debe guardar:

```
logical_key: crm:<doc_id>
raw_path:
raw_sha256:
source_kind: raw | ocr | converted
source_path:
source_sha256:
destination:
destination_sha256:
```

La extensión del destino debe corresponder a los bytes copiados.

### 9. Validar completamente el mapping

Añadir puertas para:

* carpeta fuera de las cinco permitidas;
* clave lógica duplicada;
* `fichero` con directorios;
* traversal;
* nombres reservados Windows;
* puntos/espacios finales;
* colisión tras normalización `casefold`;
* destino ajeno ya existente;
* ruta absoluta o segmento demasiado largo;
* symlink/reparse point.

Aplicar truncado dinámico con sufijo hash estable.
En el piloto, 60 caracteres caben por poco: hasta 253 caracteres en una combinación larga. No es
garantía general.

### 10. Tratar mapa, ledger y ficheros como unidad de merge

`_mapa_procesal.yaml` puede ser maestro y el ledger derivado, pero no deben sincronizarse
independientemente.
Requisitos:

* conflicto de mapa o ledger bloquea todo el grupo;
* no subir PDF/ledger si el mapa está en conflicto;
* `Drive ausente + baseline presente` debe ser conflicto, no `COPY_LOCAL`;
* el ledger solo se regenera después de aceptar una versión concreta del mapa.

### 11. Diseñar la reconciliación de `_index.md`

No llamar al `registrar()` completo para documentos CRM.
Crear una primitiva que:

* gestione solo filas `CRM:<doc_id>`;
* actualice, mueva y elimine filas;
* preserve filas del despacho;
* no añada wikilinks a `_caso.md`;
* separe claramente bloque manual y bloque CRM generado;
* permita merge por clave, no por hash del fichero completo.

### 12. Corregir las cifras y su terminología

Confirmado:

```
70 doc_id
69 rutas físicas
61 SHA
65 PDF + 2 DOC + 2 RTF
```

Corregir `62 de 70 hashes nuevos`. El `62` observado significa:

```
62 dedup_skipped
8 cross_source_overlap
```

No son 62 hashes nuevos.
Mantener 9/5/15/12/29 como pendiente de validación hasta incorporar el mapa completo o un fixture
anonimizado.

## Correcciones secundarias

* Mantener la decisión de no universalizar `01_OCR`, pero justificarla por semántica, fidelidad y
  coste, no por pérdida de custodia.
* Persistir procedencia doble: SHA crudo, SHA copiado y derivación.
* Rehacer la matriz de skills: hay doce mencionadas, no nueve.
* Reclasificar `contestacion-honorarios-art20-lau` y `oposicion-alegacion-nulidad` como cambios de
  comportamiento.
* No modificar `engel-volkers` solo para replicar subcarpetas internas.
* Definir en `organizar-sala-lectura` una exclusión operativa basada en ocurrencias/SHA, no una mera
  instrucción narrativa.
* Cambiar el handoff de `organizar-sala-maquina` para sugerir la vista procesal antes de la sala de
  lectura cuando exista pleito.
* Corregir `PLAN.md:181-183`: solo el punto `.doc` de MEJORAS #61 está promovido.
* Reformular “el core solo lee”: el cliente documental no escribe, pero `core` ya dispone de
  autenticación REST de escritura.
* El texto humano de `_caso.md:150` conserva una ruta obsoleta `00_Input/sudespacho_487/`; los
  documentos reales están en `00_Input/05_CRM`.

## Decisiones que deben conservarse

* La carpeta procesal la decide el letrado.
* El reparto se hace por `doc_id`, no por SHA.
* Dos aportaciones procesales byte-idénticas pueden producir copias en carpetas distintas.
* `00_Input/05_CRM` es inmutable.
* El mapa es la decisión humana maestra.
* El ledger delimita propiedad, una vez reforzado con verificación de SHA.
* No universalizar `01_OCR`.
* El MD no sustituye documentos visuales.
* Mantener separados índice humano y contabilidad de propiedad.

## Pruebas mínimas exigidas antes de SHIP

1. Dos `doc_id`, mismo SHA y mismo path.
2. Dos `doc_id`, mismo SHA y rutas distintas.
3. Un `doc_id` cuyo contenido cambia.
4. Manifiesto corrupto.
5. Manifiesto con rutas históricas ausentes.
6. `pull_state` con IDs ausentes del manifiesto.
7. Destino sustituido manualmente tras escribirse el ledger.
8. Destino ajeno con el nombre canónico.
9. Mapping con traversal, reservado Windows y colisión `casefold`.
10. Fallo de disco a mitad de `apply`.
11. OCR declarado pero artefacto ausente.
12. MD por visión sin PDF buscable.
13. Bundle sin MD padre.
14. PDF híbrido con páginas sin texto.
15. Raw→OCR y `.doc`→PDF con cambio de extensión.
16. Reejecución sin cambios con cero escrituras.
17. Conflicto de mapa durante checkin sin subir ledger ni PDF.
18. Borrado remoto del ledger sin resurrección.
19. Movimiento/borrado con reconciliación correcta de `_index.md`.
20. Ruta completa próxima y superior al límite configurado.

## Estado de verificación

* Repositorio: 177 pruebas pasadas, 3 omitidas por marca `lento`.
* Las siete copias de `registrar_outputs.py` son byte-idénticas.
* Expediente: 337 ficheros del baseline presentes, cero MD5 divergentes.
* No se modificó el expediente durante la auditoría.
* No se modificó el repositorio.

## Entrega esperada

1. Spec corregido.
2. Tabla explícita `hallazgo → sección corregida`.
3. Lista separada de decisiones aún abiertas.
4. Fixture anonimizado con los 70 `doc_id` o eliminación de afirmaciones no reproducibles.
5. Nuevo veredicto de diseño antes de escribir código.
