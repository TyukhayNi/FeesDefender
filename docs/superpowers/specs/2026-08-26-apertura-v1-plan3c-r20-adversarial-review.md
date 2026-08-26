---
tipo: revision-adversarial
objeto: "diseño del Plan 3C: la poda y el archivado"
objeto_rev: "rama claude/feesdefender-plan3-decision-batches-844080, commit d1b09e2"
commit: d1b09e2
ronda: "20"
revisor: Codex
veredicto: REQUIERE-REVISION
marcador_nonce: h2xw
sha256_informe: 77ac21c54ede785c0bf54ae72515939eb8f3f738950e46f1f0cca58bda7ff74a
adjudicado_en: docs/superpowers/plans/2026-08-26-apertura-v1-plan3c-poda-archivado.md §5
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R20.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicación** vive en el **§5 del plan**
> (`docs/superpowers/plans/2026-08-26-apertura-v1-plan3c-poda-archivado.md`). Es la ronda de **DISEÑO**: se corrió **antes de escribir
> una línea de código**, que es para lo que existe.
>
> Veredicto `REQUIERE-REVISION`: **13 hallazgos** — 3 CRÍTICOS, 6 ALTOS, 3 MEDIOS, 1 BAJO. Adjudicados: **13 confirmados,
> 0 refutados.**
>
> **Esta ronda EJECUTÓ.** El revisor corrió censo destructivo por AST además del textual, seis sondas propias (colisión de nombres, retirada no comprobada, ruta de `_organizado/`, gate de vistas, `Path.replace`, longitud de ruta) y la verja existente (241 pasados, 3 omitidos), y midió el comportamiento en vez de
> deducirlo. Los críticos salieron de las sondas.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:h2xw -->

REQUIERE-REVISION

## Resumen

Ataqué el censo destructivo con búsqueda textual y AST sobre `core/` y `scripts/`, y seguí los llamadores y entrypoints de cada sitio relevante.
Ejecuté sondas independientes sobre una copia del objeto para la colisión de nombres, la retirada no comprobada, la ruta de `_organizado/`, el gate de vistas, `Path.replace` y longitud de ruta.
La colisión del §1.3 y la retirada ficticia por `ignore_errors=True` son reales y quedaron reproducidas con hashes y estado del árbol.
El hallazgo principal es anterior a la implementación: la pieza K no tiene una operación de retirada en la costura heredada y `clase="derivado"` no produce el rechazo que el plan afirma.
Además, el censo omitió un `unlink` vivo dentro de `00_Input`, y el plan no asigna remedio a dos destrucciones que sí censó; por ello la pieza M no puede quedar verde con el alcance escrito.
La pieza I contradice su propia premisa: `Path.replace` sí sobrescribe un destino existente, medido; tampoco define recuperación tras un fallo a mitad de un lote.
La pieza L conserva escrituras y borrados dentro de la zona vetada y solo nominaliza una excepción general; no acredita que `_organizado/` contenga exclusivamente copias al retirarlo.
La verja relevante existente pasó (241 passed, 3 skipped), pero `pytest-randomly` no está instalado en el intérprete indicado y las dos semillas quedaron SIN VERIFICAR.

## Hallazgos

### H20-01 — CRÍTICO — El «censo real» omite otro `unlink` vivo dentro de `00_Input`

**Qué afirma el plan.** «**Cuatro destrucciones vivas que las 27 clases del §25 no enumeran**» (§1.1, líneas 51-53), y declara que la peor no enumerada es `local_organizer.py:1027`.

**Por qué está mal.** El barrido AST encontró `scripts/migrar_layout_intake.py:120-123`: después de mover físicamente el resto del cajón, la fase 2 ejecuta `hijo.unlink()` sobre duplicados de control bajo `base = caso_path(case_id) / "00_Input"` (`:66-73`, `:81`, `:120-123`). Es una vía viva: el mismo fichero define el comando Typer en `:156-176`. No es temporal ni staging; es un borrado irreversible dentro de la misma zona cuya invasión fundamenta C12. No aparece en la tabla del §1.1 ni en las exenciones de M.

