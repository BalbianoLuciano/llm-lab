"""Cliente común para llamar a LLMs gratuitos por API.

Todos los proveedores de acá hablan el mismo protocolo (el de Chat Completions de OpenAI),
así que alcanza con un solo SDK cambiando la URL base y la clave. Si un proveedor rechaza
el pedido por límite de uso (429) o falla (5xx), se pasa al siguiente modelo de la cadena.

    from llm_lab.modelos import completar, CADENA_DEFECTO
    r = completar([{"role": "user", "content": "Hola"}], CADENA_DEFECTO)
    print(r.texto, r.modelo, r.tokens_entrada, r.latencia_s)
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path

import openai
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

PROVEEDORES = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


@dataclass(frozen=True)
class Modelo:
    proveedor: str
    id: str

    def __str__(self) -> str:
        return f"{self.proveedor}/{self.id}"


@dataclass
class Respuesta:
    texto: str
    modelo: Modelo
    tokens_entrada: int
    tokens_salida: int
    latencia_s: float
    intentos_fallidos: list[str]


# Orden de respaldo: primero los de mayor cupo diario, al final los de cupo más chico.
CADENA_DEFECTO = [
    Modelo("groq", "qwen/qwen3.8-27b"),  # lab 01: el más rápido, sin razonamiento
    Modelo("nvidia", "z-ai/glm-5.3"),
    Modelo("groq", "openai/gpt-oss-120b"),
    Modelo("gemini", "gemini-3.5-flash"),
    Modelo("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
]

_clientes: dict[str, openai.OpenAI] = {}


def cliente(proveedor: str) -> openai.OpenAI:
    if proveedor not in _clientes:
        url, variable = PROVEEDORES[proveedor]
        clave = os.getenv(variable, "").strip()
        if not clave:
            raise RuntimeError(f"Falta {variable} en .env")
        # max_retries=0: ante un 429 preferimos saltar al siguiente proveedor y no esperar
        _clientes[proveedor] = openai.OpenAI(base_url=url, api_key=clave, max_retries=0,
                                             timeout=120)
    return _clientes[proveedor]


def completar(
    mensajes: list[dict],
    modelos: Modelo | list[Modelo],
    temperature: float = 0.0,
    max_tokens: int | None = None,
    aceptar_vacia: bool = False,
) -> Respuesta:
    cadena = [modelos] if isinstance(modelos, Modelo) else modelos
    fallidos = []
    for modelo in cadena:
        inicio = time.perf_counter()
        try:
            r = cliente(modelo.proveedor).chat.completions.create(
                model=modelo.id, messages=mensajes, temperature=temperature,
                max_tokens=max_tokens,
            )
        except (openai.RateLimitError, openai.InternalServerError, openai.APITimeoutError,
                openai.APIConnectionError) as e:
            fallidos.append(f"{modelo}: {type(e).__name__}")
            continue
        texto = r.choices[0].message.content or ""
        if not texto.strip() and not aceptar_vacia:
            # Lab 01: un modelo que razona y se queda sin max_tokens devuelve vacío, sin error
            fallidos.append(f"{modelo}: respuesta vacía ({r.choices[0].finish_reason})")
            continue
        return Respuesta(
            texto=texto,
            modelo=modelo,
            tokens_entrada=r.usage.prompt_tokens if r.usage else 0,
            tokens_salida=r.usage.completion_tokens if r.usage else 0,
            latencia_s=round(time.perf_counter() - inicio, 2),
            intentos_fallidos=fallidos,
        )
    raise RuntimeError(f"Ningún modelo respondió: {fallidos}")
