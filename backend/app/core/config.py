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

settings = Settings()