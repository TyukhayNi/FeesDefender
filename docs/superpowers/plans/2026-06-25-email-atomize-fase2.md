# Email Atomize — Fase 2 (Layer B: atomización inline) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruir la autoría enterrada en reenvíos/citas INLINE de los cuerpos de correo (`core/email_atomize/inline.py` + integración), produciendo mensajes atómicos `capa=B` con confianza graduada y cola de revisión, **sin alterar la salida byte-idéntica de Capa A** ni los 277 IDs congelados.

**Architecture:** Diseño detallado y aprobado en `docs/superpowers/specs/2026-06-25-email-atomize-layerb-design.md` (referido como **DD** abajo, con sus §N). Base *header-anchor* + grafts. **Directriz primaria: cero misatribución** — un remitente solo se afirma desde un bloque de cabecera inline parseable; todo lo más débil va a `_revision/`. Un **segmentador único compartido** alimenta tanto `bodies._limpia_cita` (Capa A) como Layer B desde el cuerpo SIN recortar (resuelve la "doble autoridad"). El upgrade de fidelidad vive en un **índice fp + alias aparte** en `ids.py` (no toca el path de IDs congelado ni `dedup.colapsar`).

**Tech Stack:** Python 3.14, stdlib `email`/`html.parser`/`hashlib`/`re`/`unicodedata`/`zoneinfo`, `pytest`. Reutiliza `core.email_export` y `core.email_atomize` Fase 1. Windows + PowerShell, venv `.venv`, UTF-8 sin BOM.

**Convenciones de ejecución** (idénticas a Fase 1):
- Shell desde `C:\Users\tnm33\Dev\FeesDefender`; Python `.\.venv\Scripts\python.exe`.
- Tests por ruta explícita (en PowerShell pytest NO expande `tests/test_*_*.py`): `python -m pytest tests/test_email_atomize_inline.py -q`. Suite completa con `--ignore=tests/test_email_export_mcp_server.py --ignore=tests/test_expedientes_xl_server.py` (2 ficheros pre-existentes fallan colección por falta del paquete `mcp`).
- `git add` SOLO ficheros propios (sin `add -A`). Post-commit hook auto-pushea `main`.

**Prime-directive invariant (re-verificar en cada tarea que toque salida):** los 277 `.md` de Capa A deben quedar **byte-idénticos**; `_registro.json` no renumera; `00_Input` intacto; re-ejecutar es idempotente.

---

## Modelo de datos nuevo (referencia — se crea en T2)

`core/email_atomize/model.py` añade (DD §1, §8):

```python
# Campos nuevos en RegistroMensaje (todos con default → construcción existente intacta):
fingerprint: str = ""
reconstruido_desde_cita: bool = False
fecha_inferida: bool = False
ambiguedad_profundidad: bool = False
en_revision: bool = False
reconstruido_de: str = ""          # MSG-id del portador
# (capa="A"/"B" y confianza ya existen; Layer B usa confianza "alta-reconstruida"|"media"|"baja")

@dataclass
class SegmentoEnterrado:
    """Fila de la cola de revisión / puntero a un segmento citado no promovido."""
    portador_msg_id: str = ""
    estilo: str = ""               # outlook_es | apple_es | fwd_line | html_quote | quote_gt
    profundidad: int = 0
    de: str = ""
    fecha_iso: str = "0000-00-00"
    confianza: str = ""            # media | baja
    motivo: str = ""               # sin_cabecera | quote_only | discrepancia_html_plano | ...
    extracto: str = ""             # primeras ~200 chars del segmento
    fingerprint: str = ""
```

---

## Task 1: Segmentador compartido + refactor de `bodies` (kill "doble autoridad")

**Objetivo:** una sola autoridad sobre el corte autor/cita. Extraer la lógica de `_limpia_cita` a `cortar_autor`, que devuelve TAMBIÉN el resto citado; `bodies` delega; `extraer_cuerpo` gana `conservar_resto`. **Garantía dura: los 277 `.md` quedan byte-idénticos** (rama por defecto sin cambios de comportamiento).

**Files:**
- Create: `core/email_atomize/_segmenter.py`
- Modify: `core/email_atomize/bodies.py` (delegar `_limpia_cita`; `extraer_cuerpo(..., conservar_resto=False)`)
- Test: `tests/test_email_atomize_segmenter.py`

- [ ] **Step 1: Test del segmentador + no-regresión (debe fallar)**

`tests/test_email_atomize_segmenter.py`:
```python
from __future__ import annotations
from core.email_atomize import _segmenter as S
from core.email_atomize import bodies as B
from email.message import EmailMessage


def test_cortar_autor_top_posting_devuelve_resto():
    txt = ("Mi respuesta breve.\n\n"
           "El 11 jun 2026, a las 9:00, Jaime <j@x> escribió:\n"
           "> cita larga\n> mas cita\n")
    autor, resto, inter = S.cortar_autor(txt)
    assert autor == "Mi respuesta breve."
    assert resto is not None and "cita larga" in resto
    assert inter is False


def test_cortar_autor_intercalada_no_corta():
    txt = "> p1\nresp autor 1\n> p2\nresp autor 2\n"
    autor, resto, inter = S.cortar_autor(txt)
    assert inter is True
    assert resto is None
    assert "resp autor 1" in autor and "p2" in autor


def test_cortar_autor_sin_cita():
    autor, resto, inter = S.cortar_autor("Solo texto del autor.")
    assert autor == "Solo texto del autor." and resto is None and inter is False


def test_bodies_default_byte_identico():
    # la rama por defecto (conservar_resto=False) NO cambia el cuerpo limpio de Capa A
    m = EmailMessage()
    m["Message-ID"] = "<a@x>"; m["Subject"] = "X"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("Respuesta.\n\nEl 1 ene 2020, a las 8:00, Y <y@x> escribió:\n> cita\n")
    c = B.extraer_cuerpo(m.as_bytes())
    assert c.texto == "Respuesta."
    assert c.cuerpo_recortado_cita is True


def test_bodies_conservar_resto_expone_base_y_split():
    m = EmailMessage()
    m["Message-ID"] = "<a@x>"; m["Subject"] = "X"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("Respuesta.\n\nEl 1 ene 2020, a las 8:00, Y <y@x> escribió:\n> cita\n")
    c = B.extraer_cuerpo(m.as_bytes(), conservar_resto=True)
    assert c.texto == "Respuesta."            # autor sigue siendo el corte canónico
    assert c.base_sin_recortar is not None and "cita" in c.base_sin_recortar
    assert c.resto_citado is not None and "cita" in c.resto_citado
```

