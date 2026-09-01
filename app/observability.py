import logging
import re
from contextvars import ContextVar, Token
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_request_id: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    """Attach the current request correlation ID to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format=(
            "%(asctime)s %(levelname)s %(name)s "
            "request_id=%(request_id)s: %(message)s"
        ),
    )
    context_filter = RequestContextFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(context_filter)


def start_request_trace(candidate: str | None) -> tuple[str, Token[str]]:
    """Start request tracing with a safe caller ID or a generated UUID."""
    request_id = (
        candidate if candidate and _SAFE_REQUEST_ID.fullmatch(candidate) else str(uuid4())
    )
    return request_id, _request_id.set(request_id)


def end_request_trace(token: Token[str]) -> None:
    _request_id.reset(token)
