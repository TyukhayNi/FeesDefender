# Autorrelleno de las fichas de colaborador: la firma del correo como fuente

> **Estado:** rev. 1 (2026-09-04). Diseño aprobado en conversación, sin construir todavía.
> **Origen:** encargo de Nikolai del 2026-09-04 — que las fichas de colaboradores del CRM
> se rellenen solas: los nuevos que nazcan con teléfono, y los ya dados de alta que se completen.
> **Radio de daño y rondas:** escribe en el CRM del cliente pero **sólo rellena lo vacío** →
> **una ronda adversarial sobre el diff** (`CLAUDE.md`, §«Cuántas rondas»). No decide quién
> puede escribir sobre qué copia y no borra datos de cliente, así que no entra en la
> categoría de dos rondas.

## 1. Qué problema resuelve

Las fichas de colaborador del CRM nacen y viven casi vacías. Medido el 2026-09-04 sobre los tres
colaboradores vinculados a **W-02Q38C** (ids 40, 61, 466): los tres tienen `telefono1`, `nif_cif`,
`tipo` y `notas` **vacíos**, y uno de los tres no tiene ni móvil. El dato existe —los consultores de
E&V firman sus correos con móvil, fijo y cargo, y esos correos ya están en el expediente— pero nadie
lo lleva del correo a la ficha.

El RUNBOOK §9.4 ya prescribe el remedio como paso **manual**: «Ficha completa (móvil + fijo)
buscando la firma en su correo `@engelvoelkers.com`; si ya existe → `GET → merge → PUT` para no
pisar». Esto lo mecaniza.

## 2. Alcance

**Dentro:**

1. Extraer **móvil, fijo y cargo** de las firmas de los `.eml` del expediente.
2. **Completar** en el CRM los colaboradores ya dados de alta, rellenando **sólo campos vacíos**.
3. Cerrar dos defectos vivos que este trabajo propagaría (§7).

**Fuera, y por qué:**

- **DNI/NIE y dirección postal desde los contratos del Drive.** Pendiente de una decisión de
  Nikolai que no ha tomado: los contratos llevan documento y domicilio de empleados de E&V que no
  son parte de ningún caso, y volcarlos al CRM del despacho es un tratamiento con otra finalidad y
  otro responsable. No se empieza sin que él lo valore.
- **El cargo NO se escribe en el CRM.** Decidido por Nikolai el 2026-09-04. Razón medida: la ficha
  de colaborador **no tiene campo de cargo** (§3, H-06). El cargo se extrae y sale en el informe,
  y nada más.
- **El alta automática de colaboradores.** Ver §4: no es una limitación técnica, es que el corpus
  no contiene esa información.

## 3. Verdad de campo (medido el 2026-09-04, no supuesto)

Sobre los **6 `.eml`** de W-02Q38C y contra el CRM en vivo. Los datos personales quedan fuera de
este documento por `SEGURIDAD_DATOS.md`: las personas se citan por su **id de CRM**.

| # | Hallazgo | Cómo se midió |
|---|---|---|
| **H-01** | **Sólo 3 de los 6 `.eml` traen el marcador de firma** (`-- ` / «Enviado desde mi…»). En los otros 3 la firma está presente **sin marcador ninguno**, al final del cuerpo | Parseo de los 6 con `email.parser` + el `_RE_SIG` real de `core/email_atomize/inline.py` |
| **H-02** | **La firma del cuerpo no es la del `From:`.** En 2 de los 6, el bloque de firma pertenece a una persona distinta del remitente: uno es un reenvío, y en el otro la firma va **dentro de un bloque citado `> `** | Comparación del `From:` con el email que aparece dentro del bloque |
| **H-03** | Hay **dos plantillas corporativas** distintas, con etiquetas distintas: `Telf:` / `Móvil:` en una, y `Tel. Fijo: … / Ext. ####` en la otra. Los valores llegan con `+34`, con espacios y **envueltos en asteriscos** (negrita HTML degradada) | Inspección redactada de los 6 cuerpos |
| **H-04** | Una de las dos plantillas **no lleva móvil**, sólo fijo con extensión. Y un `.eml` no lleva firma personal ninguna (es institucional) | Ídem |
| **H-05** | **`_PROP_NIF["colaboradores"] = "nif"` es falso: esa property no existe.** El CRM devuelve **HTTP 500** y su mensaje enumera el contrato real: `ccc, cp, direccion, email, fax, iva, movil, nacionalidad, nif_cif, nombre, notas, poblacion, provincia, telefono1, telefono2, telefono3, tipo, web`. Consecuencia medida: `resolver_parte("colaboradores", nif="12345678Z")` devuelve `sin_comprobar=('NIF (HTTP 500)',)`, y `_resolver_colaborador` **aborta** el camino entero en cuanto la ficha trae un NIF | `GET /api/element_register/colaboradores/40?properties=nif` (método del §14.6) y ejecución de `resolver_parte` |
| **H-06** | **No hay campo de cargo.** `tipo` es un `Select` con enum cerrado `Sin Asignar / Colaborador / Perito / Tercero`: escribir un puesto ahí corrompe la taxonomía. Los únicos huecos de texto libre son `notas` (HTML) y `web` | El 500 de H-05 + `docs/CRM_SUDESPACHO_ATLAS.md` §colaboradores |
| **H-07** | La premisa del encargo «el pipeline de correo descarta la parte donde vive el teléfono» **es inexacta**. `normaliza_cuerpo` (`inline.py:46`) trunca en el marcador, pero sus consumidores son **fingerprints, dedup e índice de búsqueda**; la ficha MD del átomo escribe `m.cuerpo.strip()` **verbatim** (`render.py:109`) y el `.historial.md` conserva el texto **VERBATIM**. Lo que se trunca es la **clave**, no el cuerpo | `git grep` de los llamadores de `normaliza_cuerpo` |

