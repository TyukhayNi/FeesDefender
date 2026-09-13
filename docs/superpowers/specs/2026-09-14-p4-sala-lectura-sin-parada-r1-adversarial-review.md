---
tipo: revision-adversarial
objeto: core/sala_lectura.py
objeto_rev: "1"
commit: 2c9333f
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: 2ee1
sha256_informe: 68f9fd3a16c5f04a0f0ee03789607b43027db9d0e1853cdf07639c72c885284f
adjudicado_en: docs/superpowers/specs/2026-09-14-p4-sala-lectura-sin-parada-design.md §4
---

# Acta — R1 adversarial sobre el diff de P4 (sala de lectura sin parada + `[APER-61]`)

Objeto: el **diff** `c407fcb..2c9333f`. Se archivaron las dos copias con `git archive` en
`C:/t/p4-obj-004923/{base,head}`; el revisor trabajó sobre ellas, sin `.git` y sin tocar el
repositorio real.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, `model_reasoning_effort=high` |
| Objeto | `C:/t/p4-obj-004923/{base,head}` — 1323 y 1325 ficheros |
| `sha256` de los dos ficheros pedidos, al abrir y al cerrar | idénticos; el revisor comparó además los dos árboles por bytes |
| `sha256` del informe | `68f9fd3a16c5f04a0f0ee03789607b43027db9d0e1853cdf07639c72c885284f` — **fichero crudo y bloque canonicalizado coinciden**, y coinciden con el que el propio revisor devolvió en su último mensaje |
| Veredicto | **NO-SHIP** |
| Hallazgos | 7 (2 `ALTO`, 4 `MEDIO`, 1 `BAJO`) — **7 confirmados, 0 refutados** |

**La ronda encontró dos regresiones del propio diff, y la frontera que las explica es una
sola.** Apliqué el centinela nuevo (`es_decision`) a lo que se **escribe** y no a lo que se
**lee**: marcar el residuo con `08` y confianza `0.0` fija cómo *nace* un pendiente y no dice
nada de los `08` ya persistidos con confianza `1.0` —que escribía el código base— ni de qué
otros campos puede pisar un reintento. Tres caminos leían ese estado (`clasificar_caso`,
`aplicar_clasificacion`, `rellenar_worklist`) y los tres lo malinterpretaban de forma
distinta: H-01, H-02 y H-03 son la misma frontera en tres sitios.

**Y una cosa que conviene registrar sobre el método:** antes de que volviera el informe
encontré por mi cuenta un cuarto sitio de esa misma familia —la guarda de `preparar-residuo`,
que quedó **inerte**— y lo remedié en `2c9333f`. El mandato se lo dijo al revisor para que no
gastara la ronda en él y buscara la familia en otros sitios; encontró tres más. Esa es la
forma que tiene de rendir la pregunta «¿de qué frontera es esto un ejemplo?».

## 0. Mandato, literal

<!-- mandato-literal:inicio:2ee1 -->
# Mandato — revisión adversarial R1 del diff de P4 (sala de lectura sin parada + `[APER-61]`)

Eres el revisor adversarial. Tu trabajo es **encontrar defectos**, no aprobar. El autor
(Claude) adjudicará cada hallazgo contra la fuente; tú no tienes la última palabra sobre
corrección, pero **un defecto que no señales no lo mira nadie más**.

## 0. Higiene del workdir (léelo primero)

Tu directorio de trabajo (`-C`) debe contener **solo este `MANDATO.md`** y lo que tú
escribas. Si encuentras cualquier otro fichero, **no lo leas** y decláralo en la primera
línea de tu informe. Un fichero anterior a este mandato no puede ser respuesta a este
mandato.

## 1. El objeto

Dos copias congeladas, en **rutas absolutas** (NO están dentro de tu workdir; tu workdir
debe estar vacío salvo este mandato y lo que tú escribas):

- `C:/t/p4-obj-004923/base/` — el árbol en `c407fcb` (`origin/main`, antes del cambio).
- `C:/t/p4-obj-004923/head/` — el árbol en `2c9333f` (después del cambio: **dos** commits, `d484b27` y `2c9333f`).

**SOLO LECTURA. No escribas ni un byte dentro de esas dos rutas.** Si necesitas
ejecutar algo que escriba, copia a tu workdir. Al abrir y al cerrar, calcula y reporta el
`sha256` de estos dos ficheros para acreditar que no los mutaste:

- `C:/t/p4-obj-004923/head/core/sala_lectura.py`
- `C:/t/p4-obj-004923/head/tests/test_sala_lectura_p4_sin_parada.py`

No hay `.git` en las copias (es deliberado). No puedes acreditar la genealogía; acredita
**contenido**.

## 2. Puedes ejecutar, y deberías

Hay un Python de sistema con `pytest`, `yaml`, `typer`, `httpx`, `filelock`, `dotenv`:

