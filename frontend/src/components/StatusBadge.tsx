const COLOR_MAP: Record<string, string> = {
  // neutral / in-progress
  NEW: "bg-slate-500/15 text-slate-300",
  COLLECTING_EVIDENCE: "bg-slate-500/15 text-slate-300",
  PENDING: "bg-slate-500/15 text-slate-300",
  PENDING_REVIEW: "bg-slate-500/15 text-slate-300",
  DRAFT: "bg-slate-500/15 text-slate-300",
  UNKNOWN: "bg-slate-500/15 text-slate-300",
  COULD_NOT_COLLECT: "bg-slate-500/15 text-slate-300",
  PERLU_VERIFIKASI: "bg-amber-500/15 text-amber-400",

  // in review / attention
  UNDER_REVIEW: "bg-amber-500/15 text-amber-400",
  NEEDS_REVIEW: "bg-amber-500/15 text-amber-400",
  NEEDS_MORE_EVIDENCE: "bg-amber-500/15 text-amber-400",
  RETURNED: "bg-amber-500/15 text-amber-400",
  DUPLICATE: "bg-amber-500/15 text-amber-400",

  // confirmed / good
  EVIDENCE_VALIDATED: "bg-emerald-500/15 text-emerald-400",
  VIOLATION_CONFIRMED: "bg-emerald-500/15 text-emerald-400",
  CONFIRMED: "bg-emerald-500/15 text-emerald-400",
  VERIFIED: "bg-emerald-500/15 text-emerald-400",
  READY: "bg-emerald-500/15 text-emerald-400",
  APPROVED: "bg-emerald-500/15 text-emerald-400",
  ACTIONED: "bg-emerald-500/15 text-emerald-400",
  ACKNOWLEDGED: "bg-emerald-500/15 text-emerald-400",

  // submitted / in flight
  REPORT_READY: "bg-blue-500/15 text-blue-400",
  SUBMITTED: "bg-blue-500/15 text-blue-400",

  // negative
  REJECTED: "bg-rose-500/15 text-rose-400",
  NOT_CONFIRMED: "bg-rose-500/15 text-rose-400",
  FAILED: "bg-rose-500/15 text-rose-400",
  INSUFFICIENT: "bg-rose-500/15 text-rose-400",
  INSUFFICIENT_EVIDENCE: "bg-rose-500/15 text-rose-400",
  CLOSED: "bg-slate-700/40 text-slate-400",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = COLOR_MAP[status] ?? "bg-slate-500/15 text-slate-300";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium tracking-wide ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
