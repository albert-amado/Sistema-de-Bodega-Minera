/* ─────────────────────────────────────────────────────────────
   PÁGINA PRINCIPAL - DASHBOARD DE GRÁFICAS (SOPORTE MODO CLARO/OSCURO)
   ───────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  let chartPrestamosInst = null;
  let chartMesesInst = null;
  let chartSaludInst = null;

  function isDarkMode() {
    return (
      document.body.classList.contains('dark-mode') ||
      document.documentElement.classList.contains('dark-mode') ||
      document.documentElement.getAttribute('data-theme') === 'dark'
    );
  }

  function getThemeColors() {
    const dark = isDarkMode();
    return {
      activo: '#39A900',
      vencido: dark ? '#E5484D' : '#ef4444',
      devuelto: '#10b981',
      parcial: dark ? '#E5A00D' : '#f59e0b',
      barFill: dark ? 'rgba(57, 169, 0, 0.75)' : 'rgba(57, 169, 0, 0.85)',
      barHover: '#39A900',
      barBorder: dark ? 'rgba(74, 222, 128, 0.45)' : '#39A900',
      gridColor: dark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.06)',
      textColor: dark ? '#9CA3AF' : '#334155',
      yTickColor: dark ? '#D1D5DB' : '#0f172a',
      borderColor: dark ? '#141619' : '#ffffff',
      tooltipBg: dark ? '#1A1D21' : '#1e293b',
      tooltipTitle: '#F3F4F6',
      tooltipBody: '#D1D5DB',
      tooltipBorder: dark ? 'rgba(255, 255, 255, 0.1)' : '#334155',
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
          labels: rawData.labels || ['Activos', 'Devueltos', 'Pendientes', 'Cancelados'],
          datasets: [{
            data: rawData.data || [0, 0, 0, 0],
            backgroundColor: rawData.colors || [tc.activo, tc.devuelto, tc.parcial, tc.vencido],
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
              backgroundColor: tc.tooltipBg,
              titleColor: tc.tooltipTitle,
              bodyColor: tc.tooltipBody,
              borderColor: tc.tooltipBorder,
              borderWidth: 1,
              cornerRadius: 8,
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
            backgroundColor: tc.barFill,
            hoverBackgroundColor: tc.barHover,
            borderColor: tc.barBorder,
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
              backgroundColor: tc.tooltipBg,
              titleColor: tc.tooltipTitle,
              bodyColor: tc.tooltipBody,
              borderColor: tc.tooltipBorder,
              borderWidth: 1,
              cornerRadius: 8,
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
              backgroundColor: tc.tooltipBg,
              titleColor: tc.tooltipTitle,
              bodyColor: tc.tooltipBody,
              borderColor: tc.tooltipBorder,
              borderWidth: 1,
              cornerRadius: 8,
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

  const observer = new MutationObserver(function (mutations) {
    for (let i = 0; i < mutations.length; i++) {
      if (mutations[i].attributeName === 'class' || mutations[i].attributeName === 'data-theme') {
        renderAllCharts();
        break;
      }
    }
  });
  observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] });

})();