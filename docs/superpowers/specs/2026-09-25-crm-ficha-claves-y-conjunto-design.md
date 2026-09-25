---
tipo: spec
estado: vigente
creado: 2026-09-25
objeto: core/crm_ficha.py, scripts/crm_ficha.py, scripts/crm_colaboradores_firmas.py
rev: "2"
---

# `crm_ficha`: el YAML se lee entero, y lo que se verifica es el conjunto y sus datos

Remedio de `MEJORAS #283` y `#288`, las dos medidas en aperturas de este mes. **Pieza de dos
rondas** por el radio de daño: escribe datos de cliente en el CRM, decide qué partes quedan
vinculadas a un expediente, y un vínculo de más **da acceso** al expediente a quien no debe
tenerlo. La primera ronda fue sobre este diseño; la segunda irá sobre el diff.

**Rev. 2 (2026-09-25), tras la R1 de Codex (`gpt-6-astra`·`medium`): `REQUIERE-REVISION`, 4
hallazgos, 4 confirmados, 0 refutados** (adjudicación en el §8). La rev. 1 cerraba las claves y
los vínculos y dejaba abierta la misma frontera en tres sitios más: el parser pierde claves
repetidas antes de validar nada, una clave válida no garantiza un valor válido, y un conjunto de
ids exacto certificaba una ficha **cuyos datos no se habían escrito** —justo el caso de
W-030A13 al relanzarlo con el YAML corregido—. La rev. 1 no se conserva: no llegó a código.
**Esta rev. 2 no ha pasado ronda propia**; la segunda ronda del presupuesto es la del diff.

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

**A.2 Claves conocidas.** Tres tuplas de módulo, una sola fuente de las que leen los
constructores: `CLAVES_RAIZ` (`contrario`, `colaboradores`, `notas_html`, `cliente_propio`,
`firmante`), `CLAVES_CONTRARIO` (las once de hoy más `id_crm`) y `CLAVES_COLABORADOR` (las cinco
de hoy más `id_crm`). Cualquier otra, con su ruta (`contrario[0].apellido`) y una sugerencia si
hay una válida cercana (`difflib.get_close_matches`; si no la hay, no se inventa).

**A.3 Valores del tipo que el campo admite (H-02).**

| Campo | Admite | Todo lo demás |
|---|---|---|
| escalares de parte y `notas_html`, `firmante` | `str`, o `null` (= «no hay dato») | error con su ruta; `int`/`float` conservan la explicación del octal |
| `nombre` de cada parte | `str` **no vacío después de quitar espacios** | error |
| `id_crm` | entero, o `str` de solo dígitos | error |
| `cliente_propio` | ausente o `null` → el de siempre; `str` del catálogo `CLIENTES_PROPIOS_EV` | error (hoy `false` caía al valor por defecto por el `or`) |
| `contrario` | como en P6: ausente/`null`, mapping, lista de mappings | error con índice |
| `colaboradores` | ausente/`null`, lista de mappings | error; elemento no mapping, error con índice |
| raíz | mapping, o documento vacío (= ficha vacía) | error: `false`, `0`, `[]`, texto |

**A.4 Identidad estable antes de escribir (H-04).** Cada contrario y cada colaborador tiene que
llevar **NIF, email o `id_crm`**. Sin ninguno, la corrida se rechaza antes de la primera
escritura: `resolver_parte` identifica solo por NIF o email, así que cada relanzamiento crearía
una ficha nueva y la anterior pasaría a «sobrante» sin salida. **`id_crm` es la salida para una
parte legítima sin identificadores** —y para declarar una parte que alguien vinculó a mano—: la
corrida no busca ni crea, **lee** esa ficha por id (tiene que existir en su elemento y su `nombre`
tiene que coincidir con el del YAML, normalizado) y la vincula. Medido: hoy ninguna parte real lo
necesita.

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

**B.2 Datos por igualdad (H-03).** Para cada parte resuelta, la corrida **relee su ficha por id**
y compara **cada campo que el YAML declara no vacío** con el del CRM, con las mismas
normalizaciones que aplica la escritura:

| YAML | CRM | Normalización antes de comparar |
|---|---|---|
| `nombre`, `apellido1`, `apellido2`, `direccion`, `poblacion` | `nombre`, `1apellido`, `2apellido`, `direccion`, `poblacion` | espacios; sin distinguir mayúsculas (el CRM las guarda en mayúsculas) |
| `nif` | `nif_cif` (colaborador) / la propiedad del contrario | espacios y mayúsculas |
| `email` | `email` | espacios y minúsculas |
| `movil`, `telefono` | `movil`, `telefono1` | la de `normalize_es_phone` |
| `cp` | `cp` | espacios |
| `provincia` | `provincia` | `provincia_canonica`; si devuelve `None`, **el dato no puede llegar** y se dice |

