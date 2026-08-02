---
tipo: revision-adversarial
objeto: diff 8f98133..ec5bdc4 (rama claude/audit-log-adversarial-reviews-df1d84)
objeto_rev: 1
commit: ec5bdc4
ronda: 1
revisor: Claude Code (sesión independiente)
veredicto: REQUIERE-REVISION
marcador_nonce: qtsw
sha256_informe: 2998a168c333c9b31826d1d9868070696d35b63a9d3f9ec67efc83e38a6db928
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §14
---

# Revisión adversarial — archivo de auditoría de las revisiones, lente L1 (fidelidad a la fuente)

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

**Lente L1 — FIDELIDAD DEL REGISTRO A LA FUENTE.** Es la de más daño: este trabajo construye un
registro de auditoría, y un número inventado ahí es el fallo exacto que el registro existe para
impedir. Mandato numerado y ordenado por daño:

1. **Recuentos de `Hallazgos`.** Para CADA una de las nueve fichas: abre el documento, cuenta los
   hallazgos de su tabla/prosa, y contrasta con el recuento escrito. ¿Cuadra? ¿Hay algún número que
   NO se pueda derivar de lo que el documento publica, es decir, inventado o estimado? El autor
   declara una regla: «se copia lo que el documento publica; donde no publica desglose y dice que
   aceptó todo, el total va a confirmados». ¿La aplica de forma consistente en las nueve, o cambia
   de criterio para que cuadre?
2. **Buckets mal asignados.** Los buckets son confirmados/rebajados/refutados/escalados/sin
   verificar. ¿Algún hallazgo que el documento describe como REFUTADO o rechazado está contado como
   confirmado, o al revés? Mira con especial cuidado: cableado plan, sandwich plan §1061,
   email-atomize §11, sandwich design §9. ¿El registro hace parecer al autor MÁS deferente con el
   revisor de lo que fue?
