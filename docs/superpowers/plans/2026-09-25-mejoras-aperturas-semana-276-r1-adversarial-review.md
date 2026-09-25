---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md
objeto_rev: "1"
commit: d0d1427
ronda: "1"
revisor: Codex
veredicto: SHIP
marcador_nonce: vi6h
sha256_informe: 8dc25180f52bec6576830e06e3ea92505089e7f2fdb6ae470b11281c04b51c06
adjudicado_en: docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md §7
---

# Acta — R1 adversarial sobre el DIFF de `MEJORAS #276` (publicar `_viabilidad.json` sin hard links)

Objeto: el **diff** `7c70b70..d0d1427` —2 ficheros, +128—: la vía de repuesto de
`viabilidad_json.escribir` cuando el sistema de ficheros no admite hard links. En la sesión se
llamó «R2» porque corrió en paralelo a la del bloque 1; es la **única** ronda de esta pieza.

**Una ronda, y la fila de modelo es `gpt-6-astra` · `high`, no la ordinaria.** La frontera que lo
justifica, nombrada y no por importancia: la vía nueva decide si una publicación puede **pisar lo
que remató una sesión humana**, y esa garantía es de exclusión entre dos escritores —la corrida y
la sesión—, que es la fila de «concurrencia … o garantías entre varios sistemas». Por eso **no**
cuenta para la calibración de la fila #38.

| | |
|---|---|
| Revisor | Codex CLI `0.155.0-alpha.16.3` (binario `80f78947ad880e6e`), `gpt-6-astra` · `high` — **releídos** del `turn_context` de `rollout-2026-09-25T16-04-44-01a0d8e1-….jsonl` (`originator: codex_exec`); velocidad `default` **afirmada** desde el lanzador |
| Objeto | dos copias `git archive` fuera del repo, sin `.git` (`base/` y `head/`, 1.405 ficheros cada una) |
| `sha256` del objeto | **idéntico al abrir y al cerrar** (bytes sin normalizar, comparados por el revisor) |
| `sha256` del informe | `8dc25180f52bec6576830e06e3ea92505089e7f2fdb6ae470b11281c04b51c06` |
| Veredicto | **SHIP** |
| Hallazgos | 0 `H-NN`; dos huecos de cobertura (mutantes supervivientes) y dos frases del docstring, señalados como no defectos |
| Tokens | 98.038 |

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:vi6h -->
Higiene inicial: solo estaban `MANDATO.md`, `base/`, `head/` y `_stdout.log`; no había elementos ajenos que excluir.

# R2 adversarial — MEJORAS #276

Objeto: base `7c70b70ea4c8efe764f1367121a6b2635846cdde` → head `d0d1427dd0181a1a69de70e2ac812489ca6f4106`, según la atribución de los archives entregados. La comparación de todos los ficheros confirma únicamente los dos cambios declarados: `core/viabilidad_json.py` (+38) y `tests/test_viabilidad_json.py` (+90), sin bajas. Se comparó el texto normalizado a LF. Sin `.git`, no se autentica independientemente la correspondencia archive/commit.

**Resultado: no encuentro un defecto de corrección del diff que impida integrarlo.** La vía nueva conserva la exclusión y publica un temporal completo bajo las semánticas de Windows examinadas. No emito hallazgos H-NN. Los límites de las pruebas, los comentarios que han quedado desactualizados y la promesa heredada sobre cortes de luz se explican expresamente abajo.

## 1. La exclusión

**No encontré un camino de sobrescritura en la vía nueva.** En `head/core/viabilidad_json.py:307-309`, `exists()` solo ahorra trabajo. La protección decisiva está en `353-358`: el destino se vuelve a resolver en el acto de `os.rename`, que rechaza la colisión aunque haya aparecido después de la comprobación inicial o después del fallo de `os.link`.

En CPython para Windows, `os.rename` usa `MoveFileExW` sin `MOVEFILE_REPLACE_EXISTING` (flags 0); `os.replace` selecciona precisamente esa bandera. No hay una comprobación Python seguida de una apertura destructiva del destino. La operación sin reemplazo rechaza el nombre ocupado. Además, el temporal se crea en el mismo directorio (`317-319`): esta vía no solicita `MOVEFILE_COPY_ALLOWED` ni introduce una copia por bloques al nombre definitivo. Esta explicación de la implementación no equivale a haber inspeccionado aquí el fuente C de la distribución de Python; se declara ese límite al final.

