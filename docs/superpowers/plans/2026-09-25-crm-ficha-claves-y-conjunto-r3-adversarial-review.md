---
tipo: revision-adversarial
objeto: diff 4209582..93c1907 de crm_ficha (core/crm_ficha.py, scripts/crm_ficha.py, scripts/crm_colaboradores_firmas.py, core/sudespacho_relations.py y sus tests), contra el plan rev. 2
objeto_rev: "2"
commit: 93c1907
ronda: "3"
revisor: Codex
modelo: gpt-6-astra
esfuerzo: medium
velocidad: default
veredicto: REQUIERE-REVISION
marcador_nonce: zqwk
sha256_informe: 11fe7d11c28bef7b720333c69fa2959384b0e01535bdf389341eabda60b9cb3d
adjudicado_en: docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md §10
---

# Acta — R3 adversarial sobre el DIFF de `crm_ficha` (MEJORAS #283 + #288)

Objeto: el diff `4209582..93c1907`, que implementa el spec rev. 3 y el plan rev. 2 de `crm_ficha`.
**Tercera y última ronda de la pieza.** La tabla de `CLAUDE.md` da dos a una pieza que escribe
sobre datos de cliente —una sobre el diseño y otra sobre el diff—; la R1 fue sobre el spec y la R2
sobre el plan, y **Nikolai autorizó expresamente el 2026-09-25 esta tercera** sobre el techo de dos
(spec §7). No hay cuarta sin su autorización. Fila de modelo: escritura sobre datos de cliente →
`gpt-6-astra` · `medium`.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), `gpt-6-astra` · `medium` — **releídos** del `turn_context` del rollout y de la cabecera del `_stdout.log`; velocidad `default` **afirmada** desde el lanzador, no acreditada |
| Objeto | `base/` (`4209582`) y `head/` (`93c1907`), copias `git archive` fuera del repo, más `diff.patch` y `commits.txt` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**: 2.827 ficheros, comparados por él y por mí contra una huella mía tomada antes de lanzar |
| `sha256` del informe | `11fe7d11c28bef7b720333c69fa2959384b0e01535bdf389341eabda60b9cb3d` |
| Tiempos | lanzado a las 09:09:20; `INFORME.md` a las 09:24:00; `exec` salió a las 09:24:10 con `exit=0` |
| Veredicto | `REQUIERE-REVISION` — 4 hallazgos: 1 `alta`, 1 `media`, 2 `baja` |

## 0. Mandato, literal

# Mandato — R3 adversarial sobre el DIFF de `crm_ficha` (MEJORAS #283 + #288)

## 0. Higiene del directorio de trabajo

Tu directorio de trabajo debe contener SOLO: este `MANDATO.md`, `base/`, `head/`, `diff.patch`,
`commits.txt` y el `_stdout.log` que escribe el lanzador. Si hay cualquier otro fichero o carpeta,
**no lo leas** y decláralo en la primera línea de tu informe. No escribas nada fuera de este
directorio.

## 0-bis. Cómo leer este encargo

Es la revisión del **código** que implementa un diseño ya revisado dos veces: la R1 fue sobre el
spec y la R2 sobre el plan. Esta es la tercera y última ronda de la pieza, autorizada por el
titular. Se te piden **dos trabajos**, en este orden de importancia:

1. **Auditar el diff en fresco**, contra el código real y contra lo que el spec rev. 3 promete: si
   hace lo que dice, en todos los caminos, y si sus tests lo acreditan.
2. **Dictaminar si el código remedia de verdad los nueve hallazgos de la R2** (adjudicados en la §9
   del plan): **real, cosmético o incompleto**, cada uno con su razón. En esta casa, remedios que
   parecían completos resultaron cubrir el caso descrito y no la propiedad de la que era ejemplo.

Puedes leer todo `base/` y `head/`, y ejecutar tests y sondas sobre copias; no hace falta red.

## 1. Objeto, anclado a commits

- **Base:** `4209582e3870c743fa28c6bd622403d9cfe9693b` (el `main` del que sale la rama), extraído en `base/`.
- **Cabeza:** `93c1907bf49b6fdb1fee58cac8ddf95f271cf923`, extraído en `head/`. Las dos copias salen de `git archive`, sin `.git` y
  en CRLF; el contenido canónico es LF.
- **`diff.patch`:** `git diff 4209582e3870c743fa28c6bd622403d9cfe9693b..93c1907bf49b6fdb1fee58cac8ddf95f271cf923`, entero. **`commits.txt`:** los commits de la rama, en
  orden, con sus mensajes: cada uno enumera sus migraciones de tests.
- **El código:** `core/crm_ficha.py`, `scripts/crm_ficha.py`, `scripts/crm_colaboradores_firmas.py`
  y, en `core/sudespacho_relations.py`, el campo `id_crm` de los dos DTOs y los resolutores
  `resolver_contrario_existente` / `resolver_colaborador_existente` con los dos `_resolver_o_crear_*`.
- **Los tests:** `tests/test_crm_ficha_lector.py`, `test_crm_ficha_auditoria.py`,
  `test_crm_ficha_id_crm.py`, `test_crm_ficha_cli.py`, `test_crm_ficha_integracion.py` (un CRM en
  memoria que sustituye solo el transporte), los migrados (`test_crm_ficha_yaml_none.py`,
  `test_crm_ficha_n_contrarios.py`, `test_crm_ficha_validacion.py`, `test_crm_ficha_validacion_r1.py`,
  `test_crm_colaboradores_firmas_cli.py`) y el arnés de mutantes `tests/_mutantes_crm_ficha.py`
  (y el re-apuntado de su M11 en `tests/_mutantes_p6.py`).
- **El diseño que el código implementa:** el spec rev. 3,
  `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md`, y el plan rev. 2,
  `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md` (su §9 es la adjudicación de
  la R2).
