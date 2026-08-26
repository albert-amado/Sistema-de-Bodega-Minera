from django.test import TestCase

from herramienta.models import Herramienta

from .models import DetallePrestamo, EstadoPrestamo, Prestamo


class PrestamoModelTest(TestCase):
    """Pruebas unitarias para el flujo de Préstamos."""

    def setUp(self):
        self.herramienta = Herramienta.objects.create(
            codigo_sku="TAL-002",
            nombre_herramienta="Taladro Industrial",
            disponibilidad="10",
        )
        self.prestamo = Prestamo.objects.create(
            documento="123456789",
            ficha="2558900",
            estado=EstadoPrestamo.PENDIENTE,
            observaciones="Prueba de préstamo",
        )
        self.detalle = DetallePrestamo.objects.create(
            prestamo=self.prestamo, herramienta=self.herramienta, cantidad=2
        )

    def test_prestamo_str(self):
        self.assertIn("Préstamo #", str(self.prestamo))

    def test_detalle_prestamo_asociacion(self):
        self.assertEqual(self.detalle.herramienta.nombre, "Taladro Industrial")
        self.assertEqual(self.detalle.cantidad, 2)
        self.assertEqual(
            self.detalle.prestamo.estado, EstadoPrestamo.PENDIENTE
        )
