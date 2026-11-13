import { FormEvent, useState } from "react";
import type { ReactNode } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import { api } from "../api/client";
import type { JobFilters } from "../api/types";
import JobCard from "../components/JobCard";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Select,
  Spinner,
} from "../components/ui";

const PAGE_SIZE = 12;

const EMPTY_FILTERS: JobFilters = { limit: PAGE_SIZE, offset: 0 };

function Field({ flag, children }: { flag: string; children: ReactNode }) {
  return (
    <label className="grid gap-1">
      <span className="text-[9px] uppercase tracking-[0.16em] text-slate-500">
        {flag}
      </span>
      {children}
    </label>
  );
}

export default function JobsPage() {
  const [query, setQuery] = useState("");
  const [technology, setTechnology] = useState("");
  const [seniority, setSeniority] = useState("");
  const [workFormat, setWorkFormat] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [sort, setSort] = useState("published_at");
  const [filters, setFilters] = useState<JobFilters>(EMPTY_FILTERS);

  const technologies = useQuery({
    queryKey: ["technologies"],
    queryFn: () => api.technologies(),
  });
  const jobs = useQuery({
    queryKey: ["jobs", filters],
    queryFn: () => api.jobs(filters),
    placeholderData: keepPreviousData,
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setFilters({
      q: query || undefined,
      technology: technology ? [technology] : undefined,
      seniority: seniority ? [seniority] : undefined,
      work_format: workFormat ? [workFormat] : undefined,
      min_salary: minSalary ? Number(minSalary) : undefined,
      sort,
      order: "desc",
      limit: PAGE_SIZE,
      offset: 0,
    });
  }

  function reset() {
    setQuery("");
    setTechnology("");
    setSeniority("");
    setWorkFormat("");
    setMinSalary("");
    setSort("published_at");
    setFilters(EMPTY_FILTERS);
  }

  const data = jobs.data;
  const page = Math.floor((filters.offset ?? 0) / PAGE_SIZE) + 1;
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <PageHeader
        title="Vacancies"
        subtitle="Search the normalized feed, then open a vacancy for the AI verdict."
        actions={<Badge tone="sky">{data?.total ?? 0} matches</Badge>}
      />

      <Card className="corner-frame mb-5">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2.5">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">
            <span className="text-emerald-400">$</span> radar query
          </p>
          <span className="text-[9px] uppercase tracking-[0.16em] text-slate-600">
            filters
          </span>
        </div>

        <form onSubmit={submit} className="grid gap-3 p-4 md:grid-cols-12">
          <div className="md:col-span-4">
            <Field flag="--q">
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-600" />
                <Input
                  className="pl-8"
                  placeholder="title or description…"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  aria-label="Search vacancies"
                />
              </div>
            </Field>
          </div>

          <div className="md:col-span-2">
            <Field flag="--tech">
              <Select
                value={technology}
                onChange={(event) => setTechnology(event.target.value)}
                aria-label="Technology"
              >
                <option value="">any</option>
                {technologies.data?.items.map((tech) => (
                  <option key={tech.id} value={tech.slug}>
                    {tech.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="md:col-span-2">
            <Field flag="--level">
              <Select
                value={seniority}
                onChange={(event) => setSeniority(event.target.value)}
                aria-label="Seniority"
              >
                <option value="">any</option>
                {["junior", "middle", "senior", "lead"].map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="md:col-span-2">
            <Field flag="--format">
              <Select
                value={workFormat}
                onChange={(event) => setWorkFormat(event.target.value)}
                aria-label="Work format"
              >
                <option value="">any</option>
                {["remote", "hybrid", "office"].map((format) => (
                  <option key={format} value={format}>
                    {format}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="md:col-span-2">
            <Field flag="--salary">
              <Input
                type="number"
                min={0}
                placeholder="min € / month"
                value={minSalary}
                onChange={(event) => setMinSalary(event.target.value)}
                aria-label="Minimum salary"
              />
            </Field>
          </div>

          <div className="flex flex-wrap items-end gap-2 md:col-span-3">
            <Button type="submit">[ run ]</Button>
            <Button type="button" variant="ghost" onClick={reset}>
              [ reset ]
            </Button>
          </div>

          <div className="md:col-span-3">
            <Field flag="--sort">
              <Select
                value={sort}
                onChange={(event) => setSort(event.target.value)}
                aria-label="Sort"
              >
                <option value="published_at">newest first</option>
                <option value="salary">highest salary</option>
                <option value="title">title a–z</option>
              </Select>
            </Field>
          </div>

          <p className="hidden items-end justify-end pb-2 text-right text-[9px] uppercase tracking-[0.14em] text-slate-600 md:col-span-6 md:flex">
            // enter runs query · filters combine with AND
          </p>
        </form>
      </Card>

      {jobs.isPending ? <Spinner label="querying vacancies" /> : null}
      {jobs.isError ? (
        <ErrorState message={jobs.error.message} onRetry={() => jobs.refetch()} />
      ) : null}

      {data ? (
        <div className="mb-3 flex items-center justify-between text-[9px] uppercase tracking-[0.16em] text-slate-500">
          <span>
            <span className="text-sky-400">&gt;&gt;</span> {data.total} records ·
            offset {data.offset}
          </span>
          <span>
            page {page}/{pages}
          </span>
        </div>
      ) : null}

      {data && data.items.length === 0 ? (
        <EmptyState
          title="No vacancies match"
          description="Try a broader query or reset the filters. New vacancies arrive with every collection run."
          action={<Button onClick={reset}>[ reset filters ]</Button>}
        />
      ) : null}

      <div className="grid gap-2.5">
        {data?.items.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>

      {data && data.total > PAGE_SIZE ? (
        <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-3 text-[9px] uppercase tracking-[0.16em] text-slate-500">
          <span>
            {filters.offset ?? 0}–
            {Math.min((filters.offset ?? 0) + PAGE_SIZE, data.total)} of{" "}
            {data.total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  offset: Math.max(0, (current.offset ?? 0) - PAGE_SIZE),
                }))
              }
            >
              [ prev ]
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pages}
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  offset: (current.offset ?? 0) + PAGE_SIZE,
                }))
              }
            >
              [ next ]
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
