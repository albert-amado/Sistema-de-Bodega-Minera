from django.contrib import admin

from .models import DetallePrestamo, DevolucionHerramienta, Prestamo


class DetallePrestamoInline(admin.TabularInline):
    model = DetallePrestamo
    extra = 1
    autocomplete_fields = ["herramienta"]


class DevolucionHerramientaInline(admin.StackedInline):
    model = DevolucionHerramienta
    extra = 0


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ("id", "documento", "ficha", "fecha", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("documento", "ficha")
    inlines = [DetallePrestamoInline, DevolucionHerramientaInline]


@admin.register(DevolucionHerramienta)
class DevolucionHerramientaAdmin(admin.ModelAdmin):
    list_display = ("id", "prestamo", "codigo_recibe", "fecha")
    list_filter = ("fecha",)
    search_fields = ("codigo_recibe", "prestamo__documento")
