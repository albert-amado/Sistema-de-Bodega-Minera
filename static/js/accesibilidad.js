(function () {

  /* ══════════════════════════════════════════
     ESTADO inicial desde localStorage
  ══════════════════════════════════════════ */
  var fontSize  = parseInt(localStorage.getItem('acc_fs') || '100');
  var contrast  = localStorage.getItem('acc_contrast') === 'true';
  var darkMode  = localStorage.getItem('acc_dark')     === 'true';
  // El modo claro es predeterminado a menos que acc_dark sea true
  var lightMode = localStorage.getItem('acc_light')    !== 'false' && !darkMode;
  var antigravity = localStorage.getItem('acc_antigravity') === 'true';
  var compactTable = localStorage.getItem('acc_compact_table') === 'true';

  /* ══════════════════════════════════════════
     APLICAR DENSIDAD DE TABLAS
  ══════════════════════════════════════════ */
  function applyTableDensity(compact) {
    compactTable = compact;
    if (compact) {
      document.body.classList.add('table-compact');
      localStorage.setItem('acc_compact_table', 'true');
    } else {
      document.body.classList.remove('table-compact');
      localStorage.setItem('acc_compact_table', 'false');
    }
  }

  /* ══════════════════════════════════════════
     APLICAR TAMAÑO DE LETRA DE ACCESIBILIDAD
  ══════════════════════════════════════════ */
  function applyFontSize(size) {
    fontSize = size;
    localStorage.setItem('acc_fs', size);
    var scale = size / 100;
    document.documentElement.style.fontSize = size + '%';
    document.documentElement.style.setProperty('--acc-font-scale', scale);

    var fontStyle = document.getElementById('acc-font-scale-style');
    if (!fontStyle) {
      fontStyle = document.createElement('style');
      fontStyle.id = 'acc-font-scale-style';
      document.head.appendChild(fontStyle);
    }
    fontStyle.textContent = 'body { font-size: calc(0.9375rem * ' + scale + ') !important; }';
  }

  applyFontSize(fontSize);

  /* ══════════════════════════════════════════
     ASIDE: los estilos de aside para modo claro y oscuro 
     están definidos directamente en style.css
  ══════════════════════════════════════════ */
  function applyAsideDark() {
    var aside = document.querySelector('aside');
    if (aside) aside.setAttribute('data-acc-dark', '1');
  }

  function resetAsideDark() {
    var aside = document.querySelector('aside');
    if (aside) aside.removeAttribute('data-acc-dark');
  }

  /* ══════════════════════════════════════════
     APLICAR ESTADO GUARDADO
  ══════════════════════════════════════════ */
  if (contrast) document.body.classList.add('high-contrast');
  if (antigravity) document.body.classList.add('antigravity-active');
  if (compactTable) document.body.classList.add('table-compact');
  if (darkMode) {
    document.body.classList.add('dark-mode');
    document.body.classList.remove('light-mode');
    applyAsideDark();
  } else {
    document.body.classList.add('light-mode');
    document.body.classList.remove('dark-mode');
    resetAsideDark();
  }

  /* ══════════════════════════════════════════
     SYNC botones
  ══════════════════════════════════════════ */
  function syncButtons() {
    var c = document.getElementById('acc-btn-contrast');
    var d = document.getElementById('acc-btn-dark');
    var l = document.getElementById('acc-btn-light');
    var a = document.getElementById('acc-btn-antigravity');
    var den = document.getElementById('acc-btn-density');
    if (c) c.classList.toggle('acc-active', contrast);
    if (d) d.classList.toggle('acc-active', darkMode);
    if (l) l.classList.toggle('acc-active', lightMode);
    if (a) a.classList.toggle('acc-active', antigravity);
    if (den) den.classList.toggle('acc-active', compactTable);
  }

  /* ══════════════════════════════════════════
     REPINTAR panel para recalcular CSS vars
  ══════════════════════════════════════════ */
  function repaintPanel() {
    var p = document.getElementById('acc-panel');
    if (!p || !p.classList.contains('acc-open')) return;
    p.style.display = 'none';
    p.offsetHeight; // force reflow
    p.style.display = '';
    p.classList.add('acc-open');
  }

  /* ══════════════════════════════════════════
     EVENTOS del widget
  ══════════════════════════════════════════ */
  var toggle = document.getElementById('acc-toggle');
  var panel  = document.getElementById('acc-panel');

  if (toggle && panel) {

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      panel.classList.toggle('acc-open');
    });

    document.addEventListener('click', function (e) {
      var widget = document.getElementById('acc-widget');
      if (widget && !widget.contains(e.target)) panel.classList.remove('acc-open');
    });

    var contrastBtn = document.getElementById('acc-btn-contrast');
    if (contrastBtn) {
      contrastBtn.addEventListener('click', function () {
        contrast = !contrast;
        document.body.classList.toggle('high-contrast', contrast);
        localStorage.setItem('acc_contrast', contrast);
        syncButtons();
      });
    }

    var darkBtn = document.getElementById('acc-btn-dark');
    if (darkBtn) {
      darkBtn.addEventListener('click', function () {
        darkMode = !darkMode;
        if (darkMode) {
          lightMode = false;
          document.body.classList.remove('light-mode');
          document.body.classList.add('dark-mode');
          localStorage.setItem('acc_light', 'false');
          localStorage.setItem('acc_dark', 'true');
          applyAsideDark();
        } else {
          lightMode = true;
          document.body.classList.add('light-mode');
          document.body.classList.remove('dark-mode');
          localStorage.setItem('acc_light', 'true');
          localStorage.setItem('acc_dark', 'false');
          resetAsideDark();
        }
        syncButtons();
        repaintPanel();
      });
    }

    var lightBtn = document.getElementById('acc-btn-light');
    if (lightBtn) {
      lightBtn.addEventListener('click', function () {
        lightMode = !lightMode;
        if (lightMode) {
          darkMode = false;
          document.body.classList.remove('dark-mode');
          document.body.classList.add('light-mode');
          localStorage.setItem('acc_dark', 'false');
          localStorage.setItem('acc_light', 'true');
          resetAsideDark();
        } else {
          localStorage.setItem('acc_light', 'false');
        }
        syncButtons();
        repaintPanel();
      });
    }

    var antiBtn = document.getElementById('acc-btn-antigravity');
    if (antiBtn) {
      antiBtn.addEventListener('click', function () {
        antigravity = !antigravity;
        document.body.classList.toggle('antigravity-active', antigravity);
        localStorage.setItem('acc_antigravity', antigravity);
        syncButtons();
      });
    }

    var densityBtn = document.getElementById('acc-btn-density');
    if (densityBtn) {
      densityBtn.addEventListener('click', function () {
        applyTableDensity(!compactTable);
        syncButtons();
      });
    }

    var plusBtn = document.getElementById('acc-btn-plus');
    if (plusBtn) {
      plusBtn.addEventListener('click', function () {
        if (fontSize >= 150) return;
        applyFontSize(fontSize + 10);
      });
    }

    var minusBtn = document.getElementById('acc-btn-minus');
    if (minusBtn) {
      minusBtn.addEventListener('click', function () {
        if (fontSize <= 70) return;
        applyFontSize(fontSize - 10);
      });
    }

    var resetBtn = document.getElementById('acc-btn-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        contrast = false; darkMode = false; lightMode = true; antigravity = false; compactTable = false;
        document.body.classList.remove('high-contrast', 'dark-mode', 'antigravity-active', 'table-compact');
        document.body.classList.add('light-mode');
        applyFontSize(100);
        resetAsideDark();
        localStorage.removeItem('acc_contrast');
        localStorage.setItem('acc_dark', 'false');
        localStorage.setItem('acc_light', 'true');
        localStorage.removeItem('acc_antigravity');
        localStorage.setItem('acc_compact_table', 'false');
        syncButtons();
      });
    }

    syncButtons();
  }

})();

