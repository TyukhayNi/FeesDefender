---
tipo: revision-adversarial
objeto: "plan 2026-09-09-vista-procesal-pieza4.md — vista procesal de 05_Procedimiento, pieza 4"
objeto_rev: "1"
commit: "8f9ad84"
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: v4p1
sha256_informe: b39f7bce53bc0d881dbec1b5d03a5f092afc32cb8f1d26d16a57056499e037f8
adjudicado_en: docs/superpowers/plans/2026-09-09-vista-procesal-pieza4.md §10
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre el PLAN.** Le tocan **dos** rondas por radio de daño:
> la pieza decide quién puede escribir sobre qué copia —lleva un ledger de propiedad— y sus
> operaciones `borrar`, `reemplazar` y `mover` actúan sobre el expediente real de un pleito en
> curso. Esta es la del diseño; la del diff vendrá después.
>
> El §1 conserva la voz del revisor **sin una coma cambiada**; el §2 es la evidencia que
> verifiqué yo contra la fuente. **La adjudicación NO está aquí:** va en el §Adjudicación del
> plan, que es el documento que la decisión modifica.
>
> **Objeto:** copia externa del commit `25c07bc` con `git archive` (1.245 ficheros, sin `.git`).
> El plan revisado tenía `sha256 aaaf72e7…955050`, y el revisor lo declaró **idéntico al abrir
> y al cerrar** — la prueba de no-mutación que aquí sustituye al `git status`. Lo comprobé yo
> también, con el mismo valor. El commit del frontmatter es `8f9ad84` y no `25c07bc` porque
> el original se **enmendó** para retirar la PII del hallazgo H-23 antes de que la rama saliera
> de esta máquina; el contenido revisado es el de `25c07bc`, cuyo digest consta arriba.
>
> **Lo que hace a esta ronda distinta de una de lectura: el revisor ejecutó.** Creó una
> *junction* real de Windows, montó tres contrapruebas de mutación, ejecutó 19 sondas sobre
> árboles sintéticos y extrajo los bloques literales del plan para correrlos — 84 casos, de los
> que **5 salieron rojos ya**. Y auditó **los 70 tests del plan uno a uno** en una tabla,
> preguntándose por cada uno «¿pasaría con el defecto que dice cazar?». **Tres pasan con el
> defecto puesto**, comprobado ejecutando, y uno de ellos —el de `adoptar`— *bendecía* el
> defecto de propiedad en vez de cazarlo. Nada de eso sale de leer.
>
> **Cobertura ausente que el propio revisor declaró, y que no se disimula:** el corpus real de
> W-02VEKE y el reparto del piloto W-02MA0R quedan **SIN VERIFICAR** (no se abrieron los
> expedientes ni se generaron los fixtures, así que los tres tests de regresión no corrieron);
> tampoco la suite completa, la segunda semilla, los motores reales de OCR/LibreOffice, las
> carreras reales con Word o Drive, ni el fallo efectivo por MAX_PATH. Trece declaraciones
> SIN VERIFICAR en total. Ninguna de ellas es un «está bien».
>
> **Digest:** el `sha256` del bloque canonicalizado coincide con el del `INFORME.md` original
> (`b39f7bce53bc…`), porque el revisor lo escribió en LF con un solo salto final. La cadena se
> verifica por tanto contra su salida, no solo contra sí misma. Y no se calculó hasta que el
> **proceso** terminó: la presencia del fichero no es la señal, y una vez ya archivé por poco
> un informe a medio escribir.

## 0. Mandato entregado, literal

<!-- mandato-literal:inicio:v4p1 -->
# Mandato — Revisión adversarial R1 del PLAN de la «vista procesal» (pieza 4)

## 0. Higiene del workdir (lee esto primero)

Tu directorio de trabajo debe contener **solo este `MANDATO.md`**. Si encuentras cualquier otro
fichero (un `INFORME.md`, un `_stdout.log`, un `VEREDICTO.md`), **no lo leas**: puede ser el trabajo
de otra ronda sobre otro objeto. Decláralo en la **primera línea** de tu informe y sigue.

## 1. Qué eres y qué NO eres

Eres el revisor adversarial. Tu trabajo es **atacar**, no aprobar. No tienes que ser amable ni
equilibrado: si el plan es malo, dilo. Pero **no inventes**: un hallazgo que no puedas anclar a una
línea concreta del objeto no vale. Y **«no pude comprobarlo» NO es «está bien»**: cuando no puedas
verificar algo, escribe literalmente **SIN VERIFICAR** y por qué. Es la diferencia más importante de
este mandato: un revisor que no corre **no refuta, deja sin verificar**.

**No eres el juez.** El autor adjudicará cada hallazgo contra la fuente. Tu informe se archivará
**literal** en un acta, así que escríbelo para ser leído tal cual.

## 2. El objeto

Copia congelada del repo FeesDefender, commit `25c07bc66d319f79d940d7c61c141e7233b9f72b`:

    C:\t\obj-vistaproc-p4-r1-2026-09-09-1307\

Es **solo lectura por construcción**: está fuera del repo y no tiene `.git`. **No la modifiques.**
Si necesitas ejecutar algo que escriba, copia a tu workdir. No puedes acreditar por genealogía que
esa copia sea ese commit (no hay `.git`): verifica **contenido**, no ascendencia.

**Al abrir y al cerrar**, computa y reporta:

    cd C:\t\obj-vistaproc-p4-r1-2026-09-09-1307
    python -c "import hashlib,pathlib;p=pathlib.Path('docs/superpowers/plans/2026-09-09-vista-procesal-pieza4.md');print(hashlib.sha256(p.read_bytes()).hexdigest())"

Los dos digests van en tu informe. Es la prueba de no-mutación que sustituye a `git status`.

### El objeto revisado, en concreto

**Lo que se revisa:**

- `docs/superpowers/plans/2026-09-09-vista-procesal-pieza4.md` — **el plan. Esto es el objeto.**

**Contra qué se revisa (fuentes de verdad, no objeto):**

- `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md` — el spec cerrado,
  v3.1, con sus decisiones §0 y sus puertas §5.
- `core/ocurrencias_crm.py` — pieza 2, YA MERGEADA. El registro de ocurrencias que el plan consume.
- `core/sala_maquina.py` — `DocCobertura`, `cobertura_desde_dicts`, `_sala_maquina_dir`.
- `core/config.py` — `CASO_SUBDIRS`, `GRUPOS_MERGE` (pieza 1, ya mergeada), y la prosa sobre
  `05_Procedimiento` en torno a la línea 470.
- `core/case_manager.py` — `read_pull_state` y el esquema D8.
- `core/repository_checkout.py` — el veto de grupo (pieza 1).
- `scripts/_mutex_cli.py` — `sostener`, `w_code_de`, y los avisos.
- `.claude/skills/_shared/registrar_outputs.py` y `scripts/sync_skill_helpers.py` — el helper que el
  plan amplía y su sincronización a siete skills.
- `CLAUDE.md` — las reglas del proyecto que el plan tiene que respetar.

## 3. Por qué esta pieza merece dos rondas, y qué implica para ti

La pieza **decide quién puede escribir sobre qué copia** (un ledger de propiedad) y **puede destruir
datos de cliente**: sus operaciones `borrar`, `reemplazar` y `mover` actúan sobre el expediente real
de un despacho, en el Drive, sobre documentos de un pleito en curso. Esta es la ronda **sobre el
diseño**; habrá una segunda sobre el diff.

Por tanto, **prioriza por radio de daño**, en este orden:

1. **Pérdida o corrupción de datos del cliente.** Cualquier camino por el que el plan, tal como está
   escrito, borre, pise o deje irrecuperable un fichero del expediente. Incluye los caminos raros:
   dos entradas que colisionan, un `apply` interrumpido, una re-ejecución, un fichero que el letrado
   editó a mano, un enlace simbólico, una carrera entre `plan` y `apply`, un `case_dir` que es a la
   vez origen y destino.
2. **Puertas que no se pueden cumplir, o que se pueden saltar.** El plan bloquea si
   `sin_asignar` no está vacío. ¿Puede el letrado vaciarlo realmente en un expediente de 76
   documentos? ¿Y hay alguna vía por la que una puerta se declare cumplida sin serlo?
3. **Contradicciones con el spec.** El plan declara TRES ajustes deliberados (§«Tres ajustes del spec
   a la realidad del código»). Esos están sobre la mesa. Busca los **no declarados**: donde el plan
   se desvía del spec sin decirlo.
4. **Contradicciones con el código real.** Firmas, semántica de estados, claves de diccionario,
   valores de `metodo`, esquema del `pull_state`. El plan cita mucho código ajeno; comprueba que
   existe y que significa lo que el plan cree.
5. **Tests que no prueban lo que dicen probar.** Esto es lo que más valor tiene y lo que menos se
   pide. Para cada test del plan, pregúntate: **¿pasaría este test si el defecto que pretende cazar
   estuviera presente?** Un test que pasa con y sin el defecto es peor que no tenerlo, porque compra
   confianza falsa. Señala también los asertos tautológicos y los que dependen del orden de un
   `dict`.

