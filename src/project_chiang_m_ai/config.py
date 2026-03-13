from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_coach_config(yaml_path: str = "coach_config.yaml") -> Dict[str, Any]:
    """Loads and parses the coach configuration YAML."""
    path = Path(yaml_path)
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


coach_config = load_coach_config()


class Settings(BaseSettings):
    INTERVALS_ATHLETE_ID: str
    INTERVALS_API_KEY: SecretStr
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str | None = None
    PERIODIZATION: str = "3:1"  # Training block pattern (2:1 or 3:1)
    DB_PATH: str = "data/workout_sync_history.json"
    WELLNESS_HISTORY_DAYS: int = 10

    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # Can be gemini, openai, anthropic
    LLM_MODEL: str = "gemini-3.1-flash"
    GEMINI_API_KEY: SecretStr | None = None
    OPENAI_API_KEY: SecretStr | None = None
    ANTHROPIC_API_KEY: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def get_db_path(self) -> Path:
        """Returns the fully resolved database path."""
        return Path(self.DB_PATH)


settings = Settings()
