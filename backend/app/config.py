"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Spider Manager V1.0"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root123"
    DB_NAME: str = "spider"

    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        pwd = quote_plus(self.DB_PASSWORD)
        return f"mysql+aiomysql://{self.DB_USER}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        pwd = quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{self.DB_USER}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # JWT
    SECRET_KEY: str = "spider-manager-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    SCRIPTS_DIR: str = os.path.join(DATA_DIR, "scripts")
    RESULTS_DIR: str = os.path.join(DATA_DIR, "results")
    LOGS_DIR: str = os.path.join(DATA_DIR, "logs")

    # Task Manager
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT: int = 1800  # 30 minutes

    # Scheduler
    SCHEDULER_ENABLED: bool = True

    # CORS
    CORS_ORIGINS: str = "*"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# Ensure directories exist
for d in [settings.DATA_DIR, settings.SCRIPTS_DIR, settings.RESULTS_DIR, settings.LOGS_DIR]:
    os.makedirs(d, exist_ok=True)
