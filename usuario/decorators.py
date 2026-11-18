from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def login_required(view_func):
    """Redirige al login si no hay sesión activa."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_documento'):
            messages.error(request, 'Debes iniciar sesión para acceder.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Solo permite acceso a usuarios con rol 'Administrador'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_documento'):
            messages.error(request, 'Debes iniciar sesión para acceder.')
            return redirect('login')
        if request.session.get('usuario_rol', '').lower() not in ('admin', 'administrador'):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('pagina_principal')
        return view_func(request, *args, **kwargs)
    return wrapper


def instructor_required(view_func):
    """Permite acceso a usuarios con rol 'Instructor' o 'Administrador'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_documento'):
            messages.error(request, 'Debes iniciar sesión para acceder.')
            return redirect('login')
        rol = request.session.get('usuario_rol', '').lower()
        if rol not in ('admin', 'administrador', 'instructor'):
            messages.error(request, 'Esta sección requiere permisos de Instructor o Administrador.')
            return redirect('pagina_principal')
        return view_func(request, *args, **kwargs)
    return wrapper


def usuario_required(view_func):
    """Permite acceso a usuarios autenticados (Aprendiz, Instructor, Administrador)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_documento'):
            messages.error(request, 'Debes iniciar sesión para acceder.')
            return redirect('login')
        rol = request.session.get('usuario_rol', '').lower()
        if rol not in ('admin', 'administrador', 'instructor', 'usuario', 'aprendiz'):
            messages.error(request, 'No tienes permisos para acceder.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
