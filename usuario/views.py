import re
import csv
import time
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.core.exceptions import ValidationError

from usuario.decorators import admin_required, login_required

from .models import Usuario, validar_numero_documento
from common.mixins import sesion_requerida
from prestamo.models import Prestamo
def registro_qr_pdf(request):
    # lógica pendiente
    pass

logger = logging.getLogger(__name__)

DOC_RULES = {
    'CC': re.compile(r'^\d{6,10}$'),
    'CE': re.compile(r'^[A-Za-z0-9]{6,12}$'),
    'PP': re.compile(r'^[A-Za-z0-9]{5,9}$'),
    'TI': re.compile(r'^\d{10,11}$'),
}
DOC_LABELS = {
    'CC': 'Cédula de Ciudadanía',
    'CE': 'Cédula de Extranjería',
    'PP': 'Pasaporte',
    'TI': 'Tarjeta de Identidad',
}
DOC_HINTS = {
    'CC': 'La Cédula de Ciudadanía debe tener entre 6 y 10 dígitos.',
    'CE': 'La Cédula de Extranjería debe tener entre 6 y 12 caracteres alfanuméricos.',
    'PP': 'El Pasaporte debe tener entre 5 y 9 caracteres alfanuméricos.',
    'TI': 'La Tarjeta de Identidad debe tener 10 u 11 dígitos.',
}
TIPOS_VALIDOS = set(DOC_RULES.keys())
ROLES_VALIDOS = [r[0] for r in Usuario.ROL_CHOICES]
ROLES         = [{'id': r[0], 'nombre': r[1]} for r in Usuario.ROL_CHOICES]


def _validar_documento(tipo, numero):
    if tipo not in TIPOS_VALIDOS:
        return 'Tipo de documento no válido.'
    if not DOC_RULES[tipo].match(numero):
        return DOC_HINTS[tipo]
    return None


# ─────────────────────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────────────────────
def login_view(request):
    if request.session.get('usuario_documento'):
        return redirect('pagina_principal')

    if request.method == 'POST':
        tipo_documento = request.POST.get('tipo_documento', '').strip().upper()
        documento      = request.POST.get('documento', '').strip()
        password       = request.POST.get('password', '')

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
            context = {
                'tipo_documento': tipo_documento,
                'documento': documento,
            }

            return render(request, 'login.html', context)

        error_doc = _validar_documento(tipo_documento, documento)
        if error_doc:
            messages.error(request, error_doc)
            context = {
                'tipo_documento': tipo_documento,
                'documento': documento,
            }

            return render(request, 'login.html', context)

        try:
            usuario = Usuario.objects.get(
                documento=documento,
                tipo_documento=tipo_documento,
            )
        except Usuario.DoesNotExist:
            messages.error(request, 'Documento o contraseña incorrectos.')
            context = {
                'tipo_documento': tipo_documento,
                'documento': documento,
            }

            return render(request, 'login.html', context)

        if not check_password(password, usuario.password):
            messages.error(request, 'Documento o contraseña incorrectos.')
            context = {
                'tipo_documento': tipo_documento,
                'documento': documento,
            }

            return render(request, 'login.html', context)

        request.session['usuario_documento']      = usuario.numero_documento
        request.session['usuario_nombre']         = usuario.nombre_completo
        request.session['usuario_rol']            = usuario.rol
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
        'roles':           ROLES,
        'tipo_documento':  'CC',
        'first_name':      '',
        'last_name':       '',
        'email':           '',
        'documento':       '',
        'numero_ficha':    '',
        'nombre_programa': '',
    }

    if request.method == 'POST':
        first_name      = request.POST.get('first_name', '').strip()
        last_name       = request.POST.get('last_name', '').strip()
        email           = request.POST.get('email', '').strip().lower()
        tipo_documento  = request.POST.get('tipo_documento', '').strip().upper()
        documento       = request.POST.get('documento', '').strip()
        password1       = request.POST.get('password1', '')
        password2       = request.POST.get('password2', '')
        numero_ficha    = request.POST.get('numero_ficha', '').strip()
        nombre_programa = request.POST.get('nombre_programa', '').strip()
        rol_id          = 'Usuario'

        ctx = {
            **ctx_base,
            'first_name':      first_name,
            'last_name':       last_name,
            'email':           email,
            'tipo_documento':  tipo_documento,
            'documento':       documento,
            'numero_ficha':    numero_ficha,
            'nombre_programa': nombre_programa,
        }

        if not all([first_name, last_name, email, tipo_documento, documento, password1, password2]):
            messages.error(request, 'Completa todos los campos obligatorios.')
            return render(request, 'registro.html', ctx)

        error_doc = _validar_documento(tipo_documento, documento)
        if error_doc:
            messages.error(request, error_doc)
            return render(request, 'registro.html', ctx)

        if len(password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return render(request, 'registro.html', ctx)

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'registro.html', ctx)

        if Usuario.objects.filter(documento=documento).exists():
            messages.error(request, 'Ya existe un usuario con ese número de documento.')
            return render(request, 'registro.html', ctx)

        if Usuario.objects.filter(correo_personal=email).exists():
            messages.error(request, 'El correo ya está registrado.')
            return render(request, 'registro.html', ctx)

        username = f"{first_name} {last_name}".strip()
        usuario = Usuario(
            numero_documento=documento,
            nombre_completo=username,
            correo=email,
            telefono='',
            tipo_documento=tipo_documento,
            password=make_password(password1),
            rol=rol_id,
            numero_ficha=numero_ficha,
            nombre_programa=nombre_programa,
        )

        try:
            usuario.full_clean()
        except ValidationError as e:
            messages.error(request, ' '.join(e.messages))
            return render(request, 'registro.html', ctx)

        usuario.save()

        request.session['usuario_documento']      = usuario.numero_documento
        request.session['usuario_nombre']         = usuario.nombre_completo
        request.session['usuario_rol']            = usuario.rol
        request.session['usuario_tipo_documento'] = usuario.tipo_documento

        return redirect('pagina_principal')

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
            # Mensaje genérico por seguridad
            messages.success(request, 'Si el correo está registrado, recibirás un enlace.')
            return render(request, 'olvido_contrasena.html')

        # Generar token y guardarlo en la base de datos (no en sesión)
        token = get_random_string(40)
        usuario.reset_token        = token
        usuario.reset_token_expira = time.time() + 900
        usuario.save(update_fields=['reset_token', 'reset_token_expira'])

        uid  = urlsafe_base64_encode(force_bytes(usuario.numero_documento))
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
            # Registrar el error real en consola/logs para poder diagnosticarlo
            logger.error('Error al enviar correo de recuperación: %s', e)
            print(f'[ERROR CORREO] {e}')  # visible en la consola del servidor
            messages.error(request, f'No se pudo enviar el correo. Error: {e}')

    return render(request, 'olvido_contrasena.html')


