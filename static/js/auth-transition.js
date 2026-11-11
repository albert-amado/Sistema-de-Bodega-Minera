/* ==========================================================================
   AUTH SENA — Transición animada entre Inicio de sesión y Registro
   Las vistas son páginas Django distintas (/ y /registro/). Este script:
     1. Al hacer clic en una pestaña o enlace de alternancia, desliza el
        indicador de pestañas y anima la salida del formulario (fade + slide).
     2. Navega a la otra página cuando termina la animación.
     3. En la página destino, anima la entrada desde el lado opuesto.
   La dirección se guarda en sessionStorage. El estado inicial de entrada se
   aplica desde un script inline en <head> para evitar parpadeos.
   ========================================================================== */
(function () {
  'use strict';

  var LEAVE_MS = 320;
  var KEY = 'sbm-auth-transition';
  var root = document.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var tabs = document.querySelector('.auth-tabs');
  if (!tabs) return;

  // Vista actual según la pestaña activa ("login" | "registro")
  var tabEls = tabs.querySelectorAll('.tab-btn');
  var current = tabEls[1] && tabEls[1].classList.contains('on') ? 'registro' : 'login';

  /* ---------- ENTRADA ---------- */
  var entering = root.classList.contains('auth-enter-right') || root.classList.contains('auth-enter-left');
  if (entering) {
    // El pill arranca en la posición de la página anterior
    tabs.setAttribute('data-active', current === 'registro' ? 'login' : 'registro');
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        root.classList.remove('auth-enter-right', 'auth-enter-left');
        tabs.setAttribute('data-active', current);
      });
    });
  } else {
    tabs.setAttribute('data-active', current);
  }

  /* ---------- SALIDA ---------- */
  var navigating = false;

  function goTo(url, target) {
    if (navigating || target === current) return;
    navigating = true;

    var forward = target === 'registro';
    try { sessionStorage.setItem(KEY, forward ? 'right' : 'left'); } catch (e) {}

    if (reduceMotion) { window.location.href = url; return; }

    // Mover pestaña activa y pill de inmediato
    tabEls.forEach(function (t, i) {
      t.classList.toggle('on', (i === 1) === forward);
    });
    tabs.setAttribute('data-active', target);
    root.classList.add(forward ? 'auth-leave-left' : 'auth-leave-right');

    setTimeout(function () { window.location.href = url; }, LEAVE_MS);
  }

  // Pestañas y enlaces "¿No tienes cuenta? / ¿Ya tienes cuenta?"
  document.querySelectorAll('.auth-tabs a.tab-btn, [data-auth-nav]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return; // permitir abrir en nueva pestaña
      e.preventDefault();
      var target = link.getAttribute('data-auth-nav') || (current === 'login' ? 'registro' : 'login');
      goTo(link.href, target);
    });
  });

  // Si el usuario vuelve con el botón "Atrás" (bfcache), restablecer estado
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      navigating = false;
      root.classList.remove('auth-leave-left', 'auth-leave-right');
      tabEls.forEach(function (t, i) { t.classList.toggle('on', (i === 1) === (current === 'registro')); });
      tabs.setAttribute('data-active', current);
    }
  });
})();