Ataques ejecutados en `sondas_r2.py::test_destino_ajeno_intacto`: fichero, directorio con un marcador dentro, fichero con nombre en mayúsculas y directorio con nombre en mayúsculas; cada uno existente antes de llamar, creado dentro del enlace fallido o creado justo al entrar al renombrado. **Las 12 combinaciones dieron `FileExistsError`, conservaron los bytes ajenos y no dejaron temporales.** Las sondas comprueban primero que la variante en mayúsculas realmente colisiona en este directorio. El rechazo de un directorio tampoco lo sustituye por un fichero.

En `test_veinte_publicadores_un_ganador`, una barrera deja a 20 escritores después de escribir sus temporales y antes de publicar. Hubo exactamente un ganador, 19 rechazos y un JSON completo correspondiente al ganador, sin temporales.

La condición `os.name == "nt"` basta para seleccionar la implementación Windows en los intérpretes ordinarios del ámbito. Python POSIX, incluido Python Linux en WSL, no toma esa rama por estar accediendo a un volumen Windows. No es una certificación de todos los controladores de filesystem posibles ni protege frente a un programa que sustituya deliberadamente `os.name` u `os.rename`. Ninguna conclusión de esta revisión exige que las mediciones aportadas de Drive sean falsas; son coherentes con lo observado localmente.

## 2. Nunca a medias

**La vía nueva no escribe el destino por partes.** La serialización ocurre antes del temporal; `Path.write_text` termina y cierra su fichero antes de intentar el enlace o el renombrado (`311-322`, `340-356`). Un fallo durante esa escritura no alcanza la publicación. El renombrado publica el mismo fichero ya completo.

`test_publicacion_completa_y_temporal_cerrado`, para códigos 1 y 50, inspecciona el temporal inmediatamente antes del renombrado real: contenido completo, directorio correcto y destino ausente. Después compara todo el JSON, no solo `ref`. Los tests originales incluyen el fallo de escritura después de dejar algunos bytes en el temporal.

`test_muerte_sin_finally` hace terminar un subproceso con `os._exit(73)` justo antes y justo después del renombrado real. Antes: destino ausente y temporal completo huérfano. Después: solo destino completo. Esto comprueba esos dos puntos de interrupción, **no** un apagón físico ni el interior de la operación del controlador de Drive.

La atomicidad de publicación no acredita durabilidad frente a pérdida de alimentación. El código no hace `fsync` del contenido ni establece una barrera de persistencia del renombrado. La promesa heredada del docstring sobre «corte de luz» no queda acreditada por el cambio ni por estas pruebas; véase §7.

## 3. La clasificación

En `head/core/viabilidad_json.py:247-261`, los códigos 1 y 50 son una selección operativa de errores, no un diagnóstico inequívoco de su causa. Ambos pueden expresar otras situaciones de operación inválida/no soportada. **Un falso positivo de ese diagnóstico no abre una vía destructiva:** el remedio sigue siendo un renombrado sin reemplazo de un temporal completo. Si renombrar tampoco está permitido o soportado, el error se propaga. Si funciona, se cumple el objetivo de publicación segura aunque la explicación inicial del fallo del enlace fuera demasiado estrecha.

Los errores ordinarios de permisos y E/S no están incluidos. La suite prueba `winerror=5`, EIO y EINVAL sin `winerror`; las sondas comprueban además propagación del mismo objeto de excepción y ausencia de llamada a `rename`. Se verificó publicación efectiva tanto con 1 como con 50.

No identifico un falso negativo evidente para el caso medido: `errno=22, winerror=1` entra. No se pretende clasificar todos los proveedores posibles. Otro código no reconocido puede mantener el fallo de apertura, pero conserva el comportamiento seguro anterior; no corresponde ampliar el conjunto por conjetura. Los errores POSIX de operación no soportada quedan fuera deliberadamente, conforme al mandato.

