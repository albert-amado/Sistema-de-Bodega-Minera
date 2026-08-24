/* ═══════════════════════════════════════════
   static/js/tables/devoluciones_table.js
   DataTable, Details & Actions for Devoluciones
  ═══════════════════════════════════════════ */
$(document).ready(function () {
  var childRows = {};

  // ─── PASO 1: extraer las filas de detalle ANTES de que DataTables
  //            las cuente como filas de datos.
  $('#devoluciones-table tbody tr.detail-row').each(function () {
    var id = $(this).attr('id');
    if (id) {
      childRows[id] = $(this).clone().removeClass('d-none');
    }
    $(this).remove();
  });

  // Extraer y remover la fila de estado vacío
  var emptyStateHtml = '';
  $('#devoluciones-table tbody tr').each(function () {
    if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
      emptyStateHtml = $(this).find('td').html();
      $(this).remove();
    }
  });

  // ─── PASO 2: inicializar DataTable sobre el tbody ya limpio
  var table = $('#devoluciones-table').DataTable({
    responsive: true,
    dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6">>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
    buttons: window.obtenerBotonesDataTable('devoluciones'),
    language: {
      url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
    },
    order: [],
    columnDefs: [
      { orderable: false, targets: [0, 4, 6] }
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

  // ─── Buscador en tiempo real y Filtros ───
  $('#devoluciones-busqueda').on('keyup input', function () {
    table.search(this.value).draw();
  });

  $('#devoluciones-estado').on('change', function () {
    var val = $(this).val();
    table.column(6).search(val ? val : '', true, false).draw();
  });

  $('#btn-limpiar-filtros-dev').on('click', function (e) {
    e.preventDefault();
    $('#devoluciones-busqueda').val('');
    $('#devoluciones-estado').val('');
    table.search('').column(6).search('').draw();
  });

  // ─── PASO 3: función toggle de detalles
  function toggleDevolucionDetail(btn) {
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
            $(row.child()).find('td').first().attr('colspan', 7);
          }
          tr.addClass('shown');
          btn.find('.row-chevron, svg').css('transform', 'rotate(90deg)');
        }
      }
    }
  }

  // Delegar clics en el botón de toggle y en la fila
  $('#devoluciones-table').on('click', '.btn-toggle-details', function (e) {
    e.preventDefault();
    e.stopPropagation();
    toggleDevolucionDetail($(this));
  });

  $('#devoluciones-table').on('click', 'tbody > tr:not(.detail-row):not(.child)', function (e) {
    if ($(e.target).closest('button, a, input, select, textarea, form, .badge').length) {
      return;
    }
    var btn = $(this).find('.btn-toggle-details');
    if (btn.length) {
      toggleDevolucionDetail(btn);
    }
  });

  // ─── Clic delegado global: Aceptar devolución
  $(document).on('click', '.btn-aceptar-click', function (e) {
    e.preventDefault();
    var btn = $(this);
    if (typeof abrirAceptar === 'function') {
      abrirAceptar(btn.attr('data-pk'), btn.attr('data-prestamo-pk'), btn.attr('data-usuario'));
    }
  });

  // ─── Clic delegado global: Rechazar devolución
  $(document).on('click', '.btn-rechazar-click', function (e) {
    e.preventDefault();
    var btn = $(this);
    if (typeof abrirRechazar === 'function') {
      abrirRechazar(btn.attr('data-pk'), btn.attr('data-prestamo-pk'), btn.attr('data-usuario'));
    }
  });
});
