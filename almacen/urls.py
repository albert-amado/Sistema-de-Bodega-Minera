from django.urls import path

from .views import crear_estante, detalle_almacen, vista_almacenes, vista_estantes

urlpatterns = [
    path('estantes/', vista_estantes, name='estantes'),
    path('estante/crear/', crear_estante, name='crear_estante'),
    path('almacenes/', vista_almacenes, name='almacenes'),
    path('almacenes/<int:pk>/', detalle_almacen, name='detalle_almacen'),
]