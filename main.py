"""Interface visual da Sprint 3 construída com Streamlit."""

import subprocess
import sys
from pathlib import Path

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from application import SimulationService
from repositories.repositories import ReportRepository, SimulationRepository
from sample_data import create_disease_repository


def create_simulation_service() -> SimulationService:
    """Cria os repositórios e o serviço usados pela interface."""
    return SimulationService(
        disease_repository=create_disease_repository(),
        simulation_repository=SimulationRepository(),
        report_repository=ReportRepository(),
    )


def get_persistent_simulation_service() -> SimulationService:
    """Reutiliza o serviço na sessão; os repositórios persistem em CSV."""
    if "simulation_service" not in st.session_state:
        st.session_state.simulation_service = create_simulation_service()
    return st.session_state.simulation_service


def extract_disease_names(response: dict[str, object]) -> list[str]:
    disease_items = response.get("diseases")
    if not isinstance(disease_items, list):
        return []

    disease_names = []
    for disease_item in disease_items:
        if isinstance(disease_item, dict):
            disease_name = disease_item.get("name")
            if isinstance(disease_name, str):
                disease_names.append(disease_name)
    return disease_names


def extract_simulation_data(response: dict[str, object]) -> dict[str, object]:
    simulation = response.get("simulation")
    return simulation if isinstance(simulation, dict) else {}


def display_error(response: dict[str, object]) -> bool:
    """Exibe o erro e informa se a operação falhou."""
    if response.get("ok") is True:
        return False
    st.error(str(response.get("error", "Não foi possível realizar a operação.")))
    return True


def queue_success_message(message: str) -> None:
    """Preserva uma confirmação para a próxima renderização do Streamlit."""
    st.session_state.success_message = message


def display_queued_success_message() -> None:
    message = st.session_state.pop("success_message", None)
    if isinstance(message, str):
        st.success(message)


def display_start_screen(simulation_service: SimulationService) -> None:
    st.subheader("Iniciar simulação")
    disease_response = simulation_service.list_available_diseases()
    disease_names = extract_disease_names(disease_response)
    if not disease_names:
        st.warning("Nenhum caso clínico está configurado.")
        return

    selected_disease = st.selectbox("Caso clínico", disease_names)
    time_limit_minutes = st.number_input(
        "Limite de tempo em minutos", min_value=1, value=30, step=1
    )
    if st.button("Iniciar", type="primary"):
        response = simulation_service.start_new_simulation(
            selected_disease, int(time_limit_minutes)
        )
        if display_error(response):
            return
        simulation = extract_simulation_data(response)
        simulation_id = simulation.get("id")
        if isinstance(simulation_id, str):
            st.session_state.current_simulation_id = simulation_id
            queue_success_message("Simulação iniciada.")
            st.rerun()


def extract_symptom_names(simulation: dict[str, object]) -> list[str]:
    symptom_items = simulation.get("symptoms")
    if not isinstance(symptom_items, list):
        return []

    symptom_names = []
    for symptom_item in symptom_items:
        if isinstance(symptom_item, dict):
            symptom_name = symptom_item.get("name")
            if isinstance(symptom_name, str):
                symptom_names.append(symptom_name)
    return symptom_names


def display_protocol_tab(
    simulation_service: SimulationService,
    simulation_id: str,
    symptom_names: list[str],
) -> None:
    st.write("O sistema revela orientação, ajuda e resposta nessa ordem.")
    selected_symptom = st.selectbox(
        "Sintoma relacionado", symptom_names, key="protocol_symptom"
    )
    if st.button("Revelar próxima parte"):
        response = simulation_service.reveal_next_protocol_content(
            simulation_id, selected_symptom
        )
        if not display_error(response):
            st.success(f"Nível {response['level']}")
            st.info(str(response["content"]))


