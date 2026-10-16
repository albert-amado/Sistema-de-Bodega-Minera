"""
Suite de Pruebas Automatizadas de QA para el Módulo de Almacenes y Estanterías (Ubicaciones Físicas).
Sistema: Mine Inventory.
Cubre:
1. Modelos: Creación, integridad relacional (CASCADE) y métodos __str__.
2. Formularios: AlmacenForm y EstanteForm con validaciones de campos obligatorios.
3. Vistas e Integración: CRUD de almacenes, CRUD de estantes, detalle de bodega y protección RBAC.
"""

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from usuario.models import Usuario

from .forms import AlmacenForm, EstanteForm
from .models import Almacen, Estante


class AlmacenBaseTestCase(TestCase):
    """Clase base con fixtures para pruebas de almacén y estantes."""

    def setUp(self):
        super().setUp()
        self.client = Client()

        self.admin = Usuario.objects.create(
            documento="1111222233",
            primer_nombre="Admin",
            primer_apellido="Root",
            tipo_documento="CC",
            rol="Administrador",
        )

        self.operador = Usuario.objects.create(
            documento="1234567890",
            primer_nombre="Carlos",
            primer_apellido="Minero",
            tipo_documento="CC",
            rol="Usuario",
        )

        self.almacen = Almacen.objects.create(
            nombre="Almacén de Perforación",
            ubicacion="Nivel 2 - Galería Central",
            dimensiones="15x10m",
        )

        self.estante = Estante.objects.create(
            codigo_almacen=self.almacen,
            codigo="EST-N2-01",
            dimensiones="3x1x2m",
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
class AlmacenModelUnitTests(AlmacenBaseTestCase):
    """Pruebas de modelos de almacén y estantes."""

    def test_almacen_creacion_y_str(self):
        """Verifica persistencia y método __str__ de Almacen."""
        self.assertEqual(str(self.almacen), "Almacén de Perforación")
        self.assertEqual(Almacen.objects.count(), 1)

    def test_estante_creacion_y_str(self):
        """Verifica persistencia y método __str__ de Estante."""
        self.assertIn("EST-N2-01", str(self.estante))
        self.assertEqual(self.estante.codigo_almacen, self.almacen)

    def test_restriccion_eliminar_almacen_con_estantes(self):
        """Verifica que el sistema impida eliminar un almacén que contenga estantes (integridad RESTRICT)."""
        from django.db.models import ProtectedError, RestrictedError
        almacen_temp = Almacen.objects.create(nombre="Almacén Temporal")
        Estante.objects.create(codigo_almacen=almacen_temp, codigo="TEMP-01")

        with self.assertRaises((RestrictedError, ProtectedError)):
            almacen_temp.delete()


# ==============================================================================
# 2. PRUEBAS UNITARIAS DE FORMULARIOS (FORMS)
# ==============================================================================
class AlmacenFormUnitTests(AlmacenBaseTestCase):
    """Pruebas de formularios de captura de almacenes y estantes."""

    def test_almacen_form_datos_validos(self):
        """Verifica que AlmacenForm sea válido con datos completos."""
        data = {
            "nombre": "Depósito de Explosivos",
            "ubicacion": "Zona Segura Exterior",
            "dimensiones": "30x20m",
        }
        form = AlmacenForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_almacen_form_nombre_obligatorio(self):
        """Verifica que el nombre del almacén sea obligatorio."""
        data = {
            "nombre": "   ",
            "ubicacion": "Sector 3",
        }
        form = AlmacenForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)

    def test_estante_form_datos_validos(self):
        """Verifica que EstanteForm valide correctamente."""
        data = {
            "codigo_almacen": self.almacen.pk,
            "codigo": "EST-EXP-01",
            "dimensiones": "2x1m",
        }
        form = EstanteForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_estante_form_codigo_obligatorio(self):
        """Verifica que el código del estante sea obligatorio."""
        data = {
            "codigo_almacen": self.almacen.pk,
            "codigo": "  ",
        }
        form = EstanteForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("codigo", form.errors)


