/**
 * mantenimiento.js
 * Validaciones frontend para el formulario de mantenimiento
 */

document.addEventListener('DOMContentLoaded', function () {

    //Campos obligatorios y sus mensajes
    const CAMPOS_OBLIGATORIOS = {
        'id_producto':           'El ítem/herramienta es obligatorio',
        'id_tipo_mantenimiento': 'El tipo de mantenimiento es obligatorio',
        'id_tipo_estado':        'El tipo de estado es obligatorio',
        'id_fecha_reporte':      'La fecha de reporte es obligatoria',
        'id_fecha_inicio':       'La fecha de inicio es obligatoria',
        'id_descripcion_problema': 'La descripción del problema es obligatoria',
        'id_responsable':        'El técnico responsable es obligatorio',
        'id_estado_registro':    'El estado del registro es obligatorio',
        'id_prioridad':          'La prioridad es obligatoria',
    };

    const MENSAJES = {
        'producto_busqueda':     { required: 'Busca y selecciona un ítem o herramienta' },
        'tipo_mantenimiento':    { required: 'Selecciona un tipo de mantenimiento' },
        'tipo_estado':           { required: 'Selecciona el estado del equipo' },
        'fecha_reporte':         { required: 'Ingresa la fecha en que se detectó el problema' },
        'fecha_inicio':          { required: 'Ingresa la fecha de inicio', invalid: 'No puede ser anterior a la fecha de reporte' },
        'fecha_fin_estimada':    { invalid: 'No puede ser anterior a la fecha de inicio' },
        'fecha_fin_real':        { invalid: 'No puede ser anterior a la fecha de inicio' },
        'descripcion_problema':  { required: 'Describe el problema (mínimo 10 caracteres)', minLength: 'Mínimo 10 caracteres' },
        'responsable':           { required: 'Asigna un técnico responsable' },
        'estado_registro':       { required: 'Selecciona el estado del registro' },
        'prioridad':             { required: 'Selecciona la prioridad' },
        'tiempo_empleado_horas': { negative: 'No puede ser negativo' },
        'costo_estimado':        { negative: 'No puede ser negativo' },
        'costo_real':            { negative: 'No puede ser negativo' },
    };

    const CAMPOS_OPCIONALES = [
        'id_fecha_fin_estimada', 'id_fecha_fin_real',
        'id_tiempo_empleado_horas', 'id_costo_estimado', 'id_costo_real',
        'id_acciones_realizadas', 'id_materiales_usados', 'id_notas_adicionales',
    ];

    const CAMPOS_TEXTO = [
        'id_descripcion_problema', 'id_acciones_realizadas',
        'id_materiales_usados', 'id_notas_adicionales',
    ];

    const CAMPOS_NUMERICOS = [
        'id_tiempo_empleado_horas', 'id_costo_estimado', 'id_costo_real',
    ];

    // ── Referencias al DOM ────────────────────────────────────────────────────
    const form       = document.getElementById('mantenimientoEditForm') || document.querySelector('form[method="post"]');
    const submitBtn  = form?.querySelector('button[type="submit"]');
    const productoInput  = document.getElementById('id_producto_busqueda');
    const productoHidden = document.getElementById('id_producto');

    if (!form) return;

    // ── Manejo de errores por campo ───────────────────────────────────────────

    // Obtiene o crea el div de error debajo de un campo
    function getErrorContainer(fieldId) {
        let container = document.getElementById(`error-${fieldId}`);
        if (!container) {
            const field = document.getElementById(fieldId);
            if (!field) return null;
            container = document.createElement('div');
            container.id = `error-${fieldId}`;
            container.className = 'invalid-feedback d-block mt-1';
            container.style.display = 'none';
            field.parentNode.appendChild(container);
        }
        return container;
    }

    // Marca el campo como válido o inválido visualmente
    function setFieldValid(fieldId, isValid) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        const container = getErrorContainer(fieldId);
        if (isValid) {
            field.classList.replace('is-invalid', 'is-valid') || field.classList.add('is-valid');
            if (container) { container.style.display = 'none'; container.textContent = ''; }
        } else {
            field.classList.replace('is-valid', 'is-invalid') || field.classList.add('is-invalid');
        }
    }

    // Muestra un mensaje de error en el campo
    function showFieldError(fieldId, message) {
        const container = getErrorContainer(fieldId);
        if (container) { container.textContent = message; container.style.display = 'block'; }
        setFieldValid(fieldId, false);
    }

    // Limpia el error de un campo
    function clearFieldError(fieldId) {
        const container = getErrorContainer(fieldId);
        if (container) { container.textContent = ''; container.style.display = 'none'; }
        setFieldValid(fieldId, true);
    }

    // ── Validación por campo ──────────────────────────────────────────────────

    function validateField(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return true;

        const value    = field.value?.trim() || '';
        const nombre   = fieldId.replace('id_', '');
        const mensajes = MENSAJES[nombre] || {};

        // Obligatorio vacío
        if (CAMPOS_OBLIGATORIOS[fieldId] && !value) {
            showFieldError(fieldId, mensajes.required || CAMPOS_OBLIGATORIOS[fieldId]);
            return false;
        }

        // Descripción mínimo 10 caracteres
        if (fieldId === 'id_descripcion_problema' && value.length < 10) {
            showFieldError(fieldId, mensajes.minLength || 'Mínimo 10 caracteres');
            return false;
        }

        // Fecha inicio no puede ser anterior a fecha reporte
        if (fieldId === 'id_fecha_inicio' && value) {
            const fechaReporte = document.getElementById('id_fecha_reporte')?.value;
            if (fechaReporte && new Date(value) < new Date(fechaReporte)) {
                showFieldError(fieldId, mensajes.invalid);
                return false;
            }
        }

        // Fechas fin no pueden ser anteriores a fecha inicio
        if (['id_fecha_fin_estimada', 'id_fecha_fin_real'].includes(fieldId) && value) {
            const fechaInicio = document.getElementById('id_fecha_inicio')?.value;
            if (fechaInicio && new Date(value) < new Date(fechaInicio)) {
                showFieldError(fieldId, mensajes.invalid);
                return false;
            }
        }

        // Campos numéricos no pueden ser negativos
        if (CAMPOS_NUMERICOS.includes(fieldId) && value && parseFloat(value) < 0) {
            showFieldError(fieldId, mensajes.negative || 'No puede ser negativo');
            return false;
        }

        clearFieldError(fieldId);
        return true;
    }

    // Valida todo el formulario y hace scroll al primer error
    function validateForm() {
        const errors = [];
        let primerCampoConError = null;

        [...Object.keys(CAMPOS_OBLIGATORIOS), ...CAMPOS_OPCIONALES].forEach(fieldId => {
            const field = document.getElementById(fieldId);
            const tieneValor = field?.value?.trim();
            const esObligatorio = !!CAMPOS_OBLIGATORIOS[fieldId];

            if (esObligatorio || tieneValor) {
                const isValid = validateField(fieldId);
                if (!isValid) {
                    errors.push(fieldId);
                    if (!primerCampoConError) primerCampoConError = field;
                }
            }
        });

        if (primerCampoConError) {
            setTimeout(() => {
                primerCampoConError.focus();
                primerCampoConError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
        }

        return errors.length === 0;
    }

    // Habilita o deshabilita el botón submit según errores actuales
    function updateSubmitButton() {
        if (!submitBtn) return;
        const hayErrores = document.querySelectorAll('.is-invalid').length > 0;
        submitBtn.disabled = hayErrores;
        submitBtn.classList.toggle('disabled', hayErrores);
    }

    // ── Eventos de validación en tiempo real ──────────────────────────────────

    // Campos obligatorios: validar al salir, al cambiar y al escribir si ya hay error
    Object.keys(CAMPOS_OBLIGATORIOS).forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.addEventListener('blur',   () => { validateField(fieldId); updateSubmitButton(); });
        field.addEventListener('change', () => { validateField(fieldId); updateSubmitButton(); });
        field.addEventListener('input',  () => { if (field.classList.contains('is-invalid')) { validateField(fieldId); updateSubmitButton(); } });
    });

    // Campos de texto: revalidar al escribir si ya tienen error
    CAMPOS_TEXTO.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.addEventListener('input', () => { if (field.classList.contains('is-invalid')) { validateField(fieldId); updateSubmitButton(); } });
    });

    // Envío del formulario
    form.addEventListener('submit', function (e) {
        if (!validateForm()) {
            e.preventDefault();
            showToastError('Por favor completa todos los campos obligatorios correctamente.');
            return;
        }

        // Muestra spinner mientras se envía
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
        }
    });

    // ── Autocompletado de producto ────────────────────────────────────────────

    if (productoInput && productoHidden) {
        let productosDisponibles = [];

        // Carga los productos desde la API
        async function loadProductos() {
            try {
                const res = await fetch('/api/productos/');
                if (res.ok) productosDisponibles = await res.json();
            } catch (e) {
                console.error('Error cargando productos:', e);
            }
        }
        loadProductos();

        // Crea la lista de sugerencias debajo del input
        const suggestionList = document.createElement('ul');
        suggestionList.id = 'producto-suggestions';
        suggestionList.className = 'list-group position-absolute w-100';
        Object.assign(suggestionList.style, { display: 'none', zIndex: '1000', maxHeight: '300px', overflowY: 'auto' });
        productoInput.parentNode.style.position = 'relative';
        productoInput.parentNode.appendChild(suggestionList);

        // Filtra y muestra sugerencias al escribir
        productoInput.addEventListener('input', function () {
            const query = this.value?.trim().toLowerCase() || '';
            suggestionList.innerHTML = '';

            if (query.length < 2) {
                suggestionList.style.display = 'none';
                productoHidden.value = '';
                return;
            }

            const filtrados = productosDisponibles.filter(p =>
                p.codigo_sku.toLowerCase().includes(query) ||
                p.nombre.toLowerCase().includes(query) ||
                p.numero_serie?.toLowerCase().includes(query)
            ).slice(0, 10);

            if (!filtrados.length) {
                const item = document.createElement('li');
                item.className = 'list-group-item text-muted';
                item.textContent = 'No se encontraron resultados';
                suggestionList.appendChild(item);
            } else {
                filtrados.forEach(producto => {
                    const item = document.createElement('li');
                    item.className = 'list-group-item';
                    item.style.cursor = 'pointer';
                    item.innerHTML = `<strong>[${producto.codigo_sku}]</strong> ${producto.nombre}<br>
                                      <small class="text-muted">Serie: ${producto.numero_serie || 'N/A'}</small>`;
                    item.addEventListener('click', () => {
                        productoInput.value  = `[${producto.codigo_sku}] ${producto.nombre}`;
                        productoHidden.value = producto.id;
                        suggestionList.style.display = 'none';
                        clearFieldError('id_producto');
                        validateField('id_producto');
                        updateSubmitButton();
                    });
                    suggestionList.appendChild(item);
                });
            }

            suggestionList.style.display = 'block';
        });

        // Oculta sugerencias al hacer click fuera
        document.addEventListener('click', e => {
            if (e.target !== productoInput) suggestionList.style.display = 'none';
        });
    }

    // ── Toast de error ────────────────────────────────────────────────────────

    // Muestra una notificación temporal en la esquina inferior derecha
    function showToastError(message) {
        showToast(message, 'bg-danger text-white', 'Error de validación');
    }

    function showToast(message, headerClass, title) {
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed bottom-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="toast-header ${headerClass}">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;
        document.body.appendChild(toast);
        new bootstrap.Toast(toast).show();
        setTimeout(() => toast.remove(), 5000);
    }

    function renderQueuedMessages() {
        const messageHost = document.getElementById('mantenimiento-messages');
        if (!messageHost) return;

        messageHost.querySelectorAll('[data-message]').forEach(function (node) {
            const message = node.dataset.message || '';
            const tag = (node.dataset.tag || 'info').trim() || 'info';
            const headerClass = tag === 'error' ? 'bg-danger text-white' : `bg-${tag} text-white`;
            showToast(message, headerClass, 'Notificación');
        });
        messageHost.remove();
    }

    // Estado inicial del botón
    updateSubmitButton();
    renderQueuedMessages();
});