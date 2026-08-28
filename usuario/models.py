import re
from django.db import models
from django.core.exceptions import ValidationError


def validar_numero_documento(value, tipo):
    REGLAS = {
        'CC': (r'^\d{6,10}$',          'La Cédula de Ciudadanía debe tener entre 6 y 10 dígitos.'),
        'CE': (r'^[A-Za-z0-9]{6,12}$', 'La Cédula de Extranjería debe tener entre 6 y 12 caracteres alfanuméricos.'),
        'PP': (r'^[A-Za-z0-9]{5,9}$',  'El Pasaporte debe tener entre 5 y 9 caracteres alfanuméricos.'),
        'TI': (r'^\d{10,11}$',         'La Tarjeta de Identidad debe tener 10 u 11 dígitos.'),
    }
    patron, mensaje = REGLAS.get(tipo, (None, None))
    if patron and not re.match(patron, value):
        raise ValidationError(mensaje)


class Usuario(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('PP', 'Pasaporte'),
        ('TI', 'Tarjeta de Identidad'),
    ]

    ROL_CHOICES = [
        ('Usuario', 'Usuario'),
        ('Administrador', 'Administrador'),
    ]

    # Campos de la tabla 'usuario' en MySQL Dump20260814.sql
    documento        = models.CharField(max_length=20, primary_key=True, db_column='documento', verbose_name="Número de Documento")
    primer_nombre    = models.CharField(max_length=50, verbose_name="Primer Nombre")
    segundo_nombre   = models.CharField(max_length=50, blank=True, null=True, verbose_name="Segundo Nombre")
    primer_apellido  = models.CharField(max_length=50, verbose_name="Primer Apellido")
    segundo_apellido = models.CharField(max_length=50, blank=True, null=True, verbose_name="Segundo Apellido")
    correo_personal  = models.CharField(max_length=100, blank=True, null=True, verbose_name="Correo Personal", db_column='correo_personal')
    telefono         = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    tipo_documento   = models.CharField(
        max_length=30,
        choices=TIPO_DOCUMENTO_CHOICES,
        default='CC',
        blank=True,
        null=True,
        verbose_name='Tipo de documento',
    )
    programa         = models.CharField(max_length=100, blank=True, null=True, verbose_name='Programa')
    ficha            = models.CharField(max_length=50, blank=True, null=True, verbose_name='Ficha')
    password         = models.CharField(max_length=255, blank=True, null=True, verbose_name='Contraseña')
    rol              = models.CharField(
        max_length=50,
        choices=ROL_CHOICES,
        default='Usuario',
        blank=True,
        null=True,
        verbose_name='Rol',
    )
    reset_token        = models.CharField(max_length=64, blank=True, default='', verbose_name='Token de recuperación')
    reset_token_expira = models.FloatField(default=0, verbose_name='Expiración del token')

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    # Propiedades de compatibilidad con vistas y formularios del sistema
    @property
    def numero_documento(self):
        return self.documento

    @numero_documento.setter
    def numero_documento(self, val):
        self.documento = val

    @property
    def nombre_completo(self):
        partes = [self.primer_nombre, self.segundo_nombre, self.primer_apellido, self.segundo_apellido]
        return " ".join([p for p in partes if p])

    @nombre_completo.setter
    def nombre_completo(self, val):
        if val:
            partes = val.strip().split()
            if len(partes) >= 4:
                self.primer_nombre, self.segundo_nombre, self.primer_apellido, self.segundo_apellido = partes[0], partes[1], partes[2], " ".join(partes[3:])
            elif len(partes) == 3:
                self.primer_nombre, self.segundo_nombre, self.primer_apellido = partes[0], partes[1], partes[2]
            elif len(partes) == 2:
                self.primer_nombre, self.primer_apellido = partes[0], partes[1]
            elif len(partes) == 1:
                self.primer_nombre = partes[0]

    @property
    def correo(self):
        return self.correo_personal or ''

    @correo.setter
    def correo(self, val):
        self.correo_personal = val

    @property
    def numero_ficha(self):
        return self.ficha or ''

    @numero_ficha.setter
    def numero_ficha(self, val):
        self.ficha = val

    @property
    def nombre_programa(self):
        return self.programa or ''

    @nombre_programa.setter
    def nombre_programa(self, val):
        self.programa = val

    def clean(self):
        super().clean()
        if self.documento and self.tipo_documento:
            validar_numero_documento(self.documento, self.tipo_documento)

    def __str__(self):
        return f"{self.nombre_completo} ({self.tipo_documento or ''} {self.documento})"