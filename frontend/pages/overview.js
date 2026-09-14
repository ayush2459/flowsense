// ============================================================
// FlowSense — Realtime Overview
// ============================================================

let overviewRealtimeUnsubscribe = null;

let energyChart = null;
let waterChart = null;

let energyHistory = [];
let waterHistory = [];

const MAX_HISTORY_POINTS = 30;

// ============================================================
// Render Overview
// ============================================================

function renderOverviewPage() {
  const main = document.getElementById("main");

  main.innerHTML = `
    <div id="overviewPage">

      ${pageHeader(
        "Resource Overview",
        "Real-time energy, water and facility intelligence"
      )}

      <!-- ================================================== -->
      <!-- Portfolio Stats -->
      <!-- ================================================== -->

      <div class="stats-grid" id="overviewStats">
        ${loadingHtml()}
      </div>

      <!-- ================================================== -->
      <!-- Efficiency -->
      <!-- ================================================== -->

      <div class="dashboard-grid">

        <section class="card">

          <div class="card-header">

            <div>
              <div class="card-title">
                Energy Efficiency
              </div>

              <div class="card-subtitle">
                Live portfolio score
              </div>
            </div>

            <span
              id="energyLiveStatus"
              class="status-badge status-healthy"
            >
              Connecting
            </span>

          </div>

          <div id="energyGaugeWrap">
            ${gauge("energyGauge", 0, "#22c55e")}
          </div>

        </section>


        <section class="card">

          <div class="card-header">

            <div>
              <div class="card-title">
                Water Efficiency
              </div>

              <div class="card-subtitle">
                Live portfolio score
              </div>
            </div>

            <span
              id="waterLiveStatus"
              class="status-badge status-healthy"
            >
              Connecting
            </span>

          </div>

          <div id="waterGaugeWrap">
            ${gauge("waterGauge", 0, "#3b82f6")}
          </div>

        </section>

      </div>


      <!-- ================================================== -->
      <!-- Realtime Charts -->
      <!-- ================================================== -->

      <div class="dashboard-grid">

        <section class="card">

          <div class="card-header">

            <div>
              <div class="card-title">
                Live Energy Consumption
              </div>

              <div class="card-subtitle">
                Portfolio telemetry
              </div>
            </div>

            <span
              id="energyUpdated"
              class="live-indicator"
            >
              ● LIVE
            </span>

          </div>

          <div class="chart-container">
            <canvas id="energyRealtimeCanvas"></canvas>
          </div>

        </section>


        <section class="card">

          <div class="card-header">

            <div>
              <div class="card-title">
                Live Water Consumption
              </div>

              <div class="card-subtitle">
                Portfolio telemetry
              </div>
            </div>

            <span
              id="waterUpdated"
              class="live-indicator"
            >
              ● LIVE
            </span>

          </div>

          <div class="chart-container">
            <canvas id="waterRealtimeCanvas"></canvas>
          </div>

        </section>

      </div>


      <!-- ================================================== -->
      <!-- Facility Intelligence -->
      <!-- ================================================== -->

      <section class="card">

        <div class="card-header">

          <div>
            <div class="card-title">
              Live Facility Intelligence
            </div>

            <div class="card-subtitle">
              Detection, source mapping and recommendations
            </div>
          </div>

          <span
            id="facilityCountLive"
            class="status-badge status-healthy"
          >
            Connecting
          </span>

        </div>

        <div id="liveFacilityTable">
          ${loadingHtml()}
        </div>

      </section>

    </div>
  `;

  initializeOverviewCharts();

  subscribeOverviewRealtime();
}


// ============================================================
// Realtime Subscription
// ============================================================

function subscribeOverviewRealtime() {

  if (!window.FlowSenseRealtime) {

    console.error(
      "[Overview] FlowSenseRealtime is not available"
    );

    return;
  }

  if (overviewRealtimeUnsubscribe) {
    overviewRealtimeUnsubscribe();
  }

  overviewRealtimeUnsubscribe =
    window.FlowSenseRealtime.subscribe(
      updateOverviewRealtime
    );
}


