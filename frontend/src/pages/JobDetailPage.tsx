import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, Sparkles } from "lucide-react";

import { api } from "../api/client";
import { formatDate, formatSalary, titleCase } from "../lib/format";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ErrorState,
  ScoreBadge,
  Spinner,
} from "../components/ui";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const job = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.job(id!),
    enabled: Boolean(id),
  });
  const analysis = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => api.analysis(id!),
    enabled: Boolean(id),
  });
  const analyze = useMutation({
    mutationFn: () => api.analyze(id!),
    onSuccess: (data) => {
      queryClient.setQueryData(["analysis", id], data);
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  if (job.isPending) return <Spinner label="Loading vacancy" />;
  if (job.isError) {
    return <ErrorState message={job.error.message} onRetry={() => job.refetch()} />;
  }

  const vacancy = job.data;
  const verdict = analysis.data ?? analyze.data ?? null;

  return (
    <div>
      <Link
        to="/jobs"
        className="mb-5 inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-sky-300"
      >
        <ArrowLeft className="h-4 w-4" /> Back to vacancies
      </Link>

      <Card className="p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">{vacancy.title}</h1>
            <p className="mt-1 text-slate-400">
              {vacancy.company.name} · {vacancy.location_raw ?? "Location not specified"}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Badge tone="sky">{titleCase(vacancy.work_format)}</Badge>
              <Badge tone="violet">{titleCase(vacancy.seniority)}</Badge>
              <Badge tone="neutral">{vacancy.language.toUpperCase()}</Badge>
              <span className="text-sm text-slate-400">{formatSalary(vacancy)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {verdict ? <ScoreBadge score={verdict.match_score} /> : null}
            {vacancy.url ? (
              <a href={vacancy.url} target="_blank" rel="noreferrer">
                <Button variant="outline">
                  Open posting <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </a>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-1.5">
          {vacancy.technologies.map((tech) => (
            <span
              key={tech.slug}
              className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-300"
            >
              {tech.name}
            </span>
          ))}
        </div>

        <p className="mt-4 text-xs text-slate-500">
          Published {formatDate(vacancy.published_at)} · first seen{" "}
          {formatDate(vacancy.first_seen_at)} · {vacancy.sources.length} source(s)
        </p>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Description" subtitle="Cleaned text used for matching" />
          <div className="max-h-[560px] overflow-y-auto whitespace-pre-line px-5 py-4 text-sm leading-6 text-slate-300">
            {vacancy.description || "No description provided by the source."}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="AI analysis"
            subtitle={
              verdict
                ? `${verdict.provider} · ${verdict.model} · prompt ${verdict.prompt_version}`
                : "Not analysed yet"
            }
            action={
              verdict?.is_degraded ? <Badge tone="amber">degraded</Badge> : undefined
            }
          />
          <div className="p-5">
            {analysis.isPending ? <Spinner label="Loading verdict" /> : null}

            {!verdict && !analysis.isPending ? (
              <div className="text-center">
                <Sparkles className="mx-auto h-8 w-8 text-sky-400" />
                <p className="mt-3 text-sm text-slate-400">
                  Compare this vacancy with the current profile.
                </p>
                <Button
                  className="mt-4"
                  onClick={() => analyze.mutate()}
                  disabled={analyze.isPending}
                >
                  {analyze.isPending ? "Analysing…" : "Analyse with AI"}
                </Button>
                {analyze.isError ? (
                  <p className="mt-3 text-xs text-rose-300">{analyze.error.message}</p>
                ) : null}
              </div>
            ) : null}

            {verdict ? (
              <div>
                <div className="flex items-center justify-between">
                  <ScoreBadge score={verdict.match_score} />
                  <Badge
                    tone={
                      verdict.recommendation === "apply"
                        ? "emerald"
                        : verdict.recommendation === "consider"
                          ? "amber"
                          : "rose"
                    }
                  >
                    {verdict.recommendation.toUpperCase()}
                  </Badge>
                </div>

                <p className="mt-4 text-sm leading-6 text-slate-300">{verdict.reason}</p>

                <div className="mt-4 border-t border-slate-800 pt-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Experience</p>
                  <p className="mt-1 text-sm text-slate-300">{verdict.experience_match}</p>
                </div>

                {verdict.strong_matches.length > 0 ? (
                  <div className="mt-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Strong matches
                    </p>
                    <ul className="mt-1 space-y-1 text-sm text-emerald-300">
                      {verdict.strong_matches.map((skill) => (
                        <li key={skill}>+ {skill}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {verdict.missing_skills.length > 0 ? (
                  <div className="mt-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Missing skills
                    </p>
                    <ul className="mt-1 space-y-1 text-sm text-rose-300">
                      {verdict.missing_skills.map((skill) => (
                        <li key={skill}>− {skill}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {verdict.red_flags.length > 0 ? (
                  <div className="mt-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Red flags</p>
                    <ul className="mt-1 space-y-1 text-sm text-amber-300">
                      {verdict.red_flags.map((flag) => (
                        <li key={flag}>! {flag}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <Button
                  variant="outline"
                  size="sm"
                  className="mt-5 w-full"
                  onClick={() => analyze.mutate()}
                  disabled={analyze.isPending}
                >
                  Re-run analysis
                </Button>
              </div>
            ) : null}
          </div>
        </Card>
      </div>
    </div>
  );
}
