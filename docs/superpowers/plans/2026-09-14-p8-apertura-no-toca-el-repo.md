---
tipo: plan
estado: vigente
creado: 2026-09-14
spec: docs/superpowers/specs/2026-09-14-p8-apertura-no-toca-el-repo-design.md
---

# P8 — Una sesión de apertura no toca el repo: plan de implementación

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development`
> (recomendada) o `superpowers:executing-plans` para ejecutar este plan tarea a tarea. Los pasos
> usan casillas (`- [ ]`) para el seguimiento.

**Goal:** que el cierre de sesión avise cuando una apertura dejó defectos anotados y sin fichar, y
que (a), (b) y (d) queden escritas donde gobiernan.

**Architecture:** un lector puro en `scripts/session_close.py` que recorre
`%LOCALAPPDATA%\FeesDefender\aperturas\*.md` y devuelve **dos** listas —pendientes e ilegibles—,
un aviso no bloqueante que solo habla si hay algo que decir, y un guard que ata el formato escrito
en el RUNBOOK al código que lo lee.

**Tech Stack:** Python 3, `pytest`, sin dependencias nuevas. **Sin `yaml`** (ver constraints).

## Global Constraints

- **Windows + PowerShell.** Todo comando desde la raíz del worktree.
- **UTF-8 sin BOM** en todo fichero escrito.
- **El parseo del frontmatter NO usa `yaml`.** Dos razones: `yaml.safe_load` convierte
  `fecha: 2026-09-14` en `datetime.date` y no en el `str` que el resto compara; y `session_close`
  tiene documentado un `ModuleNotFoundError: No module named 'yaml'` al invocarse desde un
  worktree (`tests/test_session_close_no_pude_medir.py:4-7`), que convertiría un aviso en una
  caída del cierre entero.
- **Ningún test escribe en el `%LOCALAPPDATA%` real.** Todos reciben `tmp_path`. Lo vigila
  `tests/test_guard_aislamiento_paralelo.py`.
- **`_leer_aperturas` no tiene default de raíz** — doctrina de `core/casos/workspace_registry.py`:
  «sin default no hay dónde caerse». El default vive en `raiz_aperturas_por_defecto()`, para el
  llamador.
- **Estilo del script:** los lectores de `session_close.py` devuelven **tuplas**, no dataclasses
  (`_trabajo_sin_publicar` → `list[tuple[str, int, str]]`). Se sigue el precedente.
- **Aviso, nunca verja.** La única verja es la suite.

---

### Task 1: El lector de ficheros de apertura

**Files:**
- Modify: `scripts/session_close.py` (bloque nuevo tras `_avisar_specs_sin_traza`, antes de
  `UMBRAL_COBERTURA_DEL_DIFF`)
- Test: `tests/test_session_close_aperturas.py` (crear)

**Interfaces:**
- Consumes: `Path` (ya importado en el script), `os` (ya importado).
- Produces:
  - `_ESTADOS_APERTURA: set[str]` = `{"pendiente", "fichado", "descartado"}`
  - `raiz_aperturas_por_defecto() -> Path`
  - `_leer_aperturas(raiz: Path) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]`
    — `(pendientes, ilegibles)`; pendientes son `(fichero, caso, fecha)`, ilegibles
    `(fichero, motivo)`. Ambas ordenadas por nombre de fichero.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_session_close_aperturas.py`:

