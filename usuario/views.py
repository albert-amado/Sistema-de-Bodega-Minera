import csv
import datetime
import logging
import re
import time
import unicodedata
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import EmailMultiAlternatives
from django.db.models import ProtectedError, Q, RestrictedError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from common.mixins import sesion_requerida
from prestamo.models import DevolucionHerramienta, EstadoPrestamo, Prestamo
from usuario.decorators import admin_required, login_required

from .forms import (
    DOC_PATTERNS,
    CambiarPasswordForm,
    EditarUsuarioAdminForm,
    PerfilUsuarioForm,
    RegistroUsuarioForm,
)
from .models import Usuario

logger = logging.getLogger(__name__)

ROLES_VALIDOS = [r[0] for r in Usuario.ROL_CHOICES]
ROLES = [{'id': r[0], 'nombre': r[1]} for r in Usuario.ROL_CHOICES]


@admin_required
def registro_qr_pdf(request):
    return redirect('lista_usuarios')


# ─────────────────────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────────────────────
def login_view(request):
    if request.session.get('usuario_documento'):
        return redirect('pagina_principal')

    if request.method == 'POST':
        tipo_documento = request.POST.get('tipo_documento', '').strip().upper()
        documento = request.POST.get('documento', '').strip()
        password = request.POST.get('password', '')

        campos_requeridos = {
            'Tipo de documento': tipo_documento,
            'Número de documento': documento,
            'Contraseña': password,
        }
        faltantes = [nombre for nombre, valor in campos_requeridos.items() if not valor]
        if faltantes:
            mensaje = (
                f"Faltan completar los siguientes campos: {', '.join(faltantes)}."
                if len(faltantes) > 1
                else f"Falta completar el campo: {faltantes[0]}."
            )
            messages.error(request, mensaje)
            return render(request, 'login.html', {'tipo_documento': tipo_documento, 'documento': documento})

        patron, mensaje_error = DOC_PATTERNS.get(tipo_documento, (None, None))
        if patron and not __import__('re').match(patron, documento):
            messages.error(request, mensaje_error)
            return render(request, 'login.html', {'tipo_documento': tipo_documento, 'documento': documento})

        try:
            usuario = Usuario.objects.get(
                documento=documento,
                tipo_documento=tipo_documento,
            )
        except Usuario.DoesNotExist:
            messages.error(request, 'Documento o contraseña incorrectos.')
            return render(request, 'login.html', {'tipo_documento': tipo_documento, 'documento': documento})

        if not check_password(password, usuario.password):
            messages.error(request, 'Documento o contraseña incorrectos.')
            return render(request, 'login.html', {'tipo_documento': tipo_documento, 'documento': documento})

        request.session['usuario_documento'] = usuario.numero_documento
        request.session['usuario_nombre'] = usuario.nombre_completo
        request.session['usuario_rol'] = usuario.rol
        request.session['usuario_tipo_documento'] = usuario.tipo_documento
        # Bandera de un solo uso: muestra la animación de bienvenida en el inicio
        request.session['auth_bienvenida'] = 'login'

        return redirect('pagina_principal')

    return render(request, 'login.html')


# ─────────────────────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────────────────────
def logout_view(request):
    request.session.flush()
    return redirect(reverse('login'))


# ─────────────────────────────────────────────────────────────
#  REGISTRO
# ─────────────────────────────────────────────────────────────
FICHAS_REGISTRO = ['3196477']

PROGRAMAS_CENTRO_MINERO = [
    'Análisis y Desarrollo de Software (ADSO)',
    'Administración y Gestión Minera',
    'Electricidad y Automatización Industrial',
    'Gestión y Seguridad Ambiental Minera',
    'Mantenimiento Electromecánico Industrial',
    'Operación de Maquinaria Pesada',
    'Sistemas y Computación',
    'Soldadura en Productos Metálicos',
    'Supervisión de Labores Mineras',
    'Supervisión de Labores Mineras Subterráneas',
    'Topografía y Geomática',
]


