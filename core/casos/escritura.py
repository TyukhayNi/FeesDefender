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

        **Lo que esta comprobación NO hace, y se dice aquí porque R15/H15-03 midió que la
        promesa era más ancha que el hecho:** es texto, así que no sigue enlaces ni puntos
        de reanálisis, y no reconoce que la forma corta 8.3 de una carpeta sea la misma
        carpeta. Léxico es deliberado —`resolve()` en el camino de cada escritura reabre la
        carrera que R12 cerró en el mutex— y la identidad real se comprueba **una vez** al
        construir el `Deposito`, en `deposito()`. Una junction creada dentro de la base
        *después* de esa comprobación queda fuera de alcance: es un TOCTOU declarado.
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


def _es_canon(workspace) -> bool:
    """¿La raíz de trabajo de este workspace **es** el expediente canónico?

    Se lee del **modo**, que es lo que el resolver decidió, y no de la ruta. Derivarlo de
    la ruta exigiría clasificarla otra vez —y `MEJORAS #141` acaba de medir que esa
    clasificación tiene una entrada sin validar—. El modo no depende de eso.
    """
    from .workspace_model import WorkspaceMode
    return WorkspaceMode(workspace.mode) is WorkspaceMode.DRIVE_ACTIVE


def _sin_desvio():
    """La decisión que corresponde a una copia local: escribir donde toca, sin bandeja."""
    from ..repository_checkout import DecisionEscritura
    return DecisionEscritura(
        permitido=True, desviar=False, ruta_bandeja=None, evento=None,
        motivo="copia local de trabajo: la bandeja vive en el canon (MEJORAS #96)")


def _exigir_modo_coherente_con_la_raiz(workspace, canon_dir: Path | None) -> None:
    """El modo y la raíz tienen que **concordar**, y eso no lo garantiza nadie más.

    `CaseWorkspace.__post_init__` solo exige que un modo utilizable traiga raíz; **no**
    comprueba que `DRIVE_ACTIVE` sea el canon ni que los modos locales no lo sean
    (R25/H25-03). El resolver de producción mantiene la dicotomía, pero `CaseWorkspace` es
    un valor **público**: cualquiera puede construir un `LOCAL_CHECKOUT` apuntando al canon
    y quedarse con el bypass del guard. Aquí se exige, porque aquí es donde se concede.

    ## Se compara con el canon RESUELTO, no con `CASOS_ROOT`

    La primera versión preguntaba `clasificar_bajo(raiz, config.settings.casos_root)`. Eso
    **rompió dos tests que estaban bien**: el catálogo resuelve por `case_locator._root()`
    y yo comparaba contra `settings.casos_root`, así que un caso perfectamente canónico
    caía «fuera» en cuanto las dos fuentes divergían. **Dos definiciones de «el catálogo»**
    — exactamente la clase de defecto que `MEJORAS #136` vino a cerrar, cometida al
    remediar otra cosa.

    Ahora se compara contra el directorio que **el propio catálogo devolvió** para este
    caso. Es una sola fuente y además una comprobación más fuerte: identidad del
    expediente, no contención en una raíz.
    """
    from .workspace_model import WorkspaceMode

    modo = WorkspaceMode(workspace.mode)
    raiz = _normal(Path(workspace.working_root))
    canon = _normal(canon_dir) if canon_dir is not None else None

    if modo is WorkspaceMode.DRIVE_ACTIVE:
        if canon is None or raiz != canon:
            raise ValueError(
                "un workspace `drive_active` tiene que ser el expediente canonico; esta "
                "raiz no es la que el catalogo resuelve, y concederia capacidad canonica "
                "sobre algo que no es el canon")
    elif canon is not None and raiz == canon:
        raise ValueError(
            "un workspace local no puede apuntar AL canon: eso saltaria el guard de "
            "desvio sobre el propio expediente canonico")


