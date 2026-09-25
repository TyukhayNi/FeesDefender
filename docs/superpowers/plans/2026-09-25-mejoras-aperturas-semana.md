# Mejoras de las aperturas de la semana (2026-09-15 → 2026-09-25) — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** cerrar los defectos medidos en las aperturas de las dos últimas semanas que hacen que una
apertura **pierda material sin avisar** o que su verificador **calle lo que ya sabe**, más el que
tumba toda corrida V1 contra `G:`.

**Architecture:** cuatro piezas independientes sobre módulos que ya existen, sin módulo nuevo:
`core/whatsapp_export.py` (una regla de «fichero de chat» y la normalización de referencias),
sus tres consumidores (intake, manifiesto, atomizador), `core/verificar_apertura.py` (C2, C3, C9)
y `core/viabilidad_json.py` (la publicación del JSON). Una rama y un PR; dos rondas Codex sobre
dos tramos de commits, porque las dos piezas caen en filas distintas de la tabla de modelos.

**Tech Stack:** Python 3.14, pytest (+ xdist), el venv de la raíz (`C:\Users\tnm33\Dev\FeesDefender\.venv`).

## Global Constraints

- Ningún veredicto de `verificar_apertura` se ablanda: **se explica, no se aprueba**. Un `fallo`
  sigue siendo `fallo`; lo que cambia es que el `detalle` y la `evidencia` digan lo que la función
  ya calcula.
- La custodia antes que el parser: el intake de WhatsApp **no deja de depositar** un export por no
  saber interpretarlo.
- `_viabilidad.json` **nunca se pisa**. Si una garantía se degrada en un filesystem, se declara en
  el docstring y en el mensaje, nunca en silencio.
- No se toca nada de Codicert F3 (sesión en paralelo, autorizado así por Nikolai el 2026-09-25):
  `core/codicert*`, `core/expedicion_certificada.py`, `core/certificado_lectura.py`,
  `core/sudespacho_documentos.py`, `scripts/codicert.py`, fila #37 de `PLAN.md`, `MEJORAS #286`.
- Numeración nueva del backlog desde **#287** (el #286 lo reserva la rama de Codicert F3).
- Tests en `tmp_path`; ningún test escribe en el árbol de producción
  (`tests/test_guard_aislamiento_paralelo.py`).
- Aceptación: suite completa con dos semillas (`python -m scripts.session_close`).

## Origen: qué se leyó y qué se decidió

Siete notas de `%LOCALAPPDATA%\FeesDefender\aperturas\` (W-02JSVZ, W-02SRFU, W-030A13, W-0462E1 ×2,
W-02UIQU, PARTICULAR-659), cruzadas con `docs/MEJORAS_FUTURAS.md` y con el código de `origin/main`
en `9880165`. Decisiones de Nikolai del 2026-09-25: el segundo hueco de código es `#276` (no
`crm_ficha`); se autorizan cerrar el PR #387, fichar la nota de PARTICULAR-659 y anotar la de
W-02UIQU; esta sesión trabaja en paralelo a Codicert F3 sin tocar lo suyo.

**Discrepancia que abrió el bloque 0.** La nota de W-030A13 figuraba `fichado [275-279]`, pero en
`main` esos cinco números son otras entradas: sus cinco defectos solo vivían en el PR #387, abierto
y en conflicto desde el 2026-09-16. Tres ya estaban en `main` con otro número (`#276`, `#268` y la
causa de C9 en `#218`); dos no estaban en ningún sitio (C3 con bundles partidos, y la verificación
de `crm_ficha` por inclusión). `session_close` no avisaba porque la nota decía `fichado`.

## File Structure

| Fichero | Qué cambia |
|---|---|
| `docs/MEJORAS_FUTURAS.md` | #287, #288 (rescatadas del PR #387), #289-#291 (PARTICULAR-659); datos nuevos en #218, #236, #237, #276, #285; cierres |
| `core/whatsapp_export.py` | `_limpiar_ref` (marcas invisibles) en `_adjunto_ref`; `CHAT_TXT` y `elegir_chat` (la regla única) |
| `core/whatsapp_intake.py` | `_find_chat_txt` usa `elegir_chat`; el chat se registra como `tipo_contenido: whatsapp` aunque no se llame `_chat.txt` |
| `core/whatsapp_atomize/pipeline.py` | `chat_txt_de`; `descubrir_chats` y `_leer_media` por la regla única |
| `core/whatsapp_atomize/propuesta_identidades.py` | lee el chat por `chat_txt_de` |
| `core/verificar_apertura.py` | C2 dice cuántas discrepancias explica el relleno; C3 busca el catálogo en las dos ubicaciones; C9 enseña los dos importes |
| `core/viabilidad_json.py` | publicación exclusiva por `O_EXCL` cuando el filesystem no admite hard link |
| `tests/test_whatsapp_export.py`, `tests/test_whatsapp_intake.py`, `tests/test_whatsapp_atomize_pipeline.py`, `tests/test_whatsapp_atomize_propuesta.py`, `tests/test_verificar_apertura.py`, `tests/test_viabilidad_json.py` | casos nuevos; ninguno existente se toca ni se relaja |

