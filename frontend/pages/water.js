async function renderWaterPage(main) {
  main.innerHTML = `
    ${pageHeader(
      'Water',
      'Track water input, usage, loss, treatment and reuse',
      `<select class="select"><option>Time Range</option></select>
       <select class="select"><option>Today</option></select>
       <select class="select"><option>Compare: Yesterday</option></select>`
    )}

    <div class="grid grid-4">
      ${statCard({ icon: '\u{1F4A7}', iconClass: 'icon-blue', value: '42,80,000 L', label: 'Water Input', delta: '3.2% vs yesterday', deltaDir: 'down' })}
      ${statCard({ icon: '\u{1F6BF}', iconClass: 'icon-cyan', value: '36,25,000 L', label: 'Water Used', delta: '3.6% vs yesterday', deltaDir: 'up' })}
      ${statCard({ icon: '\u26A0', iconClass: 'icon-red', value: '4,80,000 L', label: 'Water Loss (Unaccounted)', delta: '11.2% vs yesterday', deltaDir: 'up' })}
      <div class="card stat-card">
        <div class="stat-label">Water Efficiency Score</div>
        <div style="display:flex; justify-content:center; margin-top:6px;">${gauge('waterPageGauge', 76, '#3b82f6')}</div>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card">
        <div class="card-title">Water Flow (L)</div>
        <div class="chart-wrap"><canvas id="waterTrendChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Key Indicators</div>
        <div class="kv-list" style="margin-top: 10px;">
          <div class="kv-row"><span class="kv-label">Treatment Rate</span><span class="badge badge-green">91.1%</span></div>
          <div class="kv-row"><span class="kv-label">Reuse Rate</span><span class="badge badge-green">67.3%</span></div>
          <div class="kv-row"><span class="kv-label">Water Loss %</span><span class="badge badge-red">11.2%</span></div>
        </div>
      </div>
    </div>

    <div class="grid grid-3">
      ${statCard({ icon: '\u{1F4A7}', iconClass: 'icon-blue', value: '33,00,000 L', label: 'Treatment — 91.1% of water treated' })}
      ${statCard({ icon: '\u267B', iconClass: 'icon-cyan', value: '22,90,000 L', label: 'Reuse — 67.3% of treated water reused' })}
      ${statCard({ icon: '\u26A0', iconClass: 'icon-red', value: '4,80,000 L', label: 'Water Loss — 11.2% of water input' })}
    </div>
  `;

  drawGauge('waterPageGauge', 76, '#3b82f6');

  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
  const values = hours.map((_, i) => Math.round(500000 + Math.sin(i / 3) * 300000 + Math.random() * 80000));
  lineChart('waterTrendChart', hours, [
    { label: 'Flow', data: values, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.12)' },
  ]);

  const facilities = await getFacilities();
  if (facilities.length) {
    const code = facilities[0].facility_code;
    const real = await getFacilityWaterTrend(code, 24);
    if (real && real.length) {
      const labels = real.map(r => new Date(r.reading_time).toLocaleTimeString([], { hour: '2-digit' }));
      const vals = real.map(r => r.reading_value);
      lineChart('waterTrendChart', labels, [
        { label: `Flow (${code})`, data: vals, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.12)' },
      ]);
    }
  }
}
