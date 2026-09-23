"""Implementações simuladas usadas enquanto serviços externos não estão conectados."""

from .llm_mock import MockLlmEvaluation, evaluate_student_interaction_with_mock

__all__ = ["MockLlmEvaluation", "evaluate_student_interaction_with_mock"]
