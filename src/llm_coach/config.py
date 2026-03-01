import os
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    INTERVALS_ATHLETE_ID: str
    INTERVALS_API_KEY: SecretStr
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str | None = None
    PERIODIZATION: str = "3:1"  # Training block pattern (2:1 or 3:1)
    DB_PATH: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def get_db_path(self) -> Path:
        """Returns the fully resolved database path."""
        if self.DB_PATH:
            return Path(self.DB_PATH)

        # Respect XDG_DATA_HOME if set, otherwise fallback to ~/.local/share
        xdg_data_home = os.environ.get(
            "XDG_DATA_HOME", str(Path.home() / ".local" / "share")
        )
        return Path(xdg_data_home) / "llm-coach" / "workout_sync_history.json"


settings = Settings()
