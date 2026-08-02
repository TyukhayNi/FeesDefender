---
tipo: revision-adversarial
objeto: diff 8f98133..ec5bdc4 (rama claude/audit-log-adversarial-reviews-df1d84)
objeto_rev: 1
commit: ec5bdc4
ronda: 1
revisor: Claude Code (sesión independiente)
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: wxzp
sha256_informe: ea312248164967869a3dd8a5adf247953ebbe1cb0de41c42eb0b4c6dcbc709a2
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §14
---

# Revisión adversarial — archivo de auditoría de las revisiones, lente L2 (cobertura del guard)

## 0. Mandato, literal y en el orden de daño en que se entregó

**Reglas duras entregadas a los tres revisores, literales:**

1. SOLO LECTURA. No escribes NADA dentro del repo. No `git add/commit/checkout/stash`. No editas
   ficheros del repo.
2. Puedes ejecutar tests si rediriges toda escritura fuera del árbol:
   `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider --basetemp=<fuera del repo>`.
3. Escribes tu informe EXCLUSIVAMENTE en la ruta fijada por el encargo, fuera del repo.
4. NO das nada por bueno sin ABRIR el fichero fuente. Prohibido razonar solo sobre el diff: el diff
   dice lo que se escribió, no si es cierto.
5. REPRODUCE las mediciones, no las creas.
6. Al terminar devuelves ruta absoluta del informe + su `sha256` canónico + veredicto en una palabra.

**Objeto entregado:** el diff `8f98133..HEAD` de la rama, anclado a los cuatro commits `dffb2cb`,
`4340503`, `29163da`, `ec5bdc4`. Sin contexto de autoría y sin mi adjudicación.

**Lente L2 — ¿EL GUARD CUBRE DE VERDAD LO QUE EL DIFF DICE QUE CUBRE?** Mandato numerado y ordenado
por daño:

1. **La cobertura afirmada es real.** Retirar `_ADJ_LEGACY` ¿amplía de verdad el corpus, o hay otro
   filtro aguas arriba que deja fuera lo mismo? Enumera EXACTAMENTE qué ficheros entran hoy en el
   corpus de G7 y cuáles no, y por qué. Atención a `_es_acta()` y `_md_superpowers()`.
2. **Busca el DÉCIMO.** Barre TODO el repo buscando cualquier otra adjudicación que el disparador de
   G7 no vea: variantes de redacción, plurales, sinónimos, niveles `####`, o adjudicaciones fuera de
   `docs/superpowers/`. ¿Cuántas hay? Nómbralas con fichero y línea.
3. **¿El guard muerde?** El autor afirma 9 mutaciones sobre el corpus real, las 9 en rojo. Repite el
   ejercicio a tu manera e intenta construir un caso que DEBERÍA fallar y NO falla.
4. **`_ficha` y contigüidad.** ¿Puede prosa colarse como campo, o una ficha quedar truncada? ¿Y si un
   documento tiene dos adjudicaciones seguidas, la segunda ficha se atribuye a la primera?
5. **Regresiones.** ¿Rompe algún otro guard o test? Corre la suite y compárala con la base declarada:
   2714 tests, 0 fallos, 84 skip.
6. **La ceguera declarada.** Verifica que es real y reprodúcela. ¿Es la declaración honesta y
   completa, o hay más vías de evasión que el diff no menciona?

## 1. Informe recibido, sin modificar

<!-- informe-literal:inicio:wxzp -->
# Revisión adversarial L2 — ¿cubre G7 lo que el diff dice que cubre?

- **Objeto revisado:** diff `8f98133..ec5bdc4` de la rama `claude/audit-log-adversarial-reviews-df1d84`
  (4 commits: `dffb2cb`, `4340503`, `29163da`, `ec5bdc4`).
- **Commit del objeto:** `ec5bdc4ea7c411b1992862449964fea796de8729`.
- **Fecha:** 2026-08-02.
- **Revisor:** sesión adversarial en solo lectura, sin contexto de autoría.
- **Lente:** L2 — cobertura real del guard G7 (`tests/test_docs_gobernanza.py::test_adjudicaciones_bien_formadas`).
- **VEREDICTO: LISTA-CON-CAMBIOS**

**Resumen en tres frases.** El hecho central del diff es cierto y lo reproduje: el retrofit es
*load-bearing* —los ocho encabezados heredados habrían puesto G7 en rojo sin la lista— y la suite
cuadra exactamente con la base declarada. Lo que no se sostiene es el **enunciado de cobertura**: el
corpus de ficheros se amplió, pero el gate real de G7 no es el corpus sino un **disparador literal**,
y ese disparador tiene al menos siete vías de evasión, de las que el diff declara **una**. Y lo más
caro: **G7 no tiene guarda de no-vacuidad** —renombré los 15 encabezados reales del corpus y el
módulo entero de guards siguió **verde con cero adjudicaciones observadas**—, cuando su hermano G8 sí
la tiene (`test_g8_cubre_las_actas_que_declaran_nonce`).

**Higiene de la revisión.** No escribí nada dentro del repo. `git status` al terminar: limpio;
`HEAD` = `ec5bdc4`. Todas las mutaciones se hicieron sobre un **espejo de `docs/` + el fichero de
guards** copiado al scratchpad (`…/scratchpad/mirror/`), restaurado y verificado tras cada mutación.
La suite se corrió con `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider --basetemp=C:/Temp/l2bt` y el
`--junit-xml` al scratchpad. *(Nota de contexto, sin atribución: al abrir la sesión `git status`
mostraba un `?? .claude-final.xml` que al cerrarla ya no está; no lo creé ni lo borré.)*

