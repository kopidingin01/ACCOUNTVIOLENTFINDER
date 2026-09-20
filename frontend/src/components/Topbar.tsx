import { useAuth } from "../hooks/useAuth";

export default function Topbar({ title }: { title: string }) {
  const { user, logout } = useAuth();
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface/60 backdrop-blur sticky top-0 z-10">
      <h1 className="text-lg font-semibold text-slate-100">{title}</h1>
      {user && (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-300">{user.full_name}</span>
          <span className="px-2 py-0.5 rounded bg-white/5 text-[11px] text-slate-400 uppercase tracking-wide">
            {user.role}
          </span>
          <button onClick={logout} className="text-slate-400 hover:text-slate-200 transition-colors">
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
