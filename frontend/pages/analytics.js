let analyticsTab = 'Energy Analytics';

async function renderAnalyticsPage(main) {
  const tabs = ['Energy Analytics', 'Water Analytics', 'Correlation', 'Custom'];

  main.innerHTML = `
    ${pageHeader('Analytics', 'Deep insights, patterns and correlations',
      `<select class="select"><option>Time Range</option></select>
       <select class="select"><option>Last 7 Days</option></select>`
    )}

    <div class="tab-row">
      ${tabs.map(t => `<div class="tab ${t === analyticsTab ? 'active' : ''}" data-tab="${t}">${t}</div>`).join('')}
    </div>

    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card">
        <div class="card-title">Energy Pattern (Daily Heatmap)</div>
        <div id="heatmapWrap"></div>
      </div>
      <div class="card">
        <div class="card-title">Top Energy Drivers</div>
        <div class="kv-list">
          ${driverRow('HVAC', 42, '#22c55e')}
          ${driverRow('Machinery', 28, '#22c55e')}
          ${driverRow('Lighting', 18, '#f59e0b')}
          ${driverRow('Others', 12, '#3b82f6')}
        </div>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card">
        <div class="card-title">Energy vs External Factors</div>
        <div class="chart-wrap"><canvas id="scatterChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Insights</div>
        <p style="font-size:13px; color:var(--text-secondary); line-height:1.6;">
          Energy consumption increases as temperature rises above 26°C. HVAC load is the major contributor.
        </p>
      </div>
    </div>
  `;

  main.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => { analyticsTab = t.dataset.tab; renderAnalyticsPage(main); });
  });

  renderHeatmap();
  renderScatter();
}

function driverRow(label, pct, color) {
  return `
    <div>
      <div class="kv-row" style="margin-bottom:4px;"><span class="kv-label">${label}</span><span class="kv-value">${pct}%</span></div>
      <div style="height:6px; background:rgba(255,255,255,0.06); border-radius:4px; overflow:hidden;">
        <div style="height:100%; width:${pct}%; background:${color};"></div>
      </div>
    </div>`;
}

function renderHeatmap() {
  const wrap = document.getElementById('heatmapWrap');
  if (!wrap) return;
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const hours = 24;
  let html = '<div style="display:grid; grid-template-columns: 40px repeat(' + hours + ', 1fr); gap:2px;">';
  html += '<div></div>' + Array.from({ length: hours }, (_, h) => h % 4 === 0 ? `<div style="font-size:9px; color:var(--text-muted); text-align:center;">${h}h</div>` : '<div></div>').join('');
  days.forEach(d => {
    html += `<div style="font-size:11px; color:var(--text-secondary); display:flex; align-items:center;">${d}</div>`;
    for (let h = 0; h < hours; h++) {
      const intensity = Math.max(0, Math.sin((h - 13) / 6) * 0.8 + 0.2 + Math.random() * 0.15);
      html += `<div style="height:16px; border-radius:2px; background:${heatColor(intensity)};"></div>`;
    }
  });
  html += '</div>';
  wrap.innerHTML = html;
}

function heatColor(t) {
  t = Math.min(1, Math.max(0, t));
  const stops = [
    [59, 130, 246], [34, 211, 238], [34, 197, 94], [245, 158, 11], [239, 68, 68],
  ];
  const idx = Math.min(stops.length - 2, Math.floor(t * (stops.length - 1)));
  const localT = t * (stops.length - 1) - idx;
  const c = stops[idx].map((v, i) => Math.round(v + (stops[idx + 1][i] - v) * localT));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

function renderScatter() {
  const ctx = document.getElementById('scatterChart');
  if (!ctx) return;
  const points = Array.from({ length: 40 }, () => {
    const temp = 10 + Math.random() * 25;
    const energy = 100000 + temp * 55000 + Math.random() * 150000;
    return { x: Math.round(temp), y: Math.round(energy) };
  });
  new Chart(ctx, {
    type: 'scatter',
    data: { datasets: [{ label: 'Energy vs Temp', data: points, backgroundColor: '#22c55e' }] },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'Temperature (°C)', color: '#93a2bc' }, ticks: { color: '#5c6b88' }, grid: { color: '#1e2c46' } },
        y: { title: { display: true, text: 'Energy (kWh)', color: '#93a2bc' }, ticks: { color: '#5c6b88' }, grid: { color: '#1e2c46' } },
      },
    },
  });
}
