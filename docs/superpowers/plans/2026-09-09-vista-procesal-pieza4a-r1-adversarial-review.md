---
tipo: revision-adversarial
objeto: "diff e783464..9c4d5c1 — vista procesal de 05_Procedimiento, pieza 4a (la mitad que solo lee)"
objeto_rev: "1"
commit: "9c4d5c1"
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p4ad
sha256_informe: 4d32d8b34a7331e7756931fe3c1575353d53e67e4246c74b50f80feef73dc003
adjudicado_en: docs/superpowers/plans/2026-09-09-vista-procesal-pieza4a.md §8
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre el DIFF de la pieza 4a.** Ronda única, y **ese
> presupuesto es justamente lo que el revisor invalida** (ver su H-01): descansaba en que
> el diff entero careciera de escritura, y la Tarea 2 amplía los destinos de un helper que
> escribe. El radio de daño de 4a no es cero como se afirmó; es *cero en los nueve módulos
> nuevos* y no en el objeto completo.
>
> El §1 conserva la voz del revisor **sin una coma cambiada**; el §2 es la evidencia que
> verifiqué yo contra la fuente. **La adjudicación NO está aquí:** va en el §8 del plan 4a.
>
> **Objeto:** `base/` (e783464), `head/` (9c4d5c1) y `DIFF.patch` (2.894 líneas), copias
> externas sin `.git`. El parche tenía `sha256 f4986a50…e080dd2` y el revisor lo declaró
> **idéntico al abrir y al cerrar**; lo comprobé yo también, con el mismo valor. Y contrastó
> los hunks de los 26 ficheros contra ambas copias, que es más de lo que se le pidió.
>
> **Esta ronda ejecutó, y mucho.** Corrió los 120 tests de la pieza con las dos semillas
> (116+4 y 137+4), reconstruyó 13 mutantes del autor —los 13 murieron—, montó **tres
> contrapruebas propias que SOBREVIVEN**, creó junctions reales, obtuvo un alias 8.3 real con
> `GetShortPathNameW`, llamó al `_split_o_md` real de la sala de máquina para ver qué filas
> produce de verdad, y montó un *audit hook* que bloqueaba aperturas de escritura durante el
> import del paquete. Nada de eso sale de leer un diff.
>
> **La contraprueba que más duele, y que es la razón del NO-SHIP:** añadió a la copia un
> `Path(...).open('w')` que **escribe un fichero al importar el paquete**, y los 120 tests
> siguieron verdes. Mi guard de «no escribe» mira el modo en `nodo.args[1:2]`, y en
> `Path.open("w")` el modo es `args[0]`. El hueco no estaba en mi inventario de huecos
> declarados. Un segundo escritor añadido al CLI también sobrevive, porque el glob del guard
> solo mira `core/procedimiento/*.py`.
>
> **Y el defecto funcional más caro,** que ningún test mío podía ver porque mis fixtures no
> venían del productor real: agrupé los bundles por `parent_sha256`, y ese campo es la
> **clave del estado idempotente**, no el marcador de segmento. `sala_maquina.py:938` lo
> rellena también en el camino *passthrough*, con `parent_slug` vacío — así que un documento
> suelto real se trata como bundle sin padre y **se bloquea**. El revisor lo demostró llamando
> al productor, no leyéndolo.
>
> **Dos hallazgos que yo había encontrado antes, y conviene fechar bien:** el `TypeError` de
> `WorkspaceRegistry()` (su H-02) y el `drive_accesible=True` a pelo salieron de mi propio
> *smoke test* del CLI y están remediados en `16c646a`, **posterior al objeto congelado y
> anterior a su informe**. No me atribuyo mérito por ellos: los encontramos los dos, por
> separado, y su verificación con `CliRunner` es mejor que la mía.
>
> **Cobertura ausente que el propio revisor declaró — quince declaraciones SIN VERIFICAR:**
> la genealogía de los commits (no hay `.git`), **los 25 mutantes exactos del autor** (el
> arnés vive en `scratch/`, gitignored, así que no forma parte del objeto y solo reconstruyó
> 13), el corpus real de W-02VEKE, el reparto del piloto, el reparse tag real de `G:`, los
> filtros de nube, la matriz de ACL y namespaces de Windows, las carreras reales, el CRM y el
> Drive vivos, los motores de OCR y LibreOffice, y la suite global del repo.
>
> **Digest:** el `sha256` del bloque canonicalizado coincide con el del `INFORME.md` original
> (`4d32d8b34a73…`) porque lo escribió en LF con un solo salto final, y él mismo lo declara.
> No se calculó hasta que el **proceso** terminó.
>
> **Nota sobre el primer intento de esta ronda, que no produjo informe.** Un mandato anterior
> murió a mitad por el filtro de contenido de Codex tras quemar 154.000 tokens, porque yo lo
> había redactado como «intenta una escritura por una vía que el guard no vea, y demuéstrala»
> — y eso se lee como pedir una técnica de evasión. El trabajo pedido era el mismo; se
> reformuló como auditoría de completitud de un control y pasó. La cobertura de ese intento es
> **AUSENTE**, no parcial, y su `_stdout.log` se conserva como evidencia de que existió.

## 0. Mandato entregado, literal

<!-- mandato-literal:inicio:p4ad -->
# Mandato — Revisión adversarial R1 del DIFF de la «vista procesal», pieza 4a

## 0. Higiene del workdir (lee esto primero)

Tu directorio de trabajo debe contener **solo este `MANDATO.md`**. Si encuentras cualquier otro
fichero, **no lo leas**: puede ser el trabajo de otra ronda sobre otro objeto. Decláralo en la
**primera línea** de tu informe y sigue.

## 0-bis. Sobre la redacción de este mandato

Un intento anterior de este encargo se detuvo por un filtro de contenido, porque estaba redactado
como «busca la manera de sortear este control». **El trabajo que se pide es exactamente el mismo y
no se ha rebajado:** dictaminar si un paquete de código escribe en disco y si la cobertura que su
propio test declara es exacta. Lo que cambia es el enfoque — se **audita la completitud** de una
comprobación, que es trabajo de revisión de código ordinario. Si alguna frase de más abajo te
parece que pide otra cosa, interprétala así y dilo en el informe.

## 1. Qué eres y qué NO eres

Eres el revisor adversarial. Tu trabajo es **encontrar lo que está mal**, no aprobar. Pero **no
inventes**: un hallazgo que no puedas anclar a una línea concreta del objeto no vale. Y **«no pude
comprobarlo» NO es «está bien»**: cuando no puedas verificar algo, escribe literalmente
**SIN VERIFICAR** y por qué. Un revisor que no corre **no refuta, deja sin verificar**.

**No eres el juez.** El autor adjudicará cada hallazgo contra la fuente. Tu informe se archivará
**literal** en un acta, así que escríbelo para ser leído tal cual.

## 2. El objeto

Tres copias congeladas, fuera del repo y sin `.git`:

    C:\t\obj-p4a-diff-2026-09-09-1731\base\        (commit e783464, antes)
    C:\t\obj-p4a-diff-2026-09-09-1731\head\        (commit 9c4d5c1, después)
    C:\t\obj-p4a-diff-2026-09-09-1731\DIFF.patch   (2.894 líneas)

`sha256` del parche al montarlo:
`f4986a504db01b7c4f79d5f33cb28ea54f6e7876a86e94aa826869347e080dd2`

**No las modifiques.** Si necesitas ejecutar algo que escriba, copia a tu workdir. **Reporta el
`sha256` del parche al abrir y al cerrar**: es la prueba de no-mutación que aquí sustituye al
`git status`. No puedes acreditar por genealogía que las copias sean esos commits (no hay `.git`):
verifica **contenido**, no ascendencia.

### Lo que se revisa

El diff completo, y en particular estos ficheros nuevos de `head/`:

- `core/procedimiento/sede.py` — de dónde viene la autorización, y qué rutas se consideran válidas
- `core/procedimiento/carpetas.py` — las cinco carpetas de fase
- `core/procedimiento/universo.py` — los tres conjuntos de documentos del CRM
- `core/procedimiento/mapa.py` — carga y validación del fichero YAML que escribe el letrado
- `core/procedimiento/artefacto.py` — qué fichero representa a cada documento y con qué calidad
- `core/procedimiento/vista.py` — el informe
- `core/procedimiento/borrador.py` — propuesta de mapa
- `core/procedimiento/__init__.py` — fachada
- `scripts/procedimiento.py` — CLI
- `tests/test_procedimiento_*.py` — 120 tests

### Contra qué se revisa (fuentes de verdad, no objeto)

- `docs/superpowers/plans/2026-09-09-vista-procesal-pieza4a.md` — **el plan que este diff
  ejecuta**. Lo que el diff prometa y no cumpla es un hallazgo.
- `docs/superpowers/plans/2026-09-09-vista-procesal-pieza4.md` — el diseño, con **los ocho
  invariantes** (§«Los ocho invariantes») y la adjudicación de la ronda anterior.
- `docs/superpowers/plans/2026-09-09-vista-procesal-pieza4-r1-adversarial-review.md` — el informe
  de la ronda anterior **sobre el plan de la rev. 1**, que volvió NO-SHIP con 23 hallazgos. Úsalo:
  tu segunda tarea (§4) es dictaminar si las remediaciones son reales.
