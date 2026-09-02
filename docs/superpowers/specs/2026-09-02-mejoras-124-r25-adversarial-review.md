---
tipo: revision-adversarial
objeto: "diff de la costura sobre workspace y su primer cliente (MEJORAS #124, alcance recortado)"
objeto_rev: "rama claude/mejoras-124-rev2, commit 5e75553"
commit: 5e75553
ronda: "25"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p3kd
sha256_informe: e39d1da9263aac0d24f77fbbd6456ed3cb9f38352a4a70edafbace4ac47bb016
adjudicado_en: docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md §10
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R25.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicación** vive en el **§10 del plan**. Es la ronda del **DIFF**.
>
> Veredicto `NO-SHIP`: **8 hallazgos — 1 CRÍTICO, 5 ALTOS, 2 BAJOS**. Adjudicados: **todos confirmados, 0
> refutados**; los graves **reproducidos con sondas propias** antes de remediar.
>
> **Lo que esta ronda compró.** Los dos primeros hallazgos son una **regresión que yo
> introduje**: mi vía nueva aceptaba una identidad que la vía histórica rechazaba, y tomaba el
> mutex del namespace equivocado. La causa es una frase que escribí en un docstring —«el resolver ya
> validó la identidad contra el canon»— **sin comprobarla**. Octava aparición de «el nombre de una
> cosa no es la cosa», y la primera que produce una regresión de autorización.
>
> **Y midió que mis tests no protegían el cableado:** mutó los cuatro `dep=_dep_sala` a llamadas
> directas y mis diez tests siguieron verdes, porque llamaban a los *helpers* y no a los *comandos*.
>
> **El bloque literal archiva DOS textos**, por lo mismo que en R21-R24: el guard G9 exige la
> palabra del veredicto dentro del bloque y el informe no la contiene.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p3kd -->
# Revisión adversarial R25 — costura sobre workspace y primer cliente

Revisión de corrección en solo lectura. Claude Code adjudica estos hallazgos contra la fuente.

## SHA-256 agregado al abrir

`3334f6e070e18618f1ac98b807df45fb6d258afad8c9a1e34aa6cb13ad682fd0`

Calculado sobre 1.131 ficheros de `C:/tmp/r25/head`: para cada fichero, SHA-256 de sus bytes; lista de líneas `<sha256>  <ruta-relativa-posix>` ordenada lexicográficamente por ruta; unión con `\n`, sin salto final; SHA-256 del UTF-8 resultante.

## H25-01 — Un W-code contrario al canon obtiene el mutex equivocado y escribe en el caso real

**Severidad: CRÍTICO**

**Evidencia.** La premisa de `core/casos/escritura.py:191-192` —«el resolver ya validó [la identidad] contra el canon»— no es cierta. `core/casos/case_catalog.py:178-190` busca primero por W-code, pero si no encuentra candidato cae a `case_id` sin comprobar que el `_caso.md` localizado declare el mismo W-code. `core/casos/workspace_resolver.py:114-117,294-305` conserva sin enriquecer ni contrastar el `CaseRef` pedido. Finalmente, `_identidad_de_workspace()` (`core/casos/escritura.py:201-216`) solo compara `workspace.case_ref.w_code` con `ref.w_code`; ambos contienen el mismo valor falso.

Reproducción ejecutada con el resolver real:

```text
canon._caso.md: meta.id_go = W-REAL01
petición: CaseRef(case_id=<carpeta real>, w_code=W-FAKE01)
resolver: DRIVE_ACTIVE, working_root=<canon real>, case_ref.w_code=W-FAKE01
deposito(..., workspace=None): IdentidadDiscordante
mutex sostenido: solo W-FAKE01
deposito(..., workspace=ws, modo="v1"): protegida_por_mutex=True
escribir_texto(...): escribe bajo el canon W-REAL01
```

Comando:

