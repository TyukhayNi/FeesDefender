---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
objeto_rev: "5"
commit: 806079c0aed817419256aea616a7ae1e9d08eb6c
ronda: "4"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: zqwk
sha256_informe: b210a1e7843ccb1a8ca17784680e5f4e08a83bb188dd0dcab986927d1947ac6f
adjudicado_en: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md §22
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R4.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el §22 del objeto, no aquí.
>
> **Objeto pequeño a propósito.** Esta ronda no revisa la spec entera: revisa el
> **estrechamiento** del §21 (rev. 4 y rev. 5). El mandato ordenó expresamente no redescubrir
> H3-03, H3-05, H3-06 ni las tres decisiones pendientes —están adjudicados en el §20— y sí decir
> si el estrechamiento les cambia la forma o describe falsamente su efecto. Se le dijo también que
> un informe corto con veredicto favorable era un resultado legítimo.
>
> **Montaje del revisor.** Codex leyó una copia externa del árbol completo del commit
> `806079c`, obtenida con `git archive`: el repositorio quedó de solo lectura **por
> construcción**, sin `.git` y sin red. La evidencia de no-mutación es el SHA-256 del objeto y de
> las tres actas previas al abrir y al cerrar.

## 0. Mandato (literal, tal como se entregó)

```text
MANDATO R4, NUMERADO POR DAÑO

OBJETO
- Spec: `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, **rev. 5**.
- Árbol a revisar: COPIA EXTERNA completa y de solo lectura por construcción, en
  C:\Users\tnm33\.codex\reviews\_arbol-r4-806079c
  Es el árbol íntegro del commit 806079c0aed817419256aea616a7ae1e9d08eb6c (rama codex/docs/apertura-integral-w02q38c, PR #225), obtenido con `git archive`. Incluye core/, scripts/, tests/, docs/, CLAUDE.md y AGENTS.md. No tiene `.git`: no hay nada que ensuciar y no necesitas git para revisar.
- Digests del objeto: en la copia el fichero está en CRLF y su SHA-256 es
  4F311A393880EDFF0AC9610FED770CD202913FE76DACBA1C561C36A2F4FE9567.
  Su forma canónica (normalizada a LF) es
  3AA336272A2E369CC711A46C329B7D55219F2DB0D05A9F925E86D40CE7E3DB17.
  Verifica los dos al arrancar y decláralo. La discrepancia entre ambos es el final de línea, no un hallazgo.
- Actas previas, en la misma copia: `docs/superpowers/specs/2026-08-15-apertura-integral-r{1,2}-adversarial-review.md` y `2026-08-24-apertura-integral-r3-adversarial-review.md`. Adjudicaciones: §§18, 19 y **20** del objeto.
- Contrato de gobernanza de revisiones: `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`, en la misma copia.

QUÉ HA CAMBIADO, Y POR TANTO QUÉ SE REVISA
R3 devolvió NO-SHIP con siete hallazgos, adjudicados por Claude Code contra la fuente (§20). La rev. 4 y la rev. 5 **NO remedian** esos hallazgos: hacen una sola cosa, **estrechar el alcance de la primera vertical**, en el §21 nuevo. V1 = identidad → esqueleto → Drive E&V + pull de Sudespacho → intake con custodia → sala de máquina, con `--crm skip` obligatorio.

**El objeto de esta ronda es el estrechamiento, no la spec entera.** Tres hallazgos de R3 siguen deliberadamente abiertos —H3-03 acotado, H3-05 y H3-06— y tres decisiones de Nikolai están pendientes (§20: predecesor `CaseWorkspace`, primitiva y namespace del mutex, dueño ejecutable de la secuencia). NO gastes la ronda redescubriéndolos: están adjudicados y declarados. Sí debes decir si el estrechamiento **cambia su forma**, los **agrava**, o si alguna afirmación de acotamiento es **falsa**.

1. Ataca la invariante que sostiene todo el estrechamiento: «V1 no escribe en ningún servicio externo, y el pull de Sudespacho entra porque es una LECTURA» (§21.2). Contra el CÓDIGO REAL de la copia: ¿`pull_expediente_v2` y todo lo que V1 invoca son de verdad libres de efectos remotos no idempotentes? Busca cualquier escritura, mutación, marca de leído, registro remoto, side effect de autenticación o acción de comunicación en el camino de V1. Si la invariante es falsa, el estrechamiento no reduce H3-03 y hay que decirlo.
2. Ataca el reparto de criterios del §21.4 y la tabla del §21.3: 22 criterios en V1, 28 diferidos, 27 y 50 como restricciones globales. ¿Hay algún criterio que V1 NECESITA y que está diferido —es decir, un agujero por el que V1 podría quedarse verde sin demostrar algo que sí ejerce—? ¿Hay alguno en V1 que sea indemostrable dentro de V1 porque su precondición se fue con otra vertical? ¿Y algún criterio cuya versión «parcial» en V1 (10, 14, 34) pueda pasar sin cubrir lo que su enunciado promete?
3. Ataca la frontera de V1 contra las verticales diferidas. «Diferido no derogado» es la regla declarada: ¿la cumple el texto, o hay algún contrato que en la práctica quede sin dueño porque su sección lo daba por hecho en la fase que ahora sale? Mira en particular la sala de LECTURA fuera y la sala de máquina dentro, y la viabilidad fuera con el intake dentro.
4. Ataca lo que V1 arrastra del código actual y no del diseño: la deuda que el §21.2 declara absorbida (`MEJORAS #120`, el registro de ocurrencias que se persiste antes de `guard_escritura`), y cualquier otra escritura del camino de V1 que hoy esquive el guard de escritura, no hashee, no registre evento, o toque `90_Notas personales/`. ¿Está la lista completa, o V1 hereda más deuda de la que declara?
5. Verifica la honestidad de las declaraciones del §21: que V1 «respeta el gotcha del runbook» (pull antes de la sala de máquina), que el correo fuera implica `fuentes_pendientes` y nunca `completo`, y que la tabla del §21.6 describe correctamente el efecto sobre los siete hallazgos —en especial que H3-07 esté de verdad fuera de alcance y que H3-01, H3-02, H3-04 y H3-05 sigan íntegros.
6. Decide: ¿es V1, tal como la fija la rev. 5, un alcance sobre el que se pueda escribir un plan TDD **una vez tomadas las tres decisiones del §20**? SHIP / LISTA-CON-CAMBIOS / REQUIERE-REVISION / NO-SHIP. Distingue lo que bloquea el ALCANCE de lo que bloquea el PLAN. No diseñes un motor mayor ni amplíes el encargo.

CONTRATO ESTRICTO
- Trabaja SOLO sobre la copia externa. No toques `C:\Users\tnm33\Dev\FeesDefender` ni `C:\Users\tnm33\Dev\FeesDefender-crm` ni ningún sistema externo. No hay red. Si intentas un comando git contra esos repos fallará por propiedad del directorio: es deliberado, no lo sortees.
- La copia es el objeto de registro. No la modifiques. Al arrancar y al terminar calcula el SHA-256 del objeto y de las TRES actas previas: deben coincidir. Incluye esa evidencia en el informe: sustituye al `git status` limpio.
- No lances subagentes. Haz las pasadas necesarias tú mismo.
- Si ejecutas tests, hazlo sobre una copia tuya bajo tu directorio de trabajo o el temporal, con `PYTHONDONTWRITEBYTECODE=1`, `pytest -p no:cacheprovider` y `--basetemp` en ruta CORTA. Nota: el entorno de revisión puede carecer de `python-dotenv`, y sin él cualquier test que importe `core.config` falla en setup. Si ocurre, declara la cobertura dinámica SIN VERIFICAR; no la finjas ni instales nada.
- Contrasta contra el código real y las fuentes completas, no contra el diff ni contra la seguridad con que esté redactada la spec.
- Hallazgos numerados H4-01, H4-02… ordenados por severidad y daño. Cada uno: severidad, `file:line` preciso, hecho, impacto, evidencia o reproducción, y corrección mínima. No infles nitpicks. Si el estrechamiento es sólido, dilo: un informe corto con un veredicto favorable es un resultado legítimo, y esta ronda tiene un objeto pequeño a propósito.
- Secciones obligatorias: Identificación y alcance; Fortalezas; Hallazgos; Respuesta al mandato 1-6 punto por punto; Preguntas y limitaciones; Veredicto. TÚ NO ADJUDICAS: adjudica Claude Code contra la fuente. Lo que no puedas verificar, dilo como SIN VERIFICAR.
- Escribe el informe ÚNICAMENTE en: C:\Users\tnm33\.codex\reviews\2026-08-24-apertura-integral-r4\2026-08-24-apertura-integral-r4-adversarial-review.md
- Ese fichero no existe: no sobrescribas ningún informe previo. Formato canónico: UTF-8 sin BOM, finales LF, exactamente un salto final.
- Devuelve en el mensaje final: ruta exacta, SHA-256 canónico del informe, conteo de hallazgos por severidad, veredicto, lista breve de hallazgos y los digests del objeto y de las tres actas antes y después. Sin ruta y digest la revisión no cuenta.
```

## 1. Informe recibido de Codex, sin modificar

Digest declarado por el revisor y verificado de forma independiente al recibirlo, contra
`C:\Users\tnm33\.codex\reviews\2026-08-24-apertura-integral-r4\2026-08-24-apertura-integral-r4-adversarial-review.md`:
B210A1E7843CCB1A8CA17784680E5F4E08A83BB188DD0DCAB986927D1947AC6F.

<!-- informe-literal:inicio:zqwk -->
# Revisión adversarial R4 — estrechamiento de apertura integral rev. 5

## Identificación y alcance

- **Objeto:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, rev. 5, commit archivado `806079c0aed817419256aea616a7ae1e9d08eb6c`.
- **Copia revisada:** `C:\Users\tnm33\.codex\reviews\_arbol-r4-806079c`, sin `.git`, completa y tratada como solo lectura.
- **Alcance de R4:** únicamente el estrechamiento de §21: V1 = identidad → esqueleto → Drive E&V + pull Sudespacho → intake con custodia → sala de máquina, con `--crm skip` obligatorio. No se reabren H3-01, H3-02, H3-03, H3-04, H3-05, H3-06 ni H3-07 salvo para comprobar si §21 cambia su forma o describe falsamente su efecto.
- **Rol:** revisor adversarial. Este informe no adjudica; adjudica Claude Code contra las fuentes.
- **Gobernanza aplicada:** informe separado de la adjudicación, vocabulario cerrado y toda cobertura no ejecutada declarada `SIN VERIFICAR`.

### Integridad del objeto

Hashes calculados antes de leer el objeto:

| Artefacto | SHA-256 inicial |
|---|---|
| Spec rev. 5, bytes CRLF | `4F311A393880EDFF0AC9610FED770CD202913FE76DACBA1C561C36A2F4FE9567` |
| Spec rev. 5, forma canónica LF | `3AA336272A2E369CC711A46C329B7D55219F2DB0D05A9F925E86D40CE7E3DB17` |
| Acta R1 | `E30D9EF9EFABD1F822F9F67DB547217BB77C9C2FC9945BA1805F88ACA658A57F` |
| Acta R2 | `55A88365DC52656A9DBBE172F923BC288984BDAE7C58A1DFAE7215D885104032` |
| Acta R3 | `CC4B8653930F49FA2CAC6464EC4F45881935E7905B85F8E7F4BDDB96704FBD0C` |

La diferencia entre los dos hashes de la spec es exclusivamente CRLF frente a LF y no es un hallazgo. La comprobación final figura en «Preguntas y limitaciones».

## Fortalezas

1. El reparto es aritméticamente exacto: §21.4 enumera 22 criterios distintos y los 28 restantes aparecen una vez en la tabla de §21.3.
2. `pull_expediente_v2` no entra en el fallback legacy: construye `SudespachoClient`, lista mediante `GET /api/element_registries/gdocu` y obtiene/descarga URLs mediante GET (`core/sync_sudespacho.py:1433-1452,1541-1544`; métodos en `:627-846`). La ruta legacy que renueva JWT por POST está en otro cliente y no la invoca V2 (`core/sync_sudespacho_legacy.py:232-296`).
3. §21 conserva como globales 27 y 50, mantiene expresamente H3-01, H3-02 y H3-05, y no intenta presentar H3-03/H3-06 como remediados.
4. La sala de lectura y la viabilidad se nombran como diferidas, no como eliminadas. H3-07 está realmente fuera del camino V1 descrito: no hay adaptador postal en identidad, pulls, intake o sala de máquina.
5. El orden deseado Sudespacho antes de sala de máquina coincide con el gotcha del runbook (`docs/RUNBOOK_APERTURA_EXPEDIENTE.md:198-213`). El defecto está en la frontera del correo, no en esa precedencia CRM → OCR.

## Hallazgos

### H4-01 — CRÍTICA — `--crm skip` no es una invariante ejecutable de V1 y el entrypoint compartido conserva un POST remoto por defecto

- **Severidad:** CRÍTICA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1302-1307,1346-1354,1370-1374`; `scripts/abrir_caso.py:265-300,381,479-499`; `core/sudespacho_create.py:1462-1489,1652-1724`.
- **Hecho:** §21 sostiene que *toda* invocación V1 usa `--crm skip`, pero no crea un modo V1 ni un gate que lo haga cierto. El entrypoint que §21.5 ordena ampliar sigue declarando `--crm` con default `api` (`scripts/abrir_caso.py:381`), llama siempre a `_alta_crm` al final (`:497`) y, salvo `skip`, alcanza `create_expediente` (`:274-300`), cuya ruta REST ejecuta un POST de creación. El criterio 34 solo exige `--crm skip` para **intake incremental**; la apertura nueva de V1 queda fuera de esa prueba. El E2E de §21.5 pasa el flag feliz, pero no demuestra que omitirlo o usar `api` sea imposible dentro de la ruta V1.
- **Impacto:** una implementación puede dejar verdes los 22 criterios y conservar una ruta de V1 que crea un expediente extrajudicial remoto. Eso refuta la invariante operativa «V1 no escribe en ningún servicio externo» y devuelve a H3-03 una frontera POST con resultado remoto desconocido. También convierte la reducción de H3-04 en dependiente de una convención del llamador que todavía no tiene dueño.
- **Evidencia o reproducción:** cadena estática actual: `scripts.abrir_caso.main(crm="api")` → `_alta_crm(..., crm_mode="api")` → `sudespacho_create.create_expediente(...)` → `_rest_post(...)`/fallback legacy POST. No hace falta red para demostrar la alcanzabilidad. La prueba negativa que falta es invocar la secuencia V1 sin el flag y afirmar que no existe ninguna llamada a `create_expediente` ni a un método HTTP mutante.
- **Corrección mínima:** definir cómo se reconoce una ejecución V1 y hacer que ese camino fuerce/rechace técnicamente cualquier modo distinto de `skip`, tanto en caso nuevo como incremental. Añadir al reparto un criterio negativo: omitir `--crm skip` o pedir `--crm api` en V1 aborta antes de cualquier efecto, y un spy acredita cero llamadas a alta/ficha/relaciones remotas.

### H4-02 — ALTA — La sala de máquina que entra en V1 también ejecuta atomización de correo, aunque §21 y sus criterios la dejan fuera

- **Severidad:** ALTA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1325-1342,1346-1350,1385-1388`; `scripts/sala_maquina.py:291-355,472-497`; `core/email_atomize/pipeline.py:86-272`.
- **Hecho:** el entrypoint vigente `sala_maquina apply` llama siempre a `_atomizar_correo` y `_procesar_adjuntos` antes de construir el plan OCR (`scripts/sala_maquina.py:488-497`). Si el caso existente contiene `.eml` o un árbol previo, `atomize_dir` escribe mensajes, adjuntos, corpus, índices y vistas, y poda derivados huérfanos (`core/email_atomize/pipeline.py:130-272`). §21 difiere «Descubrimiento y etiquetado de Gmail» y afirma que el correo es la mitad ausente del gotcha, pero no decide si la **atomización local** queda dentro ni ofrece un modo de sala de máquina que la omita. Los parciales 10 y 14 excluyen Gmail/correo de la evidencia específica.
- **Impacto:** V1 puede modificar `01_Procesado/Emails` y su log sin que el alcance ni el reparto prueben frescura, crash/reanudación o retirada de esos derivados. H3-03 sigue local, pero su superficie ya no es solo Drive/CRM → sala de máquina; H3-05/H3-06 reciben una tercera fotografía local potencial que §21 no contabiliza. Alternativamente, cambiar el entrypoint para saltarla puede romper el contrato vigente de la sala de máquina sin criterio de no regresión.
- **Evidencia o reproducción:** la llamada es incondicional en `scripts/sala_maquina.py:491-492`; solo el no-op interno «sin correo y sin árbol previo» evita la escritura. Un caso existente con un lote `*_email_*` ejerce el camino aunque V1 no descubra Gmail.
- **Corrección mínima:** escoger y escribir una de dos fronteras: (a) V1 invoca una modalidad explícita de sala de máquina que no atomiza correo y registra la fuente como pendiente; o (b) V1 incluye **atomización local de correo existente**, no descubrimiento Gmail, y añade sus artefactos, generación, crash points y poda a 10/14/41/48. No hace falta meter Gmail remoto en V1.

### H4-03 — ALTA — El reparto 22/28 permite un V1 verde que se declara completo y difiere una no regresión que V1 ejerce

- **Severidad:** ALTA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:135-142,895-920,946-969,1322,1339-1354`; `scripts/abrir_caso.py:308-352,363-428`.
- **Hecho:** hay tres agujeros relacionados en el contrato de aceptación:
  1. El criterio 1, exigido íntegro en V1, promete que la secuencia «completa una apertura normal», mientras §21.3 ordena que V1 nunca sea `completo` si falta correo. Es indemostrable literalmente dentro de V1.
  2. El criterio 13 solo exige usar uno de los tres tokens de §13; permite `completo`. `fuentes_pendientes`, citado como la garantía en §21.3, no forma parte del enum de fuentes/fases de §10 ni de los tres estados finales de §13 y solo aparece en §21 y `PLAN.md`.
  3. El criterio 35 se difiere entero a V2 aunque V1 modifica el mismo `scripts.abrir_caso` y ejerce directamente dos de sus capacidades: `--case-id` y autodetección desde `folder-id`. La regla global de §3 prohíbe regresarlas, pero V1 puede quedar verde sin probarlas.
- **Impacto:** el plan no puede convertir los criterios en tests sin elegir entre contratos contradictorios, y una suite razonable puede certificar un cierre total falso o introducir una regresión en el entrypoint compartido.
- **Evidencia o reproducción:** búsqueda completa del árbol: `fuentes_pendientes` solo aparece en la spec `:1342` y `PLAN.md:98`; no existe en el esquema de `estado.json` (`docs/...design.md:675-780`). El código actual contiene las capacidades diferidas en `scripts/abrir_caso.py:308-352,363-428`.
- **Corrección mínima:** sustituir la versión V1 del criterio 1 por «completa la secuencia V1 y termina `preparado_con_pendientes`»; definir dónde se representa cada fuente V2/V3 pendiente y añadir `resultado != completo`; dividir 35 y conservar en V1, al menos, `--case-id` y la autodetección que el bloque de cableado toca.

### H4-04 — ALTA — El criterio 29 pierde sus precondiciones V3 al asignarse a V2

- **Severidad:** ALTA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:498-503,950-951,1323-1332`.
- **Hecho:** la fuente completa exige que la fase 8.1 espere Drive, sala de máquina, **sala de lectura** y viabilidad completada/no aplicable. §21.3 manda sala de lectura y viabilidad a V3, pero asigna criterio 29 a V2 y afirma que «su precondición pasa a ser el cierre de V1». Esa sustitución elimina dos precondiciones explícitas; no es un mero diferimiento.
- **Impacto:** V2 puede crear/actualizar la ficha del contrario antes de la lectura documental y la viabilidad, exactamente el daño que §§5.1 y 8.1 bloquean. El contrato queda sin dueño si V2 se ejecuta antes de V3; si V2 debe esperar a V3, su criterio es indemostrable en V2.
- **Evidencia o reproducción:** contraste textual directo entre criterio 29 (`:950-951`), filas V3 (`:1327-1328`) y fila de criterio 29 (`:1332`).
- **Corrección mínima:** declarar que el cierre de V1 es necesario pero no suficiente. V2 puede construir DTOs/adaptadores, pero la **ejecución** de fase 8.1 y el criterio 29 pertenecen a una integración posterior a V3, o V3 debe preceder al gate final de V2. No ampliar V1.

### H4-05 — ALTA — La deuda absorbida no se limita a `MEJORAS #120`: los caminos V1 actuales publican controles y derivados fuera del guard o sin custodia coherente

- **Severidad:** ALTA.
- **Ubicación:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:1286-1314`; `core/intake_drive.py:192-198,305-324`; `core/case_manager.py:215-285,347-376,381-425`; `core/sync_sudespacho.py:1462-1495,1502-1667`; `core/intake_manifest.py:149-203`; `core/intake_log.py:151-205`; `scripts/abrir_caso.py:108-112`; `scripts/sala_maquina.py:39-42,79-180,491-590`.
- **Hecho:** el registro de ocurrencias anterior al guard es real, pero no es la lista completa:
  - Drive desvía los bytes mediante `dir_intake`, pero tras éxito llama incondicionalmente a `register_drive_ev`, que reescribe el `_caso.md` canónico sin la decisión del guard (`core/intake_drive.py:321-324`; `core/case_manager.py:393-425`). El wrapper después hashea el cajón canónico, no el `target_dir` efectivo (`scripts/abrir_caso.py:108-112`), por lo que un desvío puede quedar sin el evento/hashes de los bytes realmente depositados.
  - Sudespacho llama al guard una vez para los bytes, pero `IntakeManifest` sigue ligado al path canónico y guarda allí (`core/intake_manifest.py:149-203`); después `update_pull_state` y todos los `_log_event` escriben también en controles canónicos. Algunas pueden ser exenciones de protocolo legítimas, pero ninguna pasa `es_protocolo=True` ni §21 las clasifica. El manifest puede afirmar una ruta viva mientras los bytes están en `_pendiente_checkin`.
  - `sala_maquina apply` y su atomizador escriben estado, cobertura, tiempos, derivados y log sin llamar al guard actual.
  - `ensure_case` no es el «esqueleto mínimo» de §21: crea `Sala lectura`, `02_Analisis`, `90_Notas personales/` y copia/prerrellena plantillas de viabilidad (`core/case_manager.py:270-285,347-376`), aunque esas verticales y sus criterios están diferidos.
- **Impacto:** cerrar solo #120 deja posibles escrituras en un caso prestado, manifest/custodia divergentes y artefactos de verticales diferidas. Los criterios 36 y 41 son amplios, pero una prueba que mire solo los PDFs —como la caracterización vigente de CRM en `tests/test_guard_intake_wiring.py:123-139`— puede quedar verde con los controles canónicos alterados.
- **Evidencia o reproducción:** las rutas anteriores forman el write-set estático. La prueba dinámica dirigida no pudo ejecutarse por ausencia de `python-dotenv`; queda `SIN VERIFICAR`, no refutada.
- **Corrección mínima:** antes del plan, enumerar el write-set V1 y decidir para cada artefacto: bloqueado, publicado bajo el mutex o exento como protocolo por contrato explícito. El E2E de workspace no disponible debe comparar el árbol completo byte a byte y acreditar cero cambios; la prueba de custodia debe seguir el destino efectivo y exigir bytes → hash → manifest → evento coherentes. El inicializador V1 debe ser realmente mínimo sin ejecutar contratos V2/V3.

## Respuesta al mandato 1–6

### 1. Invariante de cero escrituras externas

`pull_expediente_v2` en sí es lectura de negocio: usa API key estática y GET; no alcanza el cliente legacy ni sus POST de refresh. La descarga Drive también es remota→local. Sin embargo, la invariante de **V1 completa** es falsa como propiedad ejecutable mientras H4-01 siga abierto: el entrypoint dueño conserva `crm=api` por defecto y una ruta POST alcanzable.

Hay además efectos de autenticación que la frase absoluta «no escribe en ningún servicio externo» oculta. El preflight de Drive puede ejecutar `rclone about gdrive_ev:` para usar el refresh token, emitir un access token nuevo y reescribir `rclone.conf` (`core/intake_drive.py:457-466,513-540`). Es un efecto del servicio de autenticación y una escritura local fuera del caso, pero no una mutación de datos de Drive ni un efecto de negocio que H3-03 deba reconciliar por expediente. Sudespacho emite URLs prefirmadas mediante GET (`core/sync_sudespacho.py:745-846`); si el servidor crea auditoría u otro estado interno no es verificable sin red. Corrección de honestidad: formular la invariante como «cero mutaciones de datos/acciones de comunicación y cero efectos remotos no idempotentes del caso», declarar refresh/auditoría, y probar la allowlist de métodos. Con H4-01 cerrado, el estrechamiento sí reduce H3-03 a publicación local; sin cerrarlo, no.

### 2. Reparto de criterios

- Conteo: **22 V1 / 28 diferidos**, correcto.
- Criterios necesarios pero diferidos: la parte V1 de 35; además, si «rama judicial bloqueada» debe ser propiedad del mismo entrypoint V1, la parte negativa de 38 debe incorporarse o quedar expresamente global. Hoy el core pull tiene default judicial (`core/sync_sudespacho.py:1356`) y el CLI pull también (`scripts/sync_sudespacho.py:167`), por lo que no conviene confiar en la ausencia de uso.
- Criterio indemostrable en V1: 1 en su redacción «completa una apertura normal».
- Parciales:
  - 10 omite correctamente consultas Gmail/LeadHub, pero no cubre la atomización local que el entrypoint de máquina sí ejecuta (H4-02).
  - 14 limita crashes a fronteras locales, lo cual es correcto solo después de H4-01; debe incluir atomización si se mantiene dentro.
  - 34 conserva el pull preexistente antes de máquina, pero su cláusula `--crm skip` solo habla de incremental y no protege la apertura nueva (H4-01).
- Criterio 13 permite el falso `completo`; `fuentes_pendientes` no tiene esquema (H4-03).

### 3. Frontera con verticales diferidas

No se cumple por completo «diferido no derogado»:

- sala de lectura fuera / sala de máquina dentro es viable en abstracto, pero el inicializador actual crea scaffolding de sala de lectura y la sala de máquina arrastra atomización de correo; §21 no fija esas costuras;
- intake dentro / viabilidad fuera también es viable, pero `ensure_case` actual copia y prerrellena el informe de viabilidad;
- la fase 8.1 pierde sala de lectura y viabilidad al pasar criterio 29 a V2 (H4-04).

La corrección no exige ampliar V1: exige impedir que sus entrypoints ejecuten verticales diferidas y conservar sus gates para cuando entren.

### 4. Deuda actual absorbida por V1

La lista de §21.2 no es completa. Además de `MEJORAS #120`, entran al menos: registro Drive de IDs en `_caso.md` tras desviar bytes; hash/log de Drive calculado contra el cajón equivocado; manifest, estado y log canónicos del pull CRM que no consumen la decisión del guard; todas las publicaciones de sala de máquina/atomización; y el scaffolding/plantillas no mínimos de `ensure_case`. H4-05 detalla líneas y corrección.

Sobre custodia: los bytes CRM se hashean antes de escribir (`core/sync_sudespacho.py:1538-1575`) y las ocurrencias materializadas conservan SHA/ruta (`:1616-1635`), que es una base buena. El hueco es la coherencia transaccional y de destino efectivo, no ausencia total de hash. No encontré un camino V1 que lea o escriba contenido bajo `90_Notas personales/`; sí encontré su creación eager por el esqueleto actual, incompatible con el literal «nunca tocada» si `mkdir` cuenta como toque.

### 5. Honestidad de §21 y efecto sobre R3

- **Gotcha del runbook:** Sudespacho antes de sala de máquina, sí. «Atomizar correo antes de `apply`», no en el código vigente: `apply` lo hace dentro. El texto necesita distinguir adquisición, atomización y OCR.
- **Correo fuera → no completo:** intención correcta, demostración ausente. `fuentes_pendientes` no está definido y 13 permite `completo`.
- **H3-01:** íntegro, correctamente declarado.
- **H3-02:** íntegro, correctamente declarado.
- **H3-03:** acotado solo condicionalmente. H4-01 mantiene alcanzable un POST; H4-02 ensancha la publicación local. Cerrados ambos, queda local.
- **H3-04:** íntegro. «Pero menor» es razonable frente a la vertical ancha, aunque la fila `:1386` lo reduce demasiado a «llame a sala de máquina»: el CLI actual acepta una sola fuente (`scripts/abrir_caso.py:64,248-260`) y no llama ni al pull ni a máquina, por lo que el dueño debe coordinar Drive + registro/pull CRM + máquina + rondas. §21.5 lo describe mejor que §21.6.
- **H3-05:** íntegro y agravado a dos fuentes, correctamente declarado.
- **H3-06:** acotado a dos fuentes, no remediado; descripción honesta.
- **H3-07:** fuera de alcance de V1; ninguna ruta examinada invoca Correos/Catastro o retención postal.

### 6. Preparación para plan TDD

**No**, la rev. 5 no fija todavía un alcance sobre el que pueda escribirse un plan TDD únicamente tomando las tres decisiones de §20.

Bloquean el **alcance**: enforcement de `--crm skip` (H4-01), frontera de atomización (H4-02), contrato de aceptación/estado (H4-03), propiedad temporal de fase 8.1 (H4-04) y write-set absorbido (H4-05). Son correcciones acotadas al §21; no requieren diseñar un motor mayor.

Bloquean el **plan**, aun después de corregir el alcance: las tres decisiones de Nikolai sobre `CaseWorkspace`, primitiva/namespace del mutex y dueño de secuencia, más los contratos concretos todavía abiertos de H3-03 acotado, H3-05 y H3-06. H3-07 no bloquea V1.

## Preguntas y limitaciones

1. ¿«Correo fuera de V1» significa solo descubrimiento/exportación Gmail, o también la atomización local que hoy forma parte de `sala_maquina apply`? §21 necesita una respuesta binaria.
2. ¿V2 puede cerrarse antes de V3? Si sí, criterio 29 no puede estar en V2; si no, debe declararse el gate V3 → fase 8.1.
3. ¿`fuentes_pendientes` es un campo agregado nuevo, un alias de `preparado_con_pendientes` o una colección de fuentes con estados existentes? Hoy no tiene esquema.
4. Las condiciones y efectos reales de Google OAuth, Google Drive, Sudespacho y URLs prefirmadas quedan **SIN VERIFICAR** sin red. El análisis de métodos y alcanzabilidad sí está verificado contra el código de la copia.
5. Se intentó ejecutar, sobre copia temporal y con `PYTHONDONTWRITEBYTECODE=1`, `pytest -p no:cacheprovider --basetemp ... tests/test_guard_intake_wiring.py::test_crm_pull_prestado_desvia_a_bandeja tests/test_sala_maquina_cableado_atomize.py -q`. La colección falló al importar `core.config` por `ModuleNotFoundError: No module named 'dotenv'`. No se instaló nada. Cobertura dinámica: **SIN VERIFICAR**.

### Integridad final del objeto

Hashes recalculados al terminar la revisión:

| Artefacto | SHA-256 final |
|---|---|
| Spec rev. 5, bytes CRLF | `4F311A393880EDFF0AC9610FED770CD202913FE76DACBA1C561C36A2F4FE9567` |
| Spec rev. 5, forma canónica LF | `3AA336272A2E369CC711A46C329B7D55219F2DB0D05A9F925E86D40CE7E3DB17` |
| Acta R1 | `E30D9EF9EFABD1F822F9F67DB547217BB77C9C2FC9945BA1805F88ACA658A57F` |
| Acta R2 | `55A88365DC52656A9DBBE172F923BC288984BDAE7C58A1DFAE7215D885104032` |
| Acta R3 | `CC4B8653930F49FA2CAC6464EC4F45881935E7905B85F8E7F4BDDB96704FBD0C` |

Los valores iniciales y finales coinciden.

## Veredicto

**REQUIERE-REVISION.**

El estrechamiento es conceptualmente útil y, si se hace ejecutable el `skip`, puede reducir H3-03 a efectos locales y dejar H3-07 fuera. La rev. 5 todavía no delimita de forma comprobable ese V1: el entrypoint conserva una salida POST, la máquina arrastra correo, el estado final y varios criterios permiten un verde falso, una precondición V3 se pierde en V2 y la deuda de guard/custodia declarada no cubre el write-set real. Las correcciones son locales a §21; después deben tomarse las tres decisiones de §20 y cerrarse H3-03/H3-05/H3-06 antes del plan TDD.
<!-- informe-literal:fin:zqwk -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-24)

