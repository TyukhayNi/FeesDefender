---
tipo: revision-adversarial
objeto: diff eb8ac09..7872dcf — identidad sin teclado (abrir_caso.py + case_manager.update_meta)
objeto_rev: "1"
commit: 7872dcf
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: p7r1
sha256_informe: 337f045fea0b05779c71f6a45fc4d075e9ebff809ac31e89c6bc1b4ced9c7a2f
adjudicado_en: docs/superpowers/plans/2026-09-11-identidad-sin-teclado.md §3
estado: historico
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# Acta de revisión adversarial R1 — identidad sin teclado

- **Objeto revisado:** diff `eb8ac09..7872dcf` — `scripts/abrir_caso.py`, `core/case_manager.py` y sus tests
- **Ronda:** R1 de 2 (el radio de daño se reclasificó al leer este informe: la pieza podía destruir datos de cliente)
- **Revisor:** Codex (CLI 0.153.4), dos copias `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev-p7-083941/wd/INFORME.md`, 37602 bytes
- **Hallazgos:** 8 — 1 ALTO, 4 MEDIOS, 3 BAJOS; **8 confirmados, 0 refutados**
- **Remediado en:** `docs/superpowers/plans/2026-09-11-identidad-sin-teclado.md` §3

**Por qué existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.

**Una limitación de esta ronda que es culpa de mi mandato, y hay que decirlo.** El §4 del encargo
le permitía crear copias y temporales, y su última línea decía «no escribas ningún otro fichero».
El revisor interpretó el conflicto de forma conservadora —correctamente— y **no ejecutó pytest**:
su control positivo quedó SIN VERIFICAR y lo declaró como tal. El mandato de la R2 lo corrigió, y
esa ronda sí ejecutó las cuatro corridas.

**Custodia.** Dos árboles `git archive` sin `.git`, en un directorio de ronda con nombre
irrepetible comprobado vacío antes de lanzar. Los `sha256` de los tres ficheros revisados coinciden
al abrir y al cerrar. El digest se computó tras el `exit 0` del proceso.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:p7r1 -->
HIGIENE: al abrir el workdir encontré MANDATO.md y también _stdout.log; no leí _stdout.log.

# Revisión adversarial R1 — identidad sin teclado

Objeto: `../base/` frente a `../head/`. Todas las anclas de código siguientes corresponden a `head`, salvo indicación expresa. Revisión efectuada el 2026-09-11; fecha comprobada con `Get-Date`.

## Hashes de apertura

Medidos mediante `Get-FileHash -Algorithm SHA256` antes de leer el diff:

| Fichero | SHA-256 |
|---|---|
| `head/scripts/abrir_caso.py` | `E27F18D29306DFF1E876F8A2F3D6F27E2CA7189A36B88B4ACB289005E5BFCB31` |
| `head/core/case_manager.py` | `31A5F27ADBDB082E56303CB220B7B0C2F47BED972C6CBB2AB8708F70CF73E7DD` |
| `head/tests/test_case_manager_update_meta.py` | `2EA32903C657203877055BF954B6F44753C21A9A2DD08B7C8B35DCBAFF509A99` |

## Alcance y método efectivamente ejecutado

Ejecuté desde el workdir:

```powershell
& 'C:/Program Files/Git/usr/bin/diff.exe' -ru ../base ../head
```

Terminó con código 1, correspondiente a diferencias. Informó exactamente de cuatro ficheros modificados y uno nuevo:

- `core/case_manager.py`.
- `docs/MEJORAS_FUTURAS.md`.
- `scripts/abrir_caso.py`.
- `tests/test_abrir_caso_cli.py`.
- `Only in ../head/tests: test_case_manager_update_meta.py`.

No apareció ningún otro cambio. La comparación AST adicional encontró en el CLI una función nueva y tres modificadas (`_direccion_de_la_carpeta`; `_alta_crm`, `_autoderivar_drive_ev`, `main`); en `case_manager`, dos funciones nuevas y ninguna función anterior modificada. Hay 53 tests en el fichero CLI de head, de los cuales 8 son nuevos, y 13 en el nuevo fichero de metadatos: 66 tests en total.

**Límite de ejecución:** §4 permite copias y temporales, pero la última instrucción prohíbe escribir cualquier otro fichero. Pedí aclaración expresamente; no recibí respuesta durante esta revisión. No interpreté el silencio como autorización. No creé copias, directorios temporales ni ficheros de tests. Por tanto, **NO ejecuté la suite ni el control head-tests/base-code con ninguna semilla**. Sus resultados son SIN VERIFICAR.

Sí ejecuté las funciones reales de head mediante el intérprete indicado, con `-B`, cargando los módulos desde la copia congelada. Las sondas P1–P17 sustituyeron únicamente las fronteras de E/S necesarias: ruta/localizador y almacenamiento en memoria para el índice; API de Drive y CRM por dobles explícitos. `read_md`, el serializador YAML, `update_meta`, `_escribir_indice_atomico`, el parser y las funciones del CLI conservaron su implementación real, salvo la inyección de fallo/intercalación descrita en cada prueba. Un audit hook rechazó escrituras reales, creación/borrado de directorios, renombrados, procesos hijos y conexiones de red. Estas sondas **acreditan transformaciones y control de flujo; no acreditan comportamiento físico del filesystem ni sustituyen pytest**.