---

### Task 0: Bloque 0 — el backlog dice lo que pasó (solo `docs/`, exento de ronda)

**Files:** Modify `docs/MEJORAS_FUTURAS.md`; notas fuera del repo en `%LOCALAPPDATA%\FeesDefender\aperturas\`.

- [ ] **Step 1:** Añadir al final de `MEJORAS_FUTURAS.md`:
  - `## 287.` C3 no puede pasar en ningún caso con bundles partidos (texto del PR #387, su «277»),
    con la medición de 9 de 9 y la frontera («validar una invariante contra el fichero equivocado»).
  - `## 288.` La verificación de `crm_ficha` comprueba inclusión y no igualdad (su «279»), con el
    653, los dos colaboradores ajenos y el remedio (releer el bloque y contrastar el conjunto).
  - `## 289.`-`## 291.` La nota de PARTICULAR-659: el camino particular que no existe (sin
    disparador), el `movil` (lo que rechaza el CRM es el separador; medido solo en
    `clientes_propios`) y `profesional_asignado` vacío en las altas extrajudiciales.
- [ ] **Step 2:** Llevar a `#276` el dato que solo estaba en el PR (crear con `open(destino, "x")`
  funcionó sobre `G:` el 2026-09-16; **que rechace un destino existente no se midió**). Llevar a
  `#218` que C9 no enseña los dos importes. Rehacer `#237` con la medición de W-02UIQU del
  2026-09-25 (la etiqueta SÍ se aplicó, verificado por resultado; lo que siempre sale vacío es
  `label_ids`, porque para `threads().modify` las etiquetas van en `messages[].labelIds`).
- [ ] **Step 3:** Notas: W-030A13 → `fichas: [276, 268, 218, 287, 288]` con una línea que diga por
  qué cambió; PARTICULAR-659 → `estado: fichado`, `fichas: [289, 290, 291]`; W-02UIQU → solo una
  línea bajo su sección de `apply_label` («incorporado a `MEJORAS #237` por la sesión de
  reparación del 2026-09-25»), sin tocar su `estado`.
- [ ] **Step 4:** Guard G1 (`tests/test_docs_gobernanza.py::test_mejoras_futuras_numeracion_unica`)
  verde; commit `docs(mejoras): ...`.
- [ ] **Step 5:** Cerrar el PR #387 con un comentario que enumere a dónde fue cada una de sus cinco
  entradas (autorizado por Nikolai el 2026-09-25).

---

### Task 1: `#236` — las marcas invisibles en las referencias de adjuntos (iOS y Android)

**Files:** Modify `core/whatsapp_export.py:99-111`; Test `tests/test_whatsapp_export.py`, `tests/test_whatsapp_intake.py`.

**Interfaces:** Produces `_limpiar_ref(nombre: str) -> str` (privada) — `_adjunto_ref` la aplica a
las dos ramas que devuelven un nombre de fichero.

- [ ] **Step 1: tests que fallan**

```python
# tests/test_whatsapp_export.py
@pytest.mark.parametrize("linea, esperado", [
    ("\u200e<adjunto: \u200eIMG-20240310-WA0000.jpg>", "IMG-20240310-WA0000.jpg"),  # iOS, marca DENTRO del tag
    ("\u200ePTT-20260409-WA0001.opus (archivo adjunto)", "PTT-20260409-WA0001.opus"),  # Android
    ("<adjunto: IMG-1.jpg\u200f>", "IMG-1.jpg"),                                     # marca al final
    ("<adjunto: \ufeffDOC 1.pdf>", "DOC 1.pdf"),                                      # BOM
])
def test_adjunto_ref_quita_las_marcas_invisibles_de_los_bordes(linea, esperado):
    assert wa._adjunto_ref(linea) == esperado

def test_adjunto_ref_no_toca_el_interior_del_nombre():
    # control positivo: solo los BORDES; un nombre raro por dentro se devuelve tal cual
    assert wa._adjunto_ref("<adjunto: a\u200eb.jpg>") == "a\u200eb.jpg"
```

