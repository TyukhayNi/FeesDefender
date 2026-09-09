---
tipo: revision-adversarial
objeto: docs/INTEGRACION_SUDESPACHO.md §17 (+ PLAN.md fila 24 y su bloque)
objeto_rev: "1"
commit: 7e5e4ce
ronda: "2"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: zqvp
sha256_informe: 61028947c11dfb8d052ae7c575eb07234748944a5405b4f980b2dbb7ddfa013b
adjudicado_en: docs/superpowers/specs/2026-09-09-poderes-crm-subida-r2-adversarial-review.md §3
---

# Acta de la R2 — el flujo de subida al gestor documental

Segunda ronda de la misma tarea, sobre una **pieza distinta**: la R1 revisó la §16 (el elemento
`poderes`) y esta revisa la §17 (subir un documento). No es una tercera pasada sobre lo mismo, así
que no consume el techo de rondas.

La adjudicación va en el §3 de aquí por la misma razón que en la R1: el objeto no es un spec ni un
plan, y meterla en un documento de referencia operativa sería ruido para su lector. Los remedios sí
viven en los ficheros que la decisión modificó, y el §3 dice cuál en cuál.

---

## 0. Mandato entregado al revisor (literal)

<!-- mandato-literal:inicio:zqvp -->
# MANDATO — revisión adversarial R2: el flujo de subida al gestor documental (§17)

Eres el revisor. Ataca este diff; no lo apruebes. El autor (Claude) adjudicará cada hallazgo contra
la fuente. No tienes la última palabra, pero tampoco tienes que suavizar nada.

## Higiene

Tu workdir debe contener **solo este `MANDATO.md`**. Si hay otro fichero, **no lo leas** y decláralo
en la primera línea del informe. Mira las marcas de tiempo: un fichero más antiguo que este mandato
no puede ser respuesta a este mandato.

## Objeto

Dos copias del repositorio, hermanas de tu workdir. No hay `.git`.

- `../base/` — el árbol **antes** (commit `c376eb8`)
- `../head/` — el árbol **después** (commit `7e5e4ce`)

El diff son dos ficheros, ninguna línea de código:

- `docs/INTEGRACION_SUDESPACHO.md` — sección **§17** nueva (130 líneas): el flujo de subida de un
  documento al gestor documental del CRM, en tres pasos.
- `PLAN.md` — se actualizan la fila 24 y su bloque `[SIGUIENTE-ALTA-PODER]`, porque declaraban como
  hueco sin medir justo lo que la §17 cierra; y se rehace el apartado de deuda.

Sácalo con `diff -u ../base/<f> ../head/<f>`.

## Contexto que necesitas

Este diff es la **continuación** de otro que ya pasó tu revisión R1 (veredicto NO-SHIP, 7 hallazgos,
7 confirmados, 0 refutados). Esa R1 revisó la **§16** y no cubre la §17. El acta está en
`../head/docs/superpowers/specs/2026-09-08-poderes-crm-contrato-r1-adversarial-review.md`; **puedes
leerla**, y de hecho conviene: tres de sus siete hallazgos (H2, H4, H5) eran de la misma clase
—afirmaciones que otra parte del repo desmentía— y el §17 podría repetirla.

## Prohibiciones duras

1. **NO escribas nada en las copias.** Tu informe va a tu propio workdir.
2. **NO toques el CRM** (`api-crm-commons-pro.sudespacho.biz`, `tnm.sudespacho.net`), ni para leer.
   Ahí hay datos reales de clientes y una escritura accidental es irreversible. Si un hallazgo solo
   se decide llamando a la API, **dilo como «sin verificar»**: es una respuesta válida.
3. No pidas permisos ni esperes interacción. Lo que no se pueda comprobar, se declara.

## Qué atacar, en orden de importancia

### 1. ¿Repite el §17 la clase de defecto que la R1 castigó tres veces?

Es lo que más me preocupa. Busca **afirmaciones del §17 que otra parte del repo desmienta**, y
también lo contrario: **sitios del repo que la §17 deja mintiendo**. En concreto:

- el §14.6 dice que el HAR es inevitable «cuando el flujo son varias llamadas encadenadas con ids
  intermedios (subida de PDF en 3 pasos)». El §17.6 sostiene que **no hizo falta**. ¿Se ha corregido
  el §14.6, o queda contradiciendo al §17? ¿Debería corregirse, o son compatibles?
- el §16.3 dice del `DELETE /api/relation_element/{element}/{id}` que está «declarado pero **sin
  validar**». El §17.5 dice que **queda validado**. ¿Sigue el §16.3 diciendo lo viejo?
- el §5.1, §3.1, §0.4 y `docs/INDICE.md` se corrigieron en la R1 por prometer de más. ¿Hay ahora
  algún sitio equivalente que la §17 deje desfasado — `§8`, `DEAD_ENDS.md`, `MEJORAS_FUTURAS.md`,
  `docs/ARQUITECTURA*.md`, o el propio §16.7?
- comprueba **una por una** las referencias cruzadas que la §17 hace: `§14.5`, `§14.6`, `§16.2`,
  `§16.3`, `§16.7`, `§16.8`, `§17.1`, `§17.2`, `§17.4`. ¿Dicen lo que la §17 afirma que dicen?

### 2. ¿Es ejecutable el flujo tal como está escrito?

Alguien lo va a seguir para escribir en el CRM de un cliente. Léelo como implementador:

- ¿falta algún paso, cabecera, tipo o valor para que el `POST /api/documents` funcione a la primera?
- el §17.4 dice que lo recién escrito se verifica con `related_register` y el censo con el listado
  filtrado. ¿Es una regla aplicable sin ambigüedad, o hay casos que no cubre?
- el §17.5 dice que retirar un documento exige **dos** borrados «y en este orden». ¿Está justificado
  el orden, o es una afirmación sin apoyo?
- ¿hay algún paso cuya ejecución literal pueda **perder o corromper** un dato de cliente?
- el §17.6 da un método (leer los `assets/*.js` del front). ¿Es reproducible como está escrito?
  ¿Advierte de lo que caduca?

### 3. Lo que el diff afirma del repo — esto SÍ lo puedes verificar

Sin salir de las copias:

- que la §16 existe y que la §17 se apoya en ella sin duplicarla («un hecho, un hogar»: la regla está
  en `docs/GOBERNANZA_FUENTES_VERDAD.md`);
