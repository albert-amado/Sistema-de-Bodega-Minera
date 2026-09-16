from django.db import models


class ConfiguracionSistema(models.Model):
    ALMACENAMIENTO_CHOICES = [
        ('local', 'Local (SQLite)'),
        ('nube', 'Nube (PostgreSQL Neon)'),
    ]

    almacenamiento = models.CharField(
        max_length=10,
        choices=ALMACENAMIENTO_CHOICES,
        default='nube',
    )
    # URL de conexión Neon (se guarda encriptada en producción; aquí en texto)
    database_url = models.TextField(blank=True, default='')
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración del sistema'
        verbose_name_plural = 'Configuración del sistema'

    def __str__(self):
        return f'Configuración — {self.get_almacenamiento_display()}'