---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-26-codicert-estados-medidos.md
objeto_rev: "1"
commit: eb8691a
ronda: "1"
revisor: Codex
veredicto: LISTA-CON-CAMBIOS
marcador_nonce: u7xz
sha256_informe: 7ce0423af02786832f37ec12d5d1dc971568c8e91ba911b8d668b586c53a1240
adjudicado_en: docs/superpowers/plans/2026-09-26-codicert-estados-medidos.md §6
---

# Acta — R1 adversarial sobre los estados medidos de F2 del envío certificado

Objeto: la pieza entera, `73ba288` → `eb8691a` —el 22 que cierra cuando ningún aviso llegó, el
canal sin clasificar que no se cosecha ni pone fechas, el motivo de lo no cosechable con el
estancado y la hora de la lectura obligatoria, los tres textos que lo dicen, sus tests, el plan y el
spec rev. 17—.

**Primera ronda sobre esta pieza, la única que le da la tabla de `CLAUDE.md`** (no decide quién
escribe sobre qué copia ni destruye datos). **No es una R4 de F3** ni cubre la remediación de la R3
de F3, y el mandato lo decía. Modelo de la fila «escritura sobre datos de cliente»,
`gpt-6-astra`·`medium`, por una frontera silenciosa y nombrada: si la regla del 22 cerrara de más,
`cosechar` archivaría como definitivo un certificado «sin entrega», la cosecha siguiente lo
saltaría (`ya_estaba`) y un acceso posterior del requerido no entraría nunca solo en el expediente.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), sondeado `VIVO` con el mismo modelo antes de montar el objeto |
| Modelo y esfuerzo | `gpt-6-astra` · `medium` — **releídos** de la cabecera del `_stdout.log` (sesión `01a0dcb6-5841-76b0-a2fc-e380acda8703`) |
| Velocidad | `service_tier="default"` — **afirmada** desde el lanzador conservado (`C:\t\codicert-estados-r1-0954-lanzador\_lanzar.ps1`) |
| Objeto | dos copias `git archive` (`base/` 1.421 ficheros, `head/` 1.423), dentro del workdir, sin `.git`; cotejadas contra el commit por `sha256` en LF |
| Duración | de 09:55:31 a 10:08:49; terminó con `exit=0` y ninguna línea de muerte en el log (vigía armado antes de lanzar) |
| `sha256` del informe | `7ce0423af02786832f37ec12d5d1dc971568c8e91ba911b8d668b586c53a1240` |
| Veredicto | **LISTA-CON-CAMBIOS** |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:u7xz -->
Higiene inicial conforme: únicamente MANDATO.md, base/, head/ y _stdout.log; no había elementos ajenos que excluir de lectura.

# R1 — estados medidos de F2

Objeto: `73ba288d17b656ef2d612839804e431683a7a987` → `eb8691ad560122611fd231284060a8e6f6d1be21`, según las identificaciones del mandato. Archivos recibidos mediante archive, sin genealogía verificable. Revisión de los ocho ficheros indicados, leyendo primero el plan de estados medidos y el spec rev. 17. No se reabre la revisión de la implementación de F3.

**Resultado:** la lógica central implementa D-1, D-2 bis y D-3 correctamente en los caminos normales de lectura. Hay una recomendación operativa que no funciona para un caso admitido y huecos concretos de cobertura. No he encontrado un cierre definitivo indebido en el código entregado. Los dos hallazgos son de severidad baja; ninguno acredita pérdida de datos ni adelanto de plazos en head.

## 1. La regla del 22

`_INDICIOS_DE_ENTREGA` contiene exactamente `{17, 19, 20, 21, 27}` (core, l. 1083). `cerrado_en` (1171–1184) examina el conjunto de códigos del histórico entero; cualquier indicio, anterior o posterior al 22, inhibe exclusivamente el cierre por 22. No inhibe 28/40/42. Si hay varios cierres válidos conserva la fecha más temprana, coherentemente con `_primera`.

`cosechable` (1192–1212) aplica primero las guardas de canal y códigos desconocidos. Después admite la culminación del canal o un cierre. Por tanto:

- `3 → 14 → 22` y `5 → 14 → 22` cierran y se cosechan.
- `22 → 17`, `27 → 22` o `21 → 22` no cierran por el 22.
- `20 → 22` sigue siendo cosechable en EEC por el 20; `19 → 22`, en burofax por el 19. Esto no contradice D-1: culminación y cierre sin entrega son cosas distintas.
- `22 → 999` puede tener `cerrado_en`, pero nunca es cosechable; los códigos documentados que siguen desconocidos, como 0/2/16/34, producen la misma guarda. Tampoco se cosecha como definitivo un canal desconocido con 22 o 42.

Ejecuté un oráculo independiente de la implementación con todas las secuencias de longitud 0–3 de los 16 códigos clasificados, cuatro desconocidos documentados y 999, en los tipos b/c/s: **29.172 combinaciones conformes**. No es una prueba sobre futuros códigos del prestador, pero sí contrasta ambos lados de la decisión sin limitarse a los recorridos medidos.

Rastreo de consumidores: en el Python del objeto `cerrado_en` solo alimenta directamente `cosechable`; no alimenta un plazo del requerido. De `cosechable` dependen `cosechables`, `pendientes`, `completa`, los motivos, la selección y el nombre/clave del certificado cosechado, el filtro del aportable y la columna del informe. El 22 no añade recepción ni acceso, pues su nueva familia es distinta. No encontré otro cambio de fechas o de clasificación fuera de lo declarado.

**Riesgo aceptado:** existe y la descripción recoge el daño principal. Lo reproduje mediante `cosechar` y dobles, conservando un PDF sintético en disco: se archiva el 22; al añadir 17 la cosecha por defecto devuelve una lista vacía; al añadir después 20 devuelve `ya_estaba` y mantiene los bytes antiguos sin volver a pedir el certificado. Matiz del texto del plan: no todo indicio tardío conduce inmediatamente a `ya_estaba`; 17/21/27 pueden sacar al envío del conjunto cosechable. El resultado material es el mismo: no se actualiza el definitivo. F3 puede continuar trabajando sobre el íntegro antiguo cuando el envío vuelva a ser cosechable; no revalida su actualidad por esta regla. Es consecuencia del riesgo aceptado, no una refutación nueva de F3. Los 83 días observados son evidencia empírica, no un límite temporal que el motor garantice. No encontré un caso peor de cierre silencioso que el riesgo ya declarado.

## 2. El canal sin clasificar

La protección de la **cosecha definitiva y los plazos** está completa en los dos módulos examinados. `canal_clasificado` consulta `CANAL_DE_TIPO`; `cosechable` bloquea lo desconocido antes de cualquier cierre. `Requerido.recibido_en` y `accedido_en` filtran esos envíos (1368 y 1373), incluso si coexisten con envíos conocidos. La agrupación por destinatario los conserva: es lo que D-2 bis exige, no una atribución de sus fechas al plazo. Las propiedades individuales de recepción/acceso siguen disponibles por decisión explícita de «Lo que NO cambia».

El informe distingue `desconocido:s`, declara el motivo y avisa de que sus fechas no cuentan. F3 no los considera electrónicos para obtener los adjuntos y no los prepara como definitivos. Las funciones específicas de burofax no son alcanzadas para preparar un aportable desconocido.

**Excepción explícita del modo provisional:** con `incluir_pendientes=True`, el motor recorre todos los envíos, también los desconocidos. Reproduje s+42: descarga y archiva un PDF marcado `PROVISIONAL`, con `(estado 42)` en el nombre y clave separada. No lo trata como conocido ni lo vuelve definitivo. Esto concuerda con la ayuda nueva del flag, que incluye «sin clasificar», aunque el «no se cosecha nunca» de D-2/§7.1 es literalmente demasiado absoluto: aquí debe leerse «nunca como definitivo». Sin histórico no descarga, sea conocido o no: véase H-01.

## 3. El motivo de lo no definitivo

