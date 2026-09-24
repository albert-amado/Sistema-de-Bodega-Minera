import json
import logging

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import ChatLog
from .services import (
    consultar_gemini,
    enmascarar_datos_sensibles,
    sanitizar_mensaje_usuario,
    verificar_rate_limit,
)

logger = logging.getLogger(__name__)


def obtener_ip_cliente(request):
    """Extrae la IP real del cliente considerando proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@require_POST
def api_chatbot_mensaje(request):
    """
    Endpoint principal para interactuar con el Asistente Virtual Gemini.
    Ruta: POST /api/chatbot/mensaje/
    """
    # 1. Verificación de autenticación por sesión
    documento = request.session.get('usuario_documento')
    if not documento:
        return JsonResponse(
            {'error': 'Sesión no válida o expirada. Inicia sesión para continuar.'},
            status=401
        )

    # 2. Obtener rol legítimo de la sesión (previene falsificación en el payload)
    rol_sesion = request.session.get('usuario_rol', 'Usuario')
    # Normalizar para el servicio ("admin" o "usuario")
    rol_para_bot = 'admin' if str(rol_sesion).lower() in ('admin', 'administrador') else 'usuario'

    # 3. Rate limiting (20 mensajes / minuto por usuario)
    max_rpm = getattr(settings, 'CHATBOT_RATE_LIMIT_RPM', 20)
    permitido, espera = verificar_rate_limit(f"user_{documento}", max_rpm=max_rpm)
    if not permitido:
        return JsonResponse(
            {
                'error': f'Has superado el límite de consultas permitidas ({max_rpm}/min). Por favor espera {espera} segundos.'
            },
            status=429
        )

    # 4. Decodificar cuerpo JSON
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {'error': 'Cuerpo de solicitud JSON inválido.'},
            status=400
        )

    mensaje_raw = data.get('mensaje', '')
    historial_raw = data.get('historial', [])

    mensaje_sanitizado = sanitizar_mensaje_usuario(mensaje_raw)
    if not mensaje_sanitizado:
        return JsonResponse(
            {'error': 'El mensaje no puede estar vacío.'},
            status=400
        )

    # 5. Consultar a Gemini API a través del servicio proxy
    respuesta, latencia_ms = consultar_gemini(
        mensaje=mensaje_sanitizado,
        historial=historial_raw,
        rol_usuario=rol_para_bot
    )

    # 6. Registrar en ChatLog respetando Ley 1581 de 2012 (Habeas Data)
    logging_habilitado = getattr(settings, 'CHATBOT_ENABLE_LOGGING', True)
    if logging_habilitado:
        try:
            mensaje_enmascarado = enmascarar_datos_sensibles(mensaje_sanitizado)
            modelo_actual = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')
            ip = obtener_ip_cliente(request)

            ChatLog.objects.create(
                usuario_documento=documento,
                usuario_rol=rol_sesion,
                mensaje_usuario=mensaje_enmascarado,
                respuesta_asistente=respuesta,
                modelo_utilizado=modelo_actual,
                ip_address=ip,
                tiempo_respuesta_ms=latencia_ms
            )
        except Exception as e:
            logger.error(f"Error al registrar ChatLog: {str(e)}")

    return JsonResponse({'respuesta': respuesta})
