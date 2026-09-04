---
tipo: revision-adversarial
objeto: "diff de la lectura de relaciones del CRM: get_relaciones + verificacion por resultado en crm_ficha"
objeto_rev: "rama claude/repo-expediente-apertura-a4d1e6, commit b55a21f"
commit: b55a21f
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: r7kq
sha256_informe: 86596f9e68568eba96a0ef23a3682bdfba10e991903476e8ba09e22932632dcc
adjudicado_en: docs/superpowers/specs/2026-09-04-crm-lectura-relaciones-r1-adversarial-review.md §3
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revision adversarial R1.** El §1 conserva la voz del revisor sin una coma
> cambiada; el §2 es la evidencia que verifique por mi cuenta y el §3 mi adjudicacion.
>
> **Donde vive la adjudicacion, y por que aqui.** La regla de `CLAUDE.md` es que la
> adjudicacion va *embebida en el spec o el plan revisado*. **Este cambio no tiene
> ninguno de los dos**: nacio de una pregunta de Nikolai durante una sesion de
> operacion —«por que no haces todo por API»— y se construyo directo. Crear un spec
> retrospectivo solo para tener donde adjudicar seria papeleo, asi que la adjudicacion
> va en el §3 de esta misma acta, **declarado en el frontmatter** para que nadie la
> busque en otro sitio. No es la forma preferente y se dice, en vez de disimularlo.
>
> **Una ronda y no dos, por radio de dano** (`PLAN.md` fila #13): la pieza **lee**. No
> decide quien puede escribir sobre que copia y no puede destruir ni corromper datos de
> cliente. Lo unico que escribe —`crm_ficha`— ya escribia antes de este cambio y sus
> escrituras no se tocan: lo que se anade es la comprobacion posterior.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:r7kq -->

# Revisión adversarial R1 — diff `aa3380b..b55a21f`

## Alcance y controles

Se revisó el contenido de `C:/t/rev1/head/` contra `C:/t/rev1/base/` y `C:/t/rev1/DIFF.patch`. Las copias no contienen `.git`; por tanto, no se acredita genealogía, solo contenido.

Hash de apertura (comando exigido):

```text
> cd /c/t/rev1/head && find . -type f -exec sha256sum {} + | sort -k2 | sha256sum
0d0915397f21b93941bdab04c6e5325890750e8653f4c4253e1ab65b2e28b952 *-
```

Hash de cierre, después de todas las lecturas y ejecuciones:

```text
> cd /c/t/rev1/head && find . -type f -exec sha256sum {} + | sort -k2 | sha256sum
0d0915397f21b93941bdab04c6e5325890750e8653f4c4253e1ab65b2e28b952 *-
```

El objeto no cambió.

Pruebas afectadas, ejecutadas sobre copia escribible `C:/t/rev1/informe/verify/`:

```text
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -B -m pytest -q tests/test_sudespacho_relaciones_lectura.py tests/test_crm_ficha_cli.py -p no:cacheprovider --basetemp bt
...................                                                      [100%]
```

Los 19 tests verdes no refutan los hallazgos siguientes.

## H-01 — El CLI declara la ficha `VERIFICADA` sin verificar Notas ni los datos de las partes

**Severidad:** ALTO

**Fichero y línea:** `scripts/crm_ficha.py:111-113,125-130,140-159`; promesa relacionada en `docs/INTEGRACION_SUDESPACHO.md:1082-1084,1729-1732,1748-1751`.

**Cómo lo comprobé:**

```text
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -B .\tmp_cli_agent\repro_cli.py
===== notes =====
exit_code=0
Plan ficha CRM:
  - cliente propio EV_MMC_SPAIN (id 2) → exp 606
  - Notas (update_expediente)
OK cliente propio EV_MMC_SPAIN (id 2) vinculado (exp 606)
OK Notas actualizadas
Verificación: expediente 606 Numero_Expediente=49
  [ok] clientes_propios id=2
OK ficha CRM completada y VERIFICADA por lectura: BaRS11 - Falsa 1 (W-NOTES) - Vuelta
```

La reproducción hace que el PUT y el GET devuelvan las Notas anteriores. El código descarta la respuesta de `update_expediente`, no compara `rec["Notas"]` y, para las relaciones, reduce cada ficha a su `id`. Tampoco contrasta nombre, email, móvil o NIF aunque `get_relaciones()` los entregue.

**Escenario de fallo concreto:** se solicita `Notas='<p>nuevo</p>'`; el CRM conserva `'<p>anterior</p>'` (o crea/vincula el id correcto con email/NIF equivocados) → todas las relaciones esperadas existen → salida `VERIFICADA` y código 0. Es un falso positivo sobre la finalidad principal del comando y contradice la documentación que promete verificar «la ficha entera».

## H-02 — Dos partes lógicas con el mismo id se validan con una sola relación

**Severidad:** MEDIO

**Fichero y línea:** `scripts/crm_ficha.py:107-110,140-159`.

**Cómo lo comprobé:** mismo comando de H-01; salida exacta del caso `dups`:

```text
===== dups =====
exit_code=0
OK colaborador id=776 (existente) vinculado
OK colaborador id=776 (existente) vinculado
Verificación: expediente 606 Numero_Expediente=49
  [ok] clientes_propios id=2
  [ok] colaboradores id=776
  [ok] colaboradores id=776
OK ficha CRM completada y VERIFICADA por lectura: BaRS11 - Falsa 1 (W-DUPS) - Vuelta
```

**Escenario de fallo concreto:** el YAML contiene ANA (`ana@…`) y BEA (`bea@…`); por una deduplicación errónea ambas escrituras devuelven `776`; la lectura solo contiene una relación a `776` → `presentes` es un conjunto y el mismo miembro satisface las dos entradas de `esperado` → `VERIFICADA`. No se comprueba que los dos sujetos lógicos existan ni que el email leído corresponda a cada uno.

## H-03 — Un fallo tardío evita auditar las escrituras parciales ya afirmadas como `OK`

**Severidad:** MEDIO

**Fichero y línea:** `scripts/crm_ficha.py:92-120,125-159`.

**Cómo lo comprobé:** mismo comando de H-01; salida exacta del caso `partial`:

```text
===== partial =====
exit_code=1
OK cliente propio EV_MMC_SPAIN (id 2) vinculado (exp 606)
OK contrario id=1099 (existente) vinculado
OK colaborador id=776 (existente) vinculado
[ERROR] Falló una escritura al CRM (RuntimeError('segundo colaborador caido')). Re-ejecutar es seguro: contrario/colaboradores deduplican por NIF/email.
get_relaciones_calls=0
```

**Escenario de fallo concreto:** cliente, contrario y primer colaborador devuelven éxito; falla el segundo colaborador → el `except` sale con código 1 antes de `get_relaciones()` → las tres escrituras parciales que el CLI ya imprimió como `OK` no se contrastan. No es un falso éxito global, pero incumple el contrato declarado de comprobar por lectura aquello que la corrida afirma haber vinculado y deja el estado parcial sin auditar.

## H-04 — La guarda de red se traga su propia alarma y no cubre las demás rutas al CRM

**Severidad:** ALTO

**Fichero y línea:** `tests/test_crm_ficha_cli.py:158-171`; captura que neutraliza la alarma en `scripts/crm_ficha.py:125-138`.

**Cómo lo comprobé:**

```text
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -B .\tmp_cli_agent\repro_cli.py
===== guard =====
exit_code=0
[AVISO] No se pudieron LEER las relaciones (AssertionError('get_relaciones salio a la red en un test; mockealo explicitamente')); los vínculos quedan SIN VERIFICAR, que no es lo mismo que mal.
OK ficha CRM completada: BaRS11 - Falsa 1 (W-GUARD) - Vuelta
===== otherroute =====
exit_code=0
[AVISO] GET de verificación falló (AssertionError('GET REAL BLOQUEADO POR LA REPRODUCCION')); revisa manualmente el CRM
[AVISO] No se pudieron LEER las relaciones (AssertionError('guarda local get_relaciones')); los vínculos quedan SIN VERIFICAR, que no es lo mismo que mal.
OK ficha CRM completada: BaRS11 - Falsa 1 (W-OTHERROUTE) - Vuelta
httpx_get_calls=1
attempted_url=https://api-crm-commons-pro.sudespacho.biz/api/element_register/extrajudiciales/606?properties=costas,cuantia,Fecha_alta,fecha_alta_hist,historico,intereses,Notas,numero_anterior,Numero_Expediente,online,Profesional,Referencia_Cliente,referencia_historico,Referencia_Propia,saldo_cobrado,saldo_facturado,saldo_no_facturado,saldo_pendiente,serie_expediente,Tipo_Asunto,Tipo_Procedimiento,total,total_pendiente,profesional_asignado,tags,tnm_posicionprocesal,tnm_siniestro,dias_sin_actuaciones,id,grupo_contable_id,id_creador,id_ultimo_modificador,fecha_creacion,fecha_ultima_modificacion
```

Además, al añadir solo en la copia una aserción `assert "SIN VERIFICAR" not in r.output` al test existente `test_crm_ficha_orquesta_todo`, éste dejó de pasar:

```text
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest -q tests/test_crm_ficha_cli.py::test_crm_ficha_orquesta_todo --basetemp b2
FAILED tests/test_crm_ficha_cli.py::test_crm_ficha_orquesta_todo - AssertionError
```

**Escenario de fallo concreto:** un test olvida mockear `get_relaciones()` → `_prohibido` sí se ejecuta, pero `except Exception` convierte el `AssertionError` en aviso y código 0; el test puede pasar por la razón equivocada. Si olvida mockear `get_expediente`, `update_expediente`, `link_ev_mmc` o un `ensure_*`, la fixture ni siquiera los intercepta y puede alcanzar el tenant real. Esto es especialmente grave para las rutas de escritura.

Control adicional: con una barrera amplia sobre `httpx`, `requests`, `urllib` y sockets, los 11 tests actuales no intentaron salir por otra ruta:

```text
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -B -m pytest C:\t\rev1\head\tests\test_crm_ficha_cli.py -q -p no:cacheprovider -p network_guard_plugin --basetemp bt_network
...........                                                              [100%]
```

Esto describe el estado actual, pero no convierte la fixture parcial en la garantía que su comentario anuncia.

## H-05 — `_registro_de_la_clave` elimina silenciosamente valores válidos falsy

**Severidad:** MEDIO

**Fichero y línea:** `core/sudespacho_relations.py:1253-1261`; cobertura insuficiente en `tests/test_sudespacho_relaciones_lectura.py:25-33,151-157`.

**Cómo lo comprobé:**

```text
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe audit_repro.py
FALSEY_VALUES {'colaboradores': [{'id': '40'}]}
```

La entrada contenía `activo=False`, `orden=0` y `email=''`, usando `property` tanto como cadena como objeto. Los tres campos desaparecieron por `if nombre and valor`.

**Escenario de fallo concreto:** la API devuelve una property booleana desactivada, un contador cero o un campo presente pero vacío → la función devuelve la ficha sin esa property → el consumidor no puede distinguir valor falso/vacío de campo ausente. Contradice `{id, ...valores}` y la promesa documental de traer los valores de la ficha.

## H-06 — Formas alternativas o repetidas del cuerpo producen pérdida silenciosa o errores inconsistentes

**Severidad:** MEDIO

**Fichero y línea:** `core/sudespacho_relations.py:1228-1239,1243-1263`.

**Cómo lo comprobé:**

```text
> $env:PYTHONDONTWRITEBYTECODE='1'; C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -B .\tmp_rel_agent\repro.py
DUPLICATE_ELEMENT={"colaboradores": []}
MISSING_ELEMENT={"facturas": []}
REGISTRIES_NONEMPTY_LIST=EXC AttributeError: 'list' object has no attribute 'items'
REGISTRIES_EMPTY_LIST={"colaboradores": []}
REGISTRIES_NONE={"colaboradores": []}
ENTRADAS_NONE={"colaboradores": [{"id": "6"}]}
DICT_VALUE_IS_RECORD={"colaboradores": [{"id": "5"}]}
TOP_LEVEL_DICT={}
TOP_LEVEL_NONE={}
```

**Escenario de fallo concreto:** dos bloques `colaboradores`, el primero con id `1` y el segundo vacío → `salida[hijo] = vinculos` sobrescribe el primero y afirma cero vínculos. Un bloque sin `element` o un envoltorio superior objeto se descarta como lectura vacía; `registries` como registro-dict conserva solo el id y pierde la ficha. Si `registries` es lista, `[]` se acepta como vacío pero una lista no vacía lanza `AttributeError`: el comportamiento depende de la cardinalidad, no del tipo. No hay validación que convierta estas formas en «no se pudo leer» de manera inequívoca.

Comprobaciones sin defecto en estas ramas: las claves numéricas y de cadena casan mediante `str`, y `property` como cadena u objeto conserva valores truthy.

## H-07 — Los tests siguen verdes si se elimina `x-api-key`

**Severidad:** MEDIO

**Fichero y línea:** `tests/test_sudespacho_relaciones_lectura.py:164-172`; comportamiento no defendido en `core/sudespacho_relations.py:1205-1209`.

**Cómo lo comprobé:** mutación solo en la copia `tmp_docs_agent/mutant_auth`, reemplazando la línea 1206 por `headers = {}`:

```text
> Select-String -Path core\sudespacho_relations.py -Pattern '^    headers = \{\}'
1206:     headers = {}  # MUTANTE: elimina la autenticacion exigida por el contrato
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -B -m pytest tests/test_sudespacho_relaciones_lectura.py -q -p no:cacheprovider --basetemp bt4
........                                                                 [100%]
```

**Escenario de fallo concreto:** una refactorización elimina o renombra `x-api-key` → producción recibe 401/403 → los ocho tests continúan verdes porque `test_usa_la_ruta_related_register` solo inspecciona la URL, no cabeceras, `Accept`, timeout ni cardinalidad de llamadas.

## H-08 — La documentación y el test definen contratos opuestos para hijos sin vínculos

**Severidad:** MEDIO

**Fichero y línea:** `docs/INTEGRACION_SUDESPACHO.md:1729-1732`; `core/sudespacho_relations.py:1190-1193`; `tests/test_sudespacho_relaciones_lectura.py:44-70,138-144`.

**Cómo lo comprobé:**

```text
> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe audit_repro.py
EMPTY_BODY {}
```

El fixture, descrito como forma «EXACTA», incluye `{"element":"facturas","registries":{}}` y el test exige `rel["facturas"] == []`. El docstring de `get_relaciones()` promete asimismo que un elemento relacionable sin vínculos aparecerá con lista vacía. §15.5 afirma lo contrario: «uno por elemento hijo que tenga vínculos (los que no tienen no aparecen)».

**Escenario de fallo concreto:** si el cuerpo real sigue §15.5 y omite `facturas`, `get_relaciones()` devuelve `{}` → el llamador no puede distinguir «facturas es relacionable y no tiene vínculos» de «facturas no es relacionable», pese a la promesa del docstring. El test pasa únicamente porque fabrica el bloque que la documentación dice que el servidor no envía.

## Limitaciones declaradas

- Orden aleatorio: **SIN VERIFICAR**. El comando `python -m pip show pytest-randomly` devolvió `WARNING: Package(s) not found: pytest-randomly`.
- Consistencia eventual de `related_register` contra el tenant real: **SIN VERIFICAR**. Una única lectura inmediata podría causar falsos `FALTA`; no se hizo tráfico real.
- `ficha.contrario is None`: no se encontró defecto por sí solo; el modelo lo declara opcional y el CLI no afirma haber escrito un contrario en ese caso.
- Claves de `registries` numéricas/cadena y `property` cadena/objeto con valores truthy: comprobadas y correctas en los arneses.

VEREDICTO: NO-SHIP

<!-- informe-literal:fin:r7kq -->

## 2. Evidencia verificada por el adjudicador

- **H-04 CONFIRMADO ejecutándolo, y es el más caro:** al sustituir la guarda por una que
  corta `httpx` y hereda de `BaseException`, **murieron cinco tests** —
  `test_crm_ficha_orquesta_todo`, `test_crm_ficha_cliente_propio_engel_volkers_vincula_id_27`,
  `test_crm_ficha_falla_limpio_si_writer_revienta_mid_run` y los dos de la clase nueva—.
  Los cinco pasaban antes **saliendo a la red**. La guarda vieja no era débil: era inerte.
- **H-01 CONFIRMADO por reproducción propia:** con `get_expediente` devolviendo unas Notas
  distintas de las escritas, la versión revisada imprimía `VERIFICADA por lectura` y salía 0.
  Con el arreglo, `[FALTA] Notas` y salida 1.
- **H-05 y H-06 CONFIRMADOS leyendo la fuente contra su vecina:** `_parse_values` de
  `core/sudespacho_create.py:1583` **no filtra** valores; mi `if nombre and valor` era una
  desviación mía respecto de la función hermana del mismo repo, no una convención heredada.
- **H-07 CONFIRMADO, y mi propio arnés lo tapaba.** El mutante que borra `x-api-key`
  figuraba como *superviviente* en mi ronda de mutación y **no lo era**: hay cuatro líneas
  `headers = {…}` idénticas en el fichero y `str.replace(…, 1)` mutaba la de otra función.
  Con el ancla corregida (contexto de la URL) muere en `test_usa_la_ruta_related_register`.
- **H-08 CONFIRMADO contra la corrida real:** el cuerpo que devolvió el expediente 634 trae
  **tres** bloques, todos con vínculos. El bloque `facturas` vacío de mi fixture **no salió
  del CRM**; lo puse yo y describí el conjunto como «la forma EXACTA que devolvió el CRM».
- **Lo que NO pude verificar:** la consistencia eventual de `related_register` tras una
  escritura. Una sola corrida no mide eso, y no se declara medido.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-04) — NO-SHIP, remediado