- que `PLAN.md` ya no declara la subida como hueco, y que su fila 24 y su bloque son coherentes
  **entre sí** y con la §17;
- que el ancla del enlace de la fila 24 sigue resolviendo a su encabezado;
- corre `../head/tests/test_docs_gobernanza.py` y dime si pasa. Tienes Python en
  `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe` con `pytest`,
  `pytest-randomly`, `pytest-xdist` y `pyyaml`. Si algún guard falla, es un hallazgo.

### 4. Datos personales

El proyecto prohíbe nombres, correos, direcciones y NIF/CIF/NIE de terceros en `docs/`, bitácora y
commits. Barre el diff. Ojo: `EV MMC` y `EV SPAIN` (el cliente del despacho) están nombrados en la
documentación del proyecto a propósito; y el correo `nikolai.tyukhay@engelvoelkers.com` que aparece
en `PLAN.md` **es preexistente**, no lo introduce este diff — compruébalo contra `../base/`.

## Lo que NO es un hallazgo

- Estilo, tono, longitud o densidad.
- Que la pieza de código de la fila 24 no esté construida: el bloque dice que está pendiente.
- Que una medición contra el CRM no se pueda re-verificar sin credenciales: eso se declara «sin
  verificar», no se convierte en crítica.
- Que el `DELETE` sin cuerpo no se haya probado: está declarado como no probado a propósito.

## Formato del informe

`INFORME.md` en tu workdir, en castellano:

1. **Primera línea:** si tu workdir tenía algún fichero además de este mandato.
2. **`sha256` de `../base` y `../head` al abrir y al cerrar**, como prueba de no mutación (hash de un
   recorrido ordenado de ficheros).
3. **Un bloque por hallazgo:** `ID`, **severidad** (`CRÍTICO`/`ALTO`/`MEDIO`/`BAJO`), fichero y línea,
   qué afirma el diff, por qué es falso o peligroso, **cómo lo comprobaste** (comando y salida), y
   remedio propuesto.
4. **Los comandos ejecutados con su salida** para los puntos 3 de arriba.
5. **Lo que no has podido verificar**, explícito.
6. **Última línea, exactamente uno de estos y nada más:** `VEREDICTO: SHIP` o `VEREDICTO: NO-SHIP`.

Si no hay nada de severidad `MEDIO` o superior, dilo y pon `SHIP`. Un informe honesto con cero
hallazgos altos es un resultado válido; inflar la severidad para justificar la ronda, no.
<!-- mandato-literal:fin:zqvp -->

---

## 1. Informe recibido de Codex, sin modificar

`sha256` del texto canonicalizado (UTF-8, LF, un solo salto final): `61028947c11dfb8d052ae7c575eb07234748944a5405b4f980b2dbb7ddfa013b`

Calculado al recibirlo. El revisor no declara digest propio, así que la cadena se verifica contra sí
misma y contra el fichero conservado fuera del repo; **no hay prueba independiente de origen** más
allá de eso. G8 recomputa este digest sobre el bloque de abajo.

<!-- informe-literal:inicio:zqvp -->
Higiene inicial: el workdir contenía únicamente `MANDATO.md`; no había ningún otro fichero ni directorio.

# Revisión adversarial R2 — flujo de subida al gestor documental (§17)

Revisor: Codex. Ejecución: 2026-09-09, fecha comprobada en el sistema. Objeto: las copias `../base` (identificada por el mandato como `c376eb8`) y `../head` (`7e5e4ce`), sin `.git`. Las líneas se refieren a `head`, salvo indicación contraria. La adjudicación corresponde a Claude contra la fuente.

**Resultado: cinco hallazgos MEDIOS y uno BAJO; ninguno ALTO ni CRÍTICO.** Se repite la clase de contradicción documental de R1. No ha fallado ningún guard de gobernanza. No se ha accedido al CRM ni a ningún servicio externo.

## Custodia y alcance efectivo

La primera operación enumeró el directorio antes de leer el mandato:

```powershell
Get-ChildItem -Force | Select-Object Name, Mode, Length, CreationTimeUtc, LastWriteTimeUtc
```

```text
Name        Mode  Length CreationTimeUtc      LastWriteTimeUtc
MANDATO.md  -a--- 6657   09/09/2026 10:31:52  09/09/2026 10:31:52
```

No había una respuesta anterior que pudiera confundirse con la de esta ronda. Los scripts, logs, copia de pruebas e informe de este workdir se crearon después. Se leyeron las instrucciones del proyecto y las skills de uso de skills y verificación; no se ejecutaron sus comandos de apertura que llaman al CRM, incompatibles con el mandato.

**Método exacto de SHA-256 del árbol:** recorrer todos los ficheros, incluidos los ocultos; ordenar por ruta relativa POSIX, lexicográficamente en Python; formar por fichero `sha256(bytes).hexdigest() + "  " + ruta_relativa + "\n"`; concatenar y calcular SHA-256 de esos bytes UTF-8. No se excluye ningún fichero. El hash comprueba rutas y contenido; no incluye timestamps, ACL ni directorios vacíos.

| Árbol | Ficheros abrir/cerrar | SHA-256 al abrir | SHA-256 al cerrar |
|---|---:|---|---|
| `../base` | 1245 / 1245 | `bf14c2e898ff83b1695419a1f743f16ba2ac383f5916319c8509507ef930066b` | `bf14c2e898ff83b1695419a1f743f16ba2ac383f5916319c8509507ef930066b` |
| `../head` | 1245 / 1245 | `22f19bcc9b67132e502e2bb4cc960951b0c6d7f375407a4f6a9d890f82ef8115` | `22f19bcc9b67132e502e2bb4cc960951b0c6d7f375407a4f6a9d890f82ef8115` |

Apertura: `2026-09-09T10:33:04.568514+00:00`. Cierre de lectura/pruebas del objeto: `2026-09-09T10:38:15.670080+00:00`. Manifiestos completos: `hashes-open.json` y `hashes-close.json`. **Ambas copias quedaron intactas.** La copia adicional `work/test_head`, usada para completar los tests con Git, conservó los mismos 1245 ficheros byte a byte, excluyendo exclusivamente su nuevo `.git`.

El contraste de manifiestos encontró exactamente dos ficheros distintos. El diff real es **+130/-0** en `INTEGRACION_SUDESPACHO.md` y **+16/-6** en `PLAN.md`. A diferencia de lo que describe el encargo, **la fila 24 y el bloque anterior a la deuda no cambian**. La revisión se ancla a los bytes entregados, no a la descripción de cambios esperados.

