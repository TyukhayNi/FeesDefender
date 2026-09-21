"""Transporte de la API de Codicert (Servicios de MailCertificado S.L.).

Cliente puro: **no sabe qué es un expediente**. Recibe datos ya resueltos y devuelve lo
que dice el servidor. El criterio del jurídico vive en `core/expedicion_certificada.py`.

Contrato y mediciones: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
"""
from __future__ import annotations

import base64
import datetime as _dt
import os
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol


class CodicertError(RuntimeError):
    """Fallo de transporte o de uso de la API."""


class CodicertAuthError(CodicertError):
    """Credenciales ausentes o rechazadas."""


class CodicertDatosInvalidosError(CodicertError):
    """422: el servidor rechaza el payload. Lleva el detalle campo a campo."""

    def __init__(self, mensaje: str, campos: dict[str, str] | None = None) -> None:
        super().__init__(mensaje)
        self.campos = campos or {}


BASES: dict[str, str] = {
    "sandbox": "https://ws.codicert.tk/v2",
    "produccion": "https://ws.codicert.io/v2",
}

LONGITUD_PAGINA = 100  # el contrato dice [1..100]; medido, acepta [10..100]

# Ciudad canónica de `core.ciudades.CIUDADES` -> prefijo de variable de entorno.
# El slug se fija aquí y no se deriva: "San Sebastián" no admite espacio ni tilde.
PREFIJO_PLAZA: dict[str, str] = {
    "Barcelona":     "CODICERT_BARCELONA",
    "Bilbao":        "CODICERT_BILBAO",
    "Madrid":        "CODICERT_MADRID",
    "San Sebastián": "CODICERT_SANSEBASTIAN",
    "Santander":     "CODICERT_SANTANDER",
    "Sevilla":       "CODICERT_SEVILLA",
    "Valencia":      "CODICERT_VALENCIA",
}


def _de_fuentes_lentas(nombre: str) -> str | None:
    """`.env` de la raíz REAL del repo y, si no, el registro de usuario de Windows.

    Las dos existen por un defecto medido el 2026-09-17: `core/config.py` resuelve la
    raíz como `__file__.parent.parent`, que en un worktree no es la raíz y no tiene
    `.env`; y una variable creada después de arrancar el proceso no se hereda.
    """
    try:
        # `--git-common-dir`, NO `--show-toplevel`: desde un worktree, el segundo
        # devuelve el propio worktree —que es justo donde no hay `.env`— y esta
        # función reproduciría el defecto que existe para corregir. Medido.
        comun = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=10,
        )
        if comun.returncode == 0:
            env = Path(comun.stdout.strip()).parent / ".env"
            if env.is_file():
                for linea in env.read_text(encoding="utf-8", errors="replace").splitlines():
                    if linea.startswith(f"{nombre}="):
                        valor = linea.split("=", 1)[1].strip()
                        if valor:
                            return valor
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        reg = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"[Environment]::GetEnvironmentVariable('{nombre}','User')"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=20,
        )
        valor = (reg.stdout or "").strip()
        return valor or None
    except (OSError, subprocess.SubprocessError):
        return None


def _valor(nombre: str) -> str | None:
    return os.environ.get(nombre) or _de_fuentes_lentas(nombre)


def credenciales(plaza: str | None, entorno: str) -> tuple[str, str]:
    """Usuario y clave del emisor. `plaza=None` es el sandbox.

    Nunca incluye el valor de la clave en los mensajes de error: solo el nombre de la
    variable que falta.
    """
    if entorno not in BASES:
        raise CodicertError(f"entorno desconocido: {entorno!r}; son {sorted(BASES)}")
    if plaza is None:
        prefijo = "CODICERT_SANDBOX"
    else:
        prefijo = PREFIJO_PLAZA.get(plaza)
        if prefijo is None:
            raise CodicertError(
                f"{plaza!r} no es una plaza con usuario de Codicert; son {sorted(PREFIJO_PLAZA)}")
    usuario, clave = _valor(f"{prefijo}_USUARIO"), _valor(f"{prefijo}_CLAVE")
    faltan = [n for n, v in ((f"{prefijo}_USUARIO", usuario), (f"{prefijo}_CLAVE", clave)) if not v]
    if faltan:
        raise CodicertAuthError(
            "faltan credenciales de Codicert: " + ", ".join(faltan)
            + ". Se ponen como variables de entorno de usuario de Windows.")
    return usuario, clave  # type: ignore[return-value]