- **Objeto revisado:** diff `aa3380b..b55a21f` — `get_relaciones` + verificación por resultado en `crm_ficha`
- **Ronda:** 1
- **Revisor:** Codex
- **Informe recibido:** 2026-09-04, `sha256` en el frontmatter
- **Hallazgos:** 8 recibidos · **8 confirmados** · 0 refutados · 0 escalados
- **Remediado en:** `4ac83d5` y `622cc24`

**8 de 8 confirmados y ninguno refutado.** No hay nada que discutirle: el revisor ejecutó
—copió el árbol, corrió los 19 tests, escribió arneses propios y mutó en su copia— y cada
hallazgo se sostiene contra la fuente, no contra la seguridad con que venía redactado.
El objeto no se mutó: `sha256` idéntico al abrir y al cerrar.

**Lo que hay que llevarse, y es más grande que los ocho hallazgos:** *cuatro de los ocho
son el mismo defecto que este cambio existía para arreglar, cometido por mí un nivel más
abajo.* El cambio predica «un status no es un resultado» y «no pude leer no es no hay», y
yo escribí un parser que devuelve vacío ante cuerpos que no entiende (H-06), una
verificación que declara `VERIFICADA` sin mirar las Notas que acababa de escribir (H-01),
una guarda de red cuyo grito se traga el propio `except` que vigila (H-04), y una fixture
que se presenta como medida y trae material inventado (H-08). **Escribir la propiedad en
prosa no la instala en el código de al lado.**

