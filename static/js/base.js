/**
 * static/js/base.js
 * Funcionalidad global del sistema: overlay de carga, control responsivo del aside y utilidades dinámicas.
 */

document.addEventListener('DOMContentLoaded', function () {
  var overlay = document.getElementById('page-loading-overlay');
  var mainContent = document.getElementById('main-content');
  var prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var navTimer = null;

  function showLoading() {
    if (overlay) {
      overlay.classList.add('is-visible');
      overlay.setAttribute('aria-hidden', 'false');
    }
  }

  function hideLoading() {
    if (navTimer) {
      clearTimeout(navTimer);
      navTimer = null;
    }
    if (mainContent) {
      mainContent.classList.remove('is-leaving');
    }
    if (overlay) {
      overlay.classList.remove('is-visible');
      overlay.setAttribute('aria-hidden', 'true');
    }
  }

  window.showLoading = showLoading;
  window.hideLoading = hideLoading;

  window.addEventListener('pageshow', function () {
    hideLoading();
  });

  function isSamePageAnchor(anchor) {
    var rawHref = anchor.getAttribute('href');
    if (!rawHref || rawHref === '#' || rawHref.indexOf('javascript:') === 0) return true;
    try {
      var url = new URL(anchor.href, location.href);
      return (
        url.origin === location.origin &&
        url.pathname === location.pathname &&
        url.search === location.search
      );
    } catch (e) {
      return false;
    }
  }

  function isDownloadLink(anchor) {
    if (anchor.hasAttribute('download')) return true;
    try {
      var path = new URL(anchor.href, location.href).pathname.toLowerCase();
      return /exportar|descargar|excel|xlsx|pdf|backup/.test(path);
    } catch (e) {
      return false;
    }
  }

  function highlightSidebarLink(anchor) {
    var sidebarNav = anchor.closest('#aside-sidebar .aside-nav');
    if (!sidebarNav) return;
    sidebarNav.querySelectorAll('a.nav-link.active').forEach(function (el) {
      if (el !== anchor && !el.hasAttribute('data-bs-toggle')) {
        el.classList.remove('active');
      }
    });
    anchor.classList.add('active');
  }

  document.addEventListener('click', function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    var anchor = event.target.closest('a');
    if (!anchor) return;
    if (anchor.target === '_blank' || anchor.hasAttribute('data-bs-toggle') || isDownloadLink(anchor)) return;
    if (isSamePageAnchor(anchor)) return;

    var destUrl;
    try {
      destUrl = new URL(anchor.href, location.href);
    } catch (e) {
      return;
    }
    if (destUrl.origin !== location.origin) return;

    highlightSidebarLink(anchor);

    if (prefersReducedMotion || !mainContent) {
      showLoading();
      return;
    }

    event.preventDefault();
    mainContent.classList.add('is-leaving');
    showLoading();

    var targetHref = anchor.href;
    navTimer = setTimeout(function () {
      window.location.href = targetHref;
    }, 150);
  });

  document.addEventListener('submit', function (e) {
    if (e.defaultPrevented) return;
    var form = e.target;
    if (form && form.target === '_blank') return;
    setTimeout(function () {
      if (!e.defaultPrevented) {
        showLoading();
      }
    }, 50);
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
