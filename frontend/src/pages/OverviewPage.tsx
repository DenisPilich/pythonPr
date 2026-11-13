import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowUpRight, Database, Globe2, Sparkles, TrendingUp } from "lucide-react";

import { api } from "../api/client";
import { formatRelative, formatShare, titleCase } from "../lib/format";
import HeroConsole from "../components/HeroConsole";
import JobCard from "../components/JobCard";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ErrorState,
  Spinner,
} from "../components/ui";

const PIE_COLORS = [
  "var(--accent)",
  "var(--secondary)",
  "var(--green)",
  "var(--amber)",
  "var(--red)",
];

const TOOLTIP_STYLE = {
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 0,
  fontSize: 11,
  fontFamily: "var(--font-code)",
  color: "var(--text)",
};

const CHART_TICK = {
  fill: "var(--muted)",
  fontSize: 10,
  fontFamily: "var(--font-code)",
};

function Metric({
  code,
  label,
  value,
  detail,
  icon: Icon,
}: {
  code: string;
  label: string;
  value: string;
  detail: string;
  icon: typeof Database;
}) {
  return (
    <Card className="corner-frame p-4">
      <div className="flex items-center justify-between">
        <span className="code-label">{label}</span>
        <Icon className="h-3.5 w-3.5 text-sky-400" />
      </div>
      <p className="mt-2 font-display text-5xl leading-none text-white">{value}</p>
      <div className="mt-2 flex items-center justify-between gap-2">
        <p className="truncate text-[10px] text-slate-500">{detail}</p>
        <span className="text-[9px] text-slate-700">{code}</span>
      </div>
    </Card>
  );
}