- **La R2**, con el informe literal del revisor anterior:
  `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto-r2-adversarial-review.md`; su
  `sha256_informe` es `eeca36555fd1af94155d6b9e172fd86d8fed71c74008e63d6b991b242aa981c8`.

**Decisiones del titular que no se discuten salvo que produzcan un defecto:** el
`_ficha_crm.yaml` es la lista COMPLETA de partes del expediente; `crm_ficha` nunca desvincula ni
pisa un dato; la política de completar solo lo vacío (`_COMPLETABLES_*`) no se toca.

**Límites que el autor declaró en el spec rev. 3 §5** —una parte con `id_crm` cuyo NIF declarado
pertenece a otra ficha; la ventana entre la fase previa y la escritura—: evalúa si la declaración
es exacta y si el daño es el que dice; no hace falta que los trates como defectos nuevos salvo que
el código haga algo peor que lo declarado.

**Mediciones del autor que no puedes repetir** (sin CRM ni Drive): el censo de los 14
`_ficha_crm.yaml` reales (spec §0). Si una conclusión tuya depende de que sea falsa, dilo así.

## 2. Lo que se te pide, ordenado por daño

Contesta cada punto en una sección propia, con su número.

1. **Ninguna escritura sobre una ficha que el YAML contradice.** ¿Hay algún camino por el que la
   corrida escriba en el CRM —vincular, completar (PUT) o crear— antes de detectar un dato distinto
   en una ficha que ya existe, un `id_crm` que no existe, una ficha que no se puede leer, o un
   conflicto de identidad? Recorre la vía `id_crm` y la de NIF/email, los dos roles (contrario y
   colaborador), y `--dry-run`, que no debe leer el CRM.
2. **La verificación final.** ¿Puede la salida decir «VERIFICADA» con un vínculo de más o de menos
   en cualquiera de los tres bloques, o con un dato declarado que no está en el CRM? Incluye las
   partes creadas y las existentes, los dos roles, la auditoría parcial tras una escritura fallida,
   y un «SIN VERIFICAR» simultáneo con un fallo conocido.
3. **Lectura y validación del YAML.** ¿Se pierde, se transforma o pasa sin validar algo del
   fichero —claves repetidas o desconocidas, alias, merge, tipos, identidad, `id_crm`, provincia,
   teléfonos—? ¿Los dos consumidores (`cargar_ficha_yaml` y `crm_colaboradores_firmas.apply`)
   leen con el mismo lector? ¿Lo que se audita es la declaración y no el DTO normalizado?
4. **Los nueve hallazgos de la R2 (H-01 a H-09):** para cada uno, **real, cosmético o
   incompleto** en el código, con la razón.
5. **Los tests prueban lo que dicen.** ¿Alguno pasaría por el camino equivocado, o sin ejercitar
   su propiedad? ¿Los dobles del CLI (`_declara_fichas`, `_declara_resolucion`) o el CRM en memoria
   de la integración esconden algún comportamiento del CRM real que el código necesita? ¿Cada
   mutante del arnés muere por su propiedad, y falta alguno para una propiedad de los puntos 1-3?
6. **Sin `id_crm`, nada cambia para los demás llamadores** de `ensure_*` y de los resolutores (la
   jurisdicción judicial, la UI). ¿Es cierto?
7. **Las migraciones de tests existentes** (enumeradas en el plan rev. 2 y en los mensajes de
   `commits.txt`): ¿alguna debilita la propiedad del test que migra?

## 3. Cómo correr tests si te sirve

Desde una **copia** de `head/` en tu directorio (no mutes `head/` ni `base/`), con el Python de
sistema:

```powershell
$py = 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $py -m pytest tests/test_crm_ficha_lector.py tests/test_crm_ficha_auditoria.py tests/test_crm_ficha_id_crm.py tests/test_crm_ficha_cli.py tests/test_crm_ficha_integracion.py tests/test_crm_ficha_yaml_none.py tests/test_crm_ficha_n_contrarios.py tests/test_crm_colaboradores_firmas_cli.py -p no:cacheprovider --basetemp=_bt
```

El `--basetemp` va **relativo**, dentro de tu directorio. Si corres el arnés de mutantes, apunta
antes `$env:TEMP` y `$env:TMP` a una carpeta de tu directorio: crea allí su copia de trabajo. Nada
de red.

## 4. Formato de cada hallazgo

- Numeración `H-NN`.
- **Severidad** —el daño si se mergea así—: `alta` · `media` · `baja`.
- **Coste del remedio que propones**: `trivial` (una línea o un literal) · `acotado` (una función y
  su test) · `estructural` (cambia una frontera, un contrato o un formato que otros leen).
- **Dónde**: fichero y líneas de `head/`.
- **Reproducción o evidencia**: la sonda, el test o la cita del código. Si construyes datos de
  prueba, usa marcadores neutros (`PARTE-PRUEBA-1`, `00000000T`).
- **Afirmación contradicha**: la frase del spec, del plan o de un docstring que el defecto
  desmiente, citada.
- **Remedio**.

## 5. Lo que va al final del informe

- `## Lo que intenté refutar y NO pude`: los ataques que hiciste y no dieron defecto.
- `## SIN VERIFICAR`: lo que no pudiste comprobar y por qué.
- Si el objeto te desborda al esfuerzo con el que estás corriendo, dilo y di en qué punto.
- **La última línea del informe es el veredicto, sola**, del set cerrado: `SHIP`,
  `LISTA-CON-CAMBIOS`, `REQUIERE-REVISION`, `NO-SHIP`, `NO-EJECUTABLE` o `SIN-VEREDICTO`.

**Volver limpio es un resultado legítimo.** Si has auditado el diff y no encuentras nada que
impida mergearlo, `SHIP` es la respuesta correcta. No añadas hallazgos para justificar la ronda, y
no rebajes uno que encuentres.

## 6. Evidencia de no mutación y entrega

- Calcula el `sha256` de **todos** los ficheros de `base/` y de `head/` al abrir
  (`hashes-apertura.json`) y al cerrar (`hashes-cierre.json`), y di en el informe si coinciden.
