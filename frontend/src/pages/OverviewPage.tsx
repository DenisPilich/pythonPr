import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Globe2, Sparkles, TrendingUp } from "lucide-react";

import { api } from "../api/client";
import { formatRelative, formatShare, titleCase } from "../lib/format";
import JobCard from "../components/JobCard";
import { Badge, Card, CardHeader, ErrorState, PageHeader, Spinner } from "../components/ui";

const PIE_COLORS = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185"];
const TOOLTIP_STYLE = {
  background: "#0f172a",
  border: "1px solid #1e293b",
  borderRadius: 8,
  fontSize: 12,
};

function Kpi({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint: string;
  icon: typeof Activity;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
        <Icon className="h-4 w-4 text-sky-400" />
      </div>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </Card>
  );
}

export default function OverviewPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const latest = useQuery({
    queryKey: ["jobs", "latest"],
    queryFn: () => api.jobs({ limit: 4, sort: "published_at", order: "desc" }),
  });

  if (stats.isPending) return <Spinner label="Loading radar" />;
  if (stats.isError) {
    return <ErrorState message={stats.error.message} onRetry={() => stats.refetch()} />;
  }

  const data = stats.data;
  const averageScore = data.analyses.average_match_score;

  return (
    <div>
      <PageHeader
        title="Radar overview"
        subtitle="What the pipeline collected, scored and delivered."
        actions={
          <Badge tone="emerald">
            <Activity className="mr-1 h-3 w-3" />
            {data.collector_runs.last_status ?? "idle"}
          </Badge>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Vacancies"
          value={String(data.vacancies.total)}
          hint={`${data.vacancies.active} active`}
          icon={Globe2}
        />
        <Kpi
          label="New / 7 days"
          value={String(data.vacancies.new_last_7_days)}
          hint={`${data.vacancies.with_salary} with salary`}
          icon={TrendingUp}
        />
        <Kpi
          label="Remote share"
          value={formatShare(data.vacancies.remote_share)}
          hint={`${data.vacancies.remote} remote roles`}
          icon={Globe2}
        />
        <Kpi
          label="Average match"
          value={averageScore ? `${averageScore}%` : "—"}
          hint={`${data.analyses.analyses} AI analyses`}
          icon={Sparkles}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Top technologies" subtitle="By vacancy mentions" />
          <div className="h-80 p-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data.top_technologies.slice(0, 8)}
                layout="vertical"
                margin={{ left: 8, right: 16, top: 8, bottom: 8 }}
              >
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  tick={{ fill: "#cbd5e1", fontSize: 12 }}
                />
                <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "rgba(56,189,248,0.06)" }} />
                <Bar dataKey="count" fill="#38bdf8" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader title="Work formats" subtitle="Distribution across vacancies" />
          <div className="h-80 p-3">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.work_formats}
                  dataKey="count"
                  nameKey="key"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                >
                  {data.work_formats.map((entry, index) => (
                    <Cell key={entry.key} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Legend
                  formatter={(value: string) => (
                    <span style={{ color: "#94a3b8", fontSize: 12 }}>{titleCase(value)}</span>
                  )}
                />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Sources" subtitle="Health of every collector" />
          <div className="divide-y divide-slate-800/70">
            {data.sources.map((source) => (
              <div key={source.code} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-200">{source.name}</p>
                  <p className="text-xs text-slate-500">
                    {source.vacancies} vacancies · last success{" "}
                    {source.last_success_at ? formatRelative(source.last_success_at) : "never"}
                  </p>
                </div>
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
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Latest arrivals" subtitle="Fresh vacancies from all sources" />
          <div className="space-y-3 p-4">
            {latest.isPending ? (
              <p className="text-sm text-slate-500">Loading…</p>
            ) : (
              latest.data?.items.slice(0, 3).map((job) => <JobCard key={job.id} job={job} />)
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
