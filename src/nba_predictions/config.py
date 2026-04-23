import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BALLDONTLIE_API_KEY = os.environ.get("BALL_DONT_LIE_API_KEY", "")

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
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    RATELIMIT_ENABLED = False
    LOGIN_DISABLED = False  # keep auth active but disable session protection below

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # "strong" protection requires _id in session; disable for tests that
        # inject sessions manually via session_transaction()
        from .extensions import login_manager
        login_manager.session_protection = None


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
