import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/projects", label: "Projects" },
  { to: "/import", label: "Import data" },
  { to: "/charts", label: "Cost comparison" },
  { to: "/pert", label: "PERT analysis" },
  { to: "/compare", label: "Compare projects" },
  { to: "/insights", label: "AI insights" },
  { to: "/reports", label: "Reports" },
  { to: "/security", label: "Security Center" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  async function signOut() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16.5rem_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      {open ? <button className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden" aria-label="Close menu" onClick={() => setOpen(false)} /> : null}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-lavender-100 bg-white px-4 py-5 transition lg:static lg:w-auto lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="px-2">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-700">CostWise AI</p>
          <p className="mt-1 text-sm text-mist">Project cost review</p>
        </div>
        <nav className="mt-6 flex-1 space-y-1" aria-label="Primary">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2.5 text-sm font-medium ${
                  isActive ? "bg-lavender-100 text-primary-700" : "text-ink hover:bg-canvas"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="rounded-2xl bg-canvas p-3">
          <p className="truncate text-sm font-semibold">{user?.full_name}</p>
          <p className="truncate text-xs text-mist">{user?.email}</p>
          <button type="button" className="btn-secondary mt-3 w-full" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-canvas/90 px-4 py-3 backdrop-blur lg:px-8">
          <button type="button" className="btn-secondary px-3 lg:hidden" onClick={() => setOpen(true)} aria-expanded={open} aria-controls="app-sidebar">
            Menu
          </button>
          <p className="text-sm text-mist">Fictional sample data is enough. Do not enter real financial records.</p>
        </header>
        <main id="main" className="px-4 py-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