class Cliente(Protocol):
    """Superficie mínima de `httpx.Client` que usa este módulo."""

    def request(self, metodo: str, url: str, **kw: Any) -> Any: ...


@dataclass(frozen=True)
class Ficha:
    """Token de sesión con su vencimiento. La API lo da con 24 h de vida."""

    token: str
    vence: _dt.datetime

    def caducada(self, *, ahora: _dt.datetime) -> bool:
        return ahora >= self.vence


def _cliente_real() -> Cliente:
    import httpx

    class _C:
        def request(self, metodo: str, url: str, **kw: Any) -> Any:
            return httpx.request(metodo, url, timeout=kw.pop("timeout", 120), **kw)

    return _C()


def _json_o_vacio(r: Any) -> Any:
    """El cuerpo de `r` como JSON, o `{}` si no parsea — sin mirar `status_code`.

    El blindaje anterior (`r.json() if r.status_code != 500 else {}`) solo cubría el
    500, un número arbitrario que no está medido contra el servidor en ningún sitio
    del proyecto. Un 502/503/504 de un proxy, o un cuerpo corrupto con cualquier otro
    estado, hacía explotar `r.json()` con un `JSONDecodeError` crudo que rompía el
    contrato de este módulo: solo falla con `CodicertError`/`CodicertAuthError`.
    Pensado para que lo reutilicen los envíos y las lecturas que se añadan a este
    mismo módulo.
    """
    try:
        return r.json()
    except ValueError:
        # `json.JSONDecodeError` es un `ValueError`; igual cualquier otro fallo de
        # decodificación del cuerpo. Las dos cosas son "no parsea".
        return {}


def _sin_la_clave(mensaje: str | None, clave: str) -> str | None:
    """`mensaje`, con cualquier aparición literal de `clave` sustituida.

    Hallazgo de revisión (H-12, r2): el mensaje que devuelve el SERVIDOR se copiaba tal
    cual dentro de `CodicertAuthError`, pese al contrato de `acceso()` — "la clave no
    aparece nunca en el error". Si esa respuesta refleja la clave (un mensaje de
    validación que la repite, por ejemplo), el `str` de la excepción la llevaría íntegra
    y el frontal la imprimiría en stderr. Verificado con credenciales sintéticas y una
    respuesta fabricada: no se afirma que el servicio real de Codicert refleje
    contraseñas — lo demostrado es que esta ruta rompía la garantía declarada.

    `clave` vacía no se sustituye: no hay nada que ocultar y un `str.replace` con
    cadena vacía no tiene un resultado seguro que definir. El nombre de usuario NO pasa
    por aquí y sigue apareciendo tal cual en el mensaje final: el contrato solo prohíbe
    la clave, y el diseño exige el usuario en la cabecera del plan.
    """
    if not mensaje or not clave:
        return mensaje
    return mensaje.replace(clave, "«clave omitida»")


def _peticion(cliente: Cliente, metodo: str, url: str, *, que: str,
              incierto: bool = False, **kw: Any) -> Any:
    """`cliente.request(metodo, url, **kw)`, traduciendo cualquier fallo de transporte.

    Hallazgo de revisión (H-11, r2): las cuatro puertas de red del módulo (`acceso`,
    `enviar_burofax`, `enviar_eec`, `_get`) llamaban a `cliente.request` sin traducir sus
    fallos. Un cliente que levanta una excepción de transporte — `httpx.ReadTimeout` y
    semejantes, ante un servidor caído o una red lenta — la propagaba con su tipo
    crudo, fuera del contrato del módulo (solo falla con `CodicertError`/
    `CodicertAuthError`). Punto único para las cuatro puertas, en vez de repetir el
    `try` en cada una.

    `incierto=True` — solo lo pasan `enviar_burofax` y `enviar_eec`, los dos POST que
    cuestan dinero o mandan una comunicación irreversible — añade el mismo aviso que ya
    lleva `_id_de` para el sobre sin `datos.id`: la llamada PUDO HABER SALIDO antes de
    que la excepción llegara aquí, así que el mensaje manda a comprobar el portal en vez
    de invitar a reintentar a ciegas — este módulo no reintenta nada por su cuenta. Un
    GET de solo lectura (`_get`, y con él `credito`/`estados`/`certificado`/
    `descargar_adjunto`/`listar`) o el login (`acceso`) no tienen ese efecto de lado:
    fallar ahí es solo no haber podido leer o autenticar, y decir "pudo haber salido"
    sería un diagnóstico falso.

    `AssertionError` NO se traduce: es la señal con la que los dobles de test marcan un
    guion mal construido (`tests/_dobles/fake_codicert.py::FakeCliente`) — un fallo del
    TEST, no del transporte. Traducirla la disfrazaría de error de dominio y ocultaría
    el defecto real del doble en vez de dejarlo fallar con su propia traza.
    """
    try:
        return cliente.request(metodo, url, **kw)
    except AssertionError:
        raise
    except Exception as exc:
        aviso = (" La llamada PUDO HABER SALIDO: compruébalo en el portal de Codicert "
                 "antes de reintentar, no lo repitas a ciegas.") if incierto else ""
        raise CodicertError(
            f"{que}: fallo de transporte ({exc.__class__.__name__}: {exc}).{aviso}"
        ) from exc


