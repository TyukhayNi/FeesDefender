# Enumeración recursiva del atomizador (`MEJORAS #98`) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el atomizador de correo vea los `.eml` que `--extraer-adjuntos` deja en subcarpetas, y que una foto incompleta del correo nunca derive en borrado de fichas.

**Architecture:** El cambio vive en el **motor** (`core/email_atomize/`): la enumeración pasa a recursiva reportando lo que enumeró, leyó y falló; el dedup gana un desempate determinista; y la publicación se decide **en memoria antes de escribir**, con dos ramas según la naturaleza del fallo. El CLI (`scripts/sala_maquina.py`) pierde el andamio de la discrepancia, que queda sin premisa.

**Tech Stack:** Python 3.11+, `pytest` (+`pytest-randomly`), stdlib `os.walk`/`pathlib`, `typer` en el CLI.

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md` (**rev. 2**). No reabrir sus decisiones; su §11 registra la adjudicación de la revisión adversarial que las cerró.
- **Prime directive del motor: CERO MISATRIBUCIÓN.** Ningún cambio puede hacer que un mensaje se atribuya a quien no lo escribió. Ante la duda, no promover.
- **Byte-identidad de la Capa A, acotada (spec §4.2):** para todo caso actual —ninguno tiene `.eml` en subcarpeta— la salida debe ser **byte-idéntica**, y ningún `MSG-`/`ATT-` puede renumerarse. La promesa vale «mientras el conjunto de avistamientos no cambie».
- **`eml_origen` es probatorio y va al frontmatter; `eml_key` es la llave del registro y NO va al frontmatter.** No añadir campos a los dicts de `procedencia`: se renderizan, y añadir uno cambiaría el frontmatter de todos los atoms existentes.
- **Ceguera deliberada a `.EML` en mayúsculas**, simétrica entre el motor y el conteo del CLI: los dos deben medir lo mismo.
- **Fallo transitorio (lectura/enumeración) ⇒ no se publica nada. Fallo permanente (construcción A / Layer B) ⇒ se publica sin podar.** Ver spec §4.3.
- **Encoding:** UTF-8 explícito (`encoding="utf-8"`) en toda lectura/escritura de texto.
- **Comandos desde la raíz del worktree.** Suite completa antes del PR: el CI solo corre `leak-scan`, no pytest.
- **Commits acotados:** `git add <rutas>`, nunca `-A` ni `-u`.

---

## File Structure

| Fichero | Responsabilidad | Cambio |
|---|---|---|
| `core/email_atomize/extract.py` | Enumerar `.eml` y producir avistamientos | **Modificar:** enumeración recursiva vía `os.walk`, `EnumStats`, `eml_origen` relativo, `fuente`, retirada del parámetro muerto de `_ruta_de` |
| `core/email_atomize/dedup.py` | Colapsar avistamientos por identidad | **Modificar:** desempate determinista (`_desplaza`), `fuente` en el colapsado |
| `core/email_atomize/pipeline.py` | Orquestación end-to-end | **Modificar:** contadores en `AtomizeReport`, `eml_key`, las dos ramas de publicación, `contar_eml` a un solo entero |
| `scripts/sala_maquina.py` | Cableado del CLI | **Modificar:** retirar banner/guarda/`noop`-por-discrepancia; payload nuevo |
| `core/intake_log.py` | Vocabulario forense | **Modificar:** comentario de schema de `atomizado_email` |
| `tests/test_email_atomize_extract.py` | Contrato del enumerador | **Modificar:** recursión, origen relativo, fallos |
| `tests/test_email_atomize_dedup.py` | Contrato del colapso | **Modificar:** desempate |
| `tests/test_email_atomize_pipeline.py` | Contrato del motor e2e | **Modificar:** ramas de publicación, llave, contadores, `contar_eml` |
| `tests/test_sala_maquina_cableado_atomize.py` | Contrato del cableado | **Modificar:** retirar 5, invertir 1, simplificar 2, añadir 1 |
| `PLAN.md`, `docs/MEJORAS_FUTURAS.md`, `docs/ARQUITECTURA.md`, `.claude/skills/organizar-sala-maquina/SKILL.md` | Gobernanza y contrato operativo | **Modificar** (Task 7) |

---

### Task 1: Enumeración recursiva, con lo enumerado / leído / fallido declarado

**Files:**
- Modify: `core/email_atomize/extract.py:1-75`
- Test: `tests/test_email_atomize_extract.py`

**Interfaces:**
- Consumes: `core.email_export.{iter_nested_originals, message_id_of}` (ya importados).
- Produces:
  - `EnumStats` (dataclass: `enumerados: int = 0`, `leidos: int = 0`, `fallos: list[str]`)
  - `enumerar_rutas_eml(base: Path | str, stats: EnumStats | None = None) -> list[Path]` — orden determinista, recursivo, reporta directorios ilegibles
  - `iter_avistamientos(emails_dir, *, stats: EnumStats | None = None) -> Iterator[Avistamiento]` (firma retrocompatible: sin `stats` se comporta como hoy salvo por la recursión)
  - `Avistamiento` gana `fuente: str = ""`; `eml_origen` pasa a ser **ruta relativa POSIX a la base**

- [ ] **Step 1: Write the failing tests**

Añadir al final de `tests/test_email_atomize_extract.py`:

```python
def test_enumera_subcarpetas_con_origen_relativo(tmp_path):
    # El layout que deja `--extraer-adjuntos`: el .eml del mensaje CON adjunto baja a
    # su propia subcarpeta (MEJORAS #98).
    base = tmp_path / "2026-07-28_email_01"
    (base / "arras").mkdir(parents=True)
    (base / "suelto.eml").write_bytes(_eml("<a@x>", "Suelto"))
    (base / "arras" / "arras.eml").write_bytes(_eml("<b@x>", "Con adjunto"))

    stats = E.EnumStats()
    avs = list(E.iter_avistamientos(base, stats=stats))

    assert [a.eml_origen for a in avs] == ["arras/arras.eml", "suelto.eml"]
    assert {a.fuente for a in avs} == {"2026-07-28_email_01"}
    assert (stats.enumerados, stats.leidos, stats.fallos) == (2, 2, [])


def test_origen_de_nivel_superior_es_el_nombre_pelado(tmp_path):
    # Prueba de la byte-identidad: en un caso sin subcarpetas, `eml_origen` debe seguir
    # siendo exactamente lo que era antes del cambio (el nombre), o el frontmatter de
    # todos los atoms existentes cambiaría.
    base = tmp_path / "03_Email"
    base.mkdir()
    (base / "2026-06-12_a.eml").write_bytes(_eml("<a@x>", "Uno"))

    avs = list(E.iter_avistamientos(base))

    assert avs[0].eml_origen == "2026-06-12_a.eml"