```powershell
python.exe -m pytest -p no:randomly -p no:cacheprovider `
  --basetemp '..\.pytest_core_independent' `
  tests\test_adversarial_core_workspace.py::test_resolver_real_puede_devolver_w_code_discordante_y_deposito_lo_acepta -vv
```

Salida: `1 passed`. El test pasa porque caracteriza la autorización con el lock equivocado y comprueba además que la vía histórica rechaza la misma referencia.

**Qué habría que hacer.** El workspace entregado por el resolver debe portar una identidad canónica validada, no simplemente el `CaseRef` de entrada. Al localizar por `case_id`, hay que leer y contrastar/enriquecer `meta.id_go`; si el W-code pedido y el canónico discrepan, debe lanzarse `IdentidadDiscordante` antes de entregar `DRIVE_ACTIVE` o cualquier capacidad. Añadir una regresión que exija el mutex de `W-REAL01` y rechace `W-FAKE01`.

## H25-02 — Resolver solo por `case_id` pierde el W-code canónico y la vía nueva deja de proteger con mutex

**Severidad: ALTO**

**Evidencia.** Para un canon cuyo `_caso.md` declara `W-REAL01`, `CaseWorkspaceResolver.resolver_por_identidad(CaseRef(case_id=CASE))` devuelve un workspace cuyo `case_ref.w_code` sigue siendo `None`. La vía histórica `_identidad(ref)` devuelve `W-REAL01`; `_identidad_de_workspace(ref, ws)` devuelve `None` (`core/casos/escritura.py:201-220`). Por tanto, `modo="v1"` cambia de una identidad utilizable a `IdentidadNoUtilizable`, y `modo="libre"` escribe declaradamente sin mutex.

La misma función ignora por completo `case_id`: un workspace de `CASO-A` y un `ref` de `CASO-B`, ambos sin W-code, se aceptan y los bytes del pedido B caen en la raíz A. Si solo el `ref` trae W-code, ese W-code se adopta como namespace de la raíz A.

Comando conjunto independiente:

```powershell
python.exe -m pytest -p no:randomly -p no:cacheprovider `
  --basetemp '..\.pytest_core_independent' `
  tests\test_adversarial_core_workspace.py::test_case_id_only_pierde_id_go_que_el_canon_si_tiene `
  tests\test_adversarial_core_workspace.py::test_ref_y_workspace_con_case_id_distintos_sin_w_code_no_se_rechazan -vv
```

Salida: `2 passed`. Una suite contractual adicional produjo `4 failed`; entre ellos, `assert _identidad_de_workspace(...)[0] == "W-REAL01"` recibió `None` y el caso de dos `case_id` distintos no lanzó `IdentidadDiscordante`.

**Qué habría que hacer.** Normalizar el resolver para que `CaseWorkspace.case_ref` contenga la identidad canónica completa que ya ha comprobado. En la costura, comparar `case_id` cuando no exista un W-code común y rechazar cualquier pareja que no pueda demostrarse como el mismo caso; nunca rellenar el namespace desde una referencia discordante.

## H25-03 — `mode` y `working_root` no forman una invariante: un modo local puede omitir el guard sobre el canon

**Severidad: ALTO**

**Evidencia.** `CaseWorkspace.__post_init__()` (`core/casos/workspace_model.py:497-519`) solo exige raíz presente para modos utilizables. No prueba que `DRIVE_ACTIVE` apunte al catálogo ni que `LOCAL_CHECKOUT`/`LOCAL_SCRATCH` estén fuera. `_es_canon()` (`core/casos/escritura.py:161-169`) confía exclusivamente en el modo. Una instancia pública `CaseWorkspace(mode=LOCAL_CHECKOUT, working_root=<canon>)` es aceptada; con el canon marcado `prestado`, `deposito()` toma `_sin_desvio()`, devuelve `desviada=False` y escribe directamente, sin bandeja ni evento.

```powershell
python.exe -m pytest -p no:randomly -p no:cacheprovider `
  --basetemp '..\.pytest_core_contract' `
  tests\test_expected_core_workspace_contract.py::test_modo_local_no_puede_apuntar_al_canon_y_omitir_su_guard -q
