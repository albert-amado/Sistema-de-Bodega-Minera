/**
 * ==========================================================================
 * MÓDULO DE GESTIÓN DE USUARIOS - SENA CENTRO MINERO
 * Lógica de cliente desacoplada (Vistas, Modales, Búsqueda asíncrona)
 * ==========================================================================
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Restaurar preferencia de vista persistida (Tarjetas / Lista)
  var vistaGuardada = localStorage.getItem('gu_vista') || 'fichas';
  setVista(vistaGuardada);

  // 2. Búsqueda con debounce para envío automático fluido
  var qInput = document.getElementById('qInput');
  if (qInput) {
    var searchTimer;
    qInput.addEventListener('input', function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        var form = document.getElementById('filtroForm');
        if (form) form.submit();
      }, 500);
    });
  }

  // 3. Toggle de visualización de contraseña en modal de edición
  var togglePwBtn = document.getElementById('toggleEditPw');
  if (togglePwBtn) {
    togglePwBtn.addEventListener('click', function () {
      var inp = document.getElementById('edit_password');
      if (!inp) return;
      inp.type = inp.type === 'password' ? 'text' : 'password';
      var icon = this.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-eye');
        icon.classList.toggle('bi-eye-slash');
      }
    });
  }

  // 4. Limitar input de teléfono a sólo caracteres numéricos
  var telInput = document.getElementById('edit_telefono');
  if (telInput) {
    telInput.addEventListener('input', function () {
      this.value = this.value.replace(/\D/g, '');
    });
  }
});

/**
 * Alterna entre vista de fichas (grid de tarjetas) y vista de lista (tabla)
 * @param {'fichas' | 'lista'} v
 */
function setVista(v) {
  var esFichas = v === 'fichas';
  var vistaFichas = document.getElementById('vistaFichas');
  var vistaLista = document.getElementById('vistaLista');
  var btnF = document.getElementById('btnFichas');
  var btnL = document.getElementById('btnLista');

  if (vistaFichas) vistaFichas.classList.toggle('d-none', !esFichas);
  if (vistaLista) vistaLista.classList.toggle('d-none', esFichas);

  if (btnF && btnL) {
    if (esFichas) {
      btnF.classList.add('active');
      btnL.classList.remove('active');
    } else {
      btnL.classList.add('active');
      btnF.classList.remove('active');
    }
  }
  localStorage.setItem('gu_vista', v);
}

var _modalVerUsuario = null;

/**
 * Consulta el endpoint JSON protegido y abre el modal con la información detallada
 * @param {string} doc
 */
function verUsuario(doc) {
  var skeleton = document.getElementById('modalSkeleton');
  var datos = document.getElementById('modalDatos');
  var modalLabel = document.getElementById('modalUsuarioLabel');
  var modalRol = document.getElementById('modalRol');
  var modalAvatar = document.getElementById('modalAvatar');

  if (skeleton) skeleton.classList.remove('d-none');
  if (datos) datos.classList.add('d-none');
  if (modalLabel) modalLabel.textContent = '';
  if (modalRol) modalRol.textContent = '';
  if (modalAvatar) modalAvatar.textContent = '';

  var modalEl = document.getElementById('modalUsuario');
  if (modalEl) {
    if (!_modalVerUsuario) {
      _modalVerUsuario = new bootstrap.Modal(modalEl);
    }
    _modalVerUsuario.show();
  }

  fetch('/usuarios/' + encodeURIComponent(doc) + '/json/')
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (d) {
      var iniciales = (d.nombre_completo || 'US').slice(0, 2).toUpperCase();
      if (modalAvatar) {
        modalAvatar.textContent = iniciales;
        modalAvatar.className = d.rol === 'Administrador' ? 'gu-avatar gu-avatar-admin' : 'gu-avatar gu-avatar-user';
      }

      if (modalLabel) modalLabel.textContent = d.nombre_completo;
      if (modalRol) {
        modalRol.textContent = d.rol;
        modalRol.className = 'gu-badge-role ' + (d.rol === 'Administrador' ? 'gu-badge-admin' : 'gu-badge-user');
      }

      var setTxt = function (id, val) {
        var el = document.getElementById(id);
        if (el) el.textContent = val || '—';
      };

      setTxt('mTipoDoc', d.tipo_documento_display);
      setTxt('mNumDoc', d.numero_documento);
      setTxt('mCorreo', d.correo);
      setTxt('mTelefono', d.telefono);
      setTxt('mNumFicha', d.numero_ficha);
      setTxt('mPrograma', d.nombre_programa);
      setTxt('mIdDoc', 'ID · ' + d.numero_documento);

      setTxt('mPrestamosTotal', d.prestamos_totales || 0);
      setTxt('mPrestamosActivos', d.prestamos_activos || 0);
      setTxt('mPrestamosPendientes', d.prestamos_parciales || 0);

      var btnEditarModal = document.getElementById('btnEditarDesdeModal');
      if (btnEditarModal) {
        btnEditarModal.onclick = function () {
          if (_modalVerUsuario) _modalVerUsuario.hide();
          setTimeout(function () {
            abrirEditar(
              d.numero_documento,
              d.nombre_completo,
              d.correo,
              d.telefono || '',
              d.rol,
              d.tipo_documento,
              d.numero_ficha || '',
              d.nombre_programa || ''
            );
          }, 350);
        };
      }

      if (skeleton) skeleton.classList.add('d-none');
      if (datos) datos.classList.remove('d-none');
    })
    .catch(function () {
      if (skeleton) {
        skeleton.innerHTML = '<div class="alert alert-danger py-2 small mb-0">Error al cargar los datos del usuario.</div>';
      }
    });
}

/**
 * Precarga y abre el modal de edición de usuario
 */
function abrirEditar(doc, nombre, correo, telefono, rol, tipoDoc, ficha, programa) {
  var editAvatar = document.getElementById('editAvatar');
  if (editAvatar) editAvatar.textContent = (nombre || 'US').slice(0, 2).toUpperCase();

  var setVal = function (id, val) {
    var el = document.getElementById(id);
    if (el) el.value = val || '';
  };
  var setTxt = function (id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val || '';
  };

  setTxt('editDocLabel', 'Documento: ' + doc);
  setVal('edit_doc_hidden', doc);
  setVal('edit_tipo_doc_display', tipoDoc || '');
  setVal('edit_num_doc_display', doc);
  setVal('edit_nombre', nombre);
  setVal('edit_correo', correo);
  setVal('edit_telefono', telefono);
  setVal('edit_ficha', ficha);
  setVal('edit_programa', programa);
  setVal('edit_password', '');

  var selRol = document.getElementById('edit_rol');
  if (selRol) {
    for (var i = 0; i < selRol.options.length; i++) {
      selRol.options[i].selected = (selRol.options[i].value === rol || selRol.options[i].text === rol);
    }
  }

  var modalEditEl = document.getElementById('modalEditarUsuario');
  if (modalEditEl) {
    new bootstrap.Modal(modalEditEl).show();
  }
}
