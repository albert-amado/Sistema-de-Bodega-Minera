import os
import ast
import argparse

STATUS_FIELDS = {'estado', 'estado_registro', 'activo', 'disponible', 'status', 'active', 'is_active'}

def extract_model_status_fields(filepath):
    """
    Parses a models.py file and returns a dictionary mapping ModelName -> set(status_field_names)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return {}

    models_found = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it is a Django model
            is_model = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'Model':
                    is_model = True
                elif isinstance(base, ast.Attribute) and base.attr == 'Model':
                    is_model = True

            # If not explicitly inheriting from Model, look for field assignments as a heuristic
            if not is_model:
                for subnode in node.body:
                    if isinstance(subnode, ast.Assign) and isinstance(subnode.value, ast.Call):
                        func = subnode.value.func
                        func_name = ""
                        if isinstance(func, ast.Name):
                            func_name = func.id
                        elif isinstance(func, ast.Attribute):
                            func_name = func.attr
                        if func_name.endswith('Field') or func_name in ('ForeignKey', 'ManyToManyField', 'OneToOneField'):
                            is_model = True
                            break

            if not is_model:
                continue

            # Walk through assignments to find fields in STATUS_FIELDS
            status_fields = set()
            for subnode in node.body:
                if isinstance(subnode, ast.Assign):
                    for target in subnode.targets:
                        if isinstance(target, ast.Name):
                            field_name = target.id
                            if field_name in STATUS_FIELDS:
                                # Ensure it's a model field call
                                val = subnode.value
                                if isinstance(val, ast.Call):
                                    func = val.func
                                    func_name = ""
                                    if isinstance(func, ast.Name):
                                        func_name = func.id
                                    elif isinstance(func, ast.Attribute):
                                        func_name = func.attr
                                    if func_name.endswith('Field') or func_name in ('ForeignKey', 'ManyToManyField', 'OneToOneField'):
                                        status_fields.add(field_name)

            models_found[node.name] = status_fields

    return models_found


def process_forms_file(filepath, all_model_status_fields):
    """
    Parses a forms.py file and checks for status fields in creation forms.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []

    violations = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_model_form = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'ModelForm':
                    is_model_form = True
                elif isinstance(base, ast.Attribute) and base.attr == 'ModelForm':
                    is_model_form = True
            
            if not is_model_form and node.name.endswith('Form'):
                for subnode in node.body:
                    if isinstance(subnode, ast.ClassDef) and subnode.name == 'Meta':
                        is_model_form = True
                        break

            if not is_model_form:
                continue

            # Skip explicit Edit, Update, Filtro, Search, Filter forms
            class_name_lower = node.name.lower()
            if any(term in class_name_lower for term in ('edit', 'update', 'filtro', 'search', 'filter')):
                continue

            # Find Meta class and extract fields and model
            meta_node = None
            for subnode in node.body:
                if isinstance(subnode, ast.ClassDef) and subnode.name == 'Meta':
                    meta_node = subnode
                    break

            model_name = None
            fields_list = []
            is_all_fields = False
            fields_lineno = None

            if meta_node:
                for subnode in meta_node.body:
                    if isinstance(subnode, ast.Assign):
                        for target in subnode.targets:
                            if isinstance(target, ast.Name):
                                if target.id == 'model':
                                    if isinstance(subnode.value, ast.Name):
                                        model_name = subnode.value.id
                                elif target.id == 'fields':
                                    fields_lineno = subnode.lineno
                                    fields_node = subnode.value
                                    if isinstance(fields_node, (ast.List, ast.Tuple)):
                                        for elt in fields_node.elts:
                                            if isinstance(elt, ast.Constant):
                                                fields_list.append(elt.value)
                                            elif isinstance(elt, ast.Str):
                                                fields_list.append(elt.s)
                                    elif isinstance(fields_node, ast.Constant) and fields_node.value == '__all__':
                                        is_all_fields = True
                                    elif isinstance(fields_node, ast.Str) and fields_node.s == '__all__':
                                        is_all_fields = True

            # If we don't have a model, we can't check its model-level fields, but let's check class-level forms fields
            model_status_fields = all_model_status_fields.get(model_name, set()) if model_name else STATUS_FIELDS

            # Check if any model status field is present in fields_list (whether hidden or not)
            if model_name and model_name not in all_model_status_fields:
                # If model is not found in our models registry, default to STATUS_FIELDS
                model_status_fields = STATUS_FIELDS

            if is_all_fields:
                # __all__ exposes status fields if the model defines them
                matching_status_fields = model_status_fields.intersection(STATUS_FIELDS)
                if matching_status_fields:
                    violations.append({
                        'class': node.name,
                        'model': model_name,
                        'field': "fields = '__all__'",
                        'line': fields_lineno or meta_node.lineno,
                        'reason': f"expone todos los campos usando '__all__', incluyendo los de estado del modelo ({list(matching_status_fields)})"
                    })
            else:
                for f in fields_list:
                    if f in model_status_fields:
                        violations.append({
                            'class': node.name,
                            'model': model_name,
                            'field': f,
                            'line': fields_lineno or meta_node.lineno,
                            'reason': f"el campo de estado '{f}' está presente en 'fields' (debe eliminarse del formulario)"
                        })

            # Check class-level field definitions
            for subnode in node.body:
                if isinstance(subnode, ast.Assign):
                    for target in subnode.targets:
                        if isinstance(target, ast.Name) and target.id in model_status_fields:
                            violations.append({
                                'class': node.name,
                                'model': model_name,
                                'field': target.id,
                                'line': subnode.lineno,
                                'reason': f"el campo de estado '{target.id}' está declarado a nivel de clase (debe eliminarse del formulario)"
                            })

    return violations


