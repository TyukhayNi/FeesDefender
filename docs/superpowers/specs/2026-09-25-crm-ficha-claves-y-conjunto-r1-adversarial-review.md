---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md
objeto_rev: "1"
commit: dbe17ff
ronda: "1"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: gd57
sha256_informe: 42c9c2a575753cd38b2c830f4130ce574db12986a4ee2939d961c3b65b756c6b
adjudicado_en: docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md §8
---

# Acta — R1 adversarial sobre el DISEÑO de `crm_ficha`: el YAML entero y el conjunto verificado

Objeto: el **spec rev. 1** `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md` en el commit `dbe17ff` —el remedio de
`MEJORAS #283` (claves del `_ficha_crm.yaml` que se pierden) y `#288` (la verificación que mira
lo pedido y no lo que sobra)—.

**Primera de dos rondas**, por el radio de daño: la pieza escribe datos de cliente y decide qué
partes quedan vinculadas a un expediente. Fila de modelo: diseño de escritura sobre datos de
cliente → `gpt-6-astra` · `medium`. La segunda ronda irá sobre el diff.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.3` (binario `80f78947ad880e6e`), `gpt-6-astra` · `medium` — **releídos** del `turn_context` de `rollout-2026-09-25T17-06-27-01a0d91a-….jsonl` (`originator: codex_exec`); velocidad `default` **afirmada** desde el lanzador |
| Objeto | copia `git archive` de `dbe17ff` fuera del repo, sin `.git` (1.408 ficheros) |
| `sha256` del objeto | **idéntico al abrir y al cerrar** (bytes sin normalizar, comparados por el revisor) |
| `sha256` del informe | `42c9c2a575753cd38b2c830f4130ce574db12986a4ee2939d961c3b65b756c6b` |
| Veredicto | **REQUIERE-REVISION** |
| Hallazgos | 4 — **2 `alta`, 2 `media`**; los cuatro confirmados contra la fuente, 0 refutados |
| Tokens | 117.406 |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:gd57 -->
Higiene inicial: conforme; solo estaban `MANDATO.md`, `head/` y `_stdout.log`.

# R1 adversarial del diseño de `crm_ficha`

Objeto: `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md`, rev. 1, del archivo atribuido por el mandato al commit `dbe17ff47b8e56ef0d162e484b89d5d7bc3e927b`. Todas las rutas de código y documentación siguientes son relativas a `head/`; las líneas cuentan el archivo extraído. Revisión del diseño, no de una implementación futura.

La igualdad de los tres bloques cierra el ejemplo de #288 si los IDs esperados están bien resueltos. No cierra todavía la promesa de que todo el YAML se consume y llega al CRM: hay pérdida antes de validar, coerciones de valores y datos no comprobados después de resolver una identidad. Además, falta una salida estable para partes sin identificadores de deduplicación. No cuestiono que el YAML sea la lista completa ni propongo desvincular automáticamente.

## 1. Datos del YAML que pueden no llegar sin error

### H-01 — La validación llega después de que el parser haya descartado claves repetidas

- **Severidad:** alta. **Coste del remedio:** acotado.
- **Dónde:** spec §§1 y 3; `core/crm_ficha.py:153-158`. Otro camino que puede consolidar la pérdida: `scripts/crm_colaboradores_firmas.py:216`, `289-291`.
- **Evidencia:** `scratch/sondas_r1.py`, salida `sondas.log`. `contrario: {nombre: UNO}` seguido de otro `contrario: {nombre: DOS}` produce únicamente DOS. Dos `apellido1` en un mapping conservan solo el segundo. Todas las claves supervivientes están permitidas: las tuplas propuestas no detectan que se perdió una parte o un dato antes de examinarlas. Si el CRM solo contiene lo que sobrevivió al parseo, también pasa la igualdad de IDs. No depende del censo de las 14 fichas ni de que el caso 653 esté mal medido.
- **Afirmación contradicha:** «toda clave del YAML se consume o se rechaza: nada se descarta sin decirlo».
- **Remedio:** detección de claves repetidas durante la construcción del mapping YAML, antes de que se sobrescriban, con ubicación/ruta; definir también la política de merges y alias. Compartir ese parseo seguro con `crm_colaboradores_firmas.apply`: si hay algún enriquecimiento que volcar, su `safe_load`/`safe_dump` puede borrar permanentemente las apariciones repetidas antes de que `crm_ficha` tenga ocasión de rechazarlas. No basta con validar el diccionario final.

### H-02 — Las claves permitidas no aseguran valores consumibles; `_escalar` admite estructuras

- **Severidad:** media. **Coste del remedio:** acotado.
- **Dónde:** spec §3, especialmente «Lo que NO cambia»; `core/crm_ficha.py:79-82`, `98-121`, `133-136`, `154`, `166-168`.
- **Evidencia:** sondas ejecutadas: `apellido1: {apellido: PERDIDO}` se convierte en la cadena `"{'apellido': 'PERDIDO'}"`; `notas_html: {texto: importante}` también se serializa como representación Python. La clave anidada no se consume como campo ni se rechaza. `nombre: '   '` carga como nombre vacío porque se exige presencia antes del `strip`. `cliente_propio: false` se sustituye por `EV_MMC_SPAIN` antes de `_escalar`, en vez de rechazar el booleano. Una raíz `false` se convierte en `{}` por `safe_load(...) or {}`. El mismo bypass de la raíz existe para `0` y `[]`.
- **Afirmación contradicha:** «Validación ANTES de construir nada […] sobre el YAML entero» y «Lo que NO cambia: la validación de valores de `_escalar` (enteros, nulos)» no bastan para sostener «el YAML se lee entero o no se escribe nada».
- **Remedio:** fijar tipos por campo, aceptar únicamente texto/null donde corresponda y rechazar mappings, listas y otros tipos implícitos del parser; comprobar nombres después de normalizar. Separar ausencia/null de valores falsos inválidos antes de aplicar defaults, también en raíz. Incluir rutas de valores inválidos en el diagnóstico agregado. Mantener deliberadamente la semántica de null/ausente, no la de cualquier valor falsy.

### H-03 — Un conjunto exacto de IDs puede certificar una ficha cuyos datos no se escribieron

- **Severidad:** alta. **Coste del remedio:** estructural.
- **Dónde:** spec §§1, 3-4 y exclusiones de §5; `core/sudespacho_relations.py:1669-1736`, `2343-2433`; `scripts/crm_ficha.py:157-168`, `190-225`.
- **Evidencia:** sonda de CLI con YAML sintético `nombre: UNO`, `apellido1: PEREZ`, `nif: 00000000T`; resolución a ID 100 y ficha existente con `1apellido` vacío. Se ejecuta el `ensure_contrario_vinculado` real con dobles en sus accesos al CRM. Resultado: **código 0, «VERIFICADA», cero updates**. `_COMPLETABLES_CONTRARIO` no incluye nombre/apellidos/NIF; la relectura devuelve exactamente los IDs 2 y 100. La comparación propuesta por igualdad también pasa, por construcción. Esto no es pedir reparar las fichas reales excluidas: cualquier ficha existente reproduce la clase de defecto.

  Hay más vías de la misma frontera: valores distintos ya presentes se conservan sin señalar discrepancia; los errores de completar se reducen a logs y no cambian el resultado del CLI. `provincia_canonica` puede devolver `None`: en creación se omite con warning (`872-901`), y al completar puede omitirse sin aviso (`1725-1730`). Los tests actuales incluso exigen la omisión de una provincia desconocida (`tests/test_crm_ficha_campos_perdidos.py:73`). La igualdad de vínculos no comprueba nada de esto.
- **Afirmación contradicha:** «Lo que el YAML declara y lo que queda en el CRM tienen que ser verificablemente lo mismo, en los dos extremos» y «los dos vacíos y todo leído → “VERIFICADA por lectura”».
- **Remedio:** separar el resultado de relaciones del resultado de datos. Comprobar los campos declarados con normalizaciones explícitas y propagar discrepancias, omisiones y lecturas fallidas al veredicto. Conservar la política de no pisar datos existentes: una discrepancia requiere decisión humana, no un PUT automático. Si la pieza quiere cubrir únicamente claves e IDs, debe acotar expresamente su certificación; no puede seguir presentándola como comprobación de toda la ficha ni contestar negativamente al punto 1 del mandato.

**Raíz, campo por campo.** `cliente_propio` sí se transforma a ID y se compara, con el bypass de valores falsos de H-02. `notas_html` no vacío se escribe y relee; los tests cubren truncamiento y normalización de entidades. Vacío/null significa no escribir, no borrar notas antiguas: conviene declararlo, pero no deduzco una orden de borrado del YAML. `firmante` lo consume la etapa de actuación, no este CLI; una ejecución aislada de `crm_ficha` no acredita ni escribe ese campo. P6 lo separa deliberadamente por su efecto sobre la tarifa. El alcance de «VERIFICADA» debe decirlo, sin convertirlo automáticamente en un campo adicional del expediente.

## 2. Partes no declaradas y estados sin salida

Con una lectura completa válida y una resolución de identidad correcta, comparar multiplicidades de todos los IDs de los tres bloques impide que una parte adicional pase inadvertida. No encontré un contraejemplo a esa comparación matemática. H-01 sí puede alterar previamente qué se considera declarado. Tomar el ID devuelto por `ensure_*` tampoco demuestra por sí solo que corresponda a la persona pretendida: esa garantía sigue perteneciendo al resolutor y a sus datos discriminantes.

### H-04 — Una parte sin NIF ni email no se puede reconciliar mediante «añádela y relanza»

- **Severidad:** media. **Coste del remedio:** estructural.
- **Dónde:** spec §§2.3 y 4; `core/crm_ficha.py:78-95`, `124-141`; `core/sudespacho_relations.py:1239-1252`, `1293-1298`, `1669-1681`, `2292-2340`, `2436-2452`.
- **Evidencia:** el loader acepta una parte con solo nombre. La sonda ejecuta `resolver_parte('clientes_contrarios')`: devuelve resolución vacía sin consultas. Dos llamadas reales a `ensure_contrario_vinculado` con solo nombre, simulando únicamente creación y vínculo, devuelven `(101, True)` y `(102, True)`. No se busca por nombre ni hay `id` admitido en el YAML.

  Por tanto, primera corrida: esperado 101, leído 101. Segunda: esperado 102, leído 101+102, sobra 101. Añadir al YAML la parte legítima no resuelve 101: ya estaba declarada y vuelve a crearse. Desvincular el ID anterior permite terminar esa corrida, pero cada relanzamiento vuelve a producir el problema. Una parte preexistente sin esos identificadores presenta el mismo fallo desde la primera corrida. El colaborador tiene la misma ausencia de resolución cuando no hay NIF/email. No propongo inventarle un identificador que no se conoce.
- **Afirmación contradicha:** «si la parte es legítima, añádela al `_ficha_crm.yaml` y relanza» y la definición de esperado como «los ids que devolvieron `ensure_*_vinculado`» como representación suficiente de todas las partes declaradas.
- **Remedio:** definir una identidad persistente para estos casos, por ejemplo referencia explícita a ID CRM validada, o recibo duradero que permita resolver la siguiente corrida. Como mínimo, bloquear antes de escribir los casos que no se pueden resolver de forma estable y explicar cómo conciliarlos. Exigir siempre NIF/email sin una vía alternativa solo cambia la forma del bloqueo para partes legítimas que carecen de ellos.

**Otros flujos y capacidad de expresión.** El alta de la UI vincula cliente propio y colaboradores (`streamlit_app.py:2549-2595`); `link_ev_mmc` solo vincula el cliente pasado, no añade colaboradores ocultos (`core/sudespacho_relations.py:2239-2243`). Los colaboradores del alta que tienen email se pueden declarar y resolver; no procede exceptuarlos de la igualdad. No atribuyo el 653 al alta.

`cliente_propio` solo permite **un** cliente y solo las claves configuradas para IDs 2/27 (`core/config.py:259-262`, `304-316`). Un conjunto legítimo de dos clientes propios o de un cliente fuera de ese catálogo no puede expresarse. Hay un precedente documentado de dos clientes particulares en `MEJORAS_FUTURAS.md:13079-13100`, pero el propio documento lo declara camino no construido y fuera del flujo E&V: **no lo convierto en un hallazgo que obligue a implementar #289 aquí**. Sí debe limitarse el mensaje universal «añádela al YAML» a partes representables y documentarse el dominio soportado. Dentro de ese dominio, sustituir un cliente mal vinculado por el correcto tiene salida humana; no es un fallo de la comparación.

## 3. Multiplicidad y auditoría parcial

La multiplicidad es defensiva y correcta para detectar que dos declaraciones se resolvieron al mismo ID cuando solo se lee un vínculo. No cambiarla por conjuntos simples: ocultaría el colapso. Una repetición accidental de la misma persona en YAML debe corregirse en origen; el fallo no justifica crear dos vínculos artificiales.

El contrato de vinculación es idempotente (`core/sudespacho_relations.py:106-110`, `2219-2223`). Además, `get_relaciones` desacumula **un registro por clave de ID**, como documenta `INTEGRACION_SUDESPACHO.md:2256-2276`; no se deben contar las copias acumuladas como duplicados. La auditoría puede detectar multiplicidad en la secuencia que recibe, pero esa prueba con un doble no acredita duplicados físicos que el endpoint no exponga. No tengo evidencia de que el servidor admita esos duplicados: queda como límite de observabilidad, no como defecto afirmado.

Es correcto no calcular sobrantes en la auditoría parcial: esperado todavía puede ser solo un prefijo de las partes. No abre un falso «VERIFICADA» mientras se conserve la salida 1 incondicional del bloque de excepción (`scripts/crm_ficha.py:169-182`) y el mensaje de cobertura ausente. Un fallo en la escritura de notas, aun con todos los IDs resueltos, deja una auditoría conservadora de menor cobertura, no un éxito falso. La auditoría parcial tampoco repara H-04 ni verifica los datos de H-03.

## 4. Llamadores

Los tres llamadores enumerados se comportan como dice §3 ante un `ValueError` real:

- `crm_ficha`: captura en líneas 78-85, código 1, antes del primer writer de línea 154.
- `crm_ficha_validar`: líneas 52-59, código 2; no llega a validar la documental.
- `abrir_caso._firmante_de`: líneas 1204-1210, transforma un error en `FichaIlegible`; `etapa_actuacion`, líneas 1233-1243, devuelve `fallo` con pendiente `ficha_crm_ilegible`.

No encontré un llamador del loader que rebaje un `ValueError` a «no hay ficha». La ausencia real sí produce firmante vacío. Matices: `--crm skip` evita esa lectura; un `firmante` inyectado evita `_firmante_de`; y la etapa ocurre **después** de `crm_alta`, de modo que el bloqueo no significa cero escrituras de toda la apertura V2. El spec sí limita correctamente esa promesa al CLI `crm_ficha`.

El lector adicional es `scripts/crm_colaboradores_firmas.apply`, que usa directamente `yaml.safe_load` (línea 216), filtra elementos no mapping (229-231) y puede reescribir el fichero completo (289-291). No degrada una excepción del loader: **no lo llama**. Debe figurar en el inventario y compartir al menos el parseo sin pérdida de H-01. Las restantes coincidencias de `_ficha_crm.yaml` en el código son referencias de documentación, controles de intake o exclusión del corpus, no otros cargadores semánticos localizados.

## 5. Plan de pruebas y mutantes

Las pruebas propuestas son pertinentes para claves desconocidas y sobrantes, pero no prueban toda la garantía. Añadir estas propiedades al plan:

| Propiedad | Prueba que debe ponerse roja si se viola |
|---|---|
| No perder datos antes del diccionario (H-01) | Duplicados en raíz, contrario y colaborador, incluidos datos descartados por otra aparición; cero writers. Round-trip del lector `apply` sin poder consolidar la pérdida. |
| No convertir estructura/tipo inválido en dato (H-02) | Mapping/lista en cada campo escalar; raíz false/0/[]; cliente false/0/[]/{}; nombre solo espacios; null y ausente como controles positivos separados. |
| Datos comprobados además de vínculos (H-03) | Resolver una ficha existente con apellido vacío o dato distinto, ejecutar el completado real con IO doblado y comprobar que no termina «VERIFICADA» si el dato no llega. GET/PUT fallidos y provincia no reconocida. |
| Reejecución convergente (H-04) | Doble con estado persistente, dos corridas de una parte sin NIF/email: no crear una identidad nueva ni declarar sobrante la identidad anterior. La política alternativa debe probarse antes del primer writer. |
| Igualdad en los tres bloques | Sobrantes en clientes propios, contrarios y colaboradores, incluso cuando se esperan cero de estos dos últimos; faltan y sobran simultáneamente; int/string de ID. |
| Auditoría parcial no certificadora | Fallar cada writer; conservar código 1 y ausencia de «VERIFICADA», además de no inventar sobrantes. |

El control positivo «todas las claves […] carga sin error» no acredita que **cada valor** llegue al atributo correcto. Tampoco exigir presencia en una tupla mata necesariamente un constructor que recorre todas las claves pero asigna `''` a una. Usar valores centinela distintos y comprobar destino y normalización de cada campo; mutar supresión y cruce de asignaciones, no solo la lista de claves.

Los cuatro mutantes mínimos de §6 cubren sus defectos locales, no H-01 a H-04. Al implementarlos, exigir muerte por la aserción de la propiedad, no por un arnés roto. Aquí no se han construido ni ejecutado mutantes de una implementación que todavía no existe.

**Ejecución realizada:** las cinco suites ordenadas por el mandato, en `scratch/`, con Python 3.14, `PYTHONDONTWRITEBYTECODE=1`, sin caché, semilla 777 y `--basetemp=_bt777raiz`: **81 passed in 20.20s**, en `tests-final.log`. Dos intentos anteriores fallaron en setup por permisos del sandbox al invocar con `workdir=scratch`; el segundo intentó una adaptación de mkdir sin éxito. Ejecutar desde el directorio autorizado y hacer `Set-Location scratch` permitió correr el comando original **sin esa adaptación**. `tests-base.log` y `tests-adaptados.log` conservan los errores; no son fallos del diseño. Sondas adicionales en `scratch/sondas_r1.py`, con bloqueo explícito de sockets y dobles de IO, salida `sondas.log`. Las sondas reproducen comportamiento existente que las decisiones del spec dejan intacto; no se presentan como ejecución del diseño futuro.

## 6. Exclusiones y cierre de frontera

Puede seguir fuera reparar los registros reales 1128/1129, investigar quién añadió los colaboradores del 653, consultar CRM en dry-run y ampliar C6. Ninguna de esas acciones es necesaria para demostrar los hallazgos.

Deben entrar el parseo sin pérdida y los tipos de H-01/H-02, el alcance explícito de la certificación de datos de H-03 y una política de resolución estable para H-04. El recibo de IDs excluido para C6 no puede descartarse por analogía si resulta ser la solución elegida para reejecutar `crm_ficha`: son necesidades distintas. Debe declararse además qué hacer con un sobrante legítimo que el esquema actual no puede representar; no remitir siempre a una edición imposible del YAML.

## 7. Contradicciones con código, P6 y contrato CRM

H-03 contradice el alcance literal del spec con la política actual de completar sin pisar y sin propagar fallos. H-04 contradice la salida universal de conciliación por edición/relanzamiento. El propio loader contradice la descripción implícita de `_escalar` como barrera de tipos suficiente (H-02).

No encontré contradicción con la semántica P6 de `contrario` mapping/lista/null/ausente (`spec P6:125-144`), ni razón para retirarla. El bloqueo de identidad ambigua/conflictiva sigue siendo correcto: no debe resolverse escogiendo un ID para que cuadren los conjuntos. P6 ya exige convergencia tras resolver buzones compartidos; la reejecución sin ningún criterio discriminante es una frontera adicional.

El contrato de `related_register` respalda tratar bloques ausentes como vacíos tras una respuesta válida; no respalda contar sus listas acumuladas como vínculos distintos. `get_relaciones` ya rechaza formas generales inválidas y acumula bloques repetidos sin sobrescribir (`2060-2089`). Debe conservarse esa capa y comparar su salida normalizada. El valor `None` del CLI representa una lectura fallida y debe seguir siendo SIN VERIFICAR, no ausencia de relaciones.

## Lo que intenté refutar y NO pude

- Igualdad de multiplicidades con IDs correctos y lectura completa: sí detecta un ID adicional en cualquiera de los tres bloques.
- Colapso de dos declaraciones al mismo ID: la multiplicidad evita certificar dos partes con un solo vínculo.
- Error del loader rebajado a ficha ausente por los tres llamadores: no encontrado.
- La auditoría parcial como vía de éxito: el CLI sale siempre con error por escritura fallida.
- Notas no vacías truncadas o no leídas como falso éxito: los caminos existentes y sus tests distinguen FALTA/SIN VERIFICAR.
- `link_ev_mmc` añadiendo colaboradores por sí mismo: el código solo solicita el cliente indicado.
- Necesidad de desvincular automáticamente o de invalidar la decisión de lista completa: ninguna; los remedios preservan ambas decisiones del titular.

## SIN VERIFICAR

- Censo de las 14 fichas y estado/histórico real del 653: sin Drive ni CRM, conforme al mandato. Se aceptan como mediciones del autor; ningún hallazgo depende de declararlas falsas.
- Comportamiento vivo del servidor, automatismos, concurrencia, completitud efectiva de una respuesta y exposición de vínculos físicamente repetidos. Solo se contrastó el contrato documentado y el código.
- Procedencia del archivo contra el objeto Git: no hay `.git`; el commit es el anclaje aportado, no una resolución Git independiente.
- Implementación y mutantes futuros, suite completa del proyecto y apertura V2 integrada: no ejecutados. Los llamadores se contrastaron por lectura; se ejecutaron las cinco suites indicadas y las sondas descritas.
- La revisión no quedó truncada por esfuerzo: se contestaron los siete puntos. No se modificó código de `head/` ni se accedió a red, Drive o CRM.

**No mutación:** coinciden los SHA-256 de los 1408 ficheros de `head/` entre `hashes-apertura.json` y `hashes-cierre.json`: cero añadidos, cero eliminados y cero modificados. Se compararon rutas y hashes de bytes, sin normalizar CRLF, por lo que también queda cubierta una alteración de finales de línea.

REQUIERE-REVISION
<!-- informe-literal:fin:gd57 -->

## 2. Evidencia verificada por mí contra la fuente

- **Digest.** Recomputado sobre el fichero entregado: coincide con el que da el revisor en su
  mensaje final.
- **Los cuatro, contra el código:** H-01 reproducido con `yaml.safe_load` sobre dos `contrario`
  seguidos —queda solo el segundo, sin error—; H-02 leído en `_escalar` (solo rechaza números y
  booleanos) y en los `or` de `cargar_ficha_yaml`; H-03 leído en
  `core/sudespacho_relations.py::_COMPLETABLES_CONTRARIO`, que no incluye nombre, apellidos ni
  NIF; H-04 leído en `resolver_parte`, que identifica solo por NIF o email.
- **Contra el corpus real, en solo lectura y sin valores:** en los 14 `_ficha_crm.yaml` del Drive
  del despacho hay **cero** mappings con claves repetidas y **cero** partes sin NIF ni email (17
  contrarios, 39 colaboradores), así que los remedios de H-01 y H-04 no rechazan ninguna ficha
  legítima de hoy.
- **Higiene.** El revisor declara en su primera línea un directorio sin ficheros ajenos.
- **Tiempos.** Lanzado a las 17:07; `exec` salió con `exit=0` (`_exit.txt` del lanzador, señal de
  fin del vigía).
- **Adjudicación:** `docs/superpowers/specs/2026-09-25-crm-ficha-claves-y-conjunto-design.md` §8. **La rev. 2 que la remedia no ha pasado ronda propia**:
  la segunda del presupuesto es la del diff.
