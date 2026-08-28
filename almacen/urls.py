from django.urls import path
from .views import crear_estante, vista_estantes, vista_almacenes, detalle_almacen

urlpatterns = [
    path('estantes/', vista_estantes, name='estantes'),
    path('estante/crear/', crear_estante, name='crear_estante'),
    path('almacenes/', vista_almacenes, name='almacenes'),
    path('almacenes/<int:pk>/', detalle_almacen, name='detalle_almacen'),
]