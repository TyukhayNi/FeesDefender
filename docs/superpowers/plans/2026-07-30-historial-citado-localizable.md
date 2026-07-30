# El historial citado, localizable — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**SPEC (fuente única del diseño, no reabrir sus decisiones):**
`docs/superpowers/specs/2026-07-30-historial-citado-localizable-design.md`.

**Goal:** que el historial citado que `cortar_autor` retira del cuerpo de una ficha quede
**localizable** en un fichero hermano `mensajes/<atom>.historial.md`, verbatim y con los duplicados
marcados, **sin atribuir nada a nadie y sin reescribir ninguna ficha existente**.

**Architecture:** un módulo puro nuevo (`core/email_atomize/historial.py`) que parte el texto en
frases sustanciales, construye un índice `frase → fichas que la contienen` y renderiza el `.md`;
más tres puntos de cableado en `pipeline.py`. La Capa A no se toca: el flag `conservar_resto` de
`extraer_cuerpo` es puramente aditivo, y el artefacto es un fichero **nuevo**.

**Tech Stack:** Python 3.14, stdlib (`re`), pytest. Sin dependencias nuevas.

## Global Constraints

- **Entorno: Windows + PowerShell.** Intérprete:
  `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe` (ruta absoluta; los worktrees no tienen
  `.venv` propio). `cwd` en el worktree.
- **Nunca rutas relativas con las APIs estáticas de `.NET`** (`[System.IO.File]::ReadAllText`): se
  resuelven contra el CWD del **proceso**, no contra `$PWD`, y ya provocaron una escritura en la raíz
  compartida. Para mutar ficheros en un arnés, usar Python.
- **Encoding UTF-8 sin BOM**; en Python, `encoding="utf-8"` explícito.
- **`main` está protegida.** Trabajo en la rama actual, entra por PR, nunca commit directo.
- **La Capa A es byte-idéntica.** Ninguna ficha `.md` existente se reescribe. Si
  `test_capa_a_byte_identica_contra_golden` se pone rojo, el cambio es inaceptable — **no** el golden.
- **Prime directive: cero misatribución.** Nada de este artefacto afirma quién escribió qué: sin `de`,
  sin fecha, sin remitente inferido. Es la diferencia con la Capa B, que sí atribuye y por eso exige
  cabecera parseable.
- **Ningún test vacuo.** Por cada test, qué defecto concreto mata. Este motor lleva **cinco** tests
  vacuos encontrados, uno de ellos descubierto porque al mutar el código **no moría ninguno**: cada
  tarea termina con *mutation testing* de sus propios tests.
- **Nada de nombres propios de terceros ni direcciones reales** en código, tests, docs o mensajes de
  commit: los fixtures usan `@example.invalid`. La blocklist de PII **no existe en los worktrees**
  (vive en `data/_saneado/` y `data/_config/`, gitignored), así que el hook local **no comprueba PII
  ahí**: verificar antes de pushear cargando la lista de la raíz con la regex del guard (límites de
  palabra + IGNORECASE, ver `scripts/precommit_leak_guard.py::escanear`).
- **Mensajes de commit en castellano y sin tildes** (convención del repo).
- **Comando de suite:** `python -m pytest -q --tb=short`, conteo por `--junit-xml` (el resumen no
  sobrevive a las tuberías de PowerShell). Punto de partida: **2566 tests, 0 failures, 0 errors,
  77 skipped** sobre `5076823`.
- **El CI del PR solo corre `leak-scan`, NO pytest.** La suite local es la única red.

---

## Estructura de ficheros

| Fichero | Responsabilidad | Tarea |
|---|---|---|
| `core/email_atomize/historial.py` | **nuevo, puro** — partir en frases sustanciales, índice `frase → MSG-ids`, renderizar el `.md` | 1 |
| `core/email_atomize/render.py` | gana `nombre_historial(m)`, junto a `nombre_md(m)`: es la misma responsabilidad (nombrar artefactos) | 1 |
| `tests/test_email_atomize_historial.py` | **nuevo** — unitarios del módulo puro | 1 |
| `core/email_atomize/pipeline.py` | tres puntos de cableado + el arreglo de la poda | 2, 3 |
| `tests/test_email_atomize_historial_pipeline.py` | **nuevo** — integración contra `atomize_dir` | 2, 3 |
| `docs/MEJORAS_FUTURAS.md` | `#105` cerrada, `#109` con su pieza 1 hecha | 4 |

**Lo que NO se toca, y por qué:**

- `core/email_atomize/bodies.py` — `conservar_resto` **ya existe** y ya expone `resto_citado`. Solo
  hay que pasar el flag.