```

Salida relevante: `assert dep.desviada is True` → `False`.

El resolver de producción sí mantiene hoy la dicotomía: `DRIVE_ACTIVE` nace de `catalog.localizar()` (`workspace_resolver.py:114-117`), y las rutas explícitas/locales se filtran fuera del catálogo (`:148-176,209-228`). El defecto queda condicionado a que un llamador construya el valor público directamente o a que aparezca otro productor; los tests del propio diff ya construyen `CaseWorkspace` a mano.

**Qué habría que hacer.** Convertir la relación modo/raíz en una invariante de construcción verificable: fábricas no públicas emitidas por el resolver, tipos distintos por modo, o una validación central que impida local-sobre-catálogo y Drive-fuera-del-catálogo. La costura no debe conceder el bypass del guard basándose en un campo que cualquier llamador puede combinar con cualquier raíz.

## H25-04 — `plan` llama a la costura pero no usa la capacidad para su escritura real

**Severidad: MEDIO**

**Evidencia.** `scripts/sala_maquina.py:714-719` obtiene `_dep_sala = _deposito_sala(ws)`, pero nunca consume esa variable. La escritura propia de `plan`, el manifiesto `_segmentacion.md`, sigue por `split.escribir_manifiesto(...)` directo en `scripts/sala_maquina.py:752-766`. Una sonda con bundle ejecutó `_deposito_sala`, pero ningún método del `Deposito` fue llamado. Así, ese sitio es una consulta decorativa: una decisión de destino de la capacidad sería ignorada, y la nueva llamada puede abortar `plan` aunque su resultado no intervenga en nada.

**Qué habría que hacer.** O bien retirar la llamada muerta de `plan` y declarar que solo `apply`/`reforzar` son clientes, o migrar la escritura de manifiestos mediante una capacidad cuya base corresponda. Añadir un test del comando completo que falle si la escritura vuelve a ser directa.

## H25-05 — El fallback captura una discordancia de identidad y la convierte en escritura directa

**Severidad: MEDIO**

**Evidencia.** `_deposito_sala()` (`scripts/sala_maquina.py:117-123`) convierte tanto `IdentidadNoUtilizable` como `IdentidadDiscordante` en `None`; los escritores usan entonces la vía directa (`:145-150,225-230`). `IdentidadDiscordante` no significa “falta namespace”: significa que no se ha demostrado qué caso se está escribiendo. Degradarla evita precisamente la comprobación que falló.

Hoy el `except` es estructuralmente inalcanzable por datos normales: se pasa el mismo `ws.case_ref` como `ref` y dentro del workspace, y `modo="libre"` no lanza `IdentidadNoUtilizable` por identidad ausente/inválida. La sonda confirmó `IdentidadDiscordante -> None`, `IdentidadNoUtilizable -> None`, y `RuntimeError -> propaga`. Si se corrige H25-01/H25-02 añadiendo contraste canónico en la costura, esta captura podría convertir el nuevo cierre en bypass directo.

**Qué habría que hacer.** No degradar `IdentidadDiscordante`; debe abortar. Decidir el contrato de identidad no utilizable en modo libre y probar una excepción realmente inducible por producción. Si no existe tal estado, retirar el fallback y su promesa documental.

## H25-06 — La suite no protege el cableado real de `apply` ni `reforzar`

**Severidad: MEDIO**

**Evidencia.** Se mutaron los cuatro pases `dep=_dep_sala` de `apply`/`reforzar` a llamadas directas. Todos los `test_sala_maquina*.py` terminaron con código 0. En un barrido más ancho, dos mutantes independientes —ignorar `dep` dentro de ambos helpers y sustituir por `None` las tres asignaciones de los comandos— sobrevivieron a 642 tests recogidos de las familias `*escritura*`, `*sala_maquina*` y `*workspace*`: 639 pasaron y 3 E2E lentos fueron omitidos.

Los tests nuevos invocan `_deposito_sala` y los helpers por separado (`tests/test_sala_maquina_por_la_costura.py:56-98`), pero no llaman a `apply`/`reforzar` observando que la persistencia atraviesa el objeto capacidad. Como la vía directa y la capacidad apuntan hoy a la misma ruta, los asertos de existencia no distinguen ambas implementaciones.

**Qué habría que hacer.** En tests de comando completo, inyectar un `Deposito` espía y exigir llamadas a `escribir_texto` para estado y cobertura; hacer que la vía directa sea un canario que lance. Cubrir por separado `apply`, `reforzar` y la decisión explícita que se tome para `plan`.

## H25-07 — Los JSON cambian de hash en Windows aunque conserven ruta y semántica

**Severidad: BAJO**

**Evidencia.** La vía anterior de `sala_maquina` usaba `Path.write_text(..., encoding="utf-8")`, que en Windows traduce `\n` a CRLF. `Deposito.escribir_texto()` fuerza `newline="\n"` (`core/casos/escritura.py:102-109`). Comparación ejecutada para `_sala_maquina_state.json`:

```text
base/directo: b'{\r\n  "procesados": ...\r\n}'
sha256 229870abdc70606633b2c6548ccb888bfee02db81f100007dc1b168c20b02f20

