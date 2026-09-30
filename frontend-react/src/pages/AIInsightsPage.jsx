import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Building2,
  CheckCircle2,
  ChevronDown,
  Droplets,
  Loader2,
  RefreshCw,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";
import { useFlowSense } from "../context/FlowSenseContext";
import { api } from "../services/api";
import "./AIInsightsPage.css";

const PERIODS = [
  ["24h", "Last 24 hours"],
  ["7d", "Last 7 days"],
  ["30d", "Last 30 days"],
];

const txt = (v) =>
  v === null || v === undefined || v === "" ? "—" : String(v);

function Items({ title, items, Icon }) {
  if (!Array.isArray(items) || !items.length) {
    return null;
  }

  return (
    <section className="ai-block">
      <header>
        <Icon size={18} />

        <div>
          <b>{title}</b>
          <small>{items.length} items</small>
        </div>
      </header>

      {items.map((x, i) => (
        <div className="ai-item" key={i}>
          <span>{i + 1}</span>
          <p>{x}</p>
        </div>
      ))}
    </section>
  );
}

export default function AIInsightsPage() {
  const {
    facilityList = [],
    alerts = [],
  } = useFlowSense();

  const [scope, setScope] = useState("all");
  const [period, setPeriod] = useState("24h");
  const [q, setQ] = useState("");
  const [scopeOpen, setScopeOpen] = useState(false);
  const [periodOpen, setPeriodOpen] = useState(false);
  const [result, setResult] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const facilities = useMemo(
    () =>
      [...facilityList].sort((a, b) =>
        String(a.facility_code || "").localeCompare(
          String(b.facility_code || "")
        )
      ),
    [facilityList]
  );

  const filtered = useMemo(() => {
    const x = q.toLowerCase().trim();

    if (!x) {
      return facilities;
    }

    return facilities.filter((f) =>
      `${f.facility_code || ""} ${f.facility_name || ""}`
        .toLowerCase()
        .includes(x)
    );
  }, [facilities, q]);

  const selected = facilities.find(
    (f) => f.facility_code === scope
  );

  const generate = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    setEvidence(null);

    try {
      const r =
        scope === "all"
          ? await api.aiPortfolioAnalysis(period)
          : await api.aiReportAnalysis(scope, period);

      if (!r?.success) {
        throw new Error(
          r?.error || "Analysis failed"
        );
      }

      setResult(r.analysis);
      setEvidence(r.evidence_summary || null);
    } catch (e) {
      setError(
        e?.name === "AbortError"
          ? "Ollama timed out. Try again after the model warms up."
          : e?.message ||
            "Unable to generate analysis."
      );
    } finally {
      setLoading(false);
    }
  };

  const critical = alerts.filter(
    (a) =>
      String(
        a.severity ||
          a.priority ||
          a.level ||
          ""
      ).toLowerCase() === "critical"
  ).length;

  const energy = alerts.filter((a) =>
    String(
      a.resource_type ||
        a.resource ||
        a.type ||
        ""
    )
      .toLowerCase()
      .includes("energy")
  ).length;

  const water = alerts.filter((a) =>
    String(
      a.resource_type ||
        a.resource ||
        a.type ||
        ""
    )
      .toLowerCase()
      .includes("water")
  ).length;

  return (
    <main className="ai-page">
      <div className="ai-head">
        <div>
          <label>FLOWSENSE / INTELLIGENCE</label>

          <h1>
            <span>
              <Sparkles size={24} />
            </span>
            AI Insights
          </h1>

          <p>
            Evidence-backed intelligence across the
            FlowSense resource network.
          </p>
        </div>

        <div className="ai-engine">
          <i />

          <div>
            <b>Local Ollama</b>
            <small>
              llama3.2:3b · on demand
            </small>
          </div>
        </div>
      </div>

      <section className="ai-command">
        <div>
          <label>ANALYSIS SCOPE</label>

          <h2>
            {scope === "all"
              ? "Portfolio Intelligence"
              : selected?.facility_name || scope}
          </h2>

          <p>
            {scope === "all"
              ? `One AI request using all ${facilities.length} facilities.`
              : `One AI request for ${scope}.`}
          </p>
        </div>

        <div className="ai-controls">
          <div className="ai-dd">
            <button
              className="ai-select"
              onClick={() =>
                setScopeOpen(!scopeOpen)
              }
            >
              <Building2 size={16} />

              <span>
                {scope === "all"
                  ? `All Facilities · ${facilities.length}`
                  : `${scope} · ${
                      selected?.facility_name ||
                      "Facility"
                    }`}
              </span>

              <ChevronDown size={16} />
            </button>

            {scopeOpen && (
              <div className="ai-menu">
                <button
                  className={
                    scope === "all"
                      ? "active"
                      : ""
                  }
                  onClick={() => {
                    setScope("all");
                    setScopeOpen(false);
                    setResult(null);
                  }}
                >
                  <Building2 size={16} />

                  <div>
                    <b>All Facilities</b>
                    <small>
                      {facilities.length} facilities ·
                      one analysis
                    </small>
                  </div>
                </button>

                <input
                  value={q}
                  onChange={(e) =>
                    setQ(e.target.value)
                  }
                  placeholder="Search facility..."
                />

                <div className="ai-facilities">
                  {filtered.map((f) => (
                    <button
                      key={f.facility_code}
                      className={
                        scope === f.facility_code
                          ? "active"
                          : ""
                      }
                      onClick={() => {
                        setScope(
                          f.facility_code
                        );
                        setScopeOpen(false);
                        setResult(null);
                      }}
                    >
                      <b>{f.facility_code}</b>

                      <small>
                        {f.facility_name ||
                          "Facility"}
                      </small>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="ai-dd">
            <button
              className="ai-select"
              onClick={() =>
                setPeriodOpen(!periodOpen)
              }
            >
              <Target size={16} />

              <span>
                {
                  PERIODS.find(
                    (x) => x[0] === period
                  )?.[1]
                }
              </span>

              <ChevronDown size={16} />
            </button>

            {periodOpen && (
              <div className="ai-menu ai-period">
                {PERIODS.map(([v, l]) => (
                  <button
                    key={v}
                    className={
                      period === v
                        ? "active"
                        : ""
                    }
                    onClick={() => {
                      setPeriod(v);
                      setPeriodOpen(false);
                      setResult(null);
                    }}
                  >
                    {l}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            className="ai-generate"
            onClick={generate}
            disabled={
              loading || !facilities.length
            }
          >
            {loading ? (
              <Loader2
                className="spin"
                size={17}
              />
            ) : (
              <Sparkles size={17} />
            )}

            {loading
              ? "Generating..."
              : "Generate Insight"}
          </button>
        </div>
      </section>

      <div className="ai-kpis">
        {[
          [
            Building2,
            scope === "all"
              ? facilities.length
              : 1,
            "FACILITIES",
          ],
          [
            Activity,
            alerts.length,
            "SIGNALS",
          ],
          [
            AlertTriangle,
            critical,
            "CRITICAL",
          ],
          [
            Zap,
            energy,
            "ENERGY",
          ],
          [
            Droplets,
            water,
            "WATER",
          ],
        ].map(([I, v, l]) => (
          <div
            className="ai-kpi"
            key={l}
          >
            <I />

            <strong>{v}</strong>

            <small>{l}</small>
          </div>
        ))}
      </div>

      {loading && (
        <div className="ai-loading">
          <Sparkles size={22} />

          <div>
            <b>
              Generating evidence-backed insight
            </b>

            <p>
              Preparing FlowSense evidence and making
              one local Ollama request.
            </p>
          </div>

          <Loader2
            className="spin"
            size={20}
          />
        </div>
      )}

      {error && (
        <div className="ai-error">
          <AlertTriangle size={20} />

          <div>
            <b>Analysis unavailable</b>

            <p>{error}</p>
          </div>

          <button onClick={generate}>
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      )}

      {!loading &&
        !error &&
        !result && (
          <div className="ai-empty">
            <div>
              <Sparkles size={28} />
            </div>

            <h2>Ready to analyze</h2>

            <p>
              Select a facility or All Facilities,
              choose the evidence window, then
              generate the insight.
            </p>

            <small>
              <CheckCircle2 size={14} />
              No automatic Ollama calls
            </small>
          </div>
        )}

      {result && !loading && (
        <>
          <section className="ai-summary">
            <div className="ai-result-head">
              <div>
                <label>
                  GENERATED INSIGHT
                </label>

                <h2>
                  {scope === "all"
                    ? "Portfolio Intelligence"
                    : selected?.facility_name ||
                      scope}
                </h2>
              </div>

              <button onClick={generate}>
                <RefreshCw size={14} />
                Refresh
              </button>
            </div>

            <p>{txt(result.summary)}</p>

            {evidence && (
              <div className="ai-evidence">
                <span>
                  {txt(evidence.energy_kwh)} kWh
                  energy
                </span>

                <span>
                  {txt(evidence.water_kl)} kL
                  water
                </span>

                <span>
                  {txt(evidence.anomaly_count)}{" "}
                  anomalies
                </span>

                <span>
                  {txt(
                    evidence.critical_facilities
                  )}{" "}
                  critical facilities
                </span>
              </div>
            )}
          </section>

          <div className="ai-analysis">
            <section className="ai-card">
              <header>
                <Zap />

                <div>
                  <b>Energy Intelligence</b>

                  <small>
                    Backend evidence interpreted by
                    Ollama
                  </small>
                </div>
              </header>

              <p>
                {txt(result.energy_analysis)}
              </p>
            </section>

            <section className="ai-card">
              <header>
                <Droplets />

                <div>
                  <b>Water Intelligence</b>

                  <small>
                    Backend evidence interpreted by
                    Ollama
                  </small>
                </div>
              </header>

              <p>
                {txt(result.water_analysis)}
              </p>
            </section>
          </div>

          <Items
            title="Key Findings"
            items={result.key_findings}
            Icon={Activity}
          />

          {scope === "all" && (
            <Items
              title="Facilities Requiring Attention"
              items={
                result.facilities_requiring_attention
              }
              Icon={Building2}
            />
          )}

          <Items
            title="Recommended Actions"
            items={result.recommendations}
            Icon={CheckCircle2}
          />

          <Items
            title="Priority Actions"
            items={result.priority_actions}
            Icon={Target}
          />
        </>
      )}

      <footer>
        <Sparkles size={13} />
        FlowSense backend calculations remain
        authoritative. Ollama interprets supplied
        evidence only.
      </footer>
    </main>
  );
}