## 1. Contradicciones con el repositorio y referencias

### H-01 — MEDIO — PLAN sigue ordenando descubrir la subida que §17 declara resuelta

**Fichero y líneas:** `PLAN.md:41`, `3101–3104`; afirmación nueva en `docs/INTEGRACION_SUDESPACHO.md:2114–2125`.

**Qué afirma el diff:** §17 cierra la subida y documenta los tres pasos como verificados. Sin embargo, su puerta de entrada en la cola sigue diciendo «Único hueco sin contrato: la subida del PDF», y el paso 5 sigue ordenando «hay que capturarla o sondearla antes». No hay enlace a §17 desde esa fila ni desde ese paso.

**Por qué es falso o peligroso:** el hogar de planificación conserva una dependencia que la nueva referencia declara satisfecha. Quien trabaje desde la cola repetirá descubrimiento y posibles sondeos ya realizados. No es que falte construir la pieza, que correctamente sigue pendiente: falta actualizar el estado del conocimiento necesario para construirla. Fila y paso coinciden entre sí en la afirmación desfasada.

**Comprobación:** `& $py -B verify_repo.py` y `& $py -B audit_read.py lines ../head/PLAN.md 3096 3104`:

```text
PLAN_ROW24_UNCHANGED: True
PLAN_BLOCK_BEFORE_DEBT_UNCHANGED: True
3103:    (§16.7 — el renombrado preserva `nombreoriginal`). La subida en 3 pasos es la única parte del
3104:    flujo **sin contrato medido todavía**: hay que capturarla o sondearla antes.
```

El `diff -u` de PLAN contiene un único hunk, `@@ -3133,9 +3133,19 @@`, referido a la deuda.

**Remedio:** actualizar fila 24 y paso 5 a «contrato de subida en §17; integración pendiente», con enlace. Mantener la implementación pendiente y las dos rondas ya previstas para esa futura pieza.

### H-02 — MEDIO — El borrado tiene simultáneamente tres estados incompatibles

**Fichero y líneas:** nuevo `docs/INTEGRACION_SUDESPACHO.md:2208–2211`; fuentes desfasadas en el mismo fichero `1992–1997`, `docs/DEAD_ENDS.md:32–35`, `PLAN.md:41`, `3099`, `3128–3129`.

**Qué afirma el diff:** «Queda validado» el DELETE con cuerpo para quitar una relación `right.gdocu`, preservando las otras. Presenta §16.3 en pasado: «lo daba por declarado y sin probar».

**Por qué es falso o peligroso:** §16.3 todavía lo da por no validado y pide que la validación futura se escriba **allí**; DEAD_ENDS repite ese estado y remite a §16.3. PLAN incluso alterna «no hay endpoint» con «declarado pero sin validar». El añadido no reconcilia el contrato de recuperación. La inexistencia ya era falsa en `base`; lo imputable a R2 es dejarla vigente y añadir un tercer estado sin actualizar los puntos de consulta. La medición nueva tampoco autoriza a extender el resultado a todos los elementos, lados o cuerpos.

**Comprobación:** lectura numerada mediante `audit_read.py lines` de `../head/docs/INTEGRACION_SUDESPACHO.md 1992 1997`, `2208 2213`, `../head/docs/DEAD_ENDS.md 32 35` y `../head/PLAN.md 3096 3104`, `3125 3129`:

```text
INTEGRACION:1993: declarado** —en la tabla del §15.5 y en el atlas— pero **nadie lo ha validado** en este tenant, y con
INTEGRACION:1996: se quiere, no sobre uno cualquiera. Si alguien valida el DELETE, que lo mida por lectura y lo escriba
INTEGRACION:1997: aquí.
INTEGRACION:2209:   `"Deleted!"`. **Queda validado** (el §16.3 lo daba por declarado y sin probar): quita **solo** la
DEAD_ENDS:33:   `DELETE /api/relation_element/{element}/{id}` **declarado** (§15.5 y el atlas) pero **sin validar**
PLAN:3099:    (`DEAD_ENDS.md`), y **no hay endpoint para borrar un vínculo**, así que cada uno se verifica con
PLAN:3129: vínculo está declarado pero **sin validar** (ver más abajo), así que la reversión no está garantizada.
```

**Remedio:** fijar un único hogar del alcance validado, fechado y con el cuerpo concreto, y sustituir las otras afirmaciones por punteros. Conservar expresamente «sin cuerpo, no probado» y no prometer reversión genérica de vínculos de poderdante/procurador a partir de una prueba de `gdocu`.

### H-03 — MEDIO — La regla vigente sigue haciendo inevitable el HAR en el caso que §17 resuelve sin HAR

**Fichero y líneas:** `docs/INTEGRACION_SUDESPACHO.md:2220–2222`; regla que permanece en `1885–1887` (§14.6).

**Qué afirma el diff:** el HAR no fue necesario y leer los módulos del front es una vía reutilizable para este flujo de tres pasos.

**Por qué es incompatible:** §14.6 sigue formulando una regla general presente —«El HAR sigue siendo inevitable»— y cita exactamente «subida de PDF en 3 pasos». No está rotulada como descripción histórica superada ni contiene la excepción nueva. Que §17 reconozca la contradicción no modifica la instrucción en el hogar del método. Serían compatibles si §14.6 dijera cuándo el HAR pasa a ser necesario después de agotar la lectura del cliente; hoy no lo dice.

**Comprobación:** `& $py -B audit_read.py lines ../head/docs/INTEGRACION_SUDESPACHO.md 1885 1887` y `... 2220 2222`:

```text
1885: **El HAR sigue siendo inevitable** cuando el error es opaco, cuando el flujo son varias llamadas
1886: encadenadas con ids intermedios (subida de PDF en 3 pasos, §8.x) o cuando el endpoint no está en el spec
1887: (los 62 paths huérfanos que el propio atlas lista).
2220: El §14.6 dice que el HAR es inevitable «cuando el flujo son varias llamadas encadenadas con ids
2221: intermedios (subida de PDF en 3 pasos)». **Esta vez no hizo falta**, y la vía es reutilizable: la SPA
```