El orden efectivo es: cosechable → ningún motivo; canal desconocido; código desconocido; estancado; en curso. Es coherente con D-3 y con el orden publicado. La agrupación omite los motivos vacíos, mantiene el orden y no excluye estancados de `pendientes` ni los convierte en `completa`.

La comparación usa la duración completa, **`> timedelta(days=40)`**, no el entero `dias_quieto`. Exactamente 40 días no basta; un segundo adicional sí, aunque el detalle muestre todavía «40 días». `ultimo_evento` usa el máximo temporal, no la posición del elemento ni la fecha del envío, salvo histórico vacío. Estos casos están cubiertos por tests del objeto.

`leida_en` es obligatorio y keyword-only; se rechaza el datetime ordinario sin zona. Solo encontré un constructor de producción: `refrescar` (1462–1463), que pasa el reloj inyectado tomado al inicio de la lectura (1437). `entorno_real` proporciona UTC (2245). Las construcciones de tests del ámbito fueron adaptadas; no encontré un llamador de producción olvidado.

Reloj: las fechas ISO de la API llevan offset y el reloj real es UTC; probé offsets -07:00, UTC, +02:00 y +09:00 para el mismo instante y no cambia el veredicto en el umbral. No hay una dependencia del día de calendario local. La hora es la del inicio de la consulta, no la del final; un evento producido durante la consulta puede quedar en su futuro. Un evento un segundo posterior a `leida_en` da `PUEDE_MEJORAR` y `dias_quieto == -1`, por el redondeo de `timedelta.days`. No crea un cierre ni un estancado falso, pero muestra una edad negativa y no diagnostica desajuste de reloj. La corrección de un reloj externo o una fecha futura arbitrariamente errónea no se valida aquí.

El contrato de zona cubre los datos de los caminos reales, no cualquier objeto Python fabricado: comprobar solo `tzinfo is None` no valida un `tzinfo` personalizado cuyo `utcoffset()` devuelva None, ni valida el tipo de `leida_en`. No he encontrado un productor real de esos valores en el objeto; no lo elevo a defecto de producción. Tampoco extrapolo el resultado de offsets ISO a aritmética de pared con objetos de zona regional construidos directamente.

## 4. Los tres textos

`render_estado` y `render_cosecha` comparten `_no_cosechables`, que consulta `pendientes_por`; el resultado pendiente del aportable consulta `pendiente_por(expedicion.leida_en)` y el mismo `QUE_SIGNIFICA`. Los textos de canal y código explican incertidumbre; el estancado no se convierte en definitivo. «No se cerrará solo» es la redacción prescrita por el plan; las mediciones aportadas no demuestran esa predicción universal. No la cuento como divergencia entre código y diseño.

### H-01 — La salida ofrecida al estancado sin histórico no descarga nada

- **Severidad:** baja. El operador recibe una instrucción ineficaz y puede repetirla indefinidamente; no se produce un definitivo incorrecto.
- **Coste del remedio:** trivial para corregir la explicación y cubrirla con un test.
- **Dónde:** `head/scripts/codicert.py:145–152`; interacción con `head/core/expedicion_certificada.py:1214–1238` y `2433–2436`.
- **Reproducción:** desde este directorio, `$env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe' -X utf8 .\sondas_revision.py`. En `CASO sin_historico`, el envío tiene 116 días, se etiqueta `ESTANCADO`, y ambos informes recomiendan `cosechar --incluir-pendientes`. La llamada real con doble devuelve `[]`, no solicita el certificado y no archiva nada. No es una entrada inválida: `test_sin_historico_lo_quieto_se_cuenta_desde_el_envio` exige ese estancamiento.
- **Afirmación contradicha:** D-3: «señala la salida que ya existe, `cosechar --incluir-pendientes` (baja el certificado con su estado en el nombre, sin ocupar el sitio del definitivo)». La nueva ayuda también promete bajar lo no cosechable sin esta salvedad.
- **Remedio:** conservar la guarda prudente de la cosecha, pero distinguir los envíos sin eventos en la explicación: no hay estado con el que nombrar un provisional y procede revisar el histórico en el prestador. Ofrecer la descarga solo a los que tienen histórico. Añadir una prueba que conecte el mensaje con el efecto del flag para el histórico vacío.

