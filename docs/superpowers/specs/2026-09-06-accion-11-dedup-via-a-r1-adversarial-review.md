---
tipo: revision-adversarial
objeto: "diff 8bfd098..cb63770 — un fichero, un espejo: dedup por sha256 con procedencias (MEJORAS #147 vía A, PLAN fila #21 acción 11, PR #296)"
objeto_rev: "1"
commit: "cb63770"
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: v3rt
sha256_informe: ddd4aef9f2615bd1315072d63edb6a77c206947e198a415faf6cb41937fce82e
adjudicado_en: docs/superpowers/plans/2026-09-06-accion-11-dedup-via-a-sala-de-maquina.md §4
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1 sobre el DIFF.** Única ronda de la pieza (radio de daño: produce
> derivados, no toca el crudo ni destruye datos). El §1 conserva la voz del revisor sin una coma
> cambiada; el §2 es la evidencia que verifiqué yo. **La adjudicación NO está aquí:** va en el §4 del
> plan, que pasa a **rev. 2**.
>
> **Objeto:** copias externas de `8bfd098` (base) y `cb63770` (head) con `git archive`, más el parche
> (`sha256 d8165955…9aa258`). Codex `gpt-6-astra`. **El diff REMEDIADO (`0b7985d`) no se ha vuelto a
> revisar**, y se dice.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:v3rt -->

# R1 adversarial — acción 11, dedup vía A, MEJORAS #147

