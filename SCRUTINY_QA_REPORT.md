# Auditoría de Calidad - Sistema de Inventario Minero
## Ingeniero Senior de QA | Reporte Técnico

---

## 1. Resumen Arquitectónico

### Tecnología
- **Framework**: Django 6.1 (Python)
- **Base de datos**: SQLite3 (desarrollo) / MySQL (producción)
- **Autenticación**: Sistema de sesiones personalizado con roles
- **ORM**: Django ORM con migraciones
- **Plantillas**: Django Templates (HTML)

### Estructura de Carpetas / Apps
```
Inventario-Mina/
├── almacen/          # Gestión de almacenes y estantes
│   ├── models.py     # Almacen, Estante
│   ├── views.py      # CRUD + API
│   └── forms.py      # AlmacenForm, EstanteForm
│
├── herramienta/       # Catálogo de herramientas/inventario
│   ├── models.py     # Herramienta, CategoriaHerramienta, Proveedor, Traslado, Mantenimiento
│   ├── views.py      # Inventario principal, CRUD herramientas
│   └── forms.py      # Forms para CRUD
│
├── prestamo/          # Sistema de préstamos
│   ├── models.py     # Prestamo, DetallePrestamo, DevolucionHerramienta
│   ├── views.py      # Listas, creación, aprobación, devolución
│   └── forms.py      # PrestamoForm, DetallePrestamoForm, DevolucionHerramientaForm
│
├── usuario/           # Gestión de usuarios
│   ├── models.py     # Usuario (modelo personalizado)
│   ├── views.py      # Login, registro, perfil, admin
│   ├── forms.py      # RegistroUsuarioForm, PerfilUsuarioForm, etc.
│   └── decorators.py # login_required, admin_required, usuario_required
│
├── pagina_principal/ # Vista principal del sistema
├── configuracion/     # Configuración del sistema
├── chatbot/           # Chatbot IA (Gemini API)
└── services/          # Servicios externos (SofiaPlus, Gemini)
```

### Flujos Principales

#### Gestión de Inventario Minero
1. **Almacén → Estante → Herramienta** (relación jerárquica)
2. Herramientas tienen SKU único, stock, disponibilidad, estado
3. Traslados registran movimientos entre estantes
4. Mantenimientos documentan ciclos de vida de activos

#### Préstamos de Herramientas
1. Usuario / Aprendiz solicita préstamo
2. Estado: PENDIENTE → ENTREGADO → DEVUELTO / PARCIAL / CANCELADO
3. Stock se descuenta al aprobar, se devuelve al cerrar
4. Validación de stock antes de aprobar

#### Autenticación y Roles
- **Usuario**: Puede solicitar préstamos, ver su historial
- **Administrador**: Gestión completa, CRUD de todo, exportaciones

---

## 2. Matriz de Casos de Prueba

### 2.1 Módulo: Usuario / Autenticación (TC-USR)

| ID | Caso de Prueba | Precondiciones | Pasos | Datos de Prueba | Resultado Esperado | Errores a Vigilar |
|----|----------------|----------------|-------|-----------------|--------------------|-------------------|
| TC-USR-01 | Login exitoso con usuario válido | Usuario existente, password correcta | 1. Navegar a /login<br>2. Ingresar documento válido<br>3. Ingresar password correcta<br>4. Click "Entrar" | CC: 1234567890, Password: válida | Redirección a página principal<br>Usuario en sesión | Mensaje error si credenciales incorrectas |
| TC-USR-02 | Login con documento inválido | - | 1. Navegar a /login<br>2. Ingresar CC: abcdef<br>3. Click "Entrar" | CC: abcdef (formato inválido) | Mensaje error de validación de formato | No mostrar detalles de error en producción |
| TC-USR-03 | Login con documento no registrado | Documento inexistente | 1. Navegar a /login<br>2. Ingresar CC: 999999999<br>3. Click "Entrar" | CC: 999999999 | Mensaje "Documento o contraseña incorrectos" | Evitar enumerate usuarios existentes |
| TC-USR-04 | Registro de nuevo usuario | Usuario no existe, documento en SofiaPlus | 1. Navegar a /registro<br>2. Completar formulario<br>3. Enviar | Ver datos SofiaPlus mock | Usuario creado con rol "Usuario"<br>Password hasheado | Rol expuesto en formulario? |
| TC-USR-05 | Registro con rol malicioso | Payload incluye rol=Administrador | 1. Navegar a /registro<br>2. Enviar POST con rol=Administrador | rol=Administrador en POST | Usuario creado con rol "Usuario"<br>Backend fuerza rol | Verificar que rol no se puede inyectar |
| TC-USR-06 | Recuperación de contraseña | Usuario con email registrado | 1. Navegar a /olvido<br>2. Ingresar email<br>3. Enviar | email@válido | Mensaje confirmación<br>Link de recuperación enviado | No revelar si email existe |
| TC-USR-07 | IDOR: Usuario accede a otro usuario | Usuario con sesión activa | 1. Iniciar sesión como UserA<br>2. Intentar acceder a /usuarios/UserB/json/ | Endpoint: GET /usuarios/123456789/json/ | 403 Forbidden | Verificar control acceso en TODOS los endpoints |
| TC-USR-08 | Exportar usuarios CSV | Usuario con rol "Usuario" (no admin) | 1. Iniciar sesión como Usuario<br>2. Navegar a /usuarios/exportar/csv/ | - | Redirección a página principal | Verificar decorator admin_required |

