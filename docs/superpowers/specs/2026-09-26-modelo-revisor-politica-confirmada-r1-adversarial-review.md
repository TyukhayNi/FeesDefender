---
tipo: revision-adversarial
objeto: diff 7d97948..1e8924d (CLAUDE.md, AGENTS.md, PLAN.md, docs/MEJORAS_FUTURAS.md, docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md)
objeto_rev: "1"
commit: 1e8924d
ronda: "1"
revisor: Codex
modelo: gpt-6-sol
esfuerzo: high
velocidad: default
veredicto: REQUIERE-REVISION
marcador_nonce: t3xj
sha256_informe: e9bd765bbcba6488765d62b6377ae5ec80c123a3e251315ee844b5fa9a8ceeab
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §16
---

# Acta — R1 adversarial sobre el diff que confirma la política de modelo del revisor

Objeto: el **diff** `7d97948..1e8924d` de la rama `claude/politica-modelo-confirmada-38`, que registra
la decisión de Nikolai del 2026-09-26 sobre la política de modelo —confirmar `gpt-6-sol`·`high` como
habitual y dejar las filas de Astra— y deja de llamarla provisional. **Modifica el propio contrato de
revisión**, que no queda exento nunca: una ronda, y el revisor sustituto no podía cubrirla. Por la
tabla de modelo, la fila «el propio contrato de revisión, o esta misma política»: `gpt-6-sol` ·
`high` · `default`. **No es una fila del ledger de la #38**: la calibración estaba cerrada y esto no es
un encargo ordinario.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), `gpt-6-sol` · `high` — **releídos** del `turn_context` del rollout y de la cabecera del `_stdout.log`; velocidad `default` **afirmada** desde el lanzador conservado |
| Objeto | `base/` (`7d97948`) y `head/` (`1e8924d`), copias `git archive` fuera del repo, más `diff.patch` y `commits.txt` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**: 1.448 ficheros por árbol, comparados por él y por mí contra una reextracción de los dos commits desde git |
| `sha256` del informe | `e9bd765bbcba6488765d62b6377ae5ec80c123a3e251315ee844b5fa9a8ceeab` |
| Tiempos | lanzado a las 21:51:12; `INFORME.md` a las 21:59:48; `exec` salió a las 22:00:14 con `exit=0` |
| Veredicto | `REQUIERE-REVISION` — 3 hallazgos: 1 `alta`, 2 `media` |

**Lo que recibió el revisor no es exactamente lo que se archiva en el §0.** El §0 copia `MANDATO.md`
del disco, en UTF-8. Al revisor le llegó por una tubería de Windows PowerShell 5.1 cuyo
`$OutputEncoding` es ASCII, y el mensaje de usuario de su rollout lo guarda con **todo carácter no
ASCII cambiado por «?»**: 138 «?» y ninguna tilde. Los ficheros del objeto los leyó del disco,
intactos. Se midió al adjudicar; alcance y remedio, en el §16 del contrato y en `MEJORAS #279`.

## 0. Mandato, literal

# Mandato — R1 adversarial sobre el diff que confirma la política de modelo de la revisión adversarial (fila #38, FeesDefender)

## 0. Higiene y reglas

- Tu directorio de trabajo debe contener solo: `MANDATO.md`, `base/`, `head/`, `diff.patch` y
  `commits.txt`. Si hay cualquier otro fichero, **no lo leas** y decláralo en la primera línea del
  informe.
- `base/` es el commit `7d97948` (main) y `head/` es `1e8924d` (la rama del cambio), extraídos con
  `git archive`, sin `.git`. Son de **solo lectura**: si necesitas ejecutar o modificar algo, copia
  a una carpeta tuya dentro de tu directorio de trabajo. Calcula el SHA-256 de todos los ficheros de
  `base/` y `head/` al abrir y al cerrar, y di si coinciden.