Dos límites heredados, comprobados y sin reabrir F3: (a) `render_cosecha` puede listar el mismo envío como `[nuevo, PROVISIONAL]` y bajo «NO COSECHADOS», porque el segundo bloque enumera lo no definitivo, no las descargas omitidas; ya ocurría en base. (b) el motivo de F3 se alcanza después de obtener/verificar los documentos comunes (2969 y siguientes): con una expedición compuesta solo por un canal desconocido, falla antes con «ninguna entrega electrónica», sin llegar al nuevo motivo. La sonda lo reproduce. La afirmación de que los tres sitios dicen el motivo no es universal frente a esos prerrequisitos; no es un tratamiento del canal como conocido ni un defecto nuevo de recorte. No he encontrado otra rama nueva que reemplace los cuatro motivos por «aún puede mejorar» indiscriminadamente.

## 5. Los tests prueban lo que dicen

Suite indicada por el mandato, sobre `copia/`, sin cache de pytest ni bytecode, con los dos basetemp locales:

| Semilla | Resultado | Duración |
|---|---|---|
| 777 | 187 passed, 2 skipped | 55,42 s |
| 31337 | 187 passed, 2 skipped | 49,26 s |

Los omitidos son los dos tests lentos de OCR. Logs: `tests-777.log` y `tests-31337.log`. No se alteraron aserciones preexistentes en el diff: se incorporó el argumento de lectura y se adaptó la firma del render. Los nuevos tests sí separan umbral estricto, último evento, motivos vacíos, cierre por 22, cada indicio positivo y el indicio tardío.

### H-02 — Faltan controles de exclusión y de motivos concurrentes

- **Severidad:** baja en esta entrega: head implementa bien estas propiedades, pero una regresión de esas guardas puede pasar el ámbito verde.
- **Coste del remedio:** acotado.
- **Dónde:** `head/tests/test_expedicion_observada.py:80–83,110–144`; `head/tests/test_expedicion_pendientes.py:66–93`. Como cobertura de la integración del nuevo mensaje, también falta el caso de H-01 en `head/tests/test_codicert_cli_f2.py:231–267`.
- **Reproducción:** ejecutar los modos de `mutantes_revision.py` desde este directorio con el intérprete del mandato, por ejemplo `& 'C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe' -X utf8 .\mutantes_revision.py indicio_5`. El arnés modifica solo objetos en memoria, importa desde `copia/` y ejecuta los ocho ficheros del ámbito. Los otros modos son `precedencia` y `sin_guarda_codigo`; `--solo-contraejemplo` imprime el comportamiento incorrecto sin ejecutar pytest.
- **Propiedades ausentes:** añadir 5 al conjunto de indicios hace que `5 → 14 → 22` no cierre; preguntar primero por código desconocido hace que s+999 dé el motivo equivocado; quitar la guarda de códigos desconocidos de `cosechable` permite cosechar `20 → 999` o `22 → 999`. El test antiguo de desconocido usa únicamente 999, que tampoco culmina sin esa guarda, y por ello no la demuestra. El test que se llama «el canal sin clasificar se dice primero» nunca combina canal desconocido y código desconocido. El caso positivo del 22 lleva 3 y 14, pero no prueba que los restantes códigos clasificados queden fuera del conjunto de indicios.
- **Afirmaciones contradichas por esas implementaciones equivocadas:** D-1 fija los cinco indicios; el docstring de `pendiente_por` exige el orden de `MOTIVOS_PENDIENTE`; el de `cosechable` declara «Un código desconocido NO hace cosechable». La Task 5 dice: «Uno que sobreviva es un test que falta». No sostengo que sea falsa la muerte de los 18 mutantes del autor: estos son adicionales.
- **Remedio:** parametrizar códigos que no son indicios en históricos con 22, incluyendo 5; añadir canal y código desconocidos simultáneos; combinar un desconocido con 20, 19 y 22 en los canales aplicables y comprobar que no se archiva. Fijar además el orden de motivos esperado independientemente de la constante que ordena la implementación. No basta con comparar la salida con la misma constante si esta también pudiera cambiar.

