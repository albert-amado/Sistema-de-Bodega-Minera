# usuario/urls.py
from django.urls import path

from pagina_principal.views import home_usuario_view

from . import views

urlpatterns = [
    path('home/',                                   views.home_view,             name='home'),
    path('home/usuario/',                           home_usuario_view,           name='home_usuario'),
    path('',                                        views.login_view,            name='login'),
    path('logout/',                                 views.logout_view,           name='logout'),
    path('registro/',                               views.registro_view,         name='registro'),
    path('olvido/',                                 views.olvido_contrasena_view,name='olvido_contrasena'),
    path('nueva-contrasena/<uid>/<token>/',         views.nueva_contrasena_view, name='nueva_contrasena'),
    path('usuarios/',                               views.lista_usuarios_view,   name='lista_usuarios'),
    path('usuarios/exportar/csv/',                  views.exportar_usuarios_csv, name='exportar_usuarios_csv'),
    path('usuarios/<str:numero_documento>/json/',   views.detalle_usuario_json,  name='detalle_usuario_json'),
    path('perfil/',                                 views.perfil_view,           name='perfil'),
    path('registro/qr-pdf/',                        views.registro_qr_pdf,       name='registro_qr_pdf'),
    path('aprendices/verificar/',                   views.verificar_aprendiz_view, name='verificar_aprendiz'),
    path('api/aprendices/verificar/',               views.verificar_aprendiz_api,  name='api_verificar_aprendiz'),
    path('api/aprendices/verificar-documento/',     views.verificar_documento_registro_api, name='api_verificar_documento_registro'),
]