- La atribución (`inline.py`, `clasificar`, la Capa B): este artefacto no atribuye.
- `core/email_atomize/entregas.py` — `SET_ENTREGABLE` incluye `"mensajes"` como **directorio** y
  `sellar` hace `copytree`, así que los historiales entran solos en la entrega y en su lista de sha.

---

### Task 1: El módulo puro `historial.py`

**Files:**
- Create: `core/email_atomize/historial.py`
- Create: `tests/test_email_atomize_historial.py`
- Modify: `core/email_atomize/render.py` (añadir `nombre_historial`, justo después de `nombre_md`,
  línea 16)

**Interfaces:**
- Consumes: `core.email_atomize.inline.normaliza_cuerpo(texto) -> str` (el normalizador único que ya
  gobierna los fingerprints); `RegistroMensaje.cuerpo` y `.msg_id` (`model.py:67,40`).
- Produces, y lo consume la Tarea 2:
  - `frases_sustanciales(texto: str) -> list[str]`
  - `indice_frases(mensajes: list) -> dict[str, list[str]]`
  - `render_historial(*, portador_msg_id: str, nombre_ficha: str, resto_citado: str, indice: dict) -> str`
  - `render.nombre_historial(m: RegistroMensaje) -> str`

**Qué defectos matan los tests de esta tarea:**
1. Que las marcas de cita `>` impidan que una frase del historial case con su gemela en una ficha —
   el defecto que haría salir «100 % exclusivas» siempre (SPEC §3, «detalle que decide si esto
   funciona»).
2. Que una frase presente **solo en la ficha del propio portador** se cuente como duplicada.
3. Que los recuentos de la cabecera no cuadren con el índice.
4. Que el umbral de frase sustancial no se aplique.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_email_atomize_historial.py`:

```python
from __future__ import annotations

from core.email_atomize import historial as H
from core.email_atomize import render as R
from core.email_atomize.model import RegistroMensaje


def test_frases_sustanciales_aplica_el_umbral_y_aplana():
    texto = ("Corta.\n"
             "Esta frase tiene mas de ocho palabras y por tanto se conserva entera.\n"
             "Tambien corta.")
    assert H.frases_sustanciales(texto) == [
        "Esta frase tiene mas de ocho palabras y por tanto se conserva entera."]


def test_frases_sustanciales_quita_las_marcas_de_cita_ANTES_de_aplanar():
    """El defecto que haria inutil todo el modulo: si se aplana antes de quitar los `>`, quedan
    a mitad de cadena, `normaliza_cuerpo` (que los quita solo al principio de linea) no los
    limpia, y NINGUNA frase del historial casa con su gemela de una ficha."""
    citada = "> Esta frase tiene mas de ocho palabras y viene citada con marca.\n> Y sigue aqui."
    limpia = "Esta frase tiene mas de ocho palabras y viene citada con marca. Y sigue aqui."
    assert H.frases_sustanciales(citada) == H.frases_sustanciales(limpia)
    assert ">" not in H.frases_sustanciales(citada)[0]


def _msg(msg_id: str, cuerpo: str) -> RegistroMensaje:
    return RegistroMensaje(msg_id=msg_id, cuerpo=cuerpo)


def test_indice_frases_agrupa_por_frase_normalizada():
    f = "Esta frase tiene mas de ocho palabras y aparece en dos fichas distintas."
    idx = H.indice_frases([_msg("MSG-00001", f), _msg("MSG-00002", f),
                           _msg("MSG-00003", "otra cosa corta")])
    assert list(idx.values()) == [["MSG-00001", "MSG-00002"]]


def test_render_marca_duplicadas_y_exclusivas_y_los_recuentos_cuadran():
    dup = "Esta frase tiene mas de ocho palabras y ya existe en otra ficha distinta."
    exc = "Esta otra frase tiene mas de ocho palabras y no existe en ningun otro sitio."
    idx = H.indice_frases([_msg("MSG-00007", dup)])
    md = H.render_historial(portador_msg_id="MSG-00002",
                            nombre_ficha="2026-07-28_1000_asunto_MSG-00002.md",
                            resto_citado=f"> {dup}\n> {exc}", indice=idx)
    assert "- frases sustanciales (>=8 palabras): 2" in md
    assert "- ya presentes en otra ficha: 1" in md
    assert "- **exclusivas de este fichero: 1**" in md
    assert "| 1 | duplicada | MSG-00007 |" in md
    assert "| 2 | **EXCLUSIVA** | — |" in md
    assert "SIN ATRIBUIR" in md and "2026-07-28_1000_asunto_MSG-00002.md" in md
    # El texto va VERBATIM: con sus marcas de cita, sin tocar.
    assert f"> {dup}\n> {exc}" in md