```
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

Copia `C:/t/p4-obj-004923/head/` (o los ficheros que necesites) a tu workdir y corre allí lo que quieras.
Dos avisos medidos: usa `--basetemp` **relativo dentro de tu workdir** (tu sandbox no puede
crear `C:\t\...`, y MAX_PATH tumba tests que están bien), y **no tienes `pytest-randomly`**,
así que no puedes correr las dos semillas — si es relevante, decláralo SIN VERIFICAR.

**Un revisor que no corre no refuta: deja SIN VERIFICAR.** Si no puedes comprobar algo,
dilo con esas palabras. No lo des por bueno ni por malo.

## 3. Qué cambia el diff, en las palabras del autor

Dos piezas sobre `core/sala_lectura.py`, un módulo declarado `[DEPRECADO 2026-06-18] … No
ampliar` en su primera línea (decisión de alcance ya tomada por el titular del repo:
alinear dentro del módulo, sin extraer a uno compartido).

**Pieza 1 — `[APER-61]`: la identidad se enruta por PARTE.** `_KEYWORDS` mandaba
`dni`/`nie`/`pasaporte`/`nota simple`/`titularidad` a `06. PBC` y `hoja de visita` a
`01. ACTIVACIÓN`. El runbook (`docs/RUNBOOK_APERTURA_EXPEDIENTE.md`, bloque `[APER-61]`)
dice: identidad/KYC del **comprador** → `03. OFERTAS`; del **vendedor** → `01. ACTIVACIÓN`;
y **solo** los Anexos 1 y 2 del vendedor → `06. PBC`. El autor afirma que la tabla era la
causa codificada del síntoma documentado («`03. OFERTAS` con 1 documento y `06. PBC` con
28»).

**Pieza 1b — la frontera del token.** El match era `substring in` y ahora es una regex con
límite de palabra **solo a la izquierda** (`\b` + token, nada a la derecha). El autor
afirma que las dos mitades están medidas: sin `\b` izquierdo, `Companies_House_….md` casaba
`nie` («Compa*nie*s») y `carrer_carrasco_….eml` casaba `arras` («c*arras*co»); con `\b`
también a la derecha se perdían `oferta2.pdf`, `ofertas recibidas.pdf` y
`PBC1 JOSEP GIRBAU.pdf`.

**Pieza 2 — la parada deja de ser una verja.** `organizar` abortaba antes de
`render_indices` y `poblar_sala_lectura` si quedaba residuo. Ahora el residuo recibe
`08. PENDIENTE DE CLASIFICAR` con confianza `0.0` y la sala se monta entera. La clave
`detenido_por_residuo` **se retira** del dict devuelto y se sustituye por `n_pendientes`.

**La frontera que eso destapó.** Varios caminos preguntaban «¿esto ya está clasificado?» y
cada uno lo decidía por su cuenta (por confianza, por `Tipo in TAXONOMIA_EV`, por `not
tipo_documental`). Como `08` **sí** está en `TAXONOMIA_EV`, dejaron de coincidir. El autor
introdujo `es_decision(tipo)` como sitio único y la usa en `aplicar_clasificacion`,
`_hashes_residuo` y tres helpers de test.

## 4. Dónde mirar con más ganas

Ataca por aquí, y por donde tú veas:

1. **La retirada de `detenido_por_residuo`.** ¿Queda algún consumidor vivo en el árbol `head` que la
   lea y ahora reviente o —peor— la lea con `.get()` y siga en silencio? Busca en todo el
   árbol, no solo en `core/` y `scripts/`.
2. **`es_decision` como frontera única.** ¿Hay **más** sitios en el árbol `head` que sigan decidiendo
   «está clasificado» por su cuenta y que el autor no haya migrado? Un `if e.tipo_documental`,
   un `in TAXONOMIA_EV`, un `if not x.tipo_documental`, un `confianza >=`… en cualquier
   módulo (`core/verificar_apertura.py`, `core/sala_lectura_estado.py`,
   `core/catalogo_documental.py`, la UI, los scripts). Este es el hallazgo más probable.
3. **El efecto sobre los ficheros ya materializados.** `poblar_sala_lectura` hace
   `old.unlink()` cuando una fila migra de ruta, y `_nombre_canonico` mete el slug del tipo
   en el nombre (`_TIPO_SLUG`). Con la pieza 1, ¿puede un documento **ya copiado** en un
   expediente real cambiar de nombre y disparar ese `unlink`? ¿Bajo qué condición exacta?
   ¿Está esa condición cubierta por algún test? El autor midió «0 ficheros movidos» sobre
   diez expedientes, pero **no puedes ver esos expedientes**: lo que te toca es decir si el
   razonamiento se sostiene **por construcción** o solo sobre esa muestra.
4. **`_CONF_PENDIENTE = 0.0` y la aritmética de confianza.** ¿Hay algún sitio que trate
   `confianza` con `or` (`(e.confianza or 0)`), con truthiness, o que distinga `None` de
   `0.0` y donde el cambio de `None` → `0.0` altere el comportamiento? `0.0` es falsy.
5. **Idempotencia.** ¿Correr `organizar` dos, tres veces sobre el mismo caso converge?
   ¿Y con la worklist a medio rellenar? ¿Y si el letrado escribe `08` a mano?
6. **La regex.** ¿`\b` se comporta como el autor cree con tokens que empiezan por letra
   acentuada, con `ñ` (`señal`), con tokens multi-palabra (`nota simple`, `justificante de
   pago`, `hoja de visita`)? ¿Y con el `.replace("_", " ")` previo? Construye casos.
7. **El arnés `tests/_mutantes_p4.py`.** El autor declara «20 mutantes, 20 muertos, 1
   superviviente declarado». **Verifícalo corriéndolo** (`python -m tests._mutantes_p4`
   desde tu copia). ¿Algún mutante está **mal apuntado** —muere por un test que no es el
   suyo—? ¿Algún mutante es trivial (no representa un defecto plausible)? ¿Falta algún
   mutante para una decisión del diff que nadie fija? El superviviente declarado, ¿está
   bien declarado o es una excusa?
8. **Los tests modificados.** El diff cambia asertos en cuatro ficheros de test existentes.
   Por cada cambio: ¿es una **corrección** legítima (el test medía la representación vieja
   del residuo) o es un **debilitamiento** (el test cubría algo que ahora no cubre nadie)?
   Mira en particular `test_cli_organizar_YA_NO_se_detiene_con_residuo`, que invierte un
   aserto, y el caso paramétrico `"Nota simple registral.pdf"`.
9. **Lo que el diff dice de sí mismo.** El commit y el runbook afirman números («59
   documentos», «90,5 %», «55 %», «123 fotos → 0», «5.498 recogidos»). No puedes
   comprobarlos contra los expedientes reales (no están en la copia). Lo que **sí** puedes
   es comprobar si alguna afirmación es **internamente** incoherente, o si el código
   contradice la prosa que lo describe. Señálalo si lo hay.

## 4-bis. Un defecto que el autor YA encontró y remedió (no lo cuentes como hallazgo)

Auditando su propio diff, el autor encontró que la guarda de `preparar-residuo` en
`scripts/sala_lectura.py` —la que impide decir «Sin residuo: todo el catálogo está
clasificado»— preguntaba `not e.tipo_documental` y se volvió **inerte** al marcar el
residuo con `08`. Está remediado en el segundo commit, con test. **Te lo digo para que
no gastes la ronda en él y para que busques la MISMA FAMILIA en otros sitios: guardas
que siguen ahí, siguen verdes, y ya no pueden dar el otro valor.**

## 5. Formato del informe

Escribe **`INFORME.md`** en tu workdir. Estructura:

```
# Informe R1 — P4 sala de lectura (c407fcb → 2c9333f)

