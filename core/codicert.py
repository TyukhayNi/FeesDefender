"""Transporte de la API de Codicert (Servicios de MailCertificado S.L.).

Cliente puro: **no sabe qué es un expediente**. Recibe datos ya resueltos y devuelve lo
que dice el servidor. El criterio del despacho vive en `core/expedicion_certificada.py`.

Contrato y mediciones: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


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