Los **tres mutantes sobreviven** a los ocho ficheros del ámbito: cada ejecución devuelve **187 passed, 2 skipped**, exit 0. Duraciones: `indicio_5`, 114,69 s; `precedencia`, 121,11 s; `sin_guarda_codigo`, 52,38 s. Evidencias: `mutante-indicio_5.log`, `mutante-precedencia.log` y `mutante-sin_guarda_codigo.log`. Se ejecutaron por separado; ninguna mutación se escribió sobre los módulos de la copia ni del objeto.

## 6. Todo lo nuevo, en fresco

No encontré otros defectos nuevos que justifiquen un hallazgo. Las constantes, firmas y llamadas del diff están conectadas; la clasificación del 22 tiene familia propia; la guarda del canal precede a la culminación; las fechas del requerido no consumen el canal desconocido. Los nombres y claves de provisionales siguen separados del definitivo. No se añadieron dependencias ni llamadas de red por la pieza. El cálculo de días y la agrupación no modifican la decisión de cosechar.

## Evidencias y no mutación

`hashes-apertura.json` contiene SHA-256 de los **2.844 ficheros** de base y head, calculados antes de copiar o ejecutar. Son hashes de los bytes recibidos, incluyendo sus saltos CRLF: sirven para acreditar no mutación. El diff se leyó normalizando los saltos a LF.

`hashes-cierre.json` coincide con apertura **en todos los nombres y hashes**: 1.421 ficheros en base y 1.423 en head, sin añadidos, borrados ni modificaciones. Los dos módulos de producción de `copia/` también conservan los bytes de head tras las mutaciones en memoria. La ausencia de `.git` se contrastó además con `git -C copia ls-files '*.md'`: exit 128, «not a git repository».

Las pruebas y sondas se ejecutaron con el intérprete indicado, usando dobles y datos sintéticos. Se escribieron únicamente la copia y los artefactos de revisión dentro de este directorio. No hubo red, instalaciones, commits ni escrituras en base/head o en el repositorio real. No se delegó la revisión. El mandato específico autoriza estos artefactos locales, frente a la preferencia global de informe externo al repositorio.

## Lo que intenté refutar y NO pude

- Un 22 que cierre pese a cualquiera de los cinco indicios, incluido un indicio tardío.
- Un 22 que convierta un código desconocido o un canal desconocido en definitivo en head.
- Que el 22 altere los relojes de recepción/acceso o que el canal s adelante el plazo del requerido.
- La frontera estricta de 40 días, el uso del último evento y la precedencia efectiva de motivos en head.
- Que el provisional con histórico ocupe el nombre o la clave del definitivo.
- La descripción material del riesgo aceptado: queda reproducida, no refutada.

## SIN VERIFICAR

- No se verificaron los commits por genealogía, ni que los archives procedan de ellos: no tienen `.git`. Se identifica el objeto por el mandato y por sus hashes.
- No se repitió el barrido de producción/sandbox, ni se accedió a certificados reales, API, CRM o fuentes externas. Las mediciones M-17 a M-22 se toman como datos suministrados, no como observaciones propias. No se reevalúa la decisión jurídica de los indicios.
- El arnés original de los 18 mutantes no forma parte del objeto: no queda certificada su ejecución individual. Sí quedan ejecutados los mutantes adicionales y el oráculo descritos aquí.
- Se corrió la suite del ámbito indicada, no los 6.465 casos declarados por el autor. No se ejecutaron los dos tests lentos de OCR ni se reabrió la implementación de F3.
- La suite de gobernanza termina verde, pero sus comprobaciones que enumeran mediante `git ls-files`/`git grep` no acreditan el corpus en un archive sin `.git`: los helpers consumen stdout sin exigir éxito. El verde de esos guards no equivale a verificación de la genealogía o de todas las citas. Los controles que recorren el filesystem y los tests sintéticos sí se ejecutan.
- No garantizo exhaustividad sobre secuencias arbitrariamente largas, formatos Python fabricados fuera de los puertos ni futuras semánticas de códigos del prestador. No hubo desbordamiento de alcance o esfuerzo que impidiera terminar los seis puntos del mandato.

