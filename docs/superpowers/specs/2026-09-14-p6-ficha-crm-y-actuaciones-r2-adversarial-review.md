---
tipo: revision-adversarial
objeto: core/sudespacho_actuaciones.py
objeto_rev: "1"
commit: 8aed442
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: w3x8
sha256_informe: 15f0932725af6a6014e6721fa0a48189b1ce47362b4ed34537a551cdf983fb10
adjudicado_en: docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md §7
---

# Acta — R2 adversarial sobre el DIFF de P6

Objeto: el diff `530d033..8aed442`. Ronda **2 de 2** del presupuesto autorizado; la R1 fue
sobre el diseño. **Nikolai autorizó una R3 expresamente** tras leer este resultado.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, `model_reasoning_effort=high` |
| Objeto | `C:/t/p6r2-obj-025857/{base,head}` |
| `sha256` del informe | `15f0932725af6a6014e6721fa0a48189b1ce47362b4ed34537a551cdf983fb10` — coincide con el que el revisor devolvió aparte |
| Veredicto | **NO-SHIP** |
| Hallazgos | 11 (8 `ALTO`, 3 `MEDIO`), **uno preexistente** — 11 confirmados, 0 refutados |
| Arnés | **26/26 confirmado por el revisor**, corriéndolo |

**Esta ronda corrió en paralelo con un segundo revisor** —un subagente despachado con la skill
`superpowers:requesting-code-review`—, que devolvió **NO-SHIP con 13 hallazgos**. Los dos son
lecturas independientes del mismo diff: coinciden en cinco y cada uno vio cosas que el otro no.
El informe del segundo está en el acta hermana `…-r2b-adversarial-review.md`.

**La frontera común, que es lo que se remedia:** *cada helper distingue estados que su único
llamador colapsa.* El paso 1 tiene cuatro salidas y `alta_actuacion` solo lee el valor; firmante
y operador son conceptos distintos y se pasa uno como el otro; validación y fallo de red van al
mismo `try`; y el payload se valida y luego se deja sobrescribir con `extra`.

**Lo que este revisor vio y el otro no**, y merece constar: `extra` sobrescribe `Subject`,
`profesional_asignado` e `id_predefinido` **después** de validarlos —eludiendo a la vez el
prefijo del firmante, que es la tarifa, la prohibición de id numérico y la evidencia del paso
1—; la regex de W-code **trunca** (`W-ABCDEF1` y `W-ABCDEF2` colapsan) habiendo un `wcode_match`
en el módulo hermano que el propio plan mandaba usar; y un test **preexistente** intenta
alcanzar el CRM real y pasa porque `_completar_contrario_existente` absorbe la excepción.

## 0. Mandato, literal

<!-- mandato-literal:inicio:w3x8 -->
# Mandato — revisión adversarial R2 del DIFF de P6

Eres el revisor adversarial. **Ronda 2 de 2.** La R1 fue sobre el diseño y devolvió NO-SHIP con
8 hallazgos, todos confirmados y remediados en la rev. 2 del spec. Esta ronda va sobre el
**código que implementa ese diseño**.

El presupuesto es de dos rondas porque una de las piezas **decide la identidad de una parte** y,
antes de este diff, escribía encima de la ficha de otro cliente.

## 0. Higiene del workdir

Tu directorio de trabajo (`-C`) contiene **solo este `MANDATO.md`** y lo que tú escribas. Si
encuentras otro fichero, **no lo leas** y decláralo en la primera línea del informe.

## 1. El objeto

Dos copias congeladas, en rutas absolutas (NO están dentro de tu workdir):

- `C:/t/p6r2-obj-025857/base/` — `origin/main` (`530d033`), antes del cambio.
- `C:/t/p6r2-obj-025857/head/` — el diff completo (`8aed442`).

**SOLO LECTURA sobre esas dos rutas.** Reporta el `sha256` **al abrir y al cerrar** de:

- `head/core/sudespacho_relations.py`
- `head/core/sudespacho_actuaciones.py`
- `head/core/crm_ficha.py`

No hay `.git`: la genealogía queda SIN VERIFICAR; acredita **contenido**.

**Documentos del diseño, en la misma copia** (léelos: el diff se juzga contra ellos):
`head/docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md` (rev. 2, y su §6
tiene la adjudicación de la R1) y `head/docs/superpowers/plans/2026-09-14-p6-ficha-crm-y-actuaciones.md`.

## 2. Puedes ejecutar, y debes

Python de sistema con `pytest`, `httpx`, `yaml`, `typer`, `filelock`, `dotenv`:

