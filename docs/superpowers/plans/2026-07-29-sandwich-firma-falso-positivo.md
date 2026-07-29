# La firma no es una respuesta intercalada — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**SPEC (fuente única del diseño, no reabrir sus decisiones):**
`docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md` (**rev. 2**, con la
revisión adversarial de Codex adjudicada en su §9). **Leer antes la «Corrección medida» de abajo:
una cifra de la SPEC está mal y este plan la corrige con evidencia.**

**Goal:** que los trozos de texto que viven dentro de un contenedor de firma dejen de contar como
«texto de autor» en el veto de `_sandwich`, de modo que un hilo de Gmail con la firma de E&V entre
dos citas vuelva a segmentarse y sus mensajes citados reciban ficha.

**Architecture:** un solo detector de `core/email_atomize/inline.py`. `_QuoteHTMLParser` marca cada
trozo de texto de autor con un token distinto (`"S"` en vez de `"A"`) cuando está bajo un ancestro
cuyo `class`/`id` identifica una firma; `_sandwich` ignora ese token. La exclusión es **aditiva y
estructural**: solo resta trozos de firma del recuento, así que no puede levantar un veto correcto —
si queda un trozo de autor real, el sándwich sigue dando `True`. Cuando la exclusión cambia el
veredicto, `Segmentacion` lo transporta en un contador y `reconstruir` deja un puntero `info` en
`_revision/cola.md`.

**Tech Stack:** Python 3.14, `html.parser` de la stdlib (sin dependencias nuevas), pytest.

## Corrección medida sobre la SPEC (leer antes de empezar)

La SPEC §2.2 y §5 afirman que la regla arregla **5 de los 7** portadores vetados de la muestra de
Gmail. **Medido el 2026-07-29 aplicando la regla propuesta al corpus real** (`_PRUEBA_98_VaRS3`, 29
`.eml`) con una **subclase de `_QuoteHTMLParser`** —hereda el parser del repo y usa su `_html_part`,
con los tres métodos que propone la Tarea 2— y el predicado de firma sobre `class`/`id`:

| | SPEC rev. 2 | Medido |
|---|---|---|
| Portadores con HTML | — | 24 (5 sin HTML) |
| El DOM ve intercalada | 7 | **7** ✅ |
| **Cambian de veredicto con la regla** | 5 | **3** |
| Conservan el veto | 2 | **4** |

**Por qué la SPEC se equivoca, y por qué la decisión sigue en pie.** De los 4 que conservan el veto,
**2** no tienen ningún contenedor de firma (forma `A6 Q A3 Q A20`): son texto de autor real, y son los
2 que la SPEC ya preveía. Los otros **2** (forma `A S5 Q S3 Q S20 A3 Q3`) **sí** tienen la firma bajo
`gmail_signature`, pero **además** tienen texto de autor entre la segunda y la tercera cita: el
sándwich les dispara desde ahí, no desde la firma. La SPEC midió «todos los trozos disparadores son
firma» sobre parte de la secuencia, no sobre toda.

La cifra es **insensible al conjunto de marcadores**: `("gmail_signature",)`,
`+("signature",)` y `+("firma",)` dan los mismos 3. Los 28 trozos de firma ya los captura
`gmail_signature` solo.

**Lo que esto NO cambia:** que la regla no puede levantar un veto correcto — los 4 casos correctos
siguen vetados, medido. Lo que cambia es el beneficio: **3 portadores desbloqueados, no 5**, y la
expectativa de la verificación en vivo (§8 de la SPEC habla de «5 segmentan, ~2 producen ficha»; el
techo real es 3).

> **La errata NO se escribe en la SPEC hasta confirmarla con el código integrado** (Tarea 5, paso
> 1-bis). Las divergencias que la revisión adversarial temía no aplican —el script subclasea el
> parser real—, pero la cifra va a una SPEC ya adjudicada y la confirmación cuesta una corrida.

**Segunda medición de la misma ronda, y es la que obligó a añadir un guard:** la firma queda **sin
cerrar** al final del documento en **20 de 271** correos reales (5 de 24 en la prueba de Gmail, 15 de
247 en W-02VND1). Sin el guard fail-closed de la Tarea 2 (paso 7), en esos casos `_sigdepth` no vuelve
a 0, **todo** el texto de autor posterior se marca como firma y la exclusión **levanta un veto
correcto**. En estos dos corpus no llegaba a disparar —el defecto estaba armado y callado, igual que
`#98`— y el guard **no cuesta ni un portador**: 3 desbloqueados con guard y sin guard.

**Forma real del caso arreglable, medida** (es la que reproduce el fixture de la Tarea 1):

```
S3 Q S Q S3      ← trozos de firma, cita, firma, cita, firma. NINGÚN trozo "A" entre citas.
```

Y un detalle que decide el fixture: **el anclaje de las dos citas es la propia firma**
(`_pending_parts` recoge cualquier texto, también el de firma), así que no sirve para atribuir. En
los casos reales la atribución solo puede venir de la **cabecera dentro del cuerpo citado**
(`De:`/`Enviado:`/`Para:`/`Asunto:`), que es el camino `_cabecera_head` → `_parse_label`. El fixture
lo reproduce y produce 2 candidatos `media-reconstruida` por `atribucion_cuerpo` — **verificado
empíricamente antes de escribir este plan**, no deducido.

## Global Constraints

- **Entorno: Windows + PowerShell.** El intérprete de este repo es
  `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`. Los worktrees **no** tienen `.venv`
  propio: se invoca ese binario por ruta absoluta con el `cwd` en el worktree
  (`.claude/worktrees/sandwich-firma`).
- **Encoding: UTF-8 sin BOM siempre.** En Python, `read_text(encoding="utf-8")` /
  `write_text(..., encoding="utf-8")` explícitos.
- **`main` está protegida.** El trabajo va en la rama `claude/sandwich-firma` y entra por PR. Nunca
  commit directo a `main`.
- **La Capa A es byte-idéntica.** Este cambio **no reescribe ninguna ficha existente** y no toca el
  recorte del cuerpo (lo decide `_segmenter.cortar_autor`, otro detector — SPEC §2.1). Cualquier
  paso que mute un `.md` de Capa A es un fallo del plan, no una decisión a tomar.
- **Prime directive del motor: cero misatribución.** Ninguna guarda de atribución se relaja. Este
  cambio decide **si se segmenta**, no **a quién se atribuye**.
- **Los IDs son inmutables.** `msg_id_for` acuña por `Message-ID` y solo incrementa: las fichas
  nuevas van al final del contador y **nada se renumera**.
- **Trampa medida, que ya costó tres sesiones-hijas:** los `Message-ID` se guardan **normalizados,
  SIN los ángulos** (`message_id_of` y `_norm_mid` hacen `.strip("<>")`). Un mock o una llave que
  compare contra `"<a@x>"` **nunca casa**.
- **Trampa de los fixtures HTML:** una dirección entre ángulos literales (`<ana@x>`) la parsea
  `HTMLParser` como una **etiqueta** y desaparece del texto. En todo fixture HTML se escribe
  `&lt;ana@x&gt;`, que con `convert_charrefs=True` llega a `handle_data` como `<ana@x>` — que es lo
  que la guarda G5 exige para afirmar un remitente.
- **Ningún test vacuo.** En este motor ya han aparecido cuatro (uno vivo en `main`, `MEJORAS #107`).
  Por cada test, la pregunta es **qué defecto concreto mata**; un test que solo comprueba tipos o
  presencia no vale. Cada tarea lo declara.
- **Comando de suite completa:** `python -m pytest -q --tb=short`. Conteo fiable por `--junit-xml`
  (el resumen de pytest no sobrevive a las tuberías de PowerShell). Punto de partida de esta rama:
  **2547 tests, 0 failures, 0 errors, 77 skipped** sobre `c442236`.
