# Email Atomize — Fase 1 (IDs + Capa A + salidas) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el motor genérico `core/email_atomize/` que lee `00_Input/03_Email/*.eml` y produce, en `01_Procesado/Emails/`, un `.md` por mensaje atómico (frontmatter + cuerpo limpio), adjuntos deduplicados por sha256 con ficha, `corpus.jsonl`, `_registro.json` (IDs congelados), `CORREOS_LECTURA.md` e `INDICE_ADJUNTOS.md`, vía un CLI local.

**Architecture:** Paquete por responsabilidad. La Capa A es determinista: cada `.eml` aporta su mensaje principal + los `message/rfc822` embebidos (reutilizando `core.email_export.iter_nested_originals`/`message_id_of`/`parse_headers`); el dedup colapsa por Message-ID conservando la copia de mayor fidelidad y registrando todas las procedencias. La lógica vive en `core/`; `scripts/atomize_emails.py` solo orquesta. Nunca toca `00_Input`; idempotente por IDs congelados en `_registro.json`.

**Tech Stack:** Python 3.14, stdlib `email`/`hashlib`/`json`/`zoneinfo`, `pytest`. Reutiliza `core.email_export` y `core.intake_manifest.compute_sha256_bytes`. Windows + PowerShell, venv en `.venv`, UTF-8 sin BOM.

**Spec:** `docs/superpowers/specs/2026-06-24-email-atomize-design.md`.

**Convenciones de ejecución:**
- Todo comando shell: ejecutar desde `C:\Users\tnm33\Dev\FeesDefender`.
- Python: `.\.venv\Scripts\python.exe` (o `python -m pytest …`).
- Tests: `python -m pytest <ruta> -q` (suite completa: `python -m pytest -q --tb=no`).
- **Working tree compartido:** `git add` SOLO los ficheros propios de cada tarea (nunca `git add -A`). Todos los ficheros de Fase 1 son NUEVOS, así que no hay solape con sesiones concurrentes.
- Hay un `post-commit` hook que auto-pushea `main`; es esperado.

---

## Modelo de datos (referencia — se crea en la Tarea 1)

Definido en `core/email_atomize/model.py`:

```python
@dataclass
class AdjuntoRef:
    """Referencia a un adjunto desde un mensaje (va en el frontmatter del .md)."""
    att_id: str | None        # "ATT-00007" si es adjunto indexado
    msg_id_anidado: str | None  # MSG-id si la parte es un message/rfc822 (Fase 2 lo enlaza)
    nombre: str
    tipo: str                 # mime
    sha256: str

@dataclass
class AdjuntoUnico:
    """Un adjunto único (deduplicado por sha256) con su catálogo de apariciones."""
    att_id: str
    sha256: str
    nombre_original: str
    tipo: str
    data: bytes
    primera_aparicion: str    # fecha ISO del primer mensaje que lo trae
    mensajes: list[str]       # MSG-ids que lo referencian
    etiquetas: list[str]

@dataclass
class RegistroMensaje:
    """Un mensaje atómico final, listo para render/corpus."""
    msg_id: str               # "MSG-00001"
    rfc_message_id: str       # Message-ID RFC (puede ser "")
    in_reply_to: str
    hilo: str
    fecha_iso: str            # "AAAA-MM-DD"
    hora: str                 # "HHMM" Europe/Madrid ("" si no consta)
    fecha_tz: str             # ISO completo con tz, o ""
    de: str
    de_nombre: str
    para: list[str]
    cc: list[str]
    cco: list[str]
    asunto: str
    eml_origen: str
    profundidad: int
    ruta_anidacion: list[str]
    procedencia: list[dict]   # [{eml_origen, profundidad, ruta_anidacion}]
    capa: str                 # "A"
    confianza: str            # "alta"
    auth: dict                # {"dkim":..,"spf":..,"dmarc":..}
    sha256: str               # sha256 del .eml verbatim de este mensaje
    adjuntos: list[AdjuntoRef]
    idioma: str
    formato_original: str     # "plain" | "html" | "plain+html"
    emisor_dispositivo: str
    etiquetas: list[str]
    fuente: str               # "email"
    cuerpo: str               # texto limpio (solo lo que escribió el autor)
    # flags de cuerpo (no van al frontmatter salvo si True)
    cuerpo_recortado_cita: bool
    respuesta_intercalada: bool
    charset_recuperado: bool
    mojibake_marcado: bool
    raw: bytes                # bytes verbatim del mensaje (para sha y verbatim)
```

---

## Task 1: Esqueleto del paquete + modelo de datos + Registro de IDs congelados

**Files:**
- Create: `core/email_atomize/__init__.py`
- Create: `core/email_atomize/model.py`
- Create: `core/email_atomize/ids.py`
- Test: `tests/test_email_atomize_ids.py`

- [ ] **Step 1: Crear el paquete y el modelo**

`core/email_atomize/__init__.py`:
```python
"""Motor de atomización de correo a nivel de mensaje (ver docs/superpowers/specs/2026-06-24-email-atomize-design.md)."""
```

`core/email_atomize/model.py`: pegar las cuatro dataclasses del bloque "Modelo de datos" de arriba, con cabecera:
```python
"""Dataclasses del motor de atomización (sin lógica; solo estructura compartida)."""
from __future__ import annotations
from dataclasses import dataclass, field
# ... (las 3 dataclasses: AdjuntoRef, AdjuntoUnico, RegistroMensaje)
```
Usar `field(default_factory=list)`/`""`/`False` para los campos con default; los campos sin default van primero. Para `RegistroMensaje`, dar default a TODOS los flags y listas para construirlo incrementalmente.

- [ ] **Step 2: Escribir el test de Registro (debe fallar)**

`tests/test_email_atomize_ids.py`:
```python
from __future__ import annotations
import json
from core.email_atomize import ids


def test_msg_id_congela_por_message_id(tmp_path):
    reg = ids.load_registro(tmp_path)
    a = reg.msg_id_for("<m1@x>", sha="sha_a")
    b = reg.msg_id_for("<m2@x>", sha="sha_b")
    assert a == "MSG-00001"
    assert b == "MSG-00002"
    # mismo Message-ID -> mismo id (congelado), aunque cambie el sha (upgrade fidelidad)
    assert reg.msg_id_for("<m1@x>", sha="sha_a_v2") == "MSG-00001"


def test_att_id_congela_por_sha(tmp_path):
    reg = ids.load_registro(tmp_path)
    assert reg.att_id_for("shaPDF") == "ATT-00001"
    assert reg.att_id_for("shaJPG") == "ATT-00002"
    assert reg.att_id_for("shaPDF") == "ATT-00001"  # mismo contenido -> mismo id


def test_registro_persiste_y_no_renumera(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for("<m1@x>", sha="sha_a")
    reg.att_id_for("shaPDF")
    reg.marcar_procesado("2024-01-01_uno.eml")
    reg.save()

    reg2 = ids.load_registro(tmp_path)
    # tras recargar, un nuevo mensaje toma el SIGUIENTE libre, no renumera
    assert reg2.msg_id_for("<m2@x>", sha="sha_b") == "MSG-00002"
    assert reg2.att_id_for("shaJPG") == "ATT-00002"
    assert "2024-01-01_uno.eml" in reg2.procesados
    # el JSON tiene cabecera no-editar
    data = json.loads((tmp_path / "_registro.json").read_text(encoding="utf-8"))
    assert data["_no_editar"] is True
    assert "_README" in data
```

- [ ] **Step 3: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_ids.py -q`
Expected: FAIL (`ModuleNotFoundError: core.email_atomize.ids` o `AttributeError: load_registro`).

- [ ] **Step 4: Implementar `ids.py`**

`core/email_atomize/ids.py`:
```python
"""Asignación de IDs neutros congelados por contenido + control persistente.

``_registro.json``: mapa congelado Message-ID→MSG-id y sha256→ATT-id, más la lista de
``.eml`` procesados. Re-ejecutar NUNCA renumera: las claves existentes mandan; lo nuevo
toma el siguiente número libre.
"""
from __future__ import annotations

import json
from pathlib import Path

_REGISTRO_NAME = "_registro.json"
_README = (
    "Generado por core.email_atomize — NO editar a mano. Mapa congelado de identidad "
    "(Message-ID→MSG-id, sha256→ATT-id) + .eml procesados. Re-ejecutar no renumera."
)


def _norm_mid(message_id: str) -> str:
    return (message_id or "").strip().strip("<>").strip()


