from pydantic import BaseModel


class ErrorDetail(BaseModel):
    message: str


class ApiResponse[DataT](BaseModel):
    """Consistent success or failure response envelope."""

    data: DataT | None = None
    error: ErrorDetail | None = None