El censo también omitió las formas que él mismo declara abiertas: `Path.rmdir` dentro de lotes (`core/email_export.py:1085,1108-1113`) y bajo `00_Input/05_CRM` (`scripts/migrate_05crm_buckets.py:303,349-355`); `shutil.move` del expediente completo (`core/casos/case_locator.py:270-316`, llamado por `streamlit_app.py:1471`); y destrucción remota mediante `rclone moveto`/`rmdirs` (`scripts/repository_cli.py:321-327,782,979,990`). No encontré `rclone delete`, `purge` ni `sync`, pero `moveto` retira el origen remoto y `rmdirs` elimina directorios.

La propia aritmética del §1.1 tampoco sustenta «cuatro»: solo tres filas están rotuladas **NINGUNA** (`local_organizer.py:1027`, `:845`, `sala_lectura.py:646`). Si la cuarta es `sala_maquina.py:568`, la tabla la rotula #25 y deja de ser «no enumerada».

**Consecuencia práctica.** El diseño puede implementarse completo y conservar una retirada irreversible dentro de `00_Input` que ni pasa por I/L ni entra en el guard M. El criterio de salida 5 sería falso aun con todos los tests previstos verdes.

### H20-02 — CRÍTICO — El plan no remedia dos destrucciones que censó y no puede satisfacer su propio guard

**Qué afirma el plan.** M exige que «**Ningún `unlink`, `rmtree` o `replace` de producción sobre una ruta bajo un expediente**» quede fuera de I o `destino_seguro` (líneas 215-226), y el criterio 5 exige lo mismo. El §1.1 censó `core/local_organizer.py:845` y `core/sala_lectura.py:646` como NINGUNA.

**Por qué está mal.** Las piezas y el File Structure solo asignan a `local_organizer.py` el `rmtree` de `reconstruir` (`:1027`); no asignan la retirada `old.unlink()` de `ejecutar_plan` (`:841-848`). Esta última es alcanzable desde `scripts/organizar_local.py:52-55` y desde Streamlit (`streamlit_app.py:1235-1249`). El plan excluye expresamente arreglar `core/sala_lectura.py` (líneas 332-333), pero su CLI llama directamente a la función destructiva: `scripts/sala_lectura.py:64` → `poblar_sala_lectura` → `old.unlink()` en `core/sala_lectura.py:643-651`. Por fuente, es vía viva; no hace falta telemetría de uso para demostrar alcanzabilidad.

M solo permite eximir `sala_lectura.py` «si y solo si» se prueba que su CLI ya no es vía viva. Esa condición es falsa en este árbol. Tampoco propone eximir `local_organizer.py:845`, lo que sería incompatible con su propia clasificación como destrucción viva.

**Consecuencia práctica.** Task 4 deja ambos `unlink` en pie y Task 5 tiene que fallar al verlos. Si el guard no falla, no demuestra la propiedad que proclama; si falla, el plan no tiene una tarea que lo lleve a verde.

### H20-03 — CRÍTICO — La costura heredada no puede expresar la retirada no desviable que K da por diseñada

**Qué afirma el plan.** «Las dos pasan por la costura de 3A con `clase="derivado"`» y «la retirada no se desvía, se rechaza» (líneas 186-194).

**Por qué está mal.** En la costura ya construida, `deposito(..., clase="derivado")` consulta el guard y compone una base en la bandeja cuando `decision.desviar` es cierta (`core/casos/escritura.py:161-170,208-218`). `Deposito` solo ofrece `dir_para`, `escribir_texto` y `escribir_bytes` (`:92-116`); no representa un origen vivo que retirar ni una operación archivo+moción del origen.

