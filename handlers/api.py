from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth import AuthService
from services.admin import AdminService
from services.cases import CaseService
from ports.errors import ServiceError
from services.reports import ReportService
from services.simulations import SimulationService


bearer_scheme = HTTPBearer(auto_error=False)


async def require_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if credentials is None or not credentials.credentials:
        raise ServiceError("unauthorized", "Autenticação necessária.", 401)
    return credentials.credentials


class ApiHandlers:
    def __init__(self, auth: AuthService, cases: CaseService, simulations: SimulationService, reports: ReportService, admin: AdminService | None = None):
        self.auth = auth
        self.cases = cases
        self.simulations = simulations
        self.reports = reports
        self.admin = admin

    async def administrator(self, token: str = Depends(require_token)) -> str:
        if self.admin is None:
            raise ServiceError("unauthorized", "Autenticação necessária.", 401)
        self.admin.authenticate(token)
        return token

    async def owner(self, token: str = Depends(require_token)) -> str:
        return self.auth.authenticate(token)

    def health(self) -> dict:
        with self.cases.store.transaction() as tx:
            tx.list_cases()
        return {"status": "ok"}

    def register(self, email: str, password: str, name: str) -> dict:
        return self.auth.register(email, password, name)

    def login(self, email: str, password: str) -> dict:
        return self.auth.login(email, password)

    def logout(self, token: str) -> None:
        self.auth.logout(token)

    def me(self, user_id: str) -> dict:
        return self.auth.me(user_id)

    def list_cases(self) -> list[dict]:
        return self.cases.list_cases()

    def get_case(self, case_id: str) -> dict:
        return self.cases.get_case(case_id)

    def start(self, user_id: str, case_id: str, minutes: int) -> dict:
        return self.simulations.start(user_id, case_id, minutes)

    def list_simulations(self, user_id: str, limit: int, offset: int) -> list[dict]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ServiceError("invalid_pagination", "Paginação inválida.")
        return self.simulations.list(user_id, limit, offset)

    def get_simulation(self, user_id: str, simulation_id: str) -> dict:
        return self.simulations.get(user_id, simulation_id)

    async def interact(self, user_id: str, simulation_id: str, text: str, symptom_name: str) -> dict:
        return await self.simulations.interact(user_id, simulation_id, text, symptom_name)

    def interact_stream(self, user_id: str, simulation_id: str, text: str, symptom_name: str):
        return self.simulations.interact_stream(user_id, simulation_id, text, symptom_name)

    def advance(self, user_id: str, simulation_id: str, seconds: int) -> dict:
        return self.simulations.advance(user_id, simulation_id, seconds)

    def reveal(self, user_id: str, simulation_id: str, symptom_name: str) -> dict:
        return self.simulations.reveal(user_id, simulation_id, symptom_name)

    def report(self, user_id: str, simulation_id: str, interaction_id: str, description: str) -> dict:
        return self.reports.create(user_id, simulation_id, interaction_id, description)

    def finish(self, user_id: str, simulation_id: str) -> dict:
        return self.simulations.finish(user_id, simulation_id)

    def result(self, user_id: str, simulation_id: str) -> dict:
        return self.simulations.result(user_id, simulation_id)

    def feedback(self, user_id: str, simulation_id: str):
        with self.simulations.store.transaction() as tx:
            saved = tx.get_simulation(simulation_id, user_id)
            if saved is None:
                raise ServiceError("simulation_not_found", "Simulação não encontrada.", 404)
            return tx.get_experience_feedback(simulation_id)

    def submit_feedback(self, user_id: str, simulation_id: str, data: dict):
        with self.simulations.store.transaction() as tx:
            saved = tx.get_simulation(simulation_id, user_id)
            if saved is None:
                raise ServiceError("simulation_not_found", "Simulação não encontrada.", 404)
            if saved.simulation.result is None:
                raise ServiceError("simulation_running", "Finalize a simulação antes de avaliar.", 409)
            if tx.get_experience_feedback(simulation_id) is not None:
                raise ServiceError("feedback_exists", "Este atendimento já foi avaliado.", 409)
            tx.create_experience_feedback(simulation_id, data)
        return data

    def update_feedback(self, user_id: str, simulation_id: str, data: dict):
        with self.simulations.store.transaction() as tx:
            if tx.get_simulation(simulation_id, user_id) is None:
                raise ServiceError("simulation_not_found", "Simulação não encontrada.", 404)
            if not tx.update_experience_feedback(simulation_id, data):
                raise ServiceError("feedback_not_found", "Avaliação não encontrada.", 404)
        return data