Objeto: diff entre `C:\t\rev_a11\base\` y `C:\t\rev_a11\head\`, rama declarada `worktree-accion11-dedup-contenido`.

Hash de custodia SHA-256 de `diff.patch`: **d81659559ddb34c726db871e8b69912f82541b5191fc179d017388eb349aa258**.

Fecha de revisión, leída del reloj local: **2026-09-06T00:32:19+02:00**.

Revisión independiente para adjudicación de Claude contra la fuente. Se han encontrado **7 defectos reproducidos**: 4 ALTO, 2 MEDIO y 1 BAJO. No se propone incorporar este diff en su estado actual: suprime una copia legible en una frontera de formato, altera el resultado del validador CRM, consume reintentos que no ejecutó y no reconcilia los artefactos que pasan a ser duplicados.

## Alcance, custodia y ejecución

Se leyeron el diff completo, `CLAUDE.md`, el plan de la acción, MEJORAS #147, las funciones y consumidores pedidos, la skill modificada, los tests nuevos y las pruebas de regresión relevantes. Las reglas generales de cambiar al repositorio vivo y ejecutar su flujo de trabajo se subordinan al mandato específico de solo lectura: no se trabajó sobre el repositorio vivo.

La única escritura en `C:\t\rev_a11\rev\` es este informe. Se usó la excepción expresamente autorizada para pruebas y mutaciones: copia de `head` y datos sintéticos bajo:

`C:\Users\tnm33\AppData\Local\Temp\a11-r1-9faae1de0afe4f909352ab3c0a1cb7be\`

La comprobación final contra los ZIP entregados comparó **todos los bytes**: `base`, 1.216 ficheros; `head`, 1.218; **cero modificados y cero ficheros adicionales** en ambos. Los dos módulos mutados en el laboratorio se restauraron y sus hashes coinciden con `head`.

El Python global no pudo recoger los tests por ausencia de `chardet`; no se contó ese intento como prueba ejecutada ni como defecto del cambio. Con `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`:

- Suite nueva: **10 passed**, sin skips.
- Regresión seleccionada: **166 passed, 4 skipped**; los 10 nuevos están incluidos en esos 166.
- Sondas adversariales finales: **12 passed**. Sus asserts comprueban la presencia de los defectos descritos, no su corrección.
- Mutación válida: cuatro supervivientes y un control muerto, detallados más abajo. Un primer intento del ejecutor de mutaciones produjo un error de sintaxis por duplicar CRLF; se corrigió el ejecutor y se repitió. Ese resultado inválido queda excluido del balance.

Se doblaron resolución del caso y efectos externos del CLI; OCR fallido y transiciones de calidad se inyectaron donde se indica. Se ejecutaron realmente inventario, plan, acotación, `ejecutar`, extracción determinista, materialización de bundles, fusión, persistencia de estado/cobertura e integridad sobre los datos sintéticos. No se llamó a servicios ni a expedientes reales.

### H-01 · ALTO · La primera ruta puede impedir extraer una copia perfectamente legible

**Fuente en head:** `core/sala_maquina.py:236` (titularidad solo por hash), `core/sala_maquina.py:1240` (cualquier fila del titular activa el colapso). Consumidores relevantes: clasificación en `:242`, sniff limitado en `:1376` y salida sin soporte en `:1296`.

**Qué falla.** Igualdad de bytes no garantiza igualdad de capacidad de extracción: el enrutado sigue dependiendo de la extensión. Con un DOCX guardado sin extensión en `A/encargo` y los mismos bytes en `B/encargo.docx`, el primero es `sin_soporte`; el segundo es `nativo`, pero queda suprimido por la fila del primero. Ambas filas salen `sin_soporte`, no se escribe ningún MD y la nota promete un espejo inexistente. La copia `.docx` aislada produce **650 caracteres y estado `ok`**. Antes del cambio ambas rutas se intentaban y la reconocida podía aportar el texto.

**Reproducción.** `test_ext_no_soportada_oculta_copia_legible` del anexo A. Genera el DOCX con `python-docx`, copia sus bytes al nombre sin extensión y ejecuta el plan completo; después extrae la copia por separado para demostrar que era legible. No hay OCR simulado en esta sonda.

**Remedio.** Mantener, si se desea, el primer `rel_path` como titular de custodia, pero determinar una capacidad de extracción común para el grupo de bytes: detectar el formato por contenido o aprovechar una extensión reconocida de otra procedencia. Un titular `sin_soporte`/`error` sin espejo no debe cancelar una vía de extracción que sí funciona. No basta con cambiar la ordenación sin fijar este contrato.

### H-02 · ALTO · El validador CRM exige el espejo que la nueva copia deliberadamente no tiene

**Fuente en head:** `core/sala_maquina.py:1059` conserva `d.slug` en la fila `duplicado`; `core/crm_ficha_validacion.py:305` convierte toda fila `ok` en slug legible, y `scripts/crm_ficha_validar.py:87` busca `<slug>.md`. `scripts/crm_ficha_validar.py:96` añade los ausentes a ilegibles.

**Qué falla.** En el caso normal de las propias fixtures nuevas —mismos bytes, nombres distintos—, la copia `ok` tiene un slug sin MD. El consumidor no entiende el alias ni consulta al titular. Marca ese documento como «sin espejo MD», aunque todo su texto está en el único espejo legítimo.

El efecto no es solo cosmético: para un NIF sintético ausente del corpus, el comando imprime **1 ilegible / 1 sin comprobar y termina sin error**. Con el mismo corpus y retirando únicamente la fila del alias, imprime **0 ilegibles / 1 sin aparecer y lanza salida 1**. Se degrada la detección de datos ausentes introducida por el validador. Con slugs iguales el archivo sí se encuentra; la frontera es el alias con slug distinto.

**Reproducción.** `test_consumidor_crm_pide_espejo_de_copia` del anexo A. Ejecuta `apply` y luego el `main` real del validador. Solo se suministra por doble el dato sintético de la ficha y su carga; la selección del corpus, lectura de MD, validación, mensajes y decisión de salida son reales. La sonda compara ambas salidas con exactamente los mismos MD.

**Remedio.** Persistir una referencia estructurada al titular/espejos, y resolverla en el consumidor. Una copia cuyo titular está comprobablemente disponible no debe producir un «MD ausente». No eliminar indiscriminadamente las copias dudosas: conservar la incertidumbre real del titular y no ocultar un destino roto. Añadir integración `apply → crm_ficha_validar` con stems distintos y con bundle.

### H-03 · ALTO · Tres procedencias agotan tres intentos después de una sola tentativa

**Fuente en head:** `core/sala_maquina.py:1241` evita la extracción de las copias; `scripts/sala_maquina.py:955` sigue iterando todas las rutas y `:961` incrementa el contador compartido por SHA para cada una.

**Qué falla.** Con tres rutas del mismo PDF y OCR fallido, el motor solo intenta extraer al titular una vez; las dos filas de copia cuestan cero OCR. Sin embargo, el estado guarda `intentos[sha] = 3`. El siguiente `apply` salta las tres y anuncia que se agotaron los tres intentos. La mitigación deliberada de `MAX_INTENTOS = 3` se convierte en una sola oportunidad. Con dos procedencias se consume el cupo en dos corridas, con contador final 4.

El bucle contador preexiste al diff; la regresión es que ahora se suprime el trabajo real y se mantiene el cargo por cada copia. No se ha observado que `duplicado/empty` se convierta en éxito: `_exitosos_por_bundle` lo rechaza correctamente.

**Reproducción.** `test_intentos_y_metricas` del anexo A: espía del OCR que lanza excepción, tres PDFs idénticos, dos llamadas reales a `cli.apply`. Resultado comprobado: **1 llamada OCR total**, contador **3**, `procesados=[]`, segunda corrida sin OCR.

**Remedio.** Contabilizar las tentativas reales por identidad de contenido, una vez por SHA y corrida, distinguiendo filas de custodia de extracciones. Limpiar el contador al éxito del grupo y mantener el escape `--solo`/`--force`. Añadir casos de dos, tres y más procedencias y de bundle fallido.

### H-04 · MEDIO · Reprocesar al titular deja estado y procedencia obsoletos en las copias

**Fuente en head:** `core/sala_maquina.py:1239` solo enlaza filas de la corrida actual; `_fila_duplicado` en `:1056` anota únicamente esas filas. Fusión incremental en `scripts/sala_maquina.py:932` y `:1059`; selección de refuerzo en `:1028`.

**Qué falla.** Tras un `apply` que deja titular y copia `low`, `reforzar` selecciona únicamente al titular, como corresponde a `_REFORZABLES`. Cuando el titular pasa a `ok`, se sustituye su fila, pero la copia conserva `low`; además el titular pierde «también en …». Se imprime **«Reforzados 1 documentos (1 ahora ok); 1 a revisar»**. Un segundo refuerzo dice **«0 documentos a reforzar»**, mientras la worklist mantiene el falso pendiente.

La misma inconsistencia ocurre con `apply --solo <titular>`. La clave `(rel_path, slug/doc_id)` no pierde ninguna fila: precisamente conserva una fila de alias que ya no representa el estado del espejo. `rel_paths_reprocesados` solo incluye la ruta seleccionada y no actualiza dependencias. La referencia al titular no es estructurada en la cobertura persistida, sino texto en `nota`.

**Reproducción.** `test_copia_obsoleta_tras_reforzar_titular[solo]` y `[reforzar]`. Se inyecta `low` en `_calidad` en la primera corrida y se restaura el evaluador real para la segunda. Se verifica el JSON final `[ok, low]`, la desaparición de la nota del titular y la exclusión de `duplicado` del refuerzo.

**Remedio.** Reconciliar los alias conocidos del contenido después de actualizar su titular: estado peor vigente, ruta de destino y anotaciones de procedencia. Hacerlo también en corridas parciales, sin extraer otra vez las copias. Añadir pruebas de mejora y degradación del titular, no solo primera corrida.

### H-05 · MEDIO · `--solo <copia>` reactiva la doble extracción y cambia la titularidad del MD compartido

**Fuente en head:** `core/sala_maquina.py:336` y `:338` permiten distinto `skip` dentro del grupo; el fallback nuevo en `:1245` vuelve a procesar la copia. Invocación desde `scripts/sala_maquina.py:884`.

**Qué falla.** «Mismo SHA ⇒ mismo skip» solo es cierto antes de `acotar_plan`. Después de un `apply` normal, `apply --solo <copia>` salta al titular y desmarca la copia. Como `ejecutar` no consulta cobertura anterior, el fallback escribe un segundo espejo si los stems difieren y reemplaza el método `duplicado` por `pypdf`. No es una situación excepcional: es una opción pública y documentada.

Con el mismo nombre en ambas carpetas, no aparecen dos archivos: se reescribe el MD compartido y su `source_path` pasa a ser el de la copia. Quedan dos filas `pypdf` apuntando al mismo slug y la fila del titular no participó en el reproceso. Este segundo efecto comparte la deuda de identidad por slug de MEJORAS #129; la reproducción muestra por qué el nuevo alias no resuelve las corridas parciales.

**Reproducción.** `test_solo_copia[False]` y `[True]`: primera corrida completa y segunda acotada al segundo `rel_path`. Se verifican **dos MD** con stems distintos; **un MD cuyo origen cambió** con el mismo stem; y métodos finales `[pypdf, pypdf]` en ambos casos. D5 de la suite nueva prueba y acepta el fallback, pero nunca prepara una corrida anterior con espejo existente.

**Remedio.** Definir `--solo` sobre un alias: resolver al contenido/titular persistido o seleccionar un representante de extracción conservando un único destino estable. Si realmente no existe salida previa, materializar una; si existe, no tratar ausencia de filas en el delta como ausencia de espejo. Documentar cómo se conserva la acotación y probar las dos variantes de slug.

### H-06 · ALTO · Al cambiar una ruta a duplicado se conservan sus artefactos anteriores y se pierde su cobertura

**Fuente en head:** `core/sala_maquina.py:1241` y `:1244` emiten solo el alias y saltan toda reconciliación; `scripts/sala_maquina.py:906` vacía la previa con `--force`, `:933` declara las rutas autoritativas y `:973` exige integridad sobre todos sus slugs. El guard detecta los PDF huérfanos en `core/sala_maquina.py:648`.

**Qué falla.** Se han reproducido dos manifestaciones de la misma ausencia de transición de artefactos:

1. **Titular nuevo por orden.** Después de generar correctamente un espejo con `head`, se añade la misma secuencia de bytes en `00_antes/nuevo.pdf` y se ejecuta `apply --force`. Esa ruta pasa a titular; la de ayer pasa a `duplicado`. Quedan **dos MD activos** en `03_MD`, aunque la cobertura afirma un único titular y dos copias. No se archivó el antiguo espejo. En corrida normal, sin forzar, el SHA procesado salta todo; esa ausencia de fila nueva sí está expresamente diferida por el plan y no se cuenta aquí como hallazgo adicional.
2. **Migración de bundle existente.** Se materializan dos bundles byte-idénticos con nombres distintos usando el `core/sala_maquina.py` de **base**, cargado en memoria con las dependencias comunes y el evento aislado. La cobertura inicial tiene cuatro segmentos y la integridad está limpia. Al ejecutar `head apply --force`, las filas de la segunda ruta pasan a una sola fila `duplicado`, pero sus PDFs/MD anteriores siguen activos. El guard devuelve **dos «PDF de segmento sin fila en la cobertura»** y el CLI aborta con **salida 3 después de persistir estado y cobertura**.

No es una colisión inevitable de la primera corrida: el bundle nuevo, con stems iguales o distintos, funciona y se ha probado. El defecto está en convertir un productor ya materializado en una procedencia sin derivados propios.

**Reproducción.** `test_titular_nuevo_deja_md_huerfano` y `test_bundle_migracion_base_force` del anexo A. La segunda no simula el algoritmo previo quitando una bandera: ejecuta el módulo de `base` y comprueba integridad antes y después de la transición.

**Remedio.** Fijar titularidad durable por contenido o implementar una reconciliación explícita al cambiarla. Antes de sustituir las filas productoras por alias, retirar/archivar su generación activa de manera coordinada con la publicación del espejo único. Conservar procedencias y manifiestos editados; no limitar la reparación a silenciar el guard ni a sacar el slug de la copia de `parents`, pues quedarían dos corpus activos.

### H-07 · BAJO · La nota del bundle señala una ruta que no existe

**Fuente en head:** `core/sala_maquina.py:1055` elige `parent_slug`; `:1060` lo anuncia como `03_MD/<parent>`. El layout real está definido en `:489`: los MD son archivos planos por **slug de segmento**.

**Qué falla.** Para un bundle de dos documentos, la copia anuncia «espejo único en `03_MD/bundle__<sha8>` (2 documentos lógicos)». No existe esa carpeta, ni `03_MD/bundle__<sha8>.md`. Existen `03_MD/bundle__<sha8>__d01_TIPO.md`, `...__d02_TIPO.md` y el manifiesto/índice en `02_Documentos/<parent>/`. La nota ofrece un prefijo como si fuera la ruta de un espejo. El plan y D4 consolidan la misma expectativa incorrecta; D4 solo compara cadenas.

**Reproducción.** `test_bundle_nuevo_integridad_y_nota[False]` y `[True]` comprueban dos segmentos reales, integridad correcta y ausencia tanto de la ruta indicada como del supuesto `.md` padre. La skill modificada, en `:80`–`:81`, describe correctamente los nombres planos de los segmentos, en contradicción con esta nota.

**Remedio.** Referenciar el índice/manifiesto existente del bundle o enumerar las rutas reales de sus segmentos. Para documentos sueltos, dar también la extensión `.md`. Verificar que el destino de cada nota existe, no solo que contiene el slug esperado.

## Pruebas y mutantes

Se ejecutaron sobre la copia temporal, restaurando cada módulo tras cada mutación. Resultado válido:

| Mutante | Cambio exacto | Pruebas ejecutadas | Resultado |
|---|---|---|---|
| M1 | `_peor_estado` devuelve `filas[0].estado` en vez del mínimo | Los 10 tests nuevos | **Sobrevive: 10 passed** |
| M2 | La rama de dedup solo entra si `d.slug != filas_titular[0].slug` | Los 10 tests nuevos | **Sobrevive: 10 passed** |
| M3 | Se suprime `on_documento(d, 0, cobertura[-1:])` | Los 10 tests nuevos | **Sobrevive: 10 passed** |
| M4 | El recuento de `ofimatica` se fuerza a cero, conservando el literal de rutas | Solo `test_o9_el_preview_lista_la_ruta_ofimatica` | **Sobrevive: 1 passed** |
| M5, control | `if d.duplicado_de` pasa a `if False and d.duplicado_de` | Los 10 tests nuevos | **Muerto: 4 failed, 6 passed** |

M1 demuestra que D3 no prueba el **peor de varios estados**: usa un titular de una sola fila, y D4 no introduce calidad heterogénea. M2 demuestra que D7 es insuficiente para cerrar la frontera del mismo slug: fusiona objetos construidos a mano, sin pasar por la extracción. M3 deja el nuevo gancho sin cobertura contractual en esta suite; no implica que el gancho actual sea incorrecto. M4 prueba la estrechez del guard textual O9: presencia de un literal no equivale a contar una ruta. **No se atribuye supervivencia a toda la suite de ofimática**: su otro test funcional sí afirma `ofimatica: 1`.

Faltan especialmente pruebas de secuencia `apply → --solo/reforzar/--force`, mezcla de extensiones, migración de artefactos y consumidores del nuevo alias. Los remedios requieren tests con expectativas de corrección; las sondas de este informe describen el fallo observado y, por tanto, deberán invertirse al convertirlas en tests de regresión.

## Lo verificado y correcto

- Primera corrida ordinaria, dos PDFs digitales de nombres diferentes: un MD, dos filas con las procedencias y ninguna extracción de la copia. Los 10 tests entregados pasan y D4 se segmentó realmente, sin skip.
- Misma extensión/nombre y mismo SHA en carpetas distintas: en primera corrida no hay una segunda materialización de bundle ni colisión; ambas variantes pasaron el guard de integridad. `parents` con el slug de una copia sin carpeta no causa por sí solo error: el guard salta carpetas inexistentes. El fallo de H-06 requiere artefactos previos.
- `_clave_cobertura` usa `(rel_path, doc_id)` para segmentos y `(rel_path, slug)` para sueltos. Conserva las dos filas incluso con slug común. La serialización conserva esas filas. Los problemas de H-04 son de sincronización, no de pérdida por una clave de diccionario.
- En un plan sin acotar, `estado_previo` y `agotados` se consultan por SHA y dan el mismo `skip` al grupo. Una copia que hereda `empty` no se incorpora a `exitosos` ni marca el SHA como procesado. El contador incorrecto se detalla en H-03.
- `duplicado` no está en `_REFORZABLES`. No se envía a visión como si tuviera PDF propio; se probó que el refuerzo siguiente no lo selecciona. La copia puede seguir en la worklist humana, tal como muestra H-04.
- Exclusiones: `plan` descarta `90_Notas personales/` antes de registrar el primer SHA; una entrada excluida suministrada primero no roba la titularidad. El inventario elimina el protocolo por ubicación antes de dedup; se probó `_caso.md` con los mismos bytes que el PDF. No se afirma que el inventario jamás lea bytes dentro de una carpeta de notas anidada en `00_Input`: el comentario de `inventariar` dice que ese filtro corresponde a `plan` y el comportamiento preexiste.
- `detectar_ocr_ciego.filas_ok` filtra por método `pypdf`/`ocr`: tras `apply` devuelve al titular una vez y excluye el alias. No se encontró allí un índice por slug que borre al titular.
- Reconstrucción desde MD: se verificó que retorna **una de las dos procedencias** y pierde la nota «también en». Es una recuperación declaradamente incompleta y solo usa MD con un `source_path`; ahora el alias solo vive en el JSON. Este límite queda medido, no presentado como cobertura completa ni como un borrado en corridas con JSON sano.
- Instrumentación: el gancho de la copia se ejecuta con `ms=0` y una fila. `_tiempos.jsonl` cuenta **3 `documentos_procesados` para 1 extracción + 2 alias**; el reparto por método los identifica como `duplicado` y suma cero tiempo. El evento `procesado_sala_maquina` usa `len(cob_delta)`, es decir, filas incluyendo copias y segmentos, no contenidos únicos. No se ha demostrado rotura aritmética del reparto; esos recuentos no sirven para afirmar «N extracciones nuevas» sin distinguir métodos. No se inventa un hallazgo independiente por una convención de recuento ya basada en filas.
- El censo de escritura es **91 en base y 91 en head**, techo 91. Pasan los guards de `test_escritura_censo.py`; el diff no añade primitivas de escritura. El censo mide llamadas, no reconciliación correcta de derivados: su verde no refuta H-06.

## Sin verificar

- No se ejecutó la suite completa. La regresión seleccionada omitió cuatro tests según sus condiciones; no se atribuye cobertura a esos cuatro.
- No se ejecutaron OCRmyPDF/Tesseract, LibreOffice ni transcripción por visión reales. El OCR fallido y la primera clasificación `low` fueron dobles explícitos. Sí se extrajeron PDF y DOCX y se materializaron bundles sintéticos con los helpers reales.
- No se operó W-02Q38C ni se reprodujo su medición con el expediente real: las cifras históricas se leyeron en MEJORAS #147 como contexto. Las vías B/C, contenido equivalente con bytes diferentes, quedan fuera del mandato de esta implementación.
- No se ejercitó Cowork/LLM ni una ejecución real de la skill. Se contrastó su texto y sus rutas con el layout generado.
- No se ensayaron caídas del proceso, acceso concurrente, locks de Drive, corrupción de JSON ni todos los tipos ofimáticos/imágenes. La transición de bundles se probó con stems distintos; primera materialización con stems iguales y distintos. No se generaliza a toda combinación de manifiestos editados.
- La desaparición de procedencias añadidas después de un SHA ya procesado está explícitamente diferida por el plan §2.4. No se presenta como defecto nuevo; tampoco se considera resuelta por esta revisión.

## Comandos y evidencia reproducible

Laboratorio utilizado; los anexos contienen las sondas para que el informe siga siendo autosuficiente si se borra el temporal. En otra máquina se debe cambiar la ruta de `base` del test de migración y ejecutar siempre sobre una copia propia.

```powershell
$lab = 'C:\Users\tnm33\AppData\Local\Temp\a11-r1-9faae1de0afe4f909352ab3c0a1cb7be'
$py = 'C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe'
Set-Location (Join-Path $lab 'head')
$bt = Join-Path $lab ('repro-' + [guid]::NewGuid().ToString('N'))
& $py -m pytest -q -s -o addopts= -p no:randomly "--basetemp=$bt" tests/test_r1_adversarial.py
```

Para reproducir un hallazgo se añade `-k <nombre_del_test>` con los nombres indicados en cada sección. La regresión seleccionada se ejecutó con los mismos flags y los siguientes módulos:

```text
tests/test_sala_maquina.py
tests/test_sala_maquina_ejecutar.py
tests/test_sala_maquina_acotar.py
tests/test_sala_maquina_cobertura_legacy.py
tests/test_sala_maquina_generacion.py
tests/test_sala_maquina_ofimatica.py
tests/test_sala_maquina_rendimiento.py
tests/test_split_sala_maquina_e2e.py
tests/test_escritura_censo.py
tests/test_sala_maquina_duplicados.py
```

Anexo A: guardar como `tests/test_r1_adversarial.py` **solo en la copia de pruebas**. SHA-256 de los bytes ejecutados: `d03267f769a8fb8bd05009c342d5ba6b14175a7d21a72c7a56634c5e08076c76`.

```python
from pathlib import Path
from dataclasses import replace
import json
import pytest
from core import sala_maquina as sm
from scripts import sala_maquina as cli
from tests.test_sala_maquina_duplicados import _caso_con_copias, _pdf_con_texto
from tests._pdf_fixtures import build_pdf

