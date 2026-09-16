"""
views.py - Vistas y API protegidas por @admin_required.
"""
import json

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from usuario.decorators import admin_required

from .db_tester import DatabaseConnectionTester
from .forms import ConmutadorDBForm, ParametrosSistemaForm, PerfilDatabaseForm
from .manager import ConfigurationManager
from .schemas import DatabaseDriver, DatabaseProfile, DatabaseTarget

cfg_mgr = ConfigurationManager()


@admin_required
def panel_configuracion_view(request):
    """Renderiza el panel de control de configuración del sistema."""
    if request.method == "POST":
        accion = request.POST.get("accion")

        # 1. Alternar Base de Datos (Local <-> Cloud)
        if accion == "conmutar_db":
            form = ConmutadorDBForm(request.POST)
            if form.is_valid():
                target = DatabaseTarget(form.cleaned_data["target"])
                test_first = form.cleaned_data["test_first"]
                ok, msg = cfg_mgr.switch_target(target, test_first=test_first)
                if ok:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            return redirect("configuracion:panel")

        # 2. Guardar perfil Cloud
        elif accion == "guardar_cloud_db":
            form = PerfilDatabaseForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                cfg_mgr.config.cloud_db.driver = DatabaseDriver(cd["driver"])
                cfg_mgr.config.cloud_db.host = cd["host"]
                cfg_mgr.config.cloud_db.port = cd["port"]
                cfg_mgr.config.cloud_db.name = cd["name"]
                cfg_mgr.config.cloud_db.user = cd["user"]
                if cd["password"]:
                    cfg_mgr.config.cloud_db.password = cd["password"]
                cfg_mgr.config.cloud_db.ssl_mode = cd["ssl_mode"]
                cfg_mgr.save()
                messages.success(request, "Perfil de base de datos Cloud actualizado.")
            else:
                for f, errs in form.errors.items():
                    for err in errs:
                        messages.error(request, f"{f}: {err}")
            return redirect("configuracion:panel")

        # 3. Guardar parámetros generales
        elif accion == "guardar_sistema":
            form = ParametrosSistemaForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                cfg_mgr.config.system.debug = cd["debug"]
                cfg_mgr.config.system.log_level = cd["log_level"]
                cfg_mgr.config.system.timezone = cd["timezone"]
                cfg_mgr.config.system.language_code = cd["language_code"]
                cfg_mgr.config.system.currency_symbol = cd["currency_symbol"]
                cfg_mgr.config.system.storage_driver = cd["storage_driver"]
                cfg_mgr.save()
                messages.success(request, "Parámetros del sistema actualizados.")
            else:
                for f, errs in form.errors.items():
                    for err in errs:
                        messages.error(request, f"{f}: {err}")
            return redirect("configuracion:panel")

    context = {
        "config": cfg_mgr.config,
        "active_target": cfg_mgr.config.active_target.value,
        "local_db": cfg_mgr.config.local_db,
        "cloud_db": cfg_mgr.config.cloud_db,
        "system": cfg_mgr.config.system,
    }
    return render(request, "configuracion/configuracion.html", context)


@admin_required
@require_POST
def api_test_connection(request):
    """Endpoint AJAX para validar credenciales en vivo antes de guardar."""
    try:
        data = json.loads(request.body)
        profile = DatabaseProfile(
            driver=DatabaseDriver(data.get("driver", "postgresql")),
            host=data.get("host", "localhost"),
            port=int(data.get("port", 5432)),
            name=data.get("name", "postgres"),
            user=data.get("user", ""),
            password=data.get("password", "") or (cfg_mgr.config.cloud_db.password if data.get("target") == "cloud" else ""),
            ssl_mode=data.get("ssl_mode", "require"),
            timeout_sec=int(data.get("timeout_sec", 5)),
        )
        ok, msg, latency = DatabaseConnectionTester.test_profile(profile, cfg_mgr.base_dir)
        return JsonResponse({"success": ok, "message": msg, "latency_ms": latency}, status=200 if ok else 400)
    except Exception as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=400)


@admin_required
@require_GET
def descargar_backup_env(request):
    """Genera y descarga el archivo .env.backup."""
    content = cfg_mgr.generate_env_backup()
    res = HttpResponse(content, content_type="text/plain; charset=utf-8")
    res["Content-Disposition"] = 'attachment; filename=".env.backup"'
    return res


@admin_required
@require_GET
def descargar_config_json(request):
    """Exporta y descarga el archivo JSON de configuración del sistema."""
    include_pw = request.GET.get("include_passwords", "false").lower() == "true"
    content = cfg_mgr.export_json(include_passwords=include_pw)
    res = HttpResponse(content, content_type="application/json; charset=utf-8")
    res["Content-Disposition"] = 'attachment; filename="system_configuration.json"'
    return res