- El objeto es **texto normativo**: no hay código de producción ni tests nuevos. Si quieres correr
  los guards de gobernanza (`tests/test_docs_gobernanza.py`), necesitan un repositorio git: en una
  copia tuya, `git init`, `git add -A` y un commit; Python con las dependencias:
  `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, con `--basetemp` relativo
  dentro de tu directorio. Si no los corres, decláralo SIN VERIFICAR.
- No accedas a red, a Google Drive, al CRM ni al repositorio real.

## 1. Objeto

El diff `7d97948..1e8924d` (`diff.patch`, `commits.txt`): cinco ficheros, todos texto.

**Contexto.** El 2026-09-23 se escribió en `CLAUDE.md` §«Con qué modelo se revisa» una política de
modelo para las revisiones adversariales, declarada **provisional** hasta calibrarla con cinco
encargos ordinarios (PR #395; su adjudicación es el §15 del contrato,
`head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`). El ledger
de esa calibración está en `head/PLAN.md`, sección `[SIGUIENTE-MODELO-REVISOR]`, y se completó el
2026-09-26 con cinco filas.

**La decisión que el diff registra.** El autor del diff (Claude) resumió el ledger a Nikolai
—titular del proyecto— y le recomendó, literalmente: «Mi recomendación es confirmar Sol en esfuerzo
alto como modelo habitual y dejar Astra para los casos que ya tiene asignados. Las cinco rondas
encontraron defectos reales, sin ningún hallazgo refutado, y la única omisión de lectura fue menor.
Lo que estos datos no demuestran es que Sol encuentre lo mismo que Astra, porque ningún objeto se
revisó con los dos.» Nikolai respondió «ok». **Ese resumen no mencionaba** que `CLAUDE.md` preveía
que la calibración reutilizara objetos con defectos ya confirmados, cosa que no se hizo; el diff lo
declara.

**Qué cambia el diff:** la cabecera y tres párrafos de `CLAUDE.md` §«Con qué modelo se revisa»; una
frase de `AGENTS.md`; la rev. 12 del contrato (cabecera y §4); en `PLAN.md`, la fila #38, su
sección, la cabecera del ledger y dos filas nuevas (#48 y #49); y en `docs/MEJORAS_FUTURAS.md`, el
disparador de la entrada #279 y las marcas de promoción de las #280 y #281.

## 2. Qué te pido, numerado

1. **Fidelidad a la decisión.** ¿Cambia el diff algo normativo más allá de que la política deja de
   ser provisional —la tabla de modelo, los flags de invocación, lo que registra el acta, las
   rondas, el revisor sustituto—? ¿Se ha suprimido o debilitado alguna regla al pasar texto a
   pasado? En particular: la cláusula de reutilizar objetos con defectos ya confirmados, ¿era una
   regla que seguía valiendo y desaparece sin decisión?
2. **Exactitud.** Contrasta cada cifra y cada calificación del nuevo párrafo de calibración de
   `head/CLAUDE.md` —34 confirmados, ninguno refutado, los subpuntos, `alta` en cuatro de cinco, las
   cuatro omisiones y su clasificación— con las cinco filas del ledger de `head/PLAN.md` y, si hace
   falta, con las actas que enlazan.
3. **El disparador de `MEJORAS #279`.** ¿El texto nuevo (`CLAUDE.md` y `MEJORAS`) conserva el
   significado del original o lo redefine? ¿Es cierto, según el §4 del contrato, que el acta relee
   el modelo en cada ronda de Codex? ¿Queda algún caso sin vigilar?
4. **Las promociones de #280 y #281.** ¿Se cumplen de verdad sus disparadores? ¿Sigue el diff la
   regla de promoción de `CLAUDE.md` §«Planificación y estado» (marca `[PROMOVIDO → PLAN.md]` y fila
   con referencia)? ¿Son exactas las filas #48 y #49 respecto de sus entradas, incluidas la ronda y el
   modelo que les asignan según las dos tablas de `CLAUDE.md`?