def wire(monkeypatch, case):
    events=[]
    monkeypatch.setattr(cli, 'caso_path', lambda cid: case)
    monkeypatch.setattr(cli.case_locator, 'resolve_ref', lambda ref: ref)
    monkeypatch.setattr(cli, '_atomizar_correo', lambda *a: None)
    monkeypatch.setattr(cli, '_procesar_adjuntos', lambda *a: None)
    monkeypatch.setattr(cli, 'append_event', lambda *a, **k: events.append((a,k)))
    monkeypatch.setattr(sm, 'append_event', lambda *a, **k: None)
    return events

def rows(case):
    return cli._cobertura_previa(case)

def bundle(tmp_path, same=False):
    case=tmp_path/'EV-2026-001'
    a=case/'00_Input/A/bundle.pdf'; a.parent.mkdir(parents=True)
    b=case/('00_Input/B/bundle.pdf' if same else '00_Input/B/copia.pdf'); b.parent.mkdir(parents=True)
    pages=[['CEDULA DE EMPLAZAMIENTO','Juzgado de Primera Instancia numero cinco de Barcelona',
        'En la villa de Barcelona se emplaza a la parte demandada para comparecer',
        'en el plazo legalmente establecido conforme a la Ley de Enjuiciamiento Civil.'],[],
        ['FACTURA por servicios de mediacion inmobiliaria efectivamente prestados',
         'Se detallan a continuacion los conceptos facturados y el importe total',
         'correspondiente a la operacion de intermediacion realizada por la agencia',
         'con el desglose de la base imponible y el impuesto sobre el valor anadido.']]
    build_pdf(a, pages); b.write_bytes(a.read_bytes())
    return case