```
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

Copia `head/` a tu workdir y ejecuta **allí**. `--basetemp` **relativo** dentro de tu workdir.
Fija `PYTHONDONTWRITEBYTECODE=1`. **No hay credenciales del CRM y no debe haberlas:** ninguna
prueba puede llamar al tenant; si algo lo intenta, eso **es un hallazgo**.

Corre al menos:

- `tests/test_resolver_parte_aper71.py`, `tests/test_crm_ficha_n_contrarios.py`,
  `tests/test_sudespacho_actuaciones.py`, `tests/test_crm_ficha_cli.py`,
  `tests/test_sudespacho_relations.py`, `tests/test_crm_dedup_incertidumbre.py`
- **el arnés**: `python -m tests._mutantes_p6` (el autor declara **26 mutantes, 26 muertos**).

**Un revisor que no corre no refuta: deja SIN VERIFICAR.**

## 3. Qué hace el diff

Tres piezas. El diseño rev. 2 las detalla; en corto:

1. **`resolver_parte` reordenada** (`[APER-71]`). Un documento tiene **tres** estados
   (`_estado_documento`: ausente / utilizable / no interpretable). El **NIF único manda** sobre
   la multiplicidad del email. Sin match de NIF, `_resolver_por_buzon_compartido` contrasta cada
   ficha del buzón por su documento y **crear exige que todas queden descartadas**.
   `ResolucionParte` gana `motivo`.
2. **`crm_ficha` admite N contrarios** (`[APER-63]`), con `_contrarios_de` validando la
   colección **entera** antes de construir; `scripts/crm_ficha.py` los vincula todos. El DTO gana
   `firmante`.
3. **`core/sudespacho_actuaciones.py` nuevo** (`MEJORAS #209`): la receta de seis pasos, con
   `aprender_id_predefinido` de **cuatro** salidas, `resolver_destino` (paso 3), `asunto_canonico`
   sin defecto, `duracion_desde_ronda` y un **`Recibo` reanudable** de tres estados.

## 4. Dónde mirar con más ganas

1. **¿El código implementa la tabla del §2.2 del diseño, o una aproximación?** Construye sondas
   y recorre **todos** los estados: NIF ausente / utilizable / no interpretable × ficha del buzón
   con documento igual / distinto / ausente / no interpretable × una o varias fichas. ¿Queda
   algún estado sin caso, o alguno decidido de forma distinta a como el diseño dice?
2. **La reejecución (§2.3).** La R1 tumbó el primer remedio porque **creaba el estado que el
   código bloqueaba después**. ¿El nuevo orden lo resuelve de verdad? Simula: buzón con una
   ficha → crear la segunda → resolver las dos → añadir una tercera. ¿Converge? ¿Y con las
   consultas devolviendo los resultados en otro orden?
3. **`ResolucionParte()` vacía autoriza una CREACIÓN.** Busca todos los caminos que la devuelven
   y comprueba que cada uno tiene evidencia comparable detrás. Un solo camino que la devuelva por
   descarte es un duplicado en la ficha de un cliente.
4. **El `Recibo` y la recuperación.** ¿`alta_actuacion(desde=…)` puede crear una segunda
   actuación en algún camino? ¿Qué pasa si `desde` trae un `act_id` de **otro** expediente?
   ¿Y si el estado es `incierta` y alguien reanuda con él?
5. **`resolver_destino`.** ¿Se llama **siempre** antes de cualquier escritura, también al
   reanudar? ¿Qué pasa si la referencia esperada no tiene W-code, o si la leída trae varios?
   ¿Y con un elemento fuera de `_PROP_REFERENCIA`?
6. **`asunto_canonico`.** ¿Hay alguna entrada que elija un prefijo sin que nadie lo haya
   decidido? Mayúsculas, espacios, un prefijo en medio del texto, un firmante con espacios.
7. **`duracion_desde_ronda`.** Fechas con zona y sin ella, mezcladas, `terminada` presente pero
   vacía, una ronda de otro caso. ¿Alguna combinación devuelve un número que no signifique nada?
8. **El arnés (`tests/_mutantes_p6.py`).** Verifica el 26/26 corriéndolo. ¿Algún mutante está
   **mal apuntado** (muere por un test que no es el suyo)? ¿Alguno es trivial? ¿Falta mutante
   para alguna decisión del diff? Nota: en la R1 de P4 un mutante apuntado al fichero equivocado
   se declaró «superviviente» por la razón falsa.
9. **Los tests.** ¿Alguno pasa por la razón equivocada? El autor ya encontró uno así —su doble
   de HTTP consume las respuestas en orden y no contaba el GET del paso 1—. ¿Hay más de esa
   familia? ¿Algún test que no vería su propio defecto?
10. **Lo que el diff dice de sí mismo.** Los mensajes de commit y el runbook afirman cosas
    («cuadra exacto», «26 de 26», «sin regresión»). Comprueba lo que puedas y señala lo que no
    cuadre.

## 5. Formato del informe

Escribe **`INFORME.md`** en tu workdir:

```
# Informe R2 — diff de P6 (530d033 → 8aed442)

## Higiene y no-mutación
## Qué pude ejecutar y qué no
## Hallazgos
Por cada uno: **ID**, **severidad** (CRÍTICO/ALTO/MEDIO/BAJO), fichero:línea, qué está mal,
cómo se manifiesta con entradas concretas, cómo lo comprobaste, y **de qué frontera es un
ejemplo**.
## Lo que revisé y NO encontré defectuoso
## VEREDICTO
```

**La última línea debe ser el veredicto, exactamente una de estas tres palabras y nada más:**

```
SHIP
SHIP-CON-CAMBIOS
NO-SHIP
```

## 6. Recordatorios

- Ante cada hallazgo, escribe **de qué frontera es un ejemplo**. El autor remedia la frontera.
- No propongas rediseñar el alcance: está decidido.
- Si algo te parece correcto pero no puedes probarlo, **SIN VERIFICAR**. Nunca «refutado».
<!-- mandato-literal:fin:w3x8 -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:w3x8 -->
Higiene: al iniciar había `_stdout.log` además de `MANDATO.md`; no leí su contenido.