5. **Coherencia.** ¿Queda algún sitio de `head/` que siga diciendo que la política es provisional o
   que la calibración está en curso, o que contradiga el estado nuevo? ¿Sigue la cabecera de la
   rev. 12 la convención de las cabeceras de revisiones anteriores del contrato?
6. **Sobreafirmación.** ¿Presenta alguna frase nueva la confirmación como si acreditara equivalencia
   de calidad, ahorro o el acierto del reparto por filas, contra lo que el propio texto dice que el
   ledger no sostiene?
7. **El registro de la decisión.** Sabiendo que el resumen que recibió Nikolai no mencionaba la
   cláusula no cumplida, ¿registra el diff la decisión con honestidad? ¿Falta algo que debería
   constar, y dónde?
8. **`AGENTS.md`.** ¿Cambia la frase modificada alguna obligación del revisor?

## 3. Formato del informe

Escribe `INFORME.md` en tu directorio de trabajo, en castellano. Por cada hallazgo: identificador
(H-01, H-02…), **severidad** (alta · media · baja) y **coste del remedio** (trivial · acotado ·
estructural), dónde (fichero:línea en `head/`), la evidencia reproducible y el remedio que propones.
Añade una sección «Lo que intenté refutar y no pude» y otra «SIN VERIFICAR».

No encontrar defectos es un resultado legítimo: si es tu conclusión, dilo, con la evidencia de lo
que probaste. Termina el informe con una línea que contenga solo el veredicto, uno de: SHIP,
LISTA-CON-CAMBIOS, REQUIERE-REVISION, NO-SHIP.

Como último mensaje, da la ruta de `INFORME.md` y su SHA-256 calculado sobre el contenido en UTF-8,
con saltos LF y un único salto final.

## 1. Informe recibido, sin modificar (Codex, 2026-09-26)

<!-- informe-literal:inicio:t3xj -->
Había un fichero ajeno al conjunto permitido: `_stdout.log`. No lo leí.

# R1 adversarial — confirmación de la política de modelo (fila #38)

**Objeto:** `7d97948..1e8924d`, cinco ficheros de texto (`diff.patch`, `commits.txt`). **Veredicto:** la confirmación requiere corregir el registro de la decisión y la contradicción vigente en `PLAN.md`. La ampliación del disparador #279 debe quedar delimitada como tal.

## Hallazgos

### H-01 — Confirmación atribuida a Nikolai sin constancia de que conociera la excepción

**Severidad: alta · coste del remedio: acotado.** **Dónde:** `head/PLAN.md:3523-3527`; `head/CLAUDE.md:234-243`; `head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:3-7`.

**Evidencia reproducible.** `base/CLAUDE.md:224-230` decía en presente que la calibración **reutiliza** objetos con defectos ya confirmados, sin mostrar el remedio y sobre copias. Era una regla del método de estas cinco rondas, no una simple previsión de datos opcionales. Las cinco filas de `head/PLAN.md:3551-3555` son encargos vivos; `head/CLAUDE.md:234-236` y `head/PLAN.md:3525-3527` reconocen que el método no se cumplió. El mandato transcribe el resumen que recibió Nikolai: recomendó confirmar y mencionó hallazgos y límites de comparabilidad, pero **no** la desviación del método. Nikolai respondió «ok» a ese resumen. Por tanto, el diff documenta con franqueza la desviación, pero «con el ledger delante» (`PLAN.md:3523`) y «la confirmación es suya, y descansa en esos datos con estos límites» (`CLAUDE.md:242-243`) pueden leerse como si él hubiese aceptado también esa excepción. La cláusula ya no tiene una tarea futura dentro de una calibración declarada cerrada; su incumplimiento anterior no queda subsanado por pasarla a pasado.