```python
"""El lector de ficheros de apertura de `session_close`.

Prueba la lógica pura (`_leer_aperturas`) sobre un árbol sintético en `tmp_path`.
Nunca toca el `%LOCALAPPDATA%` real: la raíz se INYECTA, que es justo para lo que
la pieza no tiene default.
"""

from pathlib import Path

import scripts.session_close as sc


def _escribir(raiz: Path, nombre: str, texto: str) -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / nombre).write_text(texto, encoding="utf-8")


_PENDIENTE = """---
caso: W-02UDC1
fecha: 2026-09-14
estado: pendiente
fichas: []
---

## El pull rellenó con ceros
"""


def test_control_positivo_un_pendiente_se_ve(tmp_path):
    # Sin este test, todos los demás pasan con un lector que devuelve siempre vacío.
    _escribir(tmp_path, "2026-09-14_W-02UDC1.md", _PENDIENTE)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == [("2026-09-14_W-02UDC1.md", "W-02UDC1", "2026-09-14")]
    assert ilegibles == []


def test_fichado_y_descartado_no_avisan(tmp_path):
    _escribir(tmp_path, "a.md", _PENDIENTE.replace("estado: pendiente", "estado: fichado"))
    _escribir(tmp_path, "b.md", _PENDIENTE.replace("estado: pendiente", "estado: descartado"))

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert ilegibles == []


def test_frontmatter_roto_sale_por_ilegibles_y_no_revienta(tmp_path):
    _escribir(tmp_path, "roto.md", "---\ncaso: W-1\nestado: pendiente\nsin cierre\n")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert [f for f, _ in ilegibles] == ["roto.md"]
    assert "cierre" in ilegibles[0][1]


def test_sin_frontmatter_es_ilegible(tmp_path):
    _escribir(tmp_path, "plano.md", "solo prosa, ningun frontmatter\n")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert [f for f, _ in ilegibles] == ["plano.md"]


def test_estado_desconocido_es_ilegible_no_fichado(tmp_path):
    # La direccion del fallo importa: ante la duda, el aviso habla.
    _escribir(tmp_path, "x.md", _PENDIENTE.replace("estado: pendiente", "estado: archivado"))

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert "archivado" in ilegibles[0][1]


def test_carpeta_inexistente_no_lanza(tmp_path):
    pendientes, ilegibles = sc._leer_aperturas(tmp_path / "no-existe")

    assert (pendientes, ilegibles) == ([], [])


def test_solo_mira_md_de_la_carpeta_sin_recursion(tmp_path):
    _escribir(tmp_path, "notas.txt", "lo que sea")
    sub = tmp_path / "sub"
    _escribir(sub, "hondo.md", _PENDIENTE)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    # El .txt no es un fichero de apertura mal escrito: es que no es uno.
    assert (pendientes, ilegibles) == ([], [])


def test_caso_ausente_es_ilegible_aunque_el_nombre_lleve_el_wcode(tmp_path):
    # Impide que alguien "arregle" el lector derivando el caso del nombre.
    sin_caso = "---\nfecha: 2026-09-14\nestado: pendiente\n---\n"
    _escribir(tmp_path, "2026-09-14_W-02UDC1.md", sin_caso)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert "caso" in ilegibles[0][1]


def test_estado_se_normaliza_en_minusculas_y_sin_espacios(tmp_path):
    _escribir(tmp_path, "m.md", _PENDIENTE.replace("estado: pendiente", "estado:  Pendiente  "))

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert [c for _, c, _ in pendientes] == ["W-02UDC1"]
    assert ilegibles == []


def test_raiz_por_defecto_respeta_el_override(monkeypatch, tmp_path):
    monkeypatch.setenv("FEESDEFENDER_APERTURAS", str(tmp_path / "elegida"))

    assert sc.raiz_aperturas_por_defecto() == tmp_path / "elegida"


def test_raiz_por_defecto_cae_en_localappdata(monkeypatch, tmp_path):
    monkeypatch.delenv("FEESDEFENDER_APERTURAS", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert sc.raiz_aperturas_por_defecto() == tmp_path / "FeesDefender" / "aperturas"
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
python -m pytest tests/test_session_close_aperturas.py -q --tb=short
```

Esperado: FAIL — `AttributeError: module 'scripts.session_close' has no attribute '_leer_aperturas'`.

- [ ] **Step 3: Implementación mínima**

