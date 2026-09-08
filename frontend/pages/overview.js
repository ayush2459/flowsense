async function renderOverviewPage(main) {
  const [facilities, anomalies] = await Promise.all([getFacilities(), getRecentAnomalies()]);

  const totalFacilities = facilities.length || MOCK.portfolio.total_facilities;
  const critical = anomalies.filter(a => (a.severity || '').toLowerCase() === 'critical').length;

  main.innerHTML = `
    ${pageHeader(
      'Dashboard Overview',
      `Real-time overview of energy and water across ${totalFacilities} facilities`,
      `<select class="select"><option>All Facilities</option></select>
       <select class="select"><option>Aug 09, 2026</option></select>
       <span class="live-badge"><span class="dot"></span> Live</span>`
    )}

    <div class="grid grid-4">
      ${statCard({ icon: '\u{1F3E2}', iconClass: 'icon-blue', value: totalFacilities, label: 'Total Facilities' })}
      ${statCard({ icon: '\u2705', iconClass: 'icon-green', value: MOCK.portfolio.healthy, label: 'Healthy  60%' })}
      ${statCard({ icon: '\u26A0', iconClass: 'icon-amber', value: MOCK.portfolio.needs_attention, label: 'Needs Attention  27%' })}
      ${statCard({ icon: '\u{1F514}', iconClass: 'icon-red', value: MOCK.portfolio.critical, label: 'Critical  10%' })}
    </div>

    <div class="grid grid-4">
      ${statCard({ icon: '\u26A1', iconClass: 'icon-cyan', value: MOCK.portfolio.total_energy_gwh + ' GWh', label: 'Total Energy', delta: '6.6% vs yesterday', deltaDir: 'up' })}
      ${statCard({ icon: '\u{1F4A7}', iconClass: 'icon-blue', value: MOCK.portfolio.total_water_ml + ' ML', label: 'Total Water', delta: '3.2% vs yesterday', deltaDir: 'down' })}
      ${statCard({ icon: '\u20B9', iconClass: 'icon-purple', value: '\u20B9' + MOCK.portfolio.total_cost_cr + ' Cr', label: 'Total Cost', delta: '7.1% vs yesterday', deltaDir: 'up' })}
      ${statCard({ icon: '\u{1F343}', iconClass: 'icon-green', value: MOCK.portfolio.total_emissions_tco2 + ' tCO\u2082', label: 'Total Emissions', delta: '6.3% vs yesterday', deltaDir: 'up' })}
    </div>

    <div class="grid grid-2">
      <div class="card">
        <div class="card-title">\u26A1 Energy Overview</div>
        <div class="gauge-row">
          <div id="energyGaugeWrap">${gauge('energyGauge', MOCK.portfolio.energy_score, '#22c55e')}</div>
          <div class="kv-list">
            <div class="kv-row"><span class="kv-label">Total Consumption</span><span class="kv-value">18,40,000 kWh</span></div>
            <div class="kv-row"><span class="kv-label">Expected Consumption</span><span class="kv-value">16,95,000 kWh</span></div>
            <div class="kv-row"><span class="kv-label">Excess Consumption</span><span class="kv-value" style="color:var(--accent-red)">1,45,000 kWh</span></div>
            <div class="kv-row"><span class="kv-label">Energy Waste</span><span class="kv-value">7.9%</span></div>
            <div class="kv-row"><span class="kv-label">Estimated Savings</span><span class="kv-value" style="color:var(--accent-green)">\u20B9 18.4 L</span></div>
          </div>
        </div>
        <div class="chart-wrap" style="height:120px; margin-top:16px;"><canvas id="energyMiniChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">\u{1F4A7} Water Overview</div>
        <div class="gauge-row">
          <div id="waterGaugeWrap">${gauge('waterGauge', MOCK.portfolio.water_score, '#3b82f6')}</div>
          <div class="kv-list">
            <div class="kv-row"><span class="kv-label">Water Input</span><span class="kv-value">42,80,000 L</span></div>
            <div class="kv-row"><span class="kv-label">Water Used</span><span class="kv-value">36,25,000 L</span></div>
            <div class="kv-row"><span class="kv-label">Water Loss (Unaccounted)</span><span class="kv-value" style="color:var(--accent-red)">4,80,000 L (11.2%)</span></div>
            <div class="kv-row"><span class="kv-label">Treatment Rate</span><span class="kv-value" style="color:var(--accent-green)">91.1%</span></div>
            <div class="kv-row"><span class="kv-label">Reuse Rate</span><span class="kv-value" style="color:var(--accent-green)">67.3%</span></div>
          </div>
        </div>
        <div class="chart-wrap" style="height:120px; margin-top:16px;"><canvas id="waterMiniChart"></canvas></div>
      </div>
    </div>
  `;

  drawGauge('energyGauge', MOCK.portfolio.energy_score, '#22c55e');
  drawGauge('waterGauge', MOCK.portfolio.water_score, '#3b82f6');

  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const rand = (base, spread) => hours.map(() => Math.round(base + (Math.random() - 0.5) * spread));
  lineChart('energyMiniChart', hours, [{ label: 'Actual', data: rand(700000, 200000), borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,0.08)' }]);
  lineChart('waterMiniChart', hours, [{ label: 'Flow', data: rand(900000, 250000), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.08)' }]);
}