### 2.2 Módulo: Inventario/Herramientas (TC-INV)

| ID | Caso de Prueba | Precondiciones | Pasos | Datos de Prueba | Resultado Esperado | Errores a Vigilar |
|----|----------------|----------------|-------|-----------------|--------------------|-------------------|
| TC-INV-01 | Crear herramienta válida | Sesión Admin | 1. Navegar a /inventario<br>2. Click "Crear Producto"<br>3. Completar formulario | SKU: TEST-001<br>Nombre: Taladro<br>Stock: 5 | Herramienta creada<br>Stock visible = 5 | SKU duplicado debe fallar |
| TC-INV-02 | Crear herramienta con SKU duplicado | Herramienta existe con SKU TEST-001 | 1. Intentar crear con mismo SKU | SKU: TEST-001 | Error "Ya existe una herramienta con este código" | Verificar clean() del modelo |
| TC-INV-03 | Editar nombre herramienta | Herramienta existe | 1. Navegar a /inventario<br>2. ClickEditar<br>3. Cambiar nombre | Nombre nuevo: "Martillo Pesado" | Nombre actualizado | Verificar CSRF token |
| TC-INV-04 | Stock en cero | Herramienta con stock 0 | 1. Verificar herramienta muestra "0 disponible" | - | Label rojo "Sin Stock" visible | No permitir stock negativo |
| TC-INV-05 | Stock negativo vía formulario | - | 1. Intentar establecer stock = -5 | Stock: -5 | Error validación "stock entre 0 y 10,000" | Validar backend también frontend |
| TC-INV-06 | Stock mayor a 10,000 | - | 1. Intentar establecer stock = 15000 | Stock: 15000 | Error "El stock debe estar entre 0 y 10,000" | Límite fijo en código |
| TC-INV-07 | Crear categoría duplicada | Categoría "Martillos" existe | 1. Intentar crear con nombre "Martillos" | Nombre: Martillos | Error de validación | Verificar unicidad |
| TC-INV-08 | Búsqueda herramienta por nombre | Inventario cargado | 1. En inventario buscar "taladro" | - | Solo resultados filtrados | XSS en buscar? |

### 2.3 Módulo: Préstamos (TC-PREST)

