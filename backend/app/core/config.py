from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_name: str="Jaga"
    database_url: str
    redis_url: str

    # Auth: jwt_secret has no default, so the app refuses to start without one.
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # Banking: fake money every new customer starts with (paid from JAGA-TREASURY).
    opening_balance: Decimal = Decimal("10000.00")

    # Web frontends allowed to call the API from a browser (CORS).
    # In .env as JSON: CORS_ORIGINS=["http://localhost:3010"]
    cors_origins: list[str] = ["http://localhost:3010"]

settings = Settings()