def registro_view(request):
    ctx_base = {
        'roles': ROLES,
        'fichas': FICHAS_REGISTRO,
        'programas': PROGRAMAS_CENTRO_MINERO,
        'tipo_documento': 'CC',
        'first_name': '',
        'last_name': '',
        'email': '',
        'documento': '',
        'numero_ficha': '',
        'nombre_programa': '',
    }

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            request.session['usuario_documento'] = usuario.numero_documento
            request.session['usuario_nombre'] = usuario.nombre_completo
            request.session['usuario_rol'] = usuario.rol
            request.session['usuario_tipo_documento'] = usuario.tipo_documento
            # Bandera de un solo uso: muestra la animación de registro exitoso
            request.session['auth_bienvenida'] = 'registro'
            messages.success(request, f'¡Bienvenido, {usuario.nombre_completo}!')
            return redirect('pagina_principal')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
            ctx = {
                **ctx_base,
                'first_name': request.POST.get('first_name', ''),
                'last_name': request.POST.get('last_name', ''),
                'email': request.POST.get('email', ''),
                'tipo_documento': request.POST.get('tipo_documento', 'CC'),
                'documento': request.POST.get('documento', ''),
                'numero_ficha': request.POST.get('numero_ficha', ''),
                'nombre_programa': request.POST.get('nombre_programa', ''),
            }
            return render(request, 'registro.html', ctx)

    return render(request, 'registro.html', ctx_base)