La propiedad exacta de cada campo en el CRM se toma de `INTEGRACION_SUDESPACHO.md` y del atlas
al implementar; donde no esté documentada, **se mide antes de escribir el código**.

Tres resultados por campo: **igual**; **vacío en el CRM** (el dato no llegó: la ficha ya existía y
el campo no es de los que se completan, o se completó y no consta); **distinto** (el CRM tiene
otro valor, que no se pisa). Los dos últimos salen como `[DATO]` y hacen **fallar** la
verificación, con la instrucción de revisarlo en el CRM. Los errores al completar, que hoy solo
se registran, **pasan al veredicto**.

**Aplicado a W-030A13:** relanzar con el YAML corregido resolvería las mismas fichas por NIF, no
completaría `1apellido` (no es completable) y hoy diría «VERIFICADA». Con B.2 dice
`[DATO] clientes_contrarios id=1128 1apellido: vacío en el CRM`, y el burofax no sale con esa
ficha dada por buena.

**B.3 El veredicto.** `faltan`, `sobran` o `[DATO]` → código 1 y, para cada tipo, qué hacer sin
hacerlo: una parte sobrante legítima se añade al YAML (con `id_crm` si no tiene identificadores)
y se relanza, y si no lo es, se desvincula a mano; un dato vacío o distinto se corrige en la ficha
del CRM. **Nunca** «VERIFICADA» con algo pendiente. Los tres vacíos y todo leído → «VERIFICADA:
vínculos y datos de la ficha», con el alcance del §2.5.

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
- **`--dry-run` sigue sin leer el CRM.**

## 6. Cómo se prueba (para el plan)

Contra dobles, como `tests/test_crm_ficha_cli.py`, con un doble **con estado** donde haga falta
relanzar.

| Propiedad | El test que tiene que ponerse rojo |
|---|---|
| Sin pérdida (A.1) | claves repetidas en raíz, contrario y colaborador; alias; merge → error con línea, y **cero** writers; y `crm_colaboradores_firmas.apply` sobre un YAML con repetidas falla sin reescribir |
| Claves (A.2) | desconocida en cada nivel → error con ruta y sugerencia; varias → todas |
| Tipos (A.3) | mapping o lista en cada escalar; nombre solo espacios; `cliente_propio` `false`/`0`/`[]`/`{}`; raíz `false`/`0`/`[]` → error; **controles positivos separados** para `null` y ausente |
| Valor a su destino | cada campo con un **centinela distinto** llega a su atributo del DTO (mata el cruce de asignaciones, no solo la tupla) |
| Identidad (A.4) | parte sin NIF, email ni `id_crm` → error antes del primer writer; con `id_crm` → se lee y no se crea; `id_crm` cuyo nombre no coincide → error |
| Convergencia | dos corridas con un doble con estado: la segunda no crea otra ficha ni declara sobrante la primera |
| Vínculos (B.1) | el 653 reproducido → dos `[SOBRA]` y código 1; sobrantes en cada uno de los tres bloques, también con cero esperados; faltan y sobran a la vez; id `int` frente a `str` |
| Datos (B.2) | ficha existente con `1apellido` vacío → `[DATO]` y código 1 (el caso de W-030A13); dato distinto → `[DATO]` sin PUT; provincia no reconocida; GET o PUT de completar fallidos → al veredicto |
| Parcial (B.4) | fallar cada writer → código 1, sin «VERIFICADA», sin sobrantes inventados |
| Control positivo | conjunto y datos exactos → «VERIFICADA»; las regresiones de hoy (`[FALTA]` por cardinalidad, SIN VERIFICAR) igual |

**Mutantes**, cada uno muerto por la aserción de su propiedad y no por un arnés roto: quitar el
rechazo de repetidas; aceptar mappings en un escalar; quitar la comprobación de sobrantes;
comparar por pertenencia; quitar la verificación de datos; cruzar dos asignaciones del
constructor; que la parcial calcule sobrantes.

## 7. Rondas y modelo

Dos, por el radio de daño (`CLAUDE.md` §«Cuántas rondas»): la R1 fue sobre la rev. 1 de este
diseño, con `gpt-6-astra` · `medium`; la segunda irá sobre el diff, en la sesión que lo
implemente, con la misma fila. **La rev. 2 no tiene ronda propia**, y se declara: su primer
lector adversarial será el de la R2.

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