Un intento adicional de `pytest.main(['--collect-only', '-q', '-p', 'no:cacheprovider', '--basetemp=tmp', '--randomly-seed=777', ...])` bajo ese guard abortó antes de recoger tests: la carga automática de Faker llegó a `platform.system()`, cuyo intento de abrir `os.devnull` con `O_RDWR` fue rechazado por el guard (`RuntimeError: WRITE BLOCKED`). No es un fallo del diff, ni una corrida de tests, ni evidencia de fuga de sus fixtures.

## Hallazgos

### H-01 — ALTO — Se destruye una nota ajena que comparte el prefijo del campo

**Ancla:** `core/case_manager.py:496` y `:498`; sonda P2.

Entrada del cuerpo:

```markdown
# Notas
- Cuantía: comprobar oferta, NO BORRAR

## Sede
- Cuantía: _(pendiente)_
```

Llamada: `update_meta('C', cuantia=42)`.

Salida ejecutada:

```markdown
# Notas
- Cuantía: 42

## Sede
- Cuantía: _(pendiente)_
```

El informe devuelve `cuerpo=['cuantia']`, `sin_linea=[]`. Se perdió «comprobar oferta, NO BORRAR», y la línea del índice quedó pendiente. La búsqueda toma la primera coincidencia de todo el documento y no verifica su sección. También alcanza líneas dentro de bloques de código. La misma forma afecta a los siete prefijos de `_LINEAS_DEL_CUERPO`.

Es un defecto introducido por el actualizador, no una imputación al registrador anterior. Contradice directamente la conservación de notas del §2.6. Antes de enviar, la localización debe distinguir una línea propiedad del índice de una coincidencia ajena y debe abstenerse ante ambigüedad. No basta con ampliar el test que añade una nota al final sin prefijos coincidentes.

### H-02 — MEDIO — Una sección ficticia o duplicada recibe el dato y el informe lo da por insertado

**Ancla:** `core/case_manager.py:501`, `:511` y `:513`; sondas P3 y P4.

Entrada P3: un bloque cercado que contiene `## Sede`, seguido de la sección real, sin línea de cuantía. Tras `update_meta('C', cuantia=42)`:

````markdown
```md
## Sede
- Cuantía: 42
```

## Sede
Texto real
````

Resultado: `insertadas=['cuantia']`, `sin_linea=[]`. La cuantía se insertó en un ejemplo de código; la sección real no la contiene.

Entrada P4: `## Sede\nEjemplo histórico\n\n## Sede\nSede vigente\n`. El dato se inserta en la primera sección, antes de «Ejemplo histórico». No se detecta que hay dos candidatas.

El caso canónico de una sola sección funciona. El defecto está en tratar la igualdad textual de una línea como prueba suficiente de ubicación Markdown. `referencia_crm`, que se inserta antes de `## Partes`, usa la misma selección ambigua.

### H-03 — MEDIO — Se aceptan campos con representación existente, pero se dejan sus otros hogares desactualizados sin avisar

**Ancla:** `core/case_manager.py:411`, `:422`, `:492`; plantilla en `:183`; consumidor de expedientes en `:1121`. Sonda P5.

Escenario: índice con título «Original», estado `instruccion`, expediente 9 en el frontmatter superior, su espejo y el cuerpo. Llamada:

```python
update_meta('C', estado='archivado', titulo='Nuevo',
            drive_ev_folder_id='NEW', sudespacho_expedientes=[{'id': '20'}])
```

Resultado ejecutado:

- `meta.estado` y `estado` superior pasan a `archivado`; el cuerpo sigue diciendo `estado **instruccion**`.
- `meta.titulo` pasa a «Nuevo»; el encabezado sigue siendo `# Original`.
- `meta.sudespacho_expedientes` contiene 20; el frontmatter superior y el cuerpo siguen listando 9. `get_case_status` consulta precisamente la lista superior.
- El informe trae las cuatro claves en `frontmatter`, pero `cuerpo=[]`, `insertadas=[]`, `sin_linea=[]`.

El comentario «campo sin representación en el cuerpo» de `:493` es incorrecto para varios campos que omite el mapa: título, estado, identificadores Drive, remoto rclone y expedientes sí tienen representación. No se exige que se reutilice ni amplíe `_actualizar_cuerpo`; se exige que el contrato público declare o implemente las representaciones que promete actualizar. Para campos realmente exclusivos de metadatos, omitir `sin_linea` sí resulta razonable.

### H-04 — MEDIO — Un índice malformado se convierte silenciosamente en otro índice; puede perder frontmatter o relegar el lock al cuerpo

**Ancla:** `core/case_manager.py:476`–`:486`; `core/utils.py:255`, `:275`–`:283`. Sondas P7–P9.

Entrada P7, fichero truncado sin cierre de frontmatter:

```text
---
case_id: C
meta:
  checkout_nonce: N
```

Después de `update_meta('C', cuantia=42)`, se obtiene:

```text
---
meta:
  cuantia: 42
case_id: C
---

---
case_id: C
meta:
  checkout_nonce: N
```

El texto previo sigue en los bytes simulados, pero ahora está en el cuerpo; el nuevo frontmatter carece del nonce. El informe solo dice `sin_linea=['cuantia']`, sin advertir del índice truncado. **No atribuyo a esta llamada el truncamiento original ni una pérdida nueva de un lock que ya pudiera leerse correctamente antes**: el defecto es normalizar el archivo defectuoso sin diagnosticarlo y sin conservar su significado como metadatos.