3B añade rechazo únicamente con `agregado=True`: su interfaz prevista es `deposito(..., clase, agregado=False, ...)`, y solo `agregado=True` lanza `AgregadoNoDesviable` (Plan 3B, líneas 175-186). 3C redefine la etiqueta «categoría A» «por otra razón», pero no añade ningún discriminante de retirada ni amplía la interfaz. `clase="derivado"` por sí sola sigue siendo desviable conforme a 3A/3B.

**Consecuencia práctica.** No existe una llamada descrita por K que archive en el destino autorizado y retire el origen canónico solo cuando proceda. Una implementación literal recibirá un depósito desviado o reutilizará falsamente `agregado=True`; en ambos casos, la semántica declarada no sale de la interfaz del plan.

### H20-04 — ALTO — La pieza I conserva exactamente la primitiva de sobrescritura que dice eliminar

**Qué afirma el plan.** «`os.link` / `p.replace` sobre un destino existente es un error, no un caso a absorber» (líneas 162-165).

**Por qué está mal.** `Path.replace` invoca reemplazo, no renombrado exclusivo. Sonda ejecutada: con `src.bin=b"NEW"` y `dst.bin=b"OLD"`, `src.replace(dst)` terminó sin excepción, borró `src.bin` y dejó `dst.bin=b"NEW"`. Esto contradice también la explicación correcta del propio §1.3, que atribuye la pérdida actual a que «`replace` sobrescribe».

La colisión actual quedó medida con bases distintas: `03_MD/x.md` tenía SHA-256 `43918732...4bfa4eb9` y `02_Documentos/bundle/nested/x.md` tenía `9e41c9c...f5e5702c`. `archivar_bundle_entero` devolvió `['x.pdf', 'x.md', 'x.md']`, pero el archivo contenía solo `x.pdf` y un `x.md`, con el SHA del segundo origen. La misma clase existe en `publicar_segmentos`: un `03_MD/old.md` (`faee2a72...94647e3c`) y un residuo `_staging/old.md` (`adb582a1...465fe36`) devolvieron dos `old.md`, pero el archivo conservó solo el residuo.

**Consecuencia práctica.** Si I usa una de las primitivas que enumera (`p.replace`), P3 no puede garantizar «rompe, no sobrescribe» y C10 sigue violada. Además, una prueba limitada a `archivar_bundle_entero` no cubre la segunda ruta viva de aplanado en `publicar_segmentos` (`core/sala_maquina.py:500-535`).

### H20-05 — ALTO — I/J no definen el fallo a mitad del lote ni una reentrada segura con el mismo sello

**Qué afirma el plan.** I preserva rutas y rompe ante un destino existente; J devuelve `archivados` y `residuo`; P3-P5 cubren destino existente, residuo y `rmtree` fallido.

**Por qué está mal.** El movimiento es secuencial. Si los primeros `k` ficheros se mueven y el `k+1` falla, la excepción sale antes de la comprobación de residuo que J describe: no hay resultado con `archivados`/`residuo`. En una reentrada con el mismo sello, los destinos de los `k` ya movidos existen: con la regla exclusiva de P3 la operación vuelve a romper antes de alcanzar el residuo; con `p.replace` los sobrescribe. Ninguna frontera inyecta un fallo de movimiento intermedio ni verifica el estado repartido entre árbol vivo y archivo.

El «sello de la corrida» tampoco existe como tal en el código del que parte el plan. `_sello_reproceso()` tiene resolución de un segundo (`core/sala_maquina.py:470-472`) y se recalcula por llamada de bundle en `:850` y `:918`, no una vez en el entrypoint. P16 solo prohíbe recalcular por fichero; no acredita un sello único y estable de corrida para #18, #20 y todos los bundles.

**Consecuencia práctica.** Un fallo transitorio puede dejar una generación partida y sin resultado verificable. La siguiente tentativa puede quedar bloqueada por el propio destino preexistente que P3 exige, o distribuir una misma retirada entre sellos diferentes.

