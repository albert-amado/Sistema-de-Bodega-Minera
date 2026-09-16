from django.test import Client, TestCase
from django.urls import reverse

from herramienta.models import Herramienta
from usuario.models import Usuario

from .models import DetallePrestamo, EstadoPrestamo, Prestamo


class PrestamoModelTest(TestCase):
    """Pruebas unitarias para el flujo de Préstamos."""

    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create(
            documento="123456789",
            primer_nombre="Carlos",
            primer_apellido="Pérez",
            tipo_documento="CC",
            rol="Usuario"
        )
        self.admin = Usuario.objects.create(
            documento="987654321",
            primer_nombre="Admin",
            primer_apellido="SENA",
            tipo_documento="CC",
            rol="Administrador"
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

    def test_usuario_solicitar_prestamo_forces_session_user(self):
        """Verifica que usuario_solicitar_prestamo use estrictamente el usuario de la sesión activa."""
        session = self.client.session
        session['usuario_documento'] = self.usuario.numero_documento
        session['usuario_rol'] = self.usuario.rol
        session.save()

        # Intento de suplantación enviando documento de admin en POST
        data = {
            'documento': self.admin.numero_documento,
            'ficha': '2558900',
            'observaciones': 'Solicitud test',
            'herramienta[]': [self.herramienta.pk],
            'cantidad[]': [1],
        }
        response = self.client.post(reverse('usuario_solicitar_prestamo'), data=data)
        self.assertEqual(response.status_code, 302)

        nuevo_prestamo = Prestamo.objects.latest('codigo_prestamo')
        self.assertEqual(nuevo_prestamo.documento, self.usuario)  # Asignado al usuario en sesión, no al del POST

    def test_aprobar_prestamo_requires_admin(self):
        """Verifica que un usuario estándar no pueda aprobar préstamos."""
        session = self.client.session
        session['usuario_documento'] = self.usuario.numero_documento
        session['usuario_rol'] = self.usuario.rol
        session.save()

        response = self.client.post(reverse('aprobar_prestamo'), {'pk': self.prestamo.pk})
        self.assertRedirects(response, reverse('pagina_principal'))
        self.prestamo.refresh_from_db()
        self.assertEqual(self.prestamo.estado, EstadoPrestamo.PENDIENTE)