- `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md` — el spec.
- `core/casos/workspace_model.py`, `core/casos/workspace_resolver.py` — de dónde viene la
  autorización para tocar un caso.
- `core/sala_maquina.py` — `DocCobertura`, los valores de `metodo` reales, dónde se escribe el OCR.
- `core/ocurrencias_crm.py` — el registro de ocurrencias.
- `core/case_manager.py`, `core/sync_sudespacho.py` — el esquema D8 y quién puebla `doc_ids`.
- `scripts/sala_maquina.py` — el patrón de resolución de workspace que este diff dice seguir.
- `CLAUDE.md` — las reglas del proyecto.

## 3. Por qué esta pieza lleva UNA ronda, y qué te toca comprobar por ello

El plan de la rev. 1 juntaba dos cosas de consecuencia muy distinta: *describir* qué documentos hay
en un procedimiento judicial, y *publicar* copias de esos documentos en el expediente. Se partió en
dos. **Esto es 4a, la mitad que solo describe**, y su presupuesto de una sola ronda de revisión
descansa **enteramente** en una afirmación del autor:

> **este paquete no escribe nada en disco, y no pide al workspace ninguna capacidad de escritura.**

Lo sostiene `tests/test_procedimiento_sin_escritura.py`, un test que analiza el AST de los módulos.

**Tu primera tarea, y la más importante, es dictaminar si esa afirmación es exacta.** El paquete
tiene nueve módulos: recórrelos y di si alguno escribe en disco, directa o indirectamente — una
llamada de `pathlib` o `shutil`, un `open` en modo de escritura, una función de otro módulo del
repo que escriba por dentro, el CLI. Si hay alguna, eso **no es un hallazgo más**: invalida el
presupuesto de rondas de la pieza y hay que decirlo así.

Dictamina también el test como **instrumento de medida**, que es la parte que más suele fallar:

- ¿La cobertura que declara es la que tiene? Se pone rojo si se le pone delante un módulo que
  escriba (tiene un control positivo; compruébalo y di si es suficiente).
- Su `test_el_hueco_del_guard_esta_DECLARADO` enumera lo que un análisis de AST **no** puede ver.
  ¿Ese inventario está completo? ¿Hay más formas de escritura que se le escapen y que el test no
  mencione? Lo que busco es el **inventario de lo no cubierto**, con su consecuencia práctica.

Después, por consecuencia:

1. **Autorización.** ¿`sede.raiz_autorizada` puede devolver una raíz sin haber exigido la
   capacidad? ¿La fachada de `__init__.py` la puentea? ¿El CLI? ¿Se puede terminar leyendo un caso
   que está prestado a otra máquina?
2. **Validez de rutas.** `sede.contener` decide qué rutas son legítimas bajo la raíz del caso, y
   los tests la ejercitan con un enlace de directorio real. Audita la **completitud** de esa
   decisión: ¿qué clases de ruta quedan fuera de lo que comprueba? Interesan los nombres cortos
   8.3, los reparse points que no son junction ni symlink, un `..` intermedio, unicode que
   normaliza a otro nombre y las rutas largas.
3. **Los tres conjuntos del CRM.** El diff afirma que `pull_state.doc_ids` son los documentos
   **descargados** y no el universo enumerado. **Verifícalo contra `core/case_manager.py` y
   `core/sync_sudespacho.py`** — es la corrección más importante de la ronda anterior y el autor
   dice expresamente que no se cree a sí mismo. ¿Las puertas de `universo.incoherencias` son
   correctas y completas? ¿Hay un caso real del intake acotado que se reporte como incoherente
   cuando no lo es, o al revés?
4. **El selector de representante.** ¿Cubre los `metodo` y `estado` que `sala_maquina` produce de
   verdad? ¿El agrupado de bundles resuelve al artefacto del padre en todos los casos? ¿`alias_de`
   se resuelve bien, incluyendo una cadena de alias o un alias circular?
5. **La validación del mapa.** Es la entrada de datos del letrado, y lo que se acepte aquí acabará
   siendo una escritura cuando exista 4b. ¿Qué valores inválidos pasan la validación?

## 4. Tu SEGUNDA tarea: dictaminar las remediaciones de la ronda anterior

Esto es lo que casi nunca se pide y suele ser lo más valioso. El acta de la ronda anterior trae 23
hallazgos sobre el **plan** de la rev. 1. Para los que caen dentro del alcance de 4a, dictamina si
la remediación es **real, cosmética o incompleta**, contra el código de `head/`:

- **H-06** (la autoridad la daba el catálogo y el mutex local, no el workspace).
- **H-08** (`pull_state.doc_ids` conflatado con el universo; el intake acotado bloqueaba 74 de 76).
- **H-09** (registro de ocurrencias ausente se leía como universo vacío).
- **H-10** (el SHA del crudo no se cruzaba con la cobertura).
- **H-11** (el bundle resolvía al slug del segmento, no del padre).
- **H-12** (`duplicado` y `error` sin cubrir; `alias_de` sin resolver; el orden de las filas
  decidía la calidad).
- **H-14** (`eco_crm` sin validar: un eco falso ocultaba un documento real).
- **H-15** (`sin_cobertura_ok: 'false'` activaba el override, porque `bool('false')` es `True`).
- **H-16** (`orden` sin gramática; reservados de Windows detectados por `.stem`; claves YAML
  duplicadas que sustituían una decisión en silencio).
- **H-17** (el presupuesto de longitud de ruta olvidaba el nombre temporal).
- **H-18** (no había flujo para preparar el mapa, y sin él la pieza no se usa).
- **H-21** (tests que compraban garantías que no ejercitaban).

Los que son de 4b —H-01 a H-05, H-07, H-13, H-19, H-20, H-22— **quedan fuera de este diff**: no los
cuentes como no remediados, pero **sí** dinos si algo de 4a los hace más difíciles de remediar
después.

## 5. Los mutantes: ¿matan lo que dicen matar?

El autor montó un arnés de mutación (`scratch/mutar.py`, **no está en el diff** porque `scratch/`
está gitignored, así que solo verás sus efectos) y declara **25 mutantes muertos**. Reconstruye los
que puedas a partir de los tests y pregúntate:

- ¿Cada test se pondría rojo con el defecto que dice cazar?
- **¿Hay un mutante MEJOR que el propuesto que sobreviva?** Un mutante que mata más de lo debido
  está mal apuntado, y uno que sobrevive señala un test que compra confianza falsa.
- Dos tests se reescribieron **porque su mutante sobrevivía** (el del tag de nube en `sede.py` y el
  del `casefold` en `mapa.py`), y un caso se añadió al encontrar el input que distinguía una guarda
  aparentemente redundante. ¿Quedan más de esos?

## 6. Qué puedes ejecutar

**Puedes y debes correr los tests.** Intérprete con las dependencias:

    C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe

Trae `pytest`, `pytest-randomly`, `pytest-xdist`, `yaml`, `typer`, `filelock`, `dotenv`, `httpx`.
El `python` del PATH de este equipo es un Python pelado **sin** las dependencias: no lo uses.

Dos avisos medidos:

- Usa `--basetemp` **relativo a tu workdir**. Tu sandbox no puede crear directorios en la raíz de
  `C:`, y MAX_PATH tumba tests que están bien.
- **No modifiques las copias del objeto.** Copia a tu workdir lo que necesites ejecutar.

Cosas útiles que valen más que leer:

- Correr los 120 tests de la pieza sobre `head/`, con semilla y en paralelo.
- Escribir tus propios mutantes sobre una **copia** de `head/` y ver si los tests los cazan.
- Ejercitar `sede.contener` con enlaces de directorio reales creados en tu workdir
  (`mklink /J`, `mklink /D`) y contrastar su decisión con la esperada.
- Poner delante del test de no-escritura un módulo de prueba **tuyo** que escriba, para dictaminar
  si lo detecta. Es el control positivo del instrumento.

Si haces algo de esto, **dilo**: un hallazgo obtenido ejecutando vale más que uno leído, y el autor
necesita saber cuál es cuál.

**Lo que NO puedes verificar y conviene que declares:** el corpus real de W-02VEKE (sus 4 tests de
regresión se **saltan** porque el Drive no está montado y los fixtures no existen — eso está
declarado en el diff, no lo cuentes como oculto), el reparse tag real de un fichero en `G:`, y el
comportamiento contra un CRM o un Drive vivos.

## 7. Formato del informe

Escribe **`INFORME.md`** en tu workdir. Estructura:

1. **Primera línea:** declaración de higiene (§0) — qué había en tu workdir.
2. **`sha256` del parche al abrir.**
3. **Dictamen sobre la afirmación central** (§3): ¿escribe algo de 4a en disco, sí o no? Y ¿es
   exacta la cobertura que su test declara? Esto va arriba, en dos líneas, porque de ello depende
   el presupuesto de rondas de la pieza.
