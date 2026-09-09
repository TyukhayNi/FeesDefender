"""Qué fichero REPRESENTA a cada documento, y con qué calidad (invariante I5).

Esta mitad no copia: decide y reporta. 4b usará la misma decisión para copiar, y por eso
la decisión vive aquí — que la tome quien no puede escribir es justo lo que permite
revisarla sin riesgo.

Cuatro cosas que la rev. 1 tenía mal, verificadas contra ``core/sala_maquina.py``:

* **``clase`` y ``estado`` son ejes distintos.** ``metodo`` dice de dónde sale el texto;
  ``estado`` dice qué calidad tiene. La rev. 1 mezclaba ``error`` (un método) con
  ``empty``/``low``/``ok`` (estados) en una sola escala.
* **``duplicado`` y ``error`` existen** (``:1069`` y ``:1409``). El primero se resuelve por
  ``alias_de`` al espejo de su titular (``MEJORAS #147``); el segundo bloquea con su motivo.
* **El bundle es un GRUPO.** Su OCR está en ``01_OCR/<parent_slug>.pdf`` (``:1023``, con el
  slug del PADRE) y sus filas de cobertura son de segmento (``:975``). Se agrupa por
  ``parent_sha256`` y se resuelve al artefacto del padre con la peor calidad de los
  segmentos. La rev. 1 conservaba la fila de peor calidad y derivaba la ruta de SU slug:
  apuntaba a un fichero inexistente y bloqueaba teniendo el PDF íntegro al lado.
* **El SHA del crudo se cruza con la cobertura.** A la rev. 1 le bastaba que el fichero
  existiera, así que con el crudo sustituido reportaba la clase y la calidad de otros bytes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from core.sala_maquina import DocCobertura, cobertura_desde_dicts

SM_REL = "01_Procesado/02_Sala de máquina"
OCR_REL = f"{SM_REL}/01_OCR"
COBERTURA_REL = f"{SM_REL}/_cobertura.json"

#: De PEOR a mejor. Es el orden de ``sala_maquina._peor_estado``
#: (``{empty:0, sin_soporte:1, low:2, ok:3}``), no uno propio.
ORDEN_ESTADO: tuple[str, ...] = ("empty", "sin_soporte", "low", "ok")

#: Métodos que producen un PDF de custodia en ``01_OCR/<slug>.pdf``.
METODOS_CON_ARTEFACTO = frozenset({"ocr", "ofimatica"})
#: Métodos cuyo original es su propio representante.
METODOS_CRUDO = frozenset({"pypdf", "nativo", "sin_soporte", "vision"})
#: Copia byte-idéntica: su espejo es el del titular (``MEJORAS #147``).
METODO_DUPLICADO = "duplicado"
#: El documento reventó al procesarse.
METODO_ERROR = "error"


class Clase(StrEnum):
    CRUDO = "crudo"
    CONVERTIDO = "convertido"
    SIN_REPRESENTANTE = "sin_representante"


@dataclass(frozen=True)
class Eleccion:
    clase: Clase = Clase.SIN_REPRESENTANTE
    rel: str = ""
    ext: str = ""
    calidad: str = ""
    avisos: tuple[str, ...] = ()
    bloqueo: str = ""


@dataclass(frozen=True)
class GrupoBundle:
    parent_sha256: str
    parent_slug: str
    peor_estado: str
    n_segmentos: int
    #: El método del PADRE, compartido por todos los segmentos (`metodo_base` en
    #: `sala_maquina._split_o_md`). Decide si el grupo tiene artefacto o si su
    #: representante es el crudo: un bundle **digital** se parte sobre el propio PDF
    #: (`_split_o_md(..., "pypdf", False, ...)`) y **no genera** `01_OCR/<padre>.pdf`.
    metodo: str = ""


@dataclass(frozen=True)
class Cobertura:
    #: ``sha256 del documento físico -> su fila``
    por_sha: dict[str, DocCobertura] = field(default_factory=dict)
    #: ``parent_sha256 -> grupo``
    grupos: dict[str, GrupoBundle] = field(default_factory=dict)
    #: ``slug del alias -> slug del titular``
    titulares: dict[str, str] = field(default_factory=dict)
    por_slug: dict[str, DocCobertura] = field(default_factory=dict)


def _rango(estado: str) -> int:
    try:
        return ORDEN_ESTADO.index(estado)
    except ValueError:
        return -1               # desconocido: peor que el peor, y se dice


def _ext_de(rel: str) -> str:
    nombre = str(rel).replace("\\", "/").rsplit("/", 1)[-1]
    return nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""


def cargar(raiz: Path) -> Cobertura:
    """Índices de ``_cobertura.json``. Ausente = vacía; **corrupta LANZA**.

    «Cero documentos» y «no pude leerlo» no son lo mismo: confundirlos haría que la vista
    se describiera entera desde crudo creyendo que no hay sala de máquina.
    """
    p = Path(raiz) / COBERTURA_REL
    if not p.is_file():
        return Cobertura()
    filas = cobertura_desde_dicts(json.loads(p.read_text(encoding="utf-8")))

    por_sha: dict[str, DocCobertura] = {}
    por_slug: dict[str, DocCobertura] = {}
    titulares: dict[str, str] = {}
    segmentos: dict[str, list[DocCobertura]] = {}

    for f in filas:
        if f.slug:
            por_slug[f.slug] = f
        # **Un segmento se reconoce por `parent_slug`, NO por `parent_sha256`.** El
        # segundo es «sha del fichero FÍSICO de origen; clave del estado idempotente por
        # bundle» (`sala_maquina.py:196`) y el productor lo rellena **también en el camino
        # passthrough**, con `parent_slug` vacío (`:937-938`). Agrupar por él trataba un
        # documento suelto real como bundle sin padre y lo bloqueaba. El marcador de
        # segmento es `parent_slug` —«slug del bundle si es un segmento; vacío si
        # documento suelto»— y `doc_id`, que el mismo comentario define igual.
        if f.parent_slug:
            segmentos.setdefault(f.parent_sha256, []).append(f)
            continue
        if f.metodo == METODO_DUPLICADO and getattr(f, "alias_de", ""):
            titulares[f.slug] = f.alias_de
        if f.sha256:
            # **El titular gana al alias, y el empate se resuelve por slug.** Titular y
            # copia comparten SHA en el productor real, así que «la última fila gana»
            # hacía que el ORDEN del JSON decidiera: si ganaba un titular `error`,
            # bloqueaba; si ganaba su alias, degradaba a crudo (R1/H-09). Un `duplicado`
            # solo ocupa el índice si no hay titular para ese SHA.
            previo = por_sha.get(f.sha256)
            if previo is None:
                por_sha[f.sha256] = f
            elif previo.metodo == METODO_DUPLICADO and f.metodo != METODO_DUPLICADO:
                por_sha[f.sha256] = f
            elif (previo.metodo == METODO_DUPLICADO) == (f.metodo == METODO_DUPLICADO):
                # dos del mismo rango: determinista por slug, no por orden de lectura
                if (f.slug or "") < (previo.slug or ""):
                    por_sha[f.sha256] = f

    grupos: dict[str, GrupoBundle] = {}
    for sha, segs in segmentos.items():
        # `min` por rango, no «la primera en caso de empate»: el resultado no puede
        # depender del orden de las filas en el JSON.
        peor = min((s.estado for s in segs), key=_rango)
        padres = {s.parent_slug for s in segs if s.parent_slug}
        metodos = {s.metodo for s in segs if s.metodo}
        grupos[sha] = GrupoBundle(
            parent_sha256=sha,
            parent_slug=sorted(padres)[0] if padres else "",
            peor_estado=peor,
            n_segmentos=len(segs),
            # Los segmentos comparten `metodo_base`; si no lo hicieran, la cadena está
            # roja y se prefiere el orden estable a una elección arbitraria.
            metodo=sorted(metodos)[0] if metodos else "")
    return Cobertura(por_sha=por_sha, grupos=grupos, titulares=titulares,
                     por_slug=por_slug)


def _resolver_titular(cob: Cobertura, fila: DocCobertura) -> tuple[str, str]:
    """Sigue la cadena de alias hasta el titular real. ``(slug, "")`` o ``("", problema)``.

    Es un GRAFO, no un salto: el productor no promete que un alias apunte directamente al
    titular, y la R1 midió que una cadena ``copia → medio → titular`` no llegaba al PDF
    existente y que un ciclo se aceptaba como crudo (su H-09). Se recorre con cota y con
    detección de ciclos, y **falla cerrado**: un ciclo o un titular ausente bloquean, no
    degradan.
    """
    vistos: list[str] = []
    actual = fila.slug
    siguiente = cob.titulares.get(actual) or getattr(fila, "alias_de", "")
    while siguiente:
        if siguiente in vistos or siguiente == actual:
            return "", (f"la cadena de alias forma un ciclo: "
                        f"{' -> '.join(vistos + [siguiente])}")
        vistos.append(actual)
        actual = siguiente
        if len(vistos) > 32:
            return "", "la cadena de alias es demasiado larga: no se sigue"
        siguiente = cob.titulares.get(actual, "")
    if actual == fila.slug:
        return "", ("`metodo: duplicado` sin `alias_de`, así que no se sabe de qué "
                    "fichero es copia")
    return actual, ""


def _artefacto_de(raiz: Path, slug: str) -> tuple[str, bool]:
    rel = f"{OCR_REL}/{slug}.pdf"
    return rel, (Path(raiz) / rel).is_file()


def elegir(raiz: Path, cob: Cobertura, *, raw_rel: str, raw_sha256: str,
           sin_cobertura_ok: bool) -> Eleccion:
    """Qué fichero representa a este documento, o por qué no hay ninguno.

    ``raw_sha256`` es el hash **actual** del crudo, que el llamador ya calculó. Se cruza
    con la cobertura: si no coincide, la clase y la calidad que la cobertura declara son
    de otros bytes.
    """
    ext = _ext_de(raw_rel)
    avisos: list[str] = []

    # (1) ¿es un bundle? El grupo manda sobre la fila individual.
    grupo = cob.grupos.get(raw_sha256)
    if grupo is not None:
        avisos.append(f"bundle de {grupo.n_segmentos} segmentos: la calidad es la peor de "
                      f"ellos ({grupo.peor_estado})")
        # **Un bundle DIGITAL no tiene artefacto y no hay que exigírselo.** El productor
        # parte el propio PDF (`_split_o_md(..., "pypdf", False, ...)`, `:1381`) y no
        # genera `01_OCR/<padre>.pdf`: su representante es el crudo. Solo los métodos con
        # artefacto lo tienen, y a esos sí se les exige.
        if grupo.metodo in METODOS_CON_ARTEFACTO:
            if not grupo.parent_slug:
                return Eleccion(bloqueo=(
                    f"{raw_rel}: {grupo.n_segmentos} segmentos con `metodo: "
                    f"{grupo.metodo}` y sin `parent_slug`: no se puede localizar el "
                    f"artefacto del padre"))
            rel, existe = _artefacto_de(raiz, grupo.parent_slug)
            if not existe:
                return Eleccion(bloqueo=(
                    f"{raw_rel}: es un bundle de {grupo.n_segmentos} segmentos con "
                    f"`metodo: {grupo.metodo}` y su artefacto {rel} no está. Vuelve a "
                    f"correr la sala de máquina"))
            return Eleccion(clase=Clase.CONVERTIDO, rel=rel, ext="pdf",
                            calidad=grupo.peor_estado, avisos=tuple(avisos))
        if grupo.metodo in METODOS_CRUDO:
            return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext,
                            calidad=grupo.peor_estado, avisos=tuple(avisos))
        return Eleccion(bloqueo=(
            f"{raw_rel}: bundle de {grupo.n_segmentos} segmentos con `metodo: "
            f"{grupo.metodo!r}`, que el selector no cubre. No se adivina"))

    fila = cob.por_sha.get(raw_sha256)
    if fila is None:
        if not cob.por_sha and not cob.grupos:
            motivo = "la sala de máquina no ha corrido sobre este caso"
        else:
            motivo = ("el sha256 actual del crudo no aparece en la cobertura, así que la "
                      "clase y la calidad que se declararían son de otros bytes")
        if not sin_cobertura_ok:
            return Eleccion(bloqueo=(
                f"{raw_rel}: {motivo}. Corre la sala de máquina, o declara "
                f"`sin_cobertura_ok: true` en su entrada del mapa"))
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext, calidad="",
                        avisos=(f"override `sin_cobertura_ok`: {motivo}",))

    metodo = (fila.metodo or "").strip()

    # (2) duplicado: el representante es el del TITULAR, resuelto como GRAFO
    if metodo == METODO_DUPLICADO:
        titular, problema = _resolver_titular(cob, fila)
        if problema:
            return Eleccion(bloqueo=f"{raw_rel}: {problema}")
        ft = cob.por_slug.get(titular)
        avisos.append(f"copia byte-idéntica: su representante es el del titular "
                      f"{titular!r}")
        # **Se hereda la DECISIÓN del titular, no solo su ruta.** Antes se miraba si
        # existía un PDF y se degradaba a crudo si no; con eso, un titular en `error`
        # dejaba pasar su copia como si nada, y una cadena de alias no llegaba nunca al
        # PDF que sí existía (R1/H-09).
        if ft is None:
            return Eleccion(bloqueo=(
                f"{raw_rel}: su titular {titular!r} no está en la cobertura, así que no "
                f"se puede saber qué representa esta copia"))
        heredada = elegir(raiz, cob, raw_rel=f"00_Input/{ft.rel_path}",
                          raw_sha256=ft.sha256 or "", sin_cobertura_ok=sin_cobertura_ok)
        if heredada.bloqueo:
            return Eleccion(bloqueo=(
                f"{raw_rel}: es copia de {titular!r}, y su titular bloquea — "
                f"{heredada.bloqueo}"))
        if heredada.clase is Clase.CONVERTIDO:
            return Eleccion(clase=Clase.CONVERTIDO, rel=heredada.rel, ext=heredada.ext,
                            calidad=heredada.calidad,
                            avisos=tuple(avisos) + heredada.avisos)
        # el titular se representa por su propio crudo: esta copia, por el suyo
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext,
                        calidad=heredada.calidad,
                        avisos=tuple(avisos) + heredada.avisos)

    # (3) error: bloquea, pero diciendo QUÉ pasó — el remedio no es el mismo que el de
    # un método desconocido.
    if metodo == METODO_ERROR:
        return Eleccion(bloqueo=(
            f"{raw_rel}: la sala de máquina no pudo procesarlo — "
            f"{fila.nota or 'sin nota'}. No hay representante hasta arreglarlo"))

    # (4) imagen sin texto: es una foto de algo, no de una página
    if fila.estado == "empty" and ext not in {"pdf", ""}:
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext, calidad=fila.estado,
                        avisos=("imagen sin texto: el original es su mejor "
                                "representante",))

    if metodo in METODOS_CON_ARTEFACTO:
        if not fila.slug:
            return Eleccion(bloqueo=(
                f"{raw_rel}: `metodo: {metodo}` sin `slug`, no se puede derivar la ruta "
                f"del artefacto"))
        rel, existe = _artefacto_de(raiz, fila.slug)
        if not existe:
            return Eleccion(bloqueo=(
                f"{raw_rel}: `metodo: {metodo}` declara un artefacto y {rel} no existe. "
                f"No se degrada al crudo en silencio"))
        if fila.estado in ("low", "empty"):
            avisos.append(f"calidad declarada `{fila.estado}`: puede faltar texto")
        return Eleccion(clase=Clase.CONVERTIDO, rel=rel, ext="pdf",
                        calidad=fila.estado, avisos=tuple(avisos))

    if metodo in METODOS_CRUDO:
        if metodo == "sin_soporte":
            avisos.append("`sin_soporte`: ni MD ni OCR; lo abre el letrado, ningún LLM lo "
                          "lee")
        if metodo == "vision":
            avisos.append("extraído por visión: hay MD pero no PDF buscable de custodia")
        if fila.estado in ("low", "empty") and metodo != "sin_soporte":
            avisos.append(f"calidad declarada `{fila.estado}`")
        if _rango(fila.estado) < 0:
            avisos.append(f"estado `{fila.estado}` desconocido: no se le da el beneficio "
                          f"de la duda")
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext, calidad=fila.estado,
                        avisos=tuple(avisos))

    return Eleccion(bloqueo=(
        f"{raw_rel}: `metodo: {metodo!r}` no está cubierto por el selector. No se adivina: "
        f"si es un método nuevo de la sala de máquina, hay que decidir qué representa"))