Verificado contra la fuente, no contra el informe. Rutas del árbol del commit `806079c`; las citas
sin fichero son a `2026-08-15-orquestador-apertura-expediente-design.md`.

**Custodia del informe.** `sha256` recomputado sobre el fichero recibido:
`B210A1E7843CCB1A8CA17784680E5F4E08A83BB188DD0DCAB986927D1947AC6F`, idéntico al declarado. LF
puro, sin BOM, un salto final. Los digests del objeto y de las tres actas previas coinciden al
abrir y al cerrar según declara el revisor.

| Afirmación del informe | Comprobación |
|---|---|
| `--crm` tiene default `api` | `scripts/abrir_caso.py:381`: `crm: str = typer.Option("api", "--crm", help="api|skip")` |
| `_alta_crm` se llama siempre y solo `skip` corta | `scripts/abrir_caso.py:497` incondicional; `:275-276` retorna temprano solo `if crm_mode != "api"` |
| La ruta alcanza `create_expediente` | `scripts/abrir_caso.py:298` |
| `sala_maquina apply` atomiza correo siempre | `scripts/sala_maquina.py:491-492`: `_atomizar_correo(...)` y `_procesar_adjuntos(...)` incondicionales, con el comentario «atomizar ANTES del OCR (spec §4)» |
| `fuentes_pendientes` no tiene esquema | `grep` en todo el árbol: **dos apariciones**, `:1342` y `PLAN.md:98`, ambas escritas hoy por mí. No está en los tres estados del §13 (`completo`, `preparado_con_pendientes`, `bloqueado`) ni en los enums del §10 |
| El criterio 29 exige sala de lectura y viabilidad | `:950-951`, literal. Mi fila del §21.3 lo manda a V2 diciendo «su precondición pasa a ser el cierre de V1», y las dos precondiciones se van a V3 |
| `ensure_case` no es un esqueleto mínimo | `core/case_manager.py:277-278` crea `01_Procesado/Sala lectura`; `:347-376` copia `_INFORME_TEMPLATE` y `_cuestionario_viabilidad.xlsx`. Ambas verticales están diferidas |
| `register_drive_ev` se llama sin consultar la decisión del guard | `core/intake_drive.py:321-323`: `if returncode == 0: register_drive_ev(...)` |
| El hash de Drive se calcula contra el cajón canónico | `scripts/abrir_caso.py:110-111`: `hash_tree_local(case_dir / "00_Input" / subdir, ...)`, no contra el destino efectivo |
| `90_Notas personales` se crea eager | `core/config.py:473-483` la incluye en `CASO_SUBDIRS`; `core/case_manager.py:273-274` hace `mkdir`. `core/config.py:470-472` documenta que la creación eager es deliberada |
| El pull tiene default judicial | `core/sync_sudespacho.py:1356` `element: str = "expedientes_judiciales"`; `scripts/sync_sudespacho.py:167` `elem = element or "expedientes_judiciales"` |

