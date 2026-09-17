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

    var table = window.initSBMDataTable('#reportes-table', {
        modulo: 'reportes',
        searchPlaceholder: 'Buscar en reporte por producto, cliente, fecha…',
        pageLength: 10
    });

    // Limpiar campos de fecha y actualizar tabla en el cliente
    $('.cys-clear-dates-btn').on('click', function(e) {
        e.preventDefault();
        $('#filtro-fecha-inicio').val('');
        $('#filtro-fecha-fin').val('');
        table.draw();
    });
});
