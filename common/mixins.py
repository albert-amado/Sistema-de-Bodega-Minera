# mantenimiento/mixins.py
from django.shortcuts import redirect
from django.urls import reverse_lazy
from functools import wraps


class SesionRequeridaMixin:
    """
    clase para corregir error de seguridad. Se asegura de que exista una sesion iniciada
    no se salta los filtros por si un usuario conoce la direccion exacta de una pagina protegida
    no pueda acceder a esta. Siempre debe existir una sesion.
    (protege vistas para que solo entren usuarios con sesión válida)
    Si request.user está autenticado y además es superuser o staff, deja pasar directamente.
    Si no cumple lo anterior, revisa la sesión personalizada: request.session["usuario_documento"].
    Si usuario_documento no existe, redirige al login.
    Si existe, deja pasar a la vista.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return super().dispatch(request, *args, **kwargs)

        if not request.session.get('usuario_documento'):
            return redirect('login')
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