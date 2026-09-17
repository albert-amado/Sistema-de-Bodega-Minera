"""
services/sofia_plus_client.py
=============================================================================
Cliente de Integración para Verificación de Aprendices SENA / SofiaPlus
Sistema de Bodega Minera (SBM)
=============================================================================

Módulo aislado para la consulta externa de información académica de aprendices
SENA a partir de su tipo y número de documento de identidad.

Cumplimiento Normativo y Seguridad:
- Ley 1581 de 2012 (Habeas Data): No almacena permanentemente datos de aprendices.
  Maneja caché en memoria con TTL corto (default: 300 segundos = 5 minutos).
- Registro en logs anonimizado / enmascarado (nunca expone documentos completos).
- Nunca expone tokens, credenciales ni trazas crudas del API hacia la UI.
- Reintentos con retroceso exponencial (Exponential Backoff) ante fallos transitorios.
- Fallback seguro y modo desarrollo cuando las credenciales oficiales no están activas.
"""

import os
import re
import ssl
import json
import time
import logging
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPCIONES DEL SERVICIO
# =============================================================================

class SofiaPlusError(Exception):
    """Excepción base para errores del servicio SofiaPlus."""
    def __init__(self, message: str, user_friendly_message: Optional[str] = None):
        super().__init__(message)
        self.user_friendly_message = user_friendly_message or (
            "No fue posible completar la verificación del aprendiz en este momento."
        )


class SofiaPlusInvalidInputError(SofiaPlusError):
    """El número o tipo de documento no cumple con los formatos válidos."""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            user_friendly_message="El documento ingresado no tiene un formato válido (números de 5 a 12 dígitos)."
        )


class AprendizNotFoundError(SofiaPlusError):
    """El aprendiz no se encuentra registrado en el sistema SENA / SofiaPlus."""
    def __init__(self, masked_doc: str):
        super().__init__(
            message=f"Aprendiz con documento {masked_doc} no encontrado.",
            user_friendly_message=(
                "No se encontró ningún aprendiz registrado con el documento especificado. "
                "Verifica el número ingresado o valida si pertenece a este centro minero."
            )
        )


class SofiaPlusServiceUnavailableError(SofiaPlusError):
    """El servicio externo del SENA no está disponible o tardó demasiado en responder."""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            user_friendly_message=(
                "El servicio de verificación del SENA / SofiaPlus no se encuentra disponible "
                "en este momento. Por favor intenta nuevamente en unos minutos."
            )
        )


class SofiaPlusAuthError(SofiaPlusError):
    """Error de autenticación o credenciales inválidas con el API externo."""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            user_friendly_message=(
                "Error de autorización con la plataforma del SENA. "
                "El administrador del sistema debe verificar las credenciales configuradas."
            )
        )


# =============================================================================
# MODELO DE DATOS NORMALIZADO
# =============================================================================

@dataclass
class AprendizInfo:
    """Representación normalizada e inmutable de los datos del aprendiz."""
    documento: str
    tipo_documento: str
    nombre_completo: str
    primer_nombre: str
    primer_apellido: str
    segundo_nombre: str
    segundo_apellido: str
    programa_formacion: str
    numero_ficha: str
    nombre_ficha: str
    estado_programa: str      # 'ACTIVO', 'EN FORMACION', 'EGRESADO', 'CONDICIONADO', 'CANCELADO', 'RETIRO'
    centro_formacion: str     # Ej. "Centro Minero - Regional Boyacá"
    regional: str             # Ej. "Boyacá"
    correo_institucional: str
    telefono_contacto: str
    origen_datos: str         # 'api_externa' | 'cache' | 'base_datos_local'
    fecha_consulta: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# CLIENTE DE INTEGRACIÓN
# =============================================================================

