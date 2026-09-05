---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "MEJORAS #149 — los ficheros de protocolo se identifican por nombre a cualquier profundidad; el contrato es por ubicación"
rev: "1"
---

# Ficheros de protocolo: por dónde están, no por cómo se llaman

> **Rev. 1 (2026-09-05).** Diseño para cerrar `MEJORAS #149` **sin repetir el 2026-09-04**: aquel
> día se declararon cuatro nombres más en `INTAKE_CONTROL_FILES` y la R1 adversarial lo tumbó con
> un hallazgo CRÍTICO (una migración que borra un adjunto legítimo homónimo) y dos ALTOS; se
> revirtió entero (`4cd71dd`). La causa estaba escrita en la propia entrada: **el contrato es por
> ubicación, no por nombre**, y se implementó solo la mitad del nombre. Origen inmediato: acción 7
> del informe de Codex «Acciones para mejorar el alta de expedientes» (2026-09-05, fuera del repo).

## 1. El problema, medido

`core/config.INTAKE_CONTROL_FILES` es un **conjunto de basenames** (`.pulled`, `.synced`,
`_inventory.json`, `_exported_ids.json`, `_resolved_links.json`, `_apertura_v1.json`) y siete
consumidores lo aplican **a cualquier profundidad** de `00_Input/`:

| Consumidor | Cómo excluye | Efecto medido o demostrado |
|---|---|---|
| `core/inventory.scan` | `path.name in _CONTROL_FILES` y `path.name.startswith("_caso")`, sobre `rglob` | un adjunto llamado `_inventory.json` en un lote desaparece del inventario |
| `core/intake_manual` (`_listar`, `list_files`) | `p.name not in _CONTROL_FILES` | ídem |
| `core/intake_drive.pull_drive_ev` (recuento) | `p.name not in CONTROL_FILES` | ídem |
| `core/intake_lotes.items_desde_disco` | `p.name in INTAKE_CONTROL_FILES or p.name == MANIFIESTO_LOTE`, sobre `rglob` | **R1 2026-09-04, ALTO:** un adjunto `_manifiesto.yaml` anidado desaparece del albarán forense del lote |
| `core/email_export.export_label` | igual, para decidir si el lote quedó vacío | ídem |
| `core/sala_maquina._es_control(nombre)` | nombre ∈ registro ∪ `{_intake_log.jsonl}` o prefijo `.apertura_v1.` | la asimetría de `#149`: lo **declarado** se excluye bien y lo **no declarado** entra en `_cobertura` como `sin_soporte` (`_intake_hashes.json`, `<lote>/_manifiesto.yaml`, medido en W-02JSVZ) |
| `scripts/migrar_layout_intake` | `hijo.name in INTAKE_CONTROL_FILES` bajo `03_Email/` → mover a la raíz; si ya hay uno, **`unlink()` sin comparar bytes** | **R1 2026-09-04, CRÍTICO:** con `_ficha_crm.yaml` declarado, un adjunto legítimo así llamado se trata como estado de canal y se **borra**; **ALTO:** el homónimo anidado se mueve fuera del `mapping` M9 y sus referencias forenses quedan rancias |

Y el lado contrario del mismo defecto: cuatro ficheros que **el propio repo escribe** en `00_Input/`
no están en el registro y salen en la red de calidad como documentos sin soporte:

| Fichero | Quién lo escribe | Dónde |
|---|---|---|
| `_intake_hashes.json` | `core/intake_manifest` | `00_Input/` |
| `_manifiesto.yaml` | `core/intake_lotes` (vía `email_export`, `whatsapp_intake`, `intake_manual`, `migrar_layout_intake`) | raíz de **cada lote** |
| `_ficha_crm.yaml` | a mano, §9 del runbook | `00_Input/` |
| `_ocurrencias_crm.json` | `core/ocurrencias_crm` (`REGISTRO_REL = "00_Input/_ocurrencias_crm.json"`) | `00_Input/` |

Declararlos por nombre reproduce el CRÍTICO. No declararlos deja la red de calidad con ruido en el
sitio exacto donde se mira lo que el OCR no pudo leer.

## 2. La frontera

**Un fichero es de protocolo por dónde está, no por cómo se llama.** El repo escribe cada uno en
una ubicación que él mismo fija; un homónimo en cualquier otro sitio es un documento del cliente y
se conserva, se inventaría y se hashea como tal. El registro pasa de «nombres» a **«nombre en
ubicación»**, y los consumidores dejan de preguntar por el basename para preguntar por la ruta
relativa a `00_Input/`.

Y es un contrato **para clasificar**, no para borrar: nada de lo que esta pieza toca borra un
fichero sin haber demostrado antes, por hash, que es idéntico a otro que se conserva.

## 3. Diseño

### 3.1. El registro, por ubicación (`core/config.py`)

