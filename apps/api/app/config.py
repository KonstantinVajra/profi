from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite by default for local dev; override with postgres URL for production
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost/landing_replay"
    redis_url: Optional[str] = None        # not used in MVP
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    site_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