# ─────────────────────────────────────────────────────────────
#  OLVIDÓ CONTRASEÑA
# ─────────────────────────────────────────────────────────────
def olvido_contrasena_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Ingresa tu correo electrónico.')
            return render(request, 'olvido_contrasena.html')

        try:
            usuario = Usuario.objects.get(correo_personal=email)
        except Usuario.DoesNotExist:
            messages.success(request, 'Si el correo está registrado, recibirás un enlace.')
            return render(request, 'olvido_contrasena.html')

        token = get_random_string(40)
        usuario.reset_token = token
        usuario.reset_token_expira = time.time() + 900
        usuario.save(update_fields=['reset_token', 'reset_token_expira'])

        uid = urlsafe_base64_encode(force_bytes(usuario.numero_documento))
        link = request.build_absolute_uri(
            reverse('nueva_contrasena', kwargs={'uid': uid, 'token': token})
        )

        try:
            html_content = render_to_string('email_recuperacion.html', {
                'nombre': usuario.nombre_completo,
                'link': link,
            })
            text_content = strip_tags(html_content)

            correo = EmailMultiAlternatives(
                subject='Recuperación de contraseña – SENA Centro Minero',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            correo.attach_alternative(html_content, "text/html")
            correo.send(fail_silently=False)

            messages.success(request, 'Te enviamos un enlace a tu correo. Tienes 15 minutos para usarlo.')
        except Exception as e:
            logger.error('Error al enviar correo de recuperación: %s', e)
            messages.error(request, 'No se pudo enviar el correo.')

    return render(request, 'olvido_contrasena.html')


# ─────────────────────────────────────────────────────────────
#  NUEVA CONTRASEÑA
# ─────────────────────────────────────────────────────────────
def nueva_contrasena_view(request, uid, token):
    try:
        documento = force_str(urlsafe_base64_decode(uid))
        usuario = Usuario.objects.get(documento=documento)
    except Exception:
        messages.error(request, 'El enlace no es válido.')
        return redirect('olvido_contrasena')

    if (not usuario.reset_token
            or usuario.reset_token != token
            or time.time() > usuario.reset_token_expira):
        messages.error(request, 'El enlace ya fue usado o expiró. Solicita uno nuevo.')
        return redirect('olvido_contrasena')

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if len(password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return render(request, 'nueva_contrasena.html')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'nueva_contrasena.html')

        usuario.password = make_password(password1)
        usuario.reset_token = ''
        usuario.reset_token_expira = 0
        usuario.save(update_fields=['password', 'reset_token', 'reset_token_expira'])

        messages.success(request, '¡Contraseña actualizada! Ya puedes iniciar sesión.')
        return redirect('login')

    return render(request, 'nueva_contrasena.html')


# ─────────────────────────────────────────────────────────────
#  HOME
# ─────────────────────────────────────────────────────────────
@sesion_requerida
@login_required
def home_view(request):
    return redirect('pagina_principal')


# ─────────────────────────────────────────────────────────────
#  LISTA DE USUARIOS — solo Admin
# ─────────────────────────────────────────────────────────────
@admin_required
def lista_usuarios_view(request):
    # ── POST: editar usuario ──────────────────────────────────
    if request.method == 'POST' and request.POST.get('accion') == 'editar_usuario':
        doc = request.POST.get('numero_documento', '').strip()
        usuario = get_object_or_404(Usuario, documento=doc)

        form = EditarUsuarioAdminForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario {usuario.nombre_completo} actualizado correctamente.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
        return redirect('lista_usuarios')

    # ── POST: eliminar usuario ────────────────────────────────
    if request.method == 'POST' and request.POST.get('accion') == 'eliminar_usuario':
        doc = request.POST.get('numero_documento', '').strip()
        usuario = get_object_or_404(Usuario, documento=doc)
        if doc == str(request.session.get('usuario_documento', '')).strip():
            messages.error(request, 'No puedes eliminar tu propia cuenta de administrador.')
            return redirect('lista_usuarios')
        try:
            nombre = usuario.nombre_completo
            usuario.delete()
            messages.success(request, f'Usuario {nombre} eliminado correctamente.')
        except (ProtectedError, RestrictedError):
            messages.error(request, f'No se puede eliminar a {usuario.nombre_completo} porque tiene préstamos o registros asociados.')
        return redirect('lista_usuarios')

    # ── GET: listar con filtros ───────────────────────────────
    qs = Usuario.objects.order_by('primer_nombre', 'primer_apellido')

    q = request.GET.get('q', '').strip()
    rol = request.GET.get('rol', '').strip()
    tipo_doc = request.GET.get('tipo_doc', '').strip()

    if q:
        qs = qs.filter(
            Q(primer_nombre__icontains=q) |
            Q(primer_apellido__icontains=q) |
            Q(documento__icontains=q) |
            Q(correo_personal__icontains=q)
        )
    if rol and rol in ROLES_VALIDOS:
        qs = qs.filter(rol=rol)
    if tipo_doc:
        qs = qs.filter(tipo_documento=tipo_doc)

    ctx = {
        'usuarios': qs,
        'roles': ROLES,
        'tipos_doc': Usuario.TIPO_DOCUMENTO_CHOICES,
        'q': q,
        'rol_id': rol,
        'tipo_doc': tipo_doc,
        'total': qs.count(),
    }
    return render(request, 'lista_usuarios.html', ctx)


# ─────────────────────────────────────────────────────────────
#  DETALLE USUARIO (JSON para modal)
# ─────────────────────────────────────────────────────────────
@sesion_requerida
def detalle_usuario_json(request, numero_documento):
    doc_sesion = request.session.get('usuario_documento')
    rol_sesion = str(request.session.get('usuario_rol', '')).lower()
    es_admin = rol_sesion in ('admin', 'administrador')

    # IDOR Prevention: non-admins can only query their own document
    if not es_admin and doc_sesion != numero_documento:
        return JsonResponse({'error': 'No tienes permisos para ver estos datos.'}, status=403)

    usuario = get_object_or_404(
        Usuario.objects.all(),
        documento=numero_documento,
    )

    prestamos_qs = (
        Prestamo.objects
        .prefetch_related('detalles__codigo_herramienta')
        .filter(documento=usuario.numero_documento)
        .order_by('-fecha')
    )

    prestamos = []
    for p in prestamos_qs:
        prestamos.append({
            'pk': p.pk,
            'estado': p.estado,
            'estado_display': p.get_estado_display() if hasattr(p, 'get_estado_display') else p.estado,
            'fecha_prestamo': p.fecha.strftime('%d/%m/%Y') if p.fecha else '—',
            'observaciones': p.observaciones or '',
            'items': [
                {
                    'nombre': item.codigo_herramienta.nombre if item.codigo_herramienta else 'N/A',
                    'cantidad': item.cantidad,
                }
                for item in p.detalles.all()
            ],
        })

    data = {
        'numero_documento': usuario.numero_documento,
        'nombre_completo': usuario.nombre_completo,
        'correo': usuario.correo,
        'telefono': usuario.telefono,
        'numero_ficha': usuario.numero_ficha,
        'nombre_programa': usuario.nombre_programa,
        'tipo_documento_display': usuario.get_tipo_documento_display() if hasattr(usuario, 'get_tipo_documento_display') else usuario.tipo_documento,
        'tipo_documento': usuario.tipo_documento,
        'rol': usuario.rol,
        'prestamos_totales': prestamos_qs.count(),
        'prestamos_activos': prestamos_qs.filter(estado='ENTREGADO').count(),
        'prestamos_parciales': prestamos_qs.filter(estado='PARCIAL').count(),
        'prestamos': prestamos,
    }
    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────
#  EXPORTAR USUARIOS CSV — Solo Admin
# ─────────────────────────────────────────────────────────────
@admin_required
def exportar_usuarios_csv(request):
    qs = Usuario.objects.order_by('primer_nombre', 'primer_apellido')

    q = request.GET.get('q', '').strip()
    rol = request.GET.get('rol', '')
    tipo_doc = request.GET.get('tipo_doc', '')

    if q:
        qs = qs.filter(
            Q(primer_nombre__icontains=q) |
            Q(primer_apellido__icontains=q) |
            Q(documento__icontains=q) |
            Q(correo_personal__icontains=q)
        )
    if rol:
        qs = qs.filter(rol=rol)
    if tipo_doc:
        qs = qs.filter(tipo_documento=tipo_doc)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="usuarios.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['Número de Documento', 'Tipo de Documento', 'Nombre Completo',
                     'Correo', 'Teléfono', 'Ficha', 'Programa', 'Rol'])
    for u in qs:
        writer.writerow([
            u.numero_documento,
            u.get_tipo_documento_display() if hasattr(u, 'get_tipo_documento_display') else u.tipo_documento,
            u.nombre_completo,
            u.correo,
            u.telefono,
            u.numero_ficha,
            u.nombre_programa,
            u.rol,
        ])
    return response


