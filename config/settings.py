"""
Типизированная конфигурация через pydantic-settings: значения валидируются
при старте (например, base_url обязан быть валидным URL), а не падают
где-то в середине теста с непонятной ошибкой.
"""

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AQA_", env_file=".env", extra="ignore")

    base_url: HttpUrl = HttpUrl("https://book-tracker-api-frnm.onrender.com")
    # Render free tier "засыпает" после простоя — первый запрос может идти
    # 30-60 секунд, поэтому таймаут и ретраи заметно выше дефолтных.
    timeout: int = 60
    retry_attempts: int = 3
    retry_wait_seconds: int = 5


settings = Settings()

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}
