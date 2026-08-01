---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
objeto_rev: "5"
commit: 24f8abe
ronda: "4"
clase: diseño
independencia: independiente
revisor: Codex
cobertura: ejecutada
veredicto: NO-SHIP
mandato: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §13.2
marcador_nonce: zx7q
sha256_informe: f67d6ec53f8070898e75920a6913f0a1857b4e11da9c27439e38f003d47ad089
adjudicado_en: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md §17
---

# Revisión adversarial — gobernanza de las revisiones adversariales (rev. 5, ronda 4)

Primera acta con **marcador nonce**, y no por elegancia: el informe de esta ronda **contiene el token
de fin** en su cuerpo —es su hallazgo H-04— así que archivarlo con los marcadores planos de la rev. 5
lo habría cortado por la mitad. El defecto se materializó en el primer intento de usarlo.

## 1. Informe recibido de Codex, sin modificar

> Texto íntegro entregado el 2026-08-01 en `%TEMP%\revision-gobernanza-revisiones-r4.md`, 169 líneas,
> `sha256` verificado por Claude al recibirlo contra la copia externa. Codificación LF, y para este
> fichero el digest bruto coincide con el canónico. No se ha corregido ortografía, numeración ni
> formato. Las referencias `§N:LLL` son del revisor.

<!-- informe-literal:inicio:zx7q -->
# Cuarta revisión adversarial — gobernanza de las revisiones adversariales

