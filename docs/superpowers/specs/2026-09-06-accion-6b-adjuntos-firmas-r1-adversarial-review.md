---
estado: historico
dueno: Nikolai Tyukhay
fecha: 2026-09-06
veredicto: NO-SHIP
revisor: Codex (CLI 0.153.0-alpha.5, gpt-5.6-sol)
objeto: diff 17d9336..a0deab5 (accion 6b — default de adjuntos + filtro de firmas)
sha256_informe: 4862937724ce2222edb0fe9067d0b9e623ad37ccdeb01b65102d8809119f2e52
---

# Acta de revision adversarial R1 — accion 6b (`--extraer-adjuntos` por defecto + filtro de firmas)

- **Objeto revisado:** diff `17d9336..a0deab5` — default de `--extraer-adjuntos` y `es_firma_incrustada`
- **Ronda:** R1 (unica; radio de dano = no decide quien escribe ni destruye datos de cliente)
- **Revisor:** Codex (CLI 0.153.0-alpha.5, `gpt-5.6-sol`), copia externa `git archive`, solo lectura
- **Informe recibido:** 2026-09-06, `C:/t/r6b2244/INFORME.md`, 22.002 bytes
- **Hallazgos:** 4 — 2 ALTOS (H-01, H-02), 2 MEDIOS (H-03, H-04); **4 confirmados, 0 refutados**
- **Remediado en:** pendiente — ver el §7 del plan `docs/superpowers/plans/2026-09-06-accion-6a-filtro-de-ruido-email-export.md`

**Por que existe esta acta.** Yo soy la parte revisada: sin el informe original archivado, nadie
puede contrastar **que dijo el revisor** con **que decidi yo que dijo**.

**Digest.** `sha256_informe` se computa sobre el BLOQUE canonicalizado de abajo, que es lo que
recomputa el guard G8. El `sha256` del fichero crudo del revisor es
`4862937724ce2222edb0fe9067d0b9e623ad37ccdeb01b65102d8809119f2e52` — coincide.

**Lo que esta ronda corrige, y es lo mas caro del dia.** El autor habia declarado —en el plan, en
el mensaje de commit y **al usuario**— que el «Gate 2» de `--extraer-adjuntos` salia cero **por
construccion**, porque `particionar_eml` salta `message/rfc822`. **Es falso**, y el propio
repositorio lo desmentia: `docs/MEJORAS_FUTURAS.md` §55.1 ya documentaba la bifurcacion —un `.eml`
adjunto con MIME generico `application/octet-stream` **no** es `message/rfc822`— y ademas advertia
que esos ficheros «solo aparecen si `--extraer-adjuntos` los escribe a disco», es decir, que
**invertir el default es exactamente lo que abre esa puerta**. La medicion de 444 adjuntos con cero
correos sigue siendo valida como medicion; lo falso era la explicacion causal.

---

## 1. Informe recibido — texto LITERAL del revisor

> Lo que sigue es la voz del revisor sin una sola edicion. Nada de lo de abajo es adjudicacion.

Higiene del workdir INCUMPLIDA al abrir: había `_stdout.log` además de `MANDATO.md`; no he leído `_stdout.log` ni lo he usado como evidencia.

# R1 adversarial — acción 6b

SHA-256 de apertura de `C:/t/r6b2244obj/head/core/email_export.py`:
`c02a493c8a2ef9b839f624236cfb5ff5742b856c5d328eef3fce263547915539`.

Objeto: contenido de `base/` frente a `head/`, ambos en `C:/t/r6b2244obj/`. **Genealogía: SIN VERIFICAR.** No hay `.git`; no acredito las identidades `17d9336` y `a0deab5`. El diff real comprende 15 ficheros y también remediaciones de la acción 6a. Distingo abajo lo propio de 6b, lo anterior y un defecto de esas remediaciones.

Las copias congeladas se han tratado como entradas de solo lectura. Se creó `C:/t/r6b2244/h/` para ejecutar y mutar, y una copia local de `base/core/email_export.py` para comparar comportamiento. Los casos, imágenes y servicios de prueba son sintéticos. No se ha accedido a Gmail, Drive ni expedientes reales, ni se ha delegado la revisión.