### H20-06 — ALTO — El §1.4 atribuye a #18 un gate que no gobierna la poda de vistas

**Qué afirma el plan.** «si la corrida acumuló errores, `report.poda_omitida = True` y no se poda (`pipeline.py:205-210`)» y «el gate de #18 sigue funcionando» (líneas 117-119 y P9).

**Por qué está mal.** El `if report.errores` gobierna solo el `glob` de `mensajes` (`core/email_atomize/pipeline.py:200-226`). La generación y poda de vistas viene después y su `unlink` es incondicional respecto de ese gate (`:248-270`).

Sonda ejecutada: una primera corrida creó `vistas/v1.md`; en la segunda se inyectó `ValueError("fallo-inyectado")` al construir el único mensaje y se dejó `vistas: []`. El informe devolvió `errores=['a@x: fallo-inyectado']` y `poda_omitida=True`, pero `v1.md` desapareció (`view_survives=False`).

**Consecuencia práctica.** K puede «conservar» el gate existente y pasar P9 sobre mensajes mientras sigue retirando vistas con una fotografía parcial. El supuesto que justifica generalizar ese gate a #20 es falso para la mitad de #18.

### H20-07 — ALTO — L no aplica D4 a `_organizado/` y la excepción nominal amplía una puerta de escritura general

**Qué afirma el plan.** Elige «dejarlo donde está y hacer que su retirada atraviese `destino_seguro` con una excepción nominal» (líneas 196-211), bajo C12.

**Por qué está mal.** `_organizado/` es derivado según el propio plan, pero Task 4 solo lleva el `rmtree` por `destino_seguro`; no lo pasa por I ni conserva su contenido en `99_Versiones anteriores`. Por tanto, el artefacto derivado sigue desapareciendo y C9/D4 no se aplican al hallazgo que motivó L.

Además, el problema no es solo el borrado. `ejecutar_plan` crea directorios, copia bytes con `shutil.copy2` y escribe índices/README/audit directamente bajo `_organizado` (`core/local_organizer.py:820-876,902-953`), y Streamlit lo invoca en `streamlit_app.py:1235-1249`. L conserva todas esas escrituras dentro de la zona que §1.2 llama intocable. `destino_seguro` es una puerta general de escritura (`core/sala_maquina.py:423-436`); una excepción por basename `_organizado` podría autorizar cualquier `00_Input/**/_organizado`, y una excepción por ruta exacta seguiría autorizando a todos sus llamadores, no solo a `reconstruir`. P13 solo muta la excepción hasta «`00_Input` entera»; no prueba exactitud de componentes ni limitación por operación/llamador.

La sonda resolvió la ruta a `case/00_Input/01_Drive EV/_organizado`, colocó allí `cliente_aporto_aqui.pdf` y ejecutó `reconstruir` con planificación/ejecución neutralizadas: el fichero no sobrevivió. Un original hermano fuera de `_organizado` sí sobrevivió. El código no verifica el audit ni los hashes antes de decidir que todo lo que encuentre bajo ese nombre es una copia.

**Consecuencia práctica.** El plan institucionaliza una excepción a la zona vetada sin cerrar el conjunto de escrituras que ya la atraviesan y mantiene una retirada irreversible de cualquier contenido colocado bajo ese nombre, sea o no una copia acreditada.

### H20-08 — ALTO — J cambia el tipo, pero no diseña qué hace su único llamador con el residuo

**Qué afirma el plan.** «La firma pasa de `list[str]` a un resultado con `archivados` y `residuo`» y «el llamador decide» (líneas 169-179).

**Por qué está mal.** El único llamador de producción encontrado está en `core/sala_maquina.py:848-866`. Trata el resultado como una lista: `if archivados`, `len(archivados)`, interpolación de conteo y serialización directa en `details["archivados"]`. El File Structure no identifica este contrato ni ninguna frontera especifica la decisión ante `residuo`.