// ============================================================
// Main Realtime Update
// ============================================================

function updateOverviewRealtime(snapshot) {

  const facilities =
    snapshot.facilities || [];

  if (!facilities.length) {
    return;
  }

  updateOverviewStats(facilities);

  updateOverviewGauges(facilities);

  updateOverviewCharts(facilities);

  updateOverviewFacilityTable(facilities);

  updateOverviewConnectionStatus(snapshot);

}


// ============================================================
// Connection Status
// ============================================================

function updateOverviewConnectionStatus(snapshot) {

  const badge =
    document.getElementById(
      "facilityCountLive"
    );

  if (badge) {

    badge.textContent =
      `${snapshot.facilities.length} Facilities • ${
        snapshot.connected
          ? "LIVE"
          : "OFFLINE"
      }`;

  }

  const now =
    new Date().toLocaleTimeString();

  const energyUpdated =
    document.getElementById(
      "energyUpdated"
    );

  const waterUpdated =
    document.getElementById(
      "waterUpdated"
    );

  if (energyUpdated) {

    energyUpdated.textContent =
      `● LIVE ${now}`;

  }

  if (waterUpdated) {

    waterUpdated.textContent =
      `● LIVE ${now}`;

  }

}


// ============================================================
// Portfolio Calculations
// ============================================================

function calculatePortfolio(facilities) {

  let healthy = 0;
  let attention = 0;
  let critical = 0;

  let energy = 0;
  let water = 0;
  let power = 0;

  let energyScore = 0;
  let waterScore = 0;

  let energyScoreCount = 0;
  let waterScoreCount = 0;

  let energyLoss = 0;
  let waterLoss = 0;

  let anomalyCount = 0;

  facilities.forEach((f) => {

    const status =
      String(
        f.facility_status ||
        f.telemetry_status ||
        "healthy"
      ).toLowerCase();


    // --------------------------------------------------------
    // Status
    // --------------------------------------------------------

    if (status === "critical") {

      critical++;

    } else if (
      status === "attention" ||
      status === "warning"
    ) {

      attention++;

    } else {

      healthy++;

    }


    // --------------------------------------------------------
    // Consumption
    // --------------------------------------------------------

    energy +=
      Number(f.energy_kwh || 0);

    water +=
      Number(f.water_kl || 0);

    power +=
      Number(f.power_kw || 0);


    // --------------------------------------------------------
    // Efficiency
    // --------------------------------------------------------

    if (
      f.energy_score !== undefined &&
      f.energy_score !== null
    ) {

      energyScore +=
        Number(f.energy_score || 0);

      energyScoreCount++;

    }


    if (
      f.water_score !== undefined &&
      f.water_score !== null
    ) {

      waterScore +=
        Number(f.water_score || 0);

      waterScoreCount++;

    }


    // --------------------------------------------------------
    // Loss
    // --------------------------------------------------------

    energyLoss +=
      Number(
        f.estimated_energy_loss_kwh || 0
      );

    waterLoss +=
      Number(
        f.estimated_water_loss_kl || 0
      );


    // --------------------------------------------------------
    // Anomalies
    // --------------------------------------------------------

    anomalyCount +=
      Number(f.anomaly_count || 0);

  });


  return {

    total: facilities.length,

    healthy,

    attention,

    critical,

    energy,

    water,

    power,

    energyScore:
      energyScoreCount
        ? energyScore / energyScoreCount
        : 0,

    waterScore:
      waterScoreCount
        ? waterScore / waterScoreCount
        : 0,

    energyLoss,

    waterLoss,

    anomalyCount

  };

}


// ============================================================
// Stats Cards
// ============================================================

