import { FormEvent, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search, SlidersHorizontal } from "lucide-react";

import { api } from "../api/client";
import type { JobFilters } from "../api/types";
import JobCard from "../components/JobCard";
import {
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
        actions={
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
            <SlidersHorizontal className="h-3.5 w-3.5" />
            {data?.total ?? 0} results
          </span>
        }
      />

      <Card className="mb-6 p-4">
        <form onSubmit={submit} className="grid gap-3 md:grid-cols-12">
          <div className="relative md:col-span-4">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-500" />
            <Input
              className="pl-9"
              placeholder="Search title or description…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-label="Search vacancies"
            />
          </div>
          <Select
            className="md:col-span-2"
            value={technology}
            onChange={(event) => setTechnology(event.target.value)}
            aria-label="Technology"
          >
            <option value="">Any technology</option>
            {technologies.data?.items.map((tech) => (
              <option key={tech.id} value={tech.slug}>
                {tech.name}
              </option>
            ))}
          </Select>
          <Select
            className="md:col-span-2"
            value={seniority}
            onChange={(event) => setSeniority(event.target.value)}
            aria-label="Seniority"
          >
            <option value="">Any level</option>
            {["junior", "middle", "senior", "lead"].map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </Select>
          <Select
            className="md:col-span-2"
            value={workFormat}
            onChange={(event) => setWorkFormat(event.target.value)}
            aria-label="Work format"
          >
            <option value="">Any format</option>
            {["remote", "hybrid", "office"].map((format) => (
              <option key={format} value={format}>
                {format}
              </option>
            ))}
          </Select>
          <Input
            className="md:col-span-2"
            type="number"
            min={0}
            placeholder="Min € / month"
            value={minSalary}
            onChange={(event) => setMinSalary(event.target.value)}
            aria-label="Minimum salary"
          />
          <div className="flex gap-2 md:col-span-4">
            <Button type="submit">Apply filters</Button>
            <Button type="button" variant="ghost" onClick={reset}>
              Reset
            </Button>
          </div>
          <Select
            className="md:col-span-3"
            value={sort}
            onChange={(event) => setSort(event.target.value)}
            aria-label="Sort"
          >
            <option value="published_at">Newest first</option>
            <option value="salary">Highest salary</option>
            <option value="title">Title A–Z</option>
          </Select>
        </form>
      </Card>

      {jobs.isPending ? <Spinner label="Loading vacancies" /> : null}
      {jobs.isError ? (
        <ErrorState message={jobs.error.message} onRetry={() => jobs.refetch()} />
      ) : null}

      {data && data.items.length === 0 ? (
        <EmptyState
          title="No vacancies match these filters"
          description="Try a broader query or reset the filters. New vacancies arrive with every collection run."
          action={<Button onClick={reset}>Reset filters</Button>}
        />
      ) : null}

      <div className="grid gap-3">
        {data?.items.map((job) => <JobCard key={job.id} job={job} />)}
      </div>

      {data && data.total > PAGE_SIZE ? (
        <div className="mt-6 flex items-center justify-between text-sm text-slate-400">
          <span>
            Page {page} of {pages}
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
              Previous
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
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
