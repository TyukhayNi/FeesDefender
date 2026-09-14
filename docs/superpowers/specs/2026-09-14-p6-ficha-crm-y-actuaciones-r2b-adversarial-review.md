---
tipo: revision-adversarial
objeto: core/sudespacho_actuaciones.py
objeto_rev: "1"
commit: 8aed442
ronda: "2"
revisor: Claude Code (subagente)
veredicto: NO-SHIP
marcador_nonce: k4qz
sha256_informe: ca689c91f5b4636df5b6788abc5268e21e66cb031c53e5b4c382290af9dacd92
adjudicado_en: docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md §7
---

# Acta — R2 adversarial sobre el DIFF de P6, **segundo revisor**

Acta hermana de `…-r2-adversarial-review.md`. La R2 corrió con **dos revisores en paralelo** y
esta archiva la voz del segundo: un subagente despachado con `superpowers:requesting-code-review`
sobre el mismo diff `530d033..8aed442`.

| | |
|---|---|
| Revisor | **Claude Code (subagente `general-purpose`)** — no es Codex, y no se registra como tal |
| Objeto | el diff `530d033..8aed442`, leído desde el árbol de trabajo |
| `sha256` del informe | `ca689c91f5b4636df5b6788abc5268e21e66cb031c53e5b4c382290af9dacd92` |
| Veredicto | **NO-SHIP** |
| Hallazgos | 13 |

**Por qué existe un segundo revisor y qué NO sustituye.** La revisión obligatoria de la casa es
la de Codex, en solo lectura sobre copia externa. Ésta es una lectura **adicional** del mismo
diff con otro instrumento, y se archiva porque encontró cosas que Codex no vio. No cubre el
requisito: si la de Codex no hubiera corrido, la cobertura sería **ausente** igual.

**Los dos coinciden en cinco hallazgos y cada uno vio cosas que el otro no** — el recuento
conjunto son **19 hallazgos distintos**, agrupados en las 13 categorías del §7 del spec.

## 0. Mandato, literal

<!-- mandato-literal:inicio:k4qz -->
El encargo se despachó con la plantilla de `superpowers:requesting-code-review`
(`skills/requesting-code-review/code-reviewer.md`), rellenada con: descripción del trabajo
(las tres piezas de P6), el plan y el spec como requisitos
(`docs/superpowers/plans/2026-09-14-p6-ficha-crm-y-actuaciones.md` y
`…-p6-ficha-crm-y-actuaciones-design.md` rev. 2), `BASE_SHA=530d033` y `HEAD_SHA=8aed442`.

**No se archiva como literal un texto que no se conservó carácter a carácter.** El prompt exacto
consta en el transcript de la sesión (entrada `Agent`, `description="Review P6 code changes"`);
aquí se describe su contenido en vez de transcribirlo de memoria, que es lo que este contrato
existe para impedir.
<!-- mandato-literal:fin:k4qz -->

## 1. Informe recibido, sin modificar (subagente, 2026-09-14)

**Procedencia, que importa para lo que este acta acredita:** el `outputFile` de la tarea volvió
**vacío** (0 bytes), así que el texto se recupera de la **notificación de la tarea** en el
transcript de la sesión, que es donde llegó íntegro. Se archiva tal cual, con su preámbulo.
El digest se computó sobre ese texto.

<!-- informe-literal:inicio:k4qz -->
Revisión completada. Informe:

---

# Revisión adversarial del diff `530d033..8aed442` (P6)

**Alcance:** 14 ficheros, +3.261/−29. Suite de las cuatro piezas: **82 passed** (`pytest -q -p no:randomly tests/test_resolver_parte_aper71.py tests/test_crm_ficha_n_contrarios.py tests/test_sudespacho_actuaciones.py tests/test_crm_ficha_cli.py`). Suites colindantes (`test_sudespacho_relations`, `test_crm_dedup_incertidumbre`, `test_crm_ficha`, `test_crm_ficha_validacion{,_r1}`, `test_crm_dedup_partes`, `test_crm_ficha_campos_perdidos`): **263 passed**, sin regresiones.

