"""Resolución de credenciales de Codicert: entorno, .env de la raíz real y registro."""
from __future__ import annotations

import pytest

from core import codicert


def test_credenciales_del_sandbox_salen_del_entorno(monkeypatch):
    monkeypatch.setenv("CODICERT_SANDBOX_USUARIO", "engelvoelkersalfa")
    monkeypatch.setenv("CODICERT_SANDBOX_CLAVE", "secreto")
    assert codicert.credenciales(None, "sandbox") == ("engelvoelkersalfa", "secreto")


def test_credenciales_de_una_plaza_usan_su_prefijo(monkeypatch):
    monkeypatch.setenv("CODICERT_MADRID_USUARIO", "madrid.bd")
    monkeypatch.setenv("CODICERT_MADRID_CLAVE", "secreto")
    assert codicert.credenciales("Madrid", "produccion") == ("madrid.bd", "secreto")


def test_san_sebastian_no_lleva_espacio_ni_tilde_en_la_variable(monkeypatch):
    monkeypatch.setenv("CODICERT_SANSEBASTIAN_USUARIO", "sansebastian.bd")
    monkeypatch.setenv("CODICERT_SANSEBASTIAN_CLAVE", "secreto")
    assert codicert.credenciales("San Sebastián", "produccion")[0] == "sansebastian.bd"


def test_sin_credencial_el_error_NO_filtra_el_valor(monkeypatch):
    monkeypatch.delenv("CODICERT_SEVILLA_CLAVE", raising=False)
    monkeypatch.delenv("CODICERT_SEVILLA_USUARIO", raising=False)
    monkeypatch.setattr(codicert, "_de_fuentes_lentas", lambda nombre: None)
    with pytest.raises(codicert.CodicertAuthError) as exc:
        codicert.credenciales("Sevilla", "produccion")
    assert "CODICERT_SEVILLA_CLAVE" in str(exc.value)


def test_una_ciudad_desconocida_no_inventa_prefijo():
    with pytest.raises(codicert.CodicertError):
        codicert.credenciales("Cuenca", "produccion")
