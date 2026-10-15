"""
Conjunto de pruebas automatizadas (QA Suite) para el Módulo de Préstamos de Herramientas.
Sistema: Mine Inventory (Sistema de Gestión de Inventario Minero).

Estructura de la Suite:
1. PrestamoBaseTestCase: Fixtures, datos de prueba iniciales (setUp) y helpers de sesión.
2. PrestamoModelUnitTests: Pruebas unitarias sobre modelos, campos, métodos y restricciones.
3. PrestamoFormUnitTests: Pruebas unitarias sobre validaciones de formularios y clean methods.
4. PrestamoViewIntegrationTests: Pruebas de integración sobre flujos de vistas, respuestas HTTP y templates.
5. PrestamoEdgeCasesAndSecurityTests: Pruebas de casos límite, control de concurrencia/stock y seguridad RBAC.
"""

from datetime import timedelta
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from herramienta.models import CategoriaHerramienta, Herramienta
from usuario.models import Usuario

from .forms import (
    DetallePrestamoForm,
    DevolucionHerramientaForm,
    EditarPrestamoObservacionesForm,
    PrestamoForm,
    SolicitudPrestamoUsuarioForm,
)
from .models import (
    DetallePrestamo,
    DevolucionHerramienta,
    EstadoPrestamo,
    Prestamo,
)


class PrestamoBaseTestCase(TestCase):
    """
    Clase base para la suite de pruebas del módulo de préstamos.
    Centraliza la preparación de datos (setUp) y utilidades de autenticación / sesión.
    """

    def setUp(self):
        super().setUp()
        self.client = Client()

        # 1. Crear usuarios de prueba (Admin y Usuarios regulares)
        self.admin = Usuario.objects.create(
            documento="987654321",
            primer_nombre="Admin",
            primer_apellido="Bodega",
            tipo_documento="CC",
            rol="Administrador",
            ficha="ADM-001",
        )

        self.usuario_operador = Usuario.objects.create(
            documento="1098765432",
            primer_nombre="Carlos",
            primer_apellido="Minero",
            tipo_documento="CC",
            rol="Usuario",
            ficha="2558901",
        )

        self.usuario_auxiliar = Usuario.objects.create(
            documento="1012345678",
            primer_nombre="Laura",
            primer_apellido="Gómez",
            tipo_documento="CC",
            rol="Usuario",
            ficha="2558902",
        )

        # 2. Categoría de herramientas para el entorno minero
        self.categoria = CategoriaHerramienta.objects.create(
            tipo_herramienta="Perforación y Extracción",
            nombre_categoria="Herramienta Pesada",
            descripcion="Equipos para labor subterránea",
        )

        # 3. Herramientas con diferentes estados de stock
        # Herramienta con stock normal (10 unidades)
        self.herramienta_disponible = Herramienta.objects.create(
            codigo_sku="TAL-IND-01",
            nombre_herramienta="Taladro Percutor de Mina",
            descripcion="Taladro neumático industrial de alta resistencia",
            codigo_categoria=self.categoria,
            disponibilidad="10",
            estado="Operativo",
        )

        # Herramienta con stock crítico (1 unidad)
        self.herramienta_stock_bajo = Herramienta.objects.create(
            codigo_sku="DET-GAS-01",
            nombre_herramienta="Detector de Metano Multigas",
            descripcion="Sensor portátil de gases inflamables",
            codigo_categoria=self.categoria,
            disponibilidad="1",
            estado="Calibrado",
        )

        # Herramienta agotada (0 unidades)
        self.herramienta_sin_stock = Herramienta.objects.create(
            codigo_sku="LAM-MIN-00",
            nombre_herramienta="Lámpara Minera LED Frontal",
            descripcion="Lámpara recargable a prueba de explosión",
            codigo_categoria=self.categoria,
            disponibilidad="0",
            estado="Agotado",
        )

    def login_as(self, usuario):
        """Helper para autenticar usuarios simulando variables de sesión personalizadas."""
        session = self.client.session
        session["usuario_documento"] = usuario.documento
        session["usuario_rol"] = usuario.rol
        session.save()

    def logout(self):
        """Helper para limpiar sesión activa."""
        session = self.client.session
        session.flush()
        session.save()


