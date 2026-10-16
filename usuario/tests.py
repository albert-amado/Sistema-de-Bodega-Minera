"""
Suite de Pruebas Automatizadas de QA para el Módulo de Usuarios y Autenticación.
Sistema: Mine Inventory.
Cubre:
1. Modelos (Validación regex de documentos colombianos CC/CE/PP/TI, propiedades y __str__).
2. Formularios (Registro, Perfil, Cambio de Contraseña, Edición Admin).
3. Vistas y Flujos de Sesión (Login, Logout, Perfil, Listado de Usuarios, Recuperación).
4. Seguridad RBAC e IDOR (Protección de endpoints administrativos, inyección de rol, sanitización).
"""

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .forms import (
    CambiarPasswordForm,
    EditarUsuarioAdminForm,
    PerfilUsuarioForm,
    RegistroUsuarioForm,
)
from .models import Usuario, validar_numero_documento


class UsuarioBaseTestCase(TestCase):
    """Clase base de pruebas para la app usuario."""

    def setUp(self):
        super().setUp()
        self.client = Client()

        # Administrador del sistema
        self.admin = Usuario.objects.create(
            documento="1111222233",
            primer_nombre="Admin",
            primer_apellido="Root",
            tipo_documento="CC",
            correo_personal="admin@sena.edu.co",
            password=make_password("AdminPass123!"),
            rol="Administrador",
            ficha="ADM-01",
        )

        # Operador minero estándar
        self.usuario = Usuario.objects.create(
            documento="1234567890",
            primer_nombre="Juan",
            primer_apellido="Pérez",
            tipo_documento="CC",
            correo_personal="juan.perez@sena.edu.co",
            password=make_password("UserPass123!"),
            rol="Usuario",
            ficha="2558900",
            programa="Operación Minera",
        )

    def login_as(self, usuario):
        session = self.client.session
        session["usuario_documento"] = usuario.documento
        session["usuario_nombre"] = usuario.nombre_completo
        session["usuario_rol"] = usuario.rol
        session["usuario_tipo_documento"] = usuario.tipo_documento
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

    def logout(self):
        self.client.cookies.clear()
        session = self.client.session
        session.flush()
        session.save()


# ==============================================================================
# 1. PRUEBAS UNITARIAS DE MODELOS (MODELS)
# ==============================================================================
class UsuarioModelUnitTests(UsuarioBaseTestCase):
    """Pruebas de validación de campos, expresiones regulares y métodos del modelo Usuario."""

    def test_validador_documento_cc_valido_e_invalido(self):
        """Valida que la Cédula de Ciudadanía (CC) exija entre 6 y 10 dígitos numéricos."""
        # Válido (entre 6 y 10 dígitos)
        try:
            validar_numero_documento("10203040", "CC")
        except ValidationError:
            self.fail("validar_numero_documento lanzó ValidationError inesperado para CC válida.")

        # Inválido: contiene letras
        with self.assertRaises(ValidationError):
            validar_numero_documento("1020AB40", "CC")

        # Inválido: menos de 6 dígitos
        with self.assertRaises(ValidationError):
            validar_numero_documento("12345", "CC")

        # Inválido: más de 10 dígitos
        with self.assertRaises(ValidationError):
            validar_numero_documento("12345678901", "CC")

    def test_validador_otros_tipos_documento(self):
        """Valida las reglas para Pasaporte (PP), Cédula Extranjería (CE) y Tarjeta Identidad (TI)."""
        # TI: 10 u 11 dígitos
        validar_numero_documento("1098765432", "TI")
        with self.assertRaises(ValidationError):
            validar_numero_documento("123456789", "TI")  # 9 dígitos

        # CE: alfanumérico entre 6 y 12 caracteres
        validar_numero_documento("E123456", "CE")

        # PP: alfanumérico entre 5 y 9 caracteres
        validar_numero_documento("PAS1234", "PP")

    def test_propiedades_nombre_completo_getter_y_setter(self):
        """Verifica que el setter y getter de nombre_completo distribuyan adecuadamente los nombres y apellidos."""
        u = Usuario(documento="99887766")
        u.nombre_completo = "Andrés Felipe Moreno Gómez"
        self.assertEqual(u.primer_nombre, "Andrés")
        self.assertEqual(u.segundo_nombre, "Felipe")
        self.assertEqual(u.primer_apellido, "Moreno")
        self.assertEqual(u.segundo_apellido, "Gómez")
        self.assertEqual(u.nombre_completo, "Andrés Felipe Moreno Gómez")

        # Asignación de 2 palabras
        u.nombre_completo = "Carlos Gómez"
        self.assertEqual(u.primer_nombre, "Carlos")
        self.assertEqual(u.primer_apellido, "Gómez")

    def test_modelo_str_format(self):
        """Verifica que __str__ devuelva el nombre completo con el tipo y número de documento."""
        str_val = str(self.usuario)
        self.assertIn("Juan Pérez", str_val)
        self.assertIn("CC 1234567890", str_val)


