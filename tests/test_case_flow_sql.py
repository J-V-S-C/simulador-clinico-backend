"""A complete introductory attempt survives the SQLite serialization boundary."""

import asyncio

from fakes import FakeClock, FakeEvaluator
from repositories.database import create_session_factory
from repositories.store import SqlStore, case_id_for_name, seed_public_cases
from sample_data import create_beginner_case
from services.cases import CaseService
from services.simulations import SimulationService


def test_seeded_case_finishes_after_two_distinct_conducts(tmp_path, monkeypatch):
    factory = create_session_factory(f"sqlite:///{tmp_path / 'clinical.db'}")
    seed_public_cases(factory)
    monkeypatch.setattr("services.simulations.choice", lambda options: options[0])
    store = SqlStore(factory)
    with store.transaction() as tx:
        tx.create_user("student-1", "student@example.invalid", "test-hash", "Estudante")
    titles = [item["title"] for item in CaseService(store).list_cases()]
    assert "Paciente com febre" in titles
    assert "Paciente com nariz entupido" in titles
    assert "Paciente com tontura" in titles

    service = SimulationService(store, FakeEvaluator(), FakeClock())
    case_id = case_id_for_name(create_beginner_case().name)
    started = service.start("student-1", case_id, 5)
    assert [item["name"] for item in started["symptoms"]] == ["Febre", "Dor de cabeça"]
    simulation_id = started["id"]
    first = asyncio.run(service.interact("student-1", simulation_id, "Avaliar febre e hidratar", "Febre"))["simulation"]
    assert first["is_running"]
    second = asyncio.run(service.interact("student-1", simulation_id, "Reavaliar a dor e orientar repouso", "Dor de cabeça"))["simulation"]
    assert second["result"]["definitive_outcome"] == "Atendimento bem-sucedido"
    assert second["disease_name"] == "Quadro febril - caso introdutório"

    persisted = SimulationService(SqlStore(factory), FakeEvaluator(), FakeClock()).get("student-1", simulation_id)
    assert persisted["result"]["definitive_outcome"] == "Atendimento bem-sucedido"
    assert [item["state"] for item in persisted["symptoms"]] == ["inactive", "inactive"]

    monkeypatch.setattr("services.simulations.choice", lambda options: options[1])
    variant = service.start("student-1", case_id, 5)
    assert [item["name"] for item in variant["symptoms"]] == ["Febre"]
    uncovered = asyncio.run(service.interact("student-1", variant["id"], "Avaliar temperatura e hidratar", "Febre"))["simulation"]
    assert [item["name"] for item in uncovered["symptoms"]] == ["Febre", "Calafrios"]
    assessed = asyncio.run(service.interact("student-1", variant["id"], "Reavalie calafrios e temperatura", "Calafrios"))["simulation"]
    assert assessed["interactions"][-1]["classification"] == "assessment"
    assert assessed["is_running"] is True
    assert assessed["symptoms"][-1]["state"] == "active"
    ended = asyncio.run(service.interact("student-1", variant["id"], "Repousar, hidratar e reavaliar calafrios", "Calafrios"))["simulation"]
    assert ended["result"]["definitive_outcome"] == "Atendimento bem-sucedido"
