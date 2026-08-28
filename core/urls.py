from django.contrib import admin
from django.urls import include, path

from prestamo import views as prestamo_views
from almacen import views as almacen_views
from usuario import views as usuario_views
from pagina_principal import views as pagina_principal_views
from herramienta import views as herramienta_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('usuario.urls')),

    # Rutas principales del sistema
    path('pagina_principal/', pagina_principal_views.home_usuario_view, name='pagina_principal'),
    path('inventario/', herramienta_views.inventario_view, name='inventario'),
    path('prestamo/', prestamo_views.prestamo_lista, name='prestamo'),
    path('devoluciones/', prestamo_views.devoluciones_lista, name='devoluciones'),
    path('almacenes/', almacen_views.vista_almacenes, name='almacenes'),
    path('almacen/', almacen_views.vista_almacenes, name='almacen'),
    path('estantes/', almacen_views.vista_estantes, name='estantes'),
    path('usuarios/', usuario_views.lista_usuarios_view, name='lista_usuarios'),

    # Rutas por aplicación
    path('prestamo/', include('prestamo.urls')),
    path('almacen_app/', include('almacen.urls')),
    path('herramienta/', include('herramienta.urls')),

    # Rutas auxiliares de navegación
    path('reportes/', prestamo_views.prestamo_lista, name='reportes'),
    path('configuracion/', prestamo_views.prestamo_lista, name='configuracion'),
    path('api/notificaciones/', prestamo_views.notificaciones_json, name='notificaciones_json'),
]