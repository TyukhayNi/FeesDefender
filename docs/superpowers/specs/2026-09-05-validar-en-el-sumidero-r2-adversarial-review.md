---
tipo: revision-adversarial
objeto: "diff del sumidero (MEJORAS #153/#154) + los puntos 2, 3 y 4 de los aprendizajes en codigo"
objeto_rev: "rama claude/aprendizajes-en-codigo, 9ec96f7 -> eee9a7e"
commit: "eee9a7e"
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: t3xk
sha256_informe: 2f38d8f05586859800ca7b03fd447095b7624a28dda020b36d78aa090d60eaf7
adjudicado_en: docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md §8
adjudicador: Claude Code
independencia_adjudicacion: plena
estado_remediacion: remediado
---

> **Acta de revisión adversarial R2 sobre el DIFF.** El §0 es el mandato literal, el §1
> conserva la voz del revisor sin una coma cambiada, el §2 es la evidencia que verifiqué por
> mi cuenta y el §3 mi adjudicación.
>
> **Dónde vive la adjudicación:** en el **§8 del propio diseño**
> (`2026-09-05-validar-en-el-sumidero-design.md`, rev. 3), que es el documento que la decisión
> modificó. Aquí va **la voz del revisor**, que es para lo que sirve el acta: yo soy la parte
> revisada, así que sin el original archivado nadie puede contrastar **qué dijo el revisor**
> con **qué decidí yo que dijo**.
>
> **Ronda 2 de 2.** El presupuesto de esta pieza son dos rondas —decide **dónde se deposita
> un expediente con PII**—: la R1 sobre el diseño
> (`…-r1-adversarial-review.md`, `NO-SHIP`, cinco hallazgos) y esta sobre el diff. **No hay
> tercera ronda sin que Nikolai la autorice expresamente**, y no la pido: los seis hallazgos
> están remediados o registrados, y el techo existe justo para el argumento «la ronda
> anterior encontró algo», que nunca se agota.

## 0. Mandato, literal

<!-- El mandato no va cercado por el nonce: el guard G8 hashea SOLO el informe. Va aquí
     porque un hallazgo se juzga contra lo que se pidió, y el alcance de esta ronda lo fijó
     Codex mismo en una consulta previa, no yo. -->

```markdown
# MANDATO — Revisión adversarial R2 sobre el DIFF (FeesDefender)

## Higiene, primero

Tu directorio de trabajo debe contener **solo este `MANDATO.md`**. Si encuentras cualquier otro
fichero, **no lo leas** y decláralo en la primera línea de tu informe.

## Rol y contexto de autoridad

Eres el revisor adversarial. Tu trabajo es **encontrar defectos**, no aprobar. Claude adjudicará
cada hallazgo contra la fuente.

Nikolai (dueño del proyecto, abogado) duerme y ha pedido expresamente que las decisiones que le
consultaría a él se te consulten a ti. **Tú mismo autorizaste el alcance de este diff** en una
consulta previa: *«A — Autorizaría el alcance estrecho: corrige las entradas descritas sin tocar
de noche la gestión de copias operativas. Retira la garantía universal y registra las otras
puertas y la junction como pendientes explícitos, vinculados. La ronda 2 debe demostrar también
la contención, con pruebas que fallen al eliminarla.»*

**Esa última frase es tu propia condición, y comprobarla es parte de esta ronda.**

## Objeto

Dos copias congeladas en un directorio **hermano** al tuyo:

- `../rev-fd-sumidero-r2-0210-obj/base/` — ANTES (commit `9ec96f7`, `main`)
- `../rev-fd-sumidero-r2-0210-obj/head/` — DESPUÉS (commit `eee9a7e`)

No hay `.git`. **Calcula el `sha256` de lo que revises al abrir y al cerrar.** Si necesitas
escribir o ejecutar, copia a TU directorio; no escribas bajo el objeto.

## Esta es la R2. Lo que ya se adjudicó en la R1

La R1 fue sobre el **diseño** y dio `NO-SHIP` con cinco hallazgos, los cinco confirmados y
remediados en la rev. 2 del diseño. **No los repitas como nuevos**; sí compruébalos como
remediados:

1. **H-01** — se retiró la garantía universal. El diff **no** debe afirmar que cerrar
   `ensure_case` impide todo escape de `CASOS_ROOT`. `move_to_city`, `reservar_lote`/`caso_path`
   y la junction-en-hijo quedan como `MEJORAS #155`, `#156` y `#157`, sin tocar.
2. **H-02** — `ensure_case('')` ya no debe convertir la raíz en un expediente.
3. **H-03** — `ciudad` se valida contra `_CITY_NAMES`, el mismo conjunto que recorre `buscar`.
4. **H-04** — el límite (junction en un hijo) está **declarado** en el código y en el diseño.
5. **H-05** — la tabla de mutantes ejercita ahora la contención.

## Dónde atacar el diff

**El diff lleva dos bloques y conviene que sepas cuál es cuál, porque no compran lo mismo:**

- **Bloque 1 — la pieza de dos rondas** (esta es la segunda):
  `core/case_manager.py`, `core/utils.py`, `tests/test_ensure_case_sumidero.py`, el diseño
  rev. 2 y su acta.
- **Bloque 2 — tres mejoras de la sala de lectura, de UNA ronda, y ésta es su única ronda**:
  `core/sala_lectura.py`, `scripts/sala_lectura.py` y sus tres ficheros de test nuevos. No las
  ha revisado nadie todavía, así que **entran en alcance**. Son:
  - que «no hay residuo» y «hay residuo y no pude leerlo» dejen de decirse con la misma frase
    (nuevo `residuo_sin_texto`, tres estados en la CLI, y salida ≠ 0 en el segundo);
  - que `organizar` no cante éxito con cero acciones sobre material que sí existe (tres causas
    distinguidas: inconsistencia interna → `RuntimeError`; sin extensión relevante; input vacío);
  - un guard de comportamiento sobre los espejos MD en un caso mixto (canónico + partido +
    ciego).

Atácalos con el mismo criterio: ¿los tres estados son exhaustivos y disjuntos? ¿el
`RuntimeError` puede dispararse en un caso legítimo? ¿el guard mixto tiene algún fixture
anclado a lo que examina —yo ya me pillé uno así y lo corregí, mira si queda otro—?

1. **Tu condición, primero: ¿los tests fallan al eliminar la contención?** Suprime en tu copia
   la mitad léxica, luego la física, luego las dos, y dime **exactamente qué tests mueren en cada
   caso**. Si al quitar (b) o (c) la suite sigue verde, el diff no cumple lo que autorizaste.
2. **La contención física.** Camina el «ancestro existente más cercano» y resuelve los dos lados.
   ¿Hay un caso donde el bucle no termine, resuelva demasiado arriba, o dé un falso rechazo? UNC,
   `G:` (Drive Stream), unidad distinta, raíz inexistente, permisos.
3. **El orden.** La validación del `case_id` va **antes** de `destino_de_alta`. ¿Queda alguna
   escritura, log, evento o efecto **antes** de la guarda? ¿Puede quedar andamiaje parcial?
4. **¿Rompe algo legítimo?** `_Sin clasificar`, el modo local con `CASOS_ROOT` al Desktop, el
   *checkout* de un caso, `scripts/migrate_to_city_structure.py`, la vía `--force` del alta, los
   casos que ya existen bajo su ciudad. Corre la suite completa y dime qué se rompe.
5. **`exigir_componente_de_ruta`.** ¿Su composición sobre `exigir_sin_caracteres_de_ruta` deja
   algún hueco? Espacios, nombres reservados de Windows (`CON`, `NUL`, `AUX`, `COM1`), punto
   final, longitud, unicode que normalice a un separador.
6. **Los positivos.** Siete tests afirman que no se endureció de más. ¿Falta algún `case_id`
   legítimo que hoy se rechazaría? El catálogo real está en el objeto: `docs/` cita nombres, y
   los tests traen cuatro.
7. **¿Hay una QUINTA puerta?** La R1 encontró tres además de `ensure_case`. Si ves otra, es el
   hallazgo más valioso que puedes devolver.

## Puedes EJECUTAR

**Python de sistema:** `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`
(tiene `pytest`, `filelock`, `yaml`, `dotenv`, `typer`, `httpx`, `mcp`).

- `--basetemp` **relativo dentro de tu workdir** y **corto** (tu sandbox no puede crear
  `C:\t\...`; MAX_PATH tumba tests sanos).
- No tienes `pytest-randomly`: si algo exige dos semillas, declara **SIN VERIFICAR**.
- **Dos tests de `tests/test_crm_dedup_incertidumbre.py` fallan en base y en head** por falta de
  `SUDESPACHO_LEGACY_HOST` en `.env`. Defecto conocido y ajeno: no lo atribuyas.