class Registro:
    def __init__(self, base_dir: Path, data: dict) -> None:
        self.base_dir = base_dir
        self.mensajes: dict[str, dict] = data.get("mensajes", {})   # mid -> {"id","sha256"}
        self.adjuntos: dict[str, dict] = data.get("adjuntos", {})   # sha -> {"id"}
        self.procesados: list[str] = list(data.get("eml_procesados", []))
        cont = data.get("_contadores", {})
        self._next_msg = int(cont.get("msg", 0))
        self._next_att = int(cont.get("att", 0))

    def msg_id_for(self, message_id: str, *, sha: str) -> str:
        key = _norm_mid(message_id)
        entry = self.mensajes.get(key)
        if entry is not None:
            entry["sha256"] = sha  # upgrade de fidelidad: id estable, sha al día
            return entry["id"]
        self._next_msg += 1
        nuevo = f"MSG-{self._next_msg:05d}"
        self.mensajes[key] = {"id": nuevo, "sha256": sha}
        return nuevo

    def att_id_for(self, sha: str) -> str:
        entry = self.adjuntos.get(sha)
        if entry is not None:
            return entry["id"]
        self._next_att += 1
        nuevo = f"ATT-{self._next_att:05d}"
        self.adjuntos[sha] = {"id": nuevo}
        return nuevo

    def marcar_procesado(self, eml_name: str) -> None:
        if eml_name not in self.procesados:
            self.procesados.append(eml_name)

    def save(self) -> None:
        payload = {
            "_README": _README,
            "_no_editar": True,
            "version": 1,
            "_contadores": {"msg": self._next_msg, "att": self._next_att},
            "mensajes": self.mensajes,
            "adjuntos": self.adjuntos,
            "eml_procesados": sorted(self.procesados),
        }
        (self.base_dir / _REGISTRO_NAME).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_registro(base_dir: Path | str) -> Registro:
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
    return Registro(base, data if isinstance(data, dict) else {})
```

- [ ] **Step 5: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_ids.py -q`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add core/email_atomize/__init__.py core/email_atomize/model.py core/email_atomize/ids.py tests/test_email_atomize_ids.py
git commit -m "feat(email-atomize): paquete + modelo + Registro de IDs congelados (Fase 1 T1)"
```

---

## Task 2: Parsing rico de cabeceras (`headers.py`)

**Files:**
- Create: `core/email_atomize/headers.py`
- Test: `tests/test_email_atomize_headers.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_email_atomize_headers.py`:
```python
from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import headers as H


def _raw(**hdrs) -> bytes:
    m = EmailMessage()
    for k, v in hdrs.items():
        m[k.replace("_", "-")] = v
    m.set_content("hola")
    return m.as_bytes()


def test_parse_direcciones_y_listas():
    raw = _raw(
        Message_ID="<a@x>", Subject="Asunto", Date="Thu, 12 Jun 2026 10:30:00 +0200",
        From="PersonaUno <per01c@example.invalid>", To="uno@x, Dos <dos@x>", Cc="tres@x",
        In_Reply_To="<prev@x>", References="<root@x> <prev@x>",
    )
    c = H.parse_cabeceras(raw)
    assert c.rfc_message_id == "a@x"
    assert c.de == "per01c@example.invalid"
    assert c.de_nombre == "PersonaUno"
    assert c.para == ["uno@x", "dos@x"]
    assert c.cc == ["tres@x"]
    assert c.asunto == "Asunto"
    assert c.in_reply_to == "prev@x"
    assert c.fecha_iso == "2026-06-12"
    assert c.hora == "1030"            # Europe/Madrid
    assert c.hilo == "root@x"          # raíz de References


def test_hilo_fallback_a_propio_message_id():
    raw = _raw(Message_ID="<solo@x>", Subject="X", Date="Thu, 12 Jun 2026 10:00:00 +0200",
               From="a@x", To="b@x")
    c = H.parse_cabeceras(raw)
    assert c.hilo == "solo@x"


def test_auth_y_dispositivo():
    raw = _raw(
        Message_ID="<a@x>", Subject="X", Date="Thu, 12 Jun 2026 10:00:00 +0200",
        From="a@x", To="b@x", X_Mailer="iPhone Mail (21G93)",
        Authentication_Results="mx.google.com; dkim=pass; spf=pass; dmarc=pass",
    )
    c = H.parse_cabeceras(raw)
    assert c.auth["dkim"] == "pass"
    assert c.auth["spf"] == "pass"
    assert c.auth["dmarc"] == "pass"
    assert "iPhone" in c.emisor_dispositivo
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_headers.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar `headers.py`**

`core/email_atomize/headers.py`:
```python
"""Parsing rico de cabeceras RFC822 para la atomización.

Extiende lo que ofrece ``email_export.parse_headers`` (date/subject/from/to/message-id):
direcciones con nombre, listas (to/cc), enhebrado (in-reply-to/references→hilo), resultados
de autenticación (dkim/spf/dmarc) y dispositivo emisor (X-Mailer/User-Agent).
"""
from __future__ import annotations

import email
import re
from dataclasses import dataclass, field
from email import policy
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

_TZ = ZoneInfo("Europe/Madrid")
_SIN_FECHA = "0000-00-00"


def _norm_mid(v: str) -> str:
    return (v or "").strip().strip("<>").strip()


@dataclass
class Cabeceras:
    rfc_message_id: str = ""
    in_reply_to: str = ""
    hilo: str = ""
    asunto: str = ""
    de: str = ""
    de_nombre: str = ""
    para: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    fecha_iso: str = _SIN_FECHA
    hora: str = ""
    fecha_tz: str = ""
    auth: dict = field(default_factory=dict)
    emisor_dispositivo: str = ""


def _addrs(msg, campo: str) -> list[str]:
    vals = msg.get_all(campo, [])
    return [a.lower() for _n, a in getaddresses(vals) if a]


def _fecha(msg) -> tuple[str, str, str]:
    raw = msg.get("date")
    if not raw:
        return _SIN_FECHA, "", ""
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return _SIN_FECHA, "", ""
    if dt is None:
        return _SIN_FECHA, "", ""
    if dt.tzinfo is not None:
        local = dt.astimezone(_TZ)
    else:
        local = dt
    return local.strftime("%Y-%m-%d"), local.strftime("%H%M"), local.isoformat()


def _refs_root(msg) -> str:
    refs = msg.get("references")
    if refs:
        ids = re.findall(r"<([^>]+)>", refs)
        if ids:
            return ids[0].strip()
    irt = _norm_mid(msg.get("in-reply-to") or "")
    if irt:
        return irt
    return _norm_mid(msg.get("message-id") or "")


def _auth(msg) -> dict:
    out: dict[str, str] = {}
    val = " ".join(msg.get_all("authentication-results", []))
    for k in ("dkim", "spf", "dmarc"):
        m = re.search(rf"\b{k}\s*=\s*([a-zA-Z]+)", val)
        if m:
            out[k] = m.group(1).lower()
    return out


def _dispositivo(msg) -> str:
    for h in ("x-mailer", "user-agent"):
        v = msg.get(h)
        if v:
            return str(v).strip()
    return ""


def parse_cabeceras(raw: bytes) -> Cabeceras:
    msg = email.message_from_bytes(raw, policy=policy.default)
    de_nombre, de = parseaddr(msg.get("from") or "")
    fecha_iso, hora, fecha_tz = _fecha(msg)
    return Cabeceras(
        rfc_message_id=_norm_mid(msg.get("message-id") or ""),
        in_reply_to=_norm_mid(msg.get("in-reply-to") or ""),
        hilo=_refs_root(msg),
        asunto=str(msg.get("subject") or "").strip(),
        de=(de or "").lower(),
        de_nombre=(de_nombre or "").strip(),
        para=_addrs(msg, "to"),
        cc=_addrs(msg, "cc"),
        fecha_iso=fecha_iso,
        hora=hora,
        fecha_tz=fecha_tz,
        auth=_auth(msg),
        emisor_dispositivo=_dispositivo(msg),
    )
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_headers.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/headers.py tests/test_email_atomize_headers.py
git commit -m "feat(email-atomize): parsing rico de cabeceras (Fase 1 T2)"
```

---

## Task 3: Capa A — extracción de avistamientos (`extract.py`)

