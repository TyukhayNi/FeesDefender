"""Carga y validación de `05_Procedimiento/_mapa_procesal.yaml` (spec §3).

El mapa lo escribe el LETRADO: es la única fuente de la asignación documento → carpeta.
La vista **no** propone la carpeta (spec §0); sí propone ``orden`` y ``descripción``, y eso
vive en :mod:`core.procedimiento.borrador`.

Que esta mitad no escriba no rebaja la validación: la adelanta. Todo lo que se acepte aquí
acabará, en 4b, siendo una escritura en el expediente real.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from .carpetas import CARPETAS_FASE, es_carpeta_fase

MAPA_FILENAME = "_mapa_procesal.yaml"
VERSION_SOPORTADA = 1

ORIGEN_CRM = "crm"
ORIGEN_DESPACHO = "despacho"
ORIGENES = (ORIGEN_CRM, ORIGEN_DESPACHO)

#: Gramática de ``orden``. Cubre ``00``, ``01``, ``D-01``, ``D-02A``, ``DA-9``; y NADA
#: más — porque este valor se incrusta en un nombre de fichero. La rev. 1 no lo validaba
#: y ``orden: ../00`` producía un destino fuera de la carpeta de fase.
#:
#: Se casa con ``fullmatch`` y no con ``match``: en Python, ``$`` casa **también justo
#: antes de un salto de línea final**, así que ``match`` aceptaba un ``orden`` terminado
#: en salto de línea y metía un carácter de control en el nombre del fichero (R1/H-13).
_RE_ORDEN = re.compile(r"[A-Z]{0,2}-?\d{1,3}[A-Z]?")

#: Caracteres que Windows no admite en un nombre de fichero.
_PROHIBIDOS = set('<>:"/\\|?*') | {chr(c) for c in range(32)}

#: Nombres de dispositivo reservados. Se compara el PRIMER componente: el ``.stem`` de
#: ``NUL.extra.docx`` es ``NUL.extra`` y no casaría el set.
#: Windows reserva `COM`/`LPT` con los dígitos 1-9 **y con los superíndices ¹ ² ³**, que
#: es la variante que la R1 señaló (su H-13) y que `COM¹.docx` explotaba.
_RESERVADOS_WINDOWS = frozenset(
    ["con", "prn", "aux", "nul"]
    + [f"{fam}{d}" for fam in ("com", "lpt")
       for d in [str(i) for i in range(1, 10)] + ["¹", "²", "³"]])

#: Tope práctico de ruta absoluta en Windows sin rutas largas activadas.
LIMITE_RUTA = 259
LIMITE_SEGMENTO = 255
#: Lo que 4b añadirá al nombre para el temporal: ``.<nombre>.<pid>.tmp``. Se presupuesta
#: aquí porque quien bendice el nombre es esta mitad, y prometer un límite que el temporal
#: rompe es incumplir la promesa.
MARGEN_TEMPORAL = 1 + 1 + 6 + len(".tmp")


class MapaInvalidoError(Exception):
    """El mapa no cumple el contrato. Trae TODOS los problemas, no el primero."""

    def __init__(self, problemas: list[str]) -> None:
        self.problemas = problemas
        super().__init__(f"{len(problemas)} problema(s) en {MAPA_FILENAME}:\n"
                         + "\n".join(f"  - {p}" for p in problemas))


@dataclass(frozen=True)
class EntradaMapa:
    carpeta: str
    origen: str
    doc_id: str | None = None
    orden: str | None = None
    descripcion: str | None = None
    fichero: str | None = None
    eco_crm: str | None = None
    sin_cobertura_ok: bool = False
    logical_key: str = ""


@dataclass(frozen=True)
class MapaProcesal:
    version: int
    expediente_crm: str
    entradas: tuple[EntradaMapa, ...] = ()
    sin_asignar: tuple[dict, ...] = ()


class _CargadorSinDuplicados(yaml.SafeLoader):
    """``safe_load`` se queda la última de dos claves iguales, en silencio.

    En un mapa eso significa que la asignación de una carpeta entera desaparece sin que
    el letrado se entere. Aquí es un error.
    """


def _sin_duplicados(loader, node, deep=False):
    salida: dict = {}
    for k_node, v_node in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in salida:
            raise yaml.YAMLError(f"clave duplicada en el YAML: {k!r}")
        salida[k] = loader.construct_object(v_node, deep=deep)
    return salida


_CargadorSinDuplicados.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _sin_duplicados)


def mapa_path(raiz: Path) -> Path:
    return Path(raiz) / "05_Procedimiento" / MAPA_FILENAME


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def nombre_destino(e: EntradaMapa, ext: str) -> str:
    """Nombre final del fichero en su carpeta.

    ``origen: despacho`` conserva SU nombre: la herramienta no renombra lo que no ha
    creado (spec §0). ``origen: crm`` se nombra ``<orden>_<descripcion>.<ext>``.
    """
    if e.origen == ORIGEN_DESPACHO:
        return e.fichero or ""
    ext = str(ext).lstrip(".")
    return f"{e.orden}_{_slug(e.descripcion or '')}" + (f".{ext}" if ext else "")


def _unidades_utf16(s: str) -> int:
    """Longitud en **unidades UTF-16**, que es como Windows cuenta sus rutas.

    `len()` cuenta puntos de código, y un carácter fuera del BMP —un emoji en el nombre de
    una carpeta, por ejemplo— ocupa **dos** unidades. La R1 lo midió (su H-14): un temporal
    autorizado con 259 puntos de código ocupaba 294 unidades. Presupuestar en la unidad
    equivocada es no presupuestar.
    """
    return len(s.encode("utf-16-le")) // 2


def presupuesto_longitud(raiz: Path, carpeta: str, nombre: str) -> str:
    """``nombre``, truncado con sufijo hash ESTABLE si la ruta no cabe **con su temporal**.

    El sufijo sale del nombre completo, así que es determinista entre corridas: dos
    lecturas seguidas producen el mismo destino. Se cuenta en unidades UTF-16, que es la
    unidad de la API de destino.
    """
    base = Path(raiz).resolve() / "05_Procedimiento" / carpeta
    tope = LIMITE_RUTA - MARGEN_TEMPORAL
    if (_unidades_utf16(str(base / nombre)) <= tope
            and _unidades_utf16(nombre) + MARGEN_TEMPORAL <= LIMITE_SEGMENTO):
        return nombre
    stem, _, ext = nombre.rpartition(".")
    if not stem:
        stem, ext = nombre, ""
    sufijo = "~" + hashlib.sha256(nombre.encode("utf-8")).hexdigest()[:8]
    cola = f".{ext}" if ext else ""
    margen = min(tope - _unidades_utf16(str(base)) - 1 - len(sufijo) - len(cola),
                 LIMITE_SEGMENTO - MARGEN_TEMPORAL - len(sufijo) - len(cola))
    if margen < 1:
        raise MapaInvalidoError([
            f"la ruta de {carpeta!r} no admite ningún nombre con su temporal: "
            f"{_unidades_utf16(str(base))} unidades de carpeta sobre un tope de {tope}"])
    # El corte se hace por puntos de código y luego se COMPRUEBA en unidades: cortar
    # directamente en unidades partiría un par suplente por la mitad.
    recorte = stem[:margen]
    while recorte and _unidades_utf16(f"{recorte}{sufijo}{cola}") + MARGEN_TEMPORAL > LIMITE_SEGMENTO:
        recorte = recorte[:-1]
    return f"{recorte}{sufijo}{cola}"


def _validar_nombre_windows(nombre: str, donde: str, problemas: list[str]) -> bool:
    malos = sorted(_PROHIBIDOS & set(nombre))
    if malos:
        problemas.append(
            f"{donde}: {nombre!r} lleva un caracter que Windows no admite: "
            f"{[c if c.isprintable() else hex(ord(c)) for c in malos]}")
        return False
    if nombre.split(".")[0].lower() in _RESERVADOS_WINDOWS:
        problemas.append(f"{donde}: {nombre!r} usa un nombre reservado de Windows")
        return False
    if nombre != nombre.strip() or nombre.rstrip(" .") != nombre:
        problemas.append(
            f"{donde}: {nombre!r} tiene espacios o puntos al principio o al final")
        return False
    return True


def _validar_entrada(carpeta: str, i: int, raw: object,
                     problemas: list[str]) -> EntradaMapa | None:
    donde = f"{carpeta!r}[{i}]"
    if not isinstance(raw, dict):
        problemas.append(
            f"{donde}: cada entrada debe ser un mapa, no {type(raw).__name__}")
        return None

    origen = raw.get("origen")
    if origen not in ORIGENES:
        problemas.append(f"{donde}: `origen` es {origen!r}; válidos: {list(ORIGENES)}")
        return None

    if origen == ORIGEN_CRM:
        faltan = [c for c in ("doc_id", "orden", "descripcion") if not raw.get(c)]
        if faltan:
            problemas.append(f"{donde}: la rama `crm` exige {faltan}")
            return None
        orden = str(raw["orden"])
        if not _RE_ORDEN.fullmatch(orden):
            problemas.append(
                f"{donde}: `orden` {orden!r} no casa la gramática {_RE_ORDEN.pattern} — "
                f"este valor se incrusta en el nombre del fichero")
            return None
        descripcion = raw["descripcion"]
        if not isinstance(descripcion, (str, int)):
            problemas.append(
                f"{donde}: `descripcion` debe ser texto y es {type(descripcion).__name__}; "
                f"una lista o un dict se convertían a su repr de Python y acababan en el "
                f"nombre del fichero")
            return None
        descripcion = str(descripcion)
        if not _slug(descripcion):
            problemas.append(
                f"{donde}: `descripcion` {descripcion!r} queda vacía al normalizarla, "
                f"así que no puede nombrar un fichero")
            return None
        sco = raw.get("sin_cobertura_ok", False)
        if not isinstance(sco, bool):
            problemas.append(
                f"{donde}: `sin_cobertura_ok` debe ser un booleano de YAML y es {sco!r} "
                f"({type(sco).__name__}). `'false'` no desactiva nada: `bool('false')` es "
                f"True, y este permiso autoriza a copiar documentos no buscables")
            return None
        if not isinstance(raw["doc_id"], (str, int)) or isinstance(raw["doc_id"], bool):
            problemas.append(
                f"{donde}: `doc_id` debe ser el id del documento y es "
                f"{type(raw['doc_id']).__name__}")
            return None
        e = EntradaMapa(carpeta=carpeta, origen=origen, doc_id=str(raw["doc_id"]),
                        orden=orden, descripcion=descripcion, sin_cobertura_ok=sco)
        # El nombre que ESTA entrada va a producir pasa la misma validación que el de la
        # rama `despacho`. La rev. 1 solo validaba el `fichero` del despacho, así que un
        # `orden`/`descripcion` que produjera un nombre imposible no se veía hasta escribir.
        if not _validar_nombre_windows(nombre_destino(e, "pdf"), donde, problemas):
            return None
        return e

    fichero = raw.get("fichero")
    if not fichero or not isinstance(fichero, str):
        problemas.append(f"{donde}: la rama `despacho` exige `fichero` como texto")
        return None
    if "/" in fichero or "\\" in fichero or Path(fichero).is_absolute():
        problemas.append(
            f"{donde}: `fichero` debe ser un basename, no una ruta: {fichero!r}")
        return None
    if fichero in (".", ".."):
        problemas.append(f"{donde}: `fichero` no puede ser {fichero!r}")
        return None
    if not _validar_nombre_windows(fichero, donde, problemas):
        return None
    eco = raw.get("eco_crm")
    if eco is not None and not isinstance(eco, (str, int)):
        problemas.append(
            f"{donde}: `eco_crm` debe ser el doc_id, no {type(eco).__name__}")
        return None
    return EntradaMapa(carpeta=carpeta, origen=origen, fichero=fichero,
                       eco_crm=None if eco is None else str(eco),
                       logical_key=f"{ORIGEN_DESPACHO}:{fichero}")


def cargar(raiz: Path) -> MapaProcesal:
    """Lee y valida el mapa. Lanza :class:`MapaInvalidoError` con TODOS los problemas."""
    p = mapa_path(raiz)
    problemas: list[str] = []
    if not p.is_file():
        raise MapaInvalidoError([
            f"no existe {p}. La asignación documento → fase es del letrado; usa "
            f"`procedimiento borrador-mapa` para partir de una propuesta"])
    try:
        datos = yaml.load(p.read_text(encoding="utf-8"), _CargadorSinDuplicados) or {}
    except yaml.YAMLError as exc:
        raise MapaInvalidoError([f"YAML ilegible: {exc}"]) from exc
    if not isinstance(datos, dict):
        raise MapaInvalidoError([f"la raíz debe ser un mapa, no {type(datos).__name__}"])

    version = datos.get("version")
    if (not isinstance(version, int) or isinstance(version, bool)
            or version != VERSION_SOPORTADA):
        problemas.append(
            f"`version` es {version!r} ({type(version).__name__}); soportada: el entero "
            f"{VERSION_SOPORTADA}")
    expediente = datos.get("expediente_crm")
    if (not expediente or isinstance(expediente, bool)
            or not isinstance(expediente, (str, int))):
        problemas.append(
            f"falta `expediente_crm`, o no es el id del expediente (es "
            f"{type(expediente).__name__}). `true` se convertía en `'True'`")
        expediente = ""
    else:
        expediente = str(expediente).strip()
        if not expediente:
            problemas.append("`expediente_crm` queda vacío al quitarle los espacios")

    crudas = datos.get("carpetas") or {}
    if not isinstance(crudas, dict):
        problemas.append(f"`carpetas` debe ser un mapa, no {type(crudas).__name__}")
        crudas = {}

    entradas: list[EntradaMapa] = []
    for carpeta, lista in crudas.items():
        if not es_carpeta_fase(str(carpeta)):
            problemas.append(
                f"carpeta fuera de la lista blanca: {carpeta!r}; válidas: "
                f"{list(CARPETAS_FASE)}")
            continue
        if not isinstance(lista, list):
            problemas.append(f"{carpeta!r}: debe contener una lista de entradas")
            continue
        for i, raw in enumerate(lista):
            e = _validar_entrada(str(carpeta), i, raw, problemas)
            if e is None:
                continue
            if e.origen == ORIGEN_CRM:
                e = replace(e, logical_key=f"{ORIGEN_CRM}:{expediente}:{e.doc_id}")
            entradas.append(e)

    vistas: dict[str, str] = {}
    destinos: dict[str, str] = {}
    for e in entradas:
        if e.logical_key in vistas:
            problemas.append(
                f"clave lógica duplicada {e.logical_key!r}: en {vistas[e.logical_key]!r} "
                f"y en {e.carpeta!r}")
        else:
            vistas[e.logical_key] = e.carpeta
        # Colisión de nombre final. La extensión no se conoce todavía, así que se compara
        # el tronco: dos entradas con el mismo tronco en la misma carpeta colisionan en
        # cualquier extensión. `casefold` porque el filesystem de Windows no distingue.
        tronco = f"{e.carpeta}/{nombre_destino(e, '')}".casefold()
        if tronco in destinos:
            problemas.append(
                f"dos entradas producen el mismo nombre final en {e.carpeta!r}: "
                f"{destinos[tronco]} y {e.logical_key}")
        else:
            destinos[tronco] = e.logical_key

    if problemas:
        raise MapaInvalidoError(problemas)

    sin_asignar = tuple(d for d in (datos.get("sin_asignar") or [])
                        if isinstance(d, dict))
    return MapaProcesal(version=int(version), expediente_crm=expediente,
                        entradas=tuple(entradas), sin_asignar=sin_asignar)
