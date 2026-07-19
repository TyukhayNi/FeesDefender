---
estado: historico
dueño: Nikolai Tyukhay
---

# PLAN — Rescate de ficheros enlazados (Drive/Gmail) en el export de etiquetas Gmail

> **Parte 2 de 2.** La **Parte 1** (`docs/superpowers/plans/PLAN_email_aplanado_anidados.md`) cubre los
> emails que viajan **como `.eml` adjunto** (`message/rfc822`) dentro de un correo
> padre. Esta Parte 2 cubre el caso complementario: el material que **no viaja en el
> correo**, sino como **enlace a Drive/Gmail** en el cuerpo del padre, y exige sesión
> autenticada para recuperarlo.
>
> Origen: hilo Cowork sobre el caso W-02VND1 ([inmueble]). Decisiones de alcance
> cerradas con Nikolai (2026-06-24).

## 1. Problema

Parte del material probatorio no viaja en el correo: el consultor reenvía **un
enlace** a Drive/Gmail (carpeta, hoja de cálculo, fichero, descarga directa) en vez
del adjunto. El export actual (`core/email_export.py`) no recupera nada de esos
enlaces: solo extrae partes MIME del propio mensaje.

**Gesto manual que se automatiza.** Hoy el flujo es manual: se abre el correo en
Gmail, se clica el enlace, se abre una pestaña del navegador y desde ahí se descarga
el fichero (a menudo un `.eml`). La Parte 2 hace exactamente ese clic-y-descarga de
forma programática, con el permiso de la cuenta `@engelvoelkers.com`, para no repetirlo
a mano en decenas de correos del histórico.

**Contexto de uso.** La política operativa nueva ya pide a los consultores reenviar
**como adjunto**, no como enlace (eso lo cubre la Parte 1). Por tanto esta función
existe sobre todo para **rescatar el backlog histórico** ya recibido como enlace.

## 2. Decisiones cerradas (con Nikolai, 2026-06-24)

1. **Carpetas de Drive (`/drive/folders/<id>`): NO se bajan.** Un enlace a carpeta es
   un cajón de tamaño impredecible (puede solaparse con `01_Drive EV` o traer material
   irrelevante). Se **detecta y se anota** en la traza (qué carpeta, `file_id`), pero
   no se vuelca. Si en algún caso hace falta, el volcado es acción manual del letrado.
2. **Documentos nativos de Google (hojas, docs, slides — `/spreadsheets/d/`,
   `/document/d/`, `/presentation/d/`): NO se captura nada.** Son documentos vivos sin
   bytes inmutables; no hay original que copiar. No se exporta ni se deposita fichero.
   *(Interpretación asumida, vetable: se deja una nota mínima en la traza de que el
   enlace existió —coste cero, integridad forense— sin depositar nada.)*
3. **Activación: SIEMPRE activo, con opt-out.** `resolve_drive_links: bool = True` en
   `export_label`; bandera CLI `--no-resolver-enlaces` para desactivarlo.
4. **Lo único que se descarga: el fichero binario de descarga directa** (`/file/d/<id>`,
   `uc?export=download&id=<id>`), **byte-fiel**, verificado por `md5Checksum` de Drive,
   **filtrando las imágenes de firma**.
5. **El `.eml` rescatado reentra en la Parte 1.** Si el binario descargado es un email
   (`.eml` / `message/rfc822`), se trata como un mensaje más: nombre por su propia
   fecha, depósito a primer nivel de `03_Email`, dedup por `Message-ID`, y aplanado
   recursivo de sus anidados (reutiliza `_aplana_anidados` de la Parte 1).
6. **Dedup por contenido, no por `Message-ID`.** Un fichero de Drive no tiene
   `Message-ID`. La dedup de los binarios no-email se apoya en el `IntakeManifest`
   (SHA-256, cross-source): un fichero idéntico que ya esté en `01_Drive EV` o como
   adjunto colapsa solo. Para los `.eml` rescatados, dedup por `Message-ID` (Parte 1).
7. **Procedencia.** Cada fichero rescatado registra `resolved_from` = URL original +
   `drive_file_id` en la traza (paralelo al `forwarded_in` de la Parte 1).
8. **Idempotencia con reintento de fallos.** Índice de resolución por `drive_file_id`
   (+ `md5Checksum`/`modifiedTime`): los enlaces ya resueltos no se rebajan. Los
   fallos por permiso/expiración **NO** se marcan como definitivos: se reintentan en la
   siguiente corrida (mismo patrón que el `rclone_returncode` del `.pulled` en
   `intake_drive`), porque un permiso denegado hoy puede concederse mañana.