def main():
    parser = argparse.ArgumentParser(description="Analiza los formularios Django y verifica que no expongan campos de estado/activo.")
    parser.add_argument('directory', nargs='?', default='.', help="Directorio a escanear (por defecto: actual)")
    args = parser.parse_args()

    print(f"Buscando modelos en el directorio: {os.path.abspath(args.directory)}")
    all_model_status_fields = {}
    
    # First pass: collect model fields
    for root, dirs, files in os.walk(args.directory):
        dirs[:] = [d for d in dirs if d not in ('venv', '.venv', 'env', '__pycache__', '.git', 'migrations')]
        for file in files:
            if file.endswith('.py') and 'models.py' in file:
                filepath = os.path.join(root, file)
                models_data = extract_model_status_fields(filepath)
                if models_data:
                    all_model_status_fields.update(models_data)

    print(f"Modelos registrados con campos de estado: {len(all_model_status_fields)}")
    for model_name, fields in all_model_status_fields.items():
        if fields:
            print(f"  - {model_name}: {list(fields)}")
            
    print("-" * 75)
    print("Escaneando formularios...")
    print("-" * 75)

    total_files_scanned = 0
    total_violations = 0

    # Second pass: check forms
    for root, dirs, files in os.walk(args.directory):
        dirs[:] = [d for d in dirs if d not in ('venv', '.venv', 'env', '__pycache__', '.git', 'migrations')]
        for file in files:
            if file.endswith('.py') and 'forms.py' in file:
                filepath = os.path.join(root, file)
                total_files_scanned += 1
                violations = process_forms_file(filepath, all_model_status_fields)
                
                if violations:
                    total_violations += len(violations)
                    for v in violations:
                        model_info = f" (Modelo: {v['model']})" if v['model'] else ""
                        print(f"[ALERTA] {filepath} | Clase: {v['class']}{model_info} | Línea {v['line']}: {v['reason']}")
                else:
                    print(f"[OK]     {filepath}: Todo correcto.")

    print("-" * 75)
    print("REPORTE FINAL (SOLO LECTURA):")
    print(f"Archivos de formularios escaneados: {total_files_scanned}")
    print(f"Campos de estado expuestos encontrados: {total_violations}")

if __name__ == "__main__":
    main()
