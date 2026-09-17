from django.urls import path
from . import views

app_name = 'configuracion'

urlpatterns = [
    path('', views.configuracion_view, name='panel'),
    path('panel/', views.configuracion_view, name='panel_direct'),
    path('probar-conexion/', views.probar_conexion_neon, name='probar_conexion_neon'),
]



