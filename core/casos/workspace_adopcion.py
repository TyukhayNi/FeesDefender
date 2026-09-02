"""Adopción de checkouts anteriores al registro (Fase 1, Task 8b — §15).

Cierra un hueco que la **R7** encontró: el Task 7 construyó el lado negativo —un
checkout propio sin entrada de registro lanza `LocalWorkspaceMissing`, «no se adopta
solo»— y nadie construía el positivo. Sin esta pieza, en cuanto `sala_maquina` resuelva
por workspace, un checkout hecho antes del registro queda **bloqueado sin vía de
desbloqueo**: existe el error y no la puerta.

## Por qué la adopción la firma una persona

Esto no es ceremonia, y conviene entender por qué antes de intentar automatizarlo.

`MERGE_EXCLUSIONS` excluye **`_caso.md`** del checkout, y el nonce del préstamo se
escribe únicamente en el `_caso.md` **del Drive** (`aplicar_lock_prestado(fm_drive, …)`).
Consecuencia: **el árbol local no lleva ni identidad ni nonce**. Nada dentro de esa
carpeta prueba que sea la copia que el lock vigente designa.

Lo que sí se puede comprobar, y esta pieza comprueba:

1. que **es un checkout** — tiene `MANIFEST_CHECKOUT.json` legible;
2. que el **lock del canon es mío** — mismo usuario y misma máquina;
3. que el **W-code del nombre** casa con la referencia pedida.

Ninguna de las tres es una prueba criptográfica de correspondencia. Por eso
`verificar_adopcion` **declara lo que no pudo verificar** (`sin_verificar`) en vez de
callarlo: la firma humana solo vale si quien firma sabe qué está firmando.

## El reparto

- `verificar_adopcion` **decide y no escribe**. Pura, con reloj e identidad inyectados.
- `adoptar` **escribe y no decide**: solo corre si la verificación dio `ok`.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .case_catalog import CaseCatalog
from .workspace_model import CaseRef, LocalWorkspaceMissing, WorkspaceError

__all__ = ["Adopcion", "AdopcionRechazada", "verificar_adopcion", "adoptar"]

_MANIFEST = "MANIFEST_CHECKOUT.json"


class AdopcionRechazada(WorkspaceError):
    """Se intentó adoptar algo que la verificación no autoriza."""

    codigo = "ADOPCION_RECHAZADA"
    descripcion = "el checkout local no cumple las condiciones de adopcion"


@dataclasses.dataclass(frozen=True)
class Adopcion:
    """El veredicto. `ok=False` **nunca** adivina: siempre trae motivo."""

    ok: bool
    motivo: str = ""
    #: Nonce del lock **del canon** — en local no hay ninguno que leer.
    nonce: str | None = None
    case_id: str | None = None
    #: Lo que NO se pudo comprobar. Se declara para que la firma humana sea una
    #: decisión informada y no un trámite.
    sin_verificar: tuple[str, ...] = ()


def verificar_adopcion(case_dir: Path, ref: CaseRef, *, usuario: str,
                       maquina: str, ahora: str) -> Adopcion:
    """¿Es adoptable esta carpeta como checkout de `ref`? **No escribe nada.**"""
    case_dir = Path(case_dir)

    if not case_dir.is_dir():
        return Adopcion(False, "la ruta indicada no existe")

    # (0) ¿Es siquiera una COPIA? `MEJORAS #136`: esta comprobación no existía, y sin
    # ella las cinco de abajo pasaban sobre el propio canon —el lock es mío, el nombre
    # casa, y `MANIFEST_CHECKOUT.json` está también en el Drive porque `cmd_checkout` lo
    # sube (§3.3)—. El resultado era adoptar el expediente canónico como si fuera la
    # copia de trabajo, y con eso el intake dejaba de desviar sobre un caso prestado.
    #
    # Va la PRIMERA a propósito: `alta` también lo rechaza, pero un rechazo allí llega
    # como excepción opaca. Aquí produce el motivo que el humano lee ANTES de firmar, que
    # es para lo que existe este comando.
    from .case_catalog import bajo_catalogo
    if bajo_catalogo(case_dir):
        return Adopcion(False, "esa ruta esta bajo el catalogo: es el expediente "
                               "canonico, no una copia de trabajo que adoptar")

    # (1) ¿Es un checkout, o una carpeta cualquiera con nombre parecido?
    manifest = case_dir / _MANIFEST
    if not manifest.is_file():
        return Adopcion(False, f"falta {_MANIFEST}: no hay prueba de que sea un checkout")
    try:
        datos = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(datos, dict) or "inventario" not in datos:
            raise ValueError("sin inventario")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError):
        return Adopcion(False, f"{_MANIFEST} ilegible o sin inventario")

    # (3) La única señal de identidad del árbol local es su nombre. Es débil, y
    # por eso NO basta por sí sola — pero una discrepancia sí descarta.
    from .case_locator import _w_code_de
    w_local = _w_code_de(case_dir.name)
    if ref.w_code and w_local and w_local.upper() != ref.w_code.upper():
        return Adopcion(False, "el W-code del nombre de la carpeta no casa con la "
                               "referencia pedida")

    # (2) La comprobación que de verdad autoriza: el canon dice que es mío.
    try:
        estado = CaseCatalog().estado_compartido(ref)
    except LocalWorkspaceMissing:
        return Adopcion(False, "el caso no esta en el catalogo: no hay lock que adoptar")

    if estado.get("estado") != "prestado":
        return Adopcion(False, "el canon no lo da por prestado: no hay checkout que "
                               "adoptar (una copia local sin lock es un scratch)")
    if estado.get("checkout_maquina") != maquina or estado.get("checkout_user") != usuario:
        return Adopcion(False, "el lock pertenece a otro titular o a otra maquina")

    return Adopcion(
        ok=True,
        motivo="checkout propio con manifest y nombre coherente",
        nonce=estado.get("checkout_nonce"),
        case_id=case_dir.name,
        # Lo que ninguna comprobación local puede cerrar, dicho en voz alta.
        sin_verificar=(
            "el nonce del lock: `_caso.md` esta en MERGE_EXCLUSIONS y el nonce solo "
            "existe en el Drive, asi que nada en esta carpeta prueba que sea la copia "
            "que el lock vigente designa",
            "la integridad del contenido frente al baseline del manifest",
        ),
    )


def adoptar(case_dir: Path, ref: CaseRef, *, registry, usuario: str,
            maquina: str, ahora: str) -> Adopcion:
    """Registra el checkout y emite `checkout_adoptado`. **El único escritor.**

    No re-decide: si `verificar_adopcion` dice que no, lanza y no toca nada.
    Idempotente — adoptar dos veces deja una entrada y un evento.
    """
    from .workspace_registry import SCHEMA_SOPORTADO, WorkspaceEntry

    veredicto = verificar_adopcion(case_dir, ref, usuario=usuario,
                                   maquina=maquina, ahora=ahora)
    if not veredicto.ok:
        raise AdopcionRechazada(w_code=ref.w_code, detalle=veredicto.motivo)

    case_dir = Path(case_dir)
    ya = [e for e in registry.buscar(ref)
          if Path(e.local_path) == case_dir and e.tipo == "checkout"]
    if ya:
        return veredicto                       # idempotente: ni entrada ni evento

    registry.alta(WorkspaceEntry(
        case_id=veredicto.case_id or case_dir.name,
        w_code=ref.w_code or "",
        canonical_ref=None,
        local_path=case_dir,
        nonce=veredicto.nonce or "",
        maquina=maquina,
        tipo="checkout",
        ultima_validacion=ahora,
        schema=SCHEMA_SOPORTADO,
    ))

    # B0-1: el rastro va con la copia que se adopta, no al canon.
    from core.intake_log import append_event
    append_event(case_dir, "checkout_adoptado", ts=ahora, actor=usuario,
                 case_id=veredicto.case_id or case_dir.name,
                 details={"maquina": maquina,
                          "sin_verificar": list(veredicto.sin_verificar)})
    return veredicto
