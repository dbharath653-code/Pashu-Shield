import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Pashu-Shield API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./pashu_shield.db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "pashu-shield-super-secret-production-key-2026")
    JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "pashu-shield-refresh-token-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # External integrations
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    NADRES_API_URL: str = os.getenv("NADRES_API_URL", "https://nadres.res.in/api/v1")
    NADRES_API_KEY: str = os.getenv("NADRES_API_KEY", "")
    GOVERNMENT_API_URL: str = os.getenv("GOVERNMENT_API_URL", "https://dahd.nic.in/api/v1")
    GOVERNMENT_API_KEY: str = os.getenv("GOVERNMENT_API_KEY", "")
    WEATHER_API_URL: str = os.getenv("WEATHER_API_URL", "https://api.open-meteo.com/v1")
    
    # Notification Providers
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "mock")
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_SENDER_ID: str = os.getenv("SMS_SENDER_ID", "PASHU")
    
    WHATSAPP_PROVIDER: str = os.getenv("WHATSAPP_PROVIDER", "mock")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "local")
    TRANSLATION_API_KEY: str = os.getenv("TRANSLATION_API_KEY", "")

settings = Settings()
