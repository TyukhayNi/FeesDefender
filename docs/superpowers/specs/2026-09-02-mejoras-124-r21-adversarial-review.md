---
tipo: revision-adversarial
objeto: "diseño de MEJORAS #124 — quién contesta «¿cuál es la copia de trabajo?»"
objeto_rev: "rama claude/orquestrador-apertura-expediente-8f31bb, commit f062639"
commit: f062639
ronda: "21"
revisor: Codex
veredicto: NO-EJECUTABLE
marcador_nonce: k7wq
sha256_informe: 64179273e4ee589da32cf1e6d49b27b622c362cd0fbabcce82b0212dd128fc30
adjudicado_en: docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md §8
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R21.** El §1 conserva la voz del revisor sin una coma cambiada; la
> **adjudicación** vive en el **§8 del plan**
> (`docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md`). Es la ronda de **DISEÑO**:
> se corrió **antes de escribir una línea de código**, que es para lo que existe.
>
> Veredicto `NO-EJECUTABLE`: **8 hallazgos** — 4 CRÍTICOS, 3 ALTOS, 1 BAJO. Adjudicados: **8
> confirmados, 0 refutados** (con un matiz acotado en H21-07, §8 del plan).
>
> **El bloque literal archiva DOS textos.** El mandato pedía el veredicto en un fichero aparte
> (`VEREDICTO.md`) porque el guard **G9** exige que la palabra del veredicto conste literalmente en
> el bloque archivado, y un informe que no la contenga obligaría a que la escribiera yo — que es
> exactamente lo que el acta existe para hacer imposible. Los dos textos van dentro del bloque; esta
> explicación va fuera.
>
> **Esta ronda EJECUTÓ.** El revisor reprodujo las dos sondas del plan, escribió las suyas, corrió
> la suite entera desde una copia y midió la adopción del canon. El crítico mayor salió de una
> sonda, no de una lectura.
>
> **No-mutación acreditada por partida doble.** El hash agregado del objeto (1.121 ficheros) es
> idéntico al abrir y al cerrar — `f4fbfd7ed17d2e8d956a7d7a35bfb434430a96f28c2cb4d17c4dae80e82f705b`
> — y **lo recomputé yo por mi cuenta** antes y después de la ronda, con el mismo resultado. La
> garantía no depende de la palabra del revisor.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k7wq -->
# R21 — revisión adversarial del diseño de `MEJORAS #124`

Objeto revisado: `C:/tmp/r21/objeto`

Documento: `docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md`

## Huella de apertura

`sha256 agregado: f4fbfd7ed17d2e8d956a7d7a35bfb434430a96f28c2cb4d17c4dae80e82f705b` (1.121 ficheros).

La huella es el SHA-256 del UTF-8 sin BOM de la lista ordenada por ruta relativa, con una línea
`<sha256-del-fichero><dos espacios><ruta-con-/>` por fichero y `\n` entre líneas, sin salto final.

## Mediciones reproducidas antes de los hallazgos

- La sonda de §1.1 se reproduce: `buscar()` devuelve el canon, la copia registrada está fuera del
  catálogo y `es_copia_prestada()` devuelve `False`.
- La afirmación eje de §1.3 también se reproduce. Con el canon en `prestado`, la conducta actual
  lleva los bytes a `<canon>/_pendiente_checkin/email/00_Input/03_Email`; sustituyendo únicamente
  `es_copia_prestada` por `lambda _: True`, los bytes caen en `<canon>/00_Input/03_Email`, sin
  desvío y sin tocar la copia externa.
- Los nueve tests vigentes pasan. Si se cambia solo su fixture para registrar una copia externa,
  fallan los cuatro tests de la supuesta copia local. Esto confirma el defecto ordinario, aunque
  no confirma que la fixture original represente un estado imposible.

Comandos y salidas esenciales:

```text
python.exe r21_probe_mediciones.py
es_copia_prestada=False
arreglado_bajo_canon=True
arreglado_bajo_local=False

python.exe -m pytest tests/test_guard_copia_prestada.py -q \
  --basetemp=../.pytest_tmp_guard2
......... [100%]
```

## H21-01 — La adopción productiva registra el canon como copia local y el diseño conserva el agujero

**Severidad: CRÍTICO**

### Evidencia