```python
#: Protocolo en la RAÍZ de `00_Input/` (profundidad 1). Escritores: case_manager, intake_log,
#: intake_manifest, inventory, email_export (estado de canal), apertura_v1_estado, ocurrencias_crm,
#: y el letrado (`_ficha_crm.yaml`, §9 del runbook).
INTAKE_CONTROL_RAIZ: frozenset[str] = frozenset({
    "_caso.md", "_intake_log.jsonl", "_intake_hashes.json", "_inventory.json",
    "_exported_ids.json", "_resolved_links.json", "_apertura_v1.json",
    "_ficha_crm.yaml", "_ocurrencias_crm.json",
})
#: Temporales de escritura atómica en la raíz: un huérfano tampoco es documento.
INTAKE_CONTROL_RAIZ_PREFIJOS: tuple[str, ...] = (".apertura_v1.", "._caso.")
#: Protocolo en la raíz de una ENTREGA de primer nivel (profundidad 2): un lote
#: `AAAA-MM-DD_<fuente>_NN/`, `01_Drive EV/`, `sudespacho_<id>/` o un cajón legacy.
INTAKE_CONTROL_ENTREGA: frozenset[str] = frozenset({"_manifiesto.yaml", ".pulled", ".synced"})
```

`INTAKE_CONTROL_FILES` **se conserva** como la unión de nombres —lo espejan `MERGE_EXCLUSIONS`,
el carve-out del plugin y `tests/test_apertura_v1_control_files.py`, que son contratos por
basename de otra capa (el checkin y el MCP)— pero **ningún consumidor de `00_Input/` vuelve a
clasificar con él**. Su comentario lo dice.

### 3.2. Una sola pregunta: `es_fichero_de_protocolo(rel_path)`

Nuevo `core/intake_control.py`, sin más dependencias que `config`:

```python
def es_fichero_de_protocolo(rel_path: str) -> bool:
    """`rel_path` relativo a `00_Input/`, con `/` o `\\`. Profundidad 1: nombre en
    INTAKE_CONTROL_RAIZ o prefijo en INTAKE_CONTROL_RAIZ_PREFIJOS. Profundidad 2: nombre en
    INTAKE_CONTROL_ENTREGA. Cualquier otra profundidad: documento."""
```

Sin `..`, sin rutas absolutas: si `rel_path` no es relativa y normalizada, `False` (es un
documento en un sitio raro, que es preferible inventariar a esconder). Las dos únicas
profundidades son las que los escritores usan de verdad; una tercera **no se admite** hasta que un
escritor la necesite, para no volver a ensanchar el contrato por anticipación.

### 3.3. Los siete consumidores preguntan por la ruta

| Consumidor | Cambio |
|---|---|
| `inventory.scan` | `es_fichero_de_protocolo(path.relative_to(input_dir))`; desaparece el `startswith("_caso")` (`_caso.md` y `._caso.*` están en el registro) |
| `intake_manual` (`_listar`, `list_files`) | ídem, con la ruta relativa a `00_Input/` |
| `intake_drive.pull_drive_ev` | ídem: la ruta relativa es `01_Drive EV/<…>`, así que `01_Drive EV/.pulled` se excluye y `01_Drive EV/OFERTAS/.algo` **no** (las carpetas de E&V traen nombres con punto inicial, el propio módulo lo documenta) |
| `intake_lotes.items_desde_disco` | `es_fichero_de_protocolo(f"{lote_dir.name}/{rel}")`: solo el `_manifiesto.yaml` **de la raíz del lote** queda fuera del albarán |
| `email_export.export_label` | ídem para decidir si el lote quedó vacío |
| `sala_maquina._es_control(rel)` | la firma pasa de nombre a ruta relativa; `inventariar_cacheado` ya la calcula. `_IGNORAR` desaparece: `_intake_log.jsonl` está en el registro |
| `migrar_layout_intake` | §3.4 |

### 3.4. La migración no borra lo que no ha comparado

`scripts/migrar_layout_intake.py` mueve los cajones legacy (`03_Email/` …) a lotes. Dos de los
ficheros del cajón `03_Email/` son **estado de canal** cuyo hogar desde `MEJORAS #54` es la raíz:
`_exported_ids.json` y `_resolved_links.json`, **solo directamente bajo `03_Email/`** (profundidad
2 desde `00_Input/`). Reglas:

1. Se identifican por **ubicación y nombre**, no por pertenencia a `INTAKE_CONTROL_FILES`: un
   `03_Email/hilo/_exported_ids.json` es un adjunto, se mueve al lote con todo lo demás y **entra
   en el `mapping` M9** (cierra el ALTO del homónimo anidado).
