
document.addEventListener('DOMContentLoaded', () => {
  // ──────────────────────────────────────────────
  // 1. Lectura segura de datos JSON inyectados
  // ──────────────────────────────────────────────
  function parseJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      console.error(`Error al parsear JSON del elemento #${id}:`, e);
      return null;
    }
  }

  const chartEstados = parseJsonScript('chart-estados-data');
  const chartMeses   = parseJsonScript('chart-meses-data');

  // ──────────────────────────────────────────────
  // 2. Animación de contadores KPI
  // ──────────────────────────────────────────────
  function animarContador(el, target, duracion = 950) {
    const inicio = performance.now();

    function paso(ahora) {
      const p = Math.min((ahora - inicio) / duracion, 1);
      const ease = 1 - Math.pow(1 - p, 3); // easeOutCubic
      el.textContent = Math.round(ease * target);
      if (p < 1) {
        requestAnimationFrame(paso);
      } else {
        el.textContent = target;
      }
    }

    requestAnimationFrame(paso);
  }

  function initKpis() {
    document.querySelectorAll('.kpi-card').forEach((card) => {
      const delay = parseInt(card.getAttribute('data-kpi-delay'), 10) || 0;

      setTimeout(() => {
        card.classList.add('kpi-visible');

        card.querySelectorAll('.kpi-number').forEach((num) => {
          const target = parseInt(num.getAttribute('data-target'), 10) || 0;
          animarContador(num, target);
        });
      }, delay + 100);
    });
  }

  // ──────────────────────────────────────────────
  // 3. Inicialización de gráficos Chart.js
  // ──────────────────────────────────────────────
  function initCharts() {
    // Gráfico de estados de préstamos (doughnut / pie)
    if (chartEstados && document.getElementById('chartPrestamos')) {
      const ctxEstados = document.getElementById('chartPrestamos').getContext('2d');
      new Chart(ctxEstados, {
        type: chartEstados.type || 'doughnut',
        data: {
          labels: chartEstados.labels || [],
          datasets: [{
            data: chartEstados.data || [],
            backgroundColor: chartEstados.backgroundColor || [
              '#1D9E75', // activos
              '#98473E', // vencidos
              '#c4900a', // pendientes
              '#5b8dee'  // otros
            ],
            borderWidth: 0,
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { boxWidth: 12, padding: 16 }
            }
          }
        }
      });
    }

    // Gráfico de actividad por mes (bar)
    if (chartMeses && document.getElementById('chartMeses')) {
      const ctxMeses = document.getElementById('chartMeses').getContext('2d');
      new Chart(ctxMeses, {
        type: chartMeses.type || 'bar',
        data: {
          labels: chartMeses.labels || [],
          datasets: [{
            label: chartMeses.label || 'Préstamos',
            data: chartMeses.data || [],
            backgroundColor: chartMeses.backgroundColor || '#5b8dee',
            borderRadius: 6,
            maxBarThickness: 40
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0 }
            },
            x: {
              grid: { display: false }
            }
          }
        }
      });
    }

    // Si existe un tercer canvas (chartSalud) y datos adicionales, se puede extender aquí.
  }

  // ──────────────────────────────────────────────
  // 4. Ejecución
  // ──────────────────────────────────────────────
  initKpis();
  initCharts();
});