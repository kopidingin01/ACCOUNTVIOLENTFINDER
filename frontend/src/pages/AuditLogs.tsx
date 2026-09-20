import { useEffect, useState } from "react";
import { api } from "../api/client";
import Layout from "../components/Layout";
import type { AuditLogEntry } from "../types";

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);

  useEffect(() => {
    api.get<AuditLogEntry[]>("/audit").then(setLogs);
  }, []);

  return (
    <Layout title="Audit Logs">
      <p className="text-sm text-slate-400 mb-4">
        Append-only trail of every significant action. Entries cannot be edited or deleted through this application.
      </p>
      <div className="rounded-lg border border-surface-border bg-surface-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Timestamp</th>
              <th className="text-left px-4 py-2">Action</th>
              <th className="text-left px-4 py-2">Resource</th>
              <th className="text-left px-4 py-2">User</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-t border-surface-border">
                <td className="px-4 py-2 text-slate-400">{new Date(l.timestamp).toLocaleString()}</td>
                <td className="px-4 py-2 font-mono text-xs">{l.action}</td>
                <td className="px-4 py-2 text-slate-400">{l.resource_type ? `${l.resource_type}:${l.resource_id}` : "—"}</td>
                <td className="px-4 py-2 text-slate-500 text-xs">{l.user_id ?? "system"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