## Fortalezas

- El reordenamiento de `resolver_parte` (§2.1) está implementado **paso a paso** como el diseño lo enuncia, y la lógica antigua de intersección se conserva exactamente donde seguía siendo correcta (`len(ids_nif)==1` → `conflicto` si no está en el buzón).
- `_estado_documento` y la comparación canónica en los **dos** lados están bien cerradas; `test_h02_…` reproduce el caso `1.234.567-k` vs `1234567K` con un doble que simula la búsqueda **literal** del CRM (no con el doble cómodo que canoniza).
- `_contrarios_de` valida la colección entera **antes** de construir nada (`fuera` se calcula sobre todo el `raw`), y el lector es puro: no hay escritura posible a medias.
- Ningún test nuevo toca el CRM ni el árbol de producción — verificado por grep: cero `httpx`, cero `SUDESPACHO_API_KEY`, y las dos únicas escrituras (`test_crm_ficha_n_contrarios.py:25`, `test_sudespacho_actuaciones.py:297-301`) cuelgan de `tmp_path`.
- El arnés `tests/_mutantes_p6.py` porta las dos correcciones de P4 (restauración armada antes de mutar, `rc=4` separado del rojo) **y** exige verde previo por mutante. El test `test_el_cli_vincula_TODOS_los_contrarios…` declara en su docstring que nació de un superviviente: eso es el arnés funcionando.
- `resolver_destino` es la primera sentencia de `alta_actuacion` (`:474`): ningún POST puede precederla.

---

## Hallazgos

### H-01 — Crítico — el recibo se pierde justo después de escribir en el CRM
`core/sudespacho_actuaciones.py:101` (`_items` → `resp.json()`), consumido sin protección en `:457` (`verificar_actuacion_vinculada`) y llamado sin `try` en `:502-503`.

`verificar_actuacion_vinculada` declara en su propio `except` que «no poder verificar NO es haber verificado → `return False`», pero el `try` solo envuelve `c.get`. `_items` hace `resp.json()` **fuera** de él: un `200` cuyo cuerpo no sea JSON levanta y la excepción **atraviesa `alta_actuacion` entera**, que no envuelve el paso 6. El llamador recibe una excepción en vez de un `Recibo`, sin el `act_id` — y la respuesta natural a una excepción es repetir el alta, que es exactamente el escenario huérfano N/M que R1/H-04 y el `Recibo` existen para impedir.

Es además **el mismo defecto que el módulo hermano documenta como ya pagado**: `core/sudespacho_relations.py:1106-1110` dice literalmente que una ronda anterior midió que «el `try` solo envolvía `r.json()`» y que ahora «el parseo entero está cubierto».

Entrada concreta y verificación (sonda de lectura, cliente inyectado):
```
gets=[destino_ok, {"items": []}, Resp(200, cuerpo_no_JSON)]
posts=[Resp(201, {"id": "N"}), Resp(201, {})]
→ LEVANTO: ValueError Expecting value: line 1 column 1 (char 0)
  pero ya habia POSTeado: ['/api/element_register/actuaciones',
                           '/api/relation_element/extrajudiciales/464']
```
Misma raíz en `aprender_id_predefinido` (`:163`, levanta en vez de devolver `sin_comprobar`, y se llama **fuera** del `try` de `alta_actuacion` en `:478`) y en `resolver_destino` (`:250`, levanta `ValueError` en vez de `DestinoNoAcreditado`, así que un llamador que capture el error propio del módulo no lo captura). Las tres verificadas en la misma corrida.

---

### H-02 — Importante — «todas descartadas» se concluye sobre un conjunto que no es todas
`core/sudespacho_relations.py:1258` (la puerta) y `:1296-1310` (el bucle), con `limite: int = 5` en `:1090`.