LISTA-CON-CAMBIOS
<!-- informe-literal:fin:u7xz -->

## 2. Evidencia verificada por mí contra la fuente

**El informe es el del revisor, y está terminado.** `INFORME.md` se escribió a las 10:08:42 y el
lanzador registró la salida de `exec` a las 10:08:49: el fichero no podía seguir escribiéndose. Su
`sha256` crudo, el del bloque canonicalizado y el que el revisor declaró en su mensaje final son
**el mismo** (`7ce0423af0278683…`): el fichero ya venía en LF con un solo salto final, así que la
cadena se verifica contra su salida y no solo contra sí misma.

**El objeto es el commit.** Cuatro ficheros de `head/` —`core/expedicion_certificada.py`,
`scripts/codicert.py`, `tests/test_expedicion_pendientes.py` y el plan— coinciden, quitando los CR
de `git archive`, con `git show eb8691a:<fichero>`; y `core/expedicion_certificada.py` de `base/`,
con `git show 73ba288:…`.

**No hubo mutación.** Comparé yo `hashes-apertura.json` (09:56:58) con `hashes-cierre.json`
(10:07:59): **2.844 entradas, idénticas**. Son hashes de los bytes en CRLF que recibió, no de
`git show`: los dos números prueban cosas distintas —el suyo, que no mutó; el mío, que es el
commit—.

**Sus sondas, reproducidas sobre el objeto congelado.** Copié `sondas_revision.py` a mi scratchpad
cambiando **dos líneas** —de dónde importa— y lo corrí contra `head/` sin escribir nada dentro
(1.423 ficheros antes y después): **reproduce todo lo que afirma** —el oráculo de 29.172
combinaciones conforme, el umbral con cuatro desfases, la edad de «-1 días» con un evento un
segundo posterior, el estancado sin histórico al que el informe ofrece una descarga que no baja
nada (H-01), el riesgo aceptado paso a paso y la prioridad de canal sobre código—. Contra el árbol
remediado (`b5c39ee`), **su aserción de H-01 falla**, que es lo que tenía que pasar: el informe ya
no ofrece `--incluir-pendientes` al estancado sin eventos; el oráculo sigue conforme.

**Sus tres mutantes (H-02), con su propio arnés.** Copié `mutantes_revision.py` cambiando **dos
líneas** —la ruta del árbol— y lo corrí contra `b5c39ee`: **los tres mueren** —`indicio_5` con 1
fallo, `precedencia` con 1 y `sin_guarda_codigo` con 4—. Contra `eb8691a` los midió él
sobreviviendo (187 verdes; sus logs, en su directorio). Los mismos tres, más los de la remediación,
están en mi arnés: **26 de 26 muertos**, cada uno por su test.

**Lo que declaró sin verificar**, contrastado donde se pudo: la suite entera con las dos semillas y
los dos tests lentos de OCR los corrí yo (cifras en el §5 del plan); el arnés de los 18 mutantes del
autor ya no es de 18 sino de 26, con los suyos dentro; y lo que observó de los guards de
gobernanza —que enumeran con `git ls-files` sin mirar si git falló, así que en una copia sin `.git`
dan verde sin mirar nada— es **cierto** (`_md_trackeados`, `tests/test_docs_gobernanza.py` l. 140).
Queda fuera de esta pieza, porque no la toca: va a una tarea aparte, con su ronda, que un guard no
se exime nunca.

**Una cosa que el objeto llevaba y no debía, dicha.** La copia `git archive` es el repo entero, y el
spec de Codicert conserva desde F1 el móvil y el email reales de un tercero (la referencia
BCN-OS-008684). El revisor los ha tenido delante, como en las rondas anteriores sobre Codicert. No
es de esta pieza, pero sí de esta ronda: hay una tarea aparte para sanear el repo, y hasta
entonces una ronda nueva tiene que redactarlos de la copia antes de lanzar.
