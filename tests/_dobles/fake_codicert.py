"""Doble del cliente HTTP de Codicert. Ningún test de la suite alcanza la red."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Respuesta:
    status_code: int
    _json: Any
    content: bytes = b""

    def json(self) -> Any:
        return self._json


@dataclass
class FakeCliente:
    """Mapea `(metodo, sufijo_de_ruta)` a `(status, json)` o a `(status, json, bytes)`."""

    guion: dict[tuple[str, str], tuple] = field(default_factory=dict)
    llamadas: list[tuple[str, str, dict]] = field(default_factory=list)

    def request(self, metodo: str, url: str, **kw: Any) -> _Respuesta:
        self.llamadas.append((metodo, url, kw))
        for (m, sufijo), resp in self.guion.items():
            if m == metodo and url.endswith(sufijo):
                return _Respuesta(resp[0], resp[1], resp[2] if len(resp) > 2 else b"")
        raise AssertionError(f"el doble no tiene guion para {metodo} {url}")