def display_interaction_tab(
    simulation_service: SimulationService,
    simulation_id: str,
    symptom_names: list[str],
) -> None:
    st.caption(
        "Nesta sprint, um mock simula a resposta e a avaliação da futura LLM."
    )
    with st.form("interaction_form"):
        student_text = st.text_area("Mensagem ou conduta do estudante")
        evaluated_symptom = st.selectbox("Sintoma avaliado", symptom_names)
        submitted = st.form_submit_button("Enviar ao paciente", type="primary")

    if submitted:
        response = simulation_service.register_interaction_using_llm_mock(
            simulation_id,
            student_text,
            evaluated_symptom,
        )
        if not display_error(response):
            st.success("Interação registrada e estado clínico atualizado.")
            interaction = response.get("interaction")
            if isinstance(interaction, dict):
                st.markdown("**Resposta do paciente**")
                st.write(interaction.get("patient_response", ""))
                st.caption(
                    f"Classificação simulada: {interaction.get('classification', '')}"
                )


def display_time_tab(
    simulation_service: SimulationService, simulation_id: str
) -> None:
    with st.form("advance_time_form"):
        elapsed_minutes = st.number_input(
            "Minutos transcorridos", min_value=1, value=1, step=1
        )
        submitted = st.form_submit_button("Avançar tempo")

    if submitted:
        response = simulation_service.advance_simulation_time(
            simulation_id, int(elapsed_minutes)
        )
        if not display_error(response):
            queue_success_message("Tempo e estado clínico atualizados.")
            st.rerun()


def display_report_tab(
    simulation_service: SimulationService, simulation_id: str
) -> None:
    with st.form("report_form"):
        ai_response = st.text_area("Resposta incoerente da IA")
        report_description = st.text_area("Descrição do problema")
        submitted = st.form_submit_button("Registrar denúncia")

    if submitted:
        response = simulation_service.report_ai_response(
            simulation_id, ai_response, report_description
        )
        if not display_error(response):
            st.success("Denúncia registrada.")


def display_end_simulation_tab(
    simulation_service: SimulationService, simulation_id: str
) -> None:
    with st.form("end_simulation_form"):
        outcome = st.text_input("Desfecho", value="Atendimento concluído")
        feedback = st.text_area("Feedback", value="Simulação encerrada.")
        submitted = st.form_submit_button("Encerrar simulação")

    if submitted:
        response = simulation_service.end_simulation(
            simulation_id, outcome, feedback
        )
        if not display_error(response):
            queue_success_message("Simulação encerrada.")
            st.rerun()


def display_active_simulation(
    simulation_service: SimulationService, simulation_id: str
) -> None:
    response = simulation_service.get_simulation_state(simulation_id)
    if display_error(response):
        return

    simulation = extract_simulation_data(response)
    st.subheader(str(simulation.get("disease_name", "Simulação")))
    display_simulation_summary(simulation)

    if simulation.get("is_running") is not True:
        st.success("A simulação foi encerrada.")
        display_simulation_result(simulation)
        display_interaction_history(simulation)
        if st.button("Iniciar outra simulação"):
            del st.session_state.current_simulation_id
            st.rerun()
        return

    symptom_names = extract_symptom_names(simulation)
    state_tab, protocol_tab, interaction_tab, time_tab, report_tab, end_tab = st.tabs(
        ["Estado", "Protocolos", "Interação", "Tempo", "Denúncia", "Encerrar"]
    )
    with state_tab:
        display_vital_signs(simulation)
        display_symptoms(simulation)
        display_interaction_history(simulation)
    with protocol_tab:
        display_protocol_tab(simulation_service, simulation_id, symptom_names)
    with interaction_tab:
        display_interaction_tab(simulation_service, simulation_id, symptom_names)
    with time_tab:
        display_time_tab(simulation_service, simulation_id)
    with report_tab:
        display_report_tab(simulation_service, simulation_id)
    with end_tab:
        display_end_simulation_tab(simulation_service, simulation_id)


def display_simulation_summary(simulation: dict[str, object]) -> None:
    elapsed_minutes = simulation.get("elapsed_time_minutes", 0)
    time_limit_minutes = simulation.get("time_limit_minutes", 0)
    interaction_items = simulation.get("interactions")
    interaction_count = len(interaction_items) if isinstance(interaction_items, list) else 0

    elapsed_column, limit_column, interaction_column = st.columns(3)
    elapsed_column.metric("Tempo decorrido", f"{elapsed_minutes} min")
    limit_column.metric("Limite", f"{time_limit_minutes} min")
    interaction_column.metric("Interações", interaction_count)


def format_clinical_value(value: object) -> str:
    """Formata números clínicos sempre com duas casas decimais."""
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return "-"


