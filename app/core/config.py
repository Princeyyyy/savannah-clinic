import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Savannah Clinic Booking System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database URL defaults to local SQLite, but seamlessly accepts PostgreSQL in production (e.g. Render)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./clinic.db")
    
    # Minimum advance notice required for booking (Bonus: Prevention of bookings within 1 hour)
    MIN_ADVANCE_BOOKING_HOURS: int = 1
    
    # Slot duration in minutes
    SLOT_DURATION_MINUTES: int = 30
    
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )

    @property
    def normalized_database_url(self) -> str:
        # Render provides postgres:// or postgresql://; normalize to explicit psycopg2 driver
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
