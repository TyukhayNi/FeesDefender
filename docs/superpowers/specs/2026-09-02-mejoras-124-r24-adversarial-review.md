---
tipo: revision-adversarial
objeto: "rev. 2 del diseno de MEJORAS #124 — quien contesta cual es la copia de trabajo"
objeto_rev: "rama claude/mejoras-124-rev2, commit b01dabe"
commit: b01dabe
ronda: "24"
revisor: Codex
veredicto: NO-EJECUTABLE
marcador_nonce: t8rv
sha256_informe: c629fa63f1defb854998913ebc13faaa6e37726e0a29c992955b64c589e4c886
adjudicado_en: docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md §9
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R24.** El §1 conserva la voz del revisor sin una coma cambiada; la
> **adjudicación** vive en el **§9 del plan**. Es la ronda de **DISEÑO** de la rev. 2, corrida antes
> de escribir una línea de código.
>
> Veredicto `NO-EJECUTABLE`: **12 hallazgos** — 3 CRÍTICOS, 8 ALTOS, 1 BAJO. Adjudicados: **12
> confirmados, 0 refutados**.
>
> **Es la SEGUNDA ronda de diseño sobre `MEJORAS #124` y el segundo `NO-EJECUTABLE`.** Con esto la
> pieza ha consumido su presupuesto entero —dos rondas— **sin una línea de código**. El §13 de
> `PLAN.md` previó exactamente este punto: *«cuántas rondas come un documento antes de que la
> conclusión razonable sea recortar alcance en vez de revisar otra vez»*. La decisión de recortar o
> seguir es de Nikolai, y está planteada en el §9.4.
>
> **El bloque literal archiva DOS textos**, por lo mismo que en R21-R23: el guard G9 exige la
> palabra del veredicto dentro del bloque y el informe no la contiene.
>
> **No-mutación acreditada por partida doble.** Hash agregado idéntico al abrir y al cerrar en la
> medición del revisor; y yo recomputé el mío antes y después (`76e73013…`, 1.358 ficheros). Los
> valores absolutos difieren porque las recetas de agregación difieren; lo que acredita la
> no-mutación es que **cada uno** obtuvo el mismo valor en sus dos tomas.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:t8rv -->
# Revisión adversarial R24 — `MEJORAS #124`, rev. 2

Objeto: `C:/tmp/r24/objeto`, copia sin `.git` atribuida por el encargo al commit `b01dabe`.

`sha256` agregado al abrir: `4deeb626f02df19e3da66ac6d91d3880a2b33f90521307f9b0bebecafb23164e` (1.358 ficheros).

Método del agregado: SHA-256 del UTF-8 de la lista ordenada por ruta POSIX relativa
`<sha256-del-fichero>  <ruta>`, un registro por fichero, `\n` entre registros y sin salto final.

## H24-01 — El «siempre `False`» del §1 es falso y el valor contrario evita el guard

**Severidad: CRÍTICO.**

**Evidencia.** La premisa «`case_locator.buscar()` devuelve solo rutas bajo `CASOS_ROOT`»
(`docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md:29-39`) no la sostiene
la implementación. `buscar()` concatena `case_id` sin exigir un nombre simple ni comprobar la
contención (`core/casos/case_locator.py:121-143`). Un absoluto descarta la raíz al componer el
`Path`; `..\workspace` sale por el padre. `resolve_ref()` devuelve sin modificar una referencia
desconocida (`case_locator.py:226-258`), y existe al menos un entrypoint productivo con `--ref`
libre (`scripts/export_label_emails.py:41-64`).

Sonda ejecutada sobre la copia (`python C:/tmp/r24/informe/SONDAS_R24.py`), con un workspace externo
legítimamente registrado:

```text
buscar('..\\workspace') = ...\canon\..\workspace
buscar escapa de CASOS_ROOT: True
es_copia_prestada('..\\workspace') = True
guard sobre case_id escapado: permitido=True desviar=False
```

