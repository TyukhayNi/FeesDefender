---
tipo: handoff
estado: consumido
creado: 2026-08-01
origen: revisión adversarial de Codex (chat, solo lectura) — 1ª pasada sobre la rev. 1, commit `f965716`
destino: sesión Claude Code — adjudicar los 10 hallazgos y decidir si la decisión central sobrevive
consumido_por: "rev. 2 de la spec (§12 mapea cada hallazgo a la sección que lo corrige). B0-2 cambió la decisión central: la identidad pasa del ordinal `seg` a un `doc_id` persistente."
titulo: Revisión adversarial 1ª pasada — identidad del segmento de bundle (rev. 1)
revisor: Codex
spec: docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md
commit_revisado: f965716
veredicto: NO SHIP
---

> **Andamio efímero** (gobernanza §5). Texto **recibido de Codex por chat, sin modificar**. Trabajó
> en solo lectura y no modificó el repo.
>
> **Adjudicación de Claude Code:** en el **§12 de la spec**, no aquí. Resumen: 8 hallazgos aceptados
> tal cual, 1 confirmado con la línea mal atribuida (A-1: el `except` de `_split_o_md:562` envuelve
> solo `split.detectar`; quien absorbe es `ejecutar:732`), y 1 matizado en la solución (B0-1: se
> resuelve con archivado previo + guard por hash, no con el journal completo del motor). **B0-2 es
> el que importa: cambió la decisión central de la spec.** Las cifras del censo (M-3) se recontaron
> de forma independiente y el revisor tenía razón: 21 excedentes, no 12.
>
> Se ignora la frase final del informe sobre «la retirada de Gemini de los workflows», que no
> corresponde a este encargo.

## VEREDICTO: NO SHIP

La identidad posicional corrige el crecimiento de huérfanos, pero introduce dos riesgos
bloqueantes: puede sobrescribir un artefacto estable antes de publicar coherentemente sus derivados
y registros, y puede hacer que un mismo `segNN` represente documentos distintos después de
`--force`. La migración tampoco tiene un contrato suficiente frente a coberturas ambiguas, fallos
parciales, checkout o concurrencia.

## Hallazgos

