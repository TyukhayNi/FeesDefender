---
tipo: spec
estado: vigente
creado: 2026-09-25
objeto: core/crm_ficha.py, scripts/crm_ficha.py, scripts/crm_colaboradores_firmas.py
rev: "4"
---

# `crm_ficha`: el YAML se lee entero, y lo que se verifica es el conjunto y sus datos

Remedio de `MEJORAS #283` y `#288`, las dos medidas en aperturas de este mes. **Pieza de dos
rondas** por el radio de daño: escribe datos de cliente en el CRM, decide qué partes quedan
vinculadas a un expediente, y un vínculo de más **da acceso** al expediente a quien no debe
tenerlo. La primera ronda fue sobre este diseño, la segunda sobre el plan, y la tercera
—autorizada por Nikolai sobre el techo de dos— sobre el diff (§7).

**Rev. 2 (2026-09-25), tras la R1 de Codex (`gpt-6-astra`·`medium`): `REQUIERE-REVISION`, 4
hallazgos, 4 confirmados, 0 refutados** (adjudicación en el §8). La rev. 1 cerraba las claves y
los vínculos y dejaba abierta la misma frontera en tres sitios más: el parser pierde claves
repetidas antes de validar nada, una clave válida no garantiza un valor válido, y un conjunto de
ids exacto certificaba una ficha **cuyos datos no se habían escrito** —justo el caso de
W-030A13 al relanzarlo con el YAML corregido—. La rev. 1 no se conserva: no llegó a código.

**Rev. 3 (2026-09-25), tras la R2 de Codex (`gpt-6-astra`·`medium`) sobre el plan y sobre si
esta rev. 2 remediaba la R1: `REQUIERE-REVISION`, 9 hallazgos, 9 confirmados, 0 refutados**
(adjudicación en la §9 del plan, `docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md`).
Los remedios a H-01 y H-02 de la R1 eran reales; los de H-03 y H-04, incompletos: `id_crm` se
validaba solo por el nombre, y toda comparación de datos llegaba **después** de escribir. Cambian
A.4 (una fase previa de solo lectura, e `id_crm` dentro de los resolutores del core), B.2 (se
audita la declaración, no el DTO, y la lectura final no promete deshacer nada) y el §6. Y tres
precisiones que la misma decisión arrastra: A.1 (las repetidas se acumulan en todo el documento y
una clave que no es un texto se rechaza con su línea), A.3 (lo que no puede llegar nunca se
rechaza al validar) y el §5 (dos límites nuevos, declarados).

**Rev. 4 (2026-09-26), tras la R3 de Codex (`gpt-6-astra`·`medium`) sobre el diff:
`REQUIERE-REVISION`, 4 hallazgos y una observación, todos confirmados** (adjudicación en la §10
del plan). Cambian A.1 (se mira también lo que hay bajo un merge, y se rechaza toda clave que no
sea un texto, también la escalar), A.3 (un NIF que se queda en nada sin sus separadores), A.4 (el
NIF viaja en la forma con la que se busca, y dos partes de un rol no pueden acabar en la misma
ficha) y el §5, donde **dos frases eran falsas** y se corrigen con lo medido. **Ninguna ronda
revisa esta rev. 4**: la R3 era la última autorizada.

## 0. Lo medido, que es lo que decide el diseño

- **`#283` (W-030A13, 2026-09-16; medido por GET el 2026-09-23).** El `_ficha_crm.yaml`
  escribió el primer apellido como `apellido:`; `_contrario_de` lee `apellido1` con `d.get` y no
  mira lo que sobra: la corrida terminó sin error y las fichas 1128 y 1129 quedaron con
  `1apellido` **vacío**. **El daño llega al burofax:** Codicert compone el nombre del requerido
  desde esos campos del CRM (`core/expedicion_certificada.py`, `_CAMPOS_NOMBRE_COMPLETO`).
- **`#288` (expediente 653, 2026-09-16).** `_auditar` comprueba lo pedido y nunca lo que sobra:
  «VERIFICADA por lectura» con cuatro colaboradores y seis vinculados.
- **Censo del 2026-09-25** sobre los **14** `_ficha_crm.yaml` reales del Drive (nombres de clave y
  conteos, nunca valores): en raíz y en colaborador, solo claves que el loader conoce; en
  contrario, una desconocida —`apellido`—, dos veces y las dos en W-030A13; **cero** mappings con
  claves repetidas; y **cero** partes sin NIF ni email (17 contrarios, 39 colaboradores). Las
  reglas estrictas de este diseño no rechazan ninguna ficha legítima del corpus.
