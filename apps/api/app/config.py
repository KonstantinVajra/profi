from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite by default for local dev; override with postgres URL for production
    database_url: str = "sqlite:///./app.db"
    redis_url: Optional[str] = None        # not used in MVP
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    site_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