function updateOverviewStats(facilities) {

  const stats =
    calculatePortfolio(facilities);

  const container =
    document.getElementById(
      "overviewStats"
    );

  if (!container) {
    return;
  }

  const total =
    Math.max(stats.total, 1);


  container.innerHTML = `

    ${statCard({
      icon: "🏢",
      iconClass: "icon-cyan",
      value: stats.total,
      label: "Total Facilities",
      delta: "LIVE"
    })}


    ${statCard({
      icon: "✅",
      iconClass: "icon-green",
      value: stats.healthy,
      label: "Healthy",
      delta:
        `${Math.round(
          (stats.healthy / total) * 100
        )}%`
    })}


    ${statCard({
      icon: "⚠",
      iconClass: "icon-amber",
      value: stats.attention,
      label: "Needs Attention",
      delta:
        `${Math.round(
          (stats.attention / total) * 100
        )}%`
    })}


    ${statCard({
      icon: "🔔",
      iconClass: "icon-red",
      value: stats.critical,
      label: "Critical",
      delta:
        `${Math.round(
          (stats.critical / total) * 100
        )}%`
    })}


    ${statCard({
      icon: "⚡",
      iconClass: "icon-cyan",
      value:
        `${stats.energy.toFixed(2)} kWh`,
      label: "Live Energy",
      delta:
        `${stats.power.toFixed(2)} kW`
    })}


    ${statCard({
      icon: "💧",
      iconClass: "icon-blue",
      value:
        `${stats.water.toFixed(2)} kL`,
      label: "Live Water",
      delta:
        `${stats.anomalyCount} anomalies`
    })}

  `;

}


// ============================================================
// Gauges
// ============================================================

function updateOverviewGauges(facilities) {

  const stats =
    calculatePortfolio(facilities);


  drawGauge(
    "energyGauge",
    Math.round(stats.energyScore),
    "#22c55e"
  );


  drawGauge(
    "waterGauge",
    Math.round(stats.waterScore),
    "#3b82f6"
  );


  const energyStatus =
    document.getElementById(
      "energyLiveStatus"
    );

  const waterStatus =
    document.getElementById(
      "waterLiveStatus"
    );


  if (energyStatus) {

    energyStatus.textContent =
      `${Math.round(
        stats.energyScore
      )}% LIVE`;

  }


  if (waterStatus) {

    waterStatus.textContent =
      `${Math.round(
        stats.waterScore
      )}% LIVE`;

  }

}


// ============================================================
// Initialize Charts
// ============================================================

function initializeOverviewCharts() {

  if (typeof Chart === "undefined") {

    console.error(
      "[Overview] Chart.js is not loaded"
    );

    return;
  }


  const energyCanvas =
    document.getElementById(
      "energyRealtimeCanvas"
    );

  const waterCanvas =
    document.getElementById(
      "waterRealtimeCanvas"
    );


  if (!energyCanvas || !waterCanvas) {
    return;
  }


  energyChart =
    new Chart(
      energyCanvas,
      {
        type: "line",

        data: {

          labels: [],

          datasets: [

            {
              label: "Energy kWh",

              data: [],

              tension: 0.35,

              fill: false

            }

          ]

        },

        options: {

          responsive: true,

          maintainAspectRatio: false,

          animation: false,

          plugins: {

            legend: {
              display: false
            }

          },

          scales: {

            y: {
              beginAtZero: false
            }

          }

        }

      }
    );


  waterChart =
    new Chart(
      waterCanvas,
      {
        type: "line",

        data: {

          labels: [],

          datasets: [

            {
              label: "Water kL",

              data: [],

              tension: 0.35,

              fill: false

            }

          ]

        },

        options: {

          responsive: true,

          maintainAspectRatio: false,

          animation: false,

          plugins: {

            legend: {
              display: false
            }

          },

          scales: {

            y: {
              beginAtZero: false
            }

          }

        }

      }
    );

}


// ============================================================
// Update Charts
// ============================================================