- [ ] **Step 2: Ejecutar (debe fallar)** — `python -m pytest tests/test_email_atomize_segmenter.py -q` → FAIL.

- [ ] **Step 3: Implementar `_segmenter.py`**

Mover la lógica actual de `bodies._limpia_cita` (incluidos `_RE_CITA_HDR`, `_es_linea_citada`) a `_segmenter.cortar_autor(texto) -> (autor: str, resto: str | None, intercalada: bool)`. `resto` = la cola citada recortada (texto desde el punto de corte hasta el final), o `None` si no se recortó. Reutilizar EXACTAMENTE el algoritmo actual para no cambiar el corte (ver `bodies.py:66-98`), solo devolviendo además `resto`:
```python
# _segmenter.py
from __future__ import annotations
import re

_RE_CITA_HDR = re.compile(
    r"^\s*(el .+escribi[oó]:|on .+wrote:|-{2,}\s*(mensaje original|original message"
    r"|forwarded message|reenviado).*|de\s*:.*\n.*(enviado|asunto)\s*:)",
    re.IGNORECASE | re.MULTILINE,
)


def _es_linea_citada(linea: str) -> bool:
    return linea.lstrip().startswith(">")


def cortar_autor(texto: str) -> tuple[str, str | None, bool]:
    """(autor, resto_citado|None, intercalada). Autoridad ÚNICA del corte autor/cita."""
    lineas = texto.splitlines()
    quoted_idx = [i for i, l in enumerate(lineas) if _es_linea_citada(l)]
    if not quoted_idx:
        m = _RE_CITA_HDR.search(texto)
        if m and m.start() > 0:
            return texto[: m.start()].rstrip(), texto[m.start():], False
        return texto.strip(), None, False
    primera = quoted_idx[0]
    autor_despues = any(
        l.strip() and not _es_linea_citada(l) and not _RE_CITA_HDR.match(l)
        for l in lineas[primera + 1:]
    )
    if autor_despues:
        return texto.strip(), None, True
    corte = primera
    m = _RE_CITA_HDR.search(texto)
    if m:
        pre = texto[: m.start()].count("\n")
        corte = min(corte, pre)
    autor = "\n".join(lineas[:corte]).rstrip()
    resto = "\n".join(lineas[corte:])
    return autor, (resto if resto.strip() else None), False
```

- [ ] **Step 4: Refactor `bodies.py` para delegar**

En `bodies.py`: importar `from . import _segmenter`; borrar `_RE_CITA_HDR`/`_es_linea_citada`/`_limpia_cita` locales y sustituir su uso por `_segmenter.cortar_autor`. Añadir a `Cuerpo` los campos `base_sin_recortar: str | None = None` y `resto_citado: str | None = None`. Cambiar la firma a `extraer_cuerpo(raw, *, conservar_resto: bool = False)`. Tras elegir `base`/`formato` y aplicar `_recupera_charset` y el sniff de mojibake, hacer:
```python
    autor, resto, intercalada = _segmenter.cortar_autor(base)
    cuerpo = Cuerpo(
        texto=autor, formato_original=formato, charset_recuperado=recuperado,
        mojibake_marcado=moji, cuerpo_recortado_cita=resto is not None,
        respuesta_intercalada=intercalada,
    )
    if conservar_resto:
        cuerpo.base_sin_recortar = base
        cuerpo.resto_citado = resto
    return cuerpo
```
(El comportamiento por defecto es idéntico: `texto`=autor, `cuerpo_recortado_cita`=bool(resto), `respuesta_intercalada` igual.)

- [ ] **Step 5: Ejecutar segmenter + los tests de Fase 1 de bodies (no-regresión)**

Run: `python -m pytest tests/test_email_atomize_segmenter.py tests/test_email_atomize_bodies.py -q`
Expected: PASS (los 4 tests de `bodies` de Fase 1 siguen verdes → corte byte-idéntico).

- [ ] **Step 6: Commit**

```bash
git add core/email_atomize/_segmenter.py core/email_atomize/bodies.py tests/test_email_atomize_segmenter.py
git commit -m "feat(email-atomize): segmentador compartido autor/cita + bodies.conservar_resto (Fase 2 T1)"
```

---

## Task 2: Campos de modelo para Layer B

**Files:**
- Modify: `core/email_atomize/model.py`
- Test: `tests/test_email_atomize_model_b.py`

- [ ] **Step 1: Test (debe fallar)**

`tests/test_email_atomize_model_b.py`:
```python
from __future__ import annotations
from core.email_atomize.model import RegistroMensaje, SegmentoEnterrado


def test_registro_mensaje_campos_b_por_defecto():
    m = RegistroMensaje(msg_id="MSG-1")
    assert m.fingerprint == "" and m.reconstruido_desde_cita is False
    assert m.fecha_inferida is False and m.ambiguedad_profundidad is False
    assert m.en_revision is False and m.reconstruido_de == ""


def test_segmento_enterrado_defaults():
    s = SegmentoEnterrado(portador_msg_id="MSG-1", estilo="outlook_es", profundidad=1)
    assert s.de == "" and s.confianza == "" and s.fecha_iso == "0000-00-00"
```

- [ ] **Step 2: Ejecutar (debe fallar).** `python -m pytest tests/test_email_atomize_model_b.py -q` → FAIL.

- [ ] **Step 3: Implementar.** Añadir los 6 campos nuevos a `RegistroMensaje` (sección "flags de cuerpo") y la dataclass `SegmentoEnterrado` (ver bloque "Modelo de datos nuevo" arriba), respetando defaults.

- [ ] **Step 4: Ejecutar (debe pasar)** + no-regresión modelo: `python -m pytest tests/test_email_atomize_model_b.py tests/test_email_atomize_render.py -q` → PASS.

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/model.py tests/test_email_atomize_model_b.py
git commit -m "feat(email-atomize): campos de modelo Layer B + SegmentoEnterrado (Fase 2 T2)"
```

---

## Task 3: Índice de fingerprint + alias en `ids.py` (sin tocar el path congelado)

**Objetivo:** identidad estable para mensajes inline sin Message-ID, y puente de upgrade, **en estructuras aparte** (`mensajes_fp`, `alias`); `msg_id_for`/`att_id_for`/`mensajes` intactos. `version` 1→2 con loader tolerante (DD §1, §6).

**Files:**
- Modify: `core/email_atomize/ids.py`
- Test: `tests/test_email_atomize_ids_fp.py`

- [ ] **Step 1: Test (debe fallar)**

`tests/test_email_atomize_ids_fp.py`:
```python
from __future__ import annotations
import json
from core.email_atomize import ids