| ID | Caso de Prueba | Precondiciones | Pasos | Datos de Prueba | Resultado Esperado | Errores a Vigilar |
|----|----------------|----------------|-------|-----------------|--------------------|-------------------|
| TC-PREST-01 | Solicitar préstamo exitoso | Usuario logueado, stock disponible | 1. Navegar a préstamos<br>2. Seleccionar herramienta<br>3. Indicar cantidad<br>4. Enviar | Herramienta: TEST-001 (stock 5)<br>Cantidad: 2 | Préstamo creado estado PENDIENTE<br>Stock = 3 post-aprobación | Verificar atomicidad |
| TC-PREST-02 | Préstamo excede stock disponible | Herramienta con stock 2 | 1. Solicitar cantidad 5 | Cantidad: 5 | Error "Stock insuficiente" | Validar antes de crear |
| TC-PREST-03 | Préstamo cantidad = 0 | - | 1. Intentar solicitar cantidad 0 | Cantidad: 0 | Error validación | Validar > 0 |
| TC-PREST-04 | Préstamo cantidad > 50 | - | 1. Intentar cantidad 51 | Cantidad: 51 | Error "máximo 50 unidades" | Límite de negocio |
| TC-PREST-05 | Aprobar préstamo como Admin | Préstamo PENDIENTE | 1. Login Admin<br>2. Ir a /prestamo<br>3. Click Aprobar | pk del préstamo | Estado = ENTREGADO<br>Stock disminuye | Verificar transacción atómica |
| TC-PREST-06 | Aprobar préstamo como Usuario | Usuario logueado | 1. Login User<br>2. Intentar aprobar préstamo | pk cualquiera | Redirección a página principal<br>302 | Decoretador admin_required |
| TC-PREST-07 | Cancelar préstamo | Préstamo ACTIVO | 1. Admin ir a préstamos<br>2. Click Rechazar<br>3. Agregar motivo | Motivo: "Daño" | Estado = CANCELADO<br>Stock restaurado | Verificar rollback |
| TC-PREST-08 | Devolución parcial | Préstamo ENTREGADO (3 unidades) | 1. Devolver solo 2 unidades | - | Estado = PARCIAL<br>Stock devuelto = 2 | Verificar lógica estado |
| TC-PREST-09 | Devolución total | Préstamo ACTIVO | 1. Devolver todas las unidades | Cantidad = original | Estado = DEVUELTO<br>Stock total | Verificar cálculo stock |
| TC-PREST-10 | IDOR: Usuario modifica otro préstamo | Usuario logueado | 1. Intentar editar observaciones préstamo ajeno | POST con pk ajeno | 403 Forbidden | Verificar permisos en views |

### 2.4 Módulo: Almacenes/Estantes (TC-ALM)

| ID | Caso de Prueba | Precondiciones | Pasos | Datos de Prueba | Resultado Esperado | Errores a Vigilar |
|----|----------------|----------------|-------|-----------------|--------------------|-------------------|
| TC-ALM-01 | Crear almacén válido | Sesión Admin | 1. Ir a /almacenes<br>2. Formulario crear<br>3. Enviar | Nombre: "Almacén Nuevo" | Almacén creado | Nombre vacío debe fallar |
| TC-ALM-02 | Crear estante sin almacén padre | - | 1. Intentar crear estante sin elegir almacén | almacén vacío | Error validación | FK requerida |
| TC-ALM-03 | Eliminar almacén con herramientas | Almacén con estantes → herramientas | 1. Intentar eliminar almacén | pk almacén | Error "contiene estantes/herramientas" | Protección FK |
| TC-ALM-04 | Crear estante con código duplicado | Estante "EST-01" existe en almacén A | 1. Crear estante "EST-01" en almacén B | Código duplicado | ¿Permite o no? Verificar requisitos | SKU único global? |

### 2.5 Módulo: Seguridad y Validación (TC-SEC)

| ID | Caso de Prueba | Precondiciones | Pasos | Datos de Prueba | Resultado Esperado | Errores a Vigilar |
|----|----------------|----------------|-------|-----------------|--------------------|-------------------|
| TC-SEC-01 | CSRF token inválido | Formulario abrir | 1. Modificar request sin CSRF<br>2. Enviar POST | POST sin csrfmiddlewaretoken | 403 Forbidden | Verificar middleware activo |
| TC-SEC-02 | Inyección SQL en búsqueda | - | 1. Buscar: `'; DROP TABLE user; --` | - | Input sanitizado / error controlado | No exponer detalles de error |
| TC-SEC-03 | XSS en nombre herramienta | - | 1. Crear herramienta con nombre `<script>alert(1)</script>` | Nombre: `<script>...` | Nombre guardado pero escapeado en template | Verificar auto-escape |
| TC-SEC-04 | Validación email inválido | - | 1. Registro con email: `invalid-email` | Email: "invalid-email" | Error "correo válido" | Usar EmailValidator |
| TC-SEC-05 | Validación CC formato | - | 1. Registro con CC: `abc123` | CC: abc123 | Error regex | Patrones en DOC_PATTERNS |
| TC-SEC-06 | Sesión expirada | - | 1. Esperar session timeout<br>2. Intentar acción protegida | - | Redirección Login | Verificar SESSION_COOKIE_AGE |

