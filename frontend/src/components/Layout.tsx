import { NavLink, Outlet } from "react-router-dom";
import { BriefcaseBusiness, History, LayoutDashboard, Radar, Sparkles, UserRound } from "lucide-react";

import { cn } from "../lib/cn";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/jobs", label: "Jobs", icon: BriefcaseBusiness },
  { to: "/history", label: "History", icon: History },
  { to: "/profile", label: "Profile", icon: UserRound },
];

export default function Layout() {
  return (
    <div className="min-h-screen">
      <div className="mx-auto flex w-full max-w-7xl">
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-slate-800/70 px-4 py-6 md:flex">
          <div className="flex items-center gap-2 px-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400">
              <Radar className="h-5 w-5" />
            </span>
            <div>
              <p className="text-sm font-semibold text-white">AI Job Radar</p>
              <p className="text-[11px] text-slate-500">matched vacancies</p>
            </div>
          </div>

          <nav className="mt-8 flex flex-col gap-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-sky-500/10 text-sky-300"
                      : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-xs text-slate-400">
            <div className="flex items-center gap-2 text-slate-300">
              <Sparkles className="h-3.5 w-3.5 text-sky-400" />
              AI analysis on
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Scores are cached per profile and prompt version.
            </p>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-slate-800/70 bg-slate-950/80 backdrop-blur md:hidden">
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-2">
                <Radar className="h-5 w-5 text-sky-400" />
                <span className="text-sm font-semibold text-white">AI Job Radar</span>
              </div>
            </div>
            <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
              {NAV.map(({ to, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      "whitespace-nowrap rounded-lg px-3 py-1.5 text-xs",
                      isActive ? "bg-sky-500/10 text-sky-300" : "text-slate-400",
                    )
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>
          </header>

          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 md:py-10">
            <Outlet />
          </main>

          <footer className="border-t border-slate-900 px-6 py-4 text-center text-[11px] text-slate-600">
            AI Job Radar · FastAPI + PostgreSQL + Celery + React
          </footer>
        </div>
      </div>
    </div>
  );
}
