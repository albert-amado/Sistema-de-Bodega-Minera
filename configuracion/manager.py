"""
manager.py - Gestor de persistencia en JSON, sincronización con .env y exportador de respaldos.
"""
import json
import os
from dataclasses import asdict
from typing import Any

from django.conf import settings

from .db_tester import DatabaseConnectionTester
from .schemas import (
    DatabaseDriver,
    DatabaseProfile,
    DatabaseTarget,
    GlobalConfig,
    LogLevel,
    StorageDriver,
    SystemSettings,
)


class ConfigurationManager:
    CONFIG_FILE_NAME = "system_configuration.json"

    def __init__(self, base_dir=None):
        if base_dir:
            self.base_dir = base_dir
        else:
            try:
                self.base_dir = getattr(settings, "BASE_DIR", os.getcwd())
            except Exception:
                self.base_dir = os.getcwd()

        self.config_path = os.path.join(str(self.base_dir), self.CONFIG_FILE_NAME)
        self.env_path = os.path.join(str(self.base_dir), ".env")
        self.config: GlobalConfig = self.load()

    def load(self) -> GlobalConfig:
        """Carga la configuración persistida o inicializa una con valores por defecto."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._deserialize(data)
            except Exception:
                pass
        return GlobalConfig()

    def save(self) -> None:
        """Guarda la configuración en disco y actualiza el archivo .env."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.config), f, indent=4, ensure_ascii=False)
        self.sync_env_file()

    def get_active_django_db_dict(self) -> dict[str, Any]:
        """Obtiene la configuración lista para asignar a DATABASES['default'] en settings.py."""
        active = self.config.cloud_db if self.config.active_target == DatabaseTarget.CLOUD else self.config.local_db
        return active.to_django_dict(self.base_dir)

    def switch_target(self, target: DatabaseTarget, test_first: bool = True) -> tuple[bool, str]:
        """Alterna entre Local y Cloud con validación de conexión."""
        candidate = self.config.cloud_db if target == DatabaseTarget.CLOUD else self.config.local_db

        if test_first:
            ok, msg, _ = DatabaseConnectionTester.test_profile(candidate, self.base_dir)
            if not ok:
                return False, f"No se pudo cambiar a {target.value.upper()}: {msg}"

        self.config.active_target = target
        self.save()
        return True, f"Origen de datos cambiado con éxito a modo: {target.value.upper()}."

    def export_json(self, include_passwords: bool = False) -> str:
        """Exporta la configuración activa con contraseñas enmascaradas por defecto."""
        raw = asdict(self.config)
        if not include_passwords:
            if raw.get("local_db") and raw["local_db"].get("password"):
                raw["local_db"]["password"] = "********"
            if raw.get("cloud_db") and raw["cloud_db"].get("password"):
                raw["cloud_db"]["password"] = "********"
        return json.dumps(raw, indent=4, ensure_ascii=False)

    def generate_env_backup(self) -> str:
        """Genera el contenido exacto de un archivo .env.backup."""
        active = self.config.cloud_db if self.config.active_target == DatabaseTarget.CLOUD else self.config.local_db
        lines = [
            "# ─────────────────────────────────────────────────────────────",
            "# RESPALDO DE VARIABLES DE ENTORNO (.env.backup)",
            "# Generado por Sistema de Bodega Minera Configuration Manager",
            "# ─────────────────────────────────────────────────────────────",
            f"DB_TARGET={self.config.active_target.value}",
            f"DB_DRIVER={active.driver.value}",
            f"DB_HOST={active.host}",
            f"DB_PORT={active.port}",
            f"DB_NAME={active.name}",
            f"DB_USER={active.user}",
            f"DB_PASSWORD={active.password}",
            f"DB_SSLMODE={active.ssl_mode}",
            f"DEBUG={self.config.system.debug!s}",
            f"LOG_LEVEL={self.config.system.log_level.value}",
            f"TIME_ZONE={self.config.system.timezone}",
            f"LANGUAGE_CODE={self.config.system.language_code}",
            f"STORAGE_DRIVER={self.config.system.storage_driver.value}",
        ]
        return "\n".join(lines) + "\n"

    def sync_env_file(self) -> None:
        """Actualiza el archivo .env raíz del proyecto."""
        try:
            content = self.generate_env_backup()
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    def _deserialize(self, d: dict[str, Any]) -> GlobalConfig:
        loc = d.get("local_db", {})
        cld = d.get("cloud_db", {})
        sys = d.get("system", {})
        return GlobalConfig(
            active_target=DatabaseTarget(d.get("active_target", "local")),
            local_db=DatabaseProfile(
                driver=DatabaseDriver(loc.get("driver", "sqlite3")),
                host=loc.get("host", "localhost"),
                port=int(loc.get("port", 5432)),
                name=loc.get("name", "db.sqlite3"),
                user=loc.get("user", ""),
                password=loc.get("password", ""),
                ssl_mode=loc.get("ssl_mode", "prefer"),
            ),
            cloud_db=DatabaseProfile(
                driver=DatabaseDriver(cld.get("driver", "postgresql")),
                host=cld.get("host", "aws-0-us-east-1.pooler.supabase.com"),
                port=int(cld.get("port", 6543)),
                name=cld.get("name", "postgres"),
                user=cld.get("user", "postgres.user"),
                password=cld.get("password", ""),
                ssl_mode=cld.get("ssl_mode", "require"),
            ),
            system=SystemSettings(
                debug=bool(sys.get("debug", True)),
                log_level=LogLevel(sys.get("log_level", "INFO")),
                timezone=sys.get("timezone", "America/Bogota"),
                language_code=sys.get("language_code", "es-co"),
                currency_symbol=sys.get("currency_symbol", "COP ($)"),
                date_format=sys.get("date_format", "%d/%m/%Y"),
                storage_driver=StorageDriver(sys.get("storage_driver", "local")),
                media_path=sys.get("media_path", "media"),
            )
        )
