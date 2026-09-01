from app.config import Settings


def test_postgres_url_uses_psycopg_driver() -> None:
    settings = Settings(database_url="postgres://user:pass@database:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:pass@database:5432/app"


def test_explicit_psycopg_url_is_unchanged() -> None:
    url = "postgresql+psycopg://user:pass@database:5432/app"

    assert Settings(database_url=url).database_url == url


def test_private_vapi_key_alias_is_supported(monkeypatch) -> None:
    monkeypatch.setenv("PRIVATE_VAPI_KEY", "test-private-key")

    settings = Settings()

    assert settings.vapi_api_key is not None
    assert settings.vapi_api_key.get_secret_value() == "test-private-key"
