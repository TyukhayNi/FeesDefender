---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md
objeto_rev: "1"
commit: 3d72cd8
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: v2r1
sha256_informe: 2cc864cd29c1fa265e97994010b61c69895eacf4c9a398f7636e238df3b131e9
adjudicado_en: docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md §8
---

# Acta — R1 adversarial sobre el PLAN de V2 (el lazo del CRM)

Objeto: el **plan**, antes de la primera línea de código, con el árbol `3d72cd8` disponible para
que el revisor verificara contra la fuente todo lo que el plan afirma.

## 1. Informe recibido de Codex, sin modificar

El mandato y el informe van literales más abajo, entre marcadores con nonce `v2r1`. Ni una palabra
tocada: siendo yo la parte revisada, sin el original nadie puede contrastar **qué dijo el revisor**
con **qué decidí yo que dijo**.

## 2. Evidencia verificada por mí

| Qué | Resultado |
|---|---|
| `sha256` del informe | `2cc864cd29c1fa265e97994010b61c69895eacf4c9a398f7636e238df3b131e9` — recomputado por mí, coincide con el que devolvió el revisor |
| No mutación | los `sha256` del plan y de `scripts/abrir_caso.py` son idénticos al abrir y al cerrar |
| Ejecución del revisor | **309 tests pasados, 1 omitido**, más nueve sondas con transporte sustituido. Sin escrituras reales en el CRM |
| H-02 (`_alta_crm`) | **CONFIRMADO** por mí: la firma real es `(ident, *, cuantia, crm_mode, yes, force=False)`; el plan la llamaba `(ident, case_dir)` |
| H-06 (`verificar`) | **CONFIRMADO**: `verificar(case_dir, fuentes=None) -> Informe` ya existía en `core/verificar_apertura.py:1134`. El plan proponía crear un agregador que ya estaba |
| H-04 (`typer.Exit`) | **CONFIRMADO**: `Exit -> RuntimeError -> Exception`, luego `except Exception` **sí** lo captura. La nota del plan afirmaba lo contrario |
| H-08 (segundo POST) | **CONFIRMADO**: `create_expediente` tiene fallback legacy; el revisor lo recorrió con transporte sustituido y vio dos POST |
| Veredicto adjudicado | **8 confirmados, 0 refutados** |

**Las tres fronteras, que es la lectura que importa:**

**A. Escribí el plan contra firmas que no verifiqué una por una** (H-02, H-03, H-04, H-06). Lo
agudo es H-03: **transcribí la firma correcta de `alta_actuacion` en el bloque «Interfaces» y dos
párrafos después escribí una llamada incompatible** (`case_id=`, que no existe). Es el mismo patrón
que la R1 de P8 destapó — escribir la verdad en un sitio del documento y no aplicarla en otro del
mismo documento.

**B. Confundí exclusión nominal con exclusión material** (H-05, H-07). El plan decía «la §8.1 no
entra» y el comando que invoca **crea y actualiza contrarios**, que son sus efectos materiales.
Y decía «sala de lectura y viabilidad no entran», pero `verificar` las comprueba y su `fallo`
dejaría V2 en `bloqueado` por artefactos de una fase ajena. **Excluir una etapa del listado no
excluye sus efectos.**

**C. Capturar una excepción no es recuperación** (H-01, H-08). Traducir la excepción a `fallo` no
conserva la autorización de escritura —el default de `--crm` sigue siendo `api` y la secuencia no
recibe ese dato— ni implementa la intención durable **antes del POST** que exige el §5.2.

**Lo que el revisor intentó refutar y no pudo**, y conviene registrar: el secuenciador acepta las
estructuras del plan sin modificarse; el YAML ausente sí produce `saltada`+`Pendiente` sin
preguntar; `_alta_crm` sí protege la reentrada de un expediente ya vinculado (cero POST medido); y
las comprobaciones de sala y viabilidad son de lectura, no construyen esas fases.

**Y corrigió mi aritmética:** el plan anunciaba 13 tests y son **15** (5+3+3+2+2), con una orden de
Task 5 que reúne 15 y no los 10 que decía.

<!-- mandato-literal:inicio:v2r1 -->

# Revisión adversarial — V2, el lazo del CRM (R1, sobre el PLAN)