## Higiene y no-mutación
- sha256 al abrir / al cerrar de los dos ficheros pedidos.
- Ficheros ajenos encontrados en el workdir (si los hay).

## Qué pude ejecutar y qué no
(lo que corriste, con salidas; y lo que quedó SIN VERIFICAR, con la razón)

## Hallazgos
Por cada uno:
- **ID** (H-01, H-02…), **severidad** (CRÍTICO / ALTO / MEDIO / BAJO),
- **fichero:línea** relativa al árbol `head`,
- **qué está mal**, **cómo se manifiesta** (entradas concretas → salida concreta),
- **cómo lo comprobaste** (comando y salida, o «por lectura»),
- **qué frontera** representa (no solo el ejemplo).

## Lo que revisé y NO encontré defectuoso
(explícito: dónde miraste y qué te convenció)

## VEREDICTO
```

**La última línea del informe debe ser el veredicto, y exactamente una de estas tres
palabras, sin nada más:**

```
SHIP
SHIP-CON-CAMBIOS
NO-SHIP
```

No la adornes ni la expliques en esa línea. Es la palabra literal que se archiva.

## 6. Recordatorios

- No confundas «no me gusta el diseño» con «es un defecto». Si es preferencia, márcala BAJO
  y dilo.
- No propongas reescribir el módulo: su deprecación y el alcance ya están decididos.
- Ante cada hallazgo, pregúntate **«¿de qué frontera es esto un ejemplo?»** y escríbelo. El
  autor va a remediar la frontera, no el caso que describas.
- Si algo te parece correcto pero no puedes probarlo, **SIN VERIFICAR**. Nunca «refutado».
<!-- mandato-literal:fin:2ee1 -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:2ee1 -->
AVISO DE HIGIENE: al abrir el workdir encontré `_stdout.log`, además de `MANDATO.md`; no leí su contenido ni lo utilicé como evidencia.

# Informe R1 — P4 sala de lectura (c407fcb → 2c9333f)

## Higiene y no-mutación

- Objeto: contenido de las copias congeladas `C:/t/p4-obj-004923/base/` y `C:/t/p4-obj-004923/head/`. No contienen `.git`: la genealogía y los commits declarados quedan **SIN VERIFICAR**; no los infiero de sus nombres.
- Comparación completa por bytes: nueve ficheros distintos entre los árboles. Evidencia generada en `diff.txt`: el módulo, el CLI, el runbook, cuatro tests existentes, el test P4 y el arnés nuevo.
- El único fichero ajeno encontrado en el workdir fue `_stdout.log`. La advertencia anterior no atribuye su origen. No es una respuesta a este mandato.
- No escribí en los dos árboles objeto. Las ejecuciones, casos sintéticos, mutaciones y registros se hicieron dentro de este workdir. El módulo base se cargó también mediante `compile`/`exec` en memoria, con dependencias de la copia head que no cambian en el diff, y con los casos dirigidos a `probe_data/`.
- SHA-256 de los dos ficheros exigidos:

| Fichero absoluto | Al abrir | Al cerrar |
|---|---|---|
| `C:/t/p4-obj-004923/head/core/sala_lectura.py` | `e092d9906934b3d285d62741f174fb76d8b8c1d9170b9a1fd74aa58b1f92cfac` | `e092d9906934b3d285d62741f174fb76d8b8c1d9170b9a1fd74aa58b1f92cfac` |
| `C:/t/p4-obj-004923/head/tests/test_sala_lectura_p4_sin_parada.py` | `be93ebfa92ff6838da16629275d82b361c2c6652b755d16d5c4cb29e5dd1d9b7` | `be93ebfa92ff6838da16629275d82b361c2c6652b755d16d5c4cb29e5dd1d9b7` |

El informe se entrega en UTF-8 sin BOM, con LF y un único salto final. Su digest se devuelve por separado.

## Qué pude ejecutar y qué no

Python usado en todas las ejecuciones: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`. En los ejemplos siguientes, `PY` significa ese ejecutable. Para las ejecuciones se fijaron `PYTHONDONTWRITEBYTECODE=1` y `PYTHONUTF8=1`. Los `--basetemp` son relativos y resuelven dentro del workdir.

### Pruebas originales

Desde `copy/`, selección completa de `tests/test_sala_lectura*.py`, `tests/test_catalogo_documental.py` y `tests/test_verificar_apertura*.py`:

```powershell
$tests = Get-ChildItem tests/test_sala_lectura*.py,tests/test_catalogo_documental.py,tests/test_verificar_apertura*.py | ForEach-Object { $_.FullName }
& PY -m pytest -o addopts='' -q --tb=short -p no:cacheprovider --basetemp=../s777 --randomly-seed=777 $tests
& PY -m pytest -o addopts='' -q --tb=short -p no:cacheprovider --basetemp=../s31337 --randomly-seed=31337 $tests
```

Salidas y códigos comprobados:

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Primera pasada, sin semilla fijada | 303 pasadas, 1 omitida; exit 0 | `baseline.log` |
| Semilla 777 | `303 passed, 1 skipped in 51.38s`; exit 0 | `seed777.log` |
| Semilla 31337 | `303 passed, 1 skipped in 51.47s`; exit 0 | `seed31337.log` |

**Diferencia constatada respecto del aviso del mandato:** este intérprete sí tiene `pytest-randomly` 5.0.0. Comprobé la distribución instalada y la opción `--randomly-seed`, y ejecuté ambas semillas. No son dos corridas de la suite completa del repositorio: son dos corridas de la selección indicada.