4. **Resumen ejecutivo**, 5-10 líneas. Lo peor primero.
5. **Hallazgos**, `H-01`, `H-02`… Cada uno con: **severidad** (`CRÍTICO` · `ALTO` · `MEDIO` ·
   `BAJO` · `NOTA`), **ancla** (fichero y línea de `head/`), **qué está mal** en una frase, **por
   qué importa** con el escenario concreto, **cómo lo verificaste** (leyendo, o ejecutando y qué), y
   **remedio** si lo tienes.
6. **Dictamen de las remediaciones de la ronda anterior** (§4), una línea por hallazgo:
   `real` · `cosmética` · `incompleta` · `fuera de alcance`, con el motivo.
7. **Los mutantes** (§5): los que reconstruiste, y si alguno sobrevive.
8. **Lo que NO pudiste verificar**, con el motivo. Sección obligatoria; si está vacía, dilo.
9. **`sha256` del parche al cerrar.**
10. **Última línea: el veredicto**, una sola palabra del **set cerrado**, sin nada más:

    `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE` ·
    `SIN-VEREDICTO`

    Es obligatorio: sin él la cadena de custodia del acta se rompe y el autor no puede rellenarlo
    por ti.

No des una segunda pasada de cortesía. Cuando el informe esté terminado, para.
<!-- mandato-literal:fin:p4ad -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p4ad -->
Higiene: al abrir el workdir había MANDATO.md y _stdout.log; no leí _stdout.log. Los demás ficheros de trabajo y evidencia citados en este informe los creé durante esta revisión.

# Revisión adversarial R1 del DIFF de vista procesal, pieza 4a

## SHA-256 del parche al abrir

`f4986a504db01b7c4f79d5f33cb28ea54f6e7876a86e94aa826869347e080dd2`

Objeto: `C:\t\obj-p4a-diff-2026-09-09-1731\DIFF.patch`. Las anclas siguientes son rutas relativas a su `head\`, con líneas numeradas desde 1. Las identidades e783464/9c4d5c1 son las comunicadas: no se acredita genealogía sin `.git`. Sí comprobé que los hunks de los 26 ficheros del parche se aplican al contenido de `base` y reproducen el contenido textual de `head`.

## Dictamen central — dos líneas

**¿Escribe 4a en disco? SÍ en el DIFF completo:** amplía destinos de un helper escritor y ejecuté esa escritura; **NO encontré escritura directa en los nueve módulos nuevos**, cuya fachada aborta antes de operar, pero su dependencia de resolución contiene además una escritura indirecta latente, demostrada adaptando únicamente el constructor incompatible. La premisa de cero escrituras no justifica el presupuesto de rondas del objeto completo tal como está delimitado.
**¿Es exacta la cobertura declarada por su test? NO:** una escritura real mediante `Path.open("w")`, añadida solo a la copia, sobrevivió a los 120 casos; el inventario de huecos es incompleto, el CLI queda fuera y la ausencia de `WRITE_CASE` no impide escribir con las APIs ordinarias del sistema.

## Resumen ejecutivo

El objeto incluye una ampliación efectiva de dónde puede escribir `registrar_outputs`; no es íntegramente una modificación de lectores.
Los comandos `informe` y `borrador-mapa` fallan con `TypeError` por construir `WorkspaceRegistry` sin sus argumentos obligatorios.
El selector confunde `parent_sha256` con pertenencia a un bundle: bloquea filas normales que el productor real genera para PDF, OCR y ofimática.
El guard de no escritura deja pasar una escritura ejecutada; sus controles positivos funcionan, pero no acreditan la propiedad general que se les atribuye.
La raíz autorizada no llega a los lectores del universo; la fachada puede mezclar un workspace local con ocurrencias y D8 del catálogo una vez corregido el arranque.
Persisten rutas que no pasan por contención, alias que degradan silenciosamente al crudo, SHA de ocurrencia sin cruzar y colisiones entre destinos CRM y despacho.
El informe puede declarar «completo» con incoherencias, y el supuesto test de selector del corpus descarta la cobertura que recibe.
Ejecutado: 116 pasados y 4 saltados con semilla 777; 137 pasados y 4 saltados con 31337 al añadir 21 tests existentes; 13 mutantes reconstruidos muertos, dos adicionales supervivientes y una contraprueba del test de corpus también superviviente.

## Método y límites de la ejecución

Leí los nueve módulos, los ocho ficheros de tests nuevos, las modificaciones del helper y `.gitignore`, el plan 4a, los ocho invariantes del diseño, los hallazgos de la ronda anterior y las fuentes productoras/consumidoras citadas. El cambio `informe.py` → `vista.py` está explicado y no lo considero defecto. Tampoco atribuyo al diff la omisión declarada de los fixtures reales.

Todas las escrituras de ensayos fueron a este workdir. Copié `head` a `ejec`. Usé exclusivamente `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, raíces sintéticas y pytest sin cacheprovider. Los `--basetemp` fueron relativos al workdir. No modifiqué base, head ni el parche; no usé CRM, Drive, git add ni commits. No apliqué las instrucciones genéricas de cambiar al repo vivo o ejecutar `session_close`, porque contradirían el mandato específico de revisión aislada.

Evidencias conservadas junto al informe:

- `sondas_revision.py` y `SONDAS.json`: CLI, guard, productor de cobertura, selector, mapa y rutas.
- `sondas_integracion.py` y `INTEGRACION.json`: raíces partidas, workspace bloqueado real, OCR a través de junction, Unicode y comparación del helper base/head.
- `mutantes_revision.py`, `MUTANTES.json` y `logs_mutantes/`: cambios exactos, órdenes y resultados por mutante.
- `CONTENIDO_DIFF.json`: los 26 ficheros cuyos hunks se contrastaron contra ambas copias.

Corridas base, sin mutaciones:

1. Los ocho `ejec/tests/test_procedimiento_*.py`, pasados como argumentos explícitos, con `-n 2 --randomly-seed=777 --basetemp=bt777 -p no:cacheprovider --tb=short`: **116 passed, 4 skipped**, 37,23 s.
2. Los mismos más `test_skill_helpers_sync.py` y `test_ocurrencias_crm.py`, con `-n 2 --randomly-seed=31337 --basetemp=bt31337 -p no:cacheprovider --tb=short`: **137 passed, 4 skipped**, 32,89 s.

Los cuatro saltos corresponden a regresión/corpus y están declarados por el objeto. Los tests de junction sí corrieron. Los asertos de mis sondas comprueban el comportamiento descrito, incluidos defectos: que una sonda termine sin error no significa que apruebe el producto. Las excepciones registradas como dato, por ejemplo el `TypeError` del mapa, se distinguen de fallos del arnés.

## Hallazgos

### H-01 — La afirmación de cero escrituras no abarca el diff completo

**Severidad: ALTO. Ancla:** `.claude/skills/_shared/registrar_outputs.py:65–70`, `:79`, `:110–124`, `:127–130`, `:189–193`, `:213–220`; siete copias del mismo cambio en las skills.

**Qué está mal:** el objeto cambia una lista que autoriza destinos de un escritor mientras se justifica como una pieza sin efectos de escritura.

**Por qué importa:** antes `05_Procedimiento/05_Otros escritos` se rechazaba; después el helper puede crear allí el directorio y `_index.md`, y su entrada ordinaria también mantiene navegación. Esto está pedido expresamente por la Tarea 2 del plan: no es trabajo ajeno añadido por accidente, sino una contradicción de delimitación con la restricción global «ni un mkdir». El presupuesto de una ronda no puede descansar en que TODO este diff carezca de escritura. No afirmo que llamar a `procedimiento.informe` invoque el helper: son entradas distintas incluidas en el mismo objeto.

**Verificación:** ejecuté `_validar_destino` seguido de `update_manifest` de base y head sobre dos árboles sintéticos. Base rechazó; head escribió `05_Procedimiento/05_Otros escritos/_index.md`. `INTEGRACION.json`, `helper_amplia_escritura`.

**Remedio:** delimitar explícitamente esta ampliación del escritor y adjudicar su radio de daño; separarla si se conserva para 4a el contrato absoluto de lectura. Este hallazgo invalida esa justificación del presupuesto; no me autoriza a imponer por mi cuenta una ronda adicional.

### H-02 — Ninguno de los dos comandos puede resolver un caso

**Severidad: CRÍTICO. Ancla:** `core/procedimiento/__init__.py:45–47`; contrato real en `core/casos/workspace_registry.py:147`.

**Qué está mal:** `WorkspaceRegistry()` exige `raiz` y el keyword `ahora`, pero la fachada no suministra ninguno.

**Por qué importa:** cualquier invocación válida con `--case` o `--case-dir` aborta antes de pedir `READ_CASE`, leer el mapa o generar el borrador. `TypeError` tampoco está en `_ERRORES` del CLI. El `--help` no ejercita esta integración.

**Verificación:** `CliRunner` sobre ambos comandos sin modificar: exit 1 y `WorkspaceRegistry.__init__() missing 1 required positional argument: 'raiz'`. Lectura del patrón real de `scripts/sala_maquina.py:468–501`, que sí construye el registro mediante su helper. Ninguno de los 120 tests llama a esta resolución real.