def _base_de(entorno: str) -> str:
    """URL base de Codicert para `entorno`.

    `acceso()` ya comprobaba `entorno not in BASES` en línea; `enviar_burofax` y
    `enviar_eec` no lo hacían e indexaban `BASES[entorno]` directo, así que un
    entorno inventado reventaba con `KeyError` crudo antes incluso de tocar la red.
    Un solo helper para los tres sitios que ya lo necesitan (y los que vengan).
    """
    if entorno not in BASES:
        raise CodicertError(f"entorno desconocido: {entorno!r}; son {sorted(BASES)}")
    return BASES[entorno]


def acceso(usuario: str, clave: str, *, entorno: str, cliente: Cliente | None = None) -> Ficha:
    """`POST /usuarios/acceso`. La clave no aparece nunca en el error.

    Hallazgos de revisión (H-11/H-12, r2): un fallo de transporte del cliente inyectado
    propagaba su tipo crudo (arreglado vía `_peticion`); un `200 {"estado": "OK"}` sin
    `datos` reventaba con `KeyError` (arreglado validando la forma antes de indexar); y
    el `mensaje` que devuelve el servidor se copiaba sin filtrar, pudiendo reflejar la
    clave si la respuesta la repetía (arreglado con `_sin_la_clave`).
    """
    base = _base_de(entorno)
    cliente = cliente or _cliente_real()
    r = _peticion(cliente, "POST", f"{base}/usuarios/acceso", que="POST /usuarios/acceso",
                 json={"usuario": usuario, "clave": clave})
    cuerpo = _json_o_vacio(r)
    cuerpo = cuerpo if isinstance(cuerpo, dict) else {}
    if r.status_code != 200 or cuerpo.get("estado") != "OK":
        mensaje = _sin_la_clave(cuerpo.get("mensaje"), clave)
        raise CodicertAuthError(
            f"Codicert rechazó el acceso de {usuario!r} en {entorno}: "
            f"{mensaje or r.status_code}")
    datos = cuerpo.get("datos")
    if not isinstance(datos, dict) or "ficha" not in datos or "fecha_vencimiento" not in datos:
        raise CodicertAuthError(
            f"Codicert aceptó el acceso de {usuario!r} en {entorno} pero la respuesta no "
            "trae datos.ficha / datos.fecha_vencimiento")
    return Ficha(token=datos["ficha"], vence=_dt.datetime.fromisoformat(datos["fecha_vencimiento"]))


TIPOS_ENTREGA = ("correo", "sms")


def adjunto(ruta: Path) -> dict[str, str]:
    """Fichero en el formato que piden los dos endpoints: base64 dentro del JSON."""
    return {"nombre": ruta.name,
            "datos": base64.b64encode(ruta.read_bytes()).decode("ascii"),
            "mime": "application/pdf"}


def _cabeceras(ficha: Ficha) -> dict[str, str]:
    """Cabeceras comunes a los dos envíos: portador del token y `x-json-ficheros`,
    que el contrato exige para que los adjuntos viajen embebidos en el JSON."""
    return {"Authorization": f"Bearer {ficha.token}", "x-json-ficheros": "1"}


