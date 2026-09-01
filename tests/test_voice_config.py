from app.voice.config import (
    SYSTEM_PROMPT,
    build_assistant_config,
)


def test_assistant_uses_authenticated_backend_tools() -> None:
    config = build_assistant_config(
        tool_server_url="https://api.example.com/voice/tools",
        credential_id="credential-123",
    )

    model = config["model"]
    assert config["firstMessageInterruptionsEnabled"] is True
    assert model["provider"] == "openai"
    assert model["model"] == "gpt-4.1-mini"
    assert model["messages"][0]["content"] == SYSTEM_PROMPT
    assert {tool["function"]["name"] for tool in model["tools"]} == {
        "search_patient_by_phone",
        "create_patient",
        "update_patient",
    }
    assert all(
        tool["server"]
        == {
            "url": "https://api.example.com/voice/tools",
            "credentialId": "credential-123",
        }
        for tool in model["tools"]
    )
    update_tool = next(
        tool for tool in model["tools"] if tool["function"]["name"] == "update_patient"
    )
    assert "confirmed" in update_tool["function"]["parameters"]["required"]


def test_assistant_prompt_requires_confirmation_and_handles_corrections() -> None:
    normalized_prompt = " ".join(SYSTEM_PROMPT.split())

    assert "explicit yes-or-no confirmation" in normalized_prompt
    assert "discard the entire draft" in normalized_prompt
    assert "success=true" in normalized_prompt