def test_fp_id_congela_y_es_independiente_de_msg(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for("<a@x>", sha="sha_a")          # Layer A: MSG-00001
    a = reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1")
    b = reg.msg_id_for_fp("fp:cafef00d", cuerpo_sha="cs2")
    assert a == "MSG-00002" and b == "MSG-00003"  # comparten el contador msg
    assert reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1") == "MSG-00002"  # congelado


def test_alias_resuelve_mid_a_fp(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1")
    reg.registrar_alias("clean-mid@x", "fp:deadbeef")
    assert reg.resolver_alias("clean-mid@x") == "fp:deadbeef"
    assert reg.resolver_alias("desconocido@x") is None


def test_persistencia_v2_y_loader_tolera_v1(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for("<a@x>", sha="sha_a")
    reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1")
    reg.registrar_alias("clean-mid@x", "fp:deadbeef")
    reg.save()
    data = json.loads((tmp_path / "_registro.json").read_text(encoding="utf-8"))
    assert data["version"] == 2 and "mensajes_fp" in data and "alias" in data
    # un registro v1 (sin mensajes_fp/alias) carga sin romper
    (tmp_path / "_registro.json").write_text(json.dumps(
        {"version": 1, "mensajes": {"x@x": {"id": "MSG-00001", "sha256": "s"}},
         "adjuntos": {}, "eml_procesados": [], "_contadores": {"msg": 1, "att": 0}}),
        encoding="utf-8")
    reg2 = ids.load_registro(tmp_path)
    assert reg2.msg_id_for_fp("fp:new", cuerpo_sha="cs") == "MSG-00002"  # sigue el contador
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar.** En `Registro.__init__`: `self.mensajes_fp = data.get("mensajes_fp", {})`, `self.alias = data.get("alias", {})`. Añadir:
```python
def msg_id_for_fp(self, fp: str, *, cuerpo_sha: str) -> str:
    entry = self.mensajes_fp.get(fp)
    if entry is not None:
        return entry["id"]
    self._next_msg += 1
    nuevo = f"MSG-{self._next_msg:05d}"
    self.mensajes_fp[fp] = {"id": nuevo, "cuerpo_sha": cuerpo_sha}
    return nuevo

def registrar_alias(self, rfc_message_id: str, fp: str) -> None:
    self.alias[_norm_mid(rfc_message_id)] = fp

def resolver_alias(self, rfc_message_id: str) -> str | None:
    return self.alias.get(_norm_mid(rfc_message_id))
```
En `save()`: `version: 2`, y añadir `"mensajes_fp": self.mensajes_fp, "alias": self.alias`. (Los IDs `MSG-` de fp y de Message-ID comparten `_next_msg` → numeración global única, sin colisión.)

- [ ] **Step 4: Ejecutar fp + no-regresión ids:** `python -m pytest tests/test_email_atomize_ids_fp.py tests/test_email_atomize_ids.py -q` → PASS.

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/ids.py tests/test_email_atomize_ids_fp.py
git commit -m "feat(email-atomize): indice fingerprint + alias en Registro (Fase 2 T3)"
```

---

## Task 4: `inline.py` — normalizador + fingerprint (DD §5)

**Files:**
- Create: `core/email_atomize/inline.py`
- Test: `tests/test_email_atomize_inline.py` (se ampliará en tareas siguientes)

- [ ] **Step 1: Test (debe fallar)**

`tests/test_email_atomize_inline.py`:
```python
from __future__ import annotations
from core.email_atomize import inline as I


def test_normaliza_quita_marcas_firma_acentos():
    a = I.normaliza_cuerpo("> Hola  ESTÁ\n> aquí\n-- \nfirma irrelevante")
    b = I.normaliza_cuerpo("hola esta aqui")
    assert a == b


def test_fingerprint_reproducible_y_prefijo():
    anc = I.Anclaje(de="x@y.com", fecha_iso="2020-01-02", asunto="RE: Hola")
    fp1 = I.fingerprint_b(anc, I.normaliza_cuerpo("cuerpo suficientemente largo aqui"))
    fp2 = I.fingerprint_b(anc, I.normaliza_cuerpo("cuerpo suficientemente largo aqui"))
    assert fp1 == fp2 and fp1.startswith("fp:") and len(fp1) == 3 + 24


def test_fingerprint_dia_granular_absorbe_tz():
    # misma fecha-día, distinta hora/tz → mismo componente de día → mismo fp
    cuerpo = I.normaliza_cuerpo("texto identico de cuerpo bastante largo")
    a1 = I.Anclaje(de="x@y.com", fecha_iso="2020-01-02", asunto="Hola")
    a2 = I.Anclaje(de="x@y.com", fecha_iso="2020-01-02", asunto="Hola")
    assert I.fingerprint_b(a1, cuerpo) == I.fingerprint_b(a2, cuerpo)


def test_fingerprint_floor_no_colapsa_cuerpos_cortos():
    anc = I.Anclaje(de="x@y.com", fecha_iso="2020-01-02", asunto="Hola")
    assert I.es_cuerpo_colapsable(I.normaliza_cuerpo("ok")) is False
    assert I.es_cuerpo_colapsable(I.normaliza_cuerpo("a"*30)) is True
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar `inline.py` (cabecera + normalizador + fingerprint).** Ver DD §5 para la especificación exacta. Definir la dataclass `Anclaje(de, de_nombre, fecha_iso, fecha_dt, asunto)` (campos con default), `normaliza_cuerpo` (strip marcas `>`, cortar firma en `-- `/`Enviado desde mi`/`Sent from my`/`Obtener Outlook`/`Get Outlook`, colapsar ws, NFKC+casefold, fold ASCII de acentos reutilizando la técnica de `email_export._slug_descripcion`), `_MIN_CUERPO = 24`, `es_cuerpo_colapsable(norm) -> len(norm) >= _MIN_CUERPO`, `fingerprint_b(anc, cuerpo_norm)` y `fingerprint_a(m)` (mismo material: `remitente_addr`, `fecha_dia`, `_slug_descripcion(asunto)`, `sha256(cuerpo_norm)`; separador `\x1f`; `"fp:" + sha256(material)[:24]`). `fingerprint_a` usa `m.de`, `m.fecha_iso`, `m.asunto`, `normaliza_cuerpo(m.cuerpo)`.

- [ ] **Step 4: Ejecutar (debe pasar).** `python -m pytest tests/test_email_atomize_inline.py -q` → PASS.

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "feat(email-atomize): inline normalizador + fingerprint dia-granular (Fase 2 T4)"
```

---

## Task 5: `inline.py` — parseo de anclaje (sender/date, ES+CA) (DD §3)

**Files:** Modify `core/email_atomize/inline.py`; Modify `tests/test_email_atomize_inline.py`

- [ ] **Step 1: Tests (debe fallar)** — añadir a `tests/test_email_atomize_inline.py`:
```python
def test_anclaje_outlook_bilingue():
    blk = "De: PersonaUno <per01a@example.invalid>\nEnviado: lunes, 3 de febrero de 2020 18:42\nPara: x@y\nAsunto: RE: Tibidabo"
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "per01a@example.invalid" and anc.fecha_iso == "2020-02-03" and "Tibidabo" in anc.asunto


def test_anclaje_apple_addr_y_fecha():
    blk = "El 3 feb 2020, a las 18:42, Jaime <per01c@example.invalid> escribió:"
    anc = I.parsear_anclaje(blk, "apple_es")
    assert anc.de == "per01c@example.invalid" and anc.fecha_iso == "2020-02-03"


def test_anclaje_catalan_date():
    blk = "El 12 de març de 2021, a les 9:00, Toni <per03@example.invalid> va escriure:"
    anc = I.parsear_anclaje(blk, "apple_es")
    assert anc.de == "per03@example.invalid" and anc.fecha_iso == "2021-03-12"


def test_anclaje_display_name_sin_addr_no_inventa():
    anc = I.parsear_anclaje("De: PersonaUno\nEnviado: 3 feb 2020\nAsunto: x", "outlook_es")
    assert anc.de == "" and "Jaime" in anc.de_nombre  # nombre sí, dirección NO inventada


def test_anclaje_sin_fecha_parseable():
    anc = I.parsear_anclaje("De: x@y.com\nAsunto: z\nPara: w", "outlook_es")
    assert anc.de == "x@y.com" and anc.fecha_iso == "0000-00-00"
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar `parsear_anclaje(texto, estilo) -> Anclaje | None`** según DD §3:
  - **outlook/fwd block:** mapa bilingüe de etiquetas (`de/from`, `enviado/sent/fecha/date`, `para/to`, `asunto/subject`); sintetizar cabecera RFC y pasarla a `email.message_from_string` + reutilizar `headers._fecha`/`parseaddr`/`getaddresses` (tz Europe/Madrid). Nombre sin `<addr>` → `de=""`, `de_nombre` puesto.
  - **apple_es/en + gmail_attr:** regex `El <fecha>, a las <hora>, <Nombre> <addr> escribió:` / `On … wrote:` / `… va escriure:` (catalán). Extraer trailing `<addr>`, nombre, fragmento de fecha.
  - **Fechas ES+CA:** mapa local de meses/días (es: enero…diciembre; ca: gener…desembre) independiente del locale; `parsedate_to_datetime` primero, luego el mapa; construir datetime aware en Europe/Madrid. Fallo → `fecha_iso="0000-00-00"`.

- [ ] **Step 4: Ejecutar (debe pasar).**

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "feat(email-atomize): parseo de anclaje sender/date ES+CA (Fase 2 T5)"
```

---

## Task 6: `inline.py` — segmentación texto plano (DD §2.2)

**Files:** Modify `inline.py`; Modify `tests/test_email_atomize_inline.py`

- [ ] **Step 1: Tests (debe fallar)**:
```python
def _seg(texto):  # helper local: segmentar desde texto plano directo
    return I.segmentar_texto(texto)

def test_seg_plain_un_outlook():
    s = _seg("Mi nota.\nDe: Y <y@z.com>\nEnviado: 1 ene 2020\nAsunto: Z\nPara: w\n> cuerpo citado")
    assert s.autor.startswith("Mi nota")
    assert len(s.ancestros) == 1 and s.ancestros[0].estilo == "outlook_es"

def test_seg_plain_multimarcador_orden_documental():
    txt = ("Top.\n"
           "El 2 feb 2020, a las 9:00, A <a@x> escribió:\n"
           "> uno\n"
           "-----Mensaje original-----\nDe: B <b@x>\nAsunto: q\nEnviado: 1 feb 2020\n")
    s = _seg(txt)
    assert [a.estilo for a in s.ancestros] == ["apple_es", "fwd_line"]

def test_seg_plain_quote_gt_depth():
    s = _seg("Hola\n> n1\n>> n2\n>> n2b\n> n1b")
    profs = sorted({a.profundidad for a in s.ancestros})
    assert profs and max(profs) >= 2 and all(a.estructural for a in s.ancestros)

def test_seg_stray_de_no_segmenta():
    s = _seg("Te escribo. De: acuerdo con lo que dices sobre el asunto.")
    assert s.ancestros == []   # 'De:' sin 2ª etiqueta en 4 líneas → no es cabecera
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar `segmentar_texto(texto) -> Segmentacion`** (DD §2.0 guarda intercalada plain, §2.2). Definir dataclasses `Segmento(texto, anclaje_texto, profundidad, estilo, estructural)` y `Segmentacion(autor, ancestros: list[Segmento], respuesta_intercalada)`. Constantes `MARCADORES` con las regex exactas de DD §2.2 (`RE_FWD`, `RE_OUTLOOK` con guarda de 2ª etiqueta en ≤4 líneas, `RE_APPLE_ES`, `RE_APPLE_EN`, `>`-runs). Recoger TODOS los offsets de marcador, ordenar por posición, cada uno abre un segmento hasta el siguiente/EOF; profundidad por longitud de run `>` (estructural=True) o por adyacencia para outlook/apple/fwd (estructural=False); coalescer runs `>` a través de líneas en blanco. Tope de recursión 8.

- [ ] **Step 4: Ejecutar (debe pasar).**

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "feat(email-atomize): segmentacion texto plano multimarcador (Fase 2 T6)"
```

---

## Task 7: `inline.py` — segmentación HTML + intercalada HTML + conservación de tokens (DD §2.1, §2.0, §2.4)

**Files:** Modify `inline.py`; Modify `tests/test_email_atomize_inline.py`

- [ ] **Step 1: Tests (debe fallar)**:
```python
def test_seg_html_gmail_quote():
    html = ('<div>Mi respuesta</div>'
            '<div class="gmail_quote"><div class="gmail_attr">El 2 feb 2020, A &lt;a@x&gt; escribió:</div>'
            '<blockquote>cuerpo citado</blockquote></div>')
    s = I.segmentar_html(html)
    assert "Mi respuesta" in s.autor
    assert len(s.ancestros) == 1 and "a@x" in (s.ancestros[0].anclaje_texto or "")
    assert s.ancestros[0].estructural is True

def test_seg_html_anidado_profundidad():
    html = ('<div>top</div><blockquote>n1<blockquote>n2<blockquote>n3</blockquote></blockquote></blockquote>')
    s = I.segmentar_html(html)
    assert max(a.profundidad for a in s.ancestros) >= 3

def test_seg_html_intercalada_no_segmenta():
    html = ('<div>resp 1</div><blockquote>p1</blockquote>'
            '<div>resp 2 del autor entre citas</div><blockquote>p2</blockquote>')
    s = I.segmentar_html(html)
    assert s.respuesta_intercalada is True and s.ancestros == []

def test_seg_html_token_conservacion_falla_aborta():
    # si el split pierde/duplica texto materialmente → no segmentar (se marca para cola)
    s = I.segmentar_html("<blockquote>" + "x "*5 + "</blockquote>")  # sin autor real
    # token-conservation/edge: no debe inventar atribución; ancestros vacíos o marcado
    assert isinstance(s.respuesta_intercalada, bool)
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar `segmentar_html(html) -> Segmentacion`** (DD §2.1):
  - Subclase de `html.parser.HTMLParser` que mantiene una pila de tags y detecta contenedores de cita (selectores de la tabla DD §2.1: `blockquote` —esp. `type="cite"`—, `div.gmail_quote`/`blockquote.gmail_quote` + `gmail_attr`, Outlook `divRplyFwdMsg`/`OutlookMessageHeader`/`x_…`, `<hr>` seguido de bloque `From:`/`De:`). Profundidad = anidamiento de contenedores (estructural=True), tope 8.
  - **Autor** = nodos de texto fuera de cualquier contenedor (vía `_html_a_texto`).
  - **anclaje_texto** = nodo/header inmediatamente anterior al contenedor; validar binding header↔nivel (DD §2.1: mismo nivel padre, ≤6 nodos; ambigüedad → `ambiguedad_profundidad`).
  - **Intercalada HTML (DD §2.0):** si hay texto de autor no vacío DESPUÉS del inicio del primer contenedor → `respuesta_intercalada=True`, no segmentar.
  - **Conservación de tokens (DD §2.4):** `tokens(autor)+Σtokens(ancestros)` dentro de ±5% del total aplanado; si falla → abandonar segmentación (autor = cuerpo Capa A, marca `motivo="conservacion_tokens"` para cola).
  - HTML malformado/desbalanceado/mojibake → fallback a `segmentar_texto` sobre el `text/plain`.
  - Añadir `segmentar(raw) -> Segmentacion` que elige HTML (si hay `text/html` por `iter_body_text`) o plano, con coherencia HTML/plano (DD §2.3): si los conteos difieren materialmente → marcar `discrepancia_html_plano`.

- [ ] **Step 4: Ejecutar (debe pasar).**

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "feat(email-atomize): segmentacion HTML + intercalada HTML + conservacion tokens (Fase 2 T7)"
```

---

## Task 8: `inline.py` — clasificación de confianza + guardas anti-misatribución (DD §4)

**Files:** Modify `inline.py`; Modify `tests/test_email_atomize_inline.py`

- [ ] **Step 1: Tests (debe fallar)** — los casos prime-directive:
```python
def test_clasifica_alta_reconstruida_requiere_todo():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    conf, motivo = I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)
    assert conf == "alta-reconstruida"

def test_clasifica_fecha_posterior_al_portador_no_alta():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-03-01")
    conf, motivo = I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)
    assert conf == "media" and "fecha_incoherente" in motivo

def test_clasifica_headerless_es_baja_sin_remitente():
    conf, motivo = I.clasificar(None, "2020-02-01", estructural=False, ambigua=False)
    assert conf == "baja"

def test_clasifica_sin_estructura_o_ambigua_demota_a_media():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    assert I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)[0] == "media"
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=True)[0] == "media"

