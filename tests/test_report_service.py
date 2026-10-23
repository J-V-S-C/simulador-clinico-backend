"""ReportService unit tests: only stored, owned interactions can be reported."""

from copy import deepcopy

import pytest

from models import InteractionClassification, Patient, Simulation
from ports.errors import ServiceError
from ports.storage import SavedSimulation
from services.reports import ReportService


@pytest.fixture
def interaction_in_store(store, clock, case):
    simulation = Simulation(
        deepcopy(case),
        Patient("Paciente virtual", deepcopy(case.initial_vital_signs), deepcopy(case.symptoms)),
        30,
    )
    simulation.start()
    interaction = simulation.register_interaction(
        "Administrar oxigênio", "Estou melhor.", InteractionClassification.CORRECT, "Falta de ar"
    )
    store.create_simulation(SavedSimulation(simulation, "student-1", "case-1", 1, clock.now()))
    return simulation.id, interaction.id


def test_create_report_uses_stored_response_and_context(store, interaction_in_store):
    simulation_id, interaction_id = interaction_in_store

    report = ReportService(store).create(
        "student-1", simulation_id, interaction_id, "  Resposta incoerente  "
    )

    assert report["interaction_id"] == interaction_id
    assert report["description"] == "Resposta incoerente"
    assert store.reports[0]["response"] == "Estou melhor."
    assert "Administrar oxigênio" in store.reports[0]["context"]
    assert "Falta de ar" in store.reports[0]["context"]


@pytest.mark.parametrize("description", [" ", "x" * 2001])
def test_rejects_invalid_description(store, interaction_in_store, description):
    simulation_id, interaction_id = interaction_in_store

    with pytest.raises(ServiceError) as error:
        ReportService(store).create("student-1", simulation_id, interaction_id, description)

    assert error.value.code == "invalid_description"
    assert store.reports == []


def test_rejects_another_students_simulation(store, interaction_in_store):
    simulation_id, interaction_id = interaction_in_store

    with pytest.raises(ServiceError) as error:
        ReportService(store).create("student-2", simulation_id, interaction_id, "Erro")

    assert error.value.code == "simulation_not_found"
    assert store.reports == []


def test_rejects_unknown_interaction(store, interaction_in_store):
    simulation_id, _ = interaction_in_store

    with pytest.raises(ServiceError) as error:
        ReportService(store).create("student-1", simulation_id, "missing", "Erro")

    assert error.value.code == "interaction_not_found"
    assert store.reports == []
