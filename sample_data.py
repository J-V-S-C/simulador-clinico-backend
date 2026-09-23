"""Caso clínico de exemplo usado na demonstração pelo Streamlit."""

from models import (
    ClinicalEffect,
    Disease,
    Protocol,
    Symptom,
    SymptomState,
    VitalSign,
)
from repositories.repositories import DiseaseRepository


def create_disease_repository() -> DiseaseRepository:
    oxygenation_protocol = Protocol(
        name="Protocolo de oxigenação",
        orientation_content="Observe a respiração e a saturação do paciente.",
        help_content="Considere uma intervenção para melhorar a oxigenação.",
        expected_response=(
            "Administrar oxigênio e acompanhar a saturação do paciente."
        ),
        correct_effect=ClinicalEffect(
            symptom_intensity_changes={"Falta de ar": -3},
            vital_sign_value_changes={"Saturação de oxigênio": 2},
        ),
    )
    pain_protocol = Protocol(
        name="Protocolo de controle da dor",
        orientation_content="Avalie a intensidade e as características da dor.",
        help_content="Considere uma intervenção para aliviar a dor do paciente.",
        expected_response=(
            "Administrar analgesia adequada e reavaliar a dor do paciente."
        ),
        correct_effect=ClinicalEffect(
            symptom_intensity_changes={"Dor torácica": -5}
        ),
    )

    symptoms = [
        Symptom(
            name="Dor torácica",
            intensity=8,
            state=SymptomState.ACTIVE,
            is_visible=True,
            is_complex=False,
            protocol=pain_protocol,
            natural_evolution_per_minute=0.1,
            vital_sign_changes_per_minute={"Frequência cardíaca": 0.2},
        ),
        Symptom(
            name="Falta de ar",
            intensity=5,
            state=SymptomState.ACTIVE,
            is_visible=True,
            is_complex=False,
            protocol=oxygenation_protocol,
            natural_evolution_per_minute=0.1,
            vital_sign_changes_per_minute={"Saturação de oxigênio": -0.1},
        ),
    ]
    vital_signs = [
        VitalSign("Frequência cardíaca", 110, "bpm", maximum_critical_value=140),
        VitalSign("Saturação de oxigênio", 90, "%", minimum_critical_value=85),
    ]
    disease = Disease(
        name="Síndrome coronariana - caso didático",
        symptoms=symptoms,
        initial_vital_signs=vital_signs,
    )
    return DiseaseRepository([disease])