## Ejecución y alcance de la evidencia

Intérprete: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe` (Python 3.14.4), pytest 9.1.1. Directorio de ejecución: `C:/t/r6b2244/h`. En las pruebas se fijaron `PYTHONDONTWRITEBYTECODE=1` y `PYTHONUTF8=1`, se desactivó `cacheprovider` y se usaron `--basetemp` relativos `../t1` a `../t5`, todos dentro del workdir. No hubo escrituras de pruebas sobre las copias congeladas.

| Ejecución | Resultado y evidencia |
|---|---|
| Cinco módulos: `test_email_export.py`, `test_email_export_firmas_incrustadas.py`, `test_email_export_filtro_ruido.py`, `test_email_export_r1_remediaciones.py`, `test_abrir_caso_cli.py`; semilla 777 | 192 pruebas, salida 0. |
| Todos los `tests/test_email*.py`, más `test_atomize_emails_cli.py`, `test_intake_lotes.py`, `test_sala_maquina_cableado_adjuntos.py`, `test_sala_maquina_cableado_atomize.py`, `test_sala_maquina_duplicados.py` y `test_abrir_caso_cli.py`; semilla 31337 | **741 passed**, seis snapshots, 41,42 s; `suite-ampliada.log`. |
| Primera batería propia de caracterización | 21 passed, 4,31 s; `reproducciones.log`. |
| Mutaciones sobre la copia local, con restauración de bytes en `finally` | Dos baselines verdes y 27 mutantes ejecutados; `mutar_revision.py`, `mutaciones.json`, `mutaciones-ejecucion.log` y logs individuales en `mutaciones/`. Resultados desglosados abajo. |
| Revisión final tras restaurar: cinco módulos iniciales + `test_migrar_layout.py` + batería propia ampliada; semilla 31337 | **236 passed, 1 failed**, 13,11 s; `verificacion-final.log`. El rojo era un supuesto incorrecto de mi control de migración, explicado abajo; ningún test del autor falló. |
| Batería propia corregida (24 casos) + migración existente (21); semilla 31337 | **45 passed**, 5,58 s; `verificacion-reproducciones-final.log`. |

Los asertos propios **caracterizan el comportamiento observado**, incluidos los defectos: sus verdes no son una aprobación del código. Están en `h/tests/test_review_6b.py`; incluyen MIME real, PNG/TIFF válidos, export con servicios falsos, atomización, manifiestos, trazas, CLI, transición entre versiones y migración física de un caso sintético.

Comando para repetir las últimas reproducciones, desde `h/` y con las dos variables de entorno anteriores:

```powershell
& 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe' -m pytest tests/test_review_6b.py tests/test_migrar_layout.py -o addopts='' -v --tb=short -p no:cacheprovider --basetemp=../t5 --randomly-seed=31337
```

El arnés de mutación se repite con ese intérprete sobre `C:/t/r6b2244/mutar_revision.py`. No necesita git. No debe ejecutarse simultáneamente con otras pruebas sobre `h/`.

**SIN VERIFICAR:** suite completa del repositorio, servicios reales Gmail/Drive, corpus real, UI Streamlit en ejecución, OCR externo y despliegue en expedientes del despacho. Los resultados anteriores no acreditan esas superficies.

## Hallazgos

### H-01 — ALTO — Se omiten imágenes probatorias por confundir CID y tamaño con firma

**Localización:** `head/core/email_export.py:290-315`, especialmente `313-315`; materialización en `1459-1471`. Regresión del filtro nuevo frente a la extracción explícita anterior.

`es_firma_incrustada` no comprueba «referenciada desde el cuerpo». Solo comprueba que la cabecera `Content-ID` sea no vacía. Tampoco distingue el contexto MIME ni identifica un logotipo. Por tanto, una parte nombrada de `multipart/mixed`, con CID y sin disposición `attachment`, se descarta aunque no exista HTML ni ninguna referencia `cid:`. «No pone attachment» no demuestra que el remitente no haya incorporado deliberadamente ese documento.

**Reproducción:** PNG válido con el texto «ACEPTO HONORARIOS 3% / TRANSFERENCIA 12345», o TIFF válido comprimido Group 4, de menos de 50 KiB; nombre `aceptacion.png`/`aceptacion.tiff`, `Content-ID: <doc@x>`, disposición `inline`, ausente o desconocida `x-invalid`. El correo lleva solo cuerpo de texto y `multipart/mixed`. En los seis casos: `errors=[]`, `attachments=0`, `firmas_filtradas=1`, no se deposita la imagen. Para disposición ausente se elimina realmente la cabecera y se conserva el nombre en `Content-Type`; no se usa el falso caso ausente del fixture del autor.

También se reproduce con una captura que **sí** está referenciada desde HTML mediante `<img src="cid:doc@x">` dentro de `multipart/related`. Cerrar únicamente la comprobación de referencia no resuelve el falso positivo semántico: una aceptación, justificante o recorte pequeño puede ser contenido del caso.

**Daño preciso:** se omite el binario de `00_Input` y de la ruta de OCR de la sala de máquina. No afirmo destrucción del original: el `.eml` conserva exactamente los bytes, y el atomizador todavía puede materializar el adjunto en `01_Procesado/Emails/adjuntos`. Pero esa recuperación no neutraliza la omisión de texto: `core/adjuntos_contenido/router.py:45-49` vuelve a omitir las imágenes menores de 50 KiB. La reproducción comprueba también ese resultado, con texto vacío. No se ha ejecutado OCR real.

**Dirección del remedio:** conservar los casos ambiguos y exigir evidencia adicional para decidir que una imagen es decorativa. La presencia de CID, el contexto `related` y el tamaño no bastan por sí solos. Incorporar documentos pequeños positivos, referencias ausentes y TIFF a la aceptación; permitir recuperar la extracción de un falso positivo.

### H-02 — ALTO — El Gate 2 no está cerrado por construcción: un `.eml` genérico entra como correo independiente y elude el filtro de ruido

**Localización:** `head/core/email_export.py:327-342`, `1468-1471`; consumidores en `1334-1337`, `1595`, `1632-1635`, `1681`; `head/core/email_atomize/extract.py:101-108`. La ruta existía con extracción explícita; el default nuevo la generaliza.

Saltar el MIME `message/rfc822` no equivale a impedir extraer ficheros de nombre `.eml`. Un adjunto `application/octet-stream; filename="tercero.eml"` pasa íntegro por `particionar_eml` y se escribe a disco. Los lectores lo reconocen por extensión y no conservan la relación padre-adjunto.

**Reproducción:** correo del caso que adjunta `tercero.eml` como `application/octet-stream`. El adjunto contiene un correo con asunto «Factura agosto» dirigido a `Proveedores.ES@engelvoelkers.com`; `clasificar_ruido` devuelve `facturacion_despacho`. Con el default nuevo se observa:

- `attachments=1`, `nested_flattened=0`, `errors=[]`.
- `excluidos_ruido=[]` y `ruido_transportado=[]`.
- Dos avistamientos; el adjunto tiene `profundidad=0` y `ruta_anidacion=[]`.
- «Factura agosto» aparece en `CRONOLOGIA.md` como correo independiente.

La variante con expediente comprueba que el manifiesto clasifica ambos ficheros como `eml` y que `upload_email` registra dos correos, cero adjuntos y `forwarded_in=None` para el hijo genérico. No es solo una frase demasiado fuerte en un comentario: falla precisamente la frontera de clasificación/procedencia que motivaba el gate, y reaparece una puerta de entrada del ruido que 6a intenta excluir.

La bifurcación ya está descrita en **la propia fuente**, `docs/MEJORAS_FUTURAS.md:2327-2331` (§55.1). La afirmación «cero por construcción» contradice ese código y ese antecedente. No afirmo que el corpus real contenga uno: su cero medido sigue SIN VERIFICAR.

**Dirección del remedio:** reconocer y tratar coherentemente los adjuntos `.eml` con MIME genérico, conservando procedencia y aplicando la política de ruido antes de publicarlos como correos independientes. Convertir el Gate 2 en una prueba ejecutable que incluya esta variante.

### H-03 — MEDIO — El CLI rompe las invocaciones existentes con `--extraer-adjuntos`

**Localización:** `head/scripts/export_label_emails.py:54-58` frente a `base/scripts/export_label_emails.py:54-55`.

Se elimina el argumento positivo y se añade únicamente `--no-extraer-adjuntos`. Cambiar el default no exigía dejar de reconocer el flag que antes activaba esa misma operación.

**Reproducción:** `main(['--ref','W-TEST99','--account','revision@example.test','--label','X','--extraer-adjuntos'])` termina con `SystemExit(2)` por argumento no reconocido, antes de resolver el caso o llegar al motor. Las llamadas sin flag y con el nuevo flag negativo sí propagan `True` y `False`, respectivamente. Existen invocaciones con el positivo en los planes de aplanado y enlaces, y la skill versionada todavía lo presenta como opción.

**Dirección del remedio:** conservar el argumento positivo compatible, junto al negativo, con default `True`. Asertar el parseo de las tres formas.

### H-04 — MEDIO — `filtrar_ruido=False` no desactiva el filtrado de hijos ni de mensajes rescatados

**Localización:** `head/core/email_export.py:525-540`, `742-751`; propagación ausente en `1243-1261`. **Pertenece a las remediaciones 6a incluidas en el diff congelado; no lo atribuyo al filtro de firmas de 6b.**

La opción controla solo el bucle principal (`1269`). `_aplana_anidados` y `_deposita_mensaje_rescatado` aplican `clasificar_ruido` incondicionalmente y no reciben esa opción.

**Reproducción:** un padre legítimo con un hijo `message/rfc822` que coincide con `facturacion_despacho`, exportado con `filtrar_ruido=False`, produce `nested_flattened=0` y una entrada en `ruido_transportado`. El mismo escenario por permalink Gmail, con servicio falso y el filtro desactivado, sigue excluyendo el rescatado. Además, el enlace queda como `outcome='resolved', dedup=True` aunque el mensaje no existe en el destino: `_rescata_gmail:795-798` interpreta la exclusión como deduplicación.

**Daño:** el mecanismo anunciado para recuperar correo excluido no funciona en esas puertas. El padre se conserva íntegro, pero el hijo no se materializa; en el rescate ni siquiera se deposita el mensaje. El resultado del enlace describe incorrectamente la causa.

**Dirección del remedio:** propagar la política elegida a todas las entradas y distinguir el resultado «excluido» de «ya presente». Probar la recuperación con la opción desactivada, no solo el filtrado con ella activada.

## Respuesta a las siete afirmaciones

1. **Contrato de `split_eml`: verificado en fuente y ejecución acotada.** Devuelve el raw y las mismas ternas sin filtrar. Se comparó base/head sobre mensajes sin adjuntos, tipos y dispositions distintos y anidado RFC822; el paquete de pruebas del atomizador también pasó. Los dos llamadores citados no cambian por esta refactorización. Eso no implica invariancia de todo el pipeline cuando el export deposita nuevos `.eml` genéricos: H-02.
2. **Fidelidad del `.eml`: verificada para el depósito de mensajes de la etiqueta.** El filtro cambia qué binarios se materializan, no el raw escrito. Los controles comparan bytes completos con firmas dentro. El aplanado conserva su fallback anterior de reserialización con aviso; no extiendo la conclusión de byte-fidelidad absoluta a ese fallback.
3. **`Content-Disposition: attachment`: verificado para cabeceras válidas**, incluida capitalización `ATTACHMENT`. La excepción se aplica antes del MIME, CID y tamaño. No convierto esto en garantía sobre cabeceras malformadas o contradictorias: disposición desconocida pasa al filtro (H-01).
4. **Solo firma, sin subcarpeta: verificado** por el test existente. La decisión usa `depositables`, no todos los adjuntos. También sucede cuando la única imagen probatoria se clasifica erróneamente como firma, que es H-01.
5. **Contadores: verificados con matices.** Con extracción activada, `firmas_filtradas` cuenta los candidatos retirados y `attachments` las escrituras de adjuntos terminadas. Con `extract_attachments=False`, sigue contando firmas, aunque se haya solicitado no extraer ningún adjunto. No identifica nombres ni mensajes de las imágenes omitidas. Los contadores de `_emit_traza` se reconstruyen por tipo/ruta y pueden diferir: el `.eml` adjunto de H-02 cuenta como adjunto en el report y como correo en la traza.
6. **Los cuatro defaults están cableados en fuente.** Motor `email_export.py:1138`; helpers y opción Typer de `abrir_caso.py:301,355,912-917`; argparse en `export_label_emails.py:54-58`; checkbox `streamlit_app.py:762-790`. Se ejercitaron el motor y los CLI con dobles. **Ejecución de la UI Streamlit: SIN VERIFICAR**; solo inspección de `value=True` y de su propagación. H-03 es una rotura adicional, aunque el default esté bien.
7. **Los dos tests se invirtieron, no se borraron: verificado en el diff.** `test_export_label_plano_por_defecto_no_extrae_adjuntos` pasa a `test_export_label_extrae_adjuntos_POR_DEFECTO`, conservando el escenario y comprobando fichero/subcarpeta. `test_intake_email_no_extrae_adjuntos_por_defecto` pasa a `test_intake_email_extrae_adjuntos_POR_DEFECTO`, con el espía esperando `True`.

## Interacciones, medición y límites

**Layout ordinario.** `_recolecta_entradas`, `existing_message_ids`, `_emit_traza`, `items_desde_disco`, el inventario de la sala de máquina y `enumerar_rutas_eml` recorren recursivamente. La reproducción con PDF más firma comprueba raw fiel en subcarpeta, dos elementos reales del manifiesto, rutas M9 existentes, ambos índices cross-lote e inventario de dos ficheros. No he encontrado la antigua ceguera de los `.eml` en subcarpeta; H-02 es un problema distinto, de clasificación y procedencia.

**Migración #54.** Verificada sobre un caso sintético exportado al cajón legacy con `.eml` y PDF en subcarpeta: la migración conserva los bytes, remapea las dos rutas M9 a ficheros existentes y mantiene el índice de canal; un reexport posterior salta el mensaje y elimina el lote nuevo vacío. La primera versión de mi control esperaba dos ítems del manifiesto y falló: el export legacy también había generado `INDICE.md` y `CRONOLOGIA.md`. `intake_control.py:64-67` solo declara como estado de canal legacy los dos JSON; `migrar_layout_intake.py:275-281` inventaría los cuatro ficheros que llegaron al lote. Corregí el control para exigir exactamente las cuatro rutas de entrada y sus bytes, sin cambiar código ni tests del autor. El primer rojo queda conservado en `verificacion-final.log`; el control corregido pasó. Esta conservación de índices legacy es anterior a 6b.

**Idempotencia de la transición.** Se ejecutó el motor de base con su default antiguo y después el de head sobre el mismo destino: `skipped=1`, `written=0`, `attachments=0`, árbol byte-idéntico. El nuevo default no hace backfill de adjuntos ya exportados. Al repetir con `force=True` se conserva el `.eml` plano y aparece otra copia en subcarpeta más el PDF: dos `.eml`. Es la conducta anterior de `force` y `_ruta_unica`/`_dir_unico`, no una deduplicación nueva que haya roto 6b. El índice de Gmail evita la duplicación ordinaria; la marca por Message-ID declara duplicados, no suprime todas las escrituras del bucle principal.

**Adjuntos de hijos y rescates.** `_aplana_anidados:549-553` y `_deposita_mensaje_rescatado:757-760` escriben el `.eml` directamente. Sus adjuntos no pasan por `es_firma_incrustada`, pero tampoco se extraen sueltos: en la prueba hijo con PDF y logo, `nested_flattened=1`, `attachments=0`, `firmas_filtradas=0`. El rescatado con PDF tiene el mismo límite. Es preexistente y no lo presento como regresión; sí impide interpretar el default como extracción de todos los adjuntos de todo correo alcanzable. El atomizador conserva su ruta independiente de extracción.

**Falsos negativos previstos.** Logos nombrados de 50 KiB o más, imágenes sin CID y las marcadas `attachment` se conservan. Un GIF pequeño nombrado, `inline` y con CID se filtra; uno sin CID se conserva. Una parte `inline` sin nombre ni disposition `attachment` ni siquiera entra en la lista de adjuntos de `particionar_eml`. Son límites explícitos del criterio, no nuevos hallazgos por incumplimiento de ese criterio. No hay una medición reproducida de su frecuencia en el corpus.

**Rastro de firmas.** `firmas_filtradas` vive en el report y su resumen. No se guarda en los detalles de `upload_email`, ni el manifiesto de disco explica las imágenes omitidas. La UI muestra escritos/saltados/adjuntos (`streamlit_app.py:801-806`), no ese contador. El `.eml` permite reconstruirlo, pero no existe un inventario durable de decisiones del filtro. Se deja como límite de observabilidad, sin inventar una obligación de esquema que el mandato no fija.

**Medición de 24 casos / 462 correos / 444 adjuntos: SIN VERIFICAR.** Las copias entregadas no contienen ningún fichero `.eml` de corpus. No se aporta el script ni los inventarios de la medición y no he localizado un script equivalente en el objeto. No puedo reconstruir las tres versiones de «subcarpeta del extractor», validar su selección, la mediana ni determinar visualmente si los 140 candidatos eran logotipos. La tabla de dispositions/CID/tamaño mide atributos; por sí sola no certifica la clase semántica «firma». Los falsos positivos de H-01 satisfacen exactamente la fila marcada para filtrar. El contraejemplo de H-02 refuta la garantía universal, no el cero observado que se atribuye al corpus.

## Calidad de las pruebas y mutación

El fixture `_mensaje` **sí produce** partes `inline` con `Content-ID`. Los asertos positivos no pasan por ausencia de partes. Sin embargo, el cuerpo es texto plano «Cuerpo con firma.», sin `cid:` ni HTML, y el contenedor es `multipart/mixed`: los tests congelan «CID presente», no «referencia desde el cuerpo». Si se le pasa disposition `None`, `EmailMessage.add_attachment` genera `attachment`; para representar cabecera ausente hay que eliminarla realmente. Ninguno de los 15 tests nuevos ejerce ese caso ni un TIFF probatorio.

El test llamado `test_sin_extraer_adjuntos_el_eml_sigue_siendo_FIEL` llama en realidad con `extract_attachments=True`. Su aserto de fidelidad es útil y pasa, pero el nombre no demuestra la rama sin extracción.

**Arnés 6a adaptado:** mismos 17 parches, pruebas `test_email_export_filtro_ruido.py` y `test_email_export_r1_remediaciones.py`, baseline 56 passed. Mueren 16; **M15 sobrevive** (56 passed), coincidiendo con su declaración de ausencia de cobertura. No se ha montado una junction real. M08 mata además `test_es_lote_del_caso_falla_CERRADO_si_resolve_revienta`, que no está en el conjunto esperado del arnés original; no presento el resultado como una ejecución literal y limpia de su comparador. La adaptación conserva logs y códigos de salida y no interpreta una colección fallida como muerte.

**Diez mutaciones 6b del revisor:** ejecutadas contra los 136 tests de firmas, export y `abrir_caso`; baseline 136 passed. No se incluyeron mis reproducciones en esa medición, para medir la cobertura que trae el autor.

| Mutación | Resultado |
|---|---|
| S01: retirar excepción `attachment` | Muere en su test de protección. |
| S02: retirar requisito `image/*` | Muere en el test del PDF inline. |
| S03: retirar requisito CID | Muere en el test sin CID. |
| S04: cambiar `<` por `<=` en el umbral | Muere en el test de frontera exacta. |
| S05: filtrar solo disposition `inline`, conservando la ausente | **Sobrevive: 136 passed.** |
| S06: conservar todos los `image/tiff` | **Sobrevive: 136 passed.** |
| S07: incrementar `firmas_filtradas` solo cuando se solicita extracción | **Sobrevive: 136 passed.** |
| S08: hacer que `split_eml` retire firmas | Muere en los dos tests de compatibilidad. |
| S09: devolver el default del motor a `False` | Muere en los dos tests del default. |
| S10: escribir todos los adjuntos, incluidas firmas | Muere en los tests de depósito y default. |

No añadir mutantes en 6b **no implica que sus cuatro condiciones carezcan de tests**: S01–S04 los ponen rojos. Las fronteras que quedan sin contratar son la disposición realmente ausente, TIFF y contenido probatorio pequeño, la referencia efectiva desde el cuerpo/contexto MIME, el significado del contador con extracción desactivada, el `.eml` con MIME genérico atravesando filtro/procedencia, y la compatibilidad del argumento positivo. Un cambio de tratamiento de TIFF que sobreviva no demuestra que deba filtrarse: demuestra que los tests no fijan esa decisión. Las reproducciones nuevas distinguen esas situaciones.

## Cierre

SHA-256 de cierre de `C:/t/r6b2244obj/head/core/email_export.py`:
`c02a493c8a2ef9b839f624236cfb5ff5742b856c5d328eef3fce263547915539`.

Coincide con el de apertura y con el de `h/core/email_export.py` tras restaurar todos los mutantes. Cierre comprobado el 2026-09-06, 22:55:30 +02:00, según reloj del entorno. Informe entregado en UTF-8 sin BOM, LF y un único salto final; su digest se devuelve fuera del fichero.

El rechazo se fundamenta en la omisión de imágenes probatorias y en la puerta de entrada de `.eml` genéricos, no en exigir eliminar todo falso negativo ni en los límites preexistentes. La adjudicación corresponde al autor contra la fuente y las reproducciones.

NO-SHIP


---

## 2. Evidencia verificada por el adjudicador

Contrastado contra la fuente ANTES de remediar:

- **H-01** — `es_firma_incrustada` hace `if not parte.get("Content-ID")`, que comprueba **que la
  cabecera exista**, no que la imagen este referenciada desde el cuerpo. **Mi propio docstring dice
  «referenciada desde el cuerpo»: el comentario afirma mas de lo que el codigo hace**, que es el
  defecto que escribi como memoria dos horas antes de cometerlo. Confirmado tambien el segundo
  tramo: `core/adjuntos_contenido/router.py` omite las imagenes `< IMG_DECORATIVA_MAX` (50 KB) con
  `metodo="omitido"`, asi que la recuperacion por el atomizador **no** salva el texto. CONFIRMADO.
- **H-02** — `particionar_eml` filtra por `get_content_type() == "message/rfc822"`, o sea **por
  MIME**. Un `application/octet-stream; filename="x.eml"` no casa, pasa y se escribe. Y
  `MEJORAS_FUTURAS.md` §55.1 lo tenia documentado, con el aviso de que el flag es lo que los hace
  visibles. CONFIRMADO, y la afirmacion «por construccion» **retirada**.
- **H-03** — el diff sustituyo `--extraer-adjuntos` por `--no-extraer-adjuntos` en vez de anadir el
  negativo: una invocacion existente con el positivo muere con `SystemExit(2)`. La skill versionada
  `exportar-correos-etiqueta` todavia lo documenta. CONFIRMADO.
- **H-04** — `filtrar_ruido` solo gobierna el bucle principal; `_aplana_anidados` y
  `_deposita_mensaje_rescatado` aplican `clasificar_ruido` incondicionalmente. **Defecto que
  introduje yo el mismo dia**, al remediar el H-01 de la ronda anterior: la vuelta atras que el
  plan anuncia no funciona por esas dos puertas. CONFIRMADO, y correctamente atribuido por el
  revisor a la 6a y no a la 6b.

Digest del bloque literal recomputado por el guard G8 de `tests/test_docs_gobernanza.py`.
