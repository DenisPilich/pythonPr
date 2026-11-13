import { useRef, useState } from "react";
import type { PointerEvent } from "react";

import type { JobListItem, Stats } from "../api/types";

interface HeroConsoleProps {
  stats?: Stats;
  latest: JobListItem[];
}

function Mascot() {
  return (
    <div className="hero-mascot pointer-events-none absolute -top-10 right-4 z-20 h-24 w-24 text-sky-500 md:-top-12 md:right-10 md:h-28 md:w-28">
      <svg viewBox="0 0 96 96" fill="none" aria-hidden="true">
        <ellipse cx="48" cy="86" rx="25" ry="4" fill="black" opacity=".45" />
        <path
          d="M48 24V12"
          stroke="currentColor"
          strokeWidth="2"
          opacity=".8"
        />
        <circle cx="48" cy="9" r="4" fill="currentColor">
          <animate
            attributeName="opacity"
            values="1;.35;1"
            dur="2.4s"
            repeatCount="indefinite"
          />
        </circle>
        <path
          d="M20 34 12 26l-3 8 9 6"
          fill="currentColor"
          opacity=".55"
        />
        <path
          d="M76 34l8-8 3 8-9 6"
          fill="currentColor"
          opacity=".55"
        />
        <rect
          x="19"
          y="27"
          width="58"
          height="52"
          rx="11"
          fill="currentColor"
        />
        <rect
          x="19"
          y="27"
          width="58"
          height="52"
          rx="11"
          stroke="black"
          strokeOpacity=".35"
          strokeWidth="1.5"
        />
        <rect
          x="25"
          y="34"
          width="46"
          height="30"
          rx="6"
          fill="#07030d"
          opacity=".88"
        />
        <circle cx="39" cy="48" r="4.6" fill="#f0abfc" />
        <circle cx="57" cy="48" r="4.6" fill="#f0abfc" />
        <circle cx="40.5" cy="46.5" r="1.4" fill="#170a22" />
        <circle cx="58.5" cy="46.5" r="1.4" fill="#170a22" />
        <path
          d="M42 57c2 2 4 3 6 3s4-1 6-3"
          stroke="#f0abfc"
          strokeWidth="1.4"
          strokeLinecap="round"
          opacity=".8"
        />
        <path d="M28 72h6M62 72h6" stroke="black" strokeOpacity=".5" strokeWidth="2" />
      </svg>
    </div>
  );
}

function SkeletonLine({ width }: { width: string }) {
  return (
    <span
      className="block h-1 bg-slate-700/80"
      style={{ width }}
      aria-hidden
    />
  );
}