```python
# tests/test_whatsapp_intake.py — el síntoma del intake (W-0462E1: 30 «faltantes» con los 30 en el lote)
def test_analyze_no_da_por_faltante_un_adjunto_referenciado_con_marca():
    chat = "09/04/2026, 10:00 - Pablo: \u200ePTT-20260409-WA0001.opus (archivo adjunto)\n"
    zip_bytes = _zip({"Chat de WhatsApp con Pablo.txt": chat.encode(),
                      "PTT-20260409-WA0001.opus": b"OggS"})
    p = wi.analyze(zip_bytes, zip_name="Chat de WhatsApp con Pablo.zip")
    assert p.adjuntos_faltantes == []
    assert p.adjuntos_referenciados == ["PTT-20260409-WA0001.opus"]

def test_analyze_sigue_dando_por_faltante_el_que_de_verdad_falta():   # control positivo
    chat = "09/04/2026, 10:00 - Pablo: \u200ePTT-20260409-WA0009.opus (archivo adjunto)\n"
    zip_bytes = _zip({"Chat de WhatsApp con Pablo.txt": chat.encode()})
    p = wi.analyze(zip_bytes, zip_name="x.zip")
    assert p.adjuntos_faltantes == ["PTT-20260409-WA0009.opus"]
```

- [ ] **Step 2:** `pytest tests/test_whatsapp_export.py tests/test_whatsapp_intake.py -q` → FALLAN
  los de la marca (devuelve `'\u200eIMG…'`).
- [ ] **Step 3: implementación**

```python
# Marcas de dirección y de orden de bytes que el export de WhatsApp pone delante (o detrás) del
# nombre del adjunto. No son espacio en blanco para `str.strip()`: sin quitarlas, la referencia no
# casa con el fichero en disco (MEJORAS #236: 0 de 39 en W-02V48N). Solo en los BORDES: por
# dentro, el nombre es el que es.
_MARCAS_INVISIBLES = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff"


def _limpiar_ref(nombre: str) -> str:
    return nombre.strip().strip(_MARCAS_INVISIBLES).strip()
```

  y en `_adjunto_ref`, `return _limpiar_ref(m.group(1))` en las ramas iOS y Android.
- [ ] **Step 4:** los mismos tests → PASAN; `pytest tests -q -k "whatsapp"` verde.
- [ ] **Step 5:** commit `fix(whatsapp): las referencias de adjuntos sin marcas invisibles (MEJORAS #236)`.

---

### Task 2: `#285` — una sola regla de «fichero de chat» para intake, manifiesto y atomizador

**Files:** Modify `core/whatsapp_export.py`, `core/whatsapp_intake.py:62-74,182-203`,
`core/whatsapp_atomize/pipeline.py:27-50,67-69`, `core/whatsapp_atomize/propuesta_identidades.py:18-19`;
Tests `tests/test_whatsapp_export.py`, `tests/test_whatsapp_intake.py`,
`tests/test_whatsapp_atomize_pipeline.py`, `tests/test_whatsapp_atomize_propuesta.py`.

**Interfaces:**
- Produces `whatsapp_export.CHAT_TXT = "_chat.txt"`.
- Produces `whatsapp_export.elegir_chat(textos: Mapping[str, str]) -> str | None` — nombre (clave
  del mapping) del fichero de chat.
- Produces `whatsapp_atomize.pipeline.chat_txt_de(chat_dir: Path) -> Path | None`.

**La regla** (una, en `elegir_chat`), en este orden:
1. `_chat.txt` si está (iOS y legacy) — sin exigir que se interprete, como hoy;
2. si no, el primer `.txt` por orden alfabético cuyo texto `parse_chat` interpreta (≥1 mensaje):
   el export Android en español trae `Chat de WhatsApp con <contacto>.txt`, y un `.txt` que se
   envió como adjunto no debe ganarle por orden;
3. si ninguno se interpreta, el primer `.txt` por orden (custodia antes que parser: el intake
   deposita, y el atomizador lo verá como chat con 0 mensajes, visible en su `INDICE.md`);
4. `None` si no hay `.txt`.

Nunca se elige un derivado nuestro: los nombres que empiezan por `_` quedan fuera salvo `_chat.txt`
(`_chat_recortado.txt` lo escribe el propio intake).

