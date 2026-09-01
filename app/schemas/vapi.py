from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class VapiToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]

    model_config = ConfigDict(extra="ignore")


class VapiToolCallMessage(BaseModel):
    type: Literal["tool-calls"]
    tool_call_list: list[VapiToolCall]

    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), extra="ignore")


class VapiToolRequest(BaseModel):
    message: VapiToolCallMessage

    model_config = ConfigDict(extra="ignore")


class VapiToolResult(BaseModel):
    tool_call_id: str
    result: Any

    model_config = ConfigDict(
        alias_generator=lambda value: _to_camel(value),
        populate_by_name=True,
    )


class VapiToolResponse(BaseModel):
    results: list[VapiToolResult]
