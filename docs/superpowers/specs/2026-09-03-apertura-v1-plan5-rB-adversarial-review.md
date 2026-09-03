---
tipo: revision-adversarial
objeto: "diff del Plan 5: el cableado de la secuencia de V1 (rev. 2 ejecutada)"
objeto_rev: "rama claude/expediente-apertura-orquestado-cd68c3, commit 5cdf7da"
commit: 5cdf7da
ronda: "B"
revisor: Claude Code (sesion independiente)
veredicto: NO-SHIP
marcador_nonce: v4nt
sha256_informe: 183d869f6f80bc15a18c228b3a93b62479579039162e6760833c4562cbb1265d
adjudicado_en: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §6
adjudicador: Claude Code
independencia_adjudicacion: DEBILITADA
---

> ## ⚠ La independencia de esta ronda es MAS DEBIL de lo contratado. Se dice primero.
>
> **El revisor NO es Codex.** Codex agoto su cupo a mitad de la ronda —quemo ~153.000
> tokens leyendo el codigo y murio sin escribir informe, con la cuota restablecida el
> **2026-09-07**—. Se aplico el **revisor sustituto** que `AGENTS.md` preve para
> indisponibilidad real: **una sesion de Claude Code, y por tanto el MISMO modelo que
> escribio el codigo**, con sus mismos puntos ciegos. Eso no se maquilla: el frontmatter
> dice `revisor: Claude Code (sesion independiente)` y esta linea dice por que vale menos.
>
> **La compensacion que el contrato exige, aplicada:** **seis lentes en paralelo**, una por
> area, sobre una **copia congelada** del commit `5cdf7da` (solo lectura por construccion),
> **sin el §5 del plan** (mi adjudicacion de R-A) y **sin el acta de R-A**, con prohibicion
> expresa de dar nada por bueno sin abrir el fichero y de convertir «no pude mirar» en «no
> hay nada». Las lentes **ejecutaron**: escribieron sus propios mutantes y sus propias
> sondas.
>
> **Veredicto `NO-SHIP`.** Recuento de las lentes: **73 hallazgos** —**10 CRITICOS**, 10
> ALTOS, 2 MEDIO-ALTOS, ~29 MEDIOS, ~22 BAJOS—. Adjudicacion completa en el **§6 del plan**.
>
> **Lo que decidio el veredicto no fue cobertura sino un defecto vivo:** las dos ramas de
> `traducir_pull_crm` que produccion alcanzaria eran INALCANZABLES, y la conducta real era
> la inversa de la documentada — un expediente CRM con el gestor documental vacio, o una
> `PHPSESSID` caducada a mitad del pull, **bloqueaban la apertura entera** sin que el OCR
> arrancase.
>
> **Y el hallazgo transversal, medido por tres lentes con mutantes propios:** el «28/28
> mutantes muertos» con que yo cerre la pieza era una **autoatestacion cerrada**. Cuatro de
> esas muertes caian sobre fronteras que no existen en produccion, y el conjunto de
> ficheros del arnes **excluia justo el cableado**. Dos lentes escribieron sus mutantes:
> 17 de 21 vivos en una, 11 de 12 en la otra.
>
> **Cobertura ausente, declarada:** la corrida real sobre W-02Q38C (Task 11) no se ejecuto;
> ninguna lente tenia `pytest-randomly`, asi que el orden aleatorio quedo SIN VERIFICAR por
> el revisor (lo cubrio el autor); y la atomicidad de `os.replace` sobre `G:\` tampoco se
> midio.
>
> **Prueba de no mutacion:** el objeto (`DIFF.patch`) conservo el `sha256`
> `06a52b2f99ffcaf5596afc8b78856970d8e269511ce30788a5ae9b3a22857abf` al abrir y al cerrar,
> y las seis lentes verificaron que `head/` quedo intacto.

## 1. Informe recibido de las seis lentes, sin modificar

<!-- informe-literal:inicio:v4nt -->

# VEREDICTO

NO-SHIP

Cinco lentes (2, 3, 4, 5 y 6) devuelven **54 hallazgos**: **6 CRÍTICOS** (L2-01, L4-01, L6-01, L6-02, L6-03, L6-04), **5 ALTOS** más 2 MEDIO-ALTOS (L3-01, L3-02, L4-02, L4-03, L5-01; L2-02, L3-03), **25 MEDIOS** contando los tres mixtos (L2-05, L4-08, L5-05) y **16 BAJOS**; falta `LENTE_1.md`, así que la comprobación sistemática de las 28 fronteras del §3 contra el código y el apuntado del arnés `tests/_mutantes_plan5.py` quedan **SIN VERIFICAR** como lente propia —aunque L6 corrió el arnés (28/28 real) y midió que cuatro de sus supervivientes caen sobre fronteras que el arnés nombra mutando el otro extremo de la costura, y L2/L4 encontraron dos mutantes certificados por inputs que producción no puede fabricar (F19/F20, F6, F27)—. Lo que decide el veredicto no es el recuento sino un defecto vivo medido con las clases reales: **L2-01**, donde las dos ramas de `traducir_pull_crm` que producción alcanzaría están detrás de `if errores:` y son inalcanzables, de modo que la conducta real es la **inversa** de la documentada — un expediente CRM registrado con el gestor documental vacío, o una `PHPSESSID` que caduca a mitad del pull, **bloquean la apertura entera** (exit 1, el OCR no arranca) donde el código dice «no es un fallo; es que no hay nada». A eso se suma **L4-02** (la `PermissionError` de `os.replace` con un handle abierto —antivirus, Drive for Desktop— no la captura nadie, y en `cerrar` invierte la semántica del detector y se come el evento forense de una corrida de una hora) y **L5-01/L4-06**, confirmado por dos lentes con el inventario real: `_apertura_v1.json` y sus temporales huérfanos entran en el inventario probatorio y en `_cobertura` como documentos ilegibles del caso, en cada ronda, mientras el comentario del censo afirma lo contrario. El hallazgo con más peso por convergencia lo firman **cuatro lentes independientes** (L2-02, L3-01, L4-05, L5-04): `estado_v1.cerrar` y `registrar_cierre_v1` corren **dentro** del bloque de mutex, así que perder el lease deja el disco y el `.jsonl` afirmando «ronda terminada con éxito» mientras la pantalla dice `bloqueado`, tira el informe con los pendientes, y hace que la ronda siguiente dé por buena la salida de una ronda sin exclusión — exactamente el riesgo de la spec que esta pieza existe para cerrar; y **cinco lentes** coinciden en que el aviso de ronda previa sin cerrar es decorativo y que `abrir` destruye acto seguido su única prueba. Igual de convergente es el vacío de cobertura: cuatro lentes midieron por mutación que el cableado de `main` no lo prueba nada (suprimir el aviso, el `cerrar`, el `registrar_cierre_v1`, el `_informar_v1`, el código de salida, o el reenvío de `--hasta`, deja la suite verde: 11 de 12 supervivientes en L3, 17 de 21 en L6), que `traducir_fallo_de_mutex` **no tiene llamador de producción** y sus tres tests y su mutante F26 certifican código muerto (L2-04, L3-03, L5, L6-08), que el `return status_atomizacion` de `apply` —única costura de la etapa 3— y el `force=force` de `_intake_drive_ev` se pueden anular sin un rojo (L6-01, L6-02), y que F25 vigila `ast.Raise` en vez de la propiedad, con `sys.exit` pasándole por debajo (L3-03/M12, L6-07). Quedan además **SIN VERIFICAR**: el orden aleatorio en todas las lentes (no hay `pytest-randomly` en el intérprete del encargo), la cadena `MutexPerdido → _bajo_mutex → Exit(2) → "fallo"` de L3-07, la atomicidad de `os.replace` sobre `G:\`, el comportamiento con `LongPathsEnabled = 0`, y la Task 11 del plan (corrida real sobre un caso vivo), que no se ejecutó. Las remediaciones parecen locales y **no exigen rehacer el diseño** —invertir el orden de dos ramas, sacar el cierre y el evento fuera del `with`, dos renglones en `_IGNORAR` y en `MERGE_EXCLUSIONS`, y los tests de cableado que faltan—, pero mergear tal como está entrega software incorrecto en un escenario de rutina y un registro durable que afirma un éxito que no hubo, así que la palabra es NO-SHIP.

---

# LENTE 1 — las 28 fronteras contra el codigo y el arnes de mutacion

# LENTE 1 — ¿están realmente contratadas las 28 fronteras del §3?

**Objeto:** `rB/head/` (congelado, solo lectura). **Trabajo:** `rB/lente1/t/` (copia byte a byte).
**`sha256` de `informe/DIFF.patch`** al abrir y al cerrar: `06a52b2f99ffcaf5596afc8b78856970d8e269511ce30788a5ae9b3a22857abf` (idéntico).
No escribí en `head/` ni en `base/`. Verificado al cerrar que las cinco fuentes de producción
tocadas por el diff coinciden en `sha256` entre `head/` y mi copia.

**Veredicto de la lente, en una frase:** los 28 mutantes se reproducen (28/28, cada uno solo por su
frontera), pero **el conjunto de las 28 fronteras no toca el cuerpo de `main`**: apliqué **13
mutantes simultáneos** en la rama `v1` de `scripts/abrir_caso.py` y en `core/apertura_v1_estado.py`
y **la suite ENTERA del repo (3.770 pruebas) quedó exactamente igual de verde**. Seis de las 28
fronteras enuncian propiedades del proceso (F13, F14, F25, F26, F27, F28) y se contratan solo
contra funciones puras o contra la forma sintáctica; una de ellas (**F26**) se contrata contra
**código muerto** que producción no llama.

---

## Evidencia

### Lo que abrí (leído entero, no ojeado)

| Fichero | Para qué |
|---|---|
| `head/docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md` líneas 168-201 | la tabla de las 28 fronteras (§3). No leí §5 ni ningún `*adversarial-review*`. |
| `head/core/apertura_v1.py` (136 líneas) | secuenciador |
| `head/core/apertura_v1_estado.py` (103 líneas) | estado durable |
| `head/scripts/abrir_caso.py` 141-190, 341-620, 693-1005 | costura, adaptadores, `validar_modo`, `main` |
| `head/scripts/sala_maquina.py` 506-560, 575-650, 784-923 | `_bajo_mutex`, `_atomizar_correo`, `apply` |
| `head/core/intake_drive.py` 163-230 | semántica real de `force` / `skipped` |
| `head/core/sync_sudespacho.py` 1288-1319 | campos reales de `PullResultV2` |
| `head/core/casos/mutex_sesion.py` (entero) | reentrancia |
| `head/core/sala_maquina.py` 146, 191-205, 1173-1235 | `_IGNORAR`, `plan`, `inventariar_cacheado` |
| `head/tests/_mutantes_plan5.py` (entero) y los 5 ficheros de la SUITE contractual | el arnés y lo que afirma |
| `head/tests/test_abrir_caso_modo_v1.py`, `head/tests/test_escritura_censo.py` 1-80, 249-259 | el único test que pasa por `main` en `v1`; el trinquete del censo |
| `informe/DIFF.patch` (2.113 líneas) | los 16 ficheros |

### 1. El arnés del autor se reproduce: 28/28

```
$ cd rB/lente1/t && python -m tests._mutantes_plan5
F1: MUERTO por su frontera (2 rojo/s)
F2: MUERTO por su frontera (3 rojo/s)
...
F28: MUERTO por su frontera (1 rojo/s)

28/28 mutantes muertos, cada uno SOLO por su frontera.
EXIT=0
```

La regla de comparación de conjuntos exactos del arnés funciona: no hay *mata de menos* ni *mata de
más* declarados. Baseline de la SUITE contractual: 63 verdes, 0 rojos.

**Aviso metodológico medido:** con `--basetemp` **dentro** del árbol, 30 tests de
`test_abrir_caso_cli.py` salen rojos con `WorkspaceUnderCatalogRoot('[WORKSPACE_UNDER_CATALOG_ROOT]')`.
Es artefacto mío, no del diff: con `--basetemp=../bt` van los 66 verdes. Lo dejo escrito porque es
un rojo falso muy fácil de confundir con un hallazgo.

### 2. El contra-arnés: 20 mutaciones sobre propiedades que el §3 no enumera

Escribí `rB/lente1/cm/contra.py`: misma mecánica (JUnit XML, `no:randomly`), pero corriendo una
suite de **18 ficheros** — los 5 contractuales más los 13 restantes que mencionan
`abrir_caso|apertura_v1|estado_v1` (`git grep` sobre `tests/`), todos verificados existentes.
Baseline 0 rojos.

```
BASE: 0 rojo(s) sin mutar
CM1:  *** VIVO *** — F26 aplicada al sitio REAL de main (no a la funcion muerta)
CM2:  *** VIVO *** — main no sale con codigo no cero cuando la secuencia queda bloqueada
CM3:  *** VIVO *** — F28: main no avisa de la ronda anterior sin cerrar
CM4:  *** VIVO *** — F27: main no ABRE el estado durable (nada queda en disco)
CM5:  *** VIVO *** — la sala de maquina corre sobre OTRO caso
CM6:  *** VIVO *** — F27: el temporal deja de estar en el MISMO sistema de ficheros
CM7:  MUERTO (1)   — agregacion multi-expediente: un gestor vacio deja de ser `saltada`
CM8:  *** VIVO *** — F8/F21/F22: las puertas solo miran el PRIMER expediente
CM9:  *** VIVO *** — F4/F23: `--hasta` de la CLI no llega a la secuencia
CM10: *** VIVO *** — el evento forense miente sobre la parada
CM11: *** VIVO *** — F24: el informe en pantalla no dice las etapas que no corrieron
CM12: *** VIVO *** — F13: main no emite el evento forense
CM13: *** VIVO *** — F16 en su ULTIMA MILLA: la costura no reenvia `force` a rclone
CM14: *** VIVO *** — F27/F28: main no CIERRA la ronda (toda ronda queda `sin_cerrar`)
CM15: *** VIVO *** — control: mutacion semanticamente NEUTRA (debe sobrevivir)
CM16: MUERTO (1)   — etapa_drive: un rclone no cero sin `errors` deja de ser fallo
```

Dos murieron y el control neutro sobrevivió: **el contra-arnés discrimina**, no está mudo.
En una segunda corrida, con `tests/test_sala_maquina*.py` añadidos:

```
CM17: *** VIVO *** — `apply` deja de propagar el status: F10/F11/F12 sin entrada real
CM18: MUERTO (2)   — control: `_atomizar_correo` deja de devolver el status
      rojo: test_atomizar_correo_devuelve_el_status
      rojo: test_atomizar_correo_devuelve_fallo_si_el_motor_revienta
CM23: *** VIVO *** — etapa_drive pide el pull en dry-run: la custodia no se registra
CM28: *** VIVO *** — F23: main deja de pasar `hasta` a la puerta
CM29: MUERTO (1)   — control: F9 sin la rama de `sin expediente`
```

`CM18` es el control decisivo: la misma clase de mutación un eslabón antes (`_atomizar_correo`)
**mata dos tests**; un eslabón después (`apply`) no mata ninguno.

### 3. La medición concluyente: 13 mutantes a la vez, suite completa del repo

Apliqué **CM1, CM2, CM3, CM4, CM5, CM6, CM8, CM9, CM10, CM11, CM12, CM13 y CM14 simultáneamente** y
corrí `python -m pytest` sobre **todo el repo**:

```
2 failed, 3770 passed, 77 skipped, 10 xfailed, 1 warning in 194.15s (0:03:14)
FAILED tests/test_session_close_no_pude_medir.py::TestLaVerja::test_el_mensaje_sugiere_un_interprete_QUE_EXISTE
FAILED tests/test_session_close_no_pude_medir.py::TestLaRutaQueSugiere::test_en_este_repo_encuentra_uno_que_existe
```

Los dos rojos son **preexistentes** y de entorno (mi copia no tiene `.venv/`): salen idénticos en el
árbol sin mutar. Es decir: **la rama `v1` de `main` completa, más las llamadas al estado durable,
más el cableado de `--hasta`, más la última milla de `force`, se pueden romper todas a la vez sin
que una sola prueba del repositorio se ponga roja.** Luego restauré desde los originales guardados
y verifiqué por `sha256`.

### 4. F25: contrata la forma, no la propiedad

`test_f25_...` (`test_apertura_v1_cableado.py:94-129`) parsea el AST de `main` y afirma que **no hay
ningún `ast.Raise`** en el cuerpo de la rama `modo == "v1"`. Enruté la salida por un helper de una
línea —el refactor más plausible que existe— dejando el `typer.Exit` **dentro** del `with` del mutex:

```python
def _salir(codigo: int) -> None:
    raise typer.Exit(code=codigo)
...
                registrar_cierre_v1(case_dir, ident, resultado_v1)
                _informar_v1(resultado_v1)
                _salir(codigo_de_salida(resultado_v1.estado))
```

```
BASE: 0
CM25: *** VIVO *** 0
```

Siete ficheros de test, `test_f25_...` incluido, siguen verdes con el proceso saliendo **dentro del
bloque de mutex**, que es literalmente el defecto de HA-07. (Una variante con `os._exit(0)` mató al
propio proceso de `pytest` y por eso no la pude medir con el arnés — anotado y descartada.)

### 5. Por qué muere cada mutante: F15 muere 5 de 6 veces por un error de montaje

El arnés compara **conjuntos de nodeids**, nunca la **razón**. Instrumenté el mutante F15 y medí la
razón real:

```
$ python -c "cli.etapa_drive(_I(), Path('.'), folder_id='F', team_id='T')"   # con el mutante F15
ESTADO: fallo
DETALLE: LocalWorkspaceMissing: [LOCAL_WORKSPACE_MISSING] — el caso no existe en el
         catalogo local — caso W-000000
