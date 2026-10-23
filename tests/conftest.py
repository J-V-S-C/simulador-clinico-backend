"""Minimal fictional case and fresh in-memory dependencies for each service test."""

import pytest

from fakes import FakeClock, FakeEvaluator, MemoryStore
from models import ClinicalEffect, Disease, Protocol, Symptom, SymptomState, VitalSign


@pytest.fixture
def case():
    protocol = Protocol(
        name="Oxigenação",
        orientation_content="Observe a saturação.",
        help_content="Considere oxigênio.",
        expected_response="Administrar oxigênio.",
        correct_effect=ClinicalEffect(
            symptom_intensity_changes={"Falta de ar": -3},
            vital_sign_value_changes={"Saturação": 2},
        ),
    )
    return Disease(
        name="Diagnóstico reservado",
        symptoms=[
            Symptom(
                name="Falta de ar", intensity=5, state=SymptomState.ACTIVE,
                is_visible=True, is_complex=False, protocol=protocol,
                natural_evolution_per_minute=0.1,
                vital_sign_changes_per_minute={"Saturação": -0.1},
            ),
            Symptom(
                name="Cansaço", intensity=4, state=SymptomState.ACTIVE,
                is_visible=True, is_complex=False,
                protocol=Protocol("Repouso", "Pergunte sobre cansaço.", "Considere repouso.",
                                  "Orientar repouso e reavaliar o cansaço.",
                                  correct_effect=ClinicalEffect({"Cansaço": -2})),
            ),
        ],
        initial_vital_signs=[VitalSign("Saturação", 90, "%", minimum_critical_value=85)],
    )


@pytest.fixture
def store(case):
    return MemoryStore({"case-1": case})


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def evaluator():
    return FakeEvaluator()
