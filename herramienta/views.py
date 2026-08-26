from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Herramienta, CategoriaHerramienta, Traslado, DetalleTraslado

# Vistas para Herramienta
class HerramientaListView(ListView):
    model = Herramienta
    template_name = 'herramienta/herramienta_list.html'
    context_object_name = 'herramientas'

class HerramientaDetailView(DetailView):
    model = Herramienta
    template_name = 'herramienta/herramienta_detail.html'
    context_object_name = 'herramienta'

# Vistas para CategoriaHerramienta
class CategoriaHerramientaListView(ListView):
    model = CategoriaHerramienta
    template_name = 'herramienta/categoria_list.html'
    context_object_name = 'categorias'

class CategoriaHerramientaDetailView(DetailView):
    model = CategoriaHerramienta
    template_name = 'herramienta/categoria_detail.html'
    context_object_name = 'categoria'

# Vistas para Traslado
class TrasladoListView(ListView):
    model = Traslado
    template_name = 'herramienta/traslado_list.html'
    context_object_name = 'traslados'

class TrasladoDetailView(DetailView):
    model = Traslado
    template_name = 'herramienta/traslado_detail.html'
    context_object_name = 'traslado'

# Vistas para DetalleTraslado
class DetalleTrasladoListView(ListView):
    model = DetalleTraslado
    template_name = 'herramienta/detalle_traslado_list.html'
    context_object_name = 'detalles_traslado'

class DetalleTrasladoDetailView(DetailView):
    model = DetalleTraslado
    template_name = 'herramienta/detalle_traslado_detail.html'
    context_object_name = 'detalle_traslado'