| ID | Severidad | Afirmación atacada | Evidencia | Qué cambiar |
|---|---|---|---|---|
| B0-1 | B0 | §3: sobrescribir el slug estable "es exactamente lo que hace un documento suelto" y basta para sustituir limpiamente el segmento. | `core/split_documental.py:286-313`: `materializar` llega a `emitido.replace(destino_pdf)` antes de que terminen MD, `raw_text`, índice y publicación de cobertura. En Windows, `Path.replace` sobre un destino existente lo sobrescribe; lo confirmé en temporal. Si después falla `_split_o_md`, la cobertura antigua conserva el mismo slug y el sha anterior, pero ese nombre ya contiene los bytes nuevos. El guard de existencia pasa aunque la custodia sea falsa. | Exigir publicación transaccional: staging de PDF, MD, raw e índices; journal/respaldo; publicación conjunta de artefactos y cobertura; restauración verificable ante fallo. Añadir fault injection después de cada operación. |
| B0-2 | B0 | §10.1: `--force` solo deja la misma clase de huérfanos y puede quedar fuera de alcance. | `scripts/sala_maquina.py:303` usa cobertura fresca con `previa=[]` bajo `--force`; el manifiesto se regenera. Con identidad por ordinal, si cambian segmentación, orden o numeración, `seg02` puede pasar a designar otro documento. Si conserva también el mismo `TIPO`, no queda un huérfano: el documento anterior se sobrescribe bajo la misma identidad. El slug deja de ser estable semánticamente aunque sea estable nominalmente. | No derivar identidad permanente de un ordinal regenerable. Persistir un identificador lógico inmutable en el manifiesto, o impedir la sobrescritura posicional cuando cambie la correspondencia anterior. `--force` debe reconciliar o archivar la versión previa, no olvidar `previa`. |
| A-1 | A | §3.1: añadir `ValueError` por `seg` repetido evita una pérdida silenciosa. | `validar_manifiesto` está en `core/split_documental.py:261`; `materializar`, en `:286`. Pero `_split_o_md` captura `Exception` en `core/sala_maquina.py:562`, y `ejecutar` vuelve a aislar fallos por documento en `:732`. En una prueba sintética, el manifiesto duplicado no llegó como error fatal a la CLI: quedó absorbido por el aislamiento del documento, con finalización genérica y sin stderr útil. | Crear una excepción específica, p. ej. `ManifestValidationError`, que atraviese `_split_o_md` y fuerce exit no cero antes de materializar. Debe quedar evento/diagnóstico explícito con bundle y `seg`, sin degradarse a fallback. Probar la CLI, no solo la función pura. |
| A-2 | A | §6: si hay varias versiones, "sobrevive la que cite `_cobertura.json`". | `fusionar_cobertura`, `core/sala_maquina.py:323`, indexa por `(rel_path, slug)`. Precisamente por ello una cobertura puede conservar varias filas del mismo `(parent_slug, seg)`, una por sha. La expresión singular "la que cite" no define qué hacer cuando el registro cita dos o tres candidatos. El censo confirma que todos los grupos duplicados tienen algún candidato citado, pero no convierte esa selección en necesariamente única. | Contrato explícito para cero, una o varias coincidencias. Solo una coincidencia puede seleccionarse automáticamente; con varias, abortar el grupo y exigir resolución o una regla adicional verificable. Añadir fixture con tres versiones y dos/tres citadas. |
| A-3 | A | §6: si no hay JSON, `_cobertura.md` sirve como fallback de autoridad. | El código existente sabe cargar JSON o reconstruir desde los MD (`reconstruir_cobertura_desde_md`, `core/sala_maquina.py:219`); no existe un parser canónico de `_cobertura.md` que garantice recuperar el slug sin pérdidas o ambigüedades. El patrón citado, `migrar_nombres_informe`, tampoco aporta ese contrato. En el censo real, `W-02XOR7` tiene sala de máquina pero no `_cobertura.json`, aunque actualmente no contiene segmentos. | Definir una fuente autoritativa y un parser probado para legacy, o declarar esos casos no migrables automáticamente. No inferir el superviviente desde una tabla humana sin especificar escaping, duplicados y referencias inexistentes. |
| A-4 | A | §9: la regla "si queda un solo candidato ya renombrado, completar los registros" hace reanudable la migración. | La secuencia propuesta es mover perdedores → renombrar superviviente → reescribir registros. No hay journal que distinga una migración interrumpida de un fichero estable creado por otra ejecución, una edición manual o una sesión concurrente. Además PDF, MD y raw se operan por separado: el fallo puede dejar solo una representación renombrada. La mera presencia de "un candidato nuevo" no demuestra cuál fue la operación previa. | Journal por grupo con hashes de origen/destino, fase alcanzada y backup. Al reanudar, validar el estado contra el journal; si no coincide, fallar cerrado. Probar interrupción después de cada movimiento, renombrado y reescritura. |
| A-5 | A | §9: basta con saltar checkout abierto y recomprobar el destino frente a sincronización de Drive. | `core/repository_checkout.py:292` planifica el merge de tres vías y `:420` aplica `GRUPOS_MERGE`. Los PDF, MD, raw, índices, cobertura y `99_Versiones anteriores` no forman un grupo indivisible; el archivo histórico tampoco está protegido por `MERGE_EXCLUSIONS`. En un escenario temporal, `plan_merge` emitió simultáneamente `RENAME` y `CONFLICT`, y la ruta de aplicación copiaría los renombrados de forma independiente. Una copia desfasada puede resucitar el nombre retirado o publicar solo parte del grupo. La comprobación del destino no constituye un lock. | Prohibir migrar tanto con checkout como con cualquier copia operativa divergente; integrar un lock de caso y un baseline; tratar todo el grupo como unidad de merge o excluir formalmente el archivo de versiones. Añadir prueba E2E checkout→migración→checkin y escenario concurrente. |
| M-1 | M | §1.2/§7: están identificados todos los consumidores y referencias del slug. | La afirmación mezcla consumidores ejecutables con referencias persistentes. Además de cobertura, preclasificador y detector, la materialización mantiene índices de bundle —incluidos `indice.json` y la representación textual— y existen menciones en logs/documentación de skills. Algunas deben reescribirse y otras, por ser históricas, no deben tocarse; la spec no establece esa clasificación. No había ningún `.skill` empaquetado en el worktree, por lo que ese artefacto concreto no podía inspeccionarse. | Inventario mecánico por extensiones y campos, distinguiendo referencias operativas de históricas. Test que busque el slug viejo tras migrar en todo el radio autorizado y mantenga intactos logs forenses. Verificar también el paquete `.skill` que vaya a desplegarse. |
| M-2 | M | §8: el contrato de tests cubre suficientemente la regresión. | Falta probar el error a nivel CLI, `--force` con renumeración, cambio de `tipo`, cobertura con varias coincidencias, fallos entre pasos, checkout/checkin y carrera con otra sesión. "Toda fila cita un fichero existente" puede pasar en el estado corrupto de B0-1 porque el nombre existe aunque tenga bytes incompatibles con el sha registrado. | Añadir asertos de hash y contenido, exit code/stderr, ausencia total de nombres viejos dentro del radio, fault injection, escenarios de varias coberturas y merge. El test de doble materialización debe cambiar realmente los bytes y demostrar que PDF, MD, raw, índice y cobertura pertenecen a la misma generación. |
| M-3 | M | §2: hay "12 ficheros huérfanos entre `02_Documentos` y `03_MD`, más los de `raw_text`". | El censo real da 14 excedentes entre esas dos áreas: VND1 tiene 3 PDF + 3 MD sobrantes; VUDR, 4 PDF + 4 MD. `raw_text` añade otros 7. Son 21 representaciones excedentes en total. | Corregir 12→14; declarar 7 adicionales en raw y 21 contando las tres representaciones. Mantener aparte "5 grupos lógicos duplicados", que sí es correcto. |