`_resolver_por_buzon_compartido` es el único camino a `ResolucionParte()` vacía por esta rama, y el diseño §2.2 exige que **todas** las fichas del buzón queden descartadas. El código decide sobre `c_mail.registros`, que no son todas por dos motivos independientes:

1. **La consulta viene paginada a 5** (`itemsPerPage=5`, el defecto de `_buscar_registros`). Con seis fichas en el buzón doméstico, la sexta es invisible. Antes del diff esto era inocuo (`len(ids_mail) &gt; 1` → `ambiguo`, se paraba igual); ahora **autoriza una creación**.
2. **La puerta de `:1258` usa `ids_mail`, y `Consulta.ids` (`:1052`) filtra las filas sin `id`.** Una fila que casó el email pero llega sin `id` deja `ids_mail` vacío → no se entra en la tabla → `:1265`/`:1266` devuelve vacía → se crea.

Entrada concreta (HTTP simulado que trunca a `itemsPerPage`, como cualquier API, y busca por valor literal, como el tenant según el docstring de `_canonizar_documento`): buzón con 5 fichas de NIF propio + una sexta con el documento escrito `2.222.222-j`; se resuelve `nif="2222222J"`.
```
fichas en el buzon: 6 | itemsPerPage que manda el core: 5
resultado: ResolucionParte(id=None, ...)   resuelta (=&gt; se CREA): True
contraste con la MISMA entrada sin truncar:
  PARA -&gt; "la ficha 99 comparte el email y tiene el MISMO documento, pero la
           consulta por NIF no la encontro: revisa como esta escrito en el CRM"
```
La decisión se invierte con el tamaño de página. Segundo caso (fila sin `id`): `motivo=''`, `resuelta=True` → crea sin haber contrastado nada.

---

### H-03 — Importante — la ficha escribe N contrarios y el validador sigue anclando 1
`core/crm_ficha_validacion.py:235` (`c = ficha.contrario`) frente a `scripts/crm_ficha.py:157` (`for contrario in ficha.contrarios`).

`contrario` pasó a ser una propiedad derivada que devuelve **el primero**, así que `datos_de_ficha` compila técnicamente y su significado cambió sin que nadie lo tocara: de «el único» a «el primero de N». El resultado es que los datos de la segunda parte —NIF, email, dirección, población, CP— se escriben en el CRM **sin entrar nunca en el denominador** del anclaje a documental, y el informe de `scripts/crm_ficha_validar.py` sale limpio sobre la mitad del contenido.

Entrada concreta (sonda, ficha con dos contrarios completos):
```
contrarios leidos y que el CLI ESCRIBE: ['PRIMERA', 'SEGUNDA']
datos que el VALIDADOR ancla a la documental: 7   (todos contrario.* de PRIMERA)
claves con 'SEGUNDA'/'DOS'/'7654321M'/'MADRID': []
```
El comentario de `:236-241` presume seguir cubriendo «TODOS los campos del contrario» y ya no cubre todas las partes. Es la frontera de «antes de cambiar un campo, enumera quién lo LEE»: el diff enumeró `scripts/crm_ficha.py` y no `crm_ficha_validacion.py`.

---

### H-04 — Importante — reanudar con un recibo `incierta` crea la segunda actuación
`core/sudespacho_actuaciones.py:476`.

`act_id = desde.act_id if (desde and desde.act_id) else None`. Un `Recibo("incierta")` tiene `act_id=None` por definición —es el estado que significa «el POST pudo haber creado algo y no sé el id»—, así que pasarlo por `desde=` **cae al camino de creación completa sin decir nada**. El docstring prohíbe el reintento ciego en `incompleta`, pero el único estado en el que la API no puede protegerse es justo el otro.

