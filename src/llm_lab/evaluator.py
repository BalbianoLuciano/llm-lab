"""The quality gate's evaluators: given a block in context and a rule, return a level and a
probability for each level.

    ev = LogprobsEvaluator("mlx-community/Qwen3.5-4B-4bit", permutations=2)
    verdict = ev.evaluate(state, rule)       # Verdict(level="red", probs={...})

Three implementations behind the same interface (docs/sdd-semaforo.md §5.3):
- LogprobsEvaluator: local model with mlx-lm; reads the next-token distribution over the option
  letters in one forward pass. Never generates text.
- LibraryEvaluator: the same idea through `so1` (open-alternative-jev), Hugging Face backend.
- GenerativeEvaluator: an API model asked for JSON with level and confidence (baseline).
"""

import json
import math
import re
from dataclasses import dataclass
from typing import Protocol

from llm_lab.blocks import Document
from llm_lab.chunking import block_text
from llm_lab.models import Model, complete
from llm_lab.rules import Rule

LEVELS = ["green", "yellow", "red"]
INSTRUCTION = ("Evaluás un fragmento de un documento público contra una regla de calidad. "
               "Mirá solo el bloque marcado; el resto es contexto.")


@dataclass
class Verdict:
    level: str
    probs: dict[str, float]

    @property
    def confidence(self) -> float:
        return self.probs[self.level]


class Evaluator(Protocol):
    def evaluate(self, state: str, rule: Rule) -> Verdict: ...


def build_state(doc: Document, index: int, window_chars: int = 300) -> str:
    """Title, heading path, previous and next block (trimmed) and the block under evaluation."""
    block = doc.blocks[index]
    prev = block_text(doc.blocks[index - 1])[-window_chars:] if index > 0 else ""
    nxt = block_text(doc.blocks[index + 1])[:window_chars] if index + 1 < len(doc.blocks) else ""
    return (f"Documento: {doc.meta.get('title', doc.id)}\n"
            f"Sección: {' > '.join(block.path) or '(sin sección)'}\n\n"
            f"[Bloque anterior]\n{prev or '(ninguno)'}\n\n"
            f"[BLOQUE A EVALUAR]\n{block_text(block)}\n\n"
            f"[Bloque siguiente]\n{nxt or '(ninguno)'}")


def _orders(permutations: int) -> list[list[int]]:
    return [[0, 1, 2], [2, 1, 0]][:permutations]


def _question(rule: Rule, order: list[int]) -> tuple[str, list[str]]:
    letters = "ABC"
    options = [getattr(rule.levels, LEVELS[i]) for i in order]
    text = (f"Regla ({rule.source}): {rule.question}\n"
            + "\n".join(f"{letters[k]}. {opt}" for k, opt in enumerate(options)))
    return text, [LEVELS[i] for i in order]


def _softmax(xs: list[float], temperature: float = 1.0) -> list[float]:
    m = max(xs)
    e = [math.exp((x - m) / temperature) for x in xs]
    s = sum(e)
    return [x / s for x in e]


class LogprobsEvaluator:
    def __init__(self, model_id: str, permutations: int = 1, temperature: float = 1.0):
        from mlx_lm import load
        self.model, self.tokenizer = load(model_id)
        self.permutations = permutations
        self.temperature = temperature
        self.letter_ids = [self.tokenizer.encode(x, add_special_tokens=False)[0] for x in "ABC"]

    def letter_logits(self, state: str, question: str) -> list[float]:
        import mlx.core as mx
        messages = [{"role": "user", "content": f"{INSTRUCTION}\n\n{state}\n\n{question}\n\n"
                                                "Respondé solo con la letra de la opción."}]
        ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                 enable_thinking=False)
        logits = self.model(mx.array([ids]))[0, -1]
        return [float(logits[i]) for i in self.letter_ids]

    def raw_scores(self, state: str, rule: Rule) -> list[list[float]]:
        """Letter logits mapped back to [green, yellow, red], once per option order."""
        out = []
        for order in _orders(self.permutations):
            question, levels = _question(rule, order)
            logits = self.letter_logits(state, question)
            by_level = dict(zip(levels, logits))
            out.append([by_level[lv] for lv in LEVELS])
        return out

    def evaluate(self, state: str, rule: Rule) -> Verdict:
        runs = [_softmax(s, self.temperature) for s in self.raw_scores(state, rule)]
        probs = [sum(r[i] for r in runs) / len(runs) for i in range(3)]
        return _verdict(probs)


class LibraryEvaluator:
    def __init__(self, model_id: str, permutations: int = 1):
        from so1 import Decider
        self.decider = Decider.from_pretrained(model_id, backend="hf", device_map="mps",
                                               mode="separate", permutations=permutations)

    def evaluate(self, state: str, rule: Rule) -> Verdict:
        from so1 import Choice
        options = [getattr(rule.levels, lv) for lv in LEVELS]
        decision = self.decider.decide(f"{INSTRUCTION}\n\n{state}",
                                       [Choice(f"Regla ({rule.source}): {rule.question}",
                                               options)])[0]
        return _verdict(list(decision.probabilities))


class GenerativeEvaluator:
    def __init__(self, model: Model):
        self.model = model

    def evaluate(self, state: str, rule: Rule) -> Verdict:
        question, _ = _question(rule, [0, 1, 2])
        prompt = (f"{INSTRUCTION}\n\n{state}\n\n{question}\n\nRespondé solo con JSON: "
                  '{"opcion": "A"|"B"|"C", "confianza": número entre 0 y 1}')
        r = complete([{"role": "user", "content": prompt}], self.model,
                     response_format={"type": "json_object"}, max_tokens=100)
        match = re.search(r"\{.*\}", r.text, re.DOTALL)  # local models may wrap it in ```json
        data = json.loads(match.group() if match else r.text)
        level = LEVELS["ABC".index(data["opcion"].strip().upper()[0])]
        conf = min(max(float(data["confianza"]), 0.0), 1.0)
        rest = (1 - conf) / 2  # verbalised confidence says nothing about the other two levels
        return Verdict(level, {lv: conf if lv == level else rest for lv in LEVELS})


def _verdict(probs: list[float]) -> Verdict:
    best = max(range(3), key=lambda i: probs[i])
    return Verdict(LEVELS[best], dict(zip(LEVELS, probs)))


# ---------------------------------------------------------------- calibration


def fit_temperature(scores: list[list[float]], labels: list[int]) -> float:
    """The T that minimises negative log-likelihood of softmax(scores / T) on labelled data."""
    def nll(t):
        return -sum(math.log(max(_softmax(s, t)[y], 1e-12)) for s, y in zip(scores, labels))
    grid = [0.25 + 0.05 * i for i in range(156)]  # 0.25 .. 8.0
    return min(grid, key=nll)


def expected_calibration_error(confidences: list[float], correct: list[bool],
                               bins: int = 5) -> float:
    """Average |confidence - accuracy| over confidence bins, weighted by bin size."""
    total, n = 0.0, len(confidences)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(confidences) if lo < c <= hi or (b == 0 and c == lo)]
        if idx:
            acc = sum(correct[i] for i in idx) / len(idx)
            conf = sum(confidences[i] for i in idx) / len(idx)
            total += len(idx) / n * abs(conf - acc)
    return total
