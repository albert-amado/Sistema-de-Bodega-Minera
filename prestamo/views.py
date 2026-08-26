import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .models import Prestamo, DetallePrestamo, Herramienta, EstadoPrestamo, DevolucionHerramienta

User = get_user_model()


def notificaciones_json(request):
    """Endpoint para obtener notificaciones en JSON."""
    return JsonResponse({'items': []})


def prestamo_lista(request):
    """Vista principal para la gestión de préstamos (Admin)."""
    prestamos_qs = Prestamo.objects.prefetch_related('detalles__herramienta', 'devoluciones').select_related('usuario').order_by('-id')

    # Filtro opcional por estado
    estado_filtro = request.GET.get('estado')
    if estado_filtro:
        prestamos_qs = prestamos_qs.filter(estado=estado_filtro)

    # Conteos para tarjetas KPI
    total_prestamos = Prestamo.objects.count()
    activos = Prestamo.objects.filter(estado=EstadoPrestamo.ENTREGADO).count()
    pendientes = Prestamo.objects.filter(estado=EstadoPrestamo.PENDIENTE).count()
    devueltos = Prestamo.objects.filter(estado=EstadoPrestamo.DEVUELTO).count()
    cancelados = Prestamo.objects.filter(estado=EstadoPrestamo.CANCELADO).count()

    herramientas_qs = Herramienta.objects.all()
    usuarios_qs = User.objects.all()

    # Formateo JSON para scripts en plantilla
    herramientas_json = [
        {
            'pk': h.pk,
            'codigo': h.codigo,
            'nombre': h.nombre,
            'stock_disponible': h.stock_disponible
        }
        for h in herramientas_qs
    ]

    usuarios_json = [
        {
            'pk': u.pk,
            'username': u.username,
            'nombre_completo': u.get_full_name() or u.username,
            'documento': getattr(u, 'numero_documento', '') or getattr(u, 'documento', '')
        }
        for u in usuarios_qs
    ]

    context = {
        'all_prestamos': prestamos_qs,
        'prestamos': prestamos_qs,
        'total_prestamos': total_prestamos,
        'activos': activos,
        'pendientes': pendientes,
        'devueltos': devueltos,
        'cancelados': cancelados,
        'herramientas_disponibles': herramientas_qs,
        'productos_disponibles': herramientas_qs,
        'productos': herramientas_qs,
        'usuarios': usuarios_qs,
        'herramientas_json': json.dumps(herramientas_json),
        'productos_json': json.dumps(herramientas_json),
        'usuarios_json': json.dumps(usuarios_json),
    }
    return render(request, 'prestamo.html', context)


def prestamo_usuario_lista(request):
    """Vista de préstamos para la interfaz de Usuario."""
    usuario_actual = request.user if request.user.is_authenticated else None
    
    if usuario_actual:
        prestamos_qs = Prestamo.objects.filter(usuario=usuario_actual).prefetch_related('detalles__herramienta').order_by('-id')
    else:
        prestamos_qs = Prestamo.objects.all().prefetch_related('detalles__herramienta').order_by('-id')

    total_prestamos = prestamos_qs.count()
    total_activos = prestamos_qs.filter(estado=EstadoPrestamo.ENTREGADO).count()
    vencidos_count = 0
    proximos_vencer = 0

    herramientas_qs = Herramienta.objects.all()

    context = {
        'all_prestamos': prestamos_qs,
        'total_prestamos': total_prestamos,
        'total_activos': total_activos,
        'vencidos_count': vencidos_count,
        'proximos_vencer': proximos_vencer,
        'herramientas_disponibles': herramientas_qs,
        'productos_disponibles': herramientas_qs,
        'productos': herramientas_qs,
        'usuario': usuario_actual,
    }
    return render(request, 'prestamo_usuario.html', context)


