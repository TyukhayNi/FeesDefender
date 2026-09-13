---
tipo: handoff
estado: activo
creado: 2026-09-13
origen: sesión remota de Claude Code (contenedor Linux, sin Windows, sin `G:`/`H:`, sin rclone, sin CRM, sin OCR). Decisión de Nikolai del 2026-09-13 al cerrar la fila #28: el siguiente paso del plan de «apertura con menos decisiones» es **P3**, y su mitad sin gates es la fila #27
destino: la sesión LOCAL de Claude Code que continúe la fila #27 por la pieza A
rama: `claude/trusting-mayer-9fe7lg`
---

# Handoff — Fila #27 (`MEJORAS #214` + `#215`): pieza B cerrada, pieza A diseñada y sin construir

**Andamio efímero, no fuente de verdad** (`GOBERNANZA_FUENTES_VERDAD §5`). El estado de ciclo de
vida del ítem vive en `PLAN.md` fila #27; aquí solo va lo que la sesión local necesita para no
volver a derivar lo ya medido.

## 0. Por qué esta fila y no otra

La fila #28 (P5 + P7 + P2 del handoff del 2026-09-10) cerró en el 113º. El orden recomendado de
aquel handoff (§6) es **P5/P7 → P2 → P3 → P4 → P6 → P1**, y P3 es «la capa base antes que
cualquier V2». De las tres entradas de P3, `#214` y `#215` ya estaban promovidas como **fila #27**
con disparador consumado y **sin gates**; `#225` sigue esperando una decisión de Nikolai. P4 espera
`[APER-70]`. Así que la fila #27 es lo único de P3 construible hoy.

## 1. Estado

| Pieza | Estado | Dónde |
|---|---|---|
| **B — sniff de contenedores (`MEJORAS #215`)** | ✅ **construida y verde** | `core/sala_maquina.py`; `tests/test_sala_maquina_sniff_contenedores.py` (16 tests, 2 mutantes) |
| **A — recorrido tolerante y reconciliación (`MEJORAS #214`)** | ❌ **sin construir**, diseño cerrado en el §3 | `scripts/abrir_caso.py::hash_tree_local` |
| Ronda adversarial (1, sobre el diff) | ❌ **no corrida** | radio de daño: la pieza lee y clasifica; no decide quién escribe ni destruye datos |

**El verde de esta rama NO es el verde de la casa, y eso hay que medirlo en local.** Este
contenedor es Linux sin `.venv`, sin `cmd`, sin `G:`/`H:` y sin las dependencias de sistema: la
suite trae **rojos preexistentes de plataforma** (ya medido en el 88º cierre) y `session_close`
devuelve código 2 (medido en el 106º). Lo que esta sesión acredita es el **delta contra la base**,
no el «0 fallos». La verja con las dos semillas (777 y 31337) está **pendiente** y es tuya.

## 2. Lo que la pieza B cambió, y las dos correcciones que hubo que hacer a la prosa

`_sniff_ext_por_contenido` pasa de recibir 16 bytes a recibir la **ruta**, porque un contenedor no
se puede decidir en la cabecera: `PK\x03\x04` cubre `.docx`, `.xlsx`, `.pptx`, todo ODF y un `.zip`
cualquiera. Se abre el índice y se pregunta al paquete qué dice ser (`word/document.xml`,
`xl/workbook.xml`, `ppt/presentation.xml`, o el `mimetype` de ODF, leído **acotado** a 128 bytes
porque lo escribe un fichero de fuera).

**Corrección 1 — el plan y `MEJORAS #215` dicen que un `.docx` debe llegar a la ruta `ofimatica`, y
es falso.** `clasificar_ruta` manda `.docx` y `.xlsx` a `nativo`, que tiene extractor determinista
propio (`_try_docx`), y su docstring explica que cambiarles la ruta cambiaría el MD de casos ya
hechos. Lo que cierra `#215` es sacarlos de `sin_soporte`, no llevarlos a `ofimatica`. Los tests
están escritos contra la fuente, no contra el plan.

**Corrección 2 — `#215` le quitó la premisa a la regla 2 del titular de duplicados, y lo destapó un
rojo.** `_marcar_duplicados` documenta su regla 2 con este ejemplo: «un DOCX guardado sin extensión
es `sin_soporte`, su copia `.docx` es `nativo`». Con el sniff nuevo las **dos** copias saben
extraer, así que decide la regla 3 (la primera por ruta) y `test_d9_el_titular_es_quien_sabe_
extraer_no_el_primero` se puso rojo. **No se relajó el aserto**: se cambió el *ejemplar* a un RTF
—cuyo `{\rtf1` no es firma mágica reconocible, así que sin extensión sigue siendo `sin_soporte`— de
modo que la regla 2 vuelve a tener un caso que la ejercite, y el mundo nuevo del DOCX se contrató
aparte en `test_d9c_…`. El docstring de la regla 2 dice ahora de dónde viene el cambio.

