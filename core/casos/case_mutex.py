"""Mutex interproceso por caso — decisión D2 del §24 de la spec de apertura.

Contesta una sola pregunta: **¿puede este proceso operar ahora sobre este expediente?**
Ámbito **una máquina**: entre máquinas sigue el lock de checkout del Drive, con sus seis
defectos declarados.

**La primitiva es bloqueo NATIVO, no `O_CREAT|O_EXCL`** (§0.2 del plan): en Windows
`filelock` abre con `O_CREAT|O_TRUNC` y bloquea con `msvcrt.locking`. Se elige a
propósito: un lock nativo se suelta solo cuando el proceso muere, y un fichero creado
con `O_EXCL` sobrevive al cadáver y exige limpieza que nadie puede garantizar.

## Las tres validaciones de entrada, y por qué van antes de tocar disco

Las tres cierran críticos de la revisión R10, y las tres comparten forma: una API que
**acepta y persiste** un valor que rompe la exclusión es peor que una que lanza.

- `_instante()` — un timestamp sin zona se lee en hora **local**. Medido: hay 7.200 s
  entre `2026-08-25T12:00:00` y `...Z`, y con eso el segundo proceso da por vencido el
  lease del primero al instante.
- `_lease_valido()` — `int(0.5)` es `0` y `-1` vence siempre.
- `_w_code_valido()` — sin gramática cerrada, `..\\escape` compone una ruta **fuera** del
  registro.
"""
from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import secrets
import threading
import re
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path

_RE_W_CODE = re.compile(r"^W-[A-Z0-9]{3,20}$")

#: UUID de ESTE proceso, generado al importar: estable durante su vida y distinto para
#: cualquier otro. Sustituye al `boot_id` derivado del reloj (R10/H10-07), que `psutil`
#: declara sensible a ajustes de hora, NTP e hibernación.
_PROCESO_UID = uuid.uuid4().hex

#: Version del formato del lock en disco. Un lock de otra version NO se adivina.
SCHEMA_MUTEX = 1

#: Desvio maximo admitido entre el `ahora` que pasa el llamador y el reloj del sistema.
#: Diez minutos: holgado para relojes desincronizados y muy por debajo de cualquier lease
#: util. Existe porque el reloj es INYECTADO (R11/H11-01): sin cota, un llamador con un
#: bug —o una maquina con la hora disparatada— pasa `2099-01-01` y se lleva por delante
#: el lease de un proceso que sigue trabajando.
DESVIO_MAXIMO_SEGUNDOS = 600


def _ahora_del_sistema() -> float:
    """Costura: el reloj real, como referencia para acotar el desvio.

    Es lo unico de este modulo que mira el reloj, y solo para DESCONFIAR del `ahora`
    ajeno, no para decidir nada. La inyeccion del §7 se conserva: quien decide sigue
    siendo el `ahora` del llamador, dentro de una cota.
    """
    return datetime.now(timezone.utc).timestamp()


def _sin_desvio_absurdo(ts: str) -> float:
    """`_instante(ts)`, y ademas: que no se aleje del reloj del sistema en NINGUNA
    direccion (R11/H11-01 + R12/H12-01).

    **La cota es simetrica, y que no lo fuera es la tercera vez que cierro media
    frontera.** R10 dijo «naive o futuro» y cerre el naive. R11 cerro el futuro. Y el
    pasado seguia abierto: `adquirir` con `ahora="2000-01-01"` publica un lease que
    **nace vencido**, asi que el llamador recibe su nonce, se cree titular y cualquier
    otro proceso entra al instante. El daño es identico al del futuro; solo cambia el
    signo.
    """
    momento = _instante(ts)
    desvio = momento - _ahora_del_sistema()
    if abs(desvio) > DESVIO_MAXIMO_SEGUNDOS:
        hacia = "el futuro" if desvio > 0 else "el pasado"
        raise ValueError(
            "el instante " + repr(ts) + " se aleja mas de "
            + str(DESVIO_MAXIMO_SEGUNDOS) + " s hacia " + hacia + " respecto del reloj "
            "del sistema: hacia el futuro robaria el lease de un titular vivo, y hacia "
            "el pasado publicaria un lease ya vencido")
    return momento


