#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verificar_rubrica.py
===================
Herramienta de autoevaluación para verificar el cumplimiento de los 12 puntos de
la rúbrica técnica en el proyecto Django/Frontend.

Uso:
    python verificar_rubrica.py
"""

import os
import re
import sys
from pathlib import Path

# ────────────────────────────────────────────────────────
# Configuración
# ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROJECT_NAME = os.path.basename(os.getcwd())

# Carpetas a omitir
EXCLUDED_DIRS = {
    '.git', '__pycache__', '.venv', 'venv', 'env',
    'node_modules', 'migrations', 'staticfiles', 'media',
    '.gemini', '.agents'
}

# Códigos de color ANSI para consola (compatibles con terminales modernos)
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
WHITE = "\033[97m"

# Mapeo de sugerencias clave para cada uno de los 12 puntos de la rúbrica
SUGERENCIAS_MAP = {
    1: "Mejorar la estructura modular de las plantillas HTML utilizando herencia ({% extends %}) o fragmentos reusables ({% include %}).",
    2: "Definir un enrutamiento estructurado y limpio en archivos urls.py para todos los modulos.",
    3: "Asegurar que todas las llamadas de consumo de API REST capturen errores de conexion y manejen estados de carga.",
    4: "Reducir el uso de estilos en linea (style=\"...\") en las plantillas HTML (trasladar a CSS).",
    5: "Implementar binding reactivo de datos en el frontend mediante JavaScript y escuchadores de eventos del DOM.",
    6: "Robustecer la validacion de formularios en frontend (HTML5/JS) y backend (Django Forms y .is_valid()).",
    7: "Migrar las variables SECRET_KEY y EMAIL_HOST_PASSWORD a variables de entorno (.env).",
    8: "Organizar el codigo de forma logica respetando el patron MVT de Django (separando modelos, vistas, plantillas y archivos estaticos).",
    9: "Crear o ampliar la cobertura de pruebas unitarias (tests.py) para evaluar el comportamiento de los componentes.",
    10: "Añadir loading=\"lazy\" a imagenes y async/defer a scripts.",
    11: "Mejorar documentacion de metodos complejos del frontend usando estandar JSDoc.",
    12: "Garantizar la adaptabilidad responsiva del diseño mediante Bootstrap Grid o consultas de medios CSS (@media)."
}

def print_colored(text, color):
    # Detectar si la consola soporta colores o si redirige salida
    if sys.stdout.isatty():
        formatted_text = f"{color}{text}{RESET}"
    else:
        formatted_text = text
    try:
        print(formatted_text)
    except UnicodeEncodeError:
        safe_text = (
            text.replace("✔", "[OK]")
                .replace("⚠", "[WARN]")
                .replace("✖", "[ERROR]")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("á", "a")
                .replace("é", "e")
                .replace("ú", "u")
                .replace("ñ", "n")
                .replace("¿", "")
                .replace("¡", "")
                .replace("á", "a")
        )
        if sys.stdout.isatty():
            print(f"{color}{safe_text}{RESET}")
        else:
            print(safe_text)

# ────────────────────────────────────────────────────────
# Funciones de Análisis de Rúbrica
# ────────────────────────────────────────────────────────

def check_ui_structure():
    """
    Punto 1: Estructura los componentes de la interfaz utilizando la sintaxis específica del framework.
    Analiza Django Templates (% extends, % block, % include) que representan modularización en Django.
    """
    html_files = []
    extends_count = 0
    include_count = 0
    block_count = 0
    load_static_count = 0
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f.endswith('.html') and f != 'reporte_rubrica.html':
                path = os.path.join(root, f)
                html_files.append(path)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        if '{% extends' in content:
                            extends_count += 1
                        if '{% include' in content:
                            include_count += 1
                        if '{% block' in content:
                            block_count += 1
                        if '{% load static' in content:
                            load_static_count += 1
                except Exception:
                    pass

    total = len(html_files)
    if total == 0:
        return {"status": "RED", "score": 0, "msg": "No se encontraron archivos HTML/Plantillas.", "details": []}
    
    # Calcular cumplimiento
    reusability_ratio = (extends_count + include_count) / total
    details = [
        f"Total de plantillas HTML detectadas: {total}",
        f"Plantillas que heredan ({'{% extends %}'}): {extends_count}",
        f"Plantillas con fragmentos reusables ({'{% include %}'}): {include_count}",
        f"Bloques definidos ({'{% block %}'}): {block_count}",
        f"Uso de static ({'{% load static %}'}): {load_static_count}"
    ]
    
    if reusability_ratio >= 0.5:
        return {
            "status": "GREEN", 
            "score": 100, 
            "msg": "Excelente. La arquitectura de Django Templates usa herencia de plantillas de forma modular.",
            "details": details
        }
    elif reusability_ratio > 0.2:
        return {
            "status": "YELLOW", 
            "score": 75, 
            "msg": "Parcial. Considera modularizar componentes repetitivos usando {% include %}.",
            "details": details
        }
    else:
        return {
            "status": "RED", 
            "score": 40, 
            "msg": "Bajo nivel de herencia de plantillas. Las vistas podrían estar duplicando código de base.",
            "details": details
        }

def check_routing():
    """
    Punto 2: Implementa el enrutamiento de vistas asegurando la navegación correcta.
    Analiza archivos urls.py y la definición de rutas (path, re_path).
    """
    urls_files = []
    total_routes = 0
    route_patterns = re.compile(r'\b(path|re_path|url)\s*\(')
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f == 'urls.py':
                path = os.path.relpath(os.path.join(root, f), BASE_DIR)
                urls_files.append(path)
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                        content = file.read()
                        matches = route_patterns.findall(content)
                        total_routes += len(matches)
                except Exception:
                    pass

    details = [
        f"Archivos urls.py mapeados: {len(urls_files)}",
        f"Rutas/endpoints totales definidos en el servidor: {total_routes}"
    ]
    for url_file in urls_files:
        details.append(f"  - .\\{url_file}")
        
    if len(urls_files) > 0 and total_routes > 0:
        return {
            "status": "GREEN",
            "score": 100,
            "msg": f"Enrutamiento correcto mediante urls.py centralizado y modular en Django.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": 0,
            "msg": "No se encontraron definiciones de urls.py ni rutas.",
            "details": details
        }

def check_api_consumption():
    """
    Punto 3: Consume los servicios API REST, manejando estados de carga y errores de conexión.
    Analiza llamadas fetch, axios o $.ajax en JS y requests en Python, y la captura de excepciones/errores.
    """
    fetch_pattern = re.compile(r'\bfetch\s*\(')
    ajax_pattern = re.compile(r'\$\.ajax|\$\.get|\$\.post|\$\.getJSON')
    catch_pattern = re.compile(r'\.catch\s*\(|try\s*\{[\s\S]*?\}\s*catch')
    loading_pattern = re.compile(r'Cargando|cargando|loading|spinner|spinner-border|disabled\s*=\s*true')
    
    py_request_pattern = re.compile(r'\brequests\.(get|post|put|delete|patch)\s*\(')
    py_except_pattern = re.compile(r'except\s+.*RequestException|except\s+Exception')

    api_detections = []
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, BASE_DIR)
            if f.endswith('.js'):
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        fetches = len(fetch_pattern.findall(content))
                        ajaxes = len(ajax_pattern.findall(content))
                        catches = len(catch_pattern.findall(content))
                        has_loading = bool(loading_pattern.search(content))
                        
                        if fetches > 0 or ajaxes > 0:
                            api_detections.append({
                                "file": f".\\{rel_path}",
                                "type": "Frontend JS",
                                "calls": fetches + ajaxes,
                                "catches": catches,
                                "loading_state": has_loading,
                                "handled": catches >= (fetches + ajaxes)
                            })
                except Exception:
                    pass
            elif f.endswith('.py'):
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        reqs = len(py_request_pattern.findall(content))
                        exceptions = len(py_except_pattern.findall(content))
                        if reqs > 0:
                            api_detections.append({
                                "file": f".\\{rel_path}",
                                "type": "Backend Python",
                                "calls": reqs,
                                "catches": exceptions,
                                "loading_state": True, # Backend processes synchronously or throws
                                "handled": exceptions > 0
                            })
                except Exception:
                    pass

    details = []
    total_calls = 0
    handled_calls = 0
    
    for det in api_detections:
        total_calls += det["calls"]
        status_txt = "Con manejo de errores" if det["handled"] else "SIN manejo de errores"
        loading_txt = "y estado de carga" if det["loading_state"] else "sin estado de carga"
        details.append(f"  - {det['file']} ({det['type']}): {det['calls']} llamadas ({status_txt} {loading_txt})")
        if det["handled"]:
            handled_calls += 1

    if not api_detections:
        return {
            "status": "YELLOW",
            "score": 60,
            "msg": "No se detectó un consumo masivo de APIs externas en JS/Python. (Ej: Se encontró integración de paises_ciudades.js de forma parcial).",
            "details": ["Considera integrar servicios backend JSON REST si el proyecto lo requiere."]
        }
        
    success_rate = handled_calls / len(api_detections)
    
    if success_rate >= 0.8:
        return {
            "status": "GREEN",
            "score": 100,
            "msg": "Excelente. Se consumen APIs y se manejan correctamente los errores de conexión y estados de carga.",
            "details": details
        }
    else:
        return {
            "status": "YELLOW",
            "score": 70,
            "msg": "Consumo de API detectado, pero algunas llamadas carecen de captura de errores o estados de carga.",
            "details": details
        }

def check_styles_bem():
    """
    Punto 4: Aplica estilos CSS o preprocesadores bajo el esquema de diseño atómico o metodología BEM.
    Analiza archivos CSS en busca de BEM (.block__elem o .block--mod) y uso de clases utilitarias de Bootstrap.
    Detecta también estilos en línea (style="") que violan BEM/Atomic design.
    """
    css_files = []
    inline_styles = 0
    bem_classes = 0
    bootstrap_utilities = 0
    inline_styles_by_file = {}
    
    bem_pattern = re.compile(r'\.[a-zA-Z0-9_-]+__[a-zA-Z0-9_-]+|\.[a-zA-Z0-9_-]+--[a-zA-Z0-9_-]+')
    inline_style_pattern = re.compile(r'\bstyle\s*=\s*["\'][^"\']*["\']')
    bootstrap_class_pattern = re.compile(r'\bclass\s*=\s*["\'][^"\']*(col-|row|d-flex|d-grid|bg-|text-|shadow-|rounded-|p-|m-)[^"\']*["\']')

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith('.css'):
                css_files.append(f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        bem_classes += len(bem_pattern.findall(content))
                except Exception:
                    pass
            elif f.endswith('.html') and f != 'reporte_rubrica.html':
                try:
                    rel_path = os.path.relpath(path, BASE_DIR)
                    with open(path, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                        file_inline_lines = []
                        for idx, line in enumerate(lines, start=1):
                            matches = inline_style_pattern.findall(line)
                            if matches:
                                inline_styles += len(matches)
                                file_inline_lines.append(idx)
                        
                        content = "".join(lines)
                        bootstrap_utilities += len(bootstrap_class_pattern.findall(content))
                        
                        if file_inline_lines:
                            inline_styles_by_file[rel_path] = file_inline_lines
                except Exception:
                    pass

    details = [
        f"Archivos CSS en la carpeta estática: {len(css_files)}",
        f"Selectores con estructura BEM (__ o --) detectados: {bem_classes}",
        f"Estructuras de diseño atómico (clases utilitarias Bootstrap): {bootstrap_utilities}",
        f"Estilos en línea (style='...') en HTML: {inline_styles} (se sugiere minimizarlos)"
    ]

    if inline_styles_by_file:
        details.append("Estilos en línea detectados por archivo:")
        for rel_file, lines_list in sorted(inline_styles_by_file.items()):
            lines_str = ", ".join(map(str, lines_list))
            details.append(f"  - {rel_file}: líneas {lines_str}")

    score = 100
    if inline_styles > 20:
        score -= min(30, int(inline_styles / 2))
        
    if bootstrap_utilities > 100 or bem_classes > 5:
        status = "GREEN"
        msg = "Diseño atómico basado en Bootstrap 5 / metodología BEM aplicado de forma general."
    else:
        status = "YELLOW"
        msg = "Metodología CSS poco clara. Se detecta alta dependencia de estilos por defecto o en línea."
        
    return {
        "status": status,
        "score": max(50, score),
        "msg": msg,
        "details": details
    }

def check_data_binding():
    """
    Punto 5: Realiza el binding de datos bidireccional o unidireccional reactivo.
    Analiza manipulación dinámica y enlaces de eventos del DOM en archivos JS.
    """
    dom_writes = 0
    change_listeners = 0
    js_files_scanned = 0
    
    dom_write_patterns = [
        re.compile(r'\.innerHTML\b'),
        re.compile(r'\.innerText\b'),
        re.compile(r'\.textContent\b'),
        re.compile(r'\.value\s*='),
        re.compile(r'\.html\s*\('),
        re.compile(r'\.text\s*\('),
        re.compile(r'\.val\s*\('),
        re.compile(r'\.appendChild\s*\('),
        re.compile(r'\.replaceChild\s*\(')
    ]
    
    listener_patterns = [
        re.compile(r'\.addEventListener\s*\(\s*[\'"](change|input|keyup|click|submit)[\'"]'),
        re.compile(r'\.on\s*\(\s*[\'"](change|input|keyup|click|submit)[\'"]')
    ]
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f.endswith('.js'):
                js_files_scanned += 1
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        for pat in dom_write_patterns:
                            dom_writes += len(pat.findall(content))
                        for pat in listener_patterns:
                            change_listeners += len(pat.findall(content))
                except Exception:
                    pass

    details = [
        f"Archivos JavaScript escaneados: {js_files_scanned}",
        f"Escrituras dinámicas en el DOM (binding de salida): {dom_writes}",
        f"Escuchadores de eventos de entrada (binding de entrada): {change_listeners}"
    ]

    if dom_writes > 5 and change_listeners > 2:
        return {
            "status": "GREEN",
            "score": 100,
            "msg": "Data binding unidireccional/bidireccional reactivo manejado mediante JS y listeners de eventos del DOM.",
            "details": details
        }
    elif dom_writes > 0:
        return {
            "status": "YELLOW",
            "score": 75,
            "msg": "Data binding básico detectado, pero podría ser más dinámico o estructurado.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": 30,
            "msg": "Poca interacción reactiva del DOM mediante JavaScript.",
            "details": details
        }

def check_form_validation():
    """
    Punto 6: Valida las entradas del usuario en formularios.
    Analiza formularios Django (forms.py), validaciones backend (is_valid) y frontend (atributos HTML5 required/pattern o JS).
    """
    html5_validation_attrs = 0
    django_forms = []
    is_valid_calls = 0
    
    val_attrs = ['required', 'pattern=', 'minlength=', 'maxlength=', 'type="email"', 'type="number"']
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith('.html') and f != 'reporte_rubrica.html':
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        for attr in val_attrs:
                            html5_validation_attrs += content.count(attr)
                except Exception:
                    pass
            elif f == 'forms.py':
                django_forms.append(os.path.relpath(path, BASE_DIR))
            elif f.endswith('.py'):
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        is_valid_calls += content.count('.is_valid()')
                except Exception:
                    pass
                    
    details = [
        f"Formularios de Django estructurados (forms.py): {len(django_forms)}",
        f"Llamadas a validación segura en vistas (.is_valid()): {is_valid_calls}",
        f"Atributos de validación HTML5 en plantillas frontend: {html5_validation_attrs}"
    ]
    for form in django_forms:
        details.append(f"  - .\\{form}")

    score = 0
    if len(django_forms) > 0 and is_valid_calls > 0:
        score += 60
    if html5_validation_attrs > 15:
        score += 40
        
    score = min(100, score)
    
    if score >= 90:
        return {
            "status": "GREEN",
            "score": score,
            "msg": "Cumplido. Se realizan validaciones robustas tanto en backend (Django Forms) como en frontend.",
            "details": details
        }
    elif score >= 50:
        return {
            "status": "YELLOW",
            "score": score,
            "msg": "Formularios con validaciones básicas. Asegúrate de verificar siempre is_valid() en las vistas post.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": score,
            "msg": "Faltan esquemas de validación de formularios robustos.",
            "details": details
        }

def check_env_variables():
    """
    Punto 7: Utiliza variables de entorno para la configuración de las URLs y datos sensibles.
    Busca archivos .env y analiza si hay credenciales o secretos persistidos en el código (settings.py).
    """
    env_exists = os.path.exists(os.path.join(BASE_DIR, '.env')) or os.path.exists(os.path.join(BASE_DIR, '.env.example'))
    os_getenv_count = 0
    decouple_count = 0
    dotenv_config_detected = False
    hardcoded_secrets = []
    
    secret_key_hardcoded = re.compile(r'SECRET_KEY\s*=\s*[\'"][^\'"]*django-insecure[^\'"]*[\'"]')
    email_pass_hardcoded = re.compile(r'EMAIL_HOST_PASSWORD\s*=\s*[\'"](?![$\{\s])[^\'"]+[\'"]')
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith('.py'):
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        os_getenv_count += len(re.findall(r'os\.getenv|os\.environ', content))
                        decouple_count += len(re.findall(r'\bconfig\s*\(', content))
                        
                        if 'load_dotenv' in content or 'dotenv.load_dotenv' in content:
                            dotenv_config_detected = True
                        
                        if f == 'settings.py':
                            if secret_key_hardcoded.search(content):
                                hardcoded_secrets.append("SECRET_KEY expuesta en settings.py")
                            if email_pass_hardcoded.search(content):
                                hardcoded_secrets.append("EMAIL_HOST_PASSWORD expuesta en settings.py")
                except Exception:
                    pass

    env_configured = env_exists or dotenv_config_detected

    details = [
        f"Archivo .env o .env.example presente: {'Sí' if env_exists else 'No (pero se detectó configuración de dotenv en código)' if dotenv_config_detected else 'No'}",
        f"Llamadas a variables de entorno en código (os.getenv/decouple): {os_getenv_count + decouple_count}"
    ]
    
    if hardcoded_secrets:
        for secret in hardcoded_secrets:
            details.append(f"  [ALERTA] Credencial expuesta: {secret}")

    score = 100
    if not env_configured:
        score -= 40
    if hardcoded_secrets:
        score -= 50
        
    score = max(0, score)
    
    if score >= 90:
        return {
            "status": "GREEN",
            "score": score,
            "msg": "Perfecto. Configuración limpia basada en variables de entorno sin datos sensibles expuestos.",
            "details": details
        }
    elif score >= 50:
        return {
            "status": "YELLOW",
            "score": score,
            "msg": "Advertencia: Se detectan datos sensibles persistidos de forma directa en settings.py (ej. contraseñas de email o claves de desarrollo). Múdalos a un archivo .env.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": score,
            "msg": "Datos sensibles expuestos críticamente en el repositorio. Falta el uso de variables de entorno.",
            "details": details
        }

def check_hierarchy():
    """
    Punto 8: Organiza el código fuente en una jerarquía de carpetas lógica.
    Verifica la convención del framework (Modelos, Vistas, Controladores/Urls, Assets y Templates).
    """
    categories = {
        'vistas (views.py)': 0,
        'modelos (models.py)': 0,
        'formularios (forms.py)': 0,
        'rutas (urls.py)': 0,
        'plantillas (.html)': 0,
        'recursos estaticos (.css/.js)': 0,
        'tests (tests.py)': 0
    }
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f == 'views.py':
                categories['vistas (views.py)'] += 1
            elif f == 'models.py':
                categories['modelos (models.py)'] += 1
            elif f == 'forms.py':
                categories['formularios (forms.py)'] += 1
            elif f == 'urls.py':
                categories['rutas (urls.py)'] += 1
            elif f.endswith('.html') and f != 'reporte_rubrica.html':
                categories['plantillas (.html)'] += 1
            elif f.endswith(('.css', '.js')):
                categories['recursos estaticos (.css/.js)'] += 1
            elif f.endswith('.py') and ('test' in f or f == 'tests.py'):
                categories['tests (tests.py)'] += 1

    details = []
    for cat, count in categories.items():
        details.append(f"  - {cat}: {count}")

    # Verificar separación lógica del patrón Django
    has_mvt = categories['modelos (models.py)'] > 0 and categories['vistas (views.py)'] > 0 and categories['plantillas (.html)'] > 0
    
    if has_mvt and categories['recursos estaticos (.css/.js)'] > 0:
        return {
            "status": "GREEN",
            "score": 100,
            "msg": "Estructura de directorios altamente organizada bajo el estándar de aplicaciones Django MVT.",
            "details": details
        }
    else:
        return {
            "status": "YELLOW",
            "score": 70,
            "msg": "Estructura de carpetas básica. Asegúrate de separar adecuadamente los archivos estáticos de las plantillas.",
            "details": details
        }

def check_unit_tests():
    """
    Punto 9: Implementa pruebas unitarias básicas sobre los componentes.
    Busca archivos de pruebas de Django (tests.py, test_*.py) y el conteo de assertions.
    """
    test_files = []
    test_cases = 0
    test_methods = 0
    
    case_pat = re.compile(r'class\s+(?:\w*(?:TestCase|Tests|Test)\w*\s*\(|\w+\s*\([^)]*(?:TestCase|Tests|Test))')
    method_pat = re.compile(r'\bdef\s+test_\w+\s*\(')
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f.endswith('.py') and ('test' in f or f == 'tests.py'):
                path = os.path.join(root, f)
                rel = os.path.relpath(path, BASE_DIR)
                test_files.append(rel)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        test_cases += len(case_pat.findall(content))
                        test_methods += len(method_pat.findall(content))
                except Exception:
                    pass

    details = [
        f"Archivos de prueba detectados: {len(test_files)}",
        f"Clases de Test definidos: {test_cases}",
        f"Funciones de prueba (test_*): {test_methods}"
    ]
    for test in test_files:
        details.append(f"  - .\\{test}")

    if test_methods >= 10:
        return {
            "status": "GREEN",
            "score": 100,
            "msg": f"¡Excelente cobertura de pruebas! Se encontraron {test_methods} métodos de prueba estructurados.",
            "details": details
        }
    elif test_methods > 0:
        return {
            "status": "YELLOW",
            "score": 75,
            "msg": f"Pruebas unitarias básicas detectadas ({test_methods} tests). Considera ampliar la cobertura.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": 0,
            "msg": "No se encontraron archivos de pruebas unitarias implementadas.",
            "details": details
        }

def check_load_optimization():
    """
    Punto 10: Optimiza el rendimiento mediante lazy loading o code splitting.
    Busca atributos lazy loading en imágenes/iframe, defer/async en scripts y carga selectiva.
    """
    lazy_images = 0
    defer_async_scripts = 0
    
    lazy_pattern = re.compile(r'\bloading\s*=\s*["\']lazy["\']')
    script_opt_pattern = re.compile(r'<script[^>]*\b(async|defer)\b[^>]*>')
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f.endswith('.html') and f != 'reporte_rubrica.html':
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        lazy_images += len(lazy_pattern.findall(content))
                        defer_async_scripts += len(script_opt_pattern.findall(content))
                except Exception:
                    pass

    details = [
        f"Imágenes o recursos con carga diferida (loading='lazy'): {lazy_images}",
        f"Uso de scripts asíncronos o diferidos (async/defer): {defer_async_scripts}"
    ]

    score = 50
    if lazy_images > 0:
        score += 25
    if defer_async_scripts > 0:
        score += 25
        
    if score >= 90:
        return {
            "status": "GREEN",
            "score": score,
            "msg": "Técnicas de carga diferida (lazy loading) e importación asíncrona de recursos implementadas correctamente.",
            "details": details
        }
    elif score >= 75:
        return {
            "status": "YELLOW",
            "score": score,
            "msg": "Optimización parcial. Añade loading='lazy' en imágenes pesadas de tus catálogos o galerías.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": score,
            "msg": "Ausencia de optimizaciones de rendimiento de carga en el frontend.",
            "details": details
        }
def check_documentation():
    """
    Punto 11: Documenta los componentes mediante JSDoc o docstrings descriptivos.
    Busca bloques de comentarios de documentacion JSDoc (/** ... */) y docstrings de Python (triple comilla doble).
    """
    docstrings = 0
    jsdocs = 0
    py_files = 0
    js_files = 0
    
    docstring_pattern = re.compile(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'')
    jsdoc_pattern = re.compile(r'/\*\*[\s\S]*?\*/')

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith('.py'):
                py_files += 1
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        docstrings += len(docstring_pattern.findall(content))
                except Exception:
                    pass
            elif f.endswith('.js'):
                js_files += 1
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        jsdocs += len(jsdoc_pattern.findall(content))
                except Exception:
                    pass

    details = [
        f"Archivos de código escaneados: {py_files} Python, {js_files} JavaScript",
        f"Docstrings de documentación en Python: {docstrings}",
        f"Comentarios estilo JSDoc en JavaScript: {jsdocs}"
    ]

    coverage = (docstrings + jsdocs) / max(1, py_files + js_files)
    
    if coverage >= 1.0:
        return {
            "status": "GREEN",
            "score": 100,
            "msg": "Código fuente ampliamente documentado con estándares JSDoc y Docstrings descriptivos.",
            "details": details
        }
    elif coverage >= 0.4:
        return {
            "status": "YELLOW",
            "score": 80,
            "msg": "Nivel de documentación adecuado, pero se recomienda documentar clases y funciones complejas.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": 40,
            "msg": "Bajo nivel de documentación en el código fuente.",
            "details": details
        }

def check_responsiveness():
    """
    Punto 12: Garantiza la adaptabilidad de la interfaz (responsive design).
    Busca @media queries en CSS y grillas responsivas (col-, row, d-flex) en HTML templates.
    """
    media_queries = 0
    grid_classes = 0
    
    media_pattern = re.compile(r'@media\b')
    grid_pattern = re.compile(r'\bclass\s*=\s*["\'][^"\']*(col-|row|d-flex|d-grid|flex-wrap|col-sm-|col-md-|col-lg-)[^"\']*["\']')

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith('.css'):
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        media_queries += len(media_pattern.findall(content))
                except Exception:
                    pass
            elif f.endswith('.html') and f != 'reporte_rubrica.html':
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        grid_classes += len(grid_pattern.findall(content))
                except Exception:
                    pass

    details = [
        f"Media Queries detectadas en hojas de estilo CSS: {media_queries}",
        f"Uso de contenedores y rejillas responsivas (Bootstrap Grid/Flexbox): {grid_classes}"
    ]

    if media_queries > 0 or grid_classes > 30:
        return {
            "status": "GREEN",
            "score": 100,
            "msg": "Diseño completamente responsivo y adaptable mediante Bootstrap Grid y consultas de medios CSS.",
            "details": details
        }
    elif grid_classes > 0:
        return {
            "status": "YELLOW",
            "score": 75,
            "msg": "Diseño responsivo parcial. Valida la adaptabilidad de todas las vistas en dispositivos móviles.",
            "details": details
        }
    else:
        return {
            "status": "RED",
            "score": 30,
            "msg": "Se detectaron pocas estructuras responsivas en las vistas del proyecto.",
            "details": details
        }


def exportar_pdf(resultados, average_score, estado_final):
    """
    Genera un archivo HTML de reporte y lo compila a PDF usando xhtml2pdf.
    """
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reporte de Auditoria de Calidad - Proyecto {PROJECT_NAME}</title>
    <style>
        @page {{
            size: letter;
            margin: 0.8in;
            @frame footer_frame {{
                -pdf-frame-content: footer_content;
                bottom: 0.4in;
                left: 0.8in;
                width: 6.9in;
                height: 0.3in;
            }}
        }}
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: #334155;
            font-size: 10pt;
            line-height: 1.4;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #10b981;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 20pt;
            font-weight: bold;
            color: #0f766e;
            margin: 0;
        }}
        .subtitle {{
            font-size: 11pt;
            color: #64748b;
            margin: 5px 0 0 0;
        }}
        .summary-box {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .summary-table {{
            width: 100%;
        }}
        .summary-table td {{
            padding: 5px;
            vertical-align: middle;
        }}
        .score-large {{
            font-size: 26pt;
            font-weight: bold;
            color: #0f766e;
            text-align: center;
        }}
        .status-badge {{
            font-weight: bold;
            text-align: center;
            font-size: 12pt;
            padding: 6px;
            border-radius: 4px;
        }}
        .status-GREEN {{ color: #047857; background-color: #d1fae5; }}
        .status-YELLOW {{ color: #b45309; background-color: #fef3c7; }}
        .status-RED {{ color: #b91c1c; background-color: #fee2e2; }}
        
        .point-card {{
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            margin-bottom: 15px;
            padding: 10px;
        }}
        .point-header-table {{
            width: 100%;
            border-bottom: 1px solid #f1f5f9;
            margin-bottom: 5px;
        }}
        .point-header-table td {{
            padding: 3px 0;
            vertical-align: middle;
        }}
        .point-title {{
            font-size: 11pt;
            font-weight: bold;
            color: #1e293b;
        }}
        .point-score {{
            text-align: right;
            font-weight: bold;
            font-size: 11pt;
        }}
        .score-val-GREEN {{ color: #047857; }}
        .score-val-YELLOW {{ color: #b45309; }}
        .score-val-RED {{ color: #b91c1c; }}
        
        .point-desc {{
            font-style: italic;
            color: #475569;
            margin-bottom: 6px;
            font-size: 9.5pt;
        }}
        .metrics-list {{
            margin: 0;
            padding-left: 20px;
            color: #334155;
            font-size: 9pt;
        }}
        .footer {{
            font-size: 8pt;
            color: #94a3b8;
            text-align: center;
        }}
        .sugerencias-box {{
            background-color: #fffbeb;
            border: 1px solid #fef3c7;
            border-radius: 6px;
            padding: 12px;
            margin-top: 20px;
        }}
        .sugerencias-title {{
            font-weight: bold;
            color: #b45309;
            margin-bottom: 5px;
            font-size: 11pt;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">REPORTE DE AUDITORIA TECNICA</div>
        <div class="subtitle">Evaluacion de Calidad - Proyecto {PROJECT_NAME}</div>
    </div>
    
    <div class="summary-box">
        <table class="summary-table">
            <tr>
                <td width="35%">
                    <div class="score-large">{average_score} / 100</div>
                    <div style="text-align: center; color: #64748b; font-size: 9pt;">PUNTUACION GLOBAL</div>
                </td>
                <td width="65%">
                    <div class="status-badge status-{estado_final['status']}">
                        ESTADO: {estado_final['name']}
                    </div>
                    <div style="margin-top: 10px; font-size: 9.5pt;">
                        Este reporte autoevalua el cumplimiento del proyecto frente a los 12 puntos de control de la rubrica tecnica de desarrollo (Frontend y Backend).
                    </div>
                </td>
            </tr>
        </table>
    </div>
    
    <h3 style="color: #0f766e; border-bottom: 1px solid #cbd5e1; padding-bottom: 3px; margin-bottom: 10px;">DETALLE DE EVALUACION</h3>
"""

    for i, p in enumerate(resultados, start=1):
        status_color = p['status']
        details_html = ""
        if p['details']:
            details_html = '<ul class="metrics-list">'
            for d in p['details']:
                escaped_d = d.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                details_html += f"<li>{escaped_d}</li>"
            details_html += '</ul>'
            
        html_content += f"""
    <div class="point-card">
        <table class="point-header-table">
            <tr>
                <td class="point-title" width="80%">{i}. {p['name']}</td>
                <td class="point-score score-val-{status_color}" width="20%">{p['score']} / 100</td>
            </tr>
        </table>
        <div class="point-desc">{p['msg']}</div>
        {details_html}
    </div>
"""

    # Add recommendations dynamically based on scores less than 100
    sugerencias = [p['suggestion'] for p in resultados if p['score'] < 100 and p.get('suggestion')]
    if sugerencias:
        sugerencias_items = "\n".join([f"            <li>{sug}</li>" for sug in sugerencias])
        sugerencias_html = f"""
    <div class="sugerencias-box">
        <div class="sugerencias-title">RECOMENDACIONES CLAVE PARA MEJORA:</div>
        <ul style="margin: 0; padding-left: 20px; font-size: 9pt; color: #78350f;">
{sugerencias_items}
        </ul>
    </div>
"""
    else:
        sugerencias_html = """
    <div class="sugerencias-box" style="background-color: #ecfdf5; border: 1px solid #a7f3d0;">
        <div class="sugerencias-title" style="color: #065f46;">¡FELICITACIONES!</div>
        <div style="font-size: 9pt; color: #065f46; margin: 0; padding: 0;">El proyecto cumple al 100% con todos los puntos evaluados de la rubrica.</div>
    </div>
"""

    html_content += f"""
    {sugerencias_html}
    
    <div id="footer_content" class="footer">
        Reporte generado automaticamente - Proyecto {PROJECT_NAME} &bull; Pagina <pdf:pagenumber> de <pdf:pagecount>
    </div>
</body>
</html>
"""
    
    # Save HTML file
    html_path = os.path.join(BASE_DIR, "reporte_rubrica.html")
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Reporte HTML guardado en: {html_path}")
    except Exception as e:
        print(f"Error al escribir HTML: {e}")
        
    # Convert to PDF
    pdf_path = os.path.join(BASE_DIR, "reporte_rubrica.pdf")
    try:
        from xhtml2pdf import pisa
        with open(pdf_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
            if not pisa_status.err:
                print(f"Reporte PDF generado exitosamente: {pdf_path}")
                return True
            else:
                print("Error de conversion en xhtml2pdf.")
    except ImportError:
        print("\n[INFO] xhtml2pdf no esta instalado en este entorno python.")
        print("Para generar el PDF directamente, instala xhtml2pdf: pip install xhtml2pdf")
        print("Tambien puedes abrir 'reporte_rubrica.html' en tu navegador y guardarlo como PDF.")
    except Exception as e:
        print(f"Error inesperado al generar PDF: {e}")
    return False


# ────────────────────────────────────────────────────────
# Ejecución y Reporte Final
# ────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(f"{BOLD}{WHITE}AUDITORÍA TÉCNICA DE CALIDAD - PROYECTO {PROJECT_NAME.upper()}{RESET}")
    print("Evaluando cumplimiento de los 12 puntos de desarrollo frontend/backend...")
    print("=" * 70)
    
    puntos = [
        ("1. Estructura de Componentes de Interfaz (Plantillas)", check_ui_structure),
        ("2. Enrutamiento de vistas y módulos", check_routing),
        ("3. Consumo de API REST, carga y errores", check_api_consumption),
        ("4. Estilos y metodologías CSS (BEM / Atómico)", check_styles_bem),
        ("5. Binding de datos reactivo y DOM", check_data_binding),
        ("6. Validación de formularios", check_form_validation),
        ("7. Configuración limpia por Variables de Entorno", check_env_variables),
        ("8. Jerarquía y organización del código fuente", check_hierarchy),
        ("9. Pruebas unitarias sobre componentes", check_unit_tests),
        ("10. Optimización de carga (Lazy loading / split)", check_load_optimization),
        ("11. Documentación (JSDoc / Comentarios)", check_documentation),
        ("12. Adaptabilidad de la interfaz (Responsive)", check_responsiveness)
    ]
    
    total_score = 0
    scores_list = []
    resultados_reporte = []
    
    for i, (name, check_fn) in enumerate(puntos, start=1):
        res = check_fn()
        scores_list.append(res["score"])
        total_score += res["score"]
        res["suggestion"] = SUGERENCIAS_MAP.get(i, "")
        
        # Si el puntaje es menor a 100, marcar como RED
        if res["score"] < 100:
            res["status"] = "RED"
            
        # Color y símbolo según estado
        if res["status"] == "GREEN":
            color = GREEN
            sym = "✔ [CUMPLIDO]"
        elif res["status"] == "YELLOW":
            color = YELLOW
            sym = "⚠ [CON ADVERTENCIAS]"
        else:
            color = RED
            sym = "✖ [NO CUMPLIDO]"
            
        print_colored(f"\n{BOLD}{i}. {name}{RESET}", WHITE)
        print_colored(f"   Estado: {sym} (Puntaje: {res['score']}/100)", color)
        print(f"   Detalle: {res['msg']}")
        if res["details"]:
            print("   Métricas y Hallazgos:")
            for detail in res["details"]:
                print(f"     {detail}")
                
        resultados_reporte.append({
            "name": name,
            "score": res["score"],
            "status": res["status"],
            "msg": res["msg"],
            "details": res["details"],
            "suggestion": res["suggestion"]
        })
                
    average_score = int(total_score / len(puntos))
    
    print("\n" + "=" * 70)
    print(f"{BOLD}{WHITE}RESUMEN DE EVALUACIÓN GLOBAL{RESET}")
    print("=" * 70)
    print(f"  Puntaje Promedio: {average_score}/100")
    
    if average_score >= 90:
        estado_final_lbl = "EXCELENTE / LISTO PARA ENTREGA"
        estado_final_status = "GREEN"
        print_colored("  ESTADO FINAL: EXCELENTE / LISTO PARA ENTREGA ✔", GREEN)
    elif average_score >= 70:
        estado_final_lbl = "ACEPTABLE CON DETALLES POR CORREGIR"
        estado_final_status = "YELLOW"
        print_colored("  ESTADO FINAL: ACEPTABLE CON DETALLES POR CORREGIR ⚠", YELLOW)
    else:
        estado_final_lbl = "REQUIERE MEJORAS CRÍTICAS ANTES DE LA ENTREGA"
        estado_final_status = "RED"
        print_colored("  ESTADO FINAL: REQUIERE MEJORAS CRÍTICAS ANTES DE LA ENTREGA ✖", RED)
        
    estado_final = {
        "name": estado_final_lbl,
        "status": estado_final_status
    }
        
    print("=" * 70)
    print("Sugerencias clave:")
    sugerencias = [p['suggestion'] for p in resultados_reporte if p['score'] < 100 and p.get('suggestion')]
    if sugerencias:
        for idx, sug in enumerate(sugerencias, start=1):
            print(f"  {idx}. {sug}")
    else:
        print_colored("  ¡Excelente! Todos los puntos de control están al 100%. No hay sugerencias pendientes.", GREEN)
    print("=" * 70)
    
    # Generar Reportes PDF e HTML
    print("\nExportando reportes...")
    exportar_pdf(resultados_reporte, average_score, estado_final)
    print("=" * 70)

if __name__ == '__main__':
    main()
