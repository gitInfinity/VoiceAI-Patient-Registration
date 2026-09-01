import re
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    field_validator,
    model_validator,
)

US_STATE_CODES = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    }
)

NAME_PATTERN = re.compile(r"^[^\W\d_]+(?:[-'][^\W\d_]+)*$", re.UNICODE)
ZIP_PATTERN = re.compile(r"^\d{5}(?:-\d{4})?$")

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
City = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Sex(StrEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE_TO_ANSWER = "Decline to Answer"


def _validate_name(value: str | None) -> str | None:
    if value is None:
        return None
    if not NAME_PATTERN.fullmatch(value):
        raise ValueError("must contain only letters, hyphens, and apostrophes")
    return value


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) != 10:
        raise ValueError("must contain exactly 10 digits")
    return digits


def _normalize_state(value: str | None) -> str | None:
    if value is None:
        return None
    state = value.strip().upper()
    if state not in US_STATE_CODES:
        raise ValueError("must be a valid two-letter US state abbreviation")
    return state


def _validate_zip(value: str | None) -> str | None:
    if value is None:
        return None
    zip_code = value.strip()
    if not ZIP_PATTERN.fullmatch(zip_code):
        raise ValueError("must be a 5-digit ZIP code or ZIP+4")
    return zip_code


def _parse_date_of_birth(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    raw_value = value.strip()
    for date_format in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw_value, date_format).date()
        except ValueError:
            continue
    raise ValueError("must use MM/DD/YYYY or YYYY-MM-DD format")


def _validate_date_of_birth(value: date | None) -> date | None:
    if value is None:
        return None
    if value > date.today():
        raise ValueError("cannot be in the future")
    return value


class PatientFields(BaseModel):
    first_name: Name
    last_name: Name
    date_of_birth: date
    sex: Sex
    phone_number: str
    address_line_1: NonEmptyText
    city: City
    state: str
    zip_code: str
    email: EmailStr | None = None
    address_line_2: OptionalText | None = None
    insurance_provider: OptionalText | None = None
    insurance_member_id: OptionalText | None = None
    preferred_language: OptionalText = "English"
    emergency_contact_name: OptionalText | None = None
    emergency_contact_phone: str | None = None

    model_config = ConfigDict(extra="forbid")

    _first_name = field_validator("first_name")(_validate_name)
    _last_name = field_validator("last_name")(_validate_name)
    _date_input = field_validator("date_of_birth", mode="before")(_parse_date_of_birth)
    _date_value = field_validator("date_of_birth")(_validate_date_of_birth)
    _phone = field_validator("phone_number")(_normalize_phone)
    _emergency_phone = field_validator("emergency_contact_phone")(_normalize_phone)
    _state = field_validator("state")(_normalize_state)
    _zip = field_validator("zip_code")(_validate_zip)


class PatientCreate(PatientFields):
    """Validated payload for creating a patient."""


class PatientFilters(BaseModel):
    """Validated exact-match filters for patient listing."""

    last_name: Name | None = None
    date_of_birth: date | None = None
    phone_number: str | None = None

    model_config = ConfigDict(extra="forbid")

    _last_name = field_validator("last_name")(_validate_name)
    _date_input = field_validator("date_of_birth", mode="before")(_parse_date_of_birth)
    _date_value = field_validator("date_of_birth")(_validate_date_of_birth)
    _phone = field_validator("phone_number")(_normalize_phone)


class PatientUpdate(BaseModel):
    """Validated partial patient update.

    Use ``model_dump(exclude_unset=True)`` to distinguish omitted fields from
    optional fields intentionally cleared with null.
    """

    first_name: Name | None = None
    last_name: Name | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone_number: str | None = None
    address_line_1: NonEmptyText | None = None
    city: City | None = None
    state: str | None = None
    zip_code: str | None = None
    email: EmailStr | None = None
    address_line_2: OptionalText | None = None
    insurance_provider: OptionalText | None = None
    insurance_member_id: OptionalText | None = None
    preferred_language: OptionalText | None = None
    emergency_contact_name: OptionalText | None = None
    emergency_contact_phone: str | None = None

    model_config = ConfigDict(extra="forbid")

    _first_name = field_validator("first_name")(_validate_name)
    _last_name = field_validator("last_name")(_validate_name)
    _date_input = field_validator("date_of_birth", mode="before")(_parse_date_of_birth)
    _date_value = field_validator("date_of_birth")(_validate_date_of_birth)
    _phone = field_validator("phone_number")(_normalize_phone)
    _emergency_phone = field_validator("emergency_contact_phone")(_normalize_phone)
    _state = field_validator("state")(_normalize_state)
    _zip = field_validator("zip_code")(_validate_zip)

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "PatientUpdate":
        required_fields = {
            "first_name",
            "last_name",
            "date_of_birth",
            "sex",
            "phone_number",
            "address_line_1",
            "city",
            "state",
            "zip_code",
        }
        cleared_fields = required_fields.intersection(self.model_fields_set)
        cleared_fields = {field for field in cleared_fields if getattr(self, field) is None}
        if cleared_fields:
            fields = ", ".join(sorted(cleared_fields))
            raise ValueError(f"required fields cannot be null: {fields}")
        return self


class PatientRead(PatientFields):
    """Patient representation returned by the API."""

    patient_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
