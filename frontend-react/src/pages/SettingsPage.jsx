import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bell,
  Building2,
  CheckCircle2,
  Database,
  Globe,
  KeyRound,
  Link2,
  Lock,
  Mail,
  Moon,
  Monitor,
  Save,
  Server,
  Settings,
  Shield,
  ShieldCheck,
  Sun,
  UserRound,
  Users,
  Webhook,
  Wifi,
  XCircle,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { settingsApi } from "../services/settingsApi";
import "./SettingsPage.css";


const SECTIONS = [
  ["general", "General", Settings],
  ["users", "Users & Access", Users],
  ["notifications", "Notifications", Bell],
  ["integrations", "Integrations", Link2],
  ["system", "System", Server],
  ["security", "Security", Shield],
];


const DEFAULTS = {
  organization: {
    name: "FlowSense",
    code: "FLOWSENSE",
    contact_email: "",
    contact_phone: "",
  },
  preferences: {
    timezone: "Asia/Kolkata",
    locale: "en-IN",
    currency: "INR",
    date_format: "DD/MM/YYYY",
    theme: "dark",
  },
  monitoring: {
    realtime_telemetry: true,
    websocket_streaming: true,
    auto_refresh: true,
    refresh_interval_seconds: 15,
  },
  notifications: {
    email_enabled: true,
    anomaly_alerts: true,
    critical_alerts: true,
    report_notifications: true,
    maintenance_notifications: true,
    weekly_summary: false,
  },
  integrations: {
    mqtt_enabled: true,
    mqtt_status: "Configured",
    google_enabled: true,
    webhook_enabled: false,
    webhook_url: "",
    razorpay_enabled: false,
  },
  system: {
    heartbeat_timeout_seconds: 120,
    telemetry_retention_days: 365,
    log_retention_days: 90,
    maintenance_mode: false,
  },
  security: {
    session_timeout_minutes: 60,
    enforce_mfa: false,
    audit_logging: true,
    login_notifications: true,
  },
};


function mergeSettings(server) {
  return {
    ...DEFAULTS,
    ...server,
    organization: {
      ...DEFAULTS.organization,
      ...(server?.organization || {}),
    },
    preferences: {
      ...DEFAULTS.preferences,
      ...(server?.preferences || {}),
    },
    monitoring: {
      ...DEFAULTS.monitoring,
      ...(server?.monitoring || {}),
    },
    notifications: {
      ...DEFAULTS.notifications,
      ...(server?.notifications || {}),
    },
    integrations: {
      ...DEFAULTS.integrations,
      ...(server?.integrations || {}),
    },
    system: {
      ...DEFAULTS.system,
      ...(server?.system || {}),
    },
    security: {
      ...DEFAULTS.security,
      ...(server?.security || {}),
    },
  };
}


function Toggle({ checked, onChange, label, sub }) {
  return (
    <label className="settings-toggle-row">
      <span>
        <strong>{label}</strong>
        {sub && <small>{sub}</small>}
      </span>
      <input
        type="checkbox"
        checked={Boolean(checked)}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="settings-switch" />
    </label>
  );
}