- **El CI del PR solo corre `leak-scan`, NO pytest.** La suite local es la única red.
- **La blocklist de PII del CI es superset de la local:** no escribir nombres propios de terceros en
  código, tests, docs ni mensajes de commit. Los fixtures usan nombres sintéticos (`Ana Uno`,
  `Bea Dos`, `Nombre Sintetico`) y direcciones `@example.invalid`.

---

## Estructura de ficheros

| Fichero | Responsabilidad | Tarea |
|---|---|---|
| `core/email_atomize/inline.py` | `_QuoteHTMLParser` marca los trozos de firma; `_sandwich` los ignora; `Segmentacion` transporta el contador; `reconstruir` emite la traza | 2, 3 |
| `tests/test_email_atomize_inline.py` | unitarios de `segmentar_html` (contrato §6 tests 1 y 3, junto a los `test_seg_html_*` que ya existen) | 2 |
| `tests/test_email_atomize_firma_veto.py` | **nuevo** — golden de Capa A, traza y emparejamiento remitente↔cuerpo, todos contra el motor real vía `atomize_dir` (contrato §6 tests 4, 5, 6) | 1, 3, 4 |
| `docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md` | errata de la cifra 5→3 | 6 |
| `PLAN.md` | fila 12 y su bloque, al día | 6 |

**Lo que NO se toca, y por qué:**

- `core/email_atomize/bodies.py` y `core/email_atomize/_segmenter.py` — el recorte del cuerpo es otro
  detector y en estos correos **acierta** (SPEC §1). Tocarlo rompería la byte-identidad de Capa A por
  una causa que es un falso positivo (alternativa descartada, SPEC §4).
- `_intercalada_plain` — es el detector del camino de texto plano, no interviene aquí (SPEC §2.1).
- `tests/test_email_atomize_segmenter.py::test_cortar_autor_intercalada_no_corta` — **ya existe** y es
  el hogar del test 7 del contrato («los casos de intercalada real conservan el cuerpo íntegro»,
  regresión de `cortar_autor`, no protección de este arreglo). No se duplica: se comprueba que sigue
  verde en la Tarea 5.
- `tests/test_email_atomize_inline.py::test_seg_html_intercalada_no_segmenta` (línea 175) — **ya es**
  el test 2 del contrato: `blockquote` + `<div>` con una frase de autor que no es firma ni etiqueta +
  `blockquote`, sin `>` literales ni artificios. Coincide con la forma real medida de los 2
  portadores sin firma (`A6 Q A3 Q A20`). No se duplica; la Tarea 2 comprueba que sigue verde, y
  **si se pusiera rojo el arreglo estaría desactivando el detector**.
- `tests/test_email_atomize_inline.py:182` (`test_seg_html_token_conservacion_no_inventa`), el test
  vacuo: fuera de alcance por decisión de la SPEC §9, y ya tiene entrada propia (`MEJORAS #107`).

---

### Task 1: Golden de la Capa A, capturado ANTES de tocar el motor

Es el test 5 del contrato y **tiene que ir primero**: la SPEC lo dice — «hash de las fichas de Capa A
**capturado antes del cambio** y comparado después. Comparar dos corridas posteriores al cambio no
vale: una mutación determinista que ya ocurra en la primera pasaría inadvertida». Si esta tarea se
ejecuta después de la Tarea 2, el golden pierde todo su valor.

**Qué defecto mata:** que el arreglo reescriba, aunque sea en un carácter, la ficha de Capa A de un
portador ya atomizado. Es el riesgo material del cambio: esos `.md` son el árbol probatorio.

El corpus incluye a propósito **el portador que el arreglo va a cambiar** (`c.eml`), con la forma real
medida. Así el golden demuestra lo que hay que demostrar: que su ficha de Capa A **no** se mueve
mientras la Capa B gana fichas nuevas. El golden filtra por `capa: A`, de modo que las fichas de
Capa B que aparezcan en la Tarea 2 no lo rompan.

La salida del motor es determinista: no hay `datetime`/`now()` en `render.py`, `corpus.py` ni
`pipeline.py` (verificado), y el frontmatter no lleva sellos de tiempo.

**Files:**
- Create: `tests/test_email_atomize_firma_veto.py`

**Interfaces:**
- Consumes: `core.email_atomize.pipeline.atomize_dir(src_dir, out_dir) -> AtomizeReport` (ya existe).
- Produces: los helpers `_eml`, `_corpus`, `_frontmatter(txt) -> str`, `_capa(txt) -> str`,
  `_hashes_capa_a(out) -> dict[str, str]` y las constantes `_F3`, `_F1`, `_CAB_ANA`, `_CAB_BEA`,
  `_HTML_FIRMA_ENTRE_CITAS`, `_HTML_INTERCALADA_REAL`, que reutilizan las Tareas 3 y 4.

- [ ] **Step 1: Escribir el test con el golden a cero (fallará y enseñará los hashes reales)**

Crear `tests/test_email_atomize_firma_veto.py` con este contenido exacto:

```python
from __future__ import annotations

import hashlib
import json
from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import pipeline as P

# --- Fixtures del corpus -----------------------------------------------------------------
# Forma MEDIDA sobre el corpus real (`_PRUEBA_98_VaRS3`, 2026-07-29): `S3 Q S Q S3`. Es decir,
# trozos de firma / cita / firma / cita / firma, y NINGUN trozo de autor entre las citas.
#
# Dos cosas que NO son adorno:
#  1. Las direcciones van como `&lt;x@y&gt;`. Con angulos literales, HTMLParser las trata como
#     etiqueta y desaparecen del texto -> la guarda G5 no veria <addr>, no se afirmaria ningun
#     remitente y el test seria vacuo.
#  2. La cabecera va DENTRO del cuerpo citado. En los casos reales el anclaje de la cita es la
#     propia firma (`_pending_parts` recoge cualquier texto), asi que no sirve para atribuir:
#     la unica via es `_cabecera_head` -> `_parse_label` sobre el cuerpo.

_F3 = ('<div class="gmail_signature"><div>Un saludo</div>'
       '<div>Nombre Sintetico</div><div>Engel y Voelkers</div></div>')
_F1 = '<div class="gmail_signature"><div>Un saludo</div></div>'

_CAB_ANA = ('De: Ana Uno &lt;ana@example.invalid&gt;<br>'
            'Enviado: viernes, 4 de julio de 2025 9:00<br>'
            'Para: dest@example.invalid<br>Asunto: Oferta<br><br>')
_CAB_BEA = ('De: Bea Dos &lt;bea@example.invalid&gt;<br>'
            'Enviado: jueves, 3 de julio de 2025 18:30<br>'
            'Para: dest@example.invalid<br>Asunto: Oferta<br><br>')

_HTML_FIRMA_ENTRE_CITAS = (
    _F3
    + f'<blockquote>{_CAB_ANA}CUERPO-DE-ANA con texto suficiente para no colapsar</blockquote>'
    + _F1
    + f'<blockquote>{_CAB_BEA}CUERPO-DE-BEA con texto suficiente para no colapsar</blockquote>'
    + _F3)

# Intercalada REAL: la forma medida de los 2 portadores sin firma (`A6 Q A3 Q A20`).
_HTML_INTERCALADA_REAL = ('<div>Respondo abajo</div><blockquote>cita uno</blockquote>'
                          '<div>Esto no lo aceptamos</div><blockquote>cita dos</blockquote>')


def _eml(mid: str, subject: str, *, fecha: str, html: str | None = None,
         texto: str = "cuerpo del portador", de: str = "car@example.invalid") -> bytes:
    """Un .eml minimo y DETERMINISTA. Con *html*, multipart/alternative texto+HTML.

    `set_boundary` no es cosmetico: sin el, la stdlib genera una frontera MIME ALEATORIA en
    cada `as_bytes()`, el sha256 del raw cambia, y ese sha entra en el frontmatter de la ficha
    (`render.py:46`), en `corpus.jsonl` y en `_registro.json` -> el golden seria inestable y
    la suite fallaria en falso. Medido: 4 serializaciones, 4 sha distintos sin esta linea, 1
    con ella.
    """
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = de
    m["To"] = "dest@example.invalid"
    m.set_content(texto)
    if html is not None:
        m.add_alternative(f"<html><body>{html}</body></html>", subtype="html")
        m.set_boundary(f"=====FRONTERA-FIJA-{subject.replace(' ', '-')}=====")
    return m.as_bytes()


def _corpus(src: Path) -> None:
    """Tres portadores: sin HTML, con intercalada REAL, y con firma entre citas."""
    src.mkdir(parents=True, exist_ok=True)
    (src / "2025-07-01_a.eml").write_bytes(
        _eml("<a@example.invalid>", "Sin html", fecha="Tue, 1 Jul 2025 10:00:00 +0200"))
    (src / "2025-07-02_b.eml").write_bytes(
        _eml("<b@example.invalid>", "Intercalada real",
             fecha="Wed, 2 Jul 2025 10:00:00 +0200", html=_HTML_INTERCALADA_REAL))
    (src / "2025-07-05_c.eml").write_bytes(
        _eml("<c@example.invalid>", "Firma entre citas",
             fecha="Sat, 5 Jul 2025 10:00:00 +0200", html=_HTML_FIRMA_ENTRE_CITAS))


def _frontmatter(txt: str) -> str:
    """El primer bloque `---` del .md. `render_md` concatena frontmatter y cuerpo, asi que
    buscar `capa: A` en todo el documento clasificaria como A una ficha de Capa B que citara
    un frontmatter en su cuerpo."""
    partes = txt.split("---\n", 2)
    return partes[1] if len(partes) > 2 else ""


def _capa(txt: str) -> str:
    for l in _frontmatter(txt).splitlines():
        if l.startswith("capa:"):
            return l.split(":", 1)[1].strip()
    return ""


def _hashes_capa_a(out: Path) -> dict[str, str]:
    """{nombre del .md: sha256} de las fichas cuyo FRONTMATTER dice `capa: A`."""
    res: dict[str, str] = {}
    for p in sorted((out / "mensajes").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        if _capa(txt) == "A":
            res[p.name] = hashlib.sha256(txt.encode("utf-8")).hexdigest()
    return res


# --- Test 5 del contrato: Capa A byte-identica contra un golden previo -------------------

# GOLDEN capturado con el motor ANTERIOR al arreglo de la firma (rama claude/sandwich-firma,
# base c442236). Si este dict cambia, una ficha de Capa A se ha movido: es un FALLO, no un
# golden a actualizar.
GOLDEN_CAPA_A: dict[str, str] = {}


def test_capa_a_byte_identica_contra_golden(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    _corpus(src)
    P.atomize_dir(src, out)
    actual = _hashes_capa_a(out)
    assert actual == GOLDEN_CAPA_A, (
        "Capa A movida. Hashes actuales (pega en GOLDEN_CAPA_A SOLO si estas ANTES del "
        f"arreglo):\n{actual}")
```