def test_render_no_cuenta_como_duplicada_una_frase_que_solo_esta_en_su_propia_ficha():
    """Contrato §8.7: el indice se excluye a si mismo. Sin esto, el historial de un portador
    cuyo propio cuerpo repita una frase saldria «duplicada» y se leeria como «esto ya esta en
    otro sitio», que es falso."""
    f = "Esta frase tiene mas de ocho palabras y solo vive en el propio portador."
    idx = H.indice_frases([_msg("MSG-00002", f)])
    md = H.render_historial(portador_msg_id="MSG-00002", nombre_ficha="x.md",
                            resto_citado=f, indice=idx)
    assert "- ya presentes en otra ficha: 0" in md
    assert "- **exclusivas de este fichero: 1**" in md


def test_nombre_historial_es_el_de_la_ficha_con_el_sufijo():
    m = RegistroMensaje(msg_id="MSG-00002", fecha_iso="2026-07-28", hora="1000", asunto="Asunto")
    assert R.nombre_historial(m) == R.nombre_md(m).removesuffix(".md") + ".historial.md"
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_historial.py
```

Esperado: **todos FAIL**, el primero por `ModuleNotFoundError: No module named 'core.email_atomize.historial'`.

- [ ] **Step 3: Crear el módulo**

Crear `core/email_atomize/historial.py` con este contenido exacto:

```python
"""Historial citado no atribuible, localizable (`MEJORAS #105`, pieza 1 de `#109`).

Modulo PURO: no toca disco. Lo cablea `pipeline.atomize_dir`.

La regla que gobierna este modulo: NADA de lo que produce atribuye texto a un remitente. El
historial va verbatim y las anotaciones dicen solo «esta frase ya esta en la ficha X» o «esta
frase no esta en ningun otro sitio». Ahi esta la diferencia con la Capa B, que si atribuye y
por eso exige una cabecera parseable.

Spec: `docs/superpowers/specs/2026-07-30-historial-citado-localizable-design.md`.
"""
from __future__ import annotations

import re

from .inline import normaliza_cuerpo

# "Frase sustancial": la unidad sobre la que `MEJORAS #105` midio que el 90 % del texto
# recortado ya existia en otra ficha. No cambiar sin re-medir.
_MIN_PALABRAS = 8

# Marca de cita al PRINCIPIO de linea. Se quita ANTES de aplanar: si se aplanase primero, los
# `>` quedarian a mitad de cadena, `normaliza_cuerpo` (que tambien las quita solo al principio
# de linea) no los limpiaria, y ninguna frase del historial casaria con su gemela de una ficha
# -> el fichero saldria con «100 % exclusivas» siempre.
_RE_MARCA_CITA = re.compile(r"(?m)^\s*>+\s?")

# Fin de frase: puntuacion terminal seguida de espacio, o linea en blanco.
_RE_FIN_FRASE = re.compile(r"(?<=[.!?…])\s+|\n{2,}")

_CABECERA = (
    "<!-- GENERADO por core.email_atomize — NO editar a mano. -->\n"
    "# Historial citado de {portador} — SIN ATRIBUIR\n\n"
    "Historial que `cortar_autor` retiro del cuerpo de `{ficha}`, VERBATIM.\n"
    "**Nada de lo que hay aqui esta atribuido a un remitente.** El texto puede incluir bloques\n"
    "`De:`/`Enviado:` porque van dentro de la cita y se reproducen tal cual: son parte del texto\n"
    "citado, **no** una atribucion del motor. Si un mensaje de aqui tuviera cabecera atribuible,\n"
    "tendria su propia ficha; no la tiene.\n\n"
    "- frases sustanciales (>=8 palabras): {n_frases}\n"
    "- ya presentes en otra ficha: {n_dup}\n"
    "- **exclusivas de este fichero: {n_exc}**\n"
)


def frases_sustanciales(texto: str) -> list[str]:
    """Las frases de *texto* con >= 8 palabras, en orden y ya aplanadas a una linea.

    Devuelve el texto legible (sin marcas de cita, sin saltos), NO normalizado: estas frases se
    imprimen en el indice del `.historial.md`. La normalizacion es solo para comparar.
    """
    limpio = _RE_MARCA_CITA.sub("", texto or "")
    frases = []
    for bruto in _RE_FIN_FRASE.split(limpio):
        f = " ".join(bruto.split())
        if len(f.split()) >= _MIN_PALABRAS:
            frases.append(f)
    return frases


def indice_frases(mensajes: list) -> dict[str, list[str]]:
    """De frase NORMALIZADA al `MSG-id` de las fichas cuyo cuerpo la contiene.

    Se construye desde el cuerpo de todas las fichas publicadas (Capa A y B). Normaliza con
    `normaliza_cuerpo`, el mismo normalizador unico que gobierna los fingerprints.
    """
    idx: dict[str, list[str]] = {}
    for m in mensajes:
        for f in frases_sustanciales(m.cuerpo):
            k = normaliza_cuerpo(f)
            if not k:
                continue
            ids = idx.setdefault(k, [])
            if m.msg_id not in ids:
                ids.append(m.msg_id)
    return idx


