---
tipo: revision-adversarial
objeto: docs/superpowers/plans/2026-09-13-fila30-boton-sala-lectura.md
objeto_rev: "1"
commit: c133108
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: qz7v
sha256_informe: c7c54c8fa9b65c54df9173965d047b41f25379bad147ca027c888115f7462c3a
adjudicado_en: docs/superpowers/plans/2026-09-13-fila30-boton-sala-lectura.md §5
---

# Acta — R1 adversarial sobre el diff de la fila #30 (`[APER-70]`)

Objeto: el **diff** `f1759cf..c133108`. Se archivaron las dos copias `git archive`; el
revisor trabajó sobre ellas, sin `.git` y sin tocar el repositorio real.

| | |
|---|---|
| Revisor | Codex CLI `0.153.4`, binario `7ac07f4ce733f89a`, `model_reasoning_effort=high` |
| Objeto | `C:/t/fila30-sala-lectura-20260913-203148/{base,head}` — 1317 y 1320 ficheros |
| `sha256` de los seis ficheros, al abrir y al cerrar | idénticos, y **coinciden con los que calculé yo antes de lanzar**; el revisor recomputó además el manifiesto completo de los dos árboles (cero altas, bajas o cambios de bytes) |
| `sha256` del informe | `c7c54c8fa9b65c54df9173965d047b41f25379bad147ca027c888115f7462c3a` — **fichero crudo y bloque canonicalizado coinciden**, así que la cadena se verifica contra la salida del revisor |
| Veredicto | **NO-SHIP** |
| Hallazgos | 9 (1 `ALTO`, 4 `MEDIO`, 4 `BAJO`) — **9 confirmados, 0 refutados** |

**La ronda encontró un defecto de flujo normal, no de borde.** El `ALTO` (H-01) dice que el
lector valida el layout del **motor retirado** y rechaza el de la **skill que gobierna**: la
skill pone los cuatro artefactos dentro de `Sala lectura/` y `c4` buscaba el catálogo en
`01_Procesado/`. Consecuencia: una sala recién construida por el constructor que la propia
pantalla recomienda salía **incompleta**, con su catálogo contado además como un documento
más — y volver a correr la skill no lo arreglaba nunca.

**Y midió, no leyó.** Reprodujo H-01 ejecutando los helpers reales de la skill
(`indices_desde_manifiesto.py`, `manifiesto_a_catalogo.py`); H-02 inyectando `PermissionError`
en `os.scandir`; H-03 sustituyendo `estado` por una versión que escribe y corriendo **el
cuerpo original** de mi test —`control_mkdir: ["VERDE","VERDE","VERDE"]`, o sea mi sello era
ciego al `mkdir` que prometía cazar—; H-06 contrastando mi resolutor contra
`PathFinder.find_spec`; y corrió **las dos semillas** de la suite completa.

**Declaró su propia higiene y sus propios límites**, y se archivan: encontró un `_stdout.log`
en su workdir —lo dejó mi `exec`, que escribe ahí— lo enumeró y declaró **no haberlo leído**;
declaró que una primera corrida suya con el `cwd` equivocado no acredita nada y conservó su
log; y declaró que una sonda de permisos suya no interceptó lo que pretendía, por lo que **no
la usa como prueba**.

**Los cinco rojos de sus corridas son ambientales y los identifica uno a uno:** `.venv` y
`git` ausentes en una copia `git archive`. El conteo, **5.457**, coincidió con el mío.

## 0. Mandato, literal

<!-- mandato-literal:inicio:qz7v -->
# Revisión adversarial R1 — diff de la fila #30 (FeesDefender)

Eres el revisor adversarial. **Solo lectura sobre el objeto.** Tu informe va a un acta
hermana y se archiva literal, así que escribe para que otro pueda recomprobarte.

## §0 — Higiene del workdir

Tu directorio de trabajo (`.`) debe contener **solo este `MANDATO.md`**. Si encuentras
cualquier otro fichero, **no lo leas** y decláralo en la primera línea de tu informe.

## §0-bis — Por qué este mandato está redactado como AUDITORÍA

Parte del diff es un **guard de test** que afirma una propiedad sobre el código del
repositorio. Un mandato que pidiera «rompe el guard» o «encuentra una vía que el guard no
vea» se lee como una petición de evasión de un control de seguridad, y en una ronda
anterior eso disparó un filtro de contenido y mató la revisión tras quemar 154.000 tokens
sin producir informe.

Aquí el trabajo es **auditoría de completitud de un instrumento de prueba**: dictaminar si
lo que el guard afirma es exacto, qué casos NO cubre, y si el inventario de sus límites que
él mismo declara está completo. El filo no está en el verbo: está en que cada hallazgo vaya
anclado a `fichero:línea` y en que me entregues el inventario de lo **no cubierto**. Si
alguna frase te suena a otra cosa, interprétala como auditoría y dilo.

## §1 — El objeto

Dos copias congeladas, **hermanas de tu workdir**, y ninguna es un repositorio git (no hay
`.git`, así que no puedes acreditar genealogía: verifica **contenido y hash**).

- `../base/` — el árbol ANTES (commit `f1759cf`).
- `../head/` — el árbol DESPUÉS (commit `c133108`).

**El diff toca exactamente seis ficheros:**

| Fichero | Qué es |
|---|---|
| `core/sala_lectura_estado.py` | **NUEVO** — lector de estado, solo lectura |
| `tests/test_sala_lectura_estado.py` | **NUEVO** — sus 17 tests |
| `tests/test_guard_ui_sin_deprecados.py` | **NUEVO** — el guard, 8 tests |
| `streamlit_app.py` | MODIFICADO — el expander «📚 Sala de lectura» |
| `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` | MODIFICADO — el bloque `[APER-70]` del §7 |
| `docs/MEJORAS_FUTURAS.md` | MODIFICADO — nota al final de la entrada `## 34.` |

**Abre y cierra con el `sha256` de esos seis ficheros en `../head/`** y ponlos en el
informe. Es la prueba de no-mutación que sustituye al `git status`. **No escribas en
`../head/` ni en `../base/`.** Si necesitas ejecutar algo, **copia a tu workdir**.

## §2 — Qué hace el diff, en una frase

`streamlit_app.py` llamaba a `core.sala_lectura.organizar`, módulo cuya docstring empieza
por `[DEPRECADO 2026-06-18] … queda SUPERSEDIDO por la skill … No ampliar`. Quien pulsaba
ese botón es personal del despacho que no toca código. El diff (a) convierte el expander en
**solo lectura**, (b) añade un lector que dice en qué punto está la sala, y (c) añade un
guard que afirma: **«`streamlit_app.py` no importa ningún módulo de `core/` cuya docstring
lo declare deprecado»**.

## §3 — Puedes EJECUTAR, y eso cambia la ronda

Intérprete con todas las dependencias, verificado:
`C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`
Tiene `pytest`, `pytest-randomly`, `pytest-xdist`, `yaml`, `dotenv`, `filelock`, `typer`,
`httpx`.

Dos avisos operativos:
- Usa `--basetemp` **relativo dentro de tu workdir** (p. ej. `--basetemp=bt`). Una ruta
  larga tumba tests que están bien, y tu sandbox no puede crear en la raíz de `C:`.
- Ejecuta sobre una **copia** en tu workdir, no sobre `../head/`.

Correr la suite completa con dos semillas (`-p randomly --randomly-seed=777` y `=31337`) es
bienvenido: el autor afirma **5457 recogidos, 0 fallos, 0 errores, 94 skipped** con 777.
Si no lo compruebas, decláralo SIN VERIFICAR.

## §4 — Lo que quiero que dictamines

Ancla **cada** hallazgo a `fichero:línea` de `../head/`. Prioriza lo que un usuario real
pueda sufrir sobre lo estético.

**A. El lector (`core/sala_lectura_estado.py`).**
1. Su docstring afirma que **nada de aquí escribe**. ¿Es exacto? Recorre todas las rutas,
   **incluida la que delega** en `verificar_apertura.c4_artefactos_de_la_sala` y todo lo que
   esa función a su vez llama. Si alguna crea un directorio, un fichero, o muta estado del
   proceso, dilo con la línea. El test `test_leer_el_estado_no_toca_un_solo_byte` pretende
   fijarlo: **pon delante de él un caso tuyo** que sí escriba y dictamina si lo detecta —
   ese es el control positivo del instrumento.
