---
tipo: revision-adversarial
objeto: docs/INTEGRACION_SUDESPACHO.md §16 (+ DEAD_ENDS, MEJORAS #176, PLAN fila 24, INDICE)
objeto_rev: "1"
commit: 0ce01a8
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: qvzp
sha256_informe: 9429775e07dfbfecc47ee74199d4335a1171265449a2b698be0a4b7de2ba4364
adjudicado_en: docs/superpowers/specs/2026-09-08-poderes-crm-contrato-r1-adversarial-review.md §3
---

# Acta de la R1 — el contrato del elemento `poderes` del CRM

**Por qué la adjudicación vive en esta acta y no en un spec.** El contrato de gobernanza manda que la
adjudicación vaya *embebida en el documento revisado* y que el acta sea solo el archivo de la voz del
revisor. Aquí el objeto revisado **no es un spec ni un plan**: son cinco ficheros de documentación de
referencia, y meter una adjudicación de revisión dentro de `INTEGRACION_SUDESPACHO.md` sería ruido
para quien lo abre a buscar cómo escribir en el CRM. Así que la adjudicación va en el §3 de aquí, y
lo que de verdad exige el contrato —que **el remedio** viva en el documento que la decisión
modificó— se cumple: los siete remedios están en los cinco ficheros, y el §3 dice cuál en cuál.

---

## 0. Mandato entregado al revisor (literal)

<!-- mandato-literal:inicio:qvzp -->
# MANDATO — revisión adversarial R1 del diff de documentación del elemento `poderes`

Eres el revisor. Tu trabajo es **atacar** este diff, no aprobarlo. El autor (Claude) adjudicará
después cada hallazgo contra la fuente; tú no tienes la última palabra, pero tampoco tienes que
suavizar nada.

## Higiene

Tu directorio de trabajo debe contener **solo este `MANDATO.md`**. Si hay otro fichero, **no lo
leas** y decláralo en la primera línea de tu informe. Mira las marcas de tiempo antes de tomar
cualquier fichero por tuyo: uno más antiguo que este mandato no puede ser respuesta a este mandato.

## Objeto

Dos copias del repositorio, hermanas de tu workdir:

- `../base/` — el árbol **antes** del cambio.
- `../head/` — el árbol **después**.

El diff son cuatro ficheros de documentación, ninguna línea de código:

- `docs/INTEGRACION_SUDESPACHO.md` — sección **§16** nueva (191 líneas)
- `docs/DEAD_ENDS.md` — una entrada nueva
- `docs/MEJORAS_FUTURAS.md` — entrada **#176** nueva
- `PLAN.md` — fila 24 de la cola + bloque `[SIGUIENTE-ALTA-PODER]`

Sácalo con `diff -ru ../base ../head` o comparando fichero a fichero. No hay `.git`.

## Prohibiciones duras

1. **NO escribas nada en ninguna de las dos copias.** Tu informe va a tu propio workdir.
2. **NO toques el CRM** (`api-crm-commons-pro.sudespacho.biz`, `tnm.sudespacho.net`). No hay
   credenciales a mano y una escritura ahí es sobre datos reales de clientes. Si crees que un
   hallazgo solo se decide llamando a la API, **dilo como «sin verificar»** — eso es una respuesta
   válida y útil, no un fracaso.
3. **No pidas permisos ni esperes interacción.** Si algo no se puede comprobar, se declara.

## Qué te pido que ataques, en orden de importancia

### 1. Afirmaciones sobre el repositorio — esto SÍ lo puedes verificar y es lo que más vale

El §16.1 y la mejora #176 hacen afirmaciones comprobables **sin salir de la copia**:

- que `core/crm_atlas.py` construye la lista de elementos de la Fase B llamando a `/api/elements`
  (busca `fetch_elements` y el sitio de la llamada);
- que `docs/CRM_SUDESPACHO_ATLAS.md` **no tiene ficha de `poderes`** en su sección «Esquema por
  elemento», y que su cabecera dice «87/89»;
- que el atlas **cita `poderes`** en las líneas `Relaciones · parent: … · children: …` de otros
  elementos;
- que **28 elementos** aparecen citados en esas líneas y no tienen ficha propia. **Recalcula ese
  número por tu cuenta** y dime si te sale 28. Si te sale otro, quiero tu método y tu cifra.
- que la lista literal de los 28 que da la #176 coincide con lo que salga de tu cálculo.

Corre esto de verdad, no lo leas. Tienes Python en
`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, con `pytest`,
`pytest-randomly`, `pytest-xdist`, `pyyaml` y `httpx`.

### 2. Los guards de gobernanza documental

`../head/tests/test_docs_gobernanza.py` existe y vigila la coherencia de `docs/`. **Córrelo sobre
`../head`** y dime si pasa. Si falla, es un hallazgo. Ejecuta también lo que consideres del resto de
la suite que pueda tocar documentación (guards de PII, de índices, de anclas). Interesa
especialmente:

- si el ancla del enlace de la fila 24 de `PLAN.md` resuelve al encabezado
  `## [SIGUIENTE-ALTA-PODER] …` (regla de GitHub: minúsculas, se eliminan `[`, `]` y `,`, los
  espacios pasan a guiones);
- si `docs/INDICE.md` u otro índice debía actualizarse al añadir una sección y no se hizo. Hay un
  aprendizaje documentado del proyecto sobre corregir un documento y dejar su índice con la versión
  vieja: comprueba si aquí se ha repetido.

### 3. Contradicciones internas y con el resto del documento

`INTEGRACION_SUDESPACHO.md` tiene ya 15 secciones. La §16 nueva puede **contradecir** o **duplicar**
lo que dicen §3.1, §8, §10.6, §10.7, §14.2, §14.6, §15.1, §15.3 y §15.5. Busca:

- afirmaciones incompatibles (p. ej. sobre el verbo, la forma del body, la codificación del valor de
  un filtro, o si el PUT es parcial);
- un hecho que ahora tenga **dos hogares** con redacciones distintas — el proyecto tiene una regla
  de «un hecho, un hogar»;
- referencias cruzadas a secciones que **no dicen lo que la §16 dice que dicen**. Compruébalas una
  por una: `§0.3`, `§5.1`, `§10.7`, `§14.6`, `§15.1`, `§15.5`, `§16.3`, `§16.6`, `§16.7`.

### 4. Instrucciones que, seguidas literalmente, harían daño

Es documentación operativa: alguien la va a seguir para **escribir en el CRM de un cliente**.
Ataca eso:

- ¿hay algún paso cuya ejecución literal pueda **corromper o perder** un dato?
- ¿la §16.3 basta para no crear un vínculo mal, sabiendo que **no hay endpoint para borrarlo**?
- ¿la §16.5 (cp1252) es una regla aplicable o queda como anécdota? ¿Cubre el caso de un valor que
  viene de un PDF y no de una constante?
- ¿el §16.8 (convención de la casa) se puede seguir sin ambigüedad, o hay decisiones que el texto da
  por resueltas y no lo están?
