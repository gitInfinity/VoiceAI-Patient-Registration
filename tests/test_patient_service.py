from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.patient_service import (
    create_patient,
    get_patient,
    list_patients,
    soft_delete_patient,
    update_patient,
)


@pytest.fixture
def session(tmp_path) -> Iterator[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'service.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as database_session:
        yield database_session


def patient_payload(**overrides: object) -> PatientCreate:
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
    }
    data.update(overrides)
    return PatientCreate.model_validate(data)


def test_create_and_get_patient(session: Session) -> None:
    created = create_patient(session, patient_payload())

    retrieved = get_patient(session, created.patient_id)

    assert retrieved is created
    assert retrieved.phone_number == "2125550198"


def test_list_patients_applies_all_filters(session: Session) -> None:
    matching = create_patient(session, patient_payload())
    create_patient(
        session,
        patient_payload(
            first_name="John",
            last_name="Jones",
            phone_number="6465550100",
        ),
    )

    results = list_patients(
        session,
        last_name="Smith",
        date_of_birth=date(1990, 4, 15),
        phone_number="2125550198",
    )

    assert results == [matching]


def test_update_patient_applies_only_supplied_fields(session: Session) -> None:
    patient = create_patient(session, patient_payload(email="old@example.com"))
    original_first_name = patient.first_name

    updated = update_patient(
        session,
        patient.patient_id,
        PatientUpdate.model_validate({"city": "Albany", "email": None}),
    )

    assert updated is patient
    assert updated.city == "Albany"
    assert updated.email is None
    assert updated.first_name == original_first_name


def test_update_unknown_patient_returns_none(session: Session) -> None:
    patient = create_patient(session, patient_payload())
    soft_delete_patient(session, patient.patient_id)

    assert update_patient(
        session,
        patient.patient_id,
        PatientUpdate.model_validate({"city": "Albany"}),
    ) is None


def test_soft_delete_hides_patient_without_removing_row(session: Session) -> None:
    patient = create_patient(session, patient_payload())

    deleted = soft_delete_patient(session, patient.patient_id)

    assert deleted is patient
    assert deleted.deleted_at is not None
    assert get_patient(session, patient.patient_id) is None
    assert list_patients(session) == []
    assert session.scalar(
        select(Patient).where(Patient.patient_id == patient.patient_id)
    ) is patient


def test_soft_delete_unknown_patient_returns_none(session: Session) -> None:
    patient = create_patient(session, patient_payload())
    soft_delete_patient(session, patient.patient_id)

    assert soft_delete_patient(session, patient.patient_id) is None