## 4. Los temporales

El `finally` de `head/core/viabilidad_json.py:359-367` sigue siendo correcto:

- Si `rename` tiene éxito, el nombre temporal ha desaparecido; `unlink(missing_ok=True)` acepta su ausencia y no borra el destino.
- Si `rename` falla antes de publicar, el temporal permanece y el `finally` lo elimina. Se comprobaron colisiones reales y fallos inyectados con códigos 5, 32 y 112; estos últimos se propagaron sin dejar destino ni temporal.
- Si el proceso termina sin ejecutar `finally`, puede quedar un temporal anterior a la publicación. La sonda de muerte lo reproduce; es el residuo que el contrato ya admite.

No debe confundirse este resultado con una garantía de limpieza si el propio `unlink` falla por permisos/E/S: puede dejar residuo y reemplazar la excepción que se estaba propagando. Ese límite existe también en base y no lo introduce este diff.

El comentario de `364-366`, no modificado, ha quedado desactualizado: «nada en este camino deja a `tmp` ausente por si mismo» ya no describe el éxito de la vía nueva. `missing_ok=True` ahora es necesario también por ese éxito normal. Es una corrección editorial aconsejable, no un defecto de ejecución ni una condición para integrar.

## 5. Fuera de Windows

**El flujo conserva el comportamiento anterior.** `FileExistsError` sigue teniendo su tratamiento anterior. Los demás `OSError` llegan al nuevo `except`, pero la guarda de plataforma provoca un `raise` desnudo, que conserva la excepción original; después se ejecuta el mismo `finally`. Los errores ajenos a `OSError` tampoco adquieren una vía nueva.

Se comprobó la decisión con un proxy de `os` limitado al módulo revisado: `name="posix"`, errores 1 y 50, y un `rename` que fallaría el test si se llamara. En ambos casos salió exactamente el error del enlace y se limpió el temporal. **Es una prueba de la bifurcación, no una ejecución sobre un sistema operativo POSIX.**

## 6. Los tests prueban lo que dicen

**La carrera simulada es representativa.** Crear el destino dentro del intento fallido de enlace coloca un nombre ajeno después del atajo inicial y antes de la publicación. Para el renombrado, importa ese estado, no que lo haya creado otro hilo. La sonda adicional que crea el destino dentro del propio envoltorio de `rename` comprueba una ventana todavía posterior.

En este Windows los tests nuevos de éxito y carrera ejercitan la vía real de renombrado; no salen por el atajo de plataforma. El test de permisos ejercita deliberadamente el rechazo del fallback. El test parametrizado del clasificador solo prueba el clasificador: su caso 50 no acredita por sí solo la integración en `escribir`.

Se ejecutó `mutaciones_r2.py`, exclusivamente sobre `scratch`, restaurando después los bytes originales:

| Mutación artificial | Resultado de los 31 tests originales, semilla 777 | Qué demuestra |
|---|---|---|
| Cambiar `os.rename` por `os.replace` | 1 fallo, 30 pasan | El test nuevo de carrera detecta la pérdida de exclusión. |
| Quitar `os.name == "nt"` de la guarda | 31 pasan en Windows | Esta ejecución no protege contra habilitar accidentalmente el fallback en POSIX. |
| Añadir a la guarda `exc.winerror == 1`, dejando intacto el clasificador | 31 pasan | No hay prueba original de integración del código 50. |

Los dos mutantes supervivientes son evidencia de huecos de cobertura, **no defectos presentes en head**. Eliminar la guarda sí puede ser detectado al correr los tests originales en POSIX; no se ha hecho aquí. Conviene conservar una prueba de la decisión por plataforma y parametrizar el éxito completo con 1/50 si se quiere cerrar esos huecos.

La suite original tampoco tiene ataques específicos a directorios, equivalencia de mayúsculas, error no-colisión de `rename`, ni muerte abrupta en la vía nueva. Las sondas entregadas cubren los casos descritos, pero no pasan a formar parte automáticamente del repositorio. En POSIX, el test nuevo de éxito retorna tras verificar `OSError` y no comprueba allí los restos; tampoco verifica la identidad del error original.