El plan basa §1.1, §1.5, E1 y la derivación de `es_canon` en que el registro solo contiene rutas
fuera del catálogo (`plan:51-52, 101-103, 118, 168-170`). Esa invariante no existe en la frontera
que escribe el registro:

- `WorkspaceRegistry.alta()` registra `entrada.local_path` sin comprobar `bajo_catalogo`
  (`core/casos/workspace_registry.py:235-247`).
- `verificar_adopcion()` comprueba directorio, manifiesto, W-code y lock propio, pero no que el
  directorio esté fuera del catálogo (`core/casos/workspace_adopcion.py:68-105`).
- `adoptar()` pasa literalmente `case_dir` a `registry.alta()`
  (`core/casos/workspace_adopcion.py:122-152`), y ésa es la vía del CLI productivo
  (`scripts/repository_cli.py:1229-1261`).
- La prohibición está solo en `resolver_por_ruta()` (`core/casos/workspace_resolver.py:140-155`).
  `resolver_por_identidad()` consume la entrada sin revalidar su raíz y devuelve
  `LOCAL_CHECKOUT` con `entrada.local_path` (`:122-136`).

La condición es alcanzable porque el canon también recibe `MANIFEST_CHECKOUT.json` durante el
checkout. La sonda ejecutada sobre la copia produjo:

```text
ADOPCION ok= True
ADOPCION local_path_es_canon= True
ADOPCION identidad.mode= local_checkout
ADOPCION identidad.working_root_es_canon= True
ADOPCION resolver_rechaza_canon= WORKSPACE_UNDER_CATALOG_ROOT
ADOPCION es_copia_prestada= True
ADOPCION estado= prestado
ADOPCION escritura_canon_existe= True
```

Comando: `python.exe C:/tmp/r21/informe/agent_mediciones/sonda_adopcion_canon.py`, con
`SONDA_BASE` y `PYTHONPATH` apuntando exclusivamente al scratch y a la copia.

El defecto sobrevive al remedio: `resolver_destino(ref, ...)` usa la resolución por identidad;
puede construir `Destino(raiz=canon, es_canon=False, modo=LOCAL_CHECKOUT)`. §3.2 manda entonces
cero desvío. F3 no lo ve porque solo protege `es_canon=True`.

### Qué habría que hacer

Convertir «ninguna entrada apunta bajo el catálogo» en invariante de almacenamiento y de lectura:
rechazo en `WorkspaceRegistry.alta`, rechazo previo en `adoptar`, revalidación al cargar y al
resolver por identidad, incluida identidad física/alias de Windows. Añadir el escenario
`adoptar(canon)` como canario y mutante independiente. `es_canon` no debe derivarse de `mode` hasta
que esa invariante esté efectivamente cerrada.

## H21-02 — `Destino` no transporta el veredicto de escritura y vuelve a exponer la raíz que 3A ocultó

**Severidad: CRÍTICO**

### Evidencia

D124 exige que una sola resolución entregue «el veredicto Y la raíz» y que no exista una API que
dé uno sin la otra (`plan:138-143`). Sin embargo, `Destino` solo contiene `raiz`, `es_canon`, `modo`
y `procedencia` (`:149-156`). La firma de `resolver_destino` no recibe `ruta_relativa`, `origen` ni
`es_protocolo` (`:158-161`), aunque la decisión efectiva depende de esos tres valores
(`core/repository_checkout.py:541-576`). Por construcción, la nueva pieza no puede devolver la
`DecisionEscritura`; el guard tendrá que decidir otra vez o perder reglas.

El dilema ya aparece con un estado desconocido: el resolver clasifica cualquier estado distinto de
`prestado` y `conflicto` como `DRIVE_ACTIVE` (`core/casos/workspace_resolver.py:96-109`), mientras
el guard vigente desvía cualquier estado distinto de `disponible`
(`core/repository_checkout.py:565-576`). Si el guard confía en el modo, cambia conducta; si relee
el estado para conservarla, viola D124.

Además, §3.1 hace `raiz: Path` pública y T4 ordena entregarla a los consumidores. Es exactamente la
capacidad que el plan cita como prohibida. La costura vigente oculta `_base` y solo permite efectuar
escrituras contenidas (`core/casos/escritura.py:52-116`); su contrato dice que no devuelve la raíz
(`docs/superpowers/plans/2026-08-26-apertura-v1-plan3-write-set.md:143-145, 284-290`). F1, «devolver
`bool`», solo detecta una rotura de tipo; no detecta recomputar `caso_path`, ignorar el veredicto o
extraer el `Path` y escribir fuera de la capacidad.

