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

import dataclasses
import os
import re
import socket
import uuid
from datetime import datetime

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
