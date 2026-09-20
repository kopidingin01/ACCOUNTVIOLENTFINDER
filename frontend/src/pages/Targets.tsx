import { useEffect, useState } from "react";
import { api } from "../api/client";
import Layout from "../components/Layout";
import SafeLink from "../components/SafeLink";
import type { Platform, Target } from "../types";

export default function Targets() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);

  useEffect(() => {
    api.get<Target[]>("/targets").then(setTargets);
    api.get<Platform[]>("/platforms").then(setPlatforms);
  }, []);

  const platformName = (id: string) => platforms.find((p) => p.id === id)?.name ?? id;

  return (
    <Layout title="Targets">
      <p className="text-sm text-slate-400 mb-4">
        Target accounts are described only using information they made publicly visible. No private data is collected.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {targets.map((t) => (
          <div key={t.id} className="rounded-lg border border-surface-border bg-surface-panel p-4">
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-100">@{t.username}</span>
              <span className="text-[11px] text-slate-500">{t.verification_status}</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">{platformName(t.platform_id)}</div>
            {t.profile_description && <p className="text-xs text-slate-400 mt-2 line-clamp-3">{t.profile_description}</p>}
            <SafeLink href={t.profile_url} className="text-xs text-blue-400 hover:underline block mt-2 truncate">
              {t.profile_url}
            </SafeLink>
            <div className="flex gap-3 text-[11px] text-slate-500 mt-2">
              <span>Followers: {t.public_followers ?? "—"}</span>
              <span>Posts: {t.public_posts ?? "—"}</span>
            </div>
            <div className="text-[10px] text-slate-600 mt-2">Collected {new Date(t.collected_at).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </Layout>
  );
}
