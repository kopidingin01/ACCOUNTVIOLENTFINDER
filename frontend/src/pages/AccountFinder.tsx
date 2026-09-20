import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import Layout from "../components/Layout";
import SafeLink from "../components/SafeLink";
import StatusBadge from "../components/StatusBadge";
import type { AccountFinderResult } from "../types";

export default function AccountFinder() {
  const [url, setUrl] = useState("");
  const [createCase, setCreateCase] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AccountFinderResult | null>(null);

  async function run() {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const res = await api.post<AccountFinderResult>("/osint/account-finder", { account_url: url, create_case: createCase });
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.detail) : "Failed to analyze account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout title="Account Violation Finder">
      <div className="max-w-2xl mb-6">
        <p className="text-sm text-slate-400 mb-4">
          Enter a public social media account URL. The system collects publicly accessible content only, runs
          policy-keyword triage, and reports findings that a human reviewer must verify before any report is filed —
          it never fabricates evidence and never bypasses login walls, CAPTCHAs, or rate limits.
        </p>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-md bg-surface-panel border border-surface-border px-3 py-2 text-sm"
            placeholder="https://example-platform.com/u/username"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button onClick={run} disabled={loading || !url} className="px-4 py-2 rounded-md bg-accent-DEFAULT text-white text-sm disabled:opacity-50">
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </div>
        <label className="flex items-center gap-2 mt-2 text-xs text-slate-400">
          <input type="checkbox" checked={createCase} onChange={(e) => setCreateCase(e.target.checked)} />
          Create a case and evidence dossier from this analysis
        </label>
      </div>

      {error && <div className="mb-4 text-sm text-rose-400 border border-rose-500/30 bg-rose-500/10 rounded-md px-3 py-2">{error}</div>}

      {result && (
        <div className="space-y-4">
          <div className="rounded-lg border border-surface-border bg-surface-panel p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-slate-100">{result.platform}</div>
                <SafeLink href={result.profile_url} className="text-xs text-blue-400 hover:underline">{result.profile_url}</SafeLink>
              </div>
              <StatusBadge status={result.collection_status} />
            </div>
            <p className="text-sm text-slate-300 mt-3">{result.summary}</p>
            {result.case_id && (
              <Link to={`/cases/${result.case_id}`} className="text-xs text-blue-400 hover:underline block mt-2">
                Open case &amp; evidence dossier →
              </Link>
            )}
          </div>

          {result.findings.length > 0 && (
            <div className="space-y-3">
              {result.findings.map((f) => (
                <div key={f.finding_number} className="rounded-lg border border-surface-border bg-surface-panel p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-semibold">{f.finding_number} — {f.category.replace(/_/g, " ")}</div>
                    <StatusBadge status={f.status} />
                  </div>
                  <dl className="text-xs text-slate-400 mt-2 space-y-1">
                    <div><dt className="inline text-slate-500">URL: </dt><dd className="inline break-all">{f.source_url}</dd></div>
                    <div><dt className="inline text-slate-500">Tanggal: </dt><dd className="inline">{f.observed_at ?? "—"}</dd></div>
                    <div><dt className="inline text-slate-500">Bukti: </dt><dd className="inline">{f.evidence_ids.join(", ") || "—"}</dd></div>
                    <div><dt className="inline text-slate-500">Kebijakan terkait: </dt><dd className="inline">{f.policy_reference ?? "—"}</dd></div>
                    <div><dt className="inline text-slate-500">Confidence: </dt><dd className="inline">{(f.confidence * 100).toFixed(0)}% (triase, bukan vonis)</dd></div>
                  </dl>
                  <p className="text-xs text-slate-300 mt-2 whitespace-pre-line">{f.reasoning}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
