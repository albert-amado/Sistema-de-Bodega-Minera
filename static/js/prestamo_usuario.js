/**
 * static/js/prestamo_usuario.js
 * Funcionalidades del panel de préstamos para el usuario/aprendiz:
 * acordeones de detalle de préstamo y filtros interactivos de estado.
 */

function puFiltrar(estado, btn) {
  // Soporta tanto la clase antigua (pu-filter-btn) como la nueva (sfb-pill)
  var pills = document.querySelectorAll('.sfb-pill, .pu-filter-btn');
  pills.forEach(function (b) {
    b.classList.remove('active', 'btn-primary');
    b.classList.add('btn-outline-secondary');
  });
  if (btn) {
    btn.classList.remove('btn-outline-secondary');
    btn.classList.add('active', 'btn-primary');
  }

  document.querySelectorAll('#pu-tabla .pu-row').forEach(function (tr) {
    var mostrar =
      estado === 'todos' || tr.dataset.estado === estado || (estado === 'activo' && tr.dataset.estado === 'ENTREGADO');
    tr.style.display = mostrar ? '' : 'none';
    var siguiente = tr.nextElementSibling;
    if (siguiente && siguiente.querySelector('.collapse')) {
      siguiente.style.display = mostrar ? '' : 'none';
    }
  });
}
window.puFiltrar = puFiltrar;

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-bs-target^="#pu-detail-"]').forEach(function (btn) {
    var target = document.querySelector(btn.getAttribute('data-bs-target'));
    if (!target) return;
    target.addEventListener('show.bs.collapse', function () {
      var icon = btn.querySelector('.pu-chevron');
      if (icon) icon.style.transform = 'rotate(90deg)';
    });
    target.addEventListener('hide.bs.collapse', function () {
      var icon = btn.querySelector('.pu-chevron');
      if (icon) icon.style.transform = 'rotate(0deg)';
    });
  });

  // Delegación para botones de filtro (sfb-pill y legacy pu-filter-btn)
  document.querySelectorAll('.sfb-pill, .pu-filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var estado = btn.getAttribute('data-filter') || 'todos';
      puFiltrar(estado, btn);
    });
  });

  // Manejo de herramientas en modal de solicitud individual
  var solAddBtn = document.getElementById('sol-add-item');
  var solContainer = document.getElementById('sol-items-container');
  if (solAddBtn && solContainer) {
    function updateSolDelButtons() {
      var rows = solContainer.querySelectorAll('.sol-item-row');
      rows.forEach(function (r) {
        var del = r.querySelector('.sol-del-btn');
        if (del) {
          if (rows.length <= 1) del.classList.add('disabled');
          else del.classList.remove('disabled');
        }
      });
    }

    solAddBtn.addEventListener('click', function () {
      var firstRow = solContainer.querySelector('.sol-item-row');
      if (!firstRow) return;
      var clone = firstRow.cloneNode(true);
      var sel = clone.querySelector('select');
      var num = clone.querySelector('input[type="number"]');
      if (sel) sel.value = '';
      if (num) num.value = '1';
      var delBtn = clone.querySelector('.sol-del-btn');
      if (delBtn) delBtn.classList.remove('disabled');
      solContainer.appendChild(clone);
      updateSolDelButtons();
    });

    solContainer.addEventListener('click', function (e) {
      var delBtn = e.target.closest('.sol-del-btn');
      if (!delBtn || delBtn.classList.contains('disabled')) return;
      var row = delBtn.closest('.sol-item-row');
      if (row && solContainer.querySelectorAll('.sol-item-row').length > 1) {
        row.remove();
        updateSolDelButtons();
      }
    });
  }

  // Inicializar DataTables Responsive si la función compartida existe
  if (typeof window.initSBMDataTable === 'function') {
    window.initSBMDataTable('#pu-tabla', {
      modulo: 'prestamos',
      searchPlaceholder: 'Buscar en mis préstamos por herramienta, fecha, estado…',
      order: [[1, 'desc']],
      columnDefs: [
        { orderable: false, targets: [0, 2, 6] }
      ],
      pageLength: 10
    });
  }
});
