from integrations.gemini import GeminiEvaluator


def test_structured_answer_accepts_discovered_symptoms():
    from integrations.gemini import GeminiAnswer
    answer = GeminiAnswer.model_validate({
        "patient_response": "Também sinto calafrios.",
        "classification": "partially_correct",
        "revealed_symptoms": ["Calafrios"],
    })
    assert answer.revealed_symptoms == ["Calafrios"]


def test_partial_structured_json_preview_handles_escapes():
    extract = GeminiEvaluator._preview_from_partial_json
    assert extract('{"patient_response":"Estou com fe') == "Estou com fe"
    assert extract('{"patient_response":"Linha 1\\nLinha 2","classification":"correct"}') == "Linha 1\nLinha 2"
    assert extract('{"classification":"correct"}') == ""