En `scripts/session_close.py`, tras la función `_avisar_specs_sin_traza`:

```python
# --- Aperturas con defectos anotados y sin fichar (P8 (a)) --------------------
#: Estados que un fichero de apertura puede declarar. Cualquier otro es ILEGIBLE,
#: nunca "fichado por defecto": la direccion del fallo importa, y ante la duda el
#: aviso habla.
_ESTADOS_APERTURA = {"pendiente", "fichado", "descartado"}


def raiz_aperturas_por_defecto() -> Path:
    """El hogar de produccion de los ficheros de apertura. Para los LLAMADORES.

    `_leer_aperturas` no se cae aqui sola, y eso es deliberado: la barrera de test
    cubre rclone y `subprocess`, no las escrituras al perfil del usuario, asi que
    un test que se olvidara de redirigir la raiz escribiria en el `%LOCALAPPDATA%`
    real. Misma doctrina que `core/casos/workspace_registry.raiz_por_defecto()`.
    """
    override = os.getenv("FEESDEFENDER_APERTURAS")
    if override:
        return Path(override)
    base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "FeesDefender" / "aperturas"


def _frontmatter_apertura(texto: str) -> tuple[dict[str, str] | None, str]:
    """Parsea el frontmatter plano de un fichero de apertura.

    Devuelve `(campos, "")` o `(None, motivo)`. **No usa `yaml`**, y no es pereza:
    `safe_load` convierte `fecha: 2026-09-14` en `datetime.date` —no en el `str`
    que el resto compara— y el `import yaml` revienta al invocar este script desde
    un worktree, que convertiria un aviso en una caida del cierre entero.
    """
    lineas = texto.splitlines()
    if not lineas or lineas[0].strip() != "---":
        return None, "sin frontmatter"
    campos: dict[str, str] = {}
    for ln in lineas[1:]:
        if ln.strip() == "---":
            return campos, ""
        if not ln.strip():
            continue
        clave, sep, valor = ln.partition(":")
        if sep:
            campos[clave.strip().lower()] = valor.strip()
    return None, "frontmatter sin cierre"


def _leer_aperturas(raiz: Path) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    """Lee los ficheros de apertura de `raiz`. **La raiz se inyecta: sin default.**

    Devuelve `(pendientes, ilegibles)`. Un fichero que no se puede interpretar NO
    se cuenta como pendiente ni se traga: se declara aparte, que es la leccion de
    la pieza A de la fila #27. Aqui es exacta — un frontmatter tecleado mal es
    justo el caso que, tragado, deja el defecto sin fichar creyendo que lo esta.
    """
    pendientes: list[tuple[str, str, str]] = []
    ilegibles: list[tuple[str, str]] = []
    if not raiz.is_dir():
        return pendientes, ilegibles
    for fichero in sorted(raiz.glob("*.md")):
        nombre = fichero.name
        try:
            texto = fichero.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            ilegibles.append((nombre, f"no se pudo leer: {e}"))
            continue
        campos, motivo = _frontmatter_apertura(texto)
        if campos is None:
            ilegibles.append((nombre, motivo))
            continue
        estado = campos.get("estado", "").strip().lower()
        if not estado:
            ilegibles.append((nombre, "falta estado:"))
        elif estado not in _ESTADOS_APERTURA:
            ilegibles.append((nombre, f"estado desconocido: {estado}"))
        elif not campos.get("caso"):
            ilegibles.append((nombre, "falta caso:"))
        elif not campos.get("fecha"):
            ilegibles.append((nombre, "falta fecha:"))
        elif estado == "pendiente":
            pendientes.append((nombre, campos["caso"], campos["fecha"]))
    return pendientes, ilegibles
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

```bash
python -m pytest tests/test_session_close_aperturas.py -q --tb=short
```

Esperado: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/session_close.py tests/test_session_close_aperturas.py
git commit -m "P8: el lector de ficheros de apertura declara lo que no pudo leer"
```

