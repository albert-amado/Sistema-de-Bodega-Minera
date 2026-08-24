(function () {
  const canvas = document.getElementById('mineCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const ST  = 'rgba(255,255,255,0.11)';
  const PI  = Math.PI;

  function prep(cx, cy, s) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s);
    ctx.strokeStyle = ST; ctx.lineWidth = 1.3 / s;
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  }
  function done() { ctx.restore(); }
  function seg(x0,y0,x1,y1){ ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); ctx.stroke(); }
  function poly(pts){ if (pts.length < 2) return; ctx.beginPath(); ctx.moveTo(pts.at(0),pts.at(1)); for(var i=2;i<pts.length;i+=2) ctx.lineTo(pts.at(i),pts.at(i+1)); ctx.closePath(); ctx.stroke(); }
  function circ(x,y,r){ ctx.beginPath(); ctx.arc(x,y,r,0,PI*2); ctx.stroke(); }
  function rrect(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.lineTo(x+w-r,y); ctx.arcTo(x+w,y,x+w,y+r,r); ctx.lineTo(x+w,y+h-r); ctx.arcTo(x+w,y+h,x+w-r,y+h,r); ctx.lineTo(x+r,y+h); ctx.arcTo(x,y+h,x,y+h-r,r); ctx.lineTo(x,y+r); ctx.arcTo(x,y,x+r,y,r); ctx.closePath(); ctx.stroke(); }

  var icons = [
    function(cx,cy,s){ prep(cx,cy,s); ctx.beginPath(); ctx.moveTo(-0.62,0.62); ctx.lineTo(0.48,-0.48); ctx.stroke(); ctx.beginPath(); ctx.arc(-0.62,0.62,0.07,0,PI*2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0.48,-0.48); ctx.bezierCurveTo(0.6,-0.85,0.95,-0.7,0.78,-0.42); ctx.bezierCurveTo(0.62,-0.2,0.2,0.0,0.0,0.18); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0.48,-0.48); ctx.lineTo(0.24,-0.28); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0.78,-0.42); ctx.bezierCurveTo(0.88,-0.28,0.72,-0.1,0.56,-0.14); ctx.stroke(); done(); },
    function(cx,cy,s){ prep(cx,cy,s); ctx.beginPath(); ctx.arc(0,0.06,0.52,PI*1.08,PI*1.92); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-0.6,0.06); ctx.bezierCurveTo(-0.72,0.06,-0.75,0.22,-0.62,0.22); ctx.lineTo(0.62,0.22); ctx.bezierCurveTo(0.75,0.22,0.72,0.06,0.6,0.06); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-0.5,0.06); ctx.lineTo(-0.5,0.22); ctx.moveTo(0.5,0.06); ctx.lineTo(0.5,0.22); ctx.stroke(); rrect(-0.16,-0.46,0.32,0.22,0.06); circ(0,-0.35,0.08); seg(0,-0.24,0,0.02); ctx.beginPath(); ctx.moveTo(-0.12,-0.46); ctx.lineTo(-0.26,-0.66); ctx.moveTo(0,-0.48); ctx.lineTo(0,-0.72); ctx.moveTo(0.12,-0.46); ctx.lineTo(0.26,-0.66); ctx.stroke(); done(); },
    function(cx,cy,s){ prep(cx,cy,s); poly([-0.62,0.12,-0.46,-0.38,0.46,-0.38,0.62,0.12]); seg(-0.22,-0.38,-0.22,0.12); seg(0.22,-0.38,0.22,0.12); seg(-0.72,0.12,0.72,0.12); circ(-0.42,0.32,0.22); circ(-0.42,0.32,0.06); for(var i=0;i<4;i++){var a=i*PI/2; seg(-0.42+Math.cos(a)*0.06,0.32+Math.sin(a)*0.06,-0.42+Math.cos(a)*0.22,0.32+Math.sin(a)*0.22);} circ(0.42,0.32,0.22); circ(0.42,0.32,0.06); for(var i=0;i<4;i++){var a=i*PI/2; seg(0.42+Math.cos(a)*0.06,0.32+Math.sin(a)*0.06,0.42+Math.cos(a)*0.22,0.32+Math.sin(a)*0.22);} done(); },
    function(cx,cy,s){ prep(cx,cy,s); rrect(-0.3,0.44,0.6,0.14,0.04); ctx.beginPath(); for(var i=0;i<6;i++){var a=i*PI/3-PI/2; var x=Math.cos(a)*0.28,y=Math.sin(a)*0.28+0.08; if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);} ctx.closePath(); ctx.stroke(); circ(0,0.08,0.14); rrect(-0.06,-0.46,0.12,0.2,0.03); ctx.beginPath(); ctx.arc(0,-0.22,0.2,PI*1.1,PI*1.9); ctx.stroke(); circ(0,-0.42,0.06); done(); },
    function(cx,cy,s){ prep(cx,cy,s); seg(-0.52,0.72,0,-0.72); seg(0.52,0.72,0,-0.72); seg(-0.58,0.72,0.58,0.72); rrect(-0.58,0.6,1.16,0.14,0.04); var levels=[[0.52,-0.28],[0.34,-0.02],[0.16,0.24]]; levels.forEach(function(lv){var w=lv[0],y=lv[1]; seg(-w,y,w,y); seg(-w,y,0,y-0.28); seg(w,y,0,y-0.28);}); seg(-0.28,0.72,-0.14,-0.28); seg(0.28,0.72,0.14,-0.28); circ(0,-0.72,0.08); seg(0,-0.64,0,0.6); done(); },
    function(cx,cy,s){ prep(cx,cy,s); rrect(-0.66,-0.66,1.32,1.32,0.1); circ(0,0,0.52); circ(0,0,0.1); for(var i=0;i<4;i++){ctx.save(); ctx.rotate(i*PI/2); ctx.beginPath(); ctx.moveTo(0.1,0); ctx.bezierCurveTo(0.16,-0.22,0.42,-0.3,0.4,-0.06); ctx.bezierCurveTo(0.38,0.1,0.2,0.18,0.1,0.0); ctx.stroke(); ctx.restore();} seg(-0.66,0,-0.52,0); seg(0.52,0,0.66,0); seg(0,-0.66,0,-0.52); seg(0,0.52,0,0.66); done(); },
    function(cx,cy,s){ prep(cx,cy,s); var T=12,Ro=0.52,Ri=0.37; ctx.beginPath(); for(var i=0;i<T;i++){var a0=(i/T)*PI*2,a1=((i+0.35)/T)*PI*2,a2=((i+0.65)/T)*PI*2,a3=((i+1)/T)*PI*2; if(i===0) ctx.moveTo(Math.cos(a0)*Ri,Math.sin(a0)*Ri); else ctx.lineTo(Math.cos(a0)*Ri,Math.sin(a0)*Ri); ctx.lineTo(Math.cos(a1)*Ro,Math.sin(a1)*Ro); ctx.lineTo(Math.cos(a2)*Ro,Math.sin(a2)*Ro); ctx.lineTo(Math.cos(a3)*Ri,Math.sin(a3)*Ri);} ctx.closePath(); ctx.stroke(); circ(0,0,0.22); circ(0,0,0.07); for(var i=0;i<6;i++){var a=i*PI/3; seg(Math.cos(a)*0.07,Math.sin(a)*0.07,Math.cos(a)*0.22,Math.sin(a)*0.22);} done(); },
    function(cx,cy,s){ prep(cx,cy,s); rrect(-0.72,0.26,1.44,0.4,0.1); circ(-0.6,0.46,0.16); circ(0.6,0.46,0.16); for(var i=-2;i<=2;i++) circ(i*0.28,0.26,0.08); rrect(-0.58,-0.56,0.7,0.84,0.08); rrect(-0.5,-0.5,0.54,0.42,0.06); done(); },
    function(cx,cy,s){ prep(cx,cy,s); circ(-0.42,0,0.46); circ(0.42,0,0.46); circ(-0.42,0,0.3); circ(0.42,0,0.3); seg(-0.42,-0.3,0.42,-0.3); seg(-0.42,0.3,0.42,0.3); circ(0,0,0.08); seg(-0.42,0,-0.08,0); seg(0.08,0,0.42,0); ctx.beginPath(); ctx.moveTo(-0.54,0.46); ctx.lineTo(-0.62,0.66); ctx.lineTo(0.62,0.66); ctx.lineTo(0.54,0.46); ctx.stroke(); seg(-0.62,0.66,0.62,0.66); done(); },
  ];

  var entities = [];

  function initEntities(W, H) {
    entities = [];
    var CELL = 112;
    var cols = Math.ceil(W / CELL) + 2;
    var rows = Math.ceil(H / CELL) + 2;
    var n = 0;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var cx = c * CELL + (r % 2 === 0 ? 0 : CELL * 0.5);
        var cy = r * CELL;
        var jx = ((r * 19 + c * 13) % 11) - 5;
        var jy = ((r * 13 + c * 19) % 11) - 5;
        entities.push({
          iconIndex: n % icons.length,
          originX: cx + jx,
          originY: cy + jy,
          position: { x: cx + jx, y: cy + jy },
          velocity: { x: 0, y: 0 },
          acceleration: { x: 0, y: 0 },
          mass: 1.0 + (Math.abs(jx) % 3) * 0.15
        });
        n++;
      }
    }
  }

  var isAnimating = false;
  var lastTime = performance.now();

  function animate(now) {
    if (!isAnimating) return;
    requestAnimationFrame(animate);
    var dt = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;

    var W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    var CELL = 112, SZ = 0.28;
    var isAntigravity = document.body.classList.contains('antigravity-active');

    for (var i = 0; i < entities.length; i++) {
      var ent = entities.at(i);
      if (isAntigravity) {
        if (window.calculateGravityEffect) {
          window.calculateGravityEffect(ent, 'antygraviti', dt);
        } else {
          ent.velocity.y -= 9.81 * 0.5 * dt;
          ent.position.y += ent.velocity.y;
        }

        // Si sale por arriba, reaparece abajo con velocidad inicial 0
        if (ent.position.y < -50) {
          ent.position.y = H + 50;
          ent.velocity.y = 0;
        }
      } else {
        // Volver suavemente a su posición original
        ent.position.y += (ent.originY - ent.position.y) * 0.08;
        ent.velocity.y = 0;
      }
      var iconFn = icons.at(ent.iconIndex);
      if (iconFn) {
        iconFn(ent.position.x, ent.position.y, CELL * SZ);
      }
    }
  }

  function resize() {
    canvas.width  = canvas.offsetWidth  || canvas.parentElement.offsetWidth;
    canvas.height = canvas.offsetHeight || canvas.parentElement.offsetHeight;
    initEntities(canvas.width, canvas.height);
    if (!isAnimating) {
      isAnimating = true;
      lastTime = performance.now();
      requestAnimationFrame(animate);
    }
  }
  window.addEventListener('resize', resize);
  resize();
})();