2. `_contar_documentos`: ¿cuenta lo que su docstring dice? Piensa en enlaces simbólicos,
   ficheros ocultos, `__pycache__`, ficheros de cero bytes, y en qué hace `rglob` si la
   carpeta desaparece a mitad. ¿Alguno de esos casos produce un número que engañe a quien
   lo lee en pantalla?
3. `_solicitud`: afirma que identifica por W-code y **nunca** por el `case_id`, porque el
   `case_id` lleva la dirección del inmueble dentro (PII de un tercero). ¿Hay **alguna**
   rama por la que el nombre de la carpeta, o parte de él, acabe en el texto devuelto?
   Incluye lo que pueda venir dentro de `artefactos.evidencia`.
4. `_ARTEFACTOS_EN_LA_SALA` se **deriva** de `verificar_apertura._ARTEFACTOS_SALA` en vez de
   transcribirse. ¿La derivación es correcta hoy? ¿Y qué pasa si alguien añade un quinto
   artefacto que viva fuera de la sala?
5. El módulo importa dos privados de otro módulo (`va._dir_estructural`, `va._PROCESADO`…).
   ¿Es eso un riesgo real de rotura o una preocupación cosmética? Argumenta.

**B. El guard (`tests/test_guard_ui_sin_deprecados.py`).**
6. **Auditoría de cobertura.** El guard afirma que la UI no importa módulos deprecados.
   Enumera las formas de importar un módulo de `core/` en Python que este detector **no
   ve** — ya sea porque no son sintácticamente un `import`, porque el nombre se construye,
   o porque el import ocurre en otro fichero que la UI sí importa. Quiero el **inventario**,
   no un ejemplo. La docstring del guard no declara ningún límite: ¿debería?
7. La distinción **declarar** vs **citar** (`declaracion_de_deprecado`): el criterio es que
   el marcador abra la primera línea no vacía de la docstring. ¿Es ese el criterio que el
   repo usa de verdad? Compruébalo contra los módulos reales de `../head/core/`.
   ¿Hay algún módulo deprecado que este criterio **no** reconocería?
8. `_fichero_del_modulo` resuelve nombres punteados a ficheros. ¿Acierta con paquetes,
   submódulos y símbolos? ¿Puede confundir `core.sala_lectura_estado` con
   `core.sala_lectura`, o a la inversa?
9. Los 8 tests: ¿alguno pasa por una razón distinta de la que su nombre dice? ¿Alguno es
   tautológico (verde por construcción del fixture, no por el comportamiento)?

**C. La UI (`streamlit_app.py`, el expander «📚 Sala de lectura»).**
10. Recorre el bloque nuevo. ¿Hay alguna entrada —caso sin `01_Procesado`, `01_Procesado`
    ocupado por un fichero, caso que el localizador no encuentra, permisos— que rompa el
    render de la pestaña entera en vez de mostrar un mensaje?
11. El `except Exception` con `# noqa: BLE001`: ¿traga algún error que el usuario debería
    ver de otra forma, o que debería propagarse?
12. ¿Queda en el fichero algún resto del camino retirado (variables muertas, claves de
    `session_state` huérfanas, imports sin usar)?

**D. Las afirmaciones de los documentos.**
13. El runbook afirma ahora que el motor deprecado **sí** produce estructura plana desde el
    PR #328. Verifícalo contra `../head/core/sala_lectura.py` (mira `_directorio_destino`).
    ¿Es exacto? ¿Y la afirmación de que escribe «dos de los cuatro» artefactos?
14. ¿Alguna afirmación del runbook o de `MEJORAS_FUTURAS.md` en este diff no se sostiene
    contra el código de `../head/`?

## §5 — Formato del informe

Escribe **`INFORME.md`** en tu workdir, en español, con:

1. Primera línea: declaración de higiene del §0.
2. `sha256` de los seis ficheros **al abrir**.
3. Un hallazgo por bloque, cada uno con: **id** (`H-01`…), **severidad**
   (`CRÍTICO` / `ALTO` / `MEDIO` / `BAJO`), `fichero:línea`, qué está mal, **cómo se
   reproduce** y qué habría que hacer. Si un hallazgo lo confirmaste **ejecutando**, dilo y
   pega la salida.
4. Una sección **«Lo que NO pude verificar»**, explícita. Un límite declarado vale más que
   una conclusión adornada. **No des por refutado lo que no miraste.**
5. `sha256` de los seis ficheros **al cerrar**, y si coinciden con los de apertura.
6. **Última línea del informe: el veredicto, exactamente una de estas tres palabras y nada
   más:**

```
SHIP
SHIP-CON-REPAROS
NO-SHIP
```

No adornes el veredicto ni lo expliques en esa línea: la explicación va arriba.
<!-- mandato-literal:fin:qz7v -->

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:qz7v -->
Higiene §0: INCUMPLIDA al inicio; además de MANDATO.md había _stdout.log. No lo he leído.

## SHA-256 al abrir

| Fichero en `../head/` | SHA-256 |
|---|---|
| `core/sala_lectura_estado.py` | `e23f5fad7d18ba43dbea681b44aacf1c032cdeefc7ec1f9da256fa21eb1a6213` |
| `tests/test_sala_lectura_estado.py` | `e912818cf16bea3c8f270fe9a4af25245ae6410299686ab58c12aa27dad10cbd` |
| `tests/test_guard_ui_sin_deprecados.py` | `da45a77e027d14c9927d82ad4cb29a0155081c05f626371d56bdab8a6f2f997c` |
| `streamlit_app.py` | `e0968ccbc16a3bccc278563e41bbc3351855ecf3e8d85bfc5a95b916c5d8ad90` |
| `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` | `bbfcefef4fe96252b201c5a6b3473a23fb754166bc7d598748e876e07b109b73` |
| `docs/MEJORAS_FUTURAS.md` | `1ea4c6e35784858092156530c78a01e5cde0f1644e9894cf701247da716f3315` |

# Revisión adversarial R1 — fila #30

Objeto: las copias congeladas `../base/` y `../head/`, identificadas en el mandato como `f1759cf` y `c133108`. No contienen `.git`: estos identificadores son atribuciones del mandato, no genealogía acreditada por esta revisión. Comparé los bytes de todos los ficheros de ambos árboles: las diferencias son exactamente los seis ficheros enumerados. Tres son nuevos y tres modificados. Las ejecuciones importan exclusivamente las copias `obj/` y `obj2/`, bajo este workdir. No modifiqué los árboles objeto.

Interpreto el apartado B como auditoría de completitud de un instrumento de prueba. Los ejemplos sintéticos caracterizan qué reconoce y qué deja sin cubrir; no he cambiado el guard del objeto. El veredicto recomendado al final se apoya principalmente en H-01: la pantalla rechaza como incompleta una sala construida conforme a la skill que ella misma recomienda. La adjudicación corresponde a Claude contra la fuente.

Todas las referencias `fichero:línea` siguientes corresponden a `../head/`, salvo indicación expresa. Los scripts de reproducción y sus logs se conservan junto al informe. Los nombres de casos de las sondas son sintéticos.

## Hallazgos

### H-01 — ALTO — El lector valida el layout del motor retirado y rechaza el de la skill gobernante

**Anclaje:** `core/sala_lectura_estado.py:43`, `core/sala_lectura_estado.py:48`, `core/sala_lectura_estado.py:133`; exposición en `streamlit_app.py:1419`, `streamlit_app.py:1425` y `streamlit_app.py:1429`. Fuente delegada: `core/verificar_apertura.py:249`. Contrato del constructor: `.claude/skills/organizar-sala-lectura/SKILL.md:124` y `.claude/skills/organizar-sala-lectura/SKILL.md:465`.