- Escribe el informe en `INFORME.md`, en este directorio, UTF-8, LF, un único salto final.
- En tu **mensaje final** —el que recoge `-o`— da la ruta de `INFORME.md`, su `sha256` canónico
  (UTF-8, LF, un único salto final) y el veredicto.

## 7. Prohibiciones

- El repositorio real (`C:\Users\tnm33\Dev\FeesDefender` y sus worktrees) es de **solo lectura** y
  no te hace falta. Nada de red: ni el CRM, ni Drive, ni ningún otro servicio.
- No escribas fuera de este directorio, y no modifiques `base/` ni `head/`.

## 1. Informe recibido, sin modificar (Codex, 2026-09-26)

<!-- informe-literal:inicio:zqwk -->
Higiene inicial: conforme; solo estaban `MANDATO.md`, `base/`, `head/`, `diff.patch`, `commits.txt` y `_stdout.log`.

# R3 adversarial del diff de crm_ficha — MEJORAS #283 y #288

Objeto: `4209582e3870c743fa28c6bd622403d9cfe9693b..93c1907bf49b6fdb1fee58cac8ddf95f271cf923`. Revisión del código contra el spec rev. 3, el plan rev. 2 y la adjudicación de R2. Las referencias de código son relativas a `head/`; las evidencias de ejecución, a este directorio.

La implementación remedia sustancialmente la R2, pero encuentro **cuatro hallazgos: uno de severidad alta, uno media y dos baja**. Los relevantes para la escritura son una garantía de cierre por ambigüedad que no se sostiene con el filtro de NIF documentado y una declaración de NIF que puede desaparecer en la normalización y aun así obtener VERIFICADA. No propongo ampliar `_COMPLETABLES_*`, desvincular ni pisar datos.

He ejecutado **523 tests existentes** seleccionados, todos verdes (365 de la revisión principal y 158 de regresión adicional), **12 casos de sondas propias**, y el arnés nuevo completo: **20/20 mutantes detectados**. Esto no equivale a ausencia de defectos: las sondas reproducen los hallazgos siguientes. Se ha verificado que los 21 ficheros de `diff.patch` reconstruyen exactamente los correspondientes `head/` desde `base/`, normalizando CRLF a LF. El SHA-256 del informe literal de R2 extraído del acta coincide con `eeca36555fd1af94155d6b9e172fd86d8fed71c74008e63d6b991b242aa981c8`.

## 1. Ninguna escritura sobre una ficha que el YAML contradice

La posición de la fase previa es correcta: `scripts/crm_ficha.py:156-171`, después de dry-run y confirmación, antes de `link_ev_mmc`. Recorre ambos roles completos, acumula excepciones de resolución y GET, y compara la declaración, no el DTO. Por ID se comprueba también el nombre ausente; por NIF/email se conserva el resolutor anterior. Un dato distinto ya visible en la ficha leída, un ID inexistente o un GET que lanza impiden todos los writers. Los tests de integración ejercitan el completado real y acreditan que tampoco sale su PUT. El contrario sin ID pasa por `_exigir_identidad_cierta`; el colaborador conserva una excepción a esa propiedad, detallada en H-02.

**El límite temporal merece una precisión.** Reproduje, para los dos roles, dos declaraciones con el mismo `id_crm: '1128'`, nombre `PARTE-PRUEBA-1`, emails distintos y móvil solo en la segunda. El CRM inicial tiene únicamente el nombre. Ambas comparaciones previas pasan; la primera declaración completa el email y la segunda completa el móvil sobre una ficha cuyo email ya contradice su declaración. La lectura final da FALTA por multiplicidad y DATO por email. También ocurre con dos partes nuevas de nombres distintos y el mismo NIF `00000000T`: la primera crea y la segunda completa su ficha antes de detectar la contradicción.

Evidencia: `test_dos_declaraciones_id_existente_completados_incompatibles` y `test_contradiccion_introducida_por_la_propia_corrida`, en `scratch/tests/test_r3_sondas.py`; trazas `MISMO_ID` y `AUTOCONFLICTO` en `sondas-final.log`. No hay concurrencia externa. **No elevo esto a otro defecto bloqueante**, porque el mandato acepta la ventana entre comparación y escritura y el resultado final falla; sí desmiente que para abrir esa ventana hagan falta varios abogados o una incidencia improbable. La propia corrida cambia el estado entre sus comparaciones y sus writers. El contrato de cero escrituras tiene que leerse con esa limitación; si se quisiera cerrarla, haría falta contrastar también las declaraciones que resuelven a la misma identidad antes de ejecutar el plan.

### H-01 — El NIF ajeno por ID no garantiza el cierre por ambigüedad declarado; el doble oculta el caso

