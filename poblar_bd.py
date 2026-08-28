import os
import django
from django.utils import timezone
from datetime import timedelta

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuario.models import Usuario
from almacen.models import Almacen, Estante
from herramienta.models import CategoriaHerramienta, Herramienta, Traslado, DetalleTraslado
from prestamo.models import Prestamo, DetallePrestamo, DevolucionHerramienta
from django.contrib.auth.hashers import make_password

def poblar():
    print("Iniciando población de la base de datos...")

    # 1. Borrar datos existentes (opcional pero recomendado para empezar limpio)
    print("Borrando datos antiguos...")
    DevolucionHerramienta.objects.all().delete()
    DetallePrestamo.objects.all().delete()
    Prestamo.objects.all().delete()
    DetalleTraslado.objects.all().delete()
    Traslado.objects.all().delete()
    Herramienta.objects.all().delete()
    CategoriaHerramienta.objects.all().delete()
    Estante.objects.all().delete()
    Almacen.objects.all().delete()
    Usuario.objects.all().delete()

    # 2. Crear Usuarios
    print("Creando usuarios...")
    admin_user = Usuario.objects.create(
        documento='0000000000',
        tipo_documento='CC',
        primer_nombre='Admin',
        primer_apellido='Sistema',
        correo_personal='admin@sistema.com',
        password=make_password('@dmin123'),
        rol='Administrador'
    )
    
    normal_user = Usuario.objects.create(
        documento='987654321',
        tipo_documento='CC',
        primer_nombre='Juan',
        primer_apellido='Perez',
        correo_personal='juan@sistema.com',
        password=make_password('usuario123'),
        rol='Usuario'
    )

    # 3. Crear Almacenes y Estantes
    print("Creando almacenes y estantes...")
    almacen_principal = Almacen.objects.create(nombre="Almacén Principal", ubicacion="Sede Norte")
    almacen_secundario = Almacen.objects.create(nombre="Almacén Secundario", ubicacion="Sede Sur")

    estante_1 = Estante.objects.create(codigo="A1", codigo_almacen=almacen_principal)
    estante_2 = Estante.objects.create(codigo="B1", codigo_almacen=almacen_principal)
    estante_3 = Estante.objects.create(codigo="C1", codigo_almacen=almacen_secundario)

    # 4. Crear Categorías
    print("Creando categorías...")
    cat_electricas = CategoriaHerramienta.objects.create(
        tipo_herramienta="Eléctrica",
        nombre_categoria="Herramientas Eléctricas",
        descripcion="Herramientas que requieren energía eléctrica"
    )
    cat_manuales = CategoriaHerramienta.objects.create(
        tipo_herramienta="Manual",
        nombre_categoria="Herramientas Manuales",
        descripcion="Herramientas que no requieren energía"
    )

    # 5. Crear Herramientas
    print("Creando herramientas...")
    taladro = Herramienta.objects.create(
        codigo_sku="SKU-TAL-01",
        nombre_herramienta="Taladro Percutor",
        descripcion="Taladro industrial de 800W",
        disponibilidad="10",
        fecha_ingreso=timezone.now().date(),
        codigo_categoria=cat_electricas,
        estado="Bueno"
    )
    
    martillo = Herramienta.objects.create(
        codigo_sku="SKU-MAR-01",
        nombre_herramienta="Martillo de Carpintero",
        descripcion="Martillo con mango de goma",
        disponibilidad="20",
        fecha_ingreso=timezone.now().date(),
        codigo_categoria=cat_manuales,
        estado="Bueno"
    )

    destornillador = Herramienta.objects.create(
        codigo_sku="SKU-DES-01",
        nombre_herramienta="Juego de Destornilladores",
        descripcion="Set de 10 piezas",
        disponibilidad="15",
        fecha_ingreso=timezone.now().date(),
        codigo_categoria=cat_manuales,
        estado="Bueno"
    )

    # 6. Crear Traslados
    print("Creando traslados...")
    traslado_1 = Traslado.objects.create(
        fecha_movimiento=timezone.now().date(),
        tipo_movimiento="Ingreso",
        num_estante_origen=estante_1.num_estante,
        observaciones="Ingreso inicial"
    )
    
    DetalleTraslado.objects.create(
        codigo_traslado=traslado_1,
        codigo_herramienta=taladro,
        cantidad=5,
        observaciones="Perfecto estado"
    )

    # 7. Crear Préstamos (y detalles y devoluciones)
    print("Creando préstamos...")
    prestamo_1 = Prestamo.objects.create(
        documento=normal_user.documento,
        ficha="2345678",
        fecha=timezone.now().date(),
        estado="ENTREGADO",
        observaciones="Préstamo para práctica de carpintería"
    )
    
    # Prestar 2 martillos
    DetallePrestamo.objects.create(
        prestamo=prestamo_1,
        herramienta=martillo,
        cantidad=2,
        observaciones="Entregados en buen estado"
    )
    # Actualizar stock
    martillo.stock_disponible = int(martillo.stock_disponible) - 2
    martillo.save()
    
    print("¡Base de datos poblada con éxito!")
    print("\n--- Credenciales de acceso ---")
    print("Administrador:")
    print(" - Documento: 0000000000")
    print(" - Contraseña: @dmin123")
    print("Usuario Normal:")
    print(" - Documento: 987654321")
    print(" - Contraseña: usuario123")
    print("------------------------------")

if __name__ == '__main__':
    poblar()