```

Y las cinco muertes en el E2E:

```
test_e2e_..._y_las_LLAMA        assert ['drive'] == ['drive', 'crm', 'sala_maquina']
test_e2e_el_evento_...          assert 'bloqueado' == 'preparado_con_pendientes'
test_e2e_es_punto_fijo_...      assert {'drive': 0, 'crm': 0, 'ocr': 0} == {'drive': 2, ...}
test_e2e_un_fallo_del_crm_...   assert ('crm','sala_maquina') == ('sala_maquina',)
test_e2e_hasta_drive_...        assert {'drive': 0, ...} == {'drive': 1, ...}
```

Todas mueren porque el mutante llama al `pull_drive_ev` **real**, que hace `localizar(case_id)`, y
la fixture del E2E monta el caso en `tmp_path` y **no** en `CASOS_ROOT`. Ninguna de las cinco muere
porque «se rodeó la custodia»: mueren porque el caso no existe en el catálogo. Solo
`test_f15_bis` (que sustituye `cli._intake_drive_ev` y afirma `visto == ["custodia"]`) muere por su
frontera. Contrastado: los reds de F7, F16 y F3 en el E2E **sí** mueren por su razón (afirman sobre
`visto["element"]`, `visto["force"]` y el estado).

### 6. El censo, medido

```
scripts/abrir_caso.py 3
core/apertura_v1_estado.py 3
TOTAL 87 TECHO 87
PRIMITIVAS ['append_event','copy2','mkdir','unlink','write_bytes','write_text']
AMBIGUAS ['copy','dump','replace']
```

La cuenta cuadra (83 + 1 `append_event` en `abrir_caso` + `mkdir`/`replace`/`unlink` del módulo
nuevo = 87). `grep -rn "mkstemp"` sobre los 12 productores: **una sola aparición, la nueva**.

### 7. Lo que NO pude verificar

- **Dos semillas de `pytest-randomly`**: el intérprete del encargo no lo tiene (`-p no:randomly`
  en todas mis corridas). Cualquier dependencia de orden queda **SIN VERIFICAR**.
- **`os.replace` cruzando volúmenes** (hallazgo `L1-12`): no tengo dos sistemas de ficheros
  utilizables en este entorno. La *supervivencia del mutante* sí está medida; la *consecuencia en
  disco* queda **SIN VERIFICAR**.
- **La secuencia real cuando `MutexPerdido` sale de `sala_maquina.apply`** (hallazgo `L1-19`): la
  deduje de leer `mutex_sesion.sostenido` y `_bajo_mutex`; no construí el escenario. **SIN VERIFICAR.**
- **La corrida real sobre un caso vivo** (Task 11): no la hice y no está en el diff.

---

## Hallazgos

### `L1-01` — CRÍTICO — Ninguna de las 28 fronteras cubre el cuerpo de `main`

**Qué.** El §3 declara 28 fronteras «que este plan contrata». Trece mutaciones simultáneas en la
rama `v1` de `main` y en el módulo de estado dejan la suite completa del repo idéntica de verde.

**Dónde.** `scripts/abrir_caso.py:940-1001` (la rama `v1` entera), `core/apertura_v1_estado.py:76`.

**Por qué importa.** No es que falten fronteras sueltas: es que la **unidad de integración** —lo
único que un operador ejecuta— no tiene ninguna. El §3 mide adaptadores y secuenciador, que son
funciones puras o casi, y de `main` mide *una* propiedad (F25) y por su forma sintáctica. Las seis
fronteras cuya redacción habla del **proceso** (F13 «el evento final se emite», F14 «código de
salida distinto de 0», F25 «la salida ocurre fuera del bloque», F26 «`CaseBusy` → estado bloqueado
y salida no cero», F27 «`estado.json` se escribe», F28 «se detecta y se dice en el informe») están
contratadas contra funciones puras que `main` puede dejar de llamar sin consecuencia. El único test
que atraviesa `main` en modo `v1` (`test_abrir_caso_modo_v1.py:107-149`) dobla `secuencia_v1` **y**
`registrar_cierre_v1`, y afirma `exit_code == 0` sobre un resultado `preparado_con_pendientes`: no
puede distinguir «salió 0 porque el estado vale 0» de «salió 0 porque no hay salida». Y ese fichero
**no está en la SUITE del arnés** (`tests/_mutantes_plan5.py:26-30`), así que ni siquiera contribuye
a la medición de los 28.

**Cómo lo comprobé.** Ejecutado: 13 mutantes simultáneos, `2 failed, 3770 passed` — los mismos 2
rojos preexistentes de entorno. Restaurado y verificado por `sha256`.

**Qué haría falta.** Una prueba de integración que invoque `cli.app` en modo `v1` con los límites
doblados (`_intake_drive_ev`, `pull_expediente_v2`, `sala_maquina.apply`) pero **sin doblar
`secuencia_v1`, `registrar_cierre_v1` ni `estado_v1`**, y que afirme sobre lo observable: código de
salida por estado, `_apertura_v1.json` en disco con `terminada` puesto, el evento en el `.jsonl`, y
el texto del informe. Y meter ese fichero en la SUITE del arnés, o los mutantes de `main` seguirán
sin medirse.

---

### `L1-02` — CRÍTICO — F26 está contratada contra código muerto; el manejador real no tiene mutante

**Qué.** `traducir_fallo_de_mutex` no lo llama nada en producción. El mutante F26 la muta a ella; el
manejador que sí corre está en `main` y su mutación equivalente sobrevive.

**Dónde.** `scripts/abrir_caso.py:557-567` (la función muerta) frente a
`scripts/abrir_caso.py:992-995` (el manejador real). Mutante:
`tests/_mutantes_plan5.py:210-214`. Tests: `tests/test_apertura_v1_cableado.py:132-146`.

**Por qué importa.** `git grep traducir_fallo_de_mutex` sobre todo el árbol da cuatro sitios: la
definición, dos tests, y el plan. **Cero llamadores de producción.** Así que F26 —«`CaseBusy` y
`MutexPerdido` en la frontera → estado `bloqueado` y salida no cero»— está probada sobre un artefacto
que no participa en ninguna ejecución. Aplicada al sitio real (`except (CaseBusy, MutexPerdido):
raise`), la propiedad se rompe —vuelve el stacktrace que HA-07 quería eliminar y el código de salida
deja de ser el de `codigo_de_salida`— y **nada se pone rojo**. Es exactamente el modo de fallo que el
`CLAUDE.md` del proyecto llama «cerrar el caso que el informe describe en vez de la propiedad»: la
propiedad se nombró en una función nueva, y el sitio donde la propiedad tenía que vivir se cableó a
mano y sin contrato.

**Cómo lo comprobé.** Leído + ejecutado (`CM1`, VIVO en la suite de 18 ficheros y en la suite
completa del repo).

**Qué haría falta.** O `main` usa `traducir_fallo_de_mutex` (y entonces F26 mide algo), o se retira
la función y F26 se reapunta al `except` de `main` con un test que invoque el CLI con un `CaseBusy`
en vuelo y afirme el código de salida y el texto.

---

### `L1-03` — CRÍTICO — F14 no contrata que el proceso salga distinto de cero

**Qué.** Borrar la salida de `main` (`raise typer.Exit(code=codigo_de_salida(...))`) no rompe nada.

**Dónde.** `scripts/abrir_caso.py:997-999`. F14 en `tests/_mutantes_plan5.py:137-140`, test en
`tests/test_apertura_v1_cableado.py:88-91`.

**Por qué importa.** F14 dice «Estado `bloqueado` → código de salida distinto de 0». El test afirma
`cli.codigo_de_salida(av1.EstadoV1.BLOQUEADO) != 0` — una función de una línea. Quien consume V1 no
llama a esa función: lee `$LASTEXITCODE`. Con `CM2` aplicado, una apertura `bloqueado` sale **0** y
la pantalla dice «bloqueado»: exactamente el modo de fallo que el `CLAUDE.md` del proyecto tiene
escrito («nunca leer `$LASTEXITCODE` … hacer pasar por bueno un comando que falló»), esta vez del
lado del productor. Un runbook o un script que encadene la apertura con lo siguiente lo tomaría por
bueno.

**Cómo lo comprobé.** Ejecutado (`CM2`, VIVO en las 18 y en la suite completa).

**Qué haría falta.** Un test que invoque `cli.app` en `v1` con una etapa en `fallo` y afirme
`res.exit_code != 0`.

---

### `L1-04` — CRÍTICO — F25 contrata la forma sintáctica, no la propiedad

**Qué.** Su test prohíbe `ast.Raise` en el cuerpo de la rama `v1`. Sacar la salida por un helper la
devuelve **dentro** del mutex y el test sigue verde.

**Dónde.** `tests/test_apertura_v1_cableado.py:94-129` (el test), `scripts/abrir_caso.py:958-975`
(la rama), `tests/_mutantes_plan5.py:204-208` (el mutante).

**Por qué importa.** La propiedad que F25 dice contratar es «la salida del proceso ocurre fuera del
bloque de mutex», y su razón está bien argumentada en el propio docstring: con una excepción en
vuelo, `case_mutex.tomado` solo **anota** la pérdida del lease. Pero el test solo puede ver una
forma: un `Raise` léxicamente dentro del `body` de un `If` cuyo test sea `modo == "v1"`. Es ciega a
`sys.exit`, `os._exit`, y —lo importante— a cualquier salida enrutada por una llamada. Medí el caso
del helper: verde. Y es una aserción **sobre-amplia** en el otro sentido: cualquier `raise` legítimo
que se añada mañana a la rama `v1` (una excepción de dominio, un `raise ... from`) la pone roja sin
que haya salido nadie del proceso. Contrata la ausencia de una palabra clave, no un comportamiento.

**Cómo lo comprobé.** Ejecutado (`CM25`, VIVO sobre 7 ficheros de test incluidos los 5
contractuales).

**Qué haría falta.** Medir la propiedad, no la forma: envolver la invocación del CLI con un espía
que registre el orden real de `(salida del proceso, liberación del mutex)` —por ejemplo un
`mutex_sesion.sostenido` instrumentado— y afirmar que la salida es posterior. El AST puede quedarse
como guarda barata **además**, nunca en lugar de.

---

### `L1-05` — ALTO — F13 no contrata la emisión del evento, solo la pertenencia del nombre al set

**Qué.** `registrar_cierre_v1(...)` → `pass` en `main` no pone nada rojo.

**Dónde.** `scripts/abrir_caso.py:975` (la llamada), `tests/test_apertura_v1_cableado.py:19-22` y
`:25-43`, `tests/test_apertura_v1_e2e.py:118-128`.

**Por qué importa.** F13 dice «El evento final **se emite** con el estado real». Lo contratado es
(a) que `"apertura_v1_terminada" in intake_log.INTAKE_EVENTS` y (b) que `registrar_cierre_v1`, si se
la llama, escribe bien. Nadie contrata que `main` la llame — y el único test que atraviesa `main` la
sustituye por un no-op (`test_abrir_caso_modo_v1.py:134`). El docstring de la función dice que es
«el unico rastro DURABLE de la corrida: la pantalla se pierde, el `.jsonl` no»
(`scripts/abrir_caso.py:537-539`). Con `CM12`, ese único rastro durable desaparece y la apertura de
un expediente real no deja constancia forense.

**Cómo lo comprobé.** Ejecutado (`CM12`, VIVO).

**Qué haría falta.** La misma prueba de integración de `L1-01`, afirmando el evento leído del
`_intake_log.jsonl` del caso.

---

### `L1-06` — ALTO — F27 y F28 no contratan que `main` use el estado durable

**Qué.** Sustituir `estado_v1.abrir(...)` por un constructor en memoria y `estado_v1.cerrar(...)`
por `pass` deja todo verde: `_apertura_v1.json` no llega a existir nunca.

**Dónde.** `scripts/abrir_caso.py:967-968` (`abrir`) y `:971-974` (`cerrar`). Tests:
`tests/test_apertura_v1_estado.py` (los 7 llaman al módulo directamente con `tmp_path`).

**Por qué importa.** La spec §11 hace el `estado.json` obligatorio «desde la primera entrega», y el
docstring del módulo dice que sin él «reanudar tras un corte es una afirmación del autor y no una
propiedad del sistema» (`core/apertura_v1_estado.py:5-6`). Con `CM4` + `CM14`, la propiedad
desaparece por completo del producto y las 7 pruebas del módulo siguen verdes, porque prueban el
módulo, no el uso. Es la misma clase que `L1-05`: la pieza está construida y contratada; el que la
llame, no.

**Cómo lo comprobé.** Ejecutado (`CM4` y `CM14`, ambos VIVOS por separado y juntos).

**Qué haría falta.** Afirmar, tras una invocación real del CLI en `v1`, que
`00_Input/_apertura_v1.json` existe, que tiene `ronda_id`, y que tras una corrida completa tiene
`terminada` no nulo y las etapas.

---

### `L1-07` — ALTO — F28 promete «se dice en el informe» y solo se dice por `stderr`; `abrir` destruye acto seguido la evidencia

**Qué.** El aviso de ronda anterior sin cerrar va a `stderr` y no entra ni en
`ResultadoV1.pendientes` ni en el evento forense; y la línea siguiente sobrescribe el fichero que
lo probaba. El mutante `if False:` sobre la condición sobrevive.

**Dónde.** `scripts/abrir_caso.py:961-968`. Frontera F28 del §3. Test:
`tests/test_apertura_v1_estado.py:31-38`, que solo afirma `previa.sin_cerrar() is True`.

**Por qué importa.** F28 se enuncia «Una ronda anterior **sin cerrar** se detecta **y se dice en el
informe**». Lo que hay: se detecta (bien), se avisa con `err=True` (o sea, al canal que el propio
proyecto llama perdido), **no** se propaga al `ResultadoV1` —así que no aparece en `_informar_v1`,
que es lo que el operador llama «el informe», ni en `apertura_v1_terminada`— y en la línea 967
`estado_v1.abrir` reescribe `_apertura_v1.json` con una ronda nueva. No hay historial: `_escribir`
hace `os.replace` sobre el mismo path (`core/apertura_v1_estado.py:73-88`). Resultado: la única
constancia durable de que hubo una ronda muerta se borra en el mismo instante en que se descubre. Y
el mutante que apaga el aviso (`CM3`) no mata nada, así que el trozo de F28 que habla del informe no
está contratado en absoluto.

**Cómo lo comprobé.** Leído (`abrir` sobrescribe; el aviso no se propaga) + ejecutado (`CM3`, VIVO).

**Qué haría falta.** Que la ronda sin cerrar sea un `av1.Pendiente` del resultado —así entra en el
informe **y** en el evento por construcción— y un test que lo afirme sobre la salida del CLI.
Aparte: decidir si `abrir` puede pisar una ronda sin cerrar sin dejar rastro de ella.

---

### `L1-08` — ALTO — F16 no está contratada en su única milla que decide: `_intake_drive_ev` puede dejar de reenviar `force`

**Qué.** `pull_drive_ev(..., force=force)` → `force=False` en la costura sobrevive a toda la suite.

**Dónde.** `scripts/abrir_caso.py:151` (el reenvío), `core/intake_drive.py:206` (el único sitio donde
`force` decide algo). Frontera F16; mutante en `tests/_mutantes_plan5.py:153-159`.

**Por qué importa.** F16 dice «En V1 el pull se pide con `force=True`: **consulta remota real en
cada ronda**». Lo contratado es que `etapa_drive` pase `force=True` **a la costura** — tanto el test
unitario (`test_apertura_v1_etapas.py:57-66`) como el E2E doblan `_intake_drive_ev`, así que ninguno
llega a `pull_drive_ev`. El parámetro es nuevo en esta costura (el diff lo añade,
`DIFF.patch` líneas ~300-310) y `tests/test_custodia_destino_efectivo.py` la llama sin `force` en
sus tres tests. Así que la propiedad «se consulta Drive en cada ronda» descansa en una línea que
nadie afirma. Atenuante honesto: con `force=False` y `.pulled` presente, `pull_drive_ev` devuelve
`skipped=True` y **F6 lo convierte en `fallo`**, así que el fallo sería ruidoso (V1 quedaría
`bloqueado` en toda ronda posterior a la primera) y no silencioso. Pero el efecto es la rotura total
de la idempotencia de V1, y ninguna prueba lo detecta.

**Cómo lo comprobé.** Ejecutado (`CM13`, VIVO) + leído `core/intake_drive.py:199-230`.

**Qué haría falta.** Un test sobre `_intake_drive_ev` que doble `intake_drive.pull_drive_ev` y
afirme el `force` recibido. Es el análogo exacto de `test_f15_bis`, que el autor ya escribió para el
default de la etapa: falta el mismo para el reenvío del parámetro.

---

### `L1-09` — ALTO — `apply` no está contratada para propagar el status de la atomización: F10/F11/F12 no tienen entrada real

**Qué.** `return status_atomizacion` → `return None` en `scripts/sala_maquina.py:923` sobrevive.

**Dónde.** `scripts/sala_maquina.py:813` (se captura) y `:923` (se devuelve).
`scripts/abrir_caso.py:485-487` (`_correr` lo consume). Fronteras F10, F11, F12.

**Por qué importa.** F11 dice «Atomización `fallo` → etapa `fallo`», y el §24 D4 lo convierte en «V1
`bloqueado`». Los tres mutantes se aplican a `etapa_sala_maquina`, cuyos tests inyectan
`correr=lambda: "fallo"`; el E2E dobla `sala_maquina.apply`. Nadie prueba el eslabón. Con `CM17`,
una atomización fallida se reporta como **«OCR hecho; sin correo que atomizar»** (porque `None`
significa «no se ejecutó», `scripts/abrir_caso.py:519-521`) y V1 cierra
`preparado_con_pendientes`: la violación de D4 que F11 existe para impedir, con el mensaje más
tranquilizador posible. El control `CM18` prueba que el arnés no está mudo: la misma mutación en
`_atomizar_correo` mata dos de los tres tests nuevos del Task 5. Se contrató el productor del dato y
no su transporte.

**Cómo lo comprobé.** Ejecutado (`CM17` VIVO, `CM18` MUERTO con 2 rojos).

**Qué haría falta.** Un test de `sala_maquina.apply` que fije el status de `_atomizar_correo` y
afirme el valor devuelto por `apply`; o que `etapa_sala_maquina` no dependa del retorno.

---

### `L1-10` — ALTO — El cableado de `--hasta` no está contratado por ninguno de sus dos extremos

**Qué.** Quitar `hasta=hasta` de la llamada a `validar_modo` sobrevive; cambiar `hasta=hasta` por
`hasta=None` en la llamada a `secuencia_v1` sobrevive.

**Dónde.** `scripts/abrir_caso.py:816-820` (la puerta) y `:969-970` (la secuencia). Fronteras F4, F5
y F23.

**Por qué importa.** F23 dice «El vocabulario de `--hasta` se valida en `validar_modo`, **antes de
todo efecto**», y es la remediación de HA-06. Se contrata llamando a `validar_modo` directamente
(`test_apertura_v1_cableado.py:74-80`). Con `CM28`, `main` deja de pasarle el parámetro: un
`--hasta drve` pasa la puerta y revienta con `EtapaDesconocida` **después** de `ensure_case`, que es
el defecto de HA-06 restaurado íntegro. Con `CM9`, `--hasta drive` corre las tres etapas y el
operador no se entera: F4 («para después de esa etapa») queda contratada solo dentro de
`secuenciar`. Ningún test del repositorio invoca el CLI con `--hasta`; el flag es nuevo en este diff
y solo existe medido en funciones puras.

**Cómo lo comprobé.** Ejecutado (`CM9` y `CM28`, ambos VIVOS).

**Qué haría falta.** Dos invocaciones del CLI: una con `--hasta drve` (afirmando salida 1 y que
`ensure_case` **no** se llamó) y una con `--hasta drive` (afirmando que solo corrió la etapa de
Drive).

---

### `L1-11` — MEDIO — F8, F21 y F22 son, medidas, fronteras de «el primer expediente»

**Qué.** `for link in links:` → `for link in links[:1]:` en el bucle de puertas sobrevive.

**Dónde.** `scripts/abrir_caso.py:410-430`. Fixtures: `tests/test_apertura_v1_etapas.py:105-110`
(`_meta()` monta **un** link) y `tests/test_apertura_v1_e2e.py:29-41` (idem).

**Por qué importa.** El comentario del propio código enuncia la propiedad: «Las tres puertas de la
rama se comprueban **ANTES de pullar nada**: con dos expedientes vinculados, descubrir el segundo
invalido a mitad dejaria el primero ya escrito» (`scripts/abrir_caso.py:410-411`). Ese es el caso que
justifica el bucle previo, y es el único caso que ninguna fixture construye. Con `CM8`, un
`element` **judicial** en el segundo link pasa la puerta y se pulla el primero: F22 —«en V1 un
`element` judicial **aborta**», el cruce inverso del criterio 38, con la rama judicial declarada
bloqueada— deja de valer en cuanto hay más de un expediente. Y `sudespacho_expedientes` es una lista
en `_caso.md` precisamente porque puede tener varios. Nota: `CM7` (la agregación
`vacios == len(links)`) **sí** murió, así que la mitad de la lógica multi-link está cubierta y la
otra mitad no.

**Cómo lo comprobé.** Ejecutado (`CM8` VIVO, `CM7` MUERTO) + leído las dos fixtures.

**Qué haría falta.** Un caso con dos links donde el **segundo** sea judicial / fuera de vocabulario
/ sin `element`, afirmando `fallo` y **cero** llamadas al pull.

---

### `L1-12` — MEDIO — F27 se contrata con un espía sobre `os.replace`, y la propiedad que el código declara (el temporal en el mismo volumen) no tiene mutante

**Qué.** `tempfile.mkstemp(dir=str(f.parent), ...)` → `mkstemp(...)` sin `dir` sobrevive.

**Dónde.** `core/apertura_v1_estado.py:76`. Test: `tests/test_apertura_v1_estado.py:16-28`, que
monkeypatchea `est.os.replace` y afirma `reemplazos` no vacío.

**Por qué importa.** El docstring de `_escribir` declara la razón de ser del `dir=`: «El temporal va
al mismo directorio porque `os.replace` solo es atomico dentro del mismo sistema de ficheros»
(`core/apertura_v1_estado.py:70-71`). Con `CM6`, el temporal se crea en `%TEMP%` y —cuando el caso
vive en `G:` (Drive for Desktop) y `%TEMP%` en `C:`— `os.replace` deja de ser un rename atómico. El
test no puede verlo porque afirma que la **llamada ocurrió**, no que la escritura sea atómica: es la
aserción «se llamó» en vez de «el efecto pasó». Tampoco tienen mutante `fh.flush()`, `os.fsync`, ni
el `except BaseException` que borra el temporal. **SIN VERIFICAR** la consecuencia real en disco
cruzando volúmenes: no tengo dos sistemas de ficheros disponibles aquí. La supervivencia del
mutante sí está medida.

**Qué haría falta.** Un mutante y un test para el `dir=` (por ejemplo, afirmando que el temporal se
crea bajo `00_Input` observándolo con un `mkstemp` instrumentado), y algo para `fsync`.

---

### `L1-13` — MEDIO — El mutante F15 muere 5 de sus 6 veces por un error de montaje, no por su frontera

**Qué.** El arnés compara conjuntos de nodeids, nunca razones. Instrumentado, el mutante F15 mata
las cinco pruebas del E2E con `LocalWorkspaceMissing`, porque el `pull_drive_ev` real hace
`localizar(case_id)` y la fixture monta el caso en `tmp_path`, fuera de `CASOS_ROOT`.

**Dónde.** `tests/_mutantes_plan5.py:142-151` (los 6 nodeids declarados),
`tests/test_apertura_v1_e2e.py:22-42` (la fixture), `core/intake_drive.py:188-189` (`localizar`).

**Por qué importa.** El arnés imprime «MUERTO **por su frontera**», y para F15 eso es cierto solo de
`test_f15_bis`. Las otras cinco muertes son frágiles por la razón equivocada: si alguien hiciera la
fixture del E2E más fiel —registrando el caso en `CASOS_ROOT`, que es lo que hace la fixture
`casos_root` de `test_abrir_caso_modo_v1.py`— cinco de los seis rojos de F15 desaparecerían y el
arnés cantaría «MATA DE MENOS» sobre un mutante que sigue igual de mal. El número «6 rojos» mide la
fragilidad de la fixture, no la fuerza del contrato. En contraste, verifiqué que los rojos de F7,
F16 y F3 en el E2E **sí** mueren por su razón: afirman sobre `visto["element"]`, `visto["force"]` y
el estado.

**Cómo lo comprobé.** Ejecutado: `--tb=line` sobre el E2E con el mutante F15 (las cinco aserciones
pegadas arriba) y reproducción directa de `etapa_drive`, que devuelve
`fallo / LocalWorkspaceMissing`.

**Qué haría falta.** Que el arnés registre también el **mensaje** del rojo, o al menos que los
conjuntos declarados se limiten a los tests que afirman sobre la frontera. Lo segundo es lo que el
autor ya hizo con F7 (`tests/_mutantes_plan5.py:90-97`) por la razón correcta; F15 se quedó sin ese
pase.

---

### `L1-14` — MEDIO — La etapa de Drive puede pedir el pull en `dry-run` y la custodia no se registra

**Qué.** `dry_run=False` → `dry_run=True` en `etapa_drive` sobrevive.

**Dónde.** `scripts/abrir_caso.py:357`. Ningún doble del §3 espía `dry_run`, aunque todos lo
aceptan (`test_apertura_v1_etapas.py:26`, `:43`, `:61`; `test_apertura_v1_e2e.py:76`).

**Por qué importa.** F15 —la frontera en negrita del §3— dice que la etapa pasa por
`_intake_drive_ev` «que hashea, reconcilia y registra parciales». Con `dry_run=True` pasa por ella y
**no registra nada**: `_intake_generico` es quien emite el evento de custodia. Los bytes se copian
igual (el pull es real de todos modos, que es justo el argumento de H6-03 para prohibir `--dry-run`
en `v1`) y el ledger queda sin los hashes. Es la propiedad de F15 rota por el parámetro de al lado,
y el mismo doble que espía `force` habría podido espiar esto sin coste.

**Cómo lo comprobé.** Ejecutado (`CM23`, VIVO).

---

### `L1-15` — MEDIO — F24 se cierra a medias: el informe que el operador LEE no está contratado, y `_informar_v1` no tiene ninguna frontera

**Qué.** Iterar sobre `()` en lugar de `resultado.no_ejecutadas` en `_informar_v1` sobrevive; y
`"parada": resultado.parada` → `None` en el evento forense también.

**Dónde.** `scripts/abrir_caso.py:600-610` (`_informar_v1` entera, sin mutante ni test) y `:530`
(el campo `parada` del evento). Test del evento:
`tests/test_apertura_v1_cableado.py:41-43`, que afirma estado, pendientes y etapas — no la parada.

**Por qué importa.** F24 dice «Una parada pedida **enumera como pendientes** las etapas que no
corrieron», y lo contratado es que `ResultadoV1.pendientes` las lleve. Que el texto que el operador
lee las diga no lo contrata nada: `_informar_v1` es 11 líneas de producción con cero cobertura. Es
el modo de fallo de la aserción débil que el proyecto ya tiene medido: cuando la mitad útil del
arreglo es texto para un humano, no está verificado hasta que alguien lee ese texto. Y el campo
`parada` del evento —el rastro durable— puede mentir sin que nada muerda.

**Cómo lo comprobé.** Ejecutado (`CM10` y `CM11`, ambos VIVOS).

---

### `L1-16` — MEDIO — La sala de máquina puede correr sobre OTRO caso sin que nada muerda

**Qué.** `sala_maquina.apply(case_id=ident.case_id)` → `apply(case_id="NO_ES_ESTE_CASO")` sobrevive.

**Dónde.** `scripts/abrir_caso.py:494-496` (el `_correr` por defecto) y `:576-582` (las tres lambdas
de `secuencia_v1`). Doble del E2E: `tests/test_apertura_v1_e2e.py:88-90`, `_apply(case_id=None,
**kw)` — acepta cualquier cosa y no lo espía.

**Por qué importa.** El E2E lleva espías deliberados para `force` y `element` —y el comentario de
`visto` explica muy bien por qué (`test_apertura_v1_e2e.py:70-73`)— pero no para el `case_id` que
llega a la sala de máquina ni para el `folder_id`/`team_id` que `secuencia_v1` cablea en la lambda
de Drive. El autor escribió `test_f15_bis` exactamente para contratar el camino por defecto de una
etapa; no hay equivalente para las otras dos, ni para los argumentos que el secuenciador de
producción compone. Un `case_id` mal cableado haría OCR y escritura de derivados **en otro
expediente**, que es el radio de daño más alto de esta pieza.

**Cómo lo comprobé.** Ejecutado (`CM5`, VIVO).

---

### `L1-17` — MEDIO — El trinquete del censo abre un hueco nuevo que el propio diff introduce: `mkstemp`

**Qué.** `tempfile.mkstemp` crea un fichero real y **no** está en `PRIMITIVAS`, así que no cuenta en
el censo.

**Dónde.** `tests/test_escritura_censo.py:41-43` (`PRIMITIVAS`) y `core/apertura_v1_estado.py:76`.

**Por qué importa.** La cuenta cuadra —medido: `TOTAL 87`, `TECHO_CENSO 87`, con
`core/apertura_v1_estado.py` aportando 3 (`mkdir`, `replace`, `unlink`)— y la subida está declarada
con su razón, que es lo que la regla del trinquete pide. Lo que no cuadra es la cobertura: `grep -rn
"mkstemp"` sobre los 12 productores da **una sola aparición, la nueva**. Este diff introduce en el
write-set una forma de crear ficheros que el detector no ve, así que un segundo `mkstemp` en
cualquier productor no subiría el techo y el trinquete no mordería. Es el mismo defecto de clase que
el comentario del propio fichero describe («un techo inflado es un techo con hueco»,
`tests/test_escritura_censo.py:49-51`), esta vez por defecto y no por exceso. Ni `mkstemp` ni el
`fh.write(cuerpo)` del descriptor están contados.

**Cómo lo comprobé.** Ejecutado (censo por productor, salida pegada arriba) + `grep`.

---

### `L1-18` — BAJO — La etapa 1 de V1 siembra en `00_Input` un fichero que la etapa 3 de la misma ronda cuenta como documento

**Qué.** `_apertura_v1.json` no está en `_IGNORAR` y `plan()` lo enruta como `sin_soporte`.

**Dónde.** `core/sala_maquina.py:1173` (`_IGNORAR` es un conjunto de nombres explícitos),
`core/apertura_v1_estado.py:20,36`.

**Por qué importa.** Medido:

```
.json -> sin_soporte
plan([{'rel_path':'_apertura_v1.json', ...}]) -> [('_apertura_v1.json', 'sin_soporte', False)]
```

`skip=False`, así que cada ronda de V1 mete su propio fichero de control en `_cobertura.md` como
documento «a revisar». Es ruido auto-inflingido: la secuencia escribe el estado durable en la etapa
0 y en la etapa 3 lo inventaría como material del caso. Ninguna frontera lo cubre y el guard de
integridad de la sala (`_exigir_integridad`) sí lo verá.

**Qué haría falta.** Añadir `_apertura_v1.json` a `_IGNORAR` —o mejor, cambiar `_IGNORAR` por un
criterio (ficheros de protocolo por prefijo) para que el próximo fichero de control no repita el
paso.

---

### `L1-19` — BAJO — Dos escrituras ocurren después de que la exclusión se sepa perdida

**Qué.** Si `sala_maquina.apply` pierde el lease, lo traduce a `typer.Exit(2)`; `etapa_sala_maquina`
lo convierte en etapa `fallo`; y `main` sigue: escribe `_apertura_v1.json` y emite el evento
forense **antes** de que el `with` salga y `MutexPerdido` se levante.

**Dónde.** `scripts/sala_maquina.py:544-554` (traduce `MutexPerdido` a `Exit(2)`),
`scripts/abrir_caso.py:499-505` (lo captura como `fallo`), `:971-975` (las dos escrituras),
`core/casos/mutex_sesion.py:191-214` (el prestatario no último solo **anota**).

**Por qué importa.** Es de la misma familia que F25/HA-07 —«escribir cuando ya no se es titular»— y
ninguna de las 28 fronteras la nombra. El estado final que ve el operador sí es correcto
(`bloqueado`, salida 1, por `main:992-995`), así que el daño es acotado: dos ficheros de protocolo
escritos con otro proceso posiblemente dentro. **SIN VERIFICAR**: lo deduje de leer las tres capas y
no construí el escenario.

---

## Lo que aguanta

Con la evidencia, porque decir qué quedó cubierto es la otra mitad del trabajo.

1. **Los 28 mutantes se reproducen, 28/28, cada uno solo por su frontera** — ejecutado dos veces
   (una en corrida limpia, una tras restaurar el árbol). No hay ni un «MATA DE MENOS» ni un «MAL
   APUNTADO» **según la regla del arnés**. La objeción de `L1-13` es a la regla (compara conjuntos,
   no razones), no a la aritmética.
2. **La regla del arnés sí mide su propia medida, y el arreglo del `classname` es real.** Verificado
   leyendo `tests/_mutantes_plan5.py:243-253` y comprobando que mis propias corridas por JUnit XML
   necesitan la misma composición de nodeid. La lección de HA-09 está cerrada de verdad: la
   comparación de conjuntos habría cazado el F12 superviviente.
3. **La fixture del E2E la lee el lector real.** `test_la_fixture_es_legible_por_el_lector_real`
   (`test_apertura_v1_e2e.py:45-50`) es el guardarraíl de HA-10 y funciona: verifiqué que
   `read_case_meta` devuelve `fm["meta"]` (`core/casos/case_locator.py`) y que el `meta:` anidado de
   la fixture es lo que hace que la rama del CRM se ejercite de verdad. El E2E ya no puede pasar sin
   tocar el pull.
4. **Los espías de `force` y `element` muerden.** Comprobado que los rojos de F7 y F16 en el E2E
   mueren por sus aserciones sobre `visto`, no por accidente. El comentario que explica por qué las
   aserciones no van dentro del doble (`test_apertura_v1_e2e.py:70-73`) es correcto: `etapa_drive` y
   `etapa_crm` capturan `Exception`, así que un `assert` ahí se lo tragarían.
5. **Los cinco atributos que `traducir_pull_crm` lee por `getattr` existen de verdad.**
   `blocked_legacy_v1`, `documents_total_crm`, `documents_written`, `documents_failed` y `errors`
   son campos reales de `PullResultV2` (`core/sync_sudespacho.py:1309-1317`). No hay rama muerta por
   nombre mal escrito, que era el riesgo obvio de una tabla escrita sobre `getattr` con default.
6. **La etapa 3 no choca contra el mutex de `main`.** `mutex_sesion.sostenido` es reentrante por
   cuenta de prestatarios y la clave es `(raíz normalizada, W-code)`; `main` y
   `sala_maquina._bajo_mutex` usan ambos `raiz=None` y el mismo W-code, así que la etapa se **une**
   en vez de lanzar `CaseBusy`. Leído `core/casos/mutex_sesion.py:119-214` y
   `scripts/sala_maquina.py:521-537`. Era el fallo de producción más plausible y no está.
7. **`res.skipped` es una guarda deliberadamente inerte, y está bien puesta.** Verificado que
   `skipped=True` se devuelve en un único sitio (`core/intake_drive.py:206-230`), dentro de
   `if marker.exists() and not force`. Con `force=True` no puede ser cierto en producción: el propio
   código lo dice (`scripts/abrir_caso.py:368-369`). No es un filtro inerte que produzca un informe
   falso; es la red que hace **ruidoso** el defecto de `L1-08`. Lo único objetable es contarla entre
   las 28 fronteras: mide el camino inyectado.
8. **`previa.sin_cerrar()` no es inerte.** `abrir` escribe con `terminada=None` antes de correr y
   `cerrar` la rellena al final, así que ambos valores son alcanzables. (Lo que falla es lo que se
   hace con el `True`: `L1-07`.)
9. **`etapa_crm` comprueba las puertas antes de pullar, y la agregación `saltada` solo si todos**:
   `CM7` murió, así que esa mitad está contratada. Y `test_f9`, `test_f21`, `test_f22`, `test_f8`
   ponen trampas `pytest.fail` en el pull, que es la forma correcta de afirmar «no se llamó».
10. **El vocabulario de eventos y su doble aserto siguen midiendo lo que dicen.** La subida 33→34
    está declarada en los tres sitios y `test_los_veintiocho_de_antes_SIGUEN_estando` conserva su
    poder porque el nuevo va en su propio conjunto (`tests/test_intake_log_workspace.py:237-259`), en
    vez de cuadrarse por resta.
11. **El modo `libre` no cambia de comportamiento observable en lo que las pruebas cubren.** Los 66
    tests de `test_abrir_caso_cli.py` + `test_abrir_caso_modo_v1.py` van verdes con
    `--basetemp=../bt`, incluidos los de `--dry-run`, y `test_modo_libre_conserva_el_comportamiento`
    afirma la secuencia observable `["ensure_case","intake","crm"]` y el código de salida, no la
    ausencia de un texto. El `typer.Exit` del `--dry-run` sigue dentro del mutex y está **declarado**
    fuera de alcance con número de backlog (`scripts/abrir_caso.py:985-986`), lo cual es la forma
    honesta de dejarlo.
12. **La suite del repo está verde salvo dos rojos preexistentes y de entorno**
    (`test_session_close_no_pude_medir.py`, por la ausencia de `.venv/` en mi copia): idénticos con
    y sin mutantes, así que no los imputo al diff.

---

### Resumen de la lente

| Frontera | ¿Contratada? |
|---|---|
| F1–F5, F24 (secuenciador) | **Sí**, y en la capa correcta: son funciones puras. |
| F7–F12, F17–F22 (adaptadores) | **Sí** en la traducción; F8/F21/F22 solo para **un** link (`L1-11`). |
| F6 | Sí en el camino inyectado; **inerte en producción** por diseño (aguanta, con matiz). |
| F15 | Sí, por `test_f15_bis`. Los otros 5 rojos son de montaje (`L1-13`). |
| F16 | A medias: la costura→rclone no está contratada (`L1-08`). |
| F23 | A medias: la puerta sí, el cableado de `main` no (`L1-10`). |
| F13, F14, F27, F28 | Solo la función pura; el uso desde `main` **no** (`L1-03`, `L1-05`, `L1-06`, `L1-07`). |
| F25 | Solo la **forma** sintáctica (`L1-04`). |
| F26 | Contra **código muerto** (`L1-02`). |
| El cuerpo de `main`, `_informar_v1`, `apply`→status, `mkstemp` | **Sin frontera ninguna** (`L1-01`, `L1-09`, `L1-15`, `L1-17`). |

---

# LENTE 2 — guardas inertes y aserciones que no pueden fallar

# LENTE 2 — Guardas inertes y aserciones que no pueden fallar

Revisor adversarial. Objeto: `rB/head/` (solo lectura). Base: `rB/base/`. Ejecución en
`rB/lente2/wt` (copia de `head`, restaurada y verificada idéntica al terminar).

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`.

