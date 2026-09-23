"""Mock local da futura integração com a LLM."""

import re
import unicodedata

from models import InteractionClassification


class MockLlmEvaluation:
    def __init__(
        self,
        patient_response: str,
        classification: InteractionClassification,
    ):
        self.patient_response = patient_response
        self.classification = classification


def normalize_relevant_words(text: str) -> set[str]:
    normalized_text = unicodedata.normalize("NFD", text.lower())
    normalized_text = "".join(
        character
        for character in normalized_text
        if unicodedata.category(character) != "Mn"
    )
    ignored_words = {
        "a",
        "ao",
        "da",
        "de",
        "do",
        "e",
        "o",
        "paciente",
        "para",
        "por",
        "uma",
        "um",
    }
    words = set(re.findall(r"[a-z0-9]+", normalized_text))
    return {word for word in words if len(word) > 2 and word not in ignored_words}


def evaluate_student_interaction_with_mock(
    student_text: str,
    expected_response: str,
) -> MockLlmEvaluation:
    """Compara palavras relevantes apenas para demonstrar o fluxo da sprint."""
    student_words = normalize_relevant_words(student_text)
    expected_words = normalize_relevant_words(expected_response)
    matching_word_count = len(student_words.intersection(expected_words))
    match_ratio = matching_word_count / max(len(expected_words), 1)

    if match_ratio >= 0.4:
        return MockLlmEvaluation(
            "Estou me sentindo melhor após a sua conduta.",
            InteractionClassification.CORRECT,
        )
    if match_ratio >= 0.15:
        return MockLlmEvaluation(
            "Senti uma pequena melhora, mas o desconforto continua.",
            InteractionClassification.PARTIALLY_CORRECT,
        )
    return MockLlmEvaluation(
        "Meu quadro não apresentou melhora com essa conduta.",
        InteractionClassification.INCORRECT,
    )