# ==============================================================================
# 1. PRUEBAS UNITARIAS DE MODELOS (MODELS)
# ==============================================================================
class PrestamoModelUnitTests(PrestamoBaseTestCase):
    """Pruebas unitarias de modelos, validaciones y métodos personalizados."""

    def test_creacion_prestamo_exitoso_y_str(self):
        """[AAA] Verifica creación exitosa de un Préstamo y su método __str__."""
        # Arrange & Act
        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            fecha=timezone.now().date(),
            ficha="2558901",
            estado=EstadoPrestamo.PENDIENTE,
            observaciones="Préstamo para turno 1 en frente norte",
        )

        # Assert
        self.assertIsNotNone(prestamo.codigo_prestamo)
        self.assertEqual(prestamo.estado, EstadoPrestamo.PENDIENTE)
        self.assertEqual(prestamo.usuario, self.usuario_operador)
        self.assertEqual(
            str(prestamo),
            f"Préstamo #{prestamo.codigo_prestamo} - Ficha 2558901",
        )

    def test_prestamo_propiedad_usuario_getter_y_setter(self):
        """Verifica que la propiedad 'usuario' obtenga y asigne correctamente el ForeignKey 'documento'."""
        prestamo = Prestamo(documento=self.usuario_operador)
        self.assertEqual(prestamo.usuario, self.usuario_operador)

        prestamo.usuario = self.usuario_auxiliar
        self.assertEqual(prestamo.documento, self.usuario_auxiliar)

    def test_prestamo_clean_valida_documento_no_numerico(self):
        """Verifica que clean() lance ValidationError si el documento no es numérico."""
        prestamo = Prestamo(
            documento_id="DOC-ALFA-123",
            ficha="2558901",
        )
        with self.assertRaises(ValidationError) as ctx:
            prestamo.clean()
        self.assertIn("documento", ctx.exception.message_dict)

    def test_prestamo_save_autocrea_usuario_si_no_existe(self):
        """Verifica que save() cree automáticamente el registro de Usuario si este no existe en la BD."""
        doc_nuevo = "70998877"
        self.assertFalse(Usuario.objects.filter(documento=doc_nuevo).exists())

        prestamo = Prestamo.objects.create(
            documento_id=doc_nuevo,
            ficha="FICHANEW",
        )

        self.assertTrue(Usuario.objects.filter(documento=doc_nuevo).exists())
        creado = Usuario.objects.get(documento=doc_nuevo)
        self.assertEqual(creado.rol, "Usuario")
        self.assertEqual(prestamo.documento, creado)

    def test_detalle_prestamo_clean_valida_stock_insuficiente(self):
        """Verifica que DetallePrestamo.clean() impida asignar una cantidad superior al stock disponible."""
        prestamo = Prestamo.objects.create(documento=self.usuario_operador)
        # La herramienta disponible tiene 10 unidades. Intentamos pedir 15.
        detalle = DetallePrestamo(
            codigo_prestamo=prestamo,
            codigo_herramienta=self.herramienta_disponible,
            cantidad=15,
        )

        with self.assertRaises(ValidationError) as ctx:
            detalle.clean()
        self.assertIn("cantidad", ctx.exception.message_dict)
        self.assertIn("Stock insuficiente", str(ctx.exception.message_dict["cantidad"][0]))

    def test_detalle_prestamo_propiedades_y_str(self):
        """Verifica propiedades alias y método __str__ de DetallePrestamo."""
        prestamo = Prestamo.objects.create(documento=self.usuario_operador)
        detalle = DetallePrestamo.objects.create(
            codigo_prestamo=prestamo,
            codigo_herramienta=self.herramienta_disponible,
            cantidad=3,
        )

        self.assertEqual(detalle.prestamo, prestamo)
        self.assertEqual(detalle.herramienta, self.herramienta_disponible)
        self.assertIn("3x Taladro Percutor de Mina", str(detalle))

    def test_devolucion_herramienta_propiedades_y_str(self):
        """Verifica creación y formato __str__ del modelo DevolucionHerramienta."""
        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            estado=EstadoPrestamo.ENTREGADO,
        )
        devolucion = DevolucionHerramienta.objects.create(
            codigo_prestamo=prestamo,
            codigo_recibe=self.admin,
            observaciones="Herramientas devueltas en buen estado",
        )

        self.assertEqual(devolucion.prestamo, prestamo)
        self.assertEqual(devolucion.recibido_por, self.admin)
        self.assertIn(f"Devolución #{devolucion.codigo_devolucion}", str(devolucion))