**Trampa metodológica que casi me cuesta la revisión, dicha por si sirve al siguiente:** el barrido
inicial con `git grep -i -E '…revisi[oó]n adversarial…'` **perdió coincidencias reales** —entre ellas
`CLAUDE.md:16`— porque git grep trabaja en bytes y `[oó]` no casa un carácter UTF-8 de dos bytes.
Todos los barridos de este informe están rehechos en Python sobre `str`.

---

## Hallazgos

### H-01 — **A** — G7 puede quedarse **vacío en silencio**: renombré los 15 encabezados reales del corpus y los 26 tests del módulo siguen verdes

- **Fichero:** `tests/test_docs_gobernanza.py:374-394` (G7) y `:397-411` (G7-bis).
- **Evidencia (reproducida, no deducida).** Sobre el espejo, sustituí `Adjudicación de la revisión
  adversarial` → `Adjudicación de las revisiones adversariales` **solo en las 15 líneas no cercadas**
  que `_adjudicaciones()` detecta hoy (9 ficheros). Resultado:

  ```
  encabezados REALES renombrados a plural: 15 en 9 ficheros
  encabezados que G7 VE ahora: 0
  26 passed in 0.79s   (módulo completo test_docs_gobernanza.py)
  ```

  Con **cero** adjudicaciones observadas en todo el corpus, G7, G7-bis y las siete fixtures negativas
  pasan. La única cosa que sí muerde es una mutación más torpe —renombrar *también* la plantilla
  cercada del §5 del spec—, que rompe G7-bis por `len(crudos) > len(fuera)` (`assert 0 > 0`); basta
  no tocar la plantilla para que la evasión sea total y silenciosa.
- **Por qué es A y no M.** Es el modo de fallo que el propio contrato nombra («no se da por cubierto
  lo que nadie miró», spec §5) y contra el que el autor **ya escribió el remedio para G8**:
  `test_g8_cubre_las_actas_que_declaran_nonce` existe exactamente para que «el guard no quede vacío en
  silencio». G7 no lo tiene. El diff, que retira la única lista que nombraba explícitamente parte de
  la población (`_ADJ_LEGACY`, 7 ficheros), afirma cobertura total sin añadir esa contrapartida.
- **Coste de cerrarlo:** tres líneas, la forma ya existe en el fichero. P. ej. `assert
  sum(len(_adjudicaciones(t)) for _, t in _md_superpowers()) >= 15`.

### H-02 — **A** — «El corpus queda cubierto entero» es cierto de los FICHEROS y falso de las ADJUDICACIONES: 10 de las 28 filas del censo tienen encabezado que G7 vea

- **Ficheros:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:244-249`
  (§7, «el corpus de G7 es ahora todo `docs/superpowers/**/*.md` menos las actas»);
  `docs/INDICE.md:59-69` (tabla nueva); `tests/test_docs_gobernanza.py:289-298` (comentario nuevo).
- **Medido.** El corpus son **149** ficheros (154 `.md` bajo `docs/superpowers/` menos **5** actas
  detectadas por `_es_acta`). Dentro de él, G7 valida **15 encabezados en 9 ficheros**, todos
  conformes. Pero el censo que el mismo diff congela e indexa como «**el único inventario**»
  (`plans/2026-08-01-migracion-revisiones-adversariales.md`, §Censo, 28 filas) declara dónde consta
  cada identidad, y el reparto real es:
  - **10 filas** (6, 10, 14, 17, 18, 19, 21, 26, 27, 28) tienen un encabezado que G7 ve.
  - **11 filas** (7, 11, 12, 13, 15, 16, 20, 22, 23, 24, 25) constan **solo** en `PLAN.md` o
    `docs/bitacora/2026.md` — **fuera del corpus de G7 por construcción**. Verificado en el árbol:
    `PLAN.md:518-519` («Revisión de rama completa consumida… adjudicación en el §correspondiente del
    plan»), `PLAN.md:583-600` (dual workspace), `PLAN.md:380-390`.
  - **5 filas** (1-5) constan en actas cuya adjudicación lleva un encabezado que el disparador **no
    ve** (ver H-03).
  - **2 filas** (8, 9) constan en handoffs.
- **Medida complementaria del alcance real dentro del propio corpus:** `_sin_cercas` blanquea
  **28.205 de 74.217** líneas no vacías, es decir **el 38,0 %** del corpus queda invisible a G7 antes
  de mirar nada.
- **Refutación anticipada.** No sostengo que G7 *deba* cubrir `PLAN.md` ni la bitácora: el §6 dice
  con todas las letras que los guards «no exigen que un documento tenga revisión». Lo que sostengo es
  que **la frase de cobertura del §7 y la tabla del `INDICE` invitan a la lectura contraria**, y en un
  documento cuyo único producto es la verificabilidad, eso es el defecto. La frase honesta sería «el
  corpus de ficheros ya no tiene exclusiones; la población de adjudicaciones sigue sin estar acotada».

### H-03 — **A** — La ceguera declarada está bien medida pero **incompleta**: hay al menos siete vías de evasión del disparador, y una de ellas la tiene escrita el propio proyecto

- **Fichero de la declaración:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md:229-238`
  (párrafo «Y una ceguera medida, no deducida», `:229`; «cerraría esta vía», `:236`)
  («Ampliar el disparador es barato y **cerraría esta vía**»).