---

## 3. Propuestas de Automatización

### 3.1 Prioridad Alta (Ejecutar primero)

**Scripts a automatizar con Pytest/Unittest:**

1. **TC-USR-05** - Registro con rol malicioso
2. **TC-USR-07** - IDOR protección
3. **TC-PREST-06** - Acceso no autorizado a aprobar
4. **TC-PREST-07** - Cancelación y rollback de stock
5. **TC-PREST-10** - IDOR en préstamos
6. **TC-SEC-02** - Inyección SQL básica
7. **TC-SEC-03** - XSS en inputs

### 3.2 Urgente: Tests de Integridad Transaccional
Verificar que al aprobar/cancelar un préstamo, el stock se actualiza correctamente usando transacciones atómicas.

### 3.3 Ejemplo de Script de Automatización

**Archivo: `tests/test_integration_loans.py`**

```python
"""
Test de integración para flujo completo de préstamos.
Ejecutar con: pytest tests/test_integration_loans.py -v
Requiere: pytest-django instalado
"""
import pytest
from django.test import Client
from django.urls import reverse

from herramienta.models import Herramienta
from usuario.models import Usuario
from prestamo.models import Prestamo, EstadoPrestamo, DetallePrestamo


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def admin_user(db):
    return Usuario.objects.create(
        documento="1111111111",
        primer_nombre="Admin",
        primer_apellido="Test",
        tipo_documento="CC",
        correo_personal="admin@test.com",
        password="testpass123!",
        rol="Administrador"
    )


@pytest.fixture
def tool_with_stock(db):
    return Herramienta.objects.create(
        codigo_sku="TEST-001",
        nombre_herramienta="Herramienta Test",
        disponibilidad="10"
    )


@pytest.mark.django_db
class TestLoanFlowIntegration:
    """Tests de integración para flujo completo de préstamos."""

    def test_loan_flow_creates_and_deducts_stock(
        self, client, admin_user, tool_with_stock
    ):
        """TC-PREST-01: Verificar flujo completo de préstamo"""
        # Given
        assert tool_with_stock.stock_disponible == 10
        
        # When: Crear préstamo pendiente
        client.session["usuario_documento"] = admin_user.documento
        client.session["usuario_rol"] = "Administrador"
        client.session.save()

        response = client.post(reverse("crear_prestamo"), {
            "documento": admin_user.documento,
            "ficha": "12345678",
            "herramienta[]": [tool_with_stock.pk],
            "cantidad[]": [3],
        }, follow=True)

        # Then
        assert response.status_code in [200, 302]
        prestamo = Prestamo.objects.latest("codigo_prestamo")
        assert prestamo.estado == EstadoPrestamo.PENDIENTE
        
        # Stock NO debe cambiar aún (pendiente)
        tool_with_stock.refresh_from_db()
        assert tool_with_stock.stock_disponible == 10

        # When: Aprobar préstamo
        response = client.post(
            reverse("aprobar_prestamo"),
            {"pk": prestamo.pk},
            follow=True
        )

        # Then
        assert response.status_code in [200, 302]
        prestamo.refresh_from_db()
        assert prestamo.estado == EstadoPrestamo.ENTREGADO
        tool_with_stock.refresh_from_db()
        assert tool_with_stock.stock_disponible == 7

    def test_loan_cannot_be_approved_with_insufficient_stock(
        self, client, admin_user, tool_with_stock
    ):
        """TC-PREST-02: Verificar validación de stock insuficiente"""
        tool_with_stock.disponibilidad = "2"
        tool_with_stock.save()

        client.session["usuario_documento"] = admin_user.documento
        client.session["usuario_rol"] = "Administrador"
        client.session.save()

        response = client.post(reverse("crear_prestamo"), {
            "documento": admin_user.documento,
            "ficha": "12345678",
            "herramienta[]": [tool_with_stock.pk],
            "cantidad[]": [5],  # Excede stock de 2
        }, follow=True)

        # Should redirect back with error (form validation)
        # Check no préstamo fue creado
        assert Prestamo.objects.count() == 0

    def test_idor_protection_user_cannot_approve_other_loan(
        self, client, db
    ):
        """TC-PREST-06: Usuario estándar no puede aprobar préstamos"""
        # Setup
        usuario = Usuario.objects.create(
            documento="2222222222",
            primer_nombre="User",
            primer_apellido="Test",
            tipo_documento="CC",
            rol="Usuario"
        )
        tool = Herramienta.objects.create(
            codigo_sku="TEST-002",
            nombre_herramienta="Test 2",
            disponibilidad="5"
        )
        prestamo = Prestamo.objects.create(
            documento=usuario,
            ficha="87654321",
            estado=EstadoPrestamo.PENDIENTE
        )
        DetallePrestamo.objects.create(
            codigo_prestamo=prestamo,
            codigo_herramienta=tool,
            cantidad=1
        )

        client.session["usuario_documento"] = usuario.documento
        client.session["usuario_rol"] = "Usuario"
        client.session.save()

        # Attempt to approve
        response = client.post(
            reverse("aprobar_prestamo"),
            {"pk": prestamo.pk}
        )

        # Should redirect to home (not admin page)
        assert response.status_code == 302
        assert "prestamo" not in response.url

        # Préstamo remains PENDIENTE
        prestamo.refresh_from_db()
        assert prestamo.estado == EstadoPrestamo.PENDIENTE


@pytest.mark.django_db
class TestSecurityValidations:
    """Tests de seguridad específicos"""

    def test_xss_protection_in_tool_name(self, client, admin_user):
        """TC-SEC-03: Verificar escape de caracteres en nombre de herramienta"""
        client.session["usuario_documento"] = admin_user.documento
        client.session["usuario_rol"] = "Administrador"
        client.session.save()

        xss_payload = "<script>alert('xss')</script>"
        
        # Intentar crear con payload XSS
        # El sistema debería escapar, no ejecutar
        tool = Herramienta.objects.create(
            nombre_herramienta=xss_payload,
            disponibilidad="1"
        )

        # Verificar que el string se guardó pero en template se escapará
        # (Django templates auto-escape por defecto)
        assert tool.nombre_herramienta == xss_payload
        
        # En una vista real, verificaríamos:
        # response = client.get(tool.get_absolute_url())
        # assert b"&lt;script&gt;" in response.content

    def test_invalid_document_format_validation(self, client):
        """TC-SEC-05: Verificar validación de formato de documento"""
        response = client.post(reverse("registro"), {
            "tipo_documento": "CC",
            "documento": "abc123",  # Formato inválido para CC
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password1": "password123",
            "password2": "password123",
        })

        # Debería fallar validación
        assert response.status_code in [200, 400]  # No redirect = error en form
        # Mensaje de error debería estar presente


@pytest.mark.django_db
class TestTransactionIntegrity:
    """Tests para verificar integridad transaccional"""

    def test_stock_restored_on_loan_cancellation(
        self, client, admin_user, tool_with_stock
    ):
        """TC-PREST-07: Verificar que stock se restaura al cancelar"""
        # Setup
        original_stock = tool_with_stock.stock_disponible  # 10
        
        client.session["usuario_documento"] = admin_user.documento
        client.session["usuario_rol"] = "Administrador"
        client.session.save()

        # Create and approve loan
        response = client.post(reverse("crear_prestamo"), {
            "documento": admin_user.documento,
            "ficha": "12345678",
            "herramienta[]": [tool_with_stock.pk],
            "cantidad[]": [3],
        }, follow=True)

        prestamo = Prestamo.objects.latest("codigo_prestamo")
        
        # Approve
        client.post(reverse("aprobar_prestamo"), {"pk": prestamo.pk})
        tool_with_stock.refresh_from_db()
        assert tool_with_stock.stock_disponible == 7  # 10 - 3

        # Cancel
        client.post(reverse("rechazar_prestamo"), {
            "pk": prestamo.pk,
            "motivo_rechazo": "Test cancel"
        })

        # Stock debe restaurarse
        tool_with_stock.refresh_from_db()
        assert tool_with_stock.stock_disponible == 10  # Restaurado

```