const DOC_RULES = new Map([
  ['CC', { min: 6,  max: 10, onlyDigits: true,  pattern: /^\d{6,10}$/,          hint: 'Solo dígitos · 6 a 10 caracteres' }],
  ['CE', { min: 6,  max: 12, onlyDigits: false, pattern: /^[A-Za-z0-9]{6,12}$/, hint: 'Letras y dígitos · 6 a 12 caracteres' }],
  ['PP', { min: 5,  max: 9,  onlyDigits: false, pattern: /^[A-Za-z0-9]{5,9}$/,  hint: 'Letras y dígitos · 5 a 9 caracteres' }],
  ['TI', { min: 10, max: 11, onlyDigits: true,  pattern: /^\d{10,11}$/,          hint: 'Solo dígitos · 10 u 11 caracteres' }]
]);

(function initDocField() {
  const tipoInput   = document.getElementById('tipo_documento');
  const tipoBtn     = document.getElementById('doc-tipo-btn');
  const docInput    = document.getElementById('documento');
  const docDropdown = document.getElementById('docDropdown');
  const hint        = document.getElementById('doc-hint');

  if (!tipoInput || !tipoBtn || !docInput) return;

  tipoBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    docDropdown.classList.toggle('open');
  });
  document.addEventListener('click', () => {
    docDropdown?.classList.remove('open');
  });

  docDropdown?.querySelectorAll('a').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const val = item.dataset.value;
      tipoInput.value = val;
      tipoBtn.firstChild.textContent = val + ' ▾';
      docInput.value = '';
      docDropdown.classList.remove('open');
      applyRules();
    });
  });

  function applyRules() {
    const r = DOC_RULES.get(tipoInput.value);
    if (!r) return;
    docInput.minLength   = r.min;
    docInput.maxLength   = r.max;
    docInput.placeholder = `Mín. ${r.min} – Máx. ${r.max} car.`;
    if (hint) { hint.textContent = r.hint; hint.style.color = 'var(--sage)'; }
    validateDoc();
  }

  function validateDoc() {
    const r = DOC_RULES.get(tipoInput.value);
    if (!r || docInput.value === '') { docInput.classList.remove('is-valid','is-invalid'); return; }
    const ok = r.pattern.test(docInput.value);
    docInput.classList.toggle('is-valid',   ok);
    docInput.classList.toggle('is-invalid', !ok);
  }

  docInput.addEventListener('keypress', (e) => {
    const r = DOC_RULES.get(tipoInput.value);
    if (r?.onlyDigits && !/\d/.test(e.key)) e.preventDefault();
  });

  docInput.addEventListener('paste', (e) => {
    const r = DOC_RULES.get(tipoInput.value);
    if (!r?.onlyDigits) return;
    e.preventDefault();
    docInput.value = (e.clipboardData || window.clipboardData)
      .getData('text').replace(/\D/g, '').slice(0, r.max);
    validateDoc();
  });

  docInput.addEventListener('input', validateDoc);
  applyRules();
})();


  //mostrar error

