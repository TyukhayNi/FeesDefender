"""`verificar_apertura` — el «OK» del EXPEDIENTE, no el del paso.

Diseño: `docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md` §5 (pieza P2 de
la fila #28 de `PLAN.md`).

**El defecto que cierra no es de una herramienta, es de todas.** Cada una declara el
resultado de *su paso* y ninguna el del expediente. El handoff del 2026-09-10 contó ocho
falsos «OK» en un solo día: `organizar` diciendo «sala organizada» con 2 de los 4
artefactos escritos (`MEJORAS #221`), `render_informe` diciendo «OK» con 51 de 88 filas
sin marcar, `apply_label` devolviendo éxito sin aplicar la etiqueta (`#237`), el pull
declarando «hecho» con hashes falsos (`#225`), `ensure_contrario_vinculado` diciendo
«existente» con el id de otro deudor (`#239`). Mientras nadie cierre el lazo sobre el
expediente, el verificador es el letrado, y eso es «estar encima».

**La regla que gobierna todas las comprobaciones: verificar por resultado, nunca por
status.** Ninguna se apoya en el código de salida de la herramienta que produjo el
artefacto. Todas leen el artefacto.

**Solo lectura.** Este módulo no escribe, no repara y no pide el mutex. Un verificador
que arregla lo que encuentra deja de poder decir qué encontró.

## Los cuatro estados

`ok` · `pendiente` · `fallo` son los del diseño. `pendiente` **no** es `fallo`: un
expediente a medias tiene que poder verificarse sin que el informe grite — si «aún no
hay sala de lectura» saliera en rojo, el rojo dejaría de significar algo.

El cuarto, `sin_implementar`, es deliberado. Cinco comprobaciones necesitan red y no se
han construido. Dejarlas fuera de la lista haría que el informe dijera «9 de 9» habiendo
mirado 4 — **el modo de fallo que esta pieza cierra, cometido por la pieza**. Se
enumeran siempre, y `sin_implementar` no cuenta como comprobada: un instrumento que solo
puede devolver un valor no mide nada.

## La regla que la R1 me obligó a escribir

**No poder mirar NO es «no hay nada que ver».** La primera versión trataba cada
imposibilidad como ausencia benigna: un espejo que no se podía leer salía como «ninguno
ajeno»; una lista con entradas corruptas se filtraba en silencio y el conteo cuadraba;
un `01_Procesado` que era un fichero en vez de una carpeta se leía como «la sala aún no
ha corrido». Los tres devolvían verde sobre expedientes rotos.

Ahora toda imposibilidad de leer, toda forma inválida y toda colisión de tipo son
**`fallo`**, con el motivo. `pendiente` queda reservado para la ausencia legítima: el
productor todavía no ha corrido.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

#: El registro de protocolo por ubicación no importa nada de `core` ni escribe: es la
#: misma pregunta que se hace la sala de máquina para no inventariar un fichero (C3).
from core.intake_control import es_fichero_de_protocolo

if TYPE_CHECKING:                                     # pragma: no cover
    from core.verificar_apertura_fuentes import Fuentes

# --- Vocabulario ------------------------------------------------------------------

OK = "ok"
PENDIENTE = "pendiente"
FALLO = "fallo"
SIN_IMPLEMENTAR = "sin_implementar"

#: Los estados que SÍ son el resultado de haber mirado. `sin_implementar` queda fuera a
#: propósito: es la declaración de un hueco, no una medición.
ESTADOS_MEDIDOS: frozenset[str] = frozenset({OK, PENDIENTE, FALLO})
ESTADOS: frozenset[str] = ESTADOS_MEDIDOS | {SIN_IMPLEMENTAR}


@dataclasses.dataclass(frozen=True)
class Resultado:
    """El veredicto de una comprobación, con la evidencia que lo sostiene.

    `evidencia` lleva los números que hacen el veredicto reproducible a mano. Un
    `fallo` sin los conteos que lo produjeron obliga a repetir el trabajo para saber
    qué pasó.
    """
    id: str
    titulo: str
    estado: str
    detalle: str
    evidencia: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS:
            raise ValueError(f"estado {self.estado!r} fuera de {sorted(ESTADOS)}")


@dataclasses.dataclass(frozen=True)
class Informe:
    case_dir: str
    resultados: list[Resultado]

    @property
    def fallos(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado == FALLO]

    @property
    def comprobadas(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado in ESTADOS_MEDIDOS]

    @property
    def resumen(self) -> str:
        n_ok = sum(1 for r in self.resultados if r.estado == OK)
        n_pend = sum(1 for r in self.resultados if r.estado == PENDIENTE)
        return (f"{len(self.comprobadas)} de {len(self.resultados)} comprobaciones "
                f"ejecutadas — {n_ok} ok, {n_pend} pendiente(s), "
                f"{len(self.fallos)} fallo(s)")


# --- Rutas canónicas del expediente -------------------------------------------------
#
# Se componen aquí en vez de importarlas de sus dueños porque este módulo NO debe poder
# escribir: importar `sala_maquina` para una ruta arrastra su motor entero.

_PROCESADO = "01_Procesado"
_SALA_MAQUINA = "02_Sala de máquina"
_SALA_LECTURA = "Sala lectura"
_CATALOGO = "indice_documental.yaml"
_ARTEFACTOS_SALA = ("INDICE.md", "CRONOLOGIA.md", "_MANIFIESTO.md", _CATALOGO)


class _ColisionDeTipo(Exception):
    """Una ruta estructural existe pero no es lo que tiene que ser.

    `MEJORAS`/R1 H-06: con `01_Procesado` ocupado por un FICHERO, la primera versión
    informaba «la sala no ha corrido» y salía en verde. No es que falte una etapa: es
    que la etapa **no puede** correr, y eso es un fallo del expediente.
    """


def _dir_estructural(p: Path, etiqueta: str) -> Path | None:
    """La ruta si es un directorio, `None` si no existe, y revienta si colisiona."""
    if p.is_dir():
        return p
    if p.exists():
        raise _ColisionDeTipo(f"`{etiqueta}` existe y NO es un directorio: {p.name}")
    return None


def _sala_maquina(case_dir: Path) -> Path | None:
    proc = _dir_estructural(case_dir / _PROCESADO, _PROCESADO)
    return _dir_estructural(proc / _SALA_MAQUINA, _SALA_MAQUINA) if proc else None


def _de_red(fn: Callable) -> Callable:
    """Marca una comprobación como dependiente de `Fuentes`."""
    fn._necesita_fuentes = True                            # type: ignore[attr-defined]
    return fn


# --- Las comprobaciones -------------------------------------------------------------


# Hasta el 2026-09-26 el título decía «cuántos», y era deliberado (R1 H-03): la premisa
# era que la cobertura y el catálogo **no comparten clave**. La premisa era falsa, y se
# midió sobre los 23 expedientes que tienen los dos (`MEJORAS #287`): la cobertura lleva la
# ruta de origen de cada fila (`rel_path`) y su sha256, y el catálogo, la misma ruta
# (`ruta_relativa`) y el mismo sha256 (`hash`). Por cardinalidad, en cambio, no cuadraba
# ninguno aunque se arreglaran los hijos de bundle: los dos lados cuentan poblaciones
# distintas —copias por sha256, ficheros de protocolo, el zip crudo de WhatsApp—.
_T_C3 = "Cada documento de la sala de máquina en el catálogo, y cada entrada con su documento"


def c3_cobertura_vs_catalogo(case_dir: Path) -> Resultado:
    """La cobertura contra el catálogo, **documento a documento** (`MEJORAS #287`).

    Una fuente de la cobertura —cada `rel_path` distinto: un bundle partido es UNA fuente
    aunque tenga veinte filas— está catalogada si hay una entrada en su ruta o, si no, una
    entrada con su sha256 de origen: la skill cataloga cada sha256 una vez, y la sala de
    máquina da fila de custodia a cada copia. Y al revés: cada entrada del catálogo tiene que
    tener su fuente en la cobertura, o la sala de lectura enseña un documento del que no hay
    espejo que leer.

    **La unidad del catálogo es la ENTRADA, un par ruta/sha256** (R1/H-01). Una entrada cuya
    ruta es la de una fuente y cuyo sha256 no es el de esa fuente **contradice** —el sitio es
    el suyo y el contenido catalogado no— y no acredita a nadie: ni a la fuente de su ruta ni,
    por su hash, a otra. Lo que casa por una sola de las dos claves —una entrada sin hash, que
    el productor admite, o una ruta que la cobertura no tiene— se acepta y **se dice**, porque
    no es un cotejo íntegro (R1/H-04).

    **Solo dos cosas no se exigen, y las dos son reglas de sus productores, no criterio
    de este verificador**; la evidencia las cuenta:

    - lo que el registro por ubicación declara protocolo (`core/intake_control.py`,
      `MEJORAS #149`): las coberturas antiguas lo inventariaban como documento, y la sala de
      máquina de hoy ya no lo hace;
    - el `_export_original.zip` que el intake deja junto a su `_chat.txt`: la skill lo aparta
      por regla (`emparejar_exports_whatsapp`), porque es el crudo del chat.

    Lo demás que falte, falta: un audio de WhatsApp o un zip que la sala de lectura no recoge
    son documentos del expediente, y C3 los nombra con su ruta.

    **La cobertura tiene que estar sana para cruzarla.** Un hijo de bundle declara un padre
    que es texto, no es él mismo y existe: en la cobertura o **en su propio slug**, que el
    split construye como `<padre>__<doc_id>_<TIPO>` (`split_documental._slug_seg`). Hasta el
    2026-09-26 se exigía la fila del padre, y el split no la escribe por diseño: C3 no podía
    salir verde en ningún caso con un PDF compuesto (nueve de nueve en Barcelona). Y una fila
    sin `rel_path` no se puede cruzar: darla por catalogada o por ausente sería inventar.
    """
    cob_path = _ruta_cobertura(case_dir)
    if cob_path is None or not cob_path.is_file():
        return Resultado("cobertura_vs_catalogo", _T_C3, PENDIENTE,
                         "no hay `_cobertura.json`: la sala de máquina no ha corrido")
    # Las dos ubicaciones del catálogo, como C4 (`MEJORAS #269`). Hasta el 2026-09-25 C3
    # solo miraba la del motor retirado, así que en la misma corrida C4 decía «los 4
    # presentes» y C3 «no hay catálogo»: toda sala montada por la skill se declaraba
    # inexistente y este contraste —el que caza lo que nadie catalogó— no corría.
    proc = case_dir / _PROCESADO
    candidatas = ubicaciones_del_catalogo(proc, proc / _SALA_LECTURA)

    def _donde(p: Path) -> str:
        return "sala" if p.parent.name == _SALA_LECTURA else _PROCESADO

    ocupadas = [p for p in candidatas if p.exists() and not p.is_file()]
    if ocupadas:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         f"`{_CATALOGO}` existe y no es un fichero ({_donde(ocupadas[0])})")
    presentes = [p for p in candidatas if p.is_file()]
    if not presentes:
        return Resultado("cobertura_vs_catalogo", _T_C3, PENDIENTE,
                         "no hay catálogo: la sala de lectura no se ha montado")

    filas, err = _leer_lista_de_mapas(cob_path, json.loads)
    if err:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         f"`{cob_path.name}`: {err}")
    # Aceptar las dos ubicaciones es MIRAR las dos (R1/H-05): con las dos presentes, la
    # primera versión cogía la de la sala y no leía la otra, así que un catálogo que
    # discrepaba salía `ok` donde antes salía `fallo`. Si no cuadran entre sí, eso es el
    # hallazgo; si cuadran, se compara una y la evidencia dice que había dos. «Cuadrar» es
    # tener las MISMAS entradas, no el mismo número: hasta el 2026-09-26 un catálogo con `a`
    # y otro con `b` cuadraban, y C3 cotejaba solo el de la sala.
    catalogos: dict[str, list[dict]] = {}
    for p in presentes:
        entradas_p, err = _leer_lista_de_mapas(p, _yaml_load)
        if err:
            return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                             f"`{p.name}` ({_donde(p)}): {err}")
        catalogos[_donde(p)] = entradas_p
    from collections import Counter

    conteos = {k: len(v) for k, v in catalogos.items()}
    identidades = {k: Counter(_identidad_de_entrada(e) for e in v)
                   for k, v in catalogos.items()}
    if len(identidades) > 1 and len({frozenset(v.items()) for v in identidades.values()}) > 1:
        # Con el mismo número y distinto contenido, los dos conteos solos no dicen nada:
        # se dice cuántas entradas tiene cada uno que el otro no.
        (ka, a), (kb, b) = identidades.items()
        solo = {ka: sum((a - b).values()), kb: sum((b - a).values())}
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         "hay dos catálogos y no cuadran entre sí: "
                         + ", ".join(f"{k} {n}" for k, n in conteos.items())
                         + f" ({solo[ka]} entrada(s) solo en {ka}, {solo[kb]} solo en {kb})",
                         {"catalogos": conteos, "solo_en": solo})
    catalogo_en = _donde(presentes[0])
    entradas = catalogos[catalogo_en]

    # La cobertura, sana y agrupada por fuente.
    slugs = {str(f.get("slug") or "").strip() for f in filas}
    slugs.discard("")
    huerfanos: list[str] = []
    sin_ruta: list[str] = []
    hijos = 0
    fuentes: dict[str, set[str]] = {}          # clave de la ruta -> sha256 de origen
    muestra: dict[str, str] = {}
    for f in filas:
        slug = str(f.get("slug") or "").strip()
        padre = f.get("parent_slug")
        if padre is not None and not (isinstance(padre, str) and not padre.strip()):
            if not isinstance(padre, str):
                huerfanos.append(f"{f.get('slug')!r}: parent_slug no es texto ({padre!r})")
            elif padre.strip() == slug:
                huerfanos.append(f"{f.get('slug')!r}: se declara hijo de sí mismo")
            elif (padre.strip() not in slugs
                  and not _slug_deriva_del_padre(slug, padre.strip(), f.get("doc_id"))):
                huerfanos.append(f"{f.get('slug')!r}: padre {padre.strip()!r} no está en la "
                                 "cobertura y su slug no deriva de él")
            else:
                hijos += 1
        rel = f.get("rel_path")
        if not isinstance(rel, str) or not rel.strip():
            sin_ruta.append(repr(f.get("slug")))
            continue
        clave = _clave_de_ruta_de_origen(rel)
        muestra.setdefault(clave, rel)
        # El sha256 de ORIGEN: el del fichero físico. En una pieza de bundle, `sha256` es el
        # de la pieza y `parent_sha256` el del PDF que el catálogo recoge.
        origen = f.get("parent_sha256") or f.get("sha256")
        fuentes.setdefault(clave, set()).update(
            {origen.lower()} if isinstance(origen, str) and origen.strip() else set())

    # El catálogo, ENTRADA a entrada. La unidad es el par (ruta, sha256): partido en dos
    # conjuntos globales, una mitad acreditaba una fuente mientras la otra contradecía a otra
    # (R1/H-01). Una entrada es CONTRADICTORIA si su ruta es la de una fuente y su sha256 no es
    # el de esa fuente, con los dos lados en sha256 de verdad: un hash vacío no contradice
    # nada, solo no contrasta. Y una contradictoria no acredita a nadie.
    pares = [_identidad_de_entrada(e) for e in entradas]
    contradictorias = {
        i for i, (ruta, h) in enumerate(pares)
        if ruta in fuentes and _es_sha256(h) and h not in fuentes[ruta]
        and any(_es_sha256(s) for s in fuentes[ruta])}
    en_ruta: dict[str, list[int]] = {}
    con_hash: dict[str, list[int]] = {}
    for i, (ruta, h) in enumerate(pares):
        if ruta:
            en_ruta.setdefault(ruta, []).append(i)
        if h:
            con_hash.setdefault(h, []).append(i)

    dirs_con_chat = {k.rsplit("/", 1)[0] if "/" in k else "" for k in fuentes
                     if k.rsplit("/", 1)[-1].casefold() == "_chat.txt"}
    por_ruta = por_sha = solo_por_ruta = solo_por_sha = 0
    excluidas = {"protocolo": 0, "export_crudo_whatsapp": 0}
    sin_catalogar: list[str] = []
    contradicciones: list[str] = []
    for clave in sorted(fuentes):
        coherentes = [i for i in en_ruta.get(clave, []) if i not in contradictorias]
        por_contenido = [i for s in sorted(fuentes[clave]) for i in con_hash.get(s, [])
                         if i not in contradictorias]
        if coherentes:
            por_ruta += 1
            # Por la ruta y sin un sha256 que case: el productor admite `hash` vacío (R1/H-04).
            if not any(pares[i][1] in fuentes[clave] for i in coherentes):
                solo_por_ruta += 1
        elif en_ruta.get(clave):
            contradicciones.append(muestra[clave])
        elif por_contenido:
            por_sha += 1
            # La copia en otra carpeta es el `dedup_por_sha` de la skill: la entrada lleva la
            # ruta de OTRA fuente con ese mismo contenido. Sin eso, la ruta que anuncia la
            # entrada —ajena o vacía— no se acredita, y se dice (R1/H-04).
            if not any(pares[i][0] in fuentes for i in por_contenido):
                solo_por_sha += 1
        elif es_fichero_de_protocolo(clave):
            excluidas["protocolo"] += 1
        elif (clave.rsplit("/", 1)[-1].casefold() == _NOMBRE_EXPORT_CRUDO_WHATSAPP
              and (clave.rsplit("/", 1)[0] if "/" in clave else "") in dirs_con_chat):
            excluidas["export_crudo_whatsapp"] += 1
        else:
            sin_catalogar.append(muestra[clave])
    shas_cobertura = set().union(*fuentes.values()) if fuentes else set()
    catalogo_sin_fuente = [
        str(e.get("ruta_relativa") or f"(sin ruta; id_doc {e.get('id_doc')!r})")
        for (ruta, h), e in zip(pares, entradas)
        if ruta not in fuentes and h not in shas_cobertura]

    por_extension = Counter((Path(r).suffix.lower() or "(sin extensión)")
                            for r in sin_catalogar)
    ev = {"filas_cobertura": len(filas), "hijos_de_bundle": hijos,
          # Fuentes distintas: un bundle partido cuenta una vez, como en el catálogo.
          "documentos_logicos": len(fuentes), "entradas_catalogo": len(entradas),
          "huerfanos": huerfanos[:8], "catalogo_en": catalogo_en, "catalogos": conteos,
          "por_ruta": por_ruta, "por_sha": por_sha, "excluidas": excluidas,
          "solo_por_ruta": solo_por_ruta, "solo_por_sha": solo_por_sha,
          "n_contradicciones": len(contradicciones), "contradicciones": contradicciones[:8],
          "n_sin_catalogar": len(sin_catalogar), "sin_catalogar": sin_catalogar[:8],
          "sin_catalogar_por_extension": dict(por_extension.most_common()),
          "n_catalogo_sin_fuente": len(catalogo_sin_fuente),
          "catalogo_sin_fuente": catalogo_sin_fuente[:8], "filas_sin_rel_path": sin_ruta[:8]}
    if huerfanos:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         f"{len(huerfanos)} fila(s) con `parent_slug` que no apunta a "
                         f"un bundle real: {'; '.join(huerfanos[:3])}", ev)
    if sin_ruta:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         f"{len(sin_ruta)} fila(s) de la cobertura sin `rel_path`: no se "
                         f"pueden cruzar con el catálogo ({', '.join(sin_ruta[:3])})", ev)
    partes = []
    if contradicciones:
        partes.append(f"{len(contradicciones)} fuente(s) cuya entrada del catálogo contradice "
                      f"su sha256 —la ruta es la suya y el contenido catalogado no—: "
                      f"{', '.join(contradicciones[:3])}")
    if sin_catalogar:
        tipos = ", ".join(f"{n} {ext}" for ext, n in por_extension.most_common(4))
        partes.append(f"{len(sin_catalogar)} de las {len(fuentes)} fuentes de la cobertura "
                      f"no están entre las {len(entradas)} entradas del catálogo ({tipos}): "
                      f"{', '.join(sin_catalogar[:3])}")
    if catalogo_sin_fuente:
        partes.append(f"{len(catalogo_sin_fuente)} entrada(s) del catálogo cuya fuente no "
                      f"procesó la sala de máquina: {', '.join(catalogo_sin_fuente[:3])}")
    if partes:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO, "; ".join(partes), ev)
    # El `ok` dice cuánto se cotejó de verdad: lo no exigido no está en el catálogo, y un cruce
    # por una sola de las dos claves no es un cotejo íntegro (R1/H-04).
    exigibles = len(fuentes) - sum(excluidas.values())
    cabeza = ("no hay fuentes exigibles en la cobertura" if exigibles == 0 else
              "la única fuente exigible de la cobertura está en el catálogo" if exigibles == 1
              else f"las {exigibles} fuentes exigibles de la cobertura están en el catálogo")
    entradas_ok = ("el catálogo no tiene entradas" if not entradas else
                   "la entrada del catálogo tiene su fuente" if len(entradas) == 1 else
                   f"las {len(entradas)} entradas del catálogo tienen su fuente")
    notas = [f"{cabeza} ({por_ruta} por ruta y {por_sha} por sha256), y {entradas_ok}"]
    if solo_por_ruta:
        notas.append(f"{solo_por_ruta} solo por la ruta, sin sha256 que contrastar")
    if solo_por_sha:
        notas.append(f"{solo_por_sha} solo por sha256, con una ruta que la cobertura no tiene "
                     "o sin ruta: el sitio que anuncia la entrada no se acredita")
    no_exigidas = [f"{n} de {que}" for que, n in (("protocolo", excluidas["protocolo"]),
                                                   ("export crudo de WhatsApp",
                                                    excluidas["export_crudo_whatsapp"])) if n]
    if no_exigidas:
        notas.append(f"no se exigen {' y '.join(no_exigidas)}")
    if len(catalogos) > 1:
        # Los dos catálogos cuadran por sus pares ruta/sha256, y es lo único que se mira
        # (R1/H-03): ningún productor escribe otro `estado` que `original`.
        notas.append("los dos catálogos recogen las mismas fuentes; sus demás campos no se "
                     "cotejan")
    return Resultado("cobertura_vs_catalogo", _T_C3, OK, "; ".join(notas), ev)


#: El crudo de WhatsApp que el intake deposita junto al `_chat.txt` extraído
#: (`core/whatsapp_intake._ORIGINAL_ZIP_NAME`) y que la skill aparta del catálogo
#: (`preclasificar.emparejar_exports_whatsapp`). Copia, no importación: este módulo no
#: importa escritores. Un test anti-deriva la compara con las dos.
_NOMBRE_EXPORT_CRUDO_WHATSAPP = "_export_original.zip"


def _clave_de_ruta_de_origen(ruta: str) -> str:
    """La clave con que se cruza una ruta de origen de la cobertura con una del catálogo.

    Relativa a `00_Input/`, con `/`, y NFC como en `clave_de_cruce`. Tres casos reales
    escriben `00_Input/…` en la `ruta_relativa` del catálogo (W-02Q38C, W-02UDC1,
    W-0462E1), y un Modo de la skill puede dejar `\\`: se quita UN prefijo `00_Input/`, que
    es lo que la cobertura nunca lleva.
    """
    r = ruta.strip().replace("\\", "/").lstrip("/")
    primero, _, resto = r.partition("/")
    if resto and primero.casefold() == "00_input":
        r = resto
    return clave_de_cruce(r)


def _identidad_de_entrada(e: dict) -> tuple[str, str]:
    """`(clave de ruta, hash)` de una entrada del catálogo; `""` donde no hay dato."""
    ruta, h = e.get("ruta_relativa"), e.get("hash")
    return (_clave_de_ruta_de_origen(ruta) if isinstance(ruta, str) and ruta.strip() else "",
            h.strip().lower() if isinstance(h, str) else "")


_RE_SHA256 = re.compile(r"[0-9a-f]{64}")


def _es_sha256(h: str) -> bool:
    """¿Es un sha256 de verdad? El `_MANIFIESTO.md` admite también `md5:<32 hex>` y vacío
    (`manifiesto_parser.sha_valido`): esos no contradicen nada, solo no contrastan."""
    return bool(_RE_SHA256.fullmatch(h or ""))


def _slug_deriva_del_padre(slug: str, padre: str, doc_id: Any) -> bool:
    """¿El slug de esta pieza lo construyó el split desde ese padre?

    Con `doc_id`, el split escribe `<padre>__<doc_id>_<TIPO>` (`split_documental._slug_seg`), y
    así lo llevan las 668 piezas con `doc_id` de los 23 casos medidos el 2026-09-26. Sin él
    —splits anteriores a la identidad persistente: W-02VND1, W-02ZIIF, W-02VUDR— solo se puede
    exigir el prefijo `<padre>__`. Hasta la R1 (H-05) se exigía el prefijo siempre, y
    `bundle__basura` pasaba por pieza de `bundle`.
    """
    if doc_id is not None and str(doc_id).strip():
        return slug.startswith(f"{padre}__{str(doc_id).strip()}_")
    return slug.startswith(f"{padre}__") and len(slug) > len(padre) + 2


def ubicaciones_del_catalogo(proc: Path, sala: Path) -> tuple[Path, ...]:
    """Dónde puede estar el `indice_documental.yaml`, en orden de preferencia.

    **Los dos constructores no coinciden, y la decisión de cuál gana sigue abierta**
    (`MEJORAS #221`, su mitad de «la ubicación»). La skill `organizar-sala-lectura` —que
    gobierna desde el 2026-09-13— lo pone **dentro de la sala**, junto a los otros tres:
    lo dice su árbol (`SKILL.md` §estructura) y lo confirma su propio verificador, que
    excluye ese nombre al contar documentos de la sala. `core/sala_lectura.py`, el motor
    deprecado, lo escribe en `01_Procesado/` (`catalogo_documental._catalog_path`).

    Hasta el 2026-09-13 esta comprobación solo miraba el sitio del **motor retirado**, así
    que una sala recién construida por la skill se declaraba **incompleta** y la pantalla
    ofrecía pedir un artefacto que ya estaba. Lo levantó la R1 adversarial de la fila #30
    (H-01), reproduciéndolo con los helpers reales de la skill.

    Se aceptan las dos **mientras la decisión siga abierta**, y la evidencia dice en cuál
    apareció: tolerar en silencio convertiría este lector en el sitio donde la ambigüedad
    se esconde. Cuando se decida, aquí queda una sola.
    """
    return (sala / _CATALOGO, proc / _CATALOGO)


def c4_artefactos_de_la_sala(case_dir: Path) -> Resultado:
    """Los cuatro artefactos que la sala de lectura contrata (`MEJORAS #221`).

    El CLI decía «Sala de lectura organizada» habiendo escrito **tres de los cuatro** —los
    dos índices y el catálogo, este último en `01_Procesado/`— y ninguno de ellos el
    `_MANIFIESTO.md`. Lo que lo hace caro no es que falte: es que el operador lee
    «organizada» y no vuelve a mirar. Esta comprobación es el lector que sí mira.
    """
    titulo = "Los cuatro artefactos de la sala de lectura"
    proc = _dir_estructural(case_dir / _PROCESADO, _PROCESADO)
    sala = _dir_estructural(proc / _SALA_LECTURA, _SALA_LECTURA) if proc else None
    if sala is None:
        return Resultado("artefactos_sala", titulo, PENDIENTE,
                         "no hay `Sala lectura`: no se ha montado")
    candidatas = ubicaciones_del_catalogo(proc, sala)
    catalogo = next((p for p in candidatas if p.is_file()), candidatas[-1])
    ubicacion = {n: (catalogo if n == _CATALOGO else sala / n) for n in _ARTEFACTOS_SALA}
    faltan = sorted(n for n, p in ubicacion.items() if not p.is_file())
    no_ficheros = sorted(n for n, p in ubicacion.items() if p.exists() and not p.is_file())
    vacios = sorted(n for n, p in ubicacion.items()
                    if p.is_file() and p.stat().st_size == 0)
    ev = {"presentes": sorted(set(_ARTEFACTOS_SALA) - set(faltan)),
          "faltan": faltan, "vacios": vacios, "no_ficheros": no_ficheros,
          # En cuál de las dos apareció. Sin esto, «presente» no dice cuál de los dos
          # constructores lo puso, que es justo el dato que la decisión abierta necesita.
          "catalogo_en": ("sala" if catalogo.parent == sala else "01_Procesado"
                          ) if catalogo.is_file() else None}
    if no_ficheros:
        return Resultado("artefactos_sala", titulo, FALLO,
                         f"existen pero NO son ficheros: {', '.join(no_ficheros)}", ev)
    if faltan:
        return Resultado("artefactos_sala", titulo, FALLO,
                         f"faltan {len(faltan)} de {len(_ARTEFACTOS_SALA)}: "
                         f"{', '.join(faltan)}", ev)
    if vacios:
        # Un fichero de cero bytes cuenta como ausente: existe para `is_file()` y no
        # dice nada. Distinguirlo importa porque el modo de fallo es el mismo.
        return Resultado("artefactos_sala", titulo, FALLO,
                         f"presentes pero VACÍOS: {', '.join(vacios)}", ev)
    return Resultado("artefactos_sala", titulo, OK,
                     f"los {len(_ARTEFACTOS_SALA)} presentes y con contenido", ev)


#: El dominio que el generador escribe en la columna M, y el único que la hoja acepta.
#: `si` sin tilde entra como equivalencia de grafía, igual que en `render_informe`.
_MARCAS_VALIDAS = frozenset({"sí", "si", "no"})


def c5_viabilidad_completa(case_dir: Path, *, filas_esperadas: int = 88) -> Resultado:
    """Las 88 preguntas, con identidad única y con respuesta **o** marca del dominio.

    Es el defecto que cerró la pieza P5, mirado desde fuera: el generador podía dejar
    filas en blanco y decir «OK».

    **Contar no-vacíos no basta** (R1 H-04): una hoja con las 88 marcas a `basura`, o con
    la misma pregunta repetida 88 veces, pasaba en verde. Ahora se exige que la marca
    esté en el dominio y que los identificadores sean únicos — «las 88 preguntas» es una
    afirmación sobre identidades, no sobre filas.
    """
    titulo = "Las 88 preguntas del informe de viabilidad, marcadas"
    analisis = case_dir / "02_Analisis"
    if analisis.exists() and not analisis.is_dir():
        return Resultado("viabilidad_completa", titulo, FALLO,
                         "`02_Analisis` existe y no es un directorio")
    informes = sorted(analisis.glob("Informe viabilidad*.xlsx")) if analisis.is_dir() else []
    if not informes:
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         "no hay informe de viabilidad en `02_Analisis`")
    try:
        import openpyxl
    except ImportError:                                    # pragma: no cover
        return Resultado("viabilidad_completa", titulo, SIN_IMPLEMENTAR,
                         "no construida aquí: falta openpyxl en este entorno")

    # El más reciente: una apertura deja el del pre-relleno y el firmado. Un EMPATE de
    # mtime no se resuelve por orden alfabético (R1 H-11): sin regla de vigencia, elegir
    # es adivinar, y adivinar puede ocultar el informe malo detrás del bueno.
    mas_nuevo = max(p.stat().st_mtime for p in informes)
    candidatos = [p for p in informes if p.stat().st_mtime == mas_nuevo]
    if len(candidatos) > 1:
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         f"{len(candidatos)} informes con la misma fecha de "
                         "modificación: no hay regla que diga cuál es el vigente",
                         {"empatados": sorted(p.name for p in candidatos)})
    informe = candidatos[0]
    try:
        wb = openpyxl.load_workbook(informe, read_only=True, data_only=True)
    except Exception as exc:                               # noqa: BLE001
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"`{informe.name}` no se puede abrir: {exc!r}")
    try:
        if "PREGUNTAS" not in wb.sheetnames:
            return Resultado("viabilidad_completa", titulo, FALLO,
                             f"`{informe.name}` no tiene hoja PREGUNTAS")
        ws = wb["PREGUNTAS"]
        ids, sin_marca, marca_invalida = [], [], []
        for fila in ws.iter_rows(min_row=5, max_col=13):
            idq = fila[2].value if len(fila) > 2 else None      # C
            if _vacio(idq):
                continue
            idq = str(idq).strip()
            ids.append(idq)
            respuesta = fila[8].value if len(fila) > 8 else None    # I
            pendiente = fila[12].value if len(fila) > 12 else None  # M
            if not _vacio(pendiente):
                if str(pendiente).strip().lower() not in _MARCAS_VALIDAS:
                    marca_invalida.append(f"{idq}={pendiente!r}")
            elif _vacio(respuesta):
                sin_marca.append(idq)
    finally:
        wb.close()

    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    ev = {"fichero": informe.name, "filas_con_id": len(ids), "preguntas_distintas": len(set(ids)),
          "sin_marcar": len(sin_marca), "marcas_invalidas": marca_invalida[:8],
          "ids_repetidos": repetidos[:8], "ejemplos_sin_marcar": sorted(sin_marca)[:8]}
    if repetidos:
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"{len(repetidos)} identificador(es) de pregunta repetidos: "
                         f"{', '.join(repetidos[:5])}", ev)
    if marca_invalida:
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"{len(marca_invalida)} marca(s) fuera del dominio "
                         f"{sorted(_MARCAS_VALIDAS)}: {', '.join(marca_invalida[:3])}", ev)
    if sin_marca:
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"{len(sin_marca)} de {len(ids)} preguntas sin respuesta ni "
                         "marca de pendiente", ev)
    if len(ids) != filas_esperadas:
        # No es un fallo del expediente: es que la plantilla cambió de cuestionario. Se
        # dice, porque el «88» de todas partes deja de ser cierto en silencio.
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         f"todas marcadas, pero son {len(ids)} preguntas y no "
                         f"{filas_esperadas}: la plantilla cambió", ev)
    return Resultado("viabilidad_completa", titulo, OK,
                     f"las {len(ids)} preguntas de `{informe.name}` con respuesta o "
                     "marca válida", ev)


_RE_WCODE = re.compile(r"\bW-[A-Z0-9]{5,8}\b")
#: El W-code del caso va **entre paréntesis** en el nombre de la carpeta
#: (`<codigo> - <direccion> (<W-code>) - <sufijo>`). Buscar la primera aparición en
#: cualquier posición elegía mal en `Relacionado W-04AAAA - Caso (W-TEST01)`, y el ajeno
#: quedaba exento del barrido (R1 H-09).
_RE_WCODE_PROPIO = re.compile(r"\((W-[A-Z0-9]{5,8})\)")
#: Guiones que la extracción de texto mete en lugar del ASCII: si no se normalizan, un
#: `W‐04AAAA` con U+2010 es invisible para el barrido (R1 H-10).
_GUIONES = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")


def c8_sin_wcodes_ajenos(case_dir: Path) -> Resultado:
    """Cero W-codes de otros expedientes en los espejos `03_MD` (`MEJORAS #235`).

    El barrido de documental ajena mira NOMBRES de fichero, así que un W-code que va
    **dentro** del documento le es invisible. Aquí se mira el texto.

    **Un espejo que no se puede leer es `fallo`, no «ninguno ajeno»** (R1 H-05). La
    primera versión hacía `continue` ante un `OSError` y devolvía «ninguno en 0 espejos»
    en verde: no haber podido mirar se presentaba como prueba de que no había nada. Es
    el falso verde más caro que puede tener un verificador, y estaba en la única línea
    que la cobertura del diff no cubría.
    """
    titulo = "Cero W-codes ajenos en los espejos MD"
    sm = _sala_maquina(case_dir)
    md_dir = _dir_estructural(sm / "03_MD", "03_MD") if sm else None
    if md_dir is None:
        return Resultado("wcodes_ajenos", titulo, PENDIENTE,
                         "no hay `03_MD`: la sala de máquina no ha corrido")
    propio, ambiguo = _wcode_del_caso(case_dir)
    if ambiguo:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"el nombre de la carpeta declara {len(ambiguo)} W-codes entre "
                         f"paréntesis ({', '.join(ambiguo)}): identidad ambigua",
                         {"candidatos": ambiguo})
    if not propio:
        return Resultado("wcodes_ajenos", titulo, PENDIENTE,
                         "no se puede determinar el W-code del caso desde el nombre "
                         "de su carpeta: sin referencia no hay ajeno que valga")

    try:
        espejos = sorted(p for p in md_dir.rglob("*.md") if p.is_file())
    except OSError as exc:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"no se puede listar `03_MD`: {exc!r}")

    ajenos: dict[str, list[str]] = {}
    ilegibles: list[str] = []
    for md in espejos:
        try:
            texto = md.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            ilegibles.append(f"{md.name} ({type(exc).__name__})")
            continue
        for w in sorted(set(_RE_WCODE.findall(_normalizar(texto))) - {propio}):
            ajenos.setdefault(w, []).append(md.name)

    ev = {"propio": propio, "espejos_leidos": len(espejos) - len(ilegibles),
          "ilegibles": ilegibles[:8],
          "ajenos": {w: sorted(f)[:5] for w, f in sorted(ajenos.items())}}
    if ilegibles:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"{len(ilegibles)} espejo(s) que NO se pueden leer: no se "
                         f"puede afirmar que no haya W-codes ajenos ({ilegibles[0]})", ev)
    if ajenos:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"{len(ajenos)} W-code(s) ajeno(s) en {len(espejos)} espejos: "
                         f"{', '.join(sorted(ajenos))}", ev)
    return Resultado("wcodes_ajenos", titulo, OK,
                     f"ninguno en {len(espejos)} espejos", ev)


# --- Las cinco de red ---------------------------------------------------------------
#
# Todas comparten la misma disciplina: preguntan al **contexto** —no al puerto— y
# traducen «no se pudo consultar» a `fallo`. Ninguna aprueba por no haber podido
# preguntar.
#
# **Una sola foto, y por qué importa.** El contexto consulta cada fuente UNA vez y
# reparte el resultado. La primera versión dejaba que C1 y C2 pidieran el censo por
# separado, y la R1 lo midió: con dos respuestas distintas —un fichero aparece en la
# segunda y no en la primera— C1 validaba una foto y C2 declaraba contrastada la otra,
# y el informe salía **9 ok / 0 fallos** sobre un expediente al que le faltaba un
# documento. Un verificador que mira dos veces no está mirando: está promediando.


class _Contexto:
    """Las fuentes, consultadas una vez y repartidas. No decide nada."""

    def __init__(self, case_dir: Path, fuentes: "Fuentes") -> None:
        self.case_dir = Path(case_dir)
        self._f = fuentes
        self._censo: Any = _NO_PEDIDO
        self._exps: dict[tuple[str, str], Any] = {}

    def censo(self):
        if self._censo is _NO_PEDIDO:
            team_id, folder_id = _ids_drive(self.case_dir)
            self._censo = (self._f.censo_drive(team_id, folder_id)
                           if folder_id else _SIN_IDS)
        return self._censo

    def expediente(self, exp_id: str, element: str):
        clave = (exp_id, element)
        if clave not in self._exps:
            self._exps[clave] = self._f.expediente_crm(exp_id, element)
        return self._exps[clave]


_NO_PEDIDO = object()
_SIN_IDS = object()


def _ids_drive(case_dir: Path) -> tuple[str, str]:
    fm, _ = _frontmatter(case_dir)
    meta = fm.get("meta") if isinstance(fm.get("meta"), dict) else {}
    return (str(meta.get("drive_ev_team_id") or ""),
            str(meta.get("drive_ev_folder_id") or ""))


def _expedientes_registrados(case_dir: Path) -> tuple[list[tuple[str, str]], str]:
    """`([(exp_id, element), ...], error)`.

    **Todos**, no el primero. La R1 midió que con dos expedientes registrados —uno
    válido y uno inexistente— las tres comprobaciones del CRM preguntaban tres veces por
    el primero y **ninguna** por el segundo: el informe aprobaba una apertura con un
    expediente fantasma dentro (H-08).

    Una lista corrupta devuelve `error`, no lista vacía: «no se puede leer lo que hay»
    y «no hay nada» son cosas distintas (H-03).
    """
    fm, err = _frontmatter(case_dir)
    if err:
        return [], err
    exps = fm.get("sudespacho_expedientes")
    if exps is None:
        return [], ""
    if not isinstance(exps, list):
        return [], f"`sudespacho_expedientes` no es una lista sino {type(exps).__name__}"
    fuera: list[tuple[str, str]] = []
    malas = 0
    for e in exps:
        if not isinstance(e, dict) or not str(e.get("id") or "").strip():
            malas += 1
            continue
        fuera.append((str(e["id"]).strip(), str(e.get("element") or "").strip()))
    if malas:
        return fuera, (f"{malas} entrada(s) de `sudespacho_expedientes` sin `id` "
                       "utilizable: la lista está corrupta")
    return fuera, ""


#: Lo ÚNICO que el pull deposita en la RAÍZ de `01_Drive EV` y no es documento. La
#: primera versión excluía cuatro nombres a cualquier profundidad y todo lo que
#: empezara por punto — y la R1 midió que así un `.documento.pdf` real, presente en los
#: dos lados, salía como faltante, y que un `sub/.pulled` con contenido ajeno se
#: colaba. El propio productor dice que fuera de la raíz esos nombres pueden ser
#: documentos de E&V (H-06).
_PROTOCOLO_RAIZ = frozenset({".pulled"})


def _locales_de_drive_ev(case_dir: Path) -> tuple[list[str], str]:
    """`(rutas, error)`. Un error NO es una lista vacía."""
    raiz = case_dir / "00_Input" / "01_Drive EV"
    if not raiz.exists():
        return [], ""
    if not raiz.is_dir():
        return [], "`00_Input/01_Drive EV` existe y no es un directorio"
    out: list[str] = []
    try:
        for p in sorted(raiz.rglob("*")):
            rel = p.relative_to(raiz).as_posix()
            if p.is_symlink():
                # Sigue el enlace y podría estar fuera del expediente: `is_file()` y la
                # apertura lo siguen, mientras `relative_to` mira solo el nombre. Un
                # enlace a un fichero de fuera pasaba por copia local (H-05).
                return [], f"`{rel}` es un enlace simbólico: no acredita una copia local"
            if not p.is_file():
                continue
            if rel in _PROTOCOLO_RAIZ:
                continue
            out.append(rel)
    except OSError as exc:
        # `rglob` suprime errores de enumeración: sin este control, un directorio que
        # no se puede recorrer devolvía «cero ficheros» y el censo salía en verde (H-04).
        return [], f"no se puede recorrer `01_Drive EV`: {type(exc).__name__}"
    return out, ""


#: Los caracteres con los que `rclone` sustituye EN DISCO lo que Windows no admite en un
#: nombre, con el `--local-encoding` que el pull le pasa (`core/intake_drive.py`). **No se
#: usan para traducir: solo para RECONOCER** que un nombre pasó por ese encoding.
#:
#: Por qué no se traduce, medido por la R1 del 2026-09-13. La primera versión deshacía el
#: mapa con un `str.translate`, y eso es **inseguro por dos razones independientes**:
#:
#: 1. **Las reglas de rclone son POSICIONALES y `translate` no.** `LeftSpace`/`RightSpace`
#:    y `LeftPeriod`/`RightPeriod` solo codifican al principio o al final del segmento. Un
#:    remoto `a b.txt` y un local `a␠b.txt` —que rclone **nunca** habría escrito así— se
#:    cruzaban como el mismo fichero, y C1/C2 daban `ok`. Eso es aceptar como presente un
#:    objeto de identidad distinta: un **falso verde** sobre una red de custodia.
#: 2. **La clase no se cierra con una tabla.** El `--local-encoding` real activa también
#:    `SquareBracket`, `Ctl` e `InvalidUtf8`, y rclone tiene además un **escape** (`‛`)
#:    para cuando el nombre ya contenía el carácter de sustitución. Deshacerlo de verdad es
#:    reimplementar su decodificador; hacerlo a medias es el punto 1.
#:
#: El intercambio que la primera versión hizo —cambiar falsos descuadres, que gritan, por
#: falsos cruces, que callan— es justo el prohibido aquí: **esta red falla cerrado**.
_MARCAS_ENCODING_RCLONE = frozenset(
    "＊＜＞？：｜＂＼／［］．‛␠"                       # sustituciones y escape de rclone
) | frozenset(chr(c) for c in range(0x2400, 0x2421))   # Control Pictures (flag `Ctl`)


def tiene_marcas_de_encoding(ruta: str) -> bool:
    """¿Este nombre pasó por el `--local-encoding` de rclone? Reconoce, no traduce."""
    return any(c in _MARCAS_ENCODING_RCLONE for c in ruta)


def clave_de_cruce(ruta: str) -> str:
    """La clave con la que se cruza el censo remoto contra el disco: **NFC y nada más**.

    **Dos cadenas que se imprimen idénticas pueden no ser iguales, y entonces esta red
    acusa a un fichero que está.** Medido el 2026-09-13 sobre C1 y C2, y antes —el
    2026-09-10, en W-02V48N— por el módulo `intake_drive_hash`, donde el falso hallazgo
    **tapaba una discrepancia real de +326 bytes**: Drive publica `Á` **descompuesta**
    (`A` + U+0301, NFD) y en `G:` está **precompuesta** (U+00C1, NFC). C1 decía «1 falta y
    1 sobra» nombrando dos veces la misma ruta; C2, peor, decía «ninguno tiene hash en
    Drive con el que contrastar» — o sea **dejaba de verificarlo** y lo presentaba como si
    el remoto no publicase checksum. Un «no lo sé» disfrazado de «no hay».

    La normalización Unicode es **segura**: NFC y NFD son dos escrituras del mismo texto,
    así que unificarlas no puede fundir dos ficheros distintos. El encoding de rclone **no
    lo es** —ver `_MARCAS_ENCODING_RCLONE`— y por eso no se deshace aquí: se **reconoce**,
    y un descuadre que lo involucra sale explicado en vez de disfrazado.

    Se conserva siempre la ruta original para mostrarla: lo que se canonicaliza es la clave.
    """
    return unicodedata.normalize("NFC", ruta)


#: La extensión con que `rclone` deja en disco cada nativo de Google. Son sus formatos de
#: exportación **por defecto** (`--drive-export-formats docx,xlsx,pptx,svg`, comprobado en
#: rclone 1.73.5), que el pull no cambia (`core/intake_drive.py`): de la lista, rclone usa
#: el primero que el tipo admite. Medidos en W-02Y2J6 (`MEJORAS #306`): documento y hoja de
#: cálculo; presentación y dibujo, por la regla, sin caso medido.
#:
#: **Un nativo que no está aquí no tiene fichero que esperar** —un formulario, un sitio—:
#: rclone no lo descarga y C1 lo sigue contando como faltante. No se exime en silencio: lo
#: que el pull no trae, el censo lo dice.
_EXPORTACION_NATIVOS_RCLONE: dict[str, str] = {
    "application/vnd.google-apps.document": ".docx",
    "application/vnd.google-apps.spreadsheet": ".xlsx",
    "application/vnd.google-apps.presentation": ".pptx",
    "application/vnd.google-apps.drawing": ".svg",
}


#: Lo que el `ok` de C1 dice de los nativos, y lo que NO puede decir (R1/H-02). C1 es un censo
#: de NOMBRES —para ningún fichero mira el contenido— y el contenido de un nativo tampoco lo
#: mira C2, porque Drive no publica su hash: un `x.docx` cualquiera casa con el nativo `x`.
_AVISO_NATIVOS_SIN_CONTRASTE = ("cruzados por el nombre de su exportación: su contenido no se "
                                "contrasta, Drive no publica el hash de un nativo")


def ruta_local_esperada(f: Any) -> str:
    """El nombre con que el pull deja en disco ese objeto del remoto (`MEJORAS #306`).

    Un nativo de Google no tiene bytes propios: la API lo nombra **sin extensión** y en
    `01_Drive EV` aparece con la de exportación que añade rclone. Comparar los dos nombres
    tal cual daba el mismo fichero como faltante y como sobrante a la vez. La extensión se
    añade siempre —rclone no mira si el nombre ya acababa en `.docx`— y solo por el tipo:
    un PDF subido sin extensión se descarga tal cual.

    **Es una correspondencia de nombre, no de procedencia** (R1/H-02): no acredita que el
    fichero de disco salga de ese objeto.
    """
    return f.ruta + _EXPORTACION_NATIVOS_RCLONE.get(getattr(f, "mime_type", "") or "", "")


@_de_red
def c1_censo_remoto(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """Lo que el remoto declara contra lo que hay en `01_Drive EV`.

    `[APER-65]`: en una apertura del 2026-09-10, 11 de 58 ficheros llegaron renombrados
    por el montaje y el pull los re-copió en cada ronda, dejando 7 duplicados. El censo
    independiente es lo que lo destapó, a mano.

    Se comparan **multiconjuntos** y no conjuntos: dos objetos remotos con el mismo
    nombre son dos ficheros, y el `set` de la primera versión los fundía en uno (H-01).
    """
    titulo = "Censo remoto de E&V contra los ficheros locales"
    locales, err = _locales_de_drive_ev(case_dir)
    if err:
        return Resultado("censo_remoto", titulo, FALLO, err)
    raiz = case_dir / "00_Input" / "01_Drive EV"
    if not raiz.exists():
        return Resultado("censo_remoto", titulo, PENDIENTE,
                         "no hay `00_Input/01_Drive EV`: el pull no ha corrido")
    censo = ctx.censo()
    if censo is _SIN_IDS:
        return Resultado("censo_remoto", titulo, PENDIENTE,
                         "`_caso.md` no registra la carpeta de E&V")
    if censo is None:
        return Resultado("censo_remoto", titulo, FALLO,
                         "no se pudo consultar el remoto (token, red o permisos): no "
                         "se puede afirmar que el pull esté completo")
    if not censo.completo:
        return Resultado("censo_remoto", titulo, FALLO,
                         "el remoto declara su propia enumeración INCOMPLETA: el censo "
                         "no sirve para comparar")

    from collections import Counter

    # Se cruza por `clave_de_cruce` y se MUESTRA la ruta original: el nombre que el
    # operador tiene que buscar es el que ve, no una forma canónica que no existe en
    # ningún sitio. Del lado remoto, la ruta es la que el pull deja en disco: la de un
    # nativo de Google lleva la extensión de su exportación (`MEJORAS #306`).
    esperadas = [(f, ruta_local_esperada(f)) for f in censo.ficheros]
    c_remoto = Counter(clave_de_cruce(e) for _, e in esperadas)
    c_local = Counter(clave_de_cruce(r) for r in locales)
    muestra = {clave_de_cruce(e): e for _, e in esperadas}
    muestra.update({clave_de_cruce(r): r for r in locales})
    nativos = sum(1 for f, e in esperadas if e != f.ruta)
    faltan = sorted(muestra.get(k, k) for k in (c_remoto - c_local).elements())
    sobran = sorted(muestra.get(k, k) for k in (c_local - c_remoto).elements())

    # Dos ficheros del remoto que colapsan a la misma clave NO son el mismo fichero: en
    # un sistema de ficheros Windows **no caben los dos**, así que uno falta de verdad.
    # Fundirlos en silencio sería el defecto simétrico del que este cruce viene a
    # arreglar — un descuadre real presentado como «todo cuadra».
    # Lo mismo vale para un nativo exportado y un fichero subido que acaban en la misma
    # ruta local (`x` → `x.docx` junto a un `x.docx`): se declara con los nombres remotos.
    vistas: dict[str, list[str]] = {}
    for f, e in esperadas:
        vistas.setdefault(clave_de_cruce(e), []).append(f.ruta)
    colisiones = sorted(k for k, rutas in vistas.items() if len(rutas) > 1)

    # Un descuadre entre nombres que pasaron por el `--local-encoding` de rclone casi
    # siempre es el encoding, no un fichero perdido. No se cruza —sería inventar una
    # equivalencia (ver `clave_de_cruce`)— pero se DICE, para que el operador no persiga
    # un fantasma ni, peor, borre un «sobrante» que es el mismo documento.
    con_marcas = sorted({r for r in faltan + sobran if tiene_marcas_de_encoding(r)})
    ev = {"remoto": sum(c_remoto.values()), "local": sum(c_local.values()),
          "faltan_en_local": faltan[:8], "sobran_en_local": sobran[:8],
          "colisiones_de_clave": [vistas[k] for k in colisiones][:8],
          "con_marcas_de_encoding_rclone": con_marcas[:8],
          "nativos_google": nativos}
    if colisiones:
        return Resultado("censo_remoto", titulo, FALLO,
                         f"{len(colisiones)} colision(es) de clave en el remoto: dos "
                         "ficheros que solo se distinguen por su forma Unicode o por un "
                         "carácter que Windows no admite, y que en local no caben los dos",
                         ev)
    if faltan or sobran:
        pista = ""
        if con_marcas:
            pista = (f"; {len(con_marcas)} llevan las marcas del `--local-encoding` de "
                     "rclone, así que el descuadre puede ser SOLO del nombre: compáralos "
                     "a mano antes de tocar nada")
        return Resultado("censo_remoto", titulo, FALLO,
                         f"{len(faltan)} fichero(s) del remoto que no están en local y "
                         f"{len(sobran)} en local que no están en el remoto{pista}", ev)
    exportados = (f" ({nativos} nativos de Google, {_AVISO_NATIVOS_SIN_CONTRASTE})"
                  if nativos else "")
    return Resultado("censo_remoto", titulo, OK,
                     f"los {sum(c_remoto.values())} ficheros del remoto están en local"
                     f"{exportados}, y ninguno de más", ev)


#: Tope de la cola de ceros que se examina. El relleno de `MEJORAS #225` lleva al SIGUIENTE
#: múltiplo de 512, así que por construcción mide menos de 512 bytes.
_MAX_COLA_RELLENO = 512


def _es_el_relleno_de_225(p: Path, sha_remoto: str) -> bool:
    """¿Los bytes de `p` son los del original CON la cola de ceros de `MEJORAS #225` detrás?

    **Prueba, no parecido**, y esa es la diferencia con el intento anterior. El módulo
    `intake_drive_hash` (2026-09-10) se quedaba en «compatible con el relleno» —tamaño
    múltiplo de 512 y mayor que el origen— y su propio docstring admitía por qué: la otra
    mitad de la firma es la cola de ceros, «que exige abrir el fichero». **C2 ya lo abre
    para hashearlo**, así que aquí no hay que conformarse con una sospecha: se quita la
    cola de ceros y se rehashea. Si el resultado es el `sha256` que Drive declara, está
    demostrado que el contenido es el del original con relleno detrás.

    **Una sola pasada, y esa corrección es de la R1** (H-05). La versión anterior leía la
    cola, volvía al principio y rehasheaba: **dos lecturas de un fichero que puede cambiar
    en medio**. El revisor construyó la carrera —la cola de una versión y el prefijo de
    otra— y la función decía «confirmado» sobre una combinación que no existió nunca en
    disco. Es la misma carrera de `MEJORAS #214` un nivel más abajo, dentro del remedio que
    la persigue. Ahora se lee de corrido, se hashea por prefijos y se comprueba al cerrar
    que el tamaño no cambió.

    **La cola tiene que medir MENOS de 512 bytes** (H-05, segunda parte): el relleno lleva
    al SIGUIENTE múltiplo de 512, así que por construcción es más corto que un bloque. La
    versión anterior aceptaba 512 o más —`512 x + 512 ceros` daba «confirmado»—, o sea daba
    por explicada como el defecto conocido una alteración que no lo es.

    **Dónde acaba el original no se ve en los bytes: lo fija el hash** (`MEJORAS #307`).
    Hasta el 2026-09-26 se probaba UNA frontera —la del primer cero de la cola— y un original
    que ya acababa en ceros salía siempre sin confirmar. Se tenía por raro, y en ofimática
    es universal: todo ZIP —y `.docx`, `.xlsx` y `.pptx` lo son— acaba en `00 00`, la
    longitud del comentario de su registro final. En W-02Y2J6, cinco ficheros que eran
    exactamente `#225` salieron «sin explicar». Ahora se prueba **cada** frontera posible
    dentro de la cola de ceros, y solo se confirma si el prefijo hashea al `sha256` que
    Drive declara. Sigue siendo prueba y no parecido: si el prefijo de longitud L tiene ese
    hash, esos L bytes son el original, y detrás solo hay ceros hasta el múltiplo de 512.
    Un fichero alterado no tiene prefijo que cuadre y sale `False`, **sin etiqueta**: mejor
    un hallazgo sin explicar que una explicación falsa sobre un expediente probatorio.

    Se lee en streaming y solo cuando ya hay discrepancia: un expediente lleva vídeos de
    cientos de MB, y cargarlos enteros cambiaría un defecto de custodia por uno de memoria.
    """
    try:
        tam = p.stat().st_size
        if tam == 0 or tam % 512 != 0:
            return False
        # El prefijo que seguro NO es cola (la cola mide < 512), hasheado en bloques; y
        # luego un hash por cada frontera candidata —toda posición desde el primer cero de
        # la cola— sobre los <= 511 bytes finales. `hexdigest` no consume el estado: una
        # sola pasada y a lo sumo 511 finalizaciones baratas.
        h = hashlib.sha256()
        seguro = max(0, tam - (_MAX_COLA_RELLENO - 1))
        leidos = 0
        with p.open("rb") as f:
            while leidos < seguro:
                trozo = f.read(min(1024 * 1024, seguro - leidos))
                if not trozo:
                    return False                 # el fichero encogio: no se afirma nada
                h.update(trozo)
                leidos += len(trozo)
            cola = f.read(tam - seguro)
            if len(cola) != tam - seguro or f.read(1):
                return False                     # encogio o crecio bajo los pies
        ceros = len(cola) - len(cola.rstrip(bytes([0])))
        if ceros == 0:
            return False
        frontera = tam - ceros               # primer cero de la cola examinada
        esperado = sha_remoto.lower()
        for k in range(len(cola)):
            # `h` lleva los `seguro + k` primeros bytes: ese es el original candidato, y
            # desde `frontera` todo lo que queda detrás son ceros.
            if seguro + k >= frontera and h.hexdigest().lower() == esperado:
                return True
            h.update(cola[k:k + 1])
        return False
    except OSError:
        return False                             # no poder mirar no es haber visto
@_de_red
def c2_hash_contra_drive(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """El sha256 local contra el `sha256Checksum` que declara Drive (`MEJORAS #225`).

    El pull guardaba los documentos **rellenados con ceros** a múltiplo de 512, así que
    su sha256 dejaba de ser el del original. Mismo nombre y mismo tamaño aparente; solo
    el hash los distingue.

    Se cuenta lo **contrastado**, no lo disponible. La primera versión informaba «los N
    ficheros coinciden» usando el número de hashes que el remoto publicaba, de modo que
    con cero ficheros locales decía `ok` sin haber abierto ninguno (H-02).
    """
    titulo = "Hash local contra el sha256Checksum que declara Drive"
    raiz = case_dir / "00_Input" / "01_Drive EV"
    locales, err = _locales_de_drive_ev(case_dir)
    if err:
        return Resultado("hash_drive", titulo, FALLO, err)
    if not raiz.exists():
        return Resultado("hash_drive", titulo, PENDIENTE,
                         "no hay `00_Input/01_Drive EV`: el pull no ha corrido")
    censo = ctx.censo()
    if censo is _SIN_IDS:
        return Resultado("hash_drive", titulo, PENDIENTE,
                         "`_caso.md` no registra la carpeta de E&V")
    if censo is None:
        return Resultado("hash_drive", titulo, FALLO,
                         "no se pudo consultar el remoto: no se puede acreditar "
                         "ningún hash")

    # Por `clave_de_cruce`, no por la ruta cruda: si no, un nombre con tilde salía por la
    # rama «no tiene hash en Drive» y **dejaba de verificarse en silencio**, que es lo peor
    # que puede hacer una red de custodia (medido el 2026-09-13; ver `clave_de_cruce`).
    # **Un dict pierde el anterior ante una clave repetida, y eso es una regresión que
    # introdujo la primera versión** (R1/H-04): con dos remotos que colapsan a la misma
    # clave ganaba el último, C2 contrastaba contra el hash EQUIVOCADO y devolvía `ok`
    # donde antes daba `fallo` — dependiendo del orden del censo. Detectar la colisión en
    # C1 y no aquí fue remediar el ejemplo y no la frontera. La clave es la de la ruta que
    # el pull deja en disco, como en C1 (`MEJORAS #306`): un nativo exportado que cae
    # sobre un fichero subido es una clave con dos checksums, y no se elige.
    por_clave: dict[str, set[str]] = {}
    for f in censo.ficheros:
        por_clave.setdefault(clave_de_cruce(ruta_local_esperada(f)), set()).add(f.sha256 or "")
    ambiguas = sorted(k for k, shas in por_clave.items() if len(shas) > 1)
    con_hash = {k: next(iter(shas)) for k, shas in por_clave.items()
                if len(shas) == 1 and next(iter(shas))}
    contrastados, discrepan, ilegibles, relleno_225 = 0, [], [], []
    for rel in locales:
        esperado = con_hash.get(clave_de_cruce(rel))
        if not esperado:
            continue
        try:
            real = _sha256(raiz / rel)
        except OSError as exc:
            ilegibles.append(f"{rel} ({type(exc).__name__})")
            continue
        contrastados += 1
        if real.lower() != esperado.lower():
            discrepan.append(rel)
            if _es_el_relleno_de_225(raiz / rel, esperado):
                relleno_225.append(rel)
    sin_contrastar = len(locales) - contrastados - len(ilegibles)
    explicados = set(relleno_225)
    sin_explicar = [rel for rel in discrepan if rel not in explicados]
    # Las LISTAS se truncan a 8; los CONTEOS no (`MEJORAS #268`). Con 49 discrepancias y 8
    # confirmaciones listadas era imposible saber desde la salida si estaban explicadas
    # las 49 o solo ocho, que es la pregunta que separa íntegro de corrupto.
    ev = {"locales": len(locales), "contrastados": contrastados,
          "sin_hash_remoto": sin_contrastar, "discrepan": discrepan[:8],
          "ilegibles": ilegibles[:8], "relleno_225_confirmado": relleno_225[:8],
          "colisiones_de_clave": ambiguas[:8],
          "n_discrepan": len(discrepan), "n_relleno_225": len(relleno_225),
          "sin_explicar": sin_explicar[:8]}
    if ambiguas:
        return Resultado("hash_drive", titulo, FALLO,
                         f"{len(ambiguas)} clave(s) con MÁS DE UN checksum en el remoto: "
                         "no se puede decir contra cuál contrastar sin elegir por el "
                         f"orden del censo ({', '.join(ambiguas[:3])})", ev)
    if ilegibles:
        return Resultado("hash_drive", titulo, FALLO,
                         f"{len(ilegibles)} fichero(s) local(es) que no se pueden "
                         f"leer: {ilegibles[0]}", ev)
    if discrepan:
        # El veredicto no cambia —el sha256 local NO es el del original, y eso es un
        # fallo de custodia aunque el contenido esté íntegro—; lo que cambia es que el
        # detalle diga lo que `_es_el_relleno_de_225` ya calculó (`MEJORAS #268`).
        cabeza = f"{len(discrepan)} fichero(s) cuyo sha256 NO es el que Drive declara"
        if not sin_explicar:
            detalle = (f"{cabeza}, y TODOS son el relleno con ceros de `MEJORAS #225` "
                       "(confirmado re-hasheando sin la cola): el contenido es el del "
                       "original")
        elif relleno_225:
            detalle = (f"{cabeza}: {len(relleno_225)} con el relleno de `MEJORAS #225` y "
                       f"{len(sin_explicar)} SIN explicar: {', '.join(sin_explicar[:3])}")
        else:
            detalle = (f"{cabeza} y ninguno es el relleno de `MEJORAS #225`: "
                       f"{', '.join(discrepan[:3])}")
        return Resultado("hash_drive", titulo, FALLO, detalle, ev)
    if contrastados == 0:
        return Resultado("hash_drive", titulo, PENDIENTE,
                         f"ninguno de los {len(locales)} ficheros locales tiene hash "
                         "en Drive con el que contrastar", ev)
    if sin_contrastar:
        return Resultado("hash_drive", titulo, PENDIENTE,
                         f"{contrastados} de {len(locales)} contrastados y coinciden; "
                         f"los otros {sin_contrastar} no tienen hash en Drive y quedan "
                         "SIN comprobar", ev)
    return Resultado("hash_drive", titulo, OK,
                     f"los {contrastados} ficheros contrastados coinciden con el hash "
                     "de Drive", ev)


def _cada_expediente(case_dir: Path, ctx: "_Contexto", ident: str, titulo: str):
    """Resuelve la parte común de C6/C7/C9: los expedientes y sus fichas.

    Devuelve `(fichas, resultado_de_corte)`. Si hay corte, la comprobación lo devuelve
    tal cual: no hay nada que comparar.
    """
    exps, err = _expedientes_registrados(case_dir)
    if err:
        return None, Resultado(ident, titulo, FALLO, err)
    if not exps:
        return None, Resultado(ident, titulo, PENDIENTE,
                               "`_caso.md` no registra ningún expediente del CRM: el "
                               "alta no se ha hecho")
    fichas = []
    for exp_id, element in exps:
        ficha = ctx.expediente(exp_id, element)
        if ficha is None:
            return None, Resultado(ident, titulo, FALLO,
                                   f"no se pudo consultar el CRM para el expediente "
                                   f"{exp_id}: no se puede acreditar nada de él")
        fichas.append((exp_id, element, ficha))
    ausentes = [e for e, _, f in fichas if not f.encontrado]
    if ausentes:
        return None, Resultado(ident, titulo, FALLO,
                               f"el CRM no encuentra {len(ausentes)} expediente(s) que "
                               f"`_caso.md` registra: {', '.join(ausentes)}",
                               {"ausentes": ausentes})
    return fichas, None


@_de_red
def c6_ficha_y_relaciones_crm(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """La ficha del CRM, releída por API — no el status del alta (`MEJORAS #239`).

    `ensure_contrario_vinculado` devolvía «existente» con el id de **otro** deudor que
    compartía correo, y el alta decía OK.

    Se exigen **partes**, no «alguna relación». La primera versión contaba todos los
    bloques, de modo que un expediente con una actuación y **cero partes vinculadas**
    pasaba en verde (H-07) — y una actuación no es una parte: es trabajo.
    """
    titulo = "Ficha y relaciones del CRM, releídas por API"
    fichas, corte = _cada_expediente(case_dir, ctx, "crm_ficha", titulo)
    if corte:
        return corte

    sin_leer, sin_partes, detalle = [], [], {}
    for exp_id, _el, f in fichas:
        partes = f.partes
        if partes is None:
            sin_leer.append(exp_id)
        elif not partes:
            sin_partes.append(exp_id)
        else:
            detalle[exp_id] = partes
    ev = {"expedientes": [e for e, _, _ in fichas], "partes": detalle}
    if sin_leer:
        return Resultado("crm_ficha", titulo, FALLO,
                         f"no se pudieron leer las relaciones de {', '.join(sin_leer)}: "
                         "no se puede afirmar que tengan partes", ev)
    if sin_partes:
        return Resultado("crm_ficha", titulo, FALLO,
                         f"{len(sin_partes)} expediente(s) sin NINGUNA parte vinculada: "
                         f"{', '.join(sin_partes)}", ev)
    total = sum(sum(p.values()) for p in detalle.values())
    return Resultado("crm_ficha", titulo, OK,
                     f"{len(fichas)} expediente(s) con {total} parte(s) vinculada(s)", ev)


@_de_red
def c7_actuacion_asociada(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """Una actuación asociada, leída **por el lado del expediente** (`MEJORAS #209`).

    El matiz del lado no es retórico: preguntar al elemento «actuaciones» por las suyas
    devuelve las del despacho. `actuaciones` es **hijo** de `extrajudiciales` y de
    `expedientes_judiciales` (atlas), así que aparece en `related_register` — y eso sí
    acredita la asociación.
    """
    titulo = "Actuación asociada, por el lado del expediente"
    fichas, corte = _cada_expediente(case_dir, ctx, "crm_actuacion", titulo)
    if corte:
        return corte

    sin_leer, sin_actuacion, cuenta = [], [], {}
    for exp_id, _el, f in fichas:
        act = f.actuaciones
        if act is None:
            sin_leer.append(exp_id)
        elif not act:
            sin_actuacion.append(exp_id)
        else:
            cuenta[exp_id] = len(act)
    ev = {"actuaciones": cuenta}
    if sin_leer:
        return Resultado("crm_actuacion", titulo, FALLO,
                         f"no se pudieron leer las relaciones de {', '.join(sin_leer)}",
                         ev)
    if sin_actuacion:
        return Resultado("crm_actuacion", titulo, FALLO,
                         f"{len(sin_actuacion)} expediente(s) sin ninguna actuación "
                         f"asociada: {', '.join(sin_actuacion)}. La apertura no quedó "
                         "registrada como trabajo", ev)
    return Resultado("crm_actuacion", titulo, OK,
                     f"{sum(cuenta.values())} actuación(es) asociada(s)", ev)


@_de_red
def c9_cuantia_coherente(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """La cuantía de `_caso.md` y la del CRM, dos hogares del mismo hecho.

    `MEJORAS #227`: la cuantía se conoce al leer el encargo, así que el alta va al final
    y el dato llegaba al CRM y no al índice local.

    La conversión es **estricta** (ver `_a_numero`). La permisiva de la primera versión
    dejaba pasar `NaN` como coincidencia —porque `abs(nan - x) > 0.005` es falso— y
    confundía «no hay cuantía» con «la cuantía no se puede leer» (H-09).
    """
    titulo = "Cuantía de `_caso.md` igual a la del CRM"
    fichas, corte = _cada_expediente(case_dir, ctx, "cuantia_coherente", titulo)
    if corte:
        return corte

    fm, err = _frontmatter(case_dir)
    if err:
        return Resultado("cuantia_coherente", titulo, FALLO, err)
    meta = fm.get("meta") if isinstance(fm.get("meta"), dict) else {}
    local_crudo = meta.get("cuantia")
    n_local, err_local = _a_numero(local_crudo)
    if err_local:
        return Resultado("cuantia_coherente", titulo, FALLO,
                         f"la cuantía de `_caso.md` no es un número: {err_local}")

    problemas, ev = [], {"local": n_local, "expedientes": {}}
    for exp_id, _el, f in fichas:
        n_crm, err_crm = _a_numero(f.cuantia)
        # Los DOS números, no solo si existen (`MEJORAS #218`): en W-030A13 la evidencia
        # decía `crm_declarada: true` y hubo que leer el CRM a mano para saber cuánto.
        ev["expedientes"][exp_id] = {"crm_declarada": f.cuantia not in (None, ""),
                                     "legible": not err_crm, "crm": n_crm}
        if err_crm:
            problemas.append(f"{exp_id}: la cuantía del CRM no es un número ({err_crm})")
        elif n_local is None and n_crm is None:
            continue
        elif n_local is None:
            problemas.append(f"{exp_id}: el CRM tiene cuantía y `_caso.md` dice "
                             "«pendiente». El dato existe y el índice local miente")
        elif n_crm is None:
            problemas.append(f"{exp_id}: `_caso.md` tiene cuantía y el CRM no")
        elif abs(n_local - n_crm) > 0.005:
            # Medio céntimo: el alta mandaba la cuantía como entero y los céntimos se
            # perdían (`MEJORAS #218`); por debajo de eso es el redondeo conocido.
            nota = ""
            if n_crm == float(int(round(n_local))):
                # EXACTAMENTE lo que manda el alta —`int(round(cuantia))`, con el redondeo
                # bancario de Python— y nada más (R1/H-06: «entero a menos de un euro»
                # etiquetaba también un 48702 frente a un local de 48702.90, que el alta
                # habría mandado como 48703). El veredicto sigue siendo fallo: la property
                # REST admite céntimos, así que lo que está mal es el CRM.
                nota = ": es el truncado del alta (`MEJORAS #218`)"
            problemas.append(f"{exp_id}: la cuantía local ({n_local:.2f}) y la del CRM "
                             f"({n_crm:.2f}) no coinciden{nota}")
    if problemas:
        return Resultado("cuantia_coherente", titulo, FALLO, "; ".join(problemas[:3]), ev)
    if n_local is None:
        return Resultado("cuantia_coherente", titulo, PENDIENTE,
                         "ni `_caso.md` ni el CRM declaran cuantía", ev)
    return Resultado("cuantia_coherente", titulo, OK,
                     "la cuantía local coincide con la del CRM", ev)


def _a_numero(v: Any) -> tuple[float | None, str]:
    """`(numero, error)`. `(None, "")` = ausente. Estricta a propósito.

    Tres cosas que la versión permisiva hacía mal (H-09):

    - `float("NaN")` pasaba, y **cualquier** comparación con NaN es falsa, así que
      `abs(nan - x) > 0.005` daba «coinciden». Un `NaN` en el CRM aprobaba el caso.
    - `1e309` se convierte a infinito y `inf - inf` es NaN: mismo final.
    - Un valor **ilegible** (`'roto'`, `'1.234,56'`) devolvía `None`, igual que la
      ausencia, y el informe decía «ninguno declara cuantía» sobre dos que sí lo hacían.
    """
    import math

    if v is None or (isinstance(v, str) and not v.strip()):
        return None, ""
    if isinstance(v, bool):
        return None, f"{v!r} es un booleano"
    if isinstance(v, (int, float)):
        n = float(v)
    else:
        s = str(v).strip().replace(" ", "")
        # Separador decimal: solo se acepta una forma no ambigua. `1.234,56` y
        # `1,234.56` significan lo mismo con convenciones opuestas, y adivinar cuál usa
        # el emisor es inventarse un dato de dinero.
        if "," in s and "." in s:
            return None, f"{v!r} usa dos separadores: es ambiguo"
        s = s.replace(",", ".")
        try:
            n = float(s)
        except ValueError:
            return None, f"{v!r} no es un número"
    if math.isnan(n) or math.isinf(n):
        return None, f"{v!r} no es un número finito"
    return n, ""


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for trozo in iter(lambda: f.read(1024 * 1024), b""):
            h.update(trozo)
    return h.hexdigest()


def _frontmatter(case_dir: Path) -> tuple[dict, str]:
    """`(frontmatter, error)`. Un error NO es un frontmatter vacío.

    La primera versión devolvía `{}` ante cualquier problema —fichero ilegible, YAML
    roto, raíz que no es un mapa—, así que un `_caso.md` corrupto se leía como «el alta
    no se ha hecho» y las cinco de red salían `pendiente` con exit 0 (H-03). Es la misma
    frontera que la ronda anterior cerró en los lectores locales.
    """
    index = case_dir / "00_Input" / "_caso.md"
    if not index.exists():
        return {}, ""
    if not index.is_file():
        return {}, "`00_Input/_caso.md` existe y no es un fichero"
    try:
        texto = index.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {}, f"`_caso.md` no se puede leer: {type(exc).__name__}"
    if not texto.startswith("---"):
        return {}, "`_caso.md` no empieza por el delimitador del frontmatter"
    try:
        import yaml

        d = yaml.safe_load(texto.split("---", 2)[1])
    except Exception as exc:                               # noqa: BLE001
        return {}, f"el frontmatter de `_caso.md` no es YAML válido ({type(exc).__name__})"
    if d is None:
        return {}, ""
    if not isinstance(d, dict):
        return {}, f"el frontmatter de `_caso.md` no es un mapa sino {type(d).__name__}"
    return d, ""


#: Las nueve, en el orden del diseño. La lista se recorre SIEMPRE entera: un informe que
#: enumera solo lo que sabe mirar es el falso «OK» que esta pieza viene a cerrar.
COMPROBACIONES: tuple[Callable[[Path], Resultado], ...] = (
    c1_censo_remoto,
    c2_hash_contra_drive,
    c3_cobertura_vs_catalogo,
    c4_artefactos_de_la_sala,
    c5_viabilidad_completa,
    c6_ficha_y_relaciones_crm,
    c7_actuacion_asociada,
    c8_sin_wcodes_ajenos,
    c9_cuantia_coherente,
)

#: Los ids de las comprobaciones que SÍ miran el expediente. La guarda de los tests lo
#: usa para exigir que cada una tenga un caso que la ponga en `fallo` — y lo exige
#: EJECUTÁNDOLO, no leyendo el fichero de tests.
IMPLEMENTADAS: tuple[str, ...] = (
    "censo_remoto", "hash_drive", "cobertura_vs_catalogo", "artefactos_sala",
    "viabilidad_completa", "crm_ficha", "crm_actuacion", "wcodes_ajenos",
    "cuantia_coherente")


def verificar(case_dir: Path | str, fuentes: "Fuentes | None" = None) -> Informe:
    """Corre las nueve comprobaciones sobre un expediente. No escribe nada.

    Una comprobación que revienta no tumba el informe: se convierte en `fallo` con la
    excepción como detalle. Un verificador que muere a mitad deja al operador sin las
    ocho que sí podía dar, y sin saber cuál murió.
    """
    case_dir = Path(case_dir)
    # El default es el puerto CERRADO, no uno que consulte: un verificador cuyo modo
    # por defecto fuera «no preguntar y aprobar» sería peor que no tenerlo. Con
    # `SinRed`, las cinco de red salen en `fallo` diciendo que no se pudo consultar.
    if fuentes is None:
        from core.verificar_apertura_fuentes import SinRed

        fuentes = SinRed()
    # UNA consulta por fuente, repartida. Dos comprobaciones que preguntan por separado
    # pueden recibir dos fotos distintas y aprobar entre las dos un expediente al que le
    # falta un documento — medido (R1, H-02).
    ctx = _Contexto(case_dir, fuentes)
    resultados = []
    for fn in COMPROBACIONES:
        try:
            resultados.append(_llamar(fn, case_dir, ctx))
        except _ColisionDeTipo as exc:
            resultados.append(Resultado(
                id=_id_de(fn), titulo=_id_de(fn), estado=FALLO,
                detalle=f"estructura inválida del expediente: {exc}"))
        except Exception as exc:                           # noqa: BLE001
            resultados.append(Resultado(
                id=_id_de(fn), titulo=_id_de(fn), estado=FALLO,
                detalle=f"la comprobación reventó: {exc!r}"))
    return Informe(case_dir=str(case_dir), resultados=resultados)


def _llamar(fn: Callable, case_dir: Path, ctx: "_Contexto") -> Resultado:
    """Las locales toman solo `case_dir`; las de red, también `fuentes`.

    Se decide por una **marca explícita** (`@_de_red`) y no contando parámetros con
    `inspect`. La primera versión contaba, y `c5_viabilidad_completa` tiene un
    keyword-only con default (`filas_esperadas`): recibió el objeto de fuentes en su
    sitio y reventó, lo que el informe presentó como un `fallo` del expediente. Contar
    parámetros es una heurística sobre la forma, igual que buscar una cadena en un
    fichero de tests — y falla igual.
    """
    if getattr(fn, "_necesita_fuentes", False):
        return fn(case_dir, ctx)
    return fn(case_dir)


def _id_de(fn: Callable) -> str:
    """`c3_cobertura_vs_catalogo` -> `cobertura_vs_catalogo`, para que una comprobación
    que revienta conserve su identidad en el informe."""
    nombre = getattr(fn, "__name__", "?")
    return nombre.split("_", 1)[1] if re.match(r"^c\d+_", nombre) else nombre


# --- Lectores, estrictos a propósito ------------------------------------------------


def _vacio(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not str(v).strip())


def _yaml_load(texto: str) -> Any:
    import yaml

    return yaml.safe_load(texto)


def _leer_lista_de_mapas(p: Path, parse: Callable[[str], Any]) -> tuple[list[dict], str]:
    """`(filas, "")` o `([], motivo)`. **Nunca descarta en silencio** (R1 H-01).

    La primera versión filtraba con `[x for x in d if isinstance(x, dict)]`: una lista
    con basura se convertía en una lista más corta —o vacía— y el conteo podía cuadrar
    con el otro lado. Un fichero corrupto salía en verde. Ahora una entrada que no es un
    mapa es una **forma inválida**, y se dice cuántas y cuáles.
    """
    try:
        d = parse(p.read_text(encoding="utf-8"))
    except Exception as exc:                               # noqa: BLE001
        return [], f"ilegible ({type(exc).__name__})"
    if d is None:
        return [], ""
    if not isinstance(d, list):
        return [], f"no es una lista sino {type(d).__name__}"
    malas = [i for i, x in enumerate(d) if not isinstance(x, dict)]
    if malas:
        return [], (f"{len(malas)} de {len(d)} entradas no son mapas "
                    f"(posiciones {malas[:5]}): forma inválida, no se cuenta")
    return list(d), ""


def _ruta_cobertura(case_dir: Path) -> Path | None:
    sm = _sala_maquina(case_dir)
    return (sm / "_cobertura.json") if sm else None


def _normalizar(texto: str) -> str:
    """Mayúsculas, guiones Unicode a ASCII y saltos de línea unidos dentro de un código.

    La extracción de texto de un PDF parte identificadores por maquetación: un
    `W-\\n04AAAA` es el mismo W-code y era invisible (R1 H-10).
    """
    t = unicodedata.normalize("NFC", texto).upper().translate(_GUIONES)
    return re.sub(r"(W-)[\s ]+(?=[A-Z0-9])", r"\1", t)


def _wcode_del_caso(case_dir: Path) -> tuple[str | None, list[str]]:
    """`(w_code, [])`, o `(None, candidatos)` si el nombre declara más de uno.

    Se toma el que va **entre paréntesis**, que es donde lo pone el compositor del
    `case_id`. Si no hay ninguno entre paréntesis, se admite uno suelto — pero solo si
    es el único del nombre: elegir entre varios por posición es adivinar (R1 H-09).
    """
    nombre = _normalizar(case_dir.name)
    entre_parentesis = _RE_WCODE_PROPIO.findall(nombre)
    if len(entre_parentesis) == 1:
        return entre_parentesis[0], []
    if len(entre_parentesis) > 1:
        return None, sorted(set(entre_parentesis))
    sueltos = sorted(set(_RE_WCODE.findall(nombre)))
    if len(sueltos) == 1:
        return sueltos[0], []
    return None, sueltos if len(sueltos) > 1 else []
