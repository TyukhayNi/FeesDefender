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

#: **Bit «Name Surrogate» de un reparse tag.** Microsoft lo define así: cuando está
#: puesto, el reparse point *nombra otra entidad* — es decir, **redirige**. Cuando no,
#: el tag modifica el contenido sin cambiar de sitio, que es la familia de la nube.
#:
#: Esto sustituye a la lista de dos valores, y el cambio lo pide la R1 (su H-08): «solo
#: dos tags redirigen» no era una clasificación, era una enumeración, y un tag no
#: enumerado **no queda probado inocuo**. Ahora la política se expresa por la propiedad
#: que importa y la lista de arriba queda como los dos casos que además se conocen por
#: su nombre. https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-tags
_BIT_NAME_SURROGATE = 0x20000000

#: Cota de la cadena de ancestros. Si se agota, se **falla cerrado**: una cadena que no
#: se pudo recorrer entera no está limpia, solo sin comprobar.
_MAX_ANCESTROS = 64


class SedeError(Exception):
    """No hay sede utilizable, o la ruta pedida no es legítima. Falla CERRADO."""


def drive_accesible() -> bool:
    """¿Se puede confiar HOY en el estado compartido del canon? (spec dual §7.2.9-10)

    **Una sola condición y explícita:** ``FEESDEFENDER_OFFLINE=1``, el control del
    operador — «estoy sin la unidad del despacho, trabaja contra mi checkout». Es la
    declaración que el §7.1.5 pide para retirar las capacidades de canon.

    **Lo que NO se hace, porque `sala_maquina` ya lo midió y hubo que retirarlo:** añadir
    «…o la raíz del catálogo no está montada». Suena más listo y es peor — divergencia de
    fuente de verdad con `case_locator._root()`, y falso negativo en cualquier clon o
    worktree sin `CASOS_ROOT`, donde **toda** invocación se iría a offline en silencio.

    **Duplicación declarada:** `scripts/sala_maquina.py::_drive_accesible` decide lo mismo
    con la misma condición. Unificarlas exige tocar un módulo ya revisado y mergeado, así
    que aquí se **fija con un test de no-drift** (`test_procedimiento_sede.py`) en vez de
    dejarlas divergir en silencio. Promoverla a un sitio común es tarea aparte
    (`MEJORAS #190`).

    Pasar `True` a pelo al resolver es exactamente lo que dejó muerta la rama offline
    entera en `sala_maquina` hasta su Task 10: el modo existía, tenía tests unitarios y
    ningún entrypoint podía llegar a él.
    """
    return (os.getenv("FEESDEFENDER_OFFLINE") or "").strip() != "1"


def registro_legible(raiz_registro) -> None:
    """Comprueba que el registro de workspaces se puede leer, **sin provocar escrituras**.

    `WorkspaceRegistry._leer` pone en **cuarentena** un JSON ilegible: lo renombra a
    ``<fichero>.corrupto.<fecha>`` con `os.replace` antes de lanzar. Para su módulo eso es
    correcto —preserva la evidencia y no borra— pero significa que **una lectura de 4a
    puede provocar una escritura**, y la R1 lo demostró (su H-05). Esta mitad no escribe,
    así que se mira antes: si algo no se puede leer, se falla aquí, con un mensaje que
    dice qué pasa y qué hacer, en vez de dejar que el rename ocurra por sorpresa.

    Solo `*.json`, que es lo que el registro lee: los lockfiles de D2 viven en la misma
    raíz y no son entradas.

    **Lo que esta comprobación NO cierra, y se declara:** entre esta lectura y la del
    resolver hay una ventana. Si el fichero se corrompe justo ahí, la cuarentena ocurre.
    Cerrarla de verdad exige un modo de lectura no mutante en `WorkspaceRegistry`, que es
    su módulo y no el mío (`MEJORAS #208`).
    """
    import json

    raiz = Path(raiz_registro)
    if not raiz.is_dir():
        return
    for fichero in sorted(raiz.glob("*.json")):
        try:
            crudo = json.loads(fichero.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SedeError(
                f"el registro de workspaces tiene un fichero ilegible: {fichero.name} "
                f"({type(exc).__name__}). Esta vista no lo toca —leerlo con el registro "
                f"lo pondría en cuarentena, y esta mitad no escribe—: revísalo o "
                f"retíralo tú") from exc
        except OSError as exc:
            raise SedeError(
                f"no se pudo leer {fichero.name} del registro de workspaces: "
                f"{exc.strerror}") from exc
        if not isinstance(crudo, list):
            raise SedeError(
                f"el registro de workspaces tiene un fichero con forma inesperada: "
                f"{fichero.name} no contiene una lista. Revísalo o retíralo tú")


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
    # **La cadena se inspecciona sobre la ruta TAL COMO VIENE, antes de resolverla.**
    # `resolve()` sigue la junction, así que resolver primero borra la redirección que se
    # busca. La R1 lo señaló (su H-07): el test del ancestro llamaba a `contener(enlace,…)`
    # directamente, mientras la secuencia de producción `contener(raiz_autorizada(ws), …)`
    # ya había borrado el enlace. Aquí es donde tiene que estar la comprobación, porque
    # aquí es donde la ruta entra por primera vez.
    if not _cadena_limpia(Path(raiz)):
        raise SedeError(
            f"se llega a la raíz de trabajo a través de algo que redirige: {raiz}. La "
            f"autorización no cubre un desvío del sistema de ficheros")
    return Path(raiz).resolve()


def _redirige(p: Path) -> bool:
    """``True`` si este componente redirige a otro sitio, **o si no se pudo saber**.

    Falla **cerrado** en dos casos que la R1 señaló como aperturas silenciosas (su H-08):

    * un ``OSError`` de ``lstat`` que **no** sea «no existe» — un permiso denegado, un
      volumen que no responde — no es «no redirige», es «no lo sé», y no se le da el
      beneficio de la duda;
    * un tag con el bit **Name Surrogate** puesto, aunque no esté en la lista de dos.
      Ese bit significa, por definición de Microsoft, que el reparse point *nombra otra
      entidad*: redirige. Un tag no enumerado no queda probado inocuo.

    Lo que sigue pasando, y es el punto de todo esto: un placeholder de nube
    (``IO_REPARSE_TAG_CLOUD*``) **no** lleva ese bit, así que no veta. Sin esa distinción
    la vista no podría leer un solo expediente de ``G:``.
    """
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        return False                    # no existe: no puede redirigir
    except OSError as exc:
        raise SedeError(
            f"no se pudo inspeccionar {p} para saber si redirige ({exc.strerror}): "
            f"«no lo sé» no es «no redirige»") from exc
    if stat.S_ISLNK(st.st_mode):
        return True
    tag = getattr(st, "st_reparse_tag", 0)
    return tag in TAGS_QUE_REDIRIGEN or bool(tag & _BIT_NAME_SURROGATE)


def _cadena_limpia(raiz: Path) -> bool:
    """La raíz y sus ancestros no redirigen. Se comprueba una vez, no por ruta.

    Si se agota la cota **devuelve `False`**: una cadena que no se pudo recorrer entera no
    está limpia, solo sin comprobar. Devolver `True` ahí era la tercera apertura silenciosa
    de la R1/H-08.
    """
    p = raiz
    for _ in range(_MAX_ANCESTROS):
        if _redirige(p):
            return False
        if p.parent == p:
            return True
        p = p.parent
    return False


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