Con un `dict` de dos claves, `if` será verdadero aunque ambas listas estén vacías y `len` será siempre 2; con una dataclass sin `__len__`, `len` lanza; con un objeto no serializable, el evento falla. Incluso si el llamador extrae `resultado.archivados`, el plan no dice si continúa al passthrough, aborta o marca cobertura cuando `residuo` no está vacío.

**Consecuencia práctica.** El cambio de firma rompe o falsea el conteo/evento y deja abierta la decisión que afecta al bucle de integridad de bundles. P4/P5 solo prueban el productor del resultado, no el comportamiento observable del llamador.

### H20-09 — ALTO — «Rechazar la retirada» puede ocurrir después de haber publicado una corrida parcial

**Qué afirma el plan.** «Sobre un caso prestado, la retirada rechaza» y P10/P11 verifican rechazo y cero ficheros retirados.

**Por qué está mal.** En `email_atomize`, las fichas se escriben en `:165,187`, los agregados en `:242-251` y las vistas en `:263` antes de los `unlink` de `:220` y `:267`. En `adjuntos_contenido`, cada contenido y su estado incremental se escriben en `:86,104` antes de la poda de `:106-110`. Si el rechazo se decide al llegar a la retirada, la corrida ya produjo efectos —en el diseño 3B, potencialmente en la bandeja— y termina a mitad. El gate existente demuestra que hay un tercer resultado semántico distinto de «desviar el unlink»: no retirar y declararlo (`poda_omitida`); 3C no compara esa salida con abortar tarde.

P11 solo exige hash del árbol vivo y P10 código de salida; no exige que bandeja, eventos, estado local y agregados queden sin cambios tras ese rechazo tardío. Esto contradice la exigencia de cuatro planos del §25.4 de la spec (`docs/...design.md:1800-1806`) y la frontera de 3B (`Plan 3B:365-370`).

**Consecuencia práctica.** El sistema puede devolver rechazo con cero retiradas y, aun así, dejar una generación parcial escrita. El test previsto lo declararía correcto porque observa precisamente el plano que no cambió.

### H20-10 — MEDIO — La ruta propuesta añade 52 caracteres sin presupuesto ni frontera

**Qué afirma el plan.** I usa `99_Versiones anteriores/reproceso_<sello>/<ruta relativa al caso>` y no incluye una frontera de longitud.

**Por qué está mal.** Sonda ejecutada en `%TEMP%`: una fuente de 240 caracteres produjo un destino de 292, exactamente 52 más. La operación funcionó en este host porque `HKLM/.../FileSystem.LongPathsEnabled=1`; esto no refuta el riesgo. El propio repo documenta rutas reales de hasta 377 caracteres en `01_Procesado`, 141 de 571 por encima de 260 y herramientas de usuario que ya fallan (`docs/MEJORAS_FUTURAS.md:4247-4292`). El archivo propuesto llevaría una ruta de 377 a aproximadamente 429.

Los caracteres inválidos no son un nuevo riesgo si la relativa se obtiene de un `Path` que ya existe en el mismo volumen: esos componentes ya fueron aceptados por el sistema de ficheros y el prefijo fijo es válido. La longitud sí cambia materialmente y no aparece en P1-P16.

**Consecuencia práctica.** Las pruebas bajo un basetemp corto pueden pasar mientras el archivado de una ruta real profunda falla antes de completar la retirada. La sonda de Python tampoco acredita apertura por Office/Drive Desktop, distinción que el propio repo declara expresamente.

### H20-11 — MEDIO — M no puede inferir estáticamente «ruta bajo un expediente» con el guard descrito

**Qué afirma el plan.** Un guard AST, sin números de línea, decide si un `unlink`/`rmtree`/`replace` de producción actúa «sobre una ruta bajo un expediente», con exenciones por nombre (líneas 213-226).

