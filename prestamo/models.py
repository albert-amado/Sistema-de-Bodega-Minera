from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

User = get_user_model()


class Herramienta(models.Model):
    codigo = models.CharField("Código / Placa", max_length=50, unique=True)
    nombre = models.CharField("Nombre", max_length=100)
    descripcion = models.TextField("Descripción", blank=True, null=True)
    stock_disponible = models.PositiveIntegerField(
        "Stock Disponible", default=1, validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name_plural = "Herramientas"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class EstadoPrestamo(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    ENTREGADO = 'ENTREGADO', 'Entregado'
    DEVUELTO = 'DEVUELTO', 'Devuelto'
    PARCIAL = 'PARCIAL', 'Devolución Parcial'
    CANCELADO = 'CANCELADO', 'Cancelado'


class Prestamo(models.Model):
    documento = models.CharField("Documento", max_length=20)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ficha = models.CharField("Ficha SENA", max_length=50)
    fecha = models.DateField("Fecha", default=timezone.now)
    estado = models.CharField("Estado", max_length=20, choices=EstadoPrestamo.choices, default=EstadoPrestamo.PENDIENTE)
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        verbose_name_plural = "Préstamos"

    def __str__(self):
        return f"Préstamo #{self.id} - Ficha {self.ficha}"

    def clean(self):
        if not self.documento.isdigit():
            raise ValidationError({'documento': "El documento debe contener solo dígitos."})


class DetallePrestamo(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='detalles')
    herramienta = models.ForeignKey(Herramienta, on_delete=models.PROTECT, related_name='detalles_prestamo')
    cantidad = models.PositiveIntegerField("Cantidad", default=1, validators=[MinValueValidator(1)])
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    def __str__(self):
        return f"{self.cantidad}x {self.herramienta.nombre} (Préstamo #{self.prestamo_id})"

    def clean(self):
        if self.herramienta and self.cantidad > self.herramienta.stock_disponible:
            raise ValidationError({'cantidad': f"Stock insuficiente en modelo. Solo hay {self.herramienta.stock_disponible} disponibles."})


class DevolucionHerramienta(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='devoluciones')
    codigo_recibe = models.CharField("Recibe (Doc)", max_length=20)
    recibido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateField("Fecha", default=timezone.now)
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    def __str__(self):
        return f"Devolución #{self.id} - Préstamo #{self.prestamo_id}"
