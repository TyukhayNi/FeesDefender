---
tipo: revision-adversarial
objeto: core/sudespacho_actuaciones.py
objeto_rev: "2"
commit: 53cc575
ronda: "3"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q7zx
sha256_informe: 9cee270338dc86e23014847da342aef1a314ecbc5dbbe41950b121f5f7e0f539
adjudicado_en: docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md §8
---

# Acta — R3 adversarial sobre la REMEDIACIÓN de P6

Objeto: el diff remediado `8aed442..53cc575`. **Ronda excepcional**, autorizada expresamente por
Nikolai sobre el techo de dos rondas y pedida por una razón concreta: los remedios de hallazgos
`ALTO` son donde suele aparecer el defecto siguiente. Su objeto **no era la pieza sino la
remediación**.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, `model_reasoning_effort=high` |
| Objeto | `C:/t/p6r3-obj-034734/{base,head}` (copia `git archive`, solo lectura) |
| `sha256` del informe | `9cee270338dc86e23014847da342aef1a314ecbc5dbbe41950b121f5f7e0f539` — **coincide con el que el revisor devolvió aparte** |
| Veredicto | **NO-SHIP** |
| Hallazgos | 9 — 1 `CRÍTICO`, 4 `ALTO`, 4 `MEDIO`; **9 confirmados, 0 refutados** |
| Arnés | reprodujo el 37/37 **y midió que una de esas muertes era falsa** (H-08) |

**La ronda tardó dos intentos en arrancar, y el primero no dejó informe.** A las 03:48 murió en
el arranque con `Selected model is at capacity`, sin escribir un token — una cuarta forma de
caerse, distinta del cupo, del `404` del backend y del filtro de contenido, y la única
**transitoria**. Se descartó que fuera el mandato variando un eje cada vez: esfuerzo, flags y
prompt, los tres vivos por separado. El `_stdout.log` del intento fallido se conserva en
`C:/t/p6r3-rev-034734/`, y por eso la ronda buena corrió en un directorio nuevo.

**Lo que esta ronda compró, en una frase:** que el remedio de la R2 cerraba **el caso** y no la
frontera en cinco de los trece sitios, y que el `37/37` del arnés era **36 muertes y una
coartada**. La adjudicación completa, con las siete fronteras en que se agrupan los nueve
hallazgos, está en el §8 del spec.

**Y el revisor declaró que no pide una cuarta ronda.** Importa decirlo: el techo de rondas
existe porque el argumento «la anterior encontró algo, luego hace falta otra» nunca se agota.
Nikolai decidió cerrar sin ella.

## 0. Mandato, literal

<!-- mandato-literal:inicio:q7zx -->
# Mandato — R3 sobre el DIFF REMEDIADO de P6

**Ronda 3 de 3, autorizada expresamente por Nikolai** tras leer el resultado de la R2 (dos
revisores en paralelo, los dos NO-SHIP). El presupuesto ordinario de esta pieza eran dos
rondas; esta es la excepción, y se pidió por una razón concreta: **los remedios de hallazgos
ALTO son justo donde suele aparecer el defecto siguiente**. En esta misma pieza ya pasó — el
primer remedio de la R1 *creaba el estado que el propio código bloqueaba después*.

Tu objeto **no es la pieza entera: es la remediación**.

## 0. Higiene del workdir

Tu workdir (`-C`) contiene **solo este `MANDATO.md`** y lo que tú escribas. Si encuentras otro
fichero, **no lo leas** y decláralo en la primera línea del informe.

## 1. El objeto

- `C:/t/p6r3-obj-034734/base/` — el árbol **antes** de remediar (`8aed442`), el que la R2
  declaró NO-SHIP.
- `C:/t/p6r3-obj-034734/head/` — el árbol **remediado** (`53cc575`).

**SOLO LECTURA.** Reporta el `sha256` **al abrir y al cerrar** de:

- `head/core/sudespacho_actuaciones.py`
- `head/core/sudespacho_relations.py`
- `head/core/crm_ficha_validacion.py`

**La adjudicación de la R2 está en el objeto** y es lo que tienes que contrastar:
`head/docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md` **§7** (tabla de
los quince hallazgos y su remedio declarado), más el acta `…-r2-adversarial-review.md`.

## 2. Puedes ejecutar, y debes