**Remedio:** corregir §14.6 para incluir la lectura de assets como fuente de candidatos, enlazar §17.6 y reservar el HAR para lo que esa lectura no resuelva. Mantener la verificación por resultado: leer código cliente no garantiza que cualquier rama de ese código siga funcionando contra el servidor.

### H-04 — BAJO — La referencia que pretende justificar la carpeta raíz no contiene ese hecho

**Fichero y línea:** `docs/INTEGRACION_SUDESPACHO.md:2149`, destino §16.2 (`1923–1965`).

**Qué afirma el diff:** «`1` es la raíz del árbol de `gdocu` (§16.2)».

**Por qué no está respaldado por la cita:** §16.2 documenta que `poderes` no tiene `id_carpeta` y usa `folders/gdocu/1` como control positivo que devuelve cuatro carpetas. No identifica explícitamente `id_carpeta=1` como raíz del gestor. El hecho sí está en §13.5. No afirmo que el valor sea incorrecto: está mal dirigido el respaldo.

**Comprobación:** `& $py -B audit_read.py lines ../head/docs/INTEGRACION_SUDESPACHO.md 1943 1947` y búsqueda `audit_read.py search '1.*raíz|1.*raiz'` sobre ese fichero:

```text
1944: - **sin `id_carpeta`** → no admite carpetas. `GET /api/folders/poderes/1` devuelve `[]`, y el
1945:   instrumento sí sabe devolver datos (control positivo: `folders/gdocu/1` → 4 carpetas,
1264: | `"1"` | `General` | `99_Otros` | Raíz del gestor documental — escritos genéricos. Confirmado 2026-05-08. |
2149:   `1` es la raíz del árbol de `gdocu` (§16.2).
```

**Remedio:** apuntar a §13.5 para el significado y conservar en §17.1 la exigencia nueva de enviarlo como entero. No duplicar la tabla.

### Referencias cruzadas: comprobación una por una

| Referencia pedida | Resultado contra el destino real |
|---|---|
| §14.5 | Existe, línea 1710. Las líneas 1732–1734 dicen que el HAR acredita qué hace la UI, no todo lo que permite la API. §17.6 reproduce esa lección, pero su «simétrica» no se deduce de ella: el código del cliente muestra peticiones candidatas; la aceptación y los efectos se contrastan por resultado. |
| §14.6 | Existe, línea 1850. La cita sobre inevitabilidad es literal y permanece vigente: H-03. También exige sujeto sacrificable y verificación por resultado. |
| §16.2 | Existe, línea 1923. No sostiene la identificación de la raíz: H-04. Sí enumera `gdocu` como hijo de `poderes`. |
| §16.3 | Existe, línea 1967. Respalda la gramática con puntos y el sentido del lado. Incluye una salvedad necesaria si el relacionado aparece en ambos lados. §17 remite a esa regla sin contradecir su caso concreto documento→poder. Su estado del DELETE sigue viejo: H-02. |
| §16.7 | Existe, línea 2053. Contiene renombrado por PUT, preservación de `nombreoriginal` y descarga por `downloadUri`. No contiene subida: es compatible que §17 complete ese recorrido. No declara literalmente un «único hueco»; esa formulación estaba en PLAN. Le falta un puntero de continuación a §17, sin constituir por sí solo otro hallazgo. |
| §16.8 | Existe, línea 2071. Contiene la convención de nombres/campos y el nombre de PDF en 2108–2110. **No hay cita a §16.8 dentro de §17 en los bytes entregados.** Se contrastó igualmente con el nombre solicitado en PLAN. |
| §17.1 | Existe, línea 2120. §17.2 sí remite al objeto JSON allí mostrado. La referencia resuelve; no prueba por sí sola el resultado de la operación múltiple. |
| §17.2 | Existe, línea 2153. **No es destino de una referencia `§17.2` dentro de §17.** Se examinó su prueba declarada: seis intentos y lectura por `origen_id`, sin ventana temporal registrada. Resultado real: sin verificar por esta revisión. |
| §17.4 | Existe, línea 2183. **No es destino de una referencia `§17.4` dentro de §17.** Se examinó como regla operativa: H-05. |

El inventario automático encuentra exactamente `§14.5`, `§14.6`, `§16.2`, `§16.3`, `§16.7` y `§17.1` en §17. No atribuyo al texto las otras tres referencias que anticipa el mandato.

**Barrido de otros hogares:** §8.9 habla de `element_register` y de `relatedElement`/`relatedId`; §17 habla de `documents` y `relatedRegisters`. Son contratos distintos y no hay contradicción en que el segundo enlace durante la creación. §0.4, la introducción de §3.1 y la fila del atlas en INDICE conservan la acotación de cobertura de R1. §5.1 conserva la receta antigua pero también el aviso explícito de obsolescencia y el flujo vivo añadido en R1; §16.7 advierte de ello. No imputo otra vez ese defecto como introducido en R2.

Se revisaron `DEAD_ENDS.md`, `MEJORAS_FUTURAS.md`, `ARQUITECTURA.md`, `ARQUITECTURA_RELACIONES.md`, `ARQUITECTURA_CRM_SUDESPACHO.md`, INDICE y las coincidencias de subida en el corpus documental. La discrepancia vigente sobre DELETE es H-02. La subida a `00_Input/05_CRM` de ARQUITECTURA es intake local; «subida carpeta→CRM no construida» en `PLAN.md:1029–1031` describe código pendiente y sigue siendo compatible con tener contrato. No encontré en esos otros hogares una nueva negación operativa equivalente que merezca otro MEDIO.

Hay además un residuo en `docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md:33`: «No hay endpoint REST de upload», dentro de una decisión fechada el 2026-05-12, en un plan que aún lleva `estado: vigente`. Conviene señalar allí el descubrimiento posterior con un enlace; no cuento como otro MEDIO la decisión histórica de hacer manual aquella entrega. No propongo reescribir actas ni bitácora retrospectivamente.

## 2. Ejecutabilidad y riesgo del flujo

### H-05 — MEDIO — La regla del censo no define una ausencia fiable y permite repetir el duplicado que relata

**Fichero y líneas:** `docs/INTEGRACION_SUDESPACHO.md:2189–2200`, especialmente `2192–2193`.

**Qué afirma el diff:** lo recién escrito se verifica con `related_register`; el «censo de lo que hay de verdad» se obtiene del listado filtrado. El mismo apartado explica que el listado tiene latencia y que una guarda anti-duplicado basada en él ya duplicó un certificado.

