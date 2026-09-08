function statCard({ icon, iconClass, value, label, delta, deltaDir }) {
  const deltaHtml = delta
    ? `<span class="stat-delta ${deltaDir === 'up' ? 'up' : 'down'}">${deltaDir === 'up' ? '\u25B2' : '\u25BC'} ${delta}</span>`
    : '';
  return `
    <div class="card stat-card">
      <div class="stat-top">
        <div class="stat-icon ${iconClass}">${icon}</div>
      </div>
      <div class="stat-value">${value}</div>
      <div class="stat-label">${label} ${deltaHtml}</div>
    </div>`;
}

function gauge(id, value, color) {
  return `
    <div class="gauge-wrap">
      <canvas id="${id}" width="120" height="120"></canvas>
      <div class="gauge-value">
        <div class="gauge-num">${value}</div>
        <div class="gauge-max">/100</div>
      </div>
    </div>`;
}

function drawGauge(canvasId, value, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [value, 100 - value],
        backgroundColor: [color, 'rgba(255,255,255,0.06)'],
        borderWidth: 0,
      }],
    },
    options: {
      cutout: '75%',
      rotation: -90,
      circumference: 360,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}

function severityBadgeClass(sev) {
  const s = (sev || '').toLowerCase();
  if (s === 'critical') return 'badge-red';
  if (s === 'high') return 'badge-amber';
  if (s === 'medium') return 'badge-amber';
  if (s === 'low') return 'badge-green';
  return 'badge-gray';
}

function statusBadgeClass(status) {
  const s = (status || '').toLowerCase();
  if (s === 'healthy' || s === 'active' || s === 'resolved') return 'badge-green';
  if (s === 'needs attention' || s === 'in progress' || s === 'acknowledged') return 'badge-amber';
  if (s === 'critical' || s === 'new' || s === 'open') return 'badge-red';
  return 'badge-gray';
}

function lineChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  return new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: datasets.map(d => ({
      ...d,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2,
      fill: d.fill !== undefined ? d.fill : true,
    })) },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: datasets.length > 1, labels: { color: '#93a2bc', boxWidth: 12, font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: '#5c6b88', maxTicksLimit: 7, font: { size: 11 } }, grid: { color: '#1e2c46' } },
        y: { ticks: { color: '#5c6b88', font: { size: 11 } }, grid: { color: '#1e2c46' } },
      },
    },
  });
}

function pageHeader(title, subtitle, controlsHtml) {
  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">${title}</h1>
        <p class="page-subtitle">${subtitle}</p>
      </div>
      <div class="controls">${controlsHtml || ''}</div>
    </div>`;
}

function loadingHtml(msg = 'Loading…') {
  return `<div class="loading-state">${msg}</div>`;
}