`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, copiando `head/` a tu
workdir. `--basetemp` **relativo**, `PYTHONDONTWRITEBYTECODE=1`. **Sin credenciales del CRM: si
algo intenta llamar al tenant, es un hallazgo.**

Corre al menos: `tests/test_sudespacho_actuaciones_r2.py`, `tests/test_sudespacho_actuaciones.py`,
`tests/test_resolver_parte_aper71.py`, `tests/test_crm_ficha_n_contrarios.py`,
`tests/test_crm_ficha_cli.py`, `tests/test_crm_ficha_validacion*.py`,
`tests/test_sudespacho_relations.py`, y **el arnés** `python -m tests._mutantes_p6` (el autor
declara **37 mutantes, 37 muertos**).

## 3. La pregunta central de esta ronda

**¿El remedio de cada hallazgo cierra la FRONTERA, o solo el caso que el informe describía?**

La R2 identificó una frontera común a los quince: *cada helper distingue estados que su único
llamador colapsa*. El autor dice haber reescrito el orquestador en vez de parchear seis sitios.
Compruébalo: **¿queda algún sitio donde una distinción siga colapsándose?**

## 4. Dónde mirar con más ganas

1. **¿Algún remedio abre un estado nuevo?** Es el modo de fallo de esta pieza, ya observado dos
   veces. En particular: la guarda de truncamiento del buzón (`_LIMITE_BUZON`), ¿puede parar un
   caso legítimo que antes resolvía? ¿Y el `Recibo` con `elemento`/`exp_id`, rompe algún camino
   que antes funcionaba?
2. **`CuerpoIlegible`.** ¿Lo capturan **todos** los consumidores de `_items`? Busca cada llamada
   y comprueba qué pasa si levanta. ¿Hay alguno donde se escape y vuelva a atravesar el
   orquestador?
3. **La guarda de truncamiento.** `if len(c_mail.registros) >= _LIMITE_BUZON`. ¿Es correcta la
   comparación? ¿Qué pasa si el servidor devuelve **más** de lo pedido, o exactamente el
   límite habiendo justo esas fichas y no más? ¿Se puede distinguir «hay exactamente 50» de
   «hay 50 y puede haber más»?
4. **`alta_actuacion` reescrita.** Lee la función entera. ¿Las guardas de `desde` son
   exhaustivas? ¿Qué pasa con un `Recibo` construido a mano con estado inventado, con
   `elemento` vacío pero `exp_id` puesto, o con `paso` incoherente?
5. **`crm_ficha_validacion`.** El autor cambió la clave del `Dato` a `contrario[i].campo`
   cuando hay más de uno. ¿Rompe eso algún consumidor del informe? Busca quién lee `.campo`.
6. **`asunto_canonico` con la regex nueva.** ¿Hay alguna entrada donde `_RE_PREFIJO` case algo
   que no debería, o deje de casar algo que sí? Piensa en el prefijo repetido, en un asunto que
   empieza por guion, en unicode.
7. **La duración con zona.** ¿La comprobación cubre los dos extremos en todos los caminos?
   ¿Qué pasa con una zona explícita `+00:00` frente a `Z`?
8. **El arnés.** Verifica el 37/37. ¿Algún mutante nuevo está mal apuntado o es trivial?
   ¿Falta mutante para alguno de los quince remedios? El autor retiró M16 declarando que M29 lo
   absorbe: ¿es cierto?
9. **Los tests nuevos.** ¿Alguno pasa por la razón equivocada? El autor ya encontró dos así en
   esta pieza (un doble de HTTP que consume respuestas en orden, y un fixture con `id` fijo).
10. **Lo que el diff dice de sí mismo.** El §7 afirma que los quince están remediados y declara
    uno **no** remediado (el test preexistente que llama al CRM). Comprueba que esa declaración
    es exacta: ¿hay alguno que se dé por remediado y no lo esté?

## 5. Formato del informe

`INFORME.md` en tu workdir, con: `## Higiene y no-mutación`, `## Qué pude ejecutar y qué no`,
`## Hallazgos` (ID, **severidad** CRÍTICO/ALTO/MEDIO/BAJO, **coste** trivial/acotado/estructural,
fichero:línea, manifestación concreta, cómo lo comprobaste, **de qué frontera es un ejemplo**),
`## Lo que revisé y NO encontré defectuoso`, `## VEREDICTO`.

**Última línea: el veredicto, exactamente una de estas tres palabras y nada más:**

```
SHIP
SHIP-CON-CAMBIOS
NO-SHIP
```

**`SHIP` es un resultado legítimo y se ha emitido cero veces en 87 actas.** Si has atacado el
objeto y no encuentras nada que impida mergearlo, dilo: esa es la respuesta correcta, no la
señal de que no has mirado bastante. Lo que se te exige a cambio es la sección
`## Lo que intenté refutar y NO pude`, con el ataque detrás.
<!-- mandato-literal:fin:q7zx -->

## 1. Informe recibido, sin modificar (Codex, 2026-09-14)

Tal como lo escribió el revisor. El digest de arriba se computó **al recibirlo** y se contrastó
con el que devolvió por separado en su último mensaje:

> [INFORME.md](C:/t/p6r3c-rev-0415/INFORME.md) — 9 hallazgos. Persisten fronteras abiertas y M29 muere por `NameError`. Objetos originales sin cambios.
> 
> SHA-256: `9cee270338dc86e23014847da342aef1a314ecbc5dbbe41950b121f5f7e0f539`
> 
> NO-SHIP

<!-- informe-literal:inicio:q7zx -->
Higiene: al iniciar había `_stdout.log` además de `MANDATO.md`; no leí su contenido.

# Informe R3 — remediación de P6 (8aed442 → 53cc575)

## Higiene y no-mutación

Revisión realizada el 2026-09-14, limitada a la remediación y sus fronteras. Las referencias de código corresponden a `C:/t/p6r3-obj-034734/head/`, salvo indicación expresa. Los identificadores de commit proceden del mandato: **genealogía SIN VERIFICAR**, al tratarse de exportaciones sin `.git`. Claude adjudica contra la fuente. No hubo delegación ni consultas al remoto o al tenant.

`base/` y `head/` se mantuvieron en solo lectura. Las ejecuciones y mutaciones definitivas se hicieron sobre `copia/`, `audit-copia/` y `base-copia/`, dentro de este workdir. Los scripts, fixtures sintéticos, resultados y este informe están fuera del objeto. No se hicieron commits ni operaciones de staging. Un primer cargador de sondas intentó importar el módulo de relaciones de base con bytecode desactivado y falló por import relativo; la ejecución definitiva empleó la copia local y el nombre de paquete correcto.