def render_historial(*, portador_msg_id: str, nombre_ficha: str, resto_citado: str,
                     indice: dict[str, list[str]]) -> str:
    """El contenido del `<atom>.historial.md`: cabecera con recuentos, indice de frases y el
    texto retirado VERBATIM.

    El indice se excluye a si mismo: una frase presente solo en la ficha del propio portador NO
    cuenta como «ya presente en otra ficha».
    """
    frases = frases_sustanciales(resto_citado)
    filas, n_dup = [], 0
    for i, f in enumerate(frases, 1):
        otros = [x for x in indice.get(normaliza_cuerpo(f), []) if x != portador_msg_id]
        if otros:
            n_dup += 1
            filas.append(f"| {i} | duplicada | {', '.join(otros)} | {_celda(f)} |")
        else:
            filas.append(f"| {i} | **EXCLUSIVA** | — | {_celda(f)} |")
    partes = [_CABECERA.format(portador=portador_msg_id, ficha=nombre_ficha,
                               n_frases=len(frases), n_dup=n_dup,
                               n_exc=len(frases) - n_dup)]
    partes.append("\n## Indice de frases\n")
    partes.append("| # | estado | donde vive | frase |")
    partes.append("|---|---|---|---|")
    partes.extend(filas or ["| — | — | — | (ninguna frase de >=8 palabras) |"])
    partes.append("\n## Texto retirado (verbatim)\n")
    partes.append("```text")
    partes.append(resto_citado)
    partes.append("```")
    return "\n".join(partes) + "\n"


def _celda(f: str) -> str:
    """La frase, apta para una celda de tabla Markdown: sin `|` y acotada."""
    return f.replace("|", " ")[:120]
```

- [ ] **Step 4: Añadir `nombre_historial` a `render.py`**

En `core/email_atomize/render.py`, insertar justo **después** de `nombre_md` (que acaba en la
línea 15) y antes de `_yaml_lista`:

```python
def nombre_historial(m: RegistroMensaje) -> str:
    """El fichero hermano del historial citado de *m* (`MEJORAS #105`). Mismo nombre que su
    ficha con el sufijo cambiado, para que salgan adyacentes al ordenar el directorio."""
    return nombre_md(m).removesuffix(".md") + ".historial.md"
```

- [ ] **Step 5: Correr los tests**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_historial.py -v
```

Esperado: **6 passed**.

- [ ] **Step 6: Mutation testing de los tests de esta tarea**

Aplicar cada mutación con Python (**no** con las APIs de `.NET`, ver Global Constraints), correr el
fichero de tests y restaurar:

| Mutación en `historial.py` | Debe matar |
|---|---|
| `_MIN_PALABRAS = 8` → `= 1` | el test del umbral |
| Quitar la limpieza de marcas: `limpio = texto or ""` | el test de las marcas de cita |
| `if x != portador_msg_id` → `if True` | el test de la auto-exclusión |
| `n_exc=len(frases) - n_dup` → `n_exc=len(frases)` | el test de los recuentos |

Guion (ajustar la mutación de cada vuelta):

```python
import subprocess
from pathlib import Path
PY = r"C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe"
f = Path("core/email_atomize/historial.py")
orig = f.read_text(encoding="utf-8")
viejo, nuevo = "_MIN_PALABRAS = 8", "_MIN_PALABRAS = 1"
assert viejo in orig, "la mutacion no casa: el resultado seria invalido"
try:
    f.write_text(orig.replace(viejo, nuevo, 1), encoding="utf-8")
    r = subprocess.run([PY, "-m", "pytest", "-q", "tests/test_email_atomize_historial.py"],
                       capture_output=True, encoding="utf-8", errors="replace")
    print([l for l in r.stdout.splitlines() if l.startswith("FAILED")])
finally:
    f.write_text(orig, encoding="utf-8")
```

**Si una mutación no mata ningún test, el test que falta se escribe antes de continuar.** No seguir
con «ya lo cubre otro».

- [ ] **Step 7: Commit**

```bash
git add core/email_atomize/historial.py core/email_atomize/render.py tests/test_email_atomize_historial.py
git commit -m "feat(email_atomize): modulo puro del historial citado (MEJORAS #105)"
```

---

### Task 2: Cableado en el pipeline — el fichero se escribe

**Files:**
- Modify: `core/email_atomize/pipeline.py` — `_construir_mensaje` (línea 281), su call-site
  (línea 141), y el bloque de escritura (líneas 157-161)
- Create: `tests/test_email_atomize_historial_pipeline.py`

