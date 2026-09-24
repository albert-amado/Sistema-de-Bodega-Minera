import csv
import logging
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
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


def registro_qr_pdf(request):
    pass


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
def registro_view(request):
    ctx_base = {
        'roles': ROLES,
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
#  VERIFICACIÓN DE APRENDICES SENA (INTEGRACIÓN SOFIAPLUS)
# ─────────────────────────────────────────────────────────────
@admin_required
def verificar_aprendiz_view(request):
    """
    Renderiza la interfaz de búsqueda y verificación de aprendices SENA.
    Acceso restringido a roles autorizados (Administradores / Supervisores de bodega).
    Cumple con la Ley 1581 de 2012 (Habeas Data).
    """
    tipos_documento = [
        ('CC', 'Cédula de Ciudadanía (CC)'),
        ('TI', 'Tarjeta de Identidad (TI)'),
        ('CE', 'Cédula de Extranjería (CE)'),
        ('PPT', 'Permiso por Protección Temporal (PPT)'),
        ('PEP', 'Permiso Especial de Permanencia (PEP)'),
        ('PAS', 'Pasaporte (PAS)'),
    ]
    context = {
        'title': 'Verificar Aprendiz SENA – Sistema de Bodega Minera',
        'tipos_documento': tipos_documento,
    }
    return render(request, 'verificar_aprendiz.html', context)


@admin_required
def verificar_aprendiz_api(request):
    """
    Endpoint AJAX para la consulta en vivo de aprendices SENA.
    Recibe tipo_documento y documento por GET o POST.
    Nunca expone tokens, credenciales ni trazas de error internas al usuario.
    """
    from services.sofia_plus_client import (
        get_sofia_plus_client,
        SofiaPlusInvalidInputError,
        AprendizNotFoundError,
        SofiaPlusServiceUnavailableError,
        SofiaPlusAuthError,
    )

    if request.method not in ('GET', 'POST'):
        return JsonResponse({'success': False, 'error': 'Método HTTP no permitido.'}, status=405)

    tipo_doc = request.GET.get('tipo_documento') or request.POST.get('tipo_documento', 'CC')
    numero_doc = request.GET.get('documento') or request.POST.get('documento', '')

    client = get_sofia_plus_client()

    try:
        aprendiz_info = client.consultar_aprendiz(
            tipo_documento=tipo_doc,
            numero_documento=numero_doc,
        )
        return JsonResponse({
            'success': True,
            'aprendiz': aprendiz_info.to_dict(),
        }, status=200)

    except SofiaPlusInvalidInputError as exc:
        return JsonResponse({'success': False, 'error': exc.user_friendly_message}, status=400)

    except AprendizNotFoundError as exc:
        return JsonResponse({'success': False, 'error': exc.user_friendly_message}, status=404)

    except SofiaPlusAuthError as exc:
        logger.error("Fallo de autenticación con servicio SENA: %s", exc)
        return JsonResponse({'success': False, 'error': exc.user_friendly_message}, status=401)

    except SofiaPlusServiceUnavailableError as exc:
        logger.warning("Servicio externo SENA no disponible: %s", exc)
        return JsonResponse({'success': False, 'error': exc.user_friendly_message}, status=503)

    except Exception as exc:
        logger.error("Error inesperado en consulta de aprendiz: %s", exc, exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Ocurrió un error inesperado al consultar los datos del aprendiz. Intente nuevamente más tarde.'
        }, status=500)


