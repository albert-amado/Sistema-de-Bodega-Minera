// Custom search filter for Category in DataTables (only for inventario-table)
$.fn.dataTable.ext.search.push(
    function(settings, data, dataIndex) {
        if (settings.nTable.id !== 'inventario-table') {
            return true;
        }
        var selectedCat = $('#inventario-categoria').val();
        if (!selectedCat) {
            return true;
        }
        var row = settings.aoData[dataIndex].nTr;
        var rowCatId = $(row).find('td.col-categoria').data('categoria-id');
        return String(rowCatId) === String(selectedCat);
    }
);

$(document).ready(function() {
    // Extraer y remover la fila de estado vacío (evita warning TN/4)
    var emptyStateHtml = '';
    $('#inventario-table tbody tr').each(function () {
      if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
        emptyStateHtml = $(this).find('td').html();
        $(this).remove();
      }
    });

    var table = window.initSBMDataTable('#inventario-table', {
        modulo: 'inventario',
        order: [[1, 'asc']], // Ordenar por nombre de herramienta por defecto
        columnDefs: [
            { orderable: false, targets: [4, 6] } // Ubicación (4) y Acciones (6) no ordenables
        ],
        pageLength: 10
    });

    // Inicializar tabla de Kardex dentro del modal si existe
    if ($('#modalKardexHistorial table').length) {
        window.initSBMDataTable('#modalKardexHistorial table', {
            modulo: 'inventario',
            order: [[0, 'desc']],
            pageLength: 10
        });
    }

    // Filtro de categoría
    $('#inventario-categoria').on('change', function() {
        table.draw();
    });

    // Limpiar todos los filtros (búsqueda y categoría)
    $('#btn-limpiar-filtros').on('click', function(e) {
        e.preventDefault();
        $('#inventario-busqueda').val('');
        $('#inventario-busqueda').closest('.sfb-search-group').find('.sbm-search-clear').addClass('d-none');
        $('#inventario-categoria').val('');
        if (table) {
            var settings = table.settings()[0];
            if (settings) {
                settings._sbmSearchQuery = '';
                settings._sbmSearchTokens = [];
                settings._sbmSearchRaw = '';
            }
            table.search('').page('first').draw();
        }
    });

    // Aplicar filtro inicial de categoría si vino por GET
    var initialCat = $('#inventario-categoria').val();
    if (initialCat) {
        table.draw();
    }

    // Delegated click handler for "Ver ubicación" modal populating and opening
    $(document).on('click', '.btn-ver-ubicacion', function(e) {
        e.preventDefault();
        var btn = $(this);
        $('#ubi_producto_nombre').text(btn.data('producto-nombre'));
        $('#ubi_almacen_nombre').text(btn.data('almacen-nombre'));
        $('#ubi_almacen_pk').text('#' + btn.data('almacen-pk'));
        $('#ubi_estante_codigo').text(btn.data('estante-codigo'));
        var modal = new bootstrap.Modal(document.getElementById('modalUbicacion'));
        modal.show();
    });

    // Initialize all tooltips on the page
    var tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"], .has-tooltip');
    var tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
        return bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
    });

    // Hide tooltip when a button is clicked (to avoid lingering tooltips)
    $(document).on('click', '[data-bs-toggle="tooltip"], .has-tooltip', function() {
        var tooltip = bootstrap.Tooltip.getInstance(this);
        if (tooltip) {
            tooltip.hide();
        }
    });
});