- **Leído en el código, 2026-09-25 (R1/H-03):** los campos que se completan en un contrario que
  ya existe son `email`, `movil`, `direccion`, `poblacion`, `cp`, `telefono` y `provincia`
  (`core/sudespacho_relations.py`, `_COMPLETABLES_CONTRARIO`); **ni el nombre, ni los
  apellidos, ni el NIF**. Y los errores al completar se registran en el log sin cambiar el
  resultado del CLI.

## 1. La frontera, y por qué son varios defectos de una sola

**Lo que el YAML declara y lo que queda en el CRM tienen que ser verificablemente lo mismo, en
los dos extremos, y cada parte tiene que poder identificarse igual en cada corrida.**

- **Entrada:** el YAML se lee **sin pérdida** (ni claves repetidas, ni alias), con **claves
  conocidas** y **valores del tipo que el campo admite**. Lo que no cumpla se rechaza entero,
  antes de escribir nada.
- **Salida:** lo leído del CRM se contrasta con lo declarado como **igualdad** —en los vínculos
  de los tres bloques y en los datos que el YAML declara de cada parte—, no como inclusión.
- **Identidad:** cada parte lleva algo que la identifique de forma estable (NIF, email o el id
  del CRM); sin eso, relanzar crearía otra ficha en vez de encontrar la misma.

## 2. Decisiones

1. **El YAML es la lista COMPLETA de partes del expediente** (Nikolai, 2026-09-25). Una parte
   vinculada que el YAML no declara es un **fallo** de la verificación, no un aviso.
2. **Lo que no se entiende se rechaza, no se avisa ni se adivina:** claves desconocidas o
   repetidas, valores de otro tipo, alias. Ni alias de clave (`apellido` → `apellido1`).
3. **`crm_ficha` nunca desvincula, y no pisa datos que ya existen.** Una parte sobrante o un
   dato distinto del declarado lo decide un humano. La política de completar solo lo vacío
   (`_COMPLETABLES_*`) no se amplía aquí (§5).
4. **La comparación y la validación viven en el core**, como funciones puras (`CLAUDE.md`: la
   lógica en `core/`, el script solo orquesta).
5. **«VERIFICADA» dice exactamente lo que certifica:** los tres bloques de vínculos son los del
   YAML, cada parte tiene en el CRM los datos que el YAML declara, y las notas coinciden. No
   certifica `firmante`, que lo consume la etapa `actuacion` de V2, no este CLI.

## 3. Parte A — el YAML se lee entero o no se escribe nada (`#283`, R1/H-01, H-02, H-04)

**A.1 Lectura sin pérdida (H-01).** Un cargador propio sobre `yaml.SafeLoader` que, al
construir cada mapping, **rechaza una clave repetida** con su línea, y que rechaza **alias**
(`&` / `*`) y la clave de **merge** (`<<`): un YAML escrito a mano no los necesita, y con ellos una
parte o un dato pueden aparecer dos veces o sustituirse sin verse. Función pública
`core.crm_ficha.leer_yaml_ficha(path) -> dict`, que usan **los dos** lectores del fichero:
`cargar_ficha_yaml` y `scripts/crm_colaboradores_firmas.py::apply`, que hoy hace su propio
`yaml.safe_load` y **reescribe el fichero entero** —así consolidaría una pérdida que
`crm_ficha` ya no podría ver—. Con el cargador compartido, `apply` falla en vez de reescribir.

Las repetidas se **acumulan en todo el documento**, cada una con su línea, y una clave que no es un
texto —una lista o un mapping como clave, o un escalar que YAML convierte: `1`, `null`, `yes`, una
fecha— también se rechaza con la suya; lo que hay **debajo** de un merge rechazado también se mira
(R3/H-03). Todo sale como `ValueError`, que es el contrato de los llamadores (R2/H-04). **El límite, declarado en vez de
prometido:** un error de sintaxis para el análisis, y de ese fichero solo se puede decir ese.

**A.2 Claves conocidas.** Tres tuplas de módulo, una sola fuente de las que leen los
constructores: `CLAVES_RAIZ` (`contrario`, `colaboradores`, `notas_html`, `cliente_propio`,
`firmante`), `CLAVES_CONTRARIO` (las once de hoy más `id_crm`) y `CLAVES_COLABORADOR` (las cinco
de hoy más `id_crm`). Cualquier otra, con su ruta (`contrario[0].apellido`) y **todas** las
válidas cercanas (`difflib.get_close_matches`): `apellido` casa igual con `apellido1` que con
`apellido2`, y elegir una sería adivinar (R2/H-07). La sugerencia no se convierte en alias de
entrada, y si no hay ninguna cercana, no se inventa.