**Interfaces:**
- Consumes: `historial.indice_frases`, `historial.render_historial`, `render.nombre_historial`
  (Tarea 1).
- Produces, y lo consume la Tarea 3: una variable local `historiales` en `atomize_dir`, del tipo
  `set[str]` con los **nombres de fichero** de los historiales escritos en esta corrida.

**Qué defectos matan los tests de esta tarea:**
1. Que el fichero no se escriba (la función entera ausente).
2. Que se escriba para un portador **sin** texto recortado (ruido).
3. Que **no** se escriba cuando todo el historial está duplicado — la decisión 4 de la SPEC, cuyo
   valor es que «0 exclusivas» sea una afirmación falsable.
4. Que el bloque de texto no sea verbatim.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_email_atomize_historial_pipeline.py`:

```python
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import pipeline as P

# Cita con marcador Outlook: `cortar_autor` la reconoce y RECORTA el cuerpo, que es la
# precondicion de todo este artefacto (`cuerpo_recortado_cita`).
_HISTORIAL = ("Esta frase citada tiene mas de ocho palabras y es la primera del historial.\n"
              "Esta segunda frase citada tambien pasa de ocho palabras con holgura.")


def _eml(mid: str, subject: str, *, fecha: str, cuerpo: str) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = "autor@example.invalid"
    m["To"] = "dest@example.invalid"
    m.set_content(cuerpo)
    return m.as_bytes()


def _con_historial(texto_autor: str, historial: str = _HISTORIAL) -> str:
    """Cuerpo con cola citada: autor arriba, marcador de cita, historial debajo."""
    return (f"{texto_autor}\n"
            "De: Otro <otro@example.invalid>\n"
            "Enviado: lunes, 27 de julio de 2026 9:00\n"
            "Para: dest@example.invalid\n"
            "Asunto: Re: Asunto\n"
            f"{historial}")


def _historiales(out: Path) -> list[Path]:
    return sorted((out / "mensajes").glob("*.historial.md"))


def test_un_portador_con_cuerpo_recortado_obtiene_su_historial_verbatim(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    P.atomize_dir(src, out)

    hs = _historiales(out)
    assert len(hs) == 1, f"se esperaba un historial; hay {[p.name for p in hs]}"
    txt = hs[0].read_text(encoding="utf-8")
    assert "SIN ATRIBUIR" in txt
    # VERBATIM: el historial aparece tal cual, no reformateado.
    assert _HISTORIAL in txt
    # Y no atribuye: ninguna direccion del portador aparece como remitente del historial.
    assert "- de:" not in txt and "remitente:" not in txt


def test_un_portador_sin_cuerpo_recortado_no_genera_fichero(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Sin historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo="Solo texto del autor, sin ninguna cita debajo."))

    P.atomize_dir(src, out)
    assert _historiales(out) == []


def test_historial_100_por_cien_duplicado_se_escribe_igual_con_cero_exclusivas(tmp_path):
    """Decision 4 de la SPEC: el fichero existe siempre que haya texto recortado. «0 exclusivas»
    es una afirmacion FALSABLE — si no se escribiera, la respuesta a «me estoy perdiendo algo en
    este portador?» no existiria en ningun sitio."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    # El mensaje ANTERIOR del hilo llega como .eml propio: su cuerpo ES el historial.
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Original", fecha="Mon, 27 Jul 2026 09:00:00 +0200",
             cuerpo=_HISTORIAL))
    # Y el portador lo cita entero.
    (src / "b.eml").write_bytes(
        _eml("<b@example.invalid>", "Respuesta", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    P.atomize_dir(src, out)

    hs = _historiales(out)
    assert len(hs) == 1
    txt = hs[0].read_text(encoding="utf-8")
    assert "- **exclusivas de este fichero: 0**" in txt
    assert "duplicada" in txt, "las frases deben marcarse como duplicadas, no desaparecer"


def test_un_historial_que_falla_al_escribirse_se_declara_y_no_degrada_la_corrida(
        tmp_path, monkeypatch):
    """Contrato §7: el historial es una vista DERIVADA. Su fallo va a `notas` nombrando al
    portador, NO a `errores` -- porque `errores` gobierna `poda_omitida` y apagaria la poda del
    arbol entero por un artefacto accesorio. Y la ausencia queda declarada, no silenciosa."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    real = Path.write_text

    def falla_solo_el_historial(self, *a, **k):
        if self.name.endswith(".historial.md"):
            raise OSError("disco lleno de mentira")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "write_text", falla_solo_el_historial)
    rep = P.atomize_dir(src, out)

    assert _historiales(out) == []
    assert rep.errores == [], "un historial fallido NO puede entrar en errores: apagaria la poda"
    assert rep.poda_omitida is False
    assert any("historial de MSG-00001 no escrito" in n for n in rep.notas), \
        f"la ausencia debe declararse nombrando al portador; notas: {rep.notas}"
    # Y la ficha del portador SI se publica: la vista derivada no arrastra al artefacto principal.
    assert len(list((out / "mensajes").glob("*.md"))) == 1
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_historial_pipeline.py
```

Esperado: **el primero y el tercero FAIL** (`se esperaba un historial; hay []`), el segundo PASS (hoy
no se escribe ningún fichero, así que su aserción ya se cumple; su trabajo es **quedarse verde**
después del cambio). El cuarto (el de `notas`) también FAIL.

**Antes de implementar, comprobar la precondición** — si `cortar_autor` no recortara el fixture, esos
tests fallarían con **el mismo mensaje** que si faltara la función, y se perseguiría lo equivocado:

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -c "import sys; sys.path.insert(0,'tests'); from test_email_atomize_historial_pipeline import _eml, _con_historial; from core.email_atomize.bodies import extraer_cuerpo; c = extraer_cuerpo(_eml('<a@x>','X',fecha='Tue, 28 Jul 2026 10:00:00 +0200',cuerpo=_con_historial('Mi respuesta breve.')), conservar_resto=True); print('recortado:', c.cuerpo_recortado_cita, '| palabras del resto:', len((c.resto_citado or '').split()))"
```

