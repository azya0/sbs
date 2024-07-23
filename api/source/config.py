from functools import lru_cache

from pydantic import PostgresDsn, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class Settings(BaseSettings):
    load_dotenv()
    
    DEBUG: bool

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    SQLALCHEMY_URL: str | None = None

    @field_validator('POSTGRES_HOST')
    @classmethod
    def validate_db_host(cls, value: str, info: FieldValidationInfo):
        if info.data["DEBUG"]:
            return 'localhost'
        return value

    @field_validator('SQLALCHEMY_URL')
    @classmethod
    def validate_sqlalchemy_url(cls, value: str | None, info: FieldValidationInfo):
        if isinstance(value, str):
            return value

        return str(PostgresDsn.build(
            scheme='postgresql+asyncpg',
            username=info.data["POSTGRES_USER"],
            password=info.data["POSTGRES_PASSWORD"],
            host=info.data["POSTGRES_HOST"],
            port=info.data["POSTGRES_PORT"],
            path=info.data["POSTGRES_DB"],
        ))


@lru_cache
def get_settings() -> Settings:
    return Settings()