Entrada concreta:
```
r0 = act.Recibo("incierta", act_id=None, paso=4, motivo="timeout")
alta_actuacion(..., desde=r0, client=c)
→ Recibo(estado='verificada', act_id='M', paso=6)
  POSTs de creacion: 1  ['/api/element_register/actuaciones']
```
Ningún test cubre `desde=` con un recibo sin id; el mutante M19 sí prueba el caso simétrico (`act_id = None` forzado) pero no éste.

De la misma raíz, menor: `desde.paso` no se lee nunca, así que un recibo de `paso=5` re-POSTea el vínculo (idempotente, tolerable) y un recibo de **otro** expediente se reutiliza sin comprobación alguna.

---

### H-05 — Importante — el paso 1 aprende el `id_predefinido` de la otra tarifa
`core/sudespacho_actuaciones.py:478` frente a `:481`.

`aprender_id_predefinido` documenta en `:142-144` que filtra por el asunto **literal** del catálogo porque «una aproximación devolvería el de otra plantilla». `alta_actuacion` le pasa el `asunto` **crudo**, sin prefijo, mientras `crear_actuacion` escribe `asunto_canonico(asunto, firmante=…)` **con** prefijo. Y el operador es `like`. El helper viola el contrato de la función que él mismo llama.

Entrada concreta:
```
alta_actuacion(..., asunto="EXTRAJUDICIAL - REVISION VIABILIDAD",
               firmante="ana.velastegui")
paso 1 consulta: 'EXTRAJUDICIAL - REVISION VIABILIDAD' con operador 'like'
paso 4 escribe Subject: 'ABOGADO - EXTRAJUDICIAL - REVISION VIABILIDAD'
id_predefinido escrito: 84   (aprendido de una fila SENIOR)
recibo: verificada
```
Ningún test lo caza porque `_gets_destino_ok` devuelve siempre `{"items": []}` en el paso 1: no hay un solo test que mire **qué cadena** se consulta.

---

### H-06 — Importante — un error de validación se devuelve como «puede haberse creado una actuación»
`core/sudespacho_actuaciones.py:479-493`.

`asunto_canonico(...)` y `resolver_profesional(...)` se evalúan **dentro** del `try` que existe para clasificar los fallos del POST. Sus `ValueError` —firmante vacío, firmante fuera de tabla, profesional numérico— caen en el `except Exception` genérico y salen como el estado más alarmante del recibo.

Entrada concreta:
```
alta_actuacion(..., firmante="")
→ Recibo(estado='incierta', paso=4,
         motivo='el POST no dio recibo (ValueError(...)): puede haberse creado
                 una actuación. NO se reintenta a ciegas; concilia a mano.')
  POSTs realmente hechos: []
```
El diseño §4.3 dice que sin el campo el helper «para y lo dice». Aquí para y dice otra cosa: manda a conciliar a mano un CRM que no se tocó. Lo mismo con `firmante="pepe.desconocido"`.

---

### H-07 — Importante — `resolver_destino` acredita con la fila 0 y no comprueba su id
`core/sudespacho_actuaciones.py:250-262`.

La función filtra por `property: id` y luego lee `filas[0]` **sin comprobar que `filas[0]["id"] == exp_id`**. Si el filtro por `id` no muerde (o el CRM devuelve más de una fila), acredita el destino con la referencia de otro expediente. Es una comprobación de una línea sobre un dato que ya tiene delante, en la función cuyo cometido entero es «verificar por resultado, nunca por status».

Entrada concreta:
```
items = [ {id: "999", Referencia_Cliente: "BaRS10 (W-02VEKE)"},
          {id: "464", Referencia_Cliente: "OTRO CASO (W-0AAAAA)"} ]
resolver_destino("extrajudiciales", "464", "BaRS10 (W-02VEKE)")
→ ACREDITADO: Destino(elemento='extrajudiciales', exp_id='464',
                      evidencia='BaRS10 (W-02VEKE)')
→ escribira sobre el expediente 464, cuya referencia real es OTRO CASO (W-0AAAAA)
```
El mutante M16 solo ataca el `if` de la intersección de W-codes; esta puerta no la cubre nadie.