def _id_de(r: Any, que: str) -> str:
    """`IdEnvio` de la respuesta de un envío (burofax o entrega electrónica).

    Un 422 desglosa el detalle campo a campo en `CodicertDatosInvalidosError`;
    cualquier otro estado sin `estado: "OK"` es error de transporte corriente.
    El caso que corrige este hallazgo de revisión es el peor de los tres: un
    `200` con `estado: "OK"` pero sin `datos.id` en el cuerpo. Para cuando se
    llega aquí la llamada HTTP YA SE HIZO —el envío pudo haber salido, y si era
    el burofax, ya se ha podido pagar—, así que no cabe un `KeyError` crudo que
    rompa el contrato del módulo (solo falla con `CodicertError`/
    `CodicertAuthError`): se avisa de que el envío pudo haber salido para que
    quien llama lo compruebe en el portal antes de reintentar, en vez de
    reintentar a ciegas y arriesgar un envío duplicado.

    Hallazgo de revisión (H-11, r2): un cuerpo que parsea pero no es un objeto — `[]`,
    por ejemplo — hacía que `cuerpo.get(...)` reventara con `AttributeError` crudo, en
    la rama del 422 y en la del resto de estados por igual. Mismo patrón que ya usa
    `listar()` para su propio cuerpo: se valida la forma ANTES de llamar a `.get` en
    ella, no después.
    """
    cuerpo = _json_o_vacio(r)
    if not isinstance(cuerpo, dict):
        raise CodicertError(f"{que}: cuerpo no es un objeto — {cuerpo!r}")
    if r.status_code == 422:
        raise CodicertDatosInvalidosError(
            cuerpo.get("mensaje") or "datos no válidos", cuerpo.get("datos") or {})
    if r.status_code != 200 or cuerpo.get("estado") != "OK":
        raise CodicertError(f"{que}: HTTP {r.status_code} — {cuerpo.get('mensaje')!r}")
    datos = cuerpo.get("datos")
    id_envio = datos.get("id") if isinstance(datos, dict) else None
    if not id_envio:
        raise CodicertError(
            f"{que}: la API respondió con estado OK pero sin datos.id en el cuerpo — "
            "el envío PUDO HABER SALIDO. Compruébalo en el portal de Codicert antes "
            "de reintentar: no lo repitas a ciegas."
        )
    return id_envio


def enviar_burofax(ficha: Ficha, *, destinatario: dict, adjuntos: list[dict], asunto: str,
                   cuerpo: str, id_personalizado: str, entorno: str,
                   cliente: Cliente | None = None) -> str:
    """`POST /envios/burofax`. UN destinatario por llamada: el contrato no admite más."""
    base = _base_de(entorno)
    cliente = cliente or _cliente_real()
    r = _peticion(cliente, "POST", f"{base}/envios/burofax", que="burofax", incierto=True,
                 headers=_cabeceras(ficha),
                 json={"destinatarios": [destinatario], "adjuntos": adjuntos,
                       "asunto": asunto, "cuerpo": cuerpo,
                       "id_personalizado": id_personalizado})
    return _id_de(r, "burofax")


def enviar_eec(ficha: Ficha, *, destinatarios: list[dict], adjuntos: list[dict], asunto: str,
               cuerpo: str, tipo_entrega: str, id_personalizado: str, entorno: str,
               cliente: Cliente | None = None) -> str:
    """`POST /envios/entrega-electronica-certificada`, por correo o por SMS."""
    if tipo_entrega not in TIPOS_ENTREGA:
        raise CodicertError(f"tipo_entrega {tipo_entrega!r}; son {TIPOS_ENTREGA}")
    base = _base_de(entorno)
    cliente = cliente or _cliente_real()
    r = _peticion(cliente, "POST", f"{base}/envios/entrega-electronica-certificada",
                 que=f"entrega electrónica ({tipo_entrega})", incierto=True,
                 headers=_cabeceras(ficha),
                 json={"destinatarios": destinatarios, "adjuntos": adjuntos,
                       "asunto": asunto, "cuerpo": cuerpo, "tipo_entrega": tipo_entrega,
                       "id_personalizado": id_personalizado})
    return _id_de(r, f"entrega electrónica ({tipo_entrega})")


def _get(ficha: Ficha, ruta: str, *, entorno: str, cliente: Cliente | None = None, **kw: Any) -> Any:
    """GET genérico con autorización. Levanta `CodicertError` si status != 200."""
    base = _base_de(entorno)
    cliente = cliente or _cliente_real()
    r = _peticion(cliente, "GET", f"{base}{ruta}", que=f"GET {ruta}",
                 headers={"Authorization": f"Bearer {ficha.token}"}, **kw)
    if r.status_code != 200:
        raise CodicertError(f"GET {ruta}: HTTP {r.status_code}")
    return r


