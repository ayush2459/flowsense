import { useState } from "react";
import { Eye, EyeOff, LockKeyhole, ArrowLeft, CheckCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function ResetPassword() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    newPassword: "",
    confirmPassword: "",
  });

  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    if (error) setError("");
    if (success) setSuccess("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    const email = form.email.trim().toLowerCase();

    if (!email) {
      setError("Please enter your email address.");
      return;
    }

    if (form.newPassword.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    if (form.newPassword !== form.confirmPassword) {
      setError("New password and confirm password do not match.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/auth/reset-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            email,
            new_password: form.newPassword,
            confirm_password: form.confirmPassword,
          }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            data?.message ||
            "Unable to reset your password. Please try again."
        );
      }

      setSuccess(
        "Your password has been updated successfully. Redirecting to login..."
      );

      setForm({
        email: "",
        newPassword: "",
        confirmPassword: "",
      });

      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 1800);
    } catch (err) {
      setError(
        err.message ||
          "Unable to reset your password. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <section className="auth-showcase">
        <div className="auth-showcase-overlay" />

        <div className="auth-showcase-content">
          <div className="auth-brand">
            <div className="auth-brand-mark">
              <LockKeyhole size={22} />
            </div>

            <div>
              <div className="auth-brand-name">FlowSense</div>
              <div className="auth-brand-subtitle">
                Smart Resource Intelligence
              </div>
            </div>
          </div>

          <div className="auth-showcase-copy">
            <span className="auth-eyebrow">SECURE ACCESS</span>

            <h1>
              Reset your
              <span> password.</span>
            </h1>

            <p>
              Update your FlowSense account password and continue
              managing your energy and water intelligence securely.
            </p>
          </div>
        </div>
      </section>

      <section className="auth-form-section">
        <div className="auth-card">
          <button
            type="button"
            className="auth-back-button"
            onClick={() => navigate("/login")}
          >
            <ArrowLeft size={17} />
            Back to Login
          </button>

          <div className="auth-card-header">
            <div className="auth-form-icon">
              <LockKeyhole size={21} />
            </div>

            <div>
              <h2>Reset Password</h2>
              <p>
                Enter your account email and choose a new password.
              </p>
            </div>
          </div>

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div
              className="auth-success"
              role="status"
            >
              <CheckCircle2 size={18} />
              <span>{success}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="auth-field">
              <label htmlFor="reset-email">Email address</label>

              <div className="auth-input-wrapper">
                <input
                  id="reset-email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  autoComplete="email"
                  disabled={loading || Boolean(success)}
                  required
                />
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="reset-new-password">
                New password
              </label>

              <div className="auth-input-wrapper">
                <input
                  id="reset-new-password"
                  name="newPassword"
                  type={showNewPassword ? "text" : "password"}
                  value={form.newPassword}
                  onChange={handleChange}
                  placeholder="Enter new password"
                  autoComplete="new-password"
                  disabled={loading || Boolean(success)}
                  minLength={8}
                  required
                />

                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() =>
                    setShowNewPassword((previous) => !previous)
                  }
                  aria-label={
                    showNewPassword
                      ? "Hide password"
                      : "Show password"
                  }
                  disabled={loading || Boolean(success)}
                >
                  {showNewPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="reset-confirm-password">
                Confirm new password
              </label>

              <div className="auth-input-wrapper">
                <input
                  id="reset-confirm-password"
                  name="confirmPassword"
                  type={
                    showConfirmPassword ? "text" : "password"
                  }
                  value={form.confirmPassword}
                  onChange={handleChange}
                  placeholder="Confirm new password"
                  autoComplete="new-password"
                  disabled={loading || Boolean(success)}
                  minLength={8}
                  required
                />

                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() =>
                    setShowConfirmPassword(
                      (previous) => !previous
                    )
                  }
                  aria-label={
                    showConfirmPassword
                      ? "Hide password"
                      : "Show password"
                  }
                  disabled={loading || Boolean(success)}
                >
                  {showConfirmPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="auth-submit"
              disabled={loading || Boolean(success)}
            >
              {loading ? "Updating Password..." : "Update Password"}
            </button>
          </form>

          <div className="auth-card-footer">
            Remember your password?{" "}
            <button
              type="button"
              className="auth-link-button"
              onClick={() => navigate("/login")}
            >
              Sign in
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}