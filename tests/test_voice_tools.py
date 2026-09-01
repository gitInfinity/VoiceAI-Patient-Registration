import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.session import Base, get_db
from app.main import app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'voice-tools.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        vapi_tool_secret="test-tool-secret"
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def tool_request(name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "tool-call-1",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(arguments),
                    },
                }
            ],
        }
    }


def patient_arguments(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "first_name": "Anne",
        "last_name": "Smith",
        "date_of_birth": "04/15/1990",
        "sex": "Female",
        "phone_number": "212-555-0198",
        "address_line_1": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "confirmed": True,
    }
    data.update(overrides)
    return data


def call_tool(
    client: TestClient, name: str, arguments: dict[str, object]
) -> dict[str, object]:
    response = client.post(
        "/voice/tools",
        json=tool_request(name, arguments),
        headers={"X-Vapi-Secret": "test-tool-secret"},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["toolCallId"] == "tool-call-1"
    serialized_result = response.json()["results"][0]["result"]
    assert isinstance(serialized_result, str)
    assert "\n" not in serialized_result
    return json.loads(serialized_result)


def test_voice_tool_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/voice/tools",
        json=tool_request("search_patient_by_phone", {"phone_number": "2125550198"}),
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid voice tool credentials"


def test_voice_tool_accepts_flattened_parameters_shape(client: TestClient) -> None:
    response = client.post(
        "/voice/tools",
        json={
            "message": {
                "type": "tool-calls",
                "toolCallList": [
                    {
                        "id": "tool-call-1",
                        "name": "search_patient_by_phone",
                        "parameters": {"phone_number": "2125550198"},
                    }
                ],
            }
        },
        headers={"X-Vapi-Secret": "test-tool-secret"},
    )

    assert response.status_code == 200
    result = json.loads(response.json()["results"][0]["result"])
    assert result == {"success": True, "found": False, "patients": []}


def test_create_requires_explicit_confirmation(client: TestClient) -> None:
    result = call_tool(
        client,
        "create_patient",
        patient_arguments(confirmed=False),
    )

    assert result == {
        "success": False,
        "error": "Explicit caller confirmation is required before saving",
    }


def test_update_requires_explicit_confirmation(client: TestClient) -> None:
    created = call_tool(client, "create_patient", patient_arguments())

    result = call_tool(
        client,
        "update_patient",
        {
            "patient_id": created["patient"]["patient_id"],
            "fields": {"city": "Albany"},
            "confirmed": False,
        },
    )

    assert result == {
        "success": False,
        "error": "Explicit caller confirmation is required before updating",
    }


def test_voice_tools_create_search_and_update_patient(client: TestClient) -> None:
    created = call_tool(client, "create_patient", patient_arguments())
    patient_id = created["patient"]["patient_id"]

    search = call_tool(
        client,
        "search_patient_by_phone",
        {"phone_number": "(212) 555-0198"},
    )
    updated = call_tool(
        client,
        "update_patient",
        {"patient_id": patient_id, "fields": {"city": "Albany"}, "confirmed": True},
    )

    assert created["success"] is True
    assert search["success"] is True
    assert search["found"] is True
    assert search["patients"][0]["patient_id"] == patient_id
    assert updated["success"] is True
    assert updated["patient"]["city"] == "Albany"
