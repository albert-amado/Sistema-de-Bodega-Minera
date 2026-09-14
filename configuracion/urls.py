from django.urls import path
from . import views

app_name = "configuracion"

urlpatterns = [
    path("", views.panel_configuracion_view, name="panel"),
    path("api/test-connection/", views.api_test_connection, name="api_test_connection"),
    path("exportar/env/", views.descargar_backup_env, name="exportar_env"),
    path("exportar/json/", views.descargar_config_json, name="exportar_json"),
]
