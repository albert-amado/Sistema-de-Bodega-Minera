from django.test import TestCase

# Create your tests here.
from django.test import Client, TestCase
from django.urls import reverse

from usuario.models import Usuario

from .manager import ConfigurationManager
from .schemas import DatabaseTarget


class ConfiguracionModuleTests(TestCase):
    """Pruebas unitarias para el módulo de configuración y conmutador de base de datos."""

    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            documento="999888777",
            primer_nombre="Admin",
            primer_apellido="Root",
            tipo_documento="CC",
            rol="Administrador",
        )
        self.usuario = Usuario.objects.create(
            documento="111222333",
            primer_nombre="User",
            primer_apellido="Normal",
            tipo_documento="CC",
            rol="Usuario",
        )
        self.mgr = ConfigurationManager()

    def test_unauthenticated_user_cannot_access_config(self):
        """Verifica que usuarios anónimos o estándar no puedan acceder al panel de configuración."""
        # Anónimo
        response = self.client.get(reverse("configuracion:panel"))
        self.assertRedirects(response, reverse("login"))

        # Usuario normal
        session = self.client.session
        session["usuario_documento"] = self.usuario.numero_documento
        session["usuario_rol"] = self.usuario.rol
        session.save()

        response = self.client.get(reverse("configuracion:panel"))
        self.assertRedirects(response, reverse("pagina_principal"))

    def test_admin_can_access_config(self):
        """Verifica que un administrador pueda ingresar al panel de configuración."""
        session = self.client.session
        session["usuario_documento"] = self.admin.numero_documento
        session["usuario_rol"] = self.admin.rol
        session.save()

        response = self.client.get(reverse("configuracion:panel"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuración del Sistema")

    def test_export_json_masks_passwords_by_default(self):
        """Verifica que la exportación de configuración enmascare contraseñas por defecto."""
        self.mgr.config.cloud_db.password = "SuperSecretDbPassword123"
        export_text = self.mgr.export_json(include_passwords=False)
        self.assertNotIn("SuperSecretDbPassword123", export_text)
        self.assertIn("********", export_text)

    def test_switch_target_local_valid(self):
        """Verifica que el cambio al perfil local funcione correctamente."""
        ok, msg = self.mgr.switch_target(DatabaseTarget.LOCAL, test_first=False)
        self.assertTrue(ok)
        self.assertEqual(self.mgr.config.active_target, DatabaseTarget.LOCAL)