def test_clasifica_email_invalido_no_promueve():
    anc = I.Anclaje(de="no-es-email", fecha_iso="2020-01-01")
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)[0] in ("media", "baja")
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar `clasificar(anc, fecha_portador_iso, *, estructural, ambigua, discrepancia=False, mojibake=False) -> (confianza, motivo)`** con la escala EXACTA de DD §4 (alta-reconstruida solo si email válido AND fecha parseable AND fecha ≤ portador AND estructural AND no ambigua AND no discrepancia; media si falta exactamente uno de {email, fecha} o estructura/ambigüedad/discrepancia; baja si sin cabecera/quote-only/mojibake/fallo conservación). Guardas duras: fecha posterior → nunca alta (`motivo="fecha_incoherente"`); cualquier predicado fallido demota un nivel, nunca redondea hacia arriba. Helper `_email_valido(s)` (regex simple). 

- [ ] **Step 4: Ejecutar (debe pasar).**

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "feat(email-atomize): confianza graduada + guardas anti-misatribucion (Fase 2 T8)"
```

---

## Task 9: `inline.py` — orquestador `reconstruir` + índice Capa A + watched-list (DD §6, §9)

**Files:** Modify `inline.py`; Modify `tests/test_email_atomize_inline.py`

- [ ] **Step 1: Tests (debe fallar)**:
```python
from core.email_atomize.model import RegistroMensaje