- el bloque `[SIGUIENTE-ALTA-PODER]` de `PLAN.md` describe algo por construir: ¿hay en él un paso
  **inconstruible** con el contrato que la §16 declara, o una dependencia que no se nombra?

### 5. Datos personales

El proyecto prohíbe nombres, correos, direcciones y NIF/CIF de terceros en `docs/`, bitácora y
commits; se referencia por `W-XXXXX`. Barre el diff entero buscando cualquier resto: nombres de
personas físicas, razones sociales, NIF/CIF/NIE, direcciones, teléfonos, N.I.G. Da los que
encuentres con fichero y línea. Ojo: el diff menciona a propósito `EV MMC` y `EV SPAIN` (el cliente
del despacho, que sí está nombrado en la documentación del proyecto) y `eplanv2_TNM` (nombre de una
base de datos que ya estaba en el documento). Dime si consideras que alguno de esos dos tampoco
debería estar.

## Lo que NO es un hallazgo

- Estilo, tono, longitud, orden de las secciones, o que el documento sea denso.
- Que la §16 no numere sus subsecciones como te gustaría.
- Que el autor no haya construido todavía lo que el `PLAN.md` describe: eso es precisamente lo que
  el bloque dice que está pendiente.
- Que una afirmación medida contra el CRM no se pueda re-verificar sin credenciales. Eso se declara
  «sin verificar», no se convierte en crítica.

## Formato del informe

Escribe `INFORME.md` en tu workdir, en castellano, con:

1. **Primera línea:** si tu workdir tenía algún fichero además de este mandato.
2. **`sha256` de las dos copias al abrir y al cerrar** (`../base` y `../head`), como prueba de que no
   has mutado el objeto. Usa el hash de un recorrido ordenado de los ficheros.
3. **Un bloque por hallazgo**, con: `ID` (`H1`, `H2`…), **severidad** (`CRÍTICO` / `ALTO` / `MEDIO` /
   `BAJO`), **fichero y línea**, **qué afirma el diff**, **por qué es falso o peligroso**, **cómo lo
   has comprobado** (comando y salida, si lo has ejecutado) y **qué remedio propones**.
4. **Los comandos que has ejecutado, con su salida**, para lo del punto 1 y 2 de arriba.
5. **Lo que no has podido verificar**, explícitamente. Un hueco declarado vale más que una
   conjetura presentada como hallazgo.
6. **Última línea, exactamente uno de estos dos veredictos y nada más:**
   `VEREDICTO: SHIP` o `VEREDICTO: NO-SHIP`.

Si no encuentras nada que merezca `MEDIO` o más, dilo y pon `SHIP`. Un informe honesto con cero
hallazgos altos es un resultado válido; inflar la severidad para justificar la ronda, no.
<!-- mandato-literal:fin:qvzp -->

---

## 1. Informe recibido de Codex, sin modificar

`sha256` del texto canonicalizado (UTF-8, LF, un solo salto final): `9429775e07dfbfecc47ee74199d4335a1171265449a2b698be0a4b7de2ba4364`

Calculado al recibirlo, antes de leerlo. El revisor **no declaró** un digest propio en su informe,
así que esta cadena se verifica contra sí misma y contra el fichero original conservado fuera del
repo; **no hay prueba independiente de origen** más allá de eso, y conviene decirlo en vez de
insinuar una garantía que no existe.

Lo que sí se comprobó, y es más que una autoverificación: **el digest que recomputa G8 del bloque
literal de aquí coincide con el que se calculó del `INFORME.md` original** — o sea que la
canonicalización del guard y la mía son la misma, y el bloque embebido no perdió ni ganó nada al
copiarse. Verificado además por control positivo: sabotear un dígito del `sha256_informe` pone
`test_actas_cadena_de_custodia` **en rojo** nombrando esta acta, así que el verde de G8 no es un
verde por no mirar.

<!-- informe-literal:inicio:qvzp -->
Higiene inicial: el workdir contenía únicamente MANDATO.md; no había ningún otro fichero ni directorio.

# Revisión adversarial R1 — documentación del elemento `poderes`

Revisor: Codex. Fecha de ejecución comprobada en el sistema: 2026-09-08. Objeto: las copias `../base` y `../head`, sin `.git`. Las líneas citadas corresponden a `head`, salvo indicación expresa. La adjudicación corresponde a Claude contra las fuentes.

El resultado es **NO-SHIP**: un hallazgo ALTO, cinco MEDIOS y uno BAJO. Los problemas son documentales y de contrato operativo; **no ha fallado el guard de gobernanza documental**. El recuento de los 28 elementos y la lista literal de #176 son correctos.

## 1. Custodia del objeto

La primera operación enumeró el directorio, sin leer ficheros ajenos. Su salida fue:

```text
Name       Length CreationTimeUtc     LastWriteTimeUtc
MANDATO.md   7446 08/09/2026 14:50:34 08/09/2026 14:50:34
```

Los directorios hermanos tenían marcas anteriores: `base`, 14:48:21 UTC; `head`, 14:48:28 UTC. También existía un `../MANDATO.md` anterior, a las 14:47:28 UTC: no lo leí ni lo tomé por respuesta de esta ronda. Todos los scripts, logs, la copia de ejecución y este informe nacieron después de la comprobación inicial. Las instrucciones globales y skills se leyeron fuera del workdir.

**Método de huella reproducible:** recorrer todos los ficheros, incluidos los ocultos; ordenar por ruta relativa POSIX, con orden lexicográfico de Python; para cada fichero concatenar `ruta_relativa + NUL + sha256(bytes).hexdigest() + LF`; calcular SHA-256 del manifiesto concatenado codificado en UTF-8. No se excluye ningún fichero. Las marcas de tiempo no entran en la huella: se verifican nombres y contenido.

| Árbol | Ficheros al abrir / cerrar | SHA-256 al abrir | SHA-256 al cerrar |
|---|---:|---|---|
| `../base` | 1244 / 1244 | `6ca254d831bd3b35866bfc3ecdc99e476315766402fcd6e37098eaeadeea4c44` | `6ca254d831bd3b35866bfc3ecdc99e476315766402fcd6e37098eaeadeea4c44` |
| `../head` | 1244 / 1244 | `f60f64b2a56bc1ab6e68f5fe030a6a8cacfc0000ab61d0bce0d67f31e45ac46b` | `f60f64b2a56bc1ab6e68f5fe030a6a8cacfc0000ab61d0bce0d67f31e45ac46b` |

**Ninguno de los dos árboles fue modificado.** El guard solicitado se ejecutó directamente sobre `head`, con bytecode y caché de pytest desactivados y temporales externos. La ampliación se ejecutó sobre `work/test_head`, copia íntegra, con un índice Git local creado exclusivamente allí. No hubo llamadas al CRM, uso de credenciales ni operaciones en sistemas externos.

## 2. Hallazgos

### H1 — ALTO — El plan rebaja las rondas eliminando el criterio de corrupción de datos

**Fichero y línea:** `PLAN.md:3125`–3128. Fuente normativa: `CLAUDE.md:50`–58.

**Qué afirma el diff:** el alta merece «1 ronda sobre el diff» porque «no […] puede destruir datos (solo añadir)».

