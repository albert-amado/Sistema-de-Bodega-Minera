/* ─────────────────────────────────────────────────────────────
   PÁGINA PRINCIPAL - DASHBOARD DE GRÁFICAS (SOPORTE MODO CLARO/OSCURO)
   ───────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  let chartPrestamosInst = null;
  let chartMesesInst = null;
  let chartSaludInst = null;

  function isDarkMode() {
    return document.body.classList.contains('dark-mode');
  }

  function getThemeColors() {
    const dark = isDarkMode();
    return {
      activo: '#10b981',        // Verde esmeralda
      vencido: '#ef4444',       // Rojo
      devuelto: '#3b82f6',      // Azul
      parcial: '#f59e0b',       // Amarillo/Ámbar
      gridColor: dark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
      textColor: dark ? '#cbd5e1' : '#334155',
      yTickColor: dark ? '#f1f5f9' : '#0f172a',
      borderColor: dark ? '#1e293b' : '#ffffff',
      fontFamily: "'Inter', system-ui, sans-serif"
    };
  }

  // ── 1. Gráfica de Estado de Préstamos (Doughnut) ──
  function initChartPrestamos() {
    const el = document.getElementById('chart-prestamos-data');
    const canvas = document.getElementById('chartPrestamos');
    if (!el || !canvas) return;

    if (chartPrestamosInst) {
      chartPrestamosInst.destroy();
      chartPrestamosInst = null;
    }

    try {
      const rawData = JSON.parse(el.textContent);
      const ctx = canvas.getContext('2d');
      const tc = getThemeColors();

      chartPrestamosInst = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: rawData.labels || ['Activos', 'Devueltos', 'Vencidos'],
          datasets: [{
            data: rawData.data || [0, 0, 0],
            backgroundColor: [tc.activo, tc.devuelto, tc.vencido],
            borderWidth: 2,
            borderColor: tc.borderColor
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 600 },
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                color: tc.textColor,
                font: { family: tc.fontFamily, size: 12, weight: '600' },
                padding: 16,
                usePointStyle: true,
                pointStyleWidth: 10
              }
            },
            tooltip: {
              backgroundColor: '#1e293b',
              titleColor: '#ffffff',
              bodyColor: '#e2e8f0',
              borderColor: '#334155',
              borderWidth: 1,
              padding: 10
            }
          },
          cutout: '70%'
        }
      });
    } catch (e) {
      console.error('Error iniciando chartPrestamos:', e);
    }
  }

  // ── 2. Gráfica de Actividad por Mes (Bar / Line) ──
  function initChartMeses() {
    const el = document.getElementById('chart-meses-data');
    const canvas = document.getElementById('chartMeses');
    if (!el || !canvas) return;

    if (chartMesesInst) {
      chartMesesInst.destroy();
      chartMesesInst = null;
    }

    try {
      const rawData = JSON.parse(el.textContent);
      const ctx = canvas.getContext('2d');
      const tc = getThemeColors();

      chartMesesInst = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: rawData.labels || ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago'],
          datasets: [{
            label: 'Solicitudes / Préstamos',
            data: rawData.data || [0, 0, 0, 0, 0, 0, 0, 0],
            backgroundColor: 'rgba(59, 130, 246, 0.85)',
            borderColor: '#2563eb',
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 600 },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#1e293b',
              titleColor: '#ffffff',
              bodyColor: '#e2e8f0',
              borderColor: '#334155',
              borderWidth: 1,
              padding: 10
            }
          },
          scales: {
            x: {
              grid: { color: tc.gridColor },
              ticks: { color: tc.textColor, font: { family: tc.fontFamily, weight: '500' } }
            },
            y: {
              beginAtZero: true,
              grid: { color: tc.gridColor },
              ticks: { color: tc.yTickColor, font: { family: tc.fontFamily, weight: '600' }, precision: 0 }
            }
          }
        }
      });
    } catch (e) {
      console.error('Error iniciando chartMeses:', e);
    }
  }

  // ── 3. Gráfica de Salud de Inventario (Pie / Doughnut) ──
  function initChartSalud() {
    const el = document.getElementById('chart-salud-data');
    const canvas = document.getElementById('chartSalud');
    if (!el || !canvas) return;

    if (chartSaludInst) {
      chartSaludInst.destroy();
      chartSaludInst = null;
    }

    try {
      const rawData = JSON.parse(el.textContent);
      const ctx = canvas.getContext('2d');
      const tc = getThemeColors();

      chartSaludInst = new Chart(ctx, {
        type: 'pie',
        data: {
          labels: rawData.labels || ['Disponible', 'No disponible'],
          datasets: [{
            data: rawData.data || [0, 0],
            backgroundColor: [tc.activo, tc.vencido],
            borderWidth: 2,
            borderColor: tc.borderColor
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 600 },
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                color: tc.textColor,
                font: { family: tc.fontFamily, size: 12, weight: '600' },
                padding: 16,
                usePointStyle: true,
                pointStyleWidth: 10
              }
            },
            tooltip: {
              backgroundColor: '#1e293b',
              titleColor: '#ffffff',
              bodyColor: '#e2e8f0',
              borderColor: '#334155',
              borderWidth: 1,
              padding: 10
            }
          }
        }
      });
    } catch (e) {
      console.error('Error iniciando chartSalud:', e);
    }
  }

  function renderAllCharts() {
    initChartPrestamos();
    initChartMeses();
    initChartSalud();
  }

  // Animación contadores KPI
  function animateKpis() {
    const kpiElements = document.querySelectorAll('.kpi-number');
    kpiElements.forEach(el => {
      const target = parseInt(el.getAttribute('data-target') || '0', 10);
      let start = 0;
      const duration = 600;
      const stepTime = 25;
      const steps = duration / stepTime;
      const increment = target / steps;

      if (target === 0) {
        el.textContent = '0';
        return;
      }

      const timer = setInterval(() => {
        start += increment;
        if (start >= target) {
          el.textContent = target;
          clearInterval(timer);
        } else {
          el.textContent = Math.floor(start);
        }
      }, stepTime);
    });
  }

  function init() {
    renderAllCharts();
    animateKpis();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Observador reactivo para conmutar colores si cambia la clase dark-mode en el body
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      if (m.attributeName === 'class') {
        renderAllCharts();
      }
    });
  });
  observer.observe(document.body, { attributes: true });

})();