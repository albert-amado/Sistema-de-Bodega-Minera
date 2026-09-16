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

  // Inicializar DataTables Responsive si la función compartida existe
  if (typeof window.initSBMDataTable === 'function') {
    window.initSBMDataTable('#pu-tabla', {
      modulo: 'prestamos',
      order: [[1, 'desc']],
      columnDefs: [
        { orderable: false, targets: [0, 2, 6] }
      ],
      pageLength: 10
    });
  }
});