## 3. Bloqueante técnico a verificar antes de codificar

El token OAuth de `core.gmail_source` es **`gmail.readonly` puro** — no ve Drive. La
única credencial con scope Drive es la del remote **`gdrive_ev`** (cuenta
`@engelvoelkers.com`), que `core.intake_drive._get_drive_access_token()` ya gestiona
(refresh proactivo + backoff de rate-limit). Pero `get_drive_folder_info` solo hace
**metadatos** (`files.get`); la **descarga de bytes** (`files.get?alt=media`) usa scope
de contenido sin probar.

**Verificar en Claude Code** que el remote `gdrive_ev` se configuró con scope
`drive`/`drive.readonly` (descarga de contenido), no `drive.metadata.readonly`. Si es
metadata-only, `alt=media` devuelve 403 y todo el rescate cae a manual. Comprobación
empírica: `rclone config show gdrive_ev` (campo `scope`) o un `alt=media` de prueba
contra un `file_id` conocido.

## 4. Taxonomía de enlaces y enrutado

Las URLs viajan **quoted-printable** en el HTML. `email` con `policy.default` ya
decodifica QP/base64 + charset al hacer `parte.get_content()` sobre las partes de
texto; tras extraer, hay que **desescapar entidades HTML** (`&amp;` → `&`) y limpiar
`<`, `>`, espacios y soft-breaks. Extraer de **ambas** partes (`text/plain` y
`text/html`) del padre, **sin** descender en `message/rfc822` (eso es la Parte 1), y
deduplicar URLs por `(tipo, id)`.

| Patrón de URL | Tipo | Acción |
| --- | --- | --- |
| `/drive/folders/<id>` (y `/u/N/folders/`) | Carpeta | **No bajar.** Anotar en traza (`skipped_folder`). |
| `/spreadsheets/d/<id>`, `/document/d/<id>`, `/presentation/d/<id>` | Nativo Google | **No capturar.** Nota mínima en traza (`skipped_native`). |
| `/file/d/<id>`, `uc?export=download&id=<id>` | Binario directo | **Descargar** bytes, verificar `md5`, filtrar firma, enrutar (.eml vs. otro). |
| `<img src="…uc?export=download…">` (firma) | Imagen de firma | **Filtrar.** No ingerir. |
| `mail.google.com/...#...` (permalink Gmail) | Email en buzón | *(Candidato — confirmar en datos reales)* resolver vía Gmail API `format=raw` (token gmail.readonly ya disponible) → reentra Parte 1. |

**Filtro de firma.** Una imagen es de firma si: viene de `<img src>` (no de `<a href>`),
su `mimeType` es de imagen, es pequeña (umbral a fijar, p.ej. < 50 KB), y/o se repite
idéntica (mismo `file_id`) en varios correos del lote. Distinguir esto del
adjunto-real-por-enlace es lo que evita ensuciar el expediente.

## 5. Cambios — capa pura (`core/email_export.py`)

Detección de enlaces en el cuerpo del padre. No toca `split_eml` ni el aplanado de la
Parte 1.

```python
from dataclasses import dataclass
from enum import Enum
from html import unescape
from typing import Iterator


class DriveLinkType(Enum):
    FOLDER = "folder"            # /drive/folders/<id>            → no bajar
    NATIVE = "native"            # /spreadsheets|document|... /d  → no capturar
    FILE = "file"               # /file/d/<id>, uc?export=download → descargar
    IMAGE_SIG = "image_sig"      # <img src=…uc?export=download…>  → filtrar
    GMAIL = "gmail"             # mail.google.com permalink       → Gmail API (P1)


@dataclass(frozen=True)
class DriveLink:
    raw_url: str
    type: DriveLinkType
    file_id: str
    from_img: bool               # True si proviene de <img src>, no de <a href>


def iter_body_text(raw: bytes) -> Iterator[tuple[str, bool]]:
    """(texto_decodificado, es_html) por cada parte text/* hoja del PADRE.

    NO desciende en message/rfc822 (eso es la Parte 1). policy.default decodifica
    QP/base64 + charset en get_content()."""
    msg = _parse_message(raw)
    for parte in _iter_partes_hoja(msg):                 # helper de la Parte 1
        if parte.get_content_type() == "message/rfc822":
            continue
        if parte.get_content_maintype() != "text":
            continue
        try:
            texto = parte.get_content()
        except Exception:
            continue
        yield texto, parte.get_content_subtype() == "html"


def extract_drive_links(raw: bytes) -> list[DriveLink]:
    """Enlaces Drive/Gmail del cuerpo del padre, clasificados y deduplicados.

    Para HTML, marca si el enlace proviene de <img src> (candidato a firma) o de
    <a href> (adjunto-real-por-enlace). Desescapa entidades y limpia la URL antes
    de clasificar."""
    ...   # regex por familia (reusar _DRIVE_FOLDER_RE de intake_drive + nuevas),
          # unescape(), strip de <>/espacios/soft-breaks, dedup por (type, file_id)
```

