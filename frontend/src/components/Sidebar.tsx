import { NavLink } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "▤" },
  { to: "/account-finder", label: "Account Finder", icon: "◎" },
  { to: "/cases", label: "Cases", icon: "🗂" },
  { to: "/evidence", label: "Evidence", icon: "🔍" },
  { to: "/targets", label: "Targets", icon: "👤" },
  { to: "/policies", label: "Policy Rules", icon: "📜" },
  { to: "/reports", label: "Reports", icon: "📄" },
  { to: "/reviews", label: "Review Queue", icon: "✅" },
  { to: "/platforms", label: "Platforms", icon: "🌐" },
  { to: "/users", label: "Users", icon: "🧑‍🤝‍🧑", adminOnly: true },
  { to: "/audit", label: "Audit Logs", icon: "🧾" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

export default function Sidebar() {
  const { hasRole } = useAuth();
  return (
    <aside className="w-60 shrink-0 border-r border-surface-border bg-surface-panel h-screen sticky top-0 flex flex-col">
      <div className="px-4 py-5 border-b border-surface-border">
        <div className="text-sm font-semibold tracking-wide text-slate-100">REPORT VALIDATOR</div>
        <div className="text-[11px] text-slate-400 mt-0.5">Evidence &amp; Trust &amp; Safety</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_ITEMS.filter((item) => !item.adminOnly || hasRole("ADMIN")).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm mx-2 rounded-md transition-colors ${
                isActive ? "bg-accent/15 text-accent-DEFAULT text-blue-400" : "text-slate-300 hover:bg-white/5"
              }`
            }
          >
            <span className="text-base leading-none w-5 text-center">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-surface-border text-[11px] text-slate-500">
        Evidence-based reporting only. Human review required before any submission.
      </div>
    </aside>
  );
}