---

## Evidencia

**Baseline.** El conjunto contractual del Plan 5 más `test_abrir_caso_modo_v1.py`
corre **85/85 verde** sobre la copia intacta:

```
pytest tests/test_apertura_v1_{secuenciador,etapas,cableado,estado,e2e}.py \
       tests/test_abrir_caso_modo_v1.py -q  ->  85 passed
```

Todas las mutaciones de abajo se aplicaron sobre esa base y se revirtieron copiando el
fichero desde `head/`. Al cerrar: `diff -q head/scripts/abrir_caso.py
lente2/wt/scripts/abrir_caso.py` → idénticos.

**Sondas ejecutadas** (en `rB/lente2/probe{1..6}.py`):

| Sonda | Qué mide | Resultado |
|---|---|---|
| `probe1` | `_pytest.outcomes.Failed.__mro__`; `traducir_pull_crm` con `PullResultV2` reales | `Failed` deriva de `BaseException` (NO de `Exception`). Gestor vacío real → `fallo`. Doc fallido real → `fallo`. Gestor vacío *de test* (`errors=[]`) → `saltada`. |
| `probe2` | `pull_drive_ev` con `.pulled` presente, `force=False` vs `force=True` | `force=False → skipped=True`; `force=True → skipped=False` |
| `probe3` | `pull_drive_ev` con `rclone rc=3`, y `etapa_drive` completa por el camino de producción | `pull_drive_ev` **lanza** `DriveIntakeError`; `etapa_drive → fallo` con detalle `DriveIntakeError: …`, nunca por la rama `res.errors` |
| `probe4` | `secuencia_v1` con un `PullResultV2` de gestor vacío tal como lo construye `sync_sudespacho` | `estado=bloqueado`, `exit=1`, `etapas=[(drive,hecha),(crm,fallo)]`, `no_ejecutadas=('sala_maquina',)`, OCR **no corrió** |
| `probe5` | `read_case_meta` vs el lector de `pull_all`/`case_status` sobre el layout que mantiene `_atomic_write_caso_md` | el lector de `pull_all` ve el expediente; `read_case_meta` ve `None`; `etapa_crm → saltada` + `crm_sin_expediente` |
| `probe6` | ¿`etapa_crm` se traga un `pytest.fail` de su doble? | **PROPAGA** `Failed`: la trampa sí puede fallar el test |

**Mutaciones ejecutadas** (suite contractual completa, 85 tests, por fichero):

| # | Mutación | Rojos |
|---|---|---|
| M1 | producción de `secuencia_v1` = `[crm, drive]` (sin `sala_maquina`) | `test_apertura_v1_cableado.py` **10/10 verde**; solo el e2e cae (5 rojos) |
| M2 | `if fallidos:` → `if False:` **y** `if …documents_total_crm… == 0:` → `if False:` | exactamente 2 rojos: `test_f17_f20…[kw2-…]` y `…[kw3-…]` |
| M3 | `if previa is not None and previa.sin_cerrar():` → `if False:` (en `main`) | **0 rojos** |
| M4 | `estado_v1.cerrar(...)` suprimido de `main` | **0 rojos** |
| M5 | `registrar_cierre_v1(case_dir, ident, resultado_v1)` suprimido de `main` | **0 rojos** |

**Fuentes leídas** (no doy nada por bueno de segunda mano):
`head/core/apertura_v1.py`, `head/core/apertura_v1_estado.py`,
`head/scripts/abrir_caso.py`, `head/core/intake_drive.py:105-345`,
`head/core/sync_sudespacho.py:1290-1600`, `head/core/case_manager.py:50-230,
650-670, 1195-1390`, `head/core/casos/case_locator.py:198-224`,
`head/scripts/sala_maquina.py:413-455, 578-650, 785-925`,
`head/scripts/sync_sudespacho.py:140-260, 325-360`, y los seis ficheros de test del
diff más `tests/_mutantes_plan5.py`.

---

## Hallazgos

### L2-01 — CRÍTICO. Dos de las cinco ramas de `traducir_pull_crm` son inalcanzables, y la conducta real es la CONTRARIA a la diseñada

**Qué.** `scripts/abrir_caso.py:399` (`if fallidos:`) y `:405`
(`if int(getattr(res, "documents_total_crm", 0) or 0) == 0:`) están **detrás** de
`:396` (`if errores:`). En `core/sync_sudespacho.py` esos dos estados nunca llegan con
`errors` vacío:

- `:1546-1547` — todo incremento de `documents_failed` va **inmediatamente después** de
  `result.errors.append(f"download doc {info.doc_id}: {exc}")`. Es el **único** sitio del
  módulo que incrementa el contador.
- `:1454-1460` — `result.documents_total_crm = len(docs)`; y a continuación
  `if not docs: result.errors.append("El Gestor Documental del expediente … está vacío …")`.

Por tanto: `documents_failed > 0 ⇒ errores ≠ []` y `documents_total_crm == 0 ⇒ errores ≠ []`.
Las dos ramas están muertas, y con ellas los pendientes `crm_documentos_fallidos` y
`crm_gestor_vacio`. Colateral del mismo origen: el ternario de `:483`
(`estado = "saltada" if vacios == len(links) else "hecha"`) también es inerte, porque
`vacios` solo se incrementa cuando `traducir_pull_crm` devuelve `"saltada"` — es decir,
nunca con `links` no vacío.

**Dónde.** `scripts/abrir_caso.py:396, 399, 405, 483`;
`core/sync_sudespacho.py:1454-1460, 1546-1547`.

**Por qué importa** — y esto es lo que lo hace crítico, no cosmético. No es solo código
muerto: la conducta de producción es la **inversa** de la que el diff documenta. `probe4`,
con el `PullResultV2` que `pull_expediente_v2` construye literalmente para un gestor vacío:

```
estado V1     : bloqueado
exit code     : 1
etapas        : [('drive', 'hecha'), ('crm', 'fallo')]
no_ejecutadas : ('sala_maquina',)
OCR corrio?   : False
detalle crm   : 648: el pull devolvio errores: ["El Gestor Documental del expediente 648
                está vacío (o el elemento 'extrajudiciales' no es el correcto)."]
```

Un expediente CRM **ya registrado y sin documentos en su gestor** —situación de rutina en
el escenario mismo de V1, donde «el alta CRM es de V2» y el expediente puede llevar
semanas creado y vacío— **bloquea la apertura entera**: exit 1 y la sala de máquina (el
OCR, la etapa caro) no llega a arrancar. El comentario del código dice lo contrario:
«Vacio CONFIRMADO, que no es lo mismo que un error: el CRM contesto y no hay nada» y «No
es un fallo; es que no hay nada». Nada de eso ocurre.

Lo mismo con un solo documento fallido: diseñado como `hecha` + pendiente
(«`00_Input/05_CRM` esta incompleto»), en producción es `fallo → bloqueado`. Con una
`PHPSESSID` que caduca a mitad de un pull de 40 documentos —el gotcha nº 1 de este repo—
el resultado real es bloqueo, no un pendiente.

**Cómo lo comprobé.** `probe1` y `probe4` construyen los resultados **con la clase real**
`PullResultV2` y los rellenan exactamente como lo hace `sync_sudespacho`; los dos dan
`fallo`. El mismo `probe1` muestra que el estado que usan los tests
(`documents_total_crm=0` con `errors=[]`) sí da `saltada`: es decir, **el único input que
alcanza la rama es uno que producción no puede fabricar**. La mutación M2 lo cierra: al
suprimir las dos ramas, los únicos rojos son los dos casos parametrizados de
`test_f17_f20_el_resultado_del_pull_gobierna_la_etapa[kw2-…]` y `[kw3-…]`, cuyo doble es
`_Res(**kw)` (`tests/test_apertura_v1_etapas.py:113-119`), con `errors` por defecto `[]`.
Nada más en las 85 pruebas —el e2e incluido— defiende esas ramas.

Y el arnés de mutación lo certifica en falso: `tests/_mutantes_plan5.py` declara F19 y F20
«MUERTO por su frontera», con un solo nodeid cada uno — precisamente esos dos. Un mutante
muerto por un input imposible no prueba la frontera; prueba que el test existe.

**Qué haría falta.** Decidir cuál de las dos verdades vale y hacer que solo haya una:
(a) si un gestor vacío es `saltada`, `traducir_pull_crm` tiene que reconocer ese caso
**antes** de `if errores:` —por el texto no, por la señal: `documents_total_crm == 0` y
ningún error distinto del de vacío—, o `pull_expediente_v2` tiene que dejar de meterlo en
`errors`; (b) si un doc fallido es `hecha` con pendiente, el orden de las dos primeras
ramas tiene que invertirse para `documents_failed`. Y en cualquier caso los tests de esas
ramas deben construirse **desde `PullResultV2` rellenado como lo rellena el productor**, no
desde un doble que puede tener `errors=[]`. Mientras el productor y el traductor no se
prueben juntos, esta clase de defecto vuelve.

---

### L2-02 — MEDIO/ALTO. El cableado del estado durable y del evento forense en `main` no está protegido por nada: se puede suprimir entero y la suite sigue en 85/85

**Qué.** Tres mutaciones independientes sobre el cuerpo de `main`, cada una de ellas
destructiva de la propiedad que el diff declara, dejan la suite **completamente verde**:

- M3: `scripts/abrir_caso.py:962`, `if previa is not None and previa.sin_cerrar():` → `if False:` → **0 rojos**.
- M4: suprimir `estado_v1.cerrar(...)` (`:971-974`) → **0 rojos**. Con eso **toda** ronda
  queda «sin cerrar» en disco para siempre, que es exactamente el fallo que
  `core/apertura_v1_estado.py` existe para detectar: «lo que da es que una ronda muerta a
  mitad se DETECTE, en vez de que la siguiente corrida trate su salida como buena».
- M5: suprimir `registrar_cierre_v1(case_dir, ident, resultado_v1)` (`:975`) → **0 rojos**.
  Es la llamada que el propio docstring llama «el unico rastro DURABLE de la corrida: la
  pantalla se pierde, el `.jsonl` no», y por la que `TECHO_CENSO` subió de 83 a 87.

**Dónde.** `scripts/abrir_caso.py:958-975`. Los tests que existen
(`tests/test_apertura_v1_estado.py:31-47`) prueban el método puro `RondaV1.sin_cerrar()` y
las funciones `abrir`/`cerrar` del módulo; ninguno prueba que `main` las llame.
`tests/test_abrir_caso_modo_v1.py:132` monkeypatchea `registrar_cierre_v1` a un no-op y
**no afirma que se haya llamado** (a diferencia de `secuencia_v1`, donde sí puso el
`assert "secuencia" in llamadas`).

**Por qué importa.** El mutante F28 del arnés (`sin_cerrar → return False`) muere por
`test_f28`, en el módulo. Eso certifica el **método**, no la **guarda**. La distinción es la
de siempre en este repo: la pieza está construida y la costura no está probada. Aquí el
coste concreto es que la propiedad «reanudar tras un corte» —que la spec §11 hace
obligatoria «desde la primera entrega»— puede desaparecer en un refactor sin que un solo
test lo note.

Añado un segundo problema de la misma guarda, más de fondo. El aviso dice «esta corrida no
da por buena su salida», y **ningún código implementa eso**: no se re-ejecuta nada, no se
invalida nada, y acto seguido `estado_v1.abrir` (`:968`) sobrescribe el fichero con
`os.replace`, **destruyendo el único registro de la ronda muerta**. La afirmación resulta
cierta solo por accidente (Drive va con `force=True` y el pull del CRM es idempotente por
hash), no porque la guarda haga nada. Y el aviso va únicamente a `stderr`: no hay evento en
`_intake_log.jsonl`, así que si el operador no lee esa línea el hecho se pierde para
siempre — en la pieza cuyo propósito declarado es precisamente que no se pierda.

**Cómo lo comprobé.** Mutaciones M3, M4, M5 arriba, cada una sobre la copia intacta y con
la suite contractual completa. Lectura de `core/apertura_v1_estado.py:91-96` para confirmar
que `abrir` escribe incondicionalmente vía `_escribir` → `os.replace`.

**Qué haría falta.** Un test de `main` en modo `v1` (el runner ya está montado en
`test_abrir_caso_modo_v1.py`) que: (1) con un `_apertura_v1.json` previo sin `terminada`,
afirme que el aviso sale; (2) tras una corrida, afirme que el fichero en disco tiene
`terminada`, `estado` y `etapas`; (3) afirme que `apertura_v1_terminada` está en el
`.jsonl`. Y, si el aviso pretende significar algo, dejar constancia durable de la ronda
abandonada antes de sobrescribirla.

---

### L2-03 — MEDIO. Las tres condiciones de `etapa_drive` sobre el resultado son inertes; y el mensaje que un operador verá ante un `rclone` roto no lo afirma ningún test nuevo

**Qué.** Las tres:

- `:366` `if res.skipped:` — **inerte**. `core/intake_drive.py:206` es
  `if marker.exists() and not force:`, y es el único retorno con `skipped=True` (`:228`);
  el otro retorno lo fija a `False` (`:332`). `etapa_drive` pide siempre `force=True`
  (`:359`) y `_intake_drive_ev` lo propaga íntegro a `pull_drive_ev` (`:151`).
- `:362` `if res.errors or res.rclone_returncode != 0:` — **inerte también, y esto el diff
  no lo dice**. En `pull_drive_ev`, todo camino con `returncode != 0` appendea a `errors`
  (`:291, 294, 299`) y el final es `if errors: raise DriveIntakeError(result_obj)` (`:340`);
  `_intake_drive_ev` **relanza** esa excepción (`:186`). Un `DriveIntakeResult` *devuelto*
  siempre trae `errors == []` y `rclone_returncode == 0`.

**Dónde.** `scripts/abrir_caso.py:362, 366`; `core/intake_drive.py:206, 228, 291-340`;
`scripts/abrir_caso.py:151, 186`.

**Por qué importa.** No es dañino —el camino real cae en `except Exception` (`:360`) y
produce `fallo` igualmente— pero tres tests anuncian cobertura que no es:
`test_f6_un_skipped_en_v1_es_fallo…`, `test_drive_con_errores_es_fallo` y
`test_drive_con_returncode_no_cero_es_fallo` (`tests/test_apertura_v1_etapas.py:69-88`)
construyen `_drive_result(skipped=True)` / `(errors=[…])` / `(rclone_returncode=3)`, tres
estados que el camino de producción no puede devolver. Y el mutante F6 del arnés muere solo
por el primero de ellos: otra certificación emitida por un input imposible.

El hueco real que eso tapa: el mensaje que el operador **sí** verá cuando `rclone` falle es
`DriveIntakeError: pull_drive_ev falló para 'C': rclone exit 3: quota exceeded`
(`probe3`), y ese camino —con su registro de custodia de los bytes parciales, que es lo que
R15/H15-06 compró— no lo ejercita ningún test del diff.
`test_drive_que_revienta_es_fallo_y_no_propaga` usa un `RuntimeError` genérico.

Sobre `skipped` en concreto: el comentario lo declara red de seguridad contra que «el
marcador `.pulled` volvio al camino». Es una red defendible en principio, pero hoy solo
podría dispararse si alguien rompiera la propagación de `force` — y **eso ya lo cubre el
mutante F16**, con dos tests reales. La red, tal como está, no puede añadir información: en
el mundo donde `force` se propaga es inalcanzable, y en el mundo donde no se propaga F16 ya
está rojo.

**Cómo lo comprobé.** `probe2` (force=False → `skipped=True`; force=True → `skipped=False`,
con `.pulled` presente y válido en los dos casos) y `probe3` (rc=3 → `DriveIntakeError`,
`etapa_drive → fallo` con el detalle de la excepción).

**Qué haría falta.** Un test que llame a `etapa_drive` con un doble que lance
`intake_drive.DriveIntakeError` y afirme el detalle y el `fallo` — ése es el camino que
existe. Y, si `skipped` se conserva, decir en el comentario que hoy es inalcanzable y que
la propiedad que de verdad la sostiene es F16, en vez de describirla como si pudiera
dispararse.

---

### L2-04 — MEDIO. `traducir_fallo_de_mutex` no tiene ningún llamador de producción: `main` duplica su lógica inline, y dos tests certifican el código muerto

**Qué.** `scripts/abrir_caso.py:557` define `traducir_fallo_de_mutex(fn)`. `git grep` en
todo el árbol da tres apariciones: la definición y dos usos, ambos en
`tests/test_apertura_v1_cableado.py:138, 144`. **Ningún llamador de producción.** `main`
resuelve lo mismo con su propio `try/except (CaseBusy, MutexPerdido)` en `:977-980`.

**Dónde.** `scripts/abrir_caso.py:557-568` (definición) vs `:977-980` (la copia que sí
corre); `tests/test_apertura_v1_cableado.py:132-146`.

**Por qué importa.** `test_f26_case_busy_se_traduce_a_bloqueado_y_no_a_una_traza` lleva un
nombre que describe una propiedad del **comando**, y prueba una función que el comando no
usa. El mutante F26 del arnés muta la función muerta y muere por ese test: el arnés dice
«MUERTO por su frontera» sobre una frontera que no está en el camino. La consecuencia
práctica es la de siempre con dos copias: quien arregle el helper creyendo que arregla la
conducta no cambiará nada, y el `except` de `main` —que además hace dos cosas más, echar a
`stderr` y traducir a código de salida— no tiene test propio.

**Cómo lo comprobé.** `grep -rn "traducir_fallo_de_mutex" --include=*.py .` sobre `head`.

**Qué haría falta.** O `main` la usa (y entonces el test vale), o se borra y el test se
reescribe sobre `main` con el runner. Dejar las dos es garantizar que divergen.

---

### L2-05 — MEDIO/BAJO. `etapa_crm` lee el espejo `meta` del `_caso.md`; todos los demás lectores del mismo hecho leen la lista de nivel superior, que es la única que mantienen los mutadores

**Qué.** `etapa_crm` obtiene los links por `case_locator.read_case_meta`, que devuelve
**`fm["meta"]`** y no el frontmatter (`core/casos/case_locator.py:222-223`). El
`_caso.md` guarda el mismo hecho **dos veces**: `fm["sudespacho_expedientes"]` y
`fm["meta"]["sudespacho_expedientes"]` (`core/case_manager.py:145-155`). De los escritores:

- `register_expediente` (`:159-215`) escribe **las dos** copias, vía `_write_case_index`.
- `update_pull_state` (`:1296-1385`) escribe **solo la de nivel superior**, y
  `_atomic_write_caso_md` (`:1195-1240`) no reconcilia: lo único que toca de `meta` es
  `actualizado_en` (`:1233-1234`).

Y de los lectores, `etapa_crm` es el único que lee el espejo:
`scripts/sync_sudespacho.py:339` (`pull_all`), `core/case_manager.py:662` (`case_status`)
y `read_pull_state`/`update_pull_state` (`:1291, 1343`) leen todos el nivel superior.

**Dónde.** `scripts/abrir_caso.py:433-435` (`links = list(meta.get("sudespacho_expedientes") or [])`
y `if not links:`); `core/casos/case_locator.py:222`; `core/case_manager.py:1233-1234`.

**Por qué importa.** `if not links:` no es inerte, pero puede tener el valor **equivocado**
en la dirección peligrosa. `probe5`, sobre un `_caso.md` con el layout que mantiene
`_atomic_write_caso_md`:

```
lector de pull_all / case_status ve: [{'id': '648', 'element': 'extrajudiciales', …}]
read_case_meta (lector de etapa_crm) ve: None
etapa_crm -> saltada | sin expediente CRM registrado en _caso.md | ['crm_sin_expediente']
```

Es decir: V1 informa `saltada`, con el pendiente que dice «El caso no tiene expediente CRM
vinculado … El alta CRM es de V2», termina `preparado_con_pendientes` y sale **0** — sobre
un caso que sí tiene expediente y cuyo `05_CRM` no se ha tocado. Un verde sobre una fase
que no corrió, que es el modo de fallo que toda esta pieza intenta cerrar. Y el propio
autor lo tropezó: el docstring de la fixture del e2e
(`tests/test_apertura_v1_e2e.py:24-26`) cuenta que la rev. 1 escribía las claves «en el
nivel superior, el lector devolvia `{}` y el E2E pasaba en verde SIN tocar el CRM». La
fixture se arregló; la asimetría del lector, no.

**SIN VERIFICAR.** No conseguí exhibir una **secuencia de producción** que deje el espejo
`meta` sin la entrada: el único llamador de `update_pull_state`
(`core/sync_sudespacho.py:1639`) va siempre precedido por `register_expediente` en los
caminos que revisé (`scripts/sync_sudespacho.py:170, 251`; `streamlit_app.py:1071, 2282`),
y `register_expediente` reconstruye ambas copias. El riesgo es por tanto **estructural y
latente**, no demostrado en vivo: basta un `_caso.md` editado a mano, un caso heredado, o
un futuro escritor que use el mutador atómico, y el fallo es silencioso.

**Qué haría falta.** Que `etapa_crm` lea el mismo sitio que lee `pull_all` (el nivel
superior, con `meta` como respaldo), o que `_atomic_write_caso_md` reconcilie el espejo. Y
un test que escriba el `_caso.md` con la lista **solo** en el nivel superior y exija que
`etapa_crm` **no** diga `saltada`: hoy ese caso pasa en verde diciendo que no hay
expediente.

---

### L2-06 — BAJO. `test_una_corrida_completa_toca_TODAS_las_fases_de_v1` es tautológico: construye la lista y afirma el orden que acaba de construir

**Qué.** `tests/test_apertura_v1_cableado.py:53-60` pasa
`etapas=[_fake(n, visto) for n in cli.ETAPAS_V1]` y luego afirma
`visto == list(cli.ETAPAS_V1)`. Como `secuenciar` recorre la lista que recibe en el orden
en que la recibe, la aserción es verdadera por construcción, para cualquier contenido de
`ETAPAS_V1` y **con independencia de lo que `secuencia_v1` construya en producción** (la
rama `etapas is None`, `scripts/abrir_caso.py:585-591`).

**Dónde.** `tests/test_apertura_v1_cableado.py:53-60`.

**Por qué importa.** El docstring dice «El criterio que el bloque 4 del §21.5 de la spec
pide literalmente». No lo comprueba. Mutación M1: dejé la producción en
`[crm, drive]` —reordenada **y sin la etapa de la sala de máquina**— y el fichero entero
siguió **10/10 verde**. Los cinco rojos salieron todos del e2e. La propiedad, por tanto,
**sí está cubierta**, pero por otro fichero: la severidad es baja y el problema es de
etiqueta, no de hueco. Lo apunto porque una etiqueta falsa en un test es exactamente lo que
hace que la próxima vez nadie escriba el e2e.

**Cómo lo comprobé.** M1 (arriba), sobre la copia intacta, con los dos ficheros corridos
por separado.

**Qué haría falta.** O afirmar sobre el camino por defecto (sin `etapas=`, como hace el
e2e), o rebajar el docstring a lo que el test hace: comprobar que `secuenciar` no se salta
etapas de una lista dada.

---

### L2-07 — BAJO. El `typer.Exit` con código 0 de `etapa_sala_maquina` es inalcanzable, y su traducción —si algún día se alcanzara— sería una mentira

**Qué.** `scripts/abrir_caso.py:504-510`: al capturar `typer.Exit`, si
`exit_code` es 0 se hace `status = None`, que cae en la salida
`"OCR hecho; sin correo que atomizar"` con estado `hecha` (`:522-525`). En
`scripts/sala_maquina.py` **no existe ningún `typer.Exit(0)`**: los 16 `raise typer.Exit`
son de código 1, 2 o 3.

**Dónde.** `scripts/abrir_caso.py:505-510`; `scripts/sala_maquina.py:252, 321, 434, 438,
454, 481, 488, 493, 501, 543, 554, 565, 804, 822, 845, 981`.

**Por qué importa.** Doble. Primero, la rama es inerte hoy. Segundo, y peor: si mañana
alguien añade una salida limpia y temprana a `apply` —un `--dry-run`, un preflight que
decide que no hay nada que hacer—, esta traducción informará `hecha` + «sin correo que
atomizar» sobre una corrida en la que el **OCR no se ejecutó**. El `status is None` de
`_atomizar_correo` significa «no había correo»; el `status = None` de esta rama significa
«el motor entero se fue»; y los dos desembocan en la misma frase. Y su test,
`test_un_typer_exit_cero_no_es_fallo` (`tests/test_apertura_v1_etapas.py:231-238`), fija
ese comportamiento como el correcto.

**Cómo lo comprobé.** `grep -n "typer.Exit" scripts/sala_maquina.py` (ningún 0) y lectura
de `apply` (`:785-925`): un único `return`, al final del `with`; ningún `return` temprano
que pueda devolver `None` por otra vía.

**Qué haría falta.** Distinguir los dos «None»: un `Exit(0)` debería ser, como mínimo, un
`hecha` con pendiente («la sala de máquina salió antes de procesar») o un `saltada` con
razón declarada — nunca la misma frase que «no había correo».

---

### L2-08 — INFORMATIVO. Dos condiciones inalcanzables que están BIEN, y por qué

Las anoto para que no se confundan con las de arriba, y porque una de ellas es el modelo
de cómo debería estar tratado el resto.

- `core/apertura_v1.py:51`, `return EstadoV1.COMPLETO`: inalcanzable **desde `secuenciar`**,
  porque `:105` siembra `PENDIENTE_FUENTES_V3` en la lista. Está **declarado** en el
  docstring del módulo y en el de la función («`completo` es alcanzable aqui a proposito:
  quien lo impide en V1 es el pendiente permanente, no esta funcion»), `estado_de` es una
  función pura con contrato propio, y hay test para las dos lecturas
  (`test_sin_pendientes_y_sin_fallo_seria_completo` y
  `test_f3_el_pendiente_de_fuentes_v3_es_permanente…`). Así se hace.
- `core/apertura_v1.py:100-102`, `EtapaDesconocida`: inalcanzable desde la CLI, porque
  `validar_modo` ya filtra `hasta` contra `ETAPAS_V1` (`scripts/abrir_caso.py:725`). Es
  doble validación deliberada de una función de `core` que no depende del entrypoint, y el
  riesgo que tendría —que `ETAPAS_V1` y los nombres de la lista de producción divergieran—
  **sí está cubierto**, por `tests/test_apertura_v1_e2e.py:109`, que afirma sobre el camino
  por defecto.

---

## Lo que aguanta

Lo comprobé con el mismo criterio, y son puntos donde la sospecha de mi lente resultó
infundada:

1. **Los `pytest.fail` dentro de los dobles NO se los traga el sujeto.**
   `_pytest.outcomes.Failed` deriva de `OutcomeException(BaseException)`, no de
   `Exception` (`probe1`), así que atraviesa los `except Exception` de `etapa_drive`,
   `etapa_crm`, `etapa_sala_maquina` y `_atomizar_correo`. `probe6` lo mide en directo
   sobre `etapa_crm`: **PROPAGA `Failed`**. Las trampas de
   `tests/test_apertura_v1_etapas.py:137, 146, 156, 164, 197`,
   `tests/test_abrir_caso_modo_v1.py:135` y
   `tests/test_sala_maquina_cableado_atomize.py:474` son aserciones que **sí** pueden
   fallar. Y el diff ya había razonado esta trampa correctamente en el comentario de
   `tests/test_apertura_v1_e2e.py:69-74`, prefiriendo espiar y afirmar fuera del doble.

2. **El e2e prueba el camino por defecto, no las etapas dobladas.** Dobla solo los tres
   límites (`_intake_drive_ev`, `pull_expediente_v2`, `sala_maquina.apply`) y afirma sobre
   lo que vieron: `force == [True]` y `element == ["extrajudiciales"]`. La mutación M1
   (producción sin `sala_maquina`) lo pone rojo en cinco tests. Es el fichero que sostiene
   de verdad el orden y la propagación de `force`.

