const ROUTES = [
  { id: 'overview',   icon: '\u25A6', label: 'Overview',   badge: null, render: renderOverviewPage },
  { id: 'facilities', icon: '\u{1F3E2}', label: 'Facilities', badge: null, render: renderFacilitiesPage },
  { id: 'energy',     icon: '\u26A1', label: 'Energy',      badge: null, render: renderEnergyPage },
  { id: 'water',      icon: '\u{1F4A7}', label: 'Water',       badge: null, render: renderWaterPage },
  { id: 'alerts',     icon: '\u{1F514}', label: 'Alerts',      badge: 'live', render: renderAlertsPage },
  { id: 'reports',    icon: '\u{1F4C4}', label: 'Reports',     badge: null, render: renderReportsPage },
  { id: 'analytics',  icon: '\u{1F4C8}', label: 'Analytics',   badge: null, render: renderAnalyticsPage },
  { id: 'aiinsights', icon: '\u2728', label: 'AI Insights',  badge: null, render: renderAiInsightsPage },
  { id: 'settings',   icon: '\u2699', label: 'Settings',     badge: null, render: renderSettingsPage },
];

let currentRoute = 'overview';

function renderNav() {
  const nav = document.getElementById('nav');
  nav.innerHTML = ROUTES.map(r => `
    <div class="nav-item ${r.id === currentRoute ? 'active' : ''}" data-route="${r.id}">
      <span class="icon">${r.icon}</span>
      <span>${r.label}</span>
      ${r.badge ? `<span class="nav-badge" id="badge-${r.id}">–</span>` : ''}
    </div>
  `).join('');
  nav.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => navigate(item.dataset.route));
  });
}

async function navigate(routeId) {
  currentRoute = routeId;
  window.location.hash = routeId;
  renderNav();
  const route = ROUTES.find(r => r.id === routeId);
  const main = document.getElementById('main');
  main.innerHTML = loadingHtml('Loading ' + route.label + '…');
  try {
    await route.render(main);
  } catch (e) {
    main.innerHTML = `<div class="error-state">Something went wrong loading this page: ${e.message}</div>`;
    console.error(e);
  }
}

async function updateAlertsBadge() {
  try {
    const anomalies = await getRecentAnomalies();
    const openCount = anomalies.filter(a => (a.status || '').toLowerCase() !== 'resolved').length;
    const badge = document.getElementById('badge-alerts');
    if (badge) badge.textContent = openCount;
  } catch (e) { /* ignore */ }
}

function init() {
  const startRoute = window.location.hash.replace('#', '') || 'overview';
  currentRoute = ROUTES.some(r => r.id === startRoute) ? startRoute : 'overview';
  renderNav();
  navigate(currentRoute);
  updateAlertsBadge();
  setInterval(updateAlertsBadge, 20000);
}

init();
