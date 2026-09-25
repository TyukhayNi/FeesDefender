---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md
objeto_rev: "1"
commit: 7c70b70
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: vi6h
sha256_informe: e388cc184c380660b02ed9008f42ac7544f70162a059786f7d2828d2038c7a93
adjudicado_en: docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md §6
---

# Acta — R1 adversarial sobre el DIFF del bloque 1 de «mejoras de las aperturas de la semana»

Objeto: el **diff** `9880165..7c70b70` —12 ficheros, +1.072 / −40—: `MEJORAS #236` (las
marcas invisibles en las referencias de adjuntos de WhatsApp), `#285` (una sola regla de
«fichero de chat» para intake, manifiesto y atomizador) y `verificar_apertura` C2, C3 y C9
(`#268`, `#269`, `#218`).

**Una ronda, que es la que la tabla de `CLAUDE.md` asigna:** diff no trivial y acotado, sin
fronteras de escritura ni concurrencia. Fila de modelo ordinaria, `gpt-6-sol` · `high`, y por eso
es la **primera fila del ledger de calibración** de la fila #38 de `PLAN.md`. En la sesión se
llamó «R1»; la ronda de `#276` que corrió en paralelo tiene su propia acta.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.3` (binario `80f78947ad880e6e`), `gpt-6-sol` · `high` — **releídos** del `turn_context` de `rollout-2026-09-25T15-55-03-01a0d8d9-….jsonl` (`originator: codex_exec`); velocidad `default` **afirmada** desde el lanzador, no acreditada |
| Objeto | dos copias `git archive` fuera del repo, sin `.git` (`base/` 1.404 ficheros, `head/` 1.405) |
| `sha256` del objeto | **idéntico al abrir y al cerrar** (2.809 digests, comparados por el revisor por ruta y contenido) |
| `sha256` del informe | `e388cc184c380660b02ed9008f42ac7544f70162a059786f7d2828d2038c7a93` |
| Veredicto | **NO-SHIP** |
| Hallazgos | 6 — **1 `alta`, 5 `media`**; los seis confirmados contra la fuente, 0 refutados |
| Tokens | 124.144 (línea `tokens used` del `_stdout.log`) |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:vi6h -->
Directorio inicial: solo `MANDATO.md`, `base/`, `head/` y `_stdout.log`; ningún elemento ajeno.

# R1 adversarial — mejoras de las aperturas, bloque 1

Objeto: `base/` (`98801655f0a4cdc5477c7182def1ee12476858fe`) frente a `head/` (`7c70b70ea4c8efe764f1367121a6b2635846cdde`). Son archivos extraídos; no he comprobado genealogía Git. Todas las reproducciones usan datos sintéticos y se ejecutan desde este directorio con `$env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe' sondas_r1.py`. La sonda solo escribe temporales dentro de este directorio y los retira.

## 1. Custodia del intake (B)

**H-01 — media; remedio acotado.** `head/core/whatsapp_export.py:197-203`, `head/core/whatsapp_intake.py:64-75,96-99,158-161`. Un ZIP cuyo único chat válido se llama `_conversacion.txt` era aceptado por el fallback anterior (`base/core/whatsapp_intake.py:64-79`) y ahora `analyze` lanza `ValueError` antes de reservar el lote; no se escribe ningún miembro, incluido el ZIP original. El filtro `startswith("_")` confunde cualquier nombre recibido con un derivado propio. **Reproducción:** `sondas_r1.py`, salida `B-underscore: RECHAZADO` para un `.txt` con un mensaje Android válido. **Afirmación contradicha:** plan, Task 2, «custodia antes que parser: el intake deposita» (`head/docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md:173-178`); también la regla 3 del docstring de `elegir_chat`. **Remedio:** excluir solo los nombres generados que el canal conoce (por ejemplo `_chat_recortado.txt`), y probar un export con otro nombre inicial `_`, tanto en `analyze` como en `deposit_export`.

**H-02 — media; remedio estructural.** `head/core/whatsapp_export.py:178-203`, `head/core/whatsapp_intake.py:99-118,195-207`. Si un `.txt` adjunto contiene siquiera una línea con cabecera interpretable y precede al chat Android por orden, la regla 2 elige el adjunto. No basta con comprobar que *algún* texto se parsea. La previsualización cuenta mensajes de otro documento, omite las referencias reales y marca ese adjunto `tipo_contenido: whatsapp`, mientras el chat real queda como `txt`. El bucle de escritura sigue copiando todos los miembros; el daño aquí es de identificación y metadatos. La deduplicación por hash del ZIP sigue usando los mismos bytes, aunque la previsualización recalculada de un reingreso puede mostrar el chat equivocado. **Reproducción:** `sondas_r1.py`, `B-adjunto-interpretable`: `Acta.txt` gana a `Chat de WhatsApp con Ana.txt`; el `IMG.jpg` citado por el chat real no aparece entre `adjuntos_referenciados`. **Afirmación contradicha:** docstring de `elegir_chat`, «un `.txt` que se envió como ADJUNTO no le gana al chat por ir antes» (`head/core/whatsapp_export.py:186-188`). **Remedio:** definir una señal de identidad del chat exportado y resolver explícitamente la ambigüedad de varios textos parseables; preservar el depósito aunque no se pueda decidir y no etiquetar un adjunto como chat por una sola cabecera.

