/* ═══════════════════════════════════════════
   static/js/tables/mantenimiento_table.js
   DataTable configuration for Mantenimiento
   ═══════════════════════════════════════════ */
$(document).ready(function () {
  // Extraer y remover la fila de estado vacío (evita warning TN/4)
  var emptyStateHtml = '';
  $('#mantenimiento-table tbody tr').each(function () {
    if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
      emptyStateHtml = $(this).find('td').html();
      $(this).remove();
    }
  });

  window.initSBMDataTable('#mantenimiento-table', {
    modulo: 'mantenimiento',
    order: [[0, 'desc']],
    columnDefs: [
      { orderable: false, targets: [6, 7] } // Acciones (6) and Historial (7) no ordenables
    ],
    pageLength: 10
  });
});