# ─────────────────────────────────────────────────────────────
#  PERFIL
# ─────────────────────────────────────────────────────────────
@sesion_requerida
def perfil_view(request):
    doc = request.session.get('usuario_documento')
    usuario = get_object_or_404(Usuario, documento=doc)
    errores = {}
    accion_activa = ''

    if request.method == 'POST':
        accion_activa = request.POST.get('accion', '')

        if accion_activa == 'editar_perfil':
            form_perfil = PerfilUsuarioForm(request.POST, instance=usuario)
            if form_perfil.is_valid():
                form_perfil.save()
                request.session['usuario_nombre'] = usuario.nombre_completo
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('perfil')
            else:
                for k, v in form_perfil.errors.items():
                    errores[k] = ' '.join(v)

        elif accion_activa == 'cambiar_password':
            form_pass = CambiarPasswordForm(usuario, request.POST)
            if form_pass.is_valid():
                form_pass.save()
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('perfil')
            else:
                for k, v in form_pass.errors.items():
                    errores[k] = ' '.join(v)

        elif accion_activa == 'guardar_config':
            request.session['cfg_notif_prestamos'] = 'notif_prestamos' in request.POST
            request.session['cfg_notif_vencimientos'] = 'notif_vencimientos' in request.POST
            request.session['cfg_notif_devoluciones'] = 'notif_devoluciones' in request.POST
            messages.success(request, 'Configuración guardada.')
            return redirect('perfil')

    cfg_notif_prestamos = request.session.get('cfg_notif_prestamos', True)
    cfg_notif_vencimientos = request.session.get('cfg_notif_vencimientos', True)
    cfg_notif_devoluciones = request.session.get('cfg_notif_devoluciones', True)

    es_admin = (usuario.rol or '').lower() in ['admin', 'administrador'] or request.session.get('usuario_rol', '').lower() in ['admin', 'administrador']

    prestamos_personales = Prestamo.objects.filter(documento=usuario)
    tiene_personales = prestamos_personales.exists()

    if es_admin and not tiene_personales:
        prestamos_qs = Prestamo.objects.all()
        prestamos_count = prestamos_qs.count()
        prestamos_activos_count = prestamos_qs.filter(estado__in=['ENTREGADO', 'PARCIAL', 'activo', 'parcial']).count()
        devoluciones_count = (
            DevolucionHerramienta.objects.count()
            or prestamos_qs.filter(estado__in=['DEVUELTO', 'devuelto']).count()
        )
        vencidos_count = prestamos_qs.filter(estado__in=['CANCELADO', 'cancelado', 'vencido']).count()
        pendientes_count = prestamos_qs.filter(estado__in=['PENDIENTE', 'pendiente']).count()
    else:
        prestamos_qs = prestamos_personales
        prestamos_count = prestamos_qs.count()
        prestamos_activos_count = prestamos_qs.filter(estado__in=['ENTREGADO', 'PARCIAL', 'activo', 'parcial']).count()
        devoluciones_count = (
            DevolucionHerramienta.objects.filter(codigo_prestamo__documento=usuario).count()
            or prestamos_qs.filter(estado__in=['DEVUELTO', 'devuelto']).count()
        )
        vencidos_count = prestamos_qs.filter(estado__in=['CANCELADO', 'cancelado', 'vencido']).count()
        pendientes_count = prestamos_qs.filter(estado__in=['PENDIENTE', 'pendiente']).count()

    # Alertas recientes desde la base de datos
    alertas_recientes = []

    # 1. Alertas de préstamos vencidos / cancelados
    for p in prestamos_qs.filter(estado__in=['CANCELADO', 'cancelado', 'vencido']).order_by('-fecha', '-codigo_prestamo')[:2]:
        alertas_recientes.append({
            'titulo': f'Préstamo #{p.codigo_prestamo} requiere atención',
            'desc': f'Estado: Vencido/Cancelado · Registrado el {p.fecha.strftime("%d/%m/%Y") if p.fecha else "N/A"}',
            'icono': 'alarm',
            'tipo': 'vencido',
            'badge': 'Vencido',
            'badge_class': 'badge-danger',
        })

    # 2. Alertas de préstamos pendientes o activos
    if es_admin and not tiene_personales:
        for p in prestamos_qs.filter(estado__in=['PENDIENTE', 'pendiente']).order_by('-fecha', '-codigo_prestamo')[:2]:
            u_nom = p.usuario.nombre_completo if p.usuario else 'Sin asignar'
            alertas_recientes.append({
                'titulo': f'Préstamo #{p.codigo_prestamo} pendiente de entrega',
                'desc': f'Solicitado por {u_nom} · Ficha {p.ficha or "N/A"}',
                'icono': 'tools',
                'tipo': 'activo',
                'badge': 'Pendiente',
                'badge_class': 'badge-warning',
            })
    else:
        for p in prestamos_qs.filter(estado__in=['ENTREGADO', 'PARCIAL', 'activo', 'parcial']).order_by('-fecha', '-codigo_prestamo')[:2]:
            alertas_recientes.append({
                'titulo': f'Préstamo #{p.codigo_prestamo} en curso',
                'desc': f'Fecha de entrega: {p.fecha.strftime("%d/%m/%Y") if p.fecha else "N/A"}',
                'icono': 'tools',
                'tipo': 'activo',
                'badge': 'En uso',
                'badge_class': 'badge-info',
            })

    # 3. Alertas de devoluciones recientes
    if es_admin and not tiene_personales:
        devs_qs = DevolucionHerramienta.objects.select_related('codigo_prestamo').order_by('-fecha', '-codigo_devolucion')[:2]
    else:
        devs_qs = DevolucionHerramienta.objects.filter(codigo_prestamo__documento=usuario).order_by('-fecha', '-codigo_devolucion')[:2]

    for d in devs_qs:
        alertas_recientes.append({
            'titulo': f'Devolución #{d.codigo_devolucion} registrada',
            'desc': f'Asociada al Préstamo #{d.codigo_prestamo_id} · {d.fecha.strftime("%d/%m/%Y") if d.fecha else ""}',
            'icono': 'arrow-counterclockwise',
            'tipo': 'devolucion',
            'badge': 'Completada',
            'badge_class': 'badge-success',
        })

    context = {
        'usuario': usuario,
        'errores': errores,
        'accion_activa': accion_activa,
        'es_admin': es_admin,
        'tiene_personales': tiene_personales,
        'prestamos_count': prestamos_count,
        'prestamos_activos_count': prestamos_activos_count,
        'devoluciones_count': devoluciones_count,
        'vencidos_count': vencidos_count,
        'pendientes_count': pendientes_count,
        'alertas_recientes': alertas_recientes,
        'tab_list': [
            ('tab-datos', 'Datos personales', ''),
            ('tab-password', 'Contraseña', ''),
            ('tab-config', 'Notificaciones', ''),
        ],
        'notificaciones_lista': [
            ('notif_prestamos', 'Nuevos préstamos asignados',
             'Recibir alerta cuando se te asigne un préstamo.', cfg_notif_prestamos),
            ('notif_vencimientos', 'Próximos a vencer',
             'Alerta 3 días antes de que venza un préstamo activo.', cfg_notif_vencimientos),
            ('notif_devoluciones', 'Devoluciones pendientes',
             'Recordatorio de devoluciones en estado pendiente.', cfg_notif_devoluciones),
        ],
        'cfg_notif_prestamos': cfg_notif_prestamos,
        'cfg_notif_vencimientos': cfg_notif_vencimientos,
        'cfg_notif_devoluciones': cfg_notif_devoluciones,
    }

    return render(request, 'perfil.html', context)


