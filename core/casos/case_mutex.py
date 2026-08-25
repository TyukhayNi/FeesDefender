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
from datetime import datetime
from pathlib import Path

_RE_W_CODE = re.compile(r"^W-[A-Z0-9]{3,20}$")

#: UUID de ESTE proceso, generado al importar: estable durante su vida y distinto para
#: cualquier otro. Sustituye al `boot_id` derivado del reloj (R10/H10-07), que `psutil`
#: declara sensible a ajustes de hora, NTP e hibernación.
_PROCESO_UID = uuid.uuid4().hex


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
    for prohibida, motivo in ((Path(config.settings.casos_root), "CASOS_ROOT"),
                              (Path(config.settings.project_root), "el repo")):
        prohibida = Path(os.path.abspath(str(prohibida)))
        if _bajo(raiz, prohibida):
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
    if not isinstance(crudo["propietario"], dict):
        raise malo("el propietario no es un objeto")
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


def _guard(w_code: str, raiz: Path | None):
    """Bloqueo NATIVO durante la seccion critica. Ver la cabecera sobre por que no `O_EXCL`.

    Vive en un fichero HERMANO (`.lock.guard`) y no en el propio `.lock`: el estado se
    publica con `os.replace`, que sustituye el inodo, y bloquear el fichero que vas a
    reemplazar es pedir que el bloqueo se quede sobre un inodo huerfano.
    """
    from filelock import FileLock
    p = ruta_del_lock(w_code, raiz=raiz)
    p.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(p) + ".guard", timeout=ESPERA_SECCION_CRITICA)


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
    _instante(ahora)                       # valida el reloj antes de crear nada
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
    momento = _instante(ahora)
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


@contextlib.contextmanager
def tomado(w_code: str, *, ahora_fn, raiz: Path | None = None,
           lease_seconds: int = LEASE_POR_DEFECTO):
    """Adquiere, **renueva mientras el cuerpo corre**, y libera pase lo que pase.

    La renovacion no es un extra: sin ella, un cuerpo mas largo que el lease pierde el
    mutex a mitad, otro proceso entra, y el primero **sigue escribiendo sin enterarse**
    (R10/H10-04). Solo se entera al salir, cuando `liberar` le dice que el lock ya no
    es suyo — o sea, cuando los dos ya han escrito.

    `ahora_fn` es un **callable** y no una cadena porque el renovador necesita el
    instante de cada latido; una cadena fija escribiria siempre el mismo `renewed_at`,
    o sea que no renovaria nada.

    El hilo es `daemon` y se para en el `finally`: un renovador que sobreviviera al
    bloque estaria alargando un lock que quiza ya es de otro.
    """
    lease = _lease_valido(lease_seconds)
    nonce = adquirir(w_code, ahora=ahora_fn(), raiz=raiz, lease_seconds=lease)
    parar = threading.Event()

    def _latir():
        while not parar.wait(lease / _FRACCION_LATIDO):
            try:
                renovar(w_code, nonce=nonce, ahora=ahora_fn(), raiz=raiz)
            except Exception:                    # noqa: BLE001
                return       # perdimos la titularidad; el cuerpo se entera al liberar

    hilo = threading.Thread(target=_latir, name=f"mutex-{w_code}", daemon=True)
    hilo.start()
    try:
        yield nonce
    finally:
        parar.set()
        hilo.join(timeout=5)
        liberar(w_code, nonce=nonce, raiz=raiz)
