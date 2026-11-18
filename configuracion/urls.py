from django.urls import path

from . import views

app_name = 'configuracion'

urlpatterns = [
    path('', views.configuracion_view, name='panel'),
    path('panel/', views.configuracion_view, name='panel_direct'),
    path('probar-conexion/', views.probar_conexion_neon, name='probar_conexion_neon'),
    path('exportar-excel/', views.exportar_excel_view, name='exportar_excel'),
    path(
        'descargar-backup/<str:filename>/',
        views.descargar_backup_guardado_view,
        name='descargar_backup_guardado',
    ),
]
