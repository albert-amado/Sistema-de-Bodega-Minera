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

    var table = $('#inventario-table').DataTable({
        responsive: true,
        dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6">>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
        buttons: window.obtenerBotonesDataTable('inventario'),
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
        },
        order: [[1, 'asc']], // Order by tool name (column index 1) ascending by default
        columnDefs: [
            { orderable: false, targets: [4, 6] } // Ubicación (4) and Acciones (6) are not sortable
        ],
        pageLength: 10,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Todos"]],
        drawCallback: function(settings) {
            if (settings.aiDisplay.length === 0 && emptyStateHtml) {
                $(this).find('.dataTables_empty').html(emptyStateHtml);
            }
            // Re-initialize Bootstrap tooltips for elements inside the table after redrawing
            var tooltipTriggerList = document.querySelectorAll('#inventario-table [data-bs-toggle="tooltip"]');
            var tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
                return bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
            });
        }
    });

    // Real-time search filter
    $('#inventario-busqueda').on('keyup input', function() {
        table.search(this.value).draw();
    });

    // Category filter
    $('#inventario-categoria').on('change', function() {
        table.draw();
    });

    // Clear filters
    $('#btn-limpiar-filtros').on('click', function(e) {
        e.preventDefault();
        $('#inventario-busqueda').val('');
        $('#inventario-categoria').val('');
        table.search('').draw();
        table.draw();
    });

    // Apply initial filters if values exist (e.g. pre-populated from GET params)
    var initialSearch = $('#inventario-busqueda').val();
    if (initialSearch) {
        table.search(initialSearch).draw();
    }
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