- [ ] **Step 2: Correr el test para capturar los hashes reales**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_firma_veto.py -x
```

Esperado: **FAIL** con `AssertionError: Capa A movida. Hashes actuales (...): {...}`.
Deben salir **3 entradas**, una por portador (los tres son Capa A). Si salen menos de 3, el corpus
no se atomizó entero: **parar y diagnosticar**, no continuar.

- [ ] **Step 3: Pegar los hashes capturados en `GOLDEN_CAPA_A`**

Sustituir `GOLDEN_CAPA_A: dict[str, str] = {}` por el dict literal que imprimió el paso 2, una
entrada por línea. Los nombres y valores son los que salgan; la forma es:

```python
GOLDEN_CAPA_A: dict[str, str] = {
    "<nombre real del .md que imprimio el paso 2>": "<sha256 real que imprimio el paso 2>",
    ...
}
```

- [ ] **Step 4: Confirmar que el golden es estable — dos ejes, no uno**

Primero, que el `.eml` sea idéntico byte a byte entre construcciones (es el eje que falló en la
revisión adversarial, y correr el test dos veces **no** lo habría distinguido de una ruta absoluta
filtrada):

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -c "import hashlib,sys; sys.path.insert(0,'tests'); from test_email_atomize_firma_veto import _eml, _HTML_FIRMA_ENTRE_CITAS as H; print({hashlib.sha256(_eml('<c@example.invalid>','Firma entre citas',fecha='Sat, 5 Jul 2025 10:00:00 +0200',html=H)).hexdigest() for _ in range(4)})"
```

Esperado: un `set` de **un solo elemento**. Si salen 4, falta el `set_boundary` del paso 1.

Después, el test dos veces seguidas:

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_firma_veto.py
```

Esperado: **PASS** las dos. Si la segunda falla con el `.eml` ya estable, el no-determinismo está en
el motor (una ruta absoluta, un orden de `dict`/`set`, un locale): **parar**, identificar el campo y
documentarlo. **No** relajar el test a «al menos una ficha» ni excluir el `sha256` del hash — eso
enmascararía justo lo que el golden vigila.

- [ ] **Step 5: Commit**

```bash
git add tests/test_email_atomize_firma_veto.py
git commit -m "test(email_atomize): golden de Capa A capturado ANTES del arreglo de la firma"
```

---

### Task 2: El parser marca los trozos de firma y `_sandwich` los ignora

**Files:**
- Modify: `core/email_atomize/inline.py` — `Segmentacion` (471-476), `_QuoteHTMLParser` (662-743),
  `_sandwich` (746-756), `segmentar_html` (759-782)
- Test: `tests/test_email_atomize_inline.py`

**Interfaces:**
- Produces:
  - `Segmentacion.firma_excluida: int` — trozos de firma descartados del veto, **y solo cuando la
    exclusión cambió el veredicto**; `0` en cualquier otro caso. Lo consume la Tarea 3.
  - `_QuoteHTMLParser.firma_trozos: int` — trozos marcados como firma en esta pasada.
  - `_sandwich(seq: list[str], *, firma_como_autor: bool = False) -> bool`.
  - Tokens de módulo `_TOK_CITA = "Q"`, `_TOK_AUTOR = "A"`, `_TOK_FIRMA = "S"`.

**Qué defectos matan los tests de esta tarea:**
- Test 1 (nuevo): que la firma entre citas siga vetando la Capa B — el defecto que abre la SPEC.
- Test 3 (nuevo): que el arreglo se convierta en «desactivar el detector» cuando hay firma **y**
  texto de autor real. Es la forma real de 2 de los 4 portadores que conservan el veto
  (`A S5 Q S3 Q S20 A3 Q3`).
- Test 2 (**ya existe**, línea 175): que el arreglo desactive el detector en el caso ordinario.

- [ ] **Step 1: Escribir los tres tests (dos fallan hoy, uno es guarda verde previa)**

Añadir en `tests/test_email_atomize_inline.py`, justo **después** de
`test_seg_html_token_conservacion_no_inventa` (línea 184), este bloque:

```python
# ---------------------------------------------------------------------------
# T7-bis — la firma no es una respuesta intercalada (spec 2026-07-29, §6)
# ---------------------------------------------------------------------------

_FIRMA_HTML = ('<div class="gmail_signature"><div>Un saludo</div>'
               '<div>Nombre Sintetico</div><div>Engel y Voelkers</div></div>')


def test_seg_html_firma_entre_citas_no_es_intercalada():
    """Contrato §6.1: la firma de E&V va linea a linea en su propio elemento y en los hilos de
    Gmail queda ENTRE dos citas. Eso NO es texto de autor intercalado.

    Forma medida en el corpus real: `S3 Q S Q S3` (aqui, con el saludo delante: A S3 Q S3 Q)."""
    html = ('<div>Buenos dias, adjunto lo pedido.</div>'
            + _FIRMA_HTML +
            '<blockquote>cita uno</blockquote>'
            + _FIRMA_HTML +
            '<blockquote>cita dos</blockquote>')
    s = I.segmentar_html(html)
    assert s.respuesta_intercalada is False
    assert len(s.ancestros) == 2
    assert s.firma_excluida == 6      # 3 lineas x 2 firmas, y el veto cambio de veredicto


