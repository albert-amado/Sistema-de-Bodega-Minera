from django.test import TestCase

from herramienta.models import Herramienta
from usuario.models import Usuario

from .models import DetallePrestamo, EstadoPrestamo, Prestamo


class PrestamoModelTest(TestCase):
    """Pruebas unitarias para el flujo de Préstamos."""

    def setUp(self):
        self.usuario = Usuario.objects.create(
            documento="123456789",
            primer_nombre="Carlos",
            primer_apellido="Pérez",
            tipo_documento="CC",
            rol="Usuario"
        )
        self.herramienta = Herramienta.objects.create(
            codigo_sku="TAL-002",
            nombre_herramienta="Taladro Industrial",
            disponibilidad="10",
        )
        self.prestamo = Prestamo.objects.create(
            documento=self.usuario,
            ficha="2558900",
            estado=EstadoPrestamo.PENDIENTE,
            observaciones="Prueba de préstamo",
        )
        self.detalle = DetallePrestamo.objects.create(
            codigo_prestamo=self.prestamo, codigo_herramienta=self.herramienta, cantidad=2
        )

    def test_prestamo_str(self):
        self.assertIn("Préstamo #", str(self.prestamo))

    def test_detalle_prestamo_asociacion(self):
        self.assertEqual(self.detalle.herramienta.nombre, "Taladro Industrial")
        self.assertEqual(self.detalle.cantidad, 2)
        self.assertEqual(
            self.detalle.prestamo.estado, EstadoPrestamo.PENDIENTE
        )