**Qué se lleva H-07 por delante:** nada del diseño, pero sí de su justificación. La fuente sigue
siendo el `.eml` crudo, y ahora por la razón correcta: es **autoritativo** y no depende de que el
atomizador haya corrido, no porque el corpus haya perdido la firma.

## 4. La pregunta que fija el alcance: ¿qué colaborador se da de alta?

Preguntado por Nikolai el 2026-09-04, antes de aprobar el diseño. **Respuesta medida: el corpus no
lo sabe.**

Sobre W-02Q38C: **7** direcciones `@engelvoelkers.com` aparecen en los 6 `.eml`; **6** de ellas ya
existen como colaborador en el CRM; y **sólo 3** están vinculadas a este expediente. En el otro
sentido, el colaborador **61 está vinculado y su firma no aparece en el corpus** (su correo llevaba
la firma de otra persona).

El conjunto «firma en el corpus» **no es ni subconjunto ni superconjunto** de «es colaborador de
este caso». Las tres direcciones que ya son colaboradores pero no están vinculadas están en los
hilos por CC o por ser una unidad interna de E&V. Decidir si una de ellas es colaborador *del caso*
es juicio, no parseo — y es exactamente lo que advierte `[APER-52]` del RUNBOOK.

**Decisión:** el alta la sigue decidiendo el humano, escribiendo la lista en `_ficha_crm.yaml`. El
extractor **sólo enriquece a los que ya están en esa lista**. El informe incluye una sección de
**candidatos** («esta dirección firma en el corpus y no está en tu lista», con su id de CRM si
existe), etiquetada como sugerencia a revisar. Nunca un alta.

## 5. Arquitectura

```
.eml crudos ──A──> propuesta ──(Nikolai aprueba)──> _ficha_crm.yaml ──C──> CRM
              leer            informe MD             (ya existente)   completar sólo vacíos
```

