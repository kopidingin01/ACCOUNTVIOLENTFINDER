import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { Case, Evidence as EvidenceType } from "../types";

const EVIDENCE_TYPES = [
  "SCREENSHOT", "VIDEO", "IMAGE", "PUBLIC_POST", "PUBLIC_COMMENT",
  "PUBLIC_PROFILE", "PUBLIC_URL", "ARTICLE", "ARCHIVE", "DOCUMENT",
  "API_RESPONSE", "METADATA",
];

export default function EvidencePage() {
  const { hasRole } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [evidence, setEvidence] = useState<EvidenceType[]>([]);
  const [caseId, setCaseId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ type: "SCREENSHOT", source_url: "", description: "" });
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    api.get<Case[]>("/cases").then(setCases);
  }, []);

  function refresh() {
    api.get<EvidenceType[]>(caseId ? `/evidence?case_id=${caseId}` : "/evidence").then(setEvidence);
  }
  useEffect(refresh, [caseId]);

  async function upload() {
    setError(null);
    if (!caseId) { setError("Select a case first."); return; }
    const fd = new FormData();
    fd.append("case_id", caseId);
    fd.append("type", form.type);
    fd.append("source_url", form.source_url);
    fd.append("description", form.description);
    if (file) fd.append("file", file);
    try {
      await api.postForm("/evidence", fd);
      setForm({ type: "SCREENSHOT", source_url: "", description: "" });
      setFile(null);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? String(e.detail) : "Upload failed");
    }
  }

  async function verify(id: string) {
    await api.post(`/evidence/${id}/verify`, {});
    refresh();
  }

  return (
    <Layout title="Evidence">
      <div className="mb-4 flex gap-3 items-center">
        <select className="rounded-md bg-surface-panel border border-surface-border px-3 py-2 text-sm" value={caseId} onChange={(e) => setCaseId(e.target.value)}>
          <option value="">All cases</option>
          {cases.map((c) => <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>)}
        </select>
      </div>

      {hasRole("ADMIN", "ANALYST") && (
        <div className="mb-6 rounded-lg border border-surface-border bg-surface-panel p-4 space-y-3">
          <div className="text-sm font-medium text-slate-200">Add Evidence</div>
          <div className="grid grid-cols-2 gap-3">
            <select className="rounded-md bg-surface border border-surface-border px-3 py-2 text-sm" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              {EVIDENCE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input className="rounded-md bg-surface border border-surface-border px-3 py-2 text-sm" placeholder="Source URL (https://…)" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} />
          </div>
          <textarea className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm" placeholder="Description / context" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm text-slate-400" />
          <p className="text-[11px] text-slate-500">Allowed: images, video, PDF, text/JSON/HTML, up to 25MB. Files are stored under a randomized name; SHA-256 is computed automatically.</p>
          {error && <div className="text-sm text-rose-400">{error}</div>}
          <button onClick={upload} className="px-3 py-1.5 rounded-md bg-accent-DEFAULT text-white text-sm">Upload</button>
        </div>
      )}

      <div className="rounded-lg border border-surface-border bg-surface-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Evidence #</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">SHA-256</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Collected</th>
              <th className="text-left px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((e) => (
              <tr key={e.id} className="border-t border-surface-border">
                <td className="px-4 py-2">{e.evidence_number}</td>
                <td className="px-4 py-2 text-slate-400">{e.type}</td>
                <td className="px-4 py-2 font-mono text-[11px] text-slate-500">{e.sha256 ? e.sha256.slice(0, 20) + "…" : "—"}</td>
                <td className="px-4 py-2"><StatusBadge status={e.verification_status} /></td>
                <td className="px-4 py-2 text-slate-400">{new Date(e.collected_at).toLocaleDateString()}</td>
                <td className="px-4 py-2">
                  {hasRole("ADMIN", "ANALYST") && e.verification_status === "PENDING" && (
                    <button onClick={() => verify(e.id)} className="text-xs text-blue-400 hover:underline">Verify</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