SHA-256 al abrir, antes de leer los tres módulos, y al cerrar:

| Fichero bajo `head/` | Apertura | Cierre |
|---|---|---|
| `core/sudespacho_actuaciones.py` | `749db98e55c857e42d75f3c8048da3c520b83867345d0cc564ca5b2c933ab70d` | `749db98e55c857e42d75f3c8048da3c520b83867345d0cc564ca5b2c933ab70d` |
| `core/sudespacho_relations.py` | `c7548a91c77c238c8911f23ea38cdf538f7cfcec4087c963d5fac533c504dd60` | `c7548a91c77c238c8911f23ea38cdf538f7cfcec4087c963d5fac533c504dd60` |
| `core/crm_ficha_validacion.py` | `ccee6c3ada5f45854af2215b68b229ef073603e7c2932a17a549bb8b7b2d4e52` | `ccee6c3ada5f45854af2215b68b229ef073603e7c2932a17a549bb8b7b2d4e52` |

También comparé manifiestos completos: **1.337 ficheros en base y 1.339 en head; cero cambios de contenido, altas o bajas durante la revisión**. Evidencias: `manifest_open.json`, `manifest_close.json`. El diff por contenido tiene 12 rutas y se conserva en `diff.txt`; tres son módulos de producción. El arnés solo mutó copias locales.

## Qué pude ejecutar y qué no