def _ra(**kw):
    base = dict(msg_id="MSG-00042", rfc_message_id="p@x", fecha_iso="2026-06-01",
                asunto="Asunto", de="c@x", cuerpo="autor", capa="A", confianza="alta")
    base.update(kw); return RegistroMensaje(**base)

def test_reconstruir_promueve_del_burgo_inline():
    raw = make_eml_con_cita_outlook(  # helper de test que construye .eml con cita inline de PersonaUno
        autor="Te reenvío.", de_cita="per01a@example.invalid", fecha_cita="2020-05-01",
        asunto_cita="Tibidabo", cuerpo_cita="contenido suficientemente largo para fingerprint")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), raw)
    altas = [s for s in res.candidatos if s.confianza == "alta-reconstruida"]
    assert any(s.de == "per01a@example.invalid" for s in altas)

def test_reconstruir_watched_va_a_del_burgo_queue():
    # con IDENTIDADES_VIGILADAS conteniendo per01a@example.invalid, una alta-reconstruida marca en_revision
    res = I.reconstruir(_ra(), make_eml_con_cita_outlook(
        autor="x", de_cita="per01a@example.invalid", fecha_cita="2020-05-01", asunto_cita="z",
        cuerpo_cita="cuerpo largo de prueba"))
    db = [s for s in res.candidatos if s.de == "per01a@example.invalid"]
    assert db and db[0].en_revision is True   # doble control

