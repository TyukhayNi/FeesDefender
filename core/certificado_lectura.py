"""Lectura del certificado de Codicert: quién lo firma y dónde acaba el acta.

Vive fuera de `core/expedicion_certificada.py` porque **F3 lo va a reutilizar
entero**: el aportable del spec §7.3 recorta la reproducción y necesita exactamente
el mismo discriminante de acta. Aquí nace con lo que F2 usa —el emisor— y con el
mapa de páginas ya dentro, para que F3 no lo reescriba.

Anatomía medida el 2026-09-21 sobre tres certificados reales de producción
(`006catetonk`, `006catfpdv6`, `006cdgfj5no`) y el 2026-09-17 sobre `006casm113n`.
Detalle en el plan `docs/superpowers/plans/2026-09-21-codicert-f2.md`, mediciones
M-3, M-4 y M-6.
"""
from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass

#: Razón social del emisor esperado. Es el cliente del proyecto (`CLAUDE.md`
#: §Usuarios) y aparece así, literal, en los cuatro certificados medidos. Es un
#: DEFAULT, no una constante cerrada: `cosechar` la recibe por parámetro para que un
#: emisor distinto no obligue a tocar el core.
EMISOR_ESPERADO = "EV MMC SPAIN, S.L.U."

#: El acta lleva esta frase en la cabecera de cada una de sus páginas; la
#: reproducción del documento, no. Medido en los cuatro certificados, burofax y
#: entrega electrónica.
_MARCA_ACTA = "sello temporal"

_RE_RAZON = re.compile(
    r"1\.\s*Datos del emisor\.(?P<bloque>.*?)2\.\s*Datos del receptor\.", re.S)
_RE_NOMBRE = re.compile(r"Raz[óo]n social:\s*(?P<valor>.+)")
#: `[\w-]+(?:\.[\w-]+)*` captura `madrid.bd` entero y deja fuera el punto de la
#: frase, que en el literal va pegado al login: «...con nombre de usuario madrid.bd.»
_RE_USUARIO = re.compile(r"con nombre de usuario\s+(?P<valor>[\w-]+(?:\.[\w-]+)*)")


class CertificadoIlegibleError(RuntimeError):
    """El PDF no tiene la estructura de un certificado de Codicert."""


@dataclass(frozen=True)
class EmisorCertificado:
    """Las dos identificaciones del remitente que trae el certificado (M-4).

    `razon_social` es la persona jurídica que aparece bajo «1. Datos del emisor» —
    idéntica en las siete plazas— y `usuario` es la cuenta que cursó el envío, que
    el bloque «CERTIFICADO» nombra («con nombre de usuario madrid.bd»). Son dos
    hechos distintos: el primero acredita de quién sale la comunicación a efectos
    del art. 17.2; el segundo, por qué Market Center salió.
    """

    razon_social: str
    usuario: str | None


