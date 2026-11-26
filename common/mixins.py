# mantenimiento/mixins.py
from functools import wraps

from django.shortcuts import redirect
from django.urls import reverse_lazy


class SesionRequeridaMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return super().dispatch(request, *args, **kwargs)

        if not request.session.get('usuario_documento'):
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class AdminRequeridoMixin:
    def dispatch(self, request, *args, **kwargs):
        from django.contrib import messages
        from django.http import JsonResponse
        from usuario.decorators import _es_peticion_json, es_administrador_valido

        tiene_sesion = bool(request.session.get('usuario_documento')) or (
            request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff)
        )
        if not tiene_sesion:
            if _es_peticion_json(request):
                return JsonResponse({'error': 'Debes iniciar sesión para acceder.'}, status=401)
            messages.error(request, 'Debes iniciar sesión para acceder.')
            return redirect('login')
        if not es_administrador_valido(request):
            if _es_peticion_json(request):
                return JsonResponse({'error': 'No tienes permisos de administrador para acceder a este recurso.'}, status=403)
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('pagina_principal')
        return super().dispatch(request, *args, **kwargs)


class ContextoMixin:
    """
    Inyecta los datos en las vistas sin necesidad de escribir los mismos en todas
    simplemente se importa la clase contextomixin y se integran los datos necesarios
    para evitar duplicaciones en el codigo y hacerlo mas rapido.
    agrega variables comunes al contexto de templates para no repetir código.
    """
    titulo       = ''
    subtitulo    = ''
    boton_texto  = 'Guardar'
    url_cancelar = None
    url_accion   = None   
    label_accion = ''     

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo']       = self.titulo
        ctx['subtitulo']    = self.subtitulo
        ctx['boton_texto']  = self.boton_texto
        ctx['url_accion']   = self.url_accion
        ctx['label_accion'] = self.label_accion
        if self.url_cancelar:
            ctx['url_cancelar'] = reverse_lazy(self.url_cancelar)
        return ctx


"""
creamos funcion reutilizable
ESTA FUNCION SE IMPORTA EN TODOS LOS MODELOS CON: @sesion_requerida
"""
def sesion_requerida(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return func(request, *args, **kwargs)
        if not request.session.get('usuario_documento'):
            return redirect('login')
        return func(request, *args, **kwargs)
    return wrapper