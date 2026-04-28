"""Cliente Ollama.

Capa fina sobre la API HTTP de Ollama. Toda llamada al LLM en el sistema pasa
por aquí para garantizar trazabilidad (`prompt_id`, `model`, `prompt_hash`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import settings
from .utils import text_sha256


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_hash: str
    prompt_id: str | None = None


def _load_prompt(prompt_id: str) -> str:
    path = settings.prompts_dir / f"{prompt_id}.md"
    if not path.exists():
        raise LLMError(f"Prompt no encontrado: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(prompt_id: str, **vars: object) -> str:
    """Carga `prompts/{prompt_id}.md` y sustituye {{var}} con seguridad."""
    template = _load_prompt(prompt_id)
    rendered = template
    for key, value in vars.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def generate(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    system: str | None = None,
    prompt_id: str | None = None,
) -> LLMResponse:
    """Llamada síncrona a Ollama /api/generate."""
    model = model or settings.ollama_model
    temperature = temperature if temperature is not None else settings.ollama_temperature

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    url = f"{settings.ollama_host.rstrip('/')}/api/generate"
    try:
        with httpx.Client(timeout=settings.ollama_timeout_s) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        raise LLMError(f"Fallo al llamar a Ollama ({url}): {exc}") from exc

    text = data.get("response", "").strip()
    if not text:
        raise LLMError(f"Respuesta vacía de Ollama. Payload: {data}")

    return LLMResponse(
        text=text,
        model=model,
        prompt_hash=text_sha256(prompt),
        prompt_id=prompt_id,
    )


def run_prompt(prompt_id: str, **vars: object) -> LLMResponse:
    """Atajo: renderiza un prompt por id y lo ejecuta."""
    rendered = render_prompt(prompt_id, **vars)
    return generate(rendered, prompt_id=prompt_id)


def healthcheck() -> bool:
    """Comprueba que Ollama responde y que el modelo configurado existe."""
    url = f"{settings.ollama_host.rstrip('/')}/api/tags"
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
            r.raise_for_status()
            tags = {m.get("name", "").split(":")[0] for m in r.json().get("models", [])}
            return settings.ollama_model.split(":")[0] in tags
    except httpx.HTTPError:
        return False
