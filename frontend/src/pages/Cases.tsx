import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { Case, Platform } from "../types";

export default function Cases() {
  const { hasRole } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", platform_id: "", priority: "MEDIUM", description: "" });

  function refresh() {
    api.get<Case[]>("/cases").then(setCases);
    api.get<Platform[]>("/platforms").then(setPlatforms);
  }

  useEffect(refresh, []);

  async function createCase() {
    setError(null);
    try {
      await api.post("/cases", form);
      setShowForm(false);
      setForm({ title: "", platform_id: "", priority: "MEDIUM", description: "" });
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? String(e.detail) : "Failed to create case");
    }
  }

  const platformName = (id: string) => platforms.find((p) => p.id === id)?.name ?? id;

  return (
    <Layout title="Cases">
      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-slate-400">{cases.length} case(s)</p>
        {hasRole("ADMIN", "ANALYST") && (
          <button
            onClick={() => setShowForm((s) => !s)}
            className="text-sm px-3 py-1.5 rounded-md bg-accent-DEFAULT hover:bg-accent-soft text-white"
          >
            {showForm ? "Cancel" : "+ New Case"}
          </button>
        )}
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg border border-surface-border bg-surface-panel p-4 space-y-3">
          <input
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            placeholder="Case title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <select
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            value={form.platform_id}
            onChange={(e) => setForm({ ...form, platform_id: e.target.value })}
          >
            <option value="">Select platform…</option>
            {platforms.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}
          >
            {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <textarea
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          {error && <div className="text-sm text-rose-400">{error}</div>}
          <button onClick={createCase} className="px-3 py-1.5 rounded-md bg-accent-DEFAULT text-white text-sm">
            Create Case
          </button>
        </div>
      )}

      <div className="rounded-lg border border-surface-border bg-surface-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Case #</th>
              <th className="text-left px-4 py-2">Title</th>
              <th className="text-left px-4 py-2">Platform</th>
              <th className="text-left px-4 py-2">Priority</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id} className="border-t border-surface-border hover:bg-white/5">
                <td className="px-4 py-2">
                  <Link to={`/cases/${c.id}`} className="text-accent-DEFAULT text-blue-400 hover:underline">
                    {c.case_number}
                  </Link>
                </td>
                <td className="px-4 py-2">{c.title}</td>
                <td className="px-4 py-2 text-slate-400">{platformName(c.platform_id)}</td>
                <td className="px-4 py-2">{c.priority}</td>
                <td className="px-4 py-2"><StatusBadge status={c.status} /></td>
                <td className="px-4 py-2 text-slate-400">{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