**Files:**
- Create: `core/email_atomize/extract.py`
- Test: `tests/test_email_atomize_extract.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_email_atomize_extract.py`:
```python
from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import extract as E


def _msg(mid: str, subject: str, body: str = "cuerpo") -> EmailMessage:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "a@x"
    m["To"] = "b@x"
    m.set_content(body)
    return m


def test_avistamiento_top_level(tmp_path):
    raw = _msg("<a@x>", "Solo").as_bytes()
    p = tmp_path / "2026-06-12_solo.eml"
    p.write_bytes(raw)
    avist = list(E.iter_avistamientos(tmp_path))
    assert len(avist) == 1
    a = avist[0]
    assert a.message_id == "a@x"
    assert a.profundidad == 0
    assert a.eml_origen == "2026-06-12_solo.eml"
    assert a.raw == raw


def test_desciende_en_rfc822_embebido(tmp_path):
    hijo = _msg("<hijo@x>", "Hijo")
    padre = _msg("<padre@x>", "Padre")
    padre.add_attachment(
        hijo.as_bytes(), maintype="message", subtype="rfc822", filename="adj.eml"
    )
    p = tmp_path / "2026-06-12_padre.eml"
    p.write_bytes(padre.as_bytes())
    avist = list(E.iter_avistamientos(tmp_path))
    mids = sorted(a.message_id for a in avist)
    assert mids == ["hijo@x", "padre@x"]
    hijo_av = next(a for a in avist if a.message_id == "hijo@x")
    assert hijo_av.profundidad == 1
    assert hijo_av.ruta_anidacion == ["padre@x"]
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_extract.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `extract.py`**

`core/email_atomize/extract.py`:
```python
"""Capa A (determinista): avistamientos de mensaje atómico desde los .eml.

Cada ``.eml`` aporta su mensaje principal (profundidad 0) + cada ``message/rfc822``
embebido, recursivo a hojas (profundidad 1, 2, …). Reutiliza el rebanado byte-fiel de
``core.email_export``. El dedup por Message-ID y la fusión de procedencias los hace
``dedup.py``; aquí solo se enumeran los avistamientos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from core.email_export import iter_nested_originals, message_id_of


@dataclass
class Avistamiento:
    raw: bytes
    message_id: str
    eml_origen: str
    profundidad: int
    ruta_anidacion: list[str] = field(default_factory=list)


def _ruta_de(raw: bytes, eml_origen: str) -> dict[str, list[str]]:
    """Mapa Message-ID hijo → cadena de ancestros (Message-IDs), por avistamiento.

    Reconstruye la cadena desde el rebanado recursivo: cada anidado conoce su padre
    inmediato (``iter_nested_originals`` devuelve ``(bytes, parent_mid)``); encadenamos
    por padre hasta la raíz.
    """
    padre_de: dict[str, str] = {}
    for child, parent_mid in iter_nested_originals(raw):
        cmid = message_id_of(child)
        if cmid:
            padre_de[cmid] = parent_mid
    cadenas: dict[str, list[str]] = {}
    for cmid in padre_de:
        cadena: list[str] = []
        cur = padre_de.get(cmid, "")
        visto: set[str] = set()
        while cur and cur not in visto:
            cadena.append(cur)
            visto.add(cur)
            cur = padre_de.get(cur, "")
        cadenas[cmid] = list(reversed(cadena))
    return cadenas


def iter_avistamientos(emails_dir: Path | str) -> Iterator[Avistamiento]:
    base = Path(emails_dir)
    for eml in sorted(base.glob("*.eml")):
        try:
            raw = eml.read_bytes()
        except OSError:
            continue
        yield Avistamiento(
            raw=raw, message_id=message_id_of(raw), eml_origen=eml.name, profundidad=0
        )
        if b"message/rfc822" not in raw:
            continue
        cadenas = _ruta_de(raw, eml.name)
        for child, _parent_mid in iter_nested_originals(raw):
            cmid = message_id_of(child)
            ruta = cadenas.get(cmid, [])
            yield Avistamiento(
                raw=child, message_id=cmid, eml_origen=eml.name,
                profundidad=max(1, len(ruta)), ruta_anidacion=ruta,
            )
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_extract.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/extract.py tests/test_email_atomize_extract.py
git commit -m "feat(email-atomize): Capa A — avistamientos de mensaje atómico (Fase 1 T3)"
```

---

## Task 4: Dedup por Message-ID + fusión de procedencias (`dedup.py`)

**Files:**
- Create: `core/email_atomize/dedup.py`
- Test: `tests/test_email_atomize_dedup.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_email_atomize_dedup.py`:
```python
from __future__ import annotations
from core.email_atomize.extract import Avistamiento
from core.email_atomize import dedup as D


def test_colapsa_por_message_id_y_fusiona_procedencia():
    a1 = Avistamiento(raw=b"corto", message_id="m@x", eml_origen="suelto.eml", profundidad=0)
    a2 = Avistamiento(raw=b"copia mas larga byte-fiel", message_id="m@x",
                      eml_origen="padre.eml", profundidad=1, ruta_anidacion=["p@x"])
    msgs = D.colapsar([a1, a2])
    assert len(msgs) == 1
    m = msgs[0]
    assert m.message_id == "m@x"
    # mayor fidelidad = más bytes
    assert m.raw == b"copia mas larga byte-fiel"
    # el avistamiento canónico fija profundidad/ruta; procedencia recoge AMBOS
    assert len(m.procedencia) == 2
    orig = {p["eml_origen"] for p in m.procedencia}
    assert orig == {"suelto.eml", "padre.eml"}


def test_sin_message_id_no_se_colapsa_en_fase1():
    a1 = Avistamiento(raw=b"uno", message_id="", eml_origen="x.eml", profundidad=0)
    a2 = Avistamiento(raw=b"dos", message_id="", eml_origen="y.eml", profundidad=0)
    msgs = D.colapsar([a1, a2])
    assert len(msgs) == 2  # cada uno keyed por sha256 de su raw
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_dedup.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `dedup.py`**

`core/email_atomize/dedup.py`:
```python
"""Dedup de avistamientos a mensajes atómicos.

Fase 1: clave de identidad = Message-ID; sin Message-ID, sha256 del raw (cada copia
distinta cuenta como un mensaje — la huella inline llega en Fase 2). Conserva la copia de
MAYOR FIDELIDAD (más bytes = MIME más completo) y registra TODAS las procedencias.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.intake_manifest import compute_sha256_bytes
from .extract import Avistamiento


@dataclass
class MensajeColapsado:
    message_id: str
    raw: bytes
    eml_origen: str
    profundidad: int
    ruta_anidacion: list[str]
    procedencia: list[dict] = field(default_factory=list)


def _clave(av: Avistamiento) -> str:
    return av.message_id or "sha256:" + compute_sha256_bytes(av.raw)


def colapsar(avistamientos: list[Avistamiento]) -> list[MensajeColapsado]:
    por_clave: dict[str, MensajeColapsado] = {}
    for av in avistamientos:
        clave = _clave(av)
        proc = {
            "eml_origen": av.eml_origen,
            "profundidad": av.profundidad,
            "ruta_anidacion": list(av.ruta_anidacion),
        }
        existente = por_clave.get(clave)
        if existente is None:
            por_clave[clave] = MensajeColapsado(
                message_id=av.message_id, raw=av.raw, eml_origen=av.eml_origen,
                profundidad=av.profundidad, ruta_anidacion=list(av.ruta_anidacion),
                procedencia=[proc],
            )
            continue
        existente.procedencia.append(proc)
        # mayor fidelidad = más bytes; si gana, también adopta su origen/profundidad/ruta
        if len(av.raw) > len(existente.raw):
            existente.raw = av.raw
            existente.eml_origen = av.eml_origen
            existente.profundidad = av.profundidad
            existente.ruta_anidacion = list(av.ruta_anidacion)
    return list(por_clave.values())
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_dedup.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/dedup.py tests/test_email_atomize_dedup.py
git commit -m "feat(email-atomize): dedup por Message-ID + fusión de procedencia (Fase 1 T4)"
```

---

## Task 5: Cuerpo limpio (`bodies.py`)

**Files:**
- Create: `core/email_atomize/bodies.py`
- Test: `tests/test_email_atomize_bodies.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_email_atomize_bodies.py`:
```python
from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import bodies as B


def _con_partes(plain: str | None, html: str | None) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = "<a@x>"
    m["Subject"] = "X"
    m["From"] = "a@x"
    m["To"] = "b@x"
    if plain is not None:
        m.set_content(plain)
    if html is not None:
        if plain is None:
            m.set_content("x")  # base
        m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_prefiere_text_plain():
    raw = _con_partes("texto plano del autor", "<p>HTML que ignoramos</p>")
    cuerpo = B.extraer_cuerpo(raw)
    assert "texto plano del autor" in cuerpo.texto
    assert "HTML" not in cuerpo.texto
    assert cuerpo.formato_original == "plain"


def test_html_solo_se_convierte_a_texto():
    raw = _con_partes(None, "<p>Hola <b>mundo</b></p>")
    cuerpo = B.extraer_cuerpo(raw)
    assert "Hola" in cuerpo.texto and "mundo" in cuerpo.texto
    assert "<p>" not in cuerpo.texto


def test_recorta_cola_citada_top_posting():
    plano = (
        "Mi respuesta breve.\n\n"
        "El 11 jun 2026, a las 9:00, Jaime <j@x> escribió:\n"
        "> texto citado largo\n> mas cita\n"
    )
    raw = _con_partes(plano, None)
    cuerpo = B.extraer_cuerpo(raw)
    assert "Mi respuesta breve." in cuerpo.texto
    assert "texto citado largo" not in cuerpo.texto
    assert cuerpo.cuerpo_recortado_cita is True


