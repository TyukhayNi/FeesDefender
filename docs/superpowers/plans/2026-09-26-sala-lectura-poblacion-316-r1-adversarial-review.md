---
tipo: revision-adversarial
objeto: diff 1aa1871..196b0aa de la fila #46 (MEJORAS #316; la skill organizar-sala-lectura 1.18, core/inventory.py, core/intake_control.py, core/sala_lectura.py, la C3 de core/verificar_apertura.py y sus tests), contra el plan docs/superpowers/plans/2026-09-26-sala-lectura-poblacion-316.md
objeto_rev: "1"
commit: 196b0aa
ronda: "1"
revisor: Codex
modelo: gpt-6-sol
esfuerzo: high
velocidad: default
veredicto: NO-SHIP
marcador_nonce: r9ph
sha256_informe: fa9d9e5e61e65e58532f0ff516e75cdf7360b2d6272221ded8c364b9c0214a94
adjudicado_en: docs/superpowers/plans/2026-09-26-sala-lectura-poblacion-316.md §7
---

# Acta — R1 adversarial sobre el DIFF de la fila #46 (la población de la sala de lectura)

Objeto: el diff `1aa1871..196b0aa`, que da contrato y verja a la población de la sala de lectura
(`MEJORAS #316`) en sus dos productores —la skill `organizar-sala-lectura` y el motor CLI— y hace
que la C3 de `verificar_apertura` honre lo declarado. **Una ronda**: toca `core/` y una skill, pero
ni decide quién escribe ni puede destruir datos de cliente. Fila ordinaria de la política:
`gpt-6-sol` · `high` · `default`, y **cuarta fila del ledger de calibración de la #38**.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.4` (binario `13995fba801849b0`), `gpt-6-sol` · `high` — **releídos** del `turn_context` del rollout y de la cabecera del `_stdout.log`; velocidad `default` **afirmada** desde el lanzador conservado |
| Objeto | `base/` (`1aa1871`) y `head/` (`196b0aa`), copias `git archive` fuera del repo, más `diff.patch` y `commits.txt` |
| `sha256` del objeto | **idéntico al abrir y al cerrar**: 2.879 ficheros, comparados por él y por mí contra una reextracción de los dos commits desde git |
| `sha256` del informe | `fa9d9e5e61e65e58532f0ff516e75cdf7360b2d6272221ded8c364b9c0214a94` |
| Tiempos | lanzado a las 18:08:45; `INFORME.md` a las 18:20:58; `exec` salió a las 18:21:17 con `exit=0` |
| Veredicto | `NO-SHIP` — 11 hallazgos: 3 `alta`, 7 `media`, 1 `baja` |

## 0. Mandato, literal

# Mandato — R1 adversarial sobre el diff de la fila #46: la población de la sala de lectura (MEJORAS #316, FeesDefender)

## 0. Higiene y reglas

- Tu directorio de trabajo debe contener solo: `MANDATO.md`, `base/`, `head/`, `diff.patch` y
  `commits.txt`. Si hay cualquier otro fichero, **no lo leas** y decláralo en la primera línea del
  informe.
- `base/` es el commit `1aa1871` (main) y `head/` es `196b0aa` (la rama del cambio), extraídos con
  `git archive`, sin `.git`. Son de **solo lectura**: si necesitas ejecutar o modificar algo, copia
  a una carpeta tuya dentro de tu directorio de trabajo. Calcula el SHA-256 de todos los ficheros de
  `base/` y `head/` al abrir y al cerrar, y di si coinciden.
- Python con las dependencias del repo:
  `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe` (tiene pytest; **no** tiene
  pytest-randomly, así que no hacen falta semillas). Usa `--basetemp` con una ruta **relativa**
  dentro de tu directorio de trabajo.
- No accedas a red, al CRM, a Drive, a Google ni al repositorio real.

## 1. Objeto

El diff `1aa1871..196b0aa` (`diff.patch`, `commits.txt`). Cierra `MEJORAS #316`: documentos que la
sala de máquina de un expediente procesó —audios de WhatsApp, zips, vCards, planos, documentos sin
extensión— no llegaban a la **sala de lectura**, el conjunto de copias que el abogado lee. La causa,
según el plan, es una sola frontera con dos productores: la skill `organizar-sala-lectura` (un
agente la ejecuta; su verificador no comprobaba la población) y el motor CLI (`core/inventory.py`
decidía la población con una lista blanca de extensiones). El diff cambia la skill (`SKILL.md` 1.18
y sus scripts), el inventario CLI, el registro de ficheros de protocolo (`core/intake_control.py`)
y la comprobación C3 de `core/verificar_apertura.py`.

