import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError, downloadFile } from "../api/client";
import Layout from "../components/Layout";
import ReadinessCheck from "../components/ReadinessCheck";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { AuditLogEntry, Case, Evidence, Assessment, Platform, Report, Target } from "../types";

const CASE_STATUSES = [
  "NEW", "COLLECTING_EVIDENCE", "EVIDENCE_VALIDATED", "UNDER_REVIEW", "VIOLATION_CONFIRMED",
  "REPORT_READY", "SUBMITTED", "ACKNOWLEDGED", "ACTION_TAKEN", "REJECTED", "CLOSED",
];

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [platform, setPlatform] = useState<Platform | null>(null);
  const [target, setTarget] = useState<Target | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [audit, setAudit] = useState<AuditLogEntry[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ title: "", priority: "MEDIUM", description: "", status: "NEW" });
  const [editError, setEditError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const canEdit = hasRole("ADMIN", "ANALYST");
  const canDelete = hasRole("ADMIN");

  function refresh() {
    if (!id) return;
    api.get<Case>(`/cases/${id}`).then((c) => {
      setCaseData(c);
      api.get<Platform>(`/platforms/${c.platform_id}`).then(setPlatform);
      if (c.target_id) api.get<Target>(`/targets/${c.target_id}`).then(setTarget);
      // Filter using the case number from this response, not component
      // state — state set above hasn't re-rendered yet, so reading
      // caseData here would always see the previous (often null) value.
      api.get<AuditLogEntry[]>(`/audit?resource_type=case`).then((rows) =>
        setAudit(rows.filter((r) => r.resource_id === c.case_number))
      );
    });
    api.get<Evidence[]>(`/evidence?case_id=${id}`).then(setEvidence);
    api.get<Assessment[]>(`/assessments?case_id=${id}`).then(setAssessments);
    api.get<Report[]>(`/reports?case_id=${id}`).then(setReports);
  }

  useEffect(refresh, [id]);

  async function runAssessment() {
    if (!id) return;
    setMessage(null);
    try {
      await api.post(`/assessments`, { case_id: id });
      setMessage("Assessment engine run. See results below — human review is still required.");
      refresh();
    } catch (e) {
      setMessage(e instanceof ApiError ? String(e.detail) : "Failed to run assessment");
    }
  }

  async function generateReport(assessmentId?: string) {
    if (!id) return;
    setMessage(null);
    try {
      await api.post(`/reports`, { case_id: id, assessment_id: assessmentId });
      setMessage("Report generated.");
      refresh();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        const detail = e.detail as { existing_report_id?: string };
        setMessage(`DUPLICATE REPORT DETECTED — existing report ${detail.existing_report_id ?? ""}. Use the existing report instead of generating a new one.`);
      } else {
        setMessage(e instanceof ApiError ? String(e.detail) : "Failed to generate report");
      }
    }
  }

  function startEdit() {
    if (!caseData) return;
    setEditForm({
      title: caseData.title,
      priority: caseData.priority,
      description: caseData.description ?? "",
      status: caseData.status,
    });
    setEditError(null);
    setEditing(true);
  }

  async function saveEdit() {
    if (!id) return;
    setEditError(null);
    try {
      await api.patch(`/cases/${id}`, editForm);
      setEditing(false);
      refresh();
    } catch (e) {
      setEditError(e instanceof ApiError ? String(e.detail) : "Failed to update case");
    }
  }

  async function setStatus(newStatus: string) {
    if (!id) return;
    setMessage(null);
    try {
      await api.patch(`/cases/${id}`, { status: newStatus });
      refresh();
    } catch (e) {
      setMessage(e instanceof ApiError ? String(e.detail) : "Failed to update status");
    }
  }

  async function deleteCase() {
    if (!id || !caseData) return;
    const confirmed = window.confirm(
      `Permanently delete case ${caseData.case_number}? This removes all its evidence, assessments, and reports too, and cannot be undone.\n\nTo just retire the case while keeping the record, use "Reject" or "Close" instead.`
    );
    if (!confirmed) return;
    setDeleting(true);
    try {
      await api.delete(`/cases/${id}`);
      navigate("/cases");
    } catch (e) {
      setMessage(e instanceof ApiError ? String(e.detail) : "Failed to delete case");
      setDeleting(false);
    }
  }

  if (!caseData) return <Layout title="Case"><div className="text-slate-400">Loading…</div></Layout>;

  return (
    <Layout title={caseData.case_number}>
      <div className="mb-6">
        {editing ? (
          <div className="rounded-lg border border-surface-border bg-surface-panel p-4 space-y-3 max-w-lg">
            <input
              className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
              placeholder="Case title"
              value={editForm.title}
              onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
            />
            <div className="flex gap-3">
              <select
                className="flex-1 rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
                value={editForm.priority}
                onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
              >
                {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
              <select
                className="flex-1 rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
                value={editForm.status}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
              >
                {CASE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <textarea
              className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
              placeholder="Description"
              value={editForm.description}
              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
            />
            {editError && <div className="text-sm text-rose-400">{editError}</div>}
            <div className="flex gap-2">
              <button onClick={saveEdit} className="px-3 py-1.5 rounded-md bg-accent-DEFAULT text-white text-sm">
                Save
              </button>
              <button onClick={() => setEditing(false)} className="px-3 py-1.5 rounded-md border border-surface-border text-sm text-slate-300">
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold text-slate-100">{caseData.title}</h2>
              <div className="flex items-center gap-2 shrink-0">
                {canEdit && (
                  <button onClick={startEdit} className="text-xs px-2.5 py-1 rounded border border-surface-border text-slate-300 hover:bg-white/5">
                    Edit
                  </button>
                )}
                {canEdit && caseData.status !== "REJECTED" && (
                  <button onClick={() => setStatus("REJECTED")} className="text-xs px-2.5 py-1 rounded border border-amber-500/40 text-amber-400 hover:bg-amber-500/10">
                    Reject
                  </button>
                )}
                {canEdit && caseData.status !== "CLOSED" && (
                  <button onClick={() => setStatus("CLOSED")} className="text-xs px-2.5 py-1 rounded border border-surface-border text-slate-300 hover:bg-white/5">
                    Close
                  </button>
                )}
                {canDelete && (
                  <button
                    onClick={deleteCase}
                    disabled={deleting}
                    className="text-xs px-2.5 py-1 rounded border border-rose-500/40 text-rose-400 hover:bg-rose-500/10 disabled:opacity-50"
                  >
                    {deleting ? "Deleting…" : "Delete"}
                  </button>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={caseData.status} />
              <span className="text-xs text-slate-500">Priority: {caseData.priority}</span>
              <span className="text-xs text-slate-500">Platform: {platform?.name}</span>
            </div>
            {caseData.description && <p className="text-sm text-slate-400 mt-2">{caseData.description}</p>}
          </>
        )}
      </div>

      {message && <div className="mb-4 text-sm text-amber-400 border border-amber-500/30 bg-amber-500/10 rounded-md px-3 py-2">{message}</div>}

      {id && <ReadinessCheck caseId={id} refreshKey={`${evidence.length}-${assessments.length}-${reports.length}`} />}

      {target && (
        <Section title="Target Account">
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <Field label="Username" value={target.username} />
            <Field label="Display Name" value={target.display_name ?? "—"} />
            <Field label="Verification" value={target.verification_status} />
            <Field label="Profile URL" value={<a className="text-blue-400 hover:underline" href={target.profile_url} target="_blank" rel="noreferrer">{target.profile_url}</a>} />
          </dl>
        </Section>
      )}

      <Section
        title="Evidence"
        action={
          hasRole("ADMIN", "ANALYST") && (
            <a href="/evidence" className="text-xs text-blue-400 hover:underline">
              Manage evidence →
            </a>
          )
        }
      >
        {evidence.length === 0 ? (
          <EmptyNote text="No evidence collected yet." />
        ) : (
          <table className="w-full text-sm">
            <thead className="text-slate-400 text-xs uppercase">
              <tr>
                <th className="text-left py-1">Evidence #</th>
                <th className="text-left py-1">Type</th>
                <th className="text-left py-1">Source</th>
                <th className="text-left py-1">SHA-256</th>
                <th className="text-left py-1">Status</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((e) => (
                <tr key={e.id} className="border-t border-surface-border">
                  <td className="py-1.5">{e.evidence_number}</td>
                  <td className="py-1.5 text-slate-400">{e.type}</td>
                  <td className="py-1.5 max-w-xs truncate"><a className="text-blue-400 hover:underline" href={e.source_url} target="_blank" rel="noreferrer">{e.source_url}</a></td>
                  <td className="py-1.5 font-mono text-[11px] text-slate-500">{e.sha256 ? e.sha256.slice(0, 16) + "…" : "—"}</td>
                  <td className="py-1.5"><StatusBadge status={e.verification_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section
        title="Violation Assessment"
        action={
          hasRole("ADMIN", "ANALYST") && (
            <button onClick={runAssessment} className="text-xs px-2.5 py-1 rounded bg-accent-DEFAULT text-white">
              Run Assessment
            </button>
          )
        }
      >
        {assessments.length === 0 ? (
          <EmptyNote text="No assessment run yet." />
        ) : (
          <div className="space-y-3">
            {assessments.map((a) => (
              <div key={a.id} className="border border-surface-border rounded-md p-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium">{a.category.replace(/_/g, " ")}</div>
                  <StatusBadge status={a.status} />
                </div>
                <div className="text-xs text-slate-400 mt-1">Confidence: {(a.confidence * 100).toFixed(0)}% (triage signal, not a verdict)</div>
                <p className="text-xs text-slate-400 mt-2 whitespace-pre-line">{a.reason}</p>
                {a.missing_evidence.length > 0 && (
                  <div className="text-xs text-amber-400 mt-2">Missing: {a.missing_evidence.join(", ")}</div>
                )}
                {hasRole("ADMIN", "ANALYST") && a.status === "CONFIRMED" && (
                  <button onClick={() => generateReport(a.id)} className="mt-2 text-xs px-2.5 py-1 rounded bg-accent-DEFAULT text-white">
                    Generate Report from this Assessment
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Reports">
        {reports.length === 0 ? (
          <EmptyNote text="No report generated for this case yet." />
        ) : (
          <div className="space-y-2">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between border border-surface-border rounded-md px-3 py-2">
                <div>
                  <span className="text-sm font-medium">{r.report_number}</span>
                  <span className="ml-2"><StatusBadge status={r.status} /></span>
                  <span className="ml-2"><StatusBadge status={r.readiness_level} /></span>
                  <span className="ml-2 text-xs text-slate-500">{r.readiness_score}% ready</span>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => downloadFile(`/reports/${r.id}/export/pdf`, `${r.report_number}.pdf`)} className="text-xs text-blue-400 hover:underline">PDF</button>
                  <button onClick={() => downloadFile(`/reports/${r.id}/export/json`, `${r.report_number}.json`)} className="text-xs text-blue-400 hover:underline">JSON</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Audit Trail (case-related)">
        {audit.length === 0 ? (
          <EmptyNote text="No audit entries indexed for this case number yet." />
        ) : (
          <ul className="text-xs text-slate-400 space-y-1">
            {audit.map((a) => (
              <li key={a.id}>
                {new Date(a.timestamp).toLocaleString()} — {a.action}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </Layout>
  );
}

function Section({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="mb-5 rounded-lg border border-surface-border bg-surface-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] uppercase text-slate-500">{label}</dt>
      <dd className="text-slate-200 truncate">{value}</dd>
    </div>
  );
}

function EmptyNote({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}