Helpers de clasificación (`_classify_url(url) -> (DriveLinkType, file_id)`) y de
limpieza viven aquí. Los regex de fichero/hoja/descarga se añaden junto al
`_DRIVE_FOLDER_RE` ya existente en `intake_drive` (o se centralizan en un módulo
compartido si crecen).

## 6. Cambios — capa glue (resolución vía Drive REST)

Extender `core/intake_drive.py` con helpers a nivel de **fichero**, reutilizando
`_get_drive_access_token()` (token `gdrive_ev`, refresh + rate-limit ya resueltos). NO
usar subprocess de rclone por fichero (demasiado grueso); usar Drive REST v3 igual que
`get_drive_folder_info`.

```python
@dataclass
class DriveFileInfo:
    file_id: str
    name: str
    mime_type: str
    size: int | None
    md5: str | None
    modified_time: str | None
    drive_id: str | None


def get_drive_file_info(file_id: str) -> DriveFileInfo | None:
    """files.get?fields=id,name,mimeType,size,md5Checksum,modifiedTime,driveId
    &supportsAllDrives=true. None si 401/404/permiso/red (degradación limpia)."""
    ...


def download_drive_media(file_id: str) -> bytes | None:
    """files.get?alt=media&supportsAllDrives=true → bytes. Solo binarios; un doc
    nativo devuelve error (no se llama para natives). None si falla."""
    ...
```

Orquestación (en `email_export.py`, nueva función `_resuelve_enlaces`):

1. `extract_drive_links(raw_bytes)`.
2. Por enlace, según `type`:
   - `FOLDER` → `report` + traza `skipped_folder`. No bajar.
   - `NATIVE` → traza `skipped_native`. No capturar.
   - `IMAGE_SIG` → filtrar (sin traza o nota mínima).
   - `FILE` → `get_drive_file_info`; si `mime_type` es imagen y cumple el filtro de
     firma → filtrar. Si no:
     - `download_drive_media` → verificar `md5` contra `md5Checksum`.
     - **Sniff `.eml`**: `mime_type == "message/rfc822"`, nombre `.eml`, o cabeza de
       bytes con cabeceras RFC822 → tratar como mensaje: `existing_message_ids` +
       `_escribe_mensaje` a primer nivel de `03_Email` + `_aplana_anidados` (Parte 1).
       Dedup por `Message-ID`.
     - **Otro binario** → depositar en subcarpeta por-padre
       `AAAA-MM-DD_asunto/_enlaces/` con nombre canónico desde `name` + fecha; dedup
       por SHA-256 vía `IntakeManifest.register(..., source="drive_link")`.
   - `GMAIL` → *(si se confirma)* `messages().get(format="raw")` y reentra Parte 1.
3. Índice de resolución `_resolved_links.json` (por `drive_file_id` → `md5`/`returncode`)
   para idempotencia con reintento de fallos.

**Por qué subcarpeta y no primer nivel.** Los binarios rescatados NO son correos: no
deben aparecer en `CRONOLOGIA.md` (que solo escanea `*.eml`). Van como
adjuntos-por-referencia en una subcarpeta del padre, igual que los adjuntos extraídos.
Los `.eml` rescatados sí van a primer nivel (son correos).

## 7. Enganche en `export_label`

```python
def export_label(..., resolve_drive_links: bool = True) -> ExportReport:
    ...
    # tras report.written += 1; nuevos_gids.append(gid); y tras _aplana_anidados:
    if resolve_drive_links:
        _resuelve_enlaces(dest, raw_bytes, parent_mid=mid, vistos=vistos,
                          index=link_index, procedencia=procedencia, report=report)
```

`ExportReport` — contadores nuevos: `links_resolved`, `links_skipped_folder`,
`links_skipped_native`, `links_filtered_sig`, `links_manual` (permiso/expiración),
`links_error`. Añadir a `resumen()`.

## 8. Cambios — `scripts/export_label_emails.py`

