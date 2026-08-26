---
tipo: plan
objeto: "Apertura V1 — Plan 3B: los once derivados del write-set, y las tres puertas laterales que llegan a ellos"
estado_remediacion: pendiente
creado: 2026-08-26
---

# Apertura V1 — Plan 3B: los derivados, y las tres puertas laterales que llegan a ellos (rev. 1)

> ## ⛔ ESTADO: rev. 1 `NO-EJECUTABLE`. NO se construye con este diseño.
>
> **R18 (diseño) devolvió `NO-EJECUTABLE`: 15 hallazgos, 15 confirmados, 0 refutados, 4 críticos.**
> Adjudicación en el **§6**; acta en
> `docs/superpowers/specs/2026-08-26-apertura-v1-plan3b-r18-adversarial-review.md`.
>
> **El diagnóstico del §1 sobrevive** —el revisor reprodujo las tres puertas y el rechazo de
> `sala_maquina`—. **Las cuatro piezas no**: H18-01 hace que E y F sean **incompatibles entre sí**,
> porque `deposito(ref, …)` no puede transportar `CaseWorkspace.working_root`.
>
> **Pendiente: rev. 2**, que es rediseñar la interfaz por la que un motor recibe permiso de
> escritura, no una tanda de ediciones.

> **Predecesores.** [Plan 3A](2026-08-26-apertura-v1-plan3-write-set.md) (PR #251, `6bd78ad`) —
> la costura, el mutex de sesión y las dos puertas cableadas— y
> [Plan 3A-bis](2026-08-26-apertura-v1-plan3a-bis-fila5.md), que toma la decisión de la fila #5.
> Spec canónica: [§25](../specs/2026-08-15-orquestador-apertura-expediente-design.md).
>
> **Filas de esta tanda** (§1.2 de 3A): **#14, #15, #16, #17, #19, #21, #22, #23, #24, #26, #27**
> — 7 de clase derivado y 4 de protocolo.
>
> **Rondas: 2.** Ronda de diseño sobre este documento (**R18**) y ronda sobre el diff (**R19**).
> La pieza decide quién puede escribir sobre qué copia. **R15 cubrió 3A y solo 3A**: no se
> reutiliza.

---

## 1. Lo que se midió antes de diseñar, y que cambia la forma de la tanda

3A describió 3B como «migrar once filas a la costura». Al medir, **eso no es lo que hace falta**,
y hacerlo tal cual introduciría defectos que hoy no existen.

### 1.1. Las once filas están detrás de una puerta que ya rechaza — y hay tres puertas más que no

Los motores de 3B **no resuelven el caso**: reciben un `Path` ya resuelto y componen desde él.

| Motor | Firma | Compone desde |
|---|---|---|
| `email_atomize.atomize_dir` | `(fuentes, out, *, case_dir=None)` | `out` y `case_dir` |
| `adjuntos_contenido.procesar_dir` | `(adjuntos_dir, *, forzar)` | `adjuntos_dir` |
| `sala_maquina` (motor) | recibe `case_dir` | `sm._sala_maquina_dir(case_dir)` |
| `split_documental` | recibe el directorio del bundle | ese directorio |

Quien resuelve es el entrypoint. Y `scripts/sala_maquina.py` **ya rechaza**: desde el Task 9 de la
Fase 1 dual, sus tres subcomandos abortan con **código 2 y cero bytes** sobre un caso que otra
máquina tiene prestado, y desde el Task 5 de 3A adquiere el mutex. Las filas #21-#24, #26 y #27
llegan **solo** por ahí.

**Pero las filas #14-#17 y #19 tienen tres puertas más, y ninguna de las tres resuelve workspace,
toma mutex ni consulta el guard:**

| Puerta | Llega a | Resuelve el caso con |
|---|---|---|
| `scripts/atomize_emails.py` (`--ref`) | #14, #15, #16, #17 | `emails_out_dir(case_id)` → `caso_path` |
| `core/adjuntos_contenido/__main__.py` | #19 | `emails_out_dir(case_id)` → `caso_path` |
| `adjuntos_contenido.resumen.aplicar_resumenes(case_id, …)` | #19 | `emails_out_dir(case_id)` → `caso_path` |

`caso_path` compone la ruta **canónica**. Las tres escriben en el árbol vivo del canon de un caso
que otra máquina puede tener prestado, sin preguntar a nadie.

**Medido el 2026-08-26**, con el caso en `estado_repositorio: prestado` por otra máquina:

```
via GUARD  (dir_intake):     _pendiente_checkin/email/01_Procesado/Emails
via PUERTA (emails_out_dir):                        01_Procesado/Emails
>>> coinciden? False

>>> procesar_caso escribio en: 01_Procesado/Emails/adjuntos/_contenido_estado.json
>>> ese sitio esta en la bandeja? False
```

El guard, preguntado por esa misma ruta relativa, responde **bandeja**. La puerta resuelve al
**árbol vivo**, y `procesar_caso` escribió ahí de verdad: no es una ruta que se compone y no se usa.
La diferencia entre las dos líneas es exactamente el hueco de esta tanda.

> **Ésta es la tanda, y no la migración.** 3B no es principalmente mover once escrituras a la
> costura: es **cerrar tres puertas que llegan a cinco de ellas**. La migración de las escrituras
> es lo que hace la clausura *exigible* en vez de una promesa repetida en cada puerta —que es
> exactamente el argumento con el que 3A justificó la costura, aplicado un nivel más abajo.

### 1.2. Desviar un agregado que se calcula desde su versión anterior lo rompe

Cinco de las once filas son **read-modify-write**: leen su propia versión anterior y escriben el
resultado.

| Fila | Artefacto | Quién lee la versión anterior |
|---|---|---|
| #17 | `_registro.json` | `reg.save()` sobre el registro cargado |
| #19 | `_contenido_estado.json` | `cargar_estado(adjuntos_dir)` (caché por `sha256`) |
| #21 | `_sala_maquina_state.json` | `_estado_previo`, `_intentos_previos`, `_cache_hashes` |
| #23 | `_cobertura.json` | `_cobertura_previa(case_dir)` |
| #23 | `_cobertura.md` | se re-renderiza entera desde `_cobertura.json` |

El guard desvía **la escritura** y no la lectura. Con el destino en la bandeja y la fuente en el
árbol vivo, cada corrida:

1. lee la versión del árbol vivo, que **nunca avanza**;
2. le suma su propio delta;
3. escribe en la bandeja, **reemplazando** lo que la corrida anterior dejó ahí.

Dos corridas durante el mismo préstamo y la primera desaparece.

**No es hipotético: es el defecto de la fila #23, ya medido en este repo.** El docstring de
`_cobertura_previa` (`scripts/sala_maquina.py:150-156`) lo dice con su cifra:

> *«con `[]`, la fusión de una corrida incremental reducía el registro al delta y
> `_escribir_cobertura_md` borraba el resto del `_cobertura.md` (169 filas → 2 en W-02XOR7, medido
> el 2026-07-30)»*

Lo que se arregló entonces fue **una** vía de que la lectura devolviera vacío (el fichero ausente).
El desvío es **otra** vía al mismo resultado, y no está cerrada. Mismo defecto, distinto camino
—la forma que R14 y R15 castigaron cuatro veces en 3A.

### 1.3. La bandeja también parte la población de entrada de un agregado

La fila #16 (`corpus.jsonl`, `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md`) **no** es
read-modify-write: es función pura de los mensajes que el motor encuentra. Pero su entrada es
`00_Input`, y un intake desviado deja parte de los `.eml` en `_pendiente_checkin/`.

Entonces el agregado se calcula sobre una población **partida** y sale **completo de aspecto y
parcial de hecho**: un `CORREOS_LECTURA.md` que no dice «faltan 12 correos», dice que hay los que
hay. La nota del §25 para esta fila ya lo pedía —*«agregados coherentes con el árbol completo, no
con el conjunto reducido»*— y no había diseño que lo cumpliera.

Es una clase distinta de la del §1.2 y **no** se arregla igual: aquí el problema es la *entrada*,
no el destino.

### 1.4. Un append-only desviado no lo concatena nadie

Las filas #22 (`_tiempos.jsonl`) y #27 (eventos) son append-only y el §25 las declara exentas de
desvío. Si alguna vez se desviara, el CP10 del checkin **no las concatena**: mueve cada fichero
de la bandeja a su ruta, y **si colisiona lo renombra a `_reingesta_*` sin sobrescribir**
(`scripts/repository_cli.py:951-956`). Un log append-only que existe en los dos lados no se une:
se **bifurca**, y nada lo vuelve a unir.

Y por la otra vía —escribir el árbol vivo aprovechando la exención— `_tiempos.jsonl` **no está en
`MERGE_EXCLUSIONS`** (`core/config.py:391-399`), así que la copia prestada también lo trae y el
merge de tres vías se encuentra el mismo fichero crecido por los dos lados.

**Exposición real, sin inflarla:** hoy no ocurre, porque `_tiempos.jsonl` solo lo escribe
`scripts/sala_maquina.py` y esa puerta rechaza. **Se vuelve alcanzable en el momento en que 3B
enrute la fila #22 por la costura**, porque la costura desvía. Es un defecto que la migración
naïve *crearía*, no uno que arreglaría.

---

## 2. Las clases, contestadas como clases

> **C5 — Un artefacto que se calcula a partir de su propia versión anterior no admite desvío.**
> Desviar solo la escritura deja la lectura en el árbol vivo y convierte cada corrida en un
> reemplazo desde una foto que nunca avanza. La respuesta correcta al préstamo es **rechazar**.

> **C6 — Un agregado sobre una población que la bandeja puede partir tiene que declarar su
> población.** Si no puede enumerar lo que dejó fuera, no puede publicarse como agregado.

> **C7 — Un artefacto append-only no admite dos hogares.** O se escribe en uno solo, o el checkin
> lo **concatena**; renombrar por colisión bifurca el log y nadie lo vuelve a unir.

> **C8 — La puerta no es la población.** Cerrar una puerta no cierra las que llegan al mismo
> sitio. La propiedad se cierra **en la escritura**, y las puertas solo dejan de ser un problema
> cuando la escritura exige lo que la puerta debía haber preguntado.

C8 es la generalización de las tres apariciones que 3A pagó: *el nombre de una cosa no es la
cosa*, y **el sitio no es la clase**. Aquí el sitio sería `scripts/sala_maquina.py`, que ya
rechaza; la clase es *todo camino que llega a un derivado del expediente*.

---

## 3. El write-set de 3B en tres categorías, cada una con su respuesta

La tanda **no** tiene una respuesta única. Tres categorías, y la categoría la fija **cómo se
calcula el artefacto**, no su clase del §25.2.

| Cat. | Cómo se calcula | Filas | Respuesta al préstamo |
|---|---|---|---|
| **P** | función pura de su entrada, por documento o por mensaje | #14, #15, #24, #26 | **desviar** — la bandeja es correcta y el CP10 la integra |
| **A** | agregado read-modify-write sobre su propia versión anterior | #17, #19, #21, #23 | **rechazar** (C5) |
| **G** | agregado puro sobre una población que la bandeja parte | #16 | desviar, **declarando la población** (C6) |
| **L** | append-only | #22, #27 | **un solo hogar**: exento y al árbol vivo, nunca desviado (C7) |

Cuatro categorías, no tres: la G se separó de la P al medir el §1.3, porque compartir respuesta
con la P la habría dejado publicando un agregado parcial con aspecto de total.

**Qué significa «rechazar» para la categoría A, en concreto:** que la costura entregue un
`Deposito` es el sitio equivocado para decidirlo, porque el `Deposito` ya viene desviado. La
decisión va **arriba**, en la misma puerta que ya rechaza: si el caso no está disponible, el
subcomando aborta con código 2 y cero bytes, como el Task 9. Lo que 3B añade es que **eso deje de
depender de que el entrypoint se acuerde**: la escritura misma lo exige.

---

## 4. Las piezas

### Pieza D — la costura sabe decir «no» además de «desvía»

Hoy `deposito()` tiene dos salidas: autoriza (al canon) o autoriza (a la bandeja). La categoría A
necesita una tercera, y no es un caso especial: es la que faltaba.

```python
def deposito(ref, rel_base, origen, *, clase, agregado=False, modo="libre", raiz=None)
```

`agregado=True` significa *«este artefacto se calcula desde su propia versión anterior»*. Con él,
cuando el guard desviaría, la costura **lanza** `AgregadoNoDesviable` en vez de entregar un
`Deposito` a la bandeja.

Por qué un parámetro y no una clase nueva del §25.2: la clase gobierna la **exención de desvío**
(`es_protocolo`) y es ortogonal a esto. `_sala_maquina_state.json` es *protocolo* **y** agregado;
`_cobertura.json` es *derivado* **y** agregado. Meterlo en `CLASES` obligaría a duplicar cada
clase en dos variantes, y el §25.2 es un vocabulario cerrado por una razón.

**Lo que no hace:** `agregado=True` no exime del mutex. Rechazar el desvío y rechazar la falta de
mutex son dos puertas distintas y el orden se conserva (mutex antes que guard, R14).

### Pieza E — las tres puertas laterales resuelven workspace o no escriben

Las tres del §1.1 pasan a resolver el workspace como lo hace `scripts/sala_maquina.py`, y a
adquirir el mutex antes de llamar al motor. **No se copia la lógica tres veces**: `sala_maquina`
tiene `_resolver_workspace` y `_drive_accesible`; se extrae a un sitio y las cuatro puertas lo
usan.

Extraer es aquí una obligación y no una elegancia: cuatro copias de la regla que decide quién
puede escribir son cuatro sitios donde puede divergir, y el repo ya midió lo que cuesta
(`_resolver_workspace` pasaba `drive_accesible=True` literal y dejó la rama offline en código
muerto durante toda una fase).

**`--case-dir` se conserva** donde ya existe, con el mismo contrato que el Task 9 le dio: es la
vía del trabajo local declarado, no un bypass.

### Pieza F — los motores reciben capacidad, no ruta

Los cuatro motores dejan de recibir un `Path` del que componen y reciben el `Deposito` (o varios,
uno por familia de artefacto y clase).

**Uno por familia, no uno por motor**, y esto es diseño y no detalle: la clase del §25.2 es **por
artefacto**. `sala_maquina` escribe `_tiempos.jsonl` (protocolo, append-only, exento) y
`01_OCR/**` (derivado, desviable) en la misma corrida. Un `Deposito` único para el motor tendría
que llevar una sola `clase`, y la primera escritura que no fuera de esa clase heredaría su
exención. Ése es literalmente el mecanismo por el que la fila #10 persiste antes del guard.

Depósitos por familia:

| Familia | Base relativa | Clase | Cat. |
|---|---|---|---|
| mensajes de correo (#14) | `01_Procesado/Emails/mensajes` | derivado | P |
| adjuntos de correo (#15) | `01_Procesado/Emails/adjuntos` | derivado | P |
| agregados de correo (#16) | `01_Procesado/Emails` | derivado | G |
| revisión, vistas y registro (#17) | `01_Procesado/Emails` | derivado | **A** |
| contenido de adjuntos (#19) | `01_Procesado/Emails/adjuntos` | derivado | **A** |
| estado de sala de máquina (#21) | `01_Procesado/02_Sala de máquina` | protocolo | **A** |
| tiempos (#22) | ídem | protocolo | L |
| cobertura (#23) | ídem + `01_Procesado/_revisar` | derivado | **A** |
| salidas del motor (#24) | `01_Procesado/02_Sala de máquina` | derivado | P |
| manifiesto del bundle (#26) | el directorio del bundle | protocolo | P |
| eventos (#27) | `00_Input` (junto a los bytes, B0-1) | protocolo | L |

**Doce depósitos para once filas**, porque la #23 escribe en dos bases. Ese descuadre es la razón
de enumerarlos: «una fila, un depósito» habría dejado la vista `_cobertura.md` fuera, que es
justo el fichero cuyo defecto está medido.

### Pieza G — la población declarada (C6)

Para la fila #16, cada agregado lleva al principio una línea que dice sobre qué se calculó y qué
quedó fuera, con el conteo:

```
<!-- poblacion: 47 mensajes de 00_Input; 12 en _pendiente_checkin/ NO incluidos -->
```

Cuando no hay nada fuera, la línea dice `0 fuera`. Que la línea exista siempre es lo que impide
que su ausencia se lea como «no había nada» — el mismo argumento por el que el Task 8b imprime lo
que no pudo verificar.

`corpus.jsonl` no admite comentarios: su población va en una **primera línea de metadatos**
(`{"_poblacion": {...}}`), y el lector la salta por la clave. La alternativa —un fichero hermano—
se descarta: un agregado y su declaración en dos ficheros es dos ficheros que se pueden desincronizar.

### Pieza H — el hogar único del append-only (C7)

Las filas #22 y #27 se declaran **no desviables** en la propia costura, no solo en la tabla del
§25: `clase="protocolo"` ya las exime, y se añade el aserto de que un append-only **nunca** recibe
un `Deposito` desviado. Si alguna vez lo recibiera, es un defecto y debe romper, no continuar.

**Y `_tiempos.jsonl` entra en `MERGE_EXCLUSIONS`.** Hoy no está, así que la copia prestada lo trae
y el merge se encuentra el mismo fichero crecido por los dos lados. Es la mitad que faltaba del
«un solo hogar»: exento de desvío arriba y excluido del merge abajo.

**Lo que NO se construye aquí:** la concatenación en el CP10. Cambiar el checkin es la pieza con
más radio de daño del repo y no se toca de paso en una tanda de derivados. Con la exclusión y el
aserto, el caso que la concatenación arreglaría **no se alcanza**; queda declarado como el remedio
si alguna vez se alcanza.

---

## 5. Las fronteras — una por mutante

| # | Frontera | El mutante |
|---|---|---|
| **G1** | `agregado=True` **rechaza** cuando el guard desviaría | tratar `agregado` como ignorado |
| **G2** | `agregado=True` **no** rechaza cuando el caso está disponible | rechazar siempre |
| **G3** | `agregado=True` no exime del mutex | poner el rechazo por agregado antes del mutex |
| **G4** | `scripts/atomize_emails.py --ref` aborta sobre caso prestado, con cero bytes | quitar la resolución de workspace |
| **G5** | `core/adjuntos_contenido/__main__.py` ídem | ídem |
| **G6** | `aplicar_resumenes` ídem | ídem |
| **G7** | las cuatro puertas usan **una** resolución, no cuatro copias | duplicar la regla en una de ellas con `drive_accesible=True` |
| **G8** | cada familia lleva su propia clase; una escritura no hereda la exención de otra | dar un `Deposito` único de clase `protocolo` al motor de sala de máquina |
| **G9** | la #23 escribe en **dos** bases y las dos pasan por la costura | dejar `_cobertura.md` fuera |
| **G10** | la vista `_cobertura.md` se **fusiona**, no se reduce al delta | devolver `[]` desde `_cobertura_previa` |
| **G11** | los agregados de la #16 declaran su población, con `0 fuera` cuando no hay nada | suprimir la línea cuando el conteo es 0 |
| **G12** | el conteo de la población es el real, no el de la corrida | contar los incluidos como total |
| **G13** | un append-only nunca recibe un `Deposito` desviado (rompe si lo recibe) | degradar el aserto a aviso |
| **G14** | `_tiempos.jsonl` está en `MERGE_EXCLUSIONS` | quitarlo |
| **G15** | el mutex se sostiene durante toda la corrida del motor, no solo al entrar | liberarlo tras la resolución |
| **G16** | `--case-dir` sigue siendo vía legítima y no bypass del mutex | aceptar `--case-dir` sin mutex |
| **G17** | el censo (b) baja por la migración, y su tope solo baja | subir el tope |

Diecisiete fronteras, diecisiete mutantes. El arnés restaura en **binario** y adapta el ancla al
terminador de línea del fichero; un mutante que mate más tests de los previstos está **mal
apuntado**, no bien elegido, y se reapunta en vez de ajustarle la expectativa.

---

## Global Constraints

- **No se toca `case_mutex.py`** (cuatro rondas, 17 mutantes) ni `mutex_sesion.py`.
- **No se toca el CP10 ni el CP11 del checkin.** Ver §4-H.
- **`core/anon/` no se toca**, regla del repo.
- **Core no imprime**; los avisos viven en los entrypoints.
- **El reloj explícito**: `now_iso()` es naïve; los caminos nuevos que comparen instantes pasan
  `now_iso_utc`.
- **Suite con dos semillas** (777 y 31337). `pytest` no corre en CI.
- **No se edita el árbol con una corrida de pytest en background** — los guards de documentación
  leen del disco en tiempo de test.

## File Structure

```
core/casos/escritura.py               `agregado=` + AgregadoNoDesviable (pieza D)
core/casos/workspace_model.py         el código de error nuevo
core/casos/puerta.py                  NUEVO — resolución de workspace compartida (pieza E)
scripts/sala_maquina.py               usa la puerta compartida; 12 depósitos (E, F)
scripts/atomize_emails.py             resuelve workspace y adquiere mutex (E)
core/adjuntos_contenido/__main__.py   ídem (E)
core/adjuntos_contenido/resumen.py    ídem (E)
core/email_atomize/pipeline.py        recibe Deposito; población declarada (F, G)
core/adjuntos_contenido/pipeline.py   recibe Deposito (F)
core/split_documental.py              recibe Deposito (F)
core/config.py                        `_tiempos.jsonl` → MERGE_EXCLUSIONS (H)
tests/test_escritura_agregado.py      NUEVO — G1-G3
tests/test_puertas_laterales.py       NUEVO — G4-G7, G15, G16
tests/test_depositos_por_familia.py   NUEVO — G8, G9, G13
tests/test_agregados_poblacion.py     NUEVO — G10-G12
```

## Task 1: medir el radio ANTES de migrar

- [ ] Censo AST de llamadas a `caso_path`/`emails_out_dir` desde los cuatro motores y sus puertas.
- [ ] Reproducir en test el defecto del §1.2 (dos corridas durante el mismo préstamo) **antes** de
      tocar producción. Sin ese rojo, la pieza D no tiene por qué existir.
- [ ] Reproducir el §1.1: las tres puertas escriben en el canon de un caso prestado.

## Task 2: Pieza D — la tercera salida de la costura

- [ ] `agregado=` + `AgregadoNoDesviable`; el §10 de códigos crece y se dice en cuánto.
- [ ] G1-G3 con su mutante.

## Task 3: Pieza E — la puerta compartida

- [ ] Extraer la resolución de `scripts/sala_maquina.py` a `core/casos/puerta.py` **sin cambiarla**
      (extracción pura, con los tests de sala de máquina verdes como prueba de equivalencia).
- [ ] Cablear las tres puertas laterales. G4-G7, G15, G16 con su mutante.

## Task 4: Pieza F — depósitos por familia

- [ ] Los doce depósitos del §4-F. Motores reciben capacidad.
- [ ] G8, G9, G13 con su mutante.

## Task 5: Piezas G y H — población y hogar único

- [ ] Población declarada en los tres agregados de la #16 (`corpus.jsonl` por primera línea).
- [ ] `_tiempos.jsonl` a `MERGE_EXCLUSIONS`; aserto del append-only.
- [ ] G10-G12, G14 con su mutante.

## Task 6: E2E de los cuatro planos, por categoría

- [ ] Por cada una de las cuatro categorías del §3, doblar **los dos** destinos (canon y bandeja) y
      comprobar **cuál** cambió y que el otro no. El censo AST no es la prueba de cierre.
- [ ] Para la categoría A: dos corridas durante el mismo préstamo, y comprobar que la segunda
      **no** existe (rechaza) en vez de comprobar que su agregado es correcto.

## Task 7: censo y trinquete

- [ ] Recontar el censo (b). El tope **solo baja**; si sube, se declara como deuda con su fila.
- [ ] Extender el trinquete AST del Task 7 de 3A a las cuatro puertas: producción entra por la
      puerta compartida, no por `caso_path` crudo.

## Criterio de salida

1. Las tres puertas laterales abortan sobre un caso prestado, con **cero bytes** verificados por
   hash.
2. Ningún agregado de la categoría A se escribe en la bandeja: la corrida rechaza.
3. La vista `_cobertura.md` conserva sus filas tras una corrida incremental, medido con más de
   dos filas previas.
4. Los tres agregados de la #16 declaran su población, también cuando no falta nada.
5. `_tiempos.jsonl` tiene un solo hogar, arriba y abajo.
6. Diecisiete fronteras, diecisiete mutantes, cada uno muerto por la suya.
7. Suite verde con dos semillas, con la variación del conteo explicada.

## Lo que este plan deliberadamente NO hace

- **No construye la concatenación de append-only en el CP10.** §4-H, con su razón.
- **No migra 3C** (#18, #20, #25: la poda y el archivado), que tiene documento y rondas propias.
- **No arregla `MEJORAS #55.1`** (fundir exports de WhatsApp del mismo chat). `_declarar_solapes`
  seguirá declarando sin fundir; lo que cambia es que su escritura pase por la costura.
- **No toca las seis filas de protocolo** que el Task 6 de 3A dejó fuera (#4, #7, #10-#13).
- **No cambia el orden deliberado de la fila #10** (persistir ocurrencias antes del guard, N2 de
  `MEJORAS #120`): esa fila es de 3A, no de aquí.

## Lo que sigue SIN VERIFICAR, y se declara

- **Si la categoría A es exhaustiva.** Se enumeró leyendo los cinco read-modify-write que
  encontré; un sexto agregado que lea su versión anterior por un camino que no vi quedaría
  clasificado como P y se desviaría. Lo que lo cerraría es un detector, no una lista, y el
  detector no está en este alcance.
- **La coherencia de la población de la #16 cuando la bandeja tiene `.eml` de otro origen.** La
  línea declara conteos; no reconcilia identidades entre árbol y bandeja.
- **El coste en tiempo de resolver workspace en las tres puertas laterales.** Añade un escaneo de
  catálogo a comandos que hoy no lo hacen. No medido.
- **La extracción de `_resolver_workspace` como equivalencia.** Los tests de sala de máquina
  verdes son evidencia fuerte, no prueba: si la extracción cambia un comportamiento que ningún
  test cubre, no lo veremos.
- **La reacción del mutex a un salto real de NTP**, heredada de 3A y del plan del mutex.
- **Las seis remediaciones de R13 no tienen ronda propia** y esta tanda las usa por transitividad.

---

## 6. Adjudicación de la revisión adversarial R18 (Codex, 2026-08-26) — NO-EJECUTABLE, pendiente

- **Objeto revisado:** este documento, **rev. 1**, en el commit `d1b09e2`.
- **Ronda:** R18, la ronda de **DISEÑO** de 3B. **R15 cubrió 3A y solo 3A**; ésta no la reutiliza.
- **Revisor:** Codex por CLI sobre un `git archive` sin `.git`, solo lectura por construcción.
- **Informe recibido:** `docs/superpowers/specs/2026-08-26-apertura-v1-plan3b-r18-adversarial-review.md`, `sha256` `4a5415ba5520738d…`, recomputado al archivarlo y **coincide**.
- **Hallazgos:** 15 — 4 CRÍTICOS, 5 ALTOS, 5 MEDIOS, 1 BAJO. **15 confirmados, 0 refutados.**
- **Remediado en:** nada. **No se escribe código con este diseño.**

**Qué ejecutó el revisor:** 222 tests dirigidos (219 pasados, 3 `slow` omitidos), cinco sondas
propias y censos de llamadores por AST.

### 6.1. El crítico que invalida la pieza, y por qué era predecible

**H18-01: la costura pierde la copia que la pieza E acaba de resolver.** `deposito(ref, …)` recibe
un `CaseRef`, y su `_identidad()` hace `CaseCatalog().localizar(ref)` — que por contrato **solo
localiza el canon** y declara que no decide la copia de trabajo. Mientras tanto `CaseWorkspace`
guarda la raíz efectiva en `working_root`, que la firma que propuse **no transporta**.

El revisor lo midió: canon prestado + checkout separado, y el depósito escribió bajo `CASOS_ROOT`;
**el checkout quedó intacto.**

Así que las piezas E y F **no se pueden ejecutar juntas** con las interfaces que fijé: E resuelve un
workspace y F lo tira. Y sobre la herramienta diaria del equipo —que trabaja en `local_checkout` /
`local_scratch`— el efecto sería escribir o rechazar contra el canon en vez de contra la copia en la
que se está trabajando.

**Es la misma clase, otra vez: `ref` no es `working_root`.** Un identificador de caso no es la copia
sobre la que se opera, igual que el nombre de la carpeta no era la identidad (R14) y el sitio no era
la clase (R15). **Sexta aparición.** Y esta vez la señal estaba a la vista: `CaseWorkspace` existe
precisamente porque hay más de una copia, y diseñé la costura de 3B como si `ref` bastara.

### 6.2. Y los otros tres críticos son, cada uno, una pieza que no hace lo que dice

**H18-02: `agregado=True` no puede rechazar la fila #21.** La costura llama a `guard_escritura` con
`es_protocolo=(clase == "protocolo")`, y `decidir_escritura` devuelve **siempre** `desviar=False`
para protocolo, incluso con el caso prestado. `_sala_maquina_state.json` es de clase `protocolo`, así
que nunca desviaría y por tanto **mi rechazo nunca dispararía** sobre la fila que más lo necesita.

**Es una segunda guarda inerte, en la misma sesión que descubrió la primera** (`es_copia_prestada`,
H16-01). Dos condiciones que no pueden ser verdad nunca, escritas por mí en dos documentos
distintos el mismo día. Eso ya no es un descuido: es que **enuncio una condición y no compruebo su
alcanzabilidad**, que es una comprobación de tres líneas.

**H18-03: la fila #26 es A, no P.** `core/sala_maquina.py:883` llama a
`split.reconciliar_manifiesto(previo, propuesto)`, que hereda `doc_id`, avanza `next_doc_id` y
acumula tombstones **desde el manifiesto anterior**. Es read-modify-write. Lo verifiqué en la
fuente. El revisor además lo midió: dos corridas sobre la misma foto viva y la segunda perdió los
rangos `5-9` de la primera y reutilizó `d02`.

Mi §«SIN VERIFICAR» declaraba justo esta duda —*«un sexto agregado que lea su versión anterior por
un camino que no vi quedaría clasificado como P»*— y la dejé declarada en vez de mirarla. **Declarar
una duda no la resuelve, y aquí bastaba un `grep`.**

**H18-04: los doce depósitos no hacen exigible la familia que representan.** `Deposito` autoriza
cualquier relativa contenida bajo su `_base`; no lleva lista de ficheros ni la marca de agregado. Y
mis bases **se solapan a propósito**: `01_Procesado/Emails` sirve a #16 (G) y a #17 (A);
`…/adjuntos` a #15 (P) y #19 (A); `…/02_Sala de máquina` a #21 (A), #22 (L) y #24 (P). Así que un
motor puede escribir el artefacto de una categoría con el depósito de otra **sin salirse de la
contención y sin violar ningún tipo**. La frontera G8 no lo ve porque muta otra cosa.

O sea: la separación por familia era **nominal**. Yo mismo escribí que «uno por motor» dejaría
heredar exenciones, y el remedio que propuse las deja heredar igual por un camino distinto.

### 6.3. Los quince, uno por uno

| # | Sev. | Veredicto | Qué se hace |
|---|---|---|---|
| **H18-01** la costura pierde `working_root` | CRÍTICO | **CONFIRMADO** (verificado en `escritura.py:119-132` y `case_catalog.py:1-15`) | **Rev. 2**: la costura tiene que recibir el workspace, no el `ref`. Es un cambio de interfaz, no un parámetro |
| **H18-02** `agregado=True` inerte para protocolo | CRÍTICO | **CONFIRMADO** (verificado en `repository_checkout.py:541-576`) | **Rev. 2**: el rechazo por agregado no puede colgar del desvío del guard, porque protocolo nunca desvía |
| **H18-03** la fila #26 es A | CRÍTICO | **CONFIRMADO** (verificado: `sala_maquina.py:883` → `reconciliar_manifiesto`) | **Rev. 2**: recategorizar, y **medir** las once en vez de clasificarlas por lectura |
| **H18-04** los depósitos solapan bases entre categorías | CRÍTICO | **CONFIRMADO** | **Rev. 2**: la familia tiene que ser exigible, no nominal |
| **H18-05** las cuatro respuestas no son alcanzables en motores monolíticos | ALTO | **CONFIRMADO** | **Rev. 2**: una corrida escribe artefactos de varias categorías; «rechazar» y «desviar» no son compatibles dentro de la misma llamada |
| **H18-06** «tres puertas» no es el censo de la superficie | ALTO | **CONFIRMADO** | **Rev. 2**: el censo se hace por AST, no por lectura. La cifra «tres» era una lista, no una medición |
| **H18-07** la pieza H evita el merge perdiendo `_tiempos.jsonl` | ALTO | **CONFIRMADO** | **Rev. 2**: meterlo en `MERGE_EXCLUSIONS` no es «un solo hogar», es descartar el del prestatario. Mi §4-H lo presentaba como cierre y es una pérdida |
| **H18-08** el depósito de #27 no cubre al escritor real | ALTO | **CONFIRMADO** | **Rev. 2**: la base que asigné no es donde escribe `append_event` tras el Task 8 de la Fase 1 |
| **H18-09** la población de G no tiene magnitud computable | ALTO | **CONFIRMADO** | **Rev. 2**: «12 en la bandeja» exige un conteo que el motor no puede hacer donde lo puse |
| **H18-10** la línea nueva de `corpus.jsonl` no tiene el lector que afirmo | MEDIO | **CONFIRMADO** | **Rev. 2**: dije «el lector la salta por la clave» sin comprobar que exista tal lector |
| **H18-11** E no puede ser extracción pura y core silencioso a la vez | MEDIO | **CONFIRMADO** | **Rev. 2**: `_resolver_workspace` imprime; extraerlo a `core/` choca con «core no imprime» |
| **H18-12** G16 contradice el contrato que dice conservar | MEDIO | **CONFIRMADO** | **Rev. 2** |
| **H18-13** el rechazo de D ocurre después de una escritura del guard | MEDIO | **CONFIRMADO** | **Rev. 2**: el guard emite `pendiente_checkin` **antes** de que yo rechace, así que un rechazo deja un evento de un desvío que no ocurrió |
| **H18-14** las diecisiete fronteras no son diecisiete mutantes | MEDIO | **CONFIRMADO** | **Rev. 2**: y uno de los propuestos ya mata tests preexistentes por razones ajenas a su frontera |
| **H18-15** afirmaciones y cifras de superficie inexactas | BAJO | **CONFIRMADO** | Se corrigen en la rev. 2 con el patrón de medición publicado |

### 6.4. Qué sobrevive de la rev. 1

**El diagnóstico, medido y confirmado por el revisor por su cuenta:**

- las tres puertas laterales **sí** escriben hoy sobre el canon de un caso prestado — que es lo que
  yo había medido y él reprodujo;
- los tres subcomandos de `sala_maquina` **sí** rechazan con código 2 sin tocar bytes;
- desviar un agregado read-modify-write **sí** lo rompe, y él lo demostró sobre una fila que yo
  había clasificado mal.

**Lo que no sobrevive es el remedio.** Las cuatro piezas —D, E, F, H— fallan cada una por su
cuenta, y H18-01 hace que E y F sean incompatibles entre sí. La rev. 2 no es una edición: es
rediseñar la interfaz por la que un motor recibe permiso de escritura.

**Y una consecuencia de alcance que hay que decir en alto:** H18-01 no es solo de 3B. Si la costura
de 3A no puede expresar «escribe en esta copia», entonces **la costura tal como se mergeó en #251
solo sirve para el canon**, y eso limita lo que 3A puede reclamar. No se toca `escritura.py` desde
aquí sin ronda propia, pero queda dicho.
