"""CaseService unit tests: student-facing metadata and missing cases."""

import pytest

from ports.errors import ServiceError
from services.cases import CaseService


def test_list_cases_hides_diagnoses(store, case):
    store.cases["case-2"] = case

    listed = CaseService(store).list_cases()

    assert listed == [
        {"id": "case-1", "title": "Paciente com falta de ar e cansaço"},
        {"id": "case-2", "title": "Paciente com falta de ar e cansaço"},
    ]
    assert case.name not in str(listed)


def test_get_case_returns_setup_limits(store):
    detail = CaseService(store).get_case("case-1")

    assert detail == {
        "id": "case-1",
        "title": "Paciente com falta de ar e cansaço",
        "default_time_limit_minutes": 5,
        "max_time_limit_minutes": 10,
    }


def test_missing_case_returns_not_found(store):
    with pytest.raises(ServiceError) as error:
        CaseService(store).get_case("missing")

    assert error.value.code == "case_not_found"
    assert error.value.status == 404


def test_empty_catalog_returns_empty_list(store):
    store.cases.clear()

    assert CaseService(store).list_cases() == []