Entrada P8, YAML válido cuyo valor superior es una lista:

```text
---
- nota_a_preservar
---
# Cuerpo
```

La lista desaparece por completo: `read_md` la extrae y `update_meta` la reemplaza por `{}`. Resultado: frontmatter nuevo con cuantía y case_id, seguido únicamente de `# Cuerpo`. Tampoco hay aviso sobre el dato descartado.

En cambio, P9 (`meta: [` con delimitadores completos) lanza `yaml.parser.ParserError` antes de escribir. Un `meta` que no pueda convertirse a `dict` también puede lanzar en `:479`. Las fronteras de corrupción no tienen un comportamiento uniforme. La conservación ordinaria comprobada en P1 no prueba estas entradas.

### H-05 — MEDIO — Una cuantía no escrita después del alta no se repara al reintentar

**Ancla:** `scripts/abrir_caso.py:674`–`:679`, `:742`–`:756`; sonda P16.

Escenario ejecutado con CRM simulado: creación devuelve `9999`; `register_expediente` registra ese ID; `update_meta` lanza `OSError('disk full')`. Primera salida:

```text
[AVISO] Alta CRM falló (OSError('disk full')): Drive+intake ya completados, referencia_crm queda pendiente + TODO.
```

La etiqueta «Alta CRM falló» confunde una creación externa completada con una sincronización local fallida. Segundo intento con la misma cuantía:

```text
CRM ya registrado (element=extrajudiciales, id=9999), no se re-da de alta
```

Contadores tras dos llamadas: `create_expediente=1`, `update_meta=1`. El retorno de idempotencia impide reintentar la escritura local. Aunque el problema de disco fuera transitorio, el código no vuelve a consultar esa frontera.

No se pide repetir el alta externa. Hay que separar el resultado del alta de la persistencia local y proporcionar una recuperación que no quede anulada por la idempotencia. El test nuevo solo cubre éxito en la primera llamada.

### H-06 — BAJO — La comparación de W-codes omite la normalización de espacios que ya define el modelo

**Ancla:** `scripts/abrir_caso.py:830`; `core/casos/workspace_model.py:439`–`:441`. Sondas P11 y P17.

Entrada: nombre `Calle - W-ABCDE`, `w_code=' W-ABCDE '`. `_direccion_de_la_carpeta` devuelve `None` y acusa una carpeta de otro expediente. Sin embargo, `CaseRef.normalizar(' W-ABCDE ')` devuelve `W-ABCDE`, exactamente el código extraído del nombre.

Las minúsculas sí se admiten. El defecto de espacios exige teclear una dirección que era derivable. No rompe una invocación antigua con dirección explícita: afecta a la frontera nueva. No hay fundamento para tratar `WABCDE` o un guion distinto como equivalentes: el normalizador canónico tampoco lo hace.

### H-07 — BAJO — La documentación nueva contradice tanto el backlog corregido como el resultado de su test de conservación

**Anclas:** `tests/test_case_manager_update_meta.py:53`–`:63`; `core/case_manager.py:385`–`:390`, `:410`; `tests/test_case_manager_update_meta.py:3`–`:6`, `:67` y `:75`; `docs/MEJORAS_FUTURAS.md:10669`.

Escenario del test `test_ensure_case_sigue_sin_poder_reponerla`: un índice con cuantía pendiente recibe `ensure_case(..., cuantia=73140.0)`; las aserciones exigen que siga pendiente. **Que ese test pase confirma que la vía antigua no repone la cuantía.** Su docstring afirma lo contrario: «Si este test se pusiera verde [...] ensure_case cambió» y «Mientras siga rojo [...]». La interpretación de colores está invertida. Esta conclusión procede de los asertos; el resultado efectivo del test sigue SIN VERIFICAR.

Además, el código y el fichero de tests nuevos siguen identificando #184 con la referencia CRM. La entrada real #184 trata de cobertura de sondeos de correo. El bloque corrector del backlog reconoce el error, pero las nuevas citas no lo aplican.

La generalización «ensure_case solo fija los campos cuando CREA» también es demasiado amplia: `core/case_manager.py:868`–`:889` ya actualiza `tipo_caso`, `direccion`, `id_go` y `ciudad` en casos existentes. El diagnóstico sí es correcto para `cuantia` y `referencia_crm`. No se propone cambiar `ensure_case`; se propone describir su alcance real.

### H-08 — BAJO — La conservación no es textual: se eliminan comentarios YAML y espacios de borde del cuerpo

**Ancla:** `core/utils.py:259` y `:270`, invocados desde `core/case_manager.py:516`. Sondas P6 y P10.

Entrada P10: frontmatter con `# Nota crucial del abogado` y `ajena: 1 # manual`. Al actualizar la cuantía, la clave ajena conserva su valor, pero ambos comentarios desaparecen. Entrada P6: cuerpo sin frontmatter que empieza por dos espacios antes de «Nota del abogado»; el resultado pierde esos espacios por `body.strip()`.

Es comportamiento heredado del serializador reutilizado, no una modificación nueva de `write_md`. Se señala porque la promesa de dejar «todo lo demás intacto» excede lo que esta nueva API puede garantizar con ese escritor. Las claves ajenas ordinarias conservan su valor semántico; los comentarios y el formato no.