class SofiaPlusClient:
    """
    Cliente aislado para comunicación con el API de SofiaPlus / SENA.
    Implementa caché en memoria de corta duración, reintentos con backoff
    y protección de datos personales.
    """

    # Tipos de documentos admitidos en Colombia / SENA
    TIPOS_VALIDOS = {'CC', 'TI', 'CE', 'PEP', 'PPT', 'PAS'}

    def __init__(self):
        # ── Lectura de Variables de Entorno ──
        self.api_url = os.environ.get('SOFIAPLUS_API_URL', '').strip().rstrip('/')
        self.auth_type = os.environ.get('SOFIAPLUS_AUTH_TYPE', 'api_key').strip().lower()
        self.api_key = os.environ.get('SOFIAPLUS_API_KEY', '').strip()
        self.api_token = os.environ.get('SOFIAPLUS_API_TOKEN', '').strip()
        self.client_id = os.environ.get('SOFIAPLUS_CLIENT_ID', '').strip()
        self.client_secret = os.environ.get('SOFIAPLUS_CLIENT_SECRET', '').strip()
        self.token_url = os.environ.get('SOFIAPLUS_TOKEN_URL', '').strip()

        # Configuración de red y tolerancia a fallos
        self.timeout = float(os.environ.get('SOFIAPLUS_TIMEOUT', '5.0'))
        self.max_retries = int(os.environ.get('SOFIAPLUS_MAX_RETRIES', '2'))
        self.backoff_factor = float(os.environ.get('SOFIAPLUS_BACKOFF_FACTOR', '0.5'))
        self.cache_ttl = int(os.environ.get('SOFIAPLUS_CACHE_TTL', '300'))  # 5 minutos

        # Caché en memoria: { (tipo, doc): (timestamp, AprendizInfo) }
        self._cache: Dict[Tuple[str, str], Tuple[float, AprendizInfo]] = {}

        # Token OAuth2 en memoria (si aplica)
        self._oauth_token: Optional[str] = None
        self._oauth_expires_at: float = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # UTILIDADES DE SEGURIDAD Y HABEAS DATA
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def mask_documento(doc: str) -> str:
        """
        Enmascara el documento para logs y auditoría (ej. '1024567890' -> '******7890').
        Cumplimiento Ley 1581 de 2012 de Protección de Datos Personales.
        """
        doc = str(doc).strip()
        if len(doc) <= 4:
            return "****"
        return ("*" * (len(doc) - 4)) + doc[-4:]

    @classmethod
    def validar_y_sanitizar(cls, tipo_documento: str, numero_documento: str) -> Tuple[str, str]:
        """
        Valida que el tipo y número de documento cumplan con las reglas estándar.
        Sanitiza la entrada eliminando caracteres no válidos para prevenir inyecciones.
        """
        if not tipo_documento or not numero_documento:
            raise SofiaPlusInvalidInputError("El tipo y número de documento son obligatorios.")

        tipo = str(tipo_documento).strip().upper()
        if tipo not in cls.TIPOS_VALIDOS:
            raise SofiaPlusInvalidInputError(
                f"Tipo de documento '{tipo}' no reconocido. Tipos válidos: {', '.join(sorted(cls.TIPOS_VALIDOS))}."
            )

        # Sanitizar número: solo dígitos alfanuméricos según el tipo
        doc_limpio = re.sub(r'[^A-Za-z0-9]', '', str(numero_documento).strip())

        # Para CC y TI se exigen solo dígitos de 5 a 12 caracteres
        if tipo in {'CC', 'TI'}:
            if not doc_limpio.isdigit() or not (5 <= len(doc_limpio) <= 12):
                raise SofiaPlusInvalidInputError(
                    f"La {tipo} debe contener únicamente números (entre 5 y 12 dígitos)."
                )
        else:
            if not (4 <= len(doc_limpio) <= 16):
                raise SofiaPlusInvalidInputError(
                    f"El documento {tipo} debe tener entre 4 y 16 caracteres alfanuméricos."
                )

        return tipo, doc_limpio

    # ─────────────────────────────────────────────────────────────────────────
    # GESTIÓN DE CACHÉ DE CORTA DURACIÓN (TTL corto por Habeas Data)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_from_cache(self, tipo: str, doc: str) -> Optional[AprendizInfo]:
        """Recupera el aprendiz de la caché si no ha expirado su TTL."""
        key = (tipo, doc)
        if key in self._cache:
            created_at, info = self._cache[key]
            if time.time() - created_at < self.cache_ttl:
                # Retornar una copia con indicador de origen 'cache'
                data = info.to_dict()
                data['origen_datos'] = 'cache'
                return AprendizInfo(**data)
            else:
                del self._cache[key]
        return None

    def _save_to_cache(self, tipo: str, doc: str, info: AprendizInfo) -> None:
        """Guarda en caché en memoria y purga entradas expiradas."""
        now = time.time()
        # Purgar entradas vencidas para evitar fuga de memoria
        keys_to_del = [k for k, (ts, _) in self._cache.items() if now - ts > self.cache_ttl]
        for k in keys_to_del:
            self._cache.pop(k, None)

        self._cache[(tipo, doc)] = (now, info)

    # ─────────────────────────────────────────────────────────────────────────
    # AUTENTICACIÓN EXTERNA
    # ─────────────────────────────────────────────────────────────────────────

    def _get_auth_headers(self) -> Dict[str, str]:
        """Genera los encabezados HTTP según el método de autenticación configurado."""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'SistemaBodegaMinera-SENA/1.0',
        }

        if self.auth_type == 'api_key' and self.api_key:
            # TODO: Ajustar el nombre del header si el API del SENA usa otro
            # (ej. 'X-SENA-API-Key' o 'Ocp-Apim-Subscription-Key')
            headers['X-API-Key'] = self.api_key

        elif self.auth_type == 'bearer' and self.api_token:
            headers['Authorization'] = f"Bearer {self.api_token}"

        elif self.auth_type == 'oauth2' and self.client_id and self.client_secret:
            token = self._get_oauth2_token()
            if token:
                headers['Authorization'] = f"Bearer {token}"

        return headers

    def _get_oauth2_token(self) -> Optional[str]:
        """Obtiene o renueva un token OAuth2 Client Credentials si está configurado."""
        if self._oauth_token and time.time() < self._oauth_expires_at:
            return self._oauth_token

        if not self.token_url:
            return None

        # TODO: Ajustar el payload de autenticación OAuth2 según el Identity Provider del SENA
        payload = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }).encode('utf-8')

        req = urllib.request.Request(self.token_url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                self._oauth_token = data.get('access_token')
                expires_in = int(data.get('expires_in', 3600)) - 60
                self._oauth_expires_at = time.time() + max(60, expires_in)
                return self._oauth_token
        except Exception as err:
            logger.error("Fallo al obtener token OAuth2 de SofiaPlus: %s", type(err).__name__)
            raise SofiaPlusAuthError("No fue posible autenticarse ante el servicio de identidad del SENA.")

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL: CONSULTAR APRENDIZ
    # ─────────────────────────────────────────────────────────────────────────

    def consultar_aprendiz(self, tipo_documento: str, numero_documento: str) -> AprendizInfo:
        """
        Consulta y retorna la información de un aprendiz por tipo y número de documento.
        Aplica validación, consulta de caché, reintentos con backoff y fallback seguro.
        """
        tipo, doc = self.validar_y_sanitizar(tipo_documento, numero_documento)
        masked = self.mask_documento(doc)

        # 1. Revisar caché local de corta duración
        cached = self._get_from_cache(tipo, doc)
        if cached:
            logger.info("Verificación de aprendiz %s obtenida desde caché local.", masked)
            return cached

        # 2. Si no hay URL configurada en .env, usar el adaptador local (base de datos de usuarios SENA)
        if not self.api_url or self.api_url == 'mock' or self.auth_type == 'mock':
            logger.info(
                "SOFIAPLUS_API_URL no configurada o en modo 'mock'. Consultando registro local para %s.",
                masked
            )
            aprendiz = self._consultar_base_datos_local(tipo, doc)
            self._save_to_cache(tipo, doc, aprendiz)
            return aprendiz

        # 3. Realizar consulta HTTP contra el endpoint oficial del SENA
        aprendiz = self._ejecutar_consulta_http(tipo, doc)
        self._save_to_cache(tipo, doc, aprendiz)
        return aprendiz

    # ─────────────────────────────────────────────────────────────────────────
    # EJECUCIÓN HTTP CON RETRY Y EXPONENTIAL BACKOFF
    # ─────────────────────────────────────────────────────────────────────────

    def _ejecutar_consulta_http(self, tipo: str, doc: str) -> AprendizInfo:
        """
        Ejecuta la llamada HTTP con reintentos exponenciales ante timeouts o 5xx.
        """
        masked = self.mask_documento(doc)

        # TODO: Ajustar la estructura de la URL según la especificación oficial que entregue el SENA:
        # Opción 1: Query params -> {api_url}/aprendices?tipo={tipo}&documento={doc}
        # Opción 2: Path params  -> {api_url}/aprendices/{tipo}/{doc}
        params = urllib.parse.urlencode({'tipo_documento': tipo, 'numero_documento': doc})
        endpoint_url = f"{self.api_url}/aprendices?{params}"

        headers = self._get_auth_headers()
        req = urllib.request.Request(endpoint_url, headers=headers, method='GET')

        ultimo_error = None
        for intento in range(self.max_retries + 1):
            try:
                # Contexto SSL seguro
                ctx = ssl.create_default_context()

                with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                    status_code = response.getcode()
                    if status_code == 200:
                        body = response.read().decode('utf-8')
                        data = json.loads(body)
                        return self._mapear_respuesta_api(data, tipo, doc)
                    else:
                        raise SofiaPlusError(f"Código HTTP inesperado: {status_code}")

            except urllib.error.HTTPError as http_err:
                codigo = http_err.code
                if codigo == 404:
                    logger.warning("Aprendiz con documento %s no encontrado en SofiaPlus (HTTP 404).", masked)
                    raise AprendizNotFoundError(masked)
                elif codigo in {401, 403}:
                    logger.error("Error de autenticación contra SofiaPlus HTTP %s. Credenciales inválidas.", codigo)
                    raise SofiaPlusAuthError("Credenciales no autorizadas en la plataforma del SENA.")
                elif codigo >= 500:
                    # Error del servidor externo -> candidato a reintento
                    ultimo_error = http_err
                    logger.warning(
                        "Fallo HTTP %s al consultar SofiaPlus para %s. Intento %d/%d.",
                        codigo, masked, intento + 1, self.max_retries + 1
                    )
                else:
                    ultimo_error = http_err
                    break

            except (urllib.error.URLError, TimeoutError) as net_err:
                ultimo_error = net_err
                logger.warning(
                    "Timeout o error de red al conectar con SofiaPlus para %s: %s. Intento %d/%d.",
                    masked, type(net_err).__name__, intento + 1, self.max_retries + 1
                )

            # Esperar antes del siguiente intento con backoff exponencial
            if intento < self.max_retries:
                espera = self.backoff_factor * (2 ** intento)
                time.sleep(espera)

        # Si agotó todos los reintentos:
        logger.error(
            "Se agotaron los reintentos de conexión con SofiaPlus para %s. Error final: %s",
            masked, type(ultimo_error).__name__
        )
        raise SofiaPlusServiceUnavailableError(
            "El servicio del SENA tardó demasiado en responder o está temporalmente fuera de línea."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # MAPEO DE RESPUESTA DE API OFICIAL (TODO: AJUSTAR AL SCHEMA REAL DE SENA)
    # ─────────────────────────────────────────────────────────────────────────

    def _mapear_respuesta_api(self, raw: Dict[str, Any], tipo: str, doc: str) -> AprendizInfo:
        """
        Mapea el JSON recibido del API externo a la estructura normalizada AprendizInfo.
        
        TODO: Cuando el SENA entregue la documentación Swagger/OpenAPI o WSDL exacta,
        actualizar los nombres de los campos en este diccionario:
        - raw.get('nombres') / raw.get('primer_nombre')
        - raw.get('ficha_caracterizacion') / raw.get('numero_ficha')
        - raw.get('estado_matricula') / raw.get('estado')
        """
        # Formato esperado genérico común en APIs del Estado / SENA
        primer_nombre = raw.get('primer_nombre') or raw.get('nombres', '').split(' ')[0] or 'Aprendiz'
        primer_apellido = raw.get('primer_apellido') or raw.get('apellidos', '').split(' ')[0] or 'SENA'
        segundo_nombre = raw.get('segundo_nombre') or ''
        segundo_apellido = raw.get('segundo_apellido') or ''

        nombre_completo = raw.get('nombre_completo')
        if not nombre_completo:
            partes = [primer_nombre, segundo_nombre, primer_apellido, segundo_apellido]
            nombre_completo = " ".join(p for p in partes if p).strip()

        estado_raw = str(raw.get('estado') or raw.get('estado_matricula') or 'EN FORMACIÓN').upper().strip()

        return AprendizInfo(
            documento=doc,
            tipo_documento=tipo,
            nombre_completo=nombre_completo,
            primer_nombre=primer_nombre,
            primer_apellido=primer_apellido,
            segundo_nombre=segundo_nombre,
            segundo_apellido=segundo_apellido,
            programa_formacion=raw.get('programa') or raw.get('nombre_programa') or 'Programa de Formación Minera',
            numero_ficha=str(raw.get('ficha') or raw.get('numero_ficha') or 'S/F'),
            nombre_ficha=raw.get('nombre_ficha') or raw.get('programa') or '',
            estado_programa=estado_raw,
            centro_formacion=raw.get('centro_formacion') or 'Centro Minero - Regional Boyacá',
            regional=raw.get('regional') or 'Boyacá',
            correo_institucional=raw.get('correo_misena') or raw.get('correo') or '',
            telefono_contacto=raw.get('telefono') or '',
            origen_datos='api_externa',
            fecha_consulta=time.strftime('%Y-%m-%d %H:%M:%S'),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADAPTADOR DE DESARROLLO / FALLBACK LOCAL (CONSULTA MODELO Usuario SENA)
    # ─────────────────────────────────────────────────────────────────────────

    def _consultar_base_datos_local(self, tipo: str, doc: str) -> AprendizInfo:
        """
        Consulta en el directorio simulado de aprendices SENA o en la base de datos local.
        Permite validar tanto nuevos aprendices en registro como aprendices existentes
        mientras el SENA entrega las credenciales finales de producción.
        """
        masked = self.mask_documento(doc)
        
        # 1. Directorio simulado de aprendices SENA para pruebas de registro y desarrollo
        SIMULATED_SENA_APRENDICES = {
            '1098765432': {
                'nombre_completo': 'Carlos Andrés Martínez Gómez',
                'primer_nombre': 'Carlos',
                'segundo_nombre': 'Andrés',
                'primer_apellido': 'Martínez',
                'segundo_apellido': 'Gómez',
                'programa_formacion': 'Supervisión de Labores Mineras',
                'numero_ficha': '2758369',
                'nombre_ficha': 'Supervisión Minera y Seguridad',
                'estado_programa': 'EN FORMACIÓN',
                'centro_formacion': 'Centro Minero - Regional Boyacá',
                'regional': 'Boyacá',
                'correo_institucional': 'carlos.martinez@misena.edu.co',
                'telefono_contacto': '3114567890',
            },
            '1012345678': {
                'nombre_completo': 'Laura Valentina Sánchez Torres',
                'primer_nombre': 'Laura',
                'segundo_nombre': 'Valentina',
                'primer_apellido': 'Sánchez',
                'segundo_apellido': 'Torres',
                'programa_formacion': 'Análisis y Desarrollo de Software (ADSO)',
                'numero_ficha': '2827435',
                'nombre_ficha': 'ADSO Ficha 2827435',
                'estado_programa': 'EN FORMACIÓN',
                'centro_formacion': 'Centro Minero - Regional Boyacá',
                'regional': 'Boyacá',
                'correo_institucional': 'laura.sanchez@misena.edu.co',
                'telefono_contacto': '3157891234',
            },
            '1054321987': {
                'nombre_completo': 'Diego Fernando Morales Rincón',
                'primer_nombre': 'Diego',
                'segundo_nombre': 'Fernando',
                'primer_apellido': 'Morales',
                'segundo_apellido': 'Rincón',
                'programa_formacion': 'Mantenimiento Electromecánico',
                'numero_ficha': '2895642',
                'nombre_ficha': 'Mantenimiento Minero e Industrial',
                'estado_programa': 'EN FORMACIÓN',
                'centro_formacion': 'Centro Minero - Regional Boyacá',
                'regional': 'Boyacá',
                'correo_institucional': 'diego.morales@misena.edu.co',
                'telefono_contacto': '3206549871',
            },
        }

        if doc in SIMULATED_SENA_APRENDICES:
            mock = SIMULATED_SENA_APRENDICES[doc]
            return AprendizInfo(
                documento=doc,
                tipo_documento=tipo,
                nombre_completo=mock['nombre_completo'],
                primer_nombre=mock['primer_nombre'],
                primer_apellido=mock['primer_apellido'],
                segundo_nombre=mock['segundo_nombre'],
                segundo_apellido=mock['segundo_apellido'],
                programa_formacion=mock['programa_formacion'],
                numero_ficha=mock['numero_ficha'],
                nombre_ficha=mock['nombre_ficha'],
                estado_programa=mock['estado_programa'],
                centro_formacion=mock['centro_formacion'],
                regional=mock['regional'],
                correo_institucional=mock['correo_institucional'],
                telefono_contacto=mock['telefono_contacto'],
                origen_datos="simulador_sofia_plus (Desarrollo)",
                fecha_consulta=time.strftime('%Y-%m-%d %H:%M:%S'),
            )

        try:
            from usuario.models import Usuario

            u = Usuario.objects.filter(documento=doc).first()
            if not u:
                logger.info("Aprendiz %s no encontrado en registro local.", masked)
                raise AprendizNotFoundError(masked)

            # Normalizar nombre
            partes = [u.primer_nombre, u.segundo_nombre, u.primer_apellido, u.segundo_apellido]
            nombre_completo = " ".join(p for p in partes if p).strip() or u.primer_nombre

            # Determinar estado
            estado = "EN FORMACIÓN"
            if u.rol == 'Administrador':
                estado = "ACTIVO (INSTRUCTOR/ADMIN)"

            return AprendizInfo(
                documento=doc,
                tipo_documento=u.tipo_documento or tipo,
                nombre_completo=nombre_completo,
                primer_nombre=u.primer_nombre or '',
                primer_apellido=u.primer_apellido or '',
                segundo_nombre=u.segundo_nombre or '',
                segundo_apellido=u.segundo_apellido or '',
                programa_formacion=u.programa or "Supervisión de Labores Mineras / ADSO",
                numero_ficha=u.ficha or "2694582",
                nombre_ficha=u.programa or "Ficha de Formación Minera",
                estado_programa=estado,
                centro_formacion="Centro Minero - Regional Boyacá",
                regional="Boyacá",
                correo_institucional=u.correo_personal or f"aprendiz.{doc[-4:]}@misena.edu.co",
                telefono_contacto=u.telefono or "",
                origen_datos="base_datos_local (Adaptador de Desarrollo)",
                fecha_consulta=time.strftime('%Y-%m-%d %H:%M:%S'),
            )
        except AprendizNotFoundError:
            raise
        except Exception as err:
            logger.error("Error al consultar registro local para %s: %s", masked, err)
            raise SofiaPlusServiceUnavailableError("Error al consultar el registro interno de aprendices.")


# =============================================================================
# INSTANCIA SINGLETON REUTILIZABLE
# =============================================================================

_sofia_client_instance: Optional[SofiaPlusClient] = None

def get_sofia_plus_client() -> SofiaPlusClient:
    """Retorna una instancia única del cliente de SofiaPlus."""
    global _sofia_client_instance
    if _sofia_client_instance is None:
        _sofia_client_instance = SofiaPlusClient()
    return _sofia_client_instance