**A.3 Valores del tipo que el campo admite (H-02).**

| Campo | Admite | Todo lo demás |
|---|---|---|
| escalares de parte y `notas_html`, `firmante` | `str`, o `null` (= «no hay dato») | error con su ruta; `int`/`float` conservan la explicación del octal |
| `nombre` de cada parte | `str` **no vacío después de quitar espacios** | error |
| `id_crm` | entero positivo, o `str` de solo dígitos (un booleano no vale) | error |
| `cliente_propio` | ausente o `null` → el de siempre; `str` del catálogo `CLIENTES_PROPIOS_EV` | error (hoy `false` caía al valor por defecto por el `or`) |
| `contrario` | como en P6: ausente/`null`, mapping, lista de mappings | error con índice |
| `colaboradores` | ausente/`null`, lista de mappings | error; elemento no mapping, error con índice |
| raíz | mapping, o documento vacío (= ficha vacía) | error: `false`, `0`, `[]`, texto |
| `provincia` del contrario | un texto que `provincia_canonica` reconoce | error: el Select lo descartaría y el dato **no puede llegar nunca** |
| `movil`, `telefono` (los dos roles) | un texto que conserve algo tras `normalize_es_phone` | error: `'+34'` se queda vacío en el DTO y la parte se escribiría sin él |
| `nif` (los dos roles) | un texto que conserve algo sin sus separadores (`_canonizar_documento`) | error **aunque haya email o `id_crm`**: `'-- .'` se comparaba igual a una ficha sin NIF y salía «VERIFICADA» (R3/H-02) |

Las tres últimas filas son propiedades de la **declaración**, no de la ficha: valen igual para una
parte que se va a crear que para una que ya existe, y por eso se rechazan al validar y no al
auditar (R2/H-02). La del NIF es la misma propiedad que la del teléfono, en el comparador en vez
de en el DTO: un dato declarado no puede desaparecer por el camino.

**A.4 Identidad estable, y ninguna escritura sobre una ficha que el YAML contradice (R1/H-04;
R2/H-01, H-06, H-08).** Cada contrario y cada colaborador tiene que llevar **NIF, email o
`id_crm`**. Sin ninguno, la corrida se rechaza al validar: `resolver_parte` identifica solo por NIF
o email, así que cada relanzamiento crearía una ficha nueva y la anterior pasaría a «sobrante» sin
salida. Medido: hoy ninguna parte real necesita `id_crm`.

**`id_crm` es la salida para una parte legítima sin identificadores** —y para declarar una parte que
alguien vinculó a mano—, y **vive en el core**, en los dos resolutores (`_resolver_o_crear_contrario`
y `_resolver_o_crear_colaborador` de `core/sudespacho_relations.py`): con `id_crm` no se busca ni
se crea; se completa lo vacío de esa ficha igual que si se hubiera hallado por NIF, y se devuelve
`(id, False)`. El CLI sigue llamando a `ensure_*` para toda parte: **no hay un segundo camino de
escritura en la orquestación**, y el vínculo por id hereda el completado sin reescribirlo. El campo
del DTO, su aceptación al validar y esa rama llegan juntos: aceptar `id_crm` antes de que nadie lo
consuma lo mandaría por el camino de **creación** (R2/H-06). Sin `id_crm`, ningún comportamiento
cambia.

**El NIF viaja en la forma con la que se busca (R3/H-01).** El DTO lo lleva canonizado —sin
separadores y en mayúsculas, `_canonizar_documento`— y la declaración conserva el escrito, que es
lo que se audita. El CRM normaliza caja y espacios al buscar, pero **no** los separadores (medido;
docstring de `_canonizar_documento`): un NIF escrito con puntos se guardaba así, la búsqueda
canónica de la corrida siguiente no lo encontraba y se creaba otra ficha. Solo en los DTO de esta
pieza; los demás llamadores no cambian. Y el NIF cuenta como identidad por esa forma: uno que se
queda en nada no identifica (A.3).