**Qué está mal y daño:** la skill coloca **los cuatro artefactos dentro de `Sala lectura/`**. `c4` busca `indice_documental.yaml` en el padre y el nuevo contador excluye de la sala únicamente los otros tres. Por tanto, una sala que acaba de construirse conforme a la skill aparece incompleta, se cuenta el catálogo como documento y se ofrece una solicitud de completar algo que ya está. Pedir otra ejecución de la misma skill no corrige la discrepancia. Si además existe un catálogo antiguo en el padre, el lector puede dar verde por ese catálogo ajeno a la generación de la sala.

**Reproducción ejecutada:** `auditar_extra.py` crea un manifiesto sintético de un documento, ejecuta los helpers reales `indices_desde_manifiesto.py` y `manifiesto_a_catalogo.py` de la skill y llama al lector. El primero devolvió 0 y el segundo terminó sin excepción. Extracto literal de `sondas_extra3.log`:

```text
indices_exit: 0
skill_helpers_reales: {"archivos": ["2025-01-01_documento.txt", "CRONOLOGIA.md", "INDICE.md", "_MANIFIESTO.md", "indice_documental.yaml"], "montada": true, "n_documentos": 2, "evidencia": {"presentes": ["CRONOLOGIA.md", "INDICE.md", "_MANIFIESTO.md"], "faltan": ["indice_documental.yaml"], "vacios": [], "no_ficheros": []}}
```

También se reprodujo con el fixture mínimo de `auditar.py`: `solicitud` pide el catálogo que ya está dentro de la sala. No se ejecutó un LLM: se ejercieron los generadores deterministas y la ubicación prescrita por la skill.

**Qué hacer:** adjudicar y unificar la ubicación canónica del catálogo entre constructor, verificador y contador; si se admiten ambos layouts, distinguirlos explícitamente y evitar que un catálogo del padre haga pasar por completa otra generación de la sala. Añadir una prueba de integración que entregue al lector los artefactos generados por los helpers de la skill. Copiar un YAML a otra ubicación para silenciar el aviso no resuelve el desacuerdo entre contratos.

### H-02 — MEDIO — Una enumeración incompleta puede convertirse en un recuento exacto y un estado verde

**Anclaje:** `core/sala_lectura_estado.py:89`, `core/sala_lectura_estado.py:132`, `core/sala_lectura_estado.py:136`; `streamlit_app.py:1419` y `streamlit_app.py:1426`. La comprobación anterior del directorio está en `core/verificar_apertura.py:134`.

**Qué está mal y daño:** `rglob` no es una enumeración que garantice lanzar ante todos los errores de acceso. En el Python 3.14.4 suministrado suprime errores de exploración; además, el estado de existencia, los artefactos y el número se leen en momentos distintos. El resultado no distingue «cero ficheros» de «no pude enumerar». El `except Exception` de la UI no ayuda cuando el error ya fue suprimido por el iterador.

**Reproducción ejecutada:** `auditar.py` (1) inyecta `PermissionError` en `os.scandir` únicamente para la sala y deja accesibles sus artefactos; (2) mueve la sala a una ruta hermana **dentro del fixture** justo antes de que el contador enumere, después de que `c4` haya dado OK. Salida de `sondas.log`:

```text
sala_desaparece_antes_del_listado: {"montada": true, "n_documentos": 0, "artefactos": "ok"}
permiso_listado_denegado: {"montada": true, "n_documentos": 0, "artefactos": "ok"}
```

La denegación está inyectada en el punto de E/S real del listado, no es una prueba con ACL de Windows. La retirada del directorio sí es una operación real de filesystem en el fixture. Es una intercalación determinista que prueba el límite; no mide su frecuencia en Drive. Si desaparece durante un recorrido ya iniciado, puede conservarse el conteo de la parte vista y omitirse el resto.

**Qué hacer:** representar explícitamente un recuento no disponible/incompleto y usar una enumeración que conserve y propague sus errores. Comprobar la validez final de la sala y no presentar como exacta una lectura detectada como inconsistente. No hace falta convertir este lector en escritor ni añadir bloqueos de escritura.

### H-03 — MEDIO — El test de no escritura no detecta precisamente el `mkdir` que promete detectar

**Anclaje:** `tests/test_sala_lectura_estado.py:47`, `tests/test_sala_lectura_estado.py:51`, `tests/test_sala_lectura_estado.py:235` y `tests/test_sala_lectura_estado.py:243`; garantía atribuida al test en `core/sala_lectura_estado.py:29`.

**Qué está mal:** `_sello` registra únicamente rutas de ficheros regulares y su contenido. Crear un directorio vacío cambia el expediente pero no el sello. Tampoco observa cambios de metadatos, escrituras transitorias restauradas, cambios fuera de `case_dir` ni estado global del proceso. Los tres casos parametrizados tampoco incluyen el expediente sin `01_Procesado`.

**Control positivo ejecutado:** `auditar.py` sustituye temporalmente `sle.estado` por una función que escribe y luego llama al original, e invoca **el cuerpo original de `test_leer_el_estado_no_toca_un_solo_byte`**, en sus tres parametrizaciones. No se cambia el test objeto. `sondas.log`:

```text
control_mkdir: ["VERDE", "VERDE", "VERDE"]
control_fichero: ["ROJO", "ROJO", "ROJO"]
control_contenido: ["ROJO", "ROJO", "ROJO"]
control_mtime: ["VERDE", "VERDE", "VERDE"]
control_entorno: ["VERDE", "VERDE", "VERDE"]
```

En los casos sin ficheros, el control `contenido` crea uno para disponer de una escritura detectable. El control `mkdir` crea `_directorio_nuevo` en todos los casos; el de `mtime` modifica el timestamp de `01_Procesado`; el de entorno cambia un canario que luego retira el arnés.

**Qué hacer:** incluir rutas y tipos de directorio en la huella, añadir el control positivo de `mkdir` y ajustar la promesa del test a su alcance. Si se quiere afirmar ausencia de **operaciones** de escritura y no sólo igualdad final de contenido, observar también los sumideros de escritura. Esto es un defecto del instrumento: no demuestra que el lector actual escriba; las rutas del lector auditadas no lo hacen.

### H-04 — MEDIO — El guard atribuye una propiedad general a una comprobación sintáctica de un solo fichero

**Anclaje:** `tests/test_guard_ui_sin_deprecados.py:15`, `tests/test_guard_ui_sin_deprecados.py:18`, `tests/test_guard_ui_sin_deprecados.py:69`, `tests/test_guard_ui_sin_deprecados.py:78`, `tests/test_guard_ui_sin_deprecados.py:85` y `tests/test_guard_ui_sin_deprecados.py:144`. La afirmación se traslada al runbook en `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:712`.

**Qué está mal:** sólo recorre nodos `Import`/`ImportFrom` absolutos con prefijo literal `core` en `streamlit_app.py`, resuelve candidatos a `.py`/`__init__.py` y examina su docstring estática inicial. No declara esos límites. La promesa «deprecar un módulo basta para que su uso en la UI se ponga rojo» es demasiado amplia.

**Inventario de lo NO cubierto, por familias de mecanismos:**

