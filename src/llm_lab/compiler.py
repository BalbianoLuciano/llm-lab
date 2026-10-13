"""Compile a rule written in natural language into a typed Rule, or ask for clarification.

    result = compile_rule("Los links tienen que decir a dónde llevan...")
    result.status  # "ok" -> result.rule is a Rule; "ambiguous" -> result.clarification

Lab 02 finding: validate with Pydantic and send the error back to the model (retry) instead of
trusting the raw answer.
"""

import json
from typing import Literal

from pydantic import BaseModel, ValidationError

from llm_lab.models import DEFAULT_CHAIN, Model, complete
from llm_lab.rules import Rule

SYSTEM = """Compilás reglas de calidad para documentos de trámites públicos. Una persona escribe
la regla en lenguaje natural y vos la convertís en una definición tipada que después evalúa un
modelo, bloque por bloque o sobre el documento entero.

Criterios:
- kind: "deterministic" si se puede chequear con código sin entender el texto (contar palabras,
  mayúsculas, formato de un mail); si no, "semantic".
- scope: "document" si hay que mirar el documento entero (algo que tiene que aparecer en algún
  lugar, o la primera vez que aparece); "block" si alcanza con mirar cada bloque.
- applies_to: los tipos de bloque donde tiene sentido: heading, paragraph, list_item, table.
- question: una pregunta sobre el bloque, en español, que se pueda responder mirando el texto.
- levels: qué significa green, yellow y red, concretos y verificables. Son la explicación que ve
  la persona, así que tienen que ser cortos.
- blocking: true si la persona dice que bloquea o no se publica; si no lo dice, true solo para
  WCAG nivel A e integridad de datos (moneda, fechas, vigencia, emisor), false para el resto.
- source: la norma que menciona la persona, tal cual; si no menciona ninguna, la más cercana de
  WCAG 2.2, ISO 24495-1 (lenguaje claro), ISO 4217, ISO 8601 o Dublin Core.
- examples: dos ejemplos cortos inventados, uno que cumpla (green) y uno que no (red).

Si la regla es vaga y no se puede evaluar de forma verificable ("que sea claro", "que esté bien"),
no inventes: devolvé status "ambiguous" y en clarification pedí un ejemplo de bloque que cumple y
uno que no, o el criterio concreto."""


class CompileResult(BaseModel):
    status: Literal["ok", "ambiguous"]
    rule: Rule | None = None
    clarification: str | None = None


def _schema_hint() -> str:
    return json.dumps(CompileResult.model_json_schema(), ensure_ascii=False)


def compile_rule(text: str, models: Model | list[Model] = DEFAULT_CHAIN,
                 max_retries: int = 2) -> tuple[CompileResult | None, int, str | None]:
    """Returns (result or None, attempts, last error)."""
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Regla:\n{text}\n\nRespondé solo con un JSON que "
                                            f"cumpla este esquema:\n{_schema_hint()}"}]
    error = None
    for attempt in range(1, max_retries + 2):
        r = complete(messages, models, response_format={"type": "json_object"})
        try:
            result = CompileResult.model_validate_json(r.text)
            if result.status == "ok" and result.rule is None:
                raise ValueError("status ok sin rule")
            if result.status == "ambiguous" and not result.clarification:
                raise ValueError("status ambiguous sin clarification")
            return result, attempt, None
        except (ValidationError, ValueError) as e:
            error = str(e)[:300]
            messages += [{"role": "assistant", "content": r.text},
                         {"role": "user", "content": f"No es válido: {error}. Corregilo y "
                                                     "devolvé solo el JSON."}]
    return None, max_retries + 1, error
