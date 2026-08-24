/* ─────────────────────────────────────────────────────────────
   PÁGINA PRINCIPAL - DASHBOARD DE GRÁFICAS (SOPORTE MODO CLARO/OSCURO)
   ───────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  let chartPrestamosInst = null;
  let chartCategoriasInst = null;
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
          labels: rawData.labels || ['Activos', 'Vencidos', 'Devueltos', 'Parciales'],
          datasets: [{
            data: rawData.data || [0, 0, 0, 0],
            backgroundColor: [tc.activo, tc.vencido, tc.devuelto, tc.parcial],
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

  // ── 2. Gráfica de Stock por Categoría (Bar) ──
  function initChartCategorias() {
    const el = document.getElementById('chart-categorias-data');
    const canvas = document.getElementById('chartCategorias');
    if (!el || !canvas) return;

    if (chartCategoriasInst) {
      chartCategoriasInst.destroy();
      chartCategoriasInst = null;
    }

    try {
      const rawData = JSON.parse(el.textContent);
      const ctx = canvas.getContext('2d');
      const tc = getThemeColors();

      chartCategoriasInst = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: rawData.labels || [],
          datasets: [{
            label: 'Herramientas',
            data: rawData.data || [],
            backgroundColor: 'rgba(59, 130, 246, 0.85)',
            borderColor: '#2563eb',
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
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
              grid: { display: false },
              ticks: { color: tc.yTickColor, font: { family: tc.fontFamily, weight: '600' } }
            }
          }
        }
      });
    } catch (e) {
      console.error('Error iniciando chartCategorias:', e);
    }
  }

  // ── 3. Gráfica de Salud de Inventario (Pie) ──
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
          labels: rawData.labels || ['Disponible', 'En Préstamo', 'No disponible'],
          datasets: [{
            data: rawData.data || [0, 0, 0],
            backgroundColor: [tc.activo, tc.parcial, tc.vencido],
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
    initChartCategorias();
    initChartSalud();
  }

  document.addEventListener('DOMContentLoaded', function () {
    renderAllCharts();

    // Observador reactivo para conmutar colores si cambia la clase dark-mode en el body
    const observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        if (m.attributeName === 'class') {
          renderAllCharts();
        }
      });
    });
    observer.observe(document.body, { attributes: true });
  });

})();

/* ── Modal ver producto ── */
function verProducto(sku, nombre, desc, stock, cat) {
  var vpSku    = document.getElementById('vpd-sku');
  var vpNombre = document.getElementById('vpd-nombre');
  var vpCat    = document.getElementById('vpd-cat');
  var vpStock  = document.getElementById('vpd-stock');
  var vpDesc   = document.getElementById('vpd-desc');
  var vpLink   = document.getElementById('vpd-link');

  if (vpSku)    vpSku.textContent    = sku;
  if (vpNombre) vpNombre.textContent = nombre;
  if (vpCat)    vpCat.textContent    = cat || '—';
  if (vpStock) {
    vpStock.textContent = stock;
    vpStock.style.color = stock === 0 ? '#ef4444' : stock < 3 ? '#f59e0b' : '#10b981';
  }
  if (vpDesc)  vpDesc.textContent  = desc || '—';
  if (vpLink)  vpLink.href         = '/inventario/' + encodeURIComponent(sku) + '/editar/';

  var modal = document.getElementById('modalVerProducto');
  if (modal) new bootstrap.Modal(modal).show();
}