**Por qué es falso o peligroso:** la regla de la fuente incluye expresamente **«destruir o corromper datos de cliente»**, con dos rondas: diseño y diff. Añadir un vínculo al poderdante equivocado corrompe la información del cliente aunque no borre ninguna fila. El propio bloque reconoce relaciones que considera irreversibles y, en `PLAN.md:3133`, un registro con el cliente equivocado vinculado. Por tanto, no es una posibilidad inventada para endurecer la revisión: el plan enumera ese radio de daño y después lo excluye cambiando el predicado de la regla. También habrá escrituras de título/asunto del documento; «solo añadir» no describe todo el flujo.

**Comprobación:** lectura numerada reproducible con `python source_checks.py`, salida en `source_checks.txt`:

```text
CLAUDE.md:57: | decide **quién puede escribir** sobre qué copia, o puede **destruir o corromper datos de cliente** | **2** — una sobre el diseño (spec/plan) y una sobre el diff |
PLAN.md:3126: borrar** → según la regla de presupuesto de rondas, esto es **1 ronda sobre el diff**; el diseño no
PLAN.md:3127: decide quién escribe sobre qué copia ni puede destruir datos (solo añadir), así que no entra en la
```

**Remedio:** aplicar dos rondas a la futura pieza de alta, diseño y diff, citando la regla sin recortarla. No estoy pidiendo una ronda adicional sobre este mismo diff de documentación ni una tercera ronda sobre la pieza.

### H2 — MEDIO — «No hay endpoint documentado para borrar» contradice dos fuentes locales

**Fichero y línea:** `docs/INTEGRACION_SUDESPACHO.md:1977`; repetido en `docs/DEAD_ENDS.md:30` y, sin el calificativo «documentado», en `PLAN.md:3099` y 3125–3126.

**Qué afirma el diff:** no existe endpoint documentado para borrar un vínculo; en el plan se convierte en que los vínculos no se pueden borrar.

**Por qué es falso o peligroso:** `INTEGRACION_SUDESPACHO.md:1794`, precisamente §15.5 al que se remite al lector, enumera `DELETE /api/relation_element/{element}/{id}` como borrado de vínculo. El atlas lo declara también en `docs/CRM_SUDESPACHO_ATLAS.md:1060`, con enlace a la documentación del proveedor. Esto refuta **la ausencia documental**, no demuestra que el endpoint funcione con la clave o el tenant actuales. La operación de recuperación queda con dos contratos incompatibles y el plan convierte falta de validación en inexistencia.

**Comprobación:** `python source_checks.py`:

```text
docs/INTEGRACION_SUDESPACHO.md:1794: | Crear / actualizar / borrar vínculo | `/api/relation_element/{element}/{id}` | `POST` · `PUT` · `DELETE` — **`GET` → 405** |
docs/CRM_SUDESPACHO_ATLAS.md:1060: | `DELETE` | `/api/relation_element/{element}/{id}` | Delete an relations element. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-relation-element-relations-elements-collection/) |
```

No se abrió ese enlace ni se ejecutó DELETE o ninguna otra petición.

**Remedio:** distinguir «endpoint declarado» de «borrado no validado/no disponible con nuestros permisos» y mantener **prohibida la confianza en un rollback no verificado**. Reconciliar §15.5, §16.3, DEAD_ENDS y PLAN. Si hay una medición posterior que refuta la ruta declarada, citarla; esta revisión no la tiene.

### H3 — MEDIO — El esquema no determina un lado único: el propio ejemplo pertenece a ambos lados

**Fichero y línea:** `docs/INTEGRACION_SUDESPACHO.md:1981`–1983; `docs/DEAD_ENDS.md:26`–29. Contraejemplo en `INTEGRACION_SUDESPACHO.md:1937` y `DEAD_ENDS.md:20`–22.

**Qué afirma el diff:** antes de escribir en un elemento nuevo basta leer `view/config/{element}/relations` y derivar `parent → left`, `children → right`.

**Por qué es falso o peligroso:** el JSON aportado incluye **`clientes_propios` en `parent` y en `children`**. Aplicar la regla permite tanto `left.clientes_propios` como `right.clientes_propios`; el segundo es justamente el intento sin efecto que abre el dead end. No se puede deducir de esa pertenencia cuál expresa el papel de poderdante. Para `poderes`, la tabla empírica sí desambigua y sirve; es la supuesta generalización automática a nuevos elementos la que no se sostiene. La verificación posterior detecta un vínculo ausente, pero no previene crear uno con el papel equivocado cuando ambos lados admitan escrituras.

**Comprobación:** `python verify_repo.py` devuelve:

```text
RELACIONES_AMBIGUAS=['clientes_propios']
```

El conjunto se calcula con los dos arrays literales del contrato. `python source_checks.py` conserva el JSON y la tabla que fija por evidencia `left.clientes_propios` y `right.procuradores_propios`.

**Remedio:** conservar la tabla medida de `poderes`; acotar la derivación automática a candidatos que aparezcan en un solo lado. Si aparecen en ambos, exigir resolver el papel y el contrato antes del POST —mediante evidencia previa o captura pertinente—, sin probar variantes sobre fichas reales para decidirlo. La comparación por lectura debe comprobar elemento e identidad esperados, no solo status o número de bloques.

### H4 — MEDIO — La descarga tiene dos hogares incompatibles y el enlace nuevo lleva al obsoleto

**Fichero y línea:** `docs/INTEGRACION_SUDESPACHO.md:2043`–2044, referencia nueva a §5.1. Fuente contradictoria: §5.1, líneas 440–450; tabla §3.1, líneas 191 y 194.

**Qué afirma el diff:** descargar mediante `GET /api/documents/{id}/downloadUri` y `presignedDownloadUrl`, remitiendo a §5.1; las otras dos rutas presigned siguen rotas.

**Por qué es falso o peligroso:** §5.1 **no documenta ese flujo**: manda llamar a `/api/files/presigned_download_url/{doc_id}`, una de las rutas que la nueva línea declara rota. Además, dice que el reemplazo en `core/sync_sudespacho.py` está pendiente, mientras el código ya usa `ENDPOINTS["document_download_uri"]`. El lector que siga el enlace para completar la operación acaba en la receta que el diff advierte no usar. No atribuyo al diff la aparición histórica de §5.1 obsoleto; sí la nueva remisión a él como respaldo de un contrato distinto.

**Comprobación:** `python source_checks.py`:

```text
docs/INTEGRACION_SUDESPACHO.md:441:     GET /api/files/presigned_download_url/{doc_id}
docs/INTEGRACION_SUDESPACHO.md:450: **Pendiente de implementar en `core/sync_sudespacho.py`** como reemplazo de los métodos legacy.
core/sync_sudespacho.py:153:     "document_download_uri": "/api/documents/{id}/downloadUri",
core/sync_sudespacho.py:782:         path = ENDPOINTS["document_download_uri"].format(id=doc_id)
```

`DEAD_ENDS.md:443`–447 ya distingue las dos rutas fallidas y la implementada.