Ejecución y evidencia conservada:

- `pytest-777-reintento.log`: **31 passed**, 10,23 s.
- `pytest-31337-reintento.log`: **31 passed**, 11,51 s.
- `sondas-r2.log`: **26 passed**, 14,04 s.
- `mutaciones-r2.log` y `mutacion-*.log`: resultados de los controles anteriores, incluido el test concreto que rechaza `replace`.

Las primeras invocaciones usando `workdir=scratch` de la herramienta terminaron con 31 errores de setup por `WinError 5` al crear el basetemp; no ejecutaron las pruebas. La sonda mínima mostró que también fallaba allí un `mkdir` ordinario, tanto con modo 0777 como 0700. Entrando desde la raíz autorizada con `Set-Location scratch` desapareció el problema. Se conservaron los logs fallidos `pytest-777.log` y `pytest-31337.log`; no se parcheó pytest ni se relajó ningún test.

Reproducción desde este directorio, con el Python indicado en el mandato:

```powershell
$py = 'C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
Push-Location scratch
$env:CASOS_ROOT = Join-Path (Get-Location) '_casos_sinteticos'
& $py -m pytest tests/test_viabilidad_json.py -p no:cacheprovider --randomly-seed=777 --basetemp=_bt777
& $py -m pytest tests/test_viabilidad_json.py -p no:cacheprovider --randomly-seed=31337 --basetemp=_bt31337
Pop-Location
& $py -m pytest sondas_r2.py -p no:cacheprovider --randomly-seed=777 --basetemp=_bt_sondas -v
& $py -B mutaciones_r2.py
```

## 7. El docstring contra el código

La adición de `head/core/viabilidad_json.py:297-300` describe correctamente el fallback y su guarda de plataforma. Los párrafos anteriores, que hablan solo del enlace, deben leerse con esa excepción añadida; la publicación completa y la exclusión no se pierden.

Hay dos límites de la prosa que no convierto en defectos nuevos del diff:

1. `284-289` ya prometía en base «GARANTIZADA siempre» incluso ante «corte de luz». Cerrar el fichero y publicar su nombre no demuestra persistencia física. La vía nueva tampoco establece esa garantía; sería más preciso separar muerte del proceso de apagón del sistema. No se reprodujo corrupción por apagón y no se atribuye al cambio una regresión que ya afectaría al esquema anterior.
2. El comentario sobre `missing_ok` señalado en §4 requiere actualizar su explicación para incluir el renombrado exitoso. La instrucción ejecutada es correcta.

También es heredada la redacción de `323-327` que agrupa `os.rename` y `os.replace` y después dice «En Windows si fallan»: esa frase no debe leerse como garantía de no reemplazo para `os.replace`. El nuevo comentario `347-348` distingue correctamente la operación sin `REPLACE_EXISTING`, y la mutación demuestra por qué importa.

La Task 4 del plan conserva una propuesta de publicación mediante creación exclusiva y escritura del destino. Es contexto, no el diff revisado: el código entregado publica por renombrado un temporal completo. No se le exige reintroducir aquella escritura por partes para coincidir con un plan anterior.

## Evidencia de no mutación y alcance operativo

`hashes-apertura.json` y `hashes-cierre.json` contienen SHA-256 de los bytes de **todos** los ficheros, con rutas relativas: **1.405 en base y 1.405 en head**. Los diccionarios completos coinciden: ningún fichero añadido, eliminado o alterado en ambos árboles. No se normalizaron sus bytes al calcular estos hashes, para que un cambio de terminadores también se detectara. Las mutaciones se limitaron a la copia `scratch` y su módulo quedó restaurado byte por byte frente a head.

Todos los artefactos generados y las escrituras de prueba se ubicaron dentro de este directorio. No se usó red, Drive ni el repositorio real. Como excepción de lectura al perímetro solicitado, el entorno del agente exigió consultar fuera del directorio las instrucciones de las skills `using-superpowers` (y su referencia para Codex), `verification-before-completion` y `systematic-debugging`; no se usaron como fuente de hechos sobre el objeto ni se escribieron allí datos. No se consultó memoria de revisiones anteriores.

