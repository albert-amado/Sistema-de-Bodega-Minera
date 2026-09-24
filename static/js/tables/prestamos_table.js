// Custom search filter for Estado in DataTables (only for prestamo-table)
$.fn.dataTable.ext.search.push(
    function(settings, data, dataIndex) {
        if (settings.nTable.id !== 'prestamo-table') {
            return true;
        }
        var selectedEstado = $('#prestamo-estado').val();
        if (!selectedEstado) {
            return true;
        }
        var row = settings.aoData[dataIndex].nTr;
        var rowEstado = $(row).find('td.col-estado').data('estado');
        return String(rowEstado).toUpperCase() === String(selectedEstado).toUpperCase();
    }
);

$(document).ready(function() {
    // Extraer y remover la fila de estado vacío (evita warning TN/4)
    var emptyStateHtml = '';
    $('#prestamo-table tbody tr').each(function () {
      if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
        emptyStateHtml = $(this).find('td').html();
        $(this).remove();
      }
    });

    var table = window.initSBMDataTable('#prestamo-table', {
        modulo: 'prestamos',
        dom: '<"row mb-3 align-items-center g-2"<"col-sm-6"l><"col-sm-6 text-sm-end"B>>t<"row mt-3 align-items-center g-2"<"col-md-6 col-sm-12 text-muted small"i><"col-md-6 col-sm-12 d-flex justify-content-md-end"p>>',
        order: [[0, 'desc']], // Ordenar por # ID descendente: desde el último préstamo realizado al primero
        columnDefs: [
            { orderable: false, targets: [1, 6] } // Herramientas (1) y Acciones (6) no ordenables
        ],
        pageLength: 10
    });

    // Filtro por Estado
    $('#prestamo-estado').on('change', function() {
        table.draw();
    });

    // Limpiar todos los filtros
    $('#btn-limpiar-filtros').on('click', function(e) {
        e.preventDefault();
        $('#prestamo-busqueda').val('');
        $('#prestamo-busqueda').closest('.sfb-search-group').find('.sbm-search-clear').addClass('d-none');
        $('#prestamo-estado').val('');
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

    // Aplicar filtro inicial de estado si vino por GET
    var initialEstado = $('#prestamo-estado').val();
    if (initialEstado) {
        table.draw();
    }

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