def _identidad_de_workspace(ref, workspace) -> tuple[str | None, Path, str | None]:
    """`(w_code, working_root, motivo)`. El workspace aporta el **destino**, no la identidad.

    ## La frontera, y escribí la contraria

    La primera versión decía que la identidad salía de `workspace.case_ref` «que el
    resolver ya validó contra el canon». **Es falso**, y R25/H25-01 lo demostró
    ejecutándolo: `CaseCatalog.localizar` cae a `case_id` sin contrastar `meta.id_go`, y
    el resolver **conserva el `CaseRef` pedido sin enriquecerlo**. Resultado medido: una
    petición con `W-FAKE01` sobre el canon de `W-REAL01` era **aceptada por la vía nueva y
    rechazada por la vieja** — o sea que mi cambio abría una puerta que el código ya tenía
    cerrada, y encima tomaba el mutex del namespace equivocado.

    **El `case_ref` de un workspace es la PETICIÓN, no la PRUEBA.** La prueba es
    `meta.id_go` del canon, y sigue estando donde siempre: en el catálogo. Que la copia
    local no lleve `_caso.md` (`MERGE_EXCLUSIONS`) no cambia dónde vive la prueba —
    cambia dónde caen los bytes, que es otra cosa.

    Así que aquí hay **una sola regla de identidad**, la misma que la vía histórica, y lo
    único que el workspace decide es la raíz de escritura. Dos reglas de identidad que
    puedan divergir es precisamente cómo nació este defecto.

    ## El caso sin canon, declarado

    Un `local_scratch` que el catálogo no conoce no tiene prueba canónica. Ahí se cae al
    par (nombre de la carpeta, petición) y **se declara** que la garantía es más débil, en
    vez de fingir que es la misma.
    """
    from . import case_locator
    from .case_catalog import CaseCatalog
    from .workspace_model import (CaseRef, IdentidadDiscordante,
                                  LocalWorkspaceMissing, WorkspaceMode)

    if WorkspaceMode(workspace.mode).es_bloqueado or workspace.working_root is None:
        raise ValueError(
            "un workspace bloqueado no autoriza ninguna escritura y no tiene raiz de "
            "trabajo; el llamador debe tratar el bloqueo, no pasarlo aqui")

    raiz = Path(workspace.working_root)
    ws_ref = getattr(workspace, "case_ref", None)

    # (1) La peticion es lo que el llamador y el workspace piden JUNTOS. Que discrepen
    #     entre si ya es discordancia: son dos identidades para una escritura.
    pedidos = {x.strip().upper()
               for x in (getattr(ws_ref, "w_code", None), getattr(ref, "w_code", None))
               if x}
    if len(pedidos) > 1:
        raise IdentidadDiscordante(
            w_code=None,
            detalle="el workspace y la referencia pedida declaran W-codes distintos; "
                    "con dos identidades hay dos lockfiles para un expediente")
    case_id = (getattr(ws_ref, "case_id", None) or getattr(ref, "case_id", None))

    # (2) La PRUEBA: `meta.id_go` del canon, por la misma via que la historica.
    try:
        canon_dir = CaseCatalog().localizar(CaseRef(case_id=case_id) if case_id else ref)
    except LocalWorkspaceMissing:
        canon_dir = None

    # La coherencia modo/raiz, con el canon YA resuelto: una sola fuente.
    _exigir_modo_coherente_con_la_raiz(workspace, canon_dir)

    if canon_dir is not None:
        id_go = (str(case_locator.read_case_meta(canon_dir).get("id_go") or "")
                 .strip().upper()) or None
        del_nombre = case_locator._w_code_de(canon_dir.name)
    else:
        id_go = None
        del_nombre = case_locator._w_code_de(raiz.name)
    del_nombre = del_nombre.strip().upper() if del_nombre else None

    # (3) La MISMA comparacion de tres fuentes que `_identidad`. Cualquier desacuerdo
    #     entre las presentes es discordancia: elegir en silencio fabrica el segundo lock.
    presentes = {x for x in (id_go, del_nombre, *pedidos) if x}
    if len(presentes) > 1:
        raise IdentidadDiscordante(
            w_code=id_go,
            detalle="el metadato canonico, la presentacion y la referencia pedida no "
                    "coinciden; con dos identidades hay dos lockfiles para un expediente")

    canon = id_go or del_nombre or (next(iter(pedidos)) if pedidos else None)
    if not canon:
        return None, raiz, ("no hay identidad canonica: ni `meta.id_go` ni el nombre de "
                            "la carpeta declaran un W-code")
    try:
        w = _w_code_valido(canon)
    except ValueError:
        # El valor crudo NO se reproduce: el §16 gobierna los mensajes.
        return None, raiz, ("la identidad declarada no cumple la gramatica que el mutex "
                            "exige, asi que no hay namespace utilizable")
    return w, raiz, None


