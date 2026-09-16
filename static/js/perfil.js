/**
 * static/js/perfil.js
 * Lógica modularizada para el modal de perfil de usuario, tabs, medidor de fuerza de contraseña y validaciones.
 */

(function () {
  document.addEventListener('DOMContentLoaded', function () {
    var modalEl = document.getElementById('modalPerfil');
    if (!modalEl || typeof bootstrap === 'undefined') return;

    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);

    function activarTab(id) {
      document.querySelectorAll('.modal-tab').forEach(function (btn) {
        btn.classList.toggle('modal-tab--active', btn.dataset.tab === id);
      });
      document.querySelectorAll('.modal-tab-panel').forEach(function (panel) {
        panel.style.display = panel.id === id ? 'block' : 'none';
      });
    }
    window._activarTabPerfil = activarTab;

    var btnAbrirPerfil = document.getElementById('btn-abrir-perfil');
    if (btnAbrirPerfil) {
      btnAbrirPerfil.addEventListener('click', function () {
        activarTab('tab-datos');
        modal.show();
      });
    }

    var btnConfig = document.getElementById('btn-abrir-config');
    if (btnConfig) {
      btnConfig.addEventListener('click', function () {
        activarTab('tab-config');
        modal.show();
      });
    }

    // Auto-activación por error
    var modalPerfilContainer = document.getElementById('modalPerfil');
    var tabErrorDestino = modalPerfilContainer ? modalPerfilContainer.getAttribute('data-active-tab') : null;
    if (tabErrorDestino) {
      activarTab(tabErrorDestino);
      modal.show();
    }

    document.querySelectorAll('.modal-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        activarTab(btn.dataset.tab);
      });
    });

    // Barra de fortaleza de contraseña
    var pwNueva = document.getElementById('pw-nueva');
    var pwConfirma = document.getElementById('pw-confirma');
    var fillEl = document.getElementById('strength-fill');
    var labelEl = document.getElementById('strength-label');
    var matchEl = document.getElementById('match-label');

    function calcFuerza(pw) {
      var score = 0;
      if (pw.length >= 8) score++;
      if (pw.length >= 12) score++;
      if (/[A-Z]/.test(pw)) score++;
      if (/[0-9]/.test(pw)) score++;
      if (/[^A-Za-z0-9]/.test(pw)) score++;
      return score;
    }

    var niveles = [
      { pct: '20%', color: '#ef4444', label: 'Muy débil' },
      { pct: '40%', color: '#f97316', label: 'Débil' },
      { pct: '60%', color: '#eab308', label: 'Regular' },
      { pct: '80%', color: '#3b82f6', label: 'Buena' },
      { pct: '100%', color: '#22c55e', label: 'Muy fuerte' }
    ];

    function checkMatch() {
      if (!pwNueva || !pwConfirma || !pwConfirma.value) return;
      if (pwNueva.value === pwConfirma.value) {
        if (matchEl) {
          matchEl.textContent = '✓ Las contraseñas coinciden';
          matchEl.style.color = '#22c55e';
        }
      } else {
        if (matchEl) {
          matchEl.textContent = '✗ No coinciden';
          matchEl.style.color = '#ef4444';
        }
      }
    }

    if (pwNueva) {
      pwNueva.addEventListener('input', function () {
        var pw = this.value;
        if (!fillEl || !labelEl) return;
        if (!pw) {
          fillEl.style.width = '0';
          labelEl.textContent = '';
          return;
        }
        var n = niveles[Math.min(calcFuerza(pw) - 1, 4)] || niveles[0];
        fillEl.style.width = n.pct;
        fillEl.style.background = n.color;
        labelEl.textContent = n.label;
        labelEl.style.color = n.color;
        checkMatch();
      });
    }

    if (pwConfirma) {
      pwConfirma.addEventListener('input', checkMatch);
    }

    var telInput = document.querySelector('[name="telefono"]');
    if (telInput) {
      telInput.addEventListener('input', function () {
        this.value = this.value.replace(/\D/g, '');
      });
    }
  });
})();