**Remedio:** construir el registro con raíz explícita y reloj compartido con el resolver; añadir una prueba de entrada completa con catálogo, registro y caso sintéticos. Corregir solo esta firma deja expuestos H-05 y H-06.

### H-03 — Un documento suelto real se interpreta como bundle; los bundles digitales exigen un OCR que no existe

**Severidad: CRÍTICO. Ancla:** `core/procedimiento/artefacto.py:115–117`, `:124–134`, `:155–170`.

**Qué está mal:** todo `parent_sha256` no vacío crea un grupo, y todo grupo exige un PDF de `01_OCR`, sin distinguir documento suelto, bundle digital y bundle convertido.

**Por qué importa:** `DocCobertura.parent_sha256` es el SHA del fichero físico, no una marca suficiente de segmento (`core/sala_maquina.py:192–195`). `_split_o_md:937–938` lo rellena también en passthrough, con `parent_slug` vacío. Esa fila pasa a grupo y bloquea por falta de padre incluso si existe el OCR. Ocurre en caminos normales de PDF digital, OCR y ofimática. Los retornos de OCR fallido/visión de `:1030–1042` también llevan ese campo. Además, un bundle digital generado desde el propio crudo (`:1380–1381`) no necesita ni crea `01_OCR/<padre>.pdf`; el selector lo exige igualmente. Volver a correr sala de máquina no arregla esta incompatibilidad.

**Verificación:** llamé al `_split_o_md` real, simulando solo detección, extracción/calidad y escritura de MD para aislar el productor. Su fila `pypdf/ok`, `sha256=parent_sha256`, `parent_slug=''` fue rechazada por 4a como bundle. Otra sonda con dos segmentos `pypdf` y padre conocido bloqueó por OCR ausente. Contrasté los caminos completos con `sala_maquina.ejecutar` y `_ofimatica_y_extraer`.

**Remedio:** separar sueltos y segmentos por el contrato estructural del productor; conservar método/procedencia del padre y elegir crudo para bundle digital, artefacto para convertido. Los tests deben consumir filas producidas realmente, no eliminar de las fixtures el campo que dispara el defecto.

### H-04 — El guard deja pasar escrituras ordinarias y atribuye al workspace una barrera que no existe

**Severidad: ALTO. Ancla:** `tests/test_procedimiento_sin_escritura.py:29`, `:52–59`, `:65`, `:120–136`, `:163–169`; promesa en `core/procedimiento/__init__.py:3–6`.

**Qué está mal:** el test cubre ciertas formas sintácticas, pero su inventario omite huecos demostrados y su justificación confunde no solicitar permiso con no poder escribir.

**Por qué importa:** `Path.open('w')` lleva el modo en el primer argumento, mientras el guard examina el segundo. Añadí al final del `__init__.py` de la copia un `with Path(<ruta propia>).open('w')` que escribió un fichero al importar. Los **116 tests disponibles pasaron**, los cuatro del corpus se saltaron y el fichero existió. No se solicitó `WRITE_CASE`. `CaseWorkspace.exigir` es una comprobación explícita (`workspace_model.py:528–536`), no un control del sistema sobre `open`.

**Verificación:** control positivo propio con `write_text` detectado y ejecutado; control negativo del instrumento con `Path.open('w')` no detectado y ejecutado; después mutación sobre el paquete y corrida completa. Un segundo mutante añade un escritor `write_text` al CLI y también sobrevive, porque el glob no lo examina. Inventario detallado más abajo.

**Remedio:** limitar la garantía publicada a lo que se mide; incluir todos los entrypoints y controles positivos por forma de llamada. Complementar el AST con instrumentación de efectos y pruebas de integración. Un guard mejorado seguirá requiriendo revisar efectos transitivos; no convertir una denylist ampliada en prueba de imposibilidad.

### H-05 — La dependencia de resolución renombra un registro corrupto al leerlo

**Severidad: ALTO. Ancla:** `core/procedimiento/__init__.py:45–53`; cadena concreta en `core/casos/workspace_resolver.py:74`, `:230–233`, `core/casos/workspace_registry.py:170–177`, `:213–218`.

**Qué está mal:** el registro empleado por el resolver llama a `_cuarentena` y `os.replace` durante una lectura fallida.

**Por qué importa:** una vez corregido H-02, resolver para un informe puede renombrar `<W-code>.json` a `.corrupto.<fecha>` sin haber llegado a `READ_CASE`. El efecto está fuera del expediente, pero dentro del «nada en disco» del mandato. La ausencia de capacidad de escritura no lo detiene.

**Verificación:** preparé un registro privado sintético con JSON corrupto e inyecté únicamente un constructor compatible que entrega el `WorkspaceRegistry` real. `_resolver` lanzó `RegistryUnreadable` y el JSON quedó renombrado. **Es un efecto latente, no una ejecución alcanzable de la fachada sin modificar:** H-02 corta antes. No presento la adaptación como si fuese head literal.

**Remedio:** un modo de lectura del registro que informe la corrupción sin mover bytes, o una frontera distinta explícitamente autorizada para cuarentena. Reparar el arranque no puede darse por suficiente para conservar el contrato de esta mitad.

### H-06 — Se autoriza una raíz, pero el universo se lee de otra

**Severidad: ALTO. Ancla:** `core/procedimiento/__init__.py:59–64`, `:71–73`; `core/procedimiento/universo.py:51–58`.

**Qué está mal:** `universo.leer` recibe solo `case_id`; reconstruye las rutas por catálogo en vez de recibir `ws.working_root`.

**Por qué importa:** `RegistroOcurrencias → registro_path → caso_path → case_locator.path_for` y `read_pull_state → case_locator.buscar` vuelven a `CASOS_ROOT`. Un checkout/scratch puede tener el mismo identificador y datos distintos al canon: la vista mezcla su mapa, bytes y cobertura locales con ocurrencias/D8 canónicos. Un scratch no publicado puede fallar aunque el workspace local esté autorizado. El permiso concedido para la copia local no autoriza por sí solo ese segundo árbol.

**Verificación:** catálogo y local sintéticos con doc_id `CANON` y `LOCAL`; registro real de un scratch y adaptación exclusiva del constructor de H-02. El resolver devolvió `local_scratch` con raíz local, pero el borrador enumeró `CANON`. `INTEGRACION.json`, `raiz_partida`. No fue necesario modificar los lectores.

**Remedio:** propagar una única raíz autorizada a registro y D8; no re-resolver identidad como ruta tras autorizar. Probar la fachada con dos copias divergentes, no solo funciones a las que se inyecta el mismo doble.

### H-07 — La contención no se aplica a todos los lectores y la autorización borra una junction de la raíz

**Severidad: ALTO. Ancla:** `core/procedimiento/sede.py:60`, `core/procedimiento/mapa.py:105–106`, `:236–242`, `core/procedimiento/artefacto.py:102–105`, `:138–140`.

**Qué está mal:** mapa, cobertura y artefacto derivado se abren o aceptan mediante concatenación directa; además `raiz_autorizada` resuelve antes de que `contener` pueda inspeccionar los ancestros originales.

**Por qué importa:** una junction en `05_Procedimiento` permite leer un mapa exterior y una en `01_OCR` permite anunciar un representante exterior. El origen crudo sí pasa por `contener`, pero el convertido no. El test del ancestro llama directamente a `contener(enlace, ...)`; la secuencia de producción `contener(raiz_autorizada(ws), ...)` ya ha borrado ese enlace.

**Verificación:** junctions reales, dentro del scratch: mapa exterior aceptado; OCR exterior seleccionado sin bloqueo; `contener(link,'x')` rechazó y `contener(raiz_autorizada(ws),'x')` aceptó la misma raíz lógica. Para esta última sonda se usó un workspace mínimo; no se afirma que todo resolver produzca siempre una raíz con junction.

**Remedio:** comprobar la cadena antes de la primera resolución y usar una frontera común para todas las lecturas y para las rutas de representantes. En 4b habrá que revalidar al operar: una comprobación por nombres no cierra por sí sola las carreras.

### H-08 — «Solo dos tags redirigen» no es una clasificación completa

**Severidad: MEDIO. Ancla:** `core/procedimiento/sede.py:28–36`, `:63–71`, `:77–86`.

**Qué está mal:** se permite todo tag salvo dos y se convierte cualquier `OSError` de `lstat` en «no redirige»; agotar 64 ancestros también devuelve éxito.

**Por qué importa:** un tag no enumerado no queda probado inocuo. Microsoft define el bit Name Surrogate para otra entidad nombrada, no únicamente dos valores posibles; existen otros tags y filtros. La distinción nube/redirección debe conservarse sin afirmar que todo lo desconocido es nube. [Microsoft: Reparse Point Tags](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-tags).

**Verificación:** `_redirige` con `st_reparse_tag=0xA000001D` y modo directorio simulado devolvió False. La sonda acredita la clasificación del guard, **no** una fuga real a través de un filtro instalado. Leí los retornos permisivos de error y límite; no provoqué ACL ni cadenas de más de 64 ancestros reales.

**Remedio:** expresar una política de tags por sus propiedades y casos admitidos; distinguir inexistencia de imposibilidad de inspeccionar y no dar por limpia una cadena incompleta. Mantener el control positivo del placeholder sin extrapolarlo a todos los proveedores.

