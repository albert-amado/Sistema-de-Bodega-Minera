import json

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from herramienta.models import Herramienta
from usuario.models import Usuario
from usuario.decorators import login_required, admin_required

from .models import (
    DetallePrestamo,
    DevolucionHerramienta,
    EstadoPrestamo,
    Prestamo,
)


def notificaciones_json(request):
    """Endpoint para obtener notificaciones en JSON."""
    return JsonResponse({"items": []})


@login_required
def prestamo_lista(request):
    """Vista principal para la gestión de préstamos (Admin)."""
    prestamos_qs = (
        Prestamo.objects.prefetch_related(
            "detalles__codigo_herramienta", "devoluciones"
        )
        .select_related("documento")
        .order_by("-pk")
    )

    # Filtro opcional por estado
    estado_filtro = request.GET.get("estado")
    if estado_filtro:
        prestamos_qs = prestamos_qs.filter(estado=estado_filtro)

    # Conteos para tarjetas KPI
    total_prestamos = Prestamo.objects.count()
    activos = Prestamo.objects.filter(estado=EstadoPrestamo.ENTREGADO).count()
    pendientes = Prestamo.objects.filter(
        estado=EstadoPrestamo.PENDIENTE
    ).count()
    devueltos = Prestamo.objects.filter(estado=EstadoPrestamo.DEVUELTO).count()
    cancelados = Prestamo.objects.filter(
        estado=EstadoPrestamo.CANCELADO
    ).count()

    herramientas_qs = Herramienta.objects.all()
    usuarios_qs = Usuario.objects.all()

    # Formateo JSON para scripts en plantilla
    herramientas_json = [
        {
            "pk": h.pk,
            "codigo": h.codigo,
            "nombre": h.nombre,
            "stock_disponible": h.stock_disponible,
        }
        for h in herramientas_qs
    ]

    usuarios_json = [
        {
            "pk": u.pk,
            "username": u.documento,
            "nombre_completo": u.nombre_completo or u.documento,
            "documento": u.documento,
        }
        for u in usuarios_qs
    ]

    doc_sesion = request.session.get('usuario_documento')
    usuario_actual = Usuario.objects.filter(documento=doc_sesion).first() if doc_sesion else None

    context = {
        "all_prestamos": prestamos_qs,
        "prestamos": prestamos_qs,
        "total_prestamos": total_prestamos,
        "activos": activos,
        "pendientes": pendientes,
        "devueltos": devueltos,
        "cancelados": cancelados,
        "herramientas_disponibles": herramientas_qs,
        "productos_disponibles": herramientas_qs,
        "productos": herramientas_qs,
        "usuarios": usuarios_qs,
        "usuario": usuario_actual,
        "herramientas_json": json.dumps(herramientas_json),
        "productos_json": json.dumps(herramientas_json),
        "usuarios_json": json.dumps(usuarios_json),
    }
    return render(request, "prestamo.html", context)


@login_required
def prestamo_usuario_lista(request):
    """Vista de préstamos para la interfaz de Usuario."""
    doc_sesion = request.session.get('usuario_documento')

    if doc_sesion:
        prestamos_qs = (
            Prestamo.objects.filter(documento_id=doc_sesion)
            .prefetch_related("detalles__codigo_herramienta")
            .order_by("-pk")
        )
    else:
        prestamos_qs = (
            Prestamo.objects.all()
            .prefetch_related("detalles__codigo_herramienta")
            .order_by("-pk")
        )

    total_prestamos = prestamos_qs.count()
    total_activos = prestamos_qs.filter(
        estado=EstadoPrestamo.ENTREGADO
    ).count()
    vencidos_count = 0
    proximos_vencer = 0

    herramientas_qs = Herramienta.objects.all()
    usuario_obj = Usuario.objects.filter(documento=doc_sesion).first() if doc_sesion else None

    context = {
        "all_prestamos": prestamos_qs,
        "total_prestamos": total_prestamos,
        "total_activos": total_activos,
        "vencidos_count": vencidos_count,
        "proximos_vencer": proximos_vencer,
        "herramientas_disponibles": herramientas_qs,
        "productos_disponibles": herramientas_qs,
        "productos": herramientas_qs,
        "usuario": usuario_obj,
    }
    return render(request, "prestamo_usuario.html", context)


