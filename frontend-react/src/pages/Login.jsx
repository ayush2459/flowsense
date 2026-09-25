import { useState } from "react";
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { GoogleLogin } from "@react-oauth/google";

import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../auth/AuthContext";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const { login } = useAuth();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [showPassword, setShowPassword] =
    useState(false);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] =
    useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));

    if (error) {
      setError("");
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!form.email || !form.password) {
      setError("Please enter your email and password.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await login(form);

      const destination =
        location.state?.from?.pathname || "/";

      navigate(destination, { replace: true });
    } catch (err) {
      setError(
        err.message ||
          "Unable to sign in. Please check your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    if (!credentialResponse?.credential) {
      setError(
        "Google authentication did not return a valid credential."
      );
      return;
    }

    setGoogleLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/auth/google`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            credential: credentialResponse.credential,
          }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            data?.message ||
            "Unable to sign in with Google."
        );
      }

      if (!data?.access_token || !data?.user) {
        throw new Error(
          "Google authentication response is incomplete."
        );
      }

      localStorage.setItem(
        "flowsense_access_token",
        data.access_token
      );

      localStorage.setItem(
        "flowsense_user",
        JSON.stringify(data.user)
      );

      window.location.replace(
        location.state?.from?.pathname || "/"
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to sign in with Google. Please try again."
      );
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleGoogleError = () => {
    setGoogleLoading(false);
    setError(
      "Google Sign-In was cancelled or could not be completed."
    );
  };

  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="auth-card-header">
          <div className="auth-mobile-brand">
            <div className="auth-brand-mark">
              <ShieldCheck size={19} />
            </div>

            <span>FlowSense</span>
          </div>

          <div className="auth-card-kicker">
            WELCOME BACK
          </div>

          <h2>Sign in to FlowSense</h2>

          <p>
            Access your monitoring dashboard and
            operational insights.
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >
          {error && (
            <div className="auth-error">
              <span className="auth-error-dot" />
              {error}
            </div>
          )}

          <div className="auth-field">
            <label htmlFor="email">
              Email address
            </label>

            <div className="auth-input-wrapper">
              <Mail size={18} />

              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={form.email}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="auth-field">
            <div className="auth-label-row">
              <label htmlFor="password">
                Password
              </label>

              <button
                type="button"
                className="auth-text-button"
                onClick={() =>
                  navigate("/reset-password")
                }
              >
                Forgot password?
              </button>
            </div>

            <div className="auth-input-wrapper">
              <LockKeyhole size={18} />

              <input
                id="password"
                name="password"
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                autoComplete="current-password"
                placeholder="Enter your password"
                value={form.password}
                onChange={handleChange}
              />

              <button
                type="button"
                className="auth-password-toggle"
                onClick={() =>
                  setShowPassword(
                    (current) => !current
                  )
                }
                aria-label={
                  showPassword
                    ? "Hide password"
                    : "Show password"
                }
              >
                {showPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}
              </button>
            </div>
          </div>

          <button
            className="auth-submit"
            type="submit"
            disabled={loading || googleLoading}
          >
            {loading ? (
              <>
                <span className="auth-button-spinner" />
                Signing in...
              </>
            ) : (
              <>
                Sign in
                <ArrowRight size={18} />
              </>
            )}
          </button>

          <div className="auth-divider">
            <span />
            <p>or continue with</p>
            <span />
          </div>

          <div
            className="google-login-wrapper"
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "center",
              minHeight: "44px",
              position: "relative",
            }}
          >
            {googleLoading && (
              <div
                className="google-loading-overlay"
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "rgba(255, 255, 255, 0.8)",
                  borderRadius: "8px",
                  zIndex: 2,
                }}
              >
                <span className="auth-button-spinner" />
                <span style={{ marginLeft: "8px" }}>
                  Signing in with Google...
                </span>
              </div>
            )}

            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              useOneTap={false}
              theme="outline"
              size="large"
              text="continue_with"
              shape="rectangular"
              width="100%"
            />
          </div>
        </form>

        <div className="auth-card-footer">
          <span>Don't have an account?</span>

          <Link to="/register">
            Create an account
            <ArrowRight size={15} />
          </Link>
        </div>
      </div>

      <div className="auth-security-note">
        <ShieldCheck size={15} />
        <span>
          Your connection is protected with secure
          authentication.
        </span>
      </div>
    </AuthLayout>
  );
}