# ─────────────────────────────────────────────────────────────
#  VERIFICACIÓN DE USUARIOS DESDE EXCEL ADMINISTRADO
# ─────────────────────────────────────────────────────────────
_EXCEL_VERIFICACION_REL = Path('backups') / 'verificacion' / 'usuarios_verificacion.xlsx'

_ALIAS_EXCEL = {
    'documento': (
        'documento', 'numero_documento', 'num_documento', 'nro_documento',
        'no_documento', 'identificacion', 'cedula', 'doc',
    ),
    'tipo_documento': (
        'tipo_documento', 'tipo_doc', 'tipo', 'tipo_identificacion', 'td',
    ),
    'nombre_completo': (
        'nombre_completo', 'aprendiz', 'usuario', 'nombre_y_apellidos',
        'nombres_y_apellidos', 'nombre',
    ),
    'primer_nombre': ('primer_nombre', 'nombres'),
    'segundo_nombre': ('segundo_nombre',),
    'primer_apellido': ('primer_apellido', 'apellidos'),
    'segundo_apellido': ('segundo_apellido',),
    'numero_ficha': ('ficha', 'numero_ficha', 'nro_ficha', 'codigo_ficha', 'ficha_sena'),
    'nombre_ficha': ('nombre_ficha', 'descripcion_ficha'),
    'programa_formacion': (
        'programa', 'programa_formacion', 'nombre_programa', 'programa_de_formacion',
    ),
    'estado_programa': (
        'estado', 'estado_programa', 'estado_formacion', 'estado_aprendiz',
    ),
    'correo_institucional': (
        'correo', 'correo_personal', 'correo_institucional', 'email', 'correo_electronico',
    ),
    'telefono_contacto': ('telefono', 'telefono_contacto', 'celular', 'movil'),
    'centro_formacion': ('centro', 'centro_formacion'),
    'regional': ('regional',),
}


