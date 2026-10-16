"""
Suite de Pruebas Automatizadas de QA para el Módulo de Herramientas y Catálogo Minero.
Sistema: Mine Inventory.
Cubre:
1. Modelos: Validación SKU único, conversión de stock_disponible, ubicación por estante y remapping en QuerySet.
2. Formularios: HerramientaForm y CategoriaHerramientaForm con reglas de negocio.
3. Vistas e Integración: Acceso a inventario, cálculo de KPIs, CRUD controlado y protección RBAC.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from almacen.models import Almacen, Estante
from usuario.models import Usuario

from .forms import CategoriaHerramientaForm, HerramientaForm
from .models import CategoriaHerramienta, Herramienta, Proveedor, Suministro


class HerramientaBaseTestCase(TestCase):
    """Clase base con fixtures comunes para pruebas de inventario de herramientas."""

    def setUp(self):
        super().setUp()
        self.client = Client()

        # Usuarios de prueba
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

        # Ubicación física (Almacén y Estante)
        self.almacen = Almacen.objects.create(
            nombre="Polvorín y Almacén Central",
            ubicacion="Bocamina Nivel 1",
            dimensiones="20x15m",
        )
        self.estante = Estante.objects.create(
            codigo_almacen=self.almacen,
            codigo="EST-A1",
            dimensiones="2x1x3m",
        )

        # Categoría y Proveedor
        self.categoria = CategoriaHerramienta.objects.create(
            tipo_herramienta="Perforación",
            nombre_categoria="Martillos y Brocas",
            descripcion="Equipos de penetración de roca",
        )

        self.proveedor = Proveedor.objects.create(
            nit_proveedor="900123456-7",
            correo_proveedor="ventas@equiposmineros.com",
            telefono_contacto="3109876543",
        )

        # Herramienta estándar de prueba
        self.herramienta = Herramienta.objects.create(
            codigo_sku="HER-TAL-001",
            nombre_herramienta="Taladro Percutor Neumático",
            descripcion="Taladro para roca dura",
            disponibilidad="10",
            codigo_categoria=self.categoria,
            estante=self.estante,
            estado="Operativo",
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
class HerramientaModelUnitTests(HerramientaBaseTestCase):
    """Pruebas unitarias de modelos, campos calculados y reglas de negocio."""

    def test_herramienta_str_and_properties(self):
        """Verifica método __str__ y propiedades alias (codigo, nombre, stock_disponible)."""
        self.assertEqual(str(self.herramienta), "Taladro Percutor Neumático")
        self.assertEqual(self.herramienta.codigo, "HER-TAL-001")
        self.assertEqual(self.herramienta.nombre, "Taladro Percutor Neumático")
        self.assertEqual(self.herramienta.stock_disponible, 10)

    def test_stock_disponible_getter_and_setter(self):
        """Verifica que el setter actualice 'disponibilidad' y maneje valores frontera."""
        self.herramienta.stock_disponible = 5
        self.assertEqual(self.herramienta.disponibilidad, "5")
        self.assertEqual(self.herramienta.stock_disponible, 5)

        # Si se asigna valor negativo, debe truncar en 0
        self.herramienta.stock_disponible = -3
        self.assertEqual(self.herramienta.stock_disponible, 0)
        self.assertEqual(self.herramienta.disponibilidad, "0")

    def test_stock_disponible_string_no_disponible(self):
        """Verifica que un estado explícito de 'No disponible' retorne 0 stock."""
        h = Herramienta(disponibilidad="No disponible")
        self.assertEqual(h.stock_disponible, 0)

    def test_propiedad_ubicacion_estante(self):
        """Verifica que 'ubicacion' retorne el estante si existe o 'Sin ubicación'."""
        self.assertIn("EST-A1", self.herramienta.ubicacion)

        h_sin_estante = Herramienta(nombre_herramienta="Pica manual")
        self.assertEqual(h_sin_estante.ubicacion, "Sin ubicación")

    def test_sku_duplicado_clean_lanza_validation_error(self):
        """Verifica que clean() impida duplicar el código SKU entre herramientas."""
        herramienta_duplicada = Herramienta(
            codigo_sku="HER-TAL-001",  # Ya existe
            nombre_herramienta="Otro taladro",
            disponibilidad="2",
        )
        with self.assertRaises(ValidationError) as ctx:
            herramienta_duplicada.clean()
        self.assertIn("codigo_sku", ctx.exception.message_dict)

    def test_categoria_y_proveedor_str(self):
        """Verifica los métodos __str__ de CategoriaHerramienta y Proveedor."""
        self.assertEqual(str(self.categoria), "Martillos y Brocas")
        self.assertIn("900123456-7", str(self.proveedor))

    def test_herramienta_queryset_remap(self):
        """Verifica la compatibilidad de remapeo de kwargs del QuerySet personalizado."""
        # Búsqueda por alias 'codigo' en vez de 'codigo_sku'
        item = Herramienta.objects.get(codigo="HER-TAL-001")
        self.assertEqual(item.pk, self.herramienta.pk)

        # Búsqueda por alias 'nombre'
        item2 = Herramienta.objects.get(nombre="Taladro Percutor Neumático")
        self.assertEqual(item2.pk, self.herramienta.pk)


# ==============================================================================
# 2. PRUEBAS UNITARIAS DE FORMULARIOS (FORMS)
# ==============================================================================
class HerramientaFormUnitTests(HerramientaBaseTestCase):
    """Pruebas de formularios de creación y edición de herramientas."""

    def test_herramienta_form_valido(self):
        """Verifica que HerramientaForm valide correctamente datos consistentes."""
        data = {
            "codigo_sku": "PUL-MIN-02",
            "nombre_herramienta": "Pulidora Industrial 9 Pulgadas",
            "descripcion": "Pulidora para mantenimiento de tolvas",
            "disponibilidad": "8",
            "codigo_categoria": self.categoria.pk,
            "estante": self.estante.pk,
        }
        form = HerramientaForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_herramienta_form_nombre_obligatorio(self):
        """Verifica que HerramientaForm rechace nombres en blanco."""
        data = {
            "codigo_sku": "SKU-999",
            "nombre_herramienta": "   ",
            "disponibilidad": "1",
        }
        form = HerramientaForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("nombre_herramienta", form.errors)

    def test_herramienta_form_disponibilidad_negativa_invalida(self):
        """Verifica que no se permita disponibilidad numérica negativa."""
        data = {
            "nombre_herramienta": "Cincel de acero",
            "disponibilidad": "-5",
        }
        form = HerramientaForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("disponibilidad", form.errors)

    def test_categoria_form_valido(self):
        """Verifica creación válida de categoría mediante CategoriaHerramientaForm."""
        data = {
            "nombre_categoria": "Iluminación Subterránea",
            "tipo_herramienta": "Eléctrica",
            "descripcion": "Lámparas y reflectores para galerías",
        }
        form = CategoriaHerramientaForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


# ==============================================================================
# 3. PRUEBAS DE INTEGRACIÓN DE VISTAS Y RBAC (VIEWS)
# ==============================================================================
class HerramientaViewIntegrationTests(HerramientaBaseTestCase):
    """Pruebas de integración sobre la vista de inventario, KPIs y acciones administrativas."""

    def test_inventario_anonimo_redirige_a_login(self):
        """Verifica que un usuario sin sesión sea redirigido a login al intentar ver inventario."""
        self.logout()
        response = self.client.get(reverse("inventario"))
        self.assertRedirects(response, reverse("login"))

    def test_inventario_autenticado_status_200_y_kpis(self):
        """Verifica que un usuario autenticado pueda visualizar el catálogo con KPIs correctos."""
        self.login_as(self.operador)
        response = self.client.get(reverse("inventario"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario.html")
        self.assertIn("productos", response.context)
        self.assertIn("kpi_total_productos", response.context)
        self.assertEqual(response.context["kpi_total_productos"], 1)

    def test_crear_producto_admin_exitoso(self):
        """Verifica que un Administrador pueda registrar una nueva herramienta mediante POST."""
        self.login_as(self.admin)
        post_data = {
            "accion": "crear_producto",
            "codigo_sku": "ROT-BOS-03",
            "nombre": "Rotomartillo Bosch",
            "categoria": self.categoria.pk,
            "descripcion": "Para anclaje de mallas",
            "estante": self.estante.pk,
            "stock": "4",
        }
        response = self.client.post(reverse("inventario"), data=post_data)
        self.assertRedirects(response, reverse("inventario"))

        self.assertTrue(Herramienta.objects.filter(codigo_sku="ROT-BOS-03").exists())
        nuevo = Herramienta.objects.get(codigo_sku="ROT-BOS-03")
        self.assertEqual(nuevo.stock_disponible, 4)

    def test_crear_producto_usuario_regular_bloqueado(self):
        """[RBAC] Verifica que un usuario normal no pueda crear herramientas en el catálogo."""
        self.login_as(self.operador)
        post_data = {
            "accion": "crear_producto",
            "codigo_sku": "PICA-01",
            "nombre": "Pica no autorizada",
            "stock": "1",
        }
        response = self.client.post(reverse("inventario"), data=post_data)
        self.assertRedirects(response, reverse("inventario"))

        # No debe haberse creado
        self.assertFalse(Herramienta.objects.filter(codigo_sku="PICA-01").exists())

    def test_crear_producto_stock_invalido_fuera_de_rango(self):
        """Verifica que stocks negativos o superiores a 10,000 unidades sean rechazados."""
        self.login_as(self.admin)
        post_data = {
            "accion": "crear_producto",
            "codigo_sku": "OVER-STOCK",
            "nombre": "Herramienta Límite",
            "stock": "15000",  # Excede límite de 10,000
        }
        response = self.client.post(reverse("inventario"), data=post_data)
        self.assertRedirects(response, reverse("inventario"))
        self.assertFalse(Herramienta.objects.filter(codigo_sku="OVER-STOCK").exists())

    def test_editar_producto_admin_actualiza_correctamente(self):
        """Verifica que el Administrador pueda actualizar nombre, descripción y stock."""
        self.login_as(self.admin)
        post_data = {
            "accion": "editar_producto",
            "producto_id": self.herramienta.pk,
            "nombre": "Taladro Percutor Modificado",
            "codigo_sku": "HER-TAL-001",
            "descripcion": "Descripción actualizada",
            "stock": "15",
        }
        response = self.client.post(reverse("inventario"), data=post_data)
        self.assertRedirects(response, reverse("inventario"))

        self.herramienta.refresh_from_db()
        self.assertEqual(self.herramienta.nombre_herramienta, "Taladro Percutor Modificado")
        self.assertEqual(self.herramienta.stock_disponible, 15)

    def test_crear_categoria_admin_exitosa(self):
        """Verifica la creación ágil de categorías desde la vista de inventario."""
        self.login_as(self.admin)
        post_data = {
            "accion": "crear_categoria",
            "cat_nombre": "Ventilación y Ductos",
            "cat_descripcion": "Mangas y ventiladores de tiro forzado",
        }
        response = self.client.post(reverse("inventario"), data=post_data)
        self.assertRedirects(response, reverse("inventario"))

        self.assertTrue(CategoriaHerramienta.objects.filter(nombre_categoria="Ventilación y Ductos").exists())
