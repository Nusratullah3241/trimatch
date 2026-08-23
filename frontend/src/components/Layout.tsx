import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Ledger", end: true },
  { to: "/new", label: "New match" },
  { to: "/metrics", label: "Metrics" },
  { to: "/settings", label: "Tolerances" },
];

export default function Layout() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-rule bg-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex items-baseline gap-8 py-5">
            <div>
              <span className="font-mono text-lg font-semibold tracking-tight">TriMatch</span>
              <span className="eyebrow ml-3">Accounts payable reconciliation</span>
            </div>
          </div>

          <nav className="flex gap-6 -mb-px">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `pb-3 text-sm border-b-2 transition-colors ${
                    isActive
                      ? "border-ink text-ink font-medium"
                      : "border-transparent text-muted hover:text-ink"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  );
}
