async function renderEnergyPage(main) {
  main.innerHTML = `
    ${pageHeader(
      'Energy',
      'Monitor energy consumption, trends and efficiency',
      `<select class="select"><option>Time Range</option></select>
       <select class="select"><option>Today</option></select>
       <select class="select"><option>Compare: Yesterday</option></select>`
    )}

    <div class="grid grid-4">
      ${statCard({ icon: '\u26A1', iconClass: 'icon-blue', value: '18,40,000 kWh', label: 'Total Consumption', delta: '6.6% vs yesterday', deltaDir: 'up' })}
      ${statCard({ icon: '\u{1F4CA}', iconClass: 'icon-cyan', value: '16,95,000 kWh', label: 'Expected Consumption', delta: '6.6% vs yesterday', deltaDir: 'up' })}
      ${statCard({ icon: '\u26A0', iconClass: 'icon-red', value: '1,45,000 kWh', label: 'Excess Consumption', delta: '6.6% vs yesterday', deltaDir: 'up' })}
      <div class="card stat-card">
        <div class="stat-label">Energy Efficiency Score</div>
        <div style="display:flex; justify-content:center; margin-top:6px;">${gauge('energyPageGauge', 81, '#22c55e')}</div>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card">
        <div class="card-title">Energy Consumption (kWh)</div>
        <div class="chart-wrap"><canvas id="energyTrendChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Breakdown</div>
        <div style="display:flex; align-items:center; gap:18px;">
          ${gauge('breakdownGauge', 0, '#22d3ee').replace('gauge-num">0<', 'gauge-num">18.4<').replace('gauge-max">/100', 'gauge-max">GWh')}
          <div class="kv-list">
            <div class="kv-row"><span class="kv-label">HVAC</span><span class="kv-value">40%</span></div>
            <div class="kv-row"><span class="kv-label">Lighting</span><span class="kv-value">20%</span></div>
            <div class="kv-row"><span class="kv-label">Machinery</span><span class="kv-value">25%</span></div>
            <div class="kv-row"><span class="kv-label">Others</span><span class="kv-value">15%</span></div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-2">
      ${statCard({ icon: '\u{1F4B0}', iconClass: 'icon-green', value: '\u20B9 18.4 L', label: 'Estimated Savings — Annual Potential' })}
      ${statCard({ icon: '\u{1F4C9}', iconClass: 'icon-blue', value: '1.7 GWh', label: 'If excess is reduced — Energy Savings Potential' })}
    </div>
  `;

  drawGauge('energyPageGauge', 81, '#22c55e');

  const breakdownCanvas = document.getElementById('breakdownGauge');
  if (breakdownCanvas) {
    new Chart(breakdownCanvas, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [40, 20, 25, 15],
          backgroundColor: ['#22d3ee', '#f59e0b', '#a855f7', '#3b82f6'],
          borderWidth: 0,
        }],
      },
      options: { cutout: '70%', plugins: { legend: { display: false } } },
    });
  }

  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
  const actual = hours.map((_, i) => Math.round(600000 + Math.sin(i / 3) * 400000 + Math.random() * 100000));
  const expected = hours.map((_, i) => Math.round(550000 + Math.sin(i / 3) * 350000));
  lineChart('energyTrendChart', hours, [
    { label: 'Actual', data: actual, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.08)' },
    { label: 'Expected', data: expected, borderColor: '#f59e0b', backgroundColor: 'transparent', borderDash: [5, 4], fill: false },
  ]);

  // If a facility is wired up, try to layer real data on top (best-effort)
  const facilities = await getFacilities();
  if (facilities.length) {
    const code = facilities[0].facility_code;
    const real = await getFacilityEnergyTrend(code, 24);
    if (real && real.length) {
      const labels = real.map(r => new Date(r.reading_time).toLocaleTimeString([], { hour: '2-digit' }));
      const values = real.map(r => r.reading_value);
      lineChart('energyTrendChart', labels, [
        { label: `Actual (${code})`, data: values, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.08)' },
      ]);
    }
  }
}
