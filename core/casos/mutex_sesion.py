"""Capa reentrante sobre el mutex por caso — Plan 3A, Task 1.

Contesta una pregunta que `case_mutex` no puede contestar sola: **¿este proceso ya sostiene
el mutex de este expediente?** Sin ella, cablear el mutex es imposible, porque el dueño de
la secuencia de V1 (`--modo v1`) y las etapas que invoca —`sala_maquina` y compañía, que
además tienen que seguir corriendo sueltas— chocarían contra su propio lease: `adquirir()`
lanza `CaseBusy` ante un lease vivo **incluido el propio**.

## Propietario y prestatarios, que es la corrección de R14/H14-03

`case_mutex.tomado()` ata el hilo de latido **y la liberación** al `finally` del bloque que
adquirió. Con préstamo entre hilos eso es un defecto: si A adquiere, B se une y A sale
primero, el `finally` de A para el latido y libera el lock **con B dentro**, y otro proceso
queda autorizado a entrar mientras B escribe.

Aquí el gestor subyacente se conduce a mano —`__enter__` al primero, `__exit__` al
**último**— y la transición 1→0 rechaza uniones nuevas mientras cierra. Quien adquiere un
recurso compartido no es necesariamente quien debe cerrarlo.

## La clave es `(raíz, W-code)`, no el W-code (R14/H14-04)

Lo que nombra al lock en disco es `raiz_de_locks(raiz) / f"{W}.lock"`. Indexar solo por
W-code haría que entrar con la misma identidad bajo otra raíz se «uniese» a una sesión que
sostiene un **fichero distinto**: garantía sobre el lock equivocado. Se normaliza con la
misma función léxica con la que se compone esa ruta, así que dos grafías equivalentes de la
misma raíz son **una** sesión y dos raíces distintas son **dos**.

## Lo que esta capa NO hace

**No resuelve identidad.** Recibe un `CaseRef` que ya la trae; un `CaseRef` sin `w_code` es
un error de programación. Resolver `meta.id_go` contra el catálogo —y rechazar que el nombre
de la carpeta y el metadato discrepen— es trabajo de la costura (`escritura.py`, frontera
C0), porque ahí es donde se sabe de qué caso se está hablando.
"""
from __future__ import annotations

import contextlib
import dataclasses
import threading

from . import case_mutex
from .case_mutex import LEASE_POR_DEFECTO, SesionMutex


@dataclasses.dataclass
class _Entrada:
    """Una sesión sostenida por este proceso, y cuántos bloques dependen de ella."""

    sesion: SesionMutex
    #: El gestor de `case_mutex.tomado()` **sin cerrar**: lo cierra el último que sale.
    gestor: object
    prestatarios: int
    #: Mientras se cierra no se admiten uniones: unirse a algo que está soltándose daría
    #: una titularidad que caduca en microsegundos.
    cerrando: bool = False


#: Estado de MÓDULO, o sea del proceso. Es a propósito: el lock del sistema es del proceso,
#: así que la pregunta «¿lo tengo?» solo tiene sentido a este alcance.
_SESIONES: dict[tuple[str, str], _Entrada] = {}

#: `RLock` y no `Lock`: `_clave()` valida la raíz y podría, en el futuro, volver a entrar.
_CANDADO = threading.RLock()


def _w_code_resuelto(ref) -> str:
    """El W-code canónico de un `CaseRef` **ya resuelto**. Sin adivinar.

    Falla cerrado y con el nombre de la variable en el mensaje, porque el llamador típico
    de este error es código nuevo que pasó un `case_id` creyendo que aquí se resolvería.
    """
    w = getattr(ref, "w_code", None)
    if not w:
        raise ValueError(
            "CaseRef sin w_code: esta capa no resuelve identidad. Resuelve el caso contra "
            "el catálogo (meta.id_go) y pasa el CaseRef resuelto; el nombre de la carpeta "
            "no es identidad")
    return case_mutex._w_code_valido(w)


def _clave(ref, raiz) -> tuple[str, str]:
    """`(raíz normalizada, W-code canónico)` — lo mismo que nombra al lock.

    `raiz_de_locks` valida además que la raíz no caiga bajo `CASOS_ROOT` ni bajo el repo,
    así que calcular la clave es también el sitio donde una raíz ilegal se rechaza: antes
    de tocar disco y antes de registrar nada.
    """
    return (case_mutex._normal(case_mutex.raiz_de_locks(raiz)), _w_code_resuelto(ref))


def vigente(ref, *, raiz=None) -> SesionMutex | None:
    """La sesión que **este proceso** sostiene para este caso, revalidada contra el disco.

    Distingue **tres** estados, y que sean tres es el contrato:

    - `None` — nunca la tuve. La costura puede decidir qué hacer con eso según el modo.
    - la sesión — la tengo *ahora*, comprobado contra el fichero y contra el lease.
    - `MutexPerdido` — **la tuve y la perdí**. No es lo mismo que no tenerla: colapsar los
      dos en `None` haría que una pérdida a mitad de operación se tratase como «aquí nunca
      hubo mutex», que en modo `libre` significa «escribe y cuéntalo» en vez de «para».
    """
    from .workspace_model import MutexPerdido

    clave = _clave(ref, raiz)
    with _CANDADO:
        entrada = _SESIONES.get(clave)
        if entrada is None:
            return None
        sesion = entrada.sesion
    # La revalidación toca disco, así que se hace FUERA del candado: retenerlo aquí
    # bloquearía a cualquier otro W-code del proceso durante una lectura de fichero.
    if not sesion.revalidar():
        raise MutexPerdido(
            w_code=clave[1],
            detalle="la sesión de este proceso ya no es titular del lock")
    return sesion