**Dos partes de un rol no pueden acabar en la misma ficha (R3, observación).** La fase previa
compara cada parte con el CRM de **antes** de la corrida, y `ensure_*` vuelve a resolver al
escribir: la primera parte escribe, y la segunda aterriza en esa ficha y la completa con lo suyo.
Al validar se rechaza lo que se decide sin el CRM —el mismo `id_crm` o el mismo NIF canónico en dos
partes de un rol, y un email compartido sin el NIF de las dos o el `id_crm` de las dos, porque el
buzón compartido solo se descarta por el documento de cada ficha (`[APER-71]`)—, y en la fase
previa, lo que solo se ve resolviendo.

**La fase previa, de solo lectura.** Después del corte de `--dry-run` y de la confirmación, y
**antes del primer writer** (`link_ev_mmc`), la corrida identifica cada parte que **ya existe** —por
`id_crm` (el GET de esa ficha) o por NIF/email (la resolución de hoy, que ya es de solo lectura y ya
levanta ante conflicto o ambigüedad)— y compara su ficha con lo declarado, con las normalizaciones
de B.2. Es error, **todos juntos y con cero writers**:

- un campo **distinto** —el CRM tiene valor y es otro—. La corrida nunca pisa, así que ese dato no
  lo puede arreglar ella, y escribir antes solo dejaría un vínculo y unos completados sobre una
  ficha que el propio YAML desmiente, que `crm_ficha` además no desvincula;
- una ficha que no se puede leer; un `id_crm` que no existe —el GET falla, o la ficha vuelve sin
  `nombre`—; y cualquier conflicto o ambigüedad de la resolución: no se escribe sobre lo que no se
  ha podido comparar;
- dos partes del mismo rol que resuelven a la **misma** ficha existente —una por `id_crm` y otra
  por un NIF que el CRM ya tiene en esa ficha, por ejemplo— (R3).

Lo **vacío** no es contradicción: si el campo es completable, se completa como hoy; si no, lo dice
la lectura final (B.2), que es el caso de W-030A13. **La fase previa es la parte de B.2 que ya está
decidida antes de escribir**: lo no vacío del CRM no cambia al completar, así que no puede fallar
donde la lectura final no fallaría. Y una parte que no existe no tiene nada que comparar: se crea,
y la audita la lectura final.

**A.5 Todos los problemas en un solo `ValueError`**, no el primero: quien corrige a mano tiene
que ver la lista entera.

**Efecto en los llamadores**, todos ya en voz alta ante un `ValueError` (comprobado por la R1):
`scripts/crm_ficha.py` sale con código 1 antes del primer writer; `scripts/crm_ficha_validar.py`,
con código 2; `scripts/abrir_caso.py::_firmante_de` lo convierte en `FichaIlegible`, y la etapa
`actuacion` de V2 sale `fallo` con el pendiente `ficha_crm_ilegible` —después de `crm_alta`, así
que en V2 no significa «cero escrituras de toda la apertura»—; y `crm_colaboradores_firmas.apply`
falla sin reescribir.

## 4. Parte B — la verificación compara vínculos y datos (`#288`, R1/H-03)

**B.1 Vínculos por igualdad, con multiplicidad.** Función pura en `core/crm_ficha.py`:

```python
@dataclass(frozen=True)
class AuditoriaRelaciones:
    ok: list[str]; faltan: list[str]; sobran: list[str]

def auditar_relaciones(esperado: Mapping[str, Sequence[str]],
                       leido: Mapping[str, Sequence[Mapping]]) -> AuditoriaRelaciones: ...
```

`esperado` = el cliente propio y los ids de cada contrario y colaborador, **resueltos** (por
`ensure_*` o por `id_crm`); `leido` = la salida normalizada de `get_relaciones`, que ya desacumula
un registro por id (`docs/INTEGRACION_SUDESPACHO.md`, líneas 2256-2276 en `dbe17ff`, citadas por
la R1). Solo esos tres bloques.
Por multiplicidad en los dos sentidos: dos declaraciones que colapsan a un id con un solo vínculo
es `falta`, no «ok» —la multiplicidad no se cambia por conjuntos, que ocultarían el colapso—.
`None` de `_leer` sigue siendo SIN VERIFICAR, no «vacío».

**B.2 Datos por igualdad (R1/H-03), con lo declarado intacto (R2/H-02, H-03).** Para cada parte
resuelta —**creada o existente**, contrario o colaborador—, la corrida **relee su ficha por id**
después de escribir y compara **cada campo que el YAML declara no vacío** con el del CRM. Lo que se
compara es **la declaración** —el mapping validado de la parte—, no el DTO: el DTO normaliza al
construirse (`'+34'` se queda vacío), y cualquier transformación entre el YAML y la auditoría es un
sitio por donde lo declarado se pierde sin que la auditoría lo vea. Las normalizaciones son las que
aplica la escritura, y **las mismas en los dos lados**:

| YAML | CRM | Normalización antes de comparar |
|---|---|---|
| `nombre`, `apellido1`, `apellido2`, `direccion`, `poblacion` | `nombre`, `1apellido`, `2apellido`, `direccion`, `poblacion` | espacios (extremos y repetidos); sin distinguir mayúsculas (el CRM las guarda en mayúsculas) |
| `nif` | `nif_cif` | `_canonizar_documento`: sin separadores y en mayúsculas |
| `email` | `email` | espacios y minúsculas |
| `movil`, `telefono` | `movil`, `telefono1` | la de `normalize_es_phone` |
| `cp` | `cp` | espacios |
| `provincia` | `provincia` | `provincia_canonica` del lado del YAML, y la de texto en los dos: `barcelona` casa con `Barcelona` (R2/H-03). El `1` del enum («Sin Asignar», atlas) cuenta como vacío |

Las propiedades del CRM están ancladas a la fuente, no supuestas: el payload de creación
(`_rest_post_cliente_contrario` y `_rest_post_colaborador`), los GET (`get_cliente_contrario`,
`get_colaborador` y su `_PROPS_COLABORADOR`), el atlas (`docs/CRM_SUDESPACHO_ATLAS.md`,
`### clientes_contrarios`) e `INTEGRACION_SUDESPACHO.md` (§10.6, mapping de `clientes_contrarios`).
Si al implementar algo no cuadra, **se mide antes de codificarlo**.

Tres resultados por campo: **igual**; **vacío en el CRM** (el dato no llegó: la ficha ya existía y
el campo no es de los que se completan, o se completó y no consta); **distinto** (el CRM tiene
otro valor, que no se pisa). Los dos últimos salen como `[DATO]` y hacen **fallar** la
verificación, con la instrucción de revisarlo en el CRM. Los errores al completar, que hoy solo
se registran, **pasan al veredicto por resultado**: si el GET o el PUT del completado fallan, el
campo sigue vacío y la lectura final lo dice como `[DATO]`; una incidencia cuyo resultado sí llegó
no tiene por qué falsear el veredicto (R2, acta §6).

**Lo que la lectura final no promete.** Detectar un dato que no llegó al crear o al completar
exige leer después de escribir, y esa lectura **no deshace** la creación ni el vínculo. Por eso lo
que ya está decidido antes de escribir —un dato distinto en una ficha que existe— va a la fase
previa (A.4) y falla con cero writers; lo que solo se sabe después sale como `[DATO]` con la
corrida hecha, y lo corrige un humano en el CRM.

**Aplicado a W-030A13:** relanzar con el YAML corregido resolvería las mismas fichas por NIF, no
completaría `1apellido` (no es completable) y hoy diría «VERIFICADA». Con B.2 dice
`[DATO] clientes_contrarios id=1128 1apellido: vacío en el CRM`, y el burofax no sale con esa
ficha dada por buena.

**B.3 El veredicto.** `faltan`, `sobran` o `[DATO]` → código 1 y, para cada tipo, qué hacer sin
hacerlo: una parte sobrante legítima se añade al YAML (con `id_crm` si no tiene identificadores)
y se relanza, y si no lo es, se desvincula a mano; un dato vacío o distinto se corrige en la ficha
del CRM. **Nunca** «VERIFICADA» con algo pendiente. Los tres vacíos y todo leído → «VERIFICADA:
vínculos y datos de la ficha», con el alcance del §2.5. Y un fallo conocido **gana** a un «SIN
VERIFICAR» simultáneo: si algo se leyó y está mal, la salida es 1 aunque otra lectura haya caído.

**B.4 La auditoría parcial** —tras una escritura fallida— **solo informa de `faltan`** y lo dice:
las partes aún sin resolver no tienen id, y sus vínculos de una corrida anterior saldrían como
sobrantes sin serlo. El código de salida sigue siendo 1 (la R1 lo comprobó: no abre un falso
«VERIFICADA»).

## 5. Lo que queda fuera, dicho

- **Completar los apellidos vacíos de una ficha existente.** Es la reparación de 1128/1129, pero
  escribir en la ficha de una persona identificada quizá solo por email es otra decisión y otro
  radio de daño (`[APER-71]`): aquí **se detecta**, no se repara. Las dos fichas, como trabajo del
  caso.