**Por qué la regla no basta:** una operación posterior que quiera subir un certificado necesita censar lo existente **antes** de escribir. Si la creación anterior aún no aparece en el índice, el censo recomendado devuelve vacío y reproduce el fallo descrito. El apartado no fija una condición de convergencia, una salida «sin verificar» ni prohíbe interpretar ese vacío como autorización de otra alta. Cambiar sin más al otro endpoint tampoco resuelve el caso: el propio texto dice que conserva fantasmas. La distinción «recién escrito/censo» no decide qué hacer cuando coinciden ambas situaciones.

Este contraejemplo usa exclusivamente las propiedades que afirma el documento; **no es una reproducción del servidor** ni una afirmación de que se haya producido otro duplicado durante esta revisión.

**Comprobación:** `& $py -B audit_read.py lines ../head/docs/INTEGRACION_SUDESPACHO.md 2183 2201`:

```text
2189: | `GET /api/element_registries/gdocu?…associated&property=left.poderes.id&value={id}` | **segundos** (índice) | no los muestra |
2190: | `GET /api/related_register/poderes/{id}` | **inmediata** | **sí**: sigue listando documentos ya borrados |
2192: **Regla operativa: lo que acabas de escribir se comprueba con `related_register`; el censo de lo que
2193: hay de verdad se hace con el listado filtrado.** Usar la vía equivocada tiene un coste medido, y las
2199: - y una guarda anti-duplicado que consultaba el **listado** dio «este poder aún no tiene su
2200:   certificado» sobre uno que ya lo tenía, y **lo subió dos veces**. El duplicado se detectó por
```

**Remedio:** delimitar la regla: verificar el alta por el `doc_id` devuelto y el elemento esperado; no tomar un censo negativo posiblemente retrasado como permiso para reintentar. Documentar cómo reconciliar candidatos de relaciones con existencia/binario y qué resultado deja el flujo detenido como «sin verificar». Si se usan relecturas, acotarlas y no convertir el agotamiento del plazo en «no existe». No hace falta construir esa guarda ahora: sí dejar de llamar al listado un censo verdadero sin esa condición.

**Paso 3 y cabeceras.** El JSON proporciona los campos, `origen_id`, valores de Select, `id_carpeta` entero y la gramática de relación. §2.1 proporciona `x-api-key`; §3.1 ya contiene ejemplos de JSON y §14.2 la regla de `Accept: application/json`. No hay fuente local que permita afirmar que falta un campo obligatorio concreto. Para que la receta sea autocontenida conviene referenciar esas cabeceras, indicar `Content-Type: application/json` en el POST, `tamano` como número real de bytes y sustituir el id de ejemplo por el poder resuelto. El MIME debe corresponder a los bytes. No presento esas aclaraciones como prueba de un fallo del POST: no se ha llamado a la API.

**Verificación de bytes.** §17 abre diciendo que los bytes volvieron idénticos; §16.7 sí permite obtener la URL para descargarlos. Comprobar que existe una relación, incluso por id, no acredita esa igualdad. La implementación deberá comprobarla si pretende dar esa garantía. Ni un `201` ni el mero ETag sustituyen la comparación del binario. El query con `…associated` de §17.4 es una abreviatura: la sintaxis completa y sus dos `condition` están en §3.1/§5.1 y la paginación/serialización en §14.2; no debe ejecutarse la abreviatura como URL literal.

**Dos borrados y su orden.** Quitar primero la relación es una recomendación razonable para evitar crear el huérfano descrito. Pero el texto no acredita que sea el **único orden posible**: su propio relato describe borrar un documento y después una relación huérfana. No consta una prueba comparativa de órdenes ni de fallos intermedios. Lo clasifico como alcance no demostrado, sin elevarlo a otro MEDIO: explicitar «orden recomendado para evitar huérfanos», verificar la retirada de la relación y después la del documento haría precisa la receta. «Retirar un documento del todo» es borrado global del documento, distinto de desvincularlo de un solo poder; la autorización y los otros vínculos deben estar resueltos antes. No he encontrado una instrucción inequívoca de borrar un documento ajeno ni una pérdida demostrada en este diff. No se ha probado DELETE sin cuerpo y **no se exige probarlo**.

**Método de assets.** Da un procedimiento reconocible —localizar peticiones, leer módulos del uploader y cliente HTTP— y advierte expresamente que el hash cambia con cada despliegue. No promete una URL fija reproducible mañana. Faltan en las copias los bundles concretos y no se identifica una ruta de pantalla que garantice cargar un módulo diferido; sus nombres, longitud de 1.929 caracteres y disponibilidad pública quedan sin verificar. Leer cliente aporta claves y llamadas candidatas, no prueba de aceptación ni de totalidad del contrato del servidor. §17.2, al documentar un método múltiple del mismo cliente que no habría creado documentos, obliga a mantener ese límite.

## 3. Estado de PLAN, gobernanza y pruebas ejecutadas

### H-06 — MEDIO — La nueva deuda pierde los tres poderes sin poderdante sin darles disposición

**Fichero y líneas:** `PLAN.md:3136–3151`, que sustituye `base/PLAN.md:3136–3141`; contexto conservado en `head/PLAN.md:3092–3095`.

**Qué cambia el diff:** reemplaza la deuda anterior, que incluía «3 sin poderdante (`#82`, `#85`, `#86`)», por una lista que ya no registra esa carencia. El único cierre explícito nuevo se refiere a cinco certificados (`#72`, `#87`–`#90`). `#82` desaparece por completo de la deuda; `#85` y `#86` aparecen por otras cuestiones.

**Por qué es un defecto de planificación:** vigencia no verificada o ausencia de apoderamiento judicial no son una disposición del vínculo pendiente con el poderdante. No se dice que los tres vínculos se resolvieran, se descartaran o se transfirieran a otra tarea. El hogar de trabajo pendiente pierde así un problema de asociación de clientes. El propio paso 3 conserva que no debe crearse por efecto colateral el cliente ausente de `#85`. **No afirmo que hoy sigan sin vínculo en el CRM**; el hallazgo es que el diff retira el seguimiento sin registrar qué ocurrió.

**Comprobación:** diff de PLAN y `& $py -B verify_repo.py`:

