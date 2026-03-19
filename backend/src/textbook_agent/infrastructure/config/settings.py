from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    default_pagination_limit: int = 20

    # Output
    document_output_dir: str = "outputs/documents"

    # Authentication
    google_client_id: str = ""
    jwt_secret_key: str = "CHANGE-ME"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "sqlite+aiosqlite:///./textbook_agent.db"

    # CORS
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
