import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import Layout from "../components/Layout";
import { useAuth } from "../hooks/useAuth";
import type { Platform } from "../types";

export default function Platforms() {
  const { hasRole } = useAuth();
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", domain: "", reporting_url: "" });
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.get<Platform[]>("/platforms").then(setPlatforms);
  }
  useEffect(refresh, []);

  async function create() {
    setError(null);
    try {
      await api.post("/platforms", form);
      setForm({ name: "", domain: "", reporting_url: "" });
      setShowForm(false);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? String(e.detail) : "Failed to create platform");
    }
  }

  return (
    <Layout title="Platforms">
      {hasRole("ADMIN") && (
        <div className="mb-4">
          <button onClick={() => setShowForm((s) => !s)} className="text-sm px-3 py-1.5 rounded-md bg-accent-DEFAULT text-white">
            {showForm ? "Cancel" : "+ New Platform"}
          </button>
          {showForm && (
            <div className="mt-3 rounded-lg border border-surface-border bg-surface-panel p-4 space-y-3 max-w-md">
              <input className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm" placeholder="Platform name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <input className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm" placeholder="Domain (e.g. example-social.com)" value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} />
              <input className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm" placeholder="Official reporting URL" value={form.reporting_url} onChange={(e) => setForm({ ...form, reporting_url: e.target.value })} />
              {error && <div className="text-sm text-rose-400">{error}</div>}
              <button onClick={create} className="px-3 py-1.5 rounded-md bg-accent-DEFAULT text-white text-sm">Create</button>
            </div>
          )}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {platforms.map((p) => (
          <div key={p.id} className="rounded-lg border border-surface-border bg-surface-panel p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">{p.name}</h3>
              <span className="text-[11px] text-slate-500">{p.has_official_api ? "Official API" : "Manual reporting"}</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">{p.domain}</div>
            {p.reporting_url && (
              <a href={p.reporting_url} target="_blank" rel="noreferrer" className="text-xs text-blue-400 hover:underline block mt-2">
                Official report page →
              </a>
            )}
          </div>
        ))}
      </div>
    </Layout>
  );
}