# Informe R2 — diff de P6 (530d033 → 8aed442)

## Higiene y no-mutación

Revisión de contenido, realizada el 2026-09-14. **Genealogía SIN VERIFICAR**: las copias no tienen `.git`; los identificadores del título son los del mandato, no commits acreditados por este revisor. No consulté el remoto ni el tenant. No hubo delegación. Claude adjudica contra la fuente; este informe no sustituye esa adjudicación.

Las entradas fueron `C:/t/p6r2-obj-025857/base/` y `C:/t/p6r2-obj-025857/head/`, siempre en solo lectura. Copié `head` a este workdir para ejecutar; las comprobaciones adicionales usaron también `audit-head/` y `base/`, copias locales. Solo esas copias y los artefactos de revisión recibieron escrituras. No hubo `git add`, commits ni modificaciones del repositorio original.

SHA-256 de los tres ficheros exigidos, calculado antes de leerlos y nuevamente al cerrar:

| Fichero bajo `head/` congelado | Apertura | Cierre |
|---|---|---|
| `core/sudespacho_relations.py` | `a60158e4b45f49a2446669813d7bf0245d9854b2be82f599058210779dcb5738` | `a60158e4b45f49a2446669813d7bf0245d9854b2be82f599058210779dcb5738` |
| `core/sudespacho_actuaciones.py` | `a6032ed520629a0ffb4262b100c1350006456097a216ac27bb123a838df6bdf4` | `a6032ed520629a0ffb4262b100c1350006456097a216ac27bb123a838df6bdf4` |
| `core/crm_ficha.py` | `d242c187a9665a0094c2a8e71a4a3f9d27c4e294518096982bff1f715b56433b` | `d242c187a9665a0094c2a8e71a4a3f9d27c4e294518096982bff1f715b56433b` |

Además comparé los manifiestos completos de apertura/cierre: **1.329 ficheros en base y 1.337 en head; cero cambios de contenido, altas o bajas**. Evidencia: `manifest_open.json`, `manifest_close.json`. El diff por contenido está en `diff.txt`: 14 rutas diferentes, incluidas documentación y pruebas. Los originales permanecen intactos aunque el arnés normalice saltos de línea al restaurar las copias de ejecución.

## Qué pude ejecutar y qué no

