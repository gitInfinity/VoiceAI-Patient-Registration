from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.patient import PatientCreate, PatientUpdate, Sex


def valid_patient_data() -> dict[str, object]:
    return {
        "first_name": "Anne-Marie",
        "last_name": "O'Brien",
        "date_of_birth": "04/15/1990",
        "sex": "Female",
        "phone_number": "(212) 555-0198",
        "address_line_1": "123 Main Street",
        "city": "New York",
        "state": "ny",
        "zip_code": "10001-1234",
        "email": "anne@example.com",
    }


def test_create_patient_normalizes_valid_data() -> None:
    patient = PatientCreate.model_validate(valid_patient_data())

    assert patient.first_name == "Anne-Marie"
    assert patient.date_of_birth == date(1990, 4, 15)
    assert patient.sex is Sex.FEMALE
    assert patient.phone_number == "2125550198"
    assert patient.state == "NY"
    assert patient.preferred_language == "English"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_name", "John3"),
        ("phone_number", "555-123"),
        ("state", "XX"),
        ("zip_code", "1234"),
        ("email", "not-an-email"),
    ],
)
def test_create_patient_rejects_invalid_demographics(field: str, value: str) -> None:
    payload = valid_patient_data()
    payload[field] = value

    with pytest.raises(ValidationError):
        PatientCreate.model_validate(payload)


def test_create_patient_rejects_future_date_of_birth() -> None:
    payload = valid_patient_data()
    payload["date_of_birth"] = date.today() + timedelta(days=1)

    with pytest.raises(ValidationError, match="cannot be in the future"):
        PatientCreate.model_validate(payload)


def test_partial_update_only_contains_supplied_fields() -> None:
    update = PatientUpdate.model_validate({"phone_number": "212.555.0100"})

    assert update.model_dump(exclude_unset=True) == {"phone_number": "2125550100"}


def test_partial_update_rejects_null_required_field() -> None:
    with pytest.raises(ValidationError, match="required fields cannot be null"):
        PatientUpdate.model_validate({"first_name": None})


def test_partial_update_allows_clearing_optional_field() -> None:
    update = PatientUpdate.model_validate({"email": None})

    assert update.model_dump(exclude_unset=True) == {"email": None}
