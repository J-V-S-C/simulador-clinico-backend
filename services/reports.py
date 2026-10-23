from uuid import uuid4

from ports.storage import Store
from ports.errors import ServiceError


class ReportService:
    def __init__(self, store: Store):
        self.store = store

    def create(self, owner_id: str, simulation_id: str, interaction_id: str, description: str) -> dict:
        description = description.strip()
        if not 1 <= len(description) <= 2000:
            raise ServiceError("invalid_description", "A descrição deve ter entre 1 e 2000 caracteres.")
        with self.store.transaction() as tx:
            saved = tx.get_simulation(simulation_id, owner_id)
            if saved is None:
                raise ServiceError("simulation_not_found", "Simulação não encontrada.", 404)
            interaction = next((item for item in saved.simulation.interactions if item.id == interaction_id), None)
            if interaction is None:
                raise ServiceError("interaction_not_found", "Interação não encontrada.", 404)
            report_id = str(uuid4())
            context = f"Minuto {saved.simulation.elapsed_time_minutes}; sintoma: {interaction.evaluated_symptom_name}; estudante: {interaction.student_text}"
            tx.create_report(report_id, simulation_id, interaction_id, description, interaction.patient_response, context)
            return {"id": report_id, "interaction_id": interaction_id, "description": description}