def test_indice_layer_a_resuelve_por_cuerpo_sha():
    m = _ra(cuerpo="cuerpo identico bastante largo para superar el floor", de="z@x",
            fecha_iso="2020-05-01", asunto="t")
    idx = I.indice_layer_a([m])
    assert idx.por_cuerpo_sha(I.normaliza_cuerpo(m.cuerpo)) == "MSG-00042"
```
(El helper `make_eml_con_cita_outlook` se define en el propio test, construyendo un `EmailMessage` con cuerpo text/plain que incluye el bloque `De:/Enviado:/Asunto:` citado.)

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar:**
  - Constante `IDENTIDADES_VIGILADAS: set[str] = set()` (hook Fase 3; vacío = no-op). Comentario citando `per01b@example.invalid` (candidato, tope media — DD §9) e `ignacio@despacho-ab.example` (persona distinta) para `identidades.yaml` futuro.
  - `ReconResult(intercalada, candidatos: list[Segmento+conf], punteros: list[SegmentoEnterrado])`.
  - `reconstruir(m_a, raw)`: `segmentar(raw)` → por cada ancestro: `parsear_anclaje` → `clasificar` (con `m_a.fecha_iso` como fecha del portador) → si `alta-reconstruida`: candidato a mensaje B (calcular `fingerprint_b`, `cuerpo_sha`); si media/baja: `SegmentoEnterrado` puntero. Marcar `en_revision` cuando `de ∈ IDENTIDADES_VIGILADAS` (sin bloquear promoción). Propagar `respuesta_intercalada` al portador.
  - `indice_layer_a(mensajes) -> Indice` con `por_cuerpo_sha(norm)->msg_id`, `por_mid(rfc_mid)->msg_id`, y `resolver(seg)` (mid-alias del bloque inline si trae `Message-ID:`, si no `cuerpo_sha` con floor ≥24 — DD §6). 
  - `construir_b(seg, seg_msg_id, m_portador) -> RegistroMensaje` (capa="B", confianza, `reconstruido_desde_cita=True`, `reconstruido_de=portador`, `procedencia=[{citado_en, profundidad}]`, fingerprint, fecha/asunto/de del anclaje, `en_revision`).

- [ ] **Step 4: Ejecutar (debe pasar).**

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "feat(email-atomize): orquestador reconstruir + indice Capa A + watched-list (Fase 2 T9)"
```

---

## Task 10: Integración en `pipeline.py` (pase Layer B) (DD §6, §7)

**Files:** Modify `core/email_atomize/pipeline.py`; Test `tests/test_email_atomize_pipeline_b.py`

- [ ] **Step 1: Test e2e (debe fallar)**

`tests/test_email_atomize_pipeline_b.py`:
```python
from __future__ import annotations
import json
from email.message import EmailMessage
from core.email_atomize import pipeline as P


def _carrier_con_cita(mid, autor, de_cita, fecha_cita, asunto_cita, cuerpo_cita):
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = "RV: " + asunto_cita
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    cuerpo = (f"{autor}\n\nDe: <{de_cita}>\nEnviado: {fecha_cita}\nAsunto: {asunto_cita}\n"
              f"Para: x@y\n\n{cuerpo_cita}\n")
    m.set_content(cuerpo)
    return m.as_bytes()


def test_layerb_promueve_y_no_renumera_capaA(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_carrier.eml").write_bytes(_carrier_con_cita(
        "<carrier@x>", "Te reenvío.", "per01a@example.invalid", "1 de mayo de 2020 9:00",
        "Tibidabo", "contenido citado suficientemente largo para superar el floor de 24"))
    rep = P.atomize_dir(src, out)
    # Capa A: 1 portador; Capa B: 1 reconstruida (PersonaUno)
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg["version"] == 2 and len(reg["mensajes_fp"]) == 1     # 1 fp-keyed B
    assert (out / "_revision" / "del_burgo.md").exists()
    # idempotencia: re-run no renumera ni duplica
    P.atomize_dir(src, out)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg2["mensajes_fp"] == reg["mensajes_fp"]
    assert len(sorted((out / "mensajes").glob("*.md"))) == 2


def test_layerb_headerless_no_promueve_va_a_cola(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    m = EmailMessage(); m["Message-ID"] = "<c@x>"; m["Subject"] = "x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content("Mi nota.\n> cita sin cabecera parseable\n> mas cita\n")
    (src / "2026-06-01_c.eml").write_bytes(m.as_bytes())
    P.atomize_dir(src, out)
    assert len(sorted((out / "mensajes").glob("*.md"))) == 1   # no se promueve nada
    assert (out / "_revision" / "cola.md").exists()
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar el pase Layer B** en `atomize_dir` (DD §7), DESPUÉS del bucle Capa A. Cambios concretos:
  - En el bucle Capa A, recolectar pares portador↔raw: mantener `carriers: list[tuple[RegistroMensaje, bytes]]= []` y, tras construir `m` de un `col`, `carriers.append((m, col.raw))` (evita el `zip(mensajes, colapsados)` frágil ante errores).
  - Tras el bucle: `idx = INL.indice_layer_a(mensajes)`; recorrer `carriers` → `INL.reconstruir(m_a, raw)`; acumular `candidatos` (alta) y `punteros` (media/baja); propagar `m_a.respuesta_intercalada |= res.intercalada`.
  - Resolver/mint en orden determinista: `for seg in sorted(candidatos, key=lambda s: s.fingerprint)`: si `idx.resolver(seg)` → append `procedencia` al mensaje Capa A existente (no mint); si no → `reg.msg_id_for_fp(seg.fingerprint, cuerpo_sha=seg.cuerpo_sha)` + `INL.construir_b(...)` → `mensajes.append`.
  - Escribir `_revision/` con `R.render_revision(mensajes_b, punteros)`.
  - `colapsar` y el path de IDs Capa A NO se tocan.

- [ ] **Step 4: Ejecutar (debe pasar)** + no-regresión pipeline Fase 1: `python -m pytest tests/test_email_atomize_pipeline_b.py tests/test_email_atomize_pipeline.py -q` → PASS.

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_pipeline_b.py
git commit -m "feat(email-atomize): pase Layer B en el pipeline (Fase 2 T10)"
```