## A. Las diez afirmaciones, una por una

| Nº | Dictamen y evidencia |
|---|---|
| 1 | **VERIFICADA en código y sonda.** `:800` solo deriva si `direccion is None`; P12 conserva `EXPLICITA` aunque el nombre contiene «Calle». `main :1032` recibe el cuarto valor. No se ejecutó el test CLI completo. |
| 2 | **VERIFICADA en código y sonda para nombres sin W-code.** Parser `core/intake_drive.py:348`–`:377`; helper CLI `:824`–`:829` devuelve `None`, nombra la carpeta y pide el flag. `main :1041`–`:1044` caza `None`. El aviso es impreciso si sí hay W-code pero el prefijo está vacío: también dice que no encuentra el delimitador. |
| 3 | **PARCIAL.** Un W-code diferente del extraído produce aviso y `None` (P11; `:830`–`:835`). La comparación no normaliza espacios, y solo compara el primer W-code que el parser reconoce: H-06 y tabla de fronteras. |
| 4 | **VERIFICADA con alcance acotado.** Las dos rendiciones normales retornan `None`, sin excepción propia. La dirección explícita evita esta derivación; por ello no encontré una regresión en invocaciones antiguas válidas causada por esos dos retornos. La frase no equivale a que cualquier tipo de entrada arbitrario o cualquier fallo de API sea imposible. Las direcciones derivadas inválidas sí son rechazadas después por la validación preexistente. |
| 5 | **VERIFICADA en sonda de la función.** P12, con `team_id`, `codigo_caso` y `sufijo` completos: dirección ausente → una consulta de carpeta; dirección explícita → cero consultas. Condición en `:781`. Un sufijo ausente se deriva sin API en `:777`. |
| 6 | **REFUTADA como garantía general.** P1 conserva notas ordinarias, claves ajenas superiores y de `meta`, expedientes y cinco campos de lock. H-01 destruye una nota; H-04 y H-08 limitan la conservación del frontmatter y del texto. Además, `:486` puede añadir `case_id` aunque el llamador no lo nombre. |
| 7 | **PARCIAL.** Hay informe y para los siete campos mapeados, sin línea ni sección, se añade `sin_linea` (`:503`–`:505`). No identifica ambigüedades ni código cercado; varios campos aceptados con representación real son omitidos silenciosamente: H-02 y H-03. |
| 8 | **VERIFICADA para las entradas contractuales normales.** `:460`–`:474`: campos desconocidos y llamada vacía → `KeyError`; caso ausente o índice ausente → `FileNotFoundError`. P15 ejecutó esas cuatro ramas con localizador/almacenamiento simulado; ninguna llegó al escritor. No se ha probado su comportamiento físico bajo carreras de borrado. |
| 9 | **VERIFICADA para un alta nueva completada sin fallo local.** La llamada está en `scripts/abrir_caso.py:748`, después de crear y registrar. La escritura real de cuantía se ejerció en P1. El cableado CRM completo se probó con dobles para la rama fallida, no mediante el test de artefacto en disco. En skip, alta ya registrada o gate declinado no se llama; H-05 documenta el reintento incompleto. |
| 10 | **VERIFICADA respecto al código.** `diff -ru` y la comparación de las funciones AST muestran `_actualizar_cuerpo` sin modificación. Sigue siendo la función de tres fragmentos en `core/case_manager.py:215`–`:263`, invocada por `_actualizar_indice :378`; el nuevo método escribe directamente en `:516`. La separación preserva el alcance de los registradores; no justifica las omisiones del propio actualizador. La intención del autor no es una propiedad ejecutable. |

El parser realmente era anterior al diff y ya tenía consumidor: `streamlit_app.py:22` lo importa y `:1676` lo llama.

## B. Regresión y fronteras

### Pérdida de datos y checkout

La sonda P1 construyó un índice con:

- Clave superior desconocida con lista y diccionario anidado.
- `meta.proyeccion_local=True`, desconocida por `CaseMeta`.
- `estado_repositorio='prestado'` y `checkout_user`, `checkout_nonce`, `checkout_timestamp`, `checkout_maquina`.
- Lista superior de expedientes con `doc_ids`, espejo en `meta` y sección Markdown de expedientes.
- Sección de navegación con wikilink, sección extra del letrado y otro wikilink dentro de la nota.

Tras actualizar solo `cuantia`, la salida medida fue:

```text
unknown True
meta_unknown True
lock True
body_exact_except_field True
exp True
```

La comparación del cuerpo ignoró espacios externos mediante `strip()`; no acredita conservación byte a byte. **No se perdió contenido semántico en ese caso ordinario. Sí se perdió contenido en P2 y P8, y comentarios en P10.** El lock parseable sobrevive si no se nombra entre los campos y no hay otro escritor concurrente. No confundí conservar sus campos con adquirir un mutex ni con autorizar un checkout.

### Escritura concurrente y atomicidad

`update_meta` no adquiere mutex ni verifica una versión del fichero. La precondición está documentada en `core/case_manager.py:399`–`:400`: lo adquiere el entrypoint. La única llamada productiva encontrada a `case_manager.update_meta` es la de `_alta_crm`; queda dentro de `mutex_sesion.sostenido` (`scripts/abrir_caso.py:1126`, `:1203`). **No encontré una carrera demostrada en ese recorrido normal.**