def test_respuesta_intercalada_no_se_recorta():
    plano = (
        "> pregunta uno\n"
        "respuesta uno del autor\n"
        "> pregunta dos\n"
        "respuesta dos del autor\n"
    )
    raw = _con_partes(plano, None)
    cuerpo = B.extraer_cuerpo(raw)
    assert "respuesta uno del autor" in cuerpo.texto
    assert "pregunta dos" in cuerpo.texto  # se conserva íntegro
    assert cuerpo.respuesta_intercalada is True
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_bodies.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `bodies.py`**

`core/email_atomize/bodies.py`:
```python
"""Extracción y limpieza del cuerpo: solo lo que escribió el autor.

Reglas (spec §6): preferir text/plain; HTML→texto si el plano está vacío/muñón; recuperación
de charset condicional (solo si el sniff de mojibake dispara y el round-trip reduce marcas);
recortar la cola citada (top/bottom-posting) salvo respuesta intercalada (se conserva íntegra).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

from core.email_export import iter_body_text

_RE_TAG = re.compile(r"<[^>]+>")
_RE_BR = re.compile(r"(?i)<br\s*/?>")
_RE_BLOCK = re.compile(r"(?i)</(p|div|tr|li|h[1-6])>")
_RE_MULTINL = re.compile(r"\n{3,}")
_RE_MOJI = re.compile(r"Ã[\x80-\xbf\xa1-\xff]|Â[\xa0-\xbf]|�")

# Encabezados de cita típicos (es/en) que marcan el inicio de la cola citada.
_RE_CITA_HDR = re.compile(
    r"^\s*(el .+escribi[oó]:|on .+wrote:|-{2,}\s*(mensaje original|original message"
    r"|forwarded message|reenviado).*|de\s*:.*\n.*(enviado|asunto)\s*:)",
    re.IGNORECASE | re.MULTILINE,
)
_STUB_MAX = 3   # un text/plain de <=3 chars no-espacio se considera muñón


@dataclass
class Cuerpo:
    texto: str
    formato_original: str            # "plain" | "html" | "plain+html"
    charset_recuperado: bool = False
    mojibake_marcado: bool = False
    cuerpo_recortado_cita: bool = False
    respuesta_intercalada: bool = False


def _html_a_texto(html: str) -> str:
    t = _RE_BR.sub("\n", html)
    t = _RE_BLOCK.sub("\n", t)
    t = _RE_TAG.sub("", t)
    t = unescape(t)
    return _RE_MULTINL.sub("\n\n", t).strip()


def _recupera_charset(texto: str) -> tuple[str, bool]:
    """Si hay mojibake y el round-trip cp1252→utf-8 REDUCE marcas, aplicarlo."""
    antes = len(_RE_MOJI.findall(texto))
    if antes == 0:
        return texto, False
    try:
        fix = texto.encode("cp1252", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto, False
    if len(_RE_MOJI.findall(fix)) < antes:
        return fix, True
    return texto, False


def _es_linea_citada(linea: str) -> bool:
    return linea.lstrip().startswith(">")


def _limpia_cita(texto: str) -> tuple[str, bool, bool]:
    """Devuelve (texto_limpio, recortado, intercalada).

    Intercalada: hay líneas citadas (>) seguidas de líneas de autor MÁS ABAJO → conservar
    íntegro. Top/bottom-posting: la cola citada es un bloque final contiguo → recortarla
    (incluyendo su encabezado "El … escribió:").
    """
    lineas = texto.splitlines()
    quoted_idx = [i for i, l in enumerate(lineas) if _es_linea_citada(l)]
    if not quoted_idx:
        # buscar encabezado de cita sin '>' (reenvíos): recortar desde ahí
        m = _RE_CITA_HDR.search(texto)
        if m and m.start() > 0:
            return texto[: m.start()].rstrip(), True, False
        return texto.strip(), False, False
    # ¿hay líneas de autor (no vacías, no citadas) DESPUÉS de la primera cita?
    primera = quoted_idx[0]
    autor_despues = any(
        l.strip() and not _es_linea_citada(l) and not _RE_CITA_HDR.match(l)
        for l in lineas[primera + 1:]
    )
    if autor_despues:
        return texto.strip(), False, True  # intercalada: no recortar
    # cola citada al final: recortar desde el encabezado de cita si existe, si no desde la
    # primera línea citada.
    corte = primera
    m = _RE_CITA_HDR.search(texto)
    if m:
        # recortar por el encabezado si cae antes del primer '>'
        pre = texto[: m.start()].count("\n")
        corte = min(corte, pre)
    limpio = "\n".join(lineas[:corte]).rstrip()
    return limpio, True, False


def extraer_cuerpo(raw: bytes) -> Cuerpo:
    plano = ""
    html = ""
    for texto, es_html in iter_body_text(raw):
        if es_html and not html:
            html = texto
        elif not es_html and not plano:
            plano = texto
    if len(plano.replace(" ", "").strip()) > _STUB_MAX:
        base, formato = plano, "plain"
    elif html:
        base, formato = _html_a_texto(html), "html"
    else:
        base, formato = plano, "plain"
    base, recuperado = _recupera_charset(base)
    moji = len(_RE_MOJI.findall(base)) > 0
    limpio, recortado, intercalada = _limpia_cita(base)
    return Cuerpo(
        texto=limpio, formato_original=formato, charset_recuperado=recuperado,
        mojibake_marcado=moji, cuerpo_recortado_cita=recortado,
        respuesta_intercalada=intercalada,
    )
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_bodies.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/bodies.py tests/test_email_atomize_bodies.py
git commit -m "feat(email-atomize): cuerpo limpio (plain-pref, charset, cita) (Fase 1 T5)"
```

---

## Task 6: Adjuntos — dedup sha256 + filtro decorativo (`attachments.py`)

**Files:**
- Create: `core/email_atomize/attachments.py`
- Test: `tests/test_email_atomize_attachments.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_email_atomize_attachments.py`:
```python
from __future__ import annotations
from core.email_atomize import attachments as A


def test_clasifica_decorativo_por_recurrencia_y_tamano():
    logo = b"\x89PNG" + b"x" * 100          # pequeño
    cont鞋 = None
    # hash del logo aparece en 6 mensajes -> decorativo
    apariciones = {A._sha(logo): 6}
    assert A.es_decorativo(logo, "image/png", apariciones) is True
    # una captura grande, única -> no decorativo
    captura = b"\xff\xd8\xff" + b"y" * 80000
    assert A.es_decorativo(captura, "image/jpeg", {A._sha(captura): 1}) is False
    # un PDF (no imagen) nunca es decorativo
    pdf = b"%PDF" + b"z" * 50
    assert A.es_decorativo(pdf, "application/pdf", {A._sha(pdf): 99}) is False


def test_contar_apariciones_y_recolectar(tmp_path):
    from email.message import EmailMessage

    def _con_adj(mid, fn, data, mime="application/pdf"):
        m = EmailMessage()
        m["Message-ID"] = mid
        m["Subject"] = "x"; m["From"] = "a@x"; m["To"] = "b@x"
        m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
        m.set_content("c")
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
        return m.as_bytes()

    raws = [
        _con_adj("<a@x>", "contrato.pdf", b"%PDF mismo"),
        _con_adj("<b@x>", "renombrado.pdf", b"%PDF mismo"),   # mismo contenido, otro nombre
        _con_adj("<c@x>", "otro.pdf", b"%PDF distinto"),
    ]
    cont = A.contar_apariciones(raws)
    assert cont[A._sha(b"%PDF mismo")] == 2
    assert cont[A._sha(b"%PDF distinto")] == 1
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_attachments.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `attachments.py`**

`core/email_atomize/attachments.py`:
```python
"""Adjuntos: dedup por sha256 (contenido, no nombre) + filtro decorativo + ficha.

Decorativo (no se indexa, queda embebido en el .eml): imagen recurrente (mismo sha en
muchos mensajes = logo/firma) Y pequeña. Único + sustancial → adjunto con ficha.
"""
from __future__ import annotations

from collections import Counter

from core.email_export import split_eml
from core.intake_manifest import compute_sha256_bytes

_FIRMA_MAX_BYTES = 50 * 1024
_RECURRENCIA_MIN = 5


def _sha(data: bytes) -> str:
    return compute_sha256_bytes(data)


def contar_apariciones(raws: list[bytes]) -> Counter:
    """Cuenta, sobre todos los mensajes, cuántas veces aparece cada sha256 de adjunto."""
    cont: Counter = Counter()
    for raw in raws:
        _eml, adjuntos = split_eml(raw)
        for _fn, _mime, data in adjuntos:
            cont[_sha(data)] += 1
    return cont