La condición cuya imposibilidad afirma el documento puede ser falsa para un identificador canónico
normal y verdadera para un `case_id` con traversal/absoluto. No es un teorema. Además, el valor
verdadero no es inocuo: `guard_escritura()` devuelve permiso sin desviar antes de leer el estado
(`core/case_manager.py:882-889`).

**Qué habría que hacer.** Validar en la frontera que `case_id` es un único nombre de carpeta, no
absoluto, sin separadores ni `..`, y comprobar la contención del resultado bajo `CASOS_ROOT`.
Añadir controles mutantes para absoluto y traversal. Hasta entonces, sustituir «siempre» por la
afirmación estrecha realmente demostrada para identificadores canónicos normales.

## H24-02 — D124 no puede representar el fallback de los `BLOCKED_*`

**Severidad: CRÍTICO.**

**Evidencia.** El plan exige que la raíz salga de una sola resolución, que viaje privadamente en la
capacidad y que no se vuelva a `CaseCatalog.localizar` (`plan:109-121,173`). A la vez, la tabla exige
para `BLOCKED_CONFLICT` y `BLOCKED_FOREIGN_CHECKOUT` en `libre` «raíz = canon + desvío»
(`plan:135`). Sin embargo:

- `diagnostico=True` solo transforma esos dos bloqueos en un `CaseWorkspace` con
  `working_root=None` (`core/casos/workspace_resolver.py:279-288`);
- los modos bloqueados no conceden ninguna capacidad (`workspace_model.py:72-103`);
- `CaseWorkspace` rechaza por invariante un bloqueado con raíz (`workspace_model.py:505-514`);
- `canonical_ref` se rellena siempre con `None` (`workspace_resolver.py:290-303`).

La sonda produjo:

```text
conflicto diagnostico=True: mode=blocked_conflict working_root=None canonical_ref=None caps=[]
prestado ajeno diagnostico=True: mode=blocked_foreign_checkout working_root=None canonical_ref=None caps=[]
```

Para construir el fallback canónico, la implementación tendría que volver a localizar el canon
(segunda resolución y carrera), violar la invariante de `CaseWorkspace` o inventar un resultado que
el plan no diseña.

**Qué habría que hacer.** Diseñar un resultado interno cerrado de enrutamiento de escritura que
represente, en una sola pasada, `DENY`, `WRITE_WORKING` y `DIVERT_CANONICAL`, con la raíz de este
último ligada privadamente. No convertir un `CaseWorkspace` de diagnóstico en autorización.

## H24-03 — El único E2E no puede dejar el canon intacto si se excluyen las transitivas

**Severidad: CRÍTICO.**

**Evidencia.** T3 solo cablea `abrir_caso --modo v1` (`plan:195-196`) y V1 solo admite
`drive_ev` (`scripts/abrir_caso.py:454-460`). Ese camino llama `pull_drive_ev`
(`scripts/abrir_caso.py:136-175`). Aunque los bytes se redirijan mediante `Deposito`, el pull
exitoso sigue escribiendo `_caso.md` por `register_drive_ev(case_id, ...)`
(`core/intake_drive.py:320-323`), y el orquestador emite eventos usando el `case_dir` canónico
(`scripts/abrir_caso.py:107-115,130-133,159-175`). Esos efectos figuran entre las transitivas que
T7 y §8 excluyen (`plan:65-70,206-207,229`).

El criterio 1 exige, por hash de los dos árboles, bytes en la copia, bandeja vacía y **canon
intacto** (`plan:213-214`). Contra el entrypoint real cambia el hash canónico; contra un test
unitario de `deposito` no se verifica T3 ni que el caso reciba el intake.

**Qué habría que hacer.** Incluir en esta pieza los efectos del camino `drive_ev` necesarios para
mantener intacto el canon (sello, log y cualquier marcador), o estrechar honestamente el criterio a
un observable unitario y reconocer que el E2E queda para 3B/3C. No excluir ficheros del hash para
fabricar «intacto».

## H24-04 — La capacidad actual sí expone la raíz y F2 no observa esa fuga

**Severidad: ALTO.**