- Las junctions de Windows se crean con `cmd /c mklink /J`. El diff se apoya en su
  comportamiento: sondearlo es bienvenido.

## Qué tiene que devolver tu informe

`INFORME.md` en tu directorio, con:

1. **Un hallazgo por bloque**: severidad (`CRÍTICO`/`ALTO`/`MEDIO`/`BAJO`), **defecto** o
   **decisión mal tomada**, fichero y línea, escenario concreto de fallo, y qué lo demostraría.
   Pega la salida si lo ejecutaste.
2. **La respuesta explícita a tu condición** (punto 1 de arriba), con la tabla de qué muere al
   suprimir cada mitad.
3. Lo revisado y **no** defectuoso, una línea por pieza.
4. Lo **no verificado**, y por qué.
5. Los `sha256` al abrir y al cerrar.
6. **En la ÚLTIMA línea, el veredicto, exactamente una de estas cuatro palabras y nada más:**

```
SHIP
SHIP-CON-RESERVAS
NO-SHIP
SIN-VERIFICAR
```

Si dudas entre dos, elige la más conservadora y explícalo arriba.
```

## 1. Informe recibido de Codex, sin modificar

**Ruta original:** `C:\t\rev-fd-sumidero-r2-0210\INFORME.md` ·
**`sha256`:** `2f38d8f05586859800ca7b03fd447095b7624a28dda020b36d78aa090d60eaf7` (canonicalizado: UTF-8, LF, un único salto final).

El digest del frontmatter se recomputa sobre el bloque de abajo en los guards **G8** de
`tests/test_docs_gobernanza.py`. Una desigualdad es **roja**, nunca un aviso.

<!-- informe-literal:inicio:t3xk -->
Higiene inicial conforme: el directorio de trabajo contenía únicamente `MANDATO.md`; no se encontraron ni leyeron otros ficheros previos.

# Revisión adversarial R2 — FeesDefender

Objeto congelado: `../rev-fd-sumidero-r2-0210-obj/base/` y `head/`, atribuidos por el mandato a `9ec96f7` y `eee9a7e`. No hay `.git`: acredito contenido, no genealogía. Fecha del reloj local: 2026-09-05. Claude adjudica contra la fuente.

La condición de contención se demuestra: eliminar la física o ambas mitades mata la prueba de junction; eliminar la validación de ciudad mata sus dos negativos. Sin embargo, hay una regresión reproducida con `CASOS_ROOT` inexistente y dos carencias sustantivas en el bloque de sala de lectura. También he reproducido una quinta puerta, preexistente, distinta de las tres diferidas en R1. Recomiendo `NO-SHIP` por los defectos dentro del diff; la quinta puerta debe registrarse sin convertirla en una ampliación automática del alcance nocturno.

Todas las escrituras y ejecuciones de esta revisión se hicieron en este directorio: copias `b/`, `h/`, `m/`, temporales cortos y sondas sintéticas. No se ejecutaron integraciones reales ni se modificó el objeto. No hubo delegación.

## Hallazgos nuevos de R2

### H-01 — ALTO — Defecto: la contención física impide el primer alta cuando la raíz no existe

**Bloque 1.** `head/core/case_manager.py:402-408`, especialmente línea 404. Introducido por el diff.

Con un padre existente y `CASOS_ROOT=<padre>/missing` todavía inexistente, `ensure_case('EV-2026-001')` es un alta válida: base crea la raíz y el expediente mediante `mkdir(parents=True)`. Head asciende hasta `<padre>`, compara ese padre con `<padre>/missing` y lo acusa de escapar por un enlace. No hay enlace. El ascenso resuelve demasiado arriba para la comparación que después hace.

Ejecutado con el mismo `probe.py` sobre ambas copias:

```text
BASE missing_root: result=OK, index=true
HEAD missing_root: result=ValueError, root_exists=false
El destino del caso sale de la raiz por un enlace: ...\ph\missing\EV-2026-001
resuelve a ...\ph, fuera de ...\ph\missing.
```

Evidencia completa: `probe-base.log` y `probe-head.log`. Los positivos del diff siempre crean previamente `tmp_casos_root`, así que no ejercitan este estado. La corrección debe conservar la capacidad de crear la raíz sin dejar de rechazar una junction en el destino o sus ancestros; una regresión con raíz inexistente y otra con raíz enlazada deben comprobar ambas propiedades.

### H-02 — MEDIO — Defecto: reutilizar `_bajo` rechaza descendientes de una raíz de volumen o de recurso UNC

**Bloque 1.** Nueva llamada en `head/core/case_manager.py:397`; causa en `core/casos/case_mutex.py:188`, sin cambios en este último fichero.

`_bajo` concatena `r + os.sep`. Si `r` ya termina en separador por ser `C:\` o `\\servidor\recurso\`, exige dos separadores consecutivos y devuelve falso para sus hijos. Una configuración de `CASOS_ROOT` en la raíz de un recurso compartido rechaza todos sus expedientes en la mitad léxica, antes de comprobar enlaces. El helper ya tenía esta limitación; el diff la incorpora al alta.

Sonda léxica ejecutada en Windows, sin acceder al servidor ni escribir en raíces de unidades:

```text
_bajo(Path('C:/CASOS/EV'), Path('C:/')) -> False
_bajo(Path('//server/share/CASOS/EV'), Path('//server/share/')) -> False
_bajo(Path('D:/CASOS/EV'), Path('C:/CASOS')) -> False
```

Las dos primeras respuestas son falsos rechazos; la tercera es correcta. Evidencia: `probe-head.log`. Falta un positivo sobre raíces ancladas, usando comparación real de componentes. No afirmo haber ejecutado un alta en un servidor UNC ni sobre `G:`.

### H-03 — MEDIO — Defecto: el nuevo validador acepta nombres que todavía dejan andamiaje parcial

**Bloque 1.** `head/core/utils.py:137-164`, en particular líneas 155-164; consumo sin normalizar en `core/case_manager.py:410-417`.

`exigir_componente_de_ruta('foo ', campo='case')` acepta el valor y lo devuelve con el espacio final. En este Windows, `ensure_case('foo ')` crea `foo` y falla al intentar crear `foo /00_Input`. Se contradice la presentación de la validación como gramática completa y alta sin carpeta parcial para entradas inválidas.

```text
HEAD name='foo ': helper=true, result=FileNotFoundError
[WinError 3] ...\foo \00_Input
children=['foo']
```

El mismo comportamiento del alta existe en base: **no es una regresión nueva de escritura**, sino un hueco de la nueva validación en el sumidero, dentro del ataque a espacios solicitado. No lo presento como escape ni como repetición del vacío de R1/H-02.

También pasan el helper los controles NUL/U+0001, los nombres reservados probados y un componente de 256 caracteres; algunos fallan después en el filesystem. La reproducción relevante para daño parcial es `foo `. Véase `probe-head.log`. Hace falta validar o definir una normalización única antes de nombrar y crear, manteniendo los identificadores legítimos; comprobar únicamente `.strip()` para vacío y puntos no establece esa política.

### H-04 — MEDIO — Defecto: worklist ausente se anuncia como catálogo completamente clasificado

**Bloque 2.** `head/scripts/sala_lectura.py:101-103` y `core/sala_lectura.py:338-390`.

Secuencia legítima: alta → depositar `ambiguo.pdf` → `inventory.scan` → `build_catalog` → CLI `preparar-residuo`, sin haber generado todavía `_clasificar.md`. Hay una entrada sin `tipo_documental`. `_filas_worklist` devuelve `[]` si falta el fichero; los dos métodos de residuo parten de esa lista, devuelven vacío y la nueva CLI declara un hecho falso y sale con 0.

```json
{"probe":"catalog_without_worklist","n_catalog":1,"n_unclassified":1,"code":0,"output":"Sin residuo: todo el catálogo está clasificado. Nada que preparar.\n"}
```

Después de `clasificar_caso`, sin añadir ni quitar documentos, la misma CLI sale con 1 y avisa de un documento ilegible. Ejecutado: `probe-head.log`. En base la secuencia también devolvía 0, pero el diff añade la afirmación categórica «todo el catálogo está clasificado» y no cierra la distinción que pretende introducir.

Los tres brazos del `if` son disjuntos sobre sus dos listas; **no son exhaustivos sobre el estado documental**. Falta distinguir «worklist no generada/inconsistente» de «cero residuo». Además, un hash de worklist ausente del catálogo se descarta en ambos métodos; esa variante se constató por lectura, no se ejecutó. Los tests nuevos siempre llaman antes a `clasificar_caso`, por lo que no detectan el contraejemplo ejecutado.

### H-05 — MEDIO — Defecto de prueba: el guard mixto permite enlazar el MD de otro documento

**Bloque 2.** `head/tests/test_sala_lectura_espejos_md_resuelven.py:101-150`, especialmente el supuesto test de correspondencia de línea 136.

El literal del directorio en el fixture está bien desacoplado. La carencia está en la aserción: el test de correspondencia no renderiza ni lee el índice. Los otros tests comprueban que hay dos enlaces, que existen y qué filas tienen enlace; no comprueban que cada enlace corresponda al texto de esa fila.

Mutante aplicado **solo en `m/`**: conservar `_md_paths` y la ausencia de enlace para el ciego, pero hacer que `_link_md` enlace siempre el primer MD existente del directorio para cualquier documento legible.

```text
WRONG_LINK EXIT 0
.... [100%]
4 passed in 5.85s