def es_decorativo(data: bytes, mime: str, apariciones: dict) -> bool:
    if not mime.startswith("image/"):
        return False
    recurrente = apariciones.get(_sha(data), 0) >= _RECURRENCIA_MIN
    pequena = len(data) < _FIRMA_MAX_BYTES
    return recurrente and pequena
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_attachments.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/attachments.py tests/test_email_atomize_attachments.py
git commit -m "feat(email-atomize): adjuntos dedup sha256 + filtro decorativo (Fase 1 T6)"
```

---

## Task 7: Render del `.md` por mensaje (`render.py` parte 1)

**Files:**
- Create: `core/email_atomize/render.py`
- Test: `tests/test_email_atomize_render.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_email_atomize_render.py`:
```python
from __future__ import annotations
from core.email_atomize.model import RegistroMensaje, AdjuntoRef
from core.email_atomize import render as R


def _msg(**kw) -> RegistroMensaje:
    base = dict(
        msg_id="MSG-00001", rfc_message_id="a@x", in_reply_to="", hilo="a@x",
        fecha_iso="2026-06-12", hora="1030", fecha_tz="2026-06-12T10:30:00+02:00",
        de="per01c@example.invalid", de_nombre="PersonaUno", para=["b@x"], cc=[], cco=[],
        asunto="Oferta [inmueble]", eml_origen="2026-06-12_oferta.eml", profundidad=0,
        ruta_anidacion=[], procedencia=[{"eml_origen": "2026-06-12_oferta.eml",
                                         "profundidad": 0, "ruta_anidacion": []}],
        capa="A", confianza="alta", auth={"dkim": "pass"}, sha256="deadbeef",
        adjuntos=[], idioma="es", formato_original="plain", emisor_dispositivo="",
        etiquetas=[], fuente="email", cuerpo="Texto del autor.",
        cuerpo_recortado_cita=False, respuesta_intercalada=False,
        charset_recuperado=False, mojibake_marcado=False, raw=b"raw",
    )
    base.update(kw)
    return RegistroMensaje(**base)


def test_nombre_fichero_mensaje():
    assert R.nombre_md(_msg()) == "2026-06-12_1030_oferta_inmueble_MSG-00001.md"


def test_render_md_tiene_frontmatter_y_cuerpo():
    md = R.render_md(_msg(adjuntos=[AdjuntoRef(att_id="ATT-00003", msg_id_anidado=None,
                                               nombre="contrato.pdf", tipo="application/pdf",
                                               sha256="cafe")]))
    assert md.startswith("# GENERADO")
    assert "msg_id: MSG-00001" in md
    assert "rfc_message_id: a@x" in md
    assert "fuente: email" in md
    assert "ATT-00003" in md
    assert "Texto del autor." in md


def test_render_marca_flags_solo_si_true():
    md_sin = R.render_md(_msg())
    assert "respuesta_intercalada" not in md_sin
    md_con = R.render_md(_msg(respuesta_intercalada=True, mojibake_marcado=True))
    assert "respuesta_intercalada: true" in md_con
    assert "mojibake: true" in md_con
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_render.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `render.py` (parte 1: `.md` por mensaje)**

`core/email_atomize/render.py`:
```python
"""Render de las salidas humanas: .md por mensaje, CORREOS_LECTURA.md, INDICE_ADJUNTOS.md."""
from __future__ import annotations

import json

from core.email_export import _slug_descripcion
from .model import RegistroMensaje

_GEN_MD = "# GENERADO por core.email_atomize — NO editar (fuente de verdad regenerable).\n"


def nombre_md(m: RegistroMensaje) -> str:
    slug = _slug_descripcion(m.asunto)
    hora = m.hora or "0000"
    return f"{m.fecha_iso}_{hora}_{slug}_{m.msg_id}.md"


def _yaml_lista(nombre: str, valores: list[str]) -> str:
    if not valores:
        return f"{nombre}: []"
    items = "\n".join(f"  - {json.dumps(v, ensure_ascii=False)}" for v in valores)
    return f"{nombre}:\n{items}"


def render_md(m: RegistroMensaje) -> str:
    fm: list[str] = ["---"]
    fm.append(f"msg_id: {m.msg_id}")
    fm.append(f"rfc_message_id: {m.rfc_message_id}")
    fm.append(f"in_reply_to: {m.in_reply_to}")
    fm.append(f"hilo: {m.hilo}")
    fm.append(f"fecha: {m.fecha_tz or m.fecha_iso}")
    fm.append(f"de: {m.de}")
    fm.append(f"de_nombre: {json.dumps(m.de_nombre, ensure_ascii=False)}")
    fm.append(_yaml_lista("para", m.para))
    fm.append(_yaml_lista("cc", m.cc))
    if m.cco:
        fm.append(_yaml_lista("cco", m.cco))
    fm.append(f"asunto: {json.dumps(m.asunto, ensure_ascii=False)}")
    fm.append(f"eml_origen: {json.dumps(m.eml_origen, ensure_ascii=False)}")
    fm.append(f"profundidad: {m.profundidad}")
    fm.append(_yaml_lista("ruta_anidacion", m.ruta_anidacion))
    fm.append(f"procedencia: {json.dumps(m.procedencia, ensure_ascii=False)}")
    fm.append(f"capa: {m.capa}")
    fm.append(f"confianza: {m.confianza}")
    fm.append(f"auth: {json.dumps(m.auth, ensure_ascii=False)}")
    fm.append(f"sha256: {m.sha256}")
    fm.append(f"adjuntos: {json.dumps([a.__dict__ for a in m.adjuntos], ensure_ascii=False)}")
    fm.append(f"idioma: {m.idioma}")
    fm.append(f"formato_original: {m.formato_original}")
    if m.emisor_dispositivo:
        fm.append(f"emisor_dispositivo: {json.dumps(m.emisor_dispositivo, ensure_ascii=False)}")
    fm.append(_yaml_lista("etiquetas", m.etiquetas))
    fm.append(f"fuente: {m.fuente}")
    if m.cuerpo_recortado_cita:
        fm.append("cuerpo_recortado_cita: true")
    if m.respuesta_intercalada:
        fm.append("respuesta_intercalada: true")
    if m.charset_recuperado:
        fm.append("charset_recuperado: true")
    if m.mojibake_marcado:
        fm.append("mojibake: true")
    fm.append("---")
    return _GEN_MD + "\n".join(fm) + "\n\n" + m.cuerpo.strip() + "\n"
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_render.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/render.py tests/test_email_atomize_render.py
git commit -m "feat(email-atomize): render del .md por mensaje (Fase 1 T7)"
```

---

## Task 8: Vistas humanas + corpus (`render.py` parte 2 + `corpus.py`)

**Files:**
- Modify: `core/email_atomize/render.py` (añadir `render_correos_lectura`, `render_indice_adjuntos`)
- Create: `core/email_atomize/corpus.py`
- Test: `tests/test_email_atomize_corpus.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_email_atomize_corpus.py`:
```python
from __future__ import annotations
import json
from core.email_atomize.model import RegistroMensaje, AdjuntoUnico
from core.email_atomize import corpus as C
from core.email_atomize import render as R


def _msg(msg_id="MSG-00001", fecha="2026-06-12", asunto="Asunto", **kw):
    base = dict(
        msg_id=msg_id, rfc_message_id="a@x", in_reply_to="", hilo="a@x",
        fecha_iso=fecha, hora="1030", fecha_tz=f"{fecha}T10:30:00+02:00",
        de="per01c@example.invalid", de_nombre="Jaime", para=["b@x"], cc=[], cco=[],
        asunto=asunto, eml_origen="x.eml", profundidad=0, ruta_anidacion=[],
        procedencia=[], capa="A", confianza="alta", auth={}, sha256="deadbeef",
        adjuntos=[], idioma="es", formato_original="plain", emisor_dispositivo="",
        etiquetas=[], fuente="email", cuerpo="cuerpo", cuerpo_recortado_cita=False,
        respuesta_intercalada=False, charset_recuperado=False, mojibake_marcado=False,
        raw=b"raw",
    )
    base.update(kw)
    return RegistroMensaje(**base)


def test_corpus_jsonl_primera_linea_meta_y_una_por_mensaje():
    out = C.corpus_jsonl([_msg(), _msg(msg_id="MSG-00002")])
    lineas = out.strip().splitlines()
    meta = json.loads(lineas[0])
    assert meta["_no_editar"] is True and meta["_tipo"] == "corpus"
    fila = json.loads(lineas[1])
    assert fila["msg_id"] == "MSG-00001"
    assert fila["fuente"] == "email"
    assert "cuerpo" not in fila            # corpus es índice, no vuelca el cuerpo
    assert len(lineas) == 3                # meta + 2 mensajes


def test_correos_lectura_cronologico_con_anclas():
    doc = R.render_correos_lectura([
        _msg(msg_id="MSG-00002", fecha="2026-06-13", asunto="Segundo"),
        _msg(msg_id="MSG-00001", fecha="2026-06-12", asunto="Primero"),
    ])
    assert doc.index("Primero") < doc.index("Segundo")   # orden cronológico
    assert "Ref. MSG-00001" in doc
    assert "GENERADO" in doc.splitlines()[0] or "generado" in doc.lower()


def test_indice_adjuntos_lista_unicos():
    att = AdjuntoUnico(att_id="ATT-00001", sha256="cafe", nombre_original="contrato.pdf",
                       tipo="application/pdf", data=b"%PDF", primera_aparicion="2026-06-12",
                       mensajes=["MSG-00001", "MSG-00002"], etiquetas=[])
    doc = R.render_indice_adjuntos([att])
    assert "ATT-00001" in doc and "contrato.pdf" in doc
    assert "MSG-00001" in doc
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_corpus.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `corpus.py` y ampliar `render.py`**

`core/email_atomize/corpus.py`:
```python
"""Índice de máquina ``corpus.jsonl`` (1 línea/mensaje + registro meta inicial)."""
from __future__ import annotations