El plan con lo medido, el diseño, los tests y lo que declara no cubierto está en
`head/docs/superpowers/plans/2026-09-26-sala-lectura-poblacion-316.md`; la entrada del backlog, en
`head/docs/MEJORAS_FUTURAS.md` (#316). El §4 del plan da cifras sobre expedientes reales a los que no
tienes acceso: decláralas SIN VERIFICAR, salvo lo que puedas razonar desde el código.

## 2. Qué te pido, numerado

1. **La verja de la skill** (`problemas_poblacion` en
   `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py`). ¿Puede una fuente de la
   cobertura sin fila ni declaración pasar sin problema? Ataca el cruce por sha256 de origen, la
   normalización de rutas, las declaraciones de `## No copiados` y las tres reglas de productor
   (protocolo, zip crudo de WhatsApp, firma `_firma_*`). Y al revés: ¿grita sobre algo legítimo?
2. **El formato de `## No copiados`** (`parse_no_copiados` en `manifiesto_parser.py`). ¿Es cerrado de
   verdad? ¿Qué acepta que no debería, o rechaza que sí? ¿Delimita bien la sección?
3. **El contrato del `SKILL.md`** (Pasos 1-bis, 5 y 6.5). ¿Dice lo mismo que la verja? ¿Hay
   instrucciones que el agente no pueda cumplir o que se contradigan con otros pasos?
4. **El inventario CLI sin lista blanca** (`head/core/inventory.py`). ¿Qué consumidores de
   `_inventory.json` o del catálogo asumían solo esas extensiones —`catalogo_documental`,
   `sala_lectura` (clasificar, índices, poblar), `extractor`, `pipeline`— y qué hacen ahora con un
   `.opus`, un `.zip`, un vídeo grande o un fichero sin extensión? ¿Queda algo que la lista apartaba y
   que no es un documento?
5. **El registro de protocolo** (`head/core/intake_control.py` y su copia en la skill). ¿Son
   correctos y completos los tres prefijos de la migración? ¿Hay otros ficheros que el repo escribe
   en `00_Input` y que solo apartaba la lista blanca? ¿Es sólida la exigencia de copia byte a byte,
   también en la skill empaquetada?
6. **C3** (`head/core/verificar_apertura.py`). ¿Puede aceptar como declarado algo que no lo está, o
   una firma que no lo es? ¿Es aceptable que confíe en una declaración escrita por el agente? ¿Bastan
   los tests anti-deriva para mantener iguales las copias del parser, de la regla y de la
   normalización?
7. **Los cuatro tests reescritos** (plan §3). Dictamina, uno a uno, si corrigen un aserto que fijaba
   el defecto o si debilitan la suite; en particular el cambio de sitio de los marcadores en
   `test_inventory_clasifica_por_fuente`.
8. **Los tests nuevos.** ¿Prueba cada uno lo que su nombre dice? ¿Alguno pasaría con una
   implementación equivocada? Si puedes, introduce en una copia tuya variantes defectuosas concretas
   y di qué test las detecta y cuál no. Ten en cuenta que algunos tests recargan su módulo con
   `importlib.reload`.
9. **El §5 del plan.** ¿Alguno de esos límites es en realidad un defecto que merece remedio ahora?

## 3. Formato del informe

Escribe `INFORME.md` en tu directorio de trabajo, en castellano. Por cada hallazgo: identificador
(H-01, H-02…), **severidad** (alta · media · baja) y **coste del remedio** (trivial · acotado ·
estructural), dónde (fichero:línea en `head/`), la evidencia reproducible y el remedio que propones.
Añade una sección «Lo que intenté refutar y no pude» y otra «SIN VERIFICAR».

No encontrar defectos es un resultado legítimo: si es tu conclusión, dilo, con la evidencia de lo
que probaste. Termina el informe con una línea que contenga solo el veredicto, uno de: SHIP,
LISTA-CON-CAMBIOS, REQUIERE-REVISION, NO-SHIP.

Como último mensaje, da la ruta de `INFORME.md` y su SHA-256 calculado sobre el contenido en UTF-8,
con saltos LF y un único salto final.

## 1. Informe recibido, sin modificar (Codex, 2026-09-26)

<!-- informe-literal:inicio:r9ph -->
Fichero ajeno al paquete permitido al abrir: `.stdout.log`; no se ha leído.

# R1 adversarial — fila #46, MEJORAS #316

**Objeto.** Diff `1aa1871..196b0aa`, según `diff.patch` y `commits.txt`. Revisión estática y ejecución exclusivamente sobre `scratch/work/`, copia de `head/`; no se ha accedido al repositorio real, la red, el CRM ni los expedientes. Los hallazgos se adjudican contra `head/`, no contra lo que afirma el plan.

**Integridad.** Al abrir, 2.879 ficheros de `base/` y `head/`; SHA-256 del JSON ordenado de pares `ruta → SHA-256 individual`: `d6b4fd04f2e7d0b0b98b82407a7d76bf8a5efe1143c31abaf720d6e1547a9af5`. El manifiesto completo de huellas quedó en `scratch/open_hashes.json`. Al cerrar, los mismos 2.879 ficheros conservaban sus SHA-256 individuales; la huella del JSON ordenado volvió a ser `d6b4fd04f2e7d0b0b98b82407a7d76bf8a5efe1143c31abaf720d6e1547a9af5`.

## Hallazgos

### H-01 — Una imagen probatoria marcada como firma desaparece de la sala

**Severidad: alta. Coste: acotado.** Dónde: `head/.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:151-164`, `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:158-160`, `head/core/verificar_apertura.py:359-360`, `head/.claude/skills/organizar-sala-lectura/SKILL.md:190-191`.

**Evidencia.** `es_firma_de_correo` solo pide lote/cajón de correo y prefijo `_firma_`, sin comprobar tipo, MIME, cabecera, origen ni marca persistida. La sonda `firma_aportada_por_cliente` con `2026-09-23_email_01/adjuntos/_firma_contrato.pdf` devuelve `[]` (ningún problema) aun sin fila ni declaración. Peor: incluso la marca **real** no justifica perder la copia legible. `head/core/email_export.py:1152-1160` documenta una aceptación de honorarios escaneada que el detector llegó a considerar firma y la decisión expresa de **depositar y avisar, no descartar**; `:1528-1532` la deposita con ese prefijo. El nuevo salto en la skill y en C3 anula esa red de seguridad. Los tests `test_la_firma_de_correo_es_la_que_email_export_nombra...` y `test_316_c3_la_firma...` fijan precisamente la exención, sin caso probatorio de control.

**Remedio.** Dar fila y copia a todo adjunto extraído, incluidos los marcados; mostrar `firma_marcada` para revisión. Si se decide excluir alguna copia derivada, exigir declaración por ruta y motivo individual, sin hacer que C3 la llame corroboración del contenido. No inferir procedencia de un nombre aportado por el cliente.

### H-02 — El verify da código 0 aunque la cobertura exigida falte

**Severidad: alta. Coste: trivial.** Dónde: `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:245-263`, `head/.claude/skills/organizar-sala-lectura/SKILL.md:455-466`.

**Evidencia.** `main` solo carga la cobertura si se pasa una ruta **y existe**. Sin argumento, o con `--cobertura ausente.json`, emite aviso, `Verify OK` y retorna `0`; ambas variantes se ejecutaron en `scratch/probes_316.py`. El test `test_cli_sin_cobertura_DICE_que_no_ha_contrastado_la_poblacion` incluso exige este retorno. El Paso 6.5 llama obligatorio al argumento si hay sala de máquina, pero la verja no comprueba la condición ni distingue ruta ausente de sala de máquina ausente. Una automatización que mire el exit code puede declarar éxito sin haber corrido la nueva comprobación.

**Remedio.** Si se da `--cobertura`, exigir fichero legible y esquema válido o salir con error. Inferir la ruta de cobertura desde el caso/sala y fallar si existe la sala de máquina pero no se aporta su cobertura. Reservar el éxito sin cobertura solo para un modo explícito que comunique verificación parcial.

### H-03 — Una fila con la ruta correcta y el hash equivocado acredita la fuente

**Severidad: alta. Coste: acotado.** Dónde: `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:148-159`, `:193-214`; comparación con `head/core/verificar_apertura.py:312-321,336-346`.

**Evidencia.** `problemas_poblacion([fila(a.pdf, hash B)], [cobertura(a.pdf, hash A)], []) == []` en la sonda, pese a que el contenido atribuido a la fila contradice el del origen. C3 sí devuelve `fallo` con `n_contradicciones=1` para ese mismo par. El chequeo de hash de la copia es opcional y por defecto `--hash no`; además contrasta copia contra **el valor del manifiesto**, no contra la cobertura. Por tanto la discrepancia puede pasar íntegra por el verify normal.

**Remedio.** Cruzar `(ruta, sha256)` por entrada como C3; una ruta coincidente con dos SHA-256 válidos diferentes debe ser error aunque haya otro cruce por hash. Mantener el chequeo de bytes de la copia como comprobación separada y exigirlo para afirmar copia idéntica.

### H-04 — El hash global excusa una segunda fuente sin fila ni declaración

**Severidad: media. Coste: acotado.** Dónde: `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:151-159`, `head/core/verificar_apertura.py:337-353`, `head/.claude/skills/organizar-sala-lectura/SKILL.md:192-194,440-444`.

**Evidencia.** Una fila `a.pdf` con SHA A y dos fuentes `a.pdf` y `b.pdf` con SHA A dan `[]` en la skill y `ok`/`por_sha=1` en C3, sin línea para `b.pdf`. Eso puede ser deduplicación correcta **del contenido**, pero contradice la promesa de dar cuenta **de cada ruta** mediante fila o `## No copiados`. El test `test_una_fuente_con_FILA_por_ruta_o_por_sha256...` aprueba explícitamente esa omisión y mezcla en un solo caso las dos clases de cruce. La verja tampoco detecta una fuente a la vez en fila y en `No copiados` (`ambas_fila_y_declaracion` → `[]`), pese al «nunca ambas» del Paso 5.

**Remedio.** Exigir línea `duplicado` por cada ruta no copiada y verificar que su destino existe y tiene el mismo hash; rechazar intersecciones entre filas y declaraciones. Si se prefiere que un hash global baste, cambiar la promesa de trazabilidad por ruta y explicitarlo en ambos verificadores.

### H-05 — `## No copiados` no es una sección ni un formato cerrados

**Severidad: media. Coste: acotado.** Dónde: `head/.claude/skills/organizar-sala-lectura/scripts/manifiesto_parser.py:73-112`, copia en `head/core/verificar_apertura.py:466-483`.

**Evidencia.** En modo `estricto=True`, `## No copiados\nSe excluye a.pdf` no falla: la prosa sin guion se ignora. `### Otro\n- excluido: `a.pdf` — motivo` se registra dentro de la sección anterior, porque solo `#` y `##` la cierran. `## No copiados más cosas` también la abre; esto puede ser intencional para encabezados fechados, pero el sufijo no está delimitado. `- duplicado: `a.pdf` — cualquier motivo` se acepta sin el `de `destino`` prometido. El detalle de `excluido` admite una letra o una afirmación sin sustento. C3 usa el mismo patrón en modo tolerante, de modo que un texto formalmente aceptado por ambos puede ser semánticamente vacío. Los cuatro tests del parser comprueban casos simples; ninguno ataca esos límites.

**Remedio.** Delimitar hasta el siguiente encabezado de nivel 1–3, hacer fallar texto no vacío no reconocido dentro de la sección en modo estricto, y validar por separado `duplicado — de `ruta conservada`` y `excluido — motivo no vacío`. C3 debe reutilizar un parser validado o tratar las secciones malformadas como no acreditadas y reportarlas.

### H-06 — Normalizar una ruta de cobertura puede convertir un documento en protocolo

**Severidad: media. Coste: acotado.** Dónde: `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:113-121,146-160`, copia de normalización `head/core/verificar_apertura.py:486-498`.

**Evidencia.** Las rutas de `_cobertura.json` ya son relativas a la raíz física de `00_Input`; `_clave_ruta` les quita también un primer componente literal `00_Input`. Si un cliente entrega el árbol `00_Input/00_Input/_caso.md`, la cobertura trae `00_Input/_caso.md`; la clave queda `_caso.md` y el registro la declara protocolo de raíz. La sonda `carpeta_00_input_anidada` retorna `[]` sin fila ni declaración. `lstrip('/')` también admite una ruta absoluta como si fuese relativa. El test anti-deriva solo demuestra que C3 y la skill hacen lo mismo, incluidos estos errores.

**Remedio.** Distinguir la ruta ya relativa de cobertura de una ruta de manifiesto que puede llevar prefijo; quitar `00_Input/` únicamente a esta segunda, con comprobación de contención y rechazo de rutas absolutas o con `..` antes de clasificar protocolo.

### H-07 — La regla de zip crudo se activa fuera del productor

**Severidad: media. Coste: acotado.** Dónde: `head/.claude/skills/organizar-sala-lectura/scripts/preclasificar.py:103-140`, `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:154-160`, `head/core/verificar_apertura.py:330-358`.

**Evidencia.** La pareja se decide solo por dos basenames en una misma carpeta. `04_Manual/_chat.txt` con `04_Manual/_export_original.zip` da `[]` en la sonda, aunque `whatsapp_intake.deposit_export` escribe en un lote `whatsapp` y su manifiesto marca el zip con `es_zip_origen=True` (`head/core/whatsapp_intake.py:178-210`). Los tests prueban la pareja dentro de un lote y el zip sin chat, pero no una pareja homónima en otra fuente.

**Remedio.** Restringir la exención al directorio y manifiesto del lote WhatsApp, o leer la marca `es_zip_origen`; no deducir que un zip de otro productor es crudo por coexistencia de nombres.

### H-08 — Los dos productores discrepan sobre lo que llega a la sala

**Severidad: media. Coste: acotado.** Dónde: `head/core/inventory.py:83-104`, `head/core/catalogo_documental.py:102-125`, `head/core/sala_lectura.py:1108-1140,1148-1188`, frente a `head/.claude/skills/organizar-sala-lectura/SKILL.md:184-194,440-447`.

**Evidencia.** En la integración aislada `scratch/work/tests/test_adversarial_316.py`, `organizar` copió los **7 de 7** ficheros: chat, zip crudo, `.opus`, `.vcf`, `.mp4`, documento sin extensión y `_firma_contrato.png`; `n_pendientes=6`, `COPY=7`. La skill dispensa precisamente al zip crudo y a la firma. El inventario CLI no tiene regla para ellos, de modo que también aparecen como documentos en el catálogo y en ambos índices. `.opus`, `.vcf`, `.mp4` y sin extensión sí deben entrar; `extractor._extract_one` los salta con `ExtractionError` (`head/core/extractor.py:234-282`), sin detener el pipeline (`:381-384`). El hash se calcula por bloques de 64 KiB (`head/core/utils.py:15-20`) y la copia usa `shutil.copy2`, sin límite de tamaño: un vídeo grande se duplicará completo en disco. No se midió tiempo ni espacio de un vídeo real.

**Remedio.** Fijar una política común para derivados del productor: o fila/copia en ambas vías (necesario para las firmas de H-01), o exclusión trazable en ambas. Hacer explícita la decisión de duplicar contenedores grandes y comprobar espacio o fallo de copia antes de anunciar sala organizada.

### H-09 — C3 convierte cualquier declaración sintáctica del agente en `ok`

**Severidad: media. Coste: acotado.** Dónde: `head/core/verificar_apertura.py:265-276,359-362,408-437`.

**Evidencia.** En la sonda, cobertura con `a.pdf`, catálogo vacío y manifiesto `- excluido: `a.pdf` — x` produce `estado=ok`, `declaradas_no_copiadas=1`; no se valida motivo, autor, firma, destino ni que el agente haya aplicado una regla permitida. Aceptar una **decisión declarada** es razonable para la contabilidad de rutas, pero ese `ok` no acredita que la omisión documental sea correcta. C3 además ignora los errores de formato de otras líneas porque su parser no es estricto. Su propio detalle dice «con su motivo» incluso para `x`.

**Remedio.** Separar en el resultado `cubierta por catálogo`, `excluida por regla de productor` y `excluida por decisión pendiente de adjudicación`; una exclusión discrecional del agente no debe convertir la comprobación en `ok` sin revisión. Rechazar la sección malformada antes del veredicto.

### H-10 — Los tres nuevos prefijos de protocolo son más amplios que sus escritores

**Severidad: baja. Coste: trivial.** Dónde: `head/core/intake_control.py:62-71,129-143` y copia idéntica de la skill.

**Evidencia.** Los tres prefijos **sí corresponden** a los escritores de `head/scripts/migrate_05crm_buckets.py:268-275,341-344`: bitácora JSON y dos backups con sello temporal. El registro usa `startswith`, por lo que también aparta un fichero de cliente en la raíz llamado `_migration_05crm_contrato.pdf` o `_caso.md.bak_prueba.pdf`, que el escritor no produce. El test nuevo solo comprueba tres positivos y un homónimo profundo; no comprueba negativos de raíz. No hallé otro fichero escrito por el repo bajo `00_Input` cuya exclusión dependiera inequívocamente solo de la antigua lista; `migrate_05crm_buckets.py:64,135-137` omite `.pulled`/`.synced` en **todo** `05_CRM`, pero no establece que el repo los escriba allí.

**Remedio.** Usar regex anclados al sello real y sufijo esperado, y añadir controles negativos en la raíz. Mantener el criterio por ubicación y procedencia.

### H-11 — El contrato promete más que lo comprobado

**Severidad: media. Coste: acotado.** Dónde: `head/.claude/skills/organizar-sala-lectura/SKILL.md:178-183,381-386,429-447,455-466`; `head/.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py:124-164,193-214`.

**Evidencia.** El Paso 5 afirma que *cada fichero físico* de `00_Input` tiene fila o declaración, pero `problemas_poblacion` solo enumera las rutas presentes en `_cobertura.json`. Si la sala de máquina omitió un fichero, o no existe cobertura, la verja carece de fuente para detectarlo; el Paso 1 sigue confiado al listado del agente. El Paso 5 también dice que el SHA-256 se calcula de los bytes y que MD5 no sirve; el Paso 4 admite `md5:<hash>` en Modo 3 para binarios grandes, y `--hash` por defecto no contrasta copia alguna. Esta degradación puede ser legítima, pero la afirmación de copia byte a byte no está acreditada en ese modo. `head/core/intake_control.py` y su copia en la skill **coinciden byte a byte** (SHA-256 de cada una: `3fd59173d7730a7f94801769ff6dfb5aad098ae105b241d36206dfb11c9490a4`); no hay un artefacto `.skill` empaquetado en `head/`, así que su contenido desplegado queda sin verificar.

**Remedio.** Reconciliar la cobertura con un censo físico de `00_Input` cuando el modo tenga acceso al árbol, o limitar explícitamente la promesa a «lo que figura en cobertura». Marcar el modo MD5 como verificación parcial y exigir un cotejo posterior antes de afirmar copia idéntica. Probar el paquete construido, además de los archivos fuente.

## Revisión de los cuatro tests reescritos

| Test | Dictamen |
|---|---|
| `test_inventory_scan_filtra_extensiones` → `test_inventory_scan_recoge_tambien_lo_que_no_sabe_leer` (`head/tests/test_inventory.py:9-35`) | Corrige un aserto que fijaba el defecto; ahora exige `ruido.bin` en `files` y ausencia de `skipped`. El mutante de lista blanca lo pone rojo. |
| `test_ficheros_sin_extension_relevante_NO_abortan_pero_se_declaran` → `test_los_planos_y_lo_que_no_se_sabe_leer_ENTRAN_en_la_sala` (`head/tests/test_sala_lectura_cero_acciones.py:68-87`) | Corrige el aserto de sala vacía. Su `assert res["acciones"]` solo exige alguna acción, no dos copias ni ambas identidades; conviene precisarlo. |
| `test_inventory_clasifica_por_fuente` (`head/tests/test_inventory.py:66-121`) | Mover `.pulled` a `sudespacho_*/` y `01_Drive EV/` es fiel a los escritores; `.synced` corresponde a `drive/`, no a `01_Drive EV/`. El cambio elimina una aserción accidental de que los marcadores en ubicaciones ajenas no eran documentos; los tests del registro comprueban `01_Drive EV/.synced`, pero este test de integración debería comprobar que un marcador homónimo fuera del lugar del productor **entra** en `files`. |
| `test_t1_el_adjunto_homonimo...` (`head/tests/test_intake_control_por_ubicacion.py:229-261`) | Fortalece: el adjunto `.yaml` debe estar en `files`, ya no basta `files ∪ skipped`; mantiene el control negativo del fichero de raíz. |

## Tests nuevos y mutantes

La revisión siguiente distingue la propiedad que cada test ejecuta de la propiedad más amplia que su nombre o el plan sugieren. Los números de línea remiten a `head/tests/`.

| Test nuevo | Resultado del examen |
|---|---|
| `test_no_copiados_lee_las_lineas_de_formato_cerrado` (:107) | Sí para tres líneas válidas; no prueba que `duplicado` tenga destino válido ni la frontera de `###`. |
| `test_no_copiados_sin_seccion_es_una_lista_vacia` (:117) | Sí. |
| `test_no_copiados_ESTRICTO_rechaza_una_linea_de_texto_libre` (:121) | Sí solo para prosa **con guion**; la prosa sin él pasa. |
| `test_no_copiados_ESTRICTO_rechaza_una_linea_sin_motivo` (:131) | Sí para detalle vacío; `x` o detalle falso pasan. |
| `test_los_ficheros_que_migrate_05crm_buckets_deja_en_la_raiz_son_protocolo` (`test_intake_control_por_ubicacion.py:92`) | Sí para los tres nombres ejemplares y profundidad ajena; no ejecuta al escritor ni limita el prefijo. |
| `test_316_el_inventario_recoge_audios_zips_vcards_y_lo_que_no_tiene_extension` (`test_inventory.py:38`) | Sí para el inventario; los bytes `b"x"` no ejercitan extracción, clasificación ni copia. |
| `test_la_firma_de_correo_es_la_que_email_export_nombra_en_un_lote_de_correo` (`test_sala_lectura_poblacion_316.py:46`) | Solo prueba convención de nombre, no la marca real ni su seguridad probatoria. |
| `test_la_firma_de_correo_no_se_adivina_por_el_nombre_en_otro_sitio` (:51) | Tres negativos útiles, pero incluye un `_firma_image.pngx` positivo: acepta cualquier extensión. |
| `test_prefijo_de_firma_sin_deriva_con_email_export` (:64) | Sí para igualdad de constante, no para el criterio productor. |
| `test_el_registro_de_protocolo_de_la_skill_es_COPIA_EXACTA_del_de_core` (:69) | Sí, igualdad byte a byte en el árbol fuente. |
| `test_una_fuente_SIN_fila_ni_declaracion_es_un_problema` (:81) | Sí para una nota de voz ausente. |
| `test_una_fuente_con_FILA_por_ruta_o_por_sha256_no_es_problema` (:91) | Prueba una fila con dos fuentes y mismo hash; también aprueba la falta de línea `duplicado` (H-04), sin caso de hash contradictorio. |
| `test_una_fuente_DECLARADA_en_no_copiados_no_es_problema` (:99) | Sí para coincidencia de ruta; no exige motivo justificable ni exclusividad. |
| `test_las_tres_reglas_de_productor_no_piden_declaracion` (:107) | Sí para nombres representativos; no demuestra procedencia. |
| `test_un_homonimo_de_protocolo_o_un_zip_crudo_sin_chat_SI_piden_fila` (:117) | Dos controles útiles; falta zip con chat fuera de lote WhatsApp. |
| `test_una_fila_de_cobertura_sin_rel_path_no_se_da_por_contrastada` (:125) | Sí. |
| `test_cli_con_cobertura_FALLA_si_falta_una_fuente` (:153) | Sí para ruta existente y cobertura válida. |
| `test_cli_con_la_fuente_declarada_en_no_copiados_da_ok` (:160) | Sí para una declaración sintáctica; no prueba corrección de la decisión. |
| `test_cli_una_declaracion_en_TEXTO_LIBRE_es_un_error` (:167) | Sí para viñeta malformada; no para prosa sin viñeta. |
| `test_cli_sin_cobertura_DICE_que_no_ha_contrastado_la_poblacion` (:173) | Sí para el aviso, pero fija el falso éxito con código 0 (H-02). |
| `test_316_c3_una_fuente_DECLARADA_en_no_copiados_no_se_exige` (`test_verificar_apertura.py:2854`) | Sí para contabilidad de rutas; `ok` no acredita que el motivo sea correcto. |
| `test_316_c3_una_declaracion_en_TEXTO_LIBRE_no_cuenta` (:2870) | Sí para una viñeta libre; otras formas inválidas no se señalan. |
| `test_316_c3_la_firma_de_correo_de_email_export_no_se_exige` (:2885) | Sí para la regla codificada; bloquea un remedio a H-01 sin cambiar el test. |
| `test_316_c3_un__firma_FUERA_de_un_lote_de_correo_si_se_exige` (:2897) | Control negativo útil; no prueba `_firma_*` aportada dentro de un lote. |
| `test_316_c3_un_manifiesto_que_no_se_puede_leer_es_fallo` (:2910) | Sí para directorio ocupado; el título generaliza a otros errores de lectura no ejercitados. |
| `test_316_anti_deriva_la_firma_de_C3_es_la_de_email_export_y_la_de_la_skill` (:2944) | Sí en constantes y nueve rutas muestra; ambas copias pueden compartir una regla errónea. |
| `test_316_anti_deriva_las_rutas_se_normalizan_igual_en_C3_y_en_la_skill` (:2954) | Sí para igualdad en esas rutas, no para corrección; ambas quitan el prefijo de una ruta relativa legítima (H-06). |
| `test_316_anti_deriva_no_copiados_se_lee_igual_en_C3_y_en_la_skill` (:2960) | Sí para las líneas muestra; ambos aceptan las mismas declaraciones inválidas de H-05. |

**Ejecución.** En `scratch/work/`, los seis módulos de test dirigidos (`test_sala_lectura_poblacion_316.py`, `test_manifiesto_parser.py`, `test_inventory.py`, `test_sala_lectura_cero_acciones.py`, `test_intake_control_por_ubicacion.py`, `test_verificar_apertura.py`) terminaron con código 0, sin fallos y con una prueba lenta omitida. Comando desde la raíz del mandato: `python -m pytest scratch/work/tests/<módulos> -q -p no:randomly -p no:cacheprovider --basetemp scratch/pytest-base4 --tb=short`. El Python indicado sí cargó `pytest_randomly` en el primer intento; se desactivó en la repetición. El primer intento desde `scratch/work/` falló al crear `../pytest-base` por permisos de ese proceso, no por asertos; la ejecución válida se hizo desde la raíz, con `--basetemp` relativo dentro del mandato.

**Mutación escrita en copia.** Se reintrodujo en `scratch/work/core/inventory.py` un filtro de sufijos que dejaba entrar `.pdf`, `.txt`, `.gml` y `.dxf`, y apartaba los nuevos formatos. `test_inventory_scan_recoge_tambien_lo_que_no_sabe_leer` y `test_316_el_inventario_recoge...` fallaron; `test_los_planos_y_lo_que_no_se_sabe_leer_ENTRAN...` pasó, porque el mutante conservaba precisamente sus dos sufijos. Esto confirma que el primer par detecta el retorno de la lista blanca y que el test de planos, aislado, no protege audios ni zips. `importlib.reload(inventory)` en los tests lee la mutación **del disco**; una mutación solo en memoria habría quedado anulada. Se restauró la copia de `inventory.py` byte a byte desde `head/` después del experimento. Las sondas de H-01–H-07 pasaron por todas las pruebas existentes dirigidas: no había asertos para esas entradas adversariales.

## El §5 del plan

- **Salas ya montadas:** limitación de despliegue real, no defecto del diff por sí sola. Hay que reejecutar el productor y revisar C3 antes de decir que #316 está resuelto en cada expediente.
- **Encabezados antiguos:** no migrarlos automáticamente es defendible; C3 sigue detectando ausencias. El defecto actual es que el nuevo parser acepta prosa sin viñeta y subtítulos ajenos sin error (H-05).
- **«La verja vigila, no clasifica»:** aceptable para decisiones jurídicas; falta, sin embargo, censo físico independiente y se tolera ausencia de cobertura (H-02/H-11), que sí impide afirmar la población prometida.
- **619 líneas de `SKILL.md`:** deuda editorial; no se observa por sí misma un fallo de ejecución de #316. La contradicción SHA-256/MD5 sí merece aclaración ahora (H-11).
- **Mutantes en memoria con `reload`:** límite del arnés, no del producto; el mutante escrito de inventario sí fue detectado.

## Lo que intenté refutar y no pude

- Los tres nombres nuevos de la migración corresponden a su escritor; no encontré un **cuarto** fichero de esa migración en `00_Input`.
- La copia del registro de protocolo en la skill coincide byte a byte con la de `core` en `head/`.
- La reescritura de los tests de inventario y del adjunto homónimo corrige asertos que perpetuaban la lista blanca; el mutante de sufijos cae.
- El recorrido de CLI añade al catálogo y copia los formatos antes omitidos en el caso sintético; el extractor los salta sin abortar cuando no los conoce.
- C3 sí rechaza una entrada de catálogo con la misma ruta de la fuente y hash contradictorio, a diferencia de la nueva verja de la skill.

## SIN VERIFICAR

- Todas las cifras del §4 del plan sobre expedientes reales: 17 manifiestos, 23 expedientes, los conteos de W-02Y2J6, W-030TZY y los cambios de estado de casos concretos. No hubo acceso a esos datos.
- Las cifras históricas citadas en comentarios de `email_export` y `sala_lectura`; se contrastó el comportamiento escrito en el código, no su corpus original.
- Un paquete `.skill` importado en Cowork o una copia desplegada fuera de `head/`: no está en el material revisado.
- La suite completa de 6.844 pruebas y un vídeo realmente grande; solo se ejecutó el subconjunto dirigido y una integración sintética de pocos bytes.

NO-SHIP

<!-- informe-literal:fin:r9ph -->

## 2. Evidencia verificada por mí al adjudicar

- **Digest.** Recomputado sobre el `INFORME.md` entregado (UTF-8, LF, un único salto final):
  `fa9d9e5e61e65e58532f0ff516e75cdf7360b2d6272221ded8c364b9c0214a94`, **el mismo que declara el revisor en su último mensaje** (`_ultimo_mensaje.txt`). El
  fichero venía ya en LF con un solo salto: el digest del crudo y el del canónico coinciden.
- **La ronda terminó, y así se supo.** Vigía armado antes de lanzar, con las dos salidas —fin y
  muerte— y ejecutado con `powershell -File`, porque el `Monitor` corre en bash. Señal de fin: el
  `_exit.txt` del lanzador (`exit=0`) y el `-o`, los dos a las 18:21:17; el vigía dijo `TERMINO` a
  las 18:21:29. Ninguna de las cuatro muertes conocidas en el log.
- **Modelo y esfuerzo, releídos:** `gpt-6-sol` · `high` en el `turn_context` de
  `rollout-2026-09-26T18-08-45-01a0de79-e437-7932-ae66-914fe9886228.jsonl` (`originator:
  codex_exec`, CLI `0.155.0-alpha.16.4`) y en la cabecera del `_stdout.log`. Binario elegido por
  tener `codex-code-mode-host.exe` al lado y **sondado antes** con los tres flags
  (`C:\t\sonda-sol-316-1807`): `VIVO`, sin aviso de tier. La velocidad `default` se **afirma** desde
  el lanzador conservado (`C:\t\sala-316-r1-1808-lanzador\_lanzar.ps1`); no se puede releer.
- **El objeto no se tocó, y lo mido yo, no solo él.** Reextraje `1aa1871` y `196b0aa` desde git a
  un directorio aparte (`C:\t\sala-316-r1-1808-verif`) y comparé fichero a fichero con las copias del
  revisor: **2.879 ficheros, cero diferencias** (1.438 + 1.441, las mismas cuentas que da él).
- **La línea de higiene del informe:** el log que dice haber encontrado al abrir es el `_stdout.log`,
  la redirección de su propia salida que hace el lanzador. Hizo bien en no leerlo.
- **Tokens y cupo, para la calibración** (releídos del rollout): 6.358.983 tokens totales, de los
  que 6.159.360 son entrada en caché; **entrada nueva + salida = 199.623**, la medida de las filas
  anteriores del ledger. El contador semanal de la cuenta marcaba **78 %** en el primer evento
  (16:08:55 UTC) y **79 %** en el último (16:21:15 UTC). **Ningún otro rollout de Codex corre en esa
  ventana**: la sonda terminó antes y el siguiente, de otro proyecto, empezó a las 16:33:29 UTC. El
  punto es probablemente de esta ronda, pero el contador es de la cuenta: no se imputa como medida.
- **Los once hallazgos, reproducidos contra el código de `196b0aa` y no contra el informe** (un
  script mío monta cada contraejemplo y llama a la función real):
  - **H-01.** `problemas_poblacion` con `2026-09-23_email_01/adjuntos/_firma_contrato.pdf` en la
    cobertura y nada en el manifiesto: `[]`.
  - **H-02.** `verificar_sala.py` sin `--cobertura`, y con una `--cobertura` que no existe: `rc 0` y
    «Verify OK» las dos veces.
  - **H-03.** Fila `(a.pdf, sha B)` contra la fuente `(a.pdf, sha A)`: `[]`.
  - **H-04.** Fila `(a.pdf, A)` y fuentes `a.pdf` y `b.pdf`, las dos con `A`: `[]`, sin línea para
    `b.pdf`. Y la misma ruta con fila y declarada `excluido`: `[]`.
  - **H-05.** En modo estricto: `Se excluye a.pdf` sin viñeta, `[]`; una viñeta bajo `### Otro`,
    leída; `- duplicado: `a.pdf` — cualquier motivo`, aceptada; `## No copiados más cosas`, abre.
  - **H-06.** La cobertura `00_Input/_caso.md` da la clave `_caso.md`, protocolo: `[]`.
  - **H-07.** `04_Manual/_chat.txt` junto a `04_Manual/_export_original.zip`: el zip, apartado.
  - **H-08.** Confirmado leyendo `core/inventory.py`: todo lo que no es protocolo entra, así que el
    motor CLI copia el zip crudo y la firma que la skill aparta.
  - **H-09.** C3 con la fuente `a.pdf`, catálogo vacío y `- excluido: `a.pdf` — x`: `ok`, «con su
    motivo». Y uno más que el informe no enseñaba: `- duplicado: `a.pdf` — de `otra.pdf`` también
    daba `ok`, sin que nada comprobara el duplicado.
  - **H-10.** `_migration_05crm_contrato.pdf`, `_caso.md.bak_prueba.pdf` e
    `_intake_hashes.json.bak_x.docx` en la raíz: protocolo los tres.
  - **H-11.** Confirmado en el código y en `SKILL.md`: la verja solo recorre `_cobertura.json`, y el
    Modo 3 admite `md5:` donde el Paso 5 dice que el `md5` no sirve.
- **Y lo que medí en los 24 expedientes con cobertura antes de remediar,** para que el remedio no
  fabricara rojos: **cero** filas de manifiesto con la ruta de una fuente y otro sha256; **cero**
  rutas de cobertura con el prefijo `00_Input/` (y 457 filas de manifiesto y 457 entradas de
  catálogo que sí lo llevan); **cero** rutas absolutas en los manifiestos; 68 ficheros `_firma_*`,
  todos en lotes de correo, 46 ya en su catálogo; 14 `_export_original.zip`, todos en lotes de
  WhatsApp o en `02_Whatsapp/`; las dos secciones `## No copiados` que existen escriben 47
  `duplicado` —todos con `de `ruta``—, 3 `excluido`, cuatro rótulos sin viñeta y ningún `###`; y los
  tres ficheros de la migración que hay en las raíces casan con el sello real.
- **Adjudicación:** `docs/superpowers/plans/2026-09-26-sala-lectura-poblacion-316.md` §7.
