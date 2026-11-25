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


def normalizar_texto_para_busqueda(texto: str) -> str:
    """Normaliza un texto eliminando tildes, signos de puntuación y espacios extras."""
    if not texto:
        return ""
    texto = texto.lower()
    reemplazos = (
        ('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'),
        ('ü', 'u'), ('ñ', 'n'), ('¿', ''), ('?', ''), ('¡', ''), ('!', ''),
        ('.', ' '), (',', ' '), (':', ' '), (';', ' '), ('-', ' '), ('_', ' '),
        ('(', ' '), (')', ' '), ('"', ' '), ("'", ' ')
    )
    for a, b in reemplazos:
        texto = texto.replace(a, b)
    return " ".join(texto.split())


def consultar_base_conocimiento_local(mensaje: str, rol_usuario: str = 'usuario') -> str:
    """
    Motor de conocimiento experto local para el Sistema de Bodega Minera.
    Proporciona respuestas precisas e inmediatas cuando la API externa no está
    configurada o no está disponible, garantizando disponibilidad 24/7.
    """
    msg_norm = normalizar_texto_para_busqueda(mensaje)
    es_admin = (rol_usuario or '').strip().lower() in ('admin', 'administrador')

    # 1. Saludos y bienvenida
    saludos = ('hola', 'buenos dias', 'buenas tardes', 'buenas noches', 'saludos', 'que puedes hacer', 'ayuda', 'quien eres', 'buenas')
    if any(msg_norm == s or msg_norm.startswith(s + ' ') for s in saludos):
        if es_admin:
            return (
                "¡Hola, Bodeguero! 👋 Soy tu Asistente de Bodega Minera.\n\n"
                "Puedo orientarte en la entrega de préstamos y descuento de stock, registro de devoluciones parciales/totales, "
                "asignación de códigos AL-ES, verificación SofiaPlus y control de inventario en Kardex.\n\n"
                "¿En qué te puedo colaborar hoy?"
            )
        else:
            return (
                "¡Hola! 👋 Soy tu Asistente Virtual de Bodega Minera.\n\n"
                "Puedo orientarte en cómo solicitar herramientas desde el catálogo, revisar el estado de tus solicitudes en "
                "'Mis Préstamos', interpretar los códigos AL-ES o actualizar tus datos de perfil.\n\n"
                "¿Qué duda tienes sobre el sistema?"
            )

    # 2. Devolución parcial
    if any(k in msg_norm for k in (
        'devolucion parcial', 'devoluciones parciales', 'devolver parcial', 
        'devolver parte', 'entrega parcial', 'devolucion incompleta', 
        'faltan herramientas', 'registro una devolucion parcial', 'registrar devolucion parcial'
    )):
        if es_admin:
            return (
                "Para registrar una **Devolución Parcial** en el sistema:\n\n"
                "1. Ingresa al módulo **Préstamos** o **Devoluciones** desde el menú lateral.\n"
                "2. Ubica el préstamo activo en estado **ENTREGADO** o **PARCIAL** y haz clic en **Gestionar Devolución**.\n"
                "3. En la ventana, digita la cantidad física exacta que el aprendiz o instructor te está entregando.\n"
                "4. Al guardar, el sistema realiza una operación atómica: suma las herramientas entregadas al stock disponible, "
                "registra el movimiento en el Kardex y actualiza el estado a **PARCIAL** indicando los ítems restantes.\n"
                "5. Cuando el usuario entregue el resto de herramientas, repites el proceso y el préstamo pasará a **DEVUELTO** (cerrado)."
            )
        else:
            return (
                "Para realizar una **Devolución Parcial** de herramientas:\n\n"
                "1. Acércate a la ventanilla de la bodega minera con los equipos que ya desocupaste.\n"
                "2. El bodeguero registrará la cantidad devuelta en el sistema; tu préstamo pasará a estado **PARCIAL**.\n"
                "3. Podrás consultar en **Mis Préstamos** cuáles herramientas tienes aún pendientes por entregar.\n"
                "4. Recuerda devolver los elementos restantes antes de la fecha límite para evitar bloqueos en nuevos préstamos."
            )

    # 3. Devolución total
    if any(k in msg_norm for k in (
        'devolucion total', 'devolver herramienta', 'como devuelvo', 'cerrar prestamo', 'devolucion'
    )) and not any(k in msg_norm for k in ('parcial', 'al-es', 'sofiaplus')):
        if es_admin:
            return (
                "Para registrar una **Devolución Total**:\n\n"
                "1. En el módulo **Préstamos / Devoluciones**, localiza el préstamo activo.\n"
                "2. Haz clic en **Devolver Todo** o digita la totalidad de las herramientas recibidas.\n"
                "3. El sistema reintegrará automáticamente las unidades al stock en bodega, registrará la entrada en Kardex "
                "y marcará el préstamo como **DEVUELTO** (finalizado)."
            )
        else:
            return (
                "Para devolver todas tus herramientas:\n\n"
                "1. Lleva todos los elementos prestados a la bodega minera limpios y en buen estado.\n"
                "2. El almacenista inspeccionará los activos y confirmará la recepción completa en el sistema.\n"
                "3. Tu préstamo pasará inmediatamente al estado **DEVUELTO**, liberando tu cupo para futuras solicitudes."
            )

    # 4. Entrega de préstamos y descuento de stock
    if any(k in msg_norm for k in (
        'entregar prestamo', 'entrego un prestamo', 'descuenta stock', 'descontar stock', 
        'aprobar prestamo', 'despacho de herramientas', 'como entrego'
    )):
        if es_admin:
            return (
                "Para **Entregar un Préstamo y descontar stock**:\n\n"
                "1. Dirígete a **Gestión de Préstamos** y ubica la solicitud en estado **SOLICITADO** o **APROBADO**.\n"
                "2. Verifica físicamente la disponibilidad de las herramientas en el estante y el documento del solicitante.\n"
                "3. Haz clic en el botón **Entregar**.\n"
                "4. El sistema ejecuta una transacción atómica: descuenta de inmediato las cantidades del stock disponible en bodega, "
                "pasa el estado a **ENTREGADO** e inicia el conteo del tiempo límite de retorno.\n"
                "5. Toda la operación queda trazada en el Kardex y en el historial del usuario."
            )
        else:
            return (
                "La entrega física de herramientas y el descuento de inventario es potestad exclusiva del **Bodeguero / Almacenista**.\n\n"
                "Una vez aprueben tu solicitud, debes presentarte en la bodega con tu documento de identidad para recibir los equipos."
            )

    # 5. Código AL-ES y zonificación
    if any(k in msg_norm for k in ('al-es', 'al es', 'codigo al', 'estante', 'almacen', 'zonificacion', 'ubicacion')):
        return (
            "El código **AL-ES** identifica la ubicación física exacta de cada activo en el Centro Minero:\n\n"
            "- **AL**: Identificador del Almacén o Bodega (ejemplo: `AL1` = Almacén General de Minería subterránea).\n"
            "- **ES**: Número de Estante o Anaquel (ejemplo: `ES02` = Estante módulo 2).\n\n"
            "De este modo, `AL1-ES02` indica exactamente el almacén y estante donde reposa la herramienta, "
            "agilizando su localización tanto para el despacho como en los conteos de inventario físico."
        )

    # 6. Verificación SofiaPlus
    if any(k in msg_norm for k in ('sofiaplus', 'sofia plus', 'verificacion', 'validar aprendiz', 'aprendiz activo', 'matricula')):
        return (
            "La **Verificación SofiaPlus** es el mecanismo de control institucional del SENA:\n\n"
            "1. Valida en tiempo real que el aprendiz o instructor tenga estado de matrícula **ACTIVO** en SofiaPlus.\n"
            "2. Previene que personas con matrícula cancelada, desertadas o con sanciones académicas retiren herramientas de alto valor.\n"
            "3. Protege los activos del Centro Minero y asegura que solo el personal autorizado acceda al equipamiento técnico."
        )

    # 7. Préstamo para Instructor / Préstamo Grupal / Taller en Mina
    if any(k in msg_norm for k in (
        'instructor', 'prestamo grupal', 'varios aprendices', 'comprobante', 
        'imprimir prestamo', 'grupo de aprendices', 'taller mina'
    )):
        return (
            "Para los **Préstamos Grupales de Instructores**:\n\n"
            "1. El Instructor SENA puede solicitar un paquete de herramientas a su propio nombre para sus fichas de aprendices.\n"
            "2. El sistema genera un **Comprobante Oficial de Préstamo** con formato institucional y espacio para firmas de responsabilidad.\n"
            "3. Al presionar **Imprimir**, el comprobante se genera y el préstamo queda registrado y blindado automáticamente en el sistema.\n"
            "4. El instructor asume la custodia técnica de los activos durante la práctica en mina o taller."
        )

    # 8. Solicitar Préstamo (Aprendiz/Instructor)
    if any(k in msg_norm for k in (
        'solicitar herramienta', 'solicitar prestamo', 'pedir herramienta', 
        'como pido', 'como solicito', 'hacer un prestamo'
    )):
        return (
            "Para **Solicitar un Préstamo de Herramientas**:\n\n"
            "1. En el menú lateral, ingresa a **Catálogo de Herramientas**.\n"
            "2. Selecciona la herramienta que necesitas y verifica que cuente con stock disponible.\n"
            "3. Presiona **Solicitar Préstamo**, indica la cantidad de unidades y la justificación de la práctica.\n"
            "4. Tu solicitud quedará en estado **SOLICITADO**. Una vez el bodeguero la revise y apruebe, "
            "recibirás la notificación para reclamarla en bodega."
        )

    # 9. Consultar Mis Préstamos
    if any(k in msg_norm for k in (
        'mis prestamos', 'ver mis prestamos', 'estado de mis prestamos', 
        'donde consulto', 'consultar prestamos', 'estado prestamo'
    )):
        return (
            "Puedes consultar tus préstamos en cualquier momento desde el módulo **Mis Préstamos**:\n\n"
            "- **SOLICITADO**: Tu solicitud está en espera de revisión por el bodeguero.\n"
            "- **APROBADO**: Ha sido autorizada y puedes pasar a reclamar el equipo a la bodega.\n"
            "- **ENTREGADO**: Tienes las herramientas bajo tu responsabilidad.\n"
            "- **PARCIAL**: Has devuelto una parte de las herramientas y tienes ítems pendientes.\n"
            "- **DEVUELTO**: Préstamo concluido a conformidad."
        )

    # 10. Inventario, SKU, Altas y Kardex
    if any(k in msg_norm for k in (
        'inventario', 'kardex', 'sku', 'dar de baja', 'alta de herramienta', 
        'crear herramienta', 'ajuste de stock', 'stock minimo'
    )):
        if es_admin:
            return (
                "En el módulo de **Inventario** puedes gestionar todos los activos mineros:\n\n"
                "- **SKU**: Código identificador único por herramienta.\n"
                "- **Altas de Stock**: Registro de nuevas herramientas adquiridas con su zonificación AL-ES.\n"
                "- **Kardex**: Trazabilidad completa de entradas, salidas y ajustes con fecha, hora y usuario.\n"
                "- **Bajas Técnicas**: Retiro justificado de herramientas averiadas o en mantenimiento."
            )
        else:
            return (
                "La administración del inventario y ajustes de stock corresponde exclusivamente al Administrador/Bodeguero. "
                "Como usuario puedes navegar en el **Catálogo** para consultar fichas técnicas y unidades disponibles."
            )

    # 11. Perfil y Contraseña
    if any(k in msg_norm for k in (
        'perfil', 'editar mi perfil', 'cambiar clave', 'cambiar contrasena', 
        'olvide contrasena', 'olvide mi clave', 'recuperar contrasena'
    )):
        return (
            "Para gestionar tu cuenta y contraseña:\n\n"
            "1. Haz clic en tu nombre o avatar en la esquina superior derecha y selecciona **Mi Perfil**.\n"
            "2. Podrás actualizar tus datos de contacto y cambiar tu contraseña (mínimo 8 caracteres).\n"
            "3. Si perdiste tu acceso, en la pantalla de ingreso utiliza la opción **¿Olvidaste tu contraseña?** "
            "para restablecerla mediante tu correo registrado."
        )

    # 12. Roles del Sistema (RBAC)
    if any(k in msg_norm for k in ('roles', 'rol', 'administrador', 'almacenista', 'instructor', 'aprendiz', 'permisos')):
        return (
            "El Sistema de Bodega Minera cuenta con 4 roles (RBAC):\n\n"
            "- **Administrador**: Gestión global del sistema, usuarios, almacenes y auditoría.\n"
            "- **Almacenista**: Despacho y recepción física, devoluciones parciales/totales y control de inventario.\n"
            "- **Instructor**: Préstamos grupales para mina/talleres con comprobante oficial impreso.\n"
            "- **Aprendiz**: Consulta de catálogo, solicitud de herramientas y seguimiento en Mis Préstamos."
        )

    # 13. Respuesta guiada por defecto
    if es_admin:
        return (
            "Puedo orientarte en las operaciones de Bodega Minera:\n\n"
            "• **Devolución parcial o total**: Cómo recibir entregas y actualizar stock.\n"
            "• **Entrega de préstamos**: Descuento atómico en inventario y cambio a ENTREGADO.\n"
            "• **Código AL-ES**: Zonificación física (Almacén - Estante).\n"
            "• **Verificación SofiaPlus**: Validación de aprendices activos.\n"
            "• **Préstamo para Instructores**: Registro grupal y comprobante impreso.\n"
            "• **Gestión de Inventario**: Kardex, altas y ajuste de stock.\n\n"
            "Escribe tu duda sobre alguno de estos temas o pulsa un botón de sugerencia arriba."
        )
    else:
        return (
            "Puedo orientarte en las operaciones de Bodega Minera:\n\n"
            "• **Solicitar herramientas**: Cómo buscar en el catálogo y enviar una petición.\n"
            "• **Mis Préstamos**: Consultar estados (Solicitado, Aprobado, Entregado, Parcial).\n"
            "• **Devoluciones**: Procedimiento para devolver equipos en bodega.\n"
            "• **Código AL-ES**: Cómo interpretar la ubicación física de las herramientas.\n"
            "• **Mi Perfil**: Cambio de clave y datos de contacto.\n\n"
            "Escribe tu consulta sobre cualquiera de estos temas para ayudarte."
        )