function updateOverviewCharts(facilities) {

  if (!energyChart || !waterChart) {
    return;
  }


  const stats =
    calculatePortfolio(facilities);


  const now =
    new Date().toLocaleTimeString();


  // ----------------------------------------------------------
  // Portfolio totals
  // ----------------------------------------------------------

  energyHistory.push({

    time: now,

    value: stats.energy

  });


  waterHistory.push({

    time: now,

    value: stats.water

  });


  // Keep only recent points

  if (
    energyHistory.length >
    MAX_HISTORY_POINTS
  ) {

    energyHistory =
      energyHistory.slice(
        -MAX_HISTORY_POINTS
      );

  }


  if (
    waterHistory.length >
    MAX_HISTORY_POINTS
  ) {

    waterHistory =
      waterHistory.slice(
        -MAX_HISTORY_POINTS
      );

  }


  // ----------------------------------------------------------
  // Energy
  // ----------------------------------------------------------

  energyChart.data.labels =
    energyHistory.map(
      (p) => p.time
    );


  energyChart.data.datasets[0].data =
    energyHistory.map(
      (p) => p.value
    );


  energyChart.update("none");


  // ----------------------------------------------------------
  // Water
  // ----------------------------------------------------------

  waterChart.data.labels =
    waterHistory.map(
      (p) => p.time
    );


  waterChart.data.datasets[0].data =
    waterHistory.map(
      (p) => p.value
    );


  waterChart.update("none");

}


// ============================================================
// Facility Intelligence Table
// ============================================================

function updateOverviewFacilityTable(
  facilities
) {

  const container =
    document.getElementById(
      "liveFacilityTable"
    );

  if (!container) {
    return;
  }


  const priority = {

    critical: 3,

    attention: 2,

    warning: 2,

    healthy: 1

  };


  const sorted =
    [...facilities].sort(
      (a, b) => {

        const aStatus =
          String(
            a.facility_status ||
            a.telemetry_status ||
            "healthy"
          ).toLowerCase();

        const bStatus =
          String(
            b.facility_status ||
            b.telemetry_status ||
            "healthy"
          ).toLowerCase();


        return (
          (priority[bStatus] || 0) -
          (priority[aStatus] || 0)
        );

      }
    );


  container.innerHTML = `

    <div class="table-wrap">

      <table class="data-table">

        <thead>

          <tr>

            <th>Facility</th>

            <th>Status</th>

            <th>Energy</th>

            <th>Water</th>

            <th>Flow</th>

            <th>Pressure</th>

            <th>Anomaly</th>

            <th>Source</th>

            <th>Confidence</th>

          </tr>

        </thead>


        <tbody>

          ${sorted
            .slice(0, 25)
            .map((f) => {

              const status =
                String(
                  f.facility_status ||
                  f.telemetry_status ||
                  "healthy"
                ).toLowerCase();


              const anomaly =
                f.primary_anomaly ||
                f.telemetry_anomaly_type ||
                (
                  f.telemetry_anomaly
                    ? "Anomaly"
                    : null
                );


              const source =
                f.likely_source ||
                f.source_name ||
                (
                  anomaly
                    ? "Detection Engine"
                    : "—"
                );


              let confidence =
                "—";


              if (
                f.confidence !== undefined &&
                f.confidence !== null
              ) {

                confidence =
                  `${Math.round(
                    Number(
                      f.confidence
                    )
                  )}%`;

              }


              return `

                <tr>

                  <td>
                    <strong>
                      ${f.facility_code || "—"}
                    </strong>
                  </td>


                  <td>

                    <span
                      class="status-badge status-${status}"
                    >
                      ${status.toUpperCase()}
                    </span>

                  </td>


                  <td>
                    ${Number(
                      f.energy_kwh || 0
                    ).toFixed(2)}
                    kWh
                  </td>


                  <td>
                    ${Number(
                      f.water_kl || 0
                    ).toFixed(2)}
                    kL
                  </td>


                  <td>
                    ${Number(
                      f.water_flow_lpm || 0
                    ).toFixed(2)}
                    L/min
                  </td>


                  <td>
                    ${Number(
                      f.water_pressure_bar || 0
                    ).toFixed(2)}
                    bar
                  </td>


                  <td>
                    ${
                      anomaly || "Normal"
                    }
                  </td>


                  <td>
                    ${source}
                  </td>


                  <td>
                    ${confidence}
                  </td>

                </tr>

              `;

            })
            .join("")}

        </tbody>

      </table>

    </div>

  `;

}