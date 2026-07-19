---
estado: historico
dueño: Nikolai Tyukhay
---

# PLAN — Aplanado byte-fiel de emails anidados en el export de etiquetas Gmail

> **Parte 1 de 2.** Esta parte cubre los emails que viajan **como `.eml` adjunto**
> (`message/rfc822`) dentro de un correo padre. La **Parte 2** —emails que viajan
> como **enlace a Drive** dentro del padre— se aborda en un hilo aparte y NO entra
> en este plano.
>
> Origen: hilo Cowork sobre el caso W-02VND1 ([inmueble]). Todo el código de abajo
> está **verificado en sandbox** (7/7 tests en verde) antes de redactar el plano.

## 1. Problema

Al exportar una etiqueta Gmail al expediente (`core/email_export.py`), los emails
que viajan **adjuntos dentro de otro email** no se extraen. Ejemplo real:
`2026-06-08_mails_consulado` no muestra los correos que lleva dentro.

**Causa raíz.** En `split_eml`, las partes `message/rfc822` se descartan porque
`get_payload(decode=True)` devuelve `None` para ellas (el contenido es un `Message`
anidado, no bytes codificados), y existe `if payload is None: continue`. Los `.eml`
adjuntos no se pierden del todo —siguen embebidos en el `.eml` padre, byte-fiel—
pero no se extraen como ficheros legibles.

**Contexto de uso (clave para el diseño).** Los consultores de E&V reenvían en
bloque todas las conversaciones con un contacto (p. ej. `per01a@example.invalid`). Gmail
crea **un** correo padre que transporta años de conversaciones, cada una como `.eml`
adjunto. El padre es solo un **sobre de transporte**; la prueba son las
conversaciones individuales.

## 2. Decisiones cerradas (con Nikolai)

1. **Nombre del hijo:** por las cabeceras del **propio** email anidado →
   `AAAA-MM-DD_asunto.eml` (no por el filename MIME, que suele venir genérico).
   Fallback: filename MIME → `email_adjunto.eml`. Colisiones: `_ruta_unica`
   (`_2`, `_3`…).
2. **Fidelidad:** el `.eml` hijo debe ser **byte-original** (idéntico a como viajó),
   no una re-serialización. `as_bytes()` NO sirve (normaliza CRLF→LF, repliega
   cabeceras). Hay que **rebanar los bytes crudos** y decodificar el
   transfer-encoding de la parte. El CRLF que precede al delimitador de frontera
   pertenece al delimitador (RFC 2046), así que el hijo recuperado lo omite: eso es
   el original correcto.
3. **Aplanado por defecto:** los hijos se extraen a **primer nivel** de `03_Email`,
   nombrados por su propia fecha → se integran en la cronología real (un bloque
   2021-2026 se ordena solo). Flag de opt-out `--no-aplanar-emails`.
4. **Padre en la cronología:** se conserva (nota de remisión + prueba de quién
   reenvió qué y cuándo). Consecuencia asumida: cada conversación se guarda dos
   veces (embebida en el padre + suelta); la dedup por `Message-ID` evita que se
   multiplique al reimportar.
5. **Recursión:** hasta las hojas (email dentro de email dentro de email). Cada
   nivel es byte-original.
6. **Dedup por `Message-ID`:** una conversación reenviada por dos consultores, o
   suelta y dentro de un bloque, colapsa en un único fichero.
7. **Procedencia:** se registra en el evento `upload_email` de `_intake_log.jsonl`
   (campo `forwarded_in` por mensaje), NO en el manifest (su `register` solo
   persiste metadatos extra en aliases, no en primarios).
8. **Red de seguridad:** si el rebanado crudo no halla nada pero el parser sí ve
   `message/rfc822`, caer a `as_bytes()` y dejar aviso en `report.errors`. Nunca se
   pierde un email; en el peor caso una copia no byte-fiel marcada para revisión.

**Limitación conocida:** el rebanado crudo es ingenuo ante un `boundary` reutilizado
en distintos niveles de anidamiento. En la práctica no ocurre (boundary aleatorio) y
el fallback lo cubre. Documentar en `docs/MEJORAS_FUTURAS.md`.

## 3. Cambios — `core/email_export.py`

### 3.1 Capa pura — funciones nuevas

