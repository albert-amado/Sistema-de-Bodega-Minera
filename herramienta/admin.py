from django.contrib import admin

from .models import (
    CategoriaHerramienta,
    DetalleTraslado,
    Herramienta,
    Traslado,
)


@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_herramienta",
        "nombre_herramienta",
        "codigo_sku",
        "disponibilidad",
        "estado",
    )
    search_fields = ("codigo_sku", "nombre_herramienta")
    list_filter = ("estado", "codigo_categoria")


@admin.register(CategoriaHerramienta)
class CategoriaHerramientaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_categoria",
        "nombre_categoria",
        "tipo_herramienta",
    )
    search_fields = ("nombre_categoria", "tipo_herramienta")


@admin.register(Traslado)
class TrasladoAdmin(admin.ModelAdmin):
    list_display = ("codigo_traslado", "fecha_movimiento", "tipo_movimiento")


@admin.register(DetalleTraslado)
class DetalleTrasladoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_detalle",
        "codigo_traslado",
        "codigo_herramienta",
        "cantidad",
    )
