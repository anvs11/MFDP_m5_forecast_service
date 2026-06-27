from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    """
    Общие настройки приложения.
    Читает переменные окружения из .env файла.
    """
    APP_NAME: str = "M5 Forecast Service"
    APP_DESCRIPTION: str = "Сервис прогнозирования спроса на скоропортящиеся товары"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    COOKIE_NAME: str = "access_token"

    DEMO_BALANCE: float = 100.0

    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "rmuser"
    RABBITMQ_PASS: str = "rmpassword"
    RABBITMQ_QUEUE: str = "m5_forecast_tasks"

    MODEL_PATH: str = "/app/model/artifacts/model.pkl"
    ALPHA: float = 0.2
    HORIZON_DAYS: int = 28

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/app/logs/app.log"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """URL для асинхронного подключения (asyncpg)"""
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """URL для синхронного подключения (psycopg)"""
        return f'postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def RABBITMQ_URL(self) -> str:
        """URL для RabbitMQ"""
        return f'amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//'

    def validate(self) -> None:
        """Проверка критических параметров"""
        required_fields = {
            'SECRET_KEY': self.SECRET_KEY,
            'DB_HOST': self.DB_HOST,
            'DB_USER': self.DB_USER,
            'DB_PASS': self.DB_PASS,
            'DB_NAME': self.DB_NAME,
        }

        missing = [field for field, value in required_fields.items() if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


@lru_cache()
def get_settings() -> Settings:
    """
    Возвращает кэшированный экземпляр настроек.
    """
    settings = Settings()
    settings.validate()
    return settings
