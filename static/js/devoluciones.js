/* ═══════════════════════════════════════════
   devoluciones.js
   Lógica de la vista de devoluciones
═══════════════════════════════════════════ */

// ── MINE-106: poblar modal editar con datos de la fila (delegación global) ──
$(document).on('click', '.btn-editar', function () {
  var dataset = this.dataset;
  if (!dataset) return;
  var elId = document.getElementById('edit-devolucion-id');
  if (elId) elId.value = dataset.id || '';
  var elModalId = document.getElementById('edit-modal-id');
  if (elModalId) elModalId.textContent = '#' + (dataset.id || '');
  var elOrden = document.getElementById('edit-numero-orden');
  if (elOrden) elOrden.value = dataset.orden || '';
  var elProd = document.getElementById('edit-producto');
  if (elProd) elProd.value = dataset.producto || '';
  var elCant = document.getElementById('edit-cantidad');
  if (elCant) elCant.value = dataset.cantidad || '';
  var elMot = document.getElementById('edit-motivo');
  if (elMot) elMot.value = dataset.motivo || '';
  var elEst = document.getElementById('edit-estado');
  if (elEst) elEst.value = dataset.estado || '';
});

// ══════════════════════════════════════════════════════════════
//  BOTONES ACEPTAR / RECHAZAR — lógica de los modales
// ══════════════════════════════════════════════════════════════

function abrirAceptar(devId, prestamoId, usuario) {
  document.getElementById('acp-id').textContent       = '#' + devId;
  document.getElementById('acp-dev-id').value         = devId;
  document.getElementById('acp-prestamo').textContent = '#' + prestamoId;
  document.getElementById('acp-usuario').textContent  = usuario;
  // Limpiar textarea
  var ta = document.querySelector('#form-aceptar-devolucion textarea');
  if (ta) ta.value = '';
  new bootstrap.Modal(document.getElementById('modalAceptarDevolucion')).show();
}

function confirmarAceptar() {
  document.getElementById('form-aceptar-devolucion').submit();
}

function abrirRechazar(devId, prestamoId, usuario) {
  document.getElementById('rch-id').textContent       = '#' + devId;
  document.getElementById('rch-dev-id').value         = devId;
  document.getElementById('rch-prestamo').textContent = '#' + prestamoId;
  document.getElementById('rch-usuario').textContent  = usuario;
  // Limpiar estado
  var ta  = document.getElementById('rch-motivo-textarea');
  var err = document.getElementById('rch-motivo-err');
  if (ta)  { ta.value = ''; ta.style.borderColor = ''; }
  if (err) err.style.display = 'none';
  new bootstrap.Modal(document.getElementById('modalRechazarDevolucion')).show();
}

// Validación inline: sin cerrar el modal ni reiniciar
function confirmarRechazar() {
  var ta  = document.getElementById('rch-motivo-textarea');
  var err = document.getElementById('rch-motivo-err');
  var val = (ta.value || '').trim();

  if (val.length < 10) {
    // Mostrar alerta inline, resaltar campo, NO cerrar ni reiniciar
    err.style.display = 'flex';
    ta.style.borderColor = 'var(--rust)';
    ta.style.boxShadow   = '0 0 0 3px rgba(152,71,62,.12)';
    ta.focus();
    // Reanimar la alerta si ya estaba visible
    err.style.animation = 'none';
    void err.offsetWidth; // forzar reflow
    err.style.animation = 'shakeX .35s ease';
    return; // ← NO envía el formulario
  }

  document.getElementById('form-rechazar-devolucion').submit();
}

function rchLimpiarError() {
  var ta  = document.getElementById('rch-motivo-textarea');
  var err = document.getElementById('rch-motivo-err');
  if (!ta || !err) return;
  if ((ta.value || '').trim().length >= 10) {
    err.style.display    = 'none';
    ta.style.borderColor = '';
    ta.style.boxShadow   = '';
  }
}