**Por qué está mal.** En los casos reales, la condición depende de flujo interprocedimental: `org` viene de `_organizado_dir` → `_drive_ev_dir` → `caso_path`; `old` se compone desde un valor leído del audit; `hijo` viene de un iterador sobre `base`; y los comandos remotos se construyen en una función y se ejecutan en otra. El AST local puede reconocer la ortografía de una llamada, no demostrar el valor de la ruta. También se elude con aliases (`borrar = p.unlink; borrar()`), wrappers, `getattr`, `os.remove`, `Path.rmdir`, `shutil.move`, apertura truncante o subprocess; todas son formas que el plan declara fuera del corpus.

P14 solo exige que muerda «un `unlink` nuevo sobre un expediente», sin especificar un mutante que pase por alias/dataflow, y P15 solo congela la lista de exenciones. Un detector sintáctico puede matar ese mutante preparado y seguir sin decidir la propiedad semántica.

**Consecuencia práctica.** M será o bien sobreinclusivo (marca temporales y requiere excepciones crecientes) o bien decorativo (reconoce patrones conocidos y deja pasar formas equivalentes). «La lista solo puede encoger» no convierte esa clasificación en una prueba de contención.

### H20-12 — MEDIO — Las dieciséis fronteras no son dieciséis mutantes independientes y omiten propiedades decisivas

**Qué afirma el plan.** «Dieciséis fronteras, dieciséis mutantes, cada uno muerto por la suya» (líneas 230-252, criterio 6).

**Por qué está mal.** P1 y P2 declaran literalmente el mismo mutante: volver a `archivo / p.name`; necesariamente lo matan dos tests o son la misma frontera. P4 y P5 se solapan al volver a `ignore_errors=True`/tragar el fallo; P10 y P11 observan dos efectos del mismo mutante de desvío. Por construcción, no hay correspondencia uno-a-uno.

Faltan fronteras para: fallo del segundo de varios movimientos y estado posterior; reentrada con sello repetido tras fallo parcial; comportamiento del llamador ante `residuo`; gate de vistas con `report.errores`; segunda ruta de aplanado en `publicar_segmentos`; fuente fuera del caso/reparse point; presupuesto de longitud; exactitud de la excepción `_organizado`; primitivas destructivas distintas de tres nombres; y los cuatro planos después de un rechazo tardío.

**Consecuencia práctica.** El arnés puede cumplir el conteo 16/16 y no matar los defectos que deciden atomicidad, no sobrescritura, cobertura real del gate y cero efectos sobre caso prestado.

### H20-13 — BAJO — D4 está parafraseada como una decisión más estrecha que la fuente

**Qué afirma el plan.** Presenta D4 como «la poda archiva en vez de borrar» (líneas 13-14).

**Por qué está mal.** La fuente dice «la poda **archiva o inactiva**, y el histórico se conserva» (§24:1718-1722), y las filas #18/#20 repiten «archivar o inactivar» (§25:1779-1781). Elegir archivado es compatible con la spec, pero no es la cita literal ni la única decisión canónica. El plan no contrasta su elección con la alternativa permitida.

**Consecuencia práctica.** La trazabilidad de decisión queda sobredicha: problemas propios del archivo —colisiones, rutas, crecimiento, merge— se presentan como impuestos por D4 cuando derivan de una elección de 3C.

## Lo que verifiqué y resultó CORRECTO