def test_seg_html_autor_entre_firmas_mantiene_veto():
    """Contrato §6.3: si entre las citas hay un trozo que NO es firma, el veto sigue puesto.
    La exclusion es aditiva: resta firma del recuento, nunca levanta un veto correcto.
    Es la forma real de 2 de los 4 portadores que conservan el veto."""
    html = ('<blockquote>cita uno</blockquote>'
            + _FIRMA_HTML +
            '<div>Esto no lo aceptamos</div>'
            + _FIRMA_HTML +
            '<blockquote>cita dos</blockquote>')
    s = I.segmentar_html(html)
    assert s.respuesta_intercalada is True and s.ancestros == []


def test_seg_html_firma_sin_cerrar_no_levanta_el_veto():
    """Contrato §6.8 (añadido por la revision adversarial, hallazgo B0). Un
    `<div class="gmail_signature">` que NUNCA se cierra deja `_sigdepth > 0` para el resto del
    documento y marca como firma TODO el texto de autor posterior: la exclusion levantaria un
    veto CORRECTO, que es la unica direccion en la que esta regla no puede fallar.

    Fail-closed: si la firma queda abierta, sus trozos vuelven a contar como autor. Medido: la
    firma queda abierta en 20 de 271 correos reales (5 de 24 en la prueba de Gmail, 15 de 247
    en W-02VND1) -- el defecto estaba ARMADO, solo que todavia no habia disparado."""
    html = ('<blockquote>cita uno</blockquote>'
            '<div class="gmail_signature">Un saludo'            # <-- nunca se cierra
            '<div>Esto no lo aceptamos y es texto de autor real</div>'
            '<blockquote>cita dos</blockquote>')
    s = I.segmentar_html(html)
    assert s.respuesta_intercalada is True and s.ancestros == []
    assert s.motivo == "firma_sin_cerrar"   # y se DECLARA, no se veta en silencio
    assert s.firma_excluida == 0
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_inline.py -k "firma" -v
```

Esperado:
- `test_seg_html_firma_entre_citas_no_es_intercalada` → **FAIL**, por
  `AttributeError: 'Segmentacion' object has no attribute 'firma_excluida'` o antes por
  `assert s.respuesta_intercalada is False` (hoy es `True`: es el defecto).
- `test_seg_html_firma_sin_cerrar_no_levanta_el_veto` → **FAIL** por
  `AttributeError`/`assert s.motivo == "firma_sin_cerrar"`. Hoy el veto está puesto por la razón
  equivocada (todo veta), así que este test **no** vale como verde previo: solo prueba algo cuando
  el guard existe.
- `test_seg_html_autor_entre_firmas_mantiene_veto` → **PASS** ya hoy (hoy todo veta). Se escribe
  ahora porque su trabajo es **quedarse verde** después del cambio; escrito después, no probaría que
  el arreglo no lo rompió.

- [ ] **Step 3: Añadir el campo a `Segmentacion`**

En `core/email_atomize/inline.py`, sustituir el bloque de la línea 471:

```python
@dataclass
class Segmentacion:
    autor: str = ""
    ancestros: list = field(default_factory=list)
    respuesta_intercalada: bool = False
    motivo: str = ""
```

por:

```python
@dataclass
class Segmentacion:
    autor: str = ""
    ancestros: list = field(default_factory=list)
    respuesta_intercalada: bool = False
    motivo: str = ""
    # Trozos de firma descartados del veto de `_sandwich`, y SOLO cuando esa exclusion cambio
    # el veredicto (spec 2026-07-29 §5.1). Transporta la traza hasta `reconstruir`.
    firma_excluida: int = 0
```

- [ ] **Step 4: Declarar los tokens y el marcador de firma**

En `core/email_atomize/inline.py`, insertar justo **antes** de
`class _QuoteHTMLParser(HTMLParser):` (662), después del `from html.parser import HTMLParser`:

```python
# --- Contenedor de firma (spec 2026-07-29 §3) ------------------------------------------
# El predicado es ESTRUCTURAL: se escribe sobre `class`/`id`, nunca sobre el texto. Una lista
# de palabras ya se descarto por fragil y medida: 7 de 21 trozos se escapaban porque eran solo
# el NOMBRE de la persona. `gmail_signature` es el unico marcador necesario — medido sobre el
# corpus real: anadir "signature" o "firma" a esta tupla NO cambia ningun veredicto, porque los
# 28 trozos de firma de la muestra ya caen bajo `gmail_signature` (cubre tambien
# `gmail_signature_prefix` por ser subcadena). La tupla es el punto de extension cuando
# aparezca un cliente que marque su firma de otra forma.
_SIG_MARKERS = ("gmail_signature",)

_TOK_CITA = "Q"      # contenedor de cita
_TOK_AUTOR = "A"     # texto fuera de la cita
_TOK_FIRMA = "S"     # texto fuera de la cita PERO bajo un contenedor de firma
```

- [ ] **Step 5: Marcar los trozos de firma en el parser**

Cinco ediciones en `_QuoteHTMLParser`. El trozo **sigue enrutándose igual** (va a `author_parts` y
cuenta en `tokens_total`): lo único que cambia es el token de `seq`.

(5a) En `__init__`, después de `self._skip = 0 # >0 dentro de <style>/<script>/<head>`:

```python
        self._sigdepth = 0                    # >0 dentro de un contenedor de firma
        self.firma_trozos = 0                 # trozos de autor marcados como firma
```

(5b) Añadir el predicado justo después de `_is_container`:

```python
    @staticmethod
    def _is_signature(tag: str, attrs: list) -> bool:
        d = dict(attrs)
        val = f"{d.get('class') or ''} {d.get('id') or ''}".lower()
        return any(m in val for m in _SIG_MARKERS)
```

(5c) Sustituir `handle_starttag` entero por:

```python
    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP_TAGS:
            self._skip += 1
            self._tags.append((tag, False, False))
            return
        cont = self._is_container(tag, attrs)
        if cont and self.qdepth >= self._MAX_DEPTH:
            cont = False  # tope de profundidad: absorbe el contenido en el segmento actual
        sig = self._is_signature(tag, attrs)
        self._tags.append((tag, cont, sig))
        if sig:
            self._sigdepth += 1
        if cont:
            self.qdepth += 1
            self.seq.append(_TOK_CITA)
            seg = {"depth": self.qdepth, "anchor": self._anchor_actual(), "body": []}
            self.segments.append(seg)
            self.seg_stack.append(seg)
            self._pending_parts = []
        elif tag in self._BLOCK_TAGS:
            self._pending_parts = []   # nuevo bloque → el anclaje es solo el bloque anterior
```

(5d) Sustituir `handle_endtag` entero por (el desanidado de la firma va **fuera** de la cadena
`if/elif`: un contenedor puede ser cita **o** firma, y el contador de firma debe bajar en cualquier
caso):

```python
    def handle_endtag(self, tag: str) -> None:
        for k in range(len(self._tags) - 1, -1, -1):
            t, cont, sig = self._tags[k]
            if t == tag:
                del self._tags[k]
                if t in self._SKIP_TAGS:
                    self._skip = max(0, self._skip - 1)
                elif cont:
                    self.qdepth = max(0, self.qdepth - 1)
                    if self.seg_stack:
                        self.seg_stack.pop()
                    self._pending_parts = []   # texto tras una cita cerrada no es anclaje de la anterior
                if sig:
                    self._sigdepth = max(0, self._sigdepth - 1)
                break
```

(5e) Sustituir `handle_data` entero por:

```python
    def handle_data(self, data: str) -> None:
        if self._skip or not data.strip():
            return
        self.tokens_total += len(data.split())
        if self.qdepth == 0 or not self.seg_stack:   # guard: nunca se cae texto al vacío
            self.author_parts.append(data)           # el enrutado NO cambia (spec §3)
            if self._sigdepth:
                self.seq.append(_TOK_FIRMA)
                self.firma_trozos += 1
            else:
                self.seq.append(_TOK_AUTOR)
        else:
            self.seg_stack[-1]["body"].append(data)
        self._pending_parts.append(data)
```

- [ ] **Step 6: Enseñar a `_sandwich` a ignorar la firma**

Sustituir `_sandwich` (746-756) entero por:

```python
def _sandwich(seq: list[str], *, firma_como_autor: bool = False) -> bool:
    """¿Hay texto de autor (A) ENTRE dos citas (Q)? = respuesta intercalada en HTML.

    Los trozos bajo un contenedor de firma llegan como ``_TOK_FIRMA`` y NO cuentan como texto
    de autor (spec 2026-07-29 §3): la firma de E&V va linea a linea en su propio elemento y en
    los hilos de Gmail queda ENTRE dos citas. La exclusion es ADITIVA — si queda un trozo de
    autor real, esto sigue devolviendo True (medido: 4 de los 7 portadores vetados de la muestra
    lo siguen estando).

    *firma_como_autor* recupera el veredicto de ANTES de la exclusion. Su unico uso es saber si
    la exclusion cambio el veredicto, para emitir la traza (§5.1).
    """
    seen_q = seen_a_after_q = False
    for t in seq:
        if t == _TOK_CITA:
            if seen_a_after_q:
                return True
            seen_q = True
        elif seen_q and (t == _TOK_AUTOR or (firma_como_autor and t == _TOK_FIRMA)):
            seen_a_after_q = True
    return False
```

- [ ] **Step 7: El guard fail-closed de la firma sin cerrar**

En `segmentar_html`, sustituir las dos líneas del veto (767-768):

```python
    if _sandwich(p.seq):
        return Segmentacion(autor=_html_a_texto(html), ancestros=[], respuesta_intercalada=True)
```

por:

```python
    # FAIL-CLOSED (hallazgo B0 de la revision adversarial, reproducido): si al cerrar el
    # documento queda un contenedor de firma SIN CERRAR, `_sigdepth` nunca volvio a 0 y TODO el
    # texto de autor posterior quedo marcado como firma. Excluirlo del veto levantaria un veto
    # CORRECTO -- la unica direccion en la que esta regla NO puede fallar (spec §3). Cuando la
    # firma no es fiable, sus trozos vuelven a contar como autor.
    # `HTMLParser.close()` no sintetiza cierres ni lanza excepcion, asi que el fallback a texto
    # plano de mas abajo no cubre este caso.
    # Medido: la firma queda abierta en 20 de 271 correos reales (5 de 24 en la prueba de Gmail,
    # 15 de 247 en W-02VND1) y el guard NO cuesta ni un portador desbloqueado: 3 con guard y 3
    # sin guard. El defecto estaba armado y no habia disparado.
    firma_fiable = p._sigdepth == 0
    if _sandwich(p.seq, firma_como_autor=not firma_fiable):
        # Se declara SOLO cuando el desbalance es lo que sostiene el veto; si no, seria ruido
        # en el 7 % de correos que cierran con la firma abierta sin consecuencia.
        mot = "" if firma_fiable or _sandwich(p.seq) else "firma_sin_cerrar"
        return Segmentacion(autor=_html_a_texto(html), ancestros=[],
                            respuesta_intercalada=True, motivo=mot)
```

- [ ] **Step 8: Poblar `firma_excluida` en `segmentar_html`**

En `segmentar_html`, sustituir el bloque que va desde `autor = "\n".join(...)` hasta el `return`
final por:

```python
    autor = "\n".join(t.strip() for t in p.author_parts).strip()
    ancestros = [
        Segmento(texto="\n".join(t.strip() for t in s["body"]).strip(),
                 anclaje_texto=s["anchor"], profundidad=s["depth"], estilo="html_quote",
                 estructural=True)
        for s in p.segments
    ]
    # Traza (spec §5.1): SOLO cuando la exclusion de firma cambio el veredicto, no en cada correo
    # con firma. Llegar aqui ya implica `firma_fiable`.
    firma_excluida = p.firma_trozos if _sandwich(p.seq, firma_como_autor=True) else 0
    # Conservación de tokens (DD §2.4): todo texto enrutado debe repartirse entre autor y
    # segmentos. Si diverge (bug de enrutado), NO segmentar: portador entero a revisión.
    # `firma_excluida` SI se arrastra a esta rama: la exclusion cambio el veredicto de `_sandwich`
    # aunque la conservacion vete despues por otra razon, y el puntero de `conservacion_tokens` no
    # informa de ese cambio (hallazgo A de la revision adversarial, aceptado).
    repartidos = len(autor.split()) + sum(len(a.texto.split()) for a in ancestros)
    if p.tokens_total and abs(repartidos - p.tokens_total) > 0.05 * p.tokens_total:
        return Segmentacion(autor=_html_a_texto(html), ancestros=[],
                            motivo="conservacion_tokens", firma_excluida=firma_excluida)
    return Segmentacion(autor=autor, ancestros=ancestros, respuesta_intercalada=False,
                        firma_excluida=firma_excluida)
```

- [ ] **Step 9: Correr los tests de `inline`**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_inline.py -v
```

Esperado: **todo PASS**, y en particular estos cuatro:
- `test_seg_html_firma_entre_citas_no_es_intercalada` → PASS (era FAIL)
- `test_seg_html_firma_sin_cerrar_no_levanta_el_veto` → PASS (era FAIL)
- `test_seg_html_autor_entre_firmas_mantiene_veto` → PASS
- `test_seg_html_intercalada_no_segmenta` (el que ya existía, test 2 del contrato) → **PASS**. Si
  este se pone rojo, **el arreglo está desactivando el detector**: parar y revisar los pasos 6-7, no
  editar el test.

- [ ] **Step 10: Correr el golden de la Tarea 1**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_firma_veto.py -v
```

Esperado: **PASS**. El golden filtra por `capa: A`, así que las fichas de Capa B que el arreglo acaba
de hacer aparecer no lo afectan. Si falla, una ficha de **Capa A** se ha movido: parar, es el riesgo
material del cambio y **no** se resuelve actualizando el golden.

- [ ] **Step 11: Commit**

```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "fix(email_atomize): la firma no cuenta como texto de autor en el veto de _sandwich"
```

---

### Task 3: La traza — puntero `info` cuando la exclusión cambió el veredicto

**Files:**
- Modify: `core/email_atomize/inline.py` — `reconstruir` (934-947)
- Test: `tests/test_email_atomize_firma_veto.py`

**Interfaces:**
- Consumes: `Segmentacion.firma_excluida` (Tarea 2); `SegmentoEnterrado` de
  `core.email_atomize.model` (campos `portador_msg_id`, `estilo`, `profundidad`, `de`, `confianza`,
  `motivo`, `extracto`, todos con default).
- Produces: fila en `_revision/cola.md` con `Estilo = firma_excluida_del_veto`, `Confianza = info`,
  `Motivo = trozos_firma=<n>`.

**Qué defecto mata el test:** que el arreglo silencie un detector sin dejar rastro. La SPEC lo exige
como condición de la decisión (§3: «deja rastro… no se silencia un detector, se corrige y se
declara»). Y comprueba la consecuencia visible: el portador arreglado **deja** de aparecer con
`intercalada_no_segmentada`, que hoy es su único registro, mientras el de intercalada real **sigue**
apareciendo.

- [ ] **Step 1: Escribir el test que falla**

Añadir al final de `tests/test_email_atomize_firma_veto.py`:

