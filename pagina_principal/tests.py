from django.test import TestCase, Client
from django.urls import reverse
from usuario.models import Usuario


class PaginaPrincipalSecurityTests(TestCase):
    """Pruebas de seguridad para pagina_principal."""

    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create(
            documento="1234567890",
            primer_nombre="Carlos",
            primer_apellido="Pérez",
            tipo_documento="CC",
            rol="Usuario",
        )

    def test_anonymous_redirected_to_login(self):
        """Verifica que usuarios anónimos sean redirigidos a login."""
        response = self.client.get(reverse('pagina_principal'))
        self.assertRedirects(response, reverse('login'))

    def test_authenticated_user_can_access_dashboard(self):
        """Verifica que usuarios con sesión activa puedan ver el dashboard."""
        session = self.client.session
        session['usuario_documento'] = self.usuario.numero_documento
        session['usuario_rol'] = self.usuario.rol
        session.save()

        response = self.client.get(reverse('pagina_principal'))
        self.assertEqual(response.status_code, 200)
