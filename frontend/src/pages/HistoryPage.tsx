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

const TABS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "new", label: "New" },
  { key: "saved", label: "Saved" },
  { key: "applied", label: "Applied" },
  { key: "rejected", label: "Skipped" },
];

export default function HistoryPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const history = useQuery({
    queryKey: ["history", filter],
    queryFn: () => api.history(filter === "all" ? undefined : filter),
  });

  if (history.isPending) return <Spinner label="Loading history" />;
  if (history.isError) {
    return <ErrorState message={history.error.message} onRetry={() => history.refetch()} />;
  }

  const data = history.data;
  const counts = data.counts;

  return (
    <div>
      <PageHeader
        title="History"
        subtitle="What the radar sent, saved, applied or skipped."
        actions={<Badge tone="sky">{counts.total} tracked</Badge>}
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { label: "New", value: counts.new, tone: "sky" as const },
          { label: "Viewed", value: counts.viewed, tone: "neutral" as const },
          { label: "Saved", value: counts.saved, tone: "emerald" as const },
          { label: "Applied", value: counts.applied, tone: "violet" as const },
          { label: "Skipped", value: counts.rejected, tone: "rose" as const },
        ].map((item) => (
          <Card key={item.label} className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{item.label}</p>
            <div className="mt-2 flex items-center justify-between">
              <p className="text-xl font-semibold text-white">{item.value}</p>
              <Badge tone={item.tone}>status</Badge>
            </div>
          </Card>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <Button
            key={tab.key}
            size="sm"
            variant={filter === tab.key ? "primary" : "outline"}
            onClick={() => setFilter(tab.key)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {data.items.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          description="Once the pipeline scores a vacancy for this profile, it appears in the history with its status."
        />
      ) : (
        <div className="grid gap-3">
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
