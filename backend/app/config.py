from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg2://salinity:salinity@localhost:5432/salinity"
    secret_key: str = "dev-only-change-me"
    access_token_minutes: int = 120
    cors_origins: str = "http://localhost:5173"
    model_dir: str = "../models"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@example.org"
    max_upload_mb: int = 5


settings = Settings()