def _instante(ts: str) -> float:
    """Epoch de un ISO-8601 **con offset explícito**. Sin offset, lanza.

    `datetime.timestamp()` interpreta un datetime naïve en hora **local**. El reloj
    mayoritario del repo (`core.utils.now_iso`) es naïve: quien cablee esta primitiva
    tiene que pasar `now_iso_utc()`, no heredar el de su módulo.
    """
    momento = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if momento.tzinfo is None or momento.utcoffset() is None:
        raise ValueError(
            f"el instante {ts!r} no lleva offset de zona: sin él se leería en hora "
            f"local y el lease se calcularía mal")
    return momento.timestamp()


def _lease_valido(valor) -> int:
    """`int` estricto y positivo. `bool` y `float` se rechazan (R10/H10-03).

    `bool` explícitamente porque es subclase de `int`: `_lease_valido(True)` daría `1`
    y un lease de un segundo silencioso.
    """
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise TypeError(f"lease_seconds debe ser int, no {type(valor).__name__}")
    if valor <= 0:
        raise ValueError(f"lease_seconds debe ser positivo, no {valor}")
    return valor


def _w_code_valido(w_code: str) -> str:
    """Canónico en mayúsculas. Nada que pueda escapar de la raíz (R10/H10-08)."""
    canon = str(w_code or "").strip().upper()
    if not _RE_W_CODE.match(canon):
        raise ValueError(
            f"{w_code!r} no es un W-code: se espera W- seguido de 3-20 alfanuméricos. "
            f"Un valor libre acabaría componiendo una ruta fuera del registro")
    return canon


@dataclasses.dataclass(frozen=True)
class ProcesoID:
    """Quién soy. **Diagnóstico**: la titularidad la decide el nonce (§0.2).

    Al remediar R10/H10-07 apareció que este bloque no gobierna nada — `renovar` y
    `liberar` comparan nonce—, así que no hacía falta un identificador de arranque
    estable, sino admitir para qué sirve: para que un humano sepa quién tiene el caso.
    """

    host: str
    pid: int
    proceso_uid: str

    def a_json(self) -> dict:
        return {"host": self.host, "pid": self.pid, "proceso_uid": self.proceso_uid}

    def es_el_mismo(self, otro: dict | None) -> bool:
        if not isinstance(otro, dict):
            return False
        return (otro.get("host") == self.host and otro.get("pid") == self.pid
                and otro.get("proceso_uid") == self.proceso_uid)


def identidad_proceso() -> ProcesoID:
    return ProcesoID(host=socket.gethostname(), pid=os.getpid(),
                     proceso_uid=_PROCESO_UID)


# --------------------------------------------------------------- estado en disco

#: Los campos que un lock DEBE traer. Se comprueban todos: la rev. 1 solo validaba que
#: el nivel superior fuera un `dict`, asi que `{}` pasaba y reventaba mas tarde con un
#: `KeyError` sin codigo — o sea, sin que nadie supiera que el lock estaba roto.
_CAMPOS = ("schema", "propietario", "nonce", "acquired_at", "renewed_at",
           "lease_seconds")


def _normal(p: Path) -> str:
    """Forma canonica LEXICA de una ruta: sin tocar el disco.

    `os.path.normcase(os.path.abspath(...))` es puro texto, asi que da lo mismo con el
    directorio creado o sin crear. Es el mismo patron que usa `workspace_registry._bajo`.
    """
    return os.path.normcase(os.path.abspath(str(p)))


def _bajo(candidata: Path, raiz: Path) -> bool:
    """¿`candidata` cae dentro de `raiz`? Por COMPONENTES, no por prefijo de cadena.

    `CASOS_x` no esta bajo `CASOS` aunque su nombre empiece igual.
    """
    c, r = _normal(candidata), _normal(raiz)
    return c == r or c.startswith(r + os.sep)