### H-09 — Los duplicados no heredan la decisión del titular y el orden sigue influyendo

**Severidad: ALTO. Ancla:** `core/procedimiento/artefacto.py:119–121`, `:188–204`.

**Qué está mal:** el índice por SHA conserva la última fila y la rama de alias mira una sola referencia y la existencia de un PDF, sin resolver el método ni el bloqueo del titular.

**Por qué importa:** titular y copia comparten SHA en el productor real. Si gana una fila de titular `error`, bloquea; si gana su alias, vuelve a crudo. Para OCR ausente sucede la misma degradación en la representación de filas admitida por el cargador. Una cadena `copia → medio → titular` no llega al PDF existente del titular; un ciclo o un titular inexistente se aceptan como crudo. El test de duplicado usa `OTRO_SHA` para el titular, por lo que no ejercita la identidad byte-idéntica que anuncia.

**Verificación:** invertí dos filas del mismo SHA: bloqueo frente a elección de crudo. Ejecuté cadena con PDF del titular, ciclo de dos alias y alias de titular `error`: todos devolvieron crudo sin bloqueo. Contrasté `_fila_duplicado` y `_alias_o_none` en `sala_maquina.py:1097–1144`. No afirmo que el productor normal fabrique ciclos; el consumidor tampoco los valida si los recibe.

**Remedio:** resolver un grafo de titulares con detección de ciclos/ausencias, comprobar identidad y heredar la elección completa; hacer determinista el tratamiento de filas del mismo SHA. No decidir clase por la mera existencia de un PDF residual.

### H-10 — La cadena de custodia omite el SHA de la ocurrencia

**Severidad: ALTO. Ancla:** `core/procedimiento/vista.py:129–151`.

**Qué está mal:** se hashea el crudo y se busca ese SHA en cobertura, pero nunca se compara con `rev['sha256']`.

**Por qué importa:** un fichero sustituido por bytes de otro documento que también tenga cobertura se acepta para el doc_id original. También puede quedar una ocurrencia vieja tras reprocesar el fichero sustituido: cobertura y bytes coinciden entre sí, pero no con la identidad documental declarada. I5 exige verificar ocurrencia → cobertura → bytes, no únicamente sus dos últimos nodos.

**Verificación:** ocurrencia con SHA anterior, fichero con contenido nuevo y cobertura del SHA nuevo: informe completo, sin avisos ni bloqueos. El test actual solo cubre que el SHA nuevo esté ausente de la cobertura.

**Remedio:** cruzar SHA vigente de ocurrencia con bytes actuales antes de seleccionar; el override de cobertura no debe reemplazar una comprobación de identidad documental.

### H-11 — Dos filas pueden tener el mismo destino final y declararse completas

**Severidad: ALTO. Ancla:** `core/procedimiento/mapa.py:289–300`; `core/procedimiento/vista.py:155–159`.

**Qué está mal:** la comparación sin extensión para CRM se cruza con el basename completo de despacho, y no hay comparación posterior de los nombres efectivos.

**Por qué importa:** una entrada CRM `orden=00, descripcion=documento`, cuyo representante es PDF, y una propia `fichero=00_documento.pdf` pasan el mapa: compara `00_documento` con `00_documento.pdf`. Después ambas apuntan al fichero manual. No hay sobrescritura actual desde el informe, pero 4b no puede consumir esta salida como un conjunto de destinos validados. El truncado también necesita comparación posterior.

**Verificación:** mapa cargado y vista construida con fichero propio real: dos filas `00_documento.pdf`, cero bloqueos y `completo=True`.

**Remedio:** comprobar unicidad tras resolver extensiones y presupuesto de longitud, entre todos los orígenes, además de las claves lógicas. Mantener separada la puerta de propiedad de destinos existentes de 4b.

### H-12 — «Completo» ignora que el universo es incoherente

**Severidad: ALTO. Ancla:** `core/procedimiento/vista.py:59–65`, `:167–169`; `scripts/procedimiento.py:67–68`.

**Qué está mal:** `Informe.completo` solo considera pendientes y bloqueos; las incoherencias no afectan al valor ni al código de salida.

**Por qué importa:** si D8 anuncia 99 documentos y el registro contiene uno asignado, el usuario recibe la discrepancia y a la vez «completo: sí»; el CLI sale con 0. Una automatización puede tomar el resumen como prueba de completitud pese a no conocer 98 documentos. Igual sucede con D8 ausente o errores del pull si no generan otro bloqueo.

**Verificación:** sonda con total 99, una ocurrencia asignada y cobertura válida: `incoherencias` no vacío y `completo=True`. La conexión al exit code se verificó por lectura; la fachada literal no llega a ella por H-02.

**Remedio:** incorporar coherencia al criterio o exponer dos estados inequívocos y un resultado no satisfactorio para integridad desconocida. No equiparar «todas las filas conocidas tienen carpeta» con «todo lo que el CRM enumera».

### H-13 — Siguen entrando nombres y tipos inválidos en el mapa

**Severidad: MEDIO. Ancla:** `core/procedimiento/mapa.py:32`, `:159`, `:187–195`, `:207–209`, `:253–256`, `:304–305`.

**Qué está mal:** la gramática con `match` y `$` acepta un salto final; faltan reservados Windows y validación estricta de varios tipos.

**Por qué importa:** `orden: "00\n"` se acepta y genera un nombre con control prohibido; el resultado CRM no pasa por `_validar_nombre_windows`. `COM¹.docx` se acepta aunque Windows reserva COM/LPT con superíndices ¹, ² y ³. [Microsoft: Naming Files, Paths, and Namespaces](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file). Además `doc_id: ['1']` y una descripción dict se convierten a texto; `expediente_crm: true` pasa a `True` y un expediente de espacios pasa a vacío después de validarse. `sin_asignar: 1` termina en `TypeError`, fuera del error de validación agregado.

**Verificación:** todas esas entradas se ejecutaron mediante `mapa.cargar`; los resultados están en `SONDAS.json`. No intenté abrir un dispositivo reservado. La aceptación del salto final no es hipotética ni depende de normalización de Drive.

**Remedio:** `fullmatch` con gramática deliberada, validación del nombre final y de tipos antes de coercionar, control de vacío después de normalizar y conjunto completo de reservados relevantes. Convertir errores de esquema en problemas concretos del mapa.

### H-14 — El presupuesto arregla el temporal ASCII, pero no toda la longitud prometida

**Severidad: MEDIO. Ancla:** `core/procedimiento/mapa.py:133–147`, `:211–233`; `core/procedimiento/vista.py:122–124`, `:155–156`.

**Qué está mal:** se cuentan puntos de código Python y solo se aplica el presupuesto al destino CRM; despacho no se valida por longitud.

**Por qué importa:** una raíz con caracteres fuera del BMP consume más unidades UTF-16 que `len`. En la sonda, el temporal autorizado tiene 259 puntos de código y 294 unidades UTF-16. El mapa también acepta un basename de despacho de 265 caracteres. Es incumplimiento del presupuesto, aunque este host pueda soportar determinadas rutas largas.

**Verificación:** cálculo ejecutado del temporal con raíz sintética Unicode; carga ejecutada del basename largo. El mutante que retira el margen del temporal ASCII sí muere: esa parte de la remediación es real.

**Remedio:** presupuestar unidades de la API de destino y verificar también nombres propios sin truncarlos ni renombrarlos. Definir el contrato del temporal de 4b: los seis dígitos de PID son hoy una hipótesis del plan, no una longitud garantizada por la futura implementación.

### H-15 — eco_crm solo valida la mitad de la puerta 7-bis

**Severidad: MEDIO. Ancla:** `core/procedimiento/vista.py:94–106`, `:108–129`.

**Qué está mal:** se verifica pertenencia al universo, pero no que el mismo doc_id esté ya asignado como entrada CRM.

**Por qué importa:** una fila despacho con eco de la demanda y una fila CRM de ese mismo doc_id producen dos representantes y un informe completo. El spec §5.7-bis prohíbe expresamente esas dos vías simultáneas. Los ecos repetidos también se reducen a la última clave en el dict sin diagnóstico.

**Verificación:** ejecuté un mapa con una entrada propia existente, `eco_crm='1'` y otra CRM para `1`: dos filas y ningún bloqueo. La repetición de ecos se constató leyendo la asignación del dict; no se exige aquí detectar un eco falso por igualdad de bytes, porque el spec reserva esa declaración al letrado.

**Remedio:** validar la compatibilidad de asignaciones y ecos antes de producir filas. La persistencia de correspondencia pertenece a 4b, no se contabiliza aquí como escritura faltante.

### H-16 — El test del corpus no entrega su cobertura al selector

**Severidad: ALTO. Ancla:** `tests/test_procedimiento_regresion.py:51–67`.

**Qué está mal:** convierte las filas del fixture, pero en cada llamada pasa `artefacto.Cobertura()` vacía y `sin_cobertura_ok=True`.

