import os
import sys
import django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from usuario.models import Usuario

user = Usuario.objects.filter(rol__icontains='admin').first() or Usuario.objects.first()
client = Client()
session = client.session
session['usuario_documento'] = user.numero_documento
session['usuario_nombre'] = user.nombre_completo
session['usuario_rol'] = user.rol
session['usuario_tipo_documento'] = user.tipo_documento
session.save()
client.cookies[django.conf.settings.SESSION_COOKIE_NAME] = session.session_key

response = client.get('/prestamo/', follow=True)
print("Status code:", response.status_code)
html = response.content.decode('utf-8')

# Find sfb-wrap in HTML
start = html.find('class="sfb-wrap')
if start != -1:
    print("FOUND SFB-WRAP HTML:")
    print(html[start-20:start+1200])
else:
    print("sfb-wrap not found, length:", len(html))
