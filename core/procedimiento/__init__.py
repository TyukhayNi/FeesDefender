"""Vista procesal de `05_Procedimiento` — pieza 4a: la mitad que solo lee.

**No hay ruta de escritura en este paquete.** La única capacidad que se exige es
``READ_CASE``, y la autoridad la da el *resolver* del workspace, no el catálogo
(invariante I0). Lo vigila `tests/test_procedimiento_sin_escritura.py`, que falla si
aparece una llamada que escriba o si algún módulo pide una capacidad de escritura.

La mitad que publica ficheros en la vista —journal de intención, ledger de propiedad,
transacción e índice— es la pieza **4b**, y se planifica aparte con sus dos rondas de
revisión adversarial. El diseño de las dos está en
``docs/superpowers/plans/2026-09-09-vista-procesal-pieza4.md``.
"""
from __future__ import annotations

from pathlib import Path

from . import artefacto, borrador, carpetas, mapa, sede, universo, vista
from . import vista as _vista

__all__ = ["informe", "borrador_mapa", "artefacto", "borrador", "carpetas", "mapa",
           "sede", "universo", "vista"]


def _resolver(case_id: str | None, case_dir: str | None):
    """Workspace autorizado para leer este caso.

    La resolución **y la autorización** vienen del mismo sitio, que es el patrón que
    `sala_maquina` ya adoptó: el mutex local no dice nada sobre si el caso está prestado a
    otra máquina, y el catálogo tampoco.
    """
    import getpass
    import socket

    from core.casos.case_catalog import CaseCatalog
    from core.casos.case_locator import resolve_ref
    from core.casos.workspace_model import CaseRef
    from core.casos.workspace_registry import WorkspaceRegistry
    from core.casos.workspace_resolver import CaseWorkspaceResolver
    from core.utils import now_iso

    if bool(case_id) == bool(case_dir):
        raise ValueError(
            "hay que dar exactamente uno: la identidad del caso o `case_dir`")

    resolver = CaseWorkspaceResolver(
        CaseCatalog(), WorkspaceRegistry(), usuario=getpass.getuser(),
        maquina=socket.gethostname(), ahora=now_iso())
    if case_dir:
        ws = resolver.resolver_por_ruta(Path(case_dir), drive_accesible=True)
        return (ws.case_ref.case_id or Path(case_dir).name), ws
    cid = resolve_ref(str(case_id))
    ws = resolver.resolver_por_identidad(CaseRef(case_id=cid), drive_accesible=True)
    return cid, ws


def informe(case_id: str | None = None, expediente_id: str = "", *,
            case_dir: str | None = None) -> "_vista.Informe":
    """Qué hay en el procedimiento, qué falta y qué bloquea. **No escribe nada.**"""
    case_id, ws = _resolver(case_id, case_dir)
    raiz = sede.raiz_autorizada(ws)
    c = universo.leer(case_id, expediente_id)
    return _vista.construir(raiz, case_id, expediente_id,
                              m=mapa.cargar(raiz), c=c,
                              cob=artefacto.cargar(raiz),
                              incoherencias=universo.incoherencias(c))


def borrador_mapa(case_id: str | None = None, expediente_id: str = "", *,
                  case_dir: str | None = None) -> str:
    """YAML de partida para el mapa. **No escribe nada:** se devuelve como texto."""
    case_id, ws = _resolver(case_id, case_dir)
    sede.raiz_autorizada(ws)       # se exige READ_CASE aunque no se lea el árbol
    return borrador.proponer(universo.leer(case_id, expediente_id))
