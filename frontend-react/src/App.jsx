import { useEffect, useMemo, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Navigate,
  useNavigate,
  useParams
} from "react-router-dom";

import {
  Building2,
  Zap,
  Droplets,
  Bell,
  BarChart3,
  Sparkles,
  FileText,
  Cpu,
  Settings,
  Gauge,
  ShieldCheck,
  AlertTriangle,
  Leaf,
  RefreshCw,
  Search,
  ChevronDown,
  Activity,
  Waves,
  CircleDollarSign,
  Menu,
  X,
  Lightbulb
} from "lucide-react";

import {
  AreaChart,
  Area,
  LineChart,
  Line,
  ResponsiveContainer,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip
} from "recharts";

import { api } from "./services/api";
import RealtimeOverview from "./RealtimeOverview";
import { useFlowSense } from "./context/FlowSenseContext";
import "./App.css";

const navItems = [
  ["/", "Overview", Gauge],
  ["/facilities", "Facilities", Building2],
  ["/energy", "Energy", Zap],
  ["/water", "Water", Droplets],
  ["/alerts", "Alerts", Bell],
  ["/reports", "Reports", FileText],
  ["/analytics", "Analytics", BarChart3],
  ["/ai-insights", "AI Insights", Sparkles],
  ["/devices", "Devices", Cpu],
  ["/settings", "Settings", Settings]
];

const num = (v, d = 1) =>
  Number.isFinite(Number(v))
    ? Number(v).toLocaleString("en-IN", {
        maximumFractionDigits: d
      })
    : "0";

const fmtTime = (v) =>
  v
    ? new Date(v).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
      })
    : "—";

function getStatus(facility, anomalies) {
  const rows = anomalies.filter(
    (a) => a.facility_code === facility.facility_code
  );

  if (
    rows.some(
      (a) => String(a.severity).toLowerCase() === "critical"
    )
  ) {
    return "Critical";
  }

  if (rows.length) return "Needs Attention";

  return "Healthy";
}

function Card({ children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {children}
    </section>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  sub,
  tone = "blue"
}) {
  return (
    <Card className="kpi">
      <div className={`kpi-icon ${tone}`}>
        <Icon />
      </div>

      <label>{label}</label>
      <strong>{value}</strong>
      <small className={tone}>{sub}</small>
    </Card>
  );
}

function PanelHead({ icon: Icon, title, sub, to }) {
  const navigate = useNavigate();

  return (
    <div className="panel-head">
      <div>
        <h2>
          <Icon />
          {title}
        </h2>

        <p>{sub}</p>
      </div>

      {to && (
        <button
          type="button"
          className="link"
          onClick={() => navigate(to)}
        >
          View Details →
        </button>
      )}
    </div>
  );
}

function Ring({ value, water = false, label }) {
  const percentage = Math.max(
    0,
    Math.min(100, Number(value) || 0)
  );

  return (
    <div className="ring-wrap">
      <div
        className={`ring ${water ? "water" : ""}`}
        style={{
          "--p": `${percentage * 3.6}deg`
        }}
      >
        <div className="ring-in">
          <b>{Math.round(percentage)}</b>
          <span>/100</span>
        </div>
      </div>

      <small>{label}</small>
    </div>
  );
}

/* =========================
   SHELL
========================= */

function Shell({ anomalies, children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app">
      <aside
        className={`sidebar ${
          mobileOpen ? "open" : ""
        }`}
      >
        <div className="brand">
          <div className="brand-logo">
            <Waves />
          </div>

          <div className="brand-copy">
            <b>FlowSense</b>
            <small>
              IoT Resource Intelligence
            </small>
          </div>

          <button
            type="button"
            className="close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X />
          </button>
        </div>

        <div className="menu-label">
          MAIN MENU
        </div>

        <nav className="sidebar-nav">
          {navItems.map(
            ([to, label, Icon]) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `nav-item ${
                    isActive ? "active" : ""
                  }`
                }
                onClick={() =>
                  setMobileOpen(false)
                }
              >
                <Icon />

                <span>{label}</span>

                {label === "Alerts" &&
                  anomalies.length > 0 && (
                    <em>{anomalies.length}</em>
                  )}
              </NavLink>
            )
          )}
        </nav>

        <div className="quick">
          <Sparkles />

          <div>
            <b>Quick Insight</b>
            <span>
              {anomalies.length
                ? `${anomalies.length} recent anomalies need review`
                : "No recent anomalies"}
            </span>
          </div>
        </div>

        <div className="user">
          <div className="avatar">AG</div>

          <div>
            <b>Admin</b>
            <small>
              FlowSense Control Center
            </small>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="mobile-head">
          <button
            type="button"
            onClick={() =>
              setMobileOpen(true)
            }
            aria-label="Open menu"
          >
            <Menu />
          </button>

          <b>FlowSense</b>

          <button
            type="button"
            onClick={() =>
              window.location.reload()
            }
            aria-label="Refresh"
          >
            <RefreshCw />
          </button>
        </header>

        {children}
      </main>
    </div>
  );
}

/* =========================
   SIMPLE PAGE HEADER
========================= */

function Page({ title, sub, children }) {
  return (
    <div className="page">
      <div className="inner">
        <div className="page-title">
          <div>
            <div className="overline">
              FLOWSENSE / OPERATIONS
            </div>

            <h1>{title}</h1>
            <p>{sub}</p>
          </div>
        </div>

        {children}
      </div>
    </div>
  );
}

/* =========================
   LEGACY OVERVIEW
========================= */

