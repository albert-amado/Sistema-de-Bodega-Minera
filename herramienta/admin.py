from django.contrib import admin

from .models import (
    BitacoraEstado,
    CategoriaHerramienta,
    DetalleMantenimiento,
    DetalleTraslado,
    Herramienta,
    Mantenimiento,
    Proveedor,
    Suministro,
    Traslado,
)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("codigo_proveedor", "nit_proveedor", "telefono_contacto", "correo_proveedor")
    search_fields = ("nit_proveedor", "correo_proveedor")


@admin.register(Suministro)
class SuministroAdmin(admin.ModelAdmin):
    list_display = ("codigo_suministro", "codigo_proveedor", "fecha", "cantidad")
    list_filter = ("fecha",)


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


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ("num_mantenimiento", "codigo_herramienta", "tipo_mantenimiento", "fecha_ingreso", "fecha_salida")
    list_filter = ("tipo_mantenimiento", "fecha_ingreso")


@admin.register(DetalleMantenimiento)
class DetalleMantenimientoAdmin(admin.ModelAdmin):
    list_display = ("detalle_mantenimiento", "num_mantenimiento", "codigo_detalle_traslado", "fecha_mantenimiento")


@admin.register(BitacoraEstado)
class BitacoraEstadoAdmin(admin.ModelAdmin):
    list_display = ("codigo_bitacora", "codigo_herramienta", "documento", "es_inutilisable")
    list_filter = ("es_inutilisable",)