**Por qué importa:** el test recorre la rama de override sin examinar el método, padre, estado ni alias de la fila recibida. La mayoría resuelta será 100 % mientras funcione ese fallback, aunque todos los selectores de cobertura estén rotos. Esto oculta precisamente H-03 y H-09; añadir una mayoría no remedia el instrumento.

**Verificación:** llamé al cuerpo exacto del test con 60 filas sintéticas, inutilizando `METODOS_CON_ARTEFACTO` y `METODOS_CRUDO`: siguió pasando. No fabriqué fixtures que se hicieran pasar por W-02VEKE y los cuatro saltos originales siguen siendo cobertura ausente.

**Remedio:** construir índices con las filas del fixture, materializar representantes sintéticos apropiados y exigir resultados por clase/caso. Conservar un control positivo de tamaño sin usarlo como sustituto del contrato del selector.

### H-17 — «Materializada» se publica como existencia física sin comprobarla

**Severidad: MEDIO. Ancla:** `core/procedimiento/universo.py:60–61`, `:73–84`, `:106–111`; `core/procedimiento/borrador.py:53`.

**Qué está mal:** el conjunto materializado se toma del estado del registro, pero su descripción y el borrador lo presentan como fichero actualmente en disco.

**Por qué importa:** `RegistroOcurrencias.materializadas` filtra por estado, no hace I/O (`core/ocurrencias_crm.py:308–314`). Tras eliminar un crudo, D8 y ocurrencias pueden seguir cuadrando; el borrador dice `en_disco: true` solo porque la ruta es no vacía. El informe detectará la ausencia si esa entrada llega a asignarse como CRM, pero no verifica todo el universo al enumerarlo. Un desvío de intake a `_pendiente_checkin` también conserva la ruta intencionada en el registro; `sync_sudespacho.py:1529–1540`, `:1654–1661` muestran por qué estado no equivale a disponibilidad en esa ruta.

**Verificación:** conjunto sintético marcado materializado con ruta inexistente: `incoherencias()==()`. Lectura del productor y del test de existencia posterior de `vista.py:143–147`. No se reprodujo un intake remoto ni se atribuye todo estado materializado a un fallo.

**Remedio:** distinguir «registrada como materializada» de «presencia física verificada» o comprobar las rutas bajo la sede autorizada. No volver a exigir que las 76 enumeradas estén descargadas: eso reintroduciría H-08 de la ronda anterior.

## Respuestas expresas a las prioridades del mandato

### Escrituras y cobertura de los nueve módulos

| Módulo | Resultado de la revisión |
|---|---|
| `sede.py` | `exigir(READ_CASE)`, `lstat` y resolución; ninguna escritura directa. No obtiene capacidades mutantes. |
| `carpetas.py` | Constantes y pertenencia; sin I/O. |
| `universo.py` | Lectura de ocurrencias y D8; sus loaders utilizados no guardan el caso, pero vuelven al catálogo. |
| `mapa.py` | Lee YAML; genera nombres en memoria; no guarda el mapa. |
| `artefacto.py` | Lee JSON, construye índices, consulta existencia; importar `DocCobertura` no llama a `sala_maquina.ejecutar`. |
| `vista.py` | Lee y hashea crudos; construye dataclasses; no publica ficheros. |
| `borrador.py` | `yaml.safe_dump` sin stream devuelve texto; no escribe un YAML. |
| `__init__.py` | No escribe directamente; arranque roto y dependencia de registro con cuarentena mutante latente. |
| `scripts/procedimiento.py` | Emite stdout/stderr y códigos de salida; no abre fichero de salida. Está fuera del guard. |

Hice además un import de `core.procedimiento` y `scripts.procedimiento` con bytecode desactivado y un audit hook que bloqueaba aperturas de escritura, mutaciones de rutas y subprocesos: no se produjo ninguno de esos eventos. Es cobertura de esos imports en este entorno, no de cada rama futura. El bytecode normal de Python y la redirección de stdout por el usuario no son escrituras documentales del motor y no los uso como hallazgos. La ampliación del helper y la cuarentena sí son efectos de código de la cadena examinada, con los límites de alcance explicados en H-01/H-05.

El control positivo existente comparte `_escrituras` con el guard y detecta las cuatro muestras `write_text`, `mkdir`, `copy2`, `open(...,'w')`. Los positivos de `replace` también discriminan sus dos muestras. Esto mejora de verdad el control anterior duplicado; **no basta** para cubrir otras firmas ni otros módulos. El control separado de población exige al menos siete módulos y dos nombres, no los nueve entrypoints del mandato.

Inventario de lo no cubierto, con consecuencias prácticas:

| Frontera | Ejemplos y resultado |
|---|---|
| Firma del método | `Path.open('w')` no detectado; ejecutado y mutación completa superviviente. |
| Modos de apertura | `open(...,'wb+')`, `open(...,'at')` no detectados; la enumeración también omite otras permutaciones válidas. |
| Flujo de datos | Modo en variable, por expresión o `**kwargs`; función importada con alias o guardada en variable; no se sigue el valor ni su identidad. Sondas de variable y alias no detectadas. |
| Operaciones no enumeradas | `os.open` con flags de creación/escritura, `os.truncate`, métodos de escritura sobre handles y otros sumideros no incluidos. Los dos primeros se probaron contra el analizador. |
| Streams | `json.dump(..., fh)` y `yaml.safe_dump(..., stream=fh)` pueden escribir sin un nombre de la denylist; ambas formas pasaron el analizador. |
| `replace` | `p.replace(target='x')` no detectado. En cambio `os.replace(*args)` **sí** se detecta: el hueco que declara el docstring para esa forma es falso. `str.replace` con un solo argumento ni siquiera es una llamada válida ordinaria de str. |
| Efectos transitivos | Métodos de `core`, constructores, imports, callbacks o librerías pueden escribir; permitir el prefijo `core` no audita su implementación. `RegistroOcurrencias.save()` pasa el analizador; la cuarentena real de workspace demuestra un caso pertinente. |
| Inventario de ficheros | Solo `core/procedimiento/*.py`, sin CLI, helpers ni subpaquetes futuros. Escritor añadido al CLI: superviviente. |
| Capacidades | Búsqueda textual de `Capability.X`; no resuelve aliases, valores construidos ni otras formas sintácticas. Y aunque fuera perfecta no confina las APIs de fichero. |

El inventario no puede convertirse en lista finita de todas las formas Python posibles. Debe describir estas clases de limitación; no afirmar que hay solamente tres excepciones y que un permiso no solicitado compensa lo restante.

### Autorización

`raiz_autorizada` exige READ_CASE antes de devolver una raíz; el mutante que lo retira muere. Un `CaseWorkspace` real de modo bloqueado rechazó esa lectura en mi sonda. El resolver real con catálogo simulado prestado a otra máquina lanzó `CaseLocked`. **No encontré un camino literal por el CLI actual que lea el caso prestado: aborta antes por H-02.** La fachada no evita expresamente `exigir`, pero sus lectores posteriores ignoran la sede (H-06). Probar autorización sobre un doble de workspace no cubre esa integración.

`drive_accesible=True` se fija sin medir accesibilidad (`__init__.py:49,52`), a diferencia del patrón real de sala de máquina. No se acredita el comportamiento offline completo; deberá probarse al reparar esa resolución.

### Clases de rutas

- **8.3:** obtuve un alias real mediante `GetShortPathNameW`; la raíz abreviada fue expandida por `resolve` y `contener` produjo la ruta larga correcta. No encontré una salida de raíz por ese caso. No se demuestra la matriz de aliases 8.3 con todos los filtros o volúmenes.
- **Junction:** tests originales y sondas propias con enlaces reales; rechazo del hijo y del ancestro directos, pero huecos de composición/lectores en H-07.
- **Otros reparse points:** clasificación insuficiente demostrada por tag simulado; filtro real y ruta efectiva SIN VERIFICAR. No confundo un tag de nube con una junction.
- **`..` intermedio:** `sub/../sub` y el caso equivalente de `05_Procedimiento` se rechazan. El mutante muere específicamente por el caso que vuelve a entrar. `C:foo`, relativo a unidad, es aceptado como `foo` dentro de la raíz en la sonda; no demostré escape por ello.
- **Unicode:** `_slug` normaliza descripciones y los tests detectan su colisión. En el filesystem real del scratch, `é.txt` y `é.txt` conservaron bytes distintos y `samefile=False`: no invento una colisión NFC/NFD de Windows. La sincronización/normalización de Drive queda SIN VERIFICAR. Reservados y longitud sí tienen defectos concretos, H-13/H-14.
- **Rutas largas:** `contener` puede devolver una ruta inexistente con segmento de 270 caracteres; no es un preflight de longitud. El mapa debe cubrir esa validación y hoy no lo hace completamente. No se acredita fallo MAX_PATH del recorrido real del despacho.
- **Concurrencia:** inspección por nombres y posterior lectura no equivalen a acceso mediante handles fijados; carreras reales SIN VERIFICAR. 4b no podrá heredar una garantía temporal de estas comprobaciones.

### Los tres conjuntos del CRM

