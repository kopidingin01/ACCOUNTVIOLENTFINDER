import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ReadinessPreview } from "../types";
import StatusBadge from "./StatusBadge";

export default function ReadinessCheck({ caseId, refreshKey }: { caseId: string; refreshKey?: unknown }) {
  const [preview, setPreview] = useState<ReadinessPreview | null>(null);

  useEffect(() => {
    api.get<ReadinessPreview>(`/cases/${caseId}/readiness`).then(setPreview).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, refreshKey]);

  if (!preview) return null;

  const barColor = preview.level === "READY" ? "bg-emerald-500" : preview.level === "NEEDS_REVIEW" ? "bg-amber-500" : "bg-rose-500";

  return (
    <div className="rounded-lg border border-surface-border bg-surface-panel p-4 mb-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-200">Report Quality Check</h3>
        <div className="flex items-center gap-2">
          <StatusBadge status={preview.level} />
          <span className="text-xs text-slate-500 font-mono">{preview.score}%</span>
        </div>
      </div>
      <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden mb-3">
        <div className={`h-full ${barColor} transition-all duration-300`} style={{ width: `${preview.score}%` }} />
      </div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
        {preview.items.map((item) => (
          <li key={item.key} className="flex items-center gap-2 text-xs">
            <span className={item.met ? "text-emerald-400" : "text-slate-600"}>{item.met ? "✓" : "○"}</span>
            <span className={item.met ? "text-slate-300" : "text-slate-500"}>{item.label}</span>
            {item.weight > 0 && <span className="text-slate-600 ml-auto font-mono">{item.weight}%</span>}
          </li>
        ))}
      </ul>
      {preview.missing_items.length > 0 && (
        <p className="text-[11px] text-amber-400 mt-3">
          Belum lengkap: {preview.missing_items.join(", ")}
        </p>
      )}
    </div>
  );
}