Esperado: `recortado: True` y un resto de **más de 20 palabras**. Si sale `False`, el marcador de cita
del fixture no lo reconoce `cortar_autor` y hay que arreglar **el fixture**, no el motor: probar con
`-----Mensaje original-----` delante del bloque `De:`.

- [ ] **Step 3: `_construir_mensaje` devuelve también el resto citado**

En `core/email_atomize/pipeline.py`, en `_construir_mensaje` (línea 281), cambiar la firma y la
extracción del cuerpo:

```python
def _construir_mensaje(col, reg, apariciones, unicos, report) -> tuple[RegistroMensaje, str | None]:
```

y la línea que extrae el cuerpo:

```python
    cuerpo = B.extraer_cuerpo(col.raw, conservar_resto=True)
```

> `conservar_resto` es **puramente aditivo** (`bodies.py:60-85`): `texto=autor` se calcula igual con
> el flag o sin él, y solo se rellenan dos campos más. Por eso la Capa A no se mueve.

El `return` final es **una sola expresión** `return RegistroMensaje(...)` (línea ~305). Se parte en dos
sin tocar ni un argumento: cambiar la primera línea

```python
    return RegistroMensaje(
```

por

```python
    m = RegistroMensaje(
```

y añadir, **después** del `)` que la cierra:

```python
    return m, cuerpo.resto_citado
```

- [ ] **Step 4: Adaptar el call-site y recoger los restos**

En `atomize_dir`, sustituir el bloque de las líneas 138-151 por:

```python
    carriers: list[tuple[RegistroMensaje, bytes]] = []
    restos: dict[str, str] = {}          # msg_id -> historial citado que `cortar_autor` retiro
    for col in colapsados:
        try:
            m, resto = _construir_mensaje(col, reg, apariciones, unicos, report)
        except Exception as exc:  # noqa: BLE001 — un mensaje no aborta la corrida
            report.errores.append(f"{col.message_id or '(sin id)'}: {exc}")
            continue
        mensajes.append(m)
        carriers.append((m, col.raw))
        if resto and resto.strip():
            restos[m.msg_id] = resto
        # Llave del registro: lleva la fuente delante porque la ruta relativa a CADA
        # fuente no es única (`sub/a.eml` puede existir en dos lotes). `eml_origen` se
        # queda como está: es el valor probatorio del frontmatter.
        reg.marcar_procesado(f"{col.fuente}/{col.eml_origen}" if col.fuente
                             else col.eml_origen)
```

> Los restos van en un **dict local**, no en `RegistroMensaje`: un campo nuevo en el modelo tienta a
> emitirlo en el frontmatter, y eso reescribiría la Capa A.

- [ ] **Step 5: Escribir los historiales**

En `atomize_dir`, justo **después** del bucle que escribe las fichas (línea 161) y **antes** del
`if report.errores:`, insertar:

```python
    # `MEJORAS #105`: el historial citado que `cortar_autor` retiro no estaba en ningun
    # artefacto. Se escribe VERBATIM en un fichero hermano, con los duplicados marcados y SIN
    # atribuir nada. El indice se construye con las fichas de Capa A y B ya conocidas.
    historiales: set[str] = set()
    if restos:
        indice = HIST.indice_frases(mensajes)
        por_id = {m.msg_id: m for m in mensajes}
        for msg_id, resto in restos.items():
            m = por_id.get(msg_id)
            if m is None:
                continue
            nombre = R.nombre_historial(m)
            try:
                (out / "mensajes" / nombre).write_text(
                    HIST.render_historial(portador_msg_id=msg_id, nombre_ficha=R.nombre_md(m),
                                          resto_citado=resto, indice=indice),
                    encoding="utf-8")
            except OSError as exc:
                # Vista derivada: su fallo NO entra en `report.errores` (eso apagaria la poda
                # del arbol entero). Se declara nombrando al portador y se sigue.
                report.notas.append(f"historial de {msg_id} no escrito: {exc}")
                continue
            historiales.add(nombre)