- **Reproducido sobre el corpus real (espejo), mutación → resultado de G7:**

  | # | Mutación | G7 |
  |---|---|---|
  | M-01 | `Adjudicación de **las revisiones** adversariales` (plural — la declarada) | **VERDE** |
  | M-02 | `Adjudicacion de la revision adversarial` (sin tildes) | **VERDE** |
  | M-03 | `adjudicación de la revisión adversarial` (minúscula inicial) | **VERDE** |
  | M-06 | `   ## Adjudicación …` (sangrado 3 espacios — ATX válido en CommonMark) | **VERDE** |
  | M-07 | encabezado *setext* (texto + `----`) | **VERDE** |
  | M-08 | `Adjudicación del veredicto adversarial` | **VERDE** |
  | M-09 | `Adjudicación de la autorrevisión` | **VERDE** |
  | M-16 | cerca ``` ``` ``` sin cerrar **antes** de la adjudicación | **VERDE** |
  | M-18 | anteponer `---\ntipo: revision-adversarial\n---` al fichero | **VERDE** |

  Y las que **sí** muerden, para que conste que el arnés funciona: `####` y `#` (encabezado fuera de
  formato), ficha con un campo menos, `veredicto`/`estado_remediacion` fuera del set, encabezado sin
  revisor/fecha, prosa entre encabezado y ficha, segunda adjudicación sin ficha propia. Además tres
  mutaciones de CONTROL diseñadas para salir rojas salieron rojas.
- **Lo que agrava el «incompleta».** La vía `Adjudicación de la autorrevisión` **no es hipótesis mía**:
  está escrita, con su aviso, en
  `docs/superpowers/plans/2026-08-01-migracion-revisiones-adversariales.md:1250` y `:1262` —
  «⚠️ **El encabezado dice «autorrevisión», no «revisión adversarial», así que NO casa
  `_RE_ADJUDICACION` ni lo detecta el disparador**»—, en el mismo fichero que este diff reencuadra,
  congela e indexa desde `docs/INDICE.md` como el único inventario. El §6 presenta el plural como *la*
  vía y afirma que ampliar el disparador «cerraría esta vía»; ampliarlo **no cierra** M-06, M-07,
  M-16 ni M-18.
- **Juicio sobre la honestidad.** La declaración es **honesta** (la ceguera existe, es la que dice, y
  se reproduce en un intento) e **incompleta** (presenta como un vector lo que es una familia, y omite
  una vía ya documentada en el repo).

### H-04 — **M** — `_ficha` comprueba **presencia de clave**, nada más: seis campos con valor vacío pasan, con basura pasan, y un duplicado contradictorio se colapsa en silencio

- **Fichero:** `tests/test_docs_gobernanza.py:328-339` (`_ficha`), `:287` (`_RE_CAMPO`), `:368-370`.
- **Evidencia.** `_RE_CAMPO = r"^- \*\*(?P<campo>[^:*]+):\*\*\s*(?P<valor>.+)$"`: con `\s*` codicioso
  seguido de `.+`, la línea `- **Ronda:**` + espacios en blanco **sí casa** (el motor retrocede y
  `.+` se queda con un espacio), y `_errores_adjudicacion` solo mira `c not in _ficha(...)`. Ejecutado:

  ```
  C-01 los SEIS campos vacíos (solo espacios)      -> VERDE
     _ficha = {'Objeto revisado': '', 'Ronda': '', 'Revisor': '',
               'Informe recibido': '', 'Hallazgos': '', 'Remediado en': ''}
  C-02 los seis campos con "-" como valor          -> VERDE
  M-11 `Ronda: platano`, `Revisor: qqqq`           -> VERDE (sobre el corpus real)
  M-12 `- **Ronda:** 1` + `- **Ronda:** 7`         -> VERDE (el dict se sobrescribe, gana el último)
  M-13 veredicto `SHIP, sin-cambios` sobre un cuerpo que narra un NO-SHIP -> VERDE
  ```
- **Matiz que juega a favor del diff:** el §6 dice explícitamente que los guards «no juzgan el
  contenido de la adjudicación», así que M-11/M-13 son **fuera de alcance declarado**. Los que **no**
  están cubiertos por esa declaración son el campo vacío (una ficha de seis campos en blanco es
  formalmente conforme) y el campo duplicado con valores contradictorios: eso es forma, no contenido.
  Coste de cerrarlo: cambiar `\s*(?P<valor>.+)$` por `\s*(?P<valor>\S.*)$` y detectar clave repetida.

### H-05 — **M** — La contigüidad de `_ficha` no es tal: salta blancos sin límite **y salta bloques cercados enteros**, con atribución cruzada demostrada

- **Fichero:** `tests/test_docs_gobernanza.py:328-339`; docstring «campos contiguos tras el
  encabezado (salta blancos)».
