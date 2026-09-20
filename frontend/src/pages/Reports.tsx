import { useEffect, useState } from "react";
import { api, ApiError, downloadFile } from "../api/client";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { Case, Report } from "../types";

export default function Reports() {
  const { hasRole } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  function refresh() {
    api.get<Report[]>("/reports").then(setReports);
    api.get<Case[]>("/cases").then(setCases);
  }
  useEffect(refresh, []);

  const caseNumber = (id: string) => cases.find((c) => c.id === id)?.case_number ?? id;

  async function submit(id: string) {
    setMessage(null);
    try {
      await api.post(`/reports/${id}/submit`, { method: "MANUAL" });
      setMessage("Marked as awaiting human submission through the platform's official reporting channel.");
      refresh();
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) {
        const detail = e.detail as { error?: string; missing?: string[] };
        setMessage(`REPORT NOT READY. Missing: ${(detail.missing ?? []).join(", ")}`);
      } else {
        setMessage("Failed to submit report.");
      }
    }
  }

  return (
    <Layout title="Reports">
      {message && <div className="mb-4 text-sm text-amber-400 border border-amber-500/30 bg-amber-500/10 rounded-md px-3 py-2">{message}</div>}
      <div className="rounded-lg border border-surface-border bg-surface-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Report #</th>
              <th className="text-left px-4 py-2">Case</th>
              <th className="text-left px-4 py-2">Readiness</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Export</th>
              <th className="text-left px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.id} className="border-t border-surface-border">
                <td className="px-4 py-2">{r.report_number}</td>
                <td className="px-4 py-2 text-slate-400">{caseNumber(r.case_id)}</td>
                <td className="px-4 py-2"><StatusBadge status={r.readiness_level} /> <span className="text-xs text-slate-500">{r.readiness_score}%</span></td>
                <td className="px-4 py-2"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-2 space-x-2">
                  <button onClick={() => downloadFile(`/reports/${r.id}/export/pdf`, `${r.report_number}.pdf`)} className="text-xs text-blue-400 hover:underline">PDF</button>
                  <button onClick={() => downloadFile(`/reports/${r.id}/export/json`, `${r.report_number}.json`)} className="text-xs text-blue-400 hover:underline">JSON</button>
                  <button onClick={() => downloadFile(`/reports/${r.id}/export/csv`, `${r.report_number}.csv`)} className="text-xs text-blue-400 hover:underline">CSV</button>
                </td>
                <td className="px-4 py-2">
                  {hasRole("ADMIN", "ANALYST") && r.status === "READY" && (
                    <button onClick={() => submit(r.id)} className="text-xs px-2 py-1 rounded bg-accent-DEFAULT text-white">
                      Mark for Manual Submission
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-slate-500 mt-3">
        This system never automates submission through a platform's reporting form. "Manual submission" means the operator
        exports the report and files it themselves via the platform's official channel.
      </p>
    </Layout>
  );
}