| Familia | Qué queda fuera y por qué |
|---|---|
| Import por llamada | `__import__`, `builtins.__import__`, `importlib.import_module`; también sus alias, wrappers, `getattr` y referencias guardadas. Son `Call`, no nodos de import del módulo objetivo. Se pierde incluso el nombre literal. |
| Nombre calculado | Concatenación, f-string, variable, tabla, configuración, entorno, selección de plugins/callbacks. No hay propagación de valores. Este límite se añade al anterior, no requiere una técnica distinta de carga. |
| Código cargado o evaluado | `exec`, `eval` que llama al importador, `compile` seguido de ejecución, `runpy.run_module`/`run_path`, `spec_from_file_location`/`exec_module` y loaders de `importlib.machinery`. No se inspecciona la fuente cargada ni la cadena ejecutada. Algunas formas ejecutan el fichero sin registrarlo como import ordinario; igualmente quedan fuera de la frontera funcional anunciada. |
| Import transitivo | La UI importa un adaptador, otro módulo de `core`, un módulo de `scripts` o un paquete que a su vez importa el deprecado. El guard no recorre ese grafo ni los cuerpos de los llamadores. |
| Reexportaciones y carga diferida | Un símbolo se reexporta desde una fachada o `__init__.py`; un `__getattr__` de módulo/paquete carga otro módulo al solicitar un atributo; una función importada lo carga al ejecutarse. Resolver la fachada no inspecciona esa procedencia. |
| Estrella | `from core import *` produce **cero candidatos**, ni siquiera `core`; no expande `__all__`. `from core.pkg import *` sí examina `core.pkg`, pero no los módulos que exporta. |
| Inicializadores de ancestros | `import core.pkg.live` ejecuta normalmente `core/__init__.py` y `core/pkg/__init__.py`, pero el guard sólo examina el candidato final. Asimismo, `from core import x` no incluye `core` como candidato. |
| Imports relativos | Se descartan todos los `ImportFrom` con `level > 0`. En el actual entrypoint ejecutado como script los relativos no son una forma válida ordinaria; sí podrían serlo si pasase a ejecutarse como paquete. Límite condicionado, no defecto vivo de ese modo de arranque. |
| Otros nombres para el mismo origen | `import sala_lectura` si `core/` entra en `sys.path`, prefijos como `paquete.core.x`, alias de paquetes en `sys.modules` y resolución mediante hooks. El filtro exige el nombre literal `core` y no acredita identidad por origen. |
| Importadores y formatos fuera del árbol `.py` | Extensiones, sólo bytecode, zip, porciones de namespace en otra ruta, `__path__` ampliado y `sys.meta_path`/`path_hooks` personalizados. El resolutor sólo conoce dos ubicaciones de fuente local; no reconstruye el sistema de imports de Python. |
| Declaración dinámica o convención distinta | Asignaciones a `__doc__` o avisos/decoradores de deprecación no expresados mediante el marcador al comienzo de la docstring inicial. Es un límite adicional del clasificador de deprecación, no de `ast.walk`. |

El detector tampoco modela alcanzabilidad: marca imports bajo `if False`, `TYPE_CHECKING` o ramas nunca ejecutadas. Puede ser una política estática deliberada, pero no equivale a describir exactamente los imports realizados en ejecución.

**Reproducción ejecutada:** `auditar.py` crea árboles separados con un `core/probe.py` deprecado. Extractos literales de `sondas.log`:

```text
guard_builtin_import: {"candidatos": [], "deprecados": {}}
guard_importlib_literal: {"candidatos": [], "deprecados": {}}
guard_importlib_compuesto: {"candidatos": [], "deprecados": {}}
guard_exec: {"candidatos": [], "deprecados": {}}
guard_wrapper: {"candidatos": [], "deprecados": {}}
guard_reexport: {"candidatos": ["core.fachada", "core.fachada.ejecutar"], "deprecados": {}}
guard_from_core_estrella: {"candidatos": [], "deprecados": {}}
guard_relativo: {"candidatos": [], "deprecados": {}}
guard_ancestros: {}
```

Los controles `import core.probe as p`, `from core import probe`, `from core.probe import COSA` y `from core.probe import *` sí señalaron `core.probe`. Estos son controles del detector sobre fuentes sintéticas; no se ejecutaron las fuentes UI de los fixtures.

**Qué hacer:** declarar la garantía realmente comprobada, el inventario de límites y el alcance directo en docstring/runbook. Cubrir al menos las formas estáticas y los inicializadores de paquetes que se quieran incluir en el contrato, con controles positivos por familia. No exigir un analizador universal de Python: si la política pretendida es sólo de imports literales directos, nombrarla así. No he encontrado una dependencia deprecada viva en el grafo estático real examinado; esta incompletitud no convierte automáticamente el `head` actual en usuario del motor retirado.

### H-05 — MEDIO — El número mostrado incluye artefactos con otra capitalización y archivos sin valor documental

**Anclaje:** `core/sala_lectura_estado.py:80`, `core/sala_lectura_estado.py:90`, `core/sala_lectura_estado.py:91`; etiqueta para el usuario en `streamlit_app.py:1419`.

**Qué está mal:** la exclusión compara `p.name` con cadenas sensibles a mayúsculas aunque el filesystem de Windows identifica el mismo archivo con otra grafía. Además, todo fichero regular restante se llama «documento»: auxiliares del sistema, cachés y ficheros vacíos entran sin distinción. Es un problema distinto del catálogo de H-01.

**Reproducción ejecutada:** `auditar_extra.py` crea sólo `indice.md`, `cronologia.md`, `_manifiesto.md` en la sala y el catálogo en el padre; `c4` los encuentra y el contador los suma. `auditar.py` crea un documento, `.DS_Store`, `desktop.ini`, `Thumbs.db`, `__pycache__/mod.pyc` y `vacio.pdf`. `auditar_ramas.py` crea un archivo con el atributo Windows Hidden:

```text
artefactos_minusculas: {"estado": "ok", "n_documentos": 3}
conteo_auxiliares: {"ficheros_no_artefactos": 6, "n_documentos": 6}
windows_hidden: {"SetFileAttributesW": 1, "n_documentos": 1}
```

También se ejecutaron enlaces simbólicos reales en este entorno:

```text
enlace_enlace.pdf: {"is_file": true, "n_documentos": 7}
enlace_dir_enlazado: {"is_file": false, "n_documentos": 7}
enlace_roto.pdf: {"is_file": false, "n_documentos": 7}
```

El enlace a fichero cuenta aunque apunte fuera de la sala; el directorio enlazado no se recorre con el `rglob` usado; el enlace roto no cuenta. No deduplica archivos por identidad o hash. No afirmo que todo enlace deba excluirse: sí que la UI no explica que mezcla estas reglas bajo un número de documentos.

**Qué hacer:** alinear la identificación de artefactos con la semántica del filesystem y definir el número que se quiere mostrar. Para contar documentos de la sala, usar el inventario/manifiesto o una política explícita que separe documentos, auxiliares, vacíos y enlaces. No excluir indiscriminadamente todos los ocultos: un archivo oculto puede ser prueba válida. Mantener la exclusión por posición para no perder un adjunto legítimo llamado `INDICE.md` dentro de un compuesto.

### H-06 — BAJO — El resolutor invierte la precedencia real de un paquete frente a un fichero homónimo

**Anclaje:** `tests/test_guard_ui_sin_deprecados.py:99` y `tests/test_guard_ui_sin_deprecados.py:102`.

**Qué está mal:** si existen `core/pkg.py` y `core/pkg/__init__.py`, devuelve primero el fichero. El importador normal consultado aquí prefiere el paquete. Si el paquete es deprecado y el fichero vivo, el guard mira la docstring equivocada. También carece de información de ejecución para decidir si `from core.pkg import COSA` obtiene un atributo ya definido o importa un submódulo físico homónimo; su resolución por presencia de archivo es una aproximación.

**Reproducción ejecutada:** `auditar.py` crea el fichero vivo y el paquete deprecado y consulta tanto al guard como a `importlib.machinery.PathFinder.find_spec`. En `sondas.log`, el guard devuelve `core\pkg.py`, mientras `PathFinder` devuelve el `core\pkg\__init__.py` del mismo fixture. No se ejecuta el módulo. Salida literal:

```text
guard_colision_paquete_fichero: "core\\pkg.py"
python_colision_paquete_fichero: "C:\\t\\fila30-sala-lectura-20260913-203148\\rev\\probe_data\\tmpb02e2ijk\\paquetes\\core\\pkg\\__init__.py"
```

**Qué hacer:** ajustar la precedencia de paquetes y explicitar el carácter conservador de los candidatos a símbolos. Añadir un control para este conflicto. **No existe hoy esa colisión en `head/core/`**: es una deficiencia reproducida del instrumento ante una forma válida, no un módulo real actualmente omitido.

### H-07 — BAJO — «Dos de los cuatro» mezcla el inventario de la sala con el del expediente

**Anclaje:** `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:721`; la misma explicación aparece en `tests/test_sala_lectura_estado.py:148` y `tests/test_sala_lectura_estado.py:153`. Fuente ejecutable: `core/sala_lectura.py:1073`, `core/sala_lectura.py:1100`, `core/catalogo_documental.py:57` y `core/catalogo_documental.py:87`.

