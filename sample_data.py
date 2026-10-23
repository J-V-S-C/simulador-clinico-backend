"""Templates de casos clínicos usados pela API."""

from models import (
    ClinicalEffect,
    Disease,
    Protocol,
    Symptom,
    SymptomState,
    VitalSign,
)


def create_cardiac_case() -> Disease:
    """Emergency recognition case; clinical actions are escalation and observation."""
    oxygenation_protocol = Protocol(
        name="Reconhecimento da falta de ar",
        orientation_content="Observe a respiração e pergunte sobre a dor no peito.",
        help_content="Considere a falta de ar com dor torácica uma emergência e peça ajuda imediata.",
        expected_response="Acionar a equipe de emergência imediatamente, manter o paciente em repouso e acompanhar a respiração.",
        correct_effect=ClinicalEffect(symptom_intensity_changes={"Falta de ar": -3}),
        reference_source="https://www.nhs.uk/conditions/heart-attack/",
    )
    pain_protocol = Protocol(
        name="Reconhecimento da dor torácica",
        orientation_content="Pergunte sobre a dor no peito e sintomas associados.",
        help_content="Considere a dor torácica com falta de ar uma emergência e peça ajuda imediata.",
        expected_response="Acionar a equipe de emergência imediatamente, manter o paciente em repouso e acompanhar a dor torácica.",
        correct_effect=ClinicalEffect(symptom_intensity_changes={"Dor torácica": -5}),
        reference_source="https://www.nhs.uk/conditions/heart-attack/",
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
    return Disease(
        name="Síndrome coronariana - caso didático",
        symptoms=symptoms,
        initial_vital_signs=vital_signs,
    )


def create_beginner_case() -> Disease:
    """Fictional, plain-language case for first-time students."""
    fever = Protocol(
        name="Cuidados iniciais com febre",
        orientation_content="Pergunte quando a febre começou e acompanhe a temperatura.",
        help_content="Considere hidratação e reavaliação da temperatura.",
        expected_response="Oferecer líquidos, observar sinais de alerta e reavaliar a temperatura.",
        correct_effect=ClinicalEffect(symptom_intensity_changes={"Febre": -3}, vital_sign_value_changes={"Temperatura": -0.8}),
        partially_correct_effect=ClinicalEffect(symptom_intensity_changes={"Febre": -0.8}, vital_sign_value_changes={"Temperatura": -0.2}),
        reference_source="https://www.nhs.uk/symptoms/fever-in-adults/",
    )
    headache = Protocol(
        name="Avaliação da dor de cabeça",
        orientation_content="Pergunte sobre a intensidade e outros sintomas.",
        help_content="Considere repouso e reavaliação da dor.",
        expected_response="Orientar repouso, hidratação e reavaliar a dor de cabeça.",
        correct_effect=ClinicalEffect(symptom_intensity_changes={"Dor de cabeça": -3}),
        partially_correct_effect=ClinicalEffect(symptom_intensity_changes={"Dor de cabeça": -0.8}),
        reference_source="https://www.nhs.uk/symptoms/headaches/",
    )
    return Disease(
        name="Febre e dor de cabeça - caso introdutório",
        symptoms=[Symptom("Febre", 4, SymptomState.ACTIVE, True, False, fever, 0.7, {"Temperatura": 0.42})],
        optional_symptoms=[
            Symptom("Dor de cabeça", 4, SymptomState.ACTIVE, True, False, headache, 0.7),
            Symptom("Calafrios", 3.5, SymptomState.ACTIVE, False, False, Protocol(
                name="Observação de calafrios",
                orientation_content="Pergunte sobre outras queixas e observe os calafrios.",
                help_content="Considere repouso, líquidos e reavaliação da temperatura.",
                expected_response="Orientar repouso e hidratação, acompanhar a temperatura e observar sinais de alerta.",
                correct_effect=ClinicalEffect(symptom_intensity_changes={"Calafrios": -2.5}),
                partially_correct_effect=ClinicalEffect(symptom_intensity_changes={"Calafrios": -0.7}),
                reference_source="https://www.nhs.uk/symptoms/fever-in-adults/",
            ), 0.6),
        ],
        initial_vital_signs=[VitalSign("Temperatura", 38.0, "°C", maximum_critical_value=40.5)],
    )


def create_cold_case() -> Disease:
    """Plain-language respiratory case with one variable second complaint."""
    nose = Protocol(
        "Cuidados com congestão nasal", "Pergunte há quanto tempo o nariz está obstruído.",
        "Considere repouso, líquidos e sinais de piora que exigem avaliação.",
        "Orientar repouso e hidratação, reavaliar a congestão e buscar avaliação médica se houver falta de ar ou piora.",
        correct_effect=ClinicalEffect({"Nariz entupido": -3}, {"Frequência cardíaca": -6}),
        partially_correct_effect=ClinicalEffect({"Nariz entupido": -0.8}),
        reference_source="https://www.nhs.uk/conditions/common-cold/",
    )
    cough = Protocol(
        "Avaliação da tosse", "Pergunte quando começou e se há falta de ar.",
        "Considere repouso, líquidos e necessidade de avaliação se houver falta de ar.",
        "Orientar repouso e hidratação, reavaliar a tosse e buscar avaliação médica se houver falta de ar ou piora.",
        correct_effect=ClinicalEffect({"Tosse": -3}),
        partially_correct_effect=ClinicalEffect({"Tosse": -0.8}),
        reference_source="https://www.nhs.uk/conditions/common-cold/",
    )
    throat = Protocol(
        "Avaliação da garganta", "Pergunte se há mais sintomas e avalie a garganta.",
        "Considere líquidos, repouso e sinais de alerta.",
        "Orientar líquidos e repouso, reavaliar a garganta e buscar atendimento urgente se houver dificuldade para engolir ou respirar.",
        correct_effect=ClinicalEffect({"Dor de garganta": -3}),
        partially_correct_effect=ClinicalEffect({"Dor de garganta": -0.8}),
        reference_source="https://www.nhs.uk/symptoms/sore-throat/",
    )
    return Disease(
        "Resfriado leve - caso introdutório",
        [Symptom("Nariz entupido", 4, SymptomState.ACTIVE, True, False, nose, 0.65, {"Frequência cardíaca": 3})],
        [VitalSign("Frequência cardíaca", 84, "bpm", maximum_critical_value=125)],
        optional_symptoms=[
            Symptom("Tosse", 4, SymptomState.ACTIVE, True, False, cough, 0.7),
            Symptom("Dor de garganta", 3.5, SymptomState.ACTIVE, False, False, throat, 0.65),
        ],
    )


def create_dizziness_case() -> Disease:
    """Introductory observation case about dizziness after activity."""
    dizziness = Protocol(
        "Observação da tontura", "Pergunte quando começou e se houve queda ou desmaio.",
        "Considere interromper a atividade, repousar e oferecer água.",
        "Orientar que se sente ou deite, oferecer água se puder beber, observar sinais de alerta e reavaliar.",
        correct_effect=ClinicalEffect({"Tontura": -3}, {"Frequência cardíaca": -8}),
        partially_correct_effect=ClinicalEffect({"Tontura": -0.8}),
        reference_source="https://www.nhs.uk/symptoms/dizziness/",
    )
    thirst = Protocol(
        "Avaliação da sede", "Pergunte se há outras queixas e quanto líquido bebeu.",
        "Considere hidratação e reavaliação.",
        "Oferecer água se puder beber, acompanhar a resposta e observar sinais de alerta.",
        correct_effect=ClinicalEffect({"Sede": -3}),
        partially_correct_effect=ClinicalEffect({"Sede": -0.8}),
        reference_source="https://www.nhs.uk/conditions/dehydration/",
    )
    tired = Protocol(
        "Avaliação do cansaço", "Pergunte se há outras queixas e quando surgiu o cansaço.",
        "Considere repouso, líquidos e reavaliação.",
        "Orientar repouso e líquidos se puder beber, observar piora e reavaliar o cansaço.",
        correct_effect=ClinicalEffect({"Cansaço": -3}),
        partially_correct_effect=ClinicalEffect({"Cansaço": -0.8}),
        reference_source="https://www.nhs.uk/conditions/dehydration/",
    )
    return Disease(
        "Tontura após atividade - caso introdutório",
        [Symptom("Tontura", 4, SymptomState.ACTIVE, True, False, dizziness, 0.7, {"Frequência cardíaca": 4})],
        [VitalSign("Frequência cardíaca", 96, "bpm", maximum_critical_value=130)],
        optional_symptoms=[
            Symptom("Sede", 3.5, SymptomState.ACTIVE, True, False, thirst, 0.65),
            Symptom("Cansaço", 3.5, SymptomState.ACTIVE, False, False, tired, 0.65),
        ],
    )


def create_public_cases() -> list[Disease]:
    return [create_beginner_case(), create_cold_case(), create_dizziness_case(), create_cardiac_case()]
