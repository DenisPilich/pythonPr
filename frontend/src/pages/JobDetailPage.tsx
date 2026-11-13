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

  if (job.isPending) return <Spinner label="opening vacancy" />;
  if (job.isError) {
    return <ErrorState message={job.error.message} onRetry={() => job.refetch()} />;
  }

  const vacancy = job.data;
  const verdict = analysis.data ?? analyze.data ?? null;

  return (
    <div>
      <Link
        to="/jobs"
        className="mb-4 inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-slate-500 transition-colors hover:text-sky-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> cd ../vacancies
      </Link>

      <Card className="corner-frame overflow-hidden">
        <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-2">
          <span className="h-2 w-2 border border-sky-500/60 bg-sky-500/20" />
          <span className="h-2 w-2 border border-slate-700" />
          <span className="h-2 w-2 border border-slate-700" />
          <span className="ml-2 truncate text-[9px] uppercase tracking-[0.16em] text-slate-500">
            job://{vacancy.id.slice(0, 8)} · {vacancy.sources[0]?.source ?? "manual"}
          </span>
          <span className="ml-auto hidden text-[9px] uppercase tracking-[0.16em] text-slate-600 sm:inline">
            [ posting ]
          </span>
        </div>

        <div className="p-5 md:p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div className="min-w-0">
              <p className="text-[9px] uppercase tracking-[0.2em] text-slate-500">
                {vacancy.company.name} / {vacancy.location_raw ?? "location unknown"}
              </p>
              <h1 className="mt-2 max-w-3xl font-display text-4xl leading-[0.95] text-white md:text-5xl">
                {vacancy.title}
              </h1>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Badge tone="sky">{titleCase(vacancy.work_format)}</Badge>
                <Badge tone="violet">{titleCase(vacancy.seniority)}</Badge>
                <Badge tone="neutral">{vacancy.language.toUpperCase()}</Badge>
                <span className="text-[10px] text-slate-400">
                  {formatSalary(vacancy)}
                </span>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {verdict ? <ScoreBadge score={verdict.match_score} /> : null}
              {vacancy.url ? (
                <a href={vacancy.url} target="_blank" rel="noreferrer">
                  <Button variant="outline">
                    [ source ] <ExternalLink className="h-3 w-3" />
                  </Button>
                </a>
              ) : null}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-1">
            {vacancy.technologies.map((tech) => (
              <span key={tech.slug} className="tech-chip">
                {tech.name}
              </span>
            ))}
          </div>

          <p className="mt-4 border-t border-slate-800 pt-3 text-[9px] uppercase tracking-[0.14em] text-slate-500">
            published {formatDate(vacancy.published_at)} · first seen{" "}
            {formatDate(vacancy.first_seen_at)} · {vacancy.sources.length} source(s)
          </p>
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="description.md"
            subtitle="cleaned text used for matching"
            action={<span className="text-[9px] text-slate-600">[ read ]</span>}
          />
          <div className="max-h-[620px] overflow-y-auto whitespace-pre-line px-5 py-4 text-[11px] leading-6 text-slate-300">
            {vacancy.description || "No description provided by the source."}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="ai_analysis.json"
            subtitle={
              verdict
                ? `${verdict.provider} · ${verdict.model} · prompt ${verdict.prompt_version}`
                : "no verdict yet"
            }
            action={
              verdict?.is_degraded ? <Badge tone="amber">degraded</Badge> : undefined
            }
          />
          <div className="p-5">
            {analysis.isPending ? <Spinner label="loading verdict" /> : null}

            {!verdict && !analysis.isPending ? (
              <div className="text-center">
                <Sparkles className="mx-auto h-7 w-7 text-sky-400" />
                <p className="mt-3 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  no cached analysis
                </p>
                <p className="mt-2 text-[11px] leading-5 text-slate-400">
                  Compare this vacancy with the current profile. The result is
                  cached by profile hash and prompt version.
                </p>
                <Button
                  className="mt-4"
                  onClick={() => analyze.mutate()}
                  disabled={analyze.isPending}
                >
                  {analyze.isPending ? "[ analysing ]" : "[ run analysis ]"}
                </Button>
                {analyze.isError ? (
                  <p className="mt-3 text-[10px] text-rose-300">
                    {analyze.error.message}
                  </p>
                ) : null}
              </div>
            ) : null}

            {verdict ? (
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                    match_score
                  </span>
                  <Badge
                    tone={
                      verdict.recommendation === "apply"
                        ? "emerald"
                        : verdict.recommendation === "consider"
                          ? "amber"
                          : "rose"
                    }
                  >
                    {verdict.recommendation}
                  </Badge>
                </div>
                <p className="mt-1 font-display text-6xl leading-none text-sky-300">
                  {verdict.match_score}%
                </p>

                <p className="mt-4 border-l border-sky-500/50 pl-3 text-[11px] leading-5 text-slate-300">
                  {verdict.reason}
                </p>

                <div className="mt-4 border-t border-slate-800 pt-3">
                  <p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">
                    experience_match
                  </p>
                  <p className="mt-1 text-[11px] text-slate-300">
                    {verdict.experience_match}
                  </p>
                </div>

                {verdict.strong_matches.length > 0 ? (
                  <div className="mt-4">
                    <p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">
                      strong_matches
                    </p>
                    <ul className="mt-1 space-y-0.5 text-[11px] text-emerald-300">
                      {verdict.strong_matches.map((skill) => (
                        <li key={skill}>
                          <span className="text-emerald-500">+</span> {skill}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {verdict.missing_skills.length > 0 ? (
                  <div className="mt-4">
                    <p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">
                      missing_skills
                    </p>
                    <ul className="mt-1 space-y-0.5 text-[11px] text-rose-300">
                      {verdict.missing_skills.map((skill) => (
                        <li key={skill}>
                          <span className="text-rose-500">−</span> {skill}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {verdict.red_flags.length > 0 ? (
                  <div className="mt-4">
                    <p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">
                      red_flags
                    </p>
                    <ul className="mt-1 space-y-0.5 text-[11px] text-amber-300">
                      {verdict.red_flags.map((flag) => (
                        <li key={flag}>
                          <span className="text-amber-500">!</span> {flag}
                        </li>
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
                  {analyze.isPending ? "[ analysing ]" : "[ re-run analysis ]"}
                </Button>
              </div>
            ) : null}
          </div>
        </Card>
      </div>
    </div>
  );
}
