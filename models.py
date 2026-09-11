from enum import Enum
from typing import List, Optional


class Severity(Enum):
    LOW = 1
    MODERATE = 2
    HIGH = 3


class Protocol:
    def __init__(self, name: str, description: str, trigger_condition: str):
        self.name = name
        self.description = description
        self.trigger_condition = trigger_condition

    def evaluate_trigger(self, action_taken: str) -> bool:
        return self.trigger_condition.lower() in action_taken.lower()


class Symptom:
    def __init__(
        self,
        name: str,
        severity: Severity,
        is_active: bool,
        is_visible: bool,
        is_complex: bool,  # Symptoms who are only discovered by the doctor, if it isnt complex then the pacient can tell the symptom randonly
        protocol: Protocol,
    ):
        self.name = name
        self.severity = severity
        self.is_active = is_active
        self.is_visible = is_visible
        self.is_complex = is_complex
        self.protocol = protocol

    def update_based_on_action(self, action_taken: str):
        if self.protocol.evaluate_trigger(action_taken):
            if self.severity.value > Severity.LOW.value:
                self.severity = Severity(self.severity.value - 1)
            self.is_active = False


class Disease:
    def __init__(self, name: str, symptoms: List[Symptom]):
        self.name = name
        self.symptoms = symptoms


class VitalSign:
    def __init__(self, name: str, value: float, unit: str, severity: Severity):
        self.name = name
        self.value = value
        self.unit = unit
        self.severity = severity

    def update_state(self, new_value: float, new_severity: Severity):
        self.value = new_value
        self.severity = new_severity


class Patient:
    def __init__(
        self, name: str, vital_signs: List[VitalSign], symptoms: List[Symptom]
    ):
        self.name = name
        self.vital_signs = vital_signs
        self.symptoms = symptoms

    def update_clinical_state(self, action_taken: str):
        for symptom in self.symptoms:
            if symptom.is_active:
                symptom.update_based_on_action(action_taken)

    def check_critical_aggravation(self) -> bool:
        for vital in self.vital_signs:
            if vital.severity == Severity.HIGH:
                return True
        return False


class Report:
    def __init__(
        self, ai_response: str, simulation_context: str, report_description: str
    ):
        self.ai_response = ai_response
        self.simulation_context = simulation_context
        self.report_description = report_description


class OutcomeType(Enum):
    SUCCESS_DISCHARGED = 1
    FAILURE_TIME_EXPIRED = 2
    FAILURE_CRITICAL_AGGRAVATION = 3


class SimulationResult:
    def __init__(
        self,
        actions_taken: List[str],
        clinical_evolution: str,
        time_elapsed: int,
        definitive_outcome: str,
        feedback: str,
    ):
        self.actions_taken = actions_taken
        self.clinical_evolution = clinical_evolution
        self.time_elapsed = time_elapsed
        self.definitive_outcome = definitive_outcome
        self.feedback = feedback


class Simulation:
    def __init__(self, disease: Disease, patient: Patient, time_limit_minutes: int):
        self.disease = disease
        self.patient = patient
        self.time_limit_minutes = time_limit_minutes
        self.elapsed_time_minutes = 0
        self.applied_actions: List[str] = []
        self.registered_reports: List[Report] = []
        self.is_running = False
        self.result: Optional[SimulationResult] = None

    def start(self):
        self.is_running = True

    def process_student_interaction(self, interaction_text: str):
        self.applied_actions.append(interaction_text)
        self.patient.update_clinical_state(interaction_text)

    def advance_time(self, minutes: int):
        self.elapsed_time_minutes += minutes

    def check_time_expired(self) -> bool:
        return self.elapsed_time_minutes >= self.time_limit_minutes

    def report_ai_response(self, ai_response: str, context: str, description: str):
        new_report = Report(ai_response, context, description)
        self.registered_reports.append(new_report)

    def end_simulation(self, evolution: str, outcome: str, feedback: str):
        self.is_running = False
        self.result = SimulationResult(
            actions_taken=self.applied_actions.copy(),
            clinical_evolution=evolution,
            time_elapsed=self.elapsed_time_minutes,
            definitive_outcome=outcome,
            feedback=feedback,
        )
