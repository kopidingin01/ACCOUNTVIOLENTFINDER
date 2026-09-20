export default function StatCard({ label, value, tone = "default" }: { label: string; value: number | string; tone?: "default" | "warn" | "good" | "bad" }) {
  const toneClass: Record<string, string> = {
    default: "text-slate-100",
    warn: "text-amber-400",
    good: "text-emerald-400",
    bad: "text-rose-400",
  };
  return (
    <div className="rounded-lg border border-surface-border bg-surface-panel px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${toneClass[tone]}`}>{value}</div>
    </div>
  );
}
