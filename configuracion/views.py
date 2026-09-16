import re
from pathlib import Path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from usuario.decorators import admin_required


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _leer_env(clave: str, default: str = "") -> str:
    """Lee el valor actual de una clave en el .env."""
    if not ENV_PATH.exists():
        return default
    contenido = ENV_PATH.read_text(encoding="utf-8")
    patron = re.compile(rf"^{re.escape(clave)}\s*=\s*(.+)$", re.MULTILINE)
    match = patron.search(contenido)
    return match.group(1).strip() if match else default


def _actualizar_env(clave: str, valor: str):
    """Reemplaza o agrega una clave en el archivo .env."""
    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"{clave}={valor}\n", encoding="utf-8")
        return

    contenido = ENV_PATH.read_text(encoding="utf-8")
    patron = re.compile(rf"^{re.escape(clave)}\s*=.*$", re.MULTILINE)

    if patron.search(contenido):
        nuevo = patron.sub(f"{clave}={valor}", contenido)
    else:
        nuevo = contenido.rstrip("\n") + f"\n{clave}={valor}\n"

    ENV_PATH.write_text(nuevo, encoding="utf-8")


def _forzar_recarga():
    """Toca settings.py y views.py para forzar recarga del runserver."""
    base = Path(__file__).resolve().parent.parent
    for path in [
        base / "core" / "settings.py",
        Path(__file__).resolve(),
    ]:
        if path.exists():
            path.touch()


@admin_required
def configuracion_view(request):
    almacenamiento_actual = _leer_env("DB_ENGINE", default="nube")

    if request.method == "POST":
        accion = request.POST.get("accion", "").strip()

        # ── Botón manual: Subir todo de Local a Nube ──
        if accion == "sincronizar_local_a_nube":
            try:
                from migrar_db import migrate_local_to_cloud
                migrate_local_to_cloud()
                messages.success(request, " Sincronización exitosa: Todos los datos locales (SQLite) se han subido a la Nube (Neon PostgreSQL).")
            except Exception as e:
                messages.error(request, f"Error al subir datos a la nube: {e}")
            return redirect("configuracion")

        # ── Botón manual: Descargar todo de Nube a Local ──
        elif accion == "sincronizar_nube_a_local":
            try:
                from migrar_db import migrate as run_db_migration
                run_db_migration()
                messages.success(request, " Sincronización exitosa: Todos los datos de la Nube (Neon PostgreSQL) se han descargado a Local (SQLite).")
            except Exception as e:
                messages.error(request, f"Error al descargar datos de la nube: {e}")
            return redirect("configuracion")

        # ── Cambio de Entorno Activo (con sincronización automática) ──
        almacenamiento = request.POST.get("almacenamiento", "nube")
        sincronizado_ok = False

        if almacenamiento == "local" and almacenamiento_actual == "nube":
            try:
                from migrar_db import migrate as run_db_migration
                run_db_migration()
                sincronizado_ok = True
            except Exception as e:
                messages.error(
                    request,
                    f"Error al sincronizar datos desde la nube: {e}."
                )
        elif almacenamiento == "nube" and almacenamiento_actual == "local":
            try:
                from migrar_db import migrate_local_to_cloud
                migrate_local_to_cloud()
                sincronizado_ok = True
            except Exception as e:
                messages.error(
                    request,
                    f"Error al sincronizar datos hacia la nube: {e}."
                )
        else:
            sincronizado_ok = True

        _actualizar_env("DB_ENGINE", almacenamiento)
        _forzar_recarga()

        nombre_bd = "Local (SQLite)" if almacenamiento == "local" else "Nube (Neon PostgreSQL)"

        if sincronizado_ok:
            messages.success(
                request,
                f"Base de datos activa cambiada a {nombre_bd} y sincronizada exitosamente."
            )
            return redirect("home")
        else:
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
    context = {"config": config}
    return render(request, "configuracion.html", context)


@admin_required
@require_GET
def probar_conexion_neon(request):
    try:
        import psycopg2
        import environ
        env = environ.Env()
        environ.Env.read_env(settings.BASE_DIR / ".env")

        conn = psycopg2.connect(
            dbname=env("DB_NAME", default=""),
            user=env("DB_USER", default=""),
            password=env("DB_PASSWORD", default=""),
            host=env("DB_HOST", default=""),
            port=env("DB_PORT", default="5432"),
            connect_timeout=5,
            sslmode="require",
        )
        conn.close()
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})
