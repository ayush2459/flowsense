const API_BASE = "http://localhost:8000";

async function apiGet(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

// ---------- Mock fallbacks (used only if the backend call fails, so the UI
// stays demo-able even before the DB/backend is wired up) ----------
const MOCK = {
  portfolio: {
    total_facilities: 100, healthy: 63, needs_attention: 27, critical: 10,
    total_energy_gwh: 18.4, total_water_ml: 42.8, total_cost_cr: 2.48, total_emissions_tco2: 5684,
    energy_score: 81, water_score: 76,
  },
  facilities: [
    { facility_code: "FS-FAC-004", facility_name: "Green Tech Park", city: "Noida", state: "UP", status: "Healthy", energy_score: 94, water_score: 95, overall_score: 94, alerts: 0 },
    { facility_code: "FS-FAC-018", facility_name: "Alpha Industries", city: "Pune", state: "MH", status: "Healthy", energy_score: 91, water_score: 88, overall_score: 90, alerts: 0 },
    { facility_code: "FS-FAC-027", facility_name: "Sunrise Hospital", city: "Jaipur", state: "RJ", status: "Needs Attention", energy_score: 68, water_score: 70, overall_score: 69, alerts: 2 },
    { facility_code: "FS-FAC-061", facility_name: "Beta Pharma", city: "Hyderabad", state: "TG", status: "Needs Attention", energy_score: 73, water_score: 61, overall_score: 67, alerts: 2 },
    { facility_code: "FS-FAC-083", facility_name: "City Mall", city: "Bengaluru", state: "KA", status: "Critical", energy_score: 41, water_score: 45, overall_score: 41, alerts: 3 },
  ],
  anomalies: [
    { severity: "Critical", anomaly_type: "High Water Loss Detected", facility_code: "#27 Sunrise Hospital", detected_at: new Date().toISOString(), status: "New" },
    { severity: "Critical", anomaly_type: "Energy Anomaly", facility_code: "#83 City Mall", detected_at: new Date().toISOString(), status: "New" },
    { severity: "High", anomaly_type: "Low Treatment Rate", facility_code: "#61 Beta Pharma", detected_at: new Date().toISOString(), status: "In Progress" },
    { severity: "High", anomaly_type: "Night-time Energy Spike", facility_code: "#42 Food Park", detected_at: new Date().toISOString(), status: "New" },
    { severity: "High", anomaly_type: "Possible Water Leak", facility_code: "#14 Tech Tower", detected_at: new Date().toISOString(), status: "New" },
    { severity: "Medium", anomaly_type: "Pump Running Inefficiently", facility_code: "#18 Alpha Industries", detected_at: new Date().toISOString(), status: "Acknowledged" },
  ],
  recommendations: [
    { icon: "\u26A1", color: "amber", title: "Optimize HVAC Scheduling", desc: "Adjust HVAC timings based on occupancy and outdoor temperature.", facility: "Facility #27", impact: "High", savings: "\u20B92.4 L / month" },
    { icon: "\uD83D\uDCA7", color: "blue", title: "Fix Water Leakage", desc: "Multiple indicators suggest possible leak in water pipeline.", facility: "Facility #14", impact: "High", savings: "\u20B91.2 L / month" },
    { icon: "\u2699", color: "amber", title: "Improve Pump Efficiency", desc: "Pump is running below optimal efficiency range.", facility: "Facility #61", impact: "Medium", savings: "\u20B91.8 L / month" },
    { icon: "\u267B", color: "green", title: "Increase Water Reuse", desc: "Reuse rate can be improved with better treatment control.", facility: "Facility #33", impact: "Medium", savings: "\u20B90.8 L / month" },
    { icon: "\uD83D\uDCA1", color: "purple", title: "Lighting Optimization", desc: "Replace high wattage lights with energy efficient LEDs.", facility: "Facility #72", impact: "Low", savings: "\u20B90.9 L / month" },
  ],
};

async function getFacilities() {
  try { return await apiGet("/api/facilities"); }
  catch (e) { return MOCK.facilities; }
}

async function getFacilitySummary(code) {
  try { return await apiGet(`/api/facilities/${code}/summary`); }
  catch (e) { return null; }
}

async function getFacilityAnomalies(code) {
  try { return await apiGet(`/api/facilities/${code}/anomalies`); }
  catch (e) { return null; }
}

async function getRecentAnomalies() {
  try { return await apiGet(`/api/anomalies/recent`); }
  catch (e) { return MOCK.anomalies; }
}

async function getFacilityEnergyTrend(code, hours = 24) {
  try { return await apiGet(`/api/facilities/${code}/energy?hours=${hours}`); }
  catch (e) { return null; }
}

async function getFacilityWaterTrend(code, hours = 24) {
  try { return await apiGet(`/api/facilities/${code}/water?hours=${hours}`); }
  catch (e) { return null; }
}

async function getFacilityReconciliation(code) {
  try { return await apiGet(`/api/facilities/${code}/reconciliation`); }
  catch (e) { return null; }
}

async function getFacilityYearlySummary(code) {
  try { return await apiGet(`/api/facilities/${code}/yearly-summary`); }
  catch (e) { return null; }
}
