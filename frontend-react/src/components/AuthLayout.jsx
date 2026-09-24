import {
  Activity,
  Droplets,
  Gauge,
  Leaf,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";

export default function AuthLayout({ children }) {
  return (
    <div className="auth-shell">
      <section className="auth-showcase">
        <div className="auth-glow auth-glow-one" />
        <div className="auth-glow auth-glow-two" />

        <div className="auth-brand">
          <div className="auth-brand-mark">
            <Activity size={21} strokeWidth={2.5} />
          </div>

          <div>
            <div className="auth-brand-name">
              FlowSense
            </div>
            <div className="auth-brand-subtitle">
              Intelligent Resource Monitoring
            </div>
          </div>
        </div>

        <div className="auth-showcase-content">
          <div className="auth-eyebrow">
            <Sparkles size={15} />
            SMART RESOURCE INTELLIGENCE
          </div>

          <h1>
            Monitor every
            <span> drop and watt.</span>
          </h1>

          <p>
            FlowSense brings energy and water monitoring,
            reconciliation, anomaly detection and
            intelligent insights together in one
            operational platform.
          </p>

          <div className="auth-feature-grid">
            <div className="auth-feature">
              <div className="auth-feature-icon">
                <Zap size={19} />
              </div>

              <div>
                <strong>Energy Intelligence</strong>
                <span>Track consumption in real time</span>
              </div>
            </div>

            <div className="auth-feature">
              <div className="auth-feature-icon water">
                <Droplets size={19} />
              </div>

              <div>
                <strong>Water Monitoring</strong>
                <span>Identify losses and unusual usage</span>
              </div>
            </div>

            <div className="auth-feature">
              <div className="auth-feature-icon analytics">
                <Gauge size={19} />
              </div>

              <div>
                <strong>Smart Analytics</strong>
                <span>Turn readings into actionable insights</span>
              </div>
            </div>

            <div className="auth-feature">
              <div className="auth-feature-icon secure">
                <ShieldCheck size={19} />
              </div>

              <div>
                <strong>Secure Platform</strong>
                <span>Protected enterprise access</span>
              </div>
            </div>
          </div>
        </div>

        <div className="auth-showcase-footer">
          <div>
            <Leaf size={15} />
            Built for smarter resource management
          </div>

          <span>FlowSense Platform</span>
        </div>
      </section>

      <section className="auth-form-section">
        <div className="auth-form-container">
          {children}
        </div>
      </section>
    </div>
  );
}