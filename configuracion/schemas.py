"""
schemas.py - Modelos de datos tipados y enumeraciones del módulo de configuración.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DatabaseDriver(str, Enum):
    SQLITE = "sqlite3"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class DatabaseTarget(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class StorageDriver(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class DatabaseProfile:
    """Perfil individual de conexión a Base de Datos."""
    driver: DatabaseDriver
    host: str = "localhost"
    port: int = 5432
    name: str = "db.sqlite3"
    user: str = ""
    password: str = ""
    ssl_mode: str = "prefer"  # 'disable', 'prefer', 'require', 'verify-full'
    timeout_sec: int = 5
    conn_max_age: int = 600

    def to_django_dict(self, base_dir=None) -> dict[str, Any]:
        """Transforma el perfil a la estructura nativa de DATABASES['default'] de Django."""
        if self.driver == DatabaseDriver.SQLITE:
            db_path = str(base_dir / self.name) if (base_dir and not self.name.startswith("/")) else self.name
            return {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": db_path,
                "CONN_MAX_AGE": self.conn_max_age,
            }

        engine_map = {
            DatabaseDriver.POSTGRESQL: "django.db.backends.postgresql",
            DatabaseDriver.MYSQL: "django.db.backends.mysql",
        }

        cfg = {
            "ENGINE": engine_map.get(self.driver, "django.db.backends.sqlite3"),
            "NAME": self.name,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": str(self.port),
            "CONN_MAX_AGE": self.conn_max_age,
            "OPTIONS": {},
        }

        if self.driver == DatabaseDriver.POSTGRESQL and self.ssl_mode != "disable":
            cfg["OPTIONS"]["sslmode"] = self.ssl_mode
            cfg["OPTIONS"]["connect_timeout"] = self.timeout_sec

        return cfg


@dataclass
class SystemSettings:
    """Configuración general del entorno y aplicación."""
    debug: bool = True
    log_level: LogLevel = LogLevel.INFO
    timezone: str = "America/Bogota"
    language_code: str = "es-co"
    currency_symbol: str = "COP ($)"
    date_format: str = "%d/%m/%Y"
    storage_driver: StorageDriver = StorageDriver.LOCAL
    media_path: str = "media"
    cloud_bucket_name: str | None = None


@dataclass
class GlobalConfig:
    """Contenedor principal con perfiles Local, Cloud y configuración general."""
    active_target: DatabaseTarget = DatabaseTarget.LOCAL
    local_db: DatabaseProfile = field(default_factory=lambda: DatabaseProfile(driver=DatabaseDriver.SQLITE, name="db.sqlite3"))
    cloud_db: DatabaseProfile = field(default_factory=lambda: DatabaseProfile(
        driver=DatabaseDriver.POSTGRESQL,
        host="aws-0-us-east-1.pooler.supabase.com",
        port=6543,
        name="postgres",
        user="postgres.user",
        ssl_mode="require",
        timeout_sec=10
    ))
    system: SystemSettings = field(default_factory=SystemSettings)
