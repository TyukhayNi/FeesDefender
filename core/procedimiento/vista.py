"""La vista procesal descrita: qué hay, qué falta, qué bloquea. **No escribe nada.**

El módulo se llama `vista` y no `informe` porque la fachada expone una función
`procedimiento.informe(...)`, y un módulo y una función con el mismo nombre en el
mismo paquete se tapan: `from core.procedimiento import informe` devolvía la función.
La colisión obliga a la distinción correcta — la VISTA es la cosa, el INFORME es lo
que se dice de ella.

Lo no asignado se mide contra el **universo** (``listadas``), no contra lo que se bajó: la
rev. 1 lo medía contra ``materializadas`` y por tanto ocultaba justo lo que el CRM tiene y
el caso no. Ver el invariante I4.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from . import artefacto as art
from . import mapa as mp
from .carpetas import CARPETAS_FASE
from .sede import SedeError, contener


@dataclass(frozen=True)
class Fila:
    """Un documento de la vista. El orden de los campos es el de construcción."""

    logical_key: str
    carpeta: str
    destino: str
    origen: str
    doc_id: str | None
    clase: str
    rel_origen: str
    calidad: str
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Informe:
    case_id: str
    expediente_id: str
    filas: tuple[Fila, ...] = ()
    sin_asignar: tuple[str, ...] = ()
    solo_listadas: tuple[str, ...] = ()
    incoherencias: tuple[str, ...] = ()
    bloqueos: tuple[str, ...] = ()

    @property
    def por_carpeta(self) -> dict[str, list[Fila]]:
        out: dict[str, list[Fila]] = {c: [] for c in CARPETAS_FASE}
        for f in self.filas:
            out.setdefault(f.carpeta, []).append(f)
        for v in out.values():
            v.sort(key=lambda f: f.destino)
        return out

    @property
    def completo(self) -> bool:
        """Todo lo asignado, nada bloqueando, **y el universo coherente**.

        Las incoherencias cuentan, y esto es una corrección de la R1 (su H-12): sin
        ellas, un informe podía imprimir «el `pull_state` dice 99 documentos y el registro
        enumera 1» **y a la vez** «completo: sí», con el CLI saliendo con 0. Una
        automatización habría tomado eso por completitud sin conocer los otros 98.

        «Todas las filas que conozco tienen carpeta» no es «conozco todo lo que el CRM
        tiene». Lo primero es lo que se sabía; lo segundo es lo que se afirmaba.

        **No** dice que la vista esté publicada: esta mitad no publica.
        """
        return not self.sin_asignar and not self.bloqueos and not self.incoherencias


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def construir(raiz: Path, case_id: str, expediente_id: str, *, m: mp.MapaProcesal,
              c, cob: art.Cobertura,
              incoherencias: tuple[str, ...] = ()) -> Informe:
    """El informe. ``incoherencias`` las calcula el llamador con ``universo.incoherencias``.

    Se pasan como parámetro y no se calculan aquí a propósito: ``construir`` recibe ``c``
    ya leído —los tests lo inyectan— y hacerle llamar a ``incoherencias`` lo ataría al
    módulo que lo produce. ``Conjuntos`` **no** tiene un atributo ``incoherencias``.
    """
    raiz = Path(raiz)
    bloqueos: list[str] = []
    filas: list[Fila] = []

    if str(m.expediente_crm) != str(expediente_id):
        return Informe(case_id, str(expediente_id), bloqueos=(
            f"el mapa declara `expediente_crm: {m.expediente_crm!r}` y se pidió "
            f"{expediente_id!r}",))

    ecos: dict[str, str] = {}
    for e in m.entradas:
        if e.origen == mp.ORIGEN_DESPACHO and e.eco_crm:
            ecos[e.eco_crm] = e.logical_key

    # Puerta 7-bis del spec: un eco es una afirmación sobre el CRM y puede ser falsa. La
    # rev. 1 usaba `eco_crm` para excluir un doc_id de lo pendiente sin validar que ese
    # doc_id existiera, así que un eco equivocado ocultaba un documento real.
    for doc_id, clave in sorted(ecos.items()):
        if doc_id not in c.listadas:
            bloqueos.append(
                f"{clave}: declara `eco_crm: {doc_id!r}` y el CRM no enumera ese documento "
                f"en el expediente {expediente_id}")

    asignados: set[str] = set()
    for e in m.entradas:
        if e.origen == mp.ORIGEN_DESPACHO:
            try:
                destino = contener(raiz, "05_Procedimiento", e.carpeta, e.fichero or "")
            except SedeError as exc:
                bloqueos.append(f"{e.logical_key}: {exc}")
                continue
            if not destino.is_file():
                bloqueos.append(
                    f"{e.logical_key}: `origen: despacho` declara {e.fichero!r} en "
                    f"{e.carpeta!r} y el fichero no está ahí")
                continue
            filas.append(Fila(e.logical_key, e.carpeta, e.fichero or "", e.origen, None,
                              "despacho",
                              str(destino.relative_to(raiz)).replace("\\", "/"), "", ()))
            continue

        asignados.add(e.doc_id or "")
        rev = c.materializadas.get(e.doc_id or "")
        if rev is None:
            if (e.doc_id or "") in c.solo_listadas:
                bloqueos.append(
                    f"{e.logical_key}: el CRM lo enumera pero no está en disco (ocurrencia "
                    f"`listada`, no `materializada`). Bájalo con "
                    f"`sync_sudespacho intake-judicial --full`")
            else:
                bloqueos.append(
                    f"{e.logical_key}: sin ocurrencia en el registro de este expediente")
            continue

        try:
            crudo = contener(raiz, "00_Input", str(rev["path"]))
        except SedeError as exc:
            bloqueos.append(f"{e.logical_key}: {exc}")
            continue
        if not crudo.is_file():
            bloqueos.append(
                f"{e.logical_key}: la ruta de origen no existe: 00_Input/{rev['path']}")
            continue

        eleccion = art.elegir(raiz, cob, raw_rel=f"00_Input/{rev['path']}",
                              raw_sha256=_sha(crudo),
                              sin_cobertura_ok=e.sin_cobertura_ok)
        if eleccion.bloqueo:
            bloqueos.append(f"{e.logical_key}: {eleccion.bloqueo}")
            continue
        nombre = mp.presupuesto_longitud(raiz, e.carpeta,
                                         mp.nombre_destino(e, eleccion.ext))
        filas.append(Fila(e.logical_key, e.carpeta, nombre, e.origen, e.doc_id,
                          str(eleccion.clase), eleccion.rel, eleccion.calidad,
                          eleccion.avisos))

    # Lo no asignado se mide contra el UNIVERSO (I4), no contra lo materializado.
    sin_asignar = tuple(
        f"{d} ({(r.get('filename') or '?')}, lote {r.get('modified_at') or '?'}"
        f"{', no descargado' if d in c.solo_listadas else ''})"
        for d, r in sorted(c.listadas.items())
        if d not in asignados and d not in ecos)

    return Informe(case_id, str(expediente_id), tuple(filas), sin_asignar,
                   tuple(sorted(c.solo_listadas)), tuple(incoherencias),
                   tuple(bloqueos))