def consultar_gemini(
    mensaje: str,
    historial: Optional[List[Dict[str, str]]] = None,
    rol_usuario: str = 'usuario'
) -> Tuple[str, Optional[int]]:
    """
    Envía la solicitud a la API de Gemini si la clave está configurada;
    si no está configurada o si el servicio remoto falla/está sin conexión,
    activa automáticamente el motor de conocimiento local experto del SBM.
    """
    start_time = time.time()

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
    api_key = api_key.strip()
    model = getattr(settings, 'GEMINI_MODEL', 'gemini-flash-lite-latest') or 'gemini-flash-lite-latest'

    # Fallback automático y transparente si no hay API Key configurada
    if not api_key:
        logger.info("Chatbot: GEMINI_API_KEY no configurada. Activando base de conocimiento local experta.")
        respuesta_local = consultar_base_conocimiento_local(mensaje, rol_usuario)
        elapsed_ms = int((time.time() - start_time) * 1000)
        return respuesta_local, elapsed_ms

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
        with urllib.request.urlopen(req, timeout=12) as response:
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
                    if texto_respuesta:
                        return texto_respuesta, elapsed_ms

            # Si no hubo partes válidas, fallback local
            return consultar_base_conocimiento_local(mensaje, rol_usuario), elapsed_ms

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"Chatbot Gemini no disponible ({str(e)}). Activando base de conocimiento local.")
        # Fallback local inmediato y seguro para cualquier falla externa o sin conexión
        return consultar_base_conocimiento_local(mensaje, rol_usuario), elapsed_ms