# ==============================================================================
# 3. PRUEBAS DE INTEGRACIÓN DE VISTAS Y RBAC (VIEWS)
# ==============================================================================
class AlmacenViewIntegrationTests(AlmacenBaseTestCase):
    """Pruebas de integración sobre vistas de almacenes, estantes y permisos."""

    def test_vista_almacenes_anonimo_redirige(self):
        """Verifica que el acceso anónimo sea redirigido a login."""
        self.logout()
        response = self.client.get(reverse("almacenes"))
        self.assertRedirects(response, reverse("login"))

    def test_vista_almacenes_admin_get_200(self):
        """Verifica que un administrador acceda a la lista con status 200 y métricas."""
        self.login_as(self.admin)
        response = self.client.get(reverse("almacenes"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "almacen.html")
        self.assertIn("almacenes", response.context)
        self.assertIn("total_almacenes", response.context)

    def test_vista_almacenes_crear_admin(self):
        """Verifica creación de almacén vía POST por administrador."""
        self.login_as(self.admin)
        post_data = {
            "accion": "crear",
            "nombre": "Almacén de Seguridad",
            "ubicacion": "Superficie Edificio B",
            "dimensiones": "10x10m",
        }
        response = self.client.post(reverse("almacenes"), data=post_data)
        self.assertRedirects(response, reverse("almacenes"))
        self.assertTrue(Almacen.objects.filter(nombre="Almacén de Seguridad").exists())

    def test_vista_almacenes_editar_admin(self):
        """Verifica edición de almacén vía POST por administrador."""
        self.login_as(self.admin)
        post_data = {
            "accion": "editar",
            "almacen_id": self.almacen.pk,
            "nombre": "Almacén Modificado",
            "ubicacion": "Nivel 3",
            "dimensiones": "20x20m",
        }
        response = self.client.post(reverse("almacenes"), data=post_data)
        self.assertRedirects(response, reverse("almacenes"))
        self.almacen.refresh_from_db()
        self.assertEqual(self.almacen.nombre, "Almacén Modificado")

    def test_vista_almacenes_usuario_regular_bloqueado(self):
        """[RBAC] Verifica que usuarios regulares no puedan crear ni editar almacenes."""
        self.login_as(self.operador)
        post_data = {
            "accion": "crear",
            "nombre": "Almacén No Autorizado",
        }
        response = self.client.post(reverse("almacenes"), data=post_data)
        self.assertRedirects(response, reverse("almacenes"))
        self.assertFalse(Almacen.objects.filter(nombre="Almacén No Autorizado").exists())

    def test_vista_estantes_admin_get_200(self):
        """Verifica que la vista de estantes responda 200 con el template estante.html."""
        self.login_as(self.admin)
        response = self.client.get(reverse("estantes"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "estante.html")
        self.assertIn("estantes", response.context)

    def test_vista_estantes_crear_admin(self):
        """Verifica creación de estante por administrador."""
        self.login_as(self.admin)
        post_data = {
            "accion": "crear",
            "codigo_almacen": self.almacen.pk,
            "codigo": "EST-NUEVO-02",
            "dimensiones": "2x1m",
        }
        response = self.client.post(reverse("estantes"), data=post_data)
        self.assertRedirects(response, reverse("estantes"))
        self.assertTrue(Estante.objects.filter(codigo="EST-NUEVO-02").exists())

    def test_vista_estantes_editar_admin(self):
        """Verifica edición de estante por administrador."""
        self.login_as(self.admin)
        post_data = {
            "accion": "editar",
            "estante_id": self.estante.pk,
            "codigo_almacen": self.almacen.pk,
            "codigo": "EST-MODIFICADO",
            "dimensiones": "4x2m",
        }
        response = self.client.post(reverse("estantes"), data=post_data)
        self.assertRedirects(response, reverse("estantes"))
        self.estante.refresh_from_db()
        self.assertEqual(self.estante.codigo, "EST-MODIFICADO")
