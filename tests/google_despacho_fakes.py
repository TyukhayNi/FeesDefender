"""Doble de test del `service` de googleapiclient (Drive v3).

Imita la interfaz fluida: service.<coleccion>().<metodo>(**kw).execute().
Para media, .execute() devuelve bytes (comportamiento real de get_media/
export_media en googleapiclient). Registra las llamadas para aserciones.
"""
from __future__ import annotations


class _FakeRequest:
    def __init__(self, result):
        self._result = result

    def execute(self):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeCollection:
    """Resultados enlatados por método.

    `responses`: método -> resultado único, o método -> lista de resultados
    consumidos FIFO (para paginación). Si un método no tiene respuesta, devuelve {}.
    """
    def __init__(self, responses):
        self._responses = {
            k: (list(v) if isinstance(v, list) else v)
            for k, v in (responses or {}).items()
        }
        self.calls = []

    def __getattr__(self, method):
        def _call(**kwargs):
            self.calls.append((method, kwargs))
            resp = self._responses.get(method)
            if isinstance(resp, list):
                result = resp.pop(0) if resp else {}
            else:
                result = {} if resp is None else resp
            return _FakeRequest(result)
        return _call


class FakeService:
    def __init__(self, *, files=None, drives=None, about=None, permissions=None):
        self._c = {
            "files": _FakeCollection(files),
            "drives": _FakeCollection(drives),
            "about": _FakeCollection(about),
            "permissions": _FakeCollection(permissions),
        }

    def files(self):
        return self._c["files"]

    def drives(self):
        return self._c["drives"]

    def about(self):
        return self._c["about"]

    def permissions(self):
        return self._c["permissions"]

    def recorded(self, collection: str):
        """Lista de (metodo, kwargs) llamados sobre una colección."""
        return self._c[collection].calls