function Field({ label, value, onChange, type = "text", placeholder }) {
  return (
    <label className="settings-field">
      <span>{label}</span>
      <input
        type={type}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}


function SelectField({ label, value, onChange, children }) {
  return (
    <label className="settings-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {children}
      </select>
    </label>
  );
}


function Status({ ok = true, children }) {
  return (
    <span className={`settings-status ${ok ? "ok" : "bad"}`}>
      {ok ? <CheckCircle2 /> : <XCircle />}
      {children}
    </span>
  );
}


export default function SettingsPage() {
  const { user } = useAuth();

  const [section, setSection] = useState("general");
  const [settings, setSettings] = useState(DEFAULTS);
  const [users, setUsers] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [password, setPassword] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [profile, setProfile] = useState({
    name: user?.name || "",
    phone: "",
    job_title: "",
    department: "",
    profile_image: user?.profile_image || "",
  });

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    setError("");

    try {
      const data = await settingsApi.get();
      setSettings(mergeSettings(data));
      setProfile({
        name: data?.profile?.name || user?.name || "",
        phone: data?.profile?.phone || "",
        job_title: data?.profile?.job_title || "",
        department: data?.profile?.department || "",
        profile_image: data?.profile?.profile_image || "",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadUsers() {
    try {
      const data = await settingsApi.users();
      setUsers(data?.users || []);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadSystemStatus() {
    try {
      const data = await settingsApi.systemStatus();
      setSystemStatus(data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (section === "users") loadUsers();
    if (section === "system") loadSystemStatus();
  }, [section]);

  const update = (group, key, value) => {
    setSettings((current) => ({
      ...current,
      [group]: {
        ...current[group],
        [key]: value,
      },
    }));
  };

  async function saveSettings() {
    setSaving(true);
    setMessage("");
    setError("");

    try {
      await settingsApi.save({
        organization: settings.organization,
        preferences: settings.preferences,
        monitoring: settings.monitoring,
        notifications: settings.notifications,
        integrations: settings.integrations,
        system: settings.system,
        security: settings.security,
      });

      setMessage("Settings saved successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function saveProfile() {
    setSaving(true);
    setMessage("");
    setError("");

    try {
      const data = await settingsApi.profile(profile);
      setMessage("Profile updated successfully.");
      if (data?.user) {
        localStorage.setItem("flowsense_user", JSON.stringify({
          ...user,
          ...data.user,
        }));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function changePassword() {
    setSaving(true);
    setMessage("");
    setError("");

    try {
      await settingsApi.password(password);
      setPassword({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
      setMessage("Password changed successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function updateManagedUser(userId, payload) {
    try {
      await settingsApi.updateUser(userId, payload);
      await loadUsers();
      setMessage("User updated successfully.");
    } catch (err) {
      setError(err.message);
    }
  }

  const initials = useMemo(
    () =>
      (profile.name || "FlowSense")
        .split(" ")
        .map((x) => x[0])
        .join("")
        .slice(0, 2)
        .toUpperCase(),
    [profile.name]
  );

  return (
    <div className="flowsense-settings-page">
      <div className="settings-page-header">
        <div>
          <div className="settings-overline">FLOWSENSE / CONFIGURATION</div>
          <h1>Settings</h1>
          <p>Manage platform configuration, access, notifications and security.</p>
        </div>

        <button className="settings-save-button" onClick={saveSettings} disabled={saving || loading}>
          <Save />
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {(message || error) && (
        <div className={`settings-message ${error ? "error" : "success"}`}>
          {error ? <XCircle /> : <CheckCircle2 />}
          <span>{error || message}</span>
        </div>
      )}

      <div className="settings-layout">
        <aside className="settings-navigation">
          {SECTIONS.map(([key, label, Icon]) => (
            <button
              key={key}
              className={`settings-nav-item ${section === key ? "active" : ""}`}
              onClick={() => {
                setSection(key);
                setMessage("");
                setError("");
              }}
            >
              <Icon />
              <span>{label}</span>
            </button>
          ))}
        </aside>

        <main className="settings-content">
          {loading ? (
            <section className="settings-card">
              <div className="settings-loading">Loading settings from FlowSense backend...</div>
            </section>
          ) : (
            <>
              {section === "general" && (
                <>
                  <section className="settings-card">
                    <div className="settings-card-head">
                      <div>
                        <h2><Building2 /> Organization Information</h2>
                        <p>Stored centrally in PostgreSQL and shared across the platform.</p>
                      </div>
                    </div>

                    <div className="settings-grid two">
                      <Field label="Organization Name" value={settings.organization.name}
                        onChange={(v) => update("organization", "name", v)} />
                      <Field label="Organization Code" value={settings.organization.code}
                        onChange={(v) => update("organization", "code", v)} />
                      <Field label="Contact Email" type="email" value={settings.organization.contact_email}
                        onChange={(v) => update("organization", "contact_email", v)} />
                      <Field label="Contact Phone" value={settings.organization.contact_phone}
                        onChange={(v) => update("organization", "contact_phone", v)} />
                    </div>
                  </section>

                  <section className="settings-card">
                    <div className="settings-card-head">
                      <div>
                        <h2><SlidersIcon /> Preferences</h2>
                        <p>Defaults used by the FlowSense control center.</p>
                      </div>
                    </div>

                    <div className="settings-grid two">
                      <SelectField label="Timezone" value={settings.preferences.timezone}
                        onChange={(v) => update("preferences", "timezone", v)}>
                        <option value="Asia/Kolkata">Asia/Kolkata</option>
                        <option value="UTC">UTC</option>
                        <option value="Asia/Singapore">Asia/Singapore</option>
                      </SelectField>
                      <SelectField label="Locale" value={settings.preferences.locale}
                        onChange={(v) => update("preferences", "locale", v)}>
                        <option value="en-IN">English (India)</option>
                        <option value="en-US">English (US)</option>
                      </SelectField>
                      <SelectField label="Currency" value={settings.preferences.currency}
                        onChange={(v) => update("preferences", "currency", v)}>
                        <option value="INR">INR — Indian Rupee</option>
                        <option value="USD">USD — US Dollar</option>
                        <option value="EUR">EUR — Euro</option>
                      </SelectField>
                      <SelectField label="Date Format" value={settings.preferences.date_format}
                        onChange={(v) => update("preferences", "date_format", v)}>
                        <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                        <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                        <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                      </SelectField>
                    </div>

                    <div className="theme-selector">
                      {[
                        ["dark", <Moon />, "Dark"],
                        ["light", <Sun />, "Light"],
                        ["system", <Monitor />, "System"],
                      ].map(([value, icon, label]) => (
                        <button
                          key={value}
                          className={settings.preferences.theme === value ? "selected" : ""}
                          onClick={() => update("preferences", "theme", value)}
                        >
                          {icon}<span>{label}</span>
                        </button>
                      ))}
                    </div>
                  </section>

                  <section className="settings-card">
                    <div className="settings-card-head">
                      <div>
                        <h2><UserRound /> My Profile</h2>
                        <p>Your authenticated FlowSense account.</p>
                      </div>
                      <div className="settings-avatar">{initials}</div>
                    </div>

                    <div className="settings-grid two">
                      <Field label="Name" value={profile.name}
                        onChange={(v) => setProfile({ ...profile, name: v })} />
                      <Field label="Email" value={user?.email || ""} />
                      <Field label="Phone" value={profile.phone}
                        onChange={(v) => setProfile({ ...profile, phone: v })} />
                      <Field label="Job Title" value={profile.job_title}
                        onChange={(v) => setProfile({ ...profile, job_title: v })} />
                      <Field label="Department" value={profile.department}
                        onChange={(v) => setProfile({ ...profile, department: v })} />
                    </div>

                    <button className="settings-secondary-button" onClick={saveProfile} disabled={saving}>
                      <Save /> Save Profile
                    </button>
                  </section>
                </>
              )}

              {section === "users" && (
                <section className="settings-card">
                  <div className="settings-card-head">
                    <div>
                      <h2><Users /> Users & Access</h2>
                      <p>Manage authenticated FlowSense users and their access level.</p>
                    </div>
                  </div>

                  <div className="settings-user-list">
                    {users.map((managedUser) => (
                      <div className="settings-user-row" key={managedUser.user_id}>
                        <div className="settings-user-avatar">
                          {(managedUser.name || "U").slice(0, 1).toUpperCase()}
                        </div>
                        <div className="settings-user-main">
                          <strong>{managedUser.name}</strong>
                          <span>{managedUser.email}</span>
                        </div>
                        <select
                          value={managedUser.role || "admin"}
                          onChange={(e) =>
                            updateManagedUser(managedUser.user_id, { role: e.target.value })
                          }
                        >
                          <option value="admin">Admin</option>
                          <option value="manager">Manager</option>
                          <option value="technician">Technician</option>
                          <option value="viewer">Viewer</option>
                        </select>
                        <button
                          className={`settings-user-status ${managedUser.is_active ? "active" : "inactive"}`}
                          onClick={() =>
                            updateManagedUser(managedUser.user_id, {
                              is_active: !managedUser.is_active,
                            })
                          }
                        >
                          {managedUser.is_active ? "Active" : "Inactive"}
                        </button>
                      </div>
                    ))}
                    {!users.length && <div className="settings-empty">No users returned by the backend.</div>}
                  </div>
                </section>
              )}

              {section === "notifications" && (
                <section className="settings-card">
                  <div className="settings-card-head">
                    <div>
                      <h2><Bell /> Notifications</h2>
                      <p>Control operational alerts and reporting notifications.</p>
                    </div>
                  </div>

                  <Toggle label="Email Notifications" checked={settings.notifications.email_enabled}
                    onChange={(v) => update("notifications", "email_enabled", v)} />
                  <Toggle label="Anomaly Alerts" checked={settings.notifications.anomaly_alerts}
                    onChange={(v) => update("notifications", "anomaly_alerts", v)} />
                  <Toggle label="Critical Alerts" checked={settings.notifications.critical_alerts}
                    onChange={(v) => update("notifications", "critical_alerts", v)} />
                  <Toggle label="Report Notifications" checked={settings.notifications.report_notifications}
                    onChange={(v) => update("notifications", "report_notifications", v)} />
                  <Toggle label="Maintenance Notifications" checked={settings.notifications.maintenance_notifications}
                    onChange={(v) => update("notifications", "maintenance_notifications", v)} />
                  <Toggle label="Weekly Summary" checked={settings.notifications.weekly_summary}
                    onChange={(v) => update("notifications", "weekly_summary", v)} />
                </section>
              )}

              {section === "integrations" && (
                <section className="settings-card">
                  <div className="settings-card-head">
                    <div>
                      <h2><Link2 /> Integrations</h2>
                      <p>Manage connections used by the FlowSense platform.</p>
                    </div>
                  </div>

                  <div className="settings-integration-row">
                    <div><Wifi /><span><strong>MQTT Telemetry</strong><small>IoT device communication</small></span></div>
                    <Status ok={settings.integrations.mqtt_enabled}>{settings.integrations.mqtt_status}</Status>
                    <Toggle checked={settings.integrations.mqtt_enabled}
                      onChange={(v) => update("integrations", "mqtt_enabled", v)} />
                  </div>

                  <div className="settings-integration-row">
                    <div><Globe /><span><strong>Google Authentication</strong><small>Google OAuth account login</small></span></div>
                    <Status ok={settings.integrations.google_enabled}>Configured</Status>
                    <Toggle checked={settings.integrations.google_enabled}
                      onChange={(v) => update("integrations", "google_enabled", v)} />
                  </div>

                  <div className="settings-integration-row">
                    <div><Webhook /><span><strong>Webhooks</strong><small>External event delivery</small></span></div>
                    <Status ok={settings.integrations.webhook_enabled}>
                      {settings.integrations.webhook_enabled ? "Enabled" : "Disabled"}
                    </Status>
                    <Toggle checked={settings.integrations.webhook_enabled}
                      onChange={(v) => update("integrations", "webhook_enabled", v)} />
                  </div>

                  <Field label="Webhook URL" value={settings.integrations.webhook_url}
                    onChange={(v) => update("integrations", "webhook_url", v)}
                    placeholder="https://example.com/flowsense/webhook" />

                  <div className="settings-integration-row">
                    <div><Link2 /><span><strong>Razorpay</strong><small>Payment integration</small></span></div>
                    <Status ok={settings.integrations.razorpay_enabled}>
                      {settings.integrations.razorpay_enabled ? "Enabled" : "Disabled"}
                    </Status>
                    <Toggle checked={settings.integrations.razorpay_enabled}
                      onChange={(v) => update("integrations", "razorpay_enabled", v)} />
                  </div>
                </section>
              )}

              {section === "system" && (
                <>
                  <section className="settings-card">
                    <div className="settings-card-head">
                      <div>
                        <h2><Activity /> Monitoring</h2>
                        <p>Runtime behavior for realtime telemetry and dashboard refresh.</p>
                      </div>
                    </div>

                    <Toggle label="Realtime Telemetry" checked={settings.monitoring.realtime_telemetry}
                      onChange={(v) => update("monitoring", "realtime_telemetry", v)} />
                    <Toggle label="WebSocket Streaming" checked={settings.monitoring.websocket_streaming}
                      onChange={(v) => update("monitoring", "websocket_streaming", v)} />
                    <Toggle label="Automatic Refresh" checked={settings.monitoring.auto_refresh}
                      onChange={(v) => update("monitoring", "auto_refresh", v)} />

                    <div className="settings-grid two">
                      <Field label="Refresh Interval (seconds)" type="number"
                        value={settings.monitoring.refresh_interval_seconds}
                        onChange={(v) => update("monitoring", "refresh_interval_seconds", Number(v) || 1)} />
                      <Field label="Heartbeat Timeout (seconds)" type="number"
                        value={settings.system.heartbeat_timeout_seconds}
                        onChange={(v) => update("system", "heartbeat_timeout_seconds", Number(v) || 1)} />
                      <Field label="Telemetry Retention (days)" type="number"
                        value={settings.system.telemetry_retention_days}
                        onChange={(v) => update("system", "telemetry_retention_days", Number(v) || 1)} />
                      <Field label="Log Retention (days)" type="number"
                        value={settings.system.log_retention_days}
                        onChange={(v) => update("system", "log_retention_days", Number(v) || 1)} />
                    </div>
                  </section>

                  <section className="settings-card">
                    <div className="settings-card-head">
                      <div>
                        <h2><Server /> Live System Status</h2>
                        <p>Read-only health information from the backend.</p>
                      </div>
                    </div>

                    <div className="settings-status-grid">
                      <Status ok={systemStatus?.api === "online"}>API {systemStatus?.api || "Checking"}</Status>
                      <Status ok={systemStatus?.database === "online"}>Database {systemStatus?.database || "Checking"}</Status>
                      <div className="settings-stat"><Database /> <span>Facilities <strong>{systemStatus?.facility_count ?? "—"}</strong></span></div>
                      <div className="settings-stat"><Activity /> <span>Devices <strong>{systemStatus?.device_count ?? "—"}</strong></span></div>
                    </div>
                  </section>
                </>
              )}

              {section === "security" && (
                <>
                  <section className="settings-card">
                    <div className="settings-card-head">
                      <div>
                        <h2><ShieldCheck /> Security Controls</h2>
                        <p>Authentication and account security policies.</p>
                      </div>
                    </div>

                    <Toggle label="Enforce MFA" checked={settings.security.enforce_mfa}
                      onChange={(v) => update("security", "enforce_mfa", v)} />
                    <Toggle label="Audit Logging" checked={settings.security.audit_logging}
                      onChange={(v) => update("security", "audit_logging", v)} />
                    <Toggle label="Login Notifications" checked={settings.security.login_notifications}
                      onChange={(v) => update("security", "login_notifications", v)} />

                    <Field label="Session Timeout (minutes)" type="number"
                      value={settings.security.session_timeout_minutes}
                      onChange={(v) => update("security", "session_timeout_minutes", Number(v) || 1)} />
                  </section>

                  <section className="settings-card">
                    <div className="settings-card-head">
                      <div>
                        <h2><KeyRound /> Change Password</h2>
                        <p>Change the password for the current local account.</p>
                      </div>
                    </div>

                    <div className="settings-grid two">
                      <Field label="Current Password" type="password"
                        value={password.current_password}
                        onChange={(v) => setPassword({ ...password, current_password: v })} />
                      <Field label="New Password" type="password"
                        value={password.new_password}
                        onChange={(v) => setPassword({ ...password, new_password: v })} />
                      <Field label="Confirm Password" type="password"
                        value={password.confirm_password}
                        onChange={(v) => setPassword({ ...password, confirm_password: v })} />
                    </div>

                    <button className="settings-secondary-button" onClick={changePassword} disabled={saving}>
                      <Lock /> Change Password
                    </button>
                  </section>
                </>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}


function SlidersIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 6h16M4 12h16M4 18h16" />
      <circle cx="9" cy="6" r="2" fill="currentColor" />
      <circle cx="15" cy="12" r="2" fill="currentColor" />
      <circle cx="10" cy="18" r="2" fill="currentColor" />
    </svg>
  );
}