# ─────────────────────────────────────────────────────────────
#  NUEVA CONTRASEÑA
# ─────────────────────────────────────────────────────────────
def nueva_contrasena_view(request, uid, token):
    try:
        documento = force_str(urlsafe_base64_decode(uid))
        usuario   = Usuario.objects.get(documento=documento)
    except Exception:
        messages.error(request, 'El enlace no es válido.')
        return redirect('olvido_contrasena')

    # Validar token guardado en base de datos
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

        usuario.password           = make_password(password1)
        usuario.reset_token        = ''
        usuario.reset_token_expira = 0
        usuario.save(update_fields=['password', 'reset_token', 'reset_token_expira'])

        messages.success(request, '¡Contraseña actualizada! Ya puedes iniciar sesión.')
        return redirect('login')

    return render(request, 'nueva_contrasena.html')


# ─────────────────────────────────────────────────────────────
#  HOME
# ─────────────────────────────────────────────────────────────
from pagina_principal.views import home_usuario_view as dashboard_view

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
        doc             = request.POST.get('numero_documento', '').strip()
        nombre          = request.POST.get('nombre_completo', '').strip()
        correo          = request.POST.get('correo', '').strip().lower()
        telefono        = request.POST.get('telefono', '').strip()
        numero_ficha    = request.POST.get('numero_ficha', '').strip()
        nombre_programa = request.POST.get('nombre_programa', '').strip()
        rol_id          = request.POST.get('rol', '').strip()
        nueva_password  = request.POST.get('nueva_password', '').strip()

        usuario = get_object_or_404(Usuario, documento=doc)

        if not nombre:
            messages.error(request, 'El nombre no puede estar vacío.')
            return redirect('lista_usuarios')

        if not correo or '@' not in correo:
            messages.error(request, 'Ingresa un correo válido.')
            return redirect('lista_usuarios')

        if telefono and not telefono.isdigit():
            messages.error(request, 'El teléfono solo debe contener dígitos.')
            return redirect('lista_usuarios')

        if Usuario.objects.filter(correo_personal=correo).exclude(documento=doc).exists():
            messages.error(request, 'Ese correo ya está en uso por otro usuario.')
            return redirect('lista_usuarios')

        if rol_id not in ROLES_VALIDOS:
            messages.error(request, 'Rol no válido.')
            return redirect('lista_usuarios')

        parts = nombre.split(' ', 1)
        usuario.primer_nombre    = parts[0]
        usuario.primer_apellido  = parts[1] if len(parts) > 1 else ''
        usuario.correo_personal  = correo
        usuario.telefono         = telefono
        usuario.ficha            = numero_ficha
        usuario.programa         = nombre_programa
        usuario.rol              = rol_id

        campos = ['primer_nombre', 'primer_apellido', 'correo_personal', 'telefono', 'ficha', 'programa', 'rol']

        if nueva_password:
            if len(nueva_password) < 8:
                messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
                return redirect('lista_usuarios')
            usuario.password = make_password(nueva_password)
            campos.append('password')

        usuario.save(update_fields=campos)

        messages.success(request, f'Usuario {usuario.nombre_completo} actualizado correctamente.')
        return redirect('lista_usuarios')

    # ── GET: listar con filtros ───────────────────────────────
    qs = Usuario.objects.order_by('primer_nombre', 'primer_apellido')

    q        = request.GET.get('q', '').strip()
    rol      = request.GET.get('rol', '')
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

    ctx = {
        'usuarios':  qs,
        'roles':     ROLES,
        'tipos_doc': Usuario.TIPO_DOCUMENTO_CHOICES,
        'q':         q,
        'rol_id':    rol,
        'tipo_doc':  tipo_doc,
        'total':     qs.count(),
    }
    return render(request, 'lista_usuarios.html', ctx)


