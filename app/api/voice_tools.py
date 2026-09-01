import json
import logging
from secrets import compare_digest
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.patient import PatientCreate, PatientFilters, PatientRead, PatientUpdate
from app.schemas.vapi import VapiToolCall, VapiToolRequest, VapiToolResponse, VapiToolResult
from app.services.patient_service import (
    create_patient,
    list_patients,
    update_patient,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


def require_vapi_tool_auth(
    x_vapi_secret: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    configured_secret = settings.vapi_tool_secret
    if configured_secret is None:
        logger.error("Vapi tool endpoint is not configured with a secret")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice tool authentication is not configured",
        )

    expected = configured_secret.get_secret_value()
    if x_vapi_secret is None or not compare_digest(x_vapi_secret, expected):
        logger.warning("Rejected unauthenticated Vapi tool request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid voice tool credentials",
        )


def _patient_json(patient: Any) -> dict[str, Any]:
    return PatientRead.model_validate(patient).model_dump(mode="json")


def _dispatch_tool_call(session: Session, tool_call: VapiToolCall) -> Any:
    if tool_call.name == "search_patient_by_phone":
        filters = PatientFilters.model_validate(
            {"phone_number": tool_call.arguments.get("phone_number")}
        )
        patients = list_patients(session, phone_number=filters.phone_number)
        return {
            "success": True,
            "found": bool(patients),
            "patients": [_patient_json(patient) for patient in patients],
        }

    if tool_call.name == "create_patient":
        arguments = dict(tool_call.arguments)
        confirmed = arguments.pop("confirmed", False)
        if confirmed is not True:
            raise ValueError("Explicit caller confirmation is required before saving")
        patient_data = PatientCreate.model_validate(arguments)
        patient = create_patient(session, patient_data)
        return {
            "success": True,
            "message": "Patient registration saved successfully",
            "patient": _patient_json(patient),
        }

    if tool_call.name == "update_patient":
        arguments = dict(tool_call.arguments)
        confirmed = arguments.get("confirmed", False)
        if confirmed is not True:
            raise ValueError("Explicit caller confirmation is required before updating")
        patient_id = UUID(str(arguments.get("patient_id", "")))
        fields = arguments.get("fields")
        patient_data = PatientUpdate.model_validate(fields)
        patient = update_patient(session, patient_id, patient_data)
        if patient is None:
            return {"success": False, "error": "Patient not found"}
        return {
            "success": True,
            "message": "Patient record updated successfully",
            "patient": _patient_json(patient),
        }

    raise ValueError(f"Unsupported tool: {tool_call.name}")


@router.post(
    "/tools",
    response_model=VapiToolResponse,
    dependencies=[Depends(require_vapi_tool_auth)],
)
def handle_vapi_tools(
    request: VapiToolRequest,
    session: Annotated[Session, Depends(get_db)],
) -> VapiToolResponse:
    """Execute authenticated Vapi function calls through the service layer."""
    logger.info("Received Vapi tool invocation count=%s", len(request.message.tool_call_list))
    results: list[VapiToolResult] = []

    for tool_call in request.message.tool_call_list:
        logger.info("Executing Vapi tool name=%s", tool_call.name)
        try:
            result = _dispatch_tool_call(session, tool_call)
        except ValidationError:
            logger.warning("Vapi tool validation failed name=%s", tool_call.name)
            result = {"success": False, "error": "Invalid tool arguments"}
        except ValueError as exc:
            logger.warning("Vapi tool validation failed name=%s", tool_call.name)
            result = {"success": False, "error": str(exc)}
        except SQLAlchemyError:
            logger.exception("Vapi tool database failure name=%s", tool_call.name)
            result = {"success": False, "error": "Database operation failed"}

        serialized_result = json.dumps(result, separators=(",", ":"))
        results.append(
            VapiToolResult(tool_call_id=tool_call.id, result=serialized_result)
        )

    return VapiToolResponse(results=results)
