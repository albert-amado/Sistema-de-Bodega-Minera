/* ═══════════════════════════════════════════
   static/js/prestamos.js
   Lógica del wizard y modales para Préstamos
  ═══════════════════════════════════════════ */


/* ═══════════════════════════════════════════
   MODAL APROBAR
═══════════════════════════════════════════ */
var _aprModal = null;
function abrirAprobar(pk, nombre, doc, motivo, fecha, items) {
  document.getElementById('apr-pk').value          = pk;
  document.getElementById('apr-titulo').textContent = 'Aprobar solicitud #' + pk;
  document.getElementById('apr-subtitulo').textContent = 'Verifica la información antes de entregar';
  document.getElementById('apr-nombre').textContent = nombre;
  document.getElementById('apr-doc').textContent   = doc;
  document.getElementById('apr-fecha').textContent  = fecha;
  var motivoWrap = document.getElementById('apr-motivo-wrap');
  if (motivo && motivo.trim()) {
    document.getElementById('apr-motivo').textContent = motivo;
    motivoWrap.style.display = 'block';
  } else {
    motivoWrap.style.display = 'none';
  }
  document.getElementById('rch-pk').value = pk;
  document.getElementById('rch-id').textContent = '#' + pk;
  var container = document.getElementById('apr-items-container');
  container.innerHTML = '';
  var hayStockInsuficiente = false;
  items.forEach(function (item) {
    var insuficiente = item.stock < item.cantidad;
    if (insuficiente) hayStockInsuficiente = true;
    var row = document.createElement('div');
    row.style.cssText = 'margin-bottom:.85rem; padding:1rem; border-radius:var(--radius-md);' +
      'border:1px solid ' + (insuficiente ? 'rgba(152,71,62,.25)' : 'rgba(9,77,146,.12)') + ';' +
      'background:' + (insuficiente ? 'rgba(152,71,62,.04)' : 'rgba(9,77,146,.03)') + ';';
    row.innerHTML =
      '<div style="display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap;">' +
        '<div>' +
          '<div style="font-weight:700; font-size:.92rem; color:var(--text-main);">' + escapeHtml(item.nombre) + '</div>' +
          '<div style="font-family:var(--font-mono); font-size:.78rem; color:var(--text-muted); margin-top:.1rem;">' +
            escapeHtml(item.sku) + ' · Solicitado: <strong>' + item.cantidad + '</strong>' +
            ' · Stock disponible: <strong style="color:' + (insuficiente ? 'var(--rust)' : 'var(--sage)') + ';">' + item.stock + '</strong>' +
          '</div>' +
          (insuficiente ? '<div style="font-size:.74rem; color:var(--rust); margin-top:.25rem; font-weight:600;">⚠ Stock insuficiente</div>' : '') +
        '</div>' +
      '</div>';
    container.appendChild(row);
  });
  var btnAprobar = document.getElementById('apr-btn-aprobar');
  btnAprobar.disabled = hayStockInsuficiente;
  if (!_aprModal) _aprModal = new bootstrap.Modal(document.getElementById('modalAprobarPrestamo'));
  _aprModal.show();
}

function abrirRechazar() {
  if (_aprModal) _aprModal.hide();
  setTimeout(function () {
    new bootstrap.Modal(document.getElementById('modalRechazarPrestamo')).show();
  }, 350);
}
function abrirDevolver(pk, usuario) {
  document.getElementById('dev-pk').textContent      = pk;
  document.getElementById('dev-usuario').textContent = usuario;
  new bootstrap.Modal(document.getElementById('modalDevolverPrestamo')).show();
}
function abrirDevoluciones() {
  var pk = document.getElementById('dev-pk').textContent;
  if (pk) window.location.href = '/devoluciones/?prestamo=' + pk;
}

document.getElementById('modalEditarPrestamo').addEventListener('show.bs.modal', function (e) {
  var btn = e.relatedTarget;
  document.getElementById('edit_pk').value            = btn.dataset.pk;
  document.getElementById('edit_observaciones').value = btn.dataset.observaciones || '';
});

/* ═══════════════════════════════════════════
   WIZARD — NUEVO PRÉSTAMO
═══════════════════════════════════════════ */
var currentStep = 1;
var maxSteps    = 4;

// Lee el contenido seguro y lo transforma en objeto JS inmediatamente
var productosData = [];
var usuariosData  = [];
try {
  var prodEl = document.getElementById('productos-data');
  if (prodEl) productosData = JSON.parse(prodEl.textContent);
  var usrEl = document.getElementById('usuarios-data');
  if (usrEl) usuariosData = JSON.parse(usrEl.textContent);
} catch (e) {
  console.error("Error al parsear datos de productos/usuarios:", e);
}