def verificar_documento_registro_api(request):
    """
    Endpoint AJAX para la verificación en tiempo real durante el registro de usuarios.
    - Valida duplicados en la base de datos local (evita dos cuentas con el mismo documento).
    - Consulta aislada a SofiaPlus mediante el cliente centralizado get_sofia_plus_client().
    - Retorna datos para auto-completar y bloquear en solo lectura si el aprendiz existe.
    - Aplica las políticas configuradas si no existe (ALLOW_MANUAL_REGISTRATION)
      o si el servicio no responde (SOFIAPLUS_FALLBACK_POLICY).
    """
    from django.conf import settings
    from services.sofia_plus_client import (
        get_sofia_plus_client,
        SofiaPlusInvalidInputError,
        AprendizNotFoundError,
        SofiaPlusServiceUnavailableError,
        SofiaPlusAuthError,
    )

    if request.method not in ('GET', 'POST'):
        return JsonResponse({'success': False, 'error': 'Método HTTP no permitido.'}, status=405)

    tipo_doc = request.GET.get('tipo_documento') or request.POST.get('tipo_documento', 'CC')
    numero_doc = (request.GET.get('documento') or request.POST.get('documento', '')).strip()

    if not numero_doc:
        return JsonResponse({'success': False, 'error': 'El número de documento es obligatorio.'}, status=400)

    # 1. Validar duplicados en la base de datos local
    if Usuario.objects.filter(documento=numero_doc).exists():
        return JsonResponse({
            'success': False,
            'already_registered': True,
            'error': 'Ya existe una cuenta registrada con este número de documento. Por favor inicia sesión o recupera tu contraseña.'
        }, status=409)

    client = get_sofia_plus_client()

    try:
        aprendiz = client.consultar_aprendiz(tipo_doc, numero_doc)
        return JsonResponse({
            'success': True,
            'verificado': True,
            'aprendiz': {
                'documento': aprendiz.documento,
                'tipo_documento': aprendiz.tipo_documento,
                'nombre_completo': aprendiz.nombre_completo,
                'primer_nombre': aprendiz.primer_nombre,
                'primer_apellido': aprendiz.primer_apellido,
                'segundo_nombre': aprendiz.segundo_nombre,
                'segundo_apellido': aprendiz.segundo_apellido,
                'numero_ficha': aprendiz.numero_ficha,
                'nombre_ficha': aprendiz.nombre_ficha,
                'programa_formacion': aprendiz.programa_formacion,
                'estado_programa': aprendiz.estado_programa,
                'centro_formacion': aprendiz.centro_formacion,
                'regional': aprendiz.regional,
                'correo_institucional': aprendiz.correo_institucional,
                'telefono_contacto': aprendiz.telefono_contacto,
                'origen_datos': aprendiz.origen_datos,
            }
        }, status=200)

    except SofiaPlusInvalidInputError as exc:
        return JsonResponse({
            'success': False,
            'invalid_input': True,
            'error': exc.user_friendly_message
        }, status=400)

    except AprendizNotFoundError as exc:
        allow_manual = getattr(settings, 'ALLOW_MANUAL_REGISTRATION', False)
        return JsonResponse({
            'success': False,
            'not_found': True,
            'allow_manual': allow_manual,
            'error': (
                'El documento no se encuentra registrado en SofiaPlus. '
                'Solo aprendices verificados del SENA pueden crear una cuenta en el sistema.'
                if not allow_manual else
                'El documento no figura en SofiaPlus. Registro manual habilitado como excepción.'
            )
        }, status=200 if allow_manual else 404)

    except SofiaPlusServiceUnavailableError as exc:
        policy = getattr(settings, 'SOFIAPLUS_FALLBACK_POLICY', 'ALLOW_PENDING')
        allow_pending = (policy == 'ALLOW_PENDING')
        return JsonResponse({
            'success': False,
            'service_unavailable': True,
            'policy': policy,
            'allow_pending': allow_pending,
            'error': (
                'El servicio de SofiaPlus no responde temporalmente. Puedes continuar con el registro; '
                'tu cuenta quedará registrada provisionalmente pendiente de verificación.'
                if allow_pending else
                'El servicio de SofiaPlus no responde temporalmente. Por seguridad, el registro requiere verificación activa. Intenta de nuevo en unos minutos.'
            )
        }, status=200 if allow_pending else 503)

    except Exception as exc:
        logger.error("Error inesperado en endpoint de registro SofiaPlus: %s", exc, exc_info=True)
        policy = getattr(settings, 'SOFIAPLUS_FALLBACK_POLICY', 'ALLOW_PENDING')
        allow_pending = (policy == 'ALLOW_PENDING')
        return JsonResponse({
            'success': False,
            'service_unavailable': True,
            'policy': policy,
            'allow_pending': allow_pending,
            'error': 'No se pudo conectar con el servicio de verificación en este momento.'
        }, status=200 if allow_pending else 500)
