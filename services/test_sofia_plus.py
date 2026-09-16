import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from services.sofia_plus_client import (
    SofiaPlusClient,
    get_sofia_plus_client,
    AprendizNotFoundError,
    SofiaPlusInvalidInputError
)
from django.test import Client

print("=== TEST 1: SofiaPlusClient Local Tests ===")
client = get_sofia_plus_client()

# Masking test
assert client.mask_documento("1000000001") == "******0001", "Masking failed"
print("[OK] Masking test passed")

# Input validation test
tipo, doc = client.validar_y_sanitizar("cc", " 1000-000-001 ")
assert tipo == "CC" and doc == "1000000001", f"Sanitization failed: {tipo}, {doc}"
print("[OK] Sanitization test passed")

try:
    client.validar_y_sanitizar("CC", "123")
    assert False, "Should have raised SofiaPlusInvalidInputError for short doc"
except SofiaPlusInvalidInputError:
    print("[OK] Short document rejection passed")

# Local fallback query test
info = client.consultar_aprendiz("CC", "1000000001")
print(f"[OK] Consulta exitosa: {info.nombre_completo} | Ficha: {info.numero_ficha} | Prog: {info.programa_formacion} | Estado: {info.estado_programa}")
assert "Juan" in info.nombre_completo
assert info.numero_ficha == "3319045"

# Cache test
info_cached = client.consultar_aprendiz("CC", "1000000001")
assert "cache" in info_cached.origen_datos, f"Expected cache, got {info_cached.origen_datos}"
print("[OK] Cache en memoria verificado con exito")

# Not found test
try:
    client.consultar_aprendiz("CC", "9999999999")
    assert False, "Should have raised AprendizNotFoundError"
except AprendizNotFoundError as e:
    print("[OK] Aprendiz no encontrado verificado con mensaje amigable:", e.user_friendly_message)

print("\n=== TEST 2: Django View / API Integration Tests ===")
django_client = Client()

# Unauthenticated
res = django_client.get('/aprendices/verificar/')
assert res.status_code == 302, f"Expected 302 redirect for unauthenticated, got {res.status_code}"
print("[OK] Redireccion no autenticado correcta")

# Login as Admin
session = django_client.session
session['usuario_documento'] = '0000000000'
session['usuario_rol'] = 'Administrador'
session['usuario_nombre'] = 'Admin'
session.save()

# View test
res = django_client.get('/aprendices/verificar/')
assert res.status_code == 200, f"Expected 200 for admin view, got {res.status_code}"
print("[OK] Vista HTML carga correctamente con codigo 200")

# API Success test
res_api = django_client.get('/api/aprendices/verificar/?tipo_documento=CC&documento=1000000002')
assert res_api.status_code == 200, f"Expected 200, got {res_api.status_code}"
data = res_api.json()
assert data['success'] is True
assert data['aprendiz']['primer_nombre'] == "Maria"
print(f"[OK] API 200 OK: {data['aprendiz']['nombre_completo']} ({data['aprendiz']['numero_ficha']})")

# API 404 test
res_404 = django_client.get('/api/aprendices/verificar/?tipo_documento=CC&documento=9999999999')
assert res_404.status_code == 404
data_404 = res_404.json()
assert data_404['success'] is False
print("[OK] API 404 OK:", data_404['error'])

# API 400 test
res_400 = django_client.get('/api/aprendices/verificar/?tipo_documento=CC&documento=12')
assert res_400.status_code == 400
data_400 = res_400.json()
assert data_400['success'] is False
print("[OK] API 400 OK:", data_400['error'])

print("\nTODAS LAS PRUEBAS PASARON EXITOSAMENTE.")
