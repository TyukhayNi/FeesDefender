"""Cerebro de la ficha CRM completa (B1): modelo de entrada + carga del YAML.

Determinista, sin red: parsea ``00_Input/_ficha_crm.yaml`` a un ``FichaCRMInput``
con los DTOs de ``sudespacho_relations`` (que normalizan el teléfono, B3). El
orquestador (``scripts/crm_ficha.py``) ejecuta los efectos contra el CRM.
"""
from __future__ import annotations

import difflib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from core.config import CLIENTES_PROPIOS_EV
from core.sudespacho_relations import (NuevoClienteContrario, NuevoColaborador,
                                       _canonizar_documento, provincia_canonica)
from core.utils import normalize_es_phone

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
    #: Lo que el YAML declara de cada parte, validado y SIN normalizar, en el orden de
    #: `contrarios` / `colaboradores`. Es lo que audita la lectura (spec rev. 3 §4 B.2): el DTO
    #: normaliza al construirse, y comparar el DTO no vería lo perdido por el camino (R2/H-02).
    declarados_contrarios: list[dict[str, str]] = field(default_factory=list)
    declarados_colaboradores: list[dict[str, str]] = field(default_factory=list)

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


# ---------------------------------------------------------------------------
# Claves, tipos y lo que no puede llegar nunca (spec rev. 3 §3 A.2, A.3, A.5)
# ---------------------------------------------------------------------------

CLAVES_RAIZ = ("contrario", "colaboradores", "notas_html", "cliente_propio", "firmante")
#: `id_crm`, al final: no es un dato de la parte sino cómo se llega a su ficha (spec §3 A.4).
CLAVES_CONTRARIO = ("nombre", "apellido1", "apellido2", "email", "movil", "nif",
                    "direccion", "poblacion", "cp", "provincia", "telefono", "id_crm")
CLAVES_COLABORADOR = ("nombre", "email", "movil", "telefono", "nif", "id_crm")

_TELEFONOS = ("movil", "telefono")

#: El literal del problema de identidad, UNA vez: los tests lo importan, así que el mensaje
#: puede crecer sin vaciar un aserto que lo busque.
SIN_IDENTIDAD = "sin identidad estable"


