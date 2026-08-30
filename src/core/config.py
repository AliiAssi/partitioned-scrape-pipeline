from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mongo_uri: str = Field(default="mongodb://localhost:27017")
    mongo_database: str = Field(default="wrc")
    landing_collection: str = Field(default="landing_decisions")
    curated_collection: str = Field(default="curated_decisions")

    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: SecretStr = Field(default=SecretStr("minioadmin"))
    minio_secret_key: SecretStr = Field(default=SecretStr("minioadmin"))
    minio_secure: bool = Field(default=False)
    landing_bucket: str = Field(default="landing")
    curated_bucket: str = Field(default="curated")

    partition_size: Literal["daily", "weekly", "monthly"] = Field(default="monthly")

    robots_obey: bool = Field(default=False)
    user_agent: str = Field(default="wrc-pipeline/1.0")
    concurrent_requests_per_domain: int = Field(default=8, ge=1, le=32) # "no more than 8" controls how many run at once
    download_delay: float = Field(default=0.0, ge=0.0)
    download_timeout: int = Field(default=120, ge=1)
    retry_times: int = Field(default=3, ge=0, le=10)
    # scrapy's adaptive rhythm: it times each response and derives the delay itself, instead of us guessing one.
    autothrottle_enabled: bool = Field(default=True)
    # controls the gap between starts on every response ("aim for about 6 on average")
    autothrottle_target_concurrency: float = Field(default=6.0, gt=0)

    storage_retry_attempts: int = Field(default=3, ge=1, le=10)
    storage_retry_backoff_seconds: float = Field(default=0.5, gt=0)

    crawl_workspace_dir: str = Field(default="/tmp/wrc_pipeline_crawls") # where the subprocess drops metadata and documents for the parent to read.
    log_level: str = Field(default="INFO")

    @field_validator("log_level")
    @classmethod
    def _uppercase_log_level(cls, value: str) -> str:
        # used for accepting "info" as readily as "INFO"
        return value.upper()

    @property
    def minio_access_key_value(self) -> str:
        # used for handing the raw key to the minio client without leaking it elsewhere
        return self.minio_access_key.get_secret_value()

    @property
    def minio_secret_key_value(self) -> str:
        # used for handing the raw secret to the minio client without leaking it elsewhere
        return self.minio_secret_key.get_secret_value()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # used for making config a singleton so the environment is read exactly once
    return Settings()
