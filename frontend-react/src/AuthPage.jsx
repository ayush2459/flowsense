import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, LockKeyhole, Mail, UserRound, Waves } from "lucide-react";
import { api } from "./services/api";
import { useAuth } from "./AuthContext";
import "./Auth.css";

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { authenticate } = useAuth();
  const [mode, setMode] = useState("login");
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", confirm_password: "" });
  const [error, setError] = useState(new URLSearchParams(location.search).get("error") ? "Google sign-in could not be completed. Please try again." : "");
  const [loading, setLoading] = useState(false);
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event) => {
    event.preventDefault(); setError("");
    if (mode === "register" && form.password !== form.confirm_password) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      const result = mode === "login"
        ? await api.login({ email: form.email, password: form.password })
        : await api.register({ full_name: form.full_name, email: form.email, password: form.password });
      authenticate(result); navigate("/", { replace: true });
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return <div className="auth-page">
    <div className="auth-hero"><div className="auth-hero-overlay" /><div className="auth-hero-content">
      <div className="auth-brand"><span className="auth-brand-icon"><Waves /></span><strong>Flow<span>Sense</span></strong></div>
      <div className="auth-copy"><div className="auth-eyebrow">AI-POWERED FACILITY INTELLIGENCE</div>
        <h1>Monitor resources.<br />Understand performance.</h1>
        <p>Real-time energy and water monitoring, intelligent anomaly detection and evidence-backed operational insights.</p>
        <div className="auth-features"><span>Realtime telemetry</span><span>AI-powered insights</span><span>Automated reports</span></div>
      </div>
    </div></div>
    <div className="auth-panel"><div className="auth-panel-inner">
      <div className="auth-mobile-brand"><span className="auth-brand-icon"><Waves /></span><strong>Flow<span>Sense</span></strong></div>
      <div className="auth-heading"><span className="auth-kicker">{mode === "login" ? "WELCOME BACK" : "GET STARTED"}</span>
        <h2>{mode === "login" ? "Sign in to FlowSense" : "Create your FlowSense account"}</h2>
        <p>{mode === "login" ? "Access your facilities, live telemetry and reports." : "Create an account to start using FlowSense."}</p>
      </div>
      <a className="google-button" href={api.googleLoginUrl()}><span className="google-mark">G</span>Continue with Google</a>
      <div className="auth-divider"><span>OR</span></div>
      <form onSubmit={submit} className="auth-form">
        {mode === "register" && <label><span>Full name</span><div className="auth-input"><UserRound /><input value={form.full_name} onChange={(e) => update("full_name", e.target.value)} placeholder="Your full name" required /></div></label>}
        <label><span>Email address</span><div className="auth-input"><Mail /><input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} placeholder="you@example.com" required /></div></label>
        <label><span>Password</span><div className="auth-input"><LockKeyhole /><input type={showPassword ? "text" : "password"} value={form.password} onChange={(e) => update("password", e.target.value)} placeholder="At least 8 characters" required /><button type="button" className="password-toggle" onClick={() => setShowPassword((v) => !v)}>{showPassword ? <EyeOff /> : <Eye />}</button></div></label>
        {mode === "register" && <label><span>Confirm password</span><div className="auth-input"><LockKeyhole /><input type={showPassword ? "text" : "password"} value={form.confirm_password} onChange={(e) => update("confirm_password", e.target.value)} placeholder="Re-enter your password" required /></div></label>}
        {error && <div className="auth-error">{error}</div>}
        <button className="auth-submit" type="submit" disabled={loading}>{loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}</button>
      </form>
      <div className="auth-switch">{mode === "login" ? <>Don&apos;t have an account?<button type="button" onClick={() => { setError(""); setMode("register"); }}>Create one</button></> : <>Already have an account?<button type="button" onClick={() => { setError(""); setMode("login"); }}>Sign in</button></>}</div>
      <small className="auth-legal">By continuing, you agree to the FlowSense terms and privacy policy.</small>
    </div></div>
  </div>;
}

export function GoogleCallback() {
  const navigate = useNavigate(); const { authenticate } = useAuth();
  const [message, setMessage] = useState("Completing Google sign-in...");
  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) { setMessage("Google sign-in could not be completed."); return; }
    api.me(token).then((result) => { authenticate({ access_token: token, user: result.user }); navigate("/", { replace: true }); })
      .catch(() => setMessage("The Google sign-in session is invalid or expired."));
  }, [authenticate, navigate]);
  return <div className="auth-callback"><div><span className="auth-spinner" /><h2>Signing you in</h2><p>{message}</p></div></div>;
}