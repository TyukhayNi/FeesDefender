"""Tests de core/llm_local.py — Sprint 1 (infraestructura LLM local).

Los tests que requieren un Ollama corriendo se marcan con
``@pytest.mark.skipif(not _ollama_running(), ...)`` para que la suite no se
rompa en entornos sin el servicio arrancado. Los tests de modos de fallo
(URL inválida, timeout) no requieren Ollama y corren siempre.
"""

from __future__ import annotations

import pytest

from core import llm_local
from core.llm_local import (
    LLMLocalTimeoutError,
    LLMLocalUnavailableError,
)


def _ollama_running() -> bool:
    return llm_local.health_check()


_REQUIERE_OLLAMA = pytest.mark.skipif(
    not _ollama_running(),
    reason="Ollama no disponible (arranca `ollama serve` y `ollama pull` el modelo).",
)


# ---------------------------------------------------------------------------
# health_check — no requiere Ollama para el caso negativo
# ---------------------------------------------------------------------------

@_REQUIERE_OLLAMA
def test_health_check_with_ollama_running() -> None:
    assert llm_local.health_check() is True


def test_health_check_without_ollama(monkeypatch) -> None:
    # Puerto cerrado → False, nunca excepción.
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://127.0.0.1:1")
    assert llm_local.health_check() is False


# ---------------------------------------------------------------------------
# Modos de fallo — no requieren Ollama
# ---------------------------------------------------------------------------

def test_unavailable_raises_typed(monkeypatch) -> None:
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://127.0.0.1:1")
    with pytest.raises(LLMLocalUnavailableError):
        llm_local.complete("hola")


# ---------------------------------------------------------------------------
# Llamadas reales — requieren Ollama
# ---------------------------------------------------------------------------

@_REQUIERE_OLLAMA
def test_complete_returns_string() -> None:
    out = llm_local.complete("¿Cuál es la capital de España? Responde solo el nombre.")
    assert isinstance(out, str) and out.strip()
    assert "madrid" in out.lower()


@_REQUIERE_OLLAMA
def test_complete_json_parses() -> None:
    out = llm_local.complete_json(
        "Devuelve un objeto JSON con un campo 'pais' cuyo valor sea 'España'."
    )
    assert isinstance(out, dict)
    assert "pais" in out


@_REQUIERE_OLLAMA
def test_timeout_raises(monkeypatch) -> None:
    monkeypatch.setenv("LLM_LOCAL_TIMEOUT", "0.01")
    with pytest.raises(LLMLocalTimeoutError):
        llm_local.complete("Escribe un ensayo largo sobre el derecho civil español.")


@_REQUIERE_OLLAMA
def test_warmup_succeeds() -> None:
    llm_local.warmup()  # no debe lanzar
