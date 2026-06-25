# Motor de atomización fina de WhatsApp — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir `core/whatsapp_atomize/`, un motor que convierte los chats de WhatsApp de un expediente en una fuente de verdad legible y citable (chat numerado), con reconstrucción de contenido enterrado, atribución de identidad y dedup de multimedia — hermano de `core/email_atomize/`.

**Architecture:** Paquete paralelo a `email_atomize` con pipeline propio (grano = chat numerado + atoms solo para enterrados). Reutiliza por import las piezas transversales ya endurecidas de `email_atomize` (`atribucion_en_cuerpo`, `AdjuntoUnico`/`AdjuntoRef`, `Anclaje`) sin reescribirlas. El parser puro `core/whatsapp_export.parse_chat` se reutiliza tal cual.

**Tech Stack:** Python 3.14, pytest, dataclasses, PyYAML, hashlib. Sin red ni dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-06-25-whatsapp-atomize-design.md`.

---

## Notas de entorno (LEER ANTES DE EMPEZAR)

- **Windows + PowerShell.** Los comandos de test van con `python -m pytest …` desde la raíz del repo `C:\Users\tnm33\Dev\FeesDefender`.
- **Encoding UTF-8 sin BOM** en todo IO de ficheros (regla del proyecto). Usar `encoding="utf-8"` en `read_text`/`write_text`.
- **Working tree compartido con sesiones concurrentes.** Cada commit es **acotado** a los ficheros propios de la task (`git add <ruta> <ruta>`), **nunca `git add -A`**. Hay un hook `post-commit` que auto-pushea `main`.
- **Cuidado con los here-strings en commits:** el Bash tool es POSIX sh (no PowerShell). Para mensajes multilínea usar `git commit -m "linea"` simple o `-F`. NO usar `@'…'@` en Bash.
- Suite de referencia: `python -m pytest -q --tb=no` debe quedar verde al final de cada task (salvo fallos preexistentes ajenos ya conocidos).

---

## Task 0: Exponer `atribucion_en_cuerpo` en `email_atomize` (pre-requisito de reuso)

Hoy es `_atribucion_en_cuerpo` (privada). `whatsapp_atomize` la necesita. Renombrar a pública sin tocar lógica.

**Files:**
- Modify: `core/email_atomize/inline.py` (def línea 265; uso interno línea ~956)
- Test: `tests/test_email_atomize_inline.py` (existente — añadir test de API pública)

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_email_atomize_inline.py`, añadir:

```python
def test_atribucion_en_cuerpo_es_api_publica():
    from core.email_atomize import inline
    # símbolo público disponible
    assert hasattr(inline, "atribucion_en_cuerpo")
    # comportamiento intacto: cabecera Apple pegada → recupera remitente
    texto = "El 14 may 2024, a las 10:00, Juan <juan@ej.com> escribió:\n\nHola"
    anc = inline.atribucion_en_cuerpo(texto)
    assert anc is not None and anc.de == "juan@ej.com"
    # sin <addr> → None
    assert inline.atribucion_en_cuerpo("solo prosa sin direccion") is None
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_email_atomize_inline.py::test_atribucion_en_cuerpo_es_api_publica -v`
Expected: FAIL (`module 'core.email_atomize.inline' has no attribute 'atribucion_en_cuerpo'`)

- [ ] **Step 3: Renombrar el símbolo (sin tocar lógica)**

En `core/email_atomize/inline.py`:
- Línea 265: `def _atribucion_en_cuerpo(texto: str)` → `def atribucion_en_cuerpo(texto: str)`.
- Línea ~956: `anc_body = _atribucion_en_cuerpo(seg.texto)` → `anc_body = atribucion_en_cuerpo(seg.texto)`.

Buscar cualquier otra referencia: `python -m pytest` aparte, primero grep:
Run: `grep -rn "_atribucion_en_cuerpo" core/ tests/`
Si aparece en algún test por el nombre privado, actualizarlo al nombre público.

- [ ] **Step 4: Correr el test nuevo + la suite de inline completa**

Run: `python -m pytest tests/test_email_atomize_inline.py -q`
Expected: PASS (todos; el renombrado no cambia comportamiento)

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/inline.py tests/test_email_atomize_inline.py
git commit -m "refactor(email-atomize): expone atribucion_en_cuerpo como API publica (reuso por whatsapp_atomize, sin cambio de logica)"
```

---

## Task 1: `model.py` — dataclasses del motor WhatsApp

**Files:**
- Create: `core/whatsapp_atomize/__init__.py`
- Create: `core/whatsapp_atomize/model.py`
- Test: `tests/test_whatsapp_atomize_model.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_model.py
from core.whatsapp_atomize.model import RegistroMensajeWA, AtomEnterrado, SegmentoEnterradoWA


def test_registro_mensaje_wa_defaults():
    m = RegistroMensajeWA()
    assert m.msg_id == ""
    assert m.fecha_iso == "0000-00-00"
    assert m.es_reenviado is False
    assert m.en_revision is False
    assert m.adjunto is None


def test_atom_enterrado_defaults_en_revision():
    a = AtomEnterrado(portador_msg_id="MSG-00001", de="x@y.com")
    assert a.en_revision is True
    assert a.confianza == "media"


def test_segmento_enterrado_wa():
    s = SegmentoEnterradoWA(portador_msg_id="MSG-00002", motivo="sin_cabecera")
    assert s.portador_msg_id == "MSG-00002"
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_model.py -v`
Expected: FAIL (`ModuleNotFoundError: core.whatsapp_atomize`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/__init__.py
"""Motor de atomización fina de WhatsApp a nivel de chat numerado.

Ver docs/superpowers/specs/2026-06-25-whatsapp-atomize-design.md.
Lee 00_Input/02_Whatsapp/<rol>/<chat>/_chat.txt (+ media) y produce, en
01_Procesado/Whatsapp/, un .md numerado por chat (citable), atoms .md de las
unidades enterradas promovidas, adjuntos deduplicados por sha256 con ficha,
corpus.jsonl y _registro.json (IDs congelados). Nunca toca 00_Input; idempotente.
"""
```

