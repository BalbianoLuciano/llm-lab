"""A quality rule as data: what it asks, what each level means, where it comes from.

Rules are written in natural language by a person and compiled to this schema by an LLM
(lab 14). The level descriptions double as the explanation shown in the UI.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "rules" / "reference.yaml"

Level = Literal["green", "yellow", "red"]
BlockKind = Literal["heading", "paragraph", "list_item", "table"]


class Example(BaseModel):
    text: str
    expected: Level


class Levels(BaseModel):
    green: str
    yellow: str
    red: str


class Rule(BaseModel):
    id: str = Field(description="identificador corto, en minúsculas y con guiones")
    source: str = Field(description="la norma de la que sale la regla")
    version: int = 1
    kind: Literal["semantic", "deterministic"] = Field(
        description="semantic: la evalúa un modelo; deterministic: se chequea con código")
    scope: Literal["block", "document"]
    applies_to: list[BlockKind]
    question: str = Field(description="la pregunta que se le hace al evaluador sobre el bloque")
    levels: Levels
    blocking: bool = Field(description="si queda en rojo, el documento no se indexa")
    examples: list[Example] = Field(default_factory=list)


def load_rules(path: Path = REFERENCE) -> dict[str, Rule]:
    data = yaml.safe_load(path.read_text())
    return {r["id"]: Rule.model_validate(r) for r in data}
