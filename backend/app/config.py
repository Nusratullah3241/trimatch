from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    database_url: str = "sqlite:///./data/trimatch.db"
    inbox_dir: str = "./data/inbox"
    processed_dir: str = "./data/processed"

    # Business rules - the tolerance limits
    price_tolerance_pct: float = 2.0
    quantity_tolerance_pct: float = 0.0
    absolute_tolerance_amount: float = 500.0

    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()