export default function OverviewPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const latest = useQuery({
    queryKey: ["jobs", "latest"],
    queryFn: () => api.jobs({ limit: 9, sort: "published_at", order: "desc" }),
  });

  if (stats.isError) {
    return <ErrorState message={stats.error.message} onRetry={() => stats.refetch()} />;
  }

  const data = stats.data;
  const averageScore = data?.analyses.average_match_score;
  const heroJobs = (latest.data?.items ?? []).filter(
    (job) => job.technologies.length > 0,
  );

  return (
    <div>
      <section className="grid items-center gap-10 pb-2 lg:grid-cols-[minmax(0,6fr)_minmax(0,6fr)] lg:gap-8">
        <div>
          <p className="font-mono text-[10px] tracking-[0.12em] text-slate-500">
            <span className="text-sky-400">layout</span> {"{ row {"}{" "}
            <span className="text-slate-600">// ai job radar · v0.1.0</span>
          </p>

          <h1 className="display-hero mt-5 text-white">
            Vacancies,
            <br />
            <span className="display-em">without the noise.</span>
            <br />
            Delivered<span className="text-sky-400">.</span>
          </h1>

          <p className="mt-6 font-mono text-[11px] text-slate-400">
            <span className="text-emerald-400">$</span> radar scan --remote
            --profile=python <span className="terminal-cursor" aria-hidden />
          </p>

          <p className="mt-4 max-w-[460px] text-xs leading-6 text-slate-400">
            Five job boards, one deduplicated feed. Every vacancy is scored
            against your profile, filtered by your rules and pushed to
            Telegram — only when it clears the threshold.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-2">
            <Link to="/jobs">
              <Button>
                open the radar <ArrowUpRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
            <Link to="/history">
              <Button variant="outline">[ view pipeline ]</Button>
            </Link>
            <Link to="/profile">
              <Button variant="ghost">profile.kdl</Button>
            </Link>
          </div>

          <p className="mt-5 max-w-[440px] text-[10px] leading-5 text-amber-300/90">
            Demo mode: deterministic mock AI, no paid key required. Telegram
            delivery starts when <span className="text-amber-200">TELEGRAM_BOT_TOKEN</span>{" "}
            is set.
          </p>
        </div>

        <HeroConsole
          stats={data}
          latest={heroJobs.length > 0 ? heroJobs : latest.data?.items ?? []}
        />
      </section>

      <div className="mt-10 flex flex-wrap items-center gap-x-3 gap-y-2 border-y border-slate-800 py-3 text-[9px] uppercase tracking-[0.18em] text-slate-500">
        <span className="text-sky-400">pipeline</span>
        {["collect", "normalize", "dedupe", "score", "notify"].map((step, index) => (
          <span key={step} className="flex items-center gap-3">
            <span className={index === 3 ? "text-slate-200" : ""}>{step}</span>
            {index < 4 ? <span className="text-slate-700">→</span> : null}
          </span>
        ))}
        <span className="ml-auto flex items-center gap-2 text-slate-600">
          <span className="status-dot" />
          {data ? `${data.vacancies.total} records` : "syncing"}
        </span>
      </div>

      <div className="mt-8 scroll-mt-24" id="telemetry">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <p className="code-label">telemetry</p>
            <h2 className="mt-1 font-display text-3xl text-white">
              live<span className="text-sky-400">_</span>snapshot
            </h2>
          </div>
          <Badge tone="emerald">
            <span className="status-dot mr-1.5" />
            {data?.collector_runs.last_status ?? "idle"}
          </Badge>
        </div>

        {stats.isPending ? (
          <Spinner label="syncing telemetry" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric
              code="01"
              label="vacancies"
              value={String(data?.vacancies.total ?? 0)}
              detail={`${data?.vacancies.active ?? 0} active`}
              icon={Database}
            />
            <Metric
              code="02"
              label="new / 7d"
              value={String(data?.vacancies.new_last_7_days ?? 0)}
              detail={`${data?.vacancies.with_salary ?? 0} with salary`}
              icon={TrendingUp}
            />
            <Metric
              code="03"
              label="remote"
              value={formatShare(data?.vacancies.remote_share ?? 0)}
              detail={`${data?.vacancies.remote ?? 0} remote roles`}
              icon={Globe2}
            />
            <Metric
              code="04"
              label="avg match"
              value={averageScore ? `${averageScore}%` : "—"}
              detail={`${data?.analyses.analyses ?? 0} ai analyses`}
              icon={Sparkles}
            />
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-4 scroll-mt-24 lg:grid-cols-3" id="charts">
        <Card className="lg:col-span-2">
          <CardHeader
            title="top_technologies"
            subtitle="mentions across active vacancies"
            action={<span className="text-[9px] text-slate-600">[ bar ]</span>}
          />
          <div className="h-80 p-3">
            {data ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.top_technologies.slice(0, 8)}
                  layout="vertical"
                  margin={{ left: 8, right: 16, top: 8, bottom: 8 }}
                >
                  <CartesianGrid
                    horizontal={false}
                    stroke="var(--border)"
                    strokeDasharray="2 4"
                  />
                  <XAxis
                    type="number"
                    tick={CHART_TICK}
                    axisLine={{ stroke: "var(--border)" }}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={108}
                    tick={CHART_TICK}
                    axisLine={{ stroke: "var(--border)" }}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    cursor={{ fill: "var(--accent)", fillOpacity: 0.06 }}
                  />
                  <Bar
                    dataKey="count"
                    fill="var(--accent)"
                    radius={[0, 0, 0, 0]}
                    barSize={12}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Spinner label="loading chart" />
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="work_formats"
            subtitle="distribution"
            action={<span className="text-[9px] text-slate-600">[ pie ]</span>}
          />
          <div className="h-80 p-3">
            {data ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.work_formats}
                    dataKey="count"
                    nameKey="key"
                    innerRadius={52}
                    outerRadius={88}
                    paddingAngle={2}
                    stroke="var(--bg)"
                    strokeWidth={2}
                  >
                    {data.work_formats.map((entry, index) => (
                      <Cell key={entry.key} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Legend
                    formatter={(value: string) => (
                      <span
                        style={{
                          color: "var(--muted)",
                          fontSize: 10,
                          fontFamily: "var(--font-code)",
                          textTransform: "uppercase",
                          letterSpacing: "0.12em",
                        }}
                      >
                        {titleCase(value)}
                      </span>
                    )}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Spinner label="loading chart" />
            )}
          </div>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 scroll-mt-24 lg:grid-cols-3" id="sources">
        <Card className="lg:col-span-2">
          <CardHeader
            title="sources"
            subtitle="collector health"
            action={<span className="text-[9px] text-slate-600">[ 5 ]</span>}
          />
          <div className="divide-y divide-slate-800">
            {data?.sources.map((source) => (
              <div
                key={source.code}
                className="flex items-center justify-between gap-4 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-[11px] text-slate-200">
                    <span
                      className={
                        source.last_run_status === "failed"
                          ? "h-1.5 w-1.5 bg-rose-400"
                          : "h-1.5 w-1.5 bg-emerald-400"
                      }
                    />
                    {source.name}
                  </p>
                  <p className="mt-0.5 text-[9px] text-slate-500">
                    {source.vacancies} vacancies · last success{" "}
                    {source.last_success_at
                      ? formatRelative(source.last_success_at)
                      : "never"}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="hidden text-[9px] uppercase tracking-[0.12em] text-slate-600 sm:inline">
                    {source.code}
                  </span>
                  <Badge
                    tone={
                      source.last_run_status === "failed"
                        ? "rose"
                        : source.last_run_status === "partial"
                          ? "amber"
                          : "emerald"
                    }
                  >
                    {source.last_run_status ?? "idle"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="latest_arrivals" subtitle="fresh signal" />
          <div className="space-y-3 p-3">
            {latest.isPending ? (
              <p className="py-6 text-center text-[10px] uppercase tracking-[0.2em] text-slate-500">
                [ loading ]
              </p>
            ) : (
              latest.data?.items
                .slice(0, 3)
                .map((job) => <JobCard key={job.id} job={job} />)
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
