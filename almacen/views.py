from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import ProtectedError, RestrictedError
from django.contrib import messages
from .forms import EstanteForm, AlmacenForm
from .models import Estante, Almacen
from common.mixins import sesion_requerida


@sesion_requerida
def vista_almacenes(request):
    almacenes = Almacen.objects.all()
    form = AlmacenForm()
    form_editar = None
    show_modal_editar = False
    es_admin = request.session.get('usuario_rol', '').lower() in ['admin', 'administrador']

    if request.method == 'POST':
        if not es_admin:
            messages.error(request, 'No tienes permisos de administrador para realizar modificaciones en almacenes.')
            return redirect('almacenes')

        accion = request.POST.get('accion')

        if accion == 'crear':
            form = AlmacenForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Almacén creado exitosamente.')
                return redirect('almacenes')
            else:
                for f, errs in form.errors.items():
                    for err in errs:
                        messages.error(request, f"{f}: {err}")

        elif accion == 'editar':
            pk = request.POST.get('almacen_id')
            almacen = get_object_or_404(Almacen, pk=pk)
            form_editar = AlmacenForm(request.POST, instance=almacen)
            if form_editar.is_valid():
                form_editar.save()
                messages.success(request, 'Almacén actualizado correctamente.')
                return redirect('almacenes')
            show_modal_editar = True

        elif accion == 'eliminar':
            pk = request.POST.get('almacen_id')
            almacen = get_object_or_404(Almacen, pk=pk)
            try:
                almacen.delete()
                messages.success(request, 'Almacén eliminado correctamente.')
            except (ProtectedError, RestrictedError):
                messages.error(request, 'No se puede eliminar el almacén porque contiene estantes o herramientas asociadas.')
            return redirect('almacenes')

    context = {
        'almacenes': almacenes,
        'form': form,
        'form_editar': form_editar,
        'show_modal': bool(form.errors),
        'show_modal_editar': show_modal_editar,
        'total_almacenes': almacenes.count(),
        'total_estantes': Estante.objects.count(),
        'es_admin': es_admin,
    }

    return render(request, 'almacen.html', context)


@sesion_requerida
def vista_estantes(request):
    estantes = Estante.objects.select_related('codigo_almacen').all()
    form = EstanteForm()
    form_editar = None
    show_modal_editar = False
    es_admin = request.session.get('usuario_rol', '').lower() in ['admin', 'administrador']

    if request.method == 'POST':
        if not es_admin:
            messages.error(request, 'No tienes permisos de administrador para realizar modificaciones en estantes.')
            return redirect('estantes')

        accion = request.POST.get('accion')

        if accion == 'crear':
            form = EstanteForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Estante creado exitosamente.')
                return redirect('estantes')
            else:
                for f, errs in form.errors.items():
                    for err in errs:
                        messages.error(request, f"{f}: {err}")

        elif accion == 'editar':
            pk = request.POST.get('estante_id')
            estante = get_object_or_404(Estante, pk=pk)
            form_editar = EstanteForm(request.POST, instance=estante)
            if form_editar.is_valid():
                form_editar.save()
                messages.success(request, 'Estante actualizado correctamente.')
                return redirect('estantes')
            show_modal_editar = True

        elif accion == 'eliminar':
            pk = request.POST.get('estante_id')
            estante = get_object_or_404(Estante, pk=pk)
            try:
                estante.delete()
                messages.success(request, 'Estante eliminado correctamente.')
            except (ProtectedError, RestrictedError):
                messages.error(request, 'No se puede eliminar el estante porque tiene herramientas asignadas.')
            return redirect('estantes')

    context = {
        'estantes': estantes,
        'almacenes': Almacen.objects.all(),
        'form': form,
        'form_editar': form_editar,
        'show_modal': bool(form.errors),
        'show_modal_editar': show_modal_editar,
        'total_estantes': estantes.count(),
        'total_almacenes': Almacen.objects.count(),
        'es_admin': es_admin,
    }

    return render(request, 'estante.html', context)


@sesion_requerida
def crear_estante(request):
    return redirect('estantes')


@sesion_requerida
def detalle_almacen(request, pk):
    almacen = get_object_or_404(Almacen, pk=pk)
    estantes = Estante.objects.filter(codigo_almacen=almacen)
    context = {
        'almacen': almacen,
        'estantes': estantes,
    }

    return render(request, 'detalle_almacen.html', context)