**Remedio:** actualizar el hogar del flujo (§5.1) y los estados de su tabla de acceso (§3.1), y dejar en §16.7 un enlace al flujo correcto. Mantener el histórico del fallo en DEAD_ENDS. No hace falta otra llamada al CRM para reconciliar lo que el repo ya afirma y ejecuta.

### H5 — MEDIO — El punto ciego queda documentado al final mientras el acceso al atlas sigue prometiendo totalidad

**Fichero y línea:** `docs/INTEGRACION_SUDESPACHO.md:1894`–1908 y `docs/MEJORAS_FUTURAS.md:7872`–7873. Superficies no reconciliadas: `INTEGRACION_SUDESPACHO.md:73`–84 y 177–179; `docs/INDICE.md:46`.

**Qué afirma el diff:** el atlas tiene un punto ciego confirmado, ausencias no equivalen a inexistencia y ese problema queda documentado de momento en §16.1.

**Por qué es peligroso:** antes de que el lector llegue a §16, §0.4 aún dice «ya mapea **toda la superficie**», enumera 89 elementos y lo llama SSOT de «qué existe». §3.1 refuerza «inventario **exhaustivo** […] toda la superficie». Son afirmaciones incompatibles con los 28 nombres sin ficha que esta revisión ha recalculado. El índice mantiene la puerta de entrada al atlas como «SSOT de la superficie del CRM», sin puntero al límite recién descubierto. La nueva advertencia no llega a los lugares donde se ordena consultar primero, precisamente el error operativo que #176 pretende evitar.

**Comprobación:** `python verify_repo.py`: `FICHAS=89`, `SIN_FICHA=28`, `UNION=117`. `python source_checks.py` conserva:

```text
docs/INTEGRACION_SUDESPACHO.md:74: ya mapea toda la superficie del tenant `tnm` de forma generada y re-ejecutable — endpoints
docs/INTEGRACION_SUDESPACHO.md:76: de tipo `Select` (Fase B: 89 elementos). Es el **SSOT de "qué existe"**; a menudo evita el
docs/INTEGRACION_SUDESPACHO.md:178: > hogar legítimamente distinto). El inventario **exhaustivo** de la superficie REST (toda la
```

El aprendizaje pedido existe en `docs/bitacora/2026.md:2078`–2080: se corrigió un enunciado sobre reportlab en un handoff y se dejó la versión falsa en la fila del índice. Aquí se repite la clase de defecto en las afirmaciones de totalidad de las entradas al atlas.

**Remedio:** retirar «toda/exhaustivo/qué existe» sin acotación de §0.4 y §3.1; añadir un puntero breve al límite de cobertura también en la fila del atlas del índice. El diagnóstico completo debe vivir en un único hogar. **Añadir §16 no obliga por sí solo a crear una fila nueva en INDICE**: la fila 45 ya indexa el documento y no promete una lista exhaustiva de secciones. El hallazgo es la promesa desmentida de cobertura, no la ausencia de una fila de §16 ni la falta de implementar #176.

### H6 — MEDIO — El «registro entero sin intervención» necesita una decisión canónica que el contrato no fija

**Fichero y línea:** `PLAN.md:3077`–3081 y 3096; `docs/INTEGRACION_SUDESPACHO.md:2056`–2061. Restricción del esquema: `INTEGRACION_SUDESPACHO.md:1917`.

**Qué afirma el diff:** el extractor rinde el registro entero sin intervención, los tres Selects se rellenan siempre y OBJETO tiene un vocabulario cerrado, incluyendo `Pleitos general + especial`.

**Por qué es incompleto para ejecutarlo literalmente:** el propio dominio descrito admite general **y** especial en un certificado, pero `Tipo` es un único Select con `General` o `Especial`, sin valor combinado. No hay regla de prioridad ni correspondencia `OBJETO → Tipo`. Dos implementadores pueden producir registros distintos a partir del mismo documento cumpliendo todos los valores permitidos. Tampoco se fija qué hacer con un poder solo especial cuyo objeto no pertenezca a las materias de la lista cerrada. Esto no exige debatir el alcance jurídico de las facultades: es un hueco entre las entradas que el texto admite y el mapeo que declara canónico.

**Comprobación:** lectura conjunta, archivada por `python source_checks.py`:

```text
docs/INTEGRACION_SUDESPACHO.md:1917: | `Tipo` | `Select` | `-1`=Ninguno · `General` · `Especial` |
docs/INTEGRACION_SUDESPACHO.md:2056: | `Tipo` · `Formato` · `Apoderado` | siempre rellenos; `Apoderado` casa con la relación (si hay procurador vinculado, `Procurador`) |
docs/INTEGRACION_SUDESPACHO.md:2059: Vocabulario cerrado de OBJETO: `Pleitos general` · `Pleitos general + especial` · `Especial - herencia`
PLAN.md:3080:    el apoderado con **NIF y colegio**, y `VIGENCIA: DESDE … HASTA …`. Rinde el registro entero sin
```

**Remedio:** declarar como dependencia pendiente la decisión de la casa y fijar una tabla de mapeo que cubra el caso combinado y la salida del vocabulario. Ante un caso sin correspondencia, detenerse antes de crear, no inventar una categoría. No se pide construir el extractor en este diff: se pide dejar de presentar como resuelta una decisión necesaria para construirlo.

### H7 — BAJO — El recuento de nombres se transforma en operatividad confirmada y se duplica el hecho

**Fichero y línea:** `docs/INTEGRACION_SUDESPACHO.md:1898`–1904 y `docs/MEJORAS_FUTURAS.md:7870`–7876.

**Qué afirma el diff:** el cruce del atlas da «28 elementos operativos sin ficha»; el rótulo propuesto habla de «≥28 elementos operativos fuera de esa lista».

**Por qué excede lo comprobado:** el cruce demuestra 28 **nombres citados sin ficha**, no que cada endpoint responda para cada nombre. #176 termina reconociendo que falta «medir cuántos de los 28 responden». No refuto ninguna medición del CRM: señalo que la inferencia declarada es más amplia que el cálculo y que el propio texto separa la medición pendiente. Además, la lista completa y su explicación nacen en dos hogares, §16.1 y #176, contra `GOBERNANZA_FUENTES_VERDAD.md:17`. Hoy las listas coinciden; no hay divergencia de miembros que imputar.

**Comprobación:** `python verify_repo.py` cuenta las fichas y las relaciones sin consultar endpoints. `python source_checks.py` conserva tanto «operativos» como la frase final de medición pendiente.

**Remedio:** decir «28 elementos citados sin ficha»; reservar «operativo verificado» para lo medido por elemento. Dejar el detalle y listado en #176 y un aviso con enlace desde §16.1, o decidir el hogar inverso. No se exige sondear los 28 para publicar esta documentación.

## 3. Comprobaciones del repositorio y comandos ejecutados

Todas las órdenes Python usaron el ejecutable indicado en el mandato. En los bloques siguientes, `$py` abrevia únicamente esa ruta:

```powershell
$py = 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
```