```python
# core/whatsapp_atomize/model.py
"""Dataclasses del motor de atomización de WhatsApp (solo estructura)."""
from __future__ import annotations

from dataclasses import dataclass, field

from core.email_atomize.model import AdjuntoRef  # reuso transversal


@dataclass
class RegistroMensajeWA:
    """Un mensaje del chat, ya atomizado y numerado."""

    msg_id: str = ""                 # "MSG-00042" (congelado por _registro.json)
    fingerprint: str = ""            # hash estable de timestamp+autor+texto
    chat_id: str = ""                # carpeta del chat de origen
    fecha_iso: str = "0000-00-00"
    hora: str = ""                   # "HHMM" local (WhatsApp no exporta tz)
    autor_export: str = ""           # lo que trae el chat (nombre de contacto o número)
    persona_id: str = ""             # resuelto vía identidades (o "")
    rol: str = ""                    # propietario | buscador | E&V | tercero | ""
    de_confianza: str = ""           # "" si autor crudo; "identidades" si resuelto
    texto: str = ""                  # verbatim del mensaje
    es_sistema: bool = False
    es_reenviado: bool = False
    adjunto: AdjuntoRef | None = None
    contiene_enterrado: bool = False
    en_revision: bool = False
    responde_a: str = ""             # MSG-id ligado por quote, o ""


@dataclass
class AtomEnterrado:
    """Unidad reconstruida (email/mensaje pegado) promovida a .md propio."""

    enterrado_id: str = ""           # "ENT-00001"
    portador_msg_id: str = ""        # de qué mensaje del chat salió
    de: str = ""
    de_nombre: str = ""
    fecha_iso: str = "0000-00-00"
    extracto: str = ""
    confianza: str = "media"
    en_revision: bool = True


@dataclass
class SegmentoEnterradoWA:
    """Fila de la cola de revisión: candidato detectado pero NO promovido."""

    portador_msg_id: str = ""
    motivo: str = ""                 # sin_cabecera | ambiguo | quote_no_ligado
    extracto: str = ""
    confianza: str = ""
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_model.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/__init__.py core/whatsapp_atomize/model.py tests/test_whatsapp_atomize_model.py
git commit -m "feat(whatsapp-atomize): modelo de datos (RegistroMensajeWA, AtomEnterrado, cola de revision)"
```

---

## Task 2: `ids.py` — fingerprint + IDs congelados + `_registro.json`

