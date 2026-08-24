---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
objeto_rev: "6"
commit: ce3ab5a6e394fd2ae736f8dd9e4cade3c02a36c7
ronda: "5"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: zwqk
sha256_informe: a42eebf9d066388bf977eb2b863f6532fa072b9047dfba389aed5593efe41879
adjudicado_en: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md §23
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R5.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el §23 del objeto, no aquí.
>
> **Objeto:** si la **rev. 6 remedia de verdad** los cinco hallazgos de R4. El mandato prohibió
> redescubrir H3-01, H3-02, H3-04, las tres decisiones del §20 y los contratos abiertos de
> H3-03/H3-05/H3-06, y advirtió expresamente del patrón medido en las dos rondas anteriores: el
> adjudicador introduce defectos NUEVOS al escribir el remedio. Se le dijo que asumiera que la
> rev. 6 podía repetirlo.
>
> **Montaje del revisor.** Copia externa del árbol completo del commit `ce3ab5a` vía
> `git archive`: solo lectura **por construcción**, sin `.git` y sin red. La evidencia de
> no-mutación es el SHA-256 del objeto y de las cuatro actas previas al abrir y al cerrar.

## 0. Mandato (literal, tal como se entregó)

```text
MANDATO R5, NUMERADO POR DAÑO

OBJETO
- Spec: `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, **rev. 6**.
- Árbol a revisar: COPIA EXTERNA completa y de solo lectura por construcción, en
  C:\Users\tnm33\.codex\reviews\_arbol-r5-ce3ab5a
  Árbol íntegro del commit ce3ab5a6e394fd2ae736f8dd9e4cade3c02a36c7 (rama codex/docs/apertura-integral-w02q38c, PR #225), obtenido con `git archive`. Incluye core/, scripts/, tests/, docs/, CLAUDE.md y AGENTS.md. Sin `.git`: no hay nada que ensuciar.
- Digests del objeto: en la copia está en CRLF, SHA-256
  E2ED502B385622462CF19255D7CA8F67034E6FB404CC40A56F77ABF00160BD99.
  Forma canónica (LF): 0E147418B3EC12C98CA885205B16AEC5C783DAA1A8A9E72D2E21BB5D18F70C2E.
  Verifica los dos al arrancar. La discrepancia es el final de línea, no un hallazgo.
- Actas previas, en la misma copia: `docs/superpowers/specs/2026-08-15-apertura-integral-r{1,2}-adversarial-review.md`, `2026-08-24-apertura-integral-r3-adversarial-review.md` y `2026-08-24-apertura-integral-r4-adversarial-review.md`. Adjudicaciones: §§18, 19, 20 y 22.
- Contrato de gobernanza: `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`, en la copia.

QUÉ SE REVISA, Y QUÉ NO
La rev. 6 hace UNA cosa: **remediar los cinco hallazgos de R4** (H4-01 a H4-05), todo dentro del §21, más dos correcciones que R4 pidió (invariante sin absolutos; parte negativa del criterio 38 a global). La decisión de la frontera de H4-02 la tomó Nikolai: la atomización local del correo YA DEPOSITADO entra en V1, sin descubrimiento ni exportación de Gmail.

**El objeto de esta ronda es si esa remediación cierra de verdad.** NO redescubras: los tres críticos de mecánica H3-01, H3-02 y H3-04, las tres decisiones pendientes de Nikolai (§20), ni los contratos abiertos de H3-03 acotado, H3-05 y H3-06. Están adjudicados y declarados abiertos a propósito. Sí debes decir si la rev. 6 los agrava, les cambia la forma, o afirma sobre ellos algo falso.

**Un patrón medido que conviene que ataques.** En las dos rondas anteriores, el adjudicador introdujo defectos NUEVOS al escribir el remedio: tres de los cinco hallazgos de R4 eran texto suyo del mismo día (un token de estado inventado, un criterio movido perdiendo dos precondiciones, un inicializador llamado «mínimo» que no lo es). Asume que la rev. 6 puede repetirlo.

1. Ataca uno por uno los cinco remedios: ¿es implementable, suficiente y OBSERVABLE, o solo renombra el riesgo? En particular, y sin que esto agote tu búsqueda: el remedio de H4-01 exige «reconocer la ejecución V1 y rechazar técnicamente cualquier modo distinto de `skip`» — ¿dice el §21 CÓMO se reconoce una ejecución V1, o es una propiedad sin mecanismo, el mismo modo de fallo que H3-02 le imputó al mutex? Comprueba también si el criterio negativo propuesto es demostrable con el código real.
2. Ataca la entrada de la atomización local en V1. Contra el código: ¿qué escribe de verdad `_atomizar_correo`/`_procesar_adjuntos` y su pipeline, dónde, y con qué custodia? ¿Cubre el §21 sus artefactos, generación, fronteras de crash y poda, o lo afirma sin cubrirlo? ¿Introduce alguna escritura remota, o alguna dependencia de red o de LLM, que rompa la invariante recién formulada? ¿Y rompe el «V1 no descubre correo» por alguna vía indirecta?
3. Ataca la enumeración del write-set del §21.2: ¿está completa AHORA, o quedan caminos de V1 que escriben sin guard, sin hash, sin evento, o contra un destino distinto del efectivo? La lista de la rev. 6 salió de tu propio informe R4: busca lo que ninguno de los dos vio.
4. Ataca la contabilidad de criterios: 24 en V1, 26 diferidos, 10/14/35/38 declarados partidos, 27/50/38-negativo como globales. ¿Suma? ¿Hay algún criterio que V1 ejerce y sigue diferido, alguno indemostrable dentro de V1, o alguna parte de un criterio partido que quede sin dueño? ¿Y el criterio 1 y el 13 reescritos para V1 son ahora demostrables?
5. Busca contradicciones NUEVAS introducidas por la rev. 6, dentro del §21 y contra el resto del documento y los contratos no derogados (CLAUDE.md, AGENTS.md, arquitectura dual, runbook, contrato de gobernanza). Incluye el movimiento del criterio 29 a «posterior a V3» y la reformulación de la invariante.
6. Decide: ¿queda el alcance de V1 fijado de forma comprobable, de modo que lo único que separe la rev. 6 de un plan TDD sean las tres decisiones del §20 y los contratos abiertos de H3-03/H3-05/H3-06? SHIP / LISTA-CON-CAMBIOS / REQUIERE-REVISION / NO-SHIP. Distingue lo que bloquea el ALCANCE de lo que bloquea el PLAN.

CONTRATO ESTRICTO
- Trabaja SOLO sobre la copia externa. No toques `C:\Users\tnm33\Dev\FeesDefender` ni `C:\Users\tnm33\Dev\FeesDefender-crm` ni ningún sistema externo. Sin red. Si un comando git contra esos repos falla por propiedad del directorio, es deliberado: no lo sortees.
- La copia es el objeto de registro. No la modifiques. Calcula al arrancar y al terminar el SHA-256 del objeto y de las CUATRO actas previas: deben coincidir. Esa evidencia sustituye al `git status` limpio.
- No lances subagentes. Haz las pasadas necesarias tú mismo.
- Si ejecutas tests, sobre copia propia bajo tu directorio de trabajo o el temporal, con `PYTHONDONTWRITEBYTECODE=1`, `pytest -p no:cacheprovider` y `--basetemp` en ruta CORTA. El entorno puede carecer de `python-dotenv`; si falla la colección por eso, declara la cobertura dinámica SIN VERIFICAR y sigue. No instales nada.
- Contrasta contra el código real y las fuentes completas, no contra el diff ni contra la seguridad con que esté redactada la spec.
- Hallazgos H5-01, H5-02… por severidad y daño. Cada uno: severidad, `file:line`, hecho, impacto, evidencia o reproducción, corrección mínima. No infles nitpicks. Si la remediación cierra, dilo: un informe corto con veredicto favorable es un resultado legítimo y esta ronda tiene objeto pequeño.
- Secciones obligatorias: Identificación y alcance; Fortalezas; Hallazgos; Respuesta al mandato 1-6 punto por punto; Preguntas y limitaciones; Veredicto. TÚ NO ADJUDICAS: adjudica Claude Code contra la fuente. Lo que no puedas verificar, dilo SIN VERIFICAR.
- Escribe el informe ÚNICAMENTE en: C:\Users\tnm33\.codex\reviews\2026-08-24-apertura-integral-r5\2026-08-24-apertura-integral-r5-adversarial-review.md
- No existe: no sobrescribas ningún informe previo. Formato canónico: UTF-8 sin BOM, LF, exactamente un salto final.
- Devuelve en el mensaje final: ruta exacta, SHA-256 canónico del informe, conteo por severidad, veredicto, lista breve de hallazgos y los digests del objeto y de las cuatro actas antes y después. Sin ruta y digest la revisión no cuenta.
```

## 1. Informe recibido de Codex, sin modificar

Digest declarado por el revisor y verificado de forma independiente al recibirlo, contra
`C:\Users\tnm33\.codex\reviews\2026-08-24-apertura-integral-r5\2026-08-24-apertura-integral-r5-adversarial-review.md`:
A42EEBF9D066388BF977EB2B863F6532FA072B9047DFBA389AED5593EFE41879.

<!-- informe-literal:inicio:zwqk -->
# Revisión adversarial R5 — apertura integral rev. 6

## Identificación y alcance

- **Objeto:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, rev. 6, commit archivado `ce3ab5a6e394fd2ae736f8dd9e4cade3c02a36c7`.
- **Copia revisada:** `C:\Users\tnm33\.codex\reviews\_arbol-r5-ce3ab5a`, completa, sin `.git` y tratada como solo lectura.
- **Alcance:** exclusivamente si §21 remedia H4-01…H4-05, incluida la decisión de incorporar a V1 la atomización local del correo ya depositado, la reformulación de la invariante, el reparto de criterios y el movimiento del criterio 29. No se redescubren H3-01, H3-02, H3-04, las tres decisiones de §20 ni los contratos abiertos de H3-03/H3-05/H3-06; solo se comprueba si rev. 6 los agrava, cambia o describe falsamente.
- **Rol:** revisor adversarial. Este informe no adjudica; adjudica Claude Code contra la fuente.
- **Método:** lectura de la spec completa y sus adjudicaciones, las cuatro actas previas, gobernanza, `CLAUDE.md`, `AGENTS.md`, runbook, arquitectura dual y contratos/código de los caminos V1. No se usó red ni se tocó ningún sistema externo.

### Integridad inicial del objeto

| Artefacto | SHA-256 inicial |
|---|---|
| Spec rev. 6, bytes CRLF | `E2ED502B385622462CF19255D7CA8F67034E6FB404CC40A56F77ABF00160BD99` |
| Spec rev. 6, forma canónica LF | `0E147418B3EC12C98CA885205B16AEC5C783DAA1A8A9E72D2E21BB5D18F70C2E` |
| Acta R1 | `E30D9EF9EFABD1F822F9F67DB547217BB77C9C2FC9945BA1805F88ACA658A57F` |
| Acta R2 | `55A88365DC52656A9DBBE172F923BC288984BDAE7C58A1DFAE7215D885104032` |
| Acta R3 | `CC4B8653930F49FA2CAC6464EC4F45881935E7905B85F8E7F4BDDB96704FBD0C` |
| Acta R4 | `C345DE3F6CAB54191D70744D818806EA4D1B5028740CD217D8228CB42CEA82F3` |

La diferencia entre los dos hashes de la spec es exclusivamente CRLF frente a LF y no es un hallazgo.

## Fortalezas

1. La decisión de alcance de H4-02 ya es inequívoca: V1 incluye atomización **local** de correo depositado y excluye descubrimiento, etiquetado y exportación Gmail (`spec:1284-1308,1382-1386`). El atomizador real enumera únicamente lotes locales `*_email_*` y `00_Input/03_Email` (`core/email_atomize/pipeline.py:393-427`); su camino normal no llama a Gmail ni a un LLM.
2. H4-03 mejora sustancialmente: elimina el token inventado, reescribe el criterio 1 para la secuencia V1, refuerza el 13, conserva en V1 las partes ejercidas del 35 y lleva la parte negativa del 38 a global (`spec:1390-1424`). La lista contiene 24 números distintos y su complemento contiene 26: aritméticamente, 24 + 26 = 50.
3. H4-04 queda cerrado en su núcleo: la ejecución de fase 8.1 y el criterio 29 pasan a una integración posterior a V3, conservando sala de lectura y viabilidad como precondiciones (`spec:1375`).
4. La nueva invariante deja de negar el refresh OAuth conocido y distingue las lecturas Drive/Sudespacho de los efectos remotos no idempotentes del caso (`spec:1314-1325`). `pull_expediente_v2` lista y descarga por caminos de lectura; no encontré en ese flujo una mutación remota de negocio.
5. Rev. 6 reconoce de forma honesta dos deudas en vez de darlas por hechas: `ensure_case` no es mínimo (`spec:1292-1296`) y el write-set completo es una precondición (`spec:1349-1353,1440-1441`). Esa honestidad evita un verde falso, aunque significa que H4-05 aún no está remediado.

## Hallazgos

### H5-01 — CRÍTICA — V1 sigue sin identidad ejecutable; no puede hacer cumplir `skip` ni impedir la exportación Gmail

- **Severidad:** CRÍTICA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1327-1333,1404-1407,1442-1447`; `scripts/abrir_caso.py:64,194-212,248-260,355-385,479-499`; `core/email_export.py:906-968,1177-1214`.
- **Hecho:** §21 repite literalmente la corrección pedida por H4-01 —«reconocer la ejecución V1 y rechazar técnicamente»—, pero no define qué argumento, subcomando, API interna, estado o contexto distingue una ejecución V1 de una invocación ordinaria del entrypoint compartido. Sin ese discriminante, el criterio negativo no es implementable: cambiar el default a `skip` no hace que **omitir** el flag aborte; prohibir globalmente `api` rompería V2; y validar solo el E2E feliz no separa ambos regímenes. El código real conserva `crm="api"` y el POST alcanzable, pero además conserva `fuente="email"`: `_despachar_intake` llama a `_intake_email`, que reserva lote y ejecuta `email_export.export_label`; este construye el servicio Gmail, lista la etiqueta y descarga mensajes. También siguen seleccionables `manual` y `whatsapp`, fuera de la enumeración cerrada de V1. La búsqueda completa de `core/`, `scripts/` y `tests/` no encuentra un marcador V1.
- **Impacto:** una implementación conforme al texto puede seguir llamando al mismo entrypoint con `--yes` y alcanzar alta CRM o exportación Gmail, mientras la suite V1 solo prueba una invocación que pasa `--crm skip`. H3-03 deja de estar acotado a efectos locales y «V1 no descubre ni exporta correo» queda como convención, no como frontera técnica. El criterio negativo «aborta antes de cualquier efecto» tampoco tiene un punto observable donde disparar.
- **Evidencia o reproducción:** cadenas estáticas actuales: (a) `abrir_caso.main(crm="api", yes=True)` → `_alta_crm` → `create_expediente`; (b) `abrir_caso.main(fuente="email", cuenta=..., label=...)` → `_intake_email` → `email_export.export_label` → `labels().list`/`messages().list`/`messages().get`. Ambas rutas comparten exactamente la fachada que §21.5 ordena ampliar. La validación V1 tendría que ocurrir antes de autoderivación, `ensure_case`, intake y cualquier consulta remota, no al final.
- **Corrección mínima:** fijar en §21 un discriminante ejecutable único —por ejemplo, un modo/subcomando V1 o una llamada interna tipada del driver— y su orden de validación. En ese modo, antes de cualquier efecto o lectura remota no permitida: exigir `crm == skip`, rechazar `api`, excluir `fuente=email|manual|whatsapp` de la adquisición V1 y permitir únicamente las fuentes/capacidades enumeradas. Añadir pruebas negativas separadas para caso nuevo e incremental con spies de CRM, Gmail, Drive mutante y filesystem; omitir `--crm skip` y pedir `api` deben fallar antes de crear el esqueleto.

### H5-02 — ALTA — La atomización entra por nombre, pero no entra su contrato de publicación, crash, éxito y poda

- **Severidad:** ALTA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1304-1312,1397-1403,1415-1416,1437-1441`; `scripts/sala_maquina.py:291-355,363-410,488-579`; `core/email_atomize/pipeline.py:121-273,365-390`; `core/email_atomize/ids.py:118-147`; `core/adjuntos_contenido/pipeline.py:42-118`; `tests/test_sala_maquina_cableado_atomize.py:185-230`.
- **Hecho:** rev. 6 añade a criterios 10/14/41/48 la frase de que «cubren» artefactos, generación, crashes y poda, pero no define la unidad de generación ni el orden durable de publicación. El camino real escribe, sin staging común, `mensajes/*.md`, `*.historial.md`, binarios y sidecars de `adjuntos/`, `*.contenido.md`, `_contenido_estado.json`, `corpus.jsonl`, `CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md`, `_revision/*`, `vistas/*` y `_registro.json`, además de eventos en `_intake_log.jsonl`. Poda con `unlink()` mensajes, vistas y contenidos (`pipeline.py:218-220,264-267`; `adjuntos_contenido/pipeline.py:106-110`), mientras el contrato general exige conservar bytes históricos o inactivarlos, no retirada irreversible de derivados (`spec:469-482`). Ante error de construcción, el atomizador publica un conjunto parcial y reescribe agregados reducidos; ante excepción, `_atomizar_correo` registra `fallo` pero el OCR continúa. El test existente fija expresamente ese comportamiento blando.
- **Impacto:** V1 puede producir una sala de máquina verde sobre una generación de correo fallida o parcial, con `_registro`, agregados, adjuntos y podas pertenecientes a fotografías distintas. Un crash entre cualquiera de esas escrituras carece de algoritmo de reconciliación, y el evento solo conserva contadores/status, no un manifiesto hash de la generación publicada. Incorporar el nombre de la fase renombra el riesgo de H4-02, pero no lo vuelve observable ni recuperable.
- **Evidencia o reproducción:** `tests/test_sala_maquina_cableado_atomize.py:185-208` afirma que, si `atomize_dir` lanza, `sm.ejecutar` corre igual; `:213-230` acepta `publicado=True`, `poda_omitida=True` y errores. `core/email_atomize/pipeline.py:78-82` documenta que los agregados se reescriben desde el conjunto reducido y quedan incoherentes con el árbol completo. No hace falta ejecutar la suite para demostrar que esa es la semántica intencionada; la cobertura dinámica queda `SIN VERIFICAR`.
- **Corrección mínima:** en §21, definir una sola fotografía de entrada local y una generación de salida atomizada; enumerar sus artefactos; persistir intención antes de publicar; publicar desde staging bajo el mutex; enlazar evento/estado a un manifiesto content-addressed; decidir qué status bloquea el cierre V1 aunque el OCR continúe; y convertir la poda en archivado/inactividad coherente con §8. Añadir crash-injection después de cada clase de escritura y una prueba que impida que un `fallo`/`parcial` se presente como fase V1 completada.

### H5-03 — ALTA — H4-05 no está remediado: §21 declara futura la enumeración que su cabecera da por terminada

- **Severidad:** ALTA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1261-1266,1335-1353,1437-1441`; `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md:133-156,1078-1106`; `scripts/sala_maquina.py:79-180,537-590`; `core/sala_maquina.py:475-568,773-788`; `core/split_documental.py:304-320,554-568`.
- **Hecho:** la nota de rev. 6 afirma «el write-set se enumera», pero §21.2 solo enumera cinco familias de deuda ya señaladas en R4 y concluye que **hay que** enumerar el write-set completo. §21.5 vuelve a convertir esa enumeración en precondición futura. No existe la decisión exigida por H4-05 artefacto por artefacto —bloqueado, mutex o excepción protocolaria explícita— ni tabla de destino efectivo, hash, evento, frontera de crash y poda. El recorrido real añade detalles no individualizados: `_sala_maquina_state.json`, `_cobertura.json`, `_revisar/_cobertura.md`, `_tiempos.jsonl`, staging y manifiestos de bundles, `01_OCR`, `03_MD`, `raw_text`, `99_Versiones anteriores`, los artefactos de correo enumerados en H5-02 y el log. La prueba propuesta mira «el árbol completo», pero el contrato dual exige cuatro planos: árbol, canon incluidas carpetas/estado de canal, llamadas externas y estado local de aplicación.
- **Impacto:** el plan tendría que descubrir y clasificar la superficie de escritura que el diseño debía fijar. Puede cerrar #120 y los cuatro ejemplos de R4 dejando otro control, archivo histórico o estado de canal en el canon equivocado. También puede declarar cero cambios sobre el árbol del caso mientras muta autenticación/registro local o llama a un servicio no permitido.
- **Evidencia o reproducción:** contraste directo entre la afirmación de `spec:1263-1266` y las precondiciones pendientes de `:1349-1353,1440-1441`. Las llamadas de escritura de `scripts/sala_maquina.py`, `core/email_atomize`, `core/adjuntos_contenido`, `core/sala_maquina.py` y `core/split_documental.py` producen más de una docena de clases de artefacto sin clasificación normativa individual. Esto no reabre H3-03/H3-05/H3-06: demuestra que el remedio previo y local de H4-05 no se incorporó al objeto.
- **Corrección mínima:** sustituir los ejemplos por una tabla cerrada del write-set V1 con: productor, patrón de ruta, destino efectivo por workspace, clase contenido/protocolo/temporal, guard/capacidad, mutex/operación, hash/manifiesto/evento, crash/readback y política de poda. El E2E negativo debe comparar los cuatro planos del contrato dual, no solo los bytes del árbol. Solo después esa tabla puede ser precondición del bloque de implementación; no puede seguir siendo una tarea que el plan deba diseñar.

### H5-04 — ALTA — El criterio 38 se globaliza en la dirección opuesta al default peligroso que pretende cerrar

- **Severidad:** ALTA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:972-973,1373,1411-1414,1504-1508`; `core/sync_sudespacho.py:1352-1393`; `scripts/sync_sudespacho.py:142-203`.
- **Hecho:** el criterio 38 original y §21.4 dicen «un caso **judicial** no entra por entrypoints **extrajudiciales**». Sin embargo, el defecto usado para justificar su globalización es el inverso: tanto core como CLI del pull eligen por default `expedientes_judiciales`, de modo que una apertura **extrajudicial** puede entrar por la vía **judicial**. La propia adjudicación de R4 formula correctamente ese inverso en `spec:1504-1508`, pero el remedio copia la otra dirección. El CLI actual agrava la observabilidad: la discordancia de referencia solo muestra warning y permite continuar (`scripts/sync_sudespacho.py:172-203`).
- **Impacto:** una suite que pruebe literalmente el criterio global puede quedar verde sin atacar el default real. El pull puede consultar el elemento equivocado, presentar un vacío ambiguo o depositar bajo la rama incorrecta; el gate de referencia que V1 promete no compensa que el criterio pruebe el cruce contrario.
- **Evidencia o reproducción:** llamar `pull_expediente_v2(case_id, expediente_id)` sin `element` selecciona `expedientes_judiciales` (`core/sync_sudespacho.py:1356`); el CLI hace lo mismo con `element or "expedientes_judiciales"` (`scripts/sync_sudespacho.py:167`). Ninguna de esas rutas es refutada por probar «judicial no usa extrajudicial».
- **Corrección mínima:** hacer la restricción bidireccional y exigir en V1 un `element` explícito derivado del expediente vinculado: judicial nunca usa extrajudicial y extrajudicial nunca usa judicial. Retirar el default en el camino V1 y convertir la discrepancia de referencia/elemento en aborto anterior a toda escritura, con spies separados para ambos cruces.

### H5-05 — MEDIA — La suma 24/26 cuadra, pero dos colas de criterios partidos no tienen dueño y sobreviven textos 22/28/R4 obsoletos

- **Severidad:** MEDIA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:889-920,1363-1375,1390-1424,1464-1466`.
- **Hecho:** la lista V1 contiene 24 criterios y su complemento 26; eso sí suma. Pero §21.4 afirma que el resto de los cuatro criterios partidos 10/14/35/38 «figura en la tabla del §21.3». Solo ocurre con 35 (V2) y 38 (rama judicial diferida). Las colas de 10 —consultas Gmail/LeadHub— y 14 —LeadHub pendiente y crashes de las fronteras que vuelven en V2/V3— no aparecen en ninguna fila de la tabla. Además, la cabecera vigente del §14 aún declara 22/28 (`:891-893`) y §21.6 aún dice que «la rev. 4 debe cerrar» cuatro hallazgos, incluye H3-07 y espera que R4 corra (`:1464-1466`), aunque §21.6 acaba de declarar H3-07 fuera de V1 y §22 ya adjudica R4.
- **Impacto:** no rompe la parte V1 ya enumerada de 10/14, pero contradice la afirmación «diferido con su vertical» y deja sin prueba futura dos porciones. El texto obsoleto también responde falsamente a la pregunta de qué separa V1 del plan: H3-07 no es bloqueante de V1.
- **Evidencia o reproducción:** complemento exacto de la lista V1: `6,8,9,11,12,17,19,20,21,22,23,24,25,26,28,29,30,31,32,39,40,43,44,45,46,49`. Ninguna fila asigna explícitamente las partes diferidas de 10 y 14 porque esos números ya cuentan una vez en V1; precisamente por eso hace falta nombrar sus colas sin recontarlas.
- **Corrección mínima:** añadir a las filas Gmail/LeadHub/V2-V3 las partes diferidas de 10 y 14, actualizar §14 a 24/26 y sustituir el cierre obsoleto de §21.6 por la situación posterior a R4: H3-07 fuera de V1; decisiones §20 y H3-03/H3-05/H3-06 bloquean el plan.

## Respuesta al mandato 1-6 punto por punto

### 1. Cinco remedios de R4

- **H4-01: no cierra.** Repite la propiedad deseada, pero no define cómo se reconoce V1. El criterio negativo no puede distinguir omisión en V1 de una invocación ordinaria y no cubre el selector de fuente que alcanza Gmail (H5-01).
- **H4-02: decisión de frontera cerrada; contrato operativo no cerrado.** Está claro que entra correo ya depositado y no Gmail remoto. Faltan generación, publicación, crash, poda, hashes y condición de éxito material (H5-02).
- **H4-03: cierra en lo principal.** `preparado_con_pendientes` existe, 1 y 13 tienen semántica V1 y 35 se parte. El criterio 1 solo será ejecutable cuando se resuelvan el marcador V1 (H5-01) y el dueño de secuencia ya abierto en H3-04. El 13 es demostrable como restricción negativa, pero conviene fijar dónde `estado.json` representa las fuentes diferidas.
- **H4-04: cierra.** «Posterior a V3» conserva las dos precondiciones que rev. 5 había borrado.
- **H4-05: no cierra.** La spec confiesa que la enumeración/decisión del write-set sigue pendiente (H5-03).

### 2. Atomización local en V1

El atomizador escribe bajo `01_Procesado/Emails`: registro de IDs, mensajes e historiales, adjuntos binarios y sidecars, contenido extraído y su estado, corpus, dos índices, cola de revisión y vistas; además emite `atomizado_email`/`contenido_adjuntos` en el log. No descubre Gmail: solo recorre lotes locales y el cajón legacy. Tampoco llama a un LLM por defecto; el contenido de imágenes queda pendiente. La opción separada `sala_maquina --vision` admite un transcriptor inyectado, pero no forma parte del atomizador y su uso en V1 no está decidido.

La custodia de esos derivados no está cerrada: el evento no manifiesta sus hashes, no hay generación atómica, los fallos pueden publicar parcial y el OCR continúa, y la poda usa borrado. Los criterios 41/48 dicen que lo cubrirán sin definir cómo. No encontré una escritura remota directa en atomización, pero el entrypoint superior todavía puede exportar Gmail por `--fuente email` debido a H5-01.

### 3. Enumeración del write-set

No está completa «ahora». §21 enumera familias de deuda, no el write-set, y aplaza la clasificación artefacto por artefacto. Además de bytes de intake, manifest, log, `_caso.md` y `estado.json`, V1 toca controles/derivados de correo, contenido de adjuntos, OCR/split, coberturas, estados, tiempos, staging y archivo histórico. Tampoco adopta la prueba en cuatro planos de la arquitectura dual. H5-03 es bloqueo de **alcance**, no una reapertura de los protocolos H3 ya declarados abiertos.

### 4. Contabilidad de criterios

- **Conteo de conjuntos:** 24 V1 + 26 diferidos = 50, sin duplicados numéricos.
- **Partidos:** la parte V1 de 10/14/35/38 está descrita; las colas de 10 y 14 carecen de dueño explícito. 35 y 38 sí tienen fila, aunque 38 prueba la dirección equivocada (H5-04).
- **Globales:** 27 y 50 están correctamente globalizados. La intención de globalizar 38 es correcta; su predicado no.
- **Criterio 1:** semánticamente corregido, pero no demostrable hasta que exista marcador V1 y dueño ejecutable de la secuencia.
- **Criterio 13:** la prohibición de `completo` es observable; falta concretar la representación persistida de fuentes V2/V3 no consultadas para que no sea solo una constante del resumen.
- **Criterio 29:** correctamente posterior a V3.

### 5. Contradicciones nuevas o supervivientes

Las materiales son: la afirmación de write-set enumerado frente a su aplazamiento; la globalización invertida de 38; 24/26 frente al encabezado 22/28; y el cierre obsoleto de §21.6. La invariante reformulada es razonable si «mutaciones de datos/acciones de comunicación» se lee como **remotas**; literalmente, sin ese adjetivo, chocaría con una V1 que muta abundantes datos locales. La corrección mínima de redacción es «cero mutaciones remotas de datos del expediente y cero acciones remotas de comunicación», conservando la declaración expresa del refresh OAuth.

El movimiento del criterio 29 no contradice los contratos previos. El runbook conserva hoy comandos `--crm api` y `--fuente email`, pero §21 es una sustitución expresa para V1; por eso el plan deberá actualizar el runbook al introducir un modo V1 real, no fingir que esos comandos dejaron de existir globalmente.

### 6. Alcance comprobable y preparación para plan TDD

**No.** Rev. 6 todavía no deja el alcance V1 fijado de forma comprobable. Bloquean el **alcance** H5-01, H5-02, H5-03 y H5-04; H5-05 debe corregirse para que la asignación futura no mienta, aunque no altera el conjunto numérico V1.

Una vez cerrados esos puntos, seguirán bloqueando el **plan**, y no se reabren aquí: las tres decisiones de §20 —núcleo `CaseWorkspace`, primitiva/namespace de mutex y dueño de secuencia— y los contratos acotados de H3-03, H3-05 y H3-06. H3-07 no bloquea V1.

## Preguntas y limitaciones

1. ¿Qué discriminante concreto identifica V1 dentro del entrypoint compartido y en qué línea conceptual se valida antes de todo efecto? Sin esa decisión, H4-01 no tiene remedio implementable.
2. ¿Un fallo/parcial de atomización debe dejar V1 `bloqueado` o `preparado_con_pendientes`? Puede permitirse que el OCR continúe, pero el estado final y la generación consumible necesitan una regla única.
3. ¿`--vision` queda prohibido en V1, permitido como servicio remoto declarado o fuera del driver? El código permite inyectar un transcriptor Claude; la spec no lo decide. No se trata como hallazgo porque el default es `False` y el atomizador local no lo usa.
4. No se ejecutó red, no se verificaron efectos reales de OAuth/Drive/Sudespacho/Gmail ni condiciones de servicios externos: **SIN VERIFICAR** por mandato.
5. No se ejecutaron tests. La prueba dinámica queda **SIN VERIFICAR**; los hallazgos se sostienen por contradicción textual, alcanzabilidad estática y por contratos de tests existentes que fijan expresamente el fallo blando de atomización. No se instaló ninguna dependencia.

### Integridad final del objeto

| Artefacto | SHA-256 final |
|---|---|
| Spec rev. 6, bytes CRLF | `E2ED502B385622462CF19255D7CA8F67034E6FB404CC40A56F77ABF00160BD99` |
| Spec rev. 6, forma canónica LF | `0E147418B3EC12C98CA885205B16AEC5C783DAA1A8A9E72D2E21BB5D18F70C2E` |
| Acta R1 | `E30D9EF9EFABD1F822F9F67DB547217BB77C9C2FC9945BA1805F88ACA658A57F` |
| Acta R2 | `55A88365DC52656A9DBBE172F923BC288984BDAE7C58A1DFAE7215D885104032` |
| Acta R3 | `CC4B8653930F49FA2CAC6464EC4F45881935E7905B85F8E7F4BDDB96704FBD0C` |
| Acta R4 | `C345DE3F6CAB54191D70744D818806EA4D1B5028740CD217D8228CB42CEA82F3` |

Los valores iniciales y finales coinciden.

## Veredicto

**REQUIERE-REVISION.**

Conteo: **1 CRÍTICA · 3 ALTAS · 1 MEDIA**.

Rev. 6 toma decisiones correctas sobre la frontera local del correo, el criterio 29 y buena parte de H4-03, pero no convierte V1 en un modo reconocible, no incorpora el contrato observable de atomización y deja el write-set como tarea futura. La globalización invertida del criterio 38 repite además el patrón advertido: el remedio introduce un defecto nuevo al escribirlo. Las correcciones siguen acotadas al §21; después, y solo después, permanecen las decisiones y contratos H3 ya adjudicados que bloquean el plan TDD.
<!-- informe-literal:fin:zwqk -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-24)

Verificado contra la fuente. Rutas del árbol del commit `ce3ab5a`; las citas sin fichero son a
`2026-08-15-orquestador-apertura-expediente-design.md`.

**Custodia del informe.** `sha256` recomputado sobre la forma canónica del fichero recibido:
`A42EEBF9D066388BF977EB2B863F6532FA072B9047DFBA389AED5593EFE41879`, idéntico al declarado. Sin
BOM, un salto final. **Una precisión:** el revisor declara «LF puro» y el fichero está en disco en
**CRLF** (147 líneas, todas con CR). No afecta al digest —la canonicalización del §4 sustituye
CRLF por LF antes de hashear, y por eso el valor cuadra—, pero la afirmación de formato era
inexacta y se anota en vez de repetirse.

| Afirmación del informe | Comprobación |
|---|---|
| No existe marcador de ejecución V1 | `grep` de `modo_v1`, `MODO_V1`, `es_v1`, `V1_MODE`, `--v1` en `core/`, `scripts/`, `tests/`: **0 apariciones** |
| El mismo entrypoint alcanza Gmail | `scripts/abrir_caso.py:64`: `_FUENTES_CLI = ("drive_ev", "manual", "whatsapp", "email")`. `_intake_email` (`:194`) «exporta la etiqueta Gmail del caso a un lote nuevo de `00_Input`», por `email_export.export_label` |
| El criterio 38 dice la dirección contraria al defecto | `:972-973` literal: «Un caso **judicial** no pasa por los entrypoints **extrajudiciales**». El defecto citado como justificación es el inverso —default judicial en `core/sync_sudespacho.py:1356` y `scripts/sync_sudespacho.py:167`—, y mi propio §22 lo formula bien antes de que el remedio del §21.4 lo copiase al revés |
| El write-set se declara enumerado y se aplaza | `:1265` dice «el write-set se enumera»; `:1349` dice «V1 tiene una precondición nueva: enumerar su write-set completo»; `:1440` lo hace precondición de un bloque futuro |
| La cabecera del §14 está rancia | `:891-893` sigue diciendo «(rev. 4)», «veintidós» y «veintiocho» cuando el §21.4 dice veinticuatro y veintiséis |
| El cierre del §21.6 está obsoleto | Sigue diciendo «cuatro hallazgos que la **rev. 4** debe cerrar […] hasta que **R4 se corra** y se adjudique», con H3-07 incluido — cuando la tabla inmediatamente anterior lo declara fuera de V1 y el §22 ya adjudica R4 |
| El fallo blando de la atomización está fijado por test | `tests/test_sala_maquina_cableado_atomize.py:185` `test_fallo_del_motor_no_aborta_el_ocr_y_emite_evento`; `:213` `test_status_parcial_cuando_el_motor_termina_con_errores`, que acepta `publicado=True`, `poda_omitida=True` y `errores=[...]`. La semántica blanda es deliberada, no accidental |
| La poda borra en vez de archivar | `core/email_atomize/pipeline.py:220,267`: `p.unlink()` |

### Un hallazgo que el revisor no vio, y que también es mío

La **cabecera del §22 y su ficha se contradicen**: el encabezado canónico dice
`— REQUIERE-REVISION, pendiente` (`:1468`) y la ficha, dos líneas después, dice `**Remediado en:**
rev. 6 de este documento` (`:1475`). Lo introduje al remediar: cambié la ficha y no el
`estado_remediacion` del titular. Ningún guard lo detecta —G7 valida el **formato** del
encabezado y su vocabulario, no su acuerdo con la ficha—, y ninguna de las cinco rondas lo miró.
Un revisor que no lo ve no lo refuta: queda sin verificar, y aquí lo levanta el adjudicador.

### Lo que sigue sin verificar, y se declara

El revisor no ejecutó tests en esta ronda: la cobertura dinámica queda **SIN VERIFICAR** por su
parte, y sus hallazgos se sostienen por contradicción textual, alcanzabilidad estática y por
contratos de tests existentes —que sí verifiqué—. Siguen sin verificar por nadie, en las cinco
rondas: las condiciones y efectos reales de Google OAuth, Drive, Gmail y Sudespacho, que exigen red
y leer términos de servicio.