import json

from .model import RegistroMensaje

_META = {
    "_README": "Generado por core.email_atomize — NO editar. Índice de máquina; "
               "el lector debe saltar líneas con _README/_tipo.",
    "_tipo": "corpus",
    "_no_editar": True,
}


def _fila(m: RegistroMensaje) -> dict:
    return {
        "msg_id": m.msg_id,
        "rfc_message_id": m.rfc_message_id,
        "in_reply_to": m.in_reply_to,
        "hilo": m.hilo,
        "fecha": m.fecha_tz or m.fecha_iso,
        "de": m.de,
        "de_nombre": m.de_nombre,
        "para": m.para,
        "cc": m.cc,
        "asunto": m.asunto,
        "capa": m.capa,
        "confianza": m.confianza,
        "profundidad": m.profundidad,
        "ruta_anidacion": m.ruta_anidacion,
        "procedencia": m.procedencia,
        "adjuntos": [a.__dict__ for a in m.adjuntos],
        "idioma": m.idioma,
        "sha256": m.sha256,
        "fuente": m.fuente,
        "ruta_md": "mensajes/" + _nombre_md_lazy(m),
    }


def _nombre_md_lazy(m: RegistroMensaje) -> str:
    from .render import nombre_md
    return nombre_md(m)


def corpus_jsonl(mensajes: list[RegistroMensaje]) -> str:
    lineas = [json.dumps(_META, ensure_ascii=False)]
    for m in sorted(mensajes, key=lambda x: (x.fecha_iso, x.hora, x.msg_id)):
        lineas.append(json.dumps(_fila(m), ensure_ascii=False))
    return "\n".join(lineas) + "\n"
```

Añadir a `core/email_atomize/render.py` (al final):
```python
_GEN_VIEW = "<!-- GENERADO por core.email_atomize — NO editar a mano. -->\n"


def _ancla(msg_id: str) -> str:
    return msg_id.lower()


def render_correos_lectura(mensajes: list[RegistroMensaje]) -> str:
    ms = sorted(mensajes, key=lambda x: (x.fecha_iso, x.hora, x.msg_id))
    out = [_GEN_VIEW, f"# Correos — lectura ({len(ms)} mensajes)\n", "## Índice\n"]
    for m in ms:
        out.append(f"- [{m.fecha_iso} {m.hora} — {m.asunto or '(sin asunto)'}]"
                   f"(#{_ancla(m.msg_id)})")
    out.append("\n---\n")
    for m in ms:
        out.append(f'<a id="{_ancla(m.msg_id)}"></a>')
        out.append(f"### {m.fecha_iso} · {m.hora} — {m.asunto or '(sin asunto)'}\n")
        out.append(f"**De:** {m.de_nombre or m.de} <{m.de}>  ")
        out.append(f"**Para:** {', '.join(m.para) or '—'}  ")
        if m.cc:
            out.append(f"**CC:** {', '.join(m.cc)}  ")
        if m.cco:
            out.append(f"**CCO:** {', '.join(m.cco)}  ")
        if m.adjuntos:
            nombres = ", ".join(a.nombre for a in m.adjuntos)
            out.append(f"**Adjuntos:** {nombres}  ")
        if m.emisor_dispositivo and "iphone" in m.emisor_dispositivo.lower():
            out.append("_Enviado desde iPhone_  ")
        out.append("")
        out.append(m.cuerpo.strip())
        out.append(f"\n<sub>Ref. {m.msg_id}</sub>\n")
        out.append("\n---\n")
    return "\n".join(out) + "\n"


def render_indice_adjuntos(adjuntos: list["AdjuntoUnico"]) -> str:  # noqa: F821
    out = [_GEN_VIEW, f"# Índice de adjuntos ({len(adjuntos)} únicos)\n",
           "| ATT | Nombre | Tipo | 1ª aparición | Mensajes |",
           "| --- | --- | --- | --- | --- |"]
    for a in sorted(adjuntos, key=lambda x: x.att_id):
        msgs = ", ".join(a.mensajes)
        out.append(f"| {a.att_id} | {a.nombre_original} | {a.tipo} | "
                   f"{a.primera_aparicion} | {msgs} |")
    return "\n".join(out) + "\n"
```

Añadir el import necesario al principio de `render.py`:
```python
from .model import RegistroMensaje, AdjuntoUnico  # AdjuntoUnico usado por render_indice_adjuntos
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_corpus.py tests/test_email_atomize_render.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/render.py core/email_atomize/corpus.py tests/test_email_atomize_corpus.py
git commit -m "feat(email-atomize): vistas humanas + corpus.jsonl (Fase 1 T8)"
```

---

## Task 9: Orquestación end-to-end (`pipeline.py`)

**Files:**
- Create: `core/email_atomize/pipeline.py`
- Test: `tests/test_email_atomize_pipeline.py`

- [ ] **Step 1: Escribir el test e2e (debe fallar)**

`tests/test_email_atomize_pipeline.py`:
```python
from __future__ import annotations
import json
from email.message import EmailMessage
from core.email_atomize import pipeline as P


def _msg(mid, subject, body="cuerpo", fecha="Thu, 12 Jun 2026 10:00:00 +0200",
         attachments=None):
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = "Jaime <per01c@example.invalid>"
    m["To"] = "b@x"
    m.set_content(body)
    for fn, mime, data in attachments or []:
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
    return m.as_bytes()