P13 ejerció la intercalación siguiente sin mutex, usando funciones reales y almacenamiento en memoria:

1. A lee el índice con `cliente=OLD`, `cuantia=None`.
2. B ejecuta y termina `update_meta('C', cliente='NEW')`.
3. A continúa `update_meta('C', cuantia=42)` con su lectura anterior.

Resultado: `{'cuantia': 42, 'cliente': 'OLD', 'checkout_nonce': 'LOCK'}`. Se perdió la actualización de B. La misma intercalación puede restaurar campos de lock antiguos si otro escritor los cambia después de la lectura de A. Es una **limitación comprobada del método sin su precondición**, no prueba de que falle el mutex de la CLI.

El escritor usa temporal en el mismo directorio y `os.replace` (`core/case_manager.py:323`–`:326`); no abre el destino para truncarlo. P14 inyectó un fallo después de escribir un temporal parcial: excepción propagada, original conservado, temporal eliminado en el doble de filesystem. Esto verifica el control de flujo de limpieza, **no la atomicidad física de Windows**.

El temporal se llama `._caso.<pid>.tmp`, no incluye identificador de hilo. Dos escritores del mismo proceso comparten ese nombre; dos procesos siguen expuestos a actualización perdida aun con temporales diferentes. No se midió esa carrera en disco. Tampoco se ejecutaron corte de proceso, fallo de `os.replace`, agotamiento real de disco ni durabilidad frente a pérdida de alimentación. No hay `fsync` en este camino. No doy por probado truncamiento físico del destino; sí la pérdida lógica de actualizaciones sin exclusión.

### Índices sin frontmatter, truncados y líneas insertadas

Un cuerpo ordinario sin frontmatter se conserva semánticamente y recibe un frontmatter nuevo con `meta` y `case_id` (P6); también se le puede insertar la línea si existe una sección reconocida. Un índice truncado se envuelve como cuerpo sin diagnóstico específico (H-04). YAML sintácticamente inválido con delimitadores completos lanza antes del escritor.

La inserción canónica busca el primer encabezado exacto y avanza por líneas vacías o que empiezan por `- `. No reconoce cercas, listas con continuación indentada ni significado de secciones duplicadas. Con una continuación indentada del último item, puede intercalar el nuevo item antes de dicha continuación, cambiando su asociación visual. Este último caso se deduce de `:511`; no se ejecutó. Los falsos encabezados y secciones duplicadas sí se ejecutaron (H-02).

### Derivación de dirección y W-code: resultados ejecutados

| Nombre de carpeta | W-code pedido | Resultado de `_direccion_de_la_carpeta` |
|---|---|---|
| `Calle - W-ABCDE` | `W-ABCDE` | `Calle` |
| `Calle W-ABCDE` | `W-ABCDE` | `None`: falta separador aceptado |
| `W-ABCDE - Calle` | `W-ABCDE` | `None` |
| `Calle - W-ABCDE - W-ZZZZZ` | `W-ABCDE` | `Calle`: ignora el segundo W-code |
| `Calle - W-ABCDE - W-ZZZZZ` | `W-ZZZZZ` | `None`: compara con el primero |
| `W-ABCDE - Calle - W-ZZZZZ` | `W-ZZZZZ` | `W-ABCDE - Calle`: el primer código queda dentro de la dirección |
| cadena vacía o solo espacios | `None` | `None`, con aviso |
| ` - W-ABCDE` | `W-ABCDE` | `None`; hay código, pero no dirección |
| `Calle - W-ABCDE` | `None` | `Calle`; no comprueba igualdad |
| `Calle - W-ABCDE` | cadena vacía | `Calle`; no comprueba igualdad |
| `Calle - w-abcde` | `w-abcde` | `Calle` |
| `Calle - W-ABCDE` | ` W-ABCDE ` | `None`, falsa discrepancia |
| `Calle - W-ABCDE` | `WABCDE` | `None` |
| `Calle s/n - W-ABCDE` | `W-ABCDE` | `Calle s/n`; el compositor posterior lanza `ValueError` |
| `Calle: 3* - W-ABCDE` | `W-ABCDE` | `Calle: 3*`; el compositor posterior lanza `ValueError` |

El parser solo acepta guion simple o en dash antes de `W-` y de 5 a 8 caracteres alfanuméricos en ese código (`core/intake_drive.py:348`–`:350`). Estas restricciones son anteriores al diff. No valida unicidad de W-codes en el nombre. La dirección puede incorporar un W-code inicial y posteriormente circular en la referencia; el ejemplo de la tabla demuestra la salida, no demuestra a qué expediente real pertenecería esa carpeta ambigua.

`None` para el flag es capturado posteriormente por `main :1041`. El string vacío no lo es: se comprueba `is None`, no falsedad. El helper no deriva el W-code ausente. La validación completa y los efectos posteriores de un flag vacío no se ejecutaron; no presento la composición aislada como apertura completada.

La dirección derivada **no se sanea silenciosamente**. `core/abrir_caso.py:53`–`:55` rechaza los caracteres prohibidos y `scripts/abrir_caso.py:1062`–`:1064` captura ese error antes de `ensure_case`. Esto evita atribuir al diff el defecto antiguo de carpeta partida por `/`.

## C. Cobertura y control positivo de los tests