**Evidencia.** El plan afirma que el tipo ya existente no expone la raíz y que «no hay API que la
entregue» (`plan:102-121`). La API real permite obtenerla por tres vías:

- `_base` es un atributo Python accesible (`core/casos/escritura.py:52-68`);
- `dir_para(".")` devuelve exactamente `_base` (`escritura.py:92-100`);
- `escribir_texto` y `escribir_bytes` devuelven el `Path` escrito (`escritura.py:102-116`).

De cualquiera de los dos retornos se deriva la raíz del caso recorriendo `.parents`. La sonda
confirmó `Deposito.dir_para() devuelve base: True` y recuperó la raíz del caso. El guard C8 actual
solo busca atributos públicos cuyo **valor inmediato** sea `Path`; no invoca métodos ni inspecciona
retornos (`tests/test_escritura_costura.py:327-347`). F2 propone añadir una propiedad pública como
mutante (`plan:174`), pero esa mutación no cambia la propiedad semántica: la raíz ya era recuperable.

**Qué habría que hacer.** O estrechar la garantía a «no almacena una raíz en un atributo público»
y dejar de presentarla como frontera de capacidad, o encapsular también la ejecución de motores sin
devolver `Path`. F2 debe observar retornos y recuperación por ancestros, no solo propiedades.

## H24-05 — La fila `LocalWorkspaceMissing` contradice la adopción y hay más cambios no declarados

**Severidad: ALTO.**

**Evidencia.** Cuando el canon está prestado por esta máquina pero no existe entrada local, el
resolver lanza `LocalWorkspaceMissing` incondicionalmente, también con `diagnostico=True`, y exige
adopción explícita (`workspace_resolver.py:130-140`; `tests/test_workspace_resolver.py:146-162`).
La tabla promete en ambos modos «raíz = canon» si el canon es conocido (`plan:139`). La excepción
no transporta esa raíz y no se distingue desde el llamador del `LocalWorkspaceMissing` sin canon.

Sonda con `diagnostico=True`:

```text
prestado propio sin entrada: EXC LocalWorkspaceMissing
nonce discordante: EXC LockMismatch
canon + scratch: EXC AmbiguousCase
offline canon sin local: EXC RuntimeCannotAccessWorkspace
registro ilegible: EXC RegistryUnreadable
schema no soportado: EXC SchemaNoSoportado
offline scratch sin canon: OK mode=local_scratch
```

Esto también hace que «offline sin checkout verificado» se solape con la fila `LOCAL_SCRATCH`: un
scratch sin canon funciona offline. Además, el plan declara solo ambigüedad y `LockMismatch` como
cambios respecto de `libre` (`plan:149-150`). Hoy los fallos de registro se capturan en
`es_copia_prestada` y se continúa contra el canon (`case_manager.py:835-849`), y el guard no tiene
concepto de offline. Hacer abortar `RegistryUnreadable`, `SchemaNoSoportado` y offline son cambios
adicionales.

**Qué habría que hacer.** Adjudicar expresamente si se conserva la adopción obligatoria; separar
los dos `LocalWorkspaceMissing` en el resultado de enrutamiento; aclarar el solapamiento offline /
scratch; y añadir una matriz completa «hoy → rev. 2» para cada excepción y modo.

## H24-06 — T1/T3 no transportan resolver, contexto ni `modo`; V1 puede caer al default `libre`

**Severidad: ALTO.**

**Evidencia.** La firma real de `deposito` recibe `ref`, `rel_base`, `origen`, `clase`, `modo` y una
raíz de lockfiles; no recibe resolver, workspace, disponibilidad de Drive, usuario, máquina ni reloj
(`core/casos/escritura.py:161-172`). El snippet del plan usa un `resolver` y un
`drive_accesible=...` sin fijar quién los construye (`plan:109-118`).

En `abrir_caso`, `modo` llega a `ensure_case`, pero no se pasa a `_despachar_intake`,
`_intake_drive_ev` ni `pull_drive_ev` (`scripts/abrir_caso.py:316-329,636-671`;
`core/intake_drive.py:163-196`). Este último solo entra por `dir_intake`. Una migración natural que
llame al nuevo `deposito` sin ensanchar toda la cadena usará su default `modo="libre"`; un V1
bloqueado desviará cuando el criterio 3 exige abortar sin bytes.

