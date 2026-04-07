import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CURRENT_SEASON = os.environ.get("CURRENT_SEASON", "2026")

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_BASE_DIR / 'instance' / 'nba.sqlite'}",
    )


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:////home/nba/instance/nba.sqlite"
    )
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    RATELIMIT_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
