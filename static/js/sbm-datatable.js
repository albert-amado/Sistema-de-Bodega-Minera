/**
 * static/js/sbm-datatable.js
 * =============================================================================
 * Componente Base Reutilizable de DataTables Responsive para Sistema de Bodega Minera
 * =============================================================================
 * Proporciona:
 * - Traducción al español integrada (sin dependencia de CDN).
 * - Soporte Responsive oficial con filas hijas expandibles (ícono '+').
 * - Prioridad de columnas (la identificación principal y las acciones nunca colapsan).
 * - Integración con botones de exportación oficiales (Excel, PDF, Imprimir).
 * - Configuración personalizable por tabla con valores predeterminados sólidos.
 */

(function (window, $) {
  'use strict';

  // ─────────────────────────────────────────────────────────────────────────────
  // 1. DICCIONARIO DE IDIOMA ESPAÑOL INTEGRADO
  // ─────────────────────────────────────────────────────────────────────────────
  var SBM_DATATABLES_SPANISH = {
    processing: "Procesando registros...",
    search: '<i class="bi bi-search me-1"></i> Buscar:',
    searchPlaceholder: "Filtrar en esta tabla...",
    lengthMenu: "Mostrar _MENU_ registros",
    info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
    infoEmpty: "Mostrando 0 a 0 de 0 registros",
    infoFiltered: "(filtrado de _MAX_ registros totales)",
    infoPostFix: "",
    loadingRecords: "Cargando datos...",
    zeroRecords: "No se encontraron coincidencias.",
    emptyTable: "No hay datos disponibles en esta tabla.",
    paginate: {
      first: '<i class="bi bi-chevron-double-left"></i>',
      previous: '<i class="bi bi-chevron-left"></i> Anterior',
      next: 'Siguiente <i class="bi bi-chevron-right"></i>',
      last: '<i class="bi bi-chevron-double-right"></i>'
    },
    aria: {
      sortAscending: ": activar para ordenar la columna de manera ascendente",
      sortDescending: ": activar para ordenar la columna de manera descendente"
    },
    buttons: {
      copy: "Copiar",
      colvis: "Visibilidad"
    },
    responsive: {
      collapsed: "Contraer detalles",
      expanded: "Expandir detalles"
    }
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // 2. RENDERIZADOR PERSONALIZADO PARA FILA EXPANDIBLE (CHILD ROW)
  // ─────────────────────────────────────────────────────────────────────────────
  function sbmChildRowRenderer(api, rowIdx, columns) {
    var hiddenCols = $.grep(columns, function (col) {
      return col.hidden;
    });

    if (!hiddenCols.length) {
      return false;
    }

    var $container = $('<div class="sbm-child-row-wrapper p-3 my-2 rounded-3 border bg-white shadow-xs"></div>');
    var $header = $('<div class="d-flex align-items-center justify-content-between pb-2 mb-2 border-bottom">' +
      '<span class="fw-bold text-dark small text-uppercase" style="letter-spacing:0.04em;">' +
      '<i class="bi bi-info-circle text-warning me-1"></i>Información adicional' +
      '</span>' +
      '<span class="badge bg-light text-secondary border small">Vista expandida</span>' +
      '</div>');
    $container.append($header);

    var $grid = $('<div class="row g-2 sbm-child-row-grid"></div>');

    $.each(hiddenCols, function (i, col) {
      // Ignorar columnas de control vacías
      if (!col.title || col.title.trim() === '') return;

      var $colDiv = $('<div class="col-12 col-sm-6 col-md-4 sbm-child-item"></div>');
      var $label = $('<div class="text-secondary small fw-bold text-uppercase mb-0" style="font-size:0.7rem; letter-spacing:0.03em;"></div>').html(col.title);
      var $val = $('<div class="sbm-child-val text-dark small mt-0 text-break"></div>').html(col.data);

      $colDiv.append($label).append($val);
      $grid.append($colDiv);
    });

    $container.append($grid);
    return $container;
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 3. FUNCIÓN PRINCIPAL DE INICIALIZACIÓN: window.initSBMDataTable
  // ─────────────────────────────────────────────────────────────────────────────
  window.initSBMDataTable = function (selector, userOptions) {
    var $table = $(selector);
    if (!$table.length) {
      return null;
    }

    // Si ya fue inicializada, devolver la instancia existente
    if ($.fn.DataTable.isDataTable($table)) {
      return $table.DataTable();
    }

    userOptions = userOptions || {};

    // Obtener identificador del módulo para los botones de exportación
    var tableId = $table.attr('id') || '';
    var moduloName = userOptions.modulo || 'inventario';
    if (!userOptions.modulo) {
      if (tableId.includes('prestamo')) moduloName = 'prestamos';
      else if (tableId.includes('devolucion')) moduloName = 'devoluciones';
      else if (tableId.includes('usuario')) moduloName = 'usuarios';
      else if (tableId.includes('almacen') || tableId.includes('estante')) moduloName = 'almacenamiento';
      else if (tableId.includes('proveedor')) moduloName = 'proveedores';
      else if (tableId.includes('movimiento')) moduloName = 'movimientos';
    }

    // Botones de exportación
    var exportButtons = [];
    if (userOptions.buttons !== false) {
      if (typeof window.obtenerBotonesDataTable === 'function') {
        exportButtons = window.obtenerBotonesDataTable(moduloName);
      }
      if (userOptions.customButtons) {
        exportButtons = exportButtons.concat(userOptions.customButtons);
      }
    }

    // Limpiar fila vacía previa para evitar advertencia tn/4
    var emptyStateHtml = '';
    $table.find('tbody tr').each(function () {
      if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
        emptyStateHtml = $(this).find('td').html();
        $(this).remove();
      }
    });

    // Configuración base sólida
    var defaultDom = '<"row mb-3 align-items-center g-2"<"col-md-3 col-sm-6"l><"col-md-5 col-sm-12 text-md-center my-2 my-md-0"B><"col-md-4 col-sm-6 text-md-end"f>>' +
                     't' +
                     '<"row mt-3 align-items-center g-2"<"col-md-6 col-sm-12 text-muted small"i><"col-md-6 col-sm-12 d-flex justify-content-md-end"p>>';

    var finalConfig = $.extend(true, {
      responsive: {
        details: {
          type: 'column',
          target: '.dtr-control, td:first-child',
          renderer: sbmChildRowRenderer
        },
        breakpoints: [
          { name: 'desktop', width: Infinity },
          { name: 'tablet-l', width: 1024 },
          { name: 'tablet-p', width: 768 },
          { name: 'mobile-l', width: 480 },
          { name: 'mobile-p', width: 320 }
        ]
      },
      language: SBM_DATATABLES_SPANISH,
      dom: exportButtons.length ? defaultDom : '<"row mb-3 align-items-center g-2"<"col-md-6"l><"col-md-6 text-md-end"f>>t<"row mt-3 align-items-center g-2"<"col-md-6"i><"col-md-6 d-flex justify-content-md-end"p>>',
      buttons: exportButtons,
      pageLength: userOptions.pageLength || 10,
      lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'Todos']],
      order: userOptions.order || [],
      autoWidth: false,
      drawCallback: function (settings) {
        if (settings.aiDisplay && settings.aiDisplay.length === 0 && emptyStateHtml) {
          $table.find('.dataTables_empty').html(emptyStateHtml);
        }
        // Inicializar tooltips de Bootstrap
        var container = this.api().table().container();
        if (container && typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
          var tooltips = container.querySelectorAll('[data-bs-toggle="tooltip"]');
          tooltips.forEach(function (el) {
            bootstrap.Tooltip.getOrCreateInstance(el);
          });
        }
      }
    }, userOptions);

    // Inicializar DataTable
    var dtInstance = $table.DataTable(finalConfig);

    // Permitir clic accesible con teclado en la primera columna para expandir
    $table.on('keydown', 'td.dtr-control', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        $(this).trigger('click');
      }
    });

    return dtInstance;
  };

  // Exponer diccionario
  window.SBM_DATATABLES_SPANISH = SBM_DATATABLES_SPANISH;

})(window, jQuery);
