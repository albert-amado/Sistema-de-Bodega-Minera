import json
import logging
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# Fallback en memoria para rate-limit si la caché de Django no está disponible
_RATE_LIMIT_STORE: Dict[str, List[float]] = defaultdict(list)

# ─────────────────────────────────────────────────────────────
# 1. HABEAS DATA & ENMASCARAMIENTO (Ley 1581 de 2012)
# ─────────────────────────────────────────────────────────────
def enmascarar_datos_sensibles(texto: str) -> str:
    """
    Enmascara datos personales y sensibles antes de guardarlos en logs
    o transmitirlos a servicios externos, en cumplimiento de la Ley 1581 de 2012.
    """
    if not texto:
        return ""

    resultado = texto

    # 1. Contraseñas o claves explícitas
    resultado = re.sub(
        r'(?i)\b(clave|contrase[ñn]a|password|token)\s*[:=]\s*\S+',
        r'\1: [CONFIDENCIAL]',
        resultado
    )

    # 2. Correos electrónicos
    resultado = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        '[CORREO-ENMASCARADO]',
        resultado
    )

    # 3. Números de teléfono móvil en Colombia (inician en 3 y tienen 10 dígitos)
    resultado = re.sub(
        r'\b3\d{9}\b',
        '[TELEFONO-ENMASCARADO]',
        resultado
    )

    # 4. Números de documento de identidad (6 a 11 dígitos aislados)
    resultado = re.sub(
        r'\b\d{6,11}\b',
        '[DOCUMENTO-ENMASCARADO]',
        resultado
    )

    return resultado


# ─────────────────────────────────────────────────────────────
# 2. RATE LIMITING (Máximo 20 peticiones / minuto)
# ─────────────────────────────────────────────────────────────
def verificar_rate_limit(identificador: str, max_rpm: int = 20) -> Tuple[bool, int]:
    """
    Controla que un usuario o sesión no exceda el límite de consultas por minuto.
    Retorna (permitido: bool, segundos_restantes: int).
    """
    now = time.time()
    ventana = 60.0  # 1 minuto

    # Usar cache de Django si está configurada, sino fallback en memoria
    from django.core.cache import cache
    cache_key = f"chatbot_rl_{identificador}"

    try:
        registros = cache.get(cache_key)
        if registros is None:
            registros = []
        # Filtrar registros dentro de la ventana de 60 segundos
        registros = [t for t in registros if now - t < ventana]

        if len(registros) >= max_rpm:
            segundos_restantes = int(ventana - (now - registros[0]))
            return False, max(1, segundos_restantes)

        registros.append(now)
        cache.set(cache_key, registros, timeout=int(ventana) + 5)
        return True, 0

    except Exception:
        # Fallback local seguro en memoria
        registros = _RATE_LIMIT_STORE[identificador]
        _RATE_LIMIT_STORE[identificador] = [t for t in registros if now - t < ventana]
        registros = _RATE_LIMIT_STORE[identificador]

        if len(registros) >= max_rpm:
            segundos_restantes = int(ventana - (now - registros[0]))
            return False, max(1, segundos_restantes)

        registros.append(now)
        return True, 0


# ─────────────────────────────────────────────────────────────
# 3. CONSTRUCCIÓN DE PROMPTS Y SYSTEM INSTRUCTION
# ─────────────────────────────────────────────────────────────
INSTRUCCIONES_DEL_ASISTENTE = """Eres el asistente virtual del Sistema de Bodega Minera, una plataforma que controla inventario, préstamos, devoluciones y zonificación de herramientas para labores mineras y talleres del SENA.

Tu función es ayudar a los usuarios a entender y usar el sistema, NO a implementar código (eso lo hace el equipo de desarrollo). Responde siempre en español, de forma breve, clara y orientada a la acción.

ROLES:
- Si el usuario es "admin": puedes explicar todas las funciones (inventario, préstamos, devoluciones, almacenes/estantes, usuarios, verificación SofiaPlus, configuración de base de datos).
- Si el usuario es "usuario" (aprendiz/instructor): limita tus respuestas a lo que su rol puede hacer (consultar catálogo, solicitar préstamos, ver "Mis Préstamos", editar su perfil). Si pregunta por una función de admin, indícale amablemente que debe contactar al encargado de bodega.

CONCEPTOS CLAVE DEL SISTEMA:
- SKU: Código identificador único de cada herramienta o activo.
- Código AL-ES: Ubicación física de cada activo (ejemplo: AL1-ES02 significa Almacén 1, Estante 02).
- Estados de Préstamo: SOLICITADO, APROBADO, ENTREGADO (descuenta stock en operación atómica), DEVUELTO (cierre total), PARCIAL (devolución incompleta), RECHAZADO, CANCELADO.
- Kardex: Registro histórico de entradas, salidas y ajustes de stock.

ESTILO DE RESPUESTA:
- Máximo 3-4 líneas por respuesta, salvo que el usuario pida más detalle.
- Si no sabes algo o no está en tu conocimiento del sistema, dilo con honestidad y sugiere contactar a soporte técnico, no inventes funciones.
- Nunca pidas ni proceses contraseñas, números de documento completos u otra información sensible dentro del chat."""


