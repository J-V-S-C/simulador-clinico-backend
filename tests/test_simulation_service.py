"""SimulationService unit tests using only memory, a fixed clock, and a fake evaluator."""

import asyncio
from datetime import timedelta

import pytest

from models import InteractionClassification, is_assessment_only
from ports.evaluator import Evaluation
from ports.errors import ServiceError
from services.simulations import SimulationService


OWNER = "student-1"
SYMPTOM = "Falta de ar"


def test_start_creates_private_state_without_revealing_diagnosis(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)

    started = service.start(OWNER, "case-1", 5)

    assert started["is_running"] is True
    assert started["disease_name"] is None
    assert started["symptoms"][0]["name"] == SYMPTOM


def test_start_does_not_mutate_case_template(store, clock, evaluator, case):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    asyncio.run(service.interact(OWNER, simulation_id, "Oxigênio", SYMPTOM))

    assert case.symptoms[0].intensity == 5
    assert case.initial_vital_signs[0].value == 90


def test_list_shows_only_owners_simulations(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    assert service.list(OWNER, 20, 0)[0]["id"] == simulation_id
    assert service.list("student-2", 20, 0) == []


def test_start_rejects_invalid_time_limit(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)

    with pytest.raises(ServiceError) as error:
        service.start(OWNER, "case-1", 0)
    assert error.value.code == "invalid_time_limit"
    assert store.simulations == {}


def test_rejects_more_than_ten_minutes(store, clock, evaluator):
    with pytest.raises(ServiceError) as error:
        SimulationService(store, evaluator, clock).start(OWNER, "case-1", 11)
    assert error.value.code == "invalid_time_limit"


def test_symptom_evolves_each_second_and_scales_with_duration(store, clock, evaluator, case):
    case.symptoms[0].natural_evolution_per_minute = 0.5
    service = SimulationService(store, evaluator, clock)
    short_id = service.start(OWNER, "case-1", 1)["id"]
    long_id = service.start(OWNER, "case-1", 10)["id"]
    clock.current += timedelta(seconds=1)
    short = service.get(OWNER, short_id)
    long = service.get(OWNER, long_id)
    assert short["symptoms"][0]["intensity"] > long["symptoms"][0]["intensity"] > 5
    assert short["remaining_seconds"] == 59
    assert long["remaining_seconds"] == 599
    clock.current += timedelta(seconds=1)
    assert service.get(OWNER, long_id)["symptoms"][0]["intensity"] > long["symptoms"][0]["intensity"]


def test_effective_action_reduces_subsequent_worsening(store, clock, evaluator, case):
    case.symptoms[0].natural_evolution_per_minute = 0.5
    service = SimulationService(store, evaluator, clock)
    idle_id = service.start(OWNER, "case-1", 5)["id"]
    active_id = service.start(OWNER, "case-1", 5)["id"]
    clock.current += timedelta(seconds=30)
    idle_before = service.get(OWNER, idle_id)["symptoms"][0]["intensity"]
    asyncio.run(service.interact(OWNER, active_id, "Administrar oxigênio", SYMPTOM))
    active_before = service.get(OWNER, active_id)["symptoms"][0]["intensity"]
    clock.current += timedelta(seconds=30)
    idle_after = service.get(OWNER, idle_id)["symptoms"][0]["intensity"]
    active_after = service.get(OWNER, active_id)["symptoms"][0]["intensity"]
    assert active_after - active_before < idle_after - idle_before


def test_start_rejects_unknown_case(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)

    with pytest.raises(ServiceError) as error:
        service.start(OWNER, "missing", 5)
    assert error.value.code == "case_not_found"
    assert store.simulations == {}


def test_get_rejects_unknown_simulation(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)

    with pytest.raises(ServiceError) as error:
        service.get(OWNER, "missing")
    assert error.value.code == "simulation_not_found"


def test_owner_cannot_read_another_students_simulation(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    with pytest.raises(ServiceError) as error:
        service.get("student-2", simulation_id)

    assert error.value.code == "simulation_not_found"
    assert error.value.status == 404


def test_protocol_reveals_one_level_at_a_time_and_persists_progress(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    levels = [service.reveal(OWNER, simulation_id, SYMPTOM) for _ in range(3)]

    assert [item["content"] for item in levels] == [
        "Observe a saturação.", "Considere oxigênio.", "Administrar oxigênio."
    ]
    assert levels[-1]["has_next_level"] is False
    assert service.get(OWNER, simulation_id)["protocols"][0]["content"] == [
        item["content"] for item in levels
    ]

    with pytest.raises(ServiceError) as error:
        service.reveal(OWNER, simulation_id, SYMPTOM)
    assert error.value.code == "protocol_complete"


def test_interaction_records_patient_response_and_clinical_effect(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    result = asyncio.run(service.interact(OWNER, simulation_id, "  Administrar oxigênio  ", SYMPTOM))
    state = service.get(OWNER, simulation_id)

    assert evaluator.calls == [("  Administrar oxigênio  ", SYMPTOM)]
    assert result["interaction_id"] == state["interactions"][0]["id"]
    assert state["interactions"][0]["student_text"] == "Administrar oxigênio"
    assert state["interactions"][0]["patient_response"] == "Estou melhor."
    assert state["interactions"][0]["classification"] == "correct"
    assert state["symptoms"][0]["intensity"] == 2
    assert state["vital_signs"][0]["value"] == 92


def test_exact_level_three_conduct_is_correct_even_if_evaluator_marks_partial(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    evaluator.classification = InteractionClassification.PARTIALLY_CORRECT

    state = asyncio.run(service.interact(OWNER, simulation_id, "3. ADMINISTRAR OXIGÊNIO!", SYMPTOM))["simulation"]

    assert state["interactions"][0]["classification"] == "correct"


def test_incomplete_level_three_conduct_remains_partial(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    evaluator.classification = InteractionClassification.PARTIALLY_CORRECT

    state = asyncio.run(service.interact(OWNER, simulation_id, "Administrar", SYMPTOM))["simulation"]

    assert state["interactions"][0]["classification"] == "partially_correct"


@pytest.mark.parametrize("message", [
    "O que você sente?",
    "Quais são seus sintomas",
    "Reavalie calafrios e temperatura",
    "Verifique a temperatura.",
])
def test_assessment_alone_never_resolves_symptom_even_if_evaluator_says_correct(store, clock, evaluator, message):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    state = asyncio.run(service.interact(OWNER, simulation_id, message, SYMPTOM))["simulation"]

    assert state["interactions"][0]["classification"] == "assessment"
    assert state["symptoms"][0]["state"] == "active"
    assert state["symptoms"][0]["intensity"] == 5
    assert state["vital_signs"][0]["value"] == 90
    assert state["is_running"] is True


def test_assessment_with_real_intervention_can_still_be_evaluated_as_conduct():
    assert not is_assessment_only("Pergunte sobre a dor e oriente repouso e hidratação.")


def test_reassessment_alone_is_an_assessment():
    assert is_assessment_only("Reavalie calafrios")


@pytest.mark.parametrize("text,symptom,expected_code", [
    (" ", SYMPTOM, "invalid_text"),
    ("x" * 2001, SYMPTOM, "invalid_text"),
    ("Conduta", "Desconhecido", "symptom_not_found"),
])
def test_invalid_interaction_never_calls_evaluator(store, clock, evaluator, text, symptom, expected_code):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    with pytest.raises(ServiceError) as error:
        asyncio.run(service.interact(OWNER, simulation_id, text, symptom))

    assert error.value.code == expected_code
    assert evaluator.calls == []
    assert service.get(OWNER, simulation_id)["interactions"] == []


def test_evaluator_failure_leaves_state_unchanged(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    evaluator.error = ServiceError("evaluator_unavailable", "Unavailable", 503)

    with pytest.raises(ServiceError) as error:
        asyncio.run(service.interact(OWNER, simulation_id, "Conduta", SYMPTOM))

    assert error.value.code == "evaluator_unavailable"
    state = service.get(OWNER, simulation_id)
    assert state["interactions"] == []
    assert state["symptoms"][0]["intensity"] == 5


def test_clock_refresh_during_evaluation_keeps_student_message(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    def advance_clock_and_refresh():
        clock.current += timedelta(seconds=3)
        service.get(OWNER, simulation_id)
    evaluator.on_evaluate = advance_clock_and_refresh

    asyncio.run(service.interact(OWNER, simulation_id, "Conduta", SYMPTOM))

    state = service.get(OWNER, simulation_id)
    assert state["remaining_seconds"] == 297
    assert state["interactions"][0]["student_text"] == "Conduta"


def test_stream_previews_before_persisting_final_answer(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    async def fake_stream(snapshot, text, symptom):
        yield "preview", "Estou"
        yield "preview", "Estou melhor."
        yield "final", await evaluator.evaluate(snapshot, text, symptom)

    evaluator.evaluate_stream = fake_stream

    async def collect():
        return [event async for event in service.interact_stream(OWNER, simulation_id, "Oxigênio", SYMPTOM)]

    events = asyncio.run(collect())
    assert [kind for kind, _ in events] == ["preview", "preview", "complete"]
    assert events[-1][1]["simulation"]["interactions"][0]["patient_response"] == "Estou melhor."


def test_success_requires_each_selected_symptom_once(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    first = asyncio.run(service.interact(OWNER, simulation_id, "Conduta completa", SYMPTOM))["simulation"]
    assert first["is_running"] is True
    assert first["symptoms"][0]["state"] == "inhibited"
    with pytest.raises(ServiceError) as repeated:
        asyncio.run(service.interact(OWNER, simulation_id, "Repetir conduta", SYMPTOM))
    assert repeated.value.code == "symptom_not_found"

    completed = asyncio.run(service.interact(OWNER, simulation_id, "Orientar repouso", "Cansaço"))["simulation"]
    assert completed["is_running"] is False
    assert completed["result"]["definitive_outcome"] == "Atendimento bem-sucedido"
    assert all(item["state"] == "inactive" and item["intensity"] == 0 for item in completed["symptoms"])
    assert completed["vital_signs"][0]["value"] == 90


def test_identical_conduct_cannot_be_reused_for_another_symptom(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    asyncio.run(service.interact(OWNER, simulation_id, "Orientar repouso", SYMPTOM))

    with pytest.raises(ServiceError) as repeated:
        asyncio.run(service.interact(OWNER, simulation_id, " orientar   repouso ", "Cansaço"))

    assert repeated.value.code == "duplicate_conduct"
    assert len(service.get(OWNER, simulation_id)["interactions"]) == 1


def test_hidden_symptom_is_discovered_from_patient_answer(store, clock, evaluator, case):
    case.symptoms[1].is_visible = False
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    assert [item["name"] for item in service.get(OWNER, simulation_id)["symptoms"]] == [SYMPTOM]

    async def answer(_simulation, _text, _symptom):
        return Evaluation("Também estou cansado.", InteractionClassification.PARTIALLY_CORRECT,
                          revealed_symptoms=("Cansaço", "Inventado"))
    evaluator.evaluate = answer
    state = asyncio.run(service.interact(OWNER, simulation_id, "Tem mais sintomas?", SYMPTOM))["simulation"]
    assert [item["name"] for item in state["symptoms"]] == [SYMPTOM, "Cansaço"]


def test_hidden_symptom_appears_when_visible_complaint_is_addressed(store, clock, evaluator, case):
    case.symptoms[1].is_visible = False
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    state = asyncio.run(service.interact(OWNER, simulation_id, "Conduta adequada", SYMPTOM))["simulation"]

    assert state["is_running"] is True
    assert [item["name"] for item in state["symptoms"]] == [SYMPTOM, "Cansaço"]
    assert state["symptoms"][1]["state"] == "active"


def test_optional_symptom_is_chosen_for_each_attempt(store, clock, evaluator, case, monkeypatch):
    from copy import deepcopy
    case.optional_symptoms = [deepcopy(case.symptoms[1])]
    case.optional_symptoms[0].name = "Outro cansaço"
    monkeypatch.setattr("services.simulations.choice", lambda options: options[0])
    service = SimulationService(store, evaluator, clock)
    state = service.start(OWNER, "case-1", 5)
    assert [item["name"] for item in state["symptoms"]] == [SYMPTOM, "Cansaço", "Outro cansaço"]
    assert case.optional_symptoms[0].name == "Outro cansaço"


def test_wall_clock_expiration_ends_simulation(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 2)["id"]

    clock.advance(2)
    ended = service.get(OWNER, simulation_id)

    assert ended["is_running"] is False
    assert ended["elapsed_time_minutes"] == 2
    assert ended["result"]["definitive_outcome"] == "Tempo esgotado"
    assert service.result(OWNER, simulation_id) == ended["result"]


def test_remaining_seconds_tracks_wall_clock_and_manual_advance(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 2)["id"]

    clock.current += timedelta(seconds=17)
    assert service.get(OWNER, simulation_id)["remaining_seconds"] == 103

    advanced = service.advance(OWNER, simulation_id, 60)
    assert advanced["remaining_seconds"] == 43
    assert advanced["elapsed_time_minutes"] == 1

    short_advance = service.advance(OWNER, simulation_id, 10)
    assert short_advance["remaining_seconds"] == 33

    clock.current += timedelta(seconds=33)
    ended = service.get(OWNER, simulation_id)
    assert ended["remaining_seconds"] == 0
    assert ended["result"]["definitive_outcome"] == "Tempo esgotado"


def test_manual_advance_ends_on_critical_vital_sign(store, clock, evaluator, case):
    case.initial_vital_signs[0].minimum_critical_value = 89.95
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    ended = service.advance(OWNER, simulation_id, 60)

    assert ended["is_running"] is False
    assert ended["vital_signs"][0]["is_critical"] is True
    assert ended["result"]["definitive_outcome"] == "Agravamento crítico"


def test_finish_returns_outcome_and_feedback(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    asyncio.run(service.interact(OWNER, simulation_id, "Administrar oxigênio", SYMPTOM))

    finished = service.finish(OWNER, simulation_id)

    assert finished["is_running"] is False
    assert finished["disease_name"] == "Diagnóstico reservado"
    assert finished["result"]["definitive_outcome"] == "Atendimento concluído"
    assert finished["result"]["feedback"].startswith("1 conduta(s) adequadas e 0 parcialmente adequadas")


@pytest.mark.parametrize("action", ["finish", "advance", "reveal", "interact"])
def test_finished_simulation_rejects_further_actions(store, clock, evaluator, action):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]
    service.finish(OWNER, simulation_id)

    actions = {
        "finish": lambda: service.finish(OWNER, simulation_id),
        "advance": lambda: service.advance(OWNER, simulation_id, 60),
        "reveal": lambda: service.reveal(OWNER, simulation_id, SYMPTOM),
        "interact": lambda: asyncio.run(service.interact(OWNER, simulation_id, "Conduta", SYMPTOM)),
    }

    with pytest.raises(ServiceError) as error:
        actions[action]()
    assert error.value.code == "already_finished"


def test_result_is_unavailable_while_running(store, clock, evaluator):
    service = SimulationService(store, evaluator, clock)
    simulation_id = service.start(OWNER, "case-1", 5)["id"]

    with pytest.raises(ServiceError) as error:
        service.result(OWNER, simulation_id)

    assert error.value.code == "not_finished"
