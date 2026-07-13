"""Doble de test del `service` de googleapiclient (Gmail v1).

Imita la interfaz fluida anidada de Gmail:
    service.users().messages().<metodo>(**kw).execute()
    service.users().threads().<metodo>(**kw).execute()
    service.users().labels().<metodo>(**kw).execute()
Registra las llamadas para aserciones.
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

    `responses`: método -> resultado único, o método -> lista consumida FIFO.
    Si un método no tiene respuesta, devuelve {}.
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


class _FakeUsers:
    def __init__(self, messages, threads, labels):
        self._messages = _FakeCollection(messages)
        self._threads = _FakeCollection(threads)
        self._labels = _FakeCollection(labels)

    def messages(self):
        return self._messages

    def threads(self):
        return self._threads

    def labels(self):
        return self._labels


class FakeGmailService:
    def __init__(self, *, messages=None, threads=None, labels=None):
        self._users = _FakeUsers(messages, threads, labels)

    def users(self):
        return self._users

    def recorded(self, collection: str):
        """Lista de (metodo, kwargs) llamados sobre 'messages'|'threads'|'labels'."""
        return {
            "messages": self._users._messages,
            "threads": self._users._threads,
            "labels": self._users._labels,
        }[collection].calls
