"""Student-facing simulation projection keeps case answers private until completion."""

from copy import deepcopy

from models import Patient, Simulation
from services.presentation import simulation_view
from sample_data import create_public_cases


def test_running_view_hides_diagnosis_and_hidden_symptoms(case):
    hidden = deepcopy(case.symptoms[0])
    hidden.name = "Sintoma oculto"
    hidden.is_visible = False
    case.symptoms.append(hidden)
    simulation = Simulation(
        case,
        Patient("Paciente", deepcopy(case.initial_vital_signs), deepcopy(case.symptoms)),
        30,
    )
    simulation.start()

    view = simulation_view(simulation)

    assert view["disease_name"] is None
    assert [symptom["name"] for symptom in view["symptoms"]] == ["Falta de ar", "Cansaço"]
    assert [protocol["symptom_name"] for protocol in view["protocols"]] == ["Falta de ar", "Cansaço"]
    assert view["result"] is None
    assert view["remaining_seconds"] == 1800


def test_finished_view_exposes_result_and_diagnosis(case):
    simulation = Simulation(
        case,
        Patient("Paciente", deepcopy(case.initial_vital_signs), deepcopy(case.symptoms)),
        30,
    )
    simulation.start()
    simulation.end("Estável", "Atendimento concluído", "Boa conduta")

    view = simulation_view(simulation)

    assert view["disease_name"] == "Diagnóstico reservado"
    assert view["result"] == {
        "clinical_evolution": "Estável",
        "time_elapsed": 0,
        "definitive_outcome": "Atendimento concluído",
        "feedback": "Boa conduta",
    }
    assert view["remaining_seconds"] == 0


def test_all_published_protocols_link_to_their_clinical_source():
    for disease in create_public_cases():
        for symptom in [*disease.symptoms, *disease.optional_symptoms]:
            assert symptom.protocol.reference_source.startswith("https://www.nhs.uk/")
