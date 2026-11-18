"""
migrar_db.py - Sincroniza los datos entre SQLite (local) y Neon PostgreSQL (nube).

Ubicación: raíz del proyecto, junto a manage.py.

Funciones que usa configuracion/views.py:
    migrate_local_to_cloud()  -> copia Local -> Nube
    migrate()                 -> copia Nube  -> Local

Qué hace al copiar origen -> destino:
    0. Verifica que todas las apps con modelos tengan sus migraciones.
    1. Prueba la conexión a las dos bases.
    2. Aplica las migraciones en el destino (crea las tablas si faltan).
    3. Guarda un respaldo del destino en backups/ (por si algo sale mal).
    4. Vuelca los datos del origen.
    5. Vacía el destino y carga los datos del origen.
       Si la carga falla, restaura el respaldo.

OJO: el destino queda IGUAL al origen (se reemplaza todo su contenido).

Uso por terminal (desde la raíz del proyecto):
    python migrar_db.py subir                        # Local -> Nube
    python migrar_db.py bajar                        # Nube  -> Local
    python migrar_db.py comparar                     # Cuenta registros en ambas (solo lee)
    python migrar_db.py preparar-local               # Crea/actualiza las tablas de SQLite (sin datos)
    python migrar_db.py preparar-nube                # Crea/actualiza las tablas de Neon (sin datos)
    python migrar_db.py subir --reiniciar-destino    # Local -> Nube, borrando antes
                                                     # el esquema de Neon (úsalo si el
                                                     # historial de migraciones de Neon
                                                     # está desincronizado)
"""
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Tablas que Django recrea solo o que no tiene sentido copiar
EXCLUIR = ["contenttypes", "auth.permission", "sessions", "admin.logentry"]

ALIAS = {"local": "sync_local", "cloud": "sync_cloud"}


# ─────────────────────────────────────────────────────────────
#  Utilidades internas
# ─────────────────────────────────────────────────────────────
def _perfiles():
    """Lee los dos perfiles (local y nube) desde system_configuration.json."""
    from configuracion.manager import ConfigurationManager
    from django.conf import settings

    mgr = ConfigurationManager(base_dir=settings.BASE_DIR)
    return {
        "local": mgr.config.local_db.to_django_dict(mgr.base_dir),
        "cloud": mgr.config.cloud_db.to_django_dict(mgr.base_dir),
    }


def _verificar_migraciones():
    """Evita errores raros más adelante: toda app con modelos necesita migraciones."""
    from django.apps import apps
    from django.core.management import call_command
    from django.db.migrations.loader import MigrationLoader

    sin_migraciones = sorted(
        label
        for label in MigrationLoader(None).unmigrated_apps
        if list(apps.get_app_config(label).get_models())
    )
    if sin_migraciones:
        raise RuntimeError(
            "Estas apps tienen modelos pero no tienen migraciones: "
            f"{', '.join(sin_migraciones)}. "
            f"Ejecuta: python manage.py makemigrations {' '.join(sin_migraciones)}"
        )

    try:
        call_command("makemigrations", check=True, dry_run=True, verbosity=0)
    except SystemExit:
        raise RuntimeError(
            "Hay cambios en los modelos que aún no tienen migración. "
            "Ejecuta: python manage.py makemigrations"
        )
    except Exception as exc:
        logger.warning("No se pudo verificar si hay migraciones pendientes: %s", exc)


def _registrar(alias, cfg):
    """Registra una conexión extra en Django con los valores por defecto necesarios."""
    from django.db import connections

    cfg = dict(cfg)
    defaults = {
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "OPTIONS": {},
        "TIME_ZONE": None,
        "NAME": "",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
        "TEST": {},
    }
    for clave, valor in defaults.items():
        cfg.setdefault(clave, valor)
    if "postgresql" in str(cfg.get("ENGINE", "")):
        # Necesario con el pooler de Neon (PgBouncer)
        cfg.setdefault("DISABLE_SERVER_SIDE_CURSORS", True)
    connections.databases[alias] = cfg


def _liberar(*aliases):
    """Cierra y olvida las conexiones temporales."""
    from django.db import connections

    for alias in aliases:
        try:
            connections[alias].close()
        except Exception:
            pass
        try:
            del connections[alias]
        except Exception:
            pass
        connections.databases.pop(alias, None)