```diff
-poder** y para el que el enum `Formato` no tiene valor—; 3 sin poderdante (`#82`, `#85`, `#86`); el
+- **cerrado:** los 5 apoderamientos que faltaban se localizaron en la sede y están dados de alta con
+  su certificado (`#72` completado, `#87`-`#90` nuevos). El fichero pasa de 85 a **89** registros.
```

```text
PLAN_DEBT_OLD_ORPHANS: True
PLAN_DEBT_NEW_ORPHAN_TERM: False
PLAN_DEBT_NEW_82: False
```

**Remedio:** conservar esa deuda o registrar su disposición, por cada uno de los tres ids, con la evidencia del autor. Si sigue pendiente para `#85`, explicitar la decisión necesaria sobre su ficha de cliente. No requiere que el revisor consulte ni modifique el CRM.

### Comandos y resultados de las comprobaciones exigidas

Todos los comandos parten de este workdir. Abreviatura usada en el informe:

```powershell
$py = 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
```

`rg` no estaba disponible en PATH. Se utilizó `audit_read.py`, un lector propio que numera líneas o recorre ficheros con `pathlib` y expresiones regulares. No escribe en las copias. Los fragmentos citados arriba se obtuvieron con él; `evidence-contract.txt`, `evidence-headings.txt`, `evidence-crossrepo.txt` y `evidence-upload-corpus.txt` conservan los barridos.

**Diff solicitado:** se ejecutó GNU diff, evitando el alias `diff` de PowerShell que corresponde a otro comando:

```powershell
& 'C:/Program Files/Git/usr/bin/diff.exe' -u ../base/docs/INTEGRACION_SUDESPACHO.md ../head/docs/INTEGRACION_SUDESPACHO.md
& 'C:/Program Files/Git/usr/bin/diff.exe' -u ../base/PLAN.md ../head/PLAN.md
```

Salidas completas conservadas en `diff-integracion.txt` y `diff-plan.txt`. Los hunks son `@@ -2108,3 +2108,133 @@` y `@@ -3133,9 +3133,19 @@`. Exit 1 de diff significa que hay diferencias. No hay cambios de código.

**Existencia, dependencia, ancla y coherencia de PLAN:**

```powershell
& $py -B verify_repo.py
```

Salida relevante, completa en `checks-repo.txt`:

```text
SECTION_16_EXISTS: True
SECTION_17_ONLY_APPEND: True ADDED_LINES: 130
SECTION_17_REFERENCES: ['§14.5', '§14.6', '§16.2', '§16.3', '§16.7', '§17.1']
REFERENCE_TARGET 14.5 line=1710 CITED_BY_17=True
REFERENCE_TARGET 14.6 line=1850 CITED_BY_17=True
REFERENCE_TARGET 16.2 line=1923 CITED_BY_17=True
REFERENCE_TARGET 16.3 line=1967 CITED_BY_17=True
REFERENCE_TARGET 16.7 line=2053 CITED_BY_17=True
REFERENCE_TARGET 16.8 line=2071 CITED_BY_17=False
REFERENCE_TARGET 17.1 line=2120 CITED_BY_17=True
REFERENCE_TARGET 17.2 line=2153 CITED_BY_17=False
REFERENCE_TARGET 17.4 line=2183 CITED_BY_17=False
PLAN_ROW24_UNCHANGED: True
PLAN_BLOCK_BEFORE_DEBT_UNCHANGED: True
ROW24_LINK: siguiente-alta-poder-alta-canónica-de-un-poder-en-el-crm-desde-el-pdf-con-su-procurador-enganchado
HEADING_SLUG: siguiente-alta-poder-alta-canónica-de-un-poder-en-el-crm-desde-el-pdf-con-su-procurador-enganchado
ANCHOR_MATCH: True
DIFF PLAN.md + 16 - 6
DIFF docs/INTEGRACION_SUDESPACHO.md + 130 - 0
GOVERNANCE_RULE: **Cada hecho tiene un único hogar. Todo lo demás enlaza, no copia.**
```

El ancla se calculó del encabezado `PLAN.md:3058` con la regla indicada en R1: minúsculas, eliminación de corchetes y coma, espacios a guiones. **Resuelve.** §17 no copia el esquema completo de poderes, su convención ni las recetas de renombrado/descarga; añade un contrato distinto. El problema de hogar único se concreta en los estados contradictorios de H-01/H-02/H-03, no en la mera existencia de otra sección ni en comparar las dos gramáticas.

