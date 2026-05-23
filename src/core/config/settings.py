import logging
from typing import Optional
from pathlib import Path
from pydantic import Field, PostgresDsn, RedisDsn, validator, SecretStr
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: SecretStr = Field(..., env="DB_PASSWORD")
    DB_HOST: str = Field("localhost", env="DB_HOST")
    DB_PORT: int = Field(5432, env="DB_PORT")
    DB_NAME: str = Field(..., env="DB_NAME")

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

class RedisSettings(BaseSettings):
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[SecretStr] = Field(None, env="REDIS_PASSWORD")
    REDIS_SOCKET_TIMEOUT: int = Field(5, env="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(30, env="REDIS_HEALTH_CHECK_INTERVAL")

    @property
    def config(self) -> dict[str, any]:
        config = {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "db": self.REDIS_DB,
            "password": self.REDIS_PASSWORD,
            "socket_timeout": self.REDIS_SOCKET_TIMEOUT,
            "socket_connect_timeout": self.REDIS_SOCKET_CONNECT_TIMEOUT,
            "health_check_interval": self.REDIS_HEALTH_CHECK_INTERVAL

        }

        if self.REDIS_PASSWORD:
            config["password"] = self.REDIS_PASSWORD.get_secret_value()
        else:
            config["password"] = None

        return config

    @property
    def dsn(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD.get_secret_value()}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://:{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

class AppSettings(BaseSettings):
    # Основные настройки
    BOT_TOKEN: SecretStr = Field(..., env="BOT_TOKEN")
    EVENT_CHAT: str = Field(..., env="EVENT_CHAT")
    USE_REDIS: bool = Field(default=True, env="USE_REDIS")

    # Настройка режима бота
    DEBUG: bool = Field(default=False, env="DEBUG")
    MAINTENANCE_MODE: bool = Field(default=False, env="MAINTENANCE_MODE")

    # Настройка БД
    POSTGRES_DSN: Optional[PostgresDsn] = Field(None, env="POSTGRES_DSN")
    REDIS_DSN: RedisDsn = Field("redis://localhost:6379/0", env="REDIS_DSN")

    # Настройка платежей
    PAYMENT_PROVIDER_TOKEN: Optional[SecretStr] = Field(
        None, env="PAYMENT_TOKEN")

    @property
    def bot_token_str(self) -> str:
        return self.BOT_TOKEN.get_secret_value()

    # Пути
    BASE_DIR: Path = Path(__file__).parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"

    # Валидатор
    @validator("LOGS_DIR")
    def create_dirs(cls, v):
        v.mkdir(exist_ok=True, parents=True)
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

db_settings = DatabaseSettings()
app_settings = AppSettings()
redis_settings = RedisSettings()