---

### H-08 — Importante — las cuatro salidas del paso 1 no las consume nadie
`core/sudespacho_actuaciones.py:478-484`.

`IdPredefinido` se construye con cuatro estados y su docstring (`:130-131`) dice que colapsarlos «lleva a inventar un entero». `alta_actuacion` lee **solo `pre.valor`** y nunca `pre.estado`, así que `no_aplica`, `sin_filas` y `sin_comprobar` son indistinguibles para el único llamador: los tres omiten el campo y siguen. En particular, «no pude mirar el catálogo» no detiene ni degrada nada, en un módulo cuya política declarada es fallar cerrado ante lo no comprobado.

Verificación:
```
'pre.estado' en alta_actuacion: False   'pre.valor' en alta_actuacion: True
con el paso 1 en 'sin_comprobar' el alta sigue y declara: verificada
```
Las cuatro salidas están probadas *sobre la función*, ninguna *sobre la decisión*. Es la pieza construida que nadie encadena.

---

### H-09 — Importante — «quien opera no es quien firma» no existe en el código, y su test no puede fallar
`core/sudespacho_actuaciones.py:270` (firma de `asunto_canonico`) y `:482` (`profesional=firmante`).

El diseño §4.3 promete que «`asunto_canonico` valida su coherencia con `profesional_asignado`». `asunto_canonico` no recibe `profesional_asignado`: valida la coherencia entre el prefijo que ya trae `base` y el firmante, que es otra cosa. Y `alta_actuacion` pasa `profesional=firmante`, de modo que el par operador/firmante **no se puede expresar** — la coherencia es trivial por construcción y el escenario de R1/H-05 (Ana tramita, Nikolai firma) no tiene representación.

Consecuencia sobre los tests: `test_el_firmante_decide_el_prefijo_y_no_quien_opera` (`tests/test_sudespacho_actuaciones.py:262-267`) solo llama a `asunto_canonico(base, firmante="Nikolai_Tyukhay")` y comprueba el prefijo. No hay operador en ninguna parte, así que el test **pasa por la razón equivocada**: no puede distinguir «el operador no cambia el prefijo» de «no existe el concepto de operador». Por lectura; el propio §5 del diseño lo pedía como prueba explícita.

`FichaCRMInput.firmante` (`core/crm_ficha.py:31`) tampoco tiene consumidor: `grep` sobre todo el árbol devuelve solo su definición y su lectura del YAML. El proveedor existe; el cable, no.

---

### H-10 — Menor — la verificación del paso 6 no fija página
`core/sudespacho_actuaciones.py:443-450`: la consulta de `verificar_actuacion_vinculada` no manda `itemsPerPage` (las hermanas sí: `:148` manda 10, `_buscar_registros` manda `limite`). Sobre un expediente con más actuaciones que la página por defecto, la recién creada puede no venir, el recibo sale `incompleta` para siempre y reanudar no converge: el vínculo se repite (idempotente) y la verificación vuelve a fallar. Por lectura; no tengo la página por defecto del tenant medida.

### H-11 — Menor — los docstrings de `resolver_parte` describen el procedimiento anterior
`core/sudespacho_relations.py:1186-1207` y `:1151-1158`. Enumeran **tres** estados de parada (`conflicto`/`ambiguo`/`sin_comprobar`) cuando ahora hay cuatro —`motivo` no aparece—, y cierran con «si la interseccion tiene mas de una ficha, sigue siendo ambiguo», que tras el reordenamiento es inalcanzable (`ids_nif` tiene exactamente 1 al llegar ahí). Es el docstring de la función cuyo orden **es** el titular del diff.