- **§1.1, filas de la spec:** `core/email_atomize/pipeline.py:220` y `:267` retiran huérfanos de mensajes/vistas y corresponden a #18; `core/adjuntos_contenido/pipeline.py:109` retira `*.contenido.md` y corresponde a #20. La salvedad es H20-06: solo el primero está bajo el gate de errores.
- **`archivar_bundle_entero`:** `core/sala_maquina.py:539-569` mueve los ficheros y luego llama `shutil.rmtree(..., ignore_errors=True)`. El borrado es de artefactos de #24 después de depositarlos en #25; llamarlo simplemente «#25 (destino)» describe el destino, no la clase de lo retirado.
- **Staging:** `core/sala_maquina.py:535` y `:891` actúan sobre `_staging`; clasificarlos como staging y no como poda de datos vivos es correcto. `core/anon/separar.py:594-596` limpia el set parcial producido por la propia operación tras una excepción.
- **Sitios NINGUNA:** `core/local_organizer.py:845`, `:1027` y `core/sala_lectura.py:646` no tienen fila propia en las 27 clases del §25. La conclusión de que están fuera de la tabla es correcta; el plan no los cierra, según H20-02.
- **Ruta de `_organizado`:** quedó resuelta y medida como `caso_path(case_id)/00_Input/01_Drive EV/_organizado`. `reconstruir` es alcanzable por `scripts/organizar_local.py --rebuild` (`:41,58-59`). Streamlit importa el módulo pero no llama `reconstruir`; solo `planificar` y `ejecutar_plan` (`streamlit_app.py:1212,1249`).
- **Naturaleza actual de `_organizado`:** el productor normal copia desde el espejo con `shutil.copy2` (`local_organizer.py:847-848`) y el módulo declara audit por SHA (`:1-13`). La sonda conservó el original hermano; no demostró que el productor normal borre originales. Sí demostró que el `rmtree` no valida el contenido encontrado bajo el nombre reservado.
- **Colisión del §1.3:** CONFIRMADA con dos bases, contenidos y SHA distintos. Se perdió el primero y la lista devolvió dos veces el basename.
- **Retirada reportada sin comprobar:** CONFIRMADA por inyección controlada de un `rmtree` que no hizo nada. La función llamó con `ignore_errors=True`, devolvió `['only.bin']` y la carpeta siguió existiendo.
- **Llamadores de J:** encontré una definición y un único llamador de producción de `archivar_bundle_entero`, ambos en `core/sala_maquina.py` (`:539`, `:848`). No hay llamadas directas en tests.
- **`MERGE_EXCLUSIONS`:** `99_Versiones anteriores/**` no está en `core/config.py:391-399`, como el plan declara SIN VERIFICAR; `_tiempos.jsonl` tampoco está en esta versión.
- **Spec y predecesores:** 3A asigna #18/#20/#25 a 3C y la costura trata `derivado` como guard obligatorio. 3B define categoría A por read-modify-write y rechazo, no por retirada. 3C puede extender el concepto, pero necesita un discriminante que hoy no figura (H20-03).
- **Verja existente relevante:** ejecutada sobre la copia con el intérprete indicado y `--basetemp` corto: `241 passed, 3 skipped in 51.75s`. Los tres skips son `test_split_sala_maquina_e2e.py` marcados lentos (`--runslow`). Esto acredita el baseline de la selección, no el diseño futuro.
- **Caracteres inválidos:** no encontré un problema nuevo si I deriva la relativa de una ruta local existente. El sello actual (`AAAA-MM-DD_HHMMSS`) y los componentes fijos son válidos en Windows.

## Lo que NO pude verificar

- **Dos semillas 777 y 31337:** SIN VERIFICAR. El intérprete indicado tiene `pytest 9.1.1`, pero no carga `pytest-randomly`; `--randomly-seed=777` abortó antes de recoger tests como argumento desconocido. No instalé dependencias ni presento ese intento como suite ejecutada.
- **Suite completa:** SIN VERIFICAR. Ejecuté la verja relevante de 18 ficheros; no la totalidad de los tests del repo ni los tres E2E lentos.
- **Sharing violation real de Drive Desktop:** SIN VERIFICAR. La retirada ficticia se demostró por inyección de fallo/no-op sobre `rmtree`, no bloqueando un fichero real con Drive Desktop.
- **Fallo MAX_PATH del archivado en `G:`:** SIN VERIFICAR. La expansión 240→292 quedó medida y funcionó en este host con `LongPathsEnabled=1`; no se ejecutó contra un expediente real, Drive Desktop ni una aplicación no long-path-aware.
- **Uso humano efectivo de las CLI:** SIN VERIFICAR. La alcanzabilidad por fuente de `organizar_local`, `sala_lectura`, `migrar_layout_intake` y Streamlit sí quedó verificada; no medí telemetría de invocación.
- **Interacción real de `99_Versiones anteriores/**` con el merge de tres vías:** SIN VERIFICAR, igual que declara el plan.
- **Tamaño/retención del archivo en expedientes reales, salto NTP, seis remediaciones R13 y exhaustividad dinámica absoluta:** SIN VERIFICAR. El AST amplió el corpus, pero no prueba ausencia de destrucción vía código dinámico, binarios externos o rutas construidas fuera de los patrones revisados.

