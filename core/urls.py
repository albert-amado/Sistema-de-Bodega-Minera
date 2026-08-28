from django.contrib import admin
from django.urls import include, path

from prestamo import views as prestamo_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('usuario.urls')),

    # Rutas de la aplicación de Préstamos
    path('home-usuario/', prestamo_views.prestamo_usuario_lista, name='home_usuario'),
    path('prestamo/', include('prestamo.urls')),
    # path('herramienta/', include('herramienta.urls')),  # descomentar cuando exista la app

    # Rutas auxiliares de fallback para la navegación
    path('inventario/', prestamo_views.prestamo_lista, name='inventario'),
    path('reportes/', prestamo_views.prestamo_lista, name='reportes'),
    path('devoluciones/', prestamo_views.devoluciones_lista, name='devoluciones'),
    path('usuarios/', prestamo_views.prestamo_lista, name='lista_usuarios'),
    path('almacen/', prestamo_views.prestamo_lista, name='almacen'),
    path('estantes/', prestamo_views.prestamo_lista, name='estantes'),
    path('configuracion/', prestamo_views.prestamo_lista, name='configuracion'),
    path('api/notificaciones/', prestamo_views.notificaciones_json, name='notificaciones_json'),
]