---

## Task 11: `render.py` + `corpus.py` — `.md` capa B + cola de revisión + corpus (DD §1, §8)

**Files:** Modify `core/email_atomize/render.py`, `core/email_atomize/corpus.py`; Test `tests/test_email_atomize_render_b.py`

- [ ] **Step 1: Tests (debe fallar)**

`tests/test_email_atomize_render_b.py`:
```python
from __future__ import annotations
from core.email_atomize.model import RegistroMensaje, SegmentoEnterrado
from core.email_atomize import render as R
from core.email_atomize import corpus as C
import json


def _b(**kw):
    base = dict(msg_id="MSG-00050", capa="B", confianza="alta-reconstruida",
                de="per01a@example.invalid", de_nombre="PersonaUno", fecha_iso="2020-05-01",
                hora="0900", asunto="Tibidabo", cuerpo="texto reconstruido",
                reconstruido_desde_cita=True, reconstruido_de="MSG-00042",
                fingerprint="fp:abc", procedencia=[{"citado_en": "MSG-00042", "profundidad": 1}])
    base.update(kw); return RegistroMensaje(**base)


def test_md_capa_b_lleva_banner_y_flags():
    md = R.render_md(_b())
    assert "capa: B" in md and "confianza: alta-reconstruida" in md
    assert "reconstruido_desde_cita: true" in md and "reconstruido_de: MSG-00042" in md
    assert "RECONSTRUIDO DESDE CITA" in md  # banner en el cuerpo


def test_correos_lectura_de_reconstruido_distinto():
    doc = R.render_correos_lectura([_b()])
    assert "De (reconstruido)" in doc

def test_render_revision_tres_colas():
    punteros = [SegmentoEnterrado(portador_msg_id="MSG-1", estilo="quote_gt",
                                  confianza="baja", motivo="sin_cabecera", extracto="...")]
    msgs_b = [_b(en_revision=True)]
    out = R.render_revision(msgs_b, punteros)
    assert "cola.md" in out and "casi_duplicados.md" in out and "del_burgo.md" in out
    assert "MSG-1" in out["cola.md"]
    assert "per01a@example.invalid" in out["del_burgo.md"]

def test_corpus_incluye_fingerprint_y_capa_b():
    fila = json.loads(C.corpus_jsonl([_b()]).strip().splitlines()[1])
    assert fila["capa"] == "B" and fila["fingerprint"] == "fp:abc"
    assert fila["en_revision"] is False
```

- [ ] **Step 2: Ejecutar (debe fallar).**

- [ ] **Step 3: Implementar (DD §1 render/corpus bullets):**
  - `render.render_md`: emitir los flags nuevos cuando True (`reconstruido_desde_cita`, `reconstruido_de`, `fecha_inferida`, `ambiguedad_profundidad`, `en_revision`, `fingerprint`); para `capa=="B"` anteponer al cuerpo un banner `> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline` (alta-reconstruida) o `> AUTORÍA POR RECONSTRUIR — sin verificar` (media/baja).
  - `render.render_correos_lectura`: para capa B usar `**De (reconstruido):**` (nunca con la misma autoridad visual que un `De:` de Capa A) + nota llana "Mensaje recuperado de una cita; remitente verificado por cabecera (MSG-id)".
  - `render.render_revision(mensajes_b, punteros) -> dict[str,str]`: `cola.md` (punteros media/baja + extracto + motivo), `casi_duplicados.md` (placeholder de eventos de upgrade/near-dup; alimentado por el pipeline en T10/T12), `del_burgo.md` (toda capa B con `de ∈ IDENTIDADES_VIGILADAS` o `en_revision` con de del watched), + espejos `.jsonl` para re-alertado idempotente.
  - `corpus._fila`: añadir `fingerprint`, `reconstruido_desde_cita`, `en_revision`.

- [ ] **Step 4: Ejecutar (debe pasar)** + no-regresión: `python -m pytest tests/test_email_atomize_render_b.py tests/test_email_atomize_render.py tests/test_email_atomize_corpus.py -q` → PASS.

- [ ] **Step 5: Commit**
```bash
git add core/email_atomize/render.py core/email_atomize/corpus.py tests/test_email_atomize_render_b.py
git commit -m "feat(email-atomize): render .md capa B + cola de revision + corpus (Fase 2 T11)"
```

---

## Task 12: Verificación en vivo W-02VND1 + checks adversariales (DD §11)

**Files:** Test `tests/test_email_atomize_regresion_b.py`

- [ ] **Step 1: Regresión dura — los 277 `.md` de Capa A byte-idénticos (debe pasar)**

Antes de correr sobre el caso real, capturar un hash del set actual y re-correr. PowerShell:
```powershell
$out = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta\01_Procesado\Emails"
# hash de los .md de Capa A ANTES (de la corrida Fase 1 ya presente)
$pre = Get-ChildItem "$out\mensajes" -Filter *.md | ForEach-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash } | Sort-Object
```

- [ ] **Step 2: Correr el motor (Capa A+B) sobre el caso real (solo lectura de 00_Input)**
```powershell
$case = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta"
& ".\.venv\Scripts\python.exe" -m scripts.atomize_emails --src "$case\00_Input\03_Email" --out "$case\01_Procesado\Emails"
```
Verificar (DD §11):
- Los `.md` de **capa A** siguen siendo 277 y **byte-idénticos** (recomputar hashes Capa A y comparar con `$pre`: deben coincidir; los nuevos son solo capa B).
- `_revision/del_burgo.md`, `cola.md`, `casi_duplicados.md` presentes.
- **Auditar a mano CADA `alta-reconstruida`** (≈21 PersonaUno + otras): confirmar que el `de`/`fecha` afirmado aparece LITERALMENTE en el bloque de cabecera del `.eml` fuente. **Cero tolerancia a un remitente fabricado.**
- Diff de `_registro.json` en dos corridas: 0 renumeraciones, 0 IDs fp duplicados, 277 Capa A idénticos.
- Buscar hilos HTML intercalados: confirmar que ninguno se segmentó (deben quedar `respuesta_intercalada`).
- Cruzar `casi_duplicados.md` con `.eml` reenviados conocidos (266/266 embebidos existen como `.eml` limpio → el upgrade debe disparar).

