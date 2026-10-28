import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, Building2, CheckCircle2, Droplets, LoaderCircle, RefreshCw, ShieldCheck, Zap } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "./TALQLiveData.css";

const DEFAULT_URL = import.meta.env.VITE_TALQ_GATEWAY_URL || "https://flowsense-talq-gateway.onrender.com";
const fmt = (value, digits = 2) => Number.isFinite(Number(value)) ? Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits }) : "—";
const when = (value) => value && !Number.isNaN(new Date(value).getTime()) ? new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

async function getGateway(path, baseUrl, auth, signal) {
  const url = new URL(path, baseUrl.replace(/\/+$/, "") + "/");
  url.searchParams.set("clientAddress", auth.clientAddress);
  const response = await fetch(url, { headers: { "X-API-Key": auth.apiKey, "talq-api-version": "2.7.1", Accept: "application/json" }, signal });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Gateway request failed (${response.status})`);
  return body;
}

function Metric({ icon: Icon, title, value, note }) {
  return <section className="card talq-metric"><div className="talq-metric-icon"><Icon /></div><span>{title}</span><strong>{value}</strong><small>{note}</small></section>;
}

export default function TALQLiveData() {
  const [gatewayUrl, setGatewayUrl] = useState(DEFAULT_URL);
  const [keyInput, setKeyInput] = useState("");
  const [addressInput, setAddressInput] = useState("");
  const [auth, setAuth] = useState(null);
  const [facilities, setFacilities] = useState([]);
  const [facility, setFacility] = useState("all");
  const [devices, setDevices] = useState([]);
  const [energy, setEnergy] = useState([]);
  const [water, setWater] = useState([]);
  const [sensors, setSensors] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const abortRef = useRef(null);
  const baseUrl = gatewayUrl.trim().replace(/\/+$/, "");

  const load = useCallback(async (credentials = auth, background = false) => {
    if (!credentials) return;
    if (!baseUrl) {
      setError("Enter the gateway base URL.");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    background ? setRefreshing(true) : setLoading(true);
    setError("");
    const filter = facility === "all" ? "" : `&facility_code=${encodeURIComponent(facility)}`;
    const paths = [
      "/data/facilities?limit=100",
      `/data/devices?limit=500${filter}`,
      `/data/energy?hours=24&limit=500${filter}`,
      `/data/water?hours=24&limit=500${filter}`,
      `/data/alerts?limit=100${facility === "all" ? "" : `&facility_code=${encodeURIComponent(facility)}`}`
    ];
    try {
      const results = await Promise.allSettled(paths.map(path => getGateway(path, baseUrl, credentials, controller.signal)));
      if (controller.signal.aborted) return;
      const failed = results.filter(r => r.status === "rejected");
      const value = i => results[i].status === "fulfilled" ? results[i].value : null;
      const f = value(0), d = value(1), e = value(2), w = value(3), a = value(4);
      if (f) setFacilities(Array.isArray(f.facilities) ? f.facilities : []);
      if (d) setDevices(Array.isArray(d.devices) ? d.devices : []);
      if (e) setEnergy(Array.isArray(e.readings) ? e.readings : []);
      if (w) { setWater(Array.isArray(w.meter_readings) ? w.meter_readings : []); setSensors(Array.isArray(w.sensor_readings) ? w.sensor_readings : []); }
      if (a) setAlerts(Array.isArray(a.alerts) ? a.alerts : []);
      if (failed.length === results.length) throw failed[0].reason;
      if (failed.length) {
        const firstFailure = results.find(r => r.status === "rejected");
        setError(`Some sections failed to load: ${firstFailure?.reason?.message || "request failed"}`);
      }
      setLastUpdated(new Date());
    } catch (err) {
      if (err?.name !== "AbortError") setError(err?.message || "Could not connect to the gateway.");
    } finally {
      if (!controller.signal.aborted) { setLoading(false); setRefreshing(false); }
    }
  }, [auth, baseUrl, facility]);

  const connect = async event => {
    event.preventDefault();
    const address = addressInput.trim();
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(address)) {
      setError("Enter the valid clientAddress UUID associated with this API key."); return;
    }
    if (!keyInput.trim()) { setError("Paste your issued API key."); return; }
    const credentials = { apiKey: keyInput.trim(), clientAddress: address };
    setAuth(credentials);
    await load(credentials);
  };

  useEffect(() => {
    if (!auth) return undefined;
    const timer = window.setInterval(() => load(auth, true), 60000);
    return () => window.clearInterval(timer);
  }, [auth, load]);
  useEffect(() => () => abortRef.current?.abort(), []);

  const energyChart = useMemo(() => [...energy].slice().reverse().map(row => ({ time: when(row.reading_time), value: Number(row.reading_value), unit: row.unit || "" })).filter(row => Number.isFinite(row.value)), [energy]);
  const waterChart = useMemo(() => [...water].slice().reverse().map(row => ({ time: when(row.reading_time), value: Number(row.reading_value), unit: row.unit || "" })).filter(row => Number.isFinite(row.value)), [water]);
  const openAlerts = alerts.filter(row => !["resolved", "closed"].includes(String(row.status || "").toLowerCase())).length;

  return <div className="page"><div className="inner talq-live-page">
    <div className="page-title talq-live-heading"><div><div className="overline">FLOWSENSE / TALQ INTEGRATION</div><h1>TALQ Live Data</h1><p>Read-only data from the FlowSense gateway connected to Aurora PostgreSQL.</p></div><span className={`talq-connection ${auth ? "connected" : ""}`}><i />{auth ? "Connected" : "Not connected"}</span></div>
    {!auth && <form className="card talq-connect" onSubmit={connect}><div className="talq-connect-title"><ShieldCheck /><div><h2>Connect to the live gateway</h2><p>Credentials remain in page memory and are cleared when you disconnect or refresh.</p></div></div><div className="talq-fields"><label>Gateway URL<input type="url" required value={gatewayUrl} onChange={e => setGatewayUrl(e.target.value)} /></label><label>Client address (UUID)<input required autoComplete="off" value={addressInput} onChange={e => setAddressInput(e.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label><label className="talq-api-key-field">Issued API key<input type="password" required autoComplete="off" value={keyInput} onChange={e => setKeyInput(e.target.value)} placeholder="Paste API key issued after Telegram verification" /></label></div><div className="talq-connect-bottom"><span>Uses X-API-Key and talq-api-version: 2.7.1</span><button className="btn btn-primary" disabled={loading}>{loading ? "Connecting…" : "Connect & load data"}</button></div></form>}
    {auth && <div className="card talq-live-toolbar"><div><strong><CheckCircle2 /> Live gateway session</strong><small>{lastUpdated ? `Last refreshed ${lastUpdated.toLocaleTimeString()}` : "Loading data"} · auto-refresh every 60 seconds</small></div><label>Facility<select value={facility} onChange={e => setFacility(e.target.value)}><option value="all">All facilities</option>{facilities.map(f => <option key={f.facility_code} value={f.facility_code}>{f.facility_name || f.facility_code}</option>)}</select></label><button className="btn btn-secondary" type="button" onClick={() => load(auth, true)} disabled={refreshing}><RefreshCw className={refreshing ? "talq-spin" : ""}/> Refresh</button><button className="btn btn-secondary" type="button" onClick={() => { abortRef.current?.abort(); setAuth(null); setKeyInput(""); setAddressInput(""); setError(""); setLastUpdated(null); }}>Disconnect</button></div>}
    {error && <div className="talq-live-error"><AlertTriangle /><span>{error}</span>{auth && <button type="button" onClick={() => load(auth)}>Retry</button>}</div>}
    {!auth ? <div className="card talq-live-empty"><Activity /><h2>Connect to see live data</h2><p>Use the key and UUID issued for the same approved client. No sample or synthetic readings are shown.</p></div> : <>
      {loading && !lastUpdated ? <div className="card talq-live-loading"><LoaderCircle className="talq-spin"/> Querying live gateway endpoints…</div> : <div className="grid kpi-grid talq-live-metrics">
        <Metric icon={Building2} title="Facilities" value={facilities.length} note="Live API results" />
        <Metric icon={Activity} title="Devices" value={devices.length} note={`${devices.filter(d => d.last_seen_at).length} with last-seen timestamp`} />
        <Metric icon={Zap} title="Latest energy" value={energy.length ? fmt(energy[0].reading_value) : "—"} note={energy.length ? `${energy[0].unit || "unit"} · ${when(energy[0].reading_time)}` : "No readings returned"} />
        <Metric icon={Droplets} title="Latest water" value={water.length ? fmt(water[0].reading_value) : "—"} note={water.length ? `${water[0].unit || "unit"} · ${when(water[0].reading_time)}` : "No readings returned"} />
        <Metric icon={AlertTriangle} title="Open alerts" value={openAlerts} note={`${alerts.length} alert records returned`} />
        <Metric icon={Droplets} title="Water sensor samples" value={sensors.length} note="Sensor readings in 24 hours" />
      </div>}
      <div className="grid grid-2 talq-live-charts">
        <section className="card talq-live-chart"><div className="panel-head"><div><h2><Zap /> Energy readings</h2><p>Last 24 hours from the live gateway</p></div><span>{energy.length} records</span></div>{energyChart.length ? <ResponsiveContainer width="100%" height={260}><LineChart data={energyChart}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="time" minTickGap={30}/><YAxis/><Tooltip formatter={(v, _, item) => [`${fmt(v)} ${item?.payload?.unit || ""}`, "Reading"]}/><Line dataKey="value" type="monotone" stroke="#f0a32b" dot={false} strokeWidth={2}/></LineChart></ResponsiveContainer> : <p className="talq-no-data">No energy readings returned.</p>}</section>
        <section className="card talq-live-chart"><div className="panel-head"><div><h2><Droplets /> Water readings</h2><p>Last 24 hours from the live gateway</p></div><span>{water.length} records</span></div>{waterChart.length ? <ResponsiveContainer width="100%" height={260}><LineChart data={waterChart}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="time" minTickGap={30}/><YAxis/><Tooltip formatter={(v, _, item) => [`${fmt(v)} ${item?.payload?.unit || ""}`, "Reading"]}/><Line dataKey="value" type="monotone" stroke="#2188e8" dot={false} strokeWidth={2}/></LineChart></ResponsiveContainer> : <p className="talq-no-data">No water readings returned.</p>}</section>
      </div>
      <section className="card talq-live-table"><div className="panel-head"><div><h2><AlertTriangle /> Alerts & anomalies</h2><p>Latest records returned by the gateway</p></div><span>{alerts.length} records</span></div><div className="table-scroll"><table><thead><tr><th>Severity</th><th>Alert</th><th>Facility</th><th>Resource</th><th>Deviation</th><th>Status</th><th>Triggered</th></tr></thead><tbody>{alerts.length ? alerts.map(a => <tr key={a.alert_id}><td><span className={`talq-severity talq-${String(a.severity || "info").toLowerCase()}`}>{a.severity || "Info"}</span></td><td><strong>{a.alert_title || a.anomaly_type || "Alert"}</strong><small>{a.alert_message || a.anomaly_description || "—"}</small></td><td>{a.facility_name || a.facility_code || "—"}</td><td>{a.resource_type || "—"}</td><td>{a.deviation_percent == null ? "—" : `${fmt(a.deviation_percent)}%`}</td><td>{a.status || "—"}</td><td>{when(a.triggered_at)}</td></tr>) : <tr><td colSpan={7} className="no-results">No alert records returned.</td></tr>}</tbody></table></div></section>
      <section className="card talq-live-table"><div className="panel-head"><div><h2><Activity /> Devices</h2><p>Device status and last-seen data</p></div><span>{devices.length} devices</span></div><div className="table-scroll"><table><thead><tr><th>Device</th><th>Facility</th><th>Model</th><th>Protocol</th><th>Status</th><th>Last seen</th></tr></thead><tbody>{devices.length ? devices.map(d => <tr key={d.iot_device_id}><td><strong>{d.device_name || d.device_code || "Device"}</strong><small>{d.device_code || d.iot_device_id}</small></td><td>{d.facility_name || d.facility_code || "—"}</td><td>{d.device_model || "—"}</td><td>{d.communication_protocol || "—"}</td><td>{d.status || "Unknown"}</td><td>{when(d.last_seen_at)}</td></tr>) : <tr><td colSpan={6} className="no-results">No devices returned.</td></tr>}</tbody></table></div></section>
      <section className="card talq-live-table"><div className="panel-head"><div><h2><Droplets /> Water sensor readings</h2><p>Water-related telemetry exposed by the gateway</p></div><span>{sensors.length} records</span></div><div className="table-scroll"><table><thead><tr><th>Sensor</th><th>Facility</th><th>Measurement</th><th>Value</th><th>Unit</th><th>Quality</th><th>Time</th></tr></thead><tbody>{sensors.slice(0,100).map((s,i) => <tr key={`${s.sensor_code || "sensor"}-${s.reading_time || i}`}><td><strong>{s.sensor_name || s.sensor_code || "Sensor"}</strong><small>{s.sensor_code || "—"}</small></td><td>{s.facility_name || s.facility_code || "—"}</td><td>{s.measurement || "—"}</td><td>{s.numeric_value != null ? fmt(s.numeric_value) : s.boolean_value == null ? "—" : String(s.boolean_value)}</td><td>{s.unit || "—"}</td><td>{s.quality_status || "—"}</td><td>{when(s.reading_time)}</td></tr>)}{!sensors.length && <tr><td colSpan={7} className="no-results">No sensor readings returned.</td></tr>}</tbody></table></div></section>
    </>}
    <p className="talq-live-footnote">Read-only integration · API key is kept in component memory only · auto-refreshes every 60 seconds while connected.</p>
  </div></div>;
}