**Qué está mal:** en una organización completada sin residuo, el motor escribe `INDICE.md`, `CRONOLOGIA.md` **y** `01_Procesado/indice_documental.yaml`. Son tres de los cuatro que exige el `c4` actual. Son sólo dos **dentro de la sala**, que es otra afirmación. El test cuyo nombre dice «los dos que le faltan» construye catálogo en el padre y verifica que falta únicamente `_MANIFIESTO.md` (`tests/test_sala_lectura_estado.py:158` y `:161`). El aserto es coherente con `c4`; el nombre y la explicación no lo son.

**Reproducción ejecutada:** `auditar_extra.py` ejecuta `motor.organizar` con un TXT llamado `2025-01-01_encargo.txt`, fijando únicamente los localizadores al expediente sintético. Resultado literal de `sondas_extra3.log`:

```text
motor_real: {"resultado": {"case_id": "BaRS1 - Sintetico - (W-00TEST) - Impago", "detenido_por_residuo": false, "n_residuo": 0, "acciones": {"COPY": 1}, "sin_material": false}, "evidencia": {"presentes": ["CRONOLOGIA.md", "INDICE.md", "indice_documental.yaml"], "faltan": ["_MANIFIESTO.md"], "vacios": [], "no_ficheros": []}, "n_documentos": 1}
```

**Qué hacer:** decir «tres artefactos en el expediente, dos de ellos en la sala; falta el manifiesto y la ubicación del catálogo difiere de la skill». Alinear después el texto con la decisión sobre H-01 y corregir el nombre del test. El lector no debe heredar como autoridad una cifra histórica cuya definición cambia de párrafo a párrafo.

### H-08 — BAJO — La afirmación de que nadie escribe el manifiesto en `scripts/` es literalmente falsa

**Anclaje:** `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:722` y `tests/test_sala_lectura_estado.py:154`. Contraejemplo en `scripts/redate_whatsapp_anexos.py:72`, `scripts/redate_whatsapp_anexos.py:134` y `scripts/redate_whatsapp_anexos.py:149`.

**Qué está mal:** `procesar(sala, apply=True)` reescribe `_MANIFIESTO.md` en la línea 150 cuando encuentra anexos por refechar. La frase «no lo escribe nadie en todo core/ ni scripts/» confunde **generarlo inicialmente** con **reescribirlo**. Esto no convierte a ese script en constructor de salas ni rebate que `organizar` no genere el manifiesto.

**Cómo recomprobar:** abrir la función citada: lee el manifiesto en la línea 73, modifica filas en la 141 y ejecuta `manifiesto.write_text(...)` en la 150, condicionado a `apply and cambios`. Confirmado por lectura de fuente; no ejecuté ese script para este hallazgo.

**Qué hacer:** precisar «el motor no genera `_MANIFIESTO.md`» o, si se quiere la afirmación más amplia, «no hay generador inicial en el motor». Evitar una negación global de escrituras que el propio árbol contradice.

### H-09 — BAJO — Un test del guard anuncia un módulo vivo y prueba uno deprecado

**Anclaje:** `tests/test_guard_ui_sin_deprecados.py:224`, `tests/test_guard_ui_sin_deprecados.py:233` y `tests/test_guard_ui_sin_deprecados.py:237`.

**Qué está mal:** `test_un_simbolo_importado_de_un_modulo_vivo_no_rompe_el_resolutor` crea la docstring `[DEPRECADO ...]` y exige que `core.probe` aparezca en el resultado. El test pasa probando la retención del módulo **deprecado** y el descarte del candidato al símbolo, no el caso vivo que anuncia.

**Cómo recomprobar:** contrastar esas tres líneas y ejecutar el fichero de tests, incluido en los 25 tests nuevos aprobados. La diferencia de nombre es verificable por lectura; el test tiene un aserto de comportamiento real y **no es tautológico**.

**Qué hacer:** renombrarlo a módulo deprecado y, si interesa comprobar ambos estados, parametrizarlo con expectativas independientes. No cambiar el aserto para hacerlo coincidir artificialmente con el nombre.

## Respuestas al mandato, punto por punto

### A.1 — Solo lectura, delegación y estado del proceso

Recorrí `estado` (`core/sala_lectura_estado.py:124`) → `_sala` (`:67`) → `va._dir_estructural` (`core/verificar_apertura.py:134`); `c4_artefactos_de_la_sala` (`:235`) → el mismo helper, `Path.is_file/exists/stat` y el constructor `Resultado` (`:73`, validación de estado en `:86`); `_contar_documentos` (`core/sala_lectura_estado.py:80`) → `rglob/is_file`; `_solicitud` (`:95`) → `w_code_de_carpeta` (`core/email_atomize/contaminacion.py:30`) → regex `search/group`.

`c4` no llama al resto del verificador, no carga catálogo, no adquiere workspace/mutex, no llama fuentes remotas ni crea directorios. Los imports de producción alcanzados por el lector son `core/__init__.py`, `core/verificar_apertura.py`, `core/email_atomize/__init__.py` y `core/email_atomize/contaminacion.py`, además de biblioteca estándar. El import de `verificar_apertura_fuentes` está bajo `TYPE_CHECKING` (`core/verificar_apertura.py:56`). No encontré `mkdir`, escritura de archivo, cambio de cwd o entorno en estas rutas de llamada.

`auditar_ramas.py` ejerció caso inexistente, sin procesado, sin sala, sala vacía, completa, con faltantes, con vacíos, artefacto ocupado por directorio y colisiones de las dos rutas estructurales. Comparó rutas **de ficheros y directorios**, bytes, cwd y entorno: los diez casos conservaron el árbol y el estado observado; las dos colisiones lanzaron `_ColisionDeTipo`. `ramas.log` contiene cada resultado. Con hooks de auditoría, `sondas_extra3.log` registra:

```text
efectos_estado_caliente: {"eventos_mutacion": [], "entorno_cambio": false, "cwd_cambio": false, "modulos_nuevos": []}
```

La frase «no muta estado del proceso», entendida **literalmente incluyendo el import**, sería demasiado fuerte: importar registra módulos en `sys.modules` y compila regex. `core/email_atomize/contaminacion.py:21` y `:27` ejecutan `re.compile` al importar. La prueba fría con `-B` (`auditar_import.py`, `import_frio.log`) observó 44 módulos nuevos y 17 entradas adicionales en la caché de `re` por el conjunto de imports; no atribuyo las 17 exclusivamente a las dos regex de ese fichero. No observó escrituras, cambios de entorno o cwd. Sin `-B`, Python puede crear sus cachés de bytecode ordinarias en el árbol de código; eso es distinto de que `estado(case_dir)` escriba el expediente. La promesa de lectura de negocio se sostiene en el código inspeccionado; el instrumento que supuestamente la fija necesita H-03.

### A.2 — Recuento

H-01, H-02 y H-05 recogen los errores reproducidos. La exclusión por posición sí conserva correctamente un adjunto `sub/INDICE.md`, como prueba `tests/test_sala_lectura_estado.py:112`. Los cero bytes siguen siendo ficheros y se cuentan; no validan contenido documental. Los ocultos, `__pycache__`, enlaces a fichero y directorios enlazados se comportan como se detalla en H-05. Una carpeta desaparecida puede devolver cero o un parcial sin excepción, con estado previo de sala montada.

### A.3 — Solicitud y PII

No encontré una rama **actual de `estado`** que inserte la dirección del caso en `solicitud`. `case_dir.name` sólo entra en `w_code_de_carpeta`; el patrón `\((W-[A-Z0-9]+)\)` de `core/email_atomize/contaminacion.py:27` devuelve el grupo W y, si no casa, se usa el texto fijo «carpeta sin W-code». No hay fallback a nombre de carpeta. Minúsculas no admitidas por ese patrón pueden producir falta de identificador, pero no fuga de dirección.

Seguí también `artefactos.evidencia`: en `core/verificar_apertura.py:249`, `:250`, `:252` y `:255`, `faltan` y `vacios` se forman con claves de `_ARTEFACTOS_SALA`, no con rutas resueltas, contenidos de documentos, nombres enumerados del caso ni textos de excepciones. `no_ficheros` usa las mismas claves y además sus elementos están en `faltan`; no abre otra vía. La rama pendiente no introduce evidencia.