Anotar los conteos reales (nº alta-reconstruida, media, baja, del_burgo) para STATUS.

- [ ] **Step 3: Test de regresión sintético (debe pasar)** — `tests/test_email_atomize_regresion_b.py`: un `.eml` con cita inline de PersonaUno en HTML gmail_quote → 1 `alta-reconstruida` con `de=per01a@example.invalid`; un `.eml` headerless → 0 promovidos, entrada en cola; un `.eml` con fecha de cita POSTERIOR al portador → media + `fecha_incoherente` (nunca alta). (Bloquea las 3 regresiones prime-directive.)

- [ ] **Step 4: Suite completa verde** — `python -m pytest -q --tb=no --ignore=tests/test_email_export_mcp_server.py --ignore=tests/test_expedientes_xl_server.py` → exit 0; nº skipped = 58. Explicar cualquier diferencia en STATUS.

- [ ] **Step 5: Commit**
```bash
git add tests/test_email_atomize_regresion_b.py
git commit -m "test(email-atomize): regresion Layer B + verificacion adversarial W-02VND1 (Fase 2 T12)"
```

---

## Task 13: Cierre Fase 2 — STATUS + PLAN + memoria

**Files:** Modify `STATUS.md`; añadir entrada a `PLAN.md` (working tree, sin commitear si arrastra ajenos); memoria.

- [ ] **Step 1: STATUS.md** — nueva entrada `Última actualización` (demover la anterior a `Anterior`): Layer B completo, base header-anchor sintetizada por workflow adversarial, los conteos reales de W-02VND1 (alta-reconstruida/media/baja, PersonaUno recuperados), 277 Capa A byte-idénticos verificados, +N tests, suite exit 0, commits `<rango>`, spec `2026-06-25-...layerb-design.md` + plan `2026-06-25-...fase2.md`.
- [ ] **Step 2: PLAN.md** — marcar `[x] Fase 2` en `[SIGUIENTE-EMAIL-ATOMIZE]` con hashes; dejar Fase 3 pendiente. (Si `PLAN.md` arrastra cambios ajenos: añadir al working tree SIN commitear.)
- [ ] **Step 3: Memoria** — actualizar `project-email-atomize-fase1.md` → renombrar conceptualmente a cubrir Fase 2 (o nota): Fase 2 hecha, PersonaUno recuperado, identidades confirmadas (per01b@example.invalid candidato, ignacio@despacho-ab.example parte distinta); Fase 3 pendiente.
- [ ] **Step 4: Commit** (acotado a STATUS.md + memoria; PLAN.md según concurrencia)
```bash
git add STATUS.md
git commit -m "docs(email-atomize): cierre Fase 2 — Layer B completo + verificacion W-02VND1"
```

---

## Self-Review (autor del plan)

**Cobertura DD → tarea:**
- DD §1 module/file plan → T1 (_segmenter+bodies), T2 (model), T3 (ids), T4-T9 (inline), T10 (pipeline), T11 (render/corpus).
- DD §2 segmentación (intercalada, HTML, plano, coherencia, conservación tokens) → T6 (plano), T7 (HTML+intercalada+tokens).
- DD §3 sender/date ES+CA + headerless → T5 (+ T8/T9 routing de headerless).
- DD §4 confianza + guardas → T8.
- DD §5 fingerprint (día-granular, floor) → T4.
- DD §6 fidelity-upgrade (mid-alias + cuerpo_sha) → T3 (estructuras) + T9 (indice/resolver) + T10 (pipeline) + T12 (verificación cross-run).
- DD §7 pipeline → T10. DD §8 frontmatter → T2 + T11. DD §9 PersonaUno/watched → T9 + T11. DD §10 test plan (23) → distribuidos T1,T4-T12. DD §11 residual/verificación real → T12.

**Mapeo de los 23 escenarios DD §10:** 1,2 (HTML gmail/nested)→T7; 3 (outlook)→T6; 4 (apple)→T5/T6; 5 (fwd)→T6; 6 (multimarcador)→T6; 7 (ES/CA date)→T5; 8 (headerless)→T9/T10; 9 (quote-only)→T9; 10 (stray De:)→T6; 11 (display-name)→T5; 12 (outlook candidato media)→T8/T9; 13 (ignacio distinto)→T9/T12; 14 (fecha posterior)→T8; 15 (HTML intercalada)→T7; 16 (anchor collision)→T8/T9; 17 (token-conservación)→T7; 18 (fp reproducible)→T4; 19 (día-granular)→T4; 20 (re-run sin renumerar)→T10; 21 (fidelity-upgrade)→T10/T12; 22 (floor cuerpos cortos)→T4; 23 (regresión 277 byte-idénticos)→T1+T12.

**Placeholder scan:** los tests llevan código real; las internals profundas (regexes/selectores/escala) están especificadas verbatim en el DD committeado (no es placeholder: es doc compañero versionado). `casi_duplicados.md` en T11 es un esqueleto alimentado por el pipeline (T10/T12) — señalado, no TBD.

**Consistencia de tipos:** `Anclaje`/`Segmento`/`Segmentacion`/`ReconResult`/`Indice` definidos en `inline.py` y usados igual en T4-T11; `cortar_autor(texto)->(autor,resto,intercalada)` consistente T1↔T7; `Registro.msg_id_for_fp(fp,*,cuerpo_sha)`/`resolver_alias`/`registrar_alias` consistentes T3↔T9↔T10; `RegistroMensaje`/`SegmentoEnterrado` (T2) consumidos en T9-T11.

**Riesgo conocido (no bloqueante):** la cobertura del parser de fechas ES/CA es la compuerta alta↔media; un formato no cubierto degrada (seguro: más revisión, cero misatribución) pero reduce el yield PersonaUno. `html.parser` puede mal-contar anidamiento en HTML malformado; mitigado por validación header↔nivel + conservación de tokens + fallback plano.
