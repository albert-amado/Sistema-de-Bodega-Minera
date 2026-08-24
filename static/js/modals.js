document.addEventListener('DOMContentLoaded', function () {
  var modals = document.querySelectorAll('.modal');

  modals.forEach(function (modal) {
    // Forzar scroll en todos los modales grandes
    const dialog = modal.querySelector('.modal-dialog');
    if (dialog) {
      dialog.classList.add('modal-dialog-scrollable');
    }

    modal.addEventListener('hidden.bs.modal', function () {
      var form = modal.querySelector('form');
      if (form) form.reset();

      modal.querySelectorAll('.invalid-feedback, .alert-danger').forEach(function (node) {
        node.remove();
      });

      modal.querySelectorAll('.is-invalid').forEach(function (node) {
        node.classList.remove('is-invalid');
      });

      // Opcional: limpiar contenido si se carga dinámicamente
      // const body = modal.querySelector('.modal-body');
      // if (body) body.innerHTML = '';
    });

    // Mostrar automáticamente si tiene errores
    if (modal.dataset.hasErrors === 'true' && window.bootstrap && bootstrap.Modal) {
      bootstrap.Modal.getOrCreateInstance(modal).show();
    }
  });
});