### Qué habría que hacer

Definir un resultado por operación que incluya todos los insumos del guard y entregue una capacidad
ligada al destino, no un `Path` público. Una salida coherente es que la única puerta produzca un
`Deposito`/capacidad cuya base siga privada y cuya decisión quede fijada en el mismo valor. Añadir
mutantes funcionales que sustituyan la base autorizada por `caso_path`, recomputen el canon o
ignoren la decisión, verificados por efectos y hash.

## H21-03 — El fallback universal no tiene canon en todos los caminos y degrada errores de custodia a autorización

**Severidad: CRÍTICO**

### Evidencia

§3.3 promete que «registro ilegible, caso que el resolver bloquea, catálogo mudo,
`WorkspaceError` de cualquier clase» devuelve siempre un `Destino` con raíz canónica
(`plan:172-183`). Los `BLOCKED_*` sí vuelven como valor con `diagnostico=True`, pero llevan
`working_root=None` (`core/casos/workspace_resolver.py:99-120, 182-195, 250-259`), y
`CaseWorkspace` prohíbe darles raíz (`core/casos/workspace_model.py:505-519`). La salida tampoco
lleva `canonical_ref`: el resolver siempre la fija a `None` (`workspace_resolver.py:261-276`).

Los demás errores siguen lanzando aun con `diagnostico=True`. Sonda ejecutada:

```text
conflicto RETURN blocked_conflict root=None
prestado_ajeno RETURN blocked_foreign_checkout root=None
prestado_propio_sin_local RAISE LocalWorkspaceMissing
prestado_propio_nonce_mal RAISE LockMismatch
offline_sin_local RAISE RuntimeCannotAccessWorkspace
```

Fuente: `resolver_por_identidad`, en particular `workspace_resolver.py:68-90, 122-132, 219-248`.
También pueden escapar `AmbiguousCase`, `RegistryUnreadable` y `SchemaNoSoportado`.

Cuando ni catálogo ni registro conocen el caso, o el catálogo es ambiguo, no existe un canon único
con el que satisfacer `raiz: Path`. Una segunda llamada a `CaseCatalog.localizar()` repite la
resolución que D124 prohíbe y vuelve a lanzar; inventar `CASOS_ROOT/ref` reabre la creación de
expedientes fantasma que `localizar()` cerró (`core/casos/case_locator.py:27-59, 106-118`). Además,
tragar `LockMismatch`, ambigüedad o esquema ilegible y «desviar» sigue autorizando mutaciones en el
canon: bytes en bandeja y evento de intake.

### Qué habría que hacer

Sustituir el `except WorkspaceError` abierto por una tabla cerrada de error/resultado. Solo un
bloqueo con canon único conocido puede degradar a una capacidad expresamente limitada. Ambigüedad,
nonce discordante, registro/esquema no confiable, ausencia total y offline sin checkout verificado
deben abortar sin efectos o devolver un resultado explícito no escribible. El tipo debe poder
representar «no hay raíz» sin fingir un canon.

## H21-04 — T4 migra cuatro llamadas directas, pero deja el write-set transitivo partido entre copia y canon

**Severidad: CRÍTICO**

### Evidencia

El conteo de cuatro llamadas directas al guard es correcto, pero no es el censo de la frontera.
T4 solo nombra `dir_intake`, `deposito`, `intake_manual` y `sync_sudespacho`
(`plan:227-228`), y §7 excluye migrar las 83 escrituras (`:253-260`). Los consumidores que reciben
una base desviada vuelven a resolver por `case_id` para manifiestos, estado y auditoría:

- Manual: `_registrar_en_lote` construye `IntakeManifest(case_id)`
  (`core/intake_manual.py:55-67`); `IntakeManifest` fija su fichero y resuelve aliases mediante
  `caso_path(case_id)` (`core/intake_manifest.py:86-109, 149-151, 221-231`).
- WhatsApp: fija `case_dir=localizar(case_id)` y `IntakeManifest(case_id)` antes de reservar el lote,
  y escribe el evento en ese `case_dir` (`core/whatsapp_intake.py:154-175, 219-234`).
- Email: usa `IntakeManifest(case_id)` y eventos por `case_id`, aunque el lote salga de
  `reservar_lote` (`core/email_export.py:1250, 1311-1323, 1421-1431`).
