"""Conversão dos modelos para dados compatíveis com JSON e CSV."""

from models import (
    ClinicalEffect,
    Disease,
    Interaction,
    InteractionClassification,
    Patient,
    Protocol,
    Report,
    Simulation,
    SimulationResult,
    Symptom,
    SymptomState,
    VitalSign,
)


def read_dictionary(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def read_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def clinical_effect_to_dictionary(effect: ClinicalEffect) -> dict[str, object]:
    return {
        "symptom_intensity_changes": {
            name: round(value, 2)
            for name, value in effect.symptom_intensity_changes.items()
        },
        "vital_sign_value_changes": {
            name: round(value, 2)
            for name, value in effect.vital_sign_value_changes.items()
        },
    }


def clinical_effect_from_dictionary(data: dict[str, object]) -> ClinicalEffect:
    symptom_changes = read_dictionary(data.get("symptom_intensity_changes"))
    vital_sign_changes = read_dictionary(data.get("vital_sign_value_changes"))
    return ClinicalEffect(
        symptom_intensity_changes={
            str(name): float(value) for name, value in symptom_changes.items()
        },
        vital_sign_value_changes={
            str(name): float(value) for name, value in vital_sign_changes.items()
        },
    )


def protocol_to_dictionary(protocol: Protocol) -> dict[str, object]:
    return {
        "name": protocol.name,
        "orientation_content": protocol.orientation_content,
        "help_content": protocol.help_content,
        "expected_response": protocol.expected_response,
        "correct_effect": clinical_effect_to_dictionary(protocol.correct_effect),
        "partially_correct_effect": clinical_effect_to_dictionary(
            protocol.partially_correct_effect
        ),
        "incorrect_effect": clinical_effect_to_dictionary(protocol.incorrect_effect),
        "reference_source": protocol.reference_source,
    }


def protocol_from_dictionary(data: dict[str, object]) -> Protocol:
    return Protocol(
        name=str(data.get("name", "")),
        orientation_content=str(data.get("orientation_content", "")),
        help_content=str(data.get("help_content", "")),
        expected_response=str(data.get("expected_response", "")),
        correct_effect=clinical_effect_from_dictionary(
            read_dictionary(data.get("correct_effect"))
        ),
        partially_correct_effect=clinical_effect_from_dictionary(
            read_dictionary(data.get("partially_correct_effect"))
        ),
        incorrect_effect=clinical_effect_from_dictionary(
            read_dictionary(data.get("incorrect_effect"))
        ),
        reference_source=(
            str(data["reference_source"])
            if data.get("reference_source") is not None
            else None
        ),
    )


def symptom_to_dictionary(symptom: Symptom) -> dict[str, object]:
    return {
        "name": symptom.name,
        "intensity": round(symptom.intensity, 2),
        "state": symptom.state.value,
        "is_visible": symptom.is_visible,
        "is_complex": symptom.is_complex,
        "protocol": protocol_to_dictionary(symptom.protocol),
        "natural_evolution_per_minute": round(
            symptom.natural_evolution_per_minute, 2
        ),
        "vital_sign_changes_per_minute": {
            name: round(value, 2)
            for name, value in symptom.vital_sign_changes_per_minute.items()
        },
    }


def symptom_from_dictionary(data: dict[str, object]) -> Symptom:
    vital_sign_changes = read_dictionary(data.get("vital_sign_changes_per_minute"))
    return Symptom(
        name=str(data.get("name", "")),
        intensity=float(data.get("intensity", 0)),
        state=SymptomState(str(data.get("state", SymptomState.INACTIVE.value))),
        is_visible=bool(data.get("is_visible", False)),
        is_complex=bool(data.get("is_complex", False)),
        protocol=protocol_from_dictionary(read_dictionary(data.get("protocol"))),
        natural_evolution_per_minute=float(
            data.get("natural_evolution_per_minute", 0)
        ),
        vital_sign_changes_per_minute={
            str(name): float(value) for name, value in vital_sign_changes.items()
        },
    )


def vital_sign_to_dictionary(vital_sign: VitalSign) -> dict[str, object]:
    return {
        "name": vital_sign.name,
        "value": round(vital_sign.value, 2),
        "unit": vital_sign.unit,
        "minimum_critical_value": (
            round(vital_sign.minimum_critical_value, 2)
            if vital_sign.minimum_critical_value is not None
            else None
        ),
        "maximum_critical_value": (
            round(vital_sign.maximum_critical_value, 2)
            if vital_sign.maximum_critical_value is not None
            else None
        ),
    }


def vital_sign_from_dictionary(data: dict[str, object]) -> VitalSign:
    minimum = data.get("minimum_critical_value")
    maximum = data.get("maximum_critical_value")
    return VitalSign(
        name=str(data.get("name", "")),
        value=float(data.get("value", 0)),
        unit=str(data.get("unit", "")),
        minimum_critical_value=float(minimum) if minimum is not None else None,
        maximum_critical_value=float(maximum) if maximum is not None else None,
    )


def disease_to_dictionary(disease: Disease) -> dict[str, object]:
    return {
        "name": disease.name,
        "symptoms": [symptom_to_dictionary(item) for item in disease.symptoms],
        "initial_vital_signs": [
            vital_sign_to_dictionary(item) for item in disease.initial_vital_signs
        ],
    }


def disease_from_dictionary(data: dict[str, object]) -> Disease:
    return Disease(
        name=str(data.get("name", "")),
        symptoms=[
            symptom_from_dictionary(read_dictionary(item))
            for item in read_list(data.get("symptoms"))
        ],
        initial_vital_signs=[
            vital_sign_from_dictionary(read_dictionary(item))
            for item in read_list(data.get("initial_vital_signs"))
        ],
    )


def interaction_to_dictionary(interaction: Interaction) -> dict[str, object]:
    return {
        "student_text": interaction.student_text,
        "patient_response": interaction.patient_response,
        "classification": interaction.classification.value,
        "evaluated_symptom_name": interaction.evaluated_symptom_name,
    }


def interaction_from_dictionary(data: dict[str, object]) -> Interaction:
    return Interaction(
        student_text=str(data.get("student_text", "")),
        patient_response=str(data.get("patient_response", "")),
        classification=InteractionClassification(str(data.get("classification"))),
        evaluated_symptom_name=str(data.get("evaluated_symptom_name", "")),
    )


def report_to_dictionary(report: Report) -> dict[str, object]:
    return {
        "ai_response": report.ai_response,
        "simulation_context": report.simulation_context,
        "report_description": report.report_description,
    }


def report_from_dictionary(data: dict[str, object]) -> Report:
    return Report(
        ai_response=str(data.get("ai_response", "")),
        simulation_context=str(data.get("simulation_context", "")),
        report_description=str(data.get("report_description", "")),
    )


def simulation_to_dictionary(simulation: Simulation) -> dict[str, object]:
    result = None
    if simulation.result:
        result = {
            "interactions": [
                interaction_to_dictionary(item)
                for item in simulation.result.interactions
            ],
            "clinical_evolution": simulation.result.clinical_evolution,
            "time_elapsed": simulation.result.time_elapsed,
            "definitive_outcome": simulation.result.definitive_outcome,
            "feedback": simulation.result.feedback,
        }

    return {
        "id": simulation.id,
        "disease": disease_to_dictionary(simulation.disease),
        "patient": {
            "name": simulation.patient.name,
            "vital_signs": [
                vital_sign_to_dictionary(item)
                for item in simulation.patient.vital_signs
            ],
            "symptoms": [
                symptom_to_dictionary(item) for item in simulation.patient.symptoms
            ],
        },
        "time_limit_minutes": simulation.time_limit_minutes,
        "elapsed_time_minutes": simulation.elapsed_time_minutes,
        "interactions": [
            interaction_to_dictionary(item) for item in simulation.interactions
        ],
        "registered_reports": [
            report_to_dictionary(item) for item in simulation.registered_reports
        ],
        "revealed_protocol_level_by_symptom": (
            simulation.revealed_protocol_level_by_symptom
        ),
        "is_running": simulation.is_running,
        "result": result,
    }


def simulation_from_dictionary(data: dict[str, object]) -> Simulation:
    patient_data = read_dictionary(data.get("patient"))
    patient = Patient(
        name=str(patient_data.get("name", "")),
        vital_signs=[
            vital_sign_from_dictionary(read_dictionary(item))
            for item in read_list(patient_data.get("vital_signs"))
        ],
        symptoms=[
            symptom_from_dictionary(read_dictionary(item))
            for item in read_list(patient_data.get("symptoms"))
        ],
    )
    simulation = Simulation(
        disease=disease_from_dictionary(read_dictionary(data.get("disease"))),
        patient=patient,
        time_limit_minutes=int(data.get("time_limit_minutes", 0)),
        simulation_id=str(data.get("id", "")),
    )
    simulation.elapsed_time_minutes = int(data.get("elapsed_time_minutes", 0))
    simulation.interactions = [
        interaction_from_dictionary(read_dictionary(item))
        for item in read_list(data.get("interactions"))
    ]
    simulation.registered_reports = [
        report_from_dictionary(read_dictionary(item))
        for item in read_list(data.get("registered_reports"))
    ]
    protocol_levels = read_dictionary(
        data.get("revealed_protocol_level_by_symptom")
    )
    simulation.revealed_protocol_level_by_symptom = {
        str(name): int(level) for name, level in protocol_levels.items()
    }
    simulation.is_running = bool(data.get("is_running", False))

    result_data = data.get("result")
    if isinstance(result_data, dict):
        simulation.result = SimulationResult(
            interactions=[
                interaction_from_dictionary(read_dictionary(item))
                for item in read_list(result_data.get("interactions"))
            ],
            clinical_evolution=str(result_data.get("clinical_evolution", "")),
            time_elapsed=int(result_data.get("time_elapsed", 0)),
            definitive_outcome=str(result_data.get("definitive_outcome", "")),
            feedback=str(result_data.get("feedback", "")),
        )
    return simulation
