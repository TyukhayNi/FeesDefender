"""Cliente LLM local (Ollama) — infraestructura reusable del Sprint 1.

Capa HTTP sobre Ollama (`/api/generate`, `/api/tags`) pensada para los
consumidores que necesitan procesar material con PII **sin que salga del
entorno local del despacho**. A diferencia de ``core/llm.py`` (cliente fino
preexistente), este módulo expone:

- Excepciones tipadas (``LLMLocalUnavailableError``, ``LLMLocalTimeoutError``).
- Retry con backoff para errores transitorios (timeout, 5xx).
- ``complete_json`` con validación de esquema opcional.
- ``warmup`` / ``health_check`` para arranque controlado.

**No hay fallback a la API de Anthropic.** Si Ollama no está disponible, las
llamadas fallan ruidosamente con ``LLMLocalUnavailableError`` y un mensaje
accionable. Es deliberado: el sentido de esta capa es que los originales con
PII jamás se envíen a un proveedor externo (posición RGPD/RIA del despacho).

Configuración (variables de entorno, ver ``.env.example``):
    LLM_LOCAL_BASE_URL    (default http://127.0.0.1:11434)
    LLM_LOCAL_MODEL       (default qwen2.5:14b-instruct-q4_K_M)
    LLM_LOCAL_TIMEOUT     (segundos, default 120)
    LLM_LOCAL_TEMPERATURE (default 0.1)
"""

from __future__ import annotations

import json
import logging
import os
import time

import httpx

# Importar config asegura que load_dotenv() ya corrió y .env está cargado.
from core import config as _config  # noqa: F401

logger = logging.getLogger("feesdefender.llm_local")


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class LLMLocalError(RuntimeError):
    """Error genérico de la capa LLM local."""


class LLMLocalUnavailableError(LLMLocalError):
    """Ollama no responde (servicio caído, puerto cerrado, modelo ausente)."""


class LLMLocalTimeoutError(LLMLocalError):
    """La llamada superó el timeout configurado."""


# ---------------------------------------------------------------------------
# Configuración (lectura perezosa para que los tests puedan monkeypatchear env)
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "qwen2.5:14b-instruct-q4_K_M"
_DEFAULT_TIMEOUT = 120.0
_DEFAULT_TEMPERATURE = 0.1

_RETRY_DELAYS = (1.0, 2.0, 4.0)  # backoff exponencial; 3 intentos


