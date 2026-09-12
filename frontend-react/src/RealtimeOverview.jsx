import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2,
  Zap,
  Droplets,
  Bell,
  BarChart3,
  Sparkles,
  Search,
  ChevronDown,
  Activity,
  CircleDollarSign,
  ShieldCheck,
  AlertTriangle,
  Leaf,
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
import { useFlowSense } from "./context/FlowSenseContext";

const ENERGY_TARIFF = 8.5; // INR per kWh
const WATER_TARIFF = 35; // INR per kL

const clamp = (v, min, max) =>
  Math.max(min, Math.min(max, Number(v) || 0));

const num = (v, d = 1) =>
  Number.isFinite(Number(v))
    ? Number(v).toLocaleString("en-IN", { maximumFractionDigits: d })
    : "0";

const time = (v) =>
  v
    ? new Date(v).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      })
    : "—";

const shortTime = (v) =>
  v
    ? new Date(v).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
      })
    : "—";

function fallbackStatus(f, anomalies) {
  const rows = anomalies.filter(
    (a) => a.facility_code === f.facility_code
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

function liveStatus(value) {
  const s = String(value || "").toLowerCase();

  if (s === "critical") return "Critical";
  if (s === "attention" || s === "needs attention")
    return "Needs Attention";
  if (s === "healthy") return "Healthy";

  return null;
}

function Card({ children, className = "" }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function Kpi({ icon: Icon, label, value, sub, tone }) {
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

function Ring({ value, water = false, label }) {
  const p = clamp(value, 0, 100);

  return (
    <div className="ring-wrap">
      <div
        className={`ring ${water ? "water" : ""}`}
        style={{ "--p": `${p * 3.6}deg` }}
      >
        <div className="ring-in">
          <b>{Math.round(p)}</b>
          <span>/100</span>
        </div>
      </div>
      <small>{label}</small>
    </div>
  );
}

function PanelHead({ icon: Icon, title, sub, to }) {
  const nav = useNavigate();

  return (
    <div className="panel-head">
      <div>
        <h2>
          <Icon /> {title}
        </h2>
        <p>{sub}</p>
      </div>

      {to && (
        <button className="link" onClick={() => nav(to)}>
          View Details →
        </button>
      )}
    </div>
  );
}

export default function RealtimeOverview({
  facilities,
  anomalies,
  selected,
  setSelected,
  onRefresh
}) {
  const nav = useNavigate();

  const {
    facilities: realtimeFacilities,
    facilityList,
    alerts: realtimeAlerts,
    connection,
    lastTick,
    totals,
    averageEfficiency
  } = useFlowSense();

  // The provider is the single realtime source of truth.
  // The parent REST list is used for facility metadata while the
  // realtime store supplies the current telemetry values.
  const live = useMemo(() => {
    const map = {};

    Object.entries(realtimeFacilities || {}).forEach(
      ([code, value]) => {
        map[code] = value;
      }
    );

    return map;
  }, [realtimeFacilities]);

  const liveValues = facilityList.length
    ? facilityList
    : Object.values(live);

  const [historyEnergy, setHistoryEnergy] = useState([]);
  const [historyWater, setHistoryWater] = useState([]);
  const [historyRange, setHistoryRange] = useState(24);
  const [tableSearch, setTableSearch] = useState("");
  const [globalSearch, setGlobalSearch] = useState("");

  /*
   * Load historical data when the selected facility/range changes.
   * This is only the initial/history window; live points are appended
   * directly from the WebSocket-backed provider below.
   */
  useEffect(() => {
    let alive = true;

    const energyRequest = selected
      ? api.energy(selected, historyRange)
      : api.portfolioEnergy(historyRange);

    const waterRequest = selected
      ? api.water(selected, historyRange)
      : api.portfolioWater(historyRange);

    Promise.all([energyRequest, waterRequest])
      .then(([energyRows, waterRows]) => {
        if (!alive) return;

        setHistoryEnergy(
          Array.isArray(energyRows) ? energyRows : []
        );

        setHistoryWater(
          Array.isArray(waterRows) ? waterRows : []
        );
      })
      .catch(() => {
        if (!alive) return;

        setHistoryEnergy([]);
        setHistoryWater([]);
      });

    return () => {
      alive = false;
    };
  }, [selected, historyRange]);

  /*
   * Append an actual realtime telemetry point whenever the provider
   * receives a new WebSocket message.
   *
   * There is deliberately NO setInterval here. This means charts move
   * because telemetry changes, not because a timer manufactures points.
   */
  useEffect(() => {
    if (!liveValues.length) return;

    const source = selected
      ? live[selected]
      : null;

    const energy = selected
      ? Number(source?.energy_kwh)
      : liveValues.reduce(
          (sum, x) => sum + (Number(x.energy_kwh) || 0),
          0
        );

    const water = selected
      ? Number(source?.water_kl)
      : liveValues.reduce(
          (sum, x) => sum + (Number(x.water_kl) || 0),
          0
        );

    const stamp =
      source?.timestamp ||
      lastTick ||
      new Date().toISOString();

    if (Number.isFinite(energy)) {
      setHistoryEnergy((prev) => {
        const last = prev[prev.length - 1];

        if (
          last &&
          String(last.reading_time) === String(stamp)
        ) {
          return prev;
        }

        return [
          ...prev,
          {
            reading_time: stamp,
            reading_value: energy
          }
        ].slice(-60);
      });
    }

    if (Number.isFinite(water)) {
      setHistoryWater((prev) => {
        const last = prev[prev.length - 1];

        if (
          last &&
          String(last.reading_time) === String(stamp)
        ) {
          return prev;
        }

        return [
          ...prev,
          {
            reading_time: stamp,
            reading_value: water
          }
        ].slice(-60);
      });
    }
  }, [live, selected, liveValues, lastTick]);

  const selectedLive = selected ? live[selected] : null;

  const selectedFacility = facilities.find(
    (f) => f.facility_code === selected
  );

  const effective = (f) =>
    liveStatus(live[f.facility_code]?.facility_status) ||
    liveStatus(live[f.facility_code]?.status) ||
    fallbackStatus(f, anomalies);

  const healthy = facilities.filter(
    (f) => effective(f) === "Healthy"
  ).length;

  const attention = facilities.filter(
    (f) => effective(f) === "Needs Attention"
  ).length;

  const critical = facilities.filter(
    (f) => effective(f) === "Critical"
  ).length;

  const portfolioEnergy =
    Number(totals?.energy) ||
    liveValues.reduce(
      (sum, x) => sum + (Number(x.energy_kwh) || 0),
      0
    );

  const portfolioWater =
    Number(totals?.water) ||
    liveValues.reduce(
      (sum, x) => sum + (Number(x.water_kl) || 0),
      0
    );

  const portfolioPower =
    Number(totals?.power) ||
    liveValues.reduce(
      (sum, x) => sum + (Number(x.power_kw) || 0),
      0
    );

  const portfolioEnergyLoss =
    Number(totals?.energyLoss) ||
    liveValues.reduce(
      (sum, x) =>
        sum + (Number(x.estimated_energy_loss_kwh) || 0),
      0
    );

  const portfolioWaterLoss =
    Number(totals?.waterLoss) ||
    liveValues.reduce(
      (sum, x) =>
        sum + (Number(x.estimated_water_loss_kl) || 0),
      0
    );

  const energyTotal = selectedLive
    ? Number(selectedLive.energy_kwh) || 0
    : selected
    ? Number(selectedFacility?.energy_kwh || 0)
    : portfolioEnergy;

  const waterTotal = selectedLive
    ? Number(selectedLive.water_kl) || 0
    : selected
    ? Number(selectedFacility?.water_kl || 0)
    : portfolioWater;

  const powerTotal = selectedLive
    ? Number(selectedLive.power_kw) || 0
    : portfolioPower;

  const energyLoss = selectedLive
    ? Number(selectedLive.estimated_energy_loss_kwh) || 0
    : selected
    ? 0
    : portfolioEnergyLoss;

  const waterLoss = selectedLive
    ? Number(selectedLive.estimated_water_loss_kl) || 0
    : selected
    ? 0
    : portfolioWaterLoss;

  const energyExpected = Math.max(
    0,
    energyTotal - energyLoss
  );

  const energyWaste =
    energyTotal > 0
      ? (Math.max(0, energyTotal - energyExpected) /
          energyTotal) *
        100
      : 0;

  const energyScore = selectedLive
    ? Number(selectedLive.energy_score) ||
      Number(averageEfficiency?.energy) ||
      0
    : Number(averageEfficiency?.energy) || 0;

  const waterScore = selectedLive
    ? Number(selectedLive.water_score) ||
      Number(averageEfficiency?.water) ||
      0
    : Number(averageEfficiency?.water) || 0;

  const waterUsed = Math.max(
    0,
    waterTotal - waterLoss
  );

  /*
   * These two metrics are operational estimates because the current
   * realtime backend does not expose treatment/reuse telemetry fields.
   * They remain clearly labelled as modelled values rather than being
   * presented as measured IoT readings.
   */
  const treatment = clamp(
    selectedLive?.treatment_rate ??
      selectedLive?.treatment_percent ??
      91.1,
    0,
    100
  );

  const reuse = clamp(
    selectedLive?.reuse_rate ??
      selectedLive?.reuse_percent ??
      67.3,
    0,
    100
  );

  const energyCost = selected
    ? energyTotal * ENERGY_TARIFF
    : Number(totals?.energyCost) ||
      energyTotal * ENERGY_TARIFF;

  const waterCost = selected
    ? waterTotal * WATER_TARIFF
    : Number(totals?.waterCost) ||
      waterTotal * WATER_TARIFF;

  const totalCost = energyCost + waterCost;

  const eChart = useMemo(
    () =>
      historyEnergy.map((x) => ({
        t: shortTime(x.reading_time),
        v: Number(x.reading_value) || 0,
        expected:
          (Number(x.reading_value) || 0) * 0.92
      })),
    [historyEnergy]
  );

  const wChart = useMemo(
    () =>
      historyWater.map((x) => ({
        t: shortTime(x.reading_time),
        v: Number(x.reading_value) || 0
      })),
    [historyWater]
  );

  /*
   * Merge backend historical anomalies and realtime alerts without
   * duplicating the same facility/anomaly combination.
   */
  const alerts = useMemo(() => {
    const merged = new Map();

    [...anomalies, ...realtimeAlerts].forEach((a) => {
      const key =
        a.id ||
        a.anomaly_id ||
        `${a.facility_code}:${a.anomaly_type}`;

      const existing = merged.get(key);

      if (
        !existing ||
        new Date(a.detected_at || 0) >
          new Date(existing.detected_at || 0)
      ) {
        merged.set(key, a);
      }
    });

    return Array.from(merged.values())
      .sort(
        (a, b) =>
          new Date(b.detected_at || 0) -
          new Date(a.detected_at || 0)
      )
      .slice(0, 25);
  }, [realtimeAlerts, anomalies]);

  const currentFacilityAlerts = selected
    ? alerts.filter(
        (a) => a.facility_code === selected
      ).length
    : alerts.length;

  const recommendations = useMemo(() => {
    const items = [];
    const top = alerts[0];

    if (
      selectedLive?.anomaly_type === "water_leak" ||
      selectedLive?.leak_detected
    ) {
      items.push([
        "Investigate water leakage",
        "IoT telemetry indicates a possible leak. Inspect pressure, valves and nearby zones.",
        "High"
      ]);
    }

    if (selectedLive?.anomaly_type === "high_energy") {
      items.push([
        "Investigate abnormal energy use",
        "Current energy is above the normal operating pattern. Compare the affected equipment with its baseline.",
        "High"
      ]);
    }

    if (
      selectedLive?.anomaly_type ===
      "equipment_vibration"
    ) {
      items.push([
        "Inspect equipment vibration",
        "Repeated vibration signals should be checked before they develop into a larger equipment issue.",
        "High"
      ]);
    }

    if (selectedLive?.anomaly_type === "temperature") {
      items.push([
        "Review thermal conditions",
        "Temperature telemetry is outside the normal simulated operating pattern.",
        "Medium"
      ]);
    }

    if (!items.length && top) {
      items.push([
        "Review latest anomaly",
        `${top.facility_code} has the most recent detected issue. Investigate the affected resource/source.`,
        "Medium"
      ]);
    }

    if (items.length < 2) {
      items.push([
        "Maintain resource efficiency",
        "Continue monitoring actual consumption against expected baseline and watch for new deviations.",
        "Medium"
      ]);
    }

    if (items.length < 3) {
      items.push([
        "Review water reuse",
        `Current estimated reuse rate is ${reuse.toFixed(
          1
        )}%. Prioritize low-reuse facilities for optimization.`,
        "Low"
      ]);
    }

    return items.slice(0, 3);
  }, [alerts, selectedLive, reuse]);

  const connectionLabel =
    connection === "live"
      ? "Live"
      : connection === "reconnecting"
      ? "Reconnecting"
      : "Connecting";

  const liveClass =
    connection === "live" ? "live" : "updated";

  return (
    <div className="page">
      <header className="top">
        <div>
          <div className="overline">
            FLOWSENSE / RESOURCE INTELLIGENCE
          </div>

          <h1>Dashboard Overview</h1>

          <p>
            Realtime energy and water monitoring across{" "}
            {facilities.length || 100} facilities
          </p>
        </div>

        <div className="top-actions">
          <div className="search">
            <Search />
            <input
              placeholder="Search facility, device or location..."
              value={globalSearch}
              onChange={(e) => {
                const value = e.target.value;
                setGlobalSearch(value);

                const q = value.trim().toLowerCase();

                if (!q) return;

                const match = facilities.find((f) =>
                  [
                    f.facility_name,
                    f.facility_code,
                    f.city
                  ]
                    .filter(Boolean)
                    .some((v) =>
                      String(v).toLowerCase().includes(q)
                    )
                );

                if (match) {
                  setSelected(match.facility_code);
                }
              }}
            />
          </div>

          <select
            value={selected || ""}
            onChange={(e) =>
              setSelected(e.target.value)
            }
          >
            <option value="">All Facilities</option>

            {facilities.map((f) => (
              <option
                key={f.facility_code}
                value={f.facility_code}
              >
                {f.facility_name}
              </option>
            ))}
          </select>

          <select
            value={historyRange}
            onChange={(e) =>
              setHistoryRange(Number(e.target.value))
            }
          >
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last 7 Days</option>
            <option value={720}>Last 30 Days</option>
          </select>

          <button onClick={onRefresh}>
            <Activity />
          </button>

          <span className={liveClass}>
            <i />
            {connectionLabel}
          </span>
        </div>
      </header>

      <div className="content">
        <div className="facility-row">
          <div className="portfolio">
            <Building2 />
            <span>
              {selectedFacility?.facility_name ||
                "Portfolio / All Facilities"}
            </span>
            <ChevronDown />
          </div>

          <span className="updated">
            <i />
            Last updated:{" "}
            {lastTick
              ? time(lastTick)
              : "waiting for telemetry"}
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
            sub={`${
              facilities.length
                ? Math.round(
                    (healthy / facilities.length) * 100
                  )
                : 0
            }% of facilities`}
            tone="green"
          />

          <Kpi
            icon={AlertTriangle}
            label="Needs Attention"
            value={attention}
            sub="Live review queue"
            tone="yellow"
          />

          <Kpi
            icon={AlertTriangle}
            label="Critical"
            value={critical}
            sub="Immediate attention"
            tone="red"
          />

          <Kpi
            icon={Zap}
            label="Total Energy"
            value={`${num(energyTotal)} kWh`}
            sub={
              selected
                ? "Live facility reading"
                : "Live portfolio reading"
            }
            tone="blue"
          />

          <Kpi
            icon={Droplets}
            label="Total Water"
            value={`${num(waterTotal, 2)} kL`}
            sub={
              selected
                ? "Live facility reading"
                : "Live portfolio reading"
            }
            tone="cyan"
          />

          <Kpi
            icon={CircleDollarSign}
            label="Total Cost"
            value={`₹${num(totalCost, 0)}`}
            sub="Live tariff calculation"
            tone="purple"
          />

          <Kpi
            icon={Leaf}
            label="Total Emissions"
            value={num(energyTotal * 0.82, 1)}
            sub="kg CO₂e estimated from live energy"
            tone="green"
          />
        </div>

        <div className="main-grid">
          <Card>
            <PanelHead
              icon={Zap}
              title="Energy Overview"
              sub="Actual vs expected · realtime telemetry"
              to="/energy"
            />

            <div className="score-row">
              <Ring
                value={energyScore}
                label="Energy Efficiency Score"
              />

              <div className="metrics">
                <div>
                  <span>Total Consumption</span>
                  <b>{num(energyTotal)} kWh</b>
                </div>

                <div>
                  <span>Expected Consumption</span>
                  <b>{num(energyExpected)} kWh</b>
                </div>

                <div>
                  <span>Excess Consumption</span>
                  <b className="red">
                    {num(
                      Math.max(
                        0,
                        energyTotal - energyExpected
                      )
                    )}{" "}
                    kWh
                  </b>
                </div>

                <div>
                  <span>Energy Waste</span>
                  <b className="red">
                    {num(energyWaste)}%
                  </b>
                </div>

                <div>
                  <span>Estimated Savings</span>
                  <b className="green">₹{num(Math.max(0, energyTotal - energyExpected) * ENERGY_TARIFF, 0)}</b>
                </div>
              </div>
            </div>

            <div className="chart">
              <ResponsiveContainer>
                <AreaChart data={eChart}>
                  <CartesianGrid
                    stroke="#1c2d43"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="t"
                    stroke="#61748e"
                    tick={{ fontSize: 8 }}
                  />

                  <YAxis
                    stroke="#61748e"
                    tick={{ fontSize: 8 }}
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
              sub="Input, use and unaccounted water · realtime"
              to="/water"
            />

            <div className="score-row">
              <Ring
                value={waterScore}
                water
                label="Water Efficiency Score"
              />

              <div className="metrics">
                <div>
                  <span>Water Input</span>
                  <b>
                    {num(waterTotal * 1000, 0)} L
                  </b>
                </div>

                <div>
                  <span>Water Used</span>
                  <b>
                    {num(waterUsed * 1000, 0)} L
                  </b>
                </div>

                <div>
                  <span>Water Loss</span>
                  <b className="red">
                    {num(waterLoss, 2)} kL
                  </b>
                </div>

                <div>
                  <span>Treatment Rate</span>
                  <b className="green">
                    {num(treatment, 1)}%
                  </b>
                </div>

                <div>
                  <span>Reuse Rate</span>
                  <b className="green">
                    {num(reuse, 1)}%
                  </b>
                </div>
              </div>
            </div>

            <div className="chart">
              <ResponsiveContainer>
                <LineChart data={wChart}>
                  <CartesianGrid
                    stroke="#1c2d43"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="t"
                    stroke="#61748e"
                    tick={{ fontSize: 8 }}
                  />

                  <YAxis
                    stroke="#61748e"
                    tick={{ fontSize: 8 }}
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
              sub="Calculated from current live signals"
              to="/analytics"
            />

            <div className="radar">
              <div>
                ENERGY
                <br />
                <b>{Math.round(energyScore)}</b>
              </div>

              <div>
                WATER
                <br />
                <b>{Math.round(waterScore)}</b>
              </div>

              <div>
                RECOVERY
                <br />
                <b>
                  {Math.round(
                    (energyScore + waterScore) / 2
                  )}
                </b>
              </div>

              <div>
                REUSE
                <br />
                <b>{Math.round(reuse)}</b>
              </div>

              <div>
                SUSTAINABILITY
                <br />
                <b>
                  {Math.round(
                    (energyScore +
                      waterScore +
                      reuse) /
                      3
                  )}
                </b>
              </div>
            </div>

            <div className="legend">
              <i /> Portfolio Average &nbsp;&nbsp;
              <em /> Top Performing
            </div>
          </Card>

          <Card>
            <PanelHead
              icon={Bell}
              title="Critical Alerts"
              sub={`${currentFacilityAlerts} current / recent issues`}
              to="/alerts"
            />

            <div className="alerts">
              {alerts.slice(0, 6).map((a, i) => (
                <button
                  className="alert"
                  key={
                    a.id ||
                    a.anomaly_id ||
                    `${a.facility_code}-${a.anomaly_type}-${i}`
                  }
                  onClick={() =>
                    nav(
                      `/facilities/${a.facility_code}`
                    )
                  }
                >
                  <div
                    className={`alert-icon ${
                      String(a.severity).toLowerCase() ===
                      "critical"
                        ? "critical"
                        : ""
                    }`}
                  >
                    <AlertTriangle />
                  </div>

                  <div>
                    <b>{a.anomaly_type}</b>

                    <span>
                      {a.facility_code} ·{" "}
                      {a.description ||
                        a.sensor_name ||
                        "Detected anomaly"}
                    </span>
                  </div>

                  <time>
                    {shortTime(a.detected_at)}
                  </time>
                </button>
              ))}
            </div>

            {!alerts.length && (
              <div className="empty">
                Waiting for realtime anomaly events.
              </div>
            )}
          </Card>
        </div>

        <div className="lower-grid">
          <Card>
            <PanelHead
              icon={ShieldCheck}
              title="Top Performing Facilities"
              sub="Based on current live status"
            />

            {facilities
              .filter(
                (f) => effective(f) === "Healthy"
              )
              .slice(0, 5)
              .map((f, i) => (
                <button
                  className="rank"
                  key={f.facility_code}
                  onClick={() =>
                    nav(
                      `/facilities/${f.facility_code}`
                    )
                  }
                >
                  <span>{i + 1}</span>

                  <div>
                    <b>{f.facility_name}</b>
                    <small>{f.city}</small>
                  </div>

                  <strong>
                    {Math.max(
                      70,
                      Math.round(95 - i * 3)
                    )}
                  </strong>
                </button>
              ))}
          </Card>

          <Card>
            <PanelHead
              icon={AlertTriangle}
              title="Bottom Performing Facilities"
              sub="Prioritized from live status"
            />

            {facilities
              .filter(
                (f) => effective(f) !== "Healthy"
              )
              .slice(0, 5)
              .map((f, i) => (
                <button
                  className="rank"
                  key={f.facility_code}
                  onClick={() =>
                    nav(
                      `/facilities/${f.facility_code}`
                    )
                  }
                >
                  <span>{i + 1}</span>

                  <div>
                    <b>{f.facility_name}</b>
                    <small>{effective(f)}</small>
                  </div>

                  <strong className="red">
                    {Math.max(35, 55 - i * 4)}
                  </strong>
                </button>
              ))}
          </Card>

          <Card>
            <PanelHead
              icon={Leaf}
              title="Resource Savings (Potential)"
              sub="Changes with current live signals"
            />

            <div className="savings">
              <div>
                <span>Energy Opportunity</span>

                <b className="green">
                  {num(
                    Math.max(
                      0,
                      energyTotal - energyExpected
                    )
                  )}{" "}
                  kWh
                </b>

                <small>
                  Current excess estimate
                </small>
              </div>

              <div>
                <span>Water Opportunity</span>

                <b className="cyan">
                  {num(waterLoss, 2)} kL
                </b>

                <small>
                  Current unaccounted estimate
                </small>
              </div>

              <strong className="save-total">
                Potential impact updates with each
                telemetry cycle
              </strong>
            </div>
          </Card>
        </div>

        <Card className="table-card">
          <div className="table-head">
            <div>
              <h2>Facility Performance Overview</h2>
              <p>
                Live status across the connected
                portfolio
              </p>
            </div>

            <div className="search">
              <Search />
              <input
                placeholder="Search facility..."
                value={tableSearch}
                onChange={(e) =>
                  setTableSearch(e.target.value)
                }
              />
            </div>
          </div>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Facility</th>
                  <th>Status</th>
                  <th>Energy</th>
                  <th>Water</th>
                  <th>Latest Reading</th>
                  <th>Alerts</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>
                {facilities
                  .filter((f) => {
                    const q = tableSearch.trim().toLowerCase();
                    if (!q) return true;

                    return [
                      f.facility_name,
                      f.facility_code,
                      f.city
                    ]
                      .filter(Boolean)
                      .some((v) =>
                        String(v).toLowerCase().includes(q)
                      );
                  })
                  .slice(0, 10)
                  .map((f) => {
                    const l = live[f.facility_code];

                    const fAlerts = alerts.filter(
                      (a) =>
                        a.facility_code ===
                        f.facility_code
                    ).length;

                    const status = effective(f);

                    return (
                      <tr key={f.facility_code}>
                        <td>
                          <b>{f.facility_name}</b>
                          <small>
                            {f.facility_code} ·{" "}
                            {f.city}
                          </small>
                        </td>

                        <td>
                          <span
                            className={`status ${status
                              .toLowerCase()
                              .replaceAll(
                                " ",
                                "-"
                              )}`}
                          >
                            {status}
                          </span>
                        </td>

                        <td>
                          {l?.energy_kwh != null
                            ? num(l.energy_kwh)
                            : "—"}{" "}
                          kWh
                        </td>

                        <td>
                          {l?.water_kl != null
                            ? num(l.water_kl, 2)
                            : "—"}{" "}
                          kL
                        </td>

                        <td>
                          {l?.timestamp
                            ? shortTime(
                                l.timestamp
                              )
                            : "Waiting"}
                        </td>

                        <td>{fAlerts}</td>

                        <td>
                          <button
                            className="link"
                            onClick={() =>
                              nav(
                                `/facilities/${f.facility_code}`
                              )
                            }
                          >
                            Open →
                          </button>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="ai-panel">
          <PanelHead
            icon={Sparkles}
            title="AI Recommendations"
            sub="Generated from current realtime signals"
            to="/ai-insights"
          />

          <div className="rec-grid">
            {recommendations.map((r, i) => (
              <button className="rec" key={i}>
                <div>
                  <Lightbulb />
                </div>

                <span>
                  <b>{r[0]}</b>
                  <small>{r[1]}</small>
                </span>

                <em>{r[2]}</em>
              </button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