console.log("Productos cargados:", productosData);
console.log("Usuarios cargados:", usuariosData);

var wizardSteps = [
  { id:1, label:'Responsable' },
  { id:2, label:'Herramientas' },
  { id:3, label:'Detalles' },
  { id:4, label:'Resumen' },
];

function renderWizardProgress() {
  var bar = document.getElementById('wizard-progress-bar');
  if (!bar) return;
  bar.innerHTML = wizardSteps.map(function (step, idx) {
    var cls = 'wizard-step-dot';
    if (idx < currentStep - 1) cls += ' wizard-done';
    if (idx === currentStep - 1) cls += ' wizard-active';
    var inner = idx < currentStep - 1
      ? '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8"><polyline points="20 6 9 17 4 12"/></svg>'
      : step.id;
    return '<div class="' + cls + '">' +
             '<div class="wizard-dot-circle">' + inner + '</div>' +
             '<div class="wizard-dot-label">' + step.label + '</div>' +
           '</div>';
  }).join('');
}

/* ── Alerta inline sin cambiar de paso ── */
function mostrarAlertaInline(mensaje, tipo) {
  var colores = {
    error: { bg:'rgba(152,71,62,.08)', border:'rgba(152,71,62,.28)', color:'var(--rust)', icon:'✕' },
    warn:  { bg:'rgba(196,144,10,.08)', border:'rgba(196,144,10,.28)', color:'#7a5500', icon:'⚠' },
  };
  var c = colores[tipo] || colores.error;
  var prev = document.getElementById('wiz-inline-alert');
  if (prev) prev.remove();
  var el = document.createElement('div');
  el.id = 'wiz-inline-alert';
  el.setAttribute('style',
    'display:flex; align-items:flex-start; gap:.5rem; padding:.6rem .9rem;' +
    'border-radius:var(--radius-md); background:' + c.bg + '; border:1px solid ' + c.border + ';' +
    'color:' + c.color + '; font-family:var(--font-ui); font-size:.83rem; font-weight:600;' +
    'margin-top:.85rem;'
  );
  el.innerHTML = '<span style="flex-shrink:0; font-size:.95rem; margin-top:.05rem;">' + c.icon + '</span>' +
                 '<span>' + mensaje + '</span>';
  var stepActivo = document.getElementById('step-' + currentStep);
  if (stepActivo) stepActivo.appendChild(el);
  clearTimeout(el._t);
  el._t = setTimeout(function () {
    el.style.transition = 'opacity .35s';
    el.style.opacity = '0';
    setTimeout(function () { if (el.parentNode) el.remove(); }, 380);
  }, 4500);
}

function limpiarAlerta() {
  var prev = document.getElementById('wiz-inline-alert');
  if (prev) prev.remove();
}

/* ── Validación por paso — devuelve {ok, msg, tipo} ── */
function validarPasoActual() {
  if (currentStep === 1) {
    var sel = document.getElementById('id_usuario');
    if (!sel || !sel.value) {
      sel && sel.classList.add('is-invalid');
      return { ok:false, msg:'Debes seleccionar un usuario responsable antes de continuar.', tipo:'error' };
    }
    sel.classList.remove('is-invalid');
    return { ok:true };
  }
  if (currentStep === 2) {
    var sels    = document.querySelectorAll('.crear-prod-sel');
    var validas = 0;
    var sinStock = [];
    sels.forEach(function (s) {
      if (!s.value) return;
      var opt   = s.options[s.selectedIndex];
      var stock = parseInt(opt.dataset.stock || '0', 10);
      if (stock > 0) { validas++; s.classList.remove('is-invalid'); }
      else           { s.classList.add('is-invalid'); sinStock.push(opt.text.split('—')[0].trim()); }
    });
    if (validas === 0 && sinStock.length === 0)
      return { ok:false, msg:'Selecciona al menos una herramienta disponible.', tipo:'error' };
    if (sinStock.length > 0 && validas === 0)
      return { ok:false, msg:'Las herramientas seleccionadas no tienen stock. Elige otras.', tipo:'warn' };
    if (sinStock.length > 0)
      return { ok:false, msg:'Algunas herramientas no tienen stock (' + sinStock.join(', ') + '). Cámbialas o elimínalas.', tipo:'warn' };
    var cantInvalida = false;
    document.querySelectorAll('#crear-items-container input[name="cantidad[]"]').forEach(function (inp) {
      var v = parseInt(inp.value, 10);
      if (isNaN(v) || v < 1) { inp.classList.add('is-invalid'); cantInvalida = true; }
      else inp.classList.remove('is-invalid');
    });
    if (cantInvalida)
      return { ok:false, msg:'Todas las cantidades deben ser mayores a 0.', tipo:'error' };
    return { ok:true };
  }
  return { ok:true };
}

