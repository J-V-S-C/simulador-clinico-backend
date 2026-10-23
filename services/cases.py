"""Public case metadata without answer leakage."""

from ports.storage import Store
from ports.errors import ServiceError


class CaseService:
    def __init__(self, store: Store):
        self.store = store

    def list_cases(self) -> list[dict]:
        with self.store.transaction() as tx:
            cases = tx.list_cases()
        return [{"id": case_id, "title": "Paciente com " + " e ".join(
            symptom.name.lower() for symptom in case.symptoms if symptom.is_visible
        ) if any(symptom.is_visible for symptom in case.symptoms) else "Atendimento clínico"}
                for case_id, case in cases]

    def get_case(self, case_id: str) -> dict:
        cases = self.list_cases()
        found = next((item for item in cases if item["id"] == case_id), None)
        if found is None:
            raise ServiceError("case_not_found", "Caso clínico não encontrado.", 404)
        return {**found, "default_time_limit_minutes": 5, "max_time_limit_minutes": 10}
