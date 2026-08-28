from django.db import models


class Proveedor(models.Model):
    codigo_proveedor = models.AutoField(primary_key=True, db_column="codigo_proveedor")
    nit_proveedor = models.CharField(max_length=50)
    telefono_contacto = models.CharField(max_length=20, blank=True, null=True)
    correo_proveedor = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nit_proveedor} - {self.correo_proveedor or 'Proveedor'}"

    class Meta:
        db_table = "proveedor"
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"


class Suministro(models.Model):
    codigo_suministro = models.AutoField(primary_key=True, db_column="codigo_suministro")
    codigo_proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        db_column="codigo_proveedor",
        related_name="suministros",
    )
    fecha = models.DateField(blank=True, null=True)
    cantidad = models.IntegerField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Suministro {self.codigo_suministro}"

    class Meta:
        db_table = "suministro"
        verbose_name = "Suministro"
        verbose_name_plural = "Suministros"


class CategoriaHerramienta(models.Model):
    codigo_categoria = models.AutoField(primary_key=True, db_column="codigo_categoria")
    tipo_herramienta = models.CharField(max_length=100)
    nombre_categoria = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_categoria

    class Meta:
        db_table = "categoria_herramienta"
        verbose_name = "Categoría Herramienta"
        verbose_name_plural = "Categorías Herramienta"


class Herramienta(models.Model):
    codigo_herramienta = models.AutoField(primary_key=True, db_column="codigo_herramienta")
    codigo_sku = models.CharField(max_length=50, blank=True, null=True)
    nombre_herramienta = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    disponibilidad = models.CharField(max_length=50, blank=True, null=True)
    fecha_ingreso = models.DateField(blank=True, null=True)
    codigo_categoria = models.ForeignKey(
        CategoriaHerramienta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="codigo_categoria",
    )
    codigo_suministro = models.ForeignKey(
        Suministro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="codigo_suministro",
    )
    estado = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nombre_herramienta

    @property
    def codigo(self):
        return self.codigo_sku or f"HER-{self.codigo_herramienta}"

    @property
    def nombre(self):
        return self.nombre_herramienta

    @property
    def stock_disponible(self):
        if (
            self.disponibilidad is not None
            and str(self.disponibilidad).isdigit()
        ):
            return int(self.disponibilidad)
        return 1 if self.disponibilidad != "No disponible" else 0

    @stock_disponible.setter
    def stock_disponible(self, value):
        self.disponibilidad = str(max(0, int(value)))

    class Meta:
        db_table = "herramienta"
        verbose_name = "Herramienta"
        verbose_name_plural = "Herramientas"


class Traslado(models.Model):
    codigo_traslado = models.AutoField(primary_key=True, db_column="codigo_traslado")
    fecha_movimiento = models.DateField(blank=True, null=True)
    dimensiones = models.CharField(max_length=100, blank=True, null=True)
    tipo_movimiento = models.CharField(max_length=50, blank=True, null=True)
    num_estante_origen = models.ForeignKey(
        "almacen.Estante",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="num_estante_origen",
    )
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Traslado {self.codigo_traslado}"

    class Meta:
        db_table = "traslado"
        verbose_name = "Traslado"
        verbose_name_plural = "Traslados"


class DetalleTraslado(models.Model):
    codigo_detalle = models.AutoField(primary_key=True, db_column="codigo_detalle")
    codigo_traslado = models.ForeignKey(
        Traslado,
        on_delete=models.CASCADE,
        db_column="codigo_traslado",
    )
    codigo_herramienta = models.ForeignKey(
        Herramienta,
        on_delete=models.CASCADE,
        db_column="codigo_herramienta",
    )
    cantidad = models.IntegerField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return (
            f"Detalle {self.codigo_detalle} - "
            f"Traslado {self.codigo_traslado_id}"
        )

    class Meta:
        db_table = "detalle_traslado"
        verbose_name = "Detalle Traslado"
        verbose_name_plural = "Detalles Traslado"


class Mantenimiento(models.Model):
    num_mantenimiento = models.AutoField(primary_key=True, db_column="num_mantenimiento")
    codigo_herramienta = models.ForeignKey(
        Herramienta,
        on_delete=models.CASCADE,
        db_column="codigo_herramienta",
    )
    tipo_mantenimiento = models.CharField(max_length=50, blank=True, null=True)
    fecha_ingreso = models.DateField(blank=True, null=True)
    fecha_salida = models.DateField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Mantenimiento {self.num_mantenimiento} - {self.codigo_herramienta.nombre_herramienta}"

    class Meta:
        db_table = "mantenimiento"
        verbose_name = "Mantenimiento"
        verbose_name_plural = "Mantenimientos"


class DetalleMantenimiento(models.Model):
    detalle_mantenimiento = models.AutoField(primary_key=True, db_column="detalle_mantenimiento")
    num_mantenimiento = models.ForeignKey(
        Mantenimiento,
        on_delete=models.CASCADE,
        db_column="num_mantenimiento",
    )
    codigo_detalle_traslado = models.ForeignKey(
        DetalleTraslado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="codigo_detalle_traslado",
    )
    accion_realizada = models.TextField(blank=True, null=True)
    materiales_usados = models.TextField(blank=True, null=True)
    fecha_mantenimiento = models.DateField(blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Detalle Mantenimiento {self.detalle_mantenimiento}"

    class Meta:
        db_table = "detalle_mantenimiento"
        verbose_name = "Detalle Mantenimiento"
        verbose_name_plural = "Detalles Mantenimiento"


class BitacoraEstado(models.Model):
    codigo_bitacora = models.AutoField(primary_key=True, db_column="codigo_bitacora")
    num_mantenimiento = models.ForeignKey(
        Mantenimiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="num_mantenimiento",
    )
    codigo_herramienta = models.ForeignKey(
        Herramienta,
        on_delete=models.CASCADE,
        db_column="codigo_herramienta",
    )
    documento = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.RESTRICT,
        db_column="documento",
    )
    documento_tecnico = models.CharField(max_length=250, blank=True, null=True)
    es_inutilisable = models.BooleanField(default=False)
    descripcion = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Bitácora {self.codigo_bitacora}"

    class Meta:
        db_table = "bitacora_estado"
        verbose_name = "Bitácora Estado"
        verbose_name_plural = "Bitácoras Estado"