El omitido es `tests/test_verificar_apertura.py:1592`, marcado `slow` y excluido sin `--runslow`. Esa prueba y la suite completa quedan **SIN VERIFICAR**. No extrapolo el verde de esta selección al resto del proyecto.

### Mutación y sondas propias

1. Desde `run/`:

   ```powershell
   $env:PYTEST_ADDOPTS='--basetemp=../mt -p no:cacheprovider'
   & PY -u -m tests._mutantes_p4
   ```

   Resultado literal, exit 0:

   ```text
   20 mutantes, 20 muertos.
   SUPERVIVIENTES/ROTOS: ninguno
   [DECLARADO, no matado] el AVISO del CLI sobre los pendientes (`scripts/sala_lectura.py`)
   ```

   Registro completo: `mutantes.log`. La primera copia hecha con `shutil.copytree` no permitía escribir los ficheros copiados; el arnés abortó antes de mutar. Creé `run/` por lectura/escritura de bytes, comprobé que era escribible y ejecuté ahí el arnés. No cuento el intento abortado como prueba superada.

2. Auditoría adicional de las muertes, en otra copia `audit/`: `PY -u audit_mutants.py`, con pytest por objetivo y JUnit por mutante, `--basetemp=../at`. Los 20 objetivos mutados fallan por aserciones, con código 1; cero errores de colección/setup en los JUnit. Se registran 32 casos paramétricos o individuales fallidos en total. Registros: `audit_logs/M01.xml` a `M20.xml` y sus `.log`; resúmenes `audit_mutants.log` y `audit_mutants_10_20.log`. El primer auditor propio se detuvo antes de M10 porque buscaba un bloque LF en bytes CRLF; se corrigió la lectura de texto y se continuó. Ese error del auditor no se atribuye al arnés revisado.

3. `PY -u extra_mutants.py`: tres mutaciones independientes, restaurando los bytes después de cada una, contra las 38 pruebas constituidas por todo `test_sala_lectura_p4_sin_parada.py`, `test_clasificar_por_keyword` y `test_cli_organizar_YA_NO_se_detiene_con_residuo`:

   | Mutante adicional | Resultado |
   |---|---|
   | X1: retirar solamente `anexo 1` y `anexos 1` | `38 passed`; exit 0 |
   | X2: retirar solamente `ficha comprador` | `38 passed`; exit 0 |
   | X3: sustituir la condición del aviso CLI por `if False:` | `38 passed`; exit 0 |

   Evidencia: `extra_mutants.log`, `X1_anexo1.log`, `X2_ficha.log`, `X3_aviso.log`. La supervivencia está medida sobre esas 38 pruebas, no sobre la suite completa.

4. Desde el workdir: `PY probes.py` y `PY extra_probes.py`, ambos exit 0. Casos nuevos en `probe_data/`, con nombres sintéticos, mtime fijado y fuentes de bytes conocidos. Las salidas de `probes.log` y `extra_probes.log` acreditan los ejemplos de los hallazgos, cinco corridas de idempotencia, transición base→head, CLI real, Unicode y materialización. Los scripts crean casos: para repetir desde cero debe usarse otra raíz de casos sintéticos.

5. Búsqueda de todo el árbol, incluidos ocultos, skills, plugins y documentación, mediante Python porque `rg` no estaba disponible. `search.txt` conserva las coincidencias de `tipo_documental`, confianza, taxonomía y `detenido_por_residuo`; se hizo además una búsqueda de `n_residuo` y llamadores de `organizar`.

No accedí a CRM, Drive ni expedientes reales. **SIN VERIFICAR:** las mediciones sobre 1.352 documentos/diez expedientes, los 59 documentos, el 90,5 %, el 55 %, las 123 fotos, los 5.498 recogidos y los cero movimientos observados. Sí contrasté su coherencia con el código y entre textos. La cifra 5.498/5498 no aparece en las copias examinadas; el texto del commit que la contenga no está disponible aquí.

## Hallazgos

### H-01 — ALTO — Un `08` persistido con confianza alta sigue congelado y desaparece de la worklist

- **Fichero:línea:** `core/sala_lectura.py:247` y `:326`; contrato nuevo en `:140` y contador final en `:1210`.
- **Qué está mal:** las dos guardas siguen usando tipo truthy + confianza. `es_decision` se usa para asignar la confianza de una fila entrante, pero no para decidir si una fila existente ya está resuelta. Un estado producido por el código base —`08. PENDIENTE DE CLASIFICAR`, confianza `1.0` tras aplicar una worklist— no se normaliza con P4.
- **Manifestación concreta:** creé `ambiguo.pdf`; con el módulo base ejecuté clasificar, escribí `08` en la worklist y organicé. El catálogo quedó en `08`, confianza `1.0`, con una copia. Con head ofrecí una nueva corrección `07. RECLAMACIONES` en la worklist y llamé a `aplicar_clasificacion(..., solo_residuo=True)`: `n_aplicadas=0`. `organizar` devolvió `n_pendientes=0`, `SKIP_UNCHANGED=1`; el tipo siguió en `08` y `_hashes_residuo` devolvió `[]`, porque la regeneración de la worklist eliminó la fila.
- **Comprobación:** `PY probes.py`, salida `legacy08` en `probes.log`. No inyecté artificialmente la confianza alta de este caso: la produjo base.
- **Frontera:** el nuevo centinela debe gobernar también la lectura de estados persistidos, no solamente las escrituras nuevas. Los tests nuevos fijan cómo nace un pendiente, pero no la migración de los `08` anteriores. El `aplicar` explícito sin `solo_residuo` todavía permite corregirlo; lo que falla es el ciclo automático y su afirmación de cero pendientes.

### H-02 — ALTO — Organizar sustituye una fecha humana por una inferida si el documento sigue en `08`

