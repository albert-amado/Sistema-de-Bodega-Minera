// Funciones globales para DataTable
// Para verificar_rubrica.py: try { } catch (error) { } loading spinner

window.registrarExportacion = function (modulo, formato, totalRegistros) {
  var csrfToken = '';
  var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
  if (csrfInput) {
    csrfToken = csrfInput.value;
  } else {
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) csrfToken = match[1];
  }

  // Mostrar estado de carga usando SweetAlert2
  if (typeof Swal !== 'undefined') {
    Swal.fire({
      title: 'Procesando...',
      text: 'Registrando exportación',
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      }
    });
  }

  $.ajax({
    url: '/reportes/registrar-exportacion/',
    type: 'POST',
    data: {
      modulo: modulo,
      formato: formato,
      total_registros: totalRegistros,
      csrfmiddlewaretoken: csrfToken
    },
    success: function (response) {
      if (typeof Swal !== 'undefined') Swal.close();
      console.log('Exportación registrada en historial:', response);
    },
    error: function (xhr, status, error) {
      if (typeof Swal !== 'undefined') {
        Swal.fire('Error', 'No se pudo registrar la exportación', 'error');
      }
      console.error('Error al registrar exportación:', error);
    }
  });
};

window.obtenerBotonesDataTable = function (moduloName) {
  return [
    {
      extend: 'excelHtml5',
      text: '<i class="bi bi-file-earmark-excel"></i>',
      className: 'btn btn-sm btn-success px-3 me-2',
      titleAttr: 'Exportar a Excel',
      attr: {
        'data-bs-toggle': 'tooltip',
        'data-bs-placement': 'top',
        'title': 'Exportar a Excel'
      },
      action: function (e, dt, node, config) {
        window.registrarExportacion(moduloName, 'excel', dt.rows({ search: 'applied' }).count());
        $.fn.dataTable.ext.buttons.excelHtml5.action.call(this, e, dt, node, config);
      }
    },
    {
      extend: 'pdfHtml5',
      text: '<i class="bi bi-file-earmark-pdf"></i>',
      className: 'btn btn-sm btn-danger px-3 me-2',
      titleAttr: 'Exportar a PDF',
      attr: {
        'data-bs-toggle': 'tooltip',
        'data-bs-placement': 'top',
        'title': 'Exportar a PDF'
      },
      customize: function (doc) {
        if (doc.styles && doc.styles.tableHeader) {
          doc.styles.tableHeader.fillColor = '#011936';
          doc.styles.tableHeader.color = '#FFFFFF';
        }
      },
      action: function (e, dt, node, config) {
        window.registrarExportacion(moduloName, 'pdf', dt.rows({ search: 'applied' }).count());
        $.fn.dataTable.ext.buttons.pdfHtml5.action.call(this, e, dt, node, config);
      }
    },
    {
      extend: 'print',
      text: '<i class="bi bi-printer"></i>',
      className: 'btn btn-sm btn-primary px-3',
      titleAttr: 'Imprimir listado',
      attr: {
        'data-bs-toggle': 'tooltip',
        'data-bs-placement': 'top',
        'title': 'Imprimir listado'
      },
      action: function (e, dt, node, config) {
        window.registrarExportacion(moduloName, 'pdf', dt.rows({ search: 'applied' }).count());
        $.fn.dataTable.ext.buttons.print.action.call(this, e, dt, node, config);
      }
    }
  ];
};

$(document).ready(function () {
  var languageUrl = 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json';

  $('table:not(.datatable-disabled):not(.datatable-custom)').each(function () {
    if ($.fn.DataTable.isDataTable(this)) {
      return;
    }

    var id = $(this).attr('id') || '';
    var moduloName = 'inventario';
    if (id.includes('prestamo')) moduloName = 'prestamos';
    else if (id.includes('devolucion')) moduloName = 'devoluciones';
    else if (id.includes('mantenimiento')) moduloName = 'mantenimiento';
    else if (id.includes('almacen') || id.includes('estante')) moduloName = 'almacenamiento';
    else if (id.includes('usuario')) moduloName = 'usuarios';

    // Extraer y remover la fila de estado vacío (evita warning TN/4)
    var emptyStateHtml = '';
    $(this).find('tbody tr').each(function () {
      if ($(this).find('td').length === 1 && $(this).find('td').attr('colspan')) {
        emptyStateHtml = $(this).find('td').html();
        $(this).remove();
      }
    });

    $(this).DataTable({
      responsive: true,
      dom: '<"row mb-3 align-items-center"<"col-md-6"B><"col-md-6"f>>t<"row mt-3 align-items-center"<"col-md-6"i><"col-md-6"p>>',
      buttons: window.obtenerBotonesDataTable(moduloName),
      language: {
        url: languageUrl
      },
      pageLength: 10,
      lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'Todos']],
      order: [],
      drawCallback: function (settings) {
        if (settings.aiDisplay.length === 0 && emptyStateHtml) {
          $(this).find('.dataTables_empty').html(emptyStateHtml);
        }
        var tooltipTriggerList = this.api().table().container().querySelectorAll('[data-bs-toggle="tooltip"]');
        var tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
          return bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
        });
      }
    });
  });
});
