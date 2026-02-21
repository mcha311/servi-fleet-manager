from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Servi Fleet Manager"
    DEBUG: bool = True

    # Database (RDS)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/servi_db"

    # Redis (ElastiCache)
    REDIS_URL: str = "redis://localhost:6379"

    # Robot settings
    BATTERY_ALERT_THRESHOLD: int = 20
    MAX_ROBOTS: int = 10

    class Config:
        env_file = ".env"

settings = Settings()

# SpringBoot application.yml