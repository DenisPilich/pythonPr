import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { ExternalLink, Menu, Radio, X } from "lucide-react";

import { cn } from "../lib/cn";

const THEMES = ["ultraviolet", "phosphor", "amber"] as const;
type Theme = (typeof THEMES)[number];

const NAV = [
  { to: "/", label: "overview", code: "01", end: true },
  { to: "/jobs", label: "vacancies", code: "02" },
  { to: "/history", label: "history", code: "03" },
  { to: "/profile", label: "profile", code: "04" },
];

const DOCS_URL =
  import.meta.env.VITE_DOCS_URL ?? "http://localhost:8000/docs";

function readTheme(): Theme {
  try {
    const requested = new URLSearchParams(window.location.search).get("theme");
    if (requested && (THEMES as readonly string[]).includes(requested)) {
      return requested as Theme;
    }
    const stored = localStorage.getItem("radar:theme");
    if (stored && (THEMES as readonly string[]).includes(stored)) {
      return stored as Theme;
    }
  } catch {
    // private mode
  }
  return "ultraviolet";
}

function readCrt(): boolean {
  try {
    return localStorage.getItem("radar:crt") === "on";
  } catch {
    return false;
  }
}

function RadarMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <circle cx="16" cy="16" r="12.5" stroke="currentColor" strokeWidth="1" opacity=".55" />
      <circle cx="16" cy="16" r="7" stroke="currentColor" strokeWidth="1" opacity=".3" />
      <path d="M16 16 26.5 9.5" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="16" cy="16" r="1.8" fill="currentColor" />
      <circle cx="22" cy="11.5" r="1.4" fill="currentColor" opacity=".85" />
      <path d="M3.5 16h3M25.5 16h3M16 3.5v3M16 25.5v3" stroke="currentColor" strokeWidth="1" opacity=".45" />
    </svg>
  );
}

function pageName(pathname: string): string {
  if (pathname.startsWith("/jobs/")) return "vacancy";
  if (pathname.startsWith("/jobs")) return "vacancies";
  if (pathname.startsWith("/history")) return "history";
  if (pathname.startsWith("/profile")) return "profile";
  return "overview";
}

