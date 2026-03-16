from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SafeDoc API"
    secret_key: str = "CHANGE_ME_IN_PROD"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    database_url: str = "sqlite+aiosqlite:///./safedoc.db"

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "safedoc"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    default_superadmin_login: str = "admin"
    default_superadmin_password: str = "admin123"

    storage_dir: str = "storage"
    logs_dir: str = "logs"


settings = Settings()