**Límite de la afirmación local de `_solicitud`:** esta función no sanea una `Resultado` arbitraria. `auditar.py` le entrega por separado `faltan=[case_dir.name]` y `vacios=[case_dir.name]`: ambas cadenas aparecen completas en la salida (`solicitud_evidencia_faltan/vacios` en `sondas.log`). Las líneas `core/sala_lectura_estado.py:111` y `:113` confían en la procedencia de la evidencia. Es un supuesto de contrato que debe documentarse o validarse con una lista de etiquetas permitidas si esa frontera va a ampliarse. **No lo elevo a una fuga viva del lector:** el único productor actual de esa evidencia es el `c4` inspeccionado, y las sondas de todas sus ramas no filtraron el canario.

### A.4 — Derivación de artefactos y quinto artefacto externo

La derivación en `core/sala_lectura_estado.py:48` es correcta **respecto de la regla actual de `c4`** (`core/verificar_apertura.py:249`): toda entrada salvo `_CATALOGO` se sitúa en la sala. No es una consulta general de ubicaciones; `_ARTEFACTOS_SALA` es una tupla de nombres, no un mapa de destinos. Por eso deriva lo mismo que `c4` hoy, pero ambos discrepan del constructor canónico en H-01.

Si sólo se añade un quinto nombre a la tupla pretendiendo que viva fuera, `c4` lo buscará dentro y la derivación lo tratará como artefacto interno: no se ha expresado su ubicación. Si además se cambia `c4` para situarlo fuera pero no esta comprensión, se excluirá del conteo un posible documento homónimo dentro de la sala. Tampoco se recalcula el `frozenset` tras mutar/reasignar la tupla en un proceso ya importado. Para admitir ese futuro cambio sin divergencia, compartir un descriptor de ubicaciones o una función pública que lo resuelva. No afirmo que exista un quinto artefacto actual que ya falle.

### A.5 — Dependencia de privados

Son **cinco nombres privados distintos**, no sólo dos: `_ARTEFACTOS_SALA`, `_CATALOGO`, `_dir_estructural`, `_PROCESADO`, `_SALA_LECTURA` (`core/sala_lectura_estado.py:48`, `:74`, `:77`). El guion bajo no causa un fallo por sí mismo ni impide importarlos. La dependencia es real: renombrar los dos primeros puede romper el import del lector; cambiar los restantes puede romper una llamada. En la UI los imports están fuera del `try` (`streamlit_app.py:1395`), por lo que una rotura de inicialización no quedaría convertida en mensaje local.

No es un fallo presente por ser privado: los nombres existen, son del mismo repositorio y los tests nuevos ejercen su import y llamada. El riesgo sustantivo es que el contrato de ubicación no está exportado como API y se duplican sus supuestos; H-01 ya demuestra un desacuerdo entre consumidores. Una API pública compartida con pruebas de contrato ayuda más que copiar constantes o renombrarlas sin cambiar el contrato.

### B.6 — Cobertura del guard

Inventario completo por familias en H-04; H-06 precisa una limitación de resolución. Recorrer todo el AST sí detecta imports dentro de funciones, condicionales y expanders: no es un escáner sólo de cabeceras. Esto no lo convierte en interprocedimental ni dinámico.

### B.7 — Declarar frente a citar en los módulos reales

Parseé los **134 `.py` de `head/core/`**, incluidos inicializadores. Entre sus docstrings, sólo `core/sala_lectura.py:1` declara deprecación de módulo; el marcador abre su primera línea y es reconocido. `core/sala_lectura_estado.py:6` lo cita y es correctamente excluido. El barrido de menciones en el resto del código detectó deprecaciones de funciones en `core/email_export.py:65` y `core/intake_drive.py:742`, y metadatos de la API en `core/crm_atlas.py:83`: no declaran deprecado el módulo completo.

**No encontré un módulo realmente declarado deprecado en este árbol que el criterio posicional omita.** Eso acredita compatibilidad con la convención observada, no que toda declaración futura o toda cita inicial pueda clasificarse semánticamente con `startswith`. Por ejemplo, otros idiomas, Markdown antes del marcador o una declaración posterior quedan fuera de la convención que el guard adopta.

El guard real produjo `core.sala_lectura` al aplicarlo a `base/streamlit_app.py` y `{}` al aplicarlo a `head/streamlit_app.py` (`sondas.log`). Además recorrí un grafo estático propio con imports relativos y ancestros: 71 módulos alcanzables desde `streamlit_app`, sin camino a `core.sala_lectura` (`sondas_extra3.log`). No es una traza dinámica ni cierra los límites de H-04.

### B.8 — Paquetes, submódulos y símbolos

Sin colisiones, resuelve `core.email_atomize` a su `__init__.py`, `core.email_atomize.contaminacion` al fichero del submódulo y descarta `core.sala_lectura_estado.EstadoSala` como candidato sin fichero. Lo ejecuté en `auditar.py`. `core.sala_lectura` y `core.sala_lectura_estado` se resuelven a **ficheros distintos exactos**: no hay búsqueda por prefijo ni confusión entre ambos nombres. Un símbolo no existente en el fixture no rompe el AST; tampoco se acredita que el programa del fixture sea ejecutable. El conflicto paquete/fichero y la ambigüedad atributo/submódulo están en H-06.

### B.9 — Los ocho tests

El fichero contiene ocho tests: uno contra el árbol real y siete controles. H-09 identifica el nombre que no describe su fixture. Los otros controles sí ejercen sus intenciones: positivo, negativo, import anidado, cita posterior, mención no inicial en primera línea y comentario en el cuerpo. No encontré un test tautológico en el sentido de asertar un valor construido por el propio fixture sin pasar por el detector. Los negativos, considerados aisladamente, no demostrarían que se detecta nada, pero se complementan con controles positivos.

Sí faltan controles propios de varias formas que la docstring dice normalizar: los positivos originales se centran en `from`, no prueban `import core.x as y`, paquetes con ancestros ni estrella de raíz. Las sondas externas de esta revisión ejercen parte de esa cobertura y muestran los límites restantes. Que los ocho pasen no acredita la proposición general de su primera línea.

### C.10 — Render y entradas problemáticas

Extraje por AST y ejecuté **el bloque nuevo literal**, desde `streamlit_app.py:1384`, con un doble de Streamlit que registra mensajes y un localizador controlado (`auditar.py`). Resultados:

| Entrada | Comportamiento del bloque nuevo |
|---|---|
| Caso sin `01_Procesado` | `st.info` de sala no montada y solicitud; no excepción. |
| `01_Procesado` ocupado por fichero | `_ColisionDeTipo`, capturada y mostrada por `st.error`. |
| Caso que no localiza | `LocalWorkspaceMissing`, capturada y mostrada por `st.error`, con W-code. |
| `PermissionError` propagado por localizador/lector | Se muestra `st.error`. La sonda adicional de `Path.stat` sobre un artefacto confirma que ese error sí puede propagarse. |
| `AttributeError` de programación durante la llamada | También se convierte en `st.error`; ver C.11. |
| Error de listado suprimido por `rglob` | No llega al `except`; mensaje numérico incorrecto de H-02. |

Las selecciones están en la rama con casos disponibles (`streamlit_app.py:448` y `:449`). No observé una entrada de expediente que, por el bloque nuevo ejercido, haga caer toda la pestaña. Eso no certifica la pestaña completa: el bloque siguiente conserva un `_cl.path_for(_caso_rs)` sin protección en `streamlit_app.py:1447`, ya presente en `base` (línea 1421). Si desaparece también su caso seleccionado, ese bloque puede fallar por separado. No lo atribuyo al diff nuevo.

### C.11 — `except Exception` y `# noqa: BLE001`

En `streamlit_app.py:1412` se capturan tanto errores de expediente/E/S como errores de programación de la llamada, por ejemplo `AttributeError`. **No se silencian sin mensaje**: se llama a `st.error`. No captura `BaseException` como `KeyboardInterrupt`/`SystemExit`. `noqa` sólo afecta al lint.