## Lo que intenté refutar y NO pude

- Pisar un fichero o directorio aparecido después de `exists()`, incluso justo antes del renombrado: las 12 combinaciones conservaron el destino.
- Eludir la exclusión usando mayúsculas: se comprobó que los nombres colisionaban y el renombrado real rechazó la sustitución.
- Conseguir dos ganadores simultáneos: 20 escritores sincronizados dejaron un solo ganador y su contenido completo.
- Publicar solo parte del JSON por la vía 1 o 50: se comprobó el contenido completo antes y después del renombrado.
- Dejar basura tras un fallo ordinario de renombrado: tres errores inyectados y las colisiones reales limpiaron el temporal.
- Tomar el fallback ante errores ajenos o con plataforma POSIX simulada: se propagó el error original sin llamar a `rename`.
- Dejar el destino parcial al terminar el proceso antes/después de publicar: el subproceso dejó respectivamente un temporal completo o el destino completo.
- Que el test original de carrera aprobase una primitiva destructiva: la mutación a `replace` lo puso rojo.

## SIN VERIFICAR

- El montaje de Drive for Desktop, sus carreras reales, sincronización entre equipos y comportamiento interno ante caídas: no está disponible y el mandato prohíbe acceder a él. Se aceptan como evidencia aportada las mediciones del autor; no se presentan como repetidas aquí.
- Un corte de luz, una caída del sistema operativo o una interrupción dentro de la operación del driver. `os._exit` no simula estos sucesos y las pruebas no certifican durabilidad.
- Ejecución en un sistema POSIX real. Se revisó el flujo y se probó la guarda con un proxy local al módulo, sobre Windows.
- Inspección independiente del fuente C de CPython y documentación externa de Win32 en esta sesión, por el perímetro y la prohibición de red. La semántica de colisión se comprobó con `os.rename` real en Python 3.14.4 sobre NTFS local.
- Suite completa y flujos de apertura con servicios externos: fuera del alcance ejecutado. No se extrapola el verde del módulo a toda la aplicación.

El objeto no me desbordó al esfuerzo de esta ejecución; las limitaciones anteriores son de entorno y alcance, no trabajo omitido por falta de capacidad.

SHIP
<!-- informe-literal:fin:vi6h -->

## 2. Evidencia verificada por mí contra la fuente

- **Digest.** Recomputado: el canónico coincide con el que da el revisor (`8dc25180…`).
- **SHIP no se acepta por el veredicto, sino por el ataque que hay detrás**, y el informe lo trae
  anclado a sondas ejecutadas: doce combinaciones de carrera (fichero, directorio, mayúsculas;
  antes, dentro del enlace y dentro del `rename`) con el destino ajeno intacto; veinte escritores
  con un solo ganador; muerte del proceso antes y después del `rename`; y tres mutantes, de los
  que el que cambia `os.rename` por `os.replace` **muere** por el test de la carrera.
- **Lo medido en el montaje de Drive**, que el revisor no podía repetir y dejó como SIN VERIFICAR:
  en `G:\Mi unidad\`, carpeta de sondeo propia y borrada, `os.link` → `WinError 1`,
  `os.rename` sobre un existente → `FileExistsError` (`WinError 183`) con el destino intacto; y
  `escribir` real con el módulo de `d0d1427`: primera escritura publicada y válida, segunda
  `FileExistsError` «no se pisa», sin temporales.
- **Los dos mutantes supervivientes, cerrados en `2b2653c`**: con los tests de ese commit, el que
  quita `os.name == "nt"` de la guarda muere por
  `test_fuera_de_windows_no_hay_via_de_repuesto_aunque_el_error_la_pida`, y el que solo acepta el
  `winerror` 1 muere por `test_sin_enlace_duro_el_json_se_publica_igual[50]`. No repetí su
  supervivencia contra los tests de `d0d1427`: la afirma el revisor con su tabla de mutaciones.
- **Tiempos.** Lanzado a las 16:05; `exec` salió con `exit=0` (`_exit.txt` del lanzador).
- **Adjudicación:** `docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana.md` §7.