Además, `_identidad()` preserva hoy C0 comparando metadato, nombre y referencia y alimenta el
mutex (`escritura.py:119-158`). Sustituir su `case_dir` canónico por `working_root` requiere decidir
qué identidad manda en checkout y scratch. El resolver devuelve el `CaseRef` recibido sin
enriquecer `case_id`, y un bloqueado no tiene raíz con la que derivarlo
(`workspace_resolver.py:142-144,290-303`), aunque `guard_escritura` exige `case_id`.

**Qué habría que hacer.** Fijar la firma y el dueño de la resolución. El entrypoint debe construir
un contexto inyectable y pasar una capacidad ya ligada a `modo`, o transportar explícitamente todo
el contexto hasta el consumidor. Contratar la conservación de C0-C8 y un mutante que elimine el
transporte de `modo`.

## H24-07 — El censo de 28 no es completo y el reparto 2/5 no reproduce el AST

**Severidad: ALTO.**

**Evidencia.** El barrido AST propio confirmó cero llamadores productivos de `deposito()`. También
encontró estas llamadas activas:

```text
guard_escritura: case_manager.py:913, casos/escritura.py:210,
                  intake_manual.py:262, sync_sudespacho.py:1494        => 4
dir_intake:       intake_drive.py:196, intake_lotes.py:96,
                  whatsapp_intake.py:92                                => 3
```

No se reproduce «dos directos, cinco vía `dir_intake`» (`plan:60`). `email_export` añade una
vía indirecta `reservar_lote → dir_intake` (`email_export.py:1421-1431`).

El 28 sí cuadra aritméticamente con las celdas 8+3+1+5+7+3+1, pero omite efectos de la misma
operación. En `pull_expediente_v2`, la fila de `sync_sudespacho.py` no cuenta cuatro `_log_event`
(`:1522,1587,1604,1653`), alias de `append_event` importado en `:72`; este localiza el canon y
escribe su log (`core/intake_log.py:172-196,239-266`). Tampoco cuenta
`is_legacy_intake_v1(case_id)` (`sync_sudespacho.py:1424`), que resuelve mediante `buscar`
(`case_manager.py:1174-1192`), aunque sí cuenta otro lector, `read_bucket_overrides`. Con la misma
unidad declarada, son como mínimo 33 y la fila sync como mínimo 12.

El documento también dice que el reparto está en §5/§7 (`plan:95,206-207`), pero no asigna cada
efecto a 3B o 3C.

**Qué habría que hacer.** Versionar el comando de censo, resolver aliases/imports y seguir cada
operación hasta sus efectos finales. Publicar una allowlist efecto por efecto con propietario 3B/3C
y fijar el tope solo después de recomputar.

## H24-08 — `email_export` parte cinco planos y `#126` no es el arreglo de destino

**Severidad: ALTO.**

**Evidencia.** Es cierta la afirmación estrecha: `email_export.py` no llama directamente al guard y
sus bytes pasan por `reservar_lote`. Pero §2.3 solo nombra bytes y `IntakeManifest`. El mismo flujo
ancla al canon, por `case_id`:

- dos usos de `IntakeManifest` (`email_export.py:994,1250`);
- el estado de canal `_exported_ids.json`/`_resolved_links.json`
  (`email_export.py:1146-1174,495-513`);
- dos eventos en el log (`email_export.py:760,1311`);
- los índices cross-lote de `01_Procesado/Emails` (`email_export.py:1390-1418`).

Por tanto la partición afecta bytes, manifiesto, estado de canal, log e índices. No es exclusiva de
email: los otros consumidores que desvían bytes y conservan metadata por `case_id` ya presentan la
misma clase, como muestran las transitivas del propio §2.2.

