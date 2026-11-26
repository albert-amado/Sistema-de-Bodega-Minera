from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect

ADMIN_ROLES = ('admin', 'administrador')


def _es_peticion_json(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
        or '/api/' in request.path
    )


def es_administrador_valido(request):
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return True
    doc = request.session.get('usuario_documento')
    if not doc:
        return False
    rol_sesion = str(request.session.get('usuario_rol', '')).strip().lower()
    if rol_sesion not in ADMIN_ROLES:
        return False
    from usuario.models import Usuario
    rol_db = Usuario.objects.filter(documento=doc).values_list('rol', flat=True).first()
    if rol_db is None or str(rol_db).strip().lower() not in ADMIN_ROLES:
        return False
    return True


def login_required(view_func):
    """Redirige al login si no hay sesión activa."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_documento'):
            if _es_peticion_json(request):
                return JsonResponse({'error': 'Debes iniciar sesión para acceder.'}, status=401)
            messages.error(request, 'Debes iniciar sesión para acceder.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Solo permite acceso a usuarios autenticados con rol verificado 'Administrador'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
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
