from django.db import models

# Create your models here.
class Almacen(models.Model):
    codigo_almacen = models.AutoField(primary_key=True, db_column='codigo_almacen')
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    ubicacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ubicación")

    class Meta:
        db_table = 'almacen'
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Estante(models.Model):
    num_estante = models.AutoField(primary_key=True, db_column='num_estante')
    codigo = models.CharField(max_length=50, verbose_name="Código")
    codigo_almacen = models.ForeignKey(
        Almacen,
        on_delete=models.RESTRICT,
        db_column='codigo_almacen',
        related_name='estantes',
        verbose_name="Almacén"
    )

    class Meta:
        db_table = 'estante'
        verbose_name = "Estante"
        verbose_name_plural = "Estantes"
        ordering = ['codigo']

    @property
    def almacen(self):
        return self.codigo_almacen

    @almacen.setter
    def almacen(self, val):
        self.codigo_almacen = val

    def __str__(self):
        return f"{self.codigo} ({self.codigo_almacen.nombre})"