3. **Las dos guardas de vocabulario de `element` son alcanzables.**
   `el not in ELEMENTS_CRM`: `scripts/sync_sudespacho.py:145` expone
   `--element` sin validar y `:167` solo rellena el default con `or`, así que
   `register_expediente` puede escribir cualquier cadena en `_caso.md`.
   `el == _ELEMENT_JUDICIAL`: `scripts/sync_sudespacho.py:229` lo tiene como default
   explícito de `--element`, y `streamlit_app.py:1071, 2282` también registran. No son
   inertes.
   *(Matiz honesto sobre la tercera, `:448` `if not el:` — no encontré ningún escritor de
   producción que omita `element`: `register_expediente` siempre lo pone y
   `update_pull_state` lo **exige** al crear entrada, `core/case_manager.py:1354-1359`. Su
   única vía es un `_caso.md` editado a mano o heredado. La dejo como red de bajo valor,
   no como guarda inerte: en este repo el `_caso.md` es un índice que se edita.)*

4. **Los tres `status` de atomización se producen de verdad.**
   `scripts/sala_maquina.py:604` (`None`), `:614` (`"fallo"` por excepción del motor) y
   `:618` (`"fallo"` si no publicó / `"parcial"` si hubo errores / `"ok"`) cubren los cuatro
   valores que `etapa_sala_maquina` distingue. Ninguna de esas tres condiciones es inerte.

5. **`apply` tiene un único `return`.** Verificado sobre `:785-925`: solo
   `return status_atomizacion` y tres `raise typer.Exit(2)`. Así que `status is None` en
   `etapa_sala_maquina` significa inequívocamente «no se atomizó», y no «apply se fue por
   otra puerta». Es la premisa que hace correcto el `if status is None` de `:523`.

6. **El centinela `OptionInfo` no envenena nada.** `etapa_sala_maquina` llama a
   `sala_maquina.apply(case_id=…)`, dejando `case_dir` y `solo` con sus defaults de
   `typer.Option`, que son objetos **truthy**. Sospeché un filtro inerte por centinela
   truthy —`if case_dir:` tomando la rama equivocada— y no lo es:
   `scripts/sala_maquina.py:430` normaliza con `_arg_o_none(case_dir)` antes de decidir, y
   `:787` hace `list(solo) if isinstance(solo, list) else []`. Las dos puertas están
   cerradas.

7. **La aserción del secuenciador sobre el orden no es tautológica.**
   `tests/test_apertura_v1_secuenciador.py:51-56` inyecta `["a","b","c"]` y afirma el
   recorrido: es el contrato de `secuenciar`, con nombres que no vienen de ninguna
   constante de producción. A diferencia de L2-06, ahí no hay circularidad.

---

# LENTE 3 — el cuerpo de `main` y la no-regresion del modo `libre`

# LENTE 3 — El cuerpo de `main` y la no-regresión del modo `libre`

Revisor adversarial. Objeto en solo lectura: `Temp/rB/head/` contra `Temp/rB/base/`.
Trabajo, arneses y volcados en `Temp/rB/lente3/`. Nada escrito en el objeto.

---

## Evidencia

### Lo que leí entero

- `head/scripts/abrir_caso.py` y `base/scripts/abrir_caso.py` (diff completo, 1005 vs 683 líneas).
- `head/core/casos/mutex_sesion.py` (215 líneas, entero).
- `head/core/casos/case_mutex.py:578-659` (`tomado` y su `finally`).
- `head/core/apertura_v1.py:19-136` (`EstadoV1`, `estado_de`, `secuenciar`).
- `head/core/apertura_v1_estado.py:1-104` (`leer`, `_escribir`, `abrir`, `cerrar`).
- `head/core/casos/workspace_model.py:109`, `:273-320` (jerarquía de `CaseBusy`/`MutexPerdido`).
- `head/scripts/sala_maquina.py:506-554`, `:785-800` (`_bajo_mutex`, `apply`).
- `head/tests/test_apertura_v1_cableado.py`, `test_abrir_caso_modo_v1.py`,
  `test_entrypoints_mutex.py`, `tests/_mutantes_plan5.py` (el arnés del autor, 28 mutantes).
- `head/docs/MEJORAS_FUTURAS.md` §142.

**Declaración de contaminación.** Un `grep -rn -- "--hasta"` sobre el árbol devolvió tres
líneas de `docs/superpowers/specs/2026-09-03-apertura-v1-plan5-rA-adversarial-review.md`,
que el encargo me prohíbe leer. **No abrí el fichero y no uso su contenido.** Todos los
hallazgos de abajo se alcanzaron antes de ese grep, y cada uno lleva su propia medición.
Tampoco abrí el §5 del plan de cableado.

### Lo que ejecuté

Intérprete `pythoncore-3.14-64`, `--basetemp` corto (`C:\t\...`).

**Base verde acotada.** 113 tests en los 6 ficheros que tocan este entrypoint
(`test_apertura_v1_cableado`, `test_abrir_caso_modo_v1`, `test_apertura_v1_e2e`,
`test_apertura_v1_etapas`, `test_abrir_caso_cli`, `test_custodia_destino_efectivo`),
por JUnit XML: `tests=113 failures=0 errors=0`.

**Arnés de mutación propio** (`lente3/mut.py`): muta una línea del `main` de head, corre
los 113, cuenta rojos por XML, y restaura desde la copia congelada.

| id | mutación en `main` | resultado |
|---|---|---|
| M1 | `except (CaseBusy, MutexPerdido)` → `except (CaseBusy,)` | **SOBREVIVE** |
| M2 | `Exit(codigo_de_salida(BLOQUEADO))` → `Exit(code=0)` | **SOBREVIVE** |
| M3 | `if resultado_v1 is not None:` → `if False:` | **SOBREVIVE** |
| M4 | se borra `registrar_cierre_v1(...)` | **SOBREVIVE** |
| M5 | `secuencia_v1(..., hasta=hasta)` → `hasta=None` | **SOBREVIVE** |
| M6 | se borra `hasta=hasta` de la llamada a `validar_modo` | **SOBREVIVE** |
| M7 | se anula `estado_v1.cerrar(...)` | muerto (1 rojo) |
| M8 | el `except` no imprime nada | **SOBREVIVE** |
| M9 | `except (CaseBusy, MutexPerdido)` → `except (MutexPerdido,)` | **SOBREVIVE** |
| M10 | el `except` entero → `raise` (cero traducción) | **SOBREVIVE** |
| M11 | `if previa is not None and previa.sin_cerrar():` → `if False:` | **SOBREVIVE** |
| M12 | `sys.exit(0)` dentro del `with`, en la rama v1 | **SOBREVIVE** |

11 de 12 sobreviven. Un solo test del repo muerde el cuerpo nuevo de `main`.

**Diferencial de `libre`** (`lente3/test_L3_diff.py`, corrido dentro de `base/` y de
`head/` con los mismos escenarios y solo flags que existen en las dos; volcados
`out_b.json` / `out_w.json`). Rutas y timestamps normalizados.

| escenario | base | head |
|---|---|---|
| A camino feliz (`--fuente manual`) | exit 0, salida X | **idéntico** |
| B `--dry-run` | exit 0, salida Y | **idéntico** |
| C caso tomado por otro proceso | exit 1, `CaseBusy` sin gestionar, salida vacía | exit 1, mensaje limpio |
| D lease perdido al salir del `with` | exit 1, `MutexPerdido` sin gestionar | exit 1 + `=== Apertura: bloqueado ===` |
| E `--dry-run` + lease perdido | **exit 0, cero aviso** | **exit 0, cero aviso** |

En D, las dos versiones dejan `caso_creado: true`, `documento_depositado: true`,
`crm_registrado: true` y `OK CRM id=9999` en la salida: **el trabajo se hizo entero**.

**Sondas sobre la rama `v1`** (`lente3/test_L3_v1.py`, `_v7.py`, `_v8.py`;
`out_v1.json`, `out_v7.json`, `out_v8.json`). Doble de `secuencia_v1`, trampa en
`_intake_drive_ev` para que ninguna sonda salga al Drive real.

| sonda | resultado medido |
|---|---|
| V1 lease perdido al salir | `_apertura_v1.json`: `terminada=<TS>, estado=preparado_con_pendientes`; evento `apertura_v1_terminada` emitido; pantalla: **solo** `=== Apertura: bloqueado ===`; exit 1; **`_informar_v1` no corre** |
| V2 `--hasta drive` por CLI | llega al secuenciador con `hasta="drive"`; exit 0; informe correcto |
| V3 excepción no-exclusión en la secuencia | exit 1, traza, `_apertura_v1.json` **abierto** (`terminada=null`), `eventos: []` |
| V4 `--hasta drve` | exit 1, `[ERROR] --hasta 'drve' no es una etapa de V1`, `caso_creado: false` |
| V5 `CaseBusy` en v1 | exit 1, mensaje limpio, sin estado en disco |
| V6 etapa en fallo | exit 1, `=== Apertura V1: bloqueado ===` con `[no corre] crm/sala_maquina` |
| V7 ronda muerta + ronda siguiente | la 2ª con la misma orden **ni llega**: `ColisionCaso` |
| V8 reanudación | misma orden → exit 1 `ColisionCaso`; `--case-id` → exit 0 **y el aviso de ronda sin cerrar sí sale** |

**Censo estático** (`lente3/censo_exits.py`): salidas del proceso alcanzables desde dentro
del bloque de mutex, contando las funciones del módulo que el bloque llama, en cierre
transitivo. **base: 9. head: 9.** Todas por la rama `libre`
(`_despachar_intake`, `_intake_generico`, `_intake_manual` ×2, `_intake_whatsapp`,
`_validar_flags` ×3, más el `Exit(0)` del `--dry-run`).

**Suite completa de head:** `tests=3859 failures=2 errors=0 skipped=87` (179 s). Los dos
rojos son `tests/test_session_close_no_pude_medir.py::TestLaVerja::test_el_mensaje_sugiere_un_interprete_QUE_EXISTE`
y `::TestLaRutaQueSugiere::test_en_este_repo_encuentra_uno_que_existe`. **No son del
diff:** ese fichero no menciona `abrir_caso` ni `apertura_v1` (grep: 0 ocurrencias), y los
dos comprueban que el intérprete que `session_close` sugiere existe en el repo — la copia
congelada no lleva `.venv` (`ls head/.venv` y `ls base/.venv`: ausente en las dos). Es un
artefacto de mi copia, no un hallazgo.

---

## Hallazgos

### L3-01 — ALTO. Perder el lease al salir del `with` deja el disco diciendo «ronda terminada con éxito» y la pantalla diciendo «bloqueado», y tira el informe

**Qué.** En la rama `v1`, `estado_v1.cerrar(...)` y `registrar_cierre_v1(...)` corren
**dentro** del `with`. Si el lease se perdió, `case_mutex.tomado` lanza `MutexPerdido` al
salir del bloque (cuerpo limpio → lanza, `case_mutex.py:655-659`). El `except` de `main`
lo traduce a `bloqueado` y sale, así que `_informar_v1(resultado_v1)` **nunca corre**
aunque `resultado_v1` ya tiene valor.

**Dónde.** `head/scripts/abrir_caso.py:971-975` (cerrar + registrar dentro del `with`),
`:992-995` (el `except`), `:997-999` (el consumo, inalcanzable en ese camino).

**Por qué importa.** Tres cosas a la vez, y la tercera es la caro:

1. El disco afirma lo contrario que la pantalla. `_apertura_v1.json` queda con
   `terminada` y `estado=preparado_con_pendientes`; el evento `apertura_v1_terminada`
   está emitido; y el operador lee `bloqueado`.
2. Los `pendientes` se pierden. Son el producto entero del estado
   `preparado_con_pendientes` —lo que V1 no pudo cerrar— y solo se imprimen en
   `_informar_v1`. En el único caso en que hay que revisar el resultado a mano, es el
   caso en que no se dice qué revisar.
3. **La ronda siguiente no avisará.** `previa.sin_cerrar()` (`:962`) es False porque la
   ronda quedó cerrada, así que la corrida siguiente da por buena la salida de una ronda
   cuya exclusión se había perdido — o sea, una ronda durante la cual **otro proceso pudo
   escribir el mismo expediente**. Eso es literalmente el riesgo que el §11 cita para
   exigir estado durable («reanudación sin generación común → fase verde sobre inputs
   obsoletos»), y es el que esta pieza existe para cerrar.

**Cómo lo comprobé.** Sonda V1 (`out_v1.json`), con `mutex_sesion.sostenido` doblado por
un gestor fiel a `tomado`: lanza con cuerpo limpio, anota con excepción en vuelo.

**Qué haría falta.** Que la pérdida de exclusión gobierne el estado de la ronda, no solo
el mensaje: o no cerrar la ronda, o cerrarla como `bloqueado`, y en los dos casos imprimir
el informe de etapas antes de traducir la exclusión. Hoy el `except` descarta un resultado
que ya está calculado y ya está en disco.

---

### L3-02 — ALTO. El help de `--hasta` afirma una forma de reanudar que es imposible

**Qué.** `--hasta` se documenta así:

> «v1: para DESPUES de esta etapa (drive|crm|sala_maquina). **Reanudar es volver a lanzar
> la misma orden: lo hecho se salta solo.**»

Volver a lanzar la misma orden **no funciona nunca** para un caso V1.

**Dónde.** `head/scripts/abrir_caso.py:795-798` (el help), `:890-896` (`ColisionCaso`),
`:746-751` (`--force` prohibido en v1 sin `--case-id`).

**Por qué importa.** La cadena es cerrada y no tiene salida:

- La primera corrida de un caso nuevo **tiene** que ir con los 6 flags: la vía
  `--case-id` exige que el caso ya exista con su `_caso.md` (`:843-847`).
- La segunda corrida con esos mismos 6 flags muere en la resolución de identidad:
  `[ERROR] El W-code W-02Z2NR ya existe en la ciudad: [...]. Usa --force para forzar.`,
  exit 1, **antes** del mutex, de `ensure_case` y de la secuencia.
- Y `--force` sin `--case-id` está **prohibido** en `v1` por la propia puerta (H6-02).

Así que la única reanudación posible es `--case-id`, que el help no menciona. Con eso
funciona: exit 0 y el aviso de la ronda sin cerrar sí aparece. O sea que la maquinaria de
detección de rondas muertas —`estado_v1.leer` + `previa.sin_cerrar()`, y con ella la razón
de ser del fichero de estado— **es inalcanzable por la vía que el flag documenta**.

`--hasta` es el flag de la entrega por etapas; que su promesa central sea falsa lo
convierte en una trampa para el operador que se fíe del `--help`. Y no hay red: `--hasta`
no aparece en `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (grep: 0 ocurrencias fuera del plan y
de `core/apertura_v1.py`), así que el help **es** la documentación.

**Cómo lo comprobé.** Sondas V7 y V8 (`out_v7.json`, `out_v8.json`), con `ensure_case`
real en V8 para que `_caso.md` exista y la vía `--case-id` sea legítima. Nota de honradez:
el campo `r2a_llego_a_la_secuencia` de mi volcado es un falso positivo mío —la lista de
llamadas es compartida entre las dos invocaciones—; lo que sostiene el hallazgo es
`r2a_misma_orden_output` (el error de colisión) y que `llamadas` tiene **una** entrada
para dos invocaciones.

**Qué haría falta.** Corregir el texto para que diga la orden que de verdad reanuda
(`--case-id <W-code> --modo v1 --crm skip --folder-id ...`), y decidir si `--hasta` con
los 6 flags debe seguir siendo aceptado cuando su reanudación no lo es.

---

### L3-03 — MEDIO-ALTO. Nada verifica el cuerpo nuevo de `main`: el test de la traducción prueba un helper que producción no llama

**Qué.** `traducir_fallo_de_mutex` (`:557-567`) existe, está probado dos veces
(`test_f26_case_busy_se_traduce_a_bloqueado_y_no_a_una_traza` y
`test_traducir_fallo_de_mutex_deja_pasar_lo_que_no_es_de_exclusion`) y tiene su mutante en
el arnés del autor (F26). **`main` no lo llama**: tiene su propio `try/except` inline
(`:941`, `:992-995`). `grep -rn traducir_fallo_de_mutex head/` devuelve solo el plan y
`tests/`.

**Dónde.** `head/scripts/abrir_caso.py:557-567` (el helper huérfano) frente a `:992-999`
(el código que corre de verdad). El mutante F26 de `tests/_mutantes_plan5.py:210-214` muta
el helper, no el `except`.

**Por qué importa.** El resultado es cobertura al revés: la suite afirma la propiedad
«`CaseBusy` no sale como traza» sobre código muerto, mientras la implementación real queda
sin una sola aserción. Medido con 12 mutantes: sobreviven **11**.

Los que más pesan:

- **M10**: el `except` entero sustituido por `raise` —o sea, la traducción entera
  borrada, exactamente el defecto que F26 dice cubrir— y los 113 tests siguen verdes.
- **M2**: `bloqueado` sale **0**. El contrato que `codigo_de_salida` declara en su
  docstring («quien invoque la secuencia tiene que poder distinguir “terminó con
  pendientes” de “no terminó”») se puede romper en el sitio donde se consume sin que nada
  muerda. `test_f14` prueba la función, no su uso.
- **M3**: `_informar_v1` y la propagación del código de V1 nunca ocurren → verde.
- **M4**: el evento durable de cierre no se emite → verde. (`test_el_evento_de_cierre...`
  llama a `registrar_cierre_v1` directamente, así que no ve que `main` deje de llamarlo.)
- **M5**: `--hasta` se ignora en producción (`hasta=None`) → verde. Un operador que pide
  `--hasta drive` correría Drive **y** CRM **y** el OCR completo, y ningún test lo dice.
- **M6**: `main` deja de pasar `hasta` a la puerta → verde. La remediación de HA-06 (que
  el vocabulario se valide antes de todo efecto) es reversible sin coste: el typo volvería
  a abortar con el esqueleto ya creado, que es el defecto que se dice cerrado.
- **M12**: `sys.exit(0)` dentro del `with`, en la rama `v1`. El guard `test_f25` busca
  nodos `ast.Raise` en el cuerpo de la rama (`test_apertura_v1_cableado.py:125-129`), así
  que una salida por `sys.exit` —que es una `SystemExit`, y por tanto también solo se
  **anota** en `tomado`— le pasa por debajo. El guard comprueba la **forma** del código,
  no la propiedad «no se sale del proceso dentro del bloque».

**Qué haría falta.** O que `main` llame a `traducir_fallo_de_mutex` (y entonces F26 cubre
producción), o tests de extremo a extremo sobre `main` para: `CaseBusy` → mensaje + código,
`MutexPerdido` → mensaje + código, `--hasta` por CLI (V2 y V4 sirven de plantilla),
`_informar_v1` presente, y evento emitido. Y un guard sobre la propiedad en vez de sobre
`ast.Raise`.

---

### L3-04 — MEDIO. HA-07 se cerró en la rama que no lo tenía; quedan 9 salidas abiertas en la rama que sí, todas del modo por defecto

**Qué.** El comentario de `:936-939` explica que el resultado se calcula dentro y se
consume fuera «porque un `typer.Exit` dentro del `with` convertiría una pérdida de
exclusión en una salida 0 con el aviso enterrado en una nota». El `Exit(0)` del
`--dry-run` se deja dentro, declarado como fuera de alcance (`:985-986`, `MEJORAS #142`).

**Dónde.** `head/scripts/abrir_caso.py:984-989`, y el censo: 9 sitios de `typer.Exit`
alcanzables desde dentro del bloque, **idénticos en base y head**
(`_despachar_intake:341`, `_intake_generico:133`, `_intake_manual:236,247`,
`_intake_whatsapp:261`, `_validar_flags:306,320,324`, y `main:989`).

**Por qué importa.** Tres capas:

1. **La rama `v1` nunca tuvo el defecto.** Sus tres etapas atrapan `Exception`
   (`:359`, `:430`, `:468`) y `typer.Exit` es una `Exception`, así que ningún `Exit` de
   `_intake_*` puede escapar por ahí. La rama que se blindó es la que no podía sangrar.
2. **La rama `libre` conserva las 9**, y `libre` es el modo por defecto y el que usa el
   equipo. Además `v1` **prohíbe** `--dry-run` (`:756-761`), así que el único camino donde
   el `--dry-run` es legal es justamente el que quedó sin arreglar.
3. **Es el ejemplo remediado en vez de la frontera.** `MEJORAS #142` describe «el
   `dry-run`» y su remedio como «un movimiento de tres líneas». La propiedad no es «el
   `dry-run` no sale dentro del bloque», es «**ninguna** salida del proceso ocurre dentro
   del bloque», y hay 9. Un cuarto (`_validar_flags`) tiene además el efecto colateral de
   que un `--rol` inválido se detecta **después** de que `ensure_case` creara el
   esqueleto: la propiedad «validar antes de todo efecto» que la puerta de `v1` sostiene,
   en `libre` sigue sin sostenerse.

**Cómo lo comprobé.** Censo estático `lente3/censo_exits.py` sobre los dos árboles, y
sonda E del diferencial: `--dry-run` con el lease perdido sale **0 sin un solo aviso**, en
base y en head por igual. Eso sube `MEJORAS #142` de **SIN VERIFICAR** (su texto lo declara
así: «la sonda se corrió sobre el otro») a **CONFIRMADO** en el camino del `dry-run`.

**Nota de gobernanza.** #142 fija su propio disparador de promoción: «cualquier trabajo
que toque el cuerpo de `main` en `scripts/abrir_caso.py` —el Plan 5 lo toca, pero
deliberadamente no esta rama—». El disparador se cumple con este mismo diff y la entrada
se escribe su propia exención. Con la regla de `CLAUDE.md` en la mano, eso es una
promoción debida, no un diferimiento.

**Qué haría falta.** Cerrar la propiedad: sustituir los `Exit` de la rama `libre` por
retornos/valores consumidos fuera del bloque, o mover `_validar_flags` delante del `with`.

---

### L3-05 — MEDIO. Los dos entrypoints del mismo pipeline dan códigos distintos para la misma condición, y `abrir_caso` colapsa lo reintentable con lo que no

**Qué.** Para `CaseBusy`/`MutexPerdido`:

- `scripts/sala_maquina.py:538-554` sale con **2**, y hay guard permanente
  (`tests/test_entrypoints_mutex.py:213-237`, que exige código 2 y el texto «a medias»).
- `scripts/abrir_caso.py:995` sale con **1**.

**Dónde.** `:551-554` (`codigo_de_salida`) y `:992-995`.

**Por qué importa.** En `abrir_caso`, el 1 ya significa todo lo demás: flag mal escrito,
ciudad desconocida, faltan flags de identidad, `ColisionCaso`, reconciliación fallida,
etapa en fallo. Medido: V4 (typo) = 1, V5 (`CaseBusy`) = 1, V6 (rclone rc=1) = 1. Un
script que envuelva el entrypoint —o el operador— no puede distinguir **«espera y
reintenta»** de **«corrige la orden»** de **«el pull se rompió»**.

Y el `except` colapsa las dos excepciones en un mensaje único (`bloqueado`), cuando el
propio guard hermano documenta que no significan lo mismo y no piden lo mismo:
`CaseBusy` = «el motor no arrancó, espera»; `MutexPerdido` = «arrancó, el lease se perdió
a mitad, **puede haber trabajo a medias**». `abrir_caso` no dice «a medias» en ningún
caso, y es el entrypoint que además ya escribió en el CRM (ver L3-06).

**Qué haría falta.** Alinear el código con el hermano (2 para exclusión) o reservar un
código propio, y separar los dos mensajes como `sala_maquina` ya los separa.

---

### L3-06 — MEDIO. En `libre`, «bloqueado» se imprime sobre una corrida que ya hizo todo el trabajo

**Qué.** Con el lease perdido al salir del bloque, `libre` imprime
`=== Apertura: bloqueado ===` **después** de haber creado el caso, depositado el documento
y dado el alta en el CRM.

**Dónde.** `:992-995`; el `OK Caso abierto` de `:1001` queda inalcanzable.

**Por qué importa.** No es una regresión de código de salida —base también salía 1, por
traza sin gestionar— pero **el mensaje nuevo afirma algo falso**. En el vocabulario del
propio repo (`core/apertura_v1.py:19-25`, los tres estados del §13), `bloqueado` significa
«no terminó». Aquí terminó todo. El operador que se lo crea relanza.

Dos atenuantes medidos, que bajan la severidad de alta a media:
- `_alta_crm` es idempotente (`:616-626`: mira `element == extrajudiciales` en `_caso.md`
  y no re-da de alta), así que relanzar no duplica el expediente en el CRM.
- El código de salida no cambia respecto de base.

Queda un tercer efecto, menor pero real: el vocabulario de V1 (`bloqueado`, los tres
estados del §13) entra en el modo `libre`, que no tiene estados de V1. `libre` no es una
secuencia de V1 y no puede estar «bloqueada» en ese sentido.

**Cómo lo comprobé.** Diferencial D (`out_b.json` vs `out_w.json`): `caso_creado`,
`documento_depositado` y `crm_registrado` en `true`, `OK CRM id=9999` en la salida, y a
continuación el `=== Apertura: bloqueado ===`.

**Qué haría falta.** Un mensaje que diga lo que pasó —el trabajo se completó y la garantía
de exclusión se perdió, revisa si otro proceso entró— en lugar de un estado de V1 que
niega el trabajo hecho.

---

### L3-07 — MEDIO. Una pérdida de exclusión **dentro** de una etapa no llega al `except`: se archiva como «la sala de maquina salio con codigo 2»

**Qué.** Las tres etapas atrapan `Exception` (`:359`, `:430`, `:468`) y
`etapa_sala_maquina` atrapa además `typer.Exit` (`:504-510`). `CaseBusy` y `MutexPerdido`
heredan de `WorkspaceError(Exception)` (`core/casos/workspace_model.py:109`, `:273`,
`:308`), así que **una pérdida de exclusión detectada dentro de una etapa se convierte en
`estado="fallo"` de esa etapa** y jamás llega al `except` de `main`.

**Dónde.** El camino concreto es el de la tercera etapa:
`etapa_sala_maquina` → `scripts.sala_maquina.apply` → `_bajo_mutex`
(`scripts/sala_maquina.py:536-554`), que traduce las dos excepciones a `Exit(code=2)` →
`abrir_caso.py:504-509` lo convierte en
`EtapaResultado(estado="fallo", detalle="la sala de maquina salio con codigo 2")`.

**Por qué importa.** El estado final resultante (`bloqueado`, exit 1) es correcto, pero el
**registro durable miente sobre la causa**: `apertura_v1_terminada` queda con
`{"sala_maquina": "fallo"}` y el detalle habla de un «código 2», indistinguible de un OCR
roto. «El OCR se rompió» y «otro proceso pudo estar escribiendo este expediente» piden
cosas opuestas, que es exactamente lo que el docstring de `test_e6` dice que cuesta un
diagnóstico. Y la ronda se cierra en disco como terminada, con la exclusión ya inválida
(misma clase que L3-01, alcanzada desde dentro).

**Cómo lo comprobé.** Por lectura encadenada de las tres funciones y de la jerarquía de
excepciones. **SIN VERIFICAR en ejecución:** no reproduje la pérdida del lease dentro de la
etapa con el `sala_maquina` real; mis sondas doblan `secuencia_v1`, así que no atraviesan
`_bajo_mutex`. Lo que sí está medido es que `MutexPerdido` es una `Exception` y que
`_bajo_mutex` sale con `Exit(2)`.

**Qué haría falta.** Que `etapa_*` re-lancen `CaseBusy`/`MutexPerdido` en vez de
absorberlos, para que la exclusión la gobierne el dueño de la secuencia; y que
`_bajo_mutex` no aplane la distinción a un código numérico cuando lo llama otro proceso
Python en el mismo intérprete.

---

### L3-08 — BAJO. El rastro de una ronda muerta dura hasta la corrida siguiente, y una ronda muerta no deja ningún evento

**Qué.** `estado_v1.abrir` reescribe el fichero **entero** con una `RondaV1` nueva
(`core/apertura_v1_estado.py:91-96` vía `_escribir`): hay un único registro por caso, sin
historia. Y `registrar_cierre_v1` solo se emite al cerrar, así que una ronda que muere no
deja **nada** en `_intake_log.jsonl`.

**Dónde.** `core/apertura_v1_estado.py:64-96`; `abrir_caso.py:967-968` y `:975`.

