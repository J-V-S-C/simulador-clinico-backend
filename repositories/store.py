"""SQLAlchemy implementation of service persistence ports."""

import csv
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ports.storage import SavedSimulation
from repositories.database import CaseRow, ExperienceFeedbackRow, ReportRow, SimulationRow, TokenRow, UserRow
from repositories.serialization import disease_from_dictionary, disease_to_dictionary, simulation_from_dictionary, simulation_to_dictionary
from ports.errors import ServiceError


LEGACY_USER_ID = str(uuid5(NAMESPACE_URL, "clinical-simulator:legacy-user"))


def case_id_for_name(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"clinical-simulator:case:{name}"))


class SqlTransaction:
    def __init__(self, db: Session):
        self.db = db

    def list_cases(self):
        rows = self.db.scalars(select(CaseRow).order_by(CaseRow.name)).all()
        return [(row.id, disease_from_dictionary(row.payload)) for row in rows]

    def get_case(self, case_id):
        row = self.db.get(CaseRow, case_id)
        return disease_from_dictionary(row.payload) if row else None

    def create_user(self, user_id, email, password_hash, name=None):
        self.db.add(UserRow(id=user_id, email=email, password_hash=password_hash, name=name))
        try:
            self.db.flush()
        except IntegrityError as error:
            raise ServiceError("email_taken", "Este email já está cadastrado.", 409) from error

    def get_user_by_email(self, email):
        row = self.db.scalar(select(UserRow).where(UserRow.email == email, UserRow.disabled.is_(False)))
        return (row.id, row.password_hash) if row else None

    def get_user(self, user_id):
        row = self.db.get(UserRow, user_id)
        return {"email": row.email, "name": row.name or "Estudante"} if row and not row.disabled else None

    def create_token(self, token_hash, user_id, expires_at):
        self.db.add(TokenRow(hash=token_hash, owner_id=user_id, expires_at=expires_at))

    def get_token_owner(self, token_hash, now):
        row = self.db.get(TokenRow, token_hash)
        if not row:
            return None
        expiry = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
        return row.owner_id if expiry > now and self.get_user(row.owner_id) else None

    def delete_token(self, token_hash):
        row = self.db.get(TokenRow, token_hash)
        if row:
            self.db.delete(row)

    @staticmethod
    def _saved(row):
        checkpoint = row.clock_checkpoint.replace(tzinfo=timezone.utc) if row.clock_checkpoint.tzinfo is None else row.clock_checkpoint
        return SavedSimulation(simulation_from_dictionary(row.payload), row.owner_id, row.case_id, row.version, checkpoint)

    def create_simulation(self, saved):
        self.db.add(SimulationRow(
            id=saved.simulation.id, owner_id=saved.owner_id, case_id=saved.case_id,
            payload=simulation_to_dictionary(saved.simulation), version=1,
            clock_checkpoint=saved.checkpoint,
        ))

    def get_simulation(self, simulation_id, owner_id):
        row = self.db.scalar(select(SimulationRow).where(SimulationRow.id == simulation_id, SimulationRow.owner_id == owner_id))
        return self._saved(row) if row else None

    def list_simulations(self, owner_id, limit, offset):
        rows = self.db.scalars(select(SimulationRow).where(SimulationRow.owner_id == owner_id).order_by(SimulationRow.id).limit(limit).offset(offset)).all()
        return [self._saved(row) for row in rows]

    def save_simulation(self, saved):
        result = self.db.execute(
            update(SimulationRow)
            .where(SimulationRow.id == saved.simulation.id, SimulationRow.owner_id == saved.owner_id, SimulationRow.version == saved.version)
            .values(payload=simulation_to_dictionary(saved.simulation), clock_checkpoint=saved.checkpoint, version=saved.version + 1)
        )
        if result.rowcount != 1:
            raise ServiceError("stale_simulation", "A simulação foi alterada por outra requisição.", 409)
        saved.version += 1

    def create_report(self, report_id, simulation_id, interaction_id, description, response, context):
        self.db.add(ReportRow(
            id=report_id, simulation_id=simulation_id, interaction_id=interaction_id,
            description=description, response=response, context=context,
        ))

    def get_experience_feedback(self, simulation_id):
        row = self.db.get(ExperienceFeedbackRow, simulation_id)
        if row is None:
            return None
        return {"liked": row.liked, "clarity": row.clarity, "difficulty": row.difficulty,
                "useful_feature": row.useful_feature, "improvement": row.improvement}

    def create_experience_feedback(self, simulation_id, data):
        self.db.add(ExperienceFeedbackRow(simulation_id=simulation_id, **data))

    def update_experience_feedback(self, simulation_id, data):
        row = self.db.get(ExperienceFeedbackRow, simulation_id)
        if row is None:
            return False
        for key, value in data.items():
            setattr(row, key, value)
        return True