El plan envía el defecto a «fila #17 / `MEJORAS #126`» (`plan:83-84,230`), pero #126 solo añade
`mutex_sesion.sostenido` a cuatro entrypoints (`docs/MEJORAS_FUTURAS.md:5683-5719`); no cambia
resolución ni propaga capacidad. Y el criterio 1 dice genéricamente «un caso prestado recibe el
intake en su copia», no «solo `abrir_caso/v1/drive_ev`».

**Qué habría que hacer.** Mantener #126 como dueño del mutex y asignar el destino/capacidad de
email a 3B/3C o a una fila propia, con criterios sobre los cinco planos. Si queda fuera, estrechar el
criterio 1 al único consumidor migrado.

## H24-09 — Las fronteras no son independientes y varios mutantes no gobiernan la propiedad

**Severidad: ALTO.**

**Evidencia.** La matriz propuesta (`plan:171-180`) no satisface «cada uno por su frontera»:

| Mutante | Puede tomar ambos valores | Problema |
|---|---|---|
| F1: volver a `localizar` | Sí | Hace fallar también F4: los bytes dejan de caer en `working_root`. |
| F2: añadir propiedad `Path` | Sintácticamente sí | Semánticamente inerte: la raíz ya sale por métodos/retornos. |
| F3: «invertir la condición» | **SIN VERIFICAR** | No hay ancla ni condición futura especificada. |
| F3-bis: quitar `es_protocolo` | Los escenarios true/false existen | No se fija ancla ni conjunto exclusivo de fallos. |
| F4: forzar `desviar=True` | **SIN VERIFICAR** | Un local no tiene diseñada `ruta_bandeja`; falta el resultado que se muta. |
| F5: degradar error a desvío | No como un solo mutante | Agrupa ambigüedad, nonce, registro, schema, missing y offline. |
| F6: dejar escapar `CaseLocked` | Las dos ramas existen por `diagnostico` | No hay llamador productivo `libre` de `deposito`; T3 solo añade V1. |
| F7: censo AST con tope | 0 y 1 son fabricables | Un `if False: deposito(...)` satisface el suelo sin ejecutar producción. |

F7 mezcla dos métricas opuestas. Un techo que solo baja sirve para bypasses residuales; para
clientes deseables, eliminar el único llamador baja el censo y pasa el techo. El criterio `>=1`
evita solo el cero sintáctico, no el código muerto.

Tampoco hay mutantes para llamar dos veces al resolver, recomputar el veredicto con el guard viejo,
perder `modo`, colapsar los dos `LocalWorkspaceMissing` o perder C0-C8. F5 no puede cubrir todas las
transiciones con un parche único.

**Qué habría que hacer.** Publicar desde el plan la matriz
`mutante → ancla/parche → escenario productivo → tests propios que fallan → tests ajenos que no
fallan`. Separar suelo E2E/allowlist de llamadores y techo de bypasses. Añadir fronteras para la
resolución única, el transporte de contexto, la distinción de errores y C0-C8.

## H24-10 — Los criterios de `xfail`, llamadores y semillas son vacuos o inverificables

**Severidad: ALTO.**

**Evidencia.** T5 permite que los cuatro `xfail` pasen o que «la promesa se reescriba», y el
criterio 7 solo pide resolverlos «en una dirección u otra» (`plan:200-204,223`). Eso admite borrar o
debilitar el test. Los cuatro tests llaman a las APIs viejas `guard_escritura`/`dir_intake`
(`tests/test_guard_copia_prestada.py:168-209`), que T7 no migra. El de scratch monta scratch junto
con canon, estado que el resolver convierte en `AmbiguousCase` (`workspace_resolver.py:87-94`), no
en una copia local utilizable.

El criterio 4 `>=1 llamador` pasa con código muerto, como se explica en H24-09. El criterio 6 exige
dos semillas sin dar comando y el intérprete autorizado no tiene `pytest-randomly`:

```text
python -c "import importlib.util; print(importlib.util.find_spec('pytest_randomly'))"
pytest_randomly= None
```

Por instrucción del encargo, todo lo dependiente de semillas queda **SIN VERIFICAR**.

