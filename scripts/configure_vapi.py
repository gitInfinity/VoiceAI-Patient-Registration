import argparse
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import get_settings
from app.observability import configure_logging
from app.voice.config import build_assistant_config

VAPI_API_BASE_URL = "https://api.vapi.ai"
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update the Vapi patient-registration assistant."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Send the configuration to Vapi. Without this flag, print a dry run.",
    )
    return parser.parse_args()


def apply_assistant_config(
    *, api_key: str, assistant_id: str | None, payload: dict[str, object]
) -> dict[str, object]:
    endpoint = "/assistant" if assistant_id is None else f"/assistant/{assistant_id}"
    method = "POST" if assistant_id is None else "PATCH"
    request = Request(
        f"{VAPI_API_BASE_URL}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "VoiceAgent-Configurator/0.1",
        },
        method=method,
    )

    logger.info("Applying Vapi assistant configuration operation=%s", method)
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310
            result = json.load(response)
    except HTTPError as exc:
        logger.error("Vapi API rejected assistant configuration status=%s", exc.code)
        raise RuntimeError(f"Vapi API request failed with HTTP {exc.code}") from exc
    except URLError as exc:
        logger.error("Vapi API could not be reached")
        raise RuntimeError("Vapi API could not be reached") from exc

    if not isinstance(result, dict):
        raise RuntimeError("Vapi returned an unexpected response")
    logger.info("Vapi assistant configuration applied successfully")
    return result


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    tool_server_url = None
    if settings.public_base_url is not None:
        tool_server_url = f"{settings.public_base_url.rstrip('/')}/voice/tools"
    payload = build_assistant_config(
        tool_server_url=tool_server_url,
        credential_id=settings.vapi_credential_id,
    )

    if not args.apply:
        print(json.dumps(payload, indent=2))
        print("\nDry run only. Add --apply to create or update the Vapi assistant.")
        return

    if settings.vapi_api_key is None:
        raise SystemExit("VAPI_API_KEY is required with --apply")
    if tool_server_url is None or settings.vapi_credential_id is None:
        raise SystemExit(
            "PUBLIC_BASE_URL and VAPI_CREDENTIAL_ID are required with --apply"
        )

    result = apply_assistant_config(
        api_key=settings.vapi_api_key.get_secret_value(),
        assistant_id=settings.vapi_assistant_id,
        payload=payload,
    )
    assistant_id = result.get("id")
    print(f"Vapi assistant configured successfully. Assistant ID: {assistant_id}")
    if settings.vapi_assistant_id is None:
        print("Store this value as VAPI_ASSISTANT_ID before future updates.")


if __name__ == "__main__":
    main()