Los scripts citados están en este workdir y no modifican las copias revisadas. Se conservan `diff.txt`, `repo_checks.txt`, `offline_checks.txt`, `source_checks.txt`, las huellas JSON y los logs completos de pytest. La búsqueda inicial con `rg` falló porque no está instalado; se sustituyó por recorridos de `pathlib`/expresiones regulares y lecturas numeradas.

### 3.1 Huellas, diff y cálculo independiente

```powershell
& $py audit_hash.py opening
& $py verify_repo.py
& $py -B verify_offline.py
& $py source_checks.py
& $py audit_hash.py closing
```

Las dos ejecuciones de `audit_hash.py` dieron exactamente el mismo JSON:

```json
{
  "base": {
    "files": 1244,
    "sha256": "6ca254d831bd3b35866bfc3ecdc99e476315766402fcd6e37098eaeadeea4c44"
  },
  "head": {
    "files": 1244,
    "sha256": "f60f64b2a56bc1ab6e68f5fe030a6a8cacfc0000ab61d0bce0d67f31e45ac46b"
  }
}
```

El diff se extrajo con `difflib.unified_diff` comparando fichero a fichero `base`/`head` y se guardó en `diff.txt`. Comprobación independiente con `SequenceMatcher(autojunk=False)`:

```text
DIFF docs/DEAD_ENDS.md: +27 -0
DIFF docs/INTEGRACION_SUDESPACHO.md: +191 -0
DIFF docs/MEJORAS_FUTURAS.md: +53 -0
DIFF PLAN.md: +80 -0
```

No hay cambios de código ni otros ficheros modificados.

**Método del recuento:** aislar «Esquema por elemento» hasta el siguiente encabezado de nivel 2; tomar como fichas los encabezados `###` que sean un slug (`[a-z][a-z0-9_]*`), excluyendo «Elementos con descubrimiento degradado»; leer exclusivamente las líneas `- Relaciones · parent: … · children: …`; dividir ambos lados por comas, eliminar vacíos/marcadores y deduplicar. Restar del conjunto citado el conjunto de fichas. Para #176, extraer el bloque literal entre cercas y comparar los conjuntos en ambas direcciones.

```text
FICHAS=89 RELATION_LINES=89 CITADOS=105 INTERSECCION=77 SIN_FICHA=28 UNION=117
SIN_FICHA_ORDENADOS=catalogo_conceptos_provision, conceptos, conceptos_finance, conceptos_recibidas, conceptos_recibidas_gastos, conceptos_recibidas_honorarios, conceptos_varios, cron, cuentascontables_configuracion, gdoculogdescargas, grupos, gruposcontables, lesionados, mail, mandatos, pagos_proveedores, panels, plantillas, poderes, proyectos, remesas, reports, rgpdlopd, signatures_documents, tarifas_conceptos_honorario, templates, tracking, usuarios
LISTA_176=28 SOBRAN=[] FALTAN=[]
FICHA_PODERES=False
```

La resta correcta es `105 − 77 = 28`, no `105 − 89`: hay 12 fichas que no son mencionadas en esas líneas. La unión da `89 + 28 = 117`. **Coinciden tanto el número como la lista literal.**

La cabecera literal está en `CRM_SUDESPACHO_ATLAS.md:20`: `⚠️ 87/89 (2 degradados)`. `poderes` aparece en las relaciones de `clientes_propios` (línea 1964), `gdocu` (2988) y `procuradores_propios` (3427); no tiene ficha propia. Las líneas completas están en `repo_checks.txt`.

**Generación de la Fase B:** el AST local identifica:

```text
AST core/crm_atlas.py:923: client.get("/api/elements")
AST core/crm_atlas.py:931: get_with_retry(client, "/api/elements")
AST scripts/crm_atlas.py:127: fetch_elements(client)
```

La primera es el healthcheck; la segunda está dentro de `fetch_elements`. El llamador usa esos slugs para `todo` y ejecuta `discover_element` sobre ellos (`scripts/crm_atlas.py:135`–147). Además **se ejecutó la función real**, con `httpx.MockTransport` y host ficticio, sin red:

```text
FETCH_ELEMENTS (MockTransport; ninguna red): ['alfa', 'zeta']
REQUESTS=['GET https://offline.invalid/api/elements']
```

También se ejecutó su test existente en `tests/test_crm_atlas.py`. Esto verifica el mecanismo local; no reproduce la respuesta viva de 89 elementos del CRM.

### 3.2 Guards, cobertura efectiva, índices y anclas

**Orden solicitada directamente sobre `../head`:**

```powershell
& $py run_checks.py ../head guards_head tests/test_docs_gobernanza.py
```

El wrapper ejecuta, con cwd en `head`:

```text
python.exe -B -m pytest tests/test_docs_gobernanza.py -p no:cacheprovider --basetemp <work>/tmp_guards_head --tb=short
..............................................                           [100%]
46 passed in 13.90s
EXIT: 0
```

Variables del proceso: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `GIT_CEILING_DIRECTORIES=<review>`. El log íntegro con rutas expandidas está en `guards_head.txt`.

**Límite de ese verde:** las funciones de referencias legacy y citas a specs/plans usan Git sin comprobar su código de retorno. Comprobación ejecutada con `subprocess.run`, cwd en cada copia y techo Git en `review`:

```text
../head: git ls-files *.md -> exit=128, filas=0, stderr='fatal: not a git repository (or any of the parent directories): .git'
test_head: git ls-files *.md -> exit=0, filas=453, stderr=''
COPIA_INDEXADA: originales=1244, tracked=1244, bytes_diferentes=[]
```

Para cubrir esas ramas se creó con `shutil.copytree` una copia íntegra `work/test_head`; **solo allí** se ejecutaron:

```powershell
git -C test_head -c core.autocrlf=false init -q
git -C test_head -c core.autocrlf=false add -f -- .
# El primer add falló: Filename too long. No afectó a base/head.
git -C test_head config core.longpaths true
git -C test_head -c core.autocrlf=false add -f -- .
git -C test_head ls-files -- '*.md' | Measure-Object -Line
```

Salida final: `453` líneas Markdown, índice con los `1244` ficheros. No hubo commits. La comparación de bytes de esos 1244 ficheros contra `head` dio diferencias `[]`; solo se añadió metadata Git en la copia de prueba. El inventario sirve para este corpus entregado, sin pretender reconstruir el historial original ausente.

**Ampliación ejecutada, dos semillas:**

```powershell
& $py run_checks.py test_head guards_indexed tests/test_docs_gobernanza.py tests/test_gobernanza_taxonomia.py tests/test_no_pii_en_tests.py tests/test_precommit_leak_guard.py tests/test_leak_guard_formas.py tests/test_crm_atlas.py -p randomly --randomly-seed=777
& $py run_checks.py test_head guards_indexed_31337 tests/test_docs_gobernanza.py tests/test_gobernanza_taxonomia.py tests/test_no_pii_en_tests.py tests/test_precommit_leak_guard.py tests/test_leak_guard_formas.py tests/test_crm_atlas.py -p randomly --randomly-seed=31337
```