**Qué habría que hacer.** Exigir para cada `xfail` un test sustituto enumerado y prohibir
eliminación/debilitamiento sin ese reemplazo. F7 debe incluir un E2E con spy/contador en la rama V1
real. Sustituir «dos semillas» por un mecanismo disponible y su comando exacto, o declarar e
instalar la dependencia.

## H24-11 — La capacidad no contiene la respuesta que la fila #5 necesita

**Severidad: ALTO.**

**Evidencia.** §8 dice que la fila #5 queda fuera pero «ahora tiene la respuesta que le faltaba»
(`plan:232-233`). La regla pendiente de esa fila necesita distinguir canon disponible de checkout
local (`docs/superpowers/plans/2026-08-26-apertura-v1-plan3a-bis-fila5.md:228-249,466-480`).
`Deposito` solo expone `clase`, `origen`, `desviada` y estado del mutex; no lleva `workspace_mode`,
`es_canon` ni `MUTATE_CANONICAL` (`core/casos/escritura.py:52-68`). En canon disponible y copia
local, `desviada=False` en ambos. F2 impide deducirlo inspeccionando la raíz.

**Qué habría que hacer.** Transportar en la capacidad un discriminante opaco y seguro, idealmente
`puede_mutar_canon`, derivado por la misma resolución, y contratarlo con mutante propio. Si ese dato
queda diferido, retirar la afirmación de que #124 ya desbloquea la fila #5.

## H24-12 — Varias cifras son correctas, pero la base no quedó verde y dos referencias no se prueban

**Severidad: BAJO.**

**Evidencia.** Se confirmaron por ejecución/AST:

- `deposito()` tiene 0 llamadores de producción;
- existen cuatro `xfail(strict=True)` de #124 y diez `xfail` totales;
- se recogen 3.735 tests;
- el manifiesto de #136 contiene 14 mutantes y, ejecutado en una copia desechable con un índice Git
  local y `--basetemp` dentro de este workdir, dio base verde y 14/14 muertos, 0 supervivientes o
  mal apuntados.

La suite completa, sin plugin de semillas, no reprodujo verde:

```text
1 failed, 3647 passed, 77 skipped, 10 xfailed in 312.25s
```

El fallo fue ambiental y ajeno a #124: `test_mcp_wrappers[expedientes_xl]` vacía `PATH`, pierde
`ping` y no alcanza el diagnóstico esperado. El total 3.735 y los 87 omitidos (`77 skipped + 10
xfailed`) sí cuadran, pero `3.735 / 0 / 0 / 87` no identifica con claridad las categorías.

Las cifras históricas «18 tests y 12 mutantes» de 3A (`plan:51`) no se reconstruyen del objeto:
`test_escritura_costura.py` tiene hoy 16 funciones de test y no existe manifiesto ejecutable de esos
12. Las referencias a commit `9c947ba` y PR #255 son autocitas sin historia local.

**Qué habría que hacer.** Expresar la base como
`collected/passed/failed/errors/skipped/xfailed/xpassed`, dar el comando, y distinguir cifras
históricas de las reproducibles en el objeto. Enlazar o versionar el manifiesto de los 12 mutantes.

## Lo que NO pude verificar

- Las dos semillas del criterio 6: `pytest-randomly` no está instalado. No se infiere estabilidad
  de orden a partir de la corrida sin semillas.
- La equivalencia física UNC ↔ letra de unidad. El propio plan la deja fuera y no hay en este host
  un mapeo equivalente controlado. En consecuencia, el «siempre» del §1 tampoco está demostrado
  para ese alias, aunque ya quedó refutado por traversal sin depender de UNC.
- La genealogía `b01dabe`/`9c947ba`, PR #255 y que el objeto corresponda históricamente a esos
  identificadores: el objeto fue entregado sin `.git`. Se verificó contenido, no historia.
- Los 12 mutantes históricos de 3A: no hay manifiesto ejecutable en el objeto.
- Tests lentos, fixture SaRS1 con PII real, Ollama y el guard que depende de la blocklist ausente:
  la suite los omitió expresamente.