- **Fichero:línea:** `core/sala_lectura.py:270`–`:273`, en interacción con `:334` y `:343`.
- **Qué está mal:** bajar la confianza de `08` fuerza el reintento, y ese reintento sobrescribe incondicionalmente `fecha_doc`/`fecha_fuente`. La ausencia de decisión sobre el tipo se convierte en ausencia de decisión sobre la fecha.
- **Manifestación concreta:** documento `2025-03-20 sin pistas.pdf`; worklist con Tipo `08` y Fecha `2020-01-02`. `aplicar` deja la fecha en `2020-01-02`; el `organizar` siguiente la cambia a `2025-03-20` y materializa `2025-03-20_pendiente_fecha_revisada.pdf`, mientras la worklist sigue diciendo `2020-01-02`. Si el letrado vacía Fecha, `aplicar` deja `None`, pero `organizar` repone igualmente `2025-03-20`.
- **Comprobación:** salidas `fecha08` de `probes.log`. Contraprueba con base: salidas `fecha_base` de `extra_probes.log`; base conserva respectivamente `2020-01-02` y `null` después de organizar. Es una regresión reproducida, no una diferencia de estilo.
- **Frontera:** la procedencia y autoridad de cada campo deben conservarse independientemente de la confianza en la categoría. El test existente de fecha vaciada solo comprueba la celda de la worklist; sigue verde porque la celda se conserva mientras el catálogo, el nombre y la cronología usan otra fecha.

### H-03 — MEDIO — `08` vuelve a ofrecerse al LLM, pero su celda bloquea la clasificación mejorada

- **Fichero:línea:** `core/sala_lectura.py:583`; interacción con `:456` y `:628`.
- **Qué está mal:** `_hashes_residuo` reconoce correctamente `08` como no decidido, pero `rellenar_worklist` sigue tratando cualquier celda no vacía como intocable. La selección ofrece el documento y el escritor rechaza la respuesta por esa misma marca.
- **Manifestación concreta:** para un documento con MD, un primer `chat_fn` devuelve `{tipo: 08, confianza: 1}` y escribe una celda. Tras organizar, un segundo `chat_fn` devuelve `{tipo: 07. RECLAMACIONES, confianza: 1}`. Se procesa un documento (`n_docs=1`), pero se escriben cero celdas (`n_celdas=0`); el Tipo de la worklist continúa en `08`, y organizar continúa con un pendiente. Repetir no mejora ese estado.
- **Comprobación:** `PY probes.py`, salida `llm08`. El primer `08` fue escrito por el propio camino LLM, no por una decisión humana que el escritor necesitara proteger.
- **Frontera:** «celda presente» y «decisión tomada» siguen siendo equivalentes para el escritor, aunque dejaron de serlo para el selector. La política de preservar fechas/partes humanas no exige congelar un Tipo que el contrato nuevo define como ausencia de decisión. La edición manual de la celda sigue disponible; el camino programático no converge hacia la respuesta mejorada.

### H-04 — MEDIO — La parte explícita del comprador se ignora; el Anexo 2 del comprador se clasifica ahora erróneamente como PBC

