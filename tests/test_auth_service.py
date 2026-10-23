"""AuthService unit tests: registration, credentials, token lifetime, and revocation."""

import hashlib

import pytest

from ports.errors import ServiceError
from services.auth import AuthService


PASSWORD = "a-long-test-password"


def test_register_normalizes_email_and_stores_password_hash(store, clock):
    auth = AuthService(store, clock)

    user = auth.register("  Student@Example.com  ", PASSWORD)

    assert user["email"] == "student@example.com"
    assert store.users[user["id"]][0] == user["email"]
    assert store.users[user["id"]][1] != PASSWORD


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_register_rejects_invalid_password(store, clock, password):
    auth = AuthService(store, clock)

    with pytest.raises(ServiceError) as error:
        auth.register("student@example.com", password)

    assert error.value.code == "invalid_password"
    assert store.users == {}


def test_register_accepts_eight_character_password(store, clock):
    user = AuthService(store, clock).register("student@example.com", "12345678")
    assert user["email"] == "student@example.com"


def test_register_normalizes_email_before_uniqueness_check(store, clock):
    auth = AuthService(store, clock)
    auth.register("student@example.com", PASSWORD)

    with pytest.raises(ServiceError) as error:
        auth.register("STUDENT@example.com", PASSWORD)

    assert error.value.code == "email_taken"
    assert len(store.users) == 1


def test_login_creates_hashed_token_and_returns_identity(store, clock):
    auth = AuthService(store, clock)
    user = auth.register("student@example.com", PASSWORD)

    login = auth.login(" STUDENT@example.com ", PASSWORD)
    token = login["access_token"]

    assert login["token_type"] == "bearer"
    assert login["expires_in"] == 8 * 60 * 60
    assert token not in store.tokens
    assert hashlib.sha256(token.encode()).hexdigest() in store.tokens
    assert auth.authenticate(token) == user["id"]
    assert auth.me(user["id"]) == user


def test_logout_revokes_token(store, clock):
    auth = AuthService(store, clock)
    auth.register("student@example.com", PASSWORD)
    token = auth.login("student@example.com", PASSWORD)["access_token"]

    auth.logout(token)

    with pytest.raises(ServiceError) as error:
        auth.authenticate(token)
    assert error.value.code == "unauthorized"


@pytest.mark.parametrize("email,password", [
    ("missing@example.com", PASSWORD),
    ("student@example.com", "wrong-password"),
])
def test_login_rejects_invalid_credentials(store, clock, email, password):
    auth = AuthService(store, clock)
    auth.register("student@example.com", PASSWORD)

    with pytest.raises(ServiceError) as error:
        auth.login(email, password)

    assert error.value.code == "invalid_credentials"
    assert store.tokens == {}


def test_token_expires_after_eight_hours(store, clock):
    auth = AuthService(store, clock)
    auth.register("student@example.com", PASSWORD)
    token = auth.login("student@example.com", PASSWORD)["access_token"]

    clock.advance(8 * 60)

    with pytest.raises(ServiceError) as error:
        auth.authenticate(token)
    assert error.value.code == "unauthorized"


def test_me_rejects_unknown_user(store, clock):
    with pytest.raises(ServiceError) as error:
        AuthService(store, clock).me("unknown")
    assert error.value.code == "unauthorized"