**Remedio.** Registrar en la fila #38 y en el encabezado de la rev. 12 que el «ok» siguió a un resumen que omitió la desviación, distinguiendo **confirmación de la elección operativa** de **ratificación del método incumplido**. Presentar a Nikolai la excepción de forma expresa y registrar su decisión: confirmar pese a ella, encargar otra medición, o ajustar la política. No atribuirle una ratificación informada antes de recibirla.

### H-02 — La sección vigente del ledger sigue ordenando una calibración pendiente

**Severidad: media · coste del remedio: trivial.** **Dónde:** `head/PLAN.md:3530-3534` y título de la fila #38 en `head/PLAN.md:55`.

**Evidencia reproducible.** `PLAN.md:3523-3528` y `:3545` dicen «confirmada» y «5 de 5». Entre ambos, `:3530-3534` todavía dice «Qué queda por hacer: correr los cinco primeros encargos», «Con los cinco, Nikolai decide» y «Hasta entonces la política se sigue diciendo provisional». La fila #38 conserva además en el título «política provisional». Son texto de la cola y del ledger actuales, no una cabecera histórica. La condición «mientras no estén los cinco» de la misma fila ya es falsa, pero contribuye a la lectura desactualizada.

**Remedio.** Pasar `:3530-3534` a un registro retrospectivo de lo exigido y de su cierre, y actualizar el título de la fila #38; conservar explícita la salvedad de H-01.

### H-03 — El disparador #279 se amplía y su vigilancia se afirma con más fuerza que el mecanismo disponible

**Severidad: media · coste del remedio: acotado.** **Dónde:** `head/CLAUDE.md:219-224`; `head/docs/MEJORAS_FUTURAS.md:12807-12811`; `head/docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:154-175`.

**Evidencia reproducible.** `base/CLAUDE.md:221-222` y `base/docs/MEJORAS_FUTURAS.md:12807-12809` activaban #279 en **la primera ronda de la calibración** cuyo modelo en el acta no coincidiera con el rollout. El nuevo texto lo extiende a la primera **acta posterior de cualquier ronda de Codex**. Conserva la clase de fallo, pero cambia el alcance temporal y de objetos; no es solo redactar el mismo disparador en pasado. El §4 (`head/...design.md:160-170`) **ordena** releer `modelo` y `esfuerzo`; no establece una comprobación independiente en cada acta. Incluso prevé que, si el informe no se captura, **no hay acta** y los datos van a la ficha. El primer acta del ledger (`head/docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana-bloque1-r1-adversarial-review.md:1-12,26-28`) registra el modelo releído en prosa, pero carece de los tres campos en frontmatter. El sustituto tampoco tiene rollout de Codex (§4, `:171-175`), aunque queda correctamente fuera del nuevo alcance de #279. Sin acta capturada, o sin contraste humano del valor anotado con el rollout, la afirmación «lo vigila cada acta» de `MEJORAS:12809-12810` no garantiza detectar la discrepancia.

**Remedio.** Declarar expresamente la ampliación tras el cierre de las cinco filas y quién la decide. Redactar la vigilancia como deber de comparar, no como control que el acta realiza por sí sola; indicar que el caso sin acta se sigue en la ficha del §5 y que el sustituto no admite esa comparación. Si se quiere una garantía operativa para todas las rondas, especificar el cotejo y su evidencia, sin confundir el guard de **presencia** de #281 con uno de **verdad**.

## Lo que intenté refutar y no pude