## Verificado ejecutando

### Identidad del objeto revisado

Se verificaron la rama `claude/proximo-paso-464808`, el commit `f965716` y el estado limpio antes de
la revisión. No se modificó ningún fichero.

### Suite completa

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe `
  -m pytest -q --tb=no -p no:cacheprovider `
  --basetemp <temporal fuera del repo> `
  -o "addopts=-ra"
```

```text
2612 passed, 77 skipped, 7 xfailed in 152.29s
exit code 0
```

Los tests lentos relevantes del split también se ejecutaron separadamente: `3 passed in 2.93s`.
La suite verde no refuta los hallazgos: los escenarios anteriores no están cubiertos.

### Pruebas dirigidas

- `Path.replace` sobre Windows sobrescribe un destino existente. Confirma la premisa de B0-1.
- Un manifiesto con `seg` duplicado, introducido en la ruta real de `_split_o_md`, quedó absorbido
  por el aislamiento por documento; no produjo el fallo alto y visible que promete §3.1.
- Un escenario sintético de `plan_merge` con retirada y renombrado simultáneos produjo operaciones
  `RENAME` junto con `CONFLICT`; los renombrados se aplicarían como copias independientes.
- No se ejecutó ninguna operación destructiva o de escritura sobre Drive.

### Censo real read-only en `G:\`

