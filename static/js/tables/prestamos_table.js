/* ═══════════════════════════════════════════
   static/js/tables/prestamos_table.js
   DataTable & Collapsible Details for Préstamos
  ═══════════════════════════════════════════ */
$(document).ready(function () {
  var childRows = {};

  // ─── PASO 1: extraer las filas de detalle ANTES de que DataTables
  //            las cuente como filas de datos.
  $('#prestamo-table tbody tr.detail-row').each(function () {
    var id = $(this).attr('id');
    if (id) {
      childRows[id] = $(this).clone().removeClass('d-none');
    }
    $(this).remove();
  });

  // Extraer y remover la fila de estado vacío
  var emptyStateHtml = '';
  $('#prestamo-table tbody tr').each(function () {
    if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
      emptyStateHtml = $(this).find('td').html();
      $(this).remove();
    }
  });

  // ─── PASO 2: inicializar DataTable sobre el tbody ya limpio
  var table = $('#prestamo-table').DataTable({
    responsive: true,
    dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6">>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
    buttons: window.obtenerBotonesDataTable('prestamos'),
    language: {
      url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
    },
    order: [],
    columnDefs: [
      { orderable: false, targets: [0, 3, 7] } // expand (0), tools (3), actions (7)
    ],
    pageLength: 10,
    lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'Todos']],
    drawCallback: function (settings) {
      if (settings.aiDisplay.length === 0 && emptyStateHtml) {
        $(this).find('.dataTables_empty').html(emptyStateHtml);
      }
      var tooltipTriggerList = this.api().table().container()
            .querySelectorAll('[data-bs-toggle="tooltip"]');
      [...tooltipTriggerList].forEach(function (el) {
        bootstrap.Tooltip.getOrCreateInstance(el);
      });
    }
  });

  // ─── Real-time live filtering ───
  $('input[name="q"]').on('keyup input', function () {
    table.search(this.value).draw();
  });

  // ─── PASO 3: función toggle de detalles
  function togglePrestamoDetail(btn) {
    var targetId = btn.attr('data-target-detail');
    var tr = btn.closest('tr');
    if (!tr.length) return;

    // 1. Si la fila de detalle se encuentra directamente en el DOM
    var $domDetail = $('#' + targetId);
    if ($domDetail.length && $domDetail.parent().is('tbody')) {
      if ($domDetail.hasClass('d-none')) {
        $domDetail.removeClass('d-none');
        tr.addClass('shown');
        btn.find('.row-chevron, svg').css('transform', 'rotate(90deg)');
      } else {
        $domDetail.addClass('d-none');
        tr.removeClass('shown');
        btn.find('.row-chevron, svg').css('transform', 'rotate(0deg)');
      }
      return;
    }

    // 2. Manejo mediante DataTables row.child
    if (table && table.row) {
      var row = table.row(tr);
      if (row && row.child) {
        if (row.child.isShown()) {
          row.child.hide();
          tr.removeClass('shown');
          btn.find('.row-chevron, svg').css('transform', 'rotate(0deg)');
        } else {
          var $detailNode = childRows[targetId];
          if ($detailNode) {
            var $clone = $detailNode.clone().removeClass('d-none');
            row.child($clone).show();
            $(row.child()).find('td').first().attr('colspan', 8);
          }
          tr.addClass('shown');
          btn.find('.row-chevron, svg').css('transform', 'rotate(90deg)');
        }
      }
    }
  }

  // Delegar clics en el botón de toggle y en la fila
  $('#prestamo-table').on('click', '.btn-toggle-details', function (e) {
    e.preventDefault();
    e.stopPropagation();
    togglePrestamoDetail($(this));
  });

  $('#prestamo-table').on('click', 'tbody > tr:not(.detail-row):not(.child)', function (e) {
    if ($(e.target).closest('button, a, input, select, textarea, form, .badge').length) {
      return;
    }
    var btn = $(this).find('.btn-toggle-details');
    if (btn.length) {
      togglePrestamoDetail(btn);
    }
  });
});
