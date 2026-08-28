import json
from datetime import date
from typing import Any

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

#from devoluciones.models import Devolucion
#from inventario.models import Producto
from prestamo.models import Prestamo, productos_disponibles, Producto

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


def _tendencia_meses_usuario(doc: str) -> dict[str, list]:
    """Total y devueltos por mes (últimos 6) para UN usuario. 1 sola query agregada."""
    hoy = timezone.localdate()
    rango = _rango_ultimos_6_meses(hoy)
    fecha_inicio = date(rango[0][0], rango[0][1], 1)

    filas = (
        Prestamo.objects
        .filter(documento=doc, fecha__gte=fecha_inicio)
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(
            total=Count('id'),
            devueltos=Count('id', filter=Q(estado='devuelto')),
        )
    )
    mapa_total = {(f['mes'].year, f['mes'].month): f['total'] for f in filas}
    mapa_devueltos = {(f['mes'].year, f['mes'].month): f['devueltos'] for f in filas}

    labels = [MESES_ABREV[m - 1] for _, m in rango]
    data_total = [mapa_total.get((a, m), 0) for a, m in rango]
    data_devueltos = [mapa_devueltos.get((a, m), 0) for a, m in rango]
    return {'labels': labels, 'total': data_total, 'devueltos': data_devueltos}


def home_usuario_view(request):
    """Home del usuario — muestra sus propios préstamos, KPIs y gráficas."""
    from usuario.models import Usuario

    doc = request.session.get('usuario_documento')
    if not doc:
        return redirect('login')

    try:
        usuario = Usuario.objects.get(documento=doc)
    except Usuario.DoesNotExist:
        return redirect('login')

    # ── Query única con jerarquía completa + conteo de items (evita N+1 y {{ p.items.count }}) ──
    all_prestamos = (
        Prestamo.objects
        .prefetch_related('items__codigo_herramienta__codigo_categoria')
        .annotate(num_items=Count('items'))
        .filter(documento=doc)
        .order_by('-fecha')
    )

    # ── Conteo de estados: ANTES 3 queries (.filter().count() x3) → AHORA 1 sola (aggregate) ──
    estados = all_prestamos.aggregate(
        total=Count('id'),
        activos_count=Count('id', filter=Q(estado__in=['activo', 'parcial'])),
        devueltos_count=Count('id', filter=Q(estado='devuelto')),
        vencidos_count=Count('id', filter=Q(estado='vencido')),
    )
    total_prestamos = estados['total']

    # ── Porcentajes enteros, Python puro, división protegida ──
    tasa_devolucion = round(estados['devueltos_count'] / total_prestamos * 100) if total_prestamos else 0
    porcentaje_activos = round(estados['activos_count'] / total_prestamos * 100) if total_prestamos else 0
    porcentaje_incidencias = round(estados['vencidos_count'] / total_prestamos * 100) if total_prestamos else 0

    kpis: dict[str, Any] = {
        'total_prestamos': total_prestamos,
        'activos_count': estados['activos_count'],
        'devueltos_count': estados['devueltos_count'],
        'vencidos_count': estados['vencidos_count'],
        'tasa_devolucion': tasa_devolucion,
        'porcentaje_activos': porcentaje_activos,
        'porcentaje_incidencias': porcentaje_incidencias,
    }

    # ── Querysets filtrados (reusan all_prestamos ya optimizado, sin nueva query hasta evaluar) ──
    prestamos_activos = all_prestamos.filter(estado__in=['activo', 'parcial'])
    historial_reciente = all_prestamos.filter(estado='devuelto')
    

    productos_disponibles = Producto.objects.filter(disponibilidad='Disponible').order_by('nombre_herramienta')
    alertas_stock = list(
        Producto.objects.filter(disponibilidad='No disponible')
        .values_list('nombre_herramienta', flat=True)
    )

    hay_alertas = len(alertas_stock) > 0

    # ── Gráficas ──
    tendencia = _tendencia_meses_usuario(doc)
    chart_estados_json = json.dumps({
        'labels': ['Activos', 'Devueltos', 'Vencidos'],
        'data': [estados['activos_count'], estados['devueltos_count'], estados['vencidos_count']],
    })
    chart_meses_json = json.dumps(tendencia)

    context: dict[str, Any] = {
        'usuario': usuario,
        'all_prestamos': all_prestamos,
        'prestamos_activos': prestamos_activos,
        'historial_reciente': historial_reciente,
        'total_prestamos': total_prestamos,
        'vencidos_count': estados['vencidos_count'],  # compat: template viejo puede usar esta clave suelta
        'productos_disponibles': productos_disponibles,
        'alertas_stock': alertas_stock,
        'hay_alertas': hay_alertas,
        'kpis': kpis,
        'chart_estados_json': chart_estados_json,
        'chart_meses_json': chart_meses_json,
    }

    return render(request, 'pagina_principal.html', context)