### Los ocho, con lo que se cerró en cada uno

| # | Sev. | Veredicto | Frontera cerrada — no el ejemplo |
|---|---|---|---|
| H-01 | ALTO | confirmado | **Se contrasta TODO lo que la corrida afirma haber escrito**, no las relaciones. Las Notas entran en la comprobación; discrepancia → salida 1 |
| H-02 | MEDIO | confirmado | Se compara **cardinalidad**, no pertenencia: `presentes` era un `set` y un vínculo satisfacía a dos partes distintas |
| H-03 | MEDIO | confirmado | Un fallo a mitad **audita lo ya escrito** antes de rendirse; sigue saliendo 1 |
| H-04 | ALTO | confirmado | La guarda corta **`httpx` entero** (la clase, no una función) y hereda de `BaseException`, que ningún `except Exception` atrapa |
| H-05 | MEDIO | confirmado | La capa de lectura **copia** los valores, incluidos `False`, `0` y `""`. Filtrar es de quien presenta |
| H-06 | MEDIO | confirmado | **Toda forma inesperada del cuerpo levanta.** Y dos bloques del mismo `element` se acumulan, no se pisan |
| H-07 | MEDIO | confirmado | El test de la petición cubre **la petición entera**: URL, `x-api-key`, `Accept` y timeout |
| H-08 | MEDIO | confirmado | La fixture **declara qué es medido y qué sintético**; docstring y §15.5 dicen los dos lo que el servidor hace |