def _sin_ligaduras(texto: str) -> str:
    """Deshace las ligaduras tipográficas que el extractor devuelve tal cual.

    `pypdf` saca «certiﬁcado» con U+FB01 en vez de «fi», y los rótulos que este
    módulo busca —«Datos del emisor», «Razón social»— no las llevan, pero el texto
    que los rodea sí. Se normalizan las cinco de la tabla, no solo la `fi`, porque
    deshacer un encoding no es una tabla de un caso.
    """
    for ligada, llana in (("ﬁ", "fi"), ("ﬂ", "fl"), ("ﬀ", "ff"),
                          ("ﬃ", "ffi"), ("ﬄ", "ffl")):
        texto = texto.replace(ligada, llana)
    return texto


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y sin puntuación, para comparar razones sociales.

    «EV MMC SPAIN, S.L.U.» y «Ev Mmc Spain SLU» son la misma sociedad y ninguna
    comparación literal las junta.
    """
    plano = unicodedata.normalize("NFKD", _sin_ligaduras(texto))
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", plano).lower().split())


def emisor_de_texto(texto: str) -> EmisorCertificado:
    """El emisor, leído SOLO del bloque acotado del acta.

    ⚠️ **No se busca la razón social en todo el documento, y esa es la decisión que
    hace útil a esta función.** Medido el 2026-09-21: `EV MMC SPAIN` aparece nueve
    veces en un certificado real y una sola en el bloque del emisor — las otras ocho
    están en la reproducción de nuestro propio requerimiento. Una búsqueda global
    daría «emisor correcto» sobre el certificado de otro remitente que nos mencione,
    y el control del art. 17.2 sería inerte: no podría dar el otro valor.
    """
    plano = _sin_ligaduras(texto)
    bloque = _RE_RAZON.search(plano)
    if not bloque:
        raise CertificadoIlegibleError(
            "no se encuentra el bloque «1. Datos del emisor. … 2. Datos del "
            "receptor.» en la primera página: esto no tiene la estructura de un "
            "certificado de Codicert, o el PDF no da texto extraíble. No se "
            "verifica el remitente por otra vía: se para.")
    nombre = _RE_NOMBRE.search(bloque.group("bloque"))
    if not nombre:
        raise CertificadoIlegibleError(
            "el bloque «Datos del emisor» no trae «Razón social:»")
    usuario = _RE_USUARIO.search(plano)
    return EmisorCertificado(razon_social=nombre.group("valor").strip(),
                             usuario=usuario.group("valor") if usuario else None)


def leer_emisor(pdf: bytes) -> EmisorCertificado:
    """`emisor_de_texto` sobre el PDF: página 1 para el bloque, todo para el usuario.

    El bloque del emisor está siempre en la página 1 (medido en los cuatro), pero el
    párrafo «CERTIFICADO … con nombre de usuario X» puede caer en la 1 o más abajo
    dentro del acta, según cuántas incidencias traiga el histórico (M-6). Por eso el
    usuario se busca en el documento entero y la razón social no.
    """
    from pypdf import PdfReader

    try:
        lector = PdfReader(io.BytesIO(pdf))
        primera = lector.pages[0].extract_text() or ""
        todo = "\n".join((p.extract_text() or "") for p in lector.pages)
    except CertificadoIlegibleError:
        raise
    except Exception as exc:  # noqa: BLE001 — pypdf lanza de todo ante un PDF roto
        raise CertificadoIlegibleError(
            f"no se puede abrir el certificado como PDF "
            f"({type(exc).__name__}: {exc})") from exc
    emisor = emisor_de_texto(primera)
    if emisor.usuario is None:
        usuario = _RE_USUARIO.search(_sin_ligaduras(todo))
        emisor = EmisorCertificado(emisor.razon_social,
                                   usuario.group("valor") if usuario else None)
    return emisor


def es_emisor_esperado(emisor: EmisorCertificado, *, razon_social: str,
                       usuario: str | None = None) -> bool:
    """¿El certificado lo firmó quien debía? (art. 17.2, spec §6.2 y §7.1).

    `usuario=None` comprueba solo la persona jurídica. Pasarlo comprueba además la
    cuenta emisora, que es lo que acredita el Market Center: un certificado del que
    no se puede leer el usuario NO pasa esa comprobación — ausencia no es
    coincidencia.
    """
    if _normalizar(emisor.razon_social) != _normalizar(razon_social):
        return False
    if usuario is None:
        return True
    return (emisor.usuario is not None
            and _normalizar(emisor.usuario) == _normalizar(usuario))


def paginas_de_acta_de_textos(textos: list[str] | tuple[str, ...]) -> tuple[int, ...]:
    """Números de página (base 1) que pertenecen al ACTA, no a la reproducción.

    Medido en cuatro certificados: acta 1-4 de 8, 1-6 de 10, 1-5 de 9 y 1-4 de 6.
    **El acta no mide siempre lo mismo ni siquiera dentro del burofax**: crece con el
    histórico de incidencias, así que no hay número fijo que valga y hace falta el
    discriminante.
    """
    return tuple(i + 1 for i, t in enumerate(textos)
                 if _MARCA_ACTA in _sin_ligaduras(t or ""))


def paginas_de_acta(pdf: bytes) -> tuple[int, ...]:
    """`paginas_de_acta_de_textos` sobre el PDF."""
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(pdf))
    return paginas_de_acta_de_textos([p.extract_text() or "" for p in lector.pages])