ambiguo canonico.pdf -> ambiguo_canonico__21af8e71.md
ambiguo partido.pdf  -> ambiguo_canonico__21af8e71.md
```

Evidencia: `run_wrong_link.py`, `wrong-link.log` y los índices conservados bajo `w0/`. No afirmo que el código de producción actual cruce esos enlaces: demuestro que **el nuevo guard no detecta esa regresión de su propiedad declarada**. Debe contrastar por documento el destino o contenido del enlace con el espejo esperado independiente; no basta con la existencia física ni con dos conjuntos de nombres.

### H-06 — ALTO — Defecto preexistente: quinta puerta por `lote` externo con un `case_id` válido

**Fuera de los ficheros de producción modificados; barrido exigido por el punto 7.** `head/core/intake_manual.py:118-123`; rutas hermanas en líneas 158-163 y 190-203.

`save_file` valida el nombre y localiza un caso auténtico dentro de `CASOS_ROOT`, pero acepta el argumento `lote` sin comprobar su pertenencia a ese caso ni a una copia operativa. Un lote externo no necesita pasar por `reservar_lote`. Con un nombre de lote bien formado la operación termina con éxito, escribiendo tanto el fichero como su manifiesto fuera.

```python
case = 'EV-2026-001'  # creado y localizado dentro de la raíz
save_file(case, 'canario.txt', b'CANARIO-R2',
          lote=exterior / '2026-09-05_manual_01')
```

```json
{"probe":"fifth_lote","result":"OK","outside":true,"content":"CANARIO-R2","manifest":true}
```

Reproducido en **base y head**, sin parches a las funciones llamadas: `extra-base.log`, `extra-head.log`. Es distinto de R1/#156: allí el `case_id` era una ruta absoluta externa; aquí el `case_id` es legítimo y **otra entrada**, `lote`, decide dónde terminan los bytes. Cerrar solamente `caso_path`/`reservar_lote` no cerraría esta vía. Tampoco requiere junction.

Registrar una obligación explícita de comprobar la relación caso–lote–copia operativa en los escritores que aceptan lotes. Por el alcance autorizado, no condiciono este diff a arreglar de noche toda esa gestión; sí a no dar esta ruta por cubierta por #156 sin incluirla expresamente.

## 1. Condición de autorización: mutaciones ejecutadas

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`.

En cada variante, proceso Python nuevo, copia `m/`, `PYTHONDONTWRITEBYTECODE=1`, UTF-8, `-p no:cacheprovider`, `--basetemp=../uN` y `--tb=short`. Se sustituye únicamente el condicional correspondiente por `if False`; la física conserva el recorrido del ancestro y se retira su rechazo. Al terminar se restaura el fichero. Script y salidas: `run_mutations.py`, `mutation-summary.log`, `mut-*.log`.

La suite de mutación es **todo `tests/test_ensure_case_sumidero.py`**, 17 casos. No atribuyo estos recuentos a mutaciones de la suite global.

| Variante | Resultado | Tests que mueren, exactamente |
|---|---|---|
| Head intacto | 17 passed | Ninguno |
| Sin mitad léxica | 17 passed | Ninguno |
| Sin mitad física | 1 failed, 16 passed | `test_un_destino_fuera_de_la_raiz_ABORTA_y_no_escribe_fuera` |
| Sin ambas mitades | 1 failed, 16 passed | `test_un_destino_fuera_de_la_raiz_ABORTA_y_no_escribe_fuera` |
| Sin validación de ciudad, (b) del diseño | 2 failed, 15 passed | `test_una_ciudad_con_subruta_ABORTA`; `test_una_ciudad_desconocida_de_un_componente_ABORTA` |

Todos los nombres de la tabla pertenecen a `tests/test_ensure_case_sumidero.py`. En los cuatro fallos negativos la causa fue `Failed: DID NOT RAISE ValueError`. La junction se creó realmente; **no hubo skip**.

**Respuesta explícita: SÍ se cumple la condición de que retirar la contención produzca rojo.** La física y la eliminación conjunta quedan detectadas. La mitad léxica no tiene un test discriminante en esta suite; eso no permite decir que cada mitad esté protegida independientemente. R1/H-05 queda remediado en cuanto a eliminar (c), y también se comprobó (b) para despejar la ambigüedad de letras del mandato. No repito el H-05 de R1 como hallazgo nuevo.

## 2. Contención física, Windows y raíces

- **Terminación:** el ascenso reduce un componente y para al llegar a `parent == self`; no hay bucle infinito en esa lógica. Una junction autorreferente real terminó con `FileExistsError`, sin quedar colgada (`extra-head.log`). Eso no convierte el error en un rechazo semántico bien diagnosticado.
- **Raíz inexistente:** falso rechazo reproducido, H-01.
- **Junction en una ciudad hacia fuera:** head lanza `ValueError` y el exterior queda vacío; base crea el expediente fuera (`extra-*.log`).
- **Junction en una ciudad hacia dentro:** alta correcta y `buscar` la encuentra.
- **Raíz que es junction:** alta correcta; `config.Settings.casos_root` ya resuelve la variable de entorno y el índice aparece bajo el destino físico. La prueba no demuestra Drive Stream.
- **Raíz de volumen/UNC:** defecto léxico H-02. Comparación entre unidades distintas rechaza correctamente en la sonda léxica.
- **Permisos y `G:` real:** no verificados en vivo. `exists()`/`resolve()` pueden fallar o esconder indisponibilidad según el filesystem; no he convertido esa incertidumbre en un escape demostrado.
- **Junction en hijo:** límite explícito en código y diseño, #157, ya adjudicado; no se repite como nuevo. Tampoco se acredita atomicidad frente a cambios concurrentes de enlaces entre comprobación y escritura.

## 3. Orden y efectos anteriores a la guarda

Dentro de `ensure_case`, el nuevo control de `case_id` precede a `destino_de_alta` y al primer `mkdir`. En modo V1 hay antes validación del modo, consulta/revalidación del mutex y lectura de identidad mediante `buscar`/`read_case_meta`; no localicé escritura de expediente ni evento en ese prefijo. `buscar` y los constructores nominales no crean carpetas.

La afirmación más amplia «ningún efecto antes de la guarda en todo llamador» sería falsa: `streamlit_app.py:2143` escribe `alta_caso_incoherente` mediante `append_audit_log` **antes** de llamar a `ensure_case` cuando se confirma una ciudad incoherente con el equipo. `case_locator.append_audit_log` crea `_audit` y escribe `relocations.jsonl`. El CLI adquiere además el mutex antes del alta. Son efectos preexistentes de los envoltorios; no una escritura del árbol de expediente introducida por el diff. La UI real no se ejecutó.

Para los negativos que los tests ejercitan, no queda carpeta parcial. Eso no se extiende a todos los valores aceptados por el helper: H-03 reproduce el contraejemplo con espacio final. Ni los tests ni esta guarda prometen rollback de fallos de disco posteriores al primer `mkdir`.

## 4. Compatibilidad y suite completa

Se ejecutó la suite global predeterminada, sin selección de módulos y sin `--runslow`, sobre cada copia sin mutar:

```text
cwd=b: python -m pytest -p no:cacheprovider --basetemp=../t1 --tb=short
cwd=h: python -m pytest -p no:cacheprovider --basetemp=../t0 --tb=short
```

Con `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8`. Ambos procesos devolvieron 1.

```text
BASE: 16 failed, 4016 passed, 77 skipped, 10 xfailed, 1 warning in 466.74s (0:07:46)
HEAD: 16 failed, 4048 passed, 77 skipped, 10 xfailed, 1 warning in 486.20s (0:08:06)
```

**Mismo conjunto de 16 fallos; cero fallos adicionales en head.** Los +32 pasados corresponden exactamente a los 17 nuevos de alta y los 15 de sala. No se proclama suite verde: H-01 se encontró mediante una sonda que la suite no contiene.

Desglose de los 16 fallos comunes, comprobado en ambas trazas:

| Casos | Motivo observado |
|---|---|
| 2 de `test_crm_dedup_incertidumbre.py` | Falta `SUDESPACHO_LEGACY_HOST`, tal como advertía el mandato; ajenos al diff |
| 3 de `test_gitignore_no_inerte.py` | `git ls-files` / `git check-ignore`, rc=128: no hay `.git` |
| 7 de `test_guard_localizador.py` | `PermissionError` al crear `_zz_guard_probe_*.py` dentro de la copia |
| 1 de `test_case_mutex_r11.py` | `PermissionError` al preparar `no_deberia_escribirse` dentro de la copia; la aserción de junction no llega a ejecutarse |
| 1 de `test_mcp_wrappers.py` | Wrapper sin intérprete no alcanza diagnóstico esperado; stderr repite que `ping` no se reconoce |
| 2 de `test_session_close_no_pude_medir.py` | Las copias congeladas no tienen el venv que los tests esperan |

Nombres exactos comunes:

```text
FAILED tests/test_case_mutex_r11.py::TestUnEnlaceNoEsUnaPuertaTrasera::test_una_junction_al_repo_se_rechaza
FAILED tests/test_crm_dedup_incertidumbre.py::TestUnaConsultaCaidaNoEsAusencia::test_el_colaborador_tampoco
FAILED tests/test_crm_dedup_incertidumbre.py::test_el_respaldo_del_colaborador_no_corre_si_el_NIF_no_se_pudo_mirar
FAILED tests/test_gitignore_no_inerte.py::test_ninguna_regla_de_gitignore_es_inerte
FAILED tests/test_gitignore_no_inerte.py::test_una_negacion_no_cuenta_como_regla_inerte
FAILED tests/test_gitignore_no_inerte.py::test_los_readme_de_telemetria_estan_rescatados_y_la_telemetria_no
FAILED tests/test_guard_localizador.py::test_el_contador_detecta_una_escotilla_sintetica
FAILED tests/test_guard_localizador.py::test_el_contador_distingue_los_casos[d = caso_path('W-X', strict=False)-1]
FAILED tests/test_guard_localizador.py::test_el_contador_distingue_los_casos[d = caso_path('W-X', strict=True)-0]
FAILED tests/test_guard_localizador.py::test_el_contador_distingue_los_casos[d = caso_path('W-X')-0]
FAILED tests/test_guard_localizador.py::test_el_contador_distingue_los_casos[d = path_for('W-X', strict=False)-1]
FAILED tests/test_guard_localizador.py::test_el_contador_distingue_los_casos[d = config.caso_path('W-X', strict=False)-1]
FAILED tests/test_guard_localizador.py::test_el_contador_distingue_los_casos[d = otra_cosa('W-X', strict=False)-0]
FAILED tests/test_mcp_wrappers.py::test_sin_interprete_capaz_el_wrapper_FALLA_RUIDOSAMENTE[expedientes_xl]
FAILED tests/test_session_close_no_pude_medir.py::TestLaVerja::test_el_mensaje_sugiere_un_interprete_QUE_EXISTE
FAILED tests/test_session_close_no_pude_medir.py::TestLaRutaQueSugiere::test_en_este_repo_encuentra_uno_que_existe
```

