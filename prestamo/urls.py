from django.urls import path
from . import views

urlpatterns = [
    path('', views.prestamo_lista, name='prestamo'),
    path('mis-prestamos/', views.prestamo_usuario_lista, name='prestamo_usuario'),
    path('crear/', views.crear_prestamo, name='crear_prestamo'),
    path('aprobar/', views.aprobar_prestamo, name='aprobar_prestamo'),
    path('rechazar/', views.rechazar_prestamo, name='rechazar_prestamo'),
    path('devolver/', views.devolver_prestamo, name='devolver_prestamo'),
    path('devoluciones/', views.devoluciones_lista, name='devoluciones_lista'),
    path('editar/', views.editar_prestamo, name='editar_prestamo'),
    path('solicitar/', views.usuario_solicitar_prestamo, name='usuario_solicitar_prestamo'),
]