def construir_system_instruction(rol_usuario: str) -> str:
    """
    Agrega la directiva de rol dinámica al system instruction para guiar
    la pertinencia de las respuestas de Gemini.
    """
    rol_normalizado = (rol_usuario or 'usuario').strip().lower()
    es_admin = rol_normalizado in ('admin', 'administrador')

    if es_admin:
        linea_rol = (
            "\n\n[CONTEXTO DE LA SESIÓN ACTUAL]: El usuario autenticado es ADMINISTRADOR (Bodeguero). "
            "Tiene privilegios completos: inventario (CRUD, ajustes de stock), gestión de préstamos y devoluciones, "
            "zonificación de almacenes y estantes, verificación de aprendices en SofiaPlus y configuración de base de datos."
        )
    else:
        linea_rol = (
            "\n\n[CONTEXTO DE LA SESIÓN ACTUAL]: El usuario autenticado es APRENDIZ / INSTRUCTOR (Rol: Usuario). "
            "SOLO tiene acceso a: consultar catálogo de herramientas, solicitar préstamos, consultar 'Mis Préstamos' "
            "y editar su propio perfil. Si consulta sobre aprobación de préstamos, altas de stock, almacenes o administración, "
            "indícale con cortesía que esa función corresponde exclusivamente al Bodeguero / Administrador."
        )

    return INSTRUCCIONES_DEL_ASISTENTE + linea_rol


# ─────────────────────────────────────────────────────────────
# 4. LLAMADA PROXY A GEMINI API (HTTP REST NATIVO)
# ─────────────────────────────────────────────────────────────
def sanitizar_mensaje_usuario(texto: Optional[str]) -> str:
    """Limpia y trunca el texto de entrada a un máximo de 500 caracteres."""
    if not texto:
        return ""
    # Quitar etiquetas HTML y caracteres de control invisibles
    limpio = re.sub(r'<[^>]*>', '', str(texto))
    limpio = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', limpio)
    return limpio.strip()[:500]


def formatear_historial(historial: Optional[List[Dict[str, str]]]) -> List[Dict]:
    """
    Mapea el historial recibido al formato requerido por Gemini API:
    [{"role": "user"|"model", "parts": [{"text": "..."}]}]
    """
    contents = []
    if not isinstance(historial, list):
        return contents

    # Limitar el historial a los últimos 6 turnos para optimizar latencia y cuota
    for item in historial[-6:]:
        if not isinstance(item, dict):
            continue
        rol = item.get('rol', '').strip().lower()
        texto = str(item.get('texto', '')).strip()
        if not texto:
            continue

        gemini_role = "user" if rol in ('user', 'usuario') else "model"
        contents.append({
            "role": gemini_role,
            "parts": [{"text": texto[:500]}]
        })

    return contents


def consultar_gemini(
    mensaje: str,
    historial: Optional[List[Dict[str, str]]] = None,
    rol_usuario: str = 'usuario'
) -> Tuple[str, Optional[int]]:
    """
    Envía la solicitud a la API de Gemini (gemini-2.5-flash) y retorna:
    (respuesta_texto, tiempo_ms)
    Maneja contingencias y fallbacks amigables sin exponer detalles técnicos.
    """
    start_time = time.time()

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
    api_key = api_key.strip()
    model = getattr(settings, 'GEMINI_MODEL', 'gemini-flash-lite-latest') or 'gemini-flash-lite-latest'

    if not api_key:
        logger.warning("Chatbot: GEMINI_API_KEY no está configurada en settings ni en .env")
        return (
            "El Asistente Virtual no tiene una clave de acceso configurada en este momento. "
            "Por favor contacta al administrador de la bodega para habilitar el servicio.",
            0
        )

    # 1. Preparar System Instruction
    system_instruction = construir_system_instruction(rol_usuario)

    # 2. Preparar Contents (Historial + Mensaje Actual)
    contents = formatear_historial(historial)
    contents.append({
        "role": "user",
        "parts": [{"text": mensaje}]
    })

    payload = {
        "contents": contents,
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 600,
            "topP": 0.8
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Sistema-Bodega-Minera-Bot/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            data = json.loads(body)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Extraer texto de la respuesta
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    texto_respuesta = parts[0].get('text', '').strip()
                    return texto_respuesta, elapsed_ms

            return (
                "No pude generar una respuesta en este momento. Por favor reformula tu consulta.",
                elapsed_ms
            )

    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Chatbot Gemini HTTPError {e.code}: {e.reason}")

        if e.code == 429:
            return (
                "El asistente se encuentra temporalmente ocupado debido a un alto volumen de consultas. "
                "Por favor intenta de nuevo en unos instantes.",
                elapsed_ms
            )
        elif e.code in (400, 403):
            return (
                "El servicio de asistencia no pudo procesar la solicitud en este momento. "
                "Por favor contacta al encargado de bodega.",
                elapsed_ms
            )
        else:
            return (
                "El servicio de asistencia no está disponible temporalmente. "
                "Por favor intenta de nuevo en un momento.",
                elapsed_ms
            )

    except urllib.error.URLError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Chatbot Gemini URLError: {e.reason}")
        return (
            "No fue posible conectar con el servicio del asistente virtual (tiempo de espera o red). "
            "Por favor verifica tu conexión o intenta más tarde.",
            elapsed_ms
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Chatbot Gemini Excepción no controlada: {str(e)}")
        return (
            "Ocurrió un inconveniente al comunicarse con el asistente. "
            "Por favor intenta de nuevo más tarde.",
            elapsed_ms
        )
