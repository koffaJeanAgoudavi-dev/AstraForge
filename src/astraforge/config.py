"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AstraForge"
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    groq_api_key: str | None = None
    groq_default_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str | None = None
    gemini_default_model: str = "gemini-3.8-flash"\n    gemini_embedding_model: str = "gemini-embedding-2"
    deepseek_api_key: str | None = None
    deepseek_default_model: str = "deepseek-flash"
    openai_api_key: str | None = None
    openai_default_model: str = "gpt-5.6-terra"
    mistral_api_key: str | None = None
    mistral_default_model: str = "mistral-medium-3.5"
    cerebras_api_key: str | None = None
    cerebras_default_model: str = "gpt-oss-120b"

    github_token: str | None = None
    github_repository: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