- **Evidencia.** `_ficha` opera sobre `_sin_cercas(txt)`, donde las líneas cercadas son `""`; el bucle
  `while … not lineas[i].strip()` las trata como blancos y **las atraviesa**:

  ```
  C-03 ficha a 40 líneas en blanco del encabezado                        -> VERDE
  C-04 encabezado real + ```markdown <ejemplo con su ficha> ``` + ficha  -> VERDE
       _ficha del encabezado real recoge los 6 campos que están DESPUÉS de la cerca
  C-05 encabezado + cerca de código + ficha                              -> VERDE
  ```
  Es decir: **la ficha de un ejemplo cercado, o la de una sección posterior, puede quedar atribuida
  al encabezado anterior** sin que nada lo señale.
- **Contra-verificación (la pregunta del mandato).** El caso «dos adjudicaciones seguidas y la ficha
  de la segunda atribuida a la primera» **no ocurre**: probado en M-19, M-21 y C-14, la línea `##` de
  la segunda no casa `_RE_CAMPO`, corta el bucle y la primera sale con `ficha incompleta` → **ROJO**.
  El vector real es el de la cerca intermedia (C-04/C-05), no el de dos encabezados consecutivos.
- **Y prosa entre encabezado y ficha sí muerde** (M-14 → ROJO): la prosa **no** se cuela como campo.
  Lo que se cuela es la ausencia de barrera cuando lo intermedio es una cerca o líneas en blanco.

### H-06 — **M** — La única exclusión que queda es de **CONTENIDO y autodeclarada**, justo lo que el comentario que el diff conserva dice no querer

- **Fichero:** `tests/test_docs_gobernanza.py:347-348` (`_es_acta`) y `:289-298` (comentario nuevo).
- **Evidencia.** `_es_acta` = `txt.startswith("---") and "tipo: revision-adversarial" in txt[:600]`.
  Mutación M-18: anteponer esas tres líneas a
  `specs/2026-07-29-sandwich-firma-falso-positivo-design.md` saca el fichero **entero** de G7 →
  VERDE. Hay **50 ficheros del corpus que ya empiezan por `---`**: están a una línea de desaparecer.
- **La contradicción, que es lo sustantivo.** El comentario que el diff escribe en el hueco de
  `_ADJ_LEGACY` defiende la polaridad —«si hiciera falta excluir algo, se excluye **por NOMBRE** en
  una lista que **solo puede encoger**»— mientras la exclusión que de hecho gobierna el corpus es por
  **contenido**, no está en ninguna lista, **puede crecer sin tocar el test** y la decide el propio
  fichero excluido. Retirar `_ADJ_LEGACY` no crea el agujero, pero deja la doctrina escrita al lado
  de un mecanismo que la incumple.
- **Riesgo accidental, medido:** en el spec del contrato la cadena `tipo: revision-adversarial`
  aparece en el **offset 5987** (umbral: 600) y el fichero no empieza por `---`, así que hoy no pasa
  nada. Pero es la plantilla del §4 dentro de una cerca: dos ediciones ordinarias —añadir frontmatter
  al spec y subir el §4— bastarían para que **el propio contrato** saliera del corpus en silencio.
- **Efecto colateral ya presente:** de los 9 ficheros `*-adversarial-review.md`, `_es_acta` reconoce
  **5**; los 4 de julio (sin frontmatter) están **dentro** del corpus de G7 pese a ser actas. Hoy no
  rompe nada porque sus encabezados no disparan, pero el docstring de G7 («MENOS las actas») describe
  algo que el código solo cumple para 5 de 9.

### H-07 — **M** — Fila nueva del `INDICE` que sobredeclara: «Las actas: … literal y **con su digest**. Nueve al 2026-08-02»

- **Fichero:** `docs/INDICE.md:68` (línea añadida por `29163da`).
- **Medido, fichero a fichero:**

  | fichero | `_es_acta` | `sha256_informe` | `marcador_nonce` (⇒ lo verifica G8) |
  |---|---|---|---|
  | `2026-07-23-emails-atomizados-…-adversarial-review.md` | no | no | no |
  | `2026-07-26-gobernanza-indice-adversarial-review.md` | no | no | no |
  | `2026-07-27-cableado-atomize-…-adversarial-review.md` | no | no | no |
  | `2026-07-29-feesdefender-dual-…-adversarial-review.md` | no | no | no |
  | `…-adversariales-adversarial-review.md` (r1) | sí | sí | no |
  | `…-adversarial-review-r2.md` | sí | sí | no |
  | `…-adversarial-review-r3.md` | sí | sí | no |
  | `…-adversarial-review-r4.md` | sí | sí | **sí** |
  | `…-diff-r5-codex-bbd1fba-adversarial-review.md` | sí | sí | **sí** |

  «Nueve» es correcto como cuenta de ficheros; «con su digest» vale para **5**, y **G8 solo recomputa
  2**. Cuatro de las nueve no tienen ni frontmatter. En una tabla que existe para decir «dónde está el
  rastro y qué garantía tiene», pegar la garantía al número es exactamente la clase de afirmación que
  este contrato existe para impedir. La fila de handoffs de la misma tabla («Cinco al 2026-08-02»)
  **sí** cuadra: verificados los 5 `handoff-*-codex-*.md`.

### H-08 — **M** — «Los **nueve** encabezados de adjudicación del corpus casan el formato canónico»: el corpus tiene **quince**

- **Fichero:** `docs/superpowers/plans/2026-08-01-migracion-revisiones-adversariales.md:72-74` (marco
  añadido por `29163da`).
