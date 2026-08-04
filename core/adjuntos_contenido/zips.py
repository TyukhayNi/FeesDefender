"""Contenido de un adjunto `.zip`: export de WhatsApp o archivo genérico (`MEJORAS #55.1`).

Hasta el 2026-08-04 el router excluía los `.zip` en bloque (`_EXT_OMITIDO`) y la sala de
máquina los mandaba a `sin_soporte`. En la muestra de `MEJORAS #87` eran **8 de 15** adjuntos
únicos: la mayoría del corpus, sin una línea de contenido.

**Enrutado por tipo, no descompresión genérica.** Es la primera exigencia de `#55.1`: un
export de WhatsApp descomprimido a pelo deja el `_chat.txt` suelto y los media huérfanos,
perdiendo lo que `core/whatsapp_intake` sabe hacer. Se pregunta primero si trae un chat
parseable y solo si no, se descomprime.

La detección es **más estricta** que `whatsapp_intake._find_chat_txt`, que cae a «cualquier
`.txt`»: aquí un zip es un export solo si `parse_chat` saca al menos un mensaje. Sin eso, un
zip con un único `.txt` cualquiera se clasificaría como conversación de WhatsApp.

**Lo que este módulo NO hace, y es deliberado: fundir exports.** `#55.1` avisa de que si
cinco correos traen cinco copias del mismo chat y algo las funde, el mismo mensaje se cuenta
cinco veces, y para una cronología probatoria eso es peor que no tenerla. Aquí el contenido
es **por adjunto**: cinco copias son cinco documentos, cada uno fiel al suyo. Lo que se añade
es que el solape sea **visible** (`huella`), que es lo que `#55.1` dice que hoy no guarda
nadie. La reconciliación entre exports sigue sin construirse.
"""

from __future__ import annotations

import hashlib
import mimetypes
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from core.intake_utils import safe_zip_members
from core.whatsapp_export import parse_chat, referencias_adjuntos

#: Tope de miembros que se abren de un zip genérico. Un recorte SIEMPRE se declara en la
#: nota: un zip recortado en silencio es contexto ausente y sin declarar, que es la clase
#: de defecto que `MEJORAS #90` costó tres semanas.
MAX_MIEMBROS = 20

#: Miembro por encima de esto: se lista con su tamaño y no se extrae.
MAX_BYTES_MIEMBRO = 20 * 1024 * 1024

#: Contenedores que NO se abren dentro de un zip: profundidad 1. Sin tope, un zip anidado
#: es una bomba de descompresión.
_EXT_ANIDADAS = {".zip", ".emz", ".7z", ".rar", ".gz", ".tar"}


@dataclass
class MiembroZip:
    nombre: str
    bytes_: int
    texto: str = ""
    metodo: str = ""
    nota: str = ""


@dataclass
class ContenidoZip:
    clase: str                      # whatsapp | generico | ilegible
    texto: str = ""
    nota: str = ""
    # --- solo whatsapp
    n_mensajes: int = 0
    rango: str = ""
    media_faltante: list[str] = field(default_factory=list)
    huella: str = ""
    # --- solo generico
    miembros: list[MiembroZip] = field(default_factory=list)


def huella_chat(msgs: list) -> str:
    """Identidad del CHAT (no del zip), a partir de su primer mensaje.

    Un export de WhatsApp arranca desde el principio de la conversación, así que dos
    exports del mismo chat comparten primer mensaje aunque tengan distinto número de
    mensajes, distinto nombre de fichero y, por tanto, **distinto sha256**. Ese es
    exactamente el caso que `whatsapp_intake` no puede deduplicar: su dedup es por hash
    del zip.

    Límite declarado: si un export viene recortado por fecha —WhatsApp no lo hace por
    defecto, pero un reenvío manual sí— su primer mensaje no es el del chat y la huella no
    coincidirá. Es un falso negativo (dos copias parecerán chats distintos), nunca un falso
    positivo, que sería el error caro.
    """
    if not msgs:
        return ""
    m = msgs[0]
    ts = m.timestamp.isoformat() if getattr(m, "timestamp", None) else ""
    crudo = f"{ts}|{getattr(m, 'autor', '') or ''}|{(getattr(m, 'texto', '') or '')[:200]}"
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:16]