def _id_crm(v: object) -> str | None:
    """El `id_crm` canónico (`"01128"` → `"1128"`), o `None` si no es el número de una ficha:
    un entero positivo o dígitos ASCII. Un booleano no vale, aunque Python lo cuente como
    entero."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return str(v) if v > 0 else None
    if isinstance(v, str):
        t = v.strip()
        if t.isascii() and t.isdigit() and int(t) > 0:
            return str(int(t))
    return None


def _forma(valor: object) -> str:
    if isinstance(valor, dict):
        return "un mapping"
    if isinstance(valor, list):
        return "una lista"
    return type(valor).__name__


def _hay(valor: object) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _sugerencia(clave: object, validas: tuple[str, ...]) -> str:
    """TODAS las válidas cercanas, en el orden de la tupla (R2/H-07): `apellido` casa igual con
    `apellido1` que con `apellido2`, y elegir una sería adivinar. No es un alias de entrada: la
    clave sigue rechazada."""
    cerca = set(difflib.get_close_matches(str(clave), validas, n=len(validas), cutoff=0.6))
    elegidas = [repr(v) for v in validas if v in cerca]
    return f"; ¿querías {' o '.join(elegidas)}?" if elegidas else ""


def _problemas_escalar(valor: object, ruta: str) -> list[str]:
    """Un escalar de la ficha: un texto, o `null` (= «no hay dato»). Nada más.

    Los números conservan la explicación que ya daba `_escalar` (R1/H-08 del PR #275): `cp:
    01001` sin comillas lo resuelve PyYAML como el **entero octal 513**, y el dato original ya no
    se puede recuperar. Un mapping o una lista pasaban como su representación de Python (R1/H-02
    del diseño de esta pieza), y eso tampoco es un dato.
    """
    if valor is None or isinstance(valor, str):
        return []
    if isinstance(valor, (bool, int, float)):
        return [f"{ruta}: vino del YAML como {type(valor).__name__} ({valor!r}). Un valor con "
                "ceros a la izquierda lo reinterpreta YAML (`01001` es el octal 513) y el dato "
                "original ya no se puede recuperar. Escríbelo entre comillas: `cp: '01001'`"]
    return [f"{ruta}: tiene que ser un texto o null, y es {_forma(valor)}"]


def _problemas_parte(d: dict, ruta: str, validas: tuple[str, ...]) -> list[str]:
    p = [f"{ruta}.{k}: clave desconocida{_sugerencia(k, validas)}" for k in d if k not in validas]
    p += [x for k in validas if k != "id_crm" and k in d
          for x in _problemas_escalar(d[k], f"{ruta}.{k}")]
    if d.get("id_crm") is not None and _id_crm(d["id_crm"]) is None:     # null = no hay dato
        p.append(f"{ruta}.id_crm: {d['id_crm']!r} no es el número de una ficha del CRM")
    nombre = d.get("nombre")
    if nombre is None or (isinstance(nombre, str) and not nombre.strip()):
        p.append(f"{ruta}.nombre: falta o está vacío")     # ausente, null o solo espacios
    # Lo que no puede llegar NUNCA es propiedad de la declaración, no de la ficha: vale igual
    # para una parte que se va a crear que para una que ya existe (spec §3 A.3, R2/H-02).
    for k in _TELEFONOS:
        v = d.get(k)
        if _hay(v) and not normalize_es_phone(v.strip()):
            p.append(f"{ruta}.{k}: {v!r} se queda vacío al normalizarlo, y la parte se "
                     "escribiría sin él")
    v = d.get("provincia")
    if "provincia" in validas and _hay(v) and provincia_canonica(v) is None:
        p.append(f"{ruta}.provincia: {v!r} no es ninguna provincia del CRM y el Select la "
                 "descartaría: el dato no puede llegar nunca")
    # Identidad estable (spec §3 A.4, R1/H-04): `resolver_parte` identifica solo por NIF o
    # email, así que sin ninguno —ni `id_crm`, la salida para una parte legítima sin ellos—
    # cada relanzamiento crearía otra ficha.
    if not (_hay(d.get("nif")) or _hay(d.get("email")) or _id_crm(d.get("id_crm"))):
        p.append(f"{ruta}: {SIN_IDENTIDAD} —falta NIF, email o id_crm—: cada corrida crearía "
                 "otra ficha y la anterior quedaría como sobrante (spec §3 A.4)")
    return p


def validar_ficha(data: object) -> list[str]:
    """Todos los problemas de forma, claves y tipos, con su ruta (spec §3 A.2-A.5).

    Lista vacía = la ficha se puede construir. Se valida la colección ENTERA antes de construir
    nada (R1/H-08 de P6): validar mientras se itera escribiría la primera parte antes de
    descubrir que la segunda está mal. Y **un elemento inválido no es una parte ausente**:
    filtrarlo convertiría una lista de un elemento roto en «cero contrarios» en silencio.
    """
    if not isinstance(data, dict):
        return [f"la raíz del _ficha_crm.yaml tiene que ser un mapping, y es {_forma(data)}"]
    p = [f"{k}: clave desconocida{_sugerencia(k, CLAVES_RAIZ)}" for k in data
         if k not in CLAVES_RAIZ]
    for k in ("notas_html", "firmante"):
        p += _problemas_escalar(data.get(k), k)
    cp = data.get("cliente_propio")
    if cp is not None and not (isinstance(cp, str) and cp.strip() in CLIENTES_PROPIOS_EV):
        # Hoy `false` caía al defecto por el `or` (R1/H-02): lo declarado se respeta o se
        # rechaza, nunca se sustituye en silencio.
        p.append(f"cliente_propio desconocido: {cp!r} (tiene que ser uno de "
                 f"{sorted(CLIENTES_PROPIOS_EV)}; ver core.config.CLIENTES_PROPIOS_EV)")
    contr = data.get("contrario")
    if isinstance(contr, dict):
        p += _problemas_parte(contr, "contrario", CLAVES_CONTRARIO)
    elif isinstance(contr, list):
        for i, e in enumerate(contr):
            p += (_problemas_parte(e, f"contrario[{i}]", CLAVES_CONTRARIO) if isinstance(e, dict)
                  else [f"contrario[{i}]: tiene que ser un mapping, y es {_forma(e)}"])
    elif contr is not None:
        p.append("contrario: tiene que ser un mapping o una lista de mappings, y es "
                 f"{_forma(contr)}")
    cols = data.get("colaboradores")
    if isinstance(cols, list):
        for i, e in enumerate(cols):
            p += (_problemas_parte(e, f"colaboradores[{i}]", CLAVES_COLABORADOR)
                  if isinstance(e, dict)
                  else [f"colaboradores[{i}]: tiene que ser un mapping, y es {_forma(e)}"])
    elif cols is not None:
        p.append(f"colaboradores: tiene que ser una lista de mappings, y es {_forma(cols)}")
    return p


# ---------------------------------------------------------------------------
# Construcción, sobre lo YA validado
# ---------------------------------------------------------------------------

def _valor(v: object) -> str:
    """Un escalar YA VALIDADO, como texto. `null` es «no hay dato» (R1/H-09 del PR #275):
    `str(None)` es "None", que es *truthy*, y viajaba al CRM tal cual."""
    return "" if v is None else str(v).strip()


def _contrarios_de(raw) -> list[NuevoClienteContrario]:
    """`contrario:` ya validado, en el orden del fichero.

    | Forma | Significado |
    |---|---|
    | clave ausente o `null` | no hay contrario — legítimo |
    | mapping | uno (compatibilidad: no se migra ningún `_ficha_crm.yaml`) |
    | lista de mappings | N, **en el orden del fichero** |
    | lista vacía | no hay contrario, igual que ausente |

    Un elemento que no es un mapping ya lo ha rechazado `validar_ficha`, con su índice.
    """
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [_contrario_de(raw)]
    return [_contrario_de(e) for e in raw]


def _contrario_de(d: dict) -> NuevoClienteContrario:
    # Leyendo de la tupla, no enumerando a mano: `cp`, `provincia` y `telefono` estuvieron
    # escritos en los YAML sin leerse nunca, porque la lista de aquí no los tenía.
    return NuevoClienteContrario(**{c: _valor(d.get(c)) for c in CLAVES_CONTRARIO
                                    if c != "id_crm"},
                                 id_crm=_id_crm(d.get("id_crm")) or "")


def _colaborador_de(d: dict) -> NuevoColaborador:
    return NuevoColaborador(**{c: _valor(d.get(c)) for c in CLAVES_COLABORADOR
                               if c != "id_crm"},
                            id_crm=_id_crm(d.get("id_crm")) or "")


def _declaracion(d: dict, claves: tuple[str, ...]) -> dict[str, str]:
    """Las claves PRESENTES en la parte, con su valor validado y sin normalizar. Sin `id_crm`:
    la declaración es lo que se COMPARA con la ficha, y el id es cómo se llega a ella."""
    return {k: _valor(d[k]) for k in claves if k in d and k != "id_crm"}


def cargar_ficha_yaml(path: Path) -> FichaCRMInput:
    """Carga ``_ficha_crm.yaml`` → ``FichaCRMInput``: se lee entero o no se construye nada.

    Lanza ``FileNotFoundError`` si no existe y ``ValueError`` con TODOS los problemas —de la
    lectura (`leer_yaml_ficha`) o de la forma, las claves y los tipos (`validar_ficha`)—.
    """
    data = leer_yaml_ficha(path)
    problemas = validar_ficha(data)
    if problemas:
        raise ValueError("_ficha_crm.yaml no se puede usar:\n  - " + "\n  - ".join(problemas))
    cp = data.get("cliente_propio")
    raw = data.get("contrario")
    partes = [] if raw is None else [raw] if isinstance(raw, dict) else raw
    cols = data.get("colaboradores") or []
    return FichaCRMInput(
        contrarios=_contrarios_de(raw),
        colaboradores=[_colaborador_de(c) for c in cols],
        notas_html=_valor(data.get("notas_html")),
        cliente_propio=CLIENTE_PROPIO_DEFAULT if cp is None else _valor(cp),
        firmante=_valor(data.get("firmante")),
        declarados_contrarios=[_declaracion(d, CLAVES_CONTRARIO) for d in partes],
        declarados_colaboradores=[_declaracion(d, CLAVES_COLABORADOR) for d in cols],
    )


# ---------------------------------------------------------------------------
# Auditoría: vínculos y datos por IGUALDAD (spec rev. 3 §4, Parte B)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuditoriaRelaciones:
    ok: list[str]
    faltan: list[str]
    sobran: list[str]


#: Los tres bloques que `crm_ficha` escribe. Los demás (actuaciones, documentos…) no son suyos
#: y no se miran.
BLOQUES_AUDITADOS = ("clientes_propios", "clientes_contrarios", "colaboradores")


def _orden_id(id_: str) -> tuple:
    return (0, int(id_)) if id_.isdigit() else (1, id_)


def auditar_relaciones(esperado: Mapping[str, Sequence[str]],
                       leido: Mapping[str, Sequence[Mapping]]) -> AuditoriaRelaciones:
    """Lo escrito contra lo leído, por IGUALDAD y con multiplicidad (spec §4 B.1).

    `esperado` son los ids que la corrida resolvió, por bloque; `leido`, la salida de
    `get_relaciones`, que ya desacumula un registro por id. Lo que está de más es un fallo
    (`#288`: el YAML es la lista COMPLETA de partes, decisión de Nikolai del 2026-09-25), y la
    multiplicidad no se cambia por conjuntos: dos declaraciones que colapsan a un id con un solo
    vínculo son una `falta`, y un conjunto las daría por buenas (R1/H-02 del PR #275).
    """
    ok: list[str] = []
    faltan: list[str] = []
    sobran: list[str] = []
    for bloque in BLOQUES_AUDITADOS:
        pedidos = Counter(str(i) for i in esperado.get(bloque, ()))
        vistos = Counter(str(v.get("id")) for v in leido.get(bloque, ()) or ())
        for id_ in sorted(set(pedidos) | set(vistos), key=_orden_id):
            p, v = pedidos[id_], vistos[id_]
            if p and v >= p:
                ok.append(f"{bloque} id={id_}" + (f" (x{p})" if p > 1 else ""))
            elif p:
                faltan.append(f"{bloque} id={id_} (la corrida escribió {p}, la lectura ve {v})")
            sobran += [f"{bloque} id={id_}"] * max(0, v - p)
    return AuditoriaRelaciones(ok=ok, faltan=faltan, sobran=sobran)


@dataclass(frozen=True)
class Discrepancia:
    """Un campo que el YAML declara y la ficha del CRM no tiene igual (spec §4 B.2)."""
    elemento: str
    id: str
    campo: str          # la clave del YAML
    propiedad: str      # la del CRM
    tipo: str           # "vacio" | "distinto"
    crm: str
    yaml: str

    def __str__(self) -> str:
        base = f"{self.elemento} id={self.id} {self.propiedad}"
        if self.tipo == "vacio":
            return f"{base}: vacío en el CRM"
        return f"{base}: distinto (CRM {self.crm!r}, YAML {self.yaml!r})"


def _n_texto(v: object) -> str:
    return "" if v is None else " ".join(str(v).split()).casefold()


def _n_nif(v: object) -> str:
    return _canonizar_documento("" if v is None else str(v))


def _n_email(v: object) -> str:
    return "" if v is None else str(v).strip().lower()


def _n_tel(v: object) -> str:
    return normalize_es_phone("" if v is None else str(v).strip())


def _n_cp(v: object) -> str:
    return "" if v is None else str(v).strip()


#: El «Sin Asignar» del Select (atlas, enum `provincia`: `1=Sin Asignar`) es el VACÍO del
#: campo, no una provincia: tratarlo como un valor daría «distinto» ante una ficha sin dato.
_PROVINCIA_SIN_ASIGNAR = frozenset({"1", "sin asignar"})


def _n_provincia_crm(v: object) -> str:
    t = _n_texto(v)
    return "" if t in _PROVINCIA_SIN_ASIGNAR else t


def _n_provincia_yaml(v: object) -> str:
    # La MISMA normalización de texto en los dos lados, después de canonizar la del YAML: con
    # `provincia_canonica` en uno y `casefold` en el otro no casaban NUNCA (R2/H-03). La que no
    # se reconoce ya la ha rechazado `validar_ficha`.
    return _n_texto(provincia_canonica(str(v)) or v)


_NORMALIZA = {"texto": (_n_texto, _n_texto), "nif": (_n_nif, _n_nif),
              "email": (_n_email, _n_email), "tel": (_n_tel, _n_tel), "cp": (_n_cp, _n_cp),
              "provincia": (_n_provincia_yaml, _n_provincia_crm)}

#: (campo del YAML, propiedad del CRM, clase de normalización). Anclado a la fuente, no
#: supuesto: el payload de `_rest_post_cliente_contrario` / `_rest_post_colaborador`, los GET
#: de `get_cliente_contrario` / `get_colaborador` (`_PROPS_COLABORADOR`), el atlas
#: (`### clientes_contrarios`) e `INTEGRACION_SUDESPACHO.md` §10.6.
CAMPOS_CONTRARIO_CRM = (
    ("nombre", "nombre", "texto"), ("apellido1", "1apellido", "texto"),
    ("apellido2", "2apellido", "texto"), ("email", "email", "email"),
    ("movil", "movil", "tel"), ("nif", "nif_cif", "nif"),
    ("direccion", "direccion", "texto"), ("poblacion", "poblacion", "texto"),
    ("cp", "cp", "cp"), ("provincia", "provincia", "provincia"),
    ("telefono", "telefono1", "tel"),
)
CAMPOS_COLABORADOR_CRM = (
    ("nombre", "nombre", "texto"), ("email", "email", "email"),
    ("movil", "movil", "tel"), ("telefono", "telefono1", "tel"), ("nif", "nif_cif", "nif"),
)
_CAMPOS_DE = {"clientes_contrarios": CAMPOS_CONTRARIO_CRM,
              "colaboradores": CAMPOS_COLABORADOR_CRM}


def auditar_datos(elemento: str, id_: str, declarado: Mapping,
                  ficha_crm: Mapping) -> list[Discrepancia]:
    """Cada campo que el YAML declara no vacío, contra el de la ficha del CRM (spec §4 B.2).

    Recibe la DECLARACIÓN —el mapping validado de la parte—, no el DTO: el DTO normaliza al
    construirse (`'+34'` se queda vacío), y la auditoría no vería lo que se perdió por el camino
    (R2/H-02). Tres resultados por campo: igual (no sale), vacío en el CRM o distinto.
    """
    fuera: list[Discrepancia] = []
    for campo, propiedad, clase in _CAMPOS_DE[elemento]:
        bruto = declarado.get(campo)
        if bruto is None or not str(bruto).strip():
            continue                                   # lo que el YAML no declara no se compara
        del_yaml, del_crm = _NORMALIZA[clase]
        visto = del_crm(ficha_crm.get(propiedad))
        if del_yaml(bruto) == visto:
            continue
        fuera.append(Discrepancia(
            elemento=elemento, id=str(id_), campo=campo, propiedad=propiedad,
            tipo="vacio" if not visto else "distinto",
            crm=str(ficha_crm.get(propiedad) or "").strip(), yaml=str(bruto).strip()))
    return fuera


def contradicciones_previas(elemento: str, id_: str, declarado: Mapping, ficha_crm: Mapping,
                            *, por_id: bool) -> list[str]:
    """Lo que la fase previa no deja pasar (spec rev. 3 §3 A.4): un dato DISTINTO en una ficha
    que ya existe y, si se llegó por `id_crm`, una ficha sin nombre, que es como vuelve un id que
    no existe.

    Lo VACÍO no es contradicción: si el campo es completable lo completa la corrida, y si no, lo
    dice la lectura final (el caso de W-030A13). La fase previa es la parte de B.2 que ya está
    decidida antes de escribir: lo no vacío del CRM no cambia al completar, así que no puede
    fallar donde la lectura final no fallaría.
    """
    fuera = [str(d) for d in auditar_datos(elemento, id_, declarado, ficha_crm)
             if d.tipo == "distinto"]
    if por_id and not _n_texto(ficha_crm.get("nombre")):
        fuera.insert(0, f"{elemento} id={id_}: la ficha no existe o no tiene nombre; revisa el "
                        "id_crm")
    return fuera
