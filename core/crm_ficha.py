"""Cerebro de la ficha CRM completa (B1): modelo de entrada + carga del YAML.

Determinista, sin red: parsea ``00_Input/_ficha_crm.yaml`` a un ``FichaCRMInput``
con los DTOs de ``sudespacho_relations`` (que normalizan el teléfono, B3). El
orquestador (``scripts/crm_ficha.py``) ejecuta los efectos contra el CRM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.sudespacho_relations import NuevoClienteContrario, NuevoColaborador

CLIENTE_PROPIO_DEFAULT = "EV_MMC_SPAIN"


@dataclass
class FichaCRMInput:
    #: **Todos** los contrarios, en el orden del fichero. Nunca `None`: una lista vacía es
    #: «no hay contrario», que es un estado legítimo (`[APER-63]`).
    contrarios: list[NuevoClienteContrario] = field(default_factory=list)
    colaboradores: list[NuevoColaborador] = field(default_factory=list)
    notas_html: str = ""
    cliente_propio: str = CLIENTE_PROPIO_DEFAULT
    #: Quién FIRMA el trabajo, que no es quien lo opera (`[APER-72]`, R1/H-05). El prefijo
    #: del asunto de una actuación ES la tarifa —`SENIOR` factura a 103,00 €/h y `ABOGADO` a
    #: 77,00—, así que este dato es una entrada humana explícita y no se infiere del actor de
    #: la UI: Ana puede tramitar una revisión que firma Nikolai. Vacío = no se ha decidido.
    firmante: str = ""

    @property
    def contrario(self) -> NuevoClienteContrario | None:
        """El primero, o `None`. Compatibilidad con los llamadores de un solo contrario.

        Se conserva como propiedad derivada en vez de migrarlos todos: el campo plural es la
        verdad y este es la vista que ya consumían.
        """
        return self.contrarios[0] if self.contrarios else None


# ---------------------------------------------------------------------------
# Lectura sin pérdida (spec rev. 3 §3 A.1)
# ---------------------------------------------------------------------------

_ETIQUETA_MERGE = "tag:yaml.org,2002:merge"


class _CargadorFicha(yaml.SafeLoader):
    """`SafeLoader` que no pierde nada en silencio (spec §3 A.1). Una clave repetida, un merge
    o una clave que no es un texto no se resuelven —«gana la última»—: se APUNTAN con su línea,
    y `leer_yaml_ficha` los levanta todos juntos (R2/H-04)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.problemas: list[str] = []


def _mapping_sin_perdida(loader: _CargadorFicha, node: yaml.MappingNode,
                         deep: bool = False) -> dict:
    vistas: dict[object, int] = {}
    resultado: dict = {}
    for clave_node, valor_node in node.value:
        linea = clave_node.start_mark.line + 1
        if clave_node.tag == _ETIQUETA_MERGE:
            loader.problemas.append(f"línea {linea}: el merge (`<<`) no se admite en "
                                    "_ficha_crm.yaml: escribe cada clave")
            continue
        if not isinstance(clave_node, yaml.ScalarNode):
            forma = "una lista" if isinstance(clave_node, yaml.SequenceNode) else "un mapping"
            loader.problemas.append(f"línea {linea}: una clave tiene que ser un texto, y aquí "
                                    f"es {forma}")
            loader.construct_object(valor_node, deep=deep)     # lo de debajo también se mira
            continue
        clave = loader.construct_object(clave_node, deep=deep)
        valor = loader.construct_object(valor_node, deep=deep)
        if clave in vistas:
            loader.problemas.append(f"línea {linea}: la clave {clave!r} está repetida (ya en la "
                                    f"línea {vistas[clave]}); YAML se quedaría solo con la última")
            continue
        vistas[clave] = linea
        resultado[clave] = valor
    return resultado


_CargadorFicha.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                               _mapping_sin_perdida)


