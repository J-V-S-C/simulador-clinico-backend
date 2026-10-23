"""Modelos de domínio do simulador clínico."""

from enum import Enum
import re
from typing import Dict, List, Optional
import unicodedata
from uuid import uuid4


DECIMAL_PLACES = 3


def round_clinical_value(value: float) -> float:
    """Mantém a progressão por segundo visível sem acumular erro de arredondamento."""
    return round(float(value), DECIMAL_PLACES)


class Severity(Enum):
    LOW = 1
    MODERATE = 2
    HIGH = 3


class SymptomState(Enum):
    ACTIVE = "active"
    INHIBITED = "inhibited"
    INACTIVE = "inactive"


class InteractionClassification(Enum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    ASSESSMENT = "assessment"
    INCORRECT = "incorrect"


def is_assessment_only(text: str) -> bool:
    """Questions and observation alone cannot resolve a simulated complaint."""
    plain = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return False
    # A question with no following instruction remains an assessment, even if
    # it asks whether the patient drank water or rested.
    intervention_command = re.search(
        r"\b(oriente?\w*|recomend\w*|oferec\w*|administr\w*|"
        r"acion\w*|encaminh\w*|procure|busque|beba|hidrate|"
        r"repouse|descanse|deite|chame)\b",
        plain,
    )
    if plain.endswith("?") and not intervention_command:
        return True
    assessment = re.search(
        r"\b(reavali\w*|avali\w*|verif\w*|observ\w*|monitor\w*|"
        r"pergunt\w*|question\w*|medir\w*|meca|"
        r"o que|como|quando|quais|qual|sente|sentindo|sintomas?)\b",
        plain,
    )
    intervention = re.search(
        r"\b(hidrat\w*|liquid\w*|repous\w*|descans\w*|oferec\w*|"
        r"administr\w*|acion\w*|encaminh\w*|procur\w*|busc\w*|"
        r"beb\w*|agua|oxigen\w*|trat\w*|deit\w*|sentar|"
        r"cham\w*|ligar|urgenc\w*|emergenc\w*)\b",
        plain,
    )
    return bool(assessment and not intervention)


class ClinicalEffect:
    """Mudanças causadas no paciente após a avaliação de uma conduta.

    Exemplo: {"Falta de ar": -3} reduz a intensidade desse sintoma em
    três pontos. {"Saturação de oxigênio": 2} aumenta o sinal vital em
    duas unidades.
    """

    def __init__(
        self,
        symptom_intensity_changes: Optional[Dict[str, float]] = None,
        vital_sign_value_changes: Optional[Dict[str, float]] = None,
    ):
        self.symptom_intensity_changes = {
            name: round_clinical_value(value)
            for name, value in (symptom_intensity_changes or {}).items()
        }
        self.vital_sign_value_changes = {
            name: round_clinical_value(value)
            for name, value in (vital_sign_value_changes or {}).items()
        }


class Protocol:
    """Conteúdo clínico apresentado progressivamente e usado na avaliação.

    A orientação e a ajuda podem ser apresentadas ao estudante. A resposta
    esperada é a fonte da verdade enviada à LLM para avaliar a conduta.
    """

    def __init__(
        self,
        name: str,
        orientation_content: str,
        help_content: str,
        expected_response: str,
        correct_effect: Optional[ClinicalEffect] = None,
        partially_correct_effect: Optional[ClinicalEffect] = None,
        incorrect_effect: Optional[ClinicalEffect] = None,
        reference_source: Optional[str] = None,
    ):
        self.name = name
        self.orientation_content = orientation_content
        self.help_content = help_content
        self.expected_response = expected_response
        self.correct_effect = correct_effect or ClinicalEffect()
        self.partially_correct_effect = partially_correct_effect or ClinicalEffect()
        self.incorrect_effect = incorrect_effect or ClinicalEffect()
        self.reference_source = reference_source

    def get_content_for_level(self, level: int) -> str:
        if level == 1:
            return self.orientation_content
        if level == 2:
            return self.help_content
        if level == 3:
            return self.expected_response
        raise ValueError("O nível do protocolo deve estar entre 1 e 3.")

    def get_effect_for_classification(
        self, classification: InteractionClassification
    ) -> ClinicalEffect:
        if classification == InteractionClassification.CORRECT:
            return self.correct_effect
        if classification == InteractionClassification.PARTIALLY_CORRECT:
            return self.partially_correct_effect
        if classification == InteractionClassification.ASSESSMENT:
            return ClinicalEffect()
        return self.incorrect_effect


class Symptom:
    def __init__(
        self,
        name: str,
        intensity: float,
        state: SymptomState,
        is_visible: bool,
        is_complex: bool,
        protocol: Protocol,
        natural_evolution_per_minute: float = 0.0,
        vital_sign_changes_per_minute: Optional[Dict[str, float]] = None,
    ):
        self.name = name
        self.intensity = self.limit_intensity(intensity)
        self.state = state
        self.is_visible = is_visible
        self.is_complex = is_complex
        self.protocol = protocol
        self.natural_evolution_per_minute = round_clinical_value(
            natural_evolution_per_minute
        )
        self.vital_sign_changes_per_minute = {
            name: round_clinical_value(value)
            for name, value in (vital_sign_changes_per_minute or {}).items()
        }

    def limit_intensity(self, value: float) -> float:
        return round_clinical_value(max(0.0, min(10.0, float(value))))

    def get_severity(self) -> Severity:
        if self.intensity <= 3:
            return Severity.LOW
        if self.intensity <= 6:
            return Severity.MODERATE
        return Severity.HIGH

    def is_active(self) -> bool:
        return self.state == SymptomState.ACTIVE

    def evolve(self, minutes: int) -> None:
        if self.state == SymptomState.ACTIVE:
            change = self.natural_evolution_per_minute * minutes
            self.intensity = self.limit_intensity(self.intensity + change)


class VitalSign:
    def __init__(
        self,
        name: str,
        value: float,
        unit: str,
        minimum_critical_value: Optional[float] = None,
        maximum_critical_value: Optional[float] = None,
    ):
        self.name = name
        self.value = round_clinical_value(value)
        self.unit = unit
        self.minimum_critical_value = (
            round_clinical_value(minimum_critical_value)
            if minimum_critical_value is not None
            else None
        )
        self.maximum_critical_value = (
            round_clinical_value(maximum_critical_value)
            if maximum_critical_value is not None
            else None
        )

    def update(self, value_change: float) -> None:
        self.value = round_clinical_value(self.value + value_change)

    def is_critical(self) -> bool:
        below_minimum = (
            self.minimum_critical_value is not None
            and self.value <= self.minimum_critical_value
        )
        above_maximum = (
            self.maximum_critical_value is not None
            and self.value >= self.maximum_critical_value
        )
        return below_minimum or above_maximum


class Patient:
    def __init__(self, name: str, vital_signs: List[VitalSign], symptoms: List[Symptom]):
        self.name = name
        self.vital_signs = vital_signs
        self.symptoms = symptoms

    def find_symptom(self, symptom_name: str) -> Optional[Symptom]:
        return next(
            (symptom for symptom in self.symptoms if symptom.name == symptom_name),
            None,
        )

    def find_vital_sign(self, vital_sign_name: str) -> Optional[VitalSign]:
        return next(
            (vital_sign for vital_sign in self.vital_signs if vital_sign.name == vital_sign_name),
            None,
        )

    def apply_clinical_effect(self, effect: ClinicalEffect) -> None:
        for symptom_name, intensity_change in effect.symptom_intensity_changes.items():
            symptom = self.find_symptom(symptom_name)
            if symptom:
                symptom.intensity = symptom.limit_intensity(
                    symptom.intensity + intensity_change
                )

        for vital_sign_name, value_change in effect.vital_sign_value_changes.items():
            vital_sign = self.find_vital_sign(vital_sign_name)
            if vital_sign:
                vital_sign.update(value_change)

    def evolve_over_time(self, minutes: int) -> None:
        if minutes <= 0:
            return

        for symptom in self.symptoms:
            symptom.evolve(minutes)
            if symptom.is_active():
                for vital_sign_name, change_per_minute in symptom.vital_sign_changes_per_minute.items():
                    vital_sign = self.find_vital_sign(vital_sign_name)
                    if vital_sign:
                        vital_sign.update(change_per_minute * minutes)

    def has_critical_aggravation(self) -> bool:
        return any(vital_sign.is_critical() for vital_sign in self.vital_signs)


class Disease:
    """Configuração de um caso usada para criar o paciente da simulação."""

    def __init__(
        self,
        name: str,
        symptoms: List[Symptom],
        initial_vital_signs: List[VitalSign],
        optional_symptoms: Optional[List[Symptom]] = None,
    ):
        self.name = name
        self.symptoms = symptoms
        self.initial_vital_signs = initial_vital_signs
        self.optional_symptoms = optional_symptoms or []


class Interaction:
    """Uma troca textual entre o estudante e o paciente virtual."""

    def __init__(
        self,
        student_text: str,
        patient_response: str,
        classification: InteractionClassification,
        evaluated_symptom_name: str,
        interaction_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        self.id = interaction_id or str(uuid4())
        self.student_text = student_text
        self.patient_response = patient_response
        self.classification = classification
        self.evaluated_symptom_name = evaluated_symptom_name
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class Report:
    def __init__(
        self,
        ai_response: str,
        simulation_context: str,
        report_description: str,
    ):
        self.ai_response = ai_response
        self.simulation_context = simulation_context
        self.report_description = report_description


class SimulationResult:
    def __init__(
        self,
        interactions: List[Interaction],
        clinical_evolution: str,
        time_elapsed: float,
        definitive_outcome: str,
        feedback: str,
    ):
        self.interactions = interactions
        self.clinical_evolution = clinical_evolution
        self.time_elapsed = time_elapsed
        self.definitive_outcome = definitive_outcome
        self.feedback = feedback


class Simulation:
    def __init__(
        self,
        disease: Disease,
        patient: Patient,
        time_limit_minutes: int,
        simulation_id: Optional[str] = None,
    ):
        self.id = simulation_id or str(uuid4())
        self.disease = disease
        self.patient = patient
        self.time_limit_minutes = time_limit_minutes
        self.elapsed_time_minutes = 0
        self.elapsed_time_seconds = 0
        self.last_effective_action_second: Optional[int] = None
        self.interactions: List[Interaction] = []
        self.registered_reports: List[Report] = []
        self.revealed_protocol_level_by_symptom: Dict[str, int] = {}
        self.is_running = False
        self.result: Optional[SimulationResult] = None

    def start(self) -> None:
        if self.is_running or self.result is not None:
            raise RuntimeError("A simulação já foi iniciada.")
        self.is_running = True

    def reveal_next_protocol_content(self, symptom_name: str) -> tuple[int, str, bool]:
        if not self.is_running:
            raise RuntimeError("A simulação não está em andamento.")
        symptom = self.patient.find_symptom(symptom_name)
        if symptom is None:
            raise ValueError("Sintoma não encontrado.")

        current_level = self.revealed_protocol_level_by_symptom.get(symptom_name, 0)
        if current_level >= 3:
            raise ValueError("Todos os níveis desse protocolo já foram revelados.")

        revealed_level = current_level + 1
        content = symptom.protocol.get_content_for_level(revealed_level)
        self.revealed_protocol_level_by_symptom[symptom_name] = revealed_level
        return revealed_level, content, revealed_level < 3

    def register_interaction(
        self,
        student_text: str,
        patient_response: str,
        classification: InteractionClassification,
        evaluated_symptom_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        revealed_symptoms: Optional[List[str]] = None,
    ) -> Interaction:
        if not self.is_running:
            raise RuntimeError("A simulação não está em andamento.")
        symptom = self.patient.find_symptom(evaluated_symptom_name)
        if symptom is None:
            raise ValueError("Sintoma avaliado não encontrado.")
        if not symptom.is_visible or not symptom.is_active():
            raise ValueError("O sintoma não está disponível para esta conduta.")

        interaction = Interaction(
            student_text,
            patient_response,
            classification,
            evaluated_symptom_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.interactions.append(interaction)
        for name in revealed_symptoms or []:
            discovered = self.patient.find_symptom(name)
            if discovered and discovered.is_active():
                discovered.is_visible = True
        effect = symptom.protocol.get_effect_for_classification(classification)
        self.patient.apply_clinical_effect(effect)
        if classification == InteractionClassification.CORRECT:
            # A successful case records that this complaint was addressed once.
            # Further messages cannot farm the same protocol effect.
            symptom.state = SymptomState.INHIBITED
            if not any(item.is_active() and item.is_visible for item in self.patient.symptoms):
                for undiscovered in self.patient.symptoms:
                    if undiscovered.is_active():
                        undiscovered.is_visible = True
        if classification in (InteractionClassification.CORRECT, InteractionClassification.PARTIALLY_CORRECT):
            self.last_effective_action_second = self.elapsed_time_seconds
        return interaction

    def all_symptoms_addressed(self) -> bool:
        return bool(self.patient.symptoms) and all(
            not symptom.is_active() for symptom in self.patient.symptoms
        )

    def advance_time(self, minutes: int) -> None:
        if not self.is_running:
            raise RuntimeError("A simulação não está em andamento.")
        if minutes <= 0:
            raise ValueError("O tempo avançado deve ser positivo.")
        self.advance_seconds(minutes * 60)

    def advance_seconds(self, seconds: int) -> None:
        if not self.is_running:
            raise RuntimeError("A simulação não está em andamento.")
        if seconds <= 0:
            raise ValueError("O tempo avançado deve ser positivo.")
        for _ in range(seconds):
            self.elapsed_time_seconds += 1
            self.elapsed_time_minutes = self.elapsed_time_seconds // 60
            scale = 5 / self.time_limit_minutes
            since_action = self.elapsed_time_seconds - (self.last_effective_action_second or 0)
            pressure = 1 + 2 * min(1, since_action / (self.time_limit_minutes * 60))
            if self.last_effective_action_second is not None:
                pressure *= 0.4
            for symptom in self.patient.symptoms:
                if not symptom.is_active():
                    continue
                symptom.intensity = symptom.limit_intensity(
                    symptom.intensity + symptom.natural_evolution_per_minute * scale * pressure / 60
                )
                for name, per_minute in symptom.vital_sign_changes_per_minute.items():
                    vital = self.patient.find_vital_sign(name)
                    if vital:
                        vital.update(per_minute * scale * pressure / 60)

    def has_time_expired(self) -> bool:
        return self.elapsed_time_seconds >= self.time_limit_minutes * 60

    def end(self, clinical_evolution: str, outcome: str, feedback: str) -> None:
        if not self.is_running:
            raise RuntimeError("A simulação não está em andamento.")
        self.is_running = False
        self.result = SimulationResult(
            self.interactions.copy(),
            clinical_evolution,
            round(self.elapsed_time_seconds / 60, 1),
            outcome,
            feedback,
        )
