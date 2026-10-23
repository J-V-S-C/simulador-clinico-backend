import pytest

from handlers.api import ApiHandlers
from ports.errors import ServiceError
from services.auth import AuthService
from services.cases import CaseService
from services.reports import ReportService
from services.simulations import SimulationService


def test_student_can_edit_own_completed_feedback(store, clock, evaluator):
    simulations = SimulationService(store, evaluator, clock)
    handlers = ApiHandlers(AuthService(store, clock), CaseService(store), simulations, ReportService(store))
    simulation_id = simulations.start("student-1", "case-1", 5)["id"]
    initial = {"liked": True, "clarity": 4, "difficulty": 2, "useful_feature": "chat", "improvement": ""}
    with pytest.raises(ServiceError):
        handlers.submit_feedback("student-1", simulation_id, initial)
    simulations.finish("student-1", simulation_id)
    handlers.submit_feedback("student-1", simulation_id, initial)
    revised = {**initial, "liked": False, "improvement": "mais contexto"}
    assert handlers.update_feedback("student-1", simulation_id, revised) == revised
    assert handlers.feedback("student-1", simulation_id) == revised
    with pytest.raises(ServiceError) as error:
        handlers.update_feedback("student-2", simulation_id, initial)
    assert error.value.status == 404
