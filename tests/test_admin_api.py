"""Admin sessions are separate from student sessions and expose review data only."""

import asyncio

from httpx import ASGITransport, AsyncClient

from config import Settings
from repositories.database import create_session_factory
from repositories.store import SqlStore, seed_public_cases
from fakes import FakeClock, FakeEvaluator


def test_admin_can_review_accounts_and_feedback_but_student_cannot(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'import.db'}")
    from server import create_app
    factory = create_session_factory(f"sqlite:///{tmp_path / 'admin.db'}")
    seed_public_cases(factory)
    app = create_app(
        Settings(admin_username="admin123", admin_password="long-test-admin-password"),
        evaluator=FakeEvaluator(), clock=FakeClock(), store=SqlStore(factory),
    )

    async def scenario():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            student = await client.post("/api/auth/register", json={"name": "Ana", "email": "ana@example.com", "password": "student-password"})
            assert student.status_code == 201
            student_token = (await client.post("/api/auth/login", json={"email": "ana@example.com", "password": "student-password"})).json()["access_token"]
            student_headers = {"Authorization": f"Bearer {student_token}"}
            case_id = (await client.get("/api/cases", headers=student_headers)).json()[0]["id"]
            started = await client.post("/api/simulations", headers=student_headers, json={"case_id": case_id, "time_limit_minutes": 5})
            assert started.status_code == 201
            simulation_id = started.json()["id"]
            assert (await client.post(f"/api/simulations/{simulation_id}/finish", headers=student_headers)).status_code == 200
            review = {"liked": True, "clarity": 4, "difficulty": 2, "useful_feature": "Protocolos", "improvement": "Mais casos"}
            assert (await client.post(f"/api/simulations/{simulation_id}/experience-feedback", headers=student_headers, json=review)).status_code == 201

            assert (await client.get("/api/admin/accounts", headers=student_headers)).status_code == 401
            assert (await client.get("/api/admin/feedback", headers=student_headers)).status_code == 401
            assert (await client.post("/api/admin/login", json={"username": "admin123", "password": "wrong"})).status_code == 401
            admin = await client.post("/api/admin/login", json={"username": "admin123", "password": "long-test-admin-password"})
            assert admin.status_code == 200
            admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}
            assert (await client.get("/api/auth/me", headers=admin_headers)).status_code == 401
            accounts = await client.get("/api/admin/accounts", headers=admin_headers)
            assert accounts.status_code == 200
            assert accounts.json() == [student.json()]
            feedback = await client.get("/api/admin/feedback", headers=admin_headers)
            assert feedback.status_code == 200
            assert len(feedback.json()) == 1
            assert feedback.json()[0]["user_email"] == "ana@example.com"
            assert feedback.json()[0]["simulation_id"] == simulation_id
            assert feedback.json()[0]["improvement"] == "Mais casos"
            assert (await client.post("/api/admin/logout", headers=admin_headers)).status_code == 204
            assert (await client.get("/api/admin/accounts", headers=admin_headers)).status_code == 401

    asyncio.run(scenario())
