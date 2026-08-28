from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from herramienta.models import Herramienta
from usuario.models import Usuario


class EstadoPrestamo(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    ENTREGADO = "ENTREGADO", "Entregado"
    DEVUELTO = "DEVUELTO", "Devuelto"
    PARCIAL = "PARCIAL", "Devolución Parcial"
    CANCELADO = "CANCELADO", "Cancelado"


class Prestamo(models.Model):
    codigo_prestamo = models.AutoField(primary_key=True, db_column="codigo_prestamo")
    documento = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column="documento",
        related_name="prestamos",
        verbose_name="Usuario",
        null=True,
        blank=True,
    )
    fecha = models.DateField("Fecha", default=timezone.now)
    ficha = models.CharField("Ficha SENA", max_length=50, blank=True, null=True)
    estado = models.CharField(
        "Estado",
        max_length=50,
        choices=EstadoPrestamo.choices,
        default=EstadoPrestamo.PENDIENTE,
    )
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        db_table = "prestamo"
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"

    def __str__(self):
        return f"Préstamo #{self.codigo_prestamo} - Ficha {self.ficha or 'N/A'}"

    @property
    def usuario(self):
        return self.documento

    @usuario.setter
    def usuario(self, val):
        self.documento = val


class DetallePrestamo(models.Model):
    numeros_detalle = models.AutoField(primary_key=True, db_column="numeros_detalle")
    codigo_prestamo = models.ForeignKey(
        Prestamo,
        on_delete=models.CASCADE,
        db_column="codigo_prestamo",
        related_name="detalles",
        null=True,
        blank=True,
    )
    codigo_herramienta = models.ForeignKey(
        Herramienta,
        on_delete=models.PROTECT,
        db_column="codigo_herramienta",
        related_name="detalles_prestamo",
        null=True,
        blank=True,
    )
    cantidad = models.PositiveIntegerField(
        "Cantidad", default=1, validators=[MinValueValidator(1)]
    )
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        db_table = "detalle_prestamo"
        verbose_name = "Detalle Préstamo"
        verbose_name_plural = "Detalles Préstamo"

    @property
    def prestamo(self):
        return self.codigo_prestamo

    @prestamo.setter
    def prestamo(self, val):
        self.codigo_prestamo = val

    @property
    def herramienta(self):
        return self.codigo_herramienta

    @herramienta.setter
    def herramienta(self, val):
        self.codigo_herramienta = val

    def __str__(self):
        herramienta_nombre = self.codigo_herramienta.nombre_herramienta if self.codigo_herramienta else "N/A"
        return (
            f"{self.cantidad}x {herramienta_nombre} "
            f"(Préstamo #{self.codigo_prestamo_id})"
        )

    def clean(self):
        if (
            self.codigo_herramienta
            and self.cantidad > self.codigo_herramienta.stock_disponible
        ):
            msg = (
                f"Stock insuficiente. Solo hay "
                f"{self.codigo_herramienta.stock_disponible} disponibles."
            )
            raise ValidationError({"cantidad": msg})


class DevolucionHerramienta(models.Model):
    codigo_devolucion = models.AutoField(primary_key=True, db_column="codigo_devolucion")
    codigo_prestamo = models.ForeignKey(
        Prestamo,
        on_delete=models.CASCADE,
        db_column="codigo_prestamo",
        related_name="devoluciones",
        null=True,
        blank=True,
    )
    codigo_recibe = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="codigo_recibe",
        related_name="devoluciones_recibidas",
        verbose_name="Recibido por",
    )
    fecha = models.DateField("Fecha", default=timezone.now)
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        db_table = "devolucion_herramienta"
        verbose_name = "Devolución Herramienta"
        verbose_name_plural = "Devoluciones Herramientas"

    @property
    def prestamo(self):
        return self.codigo_prestamo

    @prestamo.setter
    def prestamo(self, val):
        self.codigo_prestamo = val

    @property
    def recibido_por(self):
        return self.codigo_recibe

    @recibido_por.setter
    def recibido_por(self, val):
        self.codigo_recibe = val

    def __str__(self):
        return f"Devolución #{self.codigo_devolucion} - Préstamo #{self.codigo_prestamo_id}"