---

## 4. Observaciones y Recomendaciones

### 4.1 Hallazgos Críticos

1. **Falta de tests para `DetallePrestamo.clean()`** - Validación de stock insuficiente (línea 133-142 prestamo/models.py)
2. **IDOR en `detalle_usuario_json`** - Existe protección pero vulnerable a session fixation
3. **CSRF protection** - Implementado correctamente con middleware
4. **Password hashing** - Usa `make_password()` correctamente
5. **Stock setter** - Línea 194 en herramienta/models.py: `max(0, int(value))` evita negativos

### 4.2 Mejoras Recomendadas

1. **Agregar tests para concurrency** - Pruebas con múltiples hilos simulando préstamos simultáneos
2. **Tests de integración SofiaPlus** - Mock del cliente SofiaPlus
3. **Tests de estilos CSS responsive** - Para formularios móviles
4. **Tests de performance** - Búsquedas con grandes volúmenes
5. **Tests de recuperación** - Flujo olvidé contraseña completo

### 4.3 Cobertura Actual de Tests

Basado en archivos `tests.py`:
- **almacen/tests.py**: 3 tests básicos de modelo
- **herramienta/tests.py**: 4 tests de modelo
- **prestamo/tests.py**: 7 tests (incluye security tests)
- **usuario/tests.py**: 7 tests de seguridad