**Guard solicitado, directamente sobre `../head`:**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:CASOS_ROOT=Join-Path (Get-Location) 'test-casos'
& $py -B -m pytest ../head/tests/test_docs_gobernanza.py -p no:cacheprovider --basetemp=./pytest-direct-777 --randomly-seed=777 -q --tb=short
```

```text
..............................................                           [100%]
EXIT=0
```

**Limitación comprobada de ese verde:** dos recorridos del módulo utilizan `git grep`/`git ls-files` sin exigir exit 0. En una copia sin `.git` no miran su población real. Comprobación:

```text
git -C ../head ls-files *.md
EXIT: 128; STDOUT_LINES: 0
fatal: not a git repository (or any of the parent directories): .git
```

Para cerrar esa cobertura se hizo `shutil.copytree(Path('../head').resolve(), Path('test_head').resolve())`, con comparación SHA-256 fichero a fichero antes de inicializar Git. **Solo en esa copia propia**, se ejecutó:

```powershell
git -C ./test_head init --quiet
git -C ./test_head -c core.autocrlf=false add --all --force .
```

El primer `add` falló por `Filename too long` (exit 128). Se conservó el fallo; se corrigió la configuración de esa invocación:

```powershell
git -C ./test_head -c core.longpaths=true -c core.autocrlf=false add --all --force .
git -C ./test_head ls-files '*.md'
```

```text
COPY_BYTES_IDENTICAL: 1245 files
GIT_ADD_EXIT=0
TRACKED_MD=454
```

Una corrida intermedia acabó con `46 passed in 16.43s`, pero no se usa como evidencia de cobertura completa porque coincidió con la preparación del índice. Una vez terminado este, se ejecutaron las dos corridas finales:

```powershell
& $py -B -m pytest ./test_head/tests/test_docs_gobernanza.py -p no:cacheprovider --basetemp=./pytest-indexed-777 --randomly-seed=777 -o addopts= -q --tb=short
& $py -B -m pytest ./test_head/tests/test_docs_gobernanza.py -p no:cacheprovider --basetemp=./pytest-indexed-31337 --randomly-seed=31337 -o addopts= -q --tb=short
```

```text
..............................................                           [100%]
46 passed in 13.82s
EXIT=0
..............................................                           [100%]
46 passed in 17.73s
EXIT=0
```

Logs: `tests-direct.txt`, `tests-indexed-777.txt`, `tests-indexed-31337.txt`. **Ningún guard falló.** No se añadieron skips, no se modificaron asertos ni se sustituyó el corpus por fixtures. No se ejecutó toda la suite de producto.

**Comprobación final de integridad:** `& $py -B close_hash.py` produjo:

```text
base files=1245 sha256=bf14c2e898ff83b1695419a1f743f16ba2ac383f5916319c8509507ef930066b UNCHANGED=True
head files=1245 sha256=22f19bcc9b67132e502e2bb4cc960951b0c6d7f375407a4f6a9d890f82ef8115 UNCHANGED=True
UTC: 2026-09-09T10:38:15.670080+00:00
TEST_COPY_CONTENTS_UNCHANGED: True 1245
```

## 4. Datos personales

Se inspeccionaron las **146 líneas añadidas** completas y se ejecutó un barrido de correos, DNI, NIE, CIF, teléfono español y NIG de 17 dígitos sobre las adiciones, con `SequenceMatcher(autojunk=False)`. `verify_repo.py` dio:

```text
EMAIL base COUNT: 1 LINES: [1736]
EMAIL head COUNT: 1 LINES: [1736]
ADDED_PII_email: []
ADDED_PII_DNI: []
ADDED_PII_NIE: []
ADDED_PII_CIF: []
ADDED_PII_NIG: []
ADDED_PII_telefono: []
ADDED_LINES_REVIEWED: 146
```

El correo `nikolai.tyukhay@engelvoelkers.com` **es preexistente**, una ocurrencia en la misma línea de ambos PLAN. No lo introduce el diff. No encontré nombres de particulares, direcciones ni identificadores fiscales de terceros nuevos en las adiciones. `Nikolai` identifica al usuario del despacho; E&V al cliente expresamente admitido por el mandato. `EV MMC`/`EV SPAIN` en la convención final de §16 son contexto preexistente, no nuevas adiciones. Los ids de registros y el UUID de evento son identificadores técnicos, no nombres ni correos.

El barrido por formas y la lectura manual no prueban ausencia universal de PII. No se dispuso de la blocklist privada ni se inspeccionaron commits reales: se revisó el diff de las dos copias.

## 5. Sin verificar y límites explícitos

- **CRM/S3:** no hubo llamadas, navegación ni uso de credenciales. Quedan sin verificar por este revisor la aceptación efectiva del JSON, autenticación específica de estas escrituras, respuestas/errores, expiración de 600 segundos, los cinco certificados y su igualdad binaria, latencias reales y causa de indexación, alcance/preservación de DELETE y tratamiento físico del binario borrado. No convierto la prohibición de reproducir esas mediciones en hallazgo.
- **Operación múltiple:** el repo relata seis intentos sin creación y devuelve ids de evento, pero no contiene aquí una observación temporal suficiente para distinguir fallo definitivo, procesamiento diferido o falta de visibilidad del índice. No afirmo que el endpoint funcione ni refuto la medición del autor; su resultado queda sin verificar. La recomendación de usar el singular probado no depende de demostrar que el múltiple nunca funciona.
- **Fallos/reintentos:** no se verificaron timeout tras POST aceptado, idempotencia por `origen_id`, recuperación de un PUT S3 sin alta documental, reintentos de creación ni el orden inverso de borrados. H-05 se sostiene en la contradicción lógica entre la regla y el contraejemplo ya escritos, no en simular esas respuestas como si fueran del servidor.
- **Datos de la deuda:** no se consultó el registro judicial ni se verificaron el paso de 85 a 89, los ids dados de alta, los comparecientes, los registros ausentes ni la decisión sobre graduados sociales. H-06 se refiere a la desaparición documental de una deuda, no a declarar falso el saneado realizado.
- **Front:** no se descargaron assets. No se contrastaron su contenido, longitud, exposición pública, pantalla que los carga ni compatibilidad futura. La advertencia sobre cambio del hash sí existe.
- **Fuentes externas:** no se abrió el repo hermano de El Contable, los enlaces al proveedor ni los PDFs originales. No se emite valoración jurídica de poderes o de vigencia.
- **Identidad de commits:** al no haber `.git` en las entradas, las etiquetas `c376eb8`/`7e5e4ce` se toman del mandato. La identidad independiente comprobada es la de los manifiestos SHA-256 de las copias.
- **Cobertura:** pruebas documentales indicadas, contraste de fuentes y PII del diff; no pruebas de integración ni suite completa. Las instrucciones de reparación son propuestas para adjudicar. No se ha remediado ningún fichero revisado.

VEREDICTO: NO-SHIP
<!-- informe-literal:fin:zqvp -->

---

## 2. Evidencia verificada por mí al adjudicar

Cada hallazgo, comprobado contra la fuente del repo o contra el CRM, no contra el informe:

| Hallazgo | Qué comprobé | Cómo | Resultado |
|---|---|---|---|
| H-01 | si la fila 24 y el paso 5 de `PLAN.md` se habían actualizado | `git show HEAD:PLAN.md` + `git show HEAD -- PLAN.md \| grep -c '^@@'` → **1 hunk**, y el texto viejo intacto en la línea 41 | **CONFIRMADO.** Los dos cambios nunca llegaron al disco |
| H-02 | el estado del `DELETE` de relación en cada hogar | `grep` sobre `INTEGRACION_SUDESPACHO.md`, `DEAD_ENDS.md` y `PLAN.md` | **CONFIRMADO y ampliado**: yo había visto §16.3; el revisor encontró además `DEAD_ENDS:33`, `PLAN:3099` y `PLAN:3131` |
| H-03 | si §14.6 seguía declarando el HAR inevitable para este caso | `grep -n 'subida de PDF en 3 pasos'` → línea 1886, en presente y sin excepción | **CONFIRMADO.** Y su referencia `§8.x` no resuelve: el §8 no tiene subsecciones ni habla de subida |
| H-04 | si §16.2 define `id_carpeta=1` como raíz | leído §16.2 (solo la usa como control positivo) y §13.5:1264, que sí lo define | **CONFIRMADO**: respaldo mal dirigido, el valor es correcto |
| H-05 | si la regla del §17.4 impide repetir el duplicado que relata | leído el apartado entero | **CONFIRMADO**, y es el mejor hallazgo de la ronda: la regla separaba «verificar lo escrito» de «censar», pero el duplicado nació de un **censo previo a escribir**, y ahí la latencia también miente |
| H-06 | si `#82`, `#85` y `#86` siguen sin poderdante | `related_register` de los tres, leído del CRM el 2026-09-09 | **CONFIRMADO**: los tres siguen sin cliente vinculado, y yo retiré esa deuda sin decir qué pasaba con ella |

