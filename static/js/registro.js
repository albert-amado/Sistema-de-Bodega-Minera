 // ── Reglas por tipo de documento ─────────────────────────────────────────
  // min/max: longitud permitida
  // onlyDigits: si true, solo acepta números al teclear
  // pattern: regex final de validación
  // hint: texto de ayuda visible bajo el input
  const DOC_RULES = {
    CC: { min: 6,  max: 10, onlyDigits: true,  pattern: /^\d{6,10}$/,          hint: 'Solo dígitos · 6 a 10 caracteres' },
    CE: { min: 6,  max: 12, onlyDigits: false, pattern: /^[A-Za-z0-9]{6,12}$/, hint: 'Letras y dígitos · 6 a 12 caracteres' },
    PP: { min: 5,  max: 9,  onlyDigits: false, pattern: /^[A-Za-z0-9]{5,9}$/,  hint: 'Letras y dígitos · 5 a 9 caracteres' },
    TI: { min: 10, max: 11, onlyDigits: true,  pattern: /^\d{10,11}$/,          hint: 'Solo dígitos · 10 u 11 caracteres' },
  };

  const tipoSel  = document.getElementById('tipo_documento');
  const docInput = document.getElementById('documento');
  const hint     = document.getElementById('doc-hint');

  function applyRules() {
    const rules = DOC_RULES[tipoSel.value];
    if (!rules) return;
    docInput.minLength = rules.min;
    docInput.maxLength = rules.max;
    docInput.placeholder = `Mín. ${rules.min} – Máx. ${rules.max} car.`;
    hint.className = 'text-muted';
    hint.textContent = rules.hint;
    validateDoc();
  }

  function validateDoc() {
    const rules = DOC_RULES[tipoSel.value];
    if (!rules || docInput.value === '') {
      docInput.classList.remove('is-valid', 'is-invalid');
      hint.className = 'text-muted';
      hint.textContent = rules?.hint ?? '';
      return;
    }
    const ok = rules.pattern.test(docInput.value);
    docInput.classList.toggle('is-valid',   ok);
    docInput.classList.toggle('is-invalid', !ok);
    hint.className   = ok ? 'text-success fw-semibold' : 'text-danger fw-semibold';
    hint.textContent = ok ? '✓ Formato correcto' : `✗ ${rules.hint}`;
  }

  // Bloquear teclas no permitidas en tiempo real
  docInput.addEventListener('keypress', (e) => {
    const rules = DOC_RULES[tipoSel.value];
    if (rules?.onlyDigits && !/\d/.test(e.key)) {
      e.preventDefault();
    }
  });

  // Al pegar, limpiar caracteres no permitidos
  docInput.addEventListener('paste', (e) => {
    const rules = DOC_RULES[tipoSel.value];
    if (!rules?.onlyDigits) return;
    e.preventDefault();
    const pasted = (e.clipboardData || window.clipboardData).getData('text');
    docInput.value = pasted.replace(/\D/g, '').slice(0, rules.max);
    validateDoc();
  });

  // Cambiar tipo limpia el número y actualiza reglas
  tipoSel.addEventListener('change', () => { docInput.value = ''; applyRules(); });
  docInput.addEventListener('input', validateDoc);

  // Validación final antes de enviar
  document.getElementById('regForm').addEventListener('submit', (e) => {
    const rules = DOC_RULES[tipoSel.value];
    if (rules && !rules.pattern.test(docInput.value)) {
      e.preventDefault();
      docInput.classList.add('is-invalid');
      docInput.focus();
      hint.className   = 'text-danger fw-semibold';
      hint.textContent = `✗ ${rules.hint}`;
    }
  });

  // Inicializar al cargar la página
  applyRules();