Ambas dieron `2 failed, 146 passed, 1 skipped, 7 errors` (62.48 s y 61.45 s). Todos los fallos/errores eran de `test_precommit_leak_guard.py` al ejecutar `git init` en fixtures con rutas demasiado largas: `Filename too long`. **No fueron fallos de `test_docs_gobernanza.py` ni del diff.** Los tracebacks completos, comandos y entornos están en `guards_indexed.txt` y `guards_indexed_31337.txt`; se conservan también los intentos fallidos.

Para probar la causa se repitieron **los mismos seis módulos, sin modificar código ni asertos**, con `AUDIT_SHORT_TMP=1`, que crea una carpeta nueva de esta revisión bajo el temporal del sistema y dirige allí `--basetemp`:

```powershell
$env:AUDIT_SHORT_TMP='1'
& $py run_checks.py test_head guards_short_777 tests/test_docs_gobernanza.py tests/test_gobernanza_taxonomia.py tests/test_no_pii_en_tests.py tests/test_precommit_leak_guard.py tests/test_leak_guard_formas.py tests/test_crm_atlas.py -p randomly --randomly-seed=777
& $py run_checks.py test_head guards_short_31337 tests/test_docs_gobernanza.py tests/test_gobernanza_taxonomia.py tests/test_no_pii_en_tests.py tests/test_precommit_leak_guard.py tests/test_leak_guard_formas.py tests/test_crm_atlas.py -p randomly --randomly-seed=31337
```

```text
Semilla 777; basetemp C:\Users\tnm33\AppData\Local\Temp\pdr1_lyu9lnap\pytest:
155 passed, 1 skipped in 47.11s
EXIT: 0

Semilla 31337; basetemp C:\Users\tnm33\AppData\Local\Temp\pdr1_t5ioi4y0\pytest:
155 passed, 1 skipped in 48.36s
EXIT: 0

SKIPPED [1] tests\test_no_pii_en_tests.py:42: blocklist no disponible (data/_saneado/replacements.txt); el guard corre donde la lista existe (PC + hooks pre-commit/pre-push)
```

Logs íntegros: `guards_short_777.txt` y `guards_short_31337.txt`. El único cambio entre fallar y pasar fue la ubicación de los temporales. No se debilitó ningún guard.

**Ancla:** se extrajo el fragmento real de la fila 24 y se calculó el del encabezado con la regla indicada en el mandato: minúsculas, eliminación de corchetes/coma y espacios por guiones. `python verify_repo.py` produjo:

```text
ANCLA_FILA24=siguiente-alta-poder-alta-canónica-de-un-poder-en-el-crm-desde-el-pdf-con-su-procurador-enganchado
ANCLA_ENCABEZADO=siguiente-alta-poder-alta-canónica-de-un-poder-en-el-crm-desde-el-pdf-con-su-procurador-enganchado
ANCLA_RESUELVE=True
```

No hay hallazgo en el ancla. Los guards de índices pasan con el corpus real enumerado; no detectan contradicciones de significado como H5. No se encontró un guard específico que resolviera esta ancla: se verificó por cálculo independiente.

## 4. Contraste por sección y referencias cruzadas

Se leyó §16 completo y se cotejaron todas las secciones pedidas. Resultado puntual:

| Referencia desde §16 / PLAN | Contraste contra la sección destino |
|---|---|
| §0.3 | Existe y enumera **nombres de propiedades escalares**. La frase nueva «contrato entero» de 1908 es demasiado amplia: la fuente excluye relaciones y el probe no proporciona tipos/enums. Debe leerse como inventario de propiedades, no contrato suficiente de alta. No lo elevo a otro MEDIO porque §16.2 aporta separadamente esquema/enums/relaciones. |
| §5.1 | No respalda `downloadUri`; receta incompatible, H4. |
| §10.7 | Sí respalda PUT plano parcial y preservación de omitidos en extrajudiciales, y la forma `properties=a,b,c` del detalle. §16.4 añade la medición sobre poderes sin contradicción de verbo/body. |
| §14.6 | Sí contiene el caso de HTTP 200 con listado completo por filtros ignorados y la regla de verificar el resultado. También prescribe sujeto sacrificable para descubrir escrituras: la generalización de §16.3 no debe convertirse en permiso de experimentar sobre clientes, H3. |
| §15.1 | Sí describe `view/config/{element}/fields` y su forma `items`, nombres y tipos. |
| §15.5 | Sí respalda `related_register` y la desacumulación por clave/id. También declara DELETE, incompatibilidad H2. |
| §16.3 | Contiene el POST con array y la tabla de direcciones para poderes. Para usar esa tabla hay contrato explícito; para derivar otros casos solo por pertenencia hay ambigüedad, H3. |
| §16.6 | Contiene las fechas/fuentes declaradas de vigencia y el formato de Notas. No hay certificados originales en el objeto para contrastar sus datos. |
| §16.7 | Sí respalda renombrar `gdocu` mediante `nombrefinal` y `asunto`, preservando `nombreoriginal` según la medición declarada. No documenta la subida, y PLAN lo reconoce como pendiente. |

Respecto a las otras secciones exigidas: §3.1 conserva las promesas de exhaustividad y rutas de descarga obsoletas de H4/H5; su POST de relación sigue marcado pendiente pese a la evidencia posterior. §8 es coherente con el array JSON del POST y con vincular en paso separado. §10.6 usa `right` desde extrajudiciales hacia sus relacionados: **no** contradice que desde poderes el poderdante vaya por `left`. Su antigua «única verificación […] visual» ya estaba superada por §15.5 antes de este diff; no se imputa como regresión nueva independiente. §14.2 permite `like` con escalar y con valor indexado para campos escalares; §16.8 no aporta un query completo que contradiga esas reglas. Se conserva el matiz de que `associated` exige escalar y `Tags` exige array; no se propone cambiarlo. §15.3 y §16.3 coinciden en POST con array de strings.

La regla «un hecho, un hogar» aparece literalmente en `GOBERNANZA_FUENTES_VERDAD.md:17`. Hay duplicación genérica de GET/PUT entre §10.7 y §16.4, pero la medición nueva específica de poderes aporta información distinta: no la considero por sí sola un defecto MEDIO. Sí importan los hogares con instrucciones incompatibles (H2/H4/H5) y la doble lista cuantitativa (H7).

## 5. Ataque operativo y datos personales

**Vínculos:** la tabla concreta de §16.3 identifica las direcciones pretendidas, pero la regla general no basta para prevenir un vínculo erróneo en otro elemento. Verificar después es necesario y no sustituye a resolver la identidad y el papel antes. El NIF identifica una persona; no acredita por sí solo que el CRM tenga una única ficha: el repo ya documenta duplicados de clientes en §10.1. Para el diseño futuro, 0/múltiples coincidencias y el respaldo por nombre necesitan una salida segura previa al POST. El texto aún no es ese diseño y no se presenta la falta de implementación como hallazgo.

**cp1252:** §16.5 sí formula una regla aplicable a **todo el valor**, por tanto también al que procede de un PDF; no se limita a constantes. PLAN la extiende a PUT/POST. Se ejecutó el codec real:

```text
CP1252 U+26A0 '⚠': UnicodeEncodeError
CP1252 U+2013 '–': 96
CP1252 U+2014 '—': 97
CP1252 U+00B7 '·': b7
CP1252 U+00F1 'ñ': f1
CP1252 U+0301 '́': UnicodeEncodeError
CP1252 U+202F '\u202f': UnicodeEncodeError
CP1252 U+0416 'Ж': UnicodeEncodeError
```

Consecuencias: `encode("cp1252")` **no detecta** los dos guiones que el texto prohíbe por separado. El consumidor tendrá que aplicar ambas condiciones; no basta implementar solo el codec. Texto extraído puede contener acentos descompuestos, espacios estrechos o cirílico: «cambiar la notación» no define qué transformaciones preservan un nombre o ámbito. Una normalización segura y la detención ante texto sin conversión fiel son decisiones pendientes; no debe inferirse autorización para usar `errors="ignore"` o `"replace"`. El mandato no aporta una ejecución que use esas conversiones, por lo que no afirmo una pérdida de datos ya ocurrida. El comportamiento real del servidor frente a esos caracteres queda sin verificar.

**Convención y plan:** el hueco determinista de `Tipo/OBJETO` es H6. Para abogado, §16.8 permite omitir el nombre del título y PLAN excluye la ficha de procurador: no hay contradicción en esa excepción. Los ocho campos limitan el diseño pero no prueban que sea imposible crear una ficha. La subida en tres pasos está **expresamente pendiente**; no se trata como trabajo incumplido. No se pudo confirmar el contrato efectivo de `POST /api/element_register/poderes` ni el prototipo externo: sanear por PUT registros existentes no reproduce un alta. La expresión «contrato entero medido» del plan no constituye evidencia independiente de ese POST. Debe conservarse como dependencia de validación, sin inventar una respuesta del CRM.

**PII:** se inspeccionaron las 351 líneas añadidas completas, además de un barrido automático sobre los fragmentos añadidos con número de línea de `head`. Patrones: DNI, NIE, CIF, correo, teléfono español y 17 dígitos de NIG. Se ejecutó además `escanear_formas` real sobre copias `.txt` de las adiciones fuera de `docs/`, para evitar su exención de detección por forma. Resultado de `python -B verify_offline.py`:

```text
PII_REGEX: 351 lineas añadidas; 0 candidatos estructurados
GUARD_FORMAS_ADICIONES_SIN_EXENCION_DOCS: ([], [])
BLOCKLIST_COPIA: 0 terminos
```

No encontré nombres de clientes particulares/terceros, NIF/CIF/NIE concretos, direcciones, teléfonos, correos ni valores de NIG en las adiciones. `N.I.G.`, `NIF` y los campos de identidad aparecen como etiquetas, sin valores. `Nikolai` y `Ana` aparecen como actores del despacho, ya identificados como usuarios internos en `CLAUDE.md:225`–226; no son nombres de partes nuevas de un caso. Los ids numéricos de poderes y relaciones son referencias técnicas, no nombres revelados por esta revisión.

`EV MMC` y `EV SPAIN` aparecen en `INTEGRACION_SUDESPACHO.md:2070` como ejemplos de abreviatura del cliente, expresamente contextualizados por el mandato; **no los considero un hallazgo de PII**. El cliente principal ya se nombra en `CLAUDE.md:8`–9 y en la documentación base. `eplanv2_TNM`, en `INTEGRACION_SUDESPACHO.md:1943`, es un identificador de base de datos del tenant dentro de un error técnico, no un identificador personal ni una credencial; tampoco lo considero un hallazgo de PII. No se ha usado para acceder a ningún sistema. Matiz respecto al mandato: la búsqueda de `eplanv2` sin distinguir mayúsculas en todos los Markdown de `base` no devolvió coincidencias; no doy por comprobada su preexistencia. Su clasificación como identificador técnico no depende de que ya estuviera publicado.

## 6. Sin verificar y límites de la cobertura

- **CRM en vivo:** no se revalidaron los 89 elementos de `/api/elements`, los ocho campos/enums de poderes, los 85 registros/87 documentos, los 431 cambios, las cifras de caducados o fichas incompletas, los POST/PUT/lecturas declarados, la respuesta 201 sin efecto, el mojibake, el filtro por partido judicial, el renombrado ni sus preservaciones. Son mediciones atribuidas al autor, no observadas por este revisor. Su falta de reproducción no se convierte en hallazgo.
- **Borrado:** se verificó que hay un endpoint **declarado en el repo**; no su funcionamiento, alcance, payload, permisos ni reversibilidad efectiva. No se ensayó ninguna escritura.
- **Los otros 27 nombres sin ficha:** su operatividad no se deduce del atlas y no se sondeó; H7 acota el lenguaje del cálculo, no afirma que no existan.
- **PDFs y prototipo:** no se dispuso de los certificados/escrituras/traducciones originales ni del prototipo que PLAN sitúa fuera del repo. No se revalidaron la extracción, el orden de cajas, la variedad de formatos, el cálculo de vigencia ni la lectura de facultades. No se emite dictamen jurídico sobre vigencia o suficiencia del poder.
- **PII por identidad conocida:** falta la blocklist privada; su test quedó explícitamente omitido. La inspección manual y los patrones no prueban ausencia universal de nombres/direcciones arbitrarios. Los tests del leak-guard prueban el mecanismo con datos sintéticos, no sustituyen a esa lista.
- **Cobertura de tests:** se ejecutaron los seis módulos indicados y los cálculos particulares; no toda la suite de producto, ni sesiones de navegador ni scripts de integración externos. La primera corrida directa de gobernanza tuvo ramas de inventario Git vacías; se compensó con la copia íntegra indexada, dos semillas y comparación de sus bytes.
- **No se modificó ni remedió el diff.** Este informe identifica correcciones para adjudicar; las fuentes y las mediciones del autor siguen siendo la base para esa adjudicación.

VEREDICTO: NO-SHIP
<!-- informe-literal:fin:qvzp -->

---

## 2. Evidencia verificada por mí al adjudicar

Cada hallazgo se comprobó **contra la fuente del repo**, no contra el informe ni contra el diff.
Comandos y salidas de esta sesión:

