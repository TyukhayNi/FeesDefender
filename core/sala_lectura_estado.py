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

## La propiedad que lo define, y lo que su prueba alcanza

**Nada de aqui escribe el expediente.** Sustituye a un camino que escribia sobre el, asi que
un `mkdir(exist_ok=True)` de mas convertiria el remedio en el mismo defecto con otra cara.
Lo fija por comportamiento `tests/test_sala_lectura_estado.py::test_leer_el_estado_no_toca_un_solo_byte`,
que sella el arbol —**rutas de ficheros Y de directorios**, mas el `sha256` del contenido—
antes y despues de llamar, y tiene su control positivo de `mkdir` al lado.

**Y lo que ese sello NO alcanza, dicho porque la primera version lo prometia entero:**
compara el estado final, no las operaciones, asi que no veria una escritura transitoria que
restaurase los mismos bytes, ni cambios de metadatos (`mtime`, atributos), ni efectos fuera
de `case_dir`. Tampoco cubre el **import**: importar este modulo registra modulos en
`sys.modules` y compila regex, como cualquier otro. La promesa es sobre el expediente. Los
limites los midio la R1 adversarial de la fila #30 (H-03), cuyo control positivo demostro
que el sello de la primera version daba **verde** ante un `mkdir`.
"""
from __future__ import annotations

import dataclasses
import os
from pathlib import Path

from core import verificar_apertura as va
from core.email_atomize.contaminacion import w_code_de_carpeta

#: Nombres que, **en la raiz de la sala**, no son documentos del expediente.
#:
#: Son los cuatro contratados, el catalogo INCLUIDO. La primera version lo excluia de esta
#: lista razonando que «vive en `01_Procesado/`, fuera» — y eso es cierto del motor
#: deprecado y **falso de la skill que gobierna**, que lo pone dentro junto a los otros
#: tres. Resultado: una sala recien montada por la skill contaba su propio catalogo como
#: un documento mas. Lo levanto la R1 adversarial (H-01). Como el nombre solo se descuenta
#: **en la raiz**, incluirlo aqui no pierde nada cuando vive fuera.
#:
#: Se compara en `casefold()`: en Windows `INDICE.md` e `indice.md` son el MISMO fichero,
#: asi que `c4` encuentra el artefacto por una grafia y el conteo lo sumaba como documento
#: por la otra — los dos numeros de la misma pantalla, discrepando (R1, H-05). Es la misma
#: razon por la que `core/sala_lectura.py` compara rutas con `clave_ruta`.
_ARTEFACTOS_EN_LA_SALA = frozenset(n.casefold() for n in va._ARTEFACTOS_SALA)


@dataclasses.dataclass(frozen=True)
class EstadoSala:
    """En que punto esta la sala de lectura de un expediente.

    `montada` y `n_documentos` son cosas distintas a proposito: una sala recien
    renderizada existe y esta vacia, y confundir «el paso corrio» con «el expediente
    tiene sala» es el defecto de `MEJORAS #221` —el motor imprimia «organizada» habiendo
    escrito dos de los cuatro artefactos— visto desde el otro lado.
    """
    montada: bool
    #: Documentos de la sala, o **`None` cuando no se pudo enumerar**.
    #:
    #: `None` no es cero, y la distincion la compro la R1 adversarial (H-02): `rglob`
    #: **suprime** los errores de exploracion, asi que una sala que existe pero no se deja
    #: listar —permisos, Drive a medio montar, la carpeta retirada a mitad del recorrido—
    #: devolvia `0` y la pantalla decia «0 documento(s)» con la misma cara que una sala
    #: vacia de verdad. Es [[feedback-no-lo-se-no-es-no-hay]] en una linea de UI.
    n_documentos: int | None
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


def _contar_documentos(sala: Path) -> int | None:
    """Ficheros de la sala que son documentos del expediente, o `None` si no se pudo leer.

    Se excluyen los artefactos **de la raiz de la sala**, no los de cualquier nivel: la
    exclusion es por POSICION. Un adjunto llamado `INDICE.md` dentro de la subcarpeta de
    un documento compuesto es un documento del expediente, y descontarlo por su nombre lo
    haria desaparecer del numero sin que nadie lo dijera.

    **Se recorre con `os.walk(onerror=...)` y no con `rglob`.** `rglob` se traga los
    errores de exploracion, asi que una sala ilegible devolvia `0` — indistinguible de una
    vacia (R1, H-02). Aqui cualquier error durante el recorrido aborta y devuelve `None`,
    que la pantalla dice con otras palabras. Falla **declarando**, no contando de menos.

    Lo que este numero SI cuenta, dicho porque la pantalla no puede matizarlo: todo fichero
    regular que no sea artefacto de la raiz. Eso incluye ficheros de cero bytes, auxiliares
    del sistema (`Thumbs.db`, `.DS_Store`, `desktop.ini`), ocultos y enlaces a fichero — un
    oculto puede ser prueba valida, asi que no se filtran a ciegas. No recorre directorios
    enlazados ni deduplica por contenido. Un recuento por el manifiesto, en vez de por el
    filesystem, seria mas fiel; no se hace aqui porque el manifiesto es justo el artefacto
    que hoy suele faltar.
    """
    fallo = False

    def _anota(_exc: OSError) -> None:
        nonlocal fallo
        fallo = True

    n = 0
    for dirpath, _dirnames, nombres in os.walk(sala, onerror=_anota):
        raiz = Path(dirpath) == sala
        for nombre in nombres:
            if raiz and nombre.casefold() in _ARTEFACTOS_EN_LA_SALA:
                continue
            if (Path(dirpath) / nombre).is_file():
                n += 1
    return None if fallo else n


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
