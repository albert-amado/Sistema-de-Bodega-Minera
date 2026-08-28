from django.contrib import admin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('documento', 'primer_nombre', 'primer_apellido', 'correo_personal', 'tipo_documento', 'telefono')
    list_filter = ('tipo_documento',)
    search_fields = ('documento', 'primer_nombre', 'primer_apellido', 'correo_personal')
    ordering = ('primer_nombre', 'primer_apellido')