@transaction.atomic
def crear_prestamo(request):
    """Procesa la creación de un nuevo préstamo (Wizard Admin)."""
    if request.method == 'POST':
        documento = request.POST.get('documento', '').strip()
        ficha = request.POST.get('ficha', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()
        herramientas_ids = request.POST.getlist('herramienta[]')
        cantidades = request.POST.getlist('cantidad[]')

        if not documento or not ficha:
            messages.error(request, "El documento y la ficha SENA son obligatorios.")
            return redirect('prestamo')

        if not herramientas_ids:
            messages.error(request, "Debes seleccionar al menos una herramienta.")
            return redirect('prestamo')

        # Buscar o vincular usuario opcional
        usuario_obj = User.objects.filter(username=documento).first()

        nuevo_prestamo = Prestamo.objects.create(
            documento=documento,
            ficha=ficha,
            usuario=usuario_obj,
            estado=EstadoPrestamo.PENDIENTE,
            observaciones=observaciones
        )

        for h_id, cant in zip(herramientas_ids, cantidades):
            if not h_id:
                continue
            try:
                cant_num = int(cant)
                herramienta = Herramienta.objects.get(pk=h_id)
                DetallePrestamo.objects.create(
                    prestamo=nuevo_prestamo,
                    herramienta=herramienta,
                    cantidad=cant_num
                )
            except (ValueError, Herramienta.DoesNotExist) as e:
                continue

        messages.success(request, f"Préstamo #{nuevo_prestamo.pk} registrado con éxito.")
    return redirect('prestamo')


def aprobar_prestamo(request):
    """Aprueba una solicitud de préstamo y descuenta stock."""
    if request.method == 'POST':
        pk = request.POST.get('pk')
        prestamo = get_object_or_404(Prestamo, pk=pk)

        with transaction.atomic():
            # Descontar stock
            for detalle in prestamo.detalles.select_related('herramienta'):
                h = detalle.herramienta
                if h.stock_disponible >= detalle.cantidad:
                    h.stock_disponible -= detalle.cantidad
                    h.save()
                else:
                    messages.error(request, f"Stock insuficiente para {h.nombre}.")
                    return redirect('prestamo')

            prestamo.estado = EstadoPrestamo.ENTREGADO
            prestamo.save()
            messages.success(request, f"Préstamo #{prestamo.pk} aprobado y entregado.")

    return redirect('prestamo')


def rechazar_prestamo(request):
    """Rechaza / Cancela una solicitud de préstamo."""
    if request.method == 'POST':
        pk = request.POST.get('pk')
        motivo = request.POST.get('motivo_rechazo', '')
        prestamo = get_object_or_404(Prestamo, pk=pk)

        prestamo.estado = EstadoPrestamo.CANCELADO
        if motivo:
            prestamo.observaciones = (prestamo.observaciones or '') + f" | Cancelado: {motivo}"
        prestamo.save()
        messages.warning(request, f"Préstamo #{prestamo.pk} rechazado.")

    return redirect('prestamo')


def devolver_prestamo(request):
    """Registra la devolución de herramientas de un préstamo."""
    if request.method == 'POST':
        pk = request.POST.get('pk')
        prestamo = get_object_or_404(Prestamo, pk=pk)

        with transaction.atomic():
            # Restablecer stock
            for detalle in prestamo.detalles.select_related('herramienta'):
                h = detalle.herramienta
                h.stock_disponible += detalle.cantidad
                h.save()

            prestamo.estado = EstadoPrestamo.DEVUELTO
            prestamo.save()

            DevolucionHerramienta.objects.create(
                prestamo=prestamo,
                codigo_recibe=request.user.username if request.user.is_authenticated else 'SISTEMA',
                recibido_por=request.user if request.user.is_authenticated else None,
                observaciones="Devolución completa registrada"
            )
            messages.success(request, f"Devolución del Préstamo #{prestamo.pk} completada.")

    return redirect('prestamo')


def editar_prestamo(request):
    """Actualiza las observaciones de un préstamo existente."""
    if request.method == 'POST':
        pk = request.POST.get('pk')
        observaciones = request.POST.get('observaciones', '')
        prestamo = get_object_or_404(Prestamo, pk=pk)
        prestamo.observaciones = observaciones
        prestamo.save()
        messages.success(request, f"Préstamo #{prestamo.pk} actualizado.")
    return redirect('prestamo')


def usuario_solicitar_prestamo(request):
    """Procesa la solicitud de préstamo enviada desde el portal de usuario."""
    if request.method == 'POST':
        documento = request.POST.get('documento', '').strip()
        ficha = request.POST.get('ficha', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()
        herramientas_ids = request.POST.getlist('herramienta[]')
        cantidades = request.POST.getlist('cantidad[]')

        if not documento or not ficha:
            messages.error(request, "Documento y Ficha SENA son requeridos.")
            return redirect('prestamo_usuario')

        with transaction.atomic():
            nuevo = Prestamo.objects.create(
                documento=documento,
                ficha=ficha,
                usuario=request.user if request.user.is_authenticated else None,
                estado=EstadoPrestamo.PENDIENTE,
                observaciones=observaciones
            )

            for h_id, cant in zip(herramientas_ids, cantidades):
                if not h_id:
                    continue
                try:
                    cant_num = int(cant)
                    herramienta = Herramienta.objects.get(pk=h_id)
                    DetallePrestamo.objects.create(
                        prestamo=nuevo,
                        herramienta=herramienta,
                        cantidad=cant_num
                    )
                except (ValueError, Herramienta.DoesNotExist):
                    continue

        messages.success(request, f"Solicitud #{nuevo.pk} enviada correctamente.")
    return redirect('prestamo_usuario')