Como frontera de presentación resulta razonable evitar que un caso roto tumbe el bloque. El límite es diagnóstico: no registra traceback ni distingue falta de permisos de un bug de implementación; el operador ve sólo `str(exc)`. El texto de un `OSError` puede contener una ruta completa. Esto no contamina `solicitud` (que no se genera en esa rama), y la UI ya muestra nombres de casos; no afirmo una fuga al canal de copia por ese camino. Mejorar el diagnóstico técnico y mantener un mensaje apropiado para el operador sería útil, pero no propongo propagar indiscriminadamente los errores de E/S y romper la pestaña.

### C.12 — Restos del camino retirado

El import ejecutable `core.sala_lectura` y el botón `sala_{_caso_sl}` desaparecen del bloque. La búsqueda en todo `streamlit_app.py` sólo encuentra la mención histórica en `:1386`, el import del lector en `:1395` y la clave `casos_sl_sel` en `:1407`, que sigue siendo usada por el selector. No quedan referencias a `detenido_por_residuo` de ese camino, variables de su resultado reutilizadas ni lecturas/escrituras explícitas de una clave huérfana de `session_state`. Los tres imports nuevos se usan. No inspeccioné una sesión de navegador ya abierta para observar la limpieza interna de estados de widgets antiguos.

### D.13 — Estructura plana y artefactos del motor

La afirmación sobre el **contenido actual** de `_directorio_destino` es correcta: `core/sala_lectura.py:781` devuelve `Sala lectura` sin bundle, `:786` devuelve el subdirectorio del compuesto para la cabecera y `:787` su `adjuntos/` para anexos. Ya no introduce carpetas por fuente/categoría. La excepción sigue siendo el documento compuesto, aunque su estructura interna no es idéntica en cada detalle a la ilustración de la skill. El texto del runbook no promete identidad de todos esos detalles.

La procedencia exacta desde PR #328 y las horas de los commits no pueden acreditarse con estos árboles sin `.git`; queda sin verificar. La afirmación de los artefactos necesita H-07 y la de sus escritores H-08. Cuando el motor se detiene por residuo, ni siquiera llega a `render_indices` (`core/sala_lectura.py:1096`); las cifras sobre una sala organizada se refieren al camino que completa la ejecución.

### D.14 — Resto de las afirmaciones documentales

La retirada del botón, la persistencia del CLI (`scripts/sala_lectura.py:207`) y que la skill corre en Cowork/Claude Code están sustentadas por el contenido. La frase del runbook que atribuye al guard la propiedad de «sólo leer» mezcla contratos: un guard de imports no detecta una escritura directa añadida a la UI. Es otro motivo para acotar su garantía conforme a H-04.

Las «unas 30 palabras clave» de `docs/MEJORAS_FUTURAS.md:1163` concuerdan con los **32 tokens** de `_KEYWORDS` (`core/sala_lectura.py:36`), medidos en `sondas_extra3.log`, y el clasificador tiene las ramas de imagen/nombre (`:172` y `:181`). También respeta clasificaciones previas con confianza suficiente (`:170`): no toda pulsación tiene que detenerse por residuo. La cifra **19 de 61** y la frecuencia **«casi siempre»** (`docs/MEJORAS_FUTURAS.md:1164`) no se deducen de esas ramas ni de una única muestra; no dispongo del corpus ni de un registro de ejecuciones que las valide.

La mención a `v1.17` en `docs/RUNBOOK_APERTURA_EXPEDIENTE.md:726` coincide con el metadato de la skill (`SKILL.md:24`) y está expresada como explicación histórica de una frase retirada, no como una nueva instrucción de fijar esa versión. No la considero otro defecto por el mero hecho de contener un número de versión. La limitación de que Paola/Ana no puedan montar desde este expander es exacta en el código; sus permisos reales en Cowork o condiciones externas del DPA no se acreditan con este diff.

## Ejecución, evidencia y reproducción

Intérprete: `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`, Python **3.14.4**; pytest **9.1.1**, pytest-randomly **5.0.0**, pytest-xdist **3.8.0**. `PYTHONDONTWRITEBYTECODE=1` y `-p no:cacheprovider`; temporales relativos que resuelven dentro de `rev/`. No se crearon repositorios Git para simular una genealogía ausente.

