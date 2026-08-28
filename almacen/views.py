from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from .forms import EstanteForm, AlmacenForm
from .models import Estante, Almacen
from common.mixins import sesion_requerida
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from django.http import HttpResponse
from django.conf import settings

@sesion_requerida
def vista_almacenes(request):
    almacenes = Almacen.objects.all()
    form = AlmacenForm()
    form_editar = None          # ← para devolver errores al modal editar
    show_modal_editar = False   # ← para reabrir el modal editar

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear':
            form = AlmacenForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('almacenes')
            # si hay errores, show_modal=True abre el modal crear

        elif accion == 'editar':
            pk = request.POST.get('almacen_id')
            almacen = get_object_or_404(Almacen, pk=pk)
            form_editar = AlmacenForm(request.POST, instance=almacen)
            if form_editar.is_valid():
                form_editar.save()
                return redirect('almacenes')
            # si hay errores, se devuelve form_editar con mensajes
            show_modal_editar = True

        elif accion == 'eliminar':
            pk = request.POST.get('almacen_id')
            get_object_or_404(Almacen, pk=pk).delete()
            return redirect('almacenes')

    context = {
        'almacenes': almacenes,
        'form': form,
        'form_editar': form_editar,
        'show_modal': bool(form.errors),
        'show_modal_editar': show_modal_editar,
        'total_almacenes': almacenes.count(),
        'total_estantes': Estante.objects.count(),
    }


    return render(request, 'almacenes.html', context)


@sesion_requerida
def vista_estantes(request):
    estantes = Estante.objects.all()
    form = EstanteForm()
    form_editar = None          # ← para devolver errores al modal editar
    show_modal_editar = False

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear':
            form = EstanteForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('estantes')

        elif accion == 'editar':
            pk = request.POST.get('estante_id')
            estante = get_object_or_404(Estante, pk=pk)
            form_editar = EstanteForm(request.POST, instance=estante)
            if form_editar.is_valid():
                form_editar.save()
                return redirect('estantes')
            show_modal_editar = True

        elif accion == 'eliminar':
            pk = request.POST.get('estante_id')
            get_object_or_404(Estante, pk=pk).delete()
            return redirect('estantes')

    context = {
        'estantes': estantes,
        'almacenes': Almacen.objects.all(),
        'form': form,
        'form_editar': form_editar,
        'show_modal': bool(form.errors),
        'show_modal_editar': show_modal_editar,
        'total_estantes': estantes.count(),           # ← agregar
        'total_almacenes': Almacen.objects.count(),   # ← agregar
    }


    return render(request, 'estantes.html', context)


@sesion_requerida
def crear_estante(request):
    return redirect('estantes')

def detalle_almacen(request, pk):
    almacen = get_object_or_404(Almacen, pk=pk)
    estantes = Estante.objects.filter(almacen=almacen)
    context = {
        'almacen': almacen,
        'estantes': estantes,
    }

    return render(request, 'detalle_almacen.html', context)