```python
import base64
import quopri
from email.message import Message
from typing import Iterator


def _payload_message(parte: Message) -> Message | None:
    """El Message anidado de una parte message/rfc822, o None."""
    payload = parte.get_payload()
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    return payload if isinstance(payload, Message) else None


def _iter_partes_hoja(msg: Message) -> Iterator[Message]:
    """Itera partes hoja tratando message/rfc822 como hoja (NO desciende en ella).

    Lo usa split_eml para extraer adjuntos binarios sin explotar los PDF que viajan
    DENTRO de un email anidado (esos se quedan embebidos en su .eml)."""
    if msg.get_content_type() == "message/rfc822":
        yield msg
        return
    if msg.get_content_maintype() == "multipart":
        for sub in msg.iter_parts():
            yield from _iter_partes_hoja(sub)
        return
    yield msg


def _split_headers_body(block: bytes) -> tuple[bytes, bytes]:
    for sep in (b"\r\n\r\n", b"\n\n"):
        i = block.find(sep)
        if i != -1:
            return block[:i], block[i + len(sep):]
    return block, b""


def _iter_raw_rfc822(block: bytes) -> Iterator[tuple[bytes, str]]:
    """(cuerpo_verbatim, transfer_encoding) por cada parte message/rfc822 del bloque
    crudo, tratando rfc822 como hoja (no desciende). El cuerpo es el byte MIME tal cual."""
    headers, body = _split_headers_body(block)
    m = _parse_message(headers + b"\r\n\r\n")
    if m.get_content_type() == "message/rfc822":
        yield body, (m.get("content-transfer-encoding") or "").strip().lower()
        return
    if m.get_content_maintype() == "multipart":
        boundary = m.get_boundary()
        if not boundary:
            return
        delim = b"--" + boundary.encode()
        for ch in body.split(delim)[1:]:
            if ch.startswith(b"--"):                       # delimitador de cierre
                break
            ch = ch[2:] if ch.startswith(b"\r\n") else ch[1:] if ch[:1] in (b"\n", b"\r") else ch
            if ch.endswith(b"\r\n"):                        # el CRLF final es del delimitador
                ch = ch[:-2]
            elif ch[-1:] in (b"\n", b"\r"):
                ch = ch[:-1]
            yield from _iter_raw_rfc822(ch)


def _decode_cte(body: bytes, cte: str) -> bytes:
    if cte == "base64":
        return base64.b64decode(body)
    if cte == "quoted-printable":
        return quopri.decodestring(body)
    return body                                            # 7bit/8bit/binary → verbatim


def iter_nested_originals(raw: bytes) -> Iterator[tuple[bytes, str]]:
    """(eml_original_bytes, parent_message_id) por cada email anidado, recursivo a hojas.

    Byte-fiel: rebana el crudo (sin pasar por el parser, que normaliza CRLF) y
    decodifica el transfer-encoding → el .eml hijo EXACTO como viajó."""
    parent_mid = message_id_of(raw)
    for body, cte in _iter_raw_rfc822(raw):
        try:
            child = _decode_cte(body, cte)
        except Exception:
            continue
        if not child.strip():
            continue
        yield child, parent_mid
        yield from iter_nested_originals(child)             # nietos, también byte-originales
```

### 3.2 `split_eml` — reemplazar el cuerpo

Sustituir el `for parte in msg.walk():` actual por `_iter_partes_hoja` y saltar
`message/rfc822` (lo gestiona el aplanado):

```python
def split_eml(raw: bytes) -> tuple[bytes, list[tuple[str, str, bytes]]]:
    msg = _parse_message(raw)
    adjuntos: list[tuple[str, str, bytes]] = []
    for parte in _iter_partes_hoja(msg):
        if parte.get_content_type() == "message/rfc822":
            continue  # los emails anidados los gestiona el aplanado, no split_eml
        filename = parte.get_filename()
        disposicion = parte.get_content_disposition()
        if disposicion != "attachment" and not filename:
            continue
        payload = parte.get_payload(decode=True)
        if payload is None:
            continue
        nombre = _sanea_nombre_fichero(filename or "", fallback="adjunto")
        adjuntos.append((nombre, parte.get_content_type(), payload))
    return raw, adjuntos
```

### 3.3 Aplanado + fallback

