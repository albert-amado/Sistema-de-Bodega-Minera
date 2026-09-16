import os
import re

print("=== AUDITORIA DE CSRF Y FORMULARIOS HTML ===")
found = 0
for root, dirs, files in os.walk('.'):
    if any(x in root for x in ['.venv', '.git']):
        continue
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            forms = re.findall(r'<form[\s\S]*?</form>', content, re.IGNORECASE)
            for form in forms:
                if re.search(r'method=[\'"]?post', form, re.IGNORECASE):
                    if '{% csrf_token %}' not in form and '{{ csrf_token }}' not in form:
                        print(f"[ALERTA CSRF] Falta CSRF en {path}:\n{form[:120]}...\n")
                        found += 1
if found == 0:
    print("[OK] Todos los formularios POST tienen token CSRF.")
