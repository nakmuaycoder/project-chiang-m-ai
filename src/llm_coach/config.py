from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    INTERVALS_ATHLETE_ID: str
    INTERVALS_API_KEY: SecretStr
    GOOGLE_API_KEY: SecretStr
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str | None = None
    PERIODIZATION: str = "3:1"  # Training block pattern (2:1 or 3:1)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
