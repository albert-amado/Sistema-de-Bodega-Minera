from django.db import models

class CategoriaHerramienta(models.Model):
    codigo_categoria = models.AutoField(primary_key=True)
    tipo_herramienta = models.CharField(max_length=100)
    nombre_categoria = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_categoria
    
    class Meta:
        db_table = 'categoria_herramienta'

class Herramienta(models.Model):
    codigo_herramienta = models.AutoField(primary_key=True)
    codigo_sku = models.CharField(max_length=50, blank=True, null=True)
    nombre_herramienta = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    disponibilidad = models.CharField(max_length=50, blank=True, null=True)
    fecha_ingreso = models.DateField(blank=True, null=True)
    codigo_categoria = models.ForeignKey(CategoriaHerramienta, on_delete=models.SET_NULL, null=True, blank=True, db_column='codigo_categoria')
    codigo_suministro = models.IntegerField(null=True, blank=True)
    estado = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nombre_herramienta

    class Meta:
        db_table = 'herramienta'

class Traslado(models.Model):
    codigo_traslado = models.AutoField(primary_key=True)
    fecha_movimiento = models.DateField(blank=True, null=True)
    tipo_movimiento = models.CharField(max_length=50, blank=True, null=True)
    num_estante_origen = models.IntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Traslado {self.codigo_traslado}"

    class Meta:
        db_table = 'traslado'

class DetalleTraslado(models.Model):
    codigo_detalle = models.AutoField(primary_key=True)
    codigo_traslado = models.ForeignKey(Traslado, on_delete=models.CASCADE, db_column='codigo_traslado')
    codigo_herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE, db_column='codigo_herramienta')
    cantidad = models.IntegerField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Detalle {self.codigo_detalle} - Traslado {self.codigo_traslado_id}"

    class Meta:
        db_table = 'detalle_traslado'
