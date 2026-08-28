from django.test import TestCase

from .models import CategoriaHerramienta, Herramienta


class HerramientaModelTest(TestCase):
    """Pruebas unitarias para el modelo Herramienta de la app herramienta."""

    def setUp(self):
        self.categoria = CategoriaHerramienta.objects.create(
            tipo_herramienta="Manual",
            nombre_categoria="Martillos",
            descripcion="Martillos de carpintería y minería",
        )
        self.herramienta = Herramienta.objects.create(
            codigo_sku="HER-001",
            nombre_herramienta="Martillo Neumático",
            descripcion="Martillo para percusión",
            disponibilidad="5",
            codigo_categoria=self.categoria,
            estado="Buena",
        )

    def test_herramienta_str(self):
        self.assertEqual(str(self.herramienta), "Martillo Neumático")

    def test_herramienta_properties(self):
        self.assertEqual(self.herramienta.codigo, "HER-001")
        self.assertEqual(self.herramienta.nombre, "Martillo Neumático")
        self.assertEqual(self.herramienta.stock_disponible, 5)

    def test_stock_setter(self):
        self.herramienta.stock_disponible = 3
        self.assertEqual(self.herramienta.disponibilidad, "3")
        self.assertEqual(self.herramienta.stock_disponible, 3)
