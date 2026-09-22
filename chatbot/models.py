from django.db import models


class ChatLog(models.Model):
    """
    Registro de interacciones del chatbot con fines de auditoría y mejora continua.
    Cumplimiento Ley 1581 de 2012 (Habeas Data): los mensajes almacenados
    deben ser previamente anonimizados/enmascarados.
    """
    usuario_documento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Documento de Usuario (Sesión)",
        help_text="Identificador de la sesión que originó la consulta"
    )
    usuario_rol = models.CharField(
        max_length=50,
        blank=True,
        default='Usuario',
        verbose_name="Rol en Sesión"
    )
    mensaje_usuario = models.TextField(
        verbose_name="Mensaje del Usuario (Enmascarado)",
        help_text="Texto con números de documento, correos o teléfonos anonimizados"
    )
    respuesta_asistente = models.TextField(
        verbose_name="Respuesta del Asistente"
    )
    modelo_utilizado = models.CharField(
        max_length=60,
        default='gemini-2.5-flash',
        verbose_name="Modelo IA"
    )
    ip_address = models.CharField(
        max_length=45,
        blank=True,
        null=True,
        verbose_name="Dirección IP"
    )
    tiempo_respuesta_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Latencia (ms)"
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora"
    )

    class Meta:
        db_table = 'chatbot_log'
        verbose_name = 'Registro de Chat'
        verbose_name_plural = 'Registros de Chat'
        ordering = ['-creado_en']

    def __str__(self):
        return f"[{self.creado_en.strftime('%Y-%m-%d %H:%M')}] {self.usuario_rol} - {self.mensaje_usuario[:40]}..."
