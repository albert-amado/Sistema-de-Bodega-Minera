"""
Suite de Pruebas Automatizadas de QA para el Módulo de Dashboard y Página Principal.
Sistema: Mine Inventory.
Cubre:
1. Seguridad: Acceso anónimo y sesiones inválidas redirigen a login.
2. Vistas y KPIs: Carga del dashboard consolidado vs personal con Chart.js data y métricas.
3. Métricas y Tendencias: Cálculo analítico de ventanas cronológicas de 6 meses.
"""

from datetime import date
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from prestamo.models import EstadoPrestamo, Prestamo
from usuario.models import Usuario

from .views import _rango_ultimos_6_meses


class PaginaPrincipalDashboardTests(TestCase):
    """Pruebas de seguridad, integración y lógica analítica para el Dashboard principal."""

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

        self.usuario = Usuario.objects.create(
            documento="1234567890",
            primer_nombre="Carlos",
            primer_apellido="Pérez",
            tipo_documento="CC",
            rol="Usuario",
        )

        # Crear préstamo entregado
        self.prestamo = Prestamo.objects.create(
            documento=self.usuario,
            estado=EstadoPrestamo.ENTREGADO,
            ficha="2558900",
        )

    def login_as(self, usuario):
        session = self.client.session
        session["usuario_documento"] = usuario.documento
        session["usuario_nombre"] = usuario.nombre_completo
        session["usuario_rol"] = usuario.rol
        session["usuario_tipo_documento"] = usuario.tipo_documento
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

    def test_anonymous_redirected_to_login(self):
        """Verifica que usuarios anónimos sean redirigidos al login."""
        response = self.client.get(reverse("pagina_principal"))
        self.assertRedirects(response, reverse("login"))

    def test_authenticated_admin_can_access_dashboard_with_global_kpis(self):
        """Verifica que el Administrador acceda al dashboard con KPIs y contexto completo."""
        self.login_as(self.admin)
        response = self.client.get(reverse("pagina_principal"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["usuario"].rol, "Administrador")
        self.assertIn("all_prestamos", response.context)
        self.assertIn("total_prestamos", response.context)
        self.assertIn("kpis", response.context)
        self.assertEqual(response.context["total_prestamos"], 1)

    def test_authenticated_operator_can_access_dashboard_with_personal_loans(self):
        """Verifica que el Operador acceda a su vista personalizada de préstamos."""
        self.login_as(self.usuario)
        response = self.client.get(reverse("pagina_principal"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["usuario"].rol, "Usuario")
        self.assertIn("all_prestamos", response.context)
        self.assertEqual(response.context["all_prestamos"].count(), 1)

    def test_sesion_con_usuario_inexistente_redirige_a_login(self):
        """Verifica que si la sesión tiene un documento que no existe en BD, redirija a login."""
        session = self.client.session
        session["usuario_documento"] = "9999999999"  # No existe en BD
        session["usuario_rol"] = "Usuario"
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        response = self.client.get(reverse("pagina_principal"))
        # Usamos fetch_redirect_response=False porque login redirige si detecta session cookie residual
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)

    def test_calculo_ventana_ultimos_6_meses(self):
        """Valida que _rango_ultimos_6_meses retorne exactamente 6 tuplas ordenadas cronológicamente."""
        hoy = date(2026, 10, 15)
        meses = _rango_ultimos_6_meses(hoy)
        self.assertEqual(len(meses), 6)
        self.assertEqual(meses[-1], (2026, 10))
        self.assertEqual(meses[0], (2026, 5))
