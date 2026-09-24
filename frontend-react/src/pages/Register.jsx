import { useState } from "react";
import {
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  UserRound,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../auth/AuthContext";

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const [showPassword, setShowPassword] =
    useState(false);

  const [showConfirmPassword, setShowConfirmPassword] =
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

  const validate = () => {
    if (!form.name.trim()) {
      return "Please enter your name.";
    }

    if (!form.email.trim()) {
      return "Please enter your email address.";
    }

    if (form.password.length < 8) {
      return "Password must contain at least 8 characters.";
    }

    if (form.password !== form.confirmPassword) {
      return "Passwords do not match.";
    }

    return "";
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const validationError = validate();

    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError("");

    try {
      await register({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      });

      navigate("/dashboard", {
        replace: true,
      });
    } catch (err) {
      setError(
        err.message ||
          "Unable to create your account."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="auth-card register-card">
        <div className="auth-card-header">
          <div className="auth-mobile-brand">
            <div className="auth-brand-mark">
              <Check size={19} />
            </div>

            <span>FlowSense</span>
          </div>

          <div className="auth-card-kicker">
            GET STARTED
          </div>

          <h2>Create your account</h2>

          <p>
            Set up your FlowSense workspace and start
            monitoring resources intelligently.
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
            <label htmlFor="name">Full name</label>

            <div className="auth-input-wrapper">
              <UserRound size={18} />

              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                placeholder="Ayush Gupta"
                value={form.name}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="auth-field">
            <label htmlFor="register-email">
              Email address
            </label>

            <div className="auth-input-wrapper">
              <Mail size={18} />

              <input
                id="register-email"
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
            <label htmlFor="register-password">
              Password
            </label>

            <div className="auth-input-wrapper">
              <LockKeyhole size={18} />

              <input
                id="register-password"
                name="password"
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                autoComplete="new-password"
                placeholder="Minimum 8 characters"
                value={form.password}
                onChange={handleChange}
              />

              <button
                type="button"
                className="auth-password-toggle"
                onClick={() =>
                  setShowPassword((current) => !current)
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

          <div className="auth-field">
            <label htmlFor="confirm-password">
              Confirm password
            </label>

            <div className="auth-input-wrapper">
              <LockKeyhole size={18} />

              <input
                id="confirm-password"
                name="confirmPassword"
                type={
                  showConfirmPassword
                    ? "text"
                    : "password"
                }
                autoComplete="new-password"
                placeholder="Re-enter your password"
                value={form.confirmPassword}
                onChange={handleChange}
              />

              <button
                type="button"
                className="auth-password-toggle"
                onClick={() =>
                  setShowConfirmPassword(
                    (current) => !current
                  )
                }
              >
                {showConfirmPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}
              </button>
            </div>
          </div>

          <div className="auth-password-hint">
            <span
              className={
                form.password.length >= 8
                  ? "valid"
                  : ""
              }
            >
              <Check size={13} />
              At least 8 characters
            </span>
          </div>

          <button
            className="auth-submit"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="auth-button-spinner" />
                Creating account...
              </>
            ) : (
              <>
                Create account
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
          <span>Already have an account?</span>

          <Link to="/login">
            Sign in
            <ArrowRight size={15} />
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
}