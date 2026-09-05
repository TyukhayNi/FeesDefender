---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "Acciones 3 y 4 del informe de Codex 2026-09-05: el formulario de alta comparte con la CLI la política de duplicados del CRM y reutiliza expedientes existentes"
rev: "1"
---

# El formulario de alta comparte la política de la CLI

> **Rev. 1 (2026-09-05).** Primer corte de las acciones 3 («dar al formulario el mismo servicio
> de apertura que a la CLI») y 4 («reutilizar expedientes existentes y distinguir varios frentes»)
> del informe `2026-09-05-acciones-alta-expediente.md`. **No es la orquestación compartida
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
   una entrada del elemento elegido (`extrajudiciales` o `expedientes_judiciales`), **no se
   crea**: se toma su `id`, se informa («se reutiliza el expediente ID N ya vinculado») y se
   continúa con los pasos 3a-3c (verificación de referencia, cliente propio, colaboradores), que
   son idempotentes por construcción (`ensure_*` deduplican). Esto es «continuar una apertura
   parcial sin repetir altas» en la forma más pequeña que la hace cierta.
3. **Si no hay local, la política.** `buscar_expedientes_duplicados(w_code=ref_mls,
   direccion=direccion)` y `decidir(dup, forzar=<casilla>)`:
   - **`vincular`**: se listan los candidatos `(elemento, id)`. Con uno, un botón «Vincular este
     expediente al caso local»; con varios, un `st.radio` para elegir el frente **y** el mismo
     botón: **nunca se vinculan dos a la vez ni se elige por el usuario**. El botón llama a
     `register_expediente(final_case_id, id, elemento)` y la corrida sigue con el pull. **No hay
     botón de «crear de todos modos»**: si de verdad hacen falta dos expedientes para un W-code,
     eso se decide en el CRM, no en un clic del formulario.
   - **`bloquear`**: `st.error` con la lista literal de lo que no se pudo comprobar y una casilla
     «Sé que este expediente no existe en el CRM: crear igualmente», que rearma la decisión con
     `forzar=True`. Es el pendiente explícito que el informe pide: la pantalla dice qué no se
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

El formulario no tiene tests (`streamlit_app.py` no se importa desde `pytest`): se verifica
**arrancándolo** con `CASOS_ROOT` apuntando a un directorio vacío y sin `SUDESPACHO_API_KEY`, que
es exactamente el camino `bloquear`, y comprobando en pantalla (1) el error legible ante un
`case_id` con `/`, (2) el bloqueo con la lista de lo no comprobado y la casilla, (3) que un caso
local con expediente registrado no ofrece crear otro. Ninguna llamada real al CRM ni al Drive.

## 6. Lo que queda fuera, con nombre

- **La orquestación compartida completa** (acción 3): que el formulario ejecute `secuencia_v1`
  (Drive → CRM → sala de máquina bajo mutex) y muestre las fases. Requiere sacar `etapa_drive`,
  `etapa_crm`, `etapa_sala_maquina` de `scripts/abrir_caso.py` al core y resolver cómo corre una
  sala de máquina de una hora dentro de una petición de Streamlit. Va a `PLAN.md` como pendiente
  con esas dos condiciones, no como hecho.
- La ayuda del flag `--hasta` dice que al reanudar «las etapas ya hechas se saltan solas» y el
  código las repite (idempotentes). Se corrige el texto en esta misma entrega porque toca
  `abrir_caso.py` de todos modos.