/* ── Navegar al paso ── */
function goToStep(step) {
  if (step > currentStep) {
    var res = validarPasoActual();
    if (!res.ok) {
      mostrarAlertaInline(res.msg, res.tipo || 'error');
      return;
    }
  }
  limpiarAlerta();
  document.querySelectorAll('.wizard-step').forEach(function (s) { s.style.display = 'none'; });
  document.getElementById('step-' + step).style.display = 'block';
  currentStep = step;
  var titles = [
    { title:'Paso 1: Responsable del préstamo',   subtitle:'Selecciona el usuario responsable' },
    { title:'Paso 2: Herramientas',               subtitle:'Selecciona las herramientas a prestar' },
    { title:'Paso 3: Detalles del préstamo',      subtitle:'Agrega información adicional' },
    { title:'Paso 4: Resumen',                    subtitle:'Revisa todos los datos antes de confirmar' },
  ];
  if (titles[step - 1]) {
    document.getElementById('wizard-title').textContent    = titles[step - 1].title;
    document.getElementById('wizard-subtitle').textContent = titles[step - 1].subtitle;
  }
  renderWizardProgress();
  document.getElementById('btn-prev').style.display   = step > 1        ? 'inline-flex' : 'none';
  document.getElementById('btn-next').style.display   = step < maxSteps ? 'inline-flex' : 'none';
  document.getElementById('btn-submit').style.display = step === maxSteps ? 'inline-flex' : 'none';
  if (step === maxSteps) updateSummary();
  /* Scroll al inicio del body del modal al cambiar paso */
  var body = document.querySelector('#modalCrearPrestamo .modal-body');
  if (body) body.scrollTop = 0;
}

function updateSummary() {
  var usuarioSelect   = document.getElementById('id_usuario');
  var nombreInput     = document.querySelector('[name="nombre_usuario"]');
  var vencimientoInput = document.querySelector('[name="fecha_vencimiento"]');
  var doc      = usuarioSelect ? usuarioSelect.value : '';
  var usuario  = usuariosData.find(function (u) { return u.doc === doc; });
  var nombreTexto = nombreInput && nombreInput.value ? nombreInput.value : (usuario ? usuario.nombre : 'No seleccionado');
  document.getElementById('summary-usuario').textContent = nombreTexto;
  var venc = vencimientoInput && vencimientoInput.value;
  document.getElementById('summary-vencimiento').textContent = venc ? 'Vencimiento: ' + venc : '';
  var container = document.getElementById('summary-items');
  container.innerHTML = '';
  document.querySelectorAll('#crear-items-container .crear-item-row').forEach(function (row) {
    var sel = row.querySelector('.crear-prod-sel');
    var qty = row.querySelector('input[name="cantidad[]"]');
    if (!sel || !sel.value) return;
    var prod = productosData.find(function (p) { return p.pk == sel.value; });
    if (!prod) return;
    var item = document.createElement('div');
    item.style.cssText = 'padding:.65rem .85rem; border-radius:var(--radius-sm);' +
      'background:rgba(9,77,146,.05); border:1px solid rgba(9,77,146,.1);' +
      'display:flex; align-items:center; justify-content:space-between;';
    item.innerHTML =
      '<div>' +
        '<div style="font-weight:600; font-size:.88rem;">' + escapeHtml(prod.nombre) + '</div>' +
        '<div style="font-family:var(--font-mono); font-size:.72rem; color:var(--text-muted);">' + escapeHtml(prod.sku) + '</div>' +
      '</div>' +
      '<div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700; color:var(--navy);">×' + (qty ? qty.value : 1) + '</div>';
    container.appendChild(item);
  });
  if (container.children.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:.8rem;">No hay herramientas seleccionadas</div>';
  }
}