- **Cifras y calificaciones del nuevo párrafo.** Las filas `head/PLAN.md:3551-3555` suman **6+4+6+11+7 = 34** confirmados; consignan cero hallazgos completos refutados. En la cuarta hubo **dos subpuntos de H-05 adjudicados en contra**, salvedad que `CLAUDE.md:231` sí conserva y que confirma el plan de la pieza (`head/docs/superpowers/plans/2026-09-26-sala-lectura-poblacion-316.md:168,214`). Hay `alta` en las filas 1, 3, 4 y 5; la 2 solo tiene `media` y `baja`. Las omisiones son **1 de alcance** (suite fuera del mandato, fila 2), **1 menor de mensaje no señalada por el revisor** (fila 3) y **2 aparecidas al medir el remedio** (fila 4), total cuatro. «De lectura» en `CLAUDE.md:233` describe que el revisor no señaló la de mensaje; convendría conservar también «de mensaje» para no perder precisión, pero no cambia el recuento. Las cinco actas enlazadas permiten comprobar los veredictos; la primera anota el modelo en prosa y las otras cuatro lo llevan en frontmatter. No verifiqué sus rollouts externos.
- **Reparto y obligaciones.** El diff no modifica las dos tablas de `CLAUDE.md:75-79,132-139`, los tres flags de `:189-193`, la regla de acta del §4 ni la del revisor sustituto. #280 y #281 alcanzaron sus disparadores de cierre de calibración (`MEJORAS:12830-12831,12860-12862`), se marcaron como promovidas según la convención visible en otras entradas y tienen las referencias `MEJORAS #280/#281` en `PLAN.md:68-69`. La fila #48 deja la decisión a Nikolai y exige ronda por tocar el contrato; corresponde `gpt-6-sol`·`high` si se limita a ese contrato. La #49 toca un guard que puede aparentar cobertura: una ronda y `gpt-6-astra`·`medium` según ambas tablas. Ninguna fila declara que ya esté implementada.
- **Límites de la conclusión.** `CLAUDE.md:238-250` niega expresamente equivalencia Sol/Astra, tasa aceptable de omisiones, reparto por filas probado y ahorro garantizado. La rev. 12 conserva la secuencia «Estado / Estado anterior» y el texto de la rev. 11 (`head/...design.md:3-24`), como las revisiones anteriores. La frase de `AGENTS.md:83-84` conserva la obligación de avisar dónde desborda el esfuerzo; cambia solo el propósito declarado de ese dato, de la calibración a la política. Las menciones a provisionalidad en cabeceras anteriores, en la bitácora histórica y en la justificación pasada de #280 son históricas; la contradicción actual está en H-02.

## Verificación del objeto y SIN VERIFICAR

- Al abrir y al cerrar calculé SHA-256 de **cada fichero** de `base/` y `head/` y comparé los manifiestos ordenados por ruta relativa y digest. **Coinciden**: 1.448 ficheros por árbol. SHA-256 del manifiesto `ruta<TAB>sha256<LF>`: `base/` `582a74e09be3fd9cde4596d47581f6c25c7132ed9f5b12bb94c9cde611043857`; `head/` `a42bf0810c06679dcd64968c96322a0e55a076122d5f71ecf58e5c83fc2ac249`.
- En una copia de `head/` hice un commit local con Git y corrí `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest -q tests/test_docs_gobernanza.py --basetemp=../_guard_tmp`: **46 pruebas, salida 0**. Hubo avisos de permiso al escribir la caché de pytest; no afectaron al resultado. `base/` y `head/` no se escribieron.
- **SIN VERIFICAR:** el contenido real de los cinco rollouts, los flags efectivos de sus lanzadores, los contadores de cupo y la ausencia de otras omisiones posteriores; son datos externos al paquete. Tampoco puede inferirse de estos guards la equivalencia de calidad ni que #279 detecte por sí solo una discordancia futura. No accedí a red, Drive, CRM ni al repositorio real.

REQUIERE-REVISION

<!-- informe-literal:fin:t3xj -->

## 2. Evidencia verificada por mí al adjudicar

- **Digest.** Recomputado sobre el `INFORME.md` entregado (UTF-8, LF, un único salto final):
  `e9bd765bbcba6488765d62b6377ae5ec80c123a3e251315ee844b5fa9a8ceeab`, **el mismo que declara el revisor en su último mensaje**. El crudo y el canónico
  coinciden: el fichero venía en LF y sin BOM.
