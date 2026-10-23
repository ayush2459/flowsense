import { useEffect, useMemo, useState } from "react";

const METRICS = [
  { key: "energy", label: "Energy", aliases: ["energy_kwh", "total_energy_kwh"], unit: "kWh", aggregate: "sum" },
  { key: "water", label: "Water", aliases: ["water_kl", "total_water_kl"], unit: "kL", aggregate: "sum" },
  { key: "power_factor", label: "Power Factor", aliases: ["powerFactor", "pf"], unit: "", aggregate: "electrical" },
  { key: "load_factor", label: "Load Factor", aliases: ["loadFactor", "lf"], unit: "%", aggregate: "electrical" },
];

const COLORS = {
  green: ["#dcfce7", "#166534", "IN RANGE"],
  red: ["#fee2e2", "#991b1b", "ABOVE RANGE"],
  orange: ["#ffedd5", "#9a3412", "OUT OF RANGE"],
  grey: ["#e2e8f0", "#475569", "INSUFFICIENT DATA"],
};

const FACILITY_OPTIONS = [
  { value: "all", label: "All Facilities" },
  ...Array.from({ length: 100 }, (_, i) => {
    const code = `FS-FAC-${String(i + 1).padStart(3, "0")}`;
    return { value: code, label: code };
  }),
];

function numeric(value) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "object") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function findMetric(report, def) {
  const roots = [
    report?.resource_discrepancy,
    report?.detection?.resource_discrepancy,
    report?.data?.resource_discrepancy,
    report,
  ].filter(Boolean);

  const keys = [def.key, ...def.aliases];

  for (const root of roots) {
    const candidates = [
      root?.metrics?.[def.key],
      root?.results?.[def.key],
      root?.values?.[def.key],
      root?.[def.key],
      root?.telemetry?.[def.key],
      root?.data?.[def.key],
      root?.metrics,
      root?.results,
      root?.values,
      root?.telemetry,
      root?.data,
      root,
    ];

    for (const node of candidates) {
      if (!node || typeof node !== "object" || Array.isArray(node)) continue;

      let metricNode = node;
      if (node[def.key] && typeof node[def.key] === "object") {
        metricNode = node[def.key];
      } else {
        for (const key of keys) {
          if (node[key] !== undefined && node[key] !== null) {
            const value = node[key];
            if (typeof value === "object" && !Array.isArray(value)) {
              metricNode = value;
              break;
            }
            const number = numeric(value);
            if (number !== null) {
              return {
                actual: number,
                expected: numeric(
                  node[`expected_${key}`] ??
                  node[`expected_${def.key}`]
                ),
                status: "grey",
              };
            }
          }
        }
      }

      const actual = numeric(
        metricNode.value ??
        metricNode.actual ??
        metricNode.current ??
        metricNode.measured ??
        metricNode.reading
      );

      if (actual === null) continue;

      const expected = numeric(
        metricNode.expected ??
        metricNode.expected_value ??
        metricNode.baseline ??
        metricNode.target
      );

      const raw = String(
        metricNode.alert_color ??
        metricNode.color ??
        metricNode.status ??
        metricNode.severity ??
        ""
      ).toLowerCase();

      let status = "grey";
      if (["red", "critical", "above_range", "exceeded"].some(x => raw.includes(x))) {
        status = "red";
      } else if (["orange", "warning", "below_range", "below_expected", "under"].some(x => raw.includes(x))) {
        status = "orange";
      } else if (["green", "balanced", "normal", "within_range", "healthy"].some(x => raw.includes(x))) {
        status = "green";
      }

      return { actual, expected, status };
    }
  }

  return { actual: null, expected: null, status: "grey" };
}

