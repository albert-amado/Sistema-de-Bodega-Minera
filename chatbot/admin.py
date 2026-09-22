from django.contrib import admin
from .models import ChatLog


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('creado_en', 'usuario_documento', 'usuario_rol', 'resumen_mensaje', 'modelo_utilizado', 'tiempo_respuesta_ms')
    list_filter = ('usuario_rol', 'modelo_utilizado', 'creado_en')
    search_fields = ('usuario_documento', 'mensaje_usuario', 'respuesta_asistente')
    readonly_fields = ('usuario_documento', 'usuario_rol', 'mensaje_usuario', 'respuesta_asistente', 'modelo_utilizado', 'ip_address', 'tiempo_respuesta_ms', 'creado_en')

    def resumen_mensaje(self, obj):
        return obj.mensaje_usuario[:60] + ('...' if len(obj.mensaje_usuario) > 60 else '')
    resumen_mensaje.short_description = 'Mensaje (Anonimizado)'