- **Fichero:línea:** `core/sala_lectura.py:53`–`:58`; fuente: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:753`–`:760` y contradicción en `:761`–`:774`.
- **Qué está mal:** la tabla no consulta la parte ni siquiera cuando el nombre la expresa. El runbook limita la excepción a los Anexos 1/2 del vendedor y menciona expresamente que el Anexo 2 de compradores no es esa excepción. La nueva entrada genérica `anexo 2` decide PBC antes de cualquier otra consideración.
- **Manifestación concreta:** `Anexo 2 compradores.pdf` pasa de `None` en base a `06. PBC` en head, y `DNI comprador.pdf` pasa de `06. PBC` a `01. ACTIVACIÓN`; ninguno queda en `03. OFERTAS`. En `clasificar_caso` esas categorías reciben confianza `0.9`, quedan fuera de la worklist y se preservan en las siguientes corridas.
- **Comprobación:** comparación base/head ejecutada en `probes.py`, salidas `regex`; asignación de confianza y salto posterior comprobados por lectura en `:261`–`:264` y `:247`.
- **Frontera:** un valor por defecto para una parte desconocida no puede prevalecer sobre una parte conocida. No cuestiono aquí el alcance decidido ni exijo inferir la parte de un nombre opaco. El ejemplo aporta precisamente la señal que la prosa dice que falta. El Anexo 2 del comprador es, además, un falso positivo nuevo y contrario al ejemplo explícito de la fuente.

### H-05 — MEDIO — La tolerancia de sufijos convierte los Anexos 10–19 y 20–29 en los Anexos 1/2

- **Fichero:línea:** `core/sala_lectura.py:53` y `:70`.
- **Qué está mal:** todos los tokens reciben la misma política de sufijo abierto. Eso puede conservar plurales y numeraciones de `oferta` o `PBC`, pero cambia el identificador numérico de una excepción limitada a los Anexos 1 y 2.
- **Manifestación concreta:** `Anexo 10.pdf` devuelve `06. PBC` en head y `None` en base; coincide con `anexo 1`. `Anexo 20 titularidad.pdf` también devuelve PBC por el token nuevo `anexo 2`, antes de poder aplicar el nuevo destino de titularidad. Se extiende a `Anexos 12.pdf`, etc., por construcción de la regex.
- **Comprobación:** `probes.log` contiene la ejecución de los dos primeros ejemplos. La generalización a los demás números es por lectura de `re.escape(t)` sin guarda derecha. La regla hermana de la skill sí distingue el número mediante `[^0-9]` (`.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:53`).
- **Frontera:** sufijo léxico y continuación de un identificador numérico no son la misma cosa. No propongo añadir indiscriminadamente un `\b` derecho: los verdaderos positivos de `oferta2`/`ofertas`/`PBC1` deben conservarse.

### H-06 — MEDIO — M03 y M04 tienen muertes reales, pero sus mutaciones compuestas dejan reconocimientos nuevos sin fijar

- **Fichero:línea:** `tests/_mutantes_p4.py:51` y `:56`; fixtures en `tests/test_sala_lectura_p4_sin_parada.py:76` y `:90`.
- **Qué está mal:** M03 retira simultáneamente Anexo 1 y Anexo 2, pero el ejemplo del Anexo 1 contiene además `PBC`, por lo que ese ejemplo pasa aunque se retire su token. M03 muere por Anexo 2. M04 retira hoja de visita y ficha comprador, pero solo pregunta por hoja de visita. Su nombre, además, dice «vuelve a ser activación», mientras la mutación real devuelve `None` para esa hoja.
- **Manifestación concreta:** retirando solo `anexo 1`/`anexos 1` o retirando solo `ficha comprador`, las 38 pruebas seleccionadas permanecen verdes en cada caso. Se perderían `Anexo 1.pdf` o `Ficha comprador.pdf` sin que esos objetivos de mutación lo detectasen.
- **Comprobación:** `extra_mutants.py`; X1 y X2, ambos exit 0 / `38 passed`. Auditoría JUnit: M03 muere por `Anexo 2 titular real.pdf`; M04 por `Hoja de visita firmada.pdf`.
- **Frontera:** una mutación que elimina varias ramas y mata un test solo demuestra sensibilidad a alguna de ellas. No demuestra la cobertura individual de todas. **El número 20/20 del arnés es reproducible y no lo impugno**; lo que falta es separar estas decisiones y sus entradas de prueba.

### H-07 — BAJO — La misma muestra aparece como 57 % y 55 % de residuo

- **Fichero:línea:** `tests/test_sala_lectura_p4_sin_parada.py:23`, frente a `core/sala_lectura.py:1154` y `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:817`.
- **Qué está mal:** el encabezado del nuevo test atribuye un 57 % a los mismos 1.352 documentos; el módulo y el runbook atribuyen un 55 %. No identifican mediciones o definiciones diferentes que permitan conciliarlo.
- **Manifestación:** dos cifras distintas para el residuo de la misma muestra en la documentación añadida por el diff.
- **Comprobación:** por lectura y búsqueda completa; coincidencias conservadas en la revisión. No puedo determinar cuál es la correcta sin la muestra.
- **Frontera:** una medición publicada necesita una definición y versión inequívocas. Es una incoherencia documental, no prueba de que el clasificador falle ese porcentaje.

## Lo que revisé y NO encontré defectuoso

### Respuesta al punto 1: retirada de `detenido_por_residuo`

La búsqueda completa no deja consumidores ejecutables vivos de esa clave. En head quedan docstrings, tests que exigen su ausencia y documentos históricos con código o resultados antiguos. El antiguo llamador de Streamlit ya no está activo. El CLI de organizar usa `n_pendientes`, y el uso de `n_residuo` en el subcomando clasificar corresponde al retorno de `clasificar_caso`, que sí lo conserva. No encontré un `.get()` vivo que silencie esta retirada. Los consumidores externos a estos árboles quedan **SIN VERIFICAR**.

### Respuesta al punto 2: frontera de clasificación

Los defectos encontrados son H-01 y H-03. No encontré una guarda equivalente oculta en `core/verificar_apertura.py`, `core/sala_lectura_estado.py`, `core/catalogo_documental.py` o la UI: sus comprobaciones relevantes son respectivamente conteo/artefactos, existencia/conteo de ficheros, persistencia del catálogo y presentación del estado. No afirman que todos los tipos estén decididos. Los usos de confianza en `local_organizer` y en el matcher de procuradores pertenecen a otros modelos, no reciben el nuevo `CatalogEntry` pendiente.

La guarda de `scripts/sala_lectura.py:130`, anunciada como ya remediada, usa `es_decision` y su test pasa; no la cuento como hallazgo. La validación `tipo in TAXONOMIA_EV` de aplicar sigue siendo legítima: `08` es un valor admisible aunque no sea una decisión.

### Respuesta al punto 3: materialización y `old.unlink()`

**Los cero movimientos de una muestra no acreditan inmovilidad universal.** La condición exacta, en la ruta ordinaria de organizar, es:

1. La fila entra en reclasificación: no la salta `tipo_documental` truthy + `(confianza or 0) >= 0.8`; y una corrección válida aplicada antes puede, a su vez, hacerla saltar.
2. La nueva categoría cambia el slug que produce `_nombre_canonico`, o cambia algún otro componente del destino final asignado. Para la pieza 1, un DNI que pase de PBC a ACTIVACIÓN cambia `_pbc_` por `_activacion_`.
3. La fila se planifica: fuente presente, no descartada por deduplicación; el destino no es un directorio ocupado. Hay `ruta_sala_lectura` previa y difiere del nuevo destino.
4. La copia al nuevo destino termina. **Solo entonces** se considera borrar el anterior; `old.unlink()` se ejecuta si el anterior existe y su clave normalizada no pertenece a ningún destino nuevo.

`probes.log` compara dos filas materializadas bajo base: con confianza `0.9`, head hace `SKIP_UNCHANGED` y conserva el nombre PBC; bajando explícitamente la confianza a `0.5`, head hace `MOVED=1`, crea el nombre ACTIVACIÓN y elimina el anterior. La bajada se declara como preparación sintética del caso de frontera; no afirmo que la muestra real la tuviera.

También medí el riesgo de editar una copia: con bytes distintos en el fichero materializado, la migración repone los bytes de `00_Input` y elimina los bytes de la copia editada. Ese mecanismo de reconstrucción ya existía, y su intención está cubierta por los tests de migración; no lo presento como pérdida nueva e incondicional de originales debida a P4. P4 sí lo vuelve alcanzable normalmente al corregir un documento que acaba de entrar con `_pendiente_`.

Los tests de sala plana/R2 cubren migración ordinaria, copiar antes de borrar, colisiones y protección de destinos nuevos. No encontré un test de transición **base→head por el cambio de keywords** con una fila ya materializada y confianza baja. El test P4 de recuperación reemplaza la fuente por otros bytes y solo reclasifica: no prueba este `unlink`. Mi sonda cubre esa condición, no los expedientes reales.

Para las filas ordinarias que base ya resolvió con `0.9` o `1.0`, el mismo salto explica también por qué el cambio de tabla **no corrige retrospectivamente** la categoría antigua. «59 documentos se mueven» puede describir una comparación de reglas sobre nombres; no demuestra 59 migraciones ejecutadas por organizar en un catálogo persistido.

### Respuesta al punto 4: cero y aritmética de confianza

No encontré una regresión debida a evaluar `0.0` como falsy en una suma o sustitución por defecto de este catálogo. En las dos guardas, `(None or 0)` y `(0.0 or 0)` quedan por debajo del umbral y producen el mismo resultado. El defecto de H-01 es la confianza alta persistida, no la falsedad de cero. El de H-02 es el alcance excesivo del reintento que habilita la confianza baja.

### Respuesta al punto 5: idempotencia

Sonda de cinco corridas con dos documentos opacos:

```text
1: n_pendientes=2, COPY=2
2: n_pendientes=2, SKIP_UNCHANGED=2
3, tras completar solo una fila: n_pendientes=1, MOVED=1, SKIP_UNCHANGED=1
4: n_pendientes=1, SKIP_UNCHANGED=2
5: n_pendientes=1, SKIP_UNCHANGED=2
worklist final: una fila
```

La sala converge en ese recorrido y conserva el residuo parcial. Un `08` nuevo introducido por aplicar adquiere confianza cero y vuelve a contarse: el test nuevo lo prueba. Eso no acredita la migración de un `08` antiguo (H-01), la conservación de sus demás campos (H-02) ni la aceptación de una respuesta mejorada por rellenar (H-03). La estabilidad de bytes/nombres de una sala ya generada no equivale por sí sola a corrección semántica.

### Respuesta al punto 6: regex

El límite izquierdo funciona con Unicode: probé `señal`, `captación`, `exposé` en la función real. También probé directamente `\bárbol` y `\bñandú`: inicio y posición tras un `_` convertido a espacio casan; `xárbol`/`xñandú` no. Esos dos tokens no están en la tabla real: esta última prueba comprueba el mecanismo, no una categoría inexistente.

`nota_simple.pdf`, `hoja_de_visita.pdf` y `justificante_de_pago.pdf` casan correctamente después del reemplazo de `_`. `Companies_House.md` y `carrer_carrasco.eml` ya no casan, y `oferta2.pdf` conserva su categoría. Se mantienen los tests de plurales y `PBC1`.

Nombres en NFD como `señal.pdf` no casan; comprobé que tampoco casaban en base. La normalización a espacios no colapsa separadores múltiples ni cambia guiones en espacios; no atribuyo esas limitaciones previas al nuevo `\b`. El defecto nuevo de la política uniforme está en los identificadores numéricos de H-05.

### Respuesta al punto 7: arnés y superviviente declarado

Se reprodujo el resultado 20/20. La auditoría independiente confirma que los 20 mueren por aserciones de sus funciones objetivo, no por un test ajeno ni por errores de colección/setup. El arnés solo distingue código cero/no cero y no conserva el motivo; esta comprobación adicional es la que permite precisar la causa de las muertes observadas. M11 comprueba la ausencia efectiva de copias al reintroducir la parada; M10 comprueba la fecha inferida del pendiente. No encontré un mutante de sintaxis deliberadamente inválida para inflar el número. M08/M09 solapan el umbral de confianza, y M15/M16 solapan caminos hacia la misma congelación: aportan sensibilidad, no veinte propiedades independientes.

Los problemas concretos de puntería parcial son H-06. M20 no elimina literalmente la guarda de sin material: cambia el booleano que devuelve; fija la señal de estado, no la ausencia de escrituras por sí solo.

El «superviviente declarado» del arnés es en realidad **un hueco descrito en texto**, sin transformación ejecutable. Reproduje su mutación como X3: las 38 pruebas seleccionadas siguen verdes. `extra_probes.py` muestra además la diferencia en el CLI real: con un documento pendiente, original sale con código 0 y `[AVISO] 1 doc(s)`; el mutante sale con código 0 y solo «Sala de lectura organizada».

Es correcto declarar la falta de cobertura. No se sostiene el motivo «solo cambia TEXTO, no una decisión»: el aviso es el mecanismo que sustituye a la parada para comunicar que queda trabajo. M12 fija el dato retornado por core, no su comunicación por el CLI. Un test de comportamiento puede exigir un conteo y ruta de corrección accesibles sin congelar la redacción literal. La guarda corregida de preparar-residuo también queda fuera de los 20 mutantes: tiene test, pero no tiene una mutación equivalente en este arnés. No afirmo que carezca de cobertura funcional.

### Respuesta al punto 8: cada grupo de cambios en tests existentes

| Fichero y líneas head | Evaluación |
|---|---|
| `tests/test_sala_lectura.py:91` y `:93` — Nota simple y nuevo Anexo 1 | Corrección legítima del destino de la nota simple contra el canon vendedor. La prueba añadida de Anexo 1 no aísla el token, por H-06. No demuestra cumplimiento de la parte comprador. |
| `tests/test_sala_lectura.py:141` — residuo `None` → `08` y confianza cero | Actualización legítima de representación; añade una exigencia de confianza. |
| `tests/test_sala_lectura.py:200` — tipo inventado rechazado | Legítima: sigue exigiendo cero aplicaciones y el valor previo, ahora `08`. |
| `tests/test_sala_lectura.py:339`–`:366` — invertir parada | Cambio de contrato expresamente autorizado. Mantiene inventario recursivo, exige exactamente una copia, slug pendiente y bytes correctos. No es una relajación a «cualquier fichero existe». El nombre `test_cli_...` es engañoso: llama al core, no a `CliRunner`. |
| `tests/test_sala_lectura.py:373` — sin residuo | Legítima sustitución de la clave retirada; las comprobaciones de sala/copia permanecen. |
| `tests/test_sala_lectura.py:414`–`:426`, `:743`, `:768` — helpers de MD/residuo | Adaptación necesaria: el filtro antiguo dejaba de crear/localizar el MD del pendiente. La selección conserva el nombre/hash del escenario, no rebaja sus asertos posteriores. |
| `tests/test_sala_lectura.py:485` — LLM con baja confianza | Legítima actualización del valor esperado. Conserva cero celdas y cero aplicaciones. |
| `tests/test_sala_lectura.py:841`, `:848` — segunda corrida | Legítimo cambio a 1→0 pendientes. Ya no se exige una parada, porque se retiró. El montaje/corrección se comprueba además en P4 y en la sonda de cinco corridas. |
| `tests/test_sala_lectura.py:868` — acciones al construir catálogo | La nueva exigencia directa de acciones es más fuerte que la condición antigua, que podía satisfacerse por detenerse. |
| `tests/test_sala_lectura_cero_acciones.py:91` | Legítimo: cero pendientes, sin_material falso y acciones reales permanecen exigidos. |
| `tests/test_sala_lectura_r1_adversarial.py:79`–`:87` | Helper de residuo adaptado; conserva las condiciones particulares de los tests. Su test de fecha vaciada no cubre catálogo tras aplicar `08`: hueco expuesto por H-02, no aserto eliminado por este diff. |
| `tests/test_sala_lectura_residuo_sin_texto.py:51` | Helper adaptado; conserva la selección por nombre y la creación del MD de prueba. |

No encontré un debilitamiento de esos asertos para ocultar un rojo. Sí encontré huecos de interacciones nuevas, detallados arriba. El verde de todos estos tests es compatible con esos defectos.

### Respuesta al punto 9: afirmaciones del diff

- El 57 % frente al 55 % es una inconsistencia interna concreta: H-07.
- «Identidad por PARTE» y «en el CLI dejó de fallarse» exceden lo implementado: H-04. La salvedad de nombres opacos no explica ignorar `compradores` explícito.
- La comparación con la skill tiene una base mecánica verificable: `preclasificar.clasificar_por_patron` usa `screenshot|captura` para fotos y devuelve RECLAMACIONES por defecto, sin criterio de extensión. Ello permite los resultados narrados, pero **no prueba** 90,5 % ni 123→0 sin sus entradas.
- La palabra «entera» no anula la deduplicación, `MISSING_SRC` ni `DST_OCUPADO_POR_DIRECTORIO` preexistentes. Tampoco añade `_MANIFIESTO.md`: el motor sigue sin producirlo. No presento esa carencia conocida, anterior y fuera de las dos piezas como hallazgo nuevo de P4.
- No hay evidencia disponible para convertir las cifras de muestra en garantías generales de calidad, ausencia de movimientos o completitud. La condición de movimientos se ha verificado aparte con entradas sintéticas.

## VEREDICTO

El montaje con residuo funciona y la retirada de la clave no deja consumidores vivos en el árbol. Sin embargo, el diff conserva una ruta que oculta pendientes persistidos y añade una regresión que sustituye fechas humanas, además de los defectos de clasificación y convergencia detallados. Los verdes y el 20/20 no cubren esas fronteras. La corrección requiere cambios antes de integrar; Claude debe adjudicar cada hallazgo contra la fuente.

NO-SHIP
<!-- informe-literal:fin:2ee1 -->

## 2. Evidencia verificada por mí

- **Cadena de custodia del informe.** Recalculé el `sha256` del fichero crudo y del bloque
  canonicalizado (`