def _probar(alias, nombre):
    from django.db import connections

    try:
        with connections[alias].cursor() as cur:
            cur.execute("SELECT 1")
    except Exception as exc:
        raise RuntimeError(f"No se pudo conectar a la base de {nombre}: {exc}") from exc


def _volcar(alias, ruta):
    """Exporta una base completa a un JSON (UTF-8). Si falla, borra el archivo a medias."""
    from django.core.management import call_command

    try:
        with open(ruta, "w", encoding="utf-8") as f:
            call_command(
                "dumpdata",
                database=alias,
                exclude=EXCLUIR,
                use_natural_foreign_keys=True,
                indent=2,
                stdout=f,
            )
    except Exception:
        try:
            Path(ruta).unlink()
        except OSError:
            pass
        raise


def _reiniciar_destino(alias):
    """Borra TODO el esquema 'public' de PostgreSQL y lo recrea vacío."""
    from django.db import connections

    conn = connections[alias]
    if conn.vendor != "postgresql":
        raise RuntimeError(
            "Reiniciar el destino solo está soportado para PostgreSQL (Neon). "
            "Para SQLite, borra db.sqlite3 a mano."
        )
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")


# ─────────────────────────────────────────────────────────────
#  Copia origen -> destino
# ─────────────────────────────────────────────────────────────
def _copiar(origen, destino, reiniciar_destino=False):
    from django.conf import settings
    from django.core.management import call_command
    from django.db.migrations.exceptions import InconsistentMigrationHistory

    perfiles = _perfiles()
    cfg_o, cfg_d = perfiles[origen], perfiles[destino]

    if (cfg_o.get("ENGINE"), str(cfg_o.get("NAME")), cfg_o.get("HOST")) == (
        cfg_d.get("ENGINE"), str(cfg_d.get("NAME")), cfg_d.get("HOST"),
    ):
        raise RuntimeError("El origen y el destino son la misma base de datos.")

    # 0. Antes de tocar nada: migraciones completas
    _verificar_migraciones()

    src, dst = ALIAS[origen], ALIAS[destino]
    _registrar(src, cfg_o)
    _registrar(dst, cfg_d)

    carpeta = Path(settings.BASE_DIR) / "backups"
    carpeta.mkdir(exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    respaldo = carpeta / f"respaldo_{destino}_{sello}.json"
    tiene_respaldo = False

    fd, volcado = tempfile.mkstemp(suffix=".json", prefix="volcado_")
    os.close(fd)

    try:
        _probar(src, origen)
        _probar(dst, destino)

        if reiniciar_destino:
            # Intentar respaldar lo que haya antes de borrar el esquema
            try:
                _volcar(dst, respaldo)
                tiene_respaldo = True
            except Exception as exc:
                logger.warning("No se pudo respaldar el destino antes de reiniciarlo: %s", exc)
            _reiniciar_destino(dst)

        # El destino debe tener las tablas antes de recibir datos
        try:
            call_command("migrate", database=dst, interactive=False, verbosity=0)
        except InconsistentMigrationHistory as exc:
            raise RuntimeError(
                f"El historial de migraciones de la base de {destino} está desincronizado ({exc}). "
                f"Para arreglarlo ejecuta en la terminal: "
                f"python migrar_db.py {'subir' if destino == 'cloud' else 'bajar'} --reiniciar-destino"
            ) from exc

        if not tiene_respaldo:
            _volcar(dst, respaldo)
            tiene_respaldo = True

        _volcar(src, volcado)

        # Reemplazar el contenido del destino
        call_command("flush", database=dst, interactive=False, verbosity=0)
        try:
            call_command("loaddata", volcado, database=dst, verbosity=0)
        except Exception as exc:
            logger.exception("Falló la carga de datos en %s", destino)
            if not tiene_respaldo:
                raise RuntimeError(f"Falló la carga de datos ({exc}) y no hay respaldo.") from exc
            try:
                call_command("flush", database=dst, interactive=False, verbosity=0)
                call_command("loaddata", str(respaldo), database=dst, verbosity=0)
            except Exception:
                logger.exception("Falló también la restauración del respaldo")
                raise RuntimeError(
                    f"Falló la carga ({exc}) y no se pudo restaurar el respaldo automáticamente. "
                    f"El respaldo está en: {respaldo}"
                ) from exc
            raise RuntimeError(
                f"Falló la carga de datos ({exc}). Se restauró el respaldo del destino."
            ) from exc

        logger.info("Sincronización %s -> %s completada. Respaldo: %s", origen, destino, respaldo)
    finally:
        _liberar(src, dst)
        try:
            os.remove(volcado)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────
#  API pública (la usa configuracion/views.py)
# ─────────────────────────────────────────────────────────────
def migrate_local_to_cloud(reiniciar_destino=False):
    """Local (SQLite) -> Nube (Neon PostgreSQL)."""
    _copiar("local", "cloud", reiniciar_destino)


def migrate(reiniciar_destino=False):
    """Nube (Neon PostgreSQL) -> Local (SQLite)."""
    _copiar("cloud", "local", reiniciar_destino)


migrate_cloud_to_local = migrate


def preparar_base(destino):
    """
    Deja lista la base 'local' o 'cloud' para usarla como base activa:
    prueba la conexión y aplica las migraciones (crea las tablas que falten).
    NO copia ni borra datos.
    """
    from django.core.management import call_command
    from django.db.migrations.exceptions import InconsistentMigrationHistory

    _verificar_migraciones()

    alias = ALIAS[destino]
    _registrar(alias, _perfiles()[destino])
    try:
        _probar(alias, destino)
        try:
            call_command("migrate", database=alias, interactive=False, verbosity=0)
        except InconsistentMigrationHistory as exc:
            raise RuntimeError(
                f"El historial de migraciones de la base de {destino} está desincronizado ({exc}). "
                "Si esa base no tiene datos que necesites, reiníciala con: "
                f"python migrar_db.py {'subir' if destino == 'cloud' else 'bajar'} --reiniciar-destino"
            ) from exc
    finally:
        _liberar(alias)


def comparar():
    """Muestra cuántos registros tiene cada modelo en Local y en Nube. Solo lee."""
    from django.apps import apps

    ignorar = {"contenttypes.ContentType", "sessions.Session", "admin.LogEntry", "auth.Permission"}

    perfiles = _perfiles()
    for clave in ("local", "cloud"):
        _registrar(ALIAS[clave], perfiles[clave])

    print(f"{'Modelo':42} {'Local':>8} {'Nube':>8}")
    print("-" * 60)
    try:
        for model in sorted(apps.get_models(), key=lambda m: m._meta.label):
            if model._meta.label in ignorar:
                continue
            conteos = []
            for clave in ("local", "cloud"):
                try:
                    conteos.append(model.objects.using(ALIAS[clave]).count())
                except Exception:
                    conteos.append(None)
            local, nube = conteos
            marca = "" if local == nube else "  <-- distinto"
            print(
                f"{model._meta.label:42} "
                f"{str(local) if local is not None else '—':>8} "
                f"{str(nube) if nube is not None else '—':>8}{marca}"
            )
    finally:
        _liberar(*ALIAS.values())


# ─────────────────────────────────────────────────────────────
#  Uso por terminal
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    accion = args[0] if args else ""
    reiniciar = "--reiniciar-destino" in sys.argv

    if accion == "comparar":
        comparar()
        sys.exit(0)

    if accion in ("preparar-local", "preparar-nube"):
        preparar_base("local" if accion == "preparar-local" else "cloud")
        print("Listo: tablas creadas o actualizadas. No se copiaron datos.")
        sys.exit(0)

    if accion not in ("subir", "bajar"):
        print(
            "Uso: python migrar_db.py subir | bajar [--reiniciar-destino] "
            "| comparar | preparar-local | preparar-nube"
        )
        sys.exit(1)

    if reiniciar:
        destino = "Nube (Neon)" if accion == "subir" else "Local (SQLite)"
        print(f"ATENCIÓN: se va a BORRAR todo el esquema de {destino} y se recreará desde cero.")
        if input("Escribe BORRAR para continuar: ").strip() != "BORRAR":
            print("Cancelado. No se cambió nada.")
            sys.exit(1)

    if accion == "subir":
        migrate_local_to_cloud(reiniciar_destino=reiniciar)
        print("Listo: Local -> Nube.")
    else:
        migrate(reiniciar_destino=reiniciar)
        print("Listo: Nube -> Local.")