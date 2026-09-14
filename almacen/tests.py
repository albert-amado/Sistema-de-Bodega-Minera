from django.test import TestCase
from .models import Almacen, Estante


class AlmacenamientoModelTest(TestCase):
    def setUp(self):
        self.almacen = Almacen.objects.create(
            nombre="Almacén Principal", ubicacion="Ubicado en el centro", dimensiones="10x20m"
        )
        self.estante = Estante.objects.create(
            codigo_almacen=self.almacen,
            codigo="EST-001",
            dimensiones="2x1m",
        )

    def test_almacen_creacion(self):
        self.assertEqual(Almacen.objects.count(), 1)
        self.assertEqual(self.almacen.nombre, "Almacén Principal")

    def test_estante_creacion(self):
        self.assertEqual(Estante.objects.count(), 1)
        self.assertEqual(self.estante.codigo_almacen, self.almacen)

    def test_str_methods(self):
        self.assertEqual(str(self.almacen), "Almacén Principal")
        self.assertIn("EST-001", str(self.estante))


