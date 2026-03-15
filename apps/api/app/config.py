from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: Optional[str] = None   # not used in MVP — optional so app starts without Redis
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    site_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
