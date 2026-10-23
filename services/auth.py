"""Student registration and revocable bearer sessions."""

import hashlib
import secrets
from datetime import timedelta
from uuid import uuid4

from pwdlib import PasswordHash

from ports.clock import Clock
from ports.storage import Store
from ports.errors import ServiceError


class AuthService:
    def __init__(self, store: Store, clock: Clock, password_hash: PasswordHash | None = None):
        self.store = store
        self.clock = clock
        self.password_hash = password_hash or PasswordHash.recommended()

    def register(self, email: str, password: str, name: str = "Estudante") -> dict:
        email = email.strip().lower()
        name = " ".join(name.split())
        if not 2 <= len(name) <= 100:
            raise ServiceError("invalid_name", "O nome deve ter entre 2 e 100 caracteres.")
        if len(password) < 8 or len(password) > 128:
            raise ServiceError("invalid_password", "A senha deve ter entre 8 e 128 caracteres.")
        user_id = str(uuid4())
        with self.store.transaction() as tx:
            tx.create_user(user_id, email, self.password_hash.hash(password), name)
        return {"id": user_id, "email": email, "name": name}

    def login(self, email: str, password: str) -> dict:
        with self.store.transaction() as tx:
            found = tx.get_user_by_email(email.strip().lower())
            if not found or not self.password_hash.verify(password, found[1]):
                raise ServiceError("invalid_credentials", "Credenciais inválidas.", 401)
            raw = secrets.token_urlsafe(32)
            tx.create_token(self._digest(raw), found[0], self.clock.now() + timedelta(hours=8))
            return {"access_token": raw, "token_type": "bearer", "expires_in": 28800}

    def authenticate(self, token: str) -> str:
        with self.store.transaction() as tx:
            owner_id = tx.get_token_owner(self._digest(token), self.clock.now())
        if owner_id is None:
            raise ServiceError("unauthorized", "Autenticação necessária.", 401)
        return owner_id

    def me(self, user_id: str) -> dict:
        with self.store.transaction() as tx:
            user = tx.get_user(user_id)
        if user is None:
            raise ServiceError("unauthorized", "Autenticação necessária.", 401)
        return {"id": user_id, **user}

    def logout(self, token: str) -> None:
        with self.store.transaction() as tx:
            tx.delete_token(self._digest(token))

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
