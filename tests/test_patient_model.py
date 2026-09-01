from datetime import date
from uuid import UUID

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.patient import Patient
from app.schemas.patient import PatientRead, Sex


def test_patient_model_persists_with_generated_fields(tmp_path) -> None:
    database_path = tmp_path / "patients.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    patient = Patient(
        first_name="Anne-Marie",
        last_name="O'Brien",
        date_of_birth=date(1990, 4, 15),
        sex=Sex.FEMALE,
        phone_number="2125550198",
        address_line_1="123 Main Street",
        city="New York",
        state="NY",
        zip_code="10001",
    )

    with Session(engine) as session:
        session.add(patient)
        session.commit()
        session.refresh(patient)

        assert isinstance(patient.patient_id, UUID)
        assert patient.preferred_language == "English"
        assert patient.created_at is not None
        assert patient.updated_at is not None
        assert patient.deleted_at is None
        assert PatientRead.model_validate(patient).phone_number == "2125550198"


def test_patient_table_indexes_lookup_fields(tmp_path) -> None:
    database_path = tmp_path / "indexes.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    indexed_columns = {
        column
        for index in inspect(engine).get_indexes("patients")
        for column in index["column_names"]
    }

    assert {"last_name", "date_of_birth", "phone_number"} <= indexed_columns