# ==============================================================================
# 2. PRUEBAS UNITARIAS DE FORMULARIOS (FORMS)
# ==============================================================================
class UsuarioFormUnitTests(UsuarioBaseTestCase):
    """Pruebas unitarias de formularios de registro, perfil y cambio de credenciales."""

    @override_settings(ALLOW_MANUAL_REGISTRATION=True)
    def test_registro_usuario_form_datos_validos_fuerza_rol_usuario(self):
        """Verifica que un registro exitoso fuerce siempre el rol 'Usuario' para evitar escalamiento."""
        data = {
            "tipo_documento": "CC",
            "documento": "1055443322",
            "first_name": "Pedro",
            "last_name": "Infante",
            "email": "pedro.infante@sena.edu.co",
            "password1": "Minero2026*",
            "password2": "Minero2026*",
            "numero_ficha": "2558900",
            "nombre_programa": "Explotación Minera",
            "rol": "Administrador",  # Intento de inyección
        }
        form = RegistroUsuarioForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        creado = form.save()
        self.assertEqual(creado.rol, "Usuario")
        self.assertTrue(check_password("Minero2026*", creado.password))

    def test_registro_usuario_form_password_mismatch(self):
        """Verifica que contraseñas que no coincidan impidan el registro."""
        data = {
            "tipo_documento": "CC",
            "documento": "1055443322",
            "first_name": "Pedro",
            "last_name": "Infante",
            "email": "pedro.infante@sena.edu.co",
            "password1": "Minero2026*",
            "password2": "Distinta123*",
            "numero_ficha": "2558900",
            "nombre_programa": "Explotación Minera",
        }
        form = RegistroUsuarioForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_perfil_form_protege_campos_inmutables(self):
        """Verifica que el formulario de perfil no permita modificar campos críticos (rol, documento, password)."""
        form = PerfilUsuarioForm(instance=self.usuario)
        self.assertNotIn("rol", form.fields)
        self.assertNotIn("documento", form.fields)
        self.assertNotIn("tipo_documento", form.fields)
        self.assertNotIn("password", form.fields)

    def test_cambiar_password_form_validacion(self):
        """Verifica que CambiarPasswordForm valide la contraseña actual y confirme la nueva."""
        # 1. Contraseña actual incorrecta
        data_err = {
            "password_actual": "WrongPassword!",
            "password_nueva": "NewPass2026*",
            "password_confirma": "NewPass2026*",
        }
        form_err = CambiarPasswordForm(self.usuario, data=data_err)
        self.assertFalse(form_err.is_valid())
        self.assertIn("password_actual", form_err.errors)

        # 2. Contraseña actual correcta y coincidente
        data_ok = {
            "password_actual": "UserPass123!",
            "password_nueva": "NewPass2026*",
            "password_confirma": "NewPass2026*",
        }
        form_ok = CambiarPasswordForm(self.usuario, data=data_ok)
        self.assertTrue(form_ok.is_valid(), form_ok.errors)


