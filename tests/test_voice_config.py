from app.voice.config import BOOTSTRAP_SYSTEM_PROMPT, build_assistant_config


def test_bootstrap_assistant_configuration_is_safe() -> None:
    config = build_assistant_config()

    assert config["firstMessageInterruptionsEnabled"] is True
    assert config["model"]["provider"] == "openai"
    assert config["model"]["model"] == "gpt-4.1-mini"
    assert config["model"]["messages"][0]["content"] == BOOTSTRAP_SYSTEM_PROMPT
    assert "claim that registration was saved" in BOOTSTRAP_SYSTEM_PROMPT
    assert "tools" not in config["model"]