```python
def _nested_con_fallback(raw: bytes, report: "ExportReport") -> list[tuple[bytes, str]]:
    """Emails anidados byte-originales; si el rebanado crudo no halla nada pero el
    parser sí ve message/rfc822, cae a as_bytes() y deja aviso (nunca se pierde un email)."""
    found = list(iter_nested_originals(raw))
    if found:
        return found
    msg = _parse_message(raw)
    fb: list[tuple[bytes, str]] = []
    pmid = message_id_of(raw)
    for parte in msg.walk():
        if parte.get_content_type() == "message/rfc822":
            inner = _payload_message(parte)
            if inner is not None:
                fb.append((inner.as_bytes(), pmid))
    if fb:
        report.errors.append(
            f"aplanado byte-fiel falló para {pmid or '(sin id)'}; "
            f"{len(fb)} email(s) guardados re-serializados (revisar)."
        )
    return fb


def _aplana_anidados(dest: Path, raw_bytes: bytes, vistos: set[str],
                     procedencia: dict[str, str], report: "ExportReport") -> None:
    """Extrae a primer nivel cada email anidado (byte-original), deduplicando por Message-ID."""
    for inner_bytes, parent_mid in _nested_con_fallback(raw_bytes, report):
        mid = message_id_of(inner_bytes)
        if mid and mid in vistos:
            report.nested_dedup += 1
            continue
        if mid:
            vistos.add(mid)
            if parent_mid:
                procedencia[mid] = parent_mid
        nombre = eml_filename(parse_headers(inner_bytes))
        ruta = _ruta_unica(dest, nombre)
        ruta.write_bytes(inner_bytes)
        report.files.append(str(ruta.relative_to(dest)))
        report.nested_flattened += 1
```

### 3.4 `ExportReport` — dos contadores nuevos

```python
    nested_flattened: int = 0   # emails anidados extraídos a primer nivel
    nested_dedup: int = 0       # emails anidados saltados por Message-ID duplicado
```

Y en `resumen()` añadir:
`f"{self.nested_flattened} emails anidados aplanados ({self.nested_dedup} dup)"`.

### 3.5 `export_label` — flag + llamada al aplanado

- Firma: añadir `flatten_nested_emails: bool = True`.
- Antes del bucle: `procedencia: dict[str, str] = {}`.
- Tras `report.written += 1; nuevos_gids.append(gid)`:

```python
            if flatten_nested_emails:
                _aplana_anidados(dest, raw_bytes, vistos, procedencia, report)
```

- En la llamada a la traza: `_emit_traza(case_id, dest, account, label, report, procedencia)`.

`write_indices(dest)` ya recoge padre + hijos → entran juntos en `CRONOLOGIA.md`
ordenados por su fecha real.

### 3.6 `_emit_traza` — procedencia

- Firma: `..., report: ExportReport, procedencia: dict[str, str] | None = None`.
- `procedencia = procedencia or {}`.
- En la rama `if es_eml:`, al construir el dict de `nuevos_eml`, añadir:
  `"forwarded_in": procedencia.get(mid)`.

## 4. Cambios — `scripts/export_label_emails.py`

```python
    parser.add_argument("--no-aplanar-emails", dest="aplanar",
                        action="store_false", default=True,
                        help="No aplanar los emails reenviados como .eml adjunto "
                             "(por defecto SÍ se aplanan a primer nivel).")
    ...
    report = export_label(
        args.account, args.label, dest,
        case_id=case_id, extract_attachments=args.extraer_adjuntos,
        max_workers=args.workers, force=args.force,
        flatten_nested_emails=args.aplanar,
    )
```

## 5. Tests — `tests/test_email_export.py`

Añadir el bloque siguiente (verificado en sandbox). Construye MIME crudo a mano
porque la fidelidad al bit exige controlar los bytes exactos.