def _extraer_miembro(nombre: str, data: bytes) -> MiembroZip:
    """Un miembro del zip por el MISMO router que los adjuntos sueltos."""
    ext = Path(nombre).suffix.lower()
    if ext in _EXT_ANIDADAS:
        return MiembroZip(nombre, len(data), "", "omitido",
                          "archivo anidado: se lista, no se abre (profundidad 1)")
    if len(data) > MAX_BYTES_MIEMBRO:
        return MiembroZip(nombre, len(data), "", "omitido",
                          f"demasiado grande ({len(data) // 1024} KB): no se extrae")

    # Import perezoso: `router` importa este módulo para el despacho del `.zip`.
    from . import router

    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / Path(nombre).name
        destino.write_bytes(data)
        mime = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
        try:
            ext_res = router.extraer(destino, mime)
        except Exception as exc:  # noqa: BLE001 — un miembro no tumba el zip
            return MiembroZip(nombre, len(data), "", "error", f"{type(exc).__name__}: {exc}")
    return MiembroZip(nombre, len(data), ext_res.texto, ext_res.metodo, ext_res.motivo)


def extraer_zip(ruta: Path) -> ContenidoZip:
    """Contenido de un `.zip`. Nunca lanza: un zip ilegible se declara."""
    try:
        miembros = safe_zip_members(Path(ruta).read_bytes())
    except Exception as exc:  # noqa: BLE001 — corrupto, cifrado, no-zip…
        return ContenidoZip(clase="ilegible",
                            nota=f"zip ilegible ({type(exc).__name__}: {exc})")

    if not miembros:
        return ContenidoZip(clase="ilegible", nota="zip sin miembros legibles")

    wa = _como_whatsapp(miembros)
    if wa is not None:
        return wa
    return _como_generico(miembros)


def _como_whatsapp(miembros: dict[str, bytes]) -> ContenidoZip | None:
    """Devuelve el contenido si es un export de WhatsApp; `None` si no lo es."""
    candidatos = ["_chat.txt"] if "_chat.txt" in miembros else sorted(
        n for n in miembros if n.lower().endswith(".txt"))
    for nombre in candidatos:
        texto = miembros[nombre].decode("utf-8", errors="replace")
        msgs = parse_chat(texto)
        if not msgs:
            continue                       # un .txt cualquiera NO es una conversación
        presentes = {n for n in miembros if n != nombre}
        refs = referencias_adjuntos(msgs)
        ts = [m.timestamp for m in msgs if getattr(m, "timestamp", None)]
        rango = f"{min(ts):%Y-%m-%d} → {max(ts):%Y-%m-%d}" if ts else ""
        return ContenidoZip(
            clase="whatsapp", texto=texto, n_mensajes=len(msgs), rango=rango,
            media_faltante=[r for r in refs if r not in presentes],
            huella=huella_chat(msgs),
            nota=(f"export de WhatsApp: {len(msgs)} mensajes"
                  + (f", {rango}" if rango else "")
                  + f", {len(presentes)} fichero(s) de media en el zip"),
        )
    return None


def _como_generico(miembros: dict[str, bytes]) -> ContenidoZip:
    total = len(miembros)
    nombres = sorted(miembros)[:MAX_MIEMBROS]
    out = ContenidoZip(clase="generico")
    if total > len(nombres):
        out.nota = (f"zip con {total} miembros; se han abierto los {len(nombres)} "
                    f"primeros por orden alfabético (tope MAX_MIEMBROS)")
    for nombre in nombres:
        out.miembros.append(_extraer_miembro(nombre, miembros[nombre]))

    partes: list[str] = []
    for m in out.miembros:
        cuerpo = m.texto.strip() if m.texto.strip() else f"_(sin texto: {m.nota or m.metodo})_"
        partes.append(f"### {m.nombre}\n\n{cuerpo}")
    out.texto = "\n\n".join(partes)
    return out