La corrección de D8 es **real**: `case_manager.py:1638` define documentos descargados; `sync_sudespacho.py:1494–1517` enumera y registra antes de filtrar, `:1519–1522` filtra, y `:1669` añade doc_ids después de descargar/materializar. Incluye descargas cuyo depósito físico se omite por deduplicación; no significa «ficheros nuevos escritos». `documents_total_crm` conserva el tamaño anterior al filtro y `update_pull_state` sustituye doc_ids de la corrida.

El caso 76 listadas, 2 materializadas y 2 descargadas es coherente y no se bloquea por los otros 74. No encontré un falso positivo de esa puerta en el caso normal acotado. Sí quedan límites: materialización nominal frente a disco (H-17), control por cardinalidad que no acredita una foto actual completa del CRM, ausencia de validación nueva del histórico y señal de completitud que ignora las incoherencias (H-12). El registro conserva revisiones históricas: dos listados de igual cardinalidad no prueban identidad de universo; no se afirma haber contrastado un CRM vivo.

### Selector y mapa

Los ocho nombres de método reales están enumerados: `pypdf`, `ocr`, `nativo`, `ofimatica`, `sin_soporte`, `vision`, `duplicado`, `error`; los cuatro estados base coinciden. **Enumerarlos no implica cubrir sus combinaciones reales:** H-03/H-09 lo demuestran. Hay además una rama `empty` que identifica como imagen cualquier extensión distinta de PDF o vacía (`artefacto.py:213–216`), y los estados desconocidos solo se avisan en ciertas ramas; estas limitaciones se constatan por lectura, sin atribuir estados nuevos al productor actual.

El mapa sí ha ganado gramática, booleanos estrictos para override, versión no booleana, rechazo de claves YAML repetidas y comparación casefold. La validación de nombres efectivos, tipos restantes, eco compatible y longitud sigue incompleta (H-11, H-13–H-15). No se requiere en 4a guardar ni el mapa ni el evento de ejercicio del override: esas escrituras corresponden a 4b.

## Dictamen de las remediaciones de la ronda anterior

Cada calificación se limita a la porción que corresponde a 4a. «Fuera de alcance» no significa remediado.

| Hallazgo anterior | Dictamen contra head |
|---|---|
| H-01 | **fuera de alcance** — propiedad al mover; H-11 actual entrega destinos colisionantes y obliga a 4b a recomprobarlos. |
| H-02 | **fuera de alcance** — adopción/journal no existen aquí; no vi reintroducción de adopción por igualdad de bytes. |
| H-03 | **incompleta** — se construye contención y hay junctions reales en tests, pero no cubre todos los lectores ni la composición con raíz autorizada (H-07/H-08 actuales). Su efecto destructivo queda para 4b. |
| H-04 | **fuera de alcance** — validación de ledger no implementada; la sede actual no sirve como garantía suficiente para sus rutas. |
| H-05 | **fuera de alcance** — carreras de publicación; nada de 4a fija handles ni mantiene validaciones hasta una escritura futura. |
| H-06 | **incompleta** — READ_CASE es real, pero fachada rota, raíz perdida en universo y dependencia que puede mutar (H-02/H-05/H-06 actuales). |
| H-07 | **fuera de alcance** — recuperación después de reemplazo; no hay transacción en 4a. |
| H-08 | **real** en la separación enumeradas/descargadas y el régimen acotado; no acredita existencia física ni permite ignorar incoherencias. |
| H-09 | **real** — universo sin ninguna ocurrencia lanza UniversoError; no se convierte en vista vacía. El test inyectado no sustituye la prueba pendiente de fachada reparada. |
| H-10 | **incompleta** — hash actual contra cobertura sí; SHA de la ocurrencia no (H-10 actual). |
| H-11 | **incompleta** — utiliza el slug del padre para el bundle OCR de su fixture, pero confunde sueltos con bundles y exige OCR a los digitales (H-03 actual). |
| H-12 | **incompleta** — métodos error/duplicado incorporados; cadenas, ciclos, herencia de bloqueo y orden por SHA siguen mal (H-09 actual). |
| H-13 | **fuera de alcance** — ledger y procedencia doble; `Fila` no transporta raw SHA ni identidad del derivado. 4b deberá obtenerlos y verificar de nuevo, no reconstruirlos desde una ruta de salida como si fueran evidencia. |
| H-14 | **incompleta** — eco inexistente bloquea, eco ya asignado como CRM no; persistencia diferida legítimamente a 4b. |
| H-15 | **real** para `'false'` y `version: true`; actor y evento al ejercer el override están fuera de 4a. |
| H-16 | **incompleta** — gramática, primer componente reservado, casefold y duplicados YAML son mejoras reales; quedan LF final, COM¹, coerciones y colisión efectiva CRM/despacho. |
| H-17 | **incompleta** — margen temporal ASCII probado y mutante muerto; longitud de despacho y unidades UTF-16 no cubiertas. |
| H-18 | **incompleta** — `borrador.proponer` existe, propone sin asignar fases y su roundtrip sintético pasa; el comando que lo hace accesible no funciona por H-02. |
| H-19 | **fuera de alcance** — no hay reconciliación de índice ni commit; H-12 actual desaconseja reutilizar `completo` como puerta de publicación. |
| H-20 | **fuera de alcance** — no se añadió el parser de bloques del índice; el helper ampliado debe mantenerse diferenciado del reconciliador futuro. |
| H-21 | **incompleta** — varios controles positivos y mutantes ahora discriminan, pero falta integración y el corpus conserva una garantía vacía (H-04/H-16 actuales). |
| H-22 | **fuera de alcance** — diseño rev. 2 reconoce el veto limitado de biblioteca; el diff no aporta un veto de PDF ni se le atribuye aquí. |
| H-23 | **fuera de alcance** — la remediación de PII fue anterior a este diff; fixtures reales, blocklist y genealogía de su retirada SIN VERIFICAR. |

El mandato enumera H-01 a H-05 como fuera de 4a. He respetado esa exclusión para las operaciones destructivas; explicito en H-03 anterior únicamente la propiedad de contención que el propio encargo exige auditar en `sede.py`, sin contar como pendiente aquí el `apply` retirado.

## Los mutantes

La afirmación exacta «25 mutantes muertos» queda **SIN VERIFICAR**: `scratch/mutar.py` no forma parte del objeto y sus cambios/logs no están disponibles. Reconstruí 13 cambios identificables del plan/tests; no los presento como identidad demostrada con los 25 del autor.

| Mutante reconstruido | Resultado ejecutado y poder discriminante |
|---|---|
| Retirar `exigir(READ_CASE)` | **MUERTO**: falla permiso ausente y registro de capacidad exigida. |
| Vetar todo tag distinto de cero | **MUERTO**: `test_un_tag_de_NUBE_no_veta_la_ruta`. La reescritura sí discrimina conducta. |
| Retirar rechazo léxico de `..` | **MUERTO**: caso `05_Procedimiento/../05_Procedimiento`; las otras guardas no bastan para esa entrada. |
| Invertir diferencia listadas/descargadas | **MUERTO**: intake acotado produce 74 pendientes tratados como incoherentes. |
| Retirar gramática de orden | **MUERTO**: seis entradas inválidas pasan. |
| Retirar tipo booleano del override | **MUERTO**: string `'false'` aceptado. |
| Volver a `.stem` para reservado | **MUERTO**: `NUL.extra.docx`. |
| Retirar margen temporal | **MUERTO**: el temporal excede el límite de la prueba. |
| Retirar casefold del tronco | **MUERTO**: dos nombres despacho que difieren en mayúsculas; la prueba CRM anterior no habría distinguido esto. |
| Ignorar grupo bundle | **MUERTO**: fixture de bundle OCR no obtiene representante del padre. No cubre passthrough ni bundle pypdf. |
| Retirar rama duplicado | **MUERTO**: test de titular. Su `OTRO_SHA` limita lo que prueba. |
| Retirar rama error | **MUERTO**: falla la explicación del motivo real; no se limita a exigir cualquier bloqueo. |
| Seleccionar primera fila en lugar de SHA actual | **MUERTO**: crudo sustituido obtiene cobertura impropia. No comprueba SHA de ocurrencia. |

Todos esos rojos tienen exit 1 y un `FAILED` en el test esperado; no son errores de sintaxis, colección o entorno. Los logs contienen el detalle.

Mutantes y contrapruebas mejores que sobreviven:

1. **Escritura real al importar el paquete con `Path.open('w')`: SOBREVIVE** a los 120 casos, con 116 verdes/4 saltados; crea `ESCRITURA_NO_DETECTADA.txt`. Es más concluyente que un simple fragmento AST: el efecto se ejecuta, la suite lo ve y sigue verde.
2. **Escritor `write_text` añadido al CLI: SOBREVIVE** a la misma suite. En este caso la función añadida no se invocó: demuestra ausencia de escaneo del entrypoint, no otra escritura ejecutada.
3. **Inutilizar selectores de crudo/convertido en el test de corpus: SOBREVIVE** al cuerpo de ese test con 60 filas sintéticas. No es una corrida del corpus real ni de toda la suite bajo ese mutante.

La campaña propia tuvo un fallo de arnés entre los 13 reconstruidos y los dos adicionales: comparaba texto LF leído con `read_text` con bytes CRLF decodificados. Lo reproduje y normalicé solo esa comparación; reanudé los dos pendientes. No conté aquel `AssertionError` de ancla como mutante muerto. Tras terminar, comprobé que los nueve módulos de `ejec` estaban restaurados **byte a byte** respecto a head.

