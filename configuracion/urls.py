from django.urls import path
from . import views

urlpatterns = [
    path('', views.configuracion_view, name='configuracion'),
    path('probar-conexion/', views.probar_conexion_neon, name='probar_conexion_neon'),
]