### Estado de ejecución

| Instrumento requerido | Estado |
|---|---|
| Head, ambos ficheros, semilla 777 | SIN VERIFICAR: no ejecutado |
| Head, ambos ficheros, semilla 31337 | SIN VERIFICAR: no ejecutado |
| Tests de head sobre copia de base, semilla 777 | SIN VERIFICAR: no ejecutado |
| Tests de head sobre copia de base, semilla 31337 | SIN VERIFICAR: no ejecutado |

No existe un conteo medido de tests verdes, rojos o saltados. Los 66 son un censo AST, no un resultado de pytest. No se modificaron base ni head para poner tests nuevos sobre código antiguo.

### Control positivo individual: lo que puede decirse sin inventar una corrida

De los 21 tests añadidos, cuatro son **candidatos esperables a seguir verdes sobre base por conservación**:

1. `test_cli_drive_ev_direccion_explicita_gana`: el código viejo ya consumía la dirección explícita.
2. `test_cli_drive_ev_sin_folder_id_no_intenta_derivar`: el código viejo ya comprobaba `folder_id` y pedía `--direccion` ausente.
3. `test_cli_sin_alta_crm_la_cuantia_no_se_inventa`: skip ya evitaba el alta; `ensure_case` no recibía esa cuantía desde el CLI.
4. `test_ensure_case_sigue_sin_poder_reponerla`: documenta que el creador no repone cuantía. Es correcto conservar ese resultado; su docstring interpreta al revés el color (H-07).

**No afirmo que ninguno haya pasado efectivamente.** La predicción está anclada al código, no cumple el control positivo solicitado. Los otros 17 nuevos tienen estos mecanismos diferenciales previstos:

| Test | Diferencia que debería detectar frente a base; ejecución SIN VERIFICAR |
|---|---|
| `test_cli_drive_ev_autoderiva_direccion_del_nombre_de_carpeta` | Base no deriva dirección y falla por flag ausente |
| `test_cli_drive_ev_direccion_con_acento_se_conserva` | Mismo diferencial; exige apertura y dirección derivada |
| `test_cli_drive_ev_carpeta_sin_w_code_pide_el_flag` | Exige el nombre `1. ACTIVAS` en el aviso, no solo el error genérico ya existente |
| `test_cli_drive_ev_carpeta_de_otro_w_code_no_deriva` | Exige ambos códigos en el aviso nuevo |
| `test_cli_alta_crm_escribe_la_cuantia_en_caso_md` | Lee cuantía en YAML y cuerpo; base no tiene esa escritura |
| `test_la_cuantia_llega_al_frontmatter_y_al_cuerpo` | Base carece de `update_meta` |
| `test_la_referencia_crm_tambien_y_en_las_dos_claves` | Base carece de `update_meta` |
| `test_no_pisa_la_nota_escrita_a_mano` | Base carece de `update_meta` |
| `test_conserva_las_claves_ajenas_del_frontmatter` | Base carece de `update_meta` |
| `test_varios_campos_en_una_llamada` | Base carece de `update_meta` |
| `test_un_campo_que_no_es_de_casemeta_duele_aqui` | La ausencia de API daría `AttributeError`, no el `KeyError` exigido |
| `test_sin_campos_tambien_duele` | La ausencia de API daría `AttributeError`, no el `KeyError` exigido |
| `test_un_caso_que_no_existe_no_se_crea` | La ausencia de API daría `AttributeError`, no el `FileNotFoundError` exigido |
| `test_un_cuerpo_sin_la_seccion_lo_DICE_en_vez_de_adivinar` | Base carece de `update_meta` |
| `test_una_seccion_sin_la_linea_la_INSERTA_donde_toca` | Base carece de `update_meta` |
| `test_un_valor_None_vuelve_a_pendiente` | Base carece de `update_meta` |
| `test_no_toca_el_lock_de_checkout` | Base carece de `update_meta` |

Los 45 tests anteriores del fichero CLI no han cambiado de cuerpo AST. Para **cada uno** queda SIN VERIFICAR el resultado sobre ambas versiones; que no se hayan editado no demuestra que no los afecte el diff. No se cuentan como pruebas nuevas del cambio.

### ¿Algún test afirma probar otra cosa?

H-07 identifica la contradicción explícita entre el docstring y los asertos del test de `ensure_case`. No se ha medido un test pasando por una excepción equivocada. Los tests de rendición de dirección sí añaden discriminantes sobre el aviso que evitan confundirlos, por simple lectura, con el error genérico de la versión vieja.

El test `test_un_caso_que_no_existe_no_se_crea` comprueba el tipo de excepción, pero no inspecciona que el árbol siga vacío tras ella. El de conservación de notas verifica dos substrings, no igualdad del cuerpo entero. El de referencia usa un índice creado sin referencia: sí ejercería inserción, no reemplazo de una referencia ya presente. Son límites concretos de sus asertos.

### ¿Escriben fuera de tmp_path?

**No encontré escrituras directas fuera de `tmp_path` en los dos ficheros revisados**, por inspección:

