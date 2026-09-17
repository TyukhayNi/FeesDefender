"""Transporte de la API de Codicert (Servicios de MailCertificado S.L.).

Cliente puro: **no sabe qué es un expediente**. Recibe datos ya resueltos y devuelve lo
que dice el servidor. El criterio del despacho vive en `core/expedicion_certificada.py`.

Contrato y mediciones: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
"""
from __future__ import annotations

import base64
import datetime as _dt
import os
import subprocess
from dataclasses import dataclass
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


def acceso(usuario: str, clave: str, *, entorno: str, cliente: Cliente | None = None) -> Ficha:
    """`POST /usuarios/acceso`. La clave no aparece nunca en el error."""
    if entorno not in BASES:
        raise CodicertError(f"entorno desconocido: {entorno!r}; son {sorted(BASES)}")
    cliente = cliente or _cliente_real()
    r = cliente.request("POST", f"{BASES[entorno]}/usuarios/acceso",
                        json={"usuario": usuario, "clave": clave})
    cuerpo = _json_o_vacio(r)
    if r.status_code != 200 or (cuerpo or {}).get("estado") != "OK":
        raise CodicertAuthError(
            f"Codicert rechazó el acceso de {usuario!r} en {entorno}: "
            f"{(cuerpo or {}).get('mensaje') or r.status_code}")
    datos = cuerpo["datos"]
    return Ficha(token=datos["ficha"], vence=_dt.datetime.fromisoformat(datos["fecha_vencimiento"]))


TIPOS_ENTREGA = ("correo", "sms")


def adjunto(ruta: Path) -> dict[str, str]:
    """Fichero en el formato que piden los dos endpoints: base64 dentro del JSON."""
    return {"nombre": ruta.name,
            "datos": base64.b64encode(ruta.read_bytes()).decode("ascii"),
            "mime": "application/pdf"}


def _cabeceras(ficha: Ficha) -> dict[str, str]:
    return {"Authorization": f"Bearer {ficha.token}", "x-json-ficheros": "1"}


def _id_de(r: Any, que: str) -> str:
    cuerpo = _json_o_vacio(r)
    if r.status_code == 422:
        raise CodicertDatosInvalidosError(
            cuerpo.get("mensaje") or "datos no válidos", cuerpo.get("datos") or {})
    if r.status_code != 200 or cuerpo.get("estado") != "OK":
        raise CodicertError(f"{que}: HTTP {r.status_code} — {cuerpo.get('mensaje')!r}")
    return cuerpo["datos"]["id"]


def enviar_burofax(ficha: Ficha, *, destinatario: dict, adjuntos: list[dict], asunto: str,
                   cuerpo: str, id_personalizado: str, entorno: str,
                   cliente: Cliente | None = None) -> str:
    """`POST /envios/burofax`. UN destinatario por llamada: el contrato no admite más."""
    cliente = cliente or _cliente_real()
    r = cliente.request("POST", f"{BASES[entorno]}/envios/burofax", headers=_cabeceras(ficha),
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
    cliente = cliente or _cliente_real()
    r = cliente.request("POST", f"{BASES[entorno]}/envios/entrega-electronica-certificada",
                        headers=_cabeceras(ficha),
                        json={"destinatarios": destinatarios, "adjuntos": adjuntos,
                              "asunto": asunto, "cuerpo": cuerpo, "tipo_entrega": tipo_entrega,
                              "id_personalizado": id_personalizado})
    return _id_de(r, f"entrega electrónica ({tipo_entrega})")
