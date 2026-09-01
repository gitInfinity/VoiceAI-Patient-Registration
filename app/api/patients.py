from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.patient import PatientCreate, PatientFilters, PatientRead, PatientUpdate
from app.schemas.response import ApiResponse
from app.services.patient_service import (
    create_patient,
    get_patient,
    list_patients,
    soft_delete_patient,
    update_patient,
)

router = APIRouter(prefix="/patients", tags=["patients"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ApiResponse[list[PatientRead]])
def get_patients(
    session: SessionDependency,
    filters: Annotated[PatientFilters, Query()],
) -> ApiResponse[list[PatientRead]]:
    patients = list_patients(
        session,
        last_name=filters.last_name,
        date_of_birth=filters.date_of_birth,
        phone_number=filters.phone_number,
    )
    return ApiResponse(data=patients)


@router.get("/{patient_id}", response_model=ApiResponse[PatientRead])
def get_patient_by_id(
    patient_id: UUID,
    session: SessionDependency,
) -> ApiResponse[PatientRead]:
    patient = get_patient(session, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return ApiResponse(data=patient)


@router.post(
    "",
    response_model=ApiResponse[PatientRead],
    status_code=status.HTTP_201_CREATED,
)
def create_patient_record(
    patient_data: PatientCreate,
    session: SessionDependency,
) -> ApiResponse[PatientRead]:
    patient = create_patient(session, patient_data)
    return ApiResponse(data=patient)


@router.put("/{patient_id}", response_model=ApiResponse[PatientRead])
def update_patient_record(
    patient_id: UUID,
    patient_data: PatientUpdate,
    session: SessionDependency,
) -> ApiResponse[PatientRead]:
    patient = update_patient(session, patient_id, patient_data)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return ApiResponse(data=patient)


@router.delete("/{patient_id}", response_model=ApiResponse[PatientRead])
def delete_patient_record(
    patient_id: UUID,
    session: SessionDependency,
) -> ApiResponse[PatientRead]:
    patient = soft_delete_patient(session, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return ApiResponse(data=patient)
