"""Small implementation of the storage port; no SQLite file or API server."""

from contextlib import contextmanager
from copy import deepcopy

from ports.errors import ServiceError


class MemoryStore:
    def __init__(self, cases=None):
        self.cases = dict(cases or {})
        self.users = {}
        self.tokens = {}
        self.simulations = {}
        self.reports = []
        self.feedbacks = {}

    @contextmanager
    def transaction(self):
        yield self

    def list_cases(self):
        return list(self.cases.items())

    def get_case(self, case_id):
        return self.cases.get(case_id)

    def create_user(self, user_id, email, password_hash, name=None):
        if any(user[0] == email for user in self.users.values()):
            raise ServiceError("email_taken", "Este email já está cadastrado.", 409)
        self.users[user_id] = (email, password_hash, name)

    def get_user_by_email(self, email):
        return next(
            (
                (user_id, password_hash)
                for user_id, (address, password_hash, _) in self.users.items()
                if address == email
            ),
            None,
        )

    def get_user(self, user_id):
        user = self.users.get(user_id)
        return {"email": user[0], "name": user[2] or "Estudante"} if user else None

    def create_token(self, token_hash, user_id, expires_at):
        self.tokens[token_hash] = (user_id, expires_at)

    def get_token_owner(self, token_hash, now):
        token = self.tokens.get(token_hash)
        return token[0] if token and token[1] > now and self.get_user(token[0]) else None

    def delete_token(self, token_hash):
        self.tokens.pop(token_hash, None)

    def create_simulation(self, saved):
        self.simulations[saved.simulation.id] = deepcopy(saved)

    def get_simulation(self, simulation_id, owner_id):
        saved = self.simulations.get(simulation_id)
        return deepcopy(saved) if saved and saved.owner_id == owner_id else None

    def list_simulations(self, owner_id, limit, offset):
        owned = [deepcopy(saved) for saved in self.simulations.values() if saved.owner_id == owner_id]
        return owned[offset:offset + limit]

    def save_simulation(self, saved):
        current = self.simulations[saved.simulation.id]
        if current.version != saved.version:
            raise ServiceError("stale_simulation", "A simulação foi alterada por outra requisição.", 409)
        saved.version += 1
        self.simulations[saved.simulation.id] = deepcopy(saved)

    def create_report(self, report_id, simulation_id, interaction_id, description, response, context):
        self.reports.append({
            "id": report_id,
            "simulation_id": simulation_id,
            "interaction_id": interaction_id,
            "description": description,
            "response": response,
            "context": context,
        })

    def get_experience_feedback(self, simulation_id):
        return deepcopy(self.feedbacks.get(simulation_id))

    def create_experience_feedback(self, simulation_id, data):
        self.feedbacks[simulation_id] = deepcopy(data)

    def update_experience_feedback(self, simulation_id, data):
        if simulation_id not in self.feedbacks:
            return False
        self.feedbacks[simulation_id] = deepcopy(data)
        return True