---

### Task 2: El aviso, y su cableado en `main()`

**Files:**
- Modify: `scripts/session_close.py` (función nueva tras `_leer_aperturas`; llamada en `main()`
  tras el bloque de `_avisar_specs_sin_traza`, líneas ~759-762)
- Test: `tests/test_session_close_aperturas.py` (añadir al final)

**Interfaces:**
- Consumes: `_leer_aperturas(raiz)`, `raiz_aperturas_por_defecto()` de la Task 1.
- Produces: `_avisar_aperturas_sin_fichar(raiz: Path | None = None) -> None`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_session_close_aperturas.py`:

```python
def test_el_aviso_calla_cuando_no_hay_nada(tmp_path, capsys):
    # Silencio total: una cabecera vacia en cada cierre es el aviso que nadie lee.
    sc._avisar_aperturas_sin_fichar(tmp_path)

    assert capsys.readouterr().out == ""


def test_el_aviso_nombra_el_pendiente(tmp_path, capsys):
    _escribir(tmp_path, "2026-09-14_W-02UDC1.md", _PENDIENTE)

    sc._avisar_aperturas_sin_fichar(tmp_path)

    salida = capsys.readouterr().out
    assert "2026-09-14_W-02UDC1.md" in salida
    assert "W-02UDC1" in salida


def test_el_aviso_declara_los_ilegibles_aparte(tmp_path, capsys):
    _escribir(tmp_path, "roto.md", "---\nestado: pendiente\n")

    sc._avisar_aperturas_sin_fichar(tmp_path)

    salida = capsys.readouterr().out
    assert "roto.md" in salida
    assert "no interpretable" in salida


def test_el_aviso_no_rompe_el_cierre_si_el_lector_lanza(tmp_path, monkeypatch, capsys):
    def _explota(_raiz):
        raise RuntimeError("boom")

    monkeypatch.setattr(sc, "_leer_aperturas", _explota)

    # La garantia es la del resto de avisos: nunca rompe el cierre.
    try:
        sc._avisar_aperturas_sin_fichar(tmp_path)
    except RuntimeError:
        raise AssertionError("el aviso dejo escapar la excepcion")
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
python -m pytest tests/test_session_close_aperturas.py -q --tb=short -k aviso
```

Esperado: FAIL — `has no attribute '_avisar_aperturas_sin_fichar'`.

- [ ] **Step 3: Implementación mínima**

En `scripts/session_close.py`, tras `_leer_aperturas`:

```python
def _avisar_aperturas_sin_fichar(raiz: Path | None = None) -> None:
    """AVISO no bloqueante: aperturas que anotaron defectos y no los ficharon.

    (a) de P8 dice que la sesion de apertura los ficha «al final», y nada obligaba
    a ese «al final»: dependia de que alguien se acordara, que es el defecto mas
    medido de esta casa. Esto es el disparador.

    **Silencio total cuando no hay nada** (decision de Nikolai, 2026-09-14). Eso
    hace que un lector roto se parezca a uno que no encuentra nada, asi que la
    prueba de que el instrumento muerde la da el control positivo de la suite, no
    la salida diaria: `test_control_positivo_un_pendiente_se_ve`.
    """
    try:
        raiz = raiz if raiz is not None else raiz_aperturas_por_defecto()
        pendientes, ilegibles = _leer_aperturas(raiz)
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudieron leer las aperturas: {e}")
        return
    if not pendientes and not ilegibles:
        return
    print("\n" + "-" * 40)
    print("Aperturas con defectos sin fichar")
    if pendientes:
        print(f"[!] {len(pendientes)} apertura(s) pendiente(s) de fichar:")
        for nombre, caso, fecha in pendientes:
            print(f"    {nombre}  ({caso}, {fecha})")
        print("    Fichalos en docs/MEJORAS_FUTURAS.md y pon `estado: fichado`,")
        print("    o `estado: descartado` si decides que no merecen ficha.")
    for nombre, motivo in ilegibles:
        print(f"[aviso] no interpretable: {nombre} ({motivo})")