- Drive E&V: los bytes usan `dir_intake`, pero `register_drive_ev(case_id, ...)` vuelve a mutar la
  ficha canónica (`core/intake_drive.py:188-197, 320-327`).
- CRM: `case_root` nace del canon antes del guard (`core/sync_sudespacho.py:1413-1415`); antes y
  después del guard escriben `RegistroOcurrencias(case_id)`, `IntakeManifest(case_id)`,
  `crm_branch_path(case_id)`, `update_pull_state(case_id)` y varios eventos
  (`:1462-1479, 1486-1508, 1550-1623, 1637-1667`). Sus clases internas también fijan ruta con
  `caso_path` (`core/ocurrencias_crm.py:70-89`; `core/intake_manifest.py:86-109`).

Por tanto, mover solo los bytes puede dejar bytes en la copia y manifest/log/estado en el canon,
contradiciendo T6 («canon intacto» y «log junto a los bytes»). Los ejemplos E1-E4 omiten al menos:

- E5: los escritores del registro no comparten la validación de `resolver_por_ruta`.
- E6: `resolver_por_identidad` confía en raíces no revalidadas.
- E7: manifiestos, ocurrencias, ficha y logs vuelven a resolver el canon por su cuenta.
- E8: exponer un `Path` permite a cada consumidor separar otra vez autorización y efecto.

### Qué habría que hacer

Enumerar el write-set transitivo por consumidor y propagar la misma capacidad resuelta a todos sus
efectos, incluidos manifiesto, dedup, ocurrencias, `_caso.md` y eventos. Añadir E2E por consumidor,
con canon y copia como raíces señuelo distintas, que compare hashes de ambos árboles y compruebe que
bytes, manifest y log terminan juntos.

## H21-05 — F3 es falsa: el protocolo productivo está exento de desvío

**Severidad: ALTO**

### Evidencia

F3 afirma que `es_canon=True` y canon `prestado`/`conflicto` implican «siempre» desvío
(`plan:199, 205-208`). §3.2 promete conservar las reglas actuales, pero éstas eximen al protocolo:

```python
if es_protocolo or estado == ESTADO_REPO_DISPONIBLE:
    # desviar=False
```

Fuente: `core/repository_checkout.py:541-576`. `deposito` hace alcanzable ambos valores mediante
`es_protocolo=(clase == "protocolo")` (`core/casos/escritura.py:45-49, 177-182, 208-213`).

Sonda:

```text
F3 estado=prestado protocolo=False desviar=True
F3 estado=prestado protocolo=True desviar=False
F3 estado=conflicto protocolo=False desviar=True
F3 estado=conflicto protocolo=True desviar=False
```

### Qué habría que hacer

Decidir expresamente si F3 excluye escrituras de protocolo o si esta pieza retira la exención. Si
la conserva, formular F3 como «toda escritura no protocolaria» y probar por separado la excepción.
Si la retira en bloqueos, declararlo como cambio de conducta y cubrir sus efectos.

## H21-06 — No hay siete fronteras independientes y el mutante F5 sobrevive

**Severidad: ALTO**

### Evidencia

El propio fallback hace observacionalmente neutro quitar `diagnostico=True`. Con el diseño literal
de §3.3, el modo bloqueado diagnosticado cae al fallback; sin diagnóstico, `CaseLocked` o
`CaseConflict` cae en el `except WorkspaceError` y produce el mismo fallback. Sonda de la envoltura
descrita por el plan:

```text
F5 conflicto diagnostico_true= FALLBACK diagnostico_false= FALLBACK
F5 prestado diagnostico_true= FALLBACK diagnostico_false= FALLBACK
```

Por tanto F5 no muere. También hay errores de apuntamiento/cobertura:

- F1 mata una incompatibilidad de tipo, no la doble resolución ni una raíz recomputada.
- F2 reúne dos propiedades —cero desvío y bytes exactamente en `raiz`— pero solo muta la primera.
- F3 es falsa por H21-05.
- Ningún mutante cubre individualmente los cuatro consumidores de T4 ni sus escritores transitivos.
- Falta el mutante `adoptar(canon)`/`LOCAL_CHECKOUT` con raíz canónica de H21-01.
- F6 se puede eludir reintroduciendo la consulta bajo otro nombre; F7 agrupa tres ayudantes y dos
  scripts bajo un único guard estructural.