def _ruta_excel_verificacion() -> Path:
    return Path(settings.BASE_DIR) / _EXCEL_VERIFICACION_REL


def _normalizar_clave_excel(clave) -> str:
    texto = str(clave or '').strip().lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFKD', texto)
        if not unicodedata.combining(c)
    )
    texto = re.sub(r'[^a-z0-9]+', '_', texto).strip('_')
    return texto


def _limpiar_valor_excel(valor) -> str:
    if valor is None:
        return ''
    texto = str(valor).strip()
    if not texto or texto.lower() == 'none':
        return ''
    if texto.endswith('.0') and texto[:-2].lstrip('-').isdigit():
        texto = texto[:-2]
    return texto


def _normalizar_documento(valor: str) -> str:
    return re.sub(r'[\s.,\-]+', '', str(valor or '').strip()).upper()


def _extraer_campo_fila(fila_norm: dict, campo: str) -> str:
    for alias in _ALIAS_EXCEL[campo]:
        val = fila_norm.get(alias, '')
        if val:
            return val
    return ''


def _extraer_registros_excel(origen) -> list[dict]:
    from configuracion.excel_backup import parse_xlsx_file

    hojas = parse_xlsx_file(origen)
    registros = []
    for filas in hojas.values():
        for fila in filas:
            fila_norm = {
                _normalizar_clave_excel(k): _limpiar_valor_excel(v)
                for k, v in fila.items()
            }
            doc_raw = _extraer_campo_fila(fila_norm, 'documento')
            doc_norm = _normalizar_documento(doc_raw)
            if not doc_norm:
                continue

            tipo_doc = _extraer_campo_fila(fila_norm, 'tipo_documento').upper() or 'CC'
            p_nombre = _extraer_campo_fila(fila_norm, 'primer_nombre')
            s_nombre = _extraer_campo_fila(fila_norm, 'segundo_nombre')
            p_apellido = _extraer_campo_fila(fila_norm, 'primer_apellido')
            s_apellido = _extraer_campo_fila(fila_norm, 'segundo_apellido')
            nombre_completo = _extraer_campo_fila(fila_norm, 'nombre_completo')

            if not nombre_completo:
                nombre_completo = ' '.join(
                    p for p in (p_nombre, s_nombre, p_apellido, s_apellido) if p
                ).strip()
            if nombre_completo and not p_nombre:
                partes = nombre_completo.split()
                p_nombre = partes[0] if partes else ''
                p_apellido = ' '.join(partes[1:]) if len(partes) > 1 else ''

            programa = _extraer_campo_fila(fila_norm, 'programa_formacion') or 'No especificado'
            ficha = _extraer_campo_fila(fila_norm, 'numero_ficha') or 'No registrada'
            nombre_ficha = _extraer_campo_fila(fila_norm, 'nombre_ficha') or programa

            registros.append({
                'documento': doc_norm,
                'tipo_documento': tipo_doc,
                'nombre_completo': nombre_completo or 'Usuario registrado',
                'primer_nombre': p_nombre,
                'segundo_nombre': s_nombre,
                'primer_apellido': p_apellido,
                'segundo_apellido': s_apellido,
                'programa_formacion': programa,
                'numero_ficha': ficha,
                'nombre_ficha': nombre_ficha,
                'estado_programa': (_extraer_campo_fila(fila_norm, 'estado_programa') or 'ACTIVO').upper(),
                'centro_formacion': _extraer_campo_fila(fila_norm, 'centro_formacion') or 'Centro Minero - Regional Boyacá',
                'regional': _extraer_campo_fila(fila_norm, 'regional') or 'Boyacá',
                'correo_institucional': _extraer_campo_fila(fila_norm, 'correo_institucional'),
                'telefono_contacto': _extraer_campo_fila(fila_norm, 'telefono_contacto'),
            })
    return registros