def deposito(ref, rel_base: str, origen: str, *, clase: str,
             modo: str = "libre", raiz: Path | None = None,
             workspace=None) -> Deposito:
    """Autoriza y **efectúa** una escritura sobre el caso de `ref`.

    Args:
        ref: `CaseRef`. Su identidad se resuelve contra `meta.id_go`, no contra el nombre.
        rel_base: base relativa al caso, con `/`. La capacidad escribe **dentro** de ella.
        origen: fuente de la escritura; da nombre a la subcarpeta de la bandeja.
        clase: una de :data:`CLASES`. Gobierna la exención de desvío, nunca la de mutex.
        modo: `v1` exige el mutex; `libre` lo declara si falta (§4 del plan).
        raiz: raíz de lockfiles. `None` = la por defecto.
        workspace: `CaseWorkspace` **ya resuelto por el llamador**. `None` = el canon, que
            es la conducta de siempre.

    ## `workspace` cierra H18-01, y quién resuelve es la decisión

    Hasta hoy la base salía de `CaseCatalog().localizar(ref)`, así que **esta costura solo
    servía para el canon**: con un caso prestado a esta máquina, los bytes iban al Drive y
    no a la copia sobre la que se trabaja.

    Resolver **aquí dentro** fue el diseño de las rev. 1 y 2 de `MEJORAS #124`, y **dos
    rondas adversariales lo tumbaron** (R21 y R24, 20 hallazgos confirmados). El motivo de
    fondo, en una línea: la costura no tiene el contexto —reloj, usuario, máquina, acceso a
    Drive— y fabricarlo aquí obliga a una segunda resolución que contradice la premisa.

    **Lo resuelve el llamador**, que ya lo tiene y ya sabe tratar los errores del resolver.
    No es un patrón nuevo: `scripts/sala_maquina.py` lo hace así desde el Task 9 de la
    Fase 1.
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

    if workspace is None:
        w_code, case_dir, motivo_identidad = _identidad(ref)
    else:
        w_code, case_dir, motivo_identidad = _identidad_de_workspace(ref, workspace)

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
    #
    # Sobre una COPIA LOCAL no se consulta: la bandeja `_pendiente_checkin` vive en el
    # canon, y desviar dentro de la copia seria una bandeja dentro de la bandeja
    # (`MEJORAS #96`). El discriminante es el MODO que el llamador ya resolvio, no una
    # segunda lectura del estado — que es justo lo que R24/H24-02 demostro imposible.
    if workspace is not None and not _es_canon(workspace):
        decision = _sin_desvio()
    else:
        case_id = case_dir.name
        decision = guard_escritura(case_id, rel_base, origen,
                                   es_protocolo=(clase == "protocolo"))

    base = case_dir / (decision.ruta_bandeja if decision.desviar else rel_base)
    # Contención de la propia base: `rel_base` viene de código del repo, pero una base que
    # se saliera del caso convertiría todas las comprobaciones de `Deposito` en decorado.
    if not _bajo(base, case_dir):
        raise ValueError(
            f"la base {rel_base!r} escapa del expediente; {_normal(base)!r} no cae dentro")
    # Y la identidad REAL de la base, una sola vez, al construir (R15/H15-03).
    #
    # La comprobación de `Deposito._resolver` es **léxica** a propósito: `resolve()` consulta
    # disco y devuelve distinto según el directorio exista o no, y eso produjo una carrera
    # real en el mutex (R12). Pero léxico no ve *reparse points*: el revisor demostró que una
    # junction colocada bajo la base apunta fuera y las escrituras la atraviesan.
    #
    # El compromiso: la comprobación por disco se hace **aquí**, una vez por `Deposito`, no
    # en cada escritura. Cierra el caso realista —una base cuyo ancestro existente resuelve
    # fuera del expediente— sin poner una llamada al disco en el camino de cada byte. Lo que
    # NO cierra, y se declara: una junction creada DENTRO de la base después de construir
    # esto. Eso es un TOCTOU que una comprobación previa no puede cerrar.
    try:
        ancestro = next((p for p in [base, *base.parents] if p.exists()), None)
        if ancestro is not None and not _bajo(ancestro.resolve(), case_dir.resolve()):
            raise ValueError(
                f"la base {rel_base!r} resuelve fuera del expediente: hay un enlace o "
                f"punto de reanálisis en su camino")
    except OSError:
        # Un fallo al resolver no autoriza: si no se puede comprobar dónde cae, no se
        # entrega la capacidad. Misma polaridad que el resto de la pieza.
        raise ValueError(
            f"no se pudo comprobar dónde resuelve la base {rel_base!r}") from None

    return Deposito(clase=clase, origen=origen, desviada=bool(decision.desviar),
                    protegida_por_mutex=protegida, motivo_sin_mutex=motivo,
                    _base=base)
