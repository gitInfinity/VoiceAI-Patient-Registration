from app.voice.config import (
    BOOTSTRAP_SYSTEM_PROMPT,
    TOOL_SYSTEM_PROMPT,
    build_assistant_config,
)


def test_bootstrap_assistant_configuration_is_safe() -> None:
    config = build_assistant_config()

    assert config["firstMessageInterruptionsEnabled"] is True
    assert config["model"]["provider"] == "openai"
    assert config["model"]["model"] == "gpt-4.1-mini"
    assert config["model"]["messages"][0]["content"] == BOOTSTRAP_SYSTEM_PROMPT
    assert "claim that registration was saved" in BOOTSTRAP_SYSTEM_PROMPT
    assert "tools" not in config["model"]


def test_tool_enabled_assistant_uses_authenticated_backend_tools() -> None:
    config = build_assistant_config(
        tool_server_url="https://api.example.com/voice/tools",
        credential_id="credential-123",
    )

    model = config["model"]
    assert model["messages"][0]["content"] == TOOL_SYSTEM_PROMPT
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