```python
parser.add_argument("--no-resolver-enlaces", dest="resolver_enlaces",
                    action="store_false", default=True,
                    help="No rescatar ficheros enlazados a Drive/Gmail en el cuerpo "
                         "(por defecto SÍ se rescatan los binarios de descarga directa).")
...
report = export_label(..., resolve_drive_links=args.resolver_enlaces)
```

## 9. Traza forense

Añadir el evento `upload_drive_link` a `INTAKE_EVENTS` (`core/intake_log.py`) y
documentar su `details` en `project_intake_estructura_v2.md`. Un evento por corrida con
una entrada por enlace, recogiendo **también los no resueltos** (worklist manual):

```json
{
  "event": "upload_drive_link",
  "details": {
    "account": "...", "label": "...",
    "enlaces": [
      {"parent_message_id": "...", "raw_url": "...", "type": "file",
       "drive_file_id": "...", "outcome": "resolved",
       "sha256": "...", "path": "03_Email/.../_enlaces/2025-07-23_offer.pdf",
       "md5_ok": true},
      {"...": "outcome ∈ {resolved, skipped_folder, skipped_native, "
       "filtered_signature, manual_permission, error}, con reason si aplica"}
    ]
  }
}
```

Los binarios depositados se registran además en `IntakeManifest`
(`source="drive_link"`, SHA-256), igual que los adjuntos de la Parte 1. La traza de
`.eml` rescatados es la de la Parte 1 (`upload_email` + `forwarded_in` si procede).

## 10. Tests — `tests/test_email_export.py`

Capa pura (sin red):

- `extract_drive_links`: cuerpo HTML con URLs en QP → desescapa, limpia y clasifica
  carpeta/hoja/fichero/`uc?export=download`; deduplica por `(tipo, id)`.
- Distinción `<a href>` vs `<img src>` → `from_img`.
- Filtro de firma: misma imagen (mismo `file_id`) repetida en N correos → filtrada.
- Sniff `.eml`: bytes con cabeceras RFC822 → enruta a la vía de la Parte 1.
- Clasificación: `/spreadsheets/d/` → NATIVE (no se descarga); `/drive/folders/` →
  FOLDER (no se descarga).

Glue (con servicio/HTTP inyectado, como el `_FakeService` existente):

- `FILE` binario → descarga, verifica `md5`, deposita en `_enlaces/`, `links_resolved==1`.
- `md5` no coincide → no deposita, `links_error`, aviso en `report.errors`.
- `FILE` que es `.eml` → primer nivel, dedup por `Message-ID`, aplanado de anidados.
- `FOLDER`/`NATIVE` → no descarga, contador y traza correctos.
- Permiso denegado (403) → `links_manual`, NO se marca definitivo en `_resolved_links.json`
  (reintento en la siguiente corrida).
- Idempotencia: segunda corrida con `file_id` ya resuelto → no rebaja.
- Evento `upload_drive_link` con una entrada por enlace, incluidos los no resueltos.

## 11. Verificación y cierre

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m pytest -q tests/test_email_export.py
python -m pytest -q --tb=no            # suite completa sigue verde
```

Antes de la corrida real: **verificar el scope del token `gdrive_ev`** (§3).

Validación contra datos reales de W-02VND1 (`00_Input/03_Email`): los fixtures
`2026-06-05_hoja_de_calculo_compartida_*` (NATIVE → no se captura, solo nota) y
`2026-05-19_share_request_for_inmueble_*` (FOLDER → no se baja, solo nota) ejercen
las dos ramas de "no descargar". Localizar además un correo con un enlace `/file/d/`
o `uc?export=download` de descarga directa para validar el rescate byte-fiel y el
filtro de firma. Comprobar en la traza que los no resueltos quedan como worklist.

```powershell
python -m scripts.export_label_emails --ref W-02VND1 `
  --account nikolai.tyukhay@engelvoelkers.com `
  --label "01. CONTING/01. EXTRAJUD/01. BARCELONA/BaRS1 - [inmueble] - (W-02VND1)" `
  --extraer-adjuntos --force
```

Al cerrar: dejar `PLAN.md`/`STATUS.md` al día con el hash del commit y anotar en
`docs/MEJORAS_FUTURAS.md` lo que quede fuera (resolución de permalinks Gmail si no se
confirma en esta entrega; volcado opcional de carpetas si en el futuro se decide).

## 12. Fuera de alcance

- Volcado de **carpetas** enlazadas (decisión 2.1: no se bajan).
- Captura de **documentos nativos** de Google (decisión 2.2: no se captura nada).
- Reescritura del enlace en el cuerpo del `.eml` (el original se conserva intacto; la
  resolución solo **añade** ficheros, nunca modifica el correo).