- `tests/test_abrir_caso_cli.py:62`–`:98` y `tests/test_case_manager_update_meta.py:27`–`:33` fijan `case_locator._root` a `tmp_path/CASOS`.
- Los pulls simulados y sus marcadores se escriben bajo esa raíz (`test_abrir_caso_cli.py:81`, `:773`).
- `tests/conftest.py:164`–`:180` redirige el registro de workspaces, del que dependen los locks, a `tmp_path/_registro_workspaces`.
- El CLI simula creación CRM y consulta de duplicados; las fixtures contienen guardas de red (`test_abrir_caso_cli.py:43`–`:58`, `:97`).

La ausencia efectiva de escrituras indirectas fuera de tmp_path durante una corrida completa queda **SIN VERIFICAR**. El rechazo de `os.devnull` en la recogida fue causado por la carga de un plugin y el guard deliberadamente estricto, no por una escritura observada del test en producción.

## Inventario de lo NO cubierto por los tests del diff

Inventario por inspección de asertos y fixtures de los dos ficheros, no porcentaje de cobertura medido. No se afirma que toda la suite anterior carezca de tests de las primitivas reutilizadas.

1. **Pérdida de notas por prefijo**, líneas coincidentes en otra sección, dos líneas del mismo campo y coincidencias en código cercado: H-01.
2. **Ubicación de inserción** con encabezados dentro de código, secciones duplicadas, continuaciones de listas y texto entre encabezado e items; inserción de referencia ante `## Partes` ambiguo: H-02.
3. **Representaciones omitidas** de título, estado, remoto, IDs Drive y expedientes; coherencia de `sudespacho_expedientes` superior con `meta` y su consumidor: H-03.
4. **Frontmatter ausente, truncado, YAML no mapping, `meta` no mapping o YAML sintácticamente inválido**; conservación de comentarios, formato e indentación inicial/final: H-04 y H-08.
5. **Índice ausente en caso existente** (`FileNotFoundError` en `:474`), distinto de caso completamente ausente; mezcla de un campo válido y otro desconocido comprobando que no hay escritura parcial.
6. **Atomicidad y concurrencia del método nuevo**: fallo al escribir/renombrar, original intacto, limpieza, temporal compartido por hilos, actualización perdida y cambios de lock concurrentes.
7. **Conservación combinada** de claves desconocidas dentro de `meta`, valores anidados, estado D8 de expedientes y cuerpo variado completo. El test de clave ajena solo añade `bucket_override` superior. La sonda P1 amplía esa comprobación, pero no es un test entregado por el diff.
8. **Todos los campos de checkout/checkin**: el test comprueba cinco; no comprueba `checkout_notas`, `ultimo_checkin_timestamp` ni `ultimo_checkin_auditlog`.
9. **Informe completo**: valor de `index`, lista `frontmatter`, orden/coherencia con varios campos, mezclas de reemplazo/inserción/ausencia, segunda actualización idéntica y garantía de no duplicación.
10. **Campos y valores adicionales del mapa**: `cliente`, `jurisdiccion`, `drive_link`, reemplazo de referencia ya existente; `None` para campos diferentes de cuantía, string vacío, valores multilineales y tipos no previstos.
11. **La nueva causa única de consulta Drive**: solo falta dirección mientras código/team/sufijo están completos. P12 la midió, pero los tests nuevos de derivación omiten también los otros tres flags.
12. **API que devuelve None cuando solo falta dirección** y rendición con campos explícitos conservados. El test anterior de API caída mantiene dirección explícita y comprueba `--codigo-caso`.
13. **Nombres raros y normalización**: sin separador, W-code inicial, múltiples códigos, vacío/espacios, dirección vacía antes del código, W-code con espacios, `None`, vacío y formatos alternativos; caracteres Windows en la dirección derivada. El test anterior de `/` utiliza dirección explícita.
14. **Fallo local después del alta CRM y reintento**, rama `sin_linea` del aviso nuevo, y cuantía en caso ya registrado: H-05. El test de cableado solo ejercita éxito inicial.
15. **Prosa del backlog y correspondencia de numeración**. Ningún aserto añadido comprueba #184/#192 ni la exactitud del docstring del control de conservación.

## D. La prosa del backlog

La corrección añadida en `docs/MEJORAS_FUTURAS.md:10669`–`:10684` es **sustancialmente exacta** al dejar #184 y #192 abiertos:

- **#184**, `:8122`–`:8150`, se titula «Los dos sondeos del módulo de correo están al 0 % de cobertura». Trata de `sondeo_copias_mail.py`, `sondeo_join_gmail_crm.py` y sus funciones `censo`, `detalle`, `main`. Este diff no los modifica ni añade sus pruebas. No es una incidencia sobre la referencia CRM.
- **#192**, `:8567`–`:8601`, describe que el CLI fija `referencia_crm=ident.case_id` sin consultar la referencia real, en particular con `--crm skip`. Esa llamada sigue en `scripts/abrir_caso.py:1131`. `update_meta` permite una corrección explícita posterior, pero `_alta_crm` solo lo llama con `cuantia`; no corrige el origen del dato falso. No cierra #192.

Matiz: la entrada #192 también proponía una alternativa mínima para reponer el dato; la nueva API facilita esa parte técnica, pero no la conecta al flujo ni modifica la creación. Es correcto no dar la incidencia por cerrada.

No verifiqué la explicación histórica de «cuatro renumeraciones» ni su atribución a la bitácora del 101º: no hacen falta para comprobar el contenido actual de esas dos entradas. Las citas equivocadas que permanecen en código/tests están recogidas en H-07.

