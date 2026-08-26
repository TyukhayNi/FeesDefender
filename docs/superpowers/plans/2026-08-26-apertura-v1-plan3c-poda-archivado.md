---
tipo: plan
objeto: "Apertura V1 — Plan 3C: la poda y el archivado, y las cuatro destrucciones que el write-set no enumeró"
estado_remediacion: pendiente
creado: 2026-08-26
---

# Apertura V1 — Plan 3C: la poda y el archivado (rev. 1)

> ## ⛔ ESTADO: rev. 1 `REQUIERE-REVISION`. NO se construye con este diseño.
>
> **R20 (diseño) devolvió `REQUIERE-REVISION`: 13 hallazgos, 13 confirmados, 0 refutados, 3
> críticos.** Adjudicación en el **§5**; acta en
> `docs/superpowers/specs/2026-08-26-apertura-v1-plan3c-r20-adversarial-review.md`.
>
> **Las tres mediciones del §1 sobreviven y el revisor las reprodujo con hashes.** El censo del
> §1.1 **no**: omitía un `unlink` vivo dentro de `00_Input` que estaba en mi propia salida de
> `grep`, y su total («cuatro») no cuadra con su propia tabla (tres filas «NINGUNA»).
>
> **Pendiente: rev. 2**, con el censo hecho por AST y las piezas I/K/L/M rehechas.

