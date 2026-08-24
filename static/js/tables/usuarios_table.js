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

  $('#usuarios-table').DataTable({
    responsive: true,
    dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6"f>>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
    buttons: window.obtenerBotonesDataTable('usuarios'),
    language: {
      url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
    },
    order: [],
    columnDefs: [
      { orderable: false, targets: [6] } // Acciones (6) is not sortable
    ],
    pageLength: 10,
    lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'Todos']],
    drawCallback: function (settings) {
      if (settings.aiDisplay.length === 0 && emptyStateHtml) {
        $(this).find('.dataTables_empty').html(emptyStateHtml);
      }
      // Re-initialize Bootstrap tooltips inside the table after redraw
      var tooltipTriggerList = this.api().table().container().querySelectorAll('[data-bs-toggle="tooltip"]');
      var tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
        return bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
      });
    }
  });
});