def credito(ficha: Ficha, *, entorno: str, cliente: Cliente | None = None) -> Decimal:
    """Saldo del usuario. `Decimal` y no `float`: con esto se decide si se gasta.

    Hallazgo de revisión (2026-09-17): la guarda de arriba comprobaba que `datos`
    fuera un `dict` con la clave `credito` presente, pero no que su VALOR fuera
    numérico — `{"datos": {"credito": None}}` la pasaba y `Decimal(str(None))`
    reventaba con `decimal.InvalidOperation` crudo, fuera del contrato del módulo
    (solo falla con `CodicertError`/`CodicertAuthError`).

    Hallazgo de revisión (H-11, r2): un cuerpo JSON `null` parsea a `None` — no es
    "no parsea", así que `_json_o_vacio` lo deja pasar tal cual — y `cuerpo.get(...)`
    reventaba con `AttributeError` crudo, porque `None` no tiene `.get`. Se valida que
    `cuerpo` sea un `dict` antes de preguntarle nada.
    """
    r = _get(ficha, "/usuarios/credito", entorno=entorno, cliente=cliente)
    cuerpo = _json_o_vacio(r)
    datos = cuerpo.get("datos") if isinstance(cuerpo, dict) else None
    if not isinstance(datos, dict) or "credito" not in datos:
        raise CodicertError("GET /usuarios/credito: respuesta sin datos.credito")
    try:
        return Decimal(str(datos["credito"]))
    except InvalidOperation as exc:
        raise CodicertError(
            f"GET /usuarios/credito: datos.credito no es numérico — {datos['credito']!r}"
        ) from exc


def estados(ficha: Ficha, id_envio: str, *, entorno: str,
            cliente: Cliente | None = None) -> list[dict]:
    """Histórico de estados certificados de una comunicación."""
    r = _get(ficha, f"/envios/{id_envio}/estados", entorno=entorno, cliente=cliente)
    cuerpo = _json_o_vacio(r)
    return cuerpo.get("datos") or []


def certificado(ficha: Ficha, id_envio: str, *, entorno: str,
                cliente: Cliente | None = None) -> bytes:
    """El certificado, en PDF. Se emite **a fecha de descarga**, no de envío."""
    return _get(ficha, f"/certificados/comunicacion/{id_envio}",
                entorno=entorno, cliente=cliente).content


def descargar_adjunto(ficha: Ficha, id_envio: str, nombre: str, *, entorno: str,
                      cliente: Cliente | None = None) -> bytes:
    """El adjunto **tal como salió**. Su `sha256` es la verificación por resultado."""
    clave = base64.urlsafe_b64encode(nombre.encode()).decode().rstrip("=")
    return _get(ficha, f"/envios/{id_envio}/adjuntos/{clave}",
                entorno=entorno, cliente=cliente).content


def listar(ficha: Ficha, *, entorno: str, cliente: Cliente | None = None,
           **filtros: Any) -> Iterator[dict]:
    """Recorre `GET /envios` entero. Acota siempre por fecha cuando se pueda.

    No hay filtro por `id_personalizado`: viene en cada elemento y se filtra en casa.

    Dos guardas de una revisión de código (2026-09-17):

    1. El cuerpo pasa por `_json_o_vacio`, como las otras cuatro lecturas del
       módulo — antes llamaba a `.json()` a pelo, así que un cuerpo no parseable en
       UNA SOLA página de una iteración larga reventaba con `JSONDecodeError` crudo
       en vez de `CodicertError`.
    2. Se valida que el cuerpo sea un `dict` y que `totalPaginas` sea numérico ANTES
       de usarlos. Por eso `totalPaginas` ya no lleva el `or 0` que tenía: un cuerpo
       no parseable se cuela como `{}` vía `_json_o_vacio`, y con `or 0` esa página
       rota se leía como "ya no hay más" y el listado se TRUNCABA EN SILENCIO — el
       fallo más caro de los tres, porque no revienta, solo faltan resultados.

    `longitud` y `pagina` van DESPUÉS de `**filtros` en `params`: son reservados y
    deben ganar siempre. Si fueran antes, un llamador que pasara `longitud` en
    `filtros` lo sobrescribiría — medido, el servidor rechaza `longitud` por debajo
    de 10.
    """
    pagina = 1
    while True:
        params = {**filtros, "longitud": LONGITUD_PAGINA, "pagina": pagina}
        cuerpo = _json_o_vacio(
            _get(ficha, "/envios", entorno=entorno, cliente=cliente, params=params))
        if not isinstance(cuerpo, dict):
            raise CodicertError(f"GET /envios: cuerpo no es un objeto — {cuerpo!r}")
        total_paginas = cuerpo.get("totalPaginas")
        if not isinstance(total_paginas, (int, float)):
            raise CodicertError(
                f"GET /envios: totalPaginas no es numérico — {total_paginas!r}")
        datos = cuerpo.get("datos")
        if datos:
            yield from datos
        if pagina >= total_paginas:
            return
        pagina += 1
