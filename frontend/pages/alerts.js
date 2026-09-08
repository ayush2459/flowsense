let alertsState = { filter: 'All', page: 1, pageSize: 6, data: [] };

async function renderAlertsPage(main) {
  const anomalies = await getRecentAnomalies();
  alertsState.data = anomalies;

  const counts = {
    All: anomalies.length,
    Critical: anomalies.filter(a => (a.severity || '').toLowerCase() === 'critical').length,
    High: anomalies.filter(a => (a.severity || '').toLowerCase() === 'high').length,
    Medium: anomalies.filter(a => (a.severity || '').toLowerCase() === 'medium').length,
    Low: anomalies.filter(a => (a.severity || '').toLowerCase() === 'low').length,
  };

  main.innerHTML = `
    ${pageHeader('Alerts', 'All important alerts with severity, time and status', '')}

    <div class="pill-row" id="alertPills">
      ${Object.entries(counts).map(([label, count]) => `
        <div class="pill ${alertsState.filter === label ? 'active' : ''}" data-filter="${label}">
          <span class="pill-dot" style="background:${pillColor(label)}"></span> ${label} (${count})
        </div>
      `).join('')}
    </div>

    <div class="card">
      <div id="alertsTableWrap"></div>
    </div>
  `;

  document.getElementById('alertPills').querySelectorAll('.pill').forEach(p => {
    p.addEventListener('click', () => {
      alertsState.filter = p.dataset.filter;
      alertsState.page = 1;
      renderAlertsPage(main);
    });
  });

  renderAlertsTable();
}

function pillColor(label) {
  return { All: '#3b82f6', Critical: '#ef4444', High: '#f59e0b', Medium: '#f59e0b', Low: '#22c55e' }[label] || '#93a2bc';
}

function renderAlertsTable() {
  const wrap = document.getElementById('alertsTableWrap');
  if (!wrap) return;

  let list = alertsState.data;
  if (alertsState.filter !== 'All') {
    list = list.filter(a => (a.severity || '').toLowerCase() === alertsState.filter.toLowerCase());
  }

  const totalPages = Math.max(1, Math.ceil(list.length / alertsState.pageSize));
  alertsState.page = Math.min(alertsState.page, totalPages);
  const start = (alertsState.page - 1) * alertsState.pageSize;
  const pageItems = list.slice(start, start + alertsState.pageSize);

  if (!pageItems.length) {
    wrap.innerHTML = `<div class="empty-state">No alerts in this category.</div>`;
    return;
  }

  wrap.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Severity</th><th>Alert</th><th>Facility</th><th>Time</th><th>Status</th><th>Action</th></tr></thead>
      <tbody>
        ${pageItems.map(a => `
          <tr>
            <td><span class="badge ${severityBadgeClass(a.severity)}">${a.severity}</span></td>
            <td>${a.anomaly_type}</td>
            <td>${a.facility_code || a.facility_name || '—'}</td>
            <td>${new Date(a.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
            <td><span class="badge ${statusBadgeClass(a.status)}">${a.status || 'New'}</span></td>
            <td><span class="link">View</span></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <div class="pagination">
      <span class="pagination-info">Showing ${start + 1} to ${start + pageItems.length} of ${list.length} alerts</span>
      <div class="page-btn" onclick="changeAlertsPage(-1)">&lsaquo;</div>
      ${Array.from({ length: totalPages }, (_, i) => i + 1).map(p => `
        <div class="page-btn ${p === alertsState.page ? 'active' : ''}" onclick="goToAlertsPage(${p})">${p}</div>
      `).join('')}
      <div class="page-btn" onclick="changeAlertsPage(1)">&rsaquo;</div>
    </div>
  `;
}

function changeAlertsPage(delta) { alertsState.page += delta; renderAlertsTable(); }
function goToAlertsPage(p) { alertsState.page = p; renderAlertsTable(); }