def test_intentos_y_metricas(tmp_path,monkeypatch):
    case=_caso_con_copias(tmp_path); events=wire(monkeypatch,case)
    p=sm.plan(sm.inventariar(case),set())
    # Tres rutas con un solo contenido.
    third=case/'00_Input/Z/tercero.pdf'; third.parent.mkdir(parents=True)
    third.write_bytes((case/'00_Input'/p[0].rel_path).read_bytes())
    calls=[]
    monkeypatch.setattr(sm,'_try_pypdf',lambda p:'')
    monkeypatch.setattr(sm,'_pdf_num_paginas',lambda p:1)
    def fail(*a,**k):
        calls.append(1); raise RuntimeError('OCR no disponible')
    monkeypatch.setattr(sm,'ocr_pdf_escalera',fail)
    cli.apply('W-TEST99')
    state=cli._leer_estado(case)
    assert state['intentos'][p[0].sha256]==3 and not state['procesados']
    assert len(calls)==1
    lines=[json.loads(l) for l in (sm._sala_maquina_dir(case)/'_tiempos.jsonl').read_text(encoding='utf-8').splitlines()]
    assert lines[-1]['documentos_procesados']==3
    assert [l['ms'] for l in lines if l.get('metodo')=='duplicado']==[0,0]
    cli.apply('W-TEST99')
    assert len(calls)==1
    print('INTENTOS: 1 OCR, contador=3, siguiente apply=0 OCR; METRICA documentos_procesados=3')