- El criterio «el aserto nombra la suya y no las otras seis» (`plan:243-244`) comprueba texto del
  mensaje, no que solo el test de esa frontera mate al mutante.

### Qué habría que hacer

Redefinir la matriz como mutantes observables e independientes: raíz reemplazada por canon;
desvío local; escritura fuera de la capacidad; adopción del canon; uno por cada consumidor y por
cada efecto auxiliar; error de custodia degradado a fallback; y una prohibición estructural por
ayudante. Para cada mutante, fijar el test que debe fallar y comprobar que los restantes conservan
su resultado esperado.

## H21-07 — T2 propone una matriz con celdas imposibles y varios criterios de salida no son ejecutables

**Severidad: ALTO**

### Evidencia

T2 pide «la matriz completa modo × estado del canon» (`plan:219-220`), pero modo y estado no son
dimensiones independientes:

- disponible/no prestado produce `DRIVE_ACTIVE` (`workspace_resolver.py:96-109`);
- conflicto produce `BLOCKED_CONFLICT` (`:99-104`);
- préstamo ajeno produce `BLOCKED_FOREIGN_CHECKOUT` (`:111-120`);
- préstamo propio con entrada y nonce correctos produce `LOCAL_CHECKOUT` (`:122-136`);
- `LOCAL_SCRATCH` por identidad exige que no haya canon (`:88-90, 209-232`);
- scratch más canon produce `AmbiguousCase` (`:79-86`).

Una tabla cartesiana fabricaría `DRIVE_ACTIVE×conflicto`, `LOCAL_SCRATCH×prestado` y otras celdas
que producción no genera, repitiendo el defecto de la fixture actual. Además omite las dimensiones
que sí deciden: usuario, máquina, nonce, candidatos, tipo de entrada y `drive_accesible`.

Los criterios tampoco fijan observables suficientes:

- C3 no prueba independencia de mutantes, solo el texto del aserto.
- C4 dice que «la rama muere» sin indicar mutación, comando ni fallo esperado.
- C6 no enumera qué vías de `streamlit_app.py` ni qué efectos constituyen «cero cambio».
- T6 dice cuatro planos, pero no exige la matriz consumidor × plano ni identifica qué evento debe
  acompañar a cada byte.
- C5 exige dos semillas 777/31337, pero el intérprete expresamente suministrado no tiene
  `pytest-randomly`; `import pytest_randomly` dio `ModuleNotFoundError`. En este entorno el criterio
  no se puede ejecutar.

### Qué habría que hacer

Sustituir el producto cartesiano por una tabla de escenarios productivos completos, cada uno
obtenido llamando al resolver real y con resultado/excepción, raíz, decisión y efectos esperados.
Convertir cada criterio en comando, fixture, mutante y observable exactos. O bien declarar e
instalar la dependencia que implementa las semillas, o sustituir ese gate por un mecanismo de orden
disponible en el entorno autorizado.

## H21-08 — Varias cifras son correctas, pero algunas referencias no prueban la afirmación asociada

**Severidad: BAJO**

### Evidencia

Comprobación una por una de las referencias y cifras materiales del plan:

| Afirmación o referencia | Resultado |
|---|---|
| `PLAN.md`, fila #15 | Correcta: `PLAN.md:34`. |
| `case_locator.py:121-143` | Correcta: cuerpo completo de `buscar`, solo bajo catálogo. |
| `workspace_model.py:224-225` prueba que el registro excluye el canon | Incorrecta: ahí solo se declara la excepción. El rechazo está en `workspace_resolver.py:150-152` y no gobierna `WorkspaceRegistry.alta`. |
| Cuatro llamadas directas al guard | Correcto: `case_manager.py:913`, `casos/escritura.py:210`, `intake_manual.py:262`, `sync_sudespacho.py:1494`. |
| `dir_intake:912-916` | Correcta. |
| `deposito:210-213`, resolución `:119-131` | Sustancialmente correcta; la interfaz que no transporta workspace está en `:161-162` y la localización exacta en `:131`. |
| `intake_manual:255-270` | Correcta. |
| `sync_sudespacho:1494` acredita raíz canónica | Incompleta: `:1494` solo llama al guard; la raíz se fija en `:1413`. |
| `sala_maquina.py:363` es la consulta al resolver | Imprecisa: `:363` inicia la función; se construye en `:394` y se llama en `:401`, `:428` y `:447`. Es el único módulo productivo que lo construye. |
| Helpers `sala_maquina:274-286`, `repository_cli:1216-1227`, `_drive_accesible:288-325` | Rangos correctos. `_registro_de_workspaces` es literal; `_identidad_actor` es equivalente/AST-idéntico, no texto literal por una línea en blanco. |
| Fixture `test_guard...:81-87` | Correcta en contenido; falsa la conclusión de que producción la prohíbe, por H21-01. |
| Nueve tests del fichero | Correcto: nueve `test_*`; pasan los nueve. |
| Cinco modos | Correcto: `workspace_model.py:25-36`. La mención «§5.2» no identifica una subsección del plan; parece remitir sin decirlo a la spec dual. |
| Siete F1-F7 | Correcto como conteo textual, no como cobertura; véase H21-06. |
| 83 escrituras del censo | Reproducido: los tests del censo pasan y su techo vivo es 83. |
| 3.695 tests | Reproducido por colección: 3.695. |
| 3.695 tests, 0 fallos, 83 skip con semilla 777 | No reproducido: sin plugin de semillas, la corrida disponible dio 3.611 pass, 77 skip, 6 xfail y un fallo ambiental del wrapper `expedientes_xl`. |
| Cuatro rondas y 17 mutantes del mutex | Corroborada en `CLAUDE.md:67-72` y plan 3A `:190`; no genealogía. |
| PR #251, PR #236 y commit `e24b9c6` | Solo corroboración documental: la copia no tiene `.git`. |

### Qué habría que hacer

Corregir las citas que confunden declaración de excepción con enforcement, apuntar a la línea donde
nace cada raíz y distinguir igualdad textual de equivalencia AST. Registrar la salida real del gate
de suite sin sumar `skip` y `xfail` bajo una sola etiqueta.

## Condiciones propuestas y prueba de no-inercia

| Condición | ¿Puede ser verdadera y falsa en producción? | Resultado adversarial |
|---|---|---|
| `es_canon` | Nominalmente sí: `DRIVE_ACTIVE` frente a local checkout/scratch. | No es un discriminante fiable mientras H21-01 permite `LOCAL_CHECKOUT` con raíz canónica. |
| `es_protocolo` | Sí: `clase="protocolo"` y las otras tres clases. | F3 olvida la rama verdadera. |
| `drive_accesible` | Sí en el entrypoint existente mediante `FEESDEFENDER_OFFLINE=1` o su ausencia (`sala_maquina.py:288-325`). | El plan no fija que los cuatro consumidores compartan la misma fuente. |
| modo bloqueado/no bloqueado | Sí. | Con `diagnostico=True`, solo conflicto y préstamo ajeno devuelven modo bloqueado; otros errores lanzan. |
| `diagnostico` en la puerta nueva | No: el plan lo fija siempre a `True`. | Su mutación a `False` no cambia el resultado observable bajo el catch-all; F5 es inerte como mutante. |
| `modo is None` | En principio sí: fallback frente a resolución útil. | No es construible para toda la clase prometida porque puede faltar una raíz canónica. |
| `procedencia == "catalogo_legacy"` | No demostrado para todos los casos declarados. | En «catálogo mudo» no hay `raiz` con la que construir esa variante. |
| modo × estado del canon | No. | Muchas celdas son imposibles por construcción; no debe testearse como producto cartesiano. |
| Guards AST F6/F7 | No son condiciones de producción. | Son controles de estructura; deben probar la propiedad observable que intentan preservar. |

## Ejecución de suite

La suite se ejecutó desde `C:/tmp/r21/informe/objeto_copia`, con
`--basetemp=../.pytest_tmp_suite2`. Resultado: 3.695 tests coleccionados; 3.611 pass, 77 skip,
6 xfail conocidos y 1 fallo en
`tests/test_mcp_wrappers.py::test_sin_interprete_capaz_el_wrapper_FALLA_RUIDOSAMENTE[expedientes_xl]`.
El fallo fue que, con `PATH` envenenado por el propio test, el `.bat` emitió repetidamente que
`ping` no existe y no llegó a nombrar `FEESDEFENDER_PYTHON`/`FEESDEFENDER_ROOT`. No se atribuye al
plan R21. Los 18 tests dirigidos de censo + guard pasaron.

## Lo que NO pude verificar

- **SIN VERIFICAR:** genealogía de `f062639`, `e24b9c6`, `origin/main` y los PR citados. El objeto no
  tiene `.git`; se verificó contenido, no historia.