## SHA-256 del documento revisado

- **Al abrir:** `96CCAD9963F1FA035E5C56C2001D927BF3677F31E7BF7505C9EE786033E3CB4F`
- **Al cerrar:** `96CCAD9963F1FA035E5C56C2001D927BF3677F31E7BF7505C9EE786033E3CB4F`

<!-- informe-literal:fin:h2xw -->

## 2. Evidencia verificada por el adjudicador

**Contra la fuente, no contra el informe.** Lo que el adjudicador comprobó por su cuenta antes de
aceptar los críticos:

1. **H20-01** — el censo del §1.1 omite `scripts/migrar_layout_intake.py:124`, un `unlink` vivo dentro de `00_Input` por vía Typer; y su total («cuatro») no cuadra con su propia tabla, que rotula **tres** filas «NINGUNA». **Verificado en la fuente** por el adjudicador, que además lo tenía en su propia salida de `grep`.
2. **H20-02** — el plan no asigna remedio a `local_organizer.py:845` ni a `sala_lectura.py:646`, y su exención condicional para `sala_lectura` es falsa: `scripts/sala_lectura.py:64` llama a la función destructiva.
3. **H20-03** — la clase `derivado` produce **desvío**, no rechazo, y la costura de 3A no tiene operación de retirada: la pieza K da por diseñado algo que no existe.

**Lo que el revisor verificó y resultó CORRECTO**, y que coincide con lo que el plan ya había
medido:

- la colisión de nombres del archivado es real, reproducida con hashes — coincide con la sonda del §1.3 del plan;
- la retirada ficticia por `ignore_errors=True` es real;
- el `rmtree` dentro de `00_Input` es real y alcanzable;
- la verja existente pasa (241 pasados, 3 omitidos).

**Lo que el revisor NO pudo verificar, y se declara como tal** (no como refutado): su intérprete no
tiene `pytest-randomly`, así que **la suite con las dos semillas (777 y 31337) queda SIN VERIFICAR
por su parte**; cinco módulos MCP no coleccionan por una dependencia ausente de su entorno; y sin
`.git` no puede acreditar la genealogía del archive, solo su contenido y su hash.

## 3. Cadena del acta

- `marcador_nonce: h2xw`, un par de marcadores en orden, el nonce no aparece fuera de ellos
  salvo en el frontmatter y en esta línea.
- `sha256_informe` recomputado al archivar sobre el bloque literal canonicalizado:
  `77ac21c54ede785c0bf54ae72515939eb8f3f738950e46f1f0cca58bda7ff74a`.
- **Objeto no mutado:** el revisor operó sobre un `git archive` sin `.git` y reportó el `sha256` del
  documento revisado **al abrir y al cerrar**, coincidentes. Ésa es la prueba de no-mutación que
  sustituye al `git status` limpio.
- **Aviso de método, de esta sesión:** al calcular el digest de la R20 obtuve un valor y dos minutos
  después otro — el revisor **seguía escribiendo**. La presencia de `INFORME.md` no es la señal de
  fin; lo es la salida del proceso. Un digest solo significa algo sobre un fichero terminado.
