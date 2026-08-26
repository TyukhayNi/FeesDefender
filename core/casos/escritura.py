"""La costura de escritura — Plan 3A, Task 2. Un sitio, dos decisiones, un destino.

El §25 de la spec de apertura midió que de **27 clases de artefacto solo 2 consultan el
guard**, y que el mutex de #247 **no lo llama nadie**. Esto es el sitio por el que pasan las
dos preguntas: *¿sostengo el mutex de este expediente?* y *¿el guard desvía esta escritura?*

## Por qué entrega una capacidad y no un `Path` (R14/H14-05)

La rev. 1 de este plan devolvía la ruta autorizada y se anunciaba como «un sitio por el que
toda escritura pasa». Era falso: era un sitio donde toda escritura **se consulta**. Un
llamador que recibe un `Path` puede componer otro, y eso no es hipotético —es literalmente
la fila #8, donde `_intake_drive_ev` pasa por el guard y luego vuelve a hashear `case_dir`—.
Aquí sale un `Deposito` que **escribe**, cuya raíz autorizada no es accesible desde fuera y
que rechaza cualquier relativa que se salga de ella.

## Por qué el mutex va ANTES del guard

`case_manager.guard_escritura` emite un evento `pendiente_checkin` en `_intake_log.jsonl`
cuando desvía, y ese evento **es la fila #13** del write-set: clase protocolo, obligada a ir
bajo mutex. Exigir el mutex después dejaría la escritura del propio guard fuera de él. El
orden no es estética; es la única forma de cerrar esa costura sin un caso especial.

## La identidad sale de `meta.id_go`, nunca del nombre de la carpeta (R14/H14-01)

Era el CRÍTICO de R14. `CaseCatalog` considera canónico `meta.id_go`; `_w_code_de` lee el
nombre de la carpeta, y el docstring de `CaseRef` dice que ese nombre «es una presentación y
no basta como identidad». Nadie comprobaba que concordaran, así que un caso cuya carpeta
dijera `(W-ABC)` y cuyo `_caso.md` declarara `id_go: W-XYZ` admitía **dos lockfiles**: dos
procesos escribiendo el mismo expediente, los dos creyéndose protegidos.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

# Se importan tres privados de `case_mutex` a propósito, y no se duplican:
#   - `_w_code_valido` tiene que ser LA MISMA gramática que nombra al lock; una copia que
#     derive convertiría «identidad válida» en dos cosas distintas.
#   - `_normal` y `_bajo` son la comprobación de contención léxica ya probada allí (y
#     léxica por una carrera real: `resolve()` consulta disco y devuelve distinto según el
#     directorio exista o no).
# El plan promete no MODIFICAR `case_mutex.py`, no ignorarlo.
from .case_mutex import _bajo, _normal, _w_code_valido

#: Las cuatro clases del §25.2. Cerrado: lo que no está aquí no puede degradar a exento.
CLASES = ("contenido", "protocolo", "derivado", "estructura")

#: Los dos modos del §24 D3. `v1` exige mutex; `libre` lo declara y lo cuenta.
MODOS = ("v1", "libre")


@dataclasses.dataclass(frozen=True)
class Deposito:
    """Capacidad de escritura sobre **una** base ya autorizada.

    No publica ningún `Path`: la raíz efectiva viaja en `_base`, privada, y la única forma
    de obtener una ruta es pedir una relativa que caiga dentro. Eso es lo que separa
    autorizar de efectuar.
    """

    clase: str
    origen: str
    desviada: bool
    protegida_por_mutex: bool
    motivo_sin_mutex: str | None
    #: Privada a propósito (frontera C8). Con un atributo público de tipo `Path` el
    #: llamador recompondría cualquier ruta y el censo del Task 7 no lo vería.
    _base: Path = dataclasses.field(repr=False, default=Path("."))

    def _resolver(self, rel: str) -> Path:
        """`_base / rel`, comprobando que no se sale. Léxico, sin tocar disco.

        Sin esta comprobación C8 sería mentira: la capacidad no expondría la raíz por un
        atributo, la regalaría por un argumento (`dir_para("..")`).
        """
        if rel is None:
            raise ValueError("la ruta relativa no puede ser None")
        candidata = self._base / str(rel)
        if not _bajo(candidata, self._base):
            raise ValueError(
                f"la ruta relativa {str(rel)!r} escapa del destino autorizado")
        return candidata

    def dir_para(self, rel: str = ".") -> Path:
        """El directorio efectivo, creado, para motores que escriben ellos mismos.

        Existe porque `rclone` y el OCR no aceptan un callback: necesitan una carpeta. Es
        la vía legítima, y la que el censo del Task 7 cuenta como uso de la costura.
        """
        destino = self._resolver(rel)
        destino.mkdir(parents=True, exist_ok=True)
        return destino

    def escribir_texto(self, rel: str, contenido: str, *,
                       encoding: str = "utf-8") -> Path:
        """Escribe texto en `rel` y devuelve dónde cayó. UTF-8 y LF, como manda el repo."""
        destino = self._resolver(rel)
        destino.parent.mkdir(parents=True, exist_ok=True)
        import io
        io.open(destino, "w", encoding=encoding, newline="\n").write(contenido)
        return destino

    def escribir_bytes(self, rel: str, contenido: bytes) -> Path:
        """Escribe bytes en `rel` y devuelve dónde cayó."""
        destino = self._resolver(rel)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        return destino


def _identidad(ref) -> tuple[str | None, Path, str | None]:
    """`(w_code utilizable | None, case_dir, motivo si no lo hay)`.

    Tres estados, no dos — y que sean tres es la corrección de R14 sobre mi propia
    enumeración: hay namespace utilizable, no hay identidad ninguna, o **hay identidad que
    el mutex no admite**. La rev. 1 solo contemplaba las dos primeras, así que la tercera
    se manifestaba como un `ValueError` crudo escapando de un validador privado.
    """
    from . import case_locator
    from .case_catalog import CaseCatalog
    from .workspace_model import IdentidadDiscordante

    case_dir = CaseCatalog().localizar(ref)
    meta = case_locator.read_case_meta(case_dir)
    id_go = (str(meta.get("id_go") or "").strip().upper()) or None
    del_nombre = case_locator._w_code_de(case_dir.name)
    del_nombre = del_nombre.strip().upper() if del_nombre else None

    # C0. Se comparan las TRES fuentes disponibles, no dos: el metadato canónico, la
    # presentación, y lo que pidió el llamador. Cualquier desacuerdo entre las presentes
    # es discordancia, porque el mutex se indexa por una sola de ellas y elegir en
    # silencio es fabricar el segundo lockfile.
    presentes = {x for x in (id_go, del_nombre, getattr(ref, "w_code", None)) if x}
    if len(presentes) > 1:
        raise IdentidadDiscordante(
            w_code=id_go,
            detalle="el nombre de la carpeta, el metadato y la referencia pedida no "
                    "coinciden; con dos identidades hay dos lockfiles para un expediente")

    canon = id_go or del_nombre
    if not canon:
        return None, case_dir, ("no hay identidad canónica: ni `meta.id_go` ni el nombre "
                                "de la carpeta declaran un W-code")
    try:
        return _w_code_valido(canon), case_dir, None
    except ValueError:
        # El valor crudo NO se reproduce en el motivo: el §16 gobierna los mensajes y un
        # W-code inventado puede llevar cualquier cosa dentro.
        return None, case_dir, ("la identidad declarada no cumple la gramática que el "
                                "mutex exige, así que no hay namespace utilizable")


def deposito(ref, rel_base: str, origen: str, *, clase: str,
             modo: str = "libre", raiz: Path | None = None) -> Deposito:
    """Autoriza y **efectúa** una escritura sobre el caso de `ref`.

    Args:
        ref: `CaseRef`. Su identidad se resuelve contra `meta.id_go`, no contra el nombre.
        rel_base: base relativa al caso, con `/`. La capacidad escribe **dentro** de ella.
        origen: fuente de la escritura; da nombre a la subcarpeta de la bandeja.
        clase: una de :data:`CLASES`. Gobierna la exención de desvío, nunca la de mutex.
        modo: `v1` exige el mutex; `libre` lo declara si falta (§4 del plan).
        raiz: raíz de lockfiles. `None` = la por defecto.
    """
    from ..case_manager import guard_escritura
    from .workspace_model import EscrituraSinMutex, IdentidadNoUtilizable
    from . import mutex_sesion

    if clase not in CLASES:
        raise ValueError(
            f"clase {clase!r} desconocida; las del §25.2 son {CLASES}. Una clase que no "
            f"se reconoce no puede degradar a exenta")
    if modo not in MODOS:
        raise ValueError(f"modo {modo!r} desconocido; los del §24 D3 son {MODOS}")

    w_code, case_dir, motivo_identidad = _identidad(ref)

    # ---- 1. El mutex, ANTES del guard. Ver el docstring del módulo.
    protegida, motivo = False, None
    if w_code is None:
        if modo == "v1":
            raise IdentidadNoUtilizable(detalle=motivo_identidad)
        motivo = motivo_identidad
    else:
        from .workspace_model import CaseRef
        # `vigente` lanza `MutexPerdido` si la teníamos y la perdimos, y eso NO se captura:
        # rechaza en los dos modos (C2). Perder no degrada a no tener.
        sesion = mutex_sesion.vigente(CaseRef(w_code=w_code), raiz=raiz)
        if sesion is None:
            if modo == "v1":
                raise EscrituraSinMutex(
                    w_code=w_code,
                    detalle="en modo v1 toda escritura va bajo el mutex del caso; "
                            "adquiérelo en el entrypoint con mutex_sesion.sostenido")
            motivo = ("este proceso no sostiene el mutex del caso: la escritura no está "
                      "protegida frente a otro proceso de esta máquina")
        else:
            protegida = True

    # ---- 2. El guard, ya dentro del mutex si lo hay.
    case_id = case_dir.name
    decision = guard_escritura(case_id, rel_base, origen,
                              es_protocolo=(clase == "protocolo"))

    base = case_dir / (decision.ruta_bandeja if decision.desviar else rel_base)
    # Contención de la propia base: `rel_base` viene de código del repo, pero una base que
    # se saliera del caso convertiría todas las comprobaciones de `Deposito` en decorado.
    if not _bajo(base, case_dir):
        raise ValueError(
            f"la base {rel_base!r} escapa del expediente; {_normal(base)!r} no cae dentro")

    return Deposito(clase=clase, origen=origen, desviada=bool(decision.desviar),
                    protegida_por_mutex=protegida, motivo_sin_mutex=motivo,
                    _base=base)
