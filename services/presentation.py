"""Student-facing state projection. Never expose hidden case answers."""

from models import Simulation


def simulation_view(simulation: Simulation, remaining_seconds: int | None = None) -> dict:
    result = None
    if simulation.result:
        result = {
            "clinical_evolution": simulation.result.clinical_evolution,
            "time_elapsed": simulation.result.time_elapsed,
            "definitive_outcome": simulation.result.definitive_outcome,
            "feedback": simulation.result.feedback,
        }
    return {
        "id": simulation.id,
        "is_running": simulation.is_running,
        "disease_name": simulation.disease.name if result else None,
        "time_limit_minutes": simulation.time_limit_minutes,
        "elapsed_time_minutes": simulation.elapsed_time_minutes,
        "remaining_seconds": (
            max(0, remaining_seconds)
            if remaining_seconds is not None
            else max(0, (simulation.time_limit_minutes - simulation.elapsed_time_minutes) * 60)
        ) if simulation.is_running else 0,
        "interactions": [
            {"id": item.id, "student_text": item.student_text,
             "patient_response": item.patient_response,
             "classification": item.classification.value,
             "evaluated_symptom_name": item.evaluated_symptom_name,
             "input_tokens": item.input_tokens, "output_tokens": item.output_tokens}
            for item in simulation.interactions
        ],
        "protocol_progress": simulation.revealed_protocol_level_by_symptom.copy(),
        "protocols": [
            {"symptom_name": item.name,
             "revealed_level": simulation.revealed_protocol_level_by_symptom.get(item.name, 0),
             "reference_source": item.protocol.reference_source,
             "content": [item.protocol.get_content_for_level(level) for level in range(1, simulation.revealed_protocol_level_by_symptom.get(item.name, 0) + 1)]}
            for item in simulation.patient.symptoms if item.is_visible
        ],
        "vital_signs": [
            {"name": item.name, "value": item.value, "unit": item.unit, "is_critical": item.is_critical(),
             "baseline_value": next((start.value for start in simulation.disease.initial_vital_signs if start.name == item.name), item.value),
             "critical_value": item.minimum_critical_value if item.minimum_critical_value is not None else item.maximum_critical_value}
            for item in simulation.patient.vital_signs
        ],
        "symptoms": [
            {"name": item.name, "intensity": item.intensity, "severity": item.get_severity().name,
             "state": item.state.value, "is_complex": item.is_complex}
            for item in simulation.patient.symptoms if item.is_visible or result
        ],
        "result": result,
    }