# ─────────────────────────────────────────────────────────────
#  DETALLE USUARIO (JSON para modal)
# ─────────────────────────────────────────────────────────────
@sesion_requerida
def detalle_usuario_json(request, numero_documento):
    usuario = get_object_or_404(
        Usuario.objects.select_related('destinado', 'solicitado'),
        documento=numero_documento,
    )

    prestamos_qs = (
        Prestamo.objects
        .prefetch_related('items__codigo_herramienta')
        .filter(usuario=usuario.numero_documento)
        .order_by('-fecha_prestamo')
    )

    prestamos = []
    for p in prestamos_qs:
        prestamos.append({
            'pk':                        p.pk,
            'estado':                    p.estado,
            'estado_display':            p.get_estado_display(),
            'fecha_prestamo':            p.fecha_prestamo.strftime('%d/%m/%Y'),
            'fecha_vencimiento':         p.fecha_vencimiento.strftime('%d/%m/%Y') if p.fecha_vencimiento else '—',
            'dias_restantes':            p.dias_restantes,
            'observaciones':             p.observaciones or '',
            'motivo_solicitud':          p.motivo_solicitud or '',
            'pendiente_para_devolucion': p.estado in ['activo', 'parcial'],
            'items': [
                {
                    'nombre':   item.producto.nombre,
                    'cantidad': item.cantidad,
                    'devuelto': item.devuelto,
                    'serial':   item.serial_entregado,
                }
                for item in p.items.all()
            ],
        })

    data = {
        'numero_documento':       usuario.numero_documento,
        'nombre_completo':        usuario.nombre_completo,
        'correo':                 usuario.correo,
        'telefono':               usuario.telefono,
        'numero_ficha':           usuario.numero_ficha,
        'nombre_programa':        usuario.nombre_programa,
        'tipo_documento_display': usuario.get_tipo_documento_display(),
        'tipo_documento':         usuario.tipo_documento,
        'rol':                    usuario.rol,
        'destinado':      usuario.destinado.nombre_completo  if usuario.destinado  else None,
        'destinado_doc':  usuario.destinado.numero_documento if usuario.destinado  else None,
        'solicitado':     usuario.solicitado.nombre_completo  if usuario.solicitado else None,
        'solicitado_doc': usuario.solicitado.numero_documento if usuario.solicitado else None,
        'prestamos_totales':   prestamos_qs.count(),
        'prestamos_activos':   prestamos_qs.filter(estado='activo').count(),
        'prestamos_parciales': prestamos_qs.filter(estado='parcial').count(),
        'prestamos_vencidos':  prestamos_qs.filter(estado='vencido').count(),
        'prestamos':           prestamos,
    }
    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────