def test_fallo_de_lectura_se_declara_y_no_aborta(tmp_path, monkeypatch):
    base = tmp_path / "03_Email"
    base.mkdir()
    (base / "bueno.eml").write_bytes(_eml("<a@x>", "Bueno"))
    (base / "malo.eml").write_bytes(_eml("<b@x>", "Malo"))

    real = Path.read_bytes

    def flaky(self):
        if self.name == "malo.eml":
            raise OSError("no hidratado en Drive")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", flaky)
    stats = E.EnumStats()
    avs = list(E.iter_avistamientos(base, stats=stats))

    assert [a.eml_origen for a in avs] == ["bueno.eml"]     # el bueno sigue saliendo
    assert (stats.enumerados, stats.leidos) == (2, 1)
    assert len(stats.fallos) == 1 and "malo.eml" in stats.fallos[0]


def test_fallo_al_enumerar_un_directorio_se_declara(tmp_path, monkeypatch):
    # `Path.rglob` silencia los errores de directorio; por eso la enumeración usa
    # `os.walk(onerror=...)`, que es el único punto donde se pueden ver.
    import os as _os
    base = tmp_path / "03_Email"
    (base / "prohibida").mkdir(parents=True)
    (base / "visible.eml").write_bytes(_eml("<a@x>", "Visible"))

    real_walk = _os.walk

    def walk_con_error(top, onerror=None, **kw):
        for tupla in real_walk(top, onerror=onerror, **kw):
            yield tupla
        if onerror is not None:
            exc = OSError("permiso denegado")
            exc.filename = str(base / "prohibida")
            onerror(exc)

    monkeypatch.setattr(_os, "walk", walk_con_error)
    stats = E.EnumStats()
    list(E.iter_avistamientos(base, stats=stats))

    assert any("prohibida" in f for f in stats.fallos)
```

Si el fichero no tiene ya un helper `_eml(mid, subj)` ni importa `E`/`Path`, añadir arriba:

```python
from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import extract as E


def _eml(mid: str, subj: str) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content("cuerpo")
    return m.as_bytes()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_email_atomize_extract.py -q
```

Expected: los 4 nuevos FAIL — `AttributeError: module 'core.email_atomize.extract' has no attribute 'EnumStats'` y, el de origen relativo, por `eml_origen` == nombre (que ya pasa) o por la recursión ausente.

- [ ] **Step 3: Write the implementation**

En `core/email_atomize/extract.py`, añadir `import os` a la cabecera y, tras la dataclass `Avistamiento`, insertar:

```python
@dataclass
class EnumStats:
    """Lo que la enumeración enumeró, leyó y no pudo leer (spec §4.3).

    `fallos` mezcla a propósito fichero-ilegible y directorio-ilegible: los dos son
    fallos TRANSITORIOS de la misma clase (sobre `G:` casi siempre es Drive sin
    hidratar) y los dos hacen incompleta la foto, que es lo que gobierna la decisión de
    publicar.
    """
    enumerados: int = 0
    leidos: int = 0
    fallos: list[str] = field(default_factory=list)


def enumerar_rutas_eml(base: Path | str, stats: EnumStats | None = None) -> list[Path]:
    """Rutas de los `.eml` bajo *base*, RECURSIVO y en orden determinista.

    Recursivo desde `MEJORAS #98`: `--extraer-adjuntos` deja el `.eml` de todo mensaje
    con adjuntos en una subcarpeta, y con `glob` esos mensajes eran invisibles sin error.

    Se usa `os.walk(onerror=...)` y no `Path.rglob` porque `rglob` **silencia** los
    errores de directorio: un directorio ilegible desaparecería igual que antes
    desaparecían las subcarpetas. Sensible a mayúsculas (`.eml`, no `.EML`) a propósito:
    el conteo del CLI mide lo mismo que esto, y los dos han de coincidir.
    """
    base = Path(base)

    def _onerror(exc: OSError) -> None:
        if stats is not None:
            stats.fallos.append(f"{getattr(exc, 'filename', base)}: {exc}")

    rutas: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(base, onerror=_onerror):
        d = Path(dirpath)
        rutas.extend(d / n for n in filenames if n.endswith(".eml"))
    return sorted(rutas)
```

Y **reemplazar** `iter_avistamientos` (líneas 51-70) por:

```python
def iter_avistamientos(emails_dir: Path | str, *,
                       stats: EnumStats | None = None) -> Iterator[Avistamiento]:
    base = Path(emails_dir)
    for eml in enumerar_rutas_eml(base, stats):
        if stats is not None:
            stats.enumerados += 1
        try:
            raw = eml.read_bytes()
        except OSError as exc:
            # NO se traga en silencio (spec §1.3): un .eml presente pero ilegible hacía
            # que el motor viera menos mensajes de los que hay y su poda borrara fichas
            # cuyo mensaje no había desaparecido.
            if stats is not None:
                stats.fallos.append(f"{eml.relative_to(base).as_posix()}: {exc}")
            continue
        if stats is not None:
            stats.leidos += 1
        # Ruta relativa, no `eml.name`: con subcarpetas el nombre deja de ser único.
        # POSIX para que el valor sea estable entre máquinas (se persiste en el
        # frontmatter y en `_registro.json`). Para un .eml de nivel superior la ruta
        # relativa ES el nombre → byte-identidad de todo lo existente (spec §4.2).
        origen = eml.relative_to(base).as_posix()
        yield Avistamiento(
            raw=raw, message_id=message_id_of(raw), eml_origen=origen, profundidad=0,
            fuente=base.name,
        )
        if b"message/rfc822" not in raw:
            continue
        cadenas = _ruta_de(raw)
        for child, _parent_mid in iter_nested_originals(raw):
            cmid = message_id_of(child)
            ruta = cadenas.get(cmid, [])
            yield Avistamiento(
                raw=child, message_id=cmid, eml_origen=origen,
                profundidad=max(1, len(ruta)), ruta_anidacion=ruta, fuente=base.name,
            )
```

Añadir `fuente: str = ""` al final de la dataclass `Avistamiento` (default para no romper construcciones existentes en tests), y cambiar la firma de `_ruta_de(raw: bytes, eml_origen: str)` a `_ruta_de(raw: bytes)` — su cuerpo **no usa** el segundo parámetro (verificado); es privado y tiene un único llamante.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_email_atomize_extract.py tests/test_email_atomize_dedup.py tests/test_email_atomize_pipeline.py -q
```

