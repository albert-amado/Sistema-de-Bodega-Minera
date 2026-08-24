// Función de búsqueda personalizada para rango de fechas en DataTables
$.fn.dataTable.ext.search.push(
    function(settings, data, dataIndex) {
        var minVal = $('#filtro-fecha-inicio').val();
        var maxVal = $('#filtro-fecha-fin').val();
        
        // La columna de fecha es la 6 (0-indexed: #, Cliente, Producto, Cantidad, Precio Unit, Total, Fecha)
        var dateVal = data[6] || ""; 
        
        if (minVal === "" && maxVal === "") {
            return true;
        }
        if (minVal !== "" && dateVal < minVal) {
            return false;
        }
        if (maxVal !== "" && dateVal > maxVal) {
            return false;
        }
        return true;
    }
);

$(document).ready(function() {
    // Extraer y remover la fila de estado vacío (evita warning TN/4)
    var emptyStateHtml = '';
    $('#reportes-table tbody tr').each(function () {
      if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
        emptyStateHtml = $(this).find('td').html();
        $(this).remove();
      }
    });

    var table = $('#reportes-table').DataTable({
        responsive: true,
        dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6"f>>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
        buttons: [
            {
                extend: 'excelHtml5',
                text: '<i class="bi bi-file-earmark-excel me-1"></i> Excel',
                className: 'btn btn-sm btn-success px-3 me-2',
                title: 'Reporte de Ventas - CYS Ltda'
            },
            {
                extend: 'pdfHtml5',
                text: '<i class="bi bi-file-earmark-pdf me-1"></i> PDF',
                className: 'btn btn-sm btn-danger px-3 me-2',
                title: 'Reporte de Ventas - CYS Ltda',
                customize: function (doc) {
                    // Personalización del PDF generado
                    if (doc.styles && doc.styles.tableHeader) {
                        doc.styles.tableHeader.fillColor = '#011936';
                        doc.styles.tableHeader.color = '#FFFFFF';
                    }
                }
            },
            {
                extend: 'print',
                text: '<i class="bi bi-printer me-1"></i> Imprimir',
                className: 'btn btn-sm btn-primary px-3',
                title: 'Reporte de Ventas - CYS Ltda'
            }
        ],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
        },
        order: [[6, 'desc']], // Ordenar por Fecha (columna 6) descendente
        pageLength: 10,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Todos"]],
        drawCallback: function (settings) {
            if (settings.aiDisplay.length === 0 && emptyStateHtml) {
                $(this).find('.dataTables_empty').html(emptyStateHtml);
            }
        }
    });

    // Escuchar los cambios en los inputs de fechas para redibujar la tabla instantáneamente
    $('#filtro-fecha-inicio, #filtro-fecha-fin').on('change', function() {
        table.draw();
    });

    // Limpiar campos de fecha y actualizar tabla en el cliente
    $('.cys-clear-dates-btn').on('click', function(e) {
        e.preventDefault();
        $('#filtro-fecha-inicio').val('');
        $('#filtro-fecha-fin').val('');
        table.draw();
    });
});
