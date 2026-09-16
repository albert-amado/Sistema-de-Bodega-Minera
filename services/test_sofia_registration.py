import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.test import Client
from django.conf import settings
from usuario.models import Usuario

print("=== INICIANDO PRUEBAS DE VERIFICACIÓN SOFIAPLUS EN REGISTRO ===")

client = Client()

# TEST 1: Endpoint de verificación de documento para aprendiz existente en SofiaPlus
print("\n--- Test 1: Verificación exitosa en SofiaPlus (simulado) ---")
res = client.get('/api/aprendices/verificar-documento/?tipo_documento=CC&documento=1098765432')
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
data = res.json()
assert data['success'] is True
assert data['verificado'] is True
assert "Carlos" in data['aprendiz']['nombre_completo']
assert data['aprendiz']['numero_ficha'] == "2758369"
print(f"[OK] Documento 1098765432 verificado: {data['aprendiz']['nombre_completo']} | Ficha: {data['aprendiz']['numero_ficha']}")

# TEST 2: Duplicado en base de datos local
print("\n--- Test 2: Validación de no duplicidad de documento ---")
# Creamos un usuario de prueba en la BD
Usuario.objects.filter(documento='1099999999').delete()
u_existente = Usuario.objects.create(
    documento='1099999999',
    primer_nombre='Prueba',
    primer_apellido='Existente',
    correo_personal='existente@sena.edu.co',
    tipo_documento='CC'
)
res_dup = client.get('/api/aprendices/verificar-documento/?tipo_documento=CC&documento=1099999999')
assert res_dup.status_code == 409, f"Expected 409 Conflict, got {res_dup.status_code}"
data_dup = res_dup.json()
assert data_dup['already_registered'] is True
print(f"[OK] Duplicado detectado y bloqueado con 409: {data_dup['error']}")
u_existente.delete()

# TEST 3: Documento no encontrado en SofiaPlus (con ALLOW_MANUAL_REGISTRATION = False)
print("\n--- Test 3: Documento no encontrado con ALLOW_MANUAL_REGISTRATION=False ---")
res_nf = client.get('/api/aprendices/verificar-documento/?tipo_documento=CC&documento=8888888888')
assert res_nf.status_code == 404, f"Expected 404, got {res_nf.status_code}"
data_nf = res_nf.json()
assert data_nf['not_found'] is True
assert data_nf['allow_manual'] is False
print(f"[OK] Documento inexistente rechazado con 404: {data_nf['error']}")

# TEST 4: Flujo completo de registro en el formulario POST
print("\n--- Test 4: Creación de cuenta con verificación automática de SofiaPlus ---")
Usuario.objects.filter(documento='1012345678').delete()

post_data = {
    'tipo_documento': 'CC',
    'documento': '1012345678',
    'first_name': 'OtroNombreFalso', # Debe ser sobreescrito por SofiaPlus
    'last_name': 'OtroApellidoFalso',
    'email': 'laura.sanchez.test@misena.edu.co',
    'numero_ficha': '999999',        # Debe ser sobreescrito por SofiaPlus
    'nombre_programa': 'Cualquiera', # Debe ser sobreescrito por SofiaPlus
    'password1': 'ClaveSegura123!',
    'password2': 'ClaveSegura123!',
}

res_post = client.post('/registro/', post_data, follow=True)
# Verificar que el usuario fue creado en la base de datos
nuevo_u = Usuario.objects.filter(documento='1012345678').first()
assert nuevo_u is not None, "El usuario no fue creado en la base de datos"
assert nuevo_u.verificado_sofia_plus is True, f"verificado_sofia_plus debió ser True, pero fue {nuevo_u.verificado_sofia_plus}"
assert nuevo_u.fecha_verificacion is not None, "fecha_verificacion debió tener timestamp"
assert nuevo_u.primer_nombre == "Laura", f"Nombre debió ser Laura de SofiaPlus, pero fue {nuevo_u.primer_nombre}"
assert nuevo_u.ficha == "2827435", f"Ficha debió ser 2827435 de SofiaPlus, pero fue {nuevo_u.ficha}"
print(f"[OK] Usuario registrado en BD:")
print(f"     - Documento: {nuevo_u.documento}")
print(f"     - Nombre oficial SofiaPlus: {nuevo_u.nombre_completo}")
print(f"     - Ficha oficial: {nuevo_u.ficha}")
print(f"     - Programa oficial: {nuevo_u.programa}")
print(f"     - verificado_sofia_plus: {nuevo_u.verificado_sofia_plus}")
print(f"     - fecha_verificacion: {nuevo_u.fecha_verificacion}")

# Limpieza
nuevo_u.delete()

print("\n=======================================================")
print("TODAS LAS PRUEBAS DE REGISTRO SOFIAPLUS PASARON CON ÉXITO")
print("=======================================================")
