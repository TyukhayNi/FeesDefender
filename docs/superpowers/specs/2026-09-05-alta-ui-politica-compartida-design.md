---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "Acciones 3 y 4 del informe de Codex 2026-09-05: el formulario de alta comparte con la CLI la política de duplicados del CRM y reutiliza expedientes existentes"
rev: "3"
---

# El formulario de alta comparte la política de la CLI

> **Rev. 3 (2026-09-05), tras la R1 adversarial sobre el diff: `REQUIERE-REVISION`, ocho
> hallazgos, los ocho confirmados.** El ALTO era mío y estaba en la frontera exacta que el §2
> declara: el remedio de la rev. 2 al «bloque que desaparecía al cambiar el radio» rearmaba el
> token de relanzamiento desde el propio render, así que **cualquier rerun** volvía a ejecutar
> el alta entera y, con el W-code editado bajo un override de `case_id` o una respuesta
> transitoria del CRM, llegaba a `create_expediente` sin clic. Lo que cambia: la decisión
> `vincular` se **guarda** y se pinta desde lo guardado sin ejecutar nada; solo los callbacks
> arman el token; el radio no preselecciona y el botón queda deshabilitado sin elección; hay
> «Cancelar»; no hay `st.stop()` en `bloquear`/`vincular`; el callback verifica por resultado
> lo que registró; `forzar` se consume al principio del alta; la CLI conserva su literal de
> `--force` y aplica la misma regla de «ya registrado» que el formulario; `decidir` colapsa
> candidatos repetidos. Adjudicación en el **§7**; voz del revisor en el acta hermana
> `…-r1-adversarial-review.md`.
>
> **Rev. 2 (2026-09-05, al implementar).** Cuatro cosas que la rev. 1 decía a medias o no
> decía, descubiertas construyéndola; lo demás no cambia:
>
> 1. **§3.2.2, reutilizar.** La rev. 1 decía «una entrada del elemento elegido». Así el
>    camino `vincular` entra en bucle cuando el frente elegido es de la **otra jurisdicción**
>    (el radio dice extrajudicial y el CRM tiene el judicial): se registra el judicial, la
>    corrida relanza, no encuentra «del elemento elegido», vuelve a la política y vuelve a
>    pedir vincular. La regla que sí es cierta: **se reutiliza cualquier expediente
>    registrado, prefiriendo el del elemento elegido**, y la pantalla dice de qué jurisdicción
>    es. Es coherente con la frontera del §2: el formulario nunca crea un segundo expediente
>    para un W-code que ya tiene uno. Helper: `expediente_local_para_alta` (con
>    `elemento_canonico`, que traduce el alias `judiciales` del frontmatter).
> 2. **§3.2.3, «la corrida sigue con el pull».** En Streamlit un botón solo es `True` en el
>    run del clic, así que ni el botón «Vincular» ni la casilla «crear igualmente» pueden
>    «seguir» sin más. Mecánica concreta: sus *callbacks* hacen el acto (registrar en
>    `_caso.md` / armar `forzar`) y dejan un **token de relanzamiento ligado al `case_id`**
>    (`_nc_relanzar`); el siguiente run lo consume como si el botón principal se hubiera
>    pulsado, `ensure_case` es idempotente, y la corrida continúa por el paso 2a (reutilizar)
>    o por la política con `forzar=True`. `forzar` se consume en esa misma corrida, salga lo
>    que salga: crear a ciegas exige un acto por intento.
> 3. **§3.1, la forma de `DecisionAltaCRM`.** `sin_comprobar` se rellena en las TRES
>    acciones (es un hecho, no una consecuencia); el prefijo de los avisos forzados es la
>    constante `alta_crm_politica.SIN_COMPROBAR`, que los dos llamadores usan para
>    distinguirlos; `motivo` no nombra flags ni widgets, porque es la misma frase en las dos
>    superficies (la CLI conserva sus mensajes de hoy, que sí nombran `--force`).
> 4. **Un cambio observable en la CLI, querido.** Con `por_wcode` **y** `sin_comprobar` a la
>    vez, `_alta_crm` antes abortaba con «no se pudo comprobar»; ahora aborta con «el CRM ya
>    tiene un expediente con el id GO» (§3.1.1: el W-code manda). Mismo código de salida,
>    otro mensaje. Ningún test lo cubría; ahora `P5` lo fija en el core.
>
> Lo verificado de verdad, y cómo, en el **§5** (bloque «Verificado el 2026-09-05»).