Expected: verde. Si algún test de pipeline falla por `eml_procesados` o por conteos, **anótalo y NO lo arregles aquí** — es Task 3; repórtalo en tus concerns.

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/extract.py tests/test_email_atomize_extract.py
git commit -m "feat(email_atomize): enumeracion recursiva con origen relativo y fallos declarados (#98)"
```

---

### Task 2: Desempate determinista en el colapso

Con la enumeración recursiva, «a igualdad de bytes gana el primero que llegó» pasa a depender del layout de carpetas. Este desempate lo vuelve explícito **sin cambiar el ganador en ningún caso actual**: hoy la secuencia de `eml_origen` es no decreciente (los ficheros se recorren en orden de ruta y los anidados heredan el origen del portador), así que el incumbente a igualdad de bytes es ya el origen lexicográficamente menor — que es exactamente lo que elige la regla nueva.

**Files:**
- Modify: `core/email_atomize/dedup.py:15-53`
- Test: `tests/test_email_atomize_dedup.py`

**Interfaces:**
- Consumes: `Avistamiento` con `fuente` y `eml_origen` relativo (Task 1).
- Produces: `MensajeColapsado` gana `fuente: str = ""`; helper privado `_desplaza(av, existente) -> bool`.

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_email_atomize_dedup.py` (usa el `_av`/helper que ya tenga el fichero; si construye `Avistamiento` a mano, pásale `fuente="03_Email"`):

```python
def test_a_bytes_iguales_gana_la_ruta_menos_enterrada():
    # El mismo Message-ID visto arriba y en subcarpeta, bytes idénticos: el canónico NO
    # puede depender del orden de enumeración (spec §4.2).
    raw = _eml("<a@x>", "Oferta")
    sub = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="arras/a.eml",
                       profundidad=0, fuente="lote")
    top = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="a.eml",
                       profundidad=0, fuente="lote")

    # en los dos órdenes de llegada gana el de nivel superior
    assert colapsar([sub, top])[0].eml_origen == "a.eml"
    assert colapsar([top, sub])[0].eml_origen == "a.eml"


def test_una_copia_de_menor_fidelidad_no_desplaza_al_canonico():
    grande = _eml("<a@x>", "Oferta", cuerpo="cuerpo largo " * 20)
    pequena = _eml("<a@x>", "Oferta")
    assert len(pequena) < len(grande)
    av_grande = Avistamiento(raw=grande, message_id="<a@x>", eml_origen="sub/a.eml",
                             profundidad=0, fuente="lote")
    av_pequena = Avistamiento(raw=pequena, message_id="<a@x>", eml_origen="a.eml",
                              profundidad=0, fuente="lote")

    # la de MÁS bytes gana aunque esté más enterrada: la fidelidad manda sobre la ruta
    assert colapsar([av_pequena, av_grande])[0].eml_origen == "sub/a.eml"
    assert colapsar([av_grande, av_pequena])[0].eml_origen == "sub/a.eml"


def test_las_dos_procedencias_se_conservan():
    raw = _eml("<a@x>", "Oferta")
    a = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="a.eml", profundidad=0,
                     fuente="lote")
    b = Avistamiento(raw=raw, message_id="<a@x>", eml_origen="arras/a.eml",
                     profundidad=0, fuente="lote")

    col = colapsar([a, b])[0]

    assert [p["eml_origen"] for p in col.procedencia] == ["a.eml", "arras/a.eml"]
    # los dicts de procedencia NO llevan `fuente`: se renderizan en el frontmatter y
    # añadir una clave cambiaría el .md de todos los atoms existentes
    assert set(col.procedencia[0]) == {"eml_origen", "profundidad", "ruta_anidacion"}
```

Si el fichero no tiene un `_eml(mid, subj, cuerpo=...)`, añádelo con el patrón de `tests/test_email_atomize_pipeline.py::_msg`.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_email_atomize_dedup.py -q
```

Expected: FAIL en el primero (hoy gana el primero que llega → `arras/a.eml` en un orden) y en el de `fuente` si `Avistamiento` aún no la acepta.

- [ ] **Step 3: Write the implementation**

En `core/email_atomize/dedup.py`, añadir `fuente: str = ""` al final de `MensajeColapsado` y **reemplazar** el bloque final de `colapsar` (líneas 38-53) por:

```python
        existente = por_clave.get(clave)
        if existente is None:
            por_clave[clave] = MensajeColapsado(
                message_id=av.message_id, raw=av.raw, eml_origen=av.eml_origen,
                profundidad=av.profundidad, ruta_anidacion=list(av.ruta_anidacion),
                procedencia=[proc], fuente=av.fuente,
            )
            continue
        existente.procedencia.append(proc)
        if _desplaza(av, existente):
            existente.raw = av.raw
            existente.eml_origen = av.eml_origen
            existente.profundidad = av.profundidad
            existente.ruta_anidacion = list(av.ruta_anidacion)
            existente.fuente = av.fuente
    return list(por_clave.values())


def _rango(origen: str) -> tuple[int, str]:
    """Orden de preferencia de un origen: menos enterrado primero, luego lexicográfico."""
    return (origen.count("/"), origen)


def _desplaza(av: Avistamiento, existente: MensajeColapsado) -> bool:
    """¿`av` debe sustituir al canónico actual?

    Fidelidad primero: más bytes = MIME más completo (regla original, intacta). A
    IGUALDAD de bytes NO decide el orden de llegada —que con enumeración recursiva
    depende del layout de carpetas— sino la ruta: gana la menos enterrada y, en empate,
    la lexicográficamente menor.

    Esto NO cambia el resultado de ningún caso actual: los ficheros se recorren en orden
    de ruta y los anidados heredan el origen de su portador, así que la secuencia de
    `eml_origen` es no decreciente y el incumbente ya era el origen menor. Lo que añade
    es que un mismo mensaje presente arriba y en subcarpeta tenga un canónico
    **determinista** (spec §4.2).
    """
    if len(av.raw) != len(existente.raw):
        return len(av.raw) > len(existente.raw)
    return _rango(av.eml_origen) < _rango(existente.eml_origen)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_email_atomize_dedup.py tests/test_email_atomize_regresion.py -q
```

Expected: verde. `test_email_atomize_regresion.py` es la red de no-regresión del motor: si algo se mueve ahí, para y repórtalo.

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/dedup.py tests/test_email_atomize_dedup.py
git commit -m "feat(email_atomize): desempate determinista del canonico (ruta, no orden de llegada)"
```

---

### Task 3: Contadores tipados en el informe y llave del registro con la fuente

Dos huecos que encontró la revisión adversarial: `eml_leidos` no tenía fuente de verdad (`report.mensajes` no vale — el dedup y los anidados rompen la igualdad «ficheros = atoms»), y la ruta relativa **a cada fuente** no hace única la llave del registro: `sub/a.eml` de dos fuentes distintas colapsaba en una sola entrada.

**Files:**
- Modify: `core/email_atomize/pipeline.py:31-52` (`AtomizeReport`) y `:93-112` (enumeración + `marcar_procesado`)
- Test: `tests/test_email_atomize_pipeline.py`

