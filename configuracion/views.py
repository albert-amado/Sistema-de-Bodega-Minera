"""
views.py - Configuración del sistema (gestión unificada de base de datos
Local <-> Nube y copias de seguridad en Excel).

Fuente única de verdad: system_configuration.json (ConfigurationManager).
Cada cambio de entorno o sincronización genera automáticamente una copia de
seguridad en Excel dentro de backups/ antes de aplicar la operación.
"""
import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from usuario.decorators import admin_required

from .db_tester import DatabaseConnectionTester
from .excel_backup import (
    exportar_backup_excel,
    importar_backup_excel,
    listar_backups_excel,
)
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


def _crear_respaldo_seguridad_excel() -> tuple[str | None, str | None]:
    """Genera y guarda una copia de seguridad Excel en backups/ antes de operar sobre la BD."""
    try:
        _, filename = exportar_backup_excel(guardar_en_disco=True)
        return filename, None
    except Exception as exc:
        logger.warning("No se pudo generar copia de seguridad preventiva en Excel: %s", exc)
        return None, str(exc)


def _formatear_resumen_importacion(resultado: dict) -> str:
    total_ins = resultado.get("total_insertados", 0)
    total_omi = resultado.get("total_omitidos", 0)
    por_tabla = resultado.get("insertados_por_tabla", {})
    if total_ins == 0:
        return (
            f"La base de datos ya está al día: no faltaba ningún registro "
            f"({total_omi} registros verificados ya existían)."
        )
    detalles = ", ".join(f"{tabla}: +{cant}" for tabla, cant in por_tabla.items())
    return (
        f"Se subieron {total_ins} registro(s) faltante(s) correctamente "
        f"({ dets if (dets := detalles) else '' }). "
        f"Se conservaron intactos {total_omi} registro(s) que ya existían."
    )


