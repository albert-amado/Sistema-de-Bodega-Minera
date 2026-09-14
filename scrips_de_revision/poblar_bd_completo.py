#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para poblar la base de datos con datos de ejemplo completos.
Cubre todas las 15 tablas del sistema acorde al MER actualizado,
generando un gran volumen de almacenes, estantes, categorias, proveedores,
suministros, herramientas, traslados, mantenimientos, bitacoras,
prestamos y devoluciones.
"""

import os
import random
import sys
from datetime import timedelta

# Asegurar que la raiz del proyecto este en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django  # noqa: E402

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.hashers import make_password  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from almacen.models import Almacen, Estante  # noqa: E402
from herramienta.models import (  # noqa: E402
    BitacoraEstado,
    CategoriaHerramienta,
    DetalleMantenimiento,
    DetalleTraslado,
    Herramienta,
    Mantenimiento,
    Proveedor,
    Suministro,
    Traslado,
)
from prestamo.models import (  # noqa: E402
    DetallePrestamo,
    DevolucionHerramienta,
    Prestamo,
)
from usuario.models import Usuario  # noqa: E402


def crear_usuarios():
    """Crear usuario admin y usuarios de prueba con Fichas y Programas."""
    print("\n" + "=" * 70)
    print(">>> CREANDO USUARIOS")
    print("=" * 70)

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
            'programa': 'Administracion y Gestion Minera'
        }
    )
    if not created:
        admin.password = make_password('@dmin123')
        admin.rol = 'Administrador'
        admin.save()
    print(f"[OK] Admin principal: {admin_doc} - "
          f"{admin.primer_nombre} {admin.primer_apellido}")

    # Segundo admin / supervisor
    admin2_doc = '1111111111'
    admin2, created2 = Usuario.objects.get_or_create(
        documento=admin2_doc,
        defaults={
            'tipo_documento': 'CC',
            'primer_nombre': 'Carlos',
            'primer_apellido': 'Restrepo',
            'correo_personal': 'carlos.supervisor@mineinventory.com',
            'rol': 'Administrador',
            'password': make_password('@dmin123'),
            'telefono': '3129998877',
            'ficha': 'SUP-002',
            'programa': 'Supervision de Labores Mineras'
        }
    )
    if not created2:
        admin2.password = make_password('@dmin123')
        admin2.rol = 'Administrador'
        admin2.save()
    print(f"[OK] Supervisor admin: {admin2_doc} - Carlos Restrepo")

    nombres_usuarios = [
        ('Juan', 'Perez'), ('Maria', 'Garcia'), ('Carlos', 'Lopez'),
        ('Ana', 'Martinez'), ('Roberto', 'Gonzalez'), ('Sofia', 'Rodriguez'),
        ('Miguel', 'Hernandez'), ('Isabella', 'Torres'), ('David', 'Ramirez'),
        ('Laura', 'Cruz'), ('Fernando', 'Morales'), ('Catalina', 'Soto'),
        ('Pablo', 'Gomez'), ('Andres', 'Castro'), ('Valentina', 'Diaz'),
        ('Mateo', 'Vargas'), ('Camila', 'Rojas'), ('Alejandro', 'Mendoza'),
        ('Daniela', 'Suarez'), ('Javier', 'Silva'), ('Natalia', 'Ortiz'),
        ('Gabriel', 'Guerrero'), ('Mariana', 'Delgado'),
        ('Esteban', 'Paredes'), ('Juliana', 'Navarro'),
    ]

    fichas_opciones = [
        '2758369', '2827435', '2895642', '2910384',
        '3021948', '3196477', '3258102', '3319045'
    ]
    programas_opciones = [
        'Analisis y Desarrollo de Software (ADSO)',
        'Sistemas y Computacion',
        'Electricidad y Automatizacion Industrial',
        'Mantenimiento Electromecanico Industrial',
        'Supervision de Labores Mineras Subterraneas',
        'Topografia y Geomatica',
        'Soldadura en Productos Metalicos',
        'Gestion y Seguridad Ambiental Minera',
        'Operacion de Maquinaria Pesada'
    ]

    usuarios = [admin, admin2]
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
        print(f"[OK] Usuario: {doc} - {nombre} {apellido} "
              f"({usuario.ficha})")

    return usuarios


def crear_almacenamiento():
    """Crear almacenes y estantes con mayor cobertura y distribucion."""
    print("\n" + "=" * 70)
    print(">>> CREANDO ALMACENES Y ESTANTES")
    print("=" * 70)

    almacenes_datos = [
        ('Almacen A - Principal y Taller Central',
         'Edificio Central Nivel 1 - Taller Mecanico',
         '25x18m', [
             ('EST-A-01', 'Estante Pesado 1 - Llaves Manuales', '2.5x1.2m'),
             ('EST-A-02', 'Estante Pesado 2 - Golpe y Corte', '2.5x1.2m'),
             ('EST-A-03', 'Gabinete Metalico A3 - Fijacion', '2.0x0.9m'),
             ('EST-A-04', 'Rack Modular A4 - Neumaticos', '3.0x1.5m'),
             ('EST-A-05', 'Mesa de Trabajo y Banco de Pruebas', '4.0x1.2m'),
         ]),
        ('Almacen B - Equipos Electricos y Poder',
         'Hangar Tecnico Zona Este',
         '18x12m', [
             ('EST-B-01', 'Rack B1 - Taladros y Rotomartillos', '3.0x1.2m'),
             ('EST-B-02', 'Rack B2 - Esmeriles y Pulidoras', '3.0x1.2m'),
             ('EST-B-03', 'Estante B3 - Baterias y Cargadores', '2.0x1.0m'),
             ('EST-B-04', 'Armario B4 - Bombas Sumergibles', '3.5x1.5m'),
         ]),
        ('Almacen C - EPP y Seguridad Industrial',
         'Modulo de Salud Ocupacional (SST)',
         '12x10m', [
             ('EST-C-01', 'Estante C1 - Cascos y Proteccion', '2.2x1.0m'),
             ('EST-C-02', 'Estante C2 - Arneses y Lineas', '2.5x1.2m'),
             ('EST-C-03', 'Estante C3 - Respiradores y Gafas', '2.0x0.8m'),
             ('EST-C-04', 'Locker C4 - Botiquines y Primeros Aux', '2.0x1.0m'),
         ]),
        ('Almacen D - Perforacion y Mineria Subterranea',
         'Bocamina Nivel 0 - Rampa Principal',
         '20x15m', [
             ('EST-D-01', 'Rack D1 - Barrenas y Brocas', '3.5x1.5m'),
             ('EST-D-02', 'Estante D2 - Lamparas Mineras', '2.5x1.0m'),
             ('EST-D-03', 'Gabinete D3 - Auto-rescatadores', '2.0x1.0m'),
             ('EST-D-04', 'Rack D4 - Picos y Palas', '3.0x1.5m'),
         ]),
        ('Almacen E - Topografia y Equipos de Precision',
         'Laboratorio de Geomatica - Nivel 2',
         '10x8m', [
             ('EST-E-01', 'Estante Climatizado E1 - Estaciones', '2.0x1.0m'),
             ('EST-E-02', 'Rack E2 - Tripodes y Miras', '2.5x1.2m'),
             ('EST-E-03', 'Armario E3 - Multimetros y Pinzas', '2.0x0.8m'),
             ('EST-E-04', 'Estante E4 - Niveles Laser', '1.8x0.8m'),
         ]),
        ('Almacen F - Auxiliar Frente de Avance',
         'Galeria Norte Km 2.5',
         '14x8m', [
             ('EST-F-01', 'Estante F1 - Mantenimiento Rapido', '2.0x1.0m'),
             ('EST-F-02', 'Estante F2 - Mangueras de Aire', '2.5x1.2m'),
             ('EST-F-03', 'Estante F3 - Repuestos de Emergencia', '2.0x1.0m'),
         ]),
    ]

    almacenes = []
    estantes = []
    for nombre, ubic, dim, estantes_info in almacenes_datos:
        alm = Almacen.objects.create(
            nombre=nombre, dimensiones=dim, ubicacion=ubic
        )
        almacenes.append(alm)
        print(f"[OK] Almacen: {nombre} ({ubic})")

        for cod_est, desc_est, dim_est in estantes_info:
            est = Estante.objects.create(
                codigo_almacen=alm,
                codigo=cod_est,
                dimensiones=dim_est
            )
            estantes.append(est)
            print(f"  [OK] Estante: {cod_est} [{dim_est}] - {desc_est}")

    return almacenes, estantes


def crear_categorias():
    """Crear categorias completas de herramientas."""
    print("\n" + "=" * 70)
    print(">>> CREANDO CATEGORIAS DE HERRAMIENTAS")
    print("=" * 70)

    categorias_datos = [
        ('Herramientas Manuales', 'Manual',
         'Herramientas de mano como llaves, destornilladores y martillos.'),
        ('Herramientas Electricas', 'Electrica',
         'Equipos de poder como taladros, esmeriles y sierras.'),
        ('Herramientas Neumaticas', 'Neumatica',
         'Equipos accionados por aire comprimido como pistolas de impacto.'),
        ('Equipos de Proteccion Personal (EPP)', 'EPP',
         'Elementos de seguridad: cascos, arneses, gafas y respiradores.'),
        ('Equipos de Medicion y Topografia', 'Medicion',
         'Instrumentos: estaciones totales, niveles y multimetros.'),
        ('Seguridad Minera y Rescate', 'Seguridad',
         'Equipos criticos: detectores multigas y lamparas mineras.'),
        ('Equipos de Soldadura y Corte', 'Termica',
         'Inversores de soldadura, caretas fotosensibles y accesorios.'),
        ('Herramientas Pesadas de Perforacion', 'Pesada',
         'Barrenas integrales, cinceles neumaticos, picos y palas.')
    ]

    categorias = []
    for nombre, tipo, desc in categorias_datos:
        cat = CategoriaHerramienta.objects.create(
            nombre_categoria=nombre,
            tipo_herramienta=tipo,
            descripcion=desc
        )
        categorias.append(cat)
        print(f"[OK] Categoria: {nombre} ({tipo})")
    return categorias


def crear_proveedores():
    """Crear proveedores industriales reconocidos."""
    print("\n" + "=" * 70)
    print(">>> CREANDO PROVEEDORES")
    print("=" * 70)

    datos = [
        ('NIT-900123456-1', '3151234567',
         'ventas@stanleyblackanddecker.co',
         'Distribuidor oficial de herramientas Stanley y DeWalt.'),
        ('NIT-860987654-2', '3109876543',
         'corporativo@bosch-industrial.co',
         'Proveedor autorizado de herramientas electricas Bosch.'),
        ('NIT-800111222-3', '3201112222',
         'contacto@3m-seguridadminera.com.co',
         'Fabricante lider de EPP, respiradores y arneses 3M.'),
        ('NIT-900555666-4', '3185556677',
         'servicio.cliente@hilti-colombia.com',
         'Sistemas de perforacion y anclaje de alto rendimiento Hilti.'),
        ('NIT-830222333-5', '3112223344',
         'ventas@truper-ferreteria.co',
         'Herramientas de ferreteria pesada y compresores Truper.'),
        ('NIT-901444888-6', '3144448899',
         'soporte@leica-geosystems.co',
         'Representante exclusivo de topografia y estaciones Leica.'),
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
        print(f"[OK] Proveedor: {nit} ({correo})")
    return proveedores


def crear_suministros(proveedores):
    """Crear lotes de suministros ordenados por proveedor."""
    print("\n" + "=" * 70)
    print(">>> CREANDO SUMINISTROS (LOTES DE ENTRADA)")
    print("=" * 70)

    suministros = []
    lote_num = 1
    for prov in proveedores:
        for j in range(1, 3):
            dias_atras = (lote_num * 12) + random.randint(1, 5)
            sumin = Suministro.objects.create(
                codigo_proveedor=prov,
                fecha=timezone.now().date() - timedelta(days=dias_atras),
                cantidad=random.randint(40, 150),
                observaciones=(
                    f"Lote #{lote_num:03d} recibido con remision oficial "
                    f"{prov.nit_proveedor[-4:]}-{j*100}. Calidad aprobada."
                )
            )
            suministros.append(sumin)
            print(f"[OK] Suministro #{sumin.codigo_suministro} "
                  f"(Proveedor: {prov.nit_proveedor}, Cant: {sumin.cantidad})")
            lote_num += 1
    return suministros


def crear_herramientas(categorias, suministros, estantes):
    """Crear catalogo amplio de herramientas con estantes asignados."""
    print("\n" + "=" * 70)
    print(">>> CREANDO HERRAMIENTAS (INVENTARIO COMPLETO)")
    print("=" * 70)

    cat_map = {c.nombre_categoria: c for c in categorias}
    estantes_map = {e.codigo: e for e in estantes}

    datos_herramientas = [
        # Herramientas Manuales
        ('MAN-LLAV-01', 'Juego de Llaves Mixtas 8-32mm Stanley',
         'Set de 14 llaves combinadas en cromo vanadio',
         'Herramientas Manuales', '18', 'Bueno', 'EST-A-01'),
        ('MAN-STIL-24', 'Llave de Tubo Stillson 24" Heavy Duty',
         'Llave para tuberia pesada con mordazas templadas',
         'Herramientas Manuales', '12', 'Bueno', 'EST-A-01'),
        ('MAN-STIL-14', 'Llave de Tubo Stillson 14" Forjada',
         'Llave para conexiones hidraulicas y tuberia',
         'Herramientas Manuales', '15', 'Bueno', 'EST-A-01'),
        ('MAN-DEST-01', 'Juego de Destornilladores Aislados 1000V',
         'Juego de 7 destornilladores dielectricos para electricista',
         'Herramientas Manuales', '20', 'Bueno', 'EST-A-03'),
        ('MAN-MART-01', 'Martillo de Goma Anti-rebote 24 oz',
         'Martillo con cabeza rellena de balines de acero',
         'Herramientas Manuales', '14', 'Bueno', 'EST-A-02'),
        ('MAN-ALIC-01', 'Alicate Universal de Alta Palanca 8"',
         'Alicate para corte y sujecion con mangos ergonomicos',
         'Herramientas Manuales', '22', 'Bueno', 'EST-A-01'),
        ('MAN-FLEX-08', 'Flexometro Profesional 8m / 26ft',
         'Cinta metrica con recubrimiento de nylon y gancho magnetico',
         'Herramientas Manuales', '30', 'Bueno', 'EST-A-03'),
        ('MAN-TORQ-01', 'Torquimetro de Trueno 1/2" 20-150 ft-lb',
         'Llave dinamometrica de precision con certificado de fabrica',
         'Herramientas Manuales', '6', 'Bueno', 'EST-E-03'),

        # Herramientas Electricas
        ('ELE-TALD-20', 'Taladro Percutor Inalambrico 20V MAX DeWalt',
         'Taladro compacto Brushless con 2 baterias de 4.0Ah y cargador',
         'Herramientas Electricas', '10', 'Bueno', 'EST-B-01'),
        ('ELE-ROTO-01', 'Rotomartillo SDS Plus 800W Bosch GBH 2-24',
         'Rotomartillo para perforacion en concreto y mamposteria',
         'Herramientas Electricas', '8', 'Bueno', 'EST-B-01'),
        ('ELE-DEMO-01', 'Martillo Demoledor SDS Max 1500W Hilti',
         'Equipo demoledor de alto impacto para fractura de roca',
         'Herramientas Electricas', '4', 'Bueno', 'EST-B-01'),
        ('ELE-ESME-45', 'Esmeril Angular 4.5" 1100W Bosch GWS',
         'Esmeriladora angular para desbaste y corte de metales',
         'Herramientas Electricas', '12', 'Bueno', 'EST-B-02'),
        ('ELE-ESME-07', 'Esmeril Angular 7" 2200W DeWalt DWE',
         'Pulidora industrial de alta potencia para trabajos pesados',
         'Herramientas Electricas', '6', 'Bueno', 'EST-B-02'),
        ('ELE-SIER-01', 'Sierra Circular 7-1/4" 1800W Makita',
         'Sierra con guia laser para corte recto de madera',
         'Herramientas Electricas', '5', 'Bueno', 'EST-B-02'),
        ('ELE-BOMB-02', 'Bomba Sumergible de Achique 2HP 220V',
         'Bomba centrifuga para extraccion de aguas lodosas en bocamina',
         'Herramientas Electricas', '3', 'Bueno', 'EST-B-04'),

        # Herramientas Neumaticas
        ('NEU-PIST-12', 'Pistola de Impacto Neumatica 1/2" Twin Hammer',
         'Llave de impacto para mantenimiento automotriz y maquinaria',
         'Herramientas Neumaticas', '7', 'Bueno', 'EST-A-04'),
        ('NEU-COMP-50', 'Compresor de Aire Portatil 50L 2.5HP Truper',
         'Compresor de piston lubricado con regulador de presion doble',
         'Herramientas Neumaticas', '4', 'Bueno', 'EST-A-04'),
        ('NEU-PULI-01', 'Pulidora Angular Neumatica 5" Heavy Duty',
         'Pulidora accionada por aire comprimido para areas confinadas',
         'Herramientas Neumaticas', '5', 'Bueno', 'EST-F-02'),

        # Equipos de Proteccion Personal (EPP)
        ('EPP-CASC-01', 'Casco Minero Tipo II con Porta-Lampara',
         'Casco dielectrico ANSI Z89.1 Clase E con suspension 4 puntos',
         'Equipos de Proteccion Personal (EPP)', '60', 'Bueno', 'EST-C-01'),
        ('EPP-ARNE-04', 'Arnes de Seguridad Multiproposito 4 Argollas',
         'Arnes de cuerpo entero con soporte lumbar y argollas',
         'Equipos de Proteccion Personal (EPP)', '25', 'Bueno', 'EST-C-02'),
        ('EPP-ESLI-01', 'Eslinga de Posicionamiento con Absorbedor',
         'Linea de vida doble con ganchos de 2-1/4" y disipador',
         'Equipos de Proteccion Personal (EPP)', '30', 'Bueno', 'EST-C-02'),
        ('EPP-RESP-3M', 'Respirador Media Cara Serie 6200 3M + P100',
         'Proteccion respiratoria contra polvos de carbon y vapores',
         'Equipos de Proteccion Personal (EPP)', '40', 'Bueno', 'EST-C-03'),
        ('EPP-GAFA-01', 'Gafas de Seguridad Anti-empanante Virtua 3M',
         'Lentes de policarbonato con proteccion UV anti-rayaduras',
         'Equipos de Proteccion Personal (EPP)', '80', 'Bueno', 'EST-C-03'),
        ('EPP-GUAN-01', 'Guantes de Vaqueta Cana Larga Reforzados',
         'Guante de cuero vacuno para manipulacion de rocas y cables',
         'Equipos de Proteccion Personal (EPP)', '100', 'Bueno', 'EST-C-01'),

        # Equipos de Medicion y Topografia
        ('MED-ESTA-01', 'Estacion Total Leica FlexLine TS07 2"',
         'Equipo de topografia de alta precision con medicion sin prisma',
         'Equipos de Medicion y Topografia', '2', 'Bueno', 'EST-E-01'),
        ('MED-NIVE-01', 'Nivel Optico Automatico Leica NA320 20x',
         'Nivel de precision con compensador de pendulo magnetico',
         'Equipos de Medicion y Topografia', '4', 'Bueno', 'EST-E-02'),
        ('MED-FLUK-117', 'Multimetro Digital True-RMS Fluke 117',
         'Multimetro profesional con detector de voltaje VoltAlert',
         'Equipos de Medicion y Topografia', '8', 'Bueno', 'EST-E-03'),
        ('MED-PINZ-376', 'Pinza Amperimetrica Fluke 376 FC con iFlex',
         'Medicion de corriente CA/CC hasta 1000A con registro inalambrico',
         'Equipos de Medicion y Topografia', '5', 'Bueno', 'EST-E-03'),
        ('MED-CLIN-01', 'Clinometro y Brujula Brunton Geo Pocket',
         'Instrumento geologico para rumbo y buzamiento de estratos',
         'Equipos de Medicion y Topografia', '6', 'Bueno', 'EST-E-04'),
        ('MED-LASE-360', 'Nivel Laser Autonivelante 360 Lineas Cruzadas',
         'Nivel laser verde para alineacion de galerias y montaje',
         'Equipos de Medicion y Topografia', '6', 'Bueno', 'EST-E-04'),

        # Seguridad Minera y Rescate
        ('SEG-GAS4-01', 'Detector Multigas Cuadruple Industrial Scientific',
         'Monitoreo de CO, O2, H2S y LEL con alarma sonora/luminica',
         'Seguridad Minera y Rescate', '12', 'Bueno', 'EST-D-03'),
        ('SEG-LAMP-01', 'Lampara Minera LED Inalambrica Ex',
         'Lampara de casco certificada ATEX/IECEx con 15h de autonomia',
         'Seguridad Minera y Rescate', '45', 'Bueno', 'EST-D-02'),
        ('SEG-RESC-30', 'Auto-rescatador de Oxigeno Quimico 30 Minutos',
         'Dispositivo de escape para emergencias mineras con O2',
         'Seguridad Minera y Rescate', '20', 'Bueno', 'EST-D-03'),

        # Equipos de Soldadura y Corte
        ('SOL-INVE-200', 'Soldador Inversor 200A Lincoln Electric',
         'Equipo inversor multiproceso SMAW/GTAW con tecnologia IGBT',
         'Equipos de Soldadura y Corte', '5', 'Bueno', 'EST-A-05'),
        ('SOL-CARE-01', 'Careta Fotosensible para Soldadura 9-13',
         'Casco para soldador con filtro auto-oscurecible y 4 sensores',
         'Equipos de Soldadura y Corte', '10', 'Bueno', 'EST-A-05'),

        # Herramientas Pesadas de Perforacion
        ('PES-BARR-12', 'Barrena Integral de Perforacion 1.2m Hilti Hex 22',
         'Barrena con inserto de carburo de tungsteno para roca',
         'Herramientas Pesadas de Perforacion', '15', 'Bueno', 'EST-D-01'),
        ('PES-PICO-05', 'Pico Minero de Punta y Pala 5 lbs Mango Fibra',
         'Pico de acero forjado con tratamiento termico antivibracion',
         'Herramientas Pesadas de Perforacion', '25', 'Bueno', 'EST-D-04'),
        ('PES-PALA-01', 'Pala Minera Punta Redonda Herragro Mango Fibra',
         'Pala carbonera y minera estampada en lamina de alta resistencia',
         'Herramientas Pesadas de Perforacion', '30', 'Bueno', 'EST-D-04'),
    ]

    herramientas = []
    for sku, nom, desc, cat_name, disp, est_nom, cod_est in datos_herramientas:
        cat = cat_map.get(cat_name, categorias[0])
        sumin = random.choice(suministros)
        estante_obj = estantes_map.get(cod_est, estantes[0])

        dias = random.randint(15, 120)
        h = Herramienta.objects.create(
            codigo_sku=sku,
            nombre_herramienta=nom,
            descripcion=desc,
            disponibilidad=disp,
            fecha_ingreso=timezone.now().date() - timedelta(days=dias),
            codigo_categoria=cat,
            codigo_suministro=sumin,
            estado=est_nom,
            estante=estante_obj
        )
        herramientas.append(h)
        print(f"[OK] Herramienta: {sku} - {nom} "
              f"(Stock: {disp}, Ubicacion: {estante_obj.codigo})")

    return herramientas


def crear_traslados(estantes, herramientas):
    """Crear registros de traslados internos y reubicaciones."""
    print("\n" + "=" * 70)
    print(">>> CREANDO TRASLADOS Y DETALLES")
    print("=" * 70)

    tipos = [
        'Ingreso', 'Reubicacion', 'Salida',
        'Mantenimiento Preventivo', 'Asignacion de Frente'
    ]
    detalles_traslado = []

    for i in range(1, 16):
        est_origen = random.choice(estantes)
        dias = random.randint(2, 45)
        tras = Traslado.objects.create(
            fecha_movimiento=timezone.now().date() - timedelta(days=dias),
            tipo_movimiento=random.choice(tipos),
            num_estante_origen=est_origen,
            dimensiones="Estandar / Lote",
            observaciones=(
                f"Movimiento interno #{i} - Autorizado por logistica de "
                f"almacen ({est_origen.codigo})."
            )
        )

        herr = random.choice(herramientas)
        dt = DetalleTraslado.objects.create(
            codigo_traslado=tras,
            codigo_herramienta=herr,
            cantidad=random.randint(1, 6),
            observaciones=(
                f"Reubicacion de {herr.nombre_herramienta} hacia frente."
            )
        )
        detalles_traslado.append(dt)
        print(f"[OK] Traslado #{tras.codigo_traslado} "
              f"({tras.tipo_movimiento}) | Detalle #{dt.codigo_detalle} - "
              f"{herr.nombre_herramienta}")

    return detalles_traslado


def crear_mantenimientos(herramientas, detalles_traslado, usuarios):
    """Crear registros de mantenimiento y bitacoras de estado."""
    print("\n" + "=" * 70)
    print(">>> CREANDO MANTENIMIENTOS, DETALLES Y BITACORAS")
    print("=" * 70)

    tipos_mant = [
        "Mantenimiento Preventivo Periodico",
        "Mantenimiento Correctivo",
        "Calibracion y Certificacion de Precision",
        "Reparacion por Desgaste de Turno",
        "Inspeccion de Seguridad Dielectrica"
    ]

    tecnicos = [
        "TEC-100293 (Juan Soto)", "TEC-100542 (Alonso Morales)",
        "TEC-100889 (Patricia Ruiz)", "EXT-90211-BOSCH"
    ]

    for _ in range(1, 14):
        herr = random.choice(herramientas)
        tipo = random.choice(tipos_mant)
        fecha_ing = timezone.now().date() - timedelta(
            days=random.randint(10, 60)
        )
        fecha_sal = fecha_ing + timedelta(days=random.randint(1, 6))

        mant = Mantenimiento.objects.create(
            codigo_herramienta=herr,
            tipo_mantenimiento=tipo,
            fecha_ingreso=fecha_ing,
            fecha_salida=fecha_sal,
            descripcion=f"Protocolo de {tipo.lower()} para "
                        f"{herr.nombre_herramienta}.",
            observaciones="Revision de componentes mecanicos y circuitos "
                          "completada satisfactoriamente."
        )

        dt_tras = random.choice(detalles_traslado)
        DetalleMantenimiento.objects.create(
            num_mantenimiento=mant,
            codigo_detalle_traslado=dt_tras,
            accion_realizada=(
                f"Limpieza ultra-sonica, cambio de rodamientos y lubricacion "
                f"en {herr.nombre_herramienta}."
            ),
            materiales_usados="Grasa dielectrica, juego de escobillas, sellos",
            fecha_mantenimiento=fecha_ing,
            observacion="Pruebas de funcionamiento aprobadas al 100%."
        )

        usr = random.choice(usuarios)
        tec = random.choice(tecnicos)
        BitacoraEstado.objects.create(
            num_mantenimiento=mant,
            codigo_herramienta=herr,
            documento=usr,
            documento_tecnico=tec,
            es_inutilisable=False,
            descripcion=(
                f"Bitacora tecnica de mantenimiento #{mant.num_mantenimiento}."
            ),
            observaciones=(
                f"Herramienta verificada por supervisor {usr.primer_nombre} "
                f"{usr.primer_apellido}. Lista para reingreso."
            )
        )
        print(f"[OK] Mantenimiento #{mant.num_mantenimiento} ({tipo}) - "
              f"{herr.nombre_herramienta}")


def crear_prestamos_y_devoluciones(usuarios, herramientas):
    """Crear gran volumen de prestamos y devoluciones coherentes."""
    print("\n" + "=" * 70)
    print(">>> CREANDO PRESTAMOS, DETALLES Y DEVOLUCIONES ABUNDANTES")
    print("=" * 70)

    # Administradores o supervisores que reciben las devoluciones
    receptores = [
        u for u in usuarios
        if u.rol == 'Administrador' or u.documento in [
            '0000000000', '1111111111', '1000000001'
        ]
    ]
    if not receptores:
        receptores = usuarios[:2]

    usuarios_aprendices = [u for u in usuarios if u.rol == 'Usuario']
    if not usuarios_aprendices:
        usuarios_aprendices = usuarios

    motivos_prestamos = [
        "Practica de topografia y levantamiento planimetrico en rampa sur.",
        "Mantenimiento electrico preventivo de transformadores en Nivel 1.",
        "Taller practico de soldadura SMAW en estructuras metalicas.",
        "Inspeccion de avance y control de atmosfera en galeria.",
        "Laboratorio de pruebas mecanicas y calibracion de instrumentos.",
        "Turno operativo de sostenimiento con mallas y pernos.",
        "Practica de rescate minero y uso de auto-rescatadores.",
        "Mantenimiento correctivo de compresores y lineas de aire.",
        "Montaje de tuberias de desague y achique en nivel freatico.",
        "Supervision y control de vibraciones en banqueo a cielo abierto.",
        "Practica de cartografia digital y nivelacion geometrica.",
        "Revision de tableros de control y motores electricos.",
        "Instalacion de luminarias LED y cableado industrial.",
        "Taller de corte y desbaste de perfiles de acero para tolva.",
        "Simulacro de evacuacion y verificacion de equipos de proteccion."
    ]

    observaciones_devolucion = [
        "Herramientas devueltas en excelente estado fisico y operativas.",
        "Devolucion recibida conforme. Se verifica funcionamiento general.",
        "Equipo entregado sin novedades. Retorna a su estante asignado.",
        "Devolucion parcial: herramientas principales entregadas en optimo.",
        "Recibido con informe de uso satisfactorio sin danos anormales.",
        "Herramientas verificadas y probadas en banco de pruebas.",
        "Devolucion completa tras finalizacion de turno de practicas."
    ]

    # 32 Prestamos con una distribucion variada de estados
    distribucion_estados = (
        ['DEVUELTO'] * 12 +
        ['ENTREGADO'] * 9 +
        ['PENDIENTE'] * 5 +
        ['PARCIAL'] * 4 +
        ['CANCELADO'] * 2
    )

    total_prestamos = 0
    total_detalles = 0
    total_devoluciones = 0

    for i, estado in enumerate(distribucion_estados, 1):
        usr = random.choice(usuarios_aprendices)
        if estado in ['DEVUELTO', 'PARCIAL', 'ENTREGADO']:
            dias_pres = random.randint(1, 40)
        else:
            dias_pres = random.randint(0, 5)

        fecha_pres = timezone.now().date() - timedelta(days=dias_pres)
        motivo = random.choice(motivos_prestamos)

        pres = Prestamo.objects.create(
            documento=usr,
            ficha=usr.ficha or "2758369",
            fecha=fecha_pres,
            estado=estado,
            observaciones=f"Prestamo #{i:02d}: {motivo}"
        )
        total_prestamos += 1

        num_items = random.choices([1, 2, 3], weights=[45, 40, 15])[0]
        herramientas_seleccionadas = random.sample(herramientas, k=num_items)

        for herr in herramientas_seleccionadas:
            cant = random.randint(1, 3)
            DetallePrestamo.objects.create(
                codigo_prestamo=pres,
                codigo_herramienta=herr,
                cantidad=cant,
                observaciones=(
                    f"Asignacion de {cant} unidad(es) de "
                    f"{herr.nombre_herramienta}"
                )
            )
            total_detalles += 1

        # Si el estado es DEVUELTO, PARCIAL o parte de ENTREGADO
        con_devolucion = estado in ['DEVUELTO', 'PARCIAL'] or (
            estado == 'ENTREGADO' and random.random() < 0.3
        )
        if con_devolucion:
            recibe_usr = random.choice(receptores)
            dias_despues = random.randint(0, min(dias_pres, 3))
            fecha_dev = fecha_pres + timedelta(days=dias_despues)
            if fecha_dev > timezone.now().date():
                fecha_dev = timezone.now().date()

            obs_dev = random.choice(observaciones_devolucion)
            if estado == 'PARCIAL':
                obs_dev = (
                    "Devolucion parcial: pendiente entrega de accesorios."
                )

            DevolucionHerramienta.objects.create(
                codigo_prestamo=pres,
                codigo_recibe=recibe_usr,
                fecha=fecha_dev,
                observaciones=(
                    f"{obs_dev} (Recepcion por {recibe_usr.primer_nombre} "
                    f"{recibe_usr.primer_apellido})."
                )
            )
            total_devoluciones += 1

        print(f"[OK] Prestamo #{pres.codigo_prestamo:02d} [{estado}] - "
              f"{usr.primer_nombre} {usr.primer_apellido} ({pres.ficha}) "
              f"- {num_items} herramientas")

    print(f"\n>> Total prestamos generados: {total_prestamos}")
    print(f">> Total items/detalles de prestamo: {total_detalles}")
    print(f">> Total registros de devolucion: {total_devoluciones}")


@transaction.atomic
def main():
    print("\n+================================================================+")
    print("|   POBLAR BASE DE DATOS LOCAL - POBLACION COMPLETA MER           |")
    print("+================================================================+")

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
        herramientas = crear_herramientas(categorias, suministros, estantes)
        detalles_traslado = crear_traslados(estantes, herramientas)
        crear_mantenimientos(herramientas, detalles_traslado, usuarios)
        crear_prestamos_y_devoluciones(usuarios, herramientas)

        print("\n" + "=" * 70)
        print("[OK] BASE DE DATOS POBLADA EXITOSAMENTE CON VOLUMEN COMPLETO!")
        print("=" * 70)
        print("\n--- Credenciales de acceso ---")
        print("Administrador Principal:")
        print(" - Documento: 0000000000")
        print(" - Contrasena: @dmin123")
        print("Administrador Secundario:")
        print(" - Documento: 1111111111")
        print(" - Contrasena: @dmin123")
        print("Usuarios / Aprendices de Prueba:")
        print(f" - Documentos: 1000000001 al 1000000{len(usuarios)-2:03d}")
        print(" - Contrasena: Contra123*")
        print("------------------------------\n")

    except Exception as e:
        safe_error_msg = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"\n[ERROR] Durante la poblacion: {safe_error_msg}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        call_command('migrate', verbosity=0)
    except Exception as e:
        print(f"Error aplicando migraciones iniciales: {e}")
    main()