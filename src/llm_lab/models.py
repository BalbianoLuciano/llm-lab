"""Shared client for calling free LLMs through their APIs.

Every provider here speaks the same protocol (OpenAI Chat Completions), so a single SDK is
enough: only the base URL and the key change. If a provider rejects the request for rate
limits (429) or fails (5xx), the next model in the chain is tried.

    from llm_lab.models import complete, DEFAULT_CHAIN
    r = complete([{"role": "user", "content": "Hola"}], DEFAULT_CHAIN)
    print(r.text, r.model, r.input_tokens, r.latency_s)
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path

import openai
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


@dataclass(frozen=True)
class Model:
    provider: str
    id: str

    def __str__(self) -> str:
        return f"{self.provider}/{self.id}"


@dataclass
class Response:
    text: str
    model: Model
    input_tokens: int
    output_tokens: int
    latency_s: float
    failed_attempts: list[str]


# Fallback order: largest daily quota first, smallest last.
DEFAULT_CHAIN = [
    Model("groq", "qwen/qwen3.8-27b"),  # lab 01: the fastest one, no reasoning
    Model("nvidia", "z-ai/glm-5.3"),
    Model("groq", "openai/gpt-oss-120b"),
    Model("gemini", "gemini-3.5-flash"),
    Model("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
]

_clients: dict[str, openai.OpenAI] = {}


def client(provider: str) -> openai.OpenAI:
    if provider not in _clients:
        url, env_var = PROVIDERS[provider]
        key = os.getenv(env_var, "").strip()
        if not key:
            raise RuntimeError(f"Missing {env_var} in .env")
        # max_retries=0: on a 429 we'd rather jump to the next provider than wait
        _clients[provider] = openai.OpenAI(base_url=url, api_key=key, max_retries=0,
                                           timeout=120)
    return _clients[provider]


def complete(
    messages: list[dict],
    models: Model | list[Model],
    temperature: float = 0.0,
    max_tokens: int | None = None,
    allow_empty: bool = False,
) -> Response:
    chain = [models] if isinstance(models, Model) else models
    failed = []
    for model in chain:
        start = time.perf_counter()
        try:
            r = client(model.provider).chat.completions.create(
                model=model.id, messages=messages, temperature=temperature,
                max_tokens=max_tokens,
            )
        except (openai.RateLimitError, openai.InternalServerError, openai.APITimeoutError,
                openai.APIConnectionError) as e:
            failed.append(f"{model}: {type(e).__name__}")
            continue
        text = r.choices[0].message.content or ""
        if not text.strip() and not allow_empty:
            # Lab 01: a reasoning model that runs out of max_tokens returns empty, with no error
            failed.append(f"{model}: empty response ({r.choices[0].finish_reason})")
            continue
        return Response(
            text=text,
            model=model,
            input_tokens=r.usage.prompt_tokens if r.usage else 0,
            output_tokens=r.usage.completion_tokens if r.usage else 0,
            latency_s=round(time.perf_counter() - start, 2),
            failed_attempts=failed,
        )
    raise RuntimeError(f"No model answered: {failed}")
