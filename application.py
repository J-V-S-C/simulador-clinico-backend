"""Casos de uso da aplicação, independentes da interface utilizada."""

from copy import deepcopy

from models import Interaction, InteractionClassification, Patient, Report, Simulation
from mocks import evaluate_student_interaction_with_mock
from repositories.repositories import DiseaseRepository, ReportRepository, SimulationRepository


def serialize_interaction(interaction: Interaction) -> dict[str, object]:
    return {
        "student_text": interaction.student_text,
        "patient_response": interaction.patient_response,
        "classification": interaction.classification.value,
        "evaluated_symptom_name": interaction.evaluated_symptom_name,
    }


def serialize_simulation(simulation: Simulation) -> dict[str, object]:
    result = None
    if simulation.result:
        result = {
            "interactions": [serialize_interaction(item) for item in simulation.result.interactions],
            "clinical_evolution": simulation.result.clinical_evolution,
            "time_elapsed": simulation.result.time_elapsed,
            "definitive_outcome": simulation.result.definitive_outcome,
            "feedback": simulation.result.feedback,
        }

    return {
        "id": simulation.id,
        "disease_name": simulation.disease.name,
        "is_running": simulation.is_running,
        "time_limit_minutes": simulation.time_limit_minutes,
        "elapsed_time_minutes": simulation.elapsed_time_minutes,
        "interactions": [serialize_interaction(item) for item in simulation.interactions],
        "protocol_progress": simulation.revealed_protocol_level_by_symptom.copy(),
        "vital_signs": [
            {
                "name": vital_sign.name,
                "value": round(vital_sign.value, 2),
                "unit": vital_sign.unit,
                "is_critical": vital_sign.is_critical(),
            }
            for vital_sign in simulation.patient.vital_signs
        ],
        "symptoms": [
            {
                "name": symptom.name,
                "intensity": round(symptom.intensity, 2),
                "severity": symptom.get_severity().name,
                "state": symptom.state.value,
                "is_visible": symptom.is_visible,
                "is_complex": symptom.is_complex,
            }
            for symptom in simulation.patient.symptoms
        ],
        "result": result,
    }