Leí el diseño rev. 2 completo, su adjudicación R1 (§6), el plan completo, los módulos modificados y sus consumidores, las pruebas exigidas y el arnés. Contrasté también la receta de `INTEGRACION_SUDESPACHO.md` §15.6 y el catálogo de `MANUAL_DESPACHO.md`, ambos locales.

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`. En todas las ejecuciones fijé `PYTHONDONTWRITEBYTECODE=1`; pytest no escribió caché y recibió `--basetemp` relativo bajo este workdir. Desactivé dotenv y retiré la clave CRM del entorno del proceso. Los valores ficticios que algunos tests fijan y el plugin de diagnóstico `synthetic_key` **no son credenciales**.

`guard/sitecustomize.py` bloqueó la resolución de nombres y las conexiones mediante auditoría de Python. Conservó el intento y posteriormente su pila/nodo de pytest. Ningún intento registrado llegó a DNS ni a una conexión con el tenant. La primera variante lanzaba `RuntimeError`; para comprobar si el código absorbía el bloqueo repetí el caso identificado con una excepción derivada directamente de `BaseException` (H-11).

| Ejecución | Resultado y evidencia |
|---|---|
| Los seis ficheros exigidos, sin plugin de clave ficticia | 220 casos ejecutados: **219 pasan, 1 falla**, `pytest-required.log`. El fallo es `test_crm_ficha_cli.py::TestLaGuardaDeRedMuerde::test_una_salida_no_declarada_MATA_el_test`. |
| Ese fallo del CLI sobre la copia de base | También falla: `base-guard.log`. Con el plugin que aporta un valor ficticio pasa: `base-guard-synthetic.log`. No es regresión de P6. |
| Seis ficheros exigidos más todos los `test_crm_ficha*.py`, con plugin ficticio | **354 pasan**, `pytest-expanded.log`. Este verde no acredita aislamiento de red: H-11. |
| Repetición diagnóstica de los seis con el mismo plugin | **220 pasan**, `pytest-network2.log`; identifica el intento de red absorbido. |
| Test que intenta red, con bloqueo no absorbible y sin plugin ficticio global | **Falla tanto en head como en base**, `strict-head.log`, `strict-base.log`. El propio test fija su clave ficticia. |
| `python -m tests._mutantes_p6`, original, sobre copia local | **26 mutantes, 26 muertos; salida 0**, `mutantes-final.log`. |
| Auditoría adicional del arnés | 26 sustituciones únicas y 26 mutantes sintácticamente válidos; reproducción detallada de M19; mutante de sintaxis experimental correctamente rechazado como arnés roto. `audit-mutants-results.json`. |
| Sondas propias | `probes_r2.py`, `supplemental.py`, `more_probes.py`; resultados en los JSON homónimos indicados abajo. Matriz de **765 combinaciones, cero diferencias** respecto de la política esperada cuando llega el conjunto completo. |

Comando esencial de la primera suite, desde la copia `head/`:

```text
python -m pytest tests/test_resolver_parte_aper71.py tests/test_crm_ficha_n_contrarios.py tests/test_sudespacho_actuaciones.py tests/test_crm_ficha_cli.py tests/test_sudespacho_relations.py tests/test_crm_dedup_incertidumbre.py -q --tb=short -p no:randomly
```

Se añadió por entorno `PYTEST_ADDOPTS="--basetemp=../tmp-tests -p no:cacheprovider"` y `PYTHONPATH` al directorio `guard`. El arnés recibió igualmente un basetemp relativo, `../tmp-mutantes`, heredado por sus subprocesos. Los scripts propios se ejecutan desde este workdir con el mismo intérprete y guard.

Dos primeros intentos del arnés fallaron por `PermissionError` al escribir la copia cuando el lanzador se configuraba con `workdir=head`; no los contabilicé como mutantes muertos. Verifiqué escritura/restauración de los mismos bytes y ejecuté desde el workdir autorizado, cambiando después a `head` dentro de PowerShell. La ejecución original completa entonces terminó. Los fallos se conservan en `mutantes.log` y `mutantes-retry.log`. No se modificó el arnés para obtener el 26/26.

**SIN VERIFICAR:** suite completa de aproximadamente 5.500 casos, cierre con semillas 777/31337, historial y mensajes reales de commit, propiedad de sesiones/ramas/PR, aceptación actual de payloads por el tenant, almacenamiento real de documentos, idempotencia real del POST y concurrencia. Las sondas HTTP acreditan decisiones del código frente a entradas concretas; no convierten los dobles en evidencia de comportamiento del servidor.

## Hallazgos

Las referencias `fichero:línea` corresponden a la copia congelada **head**, salvo indicación expresa. El coste es una estimación del remedio, no autorización para ampliar el alcance. H-01 a H-10 afectan al código de P6; H-11 es preexistente y se incluye porque el mandato exige declarar cualquier prueba que intente alcanzar el tenant.

### H-01 — ALTO — Se decide «todas descartadas» sobre una sola página

**Fichero:** `core/sudespacho_relations.py:1218`, `:1258`, `:1297`; dependencia `:1090`, `:1129`, `:1145`. **Coste: acotado.**

La consulta por email conserva el límite de **5** registros. `_buscar_registros` descarta `totalItems` y no pagina; la nueva tabla interpreta esos cinco como el buzón completo. Con cinco fichas de documentos distintos y una sexta sin documento, NIF entrante `NEW1`, devuelve `ResolucionParte()` vacía y autoriza crear. No ha descartado la sexta, que podría ser la persona buscada.

**Comprobación:** sonda `pagination` de `probes-results.json`, usando `_buscar_registros` real y HTTP simulado que respeta `itemsPerPage=5`, declara seis resultados y solo entrega la primera página. Se hicieron dos GET en total, ninguno por la segunda página. `more-probes-results.json/base_comparison` demuestra que **base bloquea por multiplicidad y head autoriza crear** ante la misma primera página. Es una regresión aunque el límite del transporte sea anterior.

**Frontera:** una prueba universal sobre candidatos exige acreditar la exhaustividad del conjunto. Recibir una página no acredita haber descartado todas las identidades. El remedio debe conservar esa información hasta decidir, mediante recorrido completo o bloqueo explícito ante truncamiento; aumentar un límite no demuestra exhaustividad. Incumple diseño §2.2.

### H-02 — ALTO — Reanudar un recibo incierto crea otra actuación

**Fichero:** `core/sudespacho_actuaciones.py:476`. **Coste: acotado.**

`alta_actuacion` ignora `desde.estado` y `desde.paso`; solo comprueba si hay `act_id`. El recibo que ella misma produce tras un timeout es `Recibo("incierta", act_id=None, paso=4)`. Pasarlo como `desde` vuelve a entrar en el POST de creación.

**Comprobación:** `probes-results.json/uncertain_resume`. El doble guarda `N1` y pierde su respuesta, simulando commit seguido de timeout. La primera llamada devuelve `incierta`; la segunda, con ese recibo, crea **N2** y devuelve `verificada`. El censo contiene las dos actuaciones y solo N2 queda vinculada. No se construyó manualmente un recibo imposible.

**Frontera:** los estados de recuperación deben gobernar las transiciones permitidas, no limitarse a describirlas en un docstring. La entrada incierta debe impedir repetir una operación cuyo efecto se desconoce. Incumple §4.2 y reproduce la clase de daño de R1/H-04.

### H-03 — ALTO — El recibo no acredita a qué expediente pertenece su actuación

**Fichero:** `core/sudespacho_actuaciones.py:375`, `:474`, `:476`, `:491`. **Coste: estructural** — afecta al contexto que transporta el recibo.

El recibo solo contiene estado, id, paso y motivo. Una reanudación puede reutilizar una actuación creada para A y vincularla a B. `resolver_destino` comprueba que B es B, pero no que el recibo corresponda a B; el paso 6 confirma precisamente el vínculo que se acaba de escribir en el destino erróneo.

**Comprobación:** `probes-results.json/foreign_receipt`. Alta para `extrajudiciales/464`, referencia `W-02VEKE`: crea N1 y falla el vínculo. Reanudar el recibo con `extrajudiciales/999`, referencia correcta de ese otro caso `W-0XXXXX`, escribe `right.actuaciones.N1` en 999 y devuelve `verificada`. No crea otra actuación, pero atribuye la existente al caso incorrecto.

**Frontera:** acreditar por separado la dirección de llegada y la existencia de un id no acredita que ambos pertenezcan a la misma operación. La recuperación necesita conservar y contrastar el contexto de la operación original antes de escribir. Es la misma distinción entre llegada e intención de §4.1, aplicada a §4.2.

### H-04 — ALTO — Un error de parseo en el paso 6 pierde el recibo después de escribir

**Fichero:** `core/sudespacho_actuaciones.py:457`, `:498`. **Coste: acotado.**

El `try` de `verificar_actuacion_vinculada` solo protege el GET. Si la respuesta es HTTP 200 pero `json()` falla, el error sale por `_items` y atraviesa `alta_actuacion`: no se devuelve `Recibo("incompleta", act_id=...)` aunque la creación y el vínculo ya se hayan realizado.

**Comprobación:** `supplemental-results.json/receipt_lost`: GET destino, GET aprendizaje, POST creación con id N, POST vínculo, GET verificación cuyo `json()` levanta `ValueError`. El resultado es una excepción sin recibo. La traza acredita los dos POST anteriores. El llamador pierde la vía prevista para reanudar y una repetición del alta puede duplicar N.

**Frontera:** conservar evidencia de efectos parciales debe cubrir todos los fallos posteriores a la escritura, incluidos decodificación y forma de la respuesta; cubrir solo errores de transporte no cierra el contrato de recuperación. Incumple §4.2.

### H-05 — ALTO — Las cuatro salidas del aprendizaje se colapsan antes de escribir

**Fichero:** `core/sudespacho_actuaciones.py:167`, `:173`, `:478`, `:483`. **Coste: acotado.**

`alta_actuacion` utiliza `pre.valor` e ignora `pre.estado`. `sin_comprobar`, `sin_filas` y `no_aplica` llegan al POST exactamente igual: se omite `id_predefinido`. Un fallo de consulta puede acabar en `verificada`, sin conservar siquiera el motivo de incertidumbre. Además, el helper clasifica un campo presente no convertible, por ejemplo `"garbage"`, como `no_aplica` y afirma falsamente que las filas lo traían vacío.

**Comprobación:** `probes-results.json/learning_states`: HTTP 500, cero filas, campo inválido y campo vacío producen todos creación sin `id_predefinido` y recibo `verificada`; un id 84 sí se transmite. Las pruebas del autor distinguen los estados al llamar al helper, pero los dobles de los caminos completos proporcionan por defecto cero filas y esperan éxito.

**Frontera:** una distinción de conocimiento solo protege si el consumidor la conserva en su decisión. «No pude aprender» no permite ejecutar como si se hubiera aprendido «no aplica»; un dato presente inválido tampoco equivale a campo vacío. Contradice las cuatro salidas de §4 y la receta de pasos obligatorios.

### H-06 — ALTO — Se aprende la plantilla de un asunto distinto del que se crea

**Fichero:** `core/sudespacho_actuaciones.py:150`, `:166`, `:170`, `:478`, `:481`. **Coste: acotado.**

El aprendizaje usa `asunto` antes de añadir el prefijo decidido por `firmante`; el POST usa después `asunto_canonico`. Con la entrada admitida `EXTRAJUDICIAL - REVISION VIABILIDAD`, la consulta `like` puede devolver actuaciones de ABOGADO y SENIOR. Se toma el primer entero encontrado sin comprobar igualdad de `Subject` ni concordancia entre filas. Por tanto el id escogido depende del orden y puede proceder de otra plantilla.

**Comprobación:** `probes-results.json/template_order`. Dos filas sintéticas, ABOGADO con id 77 y SENIOR con id 103: con `firmante="Nikolai_Tyukhay"`, el POST tiene siempre `Subject="SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD"`, pero recibe id **77 o 103 según el orden**. Esos ids son exclusivamente datos del doble, no ids afirmados del tenant. La traza conserva el filtro sin prefijo.

**Frontera:** la evidencia usada para aprender una configuración debe corresponder a la misma identidad de operación que se ejecutará. Normalizar después de consultar cambia esa identidad. La receta local §15.6 advierte expresamente que una variante histórica puede usar otro id y exige el asunto literal.

### H-07 — ALTO — El contraste del destino acepta códigos diferentes o una coincidencia secundaria

**Fichero:** `core/sudespacho_actuaciones.py:59`, `:255`, `:257`. **Coste: acotado.**

La regex nueva captura solo 5–6 caracteres y carece de fronteras de palabra. `W-ABCDEF1` y `W-ABCDEF2` se reducen ambos a `W-ABCDEF` y acreditan el mismo destino. El helper existente `wcode_match`, indicado por el plan, admite 5–8 caracteres con fronteras y devuelve falso para ese par. Además, la nueva intersección admite una referencia leída `W-0XXXXX (relacionado W-02VEKE)` para la esperada `W-02VEKE`, aunque el código principal sea otro.

**Comprobación:** `more-probes-results.json/wcodes`: para ambos ejemplos `resolver_destino` acepta y `wcode_match` devuelve falso. `probes-results.json/destinations` contiene también el caso de prefijo `W-02VEKE` frente a `W-02VEKE9`.

**Frontera:** identidad exacta y unívoca no es pertenencia a un conjunto de subcadenas. La normalización no debe truncar códigos ni convertir una referencia con varios candidatos en acreditación automática. Afecta al guard previo a cualquier escritura del §4.1.

### H-08 — ALTO — `extra` sobrescribe las decisiones que se acaban de validar

**Fichero:** `core/sudespacho_actuaciones.py:406`, consumidor `:485`. **Coste: acotado.**

Después de construir y validar el payload, `cuerpo.update(extra or {})` permite sustituir `Subject`, `profesional_asignado`, `id_predefinido` y los demás campos controlados. El orquestador transmite `extra` sin restringirlo y el paso 6 solo verifica pertenencia del id, no estos valores.

**Comprobación:** `probes-results.json/extra_override`: con firmante Nikolai y aprendizaje «no aplica», `extra={"Subject":"ABOGADO - X", "profesional_asignado":"8", "id_predefinido":999}` produce exactamente ese POST y termina `verificada`. Se eluden simultáneamente el prefijo del firmante, la prohibición de id numérico de empleado y la evidencia del paso 1.

**Frontera:** la validación debe aplicarse al objeto final que cruza la frontera de escritura. Una extensión posterior no puede reemplazar silenciosamente los campos que materializan decisiones ya verificadas. El remedio puede reservar esos campos o validar su coherencia después de combinar; no requiere retirar los extras legítimos como la fecha de vencimiento.

### H-09 — MEDIO — La duración acepta dos fechas sin zona

**Fichero:** `core/sudespacho_actuaciones.py:314`, `:345`. **Coste: acotado.**

`datetime.fromisoformat` admite fechas sin zona. Si ambas carecen de ella, la resta devuelve un número en vez de rechazarlas como exige el **diseño rev. 2 §4.4**. Mezclar una fecha con zona y otra sin ella provoca un `TypeError` de Python, no el error de dato legible previsto. El plan de la tarea 8 no repite la exigencia de zona; eso no elimina el requisito del spec al que se subordina.

**Comprobación:** `probes-results.json/durations`: `2026-09-14T10:00:00` → `2026-09-14T10:01:30` devuelve **90**. Con inicio terminado en `Z` y fin sin zona levanta `TypeError`. Dos instantes con offsets distintos correctamente equivalentes devuelven 90; los extremos invertidos sí se rechazan.

**Frontera:** poder restar representaciones temporales no acredita una duración entre instantes. La condición de zona debe validarse en ambos extremos antes de la operación.

### H-10 — MEDIO — Variar los espacios evita la detección del prefijo contradictorio

**Fichero:** `core/sudespacho_actuaciones.py:300`. **Coste: acotado.**

La detección del prefijo exige exactamente `"ABOGADO - "` o `"SENIOR - "`. Con `base="ABOGADO  -  X"` y firmante Nikolai no detecta el prefijo contrario: devuelve `"SENIOR - ABOGADO  -  X"`. La discrepancia que el docstring y el runbook dicen remitir a una persona se convierte en un asunto doble.

**Comprobación:** `probes-results.json/subjects`. La variante minúscula con espacios normales sí se rechaza; la de espacios duplicados no. Los espacios envolventes del firmante se eliminan correctamente. Un prefijo en medio del texto no se interpreta como prefijo inicial; no considero eso por sí solo un defecto.

**Frontera:** el reconocimiento de un valor estructurado debe decidir qué hacer con variantes de formato antes de aplicar una política. Aceptar como texto libre una variante reconocible de un prefijo contradictorio evita la revisión humana exigida. No afirmo que el tenant facture automáticamente una tarifa concreta por ese asunto mal formado: ese efecto está SIN VERIFICAR.

### H-11 — MEDIO — Una prueba exigida intenta alcanzar el CRM y pasa cuando se absorbe el bloqueo

**Fichero:** `tests/test_sudespacho_relations.py:1570`, `:1583`; camino `core/sudespacho_relations.py:1624`, `:1659`, `:1702`. **Coste: acotado. Preexistente, reproducido en base.**

`test_ensure_contrario_vinculado_existente` dobla resolución, creación y vínculo, pero no `_completar_contrario_existente` ni su GET. El propio test fija `SUDESPACHO_API_KEY="test-api-key"`. Al obtener la identidad simulada 1099, intenta leer esa ficha del tenant. `_completar_contrario_existente` absorbe `Exception`, por lo que un error de red o el `RuntimeError` de la barrera dejan el test verde.

**Comprobación:** `guard/network_attempts.log` identifica el nodo exacto y la pila hasta `socket.getaddrinfo('api-crm-commons-pro.sudespacho.biz',443,...)`, interceptado antes de ejecutarse. Con la barrera no absorbible, el test falla en **ambas copias**, sin plugin global de clave ficticia: `strict-head.log` y `strict-base.log`. No hubo petición real al CRM.

**Frontera:** un test de efectos externos debe cerrar todas las rutas de transporte y el fallo de aislamiento no puede convertirse en tolerancia operativa. Un verde obtenido porque una lectura real falló no verifica el comportamiento pretendido. No lo atribuyo al diff ni lo uso para fabricar una regresión, pero impide describir la suite exigida como plenamente aislada.

## Lo que revisé y NO encontré defectuoso

Respuesta punto por punto al apartado 4 del mandato, con los límites de cada comprobación:

1. **Tabla de identidad.** Construí 765 casos: los tres elementos de parte, los tres estados del documento entrante y buzones de 0, 1, 2 o 3 fichas, con todas las combinaciones ordenadas de documento igual/distinto/ausente/no interpretable. Para el NIF utilizable forcé ausencia de match NIF, ejercitando realmente §2.2; el documento igual se representó como `X-1` frente a `X1`. Cero diferencias de decisión. `motivo` en vez de rellenar `ambiguo` es coherente con el plan: bloquea por `resuelta` y por `_exigir_identidad_cierta`. La tabla local es correcta; H-01 está en la exhaustividad de su entrada.

2. **Reejecución.** Secuencia A existente → autorizar B → registrar B → resolver A/B → autorizar C → registrar C → resolver A/B/C, repetida con resultados en orden normal e inverso: converge. La sonda adicional entra por `ensure_contrario_vinculado`, crea B, falla su vínculo, reintenta y reutiliza B: una creación, dos intentos de vínculo, ninguna compleción sobre A (`more-probes-results.json/partial_identity`). El corte no invalida la identidad ya creada.

3. **Todos los retornos vacíos.** Hay dos sitios: línea 1310 tras descartar las filas del buzón y línea 1266 tras quedar sin ids. El primero es correcto con conjunto exhaustivo y falla por H-01. El segundo cubre las consultas exitosas sin coincidencias y también **ambos criterios ausentes, sin hacer consulta alguna**. Comprobé este último en base y head: ambos devuelven resolución vacía, con cero consultas. No lo presento como regresión nueva ni invento una política de alta sin datos: la tarea 2 del plan conserva expresamente ese retorno y §2.1 conserva la política sin NIF. Sí queda señalada la incompatibilidad de ese camino con la afirmación absoluta «solo con evidencia comparable»; **la inexistencia de la persona está SIN VERIFICAR en ese camino**. Una fila sin id también puede desaparecer al construir `Consulta.ids`; no se acreditó aquí robustez general frente a respuestas malformadas del transporte heredado.

4. **Recibo.** Los fallos normales de vínculo conservan el id y la reanudación del mismo caso lo reutiliza; el arnés mata M18 y M19. El recibo no cierra la frontera completa: H-02, H-03 y H-04. Un `desde` con id, incluso `verificada`, vuelve a ejecutar el vínculo porque `paso` no se consulta. No afirmo que ese mismo vínculo duplicado cause daño en el tenant: su idempotencia real no fue probada en esta revisión.

5. **Destino antes de escribir.** En `alta_actuacion` se llama siempre primero, incluso al reanudar. Mis sondas con recibos `incompleta` y `verificada` y referencia discrepante producen exclusivamente GET y levantan. Referencia esperada sin W-code, aunque coincida textualmente, se rechaza. Elemento fuera de `_PROP_REFERENCIA` se rechaza antes incluso del GET. Las dos properties, con su capitalización diferente, están conservadas. La acreditación defectuosa de H-07 es posterior a esas guardas. Las primitivas públicas `crear_actuacion`/`vincular_actuacion` no ejecutan el paso 3 por sí solas: la secuencia completa la garantiza el orquestador, tal como separa funciones el diseño.

6. **Asunto y firmante.** Sin firmante o con uno desconocido, `asunto_canonico` levanta; no hay fallback de usuario. El DTO lee el campo sin inferirlo del operador. Un prefijo contrario con formato normal se rechaza incluso en minúsculas; un firmante con espacios envolventes se reconoce. Detecté H-08 y H-10. El orquestador captura también errores de validación anteriores al POST y los etiqueta `incierta`; no se debe interpretar ese mensaje como prueba de que se intentó escribir.

7. **Duración.** Lee el fichero correcto mediante `apertura_v1_estado.leer`; ausencia de ronda, `terminada=None` y `terminada=""` devuelven `None`. Con zonas válidas, respeta los offsets; fecha ilegible e inversión se rechazan. Dos fechas sin zona incumplen §4.4 (H-09). `RondaV1` no porta identidad del caso: un marcador copiado de otra carpeta se acepta. La sonda usa `ronda_id="OTRO-CASO"` y aun así calcula. **La procedencia del marcador está SIN VERIFICAR**; el helper mide el fichero que se le entrega, no acredita a qué caso perteneció la ronda. No propongo aquí ampliar el formato histórico, fuera del contrato concreto de duración.

8. **Arnés.** El **26/26 está reproducido**, no asumido. Todos los textos originales aparecen una sola vez en su fichero y las 26 sustituciones producen Python válido. Los nodos existen y pasan antes de la mutación en la ejecución original. No encontré un mutante actual apuntado a otro fichero ni uno muerto simplemente por error sintáctico. Inyecté un mutante experimental de sintaxis: pytest devolvió 4 y el arnés lo declaró roto, sin contarlo muerto. No se debe extrapolar eso a cualquier código de error imaginable; solo se ejecutó ese caso.

   M19 merece precisión: en mi repetición con traceback completo muere en `test_sudespacho_actuaciones.py:205`, porque recibe `incierta` en vez de `verificada`, **antes del aserto que cuenta POST**. El mutante hace un GET extra, consume la respuesta de verificación como aprendizaje y utiliza como creación la respuesta prevista para el vínculo, que carece de id. Está bien apuntado y mata una reanudación incorrecta, pero ese rojo concreto tiene interferencia del doble secuencial; no acredita por sí solo una segunda creación persistida. Mi doble por rutas y con estado reproduce separadamente la duplicación real de H-02.

   M09 solo protege la veracidad del diagnóstico; no es evidencia adicional de identidad. M01/M02 ejercitan puntos distintos de una misma frontera y el 26 no debe leerse como 26 propiedades independientes. **Falta el mutante mínimo expresamente pedido por el plan**: sustituir el `continue` de descarte por retorno vacío inmediato. M06 salta otra rama y no lo sustituye. Tampoco hay mutantes para exhaustividad paginada, prohibición de reanudar `incierta`, contexto del recibo, parseo después de escribir, consumo de `pre.estado`, aprendizaje del asunto final, overrides de `extra`, zona temporal o las variantes de referencia detectadas. El arnés acredita las decisiones que ataca; no cubre todo el diff.

9. **Pruebas.** La guarda de red del CLI sí corta los verbos que prueba, pero su test de escenario completo presupone una clave ambiental: sin ella `_get_api_key` falla antes de alcanzar HTTP. De ahí el rojo heredado inicial. H-11 es otra prueba que pasa por una razón ajena a su contrato. Los dobles de actuaciones no verifican parámetros ni payloads y suministran respuestas de éxito por defecto cuando se agota la cola, lo que limita cuánto prueban sobre la gramática HTTP y explica huecos como H-05/H-06/H-08.

   `test_crm_ficha_n_contrarios.py:74` afirma «no se construye el primero», pero solo comprueba que se levanta `ValueError`. Instrumenté `_contrario_de`: ante `[{'nombre':'FIRST'}, {'sin_nombre':'x'}]` **sí construye el primero** y falla al construir el segundo. Ese test no prueba su docstring. No lo elevo a corrupción de ficha: los DTO no escriben y `cargar_ficha_yaml` no devuelve una ficha parcial. Para un elemento que no es mapping, comprobé que la validación de tipos sí aborta antes de construir ninguno.

   Para N contrarios, el CLI recorre la lista completa, conserva orden, acumula todos los ids esperados y los enumera en dry-run. M11–M13 y las pruebas ampliadas verifican los caminos correspondientes. No encontré una regresión de producción en esta pieza. Los consumidores encontrados de `FichaCRMInput` construyen el DTO desde el cargador; la propiedad singular preserva las lecturas existentes. No se acredita compatibilidad de constructores externos que usaran el antiguo argumento `contrario=`.

10. **Afirmaciones del diff.** `PLAN.md` fila 33 dice 26/26: **confirmado**. Conserva «pendiente de R2 y de mergear», no afirma una R2 aprobada. Los bloques del runbook sobre N contrarios están sustentados; «TODAS descartadas» de `RUNBOOK_APERTURA_EXPEDIENTE.md:1085` no lo está sin atender a paginación. Las cuatro salidas existen como DTO pero no gobiernan el alta, y el recibo anunciado en `:1017` solo protege algunos fallos. `MEJORAS_FUTURAS.md` no cambió: #209 todavía describe que no hay helper, pese a que la tarea 10 pedía actualizarlo; es una deuda documental de cierre, sin convertirla en defecto de identidad. **Los mensajes de commit y la afirmación global «sin regresión» quedan SIN VERIFICAR** desde una exportación sin historia y sin ejecutar la suite completa; además H-01 acredita una regresión concreta. No atribuyo al autor una frase «cuadra exacto» que no pude localizar como afirmación del cambio revisado.

## VEREDICTO

**No recomiendo mergear este contenido.** El 26/26 es cierto y la tabla de identidad funciona sobre conjuntos completos, pero P6 autoriza una creación con candidatos sin examinar, permite repetir un alta incierta, reutiliza recibos fuera de su expediente y pierde el id ante ciertos fallos posteriores a la escritura. También escribe pese a no haber aprendido la plantilla y permite invalidar decisiones ya comprobadas. Son defectos reproducidos del código, no dudas sobre aceptación del tenant.

La ronda es **2 de 2**. Este informe entrega las fronteras para adjudicación y remedio; no solicita ni presupone una tercera ronda. Las incertidumbres y los defectos preexistentes están separados de las regresiones. Evidencias reproducibles y trazas quedan junto a este fichero, fuera de las copias congeladas.

NO-SHIP
<!-- informe-literal:fin:w3x8 -->

## 2. Evidencia verificada por mí

- `sha256` del bloque canonicalizado: `15f0932725af6a6014e6721fa0a48189b1ce47362b4ed34537a551cdf983fb10`, idéntico al que el revisor devolvió por separado
  y al del fichero crudo. Esperé la señal real de fin (`_ultimo_mensaje.txt`).
- **El arnés lo corrió él**, que es lo que el otro revisor declaró no poder hacer: 26/26.
- Los once hallazgos se adjudican en el §7 del diseño, contra el código.