- **Severidad:** alta. **Coste del remedio:** acotado para esta entrada y su prueba; buscar duplicados históricos con formatos arbitrarios sería otra ampliación.
- **Dónde:** `core/crm_ficha.py:310-322` conserva el NIF sin canonizar en los DTO; `tests/test_crm_ficha_integracion.py:87-98` canoniza tanto el NIF almacenado como el consultado. La frontera real está en `core/sudespacho_relations.py:1085-1093`, `1252-1263`, `2412-2424` y `2469-2471`: la búsqueda consulta la forma canónica, mientras el completado por ID escribe el valor del DTO.
- **Evidencia:** `_canonizar_documento` documenta una medición explícita: el CRM normaliza caja y espacios envolventes, **pero no separadores**. `_buscar_registros` envía el filtro `equal`; no recorre todas las fichas canonizando sus valores. `CRMFalso.buscar_registros` sí lo hace. No son equivalentes.
- **Reproducción:** CRM inicial: colaborador 1128 con `nombre: PARTE-PRUEBA-1` y sin NIF; colaborador 1129 con `nombre: PARTE-PRUEBA-2` y `nif_cif: 00000000T`. YAML: `colaboradores: [{nombre: PARTE-PRUEBA-1, id_crm: '1128', nif: '00.000.000-T'}]`. Con el mismo doble salvo el filtro de NIF ajustado al comportamiento documentado, la corrida completa 1128 y sale VERIFICADA. La resolución posterior por `00000000T` **devuelve 1129; no lanza ambigüedad**. La ficha 1128 queda fuera del resultado del filtro. Sonda `test_limite_nif_ajeno_no_cierra_con_separadores`, traza `LIMITE_NIF`.
- **Control de fidelidad:** dos corridas de un contrario nuevo con `nif: '00.000.000-T'` crean una sola ficha con el doble original, pero dos con el filtro documentado; la segunda acaba con SOBRA. Sonda parametrizada `test_nif_con_separadores_convergencia`, trazas `FILTRO`. La escritura de NIF sin canonizar ya existía en base: no la presento como regresión introducida por el diff. El defecto del cambio es certificar la convergencia con un doble más permisivo y acotar el nuevo camino ID con una garantía que esa base no proporciona.
- **Afirmación contradicha:** spec §5: «El daño queda acotado y falla cerrado: con dos fichas del mismo NIF, la siguiente resolución por NIF sale ambigua y **para**». En el caso reproducido no para; se mantiene una identidad duplicada que el criterio fuerte no detecta. Es un daño posterior mayor que el límite aceptado por el mandato.
- **Remedio:** hacer que el NIF utilizable que `crm_ficha` envía al crear/completar use la misma forma canónica que su búsqueda, conservando la declaración original para auditarla; puede limitarse a la construcción de sus DTO y no cambiar a los demás llamadores. Ajustar el doble al filtro documentado y añadir las dos regresiones anteriores. Revalidar con esa prueba la frase de cierre por ambigüedad. Esto no exige ampliar los campos completables ni resolver aquí todos los duplicados históricos.
- **Límite de la evidencia:** no he medido el servidor actual. La reproducción usa el contrato medido que contiene la fuente entregada, no una supuesta consulta en vivo. Si ese comportamiento ha cambiado, hay que acreditarlo y actualizar la fuente; el doble actual no demuestra ese cambio.

## 2. Verificación final

En los tres bloques, `auditar_relaciones` compara Counters de IDs convertidos a texto. No encontré un camino que declare VERIFICADA con un vínculo de más o de menos cuando `get_relaciones` devuelve fielmente el conjunto. Se detectan cero esperados, exceso de copias, colapso de dos declaraciones y FALTA/SOBRA simultáneos.

La lectura de datos recorre todas las partes resueltas, creadas o existentes, de ambos roles (`scripts/crm_ficha.py:293-308`). Un fallo conocido prevalece sobre SIN VERIFICAR. Una lectura caída sin fallo conocido termina con SIN VERIFICAR y código 0, que es el contrato elegido, sin imprimir el literal de éxito. Tras una excepción de escritura se auditan solo los vínculos ya registrados, sin emitir sobrantes, y se sale con 1; no se promete una auditoría completa de datos ni rollback en esa rama.

Los mapas de propiedades coinciden con los payloads y GET entregados: apellidos, NIF, teléfono, provincia y el nombre único del colaborador. La matriz de tests está fijada independientemente de los mapas de producción. El hueco encontrado está en qué significa igualdad después de normalizar:

### H-02 — Un NIF declarado no interpretable se convierte en ausencia y puede salir VERIFICADA

- **Severidad:** media. **Coste del remedio:** acotado.
- **Dónde:** `core/crm_ficha.py:211-237`, especialmente la identidad de la línea 234; `_n_nif`, líneas 423-424; `auditar_datos`, líneas 490-496. Interacción conservada con `core/sudespacho_relations.py:2328-2363`, que no propaga `r.motivo` en el resolutor de colaborador.
- **Reproducción mínima:** ficha de contrario 1128: `{nombre: PARTE-PRUEBA-1}`, sin NIF. YAML: `contrario: {nombre: PARTE-PRUEBA-1, id_crm: '1128', nif: '-- .'}`. La carga lo acepta, la fase previa pasa, se vincula y la corrida termina con código 0 y VERIFICADA. El NIF declarado no consta en el CRM. `_canonizar_documento('-- .') == ''`, igual que la ausencia de `nif_cif`, y la línea 495 trata ambas situaciones como dato igual.
- **Los dos roles:** en colaborador por ID se permite incluso escribir `nif_cif: '-- .'` y certificarlo. La función pura tampoco distingue ese NIF de un campo CRM ausente en ninguno de los roles. Sonda parametrizada `test_nif_no_interpretable_con_id`, trazas `NIF_ID`.
- **Identidad sin ID:** `colaboradores: [{nombre: PARTE-PRUEBA-1, nif: '-- .'}]` pasa la exigencia de identidad. `resolver_parte` devuelve un `motivo` de documento no interpretable, pero `_resolver_colaborador` lo ignora y devuelve ausencia. La primera corrida crea 5000 y sale VERIFICADA; la segunda crea 5001 y luego detecta SOBRA de 5000. Sonda `test_nif_no_interpretable_colaborador_sin_id`, traza `NIF_SOLO`. El resolutor defectuoso ya estaba en base; el nuevo validador y la fase previa no cierran la propiedad que prometen apoyándose en él. Por el camino de contrario sin ID sí se rechaza ese motivo.
- **Afirmaciones contradichas:** spec B.2: «compara cada campo que el YAML declara no vacío»; §1: «cada parte tiene que poder identificarse igual en cada corrida». Conservar el mapping original arregla la pérdida del DTO, pero no la pérdida posterior en el comparador.
- **Remedio:** rechazar, al validar, todo NIF declarado no vacío cuya forma canónica sea vacía, aunque exista email o ID; no permitir que cuente como identidad. Es el mismo cierre que ya se aplica al teléfono reducido a vacío, no una validación fiscal completa del documento. Añadir controles en ambos roles y vías. Si se pretende que el resolutor compartido falle cerrado también para los demás llamadores, propagar `r.motivo` exige su propia regresión y reconocer que se cambia un comportamiento anterior.