Fuera de esos dos casos, el cambio no elimina miembros del diccionario `members` ni altera `for name, data in members.items(): _escribe(name, data)` (`head/core/whatsapp_intake.py:206-208`). La normalización previa de `safe_zip_members` a basename y su posible colisión de nombres (`head/core/intake_utils.py:101-125`) ya existían en `base/`.

## 2. El atomizador (B)

**H-03 — media; remedio estructural.** `head/core/whatsapp_atomize/pipeline.py:29-55,85-95,131-150`. `descubrir_chats` convierte en chat cualquier directorio de las bases que tenga un `.txt` elegible, incluidos el propio lote y un directorio de rol con una nota no interpretable. La regla 3 de `elegir_chat` es útil para custodiar el ZIP, pero en el atomizador registra una nota como chat de cero mensajes, calcula su `chat_sha`, añade una entrada al índice y produce un `__LECTURA.md` vacío. Si la nota tiene una cabecera interpretable, además incorpora mensajes ajenos al corpus. **Reproducción:** `sondas_r1.py`, `B-descubrir` incluye `01_Cliente` por `notas.txt` además de `01_Cliente/Conversacion`; `B-atomizar` da `chats: 2, mensajes: 1` donde el árbol contiene un solo chat. **Afirmación contradicha:** plan, Task 2, «una sola regla de fichero de chat» y «el atomizador lo verá como chat con 0 mensajes, visible en su `INDICE.md`» (`head/docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md:155,173-174`): esa visibilidad se aplica también a documentos que nunca fueron export. **Remedio:** acotar el descubrimiento a directorios de export identificados por el intake/manifiesto o por una estructura validada; reservar el fallback de cero mensajes para un chat previamente identificado, no para todo `.txt` del árbol.

Para un `_chat.txt` existente, la prioridad de la regla 1 conserva el mismo fichero y `atomize_whatsapp_case` vuelve a calcular la huella de su texto (`head/core/whatsapp_atomize/pipeline.py:87-93`). `fingerprint` y `msg_id_for_fp` no cambiaron (`head/core/whatsapp_atomize/ids.py:18-43`); la limpieza A tampoco cambia `w.texto`. Por ello no encontré un cambio de `msg_id` de esos mensajes por este diff. `_leer_media` excluye por nombre el chat elegido (`pipeline.py:62-68`), comprobado por su test. La clave `chat_id = chat_dir.name` puede colisionar entre dos carpetas homónimas y sobrescribir `chat_sha` o `__LECTURA.md`, pero esa clave ya existía en `base/`; el barrido nuevo amplía las carpetas que pueden entrar en esa colisión. Dos `.txt` parseables en un mismo directorio siguen reducidos a uno; el intake anterior también elegía uno.

## 3. Las referencias limpias (A)

**H-04 — alta; remedio estructural.** `head/core/whatsapp_export.py:101-128,169-171`, `head/core/whatsapp_atomize/pipeline.py:93-95,118`, `head/core/whatsapp_atomize/adjuntos.py:19-33`. `_limpiar_ref` elimina una marca que puede pertenecer al nombre real en disco. Con un chat que cita `\u200efoto.jpg` y dos ficheros `foto.jpg` y `\u200efoto.jpg`, la referencia limpia pasa a casar silenciosamente con los bytes de `foto.jpg`, que son **otros**. Si solo existe el fichero marcado, pasa de casar en `base/` a figurar ausente en `head/`. `referencias_adjuntos` y `adjunto_ref` transportan solo la forma limpia; `construir_adjuntos` hace `media.get(ref)` exacto y `AdjuntoRef.nombre` conserva únicamente esa forma en el frontmatter. **Reproducción:** `sondas_r1.py`, ambas salidas `A-marca-en-disco`: con dos ficheros el adjunto indexado contiene `b'OTRO'`; con solo el marcado, `ausente: True`. **Afirmación contradicha:** comentario de `_limpiar_ref`, «con ellas la referencia no casa nunca con el fichero en disco» (`head/core/whatsapp_export.py:101-106`), que no vale cuando el fichero real también lleva la marca; el plan promete quitar solo los bordes (`plan:137-149`). **Remedio:** preservar referencia cruda y normalizada, intentar primero el nombre exacto recibido y usar la forma limpia solo si identifica un único fichero; declarar ambigüedad si hay dos candidatos. La referencia publicada y el ATT deben señalar los bytes realmente elegidos.