**Por qué importa.** El docstring de `registrar_cierre_v1` dice «es el único rastro
DURABLE de la corrida: la pantalla se pierde, el `.jsonl` no». Para una ronda que muere,
ese rastro **no existe** (medido: V3, `eventos: []`), y el único que queda
—`_apertura_v1.json`— lo pisa la ronda siguiente tras un aviso de una línea por stderr.
Dos rondas muertas consecutivas y de la primera no queda constancia. Añadido: el aviso no
lo verifica nada (M11 sobrevive), y `ronda_id = now_iso_utc()` tiene granularidad de
segundo (`:967`), así que dos rondas del mismo segundo comparten identificador.

**Qué haría falta.** Emitir un evento al **abrir** la ronda, no solo al cerrarla —así el
`.jsonl` conserva la historia y el fichero de estado puede seguir siendo de un registro—.

---

### L3-09 — BAJO. La bomba de H6-07 no se extendió a los tres efectos que el diff añadió

**Qué.** `test_v1_aborta_antes_de_la_autoderivacion_y_de_la_identidad`
(`tests/test_abrir_caso_modo_v1.py:234-266`) pone bombas en 8 funciones para acreditar que
la puerta valida antes de cualquier efecto. El diff añadió tres sitios de efecto nuevos
—`estado_v1.abrir` (escribe fichero), `secuencia_v1` (Drive + CRM + OCR) y
`registrar_cierre_v1` (escribe el log)— y **ninguno está en la lista**.

**Por qué importa.** El docstring de ese test dice, con la medición, que existe porque una
puerta desplazada por debajo de la identidad dejaba 14 tests verdes. El write-set que
guarda creció y la lista no, así que hoy vuelve a ser posible desplazar la puerta por
debajo de los efectos nuevos sin que muerda.

**Qué haría falta.** Añadir los tres a la lista de bombas.

---

### L3-10 — BAJO. Ruido: import local redundante, dos encabezados y un vocabulario duplicado

- **`:934`**: `from core.casos.workspace_model import CaseBusy, MutexPerdido` dentro de
  `main`, cuando `:40` ya importa `CaseRef` **del mismo módulo** a nivel de módulo. No hay
  ciclo que lo justifique. Se paga en cada invocación de `libre` y esconde de un grep de
  imports qué excepciones maneja el entrypoint.
- **`:993` vs `:592`**: `=== Apertura: … ===` y `=== Apertura V1: … ===`. Dos encabezados
  para el mismo comando, y el de la rama bloqueada es el que pierde el «V1» — justo en
  `libre`, donde el «V1» sería lo único que explicaría de dónde sale «bloqueado».
- **`ETAPAS_V1` (`:51`)** duplica los nombres que `secuencia_v1` construye (`:581-584`).
  `validar_modo` valida contra la constante y `secuenciar` contra los construidos
  (`core/apertura_v1.py:99-102`); si divergen, la puerta admite un vocabulario que la
  secuencia rechaza **después** de `ensure_case`, que es el defecto HA-06 reintroducido por
  deriva. Nada lo ata (M5 y M6 sobreviven).

---

## Lo que aguanta

Medido, no supuesto:

1. **El camino feliz de `libre` es idéntico byte a byte.** Mismo código de salida (0),
   misma salida, mismo caso en disco (diferencial A).
2. **El `--dry-run` de `libre` es idéntico.** Mismo texto, mismo 0 (diferencial B).
3. **El orden observable de `libre` se conserva:** `ensure_case → intake → crm`, con el
   test del repo que lo afirma por secuencia y no por ausencia de texto
   (`test_modo_libre_conserva_el_comportamiento`).
4. **`CaseBusy` en `libre` no cambia de código de salida** (1 en las dos versiones) y head
   sustituye una excepción sin gestionar por un mensaje: en eso mejora.
5. **La puerta sigue validando antes de cualquier efecto, y `--hasta` entra en ella.**
   `--hasta drve` sale 1 con mensaje propio y **no crea carpeta** (V4): la remediación de
   HA-06 funciona en el código, aunque nada la proteja (L3-03/M6).
6. **`--hasta drive` llega de verdad al secuenciador** con el valor correcto, y el informe
   enumera `[no corre] crm` y `[no corre] sala_maquina` (V2, V6).
7. **Una excepción no-exclusión deja `_apertura_v1.json` abierto** (`terminada=null`, V3):
   ahí la propiedad «empezó y no terminó» se sostiene, y es lo que hace que L3-01 destaque
   como la excepción a su propia regla.
8. **`_intake_drive_ev` mantiene `force=False` por defecto** (`:141-143`), así que el
   `force=True` de `etapa_drive` no se filtra al modo `libre`: su semántica de pull no
   cambió.
9. **El reloj del único `sostenido` de `main` sigue siendo `now_iso_utc`**, con guard AST
   permanente que lo comprueba por árbol y no por subcadena
   (`tests/test_entrypoints_mutex.py:147-178`).
10. **`_alta_crm` es idempotente** (`:616-626`), lo que acota el daño de L3-06.
11. **`EstadoV1` es una clase-namespace de cadenas**, no un enum, así que el f-string de
    `:993` rinde `bloqueado` y no `EstadoV1.BLOQUEADO`: no hay defecto de representación.
12. **No hay camino que imprima `OK Caso abierto` para una corrida `v1`**, ni camino en el
    que `resultado_v1` quede a `None` debiendo tener valor. El error de flujo es el
    inverso, y es L3-01: tiene valor y se descarta.

---

## Lo que no pude comprobar

- **L3-07 en ejecución.** El encadenamiento
  `MutexPerdido → _bajo_mutex → Exit(2) → etapa_sala_maquina → "fallo"` está leído en las
  tres funciones, no corrido. **SIN VERIFICAR.**
- **El verde global del árbol, con matiz.** La suite entera dio `3859 tests / 2 failures`,
  y los dos rojos son un artefacto de mi copia (falta `.venv`), no del diff. Lo que **no**
  puedo afirmar es que el árbol esté verde en la máquina de trabajo: no reproduje esos dos
  con `.venv` presente. Para mi lente es irrelevante; para el merge, quien lo cierre debe
  correrlos en el worktree real.
- **`pytest-randomly` no está instalado** en el intérprete del encargo, así que todo lo
  medido va en orden fijo. Un verde en orden fijo no dice nada sobre el aislamiento de
  estado entre tests; en este repo eso ya está escrito como lección. **SIN VERIFICAR.**
- **El §5 del plan de cableado y las actas de revisión adversarial**, por instrucción del
  encargo. No los abrí. Ver la declaración de contaminación arriba.

---

# LENTE 4 — `core/apertura_v1_estado.py` y su atomicidad

# LENTE 4 — `core/apertura_v1_estado.py` y su cableado

Revisor adversarial. Objeto: copia congelada `C:/Users/tnm33/AppData/Local/Temp/rB/head/`.
Trabajo del revisor: `C:/Users/tnm33/AppData/Local/Temp/rB/lente4/`.

**Promesa declarada bajo ataque:** «una ronda que murió a mitad se detecta» y «la escritura
es atómica».

**Veredicto:** la segunda mitad de la promesa **no está probada por ningún test** (un
mutante enteramente NO atómico sobrevive a 312 tests, L4-01) y la primera mitad **no es una
propiedad del sistema, es una línea en `stderr` de un solo uso** que el propio módulo
destruye acto seguido (L4-03). Ambas son ejecutables y las ejecuté.

---

## Evidencia

Ficheros leídos íntegros: `head/core/apertura_v1_estado.py` (103 líneas),
`head/tests/test_apertura_v1_estado.py` (67), el cableado
`head/scripts/abrir_caso.py:38, 921-999` y sus funciones `registrar_cierre_v1`
(534-552), `secuencia_v1` (570-586), `_informar_v1` (589-600), la puerta de admisión
(695-745). Leídos en lo que toca: `head/core/apertura_v1.py`, `head/core/utils.py:72-86`,
`head/core/casos/case_mutex.py:500-660`, `head/core/casos/mutex_sesion.py:1-80`,
`head/core/sala_maquina.py:36-45, 140-225, 1173-1215`, `head/core/config.py:380-401`,
`head/core/repository_checkout.py:240-268`, `head/tests/test_escritura_censo.py:1-105`,
`head/tests/_mutantes_plan5.py`, `head/tests/test_apertura_v1_cableado.py`,
`head/tests/test_apertura_v1_e2e.py`, `head/tests/test_abrir_caso_modo_v1.py`.
**No leídos, por encargo:** nada con `adversarial-review` en el nombre, ni el §5 del plan 5.

Intérprete: `pythoncore-3.14-64` (3.14.4). `LongPathsEnabled = 1` en esta máquina (dato
que importa para L4-12). Volúmenes presentes: `C:\`, `G:\`, `H:\`. **No escribí en `G:\`
ni en `H:\`** (Drive del despacho).

Sondas (todas en `lente4/`):

| Sonda | Qué mide |
|---|---|
| `lente4/p1.py` | `os.replace` sobre destino existente; destino abierto por otro handle (3 variantes); creación de árbol; `leer()` con `terminada` falsy y con tipos raros |
| `lente4/p2.py` | asimetría de longitud temporal/destino; ruta larga real; fallo de `os.fdopen`; directorio sin permiso de escritura; corrupción externa → `leer()` → `abrir()` |
| `lente4/p3.py` | `sala_maquina.inventariar/plan` sobre un `00_Input` que contiene el fichero de control y un temporal huérfano; sha por escritura |
| `lente4/p4.py` | `repository_checkout.esta_excluido` y `plan_merge` sobre `00_Input/_apertura_v1.json` |
| `lente4/p5.py` | `os.replace` entre volúmenes (C: → G:) |
| `lente4/mut/` | arnés de mutación mínimo (7 tests del módulo) |
| `lente4/repo/` | copia completa y escribible del objeto, para correr el conjunto contractual y las sondas del cableado (`tests/test_L4_probe.py`, `tests/test_L4_probe2.py`) |

Línea base verificada antes de mutar: `tests/test_apertura_v1_estado.py` → **7 passed**;
conjunto contractual (secuenciador + etapas + cableado + estado + e2e) → **63 passed**;
`-k "apertura or estado or abrir_caso"` → **312 passed, 0 failures**.

---

## Hallazgos

### L4-01 — CRÍTICO. El único test de «la escritura es atómica» no prueba atomicidad: una escritura EN SITIO sobrevive a 312 tests

**Qué.** `tests/test_apertura_v1_estado.py:16-28` (`test_f27_la_escritura_es_atomica_y_lleva_id_de_ronda`)
afirma dos cosas: que `os.replace` **se llamó** (línea 25) y que el JSON escrito lleva el
`ronda_id` (28). Ninguna de las dos es atomicidad. El mutante declarado para esa frontera en
`tests/_mutantes_plan5.py:218-222` sustituye `os.replace(tmp, f)` por
`f.write_text(cuerpo, ...)`: muere, pero muere **porque deja el temporal atrás** y porque
`os.replace` desaparece del grafo de llamadas — no porque la escritura haya dejado de ser
atómica.

**Dónde.** `core/apertura_v1_estado.py:65-88` (`_escribir`), defendido por
`tests/test_apertura_v1_estado.py:16-28` y `63-67`.

**Por qué importa.** Es la frontera titular del fichero. Su docstring
(`core/apertura_v1_estado.py:66-72`) dice literalmente que escribir en sitio «deja un JSON
truncado si el proceso muere a mitad, y entonces la ronda siguiente no sabe que hubo una —
que es justo la propiedad que este fichero existe para dar». Con el test actual, alguien
puede reintroducir exactamente ese defecto y la suite lo bendice.

**Cómo lo comprobé.** Mutante en `lente4/repo/core/apertura_v1_estado.py`, sustituyendo el
bloque entero `mkstemp…replace…except BaseException` por:

```python
    with open(f, "w", encoding="utf-8") as fh:  # MUT-NOATOMICA
        for trozo in cuerpo:
            fh.write(trozo)
    os.replace(f, f)
```

Es la peor escritura posible: trunca el destino y escribe **carácter a carácter**, de modo
que morir a mitad deja precisamente el JSON truncado del docstring. La llamada
`os.replace(f, f)` es un no-op que satisface la aserción del test.

- conjunto contractual (`secuenciador+etapas+cableado+estado+e2e`): **63 passed, 0 red**
- `pytest tests/ -k "apertura or estado or abrir_caso" --junit-xml`: **312 tests, failures 0,
  errors 0** (contado por JUnit XML, no por el resumen)

Y como control, con el módulo restaurado, el mutante `sin_cerrar → return False` sí mata
`test_f28` (1 failed): el arnés muerde, lo que no muerde es esta frontera.

**Qué haría falta.** Un test que mate una escritura en sitio: escribir un estado válido,
inyectar un `_escribir` que falle **después** de empezar a escribir el cuerpo (p. ej.
monkeypatch de `os.replace` que lance, o de `fh.write` que lance a mitad) y afirmar que lo
que queda en disco es **el estado anterior íntegro y legible por `leer()`** — no que
`os.replace` figure en el grafo. Con eso, `open(f,"w")` muere y `mkstemp+replace` vive.
Por la regla del propio arnés («un mutante que mata de MENOS no prueba su frontera»), F27
está mal apuntado y debe reapuntarse al mutante de arriba.

---

### L4-02 — ALTA. En Windows `os.replace` falla si CUALQUIER otro proceso tiene el destino abierto, incluso solo en lectura; la `PermissionError` no la captura nadie, y en `cerrar` **invierte** la semántica del fichero

**Qué.** `os.replace` sobre un destino con otro handle abierto lanza
`PermissionError [WinError 5]`. Python abre sin `FILE_SHARE_DELETE`, así que basta un
antivirus escaneando, Drive for Desktop sincronizando, un editor con el JSON abierto o
cualquier lector externo. La excepción sale de `_escribir` (correctamente re-lanzada) y
**nadie la captura**: el `try` de `scripts/abrir_caso.py:921-995` solo atrapa
`CaseBusy`/`MutexPerdido`.

**Dónde.** `core/apertura_v1_estado.py:82`; cableado en `scripts/abrir_caso.py:967-974`.

**Por qué importa.** Dos consecuencias asimétricas:

1. En `abrir` (línea 967) un lock transitorio de 200 bytes **aborta la apertura completa
   antes de hacer nada**, con traceback crudo.
2. En `cerrar` (971-974) es peor y es lo contrario de lo que el fichero promete: la ronda
   **terminó bien**, pero el estado en disco se queda `terminada: null`. La siguiente
   corrida avisará de una «ronda que no llegó a cerrarse» que sí se cerró — un falso
   positivo del detector. Y como la excepción corta antes de
   `registrar_cierre_v1` (975), se pierde también el evento
   `apertura_v1_terminada` del log forense de una corrida que puede haber costado una hora
   de OCR, y `_informar_v1` (998) nunca imprime el informe.

**Cómo lo comprobé.** `lente4/p1.py`, tres variantes, las tres fallan:

```
P2  con destino abierto en lectura:      FALLA PermissionError [WinError 5] Acceso denegado:
      '...\.apertura_v1.pievj4wj.tmp' -> '...\_apertura_v1.json'
P2b con destino abierto en append:       FALLA PermissionError [WinError 5]
P2c con destino con byte-range lock:     FALLA PermissionError [WinError 5]
```

Que la excepción no está capturada se lee en `scripts/abrir_caso.py:992`.

**Qué haría falta.** Reintento acotado con espera corta alrededor de `os.replace`
(el patrón habitual en Windows), y —independientemente de eso— que el fallo de `cerrar`
**no** se coma el `registrar_cierre_v1` ni el informe: cerrar el estado es lo último y lo
menos importante de los tres, y hoy es lo primero y aborta a los otros dos.

**SIN VERIFICAR:** si `os.replace` es atómico sobre `G:\` (Drive for Desktop, sistema de
ficheros virtual), que es un `CASOS_ROOT` real de este proyecto. No lo probé porque exigía
escribir en el Drive del despacho.

---

### L4-03 — ALTA. «Una ronda que murió a mitad se detecta» es un `stderr` de un solo uso: el aviso no cambia nada y `abrir` destruye la evidencia inmediatamente

**Qué.** El cableado lee la ronda previa, imprime un aviso y **sigue exactamente igual**
(`scripts/abrir_caso.py:961-970`). Acto seguido `estado_v1.abrir` (967) **sobrescribe** el
registro de la ronda muerta, que era su único rastro: `registrar_cierre_v1` (534-552) no
registra el `ronda_id` ni el hecho de que la anterior no cerró, y en el camino en que la
ronda muere no llega a ejecutarse en absoluto.

**Dónde.** `scripts/abrir_caso.py:961-975`; `core/apertura_v1_estado.py:91-96`.

**Por qué importa.** El docstring del módulo (líneas 8-10) dice: «Lo que da es que una ronda
muerta a mitad se DETECTE, en vez de que la siguiente corrida trate su salida como buena»,
y el aviso afirma «esta corrida no da por buena su salida». Medido: **la corrida da por
buena su salida**. No invalida nada, no fuerza rehash, no cambia el código de salida, no
propaga el hecho a las etapas. Y las etapas sí reutilizan salidas previas: la sala de
máquina salta por sha (`core/sala_maquina.py:193-215`, `skip=sha in estado_previo`), que es
literalmente el riesgo que la spec §11 nombra («fase verde sobre inputs obsoletos»). El
aviso va además a `stderr`: en cualquier invocación que redirija o descarte `stderr`, el
único rastro del corte se pierde para siempre en la misma corrida.

**Cómo lo comprobé.** `lente4/repo/tests/test_L4_probe.py::test_W1_el_aviso_es_decorativo`,
sobre el `main()` real con los dobles del arnés existente:

```
exit sin ronda previa: 0 | exit CON ronda muerta: 0
aviso presente: True
secuencia_v1 llamada igual: ['ensure_case', 'secuencia']
estado en disco tras la 2a corrida: RondaV1(ronda_id='2026-09-03T13:30:49Z', ... terminada='...')
RONDA_MUERTA mencionada en el log forense: False
claves del evento de cierre: dict_keys(['estado','parada','pendientes','etapas'])
```

Y `::test_W4_una_excepcion_en_la_secuencia_deja_la_ronda_abierta` confirma el otro extremo:
con `secuencia_v1` lanzando, el disco queda `terminada=None` (correcto) pero
`hay log forense de la ronda muerta: False` — el `.jsonl`, que
`registrar_cierre_v1:538` llama «el unico rastro DURABLE de la corrida», no sabe nada.

**Qué haría falta.** O el aviso tiene consecuencia (marcar el caso, exigir `--force`,
invalidar el estado de la sala de máquina, salir distinto de 0), o la promesa se rebaja por
escrito a «deja constancia en pantalla». Como mínimo: **no destruir** el registro anterior
—archivarlo, o emitir un evento `apertura_v1_ronda_abandonada` con el `ronda_id` viejo antes
de sobrescribir—, porque hoy el detector borra su propia prueba.

---

### L4-04 — MEDIA. Un estado ilegible se confunde con «primera ronda» y luego se destruye: el modo de fallo que el fichero existe para detectar es justo el que no detecta

**Qué.** `leer()` devuelve `None` en tres situaciones distintas —no existe (48), ilegible
(51-52), JSON válido con otra forma (53-54)— y el llamador solo distingue
`None` / `no-None` (`scripts/abrir_caso.py:962`). Un fichero **truncado** es por tanto
indistinguible de «este caso nunca corrió».

**Dónde.** `core/apertura_v1_estado.py:39-54`; consumo en `scripts/abrir_caso.py:961-962`.

**Por qué importa.** El docstring (42-44) llama a esto «el lado seguro: lo contrario seria
decidir sobre datos inventados». Para *decidir* lo es; para *detectar* es el lado inseguro,
y detectar es la única función del fichero. Un JSON truncado es la firma exacta de «alguien
escribió aquí y murió»: es la señal más fuerte que puede existir, y se descarta en silencio.
La escritura atómica cierra una vía de llegada de ese truncamiento, no todas: quedan la
corrupción de disco, el `CONFLICT` del checkin (L4-07) y cualquier escritor ajeno.

**Cómo lo comprobé.** `lente4/p2.py`:

```
P8 fichero truncado; leer() -> None
P8 contenido antes de la siguiente ronda: '{\n  "ronda_id": "ronda_que_murio", ...'
P8 tras abrir(): la evidencia del truncado -> '{\n  "ronda_id": "nueva", ...'
```

Es decir: no se detecta, no se avisa, y la evidencia se borra.

**Qué haría falta.** Que `leer` distinga los tres casos (p. ej. `None` / `ROTO` / `RondaV1`)
y que el cableado avise **más** fuerte con `ROTO` que con «ronda sin cerrar», o al menos que
renombre el fichero roto a un lado en vez de sobrescribirlo. Es un cambio de tres líneas y
un test.

---

### L4-05 — MEDIA. `cerrar` está DENTRO del bloque del mutex: si el lease se pierde, el disco dice «cerrada, preparado_con_pendientes» mientras el CLI dice `bloqueado` y sale 1

**Qué.** `estado_v1.cerrar` se ejecuta en `scripts/abrir_caso.py:971-974`, dentro del `with
mutex_sesion.sostenido(...)`. `case_mutex.tomado` **lanza** `MutexPerdido` al salir
limpiamente del bloque si el lease dejó de ser nuestro (`core/casos/case_mutex.py:655-660`).
El orden resultante es: escribir «ronda cerrada con éxito» → salir → descubrir que no
teníamos exclusión → reportar `bloqueado`.

**Dónde.** `scripts/abrir_caso.py:971-975` frente a `992-995`.

**Por qué importa.** Pérdida de exclusión a mitad es exactamente el caso en que la ronda
siguiente **debe** desconfiar de la salida: otro escritor pudo tocar el caso. Pero el
estado durable queda `terminada != None`, así que `sin_cerrar()` es `False` y la corrida
siguiente **no avisa de nada**. El único registro que sobrevive al operador dice lo
contrario que el operador vio en pantalla. (Simétricamente, el evento
`apertura_v1_terminada` del `.jsonl` también se escribe dentro del bloque, línea 975, con
el mismo problema — está en el borde de esta lente, lo anoto por el mismo motivo.)

**Cómo lo comprobé.** `lente4/repo/tests/test_L4_probe.py::test_W2_mutex_perdido_tras_cerrar`,
con `mutex_sesion.sostenido` doblado por un gestor que lanza `MutexPerdido` **al salir**
(la semántica real de `case_mutex.tomado`, leída en las líneas citadas):

```
exit: 1
salida: === Apertura: bloqueado === |   exclusion: [MUTEX_PERDIDO] — el mutex se perdio ...
estado durable en disco: RondaV1(..., terminada='2026-09-03T13:30:31Z',
                                 estado='preparado_con_pendientes', etapas={'drive':'hecha'})
sin_cerrar(): False
```

**Qué haría falta.** O `cerrar` se llama **fuera** del bloque, con el resultado ya calculado
(el mismo patrón que el comentario de las líneas 943-946 aplica a `resultado_v1`, y por la
misma razón), o el estado se cierra con `estado="bloqueado"` cuando el mutex se perdió.
Hoy la excepción del mutex no llega al fichero de estado por ninguna vía.

---

### L4-06 — MEDIA. El fichero de control vive en `00_Input`, que es el directorio que la sala de máquina inventaría, y NO está en su lista de ignorados: entra como documento `sin_soporte`, con un sha NUEVO por escritura, en la misma ronda que lo escribió

**Qué.** `core/sala_maquina.py:1173` define
`_IGNORAR = {"_intake_log.jsonl", "_inventory.json", ".pulled", ".synced"}`.
`_apertura_v1.json` no está. `abrir` lo escribe en `00_Input` **antes** de correr la
secuencia (`scripts/abrir_caso.py:967` → `969`), y la tercera etapa de esa misma secuencia
es la sala de máquina, que inventaría `00_Input` recursivo.

**Dónde.** `core/apertura_v1_estado.py:35-36` (la ruta) contra
`core/sala_maquina.py:1173, 1210-1215` y `193-215`.

**Por qué importa.** Cada `abrir` y cada `cerrar` cambia el contenido, o sea el sha, o sea
que el inventario ve un **documento nuevo** en cada ronda. Aparece en el plan como
`sin_soporte` y engorda la cobertura y la caché sin techo, una entrada por escritura y para
siempre. No corrompe nada, pero es ruido en `_cobertura.md`, que es la red de calidad que un
humano lee para decidir si el expediente está completo — y el fichero que la ensucia es
precisamente el que se añadió para que el humano pudiera confiar en la corrida.

**Cómo lo comprobé.** `lente4/p3.py`, sobre un `00_Input` de juguete:

```
'_apertura_v1.json' en _IGNORAR: False
  plan: _apertura_v1.json ruta= sin_soporte slug= apertura_v1__32b5d2df skip= False
  plan: .apertura_v1.deadbeef.tmp ruta= sin_soporte slug= apertura_v1_deadbeef__44136fa3 skip= False
shas distintos de _apertura_v1.json en 3 cierres: 3
```

(El temporal huérfano de L4-09 también entra, por la misma puerta.)

**Qué haría falta.** Añadir `_apertura_v1.json` a `_IGNORAR` y un patrón para
`.apertura_v1.*.tmp`, con un test que lo fije. Nota: `_caso.md` tampoco está en `_IGNORAR`,
así que hay precedente — pero un precedente no es una razón, y este fichero cambia en cada
corrida mientras `_caso.md` no.

---

### L4-07 — MEDIA. No está en `MERGE_EXCLUSIONS`: el checkout se lo lleva a local y el checkin lo mergea a 3 vías. Medido: `CONFLICT` sobre un fichero de control, o `COPY_LOCAL` que empuja el estado de una copia al canon

**Qué.** `core/config.py:391-400` enumera los ficheros que gestiona el **protocolo** y no el
sync: `_caso.md`, `_intake_log.jsonl`, `MANIFEST_CHECKOUT.json`… `_apertura_v1.json` no se
añadió. `repository_checkout.esta_excluido("00_Input/_apertura_v1.json")` es `False`.

**Dónde.** `core/config.py:391-400` y `core/repository_checkout.py:245-266, 290-…`, contra
`core/apertura_v1_estado.py:35-36`.

**Por qué importa.** El estado de ronda es información **por copia** («qué ronda corrió
sobre estos bytes»), y el sistema de biblioteca lo va a tratar como un documento del caso:

- si ambas copias corrieron una ronda durante el préstamo → `CONFLICT` en un fichero de
  control, que no tiene resolución con sentido (no se pueden «fusionar» dos rondas);
- si solo corrió la local → `COPY_LOCAL`: el estado de la ronda local aterriza en el canon,
  y la siguiente corrida sobre el canon lee una ronda **ajena**. Si esa ronda importada está
  cerrada, silencia el aviso sobre una ronda del canon que sí murió; si está abierta, avisa
  de un corte que nunca ocurrió ahí.

**Cómo lo comprobé.** `lente4/p4.py`:

```
esta_excluido 00_Input/_caso.md          -> True
esta_excluido 00_Input/_intake_log.jsonl -> True
esta_excluido 00_Input/_apertura_v1.json -> False
plan_merge (ambos cambiaron): AccionMerge(ruta='00_Input/_apertura_v1.json',
    accion='CONFLICT', motivo='Divergencia real: ambos lados cambiaron', caso_tabla=4)
