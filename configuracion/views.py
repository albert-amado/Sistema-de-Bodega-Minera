"""
views.py - Configuración del sistema (cambio de base de datos Local <-> Nube).

Fuente única de verdad: system_configuration.json (ConfigurationManager).
Las bases Local y Nube son INDEPENDIENTES: cambiar de entorno NO copia datos.
Solo los botones manuales de sincronización copian datos (y reemplazan el destino).
"""
import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from usuario.decorators import admin_required

from .db_tester import DatabaseConnectionTester
from .manager import ConfigurationManager
from .schemas import DatabaseTarget

logger = logging.getLogger(__name__)


def _bd_en_uso() -> str:
    """'nube' si este proceso está conectado a PostgreSQL, 'local' si es SQLite."""
    return "nube" if connection.vendor == "postgresql" else "local"


def _forzar_recarga():
    """Toca settings.py para que runserver reinicie y vuelva a leer el JSON.
    En producción (gunicorn, etc.) hay que reiniciar el servicio."""
    path = Path(settings.BASE_DIR) / "core" / "settings.py"
    if path.exists():
        path.touch()


@admin_required
def configuracion_view(request):
    almacenamiento_actual = _bd_en_uso()

    if request.method == "POST":
        accion = request.POST.get("accion", "").strip()

        # ── Botón manual: Subir todo de Local a Nube (REEMPLAZA la nube) ──
        if accion == "sincronizar_local_a_nube":
            try:
                from migrar_db import migrate_local_to_cloud
                migrate_local_to_cloud()
                messages.success(request, "Sincronización exitosa: los datos locales (SQLite) se subieron a la Nube (Neon PostgreSQL).")
            except Exception as e:
                logger.exception("Error subiendo datos a la nube")
                messages.error(request, f"Error al subir datos a la nube: {e}")
            return redirect("configuracion")

        # ── Botón manual: Descargar todo de Nube a Local (REEMPLAZA lo local) ──
        if accion == "sincronizar_nube_a_local":
            try:
                from migrar_db import migrate as run_db_migration
                run_db_migration()
                messages.success(request, "Sincronización exitosa: los datos de la Nube (Neon PostgreSQL) se descargaron a Local (SQLite).")
            except Exception as e:
                logger.exception("Error descargando datos de la nube")
                messages.error(request, f"Error al descargar datos de la nube: {e}")
            return redirect("configuracion")

        # ── Cambio de base de datos activa (SIN copiar datos) ──
        almacenamiento = request.POST.get("almacenamiento", "").strip()

        if almacenamiento not in ("local", "nube"):
            messages.error(request, "Opción de almacenamiento no válida.")
            return redirect("configuracion")

        if almacenamiento == almacenamiento_actual:
            messages.info(request, "Ya estás usando esa base de datos.")
            return redirect("configuracion")

        nombre_bd = "Local (SQLite)" if almacenamiento == "local" else "Nube (Neon PostgreSQL)"
        destino_clave = "cloud" if almacenamiento == "nube" else "local"

        # 1) Dejar lista la base de destino: solo crea tablas (migraciones), no copia datos
        try:
            from migrar_db import preparar_base
            preparar_base(destino_clave)
        except Exception as e:
            logger.exception("Error al preparar la base de destino")
            messages.error(
                request,
                f"No se cambió la base de datos. No se pudo preparar {nombre_bd}: {e}",
            )
            return redirect("configuracion")

        # 2) Guardar el cambio donde settings.py realmente lo lee (el JSON)
        manager = ConfigurationManager(base_dir=settings.BASE_DIR)
        destino = DatabaseTarget.CLOUD if almacenamiento == "nube" else DatabaseTarget.LOCAL
        ok, msg = manager.switch_target(destino, test_first=True)
        if not ok:
            messages.error(request, msg)
            return redirect("configuracion")

        # 3) Reiniciar para que Django use la nueva conexión.
        #    Se cierra la sesión porque las sesiones viven en la base de datos.
        _forzar_recarga()
        request.session.flush()
        messages.success(
            request,
            f"Base de datos cambiada a {nombre_bd}. Inicia sesión nuevamente.",
        )
        return redirect("login")

    class Config:
        pass

    config = Config()
    config.almacenamiento = almacenamiento_actual
    return render(request, "configuracion.html", {"config": config})


@admin_required
@require_GET
def probar_conexion_neon(request):
    """Prueba la conexión a la nube con el perfil guardado en el JSON."""
    try:
        manager = ConfigurationManager(base_dir=settings.BASE_DIR)
        ok, msg, _ = DatabaseConnectionTester.test_profile(
            manager.config.cloud_db, settings.BASE_DIR
        )
        return JsonResponse({"ok": ok, "error": "" if ok else msg})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})