> **Predecesores.** [Plan 3A](2026-08-26-apertura-v1-plan3-write-set.md) (PR #251, `6bd78ad`),
> [3A-bis](2026-08-26-apertura-v1-plan3a-bis-fila5.md) y
> [3B](2026-08-26-apertura-v1-plan3b-derivados.md). Spec canónica:
> [§25](../specs/2026-08-15-orquestador-apertura-expediente-design.md); decisión **D4** del §24
> («la poda archiva en vez de borrar»).
>
> **Filas de esta tanda** (§1.2 de 3A): **#18, #20, #25** — 3 de clase derivado.
>
> **Rondas: 2.** Diseño (**R20**) y diff (**R21**). La pieza **destruye datos** por definición:
> es la categoría de radio de daño máximo del cuadro de `CLAUDE.md`, y no admite atajo.
>
> **Aviso de vocabulario, que no es pedantería.** «Poda» nombra **dos cosas distintas** en este
> repo: la de `MEJORAS #123-bis` es la de **ramas de git**, y no tiene nada que ver con ésta. Esta
> tanda es la retirada de **artefactos derivados dentro del expediente**. Un lector que cruce las
> dos entradas de backlog concluiría que 3C ya está diagnosticada, y no lo está.

---

## 1. Lo que se midió antes de diseñar

3A describió 3C como «la poda y el archivado: tres filas». Al barrer el código, **el censo de
operaciones destructivas sobre un expediente es mayor que sus tres filas**, y una de las que
faltan es la peor de todas.

### 1.1. El censo real de destrucciones en producción

Barrido de `unlink` / `rmtree` sobre `core/` y `scripts/`, descartando temporales, staging y
`.partial`:

| Sitio | Qué borra | ¿Fila del §25? |
|---|---|---|
| `core/email_atomize/pipeline.py:220` | `mensajes/*.md` huérfanos | **#18** |
| `core/email_atomize/pipeline.py:267` | `vistas/*.md` huérfanas | **#18** |
| `core/adjuntos_contenido/pipeline.py:109` | `*.contenido.md` huérfanos | **#20** |
| `core/sala_maquina.py:568` | `carpeta_bundle` entera, tras archivar | **#25** (destino) |
| `core/sala_maquina.py:535`, `:891` | staging | no — y correcto: es staging |
| **`core/local_organizer.py:1027`** | **`_organizado/` entero, con `rmtree`** | **NINGUNA** |
| **`core/local_organizer.py:845`** | el fichero previo al renombrar (`MOVED`) | **NINGUNA** |
| **`core/sala_lectura.py:646`** | ídem, en el módulo deprecado | **NINGUNA** |
| `core/anon/separar.py:596` | residuos del split | no — `core/anon/` no se toca (regla del repo) |

**Cuatro destrucciones vivas que las 27 clases del §25 no enumeran.** Es exactamente lo que R5
anticipó al detener el bucle de revisión del diseño: *«el write-set es un barrido de código»*, no
una lista que se pueda cerrar en prosa. Se cerró la lista y el barrido no se volvió a hacer.

### 1.2. La peor está dentro de `00_Input`

```python
def _drive_ev_dir(case_id): return caso_path(case_id) / "00_Input" / DRIVE_EV_SUBDIR
def _organizado_dir(case_id): return _drive_ev_dir(case_id) / ORGANIZADO_SUBDIR   # "_organizado"

def reconstruir(case_id) -> dict:
    """``--rebuild``: borra ``_organizado/`` y rehace plan + execute desde cero."""
    org = _organizado_dir(case_id)
    if org.exists():
        shutil.rmtree(org)
```

`shutil.rmtree` sobre `caso_path(case_id)/00_Input/01_Drive EV/_organizado`. Es decir: **un
`rmtree` recursivo dentro de `00_Input`**, la zona que el repo declara intocable en tres sitios a
la vez:

- `CLAUDE.md`: *«Pipeline idempotente: re-ejecutar nunca toca `00_Input/` ni
  `90_NOTAS_PERSONALES/`»*.
- `core/sala_maquina.destino_seguro`: *«Invariante del proyecto (M5): jamás escribir en `00_Input/`
  ni en `90_Notas personales/`»*, con `_ZONAS_VETADAS` comprobado por componentes de ruta.
- El §25 del diseño de apertura, que no le da fila porque no sabe que existe.

Y es **alcanzable**: `scripts/organizar_local.py` y `streamlit_app.py` importan
`core.local_organizer`.

**Lo que sí hay que decir en su defensa, para no inflar el hallazgo:** `_organizado/` es un espejo
**derivado** que el propio organizador construye, así que borrarlo no borra originales de cliente
*hoy*. El defecto no es que hoy destruya el original: es que **la única cosa que lo separa del
original es una constante**, no una comprobación. `destino_seguro` existe precisamente para eso y
este camino no la usa.

### 1.3. El archivado —lo que 3C promete que nunca pierde— puede perder

`archivar_bundle_entero` (`core/sala_maquina.py:538-569`) es el destino de la fila #25 y la
garantía de D4. Aplana:

```python
a_archivar = [p for s in slugs for p in _rutas_de(sm_dir, carpeta_bundle, s) if p.exists()]
a_archivar += [p for p in sorted(carpeta_bundle.rglob("*")) if p.is_file()]
...
for p in dict.fromkeys(a_archivar):
    p.replace(archivo / p.name)          # ← por NOMBRE, y `replace` sobrescribe
```

`a_archivar` se compone de **tres bases distintas** (`carpeta_bundle`, `sm_dir/03_MD`,
`sm_dir/raw_text`) más un `rglob` que baja por subdirectorios, y todo aterriza en **un** directorio
por `p.name`. `dict.fromkeys` deduplica por `Path`, no por nombre. Así que dos ficheros con el
mismo *basename* en bases distintas van al mismo destino y **el segundo sobrescribe al primero**,
en silencio, dentro de la operación cuyo contrato es *«nunca se borra de aquí»*.

Los tres `_rutas_de` tienen extensiones distintas (`.pdf`, `.md`, `.txt`), así que la colisión no
sale de ahí. Sale del `rglob`: un `indice.json` en la raíz del bundle y otro en un subdirectorio, o
un `.pdf` de segmento con el mismo nombre en dos niveles.

**Medido el 2026-08-26, y sale peor de lo que este párrafo afirmaba antes de la sonda.** Con un
`indice.json` en la raíz del bundle («RAIZ DEL BUNDLE») y otro en `sub/` («SUBDIRECTORIO»):

```
devuelto archivados = ['seg1.pdf', 'seg1.md', 'indice.json', 'indice.json']
EN EL ARCHIVO:        ['indice.json', 'seg1.md', 'seg1.pdf']
contenido de indice.json en el archivo: 'SUBDIRECTORIO'
carpeta_bundle sigue existiendo? False
```

La función **no solo pierde el fichero: lo declara archivado.** Devuelve **cuatro** nombres, en el
archivo hay **tres**, «RAIZ DEL BUNDLE» no existe en ninguna parte, y la carpeta de origen se
retiró. Y el nombre repetido dentro de la propia lista de retorno **era la prueba de la colisión,
en la mano del llamador**, sin que nadie la mire.

Dos consecuencias para el diseño, y las dos cambian una pieza:

1. La frontera **P2 se comprueba por CONTENIDO, no por conteo.** Un test que contara ficheros
   habría visto 4 → 3 y podido leerse como deduplicación legítima; lo que prueba la pérdida es que
   «RAIZ DEL BUNDLE» no está.
2. Hay un **detector gratis**: `len(set(nombres)) != len(nombres)` en el retorno. La pieza I lo
   incorpora como aserto además de preservar la ruta relativa — el segundo cierra la causa, el
   primero cierra la clase «el archivo afirma más de lo que contiene» aunque aparezca otra causa.

**Y el `rmtree` con `ignore_errors=True`** de la línea siguiente puede no borrar nada (una sharing
violation del cliente de Drive en Windows es el caso citado por el comentario de la función
hermana, doce líneas más arriba) y la función **devuelve la lista de archivados igual**, así que el
llamador cree que la carpeta se retiró. La función hermana filtra por ese riesgo; ésta no.

### 1.4. La poda de #18 y #20 borra sin archivar, y una de las dos ya tiene compuerta

- **#18** (`email_atomize`) tiene ya un **gate**: si la corrida acumuló errores,
  `report.poda_omitida = True` y no se poda (`pipeline.py:205-210`), con foto parcial declarada.
  Existe la noción de «hoy no podo». Lo que no existe es «podo archivando».
- **#20** (`adjuntos_contenido`) **no tiene gate**: poda huérfanos incondicionalmente
  (`pipeline.py:107-111`), en un bucle sin contención, y cuenta `report.podados`.

Que #18 tenga compuerta y #20 no es el desnivel a cerrar, y explica por qué D4 no se puede aplicar
igual a las dos.

---

## 2. Las clases

> **C9 — Un artefacto derivado no se borra: se retira a un archivo del que se puede volver.** Es
> D4, y aquí se convierte de decisión en propiedad comprobable.

> **C10 — Un archivo que aplana por nombre no es un archivo.** El destino del archivado tiene que
> preservar la distinción que su origen tenía; si dos orígenes distintos caen en el mismo nombre,
> el archivado destruye lo que dice conservar.

> **C11 — Una retirada solo se declara hecha si se verificó que se hizo.** `ignore_errors=True` en
> el paso final de una operación que devuelve «archivados: N» es afirmar un resultado que no se
> comprobó.

> **C12 — La zona vetada se comprueba en el camino, no se evita por convención.** Hay un
> `destino_seguro` en este repo; un camino que escribe o borra dentro del expediente y no lo
> atraviesa está protegido por que nadie se equivoque de constante.

C10 y C11 son, otra vez, *el nombre de una cosa no es la cosa*: el **nombre** del fichero por el
**fichero**, y la **llamada** a `rmtree` por la **retirada** efectuada. Quinta y sexta aparición de
la misma familia en esta serie de planes, y las dos en la pieza que existe para no perder nada.

---

## 3. Las piezas

### Pieza I — el archivo, con un solo constructor y sin aplanar (C10)

Un único sitio que componga la ruta de archivo, y que **preserve la ruta relativa de origen** en
vez del basename:

```
99_Versiones anteriores/reproceso_<sello>/<ruta relativa al caso>
```

Con eso, `03_MD/x.md` y `02_Documentos/slug/x.md` dejan de colisionar porque dejan de compartir
destino. Y si dos orígenes **sí** produjeran el mismo destino —no debería ocurrir, pero la
propiedad no puede depender de eso—, la operación **rompe** en vez de sobrescribir: `os.link` /
`p.replace` sobre un destino existente es un error, no un caso a absorber.

**Y el aserto del retorno, que es la otra mitad.** La sonda del §1.3 midió que el nombre repetido
aparecía **en la lista devuelta** sin que nadie lo mirara: `len(set(nombres)) != len(nombres)` es un
detector gratis de «el archivo afirma más de lo que contiene». Se pone, aunque la ruta relativa ya
cierre la causa conocida — porque cierra la **clase**, y la clase sobrevive a que aparezca otra
causa. Es literalmente la lección que 3A pagó cuatro veces: remediar la propiedad, no el ejemplo.

**El sello ya existe** (`_sello_reproceso()`); no se inventa un esquema nuevo.

### Pieza J — la retirada se verifica (C11)

`archivar_bundle_entero` deja de terminar en `rmtree(..., ignore_errors=True)` y devuelve **lo que
pasó**, no lo que intentó:

- si tras mover todo quedan ficheros en la carpeta, **no** se llama a `rmtree`: se devuelve el
  residuo y el llamador decide;
- si el `rmtree` falla, se dice; el residuo se lista.

La firma pasa de `list[str]` a un resultado con `archivados` y `residuo`. Cambiar la firma es el
punto: hoy no hay sitio donde quepa la verdad.

### Pieza K — #18 y #20 archivan en vez de borrar (C9)

Las dos podas pasan por la pieza I. Y el **gate** de #18 se generaliza: la compuerta «si la corrida
tuvo errores, hoy no se retira nada» se aplica también a #20, que hoy no la tiene.

**Y las dos pasan por la costura de 3A** con `clase="derivado"`, lo que significa que sobre un caso
prestado la retirada **no ocurre**: retirar es una escritura destructiva y desviarla a la bandeja
no tiene sentido —lo que se retiraría sigue en el árbol vivo—. Es la categoría **A** de 3B por otra
razón: no porque lea su versión anterior, sino porque su efecto es sobre el árbol vivo y la bandeja
no puede representarlo.

> **Esto es una decisión y va escrita: la retirada no se desvía, se rechaza.** Un `unlink`
> «desviado» es un `unlink` que no ocurre pero cuyo llamador cree que ocurrió, y eso deja el
> registro afirmando una poda que el árbol desmiente.

### Pieza L — `_organizado/` sale de `00_Input`, o su borrado pasa por la puerta (C12)

Dos salidas, y la elección es de arquitectura, así que la tomo y la justifico:

1. **Mover `_organizado/` fuera de `00_Input`** a `01_Procesado/`, que es donde vive todo lo
   derivado. Es lo correcto de fondo: un espejo derivado no tiene por qué vivir en la zona de los
   originales. Pero es una **migración de datos** en expedientes reales, y la migración de layout
   es un ejercicio con su propio historial en este repo.
2. **Dejarlo donde está y hacer que su retirada atraviese `destino_seguro`** con una excepción
   nominal y explícita para `_organizado`, más la costura de 3A.

**Elijo (2) para 3C y anoto (1) como backlog con disparador.** Motivo: 3C es una tanda sobre la
retirada, y (1) es una migración de layout que arrastra expedientes de cliente vivos; mezclarlas
pone el riesgo de una migración dentro de la pieza que existe para no perder datos. La excepción
nominal es fea a propósito: se **ve** en el código y en el guard, y eso es lo que hace que (1) se
acabe haciendo, mientras que una convención tácita no se ve.

### Pieza M — el guard del censo (C12)

Guard AST, sin números de línea y con prueba de mutación propia:

> **Ningún `unlink`, `rmtree` o `replace` de producción sobre una ruta bajo un expediente puede
> estar fuera de la pieza I o de un `destino_seguro`.**

Con lista de exenciones **por nombre** y que **solo puede encoger** — la polaridad que el contrato
de gobernanza ya impone a sus propias listas, y por la misma razón: definir el corpus por
inclusión deja escapar todo fichero nuevo.

Exenciones al abrir: staging de `sala_maquina` (`:535`, `:891`), `core/anon/separar.py:596`
(`core/anon/` no se toca por regla del repo), y el módulo deprecado `core/sala_lectura.py` **si y
solo si** se comprueba que su CLI ya no es vía viva; si lo es, entra.

---

## 4. Las fronteras — una por mutante

| # | Frontera | El mutante |
|---|---|---|
| **P1** | el archivo preserva la ruta relativa de origen | volver a `archivo / p.name` |
| **P2** | dos orígenes con el mismo basename no colisionan — comprobado por **CONTENIDO**, nunca por conteo (§1.3) | ídem, comprobando que los dos contenidos siguen ahí |
| **P2-bis** | el retorno no puede listar un nombre dos veces: si lo hace, rompe | degradar el aserto del retorno a aviso |
| **P3** | un destino de archivo ya existente **rompe**, no se sobrescribe | usar `replace` sobre destino existente |
| **P4** | la retirada devuelve residuo cuando la carpeta no queda vacía | volver a `ignore_errors=True` y lista sin residuo |
| **P5** | un `rmtree` fallido no se reporta como retirada hecha | tragarse la excepción |
| **P6** | #18 archiva en vez de borrar | volver a `p.unlink()` |
| **P7** | #20 archiva en vez de borrar | ídem |
| **P8** | #20 tiene el gate de errores que #18 ya tenía | quitar el gate |
| **P9** | el gate de #18 sigue funcionando (no regresión) | invertir su condición |
| **P10** | sobre caso prestado, la retirada **rechaza** y no se desvía | entregar `Deposito` desviado a la poda |
| **P11** | sobre caso prestado, **cero ficheros retirados**, verificado por hash del árbol | comprobar solo el código de salida |
| **P12** | `reconstruir` atraviesa `destino_seguro` | llamar a `rmtree` directamente |
| **P13** | la excepción nominal de `_organizado` **no** abre `00_Input` entera | ampliar la excepción a `00_Input` |
| **P14** | el guard AST muerde un `unlink` nuevo sobre un expediente | añadir uno y comprobar que el guard falla |
| **P15** | la lista de exenciones del guard **solo puede encoger** | añadir una entrada y comprobar que el test lo rechaza |
| **P16** | el sello del archivo es el de la corrida, no uno nuevo por fichero | recalcular el sello dentro del bucle |

Diecisiete fronteras (P2-bis incluida), diecisiete mutantes. Arnés con restauración **binaria** y ancla adaptada al
terminador de línea.

---

## Global Constraints

- **No se toca `case_mutex.py`, `mutex_sesion.py` ni el CP10/CP11 del checkin.**
- **`core/anon/` no se toca** (regla del repo). Su `unlink` queda exento y declarado.
- **No se migra `_organizado/` fuera de `00_Input`** en esta tanda. Backlog con disparador.
- **Ningún test de esta tanda corre sobre `data/CASOS/`.** Todo en `tmp_path`, con `--basetemp`
  corto.
- **Suite con dos semillas** (777 y 31337).

## File Structure

```
core/sala_maquina.py                 pieza I (constructor del archivo) y J (retirada verificada)
core/email_atomize/pipeline.py       #18 archiva; gate conservado (K)
core/adjuntos_contenido/pipeline.py  #20 archiva; gate nuevo (K)
core/local_organizer.py              `reconstruir` por `destino_seguro` (L)
tests/test_archivo_versiones.py      NUEVO — P1-P5, P16
tests/test_poda_archiva.py           NUEVO — P6-P11
tests/test_zona_vetada_retirada.py   NUEVO — P12, P13
tests/test_guard_destrucciones.py    NUEVO — P14, P15
```

## Task 1: el censo, y los tres hechos como tests rojos

- [ ] Censo AST de destrucciones, versionado, con su tope. **El tope solo baja.**
- [ ] Rojo de la colisión de nombres en el archivado (§1.3), con dos ficheros de contenido
      distinto y el mismo basename.
- [ ] Rojo del `rmtree` que falla y se reporta como retirada hecha.
- [ ] Rojo de `reconstruir` borrando dentro de `00_Input`.

## Task 2: Piezas I y J — el archivo y la retirada verificada

- [ ] Constructor único; ruta relativa preservada; destino existente rompe.
- [ ] Firma con `residuo`. P1-P5, P16 con su mutante.

## Task 3: Pieza K — #18 y #20 archivan

- [ ] Las dos por la pieza I y por la costura, con rechazo sobre caso prestado.
- [ ] El gate de errores en las dos. P6-P11 con su mutante.

## Task 4: Pieza L — la zona vetada

- [ ] `reconstruir` por `destino_seguro` con la excepción nominal. P12, P13 con su mutante.

## Task 5: Pieza M — el guard del censo

- [ ] Guard AST + prueba de mutación + lista de exenciones que solo encoge. P14, P15.

## Task 6: E2E de la retirada

- [ ] Sobre un caso prestado: **cero ficheros retirados**, verificado por hash del árbol antes y
      después, y código de salida correcto. Las dos cosas: R8 midió que comprobar solo el código
      dejaba pasar un entrypoint que se tragaba el fallo.
- [ ] Sobre un caso disponible: lo retirado está **completo** en el archivo, verificado por hash
      fichero a fichero, no por conteo.

## Criterio de salida

1. Nada que la poda retire desaparece: todo está en el archivo, verificado por hash.
2. El archivado no aplana: dos orígenes con el mismo nombre conviven.
3. Una retirada que no se pudo completar **no** se reporta como completada.
4. Sobre un caso prestado no se retira nada, y se dice.
5. Ninguna destrucción de producción sobre un expediente queda fuera del guard, salvo las
   exenciones declaradas por nombre.
6. Diecisiete fronteras, diecisiete mutantes, cada uno muerto por la suya.
7. Suite verde con dos semillas, con la variación del conteo explicada.

## Lo que este plan deliberadamente NO hace

- **No mueve `_organizado/` fuera de `00_Input`.** §3-L, con su razón. Va a
  `docs/MEJORAS_FUTURAS.md` con disparador: la próxima migración de layout de intake.
- **No construye la restauración desde el archivo.** El archivo garantiza que el dato está; volver
  a ponerlo en su sitio es un comando que hoy no existe y que nadie ha pedido. Se declara, no se
  finge.
- **No unifica el archivado con `_snapshot/`** (el backup del checkout). Son dos mecanismos con dos
  dueños y unificarlos toca el protocolo.
- **No arregla el módulo deprecado `core/sala_lectura.py`**, más allá de decidir si su CLI sigue
  siendo vía viva y, si lo es, meterlo en el guard.
- **No toca las seis filas de protocolo** que el Task 6 de 3A dejó fuera.

## Lo que sigue SIN VERIFICAR, y se declara

- **Si el censo de destrucciones está completo.** Salió de un barrido de `unlink`/`rmtree`/`replace`
  por texto. `os.remove`, `Path.rmdir`, `shutil.move` sobre un destino existente y cualquier
  destrucción vía subproceso (`rclone delete`, por ejemplo) **no** están en ese barrido. El guard
  del Task 5 cubre las formas que enumera, y las que no enumera siguen abiertas.
- **Si `core/sala_lectura.py` es vía viva.** `scripts/sala_lectura.py` lo importa y lo llama, así
  que *parece* viva; que alguien la use es otra pregunta y no la he medido.
- **El tamaño del archivo en expedientes reales.** Preservar la ruta relativa en vez del basename
  no cambia el volumen, pero archivar en vez de borrar sí: `99_Versiones anteriores/` crecerá y
  nadie lo vacía. No hay política de retención y este plan no la inventa.
- **La interacción del archivado con el merge de tres vías del checkin.**
  `99_Versiones anteriores/**` no está en `MERGE_EXCLUSIONS`, así que crece por los dos lados
  durante un préstamo. No medido.
- **La reacción del mutex a un salto real de NTP**, heredada.
- **Las seis remediaciones de R13 no tienen ronda propia** y esta tanda las usa por transitividad.

---

## 5. Adjudicación de la revisión adversarial R20 (Codex, 2026-08-26) — REQUIERE-REVISION, pendiente

- **Objeto revisado:** este documento, **rev. 1**, en el commit `d1b09e2`.
- **Ronda:** R20, la ronda de **DISEÑO** de 3C. R15 cubrió 3A y solo 3A.
- **Revisor:** Codex por CLI sobre un `git archive` sin `.git`, solo lectura por construcción.
- **Informe recibido:** `docs/superpowers/specs/2026-08-26-apertura-v1-plan3c-r20-adversarial-review.md`, `sha256` `77ac21c54ede785c…`, recomputado al archivarlo y **coincide**.
- **Hallazgos:** 13 — 3 CRÍTICOS, 6 ALTOS, 3 MEDIOS, 1 BAJO. **13 confirmados, 0 refutados.**
- **Remediado en:** nada. **No se escribe código con este diseño.**

**Qué ejecutó el revisor:** censo destructivo por AST además del textual, seis sondas propias
(colisión de nombres, retirada no comprobada, ruta de `_organizado/`, gate de vistas,
`Path.replace`, longitud de ruta) y la verja existente (241 pasados, 3 omitidos).

### 5.1. Un aviso de método antes de los hallazgos: casi archivé un informe a medias

Al calcular el `sha256` del informe de esta ronda obtuve `2ac43cdb…`; dos minutos después, al
archivarlo, `77ac21c5…`. **El revisor seguía escribiendo.** La presencia de `INFORME.md` **no** es
la señal de que la ronda terminó; lo es la salida del proceso (aquí, `_ultimo_mensaje.txt`).

Sin esa comprobación habría archivado un informe truncado **como la voz literal del revisor**, con
un digest internamente coherente y falso — es decir, habría destruido exactamente la garantía que el
acta existe para dar: que se pueda contrastar *qué dijo el revisor* con *qué decidí yo que dijo*.
Queda como regla: **el digest solo significa algo sobre un fichero terminado.**

### 5.2. Los tres críticos, y el que más me señala

**H20-01: el censo omite un `unlink` vivo dentro de `00_Input`, y mi aritmética tampoco cuadra.**

`scripts/migrar_layout_intake.py:124` hace `hijo.unlink()` sobre duplicados bajo
`caso_path(case_id) / "00_Input"`, por una vía viva (su propio comando Typer). **Estaba en mi
propia salida de `grep`** y lo dejé fuera de la tabla: el barrido decía descartar «temporales,
staging y `.partial`», y esto no es ninguna de las tres.

Y la cuenta: escribí *«Cuatro destrucciones vivas que las 27 clases del §25 no enumeran»* y mi tabla
rotula **tres** filas como NINGUNA. Con la que me faltaba serían cuatro, pero **no son las cuatro
que dije**.

**Es la lección del 71º cierre cometida en el párrafo que la cita.** «Un número agregado esconde su
propia composición: mirar el DESGLOSE, no el total.» Escribí un total sin contar mi propia tabla, en
una sección cuyo argumento entero es que el write-set se cerró sin volver a barrer. **Hice con mi
censo lo que denunciaba del §25.**

El revisor añade además las formas que mi barrido declaraba abiertas y no miró: `Path.rmdir` en
lotes y bajo `00_Input/05_CRM`, `shutil.move` del expediente completo (llamado desde Streamlit), y
destrucción remota por `rclone moveto`/`rmdirs`.

**H20-02: el plan no remedia dos destrucciones que sí censó, así que su propio guard no puede quedar
verde.** `local_organizer.py:845` (`old.unlink()` en `ejecutar_plan`) y `core/sala_lectura.py:646`
no tienen tarea asignada. Y mi exención condicional para `sala_lectura` —«si y solo si su CLI ya no
es vía viva»— **es falsa en este árbol**: `scripts/sala_lectura.py:64` llama a `poblar_sala_lectura`,
que borra. O el guard falla y no hay tarea que lo lleve a verde, o no falla y no prueba nada.

**H20-03: la costura heredada no puede expresar la retirada no desviable que la pieza K da por
diseñada.** `clase="derivado"` **no** produce rechazo: produce desvío. No existe operación de
retirada en la costura de 3A. Escribí «las dos pasan por la costura con `clase="derivado"`» y la
consecuencia de eso es desviar, que es justo lo que la misma pieza declara que no debe pasar. **Es
el mismo error que H18-02 en el otro plan: enuncié una condición sin comprobar que fuera
alcanzable.** Tercera guarda inerte del día.

### 5.3. El hallazgo que contradice mi propia sonda, en el mismo documento

**H20-04: la pieza I conserva la primitiva de sobrescritura que dice eliminar.** Escribí que
*«`p.replace` sobre un destino existente es un error, no un caso a absorber»*. **`Path.replace`
sobrescribe.** El revisor lo midió, y no hacía falta: **mi propia sonda del §1.3 lo había
demostrado nueve párrafos antes** — «SUBDIRECTORIO» pisó a «RAIZ DEL BUNDLE» exactamente por un
`p.replace`.

Tenía la refutación de mi premisa impresa en mi propio documento y escribí la premisa igual. No es
falta de datos: es no releer lo que acabo de medir cuando redacto el remedio.

### 5.4. Los trece, uno por uno

| # | Sev. | Veredicto | Qué se hace |
|---|---|---|---|
| **H20-01** censo incompleto y aritmética falsa | CRÍTICO | **CONFIRMADO** (verificado: `migrar_layout_intake.py:124`, y mi tabla rotula 3 «NINGUNA») | **Rev. 2**: el censo se hace por **AST**, con las formas enumeradas y su tope, y el total se cuenta de la tabla |
| **H20-02** dos destrucciones censadas sin remedio; la exención de `sala_lectura` es falsa | CRÍTICO | **CONFIRMADO** | **Rev. 2**: o entran en las piezas, o la exención se justifica por otra razón que no sea «no es vía viva» |
| **H20-03** la costura no expresa la retirada no desviable | CRÍTICO | **CONFIRMADO** | **Rev. 2**: hace falta una operación de retirada, y ligarla a `clase="derivado"` la desvía |
| **H20-04** `Path.replace` sí sobrescribe | ALTO | **CONFIRMADO** (por mi propia sonda del §1.3, antes que por la suya) | **Rev. 2**: la pieza I necesita comprobación explícita de existencia, no confiar en la primitiva |
| **H20-05** I/J no definen el fallo a mitad de lote ni la reentrada con el mismo sello | ALTO | **CONFIRMADO** | **Rev. 2**: es la mitad del contrato de una operación que mueve N ficheros |
| **H20-06** el §1.4 atribuye a #18 un gate que no gobierna la poda de vistas | ALTO | **CONFIRMADO** | **Rev. 2**: el gate cubre `mensajes/`, no `vistas/`; mi §1.4 los trataba como uno |
| **H20-07** L no aplica D4 a `_organizado/` y su excepción amplía una puerta general | ALTO | **CONFIRMADO** | **Rev. 2**: la excepción nominal abría más de lo que decía, y `_organizado/` se borra sin archivar, contra D4 |
| **H20-08** J cambia el tipo sin diseñar qué hace el llamador con el residuo | ALTO | **CONFIRMADO** | **Rev. 2**: cambiar la firma sin decidir la conducta es mover el problema |
| **H20-09** «rechazar la retirada» puede ocurrir tras publicar una corrida parcial | ALTO | **CONFIRMADO** | **Rev. 2**: el rechazo llega tarde en el orden real de `sala_maquina` |
| **H20-10** la ruta propuesta añade 52 caracteres sin presupuesto ni frontera | MEDIO | **CONFIRMADO** | **Rev. 2**: MAX_PATH es un riesgo real en este repo, con historial propio |
| **H20-11** M no puede inferir estáticamente «ruta bajo un expediente» | MEDIO | **CONFIRMADO** | **Rev. 2**: si el guard no puede distinguirlo, es decorativo. Hay que redefinir qué observa |
| **H20-12** las dieciséis fronteras no son dieciséis mutantes y omiten propiedades | MEDIO | **CONFIRMADO** | **Rev. 2** |
| **H20-13** D4 parafraseada más estrecha que la fuente | BAJO | **CONFIRMADO** | Se cita D4 literal en la rev. 2 |

### 5.5. Qué sobrevive de la rev. 1

**Las tres mediciones del §1 sobreviven, y el revisor las reprodujo por su cuenta con hashes:** la
colisión de nombres del archivado es real, la retirada ficticia por `ignore_errors=True` es real, y
el `rmtree` dentro de `00_Input` es real y alcanzable.

**Lo que no sobrevive es, otra vez, el remedio.** Y el patrón de los tres planes de hoy es el mismo:
**el diagnóstico medido aguanta; las piezas que prometen cerrarlo, no.** Las tres rondas
encontraron, entre otras cosas, **tres condiciones que no pueden ser verdad nunca** —
`es_copia_prestada` (H16-01), `agregado=True` sobre protocolo (H18-02) y `clase="derivado"` como
rechazo (H20-03)—. Tres guardas inertes escritas el mismo día por la misma mano.

**La regla operativa que sale de aquí, y que no estaba en `CLAUDE.md`:** al enunciar una condición
de guarda, **comprobar que puede ser falsa** antes de construir sobre ella. Es una sonda de tres
líneas y hoy habría ahorrado tres críticos.