## 4. Cinco cosas concretas que quiero que ataques

No te limites a estas, pero no las dejes sin respuesta:

1. **La acción `adoptar`, que el spec NO contiene.** La inventó el autor durante el self-review, al
   ver que un `apply` que copia y muere antes de escribir el ledger dejaría el fichero sin asiento y
   toda pasada posterior lo llamaría «ajeno», bloqueando el caso para siempre. Su criterio es
   «adopto el destino si tiene **exactamente los bytes** que yo iba a escribir». **¿Es seguro?**
   Piensa en: dos documentos distintos con el mismo contenido; un fichero que el letrado puso a mano
   y que casualmente coincide; el hueco entre `plan` y `apply`; qué pasa si el origen cambia entre
   los dos; y si la adopción puede transferir la propiedad de algo que no era nuestro.
2. **La procedencia doble del ledger.** ¿Basta `raw_sha256` + `source_sha256` + `destination_sha256`
   para reconstruir la cadena de custodia de un artefacto derivado (un `.doc` convertido a PDF por
   LibreOffice)? ¿Qué pregunta legítima del letrado no puede responderse con lo que el ledger guarda?
3. **El selector por clase documental** (`core/procedimiento/artefacto.py`). El plan afirma que
   «la fuente de estado es `_cobertura.json`, no la presencia de ficheros». Comprueba esa afirmación
   contra `core/sala_maquina.py`: ¿los valores de `metodo` que el plan enumera son los que el módulo
   produce? ¿Hay algún `metodo` o `estado` real que el selector deje sin cubrir y que caiga en su
   rama de bloqueo por «desconocido»? ¿Y el agrupado de bundles por `parent_sha256` es correcto?
4. **La validación del mapa** (`mapa.py`). Es la superficie de ataque: todo lo que entre por ahí
   acaba siendo una escritura en el expediente real. Busca lo que se cuela: traversal, UNC, nombres
   reservados, unicode que normaliza a otro nombre, `casefold` que colisiona en Windows y no en el
   set del plan, `orden`/`descripcion` con caracteres que Windows no admite, YAML con anclas o tipos
   inesperados, y el truncado por longitud (¿es realmente estable y no colisiona?).
5. **La idempotencia y el «cero escrituras».** El plan promete que una re-ejecución sin cambios no
   escribe nada, «ni el campo `generado` del ledger». ¿Lo cumple el código que el plan propone?
   ¿Hay algún camino en el que `plan` devuelva una operación espuria en una segunda pasada y por
   tanto `apply` reescriba? Mira con lupa el `reemplazar` por comparación de SHA y el
   `preflight_longitud`.

## 5. Qué puedes ejecutar

El Python de **sistema** tiene dependencias que el intérprete que elijas por defecto puede no tener:

    C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe

Trae `pytest`, `yaml`, `typer`, `httpx`, `filelock`, `dotenv`, `mcp`, **`pytest-randomly` y
`pytest-xdist`** (comprobado con `import` el 2026-09-09, justo antes de lanzarte esta ronda). Puedes
por tanto correr con semilla y en paralelo si te sirve para un hallazgo.

Dos avisos medidos:

- Usa `--basetemp` **relativo a tu workdir**. Tu sandbox no puede crear directorios en la raíz de
  `C:`, y MAX_PATH tumba tests que están bien.
- **No mutes la copia del objeto.** Copia a tu workdir lo que necesites ejecutar.

El plan **no tiene código construido todavía** (`core/procedimiento/` no existe: eso es correcto y
esperado). Puedes ejecutar los tests **existentes** del repo para comprobar afirmaciones del plan
sobre el estado actual — en particular `tests/test_skill_helpers_sync.py` y los de
`core/ocurrencias_crm.py` — y puedes extraer los bloques de código del plan a ficheros de tu workdir
y ejecutarlos contra árboles sintéticos si eso te permite confirmar o refutar un hallazgo. **Si haces
esto, dilo**: un hallazgo obtenido ejecutando vale más que uno leído, y el autor necesita saber cuál
es cuál.

## 6. Formato del informe

Escribe **`INFORME.md`** en tu workdir. Estructura:

1. **Primera línea:** declaración de higiene (§0) — qué había en tu workdir.
2. **Digest del objeto al abrir.**
3. **Resumen ejecutivo**, 5-10 líneas. Lo peor primero.
4. **Hallazgos**, uno por bloque, numerados `H-01`, `H-02`… Cada uno con:
   - **Severidad:** `CRÍTICO` (destruye o corrompe datos de cliente, o hace la pieza inservible) ·
     `ALTO` (defecto real con consecuencia práctica) · `MEDIO` · `BAJO` · `NOTA`.
   - **Ancla:** ruta y línea o sección del plan.
   - **Qué está mal**, en una frase.
   - **Por qué importa**: el escenario concreto —entradas y estado— que produce el daño.
   - **Cómo lo verificaste**: leyendo, o ejecutando (y qué ejecutaste).
   - **Remedio propuesto**, si lo tienes.
5. **Lo que NO pudiste verificar**, con el motivo. Sección obligatoria; si está vacía, dilo.
6. **Digest del objeto al cerrar.**
7. **Última línea: el veredicto**, una sola palabra del **set cerrado**, sin nada más:

   `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE` · `SIN-VEREDICTO`

   El veredicto es tuyo y es inmutable. Es obligatorio: sin él, la cadena de custodia del acta se
   rompe y el autor no puede rellenarlo por ti.

No des una segunda pasada de cortesía. Cuando el informe esté terminado, para.
<!-- mandato-literal:fin:v4p1 -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:v4p1 -->
Higiene: al abrir el workdir había MANDATO.md y _stdout.log; no leí _stdout.log ni ningún informe ajeno preexistente.

# Revisión adversarial R1 del plan de vista procesal, pieza 4

## Digest del objeto al abrir

`aaaf72e7ba025e7ec60060d4fdc2f042fd873b9ee1e104fe7711c5e241955050`

Objeto: `C:\t\obj-vistaproc-p4-r1-2026-09-09-1307\docs\superpowers\plans\2026-09-09-vista-procesal-pieza4.md`.
En adelante, **PLAN:L** significa esa ruta y su línea L, numerada desde 1. Las otras rutas se refieren a la misma copia congelada. El commit comunicado es `25c07bc66d319f79d940d7c61c141e7233b9f72b`; su ascendencia queda SIN VERIFICAR porque la copia carece de `.git`.

## Resumen ejecutivo

El plan permite sobrescribir documentos ajenos al mover una entrada y borrar originales del crudo atravesando una junction.
`adoptar` convierte igualdad de contenido en permiso destructivo: puede apropiarse de un fichero manual y también adoptar un destino que otro asiento aún posee.
La combinación `adoptar` + `borrar` deja un ledger que afirma poseer un fichero que la misma corrida acaba de eliminar.
La recuperación prometida tras interrupción falla después de un reemplazo; el ledger antiguo impide reconciliar la escritura ya publicada.
El mutex local no sustituye la autorización del workspace: la fachada escribe sobre el catálogo sin consultar el préstamo ni las capacidades.
La puerta D8 confunde documentos descargados con documentos listados; puede bloquear el régimen acotado y, con `doc_ids` vacío, ocultar documentos pendientes.
Los bundles buscan un PDF de segmento en el directorio del PDF padre; `duplicado` y `error` reales no están cubiertos correctamente.
Los derivados se registran con `raw_path` y `raw_sha256` vacíos, y las supuestas garantías de tres tests sobreviven a contrapruebas que las inutilizan.
Resultado ejecutado: 21 tests existentes pasados; bloques propuestos extraídos, 79 pasados y 5 fallidos. No se acredita la suite completa ni el corpus real.

## Método y evidencia ejecutada

Se leyó el plan y se contrastó con el spec v3.1, las fuentes enumeradas en el mandato y las dependencias concretas necesarias para seguir la resolución de rutas y D8. No se escribió en el objeto ni se ejecutaron operaciones contra CRM, Drive o expedientes reales.

`preparar_sondas.py` copió código Python a `scratch/` y extrajo los bloques propuestos de las tareas 1–8. Conservó la implementación literal; concatenó los bloques adicionales de tests, añadió el `import json` expresamente ordenado por el plan y tomó la última versión de la fachada. `pruebas_plan.py` aplicó únicamente en scratch la ampliación literal del helper y su sincronización. No construí una implementación corregida.