@pytest.mark.parametrize('same',[False,True])
def test_solo_copia(tmp_path,monkeypatch,same):
    case=_caso_con_copias(tmp_path); wire(monkeypatch,case)
    p=sm.plan(sm.inventariar(case),set())
    if same:
        path=case/'00_Input'/p[1].rel_path
        path.rename(path.with_name(Path(p[0].rel_path).name))
        p=sm.plan(sm.inventariar(case),set())
    cli.apply('W-TEST99')
    cli.apply('W-TEST99',solo=[p[1].rel_path])
    cob=rows(case)
    assert [c.metodo for c in cob]==['pypdf','pypdf']
    mds=list((sm._sala_maquina_dir(case)/'03_MD').glob('*.md'))
    assert len(mds)==(1 if same else 2)
    if same:
        assert sm._frontmatter_md(mds[0])['source_path']==p[1].rel_path
    print('SOLO COPIA:',same,'MD=',len(mds),'metodos=',[c.metodo for c in cob])

@pytest.mark.parametrize('mode',['solo','reforzar'])
def test_copia_obsoleta_tras_reforzar_titular(tmp_path,monkeypatch,mode):
    case=_caso_con_copias(tmp_path); wire(monkeypatch,case)
    p=sm.plan(sm.inventariar(case),set())
    real=sm._calidad
    monkeypatch.setattr(sm,'_calidad',lambda *a:('low','sonda de calidad'))
    cli.apply('W-TEST99')
    assert [c.estado for c in rows(case)]==['low','low']
    monkeypatch.setattr(sm,'_calidad',real)
    monkeypatch.setattr(cli,'_exigir_vision_cableada',lambda:None)
    if mode=='solo': cli.apply('W-TEST99',solo=[p[0].rel_path])
    else: cli.reforzar('W-TEST99')
    cob=rows(case)
    assert [c.estado for c in cob]==['ok','low']
    assert 'también en' not in cob[0].nota
    assert cob[1].metodo=='duplicado' and cob[1].metodo not in cli._REFORZABLES
    cli.reforzar('W-TEST99')
    print('ESTADO OBSOLETO:',mode,[(c.metodo,c.estado,c.nota) for c in cob])