```

Y en `main()`, tras el bloque de `_avisar_specs_sin_traza`:

```python
    # Aviso de aperturas con defectos sin fichar (modo AVISO, no bloquea).
    try:
        _avisar_aperturas_sin_fichar()
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudo comprobar las aperturas sin fichar: {e}")
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

```bash
python -m pytest tests/test_session_close_aperturas.py -q --tb=short
```

Esperado: PASS, 15 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/session_close.py tests/test_session_close_aperturas.py
git commit -m "P8: el cierre avisa de las aperturas sin fichar, y calla si no hay nada"
```

---

### Task 3: (a) en el RUNBOOK, con el bloque de formato literal

**Files:**
- Modify: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (§0, tras la entrada `[APER-41]`, antes del `---`
  de la línea ~97; y §11, tras la línea de `python -m scripts.session_close`)

**Interfaces:**
- Produces: el marcador HTML `<!-- formato-fichero-apertura -->` seguido del bloque cercado que
  la Task 4 extrae. **El marcador es contrato: el guard lo busca por ese texto exacto.**

- [ ] **Step 1: Añadir `[APER-73]` al §0 del RUNBOOK**

Insertar antes del `---` que cierra el §0:

```markdown
- **`[APER-73]` Esta sesión NO toca el repo. Anota los defectos; los fichas al cerrar.**
  Una sesión de apertura ejecuta el runbook y, si encuentra un defecto de *nuestro* código, **no
  lo arregla aquí**: lo anota y sigue. Está medido — las **838 líneas** huérfanas que hubo que
  rescatar el 2026-09-13 (fila #29) fueron una sesión de apertura que se puso a reparar y dejó
  código sin commitear sobre una base **21 commits atrás**, duplicando algo que otra vía ya había
  construido. Repara **una sola** sesión, que es la dueña del código.
  - **Dónde se anota:** `%LOCALAPPDATA%\FeesDefender\aperturas\<AAAA-MM-DD>_<W-code>.md`. Fuera
    del repo a propósito: el fichero lo escribe esta sesión y lo lee el **cierre**, que puede
    correr días después, en otra rama y en otro worktree — la ruta tiene que ser computable por
    las dos sin coordinarse.
  - **Formato** (lo lee `scripts/session_close.py`; el guard
    `tests/test_guard_formato_apertura.py` comprueba que este bloque y el código no divergen):

    <!-- formato-fichero-apertura -->

    ```markdown
    ---
    caso: W-02UDC1
    fecha: 2026-09-14
    estado: pendiente
    fichas: []
    ---

    ## Título corto del defecto

    Lo observado, con su medición y la ruta del fichero.
    ```

  - **`estado`**: `pendiente` · `fichado` · `descartado`. Al fichar, pon `fichado` y lista los
    `MEJORAS #NN` en `fichas:`; si decides que no merece ficha, `descartado` y di por qué en el
    cuerpo. Mientras siga `pendiente`, **`session_close` te lo recordará en cada cierre**.
  - **Los pendientes del CASO no van aquí** — esos son `Pendiente` / `estado.json` / la ficha de
    cierre del expediente. Este fichero es solo para defectos de nuestro código y del proceso.
```

- [ ] **Step 2: Añadir la contrapartida al §11**

Tras la línea `- Cierre estándar: python -m scripts.session_close (slash /cierre).`:

```markdown
- **`[APER-73]` Antes de cerrar: ficha lo que anotaste.** Lee
  `%LOCALAPPDATA%\FeesDefender\aperturas\<fecha>_<W-code>.md`, abre los `MEJORAS #NN` que
  procedan **leyendo `origin/main`** (no la rama en que estés), y deja el fichero en
  `estado: fichado` con sus `fichas:`, o en `estado: descartado`. `session_close` avisa si queda
  alguno en `pendiente` — es aviso, no verja: no te bloquea el cierre.
```

- [ ] **Step 3: Verificar que el marcador quedó exactamente una vez**

```bash
grep -c "formato-fichero-apertura" docs/RUNBOOK_APERTURA_EXPEDIENTE.md
```

Esperado: `1`.

- [ ] **Step 4: Commit**

```bash
git add docs/RUNBOOK_APERTURA_EXPEDIENTE.md
git commit -m "P8 (a): el runbook dice que la apertura no toca el repo, y donde anota"
```

---

### Task 4: El guard que ata el RUNBOOK al código

**Files:**
- Create: `tests/test_guard_formato_apertura.py`

**Interfaces:**
- Consumes: `sc._leer_aperturas` (Task 1) y el marcador `<!-- formato-fichero-apertura -->`
  (Task 3).

- [ ] **Step 1: Escribir el guard**

```python
"""El formato del fichero de apertura vive en DOS sitios: el RUNBOOK y el lector.

Este guard los ata. Sin el, (a) de P8 es una regla escrita que nada aplica: alguien
cambia el ejemplo de la prosa, el lector deja de entenderlo, y el aviso enmudece
justo cuando mas falta hace — que es el defecto que P8 existe para cerrar.
"""

from pathlib import Path

import pytest

import scripts.session_close as sc

RUNBOOK = Path(__file__).resolve().parents[1] / "docs" / "RUNBOOK_APERTURA_EXPEDIENTE.md"
MARCADOR = "<!-- formato-fichero-apertura -->"


def _bloque_de_ejemplo() -> str:
    """El primer bloque cercado que sigue al marcador, sin las vallas ni la sangria."""
    texto = RUNBOOK.read_text(encoding="utf-8")
    assert texto.count(MARCADOR) == 1, f"{MARCADOR} debe aparecer exactamente una vez"
    tras = texto.split(MARCADOR, 1)[1]
    lineas = tras.splitlines()
    inicio = next(i for i, ln in enumerate(lineas) if ln.strip().startswith("```"))
    fin = next(i for i, ln in enumerate(lineas[inicio + 1:], inicio + 1)
               if ln.strip().startswith("```"))
    cuerpo = lineas[inicio + 1:fin]
    sangria = min((len(ln) - len(ln.lstrip()) for ln in cuerpo if ln.strip()), default=0)
    return "\n".join(ln[sangria:] for ln in cuerpo) + "\n"


def test_el_ejemplo_del_runbook_lo_entiende_el_lector(tmp_path):
    (tmp_path / "2026-09-14_W-02UDC1.md").write_text(_bloque_de_ejemplo(), encoding="utf-8")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert ilegibles == [], f"el RUNBOOK y el lector han divergido: {ilegibles}"
    assert len(pendientes) == 1
    _, caso, fecha = pendientes[0]
    assert caso and fecha


def test_el_runbook_nombra_los_tres_estados():
    # Un estado que el codigo acepta y el runbook no documenta es un estado que
    # nadie usara; uno que el runbook promete y el codigo no acepta es un fichero
    # que caera en «ilegible» sin que su autor entienda por que.
    texto = RUNBOOK.read_text(encoding="utf-8")
    for estado in sorted(sc._ESTADOS_APERTURA):
        assert f"`{estado}`" in texto, f"el RUNBOOK no documenta el estado {estado}"
```

- [ ] **Step 2: Correrlo y verificar que pasa**

```bash
python -m pytest tests/test_guard_formato_apertura.py -q --tb=short
```

Esperado: PASS, 2 tests.

- [ ] **Step 3: Verificar que el guard MUERDE (mutante manual)**

El guard recién escrito siempre pasa: no prueba nada hasta que se le ha visto ponerse rojo.
Cambiar temporalmente en `scripts/session_close.py` la línea
`if not lineas or lineas[0].strip() != "---":` por `if True:`, correr el guard, comprobar que
sale **rojo**, y **deshacer el cambio**.

```bash
python -m pytest tests/test_guard_formato_apertura.py -q --tb=line
```

Esperado con el mutante: FAIL con «el RUNBOOK y el lector han divergido». Tras deshacer: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_guard_formato_apertura.py
git commit -m "P8: un guard ata el formato del RUNBOOK al lector que lo interpreta"
```

---

### Task 5: (b) y (d) en `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md` (sección «Flujo de trabajo estándar», tras el bloque «Durante la sesión»;
  y la subsección «Cierre de sesión»)

