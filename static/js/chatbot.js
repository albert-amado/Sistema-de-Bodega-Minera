/**
 * ==========================================================================
 * SISTEMA DE BODEGA MINERA (SBM) — ASISTENTE VIRTUAL IA (CHATBOT CLIENT)
 * Control interactivo, llamadas a API proxy Gemini, accesibilidad y estado.
 * ==========================================================================
 */

(function () {
  'use strict';

  // ── Elementos DOM ──
  var container = document.getElementById('sbmChatbotContainer');
  if (!container) return; // Si no existe el contenedor (usuario no autenticado), no inicializar

  var triggerBtn = document.getElementById('btnChatbotToggle');
  var panel = document.getElementById('chatbotPanel');
  var closeBtn = document.getElementById('btnChatbotClose');
  var resetBtn = document.getElementById('btnChatbotReset');
  var messagesBox = document.getElementById('chatbotMessages');
  var typingIndicator = document.getElementById('chatbotTyping');
  var form = document.getElementById('chatbotForm');
  var input = document.getElementById('chatbotInput');
  var sendBtn = document.getElementById('btnChatbotSend');
  var charCounter = document.getElementById('chatbotCharCounter');

  var userRole = container.getAttribute('data-user-role') || 'usuario';
  var conversationHistory = []; // [{ rol: 'usuario'|'asistente', texto: '...' }]
  var isProcessing = false;

  // ── Helper CSRF ──
  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  var csrfToken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

  // ── Control de Apertura / Cierre ──
  function toggleChatbot(open) {
    var shouldOpen = typeof open === 'boolean' ? open : !panel.classList.contains('is-active');

    if (shouldOpen) {
      container.classList.add('is-open');
      panel.classList.add('is-active');
      panel.setAttribute('aria-hidden', 'false');
      triggerBtn.setAttribute('aria-expanded', 'true');
      scrollToBottom();
      setTimeout(function () {
        input.focus();
      }, 150);
    } else {
      container.classList.remove('is-open');
      panel.classList.remove('is-active');
      panel.setAttribute('aria-hidden', 'true');
      triggerBtn.setAttribute('aria-expanded', 'false');
      triggerBtn.focus();
    }
  }

  // ── Scroll automático ──
  function scrollToBottom() {
    if (messagesBox) {
      messagesBox.scrollTop = messagesBox.scrollHeight;
    }
  }

  // ── Renderizado de burbujas ──
  function escapeHTML(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatResponseText(text) {
    // Escape HTML inicial por seguridad
    var escaped = escapeHTML(text);
    // Convertir negritas markdown simples **texto** -> <strong>texto</strong>
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convertir saltos de línea a párrafos o <br>
    return escaped.replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br>');
  }

  function appendMessage(sender, text, isError) {
    var now = new Date();
    var timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    var msgDiv = document.createElement('div');
    msgDiv.className = 'sbm-chat-message ' + (sender === 'user' ? 'sbm-message-user' : 'sbm-message-bot');
    if (isError) msgDiv.classList.add('sbm-message-system-error');

    var contentHTML = sender === 'user' ? escapeHTML(text) : '<p>' + formatResponseText(text) + '</p>';

    msgDiv.innerHTML =
      '<div class="sbm-bubble">' +
        contentHTML +
        '<span class="sbm-msg-time">' + timeStr + '</span>' +
      '</div>';

    messagesBox.appendChild(msgDiv);
    scrollToBottom();
  }

  // ── Typing Indicator ──
  function showTyping(show) {
    if (show) {
      typingIndicator.classList.remove('d-none');
    } else {
      typingIndicator.classList.add('d-none');
    }
    scrollToBottom();
  }

  // ── Envío de mensaje a la API ──
  function sendMessage(messageText) {
    var text = (messageText || input.value || '').trim();
    if (!text || isProcessing) return;

    // Truncar a 500 si supera
    if (text.length > 500) text = text.substring(0, 500);

    // Agregar mensaje del usuario a la interfaz
    appendMessage('user', text);
    conversationHistory.push({ rol: 'usuario', texto: text });

    // Limpiar campo de texto y contador
    input.value = '';
    input.style.height = 'auto';
    charCounter.textContent = '0/500';
    charCounter.classList.remove('near-limit', 'at-limit');

    isProcessing = true;
    sendBtn.disabled = true;
    showTyping(true);

    fetch('/api/chatbot/mensaje/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({
        mensaje: text,
        historial: conversationHistory.slice(-6),
        usuario_rol: userRole
      })
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { status: response.status, data: data };
        });
      })
      .then(function (res) {
        showTyping(false);
        isProcessing = false;
        sendBtn.disabled = false;

        if (res.status === 200 && res.data.respuesta) {
          appendMessage('bot', res.data.respuesta);
          conversationHistory.push({ rol: 'asistente', texto: res.data.respuesta });
        } else if (res.status === 429) {
          appendMessage('bot', res.data.error || 'Has superado el límite de consultas por minuto. Espera un momento.', true);
        } else if (res.status === 401) {
          appendMessage('bot', 'Tu sesión ha caducado. Por favor recarga la página o inicia sesión de nuevo.', true);
        } else {
          var errorMsg = res.data.error || res.data.respuesta || 'No fue posible obtener respuesta del asistente en este momento.';
          appendMessage('bot', errorMsg, true);
        }
      })
      .catch(function (err) {
        showTyping(false);
        isProcessing = false;
        sendBtn.disabled = false;
        appendMessage('bot', 'Ocurrió un error de red al consultar el asistente. Verifica tu conexión.', true);
      });
  }

  // ── Auto-resize de Textarea y Contador ──
  input.addEventListener('input', function () {
    this.style.height = 'auto';
    var newHeight = Math.min(Math.max(this.scrollHeight, 24), 110);
    this.style.height = newHeight + 'px';
    var len = this.value.length;
    charCounter.textContent = len + '/500';
    if (len >= 490) {
      charCounter.classList.add('at-limit');
      charCounter.classList.remove('near-limit');
    } else if (len >= 400) {
      charCounter.classList.add('near-limit');
      charCounter.classList.remove('at-limit');
    } else {
      charCounter.classList.remove('near-limit', 'at-limit');
    }
  });

  // ── Teclas Enter y Shift+Enter ──
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    sendMessage();
  });

  // ── Sugerencias Rápidas (Chips) ──
  messagesBox.addEventListener('click', function (e) {
    var chip = e.target.closest('.sbm-chip');
    if (chip) {
      var question = chip.getAttribute('data-question');
      if (question) {
        sendMessage(question);
      }
    }
  });

  // ── Reset de Conversación ──
  if (resetBtn) {
    resetBtn.addEventListener('click', function () {
      if (confirm('¿Deseas reiniciar la conversación con el asistente?')) {
        conversationHistory = [];
        // Mantener solo el primer mensaje (bienvenida) y las sugerencias
        var welcomeMsg = messagesBox.querySelector('.sbm-message-bot');
        var suggestions = messagesBox.querySelector('.sbm-chat-suggestions');
        messagesBox.innerHTML = '';
        if (welcomeMsg) messagesBox.appendChild(welcomeMsg);
        if (suggestions) messagesBox.appendChild(suggestions);
        input.value = '';
        input.style.height = 'auto';
        charCounter.textContent = '0/500';
        charCounter.classList.remove('near-limit', 'at-limit');
        input.focus();
      }
    });
  }

  // ── Eventos de Apertura y Cierre ──
  triggerBtn.addEventListener('click', function () {
    toggleChatbot();
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', function () {
      toggleChatbot(false);
    });
  }

  // Cerrar con Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && panel.classList.contains('is-active')) {
      toggleChatbot(false);
    }
  });

  // Enfocar input al hacer clic en cualquier parte del contenedor
  var wrapper = panel.querySelector('.sbm-input-wrapper');
  if (wrapper && input) {
    wrapper.addEventListener('click', function (e) {
      if (e.target !== input) {
        input.focus();
      }
    });
  }

  // Actualizar hora de mensaje inicial
  var initTimeSpan = messagesBox.querySelector('[data-init-time]');
  if (initTimeSpan) {
    var now = new Date();
    initTimeSpan.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

})();
