"""Templates de casos clínicos usados pela API.

Cada sintoma tem um protocolo próprio, derivado da página pública do NHS mais
específica para aquela queixa. As ações essenciais descrevem o núcleo clínico
que o estudante precisa demonstrar; orientações de seguimento e sinais de
alerta continuam no texto, mas não são exigidos para concluir a queixa.
"""

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
        orientation_content="Observe o ritmo respiratório, verifique se há dificuldade para falar e pergunte sobre dor no peito ou tontura.",
        help_content="Falta de ar aguda com suspeita cardíaca: mantenha o paciente sentado com encosto apoiado, afrouxe roupas e acione emergência (SAMU 192).",
        expected_response="Acionar a equipe de emergência imediatamente (SAMU 192), manter o paciente sentado com encosto apoiado em repouso absoluto, monitorar a respiração e não deixá-lo sozinho.",
        essential_actions=[
            ["emergencia", "samu", "192", "socorro", "ambulancia", "equipe medica", "ajuda medica"],
            ["repouso", "repousar", "repouse", "sentar", "sente", "deitar", "deite"],
        ],
        correct_effect=ClinicalEffect(symptom_intensity_changes={"Falta de ar": -3}),
        reference_source="https://www.nhs.uk/conditions/heart-attack/",
    )
    pain_protocol = Protocol(
        name="Reconhecimento da dor torácica",
        orientation_content="Investigue as características da dor: aperto ou peso no peito, irradiação para braço, pescoço ou mandíbula e sintomas como suor frio ou náusea.",
        help_content="Dor no peito com aperto é suspeita de infarto: interrompa qualquer esforço, coloque o paciente sentado ou deitado em repouso e chame socorro médico imediato (192).",
        expected_response="Acionar o serviço de emergência imediatamente (192), posicionar o paciente em repouso absoluto sentado confortavelmente com as costas apoiadas, manter a calma e acompanhar os sinais vitais até a chegada do socorro.",
        essential_actions=[
            ["emergencia", "samu", "192", "socorro", "ambulancia", "equipe medica", "ajuda medica"],
            ["repouso", "repousar", "repouse", "sentar", "sente", "deitar", "deite"],
        ],
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
        orientation_content="Pergunte quando a febre começou, meça a temperatura e verifique se há calafrios, dor no corpo ou sudorese.",
        help_content="Ofereça líquidos frequentemente para evitar desidratação, mantenha repouso em roupas leves e use antitérmico para conforto se necessário.",
        expected_response="Oferecer hidratação frequente com água fresca, manter repouso em ambiente arejado com roupas leves e administrar paracetamol ou ibuprofeno se houver desconforto febril; medir a temperatura periodicamente.",
        essential_actions=[
            ["hidratacao", "hidratar", "hidrate", "liquidos", "liquido", "agua", "beber", "beba"],
            ["paracetamol", "ibuprofeno", "antitermico", "antitermicos"],
        ],
        correct_effect=ClinicalEffect(symptom_intensity_changes={"Febre": -3}, vital_sign_value_changes={"Temperatura": -0.8}),
        partially_correct_effect=ClinicalEffect(symptom_intensity_changes={"Febre": -0.8}, vital_sign_value_changes={"Temperatura": -0.2}),
        reference_source="https://www.nhs.uk/symptoms/fever-in-adults/",
    )
    headache = Protocol(
        name="Avaliação da dor de cabeça",
        orientation_content="Pergunte sobre a intensidade, localização da dor e se há sensibilidade à luz ou barulho, rigidez no pescoço ou náusea.",
        help_content="Oriente repouso em ambiente calmo e com pouca luz, hidratação adequada com água e uso de analgésico comum (paracetamol ou ibuprofeno).",
        expected_response="Orientar repouso em local silencioso e com luz suave, oferecer água para beber e indicar paracetamol ou ibuprofeno para alívio da dor; buscar avaliação médica se houver rigidez de nuca ou piora súbita.",
        essential_actions=[
            ["repouso", "repousar", "repouse", "descanso", "descanse", "descansar"],
            ["paracetamol", "ibuprofeno", "analgesico", "analgesicos"],
        ],
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
                orientation_content="Observe se há tremores involuntários ou sensação de frio intenso e meça a temperatura axilar.",
                help_content="Aqueça o paciente com agasalho confortável ou cobertor leve, ofereça líquidos mornos e acompanhe a temperatura.",
                expected_response="Manter o paciente confortavelmente aquecido com agasalho ou cobertor sem superaquecer, oferecer líquidos para hidratação e medir a temperatura regularmente; observar sinais de alerta.",
                essential_actions=[
                    ["aquecido", "aquecer", "cobertor", "cobertores", "agasalho", "agasalhar", "repousar", "repouso"],
                    ["hidratacao", "hidratar", "hidrate", "liquidos", "liquido", "agua", "beber", "beba"],
                ],
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
        "Cuidados com congestão nasal",
        "Pergunte há quanto tempo o nariz está entupido e se há febre associada, dor facial ou secreção espessa.",
        "Inalar vapor de banho morno e beber água ajudam a fluidificar o muco; descongestionantes podem ser considerados com moderação.",
        "Orientar repouso, hidratação hídrica abundante, inalação com vapor do banho morno e, se necessário para adultos, descongestionante nasal por no máximo 7 dias.",
        essential_actions=[
            ["repouso", "repousar", "repouse", "descanso", "descanse", "descansar"],
            ["hidratacao", "hidratar", "hidrate", "liquidos", "liquido", "agua", "beber", "beba", "vapor", "inalar", "descongestionante"],
        ],
        correct_effect=ClinicalEffect({"Nariz entupido": -3}, {"Frequência cardíaca": -6}),
        partially_correct_effect=ClinicalEffect({"Nariz entupido": -0.8}),
        reference_source="https://www.nhs.uk/conditions/common-cold/",
    )
    cough = Protocol(
        "Cuidados com a tosse",
        "Pergunte se a tosse é seca ou produtiva, quando começou e se há falta de ar, dor no peito ou febre.",
        "Ofereça líquidos mornos com frequência e considere uma colher de mel para suavizar a garganta (somente maiores de 1 ano).",
        "Orientar repouso e hidratação abundante com água ou chás, oferecer uma colher de mel para aliviar o reflexo da tosse (não dar mel a menores de 1 ano) e evitar fumaça de cigarro.",
        essential_actions=[
            ["mel"],
            ["hidratacao", "hidratar", "hidrate", "liquidos", "liquido", "agua", "beber", "beba"],
        ],
        correct_effect=ClinicalEffect({"Tosse": -3}),
        partially_correct_effect=ClinicalEffect({"Tosse": -0.8}),
        reference_source="https://www.nhs.uk/conditions/common-cold/",
    )
    throat = Protocol(
        "Cuidados com a dor de garganta",
        "Pergunte se a dor piora ao engolir, examine a garganta para presença de vermelhidão e verifique febre ou gânglios doloridos no pescoço.",
        "Oriente gargarejo com água morna e sal para aliviar o desconforto e estimule a ingestão constante de líquidos frescos.",
        "Orientar gargarejo com água morna e sal, beber bastante água para não desidratar, ingerir alimentos macios ou frios, manter repouso e oferecer paracetamol ou ibuprofeno se houver dor intensa.",
        essential_actions=[
            ["gargarejo", "gargarejar", "gargareje", "gargarejos"],
            ["hidratacao", "hidratar", "hidrate", "liquidos", "liquido", "agua", "beber", "beba", "repouso", "repousar", "repouse"],
        ],
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
        "Observação da tontura",
        "Pergunte quando a tontura começou, se a sensação é de desequilíbrio, cabeça leve ou se o ambiente parece rodar, e verifique se houve queda.",
        "Interrompa qualquer atividade: deite ou sente o paciente imediatamente até a sensação passar, oriente a não levantar de repente e ofereça água se tolerar.",
        "Interromper qualquer movimento ou atividade de risco, acomodar o paciente deitado ou sentado até a crise passar, orientar a levantar-se muito devagar, hidratar com pequenos goles de água e evitar movimentos bruscos da cabeça.",
        essential_actions=[
            ["sentar", "sente", "deitar", "deite", "deitado", "interromper", "interrompa", "parar", "pare", "repouso", "repouse"],
            ["hidratacao", "hidratar", "hidrate", "agua", "liquidos", "liquido"],
        ],
        correct_effect=ClinicalEffect({"Tontura": -3}, {"Frequência cardíaca": -8}),
        partially_correct_effect=ClinicalEffect({"Tontura": -0.8}),
        reference_source="https://www.nhs.uk/symptoms/dizziness/",
    )
    thirst = Protocol(
        "Avaliação da sede",
        "Pergunte há quanto tempo o paciente sente sede excessiva, se a boca está seca e quanto líquido ingeriu após a atividade física.",
        "Sinal de desidratação: ofereça água fresca ou solução de reidratação oral em pequenos goles graduais para não provocar vômito.",
        "Oferecer reidratação com pequenos goles graduais de água fresca ou solução de sais de reidratação oral, evitar bebidas alcoólicas ou cafeinadas e acompanhar até melhora da sede e coloração clara da urina.",
        essential_actions=[
            ["agua", "hidratacao", "hidratar", "hidrate", "liquidos", "liquido", "beber", "beba", "reidratacao", "soro"],
        ],
        correct_effect=ClinicalEffect({"Sede": -3}),
        partially_correct_effect=ClinicalEffect({"Sede": -0.8}),
        reference_source="https://www.nhs.uk/conditions/dehydration/",
    )
    tired = Protocol(
        "Avaliação do cansaço",
        "Pergunte quando surgiu o cansaço, se há sonolência, fraqueza nas pernas ou braços e se houve exposição prolongada ao sol ou calor.",
        "Interrompa todo esforço: oriente o paciente a repousar imediatamente sentado ou deitado em local fresco e bem ventilado.",
        "Orientar repouso imediato em ambiente fresco e ventilado, fornecer hidratação oral fracionada com água fresca e monitorar sinais vitais; buscar avaliação médica se houver confusão, desmaio ou persistência do quadro.",
        essential_actions=[
            ["repouso", "repousar", "repouse", "descanso", "descanse", "descansar", "sentar", "sente", "deitar", "deite"],
            ["hidratacao", "hidratar", "hidrate", "liquidos", "liquido", "agua", "beber", "beba"],
        ],
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