**Interfaces:**
- Consumes: `E.EnumStats`, `E.iter_avistamientos(..., stats=)` (Task 1); `MensajeColapsado.fuente` (Task 2).
- Produces: `AtomizeReport` gana `eml_enumerados: int = 0`, `eml_leidos: int = 0`, `fallos_lectura: list[str]`, `publicado: bool = True`, `poda_omitida: bool = False`. `Registro.marcar_procesado` recibe `f"{fuente}/{eml_origen}"`.

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_email_atomize_pipeline.py`:

```python
def test_llave_del_registro_no_colisiona_entre_fuentes(tmp_path):
    # `sub/a.eml` en dos fuentes distintas, mensajes DISTINTOS: el registro debe
    # distinguirlos (hallazgo 4 de la revisión adversarial).
    lote = tmp_path / "2026-07-28_email_01"
    legacy = tmp_path / "03_Email"
    (lote / "sub").mkdir(parents=True)
    (legacy / "sub").mkdir(parents=True)
    (lote / "sub" / "a.eml").write_bytes(_msg("<uno@x>", "Uno"))
    (legacy / "sub" / "a.eml").write_bytes(_msg("<dos@x>", "Dos"))
    out = tmp_path / "Emails"

    rep = P.atomize_dir([lote, legacy], out, case_dir=tmp_path)

    assert rep.mensajes == 2
    procesados = set(json.loads((out / "_registro.json").read_text(encoding="utf-8"))
                     ["eml_procesados"])
    assert procesados == {"2026-07-28_email_01/sub/a.eml", "03_Email/sub/a.eml"}


def test_eml_leidos_cuenta_ficheros_no_atoms(tmp_path):
    # Mata la implementación perezosa `eml_leidos = report.mensajes`: con dedup, dos
    # ficheros pueden dar un solo atom.
    src = tmp_path / "03_Email"
    src.mkdir()
    raw = _msg("<a@x>", "Oferta")
    (src / "copia_1.eml").write_bytes(raw)
    (src / "copia_2.eml").write_bytes(raw)

    rep = P.atomize_dir(src, tmp_path / "Emails", case_dir=tmp_path)

    assert (rep.eml_enumerados, rep.eml_leidos) == (2, 2)
    assert rep.mensajes == 1
    assert rep.publicado is True and rep.poda_omitida is False
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_email_atomize_pipeline.py -k "llave_del_registro or eml_leidos" -v
```

Expected: FAIL — `AttributeError: 'AtomizeReport' object has no attribute 'eml_enumerados'`, y el de la llave por `{'sub/a.eml'}` (una sola entrada).

- [ ] **Step 3: Write the implementation**

En `core/email_atomize/pipeline.py`, añadir a `AtomizeReport` tras `vistas_generadas`:

```python
    eml_enumerados: int = 0           # .eml que la enumeración produjo
    eml_leidos: int = 0               # de esos, los abiertos sin error
    fallos_lectura: list[str] = field(default_factory=list)   # ruta: motivo (transitorios)
    publicado: bool = True            # False si no se publicó nada (spec §4.3, rama transitoria)
    poda_omitida: bool = False        # True si se publicó sin podar (rama permanente)
```

Y en `atomize_dir`, sustituir la línea de enumeración (`:94`) y la de `marcar_procesado` (`:112`):

```python
    stats = E.EnumStats()
    avistamientos = [a for s in srcs for a in E.iter_avistamientos(s, stats=stats)]
    report.eml_enumerados = stats.enumerados
    report.eml_leidos = stats.leidos
    report.fallos_lectura = list(stats.fallos)
    colapsados = D.colapsar(avistamientos)
```

```python
        # Llave del registro: lleva la fuente delante porque la ruta relativa a CADA
        # fuente no es única (`sub/a.eml` puede existir en dos lotes). `eml_origen` se
        # queda como está: es el valor probatorio del frontmatter.
        reg.marcar_procesado(f"{col.fuente}/{col.eml_origen}" if col.fuente
                             else col.eml_origen)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_email_atomize_pipeline.py tests/test_email_atomize_ids.py -q
```

Expected: verde.

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_pipeline.py
git commit -m "feat(email_atomize): contadores tipados + llave de registro con la fuente"
```

---

### Task 4: Foto incompleta — fail-closed en el fallo transitorio, sin poda en el permanente

El corazón del cambio. Tres caminos dejan mensajes fuera del conjunto esperado y los tres hacían que la poda borrase fichas de mensajes que no habían desaparecido: lectura (Task 1), construcción de Capa A (`pipeline.py:104-109`) y reconstrucción de Layer B (`pipeline.py:183-188`). La rev. 1 solo cubría el primero.

**Files:**
- Modify: `core/email_atomize/pipeline.py:86-125` (mkdirs, decisión de publicación, poda)
- Test: `tests/test_email_atomize_pipeline.py`

**Interfaces:**
- Consumes: `report.fallos_lectura` y `report.errores` (Task 3).
- Produces: en la rama transitoria `atomize_dir` devuelve temprano con `publicado=False` **sin escribir nada**; en la permanente publica con `poda_omitida=True`. Dos constantes de nota: `_NOTA_NO_PUBLICADA`, `_NOTA_PODA_OMITIDA`.

- [ ] **Step 1: Write the failing tests**

```python
def test_fallo_de_lectura_no_publica_nada(tmp_path, monkeypatch):
    # Rama TRANSITORIA (Drive sin hidratar): la última publicación completa queda intacta.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)          # corrida completa previa
    antes = {p.name: p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert len(list((out / "mensajes").glob("*.md"))) == 2

    real = Path.read_bytes

    def flaky(self):
        if self.name == "b.eml":
            raise OSError("no hidratado")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", flaky)
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.publicado is False
    assert rep.fallos_lectura and "b.eml" in rep.fallos_lectura[0]
    assert any("NO PUBLICADA" in n for n in rep.notas)
    # nada se ha tocado: ni fichas, ni agregados, ni registro
    assert {p.name: p.read_bytes() for p in out.rglob("*") if p.is_file()} == antes


def test_fallo_de_construccion_publica_pero_no_poda(tmp_path, monkeypatch):
    # Rama PERMANENTE (.eml corrupto): se publica lo bueno y NO se borra la ficha del
    # que falló, para que un solo correo roto no bloquee el caso para siempre.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)
    fichas_antes = sorted(p.name for p in (out / "mensajes").glob("*.md"))
    assert len(fichas_antes) == 2

    real_construir = P._construir_mensaje

    def rompe_b(col, *a, **k):
        if col.message_id == "<b@x>":
            raise ValueError("cabecera imposible")
        return real_construir(col, *a, **k)

    monkeypatch.setattr(P, "_construir_mensaje", rompe_b)
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.publicado is True and rep.poda_omitida is True
    assert rep.errores and "cabecera imposible" in rep.errores[0]
    assert any("poda de mensajes/ OMITIDA" in n for n in rep.notas)
    # la ficha del que falló SOBREVIVE
    assert sorted(p.name for p in (out / "mensajes").glob("*.md")) == fichas_antes


def test_sin_fallos_si_poda(tmp_path):
    # Contrapartida imprescindible: la poda legítima sigue funcionando.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)
    assert len(list((out / "mensajes").glob("*.md"))) == 2

    (src / "b.eml").unlink()
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.poda_omitida is False and rep.publicado is True
    assert len(list((out / "mensajes").glob("*.md"))) == 1


def test_no_siembra_carpetas_si_no_publica(tmp_path, monkeypatch):
    # Sin árbol previo y con fallo de lectura: no se crean `mensajes/`/`adjuntos/`.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    out = tmp_path / "Emails"

    real = Path.read_bytes

    def falla_los_eml(self):
        # Acotado a `.eml`: parchear `read_bytes` a secas rompería cualquier otra
        # lectura binaria de la corrida y el test fallaría por la razón equivocada.
        if self.suffix == ".eml":
            raise OSError("no hidratado")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", falla_los_eml)
    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.publicado is False
    assert not (out / "mensajes").exists() and not (out / "adjuntos").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_email_atomize_pipeline.py -k "no_publica or no_poda or si_poda or no_siembra" -v
```