```python
import base64
import pytest
from email.message import EmailMessage as PyEmailMessage
from core import email_export as ee


def _envoltorio(boundary: bytes, partes: list[bytes], *, mid: bytes = b"<padre@ev>") -> bytes:
    cab = (b"Message-ID: " + mid + b"\r\nSubject: RV bloque\r\n"
           b"Date: Mon, 08 Jun 2026 12:00:00 +0200\r\nFrom: consultor@engelvoelkers.com\r\n"
           b"MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=\"" + boundary + b"\"\r\n\r\n")
    cuerpo = b""
    for p in partes:
        cuerpo += b"--" + boundary + b"\r\n" + p
    return cab + cuerpo + b"--" + boundary + b"--\r\n"


def _parte_rfc822(eml: bytes, *, b64: bool = False) -> bytes:
    if b64:
        return (b"Content-Type: message/rfc822\r\nContent-Transfer-Encoding: base64\r\n\r\n"
                + base64.encodebytes(eml))
    return (b"Content-Type: message/rfc822\r\nContent-Disposition: attachment; "
            b"filename=\"c.eml\"\r\n\r\n" + eml)


def test_nested_original_byte_fiel_7bit_y_nombre():
    inner = (b"Message-ID: <leaf@x>\r\nSubject: RE: consulado\r\n"
             b"Date: Tue, 11 May 2023 09:00:00 +0200\r\nFrom: per01a@example.invalid\r\n"
             b"Content-Type: text/plain; charset=\"utf-8\"\r\n\r\nCuerpo jardin.\tfin\r\n")
    raw = _envoltorio(b"BTOP", [b"Content-Type: text/plain\r\n\r\nhola\r\n", _parte_rfc822(inner)])
    res = list(ee.iter_nested_originals(raw))
    assert len(res) == 1
    child, parent_mid = res[0]
    assert child == inner[:-2]                  # byte-original (el CRLF final es del delimitador)
    assert parent_mid == "padre@ev"
    assert ee.eml_filename(ee.parse_headers(child)) == "2023-05-11_consulado.eml"


def test_nested_original_base64():
    inner = b"Subject: hijo b64\r\nDate: Wed, 01 Jan 2025 00:00:00 +0100\r\n\r\nbody\xc3\xb1\r\n"
    raw = _envoltorio(b"BTOP", [_parte_rfc822(inner, b64=True)])
    res = list(ee.iter_nested_originals(raw))
    assert len(res) == 1 and res[0][0] == inner


def test_nested_original_recursivo_nieto_y_provenance_encadenada():
    nieto = (b"Message-ID: <nieto@x>\r\nSubject: nieto\r\n"
             b"Date: Mon, 02 Feb 2022 00:00:00 +0100\r\n\r\nz\r\n")
    medio = _envoltorio(b"BMED", [_parte_rfc822(nieto)], mid=b"<medio@x>")   # boundary distinto
    raw = _envoltorio(b"BTOP", [_parte_rfc822(medio)])
    mids = {ee.message_id_of(b): p for b, p in ee.iter_nested_originals(raw)}
    assert set(mids) == {"medio@x", "nieto@x"}
    assert mids["medio@x"] == "padre@ev"
    assert mids["nieto@x"] == "medio@x"


def test_nested_original_lf_only():
    inner = b"Subject: lf\nDate: Tue, 11 May 2023 09:00:00 +0200\n\ncuerpo\n"
    raw = (b"Content-Type: multipart/mixed; boundary=\"B\"\n\n--B\n"
           b"Content-Type: message/rfc822\n\n" + inner + b"--B--\n")
    res = list(ee.iter_nested_originals(raw))
    assert len(res) == 1 and res[0][0] == inner[:-1]


def test_fallback_reserializa_y_avisa(monkeypatch):
    padre = PyEmailMessage()
    padre["Message-ID"] = "<p5@ev>"; padre["Subject"] = "padre"
    padre["Date"] = "Mon, 08 Jun 2026 12:00:00 +0200"; padre.set_content("x")
    hijo = PyEmailMessage()
    hijo["Subject"] = "hijo"; hijo["Date"] = "Tue, 11 May 2023 09:00:00 +0200"; hijo.set_content("y")
    padre.add_attachment(hijo, filename="c.eml")

    monkeypatch.setattr(ee, "iter_nested_originals", lambda raw: iter(()))   # fuerza el disparador
    rep = ee.ExportReport(account="c@ev", label="L")
    got = ee._nested_con_fallback(padre.as_bytes(), rep)
    assert len(got) == 1
    assert len(rep.errors) == 1 and "p5@ev" in rep.errors[0]
    assert ee.eml_filename(ee.parse_headers(got[0][0])) == "2023-05-11_hijo.eml"


def test_split_eml_salta_rfc822_y_no_explota_pdf_interno():
    hijo = PyEmailMessage()
    hijo["Subject"] = "h"; hijo["Date"] = "Tue, 11 May 2023 09:00:00 +0200"; hijo.set_content("z")
    hijo.add_attachment(b"%PDF in", maintype="application", subtype="pdf", filename="int.pdf")
    padre = PyEmailMessage()
    padre["Subject"] = "p"; padre["Date"] = "Mon, 08 Jun 2026 12:00:00 +0200"; padre.set_content("x")
    padre.add_attachment(hijo, filename="c.eml")
    padre.add_attachment(b"%PDF dir", maintype="application", subtype="pdf", filename="dir.pdf")
    _, adjuntos = ee.split_eml(padre.as_bytes())
    assert {fn for fn, _m, _d in adjuntos} == {"dir.pdf"}
```

