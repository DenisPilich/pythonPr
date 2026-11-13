import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { VacancyStatus } from "../api/types";
import JobCard from "../components/JobCard";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
} from "../components/ui";

type Filter = "all" | VacancyStatus;

const TABS: { key: Filter; label: string; tone: string }[] = [
  { key: "all", label: "all", tone: "text-slate-300" },
  { key: "new", label: "new", tone: "text-sky-300" },
  { key: "saved", label: "saved", tone: "text-emerald-300" },
  { key: "applied", label: "applied", tone: "text-violet-300" },
  { key: "rejected", label: "skipped", tone: "text-rose-300" },
];

export default function HistoryPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const history = useQuery({
    queryKey: ["history", filter],
    queryFn: () => api.history(filter === "all" ? undefined : filter),
  });

  if (history.isPending) return <Spinner label="loading history" />;
  if (history.isError) {
    return (
      <ErrorState message={history.error.message} onRetry={() => history.refetch()} />
    );
  }

  const data = history.data;
  const counts = data.counts;

  const stats = [
    { key: "new" as const, label: "new", value: counts.new },
    { key: "viewed" as const, label: "viewed", value: counts.viewed },
    { key: "saved" as const, label: "saved", value: counts.saved },
    { key: "applied" as const, label: "applied", value: counts.applied },
    { key: "rejected" as const, label: "skipped", value: counts.rejected },
  ];

  return (
    <div>
      <PageHeader
        title="History"
        subtitle="What the radar sent, saved, applied or skipped."
        actions={<Badge tone="sky">{counts.total} tracked</Badge>}
      />

      <div className="mb-4 border border-slate-800 bg-black/20 px-3 py-2 text-[10px] text-slate-500">
        <span className="text-emerald-400">$</span> tracking --user=100000001{" "}
        <span className="text-slate-700">|</span>{" "}
        <span className="text-slate-400">{counts.total} events</span>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {stats.map((item) => (
          <Card key={item.key} className="corner-frame p-3">
            <p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">
              {item.label}
            </p>
            <div className="mt-1 flex items-end justify-between">
              <p className="font-display text-4xl leading-none text-white">
                {item.value}
              </p>
              <span className="mb-1 h-1 w-6 bg-sky-500/60" />
            </div>
          </Card>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-1.5">
        <span className="mr-1 text-[9px] uppercase tracking-[0.16em] text-slate-600">
          filter:
        </span>
        {TABS.map((tab) => (
          <Button
            key={tab.key}
            size="sm"
            variant={filter === tab.key ? "primary" : "outline"}
            onClick={() => setFilter(tab.key)}
            className={filter === tab.key ? "" : tab.tone}
          >
            [ {tab.label} ]
          </Button>
        ))}
      </div>

      {data.items.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          description="Once the pipeline scores a vacancy for this profile, it appears in the history with its status."
        />
      ) : (
        <div className="grid gap-2.5">
          {data.items.map((item) => (
            <JobCard
              key={`${item.job.id}-${item.status}`}
              job={item.job}
              score={item.match_score}
              status={item.status}
            />
          ))}
        </div>
      )}
    </div>
  );
}