### Lo que la remediación destapó por su cuenta

**Al activar la guarda de verdad murieron cinco tests** que salían a la red y pasaban por
la razón equivocada — incluidos dos preexistentes al cambio. Van mockeados
explícitamente, que es lo que la guarda pide.

**Y el arnés de mutación mentía en un punto.** `M10` (borrar `x-api-key`) figuraba como
**superviviente**, y no lo era: hay **cuatro** líneas `headers = {…}` idénticas en
`sudespacho_relations.py` y `str.replace(…, 1)` mutaba la de **otra función**. El mutante
nunca tocó la frontera que decía probar. Corregido anclando con el contexto de la URL.
Es la lección de `feedback-mutacion-vale-por-su-mutante` en su forma más barata de pasar
por alto: *un mutante mal apuntado no informa ni cuando muere ni cuando sobrevive.*

**Y el test de la guarda usaba la red real como oráculo:** llamaba a `httpx.post` contra
el host de producción esperando que la guarda lo cortara; con la guarda debilitada la
llamada **salía de verdad**, devolvía un 404 sin lanzar, y el test pasaba. Un test que
prueba «no se sale a la red» saliendo a la red. Rehecho contra un host `.invalid` y
comprobando por tipo.

### Cobertura tras remediar

**13 mutantes, 13 muertos**, cada uno por sus fronteras previstas — incluidos dos sobre la
**propia guarda** (`M19` la devuelve a `Exception`, `M20` la reduce a `httpx.get`), porque
un guard sin prueba de que muerde no es un guard, y éste fue la prueba de ello.

### Lo que queda SIN VERIFICAR, declarado

- **Orden aleatorio:** el revisor no tiene `pytest-randomly` y lo declaró correctamente
  como no verificado. Lo cubre el autor: suite completa con semillas **777 y 31337**.
- **Consistencia eventual de `related_register`** contra el tenant real: no medida. Si el
  CRM tardase en reflejar una escritura, la lectura inmediata daría un `FALTA` falso. No
  se observó en la corrida real sobre el expediente 634, pero **una corrida no es una
  medición de consistencia** y así queda dicho.
