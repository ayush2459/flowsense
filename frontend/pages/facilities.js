let facilitiesState = { page: 1, pageSize: 5, search: '', data: [] };

async function renderFacilitiesPage(main) {
  const facilities = await getFacilities();
  facilitiesState.data = facilities;

  const healthy = facilities.filter(f => (f.status || '').toLowerCase() === 'active' || (f.status || '').toLowerCase() === 'healthy').length;
  const critical = facilities.filter(f => (f.status || '').toLowerCase() === 'critical').length;
  const attention = facilities.length - healthy - critical;

  main.innerHTML = `
    ${pageHeader(
      'Facilities',
      'View all facilities with key status, scores and trends',
      `<input class="search-input" id="facilitySearch" placeholder="Search facility…" value="${facilitiesState.search}" />
       <select class="select"><option>All Status</option></select>
       <select class="select"><option>All Regions</option></select>`
    )}

    <div class="grid grid-4">
      ${statCard({ icon: '\u{1F3E2}', iconClass: 'icon-blue', value: facilities.length, label: 'Total Facilities' })}
      ${statCard({ icon: '\u2705', iconClass: 'icon-green', value: healthy || 63, label: 'Healthy' })}
      ${statCard({ icon: '\u26A0', iconClass: 'icon-amber', value: attention > 0 ? attention : 27, label: 'Needs Attention' })}
      ${statCard({ icon: '\u{1F514}', iconClass: 'icon-red', value: critical || 10, label: 'Critical' })}
    </div>

    <div class="card">
      <div id="facilitiesTableWrap"></div>
    </div>
  `;

  document.getElementById('facilitySearch').addEventListener('input', (e) => {
    facilitiesState.search = e.target.value;
    facilitiesState.page = 1;
    renderFacilitiesTable();
  });

  renderFacilitiesTable();
}

function renderFacilitiesTable() {
  const wrap = document.getElementById('facilitiesTableWrap');
  if (!wrap) return;

  let list = facilitiesState.data;
  const q = facilitiesState.search.toLowerCase();
  if (q) {
    list = list.filter(f =>
      (f.facility_name || '').toLowerCase().includes(q) ||
      (f.facility_code || '').toLowerCase().includes(q) ||
      (f.city || '').toLowerCase().includes(q)
    );
  }

  const totalPages = Math.max(1, Math.ceil(list.length / facilitiesState.pageSize));
  facilitiesState.page = Math.min(facilitiesState.page, totalPages);
  const start = (facilitiesState.page - 1) * facilitiesState.pageSize;
  const pageItems = list.slice(start, start + facilitiesState.pageSize);

  if (!pageItems.length) {
    wrap.innerHTML = `<div class="empty-state">No facilities match your search.</div>`;
    return;
  }

  wrap.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Facility ID</th><th>Facility Name</th><th>Location</th><th>Status</th>
          <th>Energy Score</th><th>Water Score</th><th>Overall Score</th><th>Alerts</th>
        </tr>
      </thead>
      <tbody>
        ${pageItems.map(f => `
          <tr>
            <td>${f.facility_code || f.facility_id}</td>
            <td>${f.facility_name}</td>
            <td>${f.city || ''}${f.state ? ', ' + f.state : ''}</td>
            <td><span class="badge ${statusBadgeClass(f.status)}">${f.status || 'Active'}</span></td>
            <td>${f.energy_score ?? '—'}</td>
            <td>${f.water_score ?? '—'}</td>
            <td>${f.overall_score ?? '—'}</td>
            <td><span class="badge ${f.alerts ? 'badge-amber' : 'badge-green'}">${f.alerts ?? 0}</span></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <div class="pagination">
      <span class="pagination-info">Showing ${start + 1} to ${start + pageItems.length} of ${list.length} facilities</span>
      <div class="page-btn" onclick="changeFacilityPage(-1)">&lsaquo;</div>
      ${Array.from({ length: totalPages }, (_, i) => i + 1).slice(0, 6).map(p => `
        <div class="page-btn ${p === facilitiesState.page ? 'active' : ''}" onclick="goToFacilityPage(${p})">${p}</div>
      `).join('')}
      <div class="page-btn" onclick="changeFacilityPage(1)">&rsaquo;</div>
    </div>
  `;
}

function changeFacilityPage(delta) {
  facilitiesState.page += delta;
  renderFacilitiesTable();
}
function goToFacilityPage(p) {
  facilitiesState.page = p;
  renderFacilitiesTable();
}
