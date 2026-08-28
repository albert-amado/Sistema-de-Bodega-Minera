#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para reiniciar la base de datos SQLite y eliminar los archivos de migración.
"""

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def reset_db_y_migraciones():
    print("=" * 60)
    print(">>> ELIMINANDO BASE DE DATOS Y MIGRACIONES")
    print("=" * 60)

    # 1. Eliminar base de datos SQLite y archivos de journal/WAL de transacciones
    archivos_db = ["db.sqlite3", "db.sqlite3-journal", "db.sqlite3-wal", "db.sqlite3-shm"]
    for db_fname in archivos_db:
        db_file = BASE_DIR / db_fname
        if db_file.exists():
            try:
                db_file.unlink()
                print(f"[OK] Archivo de base de datos eliminado: {db_fname}")
            except Exception as e:
                print(f"[ERROR] No se pudo eliminar {db_fname}: {e}")

    # 2. Buscar carpetas de apps y eliminar migraciones (conservando __init__.py)
    apps = ['almacen', 'herramienta', 'prestamo', 'usuario', 'common', 'pagina_principal']
    archivos_eliminados = 0

    for app in apps:
        migrations_dir = BASE_DIR / app / "migrations"
        if migrations_dir.exists() and migrations_dir.is_dir():
            for item in migrations_dir.iterdir():
                if item.name != "__init__.py" and item.is_file() and item.suffix == ".py":
                    try:
                        item.unlink()
                        archivos_eliminados += 1
                        print(f"  [OK] Eliminada migración: {app}/migrations/{item.name}")
                    except Exception as e:
                        print(f"  [ERROR] No se pudo eliminar {item.name}: {e}")
                elif item.name == "__pycache__" and item.is_dir():
                    try:
                        shutil.rmtree(item)
                        print(f"  [OK] Eliminado cache: {app}/migrations/__pycache__")
                    except Exception as e:
                        print(f"  [ERROR] No se pudo eliminar {item.name}: {e}")

    print("-" * 60)
    print(f"[EXITO] Proceso completado. Se eliminaron {archivos_eliminados} archivos de migración.")
    print("Para volver a regenerar la base de datos limpia, ejecuta:")
    print("  python manage.py makemigrations")
    print("  python manage.py migrate")
    print("  python poblar_bd_completo.py")
    print("=" * 60)


if __name__ == "__main__":
    reset_db_y_migraciones()
