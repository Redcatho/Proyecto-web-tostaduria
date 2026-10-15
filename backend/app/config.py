import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def normalize_database_url(database_url: str | None) -> str | None:
    """Adapt provider PostgreSQL URLs to SQLAlchemy's psycopg dialect."""
    if not database_url:
        return None
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


class Config:
    ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv("REDIS_URL")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    OBJECT_STORAGE_ENDPOINT = os.getenv("OBJECT_STORAGE_ENDPOINT")
    OBJECT_STORAGE_BUCKET = os.getenv("OBJECT_STORAGE_BUCKET")
    OBJECT_STORAGE_ACCESS_KEY_ID = os.getenv("OBJECT_STORAGE_ACCESS_KEY_ID")
    OBJECT_STORAGE_SECRET_ACCESS_KEY = os.getenv("OBJECT_STORAGE_SECRET_ACCESS_KEY")
    OBJECT_STORAGE_REGION = os.getenv("OBJECT_STORAGE_REGION", "auto")
    PAYMENT_PROOF_MAX_BYTES = int(os.getenv("PAYMENT_PROOF_MAX_BYTES", str(10 * 1024 * 1024)))
    PAYMENT_PROOF_SIGNED_URL_TTL_SECONDS = int(os.getenv("PAYMENT_PROOF_SIGNED_URL_TTL_SECONDS", "900"))
    PRODUCT_IMAGE_ENDPOINT = os.getenv("PRODUCT_IMAGE_ENDPOINT")
    PRODUCT_IMAGE_BUCKET = os.getenv("PRODUCT_IMAGE_BUCKET")
    PRODUCT_IMAGE_MAX_BYTES = int(os.getenv("PRODUCT_IMAGE_MAX_BYTES", str(5 * 1024 * 1024)))
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    PLATFORM_NAME = os.getenv("PLATFORM_NAME", "Tostaduria")
    PLATFORM_ADDRESS = os.getenv("PLATFORM_ADDRESS", "")
    PLATFORM_PHONE = os.getenv("PLATFORM_PHONE", "")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    BCV_RATE_URL = os.getenv("BCV_RATE_URL")
    FALLBACK_BCV_RATE = os.getenv("FALLBACK_BCV_RATE")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = ENV == "production"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = "200 per hour"

    @staticmethod
    def validate(config: dict) -> None:
        required = ("SECRET_KEY", "JWT_SECRET_KEY", "SQLALCHEMY_DATABASE_URI")
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")