Se utilizó `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, con bytecode desactivado y datos sintéticos. Los basetemp fueron relativos a scratch y quedaron dentro del workdir.

- Tests existentes: `python -m pytest tests/test_skill_helpers_sync.py tests/test_ocurrencias_crm.py -q --tb=short -p no:cacheprovider --basetemp=b3 --randomly-seed=777`: **21 pasados**. Antes hubo un intento con `--basetemp=b1` que produjo **21 errores de setup por PermissionError**, ninguno de test; al lanzar desde el workdir y entrar en scratch se ejecutaron. No atribuyo una causa definitiva al rechazo de aquel lanzamiento.
- Tests propuestos, tareas 1–8: invocación reproducible en `pruebas_plan.py`, semilla 777, `--basetemp=p1`: **79 pasados, 5 fallidos**, salida en `PRUEBAS_PLAN.txt`.
- `sondas.py`: 19 comprobaciones sobre árboles sintéticos, con asertos y resultados en `SONDAS.json`. Diecisiete documentan defectos o límites; las otras dos comprueban positivamente diff vacío y estabilidad de longitud. La etiqueta mecánica CONFIRMADO significa que se cumplió el aserto de la sonda, no que el diseño sea seguro.
- `sondas_extra.py`: junction real de Windows, pérdida de texto manual del índice y selección de método/estado; resultados en `SONDAS_EXTRA.json`.
- `mutantes_tests.py`: tres contrapruebas en memoria, sin alterar los bloques revisados en disco; resultados en `MUTANTES.json`.
- `python -m scripts.procedimiento --help`: exit 0; aparecen `plan` y `apply`.

## Hallazgos

### H-01 — El destino nuevo de un movimiento no tiene puerta de propiedad

**Severidad:** CRÍTICO.

**Ancla:** PLAN:2084–2106, 2134–2137 y 2195–2214, tarea 6; la emisión del movimiento está en PLAN:1630–1633.

**Qué está mal:** `mover` y `reemplazar` verifican el fichero anterior, pero sobrescriben el destino nuevo sin verificar quién lo posee.

**Por qué importa:** existe un asiento para `old.pdf`; el letrado cambia el mapa al nombre `00_f.pdf`, ocupado por un documento manual. El diff emite `mover`; `os.replace` destruye el documento manual y después se elimina `old.pdf`. También afecta al cambio `.doc` → `.pdf` y a destinos pertenecientes a otras entradas. La colisión entre nombres finales del mapa no detecta un fichero ajeno ni una dependencia con un destino anterior.

**Cómo lo verifiqué:** ejecuté `sondas.py`, caso `overwrite`, mediante el diff literal y después apply: cero bloqueos/abortos y bytes manuales sustituidos por `NEW`.

**Remedio propuesto:** validar propiedad de cada ruta que vaya a ser reemplazada, incluida la ruta nueva; reservar globalmente destinos y resolver dependencias entre movimientos antes de publicar.

### H-02 — Adoptar por SHA transfiere propiedad y colisiona con propietarios existentes

**Severidad:** CRÍTICO.

**Ancla:** PLAN:1609–1624, 1647–1656, 2172–2184 y 2224–2227.

**Qué está mal:** igualdad de bytes no acredita autoría y la adopción solo consulta la clave lógica nueva, no la propiedad del destino.

**Por qué importa:** un fichero que puso el letrado con exactamente los bytes del CRM se registra como `origen: crm` y podrá borrarse al salir del mapa. Hay un caso peor sin fichero ajeno: el ledger posee `00_f.pdf` para doc_id 2 y el mapa lo pide para doc_id 1, de idéntico contenido. Se emiten `adoptar(1)` y `borrar(2)`; el borrado final elimina el destino recién adoptado y queda un asiento falso para 1. No requiere colisión criptográfica.

**Cómo lo verifiqué:** sondas `adopt_manual` y `alias_owned`; ambas ejecutadas contra los bloques literales. La primera adopta una copia manual y luego la borra; la segunda termina sin fichero y con el nuevo asiento.

**Remedio propuesto:** exigir evidencia durable de una creación propia pendiente, ligada a operación, destino e identidad; si no existe, tratar el fichero como ajeno. Una adopción expresamente autorizada sería otra política, no recuperación inferida. Impedir dos propietarios simultáneos de una ruta.

### H-03 — La contención acepta una junction que convierte el crudo en destino

**Severidad:** CRÍTICO.

**Ancla:** PLAN:2072–2082, 2098, 2113, 2212–2214; mapa en PLAN:520–631.

**Qué está mal:** resolver también la raíz contra la que se comprueba contención permite legitimar su propia redirección, y no se vetan los reparse points de sus ancestros.

**Por qué importa:** `05_Procedimiento` es una junction hacia `00_Input/05_CRM`. Tanto el destino como la supuesta raíz autorizada resuelven al crudo. Apply acepta la operación, elimina un fichero allí y escribe incluso el ledger dentro del crudo. Un symlink a nivel de fichero no agota el problema: `is_symlink()` sobre el fichero no detecta una junction en un directorio padre.

**Cómo lo verifiqué:** creé una junction real mediante `New-Item -ItemType Junction`, exclusivamente entre dos rutas sintéticas del workdir. `sondas_extra.py` ejecutó `mover`: cero abortos, original crudo eliminado, nuevo fichero y ledger escritos en el crudo.

**Remedio propuesto:** identificar primero la raíz autorizada, vetar redirecciones en la cadena de componentes y contener cada ruta en su carpeta de fase, no solo en una raíz resuelta que puede haberse desplazado. Verificar asimismo que origen y destino no se solapan por alias.

### H-04 — El ledger acepta autoridad destructiva sin SHA y rutas anteriores fuera de la vista

**Severidad:** CRÍTICO.

**Ancla:** PLAN:1203–1217, 1242–1250, 2093–2106 y 2212–2214.

**Qué está mal:** la carga del ledger no valida su esquema de seguridad y el SHA vacío desactiva la comprobación de propiedad.

**Por qué importa:** un asiento válido para el cargador, pero sin `destination_sha256`, permite borrar un fichero editado a mano: el `if asiento.destination_sha256` omite la comparación. Otro asiento con `carpeta: ../00_Input/05_CRM` pasa al movimiento con destino nuevo dentro de la vista; `anterior` no recibe contención y se elimina el crudo. La protección debe resistir corrupción o datos antiguos, no presuponer el ledger perfecto que intenta validar.

**Cómo lo verifiqué:** `missing_hash` guardó/cargó un ledger sin SHA y borró el fichero manual; `outside_old` eliminó un origen sintético de `00_Input/05_CRM` mediante la ruta anterior del asiento. Lectura de la carga confirma que acepta esas cadenas sin validarlas.

**Remedio propuesto:** esquema estricto de origen, claves, carpeta, basename y hashes obligatorios para CRM; comprobar unicidad física de destinos y contención de todas las rutas anteriores. Un SHA ausente debe bloquear, nunca ampliar permisos.

### H-05 — Las comprobaciones de propiedad caducan antes de la escritura

**Severidad:** CRÍTICO.

**Ancla:** PLAN:1641–1644, 2102–2106, 2124–2129, 2145–2149 y 2208–2226.

**Qué está mal:** se reutiliza una comprobación de propiedad anterior a los efectos, y `copiar` con asiento ni siquiera valida un destino reaparecido.

**Por qué importa:** plan ve un asiento cuyo fichero falta y emite `copiar`; antes de apply, el letrado repone otro fichero. Como hay asiento, el preflight permite sobrescribirlo sin SHA. En reemplazos, una edición después del preflight también se pierde. En `adoptar`, la igualdad se verifica en preflight, pero después se vuelve a hashear el destino y ese nuevo SHA se registra como fuente sin repetir la igualdad: una edición en ese hueco se convierte en propiedad destructiva. El mutex entre procesos cooperantes no bloquea al editor del letrado ni a Drive.

**Cómo lo verifiqué:** `copy_race` escribe entre construir y ejecutar; `race` inyecta una edición justo después del preflight. Ambas pierden la edición. La carrera de adopción se sigue por lectura de PLAN:2117–2121 y 2176–2183, no se ejecutó por separado.

**Remedio propuesto:** ligar el plan a las versiones examinadas y proteger o volver a verificar cada publicación/borrado; `copiar` debe exigir ausencia real o cumplir la misma puerta destructiva. Diseñar explícitamente la ventana residual con escritores externos.

### H-06 — El CLI tiene mutex, pero no autorización sobre la copia del expediente

**Severidad:** CRÍTICO.

**Ancla:** PLAN:2631–2660 y 2783–2788; afirma seguir el patrón de sala de máquina en PLAN:24 y 2515–2527.

**Qué está mal:** la fachada elige el catálogo mediante `buscar` y escribe directamente, sin resolver workspace, capacidades ni guard de préstamo.

**Por qué importa:** si el caso del catálogo está prestado a otra máquina, adquirir el mutex local no autoriza a modificar su canon. El motor puede mover, reemplazar y borrar sobre esa copia pese al préstamo. La API pública `proc.apply` tampoco adquiere ni exige el mutex que promete su docstring; cualquier consumidor directo entra sin él.

**Cómo lo verifiqué:** lectura comparada con `core/casos/case_locator.py:121–143`, `core/case_manager.py:1183–1213`, `scripts/_mutex_cli.py` y el patrón real `scripts/sala_maquina.py:468–506,882–887`: este último resuelve el workspace, exige capacidades y usa `ws.working_root`. Las sondas prueban escritura directa sin mutex, pero no ejecuté un préstamo real entre máquinas.

**Remedio propuesto:** reutilizar resolución/autorización del workspace y pasar la raíz autorizada a todas las lecturas y escrituras, incluido RegistroOcurrencias. Exigir el mutex en la frontera del escritor; sostenerlo en el entrypoint.

### H-07 — El ledger como último commit no permite la recuperación prometida

**Severidad:** ALTO.

**Ancla:** PLAN:2027–2033, 2155–2229, 2684–2722 y 3014–3015.

**Qué está mal:** se publican y borran ficheros antes del ledger sin conservar información suficiente para distinguir una publicación propia de una edición ajena.

**Por qué importa:** se reemplaza `OLD` por `NEW` y falla guardar el ledger. La siguiente pasada emite otro reemplazo, pero lo aborta porque el destino NEW no coincide con el SHA OLD del ledger. Tras un movimiento o borrado, el anterior ya no existe y la puerta 10 bloquea. Además, cada fichero se publica dentro del mismo bucle que prepara el siguiente: un error al preparar el segundo ocurre después de publicar el primero. Los retiros de nombres anteriores se hacen inmediatamente, no en la lista de borrados finales. Una excepción I/O se propaga pese al contrato «ejecutar no lanza».

**Cómo lo verifiqué:** sonda `interrupted`, fallo inyectado en `guardar` después del reemplazo, seguida de plan/apply reales: aborto por SHA. Los otros puntos se verificaron leyendo el orden del bucle. El test de interrupción solo elimina el ledger después de una primera copia limpia; no reproduce ninguna operación destructiva interrumpida.

**Remedio propuesto:** preparar/verificar todo antes de publicar y conservar prueba de las transiciones pendientes, o definir recuperación manual concreta con copias previas. El diseño no puede prometer reconciliación automática de esos estados solo con el ledger viejo.

### H-08 — D8 bloquea el intake acotado y permite ocultar las solo listadas

**Severidad:** ALTO.

**Ancla:** PLAN:1522–1540, 1558–1569 y 1658–1666; ajuste declarado en PLAN:54–64.

**Qué está mal:** se compara `pull_state.doc_ids` con todas las listadas, pero las pendientes globales solo se calculan sobre materializadas.

**Por qué importa:** D8 guarda IDs descargados, no el universo enumerado (`core/case_manager.py:1637–1642`; `core/sync_sudespacho.py:1519–1522,1669,1682–1685`). En 76 documentos con descarga acotada de uno, los otros 75 bloquean por «fuera del pull_state», aunque sean ecos propios declarados correctamente. Si `doc_ids` está vacío o falta, se omite por completo el cruce; las 75 solo listadas no están en `sin_asignar` ni bloquean salvo que el mapa ya las nombre. La discrepancia de total solo avisa y `errors` no se consulta.

**Cómo lo verifiqué:** `listed76` construye exactamente esos dos estados: con `['1']` bloquea; con `[]` y error de descarga devuelve cero bloqueos y cero pendientes. Contraste con D8 y el filtro real del pull.

**Remedio propuesto:** separar universo listado, materialización y decisión del letrado. Todas las listadas deben quedar asignadas o justificadas por eco; cruzar el subconjunto descargado con su semántica real y tratar explícitamente estados ausentes, errores y totales discordantes. El ajuste de tres estados no justifica anular el régimen acotado de spec §1.1.

### H-09 — Las puertas de registro ausente e histórico inválido no están implementadas

**Severidad:** ALTO.

**Ancla:** PLAN:1518–1520 y 2644–2651, bajo la promesa de puertas 1–9 de PLAN:1291.

**Qué está mal:** se delegan garantías al registro que su API real no ofrece.

**Por qué importa:** `RegistroOcurrencias.load()` devuelve vacío si falta el fichero (`core/ocurrencias_crm.py:101–104`), comportamiento legítimo para su productor, pero prohibido para esta vista por spec §5.1. El cargador solo exige una lista de revisiones no vacía; no acredita una única vigente ni que las anteriores sean superseded. Las consultas usan la última revisión y pueden colapsar doc_id repetidos en un dict. Un registro vacío/incorrecto puede aparentar que no quedan documentos y permitir retiradas del ledger.

**Cómo lo verifiqué:** sonda `missing_registry`, sin fichero, mapa vacío y sin pull_state: plan sin bloqueos. Leí carga y consultas para el histórico; no ejecuté cada corrupción posible. Los 19 tests existentes de ocurrencias no son una prueba de las puertas adicionales del consumidor.

**Remedio propuesto:** exigir existencia y validar en la vista invariantes semánticas de claves, ámbitos y revisiones antes de producir cualquier operación destructiva.

### H-10 — No se comprueba que el crudo actual sea el de la ocurrencia y la cobertura

**Severidad:** ALTO.

**Ancla:** PLAN:1570–1575, 1635–1640 y 2216–2221.

**Qué está mal:** la existencia del crudo basta para seleccionar una cobertura indexada por un SHA antiguo; el SHA actual no se cruza con ella.

**Por qué importa:** una ocurrencia y su cobertura declaran SHA A, pero la ruta contiene bytes B, por sustitución o contaminación. El selector confía en la clase/calidad de A y apply copia B, guardando ahora su hash. En converted puede copiar el PDF viejo de A mientras el crudo ya es B. Verificar el temporal contra la fuente de copia solo acredita la copia, no la vigencia de la cadena. El spec exige expresamente SHA del crudo igual a cobertura para pypdf y nativo (§2.4).

**Cómo lo verifiqué:** `stale_raw` cambia el crudo y ejecuta diff/apply con registro y cobertura anteriores; no hay bloqueo y el ledger recoge bytes distintos. El caso converted se deriva por lectura.

**Remedio propuesto:** verificar y fijar el SHA del crudo contra la revisión vigente y la cobertura antes de seleccionar; detectar cambios hasta el consumo del artefacto.

### H-11 — El agrupado de bundles conserva el slug equivocado

**Severidad:** ALTO.

**Ancla:** PLAN:947–971 y 1004–1017; test PLAN:1042–1051.

**Qué está mal:** agrupar por `parent_sha256` eligiendo una fila de segmento conserva el slug del segmento para localizar el PDF padre.

**Por qué importa:** sala de máquina escribe el OCR completo en `01_OCR/<parent_slug>.pdf`; la cobertura de split lleva `slug` del segmento, `parent_slug` del bundle y SHA del segmento (`core/sala_maquina.py:958–979,1023`). El selector busca `01_OCR/<segmento>.pdf`, que no es ese artefacto. Bloquea aun teniendo el PDF íntegro disponible; si allí quedara un fichero de segmento, podría copiar una parte como si fuera todo el documento.

**Cómo lo verifiqué:** `bundle` crea el PDF padre y cobertura de dos segmentos: el selector bloquea buscando el segundo segmento. El test propuesto pasa porque solo asierta `estado == low` y nunca llama al selector con el grupo.

**Remedio propuesto:** representar el bundle como tal: identidad/ruta del padre y calidad agregada de segmentos. Probar conjuntamente cobertura real → selección → contenido íntegro copiado.

### H-12 — Hay métodos reales desconocidos y la selección depende del orden de filas

**Severidad:** ALTO.

**Ancla:** PLAN:926–931, 960–970 y 997–1031; afirmación de métodos en PLAN:65–67.

**Qué está mal:** faltan `duplicado` y `error`, y los empates por calidad conservan una fila arbitraria que determina el método.

**Por qué importa:** `core/sala_maquina.py:1067–1112` genera `duplicado` con `alias_de`; `:1408–1409` genera `error/empty`. Si la fila duplicada aparece antes que su titular con el mismo SHA/calidad, ocupa el índice y bloquea como desconocida; al invertirlas, copia correctamente. No se resuelve `alias_de`. Un error de PDF también queda como desconocido incluso con override. Por otra parte, un estado desconocido en una fila `pypdf` se copia sin aviso: `_rango` lo considera peor, pero `elegir` no lo trata como error. `empty` para cualquier extensión no PDF se interpreta como foto, incluido `.doc` fallido.

**Cómo lo verifiqué:** `duplicate_order` invierte las mismas dos filas y cambia bloqueo por selección raw. `sondas_extra.py` ejecuta `error/empty` y `pypdf/NUEVO_ESTADO`. Contraste con productores reales.

**Remedio propuesto:** resolver titulares/alias estructuralmente, separar clase y estado, cubrir los métodos reales y definir tratamiento explícito del error; independencia del orden de serialización.

### H-13 — La procedencia doble desaparece precisamente en converted

**Severidad:** ALTO.

**Ancla:** PLAN:1182–1183, 1454–1462, 2180–2183 y 2218–2221.

**Qué está mal:** las operaciones no transportan el crudo y apply escribe sus campos vacíos cuando copia o adopta un derivado.

**Por qué importa:** para un `.doc` convertido a PDF, el ledger no puede responder «¿qué versión exacta del Word originó este PDF?». Solo conserva ruta/hash del PDF y su copia. Incluso rellenando los tres hashes, estos no demuestran por sí solos la transformación: no permiten responder «¿cuándo, con qué versión/configuración de LibreOffice y por qué operación se convirtió?». El ledger se sobrescribe y no conserva historia propia de conversiones. No se exige aquí certificar fidelidad jurídica; sí cumplir la procedencia doble prometida y no presentar tres huellas como prueba de causalidad.

**Cómo lo verifiqué:** `custody` ejecuta copia converted: `raw_path == raw_sha256 == ''`. Lectura del dataclass y la escritura para la información que no se conserva.

**Remedio propuesto:** transportar identidad, ruta y SHA del crudo vigente; vincular el asiento a evidencia persistida de la transformación, con fecha/motor/configuración cuando se pretenda reconstruirla. Separar integridad de bytes de procedencia de conversión.

### H-14 — eco_crm carece de puerta y de persistencia

**Severidad:** ALTO.

**Ancla:** PLAN:565–569, 1551–1552, 1604–1608, 1659–1662 y 2187–2191.

**Qué está mal:** `eco_crm` se utiliza para excluir IDs, pero no se valida ni se guarda su correspondencia.

**Por qué importa:** un eco apunta a un doc_id inexistente, o al mismo ID que una entrada CRM, y no existe la puerta 7-bis del spec. En el segundo caso se registran las dos vías aunque el spec dice que el eco evita la copia duplicada. El asiento despacho no tiene campo de eco. Si el letrado mueve manualmente su fichero y cambia la carpeta del mapa, la presencia de un asiento para su misma clave hace `continue`: ni actualiza ubicación ni correspondencia, y el fichero nuevo puede aparecer como ajeno.

**Cómo lo verifiqué:** lectura completa del recorrido de `eco_crm`, del esquema de ledger y la rama despacho; contraste con spec §3, líneas 363–365, y §5.7-bis. No se ejecutaron todas estas variantes.

**Remedio propuesto:** validar pertenencia y compatibilidad de ecos; persistir y reconciliar su relación y la ubicación de documentos propios sin mover ni renombrar sus bytes.

### H-15 — Un string false autoriza el override y nunca se registra el actor

**Severidad:** ALTO.

**Ancla:** PLAN:533–542, 586–589, 989–995, 2142 y 2660.

**Qué está mal:** coerciones genéricas sustituyen a validación de tipos y la autorización de cobertura no deja el evento exigido.

**Por qué importa:** `sin_cobertura_ok: 'false'` se convierte en True; `version: true` se acepta como 1. El operador puede creer desactivado el permiso para copiar sin cobertura y ejercerlo. Una vez ejercido, el plan no llama a `_intake_log.jsonl` ni a `get_actor()`: `actor` no se consume en ejecutar. Un texto de aviso no cumple spec §0 y §11.4, que exigen registro del override con actor. No debe confundirse la excepción de log expresamente ordenada con escrituras documentales fuera de fase.

**Cómo lo verifiqué:** `yaml_types` carga ambos valores y verifica True/1. Búsqueda y lectura de los bloques completos: no hay llamada de log; el test «deja constancia» solo busca la palabra override en el aviso.

**Remedio propuesto:** tipos YAML estrictos, booleano real obligatorio y evento append-only al ejercer el permiso, con identidad del documento, hashes y actor canónico.

### H-16 — El mapa no cierra nombres ni traversal en la rama CRM

**Severidad:** ALTO.

**Ancla:** PLAN:478–493, 533–564, 580 y 2076–2081.

**Qué está mal:** se incrusta `orden` sin validar, se normalizan entradas antes de rechazarlas y la comprobación final permite salir de la carpeta de fase.

**Por qué importa:** `orden: ../00` y descripción formada por puntuación producen `../00_.pdf`; mapa y preflight lo aceptan aunque sale de la fase. No afirmo que toda esa ruta llegue a publicarse: el nombre temporal puede fallar antes, lo cual tampoco es validación segura. Se aceptan `NUL.extra.docx`, `COM¹.docx`, dos puntos y `?`; `.stem` no identifica dispositivos con varias extensiones. `fichero` recibe `.strip()` antes del test de espacios, por lo que el nombre con espacio final del propio test es normalizado y aceptado. `safe_load` no evita claves duplicadas ni valida tipos: claves YAML repetidas sustituyen decisiones silenciosamente. Las listas/dicts en campos textuales se convierten a su representación Python.

**Cómo lo verifiqué:** `yaml_types` y `reserved`; también falla el caso literal de espacios finales en pytest. Lectura de `safe_load` y de las coerciones para las demás entradas. Separadores/UNC en `fichero` sí se rechazan; no presento esa defensa existente como ausente.

**Remedio propuesto:** gramática explícita para orden y nombres finales, rechazo antes de normalizar, validación Windows completa, cargador sin claves duplicadas y contención por fase. Validar resultados de normalización y colisiones después de generar el destino efectivo.

### H-17 — El preflight de longitud olvida sus propios temporales

**Severidad:** MEDIO.

**Ancla:** PLAN:496–517, 728–742, 1268 y 2197.

**Qué está mal:** se reserva espacio para el fichero final, pero no para el prefijo y sufijo del temporal que necesita escribirlo.

**Por qué importa:** un nombre truncado al límite produce una ruta final de 259 caracteres y una temporal de 270 en la sonda. La promesa de respetar el límite práctico de la cadena de herramientas queda incumplida; tampoco se preflightean las rutas de controles y no se aplica longitud a despacho. Esto no acredita por sí mismo que Python con rutas largas activadas falle en ese host.

**Cómo lo verifiqué:** sonda `length`: final 259, temporal 270. Dos llamadas con iguales entradas y una llamada sobre el nombre ya truncado produjeron el mismo nombre. No encontré inestabilidad aleatoria del sufijo. El hash de ocho hexadecimales no garantiza unicidad, pero el diff sí comprueba colisiones de nombres finales simultáneos; el riesgo de destinos anteriores corresponde a H-01.

**Remedio propuesto:** presupuestar todas las rutas realmente escritas y temporales con nombre corto independiente; contar límites efectivos de Windows. No usar este hallazgo para afirmar un reemplazo espurio no demostrado.

### H-18 — Se omite el flujo que permite preparar el mapa

**Severidad:** MEDIO.

**Ancla:** PLAN:532–541, 573–578, 2639–2651 y 2768–2775; declaración de propuesta en PLAN:406 y 199–201.

**Qué está mal:** el plan exige un mapa completo para arrancar, pero no implementa la propuesta de orden/descripción ni `--escribir-mapa` del spec.

**Por qué importa:** el letrado de un caso con 76 documentos debe escribir a mano el YAML, los órdenes y las descripciones; si no hay mapa, plan lanza antes de enumerar pendientes. No hay generador de `D 02-A` → `D-02A`, rector o fecha, aunque se anuncia. No hace matemáticamente imposible vaciar `sin_asignar`: con todos los materializados y nombres únicos puede hacerse manualmente. Sí elimina el flujo de trabajo cerrado en spec §2.5 y §3 sin declararlo entre los ajustes.

**Cómo lo verifiqué:** lectura del cargador, fachada, CLI y búsqueda de `escribir-mapa`, ausente del plan. El smoke CLI confirma solo las opciones construidas.

**Remedio propuesto:** añadir propuesta explícita sin asignación de carpeta y un modo de emisión/reconciliación del borrador del mapa que preserve decisiones del letrado.

### H-19 — Un fallo del índice queda consolidado como estado sin cambios

**Severidad:** ALTO.

**Ancla:** PLAN:2229 y 2661–2675.

**Qué está mal:** se confirma el ledger antes del índice y la siguiente pasada solo intenta reparar índices si ha escrito otro ledger.

**Por qué importa:** el PDF y ledger se guardan; el índice falla por I/O. La siguiente ejecución calcula diff vacío y no genera el índice faltante. Igualmente, un cambio de calidad/aviso sin cambio de bytes no desencadena reconciliación: el letrado puede seguir leyendo `copiado` tras degradarse la cobertura. El cero escrituras se obtiene también ante un estado incompleto, no solo ante un estado correcto sin cambios.

**Cómo lo verifiqué:** `index_crash` inyecta el fallo en reconciliar después del ledger y vuelve a llamar apply: no operaciones y ningún índice. La deriva de avisos se verifica leyendo la condición.

**Remedio propuesto:** incluir el estado esperado de índices y avisos en la reconciliación, sin reescribir cuando sus bytes ya son correctos; definir el punto de commit y recuperación del conjunto.

### H-20 — Un marcador incompleto del índice elimina contenido manual

**Severidad:** ALTO.

**Ancla:** PLAN:2423–2427 y 2464–2477; test PLAN:2354–2370.

**Qué está mal:** el parser elimina todo lo que sigue al marcador de inicio si falta el final, sin validar el par ni el contenido.

**Por qué importa:** un `_index.md` truncado o editado conserva el inicio pero pierde el cierre. Las filas de despacho y notas posteriores desaparecen al reconciliar. Incluso con cierre, el bucle elimina cualquier fila manual situada dentro del bloque, aunque el contrato promete gestionar solo filas CRM. El test de preservación solo pone las filas antes del bloque.

**Cómo lo verifiqué:** `sondas_extra.py` creó un inicio sin cierre con fila despacho y nota manual; ambos desaparecieron.

**Remedio propuesto:** validar estructura de marcadores antes de escribir; abortar ante ambigüedad y preservar las filas que no son de su propiedad. Probar marcador ausente, doble, desordenado y contenido manual intercalado.

### H-21 — Los tests compran garantías que no ejercitan y la fachada propuesta ya está roja

**Severidad:** ALTO.

**Ancla:** PLAN:1160–1165, 1958–1971, 2283–2297, 2547–2576 y 2691–2722; regresión en PLAN:2938–2980.

**Qué está mal:** varios nombres/docstrings de tests prometen contratos más fuertes que sus entradas y asertos.

**Por qué importa:** el test de prohibición destructiva de despacho solo ejecuta `desregistrar`; el de atomicidad solo comprueba que no quedan temporales; el de reejecución pasa un plan vacío construido a mano. El test de fallo parcial simula únicamente una copia inicial sin ledger. El de selector del corpus acepta un bloqueo para cada documento y puede pasar con todos los métodos inutilizables. El de asignación del corpus no escribe los crudos ni exige cero bloqueos: puede quedar completamente bloqueado y pasar. Sus órdenes se inventan secuencialmente, de modo que no comprueba el reparto ni la nomenclatura reales.

**Cómo lo verifiqué:** ejecuté las tres primeras contrapruebas en `mutantes_tests.py`: los tests pasan sin puerta destructiva, sin escritura atómica y con `diff.construir` inutilizado. En la suite literal, los cuatro tests de fachada fallan porque el mock de `buscar` no redirige `RegistroOcurrencias → caso_path → path_for`; no llegan a lo que pretenden medir. El quinto fallo es H-16. No ejecuté los tres tests del corpus ausente; se auditan por lectura en la tabla inferior.

**Remedio propuesto:** fixture con única raíz sintética usada por todos los lectores; asertos de efectos, bytecode/mtime o instrumentación de escrituras según contrato; transiciones reales de diff/apply y fallos inyectados en cada frontera destructiva. No debilitar los cinco rojos para obtener verde.

### H-22 — La pieza 1 no proporciona el veto de PDF que este plan le atribuye

**Severidad:** ALTO.

**Ancla:** PLAN:3030–3033, párrafo «Y lo que no falta aunque el spec lo pida».

**Qué está mal:** se declara cubierto un contrato de biblioteca que el código citado excluye deliberadamente.

**Por qué importa:** `core/config.py:432–448` define un grupo de tres ficheros de control y explica expresamente que los PDF quedan fuera. `core/repository_checkout.py:433–449` solo veta rutas miembros. Un conflicto del mapa no impide por esta regla subir el PDF. Spec §8.5 y el propio plan dicen «sin subir ledger ni PDF». Además, la justificación de pieza 1 presupone que el fichero sin asiento será ajeno; la nueva adopción debilita también esa premisa.

**Cómo lo verifiqué:** lectura del grupo completo y de `_vetar_grupos`, coincidencia exacta de rutas. No ejecuté un checkin/rclone real ni atribuyo su comportamiento completo a esta única función.

**Remedio propuesto:** adjudicar explícitamente la diferencia de contrato y añadir la prueba de biblioteca que corresponda. No acreditar un veto de PDF mediante tests de tres controles que no incluyen PDF.

### H-23 — El propio plan incumple su regla de datos personales

**Severidad:** MEDIO.

**Ancla:** PLAN:45–46 frente a 2857–2864 y 2896–2898.

**Qué está mal:** el documento incluye una dirección de tercero y una lista de nombres reales para generar un fixture, pese a ordenar referencias exclusivamente por W-code.

**Por qué importa:** que el script futuro «no se commitee» no retira sus literales del plan que ya se versiona. El control de PII del fixture solo busca seis cadenas de una lista mayor; no acredita ausencia de direcciones, variantes acentuadas o nombres nuevos. La revisión humana de la lista es necesaria, pero no convierte ese grep parcial en prueba de anonimización completa.

**Cómo lo verifiqué:** lectura del objeto y contraste con `CLAUDE.md:143–148`. No reproduzco esos datos personales en este informe y no se consultó el expediente real.

**Remedio propuesto:** parametrizar la ruta por identidad/entorno, sacar el diccionario real del documento versionado y comprobar el fixture contra una política de anonimización revisada, no solo contra seis substrings.

## Respuesta expresa a los cinco ataques del mandato

1. **Adoptar:** no es seguro como prueba de propiedad. H-02 reproduce apropiación de fichero manual y conflicto entre dos doc_id byte-idénticos. La comprobación entre plan y preflight detecta que cambie solo uno de origen/destino; no prueba propiedad si ambos coinciden ni fija los bytes planificados. H-05 identifica el hueco posterior al preflight. El origen modificado sin revisión queda cubierto por H-10.
2. **Procedencia doble:** el diseño ejecutable ni siquiera conserva los dos extremos en converted (H-13). Con tres hashes completos seguiría faltando evidencia del acto de transformación para contestar cuándo/cómo se convirtió una versión. Igualdad de huellas de PDF origen/destino prueba copia, no derivación del Word.
3. **Selector:** acertar las constantes de ruta y `DocCobertura` no basta. `ofimatica` y `vision` existen; también existen `duplicado` y `error`, omitidos. La calidad agrupada usa la clave padre correcta, pero conserva la fila/slug equivocados y depende del orden en empates (H-11/H-12). El estado desconocido no siempre bloquea. No afirmo que `sin_texto` de `TextoPdf` sea un valor de `DocCobertura.metodo`: son interfaces distintas.
4. **Mapa:** hay defensas reales: set cerrado de carpetas, rechazo de separadores y UNC en `fichero`, claves lógicas duplicadas, normalización del slug y comparación casefold de destinos finales. No cubren orden, tipos, reservados completos, rutas anteriores ni reparse points (H-03/H-04/H-15/H-16). No se demostró una colisión adicional del filesystem Windows que eluda casefold; la sonda `i`/`ı` dio ficheros distintos. La normalización del slug sí puede fusionar descripciones, pero la colisión final simultánea se detecta: no es por sí sola un borrado demostrado. Anclas YAML no ejecutan código con safe_load; su presencia tampoco ofrece validación de esquema ni unicidad de claves.
5. **Idempotencia/cero escrituras:** en el camino raw normal ejecutado, el SHA que escribe apply coincide con el que compara diff y la segunda pasada es vacía. El truncado es determinista a igual raíz y nombre. No he confirmado el reemplazo espurio sugerido por el mandato. Sí faltan margen de temporales, recuperación después de destrucción e índices incompletos (H-07/H-17/H-19); el test de reejecución de tarea 6 es insuficiente y el de fachada no llega a correr por su fixture (H-21). `indice.reconciliar` reescribe aun con contenido igual; el flujo normal lo evita solo porque no lo llama ante diff vacío.

La puerta de asignación puede cumplirse manualmente para 76 materializados con nombres distintos; no afirmo que el tamaño del expediente lo haga imposible. Lo que no se cumple es el régimen acotado y la garantía de no ocultar solo listadas. Las exclusiones de skills/sala de lectura y el cambio de piloto están declarados al final del plan, aunque no dentro de «Tres ajustes»; no los califico de desviaciones ocultas. El fixture alternativo no valida el reparto del piloto exigido por spec §11.3. Quedan además prosa obsoleta en `core/config.py:475–477` y la falta de creación de las cinco carpetas vacías: las tareas crean constantes y directorios al operar, no cinco fases en todo caso.

## Auditoría individual de los tests del plan

Cada línea identifica una definición literal; sus parametrizaciones se revisan como parte de ella. «Discrimina» se limita al contrato indicado, no certifica el sistema. Salvo los tres mutantes citados, la evaluación contrafactual siguiente es por lectura; no representa 70 campañas de mutación ejecutadas. Se ejecutaron los 84 casos expandidos de tareas 1–8. Los tres últimos dependen del corpus ausente.

| Línea PLAN | Test / contrato | ¿Pasaría con el defecto que anuncia cazar? |
|---:|---|---|
| 129 | Cinco carpetas en orden | Discrimina cambio de literales u orden; no creación física. |
| 139 | Cajón como quinta | Comprueba literal y pertenencia; con orden alterado pasaría aisladamente, cubierto por 129. |
| 145 | Reconoce las cinco | Discrimina rechazo de estas cinco; una función siempre True también pasa este positivo. |
| 157 | Rechaza otras carpetas | Discrimina aceptación de las seis muestras; no es validación de rutas completa. |
| 249 | Helper sin drift | Detecta ausencias; permite extras inesperados por usar subconjunto. No sustituye al test de las siete copias. |
| 348 | Carga feliz | Discrimina campos/clave de dos entradas; asume orden de lista declarado, no orden accidental de dict. |
| 372 | Acumula problemas | Discrimina perder cualquiera de los tres diagnósticos; falta combinar errores dentro de una misma entrada. |
| 655 | Entradas inválidas | Discrimina muestras salvo espacio final, que falla ya; no cubre rama CRM hostil ni reservados compuestos. |
| 668 | Clave duplicada | Discrimina duplicar ese doc_id entre carpetas; no alias físicos/casefold ni eco. |
| 686 | Versión desconocida | Discrimina 99; no `true`, 1.0 ni tipos coerced. |
| 693 | YAML ilegible | Discrimina error sintáctico tragado; YAML válido con claves duplicadas seguiría pasando. |
| 699 | Mapa ausente | Discrimina devolver mapa vacío; no comprueba registro de ocurrencias ausente. |
| 714 | Nombre CRM/despacho | Discrimina renombrar esa muestra despacho y perder acento normalizado; no caracteres de orden. |
| 723 | Nombre corto | Discrimina truncado innecesario de esa muestra. |
| 728 | Truncado estable | Discrimina variación entre dos llamadas y exceso final; pasaría con temporal demasiado largo o sufijo fijo colisionable. |
| 740 | Extensión al truncar | Discrimina perder `.docx`; no idempotencia aplicada ni margen temporal. |
| 799 | PDF textual raw | Discrimina clase/ruta/extensión; pasa con crudo ausente o SHA incorrecto porque no crea ni verifica archivo. |
| 809 | OCR por slug | Discrimina esa ruta individual; no slug padre de bundle ni trazabilidad. |
| 820 | OCR ausente | Discrimina degradación silenciosa de ese OCR; no reparación/override de errores reales. |
| 831 | Nativo textual | Discrimina clase/extensión; no hash del crudo. |
| 839 | Ofimática PDF | Discrimina kind y extensión; no comprueba source_rel, bytes, ausencia de bloqueo ni los hashes raw. |
| 851 | Sin soporte | Discrimina falta de aviso o bloqueo; cualquier aviso no vacío satisface la prueba. |
| 861 | Visión | Discrimina elegir converted; no prueba existencia del MD ni ausencia física de PDF, que solo simula. |
| 871 | Imagen empty | Discrimina clase/extensión JPG; pasa si se aplica también erróneamente a todos los no-PDF empty. |
| 880 | Sin cobertura | Discrimina aceptar sin permiso; no tipo YAML del permiso. |
| 886 | Override con constancia | Pasaría sin evento/actor: solo pide palabra override en aviso. |
| 1042 | Peor calidad de bundle | Pasaría copiando una parte o bloqueando todo: no resuelve el grupo a artefacto. |
| 1054 | Cobertura ausente/corrupta | Discrimina JSON sintácticamente corrupto convertido a vacío; no esquema inválido. |
| 1062 | Método desconocido | Discrimina aceptar teletransporte; permite rechazar también métodos reales necesarios. |
| 1128 | Ida/vuelta ledger | Solo verifica dos campos; pasaría perdiendo raw/source u origen si conserva esos dos. |
| 1137 | Ledger ausente vacío | Discrimina lanzar por primera construcción; no confundirse con inaccesible/no regular. |
| 1143 | Ledger corrupto | Discrimina JSON ilegible; no ledger válido sin SHA ni rutas inseguras. |
| 1152 | Versión ledger | Discrimina 99; no validación semántica de asientos. |
| 1160 | Ledger atómico | **Mutante ejecutado: pasa con escritura directa no atómica**, sin temporales. |
| 1342 | CRM nuevo copiar | Discrimina operación/ruta/kind; usa SHA_E ficticio y pasaría sin integridad real, como sucede. |
| 1370 | ID de pull sin ocurrencia | Discrimina esa discrepancia no vacía; no D8 acotado ni doc_ids vacío. |
| 1383 | Solo listada | Discrimina el bloqueo si YA se escribió esa entrada en mapa; no solo listadas omitidas. |
| 1404 | Sin asignar bloquea | Discrimina omitir un materializado; no universo listado completo. |
| 1694 | Mismo contenido dos veces | Discrimina dedup de operaciones por SHA; no ejecuta copias ni destino compartido con asiento anterior. |
| 1723 | Eco elimina pendiente | Discrimina exclusión feliz; no eco inválido, repetido, asignado también como CRM ni persistencia. |
| 1743 | Despacho ausente | Discrimina falta de bloqueo por esa ruta; no symlink ni cambio de ubicación con asiento. |
| 1755 | Ajeno no declarado | Discrimina su enumeración y operación espuria en mapa vacío; no destrucción por mover otro documento encima. |
| 1767 | Control no ajeno | Discrimina `_index.md`; no todos los controles ni fichero documental cuyo nombre parezca control. |
| 1778 | Borrar/desregistrar | Discrimina clasificación de acciones; archivos no existen, no ejercita su protección. |
| 1814 | Adoptar bytes iguales | **Fija como correcto el defecto de propiedad**: no aporta evidencia de que la copia fuera propia. |
| 1830 | Otros bytes bloquean | Discrimina ajeno con contenido distinto; nada dice del ajeno idéntico. |
| 1843 | Diff vacío | Solo caso sin registro, mapa ni ledger; pasa con cualquier defecto exclusivo de segunda pasada poblada. |
| 1914 | Cero escrituras vacío | Comprueba resultados y ausencia del ledger; no intercepta toda escritura ni modificación de controles existentes. |
| 1923 | Copia/asiento | Discrimina bytes/hash de copia raw; converted sin raw seguiría pasando. |
| 1941 | SHA manual al borrar | Discrimina ese rechazo; existencia no demuestra conservación de bytes, faltan SHA vacío y carrera. |
| 1958 | Despacho no destructivo | **Mutante ejecutado: pasa con puerta destructiva desactivada**, porque ejecuta desregistrar. |
| 1974 | Destino ajeno | Discrimina copiar sin asiento sobre ajeno; no mover/reemplazar ni copiar con asiento antiguo. |
| 1987 | Plan bloqueado | Discrimina ejecución declarada; no inspecciona árbol completo para cero escrituras. |
| 1997 | Reemplazo cambia extensión | Discrimina retirada/copias felices; inventa la operación en vez de construirla, no revisa procedencia ni destino ocupado. |
| 2241 | Adopción no reescribe | Mtime y SHA discriminan reescritura ordinaria; no legitimidad de propiedad ni carreras después de preflight. |
| 2261 | Adopción cambió bytes | Discrimina desigualdad al entrar a apply; no construye plan ni inyecta cambio después de verificar. |
| 2283 | Reejecución | **Mutante ejecutado: pasa con diff inutilizado**; segundo plan vacío suministrado a mano. |
| 2344 | Índice delimitado | Discrimina ausencia de marcas/fila; no integridad de Markdown, vínculo ni preservación. |
| 2354 | Preserva manual | Discrimina desaparición de dos nombres antes del bloque; no conservación literal ni notas dentro/después de marcador roto. |
| 2374 | Retira CRM | Discrimina fila obsoleta; no movimiento entre dos carpetas por fachada. |
| 2385 | Índice idéntico | Pasaría reescribiendo los mismos bytes cada vez; compara texto, no cero escrituras. |
| 2395 | Aviso a Estado | Solo busca low en todo el texto: pasaría si se pusiera en cabecera o nota, no columna Estado. |
| 2402 | No toca caso.md | Discrimina alteración de contenido; una reescritura idéntica pasa. |
| 2580 | Plan no escribe | **Falla por fixture**. Además solo compara basenames: pasaría cambiando contenido o intercambiando rutas con mismos nombres. |
| 2588 | Fachada escribe | **Falla por fixture**. Tras corregir aislamiento, mera existencia no prueba contenido del ledger/índice. |
| 2597 | Fachada idempotente | **Falla por fixture**. Es la prueba poblada relevante, pero faltan índices, raw→OCR y control de escrituras idénticas. |
| 2691 | Interrupción reconcilia | **Falla por fixture**. Aun arreglada solo prueba creación inicial, no reemplazo/movimiento/borrado interrumpidos. |
| 2928 | Variedad del corpus | SIN VERIFICAR ejecución: no hay fixture. Discrimina falta de pypdf/ocr/tercer método, no exige ofimática ni duplicado. |
| 2938 | Selector corpus | SIN VERIFICAR ejecución. Pasaría bloqueando todos; no hay árbol de artefactos ni expectativa por documento. |
| 2950 | Asignación total corpus | SIN VERIFICAR ejecución. Pasaría con todos los crudos ausentes: no asierta bloqueos, operaciones ni completitud publicada. |

Los tests existentes de sincronización sí separan el check de lectura del ensayo de reparación en copia, y los 21 existentes ejecutados pasaron. El test nuevo de helper no-drift pasó después de aplicar la ampliación y sincronizar exclusivamente scratch. No inferí del orden de dict un fallo no visto: el orden relevante demostrado es el de las filas de cobertura en H-12. El uso de `revisiones[-1]` en el doble del corpus es una presunción de validez del histórico, no una prueba de ella.

## Lo que NO pude verificar

- **SIN VERIFICAR:** ascendencia del commit indicado; no existe `.git`. Solo se acredita identidad del contenido por los dos hashes del plan.
- **SIN VERIFICAR:** corpus real de W-02VEKE y piloto W-02MA0R, sus cantidades, fechas, reparto, calidad y anonimización completa. No se abrieron los expedientes reales ni se generaron los fixtures; los tres tests de regresión no se ejecutaron.
- **SIN VERIFICAR:** suite completa, segunda semilla 31337 y comportamiento en paralelo. No se declara una aceptación global a partir del subconjunto ejecutado. No se ejecutó `session_close`, pues es un flujo de desarrollo con efectos ajenos a esta revisión.
- **SIN VERIFICAR:** OCR/LibreOffice reales y fidelidad del PDF convertido; se contrastaron interfaces y se usaron bytes sintéticos. El fallo de procedencia no requiere ejecutar esos motores.
- **SIN VERIFICAR:** carreras reales con Word, Drive o un segundo proceso y pérdida de lease durante escritura. Se ejecutaron intercalaciones deterministas para las carreras indicadas, no una prueba de estrés distribuida.
- **SIN VERIFICAR:** todos los reparse tags, aliases 8.3, normalizaciones entre Windows y Drive y la matriz Unicode completa. Sí se ejecutó una junction real; el par `i`/`ı` no colisionó y no se usa como hallazgo.
- **SIN VERIFICAR:** fallo efectivo por MAX_PATH en la cadena completa del despacho. Se midió que el temporal excede el límite declarado; no se afirma que el Python de este host lo rechace.
- **SIN VERIFICAR:** checkin remoto y veto del conjunto completo en producción. La afirmación específica sobre pertenencia de PDF al grupo se refuta por la configuración y función reales leídas.
- **SIN VERIFICAR:** implementación futura y remediación de los hallazgos. Lo ejecutado son bloques del plan, extraídos sin corregir su lógica, y no un diff construido por el autor.

## Digest del objeto al cerrar

`aaaf72e7ba025e7ec60060d4fdc2f042fd873b9ee1e104fe7711c5e241955050`

Coincide con el digest inicial. Informe redactado para archivo literal; la adjudicación corresponde al autor contra las fuentes. No se ha realizado una segunda ronda de cortesía.

NO-SHIP
<!-- informe-literal:fin:v4p1 -->

## 2. Evidencia verificada por mí al adjudicar

Lo que sigue lo comprobé **yo**, contra la fuente y no contra el informe, antes de aceptar
ningún hallazgo. Solo consta aquí lo que miré; lo que no miré no aparece.

| Afirmación del revisor | Comprobado en | Resultado |
|---|---|---|
| `pull_state.doc_ids` son los documentos **descargados**, no el universo enumerado (H-08) | `core/case_manager.py:1638` (docstring: «IDs numéricos de los documentos descargados») y `core/sync_sudespacho.py:1519-1522, 1669` (`result.doc_ids.append` va **dentro** del bucle de descarga, después del filtro `only_doc_ids`) | **CONFIRMADO.** Y es peor de lo que el informe dice: en el régimen acotado que usó este mismo caso —2 documentos de 76— mi puerta habría bloqueado los 74 restantes. La pieza habría sido inservible en el expediente para el que la diseñé. |
| El OCR de un bundle se escribe en `01_OCR/<parent_slug>.pdf`, y las filas de segmento llevan el slug del **segmento** (H-11) | `core/sala_maquina.py:1023` (`ocr_out = sm_dir / "01_OCR" / f"{d.slug}.pdf"`, con `d` = el padre) y `:975-979` (`DocCobertura(dl.slug, …, parent_slug=dl.parent_slug, parent_sha256=d.sha256)`) | **CONFIRMADO.** Mi agrupado conservaba la fila de peor calidad —una de segmento— y derivaba la ruta de **su** slug: apuntaba a un fichero que no existe. |
| `duplicado` y `error` son métodos reales de `DocCobertura` (H-12) | `core/sala_maquina.py:1069` (`METODO_DUPLICADO = "duplicado"`, `MEJORAS #147`) y `:1409` (`DocCobertura(d.slug, d.rel_path, "error", "empty", …)`) | **CONFIRMADO.** Mi selector no cubría ninguno de los dos, así que los mandaba a su rama de «método desconocido → bloqueo». Y `alias_de` —el campo que apunta la copia al espejo de su titular— no se resolvía en absoluto. Tengo nota propia sobre esa dedup y aun así enumeré seis métodos. |
| El grupo de `GRUPOS_MERGE` **excluye** los PDF a propósito (H-22) | `core/config.py:432-449`, comentario literal: «Los PDF de la vista **se desacoplan sin peligro** — un fichero sin línea en el ledger se reporta como ajeno (visible y recuperable)» | **CONFIRMADO, y es el hallazgo más grave del informe.** No solo atribuí a la pieza 1 un veto que no da: la seguridad que la pieza 1 declara **se apoya** en que un fichero sin asiento sea ajeno, y mi `adoptar` convertía justo eso en propiedad. Debilité en silencio la justificación de una pieza ya mergeada. |
| El patrón real de `sala_maquina` resuelve **workspace y autorización**, no una ruta (H-06) | `scripts/sala_maquina.py:468-476` (`_resolver_workspace`, cuyo docstring dice: «Antes esto resolvía una ruta y escribía sin preguntar a nadie: si el caso estaba prestado a otra máquina, el motor arrancaba igual») y `:882-886` (`_exigir(ws, Capability.WRITE_CASE, …)`, `case_dir = ws.working_root`) | **CONFIRMADO.** Mi fachada usaba `case_locator.buscar` más el mutex local: exactamente el patrón que este repo ya retiró de `sala_maquina` por este motivo. El plan citaba ese patrón como el que seguía. |
| El plan incumple la regla de PII del proyecto (H-23) | Mi propio plan, sección de la Tarea 9, contra `CLAUDE.md` §«Higiene de datos y secretos» | **CONFIRMADO.** Había metido la dirección del inmueble y 18 nombres de las partes dentro de un script de generación de fixtures. Que el script «no se commitee» es irrelevante: vive en el plan y el plan se versiona. |
| El verde del `leak-guard` no desmiente lo anterior | `scripts/precommit_leak_guard.py::resolver_blocklist` sobre este árbol, el 2026-09-09 | **CONFIRMADO, medido:** 70 términos en la blocklist y **0 coincidencias** con ninguno de los nombres ni con la dirección. El guard es una denylist: pasó porque era **ciego por construcción** a este caso, no porque el fichero estuviera limpio. |

