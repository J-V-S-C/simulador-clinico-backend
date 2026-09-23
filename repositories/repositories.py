"""Repositórios persistidos em arquivos CSV com Pandas."""

import json
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from models import Disease, Report, Simulation
from repositories.serialization import (
    disease_from_dictionary,
    disease_to_dictionary,
    simulation_from_dictionary,
    simulation_to_dictionary,
)


DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "data"


def read_csv_file(file_path: Path, columns: list[str]) -> pd.DataFrame:
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    return pd.read_csv(file_path, dtype=str, keep_default_na=False)


def save_csv_file(data_frame: pd.DataFrame, file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    data_frame.to_csv(file_path, index=False)


class DiseaseRepository:
    """Persiste os casos clínicos em `data/diseases.csv`."""

    def __init__(
        self,
        diseases: Optional[Iterable[Disease]] = None,
        file_path: Path = DATA_DIRECTORY / "diseases.csv",
    ):
        self.file_path = file_path
        if not self.file_path.exists():
            save_csv_file(pd.DataFrame(columns=["name", "payload"]), self.file_path)
        for disease in diseases or []:
            self.save(disease)

    def list_all(self) -> List[Disease]:
        data_frame = read_csv_file(self.file_path, ["name", "payload"])
        return [
            disease_from_dictionary(json.loads(payload))
            for payload in data_frame["payload"].tolist()
        ]

    def find_by_name(self, name: str) -> Optional[Disease]:
        data_frame = read_csv_file(self.file_path, ["name", "payload"])
        matching_rows = data_frame[data_frame["name"] == name]
        if matching_rows.empty:
            return None
        return disease_from_dictionary(json.loads(matching_rows.iloc[0]["payload"]))

    def save(self, disease: Disease) -> None:
        data_frame = read_csv_file(self.file_path, ["name", "payload"])
        data_frame = data_frame[data_frame["name"] != disease.name]
        new_row = pd.DataFrame(
            [{
                "name": disease.name,
                "payload": json.dumps(
                    disease_to_dictionary(disease), ensure_ascii=False
                ),
            }]
        )
        save_csv_file(pd.concat([data_frame, new_row], ignore_index=True), self.file_path)


class SimulationRepository:
    """Persiste o estado completo das simulações em `data/simulations.csv`."""

    def __init__(self, file_path: Path = DATA_DIRECTORY / "simulations.csv"):
        self.file_path = file_path
        if not self.file_path.exists():
            save_csv_file(pd.DataFrame(columns=["id", "payload"]), self.file_path)

    def create(self, simulation: Simulation) -> None:
        if self.find_by_id(simulation.id) is not None:
            raise ValueError("Já existe uma simulação com este ID.")
        self.save_simulation(simulation)

    def update(self, simulation: Simulation) -> None:
        if self.find_by_id(simulation.id) is None:
            raise LookupError("Simulação não encontrada para atualização.")
        self.save_simulation(simulation)

    def find_by_id(self, simulation_id: str) -> Optional[Simulation]:
        data_frame = read_csv_file(self.file_path, ["id", "payload"])
        matching_rows = data_frame[data_frame["id"] == simulation_id]
        if matching_rows.empty:
            return None
        return simulation_from_dictionary(json.loads(matching_rows.iloc[0]["payload"]))

    def save_simulation(self, simulation: Simulation) -> None:
        data_frame = read_csv_file(self.file_path, ["id", "payload"])
        data_frame = data_frame[data_frame["id"] != simulation.id]
        new_row = pd.DataFrame(
            [{
                "id": simulation.id,
                "payload": json.dumps(
                    simulation_to_dictionary(simulation), ensure_ascii=False
                ),
            }]
        )
        save_csv_file(pd.concat([data_frame, new_row], ignore_index=True), self.file_path)


class ReportRepository:
    """Persiste denúncias de respostas da IA em `data/reports.csv`."""

    def __init__(self, file_path: Path = DATA_DIRECTORY / "reports.csv"):
        self.file_path = file_path
        if not self.file_path.exists():
            save_csv_file(
                pd.DataFrame(columns=[
                    "simulation_id",
                    "ai_response",
                    "simulation_context",
                    "description",
                ]),
                self.file_path,
            )

    def save(self, report: Report, simulation_id: str) -> None:
        data_frame = read_csv_file(
            self.file_path,
            ["simulation_id", "ai_response", "simulation_context", "description"],
        )
        new_row = pd.DataFrame(
            [{
                "simulation_id": simulation_id,
                "ai_response": report.ai_response,
                "simulation_context": report.simulation_context,
                "description": report.report_description,
            }]
        )
        save_csv_file(pd.concat([data_frame, new_row], ignore_index=True), self.file_path)

    def list_by_simulation_id(self, simulation_id: str) -> List[Report]:
        data_frame = read_csv_file(
            self.file_path,
            ["simulation_id", "ai_response", "simulation_context", "description"],
        )
        matching_rows = data_frame[data_frame["simulation_id"] == simulation_id]
        return [
            Report(
                ai_response=row["ai_response"],
                simulation_context=row["simulation_context"],
                report_description=row["description"],
            )
            for _, row in matching_rows.iterrows()
        ]