plan_merge (solo local):      AccionMerge(..., accion='COPY_LOCAL', caso_tabla=2)
```

**Qué haría falta.** Un renglón en `MERGE_EXCLUSIONS` y un test que lo fije. El coste de
omitirlo lo paga el primer checkin de un caso que se abrió en las dos copias, que es
justamente el escenario del que este proyecto ya tiene cicatriz.

---

### L4-08 — MEDIA/BAJA. El `fsync` cubre el fichero, no el directorio; y la única propiedad que hace atómico el `replace` —temporal en el MISMO sistema de ficheros— no la defiende ningún test, aunque en `CASOS_ROOT=G:` sea la diferencia entre funcionar y `WinError 17`

**Qué.** `core/apertura_v1_estado.py:78-82` hace `flush` + `os.fsync(fh.fileno())` del
**contenido del temporal** y luego `os.replace`. No hay (ni puede haber, en Windows, de
forma portable) `fsync` del **directorio**, así que la entrada de directorio del rename no
está garantizada como durable ante un corte de corriente: el contenido está en disco y el
nombre puede no estarlo.

Y la afirmación del docstring (70-71) —«El temporal va al mismo directorio porque
`os.replace` solo es atomico dentro del mismo sistema de ficheros»— es correcta y
**load-bearing**, pero ningún test la sostiene.

**Dónde.** `core/apertura_v1_estado.py:70-82`.

**Cómo lo comprobé.** Dos medidas.

1. Mutante `dir=str(f.parent)` → `dir=None` en `mkstemp` (temporal al `TEMP` del sistema):
   **7 passed**, mutante superviviente. El `TEMP` de esta máquina es `C:\Users\...\Temp`,
   el mismo volumen que `tmp_path`, así que el test no puede notarlo por construcción.
2. `lente4/p5.py`, cruce de volúmenes real:

```
TEMP = C:\Users\tnm33\AppData\Local\Temp
volumenes: ['C:\\', 'G:\\', 'H:\\']
os.replace C: -> G:\: FALLA OSError [WinError 17] El sistema no puede mover el archivo a otra unidad
```

`CASOS_ROOT` por defecto es local (`core/config.py:31`), pero `G:` es un valor real y
documentado de este proyecto. Con `dir=None` la escritura del estado sería imposible allí.

**Por qué importa.** No es un defecto vivo —el código actual hace lo correcto— es una
frontera **sin guard**: la corrección de la línea 76 depende de que nadie la «simplifique»,
y la suite no lo impediría.

**Qué haría falta.** Un test que afirme que el temporal se crea bajo `f.parent` (basta
espiar `tempfile.mkstemp` y comprobar el `dir`). Sobre el `fsync` del directorio: declararlo
en el docstring como límite conocido en Windows, en vez de dejar que «atómica + fsync» se
lea como «durable ante corte de corriente». **SIN VERIFICAR:** no probé un corte de
corriente real.

---

### L4-09 — BAJA. Si `os.fdopen` falla, el descriptor queda colgado y el temporal huérfano — en silencio, dentro del directorio que el intake escanea

**Qué.** `core/apertura_v1_estado.py:76-88`. `mkstemp` devuelve un `fd` crudo; si
`os.fdopen(fd, ...)` lanza antes de tomar posesión del descriptor, el `except BaseException`
intenta `os.unlink(tmp)` — que en Windows falla porque el fichero sigue abierto por ese
`fd`— y el `except OSError: pass` (86-87) se lo traga. Resultado: `fd` filtrado y temporal
huérfano, sin ninguna traza.

**Dónde.** `core/apertura_v1_estado.py:76-88`.

**Cómo lo comprobé.** `lente4/p2.py`, con `os.fdopen` doblado para lanzar `MemoryError`:

```
P5 excepcion propagada: MemoryError simulado
P5 temporales huerfanos tras fallo de fdopen: ['.apertura_v1.6l52ath2.tmp']
```

Y el mutante que **elimina toda la limpieza** del temporal (quitar el `try/except
BaseException` completo, dejando el `with` y el `replace`) sobrevive: **7 passed**. O sea que
la rama de limpieza no está cubierta por ningún test —
`test_no_queda_temporal_tras_una_escritura_correcta` (63-67) solo mira el camino feliz.

**Por qué importa.** Poco por sí solo (la ventana es estrecha: `MemoryError`, EMFILE) y
mucho combinado con L4-06: el huérfano cae en `00_Input`, que la sala de máquina inventaría
como documento. Además la `PermissionError` por directorio sin permiso de escritura sí sale
limpia y verificada (`P6 ... FALLA PermissionError [Errno 13]`), pero tampoco la captura
nadie arriba (mismo comentario que L4-02).

**Qué haría falta.** `os.close(fd)` en el camino de fallo antes del `unlink`, y un test de
la rama de limpieza (monkeypatch de `os.replace` que lance → afirmar que no queda temporal).
Aparte, `except OSError: pass` con un temporal sobreviviente merece al menos un aviso: un
fichero que no se pudo borrar en el directorio de entrada del expediente no es un no-evento.

---

### L4-10 — BAJA. `leer()` no valida tipos: `"terminada": 0` o `false` se lee como ronda CERRADA — un falso negativo del detector

**Qué.** `core/apertura_v1_estado.py:59` hace `terminada=d.get("terminada")` sin comprobar
tipo, y `sin_cerrar()` (31-32) es `self.terminada is None`. Cualquier valor falsy que no sea
`None` marca la ronda como cerrada. `ronda_id` e `iniciada` sí se pasan por `str()`, lo que
convierte un dict o una lista en su `repr` en vez de rechazarlo.

**Cómo lo comprobé.** `lente4/p1.py`:

```
P7  terminada=0     -> sin_cerrar(): False
P7b terminada=false -> sin_cerrar(): False
P7c ronda_id dict   -> RondaV1(ronda_id="{'a': 1}", iniciada="['y']", ...)
```

**Por qué importa.** El docstring (43-44) razona que se exigen las dos claves mínimas porque
«se pudo parsear» no es «es lo que espero». El razonamiento es correcto y se aplica a medias:
la clave de la que depende **toda** la detección no se valida. La vía de llegada realista no
es un editor de texto, es L4-07 (un merge que elige mal el lado) o cualquier escritor futuro.

**Qué haría falta.** `terminada=d["terminada"] if isinstance(d.get("terminada"), str) else None`,
y `return None` si `ronda_id`/`iniciada` no son `str`. Es la misma decisión que el módulo ya
tomó para las dos claves obligatorias, aplicada a la tercera.

---

### L4-11 — BAJA. `ronda_id` es una segunda lectura del reloj: sin unicidad, redundante con `iniciada`, y medido divergiendo de ella

**Qué.** `scripts/abrir_caso.py:967-968` llama `now_iso_utc()` **dos veces**, una para
`ronda_id` y otra para `ahora`. `now_iso_utc` (`core/utils.py:76-85`) tiene resolución de
segundo, así que el `ronda_id` no es un identificador: es la hora de inicio, con la misma
granularidad que el campo `iniciada` que va al lado, y **puede no coincidir con él**.

**Cómo lo comprobé.** `lente4/repo/tests/test_L4_probe2.py`, desviando solo las lecturas 2ª
y 3ª del reloj del CLI:

```
RondaV1(ronda_id='2026-09-03T10:00:02Z', iniciada='2026-09-03T10:00:03Z', ...)
```

El aviso de la línea 964-966 imprime los dos valores juntos, así que el operador puede leer
una ronda cuyo «id» y cuya «hora de inicio» se contradicen.

**Por qué importa.** Hoy nada empareja por `ronda_id` (fichero de una sola ranura, ningún
otro consumidor en el repo: verificado con `grep -rn "apertura_v1_estado\|_apertura_v1.json"`
→ solo el módulo, su test, el cableado y el plan). Así que el daño es cosmético. Lo señalo
porque el campo se llama `_id` y no lo es: en cuanto alguien lo use como llave —correlacionar
el aviso con un evento del `.jsonl`, que es el remedio obvio a L4-03— dos rondas del mismo
segundo colisionan.

**Qué haría falta.** Una sola lectura del reloj (`ahora = now_iso_utc()`; `ronda_id=ahora`)
si `ronda_id` va a seguir siendo la hora; o un `uuid4` si va a ser una identidad.

---

### L4-12 — BAJA. El nombre del temporal es 8 caracteres MÁS LARGO que el del destino: existe una ventana de `MAX_PATH` en la que el destino cabe y el temporal no

**Qué.** `core/apertura_v1_estado.py:76`: `prefix=".apertura_v1."` + 8 caracteres aleatorios
de `mkstemp` + `suffix=".tmp"` = **25** caracteres, frente a los **17** de
`_apertura_v1.json`. Medido:

```
len('_apertura_v1.json') = 17
nombre temp: .apertura_v1.0xw5yp6p.tmp len = 25 -> delta = 8
```

Los nombres de caso de este proyecto son largos (medido sobre el ejemplo del propio docstring
del CLI: `BaRS11 - Passeig Maritim, 30 - Castelldefels (08860) - (W-02Z2NR) - Vuelta` = **74**
caracteres), y `CASOS_ROOT` en Drive añade ~70 más.

**Cómo lo comprobé.** `lente4/p2.py`. En **esta** máquina no muerde:
`LongPathsEnabled = 1`, y tanto un directorio de 247 como uno de 241 caracteres funcionan
(`P4b: OK`, `P4c: OK (LongPaths activo)`).

**Por qué importa.** El repo ya tiene la lección de `MAX_PATH` escrita (el
`--basetemp` corto de su propia guía de pytest). En una máquina o un contexto sin
long-paths, hay un rango de longitudes de ruta —`len(dir)` entre 234 y 241— en el que
escribir `_apertura_v1.json` directamente funcionaría y la escritura atómica falla. El fallo
sería, además, en `abrir`: la apertura entera muerta antes de empezar por el nombre de un
temporal.

**SIN VERIFICAR:** el comportamiento en una máquina con `LongPathsEnabled = 0`, y sobre
`G:\`. No lo puedo medir aquí sin cambiar el registro del sistema.

**Qué haría falta.** Un prefijo corto (`prefix="."`, `suffix=".tmp"` → 13 caracteres, más
corto que el destino) elimina la ventana sin coste. O aceptarlo por escrito.

---

### L4-13 — BAJA (gobernanza). El cableado no tiene NINGÚN test, y el censo de escrituras no ve la primitiva con la que este módulo escribe

**Qué.** Dos huecos de cobertura declarables:

1. **Cableado sin test.** `grep -rn "sin_cerrar\|estado_v1\." tests/` fuera de
   `tests/test_apertura_v1_estado.py` devuelve **cero** coincidencias relevantes (solo un
   homónimo en `test_email_atomize_inline.py` y el arnés de mutantes). Ni
   `tests/test_apertura_v1_cableado.py` ni `tests/test_apertura_v1_e2e.py` ni
   `tests/test_abrir_caso_modo_v1.py` mencionan el estado por ronda: el e2e entra por
   `cli.secuencia_v1`, no por `main()`, así que las líneas 961-975 —el aviso, el `abrir`
   antes de la secuencia, el `cerrar` después— **no las ejecuta ningún test**. Los hallazgos
   L4-03 y L4-05 salieron de escribir esas sondas yo.
2. **El censo no cuenta lo que este módulo escribe.**
   `tests/test_escritura_censo.py:39-45` detecta `write_text`, `write_bytes`, `mkdir`,
   `unlink`, `copy2`, `append_event`, `open(...,"w"/"a")` y las ambiguas
   `replace`/`copy`/`dump`. La escritura de bytes real de este módulo es
   `tempfile.mkstemp` + `os.fdopen` + `fh.write` (líneas 76-79): **ninguna** de las tres está
   en el detector. El techo subió 84 → 87 contando `mkdir`, `os.replace` y `unlink`, y el
   comentario que justifica la subida (líneas 92-101) avisa contra «un techo con hueco»
   mientras la primitiva de escritura de la pieza que lo sube pasa invisible.

**Por qué importa.** El (1) explica por qué esta lente encontró lo que encontró: la pieza
está probada como módulo aislado y **no como cableado**, que es donde vive la promesa. El (2)
no es un defecto de este módulo sino del detector, pero el módulo es el primer productor que
lo destapa, y el propio fichero del censo dice que un número agregado esconde su composición.

**Qué haría falta.** (1) Tres tests sobre `main()` con el arnés que ya existe en
`test_abrir_caso_modo_v1.py`: que el aviso aparece con ronda previa abierta, que
`abrir` precede a `secuencia_v1`, que `cerrar` la sigue. (2) Añadir `mkstemp`/`fdopen` al
detector y volver a medir el techo — sabiendo que subirá y por qué.

---

## Lo que aguanta

Lo verifiqué y no encontré por dónde tumbarlo:

- **`os.replace` sobre un destino existente funciona en Windows** (la duda 1 del encargo).
  Medido en `lente4/p1.py`: `abrir` → `cerrar` → `abrir` deja el estado correcto, sin
  necesidad de borrar antes. La objeción real no es esa, es el handle abierto (L4-02).
- **El `except BaseException` no se traga nada.** El `raise` desnudo (línea 88) re-lanza la
  excepción original intacta; `KeyboardInterrupt` y `SystemExit` propagan.
  Medido: con `os.fdopen` lanzando `MemoryError`, la sonda recibe
  `MemoryError simulado`. El `except OSError` interior solo cubre el `unlink`, que es su
  alcance correcto. (El único resquicio teórico: un segundo Ctrl+C durante el `unlink`
  desplazaría la excepción original. No es accionable.)
- **El temporal va al mismo directorio, y eso es lo correcto** — precisamente lo que L4-08
  dice que nadie prueba. El código está bien; es el guard el que falta.
- **No queda temporal en el camino feliz.** Verificado por el test 63-67 y reproducido en
  todas mis sondas: los directorios de prueba quedan solo con `_apertura_v1.json`.
- **`abrir` se llama ANTES de la secuencia y `cerrar` DESPUÉS** (`scripts/abrir_caso.py:967`
  vs `969` vs `971`). El orden que la promesa necesita está bien puesto.
- **Una excepción de la secuencia deja la ronda abierta**, que es el comportamiento
  correcto. Medido (`test_W4`): `terminada=None` tras un `RuntimeError` en `secuencia_v1`.
- **`--hasta` con un typo NO envenena el estado.** Era mi hipótesis (el `abrir` precede a
  `secuenciar`, que valida `hasta`), y está **refutada**: el vocabulario se valida en la
  puerta de admisión, `scripts/abrir_caso.py:725-727`, antes del mutex y de `ensure_case`,
  y hay mutante y test para ello (`F23`).
- **Dos procesos escribiendo a la vez sobre el mismo caso**: no llegan. El bloque completo
  va bajo `mutex_sesion.sostenido` (`scripts/abrir_caso.py:941`) y `leer`/`abrir`/`cerrar`
  quedan dentro. El módulo por su cuenta no ofrece exclusión —y su docstring lo **declara**
  («No reconcilia dos escritores»), que es la forma honesta de tener ese límite—. Queda una
  observación sin severidad: `cerrar` escribe desde el `RondaV1` en memoria sin comprobar
  que en disco siga estando **su** ronda; no es compare-and-swap. Hoy lo cubre el mutex.
- **Carrera entre `mkstemp` y `replace`** (la duda 1 del encargo): dos escritores obtendrían
  temporales de nombres distintos y el `replace` es el punto de serialización, así que el
  peor caso es «gana el último», no un fichero corrupto. No encontré vía a un estado
  parcialmente escrito por esa ruta.
- **`_escribir` crea el árbol si falta** (línea 74) y falla limpio sin permisos
  (`PermissionError [Errno 13]`, medido). En el cableado siempre corre después de
  `ensure_case` + `localizar`, así que no puede crear un `00_Input` fantasma por su cuenta.
- **El estado y las etapas serializan a JSON sin sorpresas**: `EstadoV1` es una clase-espacio
  de nombres de `str`, no un `Enum` (`core/apertura_v1.py:19-25`), y `EtapaResultado.estado`
  es `str` validado contra un vocabulario cerrado. No hay `TypeError` de `json.dumps`
  esperando al final de una corrida larga.

---

# LENTE 5 — los dos trinquetes: censo de escrituras y vocabulario de eventos

# LENTE 5 — Los dos trinquetes que este diff sube

Revisor adversarial, solo lectura sobre `C:/Users/tnm33/AppData/Local/Temp/rB/head/`.
Trabajo en `C:/Users/tnm33/AppData/Local/Temp/rB/lente5/` (copia `work/`, restaurada al final).
No leídos, por mandato: ficheros `*adversarial-review*` y el §5 del plan del Plan 5.

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`.

---

## Evidencia

### E1 — El censo: número y **reparto por fichero**, head contra base

Ejecutado con el propio detector del test (`censar()` importado del fichero, `chdir` a cada
árbol), no re-implementado:

| Productor | base | head |
|---|---|---|
| `core/case_manager.py` | 9 | 9 |
| `core/intake_drive.py` | 2 | 2 |
| `core/intake_manifest.py` | 4 | 4 |
| `core/intake_log.py` | 1 | 1 |
| `core/sync_sudespacho.py` | 17 | 17 |
| `core/email_atomize/pipeline.py` | 15 | 15 |
| `core/adjuntos_contenido/pipeline.py` | 3 | 3 |
| `core/sala_maquina.py` | 13 | 13 |
| `core/split_documental.py` | 5 | 5 |
| `scripts/abrir_caso.py` | **2** | **3** |
| `scripts/sala_maquina.py` | 12 (costura=True) | 12 (costura=True) |
| `core/apertura_v1_estado.py` | — | **3** |
| **TOTAL** | **83** | **87** |

`TECHO_CENSO` base 83 → head 87. `test_el_techo_no_esta_holgado` exige igualdad, y la hay.
`tests/test_escritura_censo.py` pasa: 9 tests verdes.

El +4 se descompone en +1 (`scripts/abrir_caso.py`) y +3 (`core/apertura_v1_estado.py`), que es
lo que narran los dos párrafos añadidos («83 → 84» y «84 → 87»). La aritmética cuadra.

- El +1 de `abrir_caso.py` es el `append_event` de `registrar_cierre_v1`
  (`scripts/abrir_caso.py:539`). `grep append_event`: base 2 sitios, head 3.
- Los +3 de `apertura_v1_estado.py` son exactamente `f.parent.mkdir` (:74), `os.replace` (:82) y
  `os.unlink` (:85). El comentario dice «`mkdir`, `os.replace` y el `unlink` del temporal»: cierto.
- `censar("core/apertura_v1_estado.py")` → `(3, False)`: no importa la costura. Cierto.
- `censar("core/apertura_v1.py")` → `(0, False)`.
- `registrar_cierre_v1` está en `scripts/abrir_caso.py`, no en `core/apertura_v1.py`. La deuda
  **no** se absorbió: cierto.

### E2 — Mutantes sobre el trinquete 1

- **Mutante 1** (quitar `"core/apertura_v1_estado.py"` de `PRODUCTORES`): censo 84,
  `test_el_techo_no_esta_holgado` **falla** (`84 == 87`). El emparejamiento lista + techo exacto
  muerde. ✔
- **Mutante 2** (añadir a `core/apertura_v1_estado.py` una función de escritura NUEVA con el
  patrón atómico `tempfile.mkstemp` + `os.fdopen(fd,"w")` + `fh.write` + `os.rename`):
  **los 9 tests pasan, el censo no se mueve.** Ver L5-02.

### E3 — Quién usa la costura hoy

`grep -rn "deposito(" head/core head/scripts`: un solo llamador de producción,
`scripts/sala_maquina.py:121` (`clase="derivado"`, `modo="libre"`, con `workspace`). Base
idéntico. `deposito()` con `modo="v1"` **sigue sin un solo llamador** aunque este diff estrena
`--modo v1` en producción.

`core/repository_checkout.py:565`: `es_protocolo=True` → `desviar=False` incondicional. Por tanto,
para una escritura de clase `protocolo` la costura **no cambiaría el destino**; añadiría la
verificación de identidad (`meta.id_go` vs nombre vs petición), la contención de base y la
declaración de mutex. Eso hace defendible el «deuda declarada» **en cuanto al destino**, y es lo
único que hace defendible.

### E4 — El vocabulario de eventos

```
HEAD len(INTAKE_EVENTS) = 34   ("apertura_v1_terminada" in set: True)
BASE len(INTAKE_EVENTS) = 33   (docstring base decía 27)
```

`core/intake_log.py:9` dice 34 y `len()` es 34: **coincide**. El diff corrigió un contador rancio
con 6 de desfase.

Barrido del diff por `append_event(` y por literales `"event"`: el único nombre nuevo emitido es
`apertura_v1_terminada`, y está declarado (`core/intake_log.py:100`). No hay otro evento nuevo sin
declarar.

### E5 — Mutantes sobre el doble aserto

- **Mutante A** (mover `apertura_v1_terminada` de `NUEVOS_V1` a `NUEVOS` y vaciar `NUEVOS_V1`):
  **23 tests verdes.** El doble aserto mide lo mismo en las dos formas (28 = 34−6 = 34−5−1).
- **Mutante B** (borrar el evento histórico `delete_doc`): `len(antiguos)` = 27,
  `test_los_veintiocho_de_antes_SIGUEN_estando` **falla**. ✔ El doble aserto no se debilitó.
- **Mutante C** (borrar `delete_doc` **y** añadir `apertura_v1_reanudada`, len sigue 34):
  **los 9 tests de `TestVocabulario` pasan.** Lo caza solo el conjunto enumerado de
  `tests/test_intake_log.py:406-412`.

### E6 — El fichero de estado dentro del inventario probatorio

Arnés ejecutado sobre `head` (caso sintético; `est.abrir()` como lo llama `main`, más un `.tmp`
huérfano como lo dejaría un kill entre `mkstemp` y `os.replace`):

```
INVENTARIO de 00_Input:
    .apertura_v1.igv26sex.tmp   ext= .tmp
    01_Drive EV/contrato.pdf    ext= .pdf
    _apertura_v1.json           ext= .json

PLAN (ruta por fichero):
    .apertura_v1.igv26sex.tmp -> sin_soporte  skip= False
    01_Drive EV/contrato.pdf  -> pdf          skip= False
    _apertura_v1.json         -> sin_soporte  skip= False

_IGNORAR = {'_intake_log.jsonl', '_inventory.json', '.synced', '.pulled'}
```

### E7 — Suites ejecutadas

`tests/test_escritura_censo.py` + `tests/test_intake_log.py` +
`tests/test_intake_log_workspace.py`: **55 verdes** (`-p no:randomly`; también verde con el orden
aleatorio por defecto). `head` intacto: re-ejecutado al final, 9 verdes.

---

## Hallazgos

### L5-01 — ALTO — El fichero de estado de V1 entra en el inventario probatorio del caso, y el comentario del censo afirma lo contrario

**Qué.** `core/apertura_v1_estado.py:20,36` escribe `00_Input/_apertura_v1.json`. El único
registro de ficheros de control de `00_Input` que existe en el repo es
`core/sala_maquina.py:1173` — `_IGNORAR = {"_intake_log.jsonl", "_inventory.json", ".pulled",
".synced"}` — y **el diff no lo toca**. En `--modo v1`, `scripts/abrir_caso.py:967` escribe el
fichero **antes** de que `etapa_sala_maquina` (:970 → `sala_maquina.apply`) inventaríe `00_Input`.

**Dónde.** `core/apertura_v1_estado.py:20`, `:73-88`; `scripts/abrir_caso.py:967-975`;
`core/sala_maquina.py:1173`, `:1209-1215`, `plan()` :191-216, `clasificar_ruta()` :36-45.

**Por qué importa.**
1. `.json` no está en `_EXTS_NATIVO` (`core/sala_maquina.py:33`), así que `clasificar_ruta`
   devuelve `sin_soporte`: el fichero de control aparece en `_cobertura` como **un documento del
   caso que la sala de máquina no pudo leer**, en cada ronda de V1. Es literalmente el fallo que
   la tabla de la spec nombra: «Ficheros YAML/JSON de control entran en cobertura → Falsos
   pendientes y OCR inútil → Registro central y exhaustivo de controles excluidos del inventario
   probatorio» (`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:848`).
2. Su sha queda **rancio por construcción**: el contenido cambia entre `abrir` (:967) y `cerrar`
   (:971), y el inventario se toma en medio. El sha que entra en la cadena de custodia nunca es
   el final.
3. El temporal de la escritura atómica se llama `.apertura_v1.<aleatorio>.tmp`
   (`core/apertura_v1_estado.py:76`). El `except BaseException` de :83-88 **no cubre** un
   `SIGKILL` ni un corte de corriente, y nada más los limpia: cada muerte dura deja un huérfano
   con nombre único que **acumula** filas `sin_soporte` en el expediente.
4. Y el comentario que justifica la subida del techo dice: «Es escritura de **protocolo**: un
   fichero de control en `00_Input`, no un documento del caso»
   (`tests/test_escritura_censo.py:93-94`). Nada en el código lo hace un fichero de control: la
   clase `protocolo` solo existiría si pasara por la costura, y no pasa. **El nombre de la cosa
   no es la cosa**: el comentario declara una clasificación que el código contradice.

**Cómo lo comprobé.** E6: arnés que reproduce la secuencia de `main` y llama a
`sala_maquina.inventariar` + `sala_maquina.plan` reales. Ningún test del diff lo ve porque
`tests/test_apertura_v1_e2e.py:96` hace `monkeypatch.setattr(sala_maquina, "apply", _apply)`: el
inventario real nunca corre con el fichero de estado presente.

**Qué haría falta.** Añadir `_apertura_v1.json` a `core/sala_maquina._IGNORAR` **y** un filtro por
prefijo `.apertura_v1.` para los temporales (o mover el temporal fuera de `00_Input`… lo cual
rompe la atomicidad de `os.replace`, así que el filtro por prefijo es la vía). Y un test que corra
`inventariar` sobre un caso con el estado escrito y afirme que no aparece — el guard tiene que ver
el inventario real, no un doble.

### L5-02 — MEDIO — El censo no ve la escritura principal del módulo nuevo, y el diff estrena el patrón que lo ciega

**Qué.** El detector cuenta `PRIMITIVAS` + `open` con modo `a`/`w` + las ambiguas. No conoce
`tempfile.mkstemp` ni `os.fdopen(fd, "w")`. En `core/apertura_v1_estado.py:76,78` están las dos:
el fichero se **crea** con `mkstemp` y se **escribe** por `fdopen(...,"w")` + `fh.write`. Los tres
sitios que el censo cuenta (`mkdir`, `os.replace`, `unlink`) son el andamio; la escritura del
contenido no se cuenta.

**Dónde.** `tests/test_escritura_censo.py:38-41` (`PRIMITIVAS`), `:113-121` (rama `open`);
`core/apertura_v1_estado.py:76`, `:78-79`. Comentario afectado: `tests/test_escritura_censo.py:90-99`.

**Por qué importa.** El censo real del módulo son **5** sitios, no 3, y el techo debería ser 89.
Pero el daño no es el número: es que este diff **introduce y bendice** un patrón de escritura
—atómico, con `mkstemp`+`fdopen`— que el trinquete no ve. Mutante 2 (E2) lo prueba: una función de
escritura completamente nueva en un productor, con ese mismo patrón, **pasa los 9 tests sin mover
el censo**. Eso es exactamente el «techo con hueco» que el comentario dice estar cerrando, cinco
líneas por encima: «Un censo que no cuenta lo nuevo no es un censo, es un numero»
(`tests/test_escritura_censo.py:99`). Colateral de la misma clase: `os.rename` no está en
`AMBIGUAS`, así que el hermano de la línea 82 tampoco se contaría.

Además, el test que existe para probar que el detector no es vacuo
(`test_el_detector_encuentra_lo_que_dice_encontrar`, :204-231) enumera write_text/write_bytes/
mkdir/unlink/json.dump/open-a y **no incluye la forma atómica** — así que el hueco no se cerró ni
se detectó al escribir el fixture.

**Cómo lo comprobé.** AST sobre `head/core/apertura_v1_estado.py` buscando `mkstemp`/`fdopen`
(dos aciertos, líneas 76 y 78, `fdopen` con modo `['w']`), y el mutante 2 de E2.

**Qué haría falta.** Añadir `mkstemp`/`mkdtemp` a `PRIMITIVAS`, tratar `fdopen` en la rama de
`open` (mismo criterio de modo), añadir `rename` al lado de `replace`, re-baselinear el techo con
el desglose por fichero delante, y añadir la forma atómica al fixture del detector.

### L5-03 — MEDIO — El comentario nombra la vía de escape y la deja abierta: `core/apertura_v1.py` no está en `PRODUCTORES`

**Qué.** `tests/test_escritura_censo.py:86-89` dice: «Lo que NO se hizo, y era tentador: mover
`registrar_cierre_v1` a `core/apertura_v1.py`, que no esta en `PRODUCTORES`. El censo habria
bajado a 83 sin que la escritura desapareciera. Eso es absorber la deuda». Correcto — y el módulo
**sigue fuera de la lista**.

**Dónde.** `tests/test_escritura_censo.py:24-37` (la tupla) y `:86-89` (el comentario).

**Por qué importa.** `core/apertura_v1.py` es el hogar natural de la lógica de V1. La primera
escritura que alguien añada ahí es invisible al trinquete, con la vía de escape ya documentada en
el propio fichero del guard como algo que «era tentador». Es la frontera nombrada y no contratada:
remediar el ejemplo (no mover esta función) en vez de la propiedad (que un módulo nuevo de V1 que
escriba se cuente). El coste de cerrarla es **cero**: `censar("core/apertura_v1.py")` devuelve
`(0, False)` hoy, así que añadirlo a `PRODUCTORES` no mueve el techo.