**Lo que el revisor midió y confirmo:** corrió `tests/test_docs_gobernanza.py` sobre `head` y **no
falla**; el `diff -u` de `PLAN.md` tiene un único hunk; y el correo de `PLAN.md` que el hook marca es
**preexistente**, lo comprobó contra `base`.

**Un residuo que encontró sin que se lo pidiera, y es real:**
`docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md:33` decía «No hay endpoint REST de upload» en un
plan con `estado: vigente`. Verificado y corregido.

**Lo que NO se verificó, y queda declarado:** el revisor no llamó al CRM (se lo prohibí), así que sus
observaciones sobre §17.2 —los seis intentos que devuelven 201 sin crear— quedan **sin verificar por
él**; la medición es mía, del 2026-09-09. Tampoco están en las copias los bundles del front que cita
el §17.6, así que sus nombres y su contenido quedan sin verificar por su parte.

**Sobre el objeto:** `base` y `head` mantuvieron el mismo `sha256` de recorrido ordenado al abrir y al
cerrar (`452e3fac…` y `0370d74c…`), así que el revisor no lo mutó. Declaró en su primera línea que su
workdir solo contenía el mandato.

---

## 3. Adjudicación de la revisión adversarial del flujo de subida (Codex, 2026-09-09) — NO-SHIP, remediado

- **Objeto revisado:** `docs/INTEGRACION_SUDESPACHO.md` §17 nueva, más la fila 24 y el bloque `[SIGUIENTE-ALTA-PODER]` de `PLAN.md` — commit `7e5e4ce`
- **Ronda:** 2 de la tarea, **1 de esta pieza** (la R1 revisó la §16, no la §17)
- **Revisor:** Codex (`codex-cli 0.153.4`, esfuerzo alto, dos copias externas de solo lectura, sin acceso al CRM)
- **Informe recibido:** §1 de esta acta, literal, `sha256` `61028947c11dfb8d052ae7c575eb07234748944a5405b4f980b2dbb7ddfa013b`
- **Hallazgos:** 6 — 0 CRÍTICO, 0 ALTO, 5 MEDIO, 1 BAJO. **6 confirmados, 0 refutados.**
- **Remediado en:** el commit siguiente. H-01 en `PLAN.md` (fila 24 y paso 5), H-02 en §16.3, `DEAD_ENDS.md` y dos sitios de `PLAN.md`, H-03 en §14.6, H-04 en §17.1, H-05 en §17.4, H-06 en la deuda del bloque; más cinco menores que el revisor anotó sin elevar y el residuo de `PLAN_SaRS1_anon_pipeline.md`

**Cero refutados otra vez, y el patrón se repite: cinco de los seis son el sitio viejo que queda
mintiendo.** La R1 me castigó eso tres veces (H2, H4, H5) y yo escribí en su acta que «el remedio no
es matizar la sección nueva: es arreglar el sitio que miente». Al día siguiente lo volví a hacer en
§14.6, §16.3, `DEAD_ENDS`, dos sitios de `PLAN` y un plan ajeno. **Saber nombrar el defecto no es
tenerlo resuelto**, y la única defensa que ha funcionado es la mecánica: antes de cerrar, `grep` de
la afirmación contraria por todo `docs/` y `PLAN.md`.

**H-01 es el hallazgo que más me corrige, y no por su contenido.** El texto que había que cambiar lo
tenía identificado; lo que falló fue **mi manera de comprobar que el cambio existía**. Mi script
acumulaba tres reemplazos en memoria y escribía al final; el `sys.exit()` del tercero abortó antes del
`write`, y los dos primeros —que ya habían impreso `OK`— nunca llegaron al disco. Leí ese `OK` y lo
di por hecho. Es **exactamente** «verificar por resultado, nunca por status», la regla que este mismo
diff documenta dos veces sobre el CRM, cometida en mi propia herramienta. El script de remediación de
esta ronda escribe tras **cada** reemplazo y relee el fichero para confirmarlo, y al cerrar comprobé
los trece cambios con `grep` sobre el árbol en vez de fiarme de su salida.

**H-05 es el mejor hallazgo de la ronda y es conceptual, no documental.** Mi regla decía: lo escrito
se verifica con `related_register`, el censo con el listado. Suena completa y no lo es: el duplicado
que yo mismo relato en ese apartado **nació de un censo previo a escribir**, y ahí el listado también
miente por latencia. La regla, tal como la dejé, autorizaba a repetir el fallo que describía. Ahora
tiene una tercera parte: **un censo negativo no prueba ausencia y no autoriza a escribir**; si el «no
existe» no se puede sostener contra algo inmediato, el flujo se detiene y se declara SIN VERIFICAR.

**H-02, H-03 y H-04 son precisión de referencias**, y las tres apuntan a lo mismo: escribí la sección
nueva como si el resto del documento se actualizara solo. H-02 añade además un límite que yo no había
puesto: mi prueba del `DELETE` fue sobre `right.gdocu` en un `poderes`, y **no autoriza** a prometer
reversión de los vínculos de poderdante o procurador. Eso queda escrito.

**H-06 es una pérdida de seguimiento, no un error de hecho.** Al rehacer la deuda del bloque retiré
«3 sin poderdante (`#82`, `#85`, `#86`)» sin registrar su disposición, y el `#82` desapareció del
documento. Los tres **siguen sin cliente vinculado**, comprobado hoy contra el CRM. Repuesto, con la
decisión que el `#85` necesita: su otorgante no existe entre los clientes propios.

**Lo que el revisor NO pidió:** ni otra ronda sobre este diff, ni construir la guarda del §17.4 ahora,
ni sondear el `DELETE` sin cuerpo, ni reescribir la bitácora retrospectivamente. Lo dice
explícitamente en H-05, en el barrido de hogares y en el cierre.
