import { useEffect, useState } from "react";
import { api } from "../api/client";
import Layout from "../components/Layout";
import type { Platform, Policy } from "../types";

export default function Policies() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);

  useEffect(() => {
    api.get<Policy[]>("/policies").then(setPolicies);
    api.get<Platform[]>("/platforms").then(setPlatforms);
  }, []);

  const platformName = (id: string) => platforms.find((p) => p.id === id)?.name ?? id;

  return (
    <Layout title="Policy Rules">
      <p className="text-sm text-slate-400 mb-4">
        Keyword lists here are used for triage only — a keyword match is never treated as a violation decision by itself.
      </p>
      <div className="space-y-4">
        {policies.map((p) => (
          <div key={p.id} className="rounded-lg border border-surface-border bg-surface-panel p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100">{p.name}</h3>
              <span className="text-xs text-slate-500">{platformName(p.platform_id)}</span>
            </div>
            <table className="w-full text-sm mt-3">
              <thead className="text-slate-400 text-xs uppercase">
                <tr>
                  <th className="text-left py-1">Rule</th>
                  <th className="text-left py-1">Category</th>
                  <th className="text-left py-1">Severity</th>
                  <th className="text-left py-1">Description</th>
                </tr>
              </thead>
              <tbody>
                {p.rules.map((r) => (
                  <tr key={r.id} className="border-t border-surface-border">
                    <td className="py-1.5 font-mono text-xs">{r.rule_code}</td>
                    <td className="py-1.5">{r.category.replace(/_/g, " ")}</td>
                    <td className="py-1.5 text-slate-400">{r.severity}</td>
                    <td className="py-1.5 text-slate-400">{r.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </Layout>
  );
}
