"""De dónde viene la autoridad, y qué rutas son legítimas (invariantes I0 e I3).

**I0 — la autoridad la da el resolver del workspace, no el catálogo.** El mutex del caso
(``MEJORAS #126``) impide que otro proceso de ESTA máquina entre a la vez; no dice nada
sobre si el caso está prestado a OTRA. Eso lo dice el modo del workspace, y la raíz de
trabajo es ``ws.working_root`` — nunca una ruta que resolvamos nosotros. ``sala_maquina``
ya pasó por aquí y su docstring lo cuenta: «antes esto resolvía una ruta y escribía sin
preguntar a nadie».

**I3 — la raíz se identifica PRIMERO y no se re-deriva de la ruta que se juzga.** Una
comprobación del estilo ``destino.resolve().relative_to((base / "x").resolve())`` se
aprueba a sí misma cuando ``x`` es una junction: los dos lados resuelven al mismo sitio
ajeno. Aquí la ruta se CONSTRUYE desde la raíz, componente a componente.

Y el orden importa dentro de :func:`contener`: la cadena de la raíz se inspecciona **antes**
de ``resolve()``, porque ``resolve()`` sigue la junction y borra la redirección que se busca.
Lo destapó el test del ancestro: con la comprobación después, no levantaba nada.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

from core.casos.workspace_model import Capability, CapabilityDenied

#: Los DOS tags que redirigen una ruta a otro sitio. No se veta ningún otro, y eso es
#: deliberado: un placeholder de Drive Stream o de OneDrive también trae
#: ``st_reparse_tag`` (``IO_REPARSE_TAG_CLOUD*``) y **no redirige nada** — virtualiza el
#: contenido. Vetar «cualquier tag distinto de cero» dejaría la vista incapaz de leer los
#: expedientes reales, que viven precisamente en ``G:``.
TAGS_QUE_REDIRIGEN: frozenset[int] = frozenset({
    getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),   # junction
    getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),       # symlink
})

#: Cota de la cadena de ancestros: una ruta patológica no debe colgar el proceso.
_MAX_ANCESTROS = 64


class SedeError(Exception):
    """No hay sede utilizable, o la ruta pedida no es legítima. Falla CERRADO."""


def raiz_autorizada(ws) -> Path:
    """Raíz de trabajo del caso, **resuelta una vez**, tras exigir ``READ_CASE``.

    Se exige la capacidad ANTES de devolver la ruta: al revés, el llamador tendría la
    ruta en la mano y la autorización sería decorativa.
    """
    try:
        ws.exigir(Capability.READ_CASE)
    except CapabilityDenied as exc:
        raise SedeError(f"este workspace no autoriza `read_case`: {exc}") from exc
    raiz = getattr(ws, "working_root", None)
    if raiz is None:
        raise SedeError(
            "el workspace no tiene raíz de trabajo (modo bloqueado o sin copia local): "
            "no hay nada que leer, y no se sustituye por la cwd")
    return Path(raiz).resolve()


def _redirige(p: Path) -> bool:
    """``True`` si este componente concreto redirige a otro sitio."""
    try:
        st = os.lstat(p)
    except OSError:
        return False                    # no existe: no puede redirigir
    if stat.S_ISLNK(st.st_mode):
        return True
    return getattr(st, "st_reparse_tag", 0) in TAGS_QUE_REDIRIGEN


def _cadena_limpia(raiz: Path) -> bool:
    """La raíz y sus ancestros no redirigen. Se comprueba una vez, no por ruta."""
    p = raiz
    for _ in range(_MAX_ANCESTROS):
        if _redirige(p):
            return False
        if p.parent == p:
            return True
        p = p.parent
    return True


def contener(raiz: Path, *partes: str) -> Path:
    """Ruta bajo ``raiz``, verificando que ningún componente de la cadena redirige.

    ``raiz`` entra **ya identificada** (de :func:`raiz_autorizada`). Las ``partes`` son
    relativas y no pueden salir: ni ``..``, ni absoluta, ni UNC.
    """
    # La cadena se inspecciona ANTES de resolver, y el orden es el contrato: `resolve()`
    # SIGUE la junction, así que resolver primero borra justo la redirección que se busca.
    # Medido con una junction real: `contener(<via junction>, "05_Procedimiento")` no
    # levantaba nada porque la raíz ya había pasado a ser el destino real.
    if not _cadena_limpia(Path(raiz)):
        raise SedeError(
            f"se llega a la raíz autorizada a través de algo que redirige: {raiz}")
    raiz = Path(raiz).resolve()
    if not _cadena_limpia(raiz):
        raise SedeError(f"la propia raíz autorizada redirige a otro sitio: {raiz}")

    crudas = [str(x).replace("\\", "/") for x in partes if str(x)]
    if any(c.startswith("//") for c in crudas):
        raise SedeError(f"ruta UNC no admitida: {crudas!r}")
    rel = PurePosixPath(*crudas) if crudas else PurePosixPath("")
    if rel.is_absolute() or PureWindowsPath(str(rel)).is_absolute():
        raise SedeError(f"la parte pedida es absoluta y no relativa a la raíz: {rel}")
    if any(seg in ("..", "") for seg in rel.parts):
        raise SedeError(f"la ruta intenta salir de la raíz: {rel}")

    destino = raiz
    for seg in rel.parts:
        destino = destino / seg
        if _redirige(destino):
            raise SedeError(
                f"un componente de la ruta redirige a otro sitio y no se sigue: "
                f"{destino}. Si es legítimo, resuélvelo fuera de la vista")

    # Comparación final SIN volver a resolver la raíz desde el destino: la raíz manda.
    try:
        destino.resolve().relative_to(raiz)
    except ValueError as exc:
        raise SedeError(f"{destino} no cae bajo la raíz autorizada {raiz}") from exc
    return destino
