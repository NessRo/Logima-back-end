from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URL: str

    SESSION_SECRET: str
    SECRET_KEY: str

    DATABASE_URL: str  # no default here
    SQLALCHEMY_ECHO: bool = False  # default is OK here
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    ENV: str = "dev"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