/* ── Generar fila de producto nueva ── */
function crearFilaProducto() {
  var opciones = '<option value="">— Selecciona herramienta —</option>' +
    productosData.map(function (p) {
      return '<option value="' + p.pk + '" data-stock="' + p.stock + '">[' +
        escapeHtml(p.sku) + '] ' + escapeHtml(p.nombre) + ' — Stock: ' + p.stock + '</option>';
    }).join('');
  var div = document.createElement('div');
  div.className = 'crear-item-row row g-2 align-items-start mb-2';
  div.innerHTML =
    '<div class="col">' +
      '<select name="producto[]" class="form-select crear-prod-sel" required>' + opciones + '</select>' +
      '<div class="stock-info-dyn d-none mt-1 px-2 py-1 rounded" style="font-size:.78rem;display:flex;align-items:center;gap:.4rem;"></div>' +
    '</div>' +
    '<div class="col-auto" style="width:90px;"><input type="number" name="cantidad[]" class="form-control text-center" min="1" value="1" required></div>' +
    '<div class="col-auto"><button type="button" class="btn-ghost crear-del-btn" style="width:36px;height:36px;padding:0;display:flex;align-items:center;justify-content:center;">' +
      '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
    '</button></div>';
  div.querySelector('.crear-prod-sel').addEventListener('change', function () {
    var info = div.querySelector('.stock-info-dyn');
    var opt  = this.options[this.selectedIndex];
    info.classList.add('d-none');
    if (!opt.value) return;
    var s = parseInt(opt.dataset.stock, 10);
    info.classList.remove('d-none');
    info.style.cssText = s > 0
      ? 'background:rgba(58,122,66,.07);border:1px solid rgba(58,122,66,.2);color:var(--sage);font-size:.78rem;display:flex;align-items:center;gap:.4rem;'
      : 'background:rgba(152,71,62,.07);border:1px solid rgba(152,71,62,.2);color:var(--rust);font-size:.78rem;display:flex;align-items:center;gap:.4rem;';
    info.textContent = s > 0 ? '✓ Disponible — Stock: ' + s : '⚠ Sin stock disponible';
  });
  return div;
}

document.getElementById('btn-next').addEventListener('click', function () {
  if (currentStep < maxSteps) goToStep(currentStep + 1);
});
document.getElementById('btn-prev').addEventListener('click', function () {
  if (currentStep > 1) goToStep(currentStep - 1);
});
document.getElementById('crear-add-item').addEventListener('click', function () {
  document.getElementById('crear-items-container').appendChild(crearFilaProducto());
  actualizarDelBtns();
});
document.getElementById('crear-items-container').addEventListener('click', function (e) {
  var btn = e.target.closest('.crear-del-btn');
  if (!btn) return;
  var rows = document.querySelectorAll('#crear-items-container .crear-item-row');
  if (rows.length > 1) { btn.closest('.crear-item-row').remove(); actualizarDelBtns(); }
});
function actualizarDelBtns() {
  var rows = document.querySelectorAll('#crear-items-container .crear-item-row');
  rows.forEach(function (r) {
    var b = r.querySelector('.crear-del-btn');
    if (b) b.classList.toggle('disabled', rows.length === 1);
  });
}

document.getElementById('id_usuario').addEventListener('change', function () {
  var doc = this.value;
  var u   = usuariosData.find(function (u) { return u.doc === doc; });
  var inp = document.querySelector('[name="nombre_usuario"]');
  if (u && inp) inp.value = u.nombre;
});

document.getElementById('modalCrearPrestamo').addEventListener('show.bs.modal', function () {
  currentStep = 1;
  goToStep(1);
  document.getElementById('wizardForm').reset();
  document.getElementById('id_usuario').classList.remove('is-invalid');
  var container = document.getElementById('crear-items-container');
  while (container.children.length > 1) container.removeChild(container.lastChild);
  actualizarDelBtns();
});

/* ═══════════════════════════════════════════
   KPI — animación con IntersectionObserver
═══════════════════════════════════════════ */
(function () {
  function easeOutExpo(t) { return t === 1 ? 1 : 1 - Math.pow(2, -10 * t); }
  function animarContador(el, target, dur) {
    var inicio = performance.now();
    function paso(ahora) {
      var p    = Math.min((ahora - inicio) / dur, 1);
      var ease = easeOutExpo(p);
      el.textContent = Math.round(ease * target);
      if (p < 1) requestAnimationFrame(paso);
      else el.textContent = target;
    }
    requestAnimationFrame(paso);
  }
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var card  = entry.target;
      var delay = parseInt(card.getAttribute('data-kpi-delay') || '0', 10);
      setTimeout(function () {
        card.classList.add('kpi-visible');
        card.querySelectorAll('.kpi-number').forEach(function (num) {
          animarContador(num, parseInt(num.getAttribute('data-target')) || 0, 1100);
        });
      }, delay + 80);
      observer.unobserve(card);
    });
  }, { threshold: .15 });
  document.querySelectorAll('.kpi-card').forEach(function (c) { observer.observe(c); });
})();

/* ── Util ── */
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}