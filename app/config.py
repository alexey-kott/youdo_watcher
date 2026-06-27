from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict


class BaseSettings(PydanticBaseSettings):
    class Config:
        env_file: str = ".env"
        extra = "allow"


class AppSettings(BaseSettings):
    QUERIES_FILE: str = "queries.yaml"
    DELAY: int = 10

    model_config = SettingsConfigDict(
        env_prefix="APP_",
    )


class Watcher(BaseSettings):
    headless: bool = True

    model_config = SettingsConfigDict(
        env_prefix="WATCHER_",
    )


class TelegramSettings(BaseSettings):
    BOT_TOKEN: str
    DEST_CHANNEL_ID: int

    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
    )


class RedisSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 6379
    tasks_db: int = 1

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
    )

    @property
    def URL(self):
        return f"redis://{self.host}:{self.port}"


class Config(BaseSettings):

    app: AppSettings
    telegram: TelegramSettings
    redis: RedisSettings
    watcher: Watcher

    @classmethod
    def create(cls):
        return cls(
            app=AppSettings(),
            telegram=TelegramSettings(),
            redis=RedisSettings(),
            watcher=Watcher(),
        )

config = Config.create()