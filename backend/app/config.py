
import json
from typing import Any

from pydantic import Field, field_validator, model_validator
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
    META_USE_ACCOUNT_ATTRIBUTION_SETTING: bool = Field(
        default=True,
        description="Whether to query Insights using the ad account attribution setting"
    )
    
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
    TELEGRAM_ADMIN_CHAT_ID: int | str | None = Field(
        default=None,
        description="Optional admin Telegram chat ID for critical error alerts and stalled run notifications"
    )
    
    # Google Service Account
    GOOGLE_SERVICE_ACCOUNT_JSON: str | None = None
    GOOGLE_SERVICE_ACCOUNT_EMAIL: str | None = None
    
    # CORS: Explicit origins required when allow_credentials=True
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost",
            "https://localhost",
            "http://localhost:80",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://127.0.0.1:80",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origin URLs"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("["):
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            return [i.strip() for i in v_clean.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [
            "http://localhost",
            "https://localhost",
            "http://localhost:80",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://127.0.0.1:80",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]

    @model_validator(mode="after")
    def validate_cors_security(self) -> "Settings":
        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "Insecure CORS configuration: Wildcard '*' in CORS_ORIGINS is forbidden "
                "when allow_credentials=True (or in production). Specify explicit origin URLs (e.g. 'https://app.example.com')."
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
