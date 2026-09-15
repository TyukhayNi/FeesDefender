"""El JSON de la 1a pasada de viabilidad: su contrato, su productor y su validador.

**Por que existe este modulo y no una convencion.** `MEJORAS #262` publico el contrato
de este JSON «derivado POR EJECUCION», y salio mal en CINCO campos: su corrida paso
listas VACIAS y claves desconocidas, que el consumidor sustituye o ignora sin avisar, asi
que el instrumento no podia dar el otro valor. Medido el 2026-09-15: con
`importes: {principal: 12000}` la celda del precio queda vacia y el script imprime `OK`.
Un contrato que solo vive en prosa vuelve a pasar por eso; este vive en `CAMPOS` y en
`validar`, y los tests lo fijan contra el consumidor real.

El consumidor es `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py`, que
corre en el SERVIDOR (Cowork) y no puede importar de aqui. Por eso la validacion esta a
los dos lados: este modulo impide que la corrida escriba basura, y el aviso de claves
desconocidas del consumidor impide que una sesion la escriba a mano. No es duplicacion:
el defecto medido ocurre en el consumidor.
"""
from __future__ import annotations

#: Campo de primer nivel -> tipo que el consumidor espera. Derivado LEYENDO el consumidor
#: y comprobado CORRIENDOLO: `tests/test_render_informe_viabilidad.py`, que arranca
#: `render_informe.py` de verdad contra la plantilla real.
CAMPOS: dict[str, type | tuple[type, ...]] = {
    "case_id": str,
    "ref": str,
    "fecha": str,
    "equipo": dict,
    "observaciones": str,
    "importes": dict,
    "hitos": dict,
    "preguntas": dict,
    "actividades": dict,
    "motivos_impago": str,      # `.strip()` y `.upper()`: NO es una lista
    "avisos": list,             # de OBJETOS, no de cadenas
    "bitacora_inicial": bool,   # se usa como booleano; su texto se descarta
}

CLAVES_EQUIPO = ("director_captador", "asesor_captador",
                 "director_buscador", "asesor_buscador")
#: Las que el consumidor escribe en celdas. `principal`, `costas` e `intereses` —lo que
#: publico #262— NO estan aqui a proposito: no existen para el consumidor.
CLAVES_IMPORTES = ("precio", "pct_honorarios", "pagos_parciales", "propuesta_pago")
CLAVES_ACTIVIDADES = ("exposes_propiedad", "visitas_propiedad",
                      "exposes_buscador", "visitas_buscador")

#: Las claves de `importes` que #262 publico y que se tiran en silencio. Se nombran para
#: que el error DIGA cual es la buena en vez de solo decir que esa no vale.
_IMPORTES_DE_LA_262 = {
    "principal": "precio",
    "costas": None,
    "intereses": None,
}

#: El campo donde la corrida declara lo que no pudo derivar. Guion bajo, como el resto del
#: protocolo del expediente (`_ficha_crm.yaml`, `_recibo_actuacion.json`).
MARCA = "_residuo"


def _problema_de_tipo(nombre, valor, esperado) -> str | None:
    if isinstance(esperado, type) and esperado is bool:
        # `bool` antes que `int`: en Python `True` es `int`, y dejar pasar un 1 aqui
        # aceptaria un JSON que el consumidor interpreta distinto.
        if not isinstance(valor, bool):
            return (f"{nombre}: se espera bool y llego {type(valor).__name__} "
                    f"({valor!r}). El consumidor lo usa como booleano y descarta su "
                    f"contenido.")
        return None
    if not isinstance(valor, esperado):
        return (f"{nombre}: se espera {esperado.__name__} y llego "
                f"{type(valor).__name__} ({valor!r}).")
    return None


def validar(datos: dict) -> list[str]:
    """Los problemas de `datos` contra el contrato. Lista vacia = valido.

    Devuelve TODOS los problemas, no el primero: quien escribe un JSON a mano quiere
    verlos de una vez.
    """
    problemas: list[str] = []
    if not isinstance(datos, dict):
        return [f"el JSON de viabilidad debe ser un objeto y es "
                f"{type(datos).__name__}."]

    for nombre in datos:
        if nombre not in CAMPOS and nombre != MARCA:
            problemas.append(
                f"{nombre}: campo desconocido; el consumidor lo ignorara en silencio. "
                f"Conocidos: {', '.join(sorted(CAMPOS))}.")

    for nombre, esperado in CAMPOS.items():
        if nombre not in datos:
            continue
        p = _problema_de_tipo(nombre, datos[nombre], esperado)
        if p:
            problemas.append(p)

    problemas.extend(_problemas_de_importes(datos.get("importes")))
    problemas.extend(
        _claves_ajenas("equipo", datos.get("equipo"), CLAVES_EQUIPO))
    problemas.extend(
        _claves_ajenas("actividades", datos.get("actividades"), CLAVES_ACTIVIDADES))
    problemas.extend(_problemas_de_avisos(datos.get("avisos")))
    return problemas


def _claves_ajenas(nombre, valor, conocidas) -> list[str]:
    if not isinstance(valor, dict):
        return []
    return [f"{nombre}.{k}: clave desconocida; se ignorara en silencio. "
            f"Conocidas: {', '.join(conocidas)}."
            for k in valor if k not in conocidas]


def _problemas_de_importes(valor) -> list[str]:
    """Las claves de #262 llevan mensaje propio: el error tiene que decir cual es la
    buena, no solo que esa no vale."""
    if not isinstance(valor, dict):
        return []
    problemas = []
    for k in valor:
        if k in CLAVES_IMPORTES:
            continue
        buena = _IMPORTES_DE_LA_262.get(k, "")
        if k in _IMPORTES_DE_LA_262:
            extra = (f" Probablemente querias 'precio'." if buena
                     else " El informe no tiene celda para eso.")
            problemas.append(
                f"importes.{k}: clave que publico MEJORAS #262 y que el consumidor NO "
                f"lee: su valor se tira en silencio.{extra} "
                f"Validas: {', '.join(CLAVES_IMPORTES)}.")
        else:
            problemas.append(
                f"importes.{k}: clave desconocida; se ignorara en silencio. "
                f"Validas: {', '.join(CLAVES_IMPORTES)}.")
    return problemas


def _problemas_de_avisos(valor) -> list[str]:
    if not isinstance(valor, list):
        return []
    return [f"avisos[{i}]: se espera un objeto y llego {type(a).__name__} ({a!r}); "
            f"el consumidor hace .get() sobre cada aviso."
            for i, a in enumerate(valor) if not isinstance(a, dict)]
