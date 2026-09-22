import json
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse

from .models import ChatLog
from .services import (
    construir_system_instruction,
    consultar_gemini,
    enmascarar_datos_sensibles,
    sanitizar_mensaje_usuario,
    verificar_rate_limit,
)


class ChatbotHabeasDataTests(TestCase):
    """Pruebas de cumplimiento de la Ley 1581 de 2012 (Habeas Data)."""

    def test_enmascarar_documento_cedula(self):
        texto = "Mi cédula es 1023456789 y necesito un taladro."
        enmascarado = enmascarar_datos_sensibles(texto)
        self.assertNotIn("1023456789", enmascarado)
        self.assertIn("[DOCUMENTO-ENMASCARADO]", enmascarado)

    def test_enmascarar_correo_electronico(self):
        texto = "Escríbame a aprendiz.sena@gmail.com por favor."
        enmascarado = enmascarar_datos_sensibles(texto)
        self.assertNotIn("aprendiz.sena@gmail.com", enmascarado)
        self.assertIn("[CORREO-ENMASCARADO]", enmascarado)

    def test_enmascarar_telefono_celular(self):
        texto = "Mi contacto de WhatsApp es 3105551234."
        enmascarado = enmascarar_datos_sensibles(texto)
        self.assertNotIn("3105551234", enmascarado)
        self.assertIn("[TELEFONO-ENMASCARADO]", enmascarado)

    def test_enmascarar_contrasena(self):
        texto = "Mi clave: Secreta2026! no funciona."
        enmascarado = enmascarar_datos_sensibles(texto)
        self.assertNotIn("Secreta2026!", enmascarado)


class ChatbotSanitizacionTests(TestCase):
    """Pruebas de sanitización de entrada y rate-limit."""

    def test_limite_500_caracteres(self):
        texto_largo = "A" * 800
        sanitizado = sanitizar_mensaje_usuario(texto_largo)
        self.assertEqual(len(sanitizado), 500)

    def test_remover_etiquetas_html(self):
        texto_html = "<script>alert('hack')</script><b>Hola</b> asistente"
        sanitizado = sanitizar_mensaje_usuario(texto_html)
        self.assertNotIn("<script>", sanitizado)
        self.assertNotIn("<b>", sanitizado)
        self.assertIn("Hola asistente", sanitizado)

    def test_rate_limit_20_rpm(self):
        uid = "test_user_rate_limit"
        for i in range(20):
            permitido, _ = verificar_rate_limit(uid, max_rpm=20)
            self.assertTrue(permitido, f"El mensaje {i+1} debió ser permitido")

        # El mensaje 21 debe ser bloqueado
        permitido, espera = verificar_rate_limit(uid, max_rpm=20)
        self.assertFalse(permitido)
        self.assertGreater(espera, 0)


class ChatbotPromptTests(TestCase):
    """Pruebas de diferenciación de roles en el system instruction."""

    def test_prompt_para_admin(self):
        prompt = construir_system_instruction("admin")
        self.assertIn("ADMINISTRADOR", prompt)
        self.assertIn("inventario", prompt)
        self.assertIn("SofiaPlus", prompt)

    def test_prompt_para_usuario(self):
        prompt = construir_system_instruction("usuario")
        self.assertIn("APRENDIZ / INSTRUCTOR", prompt)
        self.assertIn("SOLO tiene acceso a: consultar catálogo", prompt)


class ChatbotApiEndpointTests(TestCase):
    """Pruebas del endpoint HTTP /api/chatbot/mensaje/."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('chatbot_mensaje')

    def test_rechazo_sin_sesion(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"mensaje": "Hola"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_sesion_activa_mensaje_vacio(self):
        session = self.client.session
        session['usuario_documento'] = '1098765432'
        session['usuario_rol'] = 'Usuario'
        session.save()

        response = self.client.post(
            self.url,
            data=json.dumps({"mensaje": "   "}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch('chatbot.views.consultar_gemini')
    def test_flujo_exitoso_y_registro_chatlog(self, mock_gemini):
        mock_gemini.return_value = ("Hola, ¿en qué te puedo orientar?", 120)

        session = self.client.session
        session['usuario_documento'] = '1098765432'
        session['usuario_rol'] = 'Administrador'
        session.save()

        payload = {
            "mensaje": "Mi cédula es 1098765432 y quiero saber cómo ver préstamos.",
            "historial": []
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('respuesta'), "Hola, ¿en qué te puedo orientar?")

        # Verificar que el ChatLog se creó y tiene el documento enmascarado
        log = ChatLog.objects.filter(usuario_documento='1098765432').first()
        self.assertIsNotNone(log)
        self.assertNotIn("1098765432", log.mensaje_usuario)
        self.assertIn("[DOCUMENTO-ENMASCARADO]", log.mensaje_usuario)
        self.assertEqual(log.usuario_rol, 'Administrador')

    def test_widget_render_en_pagina_con_sesion(self):
        """Verifica que el widget se renderice en el template base cuando hay sesión activa."""
        from usuario.models import Usuario
        Usuario.objects.create(
            documento='1098765432',
            primer_nombre='Carlos',
            primer_apellido='Admin',
            rol='Administrador'
        )

        session = self.client.session
        session['usuario_documento'] = '1098765432'
        session['usuario_rol'] = 'Administrador'
        session.save()

        # Renderizar la vista principal que hereda de base.html
        response = self.client.get(reverse('pagina_principal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="sbmChatbotContainer"')
        self.assertContains(response, 'id="btnChatbotToggle"')
        self.assertContains(response, 'id="chatbotPanel"')
        self.assertContains(response, 'chatbot.css')
        self.assertContains(response, 'chatbot.js')
        self.assertContains(response, 'Asistente Bodega Minera')
