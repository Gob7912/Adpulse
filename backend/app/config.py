
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "AdPulse"

class Settings(BaseSettings):
    APP_NAME: str = APP_NAME
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://adpulse:adpulse@db:5432/adpulse",
        description="Async database connection URL"
    )
    
    # Auth & Security
    SECRET_KEY: str = Field(
        default="super-secret-adpulse-jwt-key-change-in-production-min32chars!",
        description="JWT signing secret key"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALLOW_REGISTRATION: bool = True
    
    # Fernet encryption key for Meta tokens (32 url-safe base64-encoded bytes)
    # Default provided for out-of-the-box local testing, overridden in .env
    ENCRYPTION_KEY: str = Field(
        default="RXTngY_mhqpVeoaAoKtb7q11yY_4CLFo7IwLIp0HqXI=",
        description="Fernet symmetric encryption key"
    )
    
    # Meta Graph API
    META_GRAPH_API_VERSION: str = Field(default="v21.0", description="Supported Meta Marketing / Graph API Version")
    
    @property
    def META_GRAPH_API_BASE(self) -> str:
        version = self.META_GRAPH_API_VERSION.strip()
        if not version.startswith("v"):
            version = f"v{version}"
        return f"https://graph.facebook.com/{version}"
    
    # Report timing
    FINAL_DATA_DELAY_HOURS: int = 6
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = "AdPulseBot"
    TELEGRAM_WEBHOOK_URL: str | None = None
    
    # Google Service Account
    GOOGLE_SERVICE_ACCOUNT_JSON: str | None = None
    GOOGLE_SERVICE_ACCOUNT_EMAIL: str | None = None
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
