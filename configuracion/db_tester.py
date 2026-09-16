"""
db_tester.py - Comprobador de conectividad en vivo sin alterar el runtime activo.
"""
import logging
import time

from .schemas import DatabaseDriver, DatabaseProfile

logger = logging.getLogger("configuracion.tester")


class DatabaseConnectionTester:
    @staticmethod
    def test_profile(profile: DatabaseProfile, base_dir=None) -> tuple[bool, str, float]:
        """
        Prueba la conexión contra el motor objetivo.
        Retorna: (Éxito [bool], Mensaje descriptivo [str], Latencia ms [float])
        """
        start = time.perf_counter()
        timeout = profile.timeout_sec

        try:
            if profile.driver == DatabaseDriver.SQLITE:
                import sqlite3
                path = str(base_dir / profile.name) if (base_dir and not profile.name.startswith("/")) else profile.name
                conn = sqlite3.connect(path, timeout=timeout)
                cur = conn.cursor()
                cur.execute("SELECT 1;")
                conn.close()

            elif profile.driver == DatabaseDriver.POSTGRESQL:
                try:
                    import psycopg2
                    conn = psycopg2.connect(
                        dbname=profile.name,
                        user=profile.user,
                        password=profile.password,
                        host=profile.host,
                        port=profile.port,
                        sslmode=profile.ssl_mode,
                        connect_timeout=timeout,
                    )
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                    conn.close()
                except ImportError:
                    return False, "Driver 'psycopg2' no está instalado en el entorno Python.", 0.0

            elif profile.driver == DatabaseDriver.MYSQL:
                try:
                    import pymysql
                    conn = pymysql.connect(
                        database=profile.name,
                        user=profile.user,
                        password=profile.password,
                        host=profile.host,
                        port=int(profile.port),
                        connect_timeout=timeout,
                    )
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                    conn.close()
                except ImportError:
                    return False, "Driver 'pymysql' no está instalado en el entorno Python.", 0.0

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return True, f"Conexión exitosa verificada ({latency_ms} ms).", latency_ms

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error("Error al probar conexión: %s", str(exc))
            return False, f"Fallo de conexión ({latency_ms} ms): {exc!s}", latency_ms