function Overview({
  facilities,
  anomalies,
  selected,
  setSelected,
  onRefresh
}) {
  const [summaries, setSummaries] =
    useState([]);

  const [energy, setEnergy] =
    useState([]);

  const [water, setWater] =
    useState([]);

  const [recon, setRecon] =
    useState([]);

  const navigate = useNavigate();

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        const list = selected
          ? [selected]
          : facilities
              .slice(0, 12)
              .map((f) => f.facility_code);

        const data = await Promise.all(
          list.map((code) =>
            api.summary(code).catch(() => null)
          )
        );

        if (alive) {
          setSummaries(
            data.filter(Boolean)
          );
        }

        if (selected) {
          const [e, w, r] =
            await Promise.all([
              api.energy(selected, 24),
              api.water(selected, 24),
              api.reconciliation(
                selected,
                100
              )
            ]);

          if (alive) {
            setEnergy(
              Array.isArray(e) ? e : []
            );
            setWater(
              Array.isArray(w) ? w : []
            );
            setRecon(
              Array.isArray(r) ? r : []
            );
          }
        }
      } catch (error) {
        console.error(error);
      }
    }

    load();

    return () => {
      alive = false;
    };
  }, [selected, facilities]);

  const energyTotal =
    summaries.reduce(
      (sum, x) =>
        sum + Number(x.energy_kwh || 0),
      0
    );

  const waterTotal =
    summaries.reduce(
      (sum, x) =>
        sum + Number(x.water_kl || 0),
      0
    );

  const loss =
    recon.reduce(
      (sum, x) =>
        sum +
        Number(x.unaccounted_value || 0),
      0
    );

  const energyChart = energy.map((x) => ({
    t: fmtTime(x.reading_time),
    v: Number(x.reading_value) || 0,
    expected:
      (Number(x.reading_value) || 0) *
      0.92
  }));

  const waterChart = water.map((x) => ({
    t: fmtTime(x.reading_time),
    v: Number(x.reading_value) || 0
  }));

  const healthy = facilities.filter(
    (f) =>
      getStatus(f, anomalies) ===
      "Healthy"
  ).length;

  const attention = facilities.filter(
    (f) =>
      getStatus(f, anomalies) ===
      "Needs Attention"
  ).length;

  const critical = facilities.filter(
    (f) =>
      getStatus(f, anomalies) ===
      "Critical"
  ).length;

  return (
    <div className="page">
      <div className="content">
        <div className="page-title">
          <div>
            <div className="overline">
              FLOWSENSE / LEGACY
            </div>

            <h1>Dashboard Overview</h1>

            <p>
              Historical dashboard view
            </p>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={onRefresh}
          >
            <RefreshCw />
            Refresh
          </button>
        </div>

        <div className="facility-row">
          <div className="portfolio">
            <Building2 />
            <span>
              {selected
                ? facilities.find(
                    (f) =>
                      f.facility_code ===
                      selected
                  )?.facility_name
                : "Portfolio / All Facilities"}
            </span>
            <ChevronDown />
          </div>

          <span className="updated">
            Historical REST data
          </span>
        </div>

        <div className="kpis">
          <Kpi
            icon={Building2}
            label="Total Facilities"
            value={facilities.length}
            sub="All locations"
            tone="blue"
          />

          <Kpi
            icon={ShieldCheck}
            label="Healthy"
            value={healthy}
            sub="Current database status"
            tone="green"
          />

          <Kpi
            icon={AlertTriangle}
            label="Needs Attention"
            value={attention}
            sub="Requires review"
            tone="yellow"
          />

          <Kpi
            icon={AlertTriangle}
            label="Critical"
            value={critical}
            sub="Immediate attention"
            tone="red"
          />
        </div>

        <div className="main-grid">
          <Card>
            <PanelHead
              icon={Zap}
              title="Energy Overview"
              sub="Historical consumption"
              to="/energy"
            />

            <div className="score-row">
              <Ring
                value={81}
                label="Energy Efficiency Score"
              />

              <div className="metrics">
                <div>
                  <span>
                    Total Consumption
                  </span>
                  <b>
                    {num(energyTotal)} kWh
                  </b>
                </div>

                <div>
                  <span>
                    Expected Consumption
                  </span>
                  <b>
                    {num(
                      energyTotal * 0.92
                    )}{" "}
                    kWh
                  </b>
                </div>

                <div>
                  <span>
                    Excess Consumption
                  </span>
                  <b className="red">
                    {num(
                      energyTotal * 0.08
                    )}{" "}
                    kWh
                  </b>
                </div>
              </div>
            </div>

            <div className="chart">
              <ResponsiveContainer>
                <AreaChart
                  data={energyChart}
                >
                  <CartesianGrid
                    stroke="#1c2d43"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="t"
                    stroke="#61748e"
                  />

                  <YAxis
                    stroke="#61748e"
                  />

                  <Tooltip />

                  <Area
                    dataKey="v"
                    stroke="#31aaff"
                    fill="#31aaff"
                    fillOpacity=".12"
                  />

                  <Line
                    dataKey="expected"
                    stroke="#f2c84b"
                    strokeDasharray="5 5"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card>
            <PanelHead
              icon={Droplets}
              title="Water Overview"
              sub="Historical water consumption"
              to="/water"
            />

            <div className="score-row">
              <Ring
                value={76}
                water
                label="Water Efficiency Score"
              />

              <div className="metrics">
                <div>
                  <span>Water Input</span>
                  <b>
                    {num(
                      waterTotal * 1000,
                      0
                    )}{" "}
                    L
                  </b>
                </div>

                <div>
                  <span>Water Loss</span>
                  <b className="red">
                    {num(loss, 2)} kL
                  </b>
                </div>

                <div>
                  <span>Reuse Rate</span>
                  <b className="green">
                    67.3%
                  </b>
                </div>
              </div>
            </div>

            <div className="chart">
              <ResponsiveContainer>
                <LineChart
                  data={waterChart}
                >
                  <CartesianGrid
                    stroke="#1c2d43"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="t"
                    stroke="#61748e"
                  />

                  <YAxis
                    stroke="#61748e"
                  />

                  <Tooltip />

                  <Line
                    dataKey="v"
                    stroke="#2cc9ed"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card>
            <PanelHead
              icon={BarChart3}
              title="Resource Efficiency"
              sub="Portfolio health"
              to="/analytics"
            />

            <div className="radar">
              <div>
                ENERGY
                <br />
                <b>81</b>
              </div>

              <div>
                WATER
                <br />
                <b>76</b>
              </div>

              <div>
                RECOVERY
                <br />
                <b>84</b>
              </div>

              <div>
                REUSE
                <br />
                <b>67</b>
              </div>

              <div>
                SUSTAINABILITY
                <br />
                <b>79</b>
              </div>
            </div>
          </Card>

          <Card>
            <PanelHead
              icon={Bell}
              title="Critical Alerts"
              sub={`${anomalies.length} detected issues`}
              to="/alerts"
            />

            <div className="alerts">
              {anomalies
                .slice(0, 6)
                .map((a, i) => (
                  <button
                    type="button"
                    className="alert"
                    key={
                      a.anomaly_id ||
                      `${a.facility_code}-${i}`
                    }
                    onClick={() =>
                      navigate(
                        `/facilities/${a.facility_code}`
                      )
                    }
                  >
                    <div
                      className={`alert-icon ${
                        String(
                          a.severity
                        ).toLowerCase() ===
                        "critical"
                          ? "critical"
                          : ""
                      }`}
                    >
                      <AlertTriangle />
                    </div>

                    <div>
                      <b>
                        {a.anomaly_type}
                      </b>

                      <span>
                        {a.facility_code} ·{" "}
                        {a.description ||
                          a.sensor_name ||
                          "Detected anomaly"}
                      </span>
                    </div>

                    <time>
                      {fmtTime(
                        a.detected_at
                      )}
                    </time>
                  </button>
                ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

/* =========================
   FACILITIES
========================= */

function Facilities({
  facilities,
  anomalies
}) {
  const navigate = useNavigate();
  const [query, setQuery] =
    useState("");

  const list = useMemo(() => {
    const q = query
      .trim()
      .toLowerCase();

    if (!q) return facilities;

    return facilities.filter((f) =>
      `${f.facility_name} ${f.facility_code} ${f.city} ${f.state}`
        .toLowerCase()
        .includes(q)
    );
  }, [facilities, query]);

  return (
    <Page
      title="Facilities"
      sub="Every connected facility in the FlowSense portfolio"
    >
      <div className="page-toolbar">
        <div className="search wide">
          <Search />
          <input
            value={query}
            onChange={(e) =>
              setQuery(e.target.value)
            }
            placeholder="Search facilities..."
          />
        </div>

        <span className="result-count">
          {list.length} facilities
        </span>
      </div>

      <Card className="table-card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Facility</th>
                <th>Type</th>
                <th>Location</th>
                <th>Status</th>
                <th>Alerts</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {list.map((f) => (
                <tr
                  key={f.facility_code}
                >
                  <td>
                    <b>{f.facility_name}</b>
                    <small>
                      {f.facility_code}
                    </small>
                  </td>

                  <td>
                    {f.facility_type ||
                      "Facility"}
                  </td>

                  <td>
                    {f.city}, {f.state}
                  </td>

                  <td>
                    <span
                      className={`status ${getStatus(
                        f,
                        anomalies
                      )
                        .toLowerCase()
                        .replaceAll(
                          " ",
                          "-"
                        )}`}
                    >
                      {getStatus(
                        f,
                        anomalies
                      )}
                    </span>
                  </td>

                  <td>
                    {
                      anomalies.filter(
                        (a) =>
                          a.facility_code ===
                          f.facility_code
                      ).length
                    }
                  </td>

                  <td>
                    <button
                      type="button"
                      className="link"
                      onClick={() =>
                        navigate(
                          `/facilities/${f.facility_code}`
                        )
                      }
                    >
                      Open →
                    </button>
                  </td>
                </tr>
              ))}

              {!list.length && (
                <tr>
                  <td
                    colSpan="6"
                    className="no-results"
                  >
                    No facilities match your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
}

/* =========================
   RESOURCE PAGES
========================= */

function Resource({
  type,
  facilities
}) {
  const {
    facilityList,
    getHistory,
    totals,
    connection,
    lastTick
  } = useFlowSense();

  const [selected, setSelected] = useState("all");
  const [history, setHistory] = useState([]);

  const isEnergy = type === "energy";

  useEffect(() => {
    const buildHistory = () => {
      if (selected === "all") {
        const points = {};

        facilityList.forEach((facility) => {
          const rows = getHistory(facility.facility_code);

          rows.forEach((row) => {
            const date = new Date(row.timestamp);

            if (Number.isNaN(date.getTime())) {
              return;
            }

            // Group readings from the same simulator round
            // into one portfolio point.
            const bucket =
              Math.floor(date.getTime() / 1000) * 1000;

            const key = new Date(bucket).toISOString();

            if (!points[key]) {
              points[key] = {
                timestamp: key,
                energy_kwh: 0,
                water_kl: 0,
                power_kw: 0,
                water_flow_lpm: 0
              };
            }

            points[key].energy_kwh +=
              Number(row.energy_kwh) || 0;

            points[key].water_kl +=
              Number(row.water_kl) || 0;

            points[key].power_kw +=
              Number(row.power_kw) || 0;

            points[key].water_flow_lpm +=
              Number(row.water_flow_lpm) || 0;
          });
        });

        setHistory(
          Object.values(points)
            .sort(
              (a, b) =>
                new Date(a.timestamp) -
                new Date(b.timestamp)
            )
            .slice(-60)
        );

        return;
      }

      const rows = getHistory(selected) || [];

      setHistory(
        [...rows]
          .slice(-60)
          .sort(
            (a, b) =>
              new Date(a.timestamp) -
              new Date(b.timestamp)
          )
      );
    };

    buildHistory();
  }, [selected, facilityList, lastTick]);

  const rows = facilityList
    .map((facility) => ({
      ...facility,

      energy:
        Number(facility.energy_kwh) || 0,

      water:
        Number(facility.water_kl) || 0,

      power:
        Number(facility.power_kw) || 0,

      flow:
        Number(facility.water_flow_lpm) || 0,

      pressure:
        Number(facility.water_pressure_bar) || 0
    }))
    .sort((a, b) =>
      (a.facility_name || "").localeCompare(
        b.facility_name || ""
      )
    );

  const selectedFacility =
    selected === "all"
      ? null
      : rows.find(
          (facility) =>
            facility.facility_code === selected
        );

  const chartData = history.map((row) => ({
    time: fmtTime(row.timestamp),

    energy:
      Number(row.energy_kwh) || 0,

    water:
      Number(row.water_kl) || 0,

    power:
      Number(row.power_kw) || 0,

    flow:
      Number(row.water_flow_lpm) || 0
  }));

  const displayedEnergy = selectedFacility
    ? selectedFacility.energy
    : totals.energy;

  const displayedWater = selectedFacility
    ? selectedFacility.water
    : totals.water;

  const displayedPower = selectedFacility
    ? selectedFacility.power
    : totals.power;

  const displayedFlow = selectedFacility
    ? selectedFacility.flow
    : rows.reduce(
        (sum, facility) =>
          sum + facility.flow,
        0
      );

  const displayedPressure = selectedFacility
    ? selectedFacility.pressure
    : rows.length
      ? rows.reduce(
          (sum, facility) =>
            sum + facility.pressure,
          0
        ) / rows.length
      : 0;

  const expectedEnergy = selectedFacility
    ? Number(
        selectedFacility.expected_energy_kwh
      ) || 320
    : rows.reduce(
        (sum, facility) =>
          sum +
          (Number(
            facility.expected_energy_kwh
          ) || 320),
        0
      );

  const expectedWater = selectedFacility
    ? Number(
        selectedFacility.expected_water_kl
      ) || 30
    : rows.reduce(
        (sum, facility) =>
          sum +
          (Number(
            facility.expected_water_kl
          ) || 30),
        0
      );

  const energyExcess = Math.max(
    0,
    displayedEnergy - expectedEnergy
  );

  const waterLoss = selectedFacility
    ? Number(
        selectedFacility.estimated_water_loss_kl
      ) || 0
    : totals.waterLoss;

  const latestRows = selectedFacility
    ? [selectedFacility]
    : rows;

  return (
    <Page
      title={
        isEnergy
          ? "Energy Monitoring"
          : "Water Monitoring"
      }
      sub={
        isEnergy
          ? "Realtime energy consumption, demand and facility performance"
          : "Realtime water consumption, flow, pressure and facility performance"
      }
    >
      <div className="page-toolbar">
        <div className="selectbox">
          <Building2 />

          <select
            value={selected}
            onChange={(event) =>
              setSelected(event.target.value)
            }
          >
            <option value="all">
              All Facilities
            </option>

            {rows.map((facility) => (
              <option
                key={facility.facility_code}
                value={facility.facility_code}
              >
                {facility.facility_name} ·{" "}
                {facility.facility_code}
              </option>
            ))}
          </select>
        </div>

        <span
          className={`status ${
            connection === "live"
              ? "healthy"
              : "attention"
          }`}
        >
          {connection === "live"
            ? "● Live"
            : "● Reconnecting"}
        </span>
      </div>

      <div className="kpis">
        <Kpi
          icon={isEnergy ? Zap : Droplets}
          label={
            isEnergy
              ? "Live Energy"
              : "Live Water"
          }
          value={
            isEnergy
              ? `${num(displayedEnergy)} kWh`
              : `${num(displayedWater, 2)} kL`
          }
          sub={
            selectedFacility
              ? selectedFacility.facility_name
              : "All connected facilities"
          }
          tone={
            isEnergy
              ? "blue"
              : "cyan"
          }
        />

        <Kpi
          icon={
            isEnergy
              ? Activity
              : Waves
          }
          label={
            isEnergy
              ? "Power Demand"
              : "Water Flow"
          }
          value={
            isEnergy
              ? `${num(displayedPower)} kW`
              : `${num(displayedFlow)} L/min`
          }
          sub="Realtime IoT reading"
          tone="green"
        />

        <Kpi
          icon={
            isEnergy
              ? AlertTriangle
              : Activity
          }
          label={
            isEnergy
              ? "Excess Consumption"
              : "Water Loss"
          }
          value={
            isEnergy
              ? `${num(energyExcess)} kWh`
              : `${num(waterLoss, 2)} kL`
          }
          sub={
            isEnergy
              ? "Above expected baseline"
              : "Estimated unaccounted usage"
          }
          tone={
            (
              isEnergy
                ? energyExcess
                : waterLoss
            ) > 0
              ? "red"
              : "green"
          }
        />

        <Kpi
          icon={
            isEnergy
              ? Gauge
              : Waves
          }
          label={
            isEnergy
              ? "Expected"
              : "Pressure"
          }
          value={
            isEnergy
              ? `${num(expectedEnergy)} kWh`
              : `${num(displayedPressure, 2)} bar`
          }
          sub="Current operating baseline"
          tone="yellow"
        />
      </div>

      <Card className="large-chart">
        <div className="panel-head">
          <div>
            <h2>
              {isEnergy
                ? "Realtime Energy Consumption"
                : "Realtime Water Flow"}
            </h2>

            <p>
              {selectedFacility
                ? selectedFacility.facility_name
                : "All facilities"}{" "}
              · live WebSocket history
            </p>
          </div>

          <span className="updated">
            {lastTick
              ? `Updated ${fmtTime(lastTick)}`
              : "Waiting for telemetry..."}
          </span>
        </div>

        <div className="chart">
          <ResponsiveContainer>
            <LineChart data={chartData}>
              <CartesianGrid
                stroke="#1c2d43"
                vertical={false}
              />

              <XAxis
                dataKey="time"
                stroke="#61748e"
              />

              <YAxis
                stroke="#61748e"
              />

              <Tooltip />

              <Line
                type="monotone"
                dataKey={
                  isEnergy
                    ? "energy"
                    : "flow"
                }
                stroke={
                  isEnergy
                    ? "#31aaff"
                    : "#2cc9ed"
                }
                dot={false}
                strokeWidth={2}
              />

              {isEnergy && (
                <Line
                  type="monotone"
                  dataKey="power"
                  stroke="#f2c84b"
                  dot={false}
                  strokeWidth={1.5}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card className="table-card">
        <div className="panel-head">
          <div>
            <h2>
              {isEnergy
                ? "Live Energy Readings"
                : "Live Water Readings"}
            </h2>

            <p>
              Latest realtime readings from{" "}
              {latestRows.length} facilities
            </p>
          </div>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Facility</th>
                <th>Status</th>

                {isEnergy ? (
                  <>
                    <th>Energy</th>
                    <th>Expected</th>
                    <th>Power</th>
                    <th>Excess</th>
                  </>
                ) : (
                  <>
                    <th>Water</th>
                    <th>Flow</th>
                    <th>Pressure</th>
                    <th>Loss</th>
                  </>
                )}

                <th>Updated</th>
              </tr>
            </thead>

            <tbody>
              {latestRows.map((facility) => {
                const excess = Math.max(
                  0,
                  facility.energy -
                    (
                      Number(
                        facility.expected_energy_kwh
                      ) || 320
                    )
                );

                const loss =
                  Number(
                    facility.estimated_water_loss_kl
                  ) || 0;

                return (
                  <tr
                    key={
                      facility.facility_code
                    }
                  >
                    <td>
                      <b>
                        {facility.facility_name ||
                          facility.facility_code}
                      </b>

                      <small>
                        {facility.facility_code}
                      </small>
                    </td>

                    <td>
                      <span
                        className={`status ${String(
                          facility.facility_status ||
                            "healthy"
                        )
                          .toLowerCase()
                          .replaceAll(
                            " ",
                            "-"
                          )}`}
                      >
                        {facility.facility_status ||
                          "healthy"}
                      </span>
                    </td>

                    {isEnergy ? (
                      <>
                        <td>
                          {num(
                            facility.energy
                          )}{" "}
                          kWh
                        </td>

                        <td>
                          {num(
                            Number(
                              facility.expected_energy_kwh
                            ) || 320
                          )}{" "}
                          kWh
                        </td>

                        <td>
                          {num(
                            facility.power
                          )}{" "}
                          kW
                        </td>

                        <td
                          className={
                            excess > 0
                              ? "red"
                              : "green"
                          }
                        >
                          {num(excess)} kWh
                        </td>
                      </>
                    ) : (
                      <>
                        <td>
                          {num(
                            facility.water,
                            2
                          )}{" "}
                          kL
                        </td>

                        <td>
                          {num(
                            facility.flow
                          )}{" "}
                          L/min
                        </td>

                        <td>
                          {num(
                            facility.pressure,
                            2
                          )}{" "}
                          bar
                        </td>

                        <td
                          className={
                            loss > 0
                              ? "red"
                              : "green"
                          }
                        >
                          {num(loss, 2)} kL
                        </td>
                      </>
                    )}

                    <td>
                      {fmtTime(
                        facility.timestamp
                      )}
                    </td>
                  </tr>
                );
              })}

              {!latestRows.length && (
                <tr>
                  <td
                    colSpan={7}
                    className="no-results"
                  >
                    Waiting for realtime facility
                    telemetry...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
}
/* =========================
   ALERTS
========================= */

function Alerts({ anomalies }) {
  const navigate = useNavigate();

  return (
    <Page
      title="Alerts & Anomalies"
      sub="Detected abnormal energy, water and equipment conditions"
    >
      <Card className="table-card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Issue</th>
                <th>Facility</th>
                <th>Source</th>
                <th>Deviation</th>
                <th>Detected</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {anomalies.map((a, i) => (
                <tr
                  key={
                    a.anomaly_id || i
                  }
                >
                  <td>
                    <span
                      className={`status ${String(
                        a.severity
                      ).toLowerCase()}`}
                    >
                      {a.severity}
                    </span>
                  </td>

                  <td>
                    <b>{a.anomaly_type}</b>
                    <small>
                      {a.description ||
                        "Detected anomaly"}
                    </small>
                  </td>

                  <td>
                    {a.facility_code}
                  </td>

                  <td>
                    {a.source_name ||
                      a.sensor_name ||
                      "IoT"}
                  </td>

                  <td>
                    {num(
                      a.deviation_percent
                    )}
                    %
                  </td>

                  <td>
                    {a.detected_at
                      ? new Date(
                          a.detected_at
                        ).toLocaleString()
                      : "—"}
                  </td>

                  <td>
                    <button
                      type="button"
                      className="link"
                      onClick={() =>
                        navigate(
                          `/facilities/${a.facility_code}`
                        )
                      }
                    >
                      Investigate →
                    </button>
                  </td>
                </tr>
              ))}

              {!anomalies.length && (
                <tr>
                  <td
                    colSpan="7"
                    className="no-results"
                  >
                    No anomalies detected.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
}

/* =========================
   FACILITY DETAIL
========================= */

function Detail({
  facilities,
  anomalies
}) {
  const { code } = useParams();

  const facility = facilities.find(
    (f) => f.facility_code === code
  );

  const [summary, setSummary] =
    useState(null);

  const [reconciliation, setReconciliation] =
    useState([]);

  useEffect(() => {
    if (!code) return;

    let alive = true;

    Promise.all([
      api.summary(code),
      api.reconciliation(code, 50)
    ])
      .then(([s, r]) => {
        if (!alive) return;

        setSummary(s);
        setReconciliation(
          Array.isArray(r) ? r : []
        );
      })
      .catch(() => {
        if (!alive) return;
        setSummary(null);
        setReconciliation([]);
      });

    return () => {
      alive = false;
    };
  }, [code]);

  if (!facility) {
    return (
      <Page
        title="Facility Not Found"
        sub="The selected facility is not available."
      >
        <Card className="empty big">
          <AlertTriangle />
          <h2>
            Facility unavailable
          </h2>
          <p>
            Check the facility code and try
            again.
          </p>
        </Card>
      </Page>
    );
  }

  const alertCount =
    anomalies.filter(
      (a) =>
        a.facility_code === code
    ).length;

  return (
    <Page
      title={facility.facility_name}
      sub={`${facility.facility_code} · ${facility.city}, ${facility.state}`}
    >
      <div className="detail-grid">
        <Kpi
          icon={Zap}
          label="Energy"
          value={`${num(
            summary?.energy_kwh
          )} kWh`}
          sub="Latest reading"
          tone="blue"
        />

        <Kpi
          icon={Droplets}
          label="Water"
          value={`${num(
            summary?.water_kl,
            2
          )} kL`}
          sub="Latest reading"
          tone="cyan"
        />

        <Kpi
          icon={AlertTriangle}
          label="Alerts"
          value={alertCount}
          sub="Detected events"
          tone="red"
        />

        <Kpi
          icon={Cpu}
          label="IoT Device"
          value={
            summary?.iot_device ||
            "Connected"
          }
          sub="Facility device"
          tone="green"
        />
      </div>

      <Card>
        <PanelHead
          icon={Activity}
          title="Resource Reconciliation"
          sub="Main meter vs IoT-observed resource usage"
        />

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Resource</th>
                <th>Main Meter</th>
                <th>Observed</th>
                <th>Unaccounted</th>
                <th>%</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {reconciliation
                .slice(0, 20)
                .map((x, i) => (
                  <tr key={i}>
                    <td>
                      {x.resource_type}
                    </td>

                    <td>
                      {num(
                        x.main_meter_value
                      )}
                    </td>

                    <td>
                      {num(
                        x.observed_iot_value
                      )}
                    </td>

                    <td>
                      {num(
                        x.unaccounted_value
                      )}
                    </td>

                    <td>
                      {num(
                        x.unaccounted_percent
                      )}
                      %
                    </td>

                    <td>
                      {x.status}
                    </td>
                  </tr>
                ))}

              {!reconciliation.length && (
                <tr>
                  <td
                    colSpan="6"
                    className="no-results"
                  >
                    No reconciliation records
                    available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
}

/* =========================
   FUNCTIONAL WORKSPACES
========================= */

function Analytics({ facilities }) {
  const {
    facilityList,
    alerts,
    connection,
    lastTick,
    getHistory
  } = useFlowSense();

  const [selectedFacility, setSelectedFacility] =
    useState("all");

  const [range, setRange] =
    useState("24h");

  const [view, setView] =
    useState("energy");

  const liveFacilities =
    facilityList?.length
      ? facilityList
      : facilities || [];

  const selectedFacilities =
    selectedFacility === "all"
      ? liveFacilities
      : liveFacilities.filter(
          (f) =>
            f.facility_code === selectedFacility
        );

  const historyRows = [];

  selectedFacilities.forEach((facility) => {
    const history =
      getHistory(facility.facility_code) || [];

    history.forEach((row) => {
      historyRows.push({
        ...row,
        facility_code:
          facility.facility_code,
        facility_name:
          facility.facility_name ||
          facility.name ||
          facility.facility_code
      });
    });
  });

  const rangeMs = {
    "1h": 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000
  }[range];

  const now = Date.now();

  const filteredRows =
    historyRows
      .filter((row) => {
        const timestamp =
          new Date(row.timestamp).getTime();

        return (
          Number.isFinite(timestamp) &&
          now - timestamp <= rangeMs
        );
      })
      .sort(
        (a, b) =>
          new Date(a.timestamp) -
          new Date(b.timestamp)
      );

  const chartRows =
    filteredRows.slice(-120).map((row) => ({
      ...row,
      time: fmtTime(row.timestamp),
      energy:
        Number(row.energy_kwh) || 0,
      expectedEnergy:
        Number(row.expected_energy_kwh) || 0,
      water:
        Number(row.water_kl) || 0,
      expectedWater:
        Number(row.expected_water_kl) || 0,
      power:
        Number(row.power_kw) || 0,
      flow:
        Number(row.water_flow_lpm) || 0,
      pressure:
        Number(row.water_pressure_bar) || 0,
      energyLoss:
        Number(
          row.estimated_energy_loss_kwh
        ) || 0,
      waterLoss:
        Number(
          row.estimated_water_loss_kl
        ) || 0
    }));

  const latestRows =
    selectedFacilities.map((facility) => {
      const history =
        getHistory(
          facility.facility_code
        ) || [];

      return {
        facility,
        latest:
          history.length
            ? history[history.length - 1]
            : null
      };
    });

  const latestEnergy =
    latestRows.reduce(
      (sum, item) =>
        sum +
        (Number(
          item.latest?.energy_kwh
        ) || 0),
      0
    );

  const latestExpectedEnergy =
    latestRows.reduce(
      (sum, item) =>
        sum +
        (Number(
          item.latest
            ?.expected_energy_kwh
        ) || 0),
      0
    );

  const latestWater =
    latestRows.reduce(
      (sum, item) =>
        sum +
        (Number(
          item.latest?.water_kl
        ) || 0),
      0
    );

  const latestExpectedWater =
    latestRows.reduce(
      (sum, item) =>
        sum +
        (Number(
          item.latest
            ?.expected_water_kl
        ) || 0),
      0
    );

  const energyLoss =
    latestRows.reduce(
      (sum, item) =>
        sum +
        (Number(
          item.latest
            ?.estimated_energy_loss_kwh
        ) || 0),
      0
    );

  const waterLoss =
    latestRows.reduce(
      (sum, item) =>
        sum +
        (Number(
          item.latest
            ?.estimated_water_loss_kl
        ) || 0),
      0
    );

  const avgPower =
    latestRows.length
      ? latestRows.reduce(
          (sum, item) =>
            sum +
            (Number(
              item.latest?.power_kw
            ) || 0),
          0
        ) / latestRows.length
      : 0;

  const avgFlow =
    latestRows.length
      ? latestRows.reduce(
          (sum, item) =>
            sum +
            (Number(
              item.latest
                ?.water_flow_lpm
            ) || 0),
          0
        ) / latestRows.length
      : 0;

  const energyVariance =
    latestEnergy -
    latestExpectedEnergy;

  const waterVariance =
    latestWater -
    latestExpectedWater;

  const relevantAlerts =
    alerts.filter(
      (alert) =>
        selectedFacility === "all" ||
        alert.facility_code ===
          selectedFacility
    );

  const topDrivers =
    latestRows
      .map(({ facility, latest }) => {
        const energy =
          Number(facility?.energy_kwh) ||
          Number(latest?.energy_kwh) ||
          0;

        const expectedEnergy =
          Number(facility?.expected_energy_kwh) ||
          Number(latest?.expected_energy_kwh) ||
          0;

        const power =
          Number(facility?.power_kw) ||
          Number(latest?.power_kw) ||
          0;

        const reportedLoss =
          Number(
            facility?.estimated_energy_loss_kwh
          );

        const calculatedExcess = Math.max(
          0,
          energy - expectedEnergy
        );

        const energyLoss =
          Number.isFinite(reportedLoss) && reportedLoss > 0
            ? Math.max(0, reportedLoss)
            : calculatedExcess;

        return {
          facility,
          power,
          energy,
          expectedEnergy,
          energyLoss,

          // Live driver score:
          // use actual excess when present,
          // otherwise use current power demand.
          driverScore:
            energyLoss > 0
              ? energyLoss
              : power
        };
      })
      .sort(
        (a, b) =>
          b.driverScore - a.driverScore
      )
      .slice(0, 5);

  return (
    <Page
      title="Analytics"
      sub="Historical patterns, energy drivers, correlations and operating-condition insights"
    >
      <div className="analytics-controls">
        <select
          value={selectedFacility}
          onChange={(e) =>
            setSelectedFacility(
              e.target.value
            )
          }
        >
          <option value="all">
            All Facilities
          </option>

          {liveFacilities.map(
            (facility) => (
              <option
                key={
                  facility.facility_code
                }
                value={
                  facility.facility_code
                }
              >
                {facility.facility_name ||
                  facility.name ||
                  facility.facility_code}
              </option>
            )
          )}
        </select>

        <select
          value={range}
          onChange={(e) =>
            setRange(e.target.value)
          }
        >
          <option value="1h">
            Last 1 Hour
          </option>
          <option value="6h">
            Last 6 Hours
          </option>
          <option value="24h">
            Last 24 Hours
          </option>
          <option value="7d">
            Last 7 Days
          </option>
        </select>

        <div className="analytics-tabs">
          <button
            className={
              view === "energy"
                ? "active"
                : ""
            }
            onClick={() =>
              setView("energy")
            }
          >
            Energy Analytics
          </button>

          <button
            className={
              view === "water"
                ? "active"
                : ""
            }
            onClick={() =>
              setView("water")
            }
          >
            Water Analytics
          </button>

          <button
            className={
              view === "correlation"
                ? "active"
                : ""
            }
            onClick={() =>
              setView("correlation")
            }
          >
            Correlation
          </button>
        </div>

        <div className="analytics-live">
          <span
            className={
              connection === "live"
                ? "live-dot"
                : "live-dot muted"
            }
          />
          {connection === "live"
            ? "LIVE"
            : "RECONNECTING"}

          <small>
            Updated {fmtTime(lastTick)}
          </small>
        </div>
      </div>

      <div className="analytics-kpis">
        <Card>
          <PanelHead
            icon={Zap}
            title="Energy"
            sub="Current live state"
          />

          <strong className="analytics-value">
            {num(latestEnergy, 1)}
            <small> kWh</small>
          </strong>

          <div className="analytics-meta">
            Expected{" "}
            {num(
              latestExpectedEnergy,
              1
            )}{" "}
            kWh
          </div>
        </Card>

        <Card>
          <PanelHead
            icon={Droplets}
            title="Water"
            sub="Current live state"
          />

          <strong className="analytics-value">
            {num(latestWater, 1)}
            <small> kL</small>
          </strong>

          <div className="analytics-meta">
            Expected{" "}
            {num(
              latestExpectedWater,
              1
            )}{" "}
            kL
          </div>
        </Card>

        <Card>
          <PanelHead
            icon={Activity}
            title="Power"
            sub="Live average"
          />

          <strong className="analytics-value">
            {num(avgPower, 1)}
            <small> kW</small>
          </strong>

          <div className="analytics-meta">
            Flow{" "}
            {num(avgFlow, 1)} L/min
          </div>
        </Card>

        <Card>
          <PanelHead
            icon={AlertTriangle}
            title="Anomaly Context"
            sub="Current monitoring window"
          />

          <strong className="analytics-value">
            {relevantAlerts.length}
          </strong>

          <div className="analytics-meta">
            Energy variance{" "}
            {num(
              energyVariance,
              1
            )}{" "}
            kWh
          </div>
        </Card>
      </div>

      <div className="analytics-main-grid">
        <Card className="analytics-chart-card">
          <PanelHead
            icon={
              view === "water"
                ? Droplets
                : view === "correlation"
                ? Activity
                : Zap
            }
            title={
              view === "water"
                ? "Water Pattern"
                : view === "correlation"
                ? "Energy & Operating Conditions"
                : "Energy Pattern"
            }
            sub="Live telemetry history"
          />

          <div className="analytics-chart">
            <ResponsiveContainer
              width="100%"
              height={320}
            >
              <LineChart
                data={chartRows}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="time"
                  minTickGap={30}
                />

                <YAxis />

                <Tooltip />

                {view === "water" ? (
                  <>
                    <Line
                      type="monotone"
                      dataKey="water"
                      name="Water"
                      dot={false}
                      strokeWidth={2}
                    />

                    <Line
                      type="monotone"
                      dataKey="expectedWater"
                      name="Expected"
                      dot={false}
                      strokeWidth={2}
                    />

                    <Line
                      type="monotone"
                      dataKey="flow"
                      name="Flow L/min"
                      dot={false}
                      strokeWidth={1.5}
                    />
                  </>
                ) : view === "correlation" ? (
                  <>
                    <Line
                      type="monotone"
                      dataKey="energy"
                      name="Energy"
                      dot={false}
                      strokeWidth={2}
                    />

                    <Line
                      type="monotone"
                      dataKey="power"
                      name="Power kW"
                      dot={false}
                      strokeWidth={2}
                    />
                  </>
                ) : (
                  <>
                    <Line
                      type="monotone"
                      dataKey="energy"
                      name="Actual"
                      dot={false}
                      strokeWidth={2}
                    />

                    <Line
                      type="monotone"
                      dataKey="expectedEnergy"
                      name="Expected"
                      dot={false}
                      strokeWidth={2}
                    />

                    <Line
                      type="monotone"
                      dataKey="power"
                      name="Power kW"
                      dot={false}
                      strokeWidth={1.5}
                    />
                  </>
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="analytics-insight-card">
          <PanelHead
            icon={Sparkles}
            title="Analytics Insights"
            sub="Derived from measured telemetry"
          />

          <div className="analytics-insights">
            <div>
              <b>Energy variance</b>
              <span>
                {energyVariance > 0
                  ? `${num(
                      energyVariance,
                      1
                    )} kWh above expected`
                  : "At or below expected"}
              </span>
            </div>

            <div>
              <b>Water variance</b>
              <span>
                {waterVariance > 0
                  ? `${num(
                      waterVariance,
                      1
                    )} kL above expected`
                  : "At or below expected"}
              </span>
            </div>

            <div>
              <b>Energy loss signal</b>
              <span>
                {num(
                  energyLoss,
                  1
                )} kWh estimated
              </span>
            </div>

            <div>
              <b>Water loss signal</b>
              <span>
                {num(
                  waterLoss,
                  1
                )} kL estimated
              </span>
            </div>
          </div>
        </Card>
      </div>

      <div className="analytics-secondary-grid">
        <Card>
          <PanelHead
            icon={Zap}
            title="Top Energy Drivers"
            sub="Facilities with current loss signals"
          />

          <div className="analytics-driver-list">
            {topDrivers.map(
              (
                {
                  facility,
                  power,
                  energyLoss
                },
                index
              ) => (
                <div
                  className="analytics-driver"
                  key={
                    facility.facility_code
                  }
                >
                  <span>
                    {index + 1}
                  </span>

                  <div>
                    <b>
                      {facility.facility_name ||
                        facility.name ||
                        facility.facility_code}
                    </b>

                    <small>
                      Power{" "}
                      {num(
                        power,
                        1
                      )}{" "}
                      kW
                    </small>
                  </div>

                  <strong>
  {energyLoss > 0
    ? `${num(energyLoss, 1)} kWh excess`
    : `${num(power, 1)} kW demand`}
		</strong>
                </div>
              )
            )}
          </div>
        </Card>

        <Card>
          <PanelHead
            icon={Waves}
            title="Operating Conditions"
            sub="Water flow and pressure context"
          />

          <div className="analytics-condition">
            <div>
              <span>
                Average Flow
              </span>

              <strong>
                {num(
                  avgFlow,
                  1
                )}{" "}
                L/min
              </strong>
            </div>

            <div>
              <span>
                Latest Pressure
              </span>

              <strong>
                {num(
                  chartRows[
                    chartRows.length - 1
                  ]?.pressure,
                  2
                )}{" "}
                bar
              </strong>
            </div>

            <div>
              <span>
                Water Excess
              </span>

              <strong>
                {num(
                  Math.max(
                    0,
                    waterVariance
                  ),
                  1
                )}{" "}
                kL
              </strong>
            </div>
          </div>
        </Card>
      </div>

      <Card className="analytics-performance-card">
        <PanelHead
          icon={ShieldCheck}
          title="Facility Performance"
          sub="Live facility telemetry"
        />

        <div className="analytics-performance-table">
          <div className="analytics-table-head">
            <span>Facility</span>
            <span>Energy</span>
            <span>Expected</span>
            <span>Power</span>
            <span>Water</span>
            <span>Status</span>
          </div>

          {latestRows.map(
            ({
              facility,
              latest
            }) => {
              const energy =
                Number(
                  facility?.energy_kwh ?? latest?.energy_kwh
                ) || 0;

              const expected =
                Number(
                  facility?.expected_energy_kwh ??
                    latest?.expected_energy_kwh
                ) || 0;

              const variance =
                energy - expected;

              return (
                <div
                  className="analytics-table-row"
                  key={
                    facility.facility_code
                  }
                >
                  <span>
                    <b>
                      {facility.facility_name ||
                        facility.name ||
                        facility.facility_code}
                    </b>

                    <small>
                      {
                        facility.facility_code
                      }
                    </small>
                  </span>

                  <span>
                    {num(
                      energy,
                      1
                    )}{" "}
                    kWh
                  </span>

                  <span>
                    {num(
                      expected,
                      1
                    )}{" "}
                    kWh
                  </span>

                  <span>
                    {num(
                      facility?.power_kw ?? latest?.power_kw,
                      1
                    )}{" "}
                    kW
                  </span>

                  <span>
                    {num(
                      facility?.water_kl ?? latest?.water_kl,
                      1
                    )}{" "}
                    kL
                  </span>

                  <span
                    className={
                      variance > 0
                        ? "warning"
                        : "healthy"
                    }
                  >
                    {variance > 0
                      ? "Watch"
                      : "Normal"}
                  </span>
                </div>
              );
            }
          )}
        </div>
      </Card>
    </Page>
  );
}

function AIInsights({
  anomalies
}) {
  const navigate = useNavigate();

  const recommendations = [
    [
      "Investigate abnormal energy",
      "Compare affected equipment against its expected baseline.",
      "High"
    ],
    [
      "Investigate water loss",
      "Review pressure, valves and nearby water zones.",
      "High"
    ],
    [
      "Inspect equipment vibration",
      "Repeated vibration anomalies may indicate equipment wear.",
      "Medium"
    ]
  ];

  return (
    <Page
      title="AI Insights"
      sub="Action-oriented recommendations generated from FlowSense signals"
    >
      <div className="rec-grid">
        {recommendations.map(
          ([title, description, priority]) => (
            <button
              type="button"
              className="rec"
              key={title}
              onClick={() =>
                navigate("/alerts")
              }
            >
              <div>
                <Lightbulb />
              </div>

              <span>
                <b>{title}</b>
                <small>
                  {description}
                </small>
              </span>

              <em>{priority}</em>
            </button>
          )
        )}
      </div>

      <Card className="workspace-card">
        <PanelHead
          icon={Sparkles}
          title="Recent AI Context"
          sub={`${anomalies.length} recent anomaly records available`}
        />

        <p className="workspace-copy">
          AI recommendations are linked to the
          live anomaly and resource monitoring
          pipeline. Open an alert to investigate
          the affected facility.
        </p>
      </Card>
    </Page>
  );
}

function Reports() {
  return (
    <Page
      title="Reports"
      sub="Operational and resource reporting"
    >
      <div className="workspace-grid">
        <Card>
          <PanelHead
            icon={FileText}
            title="Resource Report"
            sub="Energy and water performance"
          />

          <p className="workspace-copy">
            Use the Energy, Water and Facility
            pages to review the underlying
            realtime and historical data.
          </p>
        </Card>

        <Card>
          <PanelHead
            icon={ShieldCheck}
            title="Operational Report"
            sub="Anomalies and facility health"
          />

          <p className="workspace-copy">
            Review current facility status and
            detected anomalies from the Alerts
            workspace.
          </p>
        </Card>
      </div>
    </Page>
  );
}

function Devices() {
  return (
    <Page
      title="Devices"
      sub="IoT device health and connectivity"
    >
      <Card className="workspace-card">
        <PanelHead
          icon={Cpu}
          title="IoT Device Network"
          sub="FlowSense facility connectivity"
        />

        <div className="device-status">
          <span className="device-dot" />
          <strong>
            Realtime network available
          </strong>
          <small>
            Devices stream telemetry through
            the FlowSense WebSocket gateway.
          </small>
        </div>
      </Card>
    </Page>
  );
}

function SettingsPage() {
  return (
    <Page
      title="Settings"
      sub="FlowSense configuration"
    >
      <div className="workspace-grid">
        <Card>
          <PanelHead
            icon={Settings}
            title="Monitoring"
            sub="Realtime dashboard configuration"
          />

          <div className="setting-row">
            <span>Realtime telemetry</span>
            <b className="green">
              Enabled
            </b>
          </div>

          <div className="setting-row">
            <span>WebSocket streaming</span>
            <b className="green">
              Enabled
            </b>
          </div>
        </Card>

        <Card>
          <PanelHead
            icon={ShieldCheck}
            title="System"
            sub="FlowSense platform"
          />

          <div className="setting-row">
            <span>Backend</span>
            <b>FastAPI</b>
          </div>

          <div className="setting-row">
            <span>Database</span>
            <b>PostgreSQL</b>
          </div>
        </Card>
      </div>
    </Page>
  );
}

/* =========================
   APP
========================= */

function App() {
  const {
    facilityList,
    alerts,
    connection,
    lastTick,
  } = useFlowSense();

 const [selected, setSelected] = useState("all");

 useEffect(() => {
  if (
    selected !== "all" &&
    !facilityList.some(
      (facility) =>
        facility.facility_code === selected
    )
  ) {
    setSelected("all");
  }
}, [facilityList, selected]);

  const refresh = () => {
    window.location.reload();
  };

  return (
    <Shell anomalies={alerts}>
      <Routes>
        <Route
          path="/"
          element={
            <RealtimeOverview
              facilities={facilityList}
              anomalies={alerts}
              selected={selected}
              setSelected={setSelected}
              onRefresh={refresh}
            />
          }
        />

        <Route
          path="/legacy-overview"
          element={
            <Overview
              facilities={facilityList}
              anomalies={alerts}
              selected={selected}
              setSelected={setSelected}
              onRefresh={refresh}
            />
          }
        />

        <Route
          path="/facilities"
          element={
            <Facilities
              facilities={facilityList}
              anomalies={alerts}
            />
          }
        />

        <Route
          path="/facilities/:code"
          element={
            <Detail
              facilities={facilityList}
              anomalies={alerts}
            />
          }
        />

        <Route
          path="/energy"
          element={
            <Resource
              type="energy"
              facilities={facilityList}
            />
          }
        />

        <Route
          path="/water"
          element={
            <Resource
              type="water"
              facilities={facilityList}
            />
          }
        />

        <Route
          path="/alerts"
          element={
            <Alerts
              anomalies={alerts}
            />
          }
        />

        <Route
          path="/analytics"
          element={
            <Analytics
              facilities={facilityList}
            />
          }
        />

        <Route
          path="/ai-insights"
          element={
            <AIInsights
              anomalies={alerts}
            />
          }
        />

        <Route
          path="/reports"
          element={<Reports />}
        />

        <Route
          path="/devices"
          element={<Devices />}
        />

        <Route
          path="/settings"
          element={<SettingsPage />}
        />

        <Route
          path="*"
          element={
            <Navigate to="/" replace />
          }
        />
      </Routes>
    </Shell>
  );
}

export default App;