// ══════════════════════════════════════════════════════════════
//  WIZARD DEVOLUCIONES
// ══════════════════════════════════════════════════════════════
(function () {

  var _paso       = 0;
  var _prestamo   = null;
  var _escaneados = {};
  var DEV_PRESTAMOS = [];
  try {
    var devEl = document.getElementById('dev-prestamos-data');
    if (devEl) DEV_PRESTAMOS = JSON.parse(devEl.textContent);
  } catch (e) {
    console.error("Error al parsear dev-prestamos-data:", e);
  }

  var DEV_STEPS = [
    { label: 'Préstamo'     },
    { label: 'Herramientas' },
    { label: 'Confirmar'    },
  ];

  var svgCheck = function() { return '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8"><polyline points="20 6 9 17 4 12"/></svg>'; };
  var svgArR   = function() { return '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>'; };
  var svgArL   = function() { return '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>'; };

  function renderProgress() {
    var bar = document.getElementById('dev-wiz-progress-bar');
    if (!bar) return;
    bar.innerHTML = DEV_STEPS.map(function(s, i) {
      var cls = 'dev-wiz-step-dot';
      if (i < _paso)  cls += ' dev-wiz-done';
      if (i === _paso) cls += ' dev-wiz-active';
      var inner = i < _paso ? svgCheck() : (i + 1);
      return '<div class="' + cls + '">' +
               '<div class="dev-wiz-dot-circle">' + inner + '</div>' +
               '<div class="dev-wiz-dot-label">' + s.label + '</div>' +
             '</div>';
    }).join('');
  }

  function canAdvance() {
    if (_paso === 0) return !!_prestamo;
    if (_paso === 1) return Object.values(_escaneados).some(function(e) { return e.seleccionado; });
    return true;
  }

  function updateBtn() {
    var btn = document.getElementById('dev-btn-next');
    if (btn) btn.disabled = !canAdvance();
  }

  // ── Mostrar alerta inline sin avanzar ──
  function mostrarAlertaInline(panelId, mensaje) {
    var panel = document.getElementById(panelId);
    if (!panel) return;
    var existing = panel.querySelector('.dev-wiz-alert-inline');
    if (existing) existing.remove();
    var div = document.createElement('div');
    div.className = 'dev-wiz-alert-inline';
    div.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="flex-shrink:0;">' +
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>' +
        '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>' +
      '</svg>' +
      '<span>' + mensaje + '</span>';
    // Insertar antes del nav-row
    var navRow = panel.querySelector('.dev-wiz-nav-row');
    if (navRow) panel.insertBefore(div, navRow);
    else panel.appendChild(div);
    // Auto-quitar al escribir o interactuar
    div.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function render() {
    renderProgress();
    var panel = document.getElementById('dev-wiz-panel');
    if (!panel) return;
    if (_paso === 0)      panel.innerHTML = renderStep0();
    else if (_paso === 1) panel.innerHTML = renderStep1();
    else                  panel.innerHTML = renderStep2();
    updateBtn();

  }

  // ══ PASO 0 ══
  function renderStep0() {
    var loansHtml = DEV_PRESTAMOS.length === 0
      ? '<div style="text-align:center;padding:2.5rem 1rem;color:var(--text-muted);font-family:var(--font-ui);font-size:.88rem;">No hay préstamos activos pendientes de devolución.</div>'
      : DEV_PRESTAMOS.map(function(p) {
          var selectedCls = (_prestamo && _prestamo.id === p.id) ? 'dev-loan-card dev-activa' : 'dev-loan-card';
          var statusMap = { activo: ['dev-badge-activo','Activo'], parcial: ['dev-badge-parcial','Parcial'], vencido: ['dev-badge-vencido','Vencido'] };
          var sm = statusMap[p.estado] || ['',''];
          var chipsHtml = p.items.filter(function(it){ return !it.devuelto; })
            .map(function(it){ return '<span style="font-family:var(--font-mono);font-size:.65rem;background:rgba(9,77,146,.07);color:var(--navy);border:1px solid rgba(9,77,146,.12);padding:.1rem .38rem;border-radius:var(--radius-sm);margin:1px 2px 0 0;">' + it.producto.nombre + ' ×' + it.cantidad + '</span>'; }).join('');
          var textoData = p.id + ' ' + p.usuario.toLowerCase() + ' ' + p.items.map(function(it){ return it.producto.nombre.toLowerCase() + ' ' + it.producto.codigo_sku.toLowerCase(); }).join(' ');
          var esActiva = (_prestamo && _prestamo.id === p.id);

          return '<div class="' + selectedCls + '" data-id="' + p.id + '" data-texto="' + textoData.replace(/"/g,'&quot;') + '" onclick="devSeleccionarPrestamo(this,' + p.id + ')">' +
            '<span style="font-family:var(--font-mono);font-size:.7rem;font-weight:700;color:var(--navy);background:rgba(9,77,146,.08);border:1px solid rgba(9,77,146,.15);padding:.18rem .5rem;border-radius:var(--radius-sm);white-space:nowrap;flex-shrink:0;">#' + p.id + '</span>' +
            '<div style="flex:1;min-width:0;">' +
              '<div style="font-family:var(--font-ui);font-size:.88rem;font-weight:600;color:var(--text-main);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:.25rem;">' + p.usuario + (p.nombre_usuario ? ' · <span style="font-weight:400;opacity:.7;">' + p.nombre_usuario + '</span>' : '') + '</div>' +
              '<div style="display:flex;flex-wrap:wrap;">' + chipsHtml + '</div>' +
            '</div>' +
            '<div style="flex-shrink:0;display:flex;flex-direction:column;align-items:flex-end;gap:.3rem;">' +
              '<span class="' + sm[0] + '" style="font-size:.65rem;font-weight:700;padding:.12rem .45rem;border-radius:20px;font-family:var(--font-ui);">' + sm[1] + '</span>' +
              '<span style="font-family:var(--font-mono);font-size:.65rem;color:var(--text-muted);">' + p.fecha_prestamo + '</span>' +
            '</div>' +
            '<div style="width:16px;height:16px;border-radius:50%;flex-shrink:0;border:1.5px solid ' + (esActiva ? 'var(--rust)' : 'rgba(0,0,0,.15)') + ';background:' + (esActiva ? 'var(--rust)' : 'transparent') + ';position:relative;">' +
              (esActiva ? '<span style="position:absolute;inset:3px;border-radius:50%;background:#fff;display:block;"></span>' : '') +
            '</div>' +
          '</div>';
        }).join('');

    return '<div class="dev-wiz-sec-label"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>Selecciona el préstamo a devolver</div>' +
      '<div style="position:relative;margin-bottom:.75rem;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--text-muted);pointer-events:none;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
      '<input type="text" class="dev-wiz-search-input" id="dev-search-prestamos" placeholder="Buscar por usuario, N° o herramienta…" oninput="devFiltrarPrestamos()" autocomplete="off"></div>' +
      '<div id="dev-loan-list" style="max-height:280px;overflow-y:auto;">' + loansHtml + '</div>' +
      '<div id="dev-sin-resultados" class="d-none" style="text-align:center;padding:1.5rem;color:var(--text-muted);font-family:var(--font-ui);font-size:.85rem;">Sin coincidencias.</div>' +
      '<div class="dev-wiz-nav-row"><div></div>' +
        '<button class="dev-wiz-btn-next" id="dev-btn-next" onclick="devWizSiguiente()" ' + (canAdvance() ? '' : 'disabled') + '>Continuar ' + svgArR() + '</button>' +
      '</div>';
  }

  // ══ PASO 1 ══
  function renderStep1() {
    if (!_prestamo) return '';
    var pendientes = _prestamo.items.filter(function(it){ return !it.devuelto; });
    var devueltos  = _prestamo.items.filter(function(it){ return  it.devuelto; });
    var badgeTxt   = pendientes.length + ' pendiente' + (pendientes.length !== 1 ? 's' : '');

    var itemsHtml = pendientes.map(function(it) {
      var e = _escaneados[it.id] || {};
      var sel  = e.seleccionado !== undefined ? e.seleccionado : true;
      var esc  = e.escaneado    || false;
      var cant = e.cantDevolver !== undefined ? e.cantDevolver : it.cantidad;
      var serialTxt = '';
      var chkMark = sel ? '<svg width="8" height="7" viewBox="0 0 11 9" fill="none"><path d="M1 4L4.5 7.5L10 1.5" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>' : '';
      var cantCtrl = sel
        ? '<div style="display:flex;align-items:center;gap:3px;" onclick="event.stopPropagation()"><button type="button" onclick="devCambiarCant(' + it.id + ',-1)" style="width:20px;height:20px;border-radius:4px;border:1px solid rgba(152,71,62,.3);background:#fff;color:var(--rust);font-size:.85rem;cursor:pointer;display:flex;align-items:center;justify-content:center;">−</button><span id="dev-cant-' + it.id + '" style="font-family:var(--font-mono);font-weight:700;font-size:.82rem;min-width:18px;text-align:center;color:var(--navy);">' + cant + '</span><button type="button" onclick="devCambiarCant(' + it.id + ',+1)" style="width:20px;height:20px;border-radius:4px;border:1px solid rgba(152,71,62,.3);background:#fff;color:var(--rust);font-size:.85rem;cursor:pointer;display:flex;align-items:center;justify-content:center;">+</button><span style="font-size:.62rem;color:var(--text-muted);">/' + it.cantidad + '</span></div>'
        : '<span style="font-family:var(--font-mono);font-size:.72rem;color:var(--text-muted);">' + it.cantidad + ' ud.</span>';

      return '<div class="' + rowCls + '" onclick="devToggleItem(' + it.id + ')">' +
        '<div class="dev-checkbox">' + chkMark + '</div>' +
        '<div style="flex:1;min-width:0;"><div style="font-weight:600;font-size:.86rem;color:var(--text-main);font-family:var(--font-ui);display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;">' + it.producto.nombre + '</div>' +
        '<div style="font-size:.7rem;color:var(--text-muted);margin-top:2px;font-family:var(--font-mono);">Stock: ' + it.producto.stock + '</div></div>' +
        '<div style="flex-shrink:0;" onclick="event.stopPropagation()">' + cantCtrl + '</div></div>';
    }).join('');

    var devueltosHtml = devueltos.length
      ? '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.07em;color:var(--text-muted);font-weight:600;margin:8px 0 5px;font-family:var(--font-mono);">Ya devueltos</div>' +
        devueltos.map(function(it){
          return '<div class="dev-item-row" style="opacity:.45;cursor:default;">' +
            '<div class="dev-checkbox" style="background:#16a34a;border-color:#16a34a;"><svg width="8" height="7" viewBox="0 0 11 9" fill="none"><path d="M1 4L4.5 7.5L10 1.5" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' +
            '<div style="flex:1;"><div style="font-weight:600;font-size:.84rem;font-family:var(--font-ui);">' + it.producto.nombre + '</div><div style="font-size:.68rem;color:var(--text-muted);font-family:var(--font-mono);">✓ Ya devuelto</div></div></div>';
        }).join('')
      : '';

    return '<div style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;flex-wrap:wrap;padding:.6rem .9rem;background:rgba(9,77,146,.04);border:1px solid rgba(9,77,146,.14);border-radius:var(--radius-md);margin-bottom:1rem;">' +
        '<div><span style="font-family:var(--font-mono);font-weight:700;color:var(--navy);font-size:.85rem;">Préstamo #' + _prestamo.id + '</span>' +
        '<span style="color:var(--text-muted);margin:0 .3rem;">·</span>' +
        '<span style="font-family:var(--font-ui);font-weight:600;font-size:.85rem;color:var(--text-main);">' + _prestamo.usuario + '</span></div>' +
        '<button type="button" onclick="devWizAtras()" style="background:none;border:none;color:var(--navy);font-family:var(--font-ui);font-size:.75rem;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px;padding:0;opacity:.7;">Cambiar</button>' +
      '</div>' +

      '<div class="dev-wiz-sec-label" style="margin-top:.85rem;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>' +
        '<span>Herramientas del préstamo</span>' +
        '<span style="font-size:.6rem;background:rgba(9,77,146,.1);color:var(--navy);border:1px solid rgba(9,77,146,.18);padding:.08rem .42rem;border-radius:10px;font-family:var(--font-mono);">' + badgeTxt + '</span>' +
        '<button type="button" onclick="devToggleTodas()" style="margin-left:auto;background:none;border:none;color:var(--navy);font-family:var(--font-ui);font-size:.72rem;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px;opacity:.75;">Marcar todas</button>' +
      '</div>' +
      '<div style="max-height:195px;overflow-y:auto;margin-bottom:.4rem;">' + itemsHtml + devueltosHtml + '</div>' +
      '<div id="dev-resumen-strip"></div>' +
      '<div class="dev-wiz-nav-row">' +
        '<button class="dev-wiz-btn-back" onclick="devWizAtras()">' + svgArL() + ' Volver</button>' +
        '<button class="dev-wiz-btn-next" id="dev-btn-next" onclick="devWizSiguiente()" ' + (canAdvance() ? '' : 'disabled') + '>Continuar ' + svgArR() + '</button>' +
      '</div>';
  }

  // ══ PASO 2 ══
  function renderStep2() {
    if (!_prestamo) return '';
    var pend    = _prestamo.items.filter(function(it){ return !it.devuelto; });
    var sel     = pend.filter(function(it){ return _escaneados[it.id] && _escaneados[it.id].seleccionado; });
    var parcial = esDevolucionParcial();

    var chipsHtml = sel.map(function(it) {
      var cant = (_escaneados[it.id] && _escaneados[it.id].cantDevolver !== undefined) ? _escaneados[it.id].cantDevolver : it.cantidad;
      var esc  = _escaneados[it.id] && _escaneados[it.id].escaneado;
      return '<span style="font-family:var(--font-mono);font-size:.72rem;margin:2px;background:' + (esc ? 'rgba(22,163,74,.1)' : 'rgba(9,77,146,.07)') + ';color:' + (esc ? '#15803d' : 'var(--navy)') + ';padding:.2rem .55rem;border-radius:6px;border:1px solid ' + (esc ? 'rgba(22,163,74,.2)' : 'rgba(9,77,146,.12)') + ';">' + (esc ? '✓ ' : '') + it.producto.nombre + ' ×' + cant + '</span>';
    }).join('');

    var tipoBadge = parcial
      ? '<span style="font-size:.72rem;background:rgba(234,179,8,.1);color:#92400e;padding:.2rem .6rem;border-radius:6px;font-weight:700;border:1px solid rgba(234,179,8,.22);">☑️ Devolución parcial</span>'
      : '<span style="font-size:.72rem;background:rgba(22,163,74,.09);color:#15803d;padding:.2rem .6rem;border-radius:6px;font-weight:700;border:1px solid rgba(22,163,74,.2);">✅ Devolución total</span>';

    return '<div class="dev-wiz-sec-label"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>Revisión final</div>' +
      '<div style="background:rgba(9,77,146,.03);border:1px solid rgba(9,77,146,.12);border-radius:var(--radius-md);padding:.85rem 1rem;margin-bottom:.75rem;">' +
        '<div style="font-size:.62rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-muted);font-weight:600;font-family:var(--font-mono);margin-bottom:.5rem;">Herramientas a devolver</div>' +
        '<div style="display:flex;flex-wrap:wrap;margin-bottom:.5rem;">' + chipsHtml + '</div>' +
        '<div>' + tipoBadge + '</div>' +
      '</div>' +
      '<div style="background:var(--bg-body);border-radius:var(--radius-md);border:1px solid var(--border-color);overflow:hidden;margin-bottom:.75rem;">' +
        '<div class="dev-summary-row" style="padding:7px 12px;"><span style="font-size:.82rem;color:var(--text-muted);">Préstamo</span><span style="font-size:.88rem;font-weight:600;color:var(--text-main);">#' + _prestamo.id + ' — ' + _prestamo.usuario + '</span></div>' +
        '<div class="dev-summary-row" style="padding:7px 12px;"><span style="font-size:.82rem;color:var(--text-muted);">Ítems devueltos</span><span style="font-size:.88rem;font-weight:600;color:var(--text-main);">' + sel.length + ' herramienta' + (sel.length !== 1 ? 's' : '') + '</span></div>' +
        '<div class="dev-summary-row" style="padding:7px 12px;"><span style="font-size:.82rem;color:var(--text-muted);">Tipo</span>' + tipoBadge + '</div>' +
      '</div>' +
      // Motivo — con validación inline (NO reinicia wizard)
      '<div class="dev-wiz-sec-label"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="21" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="21" y1="18" x2="3" y2="18"/></svg>Motivo' +
        (parcial ? '<span style="color:var(--rust);font-size:.7rem;font-weight:700;margin-left:.2rem;">* obligatorio</span>' : '<span style="color:var(--text-muted);font-size:.7rem;font-weight:400;margin-left:.2rem;">(opcional)</span>') +
      '</div>' +
      '<textarea id="dev-motivo-input" class="dev-wiz-textarea" rows="3" placeholder="' +
        (parcial ? 'Explica por qué no se devuelven todas las herramientas… (obligatorio)' : 'Observaciones adicionales (opcional)…') +
        '" oninput="devLimpiarAlertaMotivo()"></textarea>' +
      (parcial ? '<div style="display:flex;align-items:center;gap:.4rem;margin-top:.4rem;padding:.35rem .65rem;background:rgba(196,144,10,.08);border:1px solid rgba(196,144,10,.22);border-radius:var(--radius-sm);font-family:var(--font-ui);font-size:.76rem;color:#92400e;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/></svg>El motivo es obligatorio en devoluciones parciales.</div>' : '') +
      '<div class="dev-wiz-nav-row">' +
        '<button class="dev-wiz-btn-back" onclick="devWizAtras()">' + svgArL() + ' Editar</button>' +
        '<button class="dev-wiz-btn-save" id="dev-btn-next" onclick="devEnviar()"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>Guardar devolución</button>' +
      '</div>';
  }

  // ── Limpiar alerta motivo mientras escribe ──
  window.devLimpiarAlertaMotivo = function() {
    var panel = document.getElementById('dev-wiz-panel');
    if (!panel) return;
    var alerta = panel.querySelector('.dev-wiz-alert-inline');
    var ta = document.getElementById('dev-motivo-input');
    if (alerta && ta && ta.value.trim().length >= 10) {
      alerta.remove();
      ta.style.borderColor = '';
    }
  };

  // ── Navegación ──
  window.devWizSiguiente = function() {
    if (!canAdvance()) {
      // Mostrar alerta inline sin avanzar
      if (_paso === 0) {
        mostrarAlertaInline('dev-wiz-panel', 'Debes seleccionar un préstamo para continuar.');
      } else if (_paso === 1) {
        mostrarAlertaInline('dev-wiz-panel', 'Selecciona al menos una herramienta para devolver.');
      }
      return;
    }
    if (_paso < 2) { _paso++; render(); }
  };
  window.devWizAtras = function() {
    if (_paso > 0) { _paso--; render(); }
  };
  window.devUpdateBtn = function() { updateBtn(); };

  // ── Paso 0: filtro ──
  window.devFiltrarPrestamos = function() {
    var q = (document.getElementById('dev-search-prestamos') && document.getElementById('dev-search-prestamos').value || '').toLowerCase().trim();
    var vis = 0;
    document.querySelectorAll('#dev-loan-list .dev-loan-card').forEach(function(f) {
      var ok = !q || (f.dataset.texto || f.textContent).toLowerCase().includes(q);
      f.style.display = ok ? '' : 'none';
      if (ok) vis++;
    });
    var noRes = document.getElementById('dev-sin-resultados');
    if (noRes) noRes.classList.toggle('d-none', vis > 0 || !q);
  };

  window.devSeleccionarPrestamo = function(fila, id) {
    var found = DEV_PRESTAMOS.find(function(p){ return p.id === id; });
    if (!found) return;
    _prestamo   = found;
    _escaneados = {};
    found.items.forEach(function(it) {
      if (!it.devuelto) {
        _escaneados[it.id] = { item: it, cantDevolver: it.cantidad, seleccionado: true, escaneado: false };
      }
    });
    renderProgress();
    var panel = document.getElementById('dev-wiz-panel');
    if (panel) panel.innerHTML = renderStep0();
    updateBtn();
  };

  // ── Paso 1: Escáner removido ──
  window.devToggleItem = function(id) {
    if (!_escaneados[id]) return;
    _escaneados[id].seleccionado = !_escaneados[id].seleccionado;
    if (!_escaneados[id].seleccionado) _escaneados[id].escaneado = false;
    render();
  };

  window.devCambiarCant = function(id, delta) {
    if (!_escaneados[id]) return;
    var max = _escaneados[id].item.cantidad;
    _escaneados[id].cantDevolver = Math.min(max, Math.max(1, (_escaneados[id].cantDevolver || max) + delta));
    var el = document.getElementById('dev-cant-' + id);
    if (el) el.textContent = _escaneados[id].cantDevolver;
    devActualizarResumen();
  };

  window.devToggleTodas = function() {
    if (!_prestamo) return;
    var pend = _prestamo.items.filter(function(it){ return !it.devuelto; });
    var algunaSel = pend.some(function(it){ return _escaneados[it.id] && _escaneados[it.id].seleccionado; });
    pend.forEach(function(it) {
      if (_escaneados[it.id]) {
        _escaneados[it.id].seleccionado = !algunaSel;
        if (!algunaSel) _escaneados[it.id].cantDevolver = it.cantidad;
      }
    });
    render();
  };

  function devActualizarResumen() {
    var strip = document.getElementById('dev-resumen-strip');
    if (!strip || !_prestamo) return;
    var pend  = _prestamo.items.filter(function(it){ return !it.devuelto; });
    var sel   = pend.filter(function(it){ return _escaneados[it.id] && _escaneados[it.id].seleccionado; });
    var tot   = pend.length;
    var todo  = sel.length === tot && sel.every(function(it){ return (_escaneados[it.id] && _escaneados[it.id].cantDevolver !== undefined ? _escaneados[it.id].cantDevolver : it.cantidad) === it.cantidad; });
    if (!sel.length) {
      strip.innerHTML = '<div class="dev-alert-strip" style="background:rgba(185,28,28,.07);border:1px solid rgba(185,28,28,.2);color:#b91c1c;">⚠️ &nbsp;Selecciona al menos una herramienta.</div>';
    } else if (todo) {
      strip.innerHTML = '<div class="dev-alert-strip" style="background:rgba(22,163,74,.07);border:1px solid rgba(22,163,74,.2);color:#15803d;">✅ &nbsp;Devolución <strong>total</strong> — ' + tot + ' herramienta' + (tot !== 1 ? 's' : '') + '.</div>';
    } else {
      var det = sel.map(function(it){ return it.producto.nombre + ' ×' + (_escaneados[it.id] && _escaneados[it.id].cantDevolver !== undefined ? _escaneados[it.id].cantDevolver : it.cantidad); }).join(', ');
      strip.innerHTML = '<div class="dev-alert-strip" style="background:rgba(234,179,8,.07);border:1px solid rgba(234,179,8,.2);color:#92400e;">☑️ &nbsp;Devolución <strong>parcial</strong>: ' + det + '.</div>';
    }
  }

  function esDevolucionParcial() {
    if (!_prestamo) return false;
    var pend = _prestamo.items.filter(function(it){ return !it.devuelto; });
    var sel  = pend.filter(function(it){ return _escaneados[it.id] && _escaneados[it.id].seleccionado; });
    return !(sel.length === pend.length && sel.every(function(it){ return (_escaneados[it.id] && _escaneados[it.id].cantDevolver !== undefined ? _escaneados[it.id].cantDevolver : it.cantidad) === it.cantidad; }));
  }

  // ── Enviar — con validación inline sin reiniciar ──
  window.devEnviar = function() {
    if (!_prestamo) return;
    var parcial = esDevolucionParcial();
    var motivo  = (document.getElementById('dev-motivo-input') && document.getElementById('dev-motivo-input').value || '').trim();

    if (parcial && motivo.length < 10) {
      // Alerta inline: NO reinicia wizard, NO va al paso 0
      var ta = document.getElementById('dev-motivo-input');
      if (ta) {
        ta.style.borderColor = 'var(--rust)';
        ta.style.boxShadow   = '0 0 0 3px rgba(152,71,62,.12)';
        ta.focus();
      }
      mostrarAlertaInline('dev-wiz-panel', 'El motivo es obligatorio en devoluciones parciales (mínimo 10 caracteres).');
      return; // ← NO envía ni avanza
    }

    var pend = _prestamo.items.filter(function(it){ return !it.devuelto; });
    var sel  = pend.filter(function(it){ return _escaneados[it.id] && _escaneados[it.id].seleccionado; });

    var form = document.getElementById('form-devolucion-final');
    form.querySelectorAll('input[data-dyn]').forEach(function(el){ el.remove(); });

    document.getElementById('fin-prestamo-id').value      = _prestamo.id;
    document.getElementById('fin-devolucion-total').value = parcial ? 'false' : 'true';
    document.getElementById('fin-motivo-requerido').value = parcial ? 'true'  : 'false';
    document.getElementById('fin-motivo').value           = motivo;

    sel.forEach(function(it) {
      var i1 = document.createElement('input');
      i1.type = 'hidden'; i1.name = 'items'; i1.value = it.id;
      i1.setAttribute('data-dyn','1'); form.appendChild(i1);
      var i2 = document.createElement('input');
      i2.type = 'hidden'; i2.name = 'cantidad_' + it.id;
      i2.value = (_escaneados[it.id] && _escaneados[it.id].cantDevolver !== undefined) ? _escaneados[it.id].cantDevolver : it.cantidad;
      i2.setAttribute('data-dyn','1'); form.appendChild(i2);
    });
    form.submit();
  };

  // ── Init modal ──
  var modal = document.getElementById('modalCrear');
  if (modal) {
    modal.addEventListener('shown.bs.modal', function() { render(); });
    modal.addEventListener('hidden.bs.modal', function() {
      _paso = 0; _prestamo = null; _escaneados = {};
      var panel = document.getElementById('dev-wiz-panel');
      var bar   = document.getElementById('dev-wiz-progress-bar');
      if (panel) panel.innerHTML = '';
      if (bar)   bar.innerHTML   = '';
    });
  }

  // ── Auto-abrir desde prestamo.html ──
  var urlParams = new URLSearchParams(window.location.search);
  var prestamoFromUrl = urlParams.get('prestamo');
  if (prestamoFromUrl) {
    var prestamoId = parseInt(prestamoFromUrl, 10);
    var found = DEV_PRESTAMOS.find(function(p){ return p.id === prestamoId; });
    if (found) {
      _prestamo = found;
      _escaneados = {};
      found.items.forEach(function(it) {
        if (!it.devuelto) {
          _escaneados[it.id] = { item: it, cantDevolver: it.cantidad, seleccionado: true, escaneado: false };
        }
      });
      _paso = 0;
      renderProgress();
      var panel = document.getElementById('dev-wiz-panel');
      if (panel) panel.innerHTML = renderStep0();
      updateBtn();
      setTimeout(function() {
        bootstrap.Modal.getOrCreateInstance(modal).show();
      }, 100);
    }
  }

})();