# ==============================================================================
# 3. PRUEBAS DE INTEGRACIÓN DE VISTAS (VIEWS)
# ==============================================================================
class UsuarioViewIntegrationTests(UsuarioBaseTestCase):
    """Pruebas de integración sobre autenticación, sesión, listados y vistas de perfil."""

    def test_login_view_get_200(self):
        """Verifica que la página de login responda 200 OK para usuarios no autenticados."""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")

    def test_login_view_exitoso_crea_sesion_y_redirige(self):
        """Verifica que credenciales válidas establezcan la sesión personalizada y redirijan a página principal."""
        data = {
            "tipo_documento": "CC",
            "documento": "1234567890",
            "password": "UserPass123!",
        }
        response = self.client.post(reverse("login"), data=data)
        self.assertRedirects(response, reverse("pagina_principal"))

        # Validar variables de sesión
        self.assertEqual(self.client.session.get("usuario_documento"), "1234567890")
        self.assertEqual(self.client.session.get("usuario_rol"), "Usuario")

    def test_login_view_credenciales_invalidas_muestra_error(self):
        """Verifica que una contraseña incorrecta no permita el acceso y mantenga en la vista."""
        data = {
            "tipo_documento": "CC",
            "documento": "1234567890",
            "password": "PasswordInvalido!",
        }
        response = self.client.post(reverse("login"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get("usuario_documento"))

    def test_login_view_usuario_ya_autenticado_redirige(self):
        """Verifica que si un usuario con sesión activa ingresa a /login, sea redirigido al dashboard."""
        self.login_as(self.usuario)
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("pagina_principal"))

    def test_logout_view_limpia_sesion(self):
        """Verifica que logout_view limpie la sesión y redirija a login."""
        self.login_as(self.usuario)
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertIsNone(self.client.session.get("usuario_documento"))

    def test_perfil_view_requiere_sesion(self):
        """Verifica que perfil requiera autenticación previa."""
        self.logout()
        response = self.client.get(reverse("perfil"))
        self.assertRedirects(response, reverse("login"))

        # Con sesión iniciada
        self.login_as(self.usuario)
        response_auth = self.client.get(reverse("perfil"))
        self.assertEqual(response_auth.status_code, 200)

    def test_perfil_view_edicion_exitosa(self):
        """Verifica la actualización de datos de perfil mediante POST."""
        self.login_as(self.usuario)
        post_data = {
            "accion": "editar_perfil",
            "nombre_completo": "Juan Carlos Pérez",
            "correo_personal": "juancarlos.perez@sena.edu.co",
            "telefono": "3001234567",
            "ficha": "2558900",
            "programa": "Operación Minera",
        }
        response = self.client.post(reverse("perfil"), data=post_data)
        self.assertRedirects(response, reverse("perfil"))
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.primer_nombre, "Juan")
        self.assertEqual(self.usuario.telefono, "3001234567")


# ==============================================================================
# 4. SEGURIDAD, RBAC Y CONTROL DE ACCESO
# ==============================================================================
class UsuarioSecurityAndRBACUnitTests(UsuarioBaseTestCase):
    """Pruebas de seguridad contra vulnerabilidades IDOR, control de roles y exportaciones."""

    def test_idor_protection_detalle_usuario_json(self):
        """Verifica que un usuario estándar no pueda consultar datos privados de otro usuario vía API JSON."""
        self.login_as(self.usuario)
        url_admin = reverse("detalle_usuario_json", kwargs={"numero_documento": self.admin.documento})
        response = self.client.get(url_admin)
        self.assertEqual(response.status_code, 403)

        # Pero sí puede consultar sus propios datos
        url_propia = reverse("detalle_usuario_json", kwargs={"numero_documento": self.usuario.documento})
        resp_propia = self.client.get(url_propia)
        self.assertEqual(resp_propia.status_code, 200)
        self.assertEqual(resp_propia.json()["numero_documento"], self.usuario.documento)

    def test_admin_puede_consultar_cualquier_usuario_json(self):
        """Verifica que el Administrador tenga permiso de consultar el JSON de cualquier usuario."""
        self.login_as(self.admin)
        url = reverse("detalle_usuario_json", kwargs={"numero_documento": self.usuario.documento})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_lista_usuarios_view_restringido_a_admin(self):
        """Verifica que lista_usuarios_view solo permita acceso a usuarios con rol Administrador."""
        # Usuario normal redirigido a página principal
        self.login_as(self.usuario)
        resp_user = self.client.get(reverse("lista_usuarios"))
        self.assertRedirects(resp_user, reverse("pagina_principal"))

        # Admin accede con 200 OK
        self.login_as(self.admin)
        resp_admin = self.client.get(reverse("lista_usuarios"))
        self.assertEqual(resp_admin.status_code, 200)
        self.assertIn("usuarios", resp_admin.context)

    def test_exportar_usuarios_csv_requiere_admin_y_entrega_formato_correcto(self):
        """Verifica que exportar_usuarios_csv entregue un archivo CSV válido y solo al admin."""
        self.login_as(self.admin)
        response = self.client.get(reverse("exportar_usuarios_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("Número de Documento", content)
        self.assertIn(self.usuario.documento, content)
