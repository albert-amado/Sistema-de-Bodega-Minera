/**
 * static/js/prestamo_usuario.js
 * Funcionalidades del panel de préstamos para el usuario/aprendiz:
 * acordeones de detalle de préstamo y filtros interactivos de estado.
 */

function puFiltrar(estado, btn) {
  document.querySelectorAll('.pu-filter-btn').forEach(function (b) {
    b.classList.remove('btn-primary');
    b.classList.add('btn-outline-secondary');
  });
  if (btn) {
    btn.classList.remove('btn-outline-secondary');
    btn.classList.add('btn-primary');
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

  // Delegación para botones de filtro
  document.querySelectorAll('.pu-filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      var estado = btn.getAttribute('data-filter') || 'todos';
      puFiltrar(estado, btn);
    });
  });
});
