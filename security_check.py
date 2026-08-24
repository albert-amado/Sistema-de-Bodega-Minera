import os
import sys
import django

# Asegurar codificación utf-8 en consola
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Inicializar configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from prestamo.models import Herramienta, Prestamo, DetallePrestamo, DevolucionHerramienta
from prestamo.forms import PrestamoForm, DetallePrestamoForm, HerramientaForm


def run_security_audit():
    print("=" * 65)
    print("  AUDITORIA DE SEGURIDAD Y RESISTENCIA DEL BACKEND (DJANGO)")
    print("=" * 65)
    print()

    total_checks = 0
    passed_checks = 0

    # ----------------------------------------------------
    # 1. VERIFICACION DE CONFIGURACION DE SEGURIDAD (SETTINGS)
    # ----------------------------------------------------
    print("[1/6] Auditando Configuración Global (core/settings.py)...")
    
    total_checks += 1
    if settings.DEBUG:
        print("  [!] NOTA: DEBUG está activado (DEBUG=True). En producción debe ser False.")
    else:
        print("  [OK] DEBUG está desactivado.")
        passed_checks += 1

    total_checks += 1
    if 'django-insecure' in settings.SECRET_KEY:
        print("  [!] ADVERTENCIA: Usando SECRET_KEY de desarrollo insegura.")
    else:
        print("  [OK] SECRET_KEY personalizada detectada.")
        passed_checks += 1

    print()

    # ----------------------------------------------------
    # 2. AUDITORÍA DIRECTA A NIVEL DE MODELO (models.py)
    # ----------------------------------------------------
    print("[2/6] Auditando Validación Nivel Modelo (models.py)...")
    
    # Test 2.1: Inyección de documento no numérico en Modelo directamente
    total_checks += 1
    p_invalid = Prestamo(documento="abc' OR 1=1", ficha="2558190")
    try:
        p_invalid.full_clean()
        print("  [ALERTA] VULNERABILIDAD: El Modelo permitió documentos con letras o caracteres maliciosos.")
    except ValidationError:
        print("  [OK] BLOQUEADO: models.py rechazó el documento inválido vía full_clean().")
        passed_checks += 1

    # Test 2.2: Stock insuficiente directo en Modelo
    total_checks += 1
    h_temp, _ = Herramienta.objects.get_or_create(codigo="SEC-MOD-01", defaults={'nombre': 'Taladro', 'stock_disponible': 2})
    p_temp = Prestamo.objects.create(documento="12345678", ficha="2558190")
    d_invalid = DetallePrestamo(prestamo=p_temp, herramienta=h_temp, cantidad=50)
    
    try:
        d_invalid.full_clean()
        print("  [ALERTA] VULNERABILIDAD: models.py permitió crear un detalle con exceso de stock.")
    except ValidationError:
        print("  [OK] BLOQUEADO: models.py detectó stock insuficiente directo en el modelo.")
        passed_checks += 1

    print()

    # ----------------------------------------------------
    # 3. AUDITORÍA DE CLAVES ÚNICAS Y DUPLICADOS EN MODELO
    # ----------------------------------------------------
    print("[3/6] Auditando Unicidad de Códigos de Herramientas...")
    total_checks += 1
    try:
        Herramienta.objects.create(codigo="SEC-MOD-01", nombre="Duplicado Test", stock_disponible=1)
        print("  [ALERTA] VULNERABILIDAD: El modelo aceptó dos herramientas con el mismo código.")
    except Exception:
        print("  [OK] BLOQUEADO: La base de datos rechazó códigos duplicados de herramienta.")
        passed_checks += 1

    print()

    # ----------------------------------------------------
    # 4. AUDITORÍA DE BORRADO EN CASCADA (PROTECT DELETE)
    # ----------------------------------------------------
    print("[4/6] Auditando Protección contra Borrado de Herramientas Prestadas...")
    total_checks += 1
    d_temp = DetallePrestamo.objects.create(prestamo=p_temp, herramienta=h_temp, cantidad=1)
    
    try:
        h_temp.delete()
        print("  [ALERTA] VULNERABILIDAD: Se eliminó una herramienta asociada a un préstamo activo.")
    except ProtectedError:
        print("  [OK] BLOQUEADO: models.py impidió borrar una herramienta prestada (models.PROTECT).")
        passed_checks += 1

    # Limpieza
    d_temp.delete()
    p_temp.delete()
    h_temp.delete()

    print()

    # ----------------------------------------------------
    # 5. AUDITORÍA DE INYECCIÓN EN FORMULARIOS
    # ----------------------------------------------------
    print("[5/6] Auditando Resistencia a Inyección SQL y XSS en Formularios...")
    total_checks += 1
    sql_payload = "102030' OR '1'='1"

    p_form = PrestamoForm(data={'documento': sql_payload, 'ficha': '2558190', 'fecha': '2026-08-24'})

    if not p_form.is_valid():
        print("  [OK] BLOQUEADO: El formulario impidió la inyección SQL en el documento.")
        passed_checks += 1
    else:
        print("  [ALERTA] VULNERABILIDAD: El formulario aceptó caracteres de inyección SQL.")

    print()

    # ----------------------------------------------------
    # 6. AUDITORÍA DE CANTIDADES NEGATIVAS
    # ----------------------------------------------------
    print("[6/6] Auditando Inyección de Cantidades Negativas...")
    total_checks += 1
    h_neg, _ = Herramienta.objects.get_or_create(codigo="SEC-NEG-01", defaults={'nombre': 'Test', 'stock_disponible': 5})
    d_neg_form = DetallePrestamoForm(data={'herramienta': h_neg.id, 'cantidad': -10})

    if not d_neg_form.is_valid():
        print("  [OK] BLOQUEADO: El sistema rechazó cantidades negativas.")
        passed_checks += 1
    else:
        print("  [ALERTA] VULNERABILIDAD: El sistema aceptó cantidades negativas.")

    h_neg.delete()

    print()
    print("=" * 65)
    print(f"  RESUMEN DE AUDITORIA: {passed_checks}/{total_checks} Pruebas de seguridad superadas.")
    print("=" * 65)


if __name__ == '__main__':
    run_security_audit()