2. Si la raíz **no** tiene el fichero → se mueve (como hoy).
3. Si la raíz **ya** lo tiene → se comparan por `sha256`. **Idénticos** → el anidado se borra en la
   fase 2 (como hoy, pero ahora es demostrable que no se pierde nada). **Distintos** → la
   migración **aborta en tiempo de plan**, antes de mover nada, nombrando los dos ficheros: son
   dos estados de canal de momentos distintos y decidir cuál vale es del operador. Fallar cerrado,
   como manda la casa.

`_mapping_documental` aplica la misma regla de ubicación.

### 3.5. Lo que no se toca, y por qué

- `core/crm_ficha_validacion.es_fichero_de_control(rel)` clasifica **filas de `_cobertura`**, otra
  capa; con el §3.3 esas filas ya no traerán protocolo, así que su lista por nombre se vuelve
  redundante pero inofensiva. Se deja como está (es territorio de la ficha CRM, en obra en otra
  sesión) y se anota en su docstring.
- `MERGE_EXCLUSIONS` y `plugins/expedientes_xl/tiers.PROTOCOL_*` son patrones por basename **del
  checkin y del MCP**, con sus propios guards; no cambian.
- No se migra ningún `_cobertura`, inventario ni manifiesto existente: el siguiente `apply` o
  `scan` los regenera con el contrato nuevo.

## 4. Radio de daño y rondas

La pieza decide **qué es prueba documental** en el inventario y en la red de calidad, y toca el
único `unlink()` del intake. Por la regla del 2026-08-26, **dos rondas**: esta sobre el diseño y
otra sobre el diff. Codex sin cupo → revisor sustituto de `AGENTS.md`, independencia declarada
más débil.

## 5. Mutantes

`tests/test_intake_control_por_ubicacion.py` (nuevo) y ampliaciones de `test_intake_lotes.py`,
`test_inventory.py`, `test_migrar_layout.py`, `test_apertura_v1_control_files.py`. Los **(+)**
son positivos.

| # | Mutante | Qué debe pasar |
|---|---|---|
| T1 | `<lote>/adjuntos/_ficha_crm.yaml` (adjunto homónimo) | está en el inventario de `inventory.scan`, en el albarán del lote y en el inventario de la sala de máquina; `00_Input/_ficha_crm.yaml` en ninguno |
| T2 | `<lote>/_manifiesto.yaml` vs `<lote>/x/_manifiesto.yaml` | el primero fuera del albarán y del inventario; el segundo dentro |
| T3 | caso con lote de correo, `_intake_hashes.json`, `_ficha_crm.yaml` y `_ocurrencias_crm.json` en la raíz | `inventariar` de la sala de máquina no devuelve **ninguna** fila cuyo `rel_path` sea de protocolo; hoy devuelve dos (la medición de `#149`) |
| T4 | migración con `03_Email/_exported_ids.json` **idéntico** al de la raíz | fase 2 lo borra; el de la raíz sigue |
| T5 | migración con `03_Email/_exported_ids.json` **distinto** del de la raíz | aborta **antes** de mover nada; `00_Input/` queda byte a byte como estaba; el mensaje nombra los dos |
| T6 | migración con `03_Email/hilo/_exported_ids.json` (homónimo anidado) | se mueve al lote **y** aparece en el `mapping` con el que se remapea `_intake_hashes.json` |
| T7 | guard de familia: cada literal que un módulo del repo escribe en `00_Input/` | está en el registro **en la ubicación que su escritor usa** (raíz o entrega) |
| T8 (+) | `01_Drive EV/.pulled`, `sudespacho_648/.pulled`, `01_Drive EV/.synced` | protocolo |
| T9 (+) | `01_Drive EV/OFERTAS/.pulled`, `01_Drive EV/.Oferta firmada.pdf` | documento |
| T10 (+) | `_caso.md`, `._caso.4242.tmp`, `.apertura_v1.x.tmp` en la raíz | protocolo; los mismos nombres a profundidad 3, documento |
| T11 | `es_fichero_de_protocolo("../_caso.md")`, `("C:/x/_caso.md")`, `("")` | `False` los tres |
| T12 (+) | los tests hoy verdes de `test_intake_lotes`, `test_inventory`, `test_migrar_layout`, `test_email_export`, `test_intake_drive`, `test_sala_maquina*` | siguen verdes: el contrato nuevo coincide con el viejo en todo lo que el viejo hacía bien |

## 6. Alcance explícito

- **Toca:** `core/config.py` (registro), `core/intake_control.py` (nuevo), los siete consumidores
  del §3.3 y §3.4, tests. Cierra `MEJORAS #149` y declara `#54 T1` (la «lista única») como
  sustituida por el registro por ubicación.
- **No toca:** `crm_ficha_validacion`, `MERGE_EXCLUSIONS`, el plugin, ni ningún artefacto ya
  escrito en un expediente.
- **No cubre:** la deduplicación de documentos (`#147`), ni qué hacer con un fichero de protocolo
  **corrupto**: eso lo detecta quien lo lee, no quien lo clasifica.
