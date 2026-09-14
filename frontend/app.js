// ============================================================
// FlowSense Application
// Shared Realtime Navigation
// ============================================================

const ROUTES = [
  {
    id: "overview",
    icon: "\u25A6",
    label: "Overview",
    badge: null,
    render: renderOverviewPage
  },
  {
    id: "facilities",
    icon: "\u25A3",
    label: "Facilities",
    badge: null,
    render: renderFacilitiesPage
  },
  {
    id: "energy",
    icon: "\u26A1",
    label: "Energy",
    badge: null,
    render: renderEnergyPage
  },
  {
    id: "water",
    icon: "\uD83D\uDCA7",
    label: "Water",
    badge: null,
    render: renderWaterPage
  },
  {
    id: "alerts",
    icon: "\u26A0",
    label: "Alerts",
    badge: "alertsBadge",
    render: renderAlertsPage
  },
  {
    id: "analytics",
    icon: "\u25A5",
    label: "Analytics",
    badge: null,
    render: renderAnalyticsPage
  },
  {
    id: "aiinsights",
    icon: "\u2728",
    label: "AI Insights",
    badge: null,
    render: renderAIInsightsPage
  },
  {
    id: "reports",
    icon: "\u25A4",
    label: "Reports",
    badge: null,
    render: renderReportsPage
  },
  {
    id: "settings",
    icon: "\u2699",
    label: "Settings",
    badge: null,
    render: renderSettingsPage
  }
];


// ============================================================
// Navigation
// ============================================================

function renderNavigation() {

  const nav =
    document.getElementById("nav");

  if (!nav) {
    return;
  }

  nav.innerHTML = ROUTES.map(route => `

    <a
      href="#${route.id}"
      class="nav-item"
      data-route="${route.id}"
    >

      <span class="nav-icon">
        ${route.icon}
      </span>

      <span class="nav-label">
        ${route.label}
      </span>

      ${
        route.badge
          ? `<span
               id="${route.badge}"
               class="nav-badge"
               style="display:none"
             ></span>`
          : ""
      }

    </a>

  `).join("");

}


// ============================================================
// Current Route
// ============================================================

function getCurrentRoute() {

  const hash =
    window.location.hash
      .replace("#", "")
      .trim();

  return hash || "overview";

}


// ============================================================
// Route Rendering
// ============================================================

function renderRoute() {

  const routeId =
    getCurrentRoute();

  const route =
    ROUTES.find(
      r => r.id === routeId
    ) || ROUTES[0];


  // Active navigation

  document
    .querySelectorAll(".nav-item")
    .forEach(item => {

      item.classList.toggle(
        "active",
        item.dataset.route === route.id
      );

    });


  try {

    route.render();

  } catch (error) {

    console.error(
      `[FlowSense] Failed to render ${route.id}:`,
      error
    );

    const main =
      document.getElementById("main");

    if (main) {

      main.innerHTML = `

        <section class="card">

          <h2>
            Something went wrong
          </h2>

          <p>
            ${error.message}
          </p>

        </section>

      `;

    }

  }

}


// ============================================================
// Realtime Alerts Badge
// ============================================================

function updateAlertsBadgeFromRealtime(
  snapshot
) {

  const badge =
    document.getElementById(
      "alertsBadge"
    );

  if (!badge) {
    return;
  }


  const facilities =
    snapshot.facilities || [];


  let count = 0;


  facilities.forEach(f => {

    count +=
      Number(
        f.anomaly_count || 0
      );

    // Also catch simulator-side anomalies
    // while detection is being processed.

    if (
      f.telemetry_anomaly &&
      Number(f.anomaly_count || 0) === 0
    ) {
      count++;
    }

  });


  if (count > 0) {

    badge.textContent =
      count > 99
        ? "99+"
        : String(count);

    badge.style.display =
      "inline-flex";

  } else {

    badge.style.display =
      "none";

  }

}


// ============================================================
// Realtime App Subscription
// ============================================================

function subscribeAppRealtime() {

  if (!window.FlowSenseRealtime) {

    console.warn(
      "[FlowSense] Realtime engine unavailable"
    );

    return;
  }


  window.FlowSenseRealtime.subscribe(
    updateAlertsBadgeFromRealtime
  );

}


// ============================================================
// Initialization
// ============================================================

function init() {

  renderNavigation();

  window.addEventListener(
    "hashchange",
    renderRoute
  );


  if (!window.location.hash) {

    window.location.hash =
      "#overview";

  } else {

    renderRoute();

  }


  subscribeAppRealtime();

}


window.addEventListener(
  "load",
  init
);