def raiz_de_locks(raiz: Path | None = None) -> Path:
    """La raiz de los lockfiles, **validada aqui**.

    La rev. 1 del plan decia que el mutex «hereda» la barrera de `WorkspaceRegistry`, y
    era falso (R10/H10-08): nunca construye un registro, llama a `raiz_por_defecto()`
    directamente y esa funcion acepta el override de entorno sin comprobar nada.

    No puede vivir bajo `CASOS_ROOT` —`list_cases()` lo veria y un checkin lo subiria al
    Drive— ni bajo el repo, donde `git status` acabaria commiteandolo.
    """
    from .. import config
    from .workspace_model import WorkspaceUnderCatalogRoot

    if raiz is None:
        from .workspace_registry import raiz_por_defecto
        raiz = raiz_por_defecto()
    # `abspath` y NO `resolve()`, y esto lo compro una carrera real: `Path.resolve()`
    # consulta el sistema de ficheros y devuelve una cadena DISTINTA segun el directorio
    # exista o no (en Windows, la forma larga frente a la que le pasaste). Con dos
    # procesos creando la raiz a la vez, el mismo argumento resolvia distinto en cada
    # uno y la comprobacion de contencion de abajo rechazaba una ruta legitima. Una
    # comprobacion de seguridad no puede depender de quien haya llegado antes.
    raiz = Path(os.path.abspath(str(raiz)))
    # DOS formas de la misma raiz, y hacen falta las dos (R11/H11-05):
    #   - la lexica, que es la que se devuelve y con la que compara `ruta_del_lock`;
    #   - la RESUELTA, porque una junction al repo pasa el filtro lexico sin problema.
    # La resolucion vive AQUI y no en `ruta_del_lock` a proposito: alli reabriria la
    # carrera que reventaba con dos procesos creando la raiz a la vez.
    formas = {raiz}
    try:
        formas.add(raiz.resolve())
    except OSError:                                      # pragma: no cover - defensivo
        pass
    for prohibida, motivo in ((Path(config.settings.casos_root), "CASOS_ROOT"),
                              (Path(config.settings.project_root), "el repo")):
        candidatas = {Path(os.path.abspath(str(prohibida)))}
        try:
            candidatas.add(prohibida.resolve())
        except OSError:                                  # pragma: no cover - defensivo
            pass
        for forma in formas:
            for candidata in candidatas:
                if _bajo(forma, candidata):
                    raise WorkspaceUnderCatalogRoot(
                        detalle=f"el mutex no puede vivir bajo {motivo}")
    return raiz


def ruta_del_lock(w_code: str, *, raiz: Path | None = None) -> Path:
    """`<raiz>/<W-CODE>.lock`, con la contencion COMPROBADA tras resolver.

    Validar la gramatica del W-code no basta por si solo: se comprueba ademas que la
    ruta resuelta siga siendo hija directa de la raiz. Son dos redes para el mismo
    escape porque el revisor demostro que un W-code con `..` salia de la raiz.
    """
    base = raiz_de_locks(raiz)
    candidata = base / f"{_w_code_valido(w_code)}.lock"
    if _normal(candidata.parent) != _normal(base):
        raise ValueError("la ruta del lock escapa de la raiz del registro")
    return candidata


def _validar_estado(crudo, w_code: str) -> dict:
    """Esquema completo. Un lock a medias es un lock roto, no un lock permisivo."""
    from .workspace_model import MutexIlegible

    def malo(por_que: str):
        return MutexIlegible(w_code=w_code, detalle=por_que)

    if not isinstance(crudo, dict):
        raise malo("el lock no contiene un objeto")
    faltan = [c for c in _CAMPOS if c not in crudo]
    if faltan:
        raise malo(f"al lock le faltan campos: {faltan}")
    sobrantes = sorted(set(crudo) - set(_CAMPOS))
    if sobrantes:
        # Politica EXPLICITA (R12/H12-05): un lock con campos que esta version no conoce
        # se rechaza. La compatibilidad hacia delante se lleva subiendo `SCHEMA_MUTEX`,
        # no aceptando en silencio lo que no se entiende.
        raise malo("el lock trae campos desconocidos: " + str(sobrantes))
    # `type(...) is int` y no `isinstance` a proposito: `True == 1` en Python, asi que
    # `schema: true` colaba como version 1 (R12/H12-05).
    if type(crudo["schema"]) is not int or crudo["schema"] != SCHEMA_MUTEX:
        # No se adivina, igual que `WorkspaceRegistry` con `SchemaNoSoportado`: un lock
        # escrito por una version que no conocemos puede significar cualquier cosa, y
        # «cualquier cosa» no es base para autorizar una escritura (R11/H11-04).
        raise malo("schema " + repr(crudo["schema"]) + " != " + str(SCHEMA_MUTEX))
    propietario = crudo["propietario"]
    if not isinstance(propietario, dict):
        raise malo("el propietario no es un objeto")
    faltan_prop = [c for c in ("host", "pid", "proceso_uid") if not propietario.get(c)]
    if faltan_prop:
        # `{}` cumplia «es un dict» y pasaba. Un propietario vacio no identifica a nadie,
        # asi que el `CaseBusy` saldria sin decir quien tiene el caso.
        raise malo("al propietario le faltan campos: " + str(faltan_prop))
    # Y sus TIPOS: el propietario alimenta el diagnostico de `CaseBusy`, asi que un
    # `host: 7` o un `proceso_uid: ["u"]` producen un mensaje que no identifica a nadie.
    if type(propietario["host"]) is not str:
        raise malo("el host del propietario no es texto")
    if type(propietario["pid"]) is not int or propietario["pid"] <= 0:
        raise malo("el pid del propietario no es un entero positivo")
    if type(propietario["proceso_uid"]) is not str:
        raise malo("el proceso_uid del propietario no es texto")
    if not isinstance(crudo["nonce"], str) or not crudo["nonce"]:
        raise malo("el nonce esta vacio o no es texto")
    try:
        _lease_valido(crudo["lease_seconds"])
        _instante(crudo["acquired_at"])
        _instante(crudo["renewed_at"])
    except (TypeError, ValueError) as exc:
        raise malo(f"campo temporal o de lease invalido: {exc}") from exc
    return crudo


