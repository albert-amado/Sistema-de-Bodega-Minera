from django.test import TestCase
from .models import Almacen, Estante
from django.db.utils import IntegrityError


class AlmacenamientoModelTest(TestCase):
    def setUp(self):
        self.almacen = Almacen.objects.create(
            nombre="Almacén Principal", detalles="Ubicado en el centro", capacidad=100
        )
        self.estante = Estante.objects.create(
            almacen=self.almacen,
            codigo="EST-001",
            detalles="Estante de electrónicos",
            capacidad=20,
        )

    def test_almacen_creacion(self):
        self.assertEqual(Almacen.objects.count(), 1)
        self.assertEqual(self.almacen.nombre, "Almacén Principal")

    def test_estante_creacion(self):
        self.assertEqual(Estante.objects.count(), 1)
        self.assertEqual(self.estante.almacen, self.almacen)

    def test_almacen_nombre_unico(self):
        with self.assertRaises(IntegrityError):
            Almacen.objects.create(nombre="Almacén Principal", capacidad=50)

    def test_estante_codigo_unico(self):
        with self.assertRaises(IntegrityError):
            Estante.objects.create(almacen=self.almacen, codigo="EST-001")

    def test_str_methods(self):
        self.assertEqual(str(self.almacen), "Almacén Principal")
        self.assertEqual(str(self.estante), "EST-001")