def leer_yaml_ficha(path: Path) -> Any:
    """El `_ficha_crm.yaml` sin perder nada (spec §3 A.1).

    Lo usan `cargar_ficha_yaml` y `scripts/crm_colaboradores_firmas.py::apply`: con un solo
    lector, ninguno de los dos consolida una pérdida que el otro ya no podría ver. Devuelve el
    documento tal cual —`{}` si está vacío—; la forma la juzga `validar_ficha`.

    Lanza `ValueError` con TODAS las claves repetidas, alias, merges y claves que no son un
    texto, cada uno con su línea; `ValueError` ante una sintaxis rota, y `FileNotFoundError` si
    no existe.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe _ficha_crm.yaml: {path}")
    texto = path.read_text(encoding="utf-8")
    try:
        # PyYAML resuelve los alias en el composer, antes de que ningún constructor los vea:
        # donde siguen visibles es en los EVENTOS. Y dentro del `try`, porque el escaneo también
        # analiza y una sintaxis rota lo tumba con `ParserError` (R2/H-04).
        problemas = [f"línea {ev.start_mark.line + 1}: los alias (`&`/`*`) no se admiten en "
                     "_ficha_crm.yaml: escribe cada dato donde va"
                     for ev in yaml.parse(texto, Loader=yaml.SafeLoader)
                     if isinstance(ev, yaml.AliasEvent) or getattr(ev, "anchor", None)]
        cargador = _CargadorFicha(texto)
        try:
            data = cargador.get_single_data()
        finally:
            cargador.dispose()
    except yaml.YAMLError as exc:
        # El límite, declarado (spec §3 A.1): una sintaxis rota para el análisis, y es lo único
        # que se puede decir de ese fichero.
        raise ValueError(f"_ficha_crm.yaml inválido: {exc}") from exc
    problemas += cargador.problemas
    if problemas:
        raise ValueError("_ficha_crm.yaml no se puede leer sin perder datos:\n  - "
                         + "\n  - ".join(problemas))
    return {} if data is None else data


def _contrarios_de(raw) -> list[NuevoClienteContrario]:
    """`contrario:` como mapping, como lista, o ausente. **Valida TODO antes de construir.**

    La semántica entera, porque la ambigüedad estaba justo en los bordes (R1/H-08): el lector
    anterior devolvía `None` por igual para `null`, `[]` y `[«esto no es un mapping»]`.

    | Forma | Significado |
    |---|---|
    | clave ausente o `null` | no hay contrario — legítimo |
    | mapping | uno (compatibilidad: no se migra ningún `_ficha_crm.yaml`) |
    | lista de mappings | N, **en el orden del fichero** |
    | lista vacía | no hay contrario, igual que ausente |
    | elemento que no es mapping | **error con su índice**, y cero escrituras |

    **Un elemento inválido no es una parte ausente.** Filtrar lo que no sea `dict` —el patrón
    que usa `colaboradores`— convertiría una lista de un elemento roto en «cero contrarios» en
    silencio, y la ficha se completaría dejando fuera a una parte sin decirlo. Y validar
    mientras se itera escribiría el primero antes de descubrir que el segundo está mal.
    """
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [_contrario_de(raw)]
    if not isinstance(raw, list):
        raise ValueError(
            f"'contrario' tiene que ser un mapping o una lista de mappings, y es "
            f"{type(raw).__name__}")
    fuera = [str(i) for i, e in enumerate(raw) if not isinstance(e, dict)]
    if fuera:
        raise ValueError(
            f"'contrario' tiene elementos que no son mappings en las posiciones "
            f"{', '.join(fuera)}: corrígelos. No se escribe nada.")
    return [_contrario_de(e) for e in raw]


def _contrario_de(d: dict) -> NuevoClienteContrario:
    if not d.get("nombre"):
        raise ValueError("contrario sin 'nombre' en _ficha_crm.yaml")
    return NuevoClienteContrario(
        nombre=_escalar(d.get("nombre"), "contrario.nombre"),
        apellido1=_escalar(d.get("apellido1"), "contrario.apellido1"),
        apellido2=_escalar(d.get("apellido2"), "contrario.apellido2"),
        email=_escalar(d.get("email"), "contrario.email"),
        movil=_escalar(d.get("movil"), "contrario.movil"),
        nif=_escalar(d.get("nif"), "contrario.nif"),
        direccion=_escalar(d.get("direccion"), "contrario.direccion"),
        poblacion=_escalar(d.get("poblacion"), "contrario.poblacion"),
        # Estos tres no se leian del YAML, y por eso nunca llegaban al CRM aunque
        # estuvieran escritos.
        cp=_escalar(d.get("cp"), "contrario.cp"),
        provincia=_escalar(d.get("provincia"), "contrario.provincia"),
        telefono=_escalar(d.get("telefono"), "contrario.telefono"),
    )


def _escalar(valor: object, campo: str) -> str:
    """Un escalar del YAML como cadena, sin corromperlo ni inventarlo.

    Dos defectos que R1 midio y que `str(...)` producia por si solo:

    - **H-08, el codigo postal en octal.** `cp: 01001` sin comillas lo resuelve PyYAML
      como el **entero octal 513**, y `str()` lo manda al CRM como `"513"`. El caso
      concreto de `08019` se salvaba solo porque tiene un `8` y un `9`, que no son
      digitos octales validos — o sea, por suerte. Un `int` en un campo que es una
      cadena con ceros a la izquierda **no se puede recuperar**: se rechaza y se dice.
    - **H-09, el nulo que viaja como texto.** `cp:` sin valor da `None`, y `str(None)`
      es `"None"`, que es *truthy* y viajaba al CRM tal cual. Una clave preparada y
      vacia significa «no hay dato».
    """
    if valor is None:
        return ""
    if isinstance(valor, bool) or isinstance(valor, int) or isinstance(valor, float):
        raise ValueError(
            f"{campo} vino del YAML como {type(valor).__name__} ({valor!r}). Un valor "
            "con ceros a la izquierda lo reinterpreta YAML (por ejemplo `01001` es el "
            "octal 513) y el dato original ya no se puede recuperar. Escribelo entre "
            "comillas: por ejemplo `cp: \'01001\'`."
        )
    return str(valor).strip()


def _colaborador_de(d: dict) -> NuevoColaborador:
    """El colaborador del YAML, sin que una clave vacia se convierta en un dato.

    Los cinco campos van por `_escalar` por la misma razon que los tres del contrario
    (H-09 del PR #275): `str(None)` es "None", que es *truthy*, y `normalize_es_phone`
    no quita letras, asi que esa cadena viajaba al CRM tal cual. Aqui se quedo abierto
    porque el arreglo se hizo campo a campo en el contrario en vez de cerrar la clase:
    cerrar una propiedad para un rol no la cierra para los demas.
    """
    if not d.get("nombre"):
        raise ValueError("colaborador sin 'nombre' en _ficha_crm.yaml")
    return NuevoColaborador(
        nombre=_escalar(d.get("nombre"), "colaborador.nombre"),
        email=_escalar(d.get("email"), "colaborador.email"),
        movil=_escalar(d.get("movil"), "colaborador.movil"),
        telefono=_escalar(d.get("telefono"), "colaborador.telefono"),
        nif=_escalar(d.get("nif"), "colaborador.nif"),
    )


def cargar_ficha_yaml(path: Path) -> FichaCRMInput:
    """Carga ``_ficha_crm.yaml`` → ``FichaCRMInput``.

    Lanza ``FileNotFoundError`` si no existe y ``ValueError`` si el YAML no es un
    mapping o un contrario/colaborador no tiene ``nombre``.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe _ficha_crm.yaml: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"_ficha_crm.yaml inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("_ficha_crm.yaml debe ser un mapping YAML")

    colaboradores = [
        _colaborador_de(c) for c in (data.get("colaboradores") or []) if isinstance(c, dict)
    ]
    return FichaCRMInput(
        contrarios=_contrarios_de(data.get("contrario")),
        colaboradores=colaboradores,
        notas_html=_escalar(data.get("notas_html"), "notas_html"),
        cliente_propio=_escalar(data.get("cliente_propio") or CLIENTE_PROPIO_DEFAULT, "cliente_propio"),
        firmante=_escalar(data.get("firmante"), "firmante"),
    )