def leer_estado(w_code: str, *, raiz: Path | None = None) -> dict | None:
    """El estado, o `None` **si y solo si no hay lock**.

    Un fichero ilegible o que no cumple el esquema lanza `MutexIlegible`. Si esto
    devolviera `None`, `adquirir` daria el caso por libre y **dos procesos entrarian**,
    que es lo unico que este modulo existe para impedir.

    Los bytes no se tocan: un lock ilegible es evidencia.
    """
    from .workspace_model import MutexIlegible

    p = ruta_del_lock(w_code, raiz=raiz)
    if not p.is_file():
        return None
    try:
        crudo = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise MutexIlegible(
            w_code=w_code,
            detalle=f"el lock existe y no se puede leer: {type(exc).__name__}") from exc
    return _validar_estado(crudo, w_code)


# ------------------------------------------------------ adquirir / renovar / liberar

#: Cinco minutos. NO es «mas que cualquier seccion critica» —eso era una afirmacion sin
#: medicion que R10/H10-04 tumbo—: es el valor del que se parte, y `tomado()` lo RENUEVA
#: mientras el cuerpo corre, asi que una corrida de OCR larga no lo agota.
LEASE_POR_DEFECTO = 300

#: Espera maxima por la seccion critica. Es de milisegundos en la practica: dentro solo
#: se lee un JSON pequeño y se hace un `os.replace`.
ESPERA_SECCION_CRITICA = 10


def _abrir_guard(w_code: str, raiz: Path | None):
    """Costura: el `FileLock` crudo, ya adquirido. Separada para poder doblarla."""
    from filelock import FileLock
    p = ruta_del_lock(w_code, raiz=raiz)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(p) + ".guard", timeout=ESPERA_SECCION_CRITICA)
    lock.acquire()
    return lock


@contextlib.contextmanager
def _guard(w_code: str, raiz: Path | None):
    """Bloqueo NATIVO durante la seccion critica. Ver la cabecera sobre por que no `O_EXCL`.

    Vive en un fichero HERMANO (`.lock.guard`) y no en el propio `.lock`: el estado se
    publica con `os.replace`, que sustituye el inodo, y bloquear el fichero que vas a
    reemplazar es pedir que el bloqueo se quede sobre un inodo huerfano.

    **Traduce el `Timeout` de `filelock` a `CaseBusy`** (R11/H11-06). Un `Timeout` crudo
    se salta la tabla del §10 entera: sale sin codigo, sin W-code y sin la garantia de
    que el mensaje no lleva rutas. Y su significado es exactamente `CASE_BUSY`: otro
    proceso de esta maquina esta dentro de la seccion critica.
    """
    from filelock import Timeout

    from .workspace_model import CaseBusy

    # El `raise` va FUERA del `except` a proposito (R12/H12-06): dentro, Python engancha
    # el `Timeout` como `__context__` aunque se use `from None`, y ese objeto lleva la
    # ruta del guard en su mensaje. `from None` solo suprime la PRESENTACION; lo que el
    # §16 pide es que la ruta no viaje.
    tipo_del_fallo = None
    try:
        lock = _abrir_guard(w_code, raiz)
    except Timeout as exc:
        tipo_del_fallo = type(exc).__name__
    if tipo_del_fallo is not None:
        # `from None` y NO `from exc` (R12/H12-06): el `Timeout` de `filelock` lleva la
        # ruta del guard en su mensaje, asi que encadenarlo la publicaba en cualquier
        # traceback. El §16 no prohibe la ruta «en `str()`»: prohibe filtrarla. Se
        # conserva el tipo de la causa, que diagnostica sin exponer.
        raise CaseBusy(
            w_code=_w_code_valido(w_code),
            detalle="la seccion critica sigue ocupada tras "
                    + str(ESPERA_SECCION_CRITICA) + " s ("
                    + tipo_del_fallo + ")")
    try:
        yield lock
    finally:
        lock.release()


