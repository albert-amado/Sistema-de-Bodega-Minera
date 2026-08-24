/* ═══════════════════════════════════════════════════════════
   static/js/form-validation.js
   Validación en tiempo real con ✓ animado en todos los campos
   ═══════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ── Campos que no deben validarse visualmente ── */
  var SKIP_SELECTORS = [
    '[data-no-validate]',
    'input[name="q"]',
    'input[name="busqueda"]',
    '[type="hidden"]',
    '[type="submit"]',
    '[type="button"]',
    '[type="reset"]',
    '[type="checkbox"]',
    '[type="radio"]',
    '.dt-search input',           /* DataTables search */
    '.dataTables_filter input',
    '.dt-length select',          /* DataTables length */
    '.dataTables_length select',
    '.dt-container input',        /* Broad DataTables escape */
    '.dt-container select',
    '.dataTables_wrapper input',
    '.dataTables_wrapper select',
    '[id^="dt-"]',
    '.sol-del-btn',
    '.btn-close',
    '[data-bs-dismiss]',
  ];

  /* ── Crea el wrapper si no existe ── */
  function wrapField(field) {
    /* Evitar doble-wrap */
    if (field.closest('.fv-wrap')) return;

    var parent = field.parentElement;
    if (!parent) return;

    /* No wrappear dentro de input-groups de Bootstrap o personalizados (se ve mal) */
    if (parent.classList.contains('input-group') || parent.classList.contains('input-group-mine')) {
      parent.classList.add('fv-wrap');
      return;
    }

    var wrap = document.createElement('div');
    wrap.className = 'fv-wrap';
    parent.insertBefore(wrap, field);
    wrap.appendChild(field);
  }

  /* ── Crea o selecciona el ícono de estado ── */
  function getIcon(field) {
    var wrap = field.closest('.fv-wrap');
    if (!wrap) return null;
    var existing = wrap.querySelector('.fv-icon');
    if (existing) return existing;

    var icon = document.createElement('span');
    icon.className = 'fv-icon';
    icon.setAttribute('aria-hidden', 'true');
    wrap.appendChild(icon);
    return icon;
  }

  /* ── SVG checks y X ── */
  var SVG_CHECK =
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">' +
    '<polyline points="4 10 8 14 16 6"/>' +
    '</svg>';

  var SVG_X =
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">' +
    '<line x1="5" y1="5" x2="15" y2="15"/>' +
    '<line x1="15" y1="5" x2="5" y2="15"/>' +
    '</svg>';

  /* ── Valida un campo individualmente ── */
  function isFieldValid(field) {
    var tag = field.tagName.toLowerCase();
    var val = (field.value || '').trim();

    /* Campos no requeridos y vacíos → neutro (no marcar como error) */
    if (!field.required && val === '' && tag !== 'select') return null;

    /* Select */
    if (tag === 'select') {
      return field.required ? (val !== '' && val !== '0') : null;
    }

    /* Textarea */
    if (tag === 'textarea') {
      if (!field.required && val === '') return null;
      var minLen = parseInt(field.getAttribute('minlength') || '1', 10);
      return val.length >= minLen;
    }

    /* Input email */
    if (field.type === 'email') {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    }

    /* Input number */
    if (field.type === 'number') {
      var num = parseFloat(val);
      var min = field.hasAttribute('min') ? parseFloat(field.min) : -Infinity;
      var max = field.hasAttribute('max') ? parseFloat(field.max) : Infinity;
      return !isNaN(num) && num >= min && num <= max;
    }

    /* Input date */
    if (field.type === 'date') {
      if (!field.required && val === '') return null;
      return val !== '';
    }

    /* Password */
    if (field.type === 'password') {
      return val.length >= (parseInt(field.getAttribute('minlength') || '1', 10));
    }

    /* Text genérico */
    if (!field.required && val === '') return null;
    var minL = parseInt(field.getAttribute('minlength') || '1', 10);
    return val.length >= minL;
  }

  /* ── Aplica el estado visual ── */
  function applyState(field, valid) {
    var icon = getIcon(field);
    if (!icon) return;

    var wrap = field.closest('.fv-wrap');

    if (valid === true) {
      icon.className = 'fv-icon fv-icon--ok fv-icon--pop';
      icon.innerHTML = SVG_CHECK;
      field.classList.remove('fv-invalid');
      field.classList.add('fv-valid');
      if (wrap && wrap.classList.contains('input-group-mine')) {
        wrap.classList.remove('fv-invalid');
        wrap.classList.add('fv-valid');
      }
      /* Quitar clase de animación al finalizar */
      icon.addEventListener('animationend', function () {
        icon.classList.remove('fv-icon--pop');
      }, { once: true });
    } else if (valid === false) {
      icon.className = 'fv-icon fv-icon--err';
      icon.innerHTML = SVG_X;
      field.classList.remove('fv-valid');
      field.classList.add('fv-invalid');
      if (wrap && wrap.classList.contains('input-group-mine')) {
        wrap.classList.remove('fv-valid');
        wrap.classList.add('fv-invalid');
      }
    } else {
      /* Neutro: borrar */
      icon.className = 'fv-icon';
      icon.innerHTML = '';
      field.classList.remove('fv-valid', 'fv-invalid');
      if (wrap && wrap.classList.contains('input-group-mine')) {
        wrap.classList.remove('fv-valid', 'fv-invalid');
      }
    }
  }

  /* ── Handler de evento ── */
  function onInteract(e) {
    var field = e.target;
    if (!isValidatable(field)) return;

    /* Marcar como "tocado" */
    field.dataset.fvTouched = '1';

    /* Leer estado solo si ya fue tocado (o es blur) */
    var valid = isFieldValid(field);
    applyState(field, valid);
  }

  function onBlur(e) {
    var field = e.target;
    if (!isValidatable(field)) return;
    field.dataset.fvTouched = '1';
    var valid = isFieldValid(field);
    applyState(field, valid);
  }

  /* ── Comprueba si un campo debe procesarse ── */
  function isValidatable(field) {
    var tag = field.tagName && field.tagName.toLowerCase();
    if (!tag || !['input', 'select', 'textarea'].includes(tag)) return false;
    
    /* Skip DataTables explicitly (their layouts break easily) */
    if (field.closest('.dt-container') || field.closest('.dataTables_wrapper')) return false;

    for (var i = 0; i < SKIP_SELECTORS.length; i++) {
      try { if (field.matches(SKIP_SELECTORS[i])) return false; } catch (ex) {}
    }
    return true;
  }

  /* ── Inicializa todos los campos existentes ── */
  function initFields(root) {
    root = root || document;
    root.querySelectorAll('input, select, textarea').forEach(function (field) {
      if (!isValidatable(field)) return;
      wrapField(field);
    });
  }

  /* ── Delegación de eventos al document ── */
  document.addEventListener('input',  onInteract, true);
  document.addEventListener('change', onInteract, true);
  document.addEventListener('blur',   onBlur,     true);

  /* ── Observer para campos añadidos dinámicamente (ej. filas del wizard) ── */
  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      m.addedNodes.forEach(function (node) {
        if (node.nodeType !== 1) return;
        var fields = node.querySelectorAll
          ? node.querySelectorAll('input, select, textarea')
          : [];
        fields.forEach(function (field) {
          if (isValidatable(field)) wrapField(field);
        });
        if (node.matches && node.matches('input, select, textarea') && isValidatable(node)) {
          wrapField(node);
        }
      });
    });
  });

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initFields(document);
    observer.observe(document.body, { childList: true, subtree: true });
  });

})();