**Cómo lo comprobé.** E1 (censo 0) y lectura de la tupla.

**Qué haría falta.** Añadir `"core/apertura_v1.py"` a `PRODUCTORES` en este mismo commit, con el
techo sin tocar. Y —de fondo— que la lista deje de ser el punto único de fallo: un guard que
compare `PRODUCTORES` contra los módulos de `core/` que sí escriben, o al menos que exija
declaración explícita de exención.

### L5-04 — MEDIO — El único rastro durable del éxito se escribe DENTRO del bloque de mutex; la pérdida de exclusión se descubre después

**Qué.** En `scripts/abrir_caso.py`, dentro del `with mutex_sesion.sostenido(...)` (:942) se
ejecuta la secuencia (:969), se **cierra el estado durable** (:971-974) y se **emite
`apertura_v1_terminada`** (:975). `mutex_sesion.sostenido` levanta `MutexPerdido` **al salir** del
bloque cuando la sesión perdió el lease (`core/casos/mutex_sesion.py:165-187`: con `fallo is None`,
lo que salga de `gestor.__exit__` «ES la noticia: el mutex se perdió durante la operación. Que
suba»). Ese `MutexPerdido` lo captura :992 y el proceso informa `bloqueado` y sale con 1.

**Dónde.** `scripts/abrir_caso.py:936-939` (el comentario de HA-07), `:967-975`, `:992-995`;
`core/casos/mutex_sesion.py:159-187`; `tests/test_apertura_v1_cableado.py:~118-128` (el guard
estructural).

**Por qué importa.** El log forense queda con `apertura_v1_terminada` y
`details.estado="preparado_con_pendientes"` —y `_apertura_v1.json` con `terminada` y ese mismo
estado— para una ronda en la que **la exclusión se perdió mientras se escribía**, que es
precisamente el caso en que otro proceso pudo estar escribiendo el mismo expediente. El operador
ve «bloqueado» y exit 1; el `.jsonl`, que es lo que se lee seis meses después, dice que la apertura
terminó bien. Y la ronda siguiente leerá `previa.sin_cerrar() == False` y dará su salida por buena
— «fase verde sobre inputs obsoletos», el riesgo que el módulo de estado cita como su razón de ser
(`core/apertura_v1_estado.py:3-6`).

La remediación de HA-07 sacó del bloque **la pantalla y el `Exit`** y dejó dentro **el registro
durable**, que es lo que la propia docstring de `registrar_cierre_v1` (:548-550) llama «el unico
rastro DURABLE… la pantalla se pierde, el `.jsonl` no». El guard estructural que la acompaña solo
prohíbe nodos `ast.Raise` en la rama v1: no ve escrituras de éxito. Se cerró el ejemplo (`raise`
dentro del `with`), no la frontera (**no comprometer un registro de éxito antes de confirmar la
exclusión**).

**Cómo lo comprobé.** Lectura del flujo en `head` (no ejecutado end-to-end: ningún test del diff
cubre `MutexPerdido` al salir con la secuencia ya corrida — `grep MutexPerdido` en
`tests/test_apertura_v1_*.py` solo devuelve `CaseBusy` a través de `traducir_fallo_de_mutex`).
El comportamiento de `sostenido` está leído en su `finally`, no ejecutado: **la cadena completa
está SIN VERIFICAR por ejecución**; el análisis es estático y las dos piezas (escritura dentro,
excepción a la salida) son inequívocas en el código.

**Qué haría falta.** Escribir el registro durable **fuera** del bloque, junto con `_informar_v1`
(:997-999), de modo que una pérdida de exclusión lo convierta en `bloqueado`; o registrar dos
eventos y que el segundo confirme la exclusión. Y un test que pierda el lease dentro del `with` y
afirme qué quedó en el `.jsonl`.

### L5-05 — BAJO/MEDIO — La detección de «ronda previa sin cerrar» solo va a la pantalla, y nada la registra

**Qué.** `scripts/abrir_caso.py:961-966` detecta que la ronda anterior no se cerró y lo dice con
`typer.echo(..., err=True)`. Acto seguido `estado_v1.abrir` (:967) **sobrescribe** el fichero, y la
secuencia continúa igual. No hay evento en `INTAKE_EVENTS` para ese hecho.

**Por qué importa.** El módulo existe para que «una ronda muerta a mitad se DETECTE, en vez de que
la siguiente corrida trate su salida como buena» (`core/apertura_v1_estado.py:9-10`). Lo entregado
es una línea en stderr que se pierde en cualquier ejecución con la salida redirigida, y la única
prueba durable —el `.jsonl`— no sabe que hubo una ronda muerta, porque el fichero que lo decía se
acaba de sobrescribir. Es la misma contradicción de L5-04 en pequeño: la afirmación «la pantalla
se pierde, el `.jsonl` no» convive con la detección puesta solo en pantalla.

**Cómo lo comprobé.** Lectura de `scripts/abrir_caso.py:961-968` y de `INTAKE_EVENTS` completo
(34 nombres; ninguno cubre «ronda previa sin cerrar»).

**Qué haría falta.** O un evento declarado para el hecho, o `details` en `apertura_v1_terminada`
que arrastre el `ronda_id` de la previa sin cerrar. Cualquiera de las dos lo hace legible después.

### L5-06 — BAJO — El `details` del evento lleva estrictamente menos que la pantalla

**Qué.** `registrar_cierre_v1` (`scripts/abrir_caso.py:539-549`) guarda `estado`, `parada`,
`pendientes` (solo códigos) y `etapas` (solo `nombre` + `estado`). `_informar_v1` (:562-573)
imprime además `resultado.no_ejecutadas` y el `detalle` de cada etapa.

**Por qué importa.** Para una ronda `bloqueado`, el motivo del fallo —p. ej.
`"rclone rc=3; errores=[...]"` de `etapa_drive`, o «el expediente esta bloqueado por el legado v1»
de `traducir_pull_crm`— existe **solo en pantalla**. Y `no_ejecutadas` es el campo que el
dataclass añadió (`core/apertura_v1.py:~96`) para que «no corrió» sea explícito y no una inferencia
por ausencia; se imprime y no se registra. El fichero que se autodescribe como «el unico rastro
DURABLE» lleva menos información que el efímero.

**Cómo lo comprobé.** Comparación línea a línea de los dos productores del informe, y
`tests/test_apertura_v1_cableado.py:41-43`, que afirma exactamente las tres claves reducidas — el
test fija el subconjunto, así que no hay quien lo note.

**Qué haría falta.** Añadir `no_ejecutadas` y el `detalle` por etapa al `details`.

### L5-07 — BAJO — Tres contadores a mano quedan rancios, y el que acaba de corregirse sigue sin guard

**Qué.**
1. `tests/test_escritura_censo.py:24`: «Los **11** productores que la tabla del §25 nombra» — la
   tupla tiene ahora **12** entradas. El diff añadió la entrada y no tocó la cabecera.
2. `tests/test_intake_log_workspace.py:229`: «El vocabulario: 28 -> **33**, con el doble aserto» —
   son 34. El diff renombró `test_son_treinta_y_cuatro` y dejó la cabecera de la sección.
3. `core/intake_log.py:9-11` se corrigió de 27 a 34 con la nota «Un contador escrito a mano se
   pudre en silencio» (venía con 6 de desfase). Y **sigue escrito a mano**: no hay test que ate
   ese número a `len(INTAKE_EVENTS)`.

**Por qué importa.** (1) y (2) son la cabecera que se lee **antes** que el dato correcto, en el
fichero de un guard cuya razón de existir es que el número diga la verdad. (3) es el diagnóstico
correcto sin el contrato: se nombró la propiedad («se pudre en silencio») y no se escribió el
guard, así que volverá a pudrirse.

**Cómo lo comprobé.** `grep -n` sobre los tres ficheros en `head`; conteo de la tupla; `grep`
sobre `tests/*.py` buscando cualquier aserto que lea el docstring de `intake_log` (`__doc__`): solo
`tests/test_sala_maquina_workspace.py:296` lee un docstring, y es de otra cosa.

**Qué haría falta.** Corregir las dos cabeceras y añadir un test de una línea que extraiga el
número del docstring de `core/intake_log.py` y lo compare con `len(INTAKE_EVENTS)`.

### L5-08 — BAJO — La justificación de `NUEVOS_V1` es decorativa, y el doble aserto no impide lo que su docstring dice

**Qué.** `tests/test_intake_log_workspace.py:238-240`: «Va en su propio conjunto y no en `NUEVOS`
para que el doble aserto de abajo siga midiendo lo que mide: que los 28 historicos siguen todos
ahi». **Falso como causa**: mutante A (E5) mete el evento en `NUEVOS`, vacía `NUEVOS_V1`, y los 23
tests pasan — el doble aserto mide exactamente lo mismo (28 = 34−6 = 34−5−1). La separación es
higiene taxonómica (y evita que `test_los_cinco_nuevos_se_pueden_emitir`, parametrizado sobre
`NUEVOS` en :272, pase a tener seis casos con nombre «cinco»), no una propiedad de medida.

Y el docstring que el diff conserva (:246-252) dice que el doble aserto «impide cuadrar la cifra
por resta». **No lo impide**: mutante C (E5) borra `delete_doc` y añade un evento inventado
manteniendo len=34, y los 9 tests de `TestVocabulario` pasan. Lo que caza esa maniobra es el
conjunto enumerado de `tests/test_intake_log.py:406-412` — que el diff **sí** actualizó, así que
no hay regresión; pero el crédito está mal atribuido, y quien confíe en el doble aserto confía en
menos de lo que cree.

**Por qué importa.** Es la aserción débil aplicada a un guard: el comentario le atribuye una
garantía que la ejecución desmiente, y eso se propaga a la próxima ampliación del vocabulario.

**Cómo lo comprobé.** Mutantes A, B y C de E5.

**Qué haría falta.** Corregir el comentario de :238-240 (decir la razón real: `NUEVOS` es el
conjunto de la Fase 1 dual y lo parametriza otro test) y el docstring de :246-252 (el que impide
la resta es el enumerado de `test_intake_events_contiene_los_canonicos`; el doble aserto es su
red secundaria).

### L5-09 — BAJO — Cita de fuente equivocada, y el control de la spec es más ancho de lo entregado

**Qué.** Dos sitios citan «§11» como origen del `estado.json` atómico:
`core/apertura_v1_estado.py:3-4` («§11, tabla de riesgos») y `tests/test_escritura_censo.py:91`
(«la spec §11 hace obligatorio "desde la primera entrega"»). El control está en la tabla del
**§12** —`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:873`:
«Reanudación sin generación común | Fase verde sobre inputs obsoletos | `estado.json` atómico
obligatorio desde la primera entrega»—. El §11 (:798-818) son los gates bloqueantes y no menciona
`estado.json`.

Y el control es «reanudación sin **generación común**»: lo pedido es una identidad de la generación
de los inputs, para que una fase reanudada pueda saber si sus entradas cambiaron. Lo entregado es
un marcador de ronda (`ronda_id`, `iniciada`/`terminada`, estado por etapa) **sin identidad de los
inputs**. El módulo lo declara con honestidad en su propia docstring (:8-10, «Lo que NO es»); el
comentario del censo lo presenta como cumplimiento del requisito.

**Por qué importa.** Es el ancla a fuente: un lector que vaya al §11 no encuentra nada y no puede
contrastar. Y presentar un marcador de ronda como el `estado.json` que la spec exige convierte
«detecto que la ronda anterior murió» en «puedo reanudar sin arrastrar salidas obsoletas», que es
otra propiedad.

Nota aparte, no verificable aquí: «Lo cazo la R-A del Plan 5 (HA-11) antes de escribir una linea»
(`tests/test_escritura_censo.py:89`) — **SIN VERIFICAR**, el acta de la revisión está fuera de mi
mandato de lectura.

**Cómo lo comprobé.** Lectura de los §11 y §12 de la spec en `head` y `grep` de la frase literal.

**Qué haría falta.** Cambiar «§11» por «§12» en los dos sitios y matizar la afirmación del censo
para que diga qué mitad del control se cumple.

### Observación colateral (fuera de los dos trinquetes, pertinente a L5-04)

`traducir_fallo_de_mutex` (`scripts/abrir_caso.py:557-568`) tiene **cero llamadores de
producción**: `grep -rn traducir_fallo_de_mutex core scripts` devuelve solo su definición, y `main`
usa un `try/except (CaseBusy, MutexPerdido)` inline en :941/992. Los dos tests que la cubren
(`tests/test_apertura_v1_cableado.py:133-146`) dan confianza sobre un camino que producción no
recorre — y el camino que sí decide qué se registra ante pérdida de exclusión (L5-04) no tiene
prueba. `codigo_de_salida`, en cambio, sí se usa (:995, :999).

---

## Lo que aguanta

1. **87 es el número real, y su reparto es el declarado.** Reproducido con el propio detector,
   fichero a fichero, contra el árbol base: 83 → 87, con +1 en `scripts/abrir_caso.py` y +3 en
   `core/apertura_v1_estado.py`. `test_el_techo_no_esta_holgado` exige igualdad y la hay: no hay
   holgura.
2. **Los tres sitios del módulo nuevo son exactamente los que el comentario nombra**
   (`mkdir` :74, `os.replace` :82, `unlink` :85), y el módulo efectivamente no importa la costura.
3. **El +1 de `abrir_caso.py` es exactamente el `append_event` de `registrar_cierre_v1`** (:539):
   base 2 sitios, head 3. La atribución del comentario es correcta.
4. **La deuda no se absorbió.** `registrar_cierre_v1` está en `scripts/abrir_caso.py`, que sí está
   en `PRODUCTORES`, no en `core/apertura_v1.py`. La tentación que el comentario confiesa no se
   ejecutó, y `core/apertura_v1.py` censa 0: no hay escritura escondida ahí hoy.
5. **El emparejamiento lista + techo exacto muerde.** Mutante 1: quitar el productor nuevo de la
   lista deja el censo en 84 y el test falla. La lista no puede encogerse en silencio sin bajar el
   techo en el mismo commit.
6. **La clasificación como deuda y no como cobertura es defendible en cuanto al destino.** Con
   `es_protocolo=True`, `decidir_escritura` (`core/repository_checkout.py:565`) no desvía nunca, y
   la escritura ocurre bajo el mutex sostenido en `main`. Pasar por `deposito()` no habría movido
   los bytes. (Lo que sí habría añadido —verificación de identidad `meta.id_go`, contención de
   base— no se gana, y eso es coste real, no cobertura.)
7. **`len(INTAKE_EVENTS)` == 34 == lo que dice el docstring.** Ejecutado. Y el diff corrigió de
   paso un contador que llevaba 27 con 33 eventos reales: 6 de desfase, encontrados midiéndolo.
8. **`apertura_v1_terminada` es el único evento nuevo del diff**, y está declarado en el set
   cerrado (`core/intake_log.py:100`). Barrido del diff por `append_event(` y por literales
   `"event"`: no hay ningún otro nombre emitido sin declarar.
9. **El doble aserto no se debilitó, y sigue mordiendo su caso simple.** Mutante B: borrar un
   evento histórico rompe `len(antiguos) == 28`. La resta separada de `NUEVOS_V1` mantiene el 28
   histórico intacto (aunque su justificación escrita sea decorativa, L5-08).
10. **`scripts/sala_maquina.py` no añade escrituras** (12 en base y en head) y su `return
    status_atomizacion` nuevo no abre un camino de status falso: todas las salidas tempranas de
    `apply` son `typer.Exit(2)` (:804, :822, :845), que `etapa_sala_maquina` mapea a `fallo`; el
    único `return` del cuerpo es el final (:923). Verificado por barrido de `return`/`Exit` en
    :795-925.
11. **Las suites de los dos trinquetes están verdes**: 55 tests entre
    `test_escritura_censo.py`, `test_intake_log.py` y `test_intake_log_workspace.py`, con y sin
    orden aleatorio.

---

## Veredicto de esta lente

**No mergear sin cerrar L5-01.** No es un defecto del trinquete: es un efecto material sobre el
expediente —el fichero de control de V1 y sus temporales huérfanos entran en el inventario
probatorio y en `_cobertura` como documentos ilegibles del caso, en cada ronda—, y el comentario
que justifica la subida del techo afirma justo lo contrario de lo que el código hace. El arreglo es
una línea en `core/sala_maquina._IGNORAR` más un filtro de prefijo, y un test que corra el
inventario real.

L5-02, L5-03 y L5-04 son las tres del mismo molde y las tres baratas: el trinquete tiene un punto
ciego nuevo que el propio diff estrena, la vía de escape que el diff nombra sigue abierta con coste
cero de cierre, y el registro durable del éxito se compromete antes de que se confirme la
exclusión. Ninguna exige rediseño.

Las dos subidas de techo, en cambio, están **declaradas y no absorbidas**, con la aritmética y la
atribución correctas: el trinquete 1 hizo su trabajo. Y el trinquete 2 llegó a hacer el suyo dos
veces —forzó a declarar el evento y destapó un contador con 6 de desfase—; lo que falta ahí es
crédito bien atribuido (L5-08) y el guard que impida que el contador vuelva a pudrirse (L5-07).

---

# LENTE 6 — si los tests prueban lo que dicen probar

# LENTE 6 — ¿los tests prueban lo que dicen probar?

Revisor adversarial, solo lectura sobre `rB/head`. Trabajo en `rB/lente6`.
Objeto: los ~1.700 nuevos de `informe/DIFF.patch`, con el foco en los 7 ficheros de test
del encargo.

## Evidencia

**Entorno.** Intérprete `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`,
pytest 9.1.1, sin `pytest-randomly`. Copia de trabajo `rB/lente6/w` (robocopy de `head`);
verificado al final con `diff -r -q` que `core/` y `scripts/` de la copia son **idénticos**
a `head` (nada mutado quedó sin restaurar).

**Gotcha de entorno, para quien reproduzca esto:** `--basetemp` **relativo dentro del repo
tumba 10 tests buenos** de `test_sala_maquina_cableado_atomize.py` con
`WorkspaceUnderCatalogRoot` — `WorkspaceRegistry` prohíbe vivir bajo el repo. Hay que usar
un basetemp **fuera** del árbol y corto: usé `C:\p6`.

**Línea base verde:** 103 passed sobre los 7 ficheros del encargo.

**Arnés de mutación propio.** Escribí `rB/lente6/mut.py`: aplica una mutación de texto,
corre la suite con `--junit-xml`, imprime el conjunto exacto de nodeids rojos y restaura.
Mide por XML, no por resumen. Corrí **21 mutantes**; **17 sobrevivieron**. Todos los
veredictos de este informe que dicen «sobrevive» están **ejecutados**, no razonados.

**El arnés del autor.** Corrí `python -m tests._mutantes_plan5` en mi copia:
`28/28 mutantes muertos, cada uno SOLO por su frontera`. Es cierto y lo verifiqué. Lo que
mide es la suite contra las 28 fronteras que **eligió la misma persona que escribió los
tests**; no dice nada de las que no enumeró. Mis 17 supervivientes caen todos ahí, y cuatro
caen sobre fronteras que el arnés **nombra** (F16, F25, F27, F10/F12) pero mutando el otro
extremo de la costura.

**Sondeo directo.** Para `test_e2e_es_punto_fijo_MATERIAL...` escribí un test-sonda que
imprime el árbol que compara `foto()`. Resultado literal:
`antes=[('00_Input/_caso.md', 252)] despues=[('00_Input/_caso.md', 252)]`. Sonda retirada.

**Descartado por medición, no por razonamiento** (punto 5 del encargo): `pytest.fail` levanta
`_pytest.outcomes.Failed`, cuyo MRO es `(OutcomeException, BaseException, object)` —
comprobado en el intérprete. Por tanto los `except Exception` de `etapa_drive`/`etapa_crm`
**no** se tragan las trampas `pull=lambda *a, **k: pytest.fail(...)`. Ese vector no existe
en este diff, y el comentario de la fixture `dobles` (líneas 69-73 del e2e) que lo explica
es correcto.

**SIN VERIFICAR:** el orden aleatorio (no hay `pytest-randomly` en este intérprete). Aviso
de que `test_f15_bis` (`test_apertura_v1_etapas.py:47-52`) muta un global de módulo por
asignación directa en vez de `monkeypatch`; el `try/finally` lo restaura, pero no puedo
medir su comportamiento bajo reordenación.

### Tabla de mutantes (17 vivos / 21)

| id | fichero:línea | mutación | rojos |
|---|---|---|---|
| a | `scripts/abrir_caso.py:495` | `vacios == len(links)` → `vacios` | **VIVO** |
| b | `scripts/sala_maquina.py:923` | `return status_atomizacion` → `return None` | **VIVO** |
| c | `scripts/abrir_caso.py:963` | `if previa is not None and previa.sin_cerrar():` → `if False:` | **VIVO** |
| d2 | `scripts/abrir_caso.py:968` | `estado_v1.abrir(...)` → `RondaV1(...)` (no escribe) | **VIVO** |
| e | `scripts/abrir_caso.py:972` | `estado_v1.cerrar(...)` → `pass` | **VIVO** |
| f | `scripts/abrir_caso.py:999` | `Exit(codigo_de_salida(resultado_v1.estado))` → `Exit(0)` | **VIVO** |
| g | `scripts/abrir_caso.py:998` | `_informar_v1(resultado_v1)` → `pass` | **VIVO** |
| h | `scripts/abrir_caso.py:993-996` | handler `(CaseBusy, MutexPerdido)` → `raise` | **VIVO** |
| i | `scripts/abrir_caso.py:151` | `pull_drive_ev(..., force=force)` → `force=False` | **VIVO** |
| j | `scripts/abrir_caso.py:186` | `return res` → `return None` | **VIVO** |
| k | `scripts/abrir_caso.py:975` | añade `sys.exit(0)` en la rama v1, dentro del mutex | **VIVO** |
| n | `core/apertura_v1_estado.py:76-88` | quita `fsync` y el `except BaseException` de limpieza | **VIVO** |
| p | `scripts/abrir_caso.py:445` | el barrido previo valida solo `links[:1]` | **VIVO** |
| q | `scripts/abrir_caso.py:521` | `codigo="atomizacion_parcial"` → otro código | **VIVO** |
| r | `scripts/abrir_caso.py:470` | `str(link["id"])` → `link["id"]` | **VIVO** |
| s | `scripts/abrir_caso.py:969-970` | `hasta=hasta` → `hasta=None` | **VIVO** |
| u | `scripts/abrir_caso.py:512` | `apply(case_id=ident.case_id)` → `apply(case_id="W-OTRO-CASO")` | **VIVO** |
| d | `:968` | `ronda = av1.EstadoV1` | muere (por crash, no por contrato) |
| l | `:958` | `if modo == "v1":` → `if modo in ("v1",):` | muere (F25) |
| o | `:587` | `secuencia_v1` escribe un fichero por llamada | muere (punto fijo) |
| t | `:722` | guarda de `--hasta` → `if False:` | muere (F23) |

Los supervivientes se confirmaron además contra una suite ampliada
(`test_abrir_caso.py`, `test_abrir_caso_cli.py`, `test_intake_drive.py`, y para `b` los 12
ficheros `test_sala_maquina*`/`test_split_sala_maquina_e2e`): siguen vivos.

---

## Hallazgos

### L6-01 — CRÍTICO: el retorno de `apply()`, única costura de la etapa 3, no lo prueba nadie

**Qué.** `scripts/sala_maquina.py:923` añade `return status_atomizacion`. Es **el** dato por
el que `etapa_sala_maquina` decide entre `hecha`, `hecha`+pendiente y `fallo`
(`scripts/abrir_caso.py:508-532`). Mutante `b`: `return None`. **Cero rojos** en los 7
ficheros del encargo y **cero** en los 12 ficheros `test_sala_maquina*`.

**Dónde.** Producción `scripts/sala_maquina.py:923`. Los tests que *parecen* cubrirlo:
`test_apertura_v1_etapas.py:202-217` (`test_f10_f12...`, `test_f11...`) inyectan
`correr=lambda: status`, o sea **construyen el valor que la costura debería traer**;
`test_apertura_v1_e2e.py:88-96` dobla `sala_maquina.apply` entero y devuelve `"ok"` a mano.
Los tres tests nuevos de `test_sala_maquina_cableado_atomize.py:455-494` contratan
`_atomizar_correo`, que es el **eslabón anterior**.

**Por qué importa.** Con `apply` devolviendo `None`, V1 informaría siempre
`"OCR hecho; sin correo que atomizar"`: la atomización parcial nunca levantaría
`atomizacion_parcial` y una atomización en `fallo` nunca dejaría V1 `bloqueado` — el §24 D4
completo, muerto en producción, con F10/F11/F12 en verde. Es exactamente el modo de fallo
que el propio diff dice remediar («el consumidor que lee el último `atomizado_email` del log
no puede saber si es suyo»): se arregló el productor y el consumidor, y **la costura entre
ellos quedó sin contrato**.

**Cómo lo comprobé.** Mutante `b` ejecutado dos veces (suite del encargo y suite
`sala_maquina` ampliada). Además `grep -rn` en `tests/` no encuentra **ninguna** aserción
sobre el valor de retorno de `apply(`.

**Qué haría falta.** Un test que llame a `sala_maquina.apply` de verdad (con `sm.ejecutar`
doblado, como ya hace `test_evento_real_es_valido_y_serializable`) y afirme
`apply(...) == "ok"` / `"parcial"` / `"fallo"` / `None`. Y en el e2e, doblar `sm.ejecutar` en
vez de `apply`, para que el adaptador *y* la costura entren en el camino.

---

### L6-02 — CRÍTICO: `force` no llega a `pull_drive_ev`, y la propiedad HA-03 solo se prueba en el llamador

**Qué.** `scripts/abrir_caso.py:151` reenvía `force=force` a `intake_drive.pull_drive_ev`.
Mutante `i`: `force=False`. **Cero rojos**, también contra `test_intake_drive.py`,
`test_abrir_caso.py` y `test_abrir_caso_cli.py`.

**Dónde.** `scripts/abrir_caso.py:151`. El test que dice cubrirlo,
`test_apertura_v1_etapas.py:57-66` (`test_f16_en_v1_el_pull_consulta_en_cada_ronda`), afirma
`visto["force"] is True` sobre un **doble de `_intake_drive_ev`**; el e2e
(`test_apertura_v1_e2e.py:114, 151, 172`) afirma sobre el mismo doble. El mutante F16 del
arnés del autor muta el **argumento de la llamada a `_intake_drive_ev`**, no su reenvío.

**Por qué importa.** El «falso punto fijo» que la spec prohíbe es que la ronda **no consulte
Drive**. Con `force=False` en la línea 151, `pull_drive_ev` respeta el marcador `.pulled` y
la consulta remota no se hace — y `res.skipped` volvería `True`, que `etapa_drive` traduce a
`fallo`… en la segunda ronda. En la primera, silencio. Los tests contratan la mitad de la
cadena a la que se le añadió el parámetro, y no el punto donde se consume.

**Cómo lo comprobé.** Mutante `i`, dos suites.

**Qué haría falta.** Espiar `intake_drive.pull_drive_ev` (monkeypatch con captura de `force`)
y llamar a `_intake_drive_ev` de verdad. Es un test de tres líneas.

---

### L6-03 — CRÍTICO: el `return res` nuevo de `_intake_drive_ev` no está contratado, y el doble tapa exactamente eso

**Qué.** El diff cambia la firma de `_intake_drive_ev` a `-> DriveIntakeResult` y añade
`return res` (`scripts/abrir_caso.py:183-186`). Mutante `j`: `return None`. **Cero rojos**.

**Dónde.** `scripts/abrir_caso.py:186`. `test_f15_bis_el_camino_POR_DEFECTO_pasa_por_la_custodia`
(`test_apertura_v1_etapas.py:36-54`) **sustituye** `cli._intake_drive_ev` por `_falso`, que sí
devuelve un `DriveIntakeResult`; la fixture `dobles` del e2e hace lo mismo.

