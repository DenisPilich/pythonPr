import { Link } from "react-router-dom";
import { ArrowUpRight, Building2, MapPin } from "lucide-react";

import type { JobListItem, VacancyStatus } from "../api/types";
import { formatDate, formatSalary, STATUS_LABEL, titleCase } from "../lib/format";

interface JobCardProps {
  job: JobListItem;
  score?: number | null;
  status?: VacancyStatus;
}

export default function JobCard({ job, score, status }: JobCardProps) {
  const salary = formatSalary(job);
  const hasSalary = salary !== "Salary not specified";
  const location =
    job.location_raw &&
    job.location_raw.toLowerCase() !== job.work_format.toLowerCase()
      ? job.location_raw
      : null;
  const sourceCode = (job.sources[0]?.source ?? "api").slice(0, 3).toUpperCase();

  return (
    <Link
      to={`/jobs/${job.id}`}
      aria-label={`${job.title} at ${job.company.name}`}
      className="panel group flex overflow-hidden hover:border-sky-500/60 hover:bg-slate-900/70"
    >
      <div className="flex w-16 shrink-0 flex-col items-center justify-center border-r border-slate-800 bg-black/20 px-1 py-3">
        {typeof score === "number" ? (
          <>
            <span className="font-display text-3xl leading-none text-sky-300">
              {score}%
            </span>
            <span className="mt-1 text-[8px] uppercase tracking-[0.2em] text-slate-500">
              match
            </span>
          </>
        ) : (
          <>
            <span className="font-display text-lg leading-none text-slate-400">
              {sourceCode}
            </span>
            <span className="mt-1 text-[8px] uppercase tracking-[0.2em] text-slate-600">
              source
            </span>
          </>
        )}
      </div>

      <div className="min-w-0 flex-1 p-3.5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="line-clamp-2 text-[13px] font-medium leading-5 text-slate-100 transition-colors group-hover:text-sky-300">
            {job.title}
          </h3>
          <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-600 transition-all group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-sky-400" />
        </div>

        <p className="mt-1 flex items-center gap-1.5 text-[10px] text-slate-400">
          <Building2 className="h-3 w-3 text-slate-600" />
          {job.company.name}
          {status ? (
            <span className="ml-1 border border-slate-700 px-1 py-0.5 text-[8px] uppercase tracking-[0.14em] text-slate-400">
              {STATUS_LABEL[status]}
            </span>
          ) : null}
        </p>

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] uppercase tracking-[0.1em] text-slate-500">
          <span className="text-violet-300">{titleCase(job.work_format)}</span>
          <span>{titleCase(job.seniority)}</span>
          {location ? (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-2.5 w-2.5" />
              {location}
            </span>
          ) : null}
          <span className="ml-auto flex items-center gap-3 text-slate-500">
            {hasSalary ? <span className="text-slate-400">{salary}</span> : null}
            <span className="hidden sm:inline">
              {formatDate(job.published_at)}
            </span>
          </span>
        </div>

        {job.technologies.length > 0 ? (
          <div className="mt-2.5 flex flex-wrap gap-1">
            {job.technologies.slice(0, 7).map((tech) => (
              <span key={tech.slug} className="tech-chip">
                {tech.name}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </Link>
  );
}