# ==============================================================================
# 2. PRUEBAS UNITARIAS DE FORMULARIOS (FORMS)
# ==============================================================================
class PrestamoFormUnitTests(PrestamoBaseTestCase):
    """Pruebas unitarias de formularios y reglas de negocio en la capa de captura."""

    def test_prestamo_form_datos_validos(self):
        """Verifica que PrestamoForm sea válido con datos correctos."""
        form_data = {
            "documento": self.usuario_operador.documento,
            "ficha": "2558901",
            "fecha": timezone.localdate().isoformat(),
            "observaciones": "Entrega de turno mañana",
        }
        form = PrestamoForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_prestamo_form_fecha_futura_invalida(self):
        """Verifica que PrestamoForm rechace fechas futuras."""
        fecha_futura = (timezone.localdate() + timedelta(days=2)).isoformat()
        form_data = {
            "documento": self.usuario_operador.documento,
            "ficha": "2558901",
            "fecha": fecha_futura,
        }
        form = PrestamoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("fecha", form.errors)
        self.assertIn("no puede ser una fecha futura", form.errors["fecha"][0])

    def test_prestamo_form_fecha_retroactiva_mayor_a_30_dias_invalida(self):
        """Verifica que PrestamoForm rechace registros con más de 30 días de retroactividad."""
        fecha_antigua = (timezone.localdate() - timedelta(days=35)).isoformat()
        form_data = {
            "documento": self.usuario_operador.documento,
            "ficha": "2558901",
            "fecha": fecha_antigua,
        }
        form = PrestamoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("fecha", form.errors)
        self.assertIn("más de 30 días", form.errors["fecha"][0])

    def test_solicitud_usuario_form_validacion_ficha(self):
        """Verifica que SolicitudPrestamoUsuarioForm obligue a ingresar ficha no vacía."""
        # Ficha con solo espacios
        form_invalido = SolicitudPrestamoUsuarioForm(data={"ficha": "   ", "observaciones": "Test"})
        self.assertFalse(form_invalido.is_valid())
        self.assertIn("ficha", form_invalido.errors)

        # Ficha válida
        form_valido = SolicitudPrestamoUsuarioForm(data={"ficha": "2558901", "observaciones": "Test"})
        self.assertTrue(form_valido.is_valid())

    def test_detalle_prestamo_form_cantidad_invalida_limites(self):
        """Verifica que DetallePrestamoForm valide límites de cantidad (menor igual a 0 o mayor a 50)."""
        # Cantidad cero o negativa
        form_cero = DetallePrestamoForm(data={
            "codigo_herramienta": self.herramienta_disponible.pk,
            "cantidad": 0,
        })
        self.assertFalse(form_cero.is_valid())
        self.assertIn("cantidad", form_cero.errors)

        # Cantidad mayor a 50 unidades (límite de la empresa minera)
        form_exceso = DetallePrestamoForm(data={
            "codigo_herramienta": self.herramienta_disponible.pk,
            "cantidad": 51,
        })
        self.assertFalse(form_exceso.is_valid())
        self.assertIn("cantidad", form_exceso.errors)
        self.assertIn("máxima por herramienta es 50", form_exceso.errors["cantidad"][0])

    def test_detalle_prestamo_form_cantidad_superior_al_stock(self):
        """Verifica que DetallePrestamoForm rechace cantidades superiores al stock disponible."""
        # La herramienta tiene 10 disponibles; pedimos 12
        form = DetallePrestamoForm(data={
            "codigo_herramienta": self.herramienta_disponible.pk,
            "cantidad": 12,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)
        self.assertIn("Stock insuficiente", form.errors["cantidad"][0])

    def test_devolucion_herramienta_form_validaciones_de_fecha(self):
        """Verifica que DevolucionHerramientaForm valide fechas respecto al préstamo y al día de hoy."""
        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            fecha=timezone.localdate() - timedelta(days=2),
            estado=EstadoPrestamo.ENTREGADO,
        )

        # 1. Fecha de devolución anterior a la fecha en que se prestó
        form_anterior = DevolucionHerramientaForm(data={
            "codigo_prestamo": prestamo.pk,
            "fecha": (prestamo.fecha - timedelta(days=1)).isoformat(),
        })
        self.assertFalse(form_anterior.is_valid())
        self.assertIn("fecha", form_anterior.errors)

        # 2. Fecha de devolución futura
        form_futuro = DevolucionHerramientaForm(data={
            "codigo_prestamo": prestamo.pk,
            "fecha": (timezone.localdate() + timedelta(days=1)).isoformat(),
        })
        self.assertFalse(form_futuro.is_valid())
        self.assertIn("fecha", form_futuro.errors)

    def test_editar_observaciones_form(self):
        """Verifica que EditarPrestamoObservacionesForm permita actualizar las notas."""
        prestamo = Prestamo.objects.create(documento=self.usuario_operador, observaciones="Inicial")
        form = EditarPrestamoObservacionesForm(data={"observaciones": "Observación actualizada"}, instance=prestamo)
        self.assertTrue(form.is_valid())
        prestamo_actualizado = form.save()
        self.assertEqual(prestamo_actualizado.observaciones, "Observación actualizada")


