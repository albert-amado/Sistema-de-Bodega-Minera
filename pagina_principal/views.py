import json
from datetime import date
from typing import Any

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from prestamo.models import Prestamo, DevolucionHerramienta, EstadoPrestamo
from herramienta.models import Herramienta
from usuario.models import Usuario

MESES_ABREV = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def _rango_ultimos_6_meses(hoy: date) -> list[tuple[int, int]]:
    """[(año, mes), ...] de los últimos 6 meses (incluye actual), orden cronológico."""
    meses: list[tuple[int, int]] = []
    anio, mes = hoy.year, hoy.month
    for _ in range(6):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            mes, anio = 12, anio - 1
    return list(reversed(meses))


def _tendencia_meses(qs, hoy: date) -> dict[str, list]:
    """Total y devueltos por mes para el queryset dado."""
    rango = _rango_ultimos_6_meses(hoy)
    fecha_inicio = date(rango[0][0], rango[0][1], 1)

    filas = (
        qs.filter(fecha__gte=fecha_inicio)
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(
            total=Count('codigo_prestamo'),
            devueltos=Count('codigo_prestamo', filter=Q(estado__in=['DEVUELTO', 'devuelto'])),
        )
    )
    mapa_total = {(f['mes'].year, f['mes'].month): f['total'] for f in filas if f['mes']}
    mapa_devueltos = {(f['mes'].year, f['mes'].month): f['devueltos'] for f in filas if f['mes']}

    labels = [MESES_ABREV[m - 1] for _, m in rango]
    data_total = [mapa_total.get((a, m), 0) for a, m in rango]
    data_devueltos = [mapa_devueltos.get((a, m), 0) for a, m in rango]
    return {
        'labels': labels,
        'total': data_total,
        'devueltos': data_devueltos,
        'data': data_total,
    }


def home_usuario_view(request):
    """Home principal — muestra préstamos, KPIs, gráficas y devoluciones."""
    doc = request.session.get('usuario_documento')
    if not doc:
        return redirect('login')

    try:
        usuario = Usuario.objects.get(documento=doc)
    except Usuario.DoesNotExist:
        return redirect('login')

    es_admin = request.session.get('usuario_rol', '').lower() in ['admin', 'administrador']

    # ── Si es admin ve el consolidado de todo el sistema; si no, ve sus préstamos personales ──
    if es_admin:
        all_prestamos = (
            Prestamo.objects
            .select_related('documento')
            .prefetch_related('detalles__codigo_herramienta__codigo_categoria')
            .annotate(num_items=Count('detalles'))
            .order_by('-fecha', '-codigo_prestamo')
        )
    else:
        all_prestamos = (
            Prestamo.objects
            .select_related('documento')
            .prefetch_related('detalles__codigo_herramienta__codigo_categoria')
            .annotate(num_items=Count('detalles'))
            .filter(documento=doc)
            .order_by('-fecha', '-codigo_prestamo')
        )

    # ── Conteo de estados respetando los valores del modelo MER (ENTREGADO, DEVUELTO, PENDIENTE, CANCELADO) ──
    estados = all_prestamos.aggregate(
        total=Count('codigo_prestamo'),
        activos_count=Count('codigo_prestamo', filter=Q(estado__in=['ENTREGADO', 'PARCIAL', 'activo', 'parcial'])),
        devueltos_count=Count('codigo_prestamo', filter=Q(estado__in=['DEVUELTO', 'devuelto'])),
        pendientes_count=Count('codigo_prestamo', filter=Q(estado__in=['PENDIENTE', 'pendiente'])),
        cancelados_count=Count('codigo_prestamo', filter=Q(estado__in=['CANCELADO', 'cancelado'])),
    )
    total_prestamos = estados['total'] or 0
    activos_count = estados['activos_count'] or 0
    devueltos_count = estados['devueltos_count'] or 0
    pendientes_count = estados['pendientes_count'] or 0
    cancelados_count = estados['cancelados_count'] or 0

    tasa_devolucion = round((devueltos_count / total_prestamos) * 100) if total_prestamos else 0
    porcentaje_activos = round((activos_count / total_prestamos) * 100) if total_prestamos else 0
    porcentaje_incidencias = round((cancelados_count / total_prestamos) * 100) if total_prestamos else 0

    kpis: dict[str, Any] = {
        'total_prestamos': total_prestamos,
        'activos_count': activos_count,
        'devueltos_count': devueltos_count,
        'pendientes_count': pendientes_count,
        'vencidos_count': cancelados_count,
        'tasa_devolucion': tasa_devolucion,
        'porcentaje_activos': porcentaje_activos,
        'porcentaje_incidencias': porcentaje_incidencias,
    }

    prestamos_activos = all_prestamos.filter(estado__in=['ENTREGADO', 'PARCIAL', 'activo', 'parcial'])
    historial_reciente = all_prestamos.filter(estado__in=['DEVUELTO', 'devuelto'])

    # ── Disponibilidad de Herramientas ──
    total_herramientas = Herramienta.objects.count()
    sin_stock = Herramienta.objects.filter(Q(disponibilidad='No disponible') | Q(disponibilidad='0')).count()
    disponibles = max(0, total_herramientas - sin_stock)

    productos_disponibles = Herramienta.objects.exclude(Q(disponibilidad='No disponible') | Q(disponibilidad='0')).order_by('nombre_herramienta')
    alertas_stock = list(
        Herramienta.objects.filter(Q(disponibilidad='No disponible') | Q(disponibilidad='0'))
        .values_list('nombre_herramienta', flat=True)
    )
    hay_alertas = len(alertas_stock) > 0

    # ── Devoluciones Recientes ──
    if es_admin:
        devoluciones_recientes = (
            DevolucionHerramienta.objects
            .select_related('codigo_prestamo__documento', 'codigo_recibe')
            .order_by('-fecha', '-codigo_devolucion')[:5]
        )
    else:
        devoluciones_recientes = (
            DevolucionHerramienta.objects
            .filter(codigo_prestamo__documento=doc)
            .select_related('codigo_prestamo__documento', 'codigo_recibe')
            .order_by('-fecha', '-codigo_devolucion')[:5]
        )

    # ── Datos de Gráficas para Chart.js ──
    hoy = timezone.localdate()
    tendencia = _tendencia_meses(all_prestamos, hoy)

    chart_estados_json = json.dumps({
        'labels': ['Activos', 'Devueltos', 'Pendientes', 'Cancelados'],
        'data': [activos_count, devueltos_count, pendientes_count, cancelados_count],
        'colors': ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
    })
    chart_meses_json = json.dumps(tendencia)
    chart_salud_json = json.dumps({
        'labels': ['Disponible', 'Sin Stock / Mantenimiento'],
        'data': [disponibles, sin_stock],
    })

    context: dict[str, Any] = {
        'usuario': usuario,
        'all_prestamos': all_prestamos,
        'prestamos_activos': prestamos_activos,
        'historial_reciente': historial_reciente,
        'total_prestamos': total_prestamos,
        'vencidos_count': cancelados_count,
        'productos_disponibles': productos_disponibles,
        'alertas_stock': alertas_stock,
        'hay_alertas': hay_alertas,
        'devoluciones_recientes': devoluciones_recientes,
        'kpis': kpis,
        'chart_estados_json': chart_estados_json,
        'chart_meses_json': chart_meses_json,
        'chart_salud_json': chart_salud_json,
    }

    return render(request, 'pagina_principal.html', context)