## 3. Lectura y validación del YAML

Los dos consumidores usan `leer_yaml_ficha`. `cargar_ficha_yaml` valida la colección entera antes de construir DTO. `apply` comparte la lectura estructural, **no** toda la validación semántica; preserva los tipos inválidos existentes para que la carga posterior los rechace, en vez de convertirlos en texto válido. No he encontrado una migración que vuelva a blanquear un teléfono octal.

Se rechazan repetidas ordinarias con sus líneas, anclas/alias, merge con y sin alias, sintaxis rota, desconocidas, escalares estructurados y valores numéricos de campos de texto. Las sugerencias incluyen todos los candidatos cercanos y no se aceptan como alias. `null`/ausente, catálogo de cliente propio, identidad por ID y canonicalización de sus dígitos tienen caminos diferenciados. Se rechazan provincia desconocida y teléfonos reducidos a vacío. La declaración guardada excluye `id_crm` y solo recorta extremos; conserva el teléfono antes de normalizar el DTO.

Además de H-02, queda un incumplimiento menor del contrato del lector:

### H-03 — El lector no recoge todos los errores estructurales prometidos

- **Severidad:** baja. **Coste del remedio:** acotado.
- **Dónde:** `core/crm_ficha.py:77-88`.
- **Reproducción:** `contrario: {<<: {nombre: A, nombre: B}}` solo informa del merge; no informa de la clave `nombre` repetida, porque el `continue` de la línea 80 no construye ni recorre su valor. Es YAML sintácticamente correcto, por lo que no aplica la excepción declarada para sintaxis rota. Sonda `test_lector_repetida_en_merge`, traza `MERGE_ANIDADO`.
- **Otra arista de la misma comprobación:** `leer_yaml_ficha` acepta `1: x` y devuelve `{1: 'x'}`. Comprueba `ScalarNode`, no que la clave construida sea texto. `cargar_ficha_yaml` lo rechaza después como clave desconocida, pero el lector compartido no entrega el rechazo con línea que promete, y `apply` puede seguir trabajando con ese mapping. Sonda `test_lector_clave_no_texto`.
- **Afirmación contradicha:** spec A.1: «Las repetidas se acumulan en todo el documento» y «una clave que no es un texto [...] también se rechaza con la suya»; docstring de `leer_yaml_ficha`: «TODAS las claves repetidas, alias, merges y claves que no son un texto».
- **Daño acotado:** el merge sí aborta y no se consolida su pérdida. La clave numérica no llega al CRM por `cargar_ficha_yaml`. El defecto es diagnóstico incompleto y contrato desigual del lector, no una escritura CRM demostrada con esa entrada.
- **Remedio:** recorrer también el valor del merge rechazado para acumular los errores y comprobar el tipo de la clave escalar construida. Añadir pruebas combinadas, no solo un error aislado por documento.

## 4. Dictamen sobre los nueve hallazgos de R2

Los identificadores de esta tabla pertenecen a **R2**, no a los hallazgos nuevos numerados arriba.

| Hallazgo R2 | Dictamen | Razón contra el código |
|---|---|---|
| H-01 — identidad contradicha / PUT antes de comparar | **Real**, dentro del alcance declarado | La comparación de todos los datos existentes precede al primer writer; la integración observa el PUT real y exige cero escrituras. No se limita al nombre ni a un espía del CLI. La ventana aceptada sigue abierta, incluso por efectos de la propia corrida; la justificación del límite de NIF ajeno tiene el defecto nuevo H-01 de este informe. |
| H-02 — declaración perdida al normalizar el DTO | **Incompleto** | Se conserva la declaración y se rechazan los teléfonos que desaparecen: el caso original está resuelto. Pero la misma propiedad se vuelve a abrir al normalizar un NIF en la auditoría, H-02 de esta R3. |
| H-03 — provincia asimétrica | **Real** | La provincia YAML se canoniza y ambos lados pasan por normalización de texto. Barcelona/barcelona pasa; Madrid falla; vacío y Sin Asignar se distinguen. M11 del arnés nuevo mata la asimetría. |
| H-04 — excepciones/errores incompletos del lector | **Incompleto** | Los casos originales de lista/mapping como clave, sintaxis rota y dos repetidas ordinarias están resueltos y ejecutados. Quedan los errores anidados bajo merge y claves escalares no textuales de H-03 de esta R3. |
| H-05 — doble que degrada lecturas no declaradas | **Real** | `LecturaNoDeclarada` deriva de BaseException; los helpers no fabrican lecturas ni permiten que el CLI las convierta en SIN VERIFICAR. Los positivos principales exigen el éxito completo. |
| H-06 — aceptación de ID sin consumidor | **Real en head** | Los dos DTO, el validador, los dos resolutores y sus consumidores están conectados. Los tests por ID prohíben búsqueda y creación y exigen completado. `commits.txt` los sitúa juntos en `6e60332`; no hay snapshots intermedios para ejecutar cada frontera histórica. |
| H-07 — incompatibilidades y migraciones de tests | **Real en el resultado final** | Las fixtures tienen identidad sin cambiar su campo objetivo; catálogo real no predeterminado; todos los candidatos de sugerencia; constantes de mensajes. La selección de tests afectada pasa. No infiero de ello el verde histórico de cada commit. |
| H-08 — dry-run que lee CRM | **Real** | El corte está antes de `_fase_previa`; el test con ID impide lecturas y M20 lo detecta por esa guarda. |
| H-09 — integración ausente | **Incompleto** | Hay integración real de resolución y completado, estado entre corridas, fallos de GET/PUT y escrituras observadas. No es cosmética. Su filtro de NIF concede al servidor una normalización que la fuente niega, y así oculta la divergencia de H-01. La matriz de writers tampoco incluye una creación fallida de colaborador. |

Ninguno de los nueve es un remedio meramente cosmético.

