/* ═══════════════════════════════════════════
   static/js/tables/almacenamiento_table.js
   DataTable configuration for Almacenamiento (Almacenes & Estantes)
   ═══════════════════════════════════════════ */
$(document).ready(function () {
  if ($('#almacenes-table').length) {
    window.initSBMDataTable('#almacenes-table', {
      modulo: 'almacenamiento',
      searchPlaceholder: 'Buscar almacén por nombre, ubicación…',
      order: [[0, 'asc']], // ID ascendente
      columnDefs: [
        { orderable: false, targets: [2, 5] } // Ubicación y Acciones no ordenables
      ],
      pageLength: 10
    });
  }

  if ($('#estantes-table').length) {
    window.initSBMDataTable('#estantes-table', {
      modulo: 'almacenamiento',
      searchPlaceholder: 'Buscar estante por código, almacén…',
      order: [[0, 'asc']],
      columnDefs: [
        { orderable: false, targets: [3, 5] } // Dimensiones y Acciones no ordenables
      ],
      pageLength: 10
    });
  }

  if ($('#detalle-almacen-table').length) {
    window.initSBMDataTable('#detalle-almacen-table', {
      modulo: 'almacenamiento',
      searchPlaceholder: 'Buscar estante o ubicación…',
      order: [[0, 'asc']],
      columnDefs: [
        { orderable: false, targets: [2, 4] } // Dimensiones y Acciones no ordenables
      ],
      pageLength: 10
    });
  }
});
