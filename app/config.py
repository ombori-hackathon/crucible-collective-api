from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/hackathon"
    debug: bool = True
    gemini_api_key: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