- **Más de un cliente propio, o uno fuera de `CLIENTES_PROPIOS_EV`** (los particulares, `#289`):
  el dominio soportado es un cliente propio de E&V por expediente, y así se documenta.
- **C6 de `verificar_apertura`**, la misma frontera en el verificador: necesitaría el recibo de
  ids de la corrida. Otra pieza; y el `id_crm` de A.4 no es ese recibo.
- **Qué vinculó a los dos colaboradores ajenos del 653.**
- **`--dry-run` sigue sin leer el CRM**, tampoco para validar un `id_crm`: eso lo hace la fase
  previa de la corrida real (R2/H-08).
- **Una parte con `id_crm` cuyo NIF declarado pertenece a OTRA ficha**, cuando la ficha por id no
  tiene NIF. La fase previa compara con la ficha por id y, con `id_crm`, no busca (A.4), así que no
  lo ve. **Qué pasa después depende del rol, y lo midió la R3 (H-01).** En un colaborador el NIF es
  completable y se escribe —en su forma canónica, la misma con la que se busca—, así que las dos
  fichas comparten NIF y la siguiente resolución por NIF sale ambigua y **para** (lo prueba la
  integración). **Hasta la R3 esta frase era falsa:** el NIF viajaba como se escribió, y con
  separadores la búsqueda canónica no veía la ficha completada y devolvía la otra **sin**
  ambigüedad: una identidad duplicada que nadie detectaba. En un contrario el NIF no es completable
  (`_COMPLETABLES_CONTRARIO`): no se escribe, y la lectura final lo da por vacío. Sigue sin cubrirse
  una ficha **histórica** cuyo NIF se guardó con separadores, que la búsqueda canónica no encuentra:
  buscar duplicados escritos de cualquier forma es otra ampliación. Cerrarlo del todo es buscar
  también por los identificadores declarados, que es otra decisión sobre A.4 (`MEJORAS #313`).