Expected: FAIL — hoy se publica siempre y se poda siempre; el de siembra falla porque los `mkdir` son incondicionales.

- [ ] **Step 3: Write the implementation**

Añadir las dos constantes tras `_idioma` en `core/email_atomize/pipeline.py`:

```python
_NOTA_NO_PUBLICADA = (
    "ATOMIZACIÓN NO PUBLICADA: {n} .eml no se pudieron leer (¿Drive sin hidratar?). "
    "El árbol anterior queda intacto. Re-lanza cuando estén disponibles."
)

_NOTA_PODA_OMITIDA = (
    "poda de mensajes/ OMITIDA: {n} mensajes no se pudieron construir; el árbol "
    "conserva fichas cuyo mensaje no se ha reconstruido en esta corrida."
)
```

**Mover** los dos `mkdir` (`:89-90`) para que no corran antes de la decisión: bórralos de ahí y ponlos justo antes del bucle de escritura de `mensajes/`.

Insertar la decisión **después** del pase de Layer B (`:116`, tras `mensajes.extend(mensajes_b)`) y **antes** del bucle de escritura:

```python
    # --- Decisión de publicación (spec §4.3): en memoria, ANTES de escribir nada ---
    # Transitorio (lectura/enumeración): fail-closed. Sobre `G:` casi siempre es Drive
    # sin hidratar y re-correr lo resuelve; publicar con la foto incompleta borraría
    # fichas cuyo mensaje sigue existiendo.
    if report.fallos_lectura:
        report.publicado = False
        report.notas.append(_NOTA_NO_PUBLICADA.format(n=len(report.fallos_lectura)))
        return report

    (out / "mensajes").mkdir(parents=True, exist_ok=True)
    (out / "adjuntos").mkdir(parents=True, exist_ok=True)

    for m in mensajes:
        (out / "mensajes" / R.nombre_md(m)).write_text(R.render_md(m), encoding="utf-8")
    # Permanente (construcción A / Layer B): se publica lo bueno, pero NO se poda — un
    # `.eml` corrupto no se arregla re-corriendo, y bloquear el caso para siempre es peor
    # que conservar una ficha rancia. La poda solo retira huérfanos cuando la foto está
    # completa (p. ej. un mensaje B superado por un upgrade).
    if report.errores:
        report.poda_omitida = True
        report.notas.append(_NOTA_PODA_OMITIDA.format(n=len(report.errores)))
    else:
        esperados = {R.nombre_md(m) for m in mensajes}
        for p in (out / "mensajes").glob("*.md"):
            if p.name not in esperados:
                p.unlink()
```

(El `for m in mensajes: … write_text(…)` y el bloque de poda originales de `:118-125` quedan sustituidos por lo de arriba.)

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_email_atomize_pipeline.py tests/test_email_atomize_pipeline_b.py tests/test_email_atomize_pipeline_f3.py tests/test_email_atomize_regresion.py tests/test_email_atomize_regresion_b.py -q
```

Expected: verde. Ojo al orden: `report.errores` recibe el error de `vistas.yaml` **después** de este punto (`:167`), así que una config de vistas inválida no debe apagar la poda — si algún test de vistas cambia de comportamiento, es un bug de tu implementación.

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_pipeline.py
git commit -m "feat(email_atomize): fail-closed ante fallo de lectura; sin poda ante fallo de construccion"
```

---

### Task 5: `contar_eml` a un solo criterio y retirada del andamio del CLI

Con la ceguera cerrada, la discrepancia `n_rec > n_top` no puede darse: el banner, la guarda y el `noop`-por-discrepancia quedan sin premisa, y el texto del banner («el atomizador NO los verá») pasaría a ser **falso**.

**Files:**
- Modify: `core/email_atomize/pipeline.py:307-330` (`contar_eml`)
- Modify: `scripts/sala_maquina.py` (constantes, `_atomizar_correo`, `plan`)
- Modify: `core/intake_log.py` (comentario de schema)
- Test: `tests/test_email_atomize_pipeline.py`, `tests/test_sala_maquina_cableado_atomize.py`

**Interfaces:**
- Consumes: `E.enumerar_rutas_eml` (Task 1); `report.{publicado,poda_omitida,eml_enumerados,eml_leidos,fallos_lectura}` (Tasks 3-4).
- Produces: `contar_eml(fuentes) -> int`. Payload del evento `atomizado_email`:
  `{"details_schema": 2, "status": ok|parcial|fallo|noop, "eml_en_disco": int, "eml_leidos": int, "publicado": bool, "poda_omitida": bool, "mensajes"…, "notas", "errores", "fallos_lectura"}`.

- [ ] **Step 1: Write the failing tests**

En `tests/test_email_atomize_pipeline.py`, **sustituir** los dos tests de `contar_eml` (asertan tuplas) por:

```python
def test_contar_eml_cuenta_tambien_las_subcarpetas(tmp_path):
    src = tmp_path / "2026-07-28_email_01"
    (src / "arras").mkdir(parents=True)
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "arras" / "b.eml").write_bytes(_msg("<b@x>", "Dos"))

    assert P.contar_eml([src]) == 2


def test_contar_eml_suma_fuentes_y_tolera_inexistentes(tmp_path):
    lote = tmp_path / "2026-07-28_email_01"
    legacy = tmp_path / "03_Email"
    lote.mkdir()
    legacy.mkdir()
    (lote / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (legacy / "b.eml").write_bytes(_msg("<b@x>", "Dos"))

    assert P.contar_eml([lote, legacy, tmp_path / "no_existe"]) == 2
    assert P.contar_eml([]) == 0
```