## 5. Qué prueban los tests y los mutantes

`_declara_fichas` y `_declara_resolucion` son dobles explícitos de orquestación, no pruebas de deduplicación. La segunda usa prioridad ID/NIF/email solo para indexar la tabla del test; no sustituye la política real en los tests de integración. El caso de dos colaboradores que colapsan conserva una única ficha por ID y el aserto específico de cardinalidad. Los casos migrados a parte creada alcanzan la lectura final, en vez de morir antes en la fase previa.

El CRM en memoria sí ejecuta `ensure_*`, los resolutores y los completados. También implementa comportamiento de servidor: creación, búsqueda, actualización, idempotencia y GET. Por eso «solo transporte» no basta para asumir fidelidad: H-01 demuestra una diferencia concreta. No simula truncamiento/paginación, respuestas GET mal formadas ni fallback legacy operativo. Los tests de fallos de completado son del contrario; el writer de creación de colaborador no tiene la inyección de fallo que sí tiene el contrario. Son coberturas ausentes, no prueba de que esas rutas fallen en producción.

**Arnés nuevo, ejecución y revisión del JSON/JUnit:**

| Mutantes | Resultado observado |
|---|---|
| M01–M04 | Repetidas, diagnóstico de merge y conexión de ambos lectores: detectados. M02 prueba el diagnóstico; el merge sigue rechazado por el constructor alternativo. |
| M05–M07 | Tipos estructurados, identidad ausente y asignaciones cruzadas: detectados por asertos/raises. |
| M08–M11 | Sobrantes, multiplicidad, dato vacío y provincia: detectados por sus diferencias esperadas. |
| M12–M13 | Omitir colaboradores o partes creadas en lectura final: detectado. |
| M14–M15 | Parcial con sobrantes y SIN VERIFICAR ocultando fallo: detectados. M14 falla primero por la desaparición de su aviso de alcance. |
| M16–M17 | Ignorar ID en cada rol: detectado por `NoDebiaLlamarse`, la guarda pertinente de búsqueda/alta. |
| M18 | Quitar fase previa: falla específicamente `crm.escrituras == []`. |
| M19 | Detectado primero por desaparición del diagnóstico, antes del aserto de cero writers. Ejecuté una variante que introduce el writer y conserva el diagnóstico: falla exactamente «link_ev_mmc se llamó». La propiedad sí tiene defensa, aunque la muerte del M19 original por sí sola no la aísla. |
| M20 | Lectura durante dry-run: detectada por `LecturaNoDeclarada`. |

Los 20 originales tienen base verde, ejecución efectiva, rc=1 tras mutar y cero errores de colección/setup. Evidencia: `mutantes-local.log` y `tmp/mutantes_crm_ficha_00e36lap/_informe_mutantes.json`. La variante discriminante de M19 está en `scratch/review_mutantes_extra.py` y `tmp/mutantes_crm_ficha_7or4q4pn/_informe_mutantes.json`.

Faltan ataques para NIF declarado que se vacía, NIF almacenado con separadores y comparación entre declaraciones de una misma identidad. El arnés tampoco contiene mutantes específicos que desactiven el rechazo de claves desconocidas, la validación numérica de ID o el rechazo de teléfonos/provincias imposibles; existen tests de esas reglas, pero no se ha acreditado aquí su sensibilidad mediante esos mutantes. Un 20/20 no prueba exhaustividad.

### H-04 — El M11 reapuntado de P6 se cuenta como muerto por un programa que aborta con AttributeError

- **Severidad:** baja. **Coste del remedio:** acotado.
- **Dónde:** `tests/_mutantes_p6.py:100-107`, clasificación de excepciones en `:330-331` y `main`; consumidor del valor inválido en `core/crm_ficha.py:313`.
- **Reproducción:** ejecutado solo M11 sobre una copia, el arnés P6 anuncia `[muerto]` y sale 0 (`mutante-p6-m11-local.log`). Apliqué el mismo cambio y el mismo test con el arnés estricto nuevo: base verde; mutante ejecutado; `AttributeError: 'str' object has no attribute 'get'`, en `_contrario_de`. El test no llega al aserto del índice ni se obtiene una entrada inválida aceptada: cae al intentar construir el DTO. El clasificador estricto lo marca «MURIÓ POR OTRA COSA». JSON y log de mutantes extra citados arriba.
- **Afirmación contradicha:** el compromiso del spec §6 de que cada mutante muera «por el aserto de su propiedad [...] no [...] por un arnés roto», y el nombre reapuntado «un elemento inválido deja de abortar con su índice». Este mutante sigue abortando, por una excepción ajena al contrato.
- **Remedio:** construir un mutante ejecutable que omita silenciosamente el elemento inválido, modificando también su consumo en la copia, para que el test falle por `DID NOT RAISE ValueError`; o acotar expresamente que se está mutando el tipo de error y comprobarlo como tal. No registrar esa muerte como prueba de que se detecta la pérdida silenciosa de una parte. No requiere cambiar el código de producción.

## 6. Compatibilidad sin id_crm

**No encuentro un cambio de comportamiento en los demás llamadores que construyen los DTO sin ID.** El campo está al final y su defecto es cadena vacía. En contrario, el diff extrae las mismas llamadas a `resolver_parte` y `_exigir_identidad_cierta`; conserva la condición truthy del ID, el completado y la creación. En colaborador, el wrapper conserva `_resolver_colaborador(datos, client=client)` y la condición `is not None`. Los payloads de creación no incorporan el nuevo campo. Los wrappers judiciales siguen compartiendo esos caminos.

La regresión adicional ejecutó `test_sudespacho_relations.py`, `test_sudespacho_relaciones_lectura.py`, `test_crm_ficha.py` y `test_crm_ficha_campos_perdidos.py`: 158 casos, rc=0. No se ha ejecutado la UI viva. H-02 describe un defecto heredado del colaborador, no un cambio oculto de esta refactorización. Añadir el campo cambia la representación estructural del dataclass, pero no encontré un consumidor revisado que serialice todos sus campos como payload CRM.

