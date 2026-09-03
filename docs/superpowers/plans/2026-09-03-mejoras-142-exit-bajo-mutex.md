---
tipo: plan
objeto: "MEJORAS #142 — nadie termina el proceso sosteniendo el mutex del caso"
estado_remediacion: remediado
creado: 2026-09-03
---

# `MEJORAS #142` — nadie termina el proceso sosteniendo el mutex

**Objetivo.** Que ninguna vía de `scripts/abrir_caso.py` termine el proceso mientras se sostiene el
mutex de un caso. Había **nueve**: ocho en funciones que el modo `libre` invoca desde dentro del
bloque y una —el `--dry-run`— literalmente dentro.

## 1. La propiedad, y por qué es de la TERMINACIÓN

El `finally` de `core/casos/case_mutex.py` (`tomado`) **lanza** `MutexPerdido` si el bloque sale
limpio y solo lo **anota** con `add_note` si hay una excepción en vuelo. Eso es deliberado y
correcto para un fallo genuino —el error del cuerpo manda y la pérdida no se evapora, que es lo que
R12/H12-04 construyó—, pero con una **terminación del proceso** en vuelo falla dos veces:

1. un `Exit(0)` es una terminación **con éxito** disfrazada de excepción: se anota una pérdida de
   exclusión sobre un éxito, que es justo la mentira que el mecanismo existe para evitar;
2. y en cualquier `Exit`/`Abort`, **Typer descarta el traceback** al formatear la salida, con lo que
   la nota queda invisible incluso cuando el fallo es real.

Peor aún, `os._exit` no ejecuta ni el `finally`: no libera el lock ni diagnostica nada.

**Alcance: el modo `libre`**, que es el **modo por defecto y el que usa el equipo**. La rama `v1` se
había «remediado» en el Plan 5 sin que pudiera manifestarlo, porque sus etapas capturan `Exception`
y devuelven un resultado en vez de lanzar. Remedié donde el defecto no podía darse.

## 2. Lo construido

- **`AbortarApertura`**, excepción de dominio: lleva el código de salida y **no decide terminar**.
  Lo decide el entrypoint, fuera del bloque.
- **Cuatro** de las nueve eran validación de argumentos: corren ahora **fuera del mutex** y
  **después de resolver identidad** (el orden importa, ver el §3).
- **Cuatro** eran errores de ejecución: lanzan `AbortarApertura`.
- **El noveno**, el `Exit(0)` del `--dry-run`: marca una bandera y sale fuera del bloque.
- **El handler imprime `__notes__`** como `[AVISO]`. Esto no estaba en el diagnóstico y sí en el
  arreglo: convertir los `Exit` en excepciones de dominio **no basta**, porque siguen estando en
  vuelo y el `finally` sigue anotando. Lo que cambia es que ahora alguien **lee** la nota.
- **`tests/test_abrir_caso_exit_bajo_mutex.py`**: un guard que **deriva** el cierre transitivo de
  las funciones alcanzadas desde el bloque —17— y reconoce todas las formas de terminar.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-03) — NO-SHIP, remediado

- **Objeto revisado:** diff de `MEJORAS #142`, commit `6f249cb`
- **Ronda:** D
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-03-mejoras-142-rD-adversarial-review.md`
- **Hallazgos:** 5 recibidos — 5 confirmados, 0 refutados (1 ALTO, 2 MEDIOS, 2 BAJOS)
- **Remediado en:** los commits posteriores a `6f249cb`

**Una ronda y no dos**, por radio de daño: la pieza no decide quién puede escribir —el mutex sigue
decidiendo— ni cambia ninguna escritura; cambia **cuándo termina el proceso** y hace que una pérdida
de exclusión se diga. Y mueve validación a antes del lock, o sea **menos** tiempo bajo exclusión.

**El revisor confirmó que la corrección funcional central funciona.** Lo que tumbó fue **mi guard**,
y con razón:

| Id | Sev. | Qué era | Cómo se cerró |
|---|---|---|---|
| **HD-01** | ALTO | El guard solo reconocía `typer.Exit`. Un `sys.exit(77)` o un `raise typer.Abort()` dentro de `_alta_crm` lo dejaban **verde** — medido con dos mutaciones en memoria | Detecta `raise` **y** llamada, con `sys.exit`, `os._exit`, `SystemExit`, `Exit` y `Abort` de Typer/Click, por nombre cualificado y por último segmento. **Y cuatro pruebas negativas del propio guard, una por forma** |
| **HD-02** | MEDIO | La lista de funciones vigiladas estaba **escrita a mano**: 13 nombres frente a las **17** que el bloque alcanza. Faltaban cuatro, y tres nombres muertos se convertían en `skip` | El cierre se **deriva** por recorrido transitivo desde el cuerpo del `with`. Un nombre inexistente ahora **falla**. El anti-vacío exige 15 alcanzadas y comprueba cuatro que están a más de un salto |
| **HD-03** | MEDIO | Rescatar `__notes__` no tenía prueba de **comportamiento**: solo se comprobaba el campo `codigo` | Test que conduce `main` con una nota puesta como la pone el `finally`, y afirma el `[AVISO]` en la salida |
| **HD-04** | BAJO | Adelantar la validación cambiaba el **diagnóstico** que ve el operador: con la fuente y la identidad mal a la vez, antes decía «faltan los seis flags de identidad» y pasó a decir solo «falta `--src`» | La validación se mueve a **después de resolver identidad**, fuera del lock igualmente. Sacarla del mutex no autorizaba a reordenar lo que el operador lee. Con su test |
| **HD-05** | BAJO | Un `F401` nuevo (`textwrap` sin usar) | Desapareció al reescribir el guard. El diff **reduce** los diagnósticos de `ruff` de 8 a 6 |

**La lección, y es la tercera vez hoy: una lista escrita a mano es una lista que se queda corta.**
Pasó con los cuatro registros de ficheros de control de `00_Input` y volvió a pasar aquí. Cuando la
propiedad es «todo lo que alcanza X», el conjunto se **deriva**, no se enumera.

**Y la segunda: dos mutantes de la misma forma no son dos mutantes.** Yo había probado mi guard
mutando `typer.Exit` dos veces —dentro del bloque y en una función— y me quedé tranquilo. La
propiedad era «no terminar el proceso», y terminar tiene cuatro formas.

**Medición tras remediar: 3.896 tests, 0 fallos con dos semillas (777 y 31337).** `ruff` baja de 8
diagnósticos a 6.

## 4. Lo que este plan NO cierra

- **La rama `v1` no se toca:** su remediación del Plan 5 sigue como estaba, y el guard nuevo la
  cubre igual porque deriva el cierre desde el bloque, no desde una lista de modos.
- **`os._exit` no se puede defender del todo:** si alguien lo usa, no hay `finally` que ejecute. El
  guard lo detecta estáticamente, que es todo lo que se puede hacer desde aquí.
- **Los diez bloques del §6 y los dos abiertos del §7 del Plan 5 siguen abiertos.**