- **SIN VERIFICAR:** suite con semillas 777 y 31337. El intérprete no tiene `pytest-randomly` y el
  encargo prohíbe fingir esa cobertura.
- **SIN VERIFICAR:** la cifra histórica exacta «0 fallos, 83 skip con 777». La colección 3.695 sí se
  reprodujo; la clasificación/resultado de aquella corrida no.
- **SIN VERIFICAR:** muerte real de mutantes F1-F7 sobre la implementación futura. Aún no existe
  código que mutar; se probó que F5 sería neutro bajo el pseudocódigo exigido y se auditó la
  cobertura del diseño.
- **SIN VERIFICAR:** «cero cambio» en todas las vías de Streamlit del criterio 6; el criterio no las
  enumera y no existe el diff.
- **SIN VERIFICAR:** comportamiento sobre Drive real, caché de Drive for Desktop, junctions y alias
  8.3. Las sondas fueron locales y herméticas.
- **SIN VERIFICAR:** cada una de las 83 primitivas de escritura individualmente. Se confirmó el
  censo y se siguieron los consumidores relevantes del guard, no se ejecutaron 83 E2E.

## Huella de cierre

`sha256 agregado: f4fbfd7ed17d2e8d956a7d7a35bfb434430a96f28c2cb4d17c4dae80e82f705b` (1.121 ficheros).

La igualdad exacta con la huella de apertura acredita que ningún fichero del objeto cambió durante
la ronda.

----- VEREDICTO.md (fichero aparte, pedido asi en el mandato) -----

NO-EJECUTABLE
El diseño conserva una vía productiva de escritura sin desvío sobre el canon prestado y no define un resultado capaz de transportar a la vez autorización, raíz y fallback seguro.
<!-- informe-literal:fin:k7wq -->

## 2. Evidencia verificada por el adjudicador

Lo comprobado contra la fuente antes de adjudicar, **no contra el informe**:

- **H21-01, reproducido por mí con sonda propia.** `adoptar(<ruta del canon>)` es **ACEPTADO**:
  `verificar_adopcion` comprueba directorio, `MANIFEST_CHECKOUT.json`, W-code del nombre, estado
  `prestado` y titularidad del lock — y **no** comprueba que la ruta esté fuera del catálogo
  (`core/casos/workspace_adopcion.py:68-105`). `WorkspaceRegistry.alta` tampoco
  (`core/casos/workspace_registry.py:235-247`): solo rechaza reusar la ruta de **otro** caso. Salida
  de mi sonda, con el canon en `prestado` a mi propio usuario y máquina:

  ```
  verificar_adopcion.ok  : True | checkout propio con manifest y nombre coherente
  adoptar(CANON)         : ACEPTADO
  es_copia_prestada      : True
  dir_intake             : <CANON>\00_Input\03_Email      ← SIN desviar
  resolver .mode         : local_checkout
  resolver .working_root : <CANON>
  ```

- **H21-05, verificado por lectura.** `decidir_escritura` exime al protocolo **antes** de mirar el
  estado: `if es_protocolo or estado == ESTADO_REPO_DISPONIBLE` (`core/repository_checkout.py:565`),
  y `deposito` hace alcanzable el valor verdadero con `es_protocolo=(clase == "protocolo")`
  (`core/casos/escritura.py:212`).

- **H21-04, verificado por lectura.** `manifest_path` y `registro_path` fijan su fichero con
  `caso_path(case_id)` (`core/intake_manifest.py:86-88`, `core/ocurrencias_crm.py:70-72`), o sea que
  mover solo los bytes parte el expediente entre dos raíces.

- **H21-03, verificado por lectura.** `CaseWorkspace` prohíbe que un modo bloqueado lleve raíz
  (`core/casos/workspace_model.py:509-513`), así que un `BLOCKED_*` diagnosticado **no puede**
  suministrar el canon que mi §3.3 prometía.

- **La suite del revisor** dio un fallo en
  `tests/test_mcp_wrappers.py::test_sin_interprete_capaz_el_wrapper_FALLA_RUIDOSAMENTE[expedientes_xl]`
  que él mismo atribuyó al `PATH` envenenado de su sandbox. **Mi corrida base del mismo commit dio 0
  fallos**, así que es de su entorno y no del objeto. Lo digo aquí y no en el plan porque es una
  diferencia entre entornos, no un hallazgo.