class SqlStore:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    @contextmanager
    def transaction(self):
        with self.session_factory.begin() as db:
            yield SqlTransaction(db)


def import_legacy_csv(session_factory: sessionmaker[Session], data_dir: Path) -> None:
    """Idempotently preserve old cases and simulations under a disabled archive owner."""
    diseases_path = data_dir / "diseases.csv"
    if not diseases_path.exists():
        return
    with session_factory.begin() as db:
        from sample_data import create_beginner_case
        beginner = create_beginner_case()
        beginner_id = case_id_for_name(beginner.name)
        if db.get(CaseRow, beginner_id) is None:
            db.add(CaseRow(id=beginner_id, name=beginner.name, payload=disease_to_dictionary(beginner)))
        if db.get(UserRow, LEGACY_USER_ID) is None:
            db.add(UserRow(id=LEGACY_USER_ID, email="legacy@archive.invalid", password_hash="!", disabled=True))
        with diseases_path.open(newline="", encoding="utf-8") as file:
            for item in csv.DictReader(file):
                payload = json.loads(item["payload"])
                # New attempts use visible progression; old attempts keep their saved snapshot.
                for symptom in payload.get("symptoms", []):
                    symptom["natural_evolution_per_minute"] = 0.5
                    symptom["vital_sign_changes_per_minute"] = {
                        name: (1.2 if value > 0 else -0.45)
                        for name, value in symptom.get("vital_sign_changes_per_minute", {}).items()
                    }
                name = str(payload["name"])
                case_id = case_id_for_name(name)
                existing = db.get(CaseRow, case_id)
                if existing is None:
                    db.add(CaseRow(id=case_id, name=name, payload=payload))
                else:
                    existing.payload = payload
        db.flush()
        simulations_path = data_dir / "simulations.csv"
        if simulations_path.exists():
            with simulations_path.open(newline="", encoding="utf-8") as file:
                for item in csv.DictReader(file):
                    payload = json.loads(item["payload"])
                    simulation_id = str(payload["id"])
                    if db.get(SimulationRow, simulation_id) is None:
                        name = str(payload["disease"]["name"])
                        case_id = case_id_for_name(name)
                        if db.get(CaseRow, case_id) is None:
                            db.add(CaseRow(id=case_id, name=name, payload=payload["disease"]))
                            db.flush()
                        db.add(SimulationRow(
                            id=simulation_id, owner_id=LEGACY_USER_ID,
                            case_id=case_id, payload=payload,
                            version=1, clock_checkpoint=datetime.now(timezone.utc),
                        ))
        db.flush()
        reports_path = data_dir / "reports.csv"
        if reports_path.exists():
            with reports_path.open(newline="", encoding="utf-8") as file:
                for index, item in enumerate(csv.DictReader(file)):
                    simulation_id = item["simulation_id"]
                    report_id = str(uuid5(NAMESPACE_URL, f"clinical-simulator:legacy-report:{index}:{simulation_id}"))
                    if db.get(SimulationRow, simulation_id) and db.get(ReportRow, report_id) is None:
                        db.add(ReportRow(
                            id=report_id, simulation_id=simulation_id, interaction_id="legacy",
                            description=item.get("description", ""), response=item.get("ai_response", ""),
                            context=item.get("simulation_context", ""),
                        ))


def seed_public_cases(session_factory: sessionmaker[Session]) -> None:
    """Refresh built-in case templates without changing existing attempts."""
    from sample_data import create_public_cases

    with session_factory.begin() as db:
        for case in create_public_cases():
            case_id = case_id_for_name(case.name)
            payload = disease_to_dictionary(case)
            row = db.get(CaseRow, case_id)
            if row is None:
                db.add(CaseRow(id=case_id, name=case.name, payload=payload))
            else:
                row.payload = payload
