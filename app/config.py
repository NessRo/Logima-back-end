from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str  # no default here
    SQLALCHEMY_ECHO: bool = False  # default is OK here

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()