## 7. Migraciones de tests existentes

No encontré una migración que debilitase la propiedad funcional original:

- Los tests de `None` reciben identidad por otra clave; los dos de todos los campos vacíos vuelven en head a probarlos simultáneamente mediante ID.
- El cliente no predeterminado pasa de una clave fuera del catálogo a `ENGEL_VOLKERS_SPAIN`; mantiene la comprobación de conservación del valor.
- Mapping único, orden de partes y validación de apellidos reciben NIF sintético, sin cambiar sus asertos objetivo. Los negativos de octal mantienen el error de comillas.
- El primer elemento de la colección es ahora válido y el test de validación completa incorpora el espía de cero construcciones: es más discriminante.
- Las lecturas añadidas al CLI están declaradas explícitamente. Los literales de éxito positivos y negativos pasan a la constante real. Los tests de notas y cardinalidad conservan sus asertos específicos.
- Los tres escenarios que la fase previa interceptaría se trasladan a partes creadas para seguir probando la lectura final; el rechazo previo se prueba aparte. No se ha hecho pasar una prueba final por un error anterior.

La salvedad es el **reapuntado del mutante M11**, H-04: no debilita el test de producción, pero sí da una interpretación excesiva de la evidencia de mutación. El estado transitorio de aceptación de ID se conoce solo por los mensajes de commit entregados; no he ejecutado ni reconstruido versiones intermedias inexistentes en el objeto.

## Evidencia de ejecución y no mutación

- `hashes-apertura.json` y `hashes-cierre.json` contienen SHA-256 de bytes de **todos** los ficheros: **1.411 en base y 1.416 en head**. Comparación por ruta y digest: **idénticos**, cero altas, bajas o modificaciones en esos dos árboles. Se conservan los CRLF para esta comprobación.
- La aplicación independiente de los hunks sobre el contenido LF coincide con ambos extremos en los 21 ficheros del diff; inventario en `diff-verificado.json`. Esto verifica coherencia del material, no procedencia Git del archivo sin `.git`.
- Python de sistema indicado por el mandato. Primera selección: los diez ficheros pedidos, incluyendo ambas suites de validación, **365 passed in 23.12s**, rc=0. Salida conservada en la transcripción de herramientas del lanzador. Regresión adicional: **158 casos**, rc=0, `regresion.log`.
- `scratch/tests/test_r3_sondas.py`: **12 casos**, rc=0, `sondas-final.log`. Son reproducciones que afirman el comportamiento observado, no tests que declaren corregidos los defectos. Los datos nuevos usan marcadores sintéticos. No se modificaron los módulos de producción de `scratch` para estas sondas.
- Mutantes: 20 originales detectados en copia local y dos controles extra, con los resultados desglosados en §5. No se ha ejecutado el resto del arnés P6. Un primer intento de su M11 sobre `scratch` falló por permisos de escritura; se verificó que `scratch/core/crm_ficha.py` seguía idéntico a head y se ejecutó después en la copia local mutable.
- **Incidencia del revisor, no del producto:** en el primer intento del arnés nuevo falló la creación de la carpeta temporal. El proceso quedó con TEMP/TMP apuntando a una ruta todavía inexistente; lo interrumpí. `tempfile` admite rutas alternativas y **no puedo acreditar dónde quedó su copia ni garantizar que ese intento no escribiera fuera del directorio**. No uso ese intento como prueba. La repetición fijó `tempfile.tempdir` explícitamente a `C:\t\crm-ficha-diff-r3-0904\tmp`, además de TEMP/TMP, y su JSON acredita la copia local. La prohibición de escritura exterior no se puede certificar para el intento interrumpido; no la doy por cumplida en silencio. Los hashes completos sí acreditan que base/head permanecen intactos.
- No se consultaron CRM, Drive ni otros servicios de red, ni el repositorio real. Los tests utilizan sus dobles de transporte. No se implementó ningún remedio.

## Lo que intenté refutar y NO pude

- Dato distinto preexistente por NIF o ID y segunda parte inválida: la fase previa evita los writers, incluido el PUT interno del completado real, en los casos cubiertos.
- ID inexistente, GET con excepción y dry-run con ID: se preservan las fronteras de error/sin lectura.
- Sobrantes en los tres bloques, faltantes simultáneos y colapso por multiplicidad: los Counters los detectan; no se certifica solo inclusión.
- Omisión de apellidos no completables, pérdida de un dato durante creación y GET/PUT fallidos del completado: la lectura final detecta el resultado ausente. No necesita ampliar `_COMPLETABLES_*` para hacerlo.
- Colaboradores y partes creadas no se saltan la auditoría; los mutantes correspondientes los ponen en rojo.
- Fallo conocido junto a lectura caída: gana el fallo; la parcial no produce falso éxito ni acusa sobrantes de partes todavía sin resolver.
- Repetidas ordinarias, desconocidas, estructuras en campos escalares, teléfonos reducidos a vacío y provincia positiva con distinta caja: las defensas examinadas funcionan.
- Las migraciones de fixtures no sustituyen sus propiedades originales por un ValueError incidental ni por un mero código 0 con SIN VERIFICAR.

## SIN VERIFICAR

- Censo real de las 14 fichas y estados de expedientes/personas del autor. Ningún hallazgo depende de declarar falso ese censo.
- Comportamiento vivo actual de búsquedas y normalizaciones del CRM. H-01 usa la medición documentada en el propio código y una reproducción local explícita; no inventa una medición nueva.
- Semántica real de PUT de contrario: `update_cliente_contrario` documenta incertidumbre entre parcial/reemplazo, mientras el doble usa actualización parcial. No declaro pérdida de campos por esa hipótesis. Tampoco he acreditado paginación/completitud viva, automatismos ni fallback legacy.
- Procedencia de los archivos respecto de los hashes Git y verdes intermedios de cada commit; solo se dispone de los dos archivos extraídos, patch y mensajes. La coherencia del diff y la inmutabilidad sí están verificadas.
- Suite completa del repositorio, UI interactiva y 38 mutantes restantes de P6. La cobertura ejecutada se enumera arriba y no se extrapola.
- Ubicación de temporales del primer intento interrumpido del arnés, según la incidencia declarada.
- El objeto no me ha desbordado: he respondido los siete puntos y contrastado los nueve remedios. Las limitaciones anteriores son de acceso, evidencia histórica y alcance de pruebas, no hallazgos considerados refutados sin revisión.

