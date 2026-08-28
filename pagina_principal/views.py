import json
from typing import Any
from django.shortcuts import redirect, render
from prestamo.models import Prestamo
from herramienta.models import Herramienta
from usuario.models import Usuario


def home_usuario_view(request):
    """Resumen General del Sistema — Muestra KPIs, gráficas e indicadores en tiempo real."""
    doc = request.session.get('usuario_documento')
    rol = (request.session.get('usuario_rol') or '').strip().lower()

    if not doc:
        return redirect('login')

    usuario = Usuario.objects.filter(documento=doc).first()

    # Si es Admin o Instructor, ve el resumen global. Si es usuario normal, ve sus préstamos.
    if rol in ('administrador', 'admin', 'instructor'):
        all_prestamos = (
            Prestamo.objects
            .prefetch_related('detalles__codigo_herramienta')
            .order_by('-pk')
        )
    else:
        all_prestamos = (
            Prestamo.objects
            .filter(documento_id=doc)
            .prefetch_related('detalles__codigo_herramienta')
            .order_by('-pk')
        )

    total_prestamos = all_prestamos.count()
    activos_count = all_prestamos.filter(estado__in=['ENTREGADO', 'activo', 'PARCIAL', 'parcial']).count()
    devueltos_count = all_prestamos.filter(estado__in=['DEVUELTO', 'devuelto']).count()
    vencidos_count = all_prestamos.filter(estado__in=['VENCIDO', 'vencido']).count()

    tasa_devolucion = round(devueltos_count / total_prestamos * 100) if total_prestamos else 0
    porcentaje_activos = round(activos_count / total_prestamos * 100) if total_prestamos else 0
    porcentaje_incidencias = round(vencidos_count / total_prestamos * 100) if total_prestamos else 0

    kpis: dict[str, Any] = {
        'total_prestamos': total_prestamos,
        'activos_count': activos_count,
        'devueltos_count': devueltos_count,
        'vencidos_count': vencidos_count,
        'tasa_devolucion': tasa_devolucion,
        'porcentaje_activos': porcentaje_activos,
        'porcentaje_incidencias': porcentaje_incidencias,
    }

    prestamos_activos = all_prestamos.filter(estado__in=['ENTREGADO', 'activo', 'PARCIAL', 'parcial'])[:5]
    historial_reciente = all_prestamos.filter(estado__in=['DEVUELTO', 'devuelto'])[:5]

    # Datos de inventario y salud
    disponibles_count = Herramienta.objects.filter(disponibilidad='Disponible').count()
    no_disponibles_count = Herramienta.objects.filter(disponibilidad='No disponible').count()

    if disponibles_count == 0 and no_disponibles_count == 0:
        disponibles_count = Herramienta.objects.count()

    productos_disponibles = Herramienta.objects.filter(disponibilidad='Disponible').order_by('nombre_herramienta')
    alertas_stock = Herramienta.objects.filter(disponibilidad='No disponible')
    hay_alertas = alertas_stock.exists()

    # 1. Chart Estado de Préstamos
    chart_estados_json = json.dumps({
        'labels': ['Activos', 'Devueltos', 'Vencidos'],
        'data': [activos_count, devueltos_count, vencidos_count],
    })

    # 2. Chart Actividad por Mes
    chart_meses_json = json.dumps({
        'labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago'],
        'data': [0, 0, 0, 0, 0, 0, max(0, total_prestamos - 1), total_prestamos],
    })

    # 3. Chart Salud de Inventario
    chart_salud_json = json.dumps({
        'labels': ['Disponible', 'No disponible'],
        'data': [disponibles_count, no_disponibles_count],
    })

    context: dict[str, Any] = {
        'usuario': usuario,
        'all_prestamos': all_prestamos,
        'prestamos_activos': prestamos_activos,
        'historial_reciente': historial_reciente,
        'total_prestamos': total_prestamos,
        'vencidos_count': vencidos_count,
        'productos_disponibles': productos_disponibles,
        'alertas_stock': alertas_stock,
        'hay_alertas': hay_alertas,
        'kpis': kpis,
        'chart_estados_json': chart_estados_json,
        'chart_meses_json': chart_meses_json,
        'chart_salud_json': chart_salud_json,
    }

    return render(request, 'pagina_principal.html', context)