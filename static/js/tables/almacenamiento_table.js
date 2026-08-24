/* ═══════════════════════════════════════════
   static/js/tables/almacenamiento_table.js
   DataTable configuration for Almacenamiento (Almacenes & Estantes)
   ═══════════════════════════════════════════ */
$(document).ready(function () {
  if ($('#almacenes-table').length) {
    // Extraer y remover la fila de estado vacío (evita warning TN/4)
    var emptyStateAlmacenes = '';
    $('#almacenes-table tbody tr').each(function () {
      if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
        emptyStateAlmacenes = $(this).find('td').html();
        $(this).remove();
      }
    });

    $('#almacenes-table').DataTable({
      responsive: true,
      dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6"f>>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
      buttons: window.obtenerBotonesDataTable('almacenamiento'),
      language: {
        url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
      },
      order: [],
      columnDefs: [
        { orderable: false, targets: [2, 5] } // Detalles (2) and Acciones (5) are not sortable
      ],
      pageLength: 10,
      lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'Todos']],
      drawCallback: function (settings) {
        if (settings.aiDisplay.length === 0 && emptyStateAlmacenes) {
          $(this).find('.dataTables_empty').html(emptyStateAlmacenes);
        }
        // Re-initialize Bootstrap tooltips inside the table after redraw
        var tooltipTriggerList = this.api().table().container().querySelectorAll('[data-bs-toggle="tooltip"]');
        var tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
          return bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
        });
      }
    });
  }

  if ($('#estantes-table').length) {
    // Extraer y remover la fila de estado vacío (evita warning TN/4)
    var emptyStateEstantes = '';
    $('#estantes-table tbody tr').each(function () {
      if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
        emptyStateEstantes = $(this).find('td').html();
        $(this).remove();
      }
    });

    $('#estantes-table').DataTable({
      responsive: true,
      dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6"f>>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
      buttons: window.obtenerBotonesDataTable('almacenamiento'),
      language: {
        url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
      },
      order: [],
      columnDefs: [
        { orderable: false, targets: [3, 6] } // Detalles (3) and Acciones (6) are not sortable
      ],
      pageLength: 10,
      lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'Todos']],
      drawCallback: function (settings) {
        if (settings.aiDisplay.length === 0 && emptyStateEstantes) {
          $(this).find('.dataTables_empty').html(emptyStateEstantes);
        }
        // Re-initialize Bootstrap tooltips inside the table after redraw
        var tooltipTriggerList = this.api().table().container().querySelectorAll('[data-bs-toggle="tooltip"]');
        var tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
          return bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
        });
      }
    });
  }
});
