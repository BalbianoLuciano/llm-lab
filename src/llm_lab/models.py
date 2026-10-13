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
    Model("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
    Model("gemini", "gemini-3.5-flash"),  # lab 02: 20 requests/day on the free tier
    Model("local", "mlx-community/Qwen3.5-9B-4bit"),  # lab 16: no quota, last resort
]

_clients: dict[str, openai.OpenAI] = {}
_local: dict[str, tuple] = {}


def _complete_local(model: Model, messages: list[dict], max_tokens: int | None) -> tuple[str, int, int]:
    """Provider "local": an MLX model on this machine. No quotas, slower (lab 16: Groq's free
    tier caps each model at 200k tokens a day, and the full experiment needs more)."""
    from mlx_lm import generate, load
    if model.id not in _local:
        _local[model.id] = load(model.id)
    mlx_model, tokenizer = _local[model.id]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                           enable_thinking=False)
    text = generate(mlx_model, tokenizer, prompt=prompt, max_tokens=max_tokens or 512)
    return text, len(prompt), len(tokenizer.encode(text))


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
    response_format: dict | None = None,
) -> Response:
    chain = [models] if isinstance(models, Model) else models
    failed = []
    for model in chain:
        start = time.perf_counter()
        if model.provider == "local":
            text, n_in, n_out = _complete_local(model, messages, max_tokens)
            return Response(text=text, model=model, input_tokens=n_in, output_tokens=n_out,
                            latency_s=round(time.perf_counter() - start, 2),
                            failed_attempts=failed)
        try:
            extra = {"response_format": response_format} if response_format else {}
            r = client(model.provider).chat.completions.create(
                model=model.id, messages=messages, temperature=temperature,
                max_tokens=max_tokens, **extra,
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


def stream(messages: list[dict], models: Model | list[Model], temperature: float = 0.0):
    """Yield the answer token by token (for the app's chat). Falls back to the next model only
    if a provider fails before the first token; after that, an error is raised."""
    chain = [models] if isinstance(models, Model) else models
    failed = []
    for model in chain:
        try:
            response = client(model.provider).chat.completions.create(
                model=model.id, messages=messages, temperature=temperature, stream=True)
            started = False
            for chunk in response:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    started = True
                    yield delta
            if started:
                return
            failed.append(f"{model}: empty stream")
        except (openai.RateLimitError, openai.InternalServerError, openai.APITimeoutError,
                openai.APIConnectionError) as e:
            failed.append(f"{model}: {type(e).__name__}")
    raise RuntimeError(f"No model answered: {failed}")
