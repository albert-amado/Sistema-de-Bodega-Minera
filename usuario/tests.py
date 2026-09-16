from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse

from .forms import (
    PerfilUsuarioForm,
    RegistroUsuarioForm,
)
from .models import Usuario


class UsuarioSecurityTests(TestCase):
    """Pruebas de seguridad e integridad para la aplicación Usuario."""

    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            documento="1111222233",
            primer_nombre="Admin",
            primer_apellido="Root",
            tipo_documento="CC",
            correo_personal="admin@sena.edu.co",
            password=make_password("AdminPass123!"),
            rol="Administrador",
        )
        self.usuario = Usuario.objects.create(
            documento="1234567890",
            primer_nombre="Juan",
            primer_apellido="Pérez",
            tipo_documento="CC",
            correo_personal="juan.perez@sena.edu.co",
            password=make_password("UserPass123!"),
            rol="Usuario",
        )

    def test_registro_usuario_form_forces_user_role(self):
        """Verifica que el formulario de registro no permita escalar privilegios a Administrador."""
        data = {
            'tipo_documento': 'CC',
            'documento': '9876543210',
            'first_name': 'Carlos',
            'last_name': 'Gomez',
            'email': 'carlos.gomez@sena.edu.co',
            'password1': 'Segura12345',
            'password2': 'Segura12345',
            'numero_ficha': '2558190',
            'nombre_programa': 'Minería',
            'rol': 'Administrador',  # Intento de inyección de rol
        }
        form = RegistroUsuarioForm(data=data)
        self.assertTrue(form.is_valid())
        nuevo_usuario = form.save()
        self.assertEqual(nuevo_usuario.rol, 'Usuario')  # Backend forzó 'Usuario'

    def test_perfil_form_cannot_modify_sensitive_fields(self):
        """Verifica que el formulario de perfil no exponga rol ni documento."""
        form = PerfilUsuarioForm(instance=self.usuario)
        self.assertNotIn('rol', form.fields)
        self.assertNotIn('documento', form.fields)
        self.assertNotIn('tipo_documento', form.fields)
        self.assertNotIn('password', form.fields)

    def test_idor_protection_detalle_usuario_json(self):
        """Verifica que un usuario estándar no pueda consultar datos privados de otro usuario vía API JSON."""
        # Iniciar sesión como usuario estándar
        session = self.client.session
        session['usuario_documento'] = self.usuario.numero_documento
        session['usuario_rol'] = self.usuario.rol
        session.save()

        # Intentar consultar datos del administrador
        url = reverse('detalle_usuario_json', kwargs={'numero_documento': self.admin.numero_documento})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_exportar_usuarios_csv_requires_admin(self):
        """Verifica que la exportación de usuarios requiera rol Administrador."""
        # Intento anónimo
        response = self.client.get(reverse('exportar_usuarios_csv'))
        self.assertRedirects(response, reverse('login'))

        # Intento como usuario regular
        session = self.client.session
        session['usuario_documento'] = self.usuario.numero_documento
        session['usuario_rol'] = self.usuario.rol
        session.save()

        response = self.client.get(reverse('exportar_usuarios_csv'))
        self.assertRedirects(response, reverse('pagina_principal'))
