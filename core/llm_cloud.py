"""Conector LLM cloud intercambiable — Scaleway / Mistral / OpenAI-compatible.

Capa fina sobre la API Chat Completions (estándar OpenAI). Cambiar de
proveedor = cambiar base_url + model + api_key en variables de entorno.

Credenciales (variables de entorno de USUARIO de Windows, NO en .env):
    LLM_CLOUD_API_KEY     — API key del proveedor
    LLM_CLOUD_BASE_URL    — base URL (default: Scaleway Generative APIs)
    LLM_CLOUD_MODEL       — modelo (default: mistral-small-latest)

La API key NUNCA pasa por el prompt ni se loguea.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("feesdefender.llm_cloud")

_DEFAULT_BASE_URL = "https://api.scaleway.ai/v1"
_DEFAULT_MODEL = "mistral-small-3.2-24b-instruct-2506"
_DEFAULT_TIMEOUT = 30


class LLMCloudError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMCloudConfig:
    base_url: str
    api_key: str
    model: str
    timeout_s: int = _DEFAULT_TIMEOUT

    @classmethod
    def from_env(cls) -> "LLMCloudConfig":
        key = os.getenv("LLM_CLOUD_API_KEY", "").strip()
        if not key:
            raise LLMCloudError(
                "Falta LLM_CLOUD_API_KEY en variables de entorno. "
                "Configúrala como variable de entorno de usuario de Windows."
            )
        return cls(
            base_url=(os.getenv("LLM_CLOUD_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/"),
            api_key=key,
            model=os.getenv("LLM_CLOUD_MODEL") or _DEFAULT_MODEL,
            timeout_s=int(os.getenv("LLM_CLOUD_TIMEOUT_S") or _DEFAULT_TIMEOUT),
        )


def chat_json(
    messages: list[dict[str, str]],
    *,
    config: LLMCloudConfig | None = None,
    json_schema: dict[str, Any] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Envía mensajes al LLM y devuelve la respuesta parseada como dict JSON.

    Args:
        messages: Lista de mensajes [{role, content}].
        config: Configuración del LLM (default: from_env()).
        json_schema: Schema JSON para response_format (structured output).
        temperature: Temperatura de generación.
        max_tokens: Límite de tokens de salida.

    Returns:
        Dict con la respuesta JSON parseada del modelo.

    Raises:
        LLMCloudError: Si la API falla o la respuesta no es JSON válido.
    """
    cfg = config or LLMCloudConfig.from_env()

    body: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    if json_schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": json_schema},
        }

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    url = f"{cfg.base_url}/chat/completions"

    try:
        r = httpx.post(url, json=body, headers=headers, timeout=cfg.timeout_s)
    except httpx.TimeoutException as exc:
        raise LLMCloudError(f"Timeout llamando a {cfg.base_url}: {exc}") from exc
    except httpx.HTTPError as exc:
        raise LLMCloudError(f"Error HTTP llamando a {cfg.base_url}: {exc}") from exc

    if r.status_code != 200:
        raise LLMCloudError(
            f"LLM API respondió HTTP {r.status_code}: {r.text[:500]}"
        )

    try:
        data = r.json()
    except Exception as exc:
        raise LLMCloudError(f"Respuesta no es JSON: {r.text[:500]}") from exc

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMCloudError(
            f"El modelo no devolvió JSON válido: {content[:500]}"
        ) from exc