- **Entre la comparación y la escritura el CRM puede cambiar, y no solo por otra sesión: también
  por la propia corrida** (R3, observación). Las dos resuelven por separado —la fase previa lee y
  `ensure_*` vuelve a resolver—, y lo que la corrida escribe entre una parte y la siguiente cambia
  lo que la siguiente encuentra. Lo que eso tenía de **silencioso** —dos partes que acaban en una
  ficha, la segunda completando lo que la primera contradice— se cierra en A.4, al validar y en la
  fase previa. **Queda abierto, y falla cerrado:** lo que la corrida completa puede hacer que la
  resolución de una parte posterior **pare** a mitad —un contrario por id cuya ficha no tiene NIF
  recibe el email que otra parte comparte, y el buzón de esa otra ya no tiene documento con que
  descartarla—; la corrida sale con 1 y una escritura parcial, que la lectura parcial dice. Y la
  ventana frente a **otra sesión**, como estaba: nada en el equipo la hace probable —tres
  abogados que no trabajan a la vez sobre el mismo expediente—, aunque nada la impide: `crm_ficha`
  tampoco toma el mutex (fila #17 de `PLAN.md`). No se construye un bloqueo para esto.
- **`_resolver_colaborador` ignora el `motivo` de `resolver_parte`**, anterior a esta pieza: ante un
  buzón compartido con una ficha sin documento, el colaborador cae al listado por email en vez de
  parar (el contrario sí para). Por `crm_ficha` ya no llega el NIF no interpretable (A.3); el buzón,
  sí. Cambiarlo cambia a todos los llamadores y pide su propia regresión (`MEJORAS #314`).

## 6. Cómo se prueba (para el plan)

Contra dobles, como `tests/test_crm_ficha_cli.py`, y en tres niveles, porque cada uno ve lo que
los otros no: funciones puras del core; el CLI con sus lecturas y escrituras dobladas por su ruta;
y una **integración** con `ensure_*`, los resolutores y el completado **reales**, el transporte
doblado en `core.sudespacho_relations.<nombre>` por un doble **con estado**, y un espía de **todos**
los writers. Un doble que sustituye `ensure_*` no ve un PUT que ocurre dentro de `ensure_*`
(R2/H-01), y por eso las garantías de «cero writers» se prueban en la integración.

| Propiedad | El test que tiene que ponerse rojo |
|---|---|
| Sin pérdida (A.1) | claves repetidas en raíz, contrario y colaborador **con su línea afirmada**; dos repetidas → las dos; una clave lista o mapping; alias; merge **con y sin** alias; sintaxis rota → `ValueError`; y `crm_colaboradores_firmas.apply` sobre un YAML con repetidas falla sin reescribir (mismos bytes) |
| Claves (A.2) | desconocida en cada nivel → error con ruta y **todas** las sugerencias cercanas (`apellido` → `apellido1` y `apellido2`, sin convertirse en alias); sin candidata cercana, sin sugerencia; varias → todas |
| Tipos (A.3) | mapping o lista en **cada** escalar de los dos roles, en `notas_html` y en `firmante`; nombre solo espacios; `cliente_propio` `false`/`0`/`[]`/`{}`/desconocido; raíz `false`/`0`/`[]`/texto; provincia no reconocida; teléfono que se queda vacío; **controles positivos separados** para `null`, ausente, una provincia con otra caja y un teléfono legítimo |
| Valor a su destino | cada campo con un **centinela distinto** llega a su atributo del DTO; y cada campo del YAML, a su propiedad del CRM en la auditoría |
| Identidad (A.4) | parte sin NIF, email ni `id_crm` → error al validar; `id_crm` que no es un número → error; con `id_crm` → no se busca ni se crea, en los dos roles; `id_crm` inexistente o GET caído → error antes del primer writer; el mismo NIF o `id_crm` en dos partes de un rol, o un email compartido sin el NIF de las dos → error al validar, con controles positivos (dos NIF distintos con el mismo email; dos `id_crm` con el mismo email) (R3) |
| Fase previa (A.4) | dato **distinto preexistente** —por `id_crm` o por NIF— → error antes del primer writer y **cero** llamadas a writers, con la resolución y el completado reales y el transporte doblado; la **segunda** parte inválida → cero writers también para la primera; dos partes que resuelven a la misma ficha → cero writers (R3); `--dry-run` con `id_crm` no lee el CRM |
| Convergencia | dos corridas con el doble con estado: la segunda no crea otra ficha ni declara sobrante la primera; también con un NIF escrito con separadores, con el doble filtrando **como el CRM medido** —caja y espacios, no separadores— (R3/H-01); y el colaborador por id con un NIF ajeno deja la resolución siguiente por NIF **ambigua** |
| Vínculos (B.1) | el 653 reproducido → dos `[SOBRA]` y código 1; sobrantes en cada uno de los tres bloques, también con cero esperados; faltan y sobran a la vez; id `int` frente a `str` |
| Datos (B.2) | ficha existente con `1apellido` vacío → `[DATO]` y código 1 (el caso de W-030A13); la matriz campo × rol, con positivos y negativos de colaborador; una parte **creada** a la que el CRM no guardó un dato → `[DATO]`; provincia que casa con otra caja; GET o PUT del completado fallidos → `[DATO]` por resultado |
| Parcial (B.4) | fallar cada writer → código 1, sin «VERIFICADA», sin sobrantes emitidos |
| Veredicto (B.3) | un fallo conocido gana a un «SIN VERIFICAR» simultáneo; los negativos comparan contra el literal de éxito del módulo, no contra un texto copiado, para que un cambio de texto no los vacíe |
| Control positivo | conjunto y datos exactos → «VERIFICADA» y **ni rastro** de «SIN VERIFICAR»; las regresiones de hoy (`[FALTA]` por cardinalidad, SIN VERIFICAR) igual |

**Mutantes**, sobre **copias** del árbol y cada uno muerto por el aserto de su propiedad —no por
colección ni por un arnés roto—: quitar el rechazo de repetidas; quitar el del merge sin alias;
desconectar el lector en uno de sus dos consumidores; aceptar mappings en un escalar; quitar la
exigencia de identidad; cruzar dos asignaciones del constructor; quitar la comprobación de
sobrantes; comparar por pertenencia; quitar la verificación de datos, o saltarse en ella un rol o
las partes creadas; hacer asimétrica la provincia; ignorar `id_crm` en el core; quitar la fase
previa o moverla detrás de un writer; leer el CRM en `--dry-run`; que la parcial **emita**
sobrantes; y que un «SIN VERIFICAR» tape un fallo conocido. **Tras la R3**, además: el NIF que
viaja como se escribió, en cada rol; el NIF que se vacía y el que cuenta como identidad sin
serlo; lo de debajo de un merge y la clave escalar que no es texto; el mismo NIF o id en dos
partes, el email compartido y las dos partes en una ficha en la fase previa; las cuatro reglas que
tenían test y ningún mutante (clave desconocida, `id_crm` no numérico, teléfono, provincia); y un
elemento inválido de la lista filtrado en silencio, que es la versión ejecutable del M11 de P6.

## 7. Rondas y modelo

Dos, por el radio de daño (`CLAUDE.md` §«Cuántas rondas»), **más una tercera autorizada
expresamente por Nikolai el 2026-09-25** sobre ese techo. La R1 fue sobre la rev. 1 de este
diseño; la **R2, sobre el plan** de implementación y sobre si la rev. 2 remedia de verdad la R1
(`docs/superpowers/plans/2026-09-25-crm-ficha-claves-y-conjunto.md`); y la **R3, sobre el
diff** (2026-09-26, adjudicada en la §10 del plan). Las tres con `gpt-6-astra` · `medium`. El
remedio de la R3 no lo revisa ninguna ronda. El tope es por
pieza y no por fase (la tabla dice «una sobre el diseño (spec/plan) y una sobre el diff»): la R3
existe porque Nikolai la autorizó, no porque la regla la conceda.

## 8. Adjudicación de la revisión adversarial del diseño (Codex, 2026-09-25) — REQUIERE-REVISION, remediado

- **Objeto revisado:** el spec rev. 1 (`dbe17ff`)
- **Ronda:** R1 (primera de dos; la segunda, sobre el diff)
- **Revisor:** Codex CLI `0.155.0-alpha.16.3`, `gpt-6-astra` · `medium` · `default` (modelo y esfuerzo releídos del rollout)
- **Informe recibido:** `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-r1-adversarial-review.md`
- **Hallazgos:** 4 — 2 `alta`, 2 `media`; 4 confirmados contra la fuente, 0 refutados
- **Remediado en:** esta rev. 2 (§§1-6)

**Los cuatro, confirmados contra el código y no contra el informe**, y los cuatro son la misma
frontera de la rev. 1 mal cerrada: había cerrado las **claves** y los **vínculos** y el diseño
prometía «el YAML entero» y «lo mismo en los dos extremos».

- **H-01 (alta, acotado) — CONFIRMADO.** `yaml.safe_load('contrario: {nombre: UNO}\ncontrario:
  {nombre: DOS}')` devuelve solo `DOS`, sin error: una parte entera desaparece **antes** de que
  exista el diccionario que las tuplas validan. Y `crm_colaboradores_firmas.apply` lee y
  reescribe el fichero por su cuenta. Remedio: A.1, cargador sin pérdida compartido por los dos
  lectores. Medido: cero repetidas en las 14 fichas reales.
- **H-02 (media, acotado) — CONFIRMADO.** `_escalar` solo rechaza números y booleanos: un mapping
  pasa como su representación de Python; `nombre` se comprueba antes de quitar espacios; el `or`
  convierte `cliente_propio: false` en el valor por defecto y una raíz `false`/`0`/`[]` en una
  ficha vacía. Remedio: A.3, la tabla de tipos, con `null`/ausente separado de lo falso inválido.
- **H-03 (alta, estructural) — CONFIRMADO, y es el que cambia el diseño.** `_COMPLETABLES_CONTRARIO`
  no incluye nombre, apellidos ni NIF, así que una ficha existente con `1apellido` vacío se
  resuelve, se vincula, no se completa, y la igualdad de ids da «VERIFICADA». Es **exactamente**
  lo que habría pasado al relanzar W-030A13 con el YAML corregido. Remedio: B.2, la verificación
  relee los datos declarados; la reparación de lo vacío queda fuera, con su radio de daño (§5).
- **H-04 (media, estructural) — CONFIRMADO.** `resolver_parte` identifica solo por NIF o email;
  sin ninguno, cada corrida crea una ficha nueva y «añádela y relanza» no converge. Remedio: A.4,
  identidad obligatoria (NIF, email o `id_crm` validado). Medido: ninguna parte real sin NIF ni
  email hoy.

**Lo que el revisor intentó y no pudo, y se conserva:** la igualdad por multiplicidad detecta un
id de más en cualquiera de los tres bloques; ningún llamador degrada el error a «no hay ficha»; la
auditoría parcial no abre un falso «VERIFICADA»; `link_ev_mmc` no añade colaboradores ocultos; y
nada de lo propuesto obliga a desvincular ni a revisar la decisión de lista completa.

**Dos precisiones suyas incorporadas sin ser hallazgos:** la etapa `actuacion` de V2 sale
`fallo` (no «bloqueo») y ocurre después de `crm_alta`; y el dominio de `cliente_propio` es uno
de E&V por expediente, que ahora se documenta (§5) en vez de prometer que todo sobrante legítimo
se puede declarar.