**Interfaces:** ninguna. Documental.

- [ ] **Step 1: Añadir (b) tras «Durante la sesión»**

```markdown
### Apertura y reparación no se mezclan (P8 (b), decisión de Nikolai del 2026-09-13)

**Una sesión de apertura no toca el repo, y como mucho hay UNA sesión de reparación en
paralelo, que es la dueña del código.** La apertura anota los defectos que encuentra en
`%LOCALAPPDATA%\FeesDefender\aperturas\<AAAA-MM-DD>_<W-code>.md` y los ficha al cerrar, leyendo
`origin/main` al escribir; el detalle operativo está en `RUNBOOK_APERTURA_EXPEDIENTE.md`
`[APER-73]`, y `session_close` avisa de lo que quede sin fichar.

**Por qué está aquí y no solo en el runbook:** la sesión de reparación no está abriendo nada,
luego nunca lee el runbook de apertura. Una regla en el sitio equivocado no gobierna a nadie.

**La evidencia, medida:** las 838 líneas huérfanas de la fila #29 fueron una sesión de apertura
que se puso a reparar y dejó código sin commitear sobre una base 21 commits atrás — duplicando
algo que otra vía había construido un día después.
```

- [ ] **Step 2: Añadir (d) en «Cierre de sesión»**

Tras el párrafo que empieza «El cierre valida que la suite sigue verde…»:

```markdown
**Las aperturas del día van en UN bloque, no en un cierre numerado por caso** (P8 (d), decisión
de Nikolai del 2026-09-13). En `docs/bitacora/AAAA.md`, un solo bloque «aperturas del día» que
las narre todas, con sus W-codes y lo que quedó pendiente. El 101º cierre ya concluyó que un
cierre se cita por fecha y no por ordinal; numerar uno por expediente multiplica los ordinales
sin añadir información.
```

- [ ] **Step 3: Verificar que `CLAUDE.md` no rompe ningún guard de gobernanza**

```bash
python -m pytest tests/test_docs_gobernanza.py -q --tb=short
```

Esperado: PASS (sin cambio de conteo respecto a antes del commit).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "P8 (b) y (d): la regla vive donde gobierna, y las aperturas van en un bloque"
```

---

### Task 6: Tarea 0 — las filas #31 y #33 de `PLAN.md`

**Files:**
- Modify: `PLAN.md` (filas 31 y 33 de la cola priorizada, líneas ~47 y ~49)

**Interfaces:** ninguna. Documental.

- [ ] **Step 1: Cerrar la fila #33**

Sustituir en la fila 33 el texto `**construida, REVISADA EN TRES RONDAS y en PR [#371](https://github.com/TyukhayNi/FeesDefender/pull/371) — pendiente solo de MERGE**` por:

```markdown
✅ **CERRADA el 2026-09-14 (PR [#371](https://github.com/TyukhayNi/FeesDefender/pull/371), `6e7e3a6`), revisada en TRES rondas**
```

- [ ] **Step 2: Reescribir el estado de la fila #31**

Sustituir la celda de estado de la fila 31 (`sin construir — es proceso, y su sitio es
RUNBOOK_APERTURA_EXPEDIENTE.md + CLAUDE.md, no código`) por:

```markdown
**en curso — y DEJÓ de ser «proceso, no código» el 2026-09-14**: nada obligaba al «al final» de (a), que es el defecto más medido de la casa (un hecho escrito que nadie aplica, tres veces en cinco días), así que Nikolai decidió que `session_close` **avise** de las aperturas sin fichar — aviso, nunca verja. (a) va al `RUNBOOK` (`[APER-73]`) con el formato literal del fichero de trabajo; (b) y (d) a `CLAUDE.md`, porque la sesión de reparación no lee el runbook de apertura. El fichero vive en `%LOCALAPPDATA%\FeesDefender\aperturas\`, hogar que ya usa `workspace_registry`, porque lo escribe una sesión y lo lee **otra**, días después y en otro worktree. **(c) —el lote en serie— sigue APARCADO.** [spec](docs/superpowers/specs/2026-09-14-p8-apertura-no-toca-el-repo-design.md) · [plan](docs/superpowers/plans/2026-09-14-p8-apertura-no-toca-el-repo.md)
```

- [ ] **Step 3: Verificar la coherencia de `PLAN.md`**

```bash
python -m pytest tests/test_docs_gobernanza.py -q --tb=short
```

Esperado: PASS.

- [ ] **Step 4: Commit**

```bash
git add PLAN.md
git commit -m "docs(plan): la fila #33 estaba mergeada y decia pendiente; la #31 deja de ser solo proceso"
```

---

### Task 7: Verja de aceptación

- [ ] **Step 1: Correr la suite entera con las dos semillas**

```bash
python -m scripts.session_close
```

Esperado: verde con 777 y con 31337. **Cuadrar el conteo al test**: la referencia del 119º cierre
es **5.684 recogidos, 0 fallos, 94 skipped**; este plan añade **17** tests (11 + 4 + 2), luego lo
esperado es **5.701**. Cualquier otra cifra es bandera roja y se explica, no se normaliza.

- [ ] **Step 2: Comprobar que el aviso nuevo aparece en su propio cierre**

Con una raíz de prueba, verificar de punta a punta que el aviso habla:

```bash
FEESDEFENDER_APERTURAS="$TEMP/aperturas-prueba" python -c "import scripts.session_close as sc, os, pathlib; r=pathlib.Path(os.environ['FEESDEFENDER_APERTURAS']); r.mkdir(parents=True, exist_ok=True); (r/'2026-09-14_W-TEST.md').write_text('---\ncaso: W-TEST\nfecha: 2026-09-14\nestado: pendiente\n---\n', encoding='utf-8'); sc._avisar_aperturas_sin_fichar()"
```

Esperado: imprime la sección con `2026-09-14_W-TEST.md (W-TEST, 2026-09-14)`. Borrar la carpeta
de prueba después.

## Self-review del plan (hecho)

**Cobertura del spec:** §4 ruta → Task 1 (`raiz_aperturas_por_defecto`) y Task 3 (runbook). §5
contrato → Tasks 1 y 3. §6 lector y aviso, con los cuatro detalles → Tasks 1 y 2 (tests 7-10 del
fichero cubren `.md`/sin recursión, `caso:` ausente, normalización). §7 guard → Task 4. §8 los
diez casos → Tasks 1, 2 y 4. §9 docs → Tasks 3 y 5. §10 (c) no se construye: **ninguna tarea lo
menciona salvo para declararlo aparcado**. §11 ronda → fuera del plan, va al PR.

**Placeholders:** ninguno. Todo paso que cambia código lleva el código.

**Consistencia de tipos:** `_leer_aperturas` devuelve `(list[tuple[str,str,str]],
list[tuple[str,str]])` en la Task 1, y las Tasks 2 y 4 la consumen desempaquetando exactamente
eso. `_ESTADOS_APERTURA` se define en la Task 1 y la Task 4 lo lee.