3. **`escalados` con destino.** El diff afirma que los escalados están verificados en destino
   (MEJORAS #107; #101/#102/#103; 5 Minor anotados). Ábrelos. ¿Existen? ¿Dicen lo que se afirma?
4. **`Remediado en`.** Cada uno cita una rev., un PR y/o un hash. Verifícalos contra el encabezado
   del documento, `git log`, `git show`, la bitácora y `PLAN.md`. ¿Algún PR o hash que no exista o
   no corresponda?
5. **`Revisor`, `fecha`, `commit`, `Ronda`, `Objeto revisado`.** ¿Alguno afirma más de lo que consta?
   ¿Hay algún `no registrado` que SÍ constaba en alguna fuente, o algún valor concreto que NO consta?
6. **Cambios de estado.** Vista procesal §10 pasa a `parcial` y sandwich plan de rama de «aplicados»
   a `parcial`. ¿Justificados por la fuente? ¿Y hay alguno que DEBERÍA ser `parcial`/`pendiente` y se
   dejó en `remediado`?

## 1. Informe recibido, sin modificar

<!-- informe-literal:inicio:qtsw -->
# Revisión adversarial L1 — fidelidad del registro a la fuente

**Objeto:** diff `8f98133..HEAD` de `claude/audit-log-adversarial-reviews-df1d84`
(4 commits: `dffb2cb`, `4340503`, `29163da`, `ec5bdc4`).
**Commit revisado:** `ec5bdc4`.
**Fecha:** 2026-08-02.
**Lente:** L1 — fidelidad del registro a la fuente. Solo lectura; ninguna escritura en el repo.

**VEREDICTO: REQUIERE-REVISION**

El grueso de la aritmética cuadra y se puede derivar de lo que cada documento publica: comprobé
los diez recuentos abriendo el documento y, donde existía, el informe original. Pero hay **un campo
de identidad fabricado** en la ficha de vista procesal (H-01), **una afirmación de validez en bloque
sobre el censo** que es falsa en las tres columnas que vouchea y que el mismo diff promueve a «único
inventario» (H-02), y **una regla rota en el commit que la escribe** (H-03). Los tres son baratos de
arreglar; ninguno es de diseño. Pero son de la clase exacta que este artefacto existe para impedir,
y H-02 exige re-verificar columnas, no reescribir una frase.

---

## Hallazgos

### H-01 · B0 · `Objeto revisado` de vista procesal §10 nombra la revisión que la revisión produjo, y dice `no registrado` de un commit que sí consta

`docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:673`

```
- **Objeto revisado:** `docs/…/2026-07-27-vista-procesal-05-procedimiento-design.md` v3, commit `no registrado`
```

**(a) «v3» es el remedio, no el objeto.** El encabezado del propio documento, líneas 6-7:
`_**v3 — reescrita tras la revisión adversarial de Codex (veredicto NO SHIP, 25 hallazgos).**_`.
v3 es lo que la revisión produjo. Lo confirma el árbol: en `2955f65` —el commit que el informe
declara como estado revisado— el encabezado del spec **no lleva ninguna marca de versión**
(`git show 2955f65:docs/…-design.md | head`), y la marca `v3.1` solo entra a `main` con `12c8a91`.
Declarar el objeto como «v3» hace imposible reconstruir qué vio el revisor, que es la única función
del campo.

**(b) El commit consta, y consta en el fichero que la propia ficha cita.**
`docs/superpowers/handoffs/handoff-2026-07-27-vista-procesal-codex-informe.md:34`:
«El spec se revisó desde la rama local `claude/intake-crm-sudespacho-a7fc5a` (`2955f65`)». Resuelve
en git (`2955f65 2026-07-27 docs: regla de origen a tres ramas + promover el .doc de MEJORAS #61`).

No es una regla del autor, es una omisión: en las otras dos fichas con informe capturado sí minó el
commit de la fuente — `f965716` y `05d985f` de los `commit_revisado` de los handoffs de
identidad-segmento, `8d9c96c` del acta de dual. Solo aquí escribió `no registrado`.

El contrato (§5) admite `no registrado` para *no inventar lo que no consta*; no ampara lo contrario,
que es declarar ausente lo que la fuente citada registra.

---

### H-02 · A · «Sigue valiendo el resto: objeto, ronda, revisor y "dónde consta hoy"» es falso en las tres columnas, y el mismo diff promueve el censo a «único inventario»

`docs/superpowers/plans/2026-08-01-migracion-revisiones-adversariales.md:67-70` (commit `29163da`)
y `docs/INDICE.md:66` («**El único inventario** de las revisiones adversariales desde el
2026-07-23: 28 filas, una por identidad, con su fuente»).

El marco declara muertas dos columnas (`Clase`, `Tarea`) y **avala expresamente el resto**. Lo que
mide la fuente:

| Qué avala | Qué encontré |
|---|---|
| **Revisor**, fila 19 (`sandwich firma (rama)`) = `no registrado` | `docs/bitacora/2026.md:146`: «La de rama (**opus**) devolvió **LISTA CON CAMBIOS** con 3 Important» |
| **Revisor**, fila 16 (`email atomize enumeración (rama, PR #155)`) = `Codex` | `docs/bitacora/2026.md:162`: «Codex sobre el plan devolvió NO-SHIP…; **la revisión de rama con opus** devolvió otro NO-SHIP con cuatro Important» |
| **«Dónde consta hoy»**, fila 7 → `docs/bitacora/2026.md:138` | `:138` es prosa de flujo git («`gh pr merge --squash --delete-branch` desde un worktree falla su limpieza local»). El 44º cierre con PR #151 está en `:166` |
| filas 20 y 21 → `docs/bitacora/2026.md:70` | `:70` es «**No se tocó la historia.** Bitácora, las cuatro specs…», del cierre de `agy` |
| fila 15 → `docs/bitacora/2026.md:134` | `:134` es «Los siete defectos, reproducidos con evidencia y NO arreglados» |
| filas 22-24 → `docs/bitacora/2026.md:150` | `:150` es las erratas del sándwich |
| fila 16 → `PLAN.md:383-386` | son las líneas de PR #57 (layout `00_Input` por lotes) |
| fila 19 → `plans/2026-07-29-sandwich-firma-falso-positivo.md:1089` | el encabezado está hoy en **:1099** — lo desplazó **este mismo diff** al insertar la ficha de 10 líneas |
| fila 14 cita el estado «`NO-SHIP, resuelto`» de email-atomize §11 | **este diff** cambió ese token a `remediado` |

La deriva de las líneas de bitácora no es accidental: `CLAUDE.md` fija que el bloque de cierre se
escribe «reciente primero», así que **cualquier** puntero por número de línea a `docs/bitacora/`
caduca en el cierre siguiente. El marco lo avala sin comprobarlo, y el `INDICE` lo eleva a fuente
única. El marco sí acota las notas de conformidad de las filas 14, 17 y 26-28 — pero las llama
«notas de conformidad» y la de la fila 14 no lo es: es el token de estado, que quedó falso.

---

### H-03 · A · Cinco «escalados» sin destino, contra la regla que el mismo diff escribe

`docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md:1105-1109`

```
- **Hallazgos:** 6 confirmados · 0 rebajados · 0 refutados · 5 escalados · 0 sin verificar
- **Remediado en:** PR #164 (`aaf7dc1`), los 6; los 5 Minor quedan anotados aquí sin aplicar
```

La regla, añadida en `ec5bdc4`
(`…-gobernanza-revisiones-adversariales-design.md:259`): «los `escalados` se declaran **solo con
destino verificado**».

El destino de estos cinco es «**aquí**» — la propia sección de un plan terminado. Busqué destino
real: `grep -n "citas_a_revision\|firma_sin_cerrar\|conservacion_tokens" docs/MEJORAS_FUTURAS.md
PLAN.md` no devuelve ninguna entrada para Minor 3, 4, 5, 6 ni 8. Contraste dentro del mismo corpus:
sandwich design §9 escala a `MEJORAS #107` y dual §20 a `#101/#102/#103`, y **los cuatro existen y
dicen lo que se afirma** (verificados uno a uno, ver punto 3 del mandato).

O no son escalados —son confirmados sin remediar, que es justo lo que el estado `parcial` ya
declara— o la regla se incumple en el commit que la promulga. En el registro, «escalado» sugiere
seguimiento; aquí no lo hay.

---

### H-04 · A · `Revisor: no registrado` donde la bitácora del proyecto sí lo registra

`docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md:1099,1103`

```
## Adjudicación de la revisión adversarial de rama completa (no registrado, 2026-07-29) — …
- **Revisor:** no registrado — este documento no lo nombra
```

`docs/bitacora/2026.md:146` lo nombra: «La de rama (**opus**)». El matiz «este documento no lo
nombra» es literalmente cierto y por eso no es invención — pero el campo del encabezado, que es lo
que un auditor lee, dice `no registrado` a secas. Y el autor **usa la bitácora como fuente de
revisor** en el mismo corpus: fila 7 del censo, `Opus`, con puntero a `docs/bitacora/2026.md:138`.
La regla del contrato es «no se inventa lo que no consta», no «lo que no consta en este fichero».

---

### H-05 · M · «Los 13 son los 7 B0 + 4 A + 2 M **de la tabla**» — la tabla dice 8 B0 + 3 A + 2 M

`docs/superpowers/specs/2026-07-30-historial-citado-localizable-design.md:246`

Recuento sobre las filas de la tabla de §10-bis (`:250-260`), columna `Sev`:

- **B0:** `9`, `1`, `3, 4, 5, 6`, `2, 7` → **8**
- **A:** `8`, `10`, `11` → **3**
- **M:** `13`, `12` → **2**

Total 13, que es el número de la ficha y es correcto. Lo falso es la atribución: el desglose
7 B0 + 4 A + 2 M viene de la prosa de la línea siguiente (`:248`), no de la tabla, y la tabla la
contradice. El documento publica dos desgloses incompatibles y el retrofit certificó uno como
«de la tabla» sin contarla.

---

### H-06 · M · La ficha del PLAN del sándwich cuenta 9 hallazgos; su tabla publica 10

`docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md:1067` (8 confirmados · 1
rebajado = 9). La tabla de `:1074-1085` tiene las filas `#1`-`#9` **más** una décima sin numerar:

> `| — | — | Nota de su §3: el test 4 no comprobaba `reconstruido_de` | **ACEPTADO y verificado**: el campo existe (`model.py:80`, `render.py:66`) — no era un detalle inventado. Añadida la aserción de procedencia |`

Es un hallazgo del revisor («Nota de **su** §3»), aceptado y remediado, y no entra en ningún bucket.
El 9 sale de la prosa («4 bloqueantes + 4 altos + 1 menor. Ocho aceptados, uno parcialmente
refutado»), que es defendible bajo la regla de copiar — pero entonces falta la exclusión razonada.
El propio autor sí la escribe en el caso gemelo: historial §10-bis excluye su fila `—` diciendo
«el defecto de `core/linker.py::_all_md` no cuenta porque lo encontré yo auditando, no el informe».
Aquí no hay motivo, y el motivo no puede ser el mismo: esta fila **sí** es del informe.

---

### H-07 · M · `rebajado` no está definido en el contrato y se aplica a dos formas idénticas con buckets distintos

- `plans/…sandwich…:1069`: «El rebajado es el **#7**, que este documento llama "parcialmente
  refutado": se refuta el método […] y se acepta la conclusión» → **1 rebajado**.
- `specs/…vista-procesal…:685`, fila H8: «BLOQ | **Acepto parcial**, ALTA» → **confirmado**
  (`0 rebajados`).

La misma forma —hallazgo aceptado en parte— en dos buckets. Y en vista procesal hay además cinco
rebajas de severidad explícitas (H2, H7, H8, H9 de BLOQ a ALTA; H19 de ALTA a MEDIA) que van todas a
`confirmados` con `0 rebajados`. El contrato §5 define el vocabulario cerrado de `veredicto` y
`estado_remediacion` pero **no** el de los cinco buckets de `Hallazgos`, así que el criterio no es
auditable. No acuso de amañar: acuso de que el campo no significa lo mismo en dos fichas del mismo
corpus, y eso lo hace inservible para comparar.

---

### H-08 · A · `sin verificar` = 0 en las diez fichas, incluidas las que publican cobertura ausente

Las diez líneas (`grep "^\- \*\*Hallazgos:\*\*"` sobre los ocho ficheros) suman
**104 confirmados · 1 rebajado · 2 refutados · 9 escalados · 0 sin verificar**.

Cero, en un corpus donde:

- El informe de vista procesal dedica una sección entera a lo que no pudo verificar —
  `handoff-2026-07-27-vista-procesal-codex-informe.md:265-273`, «**Premisas del spec que NO he podido
  verificar**», **siete** premisas — y el propio §10 remata: «**Nada que dependa de haber ejecutado
  la suite queda verificado por esa revisión**» (`…-design.md:713`).
- email-atomize §11 titula un párrafo «**Lo que la revisión dejó como UNVERIFIED y sigue así**»
  (`…-design.md:499`).

Se puede sostener que el bucket cuenta *hallazgos* y esas son *premisas*. Pero el contrato no lo
dice en ninguna parte, y la doctrina que el propio §5 invoca dos líneas más abajo —«Un revisor que
no corre no refuta: deja sin verificar»— apunta a cobertura, no a hallazgos. Con 0/10 el campo no
transporta información y la ficha se lee como cobertura completa donde la fuente declara huecos.
Es el bucket que más carga doctrinal tiene y es el único que nunca se usa.

---

### H-09 · M · «Las dos divergencias son de remedio, no de hallazgo»: una es de hallazgo

`docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md:464`.

La segunda divergencia (claves del evento: versionar en vez de duplicar) sí es de remedio. La
primera no:

> «**`_enlaces/` no puede contener `.eml`.** **Su tabla lo daba por posible**; está descartado por
> medición: los `.eml` rescatados de un enlace se depositan **a primer nivel**
> (`_deposita_mensaje_rescatado`, `email_export.py:536-556`).» (`:495-497`)

Eso refuta una premisa fáctica de la tabla del revisor, no elige otro remedio. Ficha: `0 refutados`.

Misma forma en `specs/2026-07-29-sandwich-firma-falso-positivo-design.md:320`: «**Matices donde no
seguí al revisor:** propuso que **todos** los trozos disparadores eran firma; mi medición dice que
en 5 de 7 portadores lo son y en 2 no» → `0 refutados`. En los dos casos el registro deja al autor
**más deferente** de lo que la prosa muestra. La prosa sigue ahí, así que el daño es acotado; pero
la respuesta directa a la pregunta 2 del mandato es: sí, en estos dos.

---

### H-10 · M · «Los nueve encabezados de adjudicación del corpus»: son quince

`docs/superpowers/plans/2026-08-01-migracion-revisiones-adversariales.md:73-74`.

Medido con los propios helpers del guard (`_md_superpowers` + `_adjudicaciones`, excluyendo actas):
**15** encabezados fuera de cerca — cableado 1, sandwich plan 2, vista 1, email 1, dual 1, sandwich
design 1, historial 1, **identidad 2**, y **5** en el propio spec de gobernanza.

«Nueve» es el número de *adjudicaciones* retrofitadas (los ocho heredados + el noveno de
identidad-segmento), no de encabezados: el noveno se partió en dos (§13.1 y §13.2), así que el
retrofit tocó **diez** encabezados, y la frase además borra los cinco que ya cumplían. Nada de esto
es grave; sí es un recuento escrito en el documento que certifica recuentos.

---

### H-11 · M · El criterio de `estado_remediacion` no es el mismo en las diez

El diff acierta al bajar dos encabezados (pregunta 6 del mandato, primera mitad — **ambos
justificados por la fuente**):

- vista procesal §10 → `parcial`: la tabla dice H23 «§6 (**pendiente** de fixture)» y H24
  «**pendiente**: `PLAN.md:181`». ✔
- sandwich rama → `parcial` desde «aplicados»: «Minor 3,4,5,6,8 … **ANOTADOS, no aplicados**». ✔

La segunda mitad de la pregunta sí tiene respuesta:

- **historial §10-bis = `remediado`** con un hallazgo aceptado y no aplicado: fila 12, «**ACEPTADO
  como deuda medida** […] La batería jurídica **queda pendiente**» (`…-design.md:260`). Es
  exactamente la situación que en el sándwich obliga a `parcial`.
- **identidad §13.1 = `remediado`** apoyándose en «lo que quedó a medias, **rev. 3**» para B0-1,
  A-1, A-4, A-5 y M-2. El documento **no publica** ese cierre: §13.2 mapea IDs nuevos (`N-*`), y el
  §12 que el `consumido_por` del handoff señala como mapa de la 1ª pasada hoy se titula «Radio de
  la migración (medido)». Es una afirmación derivada, contra la regla «no se deriva ni se estima».
- **identidad §13.2 = `remediado`** con «N-B0-4 deja la **pieza B bloqueada**». Aquí sí lo doy por
  bueno: el remedio de un hallazgo de spec es una sección de spec, y §10 existe y lo documenta.

---

### H-12 · M · Tres punteros nuevos citan como vigente la regla que el mismo diff deroga

`specs/…vista-procesal…:679` («El informe vive entre los handoffs por decisión de Nikolai del
2026-07-30, `docs/GOBERNANZA_FUENTES_VERDAD.md` §5»), `specs/…identidad-segmento…:299-302` (idem) y
`docs/INDICE.md:67` (fila `handoff-*-codex-*.md`, estado **vigente**, misma cita).

En el mismo diff, `GOBERNANZA_FUENTES_VERDAD.md:184-189` reescribe ese §5 para decir lo contrario
hacia delante, y `…-gobernanza-…-design.md:66-87` (§3.1) traslada la regla al contrato con conjunto
**cerrado** de cinco. Ninguno de los tres punteros menciona §3.1. La fila del `INDICE` es la peor de
las tres: está indexada por un **glob**, marcada «vigente», y se lee como norma de archivo viva para
cualquier informe futuro de Codex.

Atenuante comprobado: el §5 reescrito sí conserva y acota la decisión de 2026-07-30, así que quien
siga el puntero llega a la versión corregida.

---

### H-13 · M · «rev. 1» declarado sobre dos planes que no publican revisión

`plans/2026-07-28-cableado-atomize-sala-maquina.md:1222` y
`plans/2026-07-29-sandwich-firma-falso-positivo.md:1063`. Abrí las dos cabeceras: ninguno de los dos
planes lleva marca de revisión (el del sándwich cita la **rev. 2 de la SPEC**, que es otra cosa). Es
una lectura razonable —son planes de una sola versión— pero es derivada, y el valor que el contrato
reserva para eso es `no registrado`. Daño bajo; lo anoto por simetría con H-01, donde la derivación
va en la dirección contraria y sí hace daño.

---

### H-14 · M · SIN VERIFICAR: «porque cuenta solo esa severidad»

`plans/2026-07-28-cableado-atomize-sala-maquina.md:1228`: «La prosa del párrafo siguiente dice
"4 bloqueantes" **porque cuenta solo esa severidad**». La tabla de «Aceptados y corregidos» no tiene
columna de severidad y el informe **no se capturó**, así que no hay forma de comprobar cuáles cuatro
de los seis eran bloqueantes. Es plausible y probablemente cierto; queda **sin verificar**, y está
escrito como hecho en el documento que prohíbe estimar.

---

## Contestación al mandato, punto por punto

### 1. Recuentos de `Hallazgos`

Abrí los diez (son **diez** fichas bajo nueve adjudicaciones, no nueve: sandwich plan lleva dos e
identidad-segmento lleva dos). Contados contra el documento y, donde existía, contra el informe:

| Ficha | Ficha dice | Contado en la fuente | ¿Cuadra? |
|---|---|---|---|
| vista procesal §10 | 25 conf. | H1…H25 en `handoff-…-codex-informe.md:65-263` | ✔ |
| email-atomize §11 | 6 conf. | 6 filas de la tabla de bloqueantes | ✔ (ver H-08, H-09) |
| dual §20 | 16 conf. + 3 esc. = 19 | IDs del acta: 4 `B0-*` + 10 `A-*` + 5 `M-*` = 19 | ✔ |
| sandwich design §9 | 3 conf. + 1 esc. | 3 filas + el hallazgo fuera de alcance | ✔ (ver H-09) |
| historial §10-bis | 13 conf. | 13 IDs en la tabla | ✔ total; ✘ desglose (H-05) |
| cableado plan | 6 conf. + 2 ref. | 6 «Aceptados y corregidos» + 2 «Rechazados, con motivo» | ✔ |
| sandwich plan (PLAN) | 8 conf. + 1 reb. = 9 | 9 filas numeradas **+ 1 sin numerar** = 10 | ✘ (H-06) |
| sandwich plan (rama) | 6 conf. + 5 esc. = 11 | 3 Important + 8 Minor = 11 | ✔ total; ✘ bucket (H-03) |
| identidad §13.1 | 10 conf. | «rev. 1: 2 B0 + 5 A + 3 M» (cabecera del spec) y «los 10 hallazgos» (`destino:` del handoff) | ✔ |
| identidad §13.2 | 11 conf. | 11 filas `N-*`; «rev. 2: 4 B0 + 5 A + 2 M» | ✔ |

**¿Algún número no derivable de lo publicado?** Ninguno de los diez totales. Todos salen de una
tabla o de una frase del propio documento. Lo que no se deriva son **campos**, no cifras: el
`v3`/`no registrado` de H-01, el `rev. 3` de identidad §13.1 (H-11) y el «7 B0 + 4 A + 2 M **de la
tabla**» de H-05.

**¿Aplica la regla de forma consistente?** La regla de *copiar el total* sí, en las diez. La regla
de *repartir en buckets* no: `rebajado` cambia de significado entre fichas (H-07), `escalado`
cambia de exigencia (H-03), `refutado` no recoge dos refutaciones fácticas publicadas (H-09) y
`sin verificar` está muerto (H-08). El autor no cambia de criterio *para que cuadre* —los totales
cuadran con cualquiera de los criterios—: cambia de criterio porque el contrato no define ninguno.

### 2. Buckets mal asignados

Revisé los cuatro que el mandato señala:

- **cableado plan («Rechazados, con motivo»):** correcto. Los 2 refutados son exactamente los dos
  rechazados (`except Exception` / notas de `vistas` a stderr). **Sin hallazgo.**
- **sandwich plan §1061 («uno parcialmente refutado»):** el #7 va a `rebajado`, no a `confirmado`.
  No infla la deferencia; sí abre H-07 por incoherencia con vista procesal H8.
- **email-atomize §11 («dos puntos donde no seguí» / «UNVERIFIED»):** H-09 y H-08.
- **sandwich design §9 («Matices donde no seguí»):** H-09.

**¿Hace el registro parecer al autor más deferente de lo que fue?** Sí, en dos sitios y de forma
acotada: las dos refutaciones fácticas de H-09 no aparecen en `refutados`. La prosa las conserva,
así que no hay ocultación — hay pérdida en la parte machine-readable de la ficha. Ningún hallazgo
descrito como refutado o rechazado está contado como confirmado, ni al revés.

### 3. `escalados` con destino

Abrí los cuatro destinos:

- **`MEJORAS #107`** (`docs/MEJORAS_FUTURAS.md:4215`): existe y dice lo que se afirma — test vacuo
  `test_seg_html_token_conservacion_no_inventa`, «Detectado 2026-07-29 por la revisión adversarial
  de Codex sobre la spec del falso positivo de `_sandwich`», «el **cuarto** test vacuo». ✔
- **`MEJORAS #101`** (`:4012`): «hallazgo **M-4** de la revisión adversarial de la arquitectura
  dual», residuos `_reingesta_*`. ✔
- **`MEJORAS #102`** (`:4041`): «hallazgo **M-5** de la misma revisión», `errors="replace"`. ✔
- **`MEJORAS #103`** (`:4070`): «hallazgo **M-3** de la misma revisión», `CaseWorkspace` en
  `st.session_state`. ✔ El §20.4 escala M-3, M-4 y M-5; el conjunto casa.

- **Los 5 Minor del sandwich de rama: NO tienen destino.** Ver H-03.

### 4. `Remediado en`

Verificados uno a uno contra `git log`/`git show` y contra la cabecera del documento:

| Cita | Resultado |
|---|---|
| PR #137 (`12c8a91`) | `12c8a91 2026-07-27 Vista procesal 05_Procedimiento: diseño (2 revisiones adversariales) + arreglo N6 del checkin (#137)` ✔ |
| PR #175 (`31b5943`) | `31b5943 2026-07-30 El historial citado no atribuible, localizable (MEJORAS #105, pieza 1 de #109) (#175)` ✔ |
| PR #164 (`aaf7dc1`) | `aaf7dc1 2026-07-29 La firma no es una respuesta intercalada… (#164)` ✔ (citado dos veces, las dos correctas) |
| PR #151 | `c845a01 … Cableado de la atomizacion de correo en la sala de maquina (resto de MEJORAS #68.a) (#151)` ✔ |
| `8d9c96c` | existe, `spec: arquitectura dual de expediente activo`; coincide con el `commit` del acta ✔ |
| `f965716` | existe, `docs(spec): identidad posicional del segmento de bundle`; coincide con `commit_revisado:` del handoff 1 ✔ |
| `05d985f` | existe, `docs(spec rev.2): la identidad del segmento no puede ser un ordinal regenerable`; coincide con `commit_revisado:` del handoff 2 ✔ |
| «rev. 2 de este documento» (email-atomize, sandwich design, dual) | los tres documentos están en rev. 2 ✔ |
| «rev. 3» (identidad, las dos fichas) | el documento está en rev. 3 ✔ para §13.2; **no publicado** para los cinco «a medias» de §13.1 → H-11 |

**Ningún PR ni hash inexistente o mal atribuido.** Es la parte más limpia del diff.

### 5. `Revisor`, `fecha`, `commit`, `Ronda`, `Objeto revisado`

- **Fechas:** las diez casan con el `creado:` del handoff, el `Fecha:` del acta o el cierre de
  bitácora correspondiente. **Sin hallazgo.**
- **Ronda:** las diez casan con el censo y con los handoffs (`pasada_anterior:` en los dos que son
  segunda ronda). **Sin hallazgo.**
- **Revisor:** un `no registrado` que **sí** constaba → H-04.
- **Commit:** un `no registrado` que **sí** constaba → H-01(b). Los otros seis `no registrado` son
  legítimos: sus informes son «no capturado — llegó por chat» y no hay fuente que los fije.
- **Objeto revisado:** un valor concreto que **no** consta y que contradice la cabecera del propio
  documento → H-01(a). Dos `rev. 1` derivados sobre planes sin marca → H-13.

### 6. Cambios de estado

- **vista procesal §10 → `parcial`:** justificado. La tabla marca H23 y H24 como pendientes. ✔
- **sandwich rama, «aplicados» → `parcial`:** justificado y honesto — el token viejo daba por
  cerrados cinco Minor que la propia tabla declara «ANOTADOS, no aplicados». ✔ Es el cambio de
  mayor valor probatorio del diff.
- **A la inversa:** historial §10-bis debería ser `parcial` con el mismo criterio (fila 12 aceptada
  y pendiente), e identidad §13.1 sostiene `remediado` sobre un cierre no publicado. Ver H-11.

---

## Lo que intenté refutar y no pude

Lo digo porque un informe que solo lista lo roto engaña sobre dónde está el riesgo.

- **La ceguera de G7 que el §6 declara: REPRODUCIDA.** Mutando `### 13.1. Adjudicación de la
  revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado` de vuelta a
  `### 13.1. Adjudicación de las revisiones adversariales` y quitando la ficha,
  `_errores_adjudicacion` devuelve `[]` y el disparador cuenta 1 (el de §13.2). El guard se queda
  verde con una adjudicación fuera de formato. La declaración del §6 es exacta, y también lo es
  «lo que pasó con el §13 durante el día que estuvo en `main`»:
  `git show 8f98133:…identidad-segmento-bundle-design.md` trae `## 13. Adjudicación de las
  revisiones adversariales`, y el spec entró a `main` en `fbb1cac` (#187) el 2026-08-01, un commit
  antes de que `8f98133` (#188) trajera G7.
- **G7 no es vacuo.** Borrando `- **Ronda:** 1` de vista procesal, muerde:
  `ficha incompleta, faltan ['Ronda']`.
- **Y G7 no puede cubrir esta lente, medido:** cambiando `25 confirmados` por `999 confirmados`,
  `_errores_adjudicacion` devuelve `[]`. Está declarado en el §6 («no juzgan el contenido de la
  adjudicación»), y conviene que conste al lado de los hallazgos: **toda la capa L1 es manual, sin
  red**.
- **`docs/INDICE.md`:** «Nueve [actas] al 2026-08-02» ✔ (nueve `*-adversarial-review.md` en
  `specs/`); «Cinco [handoffs] al 2026-08-02» ✔ (`handoff-*-codex-*.md`); «28 filas» ✔.
- **§3.1, «dos de los cinco entraron el 2026-08-01, un commit antes de que mergeara este
  contrato»:** ✔ exacto. Los dos handoffs de identidad-segmento entran en `fbb1cac` (#187) y el
  contrato en `8f98133` (#188).
- **`_ADJ_LEGACY` retirada vacía y corpus sin exclusiones:** ✔ verificado en el código y por
  ejecución.
- **Suite:** `2714 tests, 0 failures, 0 errors, 84 skipped` (JUnit XML). El único fallo que vi al
  principio —`tests/test_migrar_nombres_informe.py::test_resumen_cuenta_por_estado`— era artefacto
  de mi propio `--basetemp` largo (el test mide presupuesto de `MAX_PATH`); con un `--basetemp`
  corto pasa. **No es del diff.**

---

## Lo que dejo SIN VERIFICAR

- **Los seis `no capturado — llegó por chat`.** Sin informe archivado no hay original contra el que
  contrastar recuentos, severidades ni el reparto en buckets. Lo comprobado en esas seis fichas es
  la coherencia **interna** del documento, no su fidelidad al revisor. Es la consecuencia declarada
  del recorte, no un defecto del diff — pero significa que seis de las diez fichas no son
  auditables en el sentido que el §1 del contrato promete.
- **H-14**: «porque cuenta solo esa severidad».
- **La ronda 2 de vista procesal** (`handoff-…-codex-review-2.md`: v3.1, commit `972da2d`, 6
  hallazgos N1-N6, NO SHIP, `consumido_por` PR #137) **no tiene encabezado de adjudicación en
  ninguna parte**. Su `consumido_por` reparte los seis entre el PR, las piezas de
  `[SIGUIENTE-VISTA-PROCESAL]` y el §1.1 del spec. No es un fallo de fidelidad del diff —la ficha
  del §10 dice «Ronda: 1» y no reclama cubrirla— pero desmiente la impresión de completitud: el
  «noveno que nadie había contado» tiene al menos un hermano, y el mismo patrón se repite con la
  revisión del **plan** de historial citado (censo fila 20), que tampoco tiene sección.
<!-- informe-literal:fin:qtsw -->

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
