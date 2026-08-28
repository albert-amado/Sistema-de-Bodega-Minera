#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para poblar la base de datos con datos de ejemplo completos.
Cubre todas las 15 tablas del sistema acorde al MER actualizado.
"""

import os
import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal

import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from django.db import transaction
from django.core.management import call_command
from django.contrib.auth.hashers import make_password

# Importar todos los modelos del proyecto
from usuario.models import Usuario
from almacen.models import Almacen, Estante
from herramienta.models import (
    CategoriaHerramienta,
    Proveedor,
    Suministro,
    Herramienta,
    Traslado,
    DetalleTraslado,
    Mantenimiento,
    DetalleMantenimiento,
    BitacoraEstado,
)
from prestamo.models import Prestamo, DetallePrestamo, DevolucionHerramienta


def crear_usuarios():
    """Crear usuario admin y usuarios de prueba con Fichas y Programas válidos."""
    print("\n" + "="*70)
    print(">>> CREANDO USUARIOS")
    print("="*70)
    
    admin_doc = '0000000000'
    admin, created = Usuario.objects.get_or_create(
        documento=admin_doc,
        defaults={
            'tipo_documento': 'CC',
            'primer_nombre': 'Administrador',
            'primer_apellido': 'Principal',
            'correo_personal': 'admin@mineinventory.com',
            'rol': 'Administrador',
            'password': make_password('@dmin123'),
            'telefono': '3000000000',
            'ficha': 'ADMIN-001',
            'programa': 'Administración'
        }
    )
    if not created:
        admin.password = make_password('@dmin123')
        admin.rol = 'Administrador'
        admin.save()
    print(f"[OK] Admin creado: {admin_doc}")

    nombres_usuarios = [
        ('Juan', 'Pérez'), ('María', 'García'), ('Carlos', 'López'), ('Ana', 'Martínez'),
        ('Roberto', 'González'), ('Sofía', 'Rodríguez'), ('Miguel', 'Hernández'),
        ('Isabella', 'Torres'), ('David', 'Ramírez'), ('Laura', 'Cruz'),
        ('Fernando', 'Morales'), ('Catalina', 'Soto'), ('Pablo', 'Gómez'),
    ]
    
    fichas_opciones = ['2758369', '2827435', '2895642', '2910384', '3021948', '3196477']
    programas_opciones = [
        'Análisis y Desarrollo de Software (ADSO)',
        'Sistemas',
        'Electricidad Industrial',
        'Mantenimiento Electromecánico',
        'Supervisión de Labores Mineras',
        'Topografía',
        'Soldadura',
        'Gestión Ambiental'
    ]
    
    usuarios = [admin]
    for idx, (nombre, apellido) in enumerate(nombres_usuarios, 1):
        doc = f'1000000{idx:03d}'
        correo = f"{nombre.lower()}.{apellido.lower()}@sena.edu.co"
        
        usuario, _ = Usuario.objects.get_or_create(
            documento=doc,
            defaults={
                'tipo_documento': 'CC',
                'primer_nombre': nombre,
                'primer_apellido': apellido,
                'correo_personal': correo,
                'rol': 'Usuario',
                'password': make_password('Contra123*'),
                'telefono': f'310000{idx:04d}',
                'ficha': random.choice(fichas_opciones),
                'programa': random.choice(programas_opciones)
            }
        )
        usuarios.append(usuario)
        print(f"[OK] Usuario creado: {doc} - {nombre} {apellido}")
    
    return usuarios


def crear_almacenamiento():
    """Crear almacenes y estantes."""
    print("\n" + "="*70)
    print(">>> CREANDO ALMACENES Y ESTANTES")
    print("="*70)
    
    almacenes_datos = [
        ('Almacén A - Principal', 'Almacén general de herramientas manuales', '20x15m'),
        ('Almacén B - Eléctricos', 'Bodega especializada en herramientas de poder', '15x10m'),
        ('Almacén C - Reactivos y Seguridad', 'Almacén de EPP y equipos químicos', '10x8m')
    ]
    
    almacenes = []
    estantes = []
    for nombre, ubic, dim in almacenes_datos:
        alm = Almacen.objects.create(nombre=nombre, dimensiones=dim, ubicacion=ubic)
        almacenes.append(alm)
        print(f"[OK] Almacén: {nombre}")
        
        for i in range(1, 4):
            codigo_estante = f"EST-{nombre.split(' ')[1]}-{i}"
            est = Estante.objects.create(
                codigo_almacen=alm,
                codigo=codigo_estante,
                dimensiones="2x1m"
            )
            estantes.append(est)
            print(f"  [OK] Estante: {codigo_estante}")
            
    return almacenes, estantes


def crear_categorias():
    """Crear categorías de herramientas."""
    print("\n" + "="*70)
    print(">>> CREANDO CATEGORÍAS DE HERRAMIENTAS")
    print("="*70)
    
    nombres = [
        ('Herramientas Manuales', 'Manual'),
        ('Herramientas Eléctricas', 'Eléctrica'),
        ('Equipos de Seguridad', 'EPP'),
        ('Equipos de Medición', 'Medición'),
        ('Tuberías y Accesorios', 'Accesorios'),
        ('Suministros de Construcción', 'Insumos')
    ]
    
    categorias = []
    for nombre, tipo in nombres:
        cat = CategoriaHerramienta.objects.create(
            nombre_categoria=nombre,
            tipo_herramienta=tipo,
            descripcion=f"Categoría de {nombre}"
        )
        categorias.append(cat)
        print(f"[OK] Categoría: {nombre}")
    return categorias


def crear_proveedores():
    """Crear proveedores."""
    print("\n" + "="*70)
    print(">>> CREANDO PROVEEDORES")
    print("="*70)
    
    datos = [
        ('NIT-900123456-1', '3151234567', 'ventas@herramientascolombia.com', 'Distribuidor oficial de herramientas Stanley'),
        ('NIT-860987654-2', '3109876543', 'soporte@bosch-industrial.co', 'Proveedor de herramientas eléctricas Bosch'),
        ('NIT-800111222-3', '3201112222', 'contacto@epp-seguridad.com.co', 'Distribuidor de elementos de protección personal')
    ]
    
    proveedores = []
    for nit, tel, correo, desc in datos:
        prov = Proveedor.objects.create(
            nit_proveedor=nit,
            telefono_contacto=tel,
            correo_proveedor=correo,
            descripcion=desc
        )
        proveedores.append(prov)
        print(f"[OK] Proveedor: {nit}")
    return proveedores


def crear_suministros(proveedores):
    """Crear suministros."""
    print("\n" + "="*70)
    print(">>> CREANDO SUMINISTROS")
    print("="*70)
    
    suministros = []
    for idx, prov in enumerate(proveedores, 1):
        sumin = Suministro.objects.create(
            codigo_proveedor=prov,
            fecha=timezone.now().date() - timedelta(days=idx * 10),
            cantidad=random.randint(20, 100),
            observaciones=f"Suministro de lote #{idx} recibido correctamente."
        )
        suministros.append(sumin)
        print(f"[OK] Suministro #{sumin.codigo_suministro} (Proveedor {prov.nit_proveedor})")
    return suministros


def crear_herramientas(categorias, suministros):
    """Crear herramientas principales."""
    print("\n" + "="*70)
    print(">>> CREANDO HERRAMIENTAS")
    print("="*70)
    
    datos = [
        ('MART-001', 'Martillo de Goma', 'Martillo profesional anti-rebote', 'Herramientas Manuales', '15'),
        ('TALD-20V', 'Taladro Inalámbrico 20V', 'Taladro percutor compacto de 20V', 'Herramientas Eléctricas', '10'),
        ('CASC-001', 'Casco de Seguridad', 'Casco de protección ANSI clase E', 'Equipos de Seguridad', '50'),
        ('MULT-001', 'Multímetro Digital', 'Multímetro automotriz y profesional', 'Equipos de Medición', '8'),
        ('PINZ-001', 'Pinza Amperimétrica', 'Pinza para medición de corriente alterna', 'Equipos de Medición', '12'),
        ('ESME-001', 'Esmeril Angular 4.5"', 'Esmeriladora angular de alto rendimiento', 'Herramientas Eléctricas', '6'),
    ]
    
    cat_map = {c.nombre_categoria: c for c in categorias}
    herramientas = []
    for sku, nombre, desc, cat_name, disp in datos:
        cat = cat_map.get(cat_name, categorias[0])
        sumin = random.choice(suministros)
        h = Herramienta.objects.create(
            codigo_sku=sku,
            nombre_herramienta=nombre,
            descripcion=desc,
            disponibilidad=disp,
            fecha_ingreso=timezone.now().date(),
            codigo_categoria=cat,
            codigo_suministro=sumin,
            estado='Bueno'
        )
        herramientas.append(h)
        print(f"[OK] Herramienta: {sku} - {nombre}")
    return herramientas


def crear_traslados(estantes, herramientas):
    """Crear traslados y detalles de traslado."""
    print("\n" + "="*70)
    print(">>> CREANDO TRASLADOS Y DETALLES")
    print("="*70)
    
    detalles_traslado = []
    for i in range(1, 6):
        est = random.choice(estantes)
        tras = Traslado.objects.create(
            fecha_movimiento=timezone.now().date() - timedelta(days=i),
            tipo_movimiento=random.choice(['Ingreso', 'Reubicación', 'Salida']),
            num_estante_origen=est,
            dimensiones="Estándar",
            observaciones=f"Traslado interno #{i}"
        )
        
        herr = random.choice(herramientas)
        dt = DetalleTraslado.objects.create(
            codigo_traslado=tras,
            codigo_herramienta=herr,
            cantidad=random.randint(1, 5),
            observaciones=f"Detalle de movimiento para {herr.nombre_herramienta}"
        )
        detalles_traslado.append(dt)
        print(f"[OK] Traslado #{tras.codigo_traslado} | Detalle #{dt.codigo_detalle}")
    return detalles_traslado


def crear_mantenimientos(herramientas, detalles_traslado, usuarios):
    """Crear mantenimientos, detalles y bitácora de estado."""
    print("\n" + "="*70)
    print(">>> CREANDO MANTENIMIENTOS, DETALLES Y BITÁCORAS")
    print("="*70)

    tipos_mant = ["Mantenimiento Preventivo", "Mantenimiento Correctivo", "Calibración", "Reparación Externa"]
    
    for i in range(1, 6):
        herr = random.choice(herramientas)
        tipo = random.choice(tipos_mant)
        fecha_ing = timezone.now().date() - timedelta(days=random.randint(5, 30))
        fecha_sal = fecha_ing + timedelta(days=random.randint(1, 5))
        
        mant = Mantenimiento.objects.create(
            codigo_herramienta=herr,
            tipo_mantenimiento=tipo,
            fecha_ingreso=fecha_ing,
            fecha_salida=fecha_sal,
            descripcion=f"Revisión y {tipo.lower()}.",
            observaciones="Proceso ejecutado sin inconvenientes."
        )
        
        dt_tras = random.choice(detalles_traslado)
        dm = DetalleMantenimiento.objects.create(
            num_mantenimiento=mant,
            codigo_detalle_traslado=dt_tras,
            accion_realizada=f"Limpieza, lubricación y cambio de piezas en {herr.nombre_herramienta}.",
            materiales_usados="Lubricante industrial, sellos de goma",
            fecha_mantenimiento=fecha_ing,
            observacion="Finalizado con certificación de calidad."
        )
        
        usr = random.choice(usuarios)
        BitacoraEstado.objects.create(
            num_mantenimiento=mant,
            codigo_herramienta=herr,
            documento=usr,
            documento_tecnico="TEC-100293",
            es_inutilisable=False,
            descripcion=f"Bitácora de seguimiento de mantenimiento #{mant.num_mantenimiento}",
            observaciones="Herramienta en óptimas condiciones."
        )
        print(f"[OK] Mantenimiento #{mant.num_mantenimiento} - {herr.nombre_herramienta}")


def crear_prestamos_y_devoluciones(usuarios, herramientas):
    """Crear préstamos, detalles y devoluciones de herramientas."""
    print("\n" + "="*70)
    print(">>> CREANDO PRÉSTAMOS, DETALLES Y DEVOLUCIONES")
    print("="*70)
    
    estados = ['PENDIENTE', 'ENTREGADO', 'DEVUELTO', 'CANCELADO']
    
    for i in range(1, 8):
        usr = random.choice(usuarios)
        est = random.choice(estados)
        
        pres = Prestamo.objects.create(
            documento=usr,
            ficha=usr.ficha or "2758369",
            fecha=timezone.now().date() - timedelta(days=random.randint(1, 10)),
            estado=est,
            observaciones=f"Solicitud de préstamo #{i} para laboratorio."
        )
        
        herr = random.choice(herramientas)
        DetallePrestamo.objects.create(
            codigo_prestamo=pres,
            codigo_herramienta=herr,
            cantidad=random.randint(1, 3),
            observaciones=f"Entrega de {herr.nombre_herramienta}"
        )
        
        if est in ['DEVUELTO', 'ENTREGADO']:
            recibe_usr = random.choice(usuarios)
            DevolucionHerramienta.objects.create(
                codigo_prestamo=pres,
                codigo_recibe=recibe_usr,
                fecha=timezone.now().date(),
                observaciones=f"Devolución recibida conforme por {recibe_usr.primer_nombre}."
            )
        print(f"[OK] Préstamo #{pres.codigo_prestamo} ({est}) - Usuario {usr.documento}")


@transaction.atomic
def main():
    print("\n+======================================================+")
    print("|   POBLAR BASE DE DATOS LOCAL - COBERTURA 100% MER    |")
    print("+======================================================+")

    try:
        # Limpieza ordenada de datos existentes
        print("Borrando datos antiguos...")
        BitacoraEstado.objects.all().delete()
        DetalleMantenimiento.objects.all().delete()
        Mantenimiento.objects.all().delete()
        DevolucionHerramienta.objects.all().delete()
        DetallePrestamo.objects.all().delete()
        Prestamo.objects.all().delete()
        DetalleTraslado.objects.all().delete()
        Traslado.objects.all().delete()
        Herramienta.objects.all().delete()
        Suministro.objects.all().delete()
        Proveedor.objects.all().delete()
        CategoriaHerramienta.objects.all().delete()
        Estante.objects.all().delete()
        Almacen.objects.all().delete()
        Usuario.objects.all().delete()
        print("[OK] Limpieza completada.")

        # Generar datos limpios paso a paso
        usuarios = crear_usuarios()
        almacenes, estantes = crear_almacenamiento()
        categorias = crear_categorias()
        proveedores = crear_proveedores()
        suministros = crear_suministros(proveedores)
        herramientas = crear_herramientas(categorias, suministros)
        detalles_traslado = crear_traslados(estantes, herramientas)
        crear_mantenimientos(herramientas, detalles_traslado, usuarios)
        crear_prestamos_y_devoluciones(usuarios, herramientas)
        
        print("\n" + "="*70)
        print("[OK] BASE DE DATOS POBLADA EXITOSAMENTE CON TODAS LAS 15 TABLAS DEL MER!")
        print("="*70)
        print("\n--- Credenciales de acceso ---")
        print("Administrador Principal:")
        print(" - Documento: 0000000000")
        print(" - Contraseña: @dmin123")
        print("Usuarios de Prueba:")
        print(" - Documentos: 1000000001 al 1000000013")
        print(" - Contraseña: Contra123*")
        print("------------------------------\n")
        
    except Exception as e:
        safe_error_msg = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"\n[ERROR] Durante la población: {safe_error_msg}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        call_command('migrate', verbosity=0)
    except Exception as e:
        print(f"Error aplicando migraciones iniciales: {e}")
    main()