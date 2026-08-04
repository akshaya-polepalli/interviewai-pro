import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AxiosError } from "axios";

import { useAuth } from "@/contexts/AuthContext";
import type { ApiErrorBody } from "@/types/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(searchParams.get("oauth_error"));
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Sign in to continue your interview prep. Demo: demo@interviewai.local / DemoPass1"
      footer={
        <>
          No account?{" "}
          <Link to="/signup" className="text-accent hover:underline">
            Create one
          </Link>
        </>
      }
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        <Field label="Password" type="password" value={password} onChange={setPassword} required />
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-sm text-ink-muted hover:text-accent">
            Forgot password?
          </Link>
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <OAuthButtons />
    </AuthCard>
  );
}

export function SignupPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [debugToken, setDebugToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const { registerAccount } = await import("@/services/auth");
      const res = await registerAccount({
        email,
        full_name: fullName,
        password,
      });
      setMessage(res.message);
      if (res.debug_token) {
        setDebugToken(res.debug_token);
      } else {
        navigate("/login");
      }
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle="Start with email verification, then unlock the full platform."
      footer={
        <>
          Already registered?{" "}
          <Link to="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        <Field label="Full name" value={fullName} onChange={setFullName} required />
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          required
          hint="Min 8 chars, 1 uppercase, 1 digit"
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        {message && <p className="text-sm text-accent">{message}</p>}
        {debugToken && (
          <p className="rounded-xl bg-black/30 p-3 font-mono text-xs text-ink-muted break-all">
            Dev verify token: {debugToken}
            <br />
            <Link className="text-accent" to={`/verify-email?token=${debugToken}`}>
              Verify now
            </Link>
          </p>
        )}
        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? "Creating…" : "Create account"}
        </button>
      </form>
      <OAuthButtons />
    </AuthCard>
  );
}

export function OAuthCallbackPage() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function finish() {
      const hash = window.location.hash.replace(/^#/, "");
      const params = new URLSearchParams(hash);
      const access = params.get("access_token");
      const refresh = params.get("refresh_token");
      if (!access || !refresh) {
        setError("Missing OAuth tokens. Try signing in again.");
        return;
      }
      try {
        const { storeTokens, fetchMe } = await import("@/services/auth");
        storeTokens(access, refresh);
        const me = await fetchMe();
        setUser(me);
        window.history.replaceState(null, "", "/oauth/callback");
        navigate("/dashboard", { replace: true });
      } catch (err) {
        setError(extractError(err));
      }
    }
    void finish();
  }, [navigate, setUser]);

  return (
    <AuthCard title="Completing sign-in" subtitle="Finishing OAuth handshake…">
      {error ? (
        <p className="text-sm text-danger">
          {error}{" "}
          <Link to="/login" className="underline">
            Back to login
          </Link>
        </p>
      ) : (
        <p className="text-sm text-ink-muted">Please wait…</p>
      )}
    </AuthCard>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [debugToken, setDebugToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { forgotPassword } = await import("@/services/auth");
      const res = await forgotPassword(email);
      setMessage(res.message);
      setDebugToken(res.debug_token ?? null);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title="Reset password" subtitle="We'll email a secure one-time link.">
      <form className="space-y-4" onSubmit={onSubmit}>
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        {error && <p className="text-sm text-danger">{error}</p>}
        {message && <p className="text-sm text-accent">{message}</p>}
        {debugToken && (
          <p className="rounded-xl bg-black/30 p-3 font-mono text-xs text-ink-muted break-all">
            Dev reset token ready.{" "}
            <Link className="text-accent" to={`/reset-password?token=${debugToken}`}>
              Continue
            </Link>
          </p>
        )}
        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? "Sending…" : "Send reset link"}
        </button>
      </form>
    </AuthCard>
  );
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const params = new URLSearchParams(window.location.search);
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { resetPassword } = await import("@/services/auth");
      await resetPassword(token, password);
      navigate("/login");
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title="Choose a new password" subtitle="This invalidates existing sessions.">
      <form className="space-y-4" onSubmit={onSubmit}>
        <Field label="Reset token" value={token} onChange={setToken} required />
        <Field
          label="New password"
          type="password"
          value={password}
          onChange={setPassword}
          required
          hint="Min 8 chars, 1 uppercase, 1 digit"
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? "Updating…" : "Update password"}
        </button>
      </form>
    </AuthCard>
  );
}

export function VerifyEmailPage() {
  const params = new URLSearchParams(window.location.search);
  const [token, setToken] = useState(params.get("token") ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { verifyEmail } = await import("@/services/auth");
      const user = await verifyEmail(token);
      setMessage(`Email verified for ${user.email}. You can sign in now.`);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title="Verify email" subtitle="Paste the token from your inbox (or debug response).">
      <form className="space-y-4" onSubmit={onSubmit}>
        <Field label="Verification token" value={token} onChange={setToken} required />
        {error && <p className="text-sm text-danger">{error}</p>}
        {message && (
          <p className="text-sm text-accent">
            {message}{" "}
            <Link to="/login" className="underline">
              Sign in
            </Link>
          </p>
        )}
        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? "Verifying…" : "Verify"}
        </button>
      </form>
    </AuthCard>
  );
}

function OAuthButtons() {
  return (
    <div className="mt-6 space-y-3">
      <div className="flex items-center gap-3 text-xs uppercase tracking-[0.18em] text-ink-subtle">
        <span className="h-px flex-1 bg-white/10" />
        or continue with
        <span className="h-px flex-1 bg-white/10" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <a className="btn-ghost justify-center text-sm" href={`${API_BASE}/auth/oauth/google/authorize`}>
          Google
        </a>
        <a className="btn-ghost justify-center text-sm" href={`${API_BASE}/auth/oauth/github/authorize`}>
          GitHub
        </a>
      </div>
      <p className="text-center text-xs text-ink-subtle">
        Configure provider secrets in `.env` or you will see a 501 until they are set.
      </p>
    </div>
  );
}

function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-md">
      <div className="glass-panel p-8">
        <h1 className="font-display text-2xl font-semibold text-ink">{title}</h1>
        <p className="mt-2 text-sm text-ink-muted">{subtitle}</p>
        <div className="mt-6">{children}</div>
        {footer && <p className="mt-6 text-center text-sm text-ink-muted">{footer}</p>}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
  hint,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  hint?: string;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm text-ink-muted">{label}</span>
      <input
        className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2.5 text-ink outline-none ring-accent focus:ring-2"
        type={type}
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint && <span className="text-xs text-ink-subtle">{hint}</span>}
    </label>
  );
}

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as ApiErrorBody | undefined;
    return data?.error?.message ?? err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