- **Medido.** G7 detecta y valida **15** encabezados en 9 ficheros: 8 heredados + los 2 del noveno
  partido (`13.1`/`13.2`) + **5 nativos** del propio spec de gobernanza (§9-§13). «Nueve» cuenta las
  *identidades heredadas*, no los encabezados del corpus, y la frase dice literalmente «del corpus».
  Es el mismo fichero que el `INDICE` acaba de promover a inventario único, así que la precisión
  importa más que de costumbre.

### H-09 — **M** — Cuatro ficheros del corpus tienen hoy un número **impar** de líneas ` ``` `: su cola es invisible a G7 y nada lo avisa

- **Medido.** `plans/2026-06-12-search-expedientes-rest.md` (37), `plans/2026-06-18-organizar-sala-lectura-y-triaje-drive.md`
  (37), `plans/2026-06-18-sala-lectura-unica.md` (51), `specs/2026-06-12-search-expedientes-rest-design.md` (5).
  Ninguno oculta hoy una adjudicación —lo comprobé comparando encabezados crudos contra los vistos por
  `_adjudicaciones`, y las únicas diferencias son las deliberadas: 9 plantillas cercadas en el plan de
  migración y 1 en el spec del contrato—. Pero la mutación M-16 demuestra que una cerca desbalanceada
  **aguas arriba** apaga el resto del fichero para G7, y este corpus ya tiene cuatro casos vivos de esa
  condición. Es el mismo agujero que H-01 hace silencioso.

### H-10 — **B** (menor) — `_sin_cercas` solo entiende ` ``` `, no `~~~`

- **Fichero:** `tests/test_docs_gobernanza.py:305-319`.
- **Evidencia.** C-06: una adjudicación **completa envuelta en `~~~`** es vista y validada como si
  fuera real (`disparados=1`). Dirección segura (falso positivo, no hueco de cobertura): una plantilla
  escrita con `~~~` pondría G7 en rojo sin motivo. Se anota por completitud, no bloquea.

### H-11 — **B** (menor) — El §6 del spec publica el regex «con `re.MULTILINE`»; el código no lo lleva

- **Ficheros:** spec `…-design.md:196-202` vs. `tests/test_docs_gobernanza.py:278-283`.
- Funcionalmente equivalente (el regex se aplica línea a línea con `.match`), pero el spec presenta ese
  bloque como *el código del guard*. Deriva preexistente a este diff; se anota porque la rev. 9 se
  apoya en ese mismo §6 para declarar la ceguera.

---

## Respuesta punto por punto

### 1. ¿La cobertura afirmada es real? ¿Hay otro filtro aguas arriba?

**Sí amplía de verdad, y sí hay otro filtro aguas arriba.** Las dos cosas.

**Que amplía, verificado contra la fuente y no contra el diff.** Cargué el módulo de guards de `HEAD`
y lo corrí sobre el **texto de `8f98133`** (recuperado con `git show`, sin tocar el árbol). Resultado:
**7 ficheros fallarían G7** sin la lista, con **8 encabezados** rotos, y son exactamente los 7 de
`_ADJ_LEGACY`. Los motivos reales, para que conste que el retrofit no fue cosmético:
`'## 10. Adjudicación de la revisión adversarial'` (sin revisor ni fecha), `'— veredicto NO-SHIP…'`,
`'— NO EJECUTABLE, remediado'` (veredicto con espacio), `estado_remediacion 'resuelto' fuera del set`,
`'## 20. Adjudicación de la revisión adversarial (rev. 2)'`, y **los 8 sin ficha**. Hoy los 15
encabezados del corpus salen limpios. **La lista encogió a cero legítimamente.**

**El corpus, enumerado exactamente.**

| | ficheros | por qué |
|---|---|---|
| `docs/superpowers/**/*.md` en disco (`_SP.rglob`) | **154** | glob de sistema de ficheros, no `git ls-files`: incluiría un `.md` sin trackear |
| menos actas (`_es_acta`) | **−5** | `…-adversarial-review{,-r2,-r3,-r4}.md` y `…-diff-r5-codex-bbd1fba-adversarial-review.md` |
| **escaneados por G7** | **149** | |
| de ellos, con al menos un encabezado disparado | **9** | 15 encabezados, 0 errores |

**Los dos filtros aguas arriba que el enunciado no menciona:**

1. **`_es_acta` (H-06).** Es una **exclusión por contenido, autodeclarada**: `startswith("---")` +
   `"tipo: revision-adversarial"` en los primeros 600 caracteres. Saca el fichero **entero**.
   Reproducido (M-18). 50 ficheros del corpus ya empiezan por `---`. Y solo reconoce **5 de las 9**
   actas: las 4 de julio, sin frontmatter, están dentro del corpus pese a que el docstring dice que
   las actas quedan fuera.
2. **`_sin_cercas` + `_adjudicaciones` (H-03, H-09).** El gate efectivo no es el corpus: es
   `ln.startswith("#") and "Adjudicación de la revisión" in ln` **sobre el texto ya blanqueado**. Eso
   descarta el **38,0 %** de las líneas no vacías del corpus (28.205/74.217) antes de mirar nada, deja
   fuera cualquier encabezado sangrado o *setext*, y una cerca impar apaga todo lo que venga después.