REQUIERE-REVISION
<!-- informe-literal:fin:zqwk -->

## 2. Evidencia verificada por mí al adjudicar

- **Digest.** Recomputado sobre el `INFORME.md` entregado (UTF-8, LF, un único salto final):
  `11fe7d11c28bef7b720333c69fa2959384b0e01535bdf389341eabda60b9cb3d`, **el mismo que declara el
  revisor en su mensaje final** (`_ultimo_mensaje.txt`). El fichero venía ya en LF con un solo salto,
  así que el digest del crudo y el del canónico coinciden: la cadena se verifica contra la salida del
  revisor, no solo contra sí misma.
- **La ronda terminó, y así se supo.** Vigía armado antes de lanzar, con las dos salidas —fin y
  muerte—, y un segundo vigía (`Monitor`) por si el primero caía por su tope de tiempo. Señal de fin:
  el `_exit.txt` del lanzador (`exit=0`, 09:24:10) y el `-o` (09:24:09); `INFORME.md` terminado a las
  09:24:00; ningún `codex.exe` vivo después. Ninguna de las cuatro muertes conocidas ni un `ERROR:` en
  el log.
- **Modelo y esfuerzo, releídos:** `gpt-6-astra` · `medium` en el `turn_context` de
  `rollout-2026-09-26T09-09-20-01a0dc8c-09c5-7881-9ed6-6c9ccf69f9ef.jsonl` (`originator: codex_exec`,
  CLI `0.155.0-alpha.16.4`) y en la cabecera del `_stdout.log`. Binario elegido por tener
  `codex-code-mode-host.exe` al lado (`13995fba801849b0`; el de la R2, `80f78947ad880e6e`, ya no
  existía) y **sondado antes** con estos tres flags: `VIVO`. La velocidad `default` se **afirma**
  desde el lanzador conservado (`C:\t\crm-ficha-diff-r3-0904-lanzador\_lanzar.ps1`) y la ausencia de
  avisos de `service tier` en el log; no se puede releer.
- **El objeto no se tocó, y lo mido yo, no solo él.** Antes de lanzar tomé mi propia huella de los
  2.827 ficheros de `base/` y `head/` (fuera del directorio del revisor); al cerrar, **cero
  diferencias**. Coincide con su comparación (1.411 + 1.416, idénticos).
- **La incidencia de temporales que declara, localizada.** Su primer intento del arnés, interrumpido,
  dejó un directorio en **mi** `%TEMP%`: `C:\Users\tnm33\AppData\Local\Temp\mutantes_crm_ficha_4r3tdb0d`
  (creado a las 09:11:07, la hora de su `mutantes.log` vacío), y es exactamente lo que él dijo no
  poder acreditar: una escritura fuera de su directorio. **Su contenido no lo he podido leer**:
  lo creó el proceso aislado del revisor y mi sesión no puede listarlo ni leer sus permisos
  (comprobado el 2026-09-26, al revisar los temporales antes de borrarlos). Por cómo lo crea el
  arnés —`tempfile.mkdtemp` y una copia de `core/`, `scripts/` y `tests/` del objeto— solo puede
  contener código del repo, que no tiene datos de cliente; **eso es deducción, no lectura**. La
  repetición del arnés sí fijó `tempfile` dentro de su directorio (`tmp/mutantes_crm_ficha_00e36lap`
  y `…7or4q4pn`).
- **Los cuatro hallazgos, reproducidos contra la fuente y no contra el informe:**
  - **H-01.** `core/crm_ficha.py` construía los DTO con el NIF tal como viene (`_valor`), y los
    `_rest_post_*` y `_completar_colaborador_existente` lo escriben así en `nif_cif`; la búsqueda de
    `resolver_parte` manda la forma canónica con filtro `equal`, y la docstring de
    `_canonizar_documento` deja medido que el CRM normaliza caja y espacios **pero no separadores**.
    Y mi doble (`CRMFalso.buscar_registros`) canonizaba los dos lados: era más permisivo que el
    servidor y certificaba una convergencia que con un NIF escrito con puntos no existe.
  - **H-02.** `_problemas_parte` contaba como identidad cualquier NIF no vacío (`_hay`), y
    `auditar_datos` compara `_canonizar_documento('-- .') == ''` con la ficha sin NIF: «igual». El
    `_resolver_colaborador` que ignora `r.motivo` es anterior a este diff.
  - **H-03.** La rama del merge de `_mapping_sin_perdida` hacía `continue` sin construir el valor, y
    una clave escalar que no es texto (`1: x`) pasaba porque solo se miraba `ScalarNode`.
  - **H-04.** Con el M11 re-apuntado, la validación ya no informa del elemento y
    `_contrario_de("esto-no-es-un-mapping")` revienta en `d.get` con `AttributeError`; el arnés de P6
    no lo cuenta como roto porque su lista `_ROTO` excluye `AttributeError` a propósito.
- **La observación que no eleva a hallazgo, también reproducida:** dos declaraciones que resuelven a
  la misma ficha —el mismo `id_crm`, o dos partes nuevas con el mismo NIF— pasan cada una la fase
  previa contra el estado **anterior** a la corrida, y la primera completa lo que la segunda
  contradice. El spec rev. 3 §5 decía que esa ventana solo la abre otra sesión trabajando a la vez:
  es inexacto, la abre la propia corrida.
- **Adjudicación:** `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md` §10.
