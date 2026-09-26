"""Precheck determinista del prerrequisito OAuth de rclone para la copia en
bloque vía `rclone rcd` (backlog robustez-velocidad ítem 6). El prerrequisito
(client OAuth PROPIO del despacho, no el compartido `202264815644`) se comprueba
SOLO por exit code — NO se deduce leyendo documentación (en la pasada 2 un
agente concluyó desde un doc archivado que no existía; un comando de 1s lo
confirmaba).

NUNCA vuelca la config completa: `rclone config show` expone `token` y
`client_secret` en claro. Este script extrae SOLO la línea `client_id` por
regex y deriva de ella el project number; jamás imprime `stdout` de rclone.

exit 0 → client propio (project != 202264815644): rcd puede ser ruta primaria.
exit 3 → remote sin client propio (usa el compartido) → copia secuencial.
exit 4 → `rclone` no instalado, o el remote no existe en su configuración.
exit 5 → `rclone` TARDÓ más de lo que se le da: no se sabe qué client tiene.
exit 2 → uso incorrecto.

Cualquier exit distinto de 0 lleva a la copia secuencial; el veredicto dice cuál fue la
causa (`MEJORAS #296`). Hasta el 2026-09-26 el timeout salía como 4, junto a «no
instalado», y un remote inexistente como 3 —«client compartido»—: `rclone config show
<remote inexistente>` sale con 0 y solo lo dice en un comentario de su salida.
"""
from __future__ import annotations

import re
import subprocess
import sys

_CLIENT_COMPARTIDO_PROJECT = "202264815644"
#: Lo que `rclone config show` escribe, con código 0, cuando el remote no existe (medido con
#: rclone real el 2026-09-26).
_REMOTE_INEXISTENTE = "couldn't find type of fs"
_CLIENT_ID_RE = re.compile(r"^\s*client_id\s*=\s*(\S+)", re.M)


def client_id_de_config(salida: str) -> str | None:
    m = _CLIENT_ID_RE.search(salida or "")
    return m.group(1) if m else None


def project_de_client_id(client_id: str) -> str | None:
    # Un client_id OAuth de Google es `<project_number>-<hash>.apps.googleusercontent.com`.
    m = re.match(r"(\d+)-", client_id or "")
    return m.group(1) if m else None


def precheck(remote: str) -> int:
    nombre = (remote or "").rstrip(":")  # `config show` no lleva el ':' del remote
    try:
        r = subprocess.run(
            ["rclone", "config", "show", nombre],
            capture_output=True, encoding="utf-8", errors="replace", timeout=15,
        )
    except subprocess.TimeoutExpired:
        return 5
    except FileNotFoundError:
        return 4
    if r.returncode != 0 or _REMOTE_INEXISTENTE in (r.stdout or ""):
        return 4
    cid = client_id_de_config(r.stdout)
    if not cid:
        return 3
    project = project_de_client_id(cid)
    if project and project != _CLIENT_COMPARTIDO_PROJECT:
        return 0
    return 3


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: precheck_rclone.py <remote>  (p. ej. gdrive_tl:)")
        return 2
    code = precheck(argv[1])
    # Solo un veredicto legible; JAMÁS el stdout de rclone (secretos en claro).
    print({0: "client propio: rcd primario", 3: "client compartido: copia secuencial",
           4: "rclone no instalado o el remote no existe: copia secuencial",
           5: "rclone tardó demasiado en responder: copia secuencial (reintenta si otra "
              "corrida de rclone estaba en marcha)"}.get(code, "uso incorrecto"))
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
