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
 * - Componente oficial de búsqueda SBM (<TableSearchBox>):
 *     * Insensibilidad a mayúsculas/minúsculas y tildes (normalización NFD).
 *     * Búsqueda en tiempo real con debounce de 300ms.
 *     * Botón dinámico 'x' para limpiar la búsqueda inmediatamente.
 *     * Búsqueda multi-término sobre todas las columnas (incluyendo las colapsadas).
 *     * Placeholders contextuales por módulo en español.
 *     * Estado elegante de "Sin resultados" temático.
 * - Configuración personalizable por tabla con valores predeterminados sólidos.
 */

(function (window, $) {
  'use strict';

  // ─────────────────────────────────────────────────────────────────────────────
  // 1. NORMALIZACIÓN DE TEXTO (INSENSIBILIDAD A TILDES / DIACRÍTICOS Y HTML)
  // ─────────────────────────────────────────────────────────────────────────────
  function sbmNormalize(text) {
    return (text || '')
      .toString()
      .replace(/<[^>]*>/g, ' ')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  // Extensión de búsqueda personalizada en DataTables para normalizar tildes y multi-token
  if ($.fn.dataTable && $.fn.dataTable.ext && $.fn.dataTable.ext.search) {
    $.fn.dataTable.ext.search.push(function (settings, data, dataIndex) {
      var query = settings._sbmSearchQuery;
      if (!query) {
        return true;
      }
      var tokens = settings._sbmSearchTokens;
      if (!tokens || !tokens.length) {
        return true;
      }

      // Concatenar el contenido textual de todas las columnas (incluso las colapsadas en responsive)
      var rowText = '';
      for (var i = 0; i < data.length; i++) {
        rowText += ' ' + sbmNormalize(data[i]);
      }

      // Todos los tokens deben coincidir en la fila
      for (var t = 0; t < tokens.length; t++) {
        if (rowText.indexOf(tokens[t]) === -1) {
          return false;
        }
      }
      return true;
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 2. DICCIONARIOS Y PLACEHOLDERS CONTEXTUALES
  // ─────────────────────────────────────────────────────────────────────────────
  var SBM_MODULE_PLACEHOLDERS = {
    inventario: 'Buscar herramienta por SKU, nombre, estante…',
    prestamos: 'Buscar por ID, solicitante, documento, herramienta…',
    devoluciones: 'Buscar por ID de préstamo, aprendiz, estado…',
    usuarios: 'Buscar usuario por nombre, documento, correo, ficha…',
    almacenamiento: 'Buscar almacén o estante por nombre, ubicación…',
    almacenes: 'Buscar almacén por nombre, ubicación…',
    estantes: 'Buscar estante por código, ubicación…',
    proveedores: 'Buscar proveedor por NIT, teléfono, correo…',
    movimientos: 'Buscar movimiento por fecha, herramienta, tipo…',
    mantenimiento: 'Buscar mantenimiento por ID, herramienta, estado…',
    reportes: 'Buscar en reportes de bodega…'
  };

  var SBM_DATATABLES_SPANISH = {
    processing: "Procesando registros...",
    search: "Buscar:",
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
  // 3. RENDERIZADOR PERSONALIZADO PARA FILA EXPANDIBLE (CHILD ROW)
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
  // 4. COMPONENTE REUTILIZABLE DE BÚSQUEDA SBM: window.createSBMTableSearch
  // ─────────────────────────────────────────────────────────────────────────────
  function applySBMSearch(dtInstance, rawValue) {
    var settings = dtInstance.settings()[0];
    if (!settings) return;

    var norm = sbmNormalize(rawValue);
    settings._sbmSearchRaw = rawValue;
    settings._sbmSearchQuery = norm;
    settings._sbmSearchTokens = norm ? norm.split(/\s+/).filter(Boolean) : [];

    // Al filtrar, regresar a la primera página y redibujar
    dtInstance.page('first').draw('page');
  }

  window.createSBMTableSearch = function (dtInstance, options) {
    options = options || {};
    var placeholder = options.placeholder || 'Filtrar registros en esta tabla…';
    var debounceMs = options.debounceMs || 300;
    var searchTimeout = null;

    // Caso A: Si se proporcionó un selector externo (ej. #inventario-busqueda)
    if (options.externalInput) {
      var $extInput = $(options.externalInput);
      if ($extInput.length) {
        var $wrap = $extInput.closest('.sfb-search-group');
        var $clearBtn = $wrap.find('.sbm-search-clear');

        // Crear botón 'x' si el contenedor no lo tiene
        if (!$clearBtn.length) {
          $wrap.css('position', 'relative');
          $clearBtn = $('<button type="button" class="sbm-search-clear d-none" title="Limpiar búsqueda" aria-label="Limpiar"><i class="bi bi-x-circle-fill"></i></button>');
          $wrap.append($clearBtn);
        }

        // Listener con debounce
        $extInput.off('input.sbm keyup.sbm').on('input.sbm keyup.sbm', function () {
          var val = $(this).val();
          if (val.length > 0) {
            $clearBtn.removeClass('d-none');
          } else {
            $clearBtn.addClass('d-none');
          }
          clearTimeout(searchTimeout);
          searchTimeout = setTimeout(function () {
            applySBMSearch(dtInstance, val);
          }, debounceMs);
        });

        // Botón limpiar
        $clearBtn.off('click.sbm').on('click.sbm', function (e) {
          e.preventDefault();
          $extInput.val('');
          $clearBtn.addClass('d-none');
          clearTimeout(searchTimeout);
          applySBMSearch(dtInstance, '');
          $extInput.focus();
        });

        // Tecla Escape para limpiar
        $extInput.off('keydown.sbm').on('keydown.sbm', function (e) {
          if (e.key === 'Escape' && $extInput.val().length > 0) {
            e.preventDefault();
            $clearBtn.trigger('click.sbm');
          }
        });

        // Búsqueda inicial si ya tiene valor
        var initVal = $extInput.val();
        if (initVal) {
          $clearBtn.removeClass('d-none');
          applySBMSearch(dtInstance, initVal);
        }

        return {
          input: $extInput,
          clearBtn: $clearBtn
        };
      }
    }

    // Caso B: Renderizar componente dentro de un contenedor o reemplazar .dataTables_filter
    var $target = $(options.container);
    if (!$target.length) return null;

    var $searchBox = $(
      '<div class="sbm-table-search-wrap">' +
        '<div class="sbm-search-inner">' +
          '<svg class="sbm-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<circle cx="11" cy="11" r="8"></circle>' +
            '<line x1="21" y1="21" x2="16.65" y2="16.65"></line>' +
          '</svg>' +
          '<input type="text" class="sbm-search-input" placeholder="' + placeholder + '" autocomplete="off" spellcheck="false">' +
          '<button type="button" class="sbm-search-clear d-none" title="Limpiar búsqueda" aria-label="Limpiar búsqueda">' +
            '<i class="bi bi-x-circle-fill"></i>' +
          '</button>' +
        '</div>' +
      '</div>'
    );

    $target.empty().append($searchBox);

    var $input = $searchBox.find('.sbm-search-input');
    var $clear = $searchBox.find('.sbm-search-clear');

    $input.on('input keyup', function () {
      var val = $(this).val();
      if (val.length > 0) {
        $clear.removeClass('d-none');
      } else {
        $clear.addClass('d-none');
      }
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(function () {
        applySBMSearch(dtInstance, val);
      }, debounceMs);
    });

    $clear.on('click', function (e) {
      e.preventDefault();
      $input.val('');
      $clear.addClass('d-none');
      clearTimeout(searchTimeout);
      applySBMSearch(dtInstance, '');
      $input.focus();
    });

    $input.on('keydown', function (e) {
      if (e.key === 'Escape' && $input.val().length > 0) {
        e.preventDefault();
        $clear.trigger('click');
      }
    });

    return {
      wrap: $searchBox,
      input: $input,
      clearBtn: $clear
    };
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // 5. FUNCIÓN PRINCIPAL DE INICIALIZACIÓN: window.initSBMDataTable
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

    // Obtener identificador del módulo
    var tableId = $table.attr('id') || '';
    var moduloName = userOptions.modulo || 'inventario';
    if (!userOptions.modulo) {
      if (tableId.includes('prestamo')) moduloName = 'prestamos';
      else if (tableId.includes('devolucion')) moduloName = 'devoluciones';
      else if (tableId.includes('usuario')) moduloName = 'usuarios';
      else if (tableId.includes('almacen') || tableId.includes('estante')) moduloName = 'almacenamiento';
      else if (tableId.includes('proveedor')) moduloName = 'proveedores';
      else if (tableId.includes('movimiento')) moduloName = 'movimientos';
      else if (tableId.includes('mantenimiento')) moduloName = 'mantenimiento';
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

    // Detectar si la pantalla tiene un buscador externo preexistente
    var externalSearchSelector = userOptions.externalSearch || null;
    if (!externalSearchSelector) {
      if (tableId === 'inventario-table' && $('#inventario-busqueda').length) {
        externalSearchSelector = '#inventario-busqueda';
      } else if (tableId === 'prestamo-table' && $('#prestamo-busqueda').length) {
        externalSearchSelector = '#prestamo-busqueda';
      } else if (tableId === 'devoluciones-table' && $('#devoluciones-busqueda').length) {
        externalSearchSelector = '#devoluciones-busqueda';
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

    // Configuración del DOM: Si hay buscador externo, no duplicamos 'f' en la tarjeta
    var defaultDomWithFilter = exportButtons.length
      ? '<"row mb-3 align-items-center g-2"<"col-md-3 col-sm-6"l><"col-md-5 col-sm-12 text-md-center my-2 my-md-0"B><"col-md-4 col-sm-6 text-md-end"f>>' +
        't' +
        '<"row mt-3 align-items-center g-2"<"col-md-6 col-sm-12 text-muted small"i><"col-md-6 col-sm-12 d-flex justify-content-md-end"p>>'
      : '<"row mb-3 align-items-center g-2"<"col-md-6 col-sm-6"l><"col-md-6 col-sm-6 text-md-end"f>>' +
        't' +
        '<"row mt-3 align-items-center g-2"<"col-md-6 col-sm-12 text-muted small"i><"col-md-6 col-sm-12 d-flex justify-content-md-end"p>>';

    var defaultDomWithoutFilter = exportButtons.length
      ? '<"row mb-3 align-items-center g-2"<"col-md-4 col-sm-6"l><"col-md-8 col-sm-6 text-md-end"B>>' +
        't' +
        '<"row mt-3 align-items-center g-2"<"col-md-6 col-sm-12 text-muted small"i><"col-md-6 col-sm-12 d-flex justify-content-md-end"p>>'
      : '<"row mb-3 align-items-center g-2"<"col-md-6 col-sm-6"l><"col-md-6 col-sm-6 text-md-end">> ' +
        't' +
        '<"row mt-3 align-items-center g-2"<"col-md-6 col-sm-12 text-muted small"i><"col-md-6 col-sm-12 d-flex justify-content-md-end"p>>';

    var calculatedDom = userOptions.dom || (externalSearchSelector ? defaultDomWithoutFilter : defaultDomWithFilter);

    // Placeholder contextual
    var searchPlaceholder = userOptions.searchPlaceholder || SBM_MODULE_PLACEHOLDERS[moduloName] || 'Filtrar registros en esta tabla…';

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
      language: $.extend(true, {}, SBM_DATATABLES_SPANISH, {
        searchPlaceholder: searchPlaceholder
      }),
      dom: calculatedDom,
      buttons: exportButtons,
      pageLength: userOptions.pageLength || 10,
      lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'Todos']],
      order: userOptions.order || [],
      autoWidth: false,
      initComplete: function (settings, json) {
        var api = this.api();
        var container = api.table().container();

        // Si la tabla usa buscador externo, enlazarlo
        if (externalSearchSelector) {
          window.createSBMTableSearch(api, {
            externalInput: externalSearchSelector,
            placeholder: searchPlaceholder
          });
        } else {
          // Si no tiene buscador externo, reemplazar el contenedor .dataTables_filter con el componente SBM
          var $filter = $(container).find('.dataTables_filter');
          if ($filter.length) {
            window.createSBMTableSearch(api, {
              container: $filter,
              placeholder: searchPlaceholder
            });
          }
        }

        if (typeof userOptions.initComplete === 'function') {
          userOptions.initComplete.call(this, settings, json);
        }
      },
      drawCallback: function (settings) {
        var api = this.api();
        var $emptyCell = $table.find('.dataTables_empty');

        // Estado temático cuando 0 registros coinciden con la búsqueda
        if (settings.aiDisplay && settings.aiDisplay.length === 0) {
          var rawQuery = settings._sbmSearchRaw || '';
          if (rawQuery) {
            $emptyCell.html(
              '<div class="sbm-empty-search">' +
                '<div class="sbm-empty-search-icon"><i class="bi bi-search"></i></div>' +
                '<div class="sbm-empty-search-title">Sin resultados para "' + $('<div>').text(rawQuery).html() + '"</div>' +
                '<div class="sbm-empty-search-desc">No se encontraron registros que coincidan con la búsqueda. Intenta con otro término o limpia el filtro.</div>' +
              '</div>'
            );
          } else if (emptyStateHtml) {
            $emptyCell.html(emptyStateHtml);
          }
        }

        // Inicializar tooltips de Bootstrap en controles dinámicos
        var container = api.table().container();
        if (container && typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
          var tooltips = container.querySelectorAll('[data-bs-toggle="tooltip"]');
          tooltips.forEach(function (el) {
            bootstrap.Tooltip.getOrCreateInstance(el);
          });
        }

        if (typeof userOptions.drawCallback === 'function') {
          userOptions.drawCallback.call(this, settings);
        }
      }
    }, userOptions);

    // Inicializar DataTable
    var dtInstance = $table.DataTable(finalConfig);

    // Permitir clic accesible con teclado en la primera columna para expandir en móvil
    $table.on('keydown', 'td.dtr-control', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        $(this).trigger('click');
      }
    });

    return dtInstance;
  };

  // Exponer utilidades
  window.sbmNormalize = sbmNormalize;
  window.SBM_MODULE_PLACEHOLDERS = SBM_MODULE_PLACEHOLDERS;
  window.SBM_DATATABLES_SPANISH = SBM_DATATABLES_SPANISH;

})(window, jQuery);