### H-12 — Menor — el runbook se desmiente a sí mismo y el backlog no se cerró
- `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:1093` conserva «**Y recuerda `[APER-63]`:** `crm_ficha` lee **un** contrario del YAML… el segundo es siempre trabajo a mano», 35 líneas después del bloque «RESUELTO el 2026-09-14» que lo contradice.
- `docs/MEJORAS_FUTURAS.md` **no se toca en el diff**: `## 209.` (`:9490`) y `## 239.` (`:11346`) siguen abiertas. El plan, Tarea 10 Paso 2, decía «`MEJORAS #209` cerrada con su PR».
- `docs/ARQUITECTURA.md` no registra `core/sudespacho_actuaciones.py`, aunque sí lista a sus hermanos (`:73-74`).

### H-13 — Menor — dos cabos sueltos de contrato
- `asunto_canonico` (`:299-305`) conserva la caja del prefijo preexistente: `asunto_canonico("senior - extrajudicial - x", firmante="Nikolai_Tyukhay")` → `'senior - extrajudicial - x'`. Verificado. El catálogo es mayúsculas y el prefijo es la tarifa.
- `FichaCRMInput(contrario=…)` ya no construye (`TypeError: got an unexpected keyword argument 'contrario'`). Sin llamadores en producción (`grep` sobre todo el árbol: solo `crm_ficha.py` construye), así que no rompe nada hoy; queda dicho porque el diff lo presenta como compatibilidad y solo lo es en lectura.
- Falta el test que el diseño §2.3 y §5 nombran literalmente: «el **corte a mitad** (B creado, vínculo fallido)». `test_la_segunda_corrida_sobre_el_mismo_yaml_converge` cubre dos corridas de `resolver_parte`, no el estado intermedio a través de `ensure_contrario_vinculado`.

---

## Lo que revisé y NO encontré defectuoso

- **El orden del §2.1 contra el código, paso por paso** (`:1232-1266`). Los seis pasos están y en su sitio; `sin_comprobar` conserva la precedencia (paso 1, `:1233`); el `conflicto` del viejo camino de intersección se conserva exactamente donde importaba (`ids_nif` único fuera de `ids_mail`). Corridos `test_h03_*`, `test_el_nif_unico_fuera_del_conjunto_del_email_sigue_siendo_conflicto`, `test_una_consulta_fallida_manda_sobre_todo_lo_demas`.
- **Los tres estados de `_estado_documento`** (`:1067-1080`) y la simetría canónica de la comparación (`:1301`). El doble de `test_h02_…` simula la búsqueda **literal** del tenant, no una canonizada, así que el test sí puede fallar.
- **La convergencia de la reejecución (§2.3)** y el tercer firmante: reproducidas; con el orden nuevo el buzón con dos fichas ya no bloquea.
- **La política de fallar cerrado en `_exigir_identidad_cierta`** (`:1336-1344`): el mensaje nuevo no habla de «VARIAS fichas», y `resuelta` cuenta `motivo` — sin eso, `ResolucionParte(motivo=…)` habría pasado como «no existe, créala», que era el agujero obvio. Está cerrado.
- **`_contrarios_de`**: probé `null`, `[]`, clave ausente, mapping, lista, `[dict, str]`, `[dict, dict-sin-nombre]` y cadena suelta. La validación es previa y completa; el mensaje lleva el índice.
- **`_auditar` del CLI** (`scripts/crm_ficha.py:123-142`): compara por cardinalidad, así que dos contrarios del YAML que deduplicasen al mismo id del CRM salen `[FALTA]` en vez de darse los dos por buenos.
- **Aislamiento de los tests**: cero `httpx`, cero `SUDESPACHO_API_KEY`, cero rutas de producción en los tres ficheros nuevos; las dos escrituras cuelgan de `tmp_path`.
- **`resolver_destino` antes de cualquier escritura**: es la primera sentencia de `alta_actuacion`; `test_un_destino_no_acreditado_no_llega_a_crear_nada` y mi propia sonda confirman cero POST. (Nota de contorno, no hallazgo: `crear_actuacion` y `vincular_actuacion` son públicas y un llamador puede saltarse el paso 3 — eso es composición deliberada, no un fallo.)
- **`duracion_desde_ronda`**: fichero correcto (`_apertura_v1.json`, con el `assert est.leer(...) is not None` del fixture cerrando que es el que lee el core), `None` declarado, extremos invertidos y fecha ilegible rechazados.
- **El arnés como instrumento**: `_escribir` con reintentos, restauración en `finally` armada antes de mutar, `rc=4` distinguido del rojo, verde previo exigido por mutante, y comprobación de que la mutación no rompe la colección.

