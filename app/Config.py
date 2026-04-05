from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"
    FIREBASE_CREDENTIALS_JSON: str = ""
    FIREBASE_DATABASE_URL: str = ""
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AI Assistant API"
    DEBUG: bool = False
    TEST_MODE: bool = False
    ALLOWED_ORIGINS_RAW: str = "*"
    ENABLE_DOCS: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        value = self.ALLOWED_ORIGINS_RAW.strip()
        if not value:
            return []
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