function showError(area, msg) {
  if (!area) return;
  area.innerHTML = '';
  const errDiv = document.createElement('div');
  errDiv.className = 'alert-mine error';
  errDiv.textContent = `⚠ ${msg}`;
  area.appendChild(errDiv);
}



//LOGIN

const loginForm = document.getElementById('loginForm');
if (loginForm) {
  const area = document.getElementById('msg-area');

  loginForm.addEventListener('submit', function (e) {
    const doc = document.getElementById('documento')?.value.trim();
    const pwd = document.getElementById('password')?.value.trim();
    if (area) area.innerHTML = '';
    if (!doc || !pwd) {
      e.preventDefault();
      showError(area, 'Por favor ingresa tu documento y contraseña.');
    }
  });
}


  //RECUPERAR CONTRASEÑA

const recForm = document.getElementById('recForm');
if (recForm) {
  const area = document.getElementById('msg-area');

  recForm.addEventListener('submit', function (e) {
    const email = document.getElementById('email')?.value.trim();
    if (area) area.innerHTML = '';
    if (!email) {
      e.preventDefault();
      showError(area, 'Por favor ingresa tu correo electrónico.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      e.preventDefault();
      showError(area, 'Ingresa un correo electrónico válido.');
    }
  });
}



  // REGISTRO

const regForm = document.getElementById('regForm');
if (regForm) {
  const area = document.getElementById('msg-area');

  regForm.addEventListener('submit', function (e) {
    const firstName = document.getElementById('first_name')?.value.trim();
    const lastName  = document.getElementById('last_name')?.value.trim();
    const email     = document.getElementById('email')?.value.trim();
    const doc       = document.getElementById('documento')?.value.trim();
    const p1        = document.getElementById('password1')?.value;
    const p2        = document.getElementById('password2')?.value;
    if (area) area.innerHTML = '';

    if (!firstName || !lastName || !email || !doc || !p1 || !p2) {
      e.preventDefault();
      showError(area, 'Por favor completa todos los campos.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      e.preventDefault();
      showError(area, 'Ingresa un correo electrónico válido.');
      return;
    }
    if (p1.length < 8) {
      e.preventDefault();
      showError(area, 'La contraseña debe tener mínimo 8 caracteres.');
      return;
    }
    if (p1 !== p2) {
      e.preventDefault();
      showError(area, 'Las contraseñas no coinciden.');
    }
  });
}



  //NUEVA CONTRASEÑA

const newPassForm = document.getElementById('newPassForm');
if (newPassForm) {
  const area = document.getElementById('msg-area');

  newPassForm.addEventListener('submit', function (e) {
    const p1 = document.getElementById('password1')?.value;
    const p2 = document.getElementById('password2')?.value;
    if (area) area.innerHTML = '';

    if (!p1) {
      e.preventDefault();
      showError(area, 'Ingresa tu nueva contraseña.');
      return;
    }
    if (p1.length < 8) {
      e.preventDefault();
      showError(area, 'La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (p1 !== p2) {
      e.preventDefault();
      showError(area, 'Las contraseñas no coinciden.');
    }
  });
}
// Solo dígitos en número de ficha (si es campo de texto)
const fichaInput = document.getElementById('numero_ficha');
if (fichaInput && fichaInput.tagName === 'INPUT') {
  fichaInput.addEventListener('keypress', (e) => {
    if (!/\d/.test(e.key)) e.preventDefault();
  });
  fichaInput.addEventListener('paste', (e) => {
    e.preventDefault();
    fichaInput.value = (e.clipboardData || window.clipboardData)
      .getData('text').replace(/\D/g, '').slice(0, 7);
  });
  fichaInput.addEventListener('input', () => {
    fichaInput.value = fichaInput.value.replace(/\D/g, '');
  });
}