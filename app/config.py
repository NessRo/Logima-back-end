from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str  # no default here
    SQLALCHEMY_ECHO: bool = False  # default is OK here
    SECRET_KEY: str
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    ENV: str = "dev"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()