**Files:**
- Create: `core/whatsapp_atomize/ids.py`
- Test: `tests/test_whatsapp_atomize_ids.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_ids.py
from core.whatsapp_atomize.ids import fingerprint, load_registro_wa


def test_fingerprint_estable():
    a = fingerprint("2024-10-30T10:00", "Juan", "hola")
    b = fingerprint("2024-10-30T10:00", "Juan", "hola")
    assert a == b and len(a) == 64  # sha256 hex


def test_ids_congelados_idempotentes(tmp_path):
    reg = load_registro_wa(tmp_path)
    fp = fingerprint("2024-10-30T10:00", "Juan", "hola")
    id1 = reg.msg_id_for_fp(fp)
    id2 = reg.msg_id_for_fp(fp)            # misma fp → mismo id
    assert id1 == id2 == "MSG-00001"
    id_nuevo = reg.msg_id_for_fp(fingerprint("2024-10-30T10:01", "Ana", "ok"))
    assert id_nuevo == "MSG-00002"
    reg.save()
    # re-cargar: no renumera
    reg2 = load_registro_wa(tmp_path)
    assert reg2.msg_id_for_fp(fp) == "MSG-00001"


def test_att_id_por_sha(tmp_path):
    reg = load_registro_wa(tmp_path)
    assert reg.att_id_for("abc") == "ATT-00001"
    assert reg.att_id_for("abc") == "ATT-00001"
    assert reg.att_id_for("def") == "ATT-00002"
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_ids.py -v`
Expected: FAIL (`ModuleNotFoundError` / `cannot import name`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/ids.py
"""IDs congelados por contenido para WhatsApp + control persistente (_registro.json).

fingerprint = sha256(timestamp_iso|autor|texto). Re-ejecutar NUNCA renumera.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_REGISTRO_NAME = "_registro.json"
_README = (
    "Generado por core.whatsapp_atomize — NO editar a mano. Mapa congelado "
    "fingerprint→MSG-id, sha256→ATT-id, ENT-id. Re-ejecutar no renumera."
)


def fingerprint(timestamp_iso: str, autor: str, texto: str) -> str:
    base = f"{timestamp_iso}|{autor or ''}|{texto or ''}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


class RegistroWA:
    def __init__(self, base_dir: Path, data: dict) -> None:
        self.base_dir = base_dir
        self.mensajes_fp: dict[str, dict] = data.get("mensajes_fp", {})  # fp -> {"id"}
        self.adjuntos: dict[str, dict] = data.get("adjuntos", {})        # sha -> {"id"}
        self.enterrados: dict[str, dict] = data.get("enterrados", {})    # key -> {"id"}
        self.chats: list[str] = list(data.get("chats", []))              # {"chat": sha _chat.txt}
        self.chat_sha: dict[str, str] = data.get("chat_sha", {})
        cont = data.get("_contadores", {})
        self._next_msg = int(cont.get("msg", 0))
        self._next_att = int(cont.get("att", 0))
        self._next_ent = int(cont.get("ent", 0))

    def msg_id_for_fp(self, fp: str) -> str:
        entry = self.mensajes_fp.get(fp)
        if entry is not None:
            return entry["id"]
        self._next_msg += 1
        nuevo = f"MSG-{self._next_msg:05d}"
        self.mensajes_fp[fp] = {"id": nuevo}
        return nuevo

    def att_id_for(self, sha: str) -> str:
        entry = self.adjuntos.get(sha)
        if entry is not None:
            return entry["id"]
        self._next_att += 1
        nuevo = f"ATT-{self._next_att:05d}"
        self.adjuntos[sha] = {"id": nuevo}
        return nuevo

    def ent_id_for(self, key: str) -> str:
        entry = self.enterrados.get(key)
        if entry is not None:
            return entry["id"]
        self._next_ent += 1
        nuevo = f"ENT-{self._next_ent:05d}"
        self.enterrados[key] = {"id": nuevo}
        return nuevo

    def registrar_chat(self, chat_id: str, sha_chat_txt: str) -> None:
        if chat_id not in self.chats:
            self.chats.append(chat_id)
        self.chat_sha[chat_id] = sha_chat_txt

    def save(self) -> None:
        payload = {
            "_README": _README,
            "_no_editar": True,
            "version": 1,
            "_contadores": {"msg": self._next_msg, "att": self._next_att, "ent": self._next_ent},
            "mensajes_fp": self.mensajes_fp,
            "adjuntos": self.adjuntos,
            "enterrados": self.enterrados,
            "chats": sorted(self.chats),
            "chat_sha": self.chat_sha,
        }
        (self.base_dir / _REGISTRO_NAME).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_registro_wa(base_dir: Path | str) -> RegistroWA:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    p = base / _REGISTRO_NAME
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        data = {}
    return RegistroWA(base, data if isinstance(data, dict) else {})
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_ids.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/ids.py tests/test_whatsapp_atomize_ids.py
git commit -m "feat(whatsapp-atomize): IDs congelados por fingerprint + _registro.json idempotente"
```

---

## Task 3: `identidades.py` — mapa `autor_export → persona+rol` (yaml compartido)

**Files:**
- Create: `core/whatsapp_atomize/identidades.py`
- Test: `tests/test_whatsapp_atomize_identidades.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_identidades.py
import textwrap

from core.whatsapp_atomize.identidades import cargar_identidades_wa


def _escribir_yaml(case_dir):
    (case_dir / "identidades.yaml").write_text(textwrap.dedent("""
        personas:
          - id: prop
            nombre: Juan Propietario
            rol: propietario
            direcciones:
              - {email: juan@ej.com, estado: confirmada}
            identificadores:
              - {valor: "+34600111222", estado: confirmada}
              - {valor: "Juan", estado: candidata}
    """), encoding="utf-8")


def test_resuelve_por_identificador(tmp_path):
    _escribir_yaml(tmp_path)
    mapa = cargar_identidades_wa(tmp_path)
    assert mapa["+34600111222"] == ("prop", "Juan Propietario", "propietario")
    assert mapa["juan"] == ("prop", "Juan Propietario", "propietario")  # normaliza a lower


def test_sin_yaml_mapa_vacio(tmp_path):
    assert cargar_identidades_wa(tmp_path) == {}


def test_email_atomize_ignora_identificadores(tmp_path):
    """No-regresión: el cargador de email no peta con el campo nuevo."""
    _escribir_yaml(tmp_path)
    from core.email_atomize.identidades import cargar_identidades
    ids = cargar_identidades(tmp_path)
    assert ids.persona_de("juan@ej.com") == "prop"   # lee direcciones, ignora identificadores
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_identidades.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/identidades.py
"""Mapa autor_export → (persona_id, nombre, rol) desde el identidades.yaml del caso.

Lee el MISMO fichero que core.email_atomize.identidades pero el campo `identificadores`
(autor_export de WhatsApp: número o alias de contacto), no `direcciones` (emails).
"""
from __future__ import annotations

from pathlib import Path

import yaml

_ESTADOS = {"confirmada", "candidata"}


def cargar_identidades_wa(case_dir: Path | str) -> dict[str, tuple[str, str, str]]:
    """Devuelve {identificador_lower: (persona_id, nombre, rol)}. Sin fichero → {}."""
    path = Path(case_dir) / "identidades.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapa: dict[str, tuple[str, str, str]] = {}
    for raw in (data.get("personas") or []):
        if not isinstance(raw, dict):
            continue
        pid = str(raw.get("id") or "").strip()
        if not pid:
            continue
        nombre = str(raw.get("nombre") or "")
        rol = str(raw.get("rol") or "")
        for d in (raw.get("identificadores") or []):
            if not isinstance(d, dict):
                continue
            valor = str(d.get("valor") or "").strip().lower()
            estado = str(d.get("estado") or "").strip().lower()
            if valor and estado in _ESTADOS:
                mapa[valor] = (pid, nombre, rol)
    return mapa
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_identidades.py -v`
Expected: PASS (3 tests; el de no-regresión confirma que `email_atomize` ignora `identificadores`)

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/identidades.py tests/test_whatsapp_atomize_identidades.py
git commit -m "feat(whatsapp-atomize): mapa autor_export->persona+rol desde identidades.yaml compartido (campo identificadores)"
```

---

## Task 4: `reconstruccion.py` — reenviado, email pegado, quote

**Files:**
- Create: `core/whatsapp_atomize/reconstruccion.py`
- Test: `tests/test_whatsapp_atomize_reconstruccion.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_reconstruccion.py
from core.whatsapp_atomize.reconstruccion import es_reenviado, detectar_enterrado


def test_reenviado_marcador():
    assert es_reenviado("‎Reenviado") is True
    assert es_reenviado("Forwarded") is True
    assert es_reenviado("hola que tal") is False


def test_email_pegado_recupera_autor():
    texto = ("Mira lo que me mandaron:\n\n"
             "El 14 may 2024, a las 10:00, Juan <juan@ej.com> escribió:\n\nContenido")
    anc = detectar_enterrado(texto)
    assert anc is not None and anc.de == "juan@ej.com"


def test_reenviado_puro_sin_cabecera_no_inventa_autor():
    # un reenvío sin cabecera pegada: NO hay autor recuperable
    assert detectar_enterrado("‎Reenviado\nUn texto cualquiera sin direccion") is None
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_reconstruccion.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/reconstruccion.py
"""Reconstrucción de contenido enterrado en mensajes de WhatsApp.

Tres reglas (spec §6): reenviado puro (marcado, sin autor), email/mensaje pegado
(body-scan reutilizado de email_atomize → recupera autor original), quote de reply
(mínimo). Prime directive: nunca afirma un autor que no esté literal en el cuerpo.
"""
from __future__ import annotations

import re

from core.email_atomize.inline import Anclaje, atribucion_en_cuerpo

# Marcador de reenvío de WhatsApp (iOS/Android, ES/EN), tolerante al LRM (U+200E) inicial.
_RE_REENVIADO = re.compile(
    r"(?im)^\s*‎?(?:reenviado(?:\s+muchas\s+veces)?|forwarded(?:\s+many\s+times)?)\b")


def es_reenviado(texto: str) -> bool:
    """True si el texto abre con el marcador de reenvío de WhatsApp."""
    return bool(_RE_REENVIADO.match(texto or ""))


def detectar_enterrado(texto: str) -> Anclaje | None:
    """Email/mensaje pegado con cabecera → Anclaje (de, fecha). None si no hay autor
    literal recuperable. Reutiliza el body-scan endurecido de email_atomize."""
    return atribucion_en_cuerpo(texto or "")


def ligar_quote(extracto: str, textos_previos: dict[str, str]) -> str:
    """Si el extracto citado coincide EXACTO con el texto de un mensaje previo del mismo
    chat, devuelve su MSG-id; si no liga, "" (no inventa). v1 mínimo."""
    objetivo = (extracto or "").strip()
    if not objetivo:
        return ""
    for msg_id, texto in textos_previos.items():
        if (texto or "").strip() == objetivo:
            return msg_id
    return ""
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_reconstruccion.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/reconstruccion.py tests/test_whatsapp_atomize_reconstruccion.py
git commit -m "feat(whatsapp-atomize): reconstruccion de enterrados (reenviado/email pegado/quote) reusando body-scan"
```

---

## Task 5: `adjuntos.py` — ligar refs a bytes, sha256, dedup, ausentes

**Files:**
- Create: `core/whatsapp_atomize/adjuntos.py`
- Test: `tests/test_whatsapp_atomize_adjuntos.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_adjuntos.py
from core.whatsapp_atomize.adjuntos import construir_adjuntos
from core.whatsapp_atomize.ids import load_registro_wa


def test_dedup_por_sha_y_ausentes(tmp_path):
    reg = load_registro_wa(tmp_path)
    media = {"IMG-001.jpg": b"foto", "doc.pdf": b"pdf"}
    refs = ["IMG-001.jpg", "doc.pdf", "IMG-001.jpg", "falta.jpg", "<Media omitted>"]
    unicos, por_ref = construir_adjuntos(refs, media, reg)
    # 2 ficheros distintos presentes (IMG repetido = 1 ficha), faltantes no crean ficha
    att_ids = {a.att_id for a in unicos}
    assert len(att_ids) == 2
    assert por_ref["falta.jpg"]["ausente"] is True
    assert por_ref["<Media omitted>"]["ausente"] is True
    assert por_ref["IMG-001.jpg"]["ausente"] is False
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_adjuntos.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/adjuntos.py
"""Liga las referencias de adjunto del chat a los bytes presentes, dedup por sha256."""
from __future__ import annotations

import hashlib

from core.email_atomize.model import AdjuntoUnico

_MARCADORES_AUSENTE = {"<Media omitted>", "<archivo adjunto>"}


def construir_adjuntos(refs, media: dict[str, bytes], registro):
    """Devuelve (list[AdjuntoUnico] dedup por sha, dict ref→{att_id|None, ausente}).

    refs: lista de nombres referenciados en el chat (en orden de aparición).
    media: {nombre_fichero: bytes} presentes en el export.
    """
    por_sha: dict[str, AdjuntoUnico] = {}
    por_ref: dict[str, dict] = {}
    for ref in refs:
        if ref in por_ref:
            continue
        data = media.get(ref)
        if data is None or ref in _MARCADORES_AUSENTE:
            por_ref[ref] = {"att_id": None, "ausente": True}
            continue
        sha = hashlib.sha256(data).hexdigest()
        att_id = registro.att_id_for(sha)
        unico = por_sha.get(sha)
        if unico is None:
            unico = AdjuntoUnico(att_id=att_id, sha256=sha, nombre_original=ref,
                                 tipo="", data=data)
            por_sha[sha] = unico
        por_ref[ref] = {"att_id": att_id, "ausente": False}
    return list(por_sha.values()), por_ref
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_adjuntos.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/adjuntos.py tests/test_whatsapp_atomize_adjuntos.py
git commit -m "feat(whatsapp-atomize): adjuntos ligados a bytes + dedup por sha256 + ausentes"
```

---

## Task 6: `render.py` — chat numerado + atoms enterrados + índices

**Files:**
- Create: `core/whatsapp_atomize/render.py`
- Test: `tests/test_whatsapp_atomize_render.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_render.py
from core.whatsapp_atomize.model import RegistroMensajeWA, AtomEnterrado
from core.whatsapp_atomize.render import render_chat_lectura, render_enterrado


def test_chat_lectura_numerado_con_autor_resuelto():
    msgs = [
        RegistroMensajeWA(msg_id="MSG-00001", fecha_iso="2024-10-30", hora="1000",
                          autor_export="+34600", rol="propietario", texto="Hola"),
        RegistroMensajeWA(msg_id="MSG-00002", fecha_iso="2024-10-30", hora="1001",
                          autor_export="Ana", texto="Reenviado", es_reenviado=True),
    ]
    md = render_chat_lectura("chat-x", msgs, [], {})
    assert "MSG-00001" in md and "MSG-00002" in md
    assert "propietario" in md
    assert "reenviado" in md.lower()
    assert "NO editar" in md  # cabecera de generado


def test_enterrado_lleva_banner_por_verificar():
    a = AtomEnterrado(enterrado_id="ENT-00001", portador_msg_id="MSG-00002",
                      de="juan@ej.com", fecha_iso="2024-05-14", extracto="...")
    md = render_enterrado(a)
    assert "AUTORÍA POR VERIFICAR" in md
    assert "juan@ej.com" in md
    assert "MSG-00002" in md


def test_indice_adjuntos_lista_fichas():
    from core.email_atomize.model import AdjuntoUnico
    from core.whatsapp_atomize.render import render_indice_adjuntos
    adj = [AdjuntoUnico(att_id="ATT-00001", sha256="abc123", nombre_original="foto.jpg")]
    md = render_indice_adjuntos(adj)
    assert "ATT-00001" in md and "foto.jpg" in md and "abc123" in md
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_render.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/render.py
"""Render humano: chat numerado (.md), atoms enterrados, índices."""
from __future__ import annotations

from .model import AtomEnterrado, RegistroMensajeWA

_GEN = "<!-- Generado por core.whatsapp_atomize — NO editar a mano. -->\n\n"


def _autor_visible(m: RegistroMensajeWA) -> str:
    if m.rol and m.persona_id:
        return f"{m.autor_export} [{m.rol}]"
    if m.rol:
        return f"{m.autor_export} [{m.rol}]"
    return m.autor_export or "(sistema)"


def render_chat_lectura(chat_id, mensajes, enterrados, por_ref) -> str:
    lineas = [_GEN, f"# Chat: {chat_id}\n"]
    ent_por_portador: dict[str, list] = {}
    for a in enterrados:
        ent_por_portador.setdefault(a.portador_msg_id, []).append(a)
    for m in mensajes:
        marca = " · 🔁 reenviado" if m.es_reenviado else ""
        adj = ""
        if m.adjunto is not None:
            info = por_ref.get(m.adjunto.nombre, {})
            adj = f" · 📎 {m.adjunto.nombre}" + (" (ausente)" if info.get("ausente") else "")
        cab = f"**{m.msg_id}** · {m.fecha_iso} {m.hora} · {_autor_visible(m)}{marca}{adj}"
        lineas.append(cab)
        lineas.append(f"\n{m.texto.strip()}\n")
        for a in ent_por_portador.get(m.msg_id, []):
            lineas.append(f"> ↪ enterrado promovido: [{a.enterrado_id}](enterrados/{a.enterrado_id}.md)\n")
    return "\n".join(lineas) + "\n"


def render_enterrado(a: AtomEnterrado) -> str:
    banner = ("> AUTORÍA POR VERIFICAR — reconstruida de un mensaje pegado en el chat; "
              "WhatsApp no garantiza el origen.\n\n")
    fm = [
        f"# {a.enterrado_id}",
        f"- Portador: {a.portador_msg_id}",
        f"- De: {a.de_nombre or ''} <{a.de}>",
        f"- Fecha: {a.fecha_iso}",
        f"- Confianza: {a.confianza}",
    ]
    return _GEN + "\n".join(fm) + "\n\n" + banner + (a.extracto or "").strip() + "\n"


def render_indice(chats: dict[str, int]) -> str:
    """chats: {chat_id: n_mensajes}."""
    lineas = [_GEN, "# Índice de chats de WhatsApp\n"]
    for chat_id, n in sorted(chats.items()):
        lineas.append(f"- **{chat_id}** — {n} mensajes — [{chat_id}__LECTURA.md]({chat_id}__LECTURA.md)")
    return "\n".join(lineas) + "\n"


def render_indice_adjuntos(adjuntos) -> str:
    """Ficha de cada adjunto único (dedup por sha256)."""
    lineas = [_GEN, "# Índice de adjuntos\n"]
    for a in sorted(adjuntos, key=lambda x: x.att_id):
        lineas.append(f"- **{a.att_id}** · `{a.nombre_original}` · sha256 `{a.sha256}`")
    return "\n".join(lineas) + "\n"
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_render.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/render.py tests/test_whatsapp_atomize_render.py
git commit -m "feat(whatsapp-atomize): render del chat numerado + atoms enterrados con banner + indice"
```

---

## Task 7: `corpus.py` — `corpus.jsonl` (1 línea/mensaje)

**Files:**
- Create: `core/whatsapp_atomize/corpus.py`
- Test: `tests/test_whatsapp_atomize_corpus.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_corpus.py
import json

from core.whatsapp_atomize.corpus import corpus_jsonl_wa
from core.whatsapp_atomize.model import RegistroMensajeWA


def test_corpus_una_linea_por_mensaje_mas_meta():
    msgs = [
        RegistroMensajeWA(msg_id="MSG-00002", fecha_iso="2024-10-30", hora="1001", texto="b"),
        RegistroMensajeWA(msg_id="MSG-00001", fecha_iso="2024-10-30", hora="1000", texto="a"),
    ]
    out = corpus_jsonl_wa(msgs)
    lineas = out.strip().split("\n")
    meta = json.loads(lineas[0])
    assert meta["_tipo"] == "corpus_whatsapp"
    # ordenado por fecha/hora/msg_id → MSG-00001 primero
    primero = json.loads(lineas[1])
    assert primero["msg_id"] == "MSG-00001"
    assert len(lineas) == 3
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_corpus.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/corpus.py
"""Índice de máquina corpus.jsonl (1 línea/mensaje + meta inicial)."""
from __future__ import annotations

import json

from .model import RegistroMensajeWA

_META = {
    "_README": "Generado por core.whatsapp_atomize — NO editar. Saltar líneas con _README/_tipo.",
    "_tipo": "corpus_whatsapp",
    "_no_editar": True,
}


def _fila(m: RegistroMensajeWA) -> dict:
    return {
        "msg_id": m.msg_id,
        "fingerprint": m.fingerprint,
        "chat_id": m.chat_id,
        "fecha": m.fecha_iso,
        "hora": m.hora,
        "autor_export": m.autor_export,
        "persona_id": m.persona_id,
        "rol": m.rol,
        "texto": m.texto,
        "es_sistema": m.es_sistema,
        "es_reenviado": m.es_reenviado,
        "adjunto": (m.adjunto.__dict__ if m.adjunto is not None else None),
        "contiene_enterrado": m.contiene_enterrado,
        "en_revision": m.en_revision,
        "responde_a": m.responde_a,
    }


def corpus_jsonl_wa(mensajes: list[RegistroMensajeWA]) -> str:
    lineas = [json.dumps(_META, ensure_ascii=False)]
    for m in sorted(mensajes, key=lambda x: (x.fecha_iso, x.hora, x.msg_id)):
        lineas.append(json.dumps(_fila(m), ensure_ascii=False))
    return "\n".join(lineas) + "\n"
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_corpus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/corpus.py tests/test_whatsapp_atomize_corpus.py
git commit -m "feat(whatsapp-atomize): corpus.jsonl (1 linea por mensaje + meta)"
```

---

## Task 8: `pipeline.py` — `atomize_whatsapp_case` (orquestación)

**Files:**
- Create: `core/whatsapp_atomize/pipeline.py`
- Test: `tests/test_whatsapp_atomize_pipeline.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_pipeline.py
from pathlib import Path

from core.whatsapp_atomize.pipeline import atomize_whatsapp_case, descubrir_chats


CHAT = (
    "[30/10/2024, 10:00:00] Juan: Hola\n"
    "[30/10/2024, 10:01:00] Ana: El 14 may 2024, a las 9:00, Pe <pe@ej.com> escribió:\n"
    "Mira esto\n"
)


def _montar_caso(tmp_path) -> Path:
    chat_dir = tmp_path / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x"
    chat_dir.mkdir(parents=True)
    (chat_dir / "_chat.txt").write_text(CHAT, encoding="utf-8")
    return tmp_path


def test_descubrir_chats(tmp_path):
    caso = _montar_caso(tmp_path)
    chats = descubrir_chats(caso)
    assert len(chats) == 1 and chats[0].name == "chat-x"


def test_atomize_genera_salida_y_no_toca_input(tmp_path, monkeypatch):
    caso = _montar_caso(tmp_path)
    import core.whatsapp_atomize.pipeline as pl
    monkeypatch.setattr(pl, "caso_path", lambda cid: caso)
    input_antes = (caso / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x" / "_chat.txt").read_text(encoding="utf-8")

    resumen = atomize_whatsapp_case("CASO-X")

    out = caso / "01_Procesado" / "Whatsapp"
    assert (out / "chat-x__LECTURA.md").exists()
    assert (out / "corpus.jsonl").exists()
    assert (out / "_registro.json").exists()
    # email pegado promovido a enterrado
    assert resumen["enterrados"] >= 1
    assert any((out / "enterrados").glob("ENT-*.md"))
    # 00_Input intacto
    assert (caso / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x" / "_chat.txt").read_text(encoding="utf-8") == input_antes


def test_idempotente(tmp_path, monkeypatch):
    caso = _montar_caso(tmp_path)
    import core.whatsapp_atomize.pipeline as pl
    monkeypatch.setattr(pl, "caso_path", lambda cid: caso)
    r1 = atomize_whatsapp_case("CASO-X")
    reg1 = (caso / "01_Procesado" / "Whatsapp" / "_registro.json").read_text(encoding="utf-8")
    r2 = atomize_whatsapp_case("CASO-X")
    reg2 = (caso / "01_Procesado" / "Whatsapp" / "_registro.json").read_text(encoding="utf-8")
    assert reg1 == reg2  # IDs estables, 0 cambios
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_pipeline.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/pipeline.py
"""Orquestación: 00_Input/02_Whatsapp/**/_chat.txt → 01_Procesado/Whatsapp/.

Nunca toca 00_Input. Idempotente por fingerprint congelado en _registro.json.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from core.config import caso_path
from core.whatsapp_export import parse_chat

from . import corpus as corpus_mod
from . import render as render_mod
from .adjuntos import construir_adjuntos
from .ids import fingerprint, load_registro_wa
from .identidades import cargar_identidades_wa
from .model import AtomEnterrado, RegistroMensajeWA
from .reconstruccion import detectar_enterrado, es_reenviado

_WHATSAPP_IN = ("00_Input", "02_Whatsapp")
_OUT = ("01_Procesado", "Whatsapp")


def descubrir_chats(case_dir: Path) -> list[Path]:
    """Carpetas bajo 00_Input/02_Whatsapp que contienen un _chat.txt."""
    base = case_dir.joinpath(*_WHATSAPP_IN)
    if not base.exists():
        return []
    return sorted({p.parent for p in base.rglob("_chat.txt")}, key=lambda x: x.name)


def _hora_hhmm(ts) -> str:
    return f"{ts.hour:02d}{ts.minute:02d}" if ts is not None else ""


def _leer_media(chat_dir: Path) -> dict[str, bytes]:
    media: dict[str, bytes] = {}
    for p in chat_dir.iterdir():
        if p.is_file() and p.name not in ("_chat.txt",) and not p.name.startswith("_"):
            media[p.name] = p.read_bytes()
    return media


def atomize_whatsapp_case(case_id: str) -> dict:
    case_dir = caso_path(case_id)
    out_dir = case_dir.joinpath(*_OUT)
    ent_dir = out_dir / "enterrados"
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = load_registro_wa(out_dir)
    mapa_ids = cargar_identidades_wa(case_dir)

    todos_msgs: list[RegistroMensajeWA] = []
    todos_ent: list[AtomEnterrado] = []
    chats_meta: dict[str, int] = {}
    por_ref_global: dict[str, dict] = {}
    adjuntos_unicos: dict[str, object] = {}  # sha256 -> AdjuntoUnico (dedup global entre chats)

    for chat_dir in descubrir_chats(case_dir):
        chat_id = chat_dir.name
        texto = (chat_dir / "_chat.txt").read_text(encoding="utf-8")
        registro.registrar_chat(chat_id, hashlib.sha256(texto.encode("utf-8")).hexdigest())
        media = _leer_media(chat_dir)
        wmsgs = parse_chat(texto)
        refs = [m.adjunto_ref for m in wmsgs if m.adjunto_ref]
        unicos_chat, por_ref = construir_adjuntos(refs, media, registro)
        por_ref_global.update(por_ref)
        for u in unicos_chat:
            adjuntos_unicos.setdefault(u.sha256, u)  # primera aparición gana (dedup global)

        registros_chat: list[RegistroMensajeWA] = []
        for w in wmsgs:
            ts_iso = w.timestamp.isoformat() if w.timestamp else "0000-00-00"
            fp = fingerprint(ts_iso, w.autor or "", w.texto)
            ident = mapa_ids.get((w.autor or "").strip().lower())
            from core.email_atomize.model import AdjuntoRef
            r = RegistroMensajeWA(
                msg_id=registro.msg_id_for_fp(fp),
                fingerprint=fp,
                chat_id=chat_id,
                fecha_iso=(w.timestamp.date().isoformat() if w.timestamp else "0000-00-00"),
                hora=_hora_hhmm(w.timestamp),
                autor_export=w.autor or "",
                persona_id=(ident[0] if ident else ""),
                rol=(ident[2] if ident else ""),
                de_confianza=("identidades" if ident else ""),
                texto=w.texto,
                es_sistema=w.es_sistema,
                es_reenviado=es_reenviado(w.texto),
                adjunto=(AdjuntoRef(nombre=w.adjunto_ref) if w.adjunto_ref else None),
            )
            anc = detectar_enterrado(w.texto)
            if anc is not None and anc.de:
                r.contiene_enterrado = True
                r.en_revision = True
                key = f"{r.msg_id}|{anc.de}|{anc.fecha_iso}"
                todos_ent.append(AtomEnterrado(
                    enterrado_id=registro.ent_id_for(key),
                    portador_msg_id=r.msg_id, de=anc.de, de_nombre=anc.de_nombre,
                    fecha_iso=anc.fecha_iso, extracto=w.texto[:400]))
            registros_chat.append(r)

        chats_meta[chat_id] = len(registros_chat)
        todos_msgs.extend(registros_chat)

        ent_chat = [a for a in todos_ent if a.portador_msg_id in {r.msg_id for r in registros_chat}]
        (out_dir / f"{chat_id}__LECTURA.md").write_text(
            render_mod.render_chat_lectura(chat_id, registros_chat, ent_chat, por_ref),
            encoding="utf-8")

    if todos_ent:
        ent_dir.mkdir(parents=True, exist_ok=True)
        for a in todos_ent:
            (ent_dir / f"{a.enterrado_id}.md").write_text(render_mod.render_enterrado(a), encoding="utf-8")

    (out_dir / "INDICE.md").write_text(render_mod.render_indice(chats_meta), encoding="utf-8")
    (out_dir / "INDICE_ADJUNTOS.md").write_text(
        render_mod.render_indice_adjuntos(list(adjuntos_unicos.values())), encoding="utf-8")
    (out_dir / "corpus.jsonl").write_text(corpus_mod.corpus_jsonl_wa(todos_msgs), encoding="utf-8")
    registro.save()

    return {"chats": len(chats_meta), "mensajes": len(todos_msgs),
            "enterrados": len(todos_ent), "adjuntos": len(adjuntos_unicos)}
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_pipeline.py -v`
Expected: PASS (3 tests). Si `test_idempotente` falla por timestamps, revisar que el fingerprint no use objetos no deterministas (usa ISO string — debe ser estable).

- [ ] **Step 5: Commit**

```bash
git add core/whatsapp_atomize/pipeline.py tests/test_whatsapp_atomize_pipeline.py
git commit -m "feat(whatsapp-atomize): pipeline atomize_whatsapp_case (orquestacion idempotente, no toca 00_Input)"
```

---

## Task 9: CLI `scripts/atomize_whatsapp.py` + `proponer-identidades`

**Files:**
- Create: `scripts/atomize_whatsapp.py`
- Create: `core/whatsapp_atomize/propuesta_identidades.py`
- Test: `tests/test_whatsapp_atomize_propuesta.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_whatsapp_atomize_propuesta.py
from pathlib import Path

from core.whatsapp_atomize.propuesta_identidades import preparar_propuesta


CHAT = (
    "[30/10/2024, 10:00:00] +34600111222: Hola soy el propietario\n"
    "[30/10/2024, 10:01:00] Ana E&V: Buenas, soy de Engel\n"
)


def test_preparar_propuesta_reune_autores(tmp_path, monkeypatch):
    chat_dir = tmp_path / "00_Input" / "02_Whatsapp" / "02_Buscador" / "chat-x"
    chat_dir.mkdir(parents=True)
    (chat_dir / "_chat.txt").write_text(CHAT, encoding="utf-8")
    import core.whatsapp_atomize.propuesta_identidades as pr
    monkeypatch.setattr(pr, "caso_path", lambda cid: tmp_path)
    datos = preparar_propuesta("CASO-X")
    autores = {d["autor_export"] for d in datos}
    assert "+34600111222" in autores and "Ana E&V" in autores
    # incluye muestras de texto para que Claude-en-sesión proponga rol
    assert all("muestras" in d for d in datos)
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `python -m pytest tests/test_whatsapp_atomize_propuesta.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementación mínima**

```python
# core/whatsapp_atomize/propuesta_identidades.py
"""Reúne autores + muestras de un caso para que Claude-en-sesión proponga identidades.yaml.

Lectura pura (sin escribir, sin API). El gate y la persistencia los hace el letrado.
"""
from __future__ import annotations

from core.config import caso_path
from core.whatsapp_export import parse_chat

from .pipeline import descubrir_chats

_MAX_MUESTRAS = 5


def preparar_propuesta(case_id: str) -> list[dict]:
    case_dir = caso_path(case_id)
    muestras: dict[str, list[str]] = {}
    for chat_dir in descubrir_chats(case_dir):
        texto = (chat_dir / "_chat.txt").read_text(encoding="utf-8")
        for m in parse_chat(texto):
            if m.es_sistema or not m.autor:
                continue
            buf = muestras.setdefault(m.autor, [])
            if len(buf) < _MAX_MUESTRAS and m.texto.strip():
                buf.append(m.texto.strip()[:120])
    return [{"autor_export": a, "muestras": s} for a, s in sorted(muestras.items())]
```

```python
# scripts/atomize_whatsapp.py
"""CLI fino del motor de atomización de WhatsApp. Orquesta core.whatsapp_atomize."""
from __future__ import annotations

import argparse
import json

from core.whatsapp_atomize.pipeline import atomize_whatsapp_case
from core.whatsapp_atomize.propuesta_identidades import preparar_propuesta


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Atomización fina de WhatsApp")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("atomize", help="Atomiza los chats del caso")
    pa.add_argument("case_id")
    pp = sub.add_parser("proponer-identidades", help="Reúne autores+muestras (lectura pura)")
    pp.add_argument("case_id")
    args = parser.parse_args(argv)

    if args.cmd == "atomize":
        resumen = atomize_whatsapp_case(args.case_id)
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    elif args.cmd == "proponer-identidades":
        print(json.dumps(preparar_propuesta(args.case_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `python -m pytest tests/test_whatsapp_atomize_propuesta.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/atomize_whatsapp.py core/whatsapp_atomize/propuesta_identidades.py tests/test_whatsapp_atomize_propuesta.py
git commit -m "feat(whatsapp-atomize): CLI atomize + proponer-identidades (Claude-en-sesion, lectura pura)"
```

---

## Task 10: Verificación sobre datos reales + auditoría adversarial (NO código)

**Files:** ninguno (verificación manual; resultados a `STATUS.md`).

- [ ] **Step 1: Suite completa verde**

Run: `python -m pytest -q --tb=no`
Expected: verde (salvo fallos preexistentes ajenos conocidos). Anotar el conteo.

- [ ] **Step 2: Correr sobre un caso real con WhatsApp (W-02VND1 / BaRS1)**

Run: `python -m scripts.atomize_whatsapp atomize <CASE_ID_REAL>`
Inspeccionar `01_Procesado/Whatsapp/`: chat numerado legible, atoms `ENT-*.md` con banner, `corpus.jsonl`, `INDICE.md`.

- [ ] **Step 3: Auditoría adversarial de misatribución**

Revisar a mano cada `ENT-*.md`: ¿el `de` recuperado corresponde de verdad al autor de la cabecera pegada? ¿Algún reenvío puro generó un autor inventado (NO debe)? Anclar cada hallazgo a `MSG-id`. Documentar en `STATUS.md` igual que la verificación de email F4.

- [ ] **Step 4: Idempotencia en vivo**

Re-correr `atomize` y verificar 0 cambios en `_registro.json` (diff vacío) y Capa de verbatim intacta (`00_Input` sin tocar).

- [ ] **Step 5: Cierre — marcar #35 superado + actualizar memoria**

En `docs/MEJORAS_FUTURAS.md` #35: añadir `[SUPERADO por core/whatsapp_atomize, spec 2026-06-25]`. Commit acotado.

```bash
git add docs/MEJORAS_FUTURAS.md STATUS.md
git commit -m "docs: whatsapp-atomize verificado sobre datos reales; MEJORAS #35 superado"
```

---

## Self-review (cobertura del spec)

- §3 Arquitectura → Tasks 1-9 (un módulo por task). ✅
- §4 Modelo de datos → Task 1. ✅
- §5 Grano chat numerado → Task 6 (`render_chat_lectura`) + Task 8 (un `.md` por chat). ✅
- §6 Reconstrucción (3 reglas) → Task 4 + integración Task 8 (email pegado promueve; reenvío marca; quote vía `ligar_quote`). ✅
- §7 Identidad (yaml compartido + propuesta) → Task 3 + Task 9. ✅
- §8 Adjuntos dedup → Task 5. ✅
- §9 Salida → Tasks 6/7/8. ✅
- §10 Invariantes (no toca 00_Input, idempotencia, banner) → Tasks 8 (tests) + 6. ✅
- §13 Testing → tests por task + Task 10 (datos reales). ✅
- §14 Disparo CLI → Task 9. ✅
- §15 Reuso (exponer `atribucion_en_cuerpo`) → Task 0. ✅
- §17 #35 superado → Task 10 Step 5. ✅

**Nota de consistencia de nombres:** `RegistroWA.msg_id_for_fp`, `att_id_for`, `ent_id_for`, `registrar_chat`; `cargar_identidades_wa`; `es_reenviado`/`detectar_enterrado`/`ligar_quote`; `construir_adjuntos`; `render_chat_lectura`/`render_enterrado`/`render_indice`; `corpus_jsonl_wa`; `atomize_whatsapp_case`/`descubrir_chats`; `preparar_propuesta`. Usados consistentes entre tasks.

**Pendiente de afinar en implementación (no bloqueante):** Streamlit (botón espejo) queda fuera del plan v1 — añadir cuando el CLI esté verificado en vivo (spec §14, opcional).