def display_vital_signs(simulation: dict[str, object]) -> None:
    st.markdown("### Sinais vitais")
    vital_sign_items = simulation.get("vital_signs")
    if not isinstance(vital_sign_items, list) or not vital_sign_items:
        st.info("Nenhum sinal vital registrado.")
        return

    columns = st.columns(len(vital_sign_items))
    for column, vital_sign_item in zip(columns, vital_sign_items):
        if not isinstance(vital_sign_item, dict):
            continue
        name = str(vital_sign_item.get("name", "Sinal vital"))
        value = format_clinical_value(vital_sign_item.get("value"))
        unit = str(vital_sign_item.get("unit", ""))
        column.metric(name, f"{value} {unit}")
        if vital_sign_item.get("is_critical") is True:
            column.error("Valor crítico")
        else:
            column.success("Estável")


def display_symptoms(simulation: dict[str, object]) -> None:
    st.markdown("### Sintomas")
    symptom_items = simulation.get("symptoms")
    protocol_progress = simulation.get("protocol_progress")
    progress_by_symptom = protocol_progress if isinstance(protocol_progress, dict) else {}
    if not isinstance(symptom_items, list) or not symptom_items:
        st.info("Nenhum sintoma registrado.")
        return

    for symptom_item in symptom_items:
        if not isinstance(symptom_item, dict):
            continue
        symptom_name = str(symptom_item.get("name", "Sintoma"))
        intensity_value = symptom_item.get("intensity", 0)
        intensity = float(intensity_value) if isinstance(intensity_value, (int, float)) else 0.0
        with st.container(border=True):
            name_column, severity_column, state_column = st.columns(3)
            name_column.markdown(f"**{symptom_name}**")
            severity_column.write(f"Gravidade: {symptom_item.get('severity', '-')}")
            state_column.write(f"Estado: {symptom_item.get('state', '-')}")
            st.progress(intensity / 10, text=f"Intensidade: {intensity:.2f}/10.00")
            st.caption(
                f"Protocolo revelado até o nível "
                f"{progress_by_symptom.get(symptom_name, 0)} de 3"
            )


def display_interaction_history(simulation: dict[str, object]) -> None:
    st.markdown("### Histórico de interações")
    interaction_items = simulation.get("interactions")
    if not isinstance(interaction_items, list) or not interaction_items:
        st.info("Nenhuma interação registrada.")
        return

    for position, interaction_item in enumerate(interaction_items, start=1):
        if not isinstance(interaction_item, dict):
            continue
        title = f"Interação {position} — {interaction_item.get('evaluated_symptom_name', '')}"
        with st.expander(title):
            st.markdown("**Estudante**")
            st.write(interaction_item.get("student_text", ""))
            st.markdown("**Paciente virtual**")
            st.write(interaction_item.get("patient_response", ""))
            st.caption(f"Classificação: {interaction_item.get('classification', '')}")


def display_simulation_result(simulation: dict[str, object]) -> None:
    result = simulation.get("result")
    if not isinstance(result, dict):
        return
    st.markdown("### Resultado")
    with st.container(border=True):
        st.markdown(f"**Desfecho:** {result.get('definitive_outcome', '-')}")
        st.write(result.get("feedback", ""))
        st.caption(result.get("clinical_evolution", ""))


def run_streamlit_interface() -> None:
    st.set_page_config(page_title="Simulador clínico", page_icon="🩺")
    st.title("Simulador clínico")
    st.caption("Computational Thinking with Python — Sprint 3")
    display_queued_success_message()

    simulation_service = get_persistent_simulation_service()
    simulation_id = st.session_state.get("current_simulation_id")
    if isinstance(simulation_id, str):
        display_active_simulation(simulation_service, simulation_id)
    else:
        display_start_screen(simulation_service)


def start_application() -> None:
    """Abre o servidor quando executado com Python ou renderiza dentro dele."""
    if get_script_run_ctx(suppress_warning=True) is None:
        application_file = str(Path(__file__).resolve())
        try:
            subprocess.run(
                [sys.executable, "-m", "streamlit", "run", application_file],
                check=False,
            )
        except KeyboardInterrupt:
            pass
        return
    run_streamlit_interface()


if __name__ == "__main__":
    start_application()