Lo que **no** cambia: `.ods` y `.zip` se reconocen y siguen siendo `sin_soporte` —el sniff nombra,
`clasificar_ruta` decide—; la diferencia es que la ficha de cobertura los nombra en vez de dejar el
hueco. Y una cabecera `PK` que no se deja abrir devuelve `None`, no `.zip`: **no poder mirar no es
haber visto**.

## 3. Pieza A — el diseño, ya medido. No hace falta volver a derivarlo

### 3.1. La restricción que condiciona todo: `hash_tree_local` NO se puede mover a `core/`

Parece lo correcto (`CLAUDE.md`: «la lógica vive en el core») y **rompe un guard**.
`tests/test_abrir_caso_exit_bajo_mutex.py::cierre_bajo_mutex` recorre el AST de
`scripts/abrir_caso.py` y calcula el cierre transitivo de **funciones definidas en ese módulo**
alcanzadas desde el bloque del mutex; `test_el_cierre_derivado_no_esta_vacio_ni_es_trivial` exige
literalmente que `hash_tree_local` esté entre las alcanzadas. Moverla la sacaría del cierre y
obligaría a debilitar el guard, que es justo lo que la casa prohíbe. **Se queda donde está.** Los
tipos nuevos sí van a `core/abrir_caso.py`, junto a `Reconciliacion`, que ya es custodia.

### 3.2. Forma propuesta

```python
# core/abrir_caso.py, junto a Reconciliacion
@dataclass(frozen=True)
class FicheroSinVerificar:
    clave: str      # "01_Drive EV/…", tal como se listó
    motivo: str     # por qué no se pudo leer

@dataclass(frozen=True)
class ArbolLocal:
    hashes: dict[str, str]
    sin_verificar: tuple[FicheroSinVerificar, ...] = ()
    renombrados: tuple[tuple[str, str], ...] = ()   # (clave listada, clave efectiva)
```

`hash_tree_local(root, *, prefijo) -> ArbolLocal`, con tres cambios:

1. **Enumeración que no se traga los errores.** `rglob` los **suprime**: una carpeta irrecorrible
   devuelve «cero ficheros». Es exactamente la clase H-04 que la R1 de `verificar_apertura` ya midió
   el 2026-09-11. Usar `os.walk(root, onerror=…)` y convertir cada error de directorio en un
   `FicheroSinVerificar`.
2. **Lectura tolerante por fichero.** `file_sha256(p)` dentro de `try`:
   - `FileNotFoundError` → el montaje lo renombró entre el listado y la apertura. **Relee el
     directorio** y busca un candidato `q` en `p.parent` tal que `q.stem == p.name` (o sea, el mismo
     nombre **más** una extensión, que es lo que hace Drive for Desktop) y cuya clave **no estuviera
     en el listado original**. Exactamente uno → se hashea bajo su clave **efectiva** y se anota en
     `renombrados`. Cero o dos o más → `sin_verificar` con el motivo; la ambigüedad no se resuelve
     adivinando.
   - Cualquier otro `OSError` → `sin_verificar` con el motivo. **Nunca un hash ausente en silencio:
     un fichero que no se pudo leer no ha medido cero.**
   - Volver a comprobar `es_fichero_de_protocolo` sobre la clave efectiva.
3. **La declaración viaja hasta el estado de V1.** `_intake_generico` recibe `sin_verificar`, lo
   imprime y lo mete en los `details` del evento forense (`count` cuenta solo lo verificado, así que
   sin esa lista el registro se leería como «todo cuadró»). `DriveIntakeResult` gana un campo
   `sin_verificar` para que `etapa_drive` lo convierta en `Pendiente(codigo="custodia_sin_verificar")`.
   **La etapa no se tumba** — es lo que el plan pide explícitamente.

### 3.3. `reconcile` cuadra consigo mismo: confirmado leyendo el código

`_inventario_desde_hashes` construye el inventario **desde los mismos `hashes`** que luego se le
pasan a `reconcile`, y `esperados_en_disco` sale de `plan.items`. Para `drive_ev`, por tanto,
`extras` es **siempre vacío**: no puede ver una copia de más. El plan lo decía y es literal.

**Remedio propuesto, sin cambiar la semántica de `ok`:** `Reconciliacion` gana
`sin_verificar: tuple[...]` y una propiedad `completa = ok and not sin_verificar`. `ok` sigue
significando «lo depositado cuadra con el plan», así que ningún llamador cambia de comportamiento;
`_intake_generico` sigue abortando solo con `not ok` y **declara** los `sin_verificar` sin abortar.

### 3.4. El punto 2 del plan («reconciliación contra el remoto») ya está construido — no lo dupliques

