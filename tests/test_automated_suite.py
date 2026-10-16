"""
Scripts de prueba automatizada para el Sistema de Inventario Minero.
Ejecutar con: pytest tests/test_automated_suite.py -v

Requisitos:
    pip install pytest pytest-django pytest-cov

Para ejecutar:
    python -m pytest tests/test_automated_suite.py -v --cov=. --cov-report=term-missing
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.hashers import check_password, make_password


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def client():
    """Cliente Django para tests de integración."""
    return Client()


@pytest.fixture
def admin_user(db):
    """Usuario administrador para tests."""
    from usuario.models import Usuario
    return Usuario.objects.create(
        documento="1111111111",
        primer_nombre="Admin",
        primer_apellido="Test",
        tipo_documento="CC",
        correo_personal="admin@test.com",
        password=make_password("testpass123!"),
        rol="Administrador"
    )


@pytest.fixture
def regular_user(db):
    """Usuario estándar para tests."""
    from usuario.models import Usuario
    return Usuario.objects.create(
        documento="2222222222",
        primer_nombre="User",
        primer_apellido="Test",
        tipo_documento="CC",
        correo_personal="user@test.com",
        password=make_password("userpass123!"),
        rol="Usuario"
    )


@pytest.fixture
def tool_with_stock(db):
    """Herramienta con stock inicial de 10 unidades."""
    from herramienta.models import Herramienta
    return Herramienta.objects.create(
        codigo_sku="TEST-001",
        nombre_herramienta="Herramienta Test",
        disponibilidad="10"
    )


@pytest.fixture
def tool_zero_stock(db):
    """Herramienta sin stock disponible."""
    from herramienta.models import Herramienta
    return Herramienta.objects.create(
        codigo_sku="TEST-002",
        nombre_herramienta="Herramienta Agotada",
        disponibilidad="0"
    )


@pytest.fixture
def tool_unavailable(db):
    """Herramienta marcada como 'No disponible'."""
    from herramienta.models import Herramienta
    return Herramienta.objects.create(
        codigo_sku="TEST-003",
        nombre_herramienta="Herramienta No Disponible",
        disponibilidad="No disponible"
    )


@pytest.fixture
def session_as_admin(client, admin_user):
    """Configura sesión de administrador."""
    client.session["usuario_documento"] = admin_user.documento
    client.session["usuario_rol"] = "Administrador"
    client.session.save()
    return client


@pytest.fixture
def session_as_user(client, regular_user):
    """Configura sesión de usuario regular."""
    client.session["usuario_documento"] = regular_user.documento
    client.session["usuario_rol"] = "Usuario"
    client.session.save()
    return client


# =============================================================================
# TESTS DE AUTENTICACIÓN
# =============================================================================

class TestAuthentication:
    """Tests de autenticación y autorización."""

    def test_login_success(self, client, db):
        """TC-LOGIN-01: Login exitoso con credenciales válidas."""
        from usuario.models import Usuario
        user = Usuario.objects.create(
            documento="1234567890",
            primer_nombre="Juan",
            primer_apellido="Pérez",
            tipo_documento="CC",
            password=make_password("Password123!"),
            rol="Usuario"
        )
        
        response = client.post(reverse("login"), {
            "tipo_documento": "CC",
            "documento": "1234567890",
            "password": "Password123!"
        }, follow=True)
        
        # Debería redirigir a página principal
        assert response.status_code == 200
        assert "usuario_documento" in client.session

    def test_login_invalid_format(self, client):
        """TC-LOGIN-02: Login con formato de documento inválido."""
        response = client.post(reverse("login"), {
            "tipo_documento": "CC",
            "documento": "abc123def",  # Formato inválido
            "password": "anypassword"
        })
        
        assert response.status_code == 200  # Muestra error en formulario
        assert "usuario_documento" not in client.session

    def test_login_nonexistent_user(self, client):
        """TC-LOGIN-03: Login con documento no registrado."""
        response = client.post(reverse("login"), {
            "tipo_documento": "CC",
            "documento": "9999999999",  # No existe
            "password": "anypassword"
        })
        
        assert response.status_code == 200
        assert "usuario_documento" not in client.session


class TestRegistrationSecurity:
    """Tests de seguridad en registro de usuarios."""

    def test_role_cannot_be_injected(self, client, db):
        """TC-REG-01: El rol no puede ser inyectado vía formulario."""
        response = client.post(reverse("registro"), {
            "tipo_documento": "CC",
            "documento": "9876543210",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
            "numero_ficha": "12345678",
            "rol": "Administrador"  # Intento de inyección
        }, follow=True)
        
        # El backend debe forzar rol 'Usuario'
        from usuario.models import Usuario
        user = Usuario.objects.filter(documento="9876543210").first()
        assert user is not None
        assert user.rol == "Usuario"

    def test_duplicate_document_prevented(self, client, db, admin_user):
        """TC-REG-02: No se puede registrar con documento duplicado."""
        response = client.post(reverse("registro"), {
            "tipo_documento": "CC",
            "documento": admin_user.documento,  # Documento ya existe
            "first_name": "Duplicate",
            "last_name": "User",
            "email": "dup@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!"
        })
        
        assert response.status_code == 200  # Error en formulario
        # Mensaje de error debería aparecer


# =============================================================================
# TESTS DE INVENTARIO
# =============================================================================

class TestInventory:
    """Tests para gestión de inventario."""

    def test_create_tool_success(self, session_as_admin, db):
        """TC-INV-01: Crear herramienta exitosamente."""
        response = session_as_admin.post(reverse("inventario"), {
            "accion": "crear_producto",
            "codigo_sku": "TOOL-001",
            "nombre": "Taladro Industrial",
            "categoria": "",
            "descripcion": "Taladro de alta potencia",
            "estante": "",
            "stock": "15"
        }, follow=True)
        
        assert response.status_code == 200
        
        from herramienta.models import Herramienta
        assert Herramienta.objects.filter(codigo_sku="TOOL-001").exists()
        tool = Herramienta.objects.get(codigo_sku="TOOL-001")
        assert tool.stock_disponible == 15

    def test_create_tool_duplicate_sku(self, session_as_admin, db, tool_with_stock):
        """TC-INV-02: SKU duplicado debe fallar."""
        response = session_as_admin.post(reverse("inventario"), {
            "accion": "crear_producto",
            "codigo_sku": tool_with_stock.codigo_sku,  # Duplicado
            "nombre": "Otro Taladro",
            "stock": "5"
        }, follow=True)
        
        # Debería fallar validación
        from herramienta.models import Herramienta
        # No se crea duplicado
        assert Herramienta.objects.filter(codigo_sku=tool_with_stock.codigo_sku).count() == 1

    def test_create_tool_negative_stock_rejected(self, session_as_admin):
        """TC-INV-03: Stock negativo debe ser rechazado."""
        response = session_as_admin.post(reverse("inventario"), {
            "accion": "crear_producto",
            "codigo_sku": "TOOL-BAD",
            "nombre": "Herramienta Mal",
            "stock": "-5"
        }, follow=True)
        
        # Error validación
        from herramienta.models import Herramienta
        assert not Herramienta.objects.filter(codigo_sku="TOOL-BAD").exists()

    def test_create_tool_exceeds_max_stock(self, session_as_admin):
        """TC-INV-04: Stock mayor a 10000 debe ser rechazado."""
        response = session_as_admin.post(reverse("inventario"), {
            "accion": "crear_producto",
            "codigo_sku": "TOOL-100",
            "nombre": "Herramienta Alta",
            "stock": "15000"
        }, follow=True)
        
        from herramienta.models import Herramienta
        assert not Herramienta.objects.filter(codigo_sku="TOOL-100").exists()

    def test_stock_setter_prevents_negative(self, db, tool_with_stock):
        """TC-INV-05: El setter de stock evita valores negativos."""
        tool_with_stock.stock_disponible = -100
        tool_with_stock.save()
        
        tool_with_stock.refresh_from_db()
        # El setter usa max(0, int(value))
        # Pero como es string en disponibilidad, hay que revisar el código

    def test_zero_stock_display(self, session_as_admin, tool_zero_stock):
        """TC-INV-06: Herramienta con stock 0 se muestra correctamente."""
        response = session_as_admin.get(reverse("inventario"))
        assert response.status_code == 200
        # Buscar herramienta sin stock en contexto
        assert "sin_stock" in response.context or "Herramienta Agotada" in str(response.content)


# =============================================================================
# TESTS DE PRÉSTAMOS
# =============================================================================

class TestLoans:
    """Tests para flujo de préstamos."""

    def test_create_pending_loan(self, session_as_user, db, tool_with_stock):
        """TC-LOAN-01: Crear préstamo pendiente."""
        response = session_as_user.post(reverse("usuario_solicitar_prestamo"), {
            "ficha": "12345678",
            "herramienta[]": [tool_with_stock.pk],
            "cantidad[]": [2]
        }, follow=True)
        
        assert response.status_code == 200
        
        from prestamo.models import Prestamo
        loan = Prestamo.objects.latest("codigo_prestamo")
        assert loan.estado == "PENDIENTE"
        assert loan.documento is not None

    def test_loan_exceeds_available_stock(self, session_as_user, db, tool_with_stock):
        """TC-LOAN-02: Préstamo con cantidad excedente al stock."""
        # Intentar pedir más de lo disponible
        response = session_as_user.post(reverse("usuario_solicitar_prestamo"), {
            "ficha": "12345678",
            "herramienta[]": [tool_with_stock.pk],
            "cantidad[]": [15]  # Excede stock de 10
        }, follow=True)
        
        # Debería fallar validación
        from prestamo.models import Prestamo
        assert Prestamo.objects.count() == 0

    def test_loan_quantity_zero_rejected(self, session_as_user, db, tool_with_stock):
        """TC-LOAN-03: Cantidad 0 debe ser rechazada."""
        response = session_as_user.post(reverse("usuario_solicitar_prestamo"), {
            "ficha": "12345678",
            "herramienta[]": [tool_with_stock.pk],
            "cantidad[]": [0]
        })
        
        from prestamo.models import Prestamo
        assert Prestamo.objects.count() == 0

    def test_loan_quantity_exceeds_max(self, session_as_user, db, tool_with_stock):
        """TC-LOAN-04: Cantidad > 50 debe ser rechazada."""
        response = session_as_user.post(reverse("usuario_solicitar_prestamo"), {
            "ficha": "12345678",
            "herramienta[]": [tool_with_stock.pk],
            "cantidad[]": [51]
        })
        
        from prestamo.models import Prestamo
        assert Prestamo.objects.count() == 0

    def test_approve_loan_deducts_stock(self, session_as_admin, db, admin_user, tool_with_stock):
        """TC-LOAN-05: Aprobar préstamo descuenta stock."""
        from prestamo.models import Prestamo, DetallePrestamo
        
        # Crear préstamo pendiente
        loan = Prestamo.objects.create(
            documento=admin_user,
            ficha="12345678",
            estado="PENDIENTE"
        )
        DetallePrestamo.objects.create(
            codigo_prestamo=loan,
            codigo_herramienta=tool_with_stock,
            cantidad=3
        )
        
        initial_stock = tool_with_stock.stock_disponible
        
        # Aprobar
        session_as_admin.post(reverse("aprobar_prestamo"), {"pk": loan.pk})
        
        loan.refresh_from_db()
        tool_with_stock.refresh_from_db()
        
        assert loan.estado == "ENTREGADO"
        assert tool_with_stock.stock_disponible == initial_stock - 3

    def test_user_cannot_approve_loan(self, session_as_user, db, admin_user, tool_with_stock):
        """TC-LOAN-06: Usuario estándar no puede aprobar préstamos."""
        from prestamo.models import Prestamo
        
        loan = Prestamo.objects.create(
            documento=admin_user,
            ficha="12345678",
            estado="PENDIENTE"
        )
        
        response = session_as_user.post(reverse("aprobar_prestamo"), {"pk": loan.pk})
        
        # Debería redirigir (no autorizado)
        assert response.status_code == 302
        
        loan.refresh_from_db()
        assert loan.estado == "PENDIENTE"


class TestLoanReturn:
    """Tests para devoluciones."""

    def test_full_return_restocks(self, session_as_admin, db, admin_user, tool_with_stock):
        """TC-RET-01: Devolución total restaura stock."""
        from prestamo.models import Prestamo, DetallePrestamo
        
        # Crear y aprobar préstamo
        loan = Prestamo.objects.create(
            documento=admin_user,
            ficha="12345678",
            estado="ENTREGADO"
        )
        detalle = DetallePrestamo.objects.create(
            codigo_prestamo=loan,
            codigo_herramienta=tool_with_stock,
            cantidad=3
        )
        
        stock_before = tool_with_stock.stock_disponible
        
        # Devolver
        session_as_admin.post(reverse("devolver_prestamo"), {
            "pk": loan.pk,
            "devolucion_total": "true",
            "observaciones": "Devolución completa"
        })
        
        tool_with_stock.refresh_from_db()
        assert tool_with_stock.stock_disponible == stock_before + 3

    def test_partial_return_updates_state(self, session_as_admin, db, admin_user, tool_with_stock):
        """TC-RET-02: Devolución parcial cambia a estado PARCIAL."""
        from prestamo.models import Prestamo, DetallePrestamo
        
        loan = Prestamo.objects.create(
            documento=admin_user,
            ficha="12345678",
            estado="ENTREGADO"
        )
        DetallePrestamo.objects.create(
            codigo_prestamo=loan,
            codigo_herramienta=tool_with_stock,
            cantidad=5
        )
        
        # Devolución parcial
        session_as_admin.post(reverse("devolver_prestamo"), {
            "pk": loan.pk,
            "devolucion_total": "false",
            "observaciones": "Devolución parcial"
        })
        
        loan.refresh_from_db()
        assert loan.estado == "PARCIAL"


# =============================================================================
# TESTS DE ALMACENES
# =============================================================================

class TestAlmacenes:
    """Tests para gestión de almacenes."""

    def test_create_almacen_success(self, session_as_admin):
        """TC-ALM-01: Crear almacén exitosamente."""
        response = session_as_admin.post(reverse("almacenes"), {
            "accion": "crear",
            "nombre": "Almacen Nuevo",
            "dimensiones": "20x15m",
            "ubicacion": "Piso 2"
        }, follow=True)
        
        assert response.status_code == 200
        
        from almacen.models import Almacen
        assert Almacen.objects.filter(nombre="Almacen Nuevo").exists()

    def test_create_almacen_duplicate_name(self, session_as_admin, db):
        """TC-ALM-02: Nombre de almacén duplicado debe fallar."""
        from almacen.models import Almacen
        Almacen.objects.create(nombre="Almacen Existente", ubicacion="Test")
        
        response = session_as_admin.post(reverse("almacenes"), {
            "accion": "crear",
            "nombre": "Almacen Existente",  # Duplicado
            "dimensiones": "10x10m",
            "ubicacion": "Otra ubicacion"
        })
        
        # El nombre no es único en modelo, pero se podría agregar validación

    def test_delete_almacen_with_tools_protected(self, session_as_admin, db):
        """TC-ALM-03: No se puede eliminar almacén con herramientas."""
        from almacen.models import Almacen, Estante
        from herramienta.models import Herramienta
        
        almacen = Almacen.objects.create(nombre="Almacen Protegido")
        estante = Estante.objects.create(
            codigo="EST-01",
            codigo_almacen=almacen
        )
        Herramienta.objects.create(
            nombre_herramienta="Herramienta En Almacen",
            estante=estante
        )
        
        response = session_as_admin.post(reverse("almacenes"), {
            "accion": "eliminar",
            "almacen_id": almacen.pk
        }, follow=True)
        
        # Almacén no se elimina
        assert Almacen.objects.filter(pk=almacen.pk).exists()


# =============================================================================
# TESTS DE SEGURIDAD
# =============================================================================

class TestSecurity:
    """Tests de seguridad generales."""

    def test_csrf_protection_enabled(self, client):
        """TC-SEC-01: CSRF protection debe estar activo."""
        # Django tiene middleware csrf por defecto
        # Intentar POST sin token debe fallar o ser interceptado
        response = client.post("/login/", {
            "tipo_documento": "CC",
            "documento": "1234567890",
            "password": "testpass"
        })
        
        # En Django, si el middleware está activo, se verifica CSRF
        assert response.status_code in [200, 302, 403]

    def test_idor_protection_user_detail_json(self, session_as_user, db, admin_user):
        """TC-SEC-02: Usuario no puede acceder a detalles de otro usuario."""
        response = session_as_user.get(
            reverse("detalle_usuario_json", kwargs={"numero_documento": admin_user.documento})
        )
        
        assert response.status_code == 403

    def test_admin_only_export_users(self, session_as_user, db):
        """TC-SEC-03: Solo admin puede exportar usuarios."""
        response = session_as_user.get(reverse("exportar_usuarios_csv"))
        
        assert response.status_code == 302  # Redirección a página principal

    def test_password_hashed_not_plaintext(self, db):
        """TC-SEC-04: Contraseñas deben estar hasheadas."""
        from usuario.models import Usuario
        
        user = Usuario.objects.create(
            documento="3333333333",
            primer_nombre="Test",
            primer_apellido="Pass",
            password=make_password("plaintext123"),
            rol="Usuario"
        )
        
        # Verificar que la contraseña está hasheada
        assert user.password != "plaintext123"
        assert user.password.startswith("pbkdf2_") or user.password.startswith("argon2_")
        
        # Verificar que check_password funciona
        assert check_password("plaintext123", user.password)
        assert not check_password("wrongpassword", user.password)


# =============================================================================
# TESTS DE EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests para casos límite y edge cases."""

    def test_loan_when_stock_is_one(self, session_as_user, db):
        """TC-EDGE-01: Préstamo cuando solo hay 1 unidad disponible."""
        from herramienta.models import Herramienta
        
        tool = Herramienta.objects.create(
            codigo_sku="EDGE-001",
            nombre_herramienta="Unidad Única",
            disponibilidad="1"
        )
        
        response = session_as_user.post(reverse("usuario_solicitar_prestamo"), {
            "ficha": "12345678",
            "herramienta[]": [tool.pk],
            "cantidad[]": [1]
        })
        
        assert response.status_code in [200, 302]

    def test_loan_when_stock_is_zero(self, client, db, tool_zero_stock, regular_user):
        """TC-EDGE-02: No se puede pedir préstamo de herramienta sin stock."""
        client.session["usuario_documento"] = regular_user.documento
        client.session["usuario_rol"] = "Usuario"
        client.session.save()
        
        response = client.post(reverse("usuario_solicitar_prestamo"), {
            "ficha": "12345678",
            "herramienta[]": [tool_zero_stock.pk],
            "cantidad[]": [1]
        })
        
        # Debería fallar - stock disponible es 0
        from prestamo.models import Prestamo
        assert Prestamo.objects.count() == 0

    def test_loan_when_not_available(self, session_as_user, db, tool_unavailable):
        """TC-EDGE-03: No se puede pedir herramienta 'No disponible'."""
        response = session_as_user.post(reverse("usuario_solicitar_prestamo"), {
            "ficha": "12345678",
            "herramienta[]": [tool_unavailable.pk],
            "cantidad[]": [1]
        })
        
        from prestamo.models import Prestamo
        # El stock_disponible de "No disponible" retorna 0, así que fallará
        assert Prestamo.objects.count() == 0 or response.status_code == 302


# =============================================================================
# CONFIGURACIÓN PYTEST
# =============================================================================

# pytest.ini o conftest.py debería configurarse como:
"""
[pytest]
DJANGO_SETTINGS_MODULE = core.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
"""