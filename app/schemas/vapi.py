import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class VapiToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def normalize_vapi_tool_call(cls, value: Any) -> Any:
        """Accept both current nested Vapi calls and the legacy flattened shape."""
        if not isinstance(value, dict):
            return value

        data = dict(value)
        function = data.get("function")
        if isinstance(function, dict):
            data.setdefault("name", function.get("name"))
            data.setdefault("arguments", function.get("arguments"))

        if "arguments" not in data and "parameters" in data:
            data["arguments"] = data["parameters"]

        arguments = data.get("arguments")
        if isinstance(arguments, str):
            try:
                data["arguments"] = json.loads(arguments)
            except json.JSONDecodeError:
                # Leave the invalid string in place so Pydantic returns a safe 422.
                pass

        return data


class VapiToolCallMessage(BaseModel):
    type: Literal["tool-calls"]
    tool_call_list: list[VapiToolCall]

    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), extra="ignore")


class VapiToolRequest(BaseModel):
    message: VapiToolCallMessage

    model_config = ConfigDict(extra="ignore")


class VapiToolResult(BaseModel):
    tool_call_id: str
    result: str

    model_config = ConfigDict(
        alias_generator=lambda value: _to_camel(value),
        populate_by_name=True,
    )


class VapiToolResponse(BaseModel):
    results: list[VapiToolResult]