Evidencia completa: `head-suite.log` y `base-suite.log`. Los 77 skips incluyen 70 marcados lentos, cinco pruebas de Ollama no disponible, el fixture real SaRS1 ausente y la blocklist de PII ausente. Los 10 xfails son cuatro de copia local registrada (#124) y seis del frontal repository ya declarados. No hubo XPASS. Esta ejecución no acredita los lentos omitidos ni una suite con dos semillas.

No hay fallos en `test_case_manager.py`, `test_case_locator.py`, `test_migrate_to_city.py`, `test_repository_checkout.py` ni `test_abrir_caso_modo_v1.py` en esta corrida; su cobertura es la de sus fixtures y sustitutos, no operaciones remotas reales.


La migración usa `move_to_city`, cuyo cuerpo no cambió, y `_Sin clasificar` pertenece al catálogo aceptado. El alta de un caso ya situado bajo su ciudad conserva su ubicación. La vía V1 con `--force` conserva las restricciones previas de `validar_modo` y el nombre fijado por `--case-id`; el diff no modifica esa política. Los tests de checkout no equivalen a un checkout real con rclone/Drive.

## 5. Composición de `exigir_componente_de_ruta`

Los vacíos, espacios solos y `.`/`..` con espacios alrededor se rechazan; el helper se compone sobre el mismo filtro de separadores sin imponer formato CRM. Sin embargo, no define todos los nombres legales de Windows:

| Entrada sondeada en head | Resultado observado |
|---|---|
| `CON`, `AUX`, `COM1` | Helper acepta; este Python/Windows creó el árbol bajo esos nombres |
| `NUL` | Helper acepta; luego el alta rechaza por contención léxica |
| `foo.` | Aceptado; filesystem materializa `foo` |
| `foo ` | Aceptado; crea `foo` y falla en `00_Input`, H-03 |
| `...`, `. .`, `.. .` | Helper acepta; el alta falla sin índice en la raíz |
| `A\x00B`, `A\x01B` | Helper acepta; fallo posterior en filesystem |
| 256 letras en un componente | Helper acepta; `OSError` en este entorno |
| `foo／bar` (U+FF0F), `foo∕bar` (U+2215) | Se crean como un componente, sin escape |

Sonda idéntica en base para distinguir comportamiento previo. El campo `helper=false` de `probe-base.log` significa que el nuevo helper no existe allí, no que base rechazase esos nombres. No hay normalización Unicode en este trayecto que convierta U+FF0F en `/`; una hipotética normalización posterior ajena no constituye un escape demostrado.

## 6. Positivos y catálogo documental

Pasan los siete positivos de `test_ensure_case_sumidero.py`: cuatro identificadores parametrizados, localización con Barcelona, fallback y caso existente bajo Sevilla. El docstring habla de nueve mutantes, pero pytest ejecuta 17 casos parametrizados.

Barrido reproducible de nombres completos entre backticks en `docs/`: 15 candidatos distintos, 14 aceptados por el helper y uno rechazado. El rechazado es un **placeholder** `<calle>` de `docs/superpowers/specs/2026-07-10-intake-crm-a-llm-design.md:313`, no un nombre real que debiera aceptarse. No encontré en ese barrido un identificador legítimo rechazado por su formato. Evidencia: `scan_ids.py`, `ids-docs.json`.

Ese barrido no reconstruye ni verifica de nuevo los 27 expedientes reales que cita el diseño. La carencia relevante de los positivos no es otro acento o signo ordinal, sino los estados de raíz inexistente y raíz anclada de H-01/H-02. El modo local bajo una raíz existente no tiene una prohibición especial de Desktop; no se ha probado con la instalación real del usuario.

## 7. Quinta puerta

Reproducción y distinción respecto de #156 en H-06. Se revisaron los puntos de `mkdir`, `copytree`, movimientos y los constructores de destino en core/scripts; los demás usos de `caso_path` con ID absoluto no se cuentan como puertas nuevas independientes de R1. Tampoco se etiqueta el checkout deliberado fuera de `CASOS_ROOT` como fuga por el mero hecho de estar fuera.

## Sala de lectura: comprobaciones adicionales

El nuevo `RuntimeError` no se dispara en los estados legítimos probados. `inventory.scan` fija `count=len(entries)` y `build_catalog` añade una entrada por cada elemento de `files`, sin un filtro que legítimamente vacíe el catálogo. Sin concurrencia ni manipulación entre ambos pasos, inventario no vacío y catálogo vacío sí indica inconsistencia. No encontré un falso rechazo de esa guarda; sus cinco tests nuevos pasan.

Las tres variantes de salida de `organizar` respetan el universo del inventario: controles internos excluidos no se cuentan como material documental. No interpreto `input_vacio` como certificación de ausencia absoluta de bytes en todos los descendientes.

Mutaciones adicionales en los tres ficheros nuevos de sala, 15 tests en total (`run_mixed_mutations.py`):

| Mutante | Resultado |
|---|---|
| Head intacto | 15 passed |
| `_MD_SUBDIR` vuelve a `01_Procesado/MD` | 4 failed, 11 passed: mueren los cuatro del caso mixto |
| `_md_paths` ignora canónico | 6 failed, 9 passed |
| `_link_md` no publica enlaces | 2 failed, 13 passed |
| Enlace al primer MD de otro documento | Los 4 tests mixtos pasan; H-05 |

El fixture mixto fija correctamente la ruta del productor (`sala_maquina._sala_maquina_dir` + `03_MD`). Sigue usando `output_slug`, que también usa el productor: no lo considero una circularidad demostrada de la ruta. El helper `_md_dir` del fichero `test_sala_lectura_residuo_sin_texto.py` sí sigue `_MD_SUBDIR`; sus seis tests sobreviven al cambio de directorio. Esa limitación queda compensada para el directorio por el caso mixto, pero **no** para la correspondencia de enlaces, H-05.

## R1: verificación de las cinco remediaciones, sin contarlas como hallazgos nuevos

- **R1/H-01:** el diseño §2 y el backlog retiran la garantía universal y enlazan #155/#156/#157; sus implementaciones no cambiaron. El comentario de `ensure_case:344-346` todavía habla de «la puerta que nadie ha escrito» y convendría limitarlo expresamente al alta nominal, como hace el diseño.
- **R1/H-02:** vacío rechazado antes de `destino_de_alta`; test de no transformar la raíz ejecutado y verde.
- **R1/H-03:** ciudad validada contra `_CITY_NAMES`, equivalente al recorrido de `buscar` (`CIUDADES` + fallback); dos mutantes de supresión muertos.
- **R1/H-04:** límite de junction en hijo declarado en `case_manager` y diseño; #157 abierta.
- **R1/H-05:** la supresión de contención física/conjunta mata la prueba; remediado con la precisión léxica indicada en la tabla.

El §3(c) del diseño rev. 2 todavía describe la primitiva léxica como implementación de contención. La corrección física está explicada en el último apartado del acta y en código, pero no incorporada a esa descripción principal. Es una divergencia documental comprobada, no otro escape ejecutado. Asimismo, el backlog conserva los antiguos rótulos «ABIERTA» debajo de los nuevos «CERRADO» para #153/#154; debe leerse con su contexto histórico.

## Revisado sin defecto encontrado, por pieza

- `destino_de_alta` y `buscar`: no escriben; el caso existente bajo ciudad mantiene destino.
- Validación de ID vacío/separadores y ciudad fuera de catálogo: los negativos del diff abortan como se exige.
- Junction real en caso/ciudad hacia fuera: el rechazo físico funciona antes del depósito probado.
- Junction de raíz y enlace de ciudad hacia dentro: positivos ejecutados sin falso rechazo.
- `_Sin clasificar` y nombres canónicos con acentos, ordinales y paréntesis: positivos verdes.
- `organizar`: el vacío legítimo, extensiones omitidas y catálogo normal se distinguen en los tests ejecutados; el inventario no vacío/catalogación vacía aborta.
- Directorio del fixture mixto: independiente de `_MD_SUBDIR`; el mutante de directorio muere.
- Límite junction-en-hijo y otras tres puertas de R1: declarados y sin cambios de producción encubiertos.

## No verificado y límites de cobertura

- Dos semillas con `pytest-randomly`: **SIN VERIFICAR**, no está instalado.
- UNC remoto, `G:`/Drive Stream y fallos reales de permisos: **SIN VERIFICAR**; solo sondas léxicas de UNC y enlaces locales reales.
- Integraciones reales (CRM, rclone, Gmail, checkout en Drive), UI interactiva, concurrencia de enlaces y cortes de disco: no ejecutados; las pruebas de suite usan sus sustitutos/aislamiento.
- Los 27 casos reales citados: no se recorrió un catálogo vivo; solo objeto congelado, cuatro positivos parametrizados y candidatos documentados.
- Suite global bajo cada mutante: no ejecutada; la tabla de mutación identifica expresamente su suite de 17 tests y la de sala sus 15 tests.
- Los skips/xfails y las dependencias/guards no ejercitados por ausencia de `.git` se detallan junto al resultado global. Un verde de un guard que enumera cero ficheros con `git ls-files` no acredita su cobertura.

## Integridad: SHA-256 al abrir y al cerrar

Se calcularon hashes **antes de leer el código** para todos los ficheros: 1171 de base y 1177 de head. Al cierre se volvieron a leer y hashear los 2348; el conjunto de rutas y **todos los hashes coinciden**, sin altas, bajas ni cambios.

El manifiesto íntegro [hashes-comparados.tsv](hashes-comparados.tsv) contiene una fila por fichero con árbol, ruta, SHA-256 de apertura y SHA-256 de cierre. Incluye todos los tests ejecutados, documentación y ficheros del barrido, no solo los extractos de esta tabla. Los registros originales son [hashes-open.json](hashes-open.json) y [hashes-close.json](hashes-close.json).

| Artefacto de integridad | SHA-256 |
|---|---|
| `hashes-open.json` | `a2af880350d99b2986dfc47ea1bf8816c9b89655eff1b847a7c764690abd58b6` |
| `hashes-close.json` | `c4b7b92eb2c8ccfadde94cd16128108c28d22258a8bddf38938f31120ae5d187` |
| `hashes-comparados.tsv` | `2d48f7689cf38ad37d359866fa05d6c7d6d69868bebdedbd41349b3db3bd28ac` |

Extracto con todos los ficheros del diff y los principales soportes leídos. `—` significa fichero ausente en base, no hash omitido. La igualdad apertura/cierre se muestra en las dos columnas.

| Árbol/ruta | SHA-256 apertura | SHA-256 cierre |
|---|---|---|
| `base/AGENTS.md` | `f4cfbe9c35ea45ee324cfef29450116135dab2945686086fb6444e5301d6698b` | `f4cfbe9c35ea45ee324cfef29450116135dab2945686086fb6444e5301d6698b` |
| `head/AGENTS.md` | `f4cfbe9c35ea45ee324cfef29450116135dab2945686086fb6444e5301d6698b` | `f4cfbe9c35ea45ee324cfef29450116135dab2945686086fb6444e5301d6698b` |
| `base/CLAUDE.md` | `78bdd63acfd1b0bc198a36449fb4e86674dcfc4673698460568bd45df2384abf` | `78bdd63acfd1b0bc198a36449fb4e86674dcfc4673698460568bd45df2384abf` |
| `head/CLAUDE.md` | `78bdd63acfd1b0bc198a36449fb4e86674dcfc4673698460568bd45df2384abf` | `78bdd63acfd1b0bc198a36449fb4e86674dcfc4673698460568bd45df2384abf` |
| `base/core/case_manager.py` | `0dfd269d0240900356fbb462fd633f0cfb3c329f36bad57fa4a6952f5e0f58c2` | `0dfd269d0240900356fbb462fd633f0cfb3c329f36bad57fa4a6952f5e0f58c2` |
| `head/core/case_manager.py` | `c7eac13e546feb4bfaeaf5b8e7b02aa6bdd8bc0c831731ef2878d8b2abecd65d` | `c7eac13e546feb4bfaeaf5b8e7b02aa6bdd8bc0c831731ef2878d8b2abecd65d` |
| `base/core/casos/case_locator.py` | `3ca55e5febe1cdaf18448553bd13cf5d714a7ebebfeb15c52d521f6758b3c71d` | `3ca55e5febe1cdaf18448553bd13cf5d714a7ebebfeb15c52d521f6758b3c71d` |
| `head/core/casos/case_locator.py` | `3ca55e5febe1cdaf18448553bd13cf5d714a7ebebfeb15c52d521f6758b3c71d` | `3ca55e5febe1cdaf18448553bd13cf5d714a7ebebfeb15c52d521f6758b3c71d` |
| `base/core/casos/case_mutex.py` | `0ade763185f0d11f881dce01afb914b21f3da9379b87204306018018c0570b53` | `0ade763185f0d11f881dce01afb914b21f3da9379b87204306018018c0570b53` |
| `head/core/casos/case_mutex.py` | `0ade763185f0d11f881dce01afb914b21f3da9379b87204306018018c0570b53` | `0ade763185f0d11f881dce01afb914b21f3da9379b87204306018018c0570b53` |
| `base/core/casos/mutex_sesion.py` | `2ac19276dac9a8358638d80b7f5ef5ee29ab330845ffa8b5c35ce91ae161d4a7` | `2ac19276dac9a8358638d80b7f5ef5ee29ab330845ffa8b5c35ce91ae161d4a7` |
| `head/core/casos/mutex_sesion.py` | `2ac19276dac9a8358638d80b7f5ef5ee29ab330845ffa8b5c35ce91ae161d4a7` | `2ac19276dac9a8358638d80b7f5ef5ee29ab330845ffa8b5c35ce91ae161d4a7` |
| `base/core/catalogo_documental.py` | `b2720bffa3a697a12e9678ab6ead81b4e873d993fbfb3d7c5d8963c8039b83e4` | `b2720bffa3a697a12e9678ab6ead81b4e873d993fbfb3d7c5d8963c8039b83e4` |
| `head/core/catalogo_documental.py` | `b2720bffa3a697a12e9678ab6ead81b4e873d993fbfb3d7c5d8963c8039b83e4` | `b2720bffa3a697a12e9678ab6ead81b4e873d993fbfb3d7c5d8963c8039b83e4` |
| `base/core/config.py` | `b1ac9e68320dca7a08217570093216d7403b598c37fce40f6250a3f443bf878d` | `b1ac9e68320dca7a08217570093216d7403b598c37fce40f6250a3f443bf878d` |
| `head/core/config.py` | `b1ac9e68320dca7a08217570093216d7403b598c37fce40f6250a3f443bf878d` | `b1ac9e68320dca7a08217570093216d7403b598c37fce40f6250a3f443bf878d` |
| `base/core/intake_lotes.py` | `16a67ad072150e687d820dfa615e1431b57280234d13df697833ec6ad25ec016` | `16a67ad072150e687d820dfa615e1431b57280234d13df697833ec6ad25ec016` |
| `head/core/intake_lotes.py` | `16a67ad072150e687d820dfa615e1431b57280234d13df697833ec6ad25ec016` | `16a67ad072150e687d820dfa615e1431b57280234d13df697833ec6ad25ec016` |
| `base/core/intake_manual.py` | `44902f1930a50f211ce8e24586072ad92feaece9a68deb51d80d9ed9985917b5` | `44902f1930a50f211ce8e24586072ad92feaece9a68deb51d80d9ed9985917b5` |
| `head/core/intake_manual.py` | `44902f1930a50f211ce8e24586072ad92feaece9a68deb51d80d9ed9985917b5` | `44902f1930a50f211ce8e24586072ad92feaece9a68deb51d80d9ed9985917b5` |
| `base/core/intake_utils.py` | `29f37227f2fc7647b83078c3e87e7c90ef09349b64d2589a6c30722b9e9cae90` | `29f37227f2fc7647b83078c3e87e7c90ef09349b64d2589a6c30722b9e9cae90` |
| `head/core/intake_utils.py` | `29f37227f2fc7647b83078c3e87e7c90ef09349b64d2589a6c30722b9e9cae90` | `29f37227f2fc7647b83078c3e87e7c90ef09349b64d2589a6c30722b9e9cae90` |
| `base/core/inventory.py` | `f95f155ca3992f7cf1d805a200644959d87b0b228df6ac9a81ca8a440c61f48f` | `f95f155ca3992f7cf1d805a200644959d87b0b228df6ac9a81ca8a440c61f48f` |
| `head/core/inventory.py` | `f95f155ca3992f7cf1d805a200644959d87b0b228df6ac9a81ca8a440c61f48f` | `f95f155ca3992f7cf1d805a200644959d87b0b228df6ac9a81ca8a440c61f48f` |
| `base/core/sala_lectura.py` | `9785c3267fcc3c59a276608b30f812379fe2a9bc73f62db7d3cb2a890c304021` | `9785c3267fcc3c59a276608b30f812379fe2a9bc73f62db7d3cb2a890c304021` |
| `head/core/sala_lectura.py` | `f34d1deb6a4c164fde17aff2d0ea74ac18f2b42dd0f1094902961b4a7fb4e35d` | `f34d1deb6a4c164fde17aff2d0ea74ac18f2b42dd0f1094902961b4a7fb4e35d` |
| `base/core/sala_maquina.py` | `2a159783be6f5d8ba6e9ccd8f0c9141c5e0e3ac1581eeb3bccb7544e4bb164fb` | `2a159783be6f5d8ba6e9ccd8f0c9141c5e0e3ac1581eeb3bccb7544e4bb164fb` |
| `head/core/sala_maquina.py` | `2a159783be6f5d8ba6e9ccd8f0c9141c5e0e3ac1581eeb3bccb7544e4bb164fb` | `2a159783be6f5d8ba6e9ccd8f0c9141c5e0e3ac1581eeb3bccb7544e4bb164fb` |
| `base/core/sync.py` | `287146049fe2178d682115af45c0e961367266c87848143ffcf1ff97db823869` | `287146049fe2178d682115af45c0e961367266c87848143ffcf1ff97db823869` |
| `head/core/sync.py` | `287146049fe2178d682115af45c0e961367266c87848143ffcf1ff97db823869` | `287146049fe2178d682115af45c0e961367266c87848143ffcf1ff97db823869` |
| `base/core/utils.py` | `58a3eb59fddab37390e349763afe2d851e63868730c5df8e762e726934789721` | `58a3eb59fddab37390e349763afe2d851e63868730c5df8e762e726934789721` |
| `head/core/utils.py` | `a1b171c8e793d67a7777e50cb0c5087aecddf591bf6d9980cbc20cfc01ac5fa7` | `a1b171c8e793d67a7777e50cb0c5087aecddf591bf6d9980cbc20cfc01ac5fa7` |
| `base/docs/MEJORAS_FUTURAS.md` | `216adc33f288562efc0e153ad7146d02f03139a683daa4499b20c2e776fbfd33` | `216adc33f288562efc0e153ad7146d02f03139a683daa4499b20c2e776fbfd33` |
| `head/docs/MEJORAS_FUTURAS.md` | `248b53ce7745d58b8b837ccf4d8b6ef51a2040a565e4bbc909dfdf56df26ace3` | `248b53ce7745d58b8b837ccf4d8b6ef51a2040a565e4bbc909dfdf56df26ace3` |
| `base/docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md` | `—` | `—` |
| `head/docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md` | `d681a7086c08dd9752559c5b1d56dbf658f89392063d1fe82b533cc7812a6c68` | `d681a7086c08dd9752559c5b1d56dbf658f89392063d1fe82b533cc7812a6c68` |
| `base/docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md` | `—` | `—` |
| `head/docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-r1-adversarial-review.md` | `98caf6e019eb64e763270c3a1ee9bd2bf74790317cf97613cd05d6bbd1d7355d` | `98caf6e019eb64e763270c3a1ee9bd2bf74790317cf97613cd05d6bbd1d7355d` |
| `base/pyproject.toml` | `bb892fe7f7da0c6d5f33827fe4b8b31d030f025c2e4d7e1ce738bf0f9a225a1a` | `bb892fe7f7da0c6d5f33827fe4b8b31d030f025c2e4d7e1ce738bf0f9a225a1a` |
| `head/pyproject.toml` | `bb892fe7f7da0c6d5f33827fe4b8b31d030f025c2e4d7e1ce738bf0f9a225a1a` | `bb892fe7f7da0c6d5f33827fe4b8b31d030f025c2e4d7e1ce738bf0f9a225a1a` |
| `base/scripts/abrir_caso.py` | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` |
| `head/scripts/abrir_caso.py` | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` |
| `base/scripts/migrate_to_city_structure.py` | `f4ecbfd5956089a3b8d4ee78e055298f04cf1e52018318fa5736e0981a1aa7c4` | `f4ecbfd5956089a3b8d4ee78e055298f04cf1e52018318fa5736e0981a1aa7c4` |
| `head/scripts/migrate_to_city_structure.py` | `f4ecbfd5956089a3b8d4ee78e055298f04cf1e52018318fa5736e0981a1aa7c4` | `f4ecbfd5956089a3b8d4ee78e055298f04cf1e52018318fa5736e0981a1aa7c4` |
| `base/scripts/sala_lectura.py` | `f500c7ce69c6337698af8ec9f066f582ab89e24f50bfe10564bb9609d67769a8` | `f500c7ce69c6337698af8ec9f066f582ab89e24f50bfe10564bb9609d67769a8` |
| `head/scripts/sala_lectura.py` | `a92574148df8fd7bfe3e9a5bae0d91c658fb1600c76bfe439a8778bd6a1ed033` | `a92574148df8fd7bfe3e9a5bae0d91c658fb1600c76bfe439a8778bd6a1ed033` |
| `base/streamlit_app.py` | `855540a3c89a5c1f8a54d50d1633117326466cf9e25487349b2682f1aa104542` | `855540a3c89a5c1f8a54d50d1633117326466cf9e25487349b2682f1aa104542` |
| `head/streamlit_app.py` | `855540a3c89a5c1f8a54d50d1633117326466cf9e25487349b2682f1aa104542` | `855540a3c89a5c1f8a54d50d1633117326466cf9e25487349b2682f1aa104542` |
| `base/tests/_barrera.py` | `63accccfdb4e4ec35711105538c6dc2149c9f2558a5cc3ebafd450d62288270f` | `63accccfdb4e4ec35711105538c6dc2149c9f2558a5cc3ebafd450d62288270f` |
| `head/tests/_barrera.py` | `63accccfdb4e4ec35711105538c6dc2149c9f2558a5cc3ebafd450d62288270f` | `63accccfdb4e4ec35711105538c6dc2149c9f2558a5cc3ebafd450d62288270f` |
| `base/tests/conftest.py` | `52909c1473a0701456ec252fab07d04e159aba7e8d81125f3394d00a1f6f6413` | `52909c1473a0701456ec252fab07d04e159aba7e8d81125f3394d00a1f6f6413` |
| `head/tests/conftest.py` | `52909c1473a0701456ec252fab07d04e159aba7e8d81125f3394d00a1f6f6413` | `52909c1473a0701456ec252fab07d04e159aba7e8d81125f3394d00a1f6f6413` |
| `base/tests/test_abrir_caso_modo_v1.py` | `99df9ed6e06965d1d2e9965c721c8065db9bf57e705b4a74d666c6381884fa88` | `99df9ed6e06965d1d2e9965c721c8065db9bf57e705b4a74d666c6381884fa88` |
| `head/tests/test_abrir_caso_modo_v1.py` | `99df9ed6e06965d1d2e9965c721c8065db9bf57e705b4a74d666c6381884fa88` | `99df9ed6e06965d1d2e9965c721c8065db9bf57e705b4a74d666c6381884fa88` |
| `base/tests/test_case_locator.py` | `b00a7add1b99231f3a7cceadddbcfdd0a9134a0b0f3810f04c08f5b7a34cfa7a` | `b00a7add1b99231f3a7cceadddbcfdd0a9134a0b0f3810f04c08f5b7a34cfa7a` |
| `head/tests/test_case_locator.py` | `b00a7add1b99231f3a7cceadddbcfdd0a9134a0b0f3810f04c08f5b7a34cfa7a` | `b00a7add1b99231f3a7cceadddbcfdd0a9134a0b0f3810f04c08f5b7a34cfa7a` |
| `base/tests/test_ensure_case_sumidero.py` | `—` | `—` |
| `head/tests/test_ensure_case_sumidero.py` | `ecd2b73180397056686a55432db55b6233650b5c335c760858b3b6dd53df422b` | `ecd2b73180397056686a55432db55b6233650b5c335c760858b3b6dd53df422b` |
| `base/tests/test_guard_localizador.py` | `837bc9a1e680794dc7f38e979ec2dcca0634ced856ac5bc6ddd485ca0e831a46` | `837bc9a1e680794dc7f38e979ec2dcca0634ced856ac5bc6ddd485ca0e831a46` |
| `head/tests/test_guard_localizador.py` | `837bc9a1e680794dc7f38e979ec2dcca0634ced856ac5bc6ddd485ca0e831a46` | `837bc9a1e680794dc7f38e979ec2dcca0634ced856ac5bc6ddd485ca0e831a46` |
| `base/tests/test_guard_no_basetemp_versionado.py` | `97248d16abc02d18db6eef3856bab9069188545249c237d0ad8d5139bbcfb8ef` | `97248d16abc02d18db6eef3856bab9069188545249c237d0ad8d5139bbcfb8ef` |
| `head/tests/test_guard_no_basetemp_versionado.py` | `97248d16abc02d18db6eef3856bab9069188545249c237d0ad8d5139bbcfb8ef` | `97248d16abc02d18db6eef3856bab9069188545249c237d0ad8d5139bbcfb8ef` |
| `base/tests/test_sala_lectura_cero_acciones.py` | `—` | `—` |
| `head/tests/test_sala_lectura_cero_acciones.py` | `c26b4250dbe21a0bbf7a2b17d9ed87ee72f8723356cd73e78ccc1f28a8586e8f` | `c26b4250dbe21a0bbf7a2b17d9ed87ee72f8723356cd73e78ccc1f28a8586e8f` |
| `base/tests/test_sala_lectura_espejos_md_resuelven.py` | `—` | `—` |
| `head/tests/test_sala_lectura_espejos_md_resuelven.py` | `d0a50bae668220f77f0732f5cfcc5cc14f8ed20fd18fc83fe01b4f48d36ea221` | `d0a50bae668220f77f0732f5cfcc5cc14f8ed20fd18fc83fe01b4f48d36ea221` |
| `base/tests/test_sala_lectura_residuo_sin_texto.py` | `—` | `—` |
| `head/tests/test_sala_lectura_residuo_sin_texto.py` | `7669b90f892c738f54f927556bc788ce042fad4519b75f2642073f37da9ea911` | `7669b90f892c738f54f927556bc788ce042fad4519b75f2642073f37da9ea911` |

Huellas de ejecución para reproducir y archivar junto al informe:

| Artefacto | SHA-256 |
|---|---|
| `run_mutations.py` | `83d8a68b644085cae9f8f8ffc9f2c3fb28a1f55823b6cc78ba12ce9c4de16fef` |
| `mutation-summary.log` | `dec27158cb23a3ae64bc08cff3a120919ec41664556ab448bdfffcbccad60aa1` |
| `run_mixed_mutations.py` | `c83169913382d0f88ba9e2a38eb27705569cd1de41ea33c34a7158ca1bcdf50f` |
| `mixed-summary.log` | `24e6ef565952c6cc9519a342eada77bee5edf62fe12f7525d44dc29d0e896b18` |
| `run_wrong_link.py` | `4a584a1cc64b27d0f6263261c88a7db574625882386aec50593cf5333e91d12f` |
| `wrong-link.log` | `760bc79b93e85af8e9492564a6f3bd51ec6db6dfb7e9066ecedd49a3b1b10443` |
| `probe.py` | `fabb21429bc1cd5a292b4392bf4556c86886e4febb1129bd9d8977b3bd7ba349` |
| `probe-base.log` | `5222995c531e7088f828c2d9208279452bfea3add85434c4b7a4228f18c7bdbb` |
| `probe-head.log` | `f294ed86591865b0c5f74d68449e4047fa6e09be05716f5f64ade8b1718f6d95` |
| `probe_extra.py` | `39d20bd02f7b21bd40e4080c3c86230ff65e989656ccb254ff825b4187f80d7a` |
| `extra-base.log` | `68efb15024d230c0b67faba08ae66d952986cad07e2f448506e8aae742bccab2` |
| `extra-head.log` | `9c0d2027359407628c8949fc57b9fc5dd194fc242a3208da8d1fd7b70a023586` |
| `head-suite.log` | `49d529bd5f889b3d7475564a8a864001a45d8492217c1f990a12f1b5e9164551` |
| `base-suite.log` | `adac5dac41231d0ee4a29c12f7f8039487f88f83753739ee9a9b3f397d0d55d2` |
| `scan_ids.py` | `7fcf0f848dadcb4e4cdebb79c3d035034addfbf9d250e8dac68a5b482b753f31` |
| `ids-docs.json` | `523b1450f0161e3af6843d1b8366c7f84cf36823e5e89e4aca1c3a4f342909e7` |


El veredicto se apoya en defectos reproducidos del diff y en la supervivencia del mutante de correspondencia documental. No exige una tercera ronda ni adjudica por Claude. La quinta puerta se entrega para su registro y priorización dentro del contrato de alcance estrecho.

NO-SHIP
<!-- informe-literal:fin:t3xk -->

## 2. Evidencia verificada por mí

Cada hallazgo se contrasta **contra la fuente**, no contra el informe ni contra el diff. Lo
que verifiqué por mi cuenta antes de aceptar nada:

**Solo lectura, comprobado y no creído.** El revisor declara 2348 ficheros con los mismos
`sha256` al abrir y al cerrar. Lo comprobé yo sobre su propio manifiesto:

```
$ awk -F'\t' 'NR>1 && $3!=$4' hashes-comparados.tsv | wc -l
0
$ awk 'NR>1' hashes-comparados.tsv | wc -l
2348
```

Cero filas con hash distinto sobre 2348. El objeto no se tocó.

**H-01 — reproducido.** Con `CASOS_ROOT` inexistente y su padre creado, la versión revisada
sube al primer ancestro existente —el **padre** de la raíz— y lo compara contra la raíz.
No hay enlace: el mensaje acusa de escapar por uno que no existe. Es una **regresión mía**,
introducida por el propio arreglo, y habría bloqueado el primer alta de cualquier máquina
nueva. Ninguno de mis 17 positivos lo ejercitaba porque **todos** crean `tmp_casos_root`
antes.

**H-02 — reproducido en dos líneas, sin tocar red ni raíces de unidad.**

```
_bajo(Path('C:/CASOS/EV'),             Path('C:/'))              -> False
_bajo(Path('//server/share/CASOS/EV'), Path('//server/share/'))  -> False
```

Los dos son **falsos rechazos**. `_bajo` concatena `r + os.sep`, así que una raíz que ya
termina en separador exige dos seguidos.

**H-03 — reproducido.** `exigir_componente_de_ruta('foo ')` devolvía el valor con el espacio
final; Windows lo recorta al crear, así que `ensure_case('foo ')` creaba `foo` y reventaba al
crear `foo /00_Input`, dejando **andamiaje parcial**. El nombre pedido y el creado eran
distintos y nadie los comparaba. **Precisión que le debo al revisor:** él mismo aclara que
*«el mismo comportamiento del alta existe en base: no es una regresión nueva de escritura,
sino un hueco de la nueva validación»*. Lo que introduje no fue el fallo de escritura sino
una **guarda que se presentaba como gramática completa** sin serlo — que es peor de lo que yo
mismo escribí en el mensaje del commit llamándolo regresión.

**H-04 — reproducido, y su frontera va más allá del ejemplo.** Alta → depositar un PDF →
`scan` → `build_catalog` → `preparar-residuo`, **sin** `clasificar`: el catálogo tiene un
documento sin tipo, `_filas_worklist` devuelve `[]` porque el fichero no existe, las dos
listas salen vacías, y la CLI afirmaba *«todo el catálogo está clasificado»* con salida **0**.
Es el defecto que ese mismo comando acababa de arreglar, un estado más allá: remedié tres
ramas y la cuarta seguía mintiendo. **Y mis tests no lo cazaban porque los cuatro llamaban a
`clasificar_caso` antes**, o sea que fabricaban la worklist sin darse cuenta de que ese era
el supuesto que faltaba.

**H-05 — reproducido con su mutante, y el mutante es el hallazgo.** Un `_link_md` que enlace
**siempre el primer MD del directorio** para cualquier documento legible deja mis cuatro
tests en verde:

```
WRONG_LINK EXIT 0 · 4 passed
ambiguo canonico.pdf -> ambiguo_canonico__21af8e71.md
ambiguo partido.pdf  -> ambiguo_canonico__21af8e71.md
```

Comprobaban que hay dos enlaces, que existen, y qué filas los llevan; **nunca que el enlace
de una fila sea el texto de ESA fila**. Existencia física no es correspondencia.

**H-06 — reproducido en base y en head, sin parchear nada.** `save_file` valida el nombre y
localiza un caso auténtico dentro de `CASOS_ROOT`, y acepta `lote` sin comprobar su
pertenencia:

```json
{"probe":"fifth_lote","result":"OK","outside":true,"content":"CANARIO-R2","manifest":true}
```

Verifiqué además que las hermanas comparten el hueco: `extract_zip` valida el ZIP contra
`lote` y `save_file_en_lote` valida `rel` contra `lote` con `resolve()` y todo — **las tres
validan la mitad relativa y ninguna la absoluta**. El docstring de la tercera lo dice sin
verlo: *«el caller ya validó la existencia del caso al abrir el lote»*. Eso es una **premisa
sobre el llamador**, no una comprobación.

**La condición que el revisor se había puesto a sí mismo, cumplida.** Su autorización del
alcance estrecho exigía *«la ronda 2 debe demostrar también la contención, con pruebas que
fallen al eliminarla»*. Su tabla de mutación lo ejecuta sobre los 17 casos de
`test_ensure_case_sumidero.py`: retirar la mitad física, o las dos, mata
`test_un_destino_fuera_de_la_raiz_ABORTA_y_no_escribe_fuera`; retirar la validación de ciudad
mata sus dos negativos. **La junction se creó de verdad; no hubo skip.** Y dice lo que no
puede decir: la mitad **léxica** no tiene un test discriminante propio en esa suite, así que
no está acreditado que cada mitad esté protegida por separado.

### Lo que el revisor NO pudo hacer, y queda sin verificar por él

Lo declara él y lo repito sin maquillarlo: **las dos semillas de `pytest-randomly`** (su copia
congelada no lo tiene instalado), UNC remoto real, `G:`/Drive Stream, fallos reales de
permisos, las integraciones vivas, y la suite global bajo cada mutante. Esa cobertura la
aporto yo y se dice así — **no se presenta como revisada**. Un revisor que no corre no
refuta: deja **sin verificar**.

## 3. Adjudicación

**Veredicto del revisor: `NO-SHIP`. Lo acepto entero. Seis hallazgos, seis confirmados, cero
refutados.** Tres de los seis eran defectos **míos, introducidos por el propio arreglo del
punto 1**, y el primero habría bloqueado el primer alta de una máquina nueva.

| # | Sev. | Qué falsó | Adjudicación y remedio |
|---|---|---|---|
| H-01 | ALTO | La contención física impedía crear la raíz en el primer alta | **CONFIRMADO.** Regresión mía. La comprobación física solo corre `if raiz.exists()` y el paseo **se detiene en la raíz** (`_contenido_en(ancestro.parent, raiz)`). Dos tests hermanos: el alta que crea su raíz, y la junction que **sigue** rechazándose |
| H-02 | MEDIO | `_bajo` rechaza a los hijos de una raíz anclada (`C:\`, UNC) | **CONFIRMADO.** De ahí `_contenido_en` con `commonpath`, y su docstring explica por qué no reutiliza `_bajo`. El `_bajo` del mutex **no se toca de noche**: otro radio de daño, presupuesto de dos rondas → `MEJORAS #159` |
| H-03 | MEDIO | El validador aceptaba nombres que dejaban andamiaje parcial | **CONFIRMADO**, con la precisión del §2: no era regresión de escritura, era una guarda más estrecha que su enunciado. Se rechazan espacios al borde y caracteres de control. Medido sobre los 27 casos reales: **no rechaza nada vivo** |
| H-04 | MEDIO | Worklist ausente se anunciaba como catálogo clasificado, con salida 0 | **CONFIRMADO, y remediado por la PROPIEDAD y no por el ejemplo** — ver abajo |
| H-05 | MEDIO | Mis cuatro tests no detectaban un `_link_md` que cruzara los enlaces | **CONFIRMADO.** Test nuevo que contrasta **por contenido**, no por nombre: un cruce de slugs no puede pasar inadvertido |
| H-06 | ALTO | Cuarta puerta: `intake_manual` confía en el `lote` que le pasan | **CONFIRMADO y preexistente.** Fuera del alcance autorizado; **registrado con su reproducción** como `MEJORAS #158`, y expresamente **no** dado por cubierto por `#156` |

### El corolario que me ahorró la tercera ronda, aplicado sobre H-04

`CLAUDE.md` manda preguntar, ante cada hallazgo, **«¿de qué frontera es esto un ejemplo?»**
antes de remediarlo. La primera vez no lo hice: remedié el caso que el informe describía
—«la worklist no se ha generado»— con `if sin_tipo and not hay_worklist`. **El propio informe
señalaba la frontera en la frase siguiente**, y con un estado más anotado por lectura: los
brazos del `if` *«son disjuntos sobre sus dos listas, no exhaustivos sobre el estado
documental»*, y una fila de worklist cuyo hash no está en el catálogo **se descarta en
silencio** en los dos métodos.

Lo verifiqué contra la fuente: `preparar_residuo` y `residuo_sin_texto` hacen ambos
`if e is None: continue`. Con la worklist **presente pero rancia** —material reemplazado en
`00_Input`, hashes que ya no casan— `hay_worklist` es `True` y mi remedio **volvía a afirmar
el hecho falso**.

La propiedad, que es lo que quedó en el código: **si el catálogo tiene documentos sin tipo,
esa frase no se puede decir, venga el vacío de donde venga.** La causa solo decide qué se
aconseja, nunca si se afirma ni el código de salida. Test propio
(`test_con_worklist_RANCIA_tampoco_afirma_que_todo_esta_clasificado`) y su mutante: reponer
`sin_tipo and not hay_worklist` mata **exactamente** ese test y ninguno más.

Esto no es un hallazgo de la R2 y no se le atribuye como tal: el revisor lo dejó anotado
**sin ejecutar**, y ejecutarlo era mi trabajo.

### Mutantes de esta remediación: nueve, los nueve muertos

Los dos que sostienen las propiedades nuevas y solo ellas:

- **Enlaces cruzados** (`_link_md` devolviendo siempre el primer MD): mata solo
  `test_cada_enlace_apunta_al_TEXTO_DE_SU_documento`.
- **Paseo sin tope** (la versión anterior del ancestro): mata solo
  `test_un_alta_puede_crear_su_propia_raiz`.
- **Afirmación por enumeración de causas** (`sin_tipo and not hay_worklist`): mata solo
  `test_con_worklist_RANCIA_tampoco_afirma_que_todo_esta_clasificado`.

Un mutante que mata **más** de lo que le toca está mal apuntado y no acredita la propiedad.

### Y lo que el revisor levantó sin llamarlo hallazgo

Dos divergencias documentales, ambas confirmadas contra la fuente y **arregladas en esta
remediación**:

1. El comentario de `ensure_case` seguía diciendo que validar ahí *«cubre también la puerta
   que nadie ha escrito todavía»* — una afirmación que la **R1 ya había desmentido** con
   `move_to_city`, y que la R2 desmiente otra vez con `intake_manual`. Ahora dice su alcance
   real: **el sumidero del alta nominal**, con las otras puertas enumeradas. Un enunciado más
   ancho que lo que la función puede prometer es peor que ninguno: invita a no escribir la
   guarda que falta.
2. El §3(c) del diseño rev. 2 describía la contención como **léxica**, cuando ya son las dos
   mitades y la léxica dejó de ser `_bajo`. Corregido en la **rev. 3**.