@login_required
@transaction.atomic
def crear_prestamo(request):
    """Procesa la creación de un nuevo préstamo (Wizard Admin)."""
    if request.method == "POST":
        documento = request.POST.get("documento", "").strip()
        ficha = request.POST.get("ficha", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()
        herramientas_ids = request.POST.getlist("herramienta[]")
        cantidades = request.POST.getlist("cantidad[]")

        if not documento or not ficha:
            messages.error(
                request, "El documento y la ficha SENA son obligatorios."
            )
            return redirect("inventario")

        if not herramientas_ids:
            messages.error(
                request, "Debes seleccionar al menos una herramienta."
            )
            return redirect("inventario")

        usuario_obj = Usuario.objects.filter(documento=documento).first()

        nuevo_prestamo = Prestamo.objects.create(
            documento=usuario_obj,
            ficha=ficha,
            estado=EstadoPrestamo.PENDIENTE,
            observaciones=observaciones,
        )

        for h_id, cant in zip(herramientas_ids, cantidades):
            if not h_id:
                continue
            try:
                cant_num = int(cant)
                herramienta = Herramienta.objects.get(pk=h_id)
                DetallePrestamo.objects.create(
                    codigo_prestamo=nuevo_prestamo,
                    codigo_herramienta=herramienta,
                    cantidad=cant_num,
                )
            except (ValueError, Herramienta.DoesNotExist):
                continue

        messages.success(
            request, f"Préstamo #{nuevo_prestamo.pk} registrado con éxito."
        )
    return redirect("inventario")


@login_required
def aprobar_prestamo(request):
    """Aprueba una solicitud de préstamo y descuenta stock."""
    if request.method == "POST":
        pk = request.POST.get("pk")
        prestamo = get_object_or_404(Prestamo, pk=pk)

        with transaction.atomic():
            for detalle in prestamo.detalles.select_related("codigo_herramienta"):
                h = detalle.codigo_herramienta
                if h and h.stock_disponible >= detalle.cantidad:
                    h.stock_disponible -= detalle.cantidad
                    h.save()
                elif h:
                    messages.error(
                        request, f"Stock insuficiente para {h.nombre}."
                    )
                    return redirect("inventario")

            prestamo.estado = EstadoPrestamo.ENTREGADO
            prestamo.save()
            messages.success(
                request, f"Préstamo #{prestamo.pk} aprobado y entregado."
            )

    return redirect("inventario")


@login_required
def rechazar_prestamo(request):
    """Rechaza / Cancela una solicitud de préstamo."""
    if request.method == "POST":
        pk = request.POST.get("pk")
        motivo = request.POST.get("motivo_rechazo", "")
        prestamo = get_object_or_404(Prestamo, pk=pk)

        prestamo.estado = EstadoPrestamo.CANCELADO
        if motivo:
            prestamo.observaciones = (
                prestamo.observaciones or ""
            ) + f" | Cancelado: {motivo}"
        prestamo.save()
        messages.warning(request, f"Préstamo #{prestamo.pk} rechazado.")

    return redirect("inventario")


@login_required
def devoluciones_lista(request):
    """Vista principal para la gestión de devoluciones (Admin)."""
    devoluciones_qs = (
        DevolucionHerramienta.objects.select_related(
            "codigo_prestamo__documento", "codigo_recibe"
        )
        .prefetch_related("codigo_prestamo__detalles__codigo_herramienta")
        .order_by("-pk")
    )
    prestamos_activos = (
        Prestamo.objects.filter(
            estado__in=[EstadoPrestamo.ENTREGADO, EstadoPrestamo.PARCIAL]
        )
        .prefetch_related("detalles__codigo_herramienta")
        .select_related("documento")
        .order_by("-pk")
    )

    doc_sesion = request.session.get('usuario_documento')
    usuario_actual = Usuario.objects.filter(documento=doc_sesion).first() if doc_sesion else None

    context = {
        "devoluciones": devoluciones_qs,
        "prestamos_activos": prestamos_activos,
        "usuario": usuario_actual,
    }
    return render(request, "devoluciones.html", context)


@login_required
def devolver_prestamo(request):
    """Registra la devolución de herramientas de un préstamo."""
    if request.method == "POST":
        pk = request.POST.get("pk") or request.POST.get("prestamo_id")
        if pk:
            prestamo = get_object_or_404(Prestamo, pk=pk)

            with transaction.atomic():
                for detalle in prestamo.detalles.select_related("codigo_herramienta"):
                    h = detalle.codigo_herramienta
                    if h:
                        h.stock_disponible += detalle.cantidad
                        h.save()

                devolucion_total = (
                    request.POST.get("devolucion_total") != "false"
                )
                if devolucion_total:
                    prestamo.estado = EstadoPrestamo.DEVUELTO
                else:
                    prestamo.estado = EstadoPrestamo.PARCIAL
                prestamo.save()

                obs = (
                    request.POST.get("observaciones")
                    or request.POST.get("motivo")
                    or "Devolución registrada"
                )

                doc_sesion = request.session.get('usuario_documento')
                rec_por = Usuario.objects.filter(documento=doc_sesion).first() if doc_sesion else None

                DevolucionHerramienta.objects.create(
                    codigo_prestamo=prestamo,
                    codigo_recibe=rec_por,
                    observaciones=obs,
                )
                messages.success(
                    request,
                    f"Devolución del Préstamo #{prestamo.pk} completada.",
                )

    referer = request.META.get("HTTP_REFERER", "")
    if "devoluciones" in referer:
        return redirect("devoluciones")
    return redirect("inventario")


@login_required
def editar_prestamo(request):
    """Actualiza las observaciones de un préstamo existente."""
    if request.method == "POST":
        pk = request.POST.get("pk")
        observaciones = request.POST.get("observaciones", "")
        prestamo = get_object_or_404(Prestamo, pk=pk)
        prestamo.observaciones = observaciones
        prestamo.save()
        messages.success(request, f"Préstamo #{prestamo.pk} actualizado.")
    return redirect("inventario")


@login_required
def usuario_solicitar_prestamo(request):
    """Procesa la solicitud de préstamo enviada desde el portal de usuario."""
    if request.method == "POST":
        documento = request.POST.get("documento", "").strip()
        ficha = request.POST.get("ficha", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()
        herramientas_ids = request.POST.getlist("herramienta[]")
        cantidades = request.POST.getlist("cantidad[]")

        if not documento or not ficha:
            messages.error(request, "Documento y Ficha SENA son requeridos.")
            return redirect("pagina_principal")

        with transaction.atomic():
            usr = Usuario.objects.filter(documento=documento).first()
            nuevo = Prestamo.objects.create(
                documento=usr,
                ficha=ficha,
                estado=EstadoPrestamo.PENDIENTE,
                observaciones=observaciones,
            )

            for h_id, cant in zip(herramientas_ids, cantidades):
                if not h_id:
                    continue
                try:
                    cant_num = int(cant)
                    herramienta = Herramienta.objects.get(pk=h_id)
                    DetallePrestamo.objects.create(
                        codigo_prestamo=nuevo,
                        codigo_herramienta=herramienta,
                        cantidad=cant_num,
                    )
                except (ValueError, Herramienta.DoesNotExist):
                    continue

        messages.success(
            request, f"Solicitud #{nuevo.pk} enviada correctamente."
        )
    return redirect("pagina_principal")
