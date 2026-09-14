from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView
from common.mixins import sesion_requerida, SesionRequeridaMixin

from .models import (
    CategoriaHerramienta,
    DetalleTraslado,
    Herramienta,
    Traslado,
    Proveedor,
    Suministro,
)
from .forms import (
    HerramientaForm,
    CategoriaHerramientaForm,
    ProveedorForm,
    TrasladoForm,
    DetalleTrasladoForm,
)
from almacen.models import Almacen, Estante
from usuario.models import Usuario


@sesion_requerida
def inventario_view(request):
    """Vista principal del Inventario de Herramientas y Catálogo de Equipos."""
    herramientas = Herramienta.objects.select_related(
        'codigo_categoria', 'codigo_suministro', 'estante', 'estante__codigo_almacen'
    ).all()
    categorias = CategoriaHerramienta.objects.all()
    almacenes = Almacen.objects.all()
    estantes = Estante.objects.select_related('codigo_almacen').all()
    usuarios_sistema = Usuario.objects.all()

    es_admin = request.session.get('usuario_rol', '').lower() in ['admin', 'administrador']

    if request.method == 'POST':
        if not es_admin:
            messages.error(request, 'No tienes permisos de administrador para realizar modificaciones en inventario.')
            return redirect('inventario')

        accion = request.POST.get('accion')

        if accion == 'crear_producto':
            form = HerramientaForm(request.POST)
            if form.is_valid():
                producto = form.save(commit=False)
                if not producto.disponibilidad:
                    producto.disponibilidad = 'Disponible'
                producto.save()
                messages.success(request, f"Herramienta '{producto.nombre_herramienta}' registrada con éxito en inventario.")
            else:
                for f, errs in form.errors.items():
                    for err in errs:
                        messages.error(request, f"{f}: {err}")
            return redirect('inventario')

        elif accion == 'editar_producto':
            pk = request.POST.get('producto_id')
            herramienta = get_object_or_404(Herramienta, pk=pk)
            form = HerramientaForm(request.POST, instance=herramienta)
            if form.is_valid():
                form.save()
                messages.success(request, f"Herramienta '{herramienta.nombre_herramienta}' actualizada correctamente.")
            else:
                for f, errs in form.errors.items():
                    for err in errs:
                        messages.error(request, f"{f}: {err}")
            return redirect('inventario')

        elif accion == 'crear_categoria':
            data_cat = {
                'nombre_categoria': request.POST.get('cat_nombre') or request.POST.get('nombre_categoria', ''),
                'tipo_herramienta': request.POST.get('cat_tipo') or request.POST.get('tipo_herramienta', 'General'),
                'descripcion': request.POST.get('cat_descripcion') or request.POST.get('descripcion', ''),
            }
            form_cat = CategoriaHerramientaForm(data_cat)
            if form_cat.is_valid():
                cat = form_cat.save()
                messages.success(request, f"Categoría '{cat.nombre_categoria}' creada con éxito.")
            else:
                for f, errs in form_cat.errors.items():
                    for err in errs:
                        messages.error(request, f"Categoría: {err}")
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
        'es_admin': es_admin,
    }
    return render(request, 'inventario.html', context)


# Vistas genéricas para Herramienta
class HerramientaListView(SesionRequeridaMixin, ListView):
    model = Herramienta
    template_name = "herramienta/herramienta_list.html"
    context_object_name = "herramientas"


class HerramientaDetailView(SesionRequeridaMixin, DetailView):
    model = Herramienta
    template_name = "herramienta/herramienta_detail.html"
    context_object_name = "herramienta"


# Vistas para CategoriaHerramienta
class CategoriaHerramientaListView(SesionRequeridaMixin, ListView):
    model = CategoriaHerramienta
    template_name = "herramienta/categoria_list.html"
    context_object_name = "categorias"


class CategoriaHerramientaDetailView(SesionRequeridaMixin, DetailView):
    model = CategoriaHerramienta
    template_name = "herramienta/categoria_detail.html"
    context_object_name = "categoria"


# Vistas para Traslado
class TrasladoListView(SesionRequeridaMixin, ListView):
    model = Traslado
    template_name = "herramienta/traslado_list.html"
    context_object_name = "traslados"


class TrasladoDetailView(SesionRequeridaMixin, DetailView):
    model = Traslado
    template_name = "herramienta/traslado_detail.html"
    context_object_name = "traslado"


# Vistas para DetalleTraslado
class DetalleTrasladoListView(SesionRequeridaMixin, ListView):
    model = DetalleTraslado
    template_name = "herramienta/detalle_traslado_list.html"
    context_object_name = "detalles_traslado"


class DetalleTrasladoDetailView(SesionRequeridaMixin, DetailView):
    model = DetalleTraslado
    template_name = "herramienta/detalle_traslado_detail.html"
    context_object_name = "detalle_traslado"


# Vistas para Proveedor
class ProveedorListView(SesionRequeridaMixin, ListView):
    model = Proveedor
    template_name = "proveedores.html"
    context_object_name = "proveedores"


class ProveedorCreateView(SesionRequeridaMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = "proveedores.html"
    success_url = reverse_lazy('herramienta:proveedor_list')

    def dispatch(self, request, *args, **kwargs):
        rol = request.session.get('usuario_rol', '').lower()
        if rol not in ('admin', 'administrador') and not request.user.is_staff:
            messages.error(request, 'Solo los administradores pueden registrar proveedores.')
            return redirect('herramienta:proveedor_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Proveedor registrado con éxito.")
        return super().form_valid(form)


@sesion_requerida
def api_estantes(request):
    """
    Devuelve los estantes de un almacén específico en formato JSON.
    Usado por el dropdown encadenado almacén → estante.
    Espera ?almacen_id=<id> como query param.
    """
    almacen_id = request.GET.get('almacen_id')

    if not almacen_id or not almacen_id.isdigit():
        return JsonResponse({'error': 'almacen_id es requerido y debe ser numérico'}, status=400)

    estantes = Estante.objects.filter(
        codigo_almacen_id=almacen_id
    ).select_related('codigo_almacen').order_by('codigo')

    data = [
        {
            'id': estante.pk,
            'codigo': estante.codigo,
            'ubicacion': f"AL{estante.codigo_almacen_id}-ES{estante.pk}",
        }
        for estante in estantes
    ]

    return JsonResponse({'estantes': data})