function statusFor(metric, def) {
  if (metric.actual === null) return "grey";

  // Prefer the backend's authoritative status/alert colour when available.
  if (metric.status && metric.status !== "grey") {
    return metric.status;
  }

  const value = metric.actual;

  if (def.key === "power_factor") {
    if (value < 0.90) return "red";
    if (value < 0.97 || value > 0.98) return "orange";
    return "green";
  }

  if (def.key === "load_factor") {
    const normalized = value > 1 && value <= 100 ? value / 100 : value;
    if (normalized < 0.50 || normalized > 1) return "red";
    if (normalized < 0.65 || normalized > 0.85) return "orange";
    return "green";
  }

  if (metric.expected !== null && metric.expected > 0) {
    const deviation = (value - metric.expected) / metric.expected;
    if (deviation > 0.10) return "red";
    if (deviation > 0.05 || deviation < -0.05) return "orange";
    return "green";
  }

  return "grey";
}

function fmt(value, unit = "") {
  if (value === null || value === undefined) return "—";
  const n = numeric(value);
  if (n === null) return "—";
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 3 })}${unit ? ` ${unit}` : ""}`;
}

function getCode(report) {
  return report?.facility_code || report?.facilityCode || report?.facility?.facility_code || null;
}

function MetricCard({ def, metric }) {
  const status = statusFor(metric, def);
  const color = COLORS[status] || COLORS.grey;
  const displayValue =
    def.key === "load_factor" && metric.actual !== null
      ? fmt(metric.actual > 1 && metric.actual <= 100 ? metric.actual : metric.actual * 100, "%")
      : fmt(metric.actual, def.unit);

  return (
    <div style={{ padding: 12, borderRadius: 10, background: color[0], color: color[1], minWidth: 0 }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{def.label}</div>
      <div style={{ fontSize: 19, fontWeight: 800, margin: "7px 0", overflowWrap: "anywhere" }}>
        {displayValue}
      </div>
      {metric.expected !== null && (
        <div style={{ fontSize: 11 }}>Expected: {fmt(metric.expected, def.unit)}</div>
      )}
      <div style={{ fontSize: 10, fontWeight: 800, marginTop: 8 }}>{color[2]}</div>
    </div>
  );
}

export default function ResourceDiscrepancyAlerts() {
  const [facilities, setFacilities] = useState({});
  const [selectedFacility, setSelectedFacility] = useState("all");

  useEffect(() => {
    const receive = (event) => {
      const report = event.detail;
      if (!report || typeof report !== "object") return;

      const code = getCode(report);
      if (!code) return;

      setFacilities(previous => ({
        ...previous,
        [code]: {
          ...(previous[code] || {}),
          ...report,
          facility_code: code,
        },
      }));
    };

    window.addEventListener("flowsense:resource-discrepancy", receive);
    return () => window.removeEventListener("flowsense:resource-discrepancy", receive);
  }, []);

  const rows = useMemo(
    () => Object.values(facilities).sort((a, b) =>
      String(a.facility_code).localeCompare(String(b.facility_code))
    ),
    [facilities]
  );

  const selectedRows = selectedFacility === "all"
    ? rows
    : rows.filter(f => f.facility_code === selectedFacility);

  const summary = useMemo(() => {
    return METRICS.map(def => {
      const readings = selectedRows
        .map(f => ({ facility: f, metric: findMetric(f, def) }))
        .filter(x => x.metric.actual !== null);

      if (def.aggregate === "sum") {
        const actual = readings.length
          ? readings.reduce((sum, x) => sum + x.metric.actual, 0)
          : null;

        const expectedReadings = readings.filter(x => x.metric.expected !== null);
        const expected = expectedReadings.length
          ? expectedReadings.reduce((sum, x) => sum + x.metric.expected, 0)
          : null;

        return {
          def,
          metric: {
            actual,
            expected,
            status: actual === null ? "grey" : "grey",
          },
          coverage: readings.length,
        };
      }

      // For All Facilities, show a clearly labelled mean of available
      // facility ratios. This is descriptive only, not a weighted portfolio metric.
      if (selectedFacility === "all") {
        const electricalReadings = readings.filter(
          x => x.metric.actual !== null
        );
        const actual = electricalReadings.length
          ? electricalReadings.reduce((sum, x) => sum + x.metric.actual, 0)
              / electricalReadings.length
          : null;

        const statuses = electricalReadings.map(
          x => statusFor(x.metric, def)
        );
        const status = statuses.includes("red")
          ? "red"
          : statuses.includes("orange")
            ? "orange"
            : statuses.length && statuses.every(x => x === "green")
              ? "green"
              : "grey";

        return {
          def: { ...def, label: `Average ${def.label}` },
          metric: { actual, expected: null, status },
          coverage: electricalReadings.length,
        };
      }

      const one = selectedRows[0];
      return {
        def,
        metric: one ? findMetric(one, def) : { actual: null, expected: null, status: "grey" },
        coverage: readings.length,
      };
    });
  }, [rows, selectedRows, selectedFacility]);

  const available = selectedFacility === "all" ? rows.length : selectedRows.length;
  const missing = selectedFacility === "all" ? available < 100 : available === 0;

  const overallStatus = summary.some(x => statusFor(x.metric, x.def) === "red")
    ? "red"
    : summary.some(x => statusFor(x.metric, x.def) === "orange")
      ? "orange"
      : summary.some(x => statusFor(x.metric, x.def) === "grey")
        ? "grey"
        : "green";

  const title = selectedFacility === "all"
    ? "All Facilities · Portfolio Summary"
    : selectedFacility;

  // Live discrepancy reports may arrive directly or nested inside an event payload.
  const selectedReport = selectedFacility !== "all" ? selectedRows[0] : null;
  const scoreReport =
    selectedReport?.resource_discrepancy ??
    selectedReport?.data?.resource_discrepancy ??
    selectedReport?.detection?.resource_discrepancy ??
    (selectedReport?.metrics ? selectedReport : null);

  const discrepancyScore = scoreReport?.discrepancy_score;
  const excessScore = scoreReport?.excess_consumption_score;
  const crossResource = scoreReport?.cross_resource_indicator;
  const scoreSeverity = scoreReport?.severity ?? "insufficient_data";

  const displayScore = value =>
    typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}/100` : "Not available";

  return (
    <section style={{ margin: "18px 0", padding: 18, border: "1px solid #dbe2ea", borderRadius: 16, background: "var(--card, #fff)" }}>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 1 }}>PHASE 2 · LIVE RESOURCE MONITORING</div>
          <h2 style={{ margin: "5px 0" }}>Resource Discrepancy Alerts</h2>
          <p style={{ marginTop: 4, fontSize: 12, opacity: 0.75 }}>
            Live actual-versus-expected readings for the selected portfolio or facility.
          </p>
        </div>
        <span style={{ padding: "7px 10px", borderRadius: 20, background: COLORS[overallStatus][0], color: COLORS[overallStatus][1], fontSize: 11, fontWeight: 800 }}>
          {selectedFacility === "all"
            ? `${rows.length}/100 FACILITIES RECEIVED`
            : selectedRows.length
              ? "FACILITY DATA RECEIVED"
              : "WAITING FOR LIVE DATA"}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 1fr) minmax(160px, auto)", gap: 12, alignItems: "end", margin: "16px 0" }}>
        <label style={{ display: "grid", gap: 6, fontSize: 12, fontWeight: 700 }}>
          Select facility
          <select
            value={selectedFacility}
            onChange={e => setSelectedFacility(e.target.value)}
            style={{ width: "100%", padding: "11px 12px", borderRadius: 9, border: "1px solid #cbd5e1", background: "var(--card, #fff)", color: "inherit" }}
          >
            {FACILITY_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <div style={{ fontSize: 12, opacity: 0.75 }}>
          {selectedFacility === "all"
            ? "Showing consolidated readings only"
            : "Showing this facility only"}
        </div>
      </div>

      {selectedFacility === "all" && (
        <div style={{ padding: 12, marginBottom: 12, borderRadius: 10, background: "#f1f5f9", color: "#334155", fontSize: 12 }}>
          Portfolio totals combine the readings received from the live event stream. Missing facilities are not assumed to have zero consumption.
        </div>
      )}

      {!available ? (
        <div style={{ padding: 14, background: COLORS.grey[0], borderRadius: 10, color: COLORS.grey[1] }}>
          Waiting for live telemetry for this selection. Missing data is not classified as healthy.
        </div>
      ) : (
        <>
          <div style={{ fontWeight: 800, margin: "12px 0" }}>{title}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
            {summary.map(({ def, metric }) => (
              <MetricCard key={def.key} def={def} metric={metric} />
            ))}
          </div>

          {selectedFacility !== "all" && selectedRows[0] && (
            <div style={{
              marginTop: 14,
              padding: 14,
              border: "1px solid #dbe2ea",
              borderRadius: 12,
              background: "var(--card, #fff)"
            }}>
              <div style={{ fontWeight: 800, marginBottom: 10 }}>
                Consumption Discrepancy Scoring
              </div>

              {scoreReport ? (
                <>
                  <div style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                    gap: 10
                  }}>
                    <div style={{ padding: 12, borderRadius: 9, background: "#f1f5f9" }}>
                      <div style={{ fontSize: 12, color: "#475569" }}>Discrepancy score</div>
                      <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>
                        {displayScore(discrepancyScore)}
                      </div>
                      <div style={{ fontSize: 11, marginTop: 4, color: "#64748b" }}>
                        Magnitude of deviation
                      </div>
                    </div>

                    <div style={{ padding: 12, borderRadius: 9, background: "#fff7ed" }}>
                      <div style={{ fontSize: 12, color: "#9a3412" }}>Excess-consumption score</div>
                      <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4, color: "#9a3412" }}>
                        {displayScore(excessScore)}
                      </div>
                      <div style={{ fontSize: 11, marginTop: 4, color: "#9a3412" }}>
                        Above-baseline consumption only
                      </div>
                    </div>

                    <div style={{ padding: 12, borderRadius: 9, background: "#f1f5f9" }}>
                      <div style={{ fontSize: 12, color: "#475569" }}>Severity</div>
                      <div style={{ fontSize: 17, fontWeight: 800, marginTop: 7, textTransform: "capitalize" }}>
                        {String(scoreSeverity).replaceAll("_", " ")}
                      </div>
                    </div>

                    <div style={{ padding: 12, borderRadius: 9, background: "#f1f5f9" }}>
                      <div style={{ fontSize: 12, color: "#475569" }}>Cross-resource indicator</div>
                      <div style={{ fontSize: 15, fontWeight: 800, marginTop: 7, overflowWrap: "anywhere" }}>
                        {String(crossResource?.status ?? "insufficient_data").replaceAll("_", " ")}
                      </div>
                    </div>
                  </div>

                  {crossResource?.interpretation && (
                    <p style={{ fontSize: 12, lineHeight: 1.5, color: "#64748b", margin: "10px 0 0" }}>
                      {crossResource.interpretation}
                    </p>
                  )}
                </>
              ) : (
                <p style={{ margin: 0, fontSize: 12, color: COLORS.grey[1] }}>
                  Live metric readings are available, but this event does not contain the facility-level scoring fields. The backend may need to publish the updated discrepancy report.
                </p>
              )}
            </div>
          )}
          {selectedFacility === "all" && rows.length < 100 && (
            <p style={{ marginTop: 12, fontSize: 12, color: COLORS.grey[1] }}>
              Waiting for telemetry from {100 - rows.length} facilities. Portfolio totals currently include only facilities that have sent readings.
            </p>
          )}
          {selectedFacility !== "all" && selectedRows[0] && (
            <p style={{ marginTop: 12, fontSize: 12, opacity: 0.7 }}>
              Last update: {selectedRows[0].updated_at || selectedRows[0].timestamp || selectedRows[0].detected_at || "Most recent received event"}
            </p>
          )}
        </>
      )}
    </section>
  );
}

