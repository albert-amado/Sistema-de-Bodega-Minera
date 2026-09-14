/**
 * static/js/inventario.js
 * Lógica modularizada para la gestión del inventario de herramientas,
 * modales dinámicos, carga asíncrona de estantes y selects con búsqueda.
 */

function cargarEstantes(almacenId, selectEstanteEl, estanteSeleccionado) {
  if (!selectEstanteEl) return;
  if (!almacenId) {
    selectEstanteEl.innerHTML = '<option value="">-- Selecciona un almacén primero --</option>';
    selectEstanteEl.disabled = true;
    return;
  }
  selectEstanteEl.innerHTML = '<option value="">Cargando...</option>';
  selectEstanteEl.disabled = true;

  var apiUrl = selectEstanteEl.getAttribute('data-api-url') || '/api/estantes/';

  fetch(apiUrl + (apiUrl.includes('?') ? '&' : '?') + 'almacen_id=' + encodeURIComponent(almacenId))
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      selectEstanteEl.innerHTML = '<option value="">-- Selecciona estante --</option>';
      (data.estantes || []).forEach(function (est) {
        var opt = document.createElement('option');
        opt.value = est.id;
        opt.textContent = est.codigo + ' (' + est.ubicacion + ')';
        if (estanteSeleccionado && String(est.id) === String(estanteSeleccionado)) {
          opt.selected = true;
        }
        selectEstanteEl.appendChild(opt);
      });
      selectEstanteEl.disabled = false;
    })
    .catch(function () {
      selectEstanteEl.innerHTML = '<option value="">Error al cargar estantes</option>';
      selectEstanteEl.disabled = true;
    });
}

function abrirEditar(id, sku, nombre, descripcion, stock, categoria, almacenId, estanteId) {
  var idEl = document.getElementById('edit_producto_id');
  var skuEl = document.getElementById('edit_sku');
  var nomEl = document.getElementById('edit_nombre');
  var descEl = document.getElementById('edit_descripcion');
  var stockEl = document.getElementById('edit_stock');
  var catSelect = document.getElementById('edit_categoria');
  var almacenSelect = document.getElementById('edit_almacen');
  var estanteSelect = document.getElementById('edit_estante');

  if (idEl) idEl.value = id;
  if (skuEl) skuEl.value = sku;
  if (nomEl) nomEl.value = nombre;
  if (descEl) descEl.value = descripcion;
  if (stockEl) stockEl.value = stock;

  if (catSelect) {
    if (categoria && categoria !== 'None' && categoria !== '') {
      catSelect.value = categoria;
      if (typeof $(catSelect).val === 'function') {
        $(catSelect).val(categoria).trigger('change.select2');
      }
    } else {
      catSelect.value = '';
      if (typeof $(catSelect).val === 'function') {
        $(catSelect).val('').trigger('change.select2');
      }
    }
  }

  if (almacenSelect && estanteSelect) {
    if (almacenId && almacenId !== 'None' && almacenId !== '') {
      almacenSelect.value = almacenId;
      cargarEstantes(almacenId, estanteSelect, estanteId);
    } else {
      almacenSelect.value = '';
      estanteSelect.innerHTML = '<option value="">-- Selecciona un almacén primero --</option>';
      estanteSelect.disabled = true;
    }
  }

  var modalEl = document.getElementById('modalEditarHerramienta');
  if (modalEl && typeof bootstrap !== 'undefined') {
    var modalEdit = bootstrap.Modal.getOrCreateInstance(modalEl, { backdrop: 'static' });
    modalEdit.show();
  }
}

// Flujo puente: Abrir categoría desde el modal de producto conservando datos
function abrirCategoriaDesdeProducto() {
  var modalProdElement = document.getElementById('modalNuevaHerramienta');
  if (modalProdElement && typeof bootstrap !== 'undefined') {
    var modalProd = bootstrap.Modal.getInstance(modalProdElement);
    if (modalProd) modalProd.hide();

    var formCat = document.querySelector('#modalNuevaCategoria form');
    if (formCat) {
      var skuInput = modalProdElement.querySelector('input[name="codigo_sku"]');
      var nomInput = modalProdElement.querySelector('input[name="nombre"]');
      var descInput = modalProdElement.querySelector('textarea[name="descripcion"]');
      var stockInput = modalProdElement.querySelector('input[name="stock"]');

      var catSku = formCat.querySelector('input[name="codigo_sku"]');
      var catNom = formCat.querySelector('input[name="nombre"]');
      var catDesc = formCat.querySelector('input[name="descripcion"]');
      var catStock = formCat.querySelector('input[name="stock"]');

      if (catSku && skuInput) catSku.value = skuInput.value;
      if (catNom && nomInput) catNom.value = nomInput.value;
      if (catDesc && descInput) catDesc.value = descInput.value;
      if (catStock && stockInput) catStock.value = stockInput.value;
    }

    var modalCat = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalNuevaCategoria'));
    modalCat.show();
  }
}

document.addEventListener('DOMContentLoaded', function () {
  var nuevoAlmacen = document.getElementById('nueva_almacen');
  if (nuevoAlmacen) {
    nuevoAlmacen.addEventListener('change', function () {
      cargarEstantes(this.value, document.getElementById('nueva_estante'));
    });
  }

  var editAlmacen = document.getElementById('edit_almacen');
  if (editAlmacen) {
    editAlmacen.addEventListener('change', function () {
      cargarEstantes(this.value, document.getElementById('edit_estante'));
    });
  }

  // Inicialización Select2 con tema Bootstrap 5
  if (typeof $ !== 'undefined' && $.fn.select2) {
    $('#select-categoria-nueva').select2({
      theme: 'bootstrap-5',
      dropdownParent: $('#modalNuevaHerramienta'),
      placeholder: '-- Sin Categoría --',
      allowClear: true,
      width: '100%',
      language: {
        noResults: function () {
          return 'No se encontraron resultados';
        }
      }
    });

    $('#edit_categoria').select2({
      theme: 'bootstrap-5',
      dropdownParent: $('#modalEditarHerramienta'),
      placeholder: '-- Sin Categoría --',
      allowClear: true,
      width: '100%',
      language: {
        noResults: function () {
          return 'No se encontraron resultados';
        }
      }
    });
  }

  // Delegación de eventos para botones de editar
  document.addEventListener('click', function (e) {
    var btnEditar = e.target.closest('.btn-editar-herramienta');
    if (btnEditar) {
      e.preventDefault();
      var id = btnEditar.getAttribute('data-id');
      var sku = btnEditar.getAttribute('data-sku');
      var nombre = btnEditar.getAttribute('data-nombre');
      var descripcion = btnEditar.getAttribute('data-descripcion') || '';
      var stock = btnEditar.getAttribute('data-stock');
      var categoria = btnEditar.getAttribute('data-categoria') || '';
      var almacenId = btnEditar.getAttribute('data-almacen-id') || '';
      var estanteId = btnEditar.getAttribute('data-estante-id') || '';

      abrirEditar(id, sku, nombre, descripcion, stock, categoria, almacenId, estanteId);
    }

    var btnPuente = e.target.closest('.btn-abrir-cat-desde-prod');
    if (btnPuente) {
      e.preventDefault();
      abrirCategoriaDesdeProducto();
    }
  });

  // Apertura automática basada en dataset del body/contenedor
  var triggerModal = document.body.dataset.triggerModal;
  if (triggerModal === 'producto') {
    var modalProd = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalNuevaHerramienta'));
    modalProd.show();
  } else if (triggerModal === 'categoria') {
    var modalCat = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalNuevaCategoria'));
    modalCat.show();
  }
});