**Tests end-to-end de `export_label`** (a redactar con el `_FakeService` ya existente
en el fichero): (a) padre + N hijos → N+1 `.eml` a primer nivel, `nested_flattened==N`;
(b) mismo hijo en dos padres → una sola copia, `nested_dedup>=1`; (c) `CRONOLOGIA.md`
ordena el hijo por SU fecha (anterior al padre); (d) `flatten_nested_emails=False` →
solo el padre a primer nivel; (e) el evento `upload_email` lleva `forwarded_in` con el
Message-ID del padre.

## 6. Verificación y cierre

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m pytest -q tests/test_email_export.py
python -m pytest -q --tb=no            # suite completa sigue verde
```

Reextracción del caso W-02VND1 (rebuild forzado, idempotente):

```powershell
python -m scripts.export_label_emails --ref W-02VND1 `
  --account nikolai.tyukhay@engelvoelkers.com `
  --label "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - [inmueble] - (W-02VND1)" `
  --extraer-adjuntos --force
```

Comprobar en `03_Email`: las conversaciones del bloque a primer nivel, nombradas por
su fecha, integradas en `CRONOLOGIA.md`; el padre conservado; `_intake_log.jsonl` con
`forwarded_in` en los hijos.

Al cerrar: anotar la limitación del boundary compartido en `docs/MEJORAS_FUTURAS.md` y
dejar `PLAN.md`/`STATUS.md` al día con el hash del commit.

### 6.1 Validación contra datos reales del caso (verificado 2026-06-24)

Hay un fixture real en `00_Input/03_Email/` de W-02VND1 que exhibe exactamente el bug
y permite validar end-to-end sin sintéticos:

- **Padre:** `2026-06-08_mails_consulado.eml` — de `persona.cuatro@engelvoelkers.com`
  (consultora E&V; confirma el flujo de reenvío en bloque). Lleva un adjunto
  `Content-Type: message/rfc822; name="offer letter [inmueble].eml"` que el export
  actual NO extrae.
- **Hijo esperado tras el fix:** sus cabeceras son `Subject: Re: offer letter [inmueble]`,
  `Date: Wed, 23 Jul 2025 17:24:48 +0200` → nombre canónico `2025-07-23_offer_letter_inmueble.eml`.
- **Validación de la dedup (clave):** en la carpeta YA existen
  `2025-07-23_offer_letter_inmueble.eml` y `…_2.eml` (exportados sueltos desde la
  etiqueta). Si ese email se exportó suelto **y** viaja anidado en el padre con el
  mismo `Message-ID`, el aplanado debe **colapsarlo** (no crear un tercer fichero). Es
  el test real de la dedup por `Message-ID`. Comprobar el `Message-ID` de ambos antes
  de dar por buena la corrida.

Detalles empíricos del formato real (anclan decisiones del plano):

- Los boundaries reales de Gmail son tokens largos aleatorios
  (`000000000000e6aa6e0653c097ef`…): la limitación del *boundary* compartido es
  teórica, nunca colisiona en la práctica.
- El cuerpo del padre es `multipart/mixed` → `multipart/alternative` (text/plain +
  text/html); el HTML va **quoted-printable**. No afecta a la Parte 1 (los `.eml`
  anidados son partes `message/rfc822`), pero es el terreno de la **Parte 2** (enlaces
  a Drive embebidos en el HTML).

## 7. Fuera de alcance (→ Parte 2, hilo aparte)

Emails que el consultor reenvía **como enlace a Drive/Gmail** en vez de como `.eml`
adjunto. Ahí no viaja contenido en el correo, solo un enlace que exige sesión
autenticada; requiere resolución vía conector de Drive. Se diseña por separado.
Instrucción operativa provisional: pedir a los consultores reenvío **como adjunto**.