`core/verificar_apertura.py::c1_censo_remoto` compara **multiconjuntos** del censo remoto contra los
ficheros de `01_Drive EV` y reporta `sobran_en_local`: eso **es** ver la copia de más, y su docstring
cita el mismo `[APER-65]` («11 de 58 renombrados, 7 duplicados»). `c2_hash_contra_drive` cubre el
hash contra el `sha256Checksum`. Las dos se construyeron el 2026-09-11 (fila #28, P2).

**Decisión propuesta, para que quede por escrito en vez de duplicarse:** la detección contra el
remoto se declara **cubierta por P2** y no se mete red dentro del pull. Lo que sí falta —y es lo que
la pieza A añade— es que el pull deje de **mentir por omisión** sobre lo que no pudo leer. Si al
construirlo decides lo contrario, hazlo explícito: meter red en el camino del intake cambia el modo
por defecto y necesita su propio puerto cerrado, como el `SinRed` de P2.

### 3.5. El punto 3 («persistir el mapa junto al `.pulled`») es diferible, y además su premisa cojea

El plan lo justifica «para que la ronda siguiente no vuelva a pedir lo que ya está bajo otro
nombre». Pero hoy **no elegimos qué pedir**: `pull_drive_ev` lanza `rclone copy` sobre la carpeta
entera y es rclone quien compara contra el montaje. Un mapa junto al `.pulled` no cambia eso por sí
solo — haría falta `--files-from`, o una poda posterior al pull contra el censo remoto. Déjalo
fuera de este PR y anótalo con esa corrección.

### 3.6. El listón de los tests que fija el plan, y que es lo que impide que esto quede en verde sin probar nada

- Un fichero que **cambia de nombre entre el listado y la apertura** → tiene que hashearse, bajo la
  clave efectiva, y aparecer en `renombrados`.
- Un fichero que **desaparece de verdad** → tiene que salir declarado como no verificado.
  **Si solo se prueba el primero, el remedio se convierte en «tragarse el error».**
- Añade los dos que el diseño abre: **dos candidatos** al renombrado (ambigüedad → `sin_verificar`,
  no se elige uno) y **un directorio irrecorrible** (`onerror` → `sin_verificar`, no «cero
  ficheros»).
- Y el control positivo de la declaración: un `sin_verificar` no vacío tiene que llegar al **evento
  forense** y al `Pendiente` de la etapa. Un mutante que lo tire por el camino debe morir.

La carrera se monta en `tmp_path` parcheando la lectura para que renombre en el momento exacto (el
árbol sintético del patrón `test_guard_localizador.py::_arbol_sintetico`). **El fenómeno real —el
montaje de Drive for Desktop renombrando— no se reproduce ni en Linux ni sin `G:`**: eso solo se
comprueba en una apertura real, y hasta entonces queda declarado como no verificado.

## 3.7. La misma frontera sigue abierta en la otra sala, y conviene verlo antes de cerrar la fila

`CLAUDE.md` manda preguntar «¿de qué frontera es esto un ejemplo?» **antes** de remediar, porque es
lo que ahorró rondas en el mutex. La frontera de la pieza B es **«el tipo de un documento lo dicen
sus bytes, no su nombre»**, y la pieza B la cierra solo en la **sala de máquina**.

En la **sala de lectura** sigue abierta, y está medida: `core/inventory.py:95` descarta a `skipped`
todo lo que no case `_RELEVANT_EXTS`, comparando `path.suffix.lower()` — o sea, el **nombre**. Un
fichero sin extensión desaparece del catálogo aunque la sala de máquina ya sepa qué es y le haya
escrito espejo. Eso es `MEJORAS #190` (`[APER-60]`), con dos mediciones: **4 documentos reales** del
Drive de E&V el 2026-09-09 (un certificado municipal de tributos y tres de suministros, todos con
texto útil) y, en W-02O7E2, **los cuatro DNI de quien firmó el encargo y un vídeo**.

**No se ha construido aquí y no hace falta un número nuevo:** `#190` ya existe con su medición. Lo
que esta sesión aporta es que ahora hay una pieza de la que colgarlo —`_sniff_ext_por_contenido`
recibe una ruta y responde por contenido— así que el remedio de `#190` deja de ser «escribir un
detector» y pasa a ser «llamar al que ya hay». Decidirlo es de Nikolai: cabe en esta fila como
pieza C o va aparte.

## 4. Cabos que esta sesión deja atados y sueltos

- **Atado:** el diff de la pieza B, sus 16 tests y el re-premisado de D9 + D9c.
- **Suelto y tuyo:** la pieza A; la **ronda adversarial** (una, sobre el diff completo de la fila);
  la verja de `session_close` con las dos semillas; marcar `[PROMOVIDO]`/`✅` en `PLAN.md` fila #27 y
  en `MEJORAS #214`/`#215` con el hash del PR.
- **Suelto y de Nikolai**, las tres decisiones del §6 del handoff del 2026-09-10, que siguen
  abiertas y que él pidió el 2026-09-13 resolver: `#225` (histórico del relleno con ceros),
  `[APER-70]` (qué constructor de la sala sobrevive) y P8 (una sesión, N aperturas).

## 5. Lo que este handoff no hace

No reserva números de `MEJORAS` (se cogen al escribir, releyendo `main`), no toca `PLAN.md` —la
promoción y el cierre de la fila son de su hogar autoritativo— y no declara ninguna cobertura de
revisión: la ronda adversarial de la fila #27 **no se ha corrido**, y hasta que corra la cobertura
está **ausente**, no refutada.