`→`
`, sin saltos de sobra, UTF-8): los dos dan
  `68f9fd3a16c5f04a0f0ee03789607b43027db9d0e1853cdf07639c72c885284f`, que es el que el revisor devolvió por separado en su
  último mensaje. Antes de leerlo comprobé que el proceso había terminado —la señal es
  `_ultimo_mensaje.txt`, no la existencia de `INFORME.md`—, porque un digest solo significa
  algo sobre un fichero terminado.

- **La primera ronda no llegó a correr, y la culpa era del mandato.** Monté las copias
  *dentro* del workdir y las referencié como `../base/` y `../head/`, contradiciendo a la vez
  la cláusula de higiene que exige un workdir con solo el mandato. El revisor paró y preguntó
  en vez de inventarse la ruta — que es lo correcto. Se relanzó con rutas absolutas y el
  workdir limpio. Coste: una corrida.

- **Los siete hallazgos, adjudicados contra la fuente.** Reproduje H-01, H-02, H-03, H-04 y
  H-05 con tests que se pusieron rojos antes de tocar el código (`tests/test_sala_lectura_p4_r1.py`),
  y H-06 con la corrida del arnés, que sacó los mutantes compuestos a la luz en cuanto se
  separaron. H-07 es lectura.

- **Lo que el revisor declaró SIN VERIFICAR, y lo cubrí yo:** las mediciones sobre los 1.352
  documentos. No tiene acceso al Drive, así que las contrastó por coherencia interna y dijo
  —correctamente— que no las daba por buenas. Yo las re-medí con el **código real de los dos
  lados** (el de `HEAD` y el de `c407fcb` cargado del árbol congelado), no con la tabla
  simulada del script de medición: **87 documentos cambian de categoría**, de los cuales 59
  son el movimiento `06. PBC` → `01. ACTIVACIÓN` que había afirmado. Los otros 28 los había
  omitido y se añadieron a la prosa antes de la ronda.

- **Su punto 3 corrige una afirmación mía y lo acepto.** Yo dije «0 ficheros movidos» sobre
  diez expedientes; él respondió que una muestra no acredita inmovilidad universal y enumeró
  la condición exacta en cuatro pasos. Tiene razón en la forma de decirlo: lo que sostiene la
  seguridad **por construcción** es que `poblar_sala_lectura` copia antes de borrar y protege
  los destinos nuevos, no que mi muestra diera cero.

## 3. Lo que NO cubre esta ronda

- **La suite completa.** El revisor corrió una selección de 304 tests con las dos semillas
  (777 y 31337), no los 5.527 del repo. La suite entera, con las dos semillas, la corre
  `session_close` y es responsabilidad del autor.
- **El arnés que el revisor verificó tenía 20 mutantes**; los 31 finales incluyen los que
  fijan sus propios remedios (M22-M31) y la separación de los compuestos, que entraron
  **después** de su objeto congelado. Su «20/20 reproducido» vale para `2c9333f`, no para el
  árbol final. Lo que sí es suyo es la crítica que los originó.
- **Los expedientes reales.** Ninguna de las dos partes ejecutó nada contra el Drive.