class SimulationService:
    """Executa o fluxo principal e devolve dados simples para a interface."""

    def __init__(self, disease_repository: DiseaseRepository,
                 simulation_repository: SimulationRepository,
                 report_repository: ReportRepository):
        self.disease_repository = disease_repository
        self.simulation_repository = simulation_repository
        self.report_repository = report_repository

    def list_available_diseases(self) -> dict[str, object]:
        diseases = self.disease_repository.list_all()
        return {"ok": True, "diseases": [{"name": item.name} for item in diseases]}

    def start_new_simulation(self, disease_name: str, time_limit_minutes: int) -> dict[str, object]:
        disease = self.disease_repository.find_by_name(disease_name)
        if disease is None:
            return self.create_error_response("Doença não encontrada.")
        if time_limit_minutes <= 0:
            return self.create_error_response("O limite de tempo deve ser positivo.")

        case = deepcopy(disease)
        patient = Patient("Paciente virtual", deepcopy(case.initial_vital_signs), deepcopy(case.symptoms))
        simulation = Simulation(case, patient, time_limit_minutes)
        simulation.start()
        self.simulation_repository.create(simulation)
        return {"ok": True, "simulation": serialize_simulation(simulation)}

    def get_simulation_state(self, simulation_id: str) -> dict[str, object]:
        simulation = self.simulation_repository.find_by_id(simulation_id)
        if simulation is None:
            return self.create_error_response("Simulação não encontrada.")
        return {"ok": True, "simulation": serialize_simulation(simulation)}

    def register_interaction(self, simulation_id: str, student_text: str,
                             patient_response: str, classification_value: str,
                             evaluated_symptom_name: str) -> dict[str, object]:
        simulation = self.simulation_repository.find_by_id(simulation_id)
        if simulation is None:
            return self.create_error_response("Simulação não encontrada.")
        if not simulation.is_running:
            return self.create_error_response("A simulação já foi encerrada.")

        try:
            classification = InteractionClassification(classification_value)
        except ValueError:
            return self.create_error_response("Classificação inválida.")

        try:
            interaction = simulation.register_interaction(
                student_text, patient_response, classification, evaluated_symptom_name
            )
        except ValueError as error:
            return self.create_error_response(str(error))

        self.simulation_repository.update(simulation)
        return {
            "ok": True,
            "interaction": serialize_interaction(interaction),
            "simulation": serialize_simulation(simulation),
        }

    def register_interaction_using_llm_mock(
        self,
        simulation_id: str,
        student_text: str,
        evaluated_symptom_name: str,
    ) -> dict[str, object]:
        """Simula a resposta e avaliação que futuramente virão da LLM."""
        simulation = self.simulation_repository.find_by_id(simulation_id)
        if simulation is None:
            return self.create_error_response("Simulação não encontrada.")

        symptom = simulation.patient.find_symptom(evaluated_symptom_name)
        if symptom is None:
            return self.create_error_response("Sintoma avaliado não encontrado.")

        mock_evaluation = evaluate_student_interaction_with_mock(
            student_text,
            symptom.protocol.expected_response,
        )
        return self.register_interaction(
            simulation_id,
            student_text,
            mock_evaluation.patient_response,
            mock_evaluation.classification.value,
            evaluated_symptom_name,
        )

    def advance_simulation_time(self, simulation_id: str, minutes: int) -> dict[str, object]:
        simulation = self.simulation_repository.find_by_id(simulation_id)
        if simulation is None:
            return self.create_error_response("Simulação não encontrada.")
        try:
            simulation.advance_time(minutes)
        except (RuntimeError, ValueError) as error:
            return self.create_error_response(str(error))

        if simulation.has_time_expired():
            self.finish_simulation_state(simulation, "Tempo esgotado", "O limite de tempo foi atingido.")
        elif simulation.patient.has_critical_aggravation():
            self.finish_simulation_state(simulation, "Agravamento crítico", "Um sinal vital atingiu um valor crítico.")

        self.simulation_repository.update(simulation)
        return {"ok": True, "simulation": serialize_simulation(simulation)}

    def reveal_next_protocol_content(self, simulation_id: str,
                                     symptom_name: str) -> dict[str, object]:
        simulation = self.simulation_repository.find_by_id(simulation_id)
        if simulation is None:
            return self.create_error_response("Simulação não encontrada.")
        try:
            level, content, has_next_level = simulation.reveal_next_protocol_content(symptom_name)
        except ValueError as error:
            return self.create_error_response(str(error))

        self.simulation_repository.update(simulation)
        return {
            "ok": True,
            "symptom_name": symptom_name,
            "level": level,
            "content": content,
            "has_next_level": has_next_level,
        }

    def report_ai_response(self, simulation_id: str, ai_response: str,
                           description: str) -> dict[str, object]:
        simulation = self.simulation_repository.find_by_id(simulation_id)
        if simulation is None:
            return self.create_error_response("Simulação não encontrada.")
        messages = [item.student_text for item in simulation.interactions]
        context = f"Minuto {simulation.elapsed_time_minutes}; interações: {messages}"
        report = Report(ai_response, context, description)
        self.report_repository.save(report, simulation_id)
        simulation.registered_reports.append(report)
        self.simulation_repository.update(simulation)
        return {"ok": True, "report": {
            "description": report.report_description,
            "simulation_context": report.simulation_context,
        }}

    def end_simulation(self, simulation_id: str, outcome: str,
                       feedback: str) -> dict[str, object]:
        simulation = self.simulation_repository.find_by_id(simulation_id)
        if simulation is None:
            return self.create_error_response("Simulação não encontrada.")
        self.finish_simulation_state(simulation, outcome, feedback)
        self.simulation_repository.update(simulation)
        return {"ok": True, "simulation": serialize_simulation(simulation)}

    def finish_simulation_state(self, simulation: Simulation, outcome: str, feedback: str) -> None:
        active_symptoms = [
            item.name for item in simulation.patient.symptoms if item.is_active()
        ]
        evolution = "Sintomas ativos: " + (
            ", ".join(active_symptoms) if active_symptoms else "nenhum"
        )
        simulation.end(evolution, outcome, feedback)

    def create_error_response(self, message: str) -> dict[str, object]:
        return {"ok": False, "error": message}
