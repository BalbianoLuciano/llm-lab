"""Guided review: rewrite one red block with the person's answer, then check the rewrite.

    new = rewrite_block(state, block, rule, answer)
    invented = new_numbers(block, answer, new)          # deterministic guardrail
    verdicts = guardrails(evaluator, block, answer, new)  # evaluator-based guardrails

The rewrite may only use what is in the original block and in the person's answer. When the
answer does not bring the missing data, the model must leave a visible [FALTA: ...] marker
instead of filling the gap.
"""

import re

from llm_lab.evaluator import Evaluator, Verdict
from llm_lab.models import DEFAULT_CHAIN, Model, complete
from llm_lab.rules import Levels, Rule

SYSTEM = """Corregís un bloque de un documento público para que cumpla una regla de calidad.
Reglas estrictas:
- Usá solo información que esté en el bloque original o en la respuesta de la persona.
- Si la respuesta no trae el dato que falta, no lo inventes: dejá el bloque como está y agregá
  una marca visible [FALTA: qué dato falta].
- Cambiá lo mínimo necesario. Conservá el formato: si es una tabla, devolvé una tabla en
  markdown; si es un ítem de lista, un ítem.
- Devolvé solo el bloque corregido, sin explicaciones."""


def rewrite_block(state: str, block: str, rule: Rule, answer: str,
                  models: Model | list[Model] = DEFAULT_CHAIN) -> str:
    prompt = (f"Contexto:\n{state}\n\nRegla que no cumple: {rule.question}\n"
              f"Qué falla: {rule.levels.red}\nCómo tiene que quedar: {rule.levels.green}\n\n"
              f"Bloque original:\n{block}\n\nRespuesta de la persona:\n{answer}")
    r = complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                 models)
    return r.text.strip()


def _numbers(text: str) -> set[str]:
    """Numbers normalised: '$ 1.350.000' and '1350000' are the same; '65/100' kept as is."""
    out = set()
    for m in re.findall(r"\d[\d.,/]*\d|\d", text):
        digits = re.sub(r"[.,](?=\d{3}\b)", "", m)  # thousands separators
        out.add(digits.replace(",", "."))
    return out


def new_numbers(original: str, answer: str, rewrite: str) -> set[str]:
    """Numbers in the rewrite that appear neither in the original nor in the answer."""
    return _numbers(rewrite) - _numbers(original) - _numbers(answer)


INVENTS = Rule(
    id="guardrail-inventa", source="lab 15", kind="semantic", scope="block",
    applies_to=["paragraph", "list_item", "table", "heading"],
    question=("Comparando la REESCRITURA con el ORIGINAL y la RESPUESTA DE LA PERSONA: "
              "¿la reescritura agrega algún dato (monto, fecha, nombre, plazo, lugar) que no "
              "está ni en el original ni en la respuesta?"),
    levels=Levels(green="No agrega datos: todo sale del original o de la respuesta.",
                  yellow="Agrega una aclaración menor sin datos nuevos.",
                  red="Agrega un dato que no está ni en el original ni en la respuesta."),
    blocking=True)

MEANING = Rule(
    id="guardrail-sentido", source="lab 15", kind="semantic", scope="block",
    applies_to=["paragraph", "list_item", "table", "heading"],
    question=("¿La REESCRITURA dice lo mismo que el ORIGINAL, salvo lo que pidió corregir la "
              "regla?"),
    levels=Levels(green="Dice lo mismo, con la corrección pedida.",
                  yellow="Cambia el tono o el orden, pero no el contenido.",
                  red="Cambia el significado: agrega, quita o contradice contenido."),
    blocking=True)


def guardrails(evaluator: Evaluator, original: str, answer: str,
               rewrite: str) -> dict[str, Verdict]:
    state = (f"[ORIGINAL]\n{original}\n\n[RESPUESTA DE LA PERSONA]\n{answer}\n\n"
             f"[BLOQUE A EVALUAR: REESCRITURA]\n{rewrite}")
    return {"inventa": evaluator.evaluate(state, INVENTS),
            "sentido": evaluator.evaluate(state, MEANING)}
