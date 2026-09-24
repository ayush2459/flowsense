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

import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../auth/AuthContext";

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
            <label htmlFor="email">Email address</label>

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
                onClick={() => navigate("/reset-password")}
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
                  setShowPassword((current) => !current)
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
            disabled={loading}
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

          <button
            type="button"
            className="google-button"
            onClick={() =>
              setError(
                "Google Sign-In will be connected next."
              )
            }
          >
            <span className="google-logo">G</span>
            Continue with Google
          </button>
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