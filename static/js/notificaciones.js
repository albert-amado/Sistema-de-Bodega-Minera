/**
 * static/js/notificaciones.js
 * Módulo para la gestión y actualización del panel de notificaciones en el aside.
 */

window.localNotifications = window.localNotifications || [];

window.addNotification = function (title, desc, icon, color) {
  window.localNotifications.unshift({
    titulo: title,
    desc: desc,
    icono: icon || 'info-circle',
    color: color || 'var(--navy)'
  });

  var notifBtn = document.getElementById('aside-notif-btn');
  if (notifBtn) {
    notifBtn.classList.add('bell-ring-anim');
    setTimeout(function () {
      notifBtn.classList.remove('bell-ring-anim');
    }, 1500);

    var badge = document.getElementById('aside-notif-badge');
    if (badge) {
      var current = parseInt(badge.textContent) || 0;
      badge.textContent = current + 1;
      badge.style.display = 'inline-flex';
    }
  }

  if (window._loadNotifications) window._loadNotifications();
};

/* Override global alert para capturar alertas del sistema */
var originalAlert = window.alert;
window.alert = function (msg) {
  window.addNotification('Alerta del sistema', msg, 'exclamation-triangle-fill', '#ef4444');
};

document.addEventListener('DOMContentLoaded', function () {
  var notifBtn = document.getElementById('aside-notif-btn');
  var notifPanel = document.getElementById('aside-notif-panel');
  var notifClose = document.getElementById('aside-notif-close');
  var notifRefresh = document.getElementById('aside-notif-refresh');
  var refreshIcon = document.getElementById('aside-refresh-icon');

  function toggleNotifPanel(forceOpen) {
    if (!notifPanel || !notifBtn) return;
    var isHidden = notifPanel.classList.contains('d-none');
    if (isHidden || forceOpen === true) {
      notifPanel.classList.remove('d-none');
      notifPanel.classList.add('d-flex');
      notifBtn.setAttribute('aria-expanded', 'true');
      loadNotifications();
    } else if (!forceOpen) {
      closeNotifPanel();
    }
  }
  window._toggleNotifPanel = toggleNotifPanel;

  function closeNotifPanel() {
    if (!notifPanel || !notifBtn) return;
    notifPanel.classList.remove('d-flex');
    notifPanel.classList.add('d-none');
    notifBtn.setAttribute('aria-expanded', 'false');
  }

  function renderNotifIcon(item) {
    var ico = item.icono || 'info-circle';
    var color = item.color || '#094D92';

    if (item.tipo === 'activo') color = '#0284c7';
    else if (item.tipo === 'vencido' || item.tipo === 'vencido_no_marcado') color = '#dc2626';
    else if (item.tipo === 'proximo' || item.tipo === 'stock_bajo') color = '#d97706';
    else if (item.tipo === 'devolucion') color = '#094D92';
    else if (!color || color === 'var(--navy)' || color === 'var(--cream)') color = '#094D92';

    if (typeof ico === 'string' && ico.startsWith('<svg')) {
      return (
        '<div class="flex-shrink-0 aside-notif-row-icon" style="color: ' +
        color +
        ' !important;"><span style="color: ' +
        color +
        ' !important;">' +
        ico +
        '</span></div>'
      );
    }

    var iconClass = 'bi-info-circle';
    if (ico === 'exclamation-octagon-fill' || ico === 'error') iconClass = 'bi-exclamation-octagon-fill';
    else if (ico === 'exclamation-triangle-fill' || ico === 'warning') iconClass = 'bi-exclamation-triangle-fill';
    else if (ico === 'exclamation-circle') iconClass = 'bi-exclamation-circle';
    else if (ico === 'box-seam') iconClass = 'bi-box-seam';
    else if (ico === 'alarm') iconClass = 'bi-alarm';
    else if (ico === 'arrow-counterclockwise') iconClass = 'bi-arrow-counterclockwise';
    else if (ico === 'tools') iconClass = 'bi-tools';
    else if (typeof ico === 'string' && ico.length > 0) {
      iconClass = ico.startsWith('bi-') ? ico : 'bi-' + ico;
    }

    return (
      '<div class="flex-shrink-0 aside-notif-row-icon" style="color: ' +
      color +
      ' !important; font-size: 1.15rem; display: flex; align-items: center;"><i class="bi ' +
      iconClass +
      '" style="color: ' +
      color +
      ' !important; opacity: 1 !important;"></i></div>'
    );
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function loadNotifications() {
    var loading = document.getElementById('aside-notif-loading');
    var empty = document.getElementById('aside-notif-empty');
    var list = document.getElementById('aside-notif-list');
    var countBadge = document.getElementById('aside-panel-count');
    var bellBadge = document.getElementById('aside-notif-badge');
    var ts = document.getElementById('aside-notif-ts');

    if (!list || !loading || !empty) return;

    loading.classList.remove('d-none');
    empty.classList.add('d-none');
    list.innerHTML = '';
    if (refreshIcon) refreshIcon.style.animation = 'spin 1s linear infinite';

    var notifUrl = (notifPanel && notifPanel.getAttribute('data-url')) || '/api/notificaciones/';

    fetch(notifUrl)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        loading.classList.add('d-none');
        if (refreshIcon) refreshIcon.style.animation = '';

        var serverItems = data.items || [];
        var allItems = window.localNotifications.concat(serverItems);
        var total = allItems.length;

        if (total > 0) {
          if (bellBadge) {
            bellBadge.textContent = total;
            bellBadge.style.display = 'inline-flex';
          }
          if (countBadge) {
            countBadge.textContent = total;
            countBadge.classList.remove('d-none');
          }
        } else {
          if (bellBadge) bellBadge.style.display = 'none';
          if (countBadge) countBadge.classList.add('d-none');
        }

        var now = new Date();
        if (ts) ts.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        if (total > 0) {
          empty.classList.add('d-none');
          allItems.forEach(function (item) {
            var row = document.createElement('a');
            row.href = item.url || '#';
            row.className = 'aside-notif-row';

            row.innerHTML =
              renderNotifIcon(item) +
              '<div class="aside-notif-row-body">' +
              '<div class="aside-notif-row-title">' +
              escapeHtml(item.titulo) +
              '</div>' +
              '<div class="aside-notif-row-desc">' +
              escapeHtml(item.desc) +
              '</div>' +
              '</div>';

            list.appendChild(row);
          });
        } else {
          empty.classList.remove('d-none');
        }
      })
      .catch(function (err) {
        console.error('Error loading notifications:', err);
        loading.classList.add('d-none');

        if (window.localNotifications.length > 0) {
          window.localNotifications.forEach(function (item) {
            var row = document.createElement('a');
            row.href = item.url || '#';
            row.className = 'aside-notif-row';

            row.innerHTML =
              renderNotifIcon(item) +
              '<div class="aside-notif-row-body">' +
              '<div class="aside-notif-row-title">' +
              escapeHtml(item.titulo) +
              '</div>' +
              '<div class="aside-notif-row-desc">' +
              escapeHtml(item.desc) +
              '</div>' +
              '</div>';
            list.appendChild(row);
          });
        } else {
          empty.classList.remove('d-none');
        }
        if (refreshIcon) refreshIcon.style.animation = '';
      });
  }
  window._loadNotifications = loadNotifications;

  // Bind events
  if (notifBtn) {
    notifBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      toggleNotifPanel();
    });
  }
  if (notifClose) {
    notifClose.addEventListener('click', function (e) {
      e.stopPropagation();
      closeNotifPanel();
    });
  }
  if (notifRefresh) {
    notifRefresh.addEventListener('click', function (e) {
      e.stopPropagation();
      loadNotifications();
    });
  }
  if (notifPanel) {
    notifPanel.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  }

  document.addEventListener('click', function () {
    closeNotifPanel();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeNotifPanel();
  });

  /* Scrape global Django messages and push them locally */
  document.querySelectorAll('.alert-dismissible, .scrape-notif').forEach(function (alertEl) {
    var span = alertEl.querySelector('span:not(.btn-close):not([aria-hidden])');
    var text = span ? span.textContent.trim() : '';

    if (!text || text.length < 2) {
      text = Array.from(alertEl.childNodes)
        .filter((node) => node.nodeType === 3)
        .map((node) => node.textContent.trim())
        .join(' ');
    }

    if (!text || text.length < 2) {
      text = alertEl.textContent.replace(/Cerrar|×/gi, '').trim().replace(/\s+/g, ' ');
    }

    if (text) {
      var isError = alertEl.classList.contains('alert-danger') || alertEl.classList.contains('error');
      var isWarning = alertEl.classList.contains('warning-notif');

      var title = isError ? 'Aviso del sistema' : isWarning ? 'Acción requerida' : 'Operación exitosa';
      var icon = isError ? 'exclamation-octagon-fill' : isWarning ? 'exclamation-triangle-fill' : 'check-circle-fill';
      var color = isError ? '#ef4444' : isWarning ? '#c4900a' : '#22c55e';

      window.addNotification(title, text, icon, color);
      alertEl.remove();
    }
  });

  loadNotifications();
});