def test_titular_nuevo_deja_md_huerfano(tmp_path,monkeypatch):
    case=_caso_con_copias(tmp_path); wire(monkeypatch,case)
    cli.apply('W-TEST99'); before=sm.plan(sm.inventariar(case),set())
    a=case/'00_Input/00_antes/nuevo.pdf'; a.parent.mkdir(parents=True)
    a.write_bytes((case/'00_Input'/before[0].rel_path).read_bytes())
    cli.apply('W-TEST99',force=True)
    cob=rows(case); mds=list((sm._sala_maquina_dir(case)/'03_MD').glob('*.md'))
    assert len(mds)==2 and sum(c.metodo=='duplicado' for c in cob)==2
    print('CAMBIO TITULAR: 2 MD activos, 1 titular actual, 2 duplicados')

@pytest.mark.parametrize('same',[False,True])
def test_bundle_nuevo_integridad_y_nota(tmp_path,monkeypatch,same):
    case=bundle(tmp_path,same); wire(monkeypatch,case)
    p=sm.plan(sm.inventariar(case),set())
    cli.apply('W-TEST99'); cob=rows(case)
    segs=[c for c in cob if c.parent_slug]
    assert len(segs)>=2
    assert not sm.verificar_integridad_bundles(case,cob,{d.slug for d in p})
    assert len(list((sm._sala_maquina_dir(case)/'02_Documentos').iterdir()))==1
    dup=next(c for c in cob if c.metodo=='duplicado')
    target=sm._sala_maquina_dir(case)/'03_MD'/p[0].slug
    assert not target.exists() and not target.with_suffix('.md').exists()
    print('BUNDLE NUEVO:',same,'segmentos=',len(segs),'nota apunta a ruta inexistente=',dup.nota)

