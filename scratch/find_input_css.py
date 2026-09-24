import os
import re

css_dir = 'static/css'
for root, dirs, files in os.walk(css_dir):
    for f in files:
        if f.endswith('.css'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
                matches = re.findall(r'([^{}]*input[^{}]*\{[^}]*\})', content, re.IGNORECASE)
                for m in matches:
                    if 'max-width' in m or 'width' in m:
                        print(f"File: {path}")
                        print(m.strip()[:300])
                        print("-" * 40)