| Hallazgo | Qué comprobé | Fuente, con línea | Resultado |
|---|---|---|---|
| H1 | el predicado literal de la regla de rondas | `CLAUDE.md:57` → «decide **quién puede escribir** sobre qué copia, o puede **destruir o corromper datos de cliente**» → **2** | el diff decía «ni puede destruir datos (solo añadir)»: predicado **recortado**. CONFIRMADO |
| H2 | si el `DELETE` de vínculo está declarado | `INTEGRACION_SUDESPACHO.md:1794` → «Crear / actualizar / borrar vínculo … `POST` · `PUT` · `DELETE`»; `CRM_SUDESPACHO_ATLAS.md:1060` → `DELETE /api/relation_element/{element}/{id}` | está **declarado** en dos sitios. Mi «no hay endpoint documentado» era falso. CONFIRMADO |
| H3 | si el esquema desambigua el lado | `GET /api/view/config/poderes/relations` (mi propia medición) → `{"parent":["clientes_propios"],"children":["clientes_propios","gdocu","procuradores_propios"]}` | `clientes_propios` está en **los dos** lados: la regla generalizada no decide. CONFIRMADO |
| H4 | si §5.1 documenta el flujo vivo | `INTEGRACION_SUDESPACHO.md:441` manda a `/api/files/presigned_download_url/{doc_id}`; `:450` dice «pendiente de implementar»; `core/sync_sudespacho.py:153,782` ya usa `document_download_uri` | §5.1 lleva **cuatro meses** desmentido por el código, y yo remitía a él. CONFIRMADO |
| H5 | si las puertas de entrada al atlas prometen totalidad | `INTEGRACION_SUDESPACHO.md:74` «ya mapea toda la superficie», `:76` «SSOT de "qué existe"», `:178` «inventario **exhaustivo** … toda la superficie»; `INDICE.md:46` «SSOT de la superficie del CRM» | tres puertas prometen lo que la §16.1 desmiente, y son donde se ordena consultar primero. CONFIRMADO |
| H6 | si el vocabulario de OBJETO mapea a `Tipo` | `INTEGRACION_SUDESPACHO.md:1917` → `Tipo` es `-1`/`General`/`Especial`, **sin combinado**; `:2059` incluye `Pleitos general + especial` | la regla que usé al sanear (`+ especial` → `General`) vivía **en mi código y no en el doc**. CONFIRMADO |
| H7 | qué demuestra el cruce de 28 | mi cruce cuenta **nombres citados sin ficha**; solo sondeé `poderes` | «28 operativos» excede lo medido en 27. CONFIRMADO |

**Lo que el revisor midió y confirmo:** su recuento independiente coincide con el mío
(`FICHAS=89`, `SIN_FICHA=28`, `UNION=117`) y la lista literal de #176 casa con su cálculo. Corrió
`tests/test_docs_gobernanza.py` sobre `head` y **no falló**, lo que descarta que el diff rompiera la
gobernanza documental.

**Lo que NO se verificó, y queda declarado:** que el `DELETE` de vínculo **funcione** en este tenant.
El revisor no lo ejecutó (se lo prohibí) y yo tampoco. Lo que cambia el diff es la afirmación de
inexistencia documental, que era falsa; la operatividad sigue **sin medir**, y así se escribe.

**Sobre el objeto:** las dos copias (`base` y `head`) tenían el mismo `sha256` de recorrido ordenado
al abrir y al cerrar la ronda — `1ab37932…` y `fcf49a5c…` —, así que el revisor no mutó el objeto.
El revisor declaró en su primera línea que su workdir solo contenía el mandato.

---

## 3. Adjudicación de la revisión adversarial del contrato de `poderes` (Codex, 2026-09-08) — NO-SHIP, remediado

- **Objeto revisado:** `docs/INTEGRACION_SUDESPACHO.md` §16 nueva, más la entrada de `DEAD_ENDS.md`, `MEJORAS_FUTURAS.md` #176, la fila 24 y el bloque `[SIGUIENTE-ALTA-PODER]` de `PLAN.md`, y la fila del atlas en `docs/INDICE.md` — commit `0ce01a8`
- **Ronda:** 1 de 1 (radio de daño «todo lo demás»: documentación, sin código)
- **Revisor:** Codex (`codex-cli 0.153.4`, esfuerzo alto, sandbox de solo lectura sobre dos copias externas)
- **Informe recibido:** §1 de esta acta, literal, `sha256` `9429775e07dfbfecc47ee74199d4335a1171265449a2b698be0a4b7de2ba4364`
- **Hallazgos:** 7 — 1 ALTO, 5 MEDIO, 1 BAJO. **7 confirmados, 0 refutados.**
- **Remediado en:** el mismo commit del diff; H1 en `PLAN.md`, H2 en `INTEGRACION_SUDESPACHO.md` §16.3 y `DEAD_ENDS.md`, H3 en §16.3 y `DEAD_ENDS.md`, H4 en §5.1 y §16.7, H5 en §0.4, §3.1 y `INDICE.md`, H6 en §16.8, H7 en §16.1 y #176

**Cero refutados, y el ALTO es el que más vale.** H1 no es un descuido de redacción: es
[[feedback-no-redefinir-mi-regla-de-parada]] otra vez. La regla de `CLAUDE.md` da **dos** rondas a lo
que puede «destruir **o corromper** datos de cliente»; yo escribí «ni puede destruir datos (solo
añadir)» y me adjudiqué una. Y lo hice **en el mismo bloque** donde cito el `#56`, un registro cuyo
poder cuelga de un cliente que no lo otorgó — o sea que tenía el contraejemplo delante mientras
recortaba el predicado. La pieza de alta pasa a **dos rondas**, diseño y diff.

**H2, H4 y H5 son la misma clase, y esa clase es la que este diff venía a combatir.** Los tres son
afirmaciones que otra parte del propio repo desmiente:

- dije que no había endpoint documentado para borrar un vínculo, y el §15.5 —que **leí en esta misma
  sesión** para saber cómo leer relaciones— lo declara tres líneas más arriba de la tabla que usé;
- remití al §5.1 como respaldo de un flujo de descarga que el §5.1 no describe, y que además lleva
  cuatro meses diciendo «pendiente de implementar» algo que el código ya implementó;
- documenté el punto ciego del atlas **al final** del documento, dejando intactas las tres puertas de
  entrada que prometen «toda la superficie» — que es exactamente el error operativo que #176 dice
  querer evitar, y el defecto de [[feedback-corregir-el-doc-y-no-su-indice]].

El remedio de los tres no es matizar la §16: es **arreglar el sitio que miente**. Por eso este diff
toca §0.4, §3.1, §5.1 e `INDICE.md`, que no eran parte del encargo.

**H3 y H6 son generalizaciones mías que no se sostienen.** En H3 escribí una regla —`parent` → `left.`,
`children` → `right.`— y la ilustré con el único caso en que **no funciona**: `clientes_propios` está
en los dos lados. En H6 dejé el vocabulario de OBJETO como cerrado sin decir a qué valor de `Tipo`
mapea cada término, cuando `Tipo` no tiene valor combinado y el vocabulario sí: la regla existía en el
generador que usé para sanear y no en el documento, así que dos implementadores habrían producido
registros distintos cumpliendo el texto.

**H7 es exacto y es el más pequeño**: el cruce demuestra 28 **nombres citados sin ficha**; que el
endpoint responda solo lo comprobé en `poderes`. Llamarlos «28 operativos» era estirar el dato
27 veces. Corregido a «citados sin ficha», con la lista en un solo hogar (#176) y el aviso con
puntero en §16.1.

**Lo que el revisor NO pidió y conviene registrar:** no pidió una segunda ronda sobre este diff, ni
una tercera sobre la pieza futura, ni sondear los 28 elementos antes de publicar. Lo dice
explícitamente en H1, H5 y H7. Ninguno de sus remedios exige tocar el CRM.