**Conclusión del punto 1.** La ampliación es real y medible. La frase «el corpus queda cubierto
entero» es verdadera sobre *ficheros* y engañosa sobre *adjudicaciones*: de las 28 filas del censo que
el propio diff promueve a inventario único, **10** tienen encabezado que G7 vea (H-02).

### 2. El DÉCIMO — barrido de todo el repo

**Sin hallazgo fuera de `docs/superpowers/` en forma de encabezado canónico**, y **con hallazgo dentro
del corpus**: hay **al menos siete** adjudicaciones más que el disparador no ve. Barrido: los **1.025
ficheros trackeados** (`.md`, `.py`, `.txt`, `.yaml/.yml`, `.json`), en Python sobre `str`, buscando
en toda línea de encabezado los términos sin acentos `adjudicac`, `revision adversarial`,
`revisiones adversariales`, `veredicto`, `autorrevis`, `code review`, `revision de rama`,
`rama completa`, `red team`, `adversarial review`. **139 encabezados candidatos**, de los que **25**
disparan G7 y **114 no**.

**Adjudicaciones reales que el disparador NO ve** (fichero:línea, todas verificadas leyendo la sección):

| # | Fichero:línea | Encabezado | Situación |
|---|---|---|---|
| 1 | `docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md:120` | `## Adjudicación (Claude, 2026-07-27)` | Adjudicación completa (rondas 1 y 2 = censo 1 y 2). El fichero **está en el corpus** (`_es_acta` = no). Invisible. |
| 2 | `docs/superpowers/specs/2026-07-26-gobernanza-indice-adversarial-review.md:388` | `## Adjudicación` | Adjudicación por fila con tabla veredicto/acción (censo 3). En corpus. Invisible. |
| 3 | `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md:34` (+`:52`) | `## Tabla de adjudicación`, `## Evidencia verificada (adjudicación, no confianza)` | Censo 4 y 5. En corpus. Invisible. |
| 4 | `docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md:440` | `## 13. Revisión adversarial (2026-07-13) — correcciones aplicadas y gates en vivo` | Adjudicación embebida en un spec, con lista de correcciones aceptadas. Precorte, pero **en el corpus**. Invisible. |
| 5 | `docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-catalogo-funciones.md:187` | `## Guardas y hallazgos adoptados (revisión adversarial, 4 rondas)` | Adjudicación de 4 rondas. Precorte, en corpus. Invisible. |
| 6 | `docs/superpowers/plans/2026-07-21-preclasificacion-sala-lectura.md:817`; `…/2026-07-21-robustez-velocidad-sala-lectura-tdd.md:1601`; `…/2026-07-22-…-9-16.md:1107` | `## Auto-revisión` (×3) | Autorrevisiones. En corpus. Invisibles. |
| 7 | `docs/superpowers/handoffs/handoff-2026-07-27-sala-maquina-ocr-gaps.md:16` | `## Veredicto de la revisión (2026-07-27, sesión Claude Code)` | Postcorte, en corpus. Invisible. |

**Y el que más pesa, porque no es mío:**
`docs/superpowers/plans/2026-08-01-migracion-revisiones-adversariales.md:1250`, dentro de cerca, la
plantilla que el propio proyecto redactó: `## Adjudicación de la autorrevisión (Claude, 2026-07-27) —
SIN-VEREDICTO, remediado`, seguida en `:1262` del aviso explícito de que **no la detecta el
disparador**. Es una décima variante **conocida y escrita**, en el fichero que este diff congela,
enmarca e indexa, y que el §6 de la rev. 9 no menciona al declarar la ceguera.

**Encabezados `####`:** **no** son una vía de evasión — comprobado (M-04): `#{2,3}\s+` no casa y G7
reporta «encabezado fuera de formato». Igual `#` de nivel 1 (M-05). Aquí el guard sí muerde.

**Fuera de `docs/superpowers/`:** ninguna adjudicación con encabezado canónico. `CLAUDE.md:16`,
`AGENTS.md:56-76`, `docs/GOBERNANZA_FUENTES_VERDAD.md:182` y `docs/INDICE.md` son doctrina o vista
derivada. Pero **sí hay adjudicaciones en prosa**, sin encabezado, en `PLAN.md` (p. ej. `:517-519`,
`:583-600`) y en `docs/bitacora/2026.md`: son el hogar único de **11 de las 28 filas del censo**, y
están fuera del alcance de G7 por diseño (H-02).

### 3. ¿El guard muerde? — 21 mutaciones sobre el corpus real + 15 casos sintéticos

Sí muerde donde el diff dice, y **no muerde en nueve sitios más**. Metodología: espejo fuera del repo,
G7 corrido sobre **todo** el corpus tras cada mutación, restauración y verificación de baseline verde
tras cada una; **tres mutaciones de control** diseñadas para salir rojas salieron rojas (borrar un
campo, veredicto fuera del set, estado fuera del set) — sin eso no me creería el resto.

**Muerden (9):** `####` · `#` · prosa entre encabezado y ficha · segunda adjudicación sin ficha ·
encabezado sin revisor/fecha · ficha con un campo menos · veredicto fuera del set · estado fuera del
set · ficha con sangría de lista · separador `---` entre encabezado y ficha.

