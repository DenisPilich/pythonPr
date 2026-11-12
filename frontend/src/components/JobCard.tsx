import { Link } from "react-router-dom";
import { Building2, MapPin, Wifi } from "lucide-react";

import type { JobListItem, VacancyStatus } from "../api/types";
import { formatSalary, STATUS_LABEL, titleCase } from "../lib/format";
import { Badge, Card, ScoreBadge } from "./ui";

interface JobCardProps {
  job: JobListItem;
  score?: number | null;
  status?: VacancyStatus;
}

export default function JobCard({ job, score, status }: JobCardProps) {
  return (
    <Card className="group p-4 transition-colors hover:border-slate-700 hover:bg-slate-900/70">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Link
            to={`/jobs/${job.id}`}
            className="line-clamp-2 text-base font-semibold text-slate-100 transition-colors group-hover:text-sky-300"
          >
            {job.title}
          </Link>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-400">
            <Building2 className="h-3.5 w-3.5" />
            {job.company.name}
          </p>
        </div>
        {typeof score === "number" ? <ScoreBadge score={score} /> : null}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
        <Badge tone="sky">
          <Wifi className="mr-1 h-3 w-3" />
          {titleCase(job.work_format)}
        </Badge>
        <Badge tone="violet">{titleCase(job.seniority)}</Badge>
        {job.location_raw ? (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {job.location_raw}
          </span>
        ) : null}
        <span className="text-slate-500">{formatSalary(job)}</span>
        {status ? <Badge tone="neutral">{STATUS_LABEL[status]}</Badge> : null}
      </div>

      {job.technologies.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {job.technologies.slice(0, 7).map((tech) => (
            <span
              key={tech.slug}
              className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-300"
            >
              {tech.name}
            </span>
          ))}
        </div>
      ) : null}
    </Card>
  );
}