Para las sondas, desde `rev/`:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -B auditar.py
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -B auditar_extra.py
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -B auditar_ramas.py
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -B auditar_import.py
```

Los fixtures se crean en subdirectorios nuevos de `probe_data/`. Los hooks, dobles y parches viven en esos procesos, no en los archivos del objeto. Las sondas principales terminaron con `AUDITORIA_FINALIZADA`, `AUDITORIA_EXTRA_FINALIZADA` y `RAMAS_FINALIZADAS`. La primera versión del arnés del motor no fijaba un localizador importado dentro de `inventory.scan` y falló; `sondas_extra.log` conserva ese intento. Tras fijar ese localizador al mismo fixture, la ejecución de `sondas_extra3.log` terminó correctamente. Ningún cambio fue al motor revisado.

Otra limitación del propio arnés está registrada: `permiso_stat_denegado` en `sondas.log` no interceptó la consulta de directorio porque `Path.is_dir` en este Python llama al camino rápido de `os.path.isdir`, no a `Path.stat`. **No uso esa línea como prueba de denegación real.** H-02 usa la inyección verificada en `os.scandir`. La sonda de predicados falsos de `sondas_extra3.log` sólo acredita que la ausencia y una respuesta falsa de los predicados resultan indistinguibles; no demuestra una ACL concreta.

Los dos ficheros nuevos de tests dieron:

```text
25 passed in 5.30s
```

La primera suite completa fue lanzada por error desde `rev/` con `-c obj/pyproject.toml obj/tests`, semilla 777: `21 failed, 5335 passed, 91 skipped, 10 xfailed in 259.41s`. Dieciséis fallos fueron `FileNotFoundError` por tests que usan rutas relativas al cwd; tres exigían Git y dos un `.venv` local inexistente. No atribuyo esos dieciséis al producto. Interrumpí la primera corrida 31337, que tenía el mismo cwd incorrecto, y repetí ambas desde la raíz de sus copias. Se conservan `suite777.log` y `suite31337.log` como evidencia de esos intentos.

La corrida inicial intentó escribir el log auxiliar de `expedientes_xl` en el perfil del usuario y recibió `Permission denied`; el mensaje quedó en `suite777.log`. Las repeticiones fijan `XL_AUDIT_PATH` dentro de `rev/`, además de `CASOS_ROOT` y `FEESDEFENDER_WORKSPACE_REGISTRY` aislados. No se pidió ampliar permisos ni se accedió a expedientes operativos.

Comando de las corridas corregidas (cwd `rev/obj` y `rev/obj2`, respectivamente):

```text
python.exe -B -m pytest -n 4 -p no:cacheprovider -p randomly --randomly-seed=777 --basetemp=../bt777b --tb=short
python.exe -B -m pytest -n 4 -p no:cacheprovider -p randomly --randomly-seed=31337 --basetemp=../bt31337b --tb=short
```

- Semilla **777**, salida **1** (`suite777_correcta.log`):

```text
5 failed, 5351 passed, 91 skipped, 10 xfailed in 316.89s (0:05:16)
```

- Semilla **31337**, salida **1** (`suite31337_correcta.log`):

```text
5 failed, 5351 passed, 91 skipped, 10 xfailed in 320.54s (0:05:20)
```

Ambas corridas ejecutan **5.457 casos** (5 + 5.351 + 91 + 10), sin errores de colección/setup reportados. Los cinco fallos son los mismos en ambas:

| Test en `head` | Causa observada |
|---|---|
| `tests/test_session_close_no_pude_medir.py:161` | `venv_sugerido()` devuelve `None`; falta el `.venv` de la copia. |
| `tests/test_session_close_no_pude_medir.py:137` | Exige un intérprete dentro del `.venv` del repo que aquí no existe. |
| `tests/test_gitignore_no_inerte.py:189` | `git ls-files` devuelve 128: no hay repositorio Git. |
| `tests/test_gitignore_no_inerte.py:155` | La misma ausencia de Git impide obtener los ficheros trackeados. |
| `tests/test_gitignore_no_inerte.py:211` | `git check-ignore` devuelve 128 por la misma causa. |

Los tracebacks completos están en los dos logs. No se ha debilitado, omitido expresamente ni simulado ninguno de esos tests. El total de 5.457 coincide con el anunciado; **no se reproduce el balance anunciado de cero fallos y 94 skipped**: aquí son cinco fallos ambientales, 91 skipped y 10 xfailed. Los 25 casos de los tests nuevos no figuran entre los fallos y quedan incluidos en los aprobados de ambas semillas. La revisión no usa el verde de un test dependiente de Git como evidencia de genealogía: por ejemplo, `tests/test_guard_no_basetemp_versionado.py::_trackeados` no comprueba el código de salida y puede devolver una lista vacía fuera de Git.

## Lo que NO pude verificar

- **Genealogía:** que las copias correspondan realmente a los commits nombrados, el PR #328 y las marcas horarias del runbook. Verifiqué contenido y hashes; no inventé historia Git ni consulté sistemas remotos para sustituir la evidencia congelada.
- **La afirmación de suite enteramente verde del autor:** el conteo recogido es contrastable con las ejecuciones, pero los requisitos de Git y `.venv` no están en estas copias. Los resultados reales se detallan arriba; ningún rojo ambiental se ha convertido artificialmente en verde.
- **Pruebas omitidas/xfail:** NLP/OCR lento, corpus reales ausentes, Ollama no disponible, blocklist no aportada, comprobaciones de despliegue sin rama canónica y los defectos ya marcados `xfail` no quedan validados por esta revisión. Un `xfail` no es un aprobado del comportamiento defectuoso.
- **UI completa en ejecución real:** no arranqué Streamlit ni un navegador, no inspeccioné sesiones existentes ni lancé acciones de otras pestañas. Se ejecutó el bloque nuevo literal con un doble de presentación y se leyó el contexto adyacente.
- **Filesystem de producción:** no ejercí ACL reales de casos, cortes de Drive, sincronización concurrente ni carreras aleatorias. Los enlaces y el atributo Hidden sí se probaron en el filesystem local; el error de enumeración se inyectó y la retirada de directorio se intercaló deliberadamente.
- **Imports generales en ejecución:** el grafo de 71 módulos es estático. El inventario de H-04 queda expresamente fuera de lo que el guard acredita. No he hecho una traza exhaustiva de imports de todas las interacciones de la aplicación.
- **Medición 19/61, frecuencia «casi siempre», decisiones personales y permisos externos:** no hay en el material ejercido una medición reproducible del corpus o del historial de pulsaciones. Las decisiones atribuidas a Nikolai y los accesos reales de Paola/Ana se tratan como contexto declarado, no como hechos observados mediante ejecución.
- **Integridad semántica de una sala:** `c4` sólo comprueba presencia/tipo/tamaño, no que un YAML sea válido ni que los índices correspondan a los documentos. No extendí su OK a esa propiedad. Tampoco presento la igualdad final de hashes como prueba de que sea imposible una escritura transitoria que restaure exactamente los mismos bytes.

## Cierre de custodia

| Fichero en `../head/` | SHA-256 |
|---|---|
| `core/sala_lectura_estado.py` | `e23f5fad7d18ba43dbea681b44aacf1c032cdeefc7ec1f9da256fa21eb1a6213` |
| `tests/test_sala_lectura_estado.py` | `e912818cf16bea3c8f270fe9a4af25245ae6410299686ab58c12aa27dad10cbd` |
| `tests/test_guard_ui_sin_deprecados.py` | `da45a77e027d14c9927d82ad4cb29a0155081c05f626371d56bdab8a6f2f997c` |
| `streamlit_app.py` | `e0968ccbc16a3bccc278563e41bbc3351855ecf3e8d85bfc5a95b916c5d8ad90` |
| `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` | `bbfcefef4fe96252b201c5a6b3473a23fb754166bc7d598748e876e07b109b73` |
| `docs/MEJORAS_FUTURAS.md` | `1ea4c6e35784858092156530c78a01e5cde0f1644e9894cf701247da716f3315` |

**Los seis hashes de cierre coinciden con los de apertura.** También recomputé el manifiesto completo de ficheros de ambos árboles: `base`, 1317 ficheros; `head`, 1320 ficheros; cero altas, bajas o cambios de bytes respecto a la apertura (`custodia_cierre.json`). Esta comprobación no sella metadatos ni demuestra ausencia de escrituras transitorias restauradas.

La recomendación de no integrar se fundamenta en H-01, un fallo del flujo normal anunciado al operador. H-02 a H-05 afectan a la fiabilidad del estado y de sus instrumentos; H-06 a H-09 precisan límites y afirmaciones. La retirada del botón sí elimina el import directo deprecado, y no encontré una escritura de expediente en el lector actual ni una fuga de dirección desde su productor real de evidencia.

NO-SHIP
<!-- informe-literal:fin:qz7v -->

## 2. Evidencia verificada por mí al adjudicar

Cada hallazgo se contrastó **contra la fuente**, no contra el informe.

- **H-01 (ALTO).** Confirmado, y lo había empezado a ver por mi cuenta mientras la ronda
  corría. Dos pruebas independientes en el propio repo: `SKILL.md` §estructura pone los
  cuatro artefactos juntos dentro de `Sala lectura/`, y `verificar_sala.py` —el verificador
  **de la skill**— excluye `indice_documental.yaml` al contar documentos, o sea **asume** que
  vive ahí. `verificar_apertura.py` lo buscaba solo en `01_Procesado/`.
- **H-02 (MEDIO).** Confirmado. `Path.rglob` no propaga los errores de exploración; el
  recuento no distinguía «cero» de «no pude enumerar».
- **H-03 (MEDIO).** Confirmado por su control positivo, que es la prueba que yo no hice. Mi
  `M7` mataba el mutante del `mkdir`, pero lo mataban **otros** tests, no el sello: el sello
  daba verde. Una guarda que nunca se ha visto morder no acredita nada.
- **H-04 (MEDIO).** Confirmado. Mi docstring prometía «la UI no importa módulos deprecados» y
  lo que el guard comprueba son los imports **estáticos y literales de un fichero**. El
  inventario de once familias que devolvió es correcto y se transcribe entero.
- **H-05 (MEDIO).** Confirmado en su mitad dura: en Windows `INDICE.md` e `indice.md` son el
  mismo fichero, así que `c4` lo veía como artefacto y el recuento lo sumaba como documento —
  los dos números de la misma pantalla discrepando sobre los mismos bytes. Lo demás
  (auxiliares, vacíos, enlaces) se **declara** en la docstring en vez de filtrarse a ciegas:
  un fichero oculto puede ser prueba válida.
- **H-06 (BAJO).** Confirmado contra `PathFinder`: Python prefiere el paquete y yo miraba el
  fichero. No hay colisión así en `core/` hoy.
- **H-07 (BAJO).** Confirmado leyendo `catalogo_documental.save_catalog`: el motor escribe
  **tres** de los cuatro —los dos índices y el catálogo en el padre—. «Dos de los cuatro» era
  el conteo *dentro de la sala*, y yo lo escribí sin esa mitad, mezclando dos inventarios.
- **H-08 (BAJO).** Confirmado: `scripts/redate_whatsapp_anexos.py:150` hace
  `manifiesto.write_text(...)`. Mi frase «no lo escribe **nadie**» es literalmente falsa; lo
  cierto es que no hay **generador**, y reescribir lo que ya existe es otra cosa.
- **H-09 (BAJO).** Confirmado por lectura. El aserto siempre fue correcto; el nombre mentía.

**Lo que el revisor NO pudo verificar, y por tanto queda sin verificar —no refutado:** la
genealogía (las copias no llevan `.git`, así que la atribución a `f1759cf`/`c133108` y las
marcas horarias del PR #328 son del mandato, no acreditadas por él); la suite enteramente
verde (su entorno carece de `.venv` y `git`); la UI arrancada de verdad; ACL reales de Drive;
y **las cifras 19/61 y «casi siempre»**, que él señala expresamente como no reproducibles con
el material entregado. Esa última es mía y la asumo: viene de la bitácora del 2026-06-18
sobre un caso real, no de una medición repetida en esta sesión.