def _escribir_estado(w_code: str, estado: dict, *, raiz: Path | None) -> None:
    """Temporal en el MISMO directorio + `os.replace`. Nunca in-place."""
    p = ruta_del_lock(w_code, raiz=raiz)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + chr(10),
                   encoding="utf-8")
    os.replace(tmp, p)


def _caducado(estado: dict, ahora: str) -> bool:
    """¿Vencio el lease? **Nunca se mira el PID** — el sistema los reutiliza (H3-02).

    El estado ya paso por `_validar_estado`, asi que sus campos son interpretables: no
    hace falta un `except` que, de existir, tendria que fallar CERRADO.
    """
    return _instante(ahora) > _instante(estado["renewed_at"]) + estado["lease_seconds"]


def adquirir(w_code: str, *, ahora: str, raiz: Path | None = None,
             lease_seconds: int = LEASE_POR_DEFECTO) -> str:
    """Toma el mutex y devuelve el nonce del titular.

    Las tres validaciones corren **antes** de tocar disco: una entrada invalida no debe
    dejar ni un fichero a medias, y menos un lock que luego nadie pueda interpretar.
    """
    from .workspace_model import CaseBusy

    w_code = _w_code_valido(w_code)
    lease = _lease_valido(lease_seconds)
    _sin_desvio_absurdo(ahora)             # valida el reloj antes de crear nada
    yo = identidad_proceso()
    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is not None and not _caducado(estado, ahora):
            raise CaseBusy(w_code=w_code,
                           maquina=(estado["propietario"] or {}).get("host"),
                           fecha=estado["renewed_at"],
                           detalle="el lease del titular sigue vivo")
        nonce = secrets.token_hex(8)
        _escribir_estado(w_code, {
            "schema": 1, "propietario": yo.a_json(), "nonce": nonce,
            "acquired_at": ahora, "renewed_at": ahora, "lease_seconds": lease,
        }, raiz=raiz)
        return nonce


def renovar(w_code: str, *, nonce: str, ahora: str, raiz: Path | None = None) -> None:
    """Alarga el lease. Exige titularidad y **monotonia**.

    La monotonia no es escrupulo: un `ahora` retrasado acortaria el lease propio y
    dejaria entrar a otro proceso sin que el titular se enterase (R10/H10-02).
    """
    from .workspace_model import MutexNotMine

    w_code = _w_code_valido(w_code)
    momento = _sin_desvio_absurdo(ahora)
    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is None or estado["nonce"] != nonce:
            raise MutexNotMine(w_code=w_code,
                               detalle="el nonce no coincide con el del titular")
        if momento < _instante(estado["renewed_at"]):
            raise ValueError(
                "una renovacion no puede retroceder en el tiempo: acortaria el lease "
                "propio y dejaria entrar a otro")
        estado["renewed_at"] = ahora
        _escribir_estado(w_code, estado, raiz=raiz)


def liberar(w_code: str, *, nonce: str, raiz: Path | None = None) -> None:
    """Suelta el mutex. Exige titularidad; idempotente si ya no esta.

    Que exija el nonce es el defecto A-1 del frontal leido al reves: alli el rollback
    del checkout cancela el lock **sin comprobar que siga siendo el propio**, y eso
    sigue vivo en `xfail`. Aqui no se repite.
    """
    from .workspace_model import MutexNotMine

    w_code = _w_code_valido(w_code)
    with _guard(w_code, raiz):
        estado = leer_estado(w_code, raiz=raiz)
        if estado is None:
            return
        if estado["nonce"] != nonce:
            raise MutexNotMine(w_code=w_code,
                               detalle="el nonce no coincide con el del titular")
        ruta_del_lock(w_code, raiz=raiz).unlink(missing_ok=True)