### Un dato que el informe no recoge, y que matiza sin salvar

Antes del POST hay **puerta humana**: `scripts/abrir_caso.py:293` exige `yes or
typer.confirm("¿Dar de alta en el CRM?")`. Así que una escritura remota accidental en V1 necesita
el default `api` **más** un sí interactivo o `--yes`.

Eso baja la probabilidad y **no** salva la invariante, por dos razones. La alcanzabilidad estática
es la que sostiene el hallazgo, y sigue intacta. Y la dirección de la propia spec disuelve la
mitigación: el §21.5 ordena ampliar este mismo entrypoint hasta ser dueño de la secuencia, y el §1
promete trabajo mecánico sin supervisión — un driver no interactivo pasa `--yes` por construcción.
La puerta protege hoy al operador que teclea; no protegerá al driver que la spec pide.

### Lo que sigue sin verificar, y se declara

La cobertura dinámica dirigida (`tests/test_guard_intake_wiring.py`,
`tests/test_sala_maquina_cableado_atomize.py`) quedó **SIN VERIFICAR** para el revisor por
`ModuleNotFoundError: dotenv`. **Ejecutada aquí** con el venv del repo; el resultado consta en el
§22. Siguen sin verificar por nadie, en esta ronda y en todas: las condiciones reales de Google
OAuth, Drive, Sudespacho y sus URLs prefirmadas, que exigen red y leer términos de servicio.