/* ══════════════════════════════════════════
   FUNCION DE GRAVEDAD / ANTIGRAVEDAD GLOBAL
   Exponemos window.calculateGravityEffect
   ══════════════════════════════════════════ */
window.calculateGravityEffect = function (targetEntity, mode, deltaTime) {
  var dt = deltaTime || 0.016;
  if (!targetEntity.position) targetEntity.position = { x: 0, y: 0 };
  if (!targetEntity.velocity) targetEntity.velocity = { x: 0, y: 0 };
  if (!targetEntity.acceleration) targetEntity.acceleration = { x: 0, y: 0 };

  var gravity = 9.81;
  var mass = targetEntity.mass || 1.0;

  if (mode === 'antygraviti') {
    // Vector de fuerza negativa (hacia arriba)
    // En Canvas 2D, Y apunta hacia abajo, por lo que la fuerza ascendente es negativa.
    var upwardForce = -gravity * mass * 1.5; 
    targetEntity.acceleration.y = (upwardForce / mass) + gravity;
    targetEntity.velocity.y += targetEntity.acceleration.y * dt;
    targetEntity.velocity.y *= 0.95; // Fricción amortiguadora para flotar de forma estable
  } else {
    // Gravedad normal
    targetEntity.acceleration.y = gravity;
    targetEntity.velocity.y += targetEntity.acceleration.y * dt;
  }

  targetEntity.position.y += targetEntity.velocity.y;
};