**Declarado sin verificar** (no refutado): **no pude correr `tests/_mutantes_p6.py`**. Muta el árbol, la revisión es de solo lectura, e intenté materializar una copia aislada con `git archive` a un directorio temporal y el permiso fue denegado. La cifra «26 mutantes, 26 muertos» de `PLAN.md` fila #33 queda por tanto **sin comprobar por mí**. Lo que sí digo por lectura: los 26 mutantes existen, apuntan a tests que existen, y **ninguno ataca las puertas de H-02, H-04, H-05, H-07 ni H-08** — porque esas puertas no están escritas.

---

## Valoración final

**NO-SHIP.** El diff hace bien lo que se propuso —el NIF único deja de quedar tapado por la multiplicidad del email, la tabla del buzón está bien razonada, la ficha admite N contrarios con validación previa— pero tres cosas lo dejan por debajo de su propio contrato:

1. **H-01 derrota el `Recibo`**, que es la razón de ser de la pieza 1: hay un camino con efecto real en el CRM que devuelve una excepción en vez de un recibo con el id. Y es el defecto que el módulo hermano ya documenta como pagado en una ronda anterior.
2. **H-02 abre un camino nuevo a `ResolucionParte()` vacía** que depende del tamaño de página. La misma entrada crea o para según cuántas filas devuelva el servidor: es exactamente la clase de decisión que el §2.2 existe para eliminar.
3. **H-03 desacopla la escritura del anclaje**: se escriben N partes y se valida 1. Ese es el control que impide que un dato no acreditado llegue a la ficha de un cliente.

H-05, H-06, H-07 y H-09 son de la misma familia: el orquestador `alta_actuacion` es donde se pierden las distinciones que los helpers construyeron con cuidado (el estado del paso 1, el asunto literal, el firmante frente al operador, la validación frente al fallo de red). La pregunta que ahorra la siguiente ronda es la de la casa: **¿de qué frontera es esto un ejemplo?** — y aquí la frontera se ve de un vistazo: *cada helper distingue estados que su único llamador colapsa*. Remediar los seis casos uno a uno dejará el séptimo.

Riesgo de daño: H-03 y H-02 tocan datos de cliente en el CRM; H-01, H-04 y H-05 tocan el registro facturable. Ninguno es un fallo de diseño —el diseño rev. 2 es correcto donde lo describe—; son huecos entre lo diseñado y lo cableado.
<!-- informe-literal:fin:k4qz -->

## 2. Evidencia verificada por mí al adjudicar

La adjudicación conjunta de los dos informes de la R2 está en el **§7** del spec, agrupada por
categorías porque el remedio fue por frontera y no caso a caso. Lo que este revisor aportó y el
otro no, ya recogido allí, es sobre todo la **paginación**: «todas descartadas» se concluía sobre
`itemsPerPage=5`, de modo que con seis fichas en un buzón la decisión de **crear** dependía del
tamaño de página.

**Una precisión sobre su recuento de la suite:** declaró 82 + 263 tests verdes sin regresiones.
Eso es cierto para el estado del diff que leyó (`8aed442`) y **no acredita** el estado posterior:
la R3 midió sobre `53cc575` que varias de esas piezas seguían con la frontera abierta. Un verde
acredita que los tests que hay pasan, nunca que los que faltan pasarían.