**Remediado ya, fuera del ciclo de la pieza** (H-23, por tener consecuencia viva):

1. El plan resuelve ahora la ruta del caso con el localizador y los términos a redactar con
   `cargar_blocklist()` — cero literales de datos personales en el documento versionado.
2. La comprobación del fixture corre contra la **blocklist entera** y **falla si está vacía**;
   antes era un grep de seis substrings elegidas a mano, que es el verde de un guard sin su
   blocklist.
3. El commit se **enmendó** antes de pushear, así que la PII no entra en el historial
   compartido; un `git grep` sobre todas las revisiones de la rama no la encuentra. El commit
   original queda inalcanzable y nunca salió de esta máquina.
4. Se añadieron a `data/_config/pii_blocklist.txt` —**gitignored**, que es su hogar sancionado—
   los 13 términos de este caso que faltaban: de 70 a 83. Y se comprobó con un **control
   positivo** que el instrumento da los dos valores: señala un fichero con uno de esos términos
   y deja pasar uno inocuo. Añadir términos no prueba que los cace.

**Lo que NO verifiqué yo, y por tanto no acredito:** los caminos de destrucción de H-01, H-03,
H-04, H-05 y H-07 los reprodujo el revisor con sus sondas y yo los acepté **leyendo mi propio
plan** y siguiendo su escenario, sin volver a ejecutarlos. Son afirmaciones sobre código que
todavía no existe —los bloques del plan—, así que la verificación posible es la que él hizo:
extraerlos y correrlos. Lo digo porque la diferencia importa: en esos cinco el verificador fue
él, no yo.