@contextlib.contextmanager
def sostenido(ref, *, ahora_fn, raiz=None, lease_seconds: int = LEASE_POR_DEFECTO):
    """Sostiene el mutex del caso, uniéndose si este proceso ya lo tiene.

    `ahora_fn` es un **callable** y se pasa explícitamente: `case_mutex` rechaza a propósito
    un instante sin offset, y el reloj mayoritario del repo (`now_iso`) es naïve —43 usos
    frente a 5 de `now_iso_utc`—. Ningún módulo hereda el reloj del suyo.
    """
    from .workspace_model import MutexPerdido

    clave = _clave(ref, raiz)
    w = clave[1]

    with _CANDADO:
        entrada = _SESIONES.get(clave)
        if entrada is not None and entrada.cerrando:
            raise MutexPerdido(
                w_code=w,
                detalle="la sesión está soltándose: no se admiten uniones nuevas")
        if entrada is not None:
            # Revalidar ANTES de contar: una unión que falla no puede dejar la cuenta
            # inflada, o el lock no se liberaría nunca.
            if not entrada.sesion.revalidar():
                raise MutexPerdido(
                    w_code=w,
                    detalle="no se puede unir a una sesión que ya no es titular; "
                            "adquirir otra aquí serían DOS escritores con nonce válido")
            entrada.prestatarios += 1
        else:
            # Se adquiere con el candado tomado, y eso reduce la concurrencia a propósito.
            # No hay ciclo posible: para que otro hilo de este proceso retuviera este lock
            # tendría que haber pasado por aquí, y entonces habría una entrada en el mapa
            # y esta rama no se ejecutaría. La vía que sí lo rompería —`case_mutex.tomado`
            # en crudo desde producción— es la que prohíbe el guard del Task 7.
            gestor = case_mutex.tomado(w, ahora_fn=ahora_fn, raiz=raiz,
                                       lease_seconds=lease_seconds)
            sesion = gestor.__enter__()
            entrada = _Entrada(sesion=sesion, gestor=gestor, prestatarios=1)
            _SESIONES[clave] = entrada

    fallo: BaseException | None = None
    try:
        yield entrada.sesion
    except BaseException as exc:                          # noqa: BLE001 - se reenvía
        fallo = exc
        raise
    finally:
        with _CANDADO:
            entrada.prestatarios -= 1
            ultimo = entrada.prestatarios <= 0
            if ultimo:
                entrada.cerrando = True
        if ultimo:
            try:
                if fallo is not None:
                    # Se le pasa el error del cuerpo para que `tomado` sepa que hubo uno:
                    # de eso depende su R11/H11-03 —el error del cuerpo manda— y su
                    # R12/H12-04 —la pérdida se anota en él en vez de evaporarse—.
                    entrada.gestor.__exit__(type(fallo), fallo, fallo.__traceback__)
                else:
                    entrada.gestor.__exit__(None, None, None)
            except BaseException:                         # noqa: BLE001
                if fallo is None:
                    # Sin error del cuerpo, lo que salga de aquí ES la noticia: el mutex se
                    # perdió durante la operación. Que suba.
                    raise
                # Con error del cuerpo, `tomado` reenvía ese mismo error y ya lo llevamos
                # en vuelo con la nota de pérdida añadida. Volver a lanzarlo aquí no añade
                # nada y taparía el `raise` de arriba.
            finally:
                with _CANDADO:
                    _SESIONES.pop(clave, None)
        else:
            # **Un prestatario que NO es el último también tiene que enterarse** (R15/H15-02).
            #
            # Antes, solo quien llevaba la cuenta a cero llamaba al gestor, así que solo él
            # veía la pérdida. Medido por el revisor con dos prestatarios: el latido murió,
            # el lease caducó, **otro proceso adquirió**, y el primer prestatario salió con
            # éxito. Eso no es un mensaje pobre: es una falsa garantía de exclusión, que es
            # justo el daño que esta capa existe para impedir.
            #
            # Es la misma clase que R11/H11-02 —la pérdida silenciosa— reaparecida en la
            # capa que construí ENCIMA del arreglo de R11. Cerrar la pérdida para el
            # titular no la cierra para quien le pide prestado.
            if entrada.sesion.perdido():
                if fallo is None:
                    from .workspace_model import MutexPerdido
                    raise MutexPerdido(
                        w_code=entrada.sesion.w_code,
                        detalle="el mutex se perdió mientras este préstamo estaba dentro; "
                                "otro proceso pudo entrar") from entrada.sesion._causa
                # Con error del cuerpo en vuelo, el error del cuerpo manda: la pérdida se
                # anota en él para que no se evapore, igual que hace `tomado`.
                fallo.add_note(
                    "[mutex] además, el mutex se perdió durante este préstamo: otro "
                    "proceso pudo entrar")