**Fuera de alcance, declarado:** `core/adjuntos_contenido/zips._como_whatsapp` exige además que
`_chat.txt` se interprete; esa divergencia es deliberada (`MEJORAS #55`) y no se toca.

- [ ] **Step 1: tests que fallan**

```python
# tests/test_whatsapp_export.py
IOS = "[10/3/24, 12:00:00] Ana: hola\n"
AND = "09/04/2026, 10:00 - Pablo: hola\n"

def test_elegir_chat_prefiere_chat_txt():
    assert wa.elegir_chat({"_chat.txt": IOS, "Acta.txt": "texto"}) == "_chat.txt"

def test_elegir_chat_android_por_contenido_no_por_orden():
    # «Acta.txt» va antes por orden y NO es una conversación
    assert wa.elegir_chat({"Acta.txt": "texto libre",
                           "Chat de WhatsApp con Pablo.txt": AND}) == "Chat de WhatsApp con Pablo.txt"

def test_elegir_chat_ninguno_interpretable_devuelve_el_primero():
    assert wa.elegir_chat({"b.txt": "x", "a.txt": "y"}) == "a.txt"

def test_elegir_chat_nunca_un_derivado_nuestro_ni_sin_txt():
    assert wa.elegir_chat({"_chat_recortado.txt": AND, "foto.jpg": ""}) is None
    assert wa.elegir_chat({}) is None
```

```python
# tests/test_whatsapp_atomize_pipeline.py — el síntoma medido (W-0462E1: chats 2, mensajes 87)
def test_descubre_y_atomiza_un_chat_android_con_nombre_propio(tmp_path, monkeypatch):
    lote = tmp_path / "00_Input" / "2026-09-23_whatsapp_02" / "01_Cliente" / "Chat con Pablo"
    lote.mkdir(parents=True)
    (lote / "Chat de WhatsApp con Pablo.txt").write_text(
        "09/04/2026, 10:00 - Pablo: uno\n09/04/2026, 10:01 - Elena: dos\n", encoding="utf-8")
    ios = tmp_path / "00_Input" / "2026-09-23_whatsapp_01" / "01_Cliente" / "Chat Ana"
    ios.mkdir(parents=True)
    (ios / "_chat.txt").write_text("[10/3/24, 12:00:00] Ana: hola\n", encoding="utf-8")
    monkeypatch.setattr(pipeline, "caso_path", lambda _cid: tmp_path)
    assert {d.name for d in pipeline.descubrir_chats(tmp_path)} == {"Chat con Pablo", "Chat Ana"}
    r = pipeline.atomize_whatsapp_case("X")
    assert (r["chats"], r["mensajes"]) == (2, 3)

def test_el_chat_con_nombre_propio_no_se_lee_como_media(tmp_path):
    d = tmp_path / "c"; d.mkdir()
    (d / "Chat de WhatsApp con Pablo.txt").write_text("09/04/2026, 10:00 - Pablo: uno\n", encoding="utf-8")
    (d / "foto.jpg").write_bytes(b"\xff\xd8")
    chat = pipeline.chat_txt_de(d)
    assert chat is not None and chat.name == "Chat de WhatsApp con Pablo.txt"
    assert set(pipeline._leer_media(d, chat)) == {"foto.jpg"}
```

```python
# tests/test_whatsapp_intake.py — el manifiesto (W-0462E1: el lote registró el chat como `txt`)
def test_deposit_registra_el_chat_android_como_whatsapp(caso_tmp):   # fixture del fichero
    ...deposita un zip con «Chat de WhatsApp con Pablo.txt» + un «Acta.txt» adjunto...
    items = _items_del_manifiesto(lote)
    assert items["…/Chat de WhatsApp con Pablo.txt"]["tipo_contenido"] == "whatsapp"
    assert items["…/Acta.txt"]["tipo_contenido"] == "txt"          # control positivo
```

  (el test concreto del intake se escribe sobre la fixture y el lector de manifiesto que ya use
  `tests/test_whatsapp_intake.py`; no se inventa una nueva.)
- [ ] **Step 2:** los nuevos FALLAN (`elegir_chat` no existe; `descubrir_chats` solo ve `_chat.txt`).
- [ ] **Step 3: implementación** — `whatsapp_export`:

```python
CHAT_TXT = "_chat.txt"


def elegir_chat(textos: "Mapping[str, str]") -> str | None:
    """El fichero de chat de un export, con UNA regla para todo el canal (MEJORAS #285).

    1. `_chat.txt` si está; 2. si no, el primer `.txt` (orden alfabético) que `parse_chat`
    interpreta; 3. si ninguno, el primer `.txt` (custodia antes que parser); 4. `None`.
    Los derivados nuestros (`_…`, salvo `_chat.txt`) no son candidatos.
    """
    if CHAT_TXT in textos:
        return CHAT_TXT
    txts = sorted(n for n in textos
                  if n.lower().endswith(".txt") and not Path(n).name.startswith("_"))
    for n in txts:
        if parse_chat(textos[n]):
            return n
    return txts[0] if txts else None
```

  `whatsapp_intake._find_chat_txt`: decodifica los `.txt` y llama a `elegir_chat`; mismo
  `ValueError` si devuelve `None`. En `deposit_export`, `_escribe` recibe
  `tipo_contenido="whatsapp"` para `chat_txt_name` y deja el resto a `clasificar_tipo_contenido`.
  `pipeline.chat_txt_de(chat_dir)`: lee los `.txt` del directorio (no recursivo) y aplica
  `elegir_chat`; `descubrir_chats` recorre `rglob("*")` de las mismas bases, se queda con los
  directorios con algún `.txt` y filtra por `chat_txt_de(d) is not None`; `_leer_media(chat_dir,
  chat)` excluye `chat.name` y lo que empieza por `_`; `atomize_whatsapp_case` y
  `preparar_propuesta` leen `chat_txt_de(chat_dir)`.
- [ ] **Step 4:** nuevos → PASAN; `pytest tests -q -k "whatsapp or intake_lotes or adjuntos_contenido"` verde.
- [ ] **Step 5:** commit `fix(whatsapp): una sola regla de fichero de chat (MEJORAS #285)`.

---

### Task 3: `verificar_apertura` dice lo que ya sabe (C2 `#268`, C3 `#269`, C9 `#218`)

**Files:** Modify `core/verificar_apertura.py:166-232` (C3), `:858-861` (C2), `:1008-1027` (C9);
Test `tests/test_verificar_apertura.py`.

**Interfaces:** Consumes `ubicaciones_del_catalogo(proc, sala)` (ya existe, lo usa C4). No cambia la
firma de ninguna comprobación ni el vocabulario de estados.

- [ ] **C2.** Con discrepancias, el `detalle` distingue los tres casos y la evidencia lleva los
  **conteos sin truncar** (`n_discrepan`, `n_relleno_225`) y la lista de las **no explicadas**:
  - todas explicadas: «N fichero(s) cuyo sha256 NO es el que Drive declara; los N son el relleno con
    ceros de `MEJORAS #225` (confirmado re-hasheando sin la cola): el contenido es el del original»;
  - algunas: «…; M son el relleno de `#225` y K NO se explican: <las K primeras>»;
  - ninguna: el mensaje de hoy.
  Estado: `fallo` en los tres. Tests: uno por caso (con el mismo doble de censo que ya usan los
  tests de C2), y el conteo de 12 discrepancias con evidencia de listas truncadas a 8 y conteos
  en 12.
- [ ] **C3.** Resuelve el catálogo con `ubicaciones_del_catalogo` y la evidencia dice
  `catalogo_en` (`sala` | `01_Procesado`), igual que C4. Una ubicación que existe y no es fichero
  sigue siendo `fallo`. Tests: catálogo solo en `Sala lectura/` → se compara (no `pendiente`);
  control positivo: sin catálogo en ninguna → `pendiente`.
- [ ] **C9.** Evidencia por expediente con `crm` (el número) además de `crm_declarada`/`legible`;
  el `detalle` de la discrepancia lleva los dos importes y, si el del CRM es el entero que manda
  el alta (`round(local)` y sin decimales), lo dice: «(es el truncado del alta: `MEJORAS #218`)».
  Estado: `fallo` igual. Tests: 48702.50 vs 48702.00 → los dos números y la mención; control:
  48702.50 vs 40000 → los dos números y **sin** la mención.
- [ ] **Step final:** `pytest tests/test_verificar_apertura.py -q` verde; commit
  `fix(verificar_apertura): C2, C3 y C9 dicen lo que ya calculan (MEJORAS #268, #269, #218)`.

---

### Task 4: `#276` — `_viabilidad.json` se puede publicar sobre `G:`