#: Fraccion del lease tras la que se renueva. Un tercio deja margen para dos latidos
#: perdidos antes de que el lease venza de verdad.
_FRACCION_LATIDO = 3


@dataclasses.dataclass
class SesionMutex:
    """Lo que `tomado()` entrega al cuerpo: su nonce, y la verdad sobre si sigue siendo suyo.

    Existe por R11/H11-02. Antes el gestor cedia solo el nonce y el hilo de renovacion
    hacia `except Exception: return`: si la renovacion fallaba, el hilo moria **callado**
    y el cuerpo seguia escribiendo como titular mientras otro proceso entraba. El arnes
    del revisor lo midio con dos procesos —`BODY_CONTINUES_AFTER_RENEW_ERROR`,
    `SECOND_ENTERED`— o sea que H10-04 seguia vivo, movido de sitio.

    **Lo que esta pieza NO puede hacer, y se declara:** interrumpir el cuerpo. No se
    preempta codigo Python arbitrario a mitad. Lo que si hace es que la perdida deje de
    ser silenciosa por tres vias: el cuerpo puede **preguntar** (`perdido()`), puede
    **comprobar contra el disco** cuando le convenga (`revalidar()`), y la salida del
    bloque **lanza** `MutexPerdido` en vez de un `MutexNotMine` que parece un error de
    programacion del llamador.

    Un cuerpo largo —una corrida de OCR— deberia consultar `perdido()` antes de publicar
    nada irreversible. Eso es una convencion, no una garantia, y por eso se dice aqui.
    """

    w_code: str
    nonce: str
    raiz: "Path | None"
    #: SIN default a proposito (R13/H13-02). Con `ahora_fn=None` la comprobacion del
    #: lease se saltaba entera, o sea que una sesion construida sin reloj volvia al
    #: comportamiento que R12/H12-02 declaro critico. Un default que desactiva una
    #: comprobacion de seguridad es fail-open, y este modulo lleva tres rondas diciendo
    #: que falla cerrado. Que sea IMPOSIBLE construirla mal es mejor que comprobarlo
    #: dentro.
    ahora_fn: "object"
    _perdido: bool = False
    _causa: "BaseException | None" = None

    def perdido(self) -> bool:
        """¿Se sabe ya que el mutex dejo de ser nuestro? No consulta el disco."""
        return self._perdido

    def marcar_perdido(self, causa: BaseException | None = None) -> None:
        self._perdido = True
        if causa is not None and self._causa is None:
            self._causa = causa

    def revalidar(self) -> bool:
        """Comprueba contra el disco si el nonce sigue siendo el nuestro.

        Devuelve `True` si seguimos siendo titulares. Un lock ilegible o ausente **no**
        se lee como «sigue siendo mio»: se marca la perdida, que es el lado seguro.
        """
        from .workspace_model import WorkspaceError

        try:
            estado = leer_estado(self.w_code, raiz=self.raiz)
        except WorkspaceError as exc:
            self.marcar_perdido(exc)
            return False
        if estado is None or estado["nonce"] != self.nonce:
            self.marcar_perdido()
            return False
        # Y el LEASE (R12/H12-02). Comprobar solo el nonce daba una garantia falsa justo
        # donde mas cara sale: el cuerpo llama a esto ANTES de publicar algo
        # irreversible, y desde que el lease vence otro proceso esta autorizado a
        # adquirir. «Sigue siendo mi nonce» y «sigo siendo titular» dejaron de ser lo
        # mismo en el instante en que el lease caduco.
        #
        # El reloj se ACOTA aqui igual que en `adquirir` y `renovar` (R13/H13-01): la
        # cota simetrica de R12 no alcanzaba a esta via, asi que un `ahora_fn` roto
        # calculaba la caducidad contra un instante arbitrario y devolvia garantia. Si
        # el reloj no es utilizable, se falla CERRADO: no saber si sigo siendo titular
        # es, a efectos de autorizar una escritura, lo mismo que no serlo.
        try:
            ahora = self.ahora_fn()
            _sin_desvio_absurdo(ahora)
        except Exception as exc:                         # noqa: BLE001
            self.marcar_perdido(exc)
            return False
        if _caducado(estado, ahora):
            self.marcar_perdido()
            return False
        return True


