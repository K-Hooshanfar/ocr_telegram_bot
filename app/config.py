from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Admin credentials (seeded on first startup)
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "changeme"

    # JWT
    JWT_SECRET_KEY: str = "change-this-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Google Gemini
    GOOGLE_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
