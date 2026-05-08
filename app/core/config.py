from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./orchestrator.db"
    app_env: str = "local"
    log_level: str = "INFO"
    max_tool_retries: int = 2
    python_sandbox_timeout_seconds: int = 2
    default_model_provider: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