# ==============================================================================
# 3. PRUEBAS DE INTEGRACIÓN DE VISTAS (VIEWS & WORKFLOWS)
# ==============================================================================
class PrestamoViewIntegrationTests(PrestamoBaseTestCase):
    """Pruebas de integración para flujos de usuario y administrador en las vistas."""

    def test_prestamo_lista_admin_status_200_y_template(self):
        """Verifica que un administrador acceda a la vista principal de préstamos con status 200 y template correcto."""
        self.login_as(self.admin)
        response = self.client.get(reverse("prestamo"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "prestamo.html")
        self.assertIn("prestamos", response.context)
        self.assertIn("total_prestamos", response.context)

    def test_prestamo_lista_usuario_estandar_redirecciona_a_su_portal(self):
        """Verifica que un usuario estándar que intente acceder al panel de administración sea redirigido a 'prestamo_usuario'."""
        self.login_as(self.usuario_operador)
        response = self.client.get(reverse("prestamo"))

        self.assertRedirects(response, reverse("prestamo_usuario"))

    def test_prestamo_usuario_lista_status_200_y_filtro_personalizado(self):
        """Verifica que el portal de usuario renderice 200 y únicamente liste los préstamos del usuario en sesión."""
        # Creamos un préstamo para el operador y otro para el auxiliar
        Prestamo.objects.create(documento=self.usuario_operador, ficha="2558901")
        Prestamo.objects.create(documento=self.usuario_auxiliar, ficha="2558902")

        self.login_as(self.usuario_operador)
        response = self.client.get(reverse("prestamo_usuario"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "prestamo_usuario.html")
        prestamos_mostrados = response.context["all_prestamos"]
        self.assertEqual(prestamos_mostrados.count(), 1)
        self.assertEqual(prestamos_mostrados.first().documento, self.usuario_operador)

    def test_flujo_completo_solicitud_y_aprobacion_descuenta_stock(self):
        """
        [Flujo E2E Integración]
        1. Operador solicita 2 taladros. Estado: PENDIENTE. Stock disponible sigue en 10.
        2. Administrador aprueba el préstamo. Estado: ENTREGADO. Stock disponible pasa a 8.
        """
        # Paso 1: Solicitud por parte del usuario
        self.login_as(self.usuario_operador)
        post_data = {
            "ficha": "2558901",
            "observaciones": "Trabajo en galería 4",
            "herramienta[]": [self.herramienta_disponible.pk],
            "cantidad[]": [2],
        }
        resp_solicitud = self.client.post(reverse("usuario_solicitar_prestamo"), data=post_data)
        self.assertRedirects(resp_solicitud, reverse("prestamo_usuario"))

        prestamo = Prestamo.objects.filter(documento=self.usuario_operador).latest("codigo_prestamo")
        self.assertEqual(prestamo.estado, EstadoPrestamo.PENDIENTE)

        # El stock no debe descontarse al estar solo solicitado
        self.herramienta_disponible.refresh_from_db()
        self.assertEqual(self.herramienta_disponible.stock_disponible, 10)

        # Paso 2: Aprobación por parte del administrador
        self.login_as(self.admin)
        resp_aprobacion = self.client.post(reverse("aprobar_prestamo"), {"pk": prestamo.pk})
        self.assertRedirects(resp_aprobacion, reverse("prestamo"))

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, EstadoPrestamo.ENTREGADO)

        # El stock debe descontarse exactamente en 2 unidades (10 - 2 = 8)
        self.herramienta_disponible.refresh_from_db()
        self.assertEqual(self.herramienta_disponible.stock_disponible, 8)

    def test_flujo_rechazo_prestamo_no_altera_stock(self):
        """Verifica que rechazar un préstamo cambie el estado a CANCELADO sin descontar stock."""
        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            estado=EstadoPrestamo.PENDIENTE,
        )
        DetallePrestamo.objects.create(
            codigo_prestamo=prestamo,
            codigo_herramienta=self.herramienta_disponible,
            cantidad=3,
        )

        self.login_as(self.admin)
        post_data = {
            "pk": prestamo.pk,
            "motivo_rechazo": "Falta autorización del supervisor de seguridad",
        }
        response = self.client.post(reverse("rechazar_prestamo"), data=post_data)
        self.assertRedirects(response, reverse("prestamo"))

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, EstadoPrestamo.CANCELADO)
        self.assertIn("Falta autorización", prestamo.observaciones)

        # Stock intacto
        self.herramienta_disponible.refresh_from_db()
        self.assertEqual(self.herramienta_disponible.stock_disponible, 10)

    def test_flujo_devolucion_total_restaura_stock_y_registra_devolucion(self):
        """Verifica que devolver un préstamo entregado restaure el stock y registre la devolución."""
        # Estado inicial: Préstamo entregado de 4 unidades, stock disponible quedó en 6
        self.herramienta_disponible.stock_disponible = 6
        self.herramienta_disponible.save()

        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            estado=EstadoPrestamo.ENTREGADO,
        )
        DetallePrestamo.objects.create(
            codigo_prestamo=prestamo,
            codigo_herramienta=self.herramienta_disponible,
            cantidad=4,
        )

        self.login_as(self.admin)
        post_data = {
            "pk": prestamo.pk,
            "devolucion_total": "true",
            "observaciones": "Herramientas limpias y operativas",
        }
        response = self.client.post(reverse("devolver_prestamo"), data=post_data)
        self.assertRedirects(response, reverse("prestamo"))

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, EstadoPrestamo.DEVUELTO)

        # Stock restaurado: 6 + 4 = 10
        self.herramienta_disponible.refresh_from_db()
        self.assertEqual(self.herramienta_disponible.stock_disponible, 10)

        # Registro en la tabla de Devolución
        self.assertTrue(DevolucionHerramienta.objects.filter(codigo_prestamo=prestamo).exists())
        dev = DevolucionHerramienta.objects.get(codigo_prestamo=prestamo)
        self.assertEqual(dev.codigo_recibe, self.admin)

    def test_flujo_devolucion_parcial(self):
        """Verifica que indicar devolución no total coloque el préstamo en estado PARCIAL."""
        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            estado=EstadoPrestamo.ENTREGADO,
        )
        DetallePrestamo.objects.create(
            codigo_prestamo=prestamo,
            codigo_herramienta=self.herramienta_disponible,
            cantidad=2,
        )

        self.login_as(self.admin)
        post_data = {
            "pk": prestamo.pk,
            "devolucion_total": "false",
            "observaciones": "Devolvió 1 de 2 taladros",
        }
        self.client.post(reverse("devolver_prestamo"), data=post_data)

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, EstadoPrestamo.PARCIAL)

    def test_devoluciones_lista_admin_200_y_template(self):
        """Verifica que la vista del historial de devoluciones cargue con 200 y el template correcto."""
        self.login_as(self.admin)
        response = self.client.get(reverse("devoluciones_lista"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "devoluciones.html")
        self.assertIn("devoluciones", response.context)
        self.assertIn("prestamos_activos", response.context)

    def test_notificaciones_json_endpoint(self):
        """Verifica respuesta estructurada JSON de las notificaciones."""
        self.login_as(self.admin)
        response = self.client.get(reverse("notificaciones_json"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        json_data = response.json()
        self.assertIn("items", json_data)


# ==============================================================================
# 4. PRUEBAS DE CASOS LÍMITE (EDGE CASES) Y SEGURIDAD RBAC
# ==============================================================================
class PrestamoEdgeCasesAndSecurityTests(PrestamoBaseTestCase):
    """Pruebas rigurosas sobre escenarios adversos, validaciones de seguridad y casos borde."""

    def test_edge_case_solicitar_herramienta_sin_stock_rechazado(self):
        """[Edge Case] Intento de registrar préstamo de una herramienta con stock 0 debe ser rechazado."""
        self.login_as(self.usuario_operador)
        post_data = {
            "ficha": "2558901",
            "herramienta[]": [self.herramienta_sin_stock.pk],
            "cantidad[]": [1],
        }

        # Conteo antes
        prestamos_antes = Prestamo.objects.count()

        response = self.client.post(reverse("usuario_solicitar_prestamo"), data=post_data)
        self.assertRedirects(response, reverse("prestamo_usuario"))

        # No debe haberse creado ningún préstamo
        self.assertEqual(Prestamo.objects.count(), prestamos_antes)

    def test_edge_case_solicitar_cantidad_superior_al_stock_disponible(self):
        """[Edge Case] Intento de solicitar más unidades de las disponibles en inventario."""
        # La herramienta tiene 1 unidad disponible
        self.login_as(self.usuario_operador)
        post_data = {
            "ficha": "2558901",
            "herramienta[]": [self.herramienta_stock_bajo.pk],
            "cantidad[]": [2],  # Pide 2
        }

        prestamos_antes = Prestamo.objects.count()
        response = self.client.post(reverse("usuario_solicitar_prestamo"), data=post_data)
        self.assertRedirects(response, reverse("prestamo_usuario"))

        self.assertEqual(Prestamo.objects.count(), prestamos_antes)
        self.herramienta_stock_bajo.refresh_from_db()
        self.assertEqual(self.herramienta_stock_bajo.stock_disponible, 1)

    def test_edge_case_aprobar_prestamo_cuando_stock_se_agoto_previamente(self):
        """
        [Edge Case Concurrencia/Stock]
        Un préstamo fue solicitado cuando había 1 unidad disponible, pero antes de ser aprobado,
        otro proceso consumió el stock dejándolo en 0. Al intentar aprobar, la vista debe abortar
        la entrega y no dejar stock en valores negativos.
        """
        # Solicitud creada con éxito cuando había stock
        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            estado=EstadoPrestamo.PENDIENTE,
        )
        DetallePrestamo.objects.create(
            codigo_prestamo=prestamo,
            codigo_herramienta=self.herramienta_stock_bajo,
            cantidad=1,
        )

        # Simulamos que el stock fue agotado por otra vía antes de aprobar
        self.herramienta_stock_bajo.stock_disponible = 0
        self.herramienta_stock_bajo.save()

        # El administrador intenta aprobar
        self.login_as(self.admin)
        response = self.client.post(reverse("aprobar_prestamo"), {"pk": prestamo.pk})
        self.assertRedirects(response, reverse("prestamo"))

        prestamo.refresh_from_db()
        # Debe mantenerse en PENDIENTE por falta de stock
        self.assertEqual(prestamo.estado, EstadoPrestamo.PENDIENTE)

        # El stock debe seguir en 0, nunca negativo
        self.herramienta_stock_bajo.refresh_from_db()
        self.assertEqual(self.herramienta_stock_bajo.stock_disponible, 0)

    def test_edge_case_cantidad_excede_limite_maximo_50_unidades(self):
        """[Edge Case] Intento de pedir más de 50 unidades de golpe debe ser rechazado."""
        self.login_as(self.usuario_operador)
        post_data = {
            "ficha": "2558901",
            "herramienta[]": [self.herramienta_disponible.pk],
            "cantidad[]": [51],
        }

        prestamos_antes = Prestamo.objects.count()
        response = self.client.post(reverse("usuario_solicitar_prestamo"), data=post_data)
        self.assertRedirects(response, reverse("prestamo_usuario"))
        self.assertEqual(Prestamo.objects.count(), prestamos_antes)

    def test_seguridad_solicitud_bloquea_suplantacion_de_documento(self):
        """[Seguridad] Verifica que un usuario autenticado no pueda suplantar a otro enviando su documento por POST."""
        self.login_as(self.usuario_operador)

        # Envía maliciosamente en el formulario el documento del administrador u otro usuario
        post_data = {
            "documento": self.usuario_auxiliar.documento,
            "ficha": "2558901",
            "herramienta[]": [self.herramienta_disponible.pk],
            "cantidad[]": [1],
        }
        self.client.post(reverse("usuario_solicitar_prestamo"), data=post_data)

        # El nuevo préstamo debe pertenecer obligatoriamente al usuario autenticado (operador), no al auxiliar
        nuevo_prestamo = Prestamo.objects.latest("codigo_prestamo")
        self.assertEqual(nuevo_prestamo.documento, self.usuario_operador)
        self.assertNotEqual(nuevo_prestamo.documento, self.usuario_auxiliar)

    def test_seguridad_usuario_no_autenticado_redirige_a_login(self):
        """[Seguridad RBAC] Usuario anónimo que intente acceder a endpoints protegidos debe ser enviado al login."""
        self.logout()

        # Intentar acceder a lista admin
        resp1 = self.client.get(reverse("prestamo"))
        self.assertRedirects(resp1, reverse("login"))

        # Intentar acceder a portal de usuario
        resp2 = self.client.get(reverse("prestamo_usuario"))
        self.assertRedirects(resp2, reverse("login"))

        # Intentar aprobar préstamo
        resp3 = self.client.post(reverse("aprobar_prestamo"), {"pk": 1})
        self.assertRedirects(resp3, reverse("login"))

    def test_seguridad_usuario_estandar_no_puede_aprobar_ni_devolver(self):
        """[Seguridad RBAC] Usuario regular con rol 'Usuario' no puede ejecutar acciones de administrador."""
        prestamo = Prestamo.objects.create(
            documento=self.usuario_operador,
            estado=EstadoPrestamo.PENDIENTE,
        )

        self.login_as(self.usuario_operador)

        # Intento de aprobar
        resp_aprobar = self.client.post(reverse("aprobar_prestamo"), {"pk": prestamo.pk})
        self.assertRedirects(resp_aprobar, reverse("pagina_principal"))

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, EstadoPrestamo.PENDIENTE)

        # Intento de devolver
        resp_devolver = self.client.post(reverse("devolver_prestamo"), {"pk": prestamo.pk})
        self.assertRedirects(resp_devolver, reverse("pagina_principal"))