Leí el diff, el diseño con §7, el acta R2 disponible, la función `alta_actuacion` completa, los tres consumidores de `_items`, el transporte de relaciones, los consumidores de `Dato.campo`, los tests afectados y el arnés. Contrasté las obligaciones de aprendizaje con el plan local y `INTEGRACION_SUDESPACHO.md` §15.6. No amplié esta ronda a una revisión general del repositorio.

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`. En todas las ejecuciones: `PYTHONDONTWRITEBYTECODE=1`, UTF-8 y dotenv desactivado. Pytest recibió `--basetemp` relativo dentro del workdir y `-p no:cacheprovider`. No se usaron credenciales. Algunos tests fijan sus propios valores ficticios; una segunda corrida diagnóstica añadió un valor ficticio ambiental para ejercer el test del CLI que lo presupone.

`guard/sitecustomize.py` bloqueó el transporte HTTP real y, como segunda barrera, DNS/conexiones mediante auditoría de Python. Registró los intentos sin cabeceras ni claves. La variante inicial levanta `RuntimeError`; la variante estricta levanta una excepción que hereda directamente de `BaseException`, para evidenciar la absorción de la primera. **No hubo salida al tenant.**

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Todos los ficheros exigidos, sin clave ambiental | **317 pasan, 1 falla** | `pytest-required.log` |
| Mismos ficheros, con clave ficticia y barrera de red | **318 pasan**, salida 0 | `pytest-required-synthetic.log` |
| Test del CLI que falla y test de relaciones que intenta red, sobre base | **1 falla, 1 pasa**: mismo fallo del CLI y misma absorción del bloqueo | `pytest-base.log` |
| Test de relaciones, con barrera no absorbible | **Falla en head y en base** por intento de HTTP | `strict-head.log`, `strict-base.log` |
| `python -m tests._mutantes_p6`, sin modificar el arnés | Salida 0; declara **37 mutantes, 37 muertos** | `mutantes.log` |
| Auditoría de mutantes | 37 sustituciones únicas, 37 resultados sintácticamente válidos; ejecución detallada de M19 y M27–M38. **M29 muere por NameError** | `audit-mutants-results.json`, `mutant-audit/` |
| M29 con su regex restaurada solo en la copia; supresión completa del contraste, equivalente a M16 | Ambos producen el rojo semántico esperado | `mutant-audit/M29-fixed-fixture.log`, `mutant-audit/M16-equivalent.log` |
| Sondas por rutas HTTP y con estado, sin colas de respuestas | 18 ataques de forma JSON, 5 estados de aprendizaje, recuperación, 7 recibos manuales, 6 casos de paginación comparados con base, asuntos, plantillas y 16 combinaciones temporales | `probes_r3.py`, `probes-results.json` |
| Consumidores de `CuerpoIlegible` y CLI real del validador con documental sintética | Tres consumidores correctos ante esa excepción; CLI enumera ambos contrarios y termina con código 1 cuando faltan datos del segundo | `extra_checks.py`, `extra-checks-results.json` |

Los ficheros exigidos fueron `test_sudespacho_actuaciones_r2.py`, `test_sudespacho_actuaciones.py`, `test_resolver_parte_aper71.py`, `test_crm_ficha_n_contrarios.py`, `test_crm_ficha_cli.py`, `test_crm_ficha_validacion.py`, `test_crm_ficha_validacion_r1.py` y `test_sudespacho_relations.py`, todos bajo `tests/`.

Comando reproducible, desde una copia local de head:

```text
python -m pytest -o addopts= -p no:randomly -p no:cacheprovider --basetemp=../tmp-required-repro -q --tb=short tests/test_sudespacho_actuaciones_r2.py tests/test_sudespacho_actuaciones.py tests/test_resolver_parte_aper71.py tests/test_crm_ficha_n_contrarios.py tests/test_crm_ficha_cli.py tests/test_crm_ficha_validacion.py tests/test_crm_ficha_validacion_r1.py tests/test_sudespacho_relations.py
```

El arnés recibió por entorno `PYTEST_ADDOPTS="--basetemp=../tmp-mutantes -p no:cacheprovider"`; sus subprocesos heredaron también `PYTHONPATH` apuntando a `guard/`. Las sondas se ejecutan desde este workdir. No ejecutar el arnés sobre el objeto congelado.

**SIN VERIFICAR:** suite completa y sus dos semillas, aceptación actual de payloads por el tenant, límites efectivos de paginación del servidor, idempotencia real del POST de creación y del vínculo, concurrencia, y constructores externos al árbol. Los dobles acreditan las decisiones ante las respuestas descritas, no la frecuencia de esas respuestas en producción. El acta hermana `…-r2b-adversarial-review.md`, citada por el autor, **no está en el objeto**: no atribuyo a ese segundo revisor hallazgos que no pude leer.

## Hallazgos

Los defectos persistentes se distinguen de los estados nuevos que crea el remedio. Los costes estiman el cierre de la frontera; no autorizan una ampliación del alcance.

### H-01 — El remedio de parseo todavía pierde el recibo después de escribir

**Severidad: CRÍTICO. Coste: acotado.** `core/sudespacho_actuaciones.py:118`, `:124`, `:535`, `:622`. Remediación incompleta del «Parseo» de §7; conserva el daño allí adjudicado crítico.

El `try` de `_items` cubre exclusivamente `resp.json()`. Un JSON válido con `{"items": 1}` o `{"hydra:member": true}` falla después, al iterar, con `TypeError`, que no se convierte en `CuerpoIlegible`. El paso 6 solo captura esta última excepción y `alta_actuacion` no protege esa llamada.

**Manifestación y comprobación:** las sondas `malformed`, etapa `verification`, crean `N1`, escriben su vínculo y reciben ese HTTP 200. El resultado es `TypeError`, sin recibo; el censo sintético conserva `N1` creada y vinculada. El llamador pierde el id que necesitaba para recuperar el resultado y una repetición completa vuelve a permitir crear. En las etapas 1 y 3 también se escapa el mismo `TypeError`; `values: [null]` produce además `AttributeError` al aprender. Una lista como cuerpo o un objeto de error se convierten en filas vacías, que llegan al problema de H-03.

**Frontera:** decodificar JSON no acredita su estructura ni preserva los efectos parciales. Los tres consumidores **sí capturan `CuerpoIlegible`**; lo que no está cerrado es que toda respuesta no interpretable se traduzca a ese contrato, y que ningún fallo de verificación pueda borrar el recibo. El test nuevo solo ejercita `json()` lanzando, por eso permanece verde.

### H-02 — La identidad del recibo es opcional al reanudar

**Severidad: ALTO. Coste: acotado.** `core/sudespacho_actuaciones.py:442`, `:566`, `:572`, `:616`. Remediación incompleta de «Recibo sin destino».

La comparación está condicionada a `desde.elemento`. Los valores por defecto siguen permitiendo construir un recibo sin destino y saltarse precisamente la comprobación añadida. No se validan tampoco los estados admitidos ni la coherencia de `paso`.

**Manifestación y comprobación:** `Recibo("incompleta", act_id="AJENA", paso=4, elemento="", exp_id="999")`, pasado a un alta sobre `extrajudiciales/464`, escribe `right.actuaciones.AJENA` en `/api/relation_element/extrajudiciales/464` y termina `verificada`. Ocurre igual omitiendo ambos campos. Un estado `"inventado"` con paso `-9`, o `incompleta` con paso 1 e id, también se aceptan y vinculan. Evidencia: `probes-results.json/receipts`, con las peticiones completas. Son recibos manuales, admitidos por el constructor público, como pide atacar el mandato; no afirmo que el productor actual emita el estado inventado.

El recibo completo de otro destino sí se rechaza, y `incierta` se rechaza incluso si alguien le pone id. Eso cierra esos ejemplos, no la entrada completa. Los recibos anteriores sin contexto no acreditan identidad por el hecho de ser compatibles con el constructor.

**Frontera:** un contexto ausente no puede desactivar la comprobación que ese contexto existe para permitir. Reanudar requiere un recibo válido y un destino acreditado; acreditar solo el segundo permite vincular una actuación ajena y verificar después ese mismo error.

### H-03 — «Cuatro salidas» sigue consumiendo como iguales «sin filas», «no aplica» y dato inválido

**Severidad: ALTO. Coste: acotado.** `core/sudespacho_actuaciones.py:187`, `:190`, `:195`, `:595`, `:602`. Persistencia del H-05 de R2, adjudicado confirmado en §7.

El orquestador distingue únicamente `sin_comprobar`. `sin_filas` pasa al POST igual que `no_aplica`, sin dejar la diferencia en el recibo final. Además, un `id_predefinido="garbage"` sigue clasificándose como `no_aplica` con el motivo falso «las instancias reales traen el campo vacío».

**Manifestación y comprobación:** `learning_states` obtiene respectivamente `sin_filas`, `no_aplica` y `no_aplica` para cero filas, campo vacío y campo no convertible. Los tres producen la misma creación sin `id_predefinido` y terminan `verificada`, sin motivo. Un id 84 sí se transmite; HTTP 500 sí bloquea la creación. No es una hipótesis sobre un estado inventado: son respuestas que el propio helper produce.

**Frontera:** desconocer la configuración, comprobar que no aplica y recibir un valor inválido son estados de conocimiento diferentes. El remedio solo conserva uno. La R2 ya incluía expresamente tanto cero filas como campo inválido; no pueden considerarse cerrados por el nuevo test de HTTP 500. Debe fijarse y conservarse una decisión explícita para cada estado, sin declarar evidencia de ausencia donde no la hay.

### H-04 — Consultar el asunto canónico no basta para aprender su plantilla exacta

**Severidad: ALTO. Coste: acotado.** `core/sudespacho_actuaciones.py:172`, `:189`, `:193`, `:591`. Remediación parcial de «Paso 1 con otro asunto» y del H-06 de R2.

El filtro sigue siendo `like` y el aprendizaje toma el primer entero de cualquier fila, sin comprobar su `Subject`. Canonizar antes del GET elimina la mezcla simple ABOGADO/SENIOR, pero no distingue el asunto exacto de sus variantes que lo contienen.

**Manifestación y comprobación:** para crear `SENIOR - X`, el doble entrega `SENIOR - X AMPLIADA` con id 99 y `SENIOR - X` con id 84. Ambas filas son compatibles con la búsqueda por subcadena. Permutar su orden cambia el id del POST **99 ↔ 84**, manteniendo el asunto final y el recibo `verificada`. Evidencia: `template_identity`. Los ids son sintéticos. El requisito de exactitud y el riesgo de otro id en una variante histórica constan en el docstring del helper y en `INTEGRACION_SUDESPACHO.md:2080`.

**Frontera:** la evidencia recibida debe corresponder a la misma operación que se ejecuta. Formular una consulta más específica no sustituye la comprobación de identidad en sus resultados. El nuevo test comprueba el prefijo del filtro, pero no esta correspondencia.

### H-05 — La guarda infiere exhaustividad del límite pedido y descarta el total declarado

**Severidad: ALTO. Coste: estructural.** `core/sudespacho_relations.py:1140`, `:1151`, `:1152`, `:1227`, `:1312`. Remediación parcial de «Paginación». El coste incluye conservar información de exhaustividad en `Consulta` y consumirla al decidir.

`_buscar_registros` sigue eliminando `totalItems`/`hydra:totalItems` y devuelve solo registros. La nueva guarda presume que menos de 50 filas significa conjunto completo. Si el servidor limita la respuesta a menos de lo solicitado, se autoriza crear incluso cuando el propio cuerpo declara más coincidencias.

**Manifestación y comprobación:** con NIF sin match y respuesta de email de cinco fichas con NIF distinto más `totalItems=6`, la implementación real de `_buscar_registros` y `resolver_parte` devuelve resolución vacía y `resuelta=True`; hace una consulta por criterio y ninguna continuación. Ocurre también con 49 filas y total 51. Las sondas incluyen las dos claves de total y pasan por HTTP simulado, sin sustituir `Consulta` ni el resolver. La sexta candidata no ha sido descartada: podría carecer de documento y debería bloquear el alta. Evidencia: `pagination`; base también falla. No afirmo haber observado ese límite inferior en el tenant: su comportamiento actual queda sin verificar. Sí está reproducida la pérdida de una señal explícita de incompletitud en un formato documentado localmente.

La comparación **`>=` es correcta para el guard conservador**: bloquea tanto 50 como 51 filas. Exactamente 50 fichas legítimas y distintas quedan bloqueadas, aunque antes se autorizaba crear. Es la pérdida de disponibilidad que admite la decisión de fallar cerrado, no un motivo para cambiarla a `>` o `==`. Con solo longitud no se puede distinguir «justo 50» de «50 y quedan más». Incluso cuando la respuesta aporta el total, hoy se pierde antes de decidir.

**Frontera:** tamaño solicitado, tamaño recibido y totalidad de candidatos no son la misma información. Subir de 5 a 50 y comprobar la longitud cubre un truncamiento concreto; no acredita «todas» en la frontera que autoriza crear.

### H-06 — El remedio genera una `incompleta` que su propia guarda prohíbe reanudar

**Severidad: MEDIO. Coste: acotado.** `core/sudespacho_actuaciones.py:429`, `:567`, `:596`. **Estado nuevo introducido por esta remediación.**

Al fallar el GET de aprendizaje se devuelve `Recibo("incompleta", act_id=None, paso=1)`, aunque el contrato define `incompleta` como efecto existente con id conocido y reanudable. La nueva guarda rechaza cualquier recibo sin id como si pudiera haber una creación pendiente de conciliar.

**Manifestación y comprobación:** la sonda `new_incomplete_state` obtiene ese recibo tras HTTP 500, cambia el doble a una respuesta válida y reanuda con el mismo recibo. Recibe `ActuacionError` que ordena buscar una actuación en el CRM y dice que reintentar crearía una segunda. **Hubo cero POST en todo el recorrido.** No se construyó a mano un recibo imposible: lo produjo la nueva rama.

**Frontera:** «no se intentó escribir» no es «se escribió y conozco el id» ni «no sé si se escribió». El productor y el consumidor del recibo deben compartir esas transiciones. Reutilizar la etiqueta `incompleta` crea el estado que el propio código bloquea después, precisamente el modo de fallo que motivó esta R3.

### H-07 — La nueva validación de `extra` vuelve a convertirse en escritura incierta

**Severidad: MEDIO. Coste: acotado.** `core/sudespacho_actuaciones.py:477`, `:479`, `:600`, `:608`. Interacción entre los remedios de «extra» y «Validación disfrazada».

El firmante ya se valida fuera del `try`, pero el nuevo rechazo de campos reservados de `extra` ocurre dentro de `crear_actuacion`, antes del POST, y lo absorbe el `except Exception` del orquestador.

**Manifestación y comprobación:** con `extra={"Subject": "ABOGADO - X"}`, o sustituyendo `profesional_asignado` o `id_predefinido`, se devuelve `incierta`, paso 4, con el mensaje «el POST no dio recibo… puede haberse creado una actuación… concilia a mano». El doble registra **cero creaciones**. `duracion_s="invalid"` conserva el mismo problema, aunque ese ejemplo no lo introduce el nuevo guard. Evidencia: `validation`.

La protección de los campos sí impide escribirlos. El defecto está en clasificar la validación como incertidumbre de efectos, que es justamente lo adjudicado en R2. El test nuevo de `extra` llama directamente al helper y no ve cómo su único orquestador transforma el error.

**Frontera:** validar el payload y transmitirlo son fases distintas. La clasificación de «resultado del POST incierto» debe empezar cuando puede haber existido ese POST, no antes de construir un payload válido.

### H-08 — M29 cuenta como muerto por una dependencia eliminada

**Severidad: MEDIO. Coste: acotado.** `tests/_mutantes_p6.py:122`, `:190`, `:192`, `:327`; eliminación de `_RE_WCODE` en `core/sudespacho_actuaciones.py:60`.

El mutante sustituye `wcode_match` por una expresión que llama a `_RE_WCODE`, pero ya no define esa regex. Python puede importar el módulo y pytest devuelve 1 por `NameError` al ejecutar. El arnés lo cuenta como muerto porque solo separa el código 4 de error de uso/colección.

**Comprobación:** el arnés original declara 37/37, pero `mutant-audit/M29.log` muestra `NameError: name '_RE_WCODE' is not defined` en los dos casos. Las 37 sustituciones son únicas y sintácticamente válidas: revisar solo sintaxis no detecta este defecto.

Restauré la regex antigua **solo en la copia** junto con la mutación. Entonces el test falla correctamente porque el destino equivocado deja de rechazarse (`DID NOT RAISE DestinoNoAcreditado`). Sustituir el contraste por `if False`, equivalente a M16, produce el mismo rojo semántico. Por tanto **el test puede cubrir M16, pero el M29 entregado no acredita su absorción**. No hace falta reclamar otro test de destino por este motivo: hace falta que la mutación ejercite la propiedad.

**Frontera:** una prueba que falla porque el programa mutado está roto no demuestra que detecte la decisión incorrecta que se quiso introducir. El 37/37 es reproducible como salida del arnés; no son 37 muertes semánticas acreditadas.

### H-09 — Persiste el test preexistente que intenta leer del tenant

**Severidad: MEDIO. Coste: acotado. Preexistente y declarado correctamente en §7.2.** `tests/test_sudespacho_relations.py:1570`, `:1583`; `core/sudespacho_relations.py:1645`, `:1680`, `:1723`.

`test_ensure_contrario_vinculado_existente` deja sin doble la compleción de la ficha existente. Su propia clave ficticia permite llegar a `httpx.get`; la excepción de la barrera inicial se absorbe y el test pasa.

**Comprobación:** `network_attempts.jsonl` identifica ese nodo y el host del CRM. Al cambiar únicamente el bloqueo a una excepción no absorbible, el test falla sobre head y sobre base, con pila desde `_completar_contrario_existente` hasta el transporte. Evidencias: `strict-head.log`, `strict-base.log`. Ninguna petición alcanzó el tenant.

**Frontera:** la tolerancia operativa a un fallo de lectura no puede servir como aislamiento de una prueba. Se incluye porque el mandato exige reportar todo intento; no se presenta como regresión ni fundamenta por sí solo el NO-SHIP de la remediación.

## Lo que revisé y NO encontré defectuoso

Respuesta a los diez focos del mandato, con los límites de cada conclusión:

1. **Estados nuevos.** H-06 es generado por el propio remedio; H-07 aparece al combinar los nuevos guards. Para el buzón de exactamente 50 documenté el bloqueo de un alta legítima: es coherente con la opción conservadora de §7.1, aunque no distingue exhaustividad. Con NIF único ya encontrado y presente entre las 50 fichas de email, se sigue resolviendo por NIF: la guarda no tapa esa prioridad. Los recibos completos de la misma operación recuperan los fallos de vínculo y verificación con una única creación (`normal_resume`). No encontré un consumidor de producción en el árbol que construya `Recibo` con un cuarto argumento posicional; compatibilidad de constructores externos, sin verificar.

2. **Todos los consumidores de `_items`.** Son exactamente tres en este módulo: aprendizaje en línea 184, destino en 274 y verificación en 535. Sus tres capturas de `CuerpoIlegible` funcionan, confirmado inyectando esa excepción y con los tests de cuerpos no-JSON. Ningún consumidor adicional del helper de actuaciones apareció en el barrido. H-01 está en excepciones que el productor no traduce a ese tipo y en formas ilegibles convertidas en vacío, no en una captura olvidada.

3. **Comparación del límite.** Comprobé 49, 50 y 51 registros. `>=` no deja pasar una respuesta mayor de lo solicitado; cambiarlo a `==` abriría esa vía. Bloquear exactamente el límite es conservador y justificado si no se conoce el total. La insuficiencia que impide dar por cerrado el remedio es H-05, no el operador de comparación.

4. **`alta_actuacion` completa y `desde`.** El destino se acredita antes de escribir y también al reanudar. `incierta`, recibos sin id y destino completo distinto se rechazan. La reanudación normal conserva el id y omite el POST de creación. Quedan H-02, H-03, H-06 y H-07. `paso` no gobierna la recuperación: incluso `verificada` vuelve a intentar el vínculo. No afirmo daño por repetir el mismo vínculo; su idempotencia real no se probó.

5. **Consumidores de `Dato.campo`.** El barrido de Python de todo el árbol encontró como consumidor de producción `scripts/crm_ficha_validar.py:110`, que imprime el campo; los otros accesos están en tests. No hay un parser de `contrario.campo` que pierda `contrario[i].campo`. Con dos partes, la sonda del CLI real imprime ambos índices y cuenta dos datos faltantes de la segunda; con una parte los tests confirman la clave anterior. **No encontré defectuoso este remedio.**

6. **Regex del asunto.** Espacios repetidos, tabulaciones, espacio no separable, minúsculas y sangrado ya detectan el prefijo contradictorio. El prefijo propio se normaliza. `SENIORIDAD - X` no se confunde con `SENIOR`. La normalización de `ſenior` y `senıor` tampoco elige otra tarifa: devuelve SENIOR. Persisten, igual que en base, prefijos repetidos (`SENIOR - SENIOR - X`), un prefijo contradictorio después de otro (`SENIOR - ABOGADO - X`), guiones unicode y espacio de ancho cero. Un asunto que empieza por `- X` queda `SENIOR - - X`, sin comerse su texto. No atribuyo a esos asuntos una tarifa efectiva del tenant ni convierto toda puntuación libre en un prefijo por inferencia. El remedio específico de espacios sí funciona; una garantía general de asunto único y canónico no quedó acreditada.

7. **Duración con zona.** Probé 16 combinaciones de ausencia de zona, `Z`, `+00:00` y `+02:00`: las siete con al menos un extremo sin zona levantan `ValueError`; las nueve con ambos extremos zonificados respetan los offsets. `Z` y `+00:00` son equivalentes. También pasan los tests de ausencia de cierre y extremos invertidos. El retorno temprano `None` sin ronda cerrada no representa una duración calculada y es el contrato previsto. **No encontré defectuoso el remedio.**

8. **Arnés y cobertura.** El 37/37 se reprodujo, con la salvedad material de H-08. M27–M38 apuntan a nodos existentes y, salvo M29, sus rojos detallados son compatibles con la propiedad declarada. M19 sigue cayendo antes del aserto de número de POST: el doble secuencial consume la respuesta de verificación como aprendizaje y después recibe un 201 sin id; devuelve `incierta`. Ese rojo no es una demostración limpia de duplicación persistida. Las sondas por rutas separan la propiedad de ese efecto de la cola. M09 protege diagnóstico, y varios mutantes cubren una misma frontera: el número no equivale a 37 garantías independientes. Falta un mutante del traslado de **toda** la validación fuera de la clasificación de efectos; no hay cobertura de mutación para recibos sin contexto, `incompleta` de paso 1, forma JSON inválida, total declarado mayor que la página, ni política de `sin_filas` en el orquestador. M15 solo cambia el estado del helper. M33 solo ataca `sin_comprobar`; M34 solo verifica el override de Subject directamente en el helper.

9. **Tests nuevos.** El id de la fila destino y la preparación separada de GET al reanudar corrigen los fallos de fixture descritos. El test de M29 es sensible a la decisión cuando se le da un mutante ejecutable. No encontré que el test nuevo de N contrarios pase por inspeccionar solo el primero. Sí hay pruebas demasiado estrechas: el caso de «catálogo no comprobado» admite cualquier estado distinto de verificada y por eso aprueba la `incompleta` irrecuperable de H-06; `_gets_ok` sigue preparando cero filas como camino normal de éxito; y el test de `extra` no atraviesa el orquestador. El test nuevo de zona no incluye inicio sin zona/fin con zona, pero esa dirección quedó comprobada por mis sondas. El fallo del CLI sin clave es preexistente y reproduce en base; no lo presento como defecto del diff.

10. **Lo que el diff afirma.** La tabla siguiente contrasta todas las filas efectivamente presentes en §7. El texto habla de quince hallazgos, pero la tabla contiene **13 categorías**, una explícitamente no remediada. No hay una correspondencia individual que permita reconstruir los quince, y falta el acta R2b citada. No invento dos filas ni doy por refutada cobertura que no pude consultar. La declaración del test pendiente es exacta; la afirmación general de cierre no lo es.

| Fila de §7 | Resultado de esta R3 |
|---|---|
| Parseo | Parcial: captura no-JSON; persiste pérdida de recibo por forma JSON, H-01 |
| Paginación | Parcial: guard de longitud correcto; exhaustividad no conservada, H-05 |
| Validador | Remedio comprobado, incluidos sus consumidores |
| Recibo incierto | Se impide recrearlo; la nueva respuesta del paso 1 contradice el contrato, H-06 |
| Recibo sin destino | Parcial: contexto vacío omite el guard, H-02 |
| Paso 1 con otro asunto | Consulta ya canónica; identidad de resultados aún no contrastada, H-04 |
| Cuatro salidas | Parcial: solo se distingue `sin_comprobar`, H-03 |
| Validación disfrazada | Corregido para firmante; persiste para el nuevo guard de `extra`, H-07 |
| Destino | Fila pedida y `wcode_match` comprobados; no encontré defectuoso el remedio de identidad |
| `extra` | Los tres campos reservados ya no se escriben; clasificación posterior incorrecta, H-07 |
| Zona horaria | Remedio comprobado en ambos extremos |
| Prefijo con espacios | Remedio específico comprobado; límites descritos arriba |
| Test que llama al CRM | Correctamente declarado pendiente y reproducido, H-09 |

## Lo que intenté refutar y NO pude

- **«Se olvidó un consumidor de `CuerpoIlegible`».** Enumeré llamadas e inyecté directamente el tipo en los tres caminos. Todos responden conforme al contrato. La refutación falla; H-01 tiene otra causa precisa.
- **«`>=` deja pasar más filas de las pedidas o vuelve a tapar un NIF único».** Ataqué 50 y 51 filas, y el camino con identidad fuerte única. El guard bloquea la creación potencialmente truncada y conserva la prioridad del NIF ya confirmado.
- **«El formato nuevo de campos rompe el informe».** Construí una ficha de dos personas con documental solo de la primera y ejecuté el CLI del validador. Ambos índices se imprimen, los datos ausentes del segundo entran en el resumen y el proceso termina en error. La compatibilidad singular también pasa.
- **«La zona explícita UTC se trata distinto de Z o solo se valida el final».** La matriz temporal cubre ambos sentidos y ambas representaciones UTC; no encontré diferencia indebida ni extremo sin zona que produzca un número.
- **«La acreditación del destino sigue usando la primera fila o el W-code truncado».** Los tests de la fila equivocada, el código más largo y la referencia secundaria pasan; al invertir esas decisiones en copias producen el rojo semántico esperado. La función de producción sí quedó remediada en esos puntos, aunque M29 esté mal construido.
- **«El recibo normal deja de reanudar al ganar destino».** Simulé fallo de vínculo y fallo de verificación; al reanudar en el mismo destino se reutiliza la actuación creada. El problema se limita a los estados y contextos descritos en H-02 y H-06.

## VEREDICTO

**No recomiendo mergear el diff remediado.** Hay avances comprobados, pero siguen abiertas las fronteras de parseo posterior a la escritura, identidad del recibo, conocimiento de la plantilla y exhaustividad del buzón. Además, el remedio introduce una `incompleta` que su propio consumidor bloquea, y el nuevo rechazo de `extra` vuelve a etiquetarse como efecto incierto. El verde de la suite y la salida 37/37 no contradicen esas reproducciones; uno de los mutantes está roto.

La revisión es la **R3 excepcional autorizada, tercera de tres**. Este informe entrega resultados para adjudicación; no solicita ni presupone una cuarta ronda. H-09 queda separado como deuda preexistente reconocida por el autor. Las afirmaciones no ejecutadas permanecen expresamente sin verificar.

NO-SHIP
<!-- informe-literal:fin:q7zx -->

## 2. Evidencia verificada por mí al adjudicar

Cada hallazgo se contrastó **contra la fuente**, no contra el informe ni contra la seguridad con
que viniera redactado. Cinco de los nueve se **reprodujeron ejecutando**, no leyendo:

| Hallazgo | Cómo lo verifiqué | Resultado |
|---|---|---|
| H-01 | `_items` con `{"items": 1}`, `{"hydra:member": true}`, `{"items": "texto"}`; `_values` con `values:[null]` | `TypeError` y `AttributeError` fuera del `try`; `"texto"` salía como `[]` en silencio — **confirmado** |
| H-02 | `alta_actuacion` con `Recibo("incompleta", act_id="AJENA", elemento="", exp_id="999")` | **escribió** `/api/relation_element/extrajudiciales/464` — confirmado |
| H-03 | Lectura de `aprender_id_predefinido` y de su único llamador | solo se distinguía `sin_comprobar`; el motivo de `no_aplica` afirmaba lo no visto — confirmado |
| H-04 | Lectura del filtro (`like`) y del bucle de aprendizaje | ninguna comprobación del `Subject` de la fila leída — confirmado |
| H-05 | `grep` de `totalItems` en `core/sudespacho_relations.py` y lectura de `Consulta` | la clave solo aparece en otra función; `Consulta` no tenía campo — confirmado |
| H-06 | Alta con el paso 1 en HTTP 500, y reanudación con el recibo resultante | cero escrituras y `ActuacionError` «concilia a mano» — confirmado |
| H-07 | Alta con `extra={"Subject": …}` | `incierta` paso 4, «puede haberse creado una actuación», **cero POST** — confirmado |
| H-08 | `grep _RE_WCODE core/sudespacho_actuaciones.py` + compilación del módulo mutado | el nombre no existe ni se importa: `NameError` en ejecución — confirmado |
| H-09 | Lectura del test y de `_completar_contrario_existente` | le faltaba el doble de la compleción; la excepción se absorbía — confirmado |

**No-mutación del objeto.** El revisor reportó `sha256` de apertura y cierre idénticos para los
tres módulos, y un manifiesto completo de 1.337/1.339 ficheros sin cambios. Sus digests son los
del árbol **en CRLF** (así lo extrae `git archive` en Windows) y por eso **no coinciden** con los
de `git show 53cc575:<fichero>`, que son LF. Se comprobó que ambos describen el mismo contenido
normalizando los finales de línea. Los dos números son correctos y prueban cosas distintas: el
suyo, que no tocó el objeto; el mío, que el objeto es el commit que digo.

**Lo que el revisor declaró SIN VERIFICAR y sigue sin verificar:** suite completa y sus dos
semillas, aceptación real de los payloads por el tenant, límites de paginación del servidor,
idempotencia del POST y del vínculo, y concurrencia. Eso **no** lo cubre otra ronda de lectura:
lo cubre correr la pieza contra el CRM real, que es lo que sustituye a la cuarta ronda.
