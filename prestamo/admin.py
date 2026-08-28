from django.contrib import admin

from .models import DetallePrestamo, DevolucionHerramienta, Prestamo


class DetallePrestamoInline(admin.TabularInline):
    model = DetallePrestamo
    extra = 1
    autocomplete_fields = ["codigo_herramienta"]


class DevolucionHerramientaInline(admin.StackedInline):
    model = DevolucionHerramienta
    extra = 0


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ("codigo_prestamo", "documento", "ficha", "fecha", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("documento__documento", "ficha")
    inlines = [DetallePrestamoInline, DevolucionHerramientaInline]


@admin.register(DevolucionHerramienta)
class DevolucionHerramientaAdmin(admin.ModelAdmin):
    list_display = ("codigo_devolucion", "codigo_prestamo", "codigo_recibe", "fecha")
    list_filter = ("fecha",)
    search_fields = ("codigo_recibe__documento", "codigo_prestamo__documento__documento")
