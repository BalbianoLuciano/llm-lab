"""Jev's three question types (Choice, Score, Noul) answered by a local model through logprobs.

    s1 = SystemOne("mlx-community/Qwen3.5-4B-4bit")
    answers = s1.ask(state, {
        "level": Choice("¿El monto dice desde cuándo rige?", {"green": "...", "red": "..."}),
        "useful": Score("¿Un asistente podría responder con este fragmento?",
                        ["nada", "poco", "algo", "bastante", "todo"]),
        "visual": Noul("El significado de este bloque depende de su color o formato."),
    })
    answers["visual"]["noul"]        # 0.93
    answers["useful"]["score"]       # 4 (1-based level); "expected" is the probability-weighted mean

The question shapes and the answer fields follow Jev's API (TypeSafe AI), so swapping this class
for its client is a change in one place. Jev is a model trained for calibrated decisions; this
is the open technique behind it (lab 13): read the next-token distribution over the option
letters in one forward pass, never generate, and average two option orders against position
bias. Every question is asked in isolation against the same state, like Jev does.
"""

import math
import string
from dataclasses import dataclass

INSTRUCTION = ("Te doy un estado y una pregunta con opciones. Mirá solo el estado. "
               "Respondé solo con la letra de la opción.")


@dataclass
class Choice:
    instructions: str
    criteria: dict[str, str]  # option name -> what it means


@dataclass
class Score:
    instructions: str
    criteria: list[str]  # rubric, lowest level first


@dataclass
class Noul:
    instructions: str  # a statement; the answer is the probability that it is true


def _softmax(xs: list[float]) -> list[float]:
    m = max(xs)
    e = [math.exp(x - m) for x in xs]
    return [x / sum(e) for x in e]


class SystemOne:
    def __init__(self, model_id: str = "mlx-community/Qwen3.5-4B-4bit", permutations: int = 2):
        from mlx_lm import load
        self.model, self.tokenizer = load(model_id)
        self.permutations = permutations
        self.letter_ids = [self.tokenizer.encode(x, add_special_tokens=False)[0]
                           for x in string.ascii_uppercase]

    def _logits(self, state: str, prompt: str, n: int) -> list[float]:
        import mlx.core as mx
        messages = [{"role": "user", "content": f"{INSTRUCTION}\n\n[ESTADO]\n{state}\n\n{prompt}"}]
        ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                 enable_thinking=False)
        logits = self.model(mx.array([ids]))[0, -1]
        return [float(logits[i]) for i in self.letter_ids[:n]]

    def _distribution(self, state: str, question: str, options: list[str]) -> list[float]:
        """Probability of each option, averaged over the given and the reversed order."""
        n = len(options)
        orders = [list(range(n)), list(range(n))[::-1]][:self.permutations]
        total = [0.0] * n
        for order in orders:
            listed = "\n".join(f"{string.ascii_uppercase[k]}. {options[i]}"
                               for k, i in enumerate(order))
            probs = _softmax(self._logits(state, f"[PREGUNTA]\n{question}\n{listed}", n))
            for k, i in enumerate(order):
                total[i] += probs[k] / len(orders)
        return total

    def ask(self, state: str, questions: dict[str, Choice | Score | Noul]) -> dict[str, dict]:
        out = {}
        for name, q in questions.items():
            if isinstance(q, Choice):
                names = list(q.criteria)
                p = self._distribution(state, q.instructions,
                                       [f"{k}: {v}" for k, v in q.criteria.items()])
                best = max(range(len(names)), key=p.__getitem__)
                out[name] = {"choice": names[best], "confidence": p[best],
                             "probabilities": dict(zip(names, p))}
            elif isinstance(q, Score):
                p = self._distribution(state, q.instructions, q.criteria)
                best = max(range(len(p)), key=p.__getitem__)
                out[name] = {"score": best + 1, "confidence": p[best],
                             "expected": sum((i + 1) * x for i, x in enumerate(p)),
                             "probabilities": p, "legend": q.criteria}
            elif isinstance(q, Noul):
                p = self._distribution(state, f"¿Es cierto lo siguiente? {q.instructions}",
                                       ["Verdadero", "Falso"])
                out[name] = {"noul": p[0]}
        return out
