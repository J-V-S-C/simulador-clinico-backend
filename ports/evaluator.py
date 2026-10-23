from dataclasses import dataclass
from typing import Protocol

from models import InteractionClassification, Simulation


@dataclass(frozen=True)
class Evaluation:
    patient_response: str
    classification: InteractionClassification
    input_tokens: int = 0
    output_tokens: int = 0
    revealed_symptoms: tuple[str, ...] = ()


class Evaluator(Protocol):
    async def evaluate(self, simulation: Simulation, student_text: str, symptom_name: str) -> Evaluation: ...
