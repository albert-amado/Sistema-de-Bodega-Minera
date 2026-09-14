/**
 * static/js/configuracion.js
 * Lógica modularizada para la prueba asíncrona de conexión de base de datos en la nube.
 */

document.addEventListener('DOMContentLoaded', function () {
  var btnTestCloud = document.getElementById('btnTestCloud');
  if (!btnTestCloud) return;

  btnTestCloud.addEventListener('click', async function () {
    var alertBox = document.getElementById('testResultAlert');
    if (alertBox) {
      alertBox.className = 'alert alert-info py-2 small mb-3';
      alertBox.innerText = 'Probando conexión con el servidor en la nube...';
      alertBox.classList.remove('d-none');
    }

    var testUrl = btnTestCloud.getAttribute('data-url') || '/configuracion/api/test-connection/';

    function getCookie(name) {
      var cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
          var cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === name + '=') {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }

    var csrfToken =
      (document.querySelector('[name=csrfmiddlewaretoken]') &&
        document.querySelector('[name=csrfmiddlewaretoken]').value) ||
      getCookie('csrftoken') ||
      '';

    var payload = {
      target: 'cloud',
      driver: (document.getElementById('cloud_driver') && document.getElementById('cloud_driver').value) || '',
      host: (document.getElementById('cloud_host') && document.getElementById('cloud_host').value) || '',
      port: (document.getElementById('cloud_port') && document.getElementById('cloud_port').value) || '',
      name: (document.getElementById('cloud_name') && document.getElementById('cloud_name').value) || '',
      user: (document.getElementById('cloud_user') && document.getElementById('cloud_user').value) || '',
      password: (document.getElementById('cloud_password') && document.getElementById('cloud_password').value) || '',
      ssl_mode: (document.getElementById('cloud_ssl') && document.getElementById('cloud_ssl').value) || ''
    };

    try {
      var res = await fetch(testUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });
      var data = await res.json();
      if (alertBox) {
        if (res.ok && data.success) {
          alertBox.className = 'alert alert-success py-2 small mb-3';
          alertBox.innerHTML = '<i class="bi bi-check-circle me-1"></i> ' + (data.message || 'Conexión exitosa.');
        } else {
          alertBox.className = 'alert alert-danger py-2 small mb-3';
          alertBox.innerHTML = '<i class="bi bi-x-circle me-1"></i> ' + (data.message || 'Error en la conexión.');
        }
      }
    } catch (err) {
      if (alertBox) {
        alertBox.className = 'alert alert-danger py-2 small mb-3';
        alertBox.innerText = 'Error de red al ejecutar la prueba.';
      }
    }
  });
});
