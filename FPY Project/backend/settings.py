from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    EMAIL_FROM: str
    EMAIL_PASSWORD: str
    SMTP_SERVER: str
    SMTP_PORT: int

    class Config:
        env_file = ".env"
        extra = "allow"  # ✅ allow extra keys like GEMINI_API_KEY

settings = Settings()
