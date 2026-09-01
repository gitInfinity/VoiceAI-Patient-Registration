import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.patient import Patient, utc_now
from app.schemas.patient import PatientCreate, PatientUpdate

logger = logging.getLogger(__name__)


def create_patient(session: Session, patient_data: PatientCreate) -> Patient:
    """Persist a validated patient payload."""
    logger.info("Attempting to create patient")
    patient = Patient(**patient_data.model_dump())

    try:
        session.add(patient)
        session.commit()
        session.refresh(patient)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Patient creation failed")
        raise

    logger.info("Patient created successfully")
    return patient


def get_patient(session: Session, patient_id: UUID) -> Patient | None:
    """Return an active patient by ID."""
    statement = select(Patient).where(
        Patient.patient_id == patient_id,
        Patient.deleted_at.is_(None),
    )
    patient = session.scalar(statement)
    logger.debug("Patient lookup completed found=%s", patient is not None)
    return patient


def list_patients(
    session: Session,
    *,
    last_name: str | None = None,
    date_of_birth: date | None = None,
    phone_number: str | None = None,
) -> list[Patient]:
    """List active patients matching all supplied exact-match filters."""
    statement = select(Patient).where(Patient.deleted_at.is_(None))

    if last_name is not None:
        statement = statement.where(Patient.last_name == last_name)
    if date_of_birth is not None:
        statement = statement.where(Patient.date_of_birth == date_of_birth)
    if phone_number is not None:
        statement = statement.where(Patient.phone_number == phone_number)

    statement = statement.order_by(Patient.created_at, Patient.patient_id)
    patients = list(session.scalars(statement).all())
    logger.info("Patient list completed result_count=%s", len(patients))
    return patients


def update_patient(
    session: Session,
    patient_id: UUID,
    patient_data: PatientUpdate,
) -> Patient | None:
    """Apply supplied fields to an active patient."""
    patient = get_patient(session, patient_id)
    if patient is None:
        logger.warning("Patient update skipped because active record was not found")
        return None

    changes = patient_data.model_dump(exclude_unset=True)
    for field_name, value in changes.items():
        setattr(patient, field_name, value)

    if not changes:
        logger.info("Patient update completed with no supplied changes")
        return patient

    try:
        session.commit()
        session.refresh(patient)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Patient update failed")
        raise

    logger.info("Patient updated successfully")
    return patient


def soft_delete_patient(session: Session, patient_id: UUID) -> Patient | None:
    """Mark an active patient as deleted without removing its row."""
    patient = get_patient(session, patient_id)
    if patient is None:
        logger.warning("Patient soft deletion skipped because active record was not found")
        return None

    patient.deleted_at = utc_now()

    try:
        session.commit()
        session.refresh(patient)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Patient soft deletion failed")
        raise

    logger.info("Patient soft deleted successfully")
    return patient