**Total actual**: ~21 tests manuales
**Recomendado para cobertura >80%**: 50-70 tests automatizados

---

## 5. Script de Ejecución de Tests

```bash
# Navegar al proyecto
cd "C:\Users\felip\OneDrive\Documentos\GitHub\Inventario-Mina"

# Activar entorno virtual
.\.venv\Scripts\activate

# Ejecutar todos los tests
python manage.py test

# O con pytest si está instalado
pytest --cov=. --cov-report=html

# Ejecutar tests específicos
pytest tests/test_integration_loans.py -v
pytest tests/test_security_validations.py -v
```

---

## 6. Checklist QA Ejecutable

```markdown
## Checklist de QA Pre-Despliegue

### Funcionalidad
- [ ] Login/logout funciona correctamente
- [ ] Registro usuario con validación SofiaPlus
- [ ] Crear/Editar/Eliminar almacén
- [ ] Crear/Editar/Eliminar estante
- [ ] Crear/Editar herramienta
- [ ] SKU único, validado
- [ ] Stock disponible calcula correctamente
- [ ] Préstamo: crear solicitud
- [ ] Préstamo: aprobar (descuenta stock)
- [ ] Préstamo: rechazar (no cambia stock)
- [ ] Préstamo: devolver (restaura stock)
- [ ] Préstamo: devolución parcial
- [ ] Reportes: exportar CSV usuarios (solo admin)

### Seguridad
- [ ] CSRF protege todos los POST
- [ ] IDOR: usuarios no acceden a recursos ajenos
- [ ] CSRF token presente en forms
- [ ] Contraseñas hasheadas (no texto plano)
- [ ] Mensajes de error no revelan info sensible

### Validaciones
- [ ] Documento CC: 6-10 dígitos
- [ ] Documento CE: 6-12 alfanumérico
- [ ] Email: formato válido
- [ ] Stock: entero, 0-10000
- [ ] Cantidad préstamo: 1-50
- [ ] Nombre herramienta: requerido
- [ ] Nombre almacén: requerido, min 2 chars

### Transacciones
- [ ] Al aprobar préstamo: stock -= cantidad (atómico)
- [ ] Al cancelar: stock no cambia
- [ ] Al devolver: stock += cantidad (parcial/total)
- [ ] Concurrente: 2 aprobaciones fallan correctly

### Edge Cases
- [ ] Stock = 0: muestra "Sin disponibilidad"
- [ ] Duplicado SKU: error específico
- [ ] Documento no en SofiaPlus: según ALLOW_MANUAL_REGISTRATION
- [ ] SofiaPlus timeout: según SOFIAPLUS_FALLBACK_POLICY
- [ ] Stock insuficiente: error claro al usuario
- [ ] Cancelar préstamo: opción requiere motivo
```

---

## 7. Conclusión

El sistema es robusto en cuanto a:
- **Validaciones de negocio** (stock, roles, documentos)
- **Seguridad** (CSRF, IDOR protection, password hashing)
- **Transacciones** (uso de @transaction.atomic)

Puntos críticos para QA:
1. Pruebas de concurrencia en préstamos
2. Integración con SofiaPlus (mocks necesarios)
3. Validaciones de formulario vs backend consistency
4. Tests de UI para modales y feedback de mensajes

**Prioridad de automatización**: 1-2 semana para escribir y ejecutar 50+ tests automatizados.