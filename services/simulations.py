"""Simulation use cases. Domain owns clinical transitions."""

from copy import deepcopy
from datetime import timedelta
from math import ceil
from collections.abc import AsyncIterator
from random import choice
import re
import unicodedata

from models import InteractionClassification, Patient, Simulation, SymptomState, is_assessment_only
from ports.clock import Clock
from ports.evaluator import Evaluator
from ports.storage import SavedSimulation, Store
from ports.errors import ServiceError
from services.presentation import simulation_view


class SimulationService:
    def __init__(self, store: Store, evaluator: Evaluator, clock: Clock):
        self.store = store
        self.evaluator = evaluator
        self.clock = clock

    def start(self, owner_id: str, case_id: str, time_limit_minutes: int) -> dict:
        if not 1 <= time_limit_minutes <= 10:
            raise ServiceError("invalid_time_limit", "O limite deve estar entre 1 e 10 minutos.")
        with self.store.transaction() as tx:
            disease = tx.get_case(case_id)
            if disease is None:
                raise ServiceError("case_not_found", "Caso clínico não encontrado.", 404)
            case = deepcopy(disease)
            if case.optional_symptoms:
                case.symptoms.append(choice(case.optional_symptoms))
                case.optional_symptoms = []
            if case.name.startswith("Febre e dor de cabeça"):
                case.name = "Quadro febril - caso introdutório"
            simulation = Simulation(case, Patient("Paciente virtual", deepcopy(case.initial_vital_signs), deepcopy(case.symptoms)), time_limit_minutes)
            simulation.start()
            saved = SavedSimulation(simulation, owner_id, case_id, 1, self.clock.now())
            tx.create_simulation(saved)
        return self._view(saved)

    def list(self, owner_id: str, limit: int, offset: int) -> list[dict]:
        with self.store.transaction() as tx:
            saved_items = tx.list_simulations(owner_id, limit, offset)
            for saved in saved_items:
                self._reconcile(saved)
                if saved.clock_changed:
                    tx.save_simulation(saved)
        return [{"id": item.simulation.id, "is_running": item.simulation.is_running,
                 "elapsed_time_minutes": item.simulation.elapsed_time_minutes,
                 "time_limit_minutes": item.simulation.time_limit_minutes} for item in saved_items]

    def get(self, owner_id: str, simulation_id: str) -> dict:
        with self.store.transaction() as tx:
            saved = self._load(tx, owner_id, simulation_id)
            self._reconcile(saved)
            if saved.clock_changed:
                tx.save_simulation(saved)
            return self._view(saved)

    def result(self, owner_id: str, simulation_id: str) -> dict:
        state = self.get(owner_id, simulation_id)
        if state["result"] is None:
            raise ServiceError("not_finished", "A simulação ainda está em andamento.", 409)
        return state["result"]

    def advance(self, owner_id: str, simulation_id: str, seconds: int) -> dict:
        if not 1 <= seconds <= 600:
            raise ServiceError("invalid_seconds", "O avanço deve estar entre 1 e 600 segundos.")
        self.get(owner_id, simulation_id)
        with self.store.transaction() as tx:
            saved = self._load(tx, owner_id, simulation_id)
            self._require_running(saved.simulation)
            self._advance_seconds_until_end(saved.simulation, seconds)
            tx.save_simulation(saved)
            return self._view(saved)

    def reveal(self, owner_id: str, simulation_id: str, symptom_name: str) -> dict:
        self.get(owner_id, simulation_id)
        with self.store.transaction() as tx:
            saved = self._load(tx, owner_id, simulation_id)
            self._require_running(saved.simulation)
            symptom = saved.simulation.patient.find_symptom(symptom_name)
            if symptom is None or not symptom.is_visible or not symptom.is_active():
                raise ServiceError("symptom_not_found", "Sintoma não encontrado.", 404)
            try:
                level, content, has_next = saved.simulation.reveal_next_protocol_content(symptom_name)
            except ValueError as error:
                raise ServiceError("protocol_complete", str(error), 409) from error
            tx.save_simulation(saved)
            return {"symptom_name": symptom_name, "level": level, "content": content, "has_next_level": has_next}

    async def interact(self, owner_id: str, simulation_id: str, student_text: str, symptom_name: str) -> dict:
        if not student_text.strip() or len(student_text) > 2000:
            raise ServiceError("invalid_text", "A mensagem deve ter entre 1 e 2000 caracteres.")
        self.get(owner_id, simulation_id)
        with self.store.transaction() as tx:
            saved = self._load(tx, owner_id, simulation_id)
            self._require_running(saved.simulation)
            symptom = saved.simulation.patient.find_symptom(symptom_name)
            if symptom is None or not symptom.is_visible or not symptom.is_active():
                raise ServiceError("symptom_not_found", "Sintoma não encontrado.", 404)
            self._reject_repeated_conduct(saved.simulation, student_text)
            snapshot = saved.simulation
        evaluation = await self.evaluator.evaluate(snapshot, student_text, symptom_name)
        return self._commit_interaction(owner_id, simulation_id, snapshot, student_text, symptom_name, evaluation)

    async def interact_stream(self, owner_id: str, simulation_id: str, student_text: str, symptom_name: str) -> AsyncIterator[tuple[str, dict]]:
        if not student_text.strip() or len(student_text) > 2000:
            raise ServiceError("invalid_text", "A mensagem deve ter entre 1 e 2000 caracteres.")
        self.get(owner_id, simulation_id)
        with self.store.transaction() as tx:
            saved = self._load(tx, owner_id, simulation_id)
            self._require_running(saved.simulation)
            symptom = saved.simulation.patient.find_symptom(symptom_name)
            if symptom is None or not symptom.is_visible or not symptom.is_active():
                raise ServiceError("symptom_not_found", "Sintoma não encontrado.", 404)
            self._reject_repeated_conduct(saved.simulation, student_text)
            snapshot = saved.simulation
        if hasattr(self.evaluator, "evaluate_stream"):
            async for kind, value in self.evaluator.evaluate_stream(snapshot, student_text, symptom_name):
                if kind == "preview":
                    yield "preview", {"text": value}
                else:
                    result = self._commit_interaction(owner_id, simulation_id, snapshot, student_text, symptom_name, value)
                    yield "complete", result
        else:
            evaluation = await self.evaluator.evaluate(snapshot, student_text, symptom_name)
            yield "complete", self._commit_interaction(owner_id, simulation_id, snapshot, student_text, symptom_name, evaluation)

    def _commit_interaction(self, owner_id, simulation_id, snapshot, student_text, symptom_name, evaluation):
        with self.store.transaction() as tx:
            saved = self._load(tx, owner_id, simulation_id)
            # Clock refreshes may advance the row version while Gemini responds.
            # Only a competing interaction invalidates this evaluation snapshot.
            if len(saved.simulation.interactions) != len(snapshot.interactions):
                raise ServiceError("stale_simulation", "Outra interação foi registrada. Revise o quadro e tente novamente.", 409)
            self._reconcile(saved)
            self._require_running(saved.simulation)
            symptom = saved.simulation.patient.find_symptom(symptom_name)
            if symptom is None or not symptom.is_visible or not symptom.is_active():
                raise ServiceError("symptom_not_found", "Sintoma não encontrado ou já abordado.", 409)
            revealed = [name for name in evaluation.revealed_symptoms
                        if (discovered := saved.simulation.patient.find_symptom(name)) and not discovered.is_visible]
            classification = (
                InteractionClassification.ASSESSMENT
                if is_assessment_only(student_text)
                else InteractionClassification.CORRECT
                if self._matches_expected_conduct(student_text, symptom.protocol.expected_response)
                else evaluation.classification
            )
            interaction = saved.simulation.register_interaction(
                student_text.strip(), evaluation.patient_response, classification, symptom_name,
                input_tokens=evaluation.input_tokens, output_tokens=evaluation.output_tokens,
                revealed_symptoms=revealed,
            )
            if saved.simulation.patient.has_critical_aggravation():
                self._finish(saved.simulation, "Agravamento crítico")
            elif saved.simulation.all_symptoms_addressed():
                self._finish(saved.simulation, "Atendimento bem-sucedido")
            tx.save_simulation(saved)
            return {"interaction_id": interaction.id, "simulation": self._view(saved)}

    @staticmethod
    def _matches_expected_conduct(student_text: str, expected_response: str) -> bool:
        """An exact level-3 answer must not be downgraded by a variable evaluator."""
        answer = re.sub(r"^\s*3\s*[.)]\s*", "", student_text)

        def words(value: str) -> list[str]:
            plain = unicodedata.normalize("NFKD", value.casefold())
            plain = "".join(char for char in plain if not unicodedata.combining(char))
            return re.findall(r"[a-z0-9]+", plain)

        return bool(words(answer)) and words(answer) == words(expected_response)

    @staticmethod
    def _reject_repeated_conduct(simulation: Simulation, student_text: str) -> None:
        normalized = " ".join(student_text.casefold().split())
        if any(" ".join(item.student_text.casefold().split()) == normalized
               for item in simulation.interactions):
            raise ServiceError("duplicate_conduct", "Essa mensagem já foi enviada. Descreva a conduta para a queixa atual.", 409)

    def finish(self, owner_id: str, simulation_id: str) -> dict:
        self.get(owner_id, simulation_id)
        with self.store.transaction() as tx:
            saved = self._load(tx, owner_id, simulation_id)
            self._require_running(saved.simulation)
            self._finish(saved.simulation, "Atendimento concluído")
            tx.save_simulation(saved)
            return self._view(saved)

    def _view(self, saved: SavedSimulation) -> dict:
        remaining = 0
        if saved.simulation.is_running:
            whole_minutes = saved.simulation.time_limit_minutes - saved.simulation.elapsed_time_seconds / 60
            elapsed_since_checkpoint = max(0.0, (self.clock.now() - saved.checkpoint).total_seconds())
            remaining = max(0, ceil(whole_minutes * 60 - elapsed_since_checkpoint))
        return simulation_view(saved.simulation, remaining)

    @staticmethod
    def _load(tx, owner_id: str, simulation_id: str) -> SavedSimulation:
        saved = tx.get_simulation(simulation_id, owner_id)
        if saved is None:
            raise ServiceError("simulation_not_found", "Simulação não encontrada.", 404)
        return saved

    @staticmethod
    def _require_running(simulation: Simulation) -> None:
        if not simulation.is_running:
            raise ServiceError("already_finished", "A simulação já foi encerrada.", 409)

    def _reconcile(self, saved: SavedSimulation) -> None:
        now = self.clock.now()
        seconds = max(0, int((now - saved.checkpoint).total_seconds()))
        saved.clock_changed = False
        if seconds and saved.simulation.is_running:
            self._advance_seconds_until_end(saved.simulation, seconds)
            saved.checkpoint += timedelta(seconds=seconds)
            saved.clock_changed = True

    def _advance_seconds_until_end(self, simulation: Simulation, seconds: int) -> None:
        for _ in range(min(seconds, simulation.time_limit_minutes * 60 - simulation.elapsed_time_seconds)):
            simulation.advance_seconds(1)
            if simulation.patient.has_critical_aggravation():
                self._finish(simulation, "Agravamento crítico")
                break
            if simulation.has_time_expired():
                self._finish(simulation, "Tempo esgotado")
                break

    @staticmethod
    def _finish(simulation: Simulation, outcome: str) -> None:
        correct = sum(item.classification.value == "correct" for item in simulation.interactions)
        partial = sum(item.classification.value == "partially_correct" for item in simulation.interactions)
        if outcome == "Atendimento bem-sucedido":
            for symptom in simulation.patient.symptoms:
                symptom.state = SymptomState.INACTIVE
                symptom.intensity = 0
            for vital in simulation.patient.vital_signs:
                vital.value = next((item.value for item in simulation.disease.initial_vital_signs
                                    if item.name == vital.name), vital.value)
            evolution = "Queixas abordadas e sinais estabilizados nesta simulação."
        else:
            evolution = "Sintomas ativos: " + (", ".join(item.name for item in simulation.patient.symptoms if item.is_active()) or "nenhum")
        feedback = f"{correct} conduta(s) adequadas e {partial} parcialmente adequadas em {simulation.elapsed_time_minutes} minuto(s)."
        simulation.end(evolution, outcome, feedback)