head/costura: b'{\n  "procesados": ...\n}'
sha256 e21aec4aaeef43e889872f0fad78a01f57849e0efc55b8e5e6566555531d205b
```

La ruta y `json.loads()` son iguales; `_cobertura.json` presenta la misma normalización. Los tests nuevos parsean JSON y no comparan bytes.

**Qué habría que hacer.** Declarar la normalización LF como cambio intencional y asumir el churn de hash/checkin, o preservar los bytes históricos. En ambos casos, fijar el contrato con un aserto de bytes si “sin cambio” incluye hashes.

## H25-08 — Quedan asertos inertes y fronteras nuevas sin prueba

**Severidad: BAJO**

**Evidencia.** `tests/test_escritura_sobre_workspace.py:104` contiene `assert CaseCatalog() is not None`: si el constructor retorna, el aserto no puede ser falso y no demuestra que el catálogo siga resolviendo. `:97-104` compara solo nombres base del árbol, no rutas ni contenidos; no detectaría un append a un fichero existente. `:136` solo comprueba que una función que retorna `Deposito` o lanza no retornó `None`. `tests/test_sala_maquina_por_la_costura.py:118-119` acepta indistintamente dos contratos (`None` o depósito con motivo).

La rama de W-code inválido en `_identidad_de_workspace()` (`core/casos/escritura.py:215-220`) tampoco está cubierta: el mutante que sustituyó `_w_code_valido(canon)` por `canon` sobrevivió a los 15 tests nuevos. Falta además el caso `workspace.case_ref.w_code=None` y `ref.w_code` presente.

**Qué habría que hacer.** Sustituir el aserto inerte por `CaseCatalog().localizar(REF) == canon`; hashear el árbol canónico antes/después; fijar una sola conducta para el fallback; y añadir casos de W-code inválido, W-code presente solo en una fuente y ambos modos `libre`/`v1`.

## Verificaciones sin hallazgo

- H18-01, para workspaces locales coherentes, sí queda cerrado: una prueba propia ejercitó `escribir_texto`, `escribir_bytes` y `dir_para` con `guard_escritura` convertido en excepción-canario. Los tres artefactos quedaron bajo `working_root` y el hash agregado del canon fue idéntico antes/después (`1 passed`). Mutex y contención no escribieron en el canon.
- `_caso.md` está efectivamente en `MERGE_EXCLUSIONS` (`core/config.py:391-399`), y tanto `repository_checkout.py:246-256` como `scripts/repository_cli.py:224-226` consumen esa lista al excluir el checkout. La primera mitad de la justificación del autor es correcta; falla la premisa de que `workspace.case_ref` ya esté enriquecido/contrastado.
- Los cinco modos actuales quedan clasificados: `DRIVE_ACTIVE`, dos locales y dos bloqueados. Las ramas canónica/local y bloqueada/no bloqueada se ejecutaron. Para un `CaseWorkspace` válido, el subpredicado `working_root is None` con modo no bloqueado no puede ser verdadero por `CaseWorkspace.__post_init__`; es defensa para objetos no conformes, no una rama productiva independiente.
- La omisión del guard en `LOCAL_CHECKOUT`/`LOCAL_SCRATCH` coherentes no pierde eventos ni exenciones aplicables: el único evento del guard es `pendiente_checkin`, ligado al desvío del canon, y `es_protocolo` solo evita ese desvío. Sobre copia local, `_sin_desvio()` reproduce la decisión pertinente.
- `workspace=None`: las 18 pruebas históricas de `test_escritura_costura.py` pasaron tanto en `base` como en `head`; después de la selección de identidad, el cuerpo histórico queda textualmente igual. No observé diferencia funcional por esa vía.
- `apply` y `reforzar` sí consumen la capacidad en el código actual para `_cobertura.json` y `_sala_maquina_state.json`. Se ejercitaron `--case-dir`, `FEESDEFENDER_OFFLINE=1`, `reforzar` con visión inyectada y `plan`; los efectos quedaron en el workspace esperado.
- Tests nuevos de `head`: `15 passed`. Suite relevante restaurada de core: `39 passed`. Barrido afectado: 642 recogidos, 639 pasaron y 3 E2E lentos se omitieron.

## Lo que NO pude verificar

- La suite completa no quedó verde en este sandbox. Lanzada correctamente desde la raíz de la copia y con `--basetemp '..\.pytest_full2_basetemp'`, terminó con nueve fallos no ligados al diff: ocho tests intentan crear ficheros/directorios dentro del árbol copiado y el proceso recibió `PermissionError`; `test_mcp_wrappers[...]expedientes_xl` vacía `PATH`, el batch intenta usar `ping` y muere sin alcanzar su diagnóstico. No los cuento como refutación ni como hallazgo R25.
- No pude reproducir las corridas aleatorias 777/31337: `pytest-randomly` no está instalado. Todo lo dependiente de orden/semilla queda **SIN VERIFICAR**.
- Los 3 tests lentos de `test_split_sala_maquina_e2e.py`, el corpus OCR/PII omitido, Ollama y el flujo externo real de visión quedaron **SIN VERIFICAR**.
- No ejecuté una carrera multiproceso real sosteniendo simultáneamente `W-FAKE01` y `W-REAL01`; sí quedó demostrada la autorización `protegida_por_mutex=True` con el lock falso y la escritura en el canon real.
- No hice trazado a nivel del sistema operativo de todas las lecturas. La ausencia de escrituras canónicas en el camino local coherente se verificó por hash y canarios de guard.
- No se reabrió el TOCTOU de junctions/reparse points creados después de construir `Deposito`, ya declarado por el código.

## SHA-256 agregado al cerrar

`3334f6e070e18618f1ac98b807df45fb6d258afad8c9a1e34aa6cb13ad682fd0`

Mismo algoritmo y 1.131 ficheros. Coincide con el hash de apertura: `C:/tmp/r25/head` no cambió durante la revisión.

----- VEREDICTO.md (fichero aparte, pedido asi en el mandato) -----

NO-SHIP
La vía workspace permite proteger el canon con un W-code discordante y pierde la identidad canónica al resolver solo por case_id.
<!-- informe-literal:fin:p3kd -->

## 2. Evidencia verificada por el adjudicador

Las sondas y su resultado —antes y después de remediar— están en la adjudicación
(§10 del plan). No se repiten aquí para que el acta siga siendo lo que debe ser: el
archivo de la voz del revisor, no un segundo hogar de la decisión.
