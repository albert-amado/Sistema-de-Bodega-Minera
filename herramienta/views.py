from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import DetailView, ListView
from common.mixins import sesion_requerida

from .models import (
    CategoriaHerramienta,
    DetalleTraslado,
    Herramienta,
    Traslado,
    Proveedor,
    Suministro,
)
from almacen.models import Almacen, Estante
from usuario.models import Usuario


@sesion_requerida
def inventario_view(request):
    """Vista principal del Inventario de Herramientas y Catálogo de Equipos."""
    herramientas = Herramienta.objects.select_related('codigo_categoria', 'codigo_suministro').all()
    categorias = CategoriaHerramienta.objects.all()
    almacenes = Almacen.objects.all()
    estantes = Estante.objects.select_related('almacen').all()
    usuarios_sistema = Usuario.objects.all()

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear_producto':
            sku = request.POST.get('codigo_sku', '').strip()
            nombre = request.POST.get('nombre', '').strip()
            cat_id = request.POST.get('categoria')
            descripcion = request.POST.get('descripcion', '').strip()

            cat = CategoriaHerramienta.objects.filter(pk=cat_id).first() if cat_id else None
            Herramienta.objects.create(
                codigo_sku=sku,
                nombre_herramienta=nombre,
                codigo_categoria=cat,
                descripcion=descripcion,
                disponibilidad='Disponible'
            )
            messages.success(request, f"Herramienta '{nombre}' registrada con éxito en inventario.")
            return redirect('inventario')

        elif accion == 'editar_producto':
            pk = request.POST.get('producto_id')
            herramienta = get_object_or_404(Herramienta, pk=pk)
            herramienta.nombre_herramienta = request.POST.get('nombre', herramienta.nombre_herramienta)
            herramienta.codigo_sku = request.POST.get('codigo_sku', herramienta.codigo_sku)
            herramienta.descripcion = request.POST.get('descripcion', herramienta.descripcion)
            cat_id = request.POST.get('categoria')
            if cat_id:
                herramienta.codigo_categoria = CategoriaHerramienta.objects.filter(pk=cat_id).first()
            herramienta.save()
            messages.success(request, f"Herramienta '{herramienta.nombre_herramienta}' actualizada.")
            return redirect('inventario')

        elif accion == 'crear_categoria':
            cat_nombre = request.POST.get('cat_nombre', '').strip()
            cat_desc = request.POST.get('cat_descripcion', '').strip()
            if cat_nombre:
                CategoriaHerramienta.objects.create(nombre=cat_nombre, descripcion=cat_desc)
                messages.success(request, f"Categoría '{cat_nombre}' creada con éxito.")
            return redirect('inventario')

    total_productos = herramientas.count()
    sin_stock = herramientas.filter(disponibilidad='No disponible').count()
    disponibles = herramientas.filter(disponibilidad='Disponible').count()

    context = {
        'productos': herramientas,
        'categorias': categorias,
        'almacenes': almacenes,
        'estantes': estantes,
        'usuarios_sistema': usuarios_sistema,
        'total': total_productos,
        'kpi_total_productos': total_productos,
        'kpi_total_stock': total_productos,
        'kpi_sin_stock': sin_stock,
        'kpi_stock_bajo': 0,
    }
    return render(request, 'inventario.html', context)


# Vistas genéricas para Herramienta
class HerramientaListView(ListView):
    model = Herramienta
    template_name = "herramienta/herramienta_list.html"
    context_object_name = "herramientas"


class HerramientaDetailView(DetailView):
    model = Herramienta
    template_name = "herramienta/herramienta_detail.html"
    context_object_name = "herramienta"


# Vistas para CategoriaHerramienta
class CategoriaHerramientaListView(ListView):
    model = CategoriaHerramienta
    template_name = "herramienta/categoria_list.html"
    context_object_name = "categorias"


class CategoriaHerramientaDetailView(DetailView):
    model = CategoriaHerramienta
    template_name = "herramienta/categoria_detail.html"
    context_object_name = "categoria"


# Vistas para Traslado
class TrasladoListView(ListView):
    model = Traslado
    template_name = "herramienta/traslado_list.html"
    context_object_name = "traslados"


class TrasladoDetailView(DetailView):
    model = Traslado
    template_name = "herramienta/traslado_detail.html"
    context_object_name = "traslado"


# Vistas para DetalleTraslado
class DetalleTrasladoListView(ListView):
    model = DetalleTraslado
    template_name = "herramienta/detalle_traslado_list.html"
    context_object_name = "detalles_traslado"


class DetalleTrasladoDetailView(DetailView):
    model = DetalleTraslado
    template_name = "herramienta/detalle_traslado_detail.html"
    context_object_name = "detalle_traslado"