```python
# --- Test 6 del contrato: la traza se emite una vez, para el portador correcto -----------

def test_traza_firma_excluida_una_vez_y_sin_intercalada_no_segmentada(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    _corpus(src)
    P.atomize_dir(src, out)
    cola = (out / "_revision" / "cola.md").read_text(encoding="utf-8")
    filas = [l for l in cola.splitlines() if l.startswith("| MSG-")]

    # Los MSG-id se resuelven desde el registro, NO desde la fila encontrada: derivarlos de la
    # propia traza dejaba pasar el mutante intercambiado (traza para b, `no_seg` para c), que es
    # exactamente el defecto que este test existe para matar.
    # TRAMPA: los Message-ID se guardan SIN los angulos (`.strip("<>")`) -> la llave del registro
    # es "c@example.invalid", nunca "<c@example.invalid>".
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    msg_b = reg["mensajes"]["b@example.invalid"]["id"]
    msg_c = reg["mensajes"]["c@example.invalid"]["id"]

    trazas = [l for l in filas if "firma_excluida_del_veto" in l]
    assert len(trazas) == 1, f"la traza debe emitirse UNA vez; filas: {filas}"
    assert "| info |" in trazas[0]
    assert "trozos_firma=7" in trazas[0]   # 3 + 1 + 3 lineas de firma en _HTML_FIRMA_ENTRE_CITAS
    assert trazas[0].split("|")[1].strip() == msg_c, (
        f"la traza es de OTRO portador: se esperaba {msg_c}; fila: {trazas[0]}")

    # El portador arreglado (c) deja de declararse sin segmentar; el de intercalada REAL (b)
    # sigue declarandose, porque su veto es correcto. Se fija la lista EXACTA.
    no_seg = [l.split("|")[1].strip() for l in filas if "intercalada_no_segmentada" in l]
    assert no_seg == [msg_b], (
        f"intercalada_no_segmentada debe ser exactamente [{msg_b}]; es {no_seg}")
```

- [ ] **Step 2: Correr el test para verificar que falla**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q "tests/test_email_atomize_firma_veto.py::test_traza_firma_excluida_una_vez_y_sin_intercalada_no_segmentada" -v
```

Esperado: **FAIL** en `assert len(trazas) == 1` con `0` trazas — el contador ya se calcula (Tarea 2)
pero nadie lo convierte en puntero.

- [ ] **Step 3: Emitir el puntero en `reconstruir`**

En `core/email_atomize/inline.py`, dentro de `reconstruir`, **después** del bloque
`if seg_total.motivo:` (944-947) y **antes** del `for seg in seg_total.ancestros:`, insertar:

```python
    if seg_total.firma_excluida:
        # spec 2026-07-29 §5.1: la correccion del veto deja rastro. Solo se emite cuando la
        # exclusion CAMBIO el veredicto (lo garantiza `firma_excluida`), no en cada correo con
        # firma.
        res.punteros.append(SegmentoEnterrado(
            portador_msg_id=m_a.msg_id, estilo="firma_excluida_del_veto", confianza="info",
            motivo=f"trozos_firma={seg_total.firma_excluida}", extracto=""))
```

- [ ] **Step 4: Correr el fichero de tests**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q tests/test_email_atomize_firma_veto.py -v
```

Esperado: **PASS** los dos tests (golden + traza).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/inline.py tests/test_email_atomize_firma_veto.py
git commit -m "feat(email_atomize): traza en _revision cuando la exclusion de firma cambia el veto"
```

---

### Task 4: Emparejamiento remitente ↔ cuerpo, contra el motor real

Es el test 4 del contrato y el que la revisión adversarial reclamó con más razón: **construyó un
adversario en el que el remitente era literal y el cuerpo pertenecía a otro autor**. Que el email
aparezca en el `.eml` no prueba nada; hay que fijar **qué remitente va con qué cuerpo**.

**Comprobado empíricamente antes de escribir este plan** (con el veto retirado a mano sobre el
fixture de la Tarea 1): el motor produce **2 candidatos**, `ana@example.invalid` con
`CUERPO-DE-ANA` y `bea@example.invalid` con `CUERPO-DE-BEA`, ambos `media-reconstruida` por
`atribucion_cuerpo`, y **0 punteros**. No es una expectativa deducida.

**Files:**
- Test: `tests/test_email_atomize_firma_veto.py`

**Interfaces:**
- Consumes: `_corpus`, `atomize_dir` (Tarea 1); el arreglo de las Tareas 2-3.

**Qué defecto mata:** una misatribución — que la ficha de Ana lleve el cuerpo de Bea, o al revés. Es
el fallo más caro que este cambio puede introducir, porque las fichas nuevas entran como prueba.

- [ ] **Step 1: Escribir el test**

Añadir al final de `tests/test_email_atomize_firma_veto.py`:

```python
# --- Test 4 del contrato: remitente <-> cuerpo, contra el motor real ---------------------