#  EXPORTAR USUARIOS CSV
# ─────────────────────────────────────────────────────────────
@sesion_requerida
def exportar_usuarios_csv(request):
    qs = Usuario.objects.order_by('primer_nombre', 'primer_apellido')

    q        = request.GET.get('q', '').strip()
    rol      = request.GET.get('rol', '')
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
            u.get_tipo_documento_display(),
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
    doc     = request.session.get('usuario_documento')
    usuario = get_object_or_404(Usuario, documento=doc)
    errores = {}
    accion_activa = ''

    if request.method == 'POST':
        accion_activa = request.POST.get('accion', '')

        if accion_activa == 'editar_perfil':
            nombre          = request.POST.get('nombre_completo', '').strip()
            correo          = request.POST.get('correo', '').strip().lower()
            telefono        = request.POST.get('telefono', '').strip()
            numero_ficha    = request.POST.get('numero_ficha', '').strip()
            nombre_programa = request.POST.get('nombre_programa', '').strip()

            if not nombre:
                errores['nombre_completo'] = 'El nombre no puede estar vacío.'
            if not correo or '@' not in correo:
                errores['correo'] = 'Ingresa un correo válido.'
            if telefono and not telefono.isdigit():
                errores['telefono'] = 'El teléfono solo debe contener dígitos.'
            if not errores.get('correo'):
                if Usuario.objects.filter(correo_personal=correo).exclude(documento=doc).exists():
                    errores['correo'] = 'Este correo ya está en uso por otro usuario.'

            if not errores:
                parts = nombre.split(' ', 1)
                usuario.primer_nombre    = parts[0]
                usuario.primer_apellido  = parts[1] if len(parts) > 1 else ''
                usuario.correo_personal  = correo
                usuario.telefono         = telefono
                usuario.ficha            = numero_ficha
                usuario.programa         = nombre_programa
                usuario.save(update_fields=[
                    'primer_nombre', 'primer_apellido', 'correo_personal', 'telefono',
                    'ficha', 'programa',
                ])
                request.session['usuario_nombre'] = nombre
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('perfil')

        elif accion_activa == 'cambiar_password':
            actual   = request.POST.get('password_actual', '')
            nueva    = request.POST.get('password_nueva', '')
            confirma = request.POST.get('password_confirma', '')

            if not check_password(actual, usuario.password):
                errores['password_actual'] = 'La contraseña actual es incorrecta.'
            if len(nueva) < 8:
                errores['password_nueva'] = 'La nueva contraseña debe tener al menos 8 caracteres.'
            if nueva != confirma:
                errores['password_confirma'] = 'Las contraseñas no coinciden.'

            if not errores:
                usuario.password = make_password(nueva)
                usuario.save(update_fields=['password'])
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('perfil')

        elif accion_activa == 'guardar_config':
            request.session['cfg_notif_prestamos']    = 'notif_prestamos'    in request.POST
            request.session['cfg_notif_vencimientos'] = 'notif_vencimientos' in request.POST
            request.session['cfg_notif_devoluciones'] = 'notif_devoluciones' in request.POST
            messages.success(request, 'Configuración guardada.')
            return redirect('perfil')

    cfg_notif_prestamos    = request.session.get('cfg_notif_prestamos',    True)
    cfg_notif_vencimientos = request.session.get('cfg_notif_vencimientos', True)
    cfg_notif_devoluciones = request.session.get('cfg_notif_devoluciones', True)

    context = {
        'usuario':       usuario,
        'errores':       errores,
        'accion_activa': accion_activa,
        'tab_list': [
            ('tab-datos',    'Datos personales', ''),
            ('tab-password', 'Contraseña',       ''),
            ('tab-config',   'Notificaciones',   ''),
        ],
        'notificaciones_lista': [
            ('notif_prestamos',    'Nuevos préstamos asignados',
             'Recibir alerta cuando se te asigne un préstamo.',      cfg_notif_prestamos),
            ('notif_vencimientos', 'Próximos a vencer',
             'Alerta 3 días antes de que venza un préstamo activo.', cfg_notif_vencimientos),
            ('notif_devoluciones', 'Devoluciones pendientes',
             'Recordatorio de devoluciones en estado pendiente.',    cfg_notif_devoluciones),
        ],
        'cfg_notif_prestamos':    cfg_notif_prestamos,
        'cfg_notif_vencimientos': cfg_notif_vencimientos,
        'cfg_notif_devoluciones': cfg_notif_devoluciones,
    }


    return render(request, 'perfil.html', context)


def registro_qr_pdf(request):
    pass