def test_e2e_atomiza_a_directorio(tmp_path):
    src = tmp_path / "03_Email"
    out = tmp_path / "Emails"
    src.mkdir()
    # mensaje con adjunto
    (src / "2026-06-12_a.eml").write_bytes(
        _msg("<a@x>", "Oferta", attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")])
    )
    # padre que embebe a <a@x> (duplicado por Message-ID) + su propio mensaje
    padre = EmailMessage()
    padre["Message-ID"] = "<padre@x>"; padre["Subject"] = "RV: Oferta"
    padre["Date"] = "Fri, 13 Jun 2026 09:00:00 +0200"; padre["From"] = "c@x"; padre["To"] = "d@x"
    padre.set_content("Te reenvío.")
    padre.add_attachment(_msg("<a@x>", "Oferta", attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")]),
                         maintype="message", subtype="rfc822", filename="a.eml")
    (src / "2026-06-13_padre.eml").write_bytes(padre.as_bytes())

    rep = P.atomize_dir(src, out)

    # 2 mensajes únicos: <a@x> (colapsado de suelto+embebido) y <padre@x>
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    # corpus tiene meta + 2 filas
    corpus = (out / "corpus.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(corpus) == 3
    # registro congelado presente
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg["_no_editar"] is True
    assert len(reg["mensajes"]) == 2
    # un adjunto único
    assert (out / "INDICE_ADJUNTOS.md").exists()
    assert (out / "CORREOS_LECTURA.md").exists()
    atts = list((out / "adjuntos").glob("*"))
    assert any(p.suffix == ".pdf" for p in atts)
    assert rep.mensajes == 2


def test_e2e_idempotente_no_renumera(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-12_a.eml").write_bytes(_msg("<a@x>", "Uno"))
    P.atomize_dir(src, out)
    reg1 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    # añadir un segundo .eml y re-correr
    (src / "2026-06-13_b.eml").write_bytes(_msg("<b@x>", "Dos"))
    P.atomize_dir(src, out)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    # <a@x> conserva su MSG-id original
    assert reg1["mensajes"]["a@x"]["id"] == reg2["mensajes"]["a@x"]["id"] == "MSG-00001"
    assert reg2["mensajes"]["b@x"]["id"] == "MSG-00002"
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_email_atomize_pipeline.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar `pipeline.py`**

`core/email_atomize/pipeline.py`:
```python
"""Orquestación de la Capa A end-to-end.

Lee ``03_Email`` → avistamientos → colapsa por Message-ID → construye RegistroMensaje
(cabeceras + cuerpo + adjuntos + IDs congelados) → escribe mensajes/, adjuntos/ (+fichas),
corpus.jsonl, _registro.json, CORREOS_LECTURA.md, INDICE_ADJUNTOS.md. Idempotente.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from core.email_export import split_eml
from core.intake_manifest import compute_sha256_bytes

from . import attachments as A
from . import bodies as B
from . import corpus as C
from . import extract as E
from . import dedup as D
from . import headers as H
from . import ids as IDS
from . import render as R
from .model import AdjuntoRef, AdjuntoUnico, RegistroMensaje


@dataclass
class AtomizeReport:
    mensajes: int = 0
    adjuntos_unicos: int = 0
    adjuntos_decorativos: int = 0
    errores: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        return (f"{self.mensajes} mensajes atómicos, {self.adjuntos_unicos} adjuntos únicos "
                f"({self.adjuntos_decorativos} decorativos filtrados), "
                f"{len(self.errores)} errores")


def _idioma(texto: str) -> str:
    """Heurística mínima es/ca/en por stopwords (suficiente para Fase 1)."""
    t = " " + texto.lower() + " "
    ca = sum(t.count(w) for w in (" el ", " que ", " amb ", " aquest ", " però "))
    en = sum(t.count(w) for w in (" the ", " and ", " you ", " with ", " regards "))
    es = sum(t.count(w) for w in (" el ", " que ", " con ", " usted ", " saludos "))
    return max((("ca", ca), ("en", en), ("es", es)), key=lambda x: x[1])[0]


def atomize_dir(src_dir: Path | str, out_dir: Path | str) -> AtomizeReport:
    src = Path(src_dir)
    out = Path(out_dir)
    (out / "mensajes").mkdir(parents=True, exist_ok=True)
    (out / "adjuntos").mkdir(parents=True, exist_ok=True)
    report = AtomizeReport()

    reg = IDS.load_registro(out)
    avistamientos = list(E.iter_avistamientos(src))
    colapsados = D.colapsar(avistamientos)

    # adjuntos: contar apariciones (para filtro decorativo) sobre los raws canónicos
    raws = [m.raw for m in colapsados]
    apariciones = A.contar_apariciones(raws)

    # primer pase: construir RegistroMensaje + recolectar adjuntos únicos
    unicos: dict[str, AdjuntoUnico] = {}      # sha -> AdjuntoUnico
    mensajes: list[RegistroMensaje] = []
    for col in colapsados:
        try:
            m = _construir_mensaje(col, reg, apariciones, unicos, report)
        except Exception as exc:  # noqa: BLE001 — un mensaje no aborta la corrida
            report.errores.append(f"{col.message_id or '(sin id)'}: {exc}")
            continue
        mensajes.append(m)
        reg.marcar_procesado(col.eml_origen)

    # escribir mensajes
    for m in mensajes:
        (out / "mensajes" / R.nombre_md(m)).write_text(R.render_md(m), encoding="utf-8")
    report.mensajes = len(mensajes)

    # escribir adjuntos únicos + fichas
    for att in unicos.values():
        _escribe_adjunto(out, att)
    report.adjuntos_unicos = len(unicos)

    # corpus + vistas + registro
    (out / "corpus.jsonl").write_text(C.corpus_jsonl(mensajes), encoding="utf-8")
    (out / "CORREOS_LECTURA.md").write_text(
        R.render_correos_lectura(mensajes), encoding="utf-8")
    (out / "INDICE_ADJUNTOS.md").write_text(
        R.render_indice_adjuntos(list(unicos.values())), encoding="utf-8")
    reg.save()
    return report


def _construir_mensaje(col, reg, apariciones, unicos, report) -> RegistroMensaje:
    sha = compute_sha256_bytes(col.raw)
    msg_id = reg.msg_id_for(col.message_id, sha=sha)
    cab = H.parse_cabeceras(col.raw)
    cuerpo = B.extraer_cuerpo(col.raw)

    _eml, adjuntos = split_eml(col.raw)
    refs: list[AdjuntoRef] = []
    for fn, mime, data in adjuntos:
        att_sha = compute_sha256_bytes(data)
        if A.es_decorativo(data, mime, apariciones):
            report.adjuntos_decorativos += 1
            continue
        att_id = reg.att_id_for(att_sha)
        refs.append(AdjuntoRef(att_id=att_id, msg_id_anidado=None, nombre=fn,
                               tipo=mime, sha256=att_sha))
        u = unicos.get(att_sha)
        if u is None:
            unicos[att_sha] = AdjuntoUnico(
                att_id=att_id, sha256=att_sha, nombre_original=fn, tipo=mime, data=data,
                primera_aparicion=cab.fecha_iso, mensajes=[msg_id], etiquetas=[])
        elif msg_id not in u.mensajes:
            u.mensajes.append(msg_id)

    return RegistroMensaje(
        msg_id=msg_id, rfc_message_id=cab.rfc_message_id, in_reply_to=cab.in_reply_to,
        hilo=cab.hilo, fecha_iso=cab.fecha_iso, hora=cab.hora, fecha_tz=cab.fecha_tz,
        de=cab.de, de_nombre=cab.de_nombre, para=cab.para, cc=cab.cc, cco=[],
        asunto=cab.asunto, eml_origen=col.eml_origen, profundidad=col.profundidad,
        ruta_anidacion=col.ruta_anidacion, procedencia=col.procedencia, capa="A",
        confianza="alta", auth=cab.auth, sha256=sha, adjuntos=refs,
        idioma=_idioma(cuerpo.texto), formato_original=cuerpo.formato_original,
        emisor_dispositivo=cab.emisor_dispositivo, etiquetas=[], fuente="email",
        cuerpo=cuerpo.texto, cuerpo_recortado_cita=cuerpo.cuerpo_recortado_cita,
        respuesta_intercalada=cuerpo.respuesta_intercalada,
        charset_recuperado=cuerpo.charset_recuperado, mojibake_marcado=cuerpo.mojibake_marcado,
        raw=col.raw,
    )


def _escribe_adjunto(out: Path, att: AdjuntoUnico) -> None:
    from core.email_export import _sanea_nombre_fichero
    stem_src = Path(att.nombre_original)
    ext = stem_src.suffix or ""
    slug = _sanea_nombre_fichero(stem_src.stem, fallback="adjunto")
    base = f"{att.primera_aparicion}_{slug}_{att.att_id}"
    (out / "adjuntos" / f"{base}{ext}").write_bytes(att.data)
    ficha_suffix = ".ficha.md" if ext.lower() == ".md" else ".md"
    ficha = (
        f"# GENERADO por core.email_atomize — NO editar.\n\n"
        f"- att_id: {att.att_id}\n- nombre_original: {att.nombre_original}\n"
        f"- tipo: {att.tipo}\n- sha256: {att.sha256}\n"
        f"- primera_aparicion: {att.primera_aparicion}\n"
        f"- mensajes: {', '.join(att.mensajes)}\n- etiquetas: []\n\n"
        f"## Descripción\n\n(pendiente; OCR en fase 2)\n"
    )
    (out / "adjuntos" / f"{base}{ficha_suffix}").write_text(ficha, encoding="utf-8")


def emails_src_dir(case_id: str) -> Path:
    from core.casos.case_locator import path_for, resolve_ref
    return path_for(resolve_ref(case_id)) / "00_Input" / "03_Email"


def emails_out_dir(case_id: str) -> Path:
    from core.casos.case_locator import path_for, resolve_ref
    return path_for(resolve_ref(case_id)) / "01_Procesado" / "Emails"


def atomize_case(case_id: str) -> AtomizeReport:
    return atomize_dir(emails_src_dir(case_id), emails_out_dir(case_id))
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_email_atomize_pipeline.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Ejecutar TODA la suite del módulo**

Run: `python -m pytest tests/test_email_atomize_*.py -q`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_pipeline.py
git commit -m "feat(email-atomize): orquestación e2e de la Capa A (Fase 1 T9)"
```

---

## Task 10: CLI (`scripts/atomize_emails.py`)

**Files:**
- Create: `scripts/atomize_emails.py`
- Test: `tests/test_atomize_emails_cli.py`

- [ ] **Step 1: Escribir el test (debe fallar)**

`tests/test_atomize_emails_cli.py`:
```python
from __future__ import annotations
from email.message import EmailMessage
import scripts.atomize_emails as cli


def _eml(mid, subj):
    m = EmailMessage(); m["Message-ID"] = mid; m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("c"); return m.as_bytes()


def test_cli_con_src_y_out_explicitos(tmp_path, capsys):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-12_a.eml").write_bytes(_eml("<a@x>", "Uno"))
    rc = cli.main(["--src", str(src), "--out", str(out)])
    assert rc == 0
    assert (out / "mensajes").is_dir()
    assert list((out / "mensajes").glob("*.md"))
    captured = capsys.readouterr().out
    assert "mensajes" in captured.lower()
```

- [ ] **Step 2: Ejecutar el test (debe fallar)**

Run: `python -m pytest tests/test_atomize_emails_cli.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar el CLI**

`scripts/atomize_emails.py`:
```python
"""CLI fino del motor de atomización de correo.

Uso:
    python -m scripts.atomize_emails --ref W-02VND1
    python -m scripts.atomize_emails --src "<.../03_Email>" --out "<.../Emails>"

Solo orquesta ``core.email_atomize.pipeline`` (la lógica vive en el core).
"""
from __future__ import annotations

import argparse
import sys

from core.email_atomize import pipeline as P


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomiza 03_Email a 01_Procesado/Emails.")
    parser.add_argument("--ref", help="case_id o W-code del expediente")
    parser.add_argument("--src", help="ruta a 00_Input/03_Email (alternativa a --ref)")
    parser.add_argument("--out", help="ruta de salida (con --src)")
    args = parser.parse_args(argv)

    if args.ref:
        report = P.atomize_case(args.ref)
    elif args.src and args.out:
        report = P.atomize_dir(args.src, args.out)
    else:
        parser.error("usa --ref, o --src junto con --out")
        return 2

    print(report.resumen())
    for e in report.errores:
        print(f"  ERROR: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `python -m pytest tests/test_atomize_emails_cli.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/atomize_emails.py tests/test_atomize_emails_cli.py
git commit -m "feat(email-atomize): CLI scripts/atomize_emails.py (Fase 1 T10)"
```

---

## Task 11: Verificación en vivo sobre W-02VND1 + test de regresión de mojibake

**Files:**
- Test: `tests/test_email_atomize_regresion.py`

- [ ] **Step 1: Correr el motor sobre el caso real (verificación manual, solo lectura de 00_Input)**

Run (PowerShell, desde la raíz):
```powershell
$out = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - [inmueble] - (W-02VND1) - Vuelta\01_Procesado\Emails"
$src = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - [inmueble] - (W-02VND1) - Vuelta\00_Input\03_Email"
& ".\.venv\Scripts\python.exe" -m scripts.atomize_emails --src "$src" --out "$out"
```
Expected: imprime `277 mensajes atómicos, …`. Verificar:
- `(Get-ChildItem "$out\mensajes" -Filter *.md | Measure-Object).Count` == **277** (coincide con la medición).
- `Test-Path "$out\corpus.jsonl"`, `"$out\_registro.json"`, `"$out\CORREOS_LECTURA.md"`, `"$out\INDICE_ADJUNTOS.md"` == True.
- `(Get-Content "$out\corpus.jsonl" | Measure-Object -Line).Lines` == **278** (meta + 277).
- Abrir 2-3 `.md` de mensajes con cuerpo en catalán (p. ej. los 3 que tenían mojibake) y confirmar a ojo que el cuerpo está limpio (sin `Ã`/`Â`).
- Re-correr el mismo comando → `_registro.json` no renumera (los MSG-id se conservan); la corrida es idempotente.

Anotar los conteos reales en el commit de cierre. **No** se versiona la salida (vive en el Drive del caso, gitignored vía `data/CASOS`/Drive).

- [ ] **Step 2: Escribir un test de regresión de mojibake con un fixture sintético (debe fallar)**

`tests/test_email_atomize_regresion.py`:
```python
from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import bodies as B


def test_plain_limpio_gana_a_html_mal_declarado():
    """Reproduce el patrón real W-02VND1: text/plain UTF-8 correcto + text/html con
    bytes mal declarados. El motor debe quedarse con el plano limpio (sin mojibake)."""
    m = EmailMessage()
    m["Message-ID"] = "<cat@x>"; m["Subject"] = "Relat"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("Crec que aquest document ja està inclòs en la relació.")
    # html "equivalente" pero con caracteres que en mal-declarado se verían como mojibake
    m.add_alternative("<p>Crec que aquest document ja està inclòs en la relació.</p>",
                      subtype="html")
    cuerpo = B.extraer_cuerpo(m.as_bytes())
    assert "està inclòs en la relació" in cuerpo.texto
    assert "Ã" not in cuerpo.texto and "Â" not in cuerpo.texto
    assert cuerpo.formato_original == "plain"
    assert cuerpo.mojibake_marcado is False
```

- [ ] **Step 3: Ejecutar el test (debe pasar — valida la regla prefer-plain)**

Run: `python -m pytest tests/test_email_atomize_regresion.py -q`
Expected: PASS.

- [ ] **Step 4: Suite completa verde**

Run: `python -m pytest -q --tb=no`
Expected: la suite pasa con el mismo nº de skipped que antes + los nuevos tests de Fase 1. Si algún número difiere por causa ajena, explicarlo en `STATUS.md`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_email_atomize_regresion.py
git commit -m "test(email-atomize): regresión prefer-plain anti-mojibake + verificación W-02VND1 (Fase 1 T11)"
```

---

## Task 12: Cierre de Fase 1 — docs + STATUS/PLAN

**Files:**
- Modify: `STATUS.md`, `PLAN.md`, `CLAUDE.md` (§Referencias rápidas), `docs/MEJORAS_FUTURAS.md` (si hay flecos)

- [ ] **Step 1: Actualizar `PLAN.md`**

Añadir una entrada `[SIGUIENTE-EMAIL-ATOMIZE]` (o promover desde backlog) con:
- Fase 1 marcada `[x]` y el rango de hashes de commits.
- Fases 2 (Capa B inline) y 3 (capa de caso) como pendientes, citando el spec y este plan.

- [ ] **Step 2: Actualizar `CLAUDE.md` §Referencias rápidas**

Añadir línea:
```markdown
- **Spec/plan atomización de correo**: `docs/superpowers/specs/2026-06-24-email-atomize-design.md` + `docs/superpowers/plans/2026-06-24-email-atomize-fase1.md`
```

- [ ] **Step 3: Anotar flecos en `docs/MEJORAS_FUTURAS.md`** (si los hay tras la corrida real)

P. ej.: HTML→texto básico (mejorable con un conversor dedicado); idioma por heurística mínima; `cco` siempre vacío en Capa A (no consta en RFC entrante).

- [ ] **Step 4: Cerrar con la suite verde y commit acotado**

```bash
git add STATUS.md PLAN.md CLAUDE.md docs/MEJORAS_FUTURAS.md
git commit -m "docs(email-atomize): cierre Fase 1 — Capa A completa + verificación W-02VND1"
```

---

## Self-Review (autor del plan)

**Cobertura del spec (§ → tarea):**
- §3 arquitectura del módulo → Tareas 1-10 (un módulo por tarea).
- §4 salida (mensajes/, adjuntos/, corpus.jsonl, _registro.json, CORREOS_LECTURA.md, INDICE_ADJUNTOS.md) → T7-T9.
- §5 IDs congelados + idempotencia → T1, T9 (test idempotencia).
- §6 cuerpo limpio (prefer-plain, charset condicional, top/bottom/intercalada) → T5; mojibake → T11.
- §7 frontmatter + corpus + hilo estable → T2 (hilo), T7 (frontmatter), T8 (corpus).
- §8 adjuntos dedup sha256 + decorativo + ficha → T6, T9 (`_escribe_adjunto`).
- §9 CORREOS_LECTURA.md → T8.
- §10 forense (sha por msg/adj, no toca 00_Input, idempotente) → T1/T9; "acto de reenviar" se captura como `procedencia`/`ruta_anidacion` en frontmatter+corpus (evento jsonl dedicado: diferido, suficiente con la procedencia en Fase 1 — anotar en MEJORAS si Nikolai lo quiere como evento aparte).
- §11 capa genérica (salida por defecto) → cubierta; capa de caso → Fase 3 (fuera de este plan).
- §12 fase 1 → este plan; §13 abiertos → no bloquean Fase 1; §14 tests → cada tarea.

**Escaneo de placeholders:** sin TBD/TODO en código de pasos; todo paso de código muestra el código; comandos con salida esperada.

**Consistencia de tipos:** `RegistroMensaje`/`AdjuntoRef`/`AdjuntoUnico` (model.py) usados igual en render/corpus/pipeline; `Cabeceras` (headers) y `Cuerpo` (bodies) consumidos en pipeline con los mismos nombres de campo; `Registro.msg_id_for(message_id, *, sha)` / `att_id_for(sha)` consistentes T1↔T9; `colapsar`→`MensajeColapsado` con `.raw/.procedencia/.ruta_anidacion` usados en pipeline.

**Fleco conocido (no bloqueante):** `_idioma` y el HTML→texto básico son heurísticos; aceptable para Fase 1, anotado para MEJORAS. La numeración de `MSG-NNNNN` sigue el orden de `colapsar` (orden de `glob` de los `.eml`), estable entre corridas porque las claves quedan congeladas en `_registro.json` desde la 1ª corrida.
