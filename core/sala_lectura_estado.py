"""Lector del estado de la sala de lectura de un expediente. **Solo lee.**

## De donde sale

Fila #30 (`[APER-70]`). El boton «📚 Sala de lectura» de Streamlit llamaba a
`core.sala_lectura.organizar`, y ese modulo se declara `[DEPRECADO 2026-06-18] … queda
SUPERSEDIDO por la skill `organizar-sala-lectura` … No ampliar` en su **primera linea**.
Quien pulsaba el boton eran Paola y Ana, que no tocan codigo: no podian saber que
disparaban un camino declarado muerto.

Decision de Nikolai del 2026-09-13: **gobierna la skill**. Y la skill —`SKILL.md` §modos—
«corre en claude.ai/Cowork o en Claude Code local»: **no corre desde Streamlit**, ni puede,
porque es prompt-driven y necesita un visto bueno humano sobre la propuesta de
clasificacion. De ahi la forma de este modulo: si la UI no puede **montar** la sala, lo
util que si puede hacer es **decir en que punto esta** y a quien pedir el montaje.

## Por que aqui y no en `verificar_apertura`

El veredicto sobre los cuatro artefactos ya lo da `verificar_apertura.c4_artefactos_de_la_sala`,
y aqui se **delega**, no se reimplementa: `_ARTEFACTOS_SALA` es el duenyo de «cuales son los
cuatro y donde vive cada uno», y una segunda copia de esa lista divergiria — es como
`_MD_SUBDIR` compuesto en dos sitios dejo 140 enlaces muertos (`MEJORAS #151`).

Lo que este modulo anyade sobre `c4` es lo que la UI necesita y el informe de apertura no
da: si la carpeta existe, cuantos documentos hay dentro, y el texto de la peticion.

## La propiedad que lo define

**Nada de aqui escribe.** Sustituye a un camino que escribia sobre el expediente, asi que
un `mkdir(exist_ok=True)` de mas convertiria el remedio en el mismo defecto con otra cara.
Lo fija por comportamiento `tests/test_sala_lectura_estado.py::test_leer_el_estado_no_toca_un_solo_byte`,
que sella el arbol por `sha256` —rutas incluidas, que un fichero nuevo no cambia ningun
hash— antes y despues de llamar.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from core import verificar_apertura as va
from core.email_atomize.contaminacion import w_code_de_carpeta

#: Los que `c4` busca DENTRO de la sala. El cuarto artefacto contratado —el
#: `indice_documental.yaml`— vive en `01_Procesado/`, fuera, y por eso no puede colarse
#: en el conteo de documentos. La fuente de los cuatro sigue siendo `va._ARTEFACTOS_SALA`;
#: esto es su interseccion con la sala, derivada y no transcrita.
_ARTEFACTOS_EN_LA_SALA = frozenset(
    n for n in va._ARTEFACTOS_SALA if n != va._CATALOGO
)


@dataclasses.dataclass(frozen=True)
class EstadoSala:
    """En que punto esta la sala de lectura de un expediente.

    `montada` y `n_documentos` son cosas distintas a proposito: una sala recien
    renderizada existe y esta vacia, y confundir «el paso corrio» con «el expediente
    tiene sala» es el defecto de `MEJORAS #221` —el motor imprimia «organizada» habiendo
    escrito dos de los cuatro artefactos— visto desde el otro lado.
    """
    montada: bool
    n_documentos: int
    artefactos: va.Resultado
    solicitud: str


def _sala(case_dir: Path) -> Path | None:
    """La carpeta de la sala, o `None` si no esta montada.

    Usa el mismo `_dir_estructural` que `c4` para no tener dos criterios de «existe»:
    si `01_Procesado` esta ocupado por un FICHERO, eso no es «falta una etapa», es un
    expediente roto, y la excepcion sube en vez de informar en verde (R1 H-06).
    """
    proc = va._dir_estructural(case_dir / va._PROCESADO, va._PROCESADO)
    if proc is None:
        return None
    return va._dir_estructural(proc / va._SALA_LECTURA, va._SALA_LECTURA)


def _contar_documentos(sala: Path) -> int:
    """Ficheros de la sala que son documentos del expediente.

    Se excluyen los artefactos **de la raiz de la sala**, no los de cualquier nivel: la
    exclusion es por POSICION. Un adjunto llamado `INDICE.md` dentro de la subcarpeta de
    un documento compuesto es un documento del expediente, y descontarlo por su nombre lo
    haria desaparecer del numero sin que nadie lo dijera.
    """
    return sum(
        1 for p in sala.rglob("*")
        if p.is_file()
        and not (p.parent == sala and p.name in _ARTEFACTOS_EN_LA_SALA)
    )


def _solicitud(case_dir: Path, artefactos: va.Resultado) -> str:
    """El texto que la UI ofrece para pedir el montaje de la sala.

    **Identifica por W-code y nunca por el `case_id`.** Un `case_id` es
    `BaXXX - <direccion> - (W-XXXXX) - <tipo>` y lleva la direccion del inmueble dentro,
    o sea PII de un tercero; `docs/SEGURIDAD_DATOS.md` §16 la prohibe en un mensaje, y
    este texto esta hecho para copiarse a un chat o un correo, o sea para salir de aqui.
    Sin W-code se dice que falta en vez de volcar el nombre de la carpeta: preguntar
    cuesta una linea y filtrar no se deshace.
    """
    w = w_code_de_carpeta(case_dir.name) or "(carpeta sin W-code)"
    faltan = artefactos.evidencia.get("faltan") or []
    vacios = artefactos.evidencia.get("vacios") or []
    if artefactos.estado == va.PENDIENTE:
        que = "la sala de lectura no esta montada."
    elif faltan:
        que = f"a la sala le faltan estos artefactos: {', '.join(faltan)}."
    elif vacios:
        que = f"estos artefactos de la sala estan vacios: {', '.join(vacios)}."
    else:
        que = "la sala esta completa; se pide repasarla."
    return (
        f"Caso {w}: {que}\n\n"
        "Se pide montar / completar la sala de lectura con la skill "
        "`organizar-sala-lectura`, que es el constructor que gobierna desde el "
        "2026-09-13. Corre en Cowork o en Claude Code local, no desde esta pantalla."
    )


def estado(case_dir: Path) -> EstadoSala:
    """El estado de la sala de lectura de `case_dir`. No escribe nada.

    Toma la **ruta** y no el `case_id` por la misma razon que `c4`: quien decide que copia
    del expediente es la operativa es `CaseWorkspace`, y un lector que resolviera la ruta
    por su cuenta se convertiria en un segundo selector — lo que el disenyo dual prohibe
    expresamente (`2026-07-29-feesdefender-dual-case-workspace-design.md`).
    """
    sala = _sala(case_dir)
    artefactos = va.c4_artefactos_de_la_sala(case_dir)
    return EstadoSala(
        montada=sala is not None,
        n_documentos=_contar_documentos(sala) if sala is not None else 0,
        artefactos=artefactos,
        solicitud=_solicitud(case_dir, artefactos),
    )