La propiedad que hace este reparto correcto: **las piezas A y B no escriben en el CRM en absoluto.**
La única escritura al CRM es la pieza C, que es el espejo de un comportamiento ya aprobado y
mergeado para el contrario (`_completar_contrario_existente`, PR #275). Un solo camino de
escritura, no dos.

### 5.1 Pieza A — `core/email_firmas.py` (nuevo)

Lee firmas de un `.eml`. **No conoce el CRM ni el expediente.**

```python
def extraer_firmas(eml: Path) -> ResultadoFirmas
```

- **Un ancla, un refinamiento y una puerta.** *Precisado al implementar, el 2026-09-04: la primera
  redacción hablaba de «dos anclas», el marcador y el email, y la segunda sólo «cuando no hay
  marcador». Medido sobre los 6 `.eml`, el email corporativo aparece en los **seis** bloques —
  también en los tres que traen marcador—, así que un solo mecanismo los cubre todos y el marcador
  deja de estar en el camino crítico.*
  - **Ancla:** la línea con el email corporativo. Siempre, haya marcador o no.
  - **Refinamiento:** si existe un marcador entre el cuerpo y esa línea, **aprieta el límite
    superior** del bloque para no arrastrar prosa. No decide si hay bloque; sólo dónde empieza.
  - **Puerta obligatoria:** corroboración — al menos una de `ENGEL&VÖLKERS` / `EV MMC SPAIN` / una
    etiqueta de teléfono en la ventana. Sin ella no hay bloque: una dirección suelta en un texto no
    es una firma, y sin esta puerta cualquier correo que **mencione** a un consultor produciría una
    firma suya inventada.
- Antes de leer se quitan las marcas de cita `> ` y se descartan las URL interleaved (H-03 midió
  enlaces de mapas partiendo las líneas). **Los asteriscos de negrita NO se quitan del bloque**
  —esto también se precisó al implementar—: son la única señal que localiza la línea del nombre, y
  el cargo se posiciona respecto a ella porque no tiene etiqueta. Se limpian por valor, al leer cada
  campo, no antes.
- **Atribución por el email de DENTRO del bloque, nunca por el `From:`** (H-02). Un bloque sin
  email dentro no se atribuye a nadie: `NO_ATRIBUIBLE`.
- Cada firma registra `procedencia`: `directo` (fuera de zona citada) o `citado`. Importa porque un
  bloque citado es más antiguo.
- Campos: `movil`, `telefono` (cortando en `/ Ext.`: la extensión no es parte del número) y
  `cargo`. El cargo **no tiene etiqueta** en ninguna de las dos plantillas, así que se resuelve por
  posición —primera línea no vacía tras la línea del nombre que no sea razón social, dirección,
  teléfono, email ni el disclaimer— y si no se puede decidir, se deja vacío y se declara.
- Limpieza antes de `normalize_es_phone`, que no quita letras ni asteriscos.

### 5.2 Pieza B — `scripts/crm_colaboradores_firmas.py` (nuevo)

- `report --case-id <W-code>`: recorre `00_Input/**/*.eml`, corre la pieza A, agrupa por email, lee
  la ficha de cada colaborador del CRM y escribe **`01_Procesado/_firmas_colaboradores.md`**.
  - **Por qué ahí y no en `00_Input`:** `00_Input` es crudo intocable por la regla de
    idempotencia de `CLAUDE.md`. Y fuera del repo en cualquier caso, porque el informe lleva PII.
  - Contenido por persona: qué campos faltan en el CRM, qué dice la firma, **de qué fichero y qué
    línea** sale cada dato, y **qué no se pudo mirar**. Más la sección de candidatos del §4.
- `apply --confirmar`: mete los campos aprobados en `00_Input/_ficha_crm.yaml`, **sólo en claves
  ausentes o vacías**. No toca el CRM.

Después, el CLI que ya existe —`python -m scripts.crm_ficha --case-id <W-code>`— lleva el YAML al
CRM a través de la pieza C. Eso también resuelve el caso del expediente ya abierto: re-ejecutar ese
CLI es lo que completa las fichas existentes.

### 5.3 Pieza C — completar el colaborador existente

En `core/sudespacho_relations.py`, espejo de `_completar_contrario_existente`:

```python
def get_colaborador(colab_id: str) -> dict          # GET con ?properties= explícito
def update_colaborador(colab_id: str, cambios: dict) -> dict   # PUT
def _completar_colaborador_existente(colab_id: str, datos: NuevoColaborador) -> None
```

```python
_COMPLETABLES_COLABORADOR = (
    ("email",    "email"),
    ("movil",    "movil"),
    ("telefono", "telefono1"),
    ("nif",      "nif_cif"),     # nif_cif, no nif — H-05
)
```

Esta lista es **más ancha que lo que la pieza A extrae**, y no es un descuido: la pieza C lleva al
CRM lo que haya en `_ficha_crm.yaml`, venga de donde venga. De la firma sólo llegan `movil` y
`telefono`; `email` y `nif` los escribe Nikolai a mano y hoy tampoco llegaban. `cargo` no está en la
lista porque no tiene campo (H-06).

Contrato, idéntico al del contrario y por las mismas razones:

- **Sólo rellena lo VACÍO.** La ficha local aporta datos pero no manda sobre lo que ya hay: E&V u
  otra sesión pueden haber corregido algo ahí, y pisarlo sería destruir trabajo ajeno.
- **No lanza.** Completar la ficha es un extra sobre el vínculo; perder el vínculo por no poder
  escribir un teléfono sería peor que quedarse sin el teléfono. Lo que no se pueda hacer se
  registra en el log.
- **El GET de verificación tras escribir** lo exige el RUNBOOK §9 y se mantiene.

Dos decisiones de diseño con su fundamento:

**(a) El PUT manda sólo los campos que se rellenan, y el verbo está medido.** *Corregido durante la
ejecución, el 2026-09-04: la primera redacción de este apartado era falsa y de la clase peligrosa.*
Decía que un «GET del conjunto completo → merge → PUT del conjunto completo» era correcto «bajo las
dos hipótesis», cuando el código que este diseño especifica manda al PUT **sólo los deltas**, no el
conjunto — si el PUT fuera de reemplazo, esa frase habría dado por cubierto exactamente lo que no
cubría, y el resultado sería borrar datos del cliente. Lo destapó el implementador de la Task 3 al
medir que la tupla de properties cubre 12 de las 18.

**La evidencia real:** el PUT es **PARCIAL — preserva los campos omitidos**, verificado en vivo el
2026-07-18 sobre un expediente desechable (`INTEGRACION_SUDESPACHO.md` §10.7, `[APER-26]`): un
`PUT {"Notas": …}` cambió sólo `Notas` y dejó intacto el resto. Y la ruta
`/api/element_register/{element}/{id}` es **genérica sobre el elemento**, así que lo medido es el
verbo y la ruta, no un elemento concreto.

**Y se declara qué clase de evidencia es:** de endpoint, **no** específica de `colaboradores`. Nadie
ha hecho la prueba sobre este elemento, y hacerla exigiría crear un colaborador desechable en el
tenant del cliente sin endpoint de borrado documentado. El GET, por su parte, no necesita las 18
properties: existe para saber **qué está vacío**, y lo que no se pide tampoco se puede borrar,
porque nunca se envía.

**(b) El gancho va en un `_resolver_o_crear_colaborador(datos, client)` COMPARTIDO** por
`ensure_colaborador_vinculado` y `ensure_colaborador_vinculado_judicial`, no copiado en las dos. El
propio módulo ya lleva escrito, a raíz de H-05 de la revisión del PR #275, que «añadir el contrario
judicial y olvidar el colaborador judicial es el mismo error de siempre: cerrar una propiedad para
un rol no la cierra para los demás». Poner el gancho dos veces es firmar la tercera aparición.

## 6. Veredictos: «no lo sé» y «no hay» no son lo mismo

Cada campo de cada persona sale del informe con un veredicto explícito. Copia la idea de
`core/crm_ficha_validacion.py` (`SIN_COMPROBAR` / `NO_BUSCABLE`).

| Veredicto | Significa | Qué NO significa |
|---|---|---|
| `ENCONTRADO` | El campo se leyó, con fichero y línea de origen | — |
| `FIRMA_SIN_CAMPO` | Hay bloque de firma de esta persona y **no** trae ese campo | No significa «no tiene móvil»: H-04 midió una plantilla corporativa que simplemente no lo incluye |
| `SIN_FIRMA` | La persona aparece en el corpus, pero no se le encontró bloque de firma | Ídem |
| `NO_ATRIBUIBLE` | Se encontró un bloque, pero sin email dentro: no se sabe de quién es | No se propone nada |
| `NO_LEIBLE` | El `.eml` no se pudo parsear o no tiene parte `text/plain` | **Se declara.** No se cuenta como ausencia de dato |
| `CONFLICTO` | Dos bloques dan valores distintos para la misma persona y ningún `directo` más reciente decide | No se propone nada — se falla cerrado, como el dedup del PR #272 |

La regla que gobierna la tabla: **un dato que no se pudo mirar nunca se convierte en un dato que no
existe.** Un `.eml` ilegible no autoriza a escribir que ese colaborador no tiene teléfono.

## 7. Dos defectos vivos que este trabajo propagaría

No es alcance añadido: sin cerrarlos, la pieza C escribe basura o no llega a correr.

| | Defecto | Medido | Remedio |
|---|---|---|---|
| **D1** | `_PROP_NIF["colaboradores"] = "nif"` | HTTP 500: la property no existe (H-05). `resolver_parte` devuelve `sin_comprobar` y `_resolver_colaborador` **aborta** en cuanto la ficha trae NIF | `"nif_cif"`. El atlas —SSOT de la superficie— ya lo decía; el código lo contradecía |
| **D2** | `_colaborador_de` (`core/crm_ficha.py:73`) usa `str(d.get(...))` en los cinco campos | `movil:` presente y vacío en el YAML → `None` → `str(None)` → **`"None"`**, que es *truthy*, y `normalize_es_phone` no quita letras: devuelve `"None"` intacto | Usar `_escalar`, que ya existe en el módulo. Es el **mismo H-09** que se cerró para `cp`/`provincia`/`telefono` del contrario y quedó abierto para el colaborador entero — y para `contrario.movil` |

**Por qué D2 es de esta pieza y no de otra:** la pieza C escribe `datos.movil` en un campo vacío del
CRM. Con D2 vivo, escribiría la cadena literal `"None"` en la ficha de un colaborador del cliente.

## 8. Verificación

**Fixtures sintéticas con los seis esqueletos reales**: mismos marcadores, mismas etiquetas, misma
disposición de líneas; datos inventados (`612345678`, `912345678`, `12345678Z`). Ningún dato real
entra en `tests/`, por `SEGURIDAD_DATOS.md`.

Cobertura por hallazgo, para que cada uno tenga su test:

| Hallazgo | Test |
|---|---|
| H-01 | Firma **sin marcador** detectada; y una dirección suelta sin corroboración **no** produce firma |
| H-02 | **`From:` = B, firma de A → se atribuye a A y no a B.** Es el guard central |
| H-02 | Firma dentro de bloque citado `> ` → se lee, y se marca `procedencia=citado` |
| H-03 | Las dos plantillas; `+34`, espacios y asteriscos limpiados; `/ Ext.` cortado |
| H-04 | Plantilla sin móvil → `FIRMA_SIN_CAMPO`, y el informe **no** dice «no tiene móvil» |
| H-06 | El cargo se extrae y **no** aparece en ningún payload al CRM |
| D1 | Property `nif_cif` en la búsqueda del colaborador |
| D2 | `movil:` vacío en el YAML → `""`, no `"None"` |
| Pieza C | Espejo de los del contrario, incluido **«lo que el CRM ya tiene no se pisa»** |
| Pieza C | Conflicto → no se propone nada |

**Pruebas de mutación** — una por frontera del contrato, no una por función
(`feedback-mutacion-vale-por-su-mutante`):

1. Quitar el anclaje por email-en-bloque y atribuir por `From:` → el test de H-02 debe ponerse rojo.
2. Quitar la corroboración obligatoria → el test de «dirección suelta» debe ponerse rojo.
3. Volver `_PROP_NIF` a `"nif"` → el test de D1 debe ponerse rojo.
4. Cambiar «sólo si está vacío» por «siempre» → el test de «no se pisa» debe ponerse rojo.
5. Colapsar `FIRMA_SIN_CAMPO` en «sin dato» → el test de H-04 debe ponerse rojo.

Si un mutante **no** muerde, se sospecha del test antes que del mutante.

**Aislamiento del CRM y de Gmail:** todos los tests nuevos cortan `httpx` con la guarda derivada de
**`BaseException`** del patrón de `tests/test_crm_ficha_cli.py`. Un `AssertionError` lo atragantaría
el `except Exception` de la pieza C —que por diseño no lanza— y la guarda quedaría **inerte**
mientras la escritura sale al tenant real.

**Suite:** dos semillas (`--randomly-seed=777` y `31337`), intérprete
`C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`, `--basetemp=C:/t/<corto>`.

## 9. Deuda declarada (lo que este diseño NO cubre)

- **El punto 3 del encargo** (documento de identidad y domicilio desde los contratos del Drive):
  fuera, esperando decisión de Nikolai. §2.
- **El cargo no llega al CRM.** Decisión de Nikolai del 2026-09-04, y el CRM no tiene dónde
  ponerlo (H-06). Si algún día existe un campo, la pieza A ya lo extrae.
- **El alta sigue siendo manual.** §4: no es un hueco de implementación, es que el corpus no
  contiene la respuesta.
- **`contrario.movil` sigue con el defecto D2.** Se cierra en el mismo sitio y de paso, pero se
  anota aquí para que no se lea como cerrado por casualidad.
- **`scripts/crm_ficha.py` es extrajudicial-only** (`[APER-49]`). La pieza C sirve a las dos
  jurisdicciones por §5.3(b), pero el CLI que la dispara sólo cubre extrajudicial. El hueco es
  previo a este trabajo y no se cierra aquí.