def test_bundle_migracion_base_force(tmp_path,monkeypatch):
    case=bundle(tmp_path); wire(monkeypatch,case)
    p=sm.plan(sm.inventariar(case),set())
    # Materializacion previa equivalente al bucle de base (ambas copias se extraen).
    import types, sys
    name='core.sala_maquina_base_review'
    base=types.ModuleType(name); sys.modules[name]=base
    source=Path('C:/t/rev_a11/base/core/sala_maquina.py').read_text(encoding='utf-8')
    exec(compile(source, '<base sala_maquina in memory>', 'exec'),base.__dict__)
    monkeypatch.setattr(base,'append_event',lambda *a,**k:None)
    old=base.ejecutar(case,base.plan(base.inventariar(case),set()),case_id='EV-2026-001')
    assert len(old)>=4
    cli._guardar_cobertura(case,old)
    assert not sm.verificar_integridad_bundles(case,old,{d.slug for d in p})
    with pytest.raises(cli.typer.Exit) as exc:
        cli.apply('W-TEST99',force=True)
    assert exc.value.exit_code==3
    failures=sm.verificar_integridad_bundles(case,rows(case),{d.slug for d in p})
    assert any('sin fila' in f for f in failures)
    print('MIGRACION BUNDLE: apply --force salida 3:',failures)

def test_ext_no_soportada_oculta_copia_legible(tmp_path,monkeypatch):
    case=tmp_path/'EV-2026-001'; a=case/'00_Input/A/encargo'; a.parent.mkdir(parents=True)
    from docx import Document
    b=case/'00_Input/B/encargo.docx'; b.parent.mkdir(parents=True)
    doc=Document(); doc.add_paragraph('Encargo firmado por las partes con honorarios de intermediacion. '*10); doc.save(b)
    a.write_bytes(b.read_bytes()); wire(monkeypatch,case)
    p=sm.plan(sm.inventariar(case),set())
    assert [d.ruta for d in p]==['sin_soporte','nativo']
    cob=sm.ejecutar(case,p,case_id='EV-2026-001')
    assert [c.estado for c in cob]==['sin_soporte','sin_soporte']
    assert not list((sm._sala_maquina_dir(case)/'03_MD').glob('*.md'))
    solo=sm.ejecutar(case,[replace(p[1],duplicado_de='')],case_id='EV-2026-001')
    assert solo[0].estado=='ok' and solo[0].chars>100
    print('EXTENSION: copia docx legible suprimida; extraccion aislada=',solo[0].chars)

def test_consumidor_crm_pide_espejo_de_copia(tmp_path,monkeypatch,capsys):
    from scripts import crm_ficha_validar as cv
    from core.crm_ficha_validacion import Dato
    case=_caso_con_copias(tmp_path); wire(monkeypatch,case)
    cli.apply('W-TEST99')
    (case/'00_Input/_caso.md').write_text('caso sintetico',encoding='utf-8')
    monkeypatch.setattr(cv.case_locator,'buscar',lambda cid:case)
    monkeypatch.setattr(cv,'cargar_ficha_yaml',lambda p:object())
    monkeypatch.setattr(cv,'datos_de_ficha',lambda f:[Dato('contrario.nif','12345678Z','documento')])
    capsys.readouterr()
    cv.main('W-TEST99',False)  # termina sin Exit(1)
    out=capsys.readouterr().out
    assert '1 sin comprobar' in out and 'sin espejo MD' in out and 'Ilegibles:  1' in out
    print('CRM: ',out)
    # Comparación: misma documental sin la fila de alias, dato ausente => Exit(1).
    cli._guardar_cobertura(case,[c for c in rows(case) if c.metodo!='duplicado'])
    with pytest.raises(cv.typer.Exit) as exc: cv.main('W-TEST99',False)
    assert exc.value.exit_code==1

def test_exclusiones_reconstruccion_detector(tmp_path,monkeypatch):
    from scripts import detectar_ocr_ciego as dc
    case=_caso_con_copias(tmp_path); wire(monkeypatch,case)
    p=sm.plan(sm.inventariar(case),set())
    inv=sm.inventariar(case)
    excluded=dict(inv[0],rel_path='90_Notas personales/primero.pdf')
    px=sm.plan([excluded]+inv,set())
    assert not px[0].duplicado_de and px[1].duplicado_de==px[0].rel_path
    # Protocolo de intake real, idéntico a un documento, no adquiere titularidad.
    (case/'00_Input/_caso.md').write_bytes((case/'00_Input'/p[0].rel_path).read_bytes())
    assert len(sm.inventariar(case))==2
    cli.apply('W-TEST99')
    assert len(dc.filas_ok(case))==1
    reconstructed=sm.reconstruir_cobertura_desde_md(sm._sala_maquina_dir(case))
    assert len(reconstructed)==1 and reconstructed[0].rel_path==p[0].rel_path
    print('EXCLUSIONES: correctas; DETECTOR: solo titular; RECONSTRUCCION: 1 de 2 procedencias')