> **Resultado de la medición previa, y la decisión que cambió (2026-09-25).** En `G:\Mi unidad`,
> carpeta de sondeo propia y borrada al terminar: `os.link` → `OSError errno=22 winerror=1`;
> `os.open(existente, O_CREAT|O_EXCL)` → `FileExistsError`; `os.open(nuevo, O_EXCL)` crea y
> escribe; y —lo que no se esperaba— `os.rename(tmp, existente)` → `FileExistsError`
> (`winerror=183`) con el destino intacto. Con eso, la vía de repuesto **no es `O_EXCL`** como
> decía el paso 3 de abajo, sino `os.rename`: en Windows conserva las **dos** promesas del
> docstring (no pisa y publica de una vez un temporal completo), mientras que `O_EXCL` habría
> obligado a declarar una ventana de fichero a medias. Fuera de Windows `os.rename` pisa, así que
> ahí no hay vía de repuesto y el error se propaga como antes. Lo de abajo queda como estaba
> escrito antes de medir; lo construido es lo de este párrafo (commit `d0d1427`), y se corrió de
> verdad contra `G:` con el módulo del worktree: primera escritura publicada y válida, segunda
> `FileExistsError` «no se pisa», destino intacto, sin temporales.

**Files:** Modify `core/viabilidad_json.py:247-330`; Test `tests/test_viabilidad_json.py`.

**Medición previa, obligatoria:** en una carpeta de sondeo de `G:\Mi unidad\` (fuera de los
expedientes, borrada al terminar): `os.link` → ¿`WinError 1`?; `os.open(existente, O_CREAT|O_EXCL)`
→ ¿`FileExistsError`?; `os.open(nuevo, O_CREAT|O_EXCL)` → ¿crea? Si `O_EXCL` NO rechaza el
existente, **esta tarea se para** y se vuelve a Nikolai: sin esa garantía el remedio pisaría lo que
remató una sesión.

**Interfaces:** Produces `_sin_enlace_duro(exc: OSError) -> bool` y
`_publicar_por_creacion_exclusiva(destino: Path, datos: bytes) -> None` (privadas).

- [ ] **Step 1: tests que fallan**

```python
def test_sin_enlace_duro_publica_por_creacion_exclusiva(tmp_path, monkeypatch):
    def _link(*a, **k):
        e = OSError(22, "Función incorrecta"); e.winerror = 1; raise e   # lo que da G:
    monkeypatch.setattr(vj.os, "link", _link)
    destino = vj.escribir(tmp_path, _datos_validos())
    assert json.loads(destino.read_text(encoding="utf-8")) == _datos_validos()
    assert not list(destino.parent.glob("*.tmp"))

def test_sin_enlace_duro_sigue_sin_pisar(tmp_path, monkeypatch):
    # la carrera: el destino aparece DESPUÉS de la comprobación rápida y ANTES de publicar
    ...parchea os.link como arriba y crea el destino dentro del write_text del temporal...
    with pytest.raises(FileExistsError):
        vj.escribir(tmp_path, _datos_validos())
    assert destino.read_text(encoding="utf-8") == "LO QUE REMATÓ LA SESIÓN"

def test_otro_error_del_enlace_no_se_disfraza(tmp_path, monkeypatch):   # control positivo
    def _link(*a, **k):
        raise PermissionError(13, "denegado")
    monkeypatch.setattr(vj.os, "link", _link)
    with pytest.raises(PermissionError):
        vj.escribir(tmp_path, _datos_validos())

def test_fallo_a_mitad_de_la_escritura_no_deja_el_destino(tmp_path, monkeypatch):
    ...parchea os.link (winerror 1) y os.write para que falle tras crear el destino...
    with pytest.raises(OSError):
        vj.escribir(tmp_path, _datos_validos())
    assert not vj.ruta(tmp_path).exists()
```

- [ ] **Step 2:** FALLAN (hoy el `WinError 1` sale tal cual).
- [ ] **Step 3: implementación** — en `escribir`, alrededor del `os.link`:

```python
        try:
            os.link(tmp, destino)
        except FileExistsError:
            raise FileExistsError(_mensaje_ya_existe(destino)) from None
        except OSError as exc:
            if not _sin_enlace_duro(exc):
                raise
            _publicar_por_creacion_exclusiva(destino, tmp.read_bytes())