def _cfg() -> tuple[str, str, float, float]:
    base = os.getenv("LLM_LOCAL_BASE_URL", _DEFAULT_BASE_URL)
    model = os.getenv("LLM_LOCAL_MODEL", _DEFAULT_MODEL)
    timeout = float(os.getenv("LLM_LOCAL_TIMEOUT", str(_DEFAULT_TIMEOUT)))
    temperature = float(os.getenv("LLM_LOCAL_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))
    return base, model, timeout, temperature


def configured_model() -> str:
    """Nombre del modelo Ollama configurado (para trazabilidad/audit)."""
    return _cfg()[1]


def _arranque_accionable(base: str, model: str) -> str:
    return (
        f"Ollama no está disponible en {base}. Arráncalo y descarga el modelo:\n"
        f"  ollama serve\n"
        f"  ollama pull {model}"
    )


# ---------------------------------------------------------------------------
# Transporte con retry
# ---------------------------------------------------------------------------

def _post_with_retry(url: str, payload: dict, timeout: float) -> dict:
    """POST a Ollama con retry para errores transitorios (timeout, 5xx).

    No reintenta ConnectError (servicio caído) ni 4xx: se traducen de
    inmediato a la excepción tipada correspondiente.
    """
    base, model, *_ = _cfg()
    last_exc: Exception | None = None

    for attempt in range(len(_RETRY_DELAYS)):
        try:
            with httpx.Client(timeout=timeout) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                return r.json()
        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.debug("Timeout Ollama (intento %d/%d)", attempt + 1, len(_RETRY_DELAYS))
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if 500 <= status < 600:
                last_exc = exc
                logger.debug("Ollama %d (intento %d/%d)", status, attempt + 1, len(_RETRY_DELAYS))
            else:
                raise LLMLocalError(f"Ollama respondió {status}: {exc}") from exc
        except httpx.ConnectError as exc:
            raise LLMLocalUnavailableError(_arranque_accionable(base, model)) from exc
        except httpx.HTTPError as exc:
            raise LLMLocalError(f"Fallo HTTP al llamar a Ollama ({url}): {exc}") from exc

        if attempt < len(_RETRY_DELAYS) - 1:
            time.sleep(_RETRY_DELAYS[attempt])

    # Agotados los reintentos.
    if isinstance(last_exc, httpx.TimeoutException):
        raise LLMLocalTimeoutError(
            f"Ollama no respondió en {timeout}s tras {len(_RETRY_DELAYS)} intentos."
        ) from last_exc
    raise LLMLocalUnavailableError(_arranque_accionable(base, model)) from last_exc


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def health_check() -> bool:
    """``True`` si Ollama responde y el modelo configurado está disponible.

    No lanza excepción: ante cualquier fallo devuelve ``False``.
    """
    base, model, *_ = _cfg()
    url = base.rstrip("/") + "/api/tags"
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
            r.raise_for_status()
            names = {m.get("name", "") for m in r.json().get("models", [])}
    except (httpx.HTTPError, ValueError):
        return False
    bases = {n.split(":")[0] for n in names}
    return model in names or model.split(":")[0] in bases


def warmup() -> None:
    """Fuerza la carga del modelo en memoria con una llamada mínima.

    Lanza ``LLMLocalUnavailableError`` si Ollama no está accesible.
    """
    complete("Responde únicamente: OK", max_tokens=1)


def complete(
    prompt: str,
    *,
    system: str | None = None,
    format: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> str:
    """Llamada genérica a ``/api/generate``. Devuelve el texto crudo.

    Si ``format='json'`` se le pide a Ollama salida JSON, pero el parseo es
    responsabilidad del caller (usar ``complete_json`` para parsear+validar).
    """
    _, _, def_timeout, def_temp = _cfg()
    timeout = def_timeout if timeout is None else timeout
    temperature = def_temp if temperature is None else temperature

    options: dict[str, object] = {"temperature": temperature}
    if max_tokens is not None:
        options["num_predict"] = max_tokens

    base, model, *_ = _cfg()
    payload: dict[str, object] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": options,
    }
    if system:
        payload["system"] = system
    if format:
        payload["format"] = format

    url = base.rstrip("/") + "/api/generate"
    data = _post_with_retry(url, payload, timeout)

    text = (data.get("response") or "").strip()
    if not text:
        raise LLMLocalError(f"Respuesta vacía de Ollama. Payload recibido: {data}")
    return text


def complete_json(
    prompt: str,
    *,
    system: str | None = None,
    schema: dict | None = None,
    temperature: float | None = None,
    timeout: float | None = None,
) -> dict:
    """Wrapper sobre ``complete`` con ``format='json'`` + parseo y validación.

    No reintenta ante JSON inválido (decisión de diseño): si el modelo
    devuelve algo no parseable, lanza ``LLMLocalError`` para que el caller
    decida (p. ej. marcar el documento como ``ERROR_PARSEO``).

    Si ``schema`` incluye ``"required"``, se comprueba que todas esas claves
    estén presentes.
    """
    raw = complete(
        prompt,
        system=system,
        format="json",
        temperature=temperature,
        timeout=timeout,
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMLocalError(f"Respuesta de Ollama no es JSON válido: {raw[:300]!r}") from exc

    if not isinstance(data, dict):
        raise LLMLocalError(f"Se esperaba un objeto JSON, se obtuvo {type(data).__name__}")

    if schema and isinstance(schema.get("required"), (list, tuple)):
        missing = [k for k in schema["required"] if k not in data]
        if missing:
            raise LLMLocalError(f"Faltan campos requeridos en la respuesta: {missing}")

    return data