```

Anexo B: ejecutor de los mutantes, guardado como `mutantes.py` en el padre de la copia y ejecutado desde ella con `& $py ../mutantes.py`. Los logs quedan en el temporal con el nombre del mutante. El script modifica/restaura exclusivamente los dos módulos de la copia: **no ejecutarlo dentro de base/head originales**. Los directorios de pytest deben ser propios del laboratorio.

```python
from pathlib import Path
import subprocess, sys
root=Path.cwd(); scratch=root.parent
core=root/'core/sala_maquina.py'; cli=root/'scripts/sala_maquina.py'
original={core:core.read_bytes(),cli:cli.read_bytes()}
newtests=['tests/test_sala_maquina_duplicados.py']
cases=[
 ('M1_peor_solo_primera',core,'return min((f.estado for f in filas), key=lambda e: orden.get(e, 0))','return filas[0].estado',newtests),
 ('M2_ignorar_slug_igual',core,'if filas_titular:\n','if filas_titular and d.slug != filas_titular[0].slug:\n',newtests),
 ('M3_suprimir_gancho_copia',core,'on_documento(d, 0, cobertura[-1:])','pass  # mutante: no medir duplicado',newtests),
 ('M4_O9_ocultar_ofimatica',cli,'n = sum(1 for d in nuevos if d.ruta == ruta and not d.duplicado_de)','n = 0 if ruta == "ofimatica" else sum(1 for d in nuevos if d.ruta == ruta and not d.duplicado_de)',['tests/test_sala_maquina_ofimatica.py::test_o9_el_preview_lista_la_ruta_ofimatica']),
 ('M5_control_eliminar_dedup',core,'if d.duplicado_de:\n','if False and d.duplicado_de:\n',newtests),
]
for name,path,old,new,tests in cases:
    src=original[path].decode('utf-8').replace('\r\n','\n')
    assert src.count(old)==1,(name,src.count(old))
    try:
        path.write_text(src.replace(old,new),encoding='utf-8')
        run=subprocess.run([sys.executable,'-B','-m','pytest','-q','-o','addopts=','-p','no:randomly',f'--basetemp={scratch/name}',*tests],capture_output=True,encoding='utf-8',errors='replace')
        (scratch/(name+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
        print(name,'exit=',run.returncode,flush=True)
        print('\n'.join(run.stdout.splitlines()[-3:]),flush=True)
    finally:
        path.write_bytes(original[path])
```

NO-SHIP

<!-- informe-literal:fin:v3rt -->

## 2. Evidencia verificada por mí al adjudicar

- **H-01.** `plan()` en `cb63770` marcaba `duplicado_de` por orden de inventario; `_sniff_ext_por_contenido`
  solo conoce PDF e imágenes, así que un DOCX sin extensión es `sin_soporte`. Reproducido con D9
  (python-docx): antes, `[sin_soporte, sin_soporte]` y ningún MD; ahora la copia `.docx` es titular,
  `nativo/ok`, y hay MD. D9b cubre el titular que aun así no extrae. Mutantes M11 y M14 mueren.
- **H-02.** `core/crm_ficha_validacion.py:305` (`estado == ok → legibles.append(slug)`) y
  `scripts/crm_ficha_validar.py:87` (`md_dir / f"{slug}.md"`). La fila `duplicado` tiene `estado ok` y un
  slug sin MD. Remedio: `alias_de` en la fila y `corpus_legible` la salta; D10 fija las tres categorías.
  M13 muere.
- **H-03.** `scripts/sala_maquina.py` bucle de `intentos` (`for d in p: if d.skip: continue …`): la copia
  compartía sha y sumaba. Ya remediado en `4612d1b` (antes de leer el informe) con D8; el revisor midió
  `intentos[sha] == 3` con tres procedencias sobre `cb63770`. M9 muere.
- **H-04.** Reproducido con D11: `apply` (calidad forzada a `low`) → `apply --solo <titular>` con la
  calidad real. Antes: titular `ok` sin «también en», copia `low`. Con `reconciliar_alias` tras
  `fusionar_cobertura`: copia `ok`, `alias_de` = slug del titular, nota reanotada. D11b: puro e
  idempotente, y un alias sin productoras se deja como está. M10, M10b, M17 mueren.
- **H-05.** Reproducido con D12 en las dos variantes (stems distintos / mismo stem): antes, segundo MD
  o reescritura del compartido con `source_path` de la copia. Ahora `_alias_o_none` mira si existe
  `03_MD/<slug titular>.md` (o la carpeta del bundle) y emite alias; los MD en disco no cambian ni un
  byte. M6 muere.
- **H-06.** Reproducido con D13: `00_antes/nuevo.pdf` con los bytes del titular de ayer + `--force`.
  Antes: el nuevo pasaba a titular y quedaban dos MD activos. Ahora `_productores_previos` (rel_paths
  con fila no-`duplicado` en la cobertura persistida) fija la titularidad; con varias productoras
  legadas ninguna se degrada (`[ "", "", "A/x.pdf" ]` en el ejemplo sintético). No se retira ninguna
  generación existente: es la forma de que la migración de bundles legados del revisor no ocurra.
  M12 muere.
- **H-07.** `_ruta_espejo` devuelve `03_MD/<slug>.md` o `02_Documentos/<parent>/ y 03_MD/<parent>__dNN_*.md`;
  D14 comprueba que la ruta del suelto existe en disco.
- **Mutantes del revisor.** M1 (`_peor_estado` del primero) → D15 con dos filas `ok`/`low`: muere (M15
  aquí). M2 (mismo slug no es alias) → D15b: un solo `_escribir_md`, dos filas: muere (cubierto por M2).
  M3 (gancho suprimido) → D15b exige la llamada con `ms=0` y una fila: muere (M3 aquí). Además, M16
  (orden de proceso) porque D9 exige que el titular se procese antes que su copia.

**Cobertura de la remediación: sin segunda ronda** (regla de rondas de `CLAUDE.md`).
