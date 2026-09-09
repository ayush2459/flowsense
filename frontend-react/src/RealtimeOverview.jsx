import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Building2, Zap, Droplets, Bell, BarChart3, Sparkles, FileText, Cpu, Gauge, ShieldCheck, AlertTriangle, Leaf, Search, ChevronDown, Activity, CircleDollarSign, Lightbulb } from "lucide-react";
import { AreaChart, Area, LineChart, Line, ResponsiveContainer, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { api } from "./services/api";
import { connectAllFacilities } from "./realtime";

const clamp = (v, min, max) => Math.max(min, Math.min(max, Number(v) || 0));
const num = (v, d = 1) => Number.isFinite(Number(v)) ? Number(v).toLocaleString("en-IN", { maximumFractionDigits: d }) : "0";
const time = (v) => v ? new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—";
const shortTime = (v) => v ? new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";

function fallbackStatus(f, anomalies) {
  const rows = anomalies.filter(a => a.facility_code === f.facility_code);
  if (rows.some(a => String(a.severity).toLowerCase() === "critical")) return "Critical";
  if (rows.length) return "Needs Attention";
  return "Healthy";
}

function liveStatus(value) {
  const s = String(value || "").toLowerCase();
  if (s === "critical") return "Critical";
  if (s === "attention" || s === "needs attention") return "Needs Attention";
  if (s === "healthy") return "Healthy";
  return null;
}

function Card({ children, className = "" }) { return <section className={`card ${className}`}>{children}</section>; }
function Kpi({ icon: Icon, label, value, sub, tone }) { return <Card className="kpi"><div className={`kpi-icon ${tone}`}><Icon /></div><label>{label}</label><strong>{value}</strong><small className={tone}>{sub}</small></Card>; }
function Ring({ value, water = false, label }) { const p = clamp(value, 0, 100); return <div className="ring-wrap"><div className={`ring ${water ? "water" : ""}`} style={{ "--p": `${p * 3.6}deg` }}><div className="ring-in"><b>{Math.round(p)}</b><span>/100</span></div></div><small>{label}</small></div>; }
function PanelHead({ icon: Icon, title, sub, to }) { const nav = useNavigate(); return <div className="panel-head"><div><h2><Icon /> {title}</h2><p>{sub}</p></div>{to && <button className="link" onClick={() => nav(to)}>View Details →</button>}</div>; }

export default function RealtimeOverview({ facilities, anomalies, selected, setSelected, onRefresh }) {
  const nav = useNavigate();
  const [live, setLive] = useState({});
  const [liveAlerts, setLiveAlerts] = useState([]);
  const [connection, setConnection] = useState("connecting");
  const [historyEnergy, setHistoryEnergy] = useState([]);
  const [historyWater, setHistoryWater] = useState([]);
  const [lastTick, setLastTick] = useState(null);

  useEffect(() => connectAllFacilities({
    onStatus: setConnection,
    onMessage: (message) => {
      const code = message.facility_code;
      const data = message.data || {};
      setLive(prev => ({ ...prev, [code]: { ...prev[code], ...data, timestamp: message.timestamp || data.reading_time || new Date().toISOString() } }));
      setLastTick(message.timestamp || data.reading_time || new Date().toISOString());
      if (data.anomaly) {
        const alert = {
          id: `${code}-${message.timestamp || Date.now()}-${Math.random()}`,
          anomaly_id: null,
          facility_code: code,
          anomaly_type: data.anomaly_type || "Realtime anomaly",
          severity: String(data.status || "attention").toLowerCase() === "critical" ? "Critical" : "Warning",
          description: data.anomaly_type === "water_leak" ? "Possible water leakage detected by realtime IoT telemetry." : `Realtime IoT signal indicates ${String(data.anomaly_type || "abnormal behavior").replaceAll("_", " ")}.`,
          detected_at: message.timestamp || data.reading_time || new Date().toISOString(),
          deviation_percent: data.anomaly_type === "high_energy" ? 18 : data.anomaly_type === "high_water" ? 15 : 10,
          source_name: "Realtime IoT"
        };
        setLiveAlerts(prev => [alert, ...prev].slice(0, 25));
      }
    },
    onError: () => {}
  }), []);

  useEffect(() => {
    if (!selected) return;
    let alive = true;
    api.energy(selected, 24).then(rows => { if (alive) setHistoryEnergy(rows); }).catch(() => {});
    api.water(selected, 24).then(rows => { if (alive) setHistoryWater(rows); }).catch(() => {});
    return () => { alive = false; };
  }, [selected]);

  useEffect(() => {
    const current = selected ? live[selected] : null;
    if (!current) return;
    const stamp = current.timestamp || new Date().toISOString();
    const e = Number(current.energy_kwh);
    const w = Number(current.water_kl);
    if (Number.isFinite(e)) setHistoryEnergy(prev => [...prev, { reading_time: stamp, reading_value: e }].slice(-30));
    if (Number.isFinite(w)) setHistoryWater(prev => [...prev, { reading_time: stamp, reading_value: w }].slice(-30));
  }, [selected, live]);

  const selectedLive = selected ? live[selected] : null;
  const selectedFacility = facilities.find(f => f.facility_code === selected);
  const effective = (f) => liveStatus(live[f.facility_code]?.status) || fallbackStatus(f, anomalies);
  const healthy = facilities.filter(f => effective(f) === "Healthy").length;
  const attention = facilities.filter(f => effective(f) === "Needs Attention").length;
  const critical = facilities.filter(f => effective(f) === "Critical").length;

  const energyTotal = Number.isFinite(Number(selectedLive?.energy_kwh)) ? Number(selectedLive.energy_kwh) : Number(selectedFacility?.energy_kwh || 0);
  const waterTotal = Number.isFinite(Number(selectedLive?.water_kl)) ? Number(selectedLive.water_kl) : Number(selectedFacility?.water_kl || 0);
  const energyExpected = energyTotal * 0.92;
  const energyWaste = energyTotal > 0 ? ((energyTotal - energyExpected) / energyTotal) * 100 : 0;
  const energyScore = selectedLive ? clamp(92 - (selectedLive.anomaly_type === "high_energy" ? 20 : 0) - (selectedLive.status === "critical" ? 8 : 0), 45, 95) : 81;
  const waterLoss = selectedLive?.leak_detected || selectedLive?.anomaly_type === "water_leak" ? waterTotal * 0.12 : waterTotal * 0.05;
  const waterUsed = Math.max(0, waterTotal - waterLoss);
  const waterScore = selectedLive ? clamp(91 - (selectedLive.anomaly_type === "water_leak" ? 25 : 0) - (selectedLive.status === "critical" ? 7 : 0), 40, 95) : 76;
  const treatment = clamp(selectedLive ? 90 + (Number(selectedLive.temperature_c) % 5) : 91.1, 70, 98);
  const reuse = clamp(selectedLive ? 64 + (Number(selectedLive.humidity_percent) % 8) : 67.3, 45, 85);

  const eChart = useMemo(() => historyEnergy.map(x => ({ t: shortTime(x.reading_time), v: Number(x.reading_value) || 0, expected: (Number(x.reading_value) || 0) * 0.92 })), [historyEnergy]);
  const wChart = useMemo(() => historyWater.map(x => ({ t: shortTime(x.reading_time), v: Number(x.reading_value) || 0 })), [historyWater]);
  const alerts = useMemo(() => [...liveAlerts, ...anomalies].sort((a, b) => new Date(b.detected_at || 0) - new Date(a.detected_at || 0)).slice(0, 8), [liveAlerts, anomalies]);
  const currentFacilityAlerts = selected ? alerts.filter(a => a.facility_code === selected).length : alerts.length;

  const recommendations = useMemo(() => {
    const items = [];
    const top = alerts[0];
    if (selectedLive?.anomaly_type === "water_leak" || selectedLive?.leak_detected) items.push(["Investigate water leakage", "IoT telemetry indicates a possible leak. Inspect pressure, valves and nearby zones.", "High"]);
    if (selectedLive?.anomaly_type === "high_energy") items.push(["Investigate abnormal energy use", "Current energy is above the normal operating pattern. Compare the affected equipment with its baseline.", "High"]);
    if (selectedLive?.anomaly_type === "equipment_vibration") items.push(["Inspect equipment vibration", "Repeated vibration signals should be checked before they develop into a larger equipment issue.", "High"]);
    if (selectedLive?.anomaly_type === "temperature") items.push(["Review thermal conditions", "Temperature telemetry is outside the normal simulated operating pattern.", "Medium"]);
    if (!items.length && top) items.push(["Review latest anomaly", `${top.facility_code} has the most recent detected issue. Investigate the affected resource/source.`, "Medium"]);
    if (items.length < 2) items.push(["Maintain resource efficiency", "Continue monitoring actual consumption against expected baseline and watch for new deviations.", "Medium"]);
    if (items.length < 3) items.push(["Review water reuse", `Current modelled reuse rate is ${reuse.toFixed(1)}%. Prioritize low-reuse facilities for optimization.`, "Low"]);
    return items.slice(0, 3);
  }, [alerts, selectedLive, reuse]);

  const connectionLabel = connection === "live" ? "Live" : connection === "reconnecting" ? "Reconnecting" : "Connecting";
  const liveClass = connection === "live" ? "live" : "updated";

  return <div className="page">
    <header className="top">
      <div><div className="overline">FLOWSENSE / RESOURCE INTELLIGENCE</div><h1>Dashboard Overview</h1><p>Realtime energy and water monitoring across {facilities.length || 100} facilities</p></div>
      <div className="top-actions"><div className="search"><Search/><input placeholder="Search facility, device or location..."/></div><select value={selected || ""} onChange={e => setSelected(e.target.value)}><option value="">All Facilities</option>{facilities.map(f => <option key={f.facility_code} value={f.facility_code}>{f.facility_name}</option>)}</select><button>Today ▾</button><button onClick={onRefresh}><Activity/></button><span className={liveClass}><i/>{connectionLabel}</span></div>
    </header>

    <div className="content">
      <div className="facility-row"><div className="portfolio"><Building2/><span>{selectedFacility?.facility_name || "Portfolio / All Facilities"}</span><ChevronDown/></div><span className="updated"><i/> Last updated: {lastTick ? time(lastTick) : "waiting for telemetry"}</span></div>

      <div className="kpis">
        <Kpi icon={Building2} label="Total Facilities" value={facilities.length} sub="All locations" tone="blue"/>
        <Kpi icon={ShieldCheck} label="Healthy" value={healthy} sub={`${facilities.length ? Math.round(healthy / facilities.length * 100) : 0}% of facilities`} tone="green"/>
        <Kpi icon={AlertTriangle} label="Needs Attention" value={attention} sub="Live review queue" tone="yellow"/>
        <Kpi icon={AlertTriangle} label="Critical" value={critical} sub="Immediate attention" tone="red"/>
        <Kpi icon={Zap} label="Total Energy" value={`${num(energyTotal)} kWh`} sub="Live facility reading" tone="blue"/>
        <Kpi icon={Droplets} label="Total Water" value={`${num(waterTotal, 2)} kL`} sub="Live facility reading" tone="cyan"/>
        <Kpi icon={CircleDollarSign} label="Total Cost" value="Modelled" sub="Live tariff model" tone="purple"/>
        <Kpi icon={Leaf} label="Total Emissions" value={num(energyTotal * 0.82, 1)} sub="kg CO₂e model" tone="green"/>
      </div>

      <div className="main-grid">
        <Card><PanelHead icon={Zap} title="Energy Overview" sub="Actual vs expected · realtime telemetry" to="/energy"/><div className="score-row"><Ring value={energyScore} label="Energy Efficiency Score"/><div className="metrics"><div><span>Total Consumption</span><b>{num(energyTotal)} kWh</b></div><div><span>Expected Consumption</span><b>{num(energyExpected)} kWh</b></div><div><span>Excess Consumption</span><b className="red">{num(Math.max(0, energyTotal - energyExpected))} kWh</b></div><div><span>Energy Waste</span><b className="red">{num(energyWaste)}%</b></div><div><span>Estimated Savings</span><b className="green">Modelled</b></div></div></div><div className="chart"><ResponsiveContainer><AreaChart data={eChart}><CartesianGrid stroke="#1c2d43" vertical={false}/><XAxis dataKey="t" stroke="#61748e" tick={{fontSize:8}}/><YAxis stroke="#61748e" tick={{fontSize:8}}/><Tooltip/><Area dataKey="v" stroke="#31aaff" fill="#31aaff" fillOpacity=".12"/><Line dataKey="expected" stroke="#f2c84b" strokeDasharray="5 5" dot={false}/></AreaChart></ResponsiveContainer></div></Card>

        <Card><PanelHead icon={Droplets} title="Water Overview" sub="Input, use and unaccounted water · realtime" to="/water"/><div className="score-row"><Ring value={waterScore} water label="Water Efficiency Score"/><div className="metrics"><div><span>Water Input</span><b>{num(waterTotal * 1000, 0)} L</b></div><div><span>Water Used</span><b>{num(waterUsed * 1000, 0)} L</b></div><div><span>Water Loss</span><b className="red">{num(waterLoss, 2)} kL</b></div><div><span>Treatment Rate</span><b className="green">{num(treatment, 1)}%</b></div><div><span>Reuse Rate</span><b className="green">{num(reuse, 1)}%</b></div></div></div><div className="chart"><ResponsiveContainer><LineChart data={wChart}><CartesianGrid stroke="#1c2d43" vertical={false}/><XAxis dataKey="t" stroke="#61748e" tick={{fontSize:8}}/><YAxis stroke="#61748e" tick={{fontSize:8}}/><Tooltip/><Line dataKey="v" stroke="#2cc9ed" dot={false}/></LineChart></ResponsiveContainer></div></Card>

        <Card><PanelHead icon={BarChart3} title="Resource Efficiency" sub="Calculated from current live signals" to="/analytics"/><div className="radar"><div>ENERGY<br/><b>{Math.round(energyScore)}</b></div><div>WATER<br/><b>{Math.round(waterScore)}</b></div><div>RECOVERY<br/><b>{Math.round((energyScore + waterScore) / 2)}</b></div><div>REUSE<br/><b>{Math.round(reuse)}</b></div><div>SUSTAINABILITY<br/><b>{Math.round((energyScore + waterScore + reuse) / 3)}</b></div></div><div className="legend"><i/> Portfolio Average &nbsp;&nbsp; <em/> Top Performing</div></Card>

        <Card><PanelHead icon={Bell} title="Critical Alerts" sub={`${currentFacilityAlerts} current / recent issues`} to="/alerts"/><div className="alerts">{alerts.slice(0, 6).map((a, i) => <button className="alert" key={a.id || a.anomaly_id || `${a.facility_code}-${a.detected_at}-${i}`} onClick={() => nav(`/facilities/${a.facility_code}`)}><div className={`alert-icon ${String(a.severity).toLowerCase() === "critical" ? "critical" : ""}`}><AlertTriangle/></div><div><b>{a.anomaly_type}</b><span>{a.facility_code} · {a.description || a.sensor_name || "Detected anomaly"}</span></div><time>{shortTime(a.detected_at)}</time></button>)}</div>{!alerts.length && <div className="empty">Waiting for realtime anomaly events.</div>}</Card>
      </div>

      <div className="lower-grid">
        <Card><PanelHead icon={ShieldCheck} title="Top Performing Facilities" sub="Based on current live status"/>{facilities.filter(f => effective(f) === "Healthy").slice(0, 5).map((f, i) => <button className="rank" key={f.facility_code} onClick={() => nav(`/facilities/${f.facility_code}`)}><span>{i + 1}</span><div><b>{f.facility_name}</b><small>{f.city}</small></div><strong>{Math.max(70, Math.round(95 - i * 3))}</strong></button>)}</Card>
        <Card><PanelHead icon={AlertTriangle} title="Bottom Performing Facilities" sub="Prioritized from live status"/>{facilities.filter(f => effective(f) !== "Healthy").slice(0, 5).map((f, i) => <button className="rank" key={f.facility_code} onClick={() => nav(`/facilities/${f.facility_code}`)}><span>{i + 1}</span><div><b>{f.facility_name}</b><small>{effective(f)}</small></div><strong className="red">{Math.max(35, 55 - i * 4)}</strong></button>)}</Card>
        <Card><PanelHead icon={Leaf} title="Resource Savings (Potential)" sub="Changes with current live signals"/><div className="savings"><div><span>Energy Opportunity</span><b className="green">{num(Math.max(0, energyTotal - energyExpected))} kWh</b><small>Current excess estimate</small></div><div><span>Water Opportunity</span><b className="cyan">{num(waterLoss, 2)} kL</b><small>Current unaccounted estimate</small></div><strong className="save-total">Potential impact updates with each telemetry cycle</strong></div></Card>
      </div>

      <Card className="table-card"><div className="table-head"><div><h2>Facility Performance Overview</h2><p>Live status across the connected portfolio</p></div><div className="search"><Search/><input placeholder="Search facility..."/></div></div><div className="table-scroll"><table><thead><tr><th>Facility</th><th>Status</th><th>Energy</th><th>Water</th><th>Latest Reading</th><th>Alerts</th><th></th></tr></thead><tbody>{facilities.slice(0, 10).map(f => { const l = live[f.facility_code]; const fAlerts = alerts.filter(a => a.facility_code === f.facility_code).length; return <tr key={f.facility_code}><td><b>{f.facility_name}</b><small>{f.facility_code} · {f.city}</small></td><td><span className={`status ${effective(f).toLowerCase().replaceAll(" ", "-")}`}>{effective(f)}</span></td><td>{l?.energy_kwh != null ? num(l.energy_kwh) : "—"} kWh</td><td>{l?.water_kl != null ? num(l.water_kl, 2) : "—"} kL</td><td>{l?.timestamp ? shortTime(l.timestamp) : "Waiting"}</td><td>{fAlerts}</td><td><button className="link" onClick={() => nav(`/facilities/${f.facility_code}`)}>Open →</button></td></tr>; })}</tbody></table></div></Card>

      <Card className="ai-panel"><PanelHead icon={Sparkles} title="AI Recommendations" sub="Generated from current realtime signals" to="/ai-insights"/><div className="rec-grid">{recommendations.map((r, i) => <button className="rec" key={i}><div><Lightbulb/></div><span><b>{r[0]}</b><small>{r[1]}</small></span><em>{r[2]}</em></button>)}</div></Card>
    </div>
  </div>;
}
