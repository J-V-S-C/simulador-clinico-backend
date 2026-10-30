"""Environment configured administrator and read-only review use cases."""

import hashlib
import secrets
from datetime import timedelta

from ports.errors import ServiceError


class AdminService:
    def __init__(self, store, clock, username: str, password: str):
        self.store = store
        self.clock = clock
        self.username = username
        self.password = password

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def login(self, username: str, password: str) -> dict:
        if (not self.username or not self.password or
                not secrets.compare_digest(username, self.username) or
                not secrets.compare_digest(password, self.password)):
            raise ServiceError("invalid_credentials", "Credenciais inválidas.", 401)
        raw = secrets.token_urlsafe(32)
        with self.store.transaction() as tx:
            tx.create_admin_token(self._digest(raw), self.clock.now() + timedelta(hours=8))
        return {"access_token": raw, "token_type": "bearer", "expires_in": 28800}

    def authenticate(self, token: str) -> None:
        if not self.username or not self.password:
            raise ServiceError("unauthorized", "Autenticação necessária.", 401)
        with self.store.transaction() as tx:
            valid = tx.has_admin_token(self._digest(token), self.clock.now())
        if not valid:
            raise ServiceError("unauthorized", "Autenticação necessária.", 401)

    def logout(self, token: str) -> None:
        with self.store.transaction() as tx:
            tx.delete_admin_token(self._digest(token))

    def accounts(self) -> list[dict]:
        with self.store.transaction() as tx:
            return tx.list_admin_accounts()

    def feedback(self) -> list[dict]:
        with self.store.transaction() as tx:
            return tx.list_admin_feedback()