- **La ronda terminó, y así se supo.** Vigía armado antes de lanzar, con fin y muerte, por
  `powershell -File`. **Dio una falsa muerte a las 21:55:52**: su `-match` no distingue mayúsculas y
  `(?m)^ERROR:` casó un `error: No private key found for …id_ed25519_signing`, que era la salida de un
  `git commit` del propio revisor en su copia (la configuración global de git firma los commits). Lo
  comprobé antes de relanzar: sin `_exit.txt`, sin `-o`, y un `codex.exe` arrancado a las 21:51:12;
  el revisor ya lo había rodeado con `git -c commit.gpgsign=false`. Rearmé el vigía con `-cmatch`,
  sin ninguna coincidencia previa en el log, y dijo `TERMINO` a las 22:00:21: `_exit.txt` con
  `exit=0` y el `-o` a las 22:00:14. Ninguna de las cuatro muertes conocidas en el log.
- **Modelo y esfuerzo, releídos:** `gpt-6-sol` · `high` en el `turn_context` de
  `rollout-2026-09-26T21-51-12-01a0df45-8da3-7952-b4d9-604bb2eb2d5e.jsonl` (`originator:
  codex_exec`, `cwd` el workdir de la ronda) y en la cabecera del `_stdout.log`. Binario sondado
  antes con los tres flags (`C:\t\sonda-sol-38-2149`): `VIVO`, sin aviso de tier. La velocidad
  `default`, **afirmada** desde el lanzador (`C:\t\politica-38-r1-2149-lanzador\_lanzar.ps1`).
- **El objeto no se tocó, y lo mido yo:** reextraje `7d97948` y `1e8924d` desde git y comparé
  fichero a fichero con las copias del revisor: **1.448 ficheros por árbol, cero diferencias**.
- **Tokens y cupo:** 1.762.539 tokens totales, 1.670.016 en caché; **entrada nueva + salida =
  92.523**. El contador semanal de la cuenta marcaba **5 %** al empezar (19:51:32 UTC) y **5 %** al
  acabar (20:00:12 UTC). En la ventana, ningún otro rollout de Codex: la sonda acabó antes y la
  sonda de codificación empezó después (20:05 UTC).
- **El mandato, tal como llegó:** el mensaje de usuario del rollout lleva 138 «?» y **cero**
  caracteres acentuados; el de la R1 de #409, 121 y cero. En los rollouts de agosto y septiembre, de
  109 rondas por CLI con mandato, **cinco lo recibieron así, todas del 2026-09-26 y lanzadas por
  mí** (filas 2 a 5 de la calibración y esta); 94 llegaron con tildes y 10 estaban escritas sin
  ellas. **Sonda de remedio** (`C:\t\sonda-utf8-38`, mismo binario y flags, con `$OutputEncoding`
  en UTF-8 antes de la tubería): el rollout guarda `acción«ñ»—` intacto y la respuesta lo devuelve
  exacto.
- **Los tres hallazgos, contra la fuente:**
  - **H-01.** El resumen que recibió Nikolai está transcrito en el §1 del mandato y no menciona la
    cláusula de reutilizar objetos con defectos conocidos; `head/PLAN.md` decía «con el ledger lleno
    delante» y `head/CLAUDE.md`, «la confirmación es suya, y descansa en esos datos».
  - **H-02.** `head/PLAN.md`, sección `[SIGUIENTE-MODELO-REVISOR]`: «Qué queda por hacer… Hasta
    entonces la política se sigue diciendo provisional», en presente, y el título de la fila #38 con
    «política provisional».
  - **H-03.** El texto original de `MEJORAS #279` ataba el disparador a «la primera ronda de la
    calibración»; el nuevo lo extendía a cualquier acta. El §4 del contrato **ordena** releer y dice
    que, sin informe capturado, no hay acta y los campos van a la ficha del §5; y el acta de la
    fila 1 del ledger (`2026-09-25-mejoras-aperturas-semana-bloque1-r1-adversarial-review.md`) no
    lleva los tres campos en el frontmatter.
- **Adjudicación:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` §16.