```

  `_sin_enlace_duro`: `winerror` 1 (medido en Drive for Desktop) o 50 (`ERROR_NOT_SUPPORTED`), o
  `errno` en `ENOTSUP`/`EOPNOTSUPP`/`ENOSYS`. **No** `EPERM` ni `EACCES`: un permiso denegado no
  es un filesystem sin enlaces, y disfrazarlo sería el defecto de siempre.
  `_publicar_por_creacion_exclusiva`: `os.open(destino, O_WRONLY|O_CREAT|O_EXCL|O_BINARY)`
  (`FileExistsError` → el mismo mensaje de «no se pisa»), escribe todo, `fsync`, cierra; ante
  cualquier fallo tras crear, borra **el que acaba de crear** y relanza. Los bytes son los del
  temporal ya completo, así que lo publicado es idéntico por las dos vías.
  El docstring declara la promesa recortada en esa vía: el destino sigue sin pisarse nunca, pero
  un `kill -9` entre la creación y el `fsync` puede dejarlo **a medias**; `validar` lo rechaza al
  leerlo y un reintento lo encuentra existente, así que el síntoma es ruidoso, no silencioso.
- [ ] **Step 4:** PASAN; `pytest tests/test_viabilidad_json.py tests -q -k "viabilidad or apertura"` verde.
- [ ] **Step 5:** commit `fix(viabilidad_json): publicar sobre Drive for Desktop sin pisar nunca (MEJORAS #276)`.

---

### Task 5: rondas, adjudicación y cierre

- [ ] **R1 — Bloque 1** (Tasks 1-3): Codex `gpt-6-sol`·`high`·`default`, fila ordinaria; primer dato
  de la calibración de la fila #38. Mandato numerado y anclado a commits, sin coacción, con los dos
  ejes (severidad y coste del remedio). Vigía armado antes de lanzar (fin **o** muerte).
- [ ] **R2 — Bloque 2** (Task 4): Codex `gpt-6-astra`·`high`·`default`, por la fila de exclusión y
  estados parciales; se declara en el PR con esa frontera.
- [x] Adjudicación de cada ronda contra la fuente, embebida aquí (§6 y §7), y acta literal hermana
  por pieza con su digest: `…-bloque1-r1-adversarial-review.md` y `…-276-r1-adversarial-review.md`.
  En la sesión se llamaron «R1» y «R2» porque corrieron en paralelo; cada una es la **única**
  ronda de su pieza.
- [ ] `PLAN.md` fila nueva + `[PROMOVIDO → PLAN.md]` en las entradas; cierres en `MEJORAS`;
  bitácora; `python -m scripts.session_close`; push; PR (sin mergear hasta dar la sesión por
  terminada).

---

## 6. Adjudicación de la revisión adversarial del bloque 1 (Codex, 2026-09-25) — NO-SHIP, remediado

- **Objeto revisado:** diff `9880165..7c70b70` —`MEJORAS #236`, `#285` y `verificar_apertura` C2, C3 y C9—
- **Ronda:** R1 (única de la pieza; fila de una ronda)
- **Revisor:** Codex CLI `0.155.0-alpha.16.3`, `gpt-6-sol` · `high` · `default` (modelo y esfuerzo releídos del rollout)
- **Informe recibido:** `docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana-bloque1-r1-adversarial-review.md`
- **Hallazgos:** 6 — 1 `alta`, 5 `media`; 6 confirmados contra la fuente, 0 refutados
- **Remediado en:** `94522ce` (H-05, H-06) y `61523e8` (H-01 a H-04)

**Los seis se reprodujeron contra el código, no contra el informe**: la sonda del revisor, apuntada
al worktree, da los seis síntomas (acta §2). Y no son seis defectos sueltos: son **tres
fronteras**, y el remedio es el de la frontera.

**Frontera 1 — qué identifica al chat de un export (H-01, H-02, H-03).** Identifiqué el chat con
señales débiles —el prefijo `_`, que una línea se interprete, que haya un `.txt`— y apliqué la
regla de custodia del intake también al atomizador.

- **H-01 (media, trivial) — CONFIRMADO.** Excluir todo nombre con `_` rechazaba entero un export
  cuyo chat se llamara `_conversacion.txt`: regresión de custodia contra `base/`. Remedio: solo
  son derivados los que el canal escribe (`DERIVADOS = {"_chat_recortado.txt"}`).
- **H-02 (media, estructural) — CONFIRMADO, y no es regresión** (`base/` elegía el primer `.txt`
  sin mirar nada), pero mi docstring afirmaba que un adjunto no le ganaba al chat y era falso.
  Remedio: el chat es la conversación con **pruebas de serlo**: se descartan las que otra cita
  como adjunto, gana la que cita más ficheros del export y, a igualdad, la de más mensajes.
  **Residuo declarado** en el docstring: un export sin ficheros con un adjunto no citado más largo
  que el chat.
- **H-03 (media, estructural) — CONFIRMADO, regresión.** Cualquier directorio con un `.txt`
  pasaba por chat, el de rol incluido. Remedio: el atomizador llama con `custodia=False` y solo
  mira `<base>/<rol>/<chat>/`, donde el intake deja los chats; `_chat.txt` sigue valiendo a
  cualquier profundidad.

**Frontera 2 — limpiar un identificador no puede ligarlo a otros bytes (H-04, alta, estructural)
— CONFIRMADO.** Con la marca quitada al parsear, una referencia podía casar con OTRO fichero o
dejar de casar con el suyo. Remedio: `parse_chat` guarda la referencia cruda además de la limpia
y `resolver_adjunto` busca el nombre como lo citó el chat, después el limpio, y por nombre limpio
solo si identifica un fichero; con dos, ausente. Lo usan el intake y `construir_adjuntos`, que
nombra el adjunto por el fichero elegido. **La severidad es la del revisor y la mantengo, pero con
su contexto:** WhatsApp no escribe marcas en los nombres de fichero —en W-02V48N casaron 31 de 39
con la referencia limpia—, así que el caso exige un fichero renombrado a mano; lo caro no es la
frecuencia sino que ligaría bytes ajenos en silencio.

**Frontera 3 — lo que el verificador declara tiene que ser lo que mira (H-05, H-06).**

- **H-05 (media, acotado) — CONFIRMADO, regresión.** Con los dos catálogos, C3 cogía el de la sala
  y no leía el otro: un catálogo discordante salía `ok` donde `base/` daba `fallo`. Remedio: se
  leen los dos, y si sus conteos no cuadran es `fallo` con las dos ubicaciones en la evidencia.
- **H-06 (media, trivial) — CONFIRMADO.** «Entero a menos de un euro» etiquetaba como truncado
  del alta lo que el alta no habría mandado. Remedio: la mención exige `int(round(local))`
  exacto, con test del `.90` y del redondeo bancario `.50`.

**Lo que el revisor intentó y no pudo, y conviene no perder:** los `msg_id` de un chat ya
atomizado no cambian por este diff; C2 mantiene `fallo` en los tres casos y no trunca los
conteos; C3 con una ruta ocupada da `fallo`.

**Los 13 tests nuevos de la remediación se vieron en rojo contra `94522ce`** —el código previo al
remedio— y pasan con él. **La remediación NO ha pasado ronda, y se declara:** la pieza es de una
ronda. **Omisiones** para la columna de la calibración: ninguna conocida a esta fecha, lo que
significa «todavía no ha pasado tiempo», no «no hubo».

## 7. Adjudicación de la revisión adversarial de `MEJORAS #276` (Codex, 2026-09-25) — SHIP, remediado

- **Objeto revisado:** diff `7c70b70..d0d1427` —la vía de repuesto de `viabilidad_json.escribir` sin hard links—
- **Ronda:** R1 (única de la pieza; en la sesión, «R2»)
- **Revisor:** Codex CLI `0.155.0-alpha.16.3`, `gpt-6-astra` · `high` · `default` (modelo y esfuerzo releídos del rollout)
- **Informe recibido:** `docs/superpowers/plans/2026-09-25-mejoras-aperturas-semana-276-r1-adversarial-review.md`
- **Hallazgos:** 0 `H-NN`; 2 huecos de cobertura y 2 frases del docstring señalados como no defectos, atendidos
- **Remediado en:** `2b2653c`

**`SHIP` se acepta por el ataque que lo sostiene, no por la palabra**: doce carreras, veinte
escritores, la muerte del proceso a los dos lados del `rename` y un mutante `os.replace` que
muere (acta §2). Lo que el revisor señaló sin llamarlo defecto, y se atendió porque era barato:

- **Dos mutantes supervivientes** —quitar la guarda de plataforma; aceptar solo el `winerror`
  1—: dos tests nuevos, y cada mutante muere ahora por el suyo (comprobado sobre copias).
- **El docstring prometía sobrevivir a un corte de luz** sin `fsync`. Era anterior al diff; se
  corrige para que no prometa lo que no hace.
- **El comentario del `finally`** decía que `missing_ok` era defensivo; con la vía nueva es
  necesario.

**La remediación NO ha pasado ronda**, y se declara. Esta ronda **no cuenta para la calibración**
de la fila #38: su fila de modelo es la de Astra.
