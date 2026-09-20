import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import Layout from "../components/Layout";
import StatCard from "../components/StatCard";
import type { DashboardStats } from "../types";

const PALETTE = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#06b6d4", "#eab308", "#64748b"];

function ChartPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-panel p-4">
      <div className="text-sm font-medium text-slate-200 mb-3">{title}</div>
      <div style={{ width: "100%", height: 220 }}>{children}</div>
    </div>
  );
}

function objToChartData(obj: Record<string, number>) {
  return Object.entries(obj).map(([name, value]) => ({ name, value }));
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DashboardStats>("/dashboard/stats")
      .then(setStats)
      .catch(() => setError("Failed to load dashboard stats."));
  }, []);

  if (error) return <Layout title="Dashboard"><div className="text-rose-400">{error}</div></Layout>;
  if (!stats) return <Layout title="Dashboard"><div className="text-slate-400">Loading…</div></Layout>;

  return (
    <Layout title="Dashboard">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <StatCard label="Total Cases" value={stats.total_cases} />
        <StatCard label="Open Cases" value={stats.open_cases} />
        <StatCard label="Under Review" value={stats.under_review} tone="warn" />
        <StatCard label="Validated Cases" value={stats.validated_cases} tone="good" />
        <StatCard label="Reports Ready" value={stats.reports_ready} tone="good" />
        <StatCard label="Reports Submitted" value={stats.reports_submitted} />
        <StatCard label="Platform Responses" value={stats.platform_responses} />
        <StatCard label="Action Taken" value={stats.action_taken} tone="good" />
        <StatCard label="Rejected Reports" value={stats.rejected_reports} tone="bad" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartPanel title="Cases by Platform">
          <ResponsiveContainer>
            <BarChart data={objToChartData(stats.by_platform)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2b42" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
              <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#111a2c", border: "1px solid #1f2b42" }} />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Violation Category">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={objToChartData(stats.by_violation_category)} dataKey="value" nameKey="name" outerRadius={80}>
                {objToChartData(stats.by_violation_category).map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#111a2c", border: "1px solid #1f2b42" }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Case Status">
          <ResponsiveContainer>
            <BarChart data={objToChartData(stats.by_status)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2b42" />
              <XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} />
              <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={10} width={130} />
              <Tooltip contentStyle={{ background: "#111a2c", border: "1px solid #1f2b42" }} />
              <Bar dataKey="value" fill="#22c55e" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Evidence Validity">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={objToChartData(stats.by_evidence_validity)} dataKey="value" nameKey="name" outerRadius={80}>
                {objToChartData(stats.by_evidence_validity).map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#111a2c", border: "1px solid #1f2b42" }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Case Timeline (last 30 days)">
          <ResponsiveContainer>
            <LineChart data={stats.timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2b42" />
              <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} />
              <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#111a2c", border: "1px solid #1f2b42" }} />
              <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>
    </Layout>
  );
}