@admin_required
def exportar_excel_view(request):
    """Genera y descarga inmediatamente la copia de seguridad en formato Excel (.xlsx)."""
    try:
        xlsx_bytes, filename = exportar_backup_excel(guardar_en_disco=True)
        response = HttpResponse(
            xlsx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.exception("Error al generar la copia de seguridad en Excel")
        messages.error(request, f"No se pudo generar la copia de seguridad en Excel: {e}")
        return redirect("configuracion")


@admin_required
def descargar_backup_guardado_view(request, filename: str):
    """Permite descargar una copia de seguridad .xlsx previamente guardada en backups/."""
    nombre_limpio = Path(filename).name
    ruta = Path(settings.BASE_DIR) / "backups" / nombre_limpio
    if not ruta.exists() or ruta.suffix.lower() != ".xlsx":
        raise Http404("El archivo de copia de seguridad no existe.")
    response = HttpResponse(
        ruta.read_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_limpio}"'
    return response


@admin_required
def configuracion_view(request):
    almacenamiento_actual = _bd_en_uso()

    if request.method == "POST":
        accion = request.POST.get("accion", "").strip()

        # ── 1. Exportar Copia de Seguridad en Excel (.xlsx) ──
        if accion == "exportar_backup_excel":
            return exportar_excel_view(request)

        # ── 2. Importar Copia de Seguridad desde archivo Excel subido (sube lo que falte) ──
        if accion == "importar_backup_excel":
            archivo = request.FILES.get("archivo_excel")
            if not archivo:
                messages.error(request, "Debes seleccionar un archivo Excel (.xlsx) para importar.")
                return redirect("configuracion")
            if not archivo.name.lower().endswith(".xlsx"):
                messages.error(request, "Formato no válido. Selecciona un archivo con extensión .xlsx.")
                return redirect("configuracion")
            try:
                resultado = importar_backup_excel(archivo)
                messages.success(request, _formatear_resumen_importacion(resultado))
            except Exception as e:
                logger.exception("Error importando copia de seguridad desde Excel")
                messages.error(request, f"Error al importar la copia de seguridad Excel: {e}")
            return redirect("configuracion")

        # ── 3. Importar / Restaurar faltantes desde un backup .xlsx guardado en backups/ ──
        if accion == "restaurar_backup_guardado":
            nombre_archivo = Path(request.POST.get("nombre_archivo", "").strip()).name
            ruta = Path(settings.BASE_DIR) / "backups" / nombre_archivo
            if not nombre_archivo or not ruta.exists() or ruta.suffix.lower() != ".xlsx":
                messages.error(request, "El archivo de respaldo seleccionado no existe.")
                return redirect("configuracion")
            try:
                resultado = importar_backup_excel(ruta)
                messages.success(request, _formatear_resumen_importacion(resultado))
            except Exception as e:
                logger.exception("Error restaurando backup guardado en Excel")
                messages.error(request, f"Error al restaurar desde {nombre_archivo}: {e}")
            return redirect("configuracion")

        # ── 4. Botón manual: Subir todo de Local a Nube (con respaldo Excel previo) ──
        if accion == "sincronizar_local_a_nube":
            backup_nombre, _ = _crear_respaldo_seguridad_excel()
            try:
                from migrar_db import migrate_local_to_cloud
                migrate_local_to_cloud()
                detalle_respaldo = f" Respaldo previo guardado: {backup_nombre}." if backup_nombre else ""
                messages.success(
                    request,
                    f"Sincronización exitosa: los datos locales (SQLite) se subieron a la Nube (Neon PostgreSQL).{detalle_respaldo}",
                )
            except Exception as e:
                logger.exception("Error subiendo datos a la nube")
                messages.error(request, f"Error al subir datos a la nube: {e}")
            return redirect("configuracion")

        # ── 5. Botón manual: Descargar todo de Nube a Local (con respaldo Excel previo) ──
        if accion == "sincronizar_nube_a_local":
            backup_nombre, _ = _crear_respaldo_seguridad_excel()
            try:
                from migrar_db import migrate as run_db_migration
                run_db_migration()
                detalle_respaldo = f" Respaldo previo guardado: {backup_nombre}." if backup_nombre else ""
                messages.success(
                    request,
                    f"Sincronización exitosa: los datos de la Nube (Neon PostgreSQL) se descargaron a Local (SQLite).{detalle_respaldo}",
                )
            except Exception as e:
                logger.exception("Error descargando datos de la nube")
                messages.error(request, f"Error al descargar datos de la nube: {e}")
            return redirect("configuracion")

        # ── 6. Cambio unificado de base de datos activa con respaldo Excel automático ──
        almacenamiento = request.POST.get("almacenamiento", "").strip()

        if almacenamiento not in ("local", "nube"):
            messages.error(request, "Opción de almacenamiento no válida.")
            return redirect("configuracion")

        if almacenamiento == almacenamiento_actual:
            messages.info(request, "Ya estás usando esa base de datos.")
            return redirect("configuracion")

        nombre_bd = "Local (SQLite)" if almacenamiento == "local" else "Nube (Neon PostgreSQL)"
        destino_clave = "cloud" if almacenamiento == "nube" else "local"

        # 1) Generar copia de seguridad automática del entorno actual antes del cambio
        backup_nombre, _ = _crear_respaldo_seguridad_excel()

        # 2) Dejar lista la base de destino (migraciones)
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

        # 3) Guardar el cambio donde settings.py realmente lo lee (el JSON)
        manager = ConfigurationManager(base_dir=settings.BASE_DIR)
        destino = DatabaseTarget.CLOUD if almacenamiento == "nube" else DatabaseTarget.LOCAL
        ok, msg = manager.switch_target(destino, test_first=True)
        if not ok:
            messages.error(request, msg)
            return redirect("configuracion")

        # 4) Reiniciar para que Django use la nueva conexión.
        #    Se cierra la sesión porque las sesiones viven en la base de datos.
        _forzar_recarga()
        request.session.flush()
        detalle_respaldo = (
            f" Se generó respaldo automático ({backup_nombre}) en backups/."
            if backup_nombre
            else ""
        )
        messages.success(
            request,
            f"Base de datos cambiada a {nombre_bd}.{detalle_respaldo} Inicia sesión nuevamente.",
        )
        return redirect("login")

    class Config:
        pass

    config = Config()
    config.almacenamiento = almacenamiento_actual
    backups_excel = listar_backups_excel()
    return render(
        request,
        "configuracion.html",
        {
            "config": config,
            "backups_excel": backups_excel,
        },
    )


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
