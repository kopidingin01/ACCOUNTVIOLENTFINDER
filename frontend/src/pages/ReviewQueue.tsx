import { useEffect, useState } from "react";
import { api } from "../api/client";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { Assessment, Case, ReviewQueueItem } from "../types";

export default function ReviewQueue() {
  const { hasRole } = useAuth();
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [assessments, setAssessments] = useState<Record<string, Assessment>>({});

  function refresh() {
    api.get<ReviewQueueItem[]>("/reviews").then(setItems);
    api.get<Case[]>("/cases").then(setCases);
  }
  useEffect(refresh, []);

  useEffect(() => {
    items.forEach((item) => {
      if (item.assessment_id && !assessments[item.assessment_id]) {
        api.get<Assessment>(`/assessments/${item.assessment_id}`).then((a) =>
          setAssessments((prev) => ({ ...prev, [a.id]: a }))
        );
      }
    });
  }, [items]);

  const caseNumber = (id: string) => cases.find((c) => c.id === id)?.case_number ?? id;

  async function decide(id: string, action: string) {
    const notes = window.prompt("Optional reviewer notes:") ?? undefined;
    await api.post(`/reviews/${id}/decide`, { action, notes });
    refresh();
  }

  return (
    <Layout title="Review Queue">
      <p className="text-sm text-slate-400 mb-4">
        Every assessment produced by the triage engine lands here. A report cannot reach SUBMITTED status without a reviewer
        approving the linked assessment first.
      </p>
      <div className="space-y-3">
        {items.map((item) => {
          const assessment = item.assessment_id ? assessments[item.assessment_id] : undefined;
          return (
            <div key={item.id} className="rounded-lg border border-surface-border bg-surface-panel p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium">{caseNumber(item.case_id)}</div>
                <StatusBadge status={item.status} />
              </div>
              {assessment && (
                <div className="mt-2 text-xs text-slate-400">
                  <div>Category: {assessment.category.replace(/_/g, " ")} — Confidence {(assessment.confidence * 100).toFixed(0)}%</div>
                  <p className="mt-1 whitespace-pre-line">{assessment.reason}</p>
                </div>
              )}
              {hasRole("ADMIN", "REVIEWER") && item.status === "PENDING" && (
                <div className="flex gap-2 mt-3">
                  <button onClick={() => decide(item.id, "APPROVE")} className="text-xs px-2.5 py-1 rounded bg-emerald-600 text-white">Approve</button>
                  <button onClick={() => decide(item.id, "REQUEST_MORE_EVIDENCE")} className="text-xs px-2.5 py-1 rounded bg-amber-600 text-white">Request More Evidence</button>
                  <button onClick={() => decide(item.id, "RETURN_TO_OPERATOR")} className="text-xs px-2.5 py-1 rounded bg-slate-600 text-white">Return to Operator</button>
                  <button onClick={() => decide(item.id, "REJECT")} className="text-xs px-2.5 py-1 rounded bg-rose-600 text-white">Reject</button>
                </div>
              )}
            </div>
          );
        })}
        {items.length === 0 && <p className="text-sm text-slate-500">Review queue is empty.</p>}
      </div>
    </Layout>
  );
}