En `tests/test_sala_maquina_cableado_atomize.py`:

- **Borrar** estos 5, cuya premisa desaparece: `test_noop_con_discrepancia_emite_evento_noop`, `test_arbol_previo_con_discrepancia_total_no_llama_al_motor`, `test_arbol_previo_con_discrepancia_parcial_no_llama_al_motor`, `test_aviso_cuando_hay_eml_en_subcarpetas`, `test_sin_discrepancia_no_hay_aviso`.
- **Invertir** `test_motor_real_solo_ve_el_nivel_superior` → renombrar a `test_motor_real_ve_las_subcarpetas` y sustituir su cuerpo:

```python
def test_motor_real_ve_las_subcarpetas(caso, monkeypatch, capsys):
    # El arreglo de #98 contra el motor REAL: el .eml de la subcarpeta ya se atomiza.
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    (src / "a.eml").write_bytes(_eml("<a@x>", "Visible"))
    (src / "arras").mkdir()
    (src / "arras" / "b.eml").write_bytes(_eml("<b@x>", "AntesInvisible"))

    cli.apply("W-TEST99")

    d = _evento(eventos)[0]
    assert d["status"] == "ok" and d["publicado"] is True
    assert (d["eml_en_disco"], d["eml_leidos"]) == (2, 2)
    assert d["mensajes"] == 2
    mds = list((case_dir / "01_Procesado" / "Emails" / "mensajes").glob("*.md"))
    assert len(mds) == 2
    assert any("AntesInvisible" in p.read_text(encoding="utf-8") for p in mds)
```

- **Simplificar** `test_plan_no_atomiza_pero_informa_y_avisa`: quitar la aserción del banner en stderr y **cambiar el recuento de 2 a 3** (su fixture tiene 2 arriba y 1 en subcarpeta, y ahora se cuentan los tres); conservar que no llama al motor y que no crea `01_Procesado/Emails`.
- **Cambiar también** `test_fallo_del_motor_no_aborta_el_ocr_y_emite_evento`: asserta el dict exacto de la rama de excepción, que llevaba las claves viejas. Pasa a:

```python
    assert _evento(eventos)[0] == {
        "details_schema": 2, "status": "fallo", "eml_en_disco": 1,
        "errores": ["RuntimeError: motor roto"],
    }
```

(La rama de excepción sigue sin fabricar contadores: si el motor no terminó, el payload no finge saber cuántos mensajes hay ni si publicó.)

- **Cambiar** `test_payload_atado_a_los_campos_reales_del_report` a la igualdad exacta con el payload nuevo:

```python
    assert _evento(eventos)[0] == {
        "details_schema": 2, "status": "ok",
        "eml_en_disco": 1, "eml_leidos": 1, "publicado": True, "poda_omitida": False,
        "mensajes": 413, "adjuntos_unicos": 162, "reconstruidos_b": 136,
        "citas_a_revision": 43, "upgrades": 8,
        "notas": ["W-code ajeno en 1 mensaje: W-00000"], "errores": [], "fallos_lectura": [],
    }
```

- **Añadir** el test de la rama transitoria vista desde el cableado:

```python
def test_evento_declara_que_no_publico(caso, monkeypatch):
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(
        eml_enumerados=1, eml_leidos=0, publicado=False,
        fallos_lectura=["a.eml: no hidratado"],
        notas=["ATOMIZACIÓN NO PUBLICADA: 1 .eml no se pudieron leer…"]))

    cli.apply("W-TEST99")

    d = _evento(eventos)[0]
    assert d["status"] == "fallo" and d["publicado"] is False
    assert d["fallos_lectura"] == ["a.eml: no hidratado"]
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_email_atomize_pipeline.py tests/test_sala_maquina_cableado_atomize.py -q
```

Expected: FAIL en los de `contar_eml` (tupla vs int), en el invertido (hoy el motor ve 1) y en los de payload.

- [ ] **Step 3: Write the implementation**

**(a)** En `core/email_atomize/pipeline.py`, sustituir `contar_eml` entero por:

```python
def contar_eml(fuentes: Iterable[Path | str]) -> int:
    """Cuántos `.eml` verá el motor, con SU MISMO criterio (recursivo).

    Reutiliza `extract.enumerar_rutas_eml` en vez de reimplementar el recorrido: así el
    conteo del CLI y la enumeración del motor no pueden derivar (era el defecto que
    `MEJORAS #98` volvió visible). Solo sirve para decidir el no-op del cableado: «¿hay
    correo?». La discrepancia entre lo que hay y lo que se pudo leer la declara el motor
    en `eml_enumerados`/`eml_leidos`, no este conteo.
    """
    return sum(len(E.enumerar_rutas_eml(f)) for f in fuentes if Path(f).is_dir())
```

**(b)** En `scripts/sala_maquina.py`: **borrar** la constante `_AVISO_EML_INVISIBLE` completa, y sustituir en `_atomizar_correo` el bloque que va desde `n_top, n_rec = …` hasta el `return` del segundo guarda por:

```python
    n = atomize.contar_eml(fuentes)

    # No-op estricto: sin correo Y sin árbol previo no se llama al motor — `atomize_dir`
    # crearía `mensajes/`/`adjuntos/` y sembraría carpetas vacías en todo caso sin
    # correo. Con árbol previo SÍ se llama, para que la retirada genuina se refleje.
    if n == 0 and not out.exists():
        return

    details: dict[str, object] = {"details_schema": 2, "eml_en_disco": n}
```

y en la rama `else` del `try`, sustituir el `details.update({...})` por:

```python
        details["status"] = ("fallo" if not report.publicado
                             else "parcial" if report.errores else "ok")
        details.update({
            "eml_leidos": report.eml_leidos,
            "publicado": report.publicado,
            "poda_omitida": report.poda_omitida,
            "mensajes": report.mensajes,
            "adjuntos_unicos": report.adjuntos_unicos,
            "reconstruidos_b": report.reconstruidos_b,
            "citas_a_revision": report.citas_a_revision,
            "upgrades": report.upgrades,
            "notas": list(report.notas),
            "errores": list(report.errores),
            "fallos_lectura": list(report.fallos_lectura),
        })
```

En `plan`, sustituir las tres líneas del preview por:

```python
    n = atomize.contar_eml(atomize.emails_src_dirs_de_caso(case_dir))
    if n:
        typer.echo(f"  correo: {n} .eml (se atomizarán en apply)")
```

**(c)** En `core/intake_log.py`, sustituir el comentario del evento `atomizado_email` por:

```python
    "atomizado_email",          # atomización de correo encadenada por la sala de máquina.
                                 # details_schema 2: {"status": ok|parcial|fallo|noop,
                                 # "eml_en_disco", "eml_leidos", "publicado",
                                 # "poda_omitida", + contadores del AtomizeReport si el
                                 # motor terminó}. `noop` solo lleva status y eml_en_disco.
                                 # NO lleva "files". Sin `details_schema`: forma 1 (claves
                                 # `eml_nivel_superior`/`eml_totales`, retiradas en #98).
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_email_atomize_pipeline.py tests/test_sala_maquina_cableado_atomize.py tests/test_sala_maquina_ejecutar.py tests/test_intake_log.py -q
```

Expected: verde, con 15 tests en el fichero del cableado (19 − 5 + 1).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/pipeline.py scripts/sala_maquina.py core/intake_log.py tests/test_email_atomize_pipeline.py tests/test_sala_maquina_cableado_atomize.py
git commit -m "refactor(sala_maquina): retira el andamio de la discrepancia; payload schema 2"
```

---

### Task 6: Death tests de integración

Los que no caben en una sola pieza porque cruzan enumeración, dedup y publicación. Son los que pidió la revisión adversarial: sin ellos, una implementación que cumpla cada tarea por separado puede seguir violando las invariantes probatorias.

**Files:**
- Test: `tests/test_email_atomize_enumeracion_recursiva.py` (crear)

**Interfaces:**
- Consumes: todo lo anterior. No añade código de producción.

- [ ] **Step 1: Write the tests**

```python
"""Death tests de la enumeración recursiva (`MEJORAS #98`, spec §6 tests 12-13).

