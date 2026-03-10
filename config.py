import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://proposal_user:proposal_password@localhost/proposal_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File storage
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    GENERATED_FILES_DIR = os.path.join(BASE_DIR, "generated_files")

    # Health thresholds
    DISK_USAGE_THRESHOLD_PERCENT = float(os.environ.get("DISK_USAGE_THRESHOLD_PERCENT", 80))
    DB_SIZE_THRESHOLD_MB = float(os.environ.get("DB_SIZE_THRESHOLD_MB", 1024))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)