def _obtener_info_excel_verificacion() -> dict:
    ruta = _ruta_excel_verificacion()
    if not ruta.exists():
        return {'cargado': False, 'nombre': '', 'registros': 0, 'fecha': ''}
    try:
        registros = _extraer_registros_excel(ruta)
        stat = ruta.stat()
        fecha = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M')
        return {
            'cargado': True,
            'nombre': ruta.name,
            'registros': len(registros),
            'fecha': fecha,
        }
    except Exception as exc:
        logger.warning('No se pudo leer el archivo Excel de verificación: %s', exc)
        return {'cargado': False, 'nombre': '', 'registros': 0, 'fecha': ''}


def _buscar_usuario_en_excel(tipo_doc: str, numero_doc: str) -> tuple[dict | None, str | None, str | None]:
    tipo_norm = (tipo_doc or 'CC').strip().upper()
    doc_norm = _normalizar_documento(numero_doc)

    if not doc_norm or len(doc_norm) < 5 or len(doc_norm) > 15:
        return None, 'invalid_input', 'El número de documento debe tener entre 5 y 15 caracteres válidos.'
    if tipo_norm in ('CC', 'TI') and not doc_norm.isdigit():
        return None, 'invalid_input', f'El documento {tipo_norm} debe contener únicamente números.'

    ruta = _ruta_excel_verificacion()
    if not ruta.exists():
        return (
            None,
            'no_file',
            'No hay un archivo Excel cargado para verificación. El administrador debe cargar un archivo .xlsx en esta vista.',
        )

    registros = _extraer_registros_excel(ruta)
    coincidencia_exacta = None
    coincidencia_doc = None
    for reg in registros:
        if reg['documento'] == doc_norm:
            if reg['tipo_documento'] == tipo_norm:
                coincidencia_exacta = reg
                break
            if coincidencia_doc is None:
                coincidencia_doc = reg

    encontrado = coincidencia_exacta or coincidencia_doc
    if not encontrado:
        return (
            None,
            'not_found',
            'No se encontró ningún usuario registrado con ese documento en el archivo Excel cargado.',
        )

    resultado = dict(encontrado)
    resultado['origen_datos'] = 'excel_administrador'
    resultado['fecha_consulta'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return resultado, None, None


@admin_required
def verificar_aprendiz_view(request):
    """
    Renderiza la interfaz de búsqueda y verificación de usuarios desde el archivo
    Excel (.xlsx) administrado por el administrador.
    """
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, 'Debes seleccionar un archivo Excel (.xlsx) para cargar.')
            return redirect('verificar_aprendiz')
        if not archivo.name.lower().endswith('.xlsx'):
            messages.error(request, 'Formato no válido. Solo se permiten archivos con extensión .xlsx.')
            return redirect('verificar_aprendiz')
        try:
            contenido = archivo.read()
            registros = _extraer_registros_excel(contenido)
            if not registros:
                messages.error(
                    request,
                    'El archivo Excel no contiene registros válidos con una columna de documento (ej. documento, cedula o identificacion).',
                )
                return redirect('verificar_aprendiz')

            ruta = _ruta_excel_verificacion()
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(contenido)
            messages.success(
                request,
                f'Archivo Excel cargado correctamente ({len(registros)} usuario(s) disponibles para verificación).',
            )
        except Exception as exc:
            logger.exception('Error cargando archivo Excel de verificación')
            messages.error(request, f'No se pudo procesar el archivo Excel: {exc}')
        return redirect('verificar_aprendiz')

    tipos_documento = [
        ('CC', 'Cédula de Ciudadanía (CC)'),
        ('TI', 'Tarjeta de Identidad (TI)'),
        ('CE', 'Cédula de Extranjería (CE)'),
        ('PPT', 'Permiso por Protección Temporal (PPT)'),
        ('PEP', 'Permiso Especial de Permanencia (PEP)'),
        ('PAS', 'Pasaporte (PAS)'),
    ]
    context = {
        'title': 'Verificar Usuarios desde Excel – Sistema de Bodega Minera',
        'tipos_documento': tipos_documento,
        'excel_info': _obtener_info_excel_verificacion(),
    }
    return render(request, 'verificar_aprendiz.html', context)


