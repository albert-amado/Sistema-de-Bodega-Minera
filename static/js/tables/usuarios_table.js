/* ═══════════════════════════════════════════
   static/js/tables/usuarios_table.js
   DataTable configuration for Usuarios
   ═══════════════════════════════════════════ */
$(document).ready(function () {
  // Extraer y remover la fila de estado vacío (evita warning TN/4)
  var emptyStateHtml = '';
  $('#usuarios-table tbody tr').each(function () {
    if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
      emptyStateHtml = $(this).find('td').html();
      $(this).remove();
    }
  });

  window.initSBMDataTable('#usuarios-table', {
    modulo: 'usuarios',
    order: [[0, 'asc']], // Orden alfabético por nombre
    columnDefs: [
      { orderable: false, targets: [6] } // Acciones no ordenable
    ],
    pageLength: 10
  });
});