**Por qué importa.** Con `None`, `etapa_drive` revienta en `res.errors` → `AttributeError` →
capturado por `except Exception` → **la etapa Drive de V1 falla siempre**, y toda la suite
sigue verde. El test que se añadió *precisamente* para cubrir el camino por defecto («sin
esto, un mutante que cambiara el default sobreviviría») cubre **qué función se llama**, no
**qué devuelve**: dos mitades del mismo contrato, una contratada y la otra no.

**Cómo lo comprobé.** Mutante `j`, dos suites.

**Qué haría falta.** Un test de `_intake_drive_ev` con `pull_drive_ev` doblado que afirme
`isinstance(res, DriveIntakeResult)` y que el `target_dir` devuelto es el del pull. Cubre a
la vez L6-02 y L6-03.

---

### L6-04 — CRÍTICO: `--hasta` no llega a la secuencia, y ningún test lo nota

**Qué.** Mutante `s`: en `main`, `secuencia_v1(..., hasta=hasta)` → `hasta=None`.
**Cero rojos**.

**Dónde.** `scripts/abrir_caso.py:969-970`. Lo que sí se prueba: la **validación** del
vocabulario (`test_apertura_v1_cableado.py:74-85`, mutante `t` muere) y la **semántica** de
`hasta` dentro de `secuenciar` (`test_apertura_v1_secuenciador.py:89-95`,
`test_apertura_v1_e2e.py:168-172`, siempre pasándolo a mano). Nadie prueba el tramo
CLI → secuencia.

**Por qué importa.** Es un flag de operador que puede quedar **inerte**: `--hasta drive`
validaría, pasaría la puerta, y correría las tres etapas. Y la peor variante es
silenciosa — el informe diría `no_ejecutadas=()` y el operador leería una corrida completa
donde pidió parar. Es el patrón «guarda que valida un valor que después nadie usa», con la
validación contratada y el uso no.

**Cómo lo comprobé.** Mutante `s`.

**Qué haría falta.** `test_abrir_caso_modo_v1.py` ya dobla `secuencia_v1`: basta con que el
doble **capture `kw`** y el test afirme `kw["hasta"] == "drive"` invocando el CLI con
`--hasta drive`. El doble actual (`_secuencia_falsa(ident, case_dir, **kw)`) descarta `kw`.

---

### L6-05 — MEDIA: el estado durable se prueba contra su propia API y nunca contra su único llamador

**Qué.** Tres mutantes vivos sobre el cableado de `core/apertura_v1_estado.py` en `main`:

- `c` — `if previa is not None and previa.sin_cerrar():` → `if False:`: **el AVISO de ronda
  no cerrada desaparece** y nada se pone rojo.
- `d2` — `estado_v1.abrir(...)` → construir un `RondaV1` sin escribir a disco: **nada se
  pone rojo** (el mutante `d`, que hacía `ronda = av1.EstadoV1`, sí muere, pero por
  `TypeError` en `dataclasses.replace`: muere por crash, no por contrato).
- `e` — `estado_v1.cerrar(...)` → `pass`: **la ronda nunca se cierra en disco** y nada se
  pone rojo.

**Dónde.** `scripts/abrir_caso.py:962-974`. Los tests de
`test_apertura_v1_estado.py` son correctos pero **unitarios sobre el módulo**:
`test_f28_una_ronda_sin_cerrar_se_detecta` (línea 31) llama a `est.abrir` y `est.leer` él
mismo. `test_abrir_caso_modo_v1.py::test_v1_con_los_flags_correctos_pasa_la_puerta` es el
único que atraviesa `main` en modo v1, y no mira el fichero `_apertura_v1.json`.

**Por qué importa.** El docstring del módulo dice que lo que aporta es «que una ronda muerta
a mitad se DETECTE, en vez de que la siguiente corrida trate su salida como buena». Con `c`
vivo, la detección existe en el módulo y **no ocurre** en el producto; con `e` vivo, toda
ronda queda abierta para siempre. Es la propiedad entera del Task 8b, y su verificación se
detiene en el borde del módulo.

**Cómo lo comprobé.** Mutantes `c`, `d2`, `e`; los tres confirmados también contra la suite
ampliada.

**Qué haría falta.** Un test sobre `main` en modo v1 (la infra ya existe en
`test_abrir_caso_modo_v1.py`) que: (1) siembre un `_apertura_v1.json` sin cerrar y afirme el
`[AVISO]` en `res.output`; (2) tras una invocación limpia, lea el fichero y afirme
`terminada is not None` y `etapas == {...}`.

---

### L6-06 — MEDIA: el «punto fijo MATERIAL» compara un árbol de un solo fichero, y es el de la fixture

**Qué.** `test_apertura_v1_e2e.py:131-152` sustituye la comparación de estados por una
comparación del árbol, con el docstring «Se compara el arbol». **El árbol que compara tiene
exactamente un fichero: el `_caso.md` que escribió la fixture.** Medido:
`antes=[('00_Input/_caso.md', 252)] despues=[('00_Input/_caso.md', 252)]`.

**Dónde.** `test_apertura_v1_e2e.py:134-137` (`foto()`) y `:145` (`assert tras_1 == tras_2`).
La causa es la fixture `dobles` (`:66-98`): `_intake_drive_ev`, `pull_expediente_v2` y
`apply` están doblados **por encima de toda escritura**, así que la secuencia produce cero
artefactos y `tras_1 == tras_2` es una tautología sobre el fichero de la fixture.

**Por qué importa.** No es una aserción inerte —el mutante `o`, que hace escribir un fichero
por llamada, la mata— pero **no puede detectar la no-idempotencia de nada bajo prueba**,
porque nada bajo prueba escribe. El criterio 14 de la spec («punto fijo») queda con la misma
cobertura que en la rev. 1: se cambió la aserción y no la condición que la hacía vacía. Las
aserciones que sí muerden en ese test son las de conteo y las de `force`/`element`, que ya
están en el test de arriba.

**Cómo lo comprobé.** Sonda ejecutada (`foto()` impreso) + mutante `o`.

**Qué haría falta.** Que al menos un doble escriba: p.ej. que `_intake` de la fixture
materialice dos ficheros en `target_dir` y que `_apply` toque un `01_Procesado/`. Sin eso, o
se baja al doble de `sm.ejecutar`, la palabra «MATERIAL» del nombre no está respaldada.

---

### L6-07 — MEDIA: F25 vigila `ast.Raise`, no «salir del proceso»; `sys.exit` pasa

**Qué.** `test_f25_la_rama_v1_no_sale_del_proceso_dentro_del_bloque_de_mutex`
(`test_apertura_v1_cableado.py:94-129`) busca nodos `ast.Raise` en el cuerpo de la rama
`modo == "v1"`. Mutante `k`: añadir `import sys as _s; _s.exit(0)` justo después de
`registrar_cierre_v1`, dentro del `with`. **Cero rojos.**

**Dónde.** `test_apertura_v1_cableado.py:125-129`.

**Por qué importa.** El defecto real es *salir del proceso* con el lease en la mano; `raise
typer.Exit` es **un ejemplo** de eso, y el test contrató el ejemplo. `sys.exit` produce el
mismo `SystemExit` (que además tampoco es `Exception`, así que atraviesa igual el
`case_mutex.tomado`) y no se ve. Segundo hueco de la misma clase, este sin ejecutar por
requerir refactor: si el cuerpo de la rama se extrae a un helper (`_correr_v1(...)`), el
`if modo == "v1":` sigue existiendo, su cuerpo sigue sin `Raise`, el test **pasa**, y el
`raise typer.Exit` vive dentro del helper.

**Lo que sí aguanta:** la guarda anti-vacío. Mutante `l` (`if modo == "v1":` →
`if modo in ("v1",):`) pone rojo `test_f25` con el mensaje «no se encuentra la rama». El test
**no puede quedar vacío en silencio**, que era la pregunta 6 del encargo. Es frágil ante
refactores inocuos, pero falla en voz alta, no en verde.

**Cómo lo comprobé.** Mutantes `k` y `l`.

**Qué haría falta.** Ampliar la búsqueda a las salidas por llamada (`sys.exit`, `os._exit`,
`typer.Exit` en cualquier posición) o —mejor— sustituir el proxy estructural por un test de
comportamiento: forzar `MutexPerdido` al salir del bloque y afirmar `exit_code != 0`. Eso
cubriría además L6-08 y L6-11.

---

### L6-08 — MEDIA: `traducir_fallo_de_mutex` no tiene llamadores en producción; el handler que sí corre no está probado

**Qué.** `grep -rn "traducir_fallo_de_mutex" --include=*.py` fuera de `tests/` devuelve
**una sola línea: su propia definición** (`scripts/abrir_caso.py:557`). `main` no la usa: la
traducción real es el `except (CaseBusy, MutexPerdido)` inline de
`scripts/abrir_caso.py:993-996`. Mutante `h` (handler → `raise`, o sea la traza que el
docstring dice evitar): **cero rojos**.

**Dónde.** Función muerta: `scripts/abrir_caso.py:557-568`. Tests que la contratan:
`test_apertura_v1_cableado.py:132-146` (`test_f26...` y
`test_traducir_fallo_de_mutex_deja_pasar_lo_que_no_es_de_exclusion`). Mutante F26 del arnés
del autor: también sobre la función muerta.

**Por qué importa.** Tres tests y un mutante «muerto por su frontera» miden una función que
nadie ejecuta, mientras la costura equivalente en producción no tiene contrato. Es el patrón
«pieza construida que nadie encadena», con la agravante de que aquí la pieza **fue
reemplazada** por código inline y su prueba se quedó apuntando a la pieza. Un lector del
informe de mutación concluye que «CaseBusy se traduce a bloqueado» está verificado; lo
verificado es un helper sin llamadores.

**Cómo lo comprobé.** `grep` (arriba) + mutante `h`, dos suites.

**Qué haría falta.** Decidir una de dos: cablear `main` a `traducir_fallo_de_mutex` (y
entonces los tests valen), o borrarla y probar el handler invocando el CLI con
`mutex_sesion.sostenido` doblado para lanzar `CaseBusy`, afirmando `exit_code == 1` y el
`=== Apertura: bloqueado ===` en `res.output`.

---

### L6-09 — MEDIA: las dos propiedades multi-expediente del CRM están documentadas y sin probar

**Qué.** `etapa_crm` documenta dos propiedades que solo existen con **≥2 links**:

1. `scripts/abrir_caso.py:443-444`: «Las tres puertas se comprueban ANTES de pullar nada: con
   dos expedientes vinculados, descubrir el segundo invalido a mitad dejaria el primero ya
   escrito». Mutante `p` (el barrido previo valida solo `links[:1]`): **cero rojos**.
2. `scripts/abrir_caso.py:493-495`: «`saltada` solo si TODOS lo fueron: un expediente vacio
   junto a otro con documentos es una etapa hecha». Mutante `a`
   (`vacios == len(links)` → `vacios`): **cero rojos**.

**Dónde.** Todas las fixturas usan **exactamente un link**: `_meta()` en
`test_apertura_v1_etapas.py:105-110` construye una lista de uno, y el `_caso.md` del e2e
(`test_apertura_v1_e2e.py:35-39`) también.

**Por qué importa.** Con un solo link las dos reglas son indistinguibles de sus mutantes, así
que la suite no puede decir nada sobre ellas. Y el caso de 2+ expedientes vinculados no es
hipotético: el `_caso.md` admite una lista y `etapa_crm` está escrita para recorrerla. La
segunda propiedad, mal, produciría `saltada` en una etapa que sí escribió documentos, y ese
token viaja al evento `apertura_v1_terminada` y al `_apertura_v1.json`.

**Cómo lo comprobé.** Mutantes `p` y `a`.

**Qué haría falta.** Dos tests con `leer_meta` devolviendo dos links: (a) segundo con
`element` inválido → afirmar que el doble de `pull` **no** fue llamado ni una vez (contador,
no `pytest.fail`, para que la aserción sea sobre el efecto); (b) uno vacío + uno con
documentos → `estado == "hecha"`.

---

### L6-10 — MEDIA: el doble del OCR tiene contador pero no espía de valor, y el caso puede ser otro

**Qué.** Mutante `u`: `sala_maquina.apply(case_id=ident.case_id)` →
`apply(case_id="W-OTRO-CASO")`. **Cero rojos.**

**Dónde.** `scripts/abrir_caso.py:512`. La fixture `dobles`
(`test_apertura_v1_e2e.py:88-90`): `def _apply(case_id=None, **kw): llamadas["ocr"] += 1;
return "ok"` — **descarta `case_id`**. Y el docstring del fichero (`:8-9`) afirma «cada doble
lleva ESPIA, porque un test que no comprueba que llamo no distingue “funciono” de “no se
ejecuto”».

**Por qué importa.** El espía existe para `force` (drive) y `element` (crm), y para el OCR se
quedó en contador. Un contador responde «se llamó»; no responde «se llamó **sobre este
caso**». El mutante que sobrevive apunta el OCR de una apertura al expediente equivocado: es
la clase de defecto más caro del repo (escritura sobre la copia de otro caso) y el e2e lo
deja pasar mientras su cabecera dice lo contrario.

**Cómo lo comprobé.** Mutante `u`.

**Qué haría falta.** `visto["case_id"].append(case_id)` en `_apply` y
`assert dobles["_visto"]["case_id"] == [CASE_ID]` en los tests que ya afirman `force` y
`element`.

---

### L6-11 — MEDIA: ni el informe en pantalla ni el código de salida se comprueban a través de `main`

**Qué.** Mutante `g` (`_informar_v1(resultado_v1)` → `pass`): **cero rojos**. Mutante `f`
(`Exit(codigo_de_salida(resultado_v1.estado))` → `Exit(0)`): **cero rojos**.

**Dónde.** `scripts/abrir_caso.py:589-601` (`_informar_v1`, sin ningún test) y `:999`.
`test_f14_un_resultado_bloqueado_sale_con_codigo_no_cero`
(`test_apertura_v1_cableado.py:88-91`) prueba `codigo_de_salida` **como función pura**, no
como comportamiento del CLI.

**Por qué importa.** `_informar_v1` es el único sitio donde el operador ve los pendientes, la
parada y las etapas que no corrieron; es la mitad de la entrega dirigida a un humano y nadie
la lee en ningún test — el modo de fallo de la aserción débil, aquí en su versión extrema
(aserción cero). Y con `f` vivo, «`bloqueado` sale distinto de 0», que es la propiedad por la
que existe `codigo_de_salida`, no está verificada en el único punto donde produce un efecto:
un script que encadene `abrir_caso` leería 0 sobre una apertura bloqueada.

**Cómo lo comprobé.** Mutantes `g` y `f`, dos suites.

**Qué haría falta.** En `test_abrir_caso_modo_v1.py`, con el doble de `secuencia_v1`
devolviendo un `ResultadoV1` `bloqueado`: afirmar `res.exit_code == 1` y que `res.output`
contiene `=== Apertura V1: bloqueado ===`, la línea de cada etapa y la de cada `PENDIENTE`.

---

### L6-12 — MEDIA: el pendiente de atomización parcial se comprueba con `bool()`, y su texto dice algo que el código no hace

**Qué.** `test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente`
(`test_apertura_v1_etapas.py:202-211`) cierra con `assert bool(r.pendientes) is hay_pendiente`
— exactamente el `assert bool(...)` que el encargo señala. Mutante `q` (cambiar
`codigo="atomizacion_parcial"` por otro código): **cero rojos**.

**Y hay un segundo defecto que la aserción débil tapa.** El `detalle` del pendiente
(`scripts/abrir_caso.py:522-525`) dice: «La atomizacion publico con errores **o con poda
omitida**». `scripts/sala_maquina.py:618-619` calcula
`status = "fallo" if not publicado else "parcial" if errores else "ok"`: **`poda_omitida` no
participa**. Un report con `poda_omitida=True` y `errores=[]` da `"ok"` → ningún pendiente.
El texto que lee el operador afirma una cobertura que el código no tiene.

**Dónde.** `test_apertura_v1_etapas.py:211`; `scripts/abrir_caso.py:520-526`;
`scripts/sala_maquina.py:618-619`.

**Por qué importa.** El `codigo` es lo que viaja al evento `apertura_v1_terminada`
(`registrar_cierre_v1` serializa solo `p.codigo`) y a `_informar_v1`. Es el único dato
durable del pendiente y no está contratado; el `detalle` es lo único que el operador lee y no
está contratado **ni es cierto**. Los códigos hermanos (`crm_documentos_fallidos`,
`crm_gestor_vacio`, `crm_sin_expediente`) sí se afirman por `codigo` en el mismo fichero:
la asimetría no es de diseño, es un olvido.

**Cómo lo comprobé.** Mutante `q` + lectura de las dos funciones.

**Qué haría falta.** `assert [p.codigo for p in r.pendientes] == ["atomizacion_parcial"]` (el
idiom que ese mismo fichero ya usa en la línea 182), y corregir el `detalle` o hacer que
`poda_omitida` cuente para `parcial`.

---

### L6-13 — MEDIA: la atomicidad de `_escribir` se contrata con un espía de llamada, no con la propiedad

**Qué.** `test_f27_la_escritura_es_atomica_y_lleva_id_de_ronda`
(`test_apertura_v1_estado.py:16-28`) afirma `assert reemplazos, "la escritura no paso por
os.replace"` — que la función **fue llamada**. Mutante `n`: quitar `fh.flush()`, `os.fsync` y
todo el `except BaseException: unlink(tmp); raise`, dejando solo `write` + `replace`.
**Cero rojos.**

**Dónde.** `core/apertura_v1_estado.py:76-88`; test en
`test_apertura_v1_estado.py:16-28` y `:63-67`.

**Por qué importa.** El docstring de `_escribir` reclama tres propiedades y el test contrata
una parcialmente: (1) `os.replace` se llamó — sí, por espía; (2) no queda temporal — solo en
el camino **de éxito**, como dice el propio nombre de `test_no_queda_temporal_tras_una_
escritura_correcta`; (3) fsync — nada. El `except BaseException` existe para el camino de
fallo, que es el único que justifica su existencia, y no hay ni un test que lo recorra. Este
repo tiene precedente de espiar el fsync (`test_append_event_invoca_fsync_por_cada_escritura`
en `tests/test_intake_log.py`), así que el estándar interno está por encima de lo entregado.

**Cómo lo comprobé.** Mutante `n`.

**Qué haría falta.** Espiar `os.fsync` como se hace con `os.replace`; y un test que haga
fallar `os.replace` (monkeypatch a `OSError`) y afirme dos cosas: que **no queda temporal**
y que el fichero **anterior sigue íntegro**.

---

### L6-14 — BAJA: la coerción `str(link["id"])` no está probada

Mutante `r` (`str(link["id"])` → `link["id"]`): **cero rojos**. Todas las fixturas dan el id
ya como cadena (`"648"` en `test_apertura_v1_etapas.py:106`, `id: '648'` entrecomillado en el
YAML del e2e, `:37`). Un `_caso.md` real con `id: 648` sin comillas llegaría a
`pull_expediente_v2` como `int`. La coerción se escribió por algo y nada la sostiene; un test
con `_meta()` y `link["id"] = 648` afirmando `visto["expediente_id"] == "648"` la cierra.

---

### L6-15 — BAJA: «28/28 mutantes muertos» es una autoatestación cerrada

`tests/_mutantes_plan5.py` es un buen arnés —mide por JUnit XML, exige conjunto **exacto** de
nodeids, detecta «mata de menos» y «mal apuntado», y aborta si la base ya está roja— y su
resultado es real: lo corrí y da 28/28. Pero mide la suite contra una lista de fronteras
escrita por el autor de la suite, así que su cifra **no es una tasa de mutación**: es «los 28
casos que se me ocurrieron están cubiertos». Cuatro de mis supervivientes caen sobre
fronteras que el arnés **nombra**, mutando el otro extremo de la misma costura: F16 vs. `i`,
F25 vs. `k`, F27 vs. `n`, F10/F12 vs. `b`. Si la cifra 28/28 va a entrar en la bitácora,
debería ir con esa acotación al lado, o con el `SUITE` ampliado a
`test_abrir_caso_modo_v1.py` y `test_sala_maquina_cableado_atomize.py` — que hoy quedan
fuera del conjunto contractual y son justo donde vive el cableado a `main`.

**Detalle menor del arnés:** `_rojos()` deriva el fichero de `classname` partiendo por `.`;
para un test dentro de una clase daría `tests/test_x/TestFoo.py` y ningún conjunto
coincidiría. Hoy no muerde (ninguno de los 5 ficheros del `SUITE` agrupa tests en clases),
pero es una bomba de relojería para el primer test que se meta en una clase.

---

### Caminos del código nuevo que ningún test recorre (punto 7)

Además de los anteriores:

- `_atomizar_correo` → `report.publicado is False` ⇒ retorno `"fallo"`. Existe
  `test_evento_declara_que_no_publico`, pero afirma sobre el **evento**, no sobre el retorno
  (`scripts/sala_maquina.py:618`).
- `traducir_pull_crm`: ninguna combinación que ejerza la **precedencia** entre ramas
  (p.ej. `documents_failed=2` **y** `documents_total_crm=0`, que hoy da `hecha`).
- `etapa_sala_maquina` con `typer.Exit(code=0)`: `test_un_typer_exit_cero_no_es_fallo`
  (`test_apertura_v1_etapas.py:231-238`) afirma solo `estado == "hecha"` — un campo de la
  estructura. El `detalle` resultante dice «sin correo que atomizar», que es falso para un
  OCR que salió limpio, y el test no puede verlo.
- `apertura_v1_estado.leer`: la rama `OSError` del `except` y la rama `etapas` no-dict.
- `ResultadoV1` con `hasta` **y** un `fallo` anterior a la parada (`parada` queda `None`).
- El evento `apertura_v1_terminada` no lleva `no_ejecutadas`, y el campo `parada` que sí
  lleva no se afirma en ningún test.

### Aserciones débiles que hoy no muerden, pero que no dicen lo que parecen

- `test_apertura_v1_cableado.py:71`: `assert "crm" in " ".join(p.codigo for p in r.pendientes)`
  — substring; pasaría con `crm_sin_expediente`. La línea 70 (`r.no_ejecutadas == (...)`) es la
  que hace el trabajo.
- `test_apertura_v1_etapas.py:228`: `assert "2" in r.detalle` — el `"2"` casaría con cualquier
  cifra que contenga un 2.
- `test_apertura_v1_etapas.py:21-33` (`test_f15_...`): su nombre y docstring afirman la
  propiedad «pasa por la custodia y no por el pull a pelo», y el test pasa `intake=`
  explícito, así que no dice nada de eso. El autor lo reconoce en `f15_bis`; el nombre del
  primero sigue prometiendo lo que no entrega.

---

## Lo que aguanta

Lo comprobé y no cede:

- **La fixture del e2e está anclada al lector real, con guardarraíl propio.**
  `test_la_fixture_es_legible_por_el_lector_real` (`test_apertura_v1_e2e.py:45-50`) llama a
  `case_locator.read_case_meta` de verdad, y el `_caso.md` anida las claves bajo `meta:`,
  que es lo que `case_locator.py:222` devuelve. Es la reparación correcta del modo de fallo
  que el propio docstring narra (rev. 1 escribiendo en el nivel superior, `{}` devuelto, e2e
  verde sin tocar el CRM). No es un proxy: si la fixture se rompe, el guardarraíl lo dice
  antes de que los demás tests mientan.
- **La razón por la que las aserciones viven FUERA de los dobles es correcta y medida.**
  El comentario de `test_apertura_v1_e2e.py:69-73` es exacto: `etapa_drive`/`etapa_crm`
  capturan `Exception`, así que un `assert` dentro del doble se convierte en un `fallo` de
  etapa. Registrar en `visto` y afirmar después es la solución buena. Y las trampas
  `pytest.fail` **sí** funcionan, porque `Failed` es `BaseException` (verificado en el
  intérprete), no porque el autor tuviera suerte.
- **`test_f25` no puede quedar vacío en silencio.** El `assert ramas_v1` muerde: mutante `l`
  lo pone rojo con un mensaje que nombra lo que falta. La preocupación explícita del encargo
  sobre este test está cubierta; lo que falla es el alcance de la búsqueda (L6-07), no su
  robustez frente al vacío.
- **La comparación por estructura y no por `ast.dump` está bien argumentada y es correcta.**
  `_es_rama_v1` (`test_apertura_v1_cableado.py:110-119`) evita la búsqueda mutilada que
  describe su comentario.
- **`test_f7` afirma por igualdad de diccionario completo**
  (`visto == {"expediente_id": "648", "element": "extrajudiciales"}`), no por campo suelto:
  el mutante F7 no tiene por dónde escapar.
- **La migración de `test_v1_con_los_flags_correctos_pasa_la_puerta`** (HA-11) es real: el
  doble anterior de `_despachar_intake` había quedado inerte en modo v1, y el nuevo test
  afirma `"secuencia" in llamadas`, afirma `"crm" not in llamadas`, y pone una trampa en
  `_intake_drive_ev`. Lo que le falta es capturar los `kw` (L6-04), no la estructura.
- **`test_una_corrida_completa_toca_TODAS_las_fases_de_v1`** y
  `test_e2e_la_secuencia_recorre_las_tres_etapas_y_las_LLAMA` sí prueban que la
  construcción **por defecto** de `secuencia_v1` produce las tres etapas con los nombres de
  `ETAPAS_V1` y que las tres se ejecutan, con contadores. Ese tramo está bien cerrado.
- **La corrección del contador de `INTAKE_EVENTS`** («decía 27 y eran 33») y la subida
  declarada de `TECHO_CENSO` 83→87 con la explicación de por qué **no** se movió
  `registrar_cierre_v1` a un módulo fuera de `PRODUCTORES`: es la disciplina correcta y está
  escrita donde toca.
- **El arnés de mutación, como pieza de ingeniería**, es netamente mejor que el de la rev. 1:
  conjunto exacto en vez de booleano, JUnit XML en vez de resumen, y dos predicciones del
  autor corregidas *al medir* y documentadas como tales (comentarios de F7). El problema es
  el alcance de su lista, no su mecánica.
<!-- informe-literal:fin:v4nt -->

## 2. Evidencia verificada por el adjudicador

Los hallazgos se contrastaron contra el codigo, no contra los informes. Lo comprobado por
mi cuenta, con la fuente:

- **El critico (L2-01) CONFIRMADO en dos lineas.** `core/sync_sudespacho.py:1455` hace
  `errors.append(...)` cuando el gestor documental esta vacio, y `:1546-1547` incrementa
  `documents_failed` **en el mismo bloque** que su `errors.append`. Mi tabla comprobaba
  `errors` primero: las dos ramas siguientes eran inalcanzables.
- **El fichero de control (L5-01/L4-06/L4-07) CONFIRMADO, y la frontera era mas ancha que
  los dos ejemplos.** Existe un registro **canonico** —`config.INTAKE_CONTROL_FILES`, cuyo
  comentario dice «Lista UNICA»— y yo declare el fichero en **ninguno** de los cuatro
  sitios que clasifican `00_Input`: ese registro, `sala_maquina._IGNORAR`,
  `config.MERGE_EXCLUSIONS` y el carve-out del plugin `expedientes-xl`. El cuarto lo cazo
  un guard del repo, no yo.
- **El registro durable dentro del mutex (L3-01/L4-05/L5-04, cuatro lentes) CONFIRMADO** por
  lectura de `core/casos/case_mutex.py:615-659`.
- **La reanudacion documentada (L3-02) CONFIRMADA:** el help prometia «volver a lanzar la
  misma orden» y la puerta prohibe `--force` sin `--case-id` (`scripts/abrir_caso.py:748`),
  asi que la via principal muere en `ColisionCaso`.
- **El codigo muerto (L2-04/L3-03/L5/L6-08, cuatro lentes) CONFIRMADO:**
  `traducir_fallo_de_mutex` tenia tres tests y **cero llamadores de produccion**.
- **HA-07 remediado en el sitio equivocado (L3-04) CONFIRMADO:** 8 `raise typer.Exit` en las
  funciones que el modo `libre` invoca desde dentro del bloque, mas el del `--dry-run`.

Lo **parcialmente refutado**, y con la fuente delante: la poda de la atomizacion (HA-08 de
R-A, reaparecida aqui) esta **gateada en foto completa**
(`core/email_atomize/pipeline.py:204-220`), asi que el escenario de perdida que yo mismo
habia agravado es imposible en la via que importa.
