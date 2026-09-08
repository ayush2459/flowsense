async function renderReportsPage(main) {
  const reportTypes = [
    { icon: '\u{1F4CA}', color: 'blue', title: 'Energy Report', desc: 'Detailed energy consumption report' },
    { icon: '\u{1F4A7}', color: 'cyan', title: 'Water Report', desc: 'Detailed water usage report' },
    { icon: '\u267B', color: 'green', title: 'Efficiency Report', desc: 'Resource efficiency and performance' },
    { icon: '\u{1F4CB}', color: 'purple', title: 'Compliance Report', desc: 'Environmental compliance and sustainability' },
  ];

  const generated = [
    { name: 'Energy Report - Aug 2026', type: 'Energy', scope: 'All Facilities', period: 'Aug 2026', date: 'Aug 20, 2026' },
    { name: 'Water Report - Aug 2026', type: 'Water', scope: 'All Facilities', period: 'Aug 2026', date: 'Aug 20, 2026' },
    { name: 'Efficiency Report - Q3 2026', type: 'Efficiency', scope: 'All Facilities', period: 'Jul - Sep 2026', date: 'Aug 20, 2026' },
    { name: 'Compliance Report - 2026', type: 'Compliance', scope: 'All Facilities', period: 'Jan - Dec 2026', date: 'Aug 20, 2026' },
  ];

  main.innerHTML = `
    ${pageHeader('Reports', 'Generate and download detailed reports', '')}

    <div class="grid grid-4">
      ${reportTypes.map(r => `
        <div class="card report-card">
          <div class="stat-icon icon-${r.color}">${r.icon}</div>
          <div class="report-title">${r.title}</div>
          <div class="report-desc">${r.desc}</div>
        </div>
      `).join('')}
    </div>

    <div class="card">
      <div class="card-title">Generated Reports</div>
      <table class="data-table">
        <thead><tr><th>Report Name</th><th>Type</th><th>Facility/Group</th><th>Period</th><th>Generated On</th><th>Download</th></tr></thead>
        <tbody>
          ${generated.map(g => `
            <tr>
              <td>${g.name}</td>
              <td><span class="badge badge-blue">${g.type}</span></td>
              <td>${g.scope}</td>
              <td>${g.period}</td>
              <td>${g.date}</td>
              <td><span class="link">\u2B07</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}
