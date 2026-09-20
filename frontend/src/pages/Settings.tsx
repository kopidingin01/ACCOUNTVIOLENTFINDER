import Layout from "../components/Layout";
import { useAuth } from "../hooks/useAuth";

export default function Settings() {
  const { user } = useAuth();
  return (
    <Layout title="Settings">
      <div className="rounded-lg border border-surface-border bg-surface-panel p-4 max-w-lg space-y-3">
        <div>
          <div className="text-[11px] uppercase text-slate-500">Signed in as</div>
          <div className="text-sm text-slate-200">{user?.full_name} ({user?.username})</div>
        </div>
        <div>
          <div className="text-[11px] uppercase text-slate-500">Role</div>
          <div className="text-sm text-slate-200">{user?.role}</div>
        </div>
        <div className="pt-3 border-t border-surface-border text-xs text-slate-500 space-y-1">
          <p>Evidence retention, case retention, and audit retention periods are configured server-side via environment variables (see .env.example) and are not user-editable from this screen for auditability reasons.</p>
          <p>Platform API credentials (for official reporting APIs) are managed by an administrator and are never displayed once saved.</p>
        </div>
      </div>
    </Layout>
  );
}