def test_firma_excluida_empareja_cada_remitente_con_su_cuerpo(tmp_path):
    """El portador `c.eml` cita a Ana y a Bea. Tras excluir la firma del veto, la Capa B produce
    DOS fichas y cada una debe llevar el cuerpo de SU autor. La revision adversarial construyo
    el adversario contrario (remitente literal + cuerpo de otro): esto lo mata.

    El emparejamiento es la asercion DURA: no se relaja nunca. El numero de fichas esta medido
    (2), y si el motor diera otro numero hay que entender por que antes de tocar nada."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    _corpus(src)
    P.atomize_dir(src, out)

    fichas = {}
    for p in sorted((out / "mensajes").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        if _capa(txt) == "B":
            de = next(l.split(":", 1)[1].strip() for l in _frontmatter(txt).splitlines()
                      if l.startswith("de:"))
            fichas[de] = txt

    # DURO: cada remitente con su cuerpo, en las dos direcciones.
    for de, marca_propia, marca_ajena in (
            ("ana@example.invalid", "CUERPO-DE-ANA", "CUERPO-DE-BEA"),
            ("bea@example.invalid", "CUERPO-DE-BEA", "CUERPO-DE-ANA")):
        assert de in fichas, f"falta la ficha B de {de}; hay: {sorted(fichas)}"
        assert marca_propia in fichas[de], f"la ficha de {de} no lleva su propio cuerpo"
        assert marca_ajena not in fichas[de], f"MISATRIBUCION: la ficha de {de} lleva {marca_ajena}"

    # Medido: exactamente estas dos, ninguna mas.
    assert set(fichas) == {"ana@example.invalid", "bea@example.invalid"}, (
        f"fichas B inesperadas: {sorted(fichas)}")

    # Y la PROCEDENCIA tambien: las dos se reconstruyeron del portador `c`, no de otro. Sin esto,
    # una procedencia equivocada pasaria el test (hallazgo de la revision adversarial).
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    msg_c = reg["mensajes"]["c@example.invalid"]["id"]
    for de, txt in fichas.items():
        assert f"reconstruido_de: {msg_c}" in _frontmatter(txt), (
            f"la ficha de {de} dice venir de otro portador; se esperaba {msg_c}")
```

- [ ] **Step 2: Correr el test**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q "tests/test_email_atomize_firma_veto.py::test_firma_excluida_empareja_cada_remitente_con_su_cuerpo" -v
```

Esperado: **PASS** (medido antes de escribir el plan). Reacción correcta si no:

- **FAIL en `falta la ficha B de …`** → la atribución no llegó. **NO se relaja la aserción.**
  Diagnóstico, en este orden:
  1. `print((out / "_revision" / "cola.md").read_text(encoding="utf-8"))` y leer `Motivo`:
     `sin_cabecera` significa que ni el anclaje ni `_cabecera_head` reconocieron nada.
  2. Comprobar que la dirección llega **con ángulos** al texto: los fixtures usan `&lt;`/`&gt;`
     precisamente porque con ángulos literales `HTMLParser` se los come y la guarda G5 nunca afirma
     remitente (ver Global Constraints).
  3. Comprobar que el bloque `De:/Enviado:/Para:/Asunto:` está **al principio** del cuerpo citado:
     `_cabecera_head` solo mira el bloque contiguo al inicio, a propósito (no fabrica remitente con
     un `De:` disperso).
  4. Las fechas citadas deben ser **anteriores** a la del portador (`5 jul 2025`).
- **FAIL en `MISATRIBUCION`** → es el fallo real que este test existe para cazar. **Parar y
  reportar**: no se sigue adelante con el plan.

- [ ] **Step 3: Commit**

```bash
git add tests/test_email_atomize_firma_veto.py
git commit -m "test(email_atomize): cada ficha nueva lleva el cuerpo de SU remitente (anti-misatribucion)"
```

---

### Task 5: Suite completa y verificación en vivo

**Files:** ninguno (solo verificación) salvo lo que destape.

- [ ] **Step 1: Suite completa**

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m pytest -q --tb=short --junit-xml=suite.xml
```

Esperado: **0 failures, 0 errors**, y el total en **2547 + 6 nuevos = 2553** (77 skipped). Leer el
conteo del `suite.xml`, no del resumen por tubería. Borrar `suite.xml` antes de commitear (no va al
árbol).

Comprobar a mano que estos dos siguen verdes, porque son los que este cambio podría romper:
- `tests/test_email_atomize_inline.py::test_seg_html_intercalada_no_segmenta` (test 2 del contrato)
- `tests/test_email_atomize_segmenter.py::test_cortar_autor_intercalada_no_corta` — regresión de
  `cortar_autor`, el detector que **no** se ha tocado. **Ojo al alcance:** es **un** caso sintético,
  no los 16 medidos que pide el §6.7 de la SPEC. Esos 16 son correo real y no pueden vivir como
  fixture; se comprueban en el paso 2 (verificación en vivo). No dar este test por cobertura del
  contrato entero — corrección aceptada de la revisión adversarial.

- [ ] **Step 1-bis: Re-medir la errata con el parser INTEGRADO, antes de escribirla**

La cifra 3 se midió con una subclase de `_QuoteHTMLParser` en un script de scratch. Hereda del
parser real y usa el `_html_part` real, así que las divergencias que la revisión adversarial temía
(selección MIME, `_MAX_DEPTH`, `_BLOCK_TAGS`, `_anchor_actual`, `_SKIP_TAGS`) **no aplican**. Pero la
confirmación es barata y la errata va a una SPEC adjudicada, así que se hace con el código
integrado, llamando a `segmentar(raw)` de verdad:

```python
# Script de scratch (NO va al repo). Solo agregados; ningun contenido de correo.
from pathlib import Path
from core.email_atomize import inline as I
n_html = n_veto = n_sin_cerrar = 0
for p in sorted(Path(r"C:\Users\tnm33\Desktop\_PRUEBA_98_VaRS3").rglob("*.eml")):
    html = I._html_part(p.read_bytes())
    if not html.strip():
        continue
    n_html += 1
    s = I.segmentar_html(html)
    n_veto += s.respuesta_intercalada
    n_sin_cerrar += (s.motivo == "firma_sin_cerrar")
print(f"con HTML={n_html} vetados AHORA={n_veto} firma_sin_cerrar={n_sin_cerrar}")
```

Esperado con la medición previa: `con HTML=24`, `vetados AHORA=4` (eran 7 → **3 desbloqueados**),
`firma_sin_cerrar=0`. **Si el número no es 3, el que vale es este** y la errata de la Tarea 6 se
escribe con él.

- [ ] **Step 2: Verificación en vivo (SPEC §8) — pedir autorización a Nikolai antes de lanzarla**

Corre sobre las dos carpetas del Escritorio de la prueba de `W-02TH0W`: `_PRUEBA_98_VaRS3` (29
`.eml`) y `_PRUEBA_98_VaRS3_atomizado` (su árbol). **Es correo real de cliente: no sale de ahí, y se
borra cuando esta verificación esté hecha.** No se ejecuta sobre `G:` sin el sí explícito.

Snapshot antes → corrida → snapshot después. Las herramientas de snapshot/comparación de la sesión
del 2026-07-29 están en el scratchpad
(`snapshot_capa_a.py`, `comparar_capa_a.py`); si ya no existen, el patrón es: un dict
`{ruta relativa: sha256}` de todo el árbol de salida más los mapas de identidad de `_registro.json`
(`mensajes`, `mensajes_fp`, `adjuntos`, `_contadores`), comparado antes/después.

```bash
"C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe" -m scripts.atomize_emails --src "C:/Users/tnm33/Desktop/_PRUEBA_98_VaRS3" --out "C:/Users/tnm33/Desktop/_PRUEBA_98_VaRS3_atomizado"
```

Los cuatro puntos de la SPEC §8, con la expectativa **corregida**:
- (a) **cuántas fichas nuevas** aparecen. El techo es **3 portadores desbloqueados** (medido, no los
  5 de la SPEC). De cuántos de esos 3 sale ficha es lo que esta corrida mide por primera vez: dos de
  ellos tienen forma idéntica (`S5 Q S3 Q S20`) y anclajes `[VACIO, con-texto]`, así que es probable
  que sean el mismo hilo. **El número que vale es el de aquí**; anotarlo en la Tarea 6.
- (b) en cada ficha nueva, **el remitente va con su cuerpo** — una a una, contra el `.eml`.
- (c) las fichas que **ya existían** son byte-idénticas.
- (d) el **puntero de traza** está en `_revision/cola.md`, con una fila por portador arreglado, y los
  **4** portadores cuyo veto es correcto siguen declarados como `intercalada_no_segmentada`.
- (e) `upgrades`: la SPEC espera 0. Si aparecen, significa que esas citas eran copias de mensajes que
  ya son ficha — resultado válido, pero hay que verlo y anotarlo (SPEC §5.1).
- (f) **El test 7 del contrato, aquí y no en la suite:** los **16 casos de intercalada real medidos**
  (15 de W-02VND1 + 1 de la prueba) conservan el cuerpo íntegro. Es correo real, así que se comprueba
  sobre el corpus, no como fixture. Basta el agregado: cuántos de esos 16 tienen
  `cuerpo_recortado_cita` en su ficha (esperado: ninguno) — la regresión de `cortar_autor`, que este
  cambio no toca.

- [ ] **Step 3: Contraprueba en W-02VND1 — la regla no debe cambiar nada**

La SPEC §8 lo señala como comprobación en sí misma: en W-02VND1 el único portador con veto es un
contraejemplo legítimo y debe **seguir vetado**. Se hace sobre la **copia local** del Escritorio
(`BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta`), nunca sobre `G:`, con el mismo patrón de snapshot.
Esperado: 0 fichas nuevas, 0 trazas de `firma_excluida_del_veto`, Capa A intacta.

> Aviso medido el 2026-07-29 (`MEJORAS #99.5`): esa copia local ya arrastra 4 gemelos NFD de
> adjuntos y un artefacto viejo en `_revision/`, de la verificación de `MEJORAS #98`. **No son
> regresión de este cambio**; al comparar, ignorar los ficheros de `adjuntos/` y `_revision/` que ya
> estuvieran duplicados antes de esta corrida.

---

### Task 6: Errata de la SPEC, docs y PR

**Files:**
- Modify: `docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Errata en la SPEC**

Añadir un bloque `> **Errata (fecha, este plan):**` al final de §2.2 y otro en §5, con la corrección
5→3, su evidencia (24 portadores con HTML, 7 vetados, 3 cambian de veredicto, insensible al conjunto
de marcadores) y el motivo del error (2 de los 4 que conservan el veto sí tienen firma, pero además
tienen texto de autor entre la segunda y la tercera cita). **No reescribir las cifras originales en
su sitio**: la SPEC rev. 2 está adjudicada y el precedente del repo es dejar la errata visible junto
al dato viejo, como se hizo con el §12 de la SPEC del workspace dual.

Corregir también la expectativa de §8 («5 segmentan, ~2 producen ficha» → techo 3) con el número que
midió la Tarea 5.

- [ ] **Step 2: `PLAN.md` — «en revisión», SIN número de PR ni hash**

En el bloque `[SIGUIENTE-SANDWICH-FIRMA]`: dejar la fila 12 y sus casillas en **«construido, en
revisión»**, y anotar el **reparto real** medido en el paso 2 de la Tarea 5. Añadir el recordatorio
de la SPEC §5.1 que es fácil de olvidar: **los sellos anteriores son inmutables** — si se revisan las
fichas nuevas de un caso con entrega ya sellada, hay que **sellar una entrega nueva** (`--entrega`),
no dar por actualizada la anterior.

**No poner aquí el `✅` con el número de PR y el hash del squash:** el PR se abre en el paso 3 y el
hash no existe hasta el merge, así que no cabe en el commit que va a ser squashado. Eso es trabajo
del **cierre de sesión**, que es su hogar según `CLAUDE.md` («el estado de ciclo de vida de un ítem
vive solo en `PLAN.md`… al cerrar un ítem se pone `✅` + hash del PR»). Dependencia temporal
imposible detectada por la revisión adversarial.

- [ ] **Step 3: PR**

```bash
git push -u origin claude/sandwich-firma
```

Abrir el PR y esperar `leak-scan` verde. **El CI no corre pytest**: el conteo del paso 1 de la Tarea
5 es la única red y va en el cuerpo del PR, junto al resultado de la verificación en vivo y la errata
de la cifra.

- [ ] **Step 4: Tras el merge — cierre y borrado del corpus**

En este orden, y no antes:

1. `✅` + número de PR + hash del squash en `PLAN.md` (fila 12 y su bloque), en el cierre de sesión.
2. **Pedir autorización explícita a Nikolai** y entonces borrar del Escritorio `_PRUEBA_98_VaRS3` y
   `_PRUEBA_98_VaRS3_atomizado`. Es correo real de cliente y su única razón de estar ahí era esta
   verificación — pero **no se borra antes del merge**: si la revisión del PR obliga a repetir una
   medición, esa evidencia local es la única que hay. Conservar el informe **agregado** de la
   verificación (cifras, sin contenido) en el cuerpo del PR o en la bitácora.

---

## Adjudicación de la revisión adversarial (Codex, 2026-07-29) — NO EJECUTABLE, remediado

Veredicto recibido: **NO EJECUTABLE**, 4 bloqueantes + 4 altos + 1 menor. **Ocho aceptados, uno
parcialmente refutado.** Todo lo aceptado está aplicado arriba. Los dos bloqueantes de fondo se
**reprodujeron ejecutando**, no por lectura.

| # | Sev | Hallazgo | Adjudicación |
|---|---|---|---|
| 1 | B0 | El golden es inestable: `add_alternative()` + `as_bytes()` genera una frontera MIME **aleatoria**, y el sha del raw entra en la ficha | **CONFIRMADO ejecutando**: 4 serializaciones → 4 sha. Y mi paso 4 proponía el arreglo **equivocado** («excluir el campo del hash»), que habría enmascarado justo lo que el golden vigila. Arreglado con `set_boundary` + una comprobación de determinismo del `.eml` separada de la del motor |
| 2 | B0 | Una firma **sin cerrar** deja `_sigdepth > 0` y **levanta un veto correcto** | **CONFIRMADO ejecutando**: `Q S2 Q`, `_sigdepth=1`, veto `True → False` sobre texto de autor real, y la conservación de tokens no lo bloquea. Contradice la afirmación central de la SPEC §3. Arreglado con guard fail-closed + test propio. **Ampliación medida:** la firma queda abierta en **20 de 271** correos reales (5/24 y 15/247) y en ninguno llegaba a disparar — estaba **armado sin haber disparado**, la misma forma que tenía `#98`. El guard **no cuesta nada**: 3 portadores desbloqueados con y sin él |
| 3 | B0 | El test de traza derivaba el portador **de la propia fila**, así que el mutante intercambiado pasaba | **ACEPTADO**. Era un test casi vacuo de mi cosecha, exactamente la familia contra la que este repo lleva cuatro. Arreglado resolviendo los `MSG-id` desde `_registro.json` y fijando la lista exacta |
| 4 | B0 | La Tarea 6 pedía número de PR y hash de squash **antes** de que existieran | **ACEPTADO** en sustancia (la severidad es discutible: es orden de docs, no código roto). El arreglo coincide con la regla de `CLAUDE.md`: el `✅ + hash` es del cierre, tras el merge |
| 5 | A | `firma_excluida` se perdía en la rama `conservacion_tokens` | **ACEPTADO**. Mi decisión era defendible, pero la lectura literal del §5.1 y el valor informativo ganan: el puntero de `conservacion_tokens` no informa del cambio de veredicto |
| 6 | A | El test 7 del contrato son **16 casos medidos**, no el único sintético que ya existe | **ACEPTADO**: mi plan sobreafirmaba la cobertura. Los 16 son correo real → van a la verificación en vivo (Tarea 5, punto f), y el test unitario se declara por lo que es |
| 7 | A | La errata 5→3 se midió con una reimplementación, no con el parser real | **PARCIALMENTE REFUTADO**: el script **subclasea** `_QuoteHTMLParser` y usa el `_html_part` real, así que las divergencias que lista (selección MIME, `qdepth`, `_MAX_DEPTH`, `seg_stack`, HTML malformado) **no aplican** — es el parser del repo con los tres métodos del plan. **Aceptado en su conclusión**: la confirmación con el código integrado es barata y la errata va a una SPEC adjudicada → Tarea 5, paso 1-bis, **antes** de escribirla |
| 8 | A | El plan borraba el corpus **antes** de abrir y validar el PR | **ACEPTADO**, y con razón doble: pierde la evidencia si la revisión obliga a repetir, y era una acción destructiva sobre correo real sin autorización propia |
| 9 | M | `capa: A` se buscaba en todo el documento, no solo en el frontmatter | **ACEPTADO**: `render_md` concatena frontmatter y cuerpo. Arreglado con un `_frontmatter()`/`_capa()` que solo miran el primer bloque |
| — | — | Nota de su §3: el test 4 no comprobaba `reconstruido_de` | **ACEPTADO y verificado**: el campo existe (`model.py:80`, `render.py:66`) — no era un detalle inventado. Añadida la aserción de procedencia |

**Lo que su §4 dio por verificado y coincide con mi propia lectura:** no hay otros consumidores de
`self._tags`; un contenedor que sea a la vez cita y firma **bien cerrado** queda balanceado; el tope
`_MAX_DEPTH` no desbalancea `sig`; `estilo`/`motivo` son vocabularios abiertos y `confianza="info"` ya
se usa; el campo nuevo de `Segmentacion` lleva default; `_sandwich` no tiene otro call-site; y ningún
fixture existente contiene `gmail_signature`.

**Su §5 no aportó ataque a la decisión de diseño**, y coincido: el fallo de `_sigdepth` es una omisión
del plan de implementación, no una refutación de la exclusión estructural.

## Fuera de alcance (registrado, no se construye aquí)

- **La ficha de identidad cierta para intercaladas reales** — backlog, SPEC §7.
- **El test vacuo `test_seg_html_token_conservacion_no_inventa`** — `MEJORAS #107`, ya anotado.
- **El contenido de los adjuntos en MD** — `MEJORAS #87`. **El consumo por la sala de lectura** —
  `MEJORAS #86`.
- **Los 2 portadores con firma que conservan el veto por texto de autor entre la 2ª y la 3ª cita**
  (forma `A S5 Q S3 Q S20 A3 Q3`): quedan vetados y es correcto que lo estén con la información
  disponible. Si algún día se quisiera segmentar la parte no controvertida de un portador así, es un
  diseño nuevo (segmentación parcial), no un ajuste de este detector.
- **Un cliente de correo que no envuelva su firma en un contenedor identificable**: el falso positivo
  persiste ahí, aceptado y declarado (SPEC §7). La regla no puede fallar en la dirección peligrosa —
  si no reconoce la firma, el veto se mantiene.
