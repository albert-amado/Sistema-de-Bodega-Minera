/**
 * static/js/base.js
 * Funcionalidad global del sistema: overlay de carga, control responsivo del aside y utilidades dinámicas.
 */

document.addEventListener('DOMContentLoaded', function () {
  var overlay = document.getElementById('page-loading-overlay');

  function showLoading() {
    if (overlay) overlay.style.display = 'flex';
  }

  function hideLoading() {
    if (overlay) overlay.style.display = 'none';
  }

  window.showLoading = showLoading;
  window.hideLoading = hideLoading;

  window.addEventListener('pageshow', function () {
    hideLoading();
  });

  function isSamePageAnchor(anchor) {
    if (!anchor.href) return false;
    try {
      var url = new URL(anchor.href, location.href);
      return (
        url.origin === location.origin &&
        url.pathname === location.pathname &&
        (url.hash || anchor.getAttribute('href') === '#')
      );
    } catch (e) {
      return false;
    }
  }

  document.addEventListener('click', function (event) {
    var anchor = event.target.closest('a');
    if (!anchor) return;
    if (anchor.target === '_blank' || anchor.hasAttribute('download')) return;
    if (isSamePageAnchor(anchor)) return;
    if (anchor.href && anchor.href !== location.href) {
      showLoading();
    }
  });

  document.addEventListener('submit', function (e) {
    if (e.defaultPrevented) return;
    setTimeout(function () {
      if (!e.defaultPrevented) {
        showLoading();
      }
    }, 50);
  });

  window.addEventListener('beforeunload', function () {
    showLoading();
  });

  // Aplicar colores de fondo dinámicos desde atributos de datos
  document.querySelectorAll('[data-dynamic-bg]').forEach(function (el) {
    var color = el.getAttribute('data-dynamic-bg');
    if (color) el.style.backgroundColor = color;
  });

  // ── Control del Aside / Sidebar en dispositivos móviles y TV ──
  var toggleBtn = document.getElementById('btnToggleSidebar');
  var asideOverlay = document.getElementById('asideOverlay');
  var asideEl = document.querySelector('aside');

  function openAside() {
    if (asideEl) {
      asideEl.classList.add('aside-open');
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
      var firstLink = asideEl.querySelector('a.nav-link, a, button');
      if (firstLink && window.innerWidth <= 768) {
        setTimeout(function () { firstLink.focus(); }, 100);
      }
    }
    if (asideOverlay) asideOverlay.classList.add('active');
  }

  function closeAside() {
    if (asideEl) {
      asideEl.classList.remove('aside-open');
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', 'false');
        if (document.activeElement && asideEl.contains(document.activeElement)) {
          toggleBtn.focus();
        }
      }
    }
    if (asideOverlay) asideOverlay.classList.remove('active');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (asideEl && asideEl.classList.contains('aside-open')) {
        closeAside();
      } else {
        openAside();
      }
    });
  }

  if (asideOverlay) {
    asideOverlay.addEventListener('click', closeAside);
  }

  // ── Navegación D-pad / Control Remoto / Teclado Accesible ──
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      closeAside();
      return;
    }

    // Navegación D-pad en el menú lateral con flechas arriba / abajo
    if (asideEl && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      var activeEl = document.activeElement;
      if (activeEl && asideEl.contains(activeEl)) {
        var focusableItems = Array.prototype.slice.call(
          asideEl.querySelectorAll('a.nav-link, a[href], button:not([disabled])')
        );
        var currentIndex = focusableItems.indexOf(activeEl);
        if (currentIndex !== -1) {
          e.preventDefault();
          var nextIndex = e.key === 'ArrowDown'
            ? (currentIndex + 1) % focusableItems.length
            : (currentIndex - 1 + focusableItems.length) % focusableItems.length;
          focusableItems[nextIndex].focus();
        }
      }
    }
  });
});