Cruzan enumeración + dedup + publicación: cada tarea puede estar bien por separado y
estas invariantes seguir roras. Los cinco escenarios los pidió la revisión adversarial
del diseño.
"""
from __future__ import annotations

import json
from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import pipeline as P


def _msg(mid: str, subj: str, cuerpo: str = "cuerpo") -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content(cuerpo)
    return m.as_bytes()


def _fichas(out: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in (out / "mensajes").glob("*.md")}


def test_todos_los_eml_en_subcarpetas_se_atomizan(tmp_path):
    # Recupera la cobertura que se pierde al retirar los tres tests de la guarda: el
    # caso típico de `--extraer-adjuntos` es que TODOS los mensajes traigan adjunto.
    src = tmp_path / "2026-07-28_email_01"
    for i, mid in enumerate(("<a@x>", "<b@x>", "<c@x>"), start=1):
        d = src / f"msg_{i}"
        d.mkdir(parents=True)
        (d / f"msg_{i}.eml").write_bytes(_msg(mid, f"Asunto {i}"))
    out = tmp_path / "Emails"

    rep = P.atomize_dir(src, out, case_dir=tmp_path)

    assert rep.mensajes == 3 and rep.eml_leidos == 3
    assert len(_fichas(out)) == 3


def test_transicion_top_only_a_mixta_con_copia_igual_no_cambia_el_canonico(tmp_path):
    # Death test del hallazgo 1 de la revisión: aparece una copia en subcarpeta con
    # bytes IDÉNTICOS → el canónico NO se mueve; la ficha solo gana la procedencia nueva.
    src = tmp_path / "03_Email"
    src.mkdir()
    raw = _msg("<a@x>", "Oferta")
    (src / "oferta.eml").write_bytes(raw)
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)
    antes = _fichas(out)
    assert len(antes) == 1

    (src / "copia").mkdir()
    (src / "copia" / "oferta.eml").write_bytes(raw)
    P.atomize_dir(src, out, case_dir=tmp_path)

    despues = _fichas(out)
    assert list(despues) == list(antes)                    # mismo nombre de ficha
    md = next(iter(despues.values()))
    assert 'eml_origen: "oferta.eml"' in md                # canónico intacto
    assert "copia/oferta.eml" in md                        # procedencia nueva registrada


def test_transicion_a_copia_mayor_cambia_el_canonico_declaradamente(tmp_path):
    # La otra mitad: con MÁS bytes la copia sí gana. Se fija como comportamiento
    # declarado (la fidelidad manda), no accidental.
    src = tmp_path / "03_Email"
    src.mkdir()
    (src / "oferta.eml").write_bytes(_msg("<a@x>", "Oferta"))
    out = tmp_path / "Emails"
    P.atomize_dir(src, out, case_dir=tmp_path)

    (src / "copia").mkdir()
    (src / "copia" / "oferta.eml").write_bytes(_msg("<a@x>", "Oferta", cuerpo="c " * 200))
    P.atomize_dir(src, out, case_dir=tmp_path)

    md = next(iter(_fichas(out).values()))
    assert 'eml_origen: "copia/oferta.eml"' in md


def test_idempotente_con_subcarpetas(tmp_path):
    src = tmp_path / "03_Email"
    (src / "arras").mkdir(parents=True)
    (src / "a.eml").write_bytes(_msg("<a@x>", "Uno"))
    (src / "arras" / "b.eml").write_bytes(_msg("<b@x>", "Dos"))
    out = tmp_path / "Emails"

    P.atomize_dir(src, out, case_dir=tmp_path)
    primera = _fichas(out)
    reg1 = (out / "_registro.json").read_text(encoding="utf-8")
    P.atomize_dir(src, out, case_dir=tmp_path)

    assert _fichas(out) == primera                          # byte-idéntico
    assert (out / "_registro.json").read_text(encoding="utf-8") == reg1   # 0 renumeraciones


def test_capa_a_byte_identica_sin_subcarpetas(tmp_path):
    # La invariante que protege todo caso actual: mismo input top-only ⇒ misma salida.
    # Es la versión sintética del paso 3 de la verificación en vivo (spec §7).
    src = tmp_path / "03_Email"
    src.mkdir()
    for i, mid in enumerate(("<a@x>", "<b@x>", "<c@x>"), start=1):
        (src / f"m{i}.eml").write_bytes(_msg(mid, f"Asunto {i}"))
    out = tmp_path / "Emails"

    P.atomize_dir(src, out, case_dir=tmp_path)
    fichas = _fichas(out)
    ids = json.loads((out / "_registro.json").read_text(encoding="utf-8"))["mensajes"]

    assert len(fichas) == 3
    assert all('eml_origen: "m' in md for md in fichas.values())   # nombre pelado
    assert sorted(e["id"] for e in ids.values()) == ["MSG-00001", "MSG-00002", "MSG-00003"]
```

- [ ] **Step 2: Run the tests**

```bash
python -m pytest tests/test_email_atomize_enumeracion_recursiva.py -q
```

Expected: 5 PASSED. **Si alguno falla, es un HALLAZGO, no ruido:** diagnostica la causa raíz antes de tocar una aserción (`superpowers:systematic-debugging`) y repórtala. Estos tests son la red que la revisión adversarial pidió precisamente porque el resto del contrato podía pasar sobre invariantes rotas.

- [ ] **Step 3: Commit**

```bash
git add tests/test_email_atomize_enumeracion_recursiva.py
git commit -m "test(email_atomize): death tests de integracion de la enumeracion recursiva"
```

---

### Task 7: Documentación, suite completa y cierre de `MEJORAS #98`

**Files:**
- Modify: `docs/MEJORAS_FUTURAS.md` (`#98`), `PLAN.md` (bloque `[SIGUIENTE-CABLEADO-CORREO]`), `.claude/skills/organizar-sala-maquina/SKILL.md`, `docs/ARQUITECTURA.md`

- [ ] **Step 1: Cerrar `MEJORAS #98`**

Al principio de la entrada `## 98.`, añadir:

```markdown
> ✅ **CERRADO (PR #NNN, `<hash del merge>`).** Enumeración recursiva en el motor
> (`enumerar_rutas_eml` vía `os.walk`, que no silencia los directorios ilegibles como sí hace
> `rglob`), `eml_origen` = ruta relativa POSIX, llave del registro con la fuente delante, y la
> foto incompleta ya no borra fichas: fallo de lectura/enumeración → **no se publica nada**;
> fallo de construcción → se publica **sin podar**. Se retiró el andamio del PR #151 (banner,
> guarda del CLI y `noop`-por-discrepancia), sin pérdida de cobertura: la tabla del §5 de la
> spec la compara escenario por escenario. Spec:
> `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md`.
> **Sigue fuera:** `.EML` en mayúsculas y una carpeta fuente que `emails_src_dirs_de_caso` no
> devuelva — ninguna de las dos la cubría tampoco la guarda vieja.
```

Y borrar de esa entrada el párrafo «**Mitigación YA EN MAIN (no es el arreglo)**» y el «**Segundo motivo por el que `#98` bloquea la casilla 3**», que dejan de ser ciertos.

- [ ] **Step 2: `PLAN.md`**

En el bloque `[SIGUIENTE-CABLEADO-CORREO]`, la casilla 3 pasa de ⛔ a decidible:

```markdown
- [ ] **DECIDIBLE** (ya no bloqueada: `MEJORAS #98` cerrado en PR #NNN) — decidir si
  `--extraer-adjuntos` pasa a default `True`. El motor ya ve los `.eml` de las subcarpetas, así
  que activarlo no genera ceguera. Gate antes de encenderlo: la corrida de control del §7 de la
  spec de `#98` (export real de una etiqueta pequeña a scratch), porque activarlo mueve la
  superficie de dedup de todo intake futuro.
```

Y en la fila 11 de la cola: estado `casillas 1-2 ✅; casilla 3 decidible (#98 cerrado)`.

- [ ] **Step 3: `SKILL.md` de `organizar-sala-maquina`**

Sustituir el gotcha que hoy dice que `apply` avisa de los `.eml` invisibles por:

```markdown
- **La atomización ve todo el correo, y si no puede verlo NO borra nada.** `apply` atomiza los
  `.eml` de los lotes `email` y de `03_Email` **incluidas las subcarpetas** (`MEJORAS #98`,
  cerrado). Si algún `.eml` no se puede **leer** —típico de Drive sin hidratar— no publica nada,
  deja el árbol anterior intacto y avisa: re-lanza cuando estén disponibles. Si un mensaje no se
  puede **construir** (`.eml` corrupto), publica el resto pero **no poda**, así que puede quedar
  alguna ficha rancia; el evento lo declara con `poda_omitida`. El árbol sigue sin garantizar
  frescura de `adjuntos/` (`MEJORAS #99`), y el contenido de los adjuntos sigue fuera de la sala
  de máquina (`MEJORAS #87`).
```

- [ ] **Step 4: `docs/ARQUITECTURA.md`**

En la fila de `core/email_atomize/`, añadir al contrato de salida: `eml_origen` = ruta relativa POSIX a la carpeta fuente (para un `.eml` de nivel superior, el nombre pelado); llave de `eml_procesados` = `<fuente>/<eml_origen>`; `AtomizeReport` declara `eml_enumerados`/`eml_leidos`/`publicado`/`poda_omitida`.

- [ ] **Step 5: Suite completa y leak-scan**

```bash
python -m pytest -q --tb=short --junit-xml=%TEMP%\fd_98.xml
```

Expected: 0 failures, 0 errors. El resumen de pytest no se captura fiable por tuberías en Windows: el conteo autoritativo está en el JUnit XML. Y:

```bash
pre-commit run --all-files
```

Expected: `leak-scan` verde.

- [ ] **Step 6: Commit**

```bash
git add docs/MEJORAS_FUTURAS.md PLAN.md .claude/skills/organizar-sala-maquina/SKILL.md docs/ARQUITECTURA.md
git commit -m "docs: cierra MEJORAS #98 y desbloquea la casilla 3 del cableado de correo"
```

---

### Task 8 (operativa, NO para subagente): verificación en vivo

La ejecuta el controlador **con Nikolai delante**: toca correo real y, en el paso 3, escribe en `G:`. Un subagente no debe lanzarla.

- [ ] **Paso 1 — export de control a scratch.** El CLI `scripts/export_label_emails.py` **no sirve**: exige `--ref` y deriva el destino con `email_dest_dir(case_id)`, así que escribe dentro del expediente. Se llama al motor directamente, con `case_id=None` para que no emita `upload_email` ni registre hashes en ningún caso:

```python
from pathlib import Path
from core.email_export import export_label
rep = export_label("<cuenta>", "<etiqueta pequeña>", Path(r"%TEMP%\scratch_98"),
                   case_id=None, extract_attachments=True)
print(rep.messages, rep.attachments)
```

- [ ] **Paso 2 — atomizar ese scratch y comprobar.** `python -m scripts.atomize_emails --src <scratch> --out <scratch_out>`. Verificar: los mensajes con adjunto **aparecen**; su `eml_origen` es la ruta relativa; el remitente de cada uno es **literal** del `.eml` (cero misatribución); y una segunda corrida no cambia nada.
- [ ] **Paso 3 — no-regresión de W-02VND1, SOLO con autorización expresa de Nikolai en el momento.** Snapshot de hashes de los 277 `.md` antes, `atomize_case('W-02VND1')`, snapshot después: **byte-idénticos** y **0 IDs renumerados**. Patrón: `scripts/_verify_live_it3.py`. Demuestra solo «input top-only inalterado ⇒ salida idéntica»; el resto vive en los death tests de la Task 6.

---

## Revisión adversarial antes del PR

Por `CLAUDE.md`, la revisión adversarial del código se delega y **Claude adjudica**. `agy` estaba sin cupo al escribir este plan; si sigue seco, va a Codex, en solo lectura y sin escribir en el repo. Los puntos donde más rendiría, por orden: (1) que la byte-identidad de la Capa A se sostenga en la implementación real, no solo en los tests; (2) que la rama transitoria no publique **nada** (ni un `mkdir`); (3) que la poda siga funcionando cuando la foto está completa; (4) que `eml_key` no se filtre al frontmatter.