- **Objeto:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`, rev. 5 más las dos correcciones del §10.2.
- **Commit revisado:** `24f8abe79c0318effc555d9ffec7812a539d389a`.
- **Rama/worktree:** `claude/internal-dialogue-documentation-4fbc1c` / `.claude/worktrees/internal-dialogue-documentation-4fbc1c`.
- **Alcance:** los siete remedios de la rev. 4, M-1 a M-5 y las dos correcciones del §10.2. El plan de migración queda fuera salvo como fichero del corpus que G7 deberá atravesar.
- **Método:** solo lectura continua; contraste contra el spec completo, las tres actas, `tests/test_docs_gobernanza.py`, `AGENTS.md`, `CLAUDE.md`, `docs/GOBERNANZA_FUENTES_VERDAD.md` §5, `docs/INDICE.md`, `docs/DEAD_ENDS.md` y el corpus real de encabezados. Tests y temporales fuera del repo.

## Veredicto global

**NO-SHIP.** La rev. 5 mejora materialmente el diseño y conserva decisiones que ya eran buenas: no resucita el ledger ni el generador, fija una prohibición continua de escritura, separa el informe de la adjudicación, hace roja una desigualdad de hash y reconoce que G8 solo prueba consistencia bajo la historia de Git. Pero todavía no puede pasar a doctrina.

El bloqueo no está en el plan de migración ni en los dieciséis hallazgos ya adjudicados. Está en ocho defectos del contrato nuevo. El más dañino es la cláusula de cierre: permite que una `LISTA-CON-CAMBIOS` final introduzca decisiones normativas sin ninguna revisión posterior y las rebautiza como «riesgo residual declarado». Además, la obligación de volcar el informe de rama es *fail-open*, la autorrevisión sigue sin ser clasificable de forma inequívoca y el hash definido para el fichero recibido no es el mismo que G8 recomputa tras canonicalizarlo.

Con estos defectos, un tercero puede reconstruir bastante bien lo ocurrido en las tres rondas históricas, pero no puede acreditar de forma fiable que una revisión futura fue independiente, que el informe exigido existió, que el mandato apuntado existía ni que la última remediación normativa fue revisada. El proceso sería **auditable como relato**, no todavía como control.

## Hallazgos

### H-01 — ALTA — M-1 convierte la ausencia del informe de rama en un valor canónico que no bloquea nada

El §1.2:59-65 convierte «recuperable» en obligación del encargo, pero el §5:207 admite como valor normal de la ficha `no capturado (revisión inline sin volcado)`. G7, tal como se especifica en §8:368-373, valida el encabezado, las ocho líneas, `clase` y `cobertura`; no exige la relación:

`clase = rama` + `cobertura = ejecutada` ⇒ `Informe recibido` es una ruta que existe y tiene un acta G8 válida.

G8 tampoco puede cerrar el hueco: solo examina las actas que existen. Una ficha de rama con `Cobertura: ejecutada` e `Informe recibido: no capturado ...` no crea acta que G8 pueda rechazar. El texto la llama «defecto declarado», pero no le asigna consecuencia: no invalida la cobertura, no impide adjudicar y no bloquea doctrina o merge. Esa es exactamente la forma en que una excepción visible se convierte en la vía normal.

La operativa física es viable para un subagente en el mismo host si el encargo fija ruta y nombre antes de empezar. No está cerrada para «Opus de otra sesión» o un revisor en otro host: «fuera del repo» no dice en qué disco ni cómo se transfieren los bytes al adjudicador. Tampoco el §10.1.5 exige que el revisor devuelva por un canal separado la ruta y el SHA-256; sin esa declaración del revisor, la «prueba independiente de origen» de §6.1 depende otra vez de que el autor calcule y escriba ambos lados.

**Cambio exigido:** para revisiones prospectivas de `rama` y `diseño`, G7 debe rechazar `cobertura: ejecutada` salvo que la ficha apunte a un acta existente y válida. `no capturado` solo puede ser una excepción histórica cerrada; en un encargo nuevo obliga a repetir la revisión o deja el gate sin satisfacer. El mandato de revisión debe fijar destino/transferencia y exigir como respuesta corta `ruta + sha256` después de escribir el fichero y antes de adjudicar.

### H-02 — ALTA — M-3 mezcla el tipo de objeto con la independencia y permite etiquetar una autorrevisión como `diseño`

Las clases no son tres alternativas del mismo eje. `diseño` y `rama` describen **qué se revisa**; `autorrevision` describe **la relación del revisor con el autor del objeto**. Una pasada de Claude sobre su propio spec es simultáneamente revisión de diseño y autorrevisión. El esquema obliga a escoger una sola palabra y no contiene `autor_objeto` ni `independiente`.

La contradicción se ve dentro del propio spec:

- §1.1:41-43 permite que Nikolai adjudique;
- §4:161-165 justifica la falta de independencia diciendo que «revisor y adjudicador son la misma persona».

Eso no es la relación relevante. Si Claude escribe y revisa su spec y Nikolai adjudica, revisor y adjudicador son distintos, pero la revisión sigue sin ser independiente del **autor**. A la inversa, Codex puede revisar un objeto de Claude que después adjudica Claude: el adjudicador no es independiente, pero la voz del revisor sí.

G7 solo validará el token de clase y el prefijo de cobertura; el matiz de `Cobertura: ejecutada (sin revisión independiente)` es prosa libre. El criterio 4-bis no especifica ninguna comprobación relacional que impida declarar `Clase: diseño`, `Cobertura: ejecutada` y reclamar el gate. El incentivo que M-3 pretendía eliminar sigue presente, ahora como elección de etiqueta.

**Cambio exigido:** separar los ejes: `tipo_objeto: diseño | rama` e `independencia: independiente | autorrevision`, o conservar `clase` para el objeto y añadir un campo obligatorio de independencia derivable de `autor_objeto`/`revisor`. G7 debe aplicar la relación: si no es independiente, no satisface la revisión obligatoria aunque la ejecución se registre. La independencia se define respecto del autor del objeto, no del adjudicador.

### H-03 — ALTA — El predicado sigue incluyendo las revisiones por tarea que §1.2 expulsa, y pierde sus voces recuperables

El remedio de la rev. 4 retiró la clase C, pero no cerró la contradicción que la originó. Según §1.1:26-28 entra cualquier proceso cuyo mandato ataque un artefacto concreto y versionable y produzca **hallazgos o veredicto**. Una revisión por tarea ataca el diff de su porción —un artefacto versionable— y produce hallazgos. Por ese predicado pertenece a la población. §1.2:71-76 dice, en cambio, que no es una clase y que solo se agrega como cobertura salvo que emita un veredicto sobre el objeto completo. El umbral de salida exige veredicto global; el predicado se satisface con un hallazgo local.

La misma ambigüedad alcanza al `code-review` rutinario. Un encargo «revisa este diff y busca bugs» que produzca hallazgos satisface literalmente (a) y (b), pero §1.1:37-39 lo excluye si no tiene «veredicto adversarial». El criterio prospectivo no puede ser a la vez funcional y depender de una etiqueta de resultado.

Hay además una contradicción de traza. §1.2:53-57 exige acta siempre que un subagente produzca respuesta textual recuperable. Las revisiones por tarea suelen ser precisamente respuestas de subagentes; §1.2:71-76 solo obliga a que la adjudicación agregada enumere hallazgos y procedencia. No conserva el texto ni su hash. Así reaparece, dentro de la cobertura agregada, la pérdida de voz independiente que el remedio de H-02 de la ronda 3 pretendía cerrar.

**Cambio exigido:** separar una regla prospectiva de una heurística de migración. Para lo nuevo, el mandato debe declarar expresamente el evento de revisión adversarial y su objeto/gate completo. Las comprobaciones subordinadas por tarea se excluyen del predicado como contribuciones a una única revisión de rama; su informe consolidado debe incorporar o enlazar las respuestas recuperables con autor y hash. Si se quiere que cada una cuente, entonces necesita identidad y acta propia. No puede cumplir el predicado y desaparecer del censo a la vez.

### H-04 — ALTA — El hash del fichero recibido y el hash canonicalizado de G8 son objetos distintos; los marcadores no son inequívocos

§6.1:319 define `sha256_informe` como digest del **fichero recibido** y §6:304-310 promete texto «byte a byte». G8, en §8:379-382, recomputa otro objeto: texto extraído, recodificado a UTF-8, finales `LF` y un único salto final. Un informe legítimo con CRLF —el caso natural en el entorno Windows que gobierna `CLAUDE.md`— no puede satisfacer ambas reglas aunque la transcripción sea perfecta.

Sonda mínima, sin escribir en el repo, sobre el mismo texto:

- UTF-8/LF: `a150fcc5bff580b30cb78767e2c0e9c80447c0be406a3a2eb39191b302053ffb`.
- UTF-8/CRLF: `082509cd2580b7dbebebe7364b2dbd0d2fcdaaedaad511e05790dec7b1c2226e`.

También falta una regla de escape. Un informe puede contener en una línea propia el token de fin `informe-literal:fin` —es especialmente probable al revisar este mismo contrato—. El acta tendría un inicio y dos finales legítimos. «Extraer lo que hay entre los marcadores» no determina si se usa el primer final, el último o se rechaza; exigir un único par haría imposible archivar literalmente ese informe.

Las tres actas actuales no destapan el problema porque sus copias externas ya están en UTF-8/LF y no contienen los sentinelas: sus bloques coinciden hoy. Eso prueba esos tres casos, no el contrato general.

**Cambio exigido:** elegir una semántica. O bien el hash se calcula, tanto al recibir como en G8, sobre el texto canonicalizado y se deja de afirmar «fichero»/«byte a byte»; o bien se conserva y hashea el blob crudo, por ejemplo codificado. Para los límites, usar un identificador/nonce incluido en ambos marcadores y elegido de modo que no aparezca en el informe; G8 exige exactamente un par con ese nonce y orden correcto.

### H-05 — CRÍTICA — La cláusula de cierre permite promover una remediación normativa nunca revisada

La primera corrección de §10.2 es correcta: la remediación se acumula y antes de doctrina/ejecución hace falta una pasada completa. La segunda deshace la garantía en el último metro: §10.2:504-506 dice que la remediación de esa pasada no dispara ninguna comprobación y se acepta como «riesgo residual declarado».

`LISTA-CON-CAMBIOS` no acredita que sus cambios sean mecánicos. La ronda 3 de este mismo objeto fue `LISTA-CON-CAMBIOS` con siete hallazgos, cuatro de severidad alta; su remediación cambió el predicado, las clases, el contrato de actas, el hash, el esquema de nombres y la migración. La historia real refuta que el token baste para limitar el radio material. Bajo la nueva cláusula, una pasada final idéntica podría cambiar doctrina y entrar sin que nadie leyera el texto finalmente adoptado.

«Riesgo residual declarado» no es una garantía: no enumera qué líneas quedaron sin revisar, quién acepta el riesgo, qué severidad máxima se tolera ni qué cambio reabre el gate. Resuelve la recursión declarando que el último material no se mira. Y el momento «antes de pasar a doctrina o abrir la ejecución» no tiene estado ni gate observable; puede posponerse mientras el autor llame borrador al documento o interpretarse después de que ya exista un plan ejecutable.

**Cambio exigido:** cierre acotado por naturaleza del cambio, no por número de pasadas. Una pasada final cierra con `SHIP`; con `LISTA-CON-CAMBIOS`, solo cierra sin nueva revisión si la adjudicación enumera cambios no normativos/mecánicos y atestigua que no alteran población, obligaciones, vocabularios, guards, permisos ni regla de parada. Cualquier cambio en esos ejes exige una comprobación dirigida del diff final, no otra pasada completa. Una renuncia excepcional debe ser decisión expresa de Nikolai, con cambios y riesgos enumerados. El commit que promociona a `CLAUDE.md`/`AGENTS.md` o inicia la primera tarea debe enlazar la revisión de cierre; sin ese enlace, el gate no está satisfecho.

### H-06 — MEDIA — M-2 hace obligatorio un campo que puede apuntar a cualquier cosa

§6:298-302 dice que sin mandato no se distingue lo omitido de lo no pedido. Sin embargo, §8:385-386 exige solo que `mandato` esté presente. Un valor `mandato: foo`, una sección inexistente o un puntero a la revisión equivocada pasan G8; si el valor no dice `§0 de este acta`, el acta puede además omitir §0.

La renuncia a resolverlo por coste no resiste la comparación vecina: G8 ya debe resolver fichero **y sección** para `adjudicado_en`. El mismo helper puede validar un puntero local. Cuando el mandato vive en el objeto, debe resolverse contra el `commit`/`objeto_rev` del frontmatter, no solo contra el texto mutable de HEAD.

**Cambio exigido:** vocabulario cerrado para `mandato`: `§0 de este acta` con §0 presente, o `<ruta> §N` que exista en el commit del objeto. Si se admite una fuente externa, debe archivarse su texto o una referencia durable y verificable; una etiqueta libre no acredita el alcance.

### H-07 — MEDIA — El nombre sigue sin ser una función estable de la identidad y omite `diagnóstico`

La identidad del §1.3 incluye objeto, commit/rev, ronda, revisor y fecha. El nombre del §6 incluye fecha, tema, tipo de objeto y ronda; omite commit/rev y omite al revisor hasta que aparezca una colisión. El primer acta debe renombrarse retrospectivamente cuando llega un segundo revisor del mismo objeto/ronda, rompiendo punteros ya escritos. Dos revisiones del mismo revisor, objeto, ronda y día sobre commits distintos son identidades distintas según §1.3 y siguen colisionando.

La contradicción se repite en §10.1:463-468, que llama «nombrada por identidad» a una ruta reducida a `(objeto, ronda)`. Además, §1.1 y la clase `diseño` incluyen diagnósticos, pero el enum del nombre solo admite `spec | plan | rama | handoff | diff`.

**Cambio exigido:** hacer el nombre una función inmutable: fecha + tema + tipo de objeto + ronda + revisor siempre + commit/rev corto (o un `revision_id` estable). Añadir `diagnostico` o declarar en qué tipo se normaliza. La misma identidad debe gobernar el fichero externo y el acta.

### H-08 — MEDIA — M-4 describe una confianza en Git que el propio repo ha demostrado revocable

M-4 acierta al rebajar G8 a consistencia interna: cambiar bloque y hash juntos deja el guard verde. Pero §6.1:330-335 llama a Git el ancla porque el historial es «en la práctica, de solo-añadir». `STATUS.md:6` declara que el historial fue reescrito y el repositorio GitHub recreado el 2026-07-07. Por tanto, el supuesto no es una propiedad del sistema; es una política revocable por quien administra el repositorio.

Esto no invalida la utilidad de Git para una auditoría ordinaria. Sí limita la afirmación: un tercero puede auditar **el historial que se le entrega**, no probar que no hubo una historia anterior reescrita. G8 + Git no es una cadena de custodia criptográfica independiente.

**Cambio exigido:** declarar ese límite como frontera de confianza. Si el objetivo es auditabilidad interna, basta con «consistente bajo el historial Git retenido». Si se pretende resistencia frente al administrador, hace falta un ancla fuera de ese historial —commit/tag firmado o publicación externa del hash—. No atribuir a G8/Git una inmutabilidad que el proyecto ya ha revocado una vez.

## Respuesta al mandato, punto por punto

### 1. M-1 — volcado del informe de rama

Es **operable en el mismo host**, incluso para un subagente, si el encargo le da una ruta externa concreta y le exige escribir antes de devolver control. No está completamente especificado para otra sesión/host y, sobre todo, falla abierto: `no capturado` conserva `cobertura: ejecutada` y no bloquea nada. No debe escribirse una solución más compleja; basta con hacer del fichero + hash una precondición del gate y repetir la revisión si se pierde. H-01.

### 2. M-3 — la autorrevisión no acredita cobertura

La intención es correcta, pero el modelo no la puede acreditar porque mezcla el tipo de objeto con la independencia, carece de autor y confunde autor con adjudicador. Sí existe el incentivo perverso: una pasada propia sobre un spec puede etiquetarse honestamente como `diseño` porque también lo es. La solución es otro eje, no más prosa en `Cobertura`. H-02.

### 3. Los siete remedios de la rev. 4

1. **Predicado ampliado a handoff:** incorpora el caso que faltaba, pero sigue sin separar revisión adversarial, code-review rutinario y revisión por tarea. H-03.
2. **Tres clases y cobertura por tarea:** retirar C es mejor, pero la agregación contradice el predicado y el deber de archivar respuestas recuperables. H-02 y H-03.
3. **Acta por respuesta textual recuperable:** decisión correcta; M-1 no la hace todavía fail-closed. H-01.
4. **Marcadores, recómputo y token legacy:** desigualdad roja y allowlist cerrada son correctos. La canonicalización no hashea el mismo objeto que §6.1 y los sentinelas pueden aparecer en el informe. H-04.
5. **Nombre por identidad:** mejora `-rN`, pero la función sigue incompleta e inestable. H-07.
6. **Política de migración:** separar contrato y plan, activar guards al final y migrar por vertical es ejecutable a nivel de spec. El inventario y tareas del plan no se revisan en esta ronda, por mandato.
7. **Medición al fixture:** decisión correcta. La medición actual se reproduce; G7/G8 aún no existen en el código real, por lo que hoy es un criterio de aceptación pendiente, no una capacidad.

### 4. §10.2 y cláusula de cierre

«Antes de pasar a doctrina o abrir la ejecución» describe una intención reconocible, pero no un gate determinable por máquina ni un estado que un tercero pueda comprobar. La acumulación arregla el defecto inicial. La cláusula de «una y solo una» mueve el regreso un paso: deja la última remediación sin revisión, aunque cambie decisiones. «Riesgo residual declarado» es una fórmula de renuncia mientras no enumere cambio, riesgo, aceptante y umbral. H-05.

### 5. Contradicciones entre secciones vecinas

- §1.1 incluye con `hallazgos o veredicto`; §1.2 excluye la revisión por tarea salvo veredicto global.
- §1.2 exige acta a toda respuesta de subagente; la cobertura por tarea conserva solo síntesis/procedencia.
- §4 define independencia frente al adjudicador; §1.1 permite que el adjudicador cambie y la relación relevante es con el autor.
- §6.1 hashea el fichero/bytes; §8 hashea texto canonicalizado.
- §6 afirma nombre por identidad; §10.1 lo reduce a `(objeto, ronda)`.
- §6 hace imprescindible poder seguir el mandato; §8 valida solo que haya cualquier escalar.
- §10.2 reconoce que toda remediación queda sin revisar y acto seguido exime por completo la última.

### 6. Reproducciones y cadena

- **Regex/corpus:** 11 disparadores fuera de bloques cercados; 5 casan el regex sintáctico y 4 pasan también los vocabularios. La afirmación «11 y 4 limpios» es correcta. La plantilla cercada del §5 y las plantillas cercadas del plan quedaron descartadas.
- **Legacy estable:** 8 encabezados; 1 limpio, 1 que falla solo por token (`resuelto`) y 6 estructurales. Coincide con §5.1.
- **Ronda 1:** externo, frontmatter y bloque literal = `4f45f867de828badfdcd9f583e1731856001265ee345bb910f450b5142663f58`; 106 líneas.
- **Ronda 2:** externo, frontmatter y bloque literal = `20c45f93c0460a8f91ba426c9570ac918b01882a43f07aec9f549166070f4114`; 107 líneas.
- **Ronda 3:** externo, frontmatter y bloque literal = `43b945e24a9aa990bc7aea1ffc0d4aae205e21a55f6f3241383bc6781587a325`; 147 líneas.
- Las tres copias externas anteriores siguen existiendo y no se sobrescribieron.

## Lo que resiste

- El contrato continuo de §10.1 es más fuerte que una foto final y no prohíbe ninguna ejecución necesaria. Esta revisión pudo leer, medir y ejecutar G1-G6 sin escribir en repo, ignorados, `data/CASOS/` ni sistemas externos.
- Eliminar el registro central, G9 y el generador sin consumidor sigue siendo correcto.
- La adjudicación junto al objeto y el informe en acta separada respetan «un hecho → un hogar».
- Una acta por ronda y un frontmatter escalar son decisiones coherentes; el defecto está en la función de nombre, no en separar rondas.
- La allowlist legacy cerrada es mejor que una clase permanente exenta.
- M-4 es una corrección honesta sobre el alcance de G8; solo necesita declarar la confianza depositada en la historia Git.
- El corte temporal y el inventario de migración no se reabren en esta ronda.

## Verificaciones ejecutadas bajo el contrato de solo lectura

- `HEAD`: `24f8abe79c0318effc555d9ffec7812a539d389a`; rama correcta.
- `tests/test_docs_gobernanza.py`: **8 passed** con `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp` único bajo `%TEMP%`. Son G1-G6; G7/G8 todavía son diseño.
- Instantánea SHA-256 integral del worktree alrededor de la ejecución: **1.366 → 1.366 ficheros; 0 añadidos, 0 borrados, 0 modificados; 0 errores de lectura**.
- `git status --porcelain=v1 --untracked-files=all`: vacío antes y después.
- Un primer intento mediante el alias `python.exe` de Windows no llegó a crear proceso; se descartó y no se contó como test. La ejecución válida es la anterior, con el intérprete explícito del venv.
- No se llamó a CRM, Drive ni a ningún sistema externo. No se escribió ningún fichero dentro del repo.

## Condición de salida

No hace falta otra reescritura total. Para poder pasar a doctrina deben cerrarse H-01 a H-05. H-06 a H-08 pueden resolverse en la misma edición porque afectan precisamente a los guards y a las afirmaciones de auditabilidad. Después, por la propia regla corregida, procede una comprobación dirigida del diff final si cambia alguno de esos ejes; no otra pasada completa del corpus histórico.
<!-- informe-literal:fin:zx7q -->

## 2. Evidencia verificada por Claude al adjudicar

Comprobado abriendo la fuente. La adjudicación razonada está en el §17 del spec.

**Cinco de los ocho son contradicciones internas del propio documento**, verificables sin salir de él:

- **H-01.** El §5 admite `no capturado (revisión inline sin volcado)` como valor de ficha y el §8 no
  relaciona `clase`+`cobertura` con la existencia del acta. La rev. 5 lo llamaba «defecto de proceso
  declarado» y **no le asignaba ninguna consecuencia**: no invalida cobertura, no impide adjudicar, no
  bloquea nada. *Fail-open* es la descripción correcta. **Confirmado.**
- **H-02.** `clase ∈ diseño | rama | autorrevision` mezcla dos ejes: los dos primeros dicen **qué** se
  revisa, el tercero dice **quién**. Y el §4 justificaba la falta de independencia con «revisor y
  adjudicador son la misma persona» mientras el §1.1 permite que adjudique Nikolai — con lo que la
  justificación se cae sola. La relación que importa es con el **autor**. **Confirmado.**
- **H-03.** El §1.1 admite «hallazgos **o** veredicto» y el §1.2 solo saca a la revisión por tarea si
  emite «veredicto sobre el objeto». Umbral de entrada local, umbral de salida global: la misma
  contradicción de la ronda 3, renombrada. **Confirmado, y es una remediación que no remedió.**
- **H-04.** El §6.1 define el digest sobre el «fichero recibido» y el §8 lo recomputa sobre texto
  canonicalizado. **Y el plan de migración ya define la forma canónica**, así que spec y plan
  discrepaban entre sí. **Confirmado, con agravante:** lo supe al escribir el plan y no lo llevé al
  spec.
- **H-05.** El §10.2 reconocía que toda remediación queda sin revisar y acto seguido eximía por
  completo la última. La refutación empírica está en la historia de este mismo documento: la ronda 3
  fue `LISTA-CON-CAMBIOS` y su remediación cambió el predicado, las clases, el contrato de actas, el
  hash, el esquema de nombres y la migración. **Confirmado. CRÍTICA justificada.**
- **H-06.** El §8 decía literalmente «se comprueba presencia, no resolución», y justificaba la renuncia
  por coste — cuando G8 ya resuelve fichero **y** sección para `adjudicado_en`, con el mismo helper.
  **Confirmado; el argumento de coste era mío y era flojo.**
- **H-07.** La identidad del §1.3 incluye commit y revisor; el nombre del §6 los omite salvo colisión,
  así que la primera acta habría que renombrarla al llegar un segundo revisor, rompiendo punteros ya
  escritos. Y el enum del nombre no admite `diagnostico`, que el §1.1 sí incluye. **Confirmado.**

**El único que exigía fuente externa, y es el más elegante:**

- **H-08.** `STATUS.md:6` — aviso en rojo: «el **historial de git fue reescrito** y el repo GitHub
  **recreado**» el 2026-07-07, sin ancestro común. Llamar al historial «en la práctica, de
  solo-añadir» es un supuesto que **este proyecto ya revocó una vez**. **Confirmado.**

**Y el H-04 se materializó al archivar este mismo informe.** Su línea 65 contiene el token
`informe-literal:fin`, así que los marcadores planos de la rev. 5 habrían cortado el bloque por la
mitad. Esta acta es la primera con **marcador nonce** (`zx7q`, elegido con letras no hexadecimales para
que no pueda aparecer dentro de un digest citado). El defecto no se dedujo: bloqueó el primer intento.

### Nota de método

Cuarta ronda, ocho de ocho confirmados: **24 de 24 en cuatro rondas, cero refutados**. Y el veredicto
más duro llegó contra la corrección más reciente —la cláusula de cierre tenía dos días de vida—, lo
que confirma que la decisión de Nikolai de revisar la rev. 5 **completa**, en contra de la regla de
parada que yo mismo acababa de escribir, era la correcta.

El patrón de los cuatro rondas es estable y conviene no adornarlo: mis remediaciones cierran el
defecto señalado y abren uno nuevo en la costura de al lado. H-03 es el caso puro — la ronda 3 pidió
elegir una semántica para las revisiones por tarea, elegí «cobertura agregada», y eso ni las excluye
del predicado ni les da identidad. No es falta de cuidado: es que el diseño acopla demasiados ejes, y
H-02 lo dice con precisión.
