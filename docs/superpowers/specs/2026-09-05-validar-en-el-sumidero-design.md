---
estado: propuesto
autor: Claude Code
fecha: 2026-09-05
cierra: MEJORAS #153, MEJORAS #154
rondas_previstas: 2
motivo_dos_rondas: "la pieza decide DONDE se deposita un expediente con PII"
---

# Validar en el sumidero, no en cada puerta

## 1. El problema, medido

`MEJORAS #148` arregló `componer_case_id`, que es la vía del **CLI de seis flags**. La R1
adversarial del 2026-09-04 destapó que **no es la única puerta**, y que la otra es la que
se usa a diario:

- **`MEJORAS #153`** — `streamlit_app.py` compone `_case_id_auto` con su propia
  interpolación y pasa `final_case_id` directo a `case_manager.ensure_case`, sin pasar por
  `componer_case_id` ni por la guarda. Con una dirección que lleve `s/n`, Windows interpreta
  el `/` como separador y la UI dice «Caso local disponible». El revisor lo reprodujo:
  `test_case_creation_rejects_multicomponent_case_id → DID NOT RAISE ValueError`.
- **`MEJORAS #154`** — el override de ruta permite **escapar de `CASOS_ROOT`**.
  `destino_de_alta` es `buscar(case_id) or (_root() / case_id)` y `path_for_ciudad` es
  `_root() / ciudad / case_id`: con un `case_id` absoluto el operador `/` de `pathlib`
  **descarta el lado izquierdo** (`Path("C:/x") / "D:/y"` → `D:/y`), y con `..` lo atraviesa.
  El revisor midió `C:\Windows` como destino compuesto.

**Quién usa cada puerta importa para el orden:** el CLI de seis flags lo usa Nikolai; la UI
de Streamlit la usan Paola y Ana, que no tocan código. Arreglar la puerta de servicio y
dejar abierta la principal es el orden equivocado.

## 2. La frontera, que es de lo que esto es un ejemplo

No son dos defectos: es **uno**, y ya se ha manifestado tres veces en dos días —
`validate_case_id` que nadie llamaba desde donde se compone el `case_id`, `clasificar` del
CLI que reconstruía el catálogo mientras `organizar` lo esquivaba, y ahora la UI que compone
su propia ruta. La propiedad mal cerrada es siempre la misma:

> **La guarda está en el envoltorio y el otro llamador la rodea.**

Su remedio no es añadir la guarda a la otra puerta —eso vuelve a arreglar el ejemplo—, sino
**ponerla en el sumidero por el que pasan todas**. El propio `case_manager.ensure_case` se
declara en su comentario «la ÚNICA puerta de alta del sistema». Si valida ahí, `#153`,
`#154` y cualquier puerta futura quedan cubiertas **sin tocar la UI**.

## 3. Diseño

Una comprobación, en `ensure_case`, **inmediatamente antes del `mkdir`** que deposita, sobre
el `case_dir` ya resuelto. Dos mitades, porque son dos propiedades distintas:

**(a) Gramática del `case_id`: un solo componente de ruta.**
Reutiliza `core.utils.exigir_sin_caracteres_de_ruta` (ya existe, extraída ayer) y añade el
rechazo de `.` y `..` como nombre completo. No se exige el formato canónico del `case_id`:
eso fue medido ayer como **una guarda más ancha que el defecto** y rompió cinco fixtures con
códigos sintéticos (`BaTEST`). La frontera es la gramática de **rutas**.

**(b) Contención: el destino resuelto vive bajo la raíz.**
`case_dir.resolve()` tiene que ser `is_relative_to(_root().resolve())`. Se compara sobre
rutas **resueltas**, no por prefijo de cadena: un `..` intermedio o un enlace simbólico
hacen que la comparación textual mienta.

**Por qué las dos y no solo (b):** la contención sola dejaría pasar
`BaRS8 - Castell s/n (W-X) - BD`, que **sí** está contenido bajo la raíz y aun así parte el
expediente en dos carpetas anidadas — el defecto original de `#148`. Y (a) sola dejaría
pasar una ruta absoluta si algún día `pathlib` deja de descartar el lado izquierdo. Cada
mitad cubre lo que la otra no.

**Lo que NO se toca:**
- `destino_de_alta` y `path_for_ciudad` siguen siendo puramente nominales («nombrar no es
  crear», dice su docstring). Validar ahí obligaría a auditar todos sus llamadores de
  lectura, y el defecto no está en nombrar: está en **depositar**.
- La UI. No hace falta y es el punto: si hubiera que tocarla, sería otra vez el ejemplo.

## 4. Radio de daño y rondas

**Dos rondas** (`CLAUDE.md` §«Cuántas rondas»): la pieza decide **dónde se deposita un
expediente con PII**, así que cae en la primera categoría. Una ronda sobre este diseño y una
sobre el diff.

Y se declara la corrección de un error propio: el 2026-09-04 clasifiqué el lote de cinco
arreglos como «una ronda, ninguna puede destruir datos de cliente», y el hallazgo CRÍTICO de
la R1 demostró que `#149` sí podía. Esta pieza se clasifica **antes** de escribirla, no
después de que un revisor lo demuestre.

## 5. Riesgo, y cómo se acota antes de escribir

El riesgo real no es que la guarda falle: es que sea **demasiado estricta** y bloquee el
alta de casos legítimos. Ayer costó cinco fixtures. Acotación **antes** de implementar:

1. **Medido el 2026-09-05 sobre el catálogo real, no razonado:** los **27** casos de todas
   las ciudades (`Barcelona`, `Madrid`, `Santander`, `Sevilla`, `Valencia`) son un solo
   componente y **ninguno** lleva carácter prohibido ni es `.`/`..`. Así que la gramática
   nueva no rechaza nada de lo que ya existe.
2. La contención se mide contra `_root()`, que es una env var: en modo local (`CASOS_ROOT`
   al Desktop tras un checkout) la raíz es la local, así que la proyección local **no** se
   rompe.
3. El mutante hermano es obligatorio: un `case_id` legítimo con paréntesis, comas, acentos
   y `º` (`"BaRS10 - Passeig Marítim, 30 - Castelldefels (08860) (W-02Z2NR) - Vuelta"`)
   tiene que **seguir pasando**. Sin él, endurecer de más pasa inadvertido.

## 6. Mutantes

| # | Mutante | Debe |
|---|---|---|
| 1 | `case_id` con `/` («s/n») desde `ensure_case` | abortar, y **no dejar ninguna carpeta parcial** |
| 2 | `case_id` con `..\..\escape` | abortar |
| 3 | `case_id` absoluto (`C:\Windows\Temp\x`) | abortar |
| 4 | `case_id` `.` o `..` | abortar |
| 5 | `case_id` legítimo con paréntesis/comas/acentos | **pasar** |
| 6 | caso que ya existe bajo su ciudad | **pasar** (contención se cumple dos niveles abajo) |

El 1 exige comprobar el **disco**, no solo la excepción: lo caro del defecto original no fue
el error, fue que dejó 170 ficheros en una ruta sombra.

## 7. Alcance explícito

Cierra `#153` y `#154`. **No** aborda el tercer defecto de `MEJORAS #67` (estructura plana de
la sala de lectura), que espera la decisión sobre el pivote a la skill, ni la reapertura de
`#149`, que necesita su propio contrato por ubicación.