```

Y añadir el import, junto a los demás del paquete (bloque de las líneas 16-29):

```python
from . import historial as HIST
```

- [ ] **Step 6: Correr los tests de esta tarea**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_historial_pipeline.py -v
```

Esperado: **4 passed**.

- [ ] **Step 7: Correr el golden de la Capa A, que es el que manda**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_firma_veto.py tests/test_email_atomize_pipeline.py -v
```

Esperado: **todo PASS**, y en particular `test_capa_a_byte_identica_contra_golden`. Si se pone rojo,
`conservar_resto` ha movido una ficha: **parar**. El cambio es inaceptable, no el golden.

Los dos tests de `test_email_atomize_pipeline.py` que monkeypatchean `_construir_mensaje` (líneas
~221 y ~390) **no** necesitan cambios: su envoltorio hace `return real_construir(col, *a, **k)`, así
que la tupla pasa de forma transparente. Si alguno falla, es que el envoltorio dejó de ser
transparente y hay que mirarlo, no silenciarlo.

- [ ] **Step 8: Commit**

```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_historial_pipeline.py
git commit -m "feat(email_atomize): el historial citado se escribe como fichero hermano"
```

---

### Task 3: El arreglo de la poda — el artefacto sobrevive a la corrida siguiente

Es el defecto del §5.3 de la SPEC y **el único que rompería la función entera en silencio**: la
poda de idempotencia borra todo `mensajes/*.md` ajeno a `esperados`, así que sin este arreglo cada
historial se autodestruye en la corrida siguiente y el fichero solo existiría hasta que alguien
re-atomizara.

**Files:**
- Modify: `core/email_atomize/pipeline.py` — la poda (líneas 173-177)
- Test: `tests/test_email_atomize_historial_pipeline.py`

**Interfaces:**
- Consumes: `historiales: set[str]` (Tarea 2).

**Qué defecto mata el test:** que el historial desaparezca en la segunda corrida; y, en la otra
dirección, que un historial **huérfano** se quede para siempre, que es la convergencia que esa poda
existe para proteger.

- [ ] **Step 1: Escribir el test que falla**

Añadir al final de `tests/test_email_atomize_historial_pipeline.py`:

```python
def test_la_poda_conserva_los_historiales_pero_se_lleva_los_huerfanos(tmp_path):
    """El defecto del §5.3: la poda borra todo `mensajes/*.md` ajeno a `esperados`, asi que un
    `.historial.md` se autodestruiria en la corrida siguiente. Y la direccion contraria importa
    igual: un historial cuyo portador ya no existe TIENE que irse, o la poda deja de converger."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "a.eml").write_bytes(
        _eml("<a@example.invalid>", "Con historial", fecha="Tue, 28 Jul 2026 10:00:00 +0200",
             cuerpo=_con_historial("Mi respuesta breve.")))

    P.atomize_dir(src, out)
    primera = [p.name for p in _historiales(out)]
    assert len(primera) == 1

    # Un huerfano: historial de un portador que no existe.
    huerfano = out / "mensajes" / "2020-01-01_0000_fantasma_MSG-09999.historial.md"
    huerfano.write_text("<!-- viejo -->\n", encoding="utf-8")

    P.atomize_dir(src, out)

    assert [p.name for p in _historiales(out)] == primera, \
        "la segunda corrida se ha llevado el historial legitimo"
    assert not huerfano.exists(), "un historial huerfano debe podarse: la poda tiene que converger"
```

- [ ] **Step 2: Correr el test para verificar que falla**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q "tests/test_email_atomize_historial_pipeline.py::test_la_poda_conserva_los_historiales_pero_se_lleva_los_huerfanos" -v
```

Esperado: **FAIL** en `la segunda corrida se ha llevado el historial legitimo` — la lista queda
vacía. Es el defecto reproducido.

- [ ] **Step 3: Extender `esperados`**

En `core/email_atomize/pipeline.py`, sustituir la línea 174:

```python
        esperados = {R.nombre_md(m) for m in mensajes}
```

por:

```python
        # Los historiales (`MEJORAS #105`) tambien son artefactos esperados: sin esto la poda
        # los borraria en la corrida siguiente, porque el glob de abajo coge todo `*.md`. Se
        # anaden SOLO los escritos en esta corrida, de modo que un historial huerfano —portador
        # desaparecido, o portador que ya no tiene texto recortado— sigue podandose y la
        # convergencia no se debilita.
        esperados = {R.nombre_md(m) for m in mensajes} | historiales
```

- [ ] **Step 4: Correr el test y el fichero entero**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_historial_pipeline.py -v
```

Esperado: **5 passed**.

- [ ] **Step 5: Mutation testing del arreglo**

| Mutación en `pipeline.py` | Debe matar |
|---|---|
| `| historiales` retirado de `esperados` | el test de la poda (rama «se conserva») |
| `esperados = {...} | historiales` → `esperados = {...} | historiales | {"2020-01-01_0000_fantasma_MSG-09999.historial.md"}` | el test de la poda (rama «huérfano») |

La segunda mutación es artificial a propósito: comprueba que el test vigila **las dos direcciones** y
no solo la conservación. Si no mata, la aserción del huérfano no está haciendo su trabajo.

- [ ] **Step 6: Commit**

```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_historial_pipeline.py
git commit -m "fix(email_atomize): la poda conserva los historiales y sigue podando huerfanos"
```

---

### Task 4: Suite completa, docs y PR

**Files:**
- Modify: `docs/MEJORAS_FUTURAS.md`

- [ ] **Step 1: Suite completa**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q --tb=short --junit-xml=suite.xml
```

Esperado: **0 failures, 0 errors**, total **2566 + 11 nuevos = 2577** (77 skipped). Leer el conteo del
`suite.xml`. Borrar `suite.xml` antes de commitear.

- [ ] **Step 2: Cerrar `#105` y marcar la pieza 1 de `#109`**

En `docs/MEJORAS_FUTURAS.md`:

- En la entrada **`## 105`**, sustituir el bloque `> ▶ **PROMOVIDO 2026-07-30…**` por
  `> ✅ **CERRADO** — PR #NNN`, conservando debajo la nota de las dos correcciones y del choque con la
  poda (son el registro de por qué la propuesta original no se implementó tal cual).
- En la entrada **`## 109`**, donde dice `**Estado.** Pieza 2 **hecha**. Queda la pieza 1 (`#105`)…`,
  marcar la pieza 1 como hecha con su PR y dejar como único pendiente `#106` (el hilo).

Dejar el número de PR como `#NNN` **hasta que exista**: el `✅` con el número y el hash del squash se
pone en el cierre de sesión, tras el merge — es la regla de `CLAUDE.md` («el estado de ciclo de vida
de un ítem vive solo en `PLAN.md`… al cerrar un ítem se pone `✅` + hash del PR»).

- [ ] **Step 3: Guards de docs y comprobación de PII**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_docs_gobernanza.py tests/test_gobernanza_taxonomia.py
```

Y la comprobación de PII que el hook local **no** hace en un worktree (la blocklist vive en la raíz):

```python
import re, subprocess, sys
from pathlib import Path
sys.path.insert(0, ".")
from scripts.precommit_leak_guard import cargar_blocklist
bl = [t for t in cargar_blocklist(Path(r"C:\Users\tnm33\Dev\FeesDefender")) if t]
pat = [re.compile(r"(?<![\w])" + re.escape(t) + r"(?![\w@])", re.IGNORECASE) for t in bl]
sucios = 0
for rel in subprocess.run(["git", "ls-files"], capture_output=True, encoding="utf-8").stdout.split():
    p = Path(rel)
    if not p.is_file():
        continue
    d = p.read_bytes()
    if b"\x00" in d[:4096]:
        continue
    if any(rx.search(d.decode("utf-8", errors="replace")) for rx in pat):
        print("SUCIO:", rel)
        sucios += 1
print("limpio" if not sucios else f"{sucios} ficheros sucios")
```

Esperado: `limpio`. Un `término in texto` ingenuo da falsos positivos: la regex con límites de palabra
es la que usa el guard.

- [ ] **Step 4: PR**

```bash
git push -u origin claude/historial-citado
```

Abrir el PR y esperar `leak-scan` verde. **El CI no corre pytest**: el conteo del paso 1 va en el
cuerpo del PR.

---

## Lo que queda fuera, con dueño

- **El hilo** — tener el texto no da la conversación: `MEJORAS #106`.
- **El consumo por la sala de lectura** — `MEJORAS #86`.
- **Verificación en vivo:** esta rama **no tiene banco de pruebas real** (SPEC §10). El corpus de
  prueba se borró con autorización tras medir el hilo de `#109`, así que los números del §1 de la SPEC
  son de la medición anterior y la construcción se valida solo con tests. Se cierra re-exportando una
  etiqueta pequeña a un scratch fuera de todo expediente y mirando los `.historial.md` que salgan.