`sha256` agregado al cerrar: `PENDIENTE_DE_RECOMPUTAR`.

----- VEREDICTO.md (fichero aparte, pedido asi en el mandato) -----

NO-EJECUTABLE
La rev. 2 contiene críticos de representación y alcance: su D124 no puede producir el fallback bloqueado y su E2E contradice las exclusiones.
<!-- informe-literal:fin:t8rv -->

## 2. Evidencia verificada por el adjudicador

**H24-01, reproducido con sonda propia.** Es el hallazgo que tumba la afirmación de cabecera de la
rev. 2:

```
=== el caso NORMAL: el teorema aguanta ===
  buscar('Caso')            : <CASOS>\Caso
  es_copia_prestada('Caso') : False
=== un case_id con traversal ===
  buscar('..\workspace')    : <CASOS>\..\workspace
  escapa de CASOS_ROOT      : True
  es_copia_prestada         : True
  guard: permitido/desviar  : True / False
```

`buscar()` compone `root / case_id` **sin validar** que `case_id` sea un nombre simple
(`core/casos/case_locator.py:132-143`), y `resolve_ref` devuelve sin tocar la referencia que no
reconoce. Verifiqué además la alcanzabilidad: `scripts/export_label_emails.py` toma `--ref` como
texto libre y lo pasa a `email_dest_dir(case_id)`.

**Calibración honesta de la severidad, que el informe no hace y conviene fijar:** son CLI locales
que corre Nikolai en su portátil, no un servicio expuesto. El riesgo real es el **error de
operador** —una ruta pegada, una referencia con un separador de más— escribiendo fuera del
catálogo; no un atacante. Sigue siendo un defecto vivo y va a `MEJORAS` con su medición, pero no se
rotula como agujero de seguridad.

**H24-02, verificado por lectura.** `CaseWorkspace` prohíbe por invariante que un modo bloqueado
lleve raíz (`core/casos/workspace_model.py:509-513`) y `diagnostico=True` devuelve
`working_root=None`. Mi fila «`BLOCKED_*` en `libre` ⇒ raíz = canon + desvío» **no se puede
construir** desde la salida del resolver sin una segunda resolución, que es justo lo que D124
prohíbe. Es la misma clase que R21/H21-03, que yo creía haber cerrado en esta rev. 2: la cerré
para los errores y no para los bloqueos.

**H24-03, verificado por lectura.** `abrir_caso --modo v1` llama a `pull_drive_ev`, que sella el
`_caso.md` canónico con `register_drive_ev(case_id, …)` (`core/intake_drive.py:320-323`). Ese efecto
está entre las transitivas que mi propio §8 excluye. Así que mi criterio 1 —«canon intacto,
verificado por hash de los dos árboles»— **es insatisfacible con el entrypoint que yo elegí**. No es
un matiz: es una contradicción interna entre el §7 y el §8 del mismo documento.

**H24-04, verificado por lectura, y es una cita mía sin comprobar.** `dir_para(".")` devuelve la
base (`core/casos/escritura.py:92-100`) y `escribir_texto`/`escribir_bytes` devuelven el `Path`
escrito (`:102-116`). La doctrina de 3A —*«no devuelve la raíz canónica»*— es más estrecha que su
prosa: no la devuelve, pero entrega un directorio dentro de ella. Repetí la frase del predecesor
como si fuera una garantía verificada. **Séptima aparición de «el nombre de una cosa no es la
cosa»**, y la primera en que la cita heredada era de mi propio repo.

**Diferencia de entorno.** El revisor reporta 1 fallo en la suite completa
(`test_mcp_wrappers[expedientes_xl]`, que vacía `PATH` y pierde `ping`) y él mismo lo declara
ambiental. Mis dos corridas del mismo árbol dieron 0. **Y tiene razón en la crítica de forma:** mi
«3.735 / 0 / 0 / 87» mezcla `skipped` y `xfailed` en una sola casilla; lo correcto es
**77 skipped + 10 xfailed**.