> **Rev. 1 (2026-09-05).** Primer corte de las acciones 3 («dar al formulario el mismo servicio
> de apertura que a la CLI») y 4 («reutilizar expedientes existentes y distinguir varios frentes»)
> del informe de Codex «Acciones para mejorar el alta de expedientes» (2026-09-05, fuera del repo). **No es la orquestación compartida
> entera:** es la parte que hoy hace daño y cabe en una entrega verificable. Lo que queda fuera
> está en el §6, con nombre.

## 1. El problema, medido en `556b8b2`

El formulario «Nuevo caso» de `streamlit_app.py` es la puerta que usan Paola y Ana. La CLI
`scripts/abrir_caso.py` es la que uso yo. Las dos dan de alta en el CRM del cliente, y **no
aplican la misma regla**:

| Garantía | CLI (`_alta_crm`, `abrir_caso.py:655-735`) | Formulario (`streamlit_app.py:2180-2215`) |
|---|---|---|
| Búsqueda de duplicado | por **W-code** en las dos jurisdicciones, más dirección y contrario como aviso (`buscar_expedientes_duplicados`, PR #272) | por **referencia exacta** (`find_expediente_by_referencia(final_case_id)`): un expediente del mismo W-code con otra referencia no se ve |
| Si no se pudo consultar | **falla cerrado** (aborta salvo `--force`, decisión de Nikolai 2026-09-04) | «Puedes continuar bajo tu responsabilidad» y sigue |
| Si ya existe | aborta y manda vincular con `register_expediente` | botón **«Confirmar de todos modos»**, que crea el duplicado |
| Reintento tras un fallo a medias | idempotente por el registro local | la casilla «continuar» **vuelve a crear**; solo la guarda de referencia exacta lo evita, y ofrece el botón de arriba |
| `case_id` inválido | error legible que nombra el flag | `ensure_case` lanza `ValueError` dentro de un `st.spinner` → **traceback rojo** de Streamlit (la validación del sumidero, PR #280, llega a la UI sin traducir) |

El coste no es teórico: un duplicado en el CRM de E&V cuesta más de deshacer que repetir el alta,
y el runbook (`[APER-36]`, `[APER-42]`) documenta W-codes con varios expedientes legítimos.

## 2. La frontera

**La decisión de crear, vincular o no tocar el CRM es una y vive en el core.** La CLI y el
formulario la consumen; ninguno la reimplementa. El formulario, además, **nunca crea un
expediente cuando el caso local ya tiene uno del mismo elemento**: continúa completándolo.

## 3. Diseño

### 3.1. `core/alta_crm_politica.py` — una función pura

```python
@dataclass(frozen=True)
class DecisionAltaCRM:
    accion: str                     # "crear" | "vincular" | "bloquear"
    candidatos: tuple[tuple[str, str], ...]   # (elemento, exp_id) hallados por W-code
    avisos: tuple[str, ...]         # dirección/contrario coincidentes; con --force, lo no comprobado
    sin_comprobar: tuple[str, ...]  # lo que el CRM no dejó mirar
    motivo: str                     # una frase para el operador

def decidir(dup: DuplicadosExpediente, *, forzar: bool) -> DecisionAltaCRM
```

Reglas, en este orden y sin excepciones:

1. `dup.por_wcode` no vacío → **`vincular`**, con todos los candidatos. Tiene prioridad sobre la
   incertidumbre: si el W-code ya está en el CRM, crear otro es el daño que esto evita, se haya
   podido consultar el resto o no.
2. `dup.incierto` y no `forzar` → **`bloquear`**. `sin_comprobar` lleva la lista literal.
3. En otro caso → **`crear`**. `avisos` = `dup.avisos`; si venía incierto y se forzó, se añade
   `SIN COMPROBAR: …` por cada criterio, para que quede escrito qué se dio por bueno a ciegas.

`_alta_crm` pasa a consumirla. Su comportamiento observable no cambia: `vincular` y `bloquear`
siguen levantando `AbortarApertura(1)` con los mensajes de hoy; los tests de
`tests/test_crm_dedup_expediente.py` siguen verdes sin tocarlos. Es el mismo movimiento que
`MEJORAS #153`: la regla sale del envoltorio y va donde los dos llamadores la comparten.

### 3.2. El formulario

Sobre el bloque `if btn_sudespacho:` de `streamlit_app.py`, en este orden:

1. **`ensure_case` con error legible.** `ValueError` → `st.error(str(exc))` y `st.stop()`. El
   sumidero garantiza que no se creó nada (PR #280); la UI solo tiene que decirlo bien.
2. **Reutilizar antes de buscar.** Si `get_case_status(final_case_id)["expedientes"]` ya tiene
   **cualquier** expediente registrado —prefiriendo el del elemento elegido y, si no lo hay, el
   de la otra jurisdicción, con aviso en pantalla (rev. 2, nota 1)—, **no se crea**: se toma su
   `id`, se informa («se reutiliza el expediente ID N ya vinculado») y se continúa con los
   pasos 3a-3c (verificación de referencia, cliente propio, colaboradores), que
   son idempotentes por construcción (`ensure_*` deduplican). Esto es «continuar una apertura
   parcial sin repetir altas» en la forma más pequeña que la hace cierta.
3. **Si no hay local, la política.** `buscar_expedientes_duplicados(w_code=ref_mls,
   direccion=direccion)` y `decidir(dup, forzar=<casilla>)`:
   - **`vincular`**: se listan los candidatos `(elemento, id)`. Con uno, un botón «Vincular este
     expediente al caso local»; con varios, un `st.radio` para elegir el frente **y** el mismo
     botón: **nunca se vinculan dos a la vez ni se elige por el usuario** (el radio arranca sin
     selección y el botón está deshabilitado hasta que la haya; hay un «Cancelar»). La decisión
     se **guarda** en `session_state` ligada al `case_id` **y al W-code**, y en los reruns se
     pinta desde lo guardado sin ejecutar el alta ni consultar el CRM; el callback del botón
     llama a `register_expediente(final_case_id, id, elemento)`, **comprueba releyendo
     `_caso.md`** que quedó registrado, y solo entonces arma el token de relanzamiento con el
     que la corrida continúa por «reutilizar». **No hay botón de «crear de todos modos»**: si de verdad hacen falta dos expedientes para un W-code,
     eso se decide en el CRM, no en un clic del formulario.
   - **`bloquear`**: `st.error` con la lista literal de lo que no se pudo comprobar y una casilla
     «Sé que este expediente no existe en el CRM: crear igualmente», cuyo callback arma
     `forzar` y el token. `forzar` se **consume al principio** del siguiente alta, salga lo que
     salga (rev. 3, H-06): un intento que muera antes de la consulta no lo deja armado. Es el pendiente explícito que el informe pide: la pantalla dice qué no se
     miró, y crear exige un acto separado.
   - **`crear`**: como hoy, con los `avisos` en `st.warning` (no bloquean: una vuelta y una bad
     debt del mismo inmueble son dos expedientes correctos).
4. El elemento a buscar y crear sigue siendo el que elige el radio «Extrajudicial / Judicial»
   del formulario; la política busca en las dos jurisdicciones porque un W-code con expediente
   judicial no debe recibir otro extrajudicial sin que alguien lo vea.

### 3.3. Lo que no cambia, a propósito

- **El alta mínima en el CRM sigue yendo antes del pull de Drive.** El informe lo señala como
  divergencia con el runbook, pero el runbook coloca **la ficha completa** (§9) después del
  trabajo documental, no el alta mínima; y el comentario del formulario justifica el orden por
  resiliencia (un cierre durante el pull no pierde el alta). Cambiarlo no cierra ningún defecto
  medido.
- `find_expediente_by_referencia` sigue existiendo para sus otros consumidores; el formulario
  deja de usarla para la guarda de duplicados.

## 4. Radio de daño y rondas

La pieza decide si se **crea** un registro en el CRM del cliente; no decide quién escribe sobre
qué copia del expediente ni puede destruir datos (vincular añade una entrada al frontmatter con
`register_expediente`, que tras `MEJORAS #146` conserva lo demás). **Una ronda, sobre el diff**,
con revisor sustituto y su independencia declarada más débil.

## 5. Mutantes

`tests/test_alta_crm_politica.py`:

| # | Entrada | Debe salir |
|---|---|---|
| P1 | `por_wcode=[(extrajudiciales, 648)]` | `vincular`, candidatos `((extrajudiciales, 648),)` |
| P2 | `por_wcode` con dos elementos distintos | `vincular` con los dos, en el orden recibido; nunca `crear` |
| P3 | `sin_comprobar=[…]`, `forzar=False` | `bloquear`, `sin_comprobar` literal |
| P4 | `sin_comprobar=[…]`, `forzar=True` | `crear`, y cada criterio aparece en `avisos` como `SIN COMPROBAR` |
| P5 | `por_wcode` **y** `sin_comprobar` | `vincular` (la prioridad del §3.1.1) |
| P6 | solo `por_direccion` | `crear`, `avisos` con «mismo direccion» |
| P7 | vacío | `crear`, sin avisos |
| P8 | `_alta_crm` con `bloquea` / `incierto` / `incierto+force` | los tests de `test_crm_dedup_expediente.py` existentes, sin modificar |
| P9 (rev. 2) | `_alta_crm` con `dup` LIMPIO y un `decidir` inyectado que dice `bloquear` | aborta: la regla vive en `decidir`, no en `_alta_crm`; y `--force` llega como `forzar` |
| P10 (rev. 2) | `expediente_local_para_alta` con alias `judiciales`, con la otra jurisdicción, con entradas rotas | prefiere el elemento pedido; si no lo hay, devuelve el que haya; ignora lo sin `id` o sin elemento reconocible |

El formulario no tiene tests (`streamlit_app.py` no se importa desde `pytest`): se verifica
**arrancándolo** con `CASOS_ROOT` apuntando a un directorio vacío y sin `SUDESPACHO_API_KEY`, que
es exactamente el camino `bloquear`, y comprobando en pantalla (1) el error legible ante un
`case_id` con `/`, (2) el bloqueo con la lista de lo no comprobado y la casilla, (3) que un caso
local con expediente registrado no ofrece crear otro. Ninguna llamada real al CRM ni al Drive.

### Verificado el 2026-09-05 (rev. 2), y cómo

**Tests.** `tests/test_alta_crm_politica.py` (19 tests: P1-P7, P9, P10 y la inmutabilidad
de la decisión) escritos primero y corridos en rojo (`ImportError`: el módulo no existía);
verdes tras implementar. La suite objetivo —ese fichero más `test_crm_dedup_expediente.py`
(sin modificar), `test_abrir_caso_cli.py`, `test_alta_v1.py` y los nueve
`test_apertura_v1_*.py`— pasó de **158** (línea base en `581286e`) a **177** verdes, 0 fallos,
contados por `--junit-xml`. Comando:
`.venv\Scripts\python.exe -m pytest -q -p no:randomly tests/test_alta_crm_politica.py
tests/test_crm_dedup_expediente.py tests/test_abrir_caso_cli.py tests/test_alta_v1.py
tests/test_apertura_v1_*.py`.

**En pantalla, arrancando la app de verdad.** `streamlit run` desde el worktree, con
`CASOS_ROOT` en un directorio vacío del scratchpad, **sin `.env`** y con toda variable
`SUDESPACHO_*` retirada del entorno del proceso (la API key estaba en el entorno de la
sesión de Windows: sin retirarla la prueba habría hablado con el tenant). Ninguna llamada
llegó al CRM ni al Drive: sin API key ni host legacy, las escrituras fallan antes del HTTP y
las lecturas devuelven `sin_comprobar`. Visto, con captura en el panel del navegador (no se
guardaron como fichero):

| # | Camino | Qué se hizo | Qué salió |
|---|---|---|---|
| 1 | `ensure_case` legible | override `BaRR1 - Calle/Prueba 1 - (W-TEST01) - Bad debt` + botón CRM | `st.error` «No se puede crear el caso: El case_id contiene caracteres que no pueden estar en una carpeta de Windows…»; **cero** ficheros en `CASOS_ROOT`; sin traceback |
| 2 | `bloquear` | mismo caso sin override, sin API key | carpeta creada; `st.error` con la lista **literal** de 4 criterios («W-code en extrajudiciales (SUDESPACHO_API_KEY no configurada)», …) y la casilla «Sé que este expediente no existe en el CRM: crear igualmente»; el texto de la página **no** contiene «Confirmar de todos modos» |
| 2b | `bloquear` → forzar | marcar la casilla | relanzamiento automático; cuatro `st.warning` «Se crea SIN COMPROBAR: …»; el alta falla en `create_expediente` por falta de clave (antes de cualquier HTTP) |
| 3 | reutilizar | `register_expediente(…, "999", "extrajudiciales")` a mano en el `_caso.md` del sandbox; botón CRM | «Se reutiliza el expediente ID 999 (extrajudiciales) ya vinculado en `_caso.md`: no se crea otro»; no hay intento de creación; 3a «Validación referencia CRM omitida — endpoint no accesible» |
| 4 | `vincular` con dos frentes | app arrancada por un envoltorio **fuera del repo** que sustituye `buscar_expedientes_duplicados` por un doble que devuelve `extrajudiciales #648` y `expedientes_judiciales #700`; caso nuevo `W-TEST02` | `st.error` con el motivo, `st.radio` con los dos frentes, botón «Vincular este expediente al caso local»; sin «crear de todos modos». **Defecto medido y corregido en la misma sesión:** al cambiar el radio, el bloque desaparecía (un rerun sin botón); ahora el camino `vincular` rearma el token de relanzamiento y el radio persiste. Elegido `#700` (la otra jurisdicción) → `_caso.md` queda con `expedientes_judiciales`/`700`, la corrida relanza y entra por **reutilizar** con la nota «Es de la otra jurisdicción…»; no se crea nada |

**No verificado en pantalla:** el camino `crear` con CRM real (crearía un expediente en el
tenant del cliente: no procede en una prueba); el pull de Drive tras vincular; el 3c de
colaboradores cuando 3b lanza algo que no es `SudespachoRelationsError` (hoy un
`ValueError` en 3b corta 3c, comportamiento que ya tenía el formulario y que esta entrega
no toca).

## 6. Lo que queda fuera, con nombre

- **La orquestación compartida completa** (acción 3): que el formulario ejecute `secuencia_v1`
  (Drive → CRM → sala de máquina bajo mutex) y muestre las fases. Requiere sacar `etapa_drive`,
  `etapa_crm`, `etapa_sala_maquina` de `scripts/abrir_caso.py` al core y resolver cómo corre una
  sala de máquina de una hora dentro de una petición de Streamlit. Va a `PLAN.md` como pendiente
  con esas dos condiciones, no como hecho.
- La ayuda del flag `--hasta` dice que al reanudar «las etapas ya hechas se saltan solas» y el
  código las repite (idempotentes). Se corrige el texto en esta misma entrega porque toca
  `abrir_caso.py` de todos modos.

## 7. Adjudicación de la revisión adversarial del diff (Claude Code sesión independiente, 2026-09-05) — REQUIERE-REVISION, remediado

- **Objeto revisado:** diff `origin/main...450d61b` del PR #285 (cinco ficheros; base `2b32c32`), commit `450d61b`
- **Ronda:** 1
- **Revisor:** Claude Code (sesión independiente), solo lectura, con sondas ejecutadas (matriz 8×2 de `_alta_crm` antes/después, diez mutantes de la política, totalidad de `decidir`); la UI no se ejecutó en la ronda
- **Informe recibido:** `2026-09-05-alta-ui-politica-compartida-r1-adversarial-review.md`
- **Hallazgos:** 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este documento y el commit que la acompaña

**Independencia, declarada más débil**: Codex sin cupo; el revisor fue un subagente de Claude Code
sin el contexto de autoría (`AGENTS.md` §«Revisor sustituto»). Lo que compensa: el ALTO viene con
la traza de código línea a línea y dos vectores concretos, y la CLI se contrastó ejecutando las
dos versiones. El código del formulario lo escribió un subagente y lo reviso yo por segunda vez al
adjudicar: la lectura del H-01 es exacta contra el diff. El digest se recalculó al recibirlo y
coincide. **La ronda no ejecutó la UI**: la rev. 3 se verifica en pantalla igual que la rev. 2
(sandbox sin credenciales, doble de `buscar_expedientes_duplicados`), y lo que no se pueda ver se
declara en el §5.

| # | Sev. | Hallazgo | Veredicto | Dónde se remedia |
|---|---|---|---|---|
| H-01 | ALTO | el bloque `vincular` rearmaba el token en cada render: cualquier rerun ejecutaba el alta entera, y con override de `case_id` + W-code editado, o respuesta transitoria del CRM, llegaba a `create_expediente` sin clic | **confirmado** (traza exacta contra el diff) | decisión guardada en `_nc_vincular_pend` (case_id + W-code) y pintada sin ejecutar; solo los callbacks arman el token; §3.2 |
| H-02 | MEDIO | el radio preseleccionaba el primer frente; «Vincular» registraba sin elección y la rama «no se eligió» era inalcanzable | **confirmado** | `index=None`, botón deshabilitado sin selección; §3.2 |
| H-03 | MEDIO | `st.stop()` con el token vivo dejaba en blanco el resto de la app y relanzaba el alta en cada interacción; sin cancelar | **confirmado** | sin `st.stop()` en `bloquear`/`vincular` (`_alta_detenida`); botón «Cancelar»; queda un `st.stop()` en el `ValueError` de `ensure_case`, declarado |
| H-04 | BAJO | el callback anunciaba «vinculado» sin comprobar que `register_expediente` escribió, y sin `try/except` | **confirmado** | relee `get_case_status` antes de anunciar y armar; errores al aviso |
| H-05 | BAJO | tres cambios observables en la CLI no declarados (literal `SIN COMPROBAR:`; con W-code+incierto+`--force` ya no se imprime la línea de «se da de alta») | **confirmado** | la CLI vuelve al literal «SIN comprobar <criterio>»; el tercero se **conserva y se declara** aquí: no anunciar un alta que no ocurre es lo correcto |
| H-06 | BAJO | `forzar` podía sobrevivir a un relanzamiento abortado antes de la consulta y consumirse en un clic posterior | **confirmado** | se consume al principio del bloque del alta |
| H-07 | BAJO | el cuerpo del §3 decía la regla vieja; «queda escrito» era solo pantalla/consola; `decidir` no colapsaba candidatos repetidos | **confirmado** | §3.2 alineado; docstring de `decidir` («queda en pantalla»); `dict.fromkeys` sobre candidatos; P11 |
| H-08 | BAJO | la CLI solo reconocía `extrajudiciales` como «ya registrado»; dos vocabularios de `element` en `_caso.md` | **confirmado** | la CLI usa `expediente_local_para_alta` (P12). Los dos vocabularios (`judiciales` del camino `crear` de la UI y `expedientes_judiciales` del `vincular`) **se dejan**: `elemento_canonico` los absorbe y cambiar lo que escribe el `crear` toca a `sync_sudespacho`/`scheduled_sync`, fuera de este alcance; queda anotado |

**Lo que el revisor verificó y resultó correcto** está en el §2 del acta: política pura, total e
inmutable; «el W-code manda» defendible porque `por_wcode` solo recibe referencias confirmadas
por `wcode_match`; diez mutantes muertos por su P-test; CLI con códigos de salida y número de
creaciones idénticos en las 16 celdas; `test_crm_dedup_expediente.py` intacto y verde; conteos del
§5 exactos; G2 verde; ninguna vía «Confirmar de todos modos». **No verificado por el revisor:** la
UI en ejecución, el consumo de `forzar` y el token (no testeables con pytest), el camino `crear`
contra el CRM real.