export default function Layout() {
  const location = useLocation();
  const glowRef = useRef<HTMLDivElement>(null);
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [crt, setCrt] = useState<boolean>(readCrt);
  const [menuOpen, setMenuOpen] = useState(false);
  const [clock, setClock] = useState(() => new Date());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("radar:theme", theme);
    } catch {
      // private mode
    }
  }, [theme]);

  useEffect(() => {
    if (crt) document.documentElement.dataset.crt = "on";
    else delete document.documentElement.dataset.crt;
    try {
      localStorage.setItem("radar:crt", crt ? "on" : "off");
    } catch {
      // private mode
    }
  }, [crt]);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!location.hash) return;
    const target = decodeURIComponent(location.hash.slice(1));
    const timer = window.setTimeout(() => {
      const element = document.getElementById(target);
      if (!element) return;
      const top = element.getBoundingClientRect().top + window.scrollY - 72;
      window.scrollTo({ top, behavior: "auto" });
    }, 400);
    return () => window.clearTimeout(timer);
  }, [location.pathname, location.hash]);

  useEffect(() => {
    const timer = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const element = glowRef.current;
    if (!element) return;
    let frame = 0;
    function onPointerMove(event: PointerEvent) {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        element!.style.transform = `translate(${event.clientX - 300}px, ${event.clientY - 300}px)`;
      });
    }
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key !== "F2") return;
      event.preventDefault();
      setTheme((current) => {
        const index = THEMES.indexOf(current);
        return THEMES[(index + 1) % THEMES.length];
      });
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const time = clock.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="min-h-screen">
      <div ref={glowRef} className="pointer-glow" aria-hidden />
      <header className="fixed inset-x-0 top-0 z-40 border-b border-slate-800 bg-slate-950/85 backdrop-blur-md">
        <div className="mx-auto flex h-[58px] max-w-[1440px] items-center gap-5 px-4 md:px-8">
          <NavLink to="/" className="group flex shrink-0 items-center gap-2.5">
            <RadarMark className="h-7 w-7 text-sky-400 transition-transform duration-300 group-hover:rotate-90" />
            <span className="font-display text-[26px] leading-none tracking-tight text-white">
              AI_JOB_RADAR
            </span>
            <span className="hidden text-[9px] uppercase tracking-[0.18em] text-slate-600 sm:inline">
              v0.1.0
            </span>
          </NavLink>

          <nav className="ml-2 hidden items-center gap-1 md:flex" aria-label="Main">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "group relative flex items-center gap-1.5 px-3 py-2 text-[10px] uppercase tracking-[0.16em] transition-colors",
                    isActive
                      ? "text-white"
                      : "text-slate-400 hover:text-sky-300",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="nav-number">{item.code}</span>
                    <span>{item.label}</span>
                    <span
                      className={cn(
                        "absolute inset-x-3 -bottom-[1px] h-px bg-sky-500 transition-opacity",
                        isActive ? "opacity-100" : "opacity-0",
                      )}
                    />
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <a
              href={DOCS_URL}
              target="_blank"
              rel="noreferrer"
              className="hidden items-center gap-1 border border-slate-700 px-2.5 py-1.5 text-[9px] uppercase tracking-[0.14em] text-slate-400 transition-colors hover:border-sky-500 hover:text-sky-300 sm:inline-flex"
            >
              api <ExternalLink className="h-3 w-3" />
            </a>
            <button
              type="button"
              onClick={() => setCrt((value) => !value)}
              className="hidden border border-slate-700 px-2.5 py-1.5 text-[9px] uppercase tracking-[0.14em] text-slate-400 transition-colors hover:border-sky-500 hover:text-sky-300 lg:inline-flex"
              aria-pressed={crt}
              title="Toggle CRT scanlines"
            >
              crt:{crt ? "on" : "off"}
            </button>
            <button
              type="button"
              onClick={() =>
                setTheme(
                  THEMES[
                    (THEMES.indexOf(theme) + 1) % THEMES.length
                  ],
                )
              }
              className="inline-flex items-center gap-1.5 border border-slate-700 px-2.5 py-1.5 text-[9px] uppercase tracking-[0.14em] text-slate-300 transition-colors hover:border-sky-500 hover:text-sky-300"
              title="Cycle theme (F2)"
            >
              <Radio className="h-3 w-3 text-sky-400" />
              {theme}
            </button>
            <button
              type="button"
              onClick={() => setMenuOpen((value) => !value)}
              className="inline-flex border border-slate-700 p-1.5 text-slate-300 md:hidden"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
            >
              {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {menuOpen ? (
          <nav
            className="border-t border-slate-800 bg-slate-950/95 px-4 py-3 md:hidden"
            aria-label="Mobile"
          >
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center justify-between border-b border-slate-800/60 py-2.5 text-[11px] uppercase tracking-[0.16em]",
                    isActive ? "text-sky-300" : "text-slate-400",
                  )
                }
              >
                <span>{item.label}</span>
                <span className="nav-number">{item.code}</span>
              </NavLink>
            ))}
          </nav>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-[1440px] px-4 pb-16 pt-[82px] md:px-8 md:pt-[92px]">
        <div key={location.pathname} className="page-enter">
          <Outlet />
        </div>
      </main>

      <footer className="statusbar fixed inset-x-0 bottom-0 z-50 h-7">
        <div className="mx-auto flex h-full max-w-[1440px] items-center gap-3 px-4 text-[9px] uppercase tracking-[0.14em] text-slate-500 md:px-8">
          <span className="status-dot" aria-hidden />
          <span className="text-slate-300">radar online</span>
          <span className="hidden text-slate-700 sm:inline">/</span>
          <span className="hidden sm:inline">{pageName(location.pathname)}</span>

          <span className="mx-auto hidden items-center gap-3 md:flex">
            <button
              type="button"
              onClick={() => setTheme(THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length])}
              className="transition-colors hover:text-sky-300"
            >
              <span className="kbd">F2</span> theme
            </button>
            <button
              type="button"
              onClick={() => setCrt((value) => !value)}
              className="transition-colors hover:text-sky-300"
            >
              <span className="kbd">CRT</span> {crt ? "on" : "off"}
            </button>
            <span className="text-slate-700">·</span>
            <span>fastapi + celery</span>
          </span>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-slate-600 sm:inline">theme:{theme}</span>
            <span className="text-slate-400">{time}</span>
            <button
              type="button"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="transition-colors hover:text-sky-300"
            >
              top ↑
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