**No muerden y deberían, o al menos deberían constar (9):**
plural · sin tildes · minúsculas · encabezado sangrado · setext · sinónimos («del veredicto», «de la
autorrevisión») · cerca desbalanceada previa · `tipo: revision-adversarial` antepuesto · **los seis
campos con valor vacío**.

**No muerden y está declarado que no** (fuera de alcance por el §6, lo anoto sin computarlo como
defecto): valores basura, veredicto incoherente con el cuerpo.

**Caso construido que DEBERÍA fallar y no falla, el que me parece más caro:** el del H-01 — no una
adjudicación mal formada, sino **la desaparición de todas**. 15 encabezados renombrados, 0 vistos, 26
tests verdes.

### 4. `_ficha` y contigüidad

- **¿Puede prosa colarse como campo?** **No.** M-14 y C-11 lo confirman: cualquier línea que no case
  `- **X:** v` corta el bucle y la ficha sale incompleta → ROJO. Al contrario de lo que temía el
  mandato, la prosa **posterior** a la ficha tampoco molesta: el bucle ya paró.
- **¿Puede una ficha quedar truncada?** **Sí, y muerde bien**: basta una línea intermedia (prosa,
  `---`, sangría de lista) para perder el resto de campos → ROJO. C-10 y C-11 lo demuestran. Esto es
  laxitud a la inversa (frágil, no ciego) y no lo cuento como defecto.
- **¿Dos adjudicaciones seguidas, la segunda ficha atribuida a la primera?** **No.** M-19, M-21 y C-14:
  el `##` de la segunda no casa `_RE_CAMPO`, corta el bucle, y la primera sale con ficha incompleta.
- **Lo que sí encontré (H-05):** la contigüidad **no existe** frente a blancos ni frente a cercas.
  Una ficha a 40 líneas en blanco cuenta (C-03), y **una cerca intermedia es transparente**: en C-04
  el encabezado real absorbe los seis campos que hay *después* de un bloque ```` ```markdown ````
  con un ejemplo dentro. Ahí sí hay atribución cruzada real.
- **Y el hueco de valor (H-04):** `- **Ronda:**` seguido solo de espacios **casa**, con valor `''`.
  Una ficha con los seis campos en blanco es formalmente conforme.

### 5. Regresiones

**Sin hallazgo.** Suite completa sobre `HEAD`, con escritura fuera del árbol
(`PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider --basetemp=C:/Temp/l2bt`), contada por JUnit XML y no
por el resumen de consola:

```
tests=2714  failures=0  errors=0  skipped=84  time=107.7s
```

**Cuadra exactamente con la base declarada (2714 / 0 / 84).** Los 84 son 77 skips ambientales
(lentos, Ollama, fixture SaRS1 con PII, blocklist) + 7 `xfail` conocidos de
`test_repository_cli_defectos.py`. G1-G6 y G8 verdes; G7-bis
(`test_g7_no_se_autodetecta_en_la_plantilla_del_spec`) verde con crudos=6 / vistos=5. Las citas nuevas
del `INDICE` y del `GOBERNANZA` a specs, plans y a
`handoff-2026-08-01-identidad-segmento-codex-review{,-2}.md` resuelven bajo G2 (la expansión de llaves
da los dos ficheros, y ambos existen); los globs con `*` los descarta `_RE_PLACEHOLDER`, como está
previsto. **Usé `--basetemp` corto a propósito**: con uno largo cae
`test_resumen_cuenta_por_estado` por `RUTA_OFFICE_MAX`, que es defecto conocido del test y no de este
diff.

### 6. La ceguera declarada

**Real, reproducida, honesta — e incompleta.** Tres cosas separadas:

1. **¿Es real?** Sí. Mutación M-01 sobre el corpus real: `### 13.1. Adjudicación de **las revisiones
   adversariales** (Codex, 2026-08-01) — NO-SHIP, remediado` → G7 **VERDE**, adjudicación fuera de
   formato y nadie se entera.
2. **¿Pasó como dice?** Sí, contra git: en `8f98133` el encabezado de
   `specs/2026-08-01-identidad-segmento-bundle-design.md` era
   `## 13. Adjudicación de las revisiones adversariales`, el fichero **no** estaba en `_ADJ_LEGACY`, y
   la suite estaba verde. La narración del §6 se sostiene.
3. **¿Es completa?** **No** (H-03). Presenta como *una vía* lo que es una familia de al menos siete, y
   afirma que «ampliar el disparador… cerraría esta vía» cuando ampliarlo no cierra el encabezado
   sangrado, el setext, la cerca desbalanceada ni el `tipo: revision-adversarial`. Omite además la
   variante `Adjudicación de la autorrevisión`, que **ya estaba escrita y avisada** en
   `plans/2026-08-01-migracion-revisiones-adversariales.md:1262`, en el fichero que este mismo diff
   reencuadra e indexa. Y omite lo que las convierte a todas en gratis: **G7 no comprueba que vea
   nada** (H-01).

**La decisión de no ampliar el disparador me parece bien fundada** —el encargo no lo incluía, y
ampliar por cuenta propia es la deriva que causó el recorte—. Lo que no me parece bien es que la
declaración se quede corta describiendo lo que se deja abierto: la frase «cerraría esta vía» le vende
al siguiente lector una reparación de un renglón para un agujero que tiene siete puertas.

---

## Lo que NO conseguí refutar

Lo digo porque un revisor que no lo dice está vendiendo humo:

- **El retrofit es load-bearing y está bien hecho.** Los 8 encabezados heredados habrían puesto G7 en
  rojo por motivos concretos y verificados uno a uno contra `8f98133`; hoy los 15 del corpus casan.
- **`_ADJ_LEGACY` cubría exactamente los 7 ficheros que fallaban.** Ni uno de más.
- **La suite cuadra al test con la base declarada.** Sin regresiones en G1-G6 ni en G8.
- **El guard muerde donde el diff dice que muerde**, incluido `####`, que era una de las sospechas del
  mandato y resultó infundada.
- **La ceguera del plural se declaró antes de que nadie la buscara**, con su evidencia y sin adornarla.
- **La fila de handoffs del `INDICE` («Cinco al 2026-08-02») es exacta**, y la frontera acta/handoff
  del §3.1 declara su precio (cinco informes sin digest, «y nunca lo tendrán») sin maquillarlo.

## Cambios que pediría antes de mergear

Ordenados por daño; ninguno exige rediseño.

1. **H-01** — Añadir a G7 la guarda de no-vacuidad que G8 ya tiene. Tres líneas.
2. **H-02** — Reescribir la frase de cobertura del §7 y la tabla del `INDICE`: «el corpus de ficheros
   ya no tiene exclusiones» ≠ «las adjudicaciones están cubiertas». Decir cuántas filas del censo
   quedan fuera del alcance de G7 y por qué (11 en `PLAN.md`/bitácora, 5 en actas, 2 en handoffs).
3. **H-03** — Completar la declaración del §6 con la familia entera de vías (con la de la
   autorrevisión, que ya estaba escrita en el repo) y corregir «cerraría esta vía».
4. **H-07** — Corregir la fila de actas del `INDICE`: nueve ficheros, cinco con digest, dos
   verificados por G8.
5. **H-04/H-05** — Si se toca el parser: `\S.*` en el valor, detección de clave repetida, y no
   atravesar cercas al buscar la ficha.
6. **H-08** — «quince», no «nueve», o decir «los nueve heredados».
<!-- informe-literal:fin:wxzp -->

## 2. Evidencia verificada al adjudicar

Verificado por mí, contra la fuente y no contra el diff, antes de adjudicar. Detalle
hallazgo por hallazgo en el §14 del objeto; aquí lo que reproduje con ruta y línea:

- **`2955f65` consta** en `docs/superpowers/handoffs/handoff-2026-07-27-vista-procesal-codex-informe.md:34`
  («El spec se revisó desde la rama local `claude/intake-crm-sudespacho-a7fc5a` (`2955f65`)») y el
  commit existe en git. Mi ficha decía `commit: no registrado`: declaraba ausente lo que la fuente
  que ella misma cita registra.
- **`docs/bitacora/2026.md:146` nombra al revisor** de la rama del sándwich: «La de rama (opus)
  devolvió LISTA CON CAMBIOS con 3 Important». Mi ficha decía `no registrado`.
- **La tabla del §10-bis de historial citado da 8 B0 + 3 A + 2 M** contando su columna `Sev`
  (`9`,`1`,`3,4,5,6`,`2,7` → 8 B0; `8`,`10`,`11` → 3 A; `13`,`12` → 2 M), no el «7 B0 + 4 A + 2 M»
  que escribí «de la tabla». El total, 13, sí cuadra por las dos vías.
- **G7 era vacuo**: mutando los 15 encabezados del corpus al plural, `_adjudicaciones` observa 0 y
  `_errores_adjudicacion` devuelve 0 errores → módulo entero verde. Reproducido con los propios
  helpers del guard y luego sobre el árbol real.
- **Las actas no tienen garantía uniforme**: 9 ficheros `*-adversarial-review*.md`, 5 declaran
  `sha256_informe`, y solo 2 llevan `marcador_nonce` (las únicas que G8 recomputa). Mi fila del
  `INDICE` prometía digest en las nueve.
- **El corpus de G7 tiene 15 encabezados en 9 ficheros**, no nueve.
- **Los 5 Minor del sándwich de rama no tienen destino**: sin entrada en `docs/MEJORAS_FUTURAS.md`
  ni en `PLAN.md`. Contra los que sí lo tienen y verifiqué existiendo y diciendo lo afirmado:
  `MEJORAS #107`, `#101`, `#102`, `#103`.
- **`plans/2026-08-01-migracion-revisiones-adversariales.md:1262` ya avisaba** de que un encabezado
  de autorrevisión no lo detecta el disparador. Está en el fichero que yo reencuadré.
- **Suite** tras la remediación: `python -m pytest tests/test_docs_gobernanza.py` → 27 tests, y la
  mutación al plural sobre el corpso real ahora sale ROJA con diagnóstico.

**Independencia, sin maquillaje.** Los tres revisores son sesiones de Claude Code sin contexto de
autoría, no Codex. Misma familia de modelo que el autor: **puntos ciegos compartidos**, y sin la
tensión de interés que en rondas anteriores hizo que Codex argumentara contra la ampliación de sus
propios permisos. Compensado con tres lentes en paralelo y mandatos que prohíben dar nada por bueno
sin abrir el fichero. Registrado como `Claude Code (sesión independiente)` y **nunca como «Codex»**,
según `AGENTS.md` §«Revisor sustituto».