`scripts/redate_whatsapp_anexos.py:52-68` también consume `m.adjunto_ref`; el valor normalizado mejora su caso medido, pero ya no es una copia fiel del nombre original. No vi otro consumidor que exigiera expresamente las marcas; el problema comprobado es el enlace por nombre y la pérdida de esa distinción.

## 4. Los veredictos del verificador (C)

**H-05 — media; remedio acotado.** `head/core/verificar_apertura.py:188-205,226-241`. Cuando existen ambos catálogos, C3 toma el de `Sala lectura/` y deja sin mirar el de `01_Procesado/`. Con una fila de cobertura, catálogo de sala con una entrada y catálogo raíz con dos, `base/` habría dado `fallo`; `head/` da `ok`, sin evidencia de que hay dos catálogos discrepantes. Si una ubicación está ocupada por un directorio, sí devuelve `fallo` antes de elegir la otra; ese control se conserva. **Reproducción:** `sondas_r1.py`, `C3-dos-catalogos: ok` con `entradas_catalogo: 1`, pese al catálogo raíz de dos entradas. **Afirmación contradicha:** `ubicaciones_del_catalogo` dice «Se aceptan las dos ... y la evidencia dice en cuál apareció: tolerar en silencio convertiría este lector en el sitio donde la ambigüedad se esconde» (`head/core/verificar_apertura.py:244-263`); el plan pide que C3 use ese resolvedor (`plan:295-298`). **Remedio:** si hay dos ficheros, leer y contrastar ambos; un conflicto debe ser `fallo` con las dos ubicaciones y conteos en evidencia. Añadir test de doble presencia discordante.

**H-06 — media; remedio trivial.** `head/core/verificar_apertura.py:1050-1060`. C9 etiqueta como «es el truncado del alta» cualquier CRM entero a menos de un euro de la cuantía local. El alta real envía `int(round(datos.cuantia))` (`head/core/sudespacho_create.py:1245,1439`); con local `48702.90` habría enviado `48703`, pero C9 llama truncado conocido al CRM `48702`. Sigue en `fallo`, aunque la explicación puede distraer de una modificación distinta. **Reproducción:** `sondas_r1.py`, `C9-falso-truncado` muestra la nota y `round(local)=48703`. **Afirmación contradicha:** plan, Task 3, «si el del CRM es el entero que manda el alta (`round(local)` y sin decimales), lo dice» (`plan:299-303`). **Remedio:** exigir `n_crm == int(round(n_local))`, con tests para `.90` por debajo del entero y para el caso de redondeo bancario `.50`.

C2 mantiene `fallo` ante discrepancias. Los tests nuevos ejercen todas, algunas y ninguna explicadas, y 12 discrepancias con listas truncadas a ocho (`head/tests/test_verificar_apertura.py:1992-2040`). Los conteos `n_discrepan` y `n_relleno_225` permanecen enteros; `sin_explicar` se trunca solo como lista (`head/core/verificar_apertura.py:853-889`). No encontré una promoción a `ok`/`pendiente` ni una ocultación del caso mixto en esa rama. C3 con una ruta ocupada devuelve `fallo`; C9 conserva `fallo` en la discrepancia reproducida.

## 5. Los tests prueban lo que dicen

Hay controles positivos: A prueba marcas en ambos dialectos, marcas interiores intactas y adjunto realmente faltante (`head/tests/test_whatsapp_export.py:156-187`, `head/tests/test_whatsapp_intake.py:70-95`); B prueba Android, prioridad frente a un adjunto **no parseable**, tipo del manifiesto, exclusión del chat de `_leer_media` e idempotencia de una segunda corrida (`head/tests/test_whatsapp_export.py:203-225`, `head/tests/test_whatsapp_intake.py:240-257`, `head/tests/test_whatsapp_atomize_pipeline.py:72-117`); C prueba las tres ramas C2, catálogo en cada ubicación por separado, ubicación ocupada y un C9 lejano sin la mención (`head/tests/test_verificar_apertura.py:1992-2099`). Los tests afirmados existen y pasan en las dos semillas.

Ningún test actual se pondría rojo por H-01 (otro nombre inicial `_`), H-02 (adjunto parseable que precede al chat), H-03 (nota `.txt` en un ancestro del chat), H-04 (nombre real con marca y colisión), H-05 (ambos catálogos discordantes) o H-06 (CRM entero cercano pero distinto de `round(local)`). El test `test_idempotente` atomiza dos veces **con el mismo código**; no prueba la identidad de `msg_id` al pasar de `base/` a `head/` con un `_registro.json` previo.

