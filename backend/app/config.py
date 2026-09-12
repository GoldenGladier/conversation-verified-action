from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    openai_api_key: str
    google_calendar_credentials_path: str = "credentials.json"
    google_calendar_id: str = ""
    google_calendar_timezone: str = "America/Mexico_City"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()