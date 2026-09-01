from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base, get_db
from app.main import app
from app.models.patient import Patient


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def patient_payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "first_name": "Anne",
        "last_name": "Smith",
        "date_of_birth": "04/15/1990",
        "sex": "Female",
        "phone_number": "(212) 555-0198",
        "address_line_1": "123 Main Street",
        "city": "New York",
        "state": "ny",
        "zip_code": "10001",
    }
    data.update(overrides)
    return data


def create_patient(client: TestClient, **overrides: object) -> dict[str, object]:
    response = client.post("/patients", json=patient_payload(**overrides))
    assert response.status_code == 201
    return response.json()["data"]


def test_create_and_get_patient(client: TestClient) -> None:
    created = create_patient(client)

    response = client.get(f"/patients/{created['patient_id']}")

    assert response.status_code == 200
    assert response.json()["error"] is None
    assert response.json()["data"]["phone_number"] == "2125550198"
    assert response.json()["data"]["state"] == "NY"


def test_list_patients_supports_combined_filters(client: TestClient) -> None:
    matching = create_patient(client)
    create_patient(
        client,
        first_name="John",
        last_name="Jones",
        phone_number="6465550100",
    )

    response = client.get(
        "/patients",
        params={
            "last_name": "Smith",
            "date_of_birth": "04/15/1990",
            "phone_number": "212-555-0198",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"data": [matching], "error": None}


def test_partial_update_preserves_unsupplied_fields(client: TestClient) -> None:
    created = create_patient(client, email="old@example.com")

    response = client.put(
        f"/patients/{created['patient_id']}",
        json={"city": "Albany", "email": None},
    )

    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["city"] == "Albany"
    assert updated["email"] is None
    assert updated["first_name"] == created["first_name"]


def test_delete_soft_deletes_and_hides_patient(client: TestClient) -> None:
    created = create_patient(client)

    delete_response = client.delete(f"/patients/{created['patient_id']}")
    get_response = client.get(f"/patients/{created['patient_id']}")
    list_response = client.get("/patients")

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted_at"] is not None
    assert get_response.status_code == 404
    assert get_response.json() == {
        "data": None,
        "error": {"message": "Patient not found"},
    }
    assert list_response.json() == {"data": [], "error": None}


def test_delete_does_not_remove_database_row(client: TestClient) -> None:
    created = create_patient(client)
    client.delete(f"/patients/{created['patient_id']}")

    override = app.dependency_overrides[get_db]
    session_generator = override()
    session = next(session_generator)
    try:
        row = session.scalar(
            select(Patient).where(Patient.patient_id == UUID(str(created["patient_id"])))
        )
        assert row is not None
        assert row.deleted_at is not None
    finally:
        session_generator.close()


def test_invalid_payload_uses_error_envelope(client: TestClient) -> None:
    response = client.post("/patients", json=patient_payload(zip_code="123"))

    assert response.status_code == 422
    assert response.json() == {
        "data": None,
        "error": {"message": "Request validation failed"},
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("date_of_birth", "01/01/2999"),
        ("phone_number", "123"),
        ("state", "XX"),
        ("email", "invalid-email"),
    ],
)
def test_invalid_demographics_return_422_envelope(
    client: TestClient, field: str, value: str
) -> None:
    response = client.post("/patients", json=patient_payload(**{field: value}))

    assert response.status_code == 422
    assert response.json()["data"] is None
    assert response.json()["error"]["message"] == "Request validation failed"


def test_malformed_patient_id_returns_422_envelope(client: TestClient) -> None:
    response = client.get("/patients/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Request validation failed"


def test_request_id_is_returned_for_correlation(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-trace-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-trace-123"


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "unsafe value"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "unsafe value"
    UUID(response.headers["X-Request-ID"])


def test_database_failure_returns_safe_500_envelope(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_create(*_: object, **__: object) -> None:
        raise OperationalError("INSERT", {}, RuntimeError("database unavailable"))

    monkeypatch.setattr("app.api.patients.create_patient", fail_create)

    response = client.post("/patients", json=patient_payload())

    assert response.status_code == 500
    assert response.json() == {
        "data": None,
        "error": {"message": "Database operation failed"},
    }
    assert response.headers["X-Request-ID"]
