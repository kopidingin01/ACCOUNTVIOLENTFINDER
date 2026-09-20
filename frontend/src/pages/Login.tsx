import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
    } catch {
      setError("Invalid username or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-xl font-semibold text-slate-100">REPORT VALIDATOR</div>
          <div className="text-sm text-slate-400 mt-1">Evidence Collection &amp; Platform Reporting System</div>
        </div>
        <form onSubmit={handleSubmit} className="bg-surface-panel border border-surface-border rounded-lg p-6 space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Username</label>
            <input
              className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-accent-DEFAULT"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Password</label>
            <input
              type="password"
              className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-accent-DEFAULT"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <div className="text-sm text-rose-400">{error}</div>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-accent-DEFAULT hover:bg-accent-soft transition-colors text-white text-sm font-medium py-2 disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="text-center text-[11px] text-slate-500 mt-6">
          Evidence-based reporting only — not a mass-reporting or takedown-bot tool.
        </p>
      </div>
    </div>
  );
}
