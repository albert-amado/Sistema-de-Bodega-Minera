/**
 * static/js/sbm-actions.js
 * =============================================================================
 * Componente Reutilizable de Acciones y Modal Unificado de Detalles (SBM)
 * =============================================================================
 */

(function (window, $) {
  'use strict';

  /**
   * Abre el modal global de detalles con datos estructurados.
   * @param {Object} config
   *   - title: string
   *   - subtitle: string
   *   - badge: string
   *   - icon: string (clase bi, ej. 'bi-tools')
   *   - fields: Array<{ label: string, value: string|number, col?: number, isBadge?: boolean, badgeClass?: string }>
   *   - extraHtml: string (HTML opcional para tablas internas de herramientas, observaciones, etc.)
   */
  window.mostrarModalDetalles = function (config) {
    config = config || {};
    var $modal = $('#modalSBMDetalle');
    if (!$modal.length) {
      console.warn('El modal #modalSBMDetalle no se encuentra en el DOM.');
      return;
    }

    // Título y encabezado
    $('#modalSBMDetalleLabel').text(config.title || 'Detalles del Registro');
    $('#sbmDetalleSubtitulo').text(config.subtitle || 'Sistema de Bodega Minera');
    if (config.badge) {
      $('#sbmDetalleBadge').text(config.badge);
    }
    if (config.icon) {
      $('#sbmDetalleAvatar').html('<i class="bi ' + config.icon + '"></i>');
    } else {
      $('#sbmDetalleAvatar').html('<i class="bi bi-info-circle-fill"></i>');
    }

    // Grid de campos
    var $grid = $('#sbmDetalleGrid').empty();
    var fields = config.fields || [];

    var copyBuffer = [];
    copyBuffer.push((config.title || 'DETALLE') + ' - ' + (config.subtitle || ''));

    $.each(fields, function (idx, f) {
      if (!f || f.value === undefined || f.value === null) return;
      var colSize = f.col || 6;
      var $col = $('<div class="col-12 col-md-' + colSize + '"></div>');
      var $card = $('<div class="p-3 bg-white rounded-3 border h-100 shadow-xs"></div>');
      
      var $lbl = $('<div class="text-secondary small fw-bold text-uppercase mb-1" style="font-size:0.72rem; letter-spacing:0.03em;"></div>').html(f.label);
      var $val = $('<div class="text-dark fw-semibold small"></div>');

      if (f.isBadge) {
        $val.html('<span class="badge ' + (f.badgeClass || 'bg-light text-dark border') + '">' + f.value + '</span>');
      } else {
        $val.html(f.value || '<span class="text-muted fst-italic">—</span>');
      }

      $card.append($lbl).append($val);
      $col.append($card);
      $grid.append($col);

      copyBuffer.push(f.label.replace(/<[^>]*>?/gm, '') + ': ' + String(f.value).replace(/<[^>]*>?/gm, ''));
    });

    // Contenido adicional
    var $extra = $('#sbmDetalleExtra');
    if (config.extraHtml) {
      $extra.html(config.extraHtml).removeClass('d-none');
    } else {
      $extra.empty().addClass('d-none');
    }

    // Vincular botón de copiado
    $('#btnCopiarDetallesModal').off('click').on('click', function () {
      var fullText = copyBuffer.join('\n');
      if (navigator.clipboard) {
        navigator.clipboard.writeText(fullText).then(function () {
          var orig = $('#btnCopiarDetallesModal').html();
          $('#btnCopiarDetallesModal').html('<i class="bi bi-check2"></i> ¡Copiado!').addClass('btn-success').removeClass('btn-outline-secondary');
          setTimeout(function () {
            $('#btnCopiarDetallesModal').html(orig).removeClass('btn-success').addClass('btn-outline-secondary');
          }, 2000);
        });
      }
    });

    // Abrir modal con Bootstrap
    var modalInst = bootstrap.Modal.getOrCreateInstance($modal[0]);
    modalInst.show();
  };

  // Delegación global para botones con data-sbm-details
  $(document).on('click', '[data-sbm-details]', function (e) {
    e.preventDefault();
    try {
      var raw = $(this).attr('data-sbm-details');
      var data = JSON.parse(raw);
      window.mostrarModalDetalles(data);
    } catch (err) {
      console.error('Error al analizar data-sbm-details:', err);
    }
  });

})(window, jQuery);