@contextlib.contextmanager
def tomado(w_code: str, *, ahora_fn, raiz: Path | None = None,
           lease_seconds: int = LEASE_POR_DEFECTO):
    """Adquiere, **renueva mientras el cuerpo corre**, y libera pase lo que pase.

    Cede una `SesionMutex`, no una cadena: el cuerpo necesita poder preguntar si sigue
    siendo titular (R11/H11-02).

    `ahora_fn` es un **callable** y no una cadena porque el renovador necesita el
    instante de cada latido; una cadena fija escribiria siempre el mismo `renewed_at`,
    o sea que no renovaria nada.

    **El error del cuerpo manda** (R11/H11-03). Si el cuerpo lanza y ademas la
    liberacion falla, el llamador ve **el suyo**: perder el error de liberacion es
    molesto, perder el del cuerpo es perder la causa. Medido antes de arreglarlo: un
    `except RuntimeError` del llamador no entraba, porque lo que salia era `MutexNotMine`.
    """
    lease = _lease_valido(lease_seconds)
    nonce = adquirir(w_code, ahora=ahora_fn(), raiz=raiz, lease_seconds=lease)
    sesion = SesionMutex(w_code=_w_code_valido(w_code), nonce=nonce, raiz=raiz,
                         ahora_fn=ahora_fn)
    parar = threading.Event()

    def _latir():
        while not parar.wait(lease / _FRACCION_LATIDO):
            try:
                renovar(w_code, nonce=nonce, ahora=ahora_fn(), raiz=raiz)
            except BaseException as exc:                 # noqa: BLE001
                # `BaseException` y no `Exception` (R12/H12-03): un `SystemExit` en el
                # hilo lo dejaba morir SIN señal, que es exactamente el defecto que esta
                # rama existe para cerrar. NO se traga: se registra. El hilo no puede
                # parar el cuerpo, pero callarse es lo que dejaba a dos procesos
                # escribiendo a la vez.
                sesion.marcar_perdido(exc)
                return

    hilo = threading.Thread(target=_latir, name=f"mutex-{w_code}", daemon=True)
    hilo.start()
    fallo_del_cuerpo = False
    try:
        yield sesion
    except BaseException:
        fallo_del_cuerpo = True
        raise
    finally:
        parar.set()
        hilo.join(timeout=5)
        try:
            liberar(w_code, nonce=nonce, raiz=raiz)
        except BaseException as exc:                     # noqa: BLE001
            # `liberar` exige titularidad, asi que fallar aqui ES la señal de perdida.
            # NO se revalida despues de una liberacion CORRECTA: acabamos de borrar el
            # lock, asi que «no hay lock» significa «lo solte yo», no «lo perdi». Ese
            # matiz lo cazaron dos tests que ya existian, no yo al escribirlo.
            sesion.marcar_perdido(exc)
        if sesion.perdido() and fallo_del_cuerpo:
            # El error del cuerpo manda, pero la perdida del mutex no puede evaporarse
            # (R12/H12-04): antes solo quedaba en `sesion._causa`, invisible para el
            # llamador. Una nota es observable en el traceback sin desplazar al primario.
            #
            # Y se anota HAYA O NO excepcion detras (R13/H13-03): una perdida por lease
            # caducado no deja `_causa`, y exigirla dejaba esa mitad sin avisar. La
            # propiedad es «una perdida no se evapora», no «una excepcion no se evapora».
            import sys
            en_vuelo = sys.exc_info()[1]
            if en_vuelo is not None:
                porque = (type(sesion._causa).__name__ + ": " + str(sesion._causa)
                          if sesion._causa is not None
                          else "el lease caduco o la titularidad cambio")
                en_vuelo.add_note(
                    "[mutex] ademas, el mutex se perdio durante la operacion: " + porque)
        if sesion.perdido() and not fallo_del_cuerpo:
            from .workspace_model import MutexPerdido
            raise MutexPerdido(
                w_code=sesion.w_code,
                detalle="el mutex dejo de ser nuestro durante la operacion"
            ) from sesion._causa