## Lo que NO pude verificar

- Las cuatro corridas de pytest y el control positivo individual medido; no hubo autorización aclaratoria para crear los temporales que esas corridas requieren frente a la prohibición final. No hay tests declarados verdes por inferencia.
- El escenario de archivo real en disco con contenido variado: se ejecutó su transformación completa en memoria, no una copia física. P1, P2 y P8 demuestran conservación/pérdida en la transformación del código, no propiedades del dispositivo.
- Atomicidad física, truncamiento por carreras reales, fallo de reemplazo en Windows, disco lleno real, corte abrupto del proceso y durabilidad. El fallo de escritor y la intercalación fueron inyectados en fronteras de E/S simuladas.
- Exclusión real entre procesos de la CLI, efectos físicos de un checkout y ejecución integral con dos escritores. Solo se acreditó el contexto del mutex en código y el riesgo de llamar al método sin él.
- Ausencia dinámica de escrituras fuera de `tmp_path` de todos los caminos de los tests.
- Red/Drive/CRM reales y efectos en Gmail. No se realizaron operaciones externas. Se contrastó la composición local de referencias y el control de flujo mediante dobles.
- Procedencia histórica de las renumeraciones del backlog.

No se escribieron archivos en base ni head. El único fichero creado deliberadamente por el revisor es este informe. `_stdout.log` era preexistente y no se leyó ni se modificó mediante mis comandos.

## Reproducción mínima de los hallazgos de transformación

El siguiente bloque reproduce los casos centrales sin escribir ficheros. Se puede pasar como here-string a `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe -B -` desde el workdir. Es una versión reducida del arnés ejecutado; las salidas P1–P17 citadas arriba proceden de las sondas efectivamente ejecutadas descritas en el informe.

```python
import os, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path('../head').resolve()))

def guard(event, args):
    if event == 'open':
        mode, flags = args[1], args[2]
        if ((isinstance(mode, str) and any(c in mode for c in 'wax+'))
            or (isinstance(flags, int)
                and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))):
            raise RuntimeError('WRITE BLOCKED')
    if event in ('os.mkdir', 'os.remove', 'os.rename', 'os.rmdir',
                 'subprocess.Popen', 'socket.connect'):
        raise RuntimeError('SIDE EFFECT BLOCKED: ' + event)

sys.addaudithook(guard)
from core import case_manager as cm
from core.casos import case_locator
from core.utils import build_frontmatter

class RAM:
    files = {}
    def __init__(self, name): self.name = name
    def __truediv__(self, part): return RAM(self.name + '/' + part)
    @property
    def parent(self): return RAM(self.name.rsplit('/', 1)[0])
    def exists(self): return self.name in self.files
    def mkdir(self, **kw): pass
    def read_text(self, **kw): return self.files[self.name]
    def write_text(self, value, **kw):
        self.files[self.name] = value
        return len(value)
    def unlink(self): del self.files[self.name]
    @staticmethod
    def replace(src, dst): RAM.files[dst.name] = RAM.files.pop(src.name)

base = RAM('C')
index = base / '00_Input' / '_caso.md'
cases = {
    'prefijo': '# Notas\n- Cuantía: comprobar oferta, NO BORRAR\n\n'
               '## Sede\n- Cuantía: _(pendiente)_\n',
    'codigo': '```md\n## Sede\n```\n\n## Sede\nTexto real\n',
    'duplicada': '## Sede\nEjemplo histórico\n\n## Sede\nSede vigente\n',
}
with patch.object(case_locator, 'buscar', return_value=base), \
     patch.object(cm.os, 'replace', RAM.replace):
    for name, body in cases.items():
        index.write_text(build_frontmatter({'case_id': 'C', 'meta': {}})
                         + '\n' + body)
        result = cm.update_meta('C', cuantia=42)
        print(name, result['cuerpo'], result['insertadas'], result['sin_linea'])
        print(index.read_text())
```

## Hashes de cierre

Recalculados con `Get-FileHash -Algorithm SHA256`; los tres coinciden con apertura:

| Fichero | SHA-256 | Comparación |
|---|---|---|
| `head/scripts/abrir_caso.py` | `E27F18D29306DFF1E876F8A2F3D6F27E2CA7189A36B88B4ACB289005E5BFCB31` | Igual |
| `head/core/case_manager.py` | `31A5F27ADBDB082E56303CB220B7B0C2F47BED972C6CBB2AB8708F70CF73E7DD` | Igual |
| `head/tests/test_case_manager_update_meta.py` | `2EA32903C657203877055BF954B6F44753C21A9A2DD08B7C8B35DCBAFF509A99` | Igual |

El motivo concreto para no enviar es H-01: una actualización de cuantía puede destruir una nota del letrado y dejar desactualizada la línea que debía cambiar. H-02 y H-03 también requieren delimitar el alcance del actualizador. La falta de pytest reduce la cobertura de este informe; no convierte esos contraejemplos ejecutados en pruebas refutadas. La adjudicación corresponde al autor contra las fuentes y escenarios indicados.

VEREDICTO: NO-SHIP
<!-- informe-literal:fin:p7r1 -->

## 2. Evidencia verificada por mí, contra la fuente

La adjudicación razonada, hallazgo a hallazgo, vive en el §3 del plan hermano, que es
el documento que la decisión modificó. Aquí va la voz literal del revisor y nada más.