## Lo que NO pude verificar

- **SIN VERIFICAR:** ascendencia de e783464/9c4d5c1, ausencia de cambios de otros commits y genealogía; no hay `.git`. La comprobación de hunks y los hashes son de contenido.
- **SIN VERIFICAR:** los 25 mutantes exactos del autor, su independencia y sus resultados históricos; falta el arnés. Se acredita solamente la reconstrucción descrita.
- **SIN VERIFICAR:** corpus W-02VEKE, sus cuatro regresiones, anonimización completa y blocklist; no hay fixtures. Los saltos no estaban ocultos y no se cuentan como defecto de ejecución.
- **SIN VERIFICAR:** reparto 9/5/15/12/29 del piloto W-02MA0R, calidad real y cribado de OCR ciego de ambos expedientes; no se accedió a esos datos.
- **SIN VERIFICAR:** reparse tag de un fichero real de `G:`, filtros de nube, WSL/otros reparse points efectivos, sincronización Unicode y rutas largas en Drive. Se ejecutaron junctions, un alias 8.3 y ficheros Unicode locales; se distinguieron las simulaciones de los enlaces reales.
- **SIN VERIFICAR:** matriz completa de ACL, errores de lstat, más de 64 ancestros, enlaces `/D`, todos los namespaces Windows y carreras entre inspección y uso. No se infiere seguridad de los casos locales medidos.
- **SIN VERIFICAR:** CRM/Drive vivos, intake remoto, checkout/checkin distribuidos y funcionamiento offline completo de la fachada reparada. La reproducción de raíz partida fue sintética y adaptó exclusivamente el constructor.
- **SIN VERIFICAR:** OCR, LibreOffice y fidelidad visual reales. La sonda del productor ejecutó su lógica de construcción de filas con dependencias simuladas, no esos motores.
- **SIN VERIFICAR:** suite global del repositorio y `session_close`; se ejecutaron los 120 casos de la pieza con dos semillas y 21 tests relacionados. No se acredita aceptación global a partir de ese subconjunto.
- **SIN VERIFICAR:** transacción, journal, ledger, propiedad, eventos de override e índices futuros de 4b. Se señalaron dificultades concretas para su consumo sin calificarlos como funcionalidades incumplidas de 4a.

Interpreté el apartado 0-bis como auditoría ordinaria de efectos y completitud de pruebas. Las muestras que escriben o mutan se limitaron a ficheros sintéticos propios; ninguna intervención tuvo por objeto eludir un control de un sistema externo. La adjudicación de cada hallazgo corresponde al autor contra las fuentes.

## SHA-256 del parche al cerrar

`f4986a504db01b7c4f79d5f33cb28ea54f6e7876a86e94aa826869347e080dd2`

Coincide con el digest inicial. El informe se entrega para archivo literal, en UTF-8 sin BOM, LF y un único salto final. No se ha realizado una segunda pasada de cortesía.

NO-SHIP
<!-- informe-literal:fin:p4ad -->

## 2. Evidencia verificada por mí al adjudicar

Lo que sigue lo comprobé **yo**, contra la fuente y no contra el informe, antes de aceptar
ningún hallazgo. Solo consta aquí lo que miré.

| Afirmación del revisor | Comprobado en | Resultado |
|---|---|---|
| `parent_sha256` **no** es un marcador de segmento, y el productor lo rellena en el camino *passthrough* con `parent_slug` vacío (H-03) | `core/sala_maquina.py:937-938` — `return [DocCobertura(..., d.sha256, parent_sha256=d.sha256, tipo=tipo_pass)]` en la rama `passthrough_retira_bundle`; y el propio dataclass en `:192-196`: `parent_sha256` = «sha del fichero FÍSICO de origen; **clave del estado idempotente por bundle**», mientras `parent_slug` = «slug del bundle **si es un segmento**; vacío si documento suelto» y `doc_id` = «vacío = documento suelto» | **CONFIRMADO, y es el defecto más caro del diff.** Agrupé por la clave de idempotencia en vez de por el marcador de segmento. Un documento suelto que pasó por la detección de bundles se trata como bundle sin padre y **se bloquea**. Mis tests no podían verlo: mis fixtures ponían `parent_slug` siempre que ponían `parent_sha256`, o sea que fabricaban un mundo en el que mi error no existe. |
| Mi guard no detecta `Path.open("w")` (H-04) | `tests/test_procedimiento_sin_escritura.py:55` — `args = list(nodo.args[1:2]) + [...]`. En `open(path, "w")` el modo es `args[1]`; en `Path(x).open("w")` es `args[0]` | **CONFIRMADO.** Y no estaba en mi inventario de huecos declarados, que es lo que agrava el hallazgo: el test declaraba tres excepciones y esta es una cuarta que no menciona. Él además la **ejecutó**: la escritura ocurre al importar y los 120 tests siguen verdes. |
| El glob del guard deja el CLI fuera (H-04) | `tests/test_procedimiento_sin_escritura.py:12` — `PAQUETE = … / "core" / "procedimiento"`, y `scripts/procedimiento.py` no cae ahí | **CONFIRMADO.** El entrypoint del usuario no lo mira nadie. |
| La Tarea 2 amplía los destinos de un escritor (H-01) | El propio diff: `.claude/skills/_shared/registrar_outputs.py`, `SUBDESTINOS_EXTRA` pasa de una entrada a seis, y `DESTINOS_VALIDOS` se deriva de ella. Contra mi propia restricción global del plan 4a: «Cero escrituras en el expediente. Ninguna. Ni un fichero de estado, ni un log, ni un `mkdir`» | **CONFIRMADO, y es una contradicción que escribí yo.** El plan pone la ampliación del helper en la Tarea 2 *y* declara que la pieza no escribe nada. Las dos cosas no pueden ser verdad: `registrar_outputs` crea el directorio y su `_index.md` en la fase. |
| La raíz autorizada no llega a los lectores del universo (H-06) | `core/procedimiento/__init__.py` — `universo.leer(case_id, expediente_id)` recibe el **case_id**, no la raíz; y `universo.leer` construye `RegistroOcurrencias(case_id)` y llama a `read_pull_state(case_id, …)`, que resuelven por `case_locator` contra `CASOS_ROOT` | **CONFIRMADO.** Autorizo una raíz y leo otra. En un checkout con el mismo identificador, la vista mezcla mapa y bytes locales con ocurrencias y D8 del canon. |
| `Informe.completo` ignora las incoherencias (H-12) | `core/procedimiento/vista.py` — `return not self.sin_asignar and not self.bloqueos`; y `scripts/procedimiento.py` sale con `0 if inf.completo else 1` | **CONFIRMADO.** El CLI puede imprimir la discrepancia de D8 y a la vez «completo: sí» con exit 0. Una automatización tomaría eso por completitud. |
| Mi test del corpus pasa una cobertura VACÍA al selector (H-16) | `tests/test_procedimiento_regresion.py` — `artefacto.elegir(tmp_path, artefacto.Cobertura(), …, sin_cobertura_ok=True)` | **CONFIRMADO, y es el mismo defecto que la R1 anterior señaló en los tests de corpus de la rev. 1.** Lo repetí: el test recorre solo la rama de override, así que la «mayoría resuelta» sale del *fallback* y no del selector. Él lo demostró inutilizando los dos sets de métodos: el test siguió pasando. |
| La corrección de D8 es real (dictamen sobre H-08 de la ronda anterior) | `core/case_manager.py:1638` y `core/sync_sudespacho.py:1494-1522, 1669` | **CONFIRMADO por él, con más detalle que yo:** el productor enumera y registra **antes** de filtrar, y añade `doc_ids` después de descargar. Añade un matiz que yo no tenía: incluye descargas cuyo depósito físico se omite por deduplicación, así que `doc_ids` tampoco significa «ficheros nuevos escritos». |

**Los dos hallazgos que ya estaban remediados al llegar el informe, con su fecha:** el
`TypeError` de `WorkspaceRegistry()` (H-02) y el `drive_accesible=True` a pelo salieron de mi
*smoke test* del CLI y se corrigieron en `16c646a`, con su test de fachada
(`tests/test_procedimiento_fachada.py`). El objeto revisado es `9c4d5c1`, anterior a esa
corrección, así que **el revisor los reporta con razón** y no se cuentan como pendientes.
Su verificación con `CliRunner` es mejor que la mía y su observación de que `TypeError` no
estaba en `_ERRORES` del CLI es un defecto adicional que yo no había visto.

**Lo que NO verifiqué yo, y por tanto no acredito:** las tres contrapruebas que sobreviven
(H-04, y el escritor del CLI, y la del corpus) las **ejecutó él**; yo confirmé la causa
leyendo mi propio código, pero no reproduje sus corridas. Los hallazgos H-07 a H-11, H-13 a
H-15 y H-17 los acepté leyendo mi código y siguiendo su escenario, sin re-ejecutar sus sondas.
La diferencia importa: en esos el verificador fue él.