@admin_required
def verificar_aprendiz_api(request):
    """
    Endpoint AJAX para consultar usuarios verificados contra el archivo Excel
    cargado por el administrador.
    """
    if request.method not in ('GET', 'POST'):
        return JsonResponse({'success': False, 'error': 'Método HTTP no permitido.'}, status=405)

    tipo_doc = request.GET.get('tipo_documento') or request.POST.get('tipo_documento', 'CC')
    numero_doc = request.GET.get('documento') or request.POST.get('documento', '')

    try:
        usuario_excel, err_code, err_msg = _buscar_usuario_en_excel(tipo_doc, numero_doc)
        if usuario_excel:
            return JsonResponse({'success': True, 'aprendiz': usuario_excel}, status=200)
        status_code = 400 if err_code == 'invalid_input' else 404
        return JsonResponse({'success': False, 'error': err_msg}, status=status_code)
    except Exception as exc:
        logger.error('Error inesperado consultando Excel de verificación: %s', exc, exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Ocurrió un error al consultar el archivo Excel de verificación.',
        }, status=500)


@admin_required
def verificar_documento_registro_api(request):
    """
    Endpoint AJAX para verificar un documento contra la base local y el archivo
    Excel administrado por el administrador.
    """
    if request.method not in ('GET', 'POST'):
        return JsonResponse({'success': False, 'error': 'Método HTTP no permitido.'}, status=405)

    tipo_doc = request.GET.get('tipo_documento') or request.POST.get('tipo_documento', 'CC')
    numero_doc = (request.GET.get('documento') or request.POST.get('documento', '')).strip()

    if not numero_doc:
        return JsonResponse({'success': False, 'error': 'El número de documento es obligatorio.'}, status=400)

    if Usuario.objects.filter(documento=_normalizar_documento(numero_doc)).exists():
        return JsonResponse({
            'success': False,
            'already_registered': True,
            'error': 'Ya existe una cuenta registrada con este número de documento. Por favor inicia sesión o recupera tu contraseña.',
        }, status=409)

    try:
        usuario_excel, err_code, err_msg = _buscar_usuario_en_excel(tipo_doc, numero_doc)
        if usuario_excel:
            return JsonResponse({
                'success': True,
                'verificado': True,
                'aprendiz': usuario_excel,
            }, status=200)

        if err_code == 'invalid_input':
            return JsonResponse({
                'success': False,
                'invalid_input': True,
                'error': err_msg,
            }, status=400)

        return JsonResponse({
            'success': False,
            'not_found': True,
            'error': err_msg,
        }, status=404)
    except Exception as exc:
        logger.error('Error inesperado en verificación por Excel: %s', exc, exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'No se pudo consultar el archivo Excel de verificación en este momento.',
        }, status=500)