El primer informe omitió indebidamente este censo: la prohibición era escribir en `G:\`, no leer. Se
corrigió mediante un barrido de solo lectura, sin imprimir nombres de clientes, rutas ni contenido.

| Caso | Grupos `(parent, seg)` | Duplicados | Versiones | PDF | MD | raw |
|---|---:|---:|---|---:|---:|---:|
| `W-02VND1` | 15 | 3 | 2, 2, 2 | 18 | 18 | 18 |
| `W-02VUDR` | 20 | 2 | 3, 3 | 24 | 24 | 24 |
| `W-02T3XO` | 0 | 0 | — | 0 | 0 | 0 |
| `W-02XOR7` | 0 | 0 | — | 0 | 0 | 0 |
| `W-02TH0W` | 0 | 0 | — | 0 | 0 | 0 |

También quedó comprobado:

- Todos los artefactos encontrados en `raw_text` usan extensión `.txt`.
- VND1 y VUDR tienen `_cobertura.json`.
- Cada uno de los cinco grupos duplicados tiene al menos una versión citada por la cobertura.
- `W-02XOR7` no tiene `_cobertura.json`, aunque tampoco tiene segmentos.
- Los números centrales de la spec —35 grupos y 5 grupos duplicados— son correctos.
- El total declarado de 12 huérfanos entre PDF y MD es incorrecto: son 14.

## Verificado leyendo

Se revisó el fuente completo del commit, no solo el diff, en particular: `core/split_documental.py`
(validación, `_slug_seg`, materialización, sustitución e índices); `core/sala_maquina.py`
(reconstrucción y fusión de cobertura, escritura de `raw_text`, `_split_o_md`, `_ocr_y_extraer` y
aislamiento en `ejecutar`); `scripts/sala_maquina.py` (carga de cobertura, `apply`, `--solo` y
`--force`); `core/migrar_nombres_informe.py`; `core/repository_checkout.py` (exclusiones, detección
de renombrados, merge de tres vías y grupos indivisibles); `preclasificar.py`,
`detectar_ocr_ciego.py` y búsquedas globales de consumidores y nombres persistentes; el contrato de
tests descrito en §8 y los tests existentes del split/sala de máquina.

## NO VERIFICADO

- El dry-run, aplicación, reanudación e idempotencia del migrador: `scripts/migrar_slugs_segmento.py`
  todavía no existe.
- Una carrera real con dos procesos sobre el mismo expediente.
- El comportamiento de una migración real seguida de checkout/checkin contra Drive.
- Una operación real de `rclone` que reproduzca la resurrección: habría requerido mutar un
  expediente, expresamente prohibido.
- La cronología exacta de julio y la afirmación de que la cobertura de VND1 cita concretamente la
  versión del 23/07 mientras `indice.json` cita la del 30/07. El censo confirmó versiones y
  referencias existentes, pero no se adjudicaron esos timestamps/hashes concretos.
- Un `.skill` empaquetado: no existía ninguno en el worktree revisado.

Nada de lo anterior se declara refutado sin medición.

## Lo que intenté refutar y no pude

1. **La causa raíz es correcta.** `_slug_seg`, `core/split_documental.py:280`, incorpora hoy
   `seg_sha256[:8]`, calculado a partir del PDF recortado derivado. Si cambian esos bytes, cambia el
   nombre.
2. **La asimetría con documentos sueltos es real.** El documento suelto se apoya en el sha del
   origen de `00_Input`; el segmento se apoya en el sha de un producto regenerable.
3. **El arreglo nominal elimina los huérfanos causados únicamente por cambios de bytes.**
4. **Actualmente no se valida la unicidad de `seg`.** La comprobación propuesta es necesaria.
5. **`_slug_seg` tiene un único llamador productivo.**
6. **`raw_text` usa el mismo slug y extensión `.txt`** (`core/sala_maquina.py:505`).
7. **El manifiesto y `_sala_maquina_state.json` no son referencias directas al slug del segmento.**
8. **Los recuentos lógicos principales de §2 son correctos:** 15+20 segmentos, cinco grupos
   duplicados, versiones 2/2/2 y 3/3. Lo incorrecto es el total derivado de ficheros huérfanos.
9. **Conservar `TIPO` mejora la legibilidad.** El problema es tratarlo, junto con un ordinal
   regenerable, como identidad permanente.

## Condiciones mínimas para pasar a SHIP

1. Resolver B0-1 con publicación transaccional o rollback verificable de toda la generación.
2. Resolver B0-2: identidad lógica persistente o contrato seguro de `--force`.
3. Hacer fatal y visible la duplicidad de `seg` desde la CLI.
4. Definir inequívocamente qué ocurre cuando la cobertura cita cero, una o varias versiones.
5. Sustituir la heurística de reanudación por un journal con hashes y fases.
6. Integrar la migración con el protocolo checkout/checkin y un lock real de caso.
7. Ampliar el radio y los tests, incluyendo hashes, fallos parciales, `--force`, legacy y
   concurrencia.
8. Corregir el censo documental: 14 excedentes PDF/MD, 7 raw, 21 representaciones.

La decisión arquitectónica —sacar el sha derivado del nombre— puede conservarse, pero la spec no
debe implementarse con el contrato actual.