Ejecuté los cinco ficheros pedidos desde la raíz con `work/tests/...`, `PYTHONPATH=work`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider` y `--basetemp=_bt777`/`_bt31337`, ambos relativos a este directorio. Semilla 777: salida al 100 %, cero fallos, un test lento omitido. Semilla 31337: igual. El primer intento, con cwd `work/`, no ejecutó tests: pytest recibió `WinError 5` al crear allí `--basetemp`; la repetición desde la raíz autorizada sí ejecutó ambos conjuntos. No ejecuté la suite completa ni el test marcado `--runslow`.

## 6. Lo que el diff no toca y debería

La divergencia deliberada de `core/adjuntos_contenido/zips.py:136-144` y la de `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:109-128` son las dos exclusiones declaradas. Encontré además `core/intake_lotes.py:119`, que aún clasifica solo `_chat.txt`, pero `deposit_export` ya lo sobreescribe para el chat elegido; no es otro lector roto de este flujo. `scripts/redate_whatsapp_anexos.py:109-114` busca un `.txt` en un bundle de la *Sala lectura*, no el depósito crudo, por lo que no pude atribuirle el defecto #285. `core/whatsapp_atomize/__init__.py:4` y varios docstrings siguen diciendo `_chat.txt`; conviene actualizar esa documentación, sin hallazgo funcional adicional. H-04 sí obliga a tocar el contrato que usan `construir_adjuntos` y `AdjuntoRef`, no solo `_limpiar_ref`.

## Lo que intenté refutar y NO pude

- Probé un chat iOS previo con `_chat.txt`: conserva prioridad y texto; el cálculo de `fingerprint` sigue basado en timestamp, autor y texto crudo, y el registro reutiliza el id. No hallé renumeración de `msg_id` atribuible a este diff.
- Probé el Android con nombre propio y media: el test comprueba que el chat elegido no entra en `_leer_media`; los cinco módulos relevantes quedaron cubiertos por las dos semillas.
- Contrasté el caso C2 mixto y el de 12 discrepancias con los tests y la rama de código: sigue `fallo`, identifica las no explicadas y los conteos no se truncan.
- Comprobé la ocupación de una ubicación de catálogo por un directorio: C3 da `fallo` incluso si la otra ubicación podría ser válida.

## SIN VERIFICAR

- No hay expedientes reales ni servicios de red en esta ronda; la frecuencia real de ficheros con marcas en el **nombre en disco**, adjuntos parseables o dos catálogos coexistentes no se puede inferir de estas sondas.
- No ejecuté `--runslow`, la suite completa ni una migración de un `_registro.json` real de `base/` a `head/`. La estabilidad de id está razonada sobre las funciones no cambiadas, no medida sobre un expediente previo.
- El árbol `base/` y `head/` contiene 1.404 y 1.405 ficheros respectivamente. `hashes-apertura.json` y `hashes-cierre.json` registran los 2.809 SHA-256; comparados por ruta y digest, **coinciden todos**. El orden de las entradas JSON difiere entre capturas, pero no hay alta, baja ni cambio de contenido.

NO-SHIP
<!-- informe-literal:fin:vi6h -->

## 2. Evidencia verificada por mí contra la fuente

- **Digest.** Recomputado sobre el fichero entregado: el canónico coincide con el `sha256`
  del fichero y con el que da el revisor en su mensaje final (`e388cc18…`).
- **El objeto es el commit.** Antes de lanzar, tres ficheros de `head/` (`core/whatsapp_export.py`,
  `core/verificar_apertura.py`, `core/whatsapp_atomize/pipeline.py`) contrastados contra
  `git show 7c70b70:<fichero>` con el fin de línea normalizado: los tres coinciden.
- **Los seis hallazgos se reproducen contra la fuente, no contra el informe.** Corrí la sonda del
  revisor (`sondas_r1.py`) apuntada al código del worktree —idéntico a `head/` en esos módulos—:
  `B-underscore: RECHAZADO` (H-01); `elegido= Acta.txt` (H-02); `adjunto= [('foto.jpg', b'OTRO')]`
  y `ausente: True` (H-04); `descubrir_chats` devuelve el directorio de rol (H-03) y la
  atomización da `chats: 2`; C3 `ok` con dos catálogos discordantes (H-05); C9 etiqueta como
  truncado un CRM de 48702 frente a un local de 48702,90 (H-06).
- **Higiene.** El revisor declara en su primera línea un directorio sin ficheros ajenos.
- **Tiempos.** Lanzado a las 15:58; `exec` salió a las 16:10:44 con `exit=0` (`_exit.txt` del
  lanzador, que es la señal de fin del vigía; el `INFORME.md` existía antes de esa hora y no se
  leyó hasta la salida).
- **Adjudicación:** `docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md` §6.