Eres el revisor adversarial de un **plan de implementación** de un repositorio legal-tech en Python
(Windows). Trabajas **en solo lectura** sobre una copia congelada del árbol: no hay `.git`, y no
debes modificar nada bajo `../head`. Tu directorio de trabajo es el actual (`workdir`), y es el
único sitio donde puedes escribir, además de `/tmp`.

## El objeto

**El plan:** `../head/docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md`

Todavía **no hay código escrito**: esta ronda es sobre el diseño de la implementación, antes de la
primera línea. El árbol completo está en `../head` para que puedas **verificar contra el código
real** todo lo que el plan afirma.

**Contexto de diseño, que el plan dice no rediseñar:**
`../head/docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, sus §§5,
5.1, 5.2 y **§21.3** (la tabla de qué sale de V1 y a dónde va). Ese spec ya pasó cinco rondas.

## Qué se quiere construir, en dos frases

`scripts/abrir_caso.py --modo v1` corre hoy tres etapas (`drive`, `crm`, `sala_maquina`) y tiene una
puerta que le **prohíbe escribir en el CRM** (exige `--crm skip`). V2 añade cuatro etapas —
`crm_alta`, `crm_ficha`, `actuacion`, `verificar` — que sí escriben, sustituyendo esa puerta.

## Puedes ejecutar, y conviene que lo hagas

El Python del sistema —`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`— tiene
`pytest`, `yaml`, `dotenv`, `typer`, `httpx` y `filelock`. Desde una copia de `../head` en tu
workdir puedes correr tests y sondas AST. Dos avisos: usa un `--basetemp` corto (p. ej. `C:/t/v2`),
y **no mutes `../head`** — copia a tu workdir lo que necesites.

Si no puedes verificar algo, dilo como **SIN VERIFICAR**. No es un demérito: es información.

## Qué quiero de ti

Lee el plan con criterio propio. Interesan especialmente:

1. **¿Las firmas que el plan asume existen y son como dice?** El plan invoca `_alta_crm`,
   `core.crm_ficha.cargar_ficha_yaml`, `core.sudespacho_actuaciones.alta_actuacion`,
   `core.verificar_apertura`, `core.apertura_v1.{Etapa,EtapaResultado,Pendiente,secuenciar}` y
   `ETAPAS_V1`. Compruébalas **en el árbol**. Una firma inventada convierte el plan en ficción.
2. **La puerta que se sustituye.** Hoy `--modo v1` exige `--crm skip`
   (`scripts/abrir_caso.py`, busca el mensaje). El plan dice que esa puerta protege una propiedad
   —que nadie escriba en el CRM por accidente— y que la sustituye por otra garantía. **¿De verdad
   la conserva?** ¿Hay algún camino por el que, tras este cambio, se escriba en el CRM sin que el
   operador lo haya pedido? ¿Qué pasa con el default de `--crm`?
3. **El reparto V2 / V3.** La tabla del §21.3 manda `email`, `sala_lectura` y `viabilidad` a V3, y
   la **ejecución de la fase §8.1** a *posterior a V3*. El plan dice excluirlas. ¿Se le cuela
   alguna por la puerta de atrás — por ejemplo, a través de `verificar_apertura`, que comprueba la
   sala y la viabilidad, o del propio `crm_ficha`?
4. **`saltada` frente a `fallo` frente a `Pendiente`.** El plan decide que un `_ficha_crm.yaml`
   ausente es `saltada`+`Pendiente` (la secuencia sigue) y uno inválido es `fallo` (la secuencia
   corta, porque `secuenciar` para en el primer `fallo`). ¿Está bien esa asimetría? ¿Hay casos en
   que corte cuando no debería, o siga cuando debería parar?
5. **Idempotencia y reentrada.** La secuencia debe poder relanzarse. `crm_alta` sobre un caso que
   ya tiene expediente, `actuacion` sobre una ya creada (`alta_actuacion` tiene un `Recibo`
   reanudable y un parámetro `desde`, que el plan **no usa**). ¿Qué pasa al relanzar? ¿Se duplica
   algo en el CRM?
6. **Los tests del plan: ¿prueban lo que dicen?** Todos inyectan la dependencia. ¿Hay algún test
   que pasaría con una implementación rota? ¿Alguna propiedad importante sin test?
7. **El riesgo que el propio plan declara** al final (`typer.Exit` escapando de
   `scripts/crm_ficha.main()`): compruébalo en el árbol y di si el plan lo trata bien.

También quiero tu juicio sobre el **diseño**: si una decisión del plan te parece equivocada, dilo,
aunque esté bien especificada.

## Formato de cada hallazgo

Escribe `INFORME.md` en tu directorio de trabajo. Para cada hallazgo:

- **Id** (`H-01`, …) y **título** de una línea.
- **Dónde**: sección del plan, y fichero/línea de `../head` si aplica.
- **Qué pasa**: el defecto, con el camino concreto que lo produce.
- **Cómo lo verificaste**: comando y salida, o `SIN VERIFICAR` y por qué.
- **Severidad**: `ALTO` · `MEDIO` · `BAJO`.
- **Coste del remedio**: `trivial` (una línea) · `acotado` (una tarea del plan) ·
  `estructural` (cambia el reparto de tareas o el diseño).

Los dos ejes son independientes y los necesito **los dos**: sin el segundo, un defecto menor con
remedio estructural llega indistinguible de uno grave que se arregla en una línea, y quien adjudica
se queda sin el dato que decide.

Cierra con un **veredicto**: `SHIP`, `LISTA-CON-CAMBIOS` o `NO-SHIP`, y una línea de por qué.

## Dos cosas sobre el encargo

- **Volver sin hallazgos es un resultado válido.** Si el plan te parece correcto, dilo; no busques
  defectos para justificar la ronda. Prefiero un informe corto y cierto que uno largo y
  especulativo.
- **No escribas código ni apliques cambios.** Tu salida es el informe. Quien adjudica contrasta
  cada hallazgo contra la fuente y decide; no tienes la última palabra sobre corrección, y eso no
  te resta: un hallazgo bien argumentado vale aunque se refute.

## Evidencia de no-mutación

Al empezar y al terminar, calcula y reporta el `sha256` de:

```
../head/docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md
../head/scripts/abrir_caso.py
```

Ponlos al principio y al final del `INFORME.md`.


<!-- mandato-literal:fin:v2r1 -->

<!-- informe-literal:inicio:v2r1 -->

# Revisión adversarial V2 — R1 sobre el plan

Objeto: `../head/docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md`.
Revisor: Codex. Fecha: 2026-09-14. Árbol congelado sin `.git`.

## Evidencia inicial de no-mutación

Calculada antes de leer el plan con `Get-FileHash -Algorithm SHA256`:

| Fichero bajo `../head` | SHA-256 inicial |
|---|---|
| `docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md` | `710ea6c49899d3cc12964694d81118e2ff04b744c31392431ff69fae34dab4d8` |
| `scripts/abrir_caso.py` | `019c8846e3d070500d1308ecfb0d618288d3ea6e9036a56d88f84ddb05768a4d` |

## Alcance y evidencia ejecutada

No se ha implementado V2 ni modificado `../head`. Se copió el árbol a `workdir/copia`. Las sondas están en `sonda_revision.py` y su salida en `sondas.txt`; la salida de pytest está en `baseline.txt`, todos dentro de `workdir`. Las sondas cargan los bloques Python literales del plan **en memoria**, sustituyen los efectos externos y bloquean conexiones de socket. No son una implementación corregida ni una ejecución del CLI V2 de extremo a extremo.

Comandos reproducibles, desde `workdir`, con el Python facilitado:

```powershell
$py = 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
& $py ./sonda_revision.py
```

Desde `workdir/copia`, se ejecutó:

```powershell
$env:CASOS_ROOT = Join-Path (Get-Location) 'datos_prueba'
& $py -m pytest tests/test_abrir_caso_modo_v1.py tests/test_abrir_caso_exit_bajo_mutex.py tests/test_crm_ficha_cli.py tests/test_sudespacho_actuaciones.py tests/test_sudespacho_actuaciones_r2.py tests/test_sudespacho_actuaciones_r3.py tests/test_verificar_apertura.py -q -p no:cacheprovider --basetemp=../t --tb=short
```

Resultado: **309 pasados, 1 omitido, salida 0**. El omitido es `tests/test_verificar_apertura.py:1592`, marcado `slow`. Se usó `workdir/t`: `C:/t/v2` queda fuera de las rutas autorizadas para escribir. No hubo errores de longitud de ruta en esta selección.

**SIN VERIFICAR:** suite completa y las dos semillas; ejecución contra CRM/Drive reales; aceptación contra el expediente 636 y limpieza posterior. Esta ronda es de solo lectura y no autoriza esos efectos. Los IDs de las sondas son sintéticos.

## Hallazgos

### H-01 — El vocabulario de etapas no sustituye la autorización de escritura

**Dónde:** Task 1, líneas 58–62 y 135–150; Task 5, líneas 586–607. Fuente: `../head/scripts/abrir_caso.py:1287–1292`, `:1372`, `:1558–1559`; `../head/core/apertura_v1.py:113–118`.

**Qué pasa:** el default de `--crm` sigue siendo `api`. La nueva puerta acepta tanto `api` como `skip`, pero ni `secuencia_v2` ni `_etapas_v2` reciben ese dato: ambas construyen las tres etapas escritoras sin condición. Se pierde la distinción entre omitir el flag, autorizar y prohibir expresamente la escritura. Una orden antigua con `--crm skip`, o una orden sin `--crm`, alcanza exactamente las mismas etapas. Nombrarlas no acredita autorización. Además, `--hasta crm_alta` ejecuta el alta y para **después**; para evitarla hay que pedir `--hasta sala_maquina`.

Los errores de llamada de H-02, H-03 y H-04 impiden hoy que los snippets completen esos POST. No presento un POST real como ejecutado: el defecto de autorización permanece una vez reparadas esas llamadas. El plan tampoco especifica cómo pasar `yes` al alta sin volver a preguntar en mitad de la secuencia.

**Cómo lo verifiqué:** comando de sondas, SONDA 3: `default CLI --crm: api`; la puerta devuelve `[]` con `api` y con `skip`; la secuencia invoca las siete etapas sin recibir `crm`; con `hasta='crm_alta'` invoca también `etapa_crm_alta`.

**Severidad:** ALTO. **Coste del remedio:** acotado.

**Remedio:** definir una autorización explícita de efectos antes de empezar, conservar `skip` en todas las etapas escritoras y propagar la decisión desde el CLI. Probar omisión, `skip`, autorización y parada con espías en los efectos. Si se cambia el default del modo libre, declararlo como cambio de comportamiento adicional.

### H-02 — `_alta_crm` no acepta la llamada ni devuelve el resultado que Task 2 interpreta

**Dónde:** Task 2, líneas 181–187 y 249–271. Fuente: `../head/scripts/abrir_caso.py:1012–1037`, `:1099–1142`.

**Qué pasa:** la firma real es `_alta_crm(ident, *, cuantia, crm_mode, yes, force=False) -> None`. El plan llama `_alta_crm(ident, case_dir)`: falla antes de ejecutar el cuerpo. Corregir solo los argumentos no basta. El helper devuelve `None` si el caso ya estaba vinculado, si se declina el alta, si el POST lanza una excepción, si falla el registro local y también después de un alta correcta. Task 2 convierte todos esos `None` en `saltada` con la afirmación «el caso ya tiene expediente CRM vinculado». Un timeout sin vinculación local queda descrito como si la vinculación existiera; la secuencia sigue sin pendiente específico.

El helper tampoco adquiere su propio mutex: corre bajo el mutex de `main`. Eso funciona si se conserva ese llamador, pero no acredita la afirmación de Task 2 de que el helper aporta por sí solo la exclusión.

**Cómo lo verifiqué:** SONDA 2: `TypeError: _alta_crm() takes 1 positional argument but 2 were given`. SONDA 4, invocando el helper real con sus efectos sustituidos: alta correcta → `None`, un POST y un registro local; timeout → `None`; caso ya vinculado → `None`, cero POST. Lectura de las ramas completas citadas.

**Severidad:** ALTO. **Coste del remedio:** estructural.

**Remedio:** fijar un resultado consumible que distinga creación, vinculación previa, omisión y fallos parciales/desconocidos, preservando el comportamiento del modo libre. Task 2 no puede ser únicamente el envoltorio propuesto. La persistencia necesaria para el resultado desconocido se trata en H-08.

### H-03 — La actuación pierde tanto su contrato de entrada como el recibo que permite reanudar

**Dónde:** Task 4, líneas 426–449 y 463–491. Fuente: `../head/core/sudespacho_actuaciones.py:80–83`, `:591–617`, `:1025–1074`, `:1077–1086`, `:1111–1186`.

**Qué pasa:** la sección Interfaces transcribe correctamente la firma, pero la implementación llama `alta_actuacion(firmante=..., case_id=...)`. No existe `case_id`; faltan `elemento`, `exp_id`, `referencia_esperada` y `asunto`. Tampoco se define cómo elegir el destino si el caso tiene más de un expediente. El test emplea `NIKOLAI TYUKHAY`, aunque la tabla real admite el username `Nikolai_Tyukhay`.

Reparada la entrada, permanece el defecto más grave: el plan descarta el `Recibo`. `no_intentada`, `incierta` e `incompleta` se declaran `hecha` igual que `verificada`. No se conserva `act_id`, destino ni motivo, y no se utiliza `desde`. Relanzar vuelve a crear una actuación; si la anterior quedó incompleta puede dejarla huérfana. Incluso una ejecución ya verificada vuelve a crear otra al repetirse. El helper evita recrear **cuando se le entrega el recibo**; no deduplica automáticamente por caso.

**Cómo lo verifiqué:** SONDA 2: `TypeError: alta_actuacion() got an unexpected keyword argument 'case_id'`; el firmante del test levanta `ValueError`. SONDA 6: los cuatro recibos salen `hecha`, sin pendientes. Dos llamadas al helper real, sustituyendo sus efectos inferiores, sin `desde` producen IDs `900` y `901`; una tercera con `desde` reutiliza `901`, con dos creaciones en total.

**Severidad:** ALTO. **Coste del remedio:** estructural.

**Remedio:** definir destino/asunto/username, traducir todos los estados del recibo y conservarlo de forma durable por operación. Reentrada verificada no crea otra; incompleta reanuda; incierta exige conciliación. Probar dos corridas y los fallos después del POST, no solo que se llamó a una función.

### H-04 — La llamada directa a `crm_ficha.main` entra en dry-run y su resultado no sirve de contrato de etapa

**Dónde:** Task 3, líneas 388–399; Self-review, líneas 678–682. Fuente: `../head/scripts/crm_ficha.py:59–63`, `:105–110`, `:200–225`; `../head/scripts/abrir_caso.py:840–846`.

**Qué pasa:** `main(case_id=...)` conserva como defaults objetos `typer.Option`, no los booleanos que habría resuelto el CLI. `dry_run` resulta verdadero, imprime «no se escribe nada» y lanza `Exit(0)`. El `except Exception` del plan lo captura y devuelve `fallo` con `Exit: `, sin ficha escrita.

La explicación final del plan es incorrecta: `typer.Exit` sí es capturable por `Exception`. Que derive de `RuntimeError` no cambia eso: `RuntimeError` deriva de `Exception`. Copiar el tratamiento de `Exit(0)` de sala de máquina sin resolver los defaults convertiría esta simulación en una falsa etapa hecha. Y pasar solamente `dry_run=False` tampoco es suficiente: `yes` seguiría siendo un objeto verdadero.

Además, aun pasando los booleanos explícitos, `main` retorna `None` cuando no pudo verificar las relaciones. Task 3 declara `hecha` sin trasladar ningún `Pendiente`. La pantalla conserva el aviso, pero el resultado estructurado y su registro de pendientes lo pierden.

**Cómo lo verifiqué:** SONDA 5: MRO `Exit -> RuntimeError -> Exception`; `bool(dry_run default): True`; adaptador literal → `fallo`, `Exit: `, cero escrituras. Con `dry_run=False, yes=True` y readback sustituido por error, el comando real imprime `SIN VERIFICAR` y la etapa sale `hecha`, con `pendientes=()`.

**Severidad:** ALTO. **Coste del remedio:** acotado.

**Remedio:** convertir la operación de ficha en una llamada con parámetros y resultado explícitos, dejando a Typer la traducción de entrada/salida. Distinguir cancelación, simulación, escritura verificada y escritura sin readback. Un `except typer.Exit` añadido aisladamente no resuelve esta frontera.

### H-05 — «Llevar el YAML que haya» ejecuta los efectos de §8.1 sin sus precondiciones

**Dónde:** Constraints, líneas 30–33; Task 3, líneas 301–304 y 366–393. Fuente: spec orquestador `../head/docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:216–224`, `:449–462`, `:498–526`, `:1363–1377`; `../head/scripts/crm_ficha.py:153–168`; `../head/core/crm_ficha.py:78–95`, `:144–169`.

**Qué pasa:** la exclusión de §8.1 es nominal. El comando que se invoca vincula cliente propio, crea o actualiza contrarios, vincula colaboradores y escribe Notas. Son los efectos materiales que el spec sitúa después de sala de lectura y viabilidad. El plan solo exige que exista un YAML interpretable, sin comprobar procedencia, cierre documental ni viabilidad. Un YAML con solo `contrario.nombre` pasa. Que lo escriba una persona no acredita las precondiciones del spec ni convierte esos efectos en alta mínima.

Este camino queda actualmente tapado por H-04. Al reparar la llamada para que escriba, un caso que solo terminó sala de máquina puede crear/vincular al contrario. La nota de §21.3 permite construir DTOs y adaptadores en V2; no permite ejecutar esta fase por mera existencia del fichero.

**Cómo lo verifiqué:** SONDA 1 ejecuta y pasa el test literal de YAML con solo nombre; SONDA 5 recorre el comando real con ese mismo contenido y efectos sustituidos. Se contrastaron las líneas de escritura con las precondiciones expresas de §8.1 y el aplazamiento de §21.3. No se crearon personas reales en CRM.

**Severidad:** ALTO. **Coste del remedio:** estructural.

**Remedio:** conservar diferida la ejecución de esos efectos o definir y justificar un subconjunto permitido de alta mínima que no cree/actualice al contrario. Ejecutar la fase completa requiere sus precondiciones, o una modificación explícita del reparto aprobado; el plan actual dice que no lo modifica.

### H-06 — El agregador propuesto omite el contrato real de fuentes y un cuarto estado

**Dónde:** Task 5, líneas 521–538, 564–583 y 610–613. Fuente: `../head/core/verificar_apertura.py:61–110`, `:482–502`, `:1113–1180`; `../head/scripts/abrir_caso.py:958–965`.

**Qué pasa:** no existe `todas`, pero la nota del plan **sí prevé añadirla**; su mera ausencia no es un defecto imprevisto. El problema es que ya existe `verificar(case_dir, fuentes=None) -> Informe`, y las nueve comprobaciones no comparten la firma ni devuelven las tuplas postuladas: producen `Resultado`; cinco requieren un `_Contexto` que comparte las lecturas de fuentes. Sin fuentes, el agregador real usa `SinRed`.

El plan no especifica ese contexto ni cómo suministrar `DeLaRed`. Un envoltorio de `verificar(cd)` deja sin consultar el CRM; llamar directamente a las nueve con `cd` tampoco satisface sus firmas. Hay además cuatro estados, incluido `sin_implementar`; el traductor propuesto lo ignora y cuenta la fila como comprobación hecha sin pendiente. Existe una ruta real a ese estado si falta `openpyxl` al leer un informe de viabilidad (`:325–329`).

**Cómo lo verifiqué:** firmas y ausencia de `todas` en SONDA 2. SONDA 7: un caso sintético con expediente registrado, usando `verificar` sin fuentes, devuelve `fallo` en ficha, actuación y cuantía CRM. Una fila `sin_implementar` pasa por el adaptador del plan como `hecha`, «1 comprobaciones», sin pendientes. Lectura del agregador existente y sus tipos.

**Severidad:** MEDIO. **Coste del remedio:** acotado.

**Remedio:** reutilizar el agregador real y definir el suministro de fuentes, la conversión de `Informe/Resultado` y la traducción exhaustiva de los cuatro estados. Conservar la diferencia entre comprobaciones enumeradas y ejecutadas. Probar el adaptador real con transporte sintético.

### H-07 — La verificación global pasa a bloquear V2 por artefactos de V3

**Dónde:** Task 5, líneas 558–583 y 596. Fuente: `../head/core/verificar_apertura.py:184–198`, `:257–295`, `:305–350`; `../head/core/apertura_v1.py:44–50`; `../head/scripts/abrir_caso.py:985–1008`, `:1645–1647`.

**Qué pasa:** verificar sala y viabilidad no ejecuta sus productores, por lo que no introduce esas etapas de V3 literalmente. Sí introduce una dependencia de su estado: cualquier `fallo` de las nueve comprobaciones hace que V2 termine `bloqueado`. Una sala de lectura inexistente deja un pendiente; crear su carpeta y no tener todavía los cuatro artefactos la convierte en fallo. Así, avanzar parcialmente en una fase ajena al alcance bloquea el cierre del lazo CRM, aunque este haya terminado bien. Un informe de viabilidad ilegible tiene el mismo efecto.

Esto también cambia una decisión ya materializada: `_informar_v1_y_verificar` ejecuta el diagnóstico **fuera del mutex** y no cambia el código de salida. El plan añade otra verificación dentro de la secuencia —que corre bajo el mutex—, pero no reconcilia el llamador posterior. Si este se conserva, habrá dos verificaciones con efectos diferentes sobre el estado.

**Cómo lo verifiqué:** SONDA 7, usando `c4_artefactos_de_la_sala` real y el traductor del plan: sala ausente → `pendiente` → `preparado_con_pendientes`; carpeta de sala vacía → `fallo` → `bloqueado`, «faltan 4 de 4». No se alteró el CRM entre ambos casos. Se verificó el llamador posterior en las líneas citadas.

**Severidad:** MEDIO. **Coste del remedio:** estructural.

**Remedio:** separar las condiciones de éxito de V2 del diagnóstico del expediente completo. Mantener visibles los defectos de V3 sin convertirlos tácitamente en requisitos de V2; definir un único lugar y efecto para el diagnóstico global. No requiere modificar `secuenciar`.

### H-08 — Capturar excepciones no implementa la recuperación durable exigida por §5.2

**Dónde:** Architecture, líneas 17–21; Tasks 2–3; Self-review, líneas 665–669. Fuente: spec orquestador `:232–247`, `:1363–1377`; `../head/scripts/abrir_caso.py:1042–1090`, `:1108–1126`, `:1549–1585`; `../head/scripts/crm_ficha.py:153–182`; `../head/core/sudespacho_create.py:1692–1734`.

**Qué pasa:** el plan afirma cubrir §5.2 traduciendo excepciones a `fallo`. Esa sección exige **antes del POST** una intención durable por operación y, después, verificación/conciliación antes de repetir. El alta actual busca duplicados pero no persiste esa intención. El marcador de ronda abierto por `main` no identifica cada efecto remoto ni su resultado. Un corte después del commit remoto y antes del registro local deja un efecto sin vincular; una excepción del POST queda en un aviso y un `None` (H-02). Si en la siguiente corrida aparece un duplicado por W-code, `_alta_crm` aborta pidiendo vincularlo manualmente, no lo adopta tras GET como prescribe §5.2.

La búsqueda previa y la política que bloquea ante consultas inconcluyentes son protecciones reales, pero no cierran toda la llamada. `create_expediente`, reutilizado por `_alta_crm`, captura cualquier excepción del alta REST y hace otro POST por el frontal legacy. Si REST hizo commit y se perdió su respuesta, se intenta una segunda creación **en la misma corrida**, sin otra consulta de duplicados entre ambos intentos. El plan hereda ese comportamiento y no lo reconcilia con §5.2. Para actuaciones, la pérdida del recibo agrava esta misma frontera con recreación reproducida en H-03. Un resultado en memoria, por sí solo, tampoco cubre la muerte del proceso.

**Cómo lo verifiqué:** lectura del helper de alta, su llamador y el fallback, confrontada con §5.2. SONDA 4 confirma que el timeout se consume y retorna `None`. SONDA 9 recorre `create_expediente` real con transporte sustituido: `REST: commit simulado; respuesta perdida`, seguido de `LEGACY: segundo POST`, retorno `644`. SONDA 6 confirma la recreación de actuaciones sin el recibo. **SIN VERIFICAR:** crash real tras commit en Sudespacho y duplicado real aceptado por el tenant; no se provocaron escrituras externas. La ausencia del paso durable y el segundo intento son verificables en esas rutas del árbol.

**Severidad:** ALTO. **Coste del remedio:** estructural.

**Remedio:** asignar en el plan la intención durable, la conciliación y las pruebas de interrupción por efecto. Reutilizar las protecciones existentes, sin presentarlas como equivalentes a §5.2. Si esta entrega parcial no las incluye, no puede afirmar que cierra ese contrato al habilitar los POST.

## Respuesta a los siete focos del encargo

1. **Firmas:** comprobadas por lectura e `inspect.signature`. `Etapa`, `EtapaResultado`, `Pendiente`, `secuenciar`, `ETAPAS_V1` y `cargar_ficha_yaml` coinciden con el uso propuesto. `_alta_crm` no coincide; la firma de actuación está bien transcrita pero mal invocada; el contrato del verificador requiere el trabajo de H-06.
2. **Puerta:** no conserva la propiedad; H-01 distingue default, `skip` y parada inclusiva. Los errores de integración enmascaran el riesgo, no lo resuelven.
3. **V2/V3:** no encontré un llamador nuevo de exportación Gmail ni de los productores de sala de lectura/viabilidad. Sí hay ejecución prematura de los efectos de ficha (H-05) y conversión del diagnóstico de V3 en bloqueo de V2 (H-07).
4. **Ausente/inválido:** la asimetría está implementada tal como el plan dice. SONDA 8: sin YAML, la secuencia continúa; `contrario: {nombre: null}` corta antes de verificar. Es prudente impedir la escritura de una ficha inválida. No comparto que para hacer visible ese defecto sea necesario suprimir todo diagnóstico posterior: `Pendiente` ya es visible, y `verificar` es independiente. La constraint «ninguna etapa aborta por falta de un dato humano» necesita limitarse expresamente: una plantilla con nombre aún vacío es justamente un dato humano ausente y hoy bloquea. No elevo la asimetría, por sí sola, a otro hallazgo: la decisión de corte está declarada y el problema de diagnóstico ya figura en H-07.
5. **Reentrada:** caso con expediente vinculado no vuelve a crear en `_alta_crm`; verificado con cero POST. La actuación no es idempotente si el llamador descarta `Recibo/desde` (H-03). La conciliación durable tampoco está cubierta (H-08).
6. **Tests:** las **15 funciones** de test de los bloques Python se invocaron con los snippets literales en memoria: **15/15 PASS**, incluyendo el test llamado `test_crm_alta_no_duplica_si_ya_hay_expediente`. Este último solo entrega `lambda: None`: no prepara un expediente existente ni observa un POST. El doble de actuación admite cualquier `**kw` y devuelve una cadena, ocultando firma, username y recibo. El test de orden no ejecuta los invocables ni prueba el CLI. Faltan contratos de dependencias reales, `skip`/default, reentrada, interrupciones, readback, cuatro estados del verificador y convivencia V2/V3. Las funciones no se ejecutaron mediante pytest con sus fixtures globales; el resultado acredita sus aserciones, no integración de extremo a extremo. La cuenta de Task 6 es errónea: son 5+3+3+2+2 = **15**, no 13; la orden de Task 5 reúne 15, no los 10 anunciados. No se ha validado su cifra base de suite.
7. **`typer.Exit`:** el riesgo declarado está mal explicado y el remedio sugerido es insuficiente; reproducción y efecto en H-04.

## Lo que intenté refutar y NO pude

- El secuenciador valida `hasta` antes de ejecutar, corta ante el primer `fallo` y conserva los pendientes. Sus tipos aceptan las estructuras del plan; no exige ser modificado para añadir etapas.
- Un YAML ausente realmente produce `saltada` y un `Pendiente`; no pregunta. La falta explícita de firmante también se declara como pendiente sin inferir al operador.
- `_alta_crm` protege la reentrada de un expediente ya vinculado y consulta duplicados cuando no hay vínculo local. La revisión no invalida esas protecciones por los defectos del nuevo adaptador.
- Las comprobaciones de sala y viabilidad son de lectura: no construyen esas fases por sí mismas. Su ausencia normal es pendiente, no fallo automático.
- La creación prevista de `todas` no es un placeholder inadvertido: está pedida por la nota. El hallazgo es su contrato incompleto frente al agregador existente.
- La aceptación real con lectura posterior es útil y está prevista. No sustituye las pruebas de omisión, reentrada y fallos; no la doy por realizada en esta ronda.

## Veredicto

**NO-SHIP** — El plan no es ejecutable tal como está y habilita efectos sin conservar autorización, alcance y recuperación; requiere corregir contratos y decisiones de diseño antes de implementar.

## Evidencia final de no-mutación

Recalculada al finalizar las comprobaciones con el mismo comando. Los dos hashes coinciden con los iniciales:

| Fichero bajo `../head` | SHA-256 final |
|---|---|
| `docs/superpowers/plans/2026-09-14-apertura-v2-lazo-crm.md` | `710ea6c49899d3cc12964694d81118e2ff04b744c31392431ff69fae34dab4d8` |
| `scripts/abrir_caso.py` | `019c8846e3d070500d1308ecfb0d618288d3ea6e9036a56d88f84ddb05768a4d` |


<!-- informe-literal:fin:v2r1 -->