export default function HeroConsole({ stats, latest }: HeroConsoleProps) {
  const stageRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!stageRef.current) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const rect = stageRef.current.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    setTilt({ x: -y * 5, y: x * 9 });
  }

  const rows = latest.slice(0, 3);
  const transform = `rotateY(${-16 + tilt.y}deg) rotateX(${5 + tilt.x}deg) rotateZ(-1deg)`;

  return (
    <div
      ref={stageRef}
      className="hero-stage relative mx-auto w-full max-w-[700px]"
      onPointerMove={onPointerMove}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
    >
      <div className="console-glow" aria-hidden />
      <Mascot />

      <div
        className="console-tilt mx-auto"
        style={{ transform }}
        aria-hidden="true"
      >
        <div className="console-window">
          <div className="flex items-center gap-2 border-b border-slate-800 px-3 py-2">
            <span className="h-2 w-2 border border-sky-500/70 bg-sky-500/30" />
            <span className="h-2 w-2 border border-slate-600" />
            <span className="h-2 w-2 border border-slate-600" />
            <span className="ml-2 font-mono text-[9px] tracking-[0.16em] text-slate-500">
              radar://console
            </span>
            <span className="ml-auto flex items-center gap-1.5 text-[8px] uppercase tracking-[0.16em] text-emerald-300">
              <span className="status-dot" /> live
            </span>
          </div>

          <div className="grid grid-cols-[34px_1fr_94px] text-[10px]">
            <div className="flex flex-col items-center gap-3 border-r border-slate-800 py-4">
              <span className="h-4 w-4 border border-sky-500/60 bg-sky-500/20" />
              {[0, 1, 2, 3].map((item) => (
                <span key={item} className="h-1 w-4 bg-slate-700" />
              ))}
              <span className="mt-auto h-5 w-5 rounded-full border border-slate-700" />
            </div>

            <div className="min-w-0 border-r border-slate-800 p-3">
              <div className="flex items-center justify-between border border-slate-800 bg-black/30 px-2 py-1 text-[9px] text-slate-500">
                <span>
                  <span className="text-sky-400">$</span> scan --remote --profile
                </span>
                <span className="text-emerald-300">ok</span>
              </div>

              <div className="mt-3 flex gap-3">
                <div className="radar-scope relative h-28 w-28 shrink-0">
                  <span className="absolute left-[62%] top-[24%] h-1.5 w-1.5 rounded-full bg-sky-300 shadow-[0_0_8px_var(--accent)]" />
                  <span className="absolute left-[28%] top-[66%] h-1 w-1 rounded-full bg-violet-300" />
                  <span className="absolute left-[72%] top-[70%] h-1 w-1 rounded-full bg-emerald-400" />
                </div>
                <div className="min-w-0 flex-1 space-y-2">
                  <p className="text-[8px] uppercase tracking-[0.2em] text-slate-500">
                    signal / 24h
                  </p>
                  <p className="font-display text-4xl leading-none text-white">
                    {stats?.vacancies.new_last_7_days ?? "--"}
                  </p>
                  <div className="flex items-end gap-0.5">
                    {[3, 5, 4, 7, 6, 9, 7, 8, 11, 9, 12, 10].map((height, index) => (
                      <span
                        key={index}
                        className="w-1 bg-sky-500/70"
                        style={{ height: `${height * 3}px` }}
                      />
                    ))}
                  </div>
                  <p className="text-[8px] text-slate-500">
                    {stats?.vacancies.total ?? "--"} indexed ·{" "}
                    {stats?.analyses.analyses ?? "--"} scored
                  </p>
                </div>
              </div>

              <div className="mt-3 space-y-2">
                {rows.length > 0
                  ? rows.map((job, index) => (
                      <div
                        key={job.id}
                        className="flex items-center gap-2 border border-slate-800/80 bg-black/20 px-2 py-1.5"
                      >
                        <span className="w-4 text-[8px] text-slate-600">
                          0{index + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-[9px] text-slate-200">
                            {job.title}
                          </p>
                          <p className="truncate text-[8px] text-slate-500">
                            {job.company.name}
                          </p>
                        </div>
                        <span className="h-1 w-10 bg-slate-800">
                          <span
                            className="block h-full bg-sky-500"
                            style={{ width: `${72 - index * 14}%` }}
                          />
                        </span>
                      </div>
                    ))
                  : [1, 2, 3].map((item) => (
                      <div
                        key={item}
                        className="flex items-center gap-2 border border-slate-800/80 bg-black/20 px-2 py-1.5"
                      >
                        <span className="w-4 text-[8px] text-slate-600">0{item}</span>
                        <div className="flex-1 space-y-1">
                          <SkeletonLine width={`${70 - item * 8}%`} />
                          <SkeletonLine width="35%" />
                        </div>
                      </div>
                    ))}
              </div>

              <div className="mt-3 flex items-center gap-1.5 border-t border-slate-800 pt-2 text-[8px] text-slate-500">
                <span className="text-sky-400">radar@console:~$</span>
                <span>deliver --telegram</span>
                <span className="terminal-cursor h-2.5 w-1.5" />
              </div>
            </div>

            <div className="p-2">
              <p className="text-[8px] uppercase tracking-[0.18em] text-slate-500">
                queue
              </p>
              <div className="mt-2 space-y-2">
                {[80, 55, 68, 40, 72, 30].map((width, index) => (
                  <div key={index} className="space-y-1">
                    <SkeletonLine width={`${width}%`} />
                    {index % 2 === 0 ? (
                      <span className="block h-1 w-2 bg-sky-500/60" />
                    ) : null}
                  </div>
                ))}
              </div>
              <p className="mt-4 text-[8px] uppercase tracking-[0.18em] text-slate-500">
                workers
              </p>
              <p className="font-display text-2xl leading-none text-slate-200">
                02
              </p>
              <div className="mt-1 flex gap-1">
                <span className="h-1.5 w-1.5 bg-emerald-400" />
                <span className="h-1.5 w-1.5 bg-emerald-400" />
                <span className="h-1.5 w-1.5 bg-slate-700" />
              </div>
              <div className="mt-3 border border-slate-800 p-1.5 text-[8px] text-slate-500">
                <p>redis://</p>
                <p className="text-emerald-300">connected</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 mx-auto mt-6 max-w-[620px]">
        <p className="text-[10px] tracking-[0.08em] text-violet-300">
          pipeline/celery.kdl
        </p>
        <p className="mt-1 text-[10px] text-slate-400">
          collect → normalize → dedupe → score → notify.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <span className="bg-sky-500 px-2 py-1 text-[9px] uppercase tracking-[0.12em] text-slate-950">
            radar
          </span>
          <span className="border border-slate-700 px-2 py-1 text-[9px] uppercase tracking-[0.12em] text-slate-300">
            jobs {stats?.vacancies.total ?? "--"}
          </span>
          <span className="border border-slate-700 px-2 py-1 text-[9px] uppercase tracking-[0.12em] text-slate-300">
            analyses {stats?.analyses.analyses ?? "--"}
          </span>
          <span className="border border-slate-700 px-2 py-1 text-[9px] uppercase tracking-[0.12em] text-slate-300">
            remote {stats ? Math.round(stats.vacancies.remote_share * 100) : "--"}%
          </span>
        </div>
      </div>
    </div>
  );
}
